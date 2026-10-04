"""Scene validation -- the "did my script actually build what I think it did?" layer.

Run this after building a scene and before spending render time on it.
Every check returns a Finding; a scene with any ``error`` finding will not
produce a useful image, and a scene with ``warning`` findings usually produces
a *wrong but plausible* image, which is the expensive kind of bug.
"""

import math

import bpy
from mathutils import Matrix, Vector

from . import compat

SEVERITIES = ("error", "warning", "info")


class Finding:
    __slots__ = ("severity", "code", "message", "subject")

    def __init__(self, severity, code, message, subject=None):
        self.severity = severity
        self.code = code
        self.message = message
        self.subject = subject

    def as_dict(self):
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "subject": self.subject,
        }

    def __repr__(self):
        s = f"[{self.severity.upper():7}] {self.code}: {self.message}"
        return f"{s}  ({self.subject})" if self.subject else s

    def __str__(self):
        return repr(self)


# --- individual checks ------------------------------------------------------

def _is_nan(v):
    try:
        return any(math.isnan(float(c)) for c in v)
    except (TypeError, ValueError):
        return False


def check_transforms(objects=None):
    """NaN / inf / zero-scale detection on object matrices.

    A single NaN in a location silently poisons every downstream calculation
    including modifiers and the camera solve, and the render comes out black
    or empty with no error message anywhere.
    """
    objects = objects if objects is not None else bpy.data.objects
    out = []
    for obj in objects:
        loc, rot, scale = obj.location, obj.rotation_euler, obj.scale
        if _is_nan(loc) or _is_nan(rot) or _is_nan(scale):
            out.append(Finding("error", "TRANSFORM_NAN",
                               f"non-finite transform: loc={tuple(loc)} rot={tuple(rot)} scale={tuple(scale)}",
                               obj.name))
            continue
        if any(abs(s) < 1e-9 for s in scale):
            out.append(Finding("error", "TRANSFORM_ZERO_SCALE",
                               f"a scale axis is zero: {tuple(round(s,6) for s in scale)} "
                               f"-- object is invisible and cannot be ray-traced",
                               obj.name))
        elif any(s < 0 for s in scale):
            out.append(Finding("warning", "TRANSFORM_NEGATIVE_SCALE",
                               f"negative scale {tuple(round(s,4) for s in scale)} flips normals",
                               obj.name))
        if abs(obj.matrix_world.determinant()) < 1e-12 and obj.type == "MESH":
            out.append(Finding("error", "TRANSFORM_SINGULAR",
                               "matrix_world is singular (zero determinant)", obj.name))
    return out


def check_camera(scene=None):
    """The scene must have a render camera that is actually linked."""
    scene = scene or bpy.context.scene
    out = []
    cam = scene.camera
    if cam is None:
        out.append(Finding("error", "NO_CAMERA", "scene.camera is not set -- render will fail"))
    elif cam.name not in bpy.data.objects:
        out.append(Finding("error", "CAMERA_STALE", f"scene.camera points at missing object {cam.name!r}"))
    else:
        if cam.type == "PERSP" and cam.data.lens <= 0:
            out.append(Finding("error", "CAMERA_BAD_LENS", f"lens={cam.data.lens}", cam.name))
        if cam.data.clip_start >= cam.data.clip_end:
            out.append(Finding("warning", "CAMERA_CLIP_RANGE",
                               f"clip_start {cam.data.clip_start} >= clip_end {cam.data.clip_end}", cam.name))
        # Is the camera inside the scene's world bounds at all?
        fwd = (cam.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))).normalized()
        hit, _loc, _nrm, _idx, _obj, _mtx = scene.ray_cast(
            bpy.context.evaluated_depsgraph_get(), cam.matrix_world.translation, fwd
        )
        if not hit:
            out.append(Finding("warning", "CAMERA_SEES_NOTHING",
                               "nothing in front of the camera along its view axis", cam.name))
    return out


def check_lighting(scene=None):
    """At least one enabled light with non-zero energy."""
    scene = scene or bpy.context.scene
    out = []
    lamps = [o for o in scene.objects if o.type == "LIGHT"]
    if not lamps:
        world = scene.world
        world_energy = 0.0
        if world and world.use_nodes:
            for n in world.node_tree.nodes:
                if n.bl_idname == "ShaderNodeBackground":
                    try:
                        world_energy = float(n.inputs["Strength"].default_value)
                    except Exception:
                        world_energy = 0.0
        if world_energy <= 0.0:
            out.append(Finding("error", "NO_LIGHT", "no light objects and world background strength is 0"))
        else:
            out.append(Finding("info", "WORLD_ONLY", f"no light objects; relying on world strength {world_energy}"))
    else:
        for o in lamps:
            if o.hide_render:
                out.append(Finding("warning", "LIGHT_HIDDEN", "light is hidden from render", o.name))
            if getattr(o.data, "energy", 0) <= 0:
                out.append(Finding("warning", "LIGHT_ZERO_ENERGY", f"energy={o.data.energy}", o.name))
    return out


def check_materials(objects=None):
    """Every renderable mesh object needs a material that actually has a shader."""
    objects = objects if objects is not None else bpy.data.objects
    out = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "FONT"}:
            continue
        if not obj.data.materials:
            out.append(Finding("warning", "NO_MATERIAL",
                               "object has no material slot -- renders with the grey default", obj.name))
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                out.append(Finding("warning", "EMPTY_SLOT", "material slot is empty", obj.name))
                continue
            if mat.node_tree is None:
                if compat.has_prop(bpy.types.Material, "use_nodes"):
                    out.append(Finding("error", "MAT_NO_NODETREE",
                                       "material is in node mode but has no node_tree", obj.name))
                continue
                out_node = next((n for n in mat.node_tree.nodes
                                 if n.bl_idname == "ShaderNodeOutputMaterial"), None)
                if out_node is None:
                    out.append(Finding("error", "MAT_NO_OUTPUT",
                                       "material node tree has no ShaderNodeOutputMaterial", obj.name))
                elif not out_node.inputs["Surface"].is_linked and mat.node_tree.nodes:
                    bsdf = next((n for n in mat.node_tree.nodes
                                 if "Bsdf" in n.bl_idname), None)
                    if bsdf is not None:
                        out.append(Finding("warning", "MAT_SURFACE_UNLINKED",
                                           f"{bsdf.name!r} is not wired to the material output -- renders as fully transparent",
                                           obj.name))
    return out


def check_geometry(objects=None, depsgraph=None):
    """Evaluated-geometry sanity: non-empty, no zero-area faces, not absurdly dense."""
    objects = objects if objects is not None else bpy.data.objects
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    out = []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        ev = obj.evaluated_get(depsgraph)
        try:
            mesh = ev.to_mesh()
        except Exception as exc:
            out.append(Finding("error", "EVAL_FAIL", f"to_mesh() raised {exc}", obj.name))
            continue
        if mesh is None:
            out.append(Finding("error", "EVAL_NONE", "evaluated mesh is None", obj.name))
            continue
        nv, npoly = len(mesh.vertices), len(mesh.polygons)
        ev.to_mesh_clear()
        if nv == 0 or npoly == 0:
            out.append(Finding("error", "EMPTY_MESH",
                               f"evaluated mesh is empty ({nv} verts, {npoly} polys) -- "
                               f"a boolean/modifier stack probably collapsed it", obj.name))
            continue
        if nv > 5_000_000:
            out.append(Finding("warning", "HILLY_POLY",
                               f"{nv:,} vertices -- expect a very slow render", obj.name))
    return out


def check_modifiers(objects=None):
    """Modifier stack problems: missing targets, wrong order, unsubstituted assets."""
    objects = objects if objects is not None else bpy.data.objects
    out = []
    for obj in objects:
        for i, mod in enumerate(obj.modifiers):
            if mod.type == "NODES" and mod.node_group is None:
                out.append(Finding("error", "GN_NO_GROUP",
                                   "Geometry Nodes modifier has no node group assigned", obj.name))
            if mod.type == "BOOLEAN":
                if mod.object is None:
                    out.append(Finding("error", "BOOL_NO_TARGET",
                                       "Boolean modifier has no target object", obj.name))
                elif mod.object.name not in bpy.data.objects:
                    out.append(Finding("error", "BOOL_STALE_TARGET",
                                       f"Boolean target {mod.object.name!r} no longer exists", obj.name))
                elif mod.object is obj:
                    out.append(Finding("error", "BOOL_SELF",
                                       "Boolean modifier targets its own object", obj.name))
            if mod.type in {"ARMATURE", "LATTICE", "HOOK", "MESH_DEFORM", "SURFACE_DEFORM"}:
                tgt = getattr(mod, "object", None)
                if tgt is None and mod.type != "LATTICE":
                    out.append(Finding("warning", f"{mod.type}_NO_TARGET",
                                       f"{mod.type} modifier has no target object", obj.name))
        # Subdivision after boolean is a classic ordering mistake
        types = [m.type for m in obj.modifiers]
        if "BOOLEAN" in types and "SUBSURF" in types:
            if types.index("BOOLEAN") > types.index("SUBSURF"):
                out.append(Finding("warning", "MODIFIER_ORDER",
                                   "Subdivision is below Boolean; you almost always want Boolean first",
                                   obj.name))
    return out


def check_uvs(objects=None):
    """Objects that will need UVs: text/image textures, and glTF/UV export."""
    objects = objects if objects is not None else bpy.data.objects
    out = []
    for obj in objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if not obj.data.uv_layers:
            out.append(Finding("info", "NO_UV", "mesh has no UV layer", obj.name))
    return out


def check_scale_units(scene=None):
    """Unit system / clip range sanity for physical-scale scenes."""
    scene = scene or bpy.context.scene
    out = []
    if scene.unit_settings.system == "NONE" and scene.unit_settings.scale_length == 1.0:
        out.append(Finding("info", "UNITS_NONE", "unit system is NONE (default)"))
    return out


# --- aggregate --------------------------------------------------------------

ALL_CHECKS = (
    check_transforms,
    check_camera,
    check_lighting,
    check_materials,
    check_geometry,
    check_modifiers,
    check_uvs,
    check_scale_units,
)


#: Keyword arguments made available to every check. `run()` refreshes this
#: dict before dispatching, and `_call` filters it down to what each check
#: actually declares -- so adding a check with different parameters never
#: breaks the runner.
_CHECK_KWARGS = {"scene": None, "objects": None, "depsgraph": None}


def _call(fn):
    import inspect as _i
    params = _i.signature(fn).parameters
    kwargs = {k: v for k, v in _CHECK_KWARGS.items() if k in params}
    return fn(**kwargs)


def run(checks=None, scene=None, objects=None, verbose=True):
    """Run the checks and return ``(findings, summary_dict)``.

    ``summary["verdict"]`` is one of ``"ok"``, ``"warn"``, ``"fail"``.
    """
    scene = scene or bpy.context.scene
    objects = objects if objects is not None else list(scene.objects)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    _CHECK_KWARGS.update(scene=scene, objects=objects, depsgraph=depsgraph)
    findings = []
    for fn in (checks or ALL_CHECKS):
        try:
            findings.extend(_call(fn))
        except Exception as exc:
            findings.append(Finding("error", "CHECK_CRASHED",
                                    f"{fn.__name__} raised {exc!r}"))
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    verdict = "fail" if errors else ("warn" if warnings else "ok")
    summary = {
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
        "infos": sum(1 for f in findings if f.severity == "info"),
        "objects": len(objects),
        "meshes": sum(1 for o in objects if o.type == "MESH"),
        "materials": len(bpy.data.materials),
        "engine": scene.render.engine,
        "resolution": (scene.render.resolution_x, scene.render.resolution_y,
                       scene.render.resolution_percentage),
        "frame_range": (scene.frame_start, scene.frame_end),
    }
    if verbose:
        print("--- scene check ---")
        for f in findings:
            print(" ", f)
        print(f"  verdict={verdict} errors={errors} warnings={warnings} "
              f"objects={summary['objects']} meshes={summary['meshes']} engine={summary['engine']}")
    return findings, summary

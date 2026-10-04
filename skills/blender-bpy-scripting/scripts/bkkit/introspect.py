"""Safe introspection of bpy operators, node types and RNA properties.

Everything here exists because the obvious approach is wrong in a way that
bites automation: you cannot trust ``hasattr`` on bpy types, you cannot trust
enum introspection for dynamically registered items, and you cannot tell a
``CANCELLED`` operator apart from a successful one by the absence of an
exception.
"""

import bpy


# --- operators --------------------------------------------------------------

def op_exists(path):
    """True if the operator idname (e.g. ``"mesh.primitive_cube_add"``) exists.

    ``bpy.ops`` synthesises sub-objects on attribute access, so
    ``hasattr(bpy.ops.nope, "nope")`` is True even for an operator that does
    not exist. The only reliable test is to resolve the RNA.

    ``bpy.ops.<x>.<y>.poll()`` is not usable as an existence test because poll
    is context dependent and returns False in background mode.

    Do NOT assume a missing operator means a missing add-on. Verified on
    5.2.2 with ``--factory-startup``: ``op_exists("export_scene.gltf")`` is
    **True** -- glTF and FBX ship as bundled add-ons in ``addons_core`` and are
    enabled by default, they are not extensions you must turn on. Use
    :func:`op_check` / this function to ask what actually exists rather than
    recalling from memory.
    """
    parts = path.split(".")
    if len(parts) != 2:
        return False
    grp, name = parts
    try:
        group = getattr(bpy.ops, grp)
    except Exception:
        return False
    try:
        getattr(group, name).get_rna_type()
    except Exception:
        return False
    return True


def _is_flag_enum(prop):
    """True if this RNA ENUM property is a *flag* enum (takes a set of values).

    Verified on 5.2.2: ``bpy.ops.export_scene.fbx``'s ``object_types`` has
    ``is_enum_flag == True`` and must be given a ``set``:

    >>> bpy.ops.export_scene.fbx(filepath="x.fbx", object_types={"MESH", "EMPTY"})
    {'FINISHED'}
    >>> bpy.ops.export_scene.fbx(filepath="x.fbx", object_types=("MESH", "EMPTY"))
    TypeError: ... object_types expected a set, not a tuple

    Note that ENUM properties do **not** expose ``array_length`` / ``is_array``
    at all (unlike INT/FLOAT/BOOLEAN). Reading ``prop.array_length`` on an enum
    raises ``AttributeError``. That distinction matters: treating a flag enum
    like a scalar enum makes every valid value look invalid.
    """
    return bool(getattr(prop, "is_enum_flag", False))


def _enum_accepts(prop, value):
    """Return (ok, message) for assigning ``value`` to an ENUM property."""
    allowed = [e.identifier for e in prop.enum_items]
    if _is_flag_enum(prop):
        if isinstance(value, (set, frozenset)):
            members = set(value)
        elif isinstance(value, (list, tuple)):
            members = set(value)
            return False, (
                f"flag enum needs a set, not a {type(value).__name__} "
                f"(value={sorted(members)}); allowed={allowed}"
            )
        else:
            return False, (
                f"flag enum needs a set of identifiers, got {type(value).__name__} "
                f"({value!r}); allowed={allowed}"
            )
        bad = sorted(members - set(allowed))
        if bad:
            return False, f"unknown flag member(s) {bad}; allowed={allowed}"
        return True, None
    if value not in allowed:
        return False, f"{value!r} not in {allowed}"
    return True, None


def op_props(path):
    """Return the list of argument names accepted by an operator.

    Example::

        op_props("mesh.primitive_cube_add")
        # -> ['align','size','calc_uvs','enter_editmode','location','rotation','scale', ...]

    Returns None if the operator does not exist.
    """
    if not op_exists(path):
        return None
    grp, name = path.split(".")
    rna = getattr(getattr(bpy.ops, grp), name).get_rna_type()
    return [p.identifier for p in rna.properties if p.identifier != "rna_type"]


def op_defaults(path):
    """Return {arg: default_value} for an operator. None if it does not exist."""
    if not op_exists(path):
        return None
    grp, name = path.split(".")
    rna = getattr(getattr(bpy.ops, grp), name).get_rna_type()
    out = {}
    for p in rna.properties:
        if p.identifier == "rna_type":
            continue
        out[p.identifier] = getattr(p, "default", None)
    return out


def op_check(path, **kwargs):
    """Preflight an operator call without executing it.

    Returns a dict::

        {"ok": bool, "errors": [str], "warnings": [str]}

    Catches the three failure modes that waste an agent's whole run:
    the operator does not exist (missing/disabled add-on), a keyword argument
    does not exist, or a keyword value is not a member of the enum.

    Verified on 5.2.2 with ``--factory-startup``:
    ``op_check("export_scene.gltf", filepath="x.glb")`` -> ok. glTF and FBX
    ship as bundled add-ons in ``addons_core`` and are enabled by default.

    Enum arguments come in two shapes and they are checked differently:

    * **scalar enum** -- ``value`` must be one of the identifiers
    * **flag enum** (``prop.is_enum_flag``) -- ``value`` must be a ``set`` of
      identifiers. ENUM properties do not expose ``array_length``/``is_array``
      at all, so a flag enum silently mis-validates if treated as a scalar.
    """
    errors, warnings = [], []
    if not op_exists(path):
        errors.append(f"operator {path!r} does not exist in this session")
        return {"ok": False, "errors": errors, "warnings": warnings}

    available = op_props(path)
    for key in kwargs:
        if key not in available:
            close = [a for a in available if key in a]
            hint = f" (did you mean: {', '.join(close)}?)" if close else ""
            errors.append(f"{path!r} has no argument {key!r}{hint}")

    grp, name = path.split(".")
    rna = getattr(getattr(bpy.ops, grp), name).get_rna_type()
    by_id = {p.identifier: p for p in rna.properties}
    for key, value in kwargs.items():
        p = by_id.get(key)
        if p is None or p.type != "ENUM":
            continue
        ok, msg = _enum_accepts(p, value)
        if not ok:
            errors.append(f"{path!r} argument {key!r}={value!r} invalid: {msg}")

    if "EXEC_DEFAULT" not in available and "INVOKE_DEFAULT" not in available:
        warnings.append(f"{path!r} exposes no execution context key")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def call_op(path, **kwargs):
    """Call an operator and treat ``{'CANCELLED'}`` as a failure.

    ``bpy.ops.*`` returns a set. ``{'FINISHED'}`` means success,
    ``{'CANCELLED'}`` means the operator *ran but declined* -- no exception is
    raised, so a naive script sails on thinking it worked. This helper
    converts that into a RuntimeError.

    Returns the operator's return set.
    """
    check = op_check(path, **kwargs)
    if not check["ok"]:
        raise RuntimeError("; ".join(check["errors"]))
    grp, name = path.split(".")
    res = getattr(getattr(bpy.ops, grp), name)(**kwargs)
    if "FINISHED" not in res:
        raise RuntimeError(f"operator {path!r} returned {sorted(res)} instead of FINISHED")
    return res


# --- node types -------------------------------------------------------------

def node_idnames(prefix):
    """List every registered bpy node type whose class name starts with ``prefix``.

    Example::

        node_idnames("CompositorNode")
        # -> ['CompositorNodeAlphaOver', 'CompositorNodeBlur', ...]

    This is the reliable way to enumerate node types. ``bpy.types.ShaderNode``
    has no useful ``__subclasses__()`` because most nodes are registered
    through the RNA type system, not normal Python subclassing.
    """
    return sorted(n for n in dir(bpy.types) if n.startswith(prefix))


def node_exists(idname):
    """True if a node ``bl_idname`` is registered, e.g. ``"ShaderNodeTexNoise"``."""
    return hasattr(bpy.types, idname)


# --- node trees -------------------------------------------------------------

def socket_by_name(node, name, inputs=True):
    """Find a socket on a node by *name* or *identifier*.

    Identifiers are what you pass to Geometry Nodes modifier properties and
    what the ``.blend`` file stores; names are what you see in the UI and
    what localized labels match. Sockets whose name contains a socket
    identifier as a prefix get a suffixed name, e.g. ``"Value.001"``.

    Returns the socket or None.
    """
    coll = node.inputs if inputs else node.outputs
    if name in coll:
        return coll[name]
    for s in coll:
        if s.identifier == name or s.name == name or s.name.split(".")[0] == name:
            return s
    return None


def new_node(tree, idname, location=(0.0, 0.0), label=None, name=None):
    """Create a node by ``bl_idname`` and set its UI placement.

    Returns the node. Raises KeyError if ``idname`` is not registered.
    """
    if not node_exists(idname):
        raise KeyError(
            f"node type {idname!r} is not registered in this build. "
            f"Check with bkkit.introspect.node_exists()."
        )
    node = tree.nodes.new(idname)
    node.location = location
    if label:
        node.label = label
    if name:
        node.name = name
    return node


def clear_tree(tree):
    """Remove every node and link from a node tree."""
    tree.nodes.clear()


def set_input(node, name, value, inputs=True):
    """Set a socket value by name/identifier, tolerating missing sockets.

    Returns True on success, False if the socket is absent. Never raises --
    shaders change between Blender versions and a missing socket should not
    take down a render.

    Verified reason: Principled BSDF renamed ``Transmission`` ->
    ``Transmission Weight`` and split ``Emission`` into ``Emission Color`` +
    ``Emission Strength`` during the 4.x cycle, so hard-coded socket names
    written for older tutorials silently do nothing.
    """
    s = socket_by_name(node, name, inputs=inputs)
    if s is None:
        return False
    try:
        s.default_value = value
    except (TypeError, ValueError):
        try:
            s.default_value = (value,)
        except Exception:
            return False
    return True


# --- generic RNA helpers ----------------------------------------------------

def prop_info(thing, name):
    """Return a dict describing an RNA property, or None if absent.

    Keys: ``type``, ``is_readonly``, ``is_array``, ``length``, ``enum``,
    ``is_flag_enum``, ``default``, ``description``.

    ``is_array`` / ``length`` read ``array_length``, which **ENUM properties do
    not have** (verified on 5.2.2: ``AttributeError: 'EnumProperty' object has
    no attribute 'array_length'``). Use ``getattr(p, "array_length", 0)`` and
    report flag enums through ``is_flag_enum`` instead.
    """
    try:
        props = {p.identifier: p for p in thing.bl_rna.properties}
    except Exception:
        return None
    p = props.get(name)
    if p is None:
        return None
    length = getattr(p, "array_length", 0)
    info = {
        "type": p.type,
        "is_readonly": p.is_readonly,
        "is_array": length > 0,
        "length": length,
        "is_flag_enum": _is_flag_enum(p),
        "default": getattr(p, "default", None),
        "description": (p.description or "").strip(),
        "enum": None,
    }
    if p.type == "ENUM":
        info["enum"] = [e.identifier for e in p.enum_items]
    return info


def set_enum_safely(thing, name, value):
    """Assign an enum value, returning a helpful error instead of raising.

    ``TypeError: bpy_struct: item.attr = val: enum "X" not found in (...)``
    is a normal thing to hit when a Blender version renamed an enum member.
    """
    info = prop_info(thing, name)
    if info is None:
        return False, f"{name!r} is not an RNA property of {type(thing).__name__}"
    if info["enum"] and value not in info["enum"]:
        return False, f"{name}={value!r} not in {info['enum']}"
    setattr(thing, name, value)
    return True, None

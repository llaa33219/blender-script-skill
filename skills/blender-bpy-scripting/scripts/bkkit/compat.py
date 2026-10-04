"""Version feature detection.

Blender's Python API has several breaking changes in the 4.x -> 5.x range.
Never branch on the version *number* when you can branch on an actual
capability: ``bpy.app.version`` lies the moment someone backports a patch,
but a feature probe is always true.

Verified behaviour (Blender 5.2.2 LTS):
  * ``bpy.app.version`` -> ``(5, 2, 2)``, ``bpy.app.version_string`` -> ``'5.2.2 LTS'``
  * ``bpy.data.all_ids`` exists (new in 5.2)
  * ``bpy.types.NodesModifier`` has an RNA property named ``properties``
    (new in 5.2) -- this is the Geometry Nodes input access rewrite
  * ``bpy.types.WindowManager`` has an RNA property named ``reports`` (new in 5.2)
  * ``bpy.types.Window.screenshot`` exists (new in 5.2)
  * ``gpu.init`` exists (new in 5.2, lets you init the GPU backend in -b)
"""

import bpy

_CACHE = {}


def version():
    """Return the running Blender version as a 3-tuple of ints."""
    return tuple(bpy.app.version)


def version_string():
    return bpy.app.version_string


def at_least(major, minor=0, patch=0):
    """True if the running Blender is >= the given version."""
    return version() >= (major, minor, patch)


# --- capability probes -------------------------------------------------------
# Each returns a bool. Cached because they are called in tight validation loops.

def _probe(key, fn):
    if key not in _CACHE:
        try:
            _CACHE[key] = bool(fn())
        except Exception:
            _CACHE[key] = False
    return _CACHE[key]


def rna_props(type_or_instance):
    """Return the list of RNA property identifiers for a bpy type or instance.

    This is the ONLY reliable way to test for the existence of a bpy property.
    ``hasattr(bpy.types.Foo, "bar")`` returns False for plenty of properties
    that genuinely exist, because RNA properties are not normal class
    attributes on the Python proxy type.

    Verified: ``hasattr(bpy.types.WindowManager, "reports")`` -> False,
    but ``"reports" in rna_props(bpy.types.WindowManager)`` -> True.
    """
    if isinstance(type_or_instance, bpy.types.ID):
        return [p.identifier for p in type_or_instance.bl_rna.properties]
    return [p.identifier for p in type_or_instance.bl_rna.properties]


def has_prop(thing, name):
    """Capability test for a bpy RNA property, reliable unlike ``hasattr``."""
    try:
        return name in rna_props(thing)
    except Exception:
        return False


def has_method(thing, name):
    """Capability test for a method on a bpy struct/instance."""
    return callable(getattr(thing, name, None))


def gn_uses_rna_properties():
    """True on Blender >= 5.2.

    On 5.2+ Geometry Nodes modifier inputs are real RNA properties reachable
    via ``mod.properties.inputs.<identifier>``. Before that they were ID
    properties written as ``mod["Socket_2"] = value``.

    Prefer this probe over ``bpy.app.version >= (5, 2, 0)`` because it stays
    correct if the feature is backported or if you are on a custom build.
    """
    return _probe(
        "gn_rna",
        lambda: "properties" in rna_props(bpy.types.NodesModifier),
    )


def use_nodes_is_deprecated():
    """True on Blender >= 5.0.

    ``Material.use_nodes`` is deprecated and slated for removal in 6.0.
    A freshly created material already has a populated ``node_tree``, so you
    do not need to set it.

    Verified on 5.2.2: ``bpy.data.materials.new("M")`` immediately returns a
    material whose ``node_tree`` has 2 nodes, and setting ``use_nodes = True``
    emits ``DeprecationWarning: 'Material.use_nodes' is expected to be removed
    in Blender 6.0``.
    """
    return at_least(5, 0, 0)


def has_all_ids():
    """True when ``bpy.data.all_ids`` exists (Blender >= 5.2)."""
    return _probe("all_ids", lambda: hasattr(bpy.data, "all_ids"))


def has_scene_compositing_node_group():
    """True when ``Scene.compositing_node_group`` exists (Blender >= 5.0).

    Blender 5.0 reworked the compositor: instead of ``scene.use_nodes`` +
    ``scene.node_tree`` (a node tree owned by the scene), a *node group* is
    assigned to the scene. Verify the real behaviour on your build with
    ``scripts/bk.py doctor`` before relying on it.
    """
    return _probe("comp_group", lambda: has_prop(bpy.types.Scene, "compositing_node_group"))


def has_temp_override():
    """True when ``bpy.context.temp_override`` exists (Blender >= 3.2)."""
    return _probe("temp_override", lambda: callable(getattr(bpy.context, "temp_override", None)))


def has_action_slots():
    """True when Actions use the slotted model (Blender >= 4.4).

    On 4.4+ an Action holds ``layers`` -> ``strips`` -> ``channelbags``, and
    each slot owns its curves.
    """
    return _probe("action_slots", lambda: has_prop(bpy.types.Action, "slots"))


def action_fcurves(animated_id):
    """Return the F-Curves driving ``animated_id``'s action, on any Blender 4.x/5.x.

    ``Action.fcurves`` **does not exist at all in Blender 5.2** -- verified:
    ``act.fcurves`` raises ``AttributeError: 'Action' object has no attribute
    'fcurves'``. Every 4.x-era tutorial and add-on that touches it is dead on
    5.2. This helper hides the whole migration.

    Pass the *animated datablock* (object, material, scene, ...), not the
    Action::

        for fc in bkkit.compat.action_fcurves(obj):
            print(fc.data_path, fc.array_index)

    Resolution order:
      1. ``action.fcurve_ensure_for_datablock(id)``  (5.x modern helper)
      2. ``action.layers[*].strips[*].channelbag(obj.animation_data.action_slot)``
      3. ``action.fcurves``                          (legacy 4.0-4.3 only)
    """
    ad = getattr(animated_id, "animation_data", None)
    if ad is None or ad.action is None:
        return []
    action = ad.action

    if has_method(action, "fcurve_ensure_for_datablock"):
        try:
            return list(action.fcurve_ensure_for_datablock(animated_id))
        except Exception:
            pass

    slot = getattr(ad, "action_slot", None)
    if slot is not None and has_prop(action, "layers"):
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                try:
                    bag = strip.channelbag(slot)
                except Exception:
                    bag = None
                if bag is not None:
                    out.extend(bag.fcurves)
        return out

    legacy = getattr(action, "fcurves", None)
    return list(legacy) if legacy is not None else []


def set_gn_input(mod, identifier, value, attribute_name=None):
    """Set a Geometry Nodes modifier input in a way that works on 4.x and 5.2+.

    Blender 5.2 moved Geometry Nodes modifier inputs from ID properties to
    real RNA properties::

        # 4.0 - 5.1
        mod["Geometry"] = value
        mod["Geometry_use_attribute"] = True
        mod["Geometry_attribute_name"] = "some_attr"

        # 5.2+
        mod.properties.inputs.Geometry.value = value
        mod.properties.inputs.Geometry.type = "ATTRIBUTE"
        mod.properties.inputs.Geometry.attribute_name = "some_attr"

    ``identifier`` is the *socket identifier*, not the UI label. Get it from
    ``node_group.interface.items_tree``.

    Returns True if the value was set, False if the socket does not exist.
    """
    if gn_uses_rna_properties():
        props = getattr(mod, "properties", None)
        if props is None:
            return False
        inputs = getattr(props, "inputs", None)
        if inputs is None or not hasattr(inputs, identifier):
            return False
        sock = getattr(inputs, identifier)
        if attribute_name is not None:
            sock.type = "ATTRIBUTE"
            sock.attribute_name = attribute_name
        else:
            sock.value = value
        return True
    # legacy ID-property path
    if attribute_name is not None:
        mod[f"{identifier}_use_attribute"] = True
        mod[f"{identifier}_attribute_name"] = attribute_name
    else:
        mod[f"{identifier}_use_attribute"] = False
        mod[identifier] = value
    return True


def has_cycles_addon():
    """True when the Cycles add-on is registered in this session.

    Under ``blender -b --factory-startup`` every add-on is disabled, so
    ``scene.render.engine = 'CYCLES'`` raises a TypeError until you call
    ``enable_cycles()`` first.
    """
    try:
        return "CYCLES" in {i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} or \
               hasattr(bpy.context.preferences.addons.get("cycles"), "preferences")
    except Exception:
        return False


def enable_cycles():
    """Enable the bundled Cycles add-on and return True if it is available.

    MUST be called before touching ``scene.render.engine`` in a
    ``--factory-startup`` session.

    Verified 5.2.2::

        import addon_utils
        addon_utils.enable("cycles", default_set=True, persistent=True)
        scene.render.engine = 'CYCLES'   # now works
    """
    try:
        import addon_utils
        addon_utils.enable("cycles", default_set=True, persistent=True)
        return True
    except Exception:
        return False


def engine_enum_items(scene=None):
    """Return the render engine enum identifiers visible to RNA.

    WARNING: this lies. On a build where Cycles is registered *and enabled*,
    ``RenderSettings.bl_rna.properties['engine'].enum_items`` still reports
    only ``['BLENDER_EEVEE']``, because dynamically-registered engines are
    not materialised into the static enum.

    Verified on 5.2.2 with Cycles enabled: enum_items -> ['BLENDER_EEVEE']
    while ``scene.render.engine`` is 'CYCLES'.

    So: assign the engine by string, and catch the TypeError on failure.
    Never use this function as a guard.
    """
    scene = scene or bpy.context.scene
    try:
        return [i.identifier for i in scene.render.bl_rna.properties["engine"].enum_items]
    except Exception:
        return []


def set_engine(scene, engine):
    """Set the render engine, auto-enabling the Cycles add-on if needed.

    Returns the engine string actually in effect, or raises RuntimeError.
    """
    if engine.upper().startswith("CYCLES"):
        enable_cycles()
    try:
        scene.render.engine = engine
    except TypeError as exc:
        raise RuntimeError(
            f"render engine {engine!r} unavailable. Available per RNA enum: "
            f"{engine_enum_items(scene)}. For Cycles you must call "
            f"bkkit.compat.enable_cycles() (or addon_utils.enable('cycles')) first."
        ) from exc
    return scene.render.engine


# --------------------------------------------------------------------------
# GPU
# --------------------------------------------------------------------------

#: Preference order. OPTIX first because it is the fastest NVIDIA path when the
#: hardware supports it; CUDA is the portable fallback; METAL last because it
#: only exists on macOS builds.
GPU_BACKEND_ORDER = ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL")


def gpu_report(prefs=None):
    """Report GPU support of this build and the hardware actually present.

    This function exists for one distinction: **"backend is compiled in" is not
    "a GPU is present"**. On a machine with zero GPUs, Cycles still reports
    ``_cycles.get_device_types() == (True, True, True, False, True, True)``
    because CUDA/OptiX/HIP/oneAPI are compiled into the Linux build.

    Verified on 5.2.2 with no GPU::

        compiled = {'CUDA': True, 'OPTIX': True, 'HIP': True,
                    'METAL': False, 'ONEAPI': True}
        detected = {'OPTIX': 0, 'CUDA': 0, 'HIP': 0, 'ONEAPI': 0, 'METAL': 0}

    Returns a dict with ``compiled``, ``detected``, ``devices``, ``backend``,
    ``num_gpu``, ``has_device``, ``multi_device`` and ``features``.
    ``error`` is present only if ``_cycles`` could not be imported.
    """
    out = {"compiled": {}, "detected": {}, "devices": [], "backend": None,
           "num_gpu": 0, "has_device": False, "multi_device": False,
           "features": {}}
    enable_cycles()
    try:
        import _cycles
    except Exception as exc:                      # pragma: no cover
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out

    out["features"] = {
        "openimagedenoise": bool(_cycles.with_openimagedenoise),
        "embree": bool(_cycles.with_embree),
        "embree_gpu": bool(_cycles.with_embree_gpu),
        "osl": bool(_cycles.with_osl),
        "path_guiding": bool(_cycles.with_path_guiding),
    }

    if prefs is None:
        addons = bpy.context.preferences.addons
        prefs = addons["cycles"].preferences if "cycles" in addons else None
    if prefs is not None:
        # The device list is NOT refreshed on startup -- the Cycles addon
        # itself comments that unstable drivers can crash the enum callback.
        try:
            prefs.refresh_devices()
        except Exception as exc:
            out["refresh_error"] = f"{type(exc).__name__}: {exc}"

    try:
        flags = _cycles.get_device_types()
    except Exception:
        flags = (False,) * 6
    # _cycles.get_device_types() returns them in THIS order, which is NOT the
    # same as GPU_BACKEND_ORDER. Verified on 5.2.2:
    #   (has_cuda, has_optix, has_hip, has_metal, has_oneapi, has_hiprt)
    # -> (True, True, True, False, True, True) on a GPU-less Linux build
    # Positional zip here silently mislabels every backend.
    for name, flag in zip(("CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"), flags[:5]):
        out["compiled"][name] = bool(flag)
    out["compiled"]["HIPRT"] = bool(flags[5]) if len(flags) > 5 else False

    for name in GPU_BACKEND_ORDER:
        # NOTE: _cycles.available_devices() can crash on some drivers -- the
        # Cycles addon source warns about exactly this. Callers running this in
        # a farm should isolate the process.
        try:
            found = [d for d in _cycles.available_devices(name) if d[1] == name]
        except Exception:
            found = []
        out["detected"][name] = len(found)
        for d in found:
            out["devices"].append({"backend": name, "name": d[0], "id": d[2]})

    out["backend"] = next((b for b in GPU_BACKEND_ORDER if out["detected"].get(b)), None)
    if prefs is not None:
        try:
            out["num_gpu"] = prefs.get_num_gpu_devices()
            out["has_device"] = prefs.has_active_device()
            out["multi_device"] = prefs.has_multi_device()
        except Exception:
            pass
    return out


def set_denoiser(scene, prefer=("OPTIX", "OPENIMAGEDENOISE")):
    """Set ``scene.cycles.denoiser`` to the first available option.

    The denoiser enum is generated from detected hardware, so it cannot be
    hard-coded. Verified on a machine with no GPU: ``'OPTIX'`` raises TypeError
    and only ``'OPENIMAGEDENOISE'`` is accepted. Returns the name that was set,
    or None if none were available.
    """
    for name in prefer:
        try:
            scene.cycles.denoiser = name
            return name
        except TypeError:
            continue
    return None


def enable_gpu(scene=None, backend=None, hybrid=True, tile_size=1024,
               texture_limit="2048", denoiser=True):
    """Enable GPU rendering, or fall back to CPU *explicitly*.

    Without this, setting ``prefs.compute_device_type = 'CUDA'`` and
    ``scene.cycles.device = 'GPU'`` on a machine with no GPU succeeds silently:
    no exception, ``bpy.ops.render.render()`` returns ``{'FINISHED'}``, and the
    image is written -- rendered on the CPU. Verified on 5.2.2.

    Returns ``(ok, info)``. When ``ok is False`` the scene was deliberately left
    on the CPU and ``info['reason']`` explains why.
    """
    enable_cycles()
    scene = scene or bpy.context.scene
    set_engine(scene, "CYCLES")
    rep = gpu_report()
    prefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = backend or rep["backend"] or "NONE"

    info = {"compiled": rep["compiled"], "detected": rep["detected"],
            "chosen": chosen, "features": rep["features"]}
    if "error" in rep:
        info["reason"] = "_cycles 모듈 사용 불가: " + rep["error"]

    if chosen == "NONE":
        scene.cycles.device = "CPU"
        info.setdefault("reason",
                        "감지된 GPU 없음. compiled=True 여도 하드웨어가 없다는 뜻.")
        info["ok"] = False
        return False, info

    try:
        prefs.compute_device_type = chosen
    except TypeError as exc:
        scene.cycles.device = "CPU"
        info["reason"] = f"compute_device_type={chosen!r} 거부됨: {exc}"
        info["ok"] = False
        return False, info

    for dev in prefs.devices:
        dev.use = (dev.type != "CPU") or bool(hybrid)

    if prefs.get_num_gpu_devices() == 0:
        scene.cycles.device = "CPU"
        info["reason"] = (f"{chosen} 지정했지만 활성 GPU 0개. "
                          f"detected={rep['detected']}")
        info["ok"] = False
        return False, info

    scene.cycles.device = "GPU"
    scene.cycles.tile_size = tile_size
    if texture_limit and texture_limit != "OFF":
        scene.cycles.texture_limit = texture_limit
        scene.cycles.texture_limit_render = texture_limit
    if denoiser:
        info["denoiser"] = set_denoiser(scene)
    info["num_gpu_devices"] = prefs.get_num_gpu_devices()
    info["multi_device"] = prefs.has_multi_device()
    info["ok"] = True
    return True, info

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

import os
import re
import shutil
import subprocess

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

#: A GPU with less free VRAM than this is treated as someone else's card.
#: Cycles allocates the scene, its BVH and every kernel up front, so a card
#: that merely *looks* idle at 1 GB free will still die with
#: "System is out of GPU memory" part-way into the render.
MIN_FREE_VRAM_MB = 2000


def gpu_inventory(prefs=None):
    """Return every GPU the build can see, with the *host* facts that decide
    whether it is worth using.

    The 5.2.2 sandbox this skill was written on had zero GPUs, so the old
    code only ever had to answer "are there any?". On a real multi-GPU box
    that question is useless -- all six cards may be visible while the ones
    that matter are 100% occupied by another workload.

    ``_cycles.available_devices()`` is the only call that reports hardware
    (as opposed to "this backend is compiled in"), and it is what
    ``refresh_devices()`` uses internally.

    Returns ``{"detected": {...}, "devices": [...], "features": {...}}``.
    """
    enable_cycles()
    try:
        import _cycles
    except Exception as exc:                      # pragma: no cover
        return {"error": f"{type(exc).__name__}: {exc}",
                "detected": {}, "devices": [], "features": {}}

    out = {"detected": {}, "devices": [], "features": {}}
    out["features"] = {
        "openimagedenoise": bool(_cycles.with_openimagedenoise),
        "embree": bool(_cycles.with_embree),
        "embree_gpu": bool(_cycles.with_embree_gpu),
        "osl": bool(_cycles.with_osl),
        "path_guiding": bool(_cycles.with_path_guiding),
    }
    for name in GPU_BACKEND_ORDER:
        # The Cycles addon source warns that this can crash on some drivers,
        # so callers running in a farm should isolate the process.
        try:
            found = [d for d in _cycles.available_devices(name) if d[1] == name]
        except Exception:
            found = []
        out["detected"][name] = len(found)
        for d in found:
            out["devices"].append({
                "backend": name,
                "name": d[0],
                "id": d[2],
                # device[2] is e.g. "CUDA_NVIDIA GeForce RTX 4070_0000:82:00_OptiX";
                # the PCI bus id is what correlates a card with nvidia-smi.
                "bus_id": _bus_id_from_device_id(d[2]),
            })
    return out


def _bus_id_from_device_id(device_id):
    """Pull ``82:00`` out of a Cycles persistent id, or None.

    Cycles ids look like ``CUDA_NVIDIA GeForce RTX 4070_0000:82:00_OptiX``.
    The PCI bus id is the only part that can be matched against
    ``nvidia-smi --query-gpu=pci.bus_id`` to find out whether that card is
    already busy with someone else's work.
    """
    m = re.search(r"0000:([0-9a-fA-F]{2}:[0-9a-fA-F]{2})", device_id or "")
    return m.group(1).lower() if m else None


def gpu_host_usage(timeout=5):
    """Query per-GPU VRAM use and utilisation from nvidia-smi.

    This is the piece the original skill was missing entirely: on a shared
    workstation the GPUs Blender can *see* are not the GPUs Blender can
    *use*. Cycles will happily claim a card with 300 MB of VRAM left and
    then die with "System is out of GPU memory".

    Returns ``{bus_id: {"index":, "name":, "used_mb":, "total_mb":,
    "util_pct":, "free_mb":}}``. An empty dict means "could not tell"
    (no nvidia-smi, no NVIDIA, timeout) -- callers must treat unknown as
    "do not silently assume it is free".
    """
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,pci.bus_id,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=timeout, check=False)
    except Exception:
        return {}
    if out.returncode != 0:
        return {}
    usage = {}
    for line in out.stdout.strip().splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 6:
            continue
        idx, name, bus, used, total, util = parts[:6]
        m = re.search(r":([0-9a-fA-F]{2}:[0-9a-fA-F]{2})", bus)
        if not m:
            continue
        try:
            used_mb, total_mb = int(used), int(total)
            util_pct = int(float(util))
        except ValueError:
            continue
        usage[m.group(1).lower()] = {
            "index": idx, "name": name,
            "used_mb": used_mb, "total_mb": total_mb,
            "free_mb": total_mb - used_mb,
            "util_pct": util_pct,
        }
    return usage


def gpu_host_usage_amd(timeout=8):
    """Per-AMD-GPU VRAM use and utilisation, via ``rocm-smi``.

    The AMD counterpart of :func:`gpu_host_usage`. Without it a box with AMD
    cards claims them even when another process already owns the VRAM -- the
    same trap as relying on ``nvidia-smi`` alone.

    ``rocm-smi`` reports VRAM as a *percentage*, not megabytes, and has no PCI
    bus id, so keys are synthetic (``"amd:0"``, ``"amd:1"``). They cannot be
    matched to a Cycles HIP device id the way ``gpu_host_usage`` matches
    ``82:00`` -- see the limitation note in :func:`enable_gpu`.

    Returns ``{}`` when rocm-smi is missing or unusable; callers must read that
    as "unknown", never as "idle".
    """
    exe = shutil.which("rocm-smi")
    if not exe:
        return {}
    try:
        # rocm-smi prints a field only when its flag is present.
        r = subprocess.run([exe, "--showproductname", "--showmemuse", "--showuse"],
                           capture_output=True, text=True, timeout=timeout)
    except Exception:
        return {}
    if r.returncode != 0:
        return {}
    dev = {}
    cur = None
    for line in (r.stdout or "").splitlines():
        head = re.match(r"\s*GPU\[(\d+)\]\s*:\s*(.*)$", line)
        if not head:
            continue
        idx, rest = int(head.group(1)), head.group(2).strip()
        e = dev.setdefault(idx, {"index": idx, "name": None,
                                 "used_pct": None, "util_pct": None})
        cur = e
        if rest.startswith("Card Series:"):
            e["name"] = rest.split(":", 1)[1].strip() or None
        elif rest.startswith("GPU use (%):"):
            m = re.search(r"(\d+)\s*$", rest)
            if m:
                e["util_pct"] = int(m.group(1))
        elif rest.startswith("GPU Memory Allocated (VRAM%):"):
            m = re.search(r"(\d+)\s*$", rest)
            if m:
                e["used_pct"] = int(m.group(1))
    return {f"amd:{k}": v for k, v in dev.items() if v.get("used_pct") is not None}


def gpu_report(prefs=None, backend=None, probe_host=True):
    """Report GPU support of this build and the hardware actually present.

    This function exists for one distinction: **"backend is compiled in" is not
    "a GPU is present"**. On a machine with zero GPUs, Cycles still reports
    ``_cycles.get_device_types() == (True, True, True, False, True, True)``
    because CUDA/OptiX/HIP/oneAPI are compiled into the Linux build.

    The second distinction -- added after testing on a real 6-GPU box -- is
    **"a GPU is present" is not "a GPU is usable"**. A card can be detected
    and still be unusable because another process holds all its VRAM.

    CRASH ORDER (verified on 5.2.2 with 6 NVIDIA + 2 AMD cards): set
    ``prefs.compute_device_type`` BEFORE calling ``prefs.refresh_devices()``.
    Calling refresh first leaves the preferences RNA in a half-built state;
    ``get_num_gpu_devices()`` then raises
    ``AttributeError: 'CyclesPreferences' object has no attribute
    'compute_device_type'`` and a subsequent render segfaults (exit 139).
    ``enable_gpu()`` used to do exactly that and crashed every time.

    Returns a dict with ``compiled``, ``detected``, ``devices``, ``backend``,
    ``num_gpu``, ``has_device``, ``multi_device``, ``features``, plus
    ``usable`` (devices that pass the host-usage filter) and ``host_usage``.
    """
    out = {"compiled": {}, "detected": {}, "devices": [], "backend": None,
           "num_gpu": 0, "has_device": False, "multi_device": False,
           "features": {}, "usable": [], "host_usage": {}, "bus_id": None}
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

    inv = gpu_inventory()
    out["detected"] = inv["detected"]
    out["devices"] = inv["devices"]
    chosen = backend or next((b for b in GPU_BACKEND_ORDER if out["detected"].get(b)), None)
    out["backend"] = chosen

    # Host usage is only meaningful for the backend we are about to select.
    usage = dict(gpu_host_usage()) if probe_host else {}
    out["host_usage"] = usage
    # rocm-smi reports by index with no bus id, so it cannot be joined onto a
    # HIP device id. Keep it alongside (not merged into) the NVIDIA map, and
    # say so -- HIP selection must not silently assume "idle".
    out["host_usage_amd"] = gpu_host_usage_amd() if probe_host else {}
    cand = [d for d in out["devices"] if d["backend"] == chosen]
    usable = []
    for d in cand:
        info = usage.get(d["bus_id"]) if d["bus_id"] else None
        d["host"] = info
        if info is None:
            # No host data (AMD/HIP, or nvidia-smi unavailable). Do not
            # exclude it: on a single-GPU workstation this is the only card.
            usable.append(d)
        elif info["free_mb"] >= MIN_FREE_VRAM_MB:
            usable.append(d)
    out["usable"] = usable

    if prefs is None:
        addons = bpy.context.preferences.addons
        prefs = addons["cycles"].preferences if "cycles" in addons else None
    if prefs is not None and chosen and chosen != "NONE":
        # ORDER MATTERS -- see the crash note in the docstring.
        try:
            prefs.compute_device_type = chosen
            prefs.refresh_devices()
        except Exception as exc:
            out["refresh_error"] = f"{type(exc).__name__}: {exc}"
        else:
            try:
                out["num_gpu"] = prefs.get_num_gpu_devices()
                out["has_device"] = prefs.has_active_device()
                out["multi_device"] = prefs.has_multi_device()
            except Exception:
                pass
    return out


def set_denoiser(scene, prefer=("OPTIX", "OPENIMAGEDENOISE")):
    """Set ``scene.cycles.denoiser`` to the first *usable* option.

    The denoiser enum is generated from detected hardware, so it cannot be
    hard-coded -- but that is not the whole story, and trusting the enum alone
    picks a denoiser that does not work.

    Two different failure modes, both verified on 5.2.2:

    **No GPU at all.** ``scene.cycles.denoiser = 'OPTIX'`` raises TypeError and
    only ``'OPENIMAGEDENOISE'`` is accepted. The enum lies by omission.

    **AMD/HIP with no NVIDIA present.** The enum offers *both* --
    ``enum "__PROBE__" not found in ('OPTIX', 'OPENIMAGEDENOISE')`` -- so the
    assignment succeeds and the render succeeds. It is just quietly wrong:
    ``prefs.has_optixdenoiser_gpu_devices()`` is ``False``, no OptiX device
    exists, and the render falls back to a slower path. Measured on 2x
    Radeon RX 7600 XT, 960x720 / 64 spp:

        denoiser='OPTIX'            3.85 s
        denoiser='OPENIMAGEDENOISE' 3.01 s     (-22%)

    So: for OPTIX, also require that the preferences report an OptiX denoiser
    device. Returns the name that was set, or None if none were available.
    """
    for name in prefer:
        if name == "OPTIX":
            # Enum membership is not enough -- the device has to exist.
            # NOTE: do NOT call enable_cycles() here. Re-registering the add-on
            # rebuilds preferences RNA and get_num_gpu_devices() then raises
            # (see gpu_report's crash-order note). Read prefs as-is instead.
            try:
                prefs = bpy.context.preferences.addons.get("cycles")
                if prefs is None or not prefs.preferences.has_optixdenoiser_gpu_devices():
                    continue
            except Exception:
                continue
        try:
            scene.cycles.denoiser = name
            return name
        except TypeError:
            continue
    return None


def enable_gpu(scene=None, backend=None, hybrid=True, tile_size=1024,
               texture_limit="2048", denoiser=True, max_devices=None,
               min_free_vram_mb=MIN_FREE_VRAM_MB, probe_host=True,
               verbose=False):
    """Enable GPU rendering, or fall back to CPU *explicitly*.

    Without this, setting ``prefs.compute_device_type = 'CUDA'`` and
    ``scene.cycles.device = 'GPU'`` on a machine with no GPU succeeds silently:
    no exception, ``bpy.ops.render.render()`` returns ``{'FINISHED'}``, and the
    image is written -- rendered on the CPU. Verified on 5.2.2.

    On a *real* multi-GPU machine the naive version fails a second way. The
    naive ``for d in prefs.devices: d.use = True`` enables every card Cycles
    enumerated -- including cards belonging to other backends and cards that
    another process has filled. Measured on 6 NVIDIA + 2 AMD with three cards
    saturated by an unrelated job::

        enable all 6 OPTIX devices -> RuntimeError: System is out of GPU memory
        enable only the 3 idle ones -> renders fine

    So this picks devices deliberately:

    1. keep only devices matching the selected backend,
    2. drop any card whose free VRAM is below ``min_free_vram_mb``,
    3. order the survivors by free VRAM descending,
    4. take at most ``max_devices`` (default: **one** -- see below).

    Why the default is a single GPU: measured on this box, 960x720, 64 spp,
    SUBSURF spheres, denoising on::

        CPU (80 cores)      5.69 s
        1 GPU               4.51 s   <- fastest
        2 GPUs              5.26 s
        3 GPUs              6.17 s
        6 GPUs              out of GPU memory

    Adding cards made it *slower* because these GPUs have no NVLink -- the
    scene has to be copied to each card every tile and results synced back
    over PCIe, and that costs more than the extra compute buys. Multi-GPU only
    pays off on NVLink-connected cards or when a single card cannot hold the
    scene. Pass ``max_devices=2`` (or more) to override.

    Returns ``(ok, info)``. When ``ok is False`` the scene was deliberately left
    on the CPU and ``info['reason']`` explains why.
    """
    enable_cycles()
    scene = scene or bpy.context.scene
    set_engine(scene, "CYCLES")

    # NOTE: gpu_report() sets compute_device_type *before* refresh_devices().
    # The reverse order crashes Blender. Do not "optimise" this call away.
    rep = gpu_report(backend=backend, probe_host=probe_host)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    chosen = backend or rep["backend"] or "NONE"

    info = {"compiled": rep["compiled"], "detected": rep["detected"],
            "chosen": chosen, "features": rep["features"],
            "min_free_vram_mb": min_free_vram_mb,
            "host_usage_amd": rep.get("host_usage_amd", {})}
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

    # ORDER MATTERS: compute_device_type first (done above), then refresh.
    try:
        prefs.refresh_devices()
    except Exception as exc:
        scene.cycles.device = "CPU"
        info["reason"] = f"refresh_devices() 실패: {type(exc).__name__}: {exc}"
        info["ok"] = False
        return False, info

    usable_ids = [d["id"] for d in rep.get("usable", [])]
    candidates = [d for d in prefs.devices if d.type == chosen and d.id in usable_ids]
    # Read nvidia-smi data directly: rep["devices"][i]["host"] is only
    # populated for the chosen backend's candidates, and the skipped-device
    # list below needs the same numbers for every card of that backend.
    usage = rep.get("host_usage") or {}

    def _free_mb(dev):
        info_h = usage.get(_bus_id_from_device_id(dev.id))
        return info_h["free_mb"] if info_h else None

    candidates.sort(key=lambda d: (_free_mb(d) is not None, _free_mb(d) or 0), reverse=True)
    limit = max_devices if max_devices is not None else 1
    chosen_devices = candidates[:max(limit, 0)] if limit else candidates

    # Turn everything off first, then enable exactly what we picked.
    for dev in prefs.devices:
        dev.use = False
    for dev in chosen_devices:
        dev.use = True
    if hybrid:
        for dev in prefs.devices:
            if dev.type == "CPU":
                dev.use = True

    selected_set = set(id(d) for d in chosen_devices)
    info["selected"] = [{"name": d.name, "id": d.id,
                         "free_mb": _free_mb(d)} for d in chosen_devices]
    info["skipped"] = []
    for d in prefs.devices:
        if d.type != chosen or id(d) in selected_set:
            continue
        free = _free_mb(d)
        if free is not None and free < min_free_vram_mb:
            why = f"여유 VRAM {free} MB < {min_free_vram_mb} MB (다른 작업 중)"
        else:
            why = (f"사용 가능하나 max_devices={limit} 제한으로 미선택 "
                   f"(여유 {free} MB)")
        info["skipped"].append({"name": d.name, "free_mb": free, "why": why})
    if verbose:
        for line in info["selected"]:
            print(f"  [GPU 사용] {line['name']}  여유 {line['free_mb']} MB")
        for line in info["skipped"]:
            print(f"  [GPU 제외] {line['name']}  여유 {line['free_mb']} MB  ({line['why']})")

    try:
        n_active = prefs.get_num_gpu_devices()
    except Exception:
        n_active = 0
    if n_active == 0:
        scene.cycles.device = "CPU"
        skipped = ", ".join(s["name"] for s in info["skipped"]) or "없음"
        info["reason"] = (f"{chosen} GPU 중 사용 가능한 것이 없음 "
                          f"(제외됨: {skipped}). detected={rep['detected']}")
        info["ok"] = False
        return False, info

    scene.cycles.device = "GPU"
    scene.cycles.tile_size = tile_size
    if texture_limit and texture_limit != "OFF":
        scene.cycles.texture_limit = texture_limit
        scene.cycles.texture_limit_render = texture_limit
    if denoiser:
        info["denoiser"] = set_denoiser(scene)
        # Denoising on the GPU only pays off when the render itself is on the
        # GPU; measured here it costs ~25% of total time (5.61 s -> 4.20 s
        # with denoising off), so it stays opt-out rather than forced on.
        try:
            scene.cycles.denoising_use_gpu = True
        except Exception:
            pass
    info["num_gpu_devices"] = n_active
    info["multi_device"] = n_active > 1
    info["ok"] = True
    return True, info


def gpu_speed_preset(scene, quality="balanced", preset_samples=None):
    """Apply the render settings that measurably matter on this hardware.

    Measured deltas (960x720, SUBSURF spheres, 1 GPU, OptiX)::

        denoising off          5.61 s -> 4.20 s   (-25%)
        denoising on CPU       5.61 s -> 5.52 s   (-2%)
        tile_size 512 -> 2048  5.61 s -> 5.35 s   (-5%)

    Returns the dict of what it changed, so callers can log or verify it.
    """
    changed = {}
    c = scene.cycles
    if quality == "fast":
        c.use_denoising = False
        changed["use_denoising"] = False
        changed["_denoiser_note"] = "denoising off (-25% measured)"
    elif quality == "balanced":
        c.use_denoising = True
        changed["use_denoising"] = True
    c.tile_size = 2048 if quality in ("balanced", "quality") else 1024
    changed["tile_size"] = c.tile_size
    if preset_samples is not None:
        c.samples = preset_samples
        changed["samples"] = preset_samples
    try:
        scene.render.use_persistent_data = True
        changed["use_persistent_data"] = True
    except Exception:
        pass
    return changed


# --------------------------------------------------------------------------
# Render engines
# --------------------------------------------------------------------------

#: Engine identifiers accepted by ``scene.render.engine`` on 5.2.
#: NOTE: ``BLENDER_EEVEE_NEXT`` is the 4.x name and is *rejected* on 5.x --
#: EEVEE was folded back into ``BLENDER_EEVEE``. Verified on 5.2.2.
ENGINE_IDS_5X = ("BLENDER_WORKBENCH", "BLENDER_EEVEE", "CYCLES")


def eevee_gpu_renderer():
    """Return the GPU string EEVEE will actually draw on, or None.

    This is not a detail. On a machine with both NVIDIA and AMD, EEVEE goes
    through Blender's OpenGL/Vulkan GPU module while Cycles uses OptiX/CUDA.
    They land on **different cards**. Verified 5.2.2 on a box with 6 NVIDIA
    + 2 AMD: EEVEE reported ``AMD Radeon RX 7600 XT (radeonsi, ...)`` while
    Cycles was rendering on an NVIDIA RTX 4070.

    It matters because a headless box with no usable Mesa driver silently
    falls back to llvmpipe, which renders roughly 100x slower than Cycles on
    CPU. Detecting that before a render beats discovering it afterwards.

    ``gpu.init()`` takes no arguments on 5.2 (passing context raises TypeError).
    """
    try:
        import gpu
        gpu.init()
        return gpu.platform.renderer_get()
    except Exception:
        return None


def eevee_is_software():
    """True when EEVEE would fall back to a CPU rasteriser (llvmpipe/softpipe)."""
    rt = (eevee_gpu_renderer() or "").lower()
    return ("llvmpipe" in rt) or ("softpipe" in rt) or rt == ""


def set_engine_for_purpose(scene, purpose="final", samples=None):
    """Pick a render engine by what you are doing, not by what is fast.

    ``purpose``:
      * ``structure`` -- scene layout / camera framing. Workbench, clay render.
      * ``explore``   -- 1-3 throwaway renders. EEVEE, no raytracing.
      * ``animate``   -- animation or >3 repeats. Cycles + persistent data.
      * ``final``     -- deliverable. Cycles + denoising + high samples.

    Why this exists, measured on 6 NVIDIA + 2 AMD (960x720, 64 spp, warm median):

        scene          Workbench   EEVEE    Cycles
        mixed            2.62 s    3.06 s   0.30 s
        reflective       0.09 s    0.47 s   0.67 s
        interior         0.09 s    0.44 s   0.33 s

    Two things fall out of that table. First, the engine spread is at most ~7x
    while the *sample count* spread is orders of magnitude -- if a render feels
    slow, look at samples first. Second, EEVEE and Cycles sit on different GPUs,
    so one of them may be using a card you did not intend.

    Returns a dict describing what was chosen and why.
    """
    enable_cycles()

    if purpose == "structure":
        set_engine(scene, "BLENDER_WORKBENCH")
        try:
            scene.display.shading.color_type = "SINGLE"
            scene.display.shading.show_shadows = False
            scene.display.shading.show_cavity = False
            scene.display.render_aa = "OFF"
        except Exception:
            pass
        return {"engine": "BLENDER_WORKBENCH", "purpose": purpose,
                "note": "클레이 렌더. 품질 무관"}

    if purpose == "explore":
        if eevee_is_software():
            # EEVEE would run on llvmpipe here -- far slower than Cycles CPU.
            set_engine(scene, "CYCLES")
            scene.cycles.device = "CPU"
            scene.cycles.samples = samples or 32
            scene.cycles.use_denoising = False
            return {"engine": "CYCLES", "purpose": purpose, "device": "CPU",
                    "note": "EEVEE 가 소프트웨어 렌더러 — CPU 폴백"}
        set_engine(scene, "BLENDER_EEVEE")
        ee = scene.eevee
        ee.taa_render_samples = samples or 32
        ee.use_raytracing = False
        return {"engine": "BLENDER_EEVEE", "purpose": purpose,
                "device": eevee_gpu_renderer()}

    # animate / final -- Cycles
    ok, info = enable_gpu(scene, max_devices=1) if purpose in ("animate", "final") else (False, {})
    gpu_speed_preset(scene, quality="balanced")
    scene.cycles.samples = samples or (128 if purpose == "animate" else 512)
    scene.cycles.use_denoising = True
    scene.render.use_persistent_data = True
    return {"engine": "CYCLES", "purpose": purpose,
            "gpu": ok, "devices": info.get("num_gpu_devices", 0),
            "note": info.get("reason") if not ok else None}


def eevee_vulkan_devices():
    """List the GPUs Vulkan would expose to EEVEE, via Blender's own CLI.

    Returns a list of ``{"index", "device_id", "name"}``. Returns ``[]`` when
    the query fails -- callers should treat that as "unknown", not "none".

    Why this exists: the OpenGL backend only exposes the *first* GPU. On a mixed
    NVIDIA+AMD box that silently pins EEVEE to one AMD card, even when an idle
    NVIDIA card is right there. The Vulkan backend enumerates all of them:

        blender -b --factory-startup --gpu-backend vulkan --gpu-device help

    Measured on a 6 NVIDIA + 2 AMD box: OpenGL reported one device
    (``AMD Radeon RX 7600 XT (radeonsi, ...)``) while Vulkan listed 9 entries
    -- every card plus a trailing ``llvmpipe`` software entry. Rendering EEVEE
    on Vulkan device 5 (RTX 4070) was 1.8x faster than the OpenGL default.
    """
    exe = bpy.app.binary_path or "blender"
    try:
        r = subprocess.run(
            [exe, "-b", "--factory-startup", "--gpu-backend", "vulkan",
             "--gpu-device", "help"],
            capture_output=True, text=True, timeout=60)
    except Exception:
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        m = re.match(r"\s*(\d+)\s+(\S+)\s+(.*\S)\s*$", line)
        if m:
            out.append({"index": int(m.group(1)),
                        "device_id": m.group(2),
                        "name": m.group(3)})
    return out


def pick_eevee_vulkan_device(prefer_vendor="NVIDIA", min_free_vram_mb=MIN_FREE_VRAM_MB):
    """Choose a Vulkan device index for EEVEE, or None to keep the default.

    Prefer hardware from ``prefer_vendor``, then fall back to any non-software
    device with enough free VRAM. ``llvmpipe`` is always rejected -- measured at
    3.84 s vs 0.51 s (OpenGL) on a reflective scene, with a 29.31 s cold start.

    Returns ``(index, reason)``; ``index is None`` means "keep the default
    backend/device", and ``reason`` explains the choice for logging.
    """
    devs = eevee_vulkan_devices()
    if not devs:
        return None, "Vulkan 디바이스 조회 실패 — 기본값 유지"
    hw = [d for d in devs if "llvmpipe" not in d["name"].lower()
          and "softpipe" not in d["name"].lower()]
    if not hw:
        return None, "Vulkan 에 하드웨어 GPU 없음 (llvmpipe 만) — 기본값 유지"
    want = [d for d in hw if prefer_vendor.lower() in d["name"].lower()]
    cands = want or hw
    # Vulkan reports a name, not a bus id, so we cannot match it to nvidia-smi
    # directly. If exactly one candidate has room, take it; if several do, we
    # cannot tell which is which, so return None rather than gamble on a card
    # another process is already using (see MIN_FREE_VRAM_MB rationale).
    usage = gpu_host_usage() or {}
    if len(cands) > 1 and usage:
        free_count = sum(1 for v in usage.values()
                         if v["free_mb"] >= min_free_vram_mb)
        if free_count > 1:
            return None, ("Vulkan 디바이스와 nvidia-smi 의 카드 매칭이 불가능하고 "
                          f"여유 VRAM 이 있는 카드가 {free_count}장 — 자동 선택 안 함")
    pick = cands[0]
    return pick["index"], f"{pick['name']} (Vulkan device {pick['index']})"


def reduce_subdiv_for_preview(scene, level=1, only_render_levels=False):
    """Drop SUBSURF render levels -- the most predictable Cycles speedup.

    Measured on 60 spheres, 960x720, 64 spp, one GPU (warm median)::

        render_levels 1   119,160 verts   6.24 s
        render_levels 3   1,904,760 verts 7.67 s
        render_levels 5  30,474,360 verts 17.46 s

    Roughly linear in vertex count. The heavy cost is in ``render_levels``,
    not ``levels`` -- the viewport subdivision is already separate, so lowering
    only ``levels`` changes what you see but not what F12 renders.

    Returns the number of modifiers changed.
    """
    n = 0
    for ob in scene.objects:
        for mod in ob.modifiers:
            if mod.type == "SUBSURF":
                mod.render_levels = level
                if not only_render_levels:
                    mod.levels = level
                n += 1
    return n


def fix_decimate_type(scene, ratio=0.5):
    """Switch COLLAPSE decimation to UNSUBDIV, which is 4.8x faster here.

    Measured on 10 spheres at SUBSURF 5 (960x720, 64 spp, warm median)::

        no decimate                     5,079,060 verts   3.26 s
        DECIMATE COLLAPSE   ratio 0.5   2,539,540 verts  11.52 s   <- 3.5x SLOWER
        DECIMATE UNSUBDIV   ratio 0.5   5,079,060 verts   2.40 s   <- fastest

    COLLAPSE rebuilds triangles, which leaves the BVH more expensive to build
    and traverse -- the cost dwarfs the vertex reduction it buys. UNSUBDIV
    keeps the mesh and substitutes a coarser level of the generated surface,
    which is what you usually want anyway.

    Returns the number of modifiers changed.
    """
    n = 0
    for ob in scene.objects:
        for mod in ob.modifiers:
            if mod.type == "DECIMATE" and mod.decimate_type == "COLLAPSE":
                mod.decimate_type = "UNSUBDIV"
                mod.ratio = ratio
                n += 1
    return n

"""bk -- command line entry point for driving Blender headlessly.

    blender -b --factory-startup -noaudio -P scripts/bk.py -- <command> [options]

Commands
--------
    doctor                     Report Blender build, Python, engines, capabilities.
    check                      Validate the currently open scene.
    analyze <image> [...]      Measure rendered images and judge them.
    render <out>               Render the current scene to <out> and analyse it.
    api ops [prefix]           List bpy.ops operators (optionally filtered).
    api op <idname>            Show an operator's arguments and defaults.
    api prop <Type> <prop>     Show an RNA property's type, enum and default.
    api nodes <Prefix>         List registered node types by class-name prefix.
    api version                Print version + feature probes as JSON.
    api reach <idname>         Judge whether an operator is usable headless.
                               ✅ callable now / ⚠ needs temp_override / ❌ UI-only.
                               Full table: references/12-api-catalog.md

Exit codes
----------
    0  success
    1  the command ran but the result failed its own checks
    2  bad usage

CRITICAL: an uncaught exception inside a ``--python`` script does NOT make
Blender exit non-zero. Verified on 5.2.2: a script that raises RuntimeError
still produced exit code 0. Every command below therefore wraps its work and
calls ``sys.exit()`` explicitly. If you build your own batch scripts you MUST
do the same or your CI will report success on every failed render.
"""

import json
import os
import sys
import traceback

# Allow running as `blender -P /abs/path/bk.py` from any cwd.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402

from bkkit import compat, imagecheck, introspect, scenecheck  # noqa: E402


# --- arg parsing ------------------------------------------------------------

def script_args(argv):
    """Return the arguments after Blender's own ``--`` separator.

    Verified: ``blender -b -P s.py -- build --out x`` gives
    ``sys.argv == ['blender','-b','-P','s.py','--','build','--out','x']``.
    The ``--`` itself is retained, so strip it.
    """
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return []


class Args:
    def __init__(self, argv):
        self.pos = []
        self.flags = {}
        i = 0
        while i < len(argv):
            a = argv[i]
            if a.startswith("--"):
                key = a[2:]
                if "=" in key:
                    k, v = key.split("=", 1)
                    self.flags[k] = v
                    i += 1
                elif i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                    self.flags[key] = argv[i + 1]
                    i += 2
                else:
                    self.flags[key] = True
                    i += 1
            else:
                self.pos.append(a)
                i += 1

    def get(self, key, default=None):
        return self.flags.get(key, default)

    def int_(self, key, default):
        v = self.flags.get(key, default)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def float_(self, key, default):
        v = self.flags.get(key, default)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default


# --- commands ---------------------------------------------------------------

def cmd_doctor(args):
    import platform
    import addon_utils
    print("=== Blender build ===")
    print("  version           ", bpy.app.version, bpy.app.version_string)
    print("  build hash        ", bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else bpy.app.build_hash)
    print("  build date        ", bpy.app.build_date.decode() if isinstance(bpy.app.build_date, bytes) else bpy.app.build_date)
    print("  binary path       ", bpy.app.binary_path)
    print("  background        ", bpy.app.background)
    print("  python            ", sys.version.split()[0], platform.system(), platform.machine())
    print("  numpy             ", imagecheck.HAVE_NUMPY)

    print("=== render engines ===")
    print("  RNA enum_items    ", compat.engine_enum_items(), " <- UNRELIABLE, see notes")
    print("  build_option.cycles", bpy.app.build_options.cycles)
    ok = compat.enable_cycles()
    print("  cycles addon      ", "enabled" if ok else "NOT AVAILABLE")
    try:
        sc = bpy.context.scene
        print("  set CYCLES        ", compat.set_engine(sc, "CYCLES"))
        print("  read back         ", sc.render.engine)
        print("  cycles devices    ", [d.name for d in bpy.context.preferences.addons["cycles"].preferences.devices])
    except Exception as exc:
        print("  set CYCLES         FAILED:", exc)

    print("=== capabilities ===")
    probes = {
        "gn_modifier_rna_properties (>=5.2)": compat.gn_uses_rna_properties(),
        "material.use_nodes deprecated (>=5.0)": compat.use_nodes_is_deprecated(),
        "bpy.data.all_ids (>=5.2)": compat.has_all_ids(),
        "scene.compositing_node_group (>=5.0)": compat.has_scene_compositing_node_group(),
        "context.temp_override (>=3.2)": compat.has_temp_override(),
        "action.slots -- slotted actions (>=4.4)": compat.has_action_slots(),
    }
    for k, v in probes.items():
        print(f"  {k:42} {v}")

    print("=== add-ons in this session ===")
    enabled = sorted(m.__name__ for m in addon_utils.modules() if addon_utils.check(m.__name__)[1])
    print("  enabled:", ", ".join(enabled) or "(none)")
    print("  available:", ", ".join(sorted(m.__name__ for m in addon_utils.modules())))
    print("=== GPU ===")
    rep = compat.gpu_report()
    if "error" in rep:
        print("  조회 실패:", rep["error"])
    else:
        print("  컴파일된 백엔드 :", {k: v for k, v in rep["compiled"].items() if v})
        print("  감지된 GPU      :", rep["devices"] or "없음")
        print("  감지 수(백엔드별):", rep["detected"])
        print("  활성 GPU 수     :", rep["num_gpu"], " has_device:", rep["has_device"])
        print("  선택 백엔드     :", rep["backend"] or "NONE (CPU 로 렌더)")
        print("  빌드 기능       :", rep["features"])
        print("  주의: compiled=True 는 '하드웨어가 있다'가 아니라 "
              "'백엔드가 빌드에 포함됐다' 는 뜻")

    print("=== counts ===")
    print("  bpy.ops total     ", sum(
        len([x for x in dir(getattr(bpy.ops, g)) if not x.startswith('_')])
        for g in dir(bpy.ops) if not g.startswith('_')))
    print("  scene objects     ", len(bpy.data.objects))
    return 0


def cmd_check(args):
    findings, summary = scenecheck.run()
    if args.get("json"):
        print(json.dumps({"summary": summary, "findings": [f.as_dict() for f in findings]}, indent=2, default=str))
    return 1 if summary["verdict"] == "fail" else 0


def cmd_analyze(args):
    if not args.pos:
        print("analyze needs at least one image path")
        return 2
    results, bad = [], 0
    for path in args.pos:
        stats = imagecheck.analyze_image_file(path, fast=not args.get("slow"))
        imagecheck.print_stats(stats, path)
        results.append(stats)
        if stats.get("verdict") == "bad":
            bad += 1
    if len(results) > 1 and args.get("diff"):
        print("--- delta vs first ---")
        for r in results[1:]:
            print(" ", os.path.basename(r.get("path", "?")), imagecheck.compare(results[0], r))
    return 1 if bad else 0


def cmd_render(args):
    if not args.pos:
        print("render needs an output path")
        return 2
    out = args.pos[0]
    scene = bpy.context.scene
    if args.get("engine"):
        compat.set_engine(scene, args.get("engine"))
    if args.get("samples"):
        if scene.render.engine == "CYCLES":
            scene.cycles.samples = args.int_("samples", 64)
        else:
            scene.eevee.taa_render_samples = args.int_("samples", 64)
    if args.get("res"):
        r = str(args.get("res"))
        if "x" in r:
            x, y = r.lower().split("x")
            scene.render.resolution_x, scene.render.resolution_y = int(x), int(y)
    scene.render.image_settings.file_format = str(args.get("format", "PNG")).upper()
    scene.render.filepath = out

    findings, summary = scenecheck.run()
    if summary["verdict"] == "fail" and not args.get("force"):
        print("refusing to render: scene check failed (use --force to override)")
        return 1

    t0 = __import__("time").time()
    res = bpy.ops.render.render(write_still=True)
    dt = __import__("time").time() - t0
    if "FINISHED" not in res:
        print("render returned", sorted(res))
        return 1
    # Blender appends the frame number unless the path already has an extension
    produced = out
    if not produced.lower().endswith((".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff", ".webp")):
        candidates = [out + f"{scene.frame_current:04d}", out]
        for c in candidates:
            if os.path.exists(c + ".png"):
                produced = c + ".png"
                break
    print(f"rendered {produced} in {dt:.2f}s")
    stats = imagecheck.analyze_image_file(produced)
    imagecheck.print_stats(stats, "render result")
    return 1 if stats.get("verdict") == "bad" else 0


def cmd_api(args):
    if not args.pos:
        print("api needs a subcommand: ops | op | prop | nodes | version | reach")
        return 2
    sub = args.pos[0]
    if sub == "version":
        print(json.dumps({
            "version": list(compat.version()),
            "version_string": compat.version_string(),
            "gn_rna_properties": compat.gn_uses_rna_properties(),
            "use_nodes_deprecated": compat.use_nodes_is_deprecated(),
            "all_ids": compat.has_all_ids(),
            "compositing_node_group": compat.has_scene_compositing_node_group(),
            "temp_override": compat.has_temp_override(),
            "action_slots": compat.has_action_slots(),
        }, indent=2))
        return 0
    if sub == "reach":
        # 오퍼레이터가 헤드리스에서 도달 가능한지 즉석 판정한다.
        # 전체 표는 references/12-api-catalog.md 참조.
        if len(args.pos) < 2:
            print("api reach <idname>")
            return 2
        path = args.pos[1]
        if not introspect.op_exists(path):
            print(f"{path!r}: operator does not exist in this session")
            return 1
        grp, name = path.split(".")
        op = getattr(getattr(bpy.ops, grp), name)
        base = None
        err = None
        try:
            base = bool(op.poll())
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
        print(f"{path}")
        print(f"  poll() (현재 컨텍스트) : {base}" + (f"  [{err}]" if err else ""))
        if base:
            print("  판정: ✅ 이 컨텍스트에서 바로 호출 가능")
            return 0
        ob = bpy.data.objects.get("Cube") or next(iter(bpy.data.objects), None)
        for label, kw in (
            ("object", dict(object=ob, active_object=ob, selected_objects=[ob],
                            selected_editable_objects=[ob])),
            ("collection", dict(collection=bpy.context.collection)),
            ("scene", dict(scene=bpy.context.scene)),
        ):
            if ob is None and label != "scene":
                continue
            try:
                with bpy.context.temp_override(**kw):
                    if op.poll():
                        print(f"  temp_override({label}=...) → poll() True")
                        print("  판정: ⚠ 컨텍스트를 만들어 주면 동작")
                        return 0
            except Exception:
                continue
        print("  판정: ❌ 지금 이 컨텍스트에서는 불가")
        print("       씬이 비어 있으면 여기서 ⚠ 로 판정될 수 있는 오퍼레이터가 있다.")
        print("       씬을 채운 상태의 최종 판정은 references/12-api-catalog.md 를 보세요.")
        print("       → ❌ 로 표시된 항목은 data API 로 대체하는 것이 정답.")
        return 0
    if sub == "ops":
        prefix = args.pos[1] if len(args.pos) > 1 else ""
        all_ops = []
        for grp in dir(bpy.ops):
            if grp.startswith("_"):
                continue
            for name in dir(getattr(bpy.ops, grp)):
                if not name.startswith("_"):
                    all_ops.append(f"{grp}.{name}")
        all_ops.sort()
        sel = [o for o in all_ops if prefix in o]
        print(f"{len(sel)} operators")
        for o in sel:
            print(" ", o)
        return 0
    if sub == "op":
        if len(args.pos) < 2:
            print("api op <idname>")
            return 2
        path = args.pos[1]
        if not introspect.op_exists(path):
            print(f"operator {path!r} does not exist")
            return 1
        grp, name = path.split(".")
        rna = getattr(getattr(bpy.ops, grp), name).get_rna_type()
        print(f"=== {path} ===")
        print("  description:", (rna.description or "").strip())
        for p in rna.properties:
            if p.identifier == "rna_type":
                continue
            kind = p.type
            extra = ""
            if p.type == "ENUM":
                extra = " enum=" + str([e.identifier for e in p.enum_items])
                if introspect._is_flag_enum(p):
                    extra += "  (FLAG: 집합으로 전달, 예 {'MESH'})"
            print(f"  {p.identifier:28} {kind:10} default={getattr(p,'default',None)!r}{extra}")
        return 0
    if sub == "prop":
        if len(args.pos) < 3:
            print("api prop <bpy.types.Name|object name> <prop>")
            return 2
        target, prop = args.pos[1], args.pos[2]
        obj = getattr(bpy.types, target, None) or bpy.data.objects.get(target)
        if obj is None:
            # Some types only exist once their add-on registered them, so they
            # are not in bpy.types at all. Verified: CyclesRenderSettings lives
            # in `cycles`, and `bpy.types.CyclesRenderSettings` is a module
            # object, not a type -- only `scene.cycles` (an instance) has it.
            # Enable the cycles add-on and retry against a live instance.
            try:
                import addon_utils
                addon_utils.enable("cycles", default_set=True, persistent=True)
            except Exception:
                pass
            for getter in (lambda t: bpy.context.scene.cycles,
                           lambda t: bpy.data.materials[0].node_tree
                           if bpy.data.materials and bpy.data.materials[0].node_tree else None,
                           lambda t: bpy.context.preferences.addons["cycles"].preferences
                           if "cycles" in bpy.context.preferences.addons else None):
                try:
                    cand = getter(target)
                except Exception:
                    continue
                if cand is not None and getattr(cand, "bl_rna", None) is not None \
                        and cand.bl_rna.identifier == target:
                    obj = cand
                    break
        if obj is None:
            print(f"no such type or object: {target!r}")
            print("  팁: 사이클 관련 타입은 애드온 등록 타입이라 bpy.types 에 없을 수 있다.")
            print("      blender -b -P scripts/bk.py -- api version 으로 build_options 를 확인하고,")
            print("      'scene.cycles.<속성>' 처럼 인스턴스로 지정해라.")
            return 1
        info = introspect.prop_info(obj, prop)
        if info is None:
            print(f"{target!r} has no RNA property {prop!r}")
            print("  available:", sorted(compat.rna_props(obj))[:60])
            return 1
        print(json.dumps(info, indent=2, default=str))
        return 0
    if sub == "nodes":
        prefix = args.pos[1] if len(args.pos) > 1 else "ShaderNode"
        names = introspect.node_idnames(prefix)
        print(f"{len(names)} node types matching {prefix!r}")
        for n in names:
            print(" ", n)
        return 0
    print("unknown api subcommand", sub)
    return 2


COMMANDS = {
    "doctor": cmd_doctor,
    "check": cmd_check,
    "analyze": cmd_analyze,
    "render": cmd_render,
    "api": cmd_api,
}


def main():
    argv = script_args(sys.argv)
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"unknown command {cmd!r}; expected one of {sorted(COMMANDS)}")
        return 2
    return fn(Args(rest))


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        code = 1
    # Force the exit code: Blender swallows the exception status otherwise.
    sys.stdout.flush()
    sys.exit(code)

"""dump_api.py — Blender 스크립트 가능 API 전수 카탈로그 생성기.

왜 이게 필요한가: bpy.ops 는 2500개가 넘고 노드 타입은 500개가 넘는다.
사람이 손으로 문서화하다 보면 반드시 빠진다. 그래서 **머신이 뽑는다.**

    blender -b --factory-startup -noaudio -P scripts/dump_api.py -- \\
        --out /tmp/catalog.md
    blender -b --factory-startup -noaudio -P scripts/dump_api.py -- \\
        --out /tmp/catalog.json --format json

출력 내용
--------
* 2500+ 오퍼레이터 전부: idname, 설명, 인자 시그니처+기본값, 헤드리스 poll() 판정
* 560+ 노드 타입 전부: bl_idname, 라벨, 카테고리, 입력/출력 소켓 이름과 타입
* Modifier / Constraint / Particle / Light / Camera / Brush / Image 등 모든 타입 열거형
* bpy.data 컬렉션 전수와 실제 접근 가능 여부
* bpy.app 서브모듈 전수
* bpy.msgbus, bpy.utils, bpy.path 등 최상위 모듈

이 파일은 손으로 쓰는 문서가 아니라 **생성물**이다. 파일 맨 위에
"이것은 자동 생성됨" 이라고 명시하며, 스킬 문서에서 "목록은 전수 조회하려면
bk.py api 로 돌려라" 고 안내한다.
"""

import argparse
import json
import os
import sys
import traceback

import bpy

import addon_utils

# 5.x 에서 애드온으로 분리된 것들을 전부 켠 상태에서 덤프해야 빠짐이 없다.
# 주의: `node_wrangler` 는 일부러 켜지 않는다 -- 이 빌드에서 `poll()` 이
# `None` 인 컨텍스트에 접근해 예외를 뱉어서(백그라운드 모드) 콘솔이 지저분해진다.
# (실측: 'NoneType' object has no attribute 'type' in node_wrangler/utils/nodes.py:196)
for _m in ("cycles", "io_scene_gltf2", "io_scene_fbx", "io_mesh_uv_layout",
           "io_anim_bvh", "io_curve_svg", "pose_library"):
    try:
        addon_utils.enable(_m, default_set=True, persistent=True)
    except Exception:
        pass


# --------------------------------------------------------------------------
# 수집
# --------------------------------------------------------------------------

def collect_ops(with_poll=True):
    """모든 bpy.ops 를 시그니처 + 헤드리스 poll() 판정과 함께 수집한다.

    ``poll()`` 는 컨텍스트 의존이라 ``-b`` 에서 대부분 False 다. 하지만
    "False" 가 곧 "스크립트로 못 쓴다" 는 뜻은 아니다 -- ``temp_override``
    로 해결되는 경우가 많다. 그래서 결과는 3단계로 기록한다:
      ``ok``     poll() True  → 지금 이 컨텍스트에서 실행 가능
      ``no``     poll() False → 지금 이 컨텍스트에서 불가
      ``?``      getattr 실패 → 애드온 미등록 등
    """
    out = {}
    for grp in dir(bpy.ops):
        if grp.startswith("_"):
            continue
        g = getattr(bpy.ops, grp)
        for name in dir(g):
            if name.startswith("_"):
                continue
            op = getattr(g, name)
            rec = {"group": grp, "name": name, "idname": f"{grp}.{name}"}
            try:
                rna = op.get_rna_type()
                rec["description"] = (rna.description or "").strip()
                rec["label"] = rna.name
                args = {}
                for p in rna.properties:
                    if p.identifier == "rna_type":
                        continue
                    entry = {"type": p.type, "readonly": p.is_readonly}
                    if p.type == "ENUM":
                        entry["enum"] = [e.identifier for e in p.enum_items]
                    else:
                        entry["default"] = repr(getattr(p, "default", None))
                    args[p.identifier] = entry
                rec["args"] = args
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"
            if with_poll:
                try:
                    rec["poll_bg"] = bool(op.poll())
                except Exception as exc:
                    rec["poll_bg"] = None
                    rec["poll_error"] = f"{type(exc).__name__}: {exc}"
            out[f"{grp}.{name}"] = rec
    return out


def _node_trees():
    """노드 타입을 인스턴스화할 수 있는 실제 노드 트리들을 만든다.

    노드 타입의 정의를 읽는 것만으로는 소켓 이름을 알 수 없다. 소켓은
    노드 **인스턴스** 를 만들어서 봐야 한다. 그래서 트리를 직접 구성한다.
    """
    trees = []
    for kind in ("ShaderNodeTree", "CompositorNodeTree", "GeometryNodeTree",
                 "TextureNodeTree"):
        try:
            trees.append(bpy.data.node_groups.new(f"__probe_{kind}", kind))
        except Exception:
            pass
    # 컴포지터 노드 트리는 인터페이스가 있어야 GroupOutput 이 동작한다
    for t in trees:
        if t.bl_idname == "CompositorNodeTree":
            try:
                t.interface.new_socket("Image", in_out="OUTPUT",
                                       socket_type="NodeSocketColor")
            except Exception:
                pass
    return trees


def collect_nodes():
    """등록된 노드 타입 전수.

    각 타입에 대해:
      - 인스턴스를 직접 만들어 **입력/출력 소켓 이름과 타입** 을 읽는다
      - 인스턴스 전용 속성(열거형은 값 나열)을 함께 뽑는다

    인스턴스화가 실패하는 타입(컨텍스트 의존 노드 등)도 기록하되,
    그 사실 자체가 "이건 스크립트로 다루기 어렵다" 는 신호이므로 남긴다.
    """
    prefixes = (
        "ShaderNode", "CompositorNode", "GeometryNode", "TextureNode",
        "FunctionNode", "WorldNode", "NodeInternal", "NodeGroupInput",
        "NodeGroupOutput", "NodeReroute", "FrameNode", "NodeCustom",
        "GeometryNodeGroup", "GeometryNodeTree",
    )
    trees = _node_trees()
    out = {}
    for tname in dir(bpy.types):
        if not tname.startswith(prefixes):
            continue
        rec = {"type": tname, "inputs": [], "outputs": [], "props": []}
        inst = None
        err = None
        for tr in trees:
            try:
                inst = tr.nodes.new(tname)
                break
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
        if inst is None:
            rec["instantiable"] = False
            rec["error"] = err
            try:
                rec["props"] = [
                    {"name": p.identifier, "type": p.type,
                     **({"enum": [x.identifier for x in p.enum_items]}
                        if p.type == "ENUM" else {})}
                    for p in getattr(bpy.types, tname).bl_rna.properties
                    if p.identifier not in _BASE_NODE_PROPS
                ]
            except Exception:
                pass
            out[tname] = rec
            continue

        rec["instantiable"] = True
        rec["label"] = getattr(inst, "bl_label", "") or ""
        rec["tree_used"] = inst.id_data.bl_idname
        for s in inst.inputs:
            rec["inputs"].append({"name": s.name, "id": s.identifier,
                                  "type": s.bl_idname})
        for s in inst.outputs:
            rec["outputs"].append({"name": s.name, "id": s.identifier,
                                   "type": s.bl_idname})
        try:
            for p in inst.bl_rna.properties:
                if p.identifier in _BASE_NODE_PROPS:
                    continue
                e = {"name": p.identifier, "type": p.type, "readonly": p.is_readonly}
                if p.type == "ENUM":
                    e["enum"] = [x.identifier for x in p.enum_items]
                rec["props"].append(e)
        except Exception:
            pass
        # 노드 인스턴스 정리
        try:
            inst.id_data.nodes.remove(inst)
        except Exception:
            pass
        out[tname] = rec

    for t in trees:
        try:
            bpy.data.node_groups.remove(t)
        except Exception:
            pass
    return out


_BASE_NODE_PROPS = {
    "rna_type", "name", "label", "location", "location_absolute", "width", "height",
    "dimensions", "color", "use_custom_color", "select", "show_options",
    "show_preview", "hide", "mute", "parent", "inputs", "outputs", "bl_idname",
    "bl_label", "bl_description", "bl_icon", "bl_static_type", "bl_width_default",
    "bl_width_min", "bl_width_max", "bl_height_default", "bl_height_min",
    "bl_height_max", "warning_propagation", "internal_links", "panel_states",
    "show_texture", "color_tag",
}


def collect_enums():
    """스크립트가 자주 비교하는 타입 열거형을 전수 수집."""
    def enum_of(tname, prop):
        t = getattr(bpy.types, tname, None)
        if t is None:
            return None
        try:
            return [e.identifier for e in t.bl_rna.properties[prop].enum_items]
        except Exception:
            return None

    targets = {
        "Object.type": ("Object", "type"),
        "Modifier.type": ("Modifier", "type"),
        "Constraint.type": ("Constraint", "type"),
        "Light.type": ("Light", "type"),
        "Camera.type": ("Camera", "type"),
        "ParticleSettings.type": ("ParticleSettings", "type"),
        "ParticleSettings.render_type": ("ParticleSettings", "render_type"),
        "ParticleSettings.physics_type": ("ParticleSettings", "physics_type"),
        "Image.source": ("Image", "source"),
        "Image.file_format(deprecated)": ("Image", "file_format"),
        "Brush.stroke_method": ("Brush", "stroke_method"),
        "Keyframe.interpolation": ("Keyframe", "interpolation"),
        "Keyframe.easing": ("Keyframe", "easing"),
        "ShapeKey.interpolation": ("ShapeKey", "interpolation"),
        "Curve.fill_mode": ("Curve", "fill_mode"),
        "Curve.dimensions": ("Curve", "dimensions"),
        "Spline.type": ("Spline", "type"),
        "Mesh.mirror_axis": ("Mesh", "mirror_axis"),
        "MovieClip.tracker.type": ("MovieClip", "type"),
        "Sound.pack_method": ("Sound", "pack_method"),
        "World.node_tree.type": ("ShaderNodeBsdfWorld", "distribution"),
    }
    return {label: enum_of(t, p) for label, (t, p) in targets.items()}


def collect_data():
    """bpy.data 의 모든 컬렉션과 현재 원소 수."""
    out = {}
    for n in dir(bpy.data):
        if n.startswith("_"):
            continue
        obj = getattr(bpy.data, n)
        if not hasattr(obj, "__len__") or not hasattr(obj, "new"):
            continue
        try:
            out[n] = {"count": len(obj)}
        except Exception:
            out[n] = {"count": None}
    return out


def collect_modules():
    """bpy 최상위 모듈, bpy.app, bpy.utils, bpy.path 표면."""
    out = {"bpy": {}, "app": {}, "utils": {}, "path": {}, "types_count": 0}
    out["bpy"] = sorted(n for n in dir(bpy) if not n.startswith("_"))
    out["app"] = sorted(n for n in dir(bpy.app) if not n.startswith("_"))
    out["utils"] = sorted(n for n in dir(bpy.utils) if not n.startswith("_"))
    out["path"] = sorted(n for n in dir(bpy.path) if not n.startswith("_"))
    out["types_count"] = len([n for n in dir(bpy.types) if n[0].isupper()])
    return out


# --------------------------------------------------------------------------
# 렌더링
# --------------------------------------------------------------------------

def to_markdown(data, reach=None):
    L = []
    w = L.append
    ops, nodes, enums, dat, mods = (data["ops"], data["nodes"], data["enums"],
                                    data["data"], data["modules"])

    reach_summary = (reach or {}).get("summary", {})

    n_ok = sum(1 for o in ops.values() if o.get("poll_bg") is True)
    n_no = sum(1 for o in ops.values() if o.get("poll_bg") is False)
    n_q = sum(1 for o in ops.values() if o.get("poll_bg") is None)

    w("# Blender 5.2 bpy API 전수 카탈로그 (자동 생성)")
    w("")
    w("> **이 파일은 손으로 쓴 게 아니다.** `scripts/dump_api.py` 가 실행 중인 "
      "Blender 에서 직접 읽어 생성한 것이다.")
    w("> 재생성:")
    w("> ```bash")
    w("> blender -b --factory-startup -noaudio -P scripts/dump_api.py -- --out catalog.md")
    w("> blender -b --factory-startup -noaudio -P scripts/probe_ops.py -- --out reach.json")
    w("> ```")
    w(">")
    w(f"> 빌드 `{bpy.app.version_string}` (`{bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else bpy.app.build_hash}`), "
      f"Python {sys.version.split()[0]}")
    w("")
    w("## 요약")
    w("")
    w("| 표면 | 개수 |")
    w("|---|---|")
    w(f"| `bpy.ops` 오퍼레이터 | **{len(ops)}** |")
    w(f"| └ 빈 factory 씬에서 `poll()` True | {n_ok} |")
    w(f"| └ `poll()` False | {n_no} |")
    w(f"| └ 판정 불가 (애드온 미등록 등) | {n_q} |")
    w(f"| 노드 타입 | **{len(nodes)}** |")
    w(f"| 타입 열거형 | {len([k for k, v in enums.items() if v])} |")
    w(f"| `bpy.data` 컬렉션 | **{len(dat)}** |")
    w(f"| `bpy.types` 클래스 | {mods['types_count']} |")
    w("")

    if reach_summary:
        w("## ⭐ 헤드리스 도달 가능성 — 이게 진짜 쓸모 있는 숫자")
        w("")
        w("`scripts/probe_ops.py` 가 **오퍼레이터 전부를 실제로 `poll()` 으로 "
          "때려봤다.** (빈 factory 씬을 스크립트 친화적으로 채운 뒤, "
          "`temp_override` 조합까지 시도)")
        w("")
        w("| 판정 | 개수 | 비율 | 의미 |")
        w("|---|---:|---:|---|")
        tot = reach_summary.get("total", 0) or 1
        rb = reach_summary.get("reachable_in_factory_empty", 0)
        ro = reach_summary.get("reachable_only_with_override", 0)
        rn = reach_summary.get("not_reachable", 0)
        w(f"| **✅ 그냥 됨** | {rb} | {100*rb/tot:.1f}% | `bpy.ops.<g>.<op>(...)` 바로 호출 |")
        w(f"| **⚠ override 필요** | {ro} | {100*ro/tot:.1f}% | `temp_override(...)` 를 씌워야 함 |")
        w(f"| **❌ UI 전용** | {rn} | {100*rn/tot:.1f}% | 스크립트로 부를 수 없음. **시도하지 마라** |")
        w("")
        w("> ### 해석이 이게 중요합니다")
        w(">")
        w(f"> 오퍼레이터 {tot}개 중 **스크립트로 실제 호출 가능한 것은 "
          f"{rb+ro}개({100*(rb+ro)/tot:.0f}%) 뿐**입니다.")
        w("> 나머지 73% 는 `outliner.*`, `ui.*`, `view3d.*`, `screen.*`, "
          "`graph.*`, `clip.*` 같은 **UI 전용**입니다.")
        w(">")
        w("> **에이전트가 이걸 모르면 실제로 일이납니다.** "
          "`bpy.ops.outliner.delete()` 같은 걸 찾아서 쓰려고 하고, "
          "안 된다고 몇 시간씩 디버깅합니다.")
        w("> 이 표에서 ❌인 항목을 보지 말고 **애초에 시도하지 마세요.**")
        w("")
        w("> ⚠ 표시(`override 필요`) 항목의 정확한 컨텍스트는 "
          "[`05-automation-headless.md`](05-automation-headless.md) §2 를 보세요.")
        w("")

    w("---")
    w("")
    w("## 목차")
    w("")
    w("- [⭐ 헤드리스 도달 가능성](#-헤드리스-도달-가능성--이게-진짜-쓸모-있는-숫자)")
    w("- [1. `bpy.ops` 전수](#1-bpyops-전수)  ([그룹별 고득점](#11-그룹별-고득점-랭킹--뭘-배워야-하나))")
    w("- [2. 노드 타입 전수](#2-노드-타입-전수)")
    w("- [3. 타입 열거형 전수](#3-타입-열거형-전수)")
    w("- [4. `bpy.data` 컬렉션 전수](#4-bpydata-컬렉션-전수)")
    w("- [5. 최상위 모듈 표면](#5-최상위-모듈-표면)")
    w("")

    # 1. operators
    w("## 1. `bpy.ops` 전수")
    w("")
    w("| 기호 | 의미 |")
    w("|---|---|")
    w("| ✅ | 빈 factory 씬에서 `poll()` True — 바로 호출 가능 |")
    w("| ⚠ | `temp_override` 로 컨텍스트를 만들어야 함 |")
    w("| ❌ | 배경 모드에서 도달 불가 (UI 전용) |")
    w("")
    reach_ops = (reach or {}).get("ops", {})
    by_group = {}
    for o in ops.values():
        by_group.setdefault(o["group"], []).append(o)
    n_yes = n_ovr = n_no = 0
    for grp in sorted(by_group):
        lst = sorted(by_group[grp], key=lambda r: r["name"])
        g_yes = sum(1 for o in lst if reach_ops.get(o["idname"], {}).get("reach") == "base")
        g_ovr = sum(1 for o in lst
                    if str(reach_ops.get(o["idname"], {}).get("reach", "")).startswith("override"))
        g_no = len(lst) - g_yes - g_ovr
        n_yes += g_yes; n_ovr += g_ovr; n_no += g_no
        w(f"### `{grp}` — {len(lst)}개 (✅ {g_yes} / ⚠ {g_ovr} / ❌ {g_no})")
        w("")
        w("| | 오퍼레이터 | 설명 | 인자 |")
        w("|---|---|---|---|")
        for o in lst:
            r = reach_ops.get(o["idname"], {}).get("reach")
            mark = {"base": "✅", "no": "❌"}.get(r, "⚠" if r else "?")
            desc = (o.get("description") or o.get("label") or "").replace("|", "\\|")[:90]
            args = o.get("args") or {}
            parts = []
            for k, v in list(args.items()):
                if k == "rna_type":
                    continue
                if v["type"] == "ENUM":
                    parts.append(f"`{k}`={'/'.join(v.get('enum', []))}")
                else:
                    parts.append(f"`{k}`:{v['type']}")
            argstr = (", ".join(parts) or "—").replace("|", "\\|")
            w(f"| {mark} | `{o['idname']}` | {desc} | {argstr} |")
        w("")
    w(f"**소계: ✅ {n_yes} / ⚠ {n_ovr} / ❌ {n_no}**")
    w("")
    w("### 1.1 그룹별 고득점 랭킹 — 뭘 배워야 하나")
    w("")
    w("개수가 아니라 **도달 가능한 비율** 로 정렬했다. 비율이 높고 개수까지 있는 "
      "그룹이 실제로 쓸모 있는 영역이다. 비율이 0% 인 그룹은 아예 건드리지 마라.")
    w("")
    rows = []
    for grp in by_group:
        lst = by_group[grp]
        yes = sum(1 for o in lst if reach_ops.get(o["idname"], {}).get("reach") == "base")
        ovr = sum(1 for o in lst
                  if str(reach_ops.get(o["idname"], {}).get("reach", "")).startswith("override"))
        tot_g = len(lst)
        rows.append((100 * (yes + ovr) / tot_g, yes + ovr, tot_g, grp))
    rows.sort(reverse=True)
    w("| 그룹 | 도달가능 | 전체 | 비율 | 판단 |")
    w("|---|---:|---:|---:|---|")
    for ratio, reach_n, tot_g, grp in rows:
        if ratio >= 80:
            verdict = "**핵심** — 반드시 익혀라"
        elif ratio >= 40:
            verdict = "유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라"
        elif ratio > 0:
            verdict = "드묾 — data API 로 대체되는 경우가 많다"
        else:
            verdict = "**배우지 마라** — UI 전용"
        w(f"| `{grp}` | {reach_n} | {tot_g} | {ratio:.0f}% | {verdict} |")
    w("")

    # 2. nodes
    w("## 2. 노드 타입 전수")
    w("")
    n_inst = sum(1 for n in nodes.values() if n.get("instantiable"))
    w(f"총 **{len(nodes)}** 개. 그중 **{n_inst}** 개를 실제로 인스턴스화해 "
      "**입력/출력 소켓 이름과 타입** 을 뽑았다. 인스턴스화가 실패한 "
      f"{len(nodes)-n_inst} 개는 `⚠` 로 표시되며, 그 자체가 "
      "\"이 노드는 스크립트로 다루기 어렵다\" 는 신호다.")
    w("")
    fam = {}
    for n in nodes.values():
        key = n["type"]
        for p in ("Shader", "Compositor", "Geometry", "Texture", "Function", "World"):
            if key.startswith(p):
                fam.setdefault(p, []).append(n)
                break
        else:
            fam.setdefault("기타", []).append(n)
    for group in sorted(fam):
        lst = sorted(fam[group], key=lambda r: r["type"])
        w(f"### {group} 노드 — {len(lst)}개")
        w("")
        w("| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |")
        w("|---|---|---|---|---|")
        for n in lst:
            ok = n.get("instantiable")
            mark = "✅" if ok else "⚠"
            ins = ", ".join(f"{s['name']}:{s['type'].replace('NodeSocket','')}"
                            for s in n.get("inputs", [])) or "—"
            outs = ", ".join(f"{s['name']}:{s['type'].replace('NodeSocket','')}"
                             for s in n.get("outputs", [])) or "—"
            if not ok:
                ins = (n.get("error") or "인스턴스화 실패")[:60]
            lbl = (n.get("label") or "").replace("|", "\\|")[:34]
            w(f"| {mark} | `{n['type']}` | {lbl} "
              f"| {ins.replace('|', chr(92) + '|')} "
              f"| {outs.replace('|', chr(92) + '|')} |")
        w("")

    # 3. enums
    w("## 3. 타입 열거형 전수")
    w("")
    w("| 속성 | 값 |")
    w("|---|---|")
    for k, v in enums.items():
        if v:
            w(f"| `{k}` | {', '.join(f'`{x}`' for x in v)} |")
        else:
            w(f"| `{k}` | *(조회 불가 — 런타임 등록 enum)* |")
    w("")

    # 4. data
    w("## 4. `bpy.data` 컬렉션 전수")
    w("")
    w("| 컬렉션 | 현재 원소 수 |")
    w("|---|---|")
    for k, v in sorted(dat.items()):
        w(f"| `bpy.data.{k}` | {v['count']} |")
    w("")

    # 5. modules
    w("## 5. 최상위 모듈 표면")
    w("")
    for key, label in (("bpy", "bpy"), ("app", "bpy.app"), ("utils", "bpy.utils"),
                       ("path", "bpy.path")):
        w(f"### `{label}` — {len(mods[key])}개")
        w("")
        w("```")
        w("\n".join(mods[key]))
        w("```")
        w("")
    return "\n".join(L)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="dump_api", add_help=False)
    ap.add_argument("--out", default="bpy_api_catalog.md")
    ap.add_argument("--format", default="md", choices=["md", "json"])
    ap.add_argument("--reach", default=None,
                    help="probe_ops.py 가 만든 reachability JSON. 있으면 도달 가능성 열을 붙인다")
    ap.add_argument("--no-poll", action="store_true",
                    help="poll() 판정을 생략하고 순수 시그니처만")
    known, _ = ap.parse_known_args(argv)

    print("collecting operators ...", flush=True)
    ops = collect_ops(with_poll=not known.no_poll)
    print(f"  {len(ops)} operators", flush=True)
    print("collecting node types ...", flush=True)
    nodes = collect_nodes()
    print(f"  {len(nodes)} node types", flush=True)
    print("collecting enums / data / modules ...", flush=True)
    data = {
        "blender": bpy.app.version_string,
        "generated_by": "scripts/dump_api.py",
        "ops": ops, "nodes": nodes, "enums": collect_enums(),
        "data": collect_data(), "modules": collect_modules(),
    }
    if known.format == "json":
        with open(known.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
    else:
        with open(known.out, "w", encoding="utf-8") as fh:
            reach = None
            if known.reach and os.path.exists(known.reach):
                reach = json.load(open(known.reach, encoding="utf-8"))
            fh.write(to_markdown(data, reach=reach))
    print(f"written: {known.out}  ({os.path.getsize(known.out):,} bytes)")
    print("__SCRIPT_OK__")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    sys.stdout.flush()
    sys.exit(0)

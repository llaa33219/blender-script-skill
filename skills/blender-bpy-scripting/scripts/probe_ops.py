"""probe_ops.py — poll() 가 False 인 오퍼레이터가 temp_override 로 살아나는지 측정.

`bk.py` / `dump_api.py` 가 기록한 "배경 모드 poll() = False" 는
"스크립트로 못 쓴다" 라는 뜻이 아니다. 컨텍스트를 만들어 주면 살아나는
오퍼레이터가 많다. 이 스크립트가 그걸 **실측**해서 숫자로 남긴다.

    blender -b --factory-startup -noaudio --python-exit-code 1 -P scripts/probe_ops.py -- \
        --out /workspace/audit/ops_reach.json

측정 방법 (오퍼레이터마다):
  1. 기본 factory 씬에서 poll()
  2. 씬을 "스크립트 친화적"하게 채운다 (오브젝트+메시+키프레임+모디파이러+
     머티리얼+조명+카메라+컬렉션+노드트리+텍스트 데이터블록)
  3. 가능한 모든 컨텍스트 조합으로 temp_override 를 걸어 poll() 재시도
  4. 최종 판정: base / override / still_no

결과는 "에이전트가 어떤 오퍼레이터를 기대할 수 있는가" 의 답이다.
"""

import argparse
import json
import os
import sys
import traceback

import bpy

import addon_utils

for _m in ("cycles", "io_scene_gltf2", "io_scene_fbx", "io_mesh_uv_layout",
           "io_anim_bvh", "io_curve_svg", "pose_library"):
    try:
        addon_utils.enable(_m, default_set=True, persistent=True)
    except Exception:
        pass


# --------------------------------------------------------------------------
# 스크립트 친화적 씬 구축
# --------------------------------------------------------------------------

def build_friendly_scene():
    """오퍼레이터가 요구할 만한 참조를 최대한 다 만들어 둔다."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "ProbeScene"

    coll = bpy.data.collections.new("ProbeColl")
    scene.collection.children.link(coll)

    # 메시 + 활성 상태
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = "ProbeMesh"
    obj.data.materials.append(bpy.data.materials.new("ProbeMat"))
    obj.modifiers.new("Bevel", "BEVEL")
    obj.keyframe_insert("location", frame=1)
    obj.location = (1, 0, 0)
    obj.keyframe_insert("location", frame=10)

    # UV, 커브, 텍스트, 라이트, 카메라, 이미지, armature
    bpy.ops.mesh.primitive_cylinder_add(location=(2, 0, 0))
    bpy.context.object.data.materials.append(bpy.data.materials.get("ProbeMat"))
    bpy.ops.object.camera_add(location=(0, -6, 2))
    scene.camera = bpy.context.object
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    bpy.ops.object.text_add(location=(-2, 0, 0))

    curve = bpy.data.curves.new("ProbeCurve", "CURVE")
    co = curve.splines.new("POLY")
    co.points.add(2)
    bpy.data.objects.new("ProbeCurveObj", curve).data and None
    curve_obj = bpy.data.objects.new("ProbeCurveObj", curve)
    coll.objects.link(curve_obj)

    arm = bpy.data.armatures.new("ProbeArm")
    bpy.data.objects.new("ProbeArmObj", arm)
    coll.objects.link(bpy.data.objects["ProbeArmObj"])

    img = bpy.data.images.new("ProbeImg", 8, 8)
    txt = bpy.data.texts.new("ProbeText")
    txt.write("# probe")
    world = bpy.data.worlds.new("ProbeWorld")
    scene.world = world

    # 노드 트리들
    for kind in ("ShaderNodeTree", "GeometryNodeTree", "CompositorNodeTree"):
        ng = bpy.data.node_groups.new(f"Probe{kind}", kind)
        if kind == "ShaderNodeTree":
            ng.nodes.new("ShaderNodeBsdfPrincipled")
            ng.nodes.new("ShaderNodeOutputMaterial")
        elif kind == "GeometryNodeTree":
            ng.interface.new_socket("Geometry", in_out="INPUT",
                                    socket_type="NodeSocketGeometry")
            ng.interface.new_socket("Geometry", in_out="OUTPUT",
                                    socket_type="NodeSocketGeometry")
            gi = ng.nodes.new("NodeGroupInput")
            go = ng.nodes.new("NodeGroupOutput")
            ng.links.new(gi.outputs[0], go.inputs[0])
            m = bpy.context.object.modifiers.new("GN", "NODES")
            m.node_group = ng
        else:
            rl = ng.nodes.new("CompositorNodeRLayers")
            go = ng.nodes.new("NodeGroupOutput")
            ng.interface.new_socket("Image", in_out="OUTPUT",
                                    socket_type="NodeSocketColor")
            go = ng.nodes.new("NodeGroupOutput")
            ng.links.new(rl.outputs["Image"], go.inputs[0])
        scene.compositing_node_group = ng if kind == "CompositorNodeTree" else scene.compositing_node_group

    # 유틸
    scene.gravity = (0, 0, -9.81)
    addon_utils.enable("cycles", default_set=True, persistent=True)
    scene.render.engine = "CYCLES"
    bpy.context.view_layer.update()
    return scene


def override_variants():
    """시도할 컨텍스트 조합. 순서대로 점점 더 많은 걸 넘긴다."""
    ob = bpy.data.objects.get("ProbeMesh")
    arm = bpy.data.objects.get("ProbeArmObj")
    return [
        ("object", dict(object=ob, active_object=ob, selected_objects=[ob],
                        selected_editable_objects=[ob])),
        ("object+collection", dict(object=ob, active_object=ob, selected_objects=[ob],
                                    selected_editable_objects=[ob],
                                    collection=bpy.data.collections["ProbeColl"])),
        ("collection", dict(collection=bpy.data.collections["ProbeColl"])),
        ("scene", dict(scene=bpy.context.scene)),
        ("node_tree", dict(scene=bpy.context.scene,
                           space_data=type("S", (), {"type": "NODE_EDITOR",
                                                     "node_tree": None})())),
    ]


# --------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="probe_ops", add_help=False)
    ap.add_argument("--out", default="ops_reach.json")
    known, _ = ap.parse_known_args(argv)

    scene = build_friendly_scene()
    print("scene built; probing operators ...", flush=True)

    allops = []
    for grp in dir(bpy.ops):
        if grp.startswith("_"):
            continue
        g = getattr(bpy.ops, grp)
        for name in dir(g):
            if not name.startswith("_"):
                allops.append((grp, name, getattr(g, name)))

    results = {}
    n_base = n_ovr = n_no = 0
    for i, (grp, name, op) in enumerate(allops):
        idname = f"{grp}.{name}"
        rec = {"group": grp, "name": name}
        try:
            rec["base"] = bool(op.poll())
        except Exception as exc:
            rec["base"] = None
            rec["base_error"] = f"{type(exc).__name__}"
        if rec["base"]:
            rec["reach"] = "base"
            n_base += 1
            results[idname] = rec
            continue

        # override 시도
        reached = None
        for label, kw in override_variants():
            try:
                with bpy.context.temp_override(**kw):
                    if op.poll():
                        reached = label
                        break
            except Exception:
                continue
        if reached:
            rec["reach"] = f"override:{reached}"
            n_ovr += 1
        else:
            rec["reach"] = "no"
            n_no += 1
        results[idname] = rec
        if (i + 1) % 250 == 0:
            print(f"  {i+1}/{len(allops)}", flush=True)

    summary = {
        "blender": bpy.app.version_string,
        "total": len(allops),
        "reachable_in_factory_empty": n_base,
        "reachable_only_with_override": n_ovr,
        "not_reachable": n_no,
    }
    json.dump({"summary": summary, "ops": results},
              open(known.out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(json.dumps(summary, indent=2))
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

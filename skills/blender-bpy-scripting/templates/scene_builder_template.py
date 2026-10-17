"""블렌더 씬 빌더 템플릿 — 복사해서 쓰세요.

이 파일은 이 스킬의 모든 문서와 동일한 규칙을 따릅니다:

  1. ``--factory-startup`` 에서 돌릴 수 있다 (Cycles 애드온 활성화 포함)
  2. 모든 ``bpy.ops`` 반환값을 검사한다
  3. 예외가 나면 프로세스 종료 코드가 0이 되므로 직접 ``sys.exit`` 한다
  4. 빌드 직후 ``scenecheck`` 로 정적 검증한다
  5. 렌더 후 ``imagecheck`` 로 픽셀을 측정한다

사용법::

    blender -b --factory-startup -noaudio -P scene_template.py -- \\
        --out /tmp/shot.png --samples 48 --res 480x360

인자를 안 주고 그냥 돌리면 기본값으로 /tmp/bk_preview.png 를 만든다.
"""

import argparse
import os
import sys
import traceback

import bpy

# 이 템플릿이 스킬 패키지(bkkit)를 찾을 수 있도록 경로를 추가한다.
# 실제 프로젝트에서는 이 두 줄을 지우고 상위 경로를 쓰거나, 패키지를 설치하라.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.join(_HERE, "scripts"),
              os.path.join(_HERE, "..", "scripts")):
    _cand = os.path.abspath(_cand)
    if os.path.isdir(os.path.join(_cand, "bkkit")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

from bkkit import compat, imagecheck, introspect, scenecheck  # noqa: E402


# --------------------------------------------------------------------------
# 1. 헬퍼
# --------------------------------------------------------------------------

def link(obj, collection=None):
    """``bpy.data.objects.new`` 로 만든 객체를 씬에 연결한다.

    ``bpy.data.objects.new()`` 는 어디에도 링크하지 않아서 이게 없다면
    오브젝트가 보이지도 렌더되지도 않는다. 가장 흔한 1순위 실수.
    """
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def new_material(name, base_color=(0.8, 0.8, 0.8, 1.0), roughness=0.5,
                 metallic=0.0, emission=None, emission_strength=0.0):
    """5.x 방식의 머티리얼 생성.

    ``material.use_nodes = True`` 는 deprecated (6.0 제거 예정) 이므로
    설정하지 않는다. 새 머티리얼은 이미 ``node_tree`` 를 가지고 있다.
    """
    mat = bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def add_light(kind, location, energy, rotation=(0, 0, 0), color=(1, 1, 1), **data_kwargs):
    """조명 추가. ``bpy.ops`` 의 CANCELLED 를 실제로 감지한다."""
    introspect.call_op("object.light_add", type=kind, location=location)
    obj = bpy.context.object
    obj.data.energy = energy
    obj.data.color = color
    obj.rotation_euler = rotation
    for key, value in data_kwargs.items():
        setattr(obj.data, key, value)
    return obj


def add_camera(location, rotation, lens=50.0, **cam_kwargs):
    """카메라 추가 후 씬에 지정. ``scene.camera`` 를 안 넣으면 렌더가 실패한다."""
    introspect.call_op("object.camera_add", location=location, rotation=rotation)
    obj = bpy.context.object
    obj.data.lens = lens
    for key, value in cam_kwargs.items():
        setattr(obj.data, key, value)
    bpy.context.scene.camera = obj
    return obj


def point_at(obj, target):
    """오브젝트의 -Z 축이 ``target`` 을 향하게 한다 (카메라/조명 조준용)."""
    from mathutils import Vector
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


# --------------------------------------------------------------------------
# 2. 씬 구축 — 이 부분을 네 작업에 맞게 바꾼다
# --------------------------------------------------------------------------

def build_scene():
    """빈 씬에서 시작해 원하는 콘텐츠를 만든다. 실제 스크립트의 핵심 부분."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # --- 배경/월드 ---
    # 주의: ``World.use_nodes`` 도 5.x 에서 deprecated 라 설정하지 않는다.
    # 새 World 는 이미 Background + OutputWorld 노드가 들어있다.
    world = bpy.data.worlds.new("World")
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.02, 0.025, 0.035, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    # --- 바닥 ---
    introspect.call_op("mesh.primitive_plane_add", size=40, location=(0, 0, 0))
    ground = bpy.context.object
    ground.name = "Ground"
    ground.data.materials.append(
        new_material("GroundMat", (0.045, 0.05, 0.06, 1.0), roughness=0.35, metallic=0.0)
    )

    # --- 피사체 ---
    introspect.call_op("mesh.primitive_uv_sphere_add", radius=1.0,
                       location=(0, 0, 1.2), segments=96, ring_count=48)
    subject = bpy.context.object
    subject.name = "Subject"
    subject.data.materials.append(
        new_material("SubjectMat", (0.85, 0.25, 0.12, 1.0),
                     roughness=0.18, metallic=0.85)
    )
    # 비균일 스케일은 노멀/모디파이어를 깨뜨린다
    subject.scale = (1.0, 1.0, 1.0)
    introspect.call_op("object.shade_smooth_by_angle", angle=0.5236)

    # --- 3점 조명: 키 + 필 + 림 ---
    key = add_light("AREA", (3.0, -3.5, 4.0), energy=900.0, color=(1.0, 0.95, 0.90))
    point_at(key, (0, 0, 1.2))
    fill = add_light("AREA", (-4.0, -2.0, 2.0), energy=180.0, color=(0.75, 0.85, 1.0))
    point_at(fill, (0, 0, 1.2))
    rim = add_light("AREA", (-1.0, 4.0, 3.0), energy=600.0, color=(0.9, 0.95, 1.0))
    point_at(rim, (0, 0, 1.2))

    # --- 카메라: 3/4 앵글, 피사체 중심을 프레임의 위쪽 1/3 지점에 ---
    cam = add_camera((3.6, -5.2, 2.6), (1.18, 0.0, 0.60), lens=65.0)
    point_at(cam, (0, 0, 1.15))

    return scene


# --------------------------------------------------------------------------
# 3. 렌더 설정
# --------------------------------------------------------------------------

def setup_render(scene, path, samples=64, res=(640, 480), engine="CYCLES",
                 use_gpu=True, quality="balanced", max_devices=None):
    """렌더 엔진과 출력 설정.

    ``compat.set_engine`` 이 Cycles 애드온을 자동으로 활성화하므로
    ``--factory-startup`` 에서도 동작한다.

    ``use_gpu=True`` 면 ``compat.enable_gpu()`` 로 GPU를 켜되, **사용 가능한
    GPU가 없거나 VRAM이 부족하면 예외 없이 CPU로 내려간다.** 직접
    ``device = "GPU"`` 를 대입하는 것의 최대 문제는 정확히 그 "조용한 폴백"
    때문이다 -- 6장 GPU 머신에서 점유 중인 카드를 잡으면
    ``System is out of GPU memory`` 로 죽는다.

    quality: "fast" (디노이즈 끔, 실측 -25%) / "balanced" (기본)
    """
    compat.set_engine(scene, engine)
    if scene.render.engine == "CYCLES":
        gpu_info = None
        if use_gpu:
            ok, gpu_info = compat.enable_gpu(scene, max_devices=max_devices)
            if not ok:
                print(f"[GPU 폴백] {gpu_info.get('reason')}")
                scene.cycles.device = "CPU"
            else:
                sel = ", ".join(s["name"] for s in gpu_info.get("selected", []))
                print(f"[GPU 사용] {gpu_info['num_gpu_devices']}장: {sel} "
                      f"denoiser={gpu_info.get('denoiser')}")
        else:
            scene.cycles.device = "CPU"      # GPU 없이 강제
        scene.cycles.samples = samples
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.02
        scene.cycles.seed = 1234           # 재현성
        if scene.render.engine == "CYCLES":
            compat.gpu_speed_preset(scene, quality=quality)
    else:
        scene.eevee.taa_render_samples = samples

    setup_output(scene, path, res)
    return scene


def setup_output(scene, path, res=(640, 480)):
    """출력 포맷·해상도·컬러 매니지먼트. 엔진 설정과 독립적이다."""
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"   # look 보다 먼저 설정해야 한다
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = path
    return scene


# --------------------------------------------------------------------------
# 4. 메인
# --------------------------------------------------------------------------

def script_argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def parse_args(argv):
    p = argparse.ArgumentParser(prog="scene_template", add_help=False)
    p.add_argument("--out", default=os.path.join("/tmp", "bk_preview.png"))
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--engine", default=None,
                   help="BLENDER_WORKBENCH | BLENDER_EEVEE | CYCLES "
                        "(기본: --purpose 로 자동 선택)")
    p.add_argument("--purpose", default="final",
                   choices=["structure", "explore", "animate", "final"],
                   help="structure=Workbench 클레이 / explore=EEVEE 탐색 / "
                        "animate·final=Cycles (엔진 자동 선택)")
    p.add_argument("--cpu", action="store_true", help="GPU 무시하고 CPU 로 렌더")
    p.add_argument("--quality", default="balanced", choices=["fast", "balanced", "quality"],
                   help="fast = 디노이즈 off (실측 -25%%)")
    p.add_argument("--gpu-count", type=int, default=None,
                   help="사용할 GPU 장수 (기본 1). NVLink 없는 카드에서 늘리면 느려진다")
    p.add_argument("--force", action="store_true",
                   help="씬 검증이 실패해도 렌더한다")
    known, _ = p.parse_known_args(argv)
    return known


def main():
    args = parse_args(script_argv())

    scene = build_scene()
    if args.engine:
        # 엔진이 명시되면 그대로 사용
        compat.set_engine(scene, args.engine)
        setup_render(scene, args.out, args.samples, (args.width, args.height),
                     args.engine, use_gpu=not args.cpu, quality=args.quality,
                     max_devices=args.gpu_count)
    else:
        # 엔진 자동 선택 — purpose 로 판단 (references/19-render-engines.md)
        chosen = compat.set_engine_for_purpose(scene, args.purpose,
                                               samples=args.samples)
        print(f"[엔진 선택] {chosen['engine']} "
              f"({args.purpose}) {chosen.get('note') or ''}")
        if chosen["engine"] == "CYCLES" and chosen.get("gpu"):
            print(f"[GPU 사용] {chosen['devices']}장  "
                  f"denoiser={scene.cycles.denoiser}")
        if chosen["engine"] != "CYCLES":
            setup_render(scene, args.out, args.samples,
                         (args.width, args.height), chosen["engine"],
                         use_gpu=False)
        else:
            # 엔진 자동 선택이 이미 사이클스 설정을 했다.
            # 여기서는 출력 관련 설정만 맞춘다 (setup_render 를 다시 돌리면
            # samples/denoising 을 덮어쓴다).
            setup_output(scene, args.out, (args.width, args.height))

    # --- 정적 검증: 실패하면 렌더하지 않는다 ---
    findings, summary = scenecheck.run()
    if summary["verdict"] == "fail" and not args.force:
        print("씬 검증 실패 — 렌더하지 않음. (강제하려면 --force)")
        return 1

    # --- 렌더 ---
    import time
    t0 = time.time()
    result = bpy.ops.render.render(write_still=True)
    elapsed = time.time() - t0
    if "FINISHED" not in result:
        print("렌더 실패:", sorted(result))
        return 1
    produced = args.out
    if not produced.lower().endswith(".png"):
        produced += ".png"
    print(f"렌더 완료: {produced}  ({elapsed:.1f}s, {args.samples}spp, "
          f"{args.width}x{args.height}, {scene.render.engine})")

    # --- 픽셀 측정 ---
    stats = imagecheck.analyze_image_file(produced)
    imagecheck.print_stats(stats, "측정 결과")

    # 결과를 사용자에게 넘길 때 반드시 함께 알려줄 정보
    print("\n--- 전달 요약 ---")
    print(f"  파일        : {produced}")
    print(f"  엔진/샘플   : {scene.render.engine} / {args.samples} spp")
    print(f"  해상도      : {args.width}x{args.height}")
    print(f"  씬 검증     : {summary['verdict']} "
          f"(errors={summary['errors']} warnings={summary['warnings']})")
    print(f"  이미지 판정 : {stats['verdict']}  (mean_luma={stats['mean_luma']})")

    return 1 if stats["verdict"] == "bad" else 0


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    # 이게 없으면 예외가 나도 종료 코드가 0이 되어 CI가 조용히 성공한다
    sys.exit(code)

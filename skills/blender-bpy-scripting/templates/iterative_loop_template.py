"""개선 루프 템플릿 — 파라미터를 바꿔가며 렌더하고 측정한다.

"한 번 스크립트를 짜고 끝"이 아니라 **빌드 → 검증 → 렌더 → 측정 → 개선**을
자동으로 반복하는 패턴. 이 스킬에서 가장 중요한 워크플로.

사용법::

    blender -b --factory-startup -noaudio -P iterative_loop_template.py

개념::

    for attempt in attempts:
        scene = build(params[attempt])     # 파라미터로 씬을 만드���다
        check = scenecheck.run()           # 정적 검증 (0.1초)
        if check fails: stop               # 렌더 전에 걸러낸다
        render()                           # 렌더
        stats = measure()                  # 픽셀 측정
        if good(stats, prev): stop         # 수렴했으면 멈춘다
        prev = stats

실측 기준선 (Blender 5.2.2, CPU):
  - 320x240 @ 32spp Cycles CPU  ≈ 6~17초
  - 240x180 @ 24spp             ≈ 6초
  반복 중에는 무조건 작은 해상도/낮은 샘플을 쓴다. 최종본만 크게.
"""

import os
import sys
import traceback

import bpy

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.join(_HERE, "scripts"),
              os.path.join(_HERE, "..", "scripts")):
    _cand = os.path.abspath(_cand)
    if os.path.isdir(os.path.join(_cand, "bkkit")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

from bkkit import compat, imagecheck, introspect, scenecheck  # noqa: E402

OUT_DIR = os.environ.get("BK_OUT", "/tmp/bk_loop")


# --------------------------------------------------------------------------
# 씬 빌더 — 파라미터를 받아서 씬을 만든다
# --------------------------------------------------------------------------

def build(params):
    """``params`` 딕셔너리로 씬을 구축한다. 호출마다 완전히 새로 만든다.

    ``read_factory_settings`` 로 초기화하는 이유: 이전 시도에서 남은
    오브젝트/머티리얼/조명이 다음 시도에 섞이면 비교가 불가능해진다.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 월드 (새 World 는 이미 node_tree 를 가진다 -- use_nodes 설정 금지)
    world = bpy.data.worlds.new("World")
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.01, 0.012, 0.02, 1.0)
    bg.inputs["Strength"].default_value = params["world_strength"]
    scene.world = world

    # 바닥
    introspect.call_op("mesh.primitive_plane_add", size=40)
    ground = bpy.context.object
    ground.name = "Ground"
    mat = bpy.data.materials.new("GroundMat")
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1.0)
    bsdf.inputs["Roughness"].default_value = params["ground_roughness"]
    ground.data.materials.append(mat)

    # 피사체
    introspect.call_op("mesh.primitive_uv_sphere_add", radius=1.0,
                       location=(0, 0, 1.0), segments=64, ring_count=32)
    subj = bpy.context.object
    subj.name = "Subject"
    m = bpy.data.materials.new("SubjectMat")
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.8, 0.2, 0.1, 1.0)
    b.inputs["Roughness"].default_value = params["subject_roughness"]
    b.inputs["Metallic"].default_value = params["subject_metallic"]
    subj.data.materials.append(m)
    introspect.call_op("object.shade_smooth_by_angle", angle=0.5236)

    # 키 라이트 (반사 하이라이트를 만드는 광원)
    introspect.call_op("object.light_add", type="AREA", location=(2.5, -3.0, 3.5))
    key = bpy.context.object
    key.name = "Key"
    key.data.energy = params["key_energy"]
    key.data.size = 2.0
    from mathutils import Vector
    key.rotation_euler = (Vector((0, 0, 1.0)) - key.location).to_track_quat("-Z", "Y").to_euler()

    # 카메라
    introspect.call_op("object.camera_add", location=(0, -params["cam_dist"], 1.1),
                       rotation=(1.57, 0, 0))
    scene.camera = bpy.context.object
    scene.camera.data.lens = params["lens"]

    setup_render(scene, params)
    return scene


def setup_render(scene, p):
    compat.set_engine(scene, "CYCLES")
    scene.cycles.device = "CPU"
    scene.cycles.samples = p["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.seed = 1234                      # 재현성
    scene.render.resolution_x, scene.render.resolution_y = p["res"]
    scene.view_settings.view_transform = "AgX"    # look 보다 먼저
    scene.render.image_settings.file_format = "PNG"
    return scene


# --------------------------------------------------------------------------
# 수렴 판정
# --------------------------------------------------------------------------

TARGET_MEAN = (0.12, 0.45)      # 평균 밝기 허용 구간
MIN_CONTRAST = 0.15
MAX_WHITE = 0.20
STABLE_DELTA = 0.08              # 직전 시도 대비 평균 밝기 변화가 이보다 작으면 수렴


def assess(stats):
    """통계에서 목표 달성 여부와 다음에 고칠 것을 반환한다."""
    if stats.get("error"):
        return False, ["측정 실패: " + stats["error"]], "확인 필요"

    reasons = []
    mean = stats["mean_luma"]
    lo, hi = TARGET_MEAN

    ok = True
    if mean < lo:
        ok = False
        reasons.append(f"mean_luma {mean:.4f} < {lo} — 어둡다. 광량/월드 강도를 올려라")
    elif mean > hi:
        ok = False
        reasons.append(f"mean_luma {mean:.4f} > {hi} — 너무 밝다. 광량을 낮추거나 노출을 빼라")

    if stats["contrast_p01_p99"] < MIN_CONTRAST:
        ok = False
        reasons.append(f"contrast {stats['contrast_p01_p99']:.4f} < {MIN_CONTRAST} — "
                       f"평평하다. 키/필 대비를 키우거나 머티리얼을 나눠라")

    if stats["white_fraction"] > MAX_WHITE:
        ok = False
        reasons.append(f"white_fraction {stats['white_fraction']*100:.1f}% > {MAX_WHITE*100:.0f}% — "
                       f"클리핑 과다. AgX 톤매핑 확인 또는 광량 하향")

    if not reasons:
        reasons.append("모든 목표치 충족")
    return ok, reasons, None


# --------------------------------------------------------------------------
# 시도 시퀀스
# --------------------------------------------------------------------------

BASE = {
    "world_strength": 1.0,
    "ground_roughness": 0.35,
    "subject_roughness": 0.20,
    "subject_metallic": 0.80,
    "key_energy": 200.0,
    "cam_dist": 5.0,
    "lens": 50.0,
    "samples": 32,
    "res": (320, 240),
}

# 각 시도에서 무엇을 바꿀지. (변경 dict, 이유)
ATTEMPTS = [
    ({}, "기준선"),
    ({"key_energy": 600.0, "world_strength": 1.5}, "광량 부족 예상 → 3배"),
    ({"key_energy": 600.0, "world_strength": 1.5, "ground_roughness": 0.55,
      "subject_roughness": 0.32}, "그림자 대비 부족 → 바닥/피사체 거칠기 상향"),
    ({"key_energy": 1400.0, "world_strength": 1.5, "ground_roughness": 0.55,
      "subject_roughness": 0.32, "cam_dist": 4.2}, "키 하이라이트 부족 → 광량 추가"),
    ({"key_energy": 1400.0, "world_strength": 1.5, "ground_roughness": 0.55,
      "subject_roughness": 0.32, "cam_dist": 4.2, "samples": 128, "res": (640, 480)},
     "수렴 — 최종 해상도/샘플로 확정"),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    history = []
    prev_stats = None
    best = None

    for i, (override, why) in enumerate(ATTEMPTS, start=1):
        params = dict(BASE)
        params.update(override)
        label = f"iter{i}"
        path = os.path.join(OUT_DIR, f"{label}.png")

        print(f"\n{'='*68}\n[{label}] {why}\n{'='*68}")

        # --- BUILD ---
        scene = build(params)

        # --- CHECK (렌더 전에 걸러낸다) ---
        findings, summary = scenecheck.run(verbose=False)
        print(f"  CHECK      verdict={summary['verdict']} "
              f"errors={summary['errors']} warnings={summary['warnings']}")
        if summary["verdict"] == "fail":
            for f in findings:
                if f.severity == "error":
                    print(f"    {f}")
            print("  → 씬 검증 실패. 이 시도는 중단.")
            break

        # --- RENDER ---
        scene.render.filepath = path
        res = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in res:
            print(f"  RENDER     실패 {sorted(res)}")
            break
        print(f"  RENDER     {path}  "
              f"({params['res'][0]}x{params['res'][1]} @ {params['samples']}spp)")

        # --- MEASURE ---
        stats = imagecheck.analyze_image_file(path)
        delta = imagecheck.compare(prev_stats, stats) if prev_stats else None
        print(f"  MEASURE    mean={stats['mean_luma']:.4f} "
              f"contrast={stats['contrast_p01_p99']:.4f} "
              f"black={stats['black_fraction']*100:.1f}% "
              f"white={stats['white_fraction']*100:.1f}% "
              f"verdict={stats['verdict']}")
        if delta:
            print(f"             직전 대비 mean 변화 {delta['mean_luma']:+.4f} "
                  f"(상대 {delta['_relative_mean_luma']})")

        # --- ASSESS ---
        ok, reasons, _ = assess(stats)
        for r in reasons:
            print(f"             {'✓' if r.startswith('모든') else '→'} {r}")

        history.append({"iter": i, "why": why, "params": dict(override),
                        "mean_luma": stats["mean_luma"],
                        "contrast": stats["contrast_p01_p99"],
                        "verdict": stats["verdict"], "ok": ok, "path": path})
        if ok and best is None:
            best = history[-1]
            print("             ★ 목표 달성 — 이 설정을 베이스로 확정")

        if ok and delta and abs(delta["mean_luma"]) < STABLE_DELTA:
            print(f"             수렴 (변화 {delta['mean_luma']:+.4f} < {STABLE_DELTA}) — 반복 종료")
            break

        prev_stats = stats

    # --- 최종 보고 ---
    print(f"\n{'='*68}\n반복 요약\n{'='*68}")
    print(f"{'#':<3}{'mean':>9}{'contrast':>11}{'verdict':>10}  {'설명'}")
    for h in history:
        print(f"{h['iter']:<3}{h['mean_luma']:>9.4f}{h['contrast']:>11.4f}"
              f"{h['verdict']:>10}  {h['why']}")
    if best:
        print(f"\n최종 채택: iter{best['iter']}  {best['path']}")
        print(f"적용 파라미터: {best['params']}")
    else:
        print("\n목표를 달성한 시도가 없다. 위 표의 이유를 보고 파라미터를 손봐라.")
    return 0 if best else 1


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)

"""셰이더 텍스처링 템플릿 — 노이즈/러프니스/범프를 절차적으로 만들기.

에이전트가 "약간의 거칠기" "금속성 스크래치" 같은 요구를 받았을 때
바로 복사해서 쓸 수 있는 재현 가능한 패턴 모음.

사용법::

    blender -b --factory-startup -noaudio -P shader_texturing_template.py -- \\
        --out /tmp/tex.png --pattern brushed_metal

패턴 목록: ``plain``, ``brushed_metal``, ``worn_metal``, ``marble``,
``concrete``, ``emissive_core``, ``glass``
"""

import argparse
import os
import sys
import traceback

import bpy

_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE, os.path.join(_HERE, "scripts"), os.path.join(_HERE, "..", "scripts")):
    _cand = os.path.abspath(_cand)
    if os.path.isdir(os.path.join(_cand, "bkkit")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

from bkkit import compat, imagecheck, introspect, scenecheck  # noqa: E402


# --------------------------------------------------------------------------
# 노드 헬퍼
# --------------------------------------------------------------------------

def clear(mat):
    """기본 노드를 지우고 빈 트리로 만든다. 기본 Principled 를 쓰지 않으려면 필수."""
    mat.node_tree.nodes.clear()
    return mat.node_tree


def node(tree, idname, loc=(0, 0), **attrs):
    """``bl_idname`` 으로 노드를 만들고 위치를 지정한다."""
    n = introspect.new_node(tree, idname, location=loc)
    for k, v in attrs.items():
        setattr(n, k, v)
    return n


def set_in(n, name, value):
    """소켓을 이름으로 찾아 값을 넣는다. 없으면 False (예외 안 남)."""
    return introspect.set_input(n, name, value)


def coords(tree, loc=(-1400, 0)):
    """텍스처 좌표 노드 묶음 (Generated / Object / UV)."""
    tc = node(tree, "ShaderNodeTexCoord", loc)
    return tc


# --------------------------------------------------------------------------
# 패턴
# --------------------------------------------------------------------------

def pattern_plain(tree):
    out = node(tree, "ShaderNodeOutputMaterial", (400, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (100, 0))
    set_in(b, "Base Color", (0.6, 0.6, 0.62, 1.0))
    set_in(b, "Metallic", 0.9)
    set_in(b, "Roughness", 0.25)
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


def pattern_brushed_metal(tree):
    """방향성 있는 스크래치. Object 좌표 + 스케일 왜곡 + 매우 높은 Detail."""
    out = node(tree, "ShaderNodeOutputMaterial", (700, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (400, 0))
    tc = coords(tree)
    mapping = node(tree, "ShaderNodeMapping", (-1200, 0))
    set_in(mapping, "Scale", (1.0, 260.0, 1.0))     # Y 로 극단적으로 늘여 방향성 생성
    noise = node(tree, "ShaderNodeTexNoise", (-900, 0))
    set_in(noise, "Scale", 8.0)
    set_in(noise, "Detail", 8.0)
    set_in(noise, "Roughness", 0.75)
    ramp = node(tree, "ShaderNodeValToRGB", (-650, 0))
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.62
    bmp = node(tree, "ShaderNodeBump", (150, -350))
    set_in(bmp, "Strength", 0.12)
    set_in(bmp, "Distance", 0.002)

    tree.links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], b.inputs["Roughness"])
    tree.links.new(ramp.outputs["Color"], bmp.inputs["Height"])
    tree.links.new(bmp.outputs["Normal"], b.inputs["Normal"])
    set_in(b, "Base Color", (0.72, 0.73, 0.76, 1.0))
    set_in(b, "Metallic", 1.0)
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


def pattern_worn_metal(tree):
    """부식/마모. 두 개의 노이즈를 섞어 러프니스와 컬러를 흔든다."""
    out = node(tree, "ShaderNodeOutputMaterial", (900, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (600, 0))
    tc = coords(tree)
    n1 = node(tree, "ShaderNodeTexNoise", (-900, 200))
    set_in(n1, "Scale", 6.0); set_in(n1, "Detail", 12.0); set_in(n1, "Roughness", 0.6)
    n2 = node(tree, "ShaderNodeTexNoise", (-900, -250))
    set_in(n2, "Scale", 40.0); set_in(n2, "Detail", 8.0)
    mix = node(tree, "ShaderNodeMix", (-600, 0), data_type="FLOAT")
    rr = node(tree, "ShaderNodeMapRange", (-350, 0))
    set_in(rr, "From Min", 0.0); set_in(rr, "From Max", 1.0)
    set_in(rr, "To Min", 0.18); set_in(rr, "To Max", 0.75)
    bmp = node(tree, "ShaderNodeBump", (350, -400))
    set_in(bmp, "Strength", 0.25)

    tree.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    tree.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    tree.links.new(n1.outputs["Fac"], mix.inputs["Factor"])
    tree.links.new(n2.outputs["Fac"], mix.inputs[2])      # FLOAT A
    tree.links.new(mix.outputs[0], rr.inputs["Value"])
    tree.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    tree.links.new(n2.outputs["Fac"], bmp.inputs["Height"])
    tree.links.new(bmp.outputs["Normal"], b.inputs["Normal"])
    set_in(b, "Base Color", (0.55, 0.52, 0.48, 1.0))
    set_in(b, "Metallic", 1.0)
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


def pattern_marble(tree):
    """터블 노이즈 + 비선형 색보간."""
    out = node(tree, "ShaderNodeOutputMaterial", (800, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (500, 0))
    tc = coords(tree)
    noise = node(tree, "ShaderNodeTexNoise", (-600, 0))
    set_in(noise, "Scale", 4.0); set_in(noise, "Detail", 10.0); set_in(noise, "Roughness", 0.55)
    ramp = node(tree, "ShaderNodeValToRGB", (-300, 0))
    cr = ramp.color_ramp
    cr.elements[0].position = 0.38; cr.elements[0].color = (0.82, 0.80, 0.76, 1)
    cr.elements[1].position = 0.62; cr.elements[1].color = (0.16, 0.14, 0.13, 1)
    tree.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    set_in(b, "Roughness", 0.22)
    set_in(b, "Subsurface Weight", 0.12)
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


def pattern_concrete(tree):
    """다중 스케일 노이즈 + 범프."""
    out = node(tree, "ShaderNodeOutputMaterial", (800, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (500, 0))
    tc = coords(tree)
    big = node(tree, "ShaderNodeTexNoise", (-700, 200))
    set_in(big, "Scale", 3.0); set_in(big, "Detail", 6.0)
    fine = node(tree, "ShaderNodeTexNoise", (-700, -200))
    set_in(fine, "Scale", 60.0); set_in(fine, "Detail", 8.0)
    mix = node(tree, "ShaderNodeMix", (-420, 0), data_type="FLOAT")
    bmp = node(tree, "ShaderNodeBump", (200, -350))
    set_in(bmp, "Strength", 0.3); set_in(bmp, "Distance", 0.01)
    tree.links.new(tc.outputs["Object"], big.inputs["Vector"])
    tree.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    tree.links.new(big.outputs["Fac"], mix.inputs["Factor"])
    tree.links.new(fine.outputs["Fac"], mix.inputs[2])
    tree.links.new(mix.outputs[0], b.inputs["Roughness"])
    tree.links.new(mix.outputs[0], bmp.inputs["Height"])
    tree.links.new(bmp.outputs["Normal"], b.inputs["Normal"])
    set_in(b, "Base Color", (0.42, 0.41, 0.39, 1.0))
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


def pattern_emissive_core(tree):
    """중심이 빛나는 오브젝트. 프리뷰/아이콘 렌더에 유용."""
    out = node(tree, "ShaderNodeOutputMaterial", (700, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (350, 0))
    tc = coords(tree)
    grad = node(tree, "ShaderNodeTexGradient", (-500, 0), gradient_type="SPHERICAL")
    ramp = node(tree, "ShaderNodeValToRGB", (-250, 0))
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.1, 0.6, 1.0, 1)
    tree.links.new(tc.outputs["Generated"], grad.inputs["Vector"])
    tree.links.new(grad.outputs["Color"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], b.inputs["Emission Color"])
    set_in(b, "Emission Strength", 12.0)
    set_in(b, "Base Color", (0.02, 0.02, 0.03, 1.0))
    set_in(b, "Roughness", 0.3)
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


def pattern_glass(tree):
    """투과 유리. Cycles 에서 Transmission Weight 가 필요하다."""
    out = node(tree, "ShaderNodeOutputMaterial", (400, 0))
    b = node(tree, "ShaderNodeBsdfPrincipled", (100, 0))
    set_in(b, "Base Color", (0.92, 0.96, 0.95, 1.0))
    set_in(b, "Transmission Weight", 1.0)     # 4.x 이전의 "Transmission" 아님
    set_in(b, "Roughness", 0.03)
    set_in(b, "IOR", 1.45)
    tree.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return tree


PATTERNS = {
    "plain": pattern_plain,
    "brushed_metal": pattern_brushed_metal,
    "worn_metal": pattern_worn_metal,
    "marble": pattern_marble,
    "concrete": pattern_concrete,
    "emissive_core": pattern_emissive_core,
    "glass": pattern_glass,
}


# --------------------------------------------------------------------------
# 씬 + 렌더
# --------------------------------------------------------------------------

def build(pattern_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    world = bpy.data.worlds.new("World")
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    mat = bpy.data.materials.new("Pattern")
    clear(mat)
    PATTERNS[pattern_name](mat.node_tree)

    # 스피어 — UV/Generated/Object 좌표가 다 보이게 한다
    introspect.call_op("mesh.primitive_uv_sphere_add", radius=0.8,
                       location=(0, 0, 0.8), segments=96, ring_count=48)
    subj = bpy.context.object
    subj.name = "Subject"
    subj.data.materials.append(mat)
    introspect.call_op("object.shade_smooth_by_angle", angle=0.5236)

    # 스트라이프 바닥 — 러프니스 대비를 보기 위한 레퍼런스
    introspect.call_op("mesh.primitive_plane_add", size=40)
    gm = bpy.data.materials.new("CheckerMat")
    gnt = clear(gm)
    o = node(gnt, "ShaderNodeOutputMaterial", (400, 0))
    gb = node(gnt, "ShaderNodeBsdfPrincipled", (150, 0))
    gtc = coords(gnt)
    ck = node(gnt, "ShaderNodeTexChecker", (-200, 0))
    set_in(ck, "Color1", (0.02, 0.02, 0.02, 1.0))
    set_in(ck, "Color2", (0.65, 0.65, 0.65, 1.0))
    set_in(ck, "Scale", 12.0)
    gnt.links.new(gtc.outputs["Object"], ck.inputs["Vector"])
    gnt.links.new(ck.outputs["Color"], gb.inputs["Base Color"])
    set_in(gb, "Roughness", 0.5)
    gnt.links.new(gb.outputs["BSDF"], o.inputs["Surface"])
    bpy.context.object.data.materials.append(gm)

    # 조명: 넓은 키 + 스트립 하이라이트 (금속 반사를 읽기 위해)
    for name, loc, energy, size in (("Key", (3, -3, 4), 350.0, 4.0),
                                   ("Strip", (-3, 1.5, 2.2), 220.0, 1.0),
                                   ("Fill", (-2, -4, 2), 80.0, 5.0)):
        introspect.call_op("object.light_add", type="AREA", location=loc)
        lt = bpy.context.object
        lt.name = name
        lt.data.energy = energy
        lt.data.size = size
        from mathutils import Vector
        lt.rotation_euler = (Vector((0, 0, 0.8)) - lt.location).to_track_quat("-Z", "Y").to_euler()

    # 카메라: 피사체 전체가 프레임 안에 들어오도록 물러나서 3/4 앵글
    introspect.call_op("object.camera_add", location=(2.4, -4.6, 1.9))
    cam = bpy.context.object
    cam.rotation_euler = (Vector((0, 0, 0.72)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.camera.data.lens = 55.0

    compat.set_engine(scene, "CYCLES")
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 480, 360
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    return scene


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="shader_template", add_help=False)
    ap.add_argument("--pattern", default="brushed_metal", choices=sorted(PATTERNS))
    ap.add_argument("--out", default="/tmp/tex.png")
    ap.add_argument("--all", action="store_true", help="모든 패턴을 한 번에 렌더")
    known, _ = ap.parse_known_args(argv)

    todo = sorted(PATTERNS) if known.all else [known.pattern]
    results = []
    for name in todo:
        out = known.out.replace(".png", f"_{name}.png") if known.all else known.out
        scene = build(name)
        findings, summary = scenecheck.run(verbose=False)
        if summary["verdict"] == "fail":
            print(f"[{name}] 씬 검증 실패:")
            for f in findings:
                if f.severity == "error":
                    print("   ", f)
            results.append((name, None, "check-fail"))
            continue
        scene.render.filepath = out
        r = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in r:
            results.append((name, None, "render-fail"))
            continue
        st = imagecheck.analyze_image_file(out)
        imagecheck.print_stats(st, f"{name} -> {out}")
        results.append((name, st["verdict"], out))

    print("\n=== 요약 ===")
    for name, verdict, extra in results:
        print(f"  {name:16} {str(verdict):12} {extra}")
    return 0 if all(v != "bad" for _n, v, _e in results) else 1


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

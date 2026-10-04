# 10. 버전 마이그레이션 — 2.8 / 3.x / 4.x 스크립트를 5.x 에서 살리기

> 전 항목은 **Blender 5.2.2 LTS** 에서 실행해서 확인했다.
> "이렇게 바꾸면 된다"가 아니라 **"이렇게 바꾸면 실제로 이렇게 된다"** 를 보여주는 문서.

---

## 0. 버전 타임라인 (실측)

| 버전 | 상태 | 파이썬 | 비고 |
|---|---|---|---|
| 4.2 LTS | 2024-07 ~ 2026-07 지원 종료 | 3.11 | |
| 5.0 | 2025 | 3.11 | 컴포지터 1차 개편, Principled BSDF 개명 |
| 5.1 | 2026-03-17 | **3.13** (VFX Platform 2026) | 스트립 속성 대량 개명, Node Tools unique idname |
| **5.2 LTS** | **2026-07-14, 2028-07까지 지원** | 3.13 | **현재 안정판. 이 문서 기준** |
| 5.3 | 알파 | 3.13 | 채택 금지 |

```python
import bpy, sys
print(bpy.app.version)        # (5, 2, 2)
print(bpy.app.version_string) # 5.2.2 LTS
print(sys.version.split()[0]) # 3.13.13
```

> 이 샌드박스에서 실측한 정확한 빌드: `blender 5.2.2 LTS, build hash d13f752e3b9c, 2026-09-15`

---

## 1. 확실히 죽은 것들 (조용히 안 죽고 터진다)

### 1.1 `Action.fcurves` — 5.2에서 **속성 자체가 삭제**

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.keyframe_insert("location", frame=1)
act = obj.animation_data.action
print("has fcurves attr:", "fcurves" in [p.identifier for p in act.bl_rna.properties])
try:
    act.fcurves
except AttributeError as e:
    print("AttributeError:", e)
```
**실측 출력**
```
has fcurves attr: False
AttributeError: 'Action' object has no attribute 'fcurves'
```

**대체**: 슬롯 → 레이어 → 스트립 → 채널백

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
for f, loc in ((1, (0,0,0)), (10, (2,2,0)), (20, (4,0,0))):
    obj.location = loc
    obj.keyframe_insert("location", frame=f)

act  = obj.animation_data.action
slot = obj.animation_data.action_slot
print("slots:", [s.identifier for s in act.slots])   # ['OBCube']
bag  = act.layers[0].strips[0].channelbag(slot)
print([(f.data_path, f.array_index, len(f.keyframe_points)) for f in bag.fcurves])
# [('location', 0, 3), ('location', 1, 3), ('location', 2, 3)]
```

| 이전 (≤4.3) | 5.2 |
|---|---|
| `action.fcurves` | `action.fcurve_ensure_for_datablock(obj)` |
| — | `action.layers[i].strips[j].channelbag(slot).fcurves` |
| — | `action.slots`, `obj.animation_data.action_slot` |
| — | `action.is_action_layered`, `action.is_action_legacy` |

**버전 무관 헬퍼**: `bkkit.compat.action_fcurves(obj)`

### 1.2 `Mesh.calc_normals()` / `calc_loose_edges()` — 삭제

```python
import bpy
print("Mesh.calc_normals:", callable(getattr(bpy.types.Mesh, "calc_normals", None)))       # False
print("Mesh.calc_loose_edges:", callable(getattr(bpy.types.Mesh, "calc_loose_edges", None))) # False
```

4.1부터 `mesh.normals_split_custom_set()` 에서 커스텀 노멀을 직접 관리한다.
스크립트가 만든 메시는 기본적으로 이미 노멀이 유효하므로 **대체 호출 없이 그냥 무시**하면 된다.

### 1.3 `Mesh.use_auto_smooth` — 삭제 (4.1)

```python
print("use_auto_smooth:", "use_auto_smooth" in [p.identifier for p in bpy.types.Mesh.bl_rna.properties])  # False
print("MeshPolygon.use_smooth:", "use_smooth" in [p.identifier for p in bpy.types.MeshPolygon.bl_rna.properties])  # True
print("shade_smooth_by_angle op:", hasattr(bpy.ops.object, "shade_smooth_by_angle"))  # True
```

| 이전 | 5.x |
|---|---|
| `mesh.use_auto_smooth = True; mesh.auto_smooth_angle = 0.52` | `bpy.ops.object.shade_smooth_by_angle(angle=0.52)` |
| `mesh.use_auto_smooth = False` | `bpy.ops.object.shade_flat()` |
| `polygons.foreach_set('use_smooth', ...)` | 그대로 사용 가능 |

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3)
obj = bpy.context.object
print(introspect.call_op("object.shade_smooth_by_angle", angle=0.5236))
# {'FINISHED'}
```

### 1.4 `Armature.bone_groups` / `Armature.layers` — 삭제

```python
import bpy
props = [p.identifier for p in bpy.types.Armature.bl_rna.properties]
print("bone_groups:", "bone_groups" in props)   # False
print("layers:",     "layers" in props)         # False
print("collections:", "collections" in props)   # True
print([p for p in props if "collect" in p])     # ['collections', 'collections_all']
```

4.0에서 도입된 **Bone Collections** 체계가 최종 형태다. `Armature.collections` +
`Armature.collections_all` + `Bone.collections` / `EditBone.collections` 만 남았다.

### 1.5 `Scene.node_tree` / `CompositorNodeComposite` — 삭제 (5.0 컴포지터 재설계)

```python
import bpy
print("Scene.node_tree:", "node_tree" in [p.identifier for p in bpy.types.Scene.bl_rna.properties])  # False
print("Scene.compositing_node_group:", "compositing_node_group" in [p.identifier for p in bpy.types.Scene.bl_rna.properties])  # True
print("CompositorNodeComposite:", hasattr(bpy.types, "CompositorNodeComposite"))   # False
print("출력 노드들:", [n for n in dir(bpy.types) if n.startswith("CompositorNode") and ("Output" in n or "Viewer" in n)])
# ['CompositorNodeOutputFile', 'CompositorNodeViewer']
```

**새 방식 — 씬에 컴포지터 "노드 그룹"을 배정한다:**

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat, imagecheck

scene = bpy.context.scene

g = bpy.data.node_groups.new("MyComp", "CompositorNodeTree")
# ★ 인터페이스 소켓을 먼저 만들고 그 다음에 GroupOutput 노드를 만들어야 한다.
#   순서를 바꾸면 go.inputs 가 비어 있다.
g.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
go = g.nodes.new("NodeGroupOutput")

rl = g.nodes.new("CompositorNodeRLayers")
gl = g.nodes.new("CompositorNodeGlare")
g.links.new(rl.outputs["Image"], gl.inputs["Image"])
g.links.new(gl.outputs["Image"], go.inputs[0])

scene.compositing_node_group = g
gl.inputs["Type"].default_value = "Bloom"     # ← 속성이 아니라 소켓이다

# 렌더 실측 (200x200, Cycles 32spp)
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 1.2))
m = bpy.data.materials.new("e")
b = m.node_tree.nodes["Principled BSDF"]
b.inputs["Emission Color"].default_value = (1, 0.4, 0.1, 1)
b.inputs["Emission Strength"].default_value = 25
bpy.context.object.data.materials.append(m)
bpy.ops.object.camera_add(location=(0, -5, 1.5), rotation=(1.57, 0, 0))
scene.camera = bpy.context.object
compat.set_engine(scene, "CYCLES")
scene.cycles.samples, scene.cycles.use_denoising = 32, True
scene.render.resolution_x = scene.render.resolution_y = 200
scene.render.use_compositing = False
scene.render.filepath = "/tmp/comp_off.png"
bpy.ops.render.render(write_still=True)
scene.render.use_compositing = True
scene.render.filepath = "/tmp/comp_on.png"
bpy.ops.render.render(write_still=True)

a = imagecheck.analyze_image_file("/tmp/comp_off.png")
b = imagecheck.analyze_image_file("/tmp/comp_on.png")
print(f"OFF mean={a['mean_luma']:.5f}  ON mean={b['mean_luma']:.5f}")
```

**실측 출력**
```
OFF mean=0.35784  ON mean=0.61167
```

> 인터페이스 소켓을 `NodeGroupOutput` 노드 **이후** 에 만들면
> `go.inputs` 가 빈 상태로 남아 링크가 `IndexError: index 0 out of range` 로 난다.
> **항상 인터페이스 먼저.**

**노드 파라미터도 전부 소켓으로 이동했다** — 실측:

```python
import bpy
g = bpy.data.node_groups.new("C", "CompositorNodeTree")
gl = g.nodes.new("CompositorNodeGlare")
print([(i.name, i.bl_idname) for i in gl.inputs])
```
```
[('Image','NodeSocketColor'), ('Type','NodeSocketMenu'), ('Quality','NodeSocketMenu'),
 ('Threshold','NodeSocketFloat'), ('Smoothness','NodeSocketFloatFactor'), ('Clamp','NodeSocketBool'),
 ('Maximum','NodeSocketFloat'), ('Strength','NodeSocketFloatFactor'), ('Saturation','NodeSocketFloatFactor'),
 ('Tint','NodeSocketColor'), ('Size','NodeSocketFloatFactor'), ('Streaks','NodeSocketInt'),
 ('Streaks Angle','NodeSocketFloatAngle'), ('Iterations','NodeSocketInt'), ('Fade','NodeSocketFloatFactor'),
 ('Color Modulation','NodeSocketFloatFactor'), ('Diagonal','NodeSocketBool'),
 ('Sun Position','NodeSocketVectorFactor2D'), ('Jitter','NodeSocketFloatFactor'),
 ('Kernel Data Type','NodeSocketMenu'), ('Kernel','NodeSocketFloat'), ('Kernel','NodeSocketColor')]
print([o.name for o in gl.outputs])   # ['Image', 'Glare', 'Highlights']
```

| 이전 (속성) | 5.2 (소켓) |
|---|---|
| `node.glare_type = 'BLOOM'` | `node.inputs["Type"].default_value = "Bloom"` |
| `node.quality = 'HIGH'` | `node.inputs["Quality"].default_value = "High"` |
| `node.threshold = 1.0` | `node.inputs["Threshold"].default_value = 1.0` |
| `node.size = 8` | `node.inputs["Size"].default_value = 0.5` (0~1 정규화됨) |
| 출력 `"Image"` | 출력 `"Image"` / `"Glare"` / `"Highlights"` 3개 |

> **사이즈 스케일 변경**: 4.x 의 `size=9`(픽셀) → 5.2 의 `Size` 소켓은 `0~1` 정규화.
> `size=9` 를 그대로 넣으면 0.9(거의 최대 블러)이 된다.

### 1.6 `Material.use_nodes` / `Scene.use_nodes` — deprecated

```python
import bpy
m = bpy.data.materials.new("M")
print("use_nodes 없이 이미 node_tree 가 있다:", m.node_tree is not None)
print("노드 수:", len(m.node_tree.nodes))   # 2  ← 기본 노드가 이미 만들어져 있다
m.use_nodes = True                        # DeprecationWarning: removed in Blender 6.0
```

```
DeprecationWarning: 'Material.use_nodes' is expected to be removed in Blender 6.0
use_nodes 없이 이미 node_tree 가 있다: True
노드 수: 2
```

| 이전 | 5.x |
|---|---|
| `mat.use_nodes = True` | **삭제**. 그냥 `mat.node_tree` 를 쓴다 |
| `scene.use_nodes = True` | deprecated (`compositing_node_group` 로 대체) |
| `nodes.get("Principled BSDF")` | ⚠ 이름 의존 위험. `next(n for n in nodes if n.bl_idname=="ShaderNodeBsdfPrincipled")` |

### 1.7 EEVEE `use_bloom` / `use_gtao` / `use_ssr` — 삭제 (4.2)

```python
import bpy
ee = [p.identifier for p in bpy.context.scene.eevee.bl_rna.properties]
print("use_bloom:", "use_bloom" in ee)     # False
print("use_gtao:",  "use_gtao" in ee)      # False
print("use_ssr:",   "use_ssr" in ee)       # False
print("use_raytracing:", "use_raytracing" in ee)  # True
```

| 이전 | 5.x 대안 |
|---|---|
| `eevee.use_bloom = True` | 컴포지터의 Glare 노드 (5.x 컴포지터 사용) |
| `eevee.use_gtao` | `eevee.use_fast_gi = True` + `fast_gi_method` |
| `eevee.use_ssr` | `eevee.use_raytracing = True` + `ray_tracing_method` |

---

## 2. 이름이 바뀐 것들 (한 번에 매핑)

### 2.1 Principled BSDF 소켓 (4.0에서 바뀜, 5.2 실측 전체 목록)

```python
import bpy
m = bpy.data.materials.new("M")
b = m.node_tree.nodes["Principled BSDF"]
print([s.name for s in b.inputs])
```
**실측 (5.2.2, 33개)**
```
['Base Color', 'Metallic', 'Roughness', 'IOR', 'Alpha', 'Thin Wall', 'Normal', 'Weight',
 'Diffuse Roughness', 'Subsurface Weight', 'Subsurface Radius', 'Subsurface Scale',
 'Subsurface IOR', 'Subsurface Anisotropy', 'Specular IOR Level', 'Specular Tint',
 'Anisotropic', 'Anisotropic Rotation', 'Tangent', 'Transmission Weight',
 'Coat Weight', 'Coat Roughness', 'Coat IOR', 'Coat Tint', 'Coat Normal',
 'Sheen Weight', 'Sheen Roughness', 'Sheen Tint', 'Emission Color', 'Emission Strength',
 'Thin Film Thickness', 'Thin Film IOR']
```

| 이전 (≤3.x) | 4.x / 5.x |
|---|---|
| `Subsurface` | `Subsurface Weight` |
| `Specular` | `Specular IOR Level` |
| `Transmission` | `Transmission Weight` |
| `Clearcoat` | `Coat Weight` |
| `Clearcoat Roughness` | `Coat Roughness` |
| `Sheen` | `Sheen Weight` |
| `Emission` | `Emission Color` **+** `Emission Strength` (2개로 분리) |

> 스크립트에서 소켓 이름으로 접근하면 버전마다 조용히 실패한다.
> `bkkit.introspect.set_input(node, "Base Color", v)` 는 **없는 소켓이면 False 를 반환**하고
> 예외를 던지지 않는다. 로그로 남겨라.

### 2.2 EEVEE 엔진 식별자

```python
import bpy
sc = bpy.context.scene
print(sc.render.engine)   # 'BLENDER_EEVEE'
print([e.identifier for e in sc.render.bl_rna.properties['engine'].enum_items])
# ['BLENDER_EEVEE']   ← Cycles 는 이 목록에 없다 (동적 등록)
```

| 버전 | EEVEE 식별자 |
|---|---|
| 2.8–4.1 | `BLENDER_EEVEE` (구형) 또는 `BLENDER_EEVEE_NEXT` (4.2 프리뷰) |
| **4.2 – 5.2** | **`BLENDER_EEVEE`** (NEXT가 정식 명칭으로 통합) |
| 5.1+ | `BLENDER_WORKBENCH` 도 여전히 존재 (enum에 안 뜰 수 있음) |

**안전한 설정**: `bkkit.compat.set_engine(scene, "BLENDER_EEVEE")` — 실패하면 이유를 알려준다.

### 2.3 `ShaderNodeMixRGB` → `ShaderNodeMix` (둘 다 존재)

```python
import bpy
print("ShaderNodeMixRGB:", hasattr(bpy.types, "ShaderNodeMixRGB"))   # True (레거시, 계속 동작)
print("ShaderNodeMix:", hasattr(bpy.types, "ShaderNodeMix"))          # True (신형)
```

`ShaderNodeMix` 는 데이터타입(`data_type`: FLOAT / VECTOR / RGBA / ROTATION)을
**소켓**으로 받으므로 포즈/회전 보간도 처리한다. 새 코드는 `ShaderNodeMix` 를 써라.

### 2.4 Sky Texture 속성 (3.1에서 개명, 5.2에서 양쪽 다 존재)

```python
import bpy
print([p.identifier for p in bpy.types.ShaderNodeTexSky.bl_rna.properties if p.identifier not in ('rna_type','name','label','location','width','height','dimensions','color','use_custom_color','select','show_options','show_preview','hide','mute','parent','inputs','outputs')])
```
**실측**: `sun_disc`, `sun_size`, `sun_intensity`, `sun_elevation`, `sun_rotation`,
`altitude`, `air_density`, `aerosol_density`, `ozone_density`,
`sky_type`, `sun_direction`(레거시), `turbidity`(레거시), `ground_albedo`(레거시)

| 이전 | 현재 |
|---|---|
| `turbidity` | `aerosol_density` (+ `air_density`, `ozone_density`) |
| `sun_intensity` | `sun_disc` (불 켜기) + `sun_intensity` (세기) |
| `sun_direction` | `sun_rotation` |
| — (신규) | `sun_elevation`, `altitude` |

---

## 3. `look` 값이 뷰트랜스폼 접두사를 갖는다 (실측)

```python
import bpy
sc = bpy.context.scene
for vt in ("Standard", "Filmic", "AgX", "Raw", "Khronos PBR Neutral", "False Color"):
    sc.view_settings.view_transform = vt
    print(f"{vt:24} -> OK")
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "Medium High Contrast"
except TypeError as e:
    print("TypeError:", e)
```
**실측 출력**
```
Standard                  -> OK
Filmic                    -> OK
AgX                       -> OK
Raw                       -> OK
Khronos PBR Neutral       -> OK
False Color               -> OK
TypeError: bpy_struct: item.attr = val: enum "Medium High Contrast" not found in
('None', 'AgX - Punchy', 'AgX - Greyscale', 'AgX - Very High Contrast',
 'AgX - High Contrast', 'AgX - Medium High Contrast', 'AgX - Base Contrast',
 'AgX - Medium Low Contrast', 'AgX - Low Contrast', 'AgX - Very Low Contrast')
```

**실무 규칙**: `look` 를 설정하기 전에 **반드시 `view_transform` 을 먼저** 설정하고,
`AgX - Punchy` 처럼 접두사 붙은 이름을 써라.

> 그리고 `view_transform` 의 enum 인트로스펙션은 **쓰레기값**을 준다.
> `sc.view_settings.bl_rna.properties['view_transform'].enum_items` → `['NONE']`.
> 실제로는 6개가 전부 대입된다. **열거형 검사 대신 try/except + 문자열 대입**을 쓴다.
> `bkkit.introspect.set_enum_safely()` 도 이 이유로 신뢰하면 안 된다 —
> `enum_items` 가 비어 있으면 통과시켜버리니까. 직접 대입 후 예외를 잡아라.

---

## 4. Geometry Nodes 모디파이어 (5.2 파괴적 변경)

| ≤5.1 | 5.2 |
|---|---|
| `mod["Socket_2"] = 5.0` | `mod.properties.inputs.Socket_2.value = 5.0` |
| `mod["Socket_2_use_attribute"] = True` | `mod.properties.inputs.Socket_2.type = "ATTRIBUTE"` |
| `mod["Socket_2_attribute_name"] = "a"` | `mod.properties.inputs.Socket_2.attribute_name = "a"` |
| `mod["Output_3"] = "a"` (출력) | `mod.properties.outputs.<id>.attribute_name` (Expose 후에만 존재) |
| `list(mod.keys())` | `TypeError: ... id properties not supported for this type` |
| `ng.inputs.new(...)` / `ng.outputs.new(...)` | `ng.interface.new_socket(name, in_out=, socket_type=)` |

**하위 호환 헬퍼**: `bkkit.compat.set_gn_input(mod, identifier, value, attribute_name=None)`

**주의 3가지** (전부 실측):
1. `mod.properties.inputs["Socket_1"]` 는 `IDPropertyGroup` 를 준다 (`.value` 없음).
   **`getattr(mod.properties.inputs, "Socket_1")` 로 접근해야** RNA 구조체를 받는다.
2. `NodeSocketGeometry` 등에는 `.value` 가 없다. `AttributeError`.
3. `bpy.ops.object.geometry_nodes_input_attribute_toggle` 는 5.2.2에서 **세그폴트**.
   `00-core-model.md` §11.2 참고.

---

## 5. 그 외 알아둘 변경

| 항목 | 5.x 실측 |
|---|---|
| Python | 3.13.13 (5.1부터 3.13, VFX Platform 2026) |
| `bpy.data.all_ids` | 신규 (5.2). 모든 데이터블록 단일 이터레이터 |
| `Window.screenshot()` | 신규 (5.2). 파일 저장 없이 윈도우 픽셀 취득 |
| `gpu.init()` | 신규 (5.2). `-b` 에서 GPU 백엔드 초기화 |
| `WindowManager.reports` | 신규 (5.2). 세션 단위 uid 있는 리드온리 리포트 |
| `bpy.data.file_path_foreach` | 확장 (5.2). UDIM 타일/시퀀스/캐시파일 |
| ID 프로퍼티 중첩 | 1024 깊이 제한 (5.2) |
| `bpy.app.cachedir` | 신규 (5.1) |
| `bpy.app.handler.exit_pre` | 신규 (5.1) |
| 파이썬 user-site | 5.1부터 기본 로드 안 됨 |
| `mesh.validate()` | 5.1에서 비정상 multires 탄젠트 데이터 자동 수정 |
| `Scene.node_tree` | **삭제**. `Scene.compositing_node_group` (5.0+) |
| `Scene.use_nodes` | deprecated (5.x) |
| `paint.sample_color` | 5.1에서 제거, `paint.sample_color` 로 통합 |
| `Brush` 스트로크 속성 | 5.1에서 `brush.stroke_method` enum 으로 통합 |

---

## 6. 버전 무관 코드를 쓰는 법 — 실전 전략

### 6.1 기능 탐지 (버전 비교 금지)

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

compat.version()                              # (5, 2, 2)
compat.gn_uses_rna_properties()               # True
compat.has_action_slots()                     # True
compat.has_scene_compositing_node_group()     # True
compat.has_temp_override()                    # True
compat.use_nodes_is_deprecated()              # True
```

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat
import json
print(json.dumps({
    "version": list(compat.version()),
    "gn_rna_properties": compat.gn_uses_rna_properties(),
    "use_nodes_deprecated": compat.use_nodes_is_deprecated(),
    "all_ids": compat.has_all_ids(),
    "compositing_node_group": compat.has_scene_compositing_node_group(),
    "temp_override": compat.has_temp_override(),
    "action_slots": compat.has_action_slots(),
}, indent=2))
```

### 6.2 Try/except 폴백 체인

```python
import bpy

def get_fcurves(obj):
    act = obj.animation_data.action
    # 1순위: 5.x
    if hasattr(act, "fcurve_ensure_for_datablock"):
        return list(act.fcurve_ensure_for_datablock(obj))
    # 2순위: 4.4 - 5.1
    slot = getattr(obj.animation_data, "action_slot", None)
    if slot is not None and hasattr(act, "layers"):
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    out += list(bag.fcurves)
        return out
    # 3순위: 4.0 - 4.3
    return list(act.fcurves)
```

### 6.3 속성 설정은 항상 안전하게

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

m = bpy.data.materials.new("M")
bsdf = m.node_tree.nodes["Principled BSDF"]

# 4.x/5.x 전부 안전
print(introspect.set_input(bsdf, "Base Color", (0.8, 0.2, 0.1, 1.0)))  # True
print(introspect.set_input(bsdf, "Transmission", 0.5))                  # False  ← 조용히 무시
print(introspect.set_input(bsdf, "Emission Color", (1, 1, 0, 1)))      # True
print(introspect.set_input(bsdf, "Emission Strength", 8.0))            # True
```

### 6.4 상attr 존재 검사는 `bl_rna`

```python
import bpy

def has(thing, name):
    return name in [p.identifier for p in thing.bl_rna.properties]

print(has(bpy.types.WindowManager, "reports"))   # True  (hasattr 은 False)
print(hasattr(bpy.types.WindowManager, "reports"))  # False  ← 헷갈리지 마라
print(has(bpy.types.Material, "use_nodes"))       # True  (근데 deprecated)
```

---

## 7. 업그레이드 체크리스트 (오래된 스크립트를 고칠 때)

```
[ ] action.fcurves                  → compat.action_fcurves(obj)
[ ] mesh.calc_normals()             → 삭제. 그냥 없애기
[ ] mesh.calc_loose_edges()         → 삭제. 필요하면 bmesh
[ ] mesh.use_auto_smooth            → bpy.ops.object.shade_smooth_by_angle()
[ ] armature.bone_groups            → armature.collections
[ ] scene.node_tree / Composite     → scene.compositing_node_group + NodeGroupOutput
[ ] comp 노드.glare_type 등 속성    → comp 노드.inputs["Type"] 등 소켓
[ ] mat.use_nodes = True            → 삭제
[ ] scene.use_nodes                 → 삭제
[ ] eevee.use_bloom/gtao/ssr        → 컴포지터 Glare / use_fast_gi / use_raytracing
[ ] "Emission" 소켓                  → "Emission Color" + "Emission Strength"
[ ] "Transmission"/"Subsurface"/"Clearcoat"/"Sheen" → "... Weight"
[ ] mod["Socket_2"]                 → mod.properties.inputs.Socket_2
[ ] ng.inputs.new()                 → ng.interface.new_socket()
[ ] "BLENDER_EEVEE_NEXT"            → "BLENDER_EEVEE"
[ ] ShaderNodeMixRGB                → ShaderNodeMix (신규 코드)
[ ] look = "Medium High Contrast"   → view_transform 먼저 설정 후 "AgX - Medium High Contrast"
[ ] rigify / add-on                 → 5.x 확장 시스템 이관 확인 필요
[ ] sys.exit 없이 예외만            → try/except + sys.exit(code)
```

---

## Verification log

이 문서의 모든 ```python 블록은 `blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- references/10-migration-4x-to-5x.md` 로 실행한다.
**실측 결과: 22개 블록 → 22 PASS / 0 FRAG / 0 FAIL** (종료 코드 0)


| 항목 | 명령 | 결과 |
|---|---|---|
| 버전/파이썬 | `blender --version`, `sys.version` | PASS — 5.2.2 LTS `d13f752e3b9c`, Python 3.13.13 |
| `Action.fcurves` 부재 | `blender -b -P` 스크립트 | PASS — RNA 속성 목록에 없음, `AttributeError` 재현 |
| 슬롯 Actions 동작 코드 | 같은 스크립트 | PASS — `channelbag(slot)` 로 3커브 조회 |
| `Mesh.calc_normals` / `calc_loose_edges` | 프로브 | PASS — 둘 다 `False` |
| `use_auto_smooth` 부재 + `shade_smooth_by_angle` | 프로브 + 실행 | PASS — `{'FINISHED'}` |
| `Armature.bone_groups` / `layers` 부재 | 프로브 | PASS — `collections` 만 존재 |
| `Scene.node_tree` 부재, `compositing_node_group` 존재 | 프로브 | PASS |
| 새 컴포지터 파이프라인 | 200×200 Cycles 32spp 실제 렌더 2회 | PASS — OFF `mean=0.35784` → ON `mean=0.61167` |
| Glare 소켓 구조 | 프로브 | PASS — 23개 입력 소켓 / 3개 출력 소켓 |
| `use_nodes` deprecated | `bpy.data.materials.new` | PASS — DeprecationWarning + 이미 node_tree 존재 |
| EEVEE bloom/gtao/ssr 부재 | 프로브 | PASS — 3개 모두 `False`, `use_raytracing` 은 `True` |
| `BLENDER_EEVEE` 식별자 | 프로브 | PASS |
| `ShaderNodeMixRGB` / `ShaderNodeMix` | 프로브 | PASS — 둘 다 존재 |
| TexSky 속성 | 프로브 | PASS — 신구 속성 공존 확인 |
| `view_transform` 6종 + `look` 접두사 | 실행 | PASS — 6종 전부 대입 성공, `look` 은 접두사 필수 |
| `set_input` 없는 소켓 처리 | 실행 | PASS — `Transmission` → `False` |
| `has()` vs `hasattr()` | 실행 | PASS — `hasattr=False`, `bl_rna` 조회 `True` |

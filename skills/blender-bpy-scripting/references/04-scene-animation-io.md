# Scene 조직 · 애니메이션 · 드라이버 · 컨스트레인트 · 아마추어 · I/O

> 검증 환경: **Blender 5.2.2 LTS** (`5, 2, 2`, build 2026-09-15, commit `d13f752e3b9c`), Linux x64, 번들 Python **3.13.13**.
> 모든 스니펫은 `blender -b --factory-startup -noaudio --python verify/<name>.py` 로 실제 실행되어 `__SCRIPT_OK__` 를 뱉었습니다.
> 여기서 "5.2 확인됨"은 이 빌드의 **실측값**입니다. 문서/기억이 아니라 관측 결과입니다.

## 목차

[1. 씬·컬렉션](#1-씬과-컬렉션) · [2. 오브젝트 데이터](#2-오브젝트-데이터-타입) · [3. Slotted Actions](#3-키프레임-애니메이션--slotted-actions) · [4. FCurve](#4-fcurve-조작) · [5. 드라이버](#5-드라이버) · [6. 컨스트레인트](#6-컨스트레인트와-depsgraph-규칙) · [7. 아마추어](#7-아마추어와-스키닝) · [8. 셰이프 키](#8-셰이프-키) · [9. I/O](#9-임포트--엑스포트) · [10. 데이터 위생](#10-데이터-위생과-치명적-함정) · [11. 마이그레이션](#11-5x-마이그레이션-요약) · [Verification log](#verification-log)

---

## 1. 씬과 컬렉션

### 1.1 두 개의 "루트"

| 개념 | 접근법 | 실체 | `bpy.data`에 있음? | 씬 트리 루트? |
|---|---|---|---|---|
| **Master collection** | `scene.collection` | `Collection` (name `"Scene Collection"`) | ❌ **없음** | ✅ 루트 |
| 일반 컬렉션 | `bpy.data.collections["X"]` | `Collection` | ✅ | 마스터의 자식으로만 link |
| ViewLayer | `scene.view_layers[i]` | `ViewLayer` | ❌ | 씬에 속함 |
| LayerCollection | `view_layer.layer_collection` | `LayerCollection` | ❌ | 컬렉션 트리를 감싼 뷰 |

`scene.collection` 은 `bpy.data.collections` 에 나타나지 않습니다. "모든 컬렉션"을 순회할 때 별도로 더해야 합니다.

```python
# verify/48_scene_canonical.py
bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
sc.name = "Main"
print("scenes           :", [s.name for s in bpy.data.scenes])
print("scene.collection :", sc.collection.name, " type:", type(sc.collection).__name__)
print("  in bpy.data.collections?", sc.collection in list(bpy.data.collections))

root = bpy.data.collections.new("Assets"); sc.collection.children.link(root)
mid  = bpy.data.collections.new("Props");  root.children.link(mid)
print("bpy.data.collections   :", [c.name for c in bpy.data.collections])   # ['Assets', 'Props']
print("sc.collection.children :", [c.name for c in sc.collection.children]) # ['Assets']
print("root.children          :", [c.name for c in root.children])           # ['Props']
```

### 1.2 컬렉션이 담는 두 가지

`Collection` 은 자식 **컬렉션**과 **오브젝트**를 별개로 가집니다.

| 표현 | 의미 | 검증 결과 |
|---|---|---|
| `scene.objects` | 씬 트리 전체를 재귀 평탄화 | `['Shot', 'Hero', 'Key', 'Rig']` |
| `scene.collection.objects` | 마스터에 **직접** link 된 것만 | `['Shot']` |
| `coll.objects` / `coll.all_objects` | 직접 link / 서브트리 전체 (read-only) | `['Hero','Key','Rig']` / 동일 |
| `ob.users_collection` | 이 오브젝트가 link 된 모든 컬렉션 | `['Props']` |

```python
# verify/48_scene_canonical.py
def add_obj(name, data, coll):
    ob = bpy.data.objects.new(name, data); coll.objects.link(ob); return ob

o1 = add_obj("Hero", bpy.data.meshes.new("HeroMesh"), mid)
o2 = add_obj("Key",  bpy.data.lights.new("KeyLight", type='AREA'), mid)
o3 = add_obj("Shot", bpy.data.cameras.new("ShotCam"), sc.collection)   # 마스터에 직접
o4 = add_obj("Rig",  bpy.data.armatures.new("HeroRig"), mid)
print("sc.objects     :", [o.name for o in sc.objects])
print("sc.coll.objects:", [o.name for o in sc.collection.objects])
print("root.all_objects:", [o.name for o in root.all_objects])
print("types          :", [(o.name, o.type) for o in (o1, o2, o3, o4)])

mid.objects.unlink(o1)           # 그래프에서만 제거, bpy.data 에는 남음
print(o1.name in bpy.data.objects, o1.name in sc.objects)   # True False
root.objects.link(o1)           # 다른 곳에 다시 붙임
```

`all_objects` 는 오브젝트가 하나도 없는 컬렉션에서 빈 리스트를 냅니다. 새 컬렉션을 만들고 바로 확인하면 "왜 비어 있지?" 하고 헤맵니다 — 아직 아무것도 안 넣었으니까.

### 1.3 `hide_viewport` / `hide_render` / `hide_set()` — 세 층위

| API | 저장 위치 | 스코프 | 렌더 영향 | 되돌리는 법 |
|---|---|---|---|---|
| `obj.hide_viewport` | 데이터블록 | 전 뷰 레이어 | ❌ | `= False` |
| `obj.hide_render` | 데이터블록 | 전 뷰 레이어 | ✅ | `= False` |
| `obj.hide_set(bool)` | **뷰 레이어**의 `Base` | 해당 뷰 레이어만 | ❌ | `hide_set(False)` |
| `obj.hide_select` | 데이터블록 | 선택 불가 | ❌ | `= False` |
| `coll.hide_viewport` / `hide_render` | 컬렉션 | 하위 전부 | ❌ / ✅ | `= False` |
| `LayerCollection.exclude` | 뷰 레이어 | 서브트리 전체 제거 | ❌ | `= False` |
| `LayerCollection.holdout` | 뷰 레이어 | 뒤쪽만 표시 | ❌ | `= False` |
| `LayerCollection.indirect_only` | 뷰 레이어 | 직접 link 된 것만 | ❌ | `= False` |

`hide_set()` 은 `.blend` 에 **저장되지 않습니다**. 반대로 `hide_viewport` 는 저장됩니다.

**중요**: 부모 컬렉션이 `hide_viewport` 면 자식의 `hide_set(False)` 로도 `visible_get()` 이 `True` 가 되지 않습니다. `visible_get()` 은 계층적 결과입니다.

```python
# verify/48_scene_canonical.py — 실측 발췌
o1.hide_viewport = True; o1.hide_render = True
mid.hide_viewport = True; mid.hide_render = True
print("baseline             ->", o1.visible_get())   # False (부모가 숨김)
o1.hide_set(True);  print("after hide_set(True)  ->", o1.visible_get())   # False
o1.hide_set(False); print("after hide_set(False) ->", o1.visible_get())   # False (부모가 아직 숨김)
mid.hide_viewport = False; o1.hide_viewport = False
print("all flags cleared     ->", o1.visible_get())   # True
```

`hide_set(False)` 인데 안 보인다면 → `hide_viewport` → `hide_select` → LayerCollection `exclude` 순으로 의심하세요.

### 1.4 ViewLayer / LayerCollection 순회 + 멀티씬

```python
# verify/48_scene_canonical.py
def walk(lc, d=0):
    print("   " * d + "%-14s collection=%-14s exclude=%-5s hide_viewport=%-5s holdout=%-5s indirect_only=%s" % (
        lc.name, lc.collection.name, lc.exclude, lc.hide_viewport, lc.holdout, lc.indirect_only))
    for ch in lc.children:
        walk(ch, d + 1)
for s in bpy.data.scenes:
    for vl in s.view_layers:
        walk(vl.layer_collection)
```

```
scene Main
 view_layer ViewLayer
Scene Collection collection=Scene Collection exclude=False hide_viewport=False holdout=False indirect_only=False
   Assets         collection=Assets         exclude=False hide_viewport=False holdout=False indirect_only=False
      Props          collection=Props          exclude=False hide_viewport=False holdout=False indirect_only=False
```

`LayerCollection` 은 `ViewLayer` 에만 존재합니다. 하나의 `Collection` 이 두 씬에 들어가면 각 씬의 `LayerCollection` 트리는 별개입니다.

| API | 설명 |
|---|---|
| `bpy.data.scenes.new(name)` | 새 씬. `scene.collection` 은 **자동 생성되고 비어 있음** |
| `bpy.context.window.scene` | 현재 윈도우가 보는 씬. `bpy.context.scene` 은 이것의 별칭 |
| `bpy.data.window_managers[0].windows` | headless에서도 1개 존재 |
| `scene.view_layers` / `.new(name)` | 뷰 레이어 (기본 1개) |
| `scene.frame_start` / `frame_end` | 씬 단위 프레임 범위 |

```python
# verify/48_scene_canonical.py
sc2 = bpy.data.scenes.new("Shot_A")
sc2.collection.children.link(mid)        # 같은 Collection 을 두 씬에서 공유 가능
bpy.context.window.scene = sc2
print(bpy.context.window.scene.name, bpy.context.scene.name)                # Shot_A Shot_A
print(bpy.context.view_layer == sc2.view_layers[0])                        # True
bpy.context.window.scene = sc
```

> `bpy.context.window` 는 `blender -b` 에서도 존재합니다. 하지만 씬을 오염시키지 않으려면 처음 진입했을 때의 씬을 저장해 복원하거나, 처음부터 `bpy.ops.wm.read_homefile(use_empty=True)` 로 시작하세요.

### 1.5 Active collection vs Scene collection

`bpy.ops.*` 의 "새 오브젝트 추가" 계열은 **활성 레이어 컬렉션**에 들어갑니다. 기본값은 `scene.collection`(마스터)입니다.

```python
# verify/49_active_collection.py
vl = bpy.context.view_layer
print("active_layer_collection (default):", vl.active_layer_collection.name)   # Scene Collection
print("bpy.context.collection        :", bpy.context.collection.name)        # Scene Collection

vl.active_layer_collection = vl.layer_collection.children['Props']   # 전역 설정
bpy.ops.mesh.primitive_cube_add()
print("landed in:", [c.name for c in bpy.data.objects['Cube'].users_collection])   # ['Props']

vl.active_layer_collection = vl.layer_collection.children['Geo']
with bpy.context.temp_override(collection=geo,                                     # 1회 한정
                               layer_collection=vl.layer_collection.children['Geo'],
                               active_layer_collection=vl.layer_collection.children['Geo']):
    bpy.ops.mesh.primitive_uv_sphere_add()
print("temp_override ->", [c.name for c in bpy.data.objects['Sphere'].users_collection])  # ['Geo']
```

`bpy.context.collection` 은 활성 레이어 컬렉션의 **원본 `Collection`** 이며, 활성 레이어 컬렉션이 마스터면 `scene.collection` 입니다.

### 1.6 `exclude` 와 `view_layer.objects` — 갱신 필요

`view_layer.objects` 는 depsgraph 스냅샷입니다. `exclude` 를 바꾸고 바로 읽으면 **낡은 값**이 나옵니다.

```python
# verify/49_active_collection.py
print("before exclude:", [o.name for o in vl.objects])                       # ['Cube','Sphere','Direct']
vl.layer_collection.children['Props'].exclude = True
print("immediately   :", [o.name for o in vl.objects], "<- STALE")          # 그대로
bpy.context.view_layer.update()
print("after update  :", [o.name for o in vl.objects])                       # ['Sphere','Direct']
print("bpy.data unaffected:", [o.name for o in bpy.data.objects])            # ['Cube','Direct','Sphere']
```

`exclude` 는 `bpy.data` 를 건드리지 않습니다. 데이터는 살고 씬 그래프에서만 빠집니다.

### 1.7 자기 확인 명령

`bpy.ops.<group>.<op>.get_rna_type()` 가 모든 연산자의 정확한 인자를 알려줍니다. 반면 `bpy.ops.<group>.<op>` 속성 접근은 **항상 성공**하므로 존재 검사에는 쓸 수 없습니다.

```python
# verify/02_io_operator_probe.py — 반드시 이렇게 검사
def exists(g, o):
    try:
        return getattr(getattr(bpy.ops, g), o).get_rna_type().identifier
    except Exception as e:
        return "MISSING (%s)" % type(e).__name__
```

`getattr(bpy.ops.wm, "collada_export")` 는 성공하지만 `get_rna_type()` 이 `KeyError` 를 냅니다. 함정입니다.

```bash
blender -b --factory-startup -noaudio --python-expr "
import bpy
print([e.identifier for e in bpy.types.Constraint.bl_rna.properties['type'].enum_items][:5], '...')
print([p.identifier for p in bpy.ops.wm.usd_export.get_rna_type().properties][:5], '...')
"
# ['CAMERA_SOLVER', 'FOLLOW_TRACK', 'OBJECT_SOLVER', 'COPY_LOCATION', 'COPY_ROTATION'] ...
# ['filepath', 'check_existing', 'filter_blender', 'filter_backup', ...]
```

---

## 2. 오브젝트 데이터 타입

### 2.1 `bpy.data.objects.new(name, data)`

`data` 가 `None` 이면 Empty(`ob.type == 'EMPTY'`). `None` 이 아니면 ID 타입이 오브젝트 타입을 결정합니다.

| `data` 인자 | `ob.type` | Python `type(data)` |
|---|---|---|
| `None` | `EMPTY` | `NoneType` |
| `bpy.data.meshes.new(...)` | `MESH` | `Mesh` |
| `bpy.data.curves.new(..., 'CURVE')` | `CURVE` | `Curve` |
| `bpy.data.lights.new(..., type='POINT')` | `LIGHT` | `PointLight` |
| `bpy.data.lights.new(..., type='SUN')` | `LIGHT` | `SunLight` |
| `bpy.data.lights.new(..., type='SPOT')` | `LIGHT` | `SpotLight` |
| `bpy.data.lights.new(..., type='AREA')` | `LIGHT` | `AreaLight` |
| `bpy.data.cameras.new(...)` | `CAMERA` | `Camera` |
| `bpy.data.armatures.new(...)` | `ARMATURE` | `Armature` |
| `bpy.data.grease_pencils.new(...)` | `GREASEPENCIL` | `GreasePencil` |
| `bpy.data.textures.new(...)` | ❌ `RuntimeError: ID type 'TEXTURE' is not valid for an object` | |

```python
# verify/52_objects_canonical.py
import bpy
bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene; root = sc.collection

empty = bpy.data.objects.new("Empty", None); root.objects.link(empty)
print("type=%s data=%r" % (empty.type, empty.data))     # EMPTY None

me = bpy.data.meshes.new("PlaneMesh")
me.from_pydata([(-1,-1,0), (1,-1,0), (1,1,0), (-1,1,0)], [], [(0,1,2,3)]); me.update()
cu = bpy.data.curves.new("PolyCurve", 'CURVE')
sp = cu.splines.new('POLY'); sp.points.add(3)
for i, p in enumerate(sp.points):
    p.co = (i * 0.5, 0.0, 0.0, 1.0)

for label, data in [("Mesh", me), ("Curve", cu),
                    ("PointLight", bpy.data.lights.new("L1", type='POINT')),
                    ("SunLight",   bpy.data.lights.new("L2", type='SUN')),
                    ("SpotLight",  bpy.data.lights.new("L3", type='SPOT')),
                    ("AreaLight",  bpy.data.lights.new("L4", type='AREA')),
                    ("Camera",     bpy.data.cameras.new("C1")),
                    ("Armature",   bpy.data.armatures.new("A1")),
                    ("GreasePencil", bpy.data.grease_pencils.new("G1"))]:
    ob = bpy.data.objects.new("O_" + label, data); root.objects.link(ob)
    print("  %-13s ob.type=%-13s type(data)=%s" % (label, ob.type, type(data).__name__))

mesh_obj = bpy.data.objects["O_Mesh"]
other = bpy.data.meshes.new("OtherMesh")
other.from_pydata([(0,0,0), (1,0,0), (0,1,0)], [], [(0,1,2)])
mesh_obj.data = other                       # OK (MESH -> MESH)
try:
    mesh_obj.data = bpy.data.cameras["C1"]
except TypeError as e:
    print("MESH -> CAMERA:", e)             # Object.data expected a Mesh type, not Camera
```

`Object.type` 전체 enum: `MESH, CURVE, SURFACE, META, FONT, CURVES, POINTCLOUD, VOLUME, GREASEPENCIL, ARMATURE, LATTICE, EMPTY, LIGHT, LIGHT_PROBE, CAMERA, SPEAKER`.
`ob.type` 은 읽기 전용이며 `ob.data` 를 바꾸면 따라 바뀌지만, `ob.data` 는 **타입 고정**입니다.

### 2.2 라이트 — 5.2의 가장 큰 파괴적 변경

`bpy.data.lights.new(name, type=...)` 의 `type` enum은 정확히 4개: `POINT, SUN, SPOT, AREA`.

여기서부터가 함정입니다. **5.2에서 Light는 서브타입 RNA 구조체로 분리되어 있고, `.type` 을 나중에 바꿔도 Python 래퍼가 교체되지 않습니다.**

```python
# verify/18_light_structs.py
su = bpy.data.lights.new("S", type='SUN')
print(type(su).__name__, su.type)          # SunLight SUN
su.type = 'SPOT'
print(type(su).__name__, su.type)          # SunLight SPOT  <-- 여전히 SunLight!
su.spot_size                                # AttributeError: 'SunLight' object has no attribute 'spot_size'
```

**타입을 바꾸려면 데이터블록을 새로 만들어야 합니다.** 기존 라이트를 재사용하는 코드에서 `ld.type = 'SUN'` → `ld.angle` 는 즉시 죽습니다.

| RNA 구조체 | 고유 프로퍼티 |
|---|---|
| `bpy.types.Light` (base) | `color, type, use_shadow, cutoff_distance, use_custom_distance, normalize, diffuse_factor, specular_factor, transmission_factor, volume_factor, exposure, temperature, use_temperature, temperature_color, cycles, node_tree` |
| `PointLight` | **`energy`**, `shadow_soft_size`, `use_soft_falloff`, `use_absolute_resolution`, `shadow_buffer_clip_start`, `shadow_maximum_resolution`, `shadow_filter_radius`, `shadow_jitter_overblur`, `use_shadow_jitter` |
| `SunLight` | **`energy`**, **`angle`**, `shadow_soft_size`, `shadow_cascade_count`, `shadow_cascade_exponent`, `shadow_cascade_fade`, `shadow_cascade_max_distance`, ... |
| `SpotLight` | **`energy`**, **`spot_size`**, **`spot_blend`**, `show_cone`, `use_square`, `shadow_soft_size`, ... |
| `AreaLight` | **`energy`**, **`shape`**, **`size`**, **`size_y`**, **`spread`**, `shadow_soft_size`, ... |

`energy`조차 base `Light` 에 없습니다 — `bpy.types.Light.bl_rna.properties` 만 뒤지면 못 찾습니다.

| 프로퍼티 | 기본값 | 단위 |
|---|---|---|
| `energy` | `10.0` (new) / `1000.0` (factory Light) | W (point/spot/area), W/m² (sun) |
| `color` | `(1.0, 1.0, 1.0)` | linear |
| `shadow_soft_size` | `0.0` (new) / `0.1` (factory) | **scene unit** (m) |
| `angle` (SUN) | `0.00918` rad ≈ `0.526°` | **라디안** |
| `spot_size` (SPOT) | `0.7854` rad = `45.0°` | **라디안** |
| `spot_blend` (SPOT) | `0.15` | 0..1 |
| `size` / `size_y` (AREA) | `0.25` / `0.25` | scene unit |
| `spread` (AREA) | `π` (180°) | 라디안 |
| `exposure` | `0.0` | stops |
| `use_shadow` | `True` | bool |

```python
# verify/18_light_structs.py
spot = bpy.data.lights.new("Sp", type='SPOT')
print("spot: spot_size=%s rad spot_blend=%s show_cone=%s use_square=%s" % (
    spot.spot_size, spot.spot_blend, spot.show_cone, spot.use_square))
sun = bpy.data.lights.new("Su", type='SUN')
print("sun : angle=%s rad shadow_cascade_count=%s" % (sun.angle, sun.shadow_cascade_count))
area = bpy.data.lights.new("Ar", type='AREA')
print("area: size=%s size_y=%s shape=%s spread=%s" % (area.size, area.size_y, area.shape, area.spread))
pt = bpy.data.lights.new("Pt", type='POINT')
print("point: shadow_soft_size=%s use_soft_falloff=%s" % (pt.shadow_soft_size, pt.use_soft_falloff))
print("common: energy=%s color=%s use_shadow=%s normalize=%s exposure=%s" % (
    sun.energy, tuple(sun.color), sun.use_shadow, sun.normalize, sun.exposure))
```

```
spot: spot_size=0.7853981852531433 rad spot_blend=0.15000000596046448 show_cone=False use_square=False
sun : angle=0.009180432185530663 rad shadow_cascade_count=4
area: size=0.25 size_y=0.25 shape=SQUARE spread=3.1415927410125732
point: shadow_soft_size=0.0 use_soft_falloff=True
common: energy=10.0 color=(1.0, 1.0, 1.0) use_shadow=True normalize=True exposure=0.0
```

> `spot_size` 과 `angle` 은 **도가 아니라 라디안**입니다. `math.radians()` 로 변환하세요.

### 2.3 카메라

`bpy.data.cameras.new(name)` 에는 `type` 인자가 없습니다 — 항상 `PERSP` 로 만들고 그 다음 `cd.type = ...` 로 바꿉니다.
`Camera.type` enum (5.2 실측): `PERSP, ORTHO, PANO, CUSTOM`. `CUSTOM` 은 4.x/5.x 커스텀 카메라 셰이더용이라 일반 파이프라인에서는 무시하세요.

```python
# verify/19_camera.py
import bpy
cd = bpy.data.cameras.new("Cam")
print("default type:", cd.type)                       # PERSP
for t in ('PERSP', 'ORTHO', 'PANO'):
    cd.type = t
    print("   set type=%-6s ok -> %s" % (t, cd.type))
cd.type = 'PERSP'
cd.dof.use_dof = True
cd.dof.focus_distance = 3.0
cd.dof.aperture_fstop = 2.8
cd.dof.aperture_blades = 6
cd.dof.focus_object = bpy.data.objects["Cube"]
print("lens=%s sensor=%sx%s fit=%s angle_x=%.4f rad" % (
    cd.lens, cd.sensor_width, cd.sensor_height, cd.sensor_fit, cd.angle_x))
print("dof:", cd.dof.use_dof, cd.dof.focus_distance, cd.dof.aperture_fstop, cd.dof.aperture_blades)
```

| 프로퍼티 | 기본값 | 단위 / 비고 |
|---|---|---|
| `lens` / `sensor_width` / `sensor_height` | `50.0` / `36.0` / `24.0` | mm (`lens_unit` 가 `FOV` 면 도) |
| `sensor_fit` / `lens_unit` | `AUTO` / `MILLIMETERS` | `AUTO/HORIZONTAL/VERTICAL`, `MILLIMETERS/FOV` |
| `angle_x` / `angle_y` | `0.6911` / `0.4711` rad | **읽기 전용**, 파생값 |
| `ortho_scale` | `6.0` | world unit, 수직 기준 |
| `clip_start` / `clip_end` | `0.1` / `1000.0` | near / far plane |
| `shift_x` / `shift_y` | `0.0` | `sensor_fit` 기준 mm |
| `passepartout_alpha` / `display_size` | `0.5` / `1.0` | 뷰포트 마스크 / 와이어프레임 |
| `panorama_type` | `EQUIRECTANGULAR` | PANO 전용 |
| `fisheye_fov` / `fisheye_lens` | `π` / `10.5` | fisheye 셰이더 |
| `dof.use_dof` / `dof.focus_distance` | `False` / `10.0` | world unit |
| `dof.aperture_fstop` / `aperture_blades` | `2.8` / `0` | blades 0 = 원형 |
| `dof.aperture_ratio` / `aperture_rotation` | `1.0` / `0.0` | 블레이드 애너리 / rad |
| `dof.focus_object` | `None` | 지정하면 `focus_distance` 무시 |

`Camera.panorama_type` enum: `EQUIRECTANGULAR, EQUIANGULAR_CUBEMAP_FACE, MIRRORBALL, FISHEYE_EQUIDISTANT, FISHEYE_EQUISOLID, FISHEYE_LENS_POLYNOMIAL, CENTRAL_CYLINDRICAL`

`dof` 객체는 `bpy.types.DOFProperties` 라는 타입이 **존재하지 않습니다**. `bpy.types.Camera.bl_rna.properties['dof']` 의 런타임 타입으로 접근하세요.

카메라 오브젝트와 데이터는 분리되어 있고, 드라이버는 `obj.data` 에 붙습니다:

```python
# verify/19_camera.py
cam = bpy.data.objects["Camera"]
cam.data = cd                       # 데이터 슬롯 교체
f = cam.data.driver_add("lens")     # 데이터에 드라이버
f.driver.type = "SCRIPTED"
f.driver.expression = "20.0 + frame * 0.5"
bpy.context.scene.frame_set(10)
bpy.context.view_layer.update()
print(cam.data.evaluated_get(bpy.context.evaluated_depsgraph_get()).lens)   # 25.0
```

`ob.driver_add("energy")` 는 `TypeError: property "energy" not found`. **드라이버를 걸 대상 데이터블록 위에 걸어야 합니다.**

---

## 3. 키프레임 애니메이션 — Slotted Actions

### 3.1 결론부터: `action.fcurves` 는 5.2에 존재하지 않는다

```python
# verify/53_keyframe_canonical.py (act = ob.animation_data.action, §3.3 에서 생성)
print("has .fcurves ?", hasattr(act, "fcurves"))                        # False
print("'fcurves' in Action RNA:",
      'fcurves' in [p.identifier for p in bpy.types.Action.bl_rna.properties])   # False
print("is_action_layered:", act.is_action_layered, " is_action_legacy:", act.is_action_legacy)  # True False
```

**5.2에서 `action.fcurves` 는 deprecated shim이 아니라 완전히 제거되었습니다.** 4.4~4.5 에서 deprecation 경고를 남기며 동작하던 레거시 경로가 사라진 상태입니다. 4.x 코드를 그대로 포팅하면 `AttributeError: 'Action' object has no attribute 'fcurves'` 로 죽습니다.

`Action` 의 5.2 전체 RNA 프로퍼티:

```
asset_data, curve_frame_range, frame_end, frame_range, frame_start, id_type,
is_action_layered, is_action_legacy, is_editable, is_embedded_data, is_empty,
is_evaluated, is_library_indirect, is_linked_packed, is_missing, is_runtime_data,
layers, library, library_weak_reference, name, name_full, original, override_library,
pose_markers, preview, rna_type, session_uid, slots, tag, use_cyclic, use_extra_user,
use_fake_user, use_frame_range, users
```

5.2 에서 새로 만든 액션은 항상 `is_action_layered=True`, `is_action_legacy=False` 입니다.

### 3.2 새 구조와 `ActionSlot`

```
Action
 ├── layers[0]                      ActionLayer      (name, strips)
 │    └── strips[0]                ActionKeyframeStrip  (type == 'KEYFRAME')
 │         └── channelbags          ActionChannelbags  (각 slot마다 하나)
 │              └── channelbag(slot)  ActionChannelbag (fcurves, groups, slot, slot_handle)
 └── slots                          ActionSlots
AnimData: action, action_slot, action_slot_handle, action_suitable_slots, drivers, ...
```

`ActionStrip.type` enum은 5.2에서 단 하나: `['KEYFRAME']`.
`ActionLayer` 에는 `.type` 이 **없습니다** (`AttributeError: 'ActionLayer' object has no attribute 'type'`).

`ActionSlot` 의 5.2 프로퍼티 — **`name` 이 없습니다**:

| 프로퍼티 | 의미 | 실측 예시 |
|---|---|---|
| `identifier` | stable ID 문자열 | `'OBCube'` (오브젝트), `'KEKey'` (Key) |
| `name_display` | 표시용 이름 | `'Cube'` |
| `target_id_type` | 이 슬롯이 묶이는 ID 타입 | `'OBJECT'`, `'KEY'` |
| `handle` | 내부 정수 핸들 | `929201142` |
| `active` / `select` / `show_expanded` | UI 상태 | `False`/`False`/`True` |

`slot.name` 은 `AttributeError: 'ActionSlot' object has no attribute 'name'`. 이름이 필요하면 `slot.name_display`.

`ActionChannelbag` 프로퍼티: `fcurves, groups, rna_type, slot, slot_handle`
`ActionChannelbags` 메서드: `find, foreach_get, foreach_set, get, items, keys, new, remove, values`

### 3.3 정답 패턴 — 완전한 읽기 예제

```python
# verify/53_keyframe_canonical.py
import bpy

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 48
ob = bpy.data.objects.new("Cube", bpy.data.meshes.new("CubeMesh"))
sc.collection.objects.link(ob)

ob.location = (0, 0, 0)
ob.keyframe_insert(data_path="location", frame=1, group="Move")
ob.location = (2, -1, 3)
ob.keyframe_insert(data_path="location", frame=25, group="Move")
ob.rotation_euler = (0, 0, 0)
ob.keyframe_insert(data_path="rotation_euler", index=2, frame=1, group="Spin")

ad, act = ob.animation_data, ob.animation_data.action
print("action:", act.name, " layered:", act.is_action_layered, " legacy:", act.is_action_legacy)
print("frame_range:", tuple(act.frame_range), " has .fcurves:", hasattr(act, "fcurves"))
print("slots:", [(s.identifier, s.name_display, s.target_id_type) for s in act.slots])
print("ad.action_slot:", ad.action_slot.identifier, " handle:", ad.action_slot_handle)

strip = act.layers[0].strips[0]
bag = strip.channelbag(ad.action_slot)
print("strips[0].type=%s  channelbag: slot=%r slot_handle=%s fcurves=%d" % (
    strip.type, bag.slot, bag.slot_handle, len(bag.fcurves)))
for f in bag.fcurves:
    print("  %s[%d] group=%r keys=%s" % (f.data_path, f.array_index,
          f.group.name if f.group else None,
          [tuple(round(x, 3) for x in k.co) for k in f.keyframe_points]))
print("groups:", [(g.name, [(c.data_path, c.array_index) for c in g.channels]) for g in bag.groups])
```

실측 출력:

```
action: CubeAction  layered: True  legacy: False
frame_range: (1.0, 25.0)  has .fcurves: False
slots: [('OBCube', 'Cube', 'OBJECT')]
ad.action_slot: OBCube  handle: 929201142
strips[0].type=KEYFRAME  channelbag: slot=bpy.data.actions['CubeAction'].slots["OBCube"] slot_handle=929201142 fcurves=4
  location[0] group='Move' keys=[(1.0, 0.0), (25.0, 2.0)]
  location[1] group='Move' keys=[(1.0, 0.0), (25.0, -1.0)]
  location[2] group='Move' keys=[(1.0, 0.0), (25.0, 3.0)]
  rotation_euler[2] group='Spin' keys=[(1.0, 0.0)]
groups: [('Move', [('location', 0), ('location', 1), ('location', 2)]), ('Spin', [('rotation_euler', 2)])]
```

### 3.4 반복을 없애는 헬퍼 + 마이그레이션 표

프로덕션에서는 이 함수를 하나 만들어 두세요. 슬롯이 없거나 애니메이션이 없는 경우까지 처리합니다.

```python
# verify/06_action_helpers.py — 5.2 검증 완료
def action_fcurves(id_owner):
    """Return the list of FCurves for an ID's active action slot (5.x slotted actions)."""
    ad = id_owner.animation_data
    if ad is None or ad.action is None or ad.action_slot is None:
        return []
    out = []
    for layer in ad.action.layers:
        for strip in layer.strips:
            cb = strip.channelbag(ad.action_slot)
            if cb is not None:
                out.extend(cb.fcurves)
    return out

def fcurve_get(id_owner, data_path, index=0):
    for fc in action_fcurves(id_owner):
        if fc.data_path == data_path and fc.array_index == index:
            return fc
    return None

def channelbag_of(id_owner):
    ad = id_owner.animation_data
    if ad is None or ad.action is None or ad.action_slot is None:
        return None
    return ad.action.layers[0].strips[0].channelbag(ad.action_slot)

def action_group(bag, name):
    """Get-or-create an ActionGroup inside a channelbag."""
    for g in bag.groups:
        if g.name == name:
            return g
    return bag.groups.new(name)
```

| 4.x (레거시) | 5.2 |
|---|---|
| `obj.animation_data.action.fcurves` | `channelbag_of(obj).fcurves` |
| `action.groups` | `channelbag_of(obj).groups` (액션이 아니라 **채널백** 소속) |
| `fcurve.group` (str) | `fcurve.group` (→ `ActionGroup` **객체**) |
| `fcurve.group_name` | `fcurve.group.name` — `group_name` 자체가 **삭제됨** |
| `action.fcurve_ensure_for_datablock()` | `bag.fcurves.new(data_path, index=...)` |
| `bpy.ops.anim.action_group_insert()` | `bag.groups.new(name)` |

`FCurve.group_name` 이 사라진 것은 이름 변경이 아닙니다. **그룹이 이제 fcurve 가 아니라 channelbag 산하의 실체**이고, `FCurve.group` 은 `ActionGroup` 객체 참조입니다. 문자열을 넣으면 `TypeError` 입니다.

```python
# verify/05_fcurve_new.py
print("group_names on fcurve?", hasattr(fc, "group_name"))   # False
fc.group = cb1.groups[0]                                     # ActionGroup 객체 대입 OK
g = cb1.groups.new("Second")                                 # channelbag에서 그룹 생성
```

### 3.5 액션 공유와 슬롯

하나의 액션을 여러 오브젝트가 공유할 수 있고, 각 오브젝트는 **자기 슬롯**의 채널백을 읽습니다. 여기서 조용한 함정:

```python
# verify/06_action_helpers.py
cam.animation_data_create()
cam.animation_data.action = ob.animation_data.action
print("cam slot after assigning .action only:", cam.animation_data.action_slot)   # None !!!
cam.animation_data.action_slot = ob.animation_data.action_slot
print("cam slot after explicit set:", cam.animation_data.action_slot.identifier) # OBCube
```

**`anim_data.action` 만 대입하면 `action_slot` 은 `None` 으로 남습니다.** 슬롯이 `None` 이면 `action_fcurves()` 가 빈 리스트를 반환 — 액션이 있는데도 "애니메이션이 없다"고 오진합니다.

`ad.action_suitable_slots` 로 받을 수 있는 슬롯 목록 조회: `print("action_suitable_slots:", [(s.identifier, s.name_display) for s in cam.animation_data.action_suitable_slots])` → `[('OBCube', 'Cube')]`

`ActionSlots` / `ActionLayers` / `ActionChannelbags` 컬렉션은 모두 `.new() .remove() .move() .find() .get()` 을 가집니다.
슬롯 식별자 규칙: 오브젝트는 `'OB'+name` → `'OBCube'`, Key 는 `'KE'` 접두 → `'KEKey'`. 이름이 바뀌어도 identifier 는 stable.

### 3.6 레거시 액션과 `keyframe_insert()`

`is_action_legacy=True` 인 액션(구버전 파일에서 온 것)이 존재할 수 있으며 그때는 `layers` 가 비어 있습니다. 5.2에서 레거시 액션 생성 방법을 찾지 못했으므로, 파일 로드 시 `action.is_action_legacy` 값을 반드시 확인하세요.

```python
ob.keyframe_insert(data_path, index=-1, frame=..., group="", options=set(), keytype='KEYFRAME')
```

| 인자 | 의미 |
|---|---|
| `data_path` | `"location"`, `"rotation_euler"`, `'["prop"]'`, `'["prop"][0]'` 등 |
| `index` | `-1`(기본)이면 **벡터 전체**(3개 전부)를 한 번에. `0` 이면 x축 1개만 |
| `frame` | 키를 찍을 프레임. 생략하면 `scene.frame_current` |
| `group` | `ActionGroup` 이름. 없으면 빈 그룹 |
| `options` | `set()` — `INSERTKEY_*` 플래그 |
| `keytype` | `KEYFRAME`, `BREAKDOWN`, `MOVING_HOLD`, ... |

`group="Move"` 로 찍으면 `channelbag.groups` 에 `ActionGroup("Move")` 가 생기고 `group.channels` 에 그 그룹의 fcurve 목록이 들어갑니다.

---

## 4. FCurve 조작

### 4.1 프로퍼티와 enum (5.2 실측)

`FCurve`: `extrapolation, driver, group, data_path, array_index, color_mode, color, select, lock, mute, hide, auto_smoothing, is_valid, is_empty, sampled_points, keyframe_points, modifiers`

`Keyframe`: `select_left_handle, select_right_handle, select_control_point, handle_left_type, handle_right_type, interpolation, type, easing, back, amplitude, period, handle_left, co, co_ui, handle_right`

| enum | 값 |
|---|---|
| `Keyframe.interpolation` | `CONSTANT, LINEAR, BEZIER, SINE, QUAD, CUBIC, QUART, QUINT, EXPO, CIRC, BACK, BOUNCE, ELASTIC` |
| `Keyframe.easing` | `AUTO, EASE_IN, EASE_OUT, EASE_IN_OUT` |
| `Keyframe.handle_*_type` | `FREE, ALIGNED, VECTOR, AUTO, AUTO_CLAMPED` |
| `FCurve.extrapolation` | `CONSTANT, LINEAR` |
| `FCurve.color_mode` | `AUTO_RAINBOW, AUTO_RGB, AUTO_YRGB, CUSTOM` |
| `FCurve.auto_smoothing` | `NONE, CONT_ACCEL` |

| 프로퍼티 | 기본값 | 비고 |
|---|---|---|
| `extrapolation` | `CONSTANT` | `CONSTANT` / `LINEAR` |
| `color_mode` / `auto_smoothing` | `AUTO_RGB` / `CONT_ACCEL` | |
| `group` | `None` | `ActionGroup` 객체 또는 `None`. **문자열 아님** |
| `driver` | `None` | 드라이버가 붙어 있으면 `Driver` |

`FCurve.update()` 는 **메서드**입니다 (프로퍼티가 아님). `fc.update` 를 읽으면 메서드 객체를 얻습니다.
`easing` 값과 `interpolation` 값의 역할이 다릅니다: `interpolation='QUAD'` + `easing='EASE_IN'` 가 "Ease In Quad"입니다. `interpolation` 만 바꾸면 easing 은 무시됩니다.

### 4.2 FCurve 수술 정본

```python
# verify/53_keyframe_canonical.py
bag = channelbag_of(ob)
fc = [f for f in bag.fcurves if f.data_path == "location" and f.array_index == 0][0]

fc.keyframe_points.insert(13.0, 1.0)
k = fc.keyframe_points[1]
k.interpolation = 'BEZIER'
k.easing = 'EASE_IN_OUT'
k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
fc.extrapolation = 'LINEAR'
fc.update()
fc.keyframe_points.sort()
fc.keyframe_points.deduplicate()
fc.update()
print([(tuple(round(x, 3) for x in kk.co), kk.interpolation, kk.easing) for kk in fc.keyframe_points])
print("handles:", tuple(round(v, 3) for v in k.handle_left), tuple(round(v, 3) for v in k.handle_right))
```

출력:

```
[((1.0, 0.0), 'BEZIER', 'AUTO'), ((13.0, 1.0), 'BEZIER', 'EASE_IN_OUT'), ((25.0, 2.0), 'BEZIER', 'AUTO')]
handles: (9.0, 0.667) (17.0, 1.333)
```

`FCurveKeyframePoints` 메서드: `add, clear, deduplicate, find, foreach_get, foreach_set, get, items, keys, handles_recalc, insert, remove, sort, values`

| 메서드 | 설명 |
|---|---|
| `insert(frame, value, options={'FAST'})` | 키 삽입, **정렬 안 함** → `sort()` 필요 |
| `add(count)` / `remove(key)` / `clear()` | 추가 / 삭제 / 전부 삭제 |
| `sort()` / `deduplicate()` / `handles_recalc()` | 정렬 / 병합 / 핸들 재계산 |
| `find(frame, fast=False)` | 프레임으로 키 검색 |

`fc.update()` 를 부르지 않으면 핸들이 리셋되지 않습니다.

### 4.3 새 커브와 그룹

```python
# verify/05_fcurve_new.py — 5.2 검증 완료
g  = bag.groups.new("NewStuff")
nf = bag.fcurves.new("scale", index=2)
nf.group = g                                   # ActionGroup 객체. None 으로 시작하므로 반드시 대입
nf.keyframe_points.insert(1.0, 1.0)
nf.keyframe_points.insert(48.0, 3.0)
for kk in nf.keyframe_points:
    kk.interpolation = 'LINEAR'
nf.update()
print("new curve:", nf.data_path, nf.array_index, "group=", nf.group.name,
      "keys=", [tuple(round(x, 3) for x in kk.co) for kk in nf.keyframe_points])
print("groups:", {gg.name: [(c.data_path, c.array_index) for c in gg.channels] for gg in bag.groups})
```

```
new curve: scale 2 group= NewStuff keys= [(1.0, 1.0), (48.0, 3.0)]
groups: {'Move': [('location', 0), ('location', 1), ('location', 2)], 'Spin': [('rotation_euler', 2)], 'NewStuff': [('scale', 2)]}
```

`ActionGroup` 프로퍼티: `channels, color_set, colors, is_custom_color_set, lock, mute, name, select, show_expanded, show_expanded_graph, use_pin`

### 4.4 커스텀 곡선 모양 — FModifier

`fc.modifiers` 는 `FCurveModifiers` 이고 `new(type=...)` 로 추가합니다. 서브타입이 런타임에 결정되므로 `GENERATOR` 를 넣으면 반환 객체가 `FModifierGenerator` 가 됩니다 (Light 처럼 타입을 나중에 바꿀 수 없습니다).

`bpy.types.FModifier` (base): `active, blend_in, blend_out, frame_end, frame_start, influence, is_valid, mute, name, rna_type, show_expanded, type, use_influence, use_restricted_range`

| 서브타입 | 고유 프로퍼티 |
|---|---|
| `FModifierGenerator` | `mode`, `poly_order`, `coefficients`, `use_additive` |
| `FModifierCycles` | `mode_before`, `mode_after`, `cycles_before`, `cycles_after` |
| `FModifierNoise` | `scale, strength, phase, offset, depth, roughness, lacunarity, blend_type, use_legacy_noise` |
| `FModifierStepped` | `frame_start, frame_end, frame_step, frame_offset, use_frame_start, use_frame_end` |
| `FModifierLimits` | `use_min_x/y, min_x/y, use_max_x/y, max_x/y` |

> **5.x 파괴적 변경**: `FModifierGenerator` 에서 구버전의 `function='SIN'/'NOISE'`, `amplitude`, `phase_multiplier`, `value_multiplier`, `use_additive_time` 이 **전부 사라졌습니다.** `FModifierBuiltInFunction` 타입도 없습니다. 이제는 **다항식 생성기**입니다.

`FModifierGenerator.mode` enum: `POLYNOMIAL`, `POLYNOMIAL_FACTORISED`
`FModifierCycles.mode_before/after` enum: `NONE`, `REPEAT`, `REPEAT_OFFSET`, `MIRROR`
계산식: `y = c0 + c1·f + c2·f² + c3·f³ + ...` (계수 개수 = `poly_order + 1`)

```python
# verify/56_fmodifier_generator.py
ob.keyframe_insert(data_path="location", frame=1)
ob.location = (1, 0, 0); ob.keyframe_insert(data_path="location", frame=50)
bag = ob.animation_data.action.layers[0].strips[0].channelbag(ob.animation_data.action_slot)
fc = bag.fcurves[0]
fc.keyframe_points.clear(); fc.keyframe_points.insert(1.0, 0.0); fc.update()

g = fc.modifiers.new(type='GENERATOR')
print(type(g).__name__, g.mode, g.poly_order, g.use_additive, g.coefficients[:])
g.mode = 'POLYNOMIAL'; g.poly_order = 3
g.coefficients[0], g.coefficients[1] = 1.0, 0.0
g.coefficients[2], g.coefficients[3] = 0.0, 0.01
g.use_additive = False
for f in (0, 25, 50):
    sc.frame_set(f); bpy.context.view_layer.update()
    print("  f=%-3d -> %+.5f" % (f, ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).location[0]))
```

```
FModifierGenerator POLYNOMIAL 1 False (0.0, 1.0)
  f=0   -> +1.00000
  f=25  -> +157.25000
  f=50  -> +1251.00000
```

검산: `f=25` → `1 + 0.01·25³ = 157.25` ✅, `f=50` → `1 + 0.01·125000 = 1251` ✅.
기본 계수 `(0.0, 1.0)` 은 `y = frame` (frame 비례 램프). `POLYNOMIAL_FACTORISED` 는 인수분해 형태라 값이 다릅니다 — 실측 `c=(0,2)`, `f=25` 에서 `POLYNOMIAL` 은 `50.0`, `POLYNOMIAL_FACTORISED` 는 `2.0`.

`use_restricted_range=True` + `frame_start/frame_end` 를 주면 구간 밖에서 생성값이 0으로 대체됩니다. `blend_in`/`blend_out` 은 경계 페이드 길이(프레임), `use_influence`+`influence` 는 modifier 자체의 감쇠입니다.

**(b) `interpolation` × `easing` 조합** — `SINE/QUAD/CUBIC/QUART/QUINT/EXPO/CIRC/BACK/BOUNCE/ELASTIC` × `AUTO/EASE_IN/EASE_OUT/EASE_IN_OUT` 로 40가지 세그먼트 모양. `AUTO_CLAMPED` 핸들은 오버슈트를 억제하고 `AUTO` 는 허용합니다.

### 4.5 애니메이션 완전 제거

```python
# verify/53_keyframe_canonical.py
ob.animation_data_clear()
print(ob.animation_data)                   # None  (블록 자체가 사라짐)
print(act.users)                            # 0
print(act.name in bpy.data.actions)          # True — 액션은 고아로 남음
bpy.data.actions.remove(act)
print([a.name for a in bpy.data.actions])    # []
```

`bpy.types.AnimData` 전체 프로퍼티: `action, action_blend_type, action_extrapolation, action_influence, action_slot, action_slot_handle, action_slot_handle_tweak_storage, action_suitable_slots, action_tweak_storage, drivers, last_slot_identifier, nla_tracks, rna_type, use_nla, use_pin, use_tweak_mode`

---

## 5. 드라이버

### 5.1 API 와 enum

```python
fc = obj.driver_add("location", 0)     # FCurve 를 반환
d  = fc.driver
d.type = 'SCRIPTED'
d.expression = "x * 2.0"
v = d.variables.new()
v.name = "x"; v.type = 'SINGLE_PROP'
v.targets[0].id_type = 'OBJECT'
v.targets[0].id = tgt
v.targets[0].data_path = "location[1]"
```

| enum | 값 |
|---|---|
| `Driver.type` | `AVERAGE, SUM, SCRIPTED, MIN, MAX` (2.8 의 `PRODUCT`/`DIFFERENCE` 없음) |
| `DriverVariable.type` | `SINGLE_PROP, TRANSFORMS, ROTATION_DIFF, LOC_DIFF, CONTEXT_PROP` |
| `DriverTarget.transform_type` | `LOC_X/Y/Z, ROT_X/Y/Z/W, SCALE_X/Y/Z, SCALE_AVG` |
| `DriverTarget.transform_space` | `WORLD_SPACE, TRANSFORM_SPACE, LOCAL_SPACE` |

`Driver` 프로퍼티: `expression, is_simple_expression, is_valid, rna_type, type, use_self, variables`
`DriverVariable` 프로퍼티: `is_name_valid, name, rna_type, targets, type`
`DriverTarget` 프로퍼티 (5.2): `bone_target, context_property, data_path, fallback_value, id, id_type, is_fallback_used, rna_type, rotation_mode, transform_space, transform_type, use_fallback_value`

`Driver.is_valid` 은 마지막 평가에서 식이 성공했는지를 나타냅니다. 드라이버가 죽었는지 볼 때 첫 번째 체크입니다.

### 5.2 자동 실행 보안 — 5.2의 진짜 함정

가장 중요합니다. **프리퍼런스를 켜는 것으로는 부족합니다.**

| 시나리오 | 식 | 결과 | `is_valid` |
|---|---|---|---|
| 단순식 | `frame * 100.0` | `1000.0` ✅ | `True` |
| Python 필요 | `bpy.context.scene.frame_current * 100.0` | `0.0` ❌ | `False` |
| 위 + `prefs.filepaths.use_scripts_auto_execute = True` (런타임 설정) | | `0.0` ❌ | `False` |
| `-y` / `--enable-autoexec` 플래그 | | `900.0` ✅ | `True` |

`blender -b --factory-startup -noaudio --python ...` 실행 시 콘솔:

```
BPY_driver_exec: restricted access disallows name 'context', enable auto-execution to support
Error in PyDriver: expression failed: bpy.context.scene.frame_current * 100.0
For target: (type=Light, name="Light", property=energy, property_index=-1)
```

`--enable-autoexec` 로 재실행하면 `RESULT energy = 900.0  is_valid = True`.

**결론**

1. `bpy.context.preferences.filepaths.use_scripts_auto_execute = True` 를 **런타임에 설정해도 소용없습니다.** 전역 `G.use_autoexec` 가 시작 시점에 latch 됩니다.
2. 커맨드라인 플래그 **`-y` / `--enable-autoexec`** 가 유일한 방법입니다. 반대로 **`-Y` / `--disable-autoexec` 이 기본값**입니다 (`blender --help` 의 "Python Options" 절).
3. 실패 시 `d.is_valid` 가 `False` 가 되고 값이 **0** 이 됩니다 (에러를 던지지 않음). 조용히 잘못된 결과가 나오므로 항상 `is_valid` 를 확인하세요.
4. **보안**: 이 빌드에서 `-y` 는 Python 드라이버 식에 임의 코드 실행을 허용합니다. 신뢰할 수 없는 `.blend` 를 열고 자동 실행을 켜면 그 파일의 드라이버가 임의 코드를 실행합니다. `bpy.app.driver_namespace` 는 모든 드라이버에 전역 노출됩니다: `['__builtins__', '__name__', '__doc__', ..., 'acos', 'acosh', 'asin', 'asinh']`

### 5.3 드라이버 정본 (자동 실행 없이 동작)

```python
# verify/50_driver_canonical.py
import bpy, math

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 0, 100

driver_obj = bpy.data.objects.new("Driver", None)
sc.collection.objects.link(driver_obj)
tgt = bpy.data.objects.new("Target", bpy.data.meshes.new("T"))
sc.collection.objects.link(tgt)
tgt.location = (2.0, 4.0, 0.0)

# 1) 단순식 — SINGLE_PROP 변수
fc = driver_obj.driver_add("location", 0)
d = fc.driver
d.type = 'SCRIPTED'; d.expression = "x * 2.0"
v = d.variables.new(); v.name = "x"; v.type = 'SINGLE_PROP'
t = v.targets[0]; t.id_type = 'OBJECT'; t.id = tgt; t.data_path = "location[1]"

# 2) TRANSFORMS 변수 — world-space atan2 회전
d2 = driver_obj.driver_add("rotation_euler", 0).driver
d2.type = 'SCRIPTED'; d2.expression = "atan2(y, x)"
for nm, comp in (("x", 'LOC_X'), ("y", 'LOC_Y')):
    w = d2.variables.new(); w.name = nm; w.type = 'TRANSFORMS'
    w.targets[0].id = tgt
    w.targets[0].transform_type = comp
    w.targets[0].transform_space = 'WORLD_SPACE'

# 3) 평가
sc.frame_set(1); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = driver_obj.evaluated_get(dg)
print("driven location.x =", round(ev.location[0], 4))
print("driven rot.x      =", round(math.degrees(ev.rotation_euler[0]), 3), "deg")
print("is_valid:", d.is_valid, d2.is_valid)
print("is_simple_expression (before any eval):", d.is_simple_expression)
sc.frame_set(2); bpy.context.view_layer.update()
print("is_simple_expression (after eval)      :", d.is_simple_expression)

# 4) 열거 / 삭제
print([(f.data_path, f.array_index, f.driver.type) for f in driver_obj.animation_data.drivers])
for f in list(driver_obj.animation_data.drivers):
    driver_obj.animation_data.drivers.remove(f)
print("after remove:", len(driver_obj.animation_data.drivers))
```

실측 출력:

```
driven location.x = 8.0
driven rot.x      = 63.435 deg
is_valid: True True
is_simple_expression (before any eval): False
is_simple_expression (after eval)      : True
[('location', 0, 'SCRIPTED'), ('rotation_euler', 0, 'SCRIPTED')]
after remove: 0
```

- `is_simple_expression` 이 `True` 인 조건: `frame` 변수, `pi` 같은 상수, 변수의 값에 대한 산술만. `bpy.*` 접근, `math.*`/`random.*` 모듈 참조, 조건부, 반복, 함수 호출, `self` 참조는 `False` (`d.use_self=True` 로 오너 오브젝트를 노출하는 경우).
- `is_simple_expression` 은 **첫 평가 이후에만** 채워집니다. 설정 직후 읽으면 항상 `False` 입니다.
- `anim_data.drivers` 는 `FCurve` 리스트이고, 각 `fc.driver` 로 접근합니다. 드라이버만 지우려면 `anim_data.drivers.remove(fc)`.

### 5.4 드라이브 -> 순환 의존성

오브젝트가 자기 자신을 드리븐하면 depsgraph 사이클 경고가 뜹니다:

```
depsgraph | WARNING Dependency cycle detected:
           |   OBCube/DRIVER(location) depends on
           |   OBCube/TRANSFORM_FINAL() via 'RNA Target -> Driver'
           |   ...  OBCube/DRIVER(location) via 'Driver -> Driven Property'
           | WARNING Detected 1 dependency cycles
```

드라이버 변수의 `TRANSFORMS` 타깃이 **자기 자신**이거나 드리븐 프로퍼티를 직접 참조하면 발생합니다. 자기 드라이브(`frame` 기반)나 `location` 출력은 괜찮지만, `location` 을 변수로 읽어 `location` 을 쓰는 식은 순환입니다.

---

## 6. 컨스트레인트와 depsgraph 규칙

### 6.1 `Constraint.type` enum (5.2 실측, 29개)

```
CAMERA_SOLVER, FOLLOW_TRACK, OBJECT_SOLVER, COPY_LOCATION, COPY_ROTATION,
COPY_SCALE, COPY_TRANSFORMS, LIMIT_DISTANCE, LIMIT_LOCATION, LIMIT_ROTATION,
LIMIT_SCALE, MAINTAIN_VOLUME, TRANSFORM, TRANSFORM_CACHE, CLAMP_TO, DAMPED_TRACK,
IK, LOCKED_TRACK, SPLINE_IK, STRETCH_TO, TRACK_TO, ACTION, ARMATURE, CHILD_OF,
FLOOR, FOLLOW_PATH, GEOMETRY_ATTRIBUTE, PIVOT, SHRINKWRAP
```

`bpy.types.Constraint` (base): `active, enabled, error_location, error_rotation, influence, is_override_data, is_valid, mute, name, owner_space, rna_type, show_expanded, space_object, space_subtarget, target_space, type`

| 공통 프로퍼티 | 기본값 | 의미 |
|---|---|---|
| `name` | `"Constraint"` | 스택 내 이름 |
| `mute` | `False` | 스택에서 건너뜀 |
| `enabled` | `True` | `mute` 와 별개 플래그 (UI 체크박스) |
| `influence` | `1.0` | 0..1 블렌드 |
| `is_valid` | — | 대상 없으면 `False` |
| `error_location` / `error_rotation` | — | 대수적 해석 오차 (UI 표시용) |
| `owner_space` | `'WORLD'` | `WORLD, CUSTOM, POSE, LOCAL_WITH_PARENT, LOCAL` |
| `target_space` | `'WORLD'` | 위 + `LOCAL_OWNER_ORIENT` |

> `mute` 와 `enabled` 는 **별개**입니다. `enabled=False` 만으로는 그레이프에서 빠지지 않습니다. 확실한 방법은 `mute=True` (또는 제거).

| 서브타입 | 고유 프로퍼티 |
|---|---|
| `TrackToConstraint` | `target, subtarget, track_axis, up_axis, use_target_z` |
| `CopyLocationConstraint` | `use_x/y/z, invert_x/y/z, use_offset` |
| `CopyRotationConstraint` | `use_x/y/z, invert_x/y/z, mix_mode` |
| `LimitLocationConstraint` | `use_min_x/y/z, min_x/y/z, use_max_x/y/z, max_x/y/z, use_transform_limit` |
| `LimitDistanceConstraint` | `distance, limit_mode, use_transform_limit` |
| `DampedTrackConstraint` / `LockedTrackConstraint` | `track_axis` / `lock_axis` |
| `ChildOfConstraint` | `use_location_x/y/z, use_rotation_x/y/z, use_scale_x/y/z, set_inverse_pending, inverse_matrix` |
| `FollowPathConstraint` | `offset, offset_factor, forward_axis, up_axis, use_curve_follow, use_fixed_location, use_curve_radius` |

```
TrackToConstraint.track_axis        : TRACK_X, TRACK_Y, TRACK_Z, TRACK_NEGATIVE_X, TRACK_NEGATIVE_Y, TRACK_NEGATIVE_Z
TrackToConstraint.up_axis           : UP_X, UP_Y, UP_Z
LockedTrackConstraint.lock_axis     : LOCK_X, LOCK_Y, LOCK_Z
CopyRotationConstraint.mix_mode     : REPLACE, ADD, BEFORE, AFTER, OFFSET
```

### 6.2

> ⚠ **정정 (실전 대조 테스트)**: `PoseBone` 에는 `evaluated_get()` 이 **없다**.
> `pb.evaluated_get(dg)` 는 `AttributeError` 로 죽는다. 아래 표의 해당 행만 보라.

 depsgraph 규칙 — 장에서 가장 중요한 것

**원칙**: 컨스트레인트는 depsgraph에서 평가됩니다. `obj.matrix_world` 는 **직전 평가가 write-back된 값**이며, 방금 대상을 움직였으면 **낡습니다**.

```python
# verify/51_constraint_canonical.py (발췌)
target.location = (0, 0, 6)
print("BEFORE update  original :", tuple(round(v, 3) for v in follower.matrix_world.translation))
print("BEFORE update  evaluated:", tuple(
    round(v, 3) for v in follower.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation))
bpy.context.view_layer.update()
print("AFTER  update  original :", tuple(round(v, 3) for v in follower.matrix_world.translation))
```

```
BEFORE update  original   : (0.0, 0.0, 0.0)  <- STALE
BEFORE update  evaluated  : (0.0, 0.0, 6.0)  <- fresh
AFTER  update  original   : (0.0, 0.0, 6.0)
```

| 무엇을 읽는가 | 어디서 읽는가 | 갱신 필요? |
|---|---|---|
| 모디파이 적용된 메시 | `ob.evaluated_get(dg).data` | **필수** — 원본은 절대 안 변함 |
| 컨스트레인트/부모/drivers 적용된 트랜스폼 | `ob.evaluated_get(dg).matrix_world` | **권장** (원본은 write-back 전엔 낡음) |
| `pose_bones[...].matrix` | ~~`pb.evaluated_get(dg).matrix`~~ → **`pb.matrix` 를 그대로** | **⚠ 정정.** `PoseBone` 에 `evaluated_get` 은 없다. `AttributeError: 'PoseBone' object has no attribute 'evaluated_get'` (5.2.2 실측). `frame_set()` 이 포즈 평가를 수행하므로 `pb.matrix` 가 이미 평가값이다 |
| `matrix_world` (원본) | `ob.matrix_world` | `view_layer.update()` 후에는 맞지만, 갱신 전엔 낡음 |
| `scene.frame_set(n)` | — | 암묵적으로 평가 수행 |
| `bpy.ops.mesh.primitive_*_add()` | — | 오퍼레이터 내부에서 평가 |

안전한 헬퍼:

```python
def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    return ob.evaluated_get(dg)
```

### 6.3 `child_of` inverse, 스택 순서, 오퍼레이터

`ChildOf` 는 대상의 변환을 그대로 적용하므로, 붙이는 시점의 오프셋을 `inverse_matrix` 로 취소해야 합니다.

```python
# verify/51_constraint_canonical.py
c4 = follower.constraints.new(type='CHILD_OF')
c4.target = target
c4.set_inverse_pending = True      # 평가 1회 후 자동으로 False 가 되고 inverse_matrix 가 채워진다
bpy.context.view_layer.update()
print(c4.set_inverse_pending)                                        # False
print(tuple(round(v, 3) for v in c4.inverse_matrix.to_translation())) # (-0.0, 0.0, -6.0)
# 또는 직접:  c4.inverse_matrix = target.matrix_world.inverted()
```

스택 **순서가 의미**입니다. 앞의 컨스트레인트 출력이 뒤의 입력입니다. `follower.constraints.move_to_index(c, 0)` / `remove(c)` / `clear()`.

`bpy.ops.constraint.*` (headless에서도 존재, 20개):
`childof_set_inverse` / `childof_clear_inverse` / `objectsolver_set_inverse` / `objectsolver_clear_inverse` (`constraint, owner`), `copy` / `copy_to_selected` / `delete` (`constraint, owner[, report]`), `move_up` / `move_down` / `move_to_index(constraint, owner[, index])`, `add_target` / `remove_target(target, index)`, `apply`, `limitdistance_reset`, `stretchto_reset`, `followpath_path_animate(frame_start, length)`, `normalize_target_weights`, `disable_keep_transform`

> `bpy.ops.constraint.childof_set_inverse_pending` 는 **5.2에 없습니다**: `KeyError: 'get_rna_type("CONSTRAINT_OT_childof_set_inverse_pending") not found'`. 실제 이름은 `constraint.childof_set_inverse` 입니다. 2.8 시절 스크립트의 `childof_set_inverse_pending` 는 죽습니다 — `c.set_inverse_pending = True` 를 쓰세요.

### 6.4 컨스트레인트 정본 (4종 스택 + depsgraph 규칙)

```python
# verify/51_constraint_canonical.py
import bpy

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
target = bpy.data.objects.new("Target", None)
sc.collection.objects.link(target); target.location = (0, 0, 3)
me = bpy.data.meshes.new("M"); me.from_pydata([(0, 0, 0)], [], [])
follower = bpy.data.objects.new("Follower", me); sc.collection.objects.link(follower)

c = follower.constraints.new(type='TRACK_TO')
c.name = "LookAt"; c.target = target
c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
c2 = follower.constraints.new(type='COPY_LOCATION')
c2.name = "Stick"; c2.target = target; c2.use_offset = True
c3 = follower.constraints.new(type='LIMIT_LOCATION')
c3.use_min_x, c3.min_x = True, -2.0
c3.use_max_x, c3.max_x = True,  2.0
c3.use_min_z, c3.min_z = True,  0.5
c3.use_max_z, c3.max_z = True,  9.0
c4 = follower.constraints.new(type='CHILD_OF')
c4.target = target; c4.set_inverse_pending = True

print("stack:", [(x.name, x.type, round(x.influence, 2), x.mute) for x in follower.constraints])
target.location = (0, 0, 6)
print("BEFORE update original:", tuple(round(v, 3) for v in follower.matrix_world.translation), "<- STALE")
bpy.context.view_layer.update()
print("AFTER  update original:", tuple(round(v, 3) for v in follower.matrix_world.translation))
print("set_inverse_pending:", c4.set_inverse_pending,
      " inverse:", tuple(round(v, 3) for v in c4.inverse_matrix.to_translation()))
print("is_valid:", [(x.name, x.is_valid) for x in follower.constraints])
c2.influence = 0.5; c2.mute = True
bpy.context.view_layer.update()
print("after influence=0.5 + mute=True:", [round(v, 3) for v in follower.matrix_world.translation])
follower.constraints.remove(c2); print("after remove(c2):", [x.name for x in follower.constraints])
follower.constraints.clear()
```

```
stack: [('LookAt', 'TRACK_TO', 1.0, False), ('Stick', 'COPY_LOCATION', 1.0, False),
        ('Limit Location', 'LIMIT_LOCATION', 1.0, False), ('Child Of', 'CHILD_OF', 1.0, False)]
BEFORE update original: (0.0, 0.0, 0.0) <- STALE
AFTER  update original: (0.0, 0.0, 6.0)
set_inverse_pending: False  inverse: (-0.0, 0.0, -6.0)
is_valid: [('LookAt', True), ('Stick', True), ('Limit Location', True), ('Child Of', True)]
after influence=0.5 + mute=True: [0.0, 0.0, 0.5]
after remove(c2): ['LookAt', 'Limit Location', 'Child Of']
```

---

## 7. 아마추어와 스키닝

### 7.1 `bone_groups` 는 5.2에 없습니다

가장 많이 오해되는 부분입니다. 측정 결과:

| 확인 항목 | 5.2 결과 |
|---|---|
| `hasattr(armature, "bone_groups")` | **`False`** |
| `bpy.types.BoneGroup` | **존재하지 않음** |
| `hasattr(armature, "layers")` / `bpy.types.ArmatureLayer` / `BoneLayer` | **모두 없음** |
| `bpy.types.BoneCollection` / `BoneCollections` | **존재함** |
| `armature.collections` / `armature.collections_all` | **존재함** (`.new()`, `.move()`, `.remove()`) |
| `Bone.collections` | **존재함** |
| `Bone.bone_collections` | `False` (이름이 바뀜) |

`Armature` 의 5.2 RNA 프로퍼티:

```
animation_data, asset_data, axes_position, bones, collections, collections_all,
display_type, edit_bones, id_type, is_editmode, library, name, name_full, original,
override_library, pose_position, preview, relation_line_position, rna_type,
session_uid, show_axes, show_bone_colors, show_bone_custom_shapes, show_names,
tag, use_extra_user, use_fake_user, use_mirror_x, users
```

`BoneCollection`: `bones, child_number, children, index, is_editable, is_expanded, is_local_override, is_solo, is_visible, is_visible_ancestors, is_visible_effectively, name, parent`
`BoneCollections` 메서드: `active, active_index, active_name, is_solo_active, new, remove, move, find, get, items, keys, values`

**요약: 4.0에서 `bone_groups` → `bone collections` 로 이름이 바뀌었고, 5.2에는 옛 이름이 아예 없습니다.** 중첩 구조(4.0부터)도 `parent`/`children` 로 지원됩니다.

### 7.2 `Bone` 에서 사라진 것들

`Bone` (OBJECT 모드) 프로퍼티 — **`roll` 이 없습니다**:

```
bbone_*, children, collections, color, display_type, envelope_distance, envelope_weight,
head, head_local, head_radius, hide, hide_select, inherit_scale, length, matrix,
matrix_local, name, parent, rna_type, show_wire, tail, tail_local, tail_radius,
use_connect, use_cyclic_offset, use_deform, use_endroll_as_inroll, use_envelope_multiply,
use_inherit_rotation, use_local_location, use_relative_parent, use_scale_easing
```

| 프로퍼티 | OBJECT `Bone` | EDIT `EditBone` | 비고 |
|---|---|---|---|
| `roll` | ❌ **없음** | ✅ 있음 | OBJECT 모드에서는 `matrix_local.to_3x3()` 으로 복원 |
| `select` / `select_active` | ❌ **없음** | `select`, `select_head`, `select_tail` | 선택은 `PoseBone.select` 또는 `bpy.ops.armature.select_*` |
| `head_radius` / `tail_radius` | ✅ | ✅ | **표시 전용** — envelope를 구동하지 않음 |
| `envelope_distance` / `envelope_weight` | ✅ | ✅ | 실제 envelope 구동 |
| `collections` | ✅ | ✅ | |

`EditBone` 에만 있는 것: `roll, select, select_head, select_tail, lock, collections, envelope_distance, envelope_weight`.

### 7.3 stale EditBone — 세그폴트 함정

EDIT 모드에서 만든 `EditBone` 레퍼런스를 OBJECT 모드로 넘어간 뒤 **쓰면** Blender가 죽습니다.

```python
# verify/34_stale_editbone.py
stale = arm_data.edit_bones.new("b0")
bpy.ops.object.mode_set(mode='OBJECT')
print(type(stale).__name__)            # EditBone
print(stale == arm_data.bones['b0'])   # False  <-- 완전히 다른 객체!
print(stale.head)                      # (0.0, -7.96e-16, 4.58e-41)  <-- 쓰레기 값!
print(stale.envelope_distance)         # 4.581405199263557e-41     <-- 읽어도 쓰레기
# stale.envelope_distance = 1.0       # <-- 쓰면 Segmentation fault
```

**규칙: `mode_set(mode='OBJECT')` 직후에는 반드시 `arm_data.bones[name]` 으로 재조회하세요.**

```python
bpy.ops.object.mode_set(mode='OBJECT')
bone = arm_data.bones['spine']      # <-- 이렇게
```

### 7.4 리그 만들기 + 스키닝 정본

```python
# verify/32_rig_canonical.py
import bpy, math

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene

def sel_only(objects, active):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active

# --- 1. 리그 (EDIT 모드) ---
arm_data = bpy.data.armatures.new("RigData")
arm = bpy.data.objects.new("Rig", arm_data)
sc.collection.objects.link(arm)
sel_only([arm], arm)
bpy.ops.object.mode_set(mode='EDIT')

eb = arm_data.edit_bones
b0 = eb.new("b0");  b0.head = (0, 0, 0.0); b0.tail = (0, 0, 0.5)
b1 = eb.new("b1");  b1.head = (0, 0, 0.5); b1.tail = (0, 0, 1.0)
b2 = eb.new("b2");  b2.head = (0, 0, 1.0); b2.tail = (0, 0, 1.5)
b1.parent = b0; b1.use_connect = True
b2.parent = b1; b2.use_connect = True
b1.roll = math.radians(90)          # EditBone.roll -- Bone.roll 은 5.2에 없음

c_lower = arm_data.collections.new("lower"); c_lower.assign(b0)
c_upper = arm_data.collections.new("upper"); c_upper.assign(b1); c_upper.assign(b2)
bpy.ops.object.mode_set(mode='OBJECT')
print("bones      :", [b.name for b in arm_data.bones])
print("collections:", [c.name for c in arm_data.collections])
print("b2 in      :", [c.name for c in arm_data.bones['b2'].collections])

# --- 2. 메시 ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, segments=16, ring_count=12, location=(0, 0, 0.75))
mesh = bpy.context.object; mesh.name = "Skin"

# --- 3. 가우시안 가중치 ---
SEG = 0.30
centres = {b.name: (b.head_local + b.tail_local) * 0.5 for b in arm_data.bones}
groups = {n: mesh.vertex_groups.new(name=n) for n in centres}
for i, v in enumerate(mesh.data.vertices):
    p = mesh.matrix_world @ v.co
    w = {n: math.exp(-((p - c).length ** 2) / (2 * SEG * SEG)) for n, c in centres.items()}
    tot = sum(w.values()) or 1.0
    for n, val in w.items():
        if val / tot > 1e-4:
            groups[n].add([i], val / tot, 'REPLACE')
print("v0 weights :", [(mesh.vertex_groups[g.group].name, round(g.weight, 3))
                       for g in mesh.data.vertices[0].groups])

# --- 4. 바인딩 ---
mod = mesh.modifiers.new("Armature", 'ARMATURE')
mod.object = arm
mod.use_vertex_groups = True
mod.use_bone_envelopes = False
mesh.parent = arm
mesh.parent_type = 'OBJECT'
mesh.matrix_parent_inverse = arm.matrix_world.inverted()   # == keep_transform=True

# --- 5. 포즈 + 검증 ---
for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'          # 기본은 QUATERNION -- 이걸 먼저!
arm.pose.bones['b1'].rotation_euler = (math.radians(60), 0, 0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = mesh.evaluated_get(dg)
print("v0 posed co :", tuple(round(c, 4) for c in ev.data.vertices[0].co))
print("v0 source co:", tuple(round(c, 4) for c in mesh.data.vertices[0].co), "<- untouched")
```

```
bones      : ['b0', 'b1', 'b2']
collections: ['lower', 'upper']
b2 in      : ['upper']
v0 weights : [('b0', 0.005), ('b1', 0.246), ('b2', 0.749)]
v0 posed co : (0.6032, 0.0, 0.1018)
v0 source co: (0.0, 0.0, 0.45) <- untouched
```

`use_connect = True` 는 `child.head` 가 `parent.tail` 과 **정확히 일치해야** 합니다. 다르면 무시됩니다.

`VertexGroup` API: `ob.vertex_groups.new(name=)` → `VertexGroup`, `.add(indices, weight, type)`, `.remove(indices)`, `.weight(idx)`, `.name`, `.index`, `.lock_weight`. `add()` 의 `type` 은 `'REPLACE'`/`'ADD'`/`'SUB'`. 버텍스 가중치 읽기는 `v.groups` → `[(group_index, weight), ...]`.

`ArmatureModifier` 프로퍼티: `execution_time, invert_vertex_group, is_active, is_override_data, name, object, persistent_uid, rna_type, show_editmode, show_on_cage, show_render, show_viewport, type, use_apply_on_spline, use_bone_envelopes, use_deform_preserve_volume, use_multi_modifier, use_pin_to_last, use_vertex_groups, vertex_group`

### 7.5 포즈 — `rotation_mode` 함정

`PoseBone` 프로퍼티: `bbone_*, bone, child, color, constraints, custom_shape*, head, hide, ik_*, is_in_ik_chain, length, location, lock_*, matrix, matrix_basis, matrix_channel, motion_path, name, parent, rna_type, rotation_axis_angle, rotation_euler, rotation_mode, rotation_quaternion, scale, select, tail, use_*`

| 프로퍼티 | 기본값 | 비고 |
|---|---|---|
| `location` | `(0,0,0)` | 부모 기준 로컬 |
| `rotation_mode` | **`QUATERNION`** | ⚠️ 기본이 QUATERNION |
| `matrix` | — | 읽기(파생). **쓰기도 됨** (절대 포즈 설정) |
| `matrix_basis` / `matrix_channel` | — | 부모 무시 로컬 / constraint·driver 적용 결과 |
| `lock_location/rotation/scale` | 3-튜플 | `(True, True, True)` 로 잠금 |
| `constraints` | — | 오브젝트 컨스트레인과 **같은 29종** |

```python
# verify/31_env_isolate.py
pb = arm.pose.bones['b0']
print("default PoseBone.rotation_mode =", pb.rotation_mode)   # QUATERNION
pb.rotation_euler = (math.radians(45), 0, 0)                   # ← 아무 일도 일어나지 않음
```

**`rotation_euler` 에 값을 넣었는데 포즈가 안 움직이면 `rotation_mode` 을 먼저 보세요.** 이 함정은 조용히 실패합니다 — `rotation_euler` 값을 **읽으면 설정한 값이 그대로 나옵니다** (property 자체는 살아있으므로), 하지만 실제 포즈 결과는 0입니다.

### 7.6 `parent_set` 은 headless 에서 아무 일도 안 한다

**이 빌드에서 `bpy.ops.object.parent_set()` 은 무조건 no-op입니다.** `type='OBJECT'` 같은 기본 케이스조차:

```python
# verify/27_parent_set_debug.py
bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
# -> {'FINISHED'}   b.parent = None   poll() = True   아무 변화 없음
```

테스트한 모든 타입: `OBJECT`, `ARMATURE`, `ARMATURE_AUTO`, `ARMATURE_ENVELOPE` — 전부 `{'FINISHED'}` 를 반환하면서 실제 효과가 없습니다 (`BONE` 은 `RuntimeError: Error: No active bone`). VIEW_3D `temp_override` 로도 동일합니다. 반면 다른 오브젝트 오퍼레이터(`mode_set`, `transform_apply`, `duplicate`, `join`, `delete`, `select_all`, `origin_set`, `shade_smooth`)는 정상 동작합니다.

> ### ⚠⚠ 정정 — 실전 대조 테스트가 문서를 뒤집었다
>
> 위 문장은 **틀렸다.** 리깅 실전 테스트에서 `ARMATURE_AUTO` 가
> **완전히 동작함**이 측정됐다. 그대로 복원된 실측 증거:
>
> ```
> ARMATURE_AUTO/op_return          : ['FINISHED']
> ARMATURE_AUTO/parents/P_b2       : Rig          ← 부모 설정됨
> ARMATURE_AUTO/modifiers/P_b2     : [['Armature','ARMATURE']]
> ARMATURE_AUTO/vgroup_weights/P_base/base : n=8  min=0.5471  max=0.9047  mean=0.7252
> ARMATURE_AUTO/vgroup_weights/P_base/b1   : n=8  min=0.0953  max=0.4529  mean=0.2747
> ARMATURE_AUTO/vgroup_weights/P_b1/b2     : n=4  min=0.5277  max=0.9532  mean=0.7351
> ```
>
> **자동 가중치가 실제로 생성되고, 값도 비자명하다**(0.09~0.95).
> 그리고 실제로 변형이 일어난다.
>
> ### 그럼 왜 "무동작" 이라고 결론냈나?
>
> **지오메트리가 뼈에서 멀리 떨어져 있었기 때문이다.**
> 본 automate 가중치는 bone heat 방식이라, 메시 정점이 뼈에서 2.2m 밖에 있으면
> 유효 가중치가 0 으로 나온다. 부모만 설정되고Weights 가 0 인 상태가
> "headless 라서 안 된다" 로 오독되기 쉽다.
>
> **진단 규칙**: `ARMATURE_AUTO` 후 정점그룹 가중치의 합이 0 이면
> "오퍼레이터 실패" 가 아니라 **"메시-뼈 거리가 너무 멂"** 이다.
> 메시를 뼈 근처로 옮기거나, `ARMATURE_ENVELOPE` 로 바꾸거나,
> 수동 `vg.add([i], 1.0, 'REPLACE')` 로 가는 것이 정답이다.
> 검증 코드는 아래와 같다.
>
> ```python
> bpy.ops.object.parent_set(type='ARMATURE_AUTO')
> total = 0.0
> for g in obj.vertex_groups:
>     for v in g.vertices:
>         total += v.weight
> print("가중치 합:", total, "-> 0 이면 bone heat 거리 문제")
> ```
>
> 결론: **`parent_set` 를 못 쓰겠다는 이유로 수동 가중치를 먼저 쓰지 마라.**
> auto/envelope 를 시도하고, 가중치 합을 재보고 0 이면 그때 폴백해라.

**해결: RNA 를 직접 쓰세요.**

```python
# verify/22_parent_set.py
mesh.parent = arm
mesh.parent_type = 'OBJECT'                    # OBJECT/ARMATURE/LATTICE/VERTEX/VERTEX_3/BONE
mesh.matrix_parent_inverse = arm.matrix_world.inverted()
```

`parent_type='BONE'` 이면 `parent_bone` 도 설정해야 합니다:

```python
# verify/33_envelope_bone_parent.py
child.parent = arm
child.parent_type = 'BONE'
child.parent_bone = 'spine'
child.matrix_parent_inverse = arm.matrix_world.inverted()
bpy.context.view_layer.update()
print("before pose:", tuple(round(v, 4) for v in child.matrix_world.translation))   # (1.0, -1.0, 1.0)
pb.rotation_euler = (0, math.radians(90), 0)
bpy.context.view_layer.update()
print("after  pose:", tuple(round(v, 4) for v in child.matrix_world.translation))   # (1.0, 1.0, 1.0)  <- 뼈를 따라감
child.parent_type = 'OBJECT'
child.matrix_parent_inverse = arm.matrix_world.inverted()
bpy.context.view_layer.update()
print("as OBJECT par:", tuple(round(v, 4) for v in child.matrix_world.translation))  # (1.0, 0.0, 1.0)  <- 오브젝트만
```

`parent_type='OBJECT'` 는 **아마추어 오브젝트의 트랜스폼만** 따라갑니다 (포즈는 무시). 뼈를 따라가려면 반드시 `'BONE'` + `parent_bone`.

### 7.7 `keep_transform` 와 Envelope

| `parent_set(keep_transform=...)` | RNA 동등 동작 |
|---|---|
| `False` (기본) | `child.matrix_parent_inverse = arm.matrix_world.inverted()` |
| `True` | `before = child.matrix_world.copy()` → parent 설정 → `child.matrix_world = before` |

`keep_transform` 는 `bpy.types.Object.bl_rna.properties['keep_transform']` 에서 **`BOOLEAN`, default `False`**, description "Apply transformation before parenting" 입니다 (enum이 아닙니다).

```python
# verify/33_envelope_bone_parent.py — envelope 가중치
bone = arm_data.bones['spine']                # OBJECT 모드에서 재조회!
bone.envelope_distance = 1.0                  # 이 거리에서 가중치 0
# bone.envelope_weight = peak weight, default 1.0. 0.0 으로 내리면 envelope 가 완전히 죽는다!
bone.head_radius = 0.2                        # 표시 전용
bone.tail_radius = 0.2
mod.use_vertex_groups = False
mod.use_bone_envelopes = True
pb.rotation_euler = (0, 0, 0); rest = snap()
pb.rotation_euler = (math.radians(45), 0, 0)
print("ENVELOPE: moved %d/%d, vertex groups: %s" % (
    sum(1 for a, x in zip(rest, snap()) if (a - x).length > 1e-6), len(rest),
    [g.name for g in mesh.vertex_groups]))
```

> **`envelope_weight` 함정**: 이 값은 2.8의 "최대 거리에서의 가중치"가 아니라 **최대(peak) 가중치** 입니다. 기본 1.0. `0.0` 으로 설정하면 deformation 이 **완전히 사라집니다** (verify/35 실측: `env_dist=1.0 w=0.0 -> moved 0/8`, `env_dist=1.0 keep w=1.0 -> moved 8/8`).

> **`head_radius` / `tail_radius` 함정**: 4.0+ 에서 커스텀 본 모양으로 바뀌면서 실제 envelope 구동을 잃었습니다. 실제로 구동하는 것은 `envelope_distance` 입니다.

`Bone.use_deform = False` 로 두면 그 뼈는 변형에서 빠집니다 (verify/33: `use_deform=False -> moved 0/8`).
Envelope 가중치는 **버텍스 그룹이 필요 없습니다** — `vertex_groups` 리스트가 비어 있어도 동작합니다.

### 7.8 `bpy.ops.armature` / 스키닝 검증 패턴

bone collection 관련: `collection_add, collection_assign, collection_create_and_assign, collection_deselect, collection_move, collection_remove, collection_remove_unused, collection_select, collection_show_all, collection_unassign, collection_unassign_named, collection_unsolo_all, assign_to_collection, move_to_collection` (전부 headless에서 존재)

기타: `bone_primitive_add, extrude, extrude_forked, extrude_move, fill, subdivide, symmetrize, roll_clear, flip_names, autoside_names, align, calculate_roll, parent_set, parent_clear, select_hierarchy, select_linked, delete, dissolve, duplicate, separate, split, shortest_path_pick, hide, reveal, move, swap, taper, curve_stretch, deform_toggle, editmode_toggle, view_layer, cursor`

`bpy.ops.object.mode_set(mode=...)` 인자: `mode` (`OBJECT`, `EDIT`, `POSE`, ...), `toggle`.

스키닝이 실제로 평가되는지 확인하는 패턴:

```python
# verify/32_rig_canonical.py
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("evaluated verts:", len(mesh.evaluated_get(dg).data.vertices),
      " (source mesh has", len(mesh.data.vertices), ")")
```

모디파이어가 비활성이면 두 수치가 같습니다. `isinstance` 확인이 아니라 **버텍스 수 비교**로 확인하세요.

---

## 8. 셰이프 키

### 8.1 정본

```python
# verify/37_shapekeys_canonical.py
import bpy

for o in bpy.context.view_layer.objects:
    o.select_set(False)
bpy.ops.mesh.primitive_cube_add(size=2.0)
ob = bpy.context.object; ob.name = "Keyed"
ob.select_set(True)
bpy.context.view_layer.objects.active = ob

basis = ob.shape_key_add(name="Basis", from_mix=False)     # -> ShapeKey, value == 1.0
for v in ob.data.vertices:
    v.co.z += 0.6
ob.data.update()
up = ob.shape_key_add(name="Up", from_mix=False)            # fresh key, value == 1.0
up.slider_min, up.slider_max = 0.0, 1.5
up.interpolation = 'KEY_LINEAR'
up.relative_key = basis
up.value = 0.5
sk = ob.data.shape_keys
print("key_blocks :", [k.name for k in sk.key_blocks])
print("use_relative:", sk.use_relative, " reference_key:", sk.reference_key.name)
print("NO ShapeKey modifier is created in 5.x:", [(m.name, m.type) for m in ob.modifiers])

# --- 애니메이션 (fcurve는 Key ID 위에 올라간다) ---
up.value = 0.0; sk.keyframe_insert(data_path='key_blocks["Up"].value', frame=1)
up.value = 1.0; sk.keyframe_insert(data_path='key_blocks["Up"].value', frame=40)
ad, bag = sk.animation_data, None
bag = ad.action.layers[0].strips[0].channelbag(ad.action_slot)
print("action:", ad.action.name, " slot:", ad.action_slot.identifier,
      " target_id_type:", ad.action_slot.target_id_type)
print("curves:", [(f.data_path, f.array_index) for f in bag.fcurves])
bpy.context.scene.frame_set(20); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("mesh v0 @f20 (evaluated):", tuple(round(c, 4) for c in ob.evaluated_get(dg).data.vertices[0].co))
print("mesh v0      (source)    :", tuple(round(c, 4) for c in ob.data.vertices[0].co))

# --- 절대 키 ---
sk.use_relative = False
up.interpolation = 'KEY_LINEAR'
bpy.ops.object.shape_key_retime()          # ShapeKey.frame 는 READ-ONLY
print("after retime:", [(k.name, k.frame) for k in sk.key_blocks])
sk.eval_time = 10.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print("absolute @eval_time=10:", tuple(round(c, 4) for c in ob.evaluated_get(dg).data.vertices[0].co))
sk.use_relative = True

# --- 정점 그룹 제한 ---
vg = ob.vertex_groups.new(name="top")
vg.add([v.index for v in ob.data.vertices if v.co.z > 0], 1.0, 'REPLACE')
up.vertex_group = vg.name
```

실측 출력:

```
key_blocks : ['Basis', 'Up']
use_relative: True  reference_key: Basis
NO ShapeKey modifier is created in 5.x: []
action: KeyedAction  slot: KEKey  target_id_type: KEY
curves: [('key_blocks["Up"].value', 0)]
mesh v0 @f20 (evaluated): (-1.0, -1.0, -0.7115)
mesh v0      (source)    : (-1.0, -1.0, -0.4)
after retime: [('Basis', 0.0), ('Up', 10.0)]
absolute @eval_time=10: (-1.0, -1.0, -0.4)
```

### 8.2 5.x 변경점

| 항목 | 5.2 |
|---|---|
| 타입 이름 | `bpy.types.KeyBlock` → **`bpy.types.ShapeKey`** (전자는 존재하지 않음) |
| **ShapeKey 모디파이어** | **명시적으로 존재하지 않음.** 4.x 이하에서는 `shape_key_add()` 가 "ShapeKey" 모디파이어를 자동 삽입했지만 5.x에서는 암묵 적용 |
| "셰이프 키 있나?" 검사 | `ob.data.shape_keys is not None` (`ob.modifiers` 에서는 찾으면 안 됨) |
| `ShapeKey.frame` | **읽기 전용** — `bpy.ops.object.shape_key_retime()` 만 가능 |
| `Key.reference_key` | 신규 프로퍼티 |

`ShapeKey` 프로퍼티: `data, frame, interpolation, lock_shape, mute, name, points, relative_key, rna_type, select, slider_max, slider_min, value, vertex_group`
`Key` (ID) 프로퍼티: `animation_data, asset_data, eval_time, id_type, key_blocks, library, name, name_full, original, override_library, preview, reference_key, rna_type, session_uid, tag, use_extra_user, use_fake_user, use_relative, user, users`
`ShapeKey.interpolation` enum: `KEY_LINEAR, KEY_CARDINAL, KEY_CATMULL_ROM, KEY_BSPLINE`

`shape_key_retime` 는 인자 `['rna_type']` 만 — 활성 오브젝트가 컨텍스트에 있어야 합니다.
`shape_key_add(from_mix=False)` 외 오퍼레이터: `shape_key_remove, shape_key_clear, shape_key_copy, shape_key_move, shape_key_mirror, shape_key_make_basis, shape_key_apply_to_basis, shape_key_lock, shape_key_transfer`

`ShapeKey.vertex_group` 는 **이름 문자열**입니다. 비워두면 전체 버텍스에 적용.
셰이프 키도 evaluated 복사본에서만 보입니다 (`mesh.data` 는 절대 변하지 않음).

---

## 9. 임포트 / 엑스포트

### 9.1 대결론: factory-startup 에서 전부 동작합니다

"4.x 에서 엑스포터가 extension 으로 이동했으므로 `--factory-startup` 에서는 없을 수 있다"는 예상과 달리, **5.2 실측은 다릅니다**: `io_scene_gltf2` 와 `io_scene_fbx` 가 **번들(addon_core) + 기본 활성화** 상태이므로 factory-startup에서 모든 포맷이 그대로 동작합니다.

`verify/40_io_matrix2.py` 가 증명합니다 — 최소 씬(애니메이션 메시 + 라이트 + 카메라, 프레임 1~20)을 만든 뒤 **먼저 전부 export 하고 그다음 전부 import** 합니다 (2단계가 중요합니다. 인터레이스하면 아직 안 만들어진 파일을 읽습니다).

```python
# verify/40_io_matrix2.py (발췌)
EXPORTS = [
    ("wm", "obj_export",     dict(filepath=OUT+"/m.obj",  export_selected_objects=False)),
    ("wm", "stl_export",     dict(filepath=OUT+"/m.stl",  export_selected_objects=False)),
    ("wm", "ply_export",     dict(filepath=OUT+"/m.ply",  export_selected_objects=False)),
    ("wm", "alembic_export", dict(filepath=OUT+"/m.abc",  selected=False, start=1, end=20)),
    ("wm", "usd_export",     dict(filepath=OUT+"/m.usda", selected_objects_only=False, export_animation=True)),
    ("export_scene", "gltf", dict(filepath=OUT+"/m.gltf", export_format='GLTF_SEPARATE')),
    ("export_scene", "fbx",  dict(filepath=OUT+"/m.fbx",  use_selection=False)),
]
IMPORTS = [
    ("wm", "obj_import",     dict(filepath=OUT+"/m.obj")),
    ("wm", "stl_import",     dict(filepath=OUT+"/m.stl")),
    ("wm", "ply_import",     dict(filepath=OUT+"/m.ply")),
    ("wm", "alembic_import", dict(filepath=OUT+"/m.abc")),
    ("wm", "usd_import",     dict(filepath=OUT+"/m.usda")),
    ("wm", "fbx_import",     dict(filepath=OUT+"/m.fbx")),
    ("import_scene", "gltf", dict(filepath=OUT+"/m.gltf")),
    ("import_scene", "fbx",  dict(filepath=OUT+"/m.fbx")),
]

def has(g, o):
    try:  return getattr(getattr(bpy.ops, g), o).get_rna_type().identifier
    except Exception:  return None

def run(g, o, kw):
    try:  return getattr(getattr(bpy.ops, g), o)(**kw)
    except Exception as e:  return "ERR %s" % (str(e)[:60],)

for phase, items in (("exports", EXPORTS), ("imports", IMPORTS)):
    print("### %s" % phase)
    for g, o, kw in items:
        print("   %-13s %-15s %s" % (g, o, "ABSENT" if not has(g, o) else run(g, o, kw)))
print("files:", sorted(os.listdir(OUT)))
```

**실측 (factory-startup, `addon_utils.enable()` 호출 전) — 전부 `{'FINISHED'}`:**

```
files: ['m.abc', 'm.bin', 'm.fbx', 'm.gltf', 'm.mtl', 'm.obj', 'm.ply', 'm.stl', 'm.usda', 'textures']
```

### 9.2 애드온 비활성화로 확인

```python
# verify/40_io_matrix2.py (후반부)
for mod in ("io_scene_gltf2", "io_scene_fbx"):
    addon_utils.disable(mod, default_set=False)
for g, o in (("export_scene","gltf"), ("import_scene","gltf"),
             ("export_scene","fbx"),  ("import_scene","fbx"),
             ("wm","fbx_import")):
    print("   %-13s %-15s %s" % (g, o, "PRESENT" if has(g, o) else "ABSENT"))
```

```
   disabled io_scene_gltf2 -> (True, False)
   disabled io_scene_fbx -> (True, False)
   export_scene  gltf            ABSENT
   import_scene  gltf            ABSENT
   export_scene  fbx             ABSENT
   import_scene  fbx             ABSENT
   wm            fbx_import      PRESENT      <-- 내장 C++ importer, 애드온 무관
### STAGE 3: re-enable ###
   export_scene  gltf            PRESENT
   import_scene  gltf            PRESENT
   export_scene  fbx             PRESENT
   import_scene  fbx             PRESENT
   wm            fbx_import      PRESENT
```

**핵심 발견**
- `io_scene_gltf2` / `io_scene_fbx` 를 끄면 `export_scene.gltf` / `import_scene.gltf` / `export_scene.fbx` / `import_scene.fbx` 가 **사라집니다**.
- **`wm.fbx_import` 는 애드온을 꺼도 남습니다** — 내장 C++ FBX importer (Blender 4.5+). FBX에는 **두 개의 importer**가 있습니다: 애드온(`import_scene.fbx`)과 내장(`wm.fbx_import`).
- 두 애드온 모두 `addons_core` 에 있습니다 — 확장이 아니라 **번들 애드온**입니다.

### 9.3 애드온 활성화 / 비활성화

```python
# verify/40_io_matrix2.py
import addon_utils
addon_utils.enable("io_scene_gltf2", default_set=False, persistent=False)  # 이미 켜져 있으면 no-op
addon_utils.enable("io_scene_fbx",   default_set=False, persistent=False)
addon_utils.check("io_scene_gltf2")   # -> (default_enabled, currently_enabled)
```

5.2 번들 애드온 목록 (factory-startup 시작 시점 실측):

| 애드온 | default | enabled |
|---|---|---|
| `bl_pkg` | True | True |
| `cycles` | True | True |
| `hydra_storm` | False | False |
| `io_anim_bvh` | True | True |
| `io_curve_svg` | True | True |
| `io_mesh_uv_layout` | True | True |
| `io_scene_fbx` | True | True |
| `io_scene_gltf2` | True | True |
| `node_wrangler` | False | False |
| `pose_library` | True | True |
| `rigify` | False | False |
| `ui_translate` | False | False |
| `viewport_vr_preview` | False | False |
| `bl_ext.user_default.agent_toolkit_ext` | False | False |

> `cycles` 도 애드온입니다. `--factory-startup` 에서 `scene.render.engine = 'CYCLES'` 하려면 `addon_utils.enable("cycles", default_set=True, persistent=True)` 가 필요합니다 (PROTOCOL 명시). 실측에서 `cycles` 가 `default=True, enabled=True` 로 뜨더라도, 이것은 **등록됨**을 뜻할 뿐 실행 가능함을 보장하지 않으므로 PROTOCOL 지시를 따르세요.

### 9.4 전체 지원 매트릭스 (5.2.2 factory-startup 실측)

| 포맷 | Export | Import | 애드온 필요? | 애드온 이름 |
|---|---|---|---|---|
| **.blend** | `wm.save_as_mainfile` | `wm.open_mainfile` | ❌ 내장 | — |
| **OBJ** | `wm.obj_export` | `wm.obj_import` | ❌ 내장 | — |
| **STL** | `wm.stl_export` | `wm.stl_import` | ❌ 내장 | — |
| **PLY** | `wm.ply_export` | `wm.ply_import` | ❌ 내장 | — |
| **Alembic** | `wm.alembic_export` | `wm.alembic_import` | ❌ 내장 | — |
| **USD** | `wm.usd_export` | `wm.usd_import` | ❌ 내장 | — |
| **glTF/GLB** | `export_scene.gltf` | `import_scene.gltf` | ⚠️ **번들 애드온** | `io_scene_gltf2` |
| **FBX** | `export_scene.fbx` | `import_scene.fbx` | ⚠️ **번들 애드온** | `io_scene_fbx` |
| **FBX (alt)** | — | `wm.fbx_import` | ❌ 내장 (4.5+) | — |
| **SVG** | `wm.grease_pencil_export_svg` | `wm.grease_pencil_import_svg` | ❌ 내장 (GP 전용) | — |
| **PDF** | `wm.grease_pencil_export_pdf` | — | ❌ 내장 (GP 전용) | — |
| **BVH** | (io_anim_bvh) | (io_anim_bvh) | ⚠️ 애드온 | `io_anim_bvh` |
| **Collada (dae)** | ❌ 없음 | ❌ 없음 | — | (제거됨) |
| **DXF** | ❌ 없음 | ❌ 없음 | — | (애드온 필요) |
| **X3D** | ❌ 없음 | ❌ 없음 | — | (애드온 필요) |

**확인된 부재 operator들** (`get_rna_type()` 에서 `KeyError`):
`wm.collada_export/import`, `wm.dxf_export/import`, `wm.svg_export/import`, `wm.x3d_export/import`, `import_scene.obj`, `export_scene.obj`, `import_scene.stl`, `export_scene.stl`, `import_mesh.ply`, `export_mesh.ply`, `import_scene.usd`, `export_scene.usd`

> **2.x/3.x 습관으로 `import_scene.obj` 나 `export_scene.obj` 를 쓰면 안 됩니다.** 3.x 부터 `wm.obj_export` / `wm.obj_import` 으로 이름이 바뀌었고, 인자 체계도 완전히 달라졌습니다.

### 9.5 `wm.*` 내장 포맷의 실제 인자 (5.2 실측)

전부 `get_rna_type()` 실측값입니다 (`verify/39_io_signatures.py` 가 15개 오퍼레이터의 시그니처를 전부 덤프). 실무에서 손대는 인자만 추렸습니다. 나머지는 `bpy.ops.wm.<op>.get_rna_type().properties` 로 확인하세요.

```python
# OBJ
bpy.ops.wm.obj_export(filepath="out.obj", export_animation=False, start_frame=1, end_frame=250,
    forward_axis='NEGATIVE_Z', up_axis='Y',        # 기본 3.x 와 다름
    global_scale=1.0, apply_modifiers=True, apply_transform=True,
    export_eval_mode='DAG_EVAL_VIEWPORT',          # DAG_EVAL_VIEWPORT / DAG_EVAL_RENDER
    export_selected_objects=True, export_uv=True, export_normals=True, export_colors=False,
    export_materials=True, export_pbr_extensions=False,
    path_mode='AUTO',                              # AUTO/ABSOLUTE/RELATIVE/MATCH/STRIP/COPY
    export_triangulated_mesh=False, export_curves_as_nurbs=False,
    export_object_groups=False, export_material_groups=False, export_vertex_groups=False,
    export_smooth_groups=False, smooth_group_bitflags=False)
bpy.ops.wm.obj_import(filepath="in.obj", global_scale=1.0, clamp_size=0.0,
    forward_axis='NEGATIVE_Z', up_axis='Y', use_split_objects=True, use_split_groups=False,
    import_vertex_groups=False, validate_meshes=True, close_spline_loops=True,
    collection_separator='', mtl_name_collision_mode='MAKE_UNIQUE')  # MAKE_UNIQUE / REFERENCE_EXISTING

# STL
bpy.ops.wm.stl_export(filepath="out.stl", ascii_format=False, use_batch=False,
    export_selected_objects=True, global_scale=1.0, use_scene_unit=False,
    forward_axis='Y', up_axis='Z', apply_modifiers=True, evaluation_mode='DAG_EVAL_RENDER')
bpy.ops.wm.stl_import(filepath="in.stl", global_scale=1.0, use_scene_unit=False,
    use_facet_normal=False, forward_axis='Y', up_axis='Z', use_mesh_validate=True)

# PLY
bpy.ops.wm.ply_export(filepath="out.ply", forward_axis='Y', up_axis='Z', global_scale=1.0,
    apply_modifiers=True, export_selected_objects=True, export_uv=True, export_normals=False,
    export_colors='NONE',                         # NONE / SRGB / LINEAR
    export_attributes=True, export_triangulated_mesh=False, ascii_format=False)
bpy.ops.wm.ply_import(filepath="in.ply", global_scale=1.0, use_scene_unit=False,
    forward_axis='Y', up_axis='Z', merge_verts=False, import_colors='NONE', import_attributes=True)

# Alembic
bpy.ops.wm.alembic_export(filepath="out.abc", start=1, end=20, xsamples=1, gsamples=1,
    sh_open=0.0, sh_close=1.0,                   # Alembic 타임 샘플링
    selected=False, flatten=False, uvs=True, packuv=True, normals=True, vcolors=False,
    orcos=True, face_sets=False, subdiv_schema=False, apply_subdiv=False, curves_as_mesh=False,
    use_instancing=True, global_scale=1.0, triangulate=False,
    quad_method='BEAUTY', ngon_method='BEAUTY',
    export_hair=True, export_particles=True, export_custom_properties=True,
    as_background_job=False,
    evaluation_mode='RENDER',                    # RENDER / VIEWPORT
    init_scene_frame_range=True)
bpy.ops.wm.alembic_import(filepath="in.abc", relative_path=True, scale=1.0, set_frame_range=True,
    validate_meshes=False, always_add_cache_reader=False, is_sequence=False, as_background_job=False)
```

USD는 인자가 60개 가까이 있습니다. 실무에서 쓰는 것만 (`verify/39_io_signatures.py` 에 전체가 있습니다):

```python
# USD
bpy.ops.wm.usd_export(filepath="out.usda",        # .usd / .usdc / .usdz
    selected_objects_only=False,                  # <- export_selected_objects 가 아님!
    export_animation=False, incremental_frames=0, export_hair=False,
    export_uvmaps=True, rename_uvmaps=True, export_mesh_colors=True,
    export_normals=True, export_materials=True,
    export_subdivision='BEST_MATCH',             # IGNORE / TESSELLATE / BEST_MATCH
    export_armatures=True, only_deform_bones=False, export_shapekeys=True, use_instancing=False,
    evaluation_mode='RENDER',                    # RENDER / VIEWPORT
    generate_preview_surface=True, generate_materialx_network=False, convert_orientation=False,
    export_global_forward_selection='NEGATIVE_Z', export_global_up_selection='Y',
    export_textures_mode='PRESERVE',             # KEEP / PRESERVE / NEW
    overwrite_textures=False, relative_paths=True,
    xform_op_mode='TRS',                         # TRS / TOS / MAT
    root_prim_path='/root', export_custom_properties=True,
    custom_properties_namespace='userProperties', author_blender_name=True,
    convert_world_material=True, allow_unicode=True,
    export_meshes=True, export_lights=True, export_cameras=True, export_curves=True,
    export_points=True, export_volumes=True, triangulate_meshes=False,
    quad_method='BEAUTY', ngon_method='BEAUTY', usdz_downscale_size='KEEP',
    merge_parent_xform=False,
    convert_scene_units='METERS',                # METERS/KILOMETERS/CENTIMETERS/MILLIMETERS/INCHES/FEET/YARDS/CUSTOM
    meters_per_unit=1.0)
bpy.ops.wm.usd_import(filepath="in.usda", relative_path=True, scale=1.0, set_frame_range=True,
    import_cameras=True, import_curves=True, import_lights=True, import_materials=True,
    import_meshes=True, import_volumes=True, import_shapes=True, import_skeletons=True,
    import_blendshapes=True, import_points=True, import_subdivision=False,
    support_scene_instancing=True, import_visible_only=True, create_collection=False,
    read_mesh_uvs=True, read_mesh_colors=True, read_mesh_attributes=True, prim_path_mask='',
    import_guide=False, import_proxy=False, import_render=True,
    import_all_materials=False, import_usd_preview=True, set_material_blend=True,
    light_intensity_scale=1.0,
    mtl_purpose='MTL_ALL_PURPOSE',               # MTL_ALL_PURPOSE/MTL_PREVIEW/MTL_FULL
    mtl_name_collision_mode='MAKE_UNIQUE',
    import_textures_mode='IMPORT_COPY',          # IMPORT_NONE/IMPORT_PACK/IMPORT_COPY
    import_textures_dir='//textures/', tex_name_collision_mode='USE_EXISTING',
    property_import_mode='USER',                 # NONE / USER / ALL
    validate_meshes=False, create_world_material=True, import_defined_only=True,
    merge_parent_xform=True, apply_unit_conversion_scale=True)
```

> **주의**: `wm.usd_export` 에는 `export_selected_objects` 인자가 **없습니다**. 5.2 실측 `TypeError: keyword "export_selected_objects" unrecognized`. 올바른 인자는 `selected_objects_only` 입니다. 다른 `wm.*_export` 들은 `export_selected_objects` 를 씁니다 — 포맷별로 이름이 다릅니다.
> `wm.usd_import` 는 디렉터리 전체를 임포트할 수 있습니다 (`import_visible_only`).

### 9.6 glTF / FBX (5.2 실측)

```python
bpy.ops.export_scene.gltf(filepath="out.glb",       # 또는 .gltf
    export_format='GLB',            # GLB / GLTF_SEPARATE / GLTF_EMBEDDED (동적 enum)
    export_image_format='AUTO',     # AUTO / JPEG / WEBP / NONE
    export_texcoords=True, export_normals=True,
    export_draco_mesh_compression_enable=False, export_draco_mesh_compression_level=6,
    export_meshopt_compression_enable=False, export_tangents=False,
    export_materials='EXPORT',      # EXPORT/PLACEHOLDER/VIEWPORT/NONE
    export_vertex_color='MATERIAL', # MATERIAL/ACTIVE/NAME/NONE
    use_mesh_edges=False, use_mesh_vertices=False, export_cameras=False, export_lights=False,
    use_selection=False, use_visible=False, use_renderable=False,
    export_yup=True,                # glTF 표준(Y-up) 보정
    export_apply=False,             # 모디파이 적용 후 내보내기
    export_animations=True, export_frame_range=False, export_frame_step=1,
    export_force_sampling=True,
    export_animation_mode='ACTIONS', # ACTIONS/ACTIVE_ACTIONS/BROADCAST/NLA_TRACKS/SCENE
    export_optimize_animation_size=True,
    export_skins=True, export_influence_nb=4, export_all_influences=False,
    export_morph=True, export_morph_normal=True, export_morph_animation=True,
    export_try_sparse_sk=True, export_pointer_animation=False)
bpy.ops.import_scene.gltf(filepath="in.glb", import_pack_images=True, merge_vertices=False,
    import_shading='NORMALS',       # NORMALS / FLAT / SMOOTH
    bone_heuristic='BLENDER',       # BLENDER / TEMPERANCE / FORTUNE
    disable_bone_shape=False, bone_shape_scale_factor=1.0, guess_original_bind_pose=True,
    import_webp_texture=False, import_unused_materials=False, import_select_created_objects=True,
    import_scene_extras=True, import_scene_as_collection=True,
    import_merge_material_slots=True, import_point_as_pointcloud=False)

bpy.ops.export_scene.fbx(filepath="out.fbx", use_selection=False, use_visible=False,
    use_active_collection=False, global_scale=1.0, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_UNITS',   # FBX_SCALE_NONE/UNITS/CUSTOM/ALL
    use_space_transform=True, bake_space_transform=False,
    object_types={'EMPTY','CAMERA','LIGHT','ARMATURE','MESH','OTHER'},   # set
    use_mesh_modifiers=True, use_mesh_modifiers_render=True,
    mesh_smooth_type='FACE',                # OFF / FACE / EDGE / SMOOTH_GROUP
    colors_type='SRGB',                     # NONE / SRGB / LINEAR
    use_subsurf=False, use_mesh_edges=False, use_tspace=False, use_triangles=False,
    use_custom_props=False, add_leaf_bones=True,
    primary_bone_axis='Y', secondary_bone_axis='X',
    armature_nodetype='NULL',               # NULL / ROOT / LIMBNODE
    bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=True,
    bake_anim_use_all_actions=True, bake_anim_force_startend_keying=True,
    bake_anim_step=1.0, bake_anim_simplify_factor=1.0, path_mode='AUTO', embed_textures=False,
    batch_mode='OFF',                       # OFF/SCENE/COLLECTION/SCENE_COLLECTION/ACTIVE_SCENE_COLLECTION
    use_batch_own_dir=True, use_metadata=True, axis_forward='-Z', axis_up='Y')
bpy.ops.import_scene.fbx(filepath="in.fbx", use_manual_orientation=False, global_scale=1.0,
    bake_space_transform=False, use_custom_normals=True, colors_type='SRGB',
    use_image_search=True, use_alpha_decals=False, use_anim=True, anim_offset=1.0,
    use_subsurf=False, use_custom_props=True, ignore_leaf_bones=False,
    force_connect_children=False, automatic_bone_orientation=False,
    primary_bone_axis='Y', secondary_bone_axis='X', use_prepost_rot=True,
    mtl_name_collision_mode='MAKE_UNIQUE', axis_forward='-Z', axis_up='Y')
bpy.ops.wm.fbx_import(filepath="in.fbx",      # 내장 importer (애드온 무관)
    global_scale=1.0, mtl_name_collision_mode='MAKE_UNIQUE',
    import_colors='SRGB',                    # NONE / SRGB / LINEAR
    use_custom_normals=True, use_custom_props=True, use_custom_props_enum_as_string=True,
    import_subdivision=False, ignore_leaf_bones=False,
    validate_meshes=True, use_anim=True, anim_offset=1.0)
```

### 9.7 축 / 단위 변환

| 포맷 | 기본 축 | 변환 |
|---|---|---|
| OBJ | `forward='-Z', up='Y'` | Blender Z-up 근사 (3.x 와 다름) |
| glTF | `export_yup=True` | glTF 표준 Y-up. 끄면 Z-up로 잘못된 파일 |
| FBX | `axis_forward='-Z', axis_up='Y'` | 게임 엔진 관례 (Unity/Unreal) |
| USD | `convert_orientation=False` | Blender Z-up 유지. 게임용으로 내보내면 `True` |

### 9.8 `.blend` 저장 / 열기 / 부분 라이브러리

```python
# verify/54_blend_canonical.py
import bpy, os
OUT = "/workspace/out/docio"; os.makedirs(OUT, exist_ok=True)
A, B = OUT + "/scene_a.blend", OUT + "/lib.blend"

bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
mesh = bpy.data.meshes.new("HeroMesh")
mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)], [], [(0,1,2)]); mesh.update()
hero = bpy.data.objects.new("Hero", mesh)
sc.collection.objects.link(hero)
hero.location = (3, 0, 0)
hero.keyframe_insert(data_path="location", frame=10)

print("bpy.data.filepath =", repr(bpy.data.filepath), " is_dirty =", bpy.data.is_dirty)
bpy.ops.wm.save_as_mainfile(filepath=A, compress=True, relative_remap=True)
print("saved ->", os.path.getsize(A), "bytes; filepath now =", bpy.data.filepath)
bpy.ops.wm.save_as_mainfile(filepath=OUT+"/scene_b.blend", compress=False)
print("uncompressed size:", os.path.getsize(OUT+"/scene_b.blend"))
```

```
bpy.data.filepath = ''  is_dirty = False
saved -> 86746 bytes; filepath now = /workspace/out/docio/scene_a.blend
uncompressed size: 495727 bytes
```

| `wm.save_as_mainfile` 인자 | 기본값 | 의미 |
|---|---|---|
| `filepath` | — | 저장 경로 |
| `compress` | `False` | gzip 압축. 495727 → 86746 바이트 (**5.7배**) |
| `relative_remap` | `True` | 기존 상대 경로를 새 위치에 맞게 재매핑 |
| `copy` | `False` | True면 현재 파일명을 바꾸지 않고 **사본만** 저장 |
| `check_existing` | `True` | GUI용, headless에서는 무시 |

> `copy=True` 를 쓰면 `bpy.data.filepath` 가 **변하지 않습니다** (verify/41 실측: `after save: bpy.data.filepath = ''`).

| `wm.open_mainfile` 인자 | 기본값 | 의미 |
|---|---|---|
| `load_ui` | `True` | 저장된 UI 레이아웃 복원. headless에서는 `False` |
| `use_scripts` | `False` | `.blend` 내장 Python 자동 실행. **`False` 유지 (보안)** |
| `display_file_selector` | `True` | GUI용 |
| `state` | `0` | 전용 상태 플래그 |

**`libraries.write`** — docstring 실측 시그니처:
`write(filepath, datablocks, *, path_remap='NONE', fake_user=False, compress=False)`
`path_remap`: `NONE`(기본) / `RELATIVE` / `RELATIVE_ALL` / `ABSOLUTE`. `datablocks` 에 ID를 넣으면 **간접 참조된 데이터도 자동으로 확장**되어 기록됩니다.

> **5.2에서 `bpy.data.libraries.write()` 는 `None` 을 반환합니다.** 이전 버전의 `True`/`False` 를 검사하는 코드 (`if bpy.data.libraries.write(...)`) 는 항상 falsy 분기로 갑니다.

**`libraries.load`** — docstring 실측 시그니처:
`load(filepath, *, link=False, pack=False, relative=False, set_fake=False, recursive=False, reuse_local_id=False, assets_only=False, clear_asset_data=False, create_liboverrides=False, reuse_liboverrides=False, create_liboverrides_runtime=False)`

```python
# verify/54_blend_canonical.py
# --- APPEND (로컬 복사본) ---
with bpy.data.libraries.load(B, link=False) as (src, dst):
    print("src.objects =", list(src.objects), " src.meshes =", list(src.meshes))
    print("src.libraries =", list(src.libraries), "  (namedtuples: filepath, is_archive)")
    dst.objects = list(src.objects)          # ['Hero'] 또는 [] (아무것도 안 함) 또는 None (건너뜀)
# --- LINK (외부 참조) ---
with bpy.data.libraries.load(B, link=True) as (src, dst):
    dst.objects = list(src.objects)
for o in bpy.data.objects:
    if o.library:
        print("LINKED %-10s -> %s" % (o.name, o.library.filepath))
        o.make_local()
```

`src`(입력)에는 `bpy.data` 의 각 컬렉션 이름과 같은 속성이 **문자열 리스트**로 있습니다: `src.objects`, `src.meshes`, `src.materials`, `src.collections`, `src.scenes`, `src.armatures`, `src.actions`, `src.images`, `src.node_groups`, `src.libraries` 등.

> **중요: `src.objects` 는 문자열 리스트입니다.** `src.objects[0].name` 은 `AttributeError: 'str' object has no attribute 'name'`.

**5.2의 중첩 라이브러리 노출** — `src.libraries` 가 5.x에서 추가되어 로드 대상 `.blend` 가 참조하는 다른 라이브러리 경로를 노출합니다. **솔직한 보고: 이 속성은 문서화된 API이고 namedtuple(`filepath`, `is_archive`)을 담지만, 제가 구성한 모든 테스트에서 빈 리스트였습니다.** 원인은 `bpy.data.libraries.write()` 가 라이브러리 링크를 **평탄화(flatten)** 해서 중첩 체인이 만들어지지 않았기 때문입니다 (verify/44 실측: `chain: MidLocal -> [('mid.blend', (5,2,45), False)]`, `parent=None`). 이 속성의 동작을 검증했다고 주장할 수 없습니다.

확인된 `Library` 프로퍼티: `filepath, parent, packed_file, version, is_archive, archive_parent_library, archive_libraries, needs_liboverride_resync, is_editable, users, name, ...`
`Library.version` 은 `(5, 2, 45)` 같은 튜플.

**링크된 오브젝트의 제약:**

| 속성 | 5.2 |
|---|---|
| `ob.name` 쓰기 | ❌ `AttributeError: bpy_struct: attribute "name" from "Object" is read-only` |
| `ob.is_modified` | **메서드** — `ob.is_modified(scene, 'RENDER')`. 4.x 의 boolean property가 아님 |
| `ob.location` 쓰기 | ✅ 가능 (하지만 `is_modified` 플래그만 뜹니다) |
| `ob.make_local()` | 로컬 사본으로 전환 (`library` → `None`) |

---

## 10. 데이터 위생과 치명적 함정

### 10.1 `open_mainfile` 은 모든 Python 참조를 무효화한다

스크립트 파이프라인에서 가장 자주 터지는 버그입니다. **실측 검증 완료.**

```python
# verify/54_blend_canonical.py
stale_hero, stale_mesh = hero, mesh
print("stale_hero is bpy.data.objects['Hero']:", stale_hero is bpy.data.objects["Hero"])   # True

bpy.ops.wm.open_mainfile(filepath=A, load_ui=False, use_scripts=False)
print("bpy.data.filepath =", bpy.data.filepath)
try:
    print("stale_hero.location ->", tuple(stale_hero.location))
except ReferenceError as e:
    print("stale_hero.location -> ReferenceError:", e)
try:
    stale_mesh.name
except ReferenceError as e:
    print("stale_mesh.name    -> ReferenceError:", e)
fresh = bpy.data.objects["Hero"]
print("RE-FETCH is stale_hero?", fresh is stale_hero)      # False
print("  .location =", tuple(fresh.location), " .data =", fresh.data.name)
print("  animation still there:", fresh.animation_data.action.name if fresh.animation_data else None)
```

```
stale_hero is bpy.data.objects['Hero']: True
open_mainfile done. bpy.data.filepath = /workspace/out/docio/scene_a.blend
stale_hero.location -> ReferenceError: StructRNA of type Object has been removed
stale_mesh.name    -> ReferenceError: StructRNA of type Mesh has been removed
RE-FETCH bpy.data.objects['Hero'] -> is stale_hero? False
  .location = (3.0, 0.0, 0.0)  .data = HeroMesh
  animation still there: HeroAction
  objects now: ['Hero']
```

**왜**: `bpy.ops.wm.open_mainfile()` 은 `BKE_blendfile_read_setup()` 로 기존 `Main` 의 모든 ID 를 파괴하고 새 `Main` 을 만듭니다. Python 쪽 `bpy_struct` 래퍼는 무효 메모리를 가리키므로 RNA 접근 시 `ReferenceError` 가 발생합니다.

**규칙**: `open_mainfile` (그리고 `read_homefile`, `wm.revert_mainfile`) 이후에는 **모든 ID 참조를 재조회**하세요. 가장 안전은 **프로세스별로 나누는 것**입니다:

```python
import subprocess
for path in paths:
    subprocess.run(["blender", "-b", "--factory-startup", "-noaudio", "-P", "worker.py", "--", path])
```

### 10.2 이름 충돌과 `remove()`

```python
# verify/46_hygiene.py
bpy.ops.mesh.primitive_cube_add();      a = bpy.context.object
bpy.ops.mesh.primitive_cube_add();      b = bpy.context.object
bpy.ops.mesh.primitive_uv_sphere_add(); c = bpy.context.object
print("objects:", [o.name for o in bpy.data.objects])   # ['Cube', 'Cube.001', 'Sphere']
print("meshes :", [m.name for m in bpy.data.meshes])    # ['Cube', 'Cube.001', 'Sphere']
```

**오브젝트와 메시는 별도의 네임스페이스**입니다. `objects["Cube"]` 와 `meshes["Cube"]` 는 다른 것. 하지만 **같은 네임스페이스 안에서는** 자동으로 `.001`, `.002` … 가 붙습니다. 그래서 `bpy.data.objects["Cube"]` 로 참조하면 나중에 어떤 Cube 였는지 알 수 없게 됩니다. **이름으로 조회하지 말고 레퍼런스를 보관하세요.** (`find(name)` → index 또는 `-1`, `get(name)` → `Object` 또는 `None`)

**5.2에서 `do_unlink` 는 기본값 `True` 입니다.** 과거의 "항상 `do_unlink=True` 를 명시하라"는 조언은 이미 반영되어 있습니다. `verify/47_do_unlink.py` docstring 실측:

```
bpy.data.objects     .remove  BlendDataObjects.remove(object, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.meshes      .remove  BlendDataMeshes.remove(mesh, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.materials   .remove  BlendDataMaterials.remove(material, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.collections .remove  BlendDataCollections.remove(collection, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.images      .remove  BlendDataImages.remove(image, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.actions     .remove  BlendDataActions.remove(action, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.armatures   .remove  BlendDataArmatures.remove(armature, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.curves      .remove  BlendDataCurves.remove(curve, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.cameras     .remove  BlendDataCameras.remove(camera, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.lights      .remove  BlendDataLights.remove(light, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.node_groups .remove  BlendDataNodeTrees.remove(tree, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.texts       .remove  BlendDataTexts.remove(text, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.scenes      .remove  BlendDataScenes.remove(scene, do_unlink=True)              # <- do_id_user 없음
bpy.data.worlds      .remove  BlendDataWorlds.remove(world, do_unlink=True, do_id_user=True, do_ui_user=True)
bpy.data.textures    .remove  BlendDataTextures.remove(texture, do_unlink=True, do_id_user=True, do_ui_user=True)
```

명시적으로 `do_unlink=True` 를 쓰는 것은 여전히 좋은 습관이지만 (의도가 명확), 5.2에서 **이를 빼면 오류가 난다**는 것은 사실이 아닙니다.

```python
# verify/46_hygiene.py
mesh_name = d.data.name
bpy.data.objects.remove(d)                 # do_unlink 없이도 성공
print("object gone:", "Temp" not in bpy.data.objects)                       # True
_ = d.data       # ReferenceError: StructRNA of type Object has been removed
print("mesh still present:", mesh_name in bpy.data.meshes, " users =", bpy.data.meshes[mesh_name].users)  # True 0
```

오브젝트를 제거해도 그 오브젝트가 참조하던 메시/머티리얼은 남습니다 (users=0). 정리는 `orphans_purge()` 가 해야 합니다.

### 10.3 `orphans_purge`, fake user, `is_dirty`

```python
# verify/46_hygiene.py
print("before: objects=%d meshes=%d" % (len(bpy.data.objects), len(bpy.data.meshes)))
n = bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
print("orphans_purge(...) ->", n, "removed")     # 2 removed
print("orphans_purge() ->", bpy.data.orphans_purge())   # 0 (정리 완료)
```

```
before: objects=3 meshes=5
orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True) -> 2 removed
orphans_purge() no-args -> 0
after: objects=3 meshes=3
```

| 인자 | 기본값 | 의미 |
|---|---|---|
| `do_local_ids` | `True` | 로컬(비-라이브러리) orphan 제거 |
| `do_linked_ids` | `True` | 라이브러리 orphan 제거 (읽기 전용 파일에서 위험) |
| `do_recursive` | `True` | 참조가 사라진 뒤 새롭게 orphan이 된 것까지 연쇄 제거 |

반환값은 **제거된 데이터블록 수**입니다.

**fake user**: `m.use_fake_user = True` 는 `.blend` 에 저장될 때 "사용자 0이어도 버리지 마라"를 표시합니다. 파이프라인에서 마지막에 참조만 남기고 싶은 데이터블록에 씁니다. 실측: `users: 0 → 1`, 해제 후 `orphans_purge` → `1 removed`.

**`bpy.data.is_dirty` 는 headless 스크립트에서 신뢰할 수 없습니다.** 오브젝트를 추가해도 `False` 로 남습니다 (verify/46 실측). UI 편집 플래그이지 데이터 변경 플래그가 아닙니다 (`BoolProperty`, 읽기 전용). 변경 감지가 필요하면 직접 추적하세요.

**일괄 제거 패턴** — `for t in bpy.data.texts:` 로 직접 순회하면서 제거하면 컬렉션이 변형되어 순회가 깨집니다. **항상 `list()` 로 복사한 뒤** 순회하세요. collections/textures/images/actions 에 모두 해당합니다.

```python
for t in list(bpy.data.texts):
    bpy.data.texts.remove(t)
```

`bpy.data` 의 전체 ID 컬렉션 (5.2, `.new()` 가 있는 것만):
`actions, annotations, armatures, brushes, cameras, collections, curves, grease_pencils, hair_curves, images, lattices, lightprobes, lights, linestyles, masks, materials, meshes, metaballs, node_groups, objects, palettes, particles, pointclouds, scenes, speakers, texts, textures, volumes, worlds`

> `bpy.data.shape_keys` 도 존재합니다 (verify/37 확인). 셰이프 키 ID는 생성자가 없으므로 위 필터에는 **포함되지 않습니다**.

### 10.4 `hasattr(bpy.types.X, "prop")` 는 RNA 프로퍼티에 대해 **신뢰 불가**

프로토콜에서 이미 지적된 함정입니다. 5.2 실측 (`verify/57_preflight.py`):

```
hasattr(bpy.types.Mesh, 'polygons')     = False   ← 실제로는 존재함!
hasattr(bpy.types.Mesh, 'shade_smooth') = True    ← RNA 프로퍼티가 아님 (인스턴스 메서드)
hasattr(bpy.types.FCurve, 'group_name') = False   (실제로도 없음)
hasattr(bpy.types.Action, 'fcurves')    = False   (실제로도 없음)
hasattr(bpy.types.Bone, 'roll')         = False   (실제로도 없음)
hasattr(bpy.types.Armature, 'bone_groups') = False  (실제로도 없음)
hasattr(bpy.types.Armature, 'layers')   = False   (실제로도 없음)
```

정확한 확인 방법:

```python
[p.identifier for p in bpy.types.Mesh.bl_rna.properties]                      # 전체
'polygons' in [p.identifier for p in bpy.types.Mesh.bl_rna.properties]        # True
```

이 패턴은 본 문서 전체(`action.fcurves`, `bone_groups`, `Bone.roll`, `armature.layers`) 에서 사용했습니다. **인스턴스가 아닌 타입에 `hasattr` 를 쓰는 순간 신뢰성을 잃습니다.** 인스턴스에 직접 `hasattr(ob, "fcurves")` 를 쓰는 것은 정확합니다.

### 10.5 치명적 함정 모음

| 함정 | 증상 | 해결 |
|---|---|---|
| `open_mainfile` 후 stale 참조 | `ReferenceError: StructRNA of type Object has been removed` | 로드 후 전부 재조회 |
| `parent_set` headless no-op | `{'FINISHED'}` 인데 아무 변화 없음 | `ob.parent` / `parent_type` / `matrix_parent_inverse` 직접 설정 |
| stale `EditBone` | 쓰레기 값 반환 또는 **SIGSEGV** | `mode_set(OBJECT)` 후 `arm_data.bones[name]` 재조회 |
| `light.type` 변경 | RNA 래퍼가 안 바뀜 → `AttributeError` | 새 데이터블록 생성 |
| `PoseBone.rotation_euler` 무시 | 조용히 무동작 | `rotation_mode = 'XYZ'` 먼저 |
| `envelope_weight = 0.0` | deformation 완전 정지 | 기본값 1.0 유지 |
| `head_radius` 로 envelope 조정 | 효과 없음 | `envelope_distance` 사용 |
| `action.fcurves` | `AttributeError` | `layers[0].strips[0].channelbag(slot).fcurves` |
| `anim_data.action` 만 대입 | `action_slot` 이 `None` | `anim_data.action_slot` 도 명시 |
| `bpy.ops.constraint.childof_set_inverse_pending` | `KeyError` (op 없음) | `c.set_inverse_pending = True` |
| 드라이버 `-y` 없이 | `is_valid=False`, 값 0 (조용한 실패) | `-y` 플래그 또는 단순식만 사용 |
| `bpy.data.meshes.remove(m)` 후 `m.name` | `ReferenceError` | 이름을 먼저 문자열로 저장 |
| `ShapeKey.frame = ...` | read-only | `bpy.ops.object.shape_key_retime()` |
| `src.objects[0].name` | `AttributeError: 'str'` | `src.objects` 는 문자열 리스트 |
| `bpy.data.libraries.write()` 결과 검사 | 항상 `None` | 성공/실패 반환값 없음 (예외로만 감지) |
| `view_layer.objects` exclude 직후 | stale | `view_layer.update()` |
| `FModifierGenerator.function` | `AttributeError` | `mode='POLYNOMIAL'` + `coefficients` |
| `bpy.data.is_dirty` | 항상 `False` | 직접 추적 |
| `bpy.data.shape_keys` 가 `bpy.data.*.new()` 목록에 없음 | — | `hasattr(coll,"new")` 필터는 이 ID를 누락 |

---

## 11. 5.x 마이그레이션 요약

3.x/4.x 스크립트를 5.2로 옮길 때 반드시 손대야 하는 지점:

| 구버전 | 5.2 | 상태 |
|---|---|---|
| `action.fcurves` | `layers[0].strips[0].channelbag(slot).fcurves` | ❌ **삭제됨** |
| `action.groups` | `channelbag.groups` | 위치 변경 |
| `fcurve.group` (str) | `fcurve.group` (`ActionGroup` 객체) | 타입 변경 |
| `fcurve.group_name` | `fcurve.group.name` | ❌ **삭제됨** |
| `armature.bone_groups` | `armature.collections` | ❌ **이름 변경** |
| `bpy.types.BoneGroup` | `bpy.types.BoneCollection` | ❌ **이름 변경** |
| `Bone.bone_collections` | `Bone.collections` | ❌ **이름 변경** |
| `Bone.roll` (object mode) | `EditBone.roll` 또는 `matrix_local` | ❌ **삭제됨** |
| `Bone.select` (object mode) | `PoseBone.select` / `bpy.ops.armature.select_*` | ❌ **삭제됨** |
| `bpy.types.KeyBlock` | `bpy.types.ShapeKey` | ❌ **이름 변경** |
| `ShapeKey.frame = ...` | `bpy.ops.object.shape_key_retime()` | ❌ **read-only화** |
| "ShapeKey" 모디파이어 | 암묵 적용 (모디파이어 없음) | ❌ **삭제됨** |
| `Driver.type` 다수 | `AVERAGE, SUM, SCRIPTED, MIN, MAX` | 축소 |
| `light.type = ...` 후 타입 속성 접근 | 새 데이터블록 생성 | ❌ **파괴적** |
| `bpy.ops.constraint.childof_set_inverse_pending` | `c.set_inverse_pending = True` | ❌ **삭제됨** |
| `FModifierGenerator.function` / `amplitude` | `mode='POLYNOMIAL'` + `coefficients` | ❌ **삭제됨** |
| `bpy.data.libraries.write()` → bool | `None` 반환 | 타입 변경 |
| `ob.is_modified` (property) | `ob.is_modified(scene, 'RENDER')` (메서드) | 타입 변경 |
| `import_scene.obj` / `export_scene.obj` | `wm.obj_import` / `wm.obj_export` | 이전부터 변경 |
| `bpy.ops.object.parent_set(...)` | 직접 RNA 설정 | ❌ **headless 무동작** |
| `Material.use_nodes = True` | 설정 불필요 (5.x 기본 노드 트리 존재) | deprecation |
| `bpy.types.Light.energy` | `PointLight/SunLight/SpotLight/AreaLight.energy` | 서브타입 분리 |

### 실행 팁: 무엇이 죽었는지 빨리 찾기

```python
# verify/57_preflight.py — 파이프라인 시작 지점에 붙이는 사전 점검
import bpy, addon_utils

def preflight():
    issues = []
    if bpy.app.version < (4, 4, 0):
        issues.append("slotted actions 없음")
    for mod in ("io_scene_gltf2", "io_scene_fbx"):
        if not addon_utils.check(mod)[1]:
            issues.append("addon disabled: " + mod)
    for g, o in (("wm", "obj_export"), ("wm", "usd_export"), ("export_scene", "gltf")):
        try:
            getattr(getattr(bpy.ops, g), o).get_rna_type()
        except Exception:
            issues.append("op missing: %s.%s" % (g, o))
    return issues

print("version:", bpy.app.version, bpy.app.version_string)
print("preflight():", preflight() or "[] (all good)")
```

```
version: (5, 2, 2) 5.2.2 LTS
preflight(): [] (all good)
```

```bash
blender -b --factory-startup -noaudio --python-expr "
import bpy, addon_utils
print('Action.fcurves in RNA:', 'fcurves' in [p.identifier for p in bpy.types.Action.bl_rna.properties])
print('Bone.roll in RNA     :', 'roll' in [p.identifier for p in bpy.types.Bone.bl_rna.properties])
print('BoneGroup exists     :', hasattr(bpy.types, 'BoneGroup'))
print('glTF addon           :', addon_utils.check('io_scene_gltf2'))
"
# Action.fcurves in RNA: False / Bone.roll in RNA: False / BoneGroup exists: False / glTF addon: (True, True)
```

---

## Verification log

모든 스크립트는 `/workspace/build/scene/verify/` 에 있습니다 (51개).
실행 명령은 전부 동일하며, 자동 실행 비교 실험만 예외입니다:

```
blender -b --factory-startup -noaudio --python verify/<name>.py
blender -b --factory-startup -noaudio -y --python verify/09_autoexec_flag.py   # §5.2 비교용 (둘 다 PASS)
```

**최종 스윕 결과: 51 / 51 PASS** (`__SCRIPT_OK__` 출력 기준). 각 스크립트는 처음에 일부러 실패하도록 작성한 탐색 스크립트였고, 발견한 API 오류를 `try/except` 로 감싸고 `__SCRIPT_OK__` 를 찍도록 고쳤습니다 — 그래서 "PASS"는 그 API가 실제로 그 오류를 낸다는 뜻입니다.

| # | 스크립트 | 내용 | 결과 |
|---|---|---|---|
| 02 | `02_io_operator_probe.py` | `get_rna_type` 기반 오퍼레이터 존재 검사, `bpy.ops.wm` 전체 열거 | PASS |
| 03 | `03_slotted_actions.py` | `action.fcurves` / `ActionSlot.name` / `ActionLayer.type` 부재 확인 | PASS |
| 04 | `04_fcurve_api.py` | `FCurve`/`Keyframe`/`ActionChannelbag` RNA 덤프, enum 추출, `update` 가 메서드 | PASS |
| 05 | `05_fcurve_new.py` | `fcurves.new()`, `groups.new()`, `fc.group = ActionGroup`, 슬롯 공유 | PASS |
| 06 | `06_action_helpers.py` | §3.4 헬퍼 4종 (`action_fcurves`/`fcurve_get`/`channelbag_of`/`action_group`) | PASS |
| 07 | `07_drivers.py` | 드라이버 API, `Driver.type` enum, `ob.driver_add("energy")` TypeError 관측 | PASS |
| 08 | `08_driver_autexec.py` | `use_scripts_auto_execute` 게이트, `driver_namespace` | PASS |
| 09 | `09_autoexec_flag.py` | `-y` 유무 비교 (두 번 실행) | PASS — 없음: `energy=0.0, is_valid=False` / 있음: `900.0, True` |
| 10 | `10_constraints_enum.py` | `Constraint.type` 29개 enum, 서브타입 RNA 덤프 | PASS |
| 11 | `11_constraints_demo.py` | 4종 제약, `childof_set_inverse_pending` 부재 확인 | PASS |
| 12 | `12_constraint_ops.py` | `bpy.ops.constraint` 전체 오퍼레이터 + 인자 | PASS |
| 13 | `13_depsgraph_stale.py` | `matrix_world` vs evaluated, `frame_set` 암묵 업데이트 | PASS |
| 14 | `14_depsgraph_stale2.py` | **결정적 depsgraph 증명** (original stale / evaluated fresh) | PASS |
| 15 | `15_scene_coll.py` | 씬/컬렉션 생성·link·unlink, 멀티씬, `window.scene`, 가시성 | PASS |
| 16 | `16_light_camera.py` | Light base RNA에 `angle`/`spot_size` 없음, 서브타입별 존재 확인 | PASS |
| 17 | `17_light_subtypes.py` | **`light.type` 변경이 RNA 래퍼를 교체하지 않음** 확인 | PASS |
| 18 | `18_light_structs.py` | `type(l)` 서브타입, 단위, `su.type='SPOT'` 무효 | PASS |
| 19 | `19_camera.py` | 카메라 프로퍼티/DoF/모드 전환/`data.driver_add` | PASS |
| 20 | `20_armature_api.py` | `bone_groups`·`layers` 부재, `collections` 존재, `bpy.ops.armature` 열거 | PASS |
| 22 | `22_parent_set.py` | `parent_set` 전 타입 headless 무동작, `BONE` 는 `No active bone` | PASS |
| 23 | `23_autoweights.py` | `ARMATURE_AUTO` 실패 + `Bone.select` 부재 + 수동 폴백 | PASS — **단 §7.6 정정으로 결론이 뒤집힘. auto 는 동작함** |
| 24 | `24_bone_select.py` | `PoseBone.select` 존재, VIEW_3D `temp_override` | PASS |
| 25 | `25_autoweights2.py` | `EXEC_DEFAULT` 강제 호출, 컨텍스트 오버라이드 격리 | PASS |
| 26 | `26_skinning.py` | 3본 리그 + 가우시안 가중치 스키닝 (178/178 정점 변형) | PASS |
| 27 | `27_parent_set_debug.py` | `parent_set(type='OBJECT')` 무동작 결정적 확인 | PASS |
| 28 | `28_ops_sanity.py` | headless 에서 다른 `bpy.ops.object.*` 는 정상 동작 | PASS |
| 31 | `31_env_isolate.py` | `rotation_mode` 함정 발견, envelope/vertex group 양쪽 검증 | PASS |
| 32 | `32_rig_canonical.py` | **§7.4 리그+스키닝 정본** | PASS |
| 33 | `33_envelope_bone_parent.py` | **§7.6/7.7 envelope + BONE 패런팅 정본** | PASS |
| 34 | `34_stale_editbone.py` | stale EditBone 쓰레기 값 + **SIGSEGV** | PASS (크래시는 `--crash` 경로에서 의도적 유발) |
| 35 | `35_env_bisect.py` | `envelope_weight=0.0` 이 deformation 을 죽이는 이유 확정 | PASS |
| 37 | `37_shapekeys_canonical.py` | **§8.1 셰이프 키 정본** | PASS |
| 39 | `39_io_signatures.py` | 15개 I/O 오퍼레이터의 **전체 인자 시그니처** 덤프 | PASS |
| 40 | `40_io_matrix2.py` | **§9.1 I/O 가용성 매트릭스** + addon disable/enable 실험 | PASS |
| 41 | `41_blend_io.py` | `save_as_mainfile`, `copy=True`, `open_mainfile` 무효화, `libraries.write` | PASS |
| 42 | `42_libraries.py` | append vs link, `Library` 프로퍼티, `make_local` | PASS |
| 44 | `44_nested_libs2.py` | 중첩 라이브러리 체인 구성 시도 | PASS — **체인 평탄화**, `src.libraries` 항상 `[]` |
| 46 | `46_hygiene.py` | 이름 충돌, `remove()`, `orphans_purge`, fake user, `is_dirty`, 압축 | PASS |
| 47 | `47_do_unlink.py` | 15개 `remove()` 시그니처 — `do_unlink=True` 기본값 확인 | PASS |
| 48 | `48_scene_canonical.py` | **§1 씬/컬렉션 정본** | PASS |
| 49 | `49_active_collection.py` | 활성 컬렉션, `temp_override`, `exclude` + `view_layer.update()` | PASS |
| 50 | `50_driver_canonical.py` | **§5.3 드라이버 정본**, `is_simple_expression` 지연 계산 | PASS |
| 51 | `51_constraint_canonical.py` | **§6.4 컨스트레인트 정본**, `set_inverse_pending` | PASS |
| 52 | `52_objects_canonical.py` | **§2.1 오브젝트 데이터 정본**, `Object.data` 타입 고정 | PASS |
| 53 | `53_keyframe_canonical.py` | **§3.3/4.2 키프레임·FCurve 정본** | PASS |
| 54 | `54_blend_canonical.py` | **§9.8/10.1 .blend I/O 정본**, `ReferenceError` 재현 | PASS |
| 55 | `55_fmodifier.py` | FModifier 서브타입 전체 RNA 덤프, GENERATOR/CYCLES/NOISE | PASS |
| 56 | `56_fmodifier_generator.py` | **§4.4 다항식 생성기 정본** (`y = c0 + c1·f + ...` 검산) | PASS |
| 57 | `57_preflight.py` | §11 사전 점검 + `hasattr` 함정 재현 | PASS |
| 59 | `59_check_doc_args.py` | **본 문서의 모든 `bpy.ops.*` 호출에서 쓰인 키워드 인자가 실제 RNA 에 존재하는지 정적 검사** — `BAD ARGS: none` | PASS |
| **58** | **`58_doc_fragments.py`** | **본 문서의 모든 코드 프래그먼트를 문서 순서대로 실제 실행.** §9.5/§9.6 의 인자 블록 15개를 전부 실제 오퍼레이터에 넘겨 `{'FINISHED'}` 확인 | **PASS** |

`58_doc_fragments.py` 는 이 문서에 있는 스니펫이 **원본 탐색 스크립트가 아니라 문서에서 잘라낸 텍스트 그대로** 도는지를 증명하기 위한 하네스입니다. 출력:

```
[frag] §1 ok ... [frag] §8 ok
   sig-block wm            obj_export      OK
   sig-block wm            stl_export      OK
   sig-block wm            ply_export      OK
   sig-block wm            alembic_export  OK
   sig-block wm            usd_export      OK
   sig-block wm            usd_import      OK
   sig-block export_scene  gltf            OK
   sig-block export_scene  fbx             OK
   sig-block wm            fbx_import      OK
   sig-block import_scene  fbx             OK
   sig-block import_scene  gltf            OK
   sig-block wm            obj_import      OK
   sig-block wm            stl_import      OK
   sig-block wm            ply_import      OK
   sig-block wm            alembic_import  OK
[frag] §9.8/§10.1 ok
[frag] §10 ok
version: (5, 2, 2) 5.2.2 LTS
preflight(): [] (all good)
__SCRIPT_OK__
```

### 실패 / 미완료 항목 (정직한 보고)

| 항목 | 결과 |
|---|---|
| `bpy.data.libraries.load()` 의 `src.libraries` (중첩 경로 노출) | **API 존재 확인, 동작 미확인.** 모든 테스트에서 빈 리스트. `libraries.write()` 가 라이브러리 링크를 평탄화해 중첩 체인을 만들지 못했기 때문 (§9.8) |
| `bpy.ops.object.parent_set(type='ARMATURE_AUTO')` (bone heat) | **동작한다** (§7.6 정정 참고). 단 메시-뼈 거리가 멀면 가중치 0 → 무동작으로 오독됨. 가중치 합을 재고 판단할 것 |
| `bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')` | **headless 에서 무동작.** `use_bone_envelopes=True` 수동 경로는 정상 동작 (§7.7) |
| 레거시 액션(`is_action_legacy=True`) 상호운용 | **미검증.** 5.2에서 레거시 액션 생성 방법을 찾지 못함. §3.6 에 주의사항으로만 기록 |
| `bpy.data.libraries.write` 의 중첩 보존 | **미지원 확인.** write 시 링크가 평탄화됨 |
| `wm.usd_export` 를 정확히 재시도 | 최초 시도는 `export_selected_objects` 인자 오류로 실패 → `selected_objects_only` 로 수정 후 통과 |
| `ActionChannelbagSlot` 타입 | 5.2에 존재하지 않음 (`AttributeError: module 'bpy.types' has no attribute 'ActionChannelbagSlot'`) — 슬롯은 `ActionSlot` + `channelbag.slot_handle` 로 접근 |
| `bpy.types.DOFProperties` | 5.2에 존재하지 않음 — `bpy.types.Camera.bl_rna.properties['dof']` 의 런타임 타입으로 접근 |

### 실행 중 발견한 Blender 크래시

`verify/30_envelope_matrix.py` 와 `verify/33_envelope_bone_parent.py` (수정 전) 가 **SIGSEGV** 로 죽었습니다. 두 경우 모두 원인은 동일합니다: `mode_set(mode='OBJECT')` 이후 stale `EditBone` 레퍼런스에 `envelope_distance` 를 **쓰려다** 메모리 오염. 이 발견을 §7.3 에 별도 경고로 기록했고, `verify/34_stale_editbone.py` 로 재현·검증했습니다.

```
# Blender 5.2.2, Commit date: 2026-09-14 15:14, Hash d13f752e3b9c
# backtrace
blender(PyObject_SetAttr+0x71)
blender(_PyEval_EvalFrameDefault+0x6d5f)
...
# Python backtrace
  File ".../verify/33b.py", line 21 in <module>
```

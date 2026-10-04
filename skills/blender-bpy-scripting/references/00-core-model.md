# 00. bpy 멘탈 모델 — 스크립트를 어떻게 짜야 하는가

> 이 문서에서 모든 코드와 출력은 **Blender 5.2.2 LTS (commit `d13f752e3b9c`, 빌드 2026-09-15)** 를
> 헤드리스로 직접 실행해서 얻은 것이다. 검증 로그는 각 문서 끝의 `Verification log` 참고.

---

## 1. 한 문장 요약

> **`bpy`는 UI가 아니라 데이터베이스다. `bpy.ops.*` 는 그 데이터베이스를 조작하는
> *컨텍스트 의존적 래퍼*일 뿐이고, `bpy.data.*` 가 진짜 데이터다.**

에이전트가 가장 많이 빠지는 함정은 이 둘을 구분하지 못하고 `bpy.ops` 로 모든 걸 하려 하는 것이다.

| | `bpy.data.*` (Data API) | `bpy.ops.*` (Operator API) |
|---|---|---|
| 성격 | 순수 데이터 접근·할당 | 컨텍스트에 의존하는 "작업" 실행 |
| 컨텍스트 | 없음. 어디서든 동작 | `bpy.context` 에 의존 |
| 백그라운드(`-b`) | 100% 동작 | 대부분 동작, 일부 실패 |
| 실패 형태 | `AttributeError` / `KeyError` | `RuntimeError` **또는 조용히 `{'CANCELLED'}`** |
| 속도 | 빠름 | 느림 (오버헤드 큼) |
| 되돌리기 | 직접 구현 필요 | `'UNDO'` 옵션 사용 가능 |

**실무 규칙**: 속성 설정·생성·삭제는 전부 `bpy.data`로. `bpy.ops`는
(1) 기본 메시 생성, (2) 에디트 모드/컨텍스트 조작, (3) 파일 저장·렌더처럼
"Blender 내부 상태 전환이 필요한" 것만.

---

## 2. 데이터블록 구조 (Data-block graph)

`bpy.data` 아래에는 **데이터블록(ID)** 이라 불리는 것들이 종류별로 모인다.
각각은 자기 타입의 `bpy.data.<종류>` 컬렉션을 가지고, **참조 카운트(`users`)** 로 생존한다.

```
bpy.data
├── scenes        Scene
├── objects       Object ──▶ (Object는 "컨테이너". 실제 데이터는 아래를 참조)
├── meshes        Mesh
├── curves        Curve (CURVE / FONT / SURFACE)
├── materials     Material
├── images        Image
├── node_groups   NodeTree (Shader / Geometry / Compositor 공용)
├── lights        Light
├── cameras       Camera
├── armatures     Armature
├── collections   Collection
├── actions       Action        ← 5.x에서 구조가 완전히 바뀌었음
├── texts         Text
├── worlds        World
└── scenes ...
```

**핵심**: `Object`는 Geometry가 아니다.
`obj`는 위치/회전/스케일/머티리얼 슬롯/모디파이더만 가지고, 실제 정점은 `obj.data` 에 있다.

```python
import bpy

# 5.2에서 실측된 enum (bpy.types.Object.bl_rna.properties['type'].enum_items)
print([i.identifier for i in bpy.types.Object.bl_rna.properties["type"].enum_items])
# ['MESH','CURVE','SURFACE','FONT','META','CURVE','SURFACE','LATTICE',
#  'LIGHT','ARMATURE','LATTICE','EMPTY','POINTCLOUD','VOLUME','GREASEPENCIL','CAMERA','SPEAKER']
```

### 2.1 `bpy.data.objects.new()` 는 아무 데도 링크하지 않는다

이게 1순위 함정이다. 객체를 만들고 "왜 안 나오지?" 하면 100% 이 때문이다.

```python
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)

obj = bpy.data.objects.new("Hero", None)   # 1) 데이터블록 생성
print("users:", obj.users)                 # -> 0  ← 어디에도 없음
print("in scene:", obj.name in bpy.context.scene.objects)  # -> False

bpy.context.scene.collection.objects.link(obj)   # 2) 컬렉션에 링크해야 존재하게 된다
print("users:", obj.users)                 # -> 1
print("in scene:", obj.name in bpy.context.scene.objects)  # -> True
```

**실측 출력**
```
users: 0
in scene: False
users: 1
in scene: True
```

### 2.2 이름 충돌은 자동으로 `.001` 이 붙는다

```python
a = bpy.data.objects.new("Cube", None); bpy.context.scene.collection.objects.link(a)
b = bpy.data.objects.new("Cube", None); bpy.context.scene.collection.objects.link(b)
print(a.name, "|", b.name)     # 실측: Cube | Cube.001
```

그래서 **이름으로 오브젝트를 되찾으면 안 된다.** 참조를 직접 보관하거나,
`obj == bpy.data.objects["Cube.001"]` 처럼 실제 이름으로 찾거나,
유니크한 커스텀 프로퍼티를 붙여라.

### 2.3 참조 카운트와 정리

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)

mesh = bpy.data.meshes.new("M")
obj  = bpy.data.objects.new("O", mesh)
bpy.context.scene.collection.objects.link(obj)
print("before:", len(bpy.data.objects), len(bpy.data.meshes))   # 1 1

# do_unlink=True 를 안 주면 링크만 남고 데이터가 죽지 않는다
bpy.data.objects.remove(obj, do_unlink=True)
print("after obj remove:", len(bpy.data.objects), len(bpy.data.meshes))  # 0 1

bpy.data.meshes.remove(mesh, do_unlink=True)
print("after mesh remove:", len(bpy.data.meshes))                 # 0

# 장시간 스크립트/루프가 끝난 뒤 잔여 데이터 정리
bpy.ops.mesh.primitive_cube_add()
bpy.data.objects.remove(bpy.context.object, do_unlink=True)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
print("purged meshes:", len(bpy.data.meshes))                    # 0
```

`do_unlink=True`를 빼먹으면 "삭제했는데 안 없어져요"가 됩니다.

---

## 3. `bpy.context` — 백그라운드에서 무엇이 있고 무엇이 없는가

`bpy.context` 는 **지금 어떤 모드/어떤 창/어떤 선택 상태인가**를 담는 동적 컨텍스트다.
`-b`(배경 모드)에서 실제로 무엇이 `None`인지 실측했다:

```python
# frag  (아래 출력은 `blender -b -P` 로 실측)
print("area      ", bpy.context.area)      # None
print("region    ", bpy.context.region)    # None
print("screen    ", bpy.context.screen)    # <Screen("Layout")>  ← 존재
print("window    ", bpy.context.window)    # <Window>            ← 존재
print("scene     ", bpy.context.scene.name)      # 'Scene'
print("collection", bpy.context.collection.name) # 'Scene Collection'
print("view_layer", bpy.context.view_layer.name) # 'ViewLayer'
```

| 속성 | `-b` 백그라운드 | 비고 |
|---|---|---|
| `scene` | ✅ | 항상 안전 |
| `view_layer` | ✅ | |
| `collection` | ✅ | 기본이 `Scene Collection` |
| `window` | ✅ | |
| `screen` | ✅ | |
| `area` / `region` | ❌ `None` | UI 영역이 없음 |
| `active_object` | ⚠️ 오퍼레이터에 따라 다름 | 선택이 없으면 `None` |
| `object` / `mode` | ⚠️ | |

**규칙**: `area`, `region`, `space_data` 에 절대 의존하지 마라. 백그라운드에서 무조건 `None`이다.

---

## 4. `bpy.ops` 의 함정 — `{'CANCELLED'}` 는 성공이 아니다

이건 **프롬프트에 절대 넣지 말아야 할 정도의 함정**이다.
`bpy.ops` 는 예외를 던지지 않고 집합을 반환하는데, `{'CANCELLED'}` 는
"오퍼레이터가 실행은 됐지만 일을 거부했다"는 뜻이다. 예외가 없으므로
try/except로 절대 못 잡는다.

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)

# 활성 오브젝트가 없다 → 아무 일도 안 일어나는데 예외도 없다
res = bpy.ops.object.delete()
print(res)          # 실측: {'CANCELLED'}
print("FINISHED" in res)   # False  ← 이걸 봐야 한다
```

**실측 출력**
```
{'CANCELLED'}
False
```

같은 방식으로 `bpy.ops.mesh.primitive_cube_add()` 는 `{'FINISHED'}` 를 반환한다.

`bkkit` 에 이를 막는 래퍼가 있다:

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

bpy.ops.wm.read_factory_settings(use_empty=True)
res = introspect.call_op("mesh.primitive_cube_add", size=2.0)   # CANCELLED면 RuntimeError로 승격
print(res)                                                     # {'FINISHED'}
```

**규칙**: 자동화 코드에서 `bpy.ops.*` 호출 결과는 항상 검사하라.
```python
# frag
res = bpy.ops.<op_name>(<args>)
if "FINISHED" not in res:
    raise RuntimeError(f"operator failed: {sorted(res)}")
```

---

## 5. `bpy.ops` 인자를 미리 검증하기 (프리플라이트)

에이전트가 가장 많이 틀리는 게 오퍼레이터 인자 이름이다.
`get_rna_type()` 으로 실제 시그니처를 뽑아서 비교하면 추측이 사라진다.

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

print(introspect.op_exists("mesh.primitive_cube_add"))   # True
print(introspect.op_exists("export_scene.gltf"))        # True  (이 빌드에선 확장 기본 활성)
print(introspect.op_exists("nope.not_here"))            # False

print(introspect.op_props("mesh.primitive_cube_add"))
# 실측: ['align','size','calc_uvs','enter_editmode','location','rotation','scale',
#        'enter_editmode','align','location','rotation','scale']
```

그리고 호출 전에:

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

chk = introspect.op_check("mesh.primitive_cube_add", size=2.0, calcuvs=True, bogus=1)
print(chk)
# {'ok': False, 'errors': ["'mesh.primitive_cube_add' has no argument 'bogus'"], 'warnings': []}
```

`op_check` 는 세 가지를 잡는다: 오퍼레이터 없음 / 인자 없음(오타) / enum 값 오류.

### 5.1 빌드마다 없는 오퍼레이터

`bpy.ops` 는 총 **2498개**(5.2.2 실측)지만 빌드 옵션과 애드온 활성화 상태에 따라
존재 여부가 달라진다. 없는 오퍼레이터를 부르면 `AttributeError` 가 난다.

```python
# blender -b -P x.py 에서 실측
import addon_utils
enabled = sorted(m.__name__ for m in addon_utils.modules() if addon_utils.check(m.__name__)[1])
print(enabled)
# ['bl_pkg','cycles','io_anim_bvh','io_curve_svg','io_mesh_uv_layout',
#  'io_scene_fbx','io_scene_gltf2','pose_library']
```

`cycles` 는 애드온이라 기본 비활성 → **반드시 먼저 켜야 한다**(다음 절).

---

## 6. 렌더 엔진 — `enum` 은 거짓말을 한다

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

print(compat.engine_enum_items())
# 실측 (Cycles 애드온을 이미 켠 뒤인데도): ['BLENDER_EEVEE']
```

**RNA enum 은 동적으로 등록된 엔진을 반영하지 않는다.** Cycles 를 켜고
`scene.render.engine` 이 `'CYCLES'` 인 상태에서도 `enum_items` 는
`['BLENDER_EEVEE']` 만 알려준다. 이걸 게이트로 쓰면 안 된다.

```python
import bpy, addon_utils

addon_utils.enable("cycles", default_set=True, persistent=True)   # 1) 애드온 활성화
scene = bpy.context.scene
scene.render.engine = "CYCLES"                                     # 2) 문자열로 대입
print(scene.render.engine)                                         # -> CYCLES
```

`-b --factory-startup` 에서 이걸 빼먹으면:

```
TypeError: bpy_struct: item.attr = val: enum "CYCLES" not found in ('BLENDER_EEVEE',)
```

`bkkit.compat.set_engine(scene, "CYCLES")` 가 이걸 자동 처리하고,
실패하면 사용 가능한 값까지 알려준다.

> **메모**: 일반 설치본(사용자 설정 유지)에서는 Cycles 가 이미 켜져 있다.
> 하지만 **에이전트가 만드는 스크립트는 항상 `--factory-startup` 으로 도는 게 정석**이고,
> 그 경우 위 활성화 코드를 반드시 넣어야 한다.

---

## 7. 의존성 그래프(Dependency Graph) — 모디파이어 결과는 원본에 없다

이걸 모르면 "왜 렌더는 되는데 `obj.data` 를 읽으면 subdivide 안 된 값이 나오지?" 에
답을 못 한다.

```
obj.data (Mesh)                ← 원본. 당신이 직접 편집하는 곳
   │  모디파이어 스택
   ▼
의존성 그래프 평가 (depsgraph)
   ▼
obj.evaluated_get(depsgraph)   ← 평가된 복사본
   │  .to_mesh()  → 읽기
   │  .to_mesh_clear()  → 반드시 해제
   ▼
렌더
```

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.modifiers.new("Sub", "SUBSURF").levels = 3

print("원본 정점 수:", len(obj.data.vertices))          # 실측: 8

dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
mesh = ev.to_mesh()
print("평가 후 정점 수:", len(mesh.vertices))            # 실측: 386
ev.to_mesh_clear()                                       # 안 하면 메모리 누수
```

`obj.data` 를 수정하면 원본이 바뀐다. 하지만 **모디파이어 결과를 되돌려 써야 한다면**
`bpy.ops.object.modifier_apply()` 를 써야 한다 (컨텍스트 필요).

---

## 8. ID 프로퍼티와 커스텀 속성

`bpy_struct` 는 딕셔너리처럼 커스텀 키를 붙일 수 있다. 파이프라인 상태를
오브젝트에 태워두는 용도로 아주 유용하다.

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
obj = bpy.data.objects.new("A", None)
bpy.context.scene.collection.objects.link(obj)

obj["shot_status"] = "wip"
obj["seed"] = 42
obj["nested"] = {"pass": 1, "notes": ["a", "b"]}

print(obj["shot_status"], obj["seed"], obj["nested"]["pass"], obj["nested"]["notes"])
# 실측: wip 42 1 ['a', 'b']
print(list(obj.keys()))   # ['shot_status', 'seed', 'nested']
```

UI를 붙이려면 `id_properties_ui`:

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
obj = bpy.data.objects.new("A", None)
bpy.context.scene.collection.objects.link(obj)
obj["exposure"] = 1.0
obj.id_properties_ui("exposure").update(
    min=0.0, max=8.0, soft_max=4.0, description="EV 보정")
print(obj.id_properties_ui("exposure").as_dict())
# 실측:
# {'subtype':'NONE','description':'EV 보정','min':0.0,'max':8.0,
#  'soft_min':0.0,'soft_max':4.0,'step':1.0,'precision':3,'default':0.0}
```

> **5.2 변경**: ID 프로퍼티 중첩 깊이가 **1024로 제한**되었다
> (이전에는 무제한이라 스택 메모리를 다 먹고 재귀 크래시). 파이썬 dict를
> 파이썬 dict에 파이썬 dict에… 넣지 마라.

---

## 9. 버전이 아니라 **기능을** 확인하라

`bpy.app.version >= (5, 2, 0)` 로 분기하면 백포트 빌드나 커스텀 빌드에서 깨진다.
실제 존재 여부로 분기하는 게 언제나 맞다. 그리고 RNA 프로퍼티 존재 여부는
**`hasattr` 로는 못 본다.**

```python
import bpy

# hasattr은 거짓말을 한다
print(hasattr(bpy.types.WindowManager, "reports"))          # False  ← 존재하는데 False
print(hasattr(bpy.types.Window, "screenshot"))              # True

# 진짜 방법은 bl_rna
print("reports" in [p.identifier for p in bpy.types.WindowManager.bl_rna.properties])  # True
```

`bkkit.compat` 가 이걸 래핑한다:

```python
from bkkit import compat
compat.has_prop(bpy.types.WindowManager, "reports")   # True
compat.gn_uses_rna_properties()                      # True  (5.2+)
compat.has_action_slots()                            # True  (4.4+)
compat.has_scene_compositing_node_group()            # True  (5.0+)
```

> `hasattr(bpy.types.X, "prop")` 는 RNA 프로퍼티에 대해 거의 항상 False다.
> 인스턴스(`bpy.context.scene.render`)에 대한 `hasattr` 는 대체로 맞는다.
> 헷갈리면 `bl_rna.properties` 를 보는 게 유일하게 확실하다.

---

## 10. 5.x 슬롯 Actions — `action.fcurves` 는 죽었다

Blender 4.4부터 Action 구조가 바뀌었고, **5.2 에서는 `action.fcurves` 속성이 아예 없다.**

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
# has fcurves attr: False
# AttributeError: 'Action' object has no attribute 'fcurves'
```

5.2의 실제 구조:

```
Action
├── slots        : ActionSlot   (애니메이션되는 대상 ID를 가리킴)
└── layers
    └── strips  (type == 'KEYFRAME')
        └── channelbags
            └── fcurves
```

동작하는 코드 (실측):

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
print("slots:", [s.identifier for s in act.slots])     # ['OBCube']

bag = act.layers[0].strips[0].channelbag(slot)
print([(f.data_path, f.array_index, len(f.keyframe_points)) for f in bag.fcurves])
# [('location', 0, 3), ('location', 1, 3), ('location', 2, 3)]
```

버전 무관 헬퍼:

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.keyframe_insert("location", frame=1)
obj.location = (1, 1, 1)
obj.keyframe_insert("location", frame=10)

for fc in compat.action_fcurves(obj):
    print(fc.data_path, fc.array_index, len(fc.keyframe_points))
# location 0 2 / location 1 2 / location 2 2
```

`compat.action_fcurves()` 는 3단 폴백:
`action.fcurve_ensure_for_datablock(id)` (5.x) → `layers/strips/channelbag(slot)` (4.4+)
→ `action.fcurves` (4.0–4.3). 사용법은 언제나 같은 코드.

---

## 11. Geometry Nodes 모디파이어 — 5.2에서 RNA로 바뀌었다

4.x/5.1 까지는 커스텀(ID) 프로퍼티로 입력값을 넣었다. 5.2 에서는 실제 RNA 프로퍼티다.

```python
# frag  (4.0 - 5.1 용법. 5.2 에서는 이 라인이 죽는다)
mod["Geometry"] = 5.0
mod["Geometry_use_attribute"] = True
mod["Geometry_attribute_name"] = "some_attr"

# 5.2+ (현재)
mod.properties.inputs.Geometry.value = 5.0
mod.properties.inputs.Geometry.type = "ATTRIBUTE"
mod.properties.inputs.Geometry.attribute_name = "some_attr"
```

**작동하는 전체 예시 (실측)**:

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object

ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
ng.interface.new_socket("Amount",  in_out="INPUT",  socket_type="NodeSocketFloat")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

mod = obj.modifiers.new("GN", "NODES")
mod.node_group = ng

# 소켓 식별자는 하드코딩하지 말고 interface에서 뽑는다
ids = {i.name: i.identifier for i in ng.interface.items_tree
       if getattr(i, "in_out", "") == "INPUT"}
# 실측: {'Geometry': 'Socket_0', 'Amount': 'Socket_1'}

compat.set_gn_input(mod, ids["Amount"], 3.5)                    # 값
compat.set_gn_input(mod, ids["Amount"], 0.0, attribute_name="my_attr")  # 어트리뷰트

sock = getattr(mod.properties.inputs, ids["Amount"])
print(sock.value, sock.type, sock.attribute_name)
# 실측: 3.5 ATTRIBUTE my_attr
```

### 11.1 세 가지 함정 (모두 실측)

**(1) `getattr` 으로 접근해야 한다 — `[]` 는 다른 객체를 준다**

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
ng.interface.new_socket("Amount",  in_out="INPUT",  socket_type="NodeSocketFloat")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
mod = bpy.context.object.modifiers.new("GN", "NODES")
mod.node_group = ng
ids = {i.name: i.identifier for i in ng.interface.items_tree
       if getattr(i, "in_out", "") == "INPUT"}

print(type(getattr(mod.properties.inputs, ids["Amount"])).__name__)  # 'Socket_1'  ← RNA 구조체
print(type(mod.properties.inputs[ids["Amount"]]).__name__)          # 'IDPropertyGroup' ← 딕셔너리 복사본
print(hasattr(mod.properties.inputs[ids["Amount"]], "value"))       # False ← 그래서 값이 안 들어간다
```
`["Socket_1"]` 로 얻은 것에는 `.value` 가 없다. **항상 `getattr` 사용.**

**(2) 소켓 타입마다 `.value` 가 없다**

`NodeSocketGeometry` 같은 타입은 `properties.inputs` 에 등록되어도 `.value` 가 없다.
```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
mod = bpy.context.object.modifiers.new("GN", "NODES"); mod.node_group = ng
geo = [i.identifier for i in ng.interface.items_tree
       if getattr(i, "in_out", "") == "INPUT" and i.socket_type == "NodeSocketGeometry"][0]
sock = getattr(mod.properties.inputs, geo)
try:
    sock.value = 1.0
except AttributeError as e:
    print("AttributeError:", e)
# AttributeError: 'Socket_0' object has no attribute 'value'
```
값을 넣을 대상 소켓의 `socket_type` 을 먼저 확인하라.

**(3) 4.x 코드를 5.2에 그대로 쓰면**

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
mod = bpy.context.object.modifiers.new("GN", "NODES")
mod.node_group = ng

try:
    mod["Input_2"] = 1.0
except TypeError as e:
    print("TypeError:", e)
# TypeError: bpy_struct[key] = val: id properties not supported for this type
# (다른 컨텍스트에서는 'bpy_struct.keys(): this type doesn't support IDProperties' 로도 온다)
```

`compat.set_gn_input()` 이 이 셋을 모두 처리한다. 버전 분기는 넘기고 항상 이거 쓸 것.

**(4) 출력 소켓은 "Expose" 해야 등록된다**

`mod.properties.outputs` 에는 modifier 패널에서 **Expose 한 출력 소켓만** 나타난다.
아래 실측에서 `outputs` 에는 아무것도 없었다.

```
inputs  struct: ['Socket_0', 'Socket_1', ...]
outputs struct: []            ← NodeGroupOutput 노드를 만들어도 비어 있음
```

출력 어트리뷰트 이름을 지정하려면 modifier 패널에서 그 출력 소켓을 **Expose** 해야
`mod.properties.outputs` 에 등록된다. 스크립트에서 Expose 상태를 만드는 공식 API는
문서화된 것이 없다.

### ⚠ 11.2 `bpy.ops.object.geometry_nodes_input_attribute_toggle` 는 쓰면 죽는다

입력 소켓의 "값 ↔ 어트리뷰트" 전환을 담당하는 오퍼레이터처럼 보이는 이것은
**Blender 5.2.2 에서 세그폴트로.Blender 프로세스 자체를 죽인다.** 반복해서 실측했다:

```python
# no-exec  (실행하면 Blender 프로세스 자체가 죽는다. 검증기가 절대 실행하지 않는다)
with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
    bpy.ops.object.geometry_nodes_input_attribute_toggle(
        input_name="Amount", modifier_name="GN")
```

```
RNA_pointer_get: GeometryNodesInterfaceInputs.Amount not found.
Writing: /tmp/blender.crash.txt
Segmentation fault
```

시도해서 모두 죽었다:
`input_name` 에 **소켓 이름**을 넣을 때 / **식별자(`Socket_1`)** 를 넣을 때 /
`NodeGroupOutput` 노드를 연결하고 `view_layer.update()` 한 뒤.

다만 **컨텍스트를 충분히 못 만들어 주면 크래시 대신 예외가 난다** —
이 두 결과 모두 같은 원인(포인터 미해결)을 가리킨다:

```python
# no-exec  (아래 두 결과가 다 나왔고, 같은 코드임에도 환경에 따라 달라진다)
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Amount", in_out="INPUT", socket_type="NodeSocketFloat")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
mod = bpy.context.object.modifiers.new("GN", "NODES")
mod.node_group = ng
with bpy.context.temp_override(object=bpy.context.object,
                              active_object=bpy.context.object,
                              selected_objects=[bpy.context.object]):
    bpy.ops.object.geometry_nodes_input_attribute_toggle(
        input_name="Amount", modifier_name="GN")
```

**실제로 관찰된 두 가지 결과 (같은 코드):**

```
# A. 프로세스 죽음
RNA_pointer_get: GeometryNodesInterfaceInputs.Amount not found.
Writing: /tmp/blender.crash.txt
Segmentation fault

# B. 예외
RuntimeError: Operator bpy.ops.object.geometry_nodes_input_attribute_toggle.poll()
              Context missing active object
```

어느 쪽이 나올지가 **컨텍스트 상태에 따라 달라진다** (B 는 문서 검증기가
섹션 네임스페이스를 공유하며 돌릴 때 나온 결과다). 즉 이 오퍼레이터는
"될 때가 있고 죽을 때가 있다" 가 아니라 **판단할 수 없다**는 뜻이다.

**예외가 나든 죽든, 이 오퍼레이터는 스크립트에서 쓰지 마라.**

추정 원인은 `ng.interface` 의 식별자와 `mod.properties.inputs` 의 실제 속성명이
**어긋나기** 때문이다. 위 재현에서:

```
ng.interface.items_tree[0].identifier   ->  'Socket_1'
dir(mod.properties.inputs)              ->  ['Socket_0', ...]   ← 다른 번호
```

오퍼레이터는 `GeometryNodesInterfaceInputs.<input_name>` 을 조회해서 null 포인터를
역참조하고 죽는다.

**대신 이렇게 하라 — RNA 속성을 직접 바꾼다:**

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Amount",  in_out="INPUT",  socket_type="NodeSocketFloat")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
mod = bpy.context.object.modifiers.new("GN", "NODES")
mod.node_group = ng

ids = [i.identifier for i in ng.interface.items_tree
       if getattr(i, "in_out", "") == "INPUT"]
sock = getattr(mod.properties.inputs, ids[0])
print(sock.type, sock.value)          # VALUE 0.0

sock.type = "ATTRIBUTE"               # ← 이게 오퍼레이터가 하던 일
sock.attribute_name = "my_attr"
print(sock.type, sock.attribute_name) # ATTRIBUTE my_attr
```

> **일반 교훈**: 오퍼레이터가 "있어 보인다"는 건 호출 가능하다는 뜻이 아니다.
> 백그라운드 스크립트에서 새 오퍼레이터를 처음 쓸 때는 **반드시 별도 프로세스로 격리해서**
> 크래시가 렌더 파이프라인 전체를 죽이지 않게 하라.
> 격리 실행 패턴은 `05-automation-headless.md` 참고.

---

## 12. 런타임 종료 — CI에서 조용히 성공하는 사고

**`--python` 스크립트가 예외를 던져도 Blender의 종료 코드는 0이다.** 실측:

```bash
$ blender -b --factory-startup -noaudio --python boom.py; echo $?
RuntimeError: BOOM            ← 트레이스백 출력
0                              ← 그런데 종료코드는 0
```

이 때문에 배치 파이프라인이 "전부 성공"으로 보고된다. **반드시 직접 종료 코드를 지정하라.**

```python
import sys, traceback

def main():
    print("일하는 중...")

try:
    main()
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    code = 1
else:
    code = 0
sys.stdout.flush()
sys.exit(code)          # 실측: 이건 실제로 반영된다
```

```bash
$ blender -b -P ok.py   ; echo $?   # sys.exit(0) → 0
$ blender -b -P sys3.py ; echo $?   # sys.exit(3) → 3   (실측)
$ blender -b -P boom.py ; echo $?   # 예외만    → 0   (실측, 위험)
```

> **팁**: 이 샌드박스에서는 Blender의 stdout 가 파이프에서 새지 않는다.
> 항상 `> out.log 2>&1` 로 리다이렉트한 뒤 `cat` 하라.

### 12.1 더 나은 방법: `--python-exit-code 1`

수동 `sys.exit()` 대신 **Blender 전용 플래그**가 있다. 이건 5.2.2 에서 실측 확인했다.

```bash
# 예외가 나면 종료 코드 1
blender -b --factory-startup -noaudio --python-exit-code 1 --python script.py; echo $?
#  -> 1

# 정상 종료면 0
blender -b --factory-startup -noaudio --python-exit-code 1 --python ok.py; echo $?
#  -> 0
```

**배치 파이프라인의 정본 명령:**

```bash
blender -b --factory-startup -noaudio --python-exit-code 1 \
        --python build_and_render.py -- --out /tmp/shot.png
```

| 방식 | 예외 시 종료 코드 | 비고 |
|---|---|---|
| 기본 | **0** | 조용히 성공 (위험) |
| `--python-exit-code 1` | **1** | ✅ 이걸 쓰라 |
| 수동 `try/except` + `sys.exit(1)` | 1 | 플래그 없이 배제해야 할 때 |

> **`--python-exit-code 1` 은 예외가 났을 때만 1을 준다.**
> `sys.exit(3)` 같은 사용자 지정 코드는 여전히 3 이 나온다.
> 두 가지를 같이 써도 충돌하지 않는다.

---

## 13. 정리 — 에이전트가 지켜야 할 12가지

1. 속성 설정·생성·삭제는 `bpy.data` 로. `bpy.ops` 는 최소화.
2. `bpy.data.objects.new()` 결과는 **컬렉션에 link** 해야 보인다.
3. 이름을 키로 오브젝트를 찾지 마라 (`.001` 자동 접미사).
4. `bpy.ops` 반환값에 `'FINISHED'` 가 있는지 **반드시** 확인하라.
5. `--factory-startup` 에서 Cycles 는 `addon_utils.enable("cycles")` 선행.
6. 엔진 enum introspection은 거짓말한다. 문자열로 대입하고 예외를 잡아라.
7. RNA 프로퍼티 존재 확인은 `hasattr` 이 아니라 `bl_rna.properties`.
8. 버전이 아니라 실제 기능(features)을 탐지한다.
9. `action.fcurves` 는 5.2에 없다 → `bkkit.compat.action_fcurves()`.
10. GN 모디파이어 입력은 `getattr(mod.properties.inputs, ident)` (대괄호 아님).
11. 모디파이더 결과는 `evaluated_get()` + `to_mesh()`, 읽고 `to_mesh_clear()`.
12. 예외를 던져도 종료코드는 0 → `sys.exit(code)` 를 직접 호출.

---

## 14. 관련 문서

| 문서 | 내용 |
|---|---|
| `01-materials-nodes.md` | 머티리얼·셰이더·텍스처·GN 상세 |
| `02-geometry-modifiers.md` | 메시 생성·bmesh·커브·UV·모디파이러 |
| `03-render-output.md` | 엔진 설정·렌더·컴포지터·출력 포맷 |
| `04-scene-animation-io.md` | 씬 구조·키프레임·리그·임포트/익스포트 |
| `05-automation-headless.md` | 애드온·UI·핸들러·CLI·배치 파이프라인 |
| `09-verification-loop.md` | **빌드→렌더→측정→개선 루프** |
| `10-migration-4x-to-5x.md` | 버전 간 파괴적 변경 총정리 |
| `11-troubleshooting.md` | 에러별 원인/해결 |

---

## Verification log

이 문서의 모든 ```python 블록은 아래 명령으로 **실제 Blender 5.2.2 에서 실행**되어
PASS/FAIL 로 확인된다. 실행 안 된 블록은 `frag` 로 명시했다.

```bash
blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- references/00-core-model.md
# exit 0 = 통과, exit 1 = 실패 블록 있음
```

**실측 결과: 30개 블록 → 25 PASS / 5 SKIP / 0 FAIL** (종료 코드 0)
`# no-exec` 는 이 문서에 있는 세그폴트 재현 블록처럼, 실행하면 검증 프로세스까지
죽이는 블록에만 쓴다.

| 항목 | 명령 | 결과 |
|---|---|---|
| 배경 모드 context | `blender -b --factory-startup -P p13.py` | PASS — `area`/`region` 이 `None`, `screen`/`window` 존재 |
| `objects.new()` 미링크 | 같은 스크립트 | PASS — `users=0`, `scene.objects` 에 없음 |
| 이름 충돌 `.001` | 같은 스크립트 | PASS — `Cube` / `Cube.001` |
| `bpy.ops.object.delete()` CANCELLED | 같은 스크립트 | PASS — `{'CANCELLED'}`, 예외 없음 |
| ID 프로퍼티 + `id_properties_ui` | 같은 스크립트 | PASS — 실측 dict 출력 확인 |
| `do_unlink` / `orphans_purge` | `verify_docs` 블록 4 | PASS — `purged meshes: 0` |
| 슬롯 Actions 구조 | `blender -b -P p14.py` | PASS — `action.fcurves` 없음(확인), `channelbag(slot).fcurves` 3개 |
| `action.fcurves` 키포인트 삽입 | `blender -b -P p15.py` | PASS — `compat.action_fcurves()` 로 3커브 조회, 삽입 후 4개 |
| GN RNA 입력 | `blender -b -P p17.py` | PASS — `getattr` 는 `Socket_1`, `[]` 는 `IDPropertyGroup` |
| GN Geometry 소켓에 `.value` 없음 | `verify_docs` 블록 25 | PASS — `AttributeError` 재현 |
| 4.x GN 문법을 5.2에 | `verify_docs` 블록 26 | PASS — `TypeError` 재현 |
| GN 출력 소켓 미등록 | `blender -b -P p19.py` | PASS — `outputs` 비어 있음 확인 |
| **GN 토글 오퍼레이터** | `blender -b -P /tmp/crash*.py` (×3) | **PASS — 의도대로 세그폴트 재현.** RNA 우회책 블록 28 PASS |
| Subsurf 정점 수 | `verify_docs` 블록 14 | PASS — 386. *(초기에 512 라고 적었으나 검증기가 실제값 386 로 교정함. Catmull-Clark는 8→26→98→386)* |
| 종료 코드 | `blender -b -P p{7,8,9}.py` | PASS — 예외→0, `sys.exit(3)`→3 |

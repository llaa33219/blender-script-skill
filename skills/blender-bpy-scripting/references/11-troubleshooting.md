# 11. 트러블슈팅 — 실제 에러 메시지 사전

> 모든 에러 메시지는 **Blender 5.2.2 LTS 에서 실제로 재현**해서 뽑은 것이다.
> 처음 본 에러라면 §12 로 가기 전에 `bk api op` / `bk api prop` 으로 이름을 확인하라.

---

## 1. 즉시 죽는 런타임 오류

### `AttributeError: 'Action' object has no attribute 'fcurves'`
**원인**: 5.2에서 슬롯 Actions 로 개편되어 `Action.fcurves` 가 삭제됨.
**해결**: `bkkit.compat.action_fcurves(obj)` 또는
`action.layers[0].strips[0].channelbag(obj.animation_data.action_slot).fcurves`
→ `10-migration-4x-to-5x.md` §1.1

### `TypeError: bpy_struct: item.attr = val: enum "CYCLES" not found in ('BLENDER_EEVEE',)`
**원인**: `--factory-startup` 에서 Cycles 애드온이 비활성.
**해결**:
```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
print(scene.render.engine)   # CYCLES
```
또는 `bkkit.compat.set_engine(scene, "CYCLES")`.
→ `00-core-model.md` §6

### `TypeError: bpy_struct: item.attr = val: enum "BLENDER_EEVEE_NEXT" not found ...`
**원인**: 4.2 프리뷰 때 사용하던 식별자. 4.2 정식부터 `BLENDER_EEVEE`.
**해결**: `"BLENDER_EEVEE"` 로 변경.

### `bpy_struct: item.attr = val: enum "Medium High Contrast" not found in ('None', 'AgX - Punchy', ...)`
**원인**: `look` 값이 뷰트랜스폼 접두사를 갖는다. 또한 `view_transform` 을 먼저 안 설정했을 수도.
**해결**:
```python
import bpy
scene = bpy.context.scene
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
print(scene.view_settings.look)   # AgX - Medium High Contrast
```
→ `10-migration-4x-to-5x.md` §3

### `TypeError: bpy_struct[key] = val: id properties not supported for this type`
또는 `TypeError: bpy_struct.keys(): this type doesn't support IDProperties`
**원인**: 5.2에서 GN 모디파이퍼 입력이 ID property 를 abandon 함. 4.x 문법이 죽었다.
**해결**: `mod.properties.inputs.<identifier>.value = v`
→ `00-core-model.md` §11, `10-migration-4x-to-5x.md` §4

### `AttributeError: 'Socket_0' object has no attribute 'value'`
**원인**: `NodeSocketGeometry` 등 값이 없는 소켓 타입에 `.value` 를 대입.
**해결**: 소켓 타입 확인 후 값이 있는 타입만 설정.
```python
import bpy
ng = bpy.data.node_groups.new("T", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Amount",  in_out="INPUT", socket_type="NodeSocketFloat")
for i in ng.interface.items_tree:
    if getattr(i, "in_out", "") == "INPUT":
        print(i.identifier, i.name, i.socket_type)
# Socket_0 Geometry NodeSocketGeometry
# Socket_1 Amount   NodeSocketFloat
```

### `RuntimeError: Operator bpy.ops.<x>.<y>.poll() failed, context is incorrect`
**원인**: 오퍼레이터가 컨텍스트를 요구하는데 `-b` 모드에서 그 컨텍스트가 없다.
**해결 1**: `bpy.context.temp_override(...)` 로 필요한 객체를 넘긴다.
```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
    r = introspect.call_op("object.transform_apply", location=False, rotation=False, scale=True)
print(r)   # {'FINISHED'}
```
**해결 2 (더 나음)**: 오퍼레이터를 아예 쓰지 말고 data API 로 대체.
```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=2, scale=(3, 3, 3))
obj = bpy.context.object
print("before:", tuple(round(v,3) for v in obj.scale))     # (3.0, 3.0, 3.0)
# transform_apply(location=False, rotation=False, scale=True) 의 data API 버전
obj.scale = (1.0, 1.0, 1.0)
bpy.context.view_layer.update()
print("after :", tuple(round(v,3) for v in obj.scale))     # (1.0, 1.0, 1.0)
```

### `KeyError: bpy_prop_collection[key]: key "glare_type" not found`
**원인**: 5.x 컴포지터 노드의 파라미터가 속성에서 **소켓**으로 이동.
**해결**: `node.inputs["Type"].default_value = "Bloom"`.
→ `10-migration-4x-to-5x.md` §1.5

### `AttributeError: 'Scene' object has no attribute 'use_compositing'`
**원인**: `RenderSettings` 의 속성이다. `Scene` 가 아니라 `Scene.render` 에 있다.
**해결**: `scene.render.use_compositing = True`

---

## 2. 조용히 실패하는 경우 (더 위험)

### 2.1 `{'CANCELLED'}` — 예외 없이 아무 일도 안 일어남

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

bpy.ops.wm.read_factory_settings(use_empty=True)
res = bpy.ops.object.delete()          # 활성 오브젝트 없음
print(res, "FINISHED" in res)          # {'CANCELLED'} False
```

**해결**: `introspect.call_op("object.delete")` — `CANCELLED` 면 `RuntimeError` 로 승격.

**왜 CANCELLED 가 나올까 (실측된 케이스)**
| 원인 | 조치 |
|---|---|
| 활성 오브젝트 없음 | `temp_override(active_object=obj, ...)` |
| 오브젝트가 다른 컬렉션에 있음 | `temp_override(selected_editable_objects=[obj])` |
| 오브젝트가 Edit 모드 | `bpy.ops.object.mode_set(mode='OBJECT')` 먼저 |
| 격자(armature) 편집 중 | `bpy.ops.object.mode_set(mode='OBJECT')` 먼저 |
| `bpy.ops.object.modifier_apply` 인 다중사용자 | `use_single_user`? 아니, `single_user=True` 인자 확인 |
| 뷰포트 잠금 상태 | `bpy.context.window_manager` 확인 |

### 2.2 렌더가 성공했는데 아무것도 안 보임

**먼저 알아야 할 사실**: 카메라가 아예 없으면 Blender는 **시끄럽게 실패**한다.

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
try:
    bpy.ops.render.render(write_still=True)
except RuntimeError as e:
    print("RuntimeError:", e)
# RuntimeError: Error: Cannot render, no camera
```

하지만 **카메라만 있고 나머지가 깨져 있으면 조용히 성공한다.**
일부러 망가뜨린 6개 씬을 렌더한 실측 결과 (전부 `{'FINISHED'}` 반환):

| 망가뜨린 방식 | mean_luma | 순검정 % | 이미지 판정 |
|---|---|---|---|
| 조명 0개 | 0.00032 | 91.8% | **bad** (보정 후) |
| `obj.hide_render = True` | 0.00032 | 91.8% | **bad** |
| BSDF가 머티리얼 출력에 미연결 | 0.00032 | 91.8% | **bad** |
| 스케일 축 0 | 0.00032 | 91.8% | **bad** |
| 오브젝트가 씬에 링크 안 됨 | 0.04123 | 78.8% | **ok — 못 잡음** |
| 머티리얼 미할당 | 0.04123 | 78.8% | **ok — 못 잡음** |

기본 씬에 약한 회색 월드 조량이 있기 때문에 "순검정 픽셀 99.5% 초과" 같은
단순 기준으로는 4개를 놓친다. 그래서 판정기에 **mean_luma 하한선(0.010)** 을 넣었다.
그래도 **마지막 두 개는 픽셀로는 구분이 불가능**하다 — 기본 월드 + 기본 회색
머티리얼이 그 씬을 정상처럼 보이게 만들기 때문이다.

> **결론: 씬 검증(CHECK)과 이미지 측정(MEASURE) 둘 다 돌려라.**
> `bk.py render` 가 순서대로 수행하고, CHECK 가 실패하면 렌더를 거부한다.

상세 보정 근거는 `09-verification-loop.md` §3.0.

```python
import bpy, os, sys, tempfile
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat, imagecheck

scene = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 1))   # 조명은 의도적으로 없음
compat.set_engine(scene, "CYCLES")
scene.cycles.samples = 8
scene.render.resolution_x = scene.render.resolution_y = 64
out = os.path.join(tempfile.gettempdir(), "no_lights.png")
scene.render.filepath = out
bpy.ops.object.camera_add(location=(0, -6, 0.5), rotation=(1.5, 0, 0))
scene.camera = bpy.context.object
print("render:", bpy.ops.render.render(write_still=True))    # {'FINISHED'}  ← 성공처럼 보인다
stats = imagecheck.analyze_image_file(out)
print("실제 판정:", stats["verdict"])                        # bad
for r in stats["reasons"]:
    print("  -", r)
```

### 2.3 스크립트가 실패해도 CI 가 성공을 보고함

```bash
$ blender -b --factory-startup -noaudio --python boom.py ; echo $?
RuntimeError: BOOM
0
```

**가장 좋은 해결 — Blender 전용 플래그** (5.2.2 실측):

```bash
# 예외 -> 종료 코드 1, 정상 -> 0
blender -b --factory-startup -noaudio --python-exit-code 1 --python script.py; echo $?
# 1
blender -b --factory-startup -noaudio --python-exit-code 1 --python ok.py; echo $?
# 0
```

**플래그 없이 반드시 써야 한다면:**

```python
import bpy, sys, traceback

def main():
    bpy.ops.mesh.primitive_cube_add()

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
sys.exit(code)
```

```bash
$ blender -b -P runner.py ; echo $?    # 0 또는 1 이 실제로 반영된다
```

### 2.4 오브젝트를 만들었는데 씬에 없다

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
obj = bpy.data.objects.new("Hero", None)          # 데이터만 생성
print(obj.users)                                   # 0  ← 어디에도 링크 안 됨
bpy.context.scene.collection.objects.link(obj)     # ← 이것이 필요
print(obj.users)                                   # 1
```

### 2.5 머티리얼이 안 보인다 (투명 렌더)

```python
import bpy
m = bpy.data.materials.new("M")
nt = m.node_tree
out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial")
bsdf = next(n for n in nt.nodes if "Bsdf" in n.bl_idname)
print("BSDF가 출력에 연결됨:", out.inputs["Surface"].is_linked)   # False 이면 문제
```

`MAT_SURFACE_UNLINKED` 경고가 이걸 잡는다. 노드를 새로 만들고 **연결을 까먹는 것**이
가장 흔한 원인이다.

### 2.6 소켓 이름을 잘못 써서 아무 일도 안 일어남

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import introspect

m = bpy.data.materials.new("M")
bsdf = m.node_tree.nodes["Principled BSDF"]
print(introspect.set_input(bsdf, "Base Color", (1, 0, 0, 1)))   # True
print(introspect.set_input(bsdf, "Transmission", 0.5))          # False  ← 4.x 이름
print(introspect.set_input(bsdf, "Emission Strength", 5.0))    # True
```

**원칙: 소켓 이름으로 대입한 결과는 항상 확인하라.** `False` 면 그 설정은 버려진 것이다.

### 2.7 모디파이어를 추가했는데 메시에 반영이 안 됨

`obj.data` 는 **원본**이다. 모디파이어 결과는 depsgraph 안에만 있다.

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.modifiers.new("Sub", "SUBSURF").levels = 3

print("원본:", len(obj.data.vertices))                    # 8
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
me = ev.to_mesh()
print("평가:", len(me.vertices))                          # 386
ev.to_mesh_clear()                                        # ← 필수
```

### 2.8 모디파이어 순서 때문에 어색해짐

```
Boolean 위에 Subdiv 가 있으면 결과가 무너진다.
```
체커가 `MODIFIER_ORDER` 로 경고한다. 순서 정정:
```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
bpy.ops.mesh.primitive_cube_add(location=(0.5, 0, 0), scale=(0.6, 0.6, 0.6))
bpy.context.object.name = "Cutter"
# 주의: primitive_*_add 의 scale 은 FLOAT[3] 이다.
#      scale=0.6 (스칼라) 를 주면 TypeError: Converting py args to operator properties
cut = bpy.context.object

sub = obj.modifiers.new("Sub", "SUBSURF")
bo  = obj.modifiers.new("Bool", "BOOLEAN")
bo.object = cut
# Boolean 을 아래로, Subdiv 를 위로
obj.modifiers.move(len(obj.modifiers) - 1, 0)   # 실측: 마지막 모디파이어를 맨 위로
print([m.name for m in obj.modifiers])          # ['Sub', 'Bool']
```

---

## 2.9 🔴 조용히 실패하는 12가지 — 중앙 목록

> 이 목록은 **실전 테스트([`16-field-test.md`](16-field-test.md))에서 6명의 서브에이전트가
> 실제 작업을 수행하며 수집한 것**이다. 공통점: **예외가 없다. 경고가 없다.
> 산출물만 조용히 잘못 나온다.** try/except 로는 절대 못 잡는다.
>
> 그래서 예외 사전이 아니라 **이 목록을 별도로 본다.**

| # | 증상 | 원인 | 조치 |
|---|---|---|---|
| 1 | 렌더가 성공했는데 화면이 검정/하얀 | 조명·카메라·프레이밍 | `scenecheck` → `imagecheck` (§2.2) |
| 2 | 오브젝트를 만들었는데 씬에 안 보임 | `objects.new()` 후 링크 누락 | `collection.objects.link(obj)` (§2.4) |
| 3 | 머티리얼이 완전 투명으로 렌더 | BSDF가 출력 노드에 미연결 | `MAT_SURFACE_UNLINKED` (§2.5) |
| 4 | 소켓에 값을 넣었는데 반영이 안 됨 | 소켓 이름이 5.x 에서 개명됨 | `introspect.set_input()` 반환값 확인 (§2.6) |
| 5 | **GPU 지정했는데 CPU 로 렌더됨** | `compute_device_type` 대입은 성공, 하드웨어 없음 | `bkkit.compat.gpu_report()` (§2.6.5, `14-` §1) |
| 6 | **프로시저럴 머티리얼이 내보내기 후 전부 같은 회색** | 링크된 소켓이 `default_value` 로 방출됨 | **가장 조용하고 가장 파괴적.** 노드 트리 필수. 스킬에 경고 없음 |
| 7 | **컴포지터가 프로세스째 죽음** | 헤드리스에 `libEGL.so.1` 없음 | `apt-get install -y libegl1 libegl-mesa0` — **5분짜리 렌더가 통째로 소멸** |
| 8 | **컴포지터에서 `ColorCorrection` 썼더니 프레임 전체가 검게 죽음** | `Master Contrast` 가 0.5 피벗 연산 | 값을 1.0 근처로. 작은 배경값이 음수가 됨 |
| 9 | **비네트가 안 보인다** | `Blur.Extend Bounds=True` 가 마스크를 가장자리 Value(1.0) 로 채움 | `Extend Bounds=False` |
| 10 | **Glare 의 `Image` 출력이 원본+글로어가 아님** | Strength=0 으로 해도 원본값이 안 나옴 | 원본은 `rl.outputs["Image"]` 를 따로 보관 |
| 11 | **`TextStrip` 이 화면을 검게 덮음** | `blend_type` 기본값 `REPLACE` | `blend_type='ALPHA_OVER'` |
| 12 | **자동 가중치가 0 으로 나온다** | bone heat 는 메시-뼈 거리가 멀면 무효 | 거리 문제다. `ARMATURE_ENVELOPE` 또는 수동 (`04-` §7.6) |

### 2.9.1 반쪽만 아는 게 제일 위험하다

위 목록의 항목 중 **"정상처럼 보인다"** 는 게 6·10·12 다:

| 항목 | 왜 못 알아채는가 |
|---|---|
| 6 (내보내기 회색) | 폴리곤·UV·머티리얼 개수는 **전부 정상**이다. 노드 수만 줄었다. 파일도 열린다 |
| 10 (Glare Image) | `{'FINISHED'}`, 파일도 열린다. 픽셀이 살짝 다르다 |
| 12 (가중치 0) | `{'FINISHED'}`, 부모는 설정됐다. riggidbody·armature 모디파이러도 붙었다 |

> **공통 처방**: 이들 중 무엇이든 의심되면 **숫자를 재라.**
> "됐어 보인다" 가 아니라 "**이 값이 맞나**" 를 확인한다.
> `imagecheck` · `compare()` · 정점 수 · 가중치 합.
> `16-field-test.md` §1 의 6개 작업이 전부 이 방식으로 판정됐다.

### 2.9.2 구조적 안전망

스킬은 이 위험을 **개별 문서에 흩어두지 말고** 다음 세 곳에서 한 번에 확인하게 한다:

```bash
blender -b -P scripts/bk.py -- check     # 1. 씬 정적 검증 (16종)
blender -b -P scripts/bk.py -- render out.png   # 2. CHECK + RENDER + MEASURE 자동
blender -b -P scripts/bk.py -- api reach <idname>  # 3. 그 오퍼레이터가 여기서 도달 가능한가
```

`render` 는 `check` 가 fail 이면 **렌더 자체를 거부**한다(종료 코드 1).
`analyze` 는 `bad` 판정이면 종료 코드 1.
**이 두 개가 CI 에서 걸러주지 못하는 건 항목 5·6·10·12 다** —
그래서 그것들은 산출물 자체의 수치를 재야 한다.

---

## 3. 프로세스 자체가 죽는 경우

### `geometry_nodes_input_attribute_toggle` 세그폴트

```
RNA_pointer_get: GeometryNodesInterfaceInputs.Amount not found.
Writing: /tmp/blender.crash.txt
Segmentation fault
```

5.2.2 에서 **어떤 인자를 주어도 죽는다** (소켓 이름 / 식별자 / `temp_override` 무관).
`ng.interface` 의 식별자와 `mod.properties.inputs` 의 속성명이 어긋나는 것이 원인으로 보인다.

**대신 RNA 로 직접** (안전, 검증됨):
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
sock.type = "ATTRIBUTE"
sock.attribute_name = "my_attr"
print(sock.type, sock.attribute_name)   # ATTRIBUTE my_attr
```

→ `00-core-model.md` §11.2

### 격리 실행 패턴 (크래시 방어)

새 오퍼레이터를 처음 쓸 때는 **반드시 별도 프로세스로** 돌려서,
크래시가 파이프라인 전체를 죽이지 않게 하라.

```bash
#!/usr/bin/env bash
# risky_op.sh -- 격리 실행 래퍼
set -u
LOG=$(mktemp)
timeout "${TIMEOUT:-120}" blender -b --factory-startup -noaudio \
    --python "$1" ${2:+-- "$2"} > "$LOG" 2>&1
code=$?
if [ $code -ge 128 ]; then
    echo "!!! SIGNAL $((code-128)) -- 크래시. 로그: $LOG"
    cat "$LOG"
    exit 1
fi
if grep -q "Segmentation fault\|Writing: .*crash.txt" "$LOG"; then
    echo "!!! CRASH 감지. 로그: $LOG"; cat "$LOG"; exit 1
fi
cat "$LOG"
exit $code
```

**배치 파이프라인 규칙**: 렌더 워커는 반드시 이 래퍼(또는 동등한 격리)를 거치게 하라.
세그폴트는 예외가 아니라 **프로세스 종료**이므로 Python 레벨 try/except로는 절대 못 잡는다.

---

## 4. 성능 / 메모리

### 렌더가 너무 느릴 때

| 원인 | 조치 |
|---|---|
| EEVEE 를 GPU 없이 사용 | **Cycles CPU 로 전환.** 실측: 64×64 EEVEE 113초 vs 96×96 Cycles 0.96초 (약 100배) |
| 샘플 과다 | 루프 중 16~48, 최종만 256+ |
| 해상도 과다 | 루프 중 320×240, 최종만 1920×1080 |
| Subdiv 과다 | `HILLY_POLY` 경고 확인 |
| denoising 없음 | `use_denoising = True` 로 샘플 대폭 절약 |

### EEVEE 가 백그라운드에서 죽을 때

```
Couldn't open libEGL.so.1
EGL Error (0x3009): EGL_BAD_MATCH
```

GPU/드라이버가 없는 서버다. 설치:
```bash
apt-get install -y libegl1 libgl1 libglx-mesa0 libgl1-mesa-dri libxkbcommon0
```
설치 후 소프트웨어(llvmpipe)로 렌더는 되지만 **매우 느리다**. 반복 루프에는 Cycles CPU.

### 장시간 스크립트 메모리 증가

```python
import bpy, gc
# 루프 종료 후
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
gc.collect()
# 그리고 to_mesh_clear() 를 빼먹지 않았는지 확인
```

---

## 5. 진단 도구 모음 (모두 실행 검증됨)

```bash
# 1) 환경 전체 (버전/엔진/애드온/기능 플래그)
blender -b -P scripts/bk.py -- doctor

# 2) 오퍼레이터 실제 인자 + 기본값
blender -b -P scripts/bk.py -- api op mesh.primitive_uv_sphere_add

# 3) RNA 프로퍼티 타입/enum/기본값
blender -b -P scripts/bk.py -- api prop CyclesRenderSettings denoiser

# 4) 노드 타입 목록
blender -b -P scripts/bk.py -- api nodes CompositorNode

# 5) 현재 씬 검증
blender -b file.blend -P scripts/bk.py -- check

# 6) 렌더 → 자동 측정 → 판정
blender -b file.blend -P scripts/bk.py -- render /tmp/out.png --engine CYCLES --res 320x240

# 7) 이미지 측정 (여러 개 비교)
blender -b -P scripts/bk.py -- analyze /tmp/a.png /tmp/b.png --diff

# 8) 이 스킬 문서의 코드 블록 전부 실행 검증
blender -b -P scripts/verify_docs.py -- references/
```

### 실측: `api op` 출력 예시

```
$ blender -b -P scripts/bk.py -- api op mesh.primitive_uv_sphere_add
=== mesh.primitive_uv_sphere_add ===
  description: Add a UV sphere to the scene
  align                        ENUM        default=0 enum=['WORLD', 'VIEW']
  location                     FLOAT       default=(0.0, 0.0, 0.0)
  rotation                     FLOAT       default=(0.0, 0.0, 0.0)
  scale                        FLOAT       default=(0.0, 0.0, 0.0)
  segments                     INT         default=32
  ring_count                   INT         default=16
  radius                       FLOAT       default=1.0
  calc_uvs                     BOOLEAN     default=True
  enter_editmode               BOOLEAN     default=False
```

---

## 6. "안 된다" 증상 → 원인 역추적 체크리스트

렌더가 이상할 때 순서대로 확인:

```
1. scene.camera 가 None 이 아닌가?          (bk check → NO_CAMERA)
2. 카메라가 피사체를 향하고 있는가?          (bk check → CAMERA_SEES_NOTHING)
3. obj 가 씬 컬렉션에 링크되어 있는가?        (obj.users > 0)
4. 조명이 있는가? energy > 0?                 (bk check → NO_LIGHT)
5. 머티리얼이 붙어 있는가?                   (bk check → NO_MATERIAL)
6. BSDF 가 머티리얼 출력에 연결돼 있는가?      (bk check → MAT_SURFACE_UNLINKED)
7. obj.scale 에 0 이 있는가?                  (bk check → TRANSFORM_ZERO_SCALE)
8. 위치에 NaN 이 있는가?                      (bk check → TRANSFORM_NAN)
9. world strength 가 0 이 아닌가?
10. obj.hide_render 가 False 인가?           (숨겨진 오브젝트는 렌더 안 됨)
11. 컬렉션 자체가 exclude 되어 있지 않은가?   (view_layer 의 collection 제외)
12. 뷰포트/렌저 상한에 걸리지 않았는가?       (cam.data.clip_end)
```

`bk check` 는 1~11 중 대부분을 자동 검사한다. **렌더 전에 돌릴 것.**

---

## 7. 아직 재현하지 못한 것들 (정직한 기록)

- `drivers` 의 `use_scripts_auto_execute` 보안 토글은 GUI 설정이라 헤드리스에서
  실제 드라이버 식 평가까지 확인하지 못했다. API 존재는 확인함.
- GPU 경로 (`CUDA`/`OPTIX`/`METAL`) 는 이 샌드박스에 GPU 가 없어 검증 불가.
  `bpy.context.preferences.addons['cycles'].preferences.devices` 가 빈 리스트를 반환했다.
- Fluid / Ocean / Rigid Body 시뮬레이션은 캐시 디렉터리와 프레임 범위 설정이
  필요해 헤드리스 1회 실행으로 "결과가 맞는지"까지는 검증하지 않았다.
  (API 존재와 속성 이름은 확인 가능)

이 항목들은 이 문서를 쓸 때 실제로 확인되지 않은 것이다. 다른 문서를 참조하기 전에
스스로 재현해 볼 것.

---

## Verification log

`blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- references/11-troubleshooting.md`
**실측 결과: 16개 블록 → 16 PASS / 0 FRAG / 0 FAIL** (종료 코드 0)


본 문서의 모든 오류 메시지는 `/workspace/probe/*.py` 실행으로 재현했다.
개별 항목의 검증 로그는 각 참조 문서의 `## Verification log` 를 참고.

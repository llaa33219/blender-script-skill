# Grease Pencil & Video Sequencer — Blender 5.2.2 LTS 완전 검증 가이드

> 이 문서의 모든 코드 스니펫은 `/usr/local/bin/blender` 의 **Blender 5.2.2 LTS**
> (`d13f752e3b9c`, build 2026-09-15, 번들 Python 3.13.13) 에서 실제로 실행되어
> `__SCRIPT_OK__` 를 낸다. 실행하지 않은 코드는 이 문서에 없다.
> 2.8/3.x/4.x 시절 API 를 기억한 채로 5.x 에 붙이면 **거의 다 죽는다.** 아래에서 무엇이
> 바뀌었는지 전수 표로 정리한다.

---

## 0. 검증 환경과 결론 요약

### 0.1 실행 프로토콜

```bash
blender -b --factory-startup -noaudio --python-exit-code 1 --python verify/NN_이름.py
```

- `--python-exit-code 1` 을 **반드시** 붙인다. 없으면 예외가 나도 종료코드가 0 이다.
- 성공 판정 센티넬: 스크립트 끝에 `print("__SCRIPT_OK__")`.
- Cycles 는 `addon_utils.enable("cycles", default_set=True, persistent=True)` 로 켠다
  (`--factory-startup` 에서 비활성). `sc.render.cycles` 속성은 **이 호출 뒤에야** 생긴다.
- Grease Pencil 을 렌더하려면 GPU 컨텍스트가 필요하다 (§A5.4).

### 0.2 Part A — Grease Pencil 요약

| 질문 | 5.2.2 에서 확인된 사실 |
|---|---|
| `bpy.data.grease_pencils` 존재? | ✅ 존재. `bpy.types.GreasePencil` (ID) 컬렉션 |
| `obj.data` 타입? | `bpy.types.GreasePencil`. `Object.type` enum 에 `'GREASEPENCIL'` 존재 |
| 오브젝트 생성 | ✅ `bpy.ops.object.grease_pencil_add()` |
| 변환 | ✅ `bpy.ops.object.convert(target='GREASEPENCIL')` (MESH / CURVES 양쪽) |
| 드로우 레이어가 노드 그룹? | ❌ **아니다.** `gp.layers` 는 `GreasePencilLayer` 콜렉션이고 `NodeTree` 를 상속하지 않는다 |
| `gp.draw` ? | ❌ **5.2 에 없음** (4.x 에서 제거) |
| `gp.animation` ? | ❌ **5.2 에 없음** |
| 스트록 데이터 | `frame.drawing` → `GreasePencilDrawing` → `.attributes` (GeometrySet 스타일) |
| **포인트 추가 공개 API** | ❌ **없다.** `Attribute.data` 에 `.add()`/`.grow()` 가 없다. `new()` 로 만든 어트리뷰트는 길이 0 이고 늘릴 수 없다 |
| 그래도 스트록을 스크립트로 만들 수 있나? | ✅ **있다.** `grease_pencil_add(type='STROKE')` 가 175점 스트록을 만들어 주므로 그걸 `foreach_set` 로 재구성한다 (§A3.6) |
| `Material.use_filled_caps` ? | ❌ **5.2 RNA 전체에 존재하지 않는다** |
| `Material.grease_pencil` ? | 원본 데이터블럭에서는 항상 `None`. **평가된(evaluated) 머티리얼에서만** 접근 가능 |
| GP 패스 | ✅ `view_layer.use_pass_grease_pencil = True` → `CompositorNodeRLayers` 에 `'Grease Pencil'` 소켓 생성 |
| GP 모디파이어 위치 | `obj.modifiers` (데이터블럭/레이어가 **아님**). GP 전용 타입 26종 전부 실측 확인 |
| `bpy.data.paint_curves` | 생성 불가. `new()`/`load()` **둘 다 없고**, `PaintCurve` 는 스플라인 API가 제거된 빈 ID |
| `sculpt_curves` | 오퍼레이터 4개. `brush_stroke` 만 `poll=True` |

### 0.3 Part B — Video Sequencer 요약

| 질문 | 5.2.2 에서 확인된 사실 |
|---|---|
| `sequence_editor.sequences` ? | ❌ **존재하지 않는다.** `hasattr(se, 'sequences') == False` |
| 정답 이름 | ✅ **`sequence_editor.strips`** (+ `strips_all`) |
| `sequences` 로의 이동 경위 | 4.4: `bpy.types.Sequence`→`Strip` 리네임, `sequences`→`strips` **deprecated**. 5.0: deprecated 이름 **삭제**. → 5.x 에서는 `strips` 뿐 |
| 스트립 시간 프로퍼티 | 5.1 에서 리네임. 신/구 이름 **둘 다 존재** (구 이름은 deprecated, 6.0 제거 예정) |
| `frame_start` 타입 | **FLOAT** (4.x 에서는 INT) |
| 색상 스트립 생성 | `new_color` 없음. `strips.new_effect(type='COLOR', ..., length=N)` |
| `ColorStrip.color` | **3 floats (RGB)** — 4개를 넣으면 `ValueError` |
| `image_settings.file_format='FFMPEG'` | ⚠ **`media_type='VIDEO'` 를 먼저 설정해야** FFMPEG 가 열거에 나타난다 (5.x 신규) |
| `bpy.ops.sequencer.*` 헤드리스 | 기본 `-b` 에서 111개 중 **110개가 poll 실패**. 컨텍스트 레시피(§B10.4)를 쓰면 다수 동작 |
| `bpy.ops.clip.*` 헤드리스 | 92개 전부 poll 실패. CLIP_EDITOR 레시피(§B11.4)로 **추적까지 실제 수행 가능** |

---

# Part A — Grease Pencil (5.x)

## A1. 데이터 모델

### A1.1 무엇인가

5.x 의 Grease Pencil 은 3.x 까지의 "메시 + `bpy.types.GPencil`" 모델을 완전히 새로
썼다. 지금의 계층은 이렇다.

```
Scene.collection
 └─ Object  (Object.type == 'GREASEPENCIL')
     └─ Object.data  →  bpy.types.GreasePencil   (ID)
         ├─ .layers        : GreasePencilLayer      (컬렉션, RO)
         │    ├─ .frames   : GreasePencilFrame     (컬렉션, RO)
         │    │    └─ .drawing : GreasePencilDrawing
         │    │         ├─ .attributes       (AttributeGroupGreasePencilDrawing)
         │    │         ├─ .color_attributes (AttributeGroupGreasePencilDrawing)
         │    │         ├─ .curve_offsets
         │    │         ├─ .type   ('DRAWING' | 'REFERENCE')
         │    │         └─ .user_count
         │    ├─ .mask_layers : GreasePencilLayerMask
         │    └─ (레이어 자체 속성: opacity / blend_mode / tint_* / hide / …)
         ├─ .layer_groups : GreasePencilLayerGroup (컬렉션, RO)
         │    └─ .children  : GreasePencilTreeNode (레이어·그룹 공통 베이스)
         ├─ .root_nodes   : GreasePencilTreeNode   (레이어 트리를 펼친 평탄 목록, RO)
         ├─ .materials    : Material               (컬렉션, RO)
         ├─ .attributes / .color_attributes
         └─ .stroke_depth_order ('2D' | '3D'), .onion_* , .ghost_* , .use_autolock_layers …
```

### A1.2 `bpy.data.grease_pencils`

```python
import bpy

# ✅ 실행 검증됨
print(type(bpy.data.grease_pencils))          # <class 'bpy_prop_collection'>
bpy.ops.object.grease_pencil_add(type='EMPTY')
print(len(bpy.data.grease_pencils))           # 1
print(bpy.data.grease_pencils[0].name)        # 'GPencil'
print(bpy.data.grease_pencils[0].bl_rna.identifier)   # 'GreasePencil'
```

`BlendData.paint_curves`/`sounds`/`movieclips` 과 달리 `grease_pencils` 는 읽기/쓰기가 모두 된다.
`grease_pencils.new(...)` 는 존재하지 않고, 오브젝트 생성으로만 만들어진다.

> **주의**: 5.0 에서 옛 Grease Pencil(애너테이션) API 는 전부 이름이 바뀌었다.
> `bpy.types.GPencilStroke` → `AnnotationStroke`, `bpy.types.GPencilLayer` → `AnnotationLayer`,
> `bpy.data.grease_pencils`(구) → `bpy.data.annotations` 등.
> 그래서 `bpy.types.Annotation*` 타입이 아직 남아 있고, `bpy.ops.gpencil.*` 그룹(7개)에는
> **애너테이션 전용** 오퍼레이터만 들어 있다(`annotate`, `annotation_add`, `layer_annotation_add`, …).
> 새 GP 는 `bpy.ops.grease_pencil.*` (123개) 다룬다.

### A1.3 오브젝트 생성: `bpy.ops.object.grease_pencil_add`

✅ 헤드리스 OK (`-b` 에서 `{'FINISHED'}`).

| 파라미터 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `type` | ENUM | `'EMPTY'` | `EMPTY` / `STROKE` / `MONKEY` / `LINEART_SCENE` / `LINEART_COLLECTION` / `LINEART_OBJECT` |
| `align` | ENUM | `'WORLD'` | `WORLD` / `VIEW` / `CURSOR` |
| `location` | FLOAT[3] | `(0,0,0)` | `align='WORLD'` 일 때만 의미 있음 |
| `rotation` | FLOAT[3] | `(0,0,0)` | |
| `scale` | FLOAT[3] | `(0,0,0)` | ⚠ 기본값 0 — 스케일 0 오브젝트가 만들어질 수 있음 |
| `radius` | FLOAT | `1.0` | 스탬프 기본 반지름 |
| `use_in_front` | BOOLEAN | `True` | 뷰포트에서 항상 앞 |
| `use_lights` | BOOLEAN | `True` | 오브젝트 라이트 사용 (`Object.use_grease_pencil_lights`) |
| `stroke_depth_offset` | FLOAT | `0.05` | 2D 모드 깊이 오프셋 |
| `stroke_depth_order` | ENUM | `'2D'` | `2D` / `3D` |

```python
import bpy
bpy.ops.object.grease_pencil_add(type='STROKE', radius=1.0)
o = bpy.context.active_object
print(o.type, o.data.bl_rna.identifier)          # GREASEPENCIL GreasePencil
print([l.name for l in o.data.layers])           # ['Color', 'Lines']
print([m.name for m in o.data.materials])        # ['Black','White','Red','Green','Blue','Grey']
```

각 `type` 이 만드는 계층 (실측):

| `type` | 생성된 레이어 | 비고 |
|---|---|---|
| `EMPTY` | `['Layer']` | 프레임 1개, `position` 길이 0 |
| `STROKE` | `['Color', 'Lines']` | `Lines` 에 **175점 스트록 1개**. `material_index` 포함 |
| `MONKEY` | `['Fills', 'Lines']` | Suzanne 실루엣 |
| `LINEART_SCENE` | `['Layer']` | 씬 전체 라인아트 지오메트리 |
| `LINEART_COLLECTION` | `['Layer']` | 컬렉션 라인아트 |
| `LINEART_OBJECT` | `['Layer']` | 오브젝트 라인아트 |

### A1.4 변환: `bpy.ops.object.convert(target='GREASEPENCIL')`

✅ 헤드리스 OK. **MESH** 와 **CURVES** 양쪽에서 동작한다 (실측).

```python
import bpy
# CURVES → GREASEPENCIL
cu = bpy.data.curves.new("Wave", type='CURVE')
sp = cu.splines.new('POLY'); sp.points.add(31)
sp.points.foreach_set('co', [c for i in range(32)
                             for c in (-0.8+1.6*i/31, 0.3*0.0, 0.0, 1.0)])
o = bpy.data.objects.new("Wave", cu)
bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.objects.active = o
o.select_set(True)
print(bpy.ops.object.convert(target='GREASEPENCIL'))    # {'FINISHED'}
print(o.type, o.data.bl_rna.identifier)                 # GREASEPENCIL GreasePencil
```

> ⚠ **중요 함정**: CURVES 에서 변환된 드로잉에는 **`material_index` 어트리뷰트가 없다.**
> 그래서 `gp.materials` 에 아무리 재질을 붙여도 렌더는 항상 **무채색 기본 흰색**으로 나온다
> (실측: 순수 백색 `(0.796, 0.796, 0.796)`).
> 커스텀 머티리얼이 먹히는 스트록을 원하면 §A3.6 의 `type='STROKE'` 레시피를 쓸 것.

### A1.5 `bpy.types.GreasePencil` 전수 프로퍼티 (실측)

`RO` = 읽기 전용. `[함수]` 는 RNA 함수라 제외했다.

| 프로퍼티 | 타입 | RO | 기본값 | 비고 |
|---|---|---|---|---|
| `after_color` | FLOAT | ✗ | 0.0 | 고스트 앞 색 |
| `before_color` | FLOAT | ✗ | 0.0 | 고스트 뒤 색 |
| `attributes` | COLLECTION→`Attribute` | ✅ | | ID 레벨 attributes |
| `color_attributes` | COLLECTION→`Attribute` | ✅ | | |
| `ghost_after_range` | INT | ✗ | 1 | |
| `ghost_before_range` | INT | ✗ | 1 | |
| `id_type` | ENUM | ✅ | | `GREASEPENCIL`, `GREASEPENCIL_V3` 등 |
| `is_runtime_data` | BOOLEAN | ✗ | False | |
| `layer_groups` | COLLECTION→`GreasePencilLayerGroup` | ✅ | | §A2.2 |
| `layers` | COLLECTION→`GreasePencilLayer` | ✅ | | §A2 |
| `materials` | COLLECTION→`Material` | ✅ | | 슬롯 0부터 |
| `onion_factor` | FLOAT | ✗ | 0.5 | |
| `onion_keyframe_type` | ENUM | ✗ | `ALL` | `ALL`/`KEYFRAME`/`BREAKDOWN`/`MOVING_HOLD`/`EXTREME`/`JITTER`/`GENERATED` |
| `onion_mode` | ENUM | ✗ | `ABSOLUTE` | `ABSOLUTE`/`RELATIVE`/`SELECTED` |
| `root_nodes` | COLLECTION→`GreasePencilTreeNode` | ✅ | | 레이어+그룹 펼친 목록 |
| `stroke_depth_order` | ENUM | ✗ | `'2D'` | `2D` / `3D` |
| `use_autolock_layers` | BOOLEAN | ✗ | False | |
| `use_extra_user` | BOOLEAN | ✗ | False | |
| `use_fake_user` | BOOLEAN | ✗ | False | |
| `use_ghost_custom_colors` | BOOLEAN | ✗ | False | |
| `use_onion_fade` | BOOLEAN | ✗ | False | |
| `use_onion_loop` | BOOLEAN | ✗ | False | |
| `tag` | BOOLEAN | ✗ | False | |

인스턴스 메소드: `copy()`, `rename()`, `make_local()`, `user_clear()`, `user_remap()`,
`override_create()`, `override_hierarchy_create()`, `asset_mark()`, `asset_clear()`,
`asset_generate_preview()`, `preview_ensure()`, `update_tag()`, `unit_test_compare()`.

**없는 것** (2.8/3.x 습관): `gp.draw`, `gp.animation`, `gp.blend_alpha_mode`,
`gp.is_stroke_model_surface`, `gp.use_filled_caps`.

---

## A2. 드로우 레이어 API

### A2.1 "레이어가 노드 그룹" 이라는 전제 — **틀렸다**

질문서에 "`gp.layers` 로 열거하고, 레이어가 `GreasePencil` 노드 트리를 가진 노드 그룹이다"
라고 되어 있었지만, 5.2.2 실체는 그렇지 않다.

```python
import bpy
bpy.ops.object.grease_pencil_add(type='EMPTY')
gp = bpy.context.active_object.data
lay = gp.layers.active or gp.layers[0]

print(type(lay))                                     # <class 'bpy.types.GreasePencilLayer'>
print([c.__name__ for c in type(lay).__mro__])
# ['GreasePencilLayer', 'bpy_struct', 'object']      ← NodeTree 를 상속하지 않는다
print('node_tree' in type(lay).bl_rna.properties)   # False
print('drawing'   in type(lay).bl_rna.properties)   # False  ← frames[].drawing 로 간다
```

`GreasePencilDrawing` 도 `NodeTree` 가 아니다:

```python
print([c.__name__ for c in bpy.types.GreasePencilDrawing.__mro__])
# ['GreasePencilDrawing', 'bpy_struct', 'object']
```

5.2 에서 `GreasePencil` 이 가진 "노드 트리류" 타입은 전부 **단일 노드**다:
`bpy.types.GreasePencilTreeNode` (mro `['GreasePencilTreeNode','bpy_struct','object']`).
`GreasePencilLayer` 와 `GreasePencilLayerGroup` 이 이 타입을 상속하는 **공통 베이스**로 쓰인다.

### A2.2 레이어 트리 세 가지 접근법

| 경로 | 타입 | 의미 |
|---|---|---|
| `gp.layers` | `bpy.types.GreasePencilv3Layers` | 최상위+그룹 안 전부. 컬렉션 타입 헬퍼 |
| `gp.layer_groups` | COLLECTION→`GreasePencilLayerGroup` | 그룹만 |
| `gp.root_nodes` | COLLECTION→`GreasePencilTreeNode` | 레이어와 그룹을 **순서대로 평탄화**한 목록 |

`gp.layers.new()` 가 반환하는 실제 헬퍼는 `bpy.types.GreasePencilv3Layers` 이고, 메서드는:

| 메서드 | 시그니처 | 비고 |
|---|---|---|
| `new` | `new(name, set_active=True, layer_group=None)` | 새 레이어. **프레임 0개로 시작** |
| `remove` | `remove(layer)` | |
| `active` | (property) | 활성 레이어. 새로 만든 오브젝트는 `None` 일 때가 있다 |
| `move` | `move(layer, type)` | |
| `move_top` / `move_bottom` | `move_top(layer)` / `move_bottom(layer)` | |
| `move_to_layer_group` | `move_to_layer_group(layer, layer_group)` | |

`bpy.types.GreasePencilTreeNode` (레이어·그룹 공통) 전수 (실측):

| 프로퍼티 | 타입 | RO | 기본값 |
|---|---|---|---|
| `channel_color` | FLOAT | ✗ | 0.0 |
| `hide` | BOOLEAN | ✗ | False |
| `lock` | BOOLEAN | ✗ | False |
| `name` | STRING | ✗ | `''` |
| `next_node` | POINTER→`GreasePencilTreeNode` | ✅ | |
| `parent_group` | POINTER→`GreasePencilLayerGroup` | ✅ | |
| `prev_node` | POINTER→`GreasePencilTreeNode` | ✅ | |
| `select` | BOOLEAN | ✗ | False |
| `use_masks` | BOOLEAN | ✗ | True |
| `use_onion_skinning` | BOOLEAN | ✗ | True |

`bpy.types.GreasePencilLayerGroup` 에 추가되는 것:

| 프로퍼티 | 타입 | RO | 기본값 |
|---|---|---|---|
| `children` | COLLECTION→`GreasePencilTreeNode` | ✅ | (레이어+그룹) |
| `color_tag` | ENUM | ✗ | `NONE` — `NONE`/`COLOR1`…`COLOR8` (⚠ 언더스코어 없음) |
| `is_expanded` | BOOLEAN | ✗ | False |

`GreasePencilLayerGroup` 은 **데이터 API 로 만들 수 없다** — `gp.layer_groups` 는 RO 콜렉션이고
`new()` 가 없다. 만드는 방법은 `bpy.ops.grease_pencil.layer_group_add()` (✅ FINISHED) 뿐이다.

### A2.3 `bpy.types.GreasePencilLayer` 전수 프로퍼티 (실측)

| 프로퍼티 | 타입 | RO | 기본값 | 비고 |
|---|---|---|---|---|
| `blend_mode` | ENUM | ✗ | `REGULAR` | `REGULAR`/`HARDLIGHT`/`ADD`/`SUBTRACT`/`MULTIPLY`/`DIVIDE` |
| `channel_color` | FLOAT | ✗ | 0.0 | |
| `frames` | COLLECTION→`GreasePencilFrame` | ✅ | | §A2.4 |
| `hide` | BOOLEAN | ✗ | False | |
| `ignore_locked_materials` | BOOLEAN | ✗ | False | |
| `lock` | BOOLEAN | ✗ | False | |
| `lock_frame` | BOOLEAN | ✗ | False | |
| `mask_layers` | COLLECTION→`GreasePencilLayerMask` | ✅ | | |
| `matrix_local` | FLOAT | ✅ | 0.0 | |
| `matrix_parent_inverse` | FLOAT | ✅ | 0.0 | |
| `name` | STRING | ✗ | `''` | |
| `next_node` | POINTER→`GreasePencilTreeNode` | ✅ | | |
| `opacity` | FLOAT | ✗ | 0.0 | |
| `parent` | POINTER→`Object` | ✗ | | 오브젝트 레벨 옵션 |
| `parent_bone` | STRING | ✗ | `''` | |
| `parent_group` | POINTER→`GreasePencilLayerGroup` | ✅ | | |
| `pass_index` | INT | ✗ | 0 | GP 패스 인덱스 |
| `prev_node` | POINTER→`GreasePencilTreeNode` | ✅ | | |
| `radius_offset` | FLOAT | ✗ | 0.0 | |
| `rotation` | FLOAT | ✗ | 0.0 | 오브젝트 레벨 옵션 |
| `scale` | FLOAT | ✗ | 0.0 | 오브젝트 레벨 옵션 |
| `select` | BOOLEAN | ✗ | False | |
| `tint_color` | FLOAT[3] | ✗ | 0.0 | ⚠ **RGB 3 floats** (4 넣으면 `ValueError`) |
| `tint_factor` | FLOAT | ✗ | 0.0 | |
| `translation` | FLOAT | ✗ | 0.0 | 오브젝트 레벨 옵션 |
| `use_lights` | BOOLEAN | ✗ | False | |
| `use_masks` | BOOLEAN | ✗ | True | |
| `use_onion_skinning` | BOOLEAN | ✗ | True | |
| `use_viewlayer_masks` | BOOLEAN | ✗ | True | |
| `viewlayer_render` | STRING | ✗ | `''` | |

`GreasePencilLayerMask`: `hide`, `invert`, `name` — 3개뿐.

### A2.4 프레임

`bpy.types.GreasePencilFrame` (실측 전수):

| 프로퍼티 | 타입 | RO |
|---|---|---|
| `drawing` | POINTER→`GreasePencilDrawing` | ✗ |
| `frame_number` | INT | ✅ |
| `keyframe_type` | ENUM | ✗ — `KEYFRAME`/`BREAKDOWN`/`MOVING_HOLD`/`EXTREME`/`JITTER`/`GENERATED` |
| `select` | BOOLEAN | ✗ |

`layer.frames` 헬퍼 (`bpy.types.GreasePencilFrames`) 의 메서드: `new(frame_number)`, `remove(frame_number)`, `find`, `copy`, `move`.

```python
import bpy
bpy.ops.object.grease_pencil_add(type='EMPTY')
gp = bpy.context.active_object.data
lay = gp.layers[0]
print(len(lay.frames))            # 1 (type='EMPTY' 는 1개로 시작)
lay.frames.new(5)
print([f.frame_number for f in lay.frames])   # [1, 5]
# ⚠ 새로 만든 프레임의 position 은 길이 0 이고 Python 으로 늘릴 수 없다
print(len(lay.frames[1].drawing.attributes['position'].data))   # 0
```

---

## A3. 스트록 / 포인트 데이터

### A3.1 진짜 데이터 위치

스트록 데이터는 **3중 중첩**이다.

```
grease_pencil.layers[i]                      GreasePencilLayer
  .frames[j]                                  GreasePencilFrame
    .drawing                                  GreasePencilDrawing
      .attributes['position']                 Attribute (POINT, FLOAT_VECTOR)
      .attributes['radius']                   Attribute (POINT, FLOAT)
      .attributes['material_index']           Attribute (CURVE, INT)
      .curve_offsets                          프로퍼티 없는 컬렉션 (커브 경계)
      .color_attributes                       이름 있는 색 어트리뷰트
```

`bpy.types.GreasePencilDrawing` 전수 (실측):

| 프로퍼티 | 타입 | RO | 비고 |
|---|---|---|---|
| `attributes` | COLLECTION→`Attribute` | ✅ | `AttributeGroupGreasePencilDrawing` |
| `color_attributes` | COLLECTION→`Attribute` | ✅ | |
| `curve_offsets` | (컬렉션) | | 길이 = 스트록 개수. `find`/`foreach_get`/`foreach_set` 만 |
| `type` | ENUM | ✅ | `DRAWING` / `REFERENCE` |
| `user_count` | INT | ✅ | |

`Attribute` 공통 API:

| 프로퍼티 | 타입 | RO | 값 |
|---|---|---|---|
| `data` | COLLECTION (값 원소) | ✅ | ⚠ **`add()` 없음** |
| `data_type` | ENUM | ✅ | `FLOAT`,`INT`,`BOOLEAN`,`FLOAT_VECTOR`,`FLOAT_COLOR`,`QUATERNION`,`FLOAT4X4`,`STRING`,`INT8`,`INT16_2D`,`INT32_2D`,`FLOAT2`,`FLOAT4`,`BYTE_COLOR` |
| `domain` | ENUM | ✅ | `POINT`,`EDGE`,`FACE`,`CORNER`,`CURVE`,`INSTANCE`,`LAYER` |
| `is_internal` / `is_required` | BOOLEAN | ✅ | |
| `name` | STRING | ✗ | |
| `storage_type` | ENUM | ✅ | `ARRAY` / `SINGLE` |

값 원소 타입: `FloatAttributeValue`(`value`), `IntAttributeValue`(`value`),
`ByteIntAttributeValue`(`value`), `BoolAttributeValue`(`value`),
`FloatVectorAttributeValue`(`vector`), `Float2AttributeValue`(`vector`),
`Float4AttributeValue`(`vector`), `QuaternionAttributeValue`(`vector`),
`ByteColorAttributeValue`(`color`).

### A3.2 실측된 어트리뷰트 이름표 (어느 경로로 만들었는지에 따라 다르다)

| 생성 경로 | 어트리뷰트 (name, domain, data_type, 길이) |
|---|---|
| `grease_pencil_add(type='STROKE')` → `Lines` | `position`(POINT,FLOAT_VECTOR,175) · `curve_type`(CURVE,INT8,1) · `radius`(POINT,FLOAT,175) · `opacity`(POINT,FLOAT,175) · `cyclic`(CURVE,BOOLEAN,1) · `material_index`(CURVE,INT,1) |
| `grease_pencil_add(type='EMPTY')` | `position`(POINT,FLOAT_VECTOR,0) 만 |
| `convert(target='GREASEPENCIL')` ← **CURVES** | `position`(…,96) · `curve_type` · `cyclic` · `tilt`(POINT,FLOAT) · `normal_mode`(CURVE,INT8) · `radius` — **`material_index` 없음** |
| `convert(target='GREASEPENCIL')` ← **MESH** | `position` · `curve_type` · `cyclic` · `UVMap`(POINT,FLOAT2) · `.select_vert`/`.select_edge`/`.select_poly`/`.uv_select_*` · `radius` |
| `convert(target='GREASEPENCIL')` ← MESH (fill 모드) | `position` · `curve_type` · `cyclic` · `material_index` · `fill_id`(CURVE,INT) · `hide_stroke`(CURVE,BOOLEAN) · `.select_vert` |

5.x 스트록 속성의 의미:

| 속성 | 의미 | 3.x 대응 |
|---|---|---|
| `position` | 3D 위치. 4성분(x,y,z,weight)이나 `foreach_set` 은 **3개만** 받는다 | `co` |
| `radius` | 스트록 두께 (브러시 압력으로 그려진 값) | `pressure` |
| `opacity` | 불투명도 (2D 모드) | `fill_opacity` |
| `tilt` | 경사각 (2D 모드, CURVES 변환에서만) | `pressure` + fill |
| `curve_type` | 커브 종류 (도트/선 등) | — (신규) |
| `material_index` | `gp.materials` 슬롯 인덱스 | `material_index` |
| `cyclic` | 닫힌 곡선 여부 | `cyclic_u` 근사 |
| `fill_id` | 2D 필 묶음 ID | `fill_id` |
| `hide_stroke` | 필로만 표시 | — |

### A3.3 ❌ 포인트 추가 공개 API 는 **없다** (정직한 결론)

질문서가 물은 "5.2 에 안정적인 공개 데이터 API 가 없으면 그렇게 말하라" 에 대한 답은
**없다** 이다. 실측 근거:

```python
import bpy
bpy.ops.object.grease_pencil_add(type='EMPTY')
d = bpy.context.active_object.data.layers[0].frames[0].drawing
pos = d.attributes['position']

# 1) data 컬렉션이 제공하는 메서드
print([m for m in dir(pos.data) if not m.startswith('_')])
# ['bl_rna', 'find', 'foreach_get', 'foreach_set', 'get', 'items', 'keys', 'rna_type', 'values']
#  → add / grow / clear / reset / extend 전부 없다

# 2) 새 어트리뷰트를 만들어도 길이 0 으로 고정
a = d.attributes.new(name="mine", type='FLOAT', domain='POINT')
print(len(a.data))                     # 0
a.data.foreach_set('value', [0.5]*4)
# RuntimeError: TypeError foreach_set(...) sequence length mismatch given 4, needed 0

# 3) curve_offsets 도 마찬가지
print([m for m in dir(d.curve_offsets) if not m.startswith('_')])
# ['bl_rna', 'find', 'foreach_get', 'foreach_set']  ← add 없음
```

### A3.4 `foreach_set` 의 함정: FLOAT_VECTOR 은 **3 floats**

`position` 은 `data_type='FLOAT_VECTOR'` 이고 원소마다 4성분(x,y,z,weight)이 들지만,
`foreach_set('vector', …)` 는 **원소당 3개**를 요구한다. 4개를 주면

```
RuntimeError: internal error setting the array
Error: Array length mismatch (expected 192, got 256)   # 64점 × 3 vs 64점 × 4
```

weight(4번째 성분)는 `pos.data[i].vector` 로 **개별 대입**해야 한다.

### A3.5 오퍼레이터 경로 — 전부 막혀 있다

드로우 오퍼레이터는 `-b` 에서 `{'PASS_THROUGH'}` 를 돌려주거나 `poll()` 이 `False` 다.
`temp_override` 로 VIEW_3D 영역(백그라운드에서도 `bpy.data.screens['Layout'].areas` 에
실제로 존재한다)을 붙여도 동일하다.

```python
import bpy
bpy.ops.object.grease_pencil_add(type='EMPTY')
o = bpy.context.active_object
scr = bpy.data.screens['Layout']
area = next(a for a in scr.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(window=bpy.context.window_manager.windows[0],
                               screen=scr, area=area, region=region):
    print(bpy.ops.grease_pencil.primitive_line.poll())    # True
    print(bpy.ops.grease_pencil.primitive_line())         # {'PASS_THROUGH'}  ← 아무것도 안 그려짐
print(len(o.data.layers[0].frames[0].drawing.attributes['position'].data))   # 0 (그대로)
```

`{'PASS_THROUGH'}` 는 modal 오퍼레이터가 헤드리스에서 이벤트를 못 받고 그대로 통과한다는 뜻이다.

### A3.6 ✅ 동작하는 유일한 공개 경로: `type='STROKE'` 를 골라 재구성

`bpy.ops.object.grease_pencil_add(type='STROKE')` 는 **실제 스트록 데이터**를 만들어 준다.
175점짜리 직선을 임의의 곡선으로 `foreach_set` 로 덮어쓰면 된다. 이때 `material_index`
어트리뷰트가 이미 존재하므로 커스텀 머티리얼도 제대로 먹는다.

```python
import bpy, math
import numpy as np

bpy.ops.object.grease_pencil_add(type='STROKE', radius=1.0)
o  = bpy.context.active_object
gp = o.data

d = gp.layers['Lines'].frames[0].drawing
N  = len(d.attributes['position'].data)          # 175

pos = d.attributes['position']
arr = np.zeros(N * 3, dtype='f')                 # ← 3 floats / 원소
for i in range(N):
    t = i / (N - 1)
    arr[i*3+0] = -0.85 + 1.7 * t
    arr[i*3+1] = 0.32 * math.sin(t * math.pi * 2.0)
    arr[i*3+2] = 0.0
pos.data.foreach_set('vector', arr)              # ✅

d.attributes['radius'].data.foreach_set('value', np.full(N, 0.06, dtype='f'))
d.attributes['opacity'].data.foreach_set('value', np.full(N, 1.0,  dtype='f'))
d.attributes['material_index'].data[0].value = 2 # 슬롯 0 Black 1 White 2 Red 3 Green 4 Blue 5 Grey
```

점 개수를 175개보다 늘리거나 줄이고 싶으면 — 못 한다. `foreach_set` 은 **기존 길이만** 쓴다.
`curve_offsets` 도 조작 불가이므로 스트록 분할/병합 역시 데이터 API 로는 불가능하다.
(그것은 `bpy.ops.grease_pencil.stroke_split` / `join_selection` 처럼 이미 만들어진 스트록에만
작동하는 오퍼레이터다.)

---

## A4. 머티리얼

### A4.1 `use_filled_caps` 는 5.2 에 없다

`bpy.types` 의 **모든 클래스**의 RNA를 스캔해서 확인했다.

```python
import bpy
hits = []
for cn in dir(bpy.types):
    c = getattr(bpy.types, cn, None)
    rna = getattr(c, 'bl_rna', None)
    if rna and 'use_filled_caps' in rna.properties:
        hits.append(cn)
print(hits)        # []   ← 존재하지 않는다
```

남아 있는 것은 `Curve.use_fill_caps` / `SurfaceCurve.use_fill_caps` / `TextCurve.use_fill_caps`
(커브 계열) 뿐이고, GP 전용 캡 설정은 5.2 에서 사라졌다. `Caps` 관련 실체는
`BrushGpencilSettings.caps_type` (`'ROUND'` 등) 과 `FreestyleLineStyle.caps` 다.

### A4.2 `Material` 에서 GP 전용으로 남은 것 (실측)

| 프로퍼티 | 타입 | 비고 |
|---|---|---|
| `grease_pencil` | POINTER→`MaterialGPencilStyle` | **원본 데이터블럭에서는 항상 `None`** |
| `is_grease_pencil` | BOOLEAN [RO] | 위와 동일하게 원본에선 `False` |
| `lineart` | POINTER→`MaterialLineArt` | ✅ 항상 접근 가능 |
| `line_color` | FLOAT | Freestyle 용 |
| `line_priority` | INT | |
| `thickness_mode` | ENUM | `SPHERE` / `SLAB` |
| `use_thickness_from_shadow` | BOOLEAN | |
| `blend_method` | ENUM | `OPAQUE`/`CLIP`/`HASHED`/`BLEND` |
| `surface_render_method` | ENUM | `DITHERED` / `BLENDED` |
| `pass_index` | INT | |
| `show_transparent_back` | BOOLEAN | |

**`Material.grease_pencil` 이 `None` 인 이유** — 평가된(evaluated) 복사본에서만 살아 있다:

```python
import bpy
bpy.ops.object.grease_pencil_add(type='STROKE')
o = bpy.context.active_object
m = bpy.data.materials.new('X'); o.data.materials.append(m)

print(m.is_grease_pencil, m.grease_pencil)          # False None  ← 원본

dg = bpy.context.evaluated_depsgraph_get()
em = o.evaluated_get(dg).material_slots[0].material
print(em.is_grease_pencil, em.grease_pencil)        # True <MaterialGPencilStyle>
```

⇒ **5.2 에서 GP 머티리얼 스타일(두께/혼합/홀드아웃 등)은 스크립트로 설정할 수 없다.**
외관은 셰이더 노드로 만드는 것이 유일한 방법이다.

`bpy.types.MaterialGPencilStyle` 전수 (평가된 인스턴스에서 실측):

`alignment_mode`(`PATH`/`OBJECT`/`FIXED`) · `alignment_rotation` · `color` · `fill_color` ·
`fill_image` · `fill_style`(`SOLID`/`GRADIENT`/`TEXTURE`) · `flip` · `ghost` ·
`gradient_type`(`LINEAR`/`RADIAL`) · `hide` · `is_fill_visible`[RO] · `is_stroke_visible`[RO] ·
`lock` · `mix_color` · `mix_factor` · `mix_stroke_factor` · `mode`(`LINE`/`DOTS`/`BOX`) ·
`pass_index` · `pixel_size` · `placement_count` · `placement_density` ·
`placement_mode`(`COUNT`/`RADIUS`/`DENSITY`) · `placement_radius_spacing` ·
`random_hue_factor` · `random_noise_scale` · `random_rotation_factor` ·
`random_saturation_factor` · `random_size_factor` · `random_strength_factor` ·
`random_value_factor` · `show_fill` · `show_stroke` · `stroke_image` ·
`stroke_style`(`SOLID`/`TEXTURE`) · `texture_angle` · `texture_clamp` · `texture_offset` ·
`texture_scale` · `use_fill_holdout` · `use_overlap_strokes` · `use_randomization` ·
`use_stroke_holdout`

### A4.3 라인아트 (5.x 에서 살아남은 것)

`bpy.types.MaterialLineArt` (실측 5개):

| 프로퍼티 | 타입 | 기본값 |
|---|---|---|
| `intersection_priority` | INT | 0 |
| `mat_occlusion` | INT | 1 |
| `use_intersection_priority_override` | BOOLEAN | False |
| `use_material_mask` | BOOLEAN | False |
| `use_material_mask_bits` | BOOLEAN | False |

`bpy.types.ObjectLineArt` (실측 6개):

| 프로퍼티 | 타입 | 기본값 | 값 |
|---|---|---|---|
| `crease_threshold` | FLOAT | 2.44346 | |
| `intersection_priority` | INT | 0 | |
| `usage` | ENUM | `INHERIT` | `INHERIT`/`INCLUDE`/`OCCLUSION_ONLY`/`EXCLUDE`/`INTERSECTION_ONLY`/`NO_INTERSECTION`/`FORCE_INTERSECTION` |
| `use_crease_override` | BOOLEAN | False | |
| `use_intersection_priority_override` | BOOLEAN | False | |

관련: `Collection.lineart_usage` / `lineart_use_intersection_mask` / `lineart_intersection_mask` /
`lineart_intersection_priority` / `use_lineart_intersection_priority`,
`RenderSettings.line_thickness`(1.0) / `line_thickness_mode`(`ABSOLUTE`),
`GreasePencilLineartModifier`(§A6).

### A4.4 노드로 GP 머티리얼 만들기 (실측 동작)

5.x 에서 `Material.use_nodes` 는 deprecated 이므로 **설정하지 않는다.**
새로 만든 머티리얼은 이미 `Principled BSDF` + `Material Output` 을 가진다.

```python
import bpy
mat = bpy.data.materials.new("GPInk")
bsdf = mat.node_tree.nodes['Principled BSDF']     # use_nodes 설정 없이 바로 존재
bsdf.inputs['Base Color'].default_value = (0.9, 0.25, 0.05, 1.0)
bsdf.inputs['Roughness'].default_value = 0.6
bpy.context.active_object.data.materials.append(mat)
```

> ⚠ **슬롯 인덱스 함정**: `type='STROKE'` 로 만든 오브젝트는 이미
> `['Black','White','Red','Green','Blue','Grey']` 6개 슬롯을 갖고 있다.
> `gp.materials.append(my_mat)` 은 **7번 슬롯**이 된다. 스트록을 원하는 색으로 칠하려면
> `d.attributes['material_index'].data[0].value = <슬롯 번호>` 를 **반드시** 설정한다.
> 실측: `material_index=0` 이면 `Black` 이라서 렌더가 완전 검정(평균 휘도 0.0003)이 된다.

---

## A5. 렌더링과 Grease Pencil 패스

### A5.1 GP 패스는 존재한다

```python
import bpy
sc = bpy.context.scene
vl = sc.view_layers[0]
print(vl.use_grease_pencil)            # True  ← 뷰 레이어 전체 GP on/off
vl.use_pass_grease_pencil = True
print(vl.use_pass_grease_pencil)       # True
```

`use_pass_grease_pencil = True` 로 렌더하면 `CompositorNodeRLayers` 노드에
**`'Grease Pencil'` 출력 소켓이 실제로 생긴다** (실측):

```python
ng = bpy.data.node_groups.new("Comp", 'CompositorNodeTree')
sc.compositing_node_group = ng
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
out = ng.nodes.new('NodeGroupOutput')
rl  = ng.nodes.new('CompositorNodeRLayers'); rl.scene = sc
print([s.name for s in rl.outputs])
# ['Image', 'Alpha', 'Noisy Image', 'Grease Pencil']   ← 이게 전부다
```

> ⚠ `CompositorNodeRLayers.layer` enum 은 **동적 등록**이라 `bl_rna` 로 보면
> `['PLACEHOLDER']` 만 나온다. 문자열 대입 + `try/except` 로 접근한다(프로토콜 규칙).

> ⚠ 5.0 에서 컴포지터 노드 트리는 `Scene.node_tree` / `CompositorNodeComposite` 가 사라지고
> `Scene.compositing_node_group` + Group Output 으로 옮겨갔다.

### A5.2 GP 관련 렌더 설정 전수 (실측)

| 위치 | 프로퍼티 | 기본값 | 비고 |
|---|---|---|---|
| `ViewLayer` | `use_grease_pencil` | True | 레이어 전체 GP 렌더 |
| `ViewLayer` | `use_pass_grease_pencil` | False | GP 전용 패스 |
| `RenderLayer` | `use_grease_pencil` | [RO] | RLayers 노드에서 읽힘 |
| `Scene.grease_pencil_settings` | `SceneGpencil` | | 아래 4개 |
| ↳ | `aa_samples` | 8 | |
| ↳ | `antialias_threshold` | 1.0 | |
| ↳ | `antialias_threshold_render` | 0.25 | |
| ↳ | `motion_blur_steps` | 8 | |
| `Object` | `use_grease_pencil_lights` | True | |
| `RenderSettings` | `simplify_gpencil_view_fill` | True | 뷰포트 전용 |
| `GreasePencil` | `stroke_depth_order` | `'2D'` | `2D`/`3D` |

### A5.3 `to_mesh()` 로 GP 지오메트리를 꺼낼 수는 없다

```python
dg = bpy.context.evaluated_depsgraph_get()
ev = bpy.context.active_object.evaluated_get(dg)
ev.to_mesh()      # RuntimeError: Error: Object does not have geometry data   (2D/3D 모두)
```

GP 는 지오메트리 ID 가 아니라 별도 파이프라인이라 depsgraph 를 통한 폴리곤 추출이 안 된다.

### A5.4 ⚠ GP 렌더는 GPU 컨텍스트를 요구한다 (환경 함정)

4.3 이후 GP 스트록/필 레이아웃이 GPU 파이프라인에 올라갔다. EGL 이 없는 컨테이너에서
GP 오브젝트를 렌더하려 하면 **Blender 가 SIGABRT 로 죽는다**(스크립트 예외가 아니라 프로세스 abort).

```
Couldn't open libEGL.so.1: libEGL.so.1: cannot open shared object file
/bin/bash: line 1: 377 Aborted   blender -b ...
```

해결책(전부 실측):

```bash
apt-get install -y libegl1 libgl1-mesa-dri libglx-mesa0
export LIBGL_ALWAYS_SOFTWARE=1 EGL_PLATFORM=surfaceless
blender -b --factory-startup -noaudio --gpu-backend opengl --python-exit-code 1 --python your_script.py
```

이 조합에서 `gpu.init()` 이 성공하고 llvmpipe OpenGL 4.5 컨텍스트가 열린다:

```
backend: OPENGL
renderer: 'llvmpipe (LLVM 15.0.6, 256 bits)'
vendor: 'Mesa/X.org'
version: '4.5 (Core Profile) Mesa 22.3.6'
```

단, EGL surface 가 없어 `EGL Error (0x3009): EGL_BAD_MATCH` 가 stderr 에 계속 찍힌다.
**무시해도 렌더 결과는 정확하다** (아래 측정값이 그것을 증명한다).

---

## A6. 모디파이어

### A6.1 모디파이어는 **오브젝트**에 산다

```python
import bpy
bpy.ops.object.grease_pencil_add(type='EMPTY')
o  = bpy.context.active_object
gp = o.data
print('modifiers' in type(gp).bl_rna.properties)                 # False
print('modifiers' in type(gp.layers[0]).bl_rna.properties)       # False
print('modifiers' in type(o).bl_rna.properties)                  # True
m = o.modifiers.new("Build", type='GREASE_PENCIL_BUILD')
print(m.bl_rna.identifier, m.type)                               # GreasePencilBuildModifier GREASE_PENCIL_BUILD
print(m.id_data)                                                 # <Object>  ← 오브젝트의 자식
```

`Object.modifiers` 헬퍼: `new(name, type)`, `remove(modifier)`, `clear()`, `active`.

### A6.2 GP 모디파이어 타입 26종 — 전부 실측 추가 성공

전체 `type` enum 은 83개이고, 그중 GP 계열은 26개다. 아래는
`GREASEPENCIL` 오브젝트에 실제로 `modifiers.new()` 로 추가해서 확인한 결과다.

| `type` 문자열 | RNA 클래스 | `type` 문자열 | RNA 클래스 |
|---|---|---|---|
| `GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY` | `GreasePencilWeightProximityModifier` | `GREASE_PENCIL_SUBDIV` | `GreasePencilSubdivModifier` |
| `GREASE_PENCIL_COLOR` | `GreasePencilColorModifier` | `GREASE_PENCIL_ENVELOPE` | `GreasePencilEnvelopeModifier` |
| `GREASE_PENCIL_TINT` | `GreasePencilTintModifier` | `GREASE_PENCIL_OUTLINE` | `GreasePencilOutlineModifier` |
| `GREASE_PENCIL_OPACITY` | `GreasePencilOpacityModifier` | `GREASE_PENCIL_HOOK` | `GreasePencilHookModifier` |
| `GREASE_PENCIL_VERTEX_WEIGHT_ANGLE` | `GreasePencilWeightAngleModifier` | `GREASE_PENCIL_NOISE` | `GreasePencilNoiseModifier` |
| `GREASE_PENCIL_TIME` | `GreasePencilTimeModifier` | `GREASE_PENCIL_OFFSET` | `GreasePencilOffsetModifier` |
| `GREASE_PENCIL_TEXTURE` | `GreasePencilTextureModifier` | `GREASE_PENCIL_SMOOTH` | `GreasePencilSmoothModifier` |
| `GREASE_PENCIL_ARRAY` | `GreasePencilArrayModifier` | `GREASE_PENCIL_THICKNESS` | `GreasePencilThickModifierData` |
| `GREASE_PENCIL_BUILD` | `GreasePencilBuildModifier` | `GREASE_PENCIL_LATTICE` | `GreasePencilLatticeModifier` |
| `GREASE_PENCIL_LENGTH` | `GreasePencilLengthModifier` | `GREASE_PENCIL_DASH` | `GreasePencilDashModifierData` |
| `LINEART` | `GreasePencilLineartModifier` | `GREASE_PENCIL_ARMATURE` | `GreasePencilArmatureModifier` |
| `GREASE_PENCIL_MIRROR` | `GreasePencilMirrorModifier` | `GREASE_PENCIL_SHRINKWRAP` | `GreasePencilShrinkwrapModifier` |
| `GREASE_PENCIL_MULTIPLY` | `GreasePencilMultiplyModifier` | | |
| `GREASE_PENCIL_SIMPLIFY` | `GreasePencilSimplifyModifier` | | |

> ⚠ `LINEART` 만 예외적으로 `GREASE_PENCIL_` 접두사가 없다.
> ⚠ 3.x 의 `GREASE_PENCIL_LINEART` 이름은 없고, 3.x 의 `GPENCIL_*`(Build/Solidify 등)는
> 전부 위 표의 이름으로 바뀌었다. `GREASE_PENCIL_SUBSURF` 같은 이름은 **존재하지 않는다**
> (`TypeError: ObjectModifiers.new(): error with keyword argument "type"`).

### A6.3 `modifiers.new()` 는 실패해도 **예외를 던지지 않는다**

```python
import bpy
bpy.ops.mesh.primitive_cube_add()
mo = bpy.context.active_object
m = mo.modifiers.new("x", type='GREASE_PENCIL_COLOR")
print(m)     # None      ← raise 없이 그냥 None 반환
```

따라서 항상 `None` 체크를 해야 한다.

### A6.4 공통 모디파이어 필터 프로퍼티

거의 모든 GP 모디파이어가 이들을 공유한다(실측, `GreasePencilThickModifierData` 기준).

| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `is_active` | BOOLEAN | False | 스택에서 활성 |
| `show_viewport` / `show_render` | BOOLEAN | False | |
| `show_in_editmode` / `show_on_cage` / `show_expanded` | BOOLEAN | False | |
| `invert_layer_filter` | BOOLEAN | False | |
| `invert_layer_pass_filter` | BOOLEAN | False | |
| `invert_material_filter` | BOOLEAN | False | |
| `invert_material_pass_filter` | BOOLEAN | False | |
| `layer_pass_filter` | INT | 0 | |
| `material_filter` | POINTER→`Material` | None | |
| `material_pass_filter` | INT | 0 | |
| `use_layer_group_filter` | BOOLEAN | False | |
| `use_layer_pass_filter` / `use_material_pass_filter` | BOOLEAN | False | |
| `tree_node_filter` | STRING | `''` | |
| `persistent_uid` | INT [RO] | 0 | |
| `execution_time` | FLOAT [RO] | 0.0 | |
| `is_override_data` | BOOLEAN [RO] | False | |
| `use_apply_on_spline` | BOOLEAN | False | |
| `use_pin_to_last` | BOOLEAN | False | |
| `invert_vertex_group` | BOOLEAN | False | (일부) |

`GreasePencilBuildModifier` 고유: `frame_start`(1.0) · `frame_end`(125.0) · `length`(100.0) ·
`mode`(`SEQUENTIAL`/`CONCURRENT`/`ADDITIVE`) · `concurrent_time_alignment`(`START`/`END`) ·
`fade_factor` · `fade_opacity_strength` · `fade_thickness_strength`.

`GreasePencilThickModifierData` 고유: `thickness`(0.02) · `thickness_factor`(1.0) ·
`use_uniform_thickness` · `use_custom_curve` · `custom_curve`(POINTER→`CurveMapping`) ·
`use_weight_factor` · `vertex_group_name` · `invert_vertex_group`.

`GreasePencilLineartModifier` 고유: `stroke_depth_offset`(0.05) · `fill_strokes`(False).

### A6.5 레이어 그룹 안의 모디파이어 세그먼트

`GREASE_PENCIL_DASH` 와 `GREASE_PENCIL_TIME` 는 `.segments` 컬렉션을 갖는다:
`GreasePencilDashModifierSegment`, `GreasePencilTimeModifierSegment`.
`GreasePencilDashModifierData.segments` 는 `bpy.ops.object.grease_pencil_dash_modifier_segment_add/move/remove`
(✅ 헤드리스 OK)로 다룬다.

---

## A7. `sculpt_curves` / `paintcurve` / `bpy.data.paint_curves`

### A7.1 `bpy.ops.sculpt_curves` — 4개

커브(그리고 그.convert 결과인 GP) 를 sculpt 모드에서 브러시로 조각하는 오퍼레이터군.

| 오퍼레이터 | `-b` poll | 판정 | 비고 |
|---|---|---|---|
| `sculpt_curves.brush_stroke` | **True** | ✅ | 커브 오브젝트를 활성화하고 편집 모드에 들어가면 실제로 동작 |
| `sculpt_curves.min_distance_edit` | False | ❌ | 선택된 포인트 필요 |
| `sculpt_curves.select_grow` | False | ❌ | |
| `sculpt_curves.select_random` | False | ❌ | |

### A7.2 `bpy.ops.paintcurve` — 8개, **전부 헤드리스 불가**

| 오퍼레이터 | `-b` poll | 판정 |
|---|---|---|
| `paintcurve.new` | False | ❌ |
| `paintcurve.draw` | False | ❌ |
| `paintcurve.add_point` | False | ❌ |
| `paintcurve.add_point_slide` | False | ❌ |
| `paintcurve.delete_point` | False | ❌ |
| `paintcurve.slide` | False | ❌ |
| `paintcurve.select` | False | ❌ |
| `paintcurve.cursor` | False | ❌ |

모두 3D 뷰포트 + 페인트 모드 컨텍스트가 필수다.

### A7.3 `bpy.data.paint_curves` — **생성도 로드도 불가능**

```python
import bpy
print(type(bpy.data.paint_curves), len(bpy.data.paint_curves))
print([m for m in dir(bpy.data.paint_curves) if not m.startswith('_')])
# ['bl_rna', 'find', 'foreach_get', 'foreach_set', 'get', 'items', 'keys',
#  'remove', 'rna_type', 'tag', 'values']
#  → new() 없음, load() 없음
```

그리고 `bpy.types.PaintCurve` 자체가 **빈 껍데기**다. 2.8~4.x 에 있던
`.splines[].points[].co` 가 전부 사라졌다.

```python
print([k for k in bpy.types.PaintCurve.bl_rna.properties
       if bpy.types.PaintCurve.bl_rna.properties[k].type != 'FUNCTION'])
# ['asset_data', 'id_type', 'is_editable', 'is_embedded_data', 'is_evaluated',
#  'is_library_indirect', 'is_linked_packed', 'is_missing', 'is_runtime_data',
#  'library', 'library_weak_reference', 'name', 'name_full', 'original',
#  'override_library', 'preview', 'rna_type', 'session_uid', 'tag',
#  'use_extra_user', 'use_fake_user', 'users']
#  → splines 도 points 도 없다. 순수 ID 껍데기.
```

⇒ **5.2 에서 페인트 커브는 Python 으로 만들 수 없다.** `.blend` 파일로 불러오거나
UI(`paintcurve.new`)로 만드는 수밖에 없다.

### A7.4 `bpy.data.curves`와의 관계

`PaintCurve`(동적 페인트용)와 `bpy.data.curves`(일반 커브)는 **무관한 별개 ID**다
(`id_type` enum 에 `CURVE` 와 `PAINTCURVE` 가 따로 있다). 다만 GP 쪽에서는
`bpy.data.curves` 가 실제 역할을 한다:

1. `bpy.data.curves.new(name, type='CURVE')` 로 스플라인을 만들고
2. `bpy.ops.object.convert(target='GREASEPENCIL')` 로 GP 로 바꾸면
   **실제 스트록 어트리뷰트가 생성**된다 (§A1.4).
   단 `material_index` 가 빠져서 커스텀 머티리얼이 안 먹는다 (§A3.6).
3. `Object.type == 'CURVES'`(신형 헤어/곡선) 도 `Object.type` enum 에 있으며
   `bpy.data.hair_curves` 가 별도 컬렉션이다.

`bpy.types.CurvePaintSettings` (페인트 브러시가 쓰는 설정, 실측):
`corner_angle`(1.22173) · `curve_type`(`POLY`/`BEZIER`) · `depth_mode`(`CURSOR`/`SURFACE`) ·
`error_threshold`(8) · `fit_method`(`REFIT`/`SPLIT`) · `radius_max`(1.0) · `radius_min`(0.0) ·
`radius_taper_end` · `radius_taper_start` · `surface_offset` ·
`surface_plane`(`NORMAL_VIEW`/`NORMAL_SURFACE`/`VIEW`) · `use_corners_detect`(True) ·
`use_offset_absolute` · `use_pressure_radius` · `use_project_only_selected` ·
`use_stroke_endpoints`.

동적 페인트 자체는 아직 살아있다: `DynamicPaintModifier` → `canvas_settings`, `brush_settings`.

---

## A8. `bpy.ops.grease_pencil.*` 123개 헤드리스 판정 (전수 스윕)

판정 기준: `-b --factory-startup` 에서 `type='STROKE'` GP 오브젝트를 활성화한 상태로
`poll()` 후 바로 호출. 123개 전부를 스윕한 결과다.

| 판정 | 개수 | 의미 |
|---|---|---|
| ✅ | **75** | `-b` 에서 `{'FINISHED'}` |
| ⚠ | **5** | poll 은 True 인데 `{'CANCELLED'}` (선택/활성 레이어 부족) |
| ❌ (modal) | **8** | `{'PASS_THROUGH'}` — headless 에서 아무 것도 하지 않음 |
| ❌ (poll 실패) | **35** | `poll()` 이 `False` → `RuntimeError` |
| **합계** | **123** | |

#### ✅ — OK (75개) — `-b` 에서 `{'FINISHED'}`

| 오퍼레이터 | 판정 | 반환/예외 |
|---|---|---|
| `grease_pencil.active_frame_delete` | ✅ | `{'FINISHED'}` |
| `grease_pencil.caps_set` | ✅ | `{'FINISHED'}` |
| `grease_pencil.clean_loose` | ✅ | `{'FINISHED'}` |
| `grease_pencil.convert_curve_type` | ✅ | `{'FINISHED'}` |
| `grease_pencil.cyclical_set` | ✅ | `{'FINISHED'}` |
| `grease_pencil.delete` | ✅ | `{'FINISHED'}` |
| `grease_pencil.delete_frame` | ✅ | `{'FINISHED'}` |
| `grease_pencil.dissolve` | ✅ | `{'FINISHED'}` |
| `grease_pencil.duplicate` | ✅ | `{'FINISHED'}` |
| `grease_pencil.duplicate_move` | ✅ | `{'FINISHED'}` |
| `grease_pencil.extrude` | ✅ | `{'FINISHED'}` |
| `grease_pencil.extrude_move` | ✅ | `{'FINISHED'}` |
| `grease_pencil.frame_clean_duplicate` | ✅ | `{'FINISHED'}` |
| `grease_pencil.insert_blank_frame` | ✅ | `{'FINISHED'}` |
| `grease_pencil.interpolate_sequence` | ✅ | `{'FINISHED'}` |
| `grease_pencil.join_fills` | ✅ | `{'FINISHED'}` |
| `grease_pencil.join_selection` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_active` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_add` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_duplicate` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_duplicate_object` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_group_add` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_group_color_tag` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_group_remove` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_hide` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_isolate` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_lock_all` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_merge` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_move` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_remove` | ✅ | `{'FINISHED'}` |
| `grease_pencil.layer_reveal` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_copy_to_object` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_hide` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_isolate` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_lock_all` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_lock_unselected` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_lock_unused` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_reveal` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_select` | ✅ | `{'FINISHED'}` |
| `grease_pencil.material_unlock_all` | ✅ | `{'FINISHED'}` |
| `grease_pencil.outline` | ✅ | `{'FINISHED'}` |
| `grease_pencil.paintmode_toggle` | ✅ | `{'FINISHED'}` |
| `grease_pencil.reorder` | ✅ | `{'FINISHED'}` |
| `grease_pencil.reset_uvs` | ✅ | `{'FINISHED'}` |
| `grease_pencil.sculptmode_toggle` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_all` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_alternate` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_by_stroke_type` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_ends` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_fill` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_less` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_linked` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_more` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_random` | ✅ | `{'FINISHED'}` |
| `grease_pencil.select_similar` | ✅ | `{'FINISHED'}` |
| `grease_pencil.separate_fills` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_active_material` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_corner_type` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_curve_resolution` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_curve_type` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_handle_type` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_selection_mode` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_start_point` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_stroke_type` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_uniform_opacity` | ✅ | `{'FINISHED'}` |
| `grease_pencil.set_uniform_thickness` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_material_set` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_merge_by_distance` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_simplify` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_smooth` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_subdivide` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_subdivide_smooth` | ✅ | `{'FINISHED'}` |
| `grease_pencil.stroke_switch_direction` | ✅ | `{'FINISHED'}` |
| `grease_pencil.vertexmode_toggle` | ✅ | `{'FINISHED'}` |
| `grease_pencil.weightmode_toggle` | ✅ | `{'FINISHED'}` |

#### ⚠ — CANCEL (5개) — poll 은 True지만 결과가 `CANCELLED` (선택/컨텍스트 부족)

| 오퍼레이터 | 판정 | 반환/예외 |
|---|---|---|
| `grease_pencil.copy` | ⚠ | `{'CANCELLED'}` |
| `grease_pencil.frame_duplicate` | ⚠ | `{'CANCELLED'}` |
| `grease_pencil.remove_fill_guides` | ⚠ | `{'CANCELLED'}` |
| `grease_pencil.set_material` | ⚠ | `{'CANCELLED'}` |
| `grease_pencil.stroke_split` | ⚠ | `{'CANCELLED'}` |

#### ❌ — PASS_THROUGH (8개) — modal 드로우 오퍼레이터 — headless 에서 아무 것도 그리지 않음

| 오퍼레이터 | 판정 | 반환/예외 |
|---|---|---|
| `grease_pencil.interpolate` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.pen` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.primitive_arc` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.primitive_box` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.primitive_circle` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.primitive_curve` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.primitive_line` | ❌ | `{'PASS_THROUGH'}` |
| `grease_pencil.primitive_polyline` | ❌ | `{'PASS_THROUGH'}` |

#### ❌ — CALL_EXC (35개) — `poll()` 이 `False` → `RuntimeError`

| 오퍼레이터 | 판정 | 반환/예외 |
|---|---|---|
| `grease_pencil.bake_grease_pencil_animation` | ❌ | `RuntimeError` |
| `grease_pencil.brush_stroke` | ❌ | `RuntimeError` |
| `grease_pencil.delete_breakdown` | ❌ | `RuntimeError` |
| `grease_pencil.erase_box` | ❌ | `RuntimeError` |
| `grease_pencil.erase_lasso` | ❌ | `RuntimeError` |
| `grease_pencil.fill` | ❌ | `RuntimeError` |
| `grease_pencil.layer_mask_add` | ❌ | `RuntimeError` |
| `grease_pencil.layer_mask_remove` | ❌ | `RuntimeError` |
| `grease_pencil.layer_mask_reorder` | ❌ | `RuntimeError` |
| `grease_pencil.move_to_layer` | ❌ | `RuntimeError` |
| `grease_pencil.paste` | ❌ | `RuntimeError` |
| `grease_pencil.relative_layer_mask_add` | ❌ | `RuntimeError` |
| `grease_pencil.reproject` | ❌ | `RuntimeError` |
| `grease_pencil.sculpt_paint` | ❌ | `RuntimeError` |
| `grease_pencil.separate` | ❌ | `RuntimeError` |
| `grease_pencil.snap_cursor_to_selected` | ❌ | `RuntimeError` |
| `grease_pencil.snap_to_cursor` | ❌ | `RuntimeError` |
| `grease_pencil.snap_to_grid` | ❌ | `RuntimeError` |
| `grease_pencil.stroke_reset_vertex_color` | ❌ | `RuntimeError` |
| `grease_pencil.stroke_trim` | ❌ | `RuntimeError` |
| `grease_pencil.texture_gradient` | ❌ | `RuntimeError` |
| `grease_pencil.trace_image` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_brush_stroke` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_color_brightness_contrast` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_color_hsv` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_color_invert` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_color_levels` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_color_set` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_group_normalize` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_group_normalize_all` | ❌ | `RuntimeError` |
| `grease_pencil.vertex_group_smooth` | ❌ | `RuntimeError` |
| `grease_pencil.weight_brush_stroke` | ❌ | `RuntimeError` |
| `grease_pencil.weight_invert` | ❌ | `RuntimeError` |
| `grease_pencil.weight_sample` | ❌ | `RuntimeError` |
| `grease_pencil.weight_toggle_direction` | ❌ | `RuntimeError` |

> `bpy.ops.gpencil.*` 그룹(7개)은 5.0 부터 **애너테이션 전용**이다
> (`annotate`, `annotation_active_frame_delete`, `annotation_add`, `data_unlink`,
> `layer_annotation_add`, `layer_annotation_move`, `layer_annotation_remove`).
> Grease Pencil 오브젝트에는 쓰지 않는다.

---

# Part B — Video Sequencer (VSE)

## B8. 데이터 모델

### B8.1 `sequences` 는 없다 — `strips` 다 (5.2.2 실측)

```python
import bpy
sc  = bpy.context.scene
se  = sc.sequence_editor or sc.sequence_editor_create()
print(hasattr(se, 'sequences'))      # False   ← 5.x 에서 제거됨
print(hasattr(se, 'sequences_all'))  # False
print(hasattr(se, 'strips'))         # True
print(hasattr(se, 'strips_all'))     # True
```

**리네임 경위 (4.4 → 5.0 → 5.1):**

| 버전 | 일어난 일 |
|---|---|
| **4.4** | `bpy.types.Sequence` 및 모든 파생 타입을 `bpy.types.Strip` 으로 리네임. `SequenceEditor.sequences` → `.strips`, `.sequences_all` → `.strips_all`, `MetaStrip.sequences` → `.strips`, `context.active_sequence_strip` → `context.active_strip` 등 **구 이름은 deprecated 로 남겨둠** |
| **5.0** | deprecated 이름 **삭제**. 5.x 에서는 `strips` / `strips_all` 뿐. (`new_effect()` 의 `frame_end=` 인자가 `length=` 로 바뀜) |
| **5.1** | `strip.` **시간 프로퍼티** 리네임. 구 이름은 deprecated 로 남아 있으나 **6.0 에서 제거 예정** (PR#153012) |

타입 리네임 4.4 표 (발췌):

| 4.3 | 4.4+ (5.2 실재) |
|---|---|
| `bpy.types.Sequence` | `bpy.types.Strip` |
| `bpy.types.EffectSequence` | `bpy.types.EffectStrip` |
| `bpy.types.AddSequence` | `bpy.types.AddStrip` |
| `bpy.types.AdjustmentSequence` | `bpy.types.AdjustmentStrip` |
| `bpy.types.AlphaOverSequence` | `bpy.types.AlphaOverStrip` |
| `bpy.types.ColorSequence` | `bpy.types.ColorStrip` |
| `bpy.types.ColorMixSequence` | `bpy.types.ColorMixStrip` |
| `bpy.types.SpeedControlSequence` | `bpy.types.SpeedControlStrip` |
| `bpy.types.TextSequence` | `bpy.types.TextStrip` |
| `bpy.types.TransformSequence` | `bpy.types.TransformStrip` |
| `bpy.types.MovieSequence` | `bpy.types.MovieStrip` |
| `bpy.types.SequenceModifier` | `bpy.types.StripModifier` |
| `bpy.types.SequenceProxy` | `bpy.types.StripProxy` |
| `bpy.types.SequenceTransform` | `bpy.types.StripTransform` |
| `bpy.types.SequencesMeta` | `bpy.types.StripsMeta` |
| `bpy.types.Sequences` | `bpy.types.StripsTopLevel` |

> `bpy.types.Sequences` 도 `bpy.types.StripsMeta` 도 5.2 에 존재하지 않는다
> (확인: `hasattr(bpy.types,'Sequences') == False`).

### B8.2 시퀀스 에디터 만들기 (헤드리스)

```python
import bpy
sc = bpy.context.scene
se = sc.sequence_editor or sc.sequence_editor_create()   # ✅
print(se.bl_rna.identifier)                              # SequenceEditor
```

> ⚠ `Scene.sequence_editor` 는 **읽기 전용**(`is_readonly == True`)이다.
> 없으면 `scene.sequence_editor_create()` 로 만들어야 한다.
> ⚠ `--factory-startup` 의 기본 씬에는 **이미** 빈 `SequenceEditor` 가 붙어 있다
> (하지만 `bpy.data.scenes.new()` 로 만든 씬은 `None` 이다). 그래서 `or` 로 가드를 건다.

### B8.3 `bpy.types.SequenceEditor` 전수 (실측)

| 프로퍼티 | 타입 | RO | 기본값 | 비고 |
|---|---|---|---|---|
| `active_strip` | POINTER→`Strip` | ✗ | | 선택된 활성 스트립 |
| `cache_final_size` | INT | ✅ | | 픽셀 포맷 캐시 |
| `cache_raw_size` | INT | ✅ | | 원본 포맷 캐시 |
| `channels` | COLLECTION→`SequenceTimelineChannel` | ✅ | | |
| `meta_stack` | COLLECTION→`Strip` | ✅ | | |
| `overlay_frame` | INT | ✗ | 0 | |
| `proxy_dir` | STRING | ✗ | `''` | 프록시 기본 경로 |
| `proxy_storage` | ENUM | ✗ | `PER_STRIP` | `PER_STRIP` / `PROJECT` |
| `show_missing_media` | BOOLEAN | ✗ | False | |
| `show_overlay_frame` | BOOLEAN | ✗ | False | |
| `strips` | COLLECTION→`Strip` | ✅ | | 최상위 스트립 |
| `strips_all` | COLLECTION→`Strip` | ✅ | | 메타스트립 안까지 재귀 전부 |
| `use_cache_final` | BOOLEAN | ✗ | False | |
| `use_cache_raw` | BOOLEAN | ✗ | False | |
| `use_overlay_frame_lock` | BOOLEAN | ✗ | False | |
| `use_prefetch` | BOOLEAN | ✗ | False | |

`strips` 와 `strips_all` 는 **서로 다른 컬렉션 객체**다
(`se.strips_all is se.strips` → `False`). 메타스트립이 없으면 내용이 같지만,
메타스트립을 만들면 `strips_all` 에만 내부 스트립이 보인다.

`bpy.types.SequenceTimelineChannel` (5개):
`number`[RO] · `name` · `lock` · `mute` · `rna_type`

---

## B9. 스트립 추가

### B9.1 `se.strips` 컬렉션의 실제 메서드 (실측)

`se.strips` 의 RNA 타입은 `bpy.types.StripsTopLevel` 이고, 메서드는 8개 **뿐**이다.

| 메서드 | 시그니처 |
|---|---|
| `new_clip` | `new_clip(name, clip, channel, frame_start)` |
| `new_effect` | `new_effect(name, type, channel, frame_start, length=0, input1=None, input2=None)` |
| `new_image` | `new_image(name, filepath, channel, frame_start, fit_method='ORIGINAL')` |
| `new_mask` | `new_mask(name, mask, channel, frame_start)` |
| `new_meta` | `new_meta(name, channel, frame_start)` |
| `new_movie` | `new_movie(name, filepath, channel, frame_start, fit_method='ORIGINAL', stream=0)` |
| `new_scene` | `new_scene(name, scene, channel, frame_start)` |
| `new_sound` | `new_sound(name, filepath, channel, frame_start, stream=0)` |
| `remove` | `remove(sequence)` |

> ❌ **`new_color` 는 존재하지 않는다.** 색 스트립은
> `new_effect(name, type='COLOR', channel=..., frame_start=..., length=N)` 로 만든다.
> `new_effect` 의 `length` 를 주지 않으면 `RuntimeError: Error: Strips.new_effect: invalid length` 이 난다.
> `input1`/`input2` 를 요구하는 타입은 그 스트립을 넘겨야 하고, 안 넘기면
> `RuntimeError: Error: Strips.new_effect: effect takes N input strips` 가 난다.
> 4.5 에서 인자명이 `seq1`/`seq2` → `input1`/`input2` 로 바뀐 것도 기억해둘 것.

`new_effect` 의 `type` enum 전체 (17개, 실측):

`CROSS`, `ADD`, `SUBTRACT`, `ALPHA_OVER`, `ALPHA_UNDER`, `GAMMA_CROSS`, `MULTIPLY`, `WIPE`,
`GLOW`, `COLOR`, `SPEED`, `MULTICAM`, `ADJUSTMENT`, `GAUSSIAN_BLUR`, `TEXT`, `COLORMIX`,
`COMPOSITOR`

> ⚠ `TRANSFORM` 은 5.x 에서 제거됐다. 3.x/4.x 의 `new_effect(type='TRANSFORM')` 는 죽는다.
> 스트립 위치/스케일은 `strip.transform` (§B10.3) 으로 조작한다.

### B9.2 스트립 시간 프로퍼티 — 5.1 리네임표 (5.2.2 에서 실측)

`bpy.types.Strip` 전수 (실측). **구 이름과 신 이름이 둘 다 존재**하며 구 이름 접근 시
`DeprecationWarning: '<X>' is expected to be removed in Blender 6.0` 가 나온다.

| 5.2 이름 (권장) | 타입 | RO | 기본값 | 4.x / deprecated 이름 |
|---|---|---|---|---|
| `duration` | INT | ✗ | 0 | `frame_final_duration` |
| `left_handle` | INT | ✗ | 0 | `frame_final_start` |
| `right_handle` | INT | ✗ | 0 | `frame_final_end` |
| `left_handle_offset` | FLOAT | ✗ | 0.0 | `frame_offset_start` |
| `right_handle_offset` | FLOAT | ✗ | 0.0 | `frame_offset_end` |
| `content_start` | FLOAT | ✗ | 0.0 | `frame_start` (그리고 4.x 의 `frame_start`) |
| `content_trim_start` | INT | ✗ | 0 | `animation_offset_start` |
| `content_trim_end` | INT | ✗ | 0 | `animation_offset_end` |
| `content_end` | INT | ✅ | | **신규 (5.1)** — 읽기 전용 |
| `content_duration` | INT | ✅ | | `frame_duration` |
| `frame_duration` | INT | ✅ | | deprecated alias of `content_duration` |
| `frame_final_start` | INT | ✗ | 0 | deprecated |
| `frame_final_end` | INT | ✗ | 0 | deprecated |
| `frame_final_duration` | INT | ✗ | 0 | deprecated |
| `frame_offset_start` | FLOAT | ✗ | 0.0 | deprecated |
| `frame_offset_end` | FLOAT | ✗ | 0.0 | deprecated |
| `animation_offset_start` | INT | ✗ | 0 | deprecated |
| `animation_offset_end` | INT | ✗ | 0 | deprecated |
| `frame_start` | **FLOAT** | ✗ | 0.0 | deprecated — ⚠ 타입이 INT → FLOAT 로 바뀜 |

나머지 `Strip` 공통 프로퍼티 (실측):

| 프로퍼티 | 타입 | RO | 기본값 | 값 |
|---|---|---|---|---|
| `blend_alpha` | FLOAT | ✗ | 1.0 | |
| `blend_type` | ENUM | ✗ | `REPLACE` | 아래 28개 표 참조 |
| `channel` | INT | ✗ | 0 | 1부터 |
| `color_tag` | ENUM | ✗ | `NONE` | `NONE`,`COLOR_01`…`COLOR_09` |
| `connections` | COLLECTION→`Strip` | ✅ | | 5.x 신규 (입력으로 물린 스트립) |
| `effect_fader` | FLOAT | ✗ | 0.0 | |
| `left_handle_offset` / `right_handle_offset` | FLOAT | ✗ | 0.0 | |
| `lock` | BOOLEAN | ✗ | False | |
| `modifiers` | COLLECTION→`StripModifier` | ✅ | | §B10.3 |
| `mute` | BOOLEAN | ✗ | False | |
| `name` | STRING | ✗ | `''` | |
| `select` | BOOLEAN | ✗ | False | |
| `select_left_handle` / `select_right_handle` | BOOLEAN | ✗ | False | |
| `show_retiming_keys` | BOOLEAN | ✗ | False | |
| `type` | ENUM | ✅ | | 아래 24개 표 |

`Strip.type` enum 전체 (24개, 실측):
`IMAGE`, `META`, `SCENE`, `MOVIE`, `MOVIECLIP`, `MASK`, `SOUND`, `CROSS`, `ADD`, `SUBTRACT`,
`ALPHA_OVER`, `ALPHA_UNDER`, `GAMMA_CROSS`, `COMPOSITOR`, `MULTIPLY`, `WIPE`, `GLOW`, `COLOR`,
`SPEED`, `MULTICAM`, `ADJUSTMENT`, `GAUSSIAN_BLUR`, `TEXT`, `COLORMIX`

`Strip.blend_type` enum 전체 (28개, 실측):
`REPLACE`, `CROSS`, `DARKEN`, `MULTIPLY`, `BURN`, `LINEAR_BURN`, `LIGHTEN`, `SCREEN`, `DODGE`,
`ADD`, `OVERLAY`, `SOFT_LIGHT`, `HARD_LIGHT`, `VIVID_LIGHT`, `LINEAR_LIGHT`, `PIN_LIGHT`,
`DIFFERENCE`, `EXCLUSION`, `SUBTRACT`, `HUE`, `SATURATION`, `COLOR`, `VALUE`, `ALPHA_OVER`,
`ALPHA_UNDER`, `GAMMA_CROSS`

### B9.3 스트립 서브타입별 고유 프로퍼티 (실측 차분)

공통(`Strip`)을 뺀 **고유** 프로퍼티만 적는다.

#### `ImageStrip` (26개 고유)
| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `alpha_mode` | ENUM | `STRAIGHT` | `STRAIGHT` / `PREMUL` |
| `animation_offset_start` / `animation_offset_end` | INT | 0 | deprecated |
| `color_multiply` / `color_saturation` | FLOAT | 1.0 | |
| `colorspace_settings` | POINTER→`ColorManagedInputColorspaceSettings` | [RO] | |
| `content_trim_start` / `content_trim_end` | INT | 0 | |
| `crop` | POINTER→`StripCrop` | [RO] | `min_x`,`min_y`,`max_x`,`max_y` |
| `directory` | STRING | `''` | 이미지 시퀀스 디렉터리 |
| `elements` | COLLECTION→`StripElement` | [RO] | `filename`[✗], `orig_width/height/fps`[RO] |
| `multiply_alpha` | BOOLEAN | False | |
| `proxy` | POINTER→`StripProxy` | [RO] | 빌드 전에는 `None` |
| `retiming_keys` | COLLECTION→`RetimingKey` | [RO] | |
| `stereo_3d_format` | POINTER→`Stereo3dFormat` | [RO] | |
| `strobe` | FLOAT | 0.0 | |
| `transform` | POINTER→`StripTransform` | [RO] | §B10.3 |
| `use_deinterlace` / `use_flip_x` / `use_flip_y` / `use_float` / `use_multiview` / `use_proxy` / `use_reverse_frames` | BOOLEAN | False | |
| `views_format` | ENUM | `INDIVIDUAL` | `INDIVIDUAL` / `STEREO_3D` |

#### `MovieStrip` (28개 고유) = `ImageStrip` + 아래
| 프로퍼티 | 타입 | RO | 비고 |
|---|---|---|---|
| `filepath` | STRING | ✗ | `''` |
| `fps` | FLOAT | ✅ | 24.0 |
| `stream_index` | INT | ✗ | 오디오/비디오 스트림 선택 (5.x 신규) |

> ⚠ `MovieStrip` 에는 `use_proxy`/`proxy` 가 **없다** — 무비 스트립은 프록시를 쓰지 않는다.

#### `SoundStrip` (12개 고유)
| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `animation_offset_start` / `animation_offset_end` | INT | 0 | deprecated |
| `content_trim_start` / `content_trim_end` | INT | 0 | |
| `pan` | FLOAT | 0.0 | -1..1 |
| `pitch_correction` | BOOLEAN | True | |
| `retiming_keys` | COLLECTION→`RetimingKey` | [RO] | |
| `show_waveform` | BOOLEAN | True | |
| `sound` | POINTER→`Sound` | ✗ | `bpy.data.sounds` 의 ID |
| `sound_offset` | FLOAT | 0.0 | 오디오 내부 오프셋(초) |
| `volume` | FLOAT | 1.0 | |

#### `ColorStrip` (19개 고유)
| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `color` | FLOAT[3] | 0.0 | ⚠ **RGB 3 floats**. 4개 넣으면 `ValueError: ...should contain 3 items, not 4` |
| `color_multiply` / `color_saturation` | FLOAT | 1.0 | |
| `crop` | POINTER→`StripCrop` | [RO] | |
| `height` / `width` | INT | 0 | 색 스트립 크기 (0 = 렌더 크기) |
| `input_count` | INT | [RO] | 0 |
| `multiply_alpha` | BOOLEAN | False | |
| `proxy` | POINTER→`StripProxy` | [RO] | |
| `strobe` | FLOAT | 0.0 | |
| `transform` | POINTER→`StripTransform` | [RO] | |
| `use_deinterlace`/`use_flip_x`/`use_flip_y`/`use_float`/`use_proxy`/`use_reverse_frames` | BOOLEAN | False | |

#### `SceneStrip` (27개 고유)
| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `scene` | POINTER→`Scene` | ✗ | |
| `scene_camera` | POINTER→`Object` | ✗ | |
| `scene_input` | ENUM | `CAMERA` | `CAMERA` / `SEQUENCER` |
| `view_layer` | POINTER→`ViewLayer` | ✗ | |
| `fps` | FLOAT | [RO] | |
| `use_annotations` | BOOLEAN | True | |
| `volume` | FLOAT | 1.0 | 씬 오디오 |
| + `alpha_mode`, `color_multiply`, `color_saturation`, `content_trim_*`, `crop`, `multiply_alpha`, `proxy`, `retiming_keys`, `strobe`, `transform`, `use_deinterlace`, `use_flip_x/y`, `use_float`, `use_proxy`, `use_reverse_frames` | | | |

#### `MaskStrip` (18개 고유)
`mask`(POINTER→`Mask`) · `crop` · `transform` · `alpha_mode` · `color_multiply/saturation` ·
`content_trim_*` · `multiply_alpha` · `strobe` · `use_deinterlace` · `use_flip_x/y` ·
`use_float` · `use_reverse_frames`
(`use_proxy`/`proxy` 없음)

#### `TextStrip` (43개 고유)
| 프로퍼티 | 타입 | 기본값 | 값 |
|---|---|---|---|
| `text` | STRING | `''` | 본문 |
| `font` | POINTER→`VectorFont` | ✗ | |
| `font_size` | FLOAT | 0.0 | |
| `use_bold` / `use_italic` | BOOLEAN | False | |
| `color` / `outline_color` / `box_color` / `shadow_color` | FLOAT[4] | 0.0 | RGBA |
| `outline_width` | FLOAT | 0.05 | |
| `use_outline` / `use_box` / `use_shadow` | BOOLEAN | False | |
| `box_margin` | FLOAT | 0.01 | |
| `box_roundness` | FLOAT | 0.0 | |
| `shadow_angle` | FLOAT | 1.13446 | |
| `shadow_blur` | FLOAT | 0.0 | |
| `shadow_offset` | FLOAT | 0.04 | |
| `alignment_x` | ENUM | `LEFT` | `LEFT`/`CENTER`/`RIGHT` |
| `anchor_x` | ENUM | `LEFT` | `LEFT`/`CENTER`/`RIGHT` |
| `anchor_y` | ENUM | `TOP` | `TOP`/`CENTER`/`BOTTOM` |
| `location` | FLOAT[2] | 0.0 | |
| `wrap_width` | FLOAT | 0.0 | |
| `space_line` / `abs_space_line` | FLOAT | 1.0 | |
| `use_absolute_line_spacing` | BOOLEAN | False | |
| `textbox_state` | POINTER→`TextboxState` | [RO] | |
| + `crop`, `transform`, `proxy`, `strobe`, `input_count`[RO], `use_proxy` 등 | | | |

#### `EffectStrip` (15개 고유) = `alpha_mode`, `color_multiply`, `color_saturation`, `crop`,
`multiply_alpha`, `proxy`, `strobe`, `transform`, `use_deinterlace`, `use_flip_x/y`,
`use_float`, `use_proxy`, `use_reverse_frames`

#### `AdjustmentStrip` (20) = 위 + `animation_offset_*`, `content_trim_*`, `input_count`[RO]

#### `MetaStrip` (22)
`strips`[RO, COLLECTION→`Strip`] · `channels`[RO, COLLECTION→`SequenceTimelineChannel`] ·
`volume`(1.0) · + `EffectStrip` 공통 + `animation_offset_*`, `content_trim_*`
> ⚠ `MetaStrip.sequences` → `MetaStrip.strips` 로 리네임됨.

#### `MulticamStrip` (21) · `MovieClipStrip` (21) · `CompositorStrip` (19) · `ColorMixStrip` (20) · `SpeedControlStrip` (22)
| 타입 | 고유 프로퍼티 |
|---|---|
| `MulticamStrip` | `multicam_source`(INT 0) · `input_count`[RO] |
| `MovieClipStrip` | `clip`(POINTER→`MovieClip`) · `fps`[RO] · `stabilize2d`(False) · `undistort`(False) |
| `CompositorStrip` | `node_group`(POINTER→`NodeTree`) · `input_1`/`input_2`(POINTER→`Strip`) · `input_count`[RO] |
| `ColorMixStrip` | `blend_effect`(ENUM 21개: `DARKEN`…`VALUE`) · `factor`(0.0) · `input_1`/`input_2` · `input_count`[RO] |
| `SpeedControlStrip` | `speed_control`(ENUM: `STRETCH`/`MULTIPLY`/`FRAME_NUMBER`/`LENGTH`) · `speed_factor` · `speed_frame_number` · `speed_length` · `input_1` · `input_count`[RO] · `use_frame_interpolate`(False) |

### B9.4 스트립 생성과 시간 프로퍼티 실측

```python
import bpy, os
A = "/workspace/out/vse/assets"
sc = bpy.context.scene
se = sc.sequence_editor or sc.sequence_editor_create()

img = se.strips.new_image("SeqA", os.path.join(A, "seq_0001.png"), channel=1, frame_start=1)
img.elements.append("seq_0002.png"); img.elements.append("seq_0003.png"); img.elements.append("seq_0004.png")
img.duration = 4                                   # 5.1+ 이름

col = se.strips.new_effect("Cyan", type='COLOR', channel=2, frame_start=1, length=8)
col.color = (0.0, 1.0, 1.0)                        # RGB 3 floats
```

실측 출력 (5.2.2):

```
SeqA   IMAGE  ch=1 left_handle=1 right_handle=5 duration=4 content_start=1.0 content_end=5 content_duration=4
Cyan   COLOR  ch=2 left_handle=1 right_handle=9 duration=8 content_start=1.0 content_end=2 content_duration=1
```

`ColorStrip` 의 `content_duration == 1` 인 것은 색 스트립이 "1프레임짜리 소스" 를
`left/right_handle` 로 늘린다는 뜻이다. `ImageStrip` 는 요소 4개이므로 `content_duration == 4`.

---

## B10. 시퀀서 설정

### B10.1 씬 레벨

| 프로퍼티 | 기본값 | 비고 |
|---|---|---|
| `Scene.render.use_sequencer` | **True** | VSE 결과를 3D 렌더 대신 쓰기. 4.x 까지만 `False` 로 해둔 기억이 있으면 반대로 되어 있다 |
| `Scene.render.use_compositing` | True | |
| `Scene.sequence_editor` | [RO] | `sequence_editor_create()` 로 생성 |
| `Scene.render.fps` / `fps_base` | 24 / 1.0 | |
| `Scene.frame_start` / `frame_end` | 1 / 250 | |
| `Scene.use_preview_range` / `frame_preview_start` / `frame_preview_end` | | 재생 구간 |
| `SequenceEditor.strips.use_cache_raw` / `use_cache_final` | False | 프록시/캐시 |
| `SequenceEditor.proxy_storage` | `PER_STRIP` | `PER_STRIP` / `PROJECT` |
| `SequenceEditor.proxy_dir` | `''` | |
| `StripChannel.lock` / `.mute` / `.name` | | 채널 단위 |

`Scene.use_preview_range` 가 "preview_range" 이고, `SequenceEditor` 자체에는 preview_range 가 없다.

### B10.2 5.0 신규: `Workspace.sequencer_scene`

5.0 부터 VSE 는 컨텍스트로 **별도의 씬**을 쓴다. `context.scene`(윈도우 활성 씬)과
다를 수 있다. Python 에서는 이렇게 설정한다:

```python
import bpy
bpy.context.workspace.sequencer_scene = bpy.context.scene
print(bpy.context.sequencer_scene)       # <Scene "Scene">
```

이걸 안 설정하면 `bpy.ops.sequencer.*` poll 이 전부 실패한다 (§B10.4).

`bpy.types.WorkSpace` 에 `sequencer_scene` 이 있고, `bpy.data.screens` 는
`new()` 가 **없다** (`bpy.data.screens` 메서드: `bl_rna, find, foreach_get, foreach_set, get,
items, keys, remove, rna_type, values`).

### B10.3 `StripTransform` / `StripCrop` / `StripProxy` / `StripModifier` (실측 전수)

`bpy.types.StripTransform` (8개):

| 프로퍼티 | 타입 | 기본값 |
|---|---|---|
| `offset_x` / `offset_y` | FLOAT | 0.0 |
| `rotation` | FLOAT | 0.0 |
| `scale_x` / `scale_y` | FLOAT | 1.0 |
| `origin` | FLOAT | 0.0 |
| `filter` | ENUM | `AUTO` — `AUTO`/`NEAREST`/`BILINEAR`/`CUBIC_MITCHELL`/`CUBIC_BSPLINE`/`BOX` |

`bpy.types.StripCrop` (5개): `min_x`, `min_y`, `max_x`, `max_y` (모두 INT, 0).

`bpy.types.StripProxy` (11개, 실측) — ⚠ **프록시를 빌드하기 전에는 `strip.proxy` 가 `None`**:

| 프로퍼티 | 타입 | 기본값 |
|---|---|---|
| `build_25` / `build_50` / `build_75` / `build_100` | BOOLEAN | False |
| `directory` | STRING | `''` |
| `filepath` | STRING | `''` |
| `quality` | INT | 0 |
| `use_overwrite` | BOOLEAN | False |
| `use_proxy_custom_directory` | BOOLEAN | False |
| `use_proxy_custom_file` | BOOLEAN | False |

`bpy.types.StripModifier` (12개, 실측):

| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `type` | ENUM [RO] | | `BRIGHT_CONTRAST`, `COLOR_BALANCE`, `COMPOSITOR`, `CURVES`, `HUE_CORRECT`, `MASK`, `TONEMAP`, `WHITE_BALANCE`, `SOUND_EQUALIZER`, `PITCH`, `ECHO` (11개) |
| `enable` | BOOLEAN | True | |
| `is_active` | BOOLEAN | False | |
| `mute` | BOOLEAN | False | |
| `input_mask_type` | ENUM | `STRIP` | `STRIP` / `ID` |
| `input_mask_strip` | POINTER→`Strip` | ✗ | |
| `input_mask_id` | POINTER→`Mask` | ✗ | |
| `mask_time` | ENUM | `RELATIVE` | `RELATIVE` / `ABSOLUTE` |
| `name` | STRING | `''` | |
| `show_expanded` / `show_preview` | BOOLEAN | False | |

`strip.modifiers` 헬퍼: `new(name, type)`, `remove(modifier)`, `clear()`, `active`.
5.0 에서 `strip.modifiers.active` 가 추가됐다.

```python
mod = strip.modifiers.new("Bright", 'BRIGHT_CONTRAST')     # ✅ 헤드리스 OK
print(mod.bright, mod.contrast)                            # 0.0 0.0
print(strip.modifiers.active)                               # <BrightContrastModifier>
```

`MovieClipUser` (4개): `frame_current`(1) · `proxy_render_size`(ENUM `PROXY_25`/`PROXY_50`/
`PROXY_75`/`PROXY_100`/`FULL`) · `use_render_undistorted`.

### B10.4 `bpy.ops.sequencer.*` — 헤드리스 판정

#### (a) 그냥 `-b` 에서 부를 때

111개 전수 스윕 결과:

| 판정 | 개수 |
|---|---|
| ✅ `{'FINISHED'}` | **1** (`sequencer.text_strip_style_preset_add` 뿐) |
| ❌ `poll()` 실패 | **110** |

전부 `RuntimeError: Operator bpy.ops.sequencer.<op>.poll() failed, context is incorrect`
또는 `Context missing sequencer` 다. **이유는 3가지가 겹친다**:

1. SEQUENCE_EDITOR 영역이 없다
2. `context.sequencer_scene` 가 없다 (5.0 신규)
3. `SpaceSequenceEditor` 에 **`seqeditor` 포인터가 5.2 에서 제거**되어,
   에디터의 seqbase 에 스트립이 바인딩되지 않는다

> ⚠ **2번만 우회 가능하고 3번은 우회 불가**다. 그래서 아래 레시피로도
> "선택된 스트립" 이 필요한 오퍼레이터는 여전히 `poll()` 이 `False` 다.

#### (b) 컨텍스트 레시피로 쓸 때

```python
import bpy
sc  = bpy.context.scene
sc.render.fps = 24
se  = sc.sequence_editor or sc.sequence_editor_create()
# 스트립을 하나라도 만들어둔다
img = se.strips.new_image("I", "/path/seq_0001.png", 1, 1); img.duration = 4
sc.frame_set(3)

bpy.context.workspace.sequencer_scene = sc          # ① 5.0 신규 컨텍스트 씬
scr  = bpy.data.screens['Layout']
area = next(a for a in scr.areas if a.type == 'VIEW_3D')
area.type = 'SEQUENCE_EDITOR'                        # ② 백그라운드에서 영역 타입 변경이 된다
region = next(r for r in area.regions if r.type == 'WINDOW')
win = bpy.context.window_manager.windows[0]

with bpy.context.temp_override(window=win, screen=scr, area=area, region=region,
                               sequencer_scene=sc):
    bpy.ops.sequencer.select_all()      # {'FINISHED'}
    bpy.ops.sequencer.view_all()        # {'FINISHED'}
    bpy.ops.sequencer.refresh_all()     # {'FINISHED'}
```

> 이 레시피는 도큐먼트의 공식 권장(`temp_override`)과 다르고, 공식 권장으로는
> 부족하다. `area.type` 을 `VIEW_3D` → `SEQUENCE_EDITOR` 로 바꾸는 게 핵심이다.
> `area.regions` 는 백그라운드에서도 `WINDOW` 등 실제 리전 객체를 갖는다
> (헤더/툴바 리전의 width·height 는 1×1 이지만 `WINDOW` 은 1578×956).

#### (c) 레시피 적용 후 실측 결과

**✅ 동작 (poll=True & 실행됨)**

| 오퍼레이터 | 반환 | 비고 |
|---|---|---|
| `sequencer.select_all` | `{'FINISHED'}` | 단 실제 `strip.select` 는 안 바뀜(§주) |
| `sequencer.select_side_of_frame` | `{'FINISHED'}` | |
| `sequencer.select_linked` | `{'FINISHED'}` | |
| `sequencer.select_handles` | `{'FINISHED'}` | |
| `sequencer.select_circle` | `{'FINISHED'}` | |
| `sequencer.select_grouped` | `{'FINISHED'}` | |
| `sequencer.select_box` | `{'FINISHED'}` | |
| `sequencer.box_blade` | `{'FINISHED'}` | |
| `sequencer.mute` / `unmute` | `{'FINISHED'}` | |
| `sequencer.lock` / `unlock` | `{'FINISHED'}` | |
| `sequencer.duplicate` / `duplicate_move` / `duplicate_move_linked` | `{'FINISHED'}` | |
| `sequencer.copy` | `{'FINISHED'}` | 클립보드까지 동작 |
| `sequencer.paste` | `{'FINISHED'}` | "Info: 1 strips pasted" |
| `sequencer.delete` | `{'FINISHED'}` | |
| `sequencer.gap_remove` / `gap_insert` | `{'FINISHED'}` | |
| `sequencer.view_all` / `view_frame` / `view_all_preview` / `view_zoom_ratio` | `{'FINISHED'}` | |
| `sequencer.strip_transform_fit` / `strip_transform_clear` | `{'FINISHED'}` | |
| `sequencer.offset_clear` | `{'FINISHED'}` | |
| `sequencer.refresh_all` | `{'FINISHED'}` | |
| `sequencer.reload` | `{'FINISHED'}` | |
| `sequencer.rebuild_proxy` | `{'FINISHED'}` | |
| `sequencer.enable_proxies` | `{'FINISHED'}` | |
| `sequencer.strip_jump` | `{'FINISHED'}` | |
| `sequencer.deinterlace_selected_movies` | `{'FINISHED'}` | |
| `sequencer.retiming_freeze_frame_add` | `{'FINISHED'}` | |
| `sequencer.text_strip_style_preset_add` | `{'FINISHED'}` | 유일하게 레시피 없이도 동작 |
| `sequencer.sound_strip_add(move_strips=False)` | `{'FINISHED'}` | 스트립 생성까지 확인 |
| `sequencer.movie_strip_add(move_strips=False)` | `{'FINISHED'}` | 스트립 생성까지 확인 |
| `sequencer.effect_strip_add(move_strips=False)` | `{'FINISHED'}` | 스트립 생성까지 확인 |
| `sequencer.image_strip_add(directory=…, filemode=3, files=[{…}], move_strips=False)` | `{'FINISHED'}` | `files` 는 **dict 리스트** |
| `sequencer.scene_strip_add_new(move_strips=False)` | `{'FINISHED'}` | |
| `sequencer.strip_modifier_add(type=…)` | `{'FINISHED'}` | |

> ⚠ `move_strips=True`(기본값)면 이 오퍼레이터들이 **modal** 이 되어 헤드리스에서
> `{'PASS_THROUGH'}` 가 된다. 반드시 `move_strips=False` 를 넘길 것.
> (`image_strip_add` 는 `files=[{"name": "seq_0001.png"}]` 형태 —
> 문자열 리스트는 `TypeError: ...expected a each sequence member to be a dict`.)
> (`scene_strip_add` 의 `scene` 인자는 5.x 에서 **동적 ENUM** 이라 헤드리스에서
> `enum "Scene" not found in ()`. `scene_strip_add_new` 를 쓴다.)

**⚠ poll=True 인데 `{'CANCELLED'}` (조건 미충족)**

`select`, `select_less`, `select_more`, `select_side`, `select_handle`, `select_box`,
`select_lasso`, `snap`, `view_selected`, `swap`, `connect`, `disconnect`,
`set_range_to_strips`, `rendersize`, `retiming_show`, `retiming_add_transition_slide`,
`retiming_transition_add`, `strip_modifier_copy`, `strip_modifier_duplicate`,
`strip_modifier_move_to_index`, `strip_modifier_equalizer_redefine`, `duplicate_move_linked`,
`preview_duplicate_move`, `preview_duplicate_move_linked`, `slip`, `meta_make`,
`meta_toggle`, `meta_separate`, `select_handle`(PASS_THROUGH 포함).
전부 "에디터 seqbase 가 비어 있음" 이라 `Warning: Select one or more strips` /
`Error: Please select two strips` 로 취소된다.

**❌ 레시피 후에도 poll=False (22개) — 스트립 선택이 필수**

`cursor_set`, `strip_color_tag_set`, `strip_modifier_add`(레시피 후에도), `strip_modifier_remove`,
`strip_modifier_set_active`, `strip_modifier_move`, `strip_modifier_add_node_group`,
`fades_add`, `fades_clear`, `change_path`, `change_scene`, `text_insert`,
`text_delete`, `text_deselect_all`, `text_edit_mode_toggle`, `text_cursor_move`,
`text_cursor_set`, `text_line_break`, `text_select_all`, `text_edit_copy`, `text_edit_cut`,
`text_edit_paste`, `retiming_key_add`, `retiming_key_delete`, `retiming_reset`,
`retiming_add_freeze_frame_slide`, `retiming_segment_speed_set`, `reassign_inputs`,
`export_subtitles`, `view_ghost_border`, `scene_frame_range_update`, `split_multicam`.

**❌ 등록 자체가 안 된 이름 (호출 시 `AttributeError`)**

`bpy.ops.sequencer.color_strip_add`, `.zoom`, `.color_tag_set`, `.view_ndof`,
`.select_alternate`, `.new_image_strip` — `dir()` 에는 나오지만 RNA 등록이 없어서
`Polling operator "bpy.ops.sequencer.<name>" error, could not be found` 가 난다.
**`dir(bpy.ops.sequencer)` 의 결과를 그대로 믿으면 안 된다.**

> ⚠ **전수 스윕은 세그폴트를 일으킨다.** 레시피를 적용한 뒤 111개를 한 번에 돌리면
> 파일 브라우저 계열(`add_scene_strip_from_scene_asset` 등)에서 Blender 가 segfault 한다.
> 헤드리스에서 VSE 오퍼레이터를 스윕하면 **프로세스가 죽는다.** 목록으로 개별 호출할 것.

> **§주 — 왜 `select_all` 이 아무것도 못 하는가**
> ```python
> print(bpy.ops.sequencer.select_all())   # {'FINISHED'}
> print(img.select)                       # False
> print(se.active_strip)                  # None
> ```
> `SpaceSequenceEditor` 의 RNA 에 `seqeditor` 가 없고(5.2 에서 제거),
> `screen/area` 를 붙이는 것만으로는 에디터 seqbase 에 데이터가 오르지 않는다.
> **데이터 API(`strip.select = True`)로도 오퍼레이터 쪽은 못 속인다.**
> 결론: 헤드리스 VSE 스크립트는 **데이터 API 만 쓰는 것이 정석**이고,
> 오퍼레이터는 `view_all` / `refresh_all` 처럼 "선택 불필요" 계열만 쓴다.

---

## B11. Movieclips

### B11.1 `bpy.data.movieclips` — `new()` 없고 `load()` 뿐

```python
import bpy, os
clip = bpy.data.movieclips.load("/workspace/out/vse/assets/clip.mp4")
print(type(bpy.data.movieclips), len(bpy.data.movieclips))
print([m for m in dir(bpy.data.movieclips) if not m.startswith('_')])
# ['bl_rna','find','foreach_get','foreach_set','get','items','keys','load','remove','rna_type','tag','values']
print(bpy.data.movieclips.load.__doc__)
# BlendDataMovieClips.load(filepath, check_existing=False)
```

### B11.2 `bpy.types.MovieClip` (실측)

| 프로퍼티 | 타입 | RO | 기본값 | 비고 |
|---|---|---|---|---|
| `annotation` | POINTER→`Annotation` | ✗ | | 5.0 리네임 (옛 `grease_pencil`) |
| `colorspace_settings` | POINTER→`ColorManagedInputColorspaceSettings` | ✅ | | |
| `display_aspect` | FLOAT | ✗ | 1.0 | |
| `filepath` | STRING | ✗ | `''` | |
| `fps` | FLOAT | ✅ | 24.0 | |
| `frame_duration` | INT | ✅ | 24 | 총 프레임 수 |
| `frame_offset` | INT | ✗ | 0 | |
| `frame_start` | INT | ✗ | 1 | |
| `size` | INT[2] | ✅ | (64, 64) | |
| `source` | ENUM | ✅ | `MOVIE` | `SEQUENCE` / `MOVIE` |
| `use_proxy` | BOOLEAN | ✗ | False | |
| `proxy` | POINTER→`MovieClipProxy` | ✅ | | |
| `use_proxy_custom_directory` | BOOLEAN | ✗ | False | |
| `tracking` | POINTER→`MovieTracking` | ✅ | | §B11.3 |
| `users` | INT | ✅ | | ⚠ `MovieClip.users` 는 **int** 이다 (사용자 리스트 아님) |

### B11.3 추적 데이터 API

`clip.tracking` → `bpy.types.MovieTracking` (9개):
`active_object_index`(0) · `camera`[RO]·`dopesheet`[RO] · `objects`[RO] ·
`plane_tracks`[RO] · `reconstruction`[RO] · `settings`[RO] · `stabilization`[RO] ·
`tracks`[RO, `MovieTrackingTracks`]

`tracks.new()` → `MovieTrackingTrack` (실측 30개):
| 프로퍼티 | 타입 | 기본값 | 값 |
|---|---|---|---|
| `name` | STRING | `''` | |
| `color` | FLOAT[3] | 0.0 | |
| `offset` | FLOAT | 0.0 | |
| `weight` / `weight_stab` | FLOAT | 0.0 | |
| `margin` / `frames_limit` | INT | 0 | |
| `correlation_min` | FLOAT | 0.0 | |
| `motion_model` | ENUM | `Perspective` | `Perspective`/`Affine`/`LocRotScale`/`LocScale`/`LocRot`/`Loc` |
| `pattern_match` | ENUM | `KEYFRAME` | `KEYFRAME` / `PREV_FRAME` |
| `use_blue_channel` / `use_green_channel` / `use_red_channel` | BOOLEAN | True | |
| `use_brute` / `use_mask` / `use_normalization` / `use_custom_color` / `use_alpha_preview` / `use_grayscale_preview` | BOOLEAN | False | |
| `hide` / `lock` / `select` | BOOLEAN | False | |
| `select_anchor` / `select_pattern` / `select_search` | BOOLEAN | False | |
| `markers` | COLLECTION→`MovieTrackingMarker` | [RO] | |
| `annotation` | POINTER→`Annotation` | ✗ | 5.0 리네임 |
| `average_error` / `bundle` / `has_bundle` | | [RO] | |

`MovieTrackingMarkers` (실측 메서드): `insert_frame`, `delete_frame`, `find`, `find_frame`
— ⚠ **`new()` 가 없다.** 그리고 `co` 는 **키워드 전용**이다.

```python
track = clip.tracking.tracks[0] if len(clip.tracking.tracks) else clip.tracking.tracks.new()
track.markers.insert_frame(1, co=(0.1, 0.2))
track.markers.insert_frame(5, co=(0.3, 0.4))
print([(m.frame, tuple(m.co)) for m in track.markers])
# [(1, (0.1, 0.2)), (5, (0.3, 0.4))]
```

> ⚠ `t0.markers.new(1)` 은 `AttributeError: bpy_prop_collection: attribute "new" not found`.
> ⚠ `t0.markers.insert_frame(1, (0.1, 0.2))` 은
> `TypeError: required parameter "co" to be a keyword argument!`
> ⚠ `MovieTrackingMarkers` 는 순서 컬렉션이라 `insert_frame` 로 삽입한다
> (`bpy_prop_collection.add()` 없음).

`MovieTrackingMarker` 프로퍼티 (실측): `co` · `frame` · `mute` · `pattern_corners` ·
`pattern_bound_box` · `search_min` · `search_max` · `is_keyed`

`tracking.objects` → `MovieTrackingObjects` (실측). `new(name)` **1개 인자만** 받는다
(`clip` 을 넘기면 `TypeError: takes at most 1 arguments, got 2`).
`MovieTrackingObject` (실측 9개): `is_camera`[RO] · `keyframe_a` · `keyframe_b` ·
`name` · `plane_tracks`[RO] · `reconstruction`[RO] · `scale`(1.0) · `tracks`[RO].
> ⚠ `MovieTrackingObject` 에는 `camera`/`clip`/`constraints`/`rotation_mode` 속성이 **없다**
> (`AttributeError: ... Did you mean: 'is_camera'?` 등).

`tracking.camera` → `MovieTrackingCamera` (내재 계수, 실측 21개):
`focal_length` · `focal_length_pixels` · `sensor_width` · `pixel_aspect` · `principal_point` ·
`principal_point_pixels` · `k1`,`k2`,`k3` · `division_k1`,`division_k2` ·
`brown_p1`…`brown_p4` · `brown_k1`…`brown_k4` · `nuke_k1`,`nuke_k2`,`nuke_p1`,`nuke_p2` ·
`distortion_model`(ENUM `POLYNOMIAL`/`DIVISION`/`NUKE`/`BROWN`) ·
`units`(ENUM `PIXELS`/`MILLIMETERS`)

`tracking.settings` → `MovieTrackingSettings` (실측):
`default_pattern_size` · `default_search_size` · `default_frames_limit` · `default_margin` ·
`default_correlation_min` · `default_weight` · `default_motion_model` · `default_pattern_match` ·
`use_default_{red,green,blue}_channel` · `use_default_brute` · `use_default_mask` ·
`use_default_normalization` · `clean_action`(ENUM `SELECT`/`DELETE_TRACK`/`DELETE_SEGMENTS`) ·
`clean_error` · `clean_frames` · `speed`(ENUM `FASTEST`/`DOUBLE`/`REALTIME`/`HALF`/`QUARTER`) ·
`distance` · `object_distance` · `use_tripod_solver` · `use_keyframe_selection` ·
`refine_intrinsics_focal_length` · `refine_intrinsics_principal_point` ·
`refine_intrinsics_radial_distortion` · `refine_intrinsics_tangential_distortion`

### B11.4 `bpy.ops.clip.*` — 92개, 전부 `poll() == False` … 하지만 레시피로 복구된다

`-b` 에서 92개 전부가 `poll=False` 다. 그런데 **CLIP_EDITOR 레시피**로 전부 열린다.

```python
import bpy, os
clip = bpy.data.movieclips.load("/workspace/out/vse/assets/clip.mp4")
scr  = bpy.data.screens['Layout']
area = next(a for a in scr.areas if a.type == 'VIEW_3D')
area.type = 'CLIP_EDITOR'                       # ← 여기서 SPACECLIPEDITOR 가 된다
region = next(r for r in area.regions if r.type == 'WINDOW')
sp = area.spaces.active
sp.clip = clip                                 # SpaceClipEditor.clip 이 있다 (VSE 와의 차이!)
win = bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=win, screen=scr, area=area, region=region, clip=clip):
    bpy.ops.clip.detect_features()             # {'FINISHED'}  ← 진짜 추론 실행
    bpy.ops.clip.track_markers()               # {'FINISHED'}
    bpy.ops.clip.solve_camera()                # poll=True, 데이터 부족으로만 실패
```

| 오퍼레이터 | 레시피 후 | 비고 |
|---|---|---|
| `clip.set_active_clip` | `{'FINISHED'}` | |
| `clip.add_marker` | `{'FINISHED'}` | 마커 1개 생성됨 |
| `clip.clean_tracks` | `{'FINISHED'}` | |
| `clip.filter_tracks` | `{'FINISHED'}` | |
| `clip.average_tracks` | `{'CANCELLED'}` | |
| `clip.prefetch` | `{'PASS_THROUGH'}` | modal |
| `clip.delete_proxy` | `{'FINISHED'}` | |
| `clip.rebuild_proxy` | `{'CANCELLED'}` | |
| `clip.set_viewport_background` | `{'FINISHED'}` | |
| `clip.track_to_empty` | `{'FINISHED'}` | |
| `clip.view_all` | `{'FINISHED'}` | |
| `clip.bundles_to_mesh` | `{'FINISHED'}` | |
| `clip.stabilize_2d_add` | `{'FINISHED'}` | |
| **`clip.detect_features`** | `{'FINISHED'}` | ✅ 헤드리스에서 실제 피처 검출 수행 |
| **`clip.track_markers`** | `{'FINISHED'}` | ✅ 헤드리스에서 실제 마커 추적 수행 |
| `clip.solve_camera` | `RuntimeError: At least 8 common tracks on both keyframes are needed` | 컨텍스트는 OK, 데이터가 모자람 |
| `clip.set_plane` | `RuntimeError: Three tracks with bundles are needed to orient the floor` | 동일 |
| `clip.set_scale` | `RuntimeError: Two tracks with bundles should be selected to set scale` | 동일 |
| `clip.set_axis` | `RuntimeError: Single track with bundle should be selected to define axis` | 동일 |
| `clip.graph_select_all_markers` | poll=False | 그래프 에디터 컨텍스트 |
| `clip.dopesheet_view_all` | poll=False | 도프시트 컨텍스트 |

⇒ **질문서의 "일부 `bpy.ops.clip.*` 는 헤드리스에서도 부를 수 있다" 는 사실이 맞다.**
VSE 와 달리 CLIP_EDITOR 공간에는 `clip` 포인터가 남아 있어서 `temp_override` 가 먹는다.

---

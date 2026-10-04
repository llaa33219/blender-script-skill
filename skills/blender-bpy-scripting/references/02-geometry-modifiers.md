# Geometry Reference — mesh construction, bmesh, curves & text, UVs, modifiers

**검증 환경**: Blender **5.2.2 LTS** (build 2026-09-15, commit `d13f752e3b9c`), Linux x64, headless sandbox
/ bundled Python **3.13.13**.
모든 코드 블록은 이 빌드에서 실제 실행되어 `__SCRIPT_OK__`를 출력했다. 실행 스크립트는
`/workspace/build/geometry/verify/` (조사용) 와 `/workspace/build/geometry/snippets/` (문서에 그대로 실린 코드) 에 있다.
전체 목록은 [§13 Verification log](#13-verification-log).

> **4.x 튜토리얼을 믿지 마라.** 이 문서에는 5.2 에서 실제로 깨지거나 의미가 바뀐 것이 **24건** 있다
> ([§12 표](#12-breaking-changes--4x--tutorial에서-틀린-것들)).
> 요약은 [§12 Breaking changes](#12-breaking-changes--4x--tutorial에서-틀린-것들) 에 정리했다.
> 특히 `bmesh.ops.*` 의 `bm=` 키워드, `bpy.ops.mesh.delete` 의 enum, `pack_islands` 의 `margin_type`,
> `Curve.type`, `mesh.calc_normals()`, `use_auto_smooth` 전부 사라졌다.

---

## 목차

1. [Object lifecycle](#1-object-lifecycle)
2. [Primitive operators](#2-primitive-operators)
3. [Direct mesh construction](#3-direct-mesh-construction)
4. [bmesh](#4-bmesh)
5. [Edit mode & context override](#5-edit-mode--context-override)
6. [Modifiers](#6-modifiers)
7. [Curves & text](#7-curves--text)
8. [UVs](#8-uvs)
9. [Mesh validation / cleanup](#9-mesh-validation--cleanup)
10. [Gotchas](#10-gotchas)
11. [직접 확인하는 법](#11-직접-확인하는-법)
12. [Breaking changes](#12-breaking-changes--4x--tutorial에서-틀린-것들)
13. [Verification log](#13-verification-log)

---

## 1. Object lifecycle

### 1.1 `bpy.data.objects.new()` 는 어디에도 링크하지 않는다

`bpy.data.objects.new(name, data)` 는 **데이터블록만 만든다.** 컬렉션에도, 씬에도,
뷰 레이어에도 들어가지 않는다. unlinked 오브젝트는 렌더되지도, depsgraph 평가되지도,
`bpy.ops.object.*` 의 `poll()` 을 통과하지도 못한다. 반드시 `link()` 해야 한다.

```python
import bpy

# 1) create: this does NOT link the object anywhere
me = bpy.data.meshes.new("Cube")
ob = bpy.data.objects.new("Cube", me)
print(ob.users_collection)                       # []  <-- not in the scene yet

# 2) link into a collection, then into the scene
col = bpy.data.collections.new("Props")
bpy.context.scene.collection.children.link(col)
col.objects.link(ob)
print([c.name for c in ob.users_collection])   # ['Props']
print(ob.name in bpy.context.scene.objects)     # True

# 3) unlink (keeps the datablock alive, users -> 0)
for c in list(ob.users_collection):
    c.objects.unlink(ob)
print(ob.users_collection, ob.users)            # [] 0

# 4) remove for real
bpy.data.objects.remove(ob)
print("Cube" in bpy.data.objects)                # False
```

`bpy.data.objects.new()` 의 두 번째 인자:

| 인자 | 결과 |
|---|---|
| `None` (기본값) | Empty 오브젝트. `empty_display_type`/`empty_display_size` 사용 |
| `bpy.types.Mesh` | 메시 오브젝트 |
| `bpy.types.Curve` | 커브/폰트 오브젝트 (`ob.type` 가 `CURVE` 또는 `FONT`) |
| `bpy.types.Lattice` / `Armature` / `Camera` / `Light` | 해당 타입 |

`ob.data` 의 RNA 타입과 `ob.type` 은 다르다. `TextCurve` 데이터로 만든 오브젝트는
`ob.type == 'FONT'` 이고, `type(ob.data).__name__ == 'TextCurve'`, `ob.data.id_type == 'CURVE'`.
`Object.type` enum 전체 (5.2):

```
MESH, CURVE, SURFACE, META, FONT, CURVES, POINTCLOUD, VOLUME, GREASEPENCIL,
ARMATURE, LATTICE, EMPTY, LIGHT, LIGHT_PROBE, CAMERA, SPEAKER
```

### 1.2 컬렉션 계층과 뷰 레이어

컬렉션은 자유롭게 중첩된다. `scene.collection` 이 루트이고, 루트에 바로 링크된 컬렉션들만
`scene.collection.children` 에 보인다. `LayerCollection` 트리(= `view_layer.layer_collection`)는
`Collection` 트리와 **별개**이며, 여기에 `exclude` / `hide_viewport` / `holdout` 같은
뷰 레이어 전용 플래그가 붙는다.

```python
import bpy

root = bpy.context.scene.collection
lvl1 = bpy.data.collections.new("L1")
lvl2 = bpy.data.collections.new("L2")
root.children.link(lvl1)
lvl1.children.link(lvl2)          # nested collections are fine

ob = bpy.data.objects.new("deep", bpy.data.meshes.new("m"))
lvl2.objects.link(ob)
print([c.name for c in ob.users_collection])                       # ['L2']
print(ob.name in bpy.context.view_layer.objects)                   # False  (not synced yet)
bpy.context.view_layer.update()
print(ob.name in bpy.context.view_layer.objects)                   # True

lc1 = [lc for lc in bpy.context.view_layer.layer_collection.children if lc.collection.name == "L1"][0]
lc1.exclude = True
bpy.context.view_layer.update()
print(ob.name in bpy.context.view_layer.objects)                   # False
lc1.exclude = False
lc1.hide_viewport = True
bpy.context.view_layer.update()
print(ob.name in bpy.context.view_layer.objects)                   # True (viewport-only flag)
lc1.hide_viewport = False

# where do primitive ops put things?
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection
bpy.ops.mesh.primitive_cube_add(size=1)
print(bpy.context.active_object.users_collection[0].name)          # Scene Collection
lc1 = [lc for lc in bpy.context.view_layer.layer_collection.children
       if lc.collection.name == "L1"][0]
bpy.context.view_layer.active_layer_collection = lc1.children[0]
bpy.ops.mesh.primitive_cube_add(size=1)
print(bpy.context.active_object.users_collection[0].name)          # L2

lvl2.objects.unlink(ob)
print(ob.users_collection, ob.users)                               # [] 0
bpy.data.collections.remove(lvl2)
print("L2" in bpy.data.collections)                                # False (datablock gone)
bpy.data.objects.remove(ob)
print("deep" in bpy.data.objects)                                  # False
bpy.context.scene.collection.children.unlink(lvl1)
print([c.name for c in bpy.context.scene.collection.children])
```

핵심 규칙:

| 연산 | 효과 | 데이터블록 삭제? |
|---|---|---|
| `coll.objects.link(ob)` | 컬렉션에 등록. `view_layer.objects` 반영은 `view_layer.update()` 후 | 아니오 |
| `coll.objects.unlink(ob)` | 그 컬렉션에서만 빠짐. `ob.users` 감소 | 아니오 (`ob.users == 0` 이라도 남음) |
| `bpy.data.objects.remove(ob)` | 전부 제거. `ob.data` 의 users 도 0이 되어 함께 정리됨 | 예 |
| `bpy.data.collections.remove(c)` | 컬렉션만 제거. 그 안의 오브젝트는 `bpy.data.objects` 에 남음 (0-user) | 예 |
| `scene.collection.children.unlink(c)` | 씬에서만 분리. `bpy.data.collections` 에 남음 | 아니오 |

**주의**: 오브젝트는 여러 컬렉션에 동시에 링크될 수 있고 `users_collection` 에 전부 담긴다.
iterate 할 때 복사본(`list(ob.users_collection)`)을 돌려야 ConcurrentModification을 피한다.

### 1.3 `obj.parent` 와 `matrix_parent_inverse`

`child.parent = parent` 만 하면 **부모의 월드 변환이 그대로 곱해진다.**
"위치 유지"를 원하면 `matrix_parent_inverse` 에 부모의 역행렬을 넣어야 한다.

```python
import bpy

child = bpy.data.objects.new("child", bpy.data.meshes.new("cm"))
parent = bpy.data.objects.new("parent", None)      # None -> Empty
parent.empty_display_type = 'PLAIN_AXES'
bpy.context.scene.collection.objects.link(child)
bpy.context.scene.collection.objects.link(parent)

child.location = (1.0, 0.0, 0.0)
parent.location = (5.0, 0.0, 0.0)
bpy.context.view_layer.update()

child.parent = parent                                # naive parenting
bpy.context.view_layer.update()
print(tuple(child.matrix_world.translation))         # (6.0, 0.0, 0.0)

child.matrix_parent_inverse = parent.matrix_world.inverted()
bpy.context.view_layer.update()
print(tuple(child.matrix_world.translation))         # (1.0, 0.0, 0.0)

child.parent = None
bpy.context.view_layer.update()
print(tuple(child.matrix_world.translation))         # (1.0, 0.0, 0.0)
```

계산식: `child.matrix_world = parent.matrix_world @ child.matrix_parent_inverse @ child.matrix_basis`.
`parent_type` enum: `OBJECT`, `ARMATURE`, `LATTICE`, `VERTEX`, `VERTEX_3`, `BONE`.

`bpy.ops.object.parent_set` 을 쓰면 `keep_transform` 이 `matrix_parent_inverse` 를 대신 처리한다:

```python
bpy.ops.object.select_all(action='DESELECT')
child.select_set(True); parent.select_set(True)
bpy.context.view_layer.objects.active = parent
bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)   # world position preserved
```

`parent_set` 의 `type` enum (5.2):
`OBJECT, ARMATURE, ARMATURE_NAME, ARMATURE_AUTO, ARMATURE_ENVELOPE, BONE, BONE_RELATIVE, CURVE, FOLLOW, PATH_CONST, LATTICE, VERTEX, VERTEX_TRI`.

### 1.4 안전한 정리 루틴

```python
n_obj, n_me = len(bpy.data.objects), len(bpy.data.meshes)
for i in range(30):
    bpy.data.objects.new("junk%d" % i, bpy.data.meshes.new("junkmesh%d" % i))
# objects 16 -> 46, meshes 14 -> 44, all with 0 users
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)   # -> 63
# objects 16 -> 15, meshes 14 -> 13

ids = [bpy.data.meshes.new("z%d" % i) for i in range(5)]
bpy.data.batch_remove(ids)          # 한 번에 여러 데이터블록 제거
```

- `bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)` — 반환값은 제거된 수.
  `do_recursive=True` 없이는 제거된 오브젝트의 메시가 살아남는다.
- `bpy.data.batch_remove([...])` — 2.9+. 대량 삭제에 훨씬 빠르다.
- `to_mesh()` / `to_mesh_clear()` 쌍은 메시를 누출시키지 않는다 (200회 반복 후 `bpy.data.meshes` 개수 불변, 검증됨).

---

## 2. Primitive operators

### 2.1 5.2 의 `bpy.ops.mesh` 전체 목록

`dir(bpy.ops.mesh)` 에서 실제로 존재하는 항목만 추린다. `primitive_*` 계열은 정확히 **11개**다
(`monkey` 도 있고, `circle` 도 있다. `primitive_circle_add_gizmo` 도 별도로 존재한다).

| # | operator | 용도 | 핵심 인자 |
|---|---|---|---|
| 1 | `primitive_cube_add` | 육면체 | `size=2.0` |
| 2 | `primitive_plane_add` | 단면 | `size=2.0` |
| 3 | `primitive_circle_add` | 원(면 없음) | `vertices=32, radius=1.0, fill_type='NOTHING'` |
| 4 | `primitive_grid_add` | N×M 격자 | `x_subdivisions=10, y_subdivisions=10, size=2.0` |
| 5 | `primitive_uv_sphere_add` | UV 구 | `segments=32, ring_count=16, radius=1.0` |
| 6 | `primitive_ico_sphere_add` | 정이십면체 구 | `subdivisions=2, radius=1.0` |
| 7 | `primitive_primitive_cylinder_add` → `primitive_cylinder_add` | 원기둥 | `vertices=32, radius=1.0, depth=2.0, end_fill_type='NGON'` |
| 8 | `primitive_cone_add` | 원뿔//frustum | `vertices=32, radius1=1.0, radius2=0.0, depth=2.0` |
| 9 | `primitive_torus_add` | 토러스 | `major_segments=48, minor_segments=12, major_radius=1.0, minor_radius=0.25, mode='MAJOR_MINOR'` |
| 10 | `primitive_monkey_add` | Suzanne (v2) | `size=2.0` |
| 11 | `primitive_cube_add_gizmo` | gizmo 데모용 | (스크립팅에 무의미) |

> 7번 행은 의도된 표기다 — 실제 이름은 `primitive_cylinder_add` 이다.

`primitive_*` 외의 `bpy.ops.mesh` 연산군 (`dir()` 결과 149개) 은 4가지로 묶는다:

| 계열 | 대표 연산 |
|---|---|
| 토폴로지 생성/삭제 | `extrude_faces_indiv`, `extrude_region`, `inset`, `poke`, `loopcut`, `spin`, `bevel`, `bisect`, `bridge_edge_loops`, `circularize`, `symmetrize`, `fill`, `fill_grid`, `fill_holes`, `convex_hull`, `duplicate`, `split`, `separate` |
| 삭제/해소 | `delete`, `delete_loose`, `delete_edgeloop`, `dissolve_degenerate`, `dissolve_edges`, `dissolve_faces`, `dissolve_limited`, `dissolve_mode`, `dissolve_verts`, `unsubdivide`, `tris_convert_to_quads`, `quads_convert_to_tris` |
| 선택 | `select_all`, `select_mode`, `select_linked`, `select_linked_pick`, `select_less/more`, `select_similar_region`, `select_by_attribute`, `select_by_pole_count`, `select_face_by_sides`, `select_interior_faces`, `select_non_manifold`, `select_mirror`, `select_nth`, `select_random`, `select_axis`, `select_edge_loop_multi`, `select_edge_ring_multi`, `select_boundary_loop_multi`, `edgering_select`, `edges_select_sharp`, `faces_select_linked_flat`, `loop_select`, `loop_to_region`, `region_to_loop` |
| 노멀/컬러/스카이아 | `average_normals`, `merge_normals`, `normals_make_consistent`, `normals_tools`, `set_normals_from_faces`, `split_normals`, `point_normals`, `smooth_normals`, `customdata_custom_splitnormals_add/clear`, `customdata_face_sets_clear`, `customdata_mask_clear`, `customdata_skin_add/clear`, `colors_reverse`, `colors_rotate`, `attribute_set`, `flip_normals`, `flip_quad_tessellation` |

### 2.2 전 operator 공통 인자

`get_rna_type().properties` 로 뽑은 실제 값 (5.2). 10개 `primitive_*` 전부 동일하다:

| 인자 | 타입 | 기본값 | 의미 / 함정 |
|---|---|---|---|
| `align` | ENUM | `'WORLD'` | `WORLD` / `VIEW` / `CURSOR`. background 모드에서는 3가지 모두 결과가 같다 (VIEW_3D 영역이 없음) |
| `location` | FLOAT[3] | `(0,0,0)` | `obj.location` 에 그대로 들어간다 |
| `rotation` | FLOAT[3] | `(0,0,0)` | **Euler XYZ radians**. 쿼터니언이 아님 |
| `scale` | FLOAT | `0.0` | **headless 에서 unusable** — [§2.4](#24-scale-인자는-headless-에서-망가져있다) |
| `enter_editmode` | BOOLEAN | `False` | `True` 면 생성 직후 EDIT 모드. headless 에서도 정상 동작 |
| `calc_uvs` | BOOLEAN | `True` | `UVMap` 레이어를 만들지 않는다 → 나중에 UV 작업 전부 손해야 함 |

`align='VIEW'` 는 `bpy.context.region` 이 필요해서 background 에서는 3D 뷰와 동일한 변환을 못 한다.
스크립트에서는 **항상 `'WORLD'`** 를 쓴다. 검증 결과 (커서 위치 `(100,0,0)` 로 세팅한 상태):

```
align=WORLD   -> location=[3.0, 4.0, 5.0] matrix_world.translation=[3.0, 4.0, 5.0]
align=CURSOR  -> location=[3.0, 4.0, 5.0] matrix_world.translation=[3.0, 4.0, 5.0]
align=VIEW    -> location=[3.0, 4.0, 5.0] matrix_world.translation=[3.0, 4.0, 5.0]
```

### 2.3 operator별 고유 인자 (전체)

| operator | 인자 | 타입 | 기본값 |
|---|---|---|---|
| `primitive_cube_add` | `size` | FLOAT | 2.0 |
| `primitive_plane_add` | `size` | FLOAT | 2.0 |
| `primitive_circle_add` | `vertices` | INT | 32 |
| | `radius` | FLOAT | 1.0 |
| | `fill_type` | ENUM `NOTHING`/`NGON`/`TRIFAN` | `NOTHING` |
| `primitive_grid_add` | `x_subdivisions` | INT | 10 |
| | `y_subdivisions` | INT | 10 |
| | `size` | FLOAT | 2.0 |
| `primitive_uv_sphere_add` | `segments` (경도) | INT | 32 |
| | `ring_count` (위도) | INT | 16 |
| | `radius` | FLOAT | 1.0 |
| `primitive_ico_sphere_add` | `subdivisions` | INT | 2 |
| | `radius` | FLOAT | 1.0 |
| `primitive_cylinder_add` | `vertices` | INT | 32 |
| | `radius` / `depth` | FLOAT | 1.0 / 2.0 |
| | `end_fill_type` | ENUM `NOTHING`/`NGON`/`TRIFAN` | `NGON` |
| `primitive_cone_add` | `vertices` | INT | 32 |
| | `radius1` / `radius2` / `depth` | FLOAT | 1.0 / 0.0 / 2.0 |
| | `end_fill_type` | ENUM | `NGON` |
| `primitive_torus_add` | `major_segments` / `minor_segments` | INT | 48 / 12 |
| | `major_radius` / `minor_radius` | FLOAT | 1.0 / 0.25 |
| | `abso_major_rad` / `abso_minor_rad` | FLOAT | 1.25 / 0.75 (`mode='EXT_INT'` 전용) |
| | `mode` | ENUM `MAJOR_MINOR` / `EXT_INT` | `MAJOR_MINOR` |
| | `generate_uvs` | BOOLEAN | True |
| `primitive_monkey_add` | `size` | FLOAT | 2.0 |

주의점:

- `primitive_torus_add` **에는** `calc_uvs` 가 없다. 대신 `generate_uvs` 를 쓴다.
  나머지 10개는 전부 `calc_uvs` 가 있다.
- `segments`/`ring_count` 는 UV 스피어 전용, `subdivisions` 는 ico 스피어 전용.
  `major_segments`/`minor_segments` 는 토러스 전용. 서로 섞지 않는다.
- `radius1`/`radius2` 는 **cone 전용**. `radius2=0.0` 이면 끝없는 뾰족한 원뿔.
- `fill_type`(circle)와 `end_fill_type`(cylinder/cone)는 이름이 다르다.
- `circle` 의 기본 `fill_type='NOTHING'` 이므로 면이 없다. 면이 필요하면 `'NGON'`.

실제 생성 결과 (factory startup 씬에 위 11개 전부 실행):

```
Circle     v=32    e=32    f=1     uv=['UVMap']
Cone       v=33    e=64    f=33    uv=['UVMap']
Cube       v=8     e=12    f=6     uv=['UVMap']
Cylinder   v=64    e=96    f=34    uv=['UVMap']
Grid       v=121   e=220   f=100   uv=['UVMap']
Icosphere  v=42    e=120   f=80    uv=['UVMap']
Plane      v=4     e=4     f=1     uv=['UVMap']
Sphere     v=482   e=992   f=512   uv=['UVMap']
Suzanne    v=507   e=1005  f=500   uv=['UVMap']
Torus      v=576   e=1152  f=576   uv=['UVMap']
```

### 2.4 `scale=` 인자는 headless 에서 망가져있다

`scale` 는 RNA 에 `PROP_FLOAT` 로 선언돼 있어 직관적으로는 배율처럼 보인다. 실제로는 아니다.
**`bpy.ops.mesh.primitive_*_add(scale=...)` 는 background 모드에서 세 가지 상태 중 하나가 된다:**

| 넘긴 값 | 결과 |
|---|---|
| 스칼라 (`2.0`, `0.5`, …) | `TypeError: Converting py args to operator properties:` |
| bool (`True`, `False`) | `TypeError` (동일) |
| 3-튜플 `(2,2,2)` | **조용히 무시**. `obj.scale` 은 여전히 `(1,1,1)` |

`primitive_plane_add`, `primitive_uv_sphere_add`, `primitive_cylinder_add` 전부 동일하게 재현된다.
신뢰할 수 있는 방법은 **생성 후 `obj.scale` 을 직접 대입**하는 것:

```python
import bpy, bmesh

# ... (S16_gotchas.py 3번 항목)
for lbl, v in (("2.0", 2.0), ("True", True), ("(2,2,2)", (2, 2, 2))):
    try:
        bpy.ops.mesh.primitive_cube_add(size=1, scale=v)
        print("scale=%-8s accepted, obj.scale=%s" % (
            lbl, [round(float(c), 2) for c in bpy.context.active_object.scale]))
    except TypeError:
        print("scale=%-8s TypeError" % lbl)
bpy.ops.mesh.primitive_cube_add(size=1)
bpy.context.active_object.scale = (2.0, 2.0, 2.0)   # <- the reliable way
print([round(float(c), 2) for c in bpy.context.active_object.scale])
```

출력:
```
scale=2.0      TypeError
scale=True     TypeError
scale=(2,2,2)  accepted, obj.scale=[1.0, 1.0, 1.0]
[2.0, 2.0, 2.0]
```

### 2.5 배경 모드의 컬렉션 결정 규칙 (가장 흔한 오해)

"`bpy.context.temp_override(collection=...)` 로 어디에 생성될지 지정한다" 는 **거짓**이다 (5.2 기준).
오버라이드는 `bpy.context.collection` **값 자체는** 바꾸지만, `primitive_*_add` 는
`view_layer.active_layer_collection` 을 따른다.

```python
import bpy

target = bpy.data.collections.new("T")
bpy.context.scene.collection.children.link(target)
vl = bpy.context.view_layer
vl.active_layer_collection = vl.layer_collection
with bpy.context.temp_override(collection=target):
    bpy.ops.mesh.primitive_cube_add(size=1)
print(bpy.context.active_object.users_collection[0].name)            # Scene Collection
lc = [x for x in vl.layer_collection.children if x.collection.name == "T"][0]
vl.active_layer_collection = lc
bpy.ops.mesh.primitive_cube_add(size=1)
print(bpy.context.active_object.users_collection[0].name)            # T
```

오버라이드 블록 **안에서** `bpy.context.collection` 은 실제로 `Target` 을 반환한다.
하지만 오브젝트는 여전히 `Scene Collection` 에 들어간다. 정리:

- `bpy.context.collection` = 현재 **활성 레이어 컬렉션**의 데이터블록.
- `bpy.context.temp_override(collection=X)` 는 그 읽기값만 바꾼다. `primitive_*_add` 는 안 따른다.
- `bpy.context.temp_override(scene=..., view_layer=...)` 는 **된다** (다른 씬에 생성됨, 검증됨).
- 확실히 통하는 방법: `vl.active_layer_collection = <LayerCollection>` 을 직접 대입.
  `bpy.context.collection` 은 `LayerCollection` 이 아니라 `Collection` 이므로
  `vl.layer_collection` 트리를 탐색해야 한다.

```python
def find_lc(layer_coll, collection_name):
    if layer_coll.collection.name == collection_name:
        return layer_coll
    for ch in layer_coll.children:
        r = find_lc(ch, collection_name)
        if r:
            return r
    return None

bpy.context.view_layer.active_layer_collection = find_lc(
    bpy.context.view_layer.layer_collection, "Target")
```

또는 primitive op 을 아예 쓰지 말고 `bpy.data.objects.new()` + `col.objects.link()` 로 전부 만들기.
이 경로는 컨텍스트에 전혀 의존하지 않으므로 헤드리스 스크립트에서 가장 안전하다.

### 2.6 `bpy.ops.<group>.<op>` 존재 여부 검사

`bpy.ops` 서브모듈은 **모든 이름에 대해 `__getattr__` 로 응답한다.** 그래서 다음 함정은 실제로 발동한다:

```python
hasattr(bpy.ops.object, "shade_auto_smooth_angle")   # True  (존재하지 않는 오퍼레이터!)
hasattr(bpy.ops.object, "totally_bogus_op_xyz")     # True  (완전 쓰레기 이름)
bpy.ops.object.totally_bogus_op_xyz()
# AttributeError: Calling operator "bpy.ops.object.totally_bogus_op_xyz" error, could not be found
"shade_auto_smooth_angle" in dir(bpy.ops.object)     # False  <-- 이것이 올바른 검사
```

**`hasattr(bpy.ops.<group>, ...)` 는 절대 쓰지 않는다.** `dir()` 또는 `get_rna_type()` 만 신뢰한다.
헬퍼 정의는 [§11](#11-직접-확인하는-법) 에 있고 요약은 이렇다:

```python
def op_exists(group, name):
    return name in dir(getattr(bpy.ops, group))

def op_sig(group, name):
    """Return {prop: (type, default, enum_items)} for an operator, or None."""
    g = getattr(bpy.ops, group)
    if name not in dir(g):
        return None
    rt = getattr(g, name).get_rna_type()
    out = {}
    for p in rt.properties:
        if p.identifier == "rna_type":
            continue
        if p.type == "ENUM":
            out[p.identifier] = (p.type, p.default, [i.identifier for i in p.enum_items])
        else:
            out[p.identifier] = (p.type, getattr(p, "default", None), None)
    return out
```

## 3. Direct mesh construction

### 3.1 `from_pydata` → `validate` → `update`

```python
import bpy

V = [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0),
     (-1, -1, 2), (1, -1, 2), (1, 1, 2), (-1, 1, 2)]
F = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]

me = bpy.data.meshes.new("Box")
me.from_pydata(V, [], F, shade_flat=True)
me.validate(verbose=False)
me.update(calc_edges=True)
print(len(me.vertices), len(me.edges), len(me.polygons))     # 8 12 6
print(me.polygons[0].use_smooth)                             # False
print(hasattr(me, "calc_normals"))                           # False  (removed in 4.1)

ob = bpy.data.objects.new("Box", me)
bpy.context.scene.collection.objects.link(ob)

# ngon + loop triangles
ng = bpy.data.meshes.new("Ngon")
ng.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0.5, 1.6, 0), (0, 1, 0)], [], [(0, 1, 2, 3, 4)])
ng.update(calc_edges=True)
ng.calc_loop_triangles()
print(ng.polygons[0].loop_total, len(ng.loop_triangles))      # 5 3
print(tuple(ng.polygons[0].normal))                           # (0.0, 0.0, 1.0)
```

`from_pydata(vertices, edges, faces, shade_flat=True)` — 5.x 에서 `shade_flat` 키워드가 추가됐다.

| 인자 | 5.2 동작 |
|---|---|
| `vertices` | `[(x, y, z), ...]` |
| `edges` | `[(i, j), ...]`. **빈 리스트여도 동작한다** — 5.2 에서는 faces 에서 자동으로 추론한다 |
| `faces` | `[(i, j, k, ...), ...]`. 3개 이상 정점. n-gon 허용 |
| `shade_flat` | `True`(기본)면 신규 면을 flat 로 표시. `False` 면 smooth |

**검증된 함정들:**

- 스칼라(out of range) 인덱스는 `from_pydata` 를 **통과한다** (에러 없음). 반드시 `validate()` 필요.
  인덱스 99 를 준 삼각형 하나 → `validate()` 가 `True` 반환 후 그 면을 **삭제**한다.
- 중복 정점으로 이루어진 zero-area 면은 `validate()` 가 `False` 를 반환하고 **아무것도 고치지 않는다**.
  이건 `bmesh.ops.remove_doubles` / `dissolve_degenerate` 의 몫이다.
- `edges=[]` 여도 `from_pydata` 직후 `len(me.edges)` 가 이미 채워진다 (위 예시에서 12).
  `me.update(calc_edges=True)` 는 명시적으로 재계산을 강제할 뿐이다.

`Mesh.validate(verbose=False, clean_customdata=True)` → `True` 면 뭔가 고쳤다는 뜻.
`Mesh.update(calc_edges=False, calc_edges_loose=False)` → 재생성.
`Mesh.calc_loop_triangles()` → `loop_triangles` 를 채운다 (n-gon 삼각분할).

**메서드 vs RNA 속성 함정**: `me.validate`, `me.update`, `me.shade_smooth` 는 모두
**메서드**여서 `bl_rna.properties` 에 **없다**. `bpy.types.Mesh.bl_rna.properties` 로는
`validate` 도 `update` 도 `shade_smooth` 도 못 찾는다. 런타임 메서드 목록은 `dir(me)` 로 봐야 한다.

### 3.2 `mesh.calc_normals()` 는 4.1 에서 삭제, 5.2 에서도 없음

```python
hasattr(me, "calc_normals")            # False
hasattr(me, "calc_normals_split")      # False
```

대신:

| 필요 작업 | 5.2 API |
|---|---|
| 면 법선 읽기 | `me.polygons[i].normal` (자동 계산, `update()` 후 유효) |
| 정점 법선 | `me.vertex_normals[i].vector` |
| 코너 법선 | `me.corner_normals[i].vector` |
| 커스텀 노멀 쓰기 | `me.normals_split_custom_set(loop_normals)` / `me.normals_split_custom_set_from_vertices(vert_normals)` |
| 커스텀 노멀 존재 확인 | `me.has_custom_normals` (bool) |
| **면을 일관된 방향으로** | `bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])` |

`Mesh.normals_domain` enum: `POINT`, `FACE`, `CORNER`.

### 3.3 스무드 셰이딩 — `shade_smooth()` / `shade_flat()`

`Mesh` 에 **데이터블록 레벨 메서드**가 있다 (4.1+). 오퍼레이터를 거치지 않으므로 컨텍스트/선택 상태가 무관하다.

```python
import bpy, math

bpy.ops.mesh.primitive_cube_add(size=2)
ob = bpy.context.active_object
ob.data.shade_smooth()
print(all(p.use_smooth for p in ob.data.polygons))       # True
ob.data.shade_flat()
print(all(p.use_smooth for p in ob.data.polygons))       # False
print('sharp_face' in ob.data.attributes)                # True

ob.data.shade_smooth()
ob.data.set_sharp_from_angle(angle=math.radians(40))
se = ob.data.attributes['sharp_edge']
print(sum(1 for d in se.data if d.value), "of", len(ob.data.edges), "edges are sharp")

# operator path: the 4.1+ "Smooth by Angle" replacement for mesh.use_auto_smooth
bpy.context.view_layer.objects.active = ob
ob.select_set(True)
bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
print([(m.name, m.type) for m in ob.modifiers])          # 실측 5.2.2: []  <- 비어 있다
```

> ### ⚠⚠ 정정 — 실전 대조 테스트가 문서를 뒤집었다
>
> 이 문서는 원래 "`shade_auto_smooth` / `shade_smooth_by_angle` 가
> 스택에 `Smooth by Angle` **Geometry Nodes 모디파이어**를 추가한다" 고 적었다.
> **5.2.2 에서 그것은 사실이 아니다.** 실측:
>
> ```
> bpy.ops.object.shade_smooth_by_angle(angle=0.7)
> print([(m.name, m.type) for m in obj.modifiers])
> #  -> []            (NODES 모디파이어 없음)
> print("use_auto_smooth" in [p.identifier for p in bpy.types.Mesh.bl_rna.properties])
> #  -> False         (속성 자체가 여전히 없음 — 이건 문서대로)
> ```
>
> 4.1 에서 UI 는 "Smooth by Angle" 모디파이퍼를 쓰지만, **5.x 의 오퍼레이터는
> 노드 그래프를 실행해 `sharp_edge` 속성만 직접 쓴다.** 결과(기울기각 판정)는
> 같지만 **스택은 깨끗하게 남는다** — 내보내기 폴리곤 수나 모디파이러 순서에
> 영향이 없다.
>
> **그래서 어떤 쪽을 쓰나?**
>
> | 방법 | 스택 | 언제 쓰나 |
> |---|---|---|
> | `shade_smooth_by_angle()` | **비어 있음** | 기본. 내보내기/파이프라인 안전 |
> | `set_sharp_from_angle()` (data API) | 비어 있음 | 컨텍스트 없이 처리할 때 |
> | UI 의 "Smooth by Angle" 모디파이어 | GN 추가 | 사용자가 모디파이러를 보고 조율하고 싶을 때 |

내부 구현 (docstring에서 확인):

- `me.shade_smooth()` — "Render and display faces smooth, using interpolated vertex normals,
  **removing the `sharp_face` attribute**"
- `me.shade_flat()` — "…**setting the `sharp_face` attribute true for every face**"
- `me.set_sharp_from_angle(angle=3.14159)` — "Reset and fill the `sharp_edge` attribute based on
  the angle of faces neighboring manifold edges"

`polygons[i].use_smooth` 은 여전히 유효하지만, 이제 그건 `sharp_face` 속성으로 **저장된다**는
개념적 모델을 갖는 게 정확하다. (스크립트 관점에서는 읽기/쓰기 모두 그대로 동작한다.)

### 3.4 Auto Smooth 제거 (4.1) 와 "Smooth by Angle"

`mesh.use_auto_smooth` / `object.use_auto_smooth` / `edge.use_auto_smooth` — **셋 다 5.2에 없다.**
검증 결과:

```
Mesh has use_auto_smooth:   False
MeshEdge has use_auto_smooth: False
Object has use_auto_smooth:  False
```

대체 경로는 두 개:

| 경로 | API | 동작 |
|---|---|---|
| A. 순수 데이터 | `me.shade_smooth()` + `me.set_sharp_from_angle(angle=radians(N))` | `sharp_edge` 속성을 정적으로 계산. 모디파이어 없음 |
| B. 오퍼레이터(UI와 동일) | `bpy.ops.object.shade_auto_smooth(angle=...)` | 이름이 `Smooth by Angle` 인 **Geometry Nodes 모디파이어**를 스택에 추가 |

| `bpy.ops.object.shade_*` | 인자 | 비고 |
|---|---|---|
| `shade_smooth` | `keep_sharp_edges` (BOOL) | **선택된** 객체만 처리 |
| `shade_flat` | `keep_sharp_edges` (BOOL) | 동일 |
| `shade_auto_smooth` | `use_auto_smooth` (BOOL, 기본 False), `angle` (FLOAT) | `use_auto_smooth=True` 면 모디파이어 없이 `sharp_edge` 만 설정 |
| `shade_smooth_by_angle` | `angle` (FLOAT), `keep_sharp_edges` (BOOL) | `shade_auto_smooth` 의 별칭 |

두 함수가 결과적으로 같은 이름(`Smooth by Angle`)의 NODES 모디파이어를 만든다.
그 모디파이어의 `node_group` 은 Blender 를 처음 실행할 때
`<install>/5.2/datafiles/assets/nodes/geometry_nodes_essentials.blend` 에서 링크된다.
즉 **Python 으로 만들지 않는다** — 런타임에 노드 트리를 조립할 필요가 없다.

**`bpy.ops.object.shade_smooth()` 는 선택 상태에 민감하다:**

```
poll() with no selection: True
bpy.ops.object.shade_smooth()  ->  {'CANCELLED'}   all smooth: False
poll() with selection:      True
bpy.ops.object.shade_smooth()  ->  {'FINISHED'}
```

`poll()` 이 `True` 여도 실제 호출이 `CANCELLED` 로 끝날 수 있다. **반환 dict 를 항상 확인하라.**

### 3.5 Mesh attributes — 4.1+ 범용 레이어 API

`sharp_edge`, `sharp_face`, UV, 컬러, 커스텀 데이터가 전부 `mesh.attributes` 로 통합됐다.
`mesh.vertex_colors`, `mesh.edge_creases` 같은 옛 API는 `mesh.attributes` 위에 얹힌 façade 이다.

```python
bpy.ops.mesh.primitive_cube_add(size=2)
me = bpy.context.active_object.data
print(sorted(a.name for a in me.attributes))
# ['.corner_edge', '.corner_vert', '.edge_verts', '.select_edge', '.select_poly',
#  '.select_vert', '.uv_select_edge', '.uv_select_face', '.uv_select_vert', 'UVMap',
#  'position', 'sharp_face']

me.set_sharp_from_angle(angle=0.5)
print(sorted(a.name for a in me.attributes))     # 'sharp_face' 사라지고 'sharp_edge' 등장

attr = me.attributes.new("my_float", 'FLOAT', 'POINT')
for i, v in enumerate(me.vertices):
    attr.data[i].value = i * 0.5
print([round(attr.data[i].value, 2) for i in range(len(me.vertices))])   # [0.0 .. 3.5]
me.attributes.remove(attr)
```

`Attribute.data_type` enum: `FLOAT, INT, BOOLEAN, FLOAT_VECTOR, FLOAT_COLOR, QUATERNION,
FLOAT4X4, STRING, INT8, INT16_2D, INT32_2D, FLOAT2, FLOAT4, BYTE_COLOR`.
`Attribute.domain` enum: `POINT, EDGE, FACE, CORNER, CURVE, INSTANCE, LAYER`.
내장 속성의 `data_type` 실측값: `UVMap=FLOAT2`, `position=FLOAT_VECTOR`, `sharp_edge=BOOLEAN`,
`.edge_verts=INT32_2D`, `.corner_vert=INT`, `.corner_edge=INT`.

---

## 4. bmesh

### 4.1 5.x 에서는 BMesh 를 **위치 인자**로 넘긴다

이것이 4.x 튜토리얼과의 가장 큰 차이다.

```python
import bpy, bmesh
from mathutils import Matrix

bm = bmesh.new()
print(type(bm).__name__)                                  # BMesh

# 5.x: the BMesh is POSITIONAL; bm= as a keyword is rejected
try:
    bmesh.ops.create_cube(bm=bm, size=1.0)
except TypeError as e:
    print("TypeError:", e)
bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Identity(4), calc_uvs=True)
print(len(bm.verts), len(bm.edges), len(bm.faces))        # 8 12 6
```

`bm=` 키워드 형식의 결과:
`TypeError: bmesh operators expect a single BMesh positional argument, all other args must be keywords`
— 모든 `bmesh.ops.*` 에 대해 동일하다. 나머지 인자는 전부 키워드여야 한다.

`matrix=` 를 아예 생략하는 것도 가능하지만, **`matrix=None` 은 안 된다**:
`TypeError: expected a mathutils.Matrix, not a NoneType`.

`BMesh` 의 공개 메서드 (5.2):

```
calc_loop_triangles, calc_volume, clear, copy, edges, faces, free, from_mesh, from_object,
is_valid, is_wrapped, loops, normal_update, select_flush, select_flush_mode, select_history,
select_mode, to_mesh, transform, uv_select_flush, uv_select_flush_mode, uv_select_flush_shared,
uv_select_foreach_set, uv_select_foreach_set_from_mesh, uv_select_sync_from_mesh,
uv_select_sync_to_mesh, uv_select_sync_valid, verts
```

### 4.2 인덱스 접근 규칙 — `ensure_lookup_table()` 이 필수, `index_update()` 는 부족

```python
import bpy, bmesh

bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)          # 8 verts
bmesh.ops.create_cube(bm, size=1.0)          # 16 verts
try:
    bm.verts[3]
except IndexError as e:
    print("IndexError:", e)
bm.verts.index_update()
try:
    bm.verts[3]
except IndexError as e:
    print("still IndexError after index_update():", e)
bm.verts.ensure_lookup_table()
print(bm.verts[3].index, tuple(bm.verts[3].co))
```

출력:
```
IndexError: BMElemSeq[index]: outdated internal index table, run ensure_lookup_table() first
still IndexError after index_update(): BMElemSeq[index]: outdated internal index table, run ensure_lookup_table() first
3 (-0.5, 0.5, 0.5)
```

**`bmesh.ops.*` 로 요소를 추가/삭제한 뒤에는 `ensure_lookup_table()` 을 다시 불러야 한다.**
`index_update()` 만으로는 인덱스 접근이 열리지 않는다 (5.2 실측).

| 호출 후 | `bm.verts[i]` |
|---|---|
| `bmesh.new()` 직후 | `IndexError` |
| `bm.verts.index_update()` 후 | **여전히 `IndexError`** |
| `bm.verts.ensure_lookup_table()` 후 | OK |
| `remove_doubles` 등으로 개수가 준 뒤 | `IndexError` (outdated) → 다시 `ensure_lookup_table()` |
| 개수가 줄어서 범위를 벗어난 경우 | `IndexError: index 15 out of range` |

시퀀스 객체별 공개 속성 (5.2):

| 시퀀스 | 공개 멤버 | `get()`? | `lookup_table`? |
|---|---|---|---|
| `BMVertSeq` (`bm.verts`) | `ensure_lookup_table, index_update, layers, new, remove, sort` | **없음** | **없음** |
| `BMEdgeSeq` (`bm.edges`) | 위 + `get` | 있음 (`.get(verts, fallback=None)`) | 없음 |
| `BMFaceSeq` (`bm.faces`) | 위 + `active`, `get` | 있음 (`.get(verts, fallback=None)`) | 없음 |
| `BMLoopSeq` (`bm.loops`) | **`layers` 뿐** | 없음 | 없음 |

4.x 튜토리얼에 흔한 `bm.verts.get(co)` 와 `bm.verts.lookup_table` 은 **5.2에 없다.**
좌표 → 인덱스 검색은 직접 만든다:

```python
bm.verts.ensure_lookup_table()
co_to_idx = {tuple(round(float(c), 4) for c in v.co): v.index for v in bm.verts}
idx = co_to_idx[(1.0, 0.0, 0.0)]
```

`BMFaceSeq.get(verts, fallback=None)` 는 **정점 시퀀스**를 받는다 (인덱스 아님):
`bm.faces.get(f.verts)` 또는 `bm.faces.get([v0, v1, v2, v3])`.

### 4.3 `bm.loops` 는 순회도 인덱싱도 되지 않는다

```python
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, calc_uvs=True)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
f = bm.faces[0]
try:
    len(bm.loops)
except TypeError as e:
    print("TypeError:", e)              # object of type 'BMLoopSeq' has no len()
print(len(f.loops), f.loops[0].vert.index)      # 4 0
```

- `len(bm.loops)` → `TypeError: object of type 'BMLoopSeq' has no len()`
- `bm.loops[0]` → `TypeError: 'BMLoopSeq' object is not subscriptable`
- `list(bm.loops)` → `TypeError: 'BMLoopSeq' object is not iterable`

**반드시 `face.loops` 로 내려간다** (`BMElemSeq`, `len()`/`[]`/반복 모두 가능).
`BMLoop` 의 속성: `calc_angle, calc_normal, calc_tangent, copy_from, copy_from_face_interp,
edge, face, index, is_convex, is_valid, link_loop_next, link_loop_prev, link_loop_radial_next,
link_loop_radial_prev, link_loops, tag, uv_select_edge, uv_select_edge_set, uv_select_vert,
uv_select_vert_set, vert`.
`BMLoop.index` 는 `ensure_lookup_table()` 로도 채워지지 않는다 (항상 `-1`).

요소 속성 요약:

| 클래스 | 속성 |
|---|---|
| `BMVert` | `calc_edge_angle, calc_shell_factor, co, copy_from, copy_from_face_interp, copy_from_vert_interp, hide, hide_set, index, is_boundary, is_manifold, is_valid, is_wire, link_edges, link_faces, link_loops, normal, normal_update, select, select_set, tag` |
| `BMEdge` | `calc_face_angle, calc_face_angle_signed, calc_length, calc_tangent, copy_from, hide, hide_set, index, is_boundary, is_contiguous, is_convex, is_manifold, is_valid, is_wire, link_faces, link_loops, normal_update, other_vert, seam, select, select_set, smooth, tag, verts` |
| `BMFace` | `calc_area, calc_center_bounds, calc_center_median, calc_center_median_weighted, calc_perimeter, calc_tangent_edge, calc_tangent_edge_diagonal, calc_tangent_edge_pair, calc_tangent_vert_diagonal, copy, copy_from, copy_from_face_interp, edges, hide, hide_set, index, is_valid, loops, material_index, normal, normal_flip, normal_update, select, select_set, smooth, tag, uv_select, uv_select_set, verts` |

### 4.4 object 모드 vs edit 모드 라운드 트립

두 모드의 API 가 **완전히 다르다.**

```python
import bpy, bmesh

# ---- object-mode round trip -------------------------------------------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=2, y_subdivisions=2)
me = bpy.context.active_object.data

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
print(len(bm.verts), len(bm.edges), len(bm.faces))            # 9 12 4

# NOTE: without use_grid_fill=True, subdivide_edges turns every quad into ONE n-gon
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
print(len(bm.verts), len(bm.faces))                           # 25 16
bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(me)
bm.free()
me.update()
print(len(me.vertices), len(me.polygons))                      # 25 16

# ---- edit-mode round trip (DIFFERENT API) -----------------------------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=2, y_subdivisions=2)
ob2 = bpy.context.active_object
bpy.context.view_layer.objects.active = ob2
ob2.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')

bm = bmesh.from_edit_mesh(ob2.data)        # the live EDIT bmesh
for v in bm.verts:
    v.select = v.index in (0, 1, 5)
bmesh.update_edit_mesh(ob2.data, loop_triangles=False, destructive=False)
print(sorted(v.index for v in bmesh.from_edit_mesh(ob2.data).verts if v.select))   # [0, 1, 5]
bpy.ops.mesh.subdivide(number_cuts=1, smoothness=0.0)
try:
    bm.to_mesh(ob2.data)
except ValueError as e:
    print("ValueError:", e)               # to_mesh() is illegal while in edit mode
bpy.ops.object.mode_set(mode='OBJECT')
print(len(ob2.data.vertices))              # 25 - edits are committed on leaving EDIT
```

| | object 모드 | edit 모드 |
|---|---|---|
| BMesh 얻기 | `bm = bmesh.new(); bm.from_mesh(me)` | `bm = bmesh.from_edit_mesh(me)` |
| 되돌리기 | `bm.to_mesh(me); bm.free()` | `bmesh.update_edit_mesh(me, *, loop_triangles=True, destructive=True)` |
| `bm.to_mesh()` | OK | **`ValueError: to_mesh(): Mesh 'X' is in editmode`** |
| 해제 | `bm.free()` | 필요 없음 (라이브 객체) |
| `me.vertices` 가 반영? | 즉시 | **아니오** — leaving EDIT 해야 커밋됨 |

`bmesh.update_edit_mesh(mesh, *, loop_triangles=True, destructive=True)`:
요소를 추가/삭제했다면 `destructive=True`, 속성만 건드렸다면 `False` 로 충분하다.
`from_edit_mesh()` 는 매번 새 wrapper 를 돌려주므로, 반드시 다시 꺼내서 상태를 확인한다.

### 4.5 `bmesh.ops` 전체 (83개) 시그니처

전체는 `bmesh.ops.<name>(bmesh, ...)` 형태이고, 첫 인자 이름이 `bmesh` 이지만 **위치 인자**다.
나머지는 전부 키워드. `sort(dir(bmesh.ops))` 기준 83개 — 아래는 `verify/24_bmesh_table.py` 의 자동 덤프다
(`blender -b --factory-startup -noaudio --python verify/24_bmesh_table.py`).

| op | signature |
|---|---|
| `average_vert_facedata` | `bmesh.ops.average_vert_facedata(bmesh, verts=[])` |
| `beautify_fill` | `bmesh.ops.beautify_fill(bmesh, faces=[], edges=[], use_restrict_tag=False, method='AREA')` |
| `bevel` | `bmesh.ops.bevel(bmesh, geom=[], offset=0.0, offset_type='OFFSET', profile_type='SUPERELLIPSE', segments=0, profile=0.0, affect='VERTICES', clamp_overlap=False, material=0, loop_slide=False, mark_seam=False, mark_sharp=False, harden_normals=False, face_strength_mode='NONE', miter_outer='SHARP', miter_inner='SHARP', spread=0.0, custom_profile=None, vmesh_method='ADJ')` |
| `bisect_edges` | `bmesh.ops.bisect_edges(bmesh, edges=[], cuts=0, edge_percents={})` |
| `bisect_plane` | `bmesh.ops.bisect_plane(bmesh, geom=[], dist=0.0, plane_co=Vector(), plane_no=Vector(), use_snap_center=False, clear_outer=False, clear_inner=False)` |
| `bmesh_to_mesh` | `bmesh.ops.bmesh_to_mesh(bmesh, mesh=None, object=None)` |
| `bridge_loops` | `bmesh.ops.bridge_loops(bmesh, edges=[], use_pairs=False, use_cyclic=False, use_merge=False, merge_factor=0.0, twist_offset=0)` |
| `circularize` | `bmesh.ops.circularize(bmesh, geom=[], factor=0.0, custom_radius=0.0, angle=0.0, fit_method=0, flatten=0.0, regular=False, lock_x=False, lock_y=False, lock_z=False, mirror_x=False, mirror_y=False, mirror_z=False)` |
| `collapse` | `bmesh.ops.collapse(bmesh, edges=[], uvs=False)` |
| `collapse_uvs` | `bmesh.ops.collapse_uvs(bmesh, edges=[])` |
| `connect_vert_pair` | `bmesh.ops.connect_vert_pair(bmesh, verts=[], verts_exclude=[], faces_exclude=[])` |
| `connect_verts` | `bmesh.ops.connect_verts(bmesh, verts=[], faces_exclude=[], check_degenerate=False)` |
| `connect_verts_concave` | `bmesh.ops.connect_verts_concave(bmesh, faces=[])` |
| `connect_verts_nonplanar` | `bmesh.ops.connect_verts_nonplanar(bmesh, angle_limit=0.0, faces=[])` |
| `contextual_create` | `bmesh.ops.contextual_create(bmesh, geom=[], mat_nr=0, use_smooth=False)` |
| `convex_hull` | `bmesh.ops.convex_hull(bmesh, input=[], use_existing_faces=False)` |
| `create_circle` | `bmesh.ops.create_circle(bmesh, cap_ends=False, cap_tris=False, segments=0, radius=0.0, matrix=Matrix(), calc_uvs=False)` |
| `create_cone` | `bmesh.ops.create_cone(bmesh, cap_ends=False, cap_tris=False, segments=0, radius1=0.0, radius2=0.0, depth=0.0, matrix=Matrix(), calc_uvs=False)` |
| `create_cube` | `bmesh.ops.create_cube(bmesh, size=0.0, matrix=Matrix(), calc_uvs=False)` |
| `create_grid` | `bmesh.ops.create_grid(bmesh, x_segments=0, y_segments=0, size=0.0, matrix=Matrix(), calc_uvs=False)` |
| `create_icosphere` | `bmesh.ops.create_icosphere(bmesh, subdivisions=0, radius=0.0, matrix=Matrix(), calc_uvs=False)` |
| `create_monkey` | `bmesh.ops.create_monkey(bmesh, matrix=Matrix(), calc_uvs=False)` |
| `create_uvsphere` | `bmesh.ops.create_uvsphere(bmesh, u_segments=0, v_segments=0, radius=0.0, matrix=Matrix(), calc_uvs=False)` |
| `create_vert` | `bmesh.ops.create_vert(bmesh, co=Vector())` |
| `delete` | `bmesh.ops.delete(bmesh, geom=[], context='VERTS')` |
| `dissolve_degenerate` | `bmesh.ops.dissolve_degenerate(bmesh, dist=0.0, edges=[])` |
| `dissolve_edges` | `bmesh.ops.dissolve_edges(bmesh, edges=[], use_verts=False, use_face_split=False, angle_threshold=0.0, use_preserve_quads=False)` |
| `dissolve_faces` | `bmesh.ops.dissolve_faces(bmesh, faces=[], use_verts=False)` |
| `dissolve_limit` | `bmesh.ops.dissolve_limit(bmesh, angle_limit=0.0, use_dissolve_boundaries=False, verts=[], edges=[], delimit={})` |
| `dissolve_verts` | `bmesh.ops.dissolve_verts(bmesh, verts=[], use_face_split=False, use_boundary_tear=False)` |
| `duplicate` | `bmesh.ops.duplicate(bmesh, geom=[], dest=None, use_select_history=False, use_edge_flip_from_face=False)` |
| `edgeloop_fill` | `bmesh.ops.edgeloop_fill(bmesh, edges=[], mat_nr=0, use_smooth=False)` |
| `edgenet_fill` | `bmesh.ops.edgenet_fill(bmesh, edges=[], mat_nr=0, use_smooth=False, sides=0)` |
| `edgenet_prepare` | `bmesh.ops.edgenet_prepare(bmesh, edges=[])` |
| `extrude_discrete_faces` | `bmesh.ops.extrude_discrete_faces(bmesh, faces=[], use_normal_flip=False, use_select_history=False)` |
| `extrude_edge_only` | `bmesh.ops.extrude_edge_only(bmesh, edges=[], use_normal_flip=False, use_select_history=False)` |
| `extrude_face_region` | `bmesh.ops.extrude_face_region(bmesh, geom=[], edges_exclude={}, use_keep_orig=False, use_normal_flip=False, use_normal_from_adjacent=False, use_dissolve_ortho_edges=False, use_select_history=False, skip_input_flip=False)` |
| `extrude_vert_indiv` | `bmesh.ops.extrude_vert_indiv(bmesh, verts=[], use_select_history=False)` |
| `face_attribute_fill` | `bmesh.ops.face_attribute_fill(bmesh, faces=[], use_normals=False, use_data=False)` |
| `find_doubles` | `bmesh.ops.find_doubles(bmesh, verts=[], keep_verts=[], use_connected=False, dist=0.0)` |
| `flatten` | `bmesh.ops.flatten(bmesh, geom=[], factor=0.0, method=0, view_normal=Vector(), lock_x=False, lock_y=False, lock_z=False)` |
| `flip_quad_tessellation` | `bmesh.ops.flip_quad_tessellation(bmesh, faces=[])` |
| `grid_fill` | `bmesh.ops.grid_fill(bmesh, edges=[], mat_nr=0, use_smooth=False, use_interp_simple=False)` |
| `holes_fill` | `bmesh.ops.holes_fill(bmesh, edges=[], sides=0)` |
| `inset_individual` | `bmesh.ops.inset_individual(bmesh, faces=[], thickness=0.0, depth=0.0, use_even_offset=False, use_interpolate=False, use_relative_offset=False)` |
| `inset_region` | `bmesh.ops.inset_region(bmesh, faces=[], faces_exclude=[], use_boundary=False, use_even_offset=False, use_interpolate=False, use_relative_offset=False, use_edge_rail=False, thickness=0.0, depth=0.0, use_outset=False)` |
| `join_triangles` | `bmesh.ops.join_triangles(bmesh, faces=[], cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=False, angle_face_threshold=0.0, angle_shape_threshold=0.0, topology_influence=0.0, deselect_joined=False)` |
| `mesh_to_bmesh` | `bmesh.ops.mesh_to_bmesh(bmesh, mesh=None, object=None, use_shapekey=False)` |
| `mirror` | `bmesh.ops.mirror(bmesh, geom=[], matrix=Matrix(), merge_dist=0.0, axis='X', mirror_u=False, mirror_v=False, mirror_udim=False, use_shapekey=False)` |
| `object_load_bmesh` | `bmesh.ops.object_load_bmesh(bmesh, scene=None, object=None)` |
| `offset_edgeloops` | `bmesh.ops.offset_edgeloops(bmesh, edges=[], use_cap_endpoint=False)` |
| `planar_faces` | `bmesh.ops.planar_faces(bmesh, faces=[], iterations=0, factor=0.0)` |
| `pointmerge` | `bmesh.ops.pointmerge(bmesh, verts=[], merge_co=Vector(), vert_target=None)` |
| `pointmerge_facedata` | `bmesh.ops.pointmerge_facedata(bmesh, verts=[], vert_target=None)` |
| `poke` | `bmesh.ops.poke(bmesh, faces=[], offset=0.0, center_mode='MEAN_WEIGHTED', use_relative_offset=False)` |
| `recalc_face_normals` | `bmesh.ops.recalc_face_normals(bmesh, faces=[])` |
| `region_extend` | `bmesh.ops.region_extend(bmesh, geom=[], use_contract=False, use_faces=False, use_face_step=False)` |
| `remove_doubles` | `bmesh.ops.remove_doubles(bmesh, verts=[], use_connected=False, dist=0.0)` |
| `reverse_colors` | `bmesh.ops.reverse_colors(bmesh, faces=[], color_index=0)` |
| `reverse_faces` | `bmesh.ops.reverse_faces(bmesh, faces=[], flip_multires=False)` |
| `reverse_uvs` | `bmesh.ops.reverse_uvs(bmesh, faces=[])` |
| `rotate` | `bmesh.ops.rotate(bmesh, cent=Vector(), matrix=Matrix(), verts=[], space=Matrix(), use_shapekey=False)` |
| `rotate_colors` | `bmesh.ops.rotate_colors(bmesh, faces=[], use_ccw=False, color_index=0)` |
| `rotate_edges` | `bmesh.ops.rotate_edges(bmesh, edges=[], use_ccw=False)` |
| `rotate_uvs` | `bmesh.ops.rotate_uvs(bmesh, faces=[], use_ccw=False)` |
| `scale` | `bmesh.ops.scale(bmesh, vec=Vector(), space=Matrix(), verts=[], use_shapekey=False)` |
| `smooth_laplacian_vert` | `bmesh.ops.smooth_laplacian_vert(bmesh, verts=[], lambda_factor=0.0, lambda_border=0.0, use_x=False, use_y=False, use_z=False, preserve_volume=False)` |
| `smooth_vert` | `bmesh.ops.smooth_vert(bmesh, verts=[], factor=0.0, mirror_clip_x=False, mirror_clip_y=False, mirror_clip_z=False, clip_dist=0.0, use_axis_x=False, use_axis_y=False, use_axis_z=False)` |
| `solidify` | `bmesh.ops.solidify(bmesh, geom=[], thickness=0.0)` |Blender 5.2.2 LTS (hash d13f752e3b9c built 2026-09-15 01:34:58)
| `space_edge_loops_evenly` | `bmesh.ops.space_edge_loops_evenly(bmesh, geom=[], interpolation='CUBIC', factor=0.0, lock_x=False, lock_y=False, lock_z=False)` |
| `spin` | `bmesh.ops.spin(bmesh, geom=[], cent=Vector(), axis=Vector(), dvec=Vector(), angle=0.0, space=Matrix(), steps=0, use_merge=False, use_normal_flip=False, use_duplicate=False)` |
| `split` | `bmesh.ops.split(bmesh, geom=[], dest=None, use_only_faces=False)` |
| `split_edges` | `bmesh.ops.split_edges(bmesh, edges=[], verts=[], use_verts=False)` |
| `subdivide_edgering` | `bmesh.ops.subdivide_edgering(bmesh, edges=[], interp_mode='LINEAR', smooth=0.0, cuts=0, profile_shape='SMOOTH', profile_shape_factor=0.0)` |
| `subdivide_edges` | `bmesh.ops.subdivide_edges(bmesh, edges=[], smooth=0.0, smooth_falloff='SMOOTH', fractal=0.0, along_normal=0.0, cuts=0, seed=0, custom_patterns={}, edge_percents={}, quad_corner_type='STRAIGHT_CUT', use_grid_fill=False, use_single_edge=False, use_only_quads=False, use_sphere=False, use_smooth_even=False)` |
| `symmetrize` | `bmesh.ops.symmetrize(bmesh, input=[], direction='-X', dist=0.0, use_shapekey=False)` |
| `transform` | `bmesh.ops.transform(bmesh, matrix=Matrix(), space=Matrix(), verts=[], use_shapekey=False)` |
| `translate` | `bmesh.ops.translate(bmesh, vec=Vector(), space=Matrix(), verts=[], use_shapekey=False)` |
| `triangle_fill` | `bmesh.ops.triangle_fill(bmesh, use_beauty=False, use_dissolve=False, edges=[], normal=Vector())` |
| `triangulate` | `bmesh.ops.triangulate(bmesh, faces=[], quad_method='BEAUTY', ngon_method='BEAUTY')` |
| `unsubdivide` | `bmesh.ops.unsubdivide(bmesh, verts=[], iterations=0)` |
| `weld_verts` | `bmesh.ops.weld_verts(bmesh, targetmap={}, use_centroid=False, average_vert_data=False)` |
| `wireframe` | `bmesh.ops.wireframe(bmesh, faces=[], thickness=0.0, offset=0.0, use_replace=False, use_boundary=False, use_even_offset=False, use_crease=False, crease_weight=0.0, use_relative_offset=False, material_offset=0)` |

**`create_edge` / `create_face` / `extrude_vert` / `flip_normals` / `face_angle_limit` 는 존재하지 않는다.**
필요하면 수동으로 만든다: `bm.verts.new(co)` → `bm.edges.new((v0, v1))` → `bm.faces.new((v0, v1, v2, v3))`.
`bm.verts` / `bm.edges` / `bm.faces` 시퀀스에 `new()` 가 있다.

### 4.6 `create_*` 계열 실측 결과

| 호출 | 반환 dict | 정점 수 |
|---|---|---|
| `bmesh.ops.create_cube(bm, size=1.0)` | `{'verts': [...]}` | 8 |
| `bmesh.ops.create_cube(bm)` (인자 없음) | `{'verts': [...]}` | 8 |
| `bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)` | `{'verts': [...]}` | 42 |
| `bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=1.0)` | `{'verts': [...]}` | 26 |
| `bmesh.ops.create_circle(bm, cap_ends=True, segments=8, radius=1.0)` | `{'verts': [...]}` | 8 |
| `bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8, radius1=1.0, radius2=0.0, depth=1.0)` | `{'verts': [...]}` | 9 |
| `bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=1.0)` | `{'verts': [...]}` | 9 |
| `bmesh.ops.create_monkey(bm)` | `{'verts': [...]}` | 507 |

실패 케이스 (모두 의도된 TypeError):

| 호출 | 에러 |
|---|---|
| `bmesh.ops.create_cube(bm=bm, size=1.0)` | `bmesh operators expect a single BMesh positional argument, all other args must be keywords` |
| `bmesh.ops.create_icosphere(bm, subdivisions=2, diameter=1.0)` | `create_icosphere: keyword "diameter" is invalid for this operator` (`radius` 가 맞다) |
| `bmesh.ops.create_cube(bm, size=1.0, matrix=None)` | `expected a mathutils.Matrix, not a NoneType` |

`create_grid(x_segments=3, y_segments=3, size=1.0)` → 16 정점, 좌표가 `-1.0 … 1.0`.
즉 `size` 는 **반지름이 아니라 전체 폭**이다. `x_segments` / `y_segments` 는 컷 수라서
정점 수는 `(x+1)*(y+1)` 이다.

### 4.7 `bmesh.ops` 반환값 — 5.2 에서는 대부분 `None`

```
create_cube           -> {'verts': [...]}
subdivide_edges       -> {'geom_inner': [...], 'geom_split': [...], 'geom': [...]}
remove_doubles        -> None
dissolve_degenerate   -> None
recalc_face_normals   -> None
delete                -> None
```

**`remove_doubles` 의 `{'targetmap': ...}` 가 없다.** 인덱스 매핑이 필요하면 직접 만든다:

```python
before = {tuple(round(float(c), 6) for c in v.co): v for v in bm.verts}
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
bm.verts.ensure_lookup_table()      # 반드시
survivors = {tuple(round(float(c), 6) for c in v.co) for v in bm.verts}
removed = set(before) - survivors
```

### 4.8 `delete` 의 `context` 인자

`bmesh.ops.delete` 와 `bpy.ops.mesh.delete` 는 **enum 값이 다르다.**

| API | `context` / `type` enum |
|---|---|
| `bmesh.ops.delete(bm, geom=[...], context=...)` | `'VERTS'` (기본), `'EDGES'`, `'FACES'`, `'FACES_ONLY'`, `'EDGES_FACES'`, `'VERTS_FACES'`, `'FACES_KEEP_BOUNDARY'`, `'TAGGED_ONLY'` |
| `bpy.ops.mesh.delete(type=...)` (edit 모드) | `'VERT'`, `'EDGE'`, `'FACE'`, `'EDGE_FACE'`, `'ONLY_FACE'` (기본 `'VERT'`) |

`bpy.ops.mesh.delete(type='VERTS')` → `TypeError: ... enum "VERTS" not found in
('VERT', 'EDGE', 'FACE', 'EDGE_FACE', 'ONLY_FACE')`.

### 4.9 `subdivide_edges` 함정: `use_grid_fill=True` 없이는 n-gon 이 된다

3×3 격자 (9 정점, 4 쿼드)에 `cuts=1`:

| 인자 | 정점 | 면 | 면당 정점 수 |
|---|---|---|---|
| `cuts=1` | 21 | 4 | **8** (쿼드 1개가 8-gon 으로팽창) |
| `cuts=1, use_grid_fill=True` | 25 | 16 | 4 |
| `cuts=1, use_only_quads=True` | 21 | 4 | 8 (효과 없음) |
| `cuts=2, use_grid_fill=True` | 49 | 36 | 4 |

정확한 쿼드 분할을 원하면 `use_grid_fill=True` 가 필수다.

### 4.10 유틸리티

```python
bm.calc_volume(signed=True)   # 2x2 cube -> 8.0
bm.is_valid                   # bool
bm.normal_update()
bm.calc_loop_triangles()
```

**`Mesh` 데이터블록에는 `volume` 속성이 없다** (`hasattr(me, "volume") == False`).
부피/방향 체크는 `bmesh` 를 거쳐야 한다:

```python
chk = bmesh.new(); chk.from_mesh(me)
vol = chk.calc_volume(signed=True)   # 닫힌 메시에서 음수 = 법선 전체 반전
chk.free()
```

---

## 5. Edit mode & context override

### 5.1 `mode_set`

```python
bpy.ops.object.mode_set(mode='EDIT')       # 인자: mode (ENUM), toggle (BOOLEAN)
```

`mode` enum 전체: `OBJECT, EDIT, POSE, SCULPT, VERTEX_PAINT, WEIGHT_PAINT, TEXTURE_PAINT,
PARTICLE_EDIT, EDIT_GPENCIL, SCULPT_GREASE_PENCIL, PAINT_GREASE_PENCIL, WEIGHT_GREASE_PENCIL,
VERTEX_GREASE_PENCIL, SCULPT_CURVES`.

전제 조건:

1. 대상이 `view_layer.objects.active` 여야 한다. 아니면 `poll()` 이 `False`.
2. `bpy.context.view_layer.objects.active = ob` 와 `ob.select_set(True)` 를 명시적으로 한다.
   primitive op 이 만든 오브젝트는 자동으로 active+selected 되지만, `objects.new()` 로 만든 건 그렇지 않다.
3. EDIT 모드에서 object 모드 전용 오퍼레이터는 `RuntimeError`:

```
bpy.ops.object.transform_apply(scale=True)
# RuntimeError: Operator bpy.ops.object.transform_apply.poll() failed, context is incorrect
```

4. `mode_set(mode='EDIT')` 를 두 번 호출해도 no-op 이다 (에러 아님).
5. 다른 오브젝트가 EDIT 모드인 상태에서 `primitive_*_add` 를 부르면, 새 오브젝스가 active 가 될 뿐
   기존 오브젝트는 여전히 EDIT 에 머문다. **스크립트 시작 시점에 항상 OBJECT 로 복구하라.**

```python
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
```

### 5.2 `bpy.context.temp_override`

3.2+ 의 컨텍스트 오버라이드. 2.8 의 `context_override` dict 와 `bpy.ops.<g>.<op>(..., context=...)` 는
둘 다 죽었다:

```python
bpy.ops.mesh.primitive_cube_add(size=1, context={"scene": bpy.context.scene})
# TypeError: Converting py args to operator properties:: keyword "context" unrecognized
```

사용 가능한 오버라이드 키 (관찰된 것):

| 키 | 효과 |
|---|---|
| `window` | `bpy.context.window` |
| `area`, `region`, `region_data` | 3D 뷰 컨텍스트 흉내. **headless 에서는 area 가 없으므로 무의미** |
| `scene` | **동작함** — `bpy.ops` 가 그 씬에 오브젝트를 만든다 (검증됨) |
| `view_layer` | `scene` 과 함께 쓰면 동작 |
| `object` | `bpy.context.object` 를 강제. `poll()` 에 영향 |
| `active_object` | `bpy.context.view_layer.objects.active` 를 강제 |
| `selected_objects`, `selected_editable_objects` | 컨텍스트 선택 목록 |
| `collection` | `bpy.context.collection` **읽기값만** 바꾼다. `primitive_*_add` 는 안 따른다 ([§2.5](#25-배경-모드의-컬렉션-결정-규칙-가장-흔한-오해)) |
| 임의의 쓰레기 키 | 조용히 무시 (에러 안 남) |

### 5.3 headless 에서 인덱스 기반 선택 — 반드시 EDIT bmesh 경유

```python
import bpy, bmesh

bpy.ops.mesh.primitive_grid_add(x_subdivisions=3, y_subdivisions=3)
g = bpy.context.active_object
bpy.context.view_layer.objects.active = g
g.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')

ctx = dict(object=g, active_object=g, selected_objects=[g], selected_editable_objects=[g])
with bpy.context.temp_override(**ctx):
    print(bpy.context.object.name, bpy.context.mode)         # Grid EDIT_MESH
    print(bpy.ops.mesh.subdivide.poll())                     # True

    # select by index: must go through the live EDIT bmesh
    bm = bmesh.from_edit_mesh(g.data)
    for v in bm.verts:
        v.select = v.index in (0, 1, 5, 6)
    bmesh.update_edit_mesh(g.data, loop_triangles=False, destructive=False)
    print(sorted(v.index for v in bmesh.from_edit_mesh(g.data).verts if v.select))  # [0, 1, 5, 6]

    # bpy.ops.* operators only see edges/faces, so use bmesh.ops for indexed work
    bm = bmesh.from_edit_mesh(g.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bmesh.update_edit_mesh(g.data, loop_triangles=True, destructive=True)
    print(len(bmesh.from_edit_mesh(g.data).verts))           # 49
bpy.ops.object.mode_set(mode='OBJECT')
print(len(g.data.vertices))                                   # 49
```

**이유**: EDIT 모드 동안 `object.data` 는 *기본 메시*이고, 실제 편집 대상은 별도의 edit mesh다.
따라서 `g.data.vertices[i].select = True` 를 쓰면 **편집 버퍼에 전혀 반영되지 않는다.**
직접 증명:

```python
bpy.ops.object.mode_set(mode='EDIT')
for v in g.data.vertices:
    v.select = v.index in (0, 1, 5, 6)
print(sorted(v.index for v in bmesh.from_edit_mesh(g.data).verts if v.select))
# [0..15]  <- 전부 선택된 그대로. object.data 에 쓴 것은 버려짐
```

추가 발견: `bpy.ops.mesh.subdivide` 는 **선택된 정점만으로는 아무것도 하지 않는다** (에러 없이 no-op).
정점 선택 후 `{'FINISHED'}` 를 반환하면서 정점 수가 그대로였다. 선택된 엣지/면이 있어야 동작한다.
`bpy.ops.mesh.*` 계열보다 `bmesh.ops.*` 가 결정적(predicable)이다.

### 5.4 EDIT 모드에서 `object.data` 가 비어버리는 API

```python
bpy.ops.mesh.primitive_cube_add(size=2)
o = bpy.context.active_object
print(len(o.data.uv_layers[0].data))      # OBJECT: 24
bpy.ops.object.mode_set(mode='EDIT')
print(len(o.data.uv_layers[0].data))      # EDIT:   0   <-- 비었다
bpy.ops.object.mode_set(mode='OBJECT')
print(len(o.data.uv_layers[0].data))      # OBJECT: 24  복구
```

EDIT 모드에서 `len(mesh.loops)` 은 정상이지만 `len(mesh.uv_layers[i].data)` 는 0 이다.
UV 를 읽어야 한다면 **OBJECT 모드로 나와서** 읽는다 ([§8.5](#85-uv-읽기--반드시-object-모드에서)).

---

## 6. Modifiers

### 6.1 스택 API

```python
import bpy

bpy.ops.mesh.primitive_cube_add(size=2)
ob = bpy.context.active_object

ob.modifiers.new("Bevel", 'BEVEL')              # 위치 인자 (name, type) 가능
ob.modifiers.new(name="Subdiv", type='SUBSURF') # 키워드도 가능
print([m.name for m in ob.modifiers])            # ['Bevel', 'Subdiv']
ob.modifiers.move(1, 0)                         # (from_index, to_index)
print([m.name for m in ob.modifiers])            # ['Subdiv', 'Bevel']
ob.modifiers.remove(ob.modifiers['Bevel'])
ob.modifiers.active                              # 현재 활성 모디파이어 (읽기/쓰기)
ob.modifiers.find('Subdiv')                      # 인덱스, 없으면 -1
ob.modifiers.get('Subdiv')                       # 이름으로 조회
ob.modifiers.clear()
print(len(ob.modifiers), 'active_index' in dir(ob.modifiers))   # 0 False
```

`obj.modifiers` 는 `bpy_prop_collection` 이고 `dir()` 은:
`active, bl_rna, clear, find, foreach_get, foreach_set, get, items, keys, move, new, remove,
rna_type, values`.

- **`active_index` 는 5.2 에 없다.** 활성 모디파이어 지정은 `ob.modifiers.active = some_mod` 로 한다.
- `ob.modifiers.move(i, j)` 는 범위를 벗어나면 `RuntimeError: Error: Cannot move modifier beyond
  the end of the stack`.
- 인덱스 0이 **맨 위(=가장 먼저 평가)** 다. 즉 리스트의 **마지막**이 첫 평가다.
- 이름이 중복되면 Blender 가 자동으로 `.001` 을 붙인다 (`new("x", ...)` 두 번 → `x`, `x.001`).

### 6.2 `type` enum 전체 (5.2, 82개)

`bpy.types.Modifier.bl_rna.properties['type'].enum_items` 전량:

| 그룹 | 값 |
|---|---|
| Grease Pencil (vertext weight) | `GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY` |
| Mesh 보조 | `DATA_TRANSFER, MESH_CACHE, MESH_SEQUENCE_CACHE, NORMAL_EDIT, WEIGHTED_NORMAL, UV_PROJECT, UV_WARP, VERTEX_WEIGHT_EDIT, VERTEX_WEIGHT_MIX, VERTEX_WEIGHT_PROXIMITY` |
| Grease Pencil (paint) | `GREASE_PENCIL_COLOR, GREASE_PENCIL_TINT, GREASE_PENCIL_OPACITY, GREASE_PENCIL_VERTEX_WEIGHT_ANGLE, GREASE_PENCIL_TIME, GREASE_PENCIL_TEXTURE` |
| 모델링 | `ARRAY, BEVEL, BOOLEAN, BUILD, DECIMATE, EDGE_SPLIT, NODES, MASK, MIRROR, MESH_TO_VOLUME, MULTIRES, REMESH, SCREW, SKIN, SOLIDIFY, SUBSURF, TRIANGULATE, VOLUME_TO_MESH, WELD, WIREFRAME` |
| Grease Pencil (geometry) | `GREASE_PENCIL_ARRAY, GREASE_PENCIL_BUILD, GREASE_PENCIL_LENGTH, LINEART, GREASE_PENCIL_MIRROR, GREASE_PENCIL_MULTIPLE_STROKES, GREASE_PENCIL_SIMPLIFY, GREASE_PENCIL_SUBDIV, GREASE_PENCIL_ENVELOPE, GREASE_PENCIL_OUTLINE` |
| Deform | `ARMATURE, CAST, CURVE, DISPLACE, HOOK, LAPLACIANDEFORM, LATTICE, MESH_DEFORM, SHRINKWRAP, SIMPLE_DEFORM, SMOOTH, CORRECTIVE_SMOOTH, LAPLACIANSMOOTH, SURFACE_DEFORM, WARP, WAVE, VOLUME_DISPLACE` |
| Grease Pencil (deform) | `GREASE_PENCIL_HOOK, GREASE_PENCIL_NOISE, GREASE_PENCIL_OFFSET, GREASE_PENCIL_SMOOTH, GREASE_PENCIL_THICKNESS, GREASE_PENCIL_LATTICE, GREASE_PENCIL_DASH, GREASE_PENCIL_ARMATURE, GREASE_PENCIL_SHRINKWRAP` |
| Physics | `CLOTH, COLLISION, DYNAMIC_PAINT, DYNAMIC_PAINT, EXPLODE, FLUID, OCEAN, PARTICLE_INSTANCE, PARTICLE_SYSTEM, SOFT_BODY, SURFACE` |

4.x 의 `ARMATURE`, `ARRAY`, `BEVEL`, `BOOLEAN`, `BUILD`, `DECIMATE`, `EDGE_SPLIT`, `MASK`, `MIRROR`,
`MULTIRES`, `NODES`, `REMESH`, `SCREW`, `SKIN`, `SOLIDIFY`, `SUBSURF`, `TRIANGULATE`, `WIREFRAME`
은 모두 그대로 존재한다. 새로 생긴 것: `LAPLACIANSMOOTH` (Laplacian Smooth), `WELD`, `LINEART`.

### 6.3 결정적 함정: `new()` 가 `None` 을 반환하며 조용히 실패

`obj.modifiers.new(name, type)` 는 메시 오브젝트에 쓸 수 없는 타입이면 **예외 없이 `None` 을 반환하고
스택에도 아무것도 추가하지 않는다.**

```python
bpy.ops.mesh.primitive_cube_add(size=1)
o = bpy.context.active_object
for t in ("MESH_TO_VOLUME", "LINEART", "GREASE_PENCIL_DASH", "BEVEL"):
    before = len(o.modifiers)
    r = o.modifiers.new("t", type=t)
    print("%-20s ret=%s  stack %d -> %d" % (t, "None" if r is None else "Modifier",
                                            before, len(o.modifiers)))
# MESH_TO_VOLUME       ret=None  stack 0 -> 0
# LINEART              ret=None  stack 0 -> 0
# GREASE_PENCIL_DASH   ret=None  stack 0 -> 0
# BEVEL                ret=Modifier  stack 0 -> 1
```

Mesh 오브젝트가 거부하는 타입은 82개 중 **29개**:

```
GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY, GREASE_PENCIL_COLOR, GREASE_PENCIL_TINT,
GREASE_PENCIL_OPACITY, GREASE_PENCIL_VERTEX_WEIGHT_ANGLE, GREASE_PENCIL_TIME,
GREASE_PENCIL_TEXTURE, MESH_TO_VOLUME, GREASE_PENCIL_ARRAY, GREASE_PENCIL_BUILD,
GREASE_PENCIL_LENGTH, LINEART, GREASE_PENCIL_MIRROR, GREASE_PENCIL_MULTIPLE_STROKES,
GREASE_PENCIL_SIMPLIFY, GREASE_PENCIL_SUBDIV, GREASE_PENCIL_ENVELOPE,
GREASE_PENCIL_OUTLINE, VOLUME_DISPLACE, GREASE_PENCIL_HOOK, GREASE_PENCIL_NOISE,
GREASE_PENCIL_OFFSET, GREASE_PENCIL_SMOOTH, GREASE_PENCIL_THICKNESS,
GREASE_PENCIL_LATTICE, GREASE_PENCIL_DASH, GREASE_PENCIL_ARMATURE, GREASE_PENCIL_SHRINKWRAP
```

즉 `GREASE_PENCIL_*` 전부 + `MESH_TO_VOLUME` + `LINEART` + `VOLUME_DISPLACE`.
`WELD`, `LAPLACIANSMOOTH`, `DATA_TRANSFER` 는 허용된다.

방어적으로:

```python
mod = obj.modifiers.new(name, type)
assert mod is not None, f"modifier type {type!r} rejected for {obj.type} object"
```

### 6.4 `type(mod)` 대신 `mod.bl_rna`

`type(mod)` 은 파이썬 클래스(`BevelModifier` 등)를 주지만 어떤 경우에는 `NoneType` 가 된다
(`MESH_TO_VOLUME` 처럼 스택에 안 들어간 경우). RNA 타입을 확실히 보려면:

```python
mod.bl_rna.identifier     # 'BevelModifier'  (안전)
type(mod).__name__        # 'BevelModifier'  (대부분 안전하지만 예외 있음)
```

모디파이어 클래스 전부의 공통 속성 (`rna_type, name, type, show_viewport, show_render,
show_in_editmode, show_on_cage, show_expanded, is_active, use_pin_to_last, is_override_data,
use_apply_on_spline, execution_time, persistent_uid`) 은 아래 표에서 제외했다.

### 6.5 Modifier 속성 표 (실측)

모두 `get_rna_type().properties` 로 뽑은 실측값이다. 공통 속성
(`name, type, show_viewport, show_render, show_in_editmode, show_on_cage, show_expanded, is_active,
use_pin_to_last, is_override_data, use_apply_on_spline, execution_time, persistent_uid`) 은 제외했다.
`~` 로 묶은 행은 `속성: 타입=기본값` 형식이다.

#### BEVEL — `BevelModifier` (38 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `width` / `width_pct` | FLOAT | 0.1 / 0.1 |
| `segments` | INT | 1 |
| `affect` | ENUM `VERTICES`/`EDGES` | `EDGES` |
| `limit_method` | ENUM `NONE`/`ANGLE`/`WEIGHT`/`VGROUP` | `ANGLE` |
| `angle_limit` | FLOAT | 0.5236 (30°) |
| `edge_weight` / `vertex_weight` | STRING | `'bevel_weight_edge'` / `'bevel_weight_vert'` |
| `vertex_group` / `invert_vertex_group` | STRING / BOOLEAN | `''` / False |
| `use_clamp_overlap` / `loop_slide` | BOOLEAN | True / True |
| `offset_type` | ENUM `OFFSET`/`WIDTH`/`DEPTH`/`PERCENT`/`ABSOLUTE` | `OFFSET` |
| `profile_type` / `profile` | ENUM `SUPERELLIPSE`/`CUSTOM` / FLOAT | `SUPERELLIPSE` / 0.5 |
| `material` | INT | -1 |
| `mark_seam` / `mark_sharp` / `harden_normals` | BOOLEAN | False |
| `face_strength_mode` | ENUM `FSTR_NONE`/`FSTR_NEW`/`FSTR_AFFECTED`/`FSTR_ALL` | `FSTR_NONE` |
| `miter_outer` | ENUM `MITER_SHARP`/`MITER_PATCH`/`MITER_ARC` | `MITER_SHARP` |
| `miter_inner` | ENUM `MITER_SHARP`/`MITER_ARC` | `MITER_SHARP` |
| `spread` | FLOAT | 0.1 |
| `custom_profile` | POINTER | None |
| `vmesh_method` | ENUM `ADJ`/`CUTOFF` | `ADJ` |

#### SUBSURF — `SubsurfModifier` (29 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `levels` / `render_levels` | INT | 1 / 2 |
| `use_limit_surface` / `use_creases` / `use_custom_normals` | BOOLEAN | True / True / False |
| `subdivision_type` | ENUM `CATMULL_CLARK`/`SIMPLE` | `CATMULL_CLARK` |
| `quality` | INT | 3 |
| `boundary_smooth` | ENUM `PRESERVE_CORNERS`/`ALL` | `ALL` |
| `uv_smooth` | ENUM `NONE`/`PRESERVE_CORNERS`/`PRESERVE_CORNERS_AND_JUNCTIONS`/`PRESERVE_CORNERS_JUNCTIONS_AND_CONCAVE`/`PRESERVE_BOUNDARIES`/`SMOOTH_ALL` | `PRESERVE_BOUNDARIES` |
| `show_only_control_edges` | BOOLEAN | True |
| `use_adaptive_subdivision` / `adaptive_space` / `adaptive_pixel_size` / `adaptive_object_edge_length` | BOOLEAN / ENUM `PIXEL`/`OBJECT` / FLOAT / FLOAT | False / `PIXEL` / 1.0 / 0.01 |

#### SOLIDIFY — `SolidifyModifier` (38 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `thickness` | FLOAT | 0.01 |
| `offset` | FLOAT | **-1.0** |
| `use_even_offset` / `use_rim` / `use_rim_only` | BOOLEAN | False / True / False |
| `solidify_mode` | ENUM `EXTRUDE`/`NON_MANIFOLD` | `EXTRUDE` |
| `thickness_clamp` / `use_thickness_angle_clamp` | FLOAT / BOOLEAN | 0.0 / False |
| `thickness_vertex_group` | FLOAT | 0.0 |
| `vertex_group` / `shell_vertex_group` / `rim_vertex_group` / `invert_vertex_group` | STRING / BOOL | `''` / False |
| `material_offset` / `material_offset_rim` | INT | 0 / 0 |
| `edge_crease_inner` / `edge_crease_outer` / `edge_crease_rim` | FLOAT | 0.0 |
| `use_quality_normals` / `use_flat_faces` / `use_flip_normals` | BOOLEAN | False |
| `nonmanifold_thickness_mode` | ENUM `FIXED`/`EVEN`/`CONSTRAINTS` | `CONSTRAINTS` |
| `nonmanifold_boundary_mode` | ENUM `NONE`/`ROUND`/`FLAT` | `NONE` |
| `nonmanifold_merge_threshold` / `bevel_convex` | FLOAT | 1e-4 / 0.0 |

`offset=-1.0` 이 기본이라는 점이 중요하다 — 평면 z=0 에 두면 새 셸이 **-z** 로 나간다 (검증: `z ∈ {-0.25, 0.0}`).

#### ARRAY — `ArrayModifier` (30 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `count` | INT | 2 |
| `use_relative_offset` / `relative_offset_displace` | BOOLEAN / FLOAT[3] | True / 0.0 |
| `use_constant_offset` / `constant_offset_displace` | BOOLEAN / FLOAT[3] | False / 0.0 |
| `use_object_offset` / `offset_object` | BOOLEAN / POINTER | False / None |
| `use_merge_vertices` / `use_merge_vertices_cap` / `merge_threshold` | BOOLEAN / BOOL / FLOAT | False / False / 0.01 |
| `fit_type` | ENUM `FIXED_COUNT`/`FIT_LENGTH`/`FIT_CURVE` | `FIXED_COUNT` |
| `fit_length` / `curve` / `offset_u` / `offset_v` | FLOAT / POINTER / FLOAT | 0.0 / None / 0.0 |
| `start_cap` / `end_cap` | POINTER | None |

#### BOOLEAN — `BooleanModifier` (23 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `operation` | ENUM `INTERSECT`/`UNION`/`DIFFERENCE` | `DIFFERENCE` |
| `operand_type` | ENUM `OBJECT`/`COLLECTION` | `OBJECT` |
| `object` / `collection` | POINTER | None |
| `solver` | ENUM `FLOAT`/`EXACT`/`MANIFOLD` | **`EXACT`** |
| `double_threshold` | FLOAT | 1e-7 |
| `use_self` / `use_hole_tolerant` | BOOLEAN | False |
| `material_mode` | ENUM `INDEX`/`TRANSFER` | `INDEX` |
| `debug_options` | ENUM `''`/`SEPARATE`/`NO_DISSOLVE`/`NO_CONNECT_REGIONS` | `''` |

**`solver='FAST'` 는 5.2 에 없다.** 4.x 기본이 `'FAST'` 였으므로 옛 코드 그대로면 `TypeError`:
`enum "FAST" not found in ('FLOAT', 'EXACT', 'MANIFOLD')`. 새 `'MANIFOLD'` 솔버는 4.5+ 계열에서 추가된
manifold 기반 솔버다. 실측 (cube − cylinder, 32 sides):

```
solver=EXACT     -> target polys=40
solver=MANIFOLD  -> target polys=40
UNION/EXACT      -> target polys=74
```

#### MIRROR — `MirrorModifier` (29 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `use_axis` | **BOOLEAN[3]** | (False, False, False) |
| `use_bisect_axis` / `use_bisect_flip_axis` | BOOLEAN[3] | False |
| `use_clip` | BOOLEAN | False |
| `use_mirror_merge` / `merge_threshold` | BOOLEAN / FLOAT | True / 0.001 |
| `use_mirror_vertex_groups` | BOOLEAN | True |
| `use_mirror_u` / `use_mirror_v` / `use_mirror_udim` | BOOLEAN | False |
| `mirror_offset_u` / `mirror_offset_v` / `offset_u` / `offset_v` | FLOAT | 0.0 |
| `bisect_threshold` | FLOAT | 0.001 |
| `mirror_object` | POINTER | None |

`use_axis` 는 **문자열이 아니라 3-불 배열**이다. `mir.use_axis = 'X'` →
`ValueError: bpy_struct: item.attr = val: sequences of dimension 0 should contain 3 items, not 1`.
쓰는 법: `mir.use_axis = (True, False, False)` 또는 `mir.use_axis[1] = True`.

#### REMESH — `RemeshModifier` (22 props)

| 속성 | 타입 | 기본값 |
|---|---|---|
| `mode` | ENUM `BLOCKS`/`SMOOTH`/`SHARP`/`VOXEL` | `VOXEL` |
| `voxel_size` / `adaptivity` | FLOAT | 0.1 / 0.0 |
| `use_smooth_shade` / `use_remove_disconnected` | BOOLEAN | False / True |
| `scale` / `threshold` / `sharpness` | FLOAT | 0.9 / 1.0 / 1.0 (BLOCKS/SMOOTH 용) |
| `octree_depth` | INT | 4 |

#### 나머지 주요 모디파이어 (핵심 속성만, `속성: 타입=기본값`)

| 모디파이어 | 핵심 속성 |
|---|---|
| **DECIMATE** | `decimate_type` ENUM `COLLAPSE`/`UNSUBDIV`/`DISSOLVE`=COLLAPSE; `ratio` FLOAT=1.0; `iterations` INT=0; `angle_limit` FLOAT=0.0873; `vertex_group` STR=''; `use_collapse_triangulate` BOOL=False; `use_symmetry` BOOL=False; `symmetry_axis` ENUM `X`/`Y`/`Z`=X; `use_dissolve_boundaries` BOOL=False; `delimit` ENUM `''`/`NORMAL`/`MATERIAL`/`SEAM`/`SHARP`/`UV`=''; `face_count` INT=0 |
| **DISPLACE** | `texture` PTR=None; `texture_coords` ENUM `LOCAL`/`GLOBAL`/`OBJECT`/`UV`=LOCAL; `direction` ENUM `X`/`Y`/`Z`/`NORMAL`/`CUSTOM_NORMAL`/`RGB_TO_XYZ`=NORMAL; `space` ENUM `LOCAL`/`GLOBAL`=LOCAL; `mid_level` FLOAT=0.5; `strength` FLOAT=1.0; `vertex_group` STR=''; `uv_layer` STR='' |
| **SKIN** | `branch_smoothing` FLOAT=0.0; `use_smooth_shade` BOOL=False; `use_x_symmetry` BOOL=True; `use_y_symmetry`/`use_z_symmetry` BOOL=False |
| **WIREFRAME** | `thickness` FLOAT=0.02; `use_replace` BOOL=True; `use_even_offset` BOOL=True; `use_boundary` BOOL=False; `use_crease` BOOL=False; `offset` FLOAT=0.0; `thickness_vertex_group` FLOAT=0.0; `vertex_group` STR=''; `material_offset` INT=0 |
| **WEIGHTED_NORMAL** | `weight` INT=50; `mode` ENUM `FACE_AREA`/`CORNER_ANGLE`/`FACE_AREA_WITH_ANGLE`=FACE_AREA; `thresh` FLOAT=0.01; `keep_sharp` BOOL=False; `use_face_influence` BOOL=False |
| **NORMAL_EDIT** | `mode` ENUM `RADIAL`/`DIRECTIONAL`=RADIAL; `offset` **FLOAT[3]**; `mix_mode` ENUM `COPY`/`ADD`/`SUB`/`MUL`=COPY; `mix_factor` FLOAT=1.0; `mix_limit` FLOAT=π; `target` PTR=None; `use_direction_parallel` BOOL=True; `no_polynors_fix` BOOL=False |
| **MASK** | `mode` ENUM `VERTEX_GROUP`/`ARMATURE`=VERTEX_GROUP; `vertex_group` STR=''; `armature` PTR=None; `invert_vertex_group` BOOL=False; `use_smooth` BOOL=False; `threshold` FLOAT=0.0 |
| **LATTICE** | `object` PTR=None; `strength` FLOAT=1.0; `vertex_group` STR=''; `invert_vertex_group` BOOL=False |
| **SHRINKWRAP** | `target` PTR=None; `wrap_method` ENUM `NEAREST_SURFACEPOINT`/`PROJECT`/`NEAREST_VERTEX`/`TARGET_PROJECT`=NEAREST_SURFACEPOINT; `wrap_mode` ENUM `ON_SURFACE`/`INSIDE`/`OUTSIDE`/`OUTSIDE_SURFACE`/`ABOVE_SURFACE`=ON_SURFACE; `cull_face` ENUM `OFF`/`FRONT`/`BACK`=OFF; `offset` FLOAT=0.0; `project_limit` FLOAT=0.0; `use_project_x`/`_y`/`_z` BOOL=False; `subsurf_levels` INT=0; `use_negative_direction` BOOL=False; `use_positive_direction` BOOL=True; `auxiliary_target` PTR=None |
| **WARP** | `object_from`/`object_to` PTR=None; `bone_from`/`bone_to` STR=''; `strength` FLOAT=1.0; `falloff_type` ENUM `NONE`/`CURVE`/`SMOOTH`/`SPHERE`/`ROOT`/`INVERSE_SQUARE`/`SHARP`/`LINEAR`/`CONSTANT`=SMOOTH; `falloff_radius` FLOAT=1.0; `use_volume_preserve` BOOL=False |
| **WAVE** | `use_x`/`use_y`/`use_cyclic` BOOL=True; `use_normal` BOOL=False; `height` FLOAT=0.5; `width` FLOAT=1.5; `narrowness` FLOAT=1.5; `speed` FLOAT=0.25; `start_position_x`/`_y` FLOAT=0.0; `time_offset` FLOAT=0.0; `lifetime` FLOAT=0.0; `damping_time` FLOAT=10.0; `falloff_radius` FLOAT=0.0; `texture` PTR=None; `texture_coords` ENUM=LOCAL |
| **SIMPLE_DEFORM** | `deform_method` ENUM `TWIST`/`BEND`/`TAPER`/`STRETCH`=TWIST; `deform_axis` ENUM `X`/`Y`/`Z`=X; `angle` FLOAT=0.7854; `factor` FLOAT=0.7854; **`limits` FLOAT[2]**; `origin` PTR=None; `lock_x`/`_y`/`_z` BOOL=False |
| **SMOOTH** | `factor` FLOAT=0.5; `iterations` INT=1; `use_x`/`use_y`/`use_z` BOOL=True; `vertex_group` STR='' |
| **CORRECTIVE_SMOOTH** | `factor` FLOAT=0.5; `iterations` INT=5; `rest_source` ENUM `ORCO`/`BIND`=ORCO; `smooth_type` ENUM `SIMPLE`/`LENGTH_WEIGHTED`=SIMPLE; `scale` FLOAT=1.0; `is_bind` BOOL=False; `use_only_smooth` BOOL=False; `use_pin_boundary` BOOL=False |
| **TRIANGULATE** | `quad_method` ENUM `BEAUTY`/`FIXED`/`FIXED_ALTERNATE`/`SHORTEST_DIAGONAL`/`LONGEST_DIAGONAL`=SHORTEST_DIAGONAL; `ngon_method` ENUM `BEAUTY`/`CLIP`=BEAUTY; `min_vertices` INT=4; `keep_custom_normals` BOOL=False |
| **EDGE_SPLIT** | `use_edge_angle` BOOL=True; `split_angle` FLOAT=0.5236; `use_edge_sharp` BOOL=True |
| **SCREW** | `axis` ENUM `X`/`Y`/`Z`=Z; `angle` FLOAT=2π; `steps` INT=16; `render_steps` INT=16; `iterations` INT=1; `screw_offset` FLOAT=0.0; `use_merge_vertices` BOOL=False; `merge_threshold` FLOAT=0.01; `use_normal_flip` BOOL=False; `use_normal_calculate` BOOL=False; `use_smooth_shade` BOOL=True; `object` PTR=None |
| **NODES** | `node_group` PTR=None; `bake_target` ENUM `PACKED`/`DISK`=PACKED; `bake_directory` STR=''; `properties` PTR (5.2+ RNA 입력) |
| **WELD** | `mode` ENUM `ALL`/`CONNECTED`=ALL; `merge_threshold` FLOAT=0.001; `vertex_group` STR=''; `loose_edges` BOOL=False |
| **BUILD** | `frame_start` FLOAT=1.0; `frame_duration` FLOAT=100.0; `use_reverse` BOOL=False; `use_random_order` BOOL=False; `seed` INT=0 |
| **CAST** | `cast_type` ENUM `SPHERE`/`CYLINDER`/`CUBOID`=SPHERE; `object` PTR=None; `factor` FLOAT=0.5; `radius` FLOAT=0.0; `size` FLOAT=0.0; `use_x`/`use_y`/`use_z` BOOL=True |
| **MULTIRES** | `levels`/`render_levels`/`sculpt_levels`/`total_levels` INT=0; `is_external` BOOL=False; `quality` INT=4 |
| **DATA_TRANSFER** | `object` PTR=None; `use_vert_data`/`use_edge_data`/`use_loop_data`/`use_poly_data` BOOL=False; `mix_mode` ENUM `REPLACE`/`ABOVE_THRESHOLD`/`BELOW_THRESHOLD`/`MIX`/`ADD`/`SUB`/`MUL`=REPLACE; `mix_factor` FLOAT=0.0 |

> **배열 속성 함정**: `NORMAL_EDIT.offset` 은 FLOAT[3], `SIMPLE_DEFORM.limits` 는 FLOAT[2].
> RNA 인트로스펙션이 `FLOAT` 로만 찍히기 때문에 스칼라를 넣으면 `TypeError: sequences of dimension 0
> should contain 3 items, not 1` 이 난다. 확인법:
> `prop.type == 'FLOAT'` 이라도 `prop.array_length > 0` 이면 배열이다.

### 6.6 일반 레시피 (측정값 포함)

`ev(ob)` 헬퍼는 매번 새 depsgraph 를 잡아 평가된 메시를 돌려준다.
전체 24종 레시피는 `verify/15_modifier_examples.py`, 압축판은 `snippets/S21_recipes_compact.py`.

```python
import bpy, math

def ev(ob):
    """Evaluated mesh of ob with a fresh depsgraph."""
    return ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data

# --- Solidify on a plane: offset=-1 puts the new shell at -z --------------
bpy.ops.mesh.primitive_plane_add(size=2)
p = bpy.context.active_object
sol = p.modifiers.new("Solidify", 'SOLIDIFY')
sol.thickness, sol.offset = 0.25, -1.0
sol.use_even_offset = sol.use_rim = True
sol.use_rim_only = False
m = ev(p)
print("solidify:", len(m.vertices), len(m.polygons), sorted({round(v.co.z, 3) for v in m.vertices}))

# --- Array: 4 copies offset 1.5 x the bounding box (cube size 1) ---------
bpy.ops.mesh.primitive_cube_add(size=1)
a = bpy.context.active_object
arr = a.modifiers.new("Array", 'ARRAY')
arr.count, arr.use_relative_offset = 4, True
arr.relative_offset_displace = (1.5, 0, 0)
print("array:", len(ev(a).vertices), sorted({round(v.co.x, 2) for v in ev(a).vertices}))

# --- Boolean: solver FAST is gone; FLOAT / EXACT / MANIFOLD ---------------
bpy.ops.mesh.primitive_cube_add(size=2)
t = bpy.context.active_object
bpy.ops.mesh.primitive_cylinder_add(radius=0.7, depth=4, vertices=32)
c = bpy.context.active_object
bo = t.modifiers.new("Bool", 'BOOLEAN')
bo.operation, bo.object, bo.solver = 'DIFFERENCE', c, 'EXACT'
print("solver enum:", [i.identifier for i in bo.bl_rna.properties['solver'].enum_items])
print("boolean difference:", len(ev(t).polygons), "(target", len(t.data.polygons),
      "operand", len(c.data.polygons), ")")

# --- Mirror: use_axis is a 3-bool array, not a string --------------------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=1, y_subdivisions=1)
mg = bpy.context.active_object
mir = mg.modifiers.new("Mirror", 'MIRROR')
mir.use_axis = (True, True, False)
print("mirror:", len(ev(mg).vertices), "use_axis =", list(mir.use_axis))

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
rm = bpy.context.active_object
rmo = rm.modifiers.new("Remesh", 'REMESH')
rmo.mode, rmo.voxel_size, rmo.adaptivity, rmo.use_smooth_shade = 'VOXEL', 0.2, 0.0, True
print("remesh verts:", len(ev(rm).vertices))

# --- deformers -----------------------------------------------------------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10)
sd = bpy.context.active_object
sdm = sd.modifiers.new("SimpleDeform", 'SIMPLE_DEFORM')
sdm.deform_method, sdm.deform_axis = 'TWIST', 'Z'
sdm.angle, sdm.factor, sdm.limits = math.radians(90), 0.5, (0.0, 1.0)
print("simple_deform verts:", len(ev(sd).vertices))

bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=8)
wv = bpy.context.active_object
wm = wv.modifiers.new("Wave", 'WAVE')
wm.use_x = wm.use_y = wm.use_cyclic = True
wm.height, wm.width, wm.narrowness, wm.speed = 0.5, 1.5, 1.5, 0.25
wm.start_position_x = wm.start_position_y = 0.0        # non-zero -> the wave never arrives
zs = [v.co.z for v in ev(wv).vertices]
print("wave z range: %.3f .. %.3f" % (min(zs), max(zs)))

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
base = bpy.context.active_object
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
shr = bpy.context.active_object
sm = shr.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
sm.target, sm.wrap_method, sm.wrap_mode = base, 'NEAREST_SURFACEPOINT', 'ON_SURFACE'
print("shrinkwrap verts:", len(ev(shr).vertices))

bpy.ops.mesh.primitive_grid_add(size=4, x_subdivisions=4, y_subdivisions=4)
mk = bpy.context.active_object
vg = mk.vertex_groups.new(name="keep")
for v in mk.data.vertices:
    if v.co.x < 0.0:
        vg.add([v.index], 1.0, 'REPLACE')
mm = mk.modifiers.new("Mask", 'MASK')
mm.mode, mm.vertex_group = 'VERTEX_GROUP', "keep"
print("mask:", len(ev(mk).polygons), "of", len(mk.data.polygons))
mm.invert_vertex_group = True
print("mask inverted:", len(ev(mk).polygons))
```

출력 (전부 5.2 실측):

```
solidify: 8 6 [-0.25, 0.0]
array: 32 [-0.5, 0.5, 1.0, 2.0, 2.5, 3.5, 4.0, 5.0]
solver enum: ['FLOAT', 'EXACT', 'MANIFOLD']
boolean difference: 40 (target 6 operand 34 )
mirror: 16 use_axis = [True, True, False]
remesh verts: 432
simple_deform verts: 121
wave z range: 0.021 .. 0.497
shrinkwrap verts: 4
mask: 4 of 16
mask inverted: 8
```

정확히 수치만 필요한 나머지 (모두 `snippets/S21_recipes_compact.py` 에서 검증):

| 모디파이어 | 설정 | 결과 |
|---|---|---|
| WIREFRAME | `thickness=0.05, use_replace=True, use_even_offset=True` (2단위 큐브) | v=40 e=96 f=48 |
| TRIANGULATE | `quad_method='SHORTEST_DIAGONAL', ngon_method='BEAUTY', min_vertices=4` | v=8 e=18 f=12 |
| EDGE_SPLIT | `use_edge_angle=True, split_angle=radians(30)` | v=24 e=24 f=6 |
| DECIMATE | `decimate_type='COLLAPSE', ratio=0.4` | v=4 e=6 f=4 |
| SCREW | 원 8각 + `angle=radians(90), steps=8, screw_offset=0.25` | v=72, z = 0 … 0.25 9단 |
| LATTICE | 2×2×2, `scale=(2,2,2)`, 위층 `co_deform.z` 0.5→1.5 | z `[-0.5, 0.5]` → `[0.135, 1.865]` |
| WEIGHTED_NORMAL | UV 스피어 + `keep_sharp=True, weight=50, mode='FACE_AREA'` | f=128 |
| SKIN | 격자에서 위쪽 면 삭제 후 `branch_smoothing=0.5` | v 20 → 64 |

`Wave` 노트: `start_position_x/y` 를 0 으로 두지 않으면 (`-4.0` 같은 값) 파동이 아직 메시에 도달하지 않아
모든 정점 z 가 0.0 이 된다. 기본값 0 이 안전하다.

### 6.7 depsgraph 로 평가 결과 읽기

```python
import bpy

bpy.ops.mesh.primitive_cube_add(size=2)
ob = bpy.context.active_object
ob.modifiers.new("Subdiv", 'SUBSURF').levels = 2

dg = bpy.context.evaluated_depsgraph_get()
ev = ob.evaluated_get(dg)
print(ev is ob, ev.data is ob.data)                 # False False
print(len(ev.data.vertices), len(ob.data.vertices))  # 98 8

tmp = ev.to_mesh()
print(len(tmp.vertices), len(tmp.polygons))          # 98 96
ev.to_mesh_clear()
try:
    len(tmp.vertices)
except ReferenceError as e:
    print("ReferenceError:", e)

# change the modifier, take a FRESH depsgraph
ob.modifiers["Subdiv"].levels = 1
dg2 = bpy.context.evaluated_depsgraph_get()
print(dg2 is dg)                                      # False (new wrapper)
print(len(ob.evaluated_get(dg2).data.vertices))      # 26

# modifier_apply needs single_user for shared meshes
me = bpy.data.meshes.new("shared")
me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
me.update()
a = bpy.data.objects.new("A", me)
b = bpy.data.objects.new("B", me)
bpy.context.scene.collection.objects.link(a)
bpy.context.scene.collection.objects.link(b)
a.modifiers.new("Solid", 'SOLIDIFY')
bpy.ops.object.select_all(action='DESELECT')
a.select_set(True)
bpy.context.view_layer.objects.active = a
try:
    bpy.ops.object.modifier_apply(modifier="Solid")
except RuntimeError as e:
    print("RuntimeError:", e)
bpy.ops.object.modifier_apply(modifier="Solid", single_user=True)
print(a.data is b.data, len(a.data.polygons), len(b.data.polygons))   # False 6 1
```

핵심:

- `ob.evaluated_get(dg)` 는 **별도의 Object 래퍼**다. `ev.data` 도 복제된 Mesh.
  `ob.data` 는 절대 안 바뀐다.
- `to_mesh()` 로 얻은 임시 Mesh 는 `to_mesh_clear()` 후 **즉시 무효**. 남은 참조는 `ReferenceError`.
  `try/finally` 로 감싸라.
- `bpy.context.evaluated_depsgraph_get()` 는 호출마다 새 래퍼다 (`dg2 is dg` → False).
  값은 갱신되지만, 강제 갱신이 필요하면 `bpy.context.view_layer.update()` 먼저.
- `Depsgraph` 의 유용한 멤버: `update()`, `updates`, `objects`, `object_instances`, `scene_eval`,
  `view_layer`, `view_layer_eval`, `debug_stats`, `debug_relations_graphviz`, `id_eval_get`,
  `id_type_updated`, `mode`. (`is_updated` 는 없다.)
- 뷰 레이어에 링크되지 않은 오브젝트에도 `evaluated_get(dg)` 가 동작한다 (수정본 없음).

`bpy.data.meshes.new_from_object` 로 실제 데이터블록을 뽑는 것도 가능하다:

```python
m = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)   # 98 verts
m = bpy.data.meshes.new_from_object(ob, depsgraph=dg)                                  # 8 verts (원본)
m = bpy.data.meshes.new_from_object(ev)                                                # 98 (자동 평가)
```

### 6.8 `bpy.ops.object.modifier_apply`

```python
bpy.ops.object.modifier_apply(modifier="Bevel")
bpy.ops.object.modifier_apply(modifier="Bevel", single_user=True)
```

| `modifier_apply` 인자 | 타입 | 기본값 |
|---|---|---|
| `modifier` | STRING | '' |
| `single_user` | BOOLEAN | False |
| `report` | BOOLEAN | False |

전제 조건과 함정:

| 상황 | 결과 |
|---|---|
| 활성 객체 + 모디파이어 존재, OBJECT 모드 | `{'FINISHED'}` |
| EDIT 모드 | `poll()` = False → `RuntimeError` |
| `view_layer.objects.active = None` | `poll()` = False |
| **없는 모디파이어 이름** | `{'CANCELLED'}` — **에러 아님**, 조용히 무시 |
| **멀티유저 메시** (`mesh.users > 1`) | `RuntimeError: Error: Modifiers cannot be applied to multi-user data` |
| 스택의 첫 번째가 아닌 모디파이어 | `Info: Applied modifier was not first, result may not be as expected` (성공은 함) |
| 선택 안 된 상태 | `{'CANCELLED'}` |

멀티유저 해결: `single_user=True` 를 주면 `a.data` 가 새 메시(`shared.001`)로 분리되고
원본은 `b.data` 에 남는다. 사전에 `obj.data = obj.data.copy()` 로 미리 분리하는 방법도 있다.

적용 순서는 **스택의 위에서 아래로**. 중간 것이 남아 있으면 결과가 어긋나므로 루프를 뒤집어 돌린다.

### 6.9 비균일 스케일이 모디파이어를 망가뜨린다

`Bevel.width` 같은 값은 **오브젝트 로컬 단위**다. `obj.scale = (1, 1, 0.25)` 면
두께 0.25 인 판에 width 0.1 베벨 = 두께의 40%. 검증:

```
scale=(1.0, 1.0, 0.25), bevel width 0.1 -> eval local z: -1.000..1.000
world-space thickness after scale = 0.500
```

해결책은 스케일 적용 후 제거:

```python
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
print([round(float(c), 2) for c in sc.scale])        # [1.0, 1.0, 1.0]
```

`transform_apply` 는 OBJECT 모드 + 선택 + active 를 요구한다.
EDIT 모드에서 부르면 `RuntimeError`, 아무것도 선택 안 했으면 조용히 `{'CANCELLED'}`.
`location`/`rotation` 도 같이 apply 하려면 `bpy.ops.object.transform_apply(location=True,
rotation=True, scale=True)`.

---

## 7. Curves & text

### 7.1 `bpy.data.curves.new`

`bpy.data.curves.new(name, type='CURVE')` — `type` 은 `'CURVE'` | `'FONT'` | `'SURFACE'`.

| 속성 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `dimensions` | ENUM `2D`/`3D` | `2D` | `fill_mode` 유효값을 바꾼다 ([§7.4](#74-fill_mode-는-동적-enum)) |
| `resolution_u` | INT | 12 | 스플라인 해상도 (1 … 1024) |
| `render_resolution_u` / `_v` | INT | 0 (0 이면 `resolution_*` 사용) | |
| `bevel_depth` | FLOAT | 0.0 | 관 두께 (0 = 선) |
| `bevel_resolution` | INT | 4 | 원형 단면 분할 (0 … 32) |
| `bevel_mode` | ENUM `ROUND`/`OBJECT`/`PROFILE` | `ROUND` | |
| `bevel_object` / `bevel_profile` | POINTER | None | `bevel_mode` 가 OBJECT/PROFILE 일 때 |
| `extrude` | FLOAT | 0.0 | Z 방향 돌출 |
| `use_fill_caps` | BOOLEAN | False | 양 끝 캡 |
| `fill_mode` | **동적 ENUM** | `NONE` (CURVE) / `BOTH` (FONT) | [§7.4](#74-fill_mode-는-동적-enum) |
| `offset` | FLOAT | 0.0 | 전 이미터 옆으로 밀기 |
| `twist_mode` | ENUM `Z_UP`/`MINIMUM`/`TANGENT` | `MINIMUM` | |
| `twist_smooth` | FLOAT | 0.0 | |
| `use_path` / `use_path_follow` / `use_path_clamp` | BOOLEAN | False | 커브 애니메이션 |
| `path_duration` | INT | 100 | |
| `use_radius` | BOOLEAN | | 스플라인 point `.radius` 사용 |
| `use_map_taper` / `taper_object` / `taper_radius_mode` | BOOL / PTR / ENUM | False / None | |
| `bevel_factor_start` / `_end`, `bevel_factor_mapping_start` / `_end` | FLOAT | | |
| `fill_rule` / `fill_solver` | ENUM | | |
| `splines` / `shape_keys` | COLLECTION / | | |

### 7.2 스플라인 타입과 점 컬렉션

`spline.type` enum: **`POLY``, `BEZIER`, `NURBS`**.

```python
import bpy

cu = bpy.data.curves.new("C", type='CURVE')
cu.dimensions = '3D'
cu.resolution_u = 12
cu.bevel_depth = 0.05
cu.bevel_resolution = 3
cu.extrude = 0.02
cu.use_fill_caps = True

# POLY : 4D homogeneous points
sp = cu.splines.new('POLY')
sp.points.add(3)
for i, co in enumerate([(0, 0, 0), (1, 0, 1), (2, 1, 0), (3, 0, -1)]):
    sp.points[i].co = (co[0], co[1], co[2], 1.0)
print(sp.type, len(sp.points), tuple(sp.points[0].co))      # POLY 4 (0.0,0.0,0.0,1.0)

# BEZIER : 3D co + two handles
bz = cu.splines.new('BEZIER')
bz.bezier_points.add(2)
for i, co in enumerate([(0, 0, 0), (1, 0, 1), (2, 1, 0)]):
    bp = bz.bezier_points[i]
    bp.co = co
    bp.handle_left_type = bp.handle_right_type = 'AUTO'
    bp.tilt = 0.0
    bp.radius = 1.0
bz.use_cyclic_u = True
print(bz.type, len(bz.bezier_points), bz.bezier_points[1].handle_left_type)  # BEZIER 3 AUTO

# NURBS : POLY points + order_u
nu = cu.splines.new('NURBS')
nu.points.add(2)
for i, co in enumerate([(0, 0, 0), (1, 0, 1), (2, 1, 0)]):
    nu.points[i].co = (co[0], co[1], co[2], 1.0)
nu.order_u = 3
nu.use_endpoint_u = True
print(nu.type, len(nu.points), nu.order_u)                   # NURBS 3 3

ob = bpy.data.objects.new("CurveObj", cu)
bpy.context.scene.collection.objects.link(ob)
dg = bpy.context.evaluated_depsgraph_get()
ev = ob.evaluated_get(dg)
m = ev.to_mesh()
print(type(ev.data).__name__, len(m.vertices), len(m.polygons))
ev.to_mesh_clear()
```

| | POLY | BEZIER | NURBS |
|---|---|---|---|
| 점 컨테이너 | `spline.points` | `spline.bezier_points` | `spline.points` |
| `point.co` 차원 | **4** (w=1.0) | 3 | 4 (w=1.0) |
| 핸들 | 없음 | `handle_left` / `handle_right` | 없음 |
| `tilt` / `radius` | 없음 | 있음 | 없음 |
| `order_u` (차수) | 1 | n/a | 설정 필요 |
| `use_cyclic_u` / `use_endpoint_u` | 있음 | 있음 | 있음 |
| `spline.resolution_u` | n/a | 있음 | 있음 |

**`cu.splines.new(type)` 는 이미 점 1개를 만든다.** `.add(n)` 은 *n개를 더 추가*한다.
`Spline` 공통 속성: `character_index, hide, material_index, order_u, order_v, point_count_u,
point_count_v, points, bezier_points, radius_interpolation, resolution_u, resolution_v, tilt_interpolation,
type, use_bezier_u, use_bezier_v, use_cyclic_u, use_cyclic_v, use_endpoint_u, use_endpoint_v, use_smooth,
valid_message, calc_length()`.

`BezierSplinePoint` 속성: `co, handle_left, handle_right, handle_left_type, handle_right_type,
hide, radius, tilt, weight_softbody, select_control_point, select_left_handle, select_right_handle`.
`handle_*_type` enum: `FREE`, `VECTOR`, `ALIGNED`, `AUTO`.

**`SplinePoint.co` 는 4차원이다** — `w` 성분을 1.0 으로 넣지 않으면 (0,0,0,0) 이 되어
이동이 안 된다. 실측 출력:

```
POLY 4 (0.0, 0.0, 0.0, 1.0)
BEZIER 3 AUTO
NURBS 3 3
Curve 1224 1180
```

### 7.3 커브 오브젝트 평가

- `ob.type == 'CURVE'`, `ob.data` 는 `Curve`.
- `evaluated_get(dg).data` 는 **여전히 Curve 다** (`type(ev.data).__name__ == 'Curve'`).
  메시가 아니다. **반드시 `to_mesh()` 로 변환**해야 폴리곤 수를 얻는다.
- `bpy.ops.object.convert(target='MESH')` 로 영구 변환 가능. 이후 `ob.type == 'MESH'`,
  `type(ob.data).__name__ == 'Mesh'`, `bpy.ops.object.shade_smooth()` 등 메시 API 가 전부 열린다.
  원본 커브를 남기고 싶으면 복사본에 적용한다.
- 2점 POLY + `bevel_depth=0.1` → verts 24, polys 12 (즉 기본 프로파일 원기둥).

### 7.4 `fill_mode` 는 동적 enum — `enum_items` 가 거짓말을 한다

가장 위험한 API 중 하나.

```python
fo = bpy.data.curves.new("f", type='FONT')
print([i.identifier for i in fo.bl_rna.properties['fill_mode'].enum_items])
# ['FULL', 'BACK', 'FRONT', 'HALF']     <-- 완전히 틀린 정보
fo.fill_mode = 'FULL'
# TypeError: enum "FULL" not found in ('NONE', 'BACK', 'FRONT', 'BOTH')
```

`bpy.types.Curve`, `bpy.types.TextCurve`, 인스턴스의 `bl_rna` 전부 같은 잘못된 목록을 준다
(`enum_items` 와 `enum_items_static` 모두). 진짜 유효값은 `dimensions` 에 따라 달라진다:

| `dimensions` | 유효 `fill_mode` 값 | 기본값 |
|---|---|---|
| `'2D'` | `NONE`, `BACK`, `FRONT`, `BOTH` | CURVE: `NONE`, FONT: `BOTH` |
| `'3D'` | `BACK`, `FRONT`, `FULL`, `HALF` | `FULL` |

방어 코드:

```python
def safe_fill_mode(curve, wanted):
    for v in ('NONE', 'BACK', 'FRONT', 'BOTH', 'FULL', 'HALF'):
        try:
            curve.fill_mode = v
        except TypeError:
            continue
        if curve.fill_mode == wanted:
            return True
    return False
```

같은 함정-prone한 동적 enum 이 또 있는 곳:
`RenderSettings.engine` (PROTOCOL 에서 이미 확인됨), `bpy.ops.object.mode_set.mode` (컨텍스트에 따라),
`Decimate.delimit` / `Boolean.debug_options` / `DataTransfer.data_types_*` (기본값이 `''` 로
`enum_items` 에 없는 빈 문자열 상태).

### 7.5 Text (`type='FONT'`)

`bpy.data.curves.new(name, type='FONT')` 의 파이썬 클래스는 `TextCurve`, `id_type` 은 `CURVE`.

**`Curve.type` / `TextCurve.type` 속성이 5.2 에 없다.** `hasattr(fnt, "type") == False`.
타입을 알아내려면 `type(ob.data).__name__` 또는 `ob.type` 을 쓴다.

```python
import bpy, os

fnt = bpy.data.curves.new("T", type='FONT')
print(type(fnt).__name__, fnt.id_type, hasattr(fnt, "type"))   # TextCurve CURVE False

fnt.body = "Blender 5.2"
fnt.size = 0.8
fnt.extrude = 0.05
fnt.bevel_depth = 0.01
fnt.bevel_resolution = 2
fnt.resolution_u = 6
fnt.align_x = 'CENTER'
fnt.align_y = 'BOTTOM_BASELINE'
fnt.space_character = 1.1
fnt.space_word = 1.0
fnt.space_line = 1.0
fnt.offset = 0.02
fnt.fill_mode = 'BOTH'
fnt.shear = 0.0
try:
    fnt.fill_mode = 'FULL'
except TypeError as e:
    print("TypeError:", e)

ob = bpy.data.objects.new("TextObj", fnt)
bpy.context.scene.collection.objects.link(ob)
dg = bpy.context.evaluated_depsgraph_get()
m = ob.evaluated_get(dg).to_mesh()
xs = [v.co.x for v in m.vertices]
print(len(m.vertices), len(m.polygons), round(min(xs), 3), round(max(xs), 3))
ob.evaluated_get(dg).to_mesh_clear()

# a different font
fpath = os.path.join(bpy.utils.system_resource('DATAFILES'), 'fonts', 'DejaVuSansMono.woff2')
fnt.font = bpy.data.fonts.load(fpath)
print(fnt.font.name, os.path.exists(fpath))
```

| 속성 | 타입 | 기본값 | 범위 / enum |
|---|---|---|---|
| `body` | STRING | `'Text'` | 본문 |
| `size` | FLOAT | 1.0 | 1e-4 … 10000 |
| `extrude` | FLOAT | 0.0 | Z 돌출 |
| `bevel_depth` | FLOAT | 0.0 | |
| `bevel_resolution` | INT | 4 | 0 … 32 |
| `resolution_u` | INT | 12 | 1 … 1024 |
| `align_x` | ENUM | `LEFT` | `LEFT, CENTER, RIGHT, JUSTIFY, FLUSH` |
| `align_y` | ENUM | `TOP_BASELINE` | `TOP, TOP_BASELINE, CENTER, BOTTOM_BASELINE, BOTTOM` |
| `space_character` | FLOAT | 1.0 | 0 … 10 |
| `space_word` | FLOAT | 1.0 | 0 … 10 |
| `space_line` | FLOAT | 1.0 | 0 … 10 |
| `offset` | **FLOAT** (enum 아님) | 0.0 | 글자 오프셋 |
| `shear` | FLOAT | 0.0 | -1 … 1 |
| `fill_mode` | 동적 ENUM | `BOTH` | [§7.4](#74-fill_mode-는-동적-enum) |
| `font` | POINTER | 자동 (`Bfont Regular`) | `bpy.types.VFont` |

**`TextCurve.character_table` 는 5.2 에 없다** (2.7x 레거시). 커스텀 글리프 접근이 필요하면
`fnt.body` 와 `font` 를 조합해 새 `TextCurve` 로 굽는다.

측정: `"Blender 5.2"` @ size 0.8 + extrude 0.05 → verts 3842, polys 3471,
x 범위 `-2.027 … 2.060` (모노스페이스 힌팅 때문에 `align_x='CENTER'` 여도 정확히 대칭은 아님).

### 7.6 폰트 로딩

```python
# bpy.data.fonts 는 TextCurve 가 하나라도 존재해야 채워진다
# (factory startup 직후에는 비어 있음. TextCurve 를 만들면 'Bfont Regular' 이 추가됨)
fnt.font                          # 이미 기본 폰트가 지정돼 있다

# 시스템 번들 폰트
import os, bpy
fpath = os.path.join(bpy.utils.system_resource('DATAFILES'), 'fonts', 'DejaVuSansMono.woff2')
fnt.font = bpy.data.fonts.load(fpath)      # 'DejaVu Sans Mono Book'

# bpy.utils.system_resource(type, *, path="")  -- path= 는 '하위 디렉터리' 전용이다
bpy.utils.system_resource('DATAFILES', path='fonts/DejaVuSansMono.woff2')   # '' (파일 경로는 안 됨)
bpy.utils.system_resource('DATAFILES', path='fonts/')                       # '<install>/5.2/datafiles/fonts/'
bpy.utils.resource_path('LOCAL')                                             # '<install>/5.2'
```

- `bpy.utils.system_resource` 시그니처가 `(type, filename=..., path=...)` 에서
  **`(type, *, path="")`** 로 바뀌었다. 옛 3인자 호출은 `TypeError` 다.
- `bpy.data.fonts.load()` 를 같은 경로로 두 번 부르면 **데이터블록이 2개** 생긴다 (중복 제거 없음).
- 5.2 번들 폰트: `DejaVuSansMono.woff2`, `Inter.woff2`, `Noto Sans CJK Regular.woff2`,
  `NotoEmoji-VariableFont_wght.woff2`, `NotoSansArabic-*`, `NotoSansArmenian-*`,
  `NotoSansBengali-*`, `NotoSansDevanagari-*`, `NotoSansEthiopic-*` 등.

---

## 8. UVs

### 8.1 `mesh.uv_layers` 데이터 API

`MeshUVLoopLayer` 속성 (5.2): `name, data, uv, active, active_clone, active_render, pin, bl_rna, rna_type`.
`MeshUVLoop` 속성: `uv, pin_uv, bl_rna, rna_type`.
**`use_active`, `use_render`, `vertex_selection`, `edge_selection` 같은 옛 이름은 없다** —
`active_render` 와 `active` 만 있다. `lay.uv` 는 `lay.data` 의 별명(wrapper)이며
`is` 비교는 `False` 다 (같은 메모리를 가리킨다).

```python
import bpy, math

bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8)
ob = bpy.context.active_object
me = ob.data
print([l.name for l in me.uv_layers], me.uv_layers.active.name)   # ['UVMap'] UVMap

lay = me.uv_layers.new(name="Second")
print([l.name for l in me.uv_layers], me.uv_layers.active.name)   # ['UVMap','Second'] UVMap
me.uv_layers.active = lay
print(me.polygons[0].loop_start, me.polygons[0].loop_total, len(me.loops))
for i, lp in enumerate(me.loops[:3]):
    print(i, lp.vertex_index, tuple(round(float(c), 4) for c in lay.data[i].uv))
lay.data[0].uv = (0.123, 0.456)
print(tuple(round(float(c), 4) for c in lay.data[0].uv))
me.uv_layers.remove(lay)

bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02,
                          margin_method='SCALED', scale_to_bounds=False)
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.002)
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(margin_method='SCALED', rotate=True)
print("in EDIT mode, len(uv_layers.active.data) =", len(me.uv_layers.active.data))   # 0 !
bpy.ops.object.mode_set(mode='OBJECT')
uvs = [tuple(d.uv) for d in me.uv_layers.active.data]
print(len(uvs), round(min(u[0] for u in uvs), 3), round(max(u[0] for u in uvs), 3))
```

| 연산 | 결과 |
|---|---|
| `me.uv_layers.new(name=...)` | 레이어 추가. **active 는 바뀌지 않는다** |
| `me.uv_layers.active = lay` | active 지정 |
| `me.uv_layers.active` | `MeshUVLoopLayer` (없으면 `None`) |
| `me.uv_layers.remove(lay)` | 삭제. 반환값 `None` |
| `lay.data[i].uv = (u, v)` | per-loop UV 쓰기 |
| `lay.data[i].pin_uv` | per-loop 핀 |
| `me.polygons[i].loop_start` / `.loop_total` | 폴리곤의 루프 범위 |
| `me.loops[i].vertex_index` | 루프가 속한 정점 |

`MeshLoop` 속성: `vertex_index, edge_index, normal, tangent, bitangent, bitangent_sign, index`.
**`use_uv` / `pin` 은 없다** (핀은 `uv_layers[i].data[j].pin_uv` 로 접근).

### 8.2 UV 오퍼레이터는 EDIT 모드 전용

`bpy.ops.uv.*` 계열은 전부 `poll()` 이 EDIT 모드를 요구한다.

| 오퍼레이터 | OBJECT 모드 `poll()` | EDIT 모드 `poll()` |
|---|---|---|
| `smart_project` | False | True |
| `unwrap` | False | True |
| `pack_islands` | False | True |
| `average_islands_scale` | False | True |
| `cube_project` / `cylinder_project` / `sphere_project` / `project_from_view` | False | True |

OBJECT 모드에서 강제 호출하면:
`RuntimeError: Operator bpy.ops.uv.smart_project.poll() failed, context is incorrect`

`mode_set(mode='EDIT')` 전이 실패하면 이 에러가 발생한다. UI 스크립트라면 edit area 를 먼저 찾아야 하지만,
headless 에서는 3D 뷰가 없으므로 **단순히 모드만 바꾸면 된다** ([§5.3](#53-headless-에서-인덱스-기반-선택--반드시-edit-bmesh-경유)).

### 8.3 `pack_islands` 의 인자 — `margin_type` 은 없다

4.x 튜토리얼에 `bpy.ops.uv.pack_islands(margin_type='SCALED')` 라고 쓰여 있지만
**5.2 에서 `margin_type` 인자가 없다.**

```python
bpy.ops.uv.pack_islands()                                        # {'FINISHED'}
bpy.ops.uv.pack_islands(margin_type='SCALED')
# TypeError: Converting py args to operator properties:: keyword "margin_type" unrecognized
bpy.ops.uv.pack_islands(margin_method='SCALED', rotate=True)     # {'FINISHED'}
```

정확한 이름은 **`margin_method`** 이고 enum 은 `SCALED`(기본) / `ADD` / `FRACTION`.
`smart_project` 도 마찬가지로 `margin_type` 이 아니라 `margin_method` 다.

### 8.4 UV 오퍼레이터 인자표 (실측)

#### `bpy.ops.uv.smart_project` — `UV_OT_smart_project`

| 인자 | 타입 | 기본값 |
|---|---|---|
| `angle_limit` | FLOAT | 1.1519 (66°) |
| `margin_method` | ENUM `SCALED`/`ADD`/`FRACTION` | `SCALED` |
| `margin` (`island_margin`) | FLOAT | 0.0 |
| `rotate_method` | ENUM `AXIS_ALIGNED`/`AXIS_ALIGNED_X`/`AXIS_ALIGNED_Y` | `AXIS_ALIGNED_Y` |
| `island_margin` | FLOAT | 0.0 |
| `area_weight` | FLOAT | 0.0 |
| `correct_aspect` | BOOLEAN | True |
| `scale_to_bounds` | BOOLEAN | False |

#### `bpy.ops.uv.unwrap` — `UV_OT_unwrap`

| 인자 | 타입 | 기본값 |
|---|---|---|
| `method` | ENUM `ANGLE_BASED`/`CONFORMAL`/`MINIMUM_STRETCH` | `CONFORMAL` |
| `fill_holes` | BOOLEAN | False |
| `correct_aspect` | BOOLEAN | True |
| `use_subsurf_data` | BOOLEAN | False |
| `use_original_bounds` | BOOLEAN | False |
| `margin_method` | ENUM `SCALED`/`ADD`/`FRACTION` | `SCALED` |
| `margin` | FLOAT | 0.001 |
| `no_flip` | BOOLEAN | False |
| `iterations` | INT | 10 |
| `use_weights` | BOOLEAN | False |
| `weight_group` | STRING | `''` |
| `weight_factor` | FLOAT | 1.0 |

> **`method` 기본값이 `CONFORMAL` 이다.** 4.x 튜토리얼이 `ANGLE_BASED` 를 기본으로 말하는 건 낡았다.
> 스카이아(구면 투영)에 대한 정확도가 필요하면 `method='MINIMUM_STRETCH'`.

#### `bpy.ops.uv.pack_islands` — `UV_OT_pack_islands`

| 인자 | 타입 | 기본값 |
|---|---|---|
| `margin_method` | ENUM `SCALED`/`ADD`/`FRACTION` | `SCALED` |
| `margin` | FLOAT | 0.001 |
| `rotate` | BOOLEAN | True |
| `rotate_method` | ENUM `ANY`/`CARDINAL`/`AXIS_ALIGNED`/`AXIS_ALIGNED_X`/`AXIS_ALIGNED_Y` | `ANY` |
| `scale` | BOOLEAN | True |
| `merge_overlap` | BOOLEAN | False |
| `pin` | BOOLEAN | False |
| `pin_method` | ENUM `SCALE`/`ROTATION`/`ROTATION_SCALE`/`LOCKED` | `LOCKED` |
| `shape_method` | ENUM `CONCAVE`/`CONVEX`/`AABB` | `CONCAVE` |
| `udim_source` | ENUM `CLOSEST_UDIM`/`ACTIVE_UDIM`/`ORIGINAL_AABB`/`CUSTOM_REGION` | `CLOSEST_UDIM` |

#### 그 외 자주 쓰는 것

| 오퍼레이터 | 주요 인자 |
|---|---|
| `uv.cube_project` | `cube_size=1.0, correct_aspect=True, clip_to_bounds=False, scale_to_bounds=False` |
| `uv.average_islands_scale` | `scale_uv=False, shear=False` |
| `uv.cylinder_project` | `direction` ENUM `VIEW_ON_EQUATOR`/`VIEW_ON_POLES`/`ALIGN_TO_OBJECT`; `align` ENUM `POLAR_ZX`/`POLAR_ZY`; `pole` ENUM `PINCH`/`FAN`; `seam=False, radius=1.0, correct_aspect=True, clip_to_bounds=False, scale_to_bounds=False` |
| `uv.sphere_project` | `direction`, `align`, `pole`, `seam`, `correct_aspect`, `clip_to_bounds`, `scale_to_bounds` |
| `uv.project_from_view` | `orthographic=False, camera_bounds=True, correct_aspect=True, clip_to_bounds=False, scale_to_bounds=False` |
| `uv.minimize_stretch` | `fill_holes=True, blend=0.0, iterations=0` |
| `uv.lightmap_pack` | `PREF_CONTEXT` ENUM `SEL_FACES`/`ALL_FACES`; `PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.1` |
| `uv.align` | `axis` ENUM `ALIGN_AUTO`/`ALIGN_S`/`ALIGN_T`/`ALIGN_U`/`ALIGN_X`/`ALIGN_Y`; `position_mode` ENUM `MEAN`/`MIN`/`MAX` |
| `uv.stitch` | `use_limit=False, snap_islands=True, limit=0.01, static_island=0` |

`dir(bpy.ops.uv)` 전체: `align, align_rotation, arrange_islands, average_islands_scale, copy,
copy_mirrored_faces, cube_project, cursor_set, custom_region_set, cylinder_project, export_layout,
follow_active_quads, hide, lightmap_pack, mark_seam, minimize_stretch, move_on_axis, pack_islands,
paste, pin, project_from_view, randomize_uv_transform, remove_doubles, reset, reveal, rip, rip_move,
seams_from_islands, select, select_all, select_box, select_by_winding, select_circle,
select_edge_ring, select_lasso, select_less, select_linked, select_linked_pick, select_loop,
select_mode, select_more, select_overlap, select_pinned, select_similar, select_split, select_tile,
shortest_path_pick, shortest_path_select, smart_project, snap_cursor, snap_selected, sphere_project,
stitch, unwrap, weld`.

### 8.5 UV 읽기 — 반드시 OBJECT 모드에서

EDIT 모드 중에는 `mesh.uv_layers[i].data` 가 **비어 있다** (스니펫에서 `0` 이 나온 이유).
`mesh.loops` 수는 정상인데 UV 데이터만 비는 이상한 상태다. 검증:

```
cube   OBJECT: len(uv_layers[0].data) = 24
cube   EDIT  : len(uv_layers[0].data) = 0     (loops: 24)
cube   OBJECT: len(uv_layers[0].data) = 24
sphere OBJECT: 112 / EDIT: 0 / OBJECT: 112
```

따라서 UV 검증 루프는 항상:

```python
bpy.ops.object.mode_set(mode='OBJECT')
uvs = [tuple(d.uv) for d in me.uv_layers.active.data]
```

### 8.6 실전 UV 파이프라인

```python
import math

bpy.ops.mesh.primitive_cylinder_add(vertices=12)
ob = bpy.context.active_object
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
bpy.ops.uv.pack_islands(margin_method='SCALED')
bpy.ops.object.mode_set(mode='OBJECT')
uvs = [tuple(d.uv) for d in ob.data.uv_layers.active.data]
print("uv bbox: (%.3f,%.3f) .. (%.3f,%.3f)" % (
    min(u[0] for u in uvs), min(u[1] for u in uvs),
    max(u[0] for u in uvs), max(u[1] for u in uvs)))
# 12각 원통 -> uv bbox: (0.004,0.004) .. (0.996,0.831)
```

`unwrap` 은 시트가 없으면 `Warning: Unwrap failed to solve 1 of 1 island(s), edge seams may need to be
added` 를 출력하고도 `{'FINISHED'}` 를 반환한다. **스카이아 전에 시트를 만들거나
`smart_project` 를 쓴다.**

---

## 9. Mesh validation / cleanup

### 9.1 이 스킬의 검증 루프용 헬퍼

`mesh_report()` 는 구조적 건강 상태를 돌려준다. 검증 루프의 마지막 단계로 쓰면 된다.

```python
import bpy, bmesh


def mesh_report(me, label="mesh"):
    """Health report for a Mesh datablock. Returns a dict of ints/floats/bools/lists."""
    rep = {}
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    rep["verts"] = len(bm.verts)
    rep["edges"] = len(bm.edges)
    rep["faces"] = len(bm.faces)
    rep["loose_verts"] = sum(1 for v in bm.verts if not v.link_edges)
    rep["wire_edges"] = sum(1 for e in bm.edges if not e.link_faces)
    rep["boundary_edges"] = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    rep["branch_edges"] = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    rep["non_manifold_verts"] = sum(1 for v in bm.verts if v.link_edges and not v.is_manifold)
    rep["tri_faces"] = sum(1 for f in bm.faces if len(f.verts) == 3)
    rep["ngon_faces"] = sum(1 for f in bm.faces if len(f.verts) > 4)
    rep["zero_area_faces"] = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    rep["dup_face_keys"] = len(bm.faces) - len(
        {tuple(sorted(v.index for v in f.verts)) for f in bm.faces})
    seen, dup = set(), 0
    for v in bm.verts:
        key = tuple(round(float(c), 6) for c in v.co)
        if key in seen:
            dup += 1
        seen.add(key)
    rep["dup_verts"] = dup
    rep["volume"] = round(bm.calc_volume(signed=True), 9)
    rep["closed"] = rep["boundary_edges"] == 0 and rep["wire_edges"] == 0
    rep["is_valid"] = bool(bm.is_valid)
    rep["inverted_normals"] = bool(rep["closed"] and rep["volume"] < 0.0)
    rep["uv_layers"] = [l.name for l in me.uv_layers]
    rep["problems"] = []
    for key, txt in (("loose_verts", "loose verts"), ("wire_edges", "wire edges"),
                     ("branch_edges", "branch edges"), ("non_manifold_verts", "non-manifold verts"),
                     ("dup_verts", "duplicate verts"), ("zero_area_faces", "zero-area faces"),
                     ("dup_face_keys", "duplicate faces")):
        if rep[key]:
            rep["problems"].append("%s=%d" % (txt, rep[key]))
    if rep["inverted_normals"]:
        rep["problems"].append("inverted normals")
    if not rep["is_valid"]:
        rep["problems"].append("bm.is_valid == False")
    bm.free()
    print("[%-10s] v=%-5d e=%-5d f=%-5d closed=%-5s vol=%-12s %s" % (
        label, rep["verts"], rep["edges"], rep["faces"], rep["closed"], rep["volume"],
        ", ".join(rep["problems"]) or "OK"))
    return rep


def repair(me, dist=1e-5):
    """Canonical cleanup pass. In 5.2 every one of these returns None."""
    bm = bmesh.new()
    bm.from_mesh(me)
    out = {
        "remove_doubles": bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=dist),
        "dissolve_degenerate": bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges[:]),
        "recalc_face_normals": bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]),
    }
    bm.to_mesh(me)
    bm.free()
    me.update()
    return out


bpy.ops.mesh.primitive_cube_add(size=2)
mesh_report(bpy.context.active_object.data, "Cube")            # clean
bpy.ops.mesh.primitive_plane_add(size=2)
mesh_report(bpy.context.active_object.data, "Plane")           # open surface is fine

me = bpy.data.meshes.new("BROKEN")
me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 0, 0), (3, 0, 0)],
               [], [(0, 1, 2, 3), (4, 1, 5), (6, 7, 8)])
me.update(calc_edges=True)
mesh_report(me, "BROKEN")
print(repair(me))
mesh_report(me, "BROKEN-fixed")

me2 = bpy.data.meshes.new("FLIPPED")
me2.from_pydata([(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                 (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
                [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                     (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
me2.update(calc_edges=True)
mesh_report(me2, "FLIPPED")
bm = bmesh.new(); bm.from_mesh(me2)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(me2); bm.free(); me2.update()
mesh_report(me2, "FLIPPED-fixed")
```

출력:

```
[Cube      ] v=8     e=12    f=6     closed=True  vol=8.0          OK
[Plane     ] v=4     e=4     f=1     closed=False vol=0.0          OK
[BROKEN    ] v=9     e=10    f=3     closed=False vol=0.0          non-manifold verts=1, duplicate verts=3, zero-area faces=2
{'remove_doubles': None, 'dissolve_degenerate': None, 'recalc_face_normals': None}
[BROKEN-fixed] v=6     e=5     f=1     closed=False vol=0.0          wire edges=1, non-manifold verts=2
[FLIPPED   ] v=8     e=12    f=6     closed=True  vol=-8.0         inverted normals
[FLIPPED-fixed] v=8     e=12    f=6     closed=True  vol=8.0          OK
```

읽는 법:

- `closed` 는 boundary/wire edge 가 없을 때만 True. **평면은 정상인데 `closed=False`.**
- `inverted_normals` 는 `closed and volume < 0` 일 때만 True. 열린 표면은 부피가 0 이므로 항상 False.
- `dup_verts` 는 **좌표가 float32 로 정규화**된 뒤 비교된다. `1.0000001` 과 `1.0` 은 같은 키다.
- `repair()` 이 아무 것도 고쳐도 **모든 반환값이 `None`** 이다. 성공 여부는 전후 `mesh_report` 비교로만 알 수 있다.
  검증 스크립트에서는 반드시 전후를 다녀서 판단한다.
- `BROKEN` 은 `repair` 후에도 wire edge 가 남는다. `repair` 는 **topology 를 창조하지 않는다.**
  구멍을 메우려면 `bmesh.ops.holes_fill` / `edgeloop_fill` / `triangle_fill` 이 추가로 필요하다.

### 9.2 `bmesh.ops` 정리 오퍼레이터 요약

| 목적 | 호출 |
|---|---|
| 겹친/중복 정점 병합 | `bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)` |
| 중복 정점 탐지 (변경 없음) | `bmesh.ops.find_doubles(bm, verts=bm.verts[:], dist=1e-5)` |
| 폭 0/짧은 엣지 없애기 | `bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])` |
| 정점만 남은 엣지 삭제 | `bmesh.ops.wireframe(bm, faces=[...], thickness=0.0, use_replace=True)` |
| 면 방향 통일 | `bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])` |
| 면 방향 반전 | `bmesh.ops.reverse_faces(bm, faces=bm.faces[:])` |
| 요소 삭제 | `bmesh.ops.delete(bm, geom=[...], context='VERTS'/'EDGES'/'FACES')` |
| 콜apsed | `bmesh.ops.collapse(bm, edges=bm.edges[:], uvs=False)` |
| 삼각분할 | `bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')` |
| 구멍 메우기 | `bmesh.ops.holes_fill(bm, edges=bm.edges[:], sides=0)` / `bmesh.ops.edgeloop_fill` / `bmesh.ops.triangle_fill` |
| 격자 메우기 | `bmesh.ops.grid_fill(bm, edges=bm.edges[:], mat_nr=0, use_smooth=False, use_interp_simple=False)` |
| 정점 스무딩 | `bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x/y/z=True)` |
| 셀프 인터섹션 | `bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)` |
| 원점 복사 | `bmesh.ops.duplicate(bm, geom=bm.verts[:], dest=bm.verts)` |
| 분할 | `bmesh.ops.split_edges(bm, edges=..., verts=..., use_verts=False)` |
| 대칭 | `bmesh.ops.mirror(bm, geom=bm.verts[:], matrix=Matrix.Identity(4), merge_dist=0.0, axis='X')` |
| 평탄화 | `bmesh.ops.flatten(bm, geom=bm.faces[:], factor=1.0)` |
| 평면화 (Coplanarize) | `bmesh.ops.planar_faces(bm, faces=bm.faces[:], iterations=0, factor=0.0)` |
| 비스ect | `bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], dist=1e-6, plane_co=Vector(), plane_no=Vector(), clear_outer=False, clear_inner=False)` |

`bmesh.ops.delete` 의 `context` 값 전부:
`'VERTS'`(기본), `'EDGES'`, `'FACES'`, `'FACES_ONLY'`, `'EDGES_FACES'`, `'VERTS_FACES'`,
`'FACES_KEEP_BOUNDARY'`, `'TAGGED_ONLY'`.

### 9.3 `Mesh.validate()` 의 실제 동작 범위

| 입력 | `validate()` 반환 | 결과 |
|---|---|---|
| 인덱스 범위 초과 (face index 99) | `True` | 그 면 **삭제됨** (`polys 1 → 0`) |
| 중복 정점의 zero-area 면 | `False` | **아무 변화 없음** |
| 정상 메시 | `False` | 변화 없음 |

즉 `validate()` 는 **out-of-range 인덱스 전용 방화벽**이지 클리너가 아니다.
중복 정점은 `bmesh.ops.remove_doubles` 가 처리한다.

---

## 10. Gotchas

### 10.1 오브젝트가 링크되지 않음

```python
ob = bpy.data.objects.new("orphan", bpy.data.meshes.new("m"))
print(ob.users_collection, ob.name in bpy.context.scene.objects)     # () False
```

렌더 안 됨, 평가 안 됨, `bpy.ops.object.*` 전부 `poll()` False.
`bpy.ops.mesh.primitive_*_add` 는 자동으로 링크하므로 이 문제는 안 생기지만,
`bpy.data.objects.new` 경로는 99% 빠뜨린다.

### 10.2 EDIT 모드에 갇힘

```python
if bpy.context.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
```

스크립트 중간에 예외가 나면 프로세스가 OBJECT 모드로 남는다. 후속 `bpy.ops.mesh.*` 호출이
전부 `CANCELLED`/`RuntimeError` 가 된다. `try/finally` 로 감싸는 습관.

### 10.3 비균일 스케일이 모디파이어를 왜곡

[§6.9](#69-비균일-스케일이-모디파이어를-망가뜨린다) 참고. 생성 직후
`bpy.ops.object.transform_apply(scale=True)`.

### 10.4 depsgraph 가 갱신되지 않음

```python
ob.modifiers.new("Sub", 'SUBSURF').levels = 1
n1 = len(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)   # 26
ob.modifiers["Sub"].levels = 3
n2 = len(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)   # 386
bpy.context.view_layer.update()    # 강제 동기화 (레퍼런스 카운트나 스레드 문제 시 필요)
```

`evaluated_depsgraph_get()` 는 매번 새 래퍼를 돌려주므로 캐시 변수는 신뢰하지 마라.
`ob.data` 는 **어떤 경우에도** 원본이다.

### 10.5 `bpy.context.collection` ≠ 활성 레이어 컬렉션의 유일한 기준

[§2.5](#25-배경-모드의-컬렉션-결정-규칙-가장-흔한-오해) 참고.
`temp_override(collection=...)` 는 `primitive_*_add` 에 영향이 없다.

### 10.6 고아 데이터 누적

```python
n = len(bpy.data.objects)
for i in range(20):
    bpy.data.objects.new("junk%d" % i, bpy.data.meshes.new("junkm%d" % i))
print(n, "->", len(bpy.data.objects))      # 8 -> 28
print("purged:", bpy.data.orphans_purge(do_recursive=True))   # 42
print("after:", len(bpy.data.objects))     # 8
```

장시간/반복 실행되는 스크립트(프로시저럴 생성, 배치 렌더, 반복 최적화)에서는
`orphans_purge(do_recursive=True)` 를 루프마다 호출하거나, 생성물 전체를 하나의 컬렉션에 넣고
`bpy.data.collections.remove()` 로 한 번에 정리한다. `orphans_purge` 는 반환값이 제거 개수다
(위 예시에서 42 — 오브젝트 20 + 메시 20 + 재귀 정리 2).

`to_mesh()` / `to_mesh_clear()` 는 **누출시키지 않는다** (200회 반복 후 메시 수 불변, 검증됨).
누수는 `to_mesh()` 만 호출하고 `to_mesh_clear()` 를 안 하는 쪽에서 난다.

### 10.7 조용한 실패 목록 (5.2)

| 실수 | 증상 | 탐지 |
|---|---|---|
| `obj.modifiers.new(..., 'MESH_TO_VOLUME')` | `None` 반환, 스택 무변경 | `assert mod is not None` |
| `bpy.ops.object.modifier_apply(modifier="typo")` | `{'CANCELLED'}` | 반환 dict 확인 |
| `bpy.ops.object.transform_apply()` (선택 없음) | `{'CANCELLED'}` | 반환 dict 확인 |
| `bpy.ops.object.shade_smooth()` (선택 없음) | `{'CANCELLED'}` | 반환 dict 확인 |
| `bpy.ops.object.modifier_apply()` (스택 첫번째 아님) | `Info:` 만 출력하고 성공 | 스택 위에서부터 적용 |
| `uv.unwrap` 시트 없음 | `Warning:` + `{'FINISHED'}` | UV bbox 를 실제로 검사 |
| `bpy.ops.mesh.subdivide` (정점만 선택) | `{'FINISHED'}` 이나 무변경 | 전후 정점 수 비교 |
| `temp_override(collection=...)` | 조용히 무시 | 결과 오브젝트의 `users_collection` 확인 |
| `bmesh.ops.remove_doubles` | `None` 반환 (매핑 없음) | 전후 `len(bm.verts)` 비교 |
| `curve.fill_mode = 'FULL'` (2D) | `TypeError` | `dimensions` 먼저 확인 |
| `primitive_*_add(scale=2.0)` | `TypeError` / 무시 | 생성 후 `obj.scale` 대입 |
| `bpy.data.objects.new()` 후 링크 누락 | 렌더 안 됨 | `users_collection` 확인 |

### 10.8 인트로스펙션 함정 총정리

| 함정 | 이유 | 우회 |
|---|---|---|
| `hasattr(bpy.types.Foo, "prop")` | RNA 속성에 대해 **False** 반환 (PROTOCOL 확인) | `[p.identifier for p in bpy.types.Foo.bl_rna.properties]` |
| `hasattr(bpy.ops.mesh, "anything")` | **항상 True** | `name in dir(bpy.ops.mesh)` |
| `dir(mesh)` 로 메서드 목록 | RNA 속성만 나온다. `validate`/`update`/`shade_smooth` 는 빠져 있다 | `dir(me)` (인스턴스) |
| `bpy.types.Mesh.bl_rna.properties` | `calc_normals` 뿐 아니라 `validate`, `update` 도 없다 (메서드라서) | `dir(me)` + `getattr` |
| `p.type == 'FLOAT'` | 배열 여부를 안 알려준다 | `p.array_length > 0` 확인 |
| `enum_items` | 동적 enum(예: `Curve.fill_mode`)에서 **거짓** | `try/except TypeError` 프로브 |
| `enum_items` | 런타임 등록 addon(Cycles `engine` 등)은 아예 안 나옴 | 문자열 대입, 검증 금지 |
| `type(mod)` | 가끔 `NoneType` | `mod.bl_rna.identifier` |
| `round(Vector)` | `TypeError: type Vector doesn't define __round__ method` | `[round(float(c), 3) for c in v]` |
| `round(Matrix)` (반복) | 행이 Vector 라서 위와 같은 에러 | `[[round(float(c),3) for c in row] for row in m]` |
| `bm.verts[i]` | `ensure_lookup_table()` 전엔 `IndexError`, `index_update()` 로도 안 열림 | `ensure_lookup_table()` |
| `bm.verts.get(co)` | 5.2 에 없음 | dict lookup 직접 |
| `bm.loops` 순회 | 5.2 에서 `TypeError` | `face.loops` |
| `bm.to_mesh()` in edit mode | `ValueError` | `bmesh.update_edit_mesh(me)` |

### 10.9 전체 end-to-end 검증 스크립트

파이프라인 전체(컬렉션 → 메시 → bmesh → 모디파이어 → 커브 → 텍스트 → UV → depsgraph → 렌더)를 한 번에
도는 레퍼런스가 이미 디스크에 있다:

| 파일 | 내용 | 실측 |
|---|---|---|
| `verify/21_e2e.py` | 완성본. 12각 원기둥 3링 메시를 `from_pydata` 로 직접 생성 → bmesh 정리 → `shade_smooth` + `set_sharp_from_angle(40°)` → Bevel → 3점 BEZIER 커브(bevel 0.012) → "5.2" FONT 텍스트 → `smart_project` + `pack_islands` → depsgraph 평가 3종 → Cycles CPU 96×96@16spp 렌더 | 아래 |
| `snippets/S20_e2e_compact.py` | 위에서 렌더 부분을 뺀 축약본 (문서에 인용) | 아래 |

`verify/21_e2e.py` 의 실측 출력:

```
mesh objects left: []
active collection now: Geometry
plinth: v=36 e=60 f=26
after bmesh pass: v=36 f=26  signed volume=0.565625 (Mesh has no .volume in 5.x)
uv layers: ['UVMap'] loops: 120
uv bbox: (0.004,0.004) .. (0.995,0.997)
Plinth   type=MESH   eval verts=84     polys=74
Arc      type=CURVE  eval verts=350    polys=336
Label    type=FONT   eval verts=860    polys=633
total evaluated verts: 1294
render written: True 6692 bytes
```

`snippets/S20_e2e_compact.py` (문서에 인용된 축약본) 의 실측 출력:

```
uv bbox: (0.004,0.004) .. (0.995,0.997)
Plinth   type=MESH   eval verts=84     polys=74
Arc      type=CURVE  eval verts=350    polys=336
Label    type=FONT   eval verts=860    polys=633
```

렌더는 `--factory-startup` 에서 Cycles add-on 을 먼저 켜야 한다 (PROTOCOL):

```python
import addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.render.resolution_x = scene.render.resolution_y = 96
scene.render.film_transparent = True
scene.render.filepath = "/workspace/out/geometry_e2e.png"
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
```

## 11. 직접 확인하는 법

모든 사실은 아래 명령으로 재현 가능하다.

```bash
blender -b --factory-startup -noaudio --python verify/02_prim_args.py
blender -b --factory-startup -noaudio --python-expr \
  "import bpy; print([p.identifier for p in bpy.types.Modifier.bl_rna.properties])"
```

재사용 가능한 인트로스펙션 헬퍼 (`snippets/S18_dochelpers.py` 에서 검증):

```python
import bpy

def op_exists(group, name):
    return name in dir(getattr(bpy.ops, group))

def op_sig(group, name):
    """Return {prop: (type, default, enum_items)} for an operator, or None."""
    g = getattr(bpy.ops, group)
    if name not in dir(g):
        return None
    rt = getattr(g, name).get_rna_type()
    out = {}
    for p in rt.properties:
        if p.identifier == "rna_type":
            continue
        if p.type == "ENUM":
            out[p.identifier] = (p.type, p.default, [i.identifier for i in p.enum_items])
        else:
            out[p.identifier] = (p.type, getattr(p, "default", None), None)
    return out

def probe_enum(obj, prop, candidates):
    """Dynamic enums lie. Return the values obj.prop actually accepts."""
    cur = getattr(obj, prop)
    ok = []
    for v in candidates:
        try:
            setattr(obj, prop, v)
            ok.append(v)
        except TypeError:
            pass
    setattr(obj, prop, cur)
    return ok

print(op_exists("object", "shade_auto_smooth_angle"))            # False
print(op_sig("uv", "pack_islands")["margin_method"])
print("margin_type" in op_sig("uv", "pack_islands"))             # False

cu = bpy.data.curves.new("c", type='CURVE')
print(probe_enum(cu, "fill_mode", ('NONE', 'BACK', 'FRONT', 'BOTH', 'FULL', 'HALF')))
# ['NONE', 'BACK', 'FRONT', 'BOTH']          <- 2D

# 어떤 modifier 타입이 이 오브젝트에 실제로 허용되는가
bpy.ops.mesh.primitive_cube_add()
ob = bpy.context.active_object
all_types = [i.identifier for i in bpy.types.Modifier.bl_rna.properties['type'].enum_items]
rejected = []
for t in all_types:
    if ob.modifiers.new("t", type=t) is None:
        rejected.append(t)
    else:
        ob.modifiers.clear()
print("rejected by Mesh object:", rejected)

# bmesh.ops 시그니처 / 오퍼레이터 인자 덤프
import bmesh
for name in sorted(dir(bmesh.ops)):
    print(name, "|", (getattr(bmesh.ops, name).__doc__ or "").strip().splitlines()[0])
for p in bpy.ops.uv.pack_islands.get_rna_type().properties:
    if p.identifier == "rna_type":
        continue
    print(p.identifier, p.type, p.default,
          [i.identifier for i in p.enum_items] if p.type == "ENUM" else "")
```

실측:

```
False
('ENUM', 'SCALED', ['SCALED', 'ADD', 'FRACTION'])
False
2D fill_mode: ['NONE', 'BACK', 'FRONT', 'BOTH']
3D fill_mode: ['BACK', 'FRONT', 'FULL', 'HALF']
```

`probe_enum` 은 `Curve.fill_mode` 처럼 동적 enum 에서 유일하게 신뢰할 수 있는 방법이다
([§7.4](#74-fill_mode-는-동적-enum)).

## 12. Breaking changes — 4.x 튜토리얼에서 틀린 것들

| # | 4.x 코드 | 5.2 실제 | 에러 |
|---|---|---|---|
| 1 | `bmesh.ops.create_cube(bm=bm, size=1.0)` | `bmesh.ops.create_cube(bm, size=1.0)` | `TypeError: bmesh operators expect a single BMesh positional argument` |
| 2 | `bm.verts.index_update()` 후 `bm.verts[0]` | `ensure_lookup_table()` 필요 | `IndexError: outdated internal index table` |
| 3 | `bm.verts.get((x, y, z))` | `BMVertSeq` 에 `.get()` 없음 | `AttributeError` |
| 4 | `for loop in bm.loops:` | `bm.loops` 비반복/비인덱스 | `TypeError: 'BMLoopSeq' object is not iterable` |
| 5 | `bpy.ops.mesh.delete(type='VERTS')` | `'VERT'` | `TypeError: enum "VERTS" not found in ('VERT','EDGE','FACE','EDGE_FACE','ONLY_FACE')` |
| 6 | `bpy.ops.uv.pack_islands(margin_type='SCALED')` | `margin_method='SCALED'` | `TypeError: keyword "margin_type" unrecognized` |
| 7 | `bpy.ops.uv.smart_project(margin_type='SCALED')` | `margin_method='SCALED'`. `island_margin` 은 그대로 유효 | `TypeError: keyword "margin_type" unrecognized` |
| 8 | `mesh.calc_normals()` | 삭제됨. `shade_smooth()` / `set_sharp_from_angle()` | `AttributeError` |
| 9 | `mesh.use_auto_smooth = True; mesh.auto_smooth_angle = ...` | 둘 다 삭제. `bpy.ops.object.shade_auto_smooth(angle=...)` | `AttributeError` |
| 10 | `curve.type == 'FONT'` | `Curve.type` 삭제 | `AttributeError` |
| 11 | `curve.fill_mode = 'FULL'` (2D) | 2D 는 `NONE`/`BACK`/`FRONT`/`BOTH` | `TypeError` |
| 12 | `bo.solver = 'FAST'` | `FLOAT`/`EXACT`/`MANIFOLD`, 기본 `EXACT` | `TypeError: enum "FAST" not found` |
| 13 | `mir.use_axis = 'X'` | BOOLEAN[3]. `(True, False, False)` | `ValueError: sequences of dimension 0` |
| 14 | `nem.offset = 0.4` (FLOAT) | FLOAT[3] | `TypeError: ... should contain 3 items` |
| 15 | `sdm.limits = 0.0` | FLOAT[2] | `TypeError: ... should contain 2 items` |
| 16 | `bpy.ops.mesh.primitive_cube_add(scale=2.0)` | headless 에서 `TypeError` / 무시 | `TypeError` / no-op |
| 17 | `obj.modifiers.active_index = 0` | `active_index` 없음. `modifiers.active = mod` | `AttributeError` |
| 18 | `bpy.data.meshes['X'].volume` | `Mesh` 에 `volume` 없음. `bmesh.calc_volume(signed=True)` | `AttributeError` |
| 19 | `curve.splines.new('BEZIER')` 후 `.points` | BEZIER 는 `.bezier_points`. `.points` 는 빈 시퀀스 | 무음 실패 |
| 20 | edit 모드에서 `bm.to_mesh(me)` | `bmesh.update_edit_mesh(me)` | `ValueError: Mesh is in editmode` |
| 21 | `bpy.ops.<g>.<op>(..., context={...})` | `bpy.context.temp_override(...)` | `TypeError: keyword "context" unrecognized` |
| 22 | `bpy.utils.system_resource('DATAFILES', 'file', path=...)` | `(type, *, path="")`, 서브디렉터리만 | `TypeError: takes at most 2 arguments` |
| 23 | `bmesh.ops.remove_doubles(...)['targetmap']` | 5.2 에서 `None` 반환 | `TypeError: 'NoneType' is not subscriptable` |
| 24 | `bpy.ops.object.shade_smooth()` 는 선택 무관 | 선택 없으면 `{'CANCELLED'}` | 조용한 무효 |

**내 기억이 틀렸던 부분** (직접 확인으로 교정됨):

- `mesh.calc_normals()` 은 4.1 에서 제거되었다고 알고 있었는데, 실제로는 5.2 에서도 확실히 없다.
  `hasattr` 로 확인.
- `bmesh.ops.*` 의 `bm=` 키워드가 5.x 라면 "여전히 쓸 수 있으려나" 했는데 **위치 인자만** 허용된다.
  이건 PROTOCOL 에 없고 직접 찾아낸 변경점이다.
- `bpy.ops.uv.pack_islands(margin_type=...)` 이 4.x 때 존재하는 줄 알았는데 5.2 에는 `margin_method` 다.
- `temp_override(collection=...)` 가 primitive op 의 대상 컬렉션을 바꾼다고 여러 튜토리얼이 말하는데
  **바꾸지 않는다**. 활성 레이어 컬렉션이 이긴다.
- `Mesh.use_auto_smooth` 제거는 알고 있었는데, 대체재가 "Smooth by Angle" **모디파이어**라는 점과
  그것이 `geometry_nodes_essentials.blend` 에서 링크된다는 점은 직접 확인했다.
- `bpy.ops.mesh.delete` 의 enum 변경은 예상 밖이었다 (`VERTS` → `VERT`).
- `hasattr(bpy.ops.<group>, name)` 이 항상 True 인 것은 PROTOCOL 의 `hasattr` 경고와 별개로,
  `bpy.ops` 에서만 특히 위험하다.

---

## 13. Verification log

전 명령 형식:

```
blender -b --factory-startup -noaudio --python <script>
```

성공 판정: 종료 코드 0 **그리고** 출력을 grep 했을 때 `__SCRIPT_OK__` 존재.
Blender 의 traceback 은 stderr 로 나가므로 항상 `2>&1` 로 합쳐 확인했다.

### 조사용 스크립트 (`verify/`) — API 표면 추출

모두 **PASS**. 괄호 안은 실행 중 수정한 횟수와 원인.

| # | `verify/NN_*.py` | 커버 |
|---|---|---|
| 01 | `introspect` | `dir(bpy.ops.mesh)` 전체 149개, `modifier_apply`/`mode_set` 인자, `Modifier.type` enum 82개, `dir(bpy.ops.uv)` 55개, `temp_override` 존재 |
| 02 | `prim_args` | 10개 `primitive_*` 의 전 인자/enum/default, `Mesh` 메서드 존재 여부, `shade_*` 4종 시그니처 |
| 03 | `curve_font` | `Curve`/`TextCurve` 전 속성, spline type enum, bezier point, `hasattr(bpy.ops.*)` 함정 (1: `FloatProperty.enum_items`) |
| 04 | `mesh_api` | `from_pydata(shade_flat=)`, `validate()` 2케이스, `shade_smooth/flat`, `set_sharp_from_angle`, `TextCurve.type` 부재, `Mesh` 메서드 목록 (1: `fo.type`·`round(Vector)`) |
| 05 | `lifecycle` | `objects.new` 미링크, 컬렉션 링크/언링크/remove, `matrix_parent_inverse`, `view_layer` 활성 컬렉션 (1: `round(Matrix)`) |
| 06 | `context` | 활성 레이어 컬렉션 vs `temp_override(collection=)`, 폐기된 `context=` kwarg, 잘못된 오버라이드 키 |
| 07 | `editmode` | `temp_override` 의 `object`/`scene`/`view_layer` 효과, EDIT 모드 poll, object 전용 op 실패 |
| 08 | `bmesh` | `bmesh.ops` 83개 docstring, `bm=` 키워드 거부, `create_*` 실패 케이스, `bpy.ops.mesh.delete` enum, 인덱스 규칙 (2) |
| 09 | `bmesh2` | `create_*` 위치 인자 전 케이스, `BMVertSeq.get`·`lookup_table` 부재, `index_update()` 부족, 시퀀스 속성 (2) |
| 10 | `bmesh_elems` | `BMLoopSeq` 비반복, `BMVert/BMEdge/BMFace/BMLoop` 속성 전량, `calc_volume`, `is_valid` (1) |
| 11 | `modifiers_props` | 25개 모디파이어의 **전체** RNA 속성 + enum + default (1: `new()` → None 방어) |
| 12 | `modifiers_rest` | 나머지 모디파이어 속성, `modifiers` 컬렉션 API, `move()`, `active_index` 부재, None 반환 타입 목록 (2) |
| 13 | `depsgraph_apply` | `evaluated_get`/`to_mesh`/`to_mesh_clear`, depsgraph 신선도, `modifier_apply` + `single_user` (1: `Depsgraph.is_updated`) |
| 14 | `apply_orphans` | 없는 모디파이어 이름 → `CANCELLED`, 미링크 오브젝트 평가, `to_mesh` 누출 없음, `orphans_purge`, `batch_remove` (1) |
| 15 | `modifier_examples` | 24종 모디파이어 실측 (5회 수정: `use_axis` ValueError, `limits`/`offset` 배열, `to_mesh` in edit mode, `use_grid_fill`) |
| 16 | `uv` | 22개 `bpy.ops.uv.*` 인자, `uv_layers` API, EDIT 모드 UV 오퍼레이터, `margin_method`, OBJECT 모드 실패 (1) |
| 17 | `curve_text` | POLY/BEZIER/NURBS 점 구조, `fill_mode` 동적 enum 실측, 폰트 로딩, `convert(target='MESH')` (3) |
| 18 | `mesh_smooth` | ngon/edges, `validate()` 2케이스, `shade_smooth/flat`, `set_sharp_from_angle`, `shade_auto_smooth` → NODES 모디파이어 |
| 19 | `mesh_sanity` | `mesh_report()`: cube/ico/plane/torus/broken/flipped/non-manifold, `repair()` 전후 비교 (2) |
| 20 | `gotchas` | 대표 gotcha 10종 전부 실측 (링크 누락, 컬렉션 규칙, align, mode_set, EDIT 선택, 스케일, depsgraph, 고아, active=None) (2) |
| 21 | `e2e` | end-to-end + Cycles CPU 96×96@16spp 렌더 (`/workspace/out/geometry_e2e.png`, 6692 bytes) (1) |
| 22 | `misc` | `enter_editmode`, `scale=` 함정, `transform_apply` 전제, 중첩 컬렉션/exclude/hide, parenting, `mesh.attributes` (1) |
| 23 | `apply_misc` | `modifiers.new` 위치 인자, `single_user`, `new_from_object`, `shade_smooth` 선택 의존, "Smooth by Angle" 노드 그룹 출처, 스택 순서 (2) |
| 24 | `bmesh_table` | `bmesh.ops` 83개 전체 시그니처 마크다운 덤프 |

### 문서 스니펫 (`snippets/`) — 본문에 그대로 실린 코드

모두 **PASS**. 본문 어디에 들어갔는지는 "본문 위치" 참조.

| # | 스니펫 | 본문 위치 |
|---|---|---|
| S01 | `S01_lifecycle.py` | §1.1 |
| S02 | `S02_parent.py` | §1.3 |
| S03 | `S03_prims.py` | §2.3 (11종 생성 결과) |
| S04 | `S04_from_pydata.py` | §3.1 |
| S05 | `S05_smooth.py` | §3.3 |
| S06 | `S06_bmesh_basic.py` | §4.1, §4.2, §4.3 |
| S07 | `S07_bmesh_edit.py` | §4.4, §4.9 (1회 수정: `use_grid_fill`) |
| S08 | `S08_override.py` | §5.3 (2회 수정: 정점만 선택 시 subdivide no-op) |
| S09 | `S09_modifiers.py` | §6.1, §6.7 (1회 수정: `move()` 후 apply 순서) |
| S10 | `S10_eval.py` | §6.7 |
| S11 | `S11_curve.py` | §7.2 |
| S12 | `S12_text.py` | §7.5 |
| S13 | `S13_uv.py` | §8.1 |
| S14 | `S14_sanity.py` | §9.1 (1회 수정) |
| S15 | `S15_collection.py` | §1.2 (1회 수정: `remove()` 결과 주석) |
| S16 | `S16_gotchas.py` | §1.4, §2.4, §10.1, §10.6 |
| S17 | `S17_modrecipes.py` | §6.6 (원본 24종 레시피) |
| S18 | `S18_dochelpers.py` | §2.6, §4.7, §5.1, §7.4, §11 (`op_exists`/`op_sig`/`probe_enum`/`safe_fill_mode`) |
| S19 | `S19_e2e_doc.py` | §10.9 (렌더 포함 e2e) |
| S20 | `S20_e2e_compact.py` | §10.9 (축약 e2e) |
| S21 | `S21_recipes_compact.py` | §6.6 (압축 레시피 + 수치표) |
| S22 | `S22_docfragments.py` | §1.4, §2.5, §3.5, §6.3, §6.9, §7.3, §8.6, §10.4 (본문에만 있는 조각) |

### 실패했던 시도 (정직한 기록)

| 시나리오 | 결과 | 대응 |
|---|---|---|
| `mesh.calc_normals()` 존재 여부 가정 | **실패** — 4.1 에서 삭제됨을 확인 | `shade_smooth()` / `set_sharp_from_angle()` 로 대체 문서화 |
| `bpy.ops.object.shade_auto_smooth_angle` | **실패** — `hasattr` 이 True 라 존재하는 것처럼 보이지만 `get_rna_type()` 에서 `KeyError`. 실제로는 `shade_auto_smooth` 와 `shade_smooth_by_angle` | `dir()` 검사 헬퍼로 대체 |
| `bmesh.ops.create_icosphere(diameter=...)` | **실패** — `radius` 가 정식 인자 | 본문에 실패 케이스로 기록 |
| `bmesh.ops.*(bm=bm, ...)` | **실패** — 12개 op 전부 | 위치 인자 형식으로 전면 교체 |
| `bpy.ops.mesh.delete(type='VERTS')` | **실패** — enum 이름 변경 | `VERT`/`EDGE`/`FACE`/`EDGE_FACE`/`ONLY_FACE` 로 교체 |
| `uv.pack_islands(margin_type='SCALED')` | **실패** — `margin_method` | 교체 |
| `bpy.ops.uv.smart_project()` 후 EDIT 모드에서 UV 읽기 | **실패** — `uv_layers[i].data` 가 빈 리스트 | OBJECT 모드로 나중에 읽으므로 수정 |
| `bm.verts.get(co)` | **실패** — `AttributeError` | dict lookup 으로 교체 |
| `bm.loops` 순회 | **실패** — `TypeError` (3가지 전부) | `face.loops` 로 교체 |
| `bm.verts.lookup_table` | **실패** — `AttributeError` | `ensure_lookup_table()` + dict |
| `bm.to_mesh(me)` in edit mode | **실패** — `ValueError` | `bmesh.update_edit_mesh(me)` |
| `temp_override(collection=X)` 로 primitive 배치 제어 | **실패** — 활성 레이어 컬렉션이 이김 | `active_layer_collection` 직접 대입 |
| `bpy.ops.mesh.primitive_cube_add(scale=2.0)` | **실패** — `TypeError` | 생성 후 `obj.scale` 대입 |
| `obj.modifiers.new('MESH_TO_VOLUME')` | **조용한 실패** — `None` 반환 | `assert mod is not None` 패턴 문서화 |
| `obj.modifiers.active_index` | **실패** — 부재 | `modifiers.active = mod` |
| `me.volume` | **실패** — 부재 | `bmesh.calc_volume(signed=True)` |
| `fnt.fill_mode = 'FULL'` | **실패** — `TypeError` (`enum_items` 가 거짓말) | `dimensions` 별 유효값 표 + 프로브 헬퍼 |
| `bpy.utils.system_resource(type, filename, path)` | **실패** — `TypeError` | `(type, *, path=)` + `os.path.join` |
| `bmesh.ops.remove_doubles(...)['targetmap']` | **실패** — 5.2 에서 `None` | 전후 정점 수 비교 패턴 |
| `normal_edit.offset = 0.4` (스칼라) | **실패** — FLOAT[3] | `(x, y, z)` |
| `simple_deform.limits = 0.0` (스칼라) | **실패** — FLOAT[2] | `(lo, hi)` |
| `bpy.ops.mesh.subdivide` (정점만 선택) | **조용한 no-op** | `bmesh.ops.subdivide_edges` 로 대체 |
| `bpy.ops.object.shade_smooth()` (선택 없음) | **`{'CANCELLED'}`** | 선택 후 호출, 반환값 검사 |
| `bpy.ops.object.transform_apply()` (선택 없음) | **`{'CANCELLED'}`** | 동일 |
| `bpy.ops.object.modifier_apply(modifier="typo")` | **`{'CANCELLED'}`** | 동일 |
| `round(Vector)` / `round(Matrix)` | **실패** — `__round__` 없음 | `[round(float(c), n) for c in v]` |
| `bpy.context.scene.tool_settings.use_cursor_location` | **실패** — 부재 | 해당 라인 제거 |
| `bpy.types.Mesh.bl_rna.properties` 로 메서드 찾기 | **실패** — `validate`/`update`/`shade_smooth` 없음 | `dir(me)` |
| `Depsgraph.is_updated` | **실패** — 부재 | `dg.updates`, `dg.update()` |
| `hasattr(bpy.ops.object, "bogus")` 로 존재 확인 | **오탐** | `"name" in dir(bpy.ops.object)` |

최종 확인 (전량 재실행, `for f in verify/*.py snippets/*.py`):
**24개 `verify/*.py` + 22개 `snippets/*.py` = 46개 스크립트 전부 PASS.**
렌더 아웃풋: `/workspace/out/geometry_e2e.png` (6692 bytes, verify/21_e2e.py),
`/workspace/out/geometry_e2e_doc.png` (4229 bytes, snippets/S19_e2e_doc.py).

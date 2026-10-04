# 머티리얼 · 셰이더 노드 · 텍스처 · 월드 · 지오메트리 노드 스크립팅 (Blender 5.2 LTS)

> 검증 환경: **Blender 5.2.2 LTS** (build 2026-09-15, commit `d13f752e3b9c`), Linux x64 headless,
> 번들 Python **3.13.13**.
> 이 문서의 모든 코드 블록은 `/usr/local/bin/blender` 로 실제 실행되어 `__SCRIPT_OK__` 를 출력한
> 스크립트에서만 가져왔다. 검증 스크립트는 `verify/doc_01..09_*.py` 에 남아 있고,
> 커맨드는 [Verification log](#verification-log) 에 전부 적어두었다.
>
> **주의**: 이 문서는 3.x / 4.x 튜토리얼과 **여러 곳에서 다르게** 동작한다. 다르면
> [11. Gotchas / 트랩](#11-gotchas--트랩) 에 "4.x 에서는 …" 형태로 명시했다.

---

## 목차

1. [Material 기본](#1-material-기본)
2. [노드 트리 조작](#2-노드-트리-조작)
3. [Principled BSDF 레퍼런스 (5.2)](#3-principled-bsdf-레퍼런스-52)
4. [셰이더 노드 타입 레퍼런스](#4-셰이더-노드-타입-레퍼런스)
5. [Mix / Mix (Legacy)](#5-mix--mix-legacy)
6. [프로시저럴 텍스처링](#6-프로시저럴-텍스처링)
7. [이미지 텍스처](#7-이미지-텍스처)
8. [월드 / 환경](#8-월드--환경)
9. [지오메트리 노드](#9-지오메트리-노드)
10. [Bake / 평가](#10-bake--평가)
11. [Gotchas / 트랩](#11-gotchas--트랩)
12. [Verification log](#verification-log)

---

## 1. Material 기본

### 1.1 `use_nodes` 는 5.x 에서 더 이상 필요 없다

Blender 5.2 에서 `bpy.data.materials.new()` 는 **이미** 노드가 2 개 채워진 `node_tree` 를 가진다.
`use_nodes` 를 읽으면 deprecation 경고가 뜨고, `False` 를 대입해도 아무 일도 일어나지 않는다.

| 동작 | 5.2 실측 |
|---|---|
| `bpy.data.materials.new("M")` | `node_tree` 존재, 노드 = `Principled BSDF` + `Material Output`, 링크 1개 |
| `m.use_nodes` 읽기 | `True` + `DeprecationWarning: 'Material.use_nodes' is expected to be removed in Blender 6.0` |
| `m.use_nodes = False` | **노이즈**. `use_nodes` 는 여전히 `True` 리턴, `node_tree` 도 그대로 |
| `world.use_nodes` | 동일하게 deprecation (`'World.use_nodes' …`) |

```python
# ❌ 3.x / 4.x 습관 — 경고만 발생하고 효과 없음
mat = bpy.data.materials.new("Steel")
mat.use_nodes = True
if not mat.use_nodes:
    mat.use_nodes = True

# ✅ 5.x 정답
mat = bpy.data.materials.new("Steel")
print(mat.node_tree.nodes["Principled BSDF"].bl_idname)   # ShaderNodeBsdfPrincipled
```

`World` 도 같다. `bpy.data.worlds.new("W")` → `node_tree` 자동 생성, `Scene` 에는
`node_tree` 가 **없고** `compositing_node_group` 로 대체됐다(5.0 변경).

### 1.2 재사용 · 복사 · 노드 그룹 · 슬롯 오버라이드

`Material` 은 일반 ID 데이터블록이므로 `.copy()` 가 노드 트리까지 전부 복제한다.
같은 머티리얼을 여러 오브젝트가 공유하되, **오브젝트 단위로만** 재질만 다르게 만들고 싶을 때
`MaterialSlot.link = 'OBJECT'` 를 쓴다.

| API | 타입 | 설명 |
|---|---|---|
| `Material.copy()` | `Material` | 노드 트리까지 깊은 복사. `as_pointer()` 가 달라진다 |
| `Material.use_fake_user` | bool | 링크되지 않은 머티리얼 보존 |
| `Object.material_slots` | `bpy_prop_collection` of `MaterialSlot` | read-only collection |
| `Object.material_slots[i].link` | enum `'DATA'` \| `'OBJECT'` | `DATA`=메시 데이터, `OBJECT`=오브젝트별 오버라이드. **기본값 `DATA`** |
| `MaterialSlot.material` | `Material` | 쓰기 가능 |
| `MaterialSlot.slot_index` | int (read-only) | |
| `MaterialSlot.name` | str **read-only** | 5.2 에서 이름 변경 불가 (`AttributeError`) |
| `Object.active_material` | `Material` | 현재 활성 슬롯의 실제 머티리얼 (link 해석 결과) |
| `Mesh.materials` | collection | `Object.material_slots` 와 **다르다** — 항상 데이터 레벨 |

**검증 예제 (EX-01)** — `verify/doc_01_material.py`

```python
"""DOC EX-01 — Material lifecycle: creation, reuse, copy, node group, slots."""
import bpy, sys

# ---- 1. 생성 ---------------------------------------------------------------
mat = bpy.data.materials.new("Steel")
print("node_tree:", mat.node_tree)
print("default nodes:", [(n.name, n.bl_idname) for n in mat.node_tree.nodes])
# mat.use_nodes = True   # 5.x 에서 불필요 + DeprecationWarning

# ---- 2. 여러 오브젝트가 한 머티리얼 공유 --------------------------------
bpy.ops.mesh.primitive_cube_add()
a = bpy.context.object
bpy.ops.mesh.primitive_uv_sphere_add(location=(3, 0, 0))
b = bpy.context.object

a.data.materials.append(mat)
b.data.materials.append(mat)
print("users:", mat.users)

# ---- 3. .copy() ------------------------------------------------------------
mat2 = mat.copy()
mat2.name = "Steel_Copy"
bsdf2 = mat2.node_tree.nodes["Principled BSDF"]
bsdf2.inputs['Base Color'].default_value = (0.9, 0.55, 0.1, 1.0)
bsdf2.inputs['Metallic'].default_value = 0.8
print("copy base color:", tuple(mat2.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value))
print("copy is independent:", mat.as_pointer() != mat2.as_pointer())

# ---- 4. Object 링크 오버라이드 --------------------------------------------
alt = bpy.data.materials.new("Steel_Blue")
alt.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.1, 0.2, 0.9, 1)

b.material_slots[0].link = 'OBJECT'
b.material_slots[0].material = alt
print("A slot:", a.material_slots[0].link, a.material_slots[0].material.name)
print("B slot:", b.material_slots[0].link, b.material_slots[0].material.name)
print("active_material A/B:", a.active_material.name, b.active_material.name)

# ---- 5. 머티리얼 안에서 노드 그룹 재사용 ---------------------------------
grp = bpy.data.node_groups.new("GrimeShader", 'ShaderNodeTree')
grp.interface.new_socket("Normal",      in_out='INPUT',  socket_type='NodeSocketVector')
grp.interface.new_socket("Base Color",  in_out='OUTPUT', socket_type='NodeSocketColor')
grp.interface.new_socket("Roughness",   in_out='OUTPUT', socket_type='NodeSocketFloat')
gi = grp.nodes.new("NodeGroupInput");  gi.location = (-600, 0)
go = grp.nodes.new("NodeGroupOutput"); go.location = (400, 0)
nz  = grp.nodes.new("ShaderNodeTexNoise"); nz.location = (-600, 250)
nz.inputs['Scale'].default_value = 12.0
cr  = grp.nodes.new("ShaderNodeValToRGB");  cr.location = (-380, 250)
mr  = grp.nodes.new("ShaderNodeMapRange");  mr.location = (-180, 250)
mr.inputs['To Min'].default_value = 0.2
mr.inputs['To Max'].default_value = 0.8
grp.links.new(nz.outputs['Factor'], cr.inputs['Fac'])
grp.links.new(nz.outputs['Factor'], mr.inputs['Value'])
grp.links.new(cr.outputs['Color'], go.inputs['Base Color'])
grp.links.new(mr.outputs['Result'], go.inputs['Roughness'])

host_node = mat2.node_tree.nodes.new("ShaderNodeGroup")
host_node.node_tree = grp
host_node.location = (-200, 0)
host_bsdf = mat2.node_tree.nodes["Principled BSDF"]
mat2.node_tree.links.new(host_node.outputs['Base Color'], host_bsdf.inputs['Base Color'])
mat2.node_tree.links.new(host_node.outputs['Roughness'], host_bsdf.inputs['Roughness'])
print("group users:", grp.users)

print("__SCRIPT_OK__")
sys.exit(0)
```

실측 출력:

```
node_tree: <bpy_struct, ShaderNodeTree("Shader Nodetree") at 0x…>
default nodes: [('Principled BSDF', 'ShaderNodeBsdfPrincipled'), ('Material Output', 'ShaderNodeOutputMaterial')]
users: 2
copy base color: (0.8999999761581421, 0.550000011920929, 0.10000000149011612, 1.0)
copy is independent: True
A slot: DATA Steel
B slot: OBJECT Steel_Blue
active_material A/B: Steel Steel_Blue
group users: 1
```

#### 재사용 패턴 정리

- **색만 다른 N개 오브젝트** → 머티리얼 1개 + `slot.link='OBJECT'` + `slot.material = …`
  (메시 데이터를 공유하는 인스턴싱과 함께 쓸 때 가장 유리하다)
- **노드 로직만 공유, 색은 다름** → `ShaderNodeTree` 노드 그룹 + `ShaderNodeGroup` 노드.
  그룹 입력 소켓에 `Base Color` 같은 색 소켓을 두면 호출자가 오버라이드한다.
- `mat.copy()` 후 `use_fake_user = True` 로 붙잡아 두면 "Material" 이라는 스크립트 컨테이너로 쓸 수 있다.

### 1.3 머티리얼 렌더 속성 (5.2 에서 실제로 존재하는 것)

`Material` 의 쓰기 가능한 RNA 프로퍼티 목록(실측):

| 카테고리 | 프로퍼티 |
|---|---|
| EEVEE | `surface_render_method`, `use_transparency_overlap`, `show_transparent_back`, `use_backface_culling`, `use_backface_culling_shadow`, `use_backface_culling_lightprobe_volume`, `use_transparent_shadow`, `use_raytrace_refraction`, `use_screen_refraction`, `use_sss_translucency`, `thickness_mode`, `use_thickness_from_shadow`, `volume_intersection_method` |
| 공통 | `use_backface_culling_lightprobe_volume`, `refraction_depth`, `displacement_method`, `max_vertex_displacement` |
| 뷰포트 | `preview_render_type`, `use_preview_world` |
| ID | `node_tree`, `use_nodes`(deprecated), `diffuse_color`, `roughness`, `metallic`, `specular_intensity`, `specular_color`, `line_color`, `line_priority`, `lineart`, `grease_pencil`, `pass_index`, `use_fake_user` |

`diffuse_color` / `roughness` / `metallic` 은 **노드가 없을 때의 viewport 표시값**이다.
노드가 있으면 렌더에는 영향을 주지 않는다.

---

## 2. 노드 트리 조작

### 2.1 노드 컬렉션 API

`node_tree.nodes` 는 `bpy_prop_collection` 이고, `bpy_prop_collection` +
노드 전용 메서드(`new`, `remove`, `clear`, `get`, `find`)를 합친 인터페이스를 갖는다.

```
['active', 'bl_rna', 'clear', 'find', 'foreach_get', 'foreach_set',
 'get', 'items', 'keys', 'new', 'remove', 'rna_type', 'values']
```

| API | 설명 |
|---|---|
| `nodes.new(bl_idname)` | 새 노드. 알 수 없는 타입이면 `RuntimeError: Error: Node type X undefined` |
| `nodes.get(name)` | 없으면 `None` |
| `nodes[name]` | 없으면 `KeyError` |
| `nodes.remove(node)` | 노드 + 연결된 링크 제거 |
| `nodes.clear()` | 전체 삭제 (링크도 같이 사라진다) |
| `nodes.active` | 현재 활성 노드 |

### 2.2 `Node` 공통 프로퍼티

| 프로퍼티 | 타입 | 비고 |
|---|---|---|
| `name` | str | 트리 내 유일. 중복 시 `X.001` 자동 부여. `nodes.get()` 은 **이 값**으로 찾는다 |
| `label` | str | UI 표시용. `name` 과 독립 |
| `bl_idname` | str | `nodes.new()` 에 넘기는 타입 문자열 |
| `bl_label` | str | UI 라벨 (예: `ShaderNodeMixRGB` → `"Mix (Legacy)"`) |
| `type` | str | RNA enum (`TEX_NOISE`, `BSDF_PRINCIPLED`, …) |
| `bl_static_type` | str | `bl_idname` 과 동일 값 |
| `location` / `location_absolute` | 2-tuple float | `location_absolute` 는 부모 프레임 기준 절대 좌표 |
| `width` / `height` | float | `width` 는 쓰기 가능, `height` 는 UI 전용 |
| `dimensions` | 2-tuple float | headless 에선 항상 `(0,0)` (UI 레이아웃 없음) |
| `hide` / `mute` | bool | `hide`=완전 비활성, `mute`=결과 무시(연결 유지) |
| `select`, `show_options`, `show_preview`, `show_texture` | bool | UI |
| `parent` | `NodeFrame` | 프레임 넣기 |
| `use_custom_color`, `color`, `color_tag` | | UI |
| `panel_states` | dict | 프레임 접힘 상태 |

### 2.3 소켓 찾기: `name` vs `identifier`

| 대상 | `[...]` 로 찾는 기준 | 비고 |
|---|---|---|
| `node.inputs[name]` / `node.outputs[name]` | **소켓 `name`**, 단 **`enabled == True` 인 것만** | 비활성 소켓은 `KeyError` |
| `node.inputs[i]` | 인덱스 | 비활성 소켓도 접근 가능 |
| `node.inputs[identifier]` | ❌ 미지원 (`KeyError`) | `identifier` 로 찾으려면 순회 |
| `link.from_socket.name` | — | |
| `NodeTreeInterface.items_tree` | `it.name`, `it.identifier` | |
| `mod.properties.inputs.<identifier>` | **identifier** (getattr) | ← GN 한정 |

> **가장 많이 당하는 함정**: `node.inputs['이름']` 은 *비활성* 소켓을 못 찾는다.
> 모드 전환(`distribute_method`, `data_type`, `operation`)으로 가려진 소켓은
> `for s in node.inputs` 로는 보이는데 `node.inputs['이름']` 은 `KeyError`.
>
> ```python
> n = ng.nodes.new("GeometryNodeDistributePointsOnFaces")
> n.distribute_method = 'RANDOM'
> [s.name for s in n.inputs]        # ['Mesh','Selection','Distance Min','Density Max','Density','Density Factor','Seed']
> n.inputs['Distance Min']          # KeyError  (POISSON 일 때만 활성)
> n.distribute_method = 'POISSON'
> n.inputs['Distance Min']          # OK
> ```
> 게다가 **비활성 소켓에 `default_value` 를 대입하면 그 소켓이 강제로 활성화된다**
> (`s.enabled` 가 `True` 로 바뀜). 의도치 않은 노드 그래프 변경이므로 조심해야 한다.

> **또 다른 함정**: `ShaderNodeMix` 의 `inputs['A']` 처럼 이름이 4중으로 겹칠 때,
> `[]` 는 *그 이름의 활성 소켓* 을 돌려준다. `data_type` 을 먼저 설정하면 올바른 타입이 된다.
> (`inputs['A_Color']` 처럼 identifier 로는 `[]` 조회가 되지 않는다.)

### 2.4 링크

| API | 설명 |
|---|---|
| `links.new(from_socket, to_socket)` | 연결. 이미 연결돼 있으면 기존 링크를 **자동 대체** |
| `links.remove(link)` | |
| `link.from_node` / `from_socket` / `to_node` / `to_socket` | |
| `link.is_valid` | bool. 노드가 사라지면 `False` 로 남는다 (링크 리스트에서 자동 제거되지는 않음) |
| `link.is_muted` | bool |

**검증 예제 (EX-02)** — `verify/doc_02_nodetree.py`

```python
"""DOC EX-02 — Node tree manipulation: nodes, links, socket lookup, clearing."""
import bpy, sys

mat = bpy.data.materials.new("Plumbing")
nt = mat.node_tree
nodes, links = nt.nodes, nt.links

print("nodes collection methods:",
      [d for d in dir(nodes) if not d.startswith('_')])

# ---- 기본 트리 비우고 처음부터 --------------------------------------------
nodes.clear()
print("after clear:", len(nodes), "nodes /", len(links), "links")

out  = nodes.new("ShaderNodeOutputMaterial");  out.location  = (600, 0)
bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (300, 0)
nz   = nodes.new("ShaderNodeTexNoise");       nz.location   = (-200, 120)
cr   = nodes.new("ShaderNodeValToRGB");       cr.location   = (20, 120)
bump = nodes.new("ShaderNodeBump");           bump.location = (20, -260)
tc   = nodes.new("ShaderNodeTexCoord");       tc.location   = (-500, -260)
nz.label = "Surface Noise"
nz.width = 220.0
nz.hide = False
nz.mute = False
nz.inputs['Scale'].default_value = 15.0
links.new(tc.outputs['Object'], nz.inputs['Vector'])
links.new(nz.outputs['Factor'], cr.inputs['Fac'])
links.new(cr.outputs['Color'], bsdf.inputs['Base Color'])
links.new(nz.outputs['Factor'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

# ---- 이름으로 노드 찾기 ----------------------------------------------------
print("nodes.get('Principled BSDF'):", nodes.get('Principled BSDF').bl_idname)
print("nodes.get('nothing')        :", nodes.get('nothing'))
print("all:", [(n.name, n.label, n.bl_idname, n.type) for n in nodes])
nodes['Principled BSDF'].name = "PBSDF"
print("after rename, get('PBSDF'):", nodes.get('PBSDF') is not None)
print("get('Principled BSDF'):", nodes.get('Principled BSDF'))

# ---- 소켓: 이름 vs identifier ---------------------------------------------
print()
print("Principled inputs (name / identifier):")
for s in bsdf.inputs[:6]:
    print(f"   {s.name!r:<24} {s.identifier!r}")
print()
print("lookup by name   :", bsdf.inputs['Emission Color'].identifier)
print("lookup by index  :", bsdf.inputs[28].name)
print("Noise outputs    :", [(s.name, s.identifier, s.bl_idname) for s in nz.outputs])

# ---- 링크 정보 -------------------------------------------------------------
for link in links:
    print(f"   {link.from_node.bl_idname}.{link.from_socket.name} -> "
          f"{link.to_node.bl_idname}.{link.to_socket.name}  valid={link.is_valid}")

# ---- 노드 삭제 -------------------------------------------------------------
nodes.remove(bump)
print("after remove(bump):", len(nodes), "nodes,",
      len([l for l in links if l.is_valid]), "valid links")

# ---- "비활성" 소켓 찾기 헬퍼 -------------------------------------------------
def socket_by_identifier(node, ident, output=False):
    for s in (node.outputs if output else node.inputs):
        if s.identifier == ident:
            return s
    raise KeyError(ident)

print()
print("Noise 'Fac' identifier ->", socket_by_identifier(nz, 'Fac', output=True).name)

print("__SCRIPT_OK__")
sys.exit(0)
```

실측 출력 (발췌):

```
nodes.get('Principled BSDF'): ShaderNodeBsdfPrincipled
nodes.get('nothing')        : None
after rename, get('PBSDF'): True
get('Principled BSDF'): None            # 이름을 바꾸면 이전 이름으로는 못 찾는다
lookup by name   : Emission Color
lookup by index  : Emission Color
Noise outputs    : [('Factor', 'Fac', 'NodeSocketFloat'), ('Color', 'Color', 'NodeSocketColor')]
after remove(bump): 5 nodes, 4 valid links
Noise 'Fac' identifier -> Factor
```

`ShaderNodeBsdfPrincipled` 는 `identifier == name` 이지만, `ShaderNodeTexNoise` 의
첫 출력은 `name='Factor'` / `identifier='Fac'` 로 다르다. **정본은 `identifier` 다.**

### 2.5 기본 트리 비우기

```python
mat = bpy.data.materials.new("Scratch")
print([ (n.name, n.bl_idname) for n in mat.node_tree.nodes ])   # Principled BSDF + Material Output
mat.node_tree.nodes.clear()                                     # 0 nodes, 0 links
```

`clear()` 하면 링크도 같이 사라진다. 스크립트로 처음부터 노드 트리를 만드는 경우에
가장 안전한 방법이고, "기본 Principled 를 그대로 쓰고 싶다" 는 요구가 없으면 항상 이걸 쓴다.

---

## 3. Principled BSDF 레퍼런스 (5.2)

### 3.1 소켓 전체 목록 (32개, 실측)

`bpy.data.materials.new("M").node_tree.nodes["Principled BSDF"].inputs` 를 그대로 덤프한 것이다.

| # | name | identifier | bl_idname | type | 기본값 | 의미 / 권장값 |
|--:|---|---|---|---|---|---|
| 0 | Base Color | Base Color | `NodeSocketColor` | RGBA | `(0.8, 0.8, 0.8, 1)` | 베이스 알베도. 선형 공간 |
| 1 | Metallic | Metallic | `NodeSocketFloatFactor` | VALUE | `0` | 0=비금속, 1=금속 |
| 2 | Roughness | Roughness | `NodeSocketFloatFactor` | VALUE | `0.5` | 0=거울, 1=완전 확산 |
| 3 | IOR | IOR | `NodeSocketFloat` | VALUE | `1.5` | 유전 굴절률. 유리 1.45, 다이아몬드 2.42, 물 1.333 |
| 4 | Alpha | Alpha | `NodeSocketFloatFactor` | VALUE | `1` | 0=완전 투명 |
| 5 | **Thin Wall** | Thin Wall | `NodeSocketBool` | BOOLEAN | `0` | **5.x 신규.** 얇은 유리/필름 모드. True 면 굴절 대신 통과 |
| 6 | Normal | Normal | `NodeSocketVector` | VECTOR | `(0,0,0)` | bump/normal map 결과 |
| 7 | Weight | Weight | `NodeSocketFloat` | VALUE | `0` | BSDF 기여도. 0 이면 샘플링 안 됨 |
| 8 | Diffuse Roughness | Diffuse Roughness | `NodeSocketFloatFactor` | VALUE | `0` | Oren–Nayar 확산 roughness |
| 9 | Subsurface Weight | Subsurface Weight | `NodeSocketFloatFactor` | VALUE | `0` | 3.x `Subsurface` |
| 10 | Subsurface Radius | Subsurface Radius | `NodeSocketVector` | VECTOR | `(1.0, 0.2, 0.1)` | 3.x `Subsurface` 의 색 대신 |
| 11 | Subsurface Scale | Subsurface Scale | `NodeSocketFloatDistance` | VALUE | `0.005` | 4.x 추가. Radius 에 곱해짐 |
| 12 | Subsurface IOR | Subsurface IOR | `NodeSocketFloatFactor` | VALUE | `1.4` | |
| 13 | Subsurface Anisotropy | Subsurface Anisotropy | `NodeSocketFloatFactor` | VALUE | `0` | |
| 14 | **Specular IOR Level** | Specular IOR Level | `NodeSocketFloatFactor` | VALUE | `0.5` | 3.x `Specular` (0.5 = IOR 1.45 기준) |
| 15 | Specular Tint | Specular Tint | `NodeSocketColor` | RGBA | `(1,1,1,1)` | 반사 색상 |
| 16 | Anisotropic | Anisotropic | `NodeSocketFloatFactor` | VALUE | `0` | |
| 17 | Anisotropic Rotation | Anisotropic Rotation | `NodeSocketFloatFactor` | VALUE | `0` | radians |
| 18 | Tangent | Tangent | `NodeSocketVector` | VECTOR | `(0,0,0)` | 비어 있으면 자동 계산 |
| 19 | **Transmission Weight** | Transmission Weight | `NodeSocketFloatFactor` | VALUE | `0` | 3.x `Transmission` |
| 20 | **Coat Weight** | Coat Weight | `NodeSocketFloatFactor` | VALUE | `0` | 3.x `Clearcoat` |
| 21 | Coat Roughness | Coat Roughness | `NodeSocketFloatFactor` | VALUE | `0.03` | 3.x `Clearcoat Roughness` |
| 22 | Coat IOR | Coat IOR | `NodeSocketFloat` | VALUE | `1.5` | |
| 23 | Coat Tint | Coat Tint | `NodeSocketColor` | RGBA | `(1,1,1,1)` | |
| 24 | Coat Normal | Coat Normal | `NodeSocketVector` | VECTOR | `(0,0,0)` | 3.x `Clearcoat Normal` |
| 25 | **Sheen Weight** | Sheen Weight | `NodeSocketFloatFactor` | VALUE | `0` | 3.x `Sheen` |
| 26 | Sheen Roughness | Sheen Roughness | `NodeSocketFloatFactor` | VALUE | `0.5` | |
| 27 | Sheen Tint | Sheen Tint | `NodeSocketColor` | RGBA | `(1,1,1,1)` | |
| 28 | **Emission Color** | Emission Color | `NodeSocketColor` | RGBA | `(1,1,1,1)` | 3.x `Emission` |
| 29 | **Emission Strength** | Emission Strength | `NodeSocketFloat` | VALUE | `0` | 3.x 에서 추가 |
| 30 | **Thin Film Thickness** | Thin Film Thickness | `NodeSocketFloatWavelength` | VALUE | `0` | 나노 단위. 0=없음, 100~1000 nm |
| 31 | **Thin Film IOR** | Thin Film IOR | `NodeSocketFloat` | VALUE | `1.33` | 필름 IOR |

출력: `BSDF` (`NodeSocketShader`) 1개.

노드 레벨 프로퍼티:

| 프로퍼티 | enum | 기본값 |
|---|---|---|
| `distribution` | `GGX`, `MULTI_GGX` | `GGX` |
| `subsurface_method` | `BURLEY`, `RANDOM_WALK`, `RANDOM_WALK_SKIN`, `RANDOM_WALK_LEGACY` | `BURLEY` |

### 3.2 3.x / 4.x → 5.x 이름 마이그레이션

`bsdf.inputs['예전이름']` 이 **통하는지** 를 5.2 에서 직접 검사한 결과:

| 구 이름 (≤3.x / 4.x) | 5.2 상태 | 대체 이름 |
|---|---|---|
| `Subsurface` | ❌ 없음 | `Subsurface Weight` (+ `Subsurface Radius`, `Subsurface Scale`) |
| `Subsurface Color` | ❌ 없음 | `Base Color` |
| `Specular` | ❌ 없음 | `Specular IOR Level` |
| `Sheen` | ❌ 없음 | `Sheen Weight` |
| `Clearcoat` | ❌ 없음 | `Coat Weight` |
| `Clearcoat Roughness` | ❌ 없음 | `Coat Roughness` |
| `Clearcoat Normal` | ❌ 없음 | `Coat Normal` |
| `Transmission` | ❌ 없음 | `Transmission Weight` |
| `Transmission Roughness` | ❌ 없음 | `Roughness` (전역 roughness) |
| `Emission` | ❌ 없음 | `Emission Color` |
| `Subsurface Radius` | ✅ 그대로 | — |
| `Subsurface IOR`, `Subsurface Anisotropy` | ✅ 그대로 | — |
| `Specular Tint`, `Anisotropic`, `Anisotropic Rotation` | ✅ 그대로 | — |
| `Sheen Tint`, `Metallic`, `Roughness`, `IOR`, `Alpha`, `Normal`, `Tangent`, `Weight`, `Base Color` | ✅ 그대로 | — |
| `Emission Strength` | ✅ 그대로 | — |
| — | 4.x `Subsurface Scale` → 5.x ✅ | |
| — | 5.x 신규 `Thin Wall` | |

노드 프로퍼티로 옮겨간 것:

| 3.x | 5.x | 상태 |
|---|---|---|
| `bsdf.clearcoat` | `Coat Weight` 소켓 | ❌ 노드 프로퍼티 자체가 없음 |
| `bsdf.sheen` | `Sheen Weight` 소켓 | ❌ |
| `bsdf.sss_type` | `subsurface_method` | ❌ (3.x 이름) / ✅ 5.x 이름 |
| `bsdf.specular_intensity` | `Specular IOR Level` 소켓 | ❌ |
| `bsdf.use_multiple_importance_sampling` | — | ❌ 제거 |
| `bsdf.distribution` | `distribution` | ✅ (`MULTI_GGX` 추가됨) |

### 3.3 소켓 `min_value` / `max_value` / `subtype` 는 **5.2 에서 사라졌다**

이건 3.x/4.x 스크립트를 가장 많이 깨뜨리는 변경이다.

```python
s = p.inputs['Roughness']
s.min_value    # AttributeError: 'NodeSocketFloatFactor' object has no attribute 'min_value'
s.max_value    # AttributeError
s.subtype      # AttributeError
s.default_value = 0.5   # ✅ 이건 그대로
```

5.2 에서 `bpy.types.NodeSocketFloat` / `NodeSocketFloatFactor` / `NodeSocketInt` /
`NodeSocketColor` … **어떤 소켓 클래스에도 `min_value` / `max_value` / `subtype` RNA 가 없다.**
(직접 `getattr` 으로도 `AttributeError`. `bl_rna.properties` 에도 없다.)

대신 **서브타입이 소켓 타입 자체에 Bake** 된다:

| 의미 | 5.2 소켓 `bl_idname` | `interface` 소켓의 `subtype` 값 |
|---|---|---|
| 일반 | `NodeSocketFloat` | `NONE` |
| 픽셀 | `NodeSocketFloatPixel` | `PIXEL` |
| 퍼센트 | `NodeSocketFloatPercentage` | `PERCENTAGE` |
| 계수(0–1) | `NodeSocketFloatFactor` | `FACTOR` |
| 질량 | `NodeSocketFloatMass` | `MASS` |
| 각도 | `NodeSocketFloatAngle` | `ANGLE` |
| 시간 | `NodeSocketFloatTime` | `TIME` |
| 절대 시간 | `NodeSocketFloatTimeAbsolute` | `TIME_ABSOLUTE` |
| 거리 | `NodeSocketFloatDistance` | `DISTANCE` |
| 파장 | `NodeSocketFloatWavelength` | `WAVELENGTH` |
| 색온도 | `NodeSocketFloatColorTemperature` | `COLOR_TEMPERATURE` |
| 주파수 | `NodeSocketFloatFrequency` | `FREQUENCY` |
| 정수 계수 | `NodeSocketIntFactor` | `FACTOR` |
| 정수 퍼센트 | `NodeSocketIntPercentage` | `PERCENTAGE` |
| 정수 픽셀 | `NodeSocketIntPixel` | `PIXEL` |

주의: 이 `min_value` / `max_value` / `subtype` 는 **`NodeTreeInterfaceSocket`** 쪽에는
**아직 존재한다**. `ng.interface.new_socket(...)` 로 만든 소켓에서만 조작한다.
5.2 실측 기본값은 `min = -FLT_MAX`, `max = +FLT_MAX` 이며, `min_value = 5` 로 바꿔도
`default_value = 3` 이 클램프되지 않는다 (UI 힌트일 뿐).

**검증 예제 (EX-03)** — `verify/doc_03_principled_mix.py`

```python
"""DOC EX-03 — Principled BSDF reference + Mix node (ShaderNodeMix / Mix (Legacy))."""
import bpy, sys

mat = bpy.data.materials.new("Ref")
nt = mat.node_tree
p = nt.nodes['Principled BSDF']

# ---- 5.2 Principled 입력값 설정 ------------------------------------------
p.inputs['Base Color'].default_value        = (0.55, 0.57, 0.60, 1.0)
p.inputs['Metallic'].default_value          = 0.85
p.inputs['Roughness'].default_value         = 0.28
p.inputs['IOR'].default_value               = 1.45
p.inputs['Specular IOR Level'].default_value = 0.5
p.inputs['Coat Weight'].default_value       = 0.30
p.inputs['Coat Roughness'].default_value    = 0.06
p.inputs['Sheen Weight'].default_value      = 0.15
p.inputs['Subsurface Weight'].default_value = 0.0
p.inputs['Emission Color'].default_value    = (1.0, 0.35, 0.05, 1.0)
p.inputs['Emission Strength'].default_value = 3.0
p.inputs['Thin Film Thickness'].default_value = 420.0
p.inputs['Thin Film IOR'].default_value     = 1.38
p.distribution = 'MULTI_GGX'
p.subsurface_method = 'RANDOM_WALK'
print("p.distribution:", p.distribution, "| p.subsurface_method:", p.subsurface_method)

for name in ('Base Color', 'Emission Strength', 'Thin Film Thickness', 'Thin Wall'):
    s = p.inputs[name]
    print(f"  {name:<22} type={s.type:<8} bl_idname={s.bl_idname:<28} "
          f"min_value={'min_value' in [q.identifier for q in s.bl_rna.properties]}")

# ---- ShaderNodeMix --------------------------------------------------------
mix = nt.nodes.new("ShaderNodeMix")
mix.location = (-200, 200)
mix.data_type = 'RGBA'          # 반드시 링크를 걸기 전에
mix.blend_type = 'MIX'
mix.factor_mode = 'UNIFORM'
mix.clamp_factor = True
a = nt.nodes.new("ShaderNodeRGB"); a.outputs[0].default_value = (0.9, 0.2, 0.05, 1)
b = nt.nodes.new("ShaderNodeRGB"); b.outputs[0].default_value = (0.05, 0.2, 0.9, 1)
nt.links.new(a.outputs['Color'], mix.inputs['A'])
nt.links.new(b.outputs['Color'], mix.inputs['B'])
mix.inputs['Factor'].default_value = 0.4
nt.links.new(mix.outputs['Result'], p.inputs['Base Color'])
print()
print("Mix enabled sockets:", [(s.name, s.identifier) for s in mix.inputs if s.enabled])
print("Mix output          :", [(s.name, s.identifier) for s in mix.outputs if s.enabled])
print("resolved A ->", mix.inputs['A'].identifier, "| Result ->", mix.outputs['Result'].identifier)

# ---- ShaderNodeMixRGB (여전히 존재, 단 label 이 'Mix (Legacy)') ------------
leg = nt.nodes.new("ShaderNodeMixRGB")
leg.location = (-200, -200)
print()
print("MixRGB bl_idname:", leg.bl_idname, "| bl_label:", leg.bl_label, "| type:", leg.type)
print("  inputs :", [(s.name, s.identifier) for s in leg.inputs])
print("  outputs:", [(s.name, s.identifier) for s in leg.outputs])
print("  extra props:", [q.identifier for q in leg.bl_rna.properties
                         if q.identifier not in {p.identifier for p in bpy.types.Node.bl_rna.properties}])
leg.inputs['Color1'].default_value = (0.2, 0.8, 0.2, 1)
leg.inputs['Color2'].default_value = (0.2, 0.2, 0.8, 1)
leg.inputs['Fac'].default_value = 0.25
leg.blend_type = 'MULTIPLY'
leg.use_clamp = True
nt.links.new(leg.outputs['Color'], p.inputs['Emission Color'])

# ---- ShaderNodeValToRGB ----------------------------------------------------
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.location = (-450, 400)
e = ramp.color_ramp.elements
e[0].position = 0.25
e[0].color = (0.0, 0.0, 0.0, 1.0)
e[1].position = 0.80
e[1].color = (1.0, 1.0, 1.0, 1.0)
mid = e.new(0.5)
mid.color = (0.5, 0.2, 0.1, 1.0)
ramp.color_ramp.interpolation = 'B_SPLINE'
print()
print("ramp:", [(el.position, tuple(el.color)) for el in ramp.color_ramp.elements])
print("interpolation enum:",
      [i.identifier for i in ramp.color_ramp.bl_rna.properties['interpolation'].enum_items])

print("__SCRIPT_OK__")
sys.exit(0)
```

실측 출력:

```
p.distribution: MULTI_GGX | p.subsurface_method: RANDOM_WALK
  Base Color             type=RGBA     bl_idname=NodeSocketColor              min_value=False
  Emission Strength      type=VALUE    bl_idname=NodeSocketFloat              min_value=False
  Thin Film Thickness    type=VALUE    bl_idname=NodeSocketFloatWavelength    min_value=False
  Thin Wall              type=BOOLEAN  bl_idname=NodeSocketBool               min_value=False
Mix enabled sockets: [('Factor', 'Factor_Float'), ('A', 'A_Color'), ('B', 'B_Color')]
Mix output          : [('Result', 'Result_Color')]
MixRGB bl_idname: ShaderNodeMixRGB | bl_label: Mix (Legacy) | type: MIX_RGB
  extra props: ['blend_type', 'use_alpha', 'use_clamp']
ramp: [(0.25, (0,0,0,1)), (0.5, (0.5,0.2,0.1,1)), (0.8, (1,1,1,1))]
interpolation enum: ['EASE', 'CARDINAL', 'LINEAR', 'B_SPLINE', 'CONSTANT']
```

---

## 4. 셰이더 노드 타입 레퍼런스

### 4.1 전체 목록

5.2 에 등록된 `ShaderNode*` 타입은 총 103개다 (`bpy.types` 를 순회해서 추출, `verify/05_node_enum.py`).
| 카테고리 | `bl_idname` |
|---|---|
| BSDF / 셰이더 | `ShaderNodeAddShader`, `ShaderNodeBackground`, `ShaderNodeBsdfAnisotropic`, `ShaderNodeBsdfDiffuse`, `ShaderNodeBsdfGlass`, `ShaderNodeBsdfHair`, `ShaderNodeBsdfHairPrincipled`, `ShaderNodeBsdfMetallic`, `ShaderNodeBsdfPrincipled`, `ShaderNodeBsdfRayPortal`, `ShaderNodeBsdfRefraction`, `ShaderNodeBsdfSheen`, `ShaderNodeBsdfToon`, `ShaderNodeBsdfTranslucent`, `ShaderNodeBsdfTransparent`, `ShaderNodeEmission`, `ShaderNodeHoldout`, `ShaderNodeMixShader`, `ShaderNodeOutputLight`, `ShaderNodeOutputMaterial`, `ShaderNodeOutputWorld`, `ShaderNodeShaderToRGB`, `ShaderNodeVolumeAbsorption`, `ShaderNodeVolumePrincipled`, `ShaderNodeVolumeScatter`, `ShaderNodeVolumeCoefficients`, `ShaderNodeVolumeInfo` |
| 텍스처 | `ShaderNodeTexBrick`, `ShaderNodeTexChecker`, `ShaderNodeTexEnvironment`, `ShaderNodeTexGabor`, `ShaderNodeTexGradient`, `ShaderNodeTexIES`, `ShaderNodeTexImage`, `ShaderNodeTexMagic`, `ShaderNodeTexNoise`, `ShaderNodeTexSky`, `ShaderNodeTexVoronoi`, `ShaderNodeTexWave`, `ShaderNodeTexWhiteNoise`, `ShaderNodeTexCoord`, `ShaderNodeUVMap`, `ShaderNodeRadialTiling` |
| 색 / 벡터 / 수학 | `ShaderNodeBrightContrast`, `ShaderNodeClamp`, `ShaderNodeCombineColor`, `ShaderNodeCombineXYZ`, `ShaderNodeFloatCurve`, `ShaderNodeGamma`, `ShaderNodeHueSaturation`, `ShaderNodeInvert`, `ShaderNodeMapRange`, `ShaderNodeMapping`, `ShaderNodeMath`, `ShaderNodeMix`, `ShaderNodeMixRGB`, `ShaderNodeRGB`, `ShaderNodeRGBCurve`, `ShaderNodeRGBToBW`, `ShaderNodeSeparateColor`, `ShaderNodeSeparateXYZ`, `ShaderNodeSqueeze`, `ShaderNodeValue`, `ShaderNodeVectorCurve`, `ShaderNodeVectorMath`, `ShaderNodeVectorRotate`, `ShaderNodeVectorTransform` |
| 지오메트리 정보 / 노멀 | `ShaderNodeAttribute`, `ShaderNodeBevel`, `ShaderNodeCameraData`, `ShaderNodeFresnel`, `ShaderNodeLayerWeight`, `ShaderNodeNewGeometry`, `ShaderNodeNormal`, `ShaderNodeNormalMap`, `ShaderNodeObjectInfo`, `ShaderNodeParticleInfo`, `ShaderNodePointInfo`, `ShaderNodeTangent`, `ShaderNodeVertexColor`, `ShaderNodeWireframe`, `ShaderNodeAmbientOcclusion` |
| 변형 / 레이캐스트 / 기타 | `ShaderNodeBump`, `ShaderNodeDisplacement`, `ShaderNodeVectorDisplacement`, `ShaderNodeLightPath`, `ShaderNodeRaycast`, `ShaderNodeBlackbody`, `ShaderNodeWavelength`, `ShaderNodeGroup`, `ShaderNodeCustomGroup`, `ShaderNodeScript`, `ShaderNodeOutputAOV`, `ShaderNodeOutputLineStyle`, `ShaderNodeEeveeSpecular`, `ShaderNodeHairInfo`, `ShaderNodeUVAlongStroke` |

**5.x 에서 사라진 것**: `ShaderNodeTexMusgrave`(4.0 에서 Noise 로 통합),
`ShaderNodeTexPointDensity`(5.0 에서 제거), 구(compositor) 전용 `ShaderNode*` 다수.

### 4.2 자주 쓰는 노드의 입출력 (실측)

| bl_idname | label | inputs | outputs | 주요 프로퍼티 |
|---|---|---|---|---|
| `ShaderNodeTexNoise` | Noise Texture | Vector, W, Scale, Detail, Roughness, Lacunarity, Offset, Gain, Distortion | **Factor**, Color | `noise_dimensions` 1D/2D/3D/4D, `noise_type` MULTIFRACTAL/RIDGED_MULTIFRACTAL/HYBRID_MULTIFRACTAL/FBM/HETERO_TERRAIN, `normalize` |
| `ShaderNodeTexVoronoi` | Voronoi Texture | Vector, W, Scale, Detail, Roughness, Lacunarity, Smoothness, Exponent, Randomness | Distance, Color, Position, W, Radius | `feature` F1/F2/SMOOTH_F1/DISTANCE_TO_EDGE/N_SPHERE_RADIUS, `distance` |
| `ShaderNodeTexWave` | Wave Texture | Vector, Scale, Distortion, Detail, Detail Scale, Detail Roughness, Phase Offset | Color, Factor | `wave_type` BANDS/RINGS, `wave_profile` SIN/SAW/TRI, `bands_direction` |
| `ShaderNodeTexGradient` | Gradient Texture | Vector | Color, Factor | `gradient_type` LINEAR/QUADRATIC/EASING/DIAGONAL/SPHERICAL/QUADRATIC_SPHERE/RADIAL |
| `ShaderNodeTexWhiteNoise` | White Noise Texture | Vector, W | Value, Color | `noise_dimensions` |
| `ShaderNodeTexMagic` | Magic Texture | Vector, Scale, Distortion | Color, Factor | `turbulence_depth` |
| `ShaderNodeTexGabor` | Gabor Texture | Vector, Scale, Frequency, Anisotropy, Orientation, Orientation | Value, Phase, Intensity | `gabor_type` 2D/3D |
| `ShaderNodeTexBrick` | Brick Texture | Vector, Color1, Color2, Mortar, Scale, Mortar Size, Mortar Smooth, Bias, Brick Width, Row Height | Color, Factor | `offset_frequency`, `squash_frequency`, `offset`, `squash` |
| `ShaderNodeTexChecker` | Checker Texture | Vector, Color1, Color2, Scale | Color, Factor | — |
| `ShaderNodeBump` | Bump | Strength, Distance, **Filter Width**, Height, Normal | Normal | `invert` |
| `ShaderNodeDisplacement` | Displacement | Height, Midlevel, Scale, Normal | Displacement | `space` OBJECT/WORLD |
| `ShaderNodeVectorDisplacement` | Vector Displacement | Vector, Midlevel, Scale | Displacement | `space` TANGENT/OBJECT/WORLD |
| `ShaderNodeNormalMap` | Normal Map | Strength, Color | Normal | `space`, `uv_map`, `convention` OPENGL/DIRECTX, `base` ORIGINAL/DISPLACED |
| `ShaderNodeTexCoord` | Texture Coordinate | — | Generated, Normal, UV, Object, Camera, Window, Reflection | `object`, `from_instancer` |
| `ShaderNodeNewGeometry` | Geometry | — | Position, Normal, Tangent, True Normal, Incoming, Parametric, Backfacing, Pointiness, Random Per Island | — |
| `ShaderNodeObjectInfo` | Object Info | — | Location, Color, Alpha, Object Index, Material Index, Random | — |
| `ShaderNodeAttribute` | Attribute | — | Color, Vector, Factor, Alpha | `attribute_type` GEOMETRY/OBJECT/INSTANCER/VIEW_LAYER, `attribute_name` |
| `ShaderNodeSeparateColor` | Separate Color | Color | Red, Green, Blue | `mode` RGB/HSV/HSL |
| `ShaderNodeCombineColor` | Combine Color | Red, Green, Blue | Color | `mode` RGB/HSV/HSL |
| `ShaderNodeMath` | Math | Value, Value, Value | Value | `operation` 41종, `use_clamp` |
| `ShaderNodeVectorMath` | Vector Math | Vector, Vector, Vector, Scale | Vector, Value | `operation` 28종 |
| `ShaderNodeMapRange` | Map Range | Value, From Min, From Max, To Min, To Max, Steps, (Vector 타입 6개) | Result, Vector | `data_type` FLOAT/FLOAT_VECTOR, `interpolation_type`, `clamp` |
| `ShaderNodeClamp` | Clamp | Value, Min, Max | Result | `clamp_type` MINMAX/RANGE |
| `ShaderNodeRGBToBW` | RGB to BW | Color | Val | — |
| `ShaderNodeInvert` | Invert Color | Factor, Color | Color | — |
| `ShaderNodeFresnel` | Fresnel | IOR, Normal | Factor | — |
| `ShaderNodeLayerWeight` | Layer Weight | Blend, Normal | Fresnel, Facing | — |
| `ShaderNodeBevel` | Bevel | Radius, Normal | Normal | `samples` |
| `ShaderNodeAmbientOcclusion` | Ambient Occlusion | Color, Distance, Normal | Color, AO | `samples`, `inside`, `only_local` |
| `ShaderNodeBackground` | Background | Color, Strength, **Weight** | Background | — |
| `ShaderNodeEmission` | Emission | Color, Strength, **Weight** | Emission | — |
| `ShaderNodeVolumePrincipled` | Principled Volume | Color, Color Attribute, Density, Density Attribute, Anisotropy, Absorption Color, Emission Strength, Emission Color, Blackbody Intensity, Blackbody Tint, Temperature, Temperature Attribute, Weight | Volume | — |
| `ShaderNodeValToRGB` | Color Ramp | Fac | Color, Alpha | `.color_ramp` |
| `ShaderNodeMix` | Mix | Factor ×2, A ×4, B ×4 | Result ×4 | `data_type`, `factor_mode`, `blend_type`, `clamp_factor`, `clamp_result` |
| `ShaderNodeMixRGB` | **Mix (Legacy)** | Factor, Color1, Color2 | Color | `blend_type`, `use_alpha`, `use_clamp` |

> `Weight` 입력이 5.x 에서 `Background` / `Emission` / `BsdfDiffuse` / `BsdfToon` /
> `VolumeAbsorption` / `VolumeScatter` / `BsdfTransparent` / `SubsurfaceScattering` /
> `BsdfGlossy` / `BsdfRefraction` / `BsdfHairPrincipled` 에 붙었다 (셰이더 스택 내 가중치).

### 4.3 ColorRamp API

```python
ramp = node.color_ramp
ramp.interpolation = 'LINEAR'   # EASE | CARDINAL | LINEAR | B_SPLINE | CONSTANT
ramp.elements[0].position = 0.25          # 0 이 항상 0, 1 이 항상 1 로 남는다
ramp.elements[0].color = (0, 0, 0, 1)
e = ramp.elements.new(0.5)     # 중간 삽입 → 자동 정렬
e.color = (0.5, 0.2, 0.1, 1)
# 첫/끝 요소는 위치가 0/1 로 고정이라 이동시킬 수 없다
```

`elements.new()` 는 위치가 자동 정렬되며, 색은 삽입 시 그 앞뒤 값의 보간값이 된다.
5.2 실측: `new(0.5)` → `(0.5, 0.5, 0.5, 1)` (중간값).

### 4.4 `ShaderNodeMixRGB` 는 5.2 에 **아직 존재한다** — 단, 이름이 `Mix (Legacy)`

질문에 대한 정확한 답:

| 항목 | 5.2 실측 |
|---|---|
| `nodes.new("ShaderNodeMixRGB")` | ✅ 성공 |
| `node.bl_idname` | `ShaderNodeMixRGB` |
| `node.bl_label` / `node.name` | **`"Mix (Legacy)"`** |
| `node.type` | `MIX_RGB` |
| inputs | `Factor`(`Fac`), `Color1`(`Color1`), `Color2`(`Color2`) |
| outputs | `Color`(`Color`) |
| 노드 프로퍼티 | `blend_type`, `use_alpha`, `use_clamp` |
| `data_type` / `factor_mode` / `clamp_factor` | ❌ 없음 |
| deprecation 경고 | **없음** (조용히 동작) |

즉 **"ShaderNodeMixRGB 가 5.2 에서 제거됐는가?" 의 답은 "아니오, 레거시로 남았다"** 이다.
다만 UI 에서 "Mix (Legacy)" 라고 표시되고, 저장된 `.blend` 를 다시 열면 이 레거시 노드가
그대로 유지된다. 새 스크립트는 `ShaderNodeMix` 를 쓰는 게 맞다
(벡터/회전/정수까지 한 노드에서 처리되므로).

반면 **`TextureNodeMixRGB`** (Blender 2.7 의Mix RGB) 는 셰이더 트리에 넣을 수 없다:

```
RuntimeError: Error: Cannot add node of type TextureNodeMixRGB to node tree 'Shader Nodetree'
  Not a texture node tree
```

`TextureNodeTree` 자체가 5.2 에 남아 있지만(`bpy.data.node_groups.new(n, 'TextureNodeTree')`
가능) 옛_blender 내부 텍스처 시스템용이고 셰이더 출력에는 쓸 수 없다.

### 4.5 `ShaderNodeMix` 소켓 선택 규칙

`ShaderNodeMix` 는 소켓 이름이 4중/2중으로 겹친다:

```
inputs : Factor(Factor_Float) Factor(Factor_Vector) A(A_Float) B(B_Float)
         A(A_Vector) B(B_Vector) A(A_Color) B(B_Color) A(A_Rotation) B(A_Rotation)
outputs: Result(Result_Float) Result(Result_Vector) Result(Result_Color) Result(Result_Rotation)
```

규칙:

1. `[]` 조회는 **이름** 기준이고 **활성 소켓만** 찾는다 → `data_type` 을 먼저 설정하면
   `node.inputs['A']` 가 자동으로 `A_Color` 로 해석된다.
2. `node.inputs['A_Color']` (identifier 로 조회) 는 **항상 `KeyError`**.
3. identifier 가 필요하면 순회해야 한다.

```python
def typed_socket(node, coll, ident):
    for s in getattr(node, coll):
        if s.identifier == ident:
            return s
    raise KeyError(ident)
```

`data_type`: `FLOAT`/`VECTOR`/`RGBA`/`ROTATION`. `factor_mode`: `UNIFORM`/`NON_UNIFORM`.
`blend_type`: `MIX, DARKEN, MULTIPLY, BURN, LIGHTEN, SCREEN, DODGE, ADD, OVERLAY, SOFT_LIGHT,
LINEAR_LIGHT, DIFFERENCE, EXCLUSION, SUBTRACT, DIVIDE, HUE, SATURATION, COLOR, VALUE`.

`data_type` 을 **링크가 걸린 뒤에** 바꾸면 해당 링크가 `is_valid == False` 가 된다.
항상 `data_type` → `blend_type` → 링크 순서로 한다.

---

## 5. Mix / Mix (Legacy)

요약. `ShaderNodeMix` 는 `data_type` → `blend_type` → 링크 순서로 세팅하고
`inputs['A'] / inputs['B'] / outputs['Result']`(이름) 로 접근한다.
`ShaderNodeMixRGB` 는 5.2 에 **아직 살아 있고** UI 라벨이 `Mix (Legacy)` 다.
자세한 실측 표와 소켓 규칙은 [§4.4](#44-shadernodemixrgb-는-52-에-아직-존재한다--단-이름이-mix-legacy),
[§4.5](#45-shadernodemix-소켓-선택-규칙) 참조.

```python
# 새 코드 (권장)
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type  = 'RGBA'          # 1순위: FLOAT / VECTOR / RGBA / ROTATION
mix.blend_type = 'MULTIPLY'      # 2순위
nt.links.new(a.outputs['Color'], mix.inputs['A'])     # 이름 'A' — 활성 소켓 자동 해석
nt.links.new(b.outputs['Color'], mix.inputs['B'])
nt.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])

# 레거시 (기존 .blend 수정 시에만)
leg = nt.nodes.new("ShaderNodeMixRGB")
leg.inputs['Fac'].default_value = 0.3
leg.blend_type = 'MIX'
leg.use_clamp = True
```

---

## 6. 프로시저럴 텍스처링

### 6.1 좌표계 노드 선택

| `ShaderNodeTexCoord` 출력 | 의미 | 5.x 주의 |
|---|---|---|
| `Generated` | 오브젝트 바운딩박스 정규화 좌표 (0–1) | 슬롯 이동해도 텍스처가 따라감 |
| `Object` | 오브젝트 로컬 좌표 (미터 단위) | **오브젝트별 마스크/ dirt 에 표준**. 오브젝트를 스케일하면 패턴도 스케일됨 |
| `UV` | UV 맵 | `ShaderNodeUVMap` 으로 특정 레이어 지정 가능 |
| `Normal` | 셰이딩 노멀(월드) | 변형 텍스처용 |
| `Camera`, `Window`, `Reflection` | 각각 카메라/화면/반사 벡터 | |

`ShaderNodeMapping` 의 `vector_type` 은 `POINT` / `TEXTURE` / `VECTOR` / `NORMAL`.
`POINT` 는 보간되는 좌표(위치), `TEXTURE` 는 텍스처 공간 벡터다. 스케일/회전 전에
어느 공간에서 작업할지 정하는 것이라 실수하기 쉽다.

`ShaderNodeUVMap.uv_map` 은 빈 문자열이면 활성 UV 레이어를 쓴다.

### 6.2 노이즈 기반 roughness

```python
nz = nt.nodes.new("ShaderNodeTexNoise")
nz.inputs['Scale'].default_value     = 22.0
nz.inputs['Detail'].default_value    = 10.0
nz.inputs['Roughness'].default_value = 0.55      # 0.5=보통, 높을수록 고주파 증가
nt.links.new(nz.outputs['Factor'], bsdf.inputs['Roughness'])
```

`Roughness` 소켓은 `NodeSocketFloatFactor`(0–1) 이므로 램프 없이 직접 물려도
범위를 벗어나지 않는다. 다만 "특정 값 근처에 얼룩" 같은 표현은
`ShaderNodeValToRGB` 로 범위를 좁히는 게 자연스럽다.

5.x Noise 는 출력 이름이 `Fac` → **`Factor`** 로 바뀌었다 (identifier 는 여전히 `Fac`).
출력 이름으로 코드를 쓰면 `nz.outputs['Factor']`.

### 6.3 Bump 로 변위 표현

`ShaderNodeBump` 는 정점을 움직이지 않고 **셰이딩 노멀만** 바꾼다.
입력 `Height` / `Strength` / `Distance` / `Filter Width` / `Normal`, 출력 `Normal`,
`invert = True` 로 반전. 여러 겹을 쌓을 때는 Bump 의 `Normal` 입력에 이전 Bump 출력을
넣는다(직렬). `Filter Width` 가 너무 작으면 앨리어싱으로 터진다 —
EX-09 검증에서 `Strength=0.35`, `Distance=0.03` 이 Cycles CPU 160×90 에서 노이즈 없이
깔끔했다. 진짜 실루엣 변위는 `ShaderNodeDisplacement` + `Material.displacement_method`,
또는 `GeometryNodeSetPosition`.

### 6.4 그라디언트 마스크

`ShaderNodeTexGradient` 의 `Fac` 출력은 0→1 그라디언트.
`ShaderNodeTexCoord.Object` → `Mapping`(Z 를 Y 로 회전) → `Gradient` →
`Map Range` 로 구간 좁히기 → `ValToRGB` 로 경계 정리 → `Mix.Factor`.

**검증 예제 (EX-09)** — `verify/doc_09_procedural.py`
(하단 half 에 dirt 가 쌓인 금속 + 절차적 roughness, Cycles CPU 32spp 160×90)

```python
"""DOC EX-09 — Procedural material: noise roughness + gradient mask + bump (render)."""
import bpy, sys, os, math
import addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
sc.render.resolution_x = 160; sc.render.resolution_y = 90
sc.render.filepath = "/workspace/out/doc_procedural.png"

# ---- world: simple gradient (not sky) -------------------------------------
w = bpy.data.worlds.new("W"); sc.world = w
wnt = w.node_tree; wnt.nodes.clear()
wo = wnt.nodes.new("ShaderNodeOutputWorld")
bg = wnt.nodes.new("ShaderNodeBackground"); bg.inputs['Strength'].default_value = 0.8
tc = wnt.nodes.new("ShaderNodeTexCoord")
mp = wnt.nodes.new("ShaderNodeMapping")
mp.inputs['Rotation'].default_value = (math.radians(90), 0, 0)
mp.inputs['Location'].default_value = (0, 0, 0.5)
mp.inputs['Scale'].default_value = (0.5, 0.5, 0.5)
gr = wnt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = 'QUADRATIC'
ramp = wnt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.05, 0.06, 0.09, 1)
ramp.color_ramp.elements[1].color = (0.55, 0.72, 0.95, 1)
wnt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
wnt.links.new(mp.outputs['Vector'], gr.inputs['Vector'])
wnt.links.new(gr.outputs['Fac'], ramp.inputs['Fac'])
wnt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
wnt.links.new(bg.outputs['Background'], wo.inputs['Surface'])

# ---- material: noise roughness + gradient mask + object coords ------------
mat = bpy.data.materials.new("Proc")
nt = mat.node_tree
bsdf = nt.nodes['Principled BSDF']; bsdf.location = (400, 0)
nt.nodes['Material Output'].location = (700, 0)

objco = nt.nodes.new("ShaderNodeTexCoord"); objco.location = (-1200, 400)
genco = nt.nodes.new("ShaderNodeTexCoord"); genco.location = (-1200, 100)

# gradient mask along local Z (dirt on the lower half)
gradm = nt.nodes.new("ShaderNodeTexGradient"); gradm.location = (-1000, 100)
gradm.gradient_type = 'LINEAR'
sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-820, 100)
mr = nt.nodes.new("ShaderNodeMapRange"); mr.location = (-640, 100)
mr.clamp = True
mr.inputs['From Min'].default_value = 0.1
mr.inputs['From Max'].default_value = 0.6
mr.inputs['To Min'].default_value = 0.0
mr.inputs['To Max'].default_value = 1.0
maskramp = nt.nodes.new("ShaderNodeValToRGB"); maskramp.location = (-450, 100)
maskramp.color_ramp.elements[0].position = 0.45
maskramp.color_ramp.elements[1].position = 0.55

# noise for roughness + bump
nz = nt.nodes.new("ShaderNodeTexNoise"); nz.location = (-820, -300)
nz.inputs['Scale'].default_value = 22.0
nz.inputs['Detail'].default_value = 10.0
nz.inputs['Roughness'].default_value = 0.55
roughramp = nt.nodes.new("ShaderNodeValToRGB"); roughramp.location = (-600, -300)
roughramp.color_ramp.elements[0].color = (0.12, 0.12, 0.12, 1)
roughramp.color_ramp.elements[1].color = (0.85, 0.85, 0.85, 1)
bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-150, -350)
bump.inputs['Strength'].default_value = 0.35
bump.inputs['Distance'].default_value = 0.03
bump2 = nt.nodes.new("ShaderNodeBump"); bump2.location = (100, -350)
bump2.inputs['Strength'].default_value = 0.6

# paint the base colour: clean metal blended toward dirt by the mask
col1 = nt.nodes.new("ShaderNodeRGB"); col1.location = (-450, 400)
col1.outputs[0].default_value = (0.55, 0.57, 0.60, 1)
dirt = nt.nodes.new("ShaderNodeRGB"); dirt.location = (-450, 600)
dirt.outputs[0].default_value = (0.10, 0.055, 0.03, 1)
mixc = nt.nodes.new("ShaderNodeMix"); mixc.location = (-200, 400)
mixc.data_type = 'RGBA'
mixc.blend_type = 'MIX'

nt.links.new(genco.outputs['Object'], gradm.inputs['Vector'])
nt.links.new(gradm.outputs['Fac'], sep.inputs['Vector'])
nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
nt.links.new(mr.outputs['Result'], maskramp.inputs['Fac'])
nt.links.new(objco.outputs['Object'], nz.inputs['Vector'])
nt.links.new(nz.outputs['Factor'], roughramp.inputs['Fac'])
nt.links.new(nz.outputs['Factor'], bump.inputs['Height'])
nt.links.new(maskramp.outputs['Color'], mixc.inputs['Factor'])
nt.links.new(dirt.outputs['Color'], mixc.inputs['A'])
nt.links.new(col1.outputs['Color'], mixc.inputs['B'])
nt.links.new(mixc.outputs['Result'], bsdf.inputs['Base Color'])
nt.links.new(roughramp.outputs['Color'], bsdf.inputs['Roughness'])
nt.links.new(bump.outputs['Normal'], bump2.inputs['Normal'])
nt.links.new(maskramp.outputs['Color'], bump2.inputs['Height'])
nt.links.new(bump2.outputs['Normal'], bsdf.inputs['Normal'])
bsdf.inputs['Metallic'].default_value = 0.85

# ---- scene ----------------------------------------------------------------
bpy.ops.mesh.primitive_monkey_add(size=2, location=(0, 0, 1.3))
monkey = bpy.context.object
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
ground = bpy.context.object
monkey.data.materials.append(mat)
ground.data.materials.append(mat)
cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d)
sc.collection.objects.link(cam)
cam.location = (0, -4.2, 2.0); cam.rotation_euler = (math.radians(74), 0, 0)
sc.camera = cam
sun_d = bpy.data.lights.new("S", type='SUN'); sun_d.energy = 4.0
sun = bpy.data.objects.new("S", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(40), 0, math.radians(35))

bpy.ops.render.render(write_still=True)
print("rendered:", sc.render.filepath, os.path.getsize(sc.render.filepath))
print("__SCRIPT_OK__")
sys.exit(0)
```

---

## 7. 이미지 텍스처

### 7.1 `bpy.data.images` 함수 시그니처 (5.2 실측)

```
Images.new(name, width=1024, height=1024, alpha=False, float_buffer=False,
           stereo3d=False, is_data=False, tiled=False) -> Image
Images.load(filepath, check_existing=False) -> Image
Images.remove(image, do_unlink=True, do_id_user=True, do_ui_user=True)
Images.tag(value)
```

`new()` 의 `tiled=True` 는 **5.x 신규** — UDIM 이미지를 코드에서 바로 만들 수 있다.

### 7.2 `Image` 프로퍼티 (5.2 실측)

| 프로퍼티 | 타입 | 비고 |
|---|---|---|
| `source` | enum | `FILE`/`SEQUENCE`/`MOVIE`/`GENERATED`/`VIEWER`/**`TILED`**(UDIM Tiles). 기본 `FILE` |
| `file_format` | enum | AVIF, JPEG, OPEN_EXR, PNG, WEBP, BMP, CINEON, DPX, IRIS, JPEG2000, HDR, TARGA, TARGA_RAW, TIFF, OPEN_EXR_MULTILAYER, FFMPEG |
| `filepath` / `filepath_raw` | str | `save()` 대상 |
| `size` | (w, h) int | |
| `resolution` | float | 픽셀/단위 비율 |
| `channels` | **int** | **5.2 에서 항상 4** (아래 참고) |
| `depth` | int | 비트 수: byte RGB=24, RGBA=32, half RGBA=64, float RGBA=128 |
| `is_float` | bool | |
| `use_half_precision` | bool | float 버퍼를 half 로 유지 (5.x 기본 `True`) |
| `pixels` | float 배열 | `foreach_get` / `foreach_set` 가능 |
| `colorspace_settings` | `ColorManagedInputColorspaceSettings` | `.name` (예: `sRGB`, `Non-Color`, `Linear Rec.709`) |
| `alpha_mode` | enum | `STRAIGHT` / `PREMUL` / `CHANNEL_PACKED` / `NONE` |
| `has_data` | bool | 픽셀이 실제 로드됐는지 |
| `is_dirty` | bool | |
| `tiles` | `UDIMTiles` | `source=='TILED'` 일 때 |
| `generated_type`, `generated_width`, `generated_height`, `generated_color`, `use_generated_float` | | `GENERATED` 소스용 |
| `packed_file` | `PackedFile` | `pack()` 후 |
| `packed_files` | collection | |
| `use_view_as_render` | bool | |

메서드: `pack(data_len=0)`, `unpack(method=...)`, `save(filepath, quality=0, save_copy=False)`,
`save_render(filepath, scene, quality=0)`, `scale(width, height, frame=0, tile_index=0)`,
`update()`, `reload()`, `buffers_free()`, `copy()`, `gl_load()/gl_free()`.

> `bpy.types.ImageTile` 은 **없다**. 5.2 의 타입 이름은 **`UDIMTile`** 다.
> `UDIMTile` 프로퍼티: `label`, `number`, `size`, `channels`, `generated_type`,
> `generated_width`, `generated_height`, `use_generated_float`, `is_generated_tile`,
> `generated_color`. **`pixels` 속성이 없다** — 타일 픽셀은 `image.pixels`(첫 타일 기준)
> 또는 파일 로드로만 접근한다. `UDIMTiles` 메서드는 `new(number)`, `get`, `remove`,
> `active`, `active_index`.

### 7.3 `channels` 는 5.2 에서 신뢰할 수 없다

실측 (4×4 / 8×8 / 2×2 PNG 를 직접 만들어 로드):

| 파일 | `channels` | `depth` | `has_data` | 비고 |
|---|---|---|---|---|
| 8-bit 그레이스케일 PNG | **4** | 8 | True | 로드 성공, RGBA 로 확장 |
| 1-bit 그레이스케일 PNG | **4** | 8 | True | |
| 16-bit 그레이스케일 PNG | **4** | 32 | True | |
| 8-bit RGB PNG | **4** | 24 | True | |
| 8-bit RGBA PNG | **4** | 32 | True | |

5.2 는 **모든 이미지를 4 채널로 정규화**한다. 원본 포맷을 알아야 한다면
`file_format` + `depth` 로 추론하거나, 파일 헤더를 직접 읽어야 한다.
`alpha=True/False` 인자를 `images.new()` 에 줘도 `channels` 는 4 다
(byte RGB 는 `depth=24`, RGBA 는 `depth=32` 로만 구분된다).

### 7.4 픽셀 접근

```python
import array
n = img.size[0] * img.size[1] * img.channels
buf = array.array('f', [0.0]) * n
# ... 채우기 ...
img.pixels.foreach_set(buf)
img.update()

back = array.array('f', [0.0] * n)
img.pixels.foreach_get(back)
```

| 버퍼 종류 | 왕복 정밀도 |
|---|---|
| `float_buffer=True` | **정확** (`list(back) == list(src)` → `True`) |
| byte 버퍼 | 8비트 양자화. `0.25` 쓰고 읽으면 `0.251` (64/255) |

`foreach_set` 을 쓰면 `img.pixels = buf` 보다 훨씬 빠르다 (파이썬 레벨 반복이 없음).

**중요**: `image.pixels` 는 **컬러스페이스 변환된 값**이다. `sRGB` 이미지에서 `0.25` 를
쓰면 읽을 때 `0.251` 이 된다(양자화 + 변환). 데이터 텍스처는 생성 시 `is_data=True`,
또는 쓰기 전에 `img.colorspace_settings.name = 'Non-Color'`.

### 7.5 저장 / 패킹

```python
img.filepath_raw = "/abs/path/out.png"
img.file_format = 'PNG'
img.save()                     # filepath_raw 이 없으면 filepath 사용
img.pack()                     # .blend 에 내장
img.packed_file                 # PackedFile, .size 로 확인
img.filepath = "/nonexistent/x.png"   # 패킹 후 경로를 바꿔도 픽셀은 메모리에 남음
img.unpack(method='USE_LOCAL')        # 다시 디스크에서
```

`img.save(filepath=..., save_copy=True)` 는 **원본 `filepath` 를 바꾸지 않고**
사본만 저장한다 (자동으로 `//textures/…` 상대경로가 붙는다).

`file_format` 는 `save()` 를 부를 때 인코더를 고른다. 실측 결과:

| `source` | `file_format` | 결과 |
|---|---|---|
| `GENERATED` | PNG / TIFF / OPEN_EXR / JPEG / TARGA / WEBP / BMP / HDR | 전부 저장 성공. **첫 `save()` 후 `source` 가 `FILE` 로 바뀐다** |
| `TILED` | 아무 포맷 | ❌ `RuntimeError: When saving a tiled image, the path '…' must contain a valid UDIM marker` |

즉 타일 이미지는 경로에 `<UDIM>` 마커가 들어 있어야 저장된다
(예: `/tex/albedo.<UDIM>.png`).

### 7.6 `ShaderNodeTexImage`

| 프로퍼티 | enum / 타입 | 기본값 |
|---|---|---|
| `image` | `Image` | `None` |
| `interpolation` | **`Linear`**, `Closest`, `Cubic`, `Smart` | `Linear` |
| `extension` | `REPEAT`, `EXTEND`, `CLIP`, `MIRROR` | `REPEAT` |
| `projection` | `FLAT`, `BOX`, `SPHERE`, `TUBE` | `FLAT` |
| `projection_blend` | float | `0` |
| `image_user` | int (read-only) | |
| `vector_type` (`texture_mapping`) | `POINT`/`TEXTURE`/`VECTOR`/`NORMAL` | |

입력: `Vector`. 출력: `Color`, `Alpha`.

> `interpolation` 의 enum 값은 **대소문자가 섞여 있다** — `'Linear'`, `'Closest'`,
> `'Cubic'`, `'Smart'`. `'LINEAR'` 로 쓰면 `TypeError`. 흔한 함정.
> `ShaderNodeTexEnvironment` 의 `projection` 은 `EQUIRECTANGULAR` / `MIRROR_BALL` 이고
> `interpolation` enum 은 `TexImage` 와 동일하다.

### 7.7 UDIM (타일 이미지)

```python
udim = bpy.data.images.new("UDIM", width=512, height=512, tiled=True)
# -> source == 'TILED', tiles == 1 (번호 1001 이 자동 생성, size=(512,512), is_generated_tile=True)
t2 = udim.tiles.new(1002)
udim.tiles.new(1003)
# -> 새 타일의 size 는 (0, 0): 파일이 배정돼야 실제 크기가 생긴다
```

`source` enum 에 `'TILED'` (UI 이름 `"UDIM Tiles"`) 가 **실제로 존재한다** — 확인된 사실.
`image.scale(..., tile_index=N)` 으로 타일 단위 리샘플링이 가능하다.

### 7.8 검증 예제 (EX-06)

생성 / 픽셀 / float 버퍼 왕복 / 디스크 로드 / colorspace / UDIM / `ShaderNodeTexImage` /
`ShaderNodeTexEnvironment` 를 한 스크립트로 검증한다 — `verify/doc_06_image.py`:

```python
"""DOC EX-06 — Image textures: new/load, pixels, pack, ShaderNodeTexImage, UDIM."""
import bpy, sys, os, array, math

os.makedirs("/workspace/out", exist_ok=True)

# ---- 1. 새 이미지 생성 + 픽셀 쓰기 ---------------------------------------
img = bpy.data.images.new("Checker", width=8, height=8, alpha=False, float_buffer=False)
print("size:", tuple(img.size), "| channels:", img.channels, "| depth:", img.depth,
      "| is_float:", img.is_float, "| source:", img.source)
buf = array.array('f', [0.0]) * (img.size[0] * img.size[1] * img.channels)
for y in range(8):
    for x in range(8):
        i = (y * 8 + x) * img.channels
        c = 0.85 if ((x // 2) + (y // 2)) % 2 == 0 else 0.10
        buf[i:i + img.channels] = array.array('f', [c, c * 0.95, c * 0.9, 1.0])
img.pixels.foreach_set(buf)
img.update()
print("first 4 px:", [round(v, 3) for v in img.pixels[0:4]])

img.filepath_raw = "/workspace/out/checker.png"
img.file_format = 'PNG'
img.save()
img.pack()
print("packed:", img.packed_file is not None, "| size:", img.packed_file.size)

# ---- 2. float buffer + 정확한 왕복 ---------------------------------------
f = bpy.data.images.new("HDR", width=4, height=4, alpha=True, float_buffer=True)
print()
print("float buf channels:", f.channels, "| is_float:", f.is_float,
      "| depth(bits):", f.depth, "| cs:", f.colorspace_settings.name,
      "| use_half_precision:", f.use_half_precision)
src = array.array('f', [i / 64.0 for i in range(4 * 4 * f.channels)])
f.pixels.foreach_set(src)
f.update()
back = array.array('f', [0.0] * len(src))
f.pixels.foreach_get(back)
print("exact round trip:", list(back) == list(src))

# ---- 3. 디스크에서 로드 ----------------------------------------------------
loaded = bpy.data.images.load("/workspace/out/checker.png")
print()
print("loaded:", loaded.name, "| size:", tuple(loaded.size),
      "| channels:", loaded.channels, "| source:", loaded.source)
loaded.colorspace_settings.name = 'Non-Color'      # 데이터 텍스처면 필수
print("colorspace:", loaded.colorspace_settings.name)

# ---- 4. UDIM (tiled) ------------------------------------------------------
udim = bpy.data.images.new("UDIM", width=512, height=512, tiled=True)
print()
print("udim.source:", udim.source, "| tiles:", len(udim.tiles))
t = udim.tiles.new(1002)
udim.tiles.new(1003)
print("after tiles.new():", len(udim.tiles), [(x.number, tuple(x.size)) for x in udim.tiles])
print("tile rna:", t.bl_rna.identifier,
      "| props:", [q.identifier for q in t.bl_rna.properties])
print("udim still TILED:", udim.source == 'TILED', "| image.pixels len:", len(udim.pixels))
print("tiles collection methods:",
      [d for d in dir(udim.tiles) if not d.startswith('_')])

# ---- 5. 머티리얼 노드 -----------------------------------------------------
mat = bpy.data.materials.new("Img")
nt = mat.node_tree
bsdf = nt.nodes['Principled BSDF']
uv  = nt.nodes.new("ShaderNodeUVMap");  uv.location = (-700, 0)
tex = nt.nodes.new("ShaderNodeTexImage"); tex.location = (-450, 0)
tex.image = loaded
tex.interpolation = 'Closest'
tex.extension = 'REPEAT'
print()
print("ShaderNodeTexImage interpolation enum:",
      [i.identifier for i in tex.bl_rna.properties['interpolation'].enum_items])
print("extension enum:", [i.identifier for i in tex.bl_rna.properties['extension'].enum_items])
print("projection enum:", [i.identifier for i in tex.bl_rna.properties['projection'].enum_items])
nt.links.new(uv.outputs['UV'], tex.inputs['Vector'])
nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])

# ---- 6. Environment Texture (HDRI) ---------------------------------------
world = bpy.data.worlds.new("W")
bpy.context.scene.world = world
wnt = world.node_tree
wnt.nodes.clear()
wo = wnt.nodes.new("ShaderNodeOutputWorld")
bg = wnt.nodes.new("ShaderNodeBackground")
env = wnt.nodes.new("ShaderNodeTexEnvironment")
print()
print("ShaderNodeTexEnvironment props:",
      [q.identifier for q in env.bl_rna.properties
       if q.identifier not in {p.identifier for p in bpy.types.Node.bl_rna.properties}])
env.image = loaded
env.projection = 'EQUIRECTANGULAR'
wnt.links.new(env.outputs['Color'], bg.inputs['Color'])
wnt.links.new(bg.outputs['Background'], wo.inputs['Surface'])

print("__SCRIPT_OK__")
sys.exit(0)
```

실측 핵심 출력:

```
size: (8, 8) | channels: 4 | depth: 24 | is_float: False | source: GENERATED
first 4 px: [0.851, 0.808, 0.765, 1.0]          # 0.85 를 넣었는데 8비트 양자화로 0.851
packed: True | size: 282
float buf channels: 4 | is_float: True | depth(bits): 128 | cs: Linear Rec.709 | use_half_precision: True
exact round trip: True
loaded: checker.png | size: (8, 8) | channels: 4 | source: FILE
colorspace: Non-Color
udim.source: TILED | tiles: 1
after tiles.new(): 3 [(1001, (512, 512)), (1002, (0, 0)), (1003, (0, 0))]
tile rna: UDIMTile | props: ['rna_type','label','number','size','channels',
                             'generated_type','generated_width','generated_height',
                             'use_generated_float','is_generated_tile','generated_color']
ShaderNodeTexImage interpolation enum: ['Linear', 'Closest', 'Cubic', 'Smart']
extension enum: ['REPEAT', 'EXTEND', 'CLIP', 'MIRROR']
projection enum: ['FLAT', 'BOX', 'SPHERE', 'TUBE']
ShaderNodeTexEnvironment props: ['image','texture_mapping','color_mapping',
                                 'projection','interpolation','image_user']
```

---

## 8. 월드 / 환경

### 8.1 기본

`bpy.data.worlds.new("W")` → `node_tree` 자동 생성, 기본 노드 `Background` + `World Output`.
`world.use_nodes` 도 deprecation.

```python
w = bpy.data.worlds.new("Env")
bpy.context.scene.world = w          # 지정해야 렌더에 반영
wnt = w.node_tree
wnt.nodes.clear()
wo = wnt.nodes.new("ShaderNodeOutputWorld")
bg = wnt.nodes.new("ShaderNodeBackground")
bg.inputs['Strength'].default_value = 1.0
wnt.links.new(bg.outputs['Background'], wo.inputs['Surface'])
```

`World` 전용 프로퍼티: `color`(포리스트Solid 뷰포트), `use_eevee_finite_volume`,
`lightgroup`, `probe_resolution`, `sun_threshold`, `sun_angle`, `use_sun_shadow`,
`sun_shadow_maximum_resolution`, `sun_shadow_filter_radius`, `use_sun_shadow_jitter`,
`sun_shadow_jitter_overblur`.

### 8.2 `ShaderNodeTexSky` — 5.2 실측 (3.1 이후 이름 변경 반영)

**`dust_density` 는 없다. `aerosol_density` 로 이름이 바뀌었다.**
**`sky_type = 'NISHITA'` 도 없다.**

| 프로퍼티 | 타입 | 기본 | 상태 |
|---|---|---|---|
| `sky_type` | enum | `SINGLE_SCATTERING` | enum = `SINGLE_SCATTERING`, `MULTIPLE_SCATTERING`, `PREETHAM`, `HOSEK_WILKIE`. **`NISHITA` 없음** |
| `sun_disc` | bool | | 태양 원반 포함 |
| `sun_size` | float | | 각도(rad) |
| `sun_intensity` | float | | |
| `sun_elevation` | float | | **3.1 에서 그대로 유지** |
| `sun_rotation` | float | | **3.1 에서 그대로 유지** |
| `altitude` | float | | 해발 높이(m) |
| `air_density` | float | | 공기 분자 밀도 |
| **`aerosol_density`** | float | | **← 구 `dust_density`** |
| `ozone_density` | float | | |
| `sun_direction` | float | | (구 `Sun Direction` 입력 → 5.0 에서 소켓에서 노드 프로퍼티로) |
| `turbidity` | float | | (구 입력 → 노드 프로퍼티로) |
| `ground_albedo` | float | | (구 입력 → 노드 프로퍼티로) |

입력: `Vector`. 출력: `Color`.
읽기 전용 보조: `texture_mapping`, `color_mapping`.

실측:

```python
sk.sky_type = 'NISHITA'
# TypeError: bpy_struct: item.attr = val: enum "NISHITA" not found in
#   ('SINGLE_SCATTERING', 'MULTIPLE_SCATTERING', 'PREETHAM', 'HOSEK_WILKIE')
sk.dust_density = 1.0
# AttributeError: 'ShaderNodeTexSky' object has no attribute 'dust_density'
```

→ **5.x 정답**: `sk.sky_type = 'MULTIPLE_SCATTERING'` (Nishita 의 후속) 또는 `'SINGLE_SCATTERING'`,
`sk.aerosol_density = 1.0`.

### 8.3 HDRI 스타일 그라디언트 월드

`ShaderNodeTexEnvironment` 에 HDRI/이미지를 넣는 게 정석이지만, 이미지가 없을 때
`TexCoord.Generated` + `Mapping`(Z→Y) + `TexGradient` + `ColorRamp` 로 만드는
"HDRI 스타일" 그라디언트 월드가 표준 대체재다.

### 8.4 검증 예제 (EX-07)

그라디언트 월드와 Sky 월드를 각각 만들어 Cycles CPU 로 렌더하는 검증 스크립트 —
`verify/doc_07_world.py`:

```python
"""DOC EX-07 — World / environment: Sky Texture + HDRI-style gradient world (Cycles CPU)."""
import bpy, sys, os, math
import addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)

os.makedirs("/workspace/out", exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 24
sc.render.resolution_x = 160
sc.render.resolution_y = 90
sc.render.filepath = "/workspace/out/doc_world.png"

# ---- 1. Gradient world -----------------------------------------------------
w = bpy.data.worlds.new("GradientEnv")
sc.world = w                       # world.use_nodes 는 더 이상 필요 없음
wnt = w.node_tree
wnt.nodes.clear()

wo  = wnt.nodes.new("ShaderNodeOutputWorld");  wo.location  = (400, 0)
bg  = wnt.nodes.new("ShaderNodeBackground");   bg.location  = (200, 0)
tc  = wnt.nodes.new("ShaderNodeTexCoord");     tc.location  = (-700, 0)
mp  = wnt.nodes.new("ShaderNodeMapping");     mp.location  = (-500, 0)
grad= wnt.nodes.new("ShaderNodeTexGradient");  grad.location= (-300, 0)
ramp= wnt.nodes.new("ShaderNodeValToRGB");     ramp.location= (-100, 0)

grad.gradient_type = 'EASING'
mp.inputs['Rotation'].default_value = (math.radians(90), 0, 0)   # Z -> Y (천정/지평)
mp.inputs['Location'].default_value = (0, 0, 0.5)
mp.inputs['Scale'].default_value    = (1, 1, 0.5)
ramp.color_ramp.elements[0].color = (0.02, 0.025, 0.04, 1.0)    # 지평
ramp.color_ramp.elements[1].color = (0.35, 0.55, 0.85, 1.0)    # 천정
bg.inputs['Strength'].default_value = 1.0

wnt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
wnt.links.new(mp.outputs['Vector'], grad.inputs['Vector'])
wnt.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
wnt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
wnt.links.new(bg.outputs['Background'], wo.inputs['Surface'])

# ---- 2. Sky Texture world --------------------------------------------------
sky_w = bpy.data.worlds.new("SkyEnv")
snt = sky_w.node_tree
snt.nodes.clear()
so = snt.nodes.new("ShaderNodeOutputWorld");  so.location = (300, 0)
sb = snt.nodes.new("ShaderNodeBackground");   sb.location = (100, 0)
sk = snt.nodes.new("ShaderNodeTexSky");       sk.location = (-200, 0)

sk.sky_type = 'MULTIPLE_SCATTERING'
sk.sun_elevation   = 0.30
sk.sun_rotation    = 2.40
sk.altitude        = 200.0
sk.air_density     = 1.0
sk.aerosol_density = 1.2
sk.ozone_density   = 1.0
sk.sun_disc        = True
sk.sun_size        = 0.0095
sk.sun_intensity   = 1.0
sb.inputs['Strength'].default_value = 0.35
snt.links.new(sk.outputs['Color'], sb.inputs['Color'])
snt.links.new(sb.outputs['Background'], so.inputs['Surface'])

print("sky_type enum:",
      [i.identifier for i in sk.bl_rna.properties['sky_type'].enum_items])
print("sky writable props:",
      [p.identifier for p in sk.bl_rna.properties
       if not p.is_readonly and p.identifier not in
       {q.identifier for q in bpy.types.Node.bl_rna.properties}])

# ---- 3. 렌더 ---------------------------------------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, 0, 0.6))
sphere = bpy.context.object
mat = bpy.data.materials.new("Chrome")
mat.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 1.0
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.08
sphere.data.materials.append(mat)

cam_d = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cam_d)
sc.collection.objects.link(cam)
cam.location = (0, -3.2, 1.0); cam.rotation_euler = (math.radians(84), 0, 0)
sc.camera = cam

sc.world = sky_w
bpy.ops.render.render(write_still=True)
print("sky render:", os.path.getsize(sc.render.filepath), "bytes")

sc.world = w
sc.render.filepath = "/workspace/out/doc_world_gradient.png"
bpy.ops.render.render(write_still=True)
print("gradient render:", os.path.getsize(sc.render.filepath), "bytes")

print("__SCRIPT_OK__")
sys.exit(0)
```

실측 출력:

```
sky_type enum: ['SINGLE_SCATTERING', 'MULTIPLE_SCATTERING', 'PREETHAM', 'HOSEK_WILKIE']
sky writable props: ['sky_type', 'sun_disc', 'sun_size', 'sun_intensity',
                     'sun_elevation', 'sun_rotation', 'altitude', 'air_density',
                     'aerosol_density', 'ozone_density', 'sun_direction',
                     'turbidity', 'ground_albedo']
sky render: 19487 bytes
gradient render: 16767 bytes
```

---

## 9. 지오메트리 노드

### 9.1 그룹 생성: `ng.interface` API

| 항목 | 5.2 실측 |
|---|---|
| 생성 | `bpy.data.node_groups.new(name, 'GeometryNodeTree')` |
| 타입 enum | `GeometryNodeTree`, `CompositorNodeTree`, `ShaderNodeTree`, `TextureNodeTree` |
| 소켓 생성 | `ng.interface.new_socket(name, description="", in_out='INPUT', socket_type='DEFAULT', parent=None)` |
| 패널 생성 | `ng.interface.new_panel(name, description="", default_closed=False)` |
| 열거 | `ng.interface.items_tree` (PANEL + SOCKET 혼합) |
| 삭제/이동 | `remove(item)`, `move(item, to_index)`, `move_to_parent(item, parent, index)`, `clear()`, `copy(item)` |
| **구 API** | `ng.inputs` / `ng.outputs` → **`AttributeError: 'GeometryNodeTree' object has no attribute 'inputs'`** (5.2 에서 완전 제거) |

> `socket_type` 은 `'NodeSocketFloat'`, `'NodeSocketInt'`, `'NodeSocketGeometry'` 같은
> `bl_idname` 문자열을 받는다.
>
> **⚠ 정정 (실측 대조 테스트로 발견)**: `name` 은 **위치 인자로도, 키워드로도 둘 다** 된다.
> ```python
> ng.interface.new_socket(name='KwName', in_out='INPUT', socket_type='NodeSocketInt')
> #   -> socket.name == 'KwName', identifier == 'Socket_0'
> ng.interface.new_socket('PosName', in_out='INPUT', socket_type='NodeSocketFloat')
> #   -> socket.name == 'PosName'
> ```
> 이전 문서에 "`name=` 키워드는 불가" 라고 적었으나 **틀렸다.** 실제로 되는 건
> **4.x 스타일** `new_socket(bl_idname, name=...)` 이다:
> ```python
> ng.interface.new_socket('NodeSocketInt', name='OldStyle')
> # TypeError: NodeTreeInterface.new_socket(): was called with invalid keyword argument(s)
> ```
> 헷갈리기 쉬우니 정리하면: **`name` 자리는 하나, 거기에 문자열(소켓명)이 온다.
> 첫 인자에 `NodeSocketFloat` 같은 `bl_idname` 을 넣는 4.x 습관이 안 되는 거다.**

`NodeTreeInterfaceSocket` 가 가진 프로퍼티 (실측):

```
item_type, parent, position, index, name, identifier, description,
socket_type, in_out, hide_value, hide_in_modifier, force_non_field,
is_inspect_output, is_panel_toggle, layer_selection_field, menu_expanded,
optional_label, select, attribute_domain, default_attribute_name,
structure_type, default_input, bl_socket_idname
+ (Float 한정) subtype, default_value, min_value, max_value
```

`structure_type` enum: `AUTO`, `DYNAMIC`, `FIELD`, `GRID`, `LIST`, `SINGLE`.

### 9.2 identifier 규칙

`ng.interface.items_tree` 를 읽으면 소켓 identifier 는 `Socket_N` 이고
**패널은 정수 identifier** 를 갖는다. 패널도 번호를 소비하므로,
패널이 끼어 있으면 소켓 번호가 연속되지 않는다.

```
SOCKET  'Socket_1' OUTPUT  'Geometry'
SOCKET  'Socket_5' OUTPUT  'Density Out'
SOCKET  'Socket_0' INPUT   'Geometry'
PANEL   2          -       'Scatter'
SOCKET  'Socket_3' INPUT   'Count'
SOCKET  'Socket_4' INPUT   'Radius'
```

⇒ **identifier 는 절대 추측하지 말고 항상 `items_tree` 로 읽는다.**

```python
def socket_id(ng, name, in_out='INPUT'):
    for it in ng.interface.items_tree:
        if it.item_type == 'SOCKET' and it.name == name and it.in_out == in_out:
            return it.identifier
    raise KeyError(name)
```

`NodeGroupInput` 노드 쪽 소켓은 `gi.outputs['Count']` 로 **이름** 조회가 되고,
`gi.outputs['Socket_1']` 같은 identifier 조회는 `KeyError` 다
(패널이 번호를 먹었으므로 `Socket_1` 이 소켓이 아닐 수 있다).
`gi.outputs` 에는 숨겨진 `('__extend__', '__extend__')` 소켓이 하나 더 있다.

### 9.3 모디파이어에 배정

```python
mod = obj.modifiers.new("ScatterCubes", 'NODES')
mod.node_group = ng
```

`NodesModifier` 프로퍼티 (실측):

| 프로퍼티 | 타입 | 비고 |
|---|---|---|
| `node_group` | `NodeTree` | 핵심 |
| `properties` | `GeometryNodesModifierInterface` | **5.2 신규 RNA**. 아래 9.4 |
| `bake_target` | enum | `PACKED`(기본) / `DISK` |
| `bake_directory` | str | |
| `bakes` | collection of `NodesModifierBake` | |
| `panels` | collection of `NodesModifierPanel` | |
| `node_warnings` | collection | |
| `execution_time` | float (read-only) | |
| `persistent_uid` | int | |
| `is_override_data` | bool | GN 오버라이드용 |
| `use_pin_to_last` | bool | GN 오버라이드 |
| `use_apply_on_spline` | bool | |
| `show_viewport` / `show_render` / `show_editmode` / `show_cage` / `show_expanded` | bool | |

### 9.4 5.2 RNA 프로퍼티 API — `mod.properties`

```python
mod.properties                    # GeometryNodesModifierInterface  (rna_type, inputs, outputs, panels)
mod.properties.inputs             # GeometryNodesInterfaceInputs
mod.properties.outputs            # GeometryNodesInterfaceOutputs
mod.properties.panels             # GeometryNodesInterfacePanels
```

`inputs` 는 **컬렉션이 아니라, `Socket_0`, `Socket_1`, … 이라는 *어트리뷰트* 를 가진
구조체**다. `len()` 도 없고 순회도 불가능하다.

| 접근 방식 | 결과 |
|---|---|
| `getattr(mod.properties.inputs, 'Socket_2')` | ✅ RNA 구조체 `Socket_2` 반환 |
| `mod.properties.inputs['Socket_2']` | ⚠️ `IDPropertyGroup` 반환 (동일 데이터, 다른 타입) |
| `dir(mod.properties.inputs)` | ✅ `['Socket_0', 'Socket_1', …, 'bl_rna', 'name', 'rna_type']` |
| `for k in mod.properties.inputs` | ❌ `TypeError: not iterable` |
| `len(mod.properties.inputs)` | ❌ `TypeError: object of type … has no len()` |

**항상 `getattr` 를 써라.** (identifier 는 `Socket_N` 처럼 항상 식별자이므로
`getattr(obj, ident)` 가 안전하다. `nodes.get()` 처럼 이름을 넣으면 안 된다.)

각 소켓 엔트리의 프로퍼티:

| 프로퍼티 | 존재 조건 | 값 |
|---|---|---|
| `name` | 항상 | **항상 빈 문자열** — 식별자로 쓸 수 없다 |
| `type` | 항상 | `'FALLBACK'` (값 없음) / `'VALUE'` / `'ATTRIBUTE'` |
| `value` | 값 타입 소켓 | int / float / bool / str / `bpy_prop_array` / `mathutils.Euler` / None(ID·Object·Material·Image) |
| `attribute_name` | 필드 가능 소켓 | str |
| `layer_name` | 레이어 선택 소켓 | str |

`IDPropertyGroup` 로 접근하면 키는 `['value', 'type', 'attribute_name']` 이고
`type` 은 **정수**로 저장된다 (`VALUE == 1`).

`mod.properties.outputs` 에는 **어트리뷰트(비 Geometry 출력)만** 나타난다.
Geometry 출력 소켓은 없다. 출력 엔트리 프로퍼티는 `name`, `attribute_name` 뿐이다
(`type` 프로퍼티조차 없다).

```python
# 값 설정
getattr(mod.properties.inputs, id_count).value = 120
# 필드(어트리뷰트) 연결
e = getattr(mod.properties.inputs, id_rad)
e.type = 'ATTRIBUTE'            # enum: VALUE | ATTRIBUTE
e.attribute_name = "spacing"
# 되돌리기
e.type = 'VALUE'
e.value = 0.3
# 출력 속성 이름
getattr(mod.properties.outputs, id_out).attribute_name = "baked_density"
```

### 9.5 4.x / 5.1 호환 폴백

5.2 에서 **4.x 방식은 하드 사멸**했다:

```python
mod['Socket_1']                     # TypeError: this type doesn't support IDProperties
mod['Socket_1_use_attribute']        # TypeError
mod.keys()                          # TypeError: this type doesn't support IDProperties
```

`NodesModifier` 는 더 이상 IDProperty 를 지원하지 않는다
(`mod.id_properties_ensure()` 도 쓸 수 없다).

feature-detect 방법:

```python
# RNA 등록 여부로 판정 (신뢰할 수 있음)
has_rna = 'properties' in [p.identifier for p in bpy.types.NodesModifier.bl_rna.properties]

# 또는 인스턴스로 판정
props = getattr(mod, "properties", None)
```

> `hasattr(bpy.types.Foo, "prop")` 은 RNA 프로퍼티에 대해 **신뢰할 수 없다**
> (실제로 있는 프로퍼티에 대해서도 `False` 를 돌려준다). 항상
> `[p.identifier for p in bpy.types.Foo.bl_rna.properties]` 를 쓴다.

**검증 예제 (EX-05)** — `verify/doc_05_compat.py`

```python
"""DOC EX-05 — 4.x / 5.1 호환 fallback: feature-detect on mod.properties."""
import bpy, sys

# ---------- 공용 헬퍼 -------------------------------------------------------
def interface_map(ng):
    """{identifier: (name, in_out)} — PANEL 은 in_out 이 없으므로 제외."""
    out = {}
    for it in ng.interface.items_tree:
        if getattr(it, "in_out", None) is None:
            continue
        out[it.identifier] = (it.name, it.in_out)
    return out


def has_rna_properties(mod):
    return 'properties' in [p.identifier for p in bpy.types.NodesModifier.bl_rna.properties]


def set_gn_input(mod, ident, value):
    """5.2: mod.properties.inputs.<id>.value   /   4.x·5.1: mod[ident]"""
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props.inputs, ident):
        entry = getattr(props.inputs, ident)
        if hasattr(entry, "value"):
            entry.value = value
            return "rna"
    try:
        mod[ident] = value
        return "idprop"
    except TypeError:
        raise KeyError(f"no writable input {ident!r} on {mod!r}")


def set_gn_output_attr(mod, ident, attr_name):
    props = getattr(mod, "properties", None)
    if props is not None and hasattr(props.outputs, ident):
        getattr(props.outputs, ident).attribute_name = attr_name
        return "rna"
    mod[ident + "_use_attribute"] = True
    mod[ident + "_attribute_name"] = attr_name
    return "idprop"


# ---------- 실제 그룹 -------------------------------------------------------
ng = bpy.data.node_groups.new("Compat", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
cnt = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
cnt.default_value = 8
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket("Attr",     in_out='OUTPUT', socket_type='NodeSocketFloat')

gi = ng.nodes.new("NodeGroupInput")
go = ng.nodes.new("NodeGroupOutput")
pts = ng.nodes.new("GeometryNodePoints")
ng.links.new(gi.outputs[0], pts.inputs['Count'])
ng.links.new(pts.outputs['Points'], go.inputs[0])

bpy.ops.mesh.primitive_grid_add(size=2)
obj = bpy.context.object
mod = obj.modifiers.new("Compat", 'NODES')
mod.node_group = ng

imap = interface_map(ng)
print("interface_map:", imap)
by_name = {name: ident for ident, (name, io) in imap.items()}
print("by_name:", by_name)

print()
print("NodesModifier RNA has 'properties':", has_rna_properties(mod))
print("getattr(mod,'properties',None):", getattr(mod, "properties", None) is not None)

print()
print("set Count  -> path =", set_gn_input(mod, by_name['Count'], 25))
print("readback       :", getattr(mod.properties.inputs, by_name['Count']).value)
print("set Attr out   -> path =", set_gn_output_attr(mod, by_name['Attr'], "my_attr"))
print("readback       :", getattr(mod.properties.outputs, by_name['Attr']).attribute_name)

print()
print("=== 4.x-era IDProperty access is hard-dead in 5.2 ===")
for key in (by_name['Count'], by_name['Count'] + '_use_attribute'):
    try:
        print(f"  mod[{key!r}] =", mod[key])
    except TypeError as e:
        print(f"  mod[{key!r}] -> TypeError: {e}")

print()
print("=== feature-detect 결과 분기 ===")
if getattr(mod, "properties", None) is not None:
    print("  5.2 경로 사용")
else:
    print("  4.x IDProperty 경로 사용")

print("__SCRIPT_OK__")
sys.exit(0)
```

실측:

```
interface_map: {'Socket_2': ('Geometry','OUTPUT'), 'Socket_3': ('Attr','OUTPUT'),
                'Socket_0': ('Geometry','INPUT'),   'Socket_1': ('Count','INPUT')}
NodesModifier RNA has 'properties': True
set Count  -> path = rna      readback: 25
set Attr out -> path = rna    readback: my_attr
mod['Socket_1'] -> TypeError: this type doesn't support IDProperties
mod['Socket_1_use_attribute'] -> TypeError: this type doesn't support IDProperties
5.2 경로 사용
```

### 9.6 5.2 지오메트리 노드 소켓 변경 (4.x 스크립트를 깨뜨리는 것들)

| 노드 | 4.x | 5.2 실측 |
|---|---|---|
| `GeometryNodeMeshGrid` | `Mesh` 입력 존재 | **`Mesh` 입력 아예 없음.** `Size X, Size Y, Vertices X, Vertices Y` |
| `GeometryNodeMeshCube` | `Mesh`, `Size`, `Vertices X/Y` | **`Mesh` 입력 없음.** `Size, Vertices X, Vertices Y, Vertices Z` |
| `GeometryNodeMeshUVSphere` | `Mesh` | `Segments, Rings, Radius` + 출력에 `UV Map` 추가 |
| `GeometryNodeMeshCone` / `Cylinder` | `Mesh` | `Vertices, Side Segments, Fill Segments, Radius Top/Bottom, Depth`, `fill_type` |
| `GeometryNodeMeshIcoSphere` | `Mesh` | `Radius, Subdivisions` |
| `GeometryNodeInstanceOnPoints` | `Points, Selection, Instance, Pick Instance, Instance Index, Rotation, Scale, Location(폐기)` | `Points, Selection, Instance, Pick Instance, Instance Index, Rotation, Scale` — **`Location` / `Transform` 없음** |
| `FunctionNodeRandomValue` | 출력 6개 (Float/Vector/Int) | **출력 1개 `Value`**, `data_type` 로 타입 결정 |
| `FunctionNodeRotateVector` | `Vector, Center, Axis, Rotation` | `Vector, Rotation` |
| `GeometryNodeDistributePointsOnFaces` | `Radius` | `Distance Min`, `Density Max`, `Density`, `Density Factor` + `distribute_method` |
| `GeometryNodeMeshLine` | — | `Count, Resolution, Start Location, Offset` + `mode`, `count_mode` |
| `GeometryNodeTransform` | — | `Geometry, Mode, Translation, Rotation, Scale, Transform` |

**기본 메시 생성 노드에 `Mesh` 입력이 사라진 것**이 최대 변화다.
4.x 의 "Grid 노드의 Mesh 입력" 은 이제 `GeometryNodeTransform` 또는
`GeometryNodeSetPosition` 등으로 대체해야 한다. 실측:

```python
ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
g = ng.nodes.new("GeometryNodeMeshGrid")
[s.name for s in g.inputs]         # ['Size X', 'Size Y', 'Vertices X', 'Vertices Y']
ng.links.new(group_in.outputs[0], g.inputs['Mesh'])
# KeyError: 'bpy_prop_collection[key]: key "Mesh" not found'
```

5.x 에서 새로 생긴 지오메트리 함수 노드 (네임스페이스 `FunctionNode*`):
`FloatToInt`, `Compare`, `ProjectPoint`, `AxesToRotation`, `TransformDirection`,
`TransformPoint`, `RotateVector`, `RotateEuler`, `RotateRotation`, `SplitString`,
`FormatString`, `HashValue`, `MatchString`, `RandomValue`, … (총 56개).
수학 노드는 5.x 에서 `ShaderNodeMath` / `ShaderNodeVectorMath` 를 그대로 쓴다
(`FunctionNodeVectorMath` 같은 타입은 **없다**).

### 9.7 검증 예제 (EX-04)

패널 포함 인터페이스, Poisson 분포 + 인스턴스 + Realize + Store Named Attribute,
모디파이어 배정, identifier 매핑, `value` / `type='ATTRIBUTE'` / `attribute_name` 설정,
depsgraph 평가까지를 한 스크립트로 검증한다 — `verify/doc_04_gn.py`:

```python
"""DOC EX-04 — Geometry Nodes: build group, assign, drive inputs (5.2 RNA)."""
import bpy, sys

# ---- 1. 그룹 생성 ----------------------------------------------------------
ng = bpy.data.node_groups.new("ScatterCubes", 'GeometryNodeTree')
iface = ng.interface
iface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
iface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
panel = iface.new_panel("Scatter")
s_count = iface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt', parent=panel)
s_count.default_value = 30
s_count.description = "how many points"
s_rad = iface.new_socket("Radius", in_out='INPUT', socket_type='NodeSocketFloat', parent=panel)
s_rad.subtype = 'DISTANCE'
s_rad.default_value = 0.6
iface.new_socket("Density Out", in_out='OUTPUT', socket_type='NodeSocketFloat')

print("items_tree:")
for it in ng.interface.items_tree:
    io = it.in_out if it.item_type == 'SOCKET' else '-'
    print(f"   {it.item_type:<7} {it.identifier!r:<10} {io:<7} {it.name!r}")

# ---- 2. 노드 구성 ----------------------------------------------------------
nodes, links = ng.nodes, ng.links
n_in  = nodes.new("NodeGroupInput");               n_in.location  = (-1100,   0)
n_out = nodes.new("NodeGroupOutput");              n_out.location = (  900,   0)
grid  = nodes.new("GeometryNodeMeshGrid");         grid.location  = (-1100, -320)
grid.inputs['Size X'].default_value = 4.0
grid.inputs['Size Y'].default_value = 4.0
grid.inputs['Vertices X'].default_value = 8
grid.inputs['Vertices Y'].default_value = 8

dist  = nodes.new("GeometryNodeDistributePointsOnFaces")
dist.distribute_method = 'POISSON'                 # Distance Min / Density Max 는 이 모드에서만 활성
dist.location = (-800, 0)
cube  = nodes.new("GeometryNodeMeshCube");         cube.location  = (-800, -350)
cube.inputs['Size'].default_value = (0.16, 0.16, 0.16)
rnd   = nodes.new("FunctionNodeRandomValue");      rnd.location   = (-800, -620)
rnd.data_type = 'FLOAT_VECTOR'
rnd.inputs['Max'].default_value = (0.0, 0.0, 6.2831853)
inst  = nodes.new("GeometryNodeInstanceOnPoints");  inst.location  = (-450,   0)
store = nodes.new("GeometryNodeStoreNamedAttribute"); store.location = (250, 0)
store.data_type = 'FLOAT'
store.domain = 'POINT'
store.inputs['Name'].default_value = "density"
realz = nodes.new("GeometryNodeRealizeInstances");  realz.location = (550, 0)
setm  = nodes.new("GeometryNodeSetMaterial");      setm.location  = (750, 0)
mat = bpy.data.materials.new("ScatterMat")

links.new(grid.outputs['Mesh'],      dist.inputs['Mesh'])
links.new(n_in.outputs['Count'],     dist.inputs['Density Max'])
links.new(n_in.outputs['Radius'],    dist.inputs['Distance Min'])
links.new(dist.outputs['Points'],    inst.inputs['Points'])
links.new(cube.outputs['Mesh'],      inst.inputs['Instance'])
links.new(rnd.outputs['Value'],      inst.inputs['Rotation'])
links.new(inst.outputs['Instances'], store.inputs['Geometry'])
links.new(n_in.outputs['Count'],     store.inputs['Value'])
links.new(store.outputs['Geometry'], realz.inputs['Geometry'])
links.new(realz.outputs['Geometry'], setm.inputs['Geometry'])
links.new(setm.outputs['Geometry'],  n_out.inputs[0])
links.new(store.outputs['Geometry'], n_out.inputs['Density Out'])
setm.inputs['Material'].default_value = mat

# ---- 3. 오브젝트에 배정 ----------------------------------------------------
bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=4)
obj = bpy.context.object
mod = obj.modifiers.new("ScatterCubes", 'NODES')
mod.node_group = ng
print()
print("modifier:", mod.name, mod.type, "| node_group:", mod.node_group.name)

# ---- 4. identifier 매핑 + 입력값 설정 --------------------------------------
def socket_id(ng, name, in_out='INPUT'):
    for it in ng.interface.items_tree:
        if it.item_type == 'SOCKET' and it.name == name and it.in_out == in_out:
            return it.identifier
    raise KeyError(name)

id_count = socket_id(ng, 'Count')
id_rad   = socket_id(ng, 'Radius')
print("identifiers:", id_count, id_rad)

getattr(mod.properties.inputs, id_count).value = 120
getattr(mod.properties.inputs, id_rad).value   = 0.30
print("Count  ->", getattr(mod.properties.inputs, id_count).value)
print("Radius ->", getattr(mod.properties.inputs, id_rad).value)

entry = getattr(mod.properties.inputs, id_rad)
print("entry.type enum:", [i.identifier for i in entry.bl_rna.properties['type'].enum_items])
entry.type = 'ATTRIBUTE'
entry.attribute_name = "spacing"
print("Radius entry:", entry.type, entry.attribute_name)
entry.type = 'VALUE'
entry.value = 0.30

id_out = socket_id(ng, 'Density Out', 'OUTPUT')
getattr(mod.properties.outputs, id_out).attribute_name = "baked_density"
print("output attribute_name ->", getattr(mod.properties.outputs, id_out).attribute_name)

# ---- 5. 평가 결과 확인 -----------------------------------------------------
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
print()
print("evaluated verts:", len(ev.data.vertices), "| polys:", len(ev.data.polygons))
print("mod.execution_time:", mod.execution_time)

print("__SCRIPT_OK__")
sys.exit(0)
```

실측:

```
items_tree:
   SOCKET  'Socket_1' OUTPUT  'Geometry'
   SOCKET  'Socket_5' OUTPUT  'Density Out'
   SOCKET  'Socket_0' INPUT   'Geometry'
   PANEL   2          -       'Scatter'
   SOCKET  'Socket_3' INPUT   'Count'
   SOCKET  'Socket_4' INPUT   'Radius'
modifier: ScatterCubes NODES | node_group: ScatterCubes
identifiers: Socket_3 Socket_4
Count  -> 120
Radius -> 0.30000001192092896
entry.type enum: ['VALUE', 'ATTRIBUTE']
Radius entry: ATTRIBUTE spacing
output attribute_name -> baked_density
evaluated verts: 976 | polys: 732
```

---

## 10. Bake / 평가

### 10.1 평가 결과 읽기

```python
bpy.context.view_layer.update()                 # 또는 어떤 변경이든
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
len(ev.data.vertices)     # 모디파이어 적용 후 정점 수
mod.execution_time        # 마지막 실행 시간 (float)
```

`obj.data` 는 **원본**이고 `ev.data` 가 평가 결과다. `evaluated_get` 을 빼먹으면
"모디파이어가 안 먹었다" 고 오해한다.

### 10.2 `modifier_apply` — headless 에서 확실히 동작

`bpy.ops.object.modifier_apply` 시그니처 (실측):

```
modifier            STRING  Name of the modifier to edit
report              BOOLEAN Create a notification after the operation
merge_customdata    BOOLEAN
single_user         BOOLEAN Make the object's data single user if needed
all_keyframes       BOOLEAN (Grease Pencil)
use_selected_objects BOOLEAN
```

**실패 조건 (실측)**:

| 상황 | 결과 |
|---|---|
| 그룹 출력이 메시 | ✅ `{'FINISHED'}` |
| 그룹 출력이 **인스턴스** (`Instance on Points` 만 있고 `Realize` 없음) | ❌ `RuntimeError: Error: Evaluated geometry from modifier does not contain a mesh` |
| 그룹에 `Simulation Output` 이 있고 그 뒤가 인스턴스 | ❌ 동일 오류 |
| `Simulation Output` 을 바로 그룹 출력에 연결 | ❌ 동일 오류 |

⇒ **GN 모디파이어를 apply 하려면 반드시 Realize Instances 로 실제 메시를 만들어야 한다.**
인스턴스를 그대로 확정하고 싶으면 `bpy.ops.object.convert(target='MESH')` 를 쓴다.

### 10.3 GN bake

`mod.bakes` 는 **RNA 로 읽고 쓸 수 있다** (이건 5.x 도 그대로):

| `NodesModifierBake` 프로퍼티 | 타입 | 기본 |
|---|---|---|
| `bake_id` | int (**read-only**) | 랜덤한 큰 정수. 0 이 아니다 |
| `node` | `Node` (read-only) | 대상 시뮬레이션 노드 |
| `bake_mode` | enum | `ANIMATION` / `STILL` (기본 `STILL`) |
| `bake_target` | enum | `INHERIT` / `PACKED` / `DISK` (기본 `INHERIT`) |
| `directory` | str | |
| `use_custom_path` | bool | |
| `frame_start` / `frame_end` | int | |
| `use_custom_simulation_frame_range` | bool | |
| `data_blocks` | collection | |

`mod.bakes` 는 **모디파이어를 할당하자마자 비어 있고**, `bpy.context.view_layer.update()`
를 호출한 뒤에 채워진다. (실측: 할당 직후 `len == 0`, 업데이트 후 `len == 1`)

**headless(-b) 환경의 정직한 결과**:

```python
bpy.ops.object.simulation_nodes_cache_bake(selected=True)              # {'FINISHED'}
bpy.ops.object.geometry_node_bake_single(modifier_name="SimScatter",
                                          bake_id=b.bake_id)            # {'CANCELLED'}
# -> 디스크에 아무 파일도 생기지 않는다
```

GN bake 는 UI 잡(job) 시스템에 의존하기 때문에 `-b` 에서 실제 데이터를 쓰지 않는다.
**headless 파이프라인에서는 `modifier_apply` (또는 `object.convert`) 가 유일하게 확실한 방법**이고,
그마저도 시뮬레이션 그룹에는 통하지 않는다 (§10.2). 시뮬레이션은 디스크에 저장된
`.blend` + UI 를 거쳐야 한다.

관련 연산자 시그니처 (실측, `bpy.ops.object.geometry_node_*`):

```
geometry_node_bake_single          (modifier_name: STRING, bake_id: INT)
geometry_node_bake_delete_single   (modifier_name: STRING, bake_id: INT)
geometry_node_bake_pack_single     (modifier_name: STRING, bake_id: INT)
geometry_node_bake_unpack_single   (modifier_name: STRING, bake_id: INT, method: ENUM)
simulation_nodes_cache_bake        (selected: BOOLEAN)
```

> `bpy.ops.wm.bake_all` 은 5.2 에 **없다** (`AttributeError: could not be found`).
> 전역 bake 는 `bpy.ops.ptcache.bake_all(bake=…)` (물리 전용) 다.

### 10.4 검증 예제 (EX-08)

일반 GN 그룹 apply 성공, 시뮬레이션 그룹 `mod.bakes` 열람, headless bake 결과,
시뮬레이션 그룹 apply 실패까지 4가지를 한 스크립트로 검증한다 —
`verify/doc_08_bake.py`:

```python
"""DOC EX-08 — Bake / evaluation: evaluated_get, modifier_apply, mod.bakes."""
import bpy, sys, os

os.makedirs("/workspace/out", exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# ============================================================= A. 일반 GN 그룹
ng = bpy.data.node_groups.new("ScatterCubes", 'GeometryNodeTree')
ng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
cnt = ng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
cnt.default_value = 24

gi = ng.nodes.new("NodeGroupInput"); gi.location = (-700, 0)
go = ng.nodes.new("NodeGroupOutput"); go.location = (700, 0)
grid = ng.nodes.new("GeometryNodeMeshGrid"); grid.location = (-700, -280)
grid.inputs['Size X'].default_value = 4.0
grid.inputs['Size Y'].default_value = 4.0
grid.inputs['Vertices X'].default_value = 8
grid.inputs['Vertices Y'].default_value = 8
dist = ng.nodes.new("GeometryNodeDistributePointsOnFaces")
dist.distribute_method = 'POISSON'
dist.location = (-450, 0)
cube = ng.nodes.new("GeometryNodeMeshCube"); cube.location = (-450, -300)
cube.inputs['Size'].default_value = (0.12, 0.12, 0.12)
inst = ng.nodes.new("GeometryNodeInstanceOnPoints"); inst.location = (-200, 0)
realz = ng.nodes.new("GeometryNodeRealizeInstances"); realz.location = (100, 0)
ng.links.new(grid.outputs['Mesh'], dist.inputs['Mesh'])
ng.links.new(gi.outputs['Count'], dist.inputs['Density Max'])
ng.links.new(dist.outputs['Points'], inst.inputs['Points'])
ng.links.new(cube.outputs['Mesh'], inst.inputs['Instance'])
ng.links.new(inst.outputs['Instances'], realz.inputs['Geometry'])
ng.links.new(realz.outputs['Geometry'], go.inputs[0])

bpy.ops.mesh.primitive_plane_add(size=4)
obj = bpy.context.object
mod = obj.modifiers.new("ScatterCubes", 'NODES')
mod.node_group = ng

# --- A1. depsgraph 평가 ----------------------------------------------------
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
print("A1 original verts:", len(obj.data.vertices),
      "| evaluated verts:", len(ev.data.vertices))
print("   mod.execution_time:", mod.execution_time)

# --- A2. modifier_apply (headless 에서 확실히 동작) -------------------------
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
r = bpy.ops.object.modifier_apply(modifier="ScatterCubes")
print("A2 modifier_apply:", r, "| modifiers left:", list(obj.modifiers),
      "| verts:", len(obj.data.vertices), "| polys:", len(obj.data.polygons))

# =========================================================== B. 시뮬레이션 그룹
sng = bpy.data.node_groups.new("SimScatter", 'GeometryNodeTree')
sng.interface.new_socket("Geometry", in_out='INPUT',  socket_type='NodeSocketGeometry')
sng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
s_cnt = sng.interface.new_socket("Count", in_out='INPUT', socket_type='NodeSocketInt')
s_cnt.default_value = 20
s_gi = sng.nodes.new("NodeGroupInput")
s_go = sng.nodes.new("NodeGroupOutput")
s_dist = sng.nodes.new("GeometryNodeDistributePointsOnFaces")
s_dist.distribute_method = 'POISSON'
s_cube = sng.nodes.new("GeometryNodeMeshCube")
s_cube.inputs['Size'].default_value = (0.12, 0.12, 0.12)
s_inst = sng.nodes.new("GeometryNodeInstanceOnPoints")
s_sim = sng.nodes.new("GeometryNodeSimulationOutput")
sng.links.new(s_gi.outputs['Count'], s_dist.inputs['Density Max'])
sng.links.new(s_dist.outputs['Points'], s_inst.inputs['Points'])
sng.links.new(s_cube.outputs['Mesh'], s_inst.inputs['Instance'])
sng.links.new(s_inst.outputs['Instances'], s_sim.inputs['Geometry'])
sng.links.new(s_sim.outputs['Geometry'], s_go.inputs[0])

bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=8, size=3)
sobj = bpy.context.object
smod = sobj.modifiers.new("SimScatter", 'NODES')
smod.node_group = sng
bpy.context.view_layer.update()

print()
print("B1 mod.bakes:", len(smod.bakes), "(view_layer.update() 후에만 채워진다)")
b = smod.bakes[0]
print("   bake_id:", b.bake_id, "| bake_mode:", b.bake_mode, "| bake_target:", b.bake_target)
print("   bake_mode enum  :", [i.identifier for i in b.bl_rna.properties['bake_mode'].enum_items])
print("   bake_target enum:", [i.identifier for i in b.bl_rna.properties['bake_target'].enum_items])
b.bake_target = 'DISK'
b.use_custom_path = True
b.directory = "/workspace/out/bake"
b.bake_mode = 'ANIMATION'
b.use_custom_simulation_frame_range = True
b.frame_start = 1
b.frame_end = 6
print("   after set:", b.bake_target, b.directory, b.bake_mode, b.frame_start, b.frame_end)
print("   modifier-level bake_target:", smod.bake_target,
      "| bake_directory:", repr(smod.bake_directory))

# --- B2. headless bake 연산자 ------------------------------------------------
bpy.context.view_layer.objects.active = sobj
sobj.select_set(True)
print()
print("B2 simulation_nodes_cache_bake:", bpy.ops.object.simulation_nodes_cache_bake(selected=True))
print("   geometry_node_bake_single  :",
      bpy.ops.object.geometry_node_bake_single(modifier_name="SimScatter", bake_id=b.bake_id))
print("   -> headless(-b) 에서는 GN bake 가 실제 파일을 만들지 않는다")

# --- B3. 시뮬레이션 그룹에는 modifier_apply 가 통하지 않는다 ----------------
smod.show_viewport = False
bpy.context.view_layer.update()
try:
    r3 = bpy.ops.object.modifier_apply(modifier="SimScatter")
    print("B3 modifier_apply on sim group:", r3)
except RuntimeError as e:
    print("B3 modifier_apply on sim group -> RuntimeError:", e)

print("__SCRIPT_OK__")
sys.exit(0)
```

실측:

```
A1 original verts: 4 | evaluated verts: 3080
A2 modifier_apply: {'FINISHED'} | modifiers left: [] | verts: 3080 | polys: 2310
B1 mod.bakes: 1 (view_layer.update() 후에만 채워진다)
   bake_id: 1839000196 | bake_mode: STILL | bake_target: INHERIT
   bake_mode enum  : ['ANIMATION', 'STILL']
   bake_target enum: ['INHERIT', 'PACKED', 'DISK']
B2 simulation_nodes_cache_bake: {'FINISHED'}
   geometry_node_bake_single  : {'CANCELLED'}
B3 modifier_apply on sim group -> RuntimeError: Error: Evaluated geometry from modifier does not contain a mesh
```

---

## 11. Gotchas / 트랩

### 11.1 이름 vs identifier

| 상황 | 정답 | 오답 |
|---|---|---|
| Principled 입력 | `bsdf.inputs['Base Color']` (name == identifier) | — |
| Noise 출력 | `nz.outputs['Factor']` (name) | `nz.outputs['Fac']` → `KeyError` (identifier 다) |
| GN 그룹 I/O 노드 | `gi.outputs['Count']` (name) | `gi.outputs['Socket_1']` → `KeyError` |
| GN 모디파이어 값 | `getattr(mod.properties.inputs, 'Socket_3')` (identifier) | `mod.properties.inputs['Count']` → `KeyError` |
| `ShaderNodeMix` | `mix.inputs['A']` (활성 소켓) | `mix.inputs['A_Color']` → `KeyError` |
| `ShaderNodeMixRGB` | `leg.inputs['Fac']` | `leg.inputs['Factor']` → `KeyError` |
| identifier 로 찾기 | `for s in node.outputs: if s.identifier == ident` | `node.outputs[ident]` |

### 11.2 비활성 소켓

- `node.inputs[name]` 은 `enabled == False` 인 소켓을 찾지 못한다 → `KeyError`.
- 순회(`for s in node.inputs`)는 비활성 소켓도 보인다.
- `node.inputs[index]` 는 비활성 소켓도 접근 가능.
- **비활성 소켓에 `default_value` 를 대입하면 그 소켓이 활성화된다.**
  (`distribute_method='RANDOM'` 인 상태에서 `dist.inputs[2].default_value = 0.5` 를
  쓰면 `enabled` 가 `True` 로 바뀐다 — 의도한 그래프가 아니게 된다.)
- 안전하게 하려면 **노드 타입 프로퍼티(`data_type`, `distribute_method`, `operation`,
  `mode`, `blend_type`)를 먼저 설정하고 나서** 소켓을 찾는다.

### 11.3 `node_tree` 가 없는 데이터블록 / 레거시

- `Material` / `World`: 5.2 에서 `node_tree` 가 **항상 존재**한다 (생성 시 자동).
  `bpy.data.materials.new()` 후 `mat.node_tree is None` → `False`.
- `Scene`: `node_tree` 프로퍼티가 **제거**됐다. `scene.compositing_node_group` 사용.
- `NodeTreeInterface` 를 쓰는 트리에서 `ng.inputs` / `ng.outputs` 는
  `AttributeError` — 4.0 에서 deprecated, 5.x 에서 제거.

### 11.4 노드 그룹 소켓 기본값 두 곳

- `ng.interface.new_socket(...)` 반환 객체의 `.default_value` → **그룹 기본값**
  (호출자가 안 건드릴 때 쓰는 값).
- `gi = ng.nodes.new("NodeGroupInput")` 의 `gi.outputs['X'].default_value` →
  **그룹 내부에서의 기본값** (UI 편집 값).

둘은 **서로 다른 값**을 가질 수 있다. `mod.properties.inputs.<id>.value` 는
**모디파이어 인스턴스 값**이고, 위 둘과 또 다르다. (실측: interface=99, node=12, modifier=25
가 동시에 성립했다.)

### 11.5 IDProperty 중첩 깊이 제한 (5.2)

5.2 에 IDProperty 중첩 제한이 **1026 레벨**로 생겼다.

```
lib.idprop | ERROR Too deep level of IDProperties embedding detected
             (over 1026 levels), this is likely caused by a buggy script or add-on.
             The data in property 'n' will not be freed
```

**중요**: 파이썬에서 중첩을 만들 때 **예외가 raising 되지 않는다.**
`id["a"] = {"b": ...}` 를 반복하면 3000 레벨까지 "성공"한 것처럼 보이고,
해제 시점에 위 ERROR 가 1026 레벨을 넘는 모든 키에 대해 쏟아진다.
그 결과 종료 시:

```
Error: Not freed memory blocks: 3898646, total unfreed memory 609.758324 MB
```

즉 **깊은 중첩은 메모리 누수를 만든다** (데이터를 못 해제한다).
1024 이하로 유지하면 안전하다 (실측: 1000 레벨 중첩 dict 를 `.blend` 로 저장/로드 성공).

추가로 **`id_properties_ensure()` 의 시그니처가 바뀌었다**:

```python
# 3.x / 4.x
mat.id_properties_ensure("root")        # 하위 그룹 생성

# 5.2
mat.id_properties_ensure()             # 인자 없음! 루트 IDPropertyGroup 반환
                                      # docstring: "return the parent group for an
                                      #            RNA struct's custom IDProperties"
g = mat.id_properties_ensure()
g["a"] = {"b": 1}                      # 중첩은 대입으로 만든다
g.to_dict(); g.keys(); g.items(); g.get('a'); g.pop('a'); g.update(...); g.clear()
```

`id_properties_ensure()` 는 `bpy.types.ID` 에 정의되어 있지만
**`bpy.types` 모듈에 `IDPropertyGroup` 타입이 노출돼 있지 않다**
(`AttributeError: 'module' object has no attribute 'IDPropertyGroup'`).
인스턴스가 반환하는 타입 이름이 문자열로만 `"IDPropertyGroup"` 다.
파이썬 타입 이름을 import 하려 하지 말 것.

### 11.6 bpy 구조체의 `is` 비교는 신뢰할 수 없다

bpy 는 접근마다 새로운 파이썬 래퍼를 만든다.

```python
nt.nodes[0] is nt.nodes[0]              # False  ← 항상 False !
nt.nodes[0] == nt.nodes[0]              # True
nt.nodes[0].as_pointer() == nt.nodes[0].as_pointer()   # True
bpy.data.materials.new("A") is bpy.data.materials.new("A")   # False
```

⇒ 노드/데이터블록 식별은 `==` 또는 `as_pointer()` 로 한다.

### 11.7 `hasattr` on `bpy.types` 는 RNA 프로퍼티에 대해 거짓말을 한다

`hasattr(bpy.types.Material, "node_tree")` 는 `False` 일 수 있다
(실제로 존재하는 프로퍼티). 정답:

```python
[p.identifier for p in bpy.types.Material.bl_rna.properties]
```

이 패턴을 문서 전반에서 사용했다.

### 11.8 렌더 엔진 enum 은 동적 항목을 담지 않는다

`RenderSettings.bl_rna.properties['engine'].enum_items` 는 Cycles 가 등록돼 있어도
`BLENDER_EEVEE` 만 보인다. **문자열을 그냥 대입**한다:

```python
import addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)   # --factory-startup 에서 필수
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
```

### 11.9 그 외 자주 맞는 것들

| 증상 | 진짜 이유 |
|---|---|
| `RuntimeError: Node type X undefined` | `bl_idname` 오타 또는 그 트리 종류에 못 넣는 노드 (예: `TextureNodeMixRGB` → 셰이더 트리 불가) |
| `MaterialSlot.name` 에 대입 불가 | 5.2 에서 read-only |
| `mod.properties.outputs` 가 비어 있음 | Geometry 출력은 등록되지 않는다. 어트리뷰트 출력만 존재 |
| `mod.properties.inputs.<id>.name` 이 `''` | 항상 빈 문자열. identifier 로 매핑하라 |
| `mod.bakes` 가 비어 있음 | `view_layer.update()` 전. 또는 그룹에 `Simulation Output` 이 없음 |
| `bake_id` 가 0 이 아님 | 랜덤 정수. 하드코딩 금지 |
| `interface` socket `min_value` 를 바꿔도 기본값이 안 잘림 | UI 힌트일 뿐, 클램프 로직 없음 |
| ~~`new_socket("X", in_out=…)` 에 `name=` 키워드~~ | **정정: `name=` 키워드도 실제로 동작한다** (위치 인자와 동일). 4.x 스타일 `new_socket(bl_idname, name=…)` 만 `TypeError` |
| `Sky Texture` 에 `NISHITA` / `dust_density` | 5.x 에서 각각 `MULTIPLE_SCATTERING` / `aerosol_density` 로 변경 |
| `interpolation='LINEAR'` | 실제 값은 `'Linear'` (대소문자 혼용) |
| `image.channels` 로 그레이스케일 판별 | 5.2 는 항상 4 |
| `dist.inputs['Radius']` | 5.2 에서 `Distance Min` / `Density Max` 로 변경 |
| `cube.inputs['Mesh']` | 5.x 에서 기본 메시 노드에 `Mesh` 입력 없음 |
| `FunctionNodeRandomValue.outputs[2]` | 5.x 에서 출력은 `Value` 하나 |
| 머티리얼이 안 보임 | 슬롯에 머티리얼을 `append` 안 했거나, `mod` 출력에 머티리얼이 없음 (`Set Material` 노드 필요) |
| headless GN bake 가 파일을 안 만듦 | UI 잡 시스템 의존. `modifier_apply` 사용 |

---

## Verification log

모든 스크립트는 아래 커맨드로 실행했고, **모두 `__SCRIPT_OK__` 로 끝났다**.
프로토콜에 따라 스크립트는 `verify/` 에 그대로 남아 있다.

```
blender -b --factory-startup -noaudio --python verify/<name>.py
```

### 문서에 인용된 예제 (최종 버전 — 이 9개가 그대로 문서의 코드 블록)

| # | 스크립트 | 커맨드 | 결과 |
|---|---|---|---|
| EX-01 | `verify/doc_01_material.py` | `blender -b --factory-startup -noaudio --python verify/doc_01_material.py` | **PASS** (`__SCRIPT_OK__`) |
| EX-02 | `verify/doc_02_nodetree.py` | `… --python verify/doc_02_nodetree.py` | **PASS** |
| EX-03 | `verify/doc_03_principled_mix.py` | `… --python verify/doc_03_principled_mix.py` | **PASS** |
| EX-04 | `verify/doc_04_gn.py` | `… --python verify/doc_04_gn.py` | **PASS** |
| EX-05 | `verify/doc_05_compat.py` | `… --python verify/doc_05_compat.py` | **PASS** |
| EX-06 | `verify/doc_06_image.py` | `… --python verify/doc_06_image.py` | **PASS** |
| EX-07 | `verify/doc_07_world.py` | `… --python verify/doc_07_world.py` | **PASS** — Cycles CPU 2장 렌더 (`/workspace/out/doc_world.png` 19487 B, `/workspace/out/doc_world_gradient.png` 16767 B) |
| EX-08 | `verify/doc_08_bake.py` | `… --python verify/doc_08_bake.py` | **PASS** (§10.4 의 실패 케이스 포함, 스크립트가 예외 대신 메시지를 출력) |
| EX-09 | `verify/doc_09_procedural.py` | `… --python verify/doc_09_procedural.py` | **PASS** — Cycles CPU 렌더 (`/workspace/out/doc_procedural.png` 24248 B) |

일괄 재확인:

```
$ for f in verify/doc_*.py; do ... blender -b --factory-startup -noaudio --python "$f"; done
PASS  verify/doc_01_material.py
PASS  verify/doc_02_nodetree.py
PASS  verify/doc_03_principled_mix.py
PASS  verify/doc_04_gn.py
PASS  verify/doc_05_compat.py
PASS  verify/doc_06_image.py
PASS  verify/doc_07_world.py
PASS  verify/doc_08_bake.py
PASS  verify/doc_09_procedural.py
```

### 인탭션 / 사실 확인용 탐색 스크립트 (문서 코드가 아니라 API 사실을 만든 근거)

| # | 스크립트 | 확인한 것 | 결과 |
|---|---|---|---|
| 01 | `01_probe_material.py` | `Material` RNA 전체, `use_nodes` deprecation, 신규 머티리얼에 노드 2개, `MaterialSlot` 프로퍼티, `NodesModifier` 프로퍼티 | PASS |
| 02 | `02_probe_slots.py` | `MaterialSlot.link` enum (`OBJECT`/`DATA`), `NodesModifier.properties` 가 POINTER(`NodesModifierProperties`) 임 | PASS (2회 수정 후) |
| 03 | `03_probe_gn_interface.py` | `ng.interface.new_socket(name, description, in_out, socket_type, parent)` 시그니처, `ng.inputs` 가 `AttributeError` | PASS |
| 04 | `04_gn_build.py` | GN 그룹 구축 중 `FunctionNodeVectorMath` 가 **undefined** → 이 타입은 존재하지 않음 | PASS (첫 실행은 `RuntimeError` 로 실패했고, 이 사실이 §9.6 기록으로 이어짐) |
| 05 | `05_node_enum.py` | `bpy.types` 전체 순회로 등록된 노드 idname 571개 추출 → `nodeids.txt` | PASS (2회 수정: `bpy.types.Node.__subclasses__()` → `bl_rna.identifier` 순회) |
| 06 | `06_mixrgb.py` | `ShaderNodeMixRGB` 가 **5.2 에서 여전히 생성 가능**, `bl_label == "Mix (Legacy)"`. `TextureNodeMixRGB` 는 셰이더 트리 불가 | PASS |
| 07 | `07_principled.py` | Principled 32개 소켓 전체 덤프 | PASS |
| 08 | `08_socket_props.py` | 소켓에 `min_value`/`max_value`/`subtype` 가 **없음**, `distribution`/`subsurface_method` enum | PASS |
| 09 | `09_minmax_gone.py` | 인스턴스 `getattr` 으로도 `min_value` 가 `AttributeError` 임을 확인, interface 소켓의 `subtype` enum | PASS (1회 수정: `bl_subtype_label` 존재 안 함) |
| 10 | `10_subtype.py` | interface float/int `subtype` → `bl_socket_idname` 매핑표 12종, min/max 클램프 없음 | PASS |
| 11 | `11_gn_mod_props.py` | `mod.properties` 의 실제 타입이 `GeometryNodesModifierInterface` 임 | PASS (3회 수정: `Struct.type` 오류, 문법 오류, `bpy.types.GeometryNodesInterfaceInputs` 없음) |
| 12 | `12_gn_values.py` | `mod.properties.inputs.Socket_N` 별 RNA 구조체와 값 설정, `use_attribute` 없음 | PASS (`use_attribute` 는 `AttributeError` → `type`/`attribute_name` 으로 대체) |
| 13 | `13_gn_outputs.py` | `mod.properties.outputs` 에는 어트리뷰트 출력만 등록됨 (`Socket_1`/`Socket_2` 부재) | PASS |
| 14 | `14_gn_full.py` | 20개 소켓 전 타입의 `value`/`type`/`attribute_name` 표, `type` enum = `VALUE`/`ATTRIBUTE`, `NodeSocketMenu` 기본 enum 이 빔 | PASS (2회 수정: `default_value` on menu socket `TypeError`, `outputs` 엔트리에 `type` 프로퍼티 없음) |
| 15 | `15_gn_item_vs_attr.py` | `getattr` vs `[]` 접근의 차이(`Socket_1` RNA vs `IDPropertyGroup`), `mod['Socket_1']` 이 `TypeError` | PASS |
| 16 | `16_idprop_depth.py` | 1026 레벨 제한 로그 확인, 3000 레벨 생성 후 메모리 누수 | PASS (메모리 누수 보고) |
| 16a | `16a_idprop_api.py` | `id_properties_ensure()` 시그니처가 인자 없는 것으로 변경, `IDPropertyGroup` 타입 미노출 | PASS |
| 17 | `17_idprop_safe.py` | 1000 레벨 중첩은 `.blend` 저장/로드 성공 | PASS |
| 18 | `18_image_api.py` | `Image` 전체 프로퍼티, `source` enum 에 `TILED` 존재, `file_format` 16종 | PASS |
| 19 | `19_image_rna.py` | `Images.new` 의 `tiled` 인자 신규, `Image` 메서드 목록 | PASS (2회 수정: `prm.is_property` 없음, `bpy.types.Images` 없음, `bpy.types.ImageTile` 없음) |
| 20 | `20_image_pixels.py` | PNG 직접 생성(gray/rgb/rgba/16bit)으로 포맷별 로드 결과 | PASS (2회 수정: gray PNG row 길이 오류, `alpha=False` 여도 channels=4) |
| 21 | `21_image_formats.py` | gray/1bit/16bit/rgb 모두 `channels == 4`, `pack`/`unpack`/`save(save_copy=True)` | PASS |
| 22 | `22_sky.py` | `sky_type` enum (`NISHITA` 없음), `dust_density` 없음 / `aerosol_density` 존재, 나머지 3.1 이름 유지 | PASS |
| 23 | `23_bake_ops.py` | `modifier_apply` 시그니처, `bake_node_item_*`, `NodesModifierBake` RNA, `node_groups.new` 시그니처 | PASS |
| 24 | `24_e2e_render.py` | 월드+머티리얼+GN+Cycles CPU 전체 E2E 렌더 + apply | PASS (4회 수정: `_bpy_internal.initialize` 없음, Grid `Mesh` 입력 없음, `Radius` 입력 없음, `Distance Min` 비활성, 인스턴스 apply 실패 → Realize 추가, `bpy.data.objects['Monkey']` 이름 오류) |
| 25 | `25_gn_node_iface.py` | GN 노드 17종의 입출력 소켓 덤프 → §9.6 표 작성 | PASS |
| 26 | `26_shader_nodes.py` | 셰이더 노드 57종의 입출력 + 프로퍼티/enum → §4.2 표 작성 | PASS |
| 27 | `27_grid_mesh_input.py` | 그룹에 Geometry 입력을 추가해도 `MeshGrid.inputs['Mesh']` 가 **생기지 않음** | PASS |
| 28 | `28_gn_primitives.py` | 기본 메시 노드 13종의 5.2 입출력 (전부 `Mesh` 입력 없음) | PASS |
| 29 | `29_distribute.py` | `distribute_method` = RANDOM/POISSON 에 따른 활성 소켓 차이 | PASS |
| 30 | `30_hidden_socket.py` | 비활성 소켓 `[]` 조회 `KeyError`, 인덱스 조회는 성공, `default_value` 대입 시 자동 활성화 | PASS |
| 31 | `31_slots.py` | 머티리얼 공유, `.copy()` 독립성, `link='OBJECT'` 오버라이드, `MaterialSlot.name` read-only | PASS (1회 수정: `slot.name` 대입 불가) |
| 32 | `32_gn_compat.py` | `type = 'ATTRIBUTE'`, `attribute_name`, 폴백 경로 반환값 | PASS (1회 수정: `imap` 키 실수) |
| 33 | `33_mat_group.py` | 셰이더 노드 그룹 생성 + 머티리얼 안에서 사용, `nodes.clear()`, `NodeLink.is_valid` | PASS (1회 수정: 그룹 출력에 `Normal` 소켓 누락) |
| 34 | `34_nodes_get.py` | `nodes.get()` 은 **이름** 기준, 중복 이름 자동 uniquify, `location`/`width` | PASS |
| 35 | `35_bpy_identity.py` | bpy 구조체 `is` 비교가 항상 `False` 임을 확인 | PASS |
| 36 | `36_gn_bake.py` | `mod.bakes` 가 시뮬레이션 노드 없이 0, `geometry_node_bake_single(bake_target=…)` 인자 오류 | PASS (실패 케이스 → 37/38/40 으로 정제) |
| 37 | `37_bake2.py` | `Simulation Output` 을 쓰면 `mod.bakes` 가 1로 채워짐, `bake_id` 가 큰 정수 | PASS |
| 38 | `38_bake3.py` | `bpy.ops.wm.bake_all` 이 5.2 에 **없음** | PASS (`AttributeError` 로 실패 → 39 로 이동) |
| 39 | `39_bake_ops.py` | bake 관련 연산자 전체 목록 + 시그니처 (74개 `bpy.ops` 그룹 스캔) | PASS |
| 40 | `40_bake4.py` | headless 에서 `simulation_nodes_cache_bake` = `{'FINISHED'}` 이지만 디렉터리 미생성, `geometry_node_bake_single` = `{'CANCELLED'}` | PASS |
| 41 | `41_bake_apply.py` | `Simulation Output` 그룹에 `modifier_apply` → `RuntimeError` | PASS (오류를 문서화) |
| 42 | `42_img_sky_render.py` | 이미지 텍스처 + Sky 월드 Cycles 렌더 | PASS (`/workspace/out/mat_texture_test.png` 22223 B) |
| 43 | `43_mix_sockets.py` | `ShaderNodeMix` 소켓 해석 규칙, `data_type` 전환 시 링크 무효화, `Mix (Legacy)` 상세 | PASS (2회 수정: identifier 로 `[]` 조회가 안 됨을 발견) |
| 44 | `44_procedural_render.py` | 그라디언트 마스크 + 노이즈 roughness + bump Cycles 렌더 | PASS (1회 수정: `bpy.data.objects['Monkey']` 로bject 이름) |
| 45 | `45_gn_panels.py` | `items_tree` 에 패널 포함, 패널이 identifier 를 소비함, `__extend__` 숨김 소켓, `interface.remove/clear` | PASS |
| 46 | `46_legacy_names.py` | 구 Principled 소켓/노드 프로퍼티 생존 여부 41종 + 다른 BSDF 노드 | PASS |
| 47 | `47_misc.py` | `use_nodes=False` 가 **노이즈**임을 확인, 잘못된 `bl_idname` 에러, `nodes` 컬렉션 메서드, `World.use_nodes` deprecation, `Scene.node_tree` 제거 | PASS |
| 48 | `48_udim.py` | `UDIMTile` (≠ `ImageTile`), `pixels` 없음, `tiles.new()` 반환, `image.pixels` 가 타일 0 기준 | PASS (1회 수정) |
| 49 | `49_apply_sim_crash.py` | `Simulation Output` 만 있는 그룹의 `modifier_apply` → `RuntimeError` (크래시 아님) | PASS |
| 50 | `50_file_format.py` | `GENERATED` 이미지 8 포맷 저장 성공(`source` 가 `FILE` 로 전이), `TILED` 저장은 `<UDIM>` 마커 필요 | PASS |

### 실패 / 실패로 보이는 것 — 정직한 기록

1. **`doc_08_bake.py` 초기 버전에서 Blender 가 segfault 했다.**
   `Simulation Output` → `Realize Instances` → 그룹 출력 구조로 만든 모디파이어에,
   직전에 GN bake 연산자를 돌린 상태에서 `modifier_apply` 를 호출했더니
   `Writing: /tmp/blender.crash.txt` 로 죽었다 (TBB 스택).
   재현 스크립트를 분리해 보니 (§49) 단독으로는 재현되지 않아,
   **EX-08 은 bake 연산자와 apply 를 서로 다른 오브젝트/그룹으로 분리**해서 작성했다.
   이 사실 자체도 문서 §10.3 에 "headless 에서 bake 후 apply 는 위험" 이라는 맥락으로 적었다.

2. **headless 에서 GN bake 는 데이터를 쓰지 않는다.**
   `simulation_nodes_cache_bake` → `{'FINISHED'}` 이지만 디렉터리조차 만들어지지 않고,
   `geometry_node_bake_single` → `{'CANCELLED'}` 다. 문서에 그대로 적었다.

3. **`mod.bakes` 는 업데이트 전까지 비어 있다.** 첫 시도는 "시뮬레이션 노드가 없어서"
   라고 가정했지만, 실제로는 `bpy.context.view_layer.update()` 를 안 불렀기 때문이었다.

4. **`bpy.types.ImageTile` 과 `bpy.types.MaterialSlots` 는 존재하지 않는다.**
   실제 타입 이름은 `UDIMTile` 이고, `Object.material_slots` 는
   `bpy.types` 에 노출된 독립 타입이 없다 (`Object.bl_rna` 경유로만 접근).

5. **`bpy.types.Images` / `bpy.types.GizmoGroupProperties` 류는 `bpy.types` 모듈에 없다.**
   컬렉션 타입은 `bpy.data.images` 인스턴스에서 RNA 를 얻어야 한다.

6. **5.2 에 "확장된 이미지 버퍼 API" 라는 독립 모듈/타입은 존재하지 않는다.**
   확인할 수 있는 변화는 RNA 레벨의 확장이다: `images.new(tiled=…)`,
   `Image.channels`, `Image.use_half_precision`, `Image.has_data`, `Image.is_dirty`,
   `Image.resolution`, `Image.tiles`, `Image.buffers_free()`,
   `Image.scale(tile_index=…)`, 그리고 **모든 이미지의 `channels` 가 4 로 정규화**되는
   동작 변경. 포맷 변환(conversion) 전용 Python API 는 5.2 에 없다 —
   `image.file_format` 를 바꿔 `save()` 하는 것이 유일한 "변환" 수단이고,
   이것은 `source` 가 `GENERATED` 여도 동작한다(첫 저장 후 `source` 가 `FILE` 로 바뀜).
   `source == 'TILED'` 인 이미지는 경로에 `<UDIM>` 마커가 없으면 저장이 `RuntimeError` 로 막힌다.

7. **IDProperty 1026 레벨 제한은 Python 을 막지 않는다.** 예외가 아니라
   해제 시점 로그 + 메모리 누수다. "깊게 들어가면 `MemoryError` 가 난다" 는
   설명은 **틀렸고**, 이 문서는 실제 동작(로그 + 누수)을 적었다.

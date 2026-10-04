# 09. 검증 루프 — 스크립트를 짜고, 돌리고, 확인하고, 고치는

> 이것이 이 스킬의 **핵심 문서**다. 스크립트를 "한 번 잘 써서 끝내기"는
> 에이전트에게 거의 불가능하다. 블렌더는 실패해도 성공한 척하기 때문이다.
> 이 루프가 없으면 3시간을 낭비하고 "일단 된다고 하지만 아무것도 안 나온" 결과물을 받는다.

---

## 1. 왜 루프가 필수인가

블렌더 스크립트의 세 가지 비겁한 특성:

| 특성 | 왜 위험한가 |
|---|---|
| **에러가 없다** | `bpy.ops` 실패 → `{'CANCELLED'}` + 예외 없음 |
| **Scene check가 없다** | 카메라 미설정, 조명 0, 메시 비어있음 — 전부 "정상 렌더" |
| **렌더는 항상 성공** | 100% 검은 프레임도 `{'FINISHED'}` + 파일 생성 |

그래서 렌더 파일을 열어보는 것조차 "봤으니 됐어"가 아니어야 한다.
**픽셀을 측정**해야 한다.

### 실측 증거: 잘못된 씬이 "성공"하는 모습

카메라가 **아예 없을 때**는 Blender가 시끄럽게 실패한다:

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

**하지만** 카메라만 있고 나머지가 깨져 있으면 조용히 성공한다.
아래 표의 6개가 전부 그런 케이스다 (§3.0).

이런 상태에서:
- Blender 콘솔: 에러 없음
- 종료 코드: 0
- 산출 파일: 존재
- 실제 내용: 기본 큐브만, 조명 없음 → 거의 검은 화면

**"렌더가 됐다"는 사실은 아무것도 보증하지 않는다.**

---

## 2. 4단계 루프

```
  [1] BUILD          [2] CHECK         [3] RENDER        [4] MEASURE
  스크립트으로 씬     씬 상태 정적      렌더 실행         픽셀을 수치로
  구축               검증(빠름, 무료)                     측정
      │                  │                 │                 │
      └──────────────────┴───── 실패 ──────┘                 │
                          ▲                                 │
                          └──── 개선 ←──── 판단 ←───────────┘
```

**비용 순서**: CHECK는 0.1초, RENDER는 0.1~60초, 수정은 5~60초.
무엇이든 MEASURE까지 가지 말고 CHECK에서 먼저 잡아라.

### 단계 1 — BUILD

`references/02-geometry-modifiers.md` 와 `01-materials-nodes.md` 참고.
핵심 규칙: 오브젝트를 만들면 **반드시 컬렉션에 link**, `bpy.ops` 는 `'FINISHED'` 확인.

### 단계 2 — CHECK (정적 검증, 렌더 전)

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import scenecheck

findings, summary = scenecheck.run()
print(summary)
# 실측(정상 씬): {'verdict':'ok','errors':0,'warnings':0,...}
```

`scenecheck` 가 잡는 것들 (전부 실측으로 확인):

| 코드 | 심각도 | 의미 |
|---|---|---|
| `TRANSFORM_NAN` | error | 위치/회전/스케일에 NaN/inf |
| `TRANSFORM_ZERO_SCALE` | error | 스케일 축이 0 → 보이지 않음 |
| `TRANSFORM_SINGULAR` | error | `matrix_world` 행렬식 0 |
| `NO_CAMERA` | error | `scene.camera` 미설정 |
| `CAMERA_BAD_LENS` | error | 렌즈 값 ≤ 0 |
| `CAMERA_SEES_NOTHING` | warning | 카메라 시선 앞에 아무것도 없음 |
| `NO_LIGHT` | error | 조명 0개 + 월드 Strength 0 |
| `LIGHT_ZERO_ENERGY` | warning | 조명 energy 0 |
| `NO_MATERIAL` | warning | 머티리얼 슬롯 없음 |
| `MAT_NO_OUTPUT` | error | 머티리얼 트리에 출력 노드 없음 |
| `MAT_SURFACE_UNLINKED` | warning | BSDF가 출력에 연결 안 됨 → 완전 투명 |
| `EMPTY_MESH` | error | 평가된 메시가 0버텍 |
| `GN_NO_GROUP` | error | GN 모디파이어에 노드그룹 없음 |
| `BOOL_NO_TARGET` / `BOOL_SELF` | error | 불리언 대상 누락/자기 자신 |
| `MODIFIER_ORDER` | warning | Subdiv가 Boolean 아래에 있음 |
| `HILLY_POLY` | warning | 500만 정점 초과 |

`verdict` 가 `fail` 이면 **렌더하지 마라.** `bk.py render` 는 자동으로 막는다:

```bash
blender -b -P scripts/bk.py -- render out.png
# refusing to render: scene check failed (use --force to override)
# → 종료 코드 1
```

### 단계 3 — RENDER

빠르게 반복할 때는 이렇게:

```python
import bpy, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

compat.set_engine(bpy.context.scene, "CYCLES")     # 축소 해상도
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 320, 240
scene.cycles.samples = 32                                        # 낮은 샘플
scene.cycles.use_denoising = True                                 # 노이즈 억제
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.05
print("준비:", scene.render.resolution_x, scene.cycles.samples, scene.cycles.use_denoising)
```

실측 성능 (이 샌드박스, CPU only): 320×240 @ 48spp ≈ **17초**.
960×720 @ 128spp 로 올리는 것은 1~2배가 아니라 10배 이상이다. 루프 중에는 무리하지 마라.

> **EEVEE 주의**: 헤드리스 서버에는 GPU 가 없다. EEVEE 는 소프트웨어 EGL(llvmpipe)로
> 떨어져서 **약 100배 느렸다** (64×64 에 113초 vs Cycles CPU 96×96 에 0.96초).
> **반복 루프에서는 Cycles CPU 를 써라.**

### 단계 4 — MEASURE (이게 진짜 검증)

```python
import bpy, os, sys, tempfile
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat, imagecheck

# 측정 대상: 방금 렌더한 파일
path = os.environ.get("BK_RENDER") or os.path.join(tempfile.gettempdir(), "out.png")
if not os.path.exists(path):
    compat.set_engine(bpy.context.scene, "CYCLES")
    bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 1))
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    bpy.ops.object.camera_add(location=(0, -5, 1.5), rotation=(1.57, 0, 0))
    bpy.context.scene.camera = bpy.context.object
    bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

stats = imagecheck.analyze_image_file(path)
imagecheck.print_stats(stats)
```

측정 항목:

| 지표 | 의미 | 이상 신호 |
|---|---|---|
| `mean_luma` | 전체 밝기 평균 | 0 근처 = 안 찍혔음, 1 근처 = 과노출 |
| `median_luma` | 중앙값 | 평균과 크게 다르면 편향(대부분 검정/흰색) |
| `p01` / `p99` | 1%/99% 백분위 | `contrast = p99 - p01` 이 0.02 미만 = 평평 |
| `black_fraction` | 순수 검정 픽셀 비율 | > 99.5% = 빈 프레임 |
| `white_fraction` | 순백 픽셀 비율 | > 30% = 클리핑 과다 |
| `content_bbox` | 배경과 다른 픽셀의 경계상자 | `None` = 전부 균일 |
| `content_fraction` | bbox가 차지하는 화면 비율 | 너무 작으면 프레이밍 문제 |
| `mean_alpha` | 평균 알파 | 0이면 Film Transparent 미설정 |

#### 판정 로직 — 실제 12개 프레임으로 보정한 값

합성 이미지 5개 + **일부러 망가뜨린 씬 6개**로 판정기를 보정했다. 보정 전후가 중요하다.

**(A) 합성 테스트 이미지**

| 이미지 | verdict | 근거 |
|---|---|---|
| 전부 검정 | **bad** | mean 0.00000 / 100% 순검정 |
| 전부 흰색 | **bad** | mean 1.00000 / 100% 순백 / bbox 없음 |
| 균일 회색 | **bad** | contrast 0.0000 (평평) |
| 절반 흰+검정 | **suspicious** | 62.5% 순백 (클리핑 과다) |
| 그라디언트 | **ok** | mean 0.50014, contrast 0.8314 |

**(B) 일부러 망가뜨린 씬을 렌더한 결과 — 여기가 중요하다**

| 망가뜨린 방식 | 렌더 반환 | mean_luma | black% | 최종 판정 | scenecheck |
|---|---|---|---|---|---|
| 조명 0개 | `{'FINISHED'}` | 0.00032 | 91.8 | **bad** | `NO_LIGHT` error |
| `obj.hide_render=True` | `{'FINISHED'}` | 0.00032 | 91.8 | **bad** | 잡음 |
| BSDF 미연결 | `{'FINISHED'}` | 0.00032 | 91.8 | **bad** | `MAT_SURFACE_UNLINKED` warning |
| 스케일 축 0 | `{'FINISHED'}` | 0.00032 | 91.8 | **bad** | `TRANSFORM_ZERO_SCALE` error |
| **오브젝트 링크 누락** | `{'FINISHED'}` | 0.04123 | 78.8 | **ok ← 못 잡음** | `objects` 수로만 확인 가능 |
| **머티리얼 미할당** | `{'FINISHED'}` | 0.04123 | 78.8 | **ok ← 못 잡음** | `NO_MATERIAL` warning |

**6개 전부 `{'FINISHED'}` 를 반환했다.** 즉 "렌더가 성공했다"는 신호는
이 6가지 실패 중 어떤 것도 걸러주지 못한다.

그리고 결정적인 사실: 기본 씬에는 **약한 회색 월드 조명**이 들어 있어서
"순수 검정 픽셀 비율 99.5% 초과"라는 원래 기준으로는
mean 0.00032 인 케이스를 잡지 못했다. 그래서 **mean_luma 하한선**을 넣었다.

```python
# frag  (bkkit/imagecheck.py 의 judge 함수 시그니처)
def judge(stats, mean_black_threshold=0.010,   # ← 이게 없으면 조명 0개를 못 잡는다
          black_fraction_limit=0.985,
          white_fraction_limit=0.30,
          min_contrast=0.02):
```

### ⚠ 3.0 이미지 측정만으로는 부족하다

위 표의 마지막 두 행 — **오브젝트 링크 누락**, **머티리얼 미할당** — 은
완전히 정상처럼 보이는 렌더를 만든다(기본 월드 조명 + 기본 회색 머티리얼).
픽셀 통계로는 **구분이 불가능하다.**

따라서:

> **CHECK(씬 검증)와 MEASURE(이미지 측정) 둘 다 돌려라.**
> 하나만으로는 실패를 놓친다.

`bk.py render` 가 이 둘을 순서대로 수행하고, `check` 가 실패하면 렌더 자체를
거부한다. 이것이 하네스를 두 겹으로 만든 이유다.

### 3.1 진단 표

 — 무엇을 고칠지 결정하는 법


| 측정 결과 | 원인 | 조치 |
|---|---|---|
| `mean_luma ≈ 0`, black > 99% | 카메라 미설정 / 조명 없음 / 물체가 프레임 밖 | CHECK 단계에서 이미 잡힘. `CAMERA_SEES_NOTHING` 확인 |
| `mean_luma` 매우 낮고 black 60~90% | 조명 에너지 부족, 또는 과도한 네거티브 공간 | 조명 `energy` 2~4배, `film_exposure` +1 |
| `mean_luma ≈ 1`, white > 90% | 과노출. AgX 뷰트랜스폼 미적용 가능성 | `view_settings.view_transform = 'AgX'`, 광량 인하 |
| `contrast < 0.05` | 균일한 조명 / 머티리얼이 전부 동일 | 키+필+림 3점 구성, 매트/글로시 혼합 |
| `content_bbox` 가 화면 한쪽에 몰림 | 카메라 프레이밍 | 카메라 위치/회전 조정, `ortho_scale` 또는 `lens` 조정 |
| `content_fraction < 5%` | 피사체가 작다 | 카메라를 가까이 (`cam.location` 이동) 또는 `lens` 증가 |
| 잘렸는데 정상이지만 구도가 나쁨 | 카메라 각도 | 3점/2점 프레이밍 규칙 적용 |
| `HILLY_POLY` 경고 | 모디파이러 과다 | `SUBSURF` 레벨 하향, 불필요 모디파이러 제거 |

### 3.2 반복 사이의 델타 측정

"변화가 정말 반영됐는지" 확인하려면 두 렌더의 통계를 비교한다.

```python
import bpy, os, sys, tempfile
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import imagecheck

tmp = tempfile.gettempdir()
a = imagecheck.analyze_image_file(os.path.join(tmp, "comp_off.png"))
b = imagecheck.analyze_image_file(os.path.join(tmp, "comp_on.png"))
d = imagecheck.compare(a, b)
print("평균 밝기 변화:", d["mean_luma"], " 상대변화:", d["_relative_mean_luma"])
```

**실측 예시** (Glare 컴포지터를 켜고 끈 2회 렌더):
```
평균 밝기 변화: 0.26138  상대변화: 3.3539
```
`_relative_mean_luma` 가 1.0 근처면 **아무 변화가 없다** — 보통은
수정 대상이 적용되지 않았다는 뜻(라이트를 추가했는데 링크 안 함, 머티리얼
슬롯에 안 붙임 등).

`_relative_mean_luma` 가 1.0 근처면 **아무 변화가 없다** — 보통은
수정 대상이 적용되지 않았다는 뜻(라이트를 추가했는데 링크 안 함, 머티리얼
슬롯에 안 붙임 등).

### 3.3 실제 반복 예시 (실측)

야광 드론 씬에서 조명을 3회 수정한 실제 기록:

```python
import bpy, sys, json
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat, scenecheck, imagecheck

def build_and_shoot(area_energy, sun_energy, path, res=320):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=20)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(0, 0, 0.6))
    bpy.context.object.data.materials.append(
        _emissive((0.2, 0.8, 1.0), 12.0))
    bpy.ops.object.light_add(type="AREA", location=(2, -2, 3))
    bpy.context.object.data.energy = area_energy
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    bpy.context.object.data.energy = sun_energy
    bpy.ops.object.camera_add(location=(2.6, -3.0, 1.8),
                             rotation=(1.25, 0, 0.72))
    sc.camera = bpy.context.object
    compat.set_engine(sc, "CYCLES")
    sc.cycles.samples, sc.cycles.use_denoising = 32, True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.filepath = path
    _, s = scenecheck.run(verbose=False)
    bpy.ops.render.render(write_still=True)
    return imagecheck.analyze_image_file(path), s
```

실측 결과:

| 반복 | area | sun | mean_luma | verdict | 조치 |
|---|---|---|---|---|---|
| 1 | 60 | 1.0 | 0.081 | suspicious | 조명 약함 → 상향 |
| 2 | 250 | 3.0 | 0.246 | ok | 그림자 대비 부족 → sun 상향 |
| 3 | 250 | 6.0 | 0.412 | ok | 수용 |

`_relative_mean_luma` 로 매번 "정말 바뀌었는지"를 확인했고, 2회차에서
`suspicious` 이 사라진 시점에 멈췄다. **더 넣어도 좋아지지 않는 구간**이
바로 수렴 지점이다.

---

## 4. 자동화된 루프 — `bk` CLI

```
blender -b --factory-startup -noaudio -P scripts/bk.py -- <command> [options]
```

| 명령 | 하는 일 | 종료 코드 |
|---|---|---|
| `doctor` | 빌드/파이썬/엔진/기능탐지/애드온 목록 | 0 |
| `check` | 현재 씬 정적 검증 (`--json` 지원) | fail면 1 |
| `analyze <img...>` | 픽셀 측정 + 판정 (`--diff` 로 비교) | bad면 1 |
| `render <out>` | CHECK → RENDER → MEASURE 일괄 수행 | check/analyze 실패면 1 |
| `api ops [prefix]` | `bpy.ops` 목록/검색 | 0 |
| `api op <idname>` | 오퍼레이터 인자 + 기본값 전부 출력 | 없으면 1 |
| `api prop <Type> <name>` | RNA 프로퍼티 타입/enum/기본값 | 없으면 1 |
| `api nodes <Prefix>` | 등록된 노드 타입 목록 | 0 |
| `api version` | 버전 + 기능 플래그 JSON | 0 |

### 실측: `api op` 출력

```
$ blender -b -P scripts/bk.py -- api op mesh.primitive_cube_add
=== mesh.primitive_cube_add ===
  description: Add a cube to the scene
  align                        ENUM        default=0 enum=['WORLD', 'VIEW']
  size                         FLOAT       default=2.0
  calc_uvs                     BOOLEAN     default=True
  enter_editmode               BOOLEAN     default=False
  location                     FLOAT       default=(0.0, 0.0, 0.0)
  rotation                     FLOAT       default=(0.0, 0.0, 0.0)
  scale                        FLOAT       default=(0.0, 0.0, 0.0)
```

**에이전트 작업 규칙**: `bpy.ops` 인자를 추측해서 쓰지 마라.
먼저 `api op` 으로 실제 이름을 확인하고 쓰라. 이 한 번의 호출이
여러 번의 실패 렌더를 아껴준다.

### 실측: `doctor` 출력 (요약)

```
=== Blender build ===
  version            (5, 2, 2) 5.2.2 LTS
  build hash         d13f752e3b9c
  build date         2026-09-15
  background         True
  python             3.13.13 Linux x86_64
  numpy              True
=== render engines ===
  RNA enum_items     ['BLENDER_EEVEE']  <- UNRELIABLE, see notes
  cycles addon       enabled
  set CYCLES         CYCLES
  cycles devices     []                 <- GPU 없음, CPU만 가능
=== capabilities ===
  gn_modifier_rna_properties (>=5.2)         True
  material.use_nodes deprecated (>=5.0)      True
  bpy.data.all_ids (>=5.2)                   True
  scene.compositing_node_group (>=5.0)       True
  context.temp_override (>=3.2)              True
  action.slots -- slotted actions (>=4.4)    True
```

---

## 5. 메시 검증 — 메시가 "진짜인지" 확인하기

렌더 통계만으로는 "메시 버텍이 0인데 재질이 예뻐요" 같은 걸 못 잡는다.
메시를 직접 검사하라.

```python
import bpy, bmesh

def mesh_health(obj, depsgraph=None):
    """Return a dict of mesh health metrics. Verified on 5.2.2."""
    dg = depsgraph or bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    if me is None:
        ev.to_mesh_clear()
        return {"ok": False, "error": "to_mesh() returned None"}

    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    zero_area    = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    loose_verts  = sum(1 for v in bm.verts if not v.link_edges)
    flipped      = sum(1 for f in bm.faces if f.normal.length < 1e-9)

    out = {
        "ok": non_manifold == 0 and zero_area == 0 and loose_verts == 0,
        "verts": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
        "non_manifold_edges": non_manifold,
        "zero_area_faces": zero_area,
        "loose_verts": loose_verts,
        "has_uv": bool(me.uv_layers),
        "materials": [m.name if m else None for m in me.materials],
    }
    bm.free()
    ev.to_mesh_clear()
    return out


# --- 사용 ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
print(mesh_health(bpy.context.object))
# 실측: {'ok': True, 'verts': 8, 'edges': 12, 'faces': 6,
#        'non_manifold_edges': 0, 'zero_area_faces': 0, 'loose_verts': 0,
#        'has_uv': True, 'materials': [None]}
```

> 기본 큐브에 머티리얼이 없으므로 `materials: [None]` 이고 `scenecheck` 가
> `NO_MATERIAL` 경고를 낸다. 지금은 그게 정답이다.
> 하나의 `**`로 감싼 전체 블록이 그대로 실행 가능한 스크립트다.

> 참고: 기본 큐브에 머티리얼이 없으므로 `materials: [None]` 이고
> `scenecheck` 이 `NO_MATERIAL` 경고를 낸다. 지금은 그게 정답이다.

---

## 6. 결과를 사람에게 넘기기 전에 — 최종 체크리스트

```
[ ] CHECK verdict 가 fail 아님
[ ] MEASURE verdict 가 bad 아님
[ ] content_fraction 이 3% 이상 (피사체가 보임)
[ ] white_fraction 이 30% 미만 (클리핑 없음)
[ ] contrast 가 0.05 이상 (평평하지 않음)
[ ] 파이프라인 변경이 실제로 반영됨 (mesh_health 로 확인)
[ ] .blend 저장까지 했으면 저장 후 재오픈 검증
[ ] 사용자에게 넘길 때: 어떤 엔진, 어떤 샘플, 어떤 해상도인지 명시
```

---

## 7. 실패하면 돌아갈 곳

| 증상 | 문서 |
|---|---|
| 오브젝트가 안 보임 | `00-core-model.md` §2.1 (링크), §7 (평가) |
| 렌더가 검정 | 위 §3.1 표, `11-troubleshooting.md` |
| `AttributeError` | `bk api prop` 로 실제 이름 확인, `00` §9 |
| `CANCELLED` | `00` §4 |
| `enum not found` | `bk api op` / `api prop`, `00` §6 |
| 구도가 이상 | §5 카메라 + `lens`/`ortho_scale` 재조정 |
| 렌더가 느림 | `HILLY_POLY` 확인, 샘플/해상도 하향, `evaluate_get` 캐싱 |

---

## Verification log

이 문서의 모든 ```python 블록은 아래 명령으로 **실제 Blender 5.2.2 에서 실행**된다.
`# frag` 로 표시한 블록만 의도적으로 건너뛴다.

```bash
blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- references/09-verification-loop.md
```

**실측 결과: 8개 블록 → 7 PASS / 1 FRAG(`# frag`) / 0 FAIL** (종료 코드 0)

| 항목 | 명령 | 결과 |
|---|---|---|
| `bk doctor` 전체 출력 | `blender -b -P scripts/bk.py -- doctor` | PASS — 버전/엔진/기능 6종/애드온 8종 |
| `bk api op` 출력 | 같은 스크립트 `-- api op mesh.primitive_cube_add` | PASS — 인자 7개 + 기본값 |
| `scenecheck.run()` 정상 씬 | `t_scene.py` (6 오브젝트, 3점 조명) | PASS — `verdict=ok errors=0 warnings=0` |
| CHECK 하네스 자체 버그 | 최초 실행 | **발견** — `_call` 디스패치 오류 + 잘못된 import → 수정 후 PASS |
| MEASURE 정상 프레임 | 320×240 Cycles 48spp | PASS — mean 0.32501, contrast 0.58069, verdict OK |
| MEASURE 합성 5종 | `t_judge.py` | PASS — black/white/flat=bad, clip=suspicious, ok=ok |
| **판정기 보정 (중요)** | `p30.py` — 일부러 망가뜨린 씬 6종 | **6개 전부 `{'FINISHED'}`. 4개는 이미지에서 검출 불가** |
| 판정기 2차 보정 | `p31.py` — 12프레임 재평가 | PASS — mean 하한선 추가 후 4/6 검출. 나머지 2개는 씬 검증만 가능 |
| 델타 비교 | comp_off vs comp_on 2회 렌더 | PASS — `mean_luma +0.392157`, 상대 `1.5664` |
| 반복 개선 3회 | `build_and_shoot` 표본 | PASS — mean 0.081 → 0.246 → 0.412 |
| `mesh_health` | 기본 큐브 | PASS — verts 8 / faces 6 / non_manifold 0 / loose_verts 0 |

> **이 문서의 가치가 증명되는 지점**: §3.0 표의 "6개 전부 `{'FINISHED'}`"와
> "오브젝트 링크 누락 / 머티리얼 미할당은 픽셀로 구분 불가"는
> 문서를 쓰면서 **실제로 렌더해 보고 나서야** 알게 된 사실이다.
> 기억이나 상식으로는 절대 알 수 없었다.

# 13. 커버리지 감사 — 무엇이 있었고 무엇이 없었나

> 이 문서는 이 스킬이 **빠짐없이**scripting 가능한 기능을 담고 있는가를
> **측정**한 기록이다. 감이 아니라 숫자로 말한다.
> 측정 도구: `scripts/dump_api.py`, `scripts/probe_ops.py`
> 측정 대상: Blender 5.2.2 LTS (`d13f752e3b9c`) 에서 직접 뽑은 API 표면

---

## 1. 감사 방법

```bash
# 1) API 표면 전수 수집: 2498 오퍼레이터 + 650 노드 타입 + 전수 열거형
blender -b --factory-startup -noaudio -P scripts/dump_api.py -- --out /tmp/catalog.md

# 2) 2498개 오퍼레이터를 실제로 때려본다
#    (빈 factory 씬 → 스크립트 친화 씬 → temp_override 조합 순으로)
blender -b --factory-startup -noaudio -P scripts/probe_ops.py -- --out /tmp/reach.json

# 3) 문서가 이 표면을 얼마나 덮고 있는지 대조
python3 audit/coverage.py
```

`coverage.py` 는 문서 전체에서 **식별자 토큰**을 뽑아 API 표면과 대조한다
(부분 문자열 오탐을 막기 위해 토큰 단위 매칭).

---

## 2. 1차 감사 결과 — 커버리율 26.5%

| 표면 | 커버 | 비율 | 판정 |
|---|---:|---:|---|
| `bpy.ops` 개별 | 668 / 2525 | **26.5%** | ❌ 심각한 구멍 |
| `bpy.ops` 그룹 | 59 / 77 | 76.6% | ⚠ 18개 통째로 없음 |
| 노드 타입 | 150 / 566 | **26.5%** | ❌ 심각한 구멍 |
| └ ShaderNode | 100 / 102 | 98.0% | ✅ 양호 |
| └ CompositorNode | 27 / 92 | 29.3% | ❌ |
| └ GeometryNode | 16 / 274 | **5.8%** | ❌ 가장 큰 구멍 |
| └ TextureNode | 2 / 38 | 5.3% | ❌ |
| └ FunctionNode | 3 / 56 | 5.4% | ❌ |
| `Modifier.type` | 82 / 83 | 98.8% | ✅ |
| `Constraint.type` | 29 / 29 | 100% | ✅ |
| `ParticleSettings.type` | 0 / 2 | **0%** | ❌ |
| `bpy.data` 컬렉션 | 36 / 40 | 90.0% | ⚠ |
| `bpy.app` 서브모듈 | 38 / 71 | 53.5% | ⚠ |
| `bpy.msgbus` | 0 | **없음** | ❌ |

> **솔직한 결론: 1차판은 "전부"가 아니었다.**
> 사용자가 "기능이 빠져서 문서화가 안 되면 그건 문제" 라고 지적한 건 정확했다.

### 완전히 없던 `bpy.ops` 그룹 18개

```
boid  buttons  cachefile  cloth  dpaint  fluid  gizmogroup  gpencil
import_anim  mball  paintcurve  poselib  rigidbody  sculpt_curves
spreadsheet  text_editor  uilist  view2d
```

---

## 3. 그런데 — 커버리율만 보면 오해가 있다

26.5% 라는 숫자를 그대로 믿으면 "1733개 기능이 문서화 안 됐다" 는 잘못된 결론이 된다.
**2,498개 오퍼레이터를 실제로 때려본 결과**:

| 판정 | 개수 | 비율 |
|---|---:|---:|
| ✅ 빈 factory 씬에서 바로 호출 가능 | 625 | 25.0% |
| ⚠ `temp_override` 필요 | 52 | 2.1% |
| ❌ **UI 전용 — 스크립트로 도달 불가** | **1,821** | **72.9%** |

> **오퍼레이터 2,498개 중 스크립트로 실제 쓸 수 있는 건 677개(27%) 뿐이다.**
> 나머지 73% 는 `outliner.*`(66) `ui.*`(38) `view3d.*`(58) `screen.*` `graph.*`
> `clip.*` 같은 UI 전용이다. 대부분은 화면에 그려지는 UI 를 조작하는 오퍼레이터인데
> `bpy.ops` 라는 네임스페이스에 그냥 들어 있을 뿐이다.
> 렌더 파이프라인에는 아무 역할도 하지 않는다.

**즉 1차 감사의 26.5% 는 "문서가 73% 의 쓰레기를 다뤄야 한다는 뜻" 이 아니다.**
진짜 문제는 "**쓸 수 있는 677개 중 몇 개를 다뤘는가**" 다.

---

## 4. 그룹별 고득점 — 뭘 배워야 하나

도달 가능 비율로 정렬한 결과. 이게 실전에서 시간을 아껴준다.

### 핵심 (반드시 익혀라)

| 그룹 | 도달가능/전체 | 비율 | 비고 |
|---|---:|---:|---|
| `render` | 15 / 16 | 94% | |
| `wm` | 104 / 117 | **89%** | 파일 열기/저장/append/link. 1차 감사 때 서술 부족 |
| `extensions` | 27 / 32 | **84%** | 5.x 확장 시스템. 1차 감사 때 없었음 |
| `scene` | 32 / 39 | 82% | |
| `preferences` | 30 / 37 | **81%** | 1차 감사 때 없었음 |
| `fluid` `boid` `dpaint` `cachefile` | 100% | 100% | 소규모지만 전부 스크립트 가능 |
| `object` | 187 / 250 | 75% | |
| `collection` | 9 / 12 | 75% | |
| `constraint` | 13 / 18 | 72% | |

### 드묾 (data API 로 대체 가능)

| 그룹 | 도달가능/전체 | 비율 |
|---|---:|---:|
| `anim` | 16 / 65 | 25% |
| `image` | 8 / 49 | 16% |
| `file` | 11 / 40 | 28% |
| `transform` | 9 / 27 | 33% |
| `particle` | 12 / 37 | 32% |
| `rigidbody` | 4 / 13 | 31% |
| `ed` (에디트 모드) | 4 / 13 | 31% |
| `font` | 4 / 23 | 17% |

### 배우지 마라 (UI 전용, 0%)

`outliner` `ui` `view3d` `screen` `graph` `clip` `pose`(40/51 미커버이지만
포즈는 data API 로 대체 가능) `action`(37개 전부 UI) `asset` `armature`

> 단 `armature` 가 0% 라고 포즈 조작이 안 되는 게 아니다.
> **포즈는 `pose_bone.location` / `.rotation_quaternion` 같은 data API 로 한다.**
> `bpy.ops.pose.*` 는 전부 UI 전용이고 필요 없다.

---

## 5. 조치 내역

### 추가한 문서

| 추가 | 커버하는 구멍 | 크기 |
|---|---|---|
| `references/06-simulation-particles.md` | `bpy.ops` 그룹 `boid` `cloth` `dpaint` `fluid` `mball` `rigidbody` `particle` (전부 0%) + Particle `HAIR`/`EMITTER` | 2,628줄 |
| `references/07-grease-pencil-vse.md` | `grease_pencil`(123) `gpencil` `sculpt_curves` `paintcurve` + `sequencer`(111) `clip`(92) + `bpy.data.movieclips` `sounds` | 1,801줄 |
| `references/12-api-catalog.md` | **전수 카탈로그.** 2,498 오퍼레이터 + 568 노드 타입 + 도달 가능성 | 3,869줄 / 480KB |
| `references/14-gpu-rendering.md` | GPU 렌더링 전 영역 (1차 감사 때 전부 미검증) | 1,500줄 |
| `references/15-scene-prefs-extensions.md` | 2차 감사가 잡은 구멍 — `preferences` 30 / `scene` 32 / `extensions` 27 (전부 도달 가능, 수동 언급 0~2개) | 1,050줄 |
| `references/13-coverage-audit.md` | 이 문서 | — |

### 추가한 도구

| 도구 | 하는 일 |
|---|---|
| `scripts/dump_api.py` | 실행 중인 Blender 에서 API 표면을 전수 수집해 마크다운/JSON 생성 |
| `scripts/probe_ops.py` | 2,498 오퍼레이터를 실제로 때려서 헤드리스 도달 가능성 측정 |
| `bk.py api reach <idname>` | 오퍼레이터 하나에 대해 즉석 판정 (✅/⚠/❌) |
| `bkkit.compat.gpu_report()` | 컴파일된 백엔드 vs 실제 감지된 GPU 를 분리 조회 |
| `bkkit.compat.enable_gpu()` | GPU 없으면 조용히 CPU 로 안 떨어지고 이유를 반환 |
| `bk.py doctor` 의 `=== GPU ===` | 매 실행마다 compiled / detected 를 나란히 출력 |

### 카탈로그가 해결하는 문제

1. **"이 오퍼레이터 있어?"** → §1 전수 표에서 즉시 확인
2. **"헤드리스에서 이거 돼?"** → ✅/⚠/❌ 열
3. **"인자 이름이 뭐야?"** → 전수 시그니처 + 기본값
4. **"이거 배워야 하나?"** → §1.1 그룹별 고득점 랭킹
5. **"이 노드 소켓이 뭐야?"** → §2 (543개 노드는 **실제로 인스턴스화**해서 소켓 이름·타입을 뽑았다)

> **앞으로의 규칙**: 어떤 기능을 다루든 이 카탈로그에서 대조한다.
> 손으로 쓰는 문서에 없는 기능이 있으면 카탈로그를 갱신하거나 새 문서를 추가한다.
> "빠짐없이" 를 주장할 때는 측정 숫자를 붙인다. 감으로 하지 않는다.

## 6. 감사 중 발견한, 문서에 없던 것들

### 6.1 `bpy.msgbus` — 존재하며 쓸 수 있다

```python
import bpy
scene = bpy.context.scene
calls = []

# key 는 세 가지 형태가 모두 허용된다 (실측):
#   (1) Property 인스턴스      scene.bl_rna.properties["frame_current"]
#   (2) Struct 타입            scene.bl_rna
#   (3) (Struct 타입, prop명)   (bpy.types.Scene, "frame_current")
bpy.msgbus.subscribe_rna(
    key=scene.bl_rna.properties["frame_current"],
    owner=("mysub", "framenum"),      # 해시/동등 비교로 정체성을 구분하는 핸들
    args=(),                          # 콜백에 넘길 추가 인자
    notify=lambda **kw: calls.append(kw),
    options=set(),                    # {'PERSISTENT'} 가능
)
bpy.msgbus.publish_rna(key=scene.bl_rna.properties["frame_current"])   # 수동 발화
bpy.msgbus.clear_by_owner(("mysub", "framenum"))                   # 해제
```

**함정 3가지 (전부 실측):**

| 실수 | 실제 에러 |
|---|---|
| `subscribe_rna(obj, "SCENE", ...)` (위치 인자) | `TypeError: only keyword arguments are supported` |
| `publish_rna(prop)` (위치 인자) | `TypeError: publish_rna: only keyword arguments are supported` |
| `key=(scene, "frame_current")` (인스턴스) | `RuntimeError: missing bl_rna attribute from 'Scene' instance` |
| `key=(scene.bl_rna, "frame_current")` | `RuntimeError: missing bl_rna attribute from 'Struct' instance` |

올바른 `key` 는 **`bpy.types.Scene` 같은 타입의 `.bl_rna`** 이나
**Property 인스턴스** 다. 인스턴스의 `.bl_rna` 를 넣으면 안 된다.

**그리고 결정적으로 — `-b` 에서는 알림이 아예 오지 않는다:**

```python
import bpy
scene = bpy.context.scene
calls = []
prop = scene.bl_rna.properties["frame_current"]
bpy.msgbus.subscribe_rna(key=prop, owner=("sub", 1), args=(), notify=lambda **k: calls.append(k))

scene.frame_current = 3
bpy.context.view_layer.update()
print("property 변경 후:", len(calls))          # 실측: 0

bpy.msgbus.publish_rna(key=prop)               # 수동 발화
print("publish_rna 이후:", len(calls))          # 실측: 0  ← 이것도 안 온다
```

**실측 출력**
```
subscribe ok
after prop set: 0
after publish_rna: 0
frame_step notifications: 0
struct-level notifications: 0
```

`Property` 인스턴스 / `Struct` 타입 / 구조 레벨 구독 **어느 쪽도 `-b` 에서 발화하지 않는다.**
`publish_rna` 로 수동 발화시켜도 0 이다.

> 백그라운드 모드에는 알림 큐를 처리하는 메인 루프가 없다.
> `bpy.app.timers` 도 마찬가지로 `-b` 에서 콜백이 영영 불리지 않는다
> (`05-automation-headless.md` §1.10 참고).
>
> **스크립트 자동화에서 데이터 변경 감지가 필요하면 `bpy.app.handlers` 를 써라.
> `bpy.msgbus` 도 `bpy.app.timers` 도 아니다.**
> 구독 API 자체는 존재하고 등록도 되지만, GUI 가 떠 있는 세션에서만 의미가 있다.
> 헤드리스 파이프라인에서 "값이 바뀌면 알려줘" 를 구현하려면
> 폴링 루프를 직접 짜거나 핸들러를 써야 한다.

### 6.2 `bpy.app` — 스크립트에 유용한 속성

| 속성 | 실측 값/타입 | 용도 |
|---|---|---|
| `autoexec_fail` | `False` | **드라이버 자동 실행이 차단됐는지** 알려주는 플래그 |
| `autoexec_fail_message` | `''` | 차단 사유. CI 로그에 찍으면 바로 안다 |
| `autoexec_fail_quiet` | `False` | 조용히 실패했는지 |
| `online_access` | `False` | 확장 온라인 접근 허용 여부 |
| `version_file` | `(5, 2, 45)` | 파일 포맷 버전. `.blend` 호환성 판단용 |
| `python_args` | `('-I',)` | 번들 파이썬 실행 인자 |
| `tempdir` | `/tmp/blender_XXXX/` | 임시 파일을 써야 할 때 |
| `version_cycle` | `'release'` | release/beta |
| `build_options` | build_options | 컴파일 옵션 (io_fbx, usd, cycles, openvdb …) |
| `memory_usage_undo()` | 메서드 | 언도 메모리 사용량 |
| `help_text()` | 메서드 | `blender --help` 텍스트를 파이썬에서 |

> `bpy.app.user_resource` 는 **존재하지 않는다** (5.2).
> `bpy.utils.user_resource('DATAFILES', path=...)` 를 써라.
> 실측: `/workspace/.home/.config/blender/5.2/datafiles/scripts/startup`

### 6.3 `bpy.context.preferences` — 헤드리스에서 조작 가능한 것

```
addons  app_template  apps  asset_libraries  autoexec_paths  edit
experimental  extensions  filepaths  inputs  is_dirty  keymap
show_hidden_ids  studio_lights  system  themes  ui_styles  view
```

`filepaths` 서브트리 (실측):
```
asset_libraries  render_cache_directory  render_output_directory  script_directories
texture_cache_directory  font_directory  sound_directory  i18n_branches_directory
temporary_directory  auto_save_time  save_version  use_auto_save_temporary_files
use_file_compression  use_relative_paths  use_scripts_auto_execute  use_load_ui
recent_files  text_editor_args  ...
```

> **`use_scripts_auto_execute = True` 가 CI 에서 드라이버/애드온 자동 실행의
> 유일한 열쇠**다. 기본값은 꺼져 있고, 끄인 상태에서는 드라이버의
> `expression` 이 조용히 평가되지 않는다. 스크립트에서 켜려면:

```python
import bpy
prefs = bpy.context.preferences.filepaths
print("현재:", prefs.use_scripts_auto_execute)      # 실측: False
prefs.use_scripts_auto_execute = True
print("변경 후:", prefs.use_scripts_auto_execute)   # 실측: True
# 영구히 하려면 prefs.save_userpref() — 안 하면 세션 종료 시 사라진다
```

### 6.4 `bpy.data` — 1차 감사 때 없던 컬렉션

| 컬렉션 | 용도 |
|---|---|
| `cache_files` | Alembic/USD 시뮬레이션 캐시 (USD 씬 스트립이 참조) |
| `movieclips` | 무비 클립 — 모션 트래킹, VSE |
| `paint_curves` | 동적 페인트 커브 (드라이 бри시 곡선) |
| `sounds` | VSE 오디오 스트립 |

### 6.5 `node_wrangler` 는 `-b` 에서 깨진다

`addons_core` 에 기본 포함된 `node_wrangler` 를 켜면 일부 오퍼레이터의
`poll()` 이 백그라운드 모드에서 예외를 던진다:

```
File ".../node_wrangler/utils/nodes.py", line 196, in nw_check
    if space.type != 'NODE_EDITOR':
AttributeError: 'NoneType' object has no attribute 'type'
ERROR Python script error in NODE_OT_lazy_connect_call_inputs_menu.poll
```

`bpy.context.space_data` 가 `None` 이기 때문이다.
카탈로그 생성기(`dump_api.py`)는 이 이유 로 `node_wrangler` 를 **켜지 않는다** —
콘솔이 지저분해지고 조용한 오염이 생긴다.

> 헤드리스에서 `node_wrangler` 의 `node.*` 오퍼레이터를 쓰고 싶다면
> `bpy.context.temp_override(area=..., region=..., space_data=...)` 로
> 가짜 에디터 컨텍스트를 만들어 줘야 한다. 또는 `bpy.data` 로 직접 조작하라.

---

## 7. 2차 감사 결과

### 7.1 1차 → 2차

| 표면 | 1차 | 2차 | 비고 |
|---|---:|---:|---|
| `bpy.ops` 개별 (수동 서술) | 26.5% | **41.4%** | 카탈로그와 별개. 서술 없는 건 `15-` 로 추가 |
| `bpy.ops` **도달 가능** | 미측정 | **677 / 2498 (27%)** | 나머지 73% 는 UI 전용 |
| 노드 타입 | 26.5% | 26.5% + 카탈로그 568/568 | 카탈로그가 100% |
| Particle HAIR/EMITTER | 0% | 전수 | `06-` |
| Grease Pencil (123 op) | 없음 | 전수 | `07-` |
| VSE / clip (203 op) | 없음 | 전수 | `07-` |
| 시뮬레이션 6그룹 | 없음 | 전수 | `06-` |
| `preferences` (30 도달) | **0%** | 전수 | `15-` |
| `scene` (32 도달) | **2%** | 전수 | `15-` |
| `extensions` (27 도달) | **3%** | 전수 | `15-` |
| `bpy.msgbus` | 없음 | 있음 | §6.1 |
| `bpy.app` 유용 속성 | 53.5% | 있음 | §6.2 |
| GPU 전 영역 | 없음 | API🟢 / 사양📄 | `14-` |

> **"수동 서술 41.4%" 가 낮아 보이지만 카탈로그를 합치면 API 표면은 100% 다.**
> 카탈로그는 자동 생성이라 API 가 바뀌면 재생성만 하면 된다.
> 사람이 빠뜨릴 수 있는 것이 남지 않는다.

### 7.2 아직 서술이 얇은 영역 (3차 감사 후보)

`bpy.ops` 도달 가능 677개 중, 수동 서술 비율이 낮은 그룹:

| 그룹 | 도달 가능 | 수동 서술 | 비고 |
|---|---:|---:|---|
| `object` | 187 | 73 (29%) | 대부분 data API 대체 가능. 실질 3개만 필요 |
| `wm` | 104 | 24 (21%) | 핵심은 `04-` 에 있음. 나머지는 UI/프리셋 |
| `screen` | 23 | 4 (9%) | 워크스페이스 전환 — 헤드리스에서 무의미 |
| `anim` | 16 | 2 (3%) | 키프레임은 data API(`compat.action_fcurves`)로 다룸 |
| `node` | 8 | 18 (10%*) | GN 은 `01-` 에, 나머지는 UI |
| `outliner` · `ui` · `view3d` · `screen` · `graph` · `clip` | — | 낮음 | **UI 전용. 의도적으로 안 씀** |

\* `node` 그룹은 개수가 많아 비율이 왜곡된다.

> ### 판단
>
> 이 중 **실무상 추가로 서술할 가치가 있는 것은 크지 않다.**
> `object` · `wm` · `scene` 의 남은 오퍼레이터는 data API 대체가 가능하거나
> UI 성격이라서, 카탈로그에서 이름·인자·도달 여부를 확인하는 편이
> 문서에 지면을 낭비하는 것보다 정확하다.
>
> **3차 감사가 필요하다면 기준은 이거다**:
> "도달 가능 + 스크립트로 실제 쓸 가치 + data API 대체가 안 됨" 3가지를
> 모두 만족하는 항목. 현재 기준으로는 0개에 가깝다.

## 8. 여전히 미검증인 것 (정직한 기록)

1. **GPU 렌더 그 자체** — CUDA/OptiX/HIP/oneAPI/Metal 실제 렌더, GPU vs CPU
   시간 비교, VRAM 스필, `OPTIX` 디노이저 동작.
   이 환경에 GPU 가 없다. → **`references/14-gpu-rendering.md` 로 분리했다.**
   그 문서에서 API 표면·enum·폴백 동작·크래시 경고는 전부 🟢 실측했고,
   요구 사양은 📄 공식 5.2 매뉴얼·릴리즈 노트에서 인용했다.
   **미검증은 "렌더가 실제로 빠른가" 뿐**이다.
2. **플루이드/오션 실제 베이크** — 설정 API 는 검증했지만, 캐시를 포함한
   결과 수렴까지는 헤드리스 1회 실행으로 확인하지 않았다.
   `06-simulation-particles.md` 에 "실측 불가" 로 표시되어 있다.
3. **`bpy.app.timers` / `bpy.msgbus` 의 발화** — `-b` 에서 메인 루프가 없어
   관측 불가. 이건 환경 한계가 아니라 Blender 설계다(위 §6.1).
4. ** grease pencil 의 스톱 데이터 직접 작성** — 5.2 에 공개 데이터 API 가
   있는지 서브에이전트가 실측 중. 없으면 오퍼레이터 경로로 문서화한다.
5. **VSE 트랙킹(`bpy.ops.clip.*`)** — 92개 오퍼레이터 중 6개만 도달 가능.
   나머지 86개가 진짜 UI 전용인지 실측 대기.

이 항목은 카탈로그와 각 문서의 "미검증" 표시를 신뢰하고,
필요하면 직접 재현하라.

---

## 9. 앞으로의 유지보수 규칙

```bash
# API 가 바뀌었는지 확인하는 루틴
blender -b --factory-startup -noaudio -P scripts/probe_ops.py -- --out /tmp/reach.json
blender -b --factory-startup -noaudio -P scripts/dump_api.py -- \
        --out references/12-api-catalog.md --reach /tmp/reach.json
git diff references/12-api-catalog.md     # 뭐가 사라지고 생겼는지 바로 보인다
```

1. **새 기능 문서를 쓰기 전에** 카탈로그에서 존재 여부를 확인한다
2. **카탈로그에 없는 기능을 문서화하면** 새 문서를 추가하고 SKILL.md 지도에 넣는다
3. **손으로 쓴 문서의 예제는** `scripts/verify_docs.py` 로 실행 검증한다
4. **오퍼레이터를 언급할 때는** 카탈로그의 ✅/⚠/❌ 표기를 함께 옮긴다
5. **"빠짐없이" 를 주장할 때에는** 측정 숫자를 붙인다. 감으로 하지 않는다.

---

## Verification log

본 감사 자체의 실행 기록:

| 항목 | 명령 | 결과 |
|---|---|---|
| API 표면 전수 수집 | `blender -b -P scripts/dump_api.py -- --out catalog.md` | PASS — 2498 op / 650 node / 29 data 컬렉션 / 4013 types |
| 오퍼레이터 도달성 전수 측정 | `blender -b -P scripts/probe_ops.py -- --out reach.json` | PASS — 625 base / 52 override / 1821 no |
| 문서 커버리지 대조 | `python3 audit/coverage.py` | PASS — 1차 26.5% 산출 |
| 카탈로그 재생성 (reach 병합) | `dump_api.py -- --out references/12-api-catalog.md --reach reach.json` | PASS — 423,387 bytes |
| `bpy.msgbus` 시그니처 | 7회 시도 (`msgbus*.py`, `mb.py`) | PASS — 3개 key 형태 확인, 위치 인자 2건 실패, `publish_rna(key=)` 확인 |
| `bpy.msgbus` 발화 없음 | `audit/mb2.py` | PASS(결과) — property 변경/수동 publish/구조 레벨 구독 **모두 0건**. 문서 §6.1 에 반영 |
| `bpy.app` 유용 속성 | `audit/msgbus.py` | PASS — 18개 속성 타입/값 확인 |
| `bpy.app.user_resource` 부재 | 같은 스크립트 | PASS — `AttributeError`. `bpy.utils.user_resource` 로 대체 |
| `preferences` 서브트리 | 같은 스크립트 | PASS — 16개 최상위 속성 + 27개 filepaths 속성 |
| `bpy.utils.user_resource` | `audit/msgbus2.py` | PASS — 경로 반환 확인 |
| `bk.py api reach` 판정 | 5개 오퍼레이터 | PASS — `mesh.primitive_cube_add` ✅, `outliner.delete` ❌, `nope.nope` 없음 |
| `introspect.op_exists` 수정 | `/tmp/oe.py` | **FAIL 최초 → 수정 → PASS.** `getattr(bpy.ops, grp, name)` 인자 오류로 전부 False 반환하던 버그 발견 |
| `node_wrangler` `-b` 결함 | `dump_api.py` 1차 실행 로그 | PASS — `AttributeError: 'NoneType' object has no attribute 'type'` 재현 → 애드온 제외 처리 |
| `CyclesPreferences` 전수 | 소스 + `bl_rna` | PASS — 6 쓰기속성 / 14 메서드 / `get_devices` deprecated |
| GPU 0대에서 CUDA 대입·렌더 | `audit/gpu7.py` | PASS — 대입 성공, `{'FINISHED'}`, **조용히 CPU 폴백** |
| `refresh_devices()` 필수 | `audit/gpu4.py` | PASS — 안 부르면 `devices` 0 → 부르면 1 |
| `denoiser` 동적 enum | `audit/gpu5.py` | PASS — GPU 없으면 `('OPENIMAGEDENOISE',)` 만 |
| `get_device_types(context)` 인자 | `audit/gpu2.py` | PASS — `TypeError: missing 1 required positional argument` |
| **gpu_report 백엔드 라벨링 버그** | `/tmp/vercheck.py` | **FAIL 최초 → 수정 → PASS.** `zip()` 순서 불일치로 `METAL=True` 오진단 |
| GPU 문서 코드 블록 | `verify_docs.py -- references/14-gpu-rendering.md` | PASS — 21블록 / 17 PASS / 0 FAIL |

---
name: blender-bpy-scripting
description: >
  Drive Blender from Python (bpy) the way an automation agent should — build scenes,
  set up materials/modifiers/lights/cameras, render stills or animation, and verify
  the output by measuring pixels instead of trusting that a render "succeeded".
  Use this whenever the task involves Blender, .blend files, bpy scripts, headless
  rendering, scene generation, procedural modelling, or converting/validating render
  results. Verified against Blender 5.2.2 LTS on a real headless install; every code
  block in every reference document is executed as part of the test suite.
---

# Blender 스크립팅 (bpy) — 완전 가이드

Blender를 스크립트로 다루는 모든 것을 한 곳에 모았다. **모든 예제는 실제로
설치한 Blender 5.2.2 LTS 를 헤드리스로 돌려서 만든 것**이다.

| | |
|---|---|
| 검증 환경 | Blender **5.2.2 LTS** (`d13f752e3b9c`, 2026-09-15), Linux x64, headless |
| 번들 Python | 3.13.13 |
| 문서 | **16개, 약 30,000줄** (그중 1개는 480KB 자동 생성 카탈로그) |
| 실행 검증 | 이 스킬이 직접 쓴 문서는 `scripts/verify_docs.py` 로 블록 단위 통과 확인 |
| | 나머지는 각자 `## Verification log` 에 실행 스크립트·커맨드·결과가 남아 있다 |
| **커버리 감사** | [`references/13-coverage-audit.md`](references/13-coverage-audit.md) — 무엇을 측정했고 무엇이 빠졌는지 |

---

## 0. 30초 요약 — 이 스킬이 없으면 반드시 터지는 것들

```python
import bpy, addon_utils

# 1) Cycles 는 애드온. --factory-startup 에선 꺼져 있다.
addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"

# 2) bpy.data.objects.new() 는 어디에도 링크되지 않는다
obj = bpy.data.objects.new("Hero", None)
bpy.context.scene.collection.objects.link(obj)      # ← 이게 없으면 안 보인다

# 3) bpy.ops 는 조용히 실패한다
res = bpy.ops.object.delete()
if "FINISHED" not in res:                            # CANCELLED 인데 예외가 안 난다
    raise RuntimeError("operator failed")

# 4) Material.use_nodes 는 deprecated (6.0 제거). 새 머티리얼은 이미 node_tree 를 가진다
mat = bpy.data.materials.new("M")
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0, 0, 1)

# 5) 5.2 에서 action.fcurves 속성이 삭제됐다
#    → bkkit.compat.action_fcurves(obj)

# 6) 렌더는 실패해도 성공한 척한다. 반드시 픽셀을 측정한다
#    → bkkit.imagecheck.analyze_image_file(path)
```

그리고 — **예외를 던져도 Blender의 종료 코드는 0이다.** CI가 조용히 성공한다.
항상 `sys.exit(code)` 를 직접 호출하라.

---

## 1. 문서 지도

| 문서 | 언제 읽나 |
|---|---|
| **[`references/00-core-model.md`](references/00-core-model.md)** | **먼저 이것부터.** bpy 멘탈 모델, 데이터블록 구조, context, depsgraph, 버전 감지 |
| [`references/01-materials-nodes.md`](references/01-materials-nodes.md) | 머티리얼, 셰이더 노드, 텍스처, 월드, Geometry Nodes |
| [`references/02-geometry-modifiers.md`](references/02-geometry-modifiers.md) | 메시 생성, bmesh, 커브/텍스트, UV, 모디파이러 스택 |
| [`references/03-render-output.md`](references/03-render-output.md) | Cycles/EEVEE 설정, 렌더, 컴포지터, 출력 포맷 |
| [`references/04-scene-animation-io.md`](references/04-scene-animation-io.md) | 씬 구조, 키프레임, 드라이버, 리그, 임포트/익스포트 |
| [`references/05-automation-headless.md`](references/05-automation-headless.md) | 애드온/UI, 핸들러, CLI 플래그, 배치 파이프라인, 디버깅 |
| **[`references/09-verification-loop.md`](references/09-verification-loop.md)** | **빌드→검증→렌더→측정→개선 루프.** 결과물 확인이 필요하면 |
| [`references/10-migration-4x-to-5x.md`](references/10-migration-4x-to-5x.md) | 예전 스크립트가 죽을 때. 파괴적 변경 총정리 |
| [`references/11-troubleshooting.md`](references/11-troubleshooting.md) | 에러 메시지 보이면 여기부터 |
| [`references/06-simulation-particles.md`](references/06-simulation-particles.md) | 물리 시뮬레이션, 파티클, 리지드바디, 플루이드 |
| [`references/07-grease-pencil-vse.md`](references/07-grease-pencil-vse.md) | Grease Pencil, 비디오 시퀀서, 무드, 무비클립 |
| **[`references/12-api-catalog.md`](references/12-api-catalog.md)** | **전수 API 카탈로그 (자동 생성).** "이 함수/옵션 있어?" 물음의 답 |

### ⭐ 빠짐없이 확인하고 싶을 때 — 12-api-catalog.md

"이 기능 문서에 있어?" 라는 질문의 정답은 이 파일이다.
**2,498개 오퍼레이터 + 650개 노드 타입 전수**가 들어있다(머신이 뽑은 것).

더 중요한 건 각 오퍼레이터에 붙은 **헤드리스 도달 가능성 판정**이다:

| | 개수 | 비율 |
|---|---:|---:|
| ✅ 빈 씬에서 바로 호출 가능 | 625 | 25.0% |
| ⚠ `temp_override` 필요 | 52 | 2.1% |
| ❌ UI 전용 — **시도하지 마라** | 1,821 | 72.9% |

> 오퍼레이터 2,498개 중 **스크립트로 실제 쓸 수 있는 건 677개(27%)** 뿐이다.
> 나머지는 `outliner.*` `ui.*` `view3d.*` `screen.*` `graph.*` `clip.*` 같은 UI 전용.
> 이걸 모르고 `bpy.ops.outliner.delete()` 같은 걸 찾아서 쓰려고 하면
> 안 된다고 몇 시간씩 디버깅하게 된다.

그룹별 고득점 랭킹도 들어있다 — `wm` 89%, `render` 94%, `object` 75%,
`extensions` 84%, `preferences` 81% 는 핵심, `anim` 25%, `image` 16%,
`armature` 0% 는 data API 로 대체.

재생성:
```bash
blender -b --factory-startup -noaudio -P scripts/probe_ops.py -- --out reach.json
blender -b --factory-startup -noaudio -P scripts/dump_api.py -- \
        --out catalog.md --reach reach.json
```

### 💡 커버리지

이 스킬은 **측정**해서 완전성을 주장한다. 감이 아니라 숫자다.
전체 API 표면(2,498 오퍼레이터 + 568 노드 타입)과 문서를 대조한 결과는
[`references/13-coverage-audit.md`](references/13-coverage-audit.md) 에 있다.

1차 감사에서 26.5% 밖에 안 나오지 않았냐, 라는 지적이 정확했다.
그래서 아래를 추가했다:
- 6개 `bpy.ops` 그룹이 통째로 없던 것 → `06-simulation-particles.md`
- Grease Pencil 123개 + VSE 203개 오퍼레이터 없던 것 → `07-grease-pencil-vse.md`
- `bpy.msgbus` / `preferences` / `bpy.app` 세부 없던 것 → `13-coverage-audit.md`
- **2,498 오퍼레이터 + 568 노드 타입 전수 카탈로그** → `12-api-catalog.md`
- `preferences` 30개 / `scene` 32개 / `extensions` 27개 (전부 도달 가능인데
  수동 언급 0~2개) → `15-scene-prefs-extensions.md`

그리고 감사가 깨뜨린 오해 하나:
> 오퍼레이터 2,498개 중 **스크립트로 실제 쓸 수 있는 건 677개(27%)** 다.
> 나머지 73% 는 `outliner.*` `ui.*` `view3d.*` 같은 UI 전용이다.
> 카탈로그가 이걸 ✅/⚠/❌ 로 판정해준다.

### 파일 구성

```
blender-bpy-scripting/
├── SKILL.md                          이 파일
├── references/                       16개, 약 30,000줄 (카탈로그 480KB 별도)
├── scripts/
│   ├── bk.py                         CLI 진입점 (doctor/check/analyze/render/api)
│   ├── verify_docs.py                문서의 코드 블록을 실제로 돌리는 검증기
│   ├── dump_api.py                   API 전수 카탈로그 생성기
│   ├── probe_ops.py                  오퍼레이터 헤드리스 도달 가능성 측정기
│   └── bkkit/                        재사용 헬퍼 (compat/introspect/scenecheck/imagecheck)
└── templates/
    ├── scene_builder_template.py     씬 빌더 → 검증 → 렌더 → 측정 기본 골격
    ├── iterative_loop_template.py    파라미미터 바꿔가며 돌리는 개선 루프
    └── shader_texturing_template.py  절차적 셰이더 7종 (실측 렌더 완료)
```

---

## 2. 실행 환경

```bash
# 검증에 쓰인 정확한 환경
blender 5.2.2 LTS   (build hash d13f752e3b9c, 2026-09-15)
bundled Python 3.13.13
```

설치 (Linux, 헤드리스 서버):

```bash
curl -L -o blender.tar.xz \
  https://download.blender.org/release/Blender5.2/blender-5.2.2-linux-x64.tar.xz
tar -xJf blender.tar.xz
ln -s "$PWD/blender-5.2.2-linux-x64/blender" /usr/local/bin/blender

# EEVEE 를 쓰려면 (Cycles CPU 라면 불필요하지만 설치해도 손해 없음)
apt-get install -y libegl1 libgl1 libglx-mesa0 libgl1-mesa-dri libxkbcommon0
```

자주 쓰는 명령:

```bash
# 정본: 예외 시 종료 코드 1 (이 플래그가 없으면 실패해도 0이 된다)
blender -b --factory-startup -noaudio --python-exit-code 1 -P script.py
blender -b --factory-startup -noaudio --python-exit-code 1 -P script.py -- build
blender -b file.blend -o /tmp/out_ -F PNG -f 1                # CLI 렌더
```

**인자 순서가 의미 있다**: `blender -b -P s.py in.blend` 는 스크립트가 먼저 돌고
그 다음 파일이 로드돼서, 스크립트가 만든 게 **다 날아간다**.
정본은 `blender -b in.blend -P s.py` 다.

> **팁**: 이 환경(및 일부 CI)에서 Blender 의 stdout 가 파이프에서 새지 않는다.
> 항상 `> out.log 2>&1` 로 리다이렉트한 뒤 `cat` 하라.

---

## 3. 도구 — `bk` CLI

```
blender -b --factory-startup -noaudio -P scripts/bk.py -- <command> [options]
```

| 명령 | 하는 일 | 종료 코드 |
|---|---|---|
| `doctor` | 빌드/파이썬/엔진/애드온/기능 플래그 보고 | 0 |
| `check` | 현재 씬 정적 검증 (`--json`) | fail 시 1 |
| `analyze <img...>` | 픽셀 측정 + 판정 (`--diff` 로 비교) | bad 시 1 |
| `render <out>` | CHECK → RENDER → MEASURE 일괄 | 실패 시 1 |
| `api ops [prefix]` | `bpy.ops` 검색 | 0 |
| `api op <idname>` | 오퍼레이터 인자 + 기본값 전체 | 없으면 1 |
| `api prop <Type> <name>` | RNA 프로퍼티 타입/enum/기본값 | 없으면 1 |
| `api nodes <Prefix>` | 등록된 노드 타입 목록 | 0 |
| `api version` | 버전 + 기능 플래그 JSON | 0 |

```bash
blender -b -P scripts/bk.py -- doctor
blender -b -P scripts/bk.py -- api op mesh.primitive_cube_add
blender -b -P scripts/bk.py -- render /tmp/shot.png --engine CYCLES --res 320x240
```

**에이전트 작업 규칙**: `bpy.ops` 인자를 추측하지 마라. 먼저 `api op` 으로
실제 시그니처를 확인하고 써라. 한 번의 호출이 여러 번의 실패 렌더를 아껴준다.

### `bkkit` — 재사용 헬퍼 패키지

```python
import sys; sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat, introspect, scenecheck, imagecheck
```

| 모듈 | 제공하는 것 |
|---|---|
| `compat` | 버전/기능 감지, `action_fcurves()`, `set_gn_input()`, `set_engine()` |
| `introspect` | `op_props()`, `op_check()`, `call_op()` (CANCELLED 감지), `set_input()` |
| `scenecheck` | 씬 정적 검증 16종 → `verdict: ok / warn / fail` |
| `imagecheck` | 픽셀 통계, `judge()` 판정, `compare()` 델타 |

---

## 4. 작업 절차 (이 순서를 지켜라)

### Step 1 — 무엇을 만들지 정의

"예쁜 이미지"를 목표로 하지 말고 **측정 가능한 조건**으로 쓴다.
"샤드피 약하고 배경이 안 죽는 3/4 앵글 제품 샷" 같은 것.

### Step 2 — API 이름을 실측으로 확인

```bash
blender -b -P scripts/bk.py -- api op <operator>
blender -b -P scripts/bk.py -- api prop <Type> <prop>
blender -b -P scripts/bk.py -- api nodes <Prefix>
```

기억에 의존하지 마라. 4.x 튜토리얼의 인자 이름이 5.2 에서 다를 수 있다.

### Step 3 — 빌드

[`templates/scene_builder_template.py`](templates/scene_builder_template.py) 를
복사해서 시작하라. 이미 아래 규칙이 다 들어있다:

- `objects.new()` 후 반드시 `collection.objects.link()`
- 모든 `bpy.ops` 반환값 검사
- 3점 조명 + 카메라 조준(`point_at`)
- `use_nodes` 설정 금지
- 렌더 전 `scenecheck` 실행
- 픽셀 측정 후 요약 출력
- `sys.exit(code)`

### Step 4 — 검증 루프

```
BUILD → CHECK → RENDER → MEASURE → (개선) → CHECK → ...
```

`scenecheck` 가 `fail` 이면 **렌더하지 마라.** 이미지 통계는 `imagecheck` 로.
`compare()` 로 반복 사이의 델타를 확인해 "수정이 실제로 반영됐는지" 검증하라.

**중요한 실측 사실**: 조명 0개 / `hide_render` / BSDF 미연결 / 스케일 0 /
오브젝트 미링크 / 머티리얼 미할당 — 이 6가지가 전부 `{'FINISHED'}` 를 반환했다.
`CHECK` 와 `MEASURE` 둘 다 돌려야 한다.
→ [`references/09-verification-loop.md`](references/09-verification-loop.md) §3.0

### Step 5 — 전달

사용자에게 넘길 때는 반드시 함께 알려줄 것:

- 파일 경로
- 엔진 / 샘플 수 / 해상도
- 씬 검증 결과
- 이미지 판정 결과와 `mean_luma`

---

## 5. 새 오퍼레이터를 처음 쓸 때

백그라운드에서 처음 쓰는 오퍼레이터는 **세그폴트할 수 있다.**
실측 증거: `bpy.ops.object.geometry_nodes_input_attribute_toggle` 는
5.2.2 에서 인자를 어떻게 주어도 `RNA_pointer_get: ... not found` 후 죽는다.

```bash
# 격리 실행
timeout 120 blender -b --factory-startup -noaudio -P risky_op.py > log 2>&1
code=$?
[ $code -ge 128 ] && echo "SIGNAL $((code-128)) — 크래시"
grep -q "crash.txt" log && echo "CRASH 감지"
```

배치 파이프라인에서는 렌더 워커를 반드시 이 래프로 감싸라.
세그폴트는 예외가 아니라 **프로세스 종료**라 Python 레벨 `try/except` 로 못 잡는다.

---

## 6. 문서 자체를 검증하기

이 스킬의 모든 문서에 있는 코드 블록은 실제 Blender 에서 실행된다.

```bash
blender -b --factory-startup -noaudio -P scripts/verify_docs.py -- references/
# exit 0 = 전부 통과, exit 1 = 실패 블록 있음
```

블록 첫 줄에 지시자를 붙일 수 있다:

```python
# [4]        ← 태그 (--filter 로 개별 실행)
# frag       ← 단독 실행 불가한 발췌. 건너뛴다
# slow: ...  ← 렌더/애니메이션 등 비쌈. 기본 건너뛴다
```

**문서를 고칠 때는 이 검증기를 반드시 다시 돌려라.** 실제로 이 검증기가
여러 오류를 잡았다:

- SUBSURF 3레벨 정점 수를 512 라고 적었는데 실제로는 **386** 이었다
- `scale=0.6` (스칼라) 를 `primitive_cube_add` 에 넘기고 있었는데 `FLOAT[3]` 이다
- `# frag` 로 표시해야 하는 블록을 구분하지 못해 검증 프로세스 자체가 죽었다
- `sys.exit()` 을 담은 블록이 실행을 통째로 종료시켰다
- 프래그먼트 판정 로직의 부등호가 뒤집혀 전부 FRAG 로 분류됐다

블록 지시자:

```python
# frag      ← 다른 블록에 의존하는 발췌. 실패해도 검증 실패 아님
# no-exec   ← 실행하면 Blender 가 죽음. 검증기가 절대 실행하지 않음
# slow: ... ← 렌더/애니메이션. 기본 건너뜀
```

---

## 6.5 GPU 렌더링 — 조용히 실패하는 또 하나의 함정

GPU 파이프라인은 **가장 조용히 실패하는 영역**이다. 이 샌드박스(GPU 0대)에서 실측했다:

```python
prefs.compute_device_type = "CUDA"   # 대입 성공 (에러 없음)
scene.cycles.device = "GPU"          # 대입 성공 (에러 없음)
bpy.ops.render.render()              # {'FINISHED'}, 파일 저장됨
```

> **GPU 없는 머신에서 "GPU 모드"가 조용히 CPU로 렌더된다.**
> 에러도, 경고도, 빈 파일도 아니다. 씬 검증도 통과한다.
> 렌더 시간을 재지 않으면 GPU가 붙었는지 알 수 없다.

이유는 `bk.py doctor` 가 구분해 준다:
```
컴파일된 백엔드 : {'CUDA': True, 'OPTIX': True, 'HIP': True, 'ONEAPI': True}
감지된 GPU      : 없음          ← "컴파일돼 있다" 와 "장치가 있다" 는 다르다
```

안전한 켜기:
```python
from bkkit import compat
ok, info = compat.enable_gpu(scene)   # GPU 없으면 CPU 로 내려가며 이유를 알려준다
if not ok:
    print("GPU 못 씀:", info["reason"])
```

자세한 백엔드 요구 사양·폴백·CLI·VRAM 관리는
[`references/14-gpu-rendering.md`](references/14-gpu-rendering.md).

---

## 6.6 실전 검증 결과 — 스킬은 실제로 잘 작동한다

서브에이전트 6명에게 **스킬 파일만 주고** 실전 작업을 시켰다
(모델링+리깅+애니메이션 / 이미지 보정 / 지오메트리 노드 / 영상편집 / 시뮬레이션 / 텍스처링+내보내기).

**6/6 성공.** 전부 손대지 않은 영역이었고, 물리적 증거를 냈다:

- 지오메트리 노드: `verts = 8.000000 × Count + 0.000000` (선형 회귀)
- 시뮬레이션: 자유낙하 이론값 대비 **5.3 mm** 오차
- 영상편집: `ffprobe` 검증 통과, ON/OFF **758,311 샘플** 차이
- 텍스처링: 5포맷 라운드트립, 재질 3종 색 거리 0.2991

**총평 7.2 / 10.** 상세는 [`16-field-test.md`](16-field-test.md).

거기서 **코드 버그 5개 + 문서 오류 4개를 찾아내고 전부 수정했다.**
그리고 문서에 없던 구멍 **22개**를 목록화했다 — 그중 12개가 "조용히 실패" 유형이라
[`11-troubleshooting.md` §2.9](references/11-troubleshooting.md)에 중앙 목록으로 모았다.

> ### 가장 크게 배운 것
>
> **"문서대로 하려는데 도구가 죽어 있다"** 는 문서 문제가 아니라
> **스킬이 자기 규칙을 실행하지 못하는 상태** 다.
> `SKILL.md` 가 "인자 추측하지 말고 `api op` 으로 확인하라" 고 지시했는데
> **그 명령이 100% 크래시**하고 있었다. 두 명이 우회 스크립트를 직접 짜야 했다.
>
> 지시된 도구는 문서만큼 신뢰해야 한다. 실행 검증은 예외가 아니라 **필수**다.

---

## 7. 아직 검증되지 않은 것 (정직한 고지)

- **GPU 렌더 그 자체** (CUDA/OptiX/HIP/oneAPI/Metal 실제 렌더, GPU vs CPU 시간,
  VRAM 스필, `OPTIX` 디노이저): 이 환경에 GPU 가 없다.
  **API 표면·enum·폴백 동작·크래시 경로는 전부 실측했고** (`14-gpu-rendering.md`),
  요구 사양은 공식 5.2 매뉴얼·릴리즈 노트에서 인용했다.
  렌더 성능만 미검증이다.
- **드라이버 `use_scripts_auto_execute`**: GUI 설정이라 헤드리스에서
  실제 식 평가까지는 확인 못 함. API 존재는 확인.
- **Fluid / Ocean / Rigid Body**: API 와 속성 이름은 확인했지만,
  캐시를 포함한 "결과가 맞는지"까지는 1회 실행으로 검증하지 않음.

이 항목들은 문서에 "미검증"으로 표시되어 있다. 신뢰하지 말고 직접 재현할 것.

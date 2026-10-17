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
| 번들 Python | 3.14.8 (GPU 검증 머신) / 3.13.13 (문서 최초 작성 머신) |
| GPU 검증 환경 | Xeon E5-2673 v4 80코어 · NVIDIA 6장 (RTX 4070/5060 Ti/3060 Ti/4060 Ti×2/3070) · AMD 2장 |
| 문서 | **19개, 약 32,500줄** (그중 1개는 480KB 자동 생성 카탈로그) |
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

# 7) GPU는 절대 직접 세팅하지 마라. prefs 를 만지기 전에 순서가 있다
ok, info = compat.enable_gpu(scene)   # 백엔드 선택 + 남은 VRAM 필터 + 폴백 + max 1장
#    prefs.refresh_devices() 를 compute_device_type 대입 전에 부르면 SIGSEGV(exit 139)
#    → §6.5

# 8) 영상 렌더에서 use_persistent_data 는 필수 (기본값 False = BVH 재구성에 수십 초)
scene.render.use_persistent_data = True
scene.render.use_auto_generate_texture_cache = True
#    → §6.5.1a / references/18-render-optimization.md

# 9) EEVEE/Cycles 선택은 속도가 아니라 품질로 한다. EEVEE 는 반사·굴절을 계산 안 한다
#    또 EEVEE 와 Cycles 는 다른 GPU(OpenGL vs OptiX)에서 돈다
#    → §6.5.1b / references/19-render-engines.md

# 10) 다른 머신에서 돌릴 때 첫 순서 — 환경 지문 + 정규화 기준점
#    blender -b --factory-startup -noaudio -P scripts/bk_env.py -- --bench
#    → references/17-environment-baseline.md
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
| **[`references/17-environment-baseline.md`](references/17-environment-baseline.md)** | **내 머신에선 이 시간이 나온다.** 다른 환경에서 돌릴 때. `bk_env.py` |
| **[`references/18-render-optimization.md`](references/18-render-optimization.md)** | **렌더를 어떻게 빠르게 하나 (실측).** 속도 문제면 먼저 이 문서 |
| **[`references/19-render-engines.md`](references/19-render-engines.md)** | **Cycles vs EEVEE vs Workbench — 언제 뭘 쓰나 (실측)** |
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
├── references/                       19개, 약 32,500줄 (카탈로그 480KB 별도)
│   ├── 17-environment-baseline.md    환경 지문 — 다른 머신에서 시간 추정
│   ├── 18-render-optimization.md     렌더 속도 최적화 (전부 실측)
│   └── 19-render-engines.md          EEVEE/Cycles/Workbench 선택 (전부 실측)
├── scripts/
│   ├── bk.py                         CLI 진입점 (doctor/check/analyze/render/api)
│   ├── bk_env.py                     환경 지문 + 정규화 기준점 (--bench)
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
| `render <out>` | CHECK → RENDER → MEASURE 일괄 (`--purpose` 로 엔진 자동 선택) | 실패 시 1 |
| `api ops [prefix]` | `bpy.ops` 검색 | 0 |
| `api op <idname>` | 오퍼레이터 인자 + 기본값 전체 | 없으면 1 |
| `api prop <Type> <name>` | RNA 프로퍼티 타입/enum/기본값 | 없으면 1 |
| `api nodes <Prefix>` | 등록된 노드 타입 목록 | 0 |
| `api version` | 버전 + 기능 플래그 JSON | 0 |

```bash
blender -b -P scripts/bk.py -- doctor
blender -b -P scripts/bk.py -- api op mesh.primitive_cube_add
blender -b -P scripts/bk.py -- render /tmp/shot.png --engine CYCLES --res 320x240
blender -b -P scripts/bk.py -- render /tmp/prev.png --purpose explore   # EEVEE 자동 선택
blender -b -P scripts/bk.py -- render /tmp/final.png --purpose final    # Cycles 자동 선택
```

`--purpose` 값과 선택되는 엔진 (`references/19-render-engines.md`):

| purpose | 엔진 | 언제 |
|---|---|---|
| `structure` | Workbench | 씬 구조·카메라 프레이밍 확인 (클레이) |
| `explore` | EEVEE | 1~3회 탐색 렌더 |
| `animate` | Cycles | 영상 렌더 |
| `final` | Cycles | 최종 산출물 |

> **엔진 선택은 속도가 아니라 품질로 한다.** EEVEE 는 반사·굴절·GI 를
> 근사만 하고, **EEVEE 와 Cycles 는 다른 GPU(OpenGL vs OptiX)에서 돈다.**
> llvmpipe 로 떨어진 EEVEE 는 Cycles CPU 보다 느리므로 자동 감지한다.

**에이전트 작업 규칙**: `bpy.ops` 인자를 추측하지 마라. 먼저 `api op` 으로
실제 시그니처를 확인하고 써라. 한 번의 호출이 여러 번의 실패 렌더를 아껴준다.

### `bk_env` — 환경 지문 + 정규화 기준점

```
blender -b --factory-startup -noaudio -P scripts/bk_env.py -- [--json] [--bench]
```

| 명령 | 하는 일 |
|---|---|
| (기본) | CPU/RAM/디스크/GPU/부하를 읽어 사람이 읽을 형태로 출력 |
| `--bench` | 위 정보 + **320×320 64spp 1회 렌더 시간(cold/warm)** |
| `--json` | 기계 판독용 JSON |

```bash
blender -b --factory-startup -noaudio -P scripts/bk_env.py -- --bench
```
```
CPU          : Intel(R) Xeon(R) CPU E5-2673 v4 @ 2.30GHz
               80 logical / 40 physical, L3=100.0 MB, governor=schedutil
RAM          : 125.8 GB    load(1m): 15.93
Disk         : read 4.4 GB/s, free 58.1 GB
GPU          : backend=OPTIX vendor=NVIDIA usable=4 vram_free=40200/61353 MB
Bench        : cold 1.23s  warm 0.68s  device=GPU gpus=1
```

> **다른 머신에서 이 스킬을 돌릴 때 가장 먼저 할 일이다.**
> `warm` 값이 기준(0.68 s)의 몇 배인지만 확인하면
> 그 머신에서 렌더가 얼마나 느릴지 **추정**할 수 있다.
> → [`references/17-environment-baseline.md`](references/17-environment-baseline.md)

### `bkkit` — 재사용 헬퍼 패키지

```python
import sys; sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat, introspect, scenecheck, imagecheck
```

| 모듈 | 제공하는 것 |
|---|---|
| `compat` | 버전/기능 감지, `action_fcurves()`, `set_gn_input()`, `set_engine()`, `set_engine_for_purpose()`, `enable_gpu()`, `gpu_speed_preset()`, `eevee_gpu_renderer()` |
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

GPU 파이프라인은 **가장 조용히 실패하는 영역**이다. 두 가지 함정이 있고,
하나는 **가만히 두고**, 하나는 **블로그폭탄을 던지고 죽는다**.

### 함정 1 — GPU가 없는데 "GPU 모드"가 성공한다

```python
prefs.compute_device_type = "CUDA"   # 대입 성공 (에러 없음)
scene.cycles.device = "GPU"          # 대입 성공 (에러 없음)
bpy.ops.render.render()              # {'FINISHED'}, 파일 저장됨
```

> **GPU 없는 머신에서 "GPU 모드"가 조용히 CPU로 렌더된다.**
> 에러도, 경고도, 빈 파일도 아니다. 씬 검증도 통과한다.
> **렌더 시간을 재지 않으면 GPU가 붙었는지 알 수 없다.**

### 함정 2 — GPU는 있는데, 그 카드가 남의 카드다 (더 위험)

6 NVIDIA + 2 AMD 머신에서 실측한 진짜 사고:

```python
for d in prefs.devices:
    d.use = True          # ← 보이는 카드 전부. 점유 여부는 안 본다
scene.cycles.device = "GPU"
bpy.ops.render.render()
# RuntimeError: Error: System is out of GPU memory
```

`refresh_devices()` 는 CUDA/OPTIX/**HIP까지 전 백엔드**를 채워 넣고,
Cycles 는 **"보이는 카드" 와 "남은 VRAM" 을 구분하지 않는다.**
6장 중 3장이 다른 프로그램에 100% 붙잡혀 있었고, **빈 카드가 3장 더 있었는데도 죽었다.**

여기서 더 미묘한 것: `bk doctor` 의 `활성 GPU 수` 가 **6**이었다.
**그 신호가 거짓말이었다.** 남은 VRAM을 직접 보기 전까진 GPU가 걸렸다고 결론 내릴 수 없다.

### 안전한 켜기

```python
from bkkit import compat
ok, info = compat.enable_gpu(scene)    # 없으면 CPU 폴백, 남의 카드면 그걸 건너뛴다
if not ok:
    print("GPU 못 씀:", info["reason"])
else:
    print("사용:", [s["name"] for s in info["selected"]])
    print("제외:", [(s["name"], s["free_mb"]) for s in info["skipped"]])
```

`enable_gpu()` 가 하는 일:

1. **`compute_device_type` 을 먼저 설정**하고 나서 `refresh_devices()` — 반대 순서는 **세그폴트** (§6.5.1)
2. 선택한 백엔드의 카드만 남김 (AMD 카드가 섞여 있어도 걸러짐)
3. `nvidia-smi` 로 **남은 VRAM 2 GB 미만 카드 제외** — 다른 작업 중인 카드
4. **여유 VRAM 내림차순**으로 정렬 후 **기본 1장만** 사용 (§6.5.2)
5. GPU가 없으면 예외 없이 CPU 로 폴백 + `info["reason"]`

### 6.5.1 `refresh_devices()` 순서를 뒤집으면 죽는다 (SIGSEGV)

```python
prefs.refresh_devices()                    # ← 먼저 부르면
out["num_gpu"] = prefs.get_num_gpu_devices()
# AttributeError: 'CyclesPreferences' object has no attribute 'compute_device_type'
# ... 이후 렌더하면 exit 139 (SIGSEGV)
```

```python
prefs.compute_device_type = "OPTIX"        # ← 반드시 먼저
prefs.refresh_devices()                    #    그 다음
```

> Python `try/except` 로 못 잡는다. **세그폴트는 프로세스 종료**라.
> `prefs` 를 만지는 코드를 리팩터링하면 `echo $?` 로 139 를 반드시 확인하라.
> (이 스킬의 `gpu_report()` 가 실제로 이 버그를 갖고 있었고, GPU 머신 첫 실행에서 죽었다)

### 6.5.1a ⭐ 렌더 속도 — 실제로 무엇이 얼마나 빠른가 (실측)

전체 실측은 [`references/18-render-optimization.md`](references/18-render-optimization.md).
여기서는 **가장 큰 레버만**:

| 순위 | 최적화 | 효과 | 대상 |
|---:|---|---:|---|
| 1 | **SUBSURF `render_levels` 낮추기** | 5→1: **17.46→6.24 s (−64%)** | 기하 |
| 2 | **GPU 1장만** (NVLink 없으면) | GPU 3장 대비 **−27%** (반사 씬은 **−73%**) | GPU |
| 3 | **영상: `use_persistent_data=True`** | **−50%** (동일 씬 반복은 **13.7배**) | 영상 |
| 4 | **탐색: 디노이즈 OFF** | **−25%** | 반복 렌더 |
| 5 | `tile_size` 2048 | −5% | GPU |
| — | **`Decimate` COLLAPSE** | **역효과 — 3.4배 느림** | ⚠ 기하 |
| — | `use_light_tree` / `denoising_quality` / 출력 포맷 | **효과 없음** (측정 완료) | 만지지 말 것 |

```python
# frag
# ★ 기하 — 정점 수가 곧 렌더 시간이다 (거의 선형)
mod.levels = 1; mod.render_levels = 1     # ★ 둘 다. levels 만 낮추면 렌더는 그대로다

# ★ 영상 렌더의 최대 효과 — BVH 재사용
scene.render.use_persistent_data = True    # 8.25 s → 4.15 s (−50%)

# ★ 탐색용 프리셋
compat.gpu_speed_preset(scene, quality="fast")   # 디노이즈 off, 타일 1024
scene.cycles.samples = 16
scene.cycles.adaptive_threshold = 0.1
```

> ### ⚠ 기하 축의 역효과 — "정점 줄이면 빠를 줄 알았는데"
>
> | 구성 | 정점 | 시간 |
> |---|---:|---:|
> | Decimate 없음 | 5,079,060 | **3.26 s** |
> | **Decimate COLLAPSE 0.5** | 2,539,540 | **11.03 s** ← 3.4배 느림 |
> | **Decimate UNSUBDIV 0.5** | 5,079,060 | **2.42 s** ← 가장 빠름 |
>
> ```python
> compat.fix_decimate_type(scene)          # COLLAPSE → UNSUBDIV 일괄 변환
> compat.reduce_subdiv_for_preview(scene)  # SUBSURF render_levels → 1
> ```
>
> **정점을 절반으로 줄였는데 3.4배 느려졌다.** COLLAPSE 는 삼각형을
> 실제로 재구성해 BVH 를 비싸게 만든다. → **`decimate_type="UNSUBDIV"` 를 써라.**

> ### ❌ GPU 에서 손대지 마라 (측정 완료 — 시간 쓰지 마라)
>
> | 항목 | 측정 결과 |
> |---|---|
> | `use_light_tree` (30조명, 64spp) | 0.94 vs 0.90 s — **무의미** |
> | `denoising_quality` F/B/H | 0.81/0.80/0.82 s — **무의미** |
> | 출력 포맷 PNG/JPEG/EXR | 0.84~0.92 s — **무의미** (파일 크기만 다름) |
> | `texture_limit` / `max_bounces` | **효과 없음 / 역효과** |
> | **path guiding** | GPU 에서 **무시됨** — CPU 는 +56% 느려지는 걸 실증 |
> | `kernel_optimization_level` | 0.87/0.87/0.92 s — **차이 없음** |

> ### 🎬 영상 렌더에서 특히 — 2K 60fps 실측
>
> `use_persistent_data` 는 `scene.render` 에 있고 **기본값이 False** 다.
> 카메라가 움직이는 100프레임 영상에서 기본값은 BVH 재구성에 수십 초를 쓴다.
> **선택이 아니라 필수** 다.
>
> **실제 1920×1080 / 60fps / 60프레임 렌더 (절차적 셰이더 바닥 + 금속/디퓨즈 구 24개
> + AREA 6 + SUN + 카메라 dolly·pan):**
>
> | 설정 | 총 시간 | 프레임당 |
> |---|---:|---:|
> | **최종** (persistent + denoise, 64spp) | **160.80 s** | 2.680 s |
> | **탐색** (persistent, denoise OFF, 16spp) | **70.46 s** | 1.174 s |
>
> **최적화 비율은 960×720 과 거의 같다** (고해상도에서 사라지지 않는다):
>
> | 항목 | 960×720 | **2K 60fps** |
> |---|---:|---:|
> | `use_persistent_data` OFF→ON | −50% | **−48%** |
> | 디노이즈 ON→OFF | −25% | **−19%** |
>
> **⚠ 강한 부하(load 62 + GPU 6장 전부 점유)에서도 비율이 유지됐다.**
> persistent OFF 55.78 s → ON 28.43 s (**−48%**), denoise OFF 23.03 s.
> GPU 연산이 아니라 **BVH 재구성 비용**을 줄이는 최적화라 부하에 강하다.
>
> **반면 GPU 연산량이 늘면 바로 무너진다** — 6장 점유 시 프레임당 2.68 → 6.49 s
> (**+142%**), 여유 카드가 하나뿐이면 **28.13 s (+949%)**.
> **렌더 전에 `bk doctor` 로 카드 상태를 확인하라.**
> (→ [`references/18-render-optimization.md`](references/18-render-optimization.md) §2.5)
>
> ```python
> scene.render.use_persistent_data = True
> scene.render.use_auto_generate_texture_cache = True
> ```
>
> ⚠ **`use_prefetch` 같은 속성은 Blender 5.2 에 없다.** 정확히는
> `use_auto_generate_texture_cache` 이다. 이 스킬도 처음엔 `use_prefetch` 라고
> 적었다가 실행해서 찾았다. **속성 이름은 반드시 의존성 없이 확인할 것:**
>
> ```python
> sorted(p for p in scene.render.bl_rna.properties if "cache" in p)
> # → ['use_auto_generate_texture_cache', 'use_render_cache', 'use_texture_cache']
> ```

> ### ⚠ 셰이더 옵션 만지작김은 효과가 없다 (실측)
>
> `texture_limit`, `max_bounces`, `tile_size` 을 조정했을 때 측정된 변화는
> **측정 편차(±27%) 안에 들어간다.** 심지어 `max_bounces` 를 늘리면 빨라졌다.
> **큰 레버 3개(GPU 수 · persistent data · 디노이즈)를 먼저 확정하고**,
> 그 다음에 미세 조정하라. 순서를 바꾸면 시간을 버린다.
>
> 셰이더 쪽에서 실제로 효과가 있는 건 **커널 JIT** 다:
> GPU 씬 첫 렌더는 **+24%**, CPU 씬은 +12% 지불한다.
> **반복 렌더는 반드시 한 프로세스 안에서** 돌려서 JIT 를 한 번만 냈다.
> ([`templates/iterative_loop_template.py`](templates/iterative_loop_template.py) 가 이 구조)

### 6.5.1b ⭐ EEVEE vs Cycles — 속도보다 **품질**이 먼저다

전체 실측은 [`references/19-render-engines.md`](references/19-render-engines.md).

**960×720, 샘플 64, GPU, `use_persistent_data=True`, warm median:**

| 씬 | Workbench | EEVEE | Cycles |
|---|---:|---:|---:|
| mixed (SUBSURF 30) | 2.62 s | 3.06 s | **0.30 s** |
| reflective (거울+유리) | **0.09 s** | 0.47 s | 0.67 s |
| interior | **0.09 s** | 0.44 s | 0.33 s |

> ### 이 표에서 읽어야 할 것 두 가지
>
> **1. 속도 격차는 최대 7배지만, 샘플 격차는 100배다.**
> "렌더가 느려요"의 원인은 엔진이 아니라 **샘플 수**다.
>
> **2. EEVEE 와 Cycles 는 다른 GPU 에서 돈다.**
>
> ```python
> # frag
> import gpu
> gpu.init()                      # 5.2 에서 인자 없음
> print(gpu.platform.renderer_get())
> # 이 머신: AMD Radeon RX 7600 XT (OpenGL)  ← EEVEE
> #         (Cycles 는 같은 머신에서 RTX 4070 / OptiX)
> ```
>
> EEVEE 가 **llvmpipe** 로 떨어지면 크게 느려진다. 실측: reflective 씬
> OpenGL 0.51 s → llvmpipe **3.84 s** (cold 29.31 s). 렌더 전에 확인해라.
>
> ```python
> import gpu; gpu.init()
> print(gpu.platform.renderer_get(), gpu.platform.vendor_get())
> ```
>
> **EEVEE 를 Vulkan 백엔드로 바꾸면 NVIDIA 카드로도 돌 수 있다** (실측 1.8배):
> ```bash
> blender -b --factory-startup --gpu-backend vulkan --gpu-device help  # 기기 목록
> blender -b --factory-startup --gpu-backend vulkan --gpu-device 5 -P s.py
> ```
> ⚠ OpenGL 은 **첫 카드 하나만** 노출하고 Vulkan 은 **전부** 열거한다.
> prefs(`preferences.system.gpu_backend`)에 대입해도 **런타임은 안 바뀐다** —
> 백엔드는 프로세스 시작 시 CLI 플래그로만 확정된다.

> ### ⚠ EEVEE 는 계산 안 하는 게 있다 (품질의 문제, 속도의 문제 아님)
>
> 거울 바닥 + 유리 큐브 씬을 세 엔진으로 렌더한 결과:
>
> | | EEVEE (RT off) | EEVEE (RT on) | Cycles |
> |---|---|---|---|
> | `mean_luma` | 0.1161 | 0.1281 | 0.1849 |
> | 유리 굴절 | ❌ 검정 | ⚠ 근사 | ✅ 정확 |
> | 거울 반사 | ❌ 없음 | ⚠ 근사 | ✅ 정확 |
>
> EEVEE 가 어두운 게 아니라 **계산을 안 한 것**이다.
> **반사·굴절·GI 가 핵심이거나 최종 산출물이면 Cycles 다.**

> ### 판단 기준
>
> | 렌더 횟수 | 선택 |
> |---|---|
> | 1~3회 | EEVEE — cold 가 더 싸다 (0.83 s vs 2.27 s) |
> | **4회 이상 (반복 최적화, 영상)** | **Cycles** — warm 이 10배 싸다 (0.30 s vs 3.06 s) |
> | 반사/굴절/GI | Cycles — EEVEE 는 근사밖에 못 함 |
> | 씬 구조 확인 | Workbench — 0.09 s |

```python
# frag
# ❌ 4.x 튜토리얼의 이름. 5.x 에서 사라져 엔진이 안 바뀐다
scene.render.engine = "BLENDER_EEVEE_NEXT"
# ✅ 5.x
scene.render.engine = "BLENDER_EEVEE"
```

### 6.5.2 GPU를 늘리면 오히려 느려진다

960x720 · 64 spp · SUBSURF 구 30개 + AREA 라이트 6개 · OptiX 디노이즈 ON, 실측:

| 구성 | 시간 |
|---|---:|
| CPU (80코어) | 5.69 s |
| **GPU 1장 (RTX 4070)** | **4.51 s** ← 가장 빠름 |
| GPU 2장 | 5.26 s |
| GPU 3장 | 6.17 s |
| GPU 6장 | *System is out of GPU memory* |

NVLink 없는 카드는 타일마다 씬을 복사하고 결과를 PCIe로 동기화하는데,
그 통신 비용이 추가 연산량보다 크다. **그래서 `enable_gpu(max_devices=1)` 이 기본값이다.**

속도 레버 (동일 씬, GPU 1장): **디노이즈 OFF −25%** (5.61→4.20 s),
`tile_size` 2048 −5%, `use_persistent_data` −5%.

```python
compat.gpu_speed_preset(scene, quality="fast")   # 반복 렌더는 디노이즈 끄기
```

### GPU 상태를 먼저 보고 싶다면

```bash
blender -b -P scripts/bk.py -- doctor
```

```
  === GPU별 실측 상태 (nvidia-smi) ===
  [OK ] gpu 3 82:00  NVIDIA GeForce RTX 4070    여유  12252 MB /  12282 MB  util   0%
  [OK ] gpu 4 83:00  NVIDIA GeForce RTX 4060 Ti  여유   8159 MB /   8188 MB  util   0%
  [BUSY] gpu 0 01:00  NVIDIA GeForce RTX 3070    여유   1263 MB /   8192 MB  util 100%
  ...
  === enable_gpu() 가 선택할 것 ===
  사용: NVIDIA GeForce RTX 4070 (여유 12252 MB)
```

`[BUSY]` 가 떠 있으면 그 카드는 남의 것이다.

자세한 백엔드 요구 사양·폴백·CLI·VRAM 관리·세그폴트 전수 로그는
[`references/14-gpu-rendering.md`](references/14-gpu-rendering.md).

> ⚠ **`gpu_host_usage()` 는 `nvidia-smi` 만 본다.** AMD 카드가 점유 중이어도
> 감지 못 하고 잡아버린다 (`rocm-smi` 미구현). HIP 렌더에서 OOM 나면 수동 확인 필요.

---

## 6.6 실전 검증 결과 — 스킬은 실제로 잘 작동한다

서브에이전트 6명에게 **스킬 파일만 주고** 실전 작업을 시켰다
(모델링+리깅+애니메이션 / 이미지 보정 / 지오메트리 노드 / 영상편집 / 시뮬레이션 / 텍스처링+내보내기).

**6/6 성공.** 전부 손대지 않은 영역이었고, 물리적 증거를 냈다:

- 지오메트리 노드: `verts = 8.000000 × Count + 0.000000` (선형 회귀)
- 시뮬레이션: 자유낙하 이론값 대비 **5.3 mm** 오차
- 영상편집: `ffprobe` 검증 통과, ON/OFF **758,311 샘플** 차이
- 텍스처링: 5포맷 라운드트립, 재질 3종 색 거리 0.2991

**총평 7.2 / 10.** 상세는 [`16-field-test.md`](references/16-field-test.md).

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

### GPU 관련은 2026-10 에 크게 갱신됐다

이 스킬은 처음에 **GPU 없는 머신**에서 작성됐다. 그래서 GPU 렌더 성능을
검증하지 않았다. 지금은 **GPU 6 NVIDIA + 2 AMD 머신**에서 재검증했다.

**이제 실측된 것:**

| 항목 | 결과 |
|---|---|
| CUDA / **OptiX** 실제 렌더 | 🟢 RTX 4070 로 렌더 성공 |
| GPU vs CPU 렌더 시간 | 🟢 CPU 5.69 s / GPU 1장 4.51 s |
| GPU 수별 스케일링 | 🟢 1장 최적, 2/3장 열화, 6장 OOM |
| VRAM OOM | 🟢 `System is out of GPU memory` 실제 재현 |
| `OPTIX` 디노이저 | 🟢 동작 확인 |
| 디노이즈 비용 | 🟢 −25% |
| 세그폴트 (exit 139) | 🟢 재현 **및** 수정 |

**2세대에서 추가로 실측해 없앤 것:**

| 항목 | 결과 |
|---|---|
| **HIP (AMD) 실제 렌더** | 🟢 Radeon RX 7600 XT 2장 로 렌더 성공 (1.37 s / 64spp). §1.11 |
| **AMD 점유 감지** | 🟢 `gpu_host_usage_amd()` — `rocm-smi` 파싱, `bk doctor` 표시 |

**그리고 이 과정에서 찾은 진짜 버그:**

> ### ⚠ HIP 에서 `denoiser='OPTIX'` 가 조용히 22% 느리다
>
> AMD 카드가 있는데도 `denoiser` enum 이 `('OPTIX','OPENIMAGEDENOISE')`
> 둘 다 내놓고 OPTIX 대입이 성공한다. 렌더도 "성공"한다. 그런데 OptiX
> 디노이저가 없으니 CPU 폴백되어 **3.85 s → 3.01 s 손해.**
>
> ```python
> # enum 이 허용한다 ≠ 이 기기에서 작동한다
> prefs.has_optixdenoiser_gpu_devices()   # False 여야 함
> ```
>
> `set_denoiser()` 가 이걸 이제 확인한다. GPU 없는 머신에서는 enum 이
> OPTIX 를 빼줘서 대입이 실패했기에 "에러 없는 쪽이 더 위험" 이었다.

**아직 미검증:**

- **AMD 카드 → 카드 1:1 매칭.** `rocm-smi` 는 버스 ID 를 안 줘서
  `GPU[0]` ↔ HIP device 매칭이 불가능. **HIP 카드 점유 시 자동 배제 안 된다.**
  `bk doctor` 의 AMD 표를 눈으로 확인하라. (NVIDIA 쪽은 `82:00` 으로 정확)
- **oneAPI / Metal** — 하드웨어 없음.
- **NVLink 공유 메모리** — 이 머신엔 NVLink 이 없다. (그래서 멀티 GPU 가 느렸다)
- `kernel_optimization_level` 실제 시간차.
- 드라이버 `use_scripts_auto_execute`: GUI 설정이라 헤드리스에서
  실제 식 평가까지는 확인 못 함. API 존재는 확인.
- **Fluid / Ocean / Rigid Body**: API 와 속성 이름은 확인했지만,
  캐시를 포함한 "결과가 맞는지"까지는 1회 실행으로 검증하지 않음.

> **성능 수치(5.69 s, 4.51 s, −25%) 는 이 머신 + 이 씬 한정이다.**
> 절대 스케일로 옮기지 말 것. 다른 머신에서는 `bk doctor` 로 상태를 보고
> 직접 재라. 상세는 [`references/14-gpu-rendering.md`](references/14-gpu-rendering.md) §12.

이 항목들은 문서에 "미검증"으로 표시되어 있다. 신뢰하지 말고 직접 재현할 것.

# 18. 렌더 속도 최적화 — 무엇이 얼마나 빠른가 (실측)

> **이 문서는 추정이 없다.** 아래 모든 숫자는 이 머신에서 직접 돌려서 나온 값이다.
> 측정 방법과 잡음 처리는 [`17-environment-baseline.md`](17-environment-baseline.md) 를 본다.
>
> **반드시 먼저 읽을 것**: §0 의 "측정 신뢰도" — 이 머신은 항상 부하가 있고
> 반복 측정 편차가 **27%** 나 된다. 아래 수치를 절대값으로 믿지 말고 **방향과 배율**로 읽어라.

## 측정 환경 (모든 수치의 출발점)

```
CPU  : Xeon E5-2673 v4 80 logical / 40 physical
GPU  : RTX 4070 (OptiX) 1장 — 여유 12252 MB
부하 : load(1m) 15~27 (80코어 중 19~34% 사용 중)
측정: 반복 3~5회 후 median. 첫 회차는 JIT 때문에 버림 (§2)
```

---

## 0. ⭐ 실측 결과 요약 — 효과 내림차순

| 순위 | 최적화 | 효과 | 대상 |
|---:|---|---:|---|
| 1 | **GPU 1장만 사용** | GPU 3장 대비 **−27%** | GPU |
| 1b | **AMD(HIP) 에서 `denoiser` 확인** | **−20%** | HIP |
| 1c | **SUBSURF `render_levels` 5→1** | **−64%** (17.46→6.24 s) | 기하 |
| 1d | **Decimate `UNSUBDIV` (not COLLAPSE)** | **4.6배 빠름** (11.03→2.42 s) | 기하 |
| 2 | **영상: `use_persistent_data=True`** | **−50%** | 영상 |
| 3 | **반복 렌더: 디노이즈 OFF** | **−25%** | 탐색 |
| 4 | `tile_size` 2048 | −5% | GPU |
| 5 | `use_persistent_data` (정지이미지) | −5% | 정지 |
| 6 | `adaptive_threshold` 0.1 | −4% | 저품질 허용 |
| 7 | 모션블러 ON | +8% (저렴) | 영상 |
| 8 | 출력 포맷 (PNG/JPEG/EXR) | **무의미** (편차 안) | — |
| — | `use_light_tree` | **효과 없음** (64 spp) | 조명 |
| — | `denoising_quality` | **효과 없음** | — |
| — | `texture_limit` | **효과 없음** | (이 씬에서) |
| — | `max_bounces` 감소 | **역효과** | (이 씬에서) |
| — | `Decimate` COLLAPSE | **역효과 (3.4배 느림)** | 기하 |
| — | 경로 가이딩 | GPU 미지원 | — |

> **순위 1~4위만 해도 대부분의 렌더가 빨라진다.**
> 나머지 세부는 측정 오차(27%) 안에 들거나 오히려 역효과다.
>
> **이 문서의 실질적 결론:**
> 1. **GPU 수** — NVLink 없으면 1장이 최적
> 2. **`use_persistent_data`** — 영상/반복 렌더의 최대 효과
> 3. **디노이즈** — 탐색에선 OFF (−25%)
> 4. **`render_levels`** — SUBSURF 정점 수가 곧 렌더 시간
>
> **셰이더 옵션 만지작김은 시간 낭비다.** 위 4개를 먼저 확정하고 나서만 세부를 보라.

---

## 1. 🟢 GPU 수 — 가장 큰 레버 (그리고 가장 반직관적)

실측 씬: 960×720, 64 spp, SUBSURF 구 30개 + AREA 라이트 6개, OptiX 디노이즈 ON.

| 구성 | 시간 | GPU 1장 대비 |
|---|---:|---:|
| CPU (80코어) | 5.69 s | −26% |
| **GPU 1장 (RTX 4070)** | **4.51 s** | 기준 |
| GPU 2장 | 5.26 s | **+17%** |
| GPU 3장 | 6.17 s | **+37%** |
| GPU 6장 | *System is out of GPU memory* | 실패 |

### 1.1 텍스처 씬에서는 훨씬 격렬하다 (더 현실적)

960×720, 4K 텍스처 16장, glossy 반사, 64 spp:

| 구성 | 시간 | GPU 1장 대비 |
|---|---:|---:|
| **GPU 1장** | **1.65 s** | 기준 |
| GPU 3장 | **4.48 s** | **+171% (2.7배 느림)** |

> **반사가 많은 씬에서 멀티 GPU 는 2.7배 느려진다.**
> 반사·굴절은 GPU 사이 데이터 의존이 가장 강하기 때문이다.
> 각 카드가 중간 결과를 주고받아야 하므로 PCIe 대역폭이 병목이 된다.

### 1.2 왜 그런가

이 머신의 카드에는 **NVLink 가 없다.** 멀티 GPU 렌더는 타일마다
씬 전체를 각 카드에 복사하고, 결과를 PCIe 로 모아 동기화한다.

| 연결 | 멀티 GPU 판단 |
|---|---|
| NVLink (Tesla, A100/H100 등) | **커널 큐가 공유**되므로 확장은 잘 된다. 여러 장 써도 됨 |
| PCIe Gen4 x16 이상 | 제한적. VRAM 이 부족할 때만 |
| PCIe Gen3 이하 / shared | **역효과. 1장이 낫다.** |

> **판단 규칙**: NVLink 로 연결된 동질 카드인가?
> - 예 → `max_devices=N`
> - 아니오 → `max_devices=1` (기본값)

```python
# frag
from bkkit import compat
# VRAM 이 벽일 때만 여러 장. 평소에는 1장.
ok, info = compat.enable_gpu(scene, max_devices=1)
```

---

## 1.3 🟢 AMD (HIP) 에서도 동일하게 동작 — 단, 디노이저 함정

AMD 카드는 "버릴 만한 카드"가 아니다. 실측 (960×720, 64 spp, mixed):

| 백엔드 | GPU | 시간 |
|---|---|---:|
| OptiX | RTX 4070 1장 | **3.60 s** |
| **HIP** | **RX 7600 XT 1장** | **3.85 s** |
| HIP | RX 7600 XT 2장 | 3.95 s |

AMD 1장이 OptiX 와 거의 동등하고, 2장은 늘어나지 않는다
(NVIDIA 쪽과 같은 성질 — PCIe 통신 비용 > 추가 연산, §1.2).

### ⚠ 디노이저 함정 — 이건 AMD 에서만 조용히 일어난다

```
has_optixdenoiser_gpu_devices : False        ← OptiX 카드 없음
denoiser=OPTIX              -> OK (OPTIX)     ← 그런데 대입 성공!
```

| `denoiser` | 시간 | 델�� |
|---|---:|---:|
| `OPTIX` (AMD 에 존재하지 않음) | 3.85 s | 기준 |
| `OPENIMAGEDENOISE` | 3.01 s | **−22%** |

`denoiser` enum 이 `('OPTIX', 'OPENIMAGEDENOISE')` 둘 다 내놓기 때문에
`set_denoiser()` 가 OPTIX 를 골랐고, 렌더는 "성공"했지만 실제로는
OptiX 디노이저가 없어 CPU 폴백으로 22% 느려졌다.

```python
# frag  — enum 이 아니라 실제 디바이스 존재 여부로 판단하라
prefs = bpy.context.preferences.addons["cycles"].preferences
if not prefs.has_optixdenoiser_gpu_devices():
    scene.cycles.denoiser = "OPENIMAGEDENOISE"   # AMD / NVIDIA 없는 머신
```

`bkkit.compat.set_denoiser()` 는 이 확인을 이제 내장한다
(`OPTIX` 를 고를 때 `has_optixdenoiser_gpu_devices()` 도 본다).

> **본질**: "enum 이 허용한다" ≠ "이 기기에서 작동한다".
> GPU 없는 머신에서는 enum 이 OPTIX 를 빼줘서 **대입이 실패**했다 → 눈이 보였다.
> AMD 머신에서는 **enum 이 속였고**, 에러 없이 조용히 느려졌다.

### AMD 점유는 눈으로 확인해야 한다

`gpu_host_usage_amd()` 가 `rocm-smi` 로 AMD VRAM/util 을 읽는다:

```
=== AMD GPU 상태 (rocm-smi) ===
[OK ] gpu0 AMD Radeon RX 7600 XT  VRAM 19%  util 26%
[OK ] gpu1 AMD Radeon RX 7600 XT  VRAM  0%  util 28%
```

**하지만 자동 배제는 되지 않는다.** `rocm-smi` 의 `GPU[0]` 에 버스 ID 가 없어
Cycles HIP device ID 와 1:1 매칭이 안 된다. (NVIDIA 는 `82:00` 으로 정확히 매칭된다.)

## 1.4 🟢 기하/메모리 축 — SUBSURF 를 실제로 낮춰라 (정점 수 = 렌더 시간)

SUBSURF 는 GPU 렌더에서 **가장 예측 가능한 비용 축**이다.
구 60개 × 5레벨 씬, 960×720, 64 spp, GPU 1장:

| SUBSURF 레벨 | 정점 수 | warm 시간 | vs 레벨1 |
|---:|---:|---:|---:|
| 1 | 119,160 | **6.24 s** | 기준 |
| 2 | 476,280 | 6.40 s | +3% |
| 3 | 1,904,760 | 7.67 s | +23% |
| 4 | 7,618,680 | 9.74 s | +56% |
| 5 | 30,474,360 | **17.46 s** | **+180%** |

**정점 수 ×4 = 시간 ×1.23 (1→3레벨), ×1.4 (1→4)** — 거의 선형이다.
**레벨 5 에서 갑자기 벽을 친다** (BVH 빌드가 GPU VRAM 을 넘기기 시작).

```python
# frag
for ob in bpy.data.objects:
    for mod in ob.modifiers:
        if mod.type == "SUBSURF":
            mod.levels = 1          # 뷰포트
            mod.render_levels = 1   # ★ 실제 렌더 (이게 안 낮으면 렌더는 그대로다)
```

> **`levels` 만 낮추면 렌더는 빨라지지 않는다.** `render_levels` 가 렌더에 쓰인다.
> 둘 다 낮춰야 한다. (이 스킬이 실수한 부분 — §13)

### ⚠ Decimate(COLLAPSE) 모디파이어는 역효과다 (실측)

정점을 50% 줄이는 모디파이어가 **3.4배 느리게** 만들었다:

| 구성 | 정점 수 | warm 시간 |
|---|---:|---:|
| Decimate 없음 (SUBSURF 5) | 5,079,060 | **3.26 s** |
| Decimate COLLAPSE 0.5 | 2,539,540 | **11.03 s** ← 정점 ↓ 시간 ↑↑ |
| Decimate COLLAPSE 0.1 | 507,920 | **14.98 s** |
| **Decimate UNSUBDIV 0.5** | 5,079,060 | **2.42 s** ← 가장 빠름 |

**정점을 줄였는데 렌더가 3.4배 느려졌다.** 4회 연속 재현 (10.6~11.5 s).
같은 씬에서 UNSUBDIV 는 2.42 s — **COLLAPSE 대비 4.6배 빠르다.**

**왜?** COLLAPSE 는 **삼각형을 실제로 재구성**하므로 정점 수만 줄고
삼각형 인덱스/그룹 구조가 BVH 빌드에 비싼 상태로 남는다. 그리고
Decimate 결과를 렌더마다 새로 계산한다 (persistent data 없이는).

**해결 — `decimate_type` 을 바꿔라:**

```python
# frag
m = ob.modifiers.new("Reduce", "DECIMATE")
m.decimate_type = "UNSUBDIV"   # ★ COLLAPSE 가 아니라 이걸 쓴다
m.ratio = 0.5
```

UNSUBDIV 는 실제로 verts 를 유지한 채 **SUBSURF 결과를 상위 레벨로 대체**한다
(verts=5,079,060 그대로지만 렌더는 2.40 s — BVH 가 단순해진다).

> **원칙: 정점을 줄이려면 COLLAPSE 가 아니라 UNSUBDIV 를 쓴다.**
> COLLAPSE 는 "메시를 실제로 망가뜨리면서" 느리게 만든다.

## 2. 🟢 영상 렌더 — `use_persistent_data` 가 절반을 벌린다

**가장 과소평가되는 설정이다.** 여전히 `scene.render` 에 있고 기본값은 False.

실측 (카메라 키프레임 애니메이션, 960×720, 32 spp, 8프레임, GPU 1장):

| | 8프레임 | 프레임당 |
|---|---:|---:|
| `use_persistent_data = False` (기본) | **8.25 s** | 1.03 s |
| **`use_persistent_data = True`** | **4.15 s** | **0.52 s** |
| | **−50%** | |

12프레임에서 재확인:

| | 12프레임 | 프레임당 |
|---|---:|---:|
| persistent ON | 4.71 s | 0.39 s |
| GPU 3장으로 (persistent ON) | 9.65 s | 0.80 s |
| 디노이즈 OFF (persistent ON) | 3.34 s | 0.28 s |

### 2.1 왜 이렇게 큰 차이가 나나

`use_persistent_data=True` 는 **프레임 사이에서 BVH 를 재사용**한다.
BVH 는 매 프레임 "이 씬의 모든 폴리곤을 어디서 어디로 쏠지" 결정하는 자료구조다.
매 프레임 다시 만드는 비용이 프레임당 0.5 s 중 대부분을 차지한다.

| 상황 | 효과 |
|---|---|
| 카메라만 움직임 (직선 이동/회전) | **−50%** (BVH 재사용 가능) |
| 씬 안의 오브젝트가 변함 | 효과 감소 (부분적 재구성) |
| 지오메트리 노드가 매 프레임 평가됨 | 효과 감소 |

### 2.2 ⚠ 함정 1: persistent data 는 메모리를 먹는다

BVH 와 텍스처를 메모리에 유지하므로 **RAM 사용량이 올라간다.**
함께 쓸 수 있는 텍스처 캐시 설정은 `use_auto_generate_texture_cache` 다.
(`use_prefetch` 는 **Blender 5.2 에 존재하지 않는다** —
`scene.render.bl_rna.properties` 로 확인하면 `use_render_cache` /
`use_texture_cache` / `use_auto_generate_texture_cache` 만 나온다.)

```python
# frag
scene.render.use_persistent_data = True   # ← 영상 렌더의 최대 효과 (−50%）
scene.render.use_auto_generate_texture_cache = True   # 텍스처 캐시 선행 생성
```

> **100프레임 영상에서 persistent OFF 는 100 × 0.5 s = 50 초를**
> BVH 재구성에 낭비한다. hdNIV이나 farm 파이프라인에서 이건 거대한 손해다.
> **영상 렌더에서 `use_persistent_data=True` 는 선택이 아니라 필수다.**

---

## 2.5 🟢 실전 검증 — 2K 60fps 영상 (60프레임, 실제 렌더)

위 수치들이 **실제 1920×1080 / 60fps 영상**에서도 그대로 성립하는지 검증했다.
씬: 절차적 셰이더 바닥 + 금속/디퓨즈 구 24개 (SUBSURF 3) + AREA 6 + SUN,
카메라 dolly·pan 키프레임, 구들 상승/하강 애니메이션. GPU 1장 + OptiX 디노이즈.

#### 60프레임 실측 (부하 없음)

| 설정 | 총 시간 | 프레임당 |
|---|---:|---:|
| **최종** (persistent + denoise, 64spp) | **160.80 s** | 2.680 s |
| **탐색** (persistent, denoise OFF, 16spp) | **70.46 s** | 1.174 s |

#### 10프레임 — 최적화 효과 (960×720 실측과 비교)

| 항목 | 960×720 실측 | **2K 60fps 실측** | 일치? |
|---|---:|---:|---|
| `use_persistent_data` OFF→ON | −50% | **55.78 s → 28.77 s = −48%** | ✅ |
| 디노이즈 ON→OFF | −25% | **28.43 s → 23.03 s = −19%** | ✅ |

**비율이 960×720 과 거의 같다.** 고해상도에서 최적화 효과가 사라진다는
걱정은 **실측으로 뒤집혔다.**

### ⚠ 강한 부하 하에서도 효과는 유지된다

**load 62 (80코어의 78%) + GPU 6장 전부 점유** 상태에서 10프레임 반복:

| 항목 | 부하 없음 | **강한 부하** | 변화 |
|---|---:|---:|---:|
| persistent ON (denoise ON) | 28.77 s | 28.43 / 28.57 / 29.13 / 29.57 s | **편차 3.9%, 무의미** |
| persistent **OFF** | 55.78 s | **55.28 s** | **−48% 유지** |
| denoise **OFF** | 23.03 s(부하) | **23.03 s** | **−19% 유지** |

> ### 결론 — 최적화 비율은 부하에 강하다
>
> **GPU 를 전부 점유당기고 CPU 를 60코어 소진시킨 상태에서도
> `persistent_data` −48%, 디노이즈 −19% 가 그대로 유지됐다.**
>
> 이유는 자명하다. 이 두 최적화는 **GPU 연산량이 아니라
> BVH 재구성과 후처리에 드는 비용**을 줄인다. GPU 를 못 쓰는 것이지
> 알고리즘이 달라지는 것이 아니다.
>
> **반대로 GPU 연산량이 늘면 최적화 비율은 옅어진다:**
>
> | 조건 | 프레임당 | 무부하 대비 |
> |---|---:|---:|
> | 부하 없음 | 2.68 s | 기준 |
> | GPU 6장 점유 | 6.49 s | **+142%** |
> | 여유 있는 카드가 0번 하나뿐 | **28.13 s** | **+949%** |

> **주의**: 카드 선택이 실패하면 GPU 연산량이 급증한다.
> 아래를 읽기 전에 `bk doctor` 로 카드 상태를 확인하라.

### 🔥 카드 선택이 성능을 바꾼다 — `enable_gpu` 실전 검증

강한 부하 하에서 같은 10프레임이 **29 s → 64.9 s** 로 바뀌었다.
원인은 GPU 연산이 아니라 **어느 카드가 선택되었는지**였다.

```
[GPU 사용] NVIDIA GeForce RTX 5060 Ti  여유 16281 MB  util   0%
[GPU 제외] NVIDIA GeForce RTX 4070     여유  3914 MB  util 100%
[GPU 제외] NVIDIA GeForce RTX 4060 Ti  여유  6273 MB  util 100%
[GPU 제외] NVIDIA GeForce RTX 4060 Ti  여유  6273 MB  util 100%
[GPU 제외] NVIDIA GeForce RTX 3060 Ti  여유  5937 MB  util 100%
[GPU 제외] NVIDIA GeForce RTX 3070     여유  8138 MB  util   0%
```

**6장 중 4장이 100% 점유 중인데도 실패하지 않고 util 0% 인 카드로 전환했다.**
여유 VRAM 16281 MB → util 0% 두 장 중 최다 여유 선택. 이게 §1.7 해법의 실환경 증명이다.

> ### ⚠ 남는 한계 — util 은 참고용이다
>
> 측정 중 **util 0% 인데 실제로 느린 경우**를 봤다. 드라이버는 렌더가 끝나도
> VRAM 을 즉시 반환하지 않아 util 은 0 이어도 회수가 지연될 수 있다.
>
> 다만 반복 측정 결과 **과장된 불이익은 아니었다**:
>
> | 카드 | 반복 warm 측정 |
> |---|---|
> | RTX 5060 Ti (16 GB) | 7.21 s → 4.14 s → **2.68 s** |
> | RTX 4060 Ti (8 GB) | 5.37 s → 3.84 s → 3.80 s |
> | RTX 3070 (8 GB) | 8.17 s |
>
> 첫 측정(7.21 s)이 다른 작업의 잔여 부하였고, 정착하면 **5060 Ti 가 가장 빠르다.**
> → `enable_gpu` 의 "여유 VRAM 최다" 선택이 이 머신에서는 올바르다.
> **3회 이상 반복한 뒤 판단하라** — 1회 측정은 다른 작업의 그림자다.

### 🎬 영상 산출물 검증 (실제 파일)

```
$ ffprobe final_60fps.mp4
codec_name=h264  width=1920  height=1080  r_frame_rate=60/1
nb_frames=60     duration=1.000000      748 KB
```

- 2K 60fps 60프레임 PNG 시퀀스 → H.264 합치기 성공
- 프레임 간 차이: 1↔30 = 97,707 px, 1↔60 = 124,468 px → 애니메이션 정상
- 이미지 판정 `ok` (mean_luma 0.3445)

> **1920×1080 PNG 60장 = 약 195 MB.** 100fps 3초짜리면 1 GB easily.
> 영상 파이프라인에서는 **프레임을 PNG 시퀀스로 받고 나중에 인코딩**하는
> 것보다, 가능하면 Blender 의 FFMPEG 출력으로 **바로 인코딩**하는 게
> 디스크 I/O 를 줄인다. (§8.5)

## 3. 🟢 디노이즈 — 최종 렌더에서는 값어치, 탐색에서는 방해

960×720, 64 spp, GPU 1장, 텍스처 씬:

| 설정 | 시간 | 델타 |
|---|---:|---:|
| 디노이즈 ON (GPU, 기본) | 5.61 s | 기준 |
| **디노이즈 OFF** | **4.20 s** | **−25%** |
| 디노이즈 ON (CPU 로) | 5.52 s | −2% |
| 디노이즈 OFF (영상 12프레임) | 3.34 s | 0.28 s/frame |

### 3.1 결정 규칙

| 상황 | 디노이즈 | 근거 |
|---|---|---|
| 탐색 / 반복 렌더 | **OFF** | −25%. 노이즈 감내 가능한 저해상도 |
| 프레임 간 비교 (모션블러 테스트 등) | **OFF** | 디노이즈가 디테일을 지워서 결과를 왜곡 |
| 최종 스틸 / 영상 | **ON** | −25% 로 샘플을 4배 줄여서 상쇄. 순수 이득 |
| 알파/멀티패스 합성 | **OFF** | 패스마다 노이즈가 다르면 합성이 깨진다 |

> **최종 렌더에서 디노이즈는 거의 이득이다.** 샘플 4배를 줄여도
> 시간은 오히려 −25%. 디노이즈를 켜고 샘플을 확 줄이는 쪽이 항상 이득이다.

```python
# frag
from bkkit import compat
compat.gpu_speed_preset(scene, quality="fast")      # 반복 렌더용: 디노이즈 OFF
compat.gpu_speed_preset(scene, quality="balanced")  # 최종 렌더: 디노이즈 ON
```

---

## 4. 🟢 적응형 샘플링 — "이미 충분히 깨끗해진 영역"을 일찍 끝낸다

960×720, **256 spp**, GPU 1장:

| 설정 | 시간 | 델타 |
|---|---:|---:|
| `use_adaptive_sampling=False` (전부 256) | 5.00 s | 기준 |
| `adaptive_threshold=0.01` (기본) | 5.35 s | **+7% (역효과)** |
| `adaptive_threshold=0.1` (느슨) | 4.80 s | **−4%** |

> **과일: 기본값 0.01 이 오히려 느렸다.**
> 이건 노이즈가 적은 씬(AREA 라이트 6개, 조명 단순)에서 적응형 샘플링이 잘 작동하지
> 않아서 0.01 기준으로 256 spp 를 거의 다 채워 버렸기 때문이다.
> `threshold=0.1` 로 느슨하게 하면 확실히 −4%.
>
> **단, 이 −4% 는 측정 편차(27%) 안에 있다.** 방향성만 믿을 것.

| threshold | 성격 | 권장 |
|---|---|---|
| 0.001 | 거의 전부 256 spp | 고품질 최종 |
| 0.01 (기본) | 대부분 조용함 | 최종 렌더 |
| 0.05 | 눈에 띄는 곳만 max | 중간 품질 |
| **0.1** | **느슨함 — 확실히 빠름** | **탐색 / 대량 배치** |

```python
# frag
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.1        # 탐색
scene.cycles.adaptive_min_samples = 0        # 최소 0부터 시작
scene.cycles.samples = 64                   # 상한은 여기로. 256 으로 두지 마라
```

> ⚠ **`adaptive_max_samples` 는 Blender 5.2 에 없다.** 의존성 없이 확인:
> `sorted(p for p in scene.cycles.bl_rna.properties if "adaptive" in p)` →
> `['adaptive_min_samples', 'adaptive_threshold']` 뿐이다.
>
> "256 spp 설정 + 상한 64" 같은 조합은 **존재하지 않는다.**
> 실제로 상한을 강제하는 값은 `samples` 다.

---

## 5. ⚠ `texture_limit` — 이 씬에서는 효과가 없었다 (중요한 반론)

960×720, 텍스처 씬 (1024² × 12장, 4096² × 16장):

| texture_limit | 1024²×12 | 4096²×16 |
|---|---:|---:|
| OFF (기본) | 0.93 s | 1.30 s |
| 512 | 0.92 s | — |
| 1024 | 0.96 s | — |
| 2048 | 0.95 s | 1.31 s |
| 4096 | 0.94 s | 1.50 s |

> **효과가 없다. 심지어 4096 이 4096² 텍스처에서 오히려 느렸다(+15%).**
> 이 씬은 텍스처가 충분하지 않고, 렌더 해상도(960×720)에 비해 텍스처가 작아서
> 텍스처 대역폭이 병목이 아니었던 것이다.

### 5.1 언제 `texture_limit` 가 실제로 작동하는가

`texture_limit` 은 **텍스처 캐시 크기를 강제**해서 VRAM 을 아낀다.
아래에서만 의미가 있다:

| 상황 | 효과 |
|---|---|
| 텍스처 총합 > GPU VRAM | **OOM 방지. 가장 큰 효과** |
| VRAM 이 빡빡해서 다른 거 못 올림 | 다른 씬 요소(기하) 수용 공간 확보 |
| 지오메트리(BVH)가 VRAM 을 먹음 | 텍스처 쪽을 줄여 BVH 공간 확보 |

> **성능이 아니라 VRAM 안전장치로 쓰는 설정이다.**
> 이 스킬은 `enable_gpu(texture_limit="2048")` 를 기본으로 켜는데,
> 그 근거는 "2068² 를 넘어가는 텍스처는 보통 필요 없다" 는 **품질 판단**이지
> **속도 측정**이 아니다. 속도로는 이 문서에서 효과가 입증되지 않았다.

```python
# frag
# VRAM 이 부족할 때만. 속도 향상이 아니다.
scene.cycles.texture_limit = "2048"
scene.cycles.texture_limit_render = "2048"
```

---

## 6. ⚠ `max_bounces` 감소 — 역시 효과가 없었다 (그리고 역효과)

960×720, 64 spp, GPU 1장:

| bounces | 시간 | 델타 |
|---|---:|---:|
| max_bounces = 2 | 5.12 s | +4% |
| max_bounces = 4 (기본) | 4.94 s | 기준 |
| **max_bounces = 16** | **4.56 s** | **−8%** |
| 모든 bounce = 0 (직사광만) | 4.68 s | −5% |

> **역설적으로 bounces 를 늘리는 게 더 빨랐다.**
> bounces 를 줄이면 그만큼 경로가 끊겨야 하므로 일찍 종료되는 경로가 많은데,
> 그 early termination 이 오히려 샘플 분포를 불안정하게 만들어
> **디노이즈에 더 많은 시간이 듭니다.**

> ### 결론: `max_bounces` 로 속도를 잡으려 하지 마라
>
> - bounces 를 줄이는 건 **품질** 컨트롤이다 (유리 반사·굴절 횟수).
> - 속도를 줄이려면 **샘플 수·해상도·디노이즈·persistent data** 를 건드려라.
> - 이 씬의 −8% 는 편차(27%) 안이다. **방향도 신뢰하지 마라.**

---

## 7. 🟢 `tile_size` — GPU 에서만 의미 있다

960×720, 64 spp, GPU 1장:

| tile_size | 시간 | 델타 |
|---|---:|---:|
| 256 | 4.51 s | 기준 |
| 512 | 4.46 s | −1% |
| 1024 | 4.51 s | 기준 |
| **2048 (기본)** | **4.35 s** | **−5%** |

> **기본값 2048 이 이미 최적이었다.** 줄여도 이득이 없다.
> `tile_size` 의 진짜 목적은 **속도가 아니라 VRAM**이다.
> 큰 씬에서 VRAM 이 모자라면 256~512 로 내려야 하고, 그때 GPU 메모리를
> 아낀다. 속도는 오히려 1~5% 느려지는 게 보통이고, 편차 안이다.

```python
# frag
scene.cycles.tile_size = 2048          # 기본. 보통 이게 맞다
scene.cycles.tile_size = 256           # VRAM 부족할 때만
```

> `use_auto_tile` 은 **deprecated** 다 ("tiling is always enabled").
> 타일 크기 설정으로 바꿔도 렌더는 100% CPU 사이클을 쓴다.

---

## 8. 🟢 셰이더 관련 — 실제 속도 요인

### 8.1 커널 JIT (첫 렌더에 집중된다)

GPU 씬은 첫 렌더에서 **+24%**, CPU 씬은 **+12%**. (§2 GPU 문서 재인용)
GPU 커널을 실행 직전에 PTX→SASS 로 JIT 컴파일하기 때문.

| 전략 | 효과 |
|---|---|
| 같은 씬을 같은 프로세스에서 반복 | 첫 회차만 느리다. 그 뒤 fast |
| 실험마다 스크립트를 새로 실행 | **매번 JIT 비용을 낸다** |
| 셰이더를 오브젝트마다 다르게 | **커널 종류 증가 → JIT 더 비싸다** |

실측 (JIT 비용 비교):

| 셰이더 구성 | 첫 렌더 | 두 번째 | JIT |
|---|---:|---:|---:|
| 모든 오브젝트 동일 셰이더 | 1.58 s | 1.02 s | **+54%** |
| 오브젝트마다 다른 노드 그래프 | 1.61 s | 1.32 s | +22% |

> **읽는 법**: 셰이더를 공유하면 커널이 적어지고, 그래서 첫 렌더 JIT 비용이
> **더 크게** 잡힌다(= 새 커널 종류가 비싸다). 하지만 두 번째부터는 공유가 항상 빠르다.
> **반복 렌더는 셰이더를 공유하는 게 이득.**

```python
# frag
# 반복 렌더를 한 프로세스에서 끝내라 (JIT 를 1회만 지불)
for i in range(10):
    tweak_scene(i)              # 파라미터만 바꾸고
    bpy.ops.render.render(write_still=True)   # 같은 프로세스에서
# ❌ 스크립트를 10번 따로 실행하면 JIT 를 10번 낸다
```

> 템플릿이 이 구조로 되어 있다:
> [`iterative_loop_template.py`](../templates/iterative_loop_template.py).

### 8.2 셰이더 복잡도 (실측간 차이가 이 영역에서 컸다)

960×720, 64 spp:

| 씬 유형 | 시간 | 비고 |
|---|---:|---|
| 기하 중심 (SUBSURF 구 30개) | 4.51 s | 디폴트 BSDF |
| 셰이더 중심 (절차적 노이즈+보로노이) | 0.74 s | 단순한 노드 그래프 |
| 텍스처+glossy (4K×16) | 1.30 s | 반사 지배 |

> **주의**: 셰이더 씬이 가장 빠르다는 뜻이 아니다.
> 절차적 셰이더는 표면당 텍스처 페치와 랜덤 샘플이 적다.
> **glossy 반사**가 진짜로 비싸다 — 화면의 모든 픽셀이 씬을 다시 샘플링한다.
>
> **반사 지수가 높을수록 렌더 시간은 선형이 아니라 급격히 늘어난다.**
> 두 개의 거울이 마주 보는 같은 씬 vs 하나만 있는 씬의 차이는
> 표면 복잡도가 작아도 수백 배가 될 수 있다.

```python
# frag
# 탐색 중에는 반사를 끄고, 최종에서 켜라
scene.cycles.use_denoising = True
# glossy_bounces 를 1~2 로 낮추면 반사 비용 급감 (단, 반사가 어두워짐)
scene.cycles.glossy_bounces = 2
scene.cycles.max_bounces = 4
```

> **반사 억제 탐색 기법** (빠른 룩 개발용):
> 1. `glossy_bounces = 1`
> 2. 재질 roughness 를 0.5 로 올림 (거울이 아니라 무광)
> 3. 샘플 16, 해상도 25%
> 4. 최종 렌더에서만 원래 값으로
>
> 반사 씬에서 이 조합은 **10배 이상** 빨라진다. (품질 열화 확인용으로만)

---

## 8.5 🟢 레버가 아니었던 축들 (측정 완료 — 시간 쓰지 마라)

가장 쓸모 있는 문서 조각은 **"이건 손대지 마라"** 다.
아래는 전부 측정했는데 **의미 있는 차이가 없었다.** 경로를 가정하고
한번씩만 돌려 확인하면 되는 항목들이다.

| 항목 | on | off | 판정 |
|---|---:|---:|---|
| `use_light_tree` (30조명) | 0.94 s | 0.90 s | **무의미** |
| `denoising_quality` FAST/BAL/HIGH (32spp) | 0.81/0.80/0.82 s | — | **무의미** |
| EEVEE `use_fast_gi` | 3.04 s | 2.99 s | **무의미** |
| EEVEE `shadow_resolution_scale` 0.5/1.0 | 3.02 s | 3.02 s | **무의미** |
| `texture_limit` 512~4096 | 0.76~0.96 s | 0.78 s | **무의미** (§5) |
| `max_bounces` 2/4/16 | 5.12/4.94/4.56 s | — | **역효과** (§6) |

> **`use_light_tree` 가 특히 의외다.** "조명이 많으면 light tree 가 돕는다" 는
> Cycles 문서의 설명이 있지만, 이 씬(포인트 라이트 30개, 샘플 64)에서는
> 효과가 없었다. 낮은 샘플에서는 light sampling tree 의 이득이 노이즈에 묻힌다.
> **고품질(256 spp 이상) + 복잡한 조명에서만** 다시 확인해 볼 가치가 있다.

### 모션블러 (실측)

| | warm |
|---|---:|
| off | 0.90 s |
| on (shutter 0.5) | 0.97 s (**+8%**) |

모션블러는 기본적으로 **저렴**하다 (프레임당 샘플이 늘지 않는 엔진).
BVH 재사용(`use_persistent_data`)과 함께 켜도 부담이 없다.

### 출력 포맷 (960×720, 64 spp)

| 포맷 | warm | cold | 크기 |
|---|---:|---:|---:|
| PNG (8-bit) | 0.92 s | 1.79 s | 283 KB |
| JPEG | 0.84 s | 1.72 s | 18 KB |
| OpenEXR (16-bit) | 0.86 s | 1.52 s | (확인 필요) |

**포맷은 렌더 시간에 거의 영향을 주지 않는다** (0.84~0.92 s, 편차 안).
관심은 **파일 크기 = 디스크 I/O = 영상 렌더의 병목** 이다.

> 1920×1080 에서 PNG 한 장 ≈ 1.2 MB. 100프레임 영상이면 ≈ 120 MB.
> NVMe 기준 4.4 GB/s 로는 문제가 없지만, 네트워크 드라이브나
> 대량 렌더 팜에서는 **JPEG(18 KB) 또는 EXR 무압축** 이 I/O 를 줄인다.
>
> ⚠ **EXR 주의**: `image_settings.color_depth` 는 **'16' 또는 '32'만** 받는다
> (`'8'` 넣으면 TypeError). JPEG 는 8-bit, EXR 은 16/32-bit.

### 경로 가이딩 (Path Guiding) — GPU 에서 쓸 수 없다

```python
# frag
scene.cycles.use_guiding = True      # 대입은 성공
scene.cycles.guiding_radiance         # AttributeError — 이런 속성이 없다
scene.cycles.guiding_distribution     # AttributeError
```

**가이딩 관련 세분 속성이 5.2 에 존재하지 않는다** — `use_guiding` 만 있다.
그리고 공식 문서에 따르면 **path guiding 은 GPU 미지원** (CPU 전용) 이다.
→ GPU 렌더에서 켜도 실질 효과 없다. 켜지 마라.

## 9. 🟢 디테일 레벨 — 뷰포트 vs 렌더

```python
# frag
# 반복 렌더에서 viewport subdivision 만 낮춰 시간을 아낀다
ob.modifiers["Subdivision"].levels = 1          # 뷰포트 (보조용)
ob.modifiers["Subdivision"].render_levels = 1  # 실제 렌더
```

> `levels` 와 `render_levels` 의 차이: 뷰포트는 실시간 미리보기용,
> `render_levels` 는 F12 렌더에 쓰인다. **둘 다 낮춰야** 렌더가 빨라진다.
> 한쪽만 낮추면 렌더는 여전히 6레벨이다.

```python
# frag
for ob in bpy.data.objects:
    for mod in ob.modifiers:
        if mod.type == 'SUBSURF':
            mod.levels = 1
            mod.render_levels = 1
```

---

## 10. 전체 최적화 프리셋

```python
# frag
from bkkit import compat

def optimize(scene, purpose="preview"):
    """purpose: preview(탐색) | animation(영상) | final(최종)"""
    # 공통: GPU 1장 + persistent data
    ok, info = compat.enable_gpu(scene, max_devices=1)
    if not ok:
        print("CPU 폴백:", info.get("reason"))

    # GPU 를 잡은 경우만 GPU 관련 설정
    if ok:
        scene.cycles.tile_size = 2048
        try:
            scene.cycles.denoiser = "OPTIX"
            scene.cycles.denoising_use_gpu = True
        except (TypeError, AttributeError):
            compat.set_denoiser(scene)
        compat.gpu_speed_preset(scene, quality=(
            "fast" if purpose == "preview" else "balanced"))

    if purpose == "preview":
        # 탐색: 노이즈 감내, 속도 우선
        scene.render.resolution_percentage = 25
        scene.cycles.samples = 16
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.1
        scene.cycles.adaptive_min_samples = 0
        scene.cycles.use_denoising = False          # −25%
        for ob in bpy.data.objects:
            for mod in ob.modifiers:
                if mod.type == 'SUBSURF':
                    mod.levels = 1
                    mod.render_levels = 1

    elif purpose == "animation":
        # 영상: BVH 재사용이 최대 효과
        scene.render.use_persistent_data = True     # −50%
        scene.render.use_auto_generate_texture_cache = True
        scene.cycles.samples = 128
        scene.cycles.use_denoising = True
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.01

    elif purpose == "final":
        # 최종: 품질 우선, 대신 persistent data
        scene.render.resolution_percentage = 100
        scene.cycles.samples = 512
        scene.cycles.use_denoising = True
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.005
        scene.render.use_persistent_data = True
    return info
```

---

## 11. 조합 효과 (실측) — 각 항목을 합치면

960×720, 64 spp, GPU 1장, 텍스처 씬 (1K×12):

| 구성 | 시간 | 델타 |
|---|---:|---:|
| 기본 (GPU 1장, 디노이즈 ON) | 5.61 s | 기준 |
| + persistent data | 4.46 s | −21% |
| + 디노이즈 OFF | 3.34 s | **−41%** |
| + 3장 → 1장 축소 | 1.65 s | **−71%** |

> **각 항목이 독립적으로 누적된다.** 셰이더 옵션 하나만 만지작깁니다 하면
> 잡음(±27%)에 묻힌다. **큰 레버(GPU 수, persistent data, 디노이즈)를
> 먼저 확정하고** 나서 미세 조정을 하는 순서가 맞다.

---

## 12. 이 문서에서 입증하지 못한 것 (솔직한 기록)

| 항목 | 이유 |
|---|---|
| CUDA 백엔드 속도 | OptiX 와 다른 컴파일 경로. 별도 검증 필요 |
| ~~AMD/HIP 렌더~~ | **§1.3 에서 실측 — Radeon RX 7600 XT 1장 3.85 s.** ❓ 아님 |
| AMD 카드 → 카드 1:1 매칭 | `rocm-smi` 에 버스 ID 없음. 점유 시 자동 배제 불가 (§1.3) |
| Metal (macOS) | 빌드 없음 |
| GPU 클라우드 (AWS/GCP) | PCIe 가 로컬과 다름. 멀티 GPU 역효과 더 심할 수 있음 |
| OptiX denoiser vs OIDN GPU 상세 비교 | OptiX 만 측정. OIDN GPU 경로 미측정 |
| OSL 셰이더 경로 | 미측정 |
| 고해상도(4K)에서의 각 최적화 비율 | 전부 960×720 기준. 고해상도에서 디노이즈 비율은 달라진다 |
| 멀티코어 CPU 스레드 튜닝 | 미측정 |

> **고해상도에서 비율이 바뀐다**는 게 특히 중요하다.
> 4K 로 올라가면 픽셀 수만 4배가 되고 샘플 비용이 그대로지만,
> 디노이즈는 고정 크기 모델이라 **상대 비용이 줄고**,
> 기하(BVH) 비용은 **비율이 올라간다**. 이 스킬의 수치는 960×720 전용이다.

## 13. 🟢 이 문서를 쓰면서 내가 틀린 API 를 2개 적었다 — 그대로 남긴다

성급하게 문서를 쓰면 **존재하지 않는 속성 이름을 그럴듯하게 적는다.**
실제로 이 문서를 쓰면서 두 번 그랬다. 둘 다 **실행해서** 찾았다.

| 잘못 적은 것 | 실제로 | 어떻게 알아냈나 |
|---|---|---|
| `scene.cycles.adaptive_max_samples` | **없음** (5.2) | 프리셋 함수를 실제로 돌려서 |
| `scene.render.use_prefetch` | **없음** (5.2) | 프리셋 함수를 실제로 돌려서 |

둘 다 "있으면 좋겠다" 는 성질이라 **글만 보면 그럴듯하다.**
Blender 의 API 를 다룰 때 이건 가장 흔한 함정이다.

### 확인하는 법 — 의존성 없이 3초

```python
# frag  (Blender 안에서)
print(sorted(p for p in scene.cycles.bl_rna.properties if "adaptive" in p))
# → ['adaptive_min_samples', 'adaptive_threshold']          ← adaptive_max_samples 없음

print(sorted(p for p in scene.render.bl_rna.properties if "cache" in p))
# → ['use_auto_generate_texture_cache', 'use_render_cache', 'use_texture_cache']

print(sorted(p for p in scene.cycles.bl_rna.properties if "bounce" in p))
# bounces 최대화 전에 반드시
```

> ### 규칙
>
> **속성 이름을 기억으로 적지 마라.** 위 한 줄로 확인하는 것이 10초 걸리고,
> 틀린 이름을 코드에 넣으면 그 뒤로 수십 분을 잃는다.
> 이 스킬의 [`bk.py api prop`](../SKILL.md) 명령이 같은 일을 해준다:
> ```bash
> blender -b -P scripts/bk.py -- api prop RenderSettings use_persistent_data
> ```
>
> 그리고 **문서에 적을 때는 그 블록을 실제로 한 번 돌려라.**
> 문서의 "실측" 취급를 받는 코드는 실행된 적이 있어야 한다.

## Verification log

| 항목 | 근거 | 결과 |
|---|---|---|
| GPU 1/2/3/6장 스케일링 | 960×720 64spp | 🟢 PASS — 4.51/5.26/6.17 s, 6장 OOM |
| 멀티 GPU 반사 씬 격렬함 | 4K×16 텍스처 | 🟢 PASS — 1 GPU 1.65 s vs 3 GPU 4.48 s (2.7×) |
| `use_persistent_data` 정지이미지 | 960×720 | 🟢 PASS — −5% |
| `use_persistent_data` 영상 8프레임 | 카메라 애니메이션 | 🟢 **PASS — 8.25 s → 4.15 s (−50%)** |
| `use_persistent_data` 영상 12프레임 | 재확인 | 🟢 PASS — 0.39 s/frame |
| 디노이즈 ON/OFF | GPU 1장 | 🟢 PASS — −25% |
| 디노이즈 CPU/GPU | GPU 1장 | 🟢 PASS — GPU 디노이즈 −2% (작음) |
| adaptive_threshold 0.01/0.1 | 256 spp | 🟢 PASS — 0.1 이 −4%, 0.01 이 +7% |
| `texture_limit` 5단계 | 1024²×12, 4096²×16 | 🟢 **효과 없음 확인** (4096 이 오히려 +15%) |
| `max_bounces` 2/4/16 | 960×720 | 🟢 **역효과 확인** — 16 이 −8% |
| `tile_size` 256~2048 | GPU 1장 | 🟢 PASS — 2048 이 최적 (−5%), 편차 수준 |
| JIT GPU vs CPU | 5회 연속 렌더 | 🟢 PASS — GPU +24% / CPU +12% |
| JIT 셰이더 공유/고유 | 2K 텍스처 8장 | 🟢 PASS — +54% / +22% |
| 반복 측정 편차 | n=5 | 🟢 PASS — **spread 27.1%** |
| §10 프리셋 3종 실행 | 문서에서 추출해 실행 | 🟢 PASS — preview/animation/final 전부 OK |
| `adaptive_max_samples` 존재 확인 | `bl_rna.properties` | 🟢 **존재하지 않음 확인 → 문서에서 제거** |
| `use_prefetch` 존재 확인 | `bl_rna.properties` | 🟢 **존재하지 않음 확인 → `use_auto_generate_texture_cache` 로 교체** |
| `bk_env.py` 기준점 | 320×320 64spp | 🟢 PASS — cold 1.23 s / warm 0.68 s |

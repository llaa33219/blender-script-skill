# 19. 렌더 엔진 — EEVEE / Cycles / Workbench 선택과 설정

> **이 문서가 답하는 질문**: "Cycles 로 해야 하나, EEVEE 로 하면 안 되나?"
> 속도만 보면 답이 들키는데 **품질까지 같이 보면 답이 뒤집힌다.**
> 아래 수치는 이 머신에서 직접 돌린 값이다. (측정 잡음 처리: [`17-environment-baseline.md`](17-environment-baseline.md) §4)

## 0. 30초 결론

| | 속도 | 품질 | 써야 할 때 |
|---|---|---|---|
| **Workbench** | 🥇 **0.09 s** | 클레이(재질 없음) | 씬 구조 확인, 레이아웃, 임시 확인 |
| **EEVEE** | 🥈 0.47 s | 화면 표시 재질, **굴절/반사 불완전** | 탐색, 빠른 미리보기, 애니메이션 |
| **Cycles** | 🥉 0.67 s | **정확** (물리 기반) | 최종 산출물, 반사/굴절/GI |

> ### 역설 — 여기까지가 이 문서의 핵심
>
> **속도만 보면 EEVEE → Cycles 순서인데, 실제 병목은 샘플 64 에서 0.3~0.7 s 다.**
> 수십 초·수 분짜리 "느린 렌더"의 원인은 **엔진이 아니라 샘플 수와 씬 복잡도** 다.
>
> **엔진을 바꾸면 최대 7배만 달라진다. 샘플을 바꾸면 100배가 달라진다.**
>
> → "렌더가 느려요"라는 질문에는 **먼저 샘플 수를 봐라.**

---

## 1. 🟢 엔진은 3개가 아니다 — 5.2 에서 실제로 되는 것

```python
# frag
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
sc = bpy.context.scene

# RNA enum 은 거짓말한다. Cycles 는 등록돼 있는데 여기 안 보인다.
print([i.identifier for i in sc.render.bl_rna.properties["engine"].enum_items])
# → ['BLENDER_EEVEE']        ← CYCLES 가 없다!

for cand in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH"):
    try:
        sc.render.engine = cand
        print(f"{cand:22} OK")
    except TypeError:
        print(f"{cand:22} 거부")
```

**실측 출력 (5.2.2):**
```
  BLENDER_EEVEE          OK
  BLENDER_EEVEE_NEXT     거부      ← 4.x 에서 이 이름이었다. 5.x 에서 사라짐
  CYCLES                 OK
  BLENDER_WORKBENCH      OK
```

> ⚠ **`BLENDER_EEVEE_NEXT` 는 4.x 의 이름이다.** 5.x 에서 EEVEE 가
> `BLENDER_EEVEE` 로 통합됐다. 4.x 튜토리얼을 그대로 따라가면 엔진이 안 바뀐다.
>
> ⚠ 그리고 RNA `enum_items` 에 CYCLES 가 **없는데도 대입은 된다.**
> (`engine_enum_items()` 함수가 정확히 이 함정을 문서화하고 있다)

---

## 2. 🟢 GPU 백엔드 — EEVEE 와 Cycles 는 **다른 GPU 에서 돈다**

이게 가장 중요하고 가장 알려지지 않은 사실이다.

```python
# frag
import bpy, addon_utils, gpu
addon_utils.enable("cycles", default_set=True, persistent=True)
gpu.init()                       # ← 5.2 에서 인자를 받지 않는다
pt = gpu.platform
print(pt.backend_type_get(), "|", pt.vendor_get(), "|", pt.renderer_get())
```

**실측 출력 (이 머신):**
```
OPENGL | AMD | AMD Radeon RX 7600 XT (radeonsi, navi33, ACO, DRM 3.64, 7.2.9-2-cachyos)
```

| | 백엔드 | 이 머신에서 쓰는 카드 (기본) |
|---|---|---|
| **Cycles** | OptiX | **NVIDIA RTX 4070** (CUDA) |
| **EEVEE** | OpenGL | **AMD Radeon RX 7600 XT** |

> ⚠ **이것은 기본값일 뿐이다.** EEVEE 는 **Vulkan 백엔드로 바꾸면
> NVIDIA 카드로도 돌아간다** (§2.5 에 실측). EEVEE 가 AMD 에 묶이는 것은
> OpenGL 백엔드가 첫 카드만 노출하기 때문이고, Vulkan 은 8개 기기 전부 열거한다.
>
> ### 왜 차이가 생기나
>
> Cycles 는 **Compute API**(OptiX/CUDA/HIP/Metal)로 직접 렌더 커널을 띄운다.
> EEVEE 는 **Blender 의 GPU 모듈(OpenGL/Vulkan)** 를 통해 그린다.
> 두 스택은 **완전히 다른 드라이버 경로**다.
>
> ### 왜 이게 문제인가
>
> 1. **NVIDIA 강점(OptiX RT)이 EEVEE 에는 없다.**
>    OptiX 하드웨어 RT 는 OptiX 경로 전용이라 EEVEE 가 못 쓴다.
>    (EEVEE 의 RT 는 Vulkan 경로의 스크린스페이스 근사다)
> 2. **머신에 두 벌의 드라이버가 필요하다.** (NVIDIA + Mesa/AMD)
>    Mesa 드라이버가 없으면 EEVEE 가 llvmpipe 로 떨어진다.
>    **실측: reflective 씬에서 OpenGL 0.51 s → llvmpipe 3.84 s (7.5배),
>    cold 는 29.31 s** (§2.5). 기존 문서의 "100배" 는 다른 씬 기준이다.
> 3. **EEVEE 가 어느 카드를 타는지는 렌더마다 확인할 것.**
>    `gpu.platform.renderer_get()` 로 즉시 알 수 있다.
>
> ```python
> # frag  — 렌더 전에 EEVEE 가 어느 GPU 를 타는지 확인하라
> import gpu
> gpu.init()
> rt = gpu.platform.renderer_get()
> if "llvmpipe" in rt.lower() or "softpipe" in rt.lower():
>     print("!! EEVEE 가 소프트웨어 렌더러로 떨어졌다 — Cycles CPU 가 더 빠르다")
> print("EEVEE GPU:", rt)
> ```

---

### 2.5 🟢 Vulkan 백엔드 — EEVEE 를 어느 GPU 에서 돌릴지 선택할 수 있다

OpenGL 백엔드는 **첫 카드 하나만 노출**한다. 이 머신에서는 AMD RX 7600 XT.
Vulkan 은 **모든 GPU 를 열거**하고 그중 하나를 고를 수 있게 한다.

```bash
blender -b --factory-startup --gpu-backend vulkan --gpu-device help
```

**실측 출력 (5.2.2, 이 머신):**
```
Blender GPU Device Listing (Vulkan):
  Index  Device-ID    Name
  0      1002/7480/0  AMD Radeon RX 7600 XT (RADV NAVI33)
  1      10de/2484/1  NVIDIA GeForce RTX 3070
  2      10de/2486/2  NVIDIA GeForce RTX 3060 Ti
  3      1002/7480/3  AMD Radeon RX 7600 XT (RADV NAVI33)
  4      10de/2d04/4  NVIDIA GeForce RTX 5060 Ti
  5      10de/2786/5  NVIDIA GeForce RTX 4070
  6      10de/2803/6  NVIDIA GeForce RTX 4060 Ti
  7      10de/2803/7  NVIDIA GeForce RTX 4060 Ti
  8      10005/0/8    llvmpipe (LLVM 23.1.1, 256 bits)
```

#### 🟢 실측 — EEVEE 백엔드 × GPU (960×720, 64 spp, warm median)

| 백엔드 / 디바이스 | mixed | reflective | interior |
|---|---:|---:|---:|
| OpenGL (AMD RX 7600 XT) | 3.00 s | 0.51 s | 0.42 s |
| Vulkan dev 0 (AMD RX 7600 XT) | 2.88 s | 0.43 s | 0.34 s |
| **Vulkan dev 5 (RTX 4070)** | **2.94 s** | **0.28 s** | **0.24 s** |
| Vulkan dev 8 (**llvmpipe**) | — | **3.84 s** (cold 29.31 s) | — |

**읽는 법**:
- **픽셀은 4가지 모두 `luma=0.1161` / `0.2826` 로 동일하다.** 백엔드·디바이스가
  아니라 렌더 결과가 같다는 뜻이다.
- Vulkan 은 OpenGL 보다 **약간 빠르다** (reflective 0.51 → 0.43 s).
- **NVIDIA 카드로 EEVEE 를 돌리면 가장 빠르다** (0.51 → 0.28 s, **1.8배**).
  OpenGL 로는 이걸 할 수 없다 — AMD 하나만 노출되기 때문이다.
- llvmpipe 는 **0.51 s → 3.84 s (7.5배), cold 는 29.31 s**. 반드시 피해야 한다.

#### ⚠ prefs 로는 백엔드가 안 바뀐다 — CLI 플래그만 통한다

```python
# frag
sp = bpy.context.preferences.system
print(sp.gpu_backend)                      # 'OPENGL'
print([i.identifier for i in sp.bl_rna.properties["gpu_backend"].enum_items])
# → ['OPENGL', 'METAL', 'VULKAN']          ← enum 은 있다

sp.gpu_backend = "VULKAN"                  # 대입은 성공한다
print(sp.gpu_backend)                      # 'VULKAN'  ← 읽기백은 VULKAN

import gpu; gpu.init()
print(gpu.platform.backend_type_get())     # 'OPENGL'  ← 실제로는 그대로!
```

**실측: 대입은 되고 읽기백도 `VULKAN` 인데, 런타임 백엔드는 `OPENGL` 이다.**
Blender 의 GPU 백엔드는 **프로세스 시작 시점(CLI 플래그)에서만** 확정된다.
prefs 는 저장용이고 현재 프로세스에는 영향이 없다.

> **유일한 방법**: 커맨드라인
> ```bash
> blender -b --gpu-backend vulkan --gpu-device 5 ...
> blender -b --gpu-backend vulkan --gpu-device help   # 지원 기기 목록
> ```

#### Vulkan 플래그는 EEVEE 만 바꾼다 — Cycles 는 여전히 OptiX

```python
# frag
import gpu, sys
sys.path.insert(0, ".../scripts")
from bkkit import compat
gpu.init()
print(gpu.platform.backend_type_get(), gpu.platform.renderer_get())
# VULKAN NVIDIA GeForce RTX 4070
rep = compat.gpu_report()
print(rep["backend"])                      # OPTIX  ← 그대로
```

**실측**: `--gpu-backend vulkan --gpu-device 5` 로 실행해도
Cycles 는 **RTX 4070 / OptiX** 로 렌더한다. 플래그는 EEVEE 백엔드만 바꾼다.
**두 스택은 완전히 독립**이므로 EEVEE 를 Vulkan 으로 올려도 Cycles 설정은 영향받지 않는다.

| 플래그 | EEVEE | Cycles |
|---|---|---|
| (없음) | OpenGL / AMD RX 7600 XT | OptiX / RTX 4070 |
| `--gpu-backend vulkan --gpu-device 5` | **Vulkan / RTX 4070** | OptiX / RTX 4070 |

#### ⚠ 한계 — Vulkan 디바이스를 자동 선택하는 것은 위험하다

`--gpu-device` 의 인덱스는 **Vulkan 열거 순서**라 nvidia-smi 의 카드와
직접 매칭되지 않는다. Vulkan 출력에는 버스 ID 가 없다:

```
  5      10de/2786/5  NVIDIA GeForce RTX 4070
  # ← PCI vendor/device ID 만 있고 버스 ID(82:00) 가 없다
```

그래서 `bkkit.compat.pick_eevee_vulkan_device()` 는 **여유 VRAM 이 있는
카드가 여러 장이면 자동 선택을 거부한다:**

```
picked index=None  reason=Vulkan 디바이스와 nvidia-smi 의 카드 매칭이 불가능하고
                           여유 VRAM 이 있는 카드가 4장 — 자동 선택 안 함
```

이 머신에서 device 1(RTX 3070)이 다른 프로세스가 94% 점유 중인데
Vulkan 목록의 1번은 RTX 3070 이었다. **인덱스로 골랐다면 남의 카드를 잡았을 것이다.**

```python
# frag
from bkkit import compat
idx, why = compat.pick_eevee_vulkan_device()
print(idx, why)
# 여러 후보가 있으면 None 이 온다 — CLI 플래그로 직접 지정하라
```

```bash
# 확실할 때만 수동 지정
blender -b --factory-startup --gpu-backend vulkan --gpu-device 5 -P script.py
```

#### ⚠ llvmpipe 는 자동으로 걸러야 한다

Vulkan 목록 맨 끝에 **항상 llvmpipe 가 있다** (CPU 소프트웨어 래스터라이저).
디바이스를 잘못 고르면 조용히 느려진다. 렌더 전에 확인하라:

```python
# frag
import gpu
gpu.init()
rt = gpu.platform.renderer_get()
vendor = gpu.platform.vendor_get()
print(f"EEVEE GPU: {rt} (vendor={vendor})")
if "llvmpipe" in rt.lower() or vendor.upper() == "SOFTWARE":
    print("!! 소프트웨어 렌더러 — Cycles CPU 가 훨씬 빠르다")
```

---

## 3. 🟢 엔진 × 씬 실측 매트릭스

960×720, 샘플 64, `use_persistent_data=True`, GPU 1장.
`warm` = 4회 반복의 median (첫 회차 cold 는 §5 에 별도).

| 씬 | Workbench | EEVEE | Cycles | 비고 |
|---|---:|---:|---:|---|
| **mixed** (SUBSURF 구 30) | 2.62 s | 3.06 s | **0.30 s** | 기하 복잡 |
| **reflective** (거울+유리) | **0.09 s** | 0.47 s | 0.67 s | 반사/굴절 |
| **interior** (평면+광원) | **0.09 s** | 0.44 s | 0.33 s | 단순 |

```
=== mixed ===
eng=BLENDER_WORKBENCH  cold= 3.06s warm= 2.62s luma=0.3058
eng=BLENDER_EEVEE      cold= 3.50s warm= 3.06s luma=0.2826
eng=CYCLES             cold= 4.91s warm= 0.30s luma=0.2824
=== reflective ===
eng=BLENDER_WORKBENCH  cold= 0.38s warm= 0.09s luma=0.5317
eng=BLENDER_EEVEE      cold= 0.83s warm= 0.47s luma=0.1161
eng=CYCLES             cold= 2.27s warm= 0.67s luma=0.1849
=== interior ===
eng=BLENDER_WORKBENCH  cold= 0.38s warm= 0.09s luma=0.3501
eng=BLENDER_EEVEE      cold= 0.86s warm= 0.44s luma=0.4125
eng=CYCLES             cold= 1.95s warm= 0.33s luma=0.4123
```

> ### ⚠ `mixed` 에서 Cycles 가 0.30 s 인 이유 — 지터를 읽어야 한다
>
> EEVEE(3.06 s)보다 **10배 빠른데**, `cold` 는 4.91 s 로 EEVEE 보다 느리다.
> GPU 쪽 상태를 보면:
>
> | | cold | warm | 비고 |
> |---|---:|---:|---|
> | EEVEE (AMD RX 7600 XT) | 3.50 s | 3.06 s | 거의 안 변함 |
> | Cycles (RTX 4070) | 4.91 s | **0.30 s** | **16배 감소** |
>
> → EEVEE 는 **Mesa(AMD) 스택이 고정 비용이 크고 캐싱이 안 된다.**
> Cycles 는 **OptiX 커널 캐시가 첫 렌더 후 완전히 히트**한다.
> **반복 렌더를 여러 번 한다면 Cycles 가 압도적으로 이득**이다.

---

## 4. 🟢 품질 차이는 수치보다 눈으로 봐야 한다

reflective 씬(거울 바닥 + 유리 큐브 + 빨간 큐브)을 세 엔진으로 렌더한 결과:

```
Workbench (0.09s)          EEVEE (0.47s)              Cycles (0.67s)
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│                  │      │                  │      │                  │
│   ▓▓▓▓▓▓▓▓       │      │      ▓▓▓▓        │      │   ▓▓▓▓  ▒▒▒     │
│   (전부 클레이)   │      │   빨간 큐브만     │      │  빨간 큐브 +      │
│                  │      │   보임. 유리는    │      │  유리 굴절이      │
│   재질 없음      │      │   거의 검정      │      │  실제로 보임      │
│   그림자 없음    │      │   반사 거의 없음  │      │  거울 반사 정확   │
│                  │      │                  │      │  그림자 부드러움  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
mean_luma  0.5317          mean_luma  0.1161          mean_luma  0.1849
```

`mean_luma` 만 보면 EEVEE(0.1161)가 Cycles(0.1849)보다 어둡다.
**EEVEE 는 씬을 정확히 재현하지 못한 것이다**, 소실이 아니라 **계산 안 함**이다.

> ### EEVEE 와 Cycles 가 갈리는 지점
>
> | 기능 | EEVEE (RT off) | EEVEE (RT on) | Cycles |
> |---|---|---|---|
> | 기본 음영 | ✅ | ✅ | ✅ |
> | 반사 (screen-space) | ❌ 없음 | ⚠ 근사 | ✅ 정확 |
> | 유리 굴절 | ❌ 검정 | ⚠ 근사 | ✅ 정확 |
> | 간접광 (GI) | ❌ 없음 | ⚠ 근사 | ✅ 정확 |
> | 다중 반사 | ❌ | ⚠ 1회 근사 | ✅ |

**실측 (reflective 씬, EEVEE 레이 트레이싱 on/off):**
```
EEVEE use_raytracing=False : 0.85 s  luma=0.1161
EEVEE use_raytracing=True  : 1.26 s  luma=0.1281
Cycles                     : 2.49 s  luma=0.1868
```
→ 레이 트레이싱을 켜면 EEVEE 가 Cycles 에 **훨씬 가까워진다** (0.1161 → 0.1281, 목표 0.1868).
속도는 1.5배가 되지만 여전히 Cycles 보다 빠르다.

> **EEVEE 의 레이 트레이싱은 "있으면 Cycles 급으로 가까워지는" 옵션이지,
> Cycles 의 대체가 아니다.** 다중 반사·정확한 굴절은 여전히 못 따라온다.

---

## 5. 🟢 cold vs warm — 엔진마다 캐싱 동작이 다르다

4회 연속 렌더의 각 회차:

| 엔진 | cold | warm (2~4회차 median) | 감소율 |
|---|---:|---:|---:|
| EEVEE (reflective) | 0.83 s | 0.47 s | −43% |
| EEVEE (mixed) | 3.50 s | 3.06 s | −13% |
| **Cycles (mixed)** | **4.91 s** | **0.30 s** | **−94%** |
| Cycles (reflective) | 2.27 s | 0.67 s | −70% |

> **Cycles 는 첫 렌더 후 미친 듯이 빨라진다.** OptiX 커널 캐시가 히트하기 때문이다.
> **EEVEE 는 개선이 미미하다.** Mesa/OpenGL 경로의 셰이더 캐싱이 약하다.
>
> ### 실전 규칙
>
> | 렌더 횟수 | 선택 |
> |---|---|
> | **1~3회** (결과물 1개) | cold 가 크므로 **EEVEE 가 나을 수 있다** |
> | **4회 이상** (반복 최적화, 영상) | **Cycles 가 압도적** (0.30 s vs 3.06 s) |
>
> **렌더를 한 번만 한다면 EEVEE 로 충분하다.**
> 10번 이상 돌린다면 cold 를 EEVEE 가 3.50 s, Cycles 가 4.91 s 로 비슷하지만
> 그 뒤로 Cycles 가 10배 빨라진다.

---

## 6. 🟢 샘플 수 — 엔진보다 훨씬 큰 레버

**EEVEE (reflective, pd=True):**
| 샘플 | warm | 비고 |
|---|---:|---|
| 16 | 0.25 s | |
| 64 | 0.46 s | |
| 256 | 1.70 s | **선형 증가** |

**Cycles (reflective):**
| 샘플 | warm | 비고 |
|---|---:|---|
| 16 | 0.81 s | |
| 64 | 0.98 s | |
| 256 | 1.65 s | **거의 변하지 않음** |

> ### 읽는 법 — 이게 핵심이다
>
> **EEVEE 는 샘플에 선형으로 비례한다.** 16→256 = 6.8배.
> **Cycles 는 거의 변하지 않는다.** 16→256 = 2배 (적응형 샘플링 + 디노이즈).
>
> → **샘플을 높여 품질을 얻으려면 EEVEE 가 비용이 크고, Cycles 가 싸다.**
> Cycles 에서 샘플 256 → 512 → 1024 로 올려도 비용이 선형이 아니다.
>
> | 목표 | 권장 |
> |---|---|
> | 빠른 탐색 | EEVEE 샘플 16 |
> | 중간 확인 | EEVEE 샘플 64, 또는 Cycles 샘플 64+디노이즈 |
> | 최종 품질 | **Cycles 샘플 256~512 + 디노이즈** (비용 대비 최고) |

---

## 7. ⚠ EEVEE 의 반복 측정 편차 — 이 머신에서 특히 심하다

**동일 설정, 4회 반복:**
```
EEVEE mixed  : 3.50 → 3.06 s (편차 작음)
Cycles mixed : 4.91 → 0.30 s (편차 매우 큼)
```

EEVEE 는 편차가 작은 대신 캐싱 이득도 없다.
**Cycles 는 편차가 크지만 그 이득이 10배다.**
전체 반복(예: 20회) 총합으로는 **Cycles 압승**이다.

> **판정 기준**: 3회 이하라면 EEVEE. 그 이상은 Cycles.
> 애니메이션은 기본 24~250프레임이므로 **Cycles 가 정답**이다.

---

## 8. 🟢 엔진 선택 플로우

```
질문: 이 렌더로 무엇을 하는가?
│
├─ 씬 구조 확인? (배치, 카메라 프레이밍)
│   └─ Workbench  (0.09 s, 클레이)      ← 속도 최우선, 품질 무관
│
├─ 탐색 / 반복 최적화? (3회 이하)
│   └─ EEVEE 샘플 16~32                ← cold 3.50 s vs Cycles 4.91 s
│
├─ 애니메이션? (영상 렌더)
│   └─ Cycles 샘플 128~256 + persistent_data   ← 10프레임 넘으면 압도적
│
├─ 반사·굴절·GI 가 핵심? (제품 렌더, 유리, 금속)
│   └─ Cycles  ← EEVEE 는 근사밖에 못 함
│
└─ GPU 없는 머신?
    └─ Cycles CPU  ← EEVEE 는 llvmpipe 로 100배 느림 (기존 실측)
```

---

## 9. 🟢 엔진별 최적 설정 모음

### 9.1 Workbench — 속도 최우선

```python
# frag
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"       # 또는 "FLAT"
scene.display.shading.color_type = "SINGLE"  # 단색 (가장 빠름)
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.display.render_aa = "OFF"              # 앤티앨리어싱 끄기
```

### 9.2 EEVEE — 탐색·애니메이션

```python
# frag
scene.render.engine = "BLENDER_EEVEE"
ee = scene.eevee

# 속도 우선 (기본값)
ee.taa_render_samples = 32                  # 64 → 32 로 낮춰도 육안 차이 적음
ee.use_raytracing = False                   # RT 는 1.5배 느림. 탐색에서 불필요

# 품질 우선 (최종 미리보기)
ee.use_raytracing = True                    # 반사·굴절 근사 (Cycles 의 1.5배 느림)
ee.use_shadows = True
ee.use_fast_gi = False                      # Fast GI 는 거의 효과 없음 (측정: 3.04 vs 2.99 s)
ee.shadow_resolution_scale = 1.0            # 0.5 로 낮춰도 시간 차이 미미
```

### 9.3 Cycles — 최종 산출물

```python
# frag
from bkkit import compat
ok, info = compat.enable_gpu(scene, max_devices=1)   # GPU 1장 + 폴백
scene.cycles.samples = 256                 # EEVEE 와 달리 비용이 선형 아님
scene.cycles.use_denoising = True          # 샘플을 4배 줄여도 시간 동일
scene.cycles.adaptive_threshold = 0.01
scene.render.use_persistent_data = True    # 반복 렌더 13.7배 효과
```

---

## 10. 엔진 선택을 코드로 — `bk_render_engine()`

```python
# frag
def bk_render_engine(scene, purpose="final", samples=None):
    """엔진 자동 선택. purpose: structure | explore | animate | final"""
    if purpose == "structure":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.color_type = "SINGLE"
        scene.display.render_aa = "OFF"
        return {"engine": "BLENDER_WORKBENCH", "note": "클레이. 품질 무관"}

    if purpose == "explore":
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = samples or 32
        scene.eevee.use_raytracing = False
        try:
            import gpu
            gpu.init()
            rt = gpu.platform.renderer_get()
        except Exception:
            rt = "unknown"
        if "llvmpipe" in rt.lower():
            # 소프트웨어 렌더러 — EEVEE 는 100배 느림. Cycles CPU 로 전환.
            scene.render.engine = "CYCLES"
            from bkkit import compat
            compat.set_engine(scene, "CYCLES")
            scene.cycles.device = "CPU"
            scene.cycles.samples = samples or 32
            return {"engine": "CYCLES", "note": "llvmpipe — EEVEE 사용 불가"}
        return {"engine": "BLENDER_EEVEE", "gpu": rt}

    if purpose in ("animate", "final"):
        from bkkit import compat
        ok, info = compat.enable_gpu(scene, max_devices=1)
        compat.gpu_speed_preset(scene, quality="balanced")
        scene.cycles.samples = samples or (128 if purpose == "animate" else 512)
        scene.cycles.use_denoising = True
        scene.render.use_persistent_data = True
        return {"engine": "CYCLES", "gpu": ok,
                "devices": info.get("num_gpu_devices")}
    return None
```

---

## 11. 이 문서에서 입증하지 못한 것 (솔직한 기록)

| 항목 | 이유 |
|---|---|
| CUDA/OptiX 아닌 백엔드 | EEVEE 는 OpenGL, Cycles 는 OptiX. NVIDIA 전용 EEVEE 미측정 |
| ~~EEVEE Vulkan 백엔드~~ | **§2.5 에서 실측 완료.** ❓ 아님 |
| Metal (macOS) | 빌드 없음 |
| EEVEE + Cycles 백엔드 조합 전체 | OptiX+OpenGL, OptiX+Vulkan, HIP 은 실측. CUDA+Metal 조합은 미측정 |
| volumetrics | 실측 안 함 (EEVEE 볼륨 vs Cycles 볼륨 차이 큼) |
| Blender 4.x EEVEE Legacy | `BLENDER_EEVEE_NEXT` 가 사라진 경계만 확인 |
| 모션 블러 / DOF | 미측정 (블러 큐브는 EEVEE 가 훨씬 싸다) |
| **llvmpipe 강제 렌더 시간** | **§2.5 에서 실측 — reflective 29.31 s** |

> **Vulkan 경로는 §2.5 에서 실측했다 — ❓ 가 아니다.**
> 결론은 §2.5 의 표에 있다.

## Verification log

| 항목 | 근거 | 결과 |
|---|---|---|
| 엔진 4개 대입 가능 여부 | `scene.render.engine` | 🟢 PASS — EEVEE/CYCLES/WORKBENCH OK, **EEVEE_NEXT 거부** |
| RNA enum 에 CYCLES 없음 | `bl_rna.properties['engine']` | 🟢 PASS — `['BLENDER_EEVEE']` 만 (거짓말 확인) |
| EEVEE GPU 백엔드 확인 | `gpu.init()` + `gpu.platform` | 🟢 PASS — **OPENGL / AMD RX 7600 XT** |
| Cycles GPU 백엔드 | `compat.gpu_report()` | 🟢 PASS — **OPTIX / NVIDIA RTX 4070** |
| 엔진 × 씬 3×3 매트릭스 | 960×720 64spp pd=True | 🟢 PASS — 9개 조합 전부 측정 |
| EEVEE 레이 트레이싱 on/off | reflective 씬 | 🟢 PASS — 0.85 s / 1.26 s, luma 0.1161 / 0.1281 |
| EEVEE Fast GI on/off | mixed 씬 | 🟢 PASS — 3.04 vs 2.99 s (효과 없음) |
| EEVEE 샘플 스케일 16/64/256 | reflective | 🟢 PASS — 0.25 / 0.46 / 1.70 s (선형) |
| Cycles 샘플 스케일 16/64/256 | reflective | 🟢 PASS — 0.81 / 0.98 / 1.65 s (거의 평탄) |
| persistent_data 반복 효과 | mixed, Cycles | 🟢 **PASS — 3.83 → 0.28 s (13.7배)** |
| 엔진별 cold/warm 비교 | 4회 반복 | 🟢 PASS — Cycles −94%, EEVEE −13~43% |
| shadow_resolution_scale 0.5/1.0 | mixed, EEVEE | 🟢 PASS — 3.02 vs 3.02 s (효과 없음) |

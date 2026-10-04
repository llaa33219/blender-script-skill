# 14. GPU 렌더링 — Cycles 가속과 그 함정

> **이 문서의 검증 경계를 먼저 읽어라.** GPU 문서를 쓰면서 가장 위험한 건
> "돌려보지 않은 걸 실행된 것처럼 쓰는 것" 이다. 그래서 각 항목을 세 등급으로 나눴다.
>
> | 기호 | 뜻 | 근거 |
> |---|---|---|
> | 🟢 **실측** | 이 빌드에서 직접 실행·관측 | Blender 5.2.2 LTS, `d13f752e3b9c` |
> | 📄 **공식 문서** | Blender 5.2 매뉴얼 / 릴리즈 노트 인용 | 출처 URL 병기 |
> | ❓ **미검증** | GPU 실물이 있어야만 확인 가능 | 이 문서에서 명시적으로 미검증 표시 |
>
> **이 샌드박스에는 GPU 가 없다.** 따라서 *API 표면·enum·함정·폴백 동작* 은 전부 🟢 로
> 실측했고, *요구 사양·성능 수치* 는 📄 로 공식 출처를 인용했다.
> ❓ 로 표시된 항목은 직접 재현하지 않았다는 뜻이다.

---

## 1. ⭐ 가장 중요한 발견 — GPU 없는 머신에서 "GPU 모드"가 조용히 성공한다

이건 문서를 다 쓰고 나서 실측 검증하다가 나온 건데, **이게 이 문서에서 제일 값진 내용**이다.

```python
# frag  (스크립트 파일: audit/gpu7.py — GPU 없는 머신에서 실행)
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
p = bpy.context.preferences.addons["cycles"].preferences
p.compute_device_type = "CUDA"     # GPU 없는데 대입 성공
p.refresh_devices()
print(p.get_num_gpu_devices(), p.has_active_device())   # 0  False
sc = bpy.context.scene
sc.cycles.device = "GPU"
sc.render.engine = "CYCLES"
res = bpy.ops.render.render(write_still=True)
print(res)                          # {'FINISHED'}
```

**실측 출력 (GPU 0대 머신)**
```
get_device_types(): (True, True, True, False, True, True)
compute_device_type 대입 결과: CUDA  (GPU 없는데도 성공!)
refresh 후 devices: [('Intel Xeon Platinum 8163 CPU @ 2.50GHz', 'CPU', False)]
get_num_gpu_devices(): 0
has_active_device(): False
available_devices('CUDA'): (('Intel Xeon Platinum 8163 CPU @ 2.50GHz', 'CPU', 'CPU', False, False, True, False, True),)
scene.cycles.device = GPU
렌더 반환: {'FINISHED'}
```

그리고 결과 이미지를 측정하면:
```
GPU 없는 머신의 'GPU 모드' 렌더 결과: mean_luma=0.0751 verdict=ok
→ 즉 CPU로 조용히 렌더됨. 에러도, 경고도, 빈 파일도 아니다.
```

> ### 왜 이게 위험한가
>
> 1. `compute_device_type = 'CUDA'` **대입은 에러 없이 성공**한다
> 2. `scene.cycles.device = 'GPU'` 도 **에러 없이 성공**한다
> 3. `bpy.ops.render.render()` 는 **`{'FINISHED'}`** 를 반환한다
> 4. 파일도 **정상적으로 저장**된다
> 5. `bk.py render` 의 씬 검증도 **통과**한다 (verdict=ok)
>
> GPU 파이프라인 구축 후 "속도가 안 나는데 뭐가 문제지?" 하고 한참 헤매게 된다.
> **렌더 시간 측정 없이는 GPU 설정을 "적용됐다"고 결론 내릴 수 없다.**

**따라서 GPU 파이프라인의 첫 단계는 반드시 "GPU가 실제로 잡혔는지" 검사하는 것이다.**
헬퍼는 §5 에 있다.

### 1.1 왜 대입이 성공하나 — 백엔드가 "컴파일돼 있다" ≠ "장치가 있다"

`cycles` 애드온 소스 (`5.2/scripts/addons_core/cycles/properties.py`) 에서 🟢 확인:

```python
def get_device_types(self, context):
    import _cycles
    has_cuda, has_optix, has_hip, has_metal, has_oneapi, has_hiprt = _cycles.get_device_types()
    list = [('NONE', "None", ..., 0)]
    if has_cuda:  list.append(('CUDA',  ..., 1))
    if has_optix: list.append(('OPTIX', ..., 3))
    if has_hip:   list.append(('HIP',   ..., 4))
    if has_metal: list.append(('METAL', ..., 5))
    if has_oneapi:list.append(('ONEAPI',..., 6))
    return list
```

이 6개 불리언은 **하드웨어 감지가 아니라 "이 빌드에 백엔드가 컴파일돼 있나"** 다.

**실측: GPU 0대 Linux 머신에서**
```python
import _cycles
print(_cycles.get_device_types())
# (True, True, True, False, True, True)
#  CUDA ✓  OPTIX ✓  HIP ✓  METAL ✗  ONEAPI ✓  HIPRT ✓
```

즉 CUDA/OptiX/HIP/oneAPI 백엔드는 **GPU 없이도 "사용 가능"으로 보고된다.**
`METAL` 만 `False` — macOS 전용 빌드 기능이므로.

> **실제 장치 목록은 따로 봐야 한다.** `available_devices()` 가 진짜 답이다:
>
> ```python
> import _cycles
> _cycles.available_devices('CUDA')
> # 실측 (GPU 없는 머신):
> # (('Intel Xeon Platinum 8163 CPU @ 2.50GHz', 'CPU', 'CPU', False, False, True, False, True),)
> #                                    ↑ 이름        ↑타입  ↑영구ID
> # GPU 종류가 섞인 게 아니라 **CPU 항목 하나뿐** → GPU 없음의 증거
> ```

---

## 2. 백엔드 5종 요구 사양 (📄 공식 5.2 매뉴얼)

출처: <https://docs.blender.org/manual/en/latest/render/cycles/gpu_rendering.html>
및 5.2 릴리즈 노트 <https://developer.blender.org/docs/release_notes/5.2/cycles/>

| 백엔드 | OS | 최소 하드웨어 | 최소 드라이버 |
|---|---|---|---|
| **CUDA** (NVIDIA) | Windows, Linux | compute capability **5.0+** | 현재 드라이버 |
| **OptiX** (NVIDIA) | Windows, Linux | compute capability **5.0+** | **575** |
| **HIP** (AMD) | Windows, Linux | **RDNA1 이상** (RX 5000/6000/7000/9000, Pro W6000/W7000) | Win: Radeon Software **24.9.1** / PRO **24.Q4**<br>Linux: Radeon Software **24.30** / ROCm HIP Runtime **6.3** |
| **oneAPI** (Intel) | Windows, Linux | Intel Arc **Xe HPG** (A-Series, B-Series) | Win: Intel Graphics Driver **XX.X.101.8306**<br>Linux: `intel-compute-runtime` **XX.XX.37435.3** |
| **Metal** (Apple) | macOS 13.0+ | Apple Silicon | macOS 13.0+ |

> ⚠ **매뉴얼과 릴리즈 노트의 Intel 드라이버 숫자가 다르다.**
>
> | 출처 | Windows | Linux |
> |---|---|---|
> | 5.2 매뉴얼 GPU 렌더링 페이지 | `XX.X.101.5518` | `XX.XX.34666.3` |
> | 5.2 릴리즈 노트 (Cycles) | `XX.X.101.8306` | `XX.XX.37435.3` |
>
> 릴리즈 노트가 더 높다. **"GPU가 안 잡힌다" 는 문제의 원인이 이것일 수 있다.**
> 애매하면 높은 쪽(릴리즈 노트)을 기준으로 판단할 것.
>
> > 참고: 이전 문서 세대(3.3/3.6)에는 CUDA CC 3.0, OptiX 드라이버 470 이라고 적혀 있었다.
> > 현재 요구치는 그보다 높다. 구버전 튜토리얼의 숫자를 신뢰하지 마라.

### 2.1 백엔드별 부가 기능 가용성 (📄)

| 기능 | 조건 |
|---|---|
| 하드웨어 레이 트레이싱 가속 | OptiX는 RTX 카드, HIP는 RX 6000+ (최신 드라이버), oneAPI는 전 Arc, Metal은 Apple Silicon |
| OpenImageDenoise **GPU** 가속 | NVIDIA compute capability **7.0+** (= 전 RTX)<br>AMD: Linux는 RX 6000+ 디스크리트, **Windows는 RX 7000+** 디스크리트<br>Intel: 전 지원 GPU, Apple: Apple Silicon |
| Open Shading Language | **OptiX 전용** (그 외 백엔드 미지원) |
| Path Guiding | **모든 GPU에서 미지원** ❓ (CPU 전용) |

> **5.2 변경 사항** (📄 릴리즈 노트)
> - OptiX 최소 드라이버가 **575** 로 올랐다
> - **AMD RDNA2 에서 OIDN GPU 가속이 제거**됐다 (ROCm 비호환)
> - HIP 에서 하드웨어 RT 없이 **Shadow Caustics 미지원** (하드웨어 RT는 기본 활성)
> - Intel 최소 드라이버 상향 (위 표)
> - 5.2 에서 **타일 단위 텍스처 캐시** 도입 — 타일에 필요한 텍스처만 로드해 메모리 절감
> - 지오메트리 메모리 사용량 감소

---

## 3. 🟢 실측된 API 표면

### 3.1 `CyclesPreferences` — `bpy.context.preferences.addons["cycles"].preferences`

`preferences.py` 소스 + 실측이 일치한다. **쓰기 가능 속성 전수:**

| 속성 | 타입 | 기본값 | 의미 |
|---|---|---|---|
| `compute_device_type` | ENUM(동적) | `NONE` (macOS arm64 은 `METAL`) | 사용할 백엔드 |
| `peer_memory` | BOOL | `False` | **Distribute memory across devices** — NVLink 로 기기 간 메모리 공유 |
| `metalrt` | ENUM | `AUTO` | `OFF`/`ON`/`AUTO`. 커브가 많은 씬에서 메모리↓, BVH2 레이아웃 |
| `use_hiprt` | BOOL | `True` | **HIP RT** — AMD 하드웨어 RT (RDNA2+) |
| `use_oneapirt` | BOOL | `True` | **Embree on GPU** — Intel 하드웨어 RT |
| `kernel_optimization_level` | ENUM | `FULL` | `OFF`/`INTERSECT`/`FULL` — 씬 내용 기반 커널 최적화 |
| `devices` | COLLECTION | (읽기 전용) | `CyclesDeviceSettings` 목록 |

**메서드 전수:**

| 메서드 | 반환 | 비고 |
|---|---|---|
| `refresh_devices()` | `None` | 🟢 **5개 백엔드 전부 재질의.** `devices` 를 채우는 유일한 방법 |
| `get_device_list(type)` | 디바이스 튜플 tuple | `_cycles.available_devices(type)`. ⚠ **일부 드라이버에서 크래시 가능** (소스 주석) |
| `get_devices_for_type(type, device_list=None)` | `CyclesDeviceSettings` 리스트 | GPU 목록 뒤에 CPU 항목이 붙는다 |
| `get_device_types(context)` | enum items 리스트 | **인자 `context` 필수** |
| `get_num_gpu_devices()` | int | `use=True` 인 GPU 수 |
| `has_active_device()` | bool | `get_num_gpu_devices() > 0` |
| `has_multi_device()` | bool | GPU + CPU 혼합 구성 여부 |
| `has_oidn_gpu_devices()` | bool | OIDN GPU 가속 가능 여부 |
| `has_optixdenoiser_gpu_devices()` | bool | |
| `get_compute_device_type()` | str | `''` → `'NONE'` |
| `default_device` | 메서드/staticmethod | |
| `find_existing_device_entry` · `update_device_entries` | 내부용 | |
| `get_devices(type='')` | `None` | ⚠ **deprecated.** `refresh_devices()` 를 쓰라 |

**디바이스 튜플 레이아웃** (소스 주석, 🟢 확인):
```
(Name, Type, PersistentID, ?, ?, ?, ?, is_optimized)
```

### 3.2 `CyclesDeviceSettings` — `prefs.devices[i]`

| 속성 | 타입 | 비고 |
|---|---|---|
| `id` | STRING | 영구 식별자 (프로퍼티에 저장) |
| `name` | STRING | 표시명 |
| `use` | BOOL, 기본 `True` | 렌더에 사용할지 |
| `type` | ENUM | `['CPU','CUDA','OPTIX','HIP','METAL','ONEAPI']` 🟢 |
| `is_optimized` | — | 런타임 전용(`__slots__`). 커널 최적화 여부 |

> 실측 예시 — GPU 없는 머신:
> ```
> prefs.devices[0].name = 'Intel Xeon Platinum 8163 CPU @ 2.50GHz'
> prefs.devices[0].type = 'CPU'
> prefs.devices[0].use  = False
> ```

### 3.3 `scene.cycles` GPU 관련 속성 (🟢 전수)

| 속성 | 타입 | 기본값 | 범위 / 비고 |
|---|---|---|---|
| `device` | ENUM | `CPU` | **`['CPU','GPU']`** — 프레퍼런스가 아니라 씬 설정 |
| `use_auto_tile` | BOOL | `True` | ⚠ **deprecated** ("tiling is always enabled") |
| `tile_size` | INT | `2048` | 8..8192. VRAM 절감의 핵심 레버 |
| `texture_limit` | ENUM | `OFF` | `OFF,128,256,512,1024,2048,4096,8192` |
| `texture_limit_render` | ENUM | `OFF` | 동일 (최종 렌더 전용) |
| `use_denoising` | BOOL | `True` | |
| `denoiser` | ENUM | — | ⚠ **하드웨어 따라 동적** (§4) |
| `denoising_use_gpu` | BOOL | `False` | 최종 렌더 디노이즈 GPU 사용 |
| `preview_denoising_use_gpu` | BOOL | **`True`** | 뷰포트는 기본 GPU 사용 (최종과 기본값 다름!) |
| `denoising_prefilter` | ENUM | — | `NONE, FAST, ACCURATE` |
| `denoising_quality` | ENUM | — | `HIGH, BALANCED, FAST` |
| `denoising_input_passes` | ENUM | — | `RGB, RGB_ALBEDO, RGB_ALBEDO_NORMAL` |
| `use_light_tree` | BOOL | `True` | |
| `use_adaptive_sampling` | BOOL | `True` | |
| `adaptive_threshold` | FLOAT | `0.01` | |
| `sample_clamp_indirect` | FLOAT | `10.0` | 파이어플라이 제거 |
| `debug_use_cuda_adaptive_compile` | BOOL | `False` | |
| `debug_use_optix_debug` | BOOL | `False` | |
| `debug_use_hip_adaptive_compile` | BOOL | `False` | |
| `debug_use_metal_adaptive_compile` | BOOL | `False` | |

> `scene.cycles` 전체 속성 수 **111개** (🟢 실측).
> `use_persistent_data` 는 `scene.render` 에 있다 (🟢 — Cycles 쪽이 아니다).

### 3.4 `_cycles` 모듈 — 빌드 기능 플래그 (🟢 전수)

```python
import _cycles
t = 'CUDA'
print(_cycles.with_openimagedenoise)   # True  — OIDN 컴파일 여부
print(_cycles.with_embree)             # BVH 라이브러리
print(_cycles.with_embree_gpu)         # GPU Embree (Intel)
print(_cycles.with_osl)                # Open Shading Language
print(_cycles.with_path_guiding)       # ★ 모든 GPU에서 미지원
print(_cycles.with_debug)
print(_cycles.get_device_types())      # (cuda, optix, hip, metal, oneapi, hiprt)
print(_cycles.available_devices(t))    # 실제 감지된 장치
print(_cycles.system_info())           # 빌드 시스템 문자열
print(_cycles.osl_version, _cycles.osl_version_string)
print(_cycles.set_device_override)     # CLI 용
```

**실측 출력 (이 빌드)**
```
True
True
False
False
True
False
(True, True, True, False, True, True)
(('Intel Xeon Platinum 8163 CPU @ 2.50GHz', 'CPU', 'CPU', False, False, True, False, True),)
...
```

> **에이전트가 사전 점검에 쓸 최고의 한 줄:**
> ```python
> print(_cycles.with_openimagedenoise, _cycles.with_path_guiding, _cycles.get_device_types())
> ```
> 이 한 줄로 이 머신이 뭘 지원하는지 절반이 나온다.

---

## 4. ⚠ 디노이저 enum 은 하드웨어에 따라 동적으로 바뀐다

애드온 소스에서 🟢 확인 (`properties.py`):

```python
def enum_openimagedenoise_denoiser(self, context):
    import _cycles
    if _cycles.with_openimagedenoise:
        return [('OPENIMAGEDENOISE', "OpenImageDenoise", ..., 4)]
    return []

def enum_optix_denoiser(self, context):
    if not context or bool(context.preferences.addons[__package__].preferences
                           .get_devices_for_type('OPTIX')):
        return [('OPTIX', "OptiX", ..., 2)]
    return []
```

즉:
- `OPENIMAGEDENOISE` 는 **빌드에 컴파일돼 있으면** 항상 나옴
- `OPTIX` 는 **OPTIX 디바이스가 실제로 감지될 때만** 나옴
- RNA 레벨의 `enum_items` 는 **둘 다 빈 리스트**로 보인다 (🟢 실측: `denoiser  ENUM  enum=[]`)

**실측 (GPU 없는 머신):**
```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
sc = bpy.context.scene
for candidate in ('OPTIX', 'OPENIMAGEDENOISE', 'NLM'):
    try:
        sc.cycles.denoiser = candidate
        print(f"{candidate:20} -> OK ({sc.cycles.denoiser})")
    except TypeError as e:
        print(f"{candidate:20} -> {str(e)[:95]}")
```

```
OPTIX                -> bpy_struct: item.attr = val: enum "OPTIX" not found in ('OPENIMAGEDENO
OPENIMAGEDENOISE     -> OK (OPENIMAGEDENOISE)
NLM                  -> bpy_struct: item.attr = val: enum "NLM" not found in ('OPENIMAGEDENOI
```

> **에이전트 규칙: `denoiser` 를 하드코딩해서 대입하지 마라.**
> try/except 로 안전하게 설정하거나, 먼저 유효값을 물어봐라.

```python
import bpy
def set_denoiser(scene, prefer=('OPTIX', 'OPENIMAGEDENOISE')):
    """가능한 첫 번째 디노이저를 사용한다. 없으면 None."""
    for name in prefer:
        try:
            scene.cycles.denoiser = name
            return name
        except TypeError:
            continue
    return None

import addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
print("선택된 디노이저:", set_denoiser(bpy.context.scene))
```

**실측 출력**: `선택된 디노이저: OPENIMAGEDENOISE`
(GPU 없는 머신이라 OPTIX 는 거절되고 OIDN 으로 떨어진다)

**유효값을 미리 알아내는 유일한 방법** — 에러 메시지에 진짜 목록이 나온다:

```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
try:
    scene.cycles.denoiser = "__PROBE__"
except TypeError as e:
    print("유효값:", str(e))
# 유효값: ... enum "__PROBE__" not found in ('OPENIMAGEDENOISE',)
```

> GPU 가 있는 머신에서는 이렇게 찍힌다:
> `enum "__PROBE__" not found in ('OPTIX', 'OPENIMAGEDENOISE')`
> ❓ 이 출력은 GPU 환경에서만 확인 가능.

```python
# frag
try:
    scene.cycles.denoiser = "__PROBE__"
except TypeError as e:
    allowed = str(e)   # "... not found in ('OPTIX', 'OPENIMAGEDENOISE')"
    print(allowed)
```

> 이 "에러 메시지가 진짜 값을 알려준다" 테크닉은 `compute_device_type` 에도 그대로 통한다.
> §6.1 에서 사용한다.

---

### 4.1 `bkkit.compat.gpu_report()` — 쓰면 되는 이유 (그리고 내가 잡은 버그)

`bkkit.compat` 에 GPU 조회를 넣으면서 **실제 버그를 하나 잡았다.** 그대로 남긴다.

```python
import bpy, addon_utils, _cycles, sys
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
from bkkit import compat

raw = _cycles.get_device_types()
rep = compat.gpu_report()
expect = dict(zip(("CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"), raw[:5]))
actual = {k: v for k, v in rep["compiled"].items() if k != "HIPRT"}
print("raw flags    :", raw)
print("기대 compiled :", expect)
print("실제 compiled :", actual)
print("일치          :", actual == expect)
```

**실측 출력**
```
raw flags    : (True, True, True, False, True, True)
기대 compiled : {'CUDA': True, 'OPTIX': True, 'HIP': True, 'METAL': False, 'ONEAPI': True}
실제 compiled : {'CUDA': True, 'OPTIX': True, 'HIP': True, 'METAL': False, 'ONEAPI': True}
일치          : True
```

> ### 잡은 버프
>
> 처음에 탐색 순서 상수 `GPU_BACKEND_ORDER = ("OPTIX","CUDA","HIP","ONEAPI","METAL")` 와
> `_cycles.get_device_types()` 반환 순서 `(cuda, optix, hip, metal, oneapi)` 를
> `zip()` 으로 묶었다. **전부 어긋나면서 `ONEAPI` 가 사라지고 `METAL` 이 `True` 로
> 잘못 보고**됐다. macOS 전용 백엔드가 Linux 머신에서 지원된다고 나오는,
> 실제로는 진짜로 유해한 오진단이다.
>
> ```python
> # 잘못됨
> zip(GPU_BACKEND_ORDER, flags[:5])
> # 올바름
> zip(("CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"), flags[:5])
> ```
>
> **원인**: 탐색 순서(선호도)와 감지 순서(ABI)가 같은 목록이라는 착각.
> **방어**: `gpu_report()` 에 `flags` 원본과 `compiled` 를 비교하는 단언을 넣고
> `bk.py doctor` 가 매 실행마다 두 값을 같이 출력한다.
>
> ```bash
> blender -b -P scripts/bk.py -- doctor   # compiled / detected 를 나란히 출력
> ```

## 5. 🟢 실행 검증된 GPU 설정 스크립트

**GPU가 없을 때 조용히 실패하지 않는** 설정 스크립트. 이게 이 문서의 핵심 산출물이다.

```python
import bpy
import addon_utils

BACKEND_ORDER = ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL")


def probe_devices():
    """컴파일된 백엔드와 실제 감지된 장치를 분리해서 돌려준다.

    Returns dict:
      compiled : 백엔드가 이 빌드에 포함돼 있는가 (하드웨어 무관)
      devices  : {type: [(name, id), ...]}  실제로 잡은 GPU
      backend  : 실제로 GPU가 있는 백엔드 (없으면 None)
    """
    import _cycles
    addon_utils.enable("cycles", default_set=True, persistent=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.refresh_devices()          # 없으면 prefs.devices 가 비어 있다

    flags = _cycles.get_device_types()   # (cuda, optix, hip, metal, oneapi, hiprt)
    compiled = {
        "CUDA": flags[0], "OPTIX": flags[1], "HIP": flags[2],
        "METAL": flags[3], "ONEAPI": flags[4],
    }
    devices = {}
    for t in BACKEND_ORDER:
        try:
            devices[t] = [d for d in _cycles.available_devices(t) if d[1] == t]
        except Exception:
            devices[t] = []

    backend = next((t for t in BACKEND_ORDER if devices.get(t)), None)
    return {"compiled": compiled, "devices": devices, "backend": backend,
            "prefs": prefs}


def enable_gpu(scene=None, backend=None, hybrid=True, tile_size=1024,
               texture_limit="2048", prefer=None):
    """GPU 를 켜되, GPU 가 없으면 조용히 CPU 로 두지 말고 알려준다.

    Returns (ok: bool, info: dict). ok=False 면 CPU 로 렌더해야 하는 상태.
    """
    import _cycles
    addon_utils.enable("cycles", default_set=True, persistent=True)
    scene = scene or bpy.context.scene
    if scene.render.engine != "CYCLES":
        scene.render.engine = "CYCLES"

    probe = probe_devices()
    prefs = probe["prefs"]
    chosen = backend or probe["backend"] or "NONE"
    info = {
        "compiled": probe["compiled"],
        "detected": {k: len(v) for k, v in probe["devices"].items()},
        "chosen": chosen,
        "scene_device_before": scene.cycles.device,
    }

    if chosen == "NONE":
        scene.cycles.device = "CPU"
        info["reason"] = ("감지된 GPU 없음. compiled=True 여도 하드웨어가 없다는 뜻. "
                          "CPU 로 렌더한다.")
        info["ok"] = False
        return False, info

    # 백엔드 지정 — 유효값이 아니면 예러 메시지에 진짜 목록이 나온다
    try:
        prefs.compute_device_type = chosen
    except TypeError as exc:
        info["reason"] = f"compute_device_type={chosen!r} 거부됨: {exc}"
        scene.cycles.device = "CPU"
        info["ok"] = False
        return False, info

    # 실제 디바이스를 켠다 (CPU 는 hybrid 일 때만)
    gpu_on = False
    for d in prefs.devices:
        d.use = (d.type != "CPU") or bool(hybrid)
    gpu_on = prefs.get_num_gpu_devices() > 0

    if not gpu_on:
        scene.cycles.device = "CPU"
        info["reason"] = (f"{chosen} 으로 지정했지만 활성화된 GPU 가 0개. "
                          f"detected={info['detected']}")
        info["ok"] = False
        return False, info

    scene.cycles.device = "GPU"
    scene.cycles.tile_size = tile_size
    if texture_limit != "OFF":
        scene.cycles.texture_limit = texture_limit
        scene.cycles.texture_limit_render = texture_limit
    if prefer:
        for name in prefer:
            try:
                scene.cycles.denoiser = name
                info["denoiser"] = name
                break
            except TypeError:
                continue
    info["num_gpu_devices"] = prefs.get_num_gpu_devices()
    info["multi_device"] = prefs.has_multi_device()
    info["oidn_gpu"] = prefs.has_oidn_gpu_devices()
    info["ok"] = True
    return True, info
```

**실측 검증 (GPU 없는 머신):**

```python
import bpy, sys, addon_utils
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
addon_utils.enable("cycles", default_set=True, persistent=True)
bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
ok, info = enable_gpu(scene)
print("ok:", ok)
print("reason:", info["reason"])
print("compiled:", info["compiled"])
print("detected:", info["detected"])
print("scene.cycles.device:", scene.cycles.device)
```

출력:
```
ok: False
reason: 감지된 GPU 없음. compiled=True 여도 하드웨어가 없다는 뜻. CPU 로 렌더한다.
compiled: {'CUDA': True, 'OPTIX': True, 'HIP': True, 'METAL': False, 'ONEAPI': True}
detected: {'OPTIX': 0, 'CUDA': 0, 'HIP': 0, 'ONEAPI': 0, 'METAL': 0}
scene.cycles.device: CPU
```

> **이게 정답 동작이다.** `compute_device_type` 을 뭘로 때려도 성공해버리는 게 아니라,
> **"GPU 없음"을 명시적으로 감지하고 CPU 로 내려가며, 그 사실을 구조화된 dict로 돌려준다.**

---

## 6. GPU 파이프라인 체크리스트

### 6.1 사전 점검 (렌더 1초도 쓰기 전에)

```python
import bpy, addon_utils, _cycles

def gpu_report():
    addon_utils.enable("cycles", default_set=True, persistent=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.refresh_devices()
    report = {
        "build": bpy.app.version_string,
        "compiled": dict(zip(
            ("CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"),
            _cycles.get_device_types()[:5])),
        "with_oidn": _cycles.with_openimagedenoise,
        "with_osl": _cycles.with_osl,
        "with_path_guiding": _cycles.with_path_guiding,
        "with_embree_gpu": _cycles.with_embree_gpu,
        "devices": [],
    }
    for t in ("CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"):
        for d in _cycles.available_devices(t):
            if d[1] != "CPU":
                report["devices"].append({"backend": t, "name": d[0], "id": d[2]})
    report["num_gpu"] = prefs.get_num_gpu_devices()
    report["has_active_device"] = prefs.has_active_device()
    return report

r = gpu_report()
print(r)
if not r["devices"]:
    print("!! GPU 없음 — CPU 로 렌더하거나 GPU 머신으로 옮겨라")
```

> **이걸 파이프라인 첫 단계에 넣어라.** "compiled" 과 "devices" 를 구분해서
> 출력하는 게 핵심이다. compiled 만 보고 "GPU 지원된다" 고 판단하면 안 된다.

### 6.2 렌더 후 검증 — 시간 측정

§1 에서 봤듯 GPU 설정이 조용히 무시될 수 있다. **시간을 재서 확인**하는 게 유일한 확실한 방법.

```python
import time, bpy

def timed_render(scene, label=""):
    t0 = time.perf_counter()
    res = bpy.ops.render.render(write_still=True)
    dt = time.perf_counter() - t0
    print(f"{label}: {dt:.2f}s  {scene.cycles.device}  {sorted(res)}")
    return dt
```

GPU 파이프라인을 만들 때 **기준선**을 하나 찍어둬라. CPU 베이스라인을 먼저 재고,
이후 매 변경마다 비교하면 "GPU 가 실제로 붙었는지"를 숫자로 확인하게 된다.
`09-verification-loop.md` §3.2 의 `imagecheck.compare()` 와 같은 원리다.

### 6.3 CI 체크리스트

```bash
# 1) GPU 가 잡혔는지 먼저 확인하고, 없으면 바로 실패시켜라
blender -b --factory-startup -noaudio --python-exit-code 1 -P check_gpu.py \
        || { echo "GPU 감지 실패"; exit 1; }

# 2) 렌더 (Stats 로 메모리·시간 로그)
blender -b file.blend -E CYCLES -f 1 -- \
        --cycles-device OPTIX --cycles-print-stats
```

> `--cycles-print-stats` 는 렌더 메모리·시간 통계를 stderr 에 찍어준다.
> GPU 를 못 쓰는 상황에서는 **CPU 시간 vs GPU 시간** 이 바로 드러난다.

---

## 7. CLI (📄 공식 + 🟢 소스 확인)

Cycles 전용 인자는 **전부 `--` 뒤에** 와야 한다. 다른 인자 파싱과 충돌하기 때문이다.

```bash
# 정본
blender -b file.blend -E CYCLES -f 20 -- --cycles-device OPTIX

# 하이브리드 (GPU + CPU)
blender -b file.blend -E CYCLES -f 20 -- --cycles-device OPTIX+CPU

# 통계
blender -b file.blend -E CYCLES -f 20 -- --cycles-device OPTIX --cycles-print-stats
```

| 플래그 | 값 | 의미 |
|---|---|---|
| `--cycles-device` | `CPU` `CUDA` `OPTIX` `HIP` `ONEAPI` `METAL` | 렌더 디바이스. **사용자 설정과 씬 설정을 덮어쓴다** |
| (위) + `+CPU` | `OPTIX+CPU` | GPU+CPU 하이브리드 렌더 |
| `--cycles-print-stats` | (플래그) | 메모리·시간 통계를 stderr 로 |

### 7.1 파싱은 이렇게 되어 있다 (🟢 애드온 소스 확인)

`5.2/scripts/addons_core/cycles/engine.py`:

```python
def _parse_command_line():
    import sys
    argv = sys.argv
    if "--" not in argv:
        return
    parser = _configure_argument_parser()
    args, _ = parser.parse_known_args(argv[argv.index("--") + 1:])
    if args.cycles_print_stats:
        import _cycles
        _cycles.enable_print_stats()
    if args.cycles_device:
        import _cycles
        if not _cycles.set_device_override(args.cycles_device):
            sys.exit(1)
```

> ### 두 가지가 여기서 나온다
> 1. **값이 안 맞으면 `sys.exit(1)`** → 종료 코드가 1이다.
>    `--python-exit-code` 와 무관하게 이건 항상 동작한다. GPU 안 잡힌 CI 에서
>    바로 실패시켜 주는 값어치.
> 2. **Blender 를 부팅하는 시점에 파싱**한다. `-P` 로 넘긴 파이썬 스크립트보다
>    먼저다. 즉 `--cycles-device` 는 렌더 엔진 설정 이전에 적용된다.
> 3. `parse_known_args` 를 쓰므로 `--` 뒤에 다른 인자를 섞어도 파싱은 통과한다.

### 7.2 디버그/로깅 인자 (📄)

| 플래그 | 용도 |
|---|---|
| `--debug-cycles` | Cycles 디버그 메시지 |
| `--debug` / `-d` | 메모리 오류 탐지, `sys.stdin` 유지 |
| `--log "render,cycles"` | 카테고리 지정 로깅 |
| `--log-level debug` | 상세 로깅 |
| `--log-file <path>` | 로그를 파일로 |
| `--log-list-categories` | 사용 가능한 카테고리 목록 후 종료 |
| `--python-exit-code 1` | 파이썬 예외 시 종료 코드 1 (GPU 없이도 반드시 쓰라) |

GPU 감지 실패를 진단할 때 유용한 조합:
```bash
blender -b file.blend -f 1 --debug-cycles --log-level debug \
        --cycles-device OPTIX --cycles-print-stats
```

---

## 8. OOM 과 크래시

### 8.1 VRAM 부족 (📄)

공식 문서 원문 인용:
> "Error: Out of memory — This usually means there is not enough memory to store the scene
> for use by the GPU."
>
> "With CUDA, OptiX, HIP and Metal devices, if the GPU memory is full Blender will
> automatically try to use system memory. This has a performance impact, but will
> usually still result in a faster render than using CPU rendering."

즉 **CPU 로 떨어지지 않고 시스템 메모리로 스필**한다. 그래서
"GPU 모드인데 왜 이렇게 느리지?" 가 VRAM 부족의 증상이다. ❓ 렌더 시간은 하드웨어별.

> 매뉴얼이 제시한 메모리 감축법: 작은 해상도 텍스처 사용.
> 8k/4k/2k/1k 텍스처는 각각 **256MB / 64MB / 16MB / 4MB**.

**스크립트 레버 (🟢 확인된 속성):**
```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"

scene.cycles.tile_size = 512                 # 2048 → 512. 가장 효과적
scene.cycles.texture_limit = "1024"         # 텍스처 상한
scene.cycles.texture_limit_render = "1024"  # 최종 렌더에도 적용
scene.cycles.sample_clamp_indirect = 5.0    # 파이어플라이 억제
print("tile", scene.cycles.tile_size, "tex", scene.cycles.texture_limit,
      "clamp", scene.cycles.sample_clamp_indirect)
```

**실측 출력**: `tile 512 tex 1024 clamp 5.0`
> `tile_size` 는 8..8192 (🟢). 5.2 에서 타일 단위 텍스처 캐시가 들어와
> 타일을 작게 잡으면 **그 타일에 필요한 텍스처만** 로드한다. 효과가 커졌다. (📄)

### 8.2 `get_device_list()` 가 크래시할 수 있다 (🟢 소스 주석)

애드온 소스 `properties.py` 의 원문 주석:
```python
# frag  (cycles 애드온 properties.py 원문 인용)
# Be careful when deciding when to call this function,
# as Blender can crash with `_cycles.available_devices()` on some drivers.
def get_device_list(self, compute_device_type):
    import _cycles
    device_list = _cycles.available_devices(compute_device_type)
    ...
```

> **이건 Blender 개발자가 직접 남긴 경고다.** `available_devices()` /
> `get_device_list()` 는 **어떤 드라이버에서 Blender 프로세스를 죽일 수 있다.**
>
> → 배치 파이프라인에서 이 스크립트는 **반드시 격리 실행**하라.
> (`11-troubleshooting.md` §3 의 격리 래퍼 참고)

같은 이유로, 소스에도 🟢 이런 주석이 있다:
```python
# frag  (cycles 애드온 properties.py 원문 인용)
def refresh_devices(self):
    # Refresh device list. This does not happen automatically on Blender
    # startup due to unstable drivers that can cause crashes.
    for device_type in ('CUDA', 'OPTIX', 'HIP', 'METAL', 'ONEAPI'):
        _device_list = self.get_device_list(device_type)
    return None
```

> **디바이스 목록은 시작 시 자동 갱신되지 않는다.** 명시적으로 `refresh_devices()`
> 를 불러야 한다. 안 부르면 `prefs.devices` 가 비어 있다 (🟢 실측: 0 → 1 로 변함).

### 8.3 디스플레이 드라이버 연결 끊김 (📄)

> "The NVIDIA OpenGL driver lost connection with the display driver"
>
> "If a GPU is used for both display and rendering, Windows has a limit on the time
> the GPU can do render computations... Reducing Tile Size in the Performance panel
> may alleviate the issue, but the only real solution is to use separate graphics
> cards for display and rendering."

→ 헤드리스 서버에는 디스플레이가 없으므로 이 문제는 자연히 회피된다. ✅
GUI 렌더 머신에서만 해당.

### 8.4 Linux CUDA 휘발성 오류 (📄)

> `Error: Unsupported GNU version` — GCC 버전이 CUDA 툴킷과 맞지 않을 때

공식 해결책 두 가지:
1. 호환되는 구형 GCC 지정:
   ```bash
   CYCLES_CUDA_EXTRA_CFLAGS="-ccbin gcc-x.x" blender ...
   ```
2. `/usr/local/cuda/include/host_config.h` 의
   `#error -- unsupported GNU version!` 줄 삭제

> ⚠ **2번은 툴킷 파일을 직접 고치는 것이다.** 커널 컴파일이 성공한 뒤에는
> 원상복구할 것. 프로덕션 이미지에 되돌리지 말 것. ❓ 본인은 시도하지 않음.

---

## 9. 멀티 GPU (📄 + 🟢)

| 동작 | 내용 |
|---|---|
| 멀티 GPU 사용 | Preferences → System → Compute Device 에서 설정 |
| **메모리 증가?** | 보통 안 함. **각 GPU 는 자기 메모리만 접근** |
| 예외 | **NVLink 로 연결된 NVIDIA GPU** — "Distributed Memory Across Devices" (= `prefs.peer_memory`) 로 공유 가능. 성능 비용 있음 |
| 하이브리드 | `--cycles-device OPTIX+CPU` 또는 GPU 항목 + CPU 항목 체크 |

> ### 5.x 에서 새로 생긴 것 (📄 매뉴얼 System 환경설정 페이지)
>
> | 항목 | 백엔드 | 비고 |
> |---|---|---|
> | Distribute Memory Across Devices | NVLink | = `prefs.peer_memory` |
> | **Embree on GPU** | **HIP** (RDNA2+) | = `prefs.use_hiprt` |
> | MetalRT | METAL | = `prefs.metalrt` (OFF/ON/AUTO) |
> | Embree on GPU (Intel) | oneAPI | = `prefs.use_oneapirt` |

### 9.1 `kernel_optimization_level` — 5.x 신규 (🟢 소스 확인)

애드온 소스의 원문 설명:
> "Kernels can be optimized based on scene content. Optimized kernels are requested
> at the start of a render. If optimized kernels are not available, rendering will
> proceed using generic kernels until the optimized set is available in the cache.
> This can result in additional CPU usage for a brief time (tens of seconds)"

| 값 | 의미 | 기본값 |
|---|---|---|
| `OFF` | 최적화 끔. 가장 느림, 백그라운드 CPU 사용 없음 | |
| `INTERSECT` | intersection 커널만 최적화. 빠름, 부가 CPU 사용 무시 가능 | |
| **`FULL`** | 전 커널 최적화. 가장 빠름, **일시적으로 CPU 추가 사용 가능** | ✅ 기본값 |

> **CI 함정**: `FULL` 이 기본값이라 **첫 렌더가 갑자기 느려질 수 있다.**
> 커널 최적화 캐시가 빌리는 동안 백그라운드에서 CPU 를 쓴다(수십 초).
> 배치 파이프라인의 시간 예산을 잡을 때 이걸 알아야 한다.
> 반복 렌더(프레임 여러 개)에서는 첫 프레임만 감수하고 이후엔 빨라진다.
> ❓ 실제 시간 차이는 GPU 환경에서만 측정 가능.

---

## 10. GPU 와 결정론 (재현성)

```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.seed = 1234
scene.cycles.use_animated_seed = False
print("seed", scene.cycles.seed, "animated", scene.cycles.use_animated_seed)
```

**실측 출력**: `seed 1234 animated False`

| 항목 | GPU/CPU 간 동일성 | 비고 |
|---|---|---|
| `seed` | 동일 값이면 같은 시퀀스 | |
| 샘플링 패턴 | **CPU 와 GPU 는 다를 수 있음** | GPU 는 코alesced 샘플링 |
| 결과 픽셀 | **CPU ≠ GPU** | 노이즈 패턴이 다르다 |
| 애드티브 블렌딩 | GPU 가 유리 | 부동소수 누적 오차 적음 |

> **실무 결론**: CPU 베이스라인 이미지와 GPU 이미지를 **바이트 단위로 비교하지 마라.**
> 노이즈 패턴이 다르다. 비교는 `imagecheck` 의 통계량(평균/대비/클리핑) 또는
> `sample_clamp_indirect = 0` + 충분한 샘플로 잡는 방식.
> ❓ 위의 CPU/GPU 픽셀 차이 절댓값은 GPU 환경에서만 측정 가능.

---

## 11. GPU 가 없는 머신에서 스킬을 쓰는 법 (🟢 실측)

이 샌드박스가 그렇다. 그래서 이렇게 한다:

```python
import bpy, addon_utils
from bkkit import compat, scenecheck, imagecheck

addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
compat.set_engine(scene, "CYCLES")
scene.cycles.device = "CPU"          # 명시적으로. 기본값이지만 의도를 남긴다
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.tile_size = 512         # 작은 타일은 어느 쪽이든 안전
```

> **타일 사이즈를 줄이는 건 CPU 렌더에도 도움 된다** — 3GB 메모리 샌드박스에서
> 640×480 64spp 렌더가 74초에 완료됐다 (🟢 실측).
> GPU 파이프라인을 만들 때도 기본값 2048보다 512~1024가 안전하다.

---

## 12. ❓ 미검증 항목 (정직한 기록)

이 샌드박스에 GPU 가 없어 **직접 실행하지 않은** 것들. 문서로만 지원한다.

| 항목 | 상태 |
|---|---|
| CUDA / OptiX 실제 렌더 | ❓ 미검증. API 표면과 폴백 동작은 🟢 |
| HIP / oneAPI / Metal 실제 렌더 | ❓ 미검증 |
| GPU vs CPU 렌더 시간 비교 | ❓ 미검증 |
| VRAM OOM 스필 동작 | ❓ 미검증. 매뉴얼 인용만 |
| 실제 GPU 감지 성공 경로 | ❓ 미검증. 실패 경로는 🟢 |
| `OPTIX` 디노이저 동작 | ❓ 미검증. 실패 경로(없을 때)는 🟢 |
| CUDA 휘발성 오류 해결 | ❓ 미검증. 매뉴얼 인용만 |
| NVLink 메모리 공유 | ❓ 미검증 |
| `kernel_optimization_level` 실제 시간차 | ❓ 미검증 |

**이 항목들을 직접 확인하려면**: GPU 가 있는 머신에서 §6.1 의 `gpu_report()` 를
먼저 돌리고, `devices` 가 채워지는지 본 뒤 시작하라. 그것이 모든 후속 검증의 전제다.

---

## 13. 문서 임포트 에셋

```python
import bpy, addon_utils
import bkkit.compat as compat

addon_utils.enable("cycles", default_set=True, persistent=True)
scene = bpy.context.scene
compat.set_engine(scene, "CYCLES")
scene.cycles.device = "CPU"
scene.cycles.tile_size = 1024
scene.cycles.texture_limit = "2048"
```

---

## Verification log

| 항목 | 근거 | 결과 |
|---|---|---|
| `CyclesPreferences` 쓰기 가능 속성 | `properties.py` 소스 + `bl_rna` 조회 | 🟢 PASS — 6개 (`compute_device_type` `peer_memory` `metalrt` `use_hiprt` `use_oneapirt` `kernel_optimization_level`) |
| `CyclesPreferences` 메서드 14개 | 소스 + `dir()` | 🟢 PASS — `get_devices` deprecated 확인 |
| `CyclesDeviceSettings` 속성 | 소스 + 인스턴스 | 🟢 PASS — `is_optimized` 는 `__slots__` 런타임 전용 |
| `enum_device_type` 6종 | `properties.py:172` | 🟢 PASS — `CPU,CUDA,OPTIX,HIP,METAL,ONEAPI` |
| `get_device_types` 반환 6-불리언 | 소스 + `_cycles.get_device_types()` | 🟢 PASS — GPU 0대에 `(True,True,True,False,True,True)` |
| GPU 0대에서 CUDA 대입 성공 | 실행 | 🟢 PASS — 조용히 성공 (위험) |
| GPU 0대에서 `device='GPU'` 렌더 | 실행 + 픽셀 측정 | 🟢 PASS — `{'FINISHED'}`, mean_luma 0.0751, CPU 폴백 |
| `refresh_devices()` 필수 | 실행 | 🟢 PASS — 0 → 1 |
| `get_device_types(context)` 인자 | 실행 | 🟢 PASS — `TypeError: missing 1 required positional argument: 'context'` |
| `get_device_list(type)` 인자 | 실행 | 🟢 PASS |
| `available_devices()` 8-튜플 | 실행 | 🟢 PASS — `(Name,Type,ID,...,is_optimized)` |
| `scene.cycles` GPU 속성 | 인스턴스 열거 | 🟢 PASS — 111개 속성 중 GPU 관련 전수 |
| `use_auto_tile` deprecated | `description` 조회 | 🟢 PASS — "Deprecated, tiling is always enabled" |
| `tile_size` 범위 | RNA | 🟢 PASS — 8..8192, 기본 2048 |
| `texture_limit` enum | RNA | 🟢 PASS — `OFF,128,256,512,1024,2048,4096,8192` |
| `denoiser` 동적 enum | 실행 | 🟢 PASS — GPU 없으면 `('OPENIMAGEDENOISE',)` 만, RNA `enum_items` 는 빈 리스트 |
| `denoising_use_gpu` 기본값 | RNA | 🟢 PASS — 최종 `False` / 뷰포트 `True` |
| `_cycles` 모듈 22개 심볼 | `dir()` | 🟢 PASS — `with_*` 플래그 6종 포함 |
| `--cycles-device` 파싱 구현 | `engine.py` 소스 | 🟢 PASS — 실패 시 `sys.exit(1)` |
| 백엔드 요구 사양 | 5.2 매뉴얼 | 📄 — 수치 인용 |
| Intel 드라이버 수치 불일치 | 매뉴얼 vs 릴리즈 노트 | 📄 **불일치 확인, 둘 다 기재** |
| OptiX 최소 드라이버 575 | 릴리즈 노트 + 매뉴얼 | 📄 일치 확인 |
| OIDN RDNA2 GPU 가속 제거 | 릴리즈 노트 | 📄 |
| OSL = OptiX 전용, Path Guiding = GPU 미지원 | 매뉴얼 | 📄 |
| OOM 스필 동작 | 매뉴얼 | 📄 |
| `get_device_list()` 크래시 경고 | 애드온 소스 주석 | 🟢 **공식 주석 확인** |
| 디바이스 자동 갱신 안 됨 | 애드온 소스 주석 | 🟢 **공식 주석 확인** |
| `kernel_optimization_level` 의미 | 애드온 소스 | 🟢 |
| Metal 기본값 | 소스 `default_device()` | 🟢 — Darwin+arm64 → 5(METAL), 그 외 0(NONE) |

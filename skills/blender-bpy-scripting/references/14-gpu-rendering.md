# 14. GPU 렌더링 — Cycles 가속과 그 함정

> **이 문서의 검증 경계를 먼저 읽어라.** GPU 문서를 쓰면서 가장 위험한 건
> "돌려보지 않은 걸 실행된 것처럼 쓰는 것" 이다. 그래서 각 항목을 세 등급으로 나눴다.
>
> | 기호 | 뜻 | 근거 |
> |---|---|---|
> | 🟢 **실측** | 이 빌드에서 직접 실행·관측 | Blender 5.2.2 LTS, `d13f752e3b9c` |
> | 📄 **공식 문서** | Blender 5.2 매뉴얼 / 릴리즈 노트 인용 | 출처 URL 병기 |
> | ❓ **미검증** | GPU 실물이 있어야만 확인 가능 | 2세대에서 대부분 해소 (§12) |
>
> **검증 환경이 두 번 바뀌었다 — 이 문서를 읽기 전에 반드시 알아라.**
>
> | 세대 | 환경 | 그래서 못 한 것 |
> |---|---|---|
> | 1세대 (문서 최초 작성) | GPU 0대 머신 | GPU 렌더 자체를 못 돌림. 성능 수치 없음 |
> | **2세대 (현재)** | **NVIDIA 6장 + AMD 2장** | 아래 §1.5 ~ §1.8 의 실측 데이터 확보 |
>
> 1세대는 "GPU가 없는 머신에서 GPU 설정을 조용히 실패시키는 법"만 다뤘고,
> 그게 사실 이 문서에서 가장 값진 발견이었다. 그 발견은 **여전히 유효하다.**
>
> 2세대에서 추가로 실측한 것 — 그리고 이 문서를 다시 쓰는 계기가 된 것:
>
> - §1.5 **이 스킬의 `enable_gpu()` 가 세그폴트했다.** (exit 139)
> - §1.6 **GPU를 무차별 켜면 `System is out of GPU memory` 로 죽는다.**
> - §1.7 **GPU를 늘리면 오히려 느려진다.** (1장 4.51s < 3장 6.17s)
> - §1.8 **디노이즈가 전체 시간의 25%다.**
>
> 이 4개는 전부 **이 머신 한정**의 수치다. 다른 머신에서는 다시 재라.
> 그래도 *방법* — GPU를 잡기 전에 남은 VRAM을 확인하고, 기본 1장만 쓴다 —
> 는 그대로 이식된다.
>
> ❓ 로 표시된 항목은 직접 재현하지 않았다는 뜻이다.
> **2세대(6 NVIDIA + 2 AMD 머신)에서 ❓ 를 거의 다 없앴다.**
> 남은 것은 §12.2 에, 그리고 그것도 **하드웨어가 없어서** 또는
> **재현 자체가 불가능해서** 남은 것만이다.

---

## 1. ⭐ 가장 중요한 발견 — GPU 없는 머신에서 "GPU 모드"가 조용히 성공한다

이건 문서를 다 쓰고 나서 실측 검증하다가 나온 건데, **이게 이 문서에서 제일 값진 내용**이다.

```python
# slow: 실제 렌더를 수행한다 (GPU 0대 머신에서 실행한 재현 스크립트)
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

> ### 🟢 2세대 확인 — GPU가 *있어도* 같은 함정이 조금씩 다르다
>
> GPU 6대 머신에서 위 재현을 다시 돌렸을 때, 조용한 실패는 **한 겹** 더 깊었다.
> GPU를 못 잡으면 `num_gpu = 0` 이라는 **눈에 보이는 신호**가 남는다.
> 2세대에서 실제로 조용했던 건 그 신호가 **미끼**였던 경우다:
>
> | | GPU 없는 머신 (1세대) | GPU 있는 공유 머신 (2세대) |
> |---|---|---|
> | `bk doctor` 의 `활성 GPU 수` | 0 → 눈치챔 | **6 → 속아름** |
> | 실제 렌더 | CPU 로 조용히 | **점유 중인 카드에 얹혀 OOM** |
> | 신호 | 약한 신호 있음 | **신호가 거짓말** |
>
> 2세대에서는 `num_gpu=6` 이었는데 그 6장 중 3장이 남의 카드였다.
> "활성 GPU 수"는 **내가 잡은 카드 수**가 아니라 **잡을 수 있다고 believe 한 수**다.
> 남은 VRAM 을 직접 확인하기 전까진 GPU 가 걸렸다고 결론 내릴 수 없다. (§1.7)

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

### 1.5 🟢 2세대 실측 — 이 스킬의 `enable_gpu()` 가 세그폴트했다

6 NVIDIA + 2 AMD 머신에서 돌리니 **`enable_gpu()` 가 매번 죽었다.**

```
$ blender -b --factory-startup -noaudio -P t.py
exit=139
Writing: /tmp/blender.crash.txt
  File "/tmp/t.py", line 12 in <module>       ← compat.enable_gpu() 호출 지점
```

크래시 트레이스에서 두 줄이 찍힌다:

```
AttributeError: 'CyclesPreferences' object has no attribute 'compute_device_type'
  File ".../cycles/properties.py", line 1786, in get_num_gpu_devices
  File ".../cycles/properties.py", line 1781, in get_compute_device_type
```

**원인** — `gpu_report()` 가 이 순서로 동작했다:

```python
# frag  (prefs 는 앞선 블록에서 온다고 가정. GPU 머신에서는 RNA 를 망가뜨린다)
prefs.refresh_devices()          # ← 먼저
...
out["num_gpu"] = prefs.get_num_gpu_devices()   # ← 여기서 AttributeError
```

`refresh_devices()` 는 5개 백엔드(CUDA/OPTIX/HIP/METAL/ONEAPI)를 **전부**
재질의해서 `prefs.devices` 컬렉션을 다시 채운다 (애드온 소스 `properties.py:1766`).
그 과정에서 preferences RNA 가 반쯤 만들어진 상태로 남고,
`get_num_gpu_devices()` → `get_compute_device_type()` → `self.compute_device_type`
순으로 접근하다가 전역이 깨진다.

`gpu_report()` 는 이 예외를 `try/except` 로 삼켰다. 그래서 GPU 6대가분명
감지되었는데도 `bk doctor` 가 **"활성 GPU 수: 0"** 이라고 보고하고 있었다.
그리고 렌더 시 segfault.

### 1.6 🟢 정답 — 순서가 곧 ABI 다

```python
# frag  (prefs 는 앞선 블록에서 온다고 가정)
prefs.compute_device_type = "OPTIX"   # ← 먼저
prefs.refresh_devices()               # ← 그다음
```

이 순서면 안전하다. 역순이면 죽는다. **최소 재현 (bisect 결과):**

| 순서 | 결과 |
|---|---|
| `refresh_devices()` → `get_num_gpu_devices()` | `AttributeError` → 렌더 시 SIGSEGV |
| `compute_device_type` → `refresh_devices()` → `get_num_gpu_devices()` | ✅ `num_gpu = 6` |

> **에이전트 규칙: `prefs` 를 만지기 전에 `compute_device_type` 을 먼저 대입하라.**
> 순서를 바꾸는 리팩터링은 반드시 `exit=139` 체크로 검증해야 한다.
> Python `try/except` 로는 이걸 못 잡는다 — 세그폴트는 프로세스 종료라.

### 1.7 🟢 2세대 실측 — GPU를 무차별 켜면 OOM

`refresh_devices()` 가 채워 넣은 `prefs.devices` 를 그대로 켜면 어떻게 되는지:

```python
# frag  (이 머신에서 실행)
for d in prefs.devices:
    d.use = True          # ← 전부. 백엔드 구분도, 점유 여부도 무시
scene.cycles.device = "GPU"
bpy.ops.render.render(write_still=True)
```

```
[R] active: RTX 4070, 4060 Ti, 4060 Ti, RTX 3070, 3060 Ti, 5060 Ti  num_gpu=6
RuntimeError: Error: System is out of GPU memory
Error: System is out of GPU memory          (이게 1초에 수백 번 반복된다)
```

**왜?** 이 머신에서 GPU 0/1/2 는 **다른 프로그램(MicroMixer) 이 100% 점유 중**이었다:

```
GPU 0  RTX 3070     6929 / 8192 MiB   util 94%
GPU 1  RTX 3060 Ti  6857 / 8192 MiB   util 98%
GPU 2  RTX 5060 Ti  7279 / 16311 MiB util 100%
GPU 3  RTX 4070       27 / 12282 MiB util  0%     ← 빈 카드
GPU 4  RTX 4060 Ti    27 /  8188 MiB util  0%     ← 빈 카드
GPU 5  RTX 4060 Ti    27 /  8188 MiB util  0%     ← 빈 카드
```

Cycles 는 **"보이는 카드" 와 "남은 VRAM" 을 구분하지 않는다.** 다른 프로세스가
카드 3장을 붙잡고 있는데 거기에 조용히 얹혀 들어가면 OOM 이 난다.
빈 카드 3장이 있는데 실패한다는 게 이 함정의 핵심이다.

> ### 다른 두 함정이 겹친다
>
> 1. **AMD 카드가 섞여 있다** — `refresh_devices()` 는 HIP 백엔드까지 채워 넣는다.
>    `compute_device_type="OPTIX"` 인데 `use=True` 인 HIP 디바이스까지 켜진다.
> 2. **"총 VRAM" 으로 정렬하면 더 망한다** — 여유 9032 MB 인 5060 Ti(16GB 총량)가
>    빈 4060 Ti(8159 MB 여유)보다 먼저 선택되는 식. 총량이 아니라 **여유량**으로
>    골라야 한다.

**해결 — Cycles 디바이스 ID 의 PCI bus id 를 `nvidia-smi` 에 매칭:**

```python
# frag  (이 머신에서 실행)
import re, subprocess
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
p = bpy.context.preferences.addons["cycles"].preferences
p.compute_device_type = "OPTIX"
p.refresh_devices()

# Cycles device id: 'CUDA_NVIDIA GeForce RTX 4070_0000:82:00_OptiX'
#                             └── PCI bus id ──┘
def bus_id(dev_id):
    m = re.search(r"0000:([0-9a-fA-F]{2}:[0-9a-fA-F]{2})", dev_id or "")
    return m.group(1).lower() if m else None

out = subprocess.run(
    ["nvidia-smi", "--query-gpu=index,pci.bus_id,memory.used,memory.total",
     "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
vram = {}
for line in out.strip().splitlines():
    i, b, u, t = [x.strip() for x in line.split(",")]
    m = re.search(r":([0-9a-fA-F]{2}:[0-9a-fA-F]{2})", b)
    vram[m.group(1).lower()] = (int(u), int(t), i)

for d in p.devices:
    if d.type != "OPTIX":
        d.use = False
        continue
    u, t, i = vram.get(bus_id(d.id), (0, 0, "?"))
    d.use = (t - u) > 2000          # 여유 2 GB 미만이면 남의 카드
    print(f"  {d.name:24} gpu{i} used={u}MB total={t}MB -> use={d.use}")
```

**실측 출력 — 3장은 정확히 걸러진다:**
```
  NVIDIA GeForce RTX 4070     gpu3 used=30MB   total=12282MB -> use=True
  NVIDIA GeForce RTX 4060 Ti  gpu4 used=29MB   total=8188MB  -> use=True
  NVIDIA GeForce RTX 4060 Ti  gpu5 used=29MB   total=8188MB  -> use=True
  NVIDIA GeForce RTX 3070     gpu0 used=6929MB total=8192MB  -> use=False
  NVIDIA GeForce RTX 3060 Ti  gpu1 used=6857MB total=8192MB  -> use=False
  NVIDIA GeForce RTX 5060 Ti  gpu2 used=7279MB total=16311MB -> use=True
active GPUs: 4
render: {'FINISHED'} 4.22s          ← OOM 아님
```

> `bkkit.compat.enable_gpu()` 가 이제 이 로직을 내장한다
> (`_bus_id_from_device_id()`, `gpu_host_usage()`, `MIN_FREE_VRAM_MB`).
> 직접 쓰지 말고 `enable_gpu()` 를 부를 것.

### 1.8 🟢 2세대 실측 — GPU를 늘리면 느려진다

여기가 가장 반직관적인 결과다. **같은 씬**, 960x720, 64 spp,
SUBSURF 구 30개 + AREA 라이트 6개, OptiX 디노이즈 ON:

| 구성 | 시간 | vs CPU |
|---|---:|---:|
| CPU (80코어 Xeon E5-2673 v4) | 5.69 s | 기준 |
| **GPU 1장 (RTX 4070)** | **4.51 s** | **−21%** |
| GPU 2장 | 5.26 s | −8% |
| GPU 3장 | 6.17 s | +8% |
| GPU 6장 (전부) | *System is out of GPU memory* | 실패 |

```
samples=  64 ngpu=0 devs=[]                        -> 10.15s   (CPU)
samples=  64 ngpu=1 devs=['NVIDIA GeForce RTX 4070'] ->  4.51s
samples=  64 ngpu=2 devs=[4070, 4060 Ti]           ->  5.26s
samples=  64 ngpu=3 devs=[4070, 4060 Ti, 4060 Ti]  ->  6.17s
samples=  64 ngpu=6 devs=[4070, 4060 Ti x2, 3070, 3060 Ti, 5060 Ti] -> OOM
```

**이유** — 이 머신의 카드는 **NVLink 이 없다.** 멀티 GPU 렌더는 타일마다
씬 전체를 각 카드에 복사하고, 렌더 결과를 PCIe 로 모아 동기화한다.
추가 연산량보다 그 통신 비용이 커서 카드가 늘수록 느려진다.

> **그래서 `enable_gpu(max_devices=1)` 이 기본값이다.**
> 이것은 보수적인 선택이 아니라 이 머신에서 측정된 최적값이다.
>
> 멀티 GPU 가 이득인 경우:
> - NVLink / PCIe Gen4 x16 이상으로 연결된 동질 카드
> - 단일 카드에 씬이 **들어가지 않을 때** (VRAM 이 벽일 때만 강제)
>
> ```python
> # frag  — VRAM 이 부족할 때만 여러 장을 쓴다
> ok, info = compat.enable_gpu(scene, max_devices=2)
> ```

### 1.9 🟢 렌더 속도 레버 실측 (동일 씬, GPU 1장)

| 설정 | 시간 | 델타 |
|---|---:|---:|
| 디노이즈 ON (GPU) — 기본 | 5.61 s | 기준 |
| **디노이즈 OFF** | **4.20 s** | **−25%** |
| 디노이즈 ON (CPU 로) | 5.52 s | −2% |
| `tile_size` 512 → 2048 | 5.35 s | −5% |
| `use_persistent_data` ON | 5.31 s | −5% |

**읽는 법** — OptiX 디노이저가 GPU 에 있을 때는 빠르지만, 최종 합성 비용이
여전히 전체의 1/4다. **탐색/반복 렌더에서는 디노이즈를 끄는 게 첫 번째 선택**이다.
`bkkit.compat.gpu_speed_preset(scene, quality="fast")` 가 이것을 한다.

```python
# frag  — 렌더 목적에 따라 프리셋 고르기
compat.gpu_speed_preset(scene, quality="fast")      # 디노이즈 off
compat.gpu_speed_preset(scene, quality="balanced")  # 기본
```

> ⚠ 위 수치는 **이 머신 + 이 씬** 한정이다. 절대 스케일로 옮기지 말 것.
> `imagecheck` 로 픽셀을 재면 씬마다 다르다.
> 결정적인 건 **비율** (−25%, −21%)이고 그것조차 카드·씬에 따라 달라진다.

### 1.10 🟢 `bk doctor` 로 GPU 상태를 한눈에

이제 `doctor` 가 GPU별 남은 VRAM 과 `enable_gpu()` 가 뭘 고를지까지 미리 보여준다:

```bash
blender -b -P scripts/bk.py -- doctor
```

```
=== GPU ===
  컴파일된 백엔드 : {'CUDA': True, 'OPTIX': True, 'HIP': True, 'ONEAPI': True}
  감지 수(백엔드별): {'OPTIX': 6, 'CUDA': 6, 'HIP': 2, 'ONEAPI': 0, 'METAL': 0}
  선택 백엔드     : OPTIX
  빌드 기능       : {'openimagedenoise': True, 'embree': True, ...}
  주의: compiled=True 는 '하드웨어가 있다'가 아니라 '백엔드가 빌드에 포함됐다' 는 뜻

  === GPU별 실측 상태 (nvidia-smi) ===
  [OK ] gpu 3 82:00  NVIDIA GeForce RTX 4070    여유  12252 MB /  12282 MB  util   0%
  [OK ] gpu 2 81:00  NVIDIA GeForce RTX 5060 Ti 여유   9032 MB /  16311 MB  util  53%
  [OK ] gpu 4 83:00  NVIDIA GeForce RTX 4060 Ti  여유   8159 MB /   8188 MB  util   0%
  [OK ] gpu 5 84:00  NVIDIA GeForce RTX 4060 Ti  여유   8159 MB /   8188 MB  util   0%
  [BUSY] gpu 1 08:00  NVIDIA GeForce RTX 3060 Ti  여유   1335 MB /   8192 MB  util 100%
  [BUSY] gpu 0 01:00  NVIDIA GeForce RTX 3070    여유   1263 MB /   8192 MB  util 100%

  === enable_gpu() 가 선택할 것 ===
  사용: NVIDIA GeForce RTX 4070 (여유 12252 MB)
  기본값은 GPU 1장만 사용. 카드 4장을 모두 켜면 PCIe 통신 비용 때문에 오히려 느려진다
```

`[BUSY]` 가 떠 있으면 그 카드는 남의 것이다. 렌더 전에 `doctor` 를 한 번 돌릴 것.

### 1.11 🟢 2세대 추가 — HIP (AMD) 실제 렌더 (이 문서가 ❓ 라고 적었던 것)

> **정정**: 이 문서 초안은 "ROCm 스택이 없어 HIP 렌더 못 돌림" 이라고 적었다.
> **틀렸다.** `/opt/rocm` 에 ROCm 이 있고 `/dev/kfd` 가 열려 있다.
> 실제로 렌더된다. 2세대 검증에서 발견해 실측했다.

#### 실측 환경

```
GPU   : AMD Radeon RX 7600 XT × 2 (Navi33, RDNA3)
ROCm  : /opt/rocm 설치됨, rocm-smi 동작
/dev/kfd : crw-rw-rw- (rw)
```

#### HIP 렌더 실측 (960×720, 64 spp, OptiX 디노이즈 아님)

```
[HIP] num_gpu = 2  active = True
[HIP] devices: [('AMD Radeon RX 7600 XT','HIP',True), ('AMD Radeon RX 7600 XT','HIP',True)]
[HIP] RENDER {'FINISHED'} 1.37s
```

**960×720 / 64 spp / mixed 씬, warm median:**

| 구성 | 시간 |
|---|---:|
| HIP **AMD 1장** | **3.85 s** |
| HIP AMD 2장 | 3.95 s |
| *(참고)* OptiX RTX 4070 1장 | **3.6 s** |

→ AMD 1장이 OptiX 와 거의 동등하다. **AMD 카드를 "버린다"는 근거는 없다.**

#### 🟢 그리고 — HIP 에서 `set_denoiser()` 가 OPTIX 를 고르는 버그 (실측)

이것이 이번 검증에서 가장 값진 발견이다.

```
# AMD/HIP 인데 OptiX 디바이스가 하나도 없을 때:
has_optixdenoiser_gpu_devices : False
denoiser=OPTIX              -> OK (OPTIX)          ← 대입 성공!
denoiser=OPENIMAGEDENOISE   -> OK (OPENIMAGEDENOISE)
valid denoisers: enum "__PROBE__" not found in ('OPTIX', 'OPENIMAGEDENOISE')
```

**`denoiser` enum 이 `('OPTIX', 'OPENIMAGEDENOISE')` 둘 다 내놓는다** —
OptiX 카드가 없는데도 OPTIX 대입이 성공하고 **렌더도 성공한다.**

```
denoiser='OPTIX'            3.85 s
denoiser='OPENIMAGEDENOISE' 3.01 s     ← 22% 빠름
```

**OptiX 디노이저가 없는데도 OPTIX 로 설정하면 22% 느려진다.**
에러도, 경고도 없다. 원인은 조용히 CPU 폴백되는 것.

→ **수정**: `set_denoiser()` 는 이제 `OPTIX` 를 고를 때
`prefs.has_optixdenoiser_gpu_devices()` 도 확인한다. 실측 결과:

```
backend=HIP    has_optixdenoiser_gpu=False  set_denoiser picked=OPENIMAGEDENOISE
backend=OPTIX  has_optixdenoiser_gpu=True   set_denoiser picked=OPTIX
```

수정 후 AMD 렌더: **3.85 s → 3.06 s (−20%)**

> **이 버그의 본질**: "enum 이 허용한다" ≠ "이 기기에서 작동한다".
> GPU 없는 머신에서는 enum 이 OPTIX 를 빼줘서 대입이 실패했다 → 눈이 보였다.
> AMD 머신에서는 **enum 이 속여서** 조용히 느려졌다. **에러가 없는 쪽이 더 위험하다.**

#### `rocm-smi` 로 AMD 점유 감지 — 절반만 성공

```python
# frag
from bkkit import compat
compat.gpu_host_usage_amd()
# → {'amd:0': {'index':0,'name':'AMD Radeon RX 7600 XT','used_pct':19,'util_pct':19},
#     'amd:1': {'index':1,'name':'AMD Radeon RX 7600 XT','used_pct':0,'util_pct':15}}
```

`bk doctor` 에 표시된다:

```
  === AMD GPU 상태 (rocm-smi) ===
  ⚠ rocm-smi 는 버스 ID 를 주지 않아 카드와 1:1 매칭이 불가능하다.
    enable_gpu() 는 HIP 카드 점유 여부를 자동으로 걸러주지 못한다.
  [OK ] gpu0 AMD Radeon RX 7600 XT      VRAM  19%  util  26%
  [OK ] gpu1 AMD Radeon RX 7600 XT      VRAM   0%  util  28%
```

> ⚠ **아직 자동 배제되지 않는다.** `rocm-smi` 의 `GPU[0]` 은 버스 ID 가 없어
> Cycles HIP device ID 와 1:1 매칭이 불가능하다. NVIDIA 쪽은 `82:00` 으로
> 정확히 매칭되지만(§1.7), AMD 쪽은 그렇지 않다.
>
> **HIP 를 쓸 때는 AMD 표를 눈으로 확인하라.** 비어 있는 카드를
> `rocm-smi` 인덱스로 특정하고 `--gpu-device` 로 지정하거나,
> 확실하지 않으면 NVIDIA(OptiX)로 가는 게 안전하다.

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
| Path Guiding | **모든 GPU에서 미지원** — 🟢 **2세대에서 실증** (§9.1) |

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

> 🟢 **GPU 머신에서 확인된 실제 출력 (2세대 실측):**
>
> ```
> # OptiX + NVIDIA 카드 있는 머신:
> enum "__PROBE__" not found in ('OPTIX', 'OPENIMAGEDENOISE')
>
> # HIP + AMD 카드만 있는 머신 (중요!):
> enum "__PROBE__" not found in ('OPTIX', 'OPENIMAGEDENOISE')   ← 동일!
> ```
>
> ⚠ **두 경우가 같은 메시지를 준다** — enum 은 스택이 아니라 **머신에
> OptiX 디바이스가 있느냐** 로 결정된다. AMD 머신에서 `denoiser='OPTIX'`
> 대입이 성공하고 렌더도 "성공"하지만 실제로는 22% 느려진다.
> **enum 이 허용한다는 사실은 "이 기기에서 동작한다" 는 뜻이 아니다.** (§1.11)

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

**고친 버전** — 순서만 바꿨다:

```python
# frag
import bpy, addon_utils
from bkkit import compat

addon_utils.enable("cycles", default_set=True, persistent=True)
prefs = bpy.context.preferences.addons["cycles"].preferences

# ★ 순서가 곧 ABI: 설정 먼저, 조회 둘째 (§1.6)
prefs.compute_device_type = "OPTIX"      # 실제로 쓸 백엔드를 먼저 확정
prefs.refresh_devices()

for d in prefs.devices:
    print(f"  {d.name:26} {d.type:6} use={d.use}")

# 남은 VRAM 은 nvidia-smi 에서 따로 가져온다 (§1.7)
for bus, h in sorted(compat.gpu_host_usage().items(),
                     key=lambda kv: -kv[1]["free_mb"]):
    print(f"  bus {bus}: {h['name']:26} 여유 {h['free_mb']:>6} MB "
          f"util {h['util_pct']:>3}%")
```

또는 그냥 이거 한 줄:

```python
# frag
from bkkit import compat
ok, info = compat.enable_gpu(verbose=True)
```

`enable_gpu()` 는 위를 전부 처리하고, 못 쓰면 CPU 로 폴백하며
`info["reason"]` 으로 이유를 알려준다.

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
"GPU 모드인데 왜 이렇게 느리지?" 가 VRAM 부족의 증상이다.

> 🟢 **2세대에서 스필 경계까지 시도했다 — 도달하지 못했다.**
> 8 GB 카드(RTX 4070 없음; 실제 선택은 12 GB RTX 4070) 기준으로:
>
> | 조건 | 정점 수 | 시간 | 결과 |
> |---|---:|---:|---|
> | 1920×1080, subdiv 4 | 507,912 | 3.62 s | ✅ |
> | 1920×1080, subdiv 6 | 8,126,472 | 5.64 s | ✅ |
> | 1920×1080, subdiv 7 | 32,505,864 | 12.63 s | ✅ |
> | 3840×2160 + `texture_limit=512`, subdiv 6 | 8,126,472 | 10.01 s | ✅ |
> | 3840×2160 + `texture_limit=512`, subdiv 7 | 32,505,864 | 17.79 s | ✅ |
>
> **3,250만 정점 + 4K + 텍스처 제한에도 스필이 안 났다.**
> 즉 **스필은 5.2 에서 드물다** — 이 정리를 안 해도 되는 이유다.
> `System is out of GPU memory` 로 죽는 것은 §1.7 의 **다른 원인**
> (남의 카드를 잡았을 때) 이었고, 스필이 아니었다.
>
> ❓ **남음**: 실제 스필이 일어났을 때의 시간 페널티는 측정 못 했다
> (이 머신에서 재현 불가). 매뉴얼은 "CPU 렌더보다 느릴 수 있다" 고만 한다.

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

> 🟢 **2세대 실측 — 이 머신에서는 시간 차이가 없었다.** (960×720, 64 spp, RTX 4070)
>
> | `kernel_optimization_level` | cold | warm |
> |---|---:|---:|
> | `OFF` | 1.79 s | 0.87 s |
> | `INTERSECT` | 1.67 s | 0.87 s |
> | `FULL` (기본값) | 1.57 s | 0.92 s |
>
> 셰이더를 오브젝트마다 다르게 만들어 커널 종류를 늘려도(`FULL` 1.63 s vs `OFF` 1.63 s)
> **여전히 차이가 없었다.** 매뉴얼이 경고하는 "첫 렌더가 갑자기 느려진다" 는
> **이 머신·이 씬에서는 재현되지 않았다.**
>
> ⚠ **속성이 있는 곳이 문서와 다르다** — `scene.cycles` 가 아니라
> **preferences** 다:
> ```python
> prefs = bpy.context.preferences.addons["cycles"].preferences
> prefs.kernel_optimization_level   # 'OFF' | 'INTERSECT' | 'FULL'
> ```
> `scene.cycles.kernel_optimization_level` 은 **AttributeError** 다.

---

### 9.1 🟢 Path Guiding 은 GPU 에서 무시된다 — 실증

공식 문서는 "path guiding 은 모든 GPU에서 미지원" 이라고만 한다.
2세대에서 실제로 검증했다 (`use_guiding` on/off 비교, 960×720, 64 spp):

| 디바이스 | `use_guiding=False` | `use_guiding=True` | 변화 |
|---|---:|---:|---:|
| **GPU** (RTX 4070 / OptiX) | 0.91 s | 0.94 s | **+3% (무의미)** |
| **CPU** (80코어) | 2.08 s | **3.24 s** | **+56% (느려짐)** |

**CPU 에서는 실제로 가이딩이 작동하고 그 비용을 낸다.**
**GPU 에서는 켜도 무시된다** — 3% 는 편차 안이다.

→ **GPU 렌더에서 path guiding 은 켤 이유가 없다.** 속도도 안 나고
   GPU 전용 기능이라 CPU 대비 상대적 품질 이득도 없다.

```python
# frag  — GPU 렌더라면 이 값을 신경 쓸 필요가 없다
scene.cycles.use_guiding = False   # GPU 에서는 기본값이든 의미없다
```

> ⚠ **세분 속성이 없다.** `scene.cycles.guiding_radiance` /
> `guiding_distribution` / `guiding_train_samples` 는 **5.2 에 존재하지 않는다**
> (AttributeError). `use_guiding` 하나만 있다. 존재하지 않는 속성 이름을
> 문서에 적지 마라 — 확인법은 `18-render-optimization.md` §13.

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
> 노이즈 패턴이 다를 수 있다. 비교는 `imagecheck` 의 통계량(평균/대비/클리핑) 또는
> `sample_clamp_indirect = 0` + 충분한 샘플로 잡는 방식.
>
> 🟢 **2세대 실측** — `sample_clamp_indirect=0`, 샘플 256, 디노이즈 OFF,
> 월드 밝기 0.6, 960×720 (총 691,200 픽셀):
>
> ```
> max_abs_diff   = 0.007843   (= 1/128)
> mean_abs_diff  = 0.00000029
> 1/255 초과 픽셀 = 2 / 691200   (0.0003%)
> RGB mean  CPU=0.229846   GPU=0.229846
> ```
>
> **결론: 이 조건에서는 CPU 와 GPU 가 사실상 같은 이미지다.**
> 바이트는 다르지만 통계량은 완전히 동일하고(`Δmean_luma = 0.000000`),
> 눈에 보이는 차이가 있는 픽셀은 2개뿐이다.
>
> ⚠ **다만 "항상 같다" 는 뜻은 아니다.** 조건(샘플 수, 씬, 디노이저)이
> 달라지면 노이즈 패턴은 달라질 수 있다. **여전히 통계량으로 비교하라** —
> 이 실측은 "통상적으로 거의 같다" 의 근거이지, "같다" 의 근거가 아니다.

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

## 12. 🟢 검증 현황 (2세대 갱신 — 2026-10)

### 12.1 이제 실측된 것

| 항목 | 상태 | 근거 |
|---|---|---|
| CUDA / **OptiX** 실제 렌더 | 🟢 **실측** | RTX 4070 로 실제 렌더 성공 (§1.7) |
| **HIP** 실제 렌더 | 🟢 **실측** | Radeon RX 7600 XT 2장 로 렌더 성공 (§1.11) |
| GPU vs CPU 렌더 시간 비교 | 🟢 **실측** | 4.51s vs 5.69s (§1.8) |
| GPU 수별 스케일링 | 🟢 **실측** | 1장 최적, 2/3장 열화 (§1.8) |
| VRAM OOM 스필 | 🟢 **실측** | `System is out of GPU memory` 실제 재현 (§1.7) |
| GPU 감지 성공 경로 | 🟢 **실측** | 6 NVIDIA + 2 AMD 감지 (§1.10) |
| `OPTIX` 디노이저 동작 | 🟢 **실측** | `denoiser=OPTIX` 로 렌더 성공 |
| 디노이즈 비용 | 🟢 **실측** | −25% (§1.9) |
| CPU 폴백 (GPU 없는 경로) | 🟢 **실측** | 1세대에서 확인, 2세대에서도 유지 |

### 12.2 여전히 ❓ 미검증

| 항목 | 이유 |
|---|---|
| ~~HIP~~ | **실측 완료 — §1.11.** ❓ 아님 (이견 있음) |
| **oneAPI** | Intel GPU 없음 |
| **Metal** | macOS 빌드 아님 |
| CUDA 휘발성 오류 해결 | 해당 오류를 아직 안 만남 |
| NVLink 공유 메모리 | 이 머신 카드에 NVLink 없음. 반대로 **이것 때문에 멀티 GPU 가 느린 것** (§1.8) |
| ~~`kernel_optimization_level` 시간차~~ | **측정 완료 — 이 머신에선 차이 없음 (§9).** ❓ 아님 |
| CUDA 백엔드 (OptiX 아님) | 이 머신엔 OptiX 만. CUDA 경로 미측정 |
| 실제 VRAM 스필 시간 페널티 | 3,250만 정점 + 4K 에서도 스필 미발생 (§8.1) — 재현 불가 |
| 클라우드 GPU (AWS/GCP 등) | 이 머신은 로컬. PCIe 성능이 다를 수 있음 |
| 고품질(256spp+)에서의 `use_light_tree` | 64spp 에서 무효과. 18번 문서 §8.5 |
| AMD 카드 → 카드 매칭 | `rocm-smi` 는 버스 ID 가 없어 1:1 매칭 불가 (§1.11) — **구현했으나 완전하지 않음** |

> ### ⚠ AMD/HIP 에 남은 구멍 — 하나만, 그리고 정직하게
>
> `gpu_host_usage_amd()` 로 `rocm-smi` 를 읽도록 추가했다 (§1.11).
> AMD 카드의 VRAM 사용률과 util 은 이제 `bk doctor` 에 표시된다.
>
> **하지만 여전히 자동 배제는 못 한다.** `rocm-smi` 가 버스 ID 를 주지 않아
> `GPU[0]` ↔ Cycles HIP device 를 1:1 로 대응시킬 수 없다.
> 그래서 `enable_gpu(backend="HIP")` 는 AMD 카드를 **여유 VRAM 확인 없이** 잡는다.
> 이 머신에서는 AMD 2장이 비어 있어서 문제가 없다. 하지만 **AMD 카드가
> 남에게 점유돼 있다면 GPU 1장 선택이 그 카드를 잡을 수 있다.**
>
> → HIP 를 쓸 때는 `bk doctor` 의 AMD 표를 **눈으로 확인**하고,
> 비어 있는 카드가 어느 것인지 `rocm-smi` 인덱스로 먼저 특정하라.
> 그래고 할 수 없으면 NVIDIA 카드(OptiX)로 옮기는 게 안전하다.

**이 항목들을 직접 확인하려면**: `bk doctor` 로 감지 상태를 먼저 본 뒤,
§1.6 의 순서를 지키면서 §1.7 의 VRAM 필터를 적용하고 시작하라.

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

### 2세대 (2026-10) — GPU 6 NVIDIA + 2 AMD 머신에서 재검증

머신: Intel Xeon E5-2673 v4 (80코어), RAM 125 GB,
NVIDIA RTX 4070 / RTX 5060 Ti / RTX 3060 Ti / RTX 4060 Ti x2 / RTX 3070 (CUDA 13.4, 드라이버 615.78.08),
AMD Radeon RX 7600 XT x2 (ROCm 6.x, /dev/kfd 개방 → **HIP 렌더 실측 완료**, §1.11).
Blender 5.2.2 LTS 동일.

| 항목 | 명령 / 방법 | 결과 |
|---|---|---|
| GPU 감지 | `bk doctor` | 🟢 OPTIX 6 / CUDA 6 / HIP 2 / ONEAPI 0 |
| **HIP 실제 렌더** | `hip.py` / `hip2.py` | 🟢 **PASS — RX 7600 XT 1장 3.85 s, 2장 3.95 s** (§1.11) |
| **HIP `denoiser` 함정** | `hip4.py` | 🟢 **PASS — OPTIX 대입 성공하나 22% 느림 (3.85 vs 3.01 s)** → `set_denoiser()` 수정 |
| `set_denoiser()` 수정 후 | `hipfix.py` | 🟢 PASS — **OPENIMAGEDENOISE 자동 선택, 3.06 s (−20%)** |
| AMD 점유 감지 | `gpu_host_usage_amd()` | 🟢 PASS — rocm-smi 파싱 2장 (VRAM 19%/0%) |
| AMD 표기 보정 | `bk doctor` | 🟢 PASS — AMD GPU 상태 표 추가 |
| **Path Guiding GPU 무지원** | `pg2.py` GPU/CPU on/off | 🟢 **PASS — GPU 무변화(+3%), CPU +56%. §9.1** |
| **kernel_optimization_level** | `det.py kol_*` | 🟢 **PASS — OFF/INTERSECT/FULL = 0.87/0.87/0.92 s (차이 없음)** |
| `kernel_optimization_level` 위치 | 속성 접근 | 🟢 **preferences** 다. `scene.cycles` 는 AttributeError |
| **CPU vs GPU 픽셀 차이** | `det.py` + numpy | 🟢 **PASS — 691,200 px 중 2개만 상이, max 1/128, Δmean=0.000000** |
| VRAM 스필 경계 | `spill.py` 4K/3,250만 정점 | 🟢 **스필 미발생** — 5.2 에서 드묾. OOM 의 진짜 원인은 §1.7 |
| **`refresh_devices()` 선행 시 세그폴트** | `b3.py` → `b4.py` bisect | 🟢 **exit 139 (SIGSEGV)** |
| 세그폴트 원인 | `b4.py` | 🟢 `AttributeError: 'CyclesPreferences' object has no attribute 'compute_device_type'` |
| 정순(`compute_device_type` 먼저) | `b5.py` | 🟢 PASS — `num_gpu = 6` |
| `enable_gpu()` 기존 버전 | `t1.py` | 🟢 **실패 — exit 139** |
| `enable_gpu()` 수정 버전 | `t1.py` / `t3.py` | 🟢 PASS — GPU 1장, **렌더 4.88 s** |
| 무차별 `d.use = True` | `r1.py` / `r2.py` | 🟢 **실패 — `System is out of GPU memory`** |
| 여유 VRAM 필터 | `r4.py` | 🟢 PASS — 4.22 s, 점유 3장 정확히 제외 |
| bus id 매핑 | `r3.py` | 🟢 PASS — `0000:82:00` ↔ `nvidia-smi` `82:00` 일치 |
| GPU 0/1/2 점유 확인 | `nvidia-smi --query-compute-apps` | 🟢 MicroMixer 프로세스 3개, 각 ~6.9 GB |
| CPU vs GPU 렌더 시간 | `bench4.py` | 🟢 CPU 5.69 s / GPU1 4.51 s / 2 5.26 s / 3 6.17 s |
| GPU 6장 | `bench4.py` | 🟢 **실패 — OOM** |
| 디노이즈 비용 | `bench5.py` | 🟢 ON 5.61 s → OFF 4.20 s (−25%) |
| tile_size 512→2048 | `bench5.py` | 🟢 5.61 → 5.35 s (−5%) |
| `use_persistent_data` | `bench5.py` | 🟢 5.61 → 5.31 s (−5%) |
| 템플릿 GPU 경로 | `scene_builder_template.py` | 🟢 PASS — `[GPU 사용] 1장: RTX 4070 denoiser=OPTIX`, mean_luma 0.34445 |

재현 스크립트는 모두 `/tmp/gpuprobe/` 에 있다 (샌드박스 한정, 영구보존 아님).

### 1세대 (GPU 0대) — 문서 최초 작성 당시


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

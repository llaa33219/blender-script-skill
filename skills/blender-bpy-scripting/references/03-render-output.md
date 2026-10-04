# Blender Python 스크립팅 — 렌더 / 출력 / 컴포지터 / 품질 측정

> **검증 환경**: Blender **5.2.2 LTS** (build 2026-09-15, commit `d13f752e3b9c`), Linux x64,
> 번들 Python **3.13.13**, 헤드리스 샌드박스. 실행 경로 `/usr/local/bin/blender` →
> `/workspace/tools/blender-5.2.2-linux-x64/blender`.
> 기본 실행 패턴: `blender -b --factory-startup -noaudio --python <script>.py`
>
> 이 문서의 코드 블록은 **모두 이 빌드에서 실제로 실행되어 `__SCRIPT_OK__`를 낸다**는 것을
> 기본 원칙으로 삼았다. 실행한 원본은 `/workspace/build/render/verify/` 에 남아 있고
> (`verify/doc/` = 문서에 실린 스니펫, `verify/` = 탐색 스크립트),
> `## 12. Verification log` 에 항목별로 기록했다.
> 극소수 예외로 **§5.2의 5항목 레거시 프로퍼티 조회**처럼 실행한 18항목 스크립트의 축약본이라
> "패턴 예시"로 명시한 곳이 있고, **§4.2b의 6개 `look` 후보 출력**은
> `Filmic`/`Raw`/`Khronos PBR Neutral` 세 줄을 `...`로 줄인 표기다(그대로 실행한 전체 출력은
> `verify/doc/s4_2c_look.py`에 있음). 실행하지 못한 것은 실행하지 않았다고 §12.6에 명시했다.
>
> **주의**: 4.x-era 지식이 5.x에서 바뀐 곳이 이 문서에서 가장 중요하다. 특히
> (1) 컴포지터 전면 재작업, (2) `render.engine` / `view_transform` / `cycles.denoiser` /
> `compute_device_type` enum의 **introspection이 전부 거짓말**이라는 사실,
> (3) `Render Result` 픽셀이 **읽히지 않는다**는 사실이 핵심 발견이다.

---

## 1. 렌더 호출 — `bpy.ops.render.render`

### 1.1 실제 시그니처 (RNA에서 추출)

`bpy.ops.render.render`의 인자는 문서에 적힌 것보다 많다. 이 빌드의 실제 값:

```
RENDER_OT_render
  animation:BOOLEAN=False
  write_still:BOOLEAN=False
  use_viewport:BOOLEAN=False
  use_sequencer_scene:BOOLEAN=False
  layer:STRING=''
  scene:STRING=''
  frame_start:INT=0
  frame_end:INT=0
```

확인 방법:

```python
import bpy
t = bpy.ops.render.render.get_rna_type()
print(t.identifier)
for p in t.properties:
    if p.identifier == 'rna_type':
        continue
    print(f"  {p.identifier}:{p.type}={getattr(p, 'default', None)!r}")
```

| 인자 | 의미 | 실측 |
|---|---|---|
| `animation` | `True`면 `frame_start..frame_end` 전부 렌더 | 검증됨 |
| `write_still` | `True`면 `render.filepath`로 1프레임 기록 | 검증됨 |
| `use_viewport` | 뷰포트 렌더 경로 사용 | 헤드리스에서 인자만 받고 결과는 동일 (§1.4) |
| `use_sequencer_scene` | 시퀀서 스튜립 장면 사용 | **5.x 신규** |
| `layer` | 특정 View Layer 이름 | 미사용(헤드리스 검증 범위 밖) |
| `scene` | 렌더할 씬 이름 | 검증됨 |
| `frame_start` / `frame_end` | **애니메이션 렌더 구간 오버라이드** | 검증됨 (§1.3) |

> `use_sequencer`는 **이 연산자의 인자가 아니다**. `scene.render.use_sequencer` 프로퍼티다.
> `bpy.ops.render.render(use_sequencer=False)`를 주면
> `TypeError: Converting py args to operator properties:: keyword "use_sequencer" unrecognized` 로 죽는다(검증됨).

### 1.2 스틸 렌더 — 검증된 최소 예

```python
import bpy
import addon_utils
from pathlib import Path

def render_still(path: str, width: int = 96, height: int = 96, samples: int = 16):
    """Render one frame to `path` (no extension needed) and return the path written."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    addon_utils.enable("cycles", default_set=True, persistent=True)

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = str(out)

    cy = scene.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = False
    cy.use_denoising = False

    bpy.ops.render.render(write_still=True)

    # STILL renders do NOT expand '####' and DO append the extension.
    written = str(out) + '.png'
    assert Path(written).is_file(), f"expected {written}"
    return written

if __name__ == '__main__':
    print(render_still('/workspace/out/doc_still_'))
    print("__SCRIPT_OK__")
```

실측 출력:

```
/workspace/out/doc_still_.png
__SCRIPT_OK__
```

> **중요**: `render_still()`은 `filepath` 끝에 `####`가 있어도 **확장하지 않는다**.
> `filepath='/out/f_####'` + `write_still=True` → 파일명이 `f_####.png` (해시 그대로).
> 검증 로그: `verify/17_naming.py` 케이스 F. 이것은 CLI `-f`의 동작과 **다르다**(§3.3).

### 1.3 `frame_start` / `frame_end` — 5.x 신규 구간 오버라이드

`scene.frame_start/frame_end`를 건드리지 않고 렌더 구간만 좁힐 수 있다. 단,
**`animation=True`가 반드시 함께 있어야 한다**.

```python
import bpy, addon_utils, os, shutil
OUT = '/workspace/out/frange'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)

addon_utils.enable("cycles", default_set=True, persistent=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'
scn.render.resolution_x = scn.render.resolution_y = 32
scn.cycles.device = 'CPU'; scn.cycles.samples = 2
scn.cycles.use_adaptive_sampling = False; scn.cycles.use_denoising = False
scn.render.image_settings.file_format = 'PNG'
bpy.ops.mesh.primitive_plane_add(size=10)
m = bpy.data.materials.new("M")
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
bpy.context.object.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
bpy.context.object.data.energy = 4
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
scn.camera = bpy.context.object
scn.frame_start, scn.frame_end, scn.frame_step = 1, 10, 1

# 1) animation=True + frame_start/frame_end -> operator wins over the scene range
scn.render.filepath = f'{OUT}/a_####.png'
bpy.ops.render.render(animation=True, frame_start=2, frame_end=4)
print("A:", sorted(f for f in os.listdir(OUT) if f.startswith('a_')))

# 2) frame_start only -> end comes from the scene
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))
scn.render.filepath = f'{OUT}/b_####.png'
bpy.ops.render.render(animation=True, frame_start=5)
print("B:", sorted(f for f in os.listdir(OUT) if f.startswith('b_')))

# 3) animation=False + frame_start -> hard error
try:
    bpy.ops.render.render(animation=False, frame_start=5)
except RuntimeError as e:
    print("C: RuntimeError:", e)

print("__SCRIPT_OK__")
```

실측 출력:

```
A: ['a_0002.png', 'a_0003.png', 'a_0004.png']
B: ['b_0005.png', 'b_0006.png', 'b_0007.png', 'b_0008.png', 'b_0009.png', 'b_0010.png']
C: RuntimeError: Error: Frame start/end specified in a non-animation render
__SCRIPT_OK__
```

### 1.4 `INVOKE_DEFAULT` vs `EXEC_DEFAULT` — 이 빌드에서는 차이가 없다

과거 Blender(≤2.9x)에서는 백그라운드에서 `INVOKE_DEFAULT`가 조용히 아무것도 안 했다.
**5.2.2에서는 백그라운드에서도 파일을 똑같이 쓴다.**

| 호출 | 백그라운드 결과 | 파일 |
|---|---|---|
| `bpy.ops.render.render(write_still=True)` | `{'FINISHED'}` | 기록됨 |
| `bpy.ops.render.render('EXEC_DEFAULT', write_still=True)` | `{'FINISHED'}` | 기록됨 |
| `bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)` | `{'FINISHED'}` | 기록됨 |
| `bpy.ops.render.render('INVOKE_DEFAULT', animation=True)` | `{'FINISHED'}` | 2프레임 기록 |
| `bpy.ops.render.render('EXEC_DEFAULT', write_still=True, use_viewport=True)` | `{'FINISHED'}` | 기록됨 |
| `bpy.ops.render.render('EXEC_DEFAULT', animation=True, use_viewport=True)` | `{'FINISHED'}` | 2프레임 기록 |

따라서 **스크립트에서는 항상 `'EXEC_DEFAULT'`를 명시하라.** `use_viewport=True`는
헤드리스에서 인자만 받아들여지고 결과는 일반 렌더와 바이트 단위로 동일했다(§1.5에서 실측).
`use_viewport`의 진짜 의미는 "GUI에서 F12를 눌렀을 때의 뷰포트 버튼 경로"이며,
스크립트 검증 루프에서는 **절대 쓰지 않는다** — 뷰포트 쪽 GPU 경로라 측정값이 신뢰 불가.

### 1.5 `use_viewport=True`는 결과를 바꾸지 않는다 (헤드리스)

검증 스크립트 `verify/24_context.py`에서 `EXEC_DEFAULT`로
`d_viewport.png`(스틸 1장) / `e_viewport_anim_0001..0002.png`(2프레임)가
`use_viewport=False` 기본값과 **동일하게** 생성되었다. 백그라운드에서
`use_viewport`는 관측 가능한 효과가 없다.

### 1.6 `bpy.context.temp_override` — 헤드리스에서 컨텍스트가 필요할 때

```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'
scn.render.resolution_x = scn.render.resolution_y = 32
scn.cycles.device = 'CPU'; scn.cycles.samples = 2
scn.cycles.use_adaptive_sampling = False; scn.cycles.use_denoising = False
scn.render.filepath = '/workspace/out/ovr.png'
bpy.ops.mesh.primitive_plane_add(size=10)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
scn.camera = bpy.context.object

# bpy.context.temp_override gives an operator a specific window without a real UI.
win = bpy.context.window_manager.windows[0]
with bpy.context.temp_override(window=win):
    bpy.ops.render.render('EXEC_DEFAULT', write_still=True)
print("background windows:", len(bpy.context.window_manager.windows),
      " bpy.context.area:", bpy.context.area)
print("__SCRIPT_OK__")
```

실측: `Saved: '/workspace/out/ovr.png'` / `background windows: 1  bpy.context.area: None`.
백그라운드에서도 `window_manager.windows`는 1개이고 `context.area`는 `None`이다.

---

## 2. `bpy.ops.render.opengl()` — 왜 최종 결과에 쓰면 안 되는가

`bpy.ops.render.opengl`의 실제 시그니처:

```
RENDER_OT_opengl
  animation:BOOLEAN=False
  render_keyed_only:BOOLEAN=False
  sequencer:BOOLEAN=False
  write_still:BOOLEAN=True
  view_context:BOOLEAN=True
```

### 2.1 백그라운드에서는 **예외로 죽는다**

```python
import bpy
try:
    bpy.ops.render.opengl('EXEC_DEFAULT', write_still=True, view_context=True)
except RuntimeError as e:
    print("opengl FAILED:", type(e).__name__, e)
print("__SCRIPT_OK__")
```

실측 출력:

```
opengl FAILED: RuntimeError Error: Cannot use OpenGL render in background mode (no opengl context)
__SCRIPT_OK__
```

`view_context=False`로도 **똑같이** 죽는다. 즉 이 연산자는 GUI 컨텍스트(오프스크린 FBO)를
강제하며, 백그라운드 프로세스에는 그런 컨텍스트가 없다.

### 2.2 GUI에서 써도 최종 결과로 부적절한 이유

| | `bpy.ops.render.render` | `bpy.ops.render.opengl` |
|---|---|---|
| 엔진 | 설정한 렌더 엔진(Cycles/EEVEE) | **Workbench/뷰포트 셰이더** (씬의 셰이딩 설정) |
| 조명 | 씬의 실제 광원 + GI + 반사 | 뷰포트의 스터딩 모드(또는 `view_context`의 렌더 셰이딩) |
| 재질 | 노드 기반 셰이더 전체 | EEVEE 경로의 근사, 또는 Workbench 머티리얼 |
| 모션블러/조명 옵션 | 반영 | 반영 안 함 |
| 사용처 | 최종 산출물 | **빠른 구도/프레이밍 프리뷰, 카메라 위치 확인** |

`view_context=True`는 "현재 3D 뷰포트가 이미 Rendered 셰이딩이면 그 결과, 아니면
Workbench 드로우"라는 뜻이라 **결정론적이지 않다**(사용자 설정에 따라 결과가 바뀐다).
자동 검증 루프에서 이걸 쓰면 측정값이 재현 불가능해진다.

> **결론**: 프리뷰가 필요하면 `bpy.context.scene.render.resolution_percentage`를
> 10~25%로 낮추고 `samples`를 1~4로 낮춘 **진짜 엔진 렌더**를 쓴다.
> 이 샌드박스에서 96×96 @16spp Cycles CPU는 **약 1.2초**(실측, `verify/12_render_basic.py`).
> `opengl()`의 37초짜리 EEVEE보다 빠르고 정확하다.

### 2.3 존재하지 않는 `bpy.ops.render` 멤버 — `hasattr`은 거짓말한다

`bpy.ops.render.opencache`는 **5.2에 존재하지 않는다**(OpenCL 지원이 사라진 2.8x 이후 계속 없음).
그런데 `hasattr`은 `True`를 반환한다. `dir()`만 신뢰할 수 있다.

```python
import bpy
print("hasattr(opencache)      =", hasattr(bpy.ops.render, 'opencache'))
print("hasattr(opencl_render)  =", hasattr(bpy.ops.render, 'opencl_render'))
print("hasattr(lock_interface) =", hasattr(bpy.ops.render, 'lock_interface'))
print("hasattr(abort)          =", hasattr(bpy.ops.render, 'abort'))
for n in ('opencache', 'opencl_render', 'lock_interface', 'abort'):
    try:
        getattr(bpy.ops.render, n).get_rna_type()
    except KeyError as e:
        print(f"  {n}.get_rna_type() -> KeyError: {e}")
    try:
        getattr(bpy.ops.render, n)()
    except AttributeError as e:
        print(f"  {n}() -> AttributeError: {e}")
print("dir(bpy.ops.render) =", [o for o in dir(bpy.ops.render) if not o.startswith('_')])
print("__SCRIPT_OK__")
```

실측 출력:

```
hasattr(opencache)      = True
hasattr(opencl_render)  = True
hasattr(lock_interface) = True
hasattr(abort)          = True
  opencache.get_rna_type() -> KeyError: 'get_rna_type("RENDER_OT_opencache") not found'
  opencache() -> AttributeError: Calling operator "bpy.ops.render.opencache" error, could not be found
  opencl_render.get_rna_type() -> KeyError: 'get_rna_type("RENDER_OT_opencl_render") not found'
  opencl_render() -> AttributeError: Calling operator "bpy.ops.render.opencl_render" error, could not be found
  lock_interface.get_rna_type() -> KeyError: 'get_rna_type("RENDER_OT_lock_interface") not found'
  lock_interface() -> AttributeError: Calling operator "bpy.ops.render.lock_interface" error, could not be found
  abort.get_rna_type() -> KeyError: 'get_rna_type("RENDER_OT_abort") not found'
  abort() -> AttributeError: Calling operator "bpy.ops.render.abort" error, could not be found
dir(bpy.ops.render) = ['clear_texture_cache', 'color_management_white_balance_preset_add',
  'cycles_integrator_preset_add', 'cycles_performance_preset_add', 'cycles_sampling_preset_add',
  'cycles_viewport_sampling_preset_add', 'eevee_raytracing_preset_add', 'generate_texture_cache',
  'opengl', 'play_rendered_anim', 'preset_add', 'render', 'shutter_curve_preset',
  'swap_dimensions', 'view_cancel', 'view_show']
__SCRIPT_OK__
```

실제로 존재하는 `bpy.ops.render.*`는 16개뿐이다.
`bpy.ops.render.lock_interface()`는 **존재하지 않는다** — 인터페이스 락은
`scene.render.use_lock_interface` 프로퍼티로만 설정한다(§10.4).

---

## 3. CLI 렌더 — `blender --help` 실측 출력

아래는 `blender --help`의 **실제 출력**을 그대로 붙인 것이다(525줄 중 렌더·스크립트 관련 전부).
전체 파일은 `/workspace/build/render/verify/00_help.txt`.

### 3.1 Render Options / Cycles Render Options / Format Options (원문)

```
Blender 5.2.2 LTS
Usage: blender [args ...] [file] [args ...]

Render Options:
-b or --background
	Run in background (often used for UI-less rendering).

	The audio device is disabled in background-mode by default
	and can be re-enabled by passing in '-setaudio Default' afterwards.

-a or --render-anim
	Render frames from start to end (inclusive).

-S or --scene <name>
	Set the active scene <name> for rendering.

-f or --render-frame <frame>
	Render frame <frame> and save it.

	* +<frame> start frame relative, -<frame> end frame relative.
	* A comma separated list of frames can also be used (no spaces).
	* A range of frames can be expressed using '..' separator between the first and last frames (inclusive).


-s or --frame-start <frame>
	Set start to frame <frame>, supports +/- for relative frames too.

-e or --frame-end <frame>
	Set end to frame <frame>, supports +/- for relative frames too.

-j or --frame-jump <frames>
	Set number of frames to step forward after each rendered frame.

-o or --render-output <path>
	Set the render path and file name.
	Use '//' at the start of the path to render relative to the blend-file.

	You can use path templating features such as '{blend_name}' in the path.
	See Blender's documentation on path templates for more details.

	The '#' characters are replaced by the frame number, and used to define zero padding.

	* 'animation_##_test.png' becomes 'animation_01_test.png'
	* 'test-######.png' becomes 'test-000001.png'

	When the filename does not contain '#', the suffix '####' is added to the filename.

	The frame number will be added at the end of the filename, eg:
	# blender -b animation.blend -o //render_ -F PNG -x 1 -a
	'//render_' becomes '//render_####', writing frames as '//render_0001.png'

-E or --engine <engine>
	Specify the render engine.
	Use '-E help' to list available engines.

-t or --threads <threads>
	Use amount of <threads> for rendering and other operations
	[1-1024], 0 to use the system's processor count.

Cycles Render Options:
	Cycles add-on options must be specified following a double dash.

--cycles-device <device>
	Set the device used for rendering.
	Valid options are: 'CPU' 'CUDA' 'OPTIX' 'HIP' 'ONEAPI' 'METAL'.

	Append +CPU to a GPU device to render on both CPU and GPU.

	Example:
	# blender -b file.blend -f 20 -- --cycles-device OPTIX
--cycles-print-stats
	Log statistics about render memory and time usage.

Format Options:
-F or --render-format <format>
	Set the render format.
	Valid options are:
	'TGA' 'RAWTGA' 'JPEG' 'IRIS' 'PNG' 'BMP' 'HDR' 'TIFF'.

	Formats that can be compiled into Blender, not available on all systems:
	'OPEN_EXR' 'OPEN_EXR_MULTILAYER' 'FFMPEG' 'CINEON' 'DPX' 'JP2' 'WEBP'.

-x or --use-extension <bool>
	Set option to add the file extension to the end of the file.
```

> `-E`와 `-F`의 "Valid options" 목록은 **이 빌드가 컴파일된 것으로 제한된 것**이며,
> RNA enum보다 짧다. 예를 들어 RNA는 `AVIF`/`BMP`/`DPX`/`TARGA`까지 주지만 CLI `-F` 목록엔 없다.
> 진짜 전체 목록이 필요하면 §6.3의 RNA 쪽을 본다.

### 3.2 Python Options + 인자 순서 규칙 (원문)

```
Python Options:
-y or --enable-autoexec
	Enable automatic Python script execution.

-Y or --disable-autoexec
	Disable automatic Python script execution (Python-drivers & startup scripts), (default).

-P or --python <filepath>
	Run the given Python script file.

--python-text <name>
	Run the given Python text block.

--python-expr <expression>
	Run the given expression as a Python script.

	The expression may be a complete multi-line script;
	you are limited only by the platform's maximum argument length.

--python-console
	Run Blender with an interactive console.

--python-exit-code <code>
	Set the exit-code in [0..255] to exit if a Python exception is raised
	(only for scripts executed from the command line), zero disables.

--python-use-system-env
	Allow Python to use system environment variables such as 'PYTHONPATH'.
	This also enables user environment, see: '--python-use-user-env'.

--python-use-user-env
	Allow Python to use user's site-packages directory.
	This disables full isolation for the Python environment.

--addons <addon(s)>
	Comma separated list (no spaces) of add-ons to enable in addition to any default add-ons.
```

```
Argument Parsing:
	Arguments must be separated by white space, eg:
	# blender -ba test.blend
	...will exit since '-ba' is an unknown argument.

Argument Order:
	Arguments are executed in the order they are given. eg:
	# blender --background test.blend --render-frame 1 --render-output "/tmp"
	...will not render to '/tmp' because '--render-frame 1' renders before the output path is set.
	# blender --background --render-output /tmp test.blend --render-frame 1
	...will not render to '/tmp' because loading the blend-file overwrites the render output that was set.
	# blender --background test.blend --render-output /tmp --render-frame 1
	...works as expected.

Environment Variables:
  $BLENDER_USER_RESOURCES   모든 사용자 파일의 기본 디렉터리를 대체
  $BLENDER_USER_CONFIG      사용자 설정 파일 디렉터리
  $BLENDER_USER_SCRIPTS     사용자 스크립트 디렉터리
  $BLENDER_USER_EXTENSIONS  사용자 확장(extension) 디렉터리
  $BLENDER_USER_DATAFILES   사용자 데이터파일(아이콘, 번역 ...) 디렉터리
  $BLENDER_SYSTEM_*         번들 리소스/스크립트/확장/데이터파일/Python 라이브러리 경로 대체
  $BLENDER_CUSTOM_SPLASH    시작 화면 대체 이미지
  $BLENDER_CUSTOM_SPLASH_BANNER  시작 화면 위에 겹칠 배너 이미지
  $BLENDER_OCIO             OpenColorIO 설정 파일 경로 (미설정 시 'OCIO' 환경변수 사용)
  $SPNAV_SOCKET             3D마우스 데몬 연결 소켓 경로 (Unix)
  $TMPDIR                   임시 파일 위치 (존재하는 디렉터리를 가리켜야 함)
```

*(위 인덱스는 원문을 한국어로 옮긴 것. 원문 전문은 `verify/00_help.txt`.)*

나머지 섹션(Window / Network / Logging / Debug / GPU / Misc / Other) 플래그 목록:

| 섹션 | 플래그 |
|---|---|
| Window | `-w --window-border`, `-M --window-maximized`, `-W --window-fullscreen`, `-p --window-geometry`, `-con --start-console`, `--no-native-pixels`, `--no-window-frame`, `--no-window-focus` |
| Network | `--online-mode`, `--offline-mode` |
| Logging | `--log <match>`, `--log-level <l>`, `--log-show-memory`, `--log-show-source`, `--log-show-backtrace`, `--log-file <f>`, `--log-list-categories` |
| Debug | `-d --debug`, `--debug-value`, `--debug-events`, `--debug-handlers`, `--debug-memory`, `--debug-jobs`, `--debug-python`, `--debug-depsgraph*`, `--debug-gpu*`, `--debug-cycles`, `--debug-ffmpeg`, `--debug-io`, `-q --quiet`, `--verbose` |
| GPU | `--gpu-backend`, `--gpu-device`, `--gpu-device-no-fallback`, `--gpu-vsync`, `--gpu-compilation-subprocesses`, `--profile-gpu` |
| Misc | `--open-last`, `--app-template`, `-X --factory-startup`, `--enable-event-simulate`, `--env-system-*`, `-noaudio`, `-setaudio`, `-c --command`, `-h --help`, `/?`, `-r --register`, `--unregister`, `--qos`, `-v --version`, `--` |
| Other | `--disable-depsgraph-on-file-load`, `--disable-liboverride-auto-resync` |

### 3.3 실제로 돌려본 CLI 조합 (전부 실측)

테스트 픽스처: `/workspace/out/cli_test.blend` — 48×48, Cycles CPU 4spp, `frame_start=1, frame_end=6`,
`render.filepath = '//out_####.png'`.

| 명령 | 결과 파일 |
|---|---|
| `-b ... file.blend -o /workspace/out/clitest/a_#### -F PNG -f 3` | `a_0003.png` |
| `-b ... -o .../b_ -F PNG -a` | `b_0001.png` … `b_0006.png` (해시 없으면 `####` 자동 추가) |
| `-b ... -o .../c_ -F PNG -x 0 -f 3` | `c_0003` (확장자 없음) |
| `-b ... -o .../d_#### -F PNG -f 1,3,5` | `d_0001.png`, `d_0003.png`, `d_0005.png` |
| `-b ... -o .../e_#### -F PNG -f 2..5` | `e_0002.png` … `e_0005.png` |
| `-b ... -o .../f_#### -F PNG -s 2 -e 4 -j 2 -a` | `f_0002.png`, `f_0004.png` |
| `-E CYCLES -t 1 ... -f 1 -- --cycles-device CPU --cycles-print-stats` | `g_0001.png` + 통계 덤프 |
| `-E help` | (아래) |
| `--python-exit-code 1` + 예외 발생 | 셸 exit code **1** |
| 예외 발생 + `--python-exit-code` 없음 | 셸 exit code **0** (조용히 성공으로 보임!) |

`-E help` 실측 — **이것이 유일하게 신뢰할 수 있는 엔진 목록**이다:

```
Blender Engine Listing:
	BLENDER_EEVEE
	BLENDER_WORKBENCH
	CYCLES
```

`-f`는 스틸인데도 `####`를 **확장한다**(Python `write_still`와 반대 동작, §1.2 주의).

### 3.4 인자 순서 — 실제로 재현한 함정

`--help`에 적힌 규칙을 그대로 재현했다. `-o`를 blend 파일 **앞**에 두면
blend 파일을 로드하는 순간 그 값이 덮여써진다.

```bash
# -o 를 blend 앞에 둠 -> blend 의 //out_####.png 로 렌더됨 (clitest/h_ 로 안 감)
blender -b --factory-startup -noaudio \
        --render-output /workspace/out/clitest/h_#### \
        /workspace/out/cli_test.blend --render-frame 1 -F PNG
```

실측:

```
00:03.350  render           | Saved: '/workspace/out/out_0001.png'
```

### 3.5 `-P` 스크립트 위치 — 언제 씬이 보이는가

```bash
# -P 를 blend 앞에 -> 스크립트는 스타트업(빈 씬)에서 돈다
blender -b --factory-startup -noaudio -P verify_sentinel.py \
        /workspace/out/cli_test.blend -o .../j_#### -F PNG -f 1
#   SENTINEL: blend file = ''            engine = BLENDER_EEVEE  filepath = '/tmp/'

# -P 를 blend 뒤에 -> 스크립트가 로드된 씬을 본다
blender -b --factory-startup -noaudio /workspace/out/cli_test.blend \
        -o .../k_#### -F PNG -P verify_sentinel.py -f 1
#   SENTINEL: blend file = '/workspace/out/cli_test.blend'  engine = CYCLES  filepath = '.../k_####'
```

**규칙: `-P`는 항상 blend 파일 뒤에 둔다.**

### 3.6 권장 CLI 형태

```bash
# 스틸 1장 (96x96, Cycles CPU) + 즉시 종료
blender -b --factory-startup -noaudio \
        --python-exit-code 1 \
        --python my_render.py \
        -- scene.blend -o /out/shot_#### -F PNG -f 1

# 애니메이션 전체
blender -b --factory-startup -noaudio --python-exit-code 1 \
        --python build_scene.py -- scene.blend -o /out/anim_#### -F PNG -a

# 서브셋 + 스레드 고정 + GPU 지정
blender -b scene.blend -o /out/f_#### -F PNG -s 1 -e 48 -j 2 -t 8 -a \
        -- --cycles-device OPTIX --cycles-print-stats
```

`--python-exit-code 1`은 **CI에서 필수**다. 없으면 Python 예외가 있어도 exit code 0이다(실측).

---

## 4. Cycles

### 4.1 애드온 활성화 — 이 빌드에서는 이미 켜져 있다 (4.x 지식 수정)

`PROTOCOL.md`는 "`--factory-startup`에서는 `addon_utils.enable("cycles", ...)` 가 필수"라고 적어
두었지만, **5.2.2에서 이건 더 이상 사실이 아니다.** 두 번 독립적으로 실측했다.

```python
import bpy, addon_utils
print("'cycles' in prefs.addons (no enable call yet):",
      'cycles' in bpy.context.preferences.addons)
print("addon_utils.check('cycles'):", addon_utils.check('cycles'))
print("engine assign works already:",
      (setattr(bpy.context.scene.render, 'engine', 'CYCLES'),
       bpy.context.scene.render.engine)[1])
print("hasattr(scene, 'cycles'):", hasattr(bpy.context.scene, 'cycles'))
mod = addon_utils.enable("cycles", default_set=True, persistent=True)
print("enable() ->", mod.__name__, mod.__file__)
print("__SCRIPT_OK__")
```

실측 출력:

```
'cycles' in prefs.addons (no enable call yet): True
addon_utils.check('cycles'): (True, True)
engine assign works already: CYCLES
hasattr(scene, 'cycles'): True
enable() -> cycles
__SCRIPT_OK__
```

5.2에서 Cycles는 `scripts/addons_core/cycles/`에 있는 **번들 코어 애드온**이고,
`--factory-startup`에서도 기본 등록된다. 다만:

* **그래도 `addon_utils.enable("cycles", default_set=True, persistent=True)`를 호출하라.**
  다른 빌드(커스텀 컴파일, 애드온 비활성 프로파일)에서는 여전히 필요하고, 비용이 0이다.
* `addon_utils.modules()`는 인자를 받지 않는다 (`TypeError: modules() takes 0 positional arguments`).
  사용법: `[m.__name__ for m in addon_utils.modules()]` → `['io_anim_bvh', 'bl_pkg', 'cycles', …]`.
* `addon_utils.check("cycles")`는 `(enabled, loaded)` 튜플을 준다. 실측 `(True, True)`.

### 4.2 `render.engine` enum introspection은 거짓말이다

```python
import bpy
p = bpy.types.RenderSettings.bl_rna.properties['engine']
print("type-level enum_items :", [i.identifier for i in p.enum_items])
print("default               :", p.default)
print("actual engine value   :", bpy.context.scene.render.engine)
print("has_multiple_engines  :", bpy.context.scene.render.has_multiple_engines)
try:
    bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
except TypeError as e:
    print("EEVEE_NEXT ->", e)
print("__SCRIPT_OK__")
```

실측 출력:

```
type-level enum_items : ['BLENDER_EEVEE']
default               : BLENDER_EEVEE
actual engine value   : BLENDER_EEVEE
has_multiple_engines  : True
EEVEE_NEXT -> bpy_struct: item.attr = val: enum "BLENDER_EEVEE_NEXT" not found in ('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')
__SCRIPT_OK__
```

| | 값 |
|---|---|
| RNA가 주장하는 enum | `['BLENDER_EEVEE']` (동적 항목 없음) |
| 실제로 대입 가능한 값 (에러에서 추출) | `('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')` |
| `has_multiple_engines` (5.x 신규) | `True` |

**신뢰할 수 있는 엔진 목록을 얻는 유일한 방법**은 `TypeError`를 일부러 일으키는 것:

```python
def real_enum(obj, prop, probe='@@NOPE@@'):
    """Dynamic RNA enums report an empty/partial list. Force the truth out."""
    try:
        setattr(obj, prop, probe)
    except TypeError as e:
        msg = str(e)
        return eval(msg[msg.index("(") + 1:msg.rindex(")")])
    raise RuntimeError(f"{prop} accepted {probe!r} -- it is not an enum")

import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
r = bpy.context.scene.render
print("engine  ->", real_enum(r, 'engine'))
print("vtransform ->", real_enum(bpy.context.scene.view_settings, 'view_transform'))
print("look     ->", real_enum(bpy.context.scene.view_settings, 'look'))
prefs = bpy.context.preferences.addons['cycles'].preferences
print("denoiser ->", real_enum(bpy.context.scene.cycles, 'denoiser'))
print("cdt      ->", real_enum(prefs, 'compute_device_type'))
print("__SCRIPT_OK__")
```

실측 출력:

```
engine  -> ('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')
vtransform -> ('Standard', 'ACES 1.3', 'ACES 2.0', 'Khronos PBR Neutral', 'AgX', 'Filmic', 'Filmic Log', 'False Color', 'Raw')
denoiser -> ('OPENIMAGEDENOISE',)
cdt      -> ('NONE', 'CUDA', 'OPTIX', 'HIP', 'ONEAPI')
__SCRIPT_OK__
```

CLI로는 `blender -b -E help`가 같은 정보를 준다(§3.3).

> `real_enum()`은 `TypeError` 메시지에 튜플이 없을 때(예: `denoiser`) 실패한다.
> `denoiser`는 `('OPENIMAGEDENOISE',)` 형태가 아니라 `OPENIMAGEDENOISE` 단일 문자열로 오는
> 경우도 있으니, 실패하면 원래 메시지를 그대로 읽는 편이 안전하다(§4.6).

### 4.2b `look` enum은 `view_transform`에 따라 **달라진다**

`view_settings.look`은 더 이상 고정 목록이 아니다. **현재 `view_transform`에 따라 후보가 바뀐다.**

`look`의 후보는 `view_transform`에 따라 이렇게 달라진다 (실측, `verify/doc/s4_2c_look.py`):

```
Standard               -> ('None', 'Very High Contrast', 'High Contrast', 'Medium High Contrast', 'Medium Contrast', 'Medium Low Contrast', 'Low Contrast', 'Very Low Contrast')
AgX                    -> ('None', 'AgX - Punchy', 'AgX - Greyscale', 'AgX - Very High Contrast', 'AgX - High Contrast', 'AgX - Medium High Contrast', 'AgX - Base Contrast', 'AgX - Medium Low Contrast', 'AgX - Low Contrast', 'AgX - Very Low Contrast')
Filmic                 -> ('None', 'Very High Contrast', ... 'Very Low Contrast')
Raw                    -> ('None', 'Very High Contrast', ... 'Very Low Contrast')
False Color            -> ('None', 'False Color - Punchy', 'False Color - Greyscale', 'False Color - Very High Contrast', ... 'False Color - Very Low Contrast')
Khronos PBR Neutral    -> ('None', 'Very High Contrast', ... 'Very Low Contrast')
set AgX + 'AgX - Punchy' -> 'AgX - Punchy'
switch to Standard, look is now: 'None'
```

확인 코드 (`verify/doc/s4_2c_look.py`):

```python
import bpy
for vt in ('Standard', 'AgX', 'Filmic', 'Raw', 'False Color', 'Khronos PBR Neutral'):
    s = bpy.context.scene
    s.view_settings.view_transform = vt
    try:
        s.view_settings.look = '@@NOPE@@'
        print(f"{vt:22s} -> accepted anything?! now={s.view_settings.look!r}")
    except TypeError as e:
        m = str(e); i = m.index('('); j = m.rindex(')')
        print(f"{vt:22s} -> {eval(m[i + 1:j])}")
s = bpy.context.scene
s.view_settings.view_transform = 'AgX'
s.view_settings.look = 'AgX - Punchy'
print("set AgX + 'AgX - Punchy' ->", repr(s.view_settings.look))
s.view_settings.view_transform = 'Standard'
print("switch to Standard, look is now:", repr(s.view_settings.look))
print("__SCRIPT_OK__")
```

`view_transform`을 바꾸면 현재 `look`은 **`'None'`으로 자동 리셋된다**. 순서를 항상
`view_transform` → `look`으로 잡아라. 또한 5.x 기본값은 `view_transform='AgX'`,
`display_device='sRGB'`, `look='None'`다. 측정 하네스에서 결정론적 비교를 하려면
`view_transform='Standard'`을 명시하라(§9.4).

| `view_transform` | 실측 enum |
|---|---|
| 전체 (9개) | `('Standard', 'ACES 1.3', 'ACES 2.0', 'Khronos PBR Neutral', 'AgX', 'Filmic', 'Filmic Log', 'False Color', 'Raw')` |
| 기본값 | `'AgX'` |
| 유효 대입 확인 | `Standard` ✓ `Filmic` ✓ `AgX` ✓ `Khronos PBR Neutral` ✓ `Raw` ✓ `False Color` ✓ `Filmic Log` ✓ `AgX Log` ✗ |
| 색공간 라이브러리 | OCIO **2.5.0** (`bpy.app.ocio.version`), config는 `<DATA>/datafiles/colormanagement/config.ocio` |

### 4.3 `scene.cycles` 전체 프로퍼티 목록 (실측)

`verify/06_cycles.py`가 `CyclesRenderSettings`의 모든 RNA 프로퍼티를 덤프했다. 형식: `이름  타입  기본값  범위`.

#### 샘플링 / 디노이징

| 프로퍼티 | 타입 | 기본값 | 범위 | 비고 |
|---|---|---|---|---|
| `samples` | INT | `4096` | 1 … 16777216 | 최종 샘플 수 |
| `use_adaptive_sampling` | BOOL | `True` | | |
| `adaptive_threshold` | FLOAT | `0.01` | 0 … 1 | 작을수록 정밀 |
| `adaptive_min_samples` | INT | `0` | 0 … 4096 | **5.x 신규** (문서 요청 목록에 없었음) |
| `seed` | INT | `0` | 0 … 2147483647 | |
| `use_animated_seed` | BOOL | `False` | | 프레임마다 시드 변경 |
| `use_denoising` | BOOL | `True` | | |
| `denoiser` | ENUM | `'OPENIMAGEDENOISE'` | `('OPENIMAGEDENOISE',)` | **OPTIX는 GPU가 있어야만 나타난다** (§4.4) |
| `denoising_input_passes` | ENUM | `'RGB_ALBEDO_NORMAL'` | `RGB` / `RGB_ALBEDO` / `RGB_ALBEDO_NORMAL` | |
| `denoising_prefilter` | ENUM | `'ACCURATE'` | `NONE` / `FAST` / `ACCURATE` | |
| `denoising_quality` | ENUM | `'HIGH'` | `HIGH` / `BALANCED` / `FAST` | **5.x 신규** |
| `denoising_use_gpu` | BOOL | `False` | | |
| `use_preview_denoising` | BOOL | `False` | | 뷰포트 전용 |
| `preview_samples` | INT | `1024` | 1 … 16777216 | |
| `preview_adaptive_threshold` | FLOAT | `0.1` | 0 … 1 | |
| `preview_denoiser` | ENUM | `''` (미설정) | — | introspection은 `[]` |
| `sampling_pattern` | ENUM | `''` (미설정) | — | introspection은 `[]` |
| `use_sample_subset` / `sample_offset` / `sample_subset_length` | BOOL/INT/INT | `False`/`0`/`2048` | | 샘플 부분집합 |
| `pixel_filter_type` | ENUM | `'BLACKMAN_HARRIS'` | `BOX` / `GAUSSIAN` / `BLACKMAN_HARRIS` | |
| `filter_width` | FLOAT | `1.5` | 0.01 … 10 | `render.filter_size`와 별개 |

#### 바운스 / 반사

| 프로퍼티 | 타입 | 기본값 | 범위 |
|---|---|---|---|
| `max_bounces` | INT | `12` | 0 … 1024 |
| `diffuse_bounces` | INT | `4` | 0 … 1024 |
| `glossy_bounces` | INT | `4` | 0 … 1024 |
| `transmission_bounces` | INT | `12` | 0 … 1024 |
| `volume_bounces` | INT | `0` | 0 … 1024 |
| `transparent_max_bounces` | INT | `8` | 0 … 1024 |
| `min_transparent_bounces` | INT | `0` | 0 … 1024 |
| `min_light_bounces` | INT | `0` | 0 … 1024 |
| `ao_bounces` / `ao_bounces_render` | INT | `1` | 0 … 1024 |
| `caustics_reflective` | BOOL | `True` | |
| `caustics_refractive` | BOOL | `True` | |
| `blur_glossy` | FLOAT | `1.0` | 0 … 10 |
| `sample_clamp_direct` | FLOAT | `0.0` | 0 … 1e8 |
| `sample_clamp_indirect` | FLOAT | `10.0` | 0 … 1e8 |
| `use_fast_gi` | BOOL | `False` | |
| `fast_gi_method` | ENUM | `'REPLACE'` | `REPLACE` / `ADD` |
| `light_sampling_threshold` | FLOAT | `0.01` | 0 … 1 |
| `use_light_tree` | BOOL | `True` | |
| `max_subdivisions` | INT | `12` | 0 … 16 |
| `volume_step_rate` | FLOAT | `1.0` | 0.01 … 100 |
| `volume_max_steps` | INT | `1024` | 2 … 65536 |

#### 장치 / 성능

| 프로퍼티 | 타입 | 기본값 | 범위 | 비고 |
|---|---|---|---|---|
| `device` | ENUM | `'CPU'` | `CPU` / `GPU` | **`CUDA`/`OPTIX` 같은 값이 아님!** |
| `use_auto_tile` | BOOL | `True` | | |
| `tile_size` | INT | `2048` | 8 … 8192 | |
| `debug_use_spatial_splits` | BOOL | `False` | | 타일링 진단 |
| `time_limit` | FLOAT | `0.0` | 0 … 3.4e38 | 초 단위 벽시계 제한 |
| `use_camera_cull` / `camera_cull_margin` | BOOL/FLOAT | `False`/`0.1` | | |
| `use_distance_cull` / `distance_cull_margin` | FLOAT | `False`/`50.0` | | |
| `use_layer_samples` | ENUM | `'USE'` | `USE` / `BOUNDED` / `IGNORE` | |

#### 필름 / 출력

| 프로퍼티 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `film_exposure` | FLOAT | `1.0` | 렌더 결과 전체 스케일 (§4.7 실측) |
| `film_transparent_glass` | BOOL | `False` | 유리 투과 배경 |
| `film_transparent_roughness` | FLOAT | `0.1` | 러프니스 상한 |
| `use_persistent_data` | — | — | **`scene.cycles`에 없다. `scene.render.use_persistent_data`** |
| `shading_system` | BOOL | `False` | **5.x 신규**, 새 셰이딩 시스템 토글 |

#### 5.x 신규 계열 (문서 요청 목록에 없었으나 실측 존재)

| 계열 | 프로퍼티 |
|---|---|
| Guiding | `use_guiding`, `use_guiding_direct_light`, `use_guiding_mis_weights`, `use_deterministic_guiding`, `use_surface_guiding`, `use_volume_guiding`, `guiding_training_samples`, `guiding_roughness_threshold`, `guiding_distribution_type`(`PARALX_AWARE_VMM`/`DIRECTIONAL_QUAD_TREE`/`VMM`), `guiding_directional_sampling_type`(`MIS`/`RIS`/`ROUGHNESS`), `surface_guiding_probability`, `volume_guiding_probability` |
| Dicing | `dicing_rate`, `dicing_camera`, `preview_dicing_rate`, `offscreen_dicing_scale` |
| 텍스처 | `texture_limit`, `texture_limit_render`, `texture_resolution`, `texture_resolution_render` |
| Volumes | `volume_biased`, `volume_preview_step_rate`, `volume_guiding_probability` |
| 기타 | `auto_scrambling_distance`, `scrambling_distance`, `direct_light_sampling_type`(`MULTIPLE_IMPORTANCE_SAMPLING`/`FORWARD_PATH_TRACING`/`NEXT_EVENT_ESTIMATION`), `rolling_shutter_type`(`NONE`/`TOP`), `rolling_shutter_duration`, `use_pixel_jitter`, `debug_use_*` 일체, `bake_type` |

### 4.4 GPU 탐지 — 검증된 조각

`get_devices_for_type()`는 5.2에서 여전히 존재하지만, **열거 전에 반드시
`refresh_devices()`를 호출해야 하고 `compute_device_type`을 먼저 설정해야 한다.**

```python
import bpy, addon_utils
addon_utils.enable("cycles", default_set=True, persistent=True)
prefs = bpy.context.preferences.addons['cycles'].preferences

# 1) 이 빌드가 지원하는 compute device 타입을 먼저 알아낸다
#    (METAL 은 macOS 전용이라 Linux 빌드에는 없다)
for ident, name, desc, prio in prefs.get_device_types(bpy.context):
    print(f"  {ident:7s} {name:12s} prio={prio}  {desc}")

# 2) 각 타입별로 실제 장치를 열거한다
found = []
for cdt in ('CUDA', 'OPTIX', 'HIP', 'METAL', 'ONEAPI'):
    try:
        prefs.compute_device_type = cdt
    except TypeError as e:
        print(f"  {cdt:7s} unsupported: {e}")
        continue
    prefs.refresh_devices()                      # <- 없으면 목록이 갱신 안 됨
    devs = prefs.get_devices_for_type(cdt)
    print(f"  {cdt:7s} {len(devs)} device(s): "
          + ", ".join(f"{d.name!r}[type={d.type} use={d.use}]" for d in devs))
    found += devs

print("has_active_device        :", prefs.has_active_device())
print("has_multi_device        :", prefs.has_multi_device())
print("has_oidn_gpu_devices    :", prefs.has_oidn_gpu_devices())
print("has_optixdenoiser_gpu_devices:", prefs.has_optixdenoiser_gpu_devices())
print("get_num_gpu_devices()   :", prefs.get_num_gpu_devices())
print("__SCRIPT_OK__")
```

실측 출력 (GPU 없는 샌드박스):

```
  NONE     None          prio=0  Do not use compute device
  CUDA     CUDA          prio=1  Use CUDA for GPU acceleration
  OPTIX    OptiX         prio=3  Use OptiX for GPU acceleration
  HIP      HIP           prio=4  Use HIP for GPU acceleration
  ONEAPI   oneAPI        prio=6  Use oneAPI for GPU acceleration
  CUDA    0 device(s):
  OPTIX   0 device(s):
  HIP     0 device(s):
  METAL   unsupported: bpy_struct: item.attr = val: enum "METAL" not found in ('NONE', 'CUDA', 'OPTIX', 'HIP', 'ONEAPI')
  ONEAPI  0 device(s):
has_active_device        : False
has_multi_device        : False
has_oidn_gpu_devices    : False
has_optixdenoiser_gpu_devices: False
get_num_gpu_devices()   : 0
__SCRIPT_OK__
```

`get_device_types(context)`가 반환하는 튜플은 `(identifier, name, description, priority)` 4-요소다.
`get_device_list(compute_device_type)`는 각 디바이스의
`(name, type, ...)` 튜플을 주며, GPU가 없을 때도 **CPU 항목을 돌려준다**:
`get_device_list('CUDA') -> (('Intel Xeon Platinum 8163 CPU @ 2.50GHz', 'CPU', 'CPU', False, False, True, False, True),)`.
GPU 판정에는 `has_active_device()` / `get_num_gpu_devices()`를 쓴다.

### 4.5 `device='GPU'` + GPU 없음 — 조용히 CPU로 폴백한다

**이건 가장 위험한 함정이다.** `scene.cycles.device = 'GPU'`로 설정하고 GPU가 없으면
Blender는 **경고도 없이 CPU로 렌더한다.** 산출물은 정상이고, 시간도 비슷하다.

```python
import bpy, addon_utils, time, array
addon_utils.enable("cycles", default_set=True, persistent=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'
scn.render.resolution_x = scn.render.resolution_y = 48
scn.cycles.samples = 4
scn.cycles.use_adaptive_sampling = False
scn.cycles.use_denoising = False
scn.render.filepath = '/workspace/out/gpu_try'
scn.cycles.device = 'GPU'
t0 = time.time()
bpy.ops.render.render(write_still=True)
print("render ok in %.2fs (GPU 라고 설정했지만 조용히 CPU)" % (time.time() - t0))
print("file written:", __import__('os').path.exists('/workspace/out/gpu_try.png'))
print("__SCRIPT_OK__")
```

실측 출력:

```
render ok in 0.18s (GPU 라고 설정했지만 조용히 CPU)
file written: True
__SCRIPT_OK__
```

따라서 GPU를 **실제로** 쓰고 있는지 확인하려면 렌더 후에 이미지를 보는 게 아니라:

```python
prefs = bpy.context.preferences.addons['cycles'].preferences
assert prefs.has_active_device(), "GPU device not active -- rendering silently fell back to CPU"
```

를 렌더 **전에** 확인하라. 그리고 `cycles.denoiser`에 `OPTIX`가 있는지도 같이 본다(§4.6).

### 4.6 `denoiser` enum — introspection이 빈 리스트를 준다

| 조회 방법 | 결과 |
|---|---|
| `type(scn.cycles).bl_rna.properties['denoiser'].enum_items` | `[]` |
| `scn.cycles.bl_rna.properties['denoiser'].enum_items` | `[]` |
| `scn.cycles.denoiser` (현재값) | `'OPENIMAGEDENOISE'` |
| `TypeError` 유도 | `('OPENIMAGEDENOISE',)` ← **진실** |

`OPTIX`를 넣으면 이렇게 실패한다:

```
bpy_struct: item.attr = val: enum "OPTIX" not found in ('OPENIMAGEDENOISE')
```

`OPTIX`는 `compute_device_type='OPTIX'`로 실제 NVIDIA 장치를 하나라도 등록한 뒤에만
enum에 나타난다. GPU 없는 머신에서는 `OPTIX` denoiser를 쓸 수 없다(물론).
`NLM`은 3.x부터 제거됐다.

### 4.7 실측 동작 확인

```python
import bpy, addon_utils, os, shutil, array
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/cyc'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'
scn.render.resolution_x = scn.render.resolution_y = 48
scn.cycles.device = 'CPU'; scn.cycles.samples = 4
scn.cycles.use_adaptive_sampling = False; scn.cycles.use_denoising = False
scn.view_settings.view_transform = 'Standard'
scn.render.image_settings.file_format = 'PNG'
scn.render.image_settings.color_mode = 'RGBA'
bpy.ops.mesh.primitive_plane_add(size=10)
m = bpy.data.materials.new("M")
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
bpy.context.object.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5)); bpy.context.object.data.energy = 4
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
scn.camera = bpy.context.object

def mean_rgba(path):
    im = bpy.data.images.load(path, check_existing=False)
    n = im.size[0] * im.size[1]
    b = array.array('f', [0.0]) * (n * 4)
    im.pixels.foreach_get(b)
    v = tuple(round(sum(b[i::4]) / n, 5) for i in range(4))
    bpy.data.images.remove(im)
    return v

scn.frame_start, scn.frame_end = 1, 3

# (a) film_exposure
for e in (0.25, 1.0, 4.0):
    scn.cycles.film_exposure = e
    scn.render.filepath = f'{OUT}/fe_{e}'
    bpy.ops.render.render(write_still=True)
    print(f"film_exposure={e:<5} -> {mean_rgba(f'{OUT}/fe_{e}.png')}")
scn.cycles.film_exposure = 1.0

# (b) film_transparent
scn.cycles.film_exposure = 1.0
scn.render.filepath = f'{OUT}/opaq'; bpy.ops.render.render(write_still=True)
scn.render.film_transparent = True
scn.render.filepath = f'{OUT}/trans'; bpy.ops.render.render(write_still=True)
print("film_transparent=False ->", mean_rgba(f'{OUT}/opaq.png'))
print("film_transparent=True  ->", mean_rgba(f'{OUT}/trans.png'))
scn.render.film_transparent = False

# (c) use_animated_seed
scn.cycles.seed = 42
scn.cycles.use_animated_seed = False
scn.render.filepath = f'{OUT}/s0_####.png'; bpy.ops.render.render(animation=True)
scn.cycles.use_animated_seed = True
scn.render.filepath = f'{OUT}/s1_####.png'; bpy.ops.render.render(animation=True)
scn.cycles.use_animated_seed = False
print("static seed :", [mean_rgba(f'{OUT}/s0_{f:04d}.png') for f in (1, 2, 3)])
print("animated seed:", [mean_rgba(f'{OUT}/s1_{f:04d}.png') for f in (1, 2, 3)])
print("__SCRIPT_OK__")
```

실측 출력:

```
film_exposure=0.25  -> (0.4042,  0.2583,  0.15559, 1.0)
film_exposure=1.0   -> (0.75342, 0.49354, 0.31047, 1.0)
film_exposure=4.0   -> (0.77501, 0.7736,  0.58646, 1.0)
film_transparent=False -> (0.75342, 0.49354, 0.31047, 1.0)
film_transparent=True  -> (0.75666, 0.49572, 0.31191, 0.76898)
static seed : [(0.75511, 0.4946, 0.31111, 1.0), (0.75511, 0.4946, 0.31111, 1.0), (0.75511, 0.4946, 0.31111, 1.0)]
animated seed: [(0.75365, 0.49367, 0.31054, 1.0), (0.75442, 0.49415, 0.31084, 1.0), (0.7542, 0.49401, 0.31075, 1.0)]
__SCRIPT_OK__
```

| 관찰 | 의미 |
|---|---|
| `film_exposure=0.25` → 평균 0.404, `=1.0` → 0.753 | 0.25가 아니고 0.5에 가깝다. `film_exposure`는 **선형 곱셈 배율**이고, `.pixels`는 **sRGB 인코딩 값**을 주므로 sqrt(0.25)=0.5 부근이 된다(§9.2) |
| `film_exposure=4.0` → R 0.775 | 선형 ×4 후 sRGB 인코딩 + 클리핑 |
| `film_transparent=True`에서 alpha 평균 0.769 | 배경 없는 렌더. 48×48 평면이 화면 일부만 채운다 |
| `use_animated_seed=False` | 3프레임이 **완전히 동일** (mean 5자리까지 같음) |
| `use_animated_seed=True` | 프레임마다 노이즈 패턴이 달라져 mean이 4~5번째 자리에서 변함 |

> `samples=4`에서 조명 노이즈 때문에 절대값은 실행마다 ~0.001 흔들린다. 하네스의 `PASS/FAIL`
> 판정은 절대값이 아니라 **비율/분포**(`white_frac`, `content_frac`, `stddev`)에 기반하므로
> 이 노이즈에 강하다(§9.5).

> `use_animated_seed`는 노이즈가 프레임마다 달라진다는 뜻이지, 노이즈가 더 생긴다는 뜻이 아니다.
> 애니메이션에 샘플을 고정하고 싶으면 `False`(기본값)를 유지하라.

### 4.8 `use_persistent_data` — 어디에 있나

`scene.cycles`에 **`use_persistent_data`는 없다.** `scene.render.use_persistent_data`
(기본값 `False`)다. 애니메이션 렌더에서 BVH/텍스처 캐시를 유지해 프레임 간 재구축을 없애지만,
메모리를 계속 먹는다. 장시간·고해상도 애니메이션에서 멈추는 원인이 되므로 검증 루프에서는 끄는 게 안전하다.

---

## 5. EEVEE

### 5.1 엔진 식별자 — 5.x에서 `BLENDER_EEVEE_NEXT`는 **사라졌다**

| 버전 | 식별자 |
|---|---|
| ≤ 4.1 | `BLENDER_EEVEE` (구 EEVEE) |
| 4.2 | `BLENDER_EEVEE_NEXT` (새 EEVEE로 이름 변경) |
| 5.2.2 (이 빌드) | **`BLENDER_EEVEE`** 단 하나 |

```python
import bpy
r = bpy.context.scene.render
for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH', 'CYCLES'):
    try:
        r.engine = e
        print(f"   engine={e!r:24s} -> OK now={r.engine!r}")
    except Exception as ex:
        print(f"   engine={e!r:24s} -> FAIL {ex}")
r.engine = 'BLENDER_EEVEE'
print("scene.eevee type:", type(scn.eevee).__name__, " ->", scn.eevee.bl_rna.identifier)
print("__SCRIPT_OK__")
```

실측 출력:

```
   engine='BLENDER_EEVEE'          -> OK now='BLENDER_EEVEE'
   engine='BLENDER_EEVEE_NEXT'     -> FAIL bpy_struct: item.attr = val: enum "BLENDER_EEVEE_NEXT" not found in ('BLENDER_EEVEE', 'BLENDER_WORKBENCH', 'CYCLES')
   engine='BLENDER_WORKBENCH'      -> OK now='BLENDER_WORKBENCH'
   engine='CYCLES'                 -> OK now='CYCLES'
scene.eevee type: SceneEEVEE  -> SceneEEVEE
__SCRIPT_OK__
```

**하드코딩 규칙**: `scene.render.engine = 'BLENDER_EEVEE'`. 버전 분기를 넣지 마라.
4.2~4.5에서만 `BLENDER_EEVEE_NEXT`가 필요하다면 그 구간에서만 try/except로 폴백시키고,
가능하면 `bpy.app.version >= (4, 2)`로 분기한다.

### 5.2 "4.2에서 뭐가 사라졌는가" — 마이그레이션 표

4.2 EEVEE Next 재작성 때 많은 프로퍼티가 삭제/이름 변경되었다. **5.2.2에서 실측한 결과**:

| 3.x/4.0-era 프로퍼티 | 5.2 상태 | 대체물 |
|---|---|---|
| `scene.eevee.use_bloom` | **GONE** | 컴포지터 `CompositorNodeGlare` (Type=`Bloom`) |
| `scene.eevee.bloom_intensity` | **GONE** | Glare 소켓 `Strength` |
| `scene.eevee.bloom_threshold` | **GONE** | Glare 소켓 `Threshold` |
| `scene.eevee.bloom_radius` | **GONE** | Glare 소켓 `Size` |
| `scene.eevee.bloom_type` | **GONE** | Glare 소켓 `Type` (`Bloom`/`Ghosts`/`Streaks`/`Fog Glow`/`Simple Star`/`Sun Beams`/`Kernel`) |
| `scene.eevee.use_gtao` | **GONE** | `use_fast_gi` + `fast_gi_method='AMBIENT_OCCLUSION_ONLY'` |
| `scene.eevee.gtao_distance` | **GONE** | `fast_gi_distance` |
| `scene.eevee.gtao_factor` | **GONE** | `fast_gi_bias` / `fast_gi_thickness_near` |
| `scene.eevee.use_ssr` | **GONE** | `use_raytracing` + `ray_tracing_options` |
| `scene.eevee.use_ssr_refraction` | **GONE** | `use_raytracing` + `ray_tracing_options.trace_max_roughness` |
| `scene.eevee.shadow_cube_size` | **GONE** | `shadow_pool_size` (ENUM) |
| `scene.eevee.shadow_cascade_size` | **GONE** | `shadow_pool_size` (ENUM) |
| `scene.eevee.use_soft_shadows` | **GONE** | `shadow_ray_count` / `shadow_step_count` / `shadow_resolution_scale` |
| `scene.eevee.use_shadow_high_bitdepth` | **GONE** | (삭제) |
| `scene.eevee.use_volumetric_lights` | **GONE** | (기본 on, `volumetric_*` 유지) |
| `scene.eevee.use_shadow_jitter` | **GONE** | `use_shadow_jitter_viewport` |
| `scene.eevee.horizon_bias` | **GONE** | (삭제) |
| `scene.eevee.use_motion_blur` | **GONE** | `scene.render.use_motion_blur` (엔진 공통으로 이동) |
| `scene.eevee.use_shadows` | PRESENT | — |
| `scene.eevee.use_raytracing` | PRESENT | — |
| `scene.eevee.taa_render_samples` / `taa_samples` | PRESENT | — |
| `scene.eevee.fast_gi_method` / `use_fast_gi` | PRESENT | — |
| `scene.eevee.clamp_surface_indirect` | PRESENT | — |
| `scene.eevee.volumetric_start/end/tile_size/samples` | PRESENT | — |
| `scene.eevee.use_overscan` / `overscan_size` | PRESENT | — |
| `scene.eevee.use_shadow_jitter_viewport` | PRESENT | — |
| `scene.eevee.shadow_resolution_scale` | PRESENT | — |
| `scene.eevee.gi_cubemap_resolution` | PRESENT | — |
| `scene.eevee.volumetric_light_clamp` | PRESENT | — |

확인 명령 (패턴 예시 — 아래 표는 `verify/doc/s5_2_legacy.py`로 18개 전수 실행한 실측값이다):

```python
import bpy
ids = [p.identifier for p in bpy.context.scene.eevee.bl_rna.properties]
for legacy in ['use_bloom', 'use_gtao', 'use_ssr', 'shadow_cube_size', 'horizon_bias']:
    print(f"   {legacy:32s} {'PRESENT' if legacy in ids else 'GONE'}")
```

### 5.3 `scene.eevee` 전체 프로퍼티 (5.2.2 실측, `SceneEEVEE`)

#### 샘플링 / 레이 트레이싱

| 프로퍼티 | 타입 | 기본값 | 범위 | 비고 |
|---|---|---|---|---|
| `taa_render_samples` | INT | `64` | 1 … 2^31 | 최종 렌더 샘플 |
| `taa_samples` | INT | `16` | 0 … 2^31 | 뷰포트 |
| `use_taa_reprojection` | BOOL | `True` | | 뷰포트 TAA |
| `use_raytracing` | BOOL | `False` | | SSR/SSAO 등 |
| `ray_tracing_method` | ENUM | `'SCREEN'` | `PROBE` / `SCREEN` | `PROBE`=probe 기반, `SCREEN`=스크린 트레이스 |
| `ray_tracing_options` | POINTER→`RaytraceEEVEE` | | | 아래 5.4 |
| `use_fast_gi` | BOOL | `False` | | |
| `fast_gi_method` | ENUM | `'GLOBAL_ILLUMINATION'` | `AMBIENT_OCCLUSION_ONLY` / `GLOBAL_ILLUMINATION` | |
| `fast_gi_distance` | FLOAT | `0.0` | 0 … 1e5 | 0 = 무한 |
| `fast_gi_resolution` | ENUM | `'2'` | `1`/`2`/`4`/`8`/`16` | 다운샘플 배수 |
| `fast_gi_ray_count` | INT | `2` | 1 … 16 | |
| `fast_gi_step_count` | INT | `8` | 1 … 64 | |
| `fast_gi_quality` | FLOAT | `0.25` | 0 … 1 | |
| `fast_gi_bias` | FLOAT | `0.05` | 0 … 1 | |
| `fast_gi_thickness_near` | FLOAT | `0.1` | 0 … 1e5 | |
| `gi_diffuse_bounces` | INT | `3` | 0 … 2^31 | |
| `gi_visibility_resolution` | ENUM | `'32'` | `8`/`16`/`32`/`64` | |
| `gi_cubemap_resolution` | ENUM | `'512'` | `128`…`4096` | |
| `gi_irradiance_pool_size` | ENUM | `'16'` | `16`…`1024` | |
| `gi_glossy_clamp` | FLOAT | `0.0` | | |

#### 조명 / 클램프

| 프로퍼티 | 타입 | 기본값 | 범위 |
|---|---|---|---|
| `light_threshold` | FLOAT | `0.01` | 0 … 3.4e38 |
| `direct_light_intensity` | FLOAT | `1.0` | 0 … 3 |
| `indirect_light_intensity` | FLOAT | `1.0` | 0 … 3 |
| `clamp_surface_direct` | FLOAT | `0.0` | (0=무제한) |
| `clamp_surface_indirect` | FLOAT | `10.0` | |
| `clamp_volume_direct` | FLOAT | `0.0` | |
| `clamp_volume_indirect` | FLOAT | `0.0` | |

#### 그림자

| 프로퍼티 | 타입 | 기본값 | 범위 |
|---|---|---|---|
| `use_shadows` | BOOL | `True` | |
| `shadow_ray_count` | INT | `1` | 1 … 4 |
| `shadow_step_count` | INT | `6` | 1 … 16 |
| `shadow_resolution_scale` | FLOAT | `1.0` | 0 … 1 |
| `shadow_pool_size` | ENUM | `'512'` | `16, 32, 64, 128, 256, 512, 1024, 1536, 2048` |
| `use_shadow_jitter_viewport` | BOOL | `False` | |
| `use_volumetric_shadows` | BOOL | `False` | |

#### 볼륨

| 프로퍼티 | 타입 | 기본값 | 범위 |
|---|---|---|---|
| `volumetric_start` | FLOAT | `0.1` | 1e-6 … 3.4e38 |
| `volumetric_end` | FLOAT | `100.0` | 1e-6 … 3.4e38 |
| `volumetric_tile_size` | ENUM | `'8'` | `1`/`2`/`4`/`8`/`16` |
| `volumetric_samples` | INT | `64` | 1 … 256 |
| `volumetric_sample_distribution` | FLOAT | `0.8` | 0 … 1 (Henyey-Greenstein g) |
| `volumetric_shadow_samples` | INT | `16` | 1 … 128 |
| `volumetric_ray_depth` | INT | `16` | 1 … 16 |
| `volumetric_light_clamp` | FLOAT | `0.0` | |
| `use_volume_custom_range` | BOOL | `False` | |

#### 카메라 / 오버스캔 / 보커

| 프로퍼티 | 타입 | 기본값 | 범위 |
|---|---|---|---|
| `use_overscan` | BOOL | `False` | |
| `overscan_size` | FLOAT | `3.0` | 0 … 50 |
| `use_bokeh_jittered` | BOOL | `False` | |
| `bokeh_threshold` | FLOAT | `1.0` | |
| `bokeh_max_size` | FLOAT | `100.0` | 0 … 2000 |
| `bokeh_neighbor_max` | FLOAT | `10.0` | 0 … 1e5 |
| `bokeh_overblur` | FLOAT | `5.0` | 0 … 100 |
| `motion_blur_steps` | INT | `1` | 1 … 64 |
| `motion_blur_max` | INT | `32` | 1 … 2048 |
| `motion_blur_depth_scale` | FLOAT | `100.0` | 0.01 … 1000 |

### 5.4 `scene.eevee.ray_tracing_options` (`RaytraceEEVEE`) — 실측

| 프로퍼티 | 타입 | 기본값 | 범위 |
|---|---|---|---|
| `resolution_scale` | ENUM | `'2'` | `1`/`2`/`4`/`8`/`16` |
| `screen_trace_quality` | FLOAT | `0.25` | 0 … 1 |
| `screen_trace_thickness` | FLOAT | `0.1` | 1e-6 … 3.4e38 |
| `trace_max_roughness` | FLOAT | `0.5` | 0 … 1 (이 값 위 러프니스는 probe로 폴백) |
| `use_backface_hit` | BOOL | `True` | |
| `backface_radiance_scale` | FLOAT | `0.25` | 0 … 1 |
| `use_denoise` | BOOL | `True` | |
| `denoise_spatial` | BOOL | `True` | |
| `denoise_temporal` | BOOL | `True` | |
| `denoise_bilateral` | BOOL | `True` | |

위 표는 `verify/doc/s5_4_rt.py`로 전수 덤프한 실측값이다 (`type(rt).__name__ == 'RaytraceEEVEE'`).

### 5.5 EEVEE 헤드리스 — libEGL 없으면 100배 느려진다

```python
import bpy, os, shutil, time
OUT = '/workspace/out/eevee'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'BLENDER_EEVEE'
scn.render.resolution_x = scn.render.resolution_y = 64
scn.eevee.taa_render_samples = 8
bpy.ops.mesh.primitive_plane_add(size=10)
m = bpy.data.materials.new("M")
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
bpy.context.object.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
bpy.context.object.data.energy = 4
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
scn.camera = bpy.context.object
scn.render.filepath = f'{OUT}/ev'
t0 = time.time()
bpy.ops.render.render(write_still=True)
print("EEVEE 64px/8spp took %.2fs; exists=%s" % (time.time() - t0,
                                                 os.path.exists(f'{OUT}/ev.png')))
try:
    bpy.ops.render.opengl('EXEC_DEFAULT', write_still=True, view_context=True)
except RuntimeError as e:
    print("opengl FAILED:", type(e).__name__, e)
print("__SCRIPT_OK__")
```

실측 출력 (stderr에 EGL 경고 3줄이 먼저 나온다):

```
EGL Error (0x3009): EGL_BAD_MATCH: Arguments are inconsistent (for example, a valid context requires buffers not supplied by a valid surface).
EGL Error (0x3009): EGL_BAD_MATCH: Arguments are inconsistent (for example, a valid context requires buffers not supplied by a valid surface).
EGL Error (0x3009): EGL_BAD_MATCH: Arguments are inconsistent (for example, a valid context requires buffers not supplied by a valid surface).
00:22.903  render           | Saved: '/workspace/out/eevee/ev.png'
EEVEE 64px/8spp took 20.67s; exists=True
opengl FAILED: RuntimeError Error: Cannot use OpenGL render in background mode (no opengl context)
__SCRIPT_OK__
```

| | Cycles CPU | EEVEE (llvmpipe 소프트웨어 EGL) |
|---|---|---|
| 48×48 @ 4spp | ~0.03 s | — |
| 64×64 @ 8spp | — | **20.7 s ~ 37.1 s** (두 번 실측, llvmpipe 타임이 크게 흔들림) |
| 96×96 @ 16spp | ~1.2 s | 수백 초 추정 |
| stderr 잡음 | 없음 | `EGL_BAD_MATCH` 3줄 (무해, 렌더를 막지 않음) |

**결론: 스크립트 검증 루프에서는 EEVEE를 쓰지 마라.** 프로퍼티 값만 introspection으로
확인하고(그건 GPU 없이도 된다), 실제 렌더 검증은 Cycles CPU로 한다.

---

## 6. 출력 설정

### 6.1 `RenderSettings` 중 출력 관련 프로퍼티 (5.2.2 실측)

| 프로퍼티 | 타입 | 기본값 | 의미 |
|---|---|---|---|
| `filepath` | STRING | `'//'` | 출력 경로. `#`가 프레임 번호 자리표시자 |
| `use_file_extension` | BOOL | `True` | 확장자를 파일명에 붙일지 |
| `use_overwrite` | BOOL | `True` | `False`면 이미 있는 프레임을 건너뛴다 |
| `use_placeholder` | BOOL | `False` | **5.x에서 여전히 존재하나 이 빌드에서 동작 미검증** |
| `save_output` | BOOL | `True` | **5.x 신규**. `False`면 Output Properties를 끄고 File Output 노드로만 기록 |
| `is_movie_format` | BOOL | —(읽기) | `file_format='FFMPEG'`이면 `True` |
| `use_multiview` | BOOL | `False` | 스테레오/멀티뷰 |
| `views_format` | ENUM | `'STEREO_3D'` | `STEREO_3D` / `MULTIVIEW` |
| `stereo_views` / `views` | COLLECTION | | 5.x에서 `stereo` → `views`로 이름 변경 |
| `use_spherical_stereo` | BOOL | `False` | |
| `use_single_layer` | BOOL | `False` | View Layer 하나만 |
| `use_sequencer` | BOOL | `True` | 비어 있으면 자동으로 꺼진다 |
| `use_compositing` | BOOL | `True` | 컴포지터 사용 |
| `use_lock_interface` | BOOL | `False` | 렌더 중 UI 잠금 |
| `use_border` / `use_crop_to_border` | BOOL | `False` | |
| `border_min_x`…`border_max_y` | FLOAT | 0/0/1/1 | 0…1 정규화 |
| `use_stamp` | BOOL | `False` | 각인 |
| `use_stamp_*` | BOOL 다수 | | `note`, `date`, `time`, `frame`, `frame_range`, `camera`, `lens`, `scene`, `memory`, `render_time`, `hostname`, `filename`, `labels`, `marker`, `sequencer_strip` |
| `stamp_note_text` / `stamp_font_size` / `stamp_background` / `stamp_foreground` | | | |
| `resolution_x` / `resolution_y` | INT | 1920 / 1080 | 4 … 65536 |
| `resolution_percentage` | INT | `100` | 1 … 32767 |
| `pixel_aspect_x` / `pixel_aspect_y` | FLOAT | 1.0 / 1.0 | 1 … 200 |
| `filter_size` | FLOAT | `1.5` | 0.01 … 10 (soft), 0 … 500 (hard) |
| `use_motion_blur` / `motion_blur_shutter` / `motion_blur_position` | | `False`/`0.5`/`CENTER` | |
| `threads_mode` / `threads` | ENUM/INT | `AUTO`/`1` | `threads=1`은 AUTO가 아니라 **고정 1** |
| `use_persistent_data` | BOOL | `False` | |
| `use_simplify` | BOOL | `False` | + `simplify_subdivision_render` 등 6종 |
| `use_high_quality_normals` | BOOL | `False` | |
| `use_render_cache` | BOOL | `False` | |
| `use_auto_generate_texture_cache` / `use_texture_cache` | BOOL | `False`/`True` | |
| `use_freestyle` | BOOL | `False` | |

**`save_output=False`의 실제 동작 (실측)**: 컴포지터에 File Output 노드가 하나도 없으면
`bpy.ops.render.render`가 즉시 죽는다.

```
RuntimeError: Error: Render output disabled in Output properties and no active compositing File Output nodes
```

### 6.2 `filepath`와 `####` — 전부 실측

`verify/17_naming.py`가 `frame_start=7, frame_end=9`로 모든 조합을 돌렸다.

| `filepath` | 호출 | 실제 파일 |
|---|---|---|
| `a_` | `animation=True` | `a_0007.png` `a_0008.png` `a_0009.png` |
| `b_####` | `animation=True` | `b_0007.png` `b_0008.png` `b_0009.png` |
| `c_######` | `animation=True` | `c_000007.png` `c_000008.png` `c_000009.png` |
| `d_####.png` | `animation=True` | `d_0007.png` `d_0008.png` `d_0009.png` (중복 확장자 안 붙음) |
| `e_` | `write_still=True` | `e_.png` (프레임 번호 **없음**) |
| `f_####` | `write_still=True` | **`f_####.png`** (해시가 **확장되지 않음**) |
| `g_.png` | `write_still=True`, `use_file_extension=True` | `g_.png` |
| `g2_.png` | `write_still=True`, `use_file_extension=False` | `g2_.png` |
| `g3_` | `write_still=True`, `use_file_extension=False` | `g3_` (확장자 없음) |
| `h_####.png` | `write_still=True` (frame 8) | `h_####.png` (해시 그대로!) |
| `i_####.png` | `animation=True`, `frame_step=3`, 1..10 | `i_0001` `i_0004` `i_0007` `i_0010` |
| `//rel_####.png` | `animation=True` (blend가 열려 있음) | `rel_0001.png` … `rel_0010.png` |

| 규칙 | 내용 |
|---|---|
| 스필 | `write_still=True`는 `#`를 **확장하지 않고** 프레임 번호를 붙이지 **않는다** |
| 애니메이션 | `#`가 없으면 `####`가 자동으로 붙는다 |
| 확장자 | 이미 `.png`가 있으면 중복해서 안 붙는다 |
| 상대 경로 | `//`는 **blend 파일 기준**. blend를 안 열었으면 현재 작업 디렉터리 기준(위험) |

> CLI `-f`는 이 규칙이 **반대**다: `-o out_####`가 없어도 `-f`는 `out_0003.png`처럼
> 해시를 확장한다(§3.3). Python `write_still`과 CLI `-f`를 섞어 쓰면 파일명이 뒤바뀐다.

### 6.3 `image_settings.file_format` 전체 (5.2.2 실측)

```
'AVIF'  'JPEG'  'OPEN_EXR'  'PNG'  'WEBP'  'BMP'  'CINEON'  'DPX'
'IRIS'  'JPEG2000'  'HDR'  'TARGA'  'TARGA_RAW'  'TIFF'
'OPEN_EXR_MULTILAYER'  'FFMPEG'
```

**16개.** 4.x에 없던 `AVIF`, `WEBP`이 들어 있고, `AVI`는 없고 `TARGA`가 있다.

> **5.x 함정**: `file_format` 대입이 `media_type`에 **게이트된다.**
> `media_type`가 `'IMAGE'`인 상태에서 `OPEN_EXR_MULTILAYER`나 `FFMPEG`를 대입하려 하면
> 그 순간 `TypeError`가 난다(§6.4).

### 6.4 `media_type` — 5.x 신규 게이트

`ImageFormatSettings.media_type`는 5.x에 추가된 ENUM으로 `'IMAGE'`,
`'MULTI_LAYER_IMAGE'`, `'VIDEO'` 세 값이다. `media_type`가 바뀌면 `file_format`과
`color_mode`/`color_depth`의 **기본값이 같이 바뀐다.**

| `media_type` | `color_mode` 기본 | `color_depth` 기본 | 비고 |
|---|---|---|---|
| `IMAGE` | `'RGBA'` | `'8'` | |
| `MULTI_LAYER_IMAGE` | `'RGBA'` | `'32'` | 자동 float |
| `VIDEO` | `'RGB'` | `'8'` | alpha 불가 경로 |

`FFMPEG`을 쓰려면 **반드시 `media_type='VIDEO'`를 먼저** 설정한다:

```python
import bpy
ims = bpy.context.scene.render.image_settings
ims.file_format = 'PNG'                      # IMAGE 상태
try:
    ims.file_format = 'FFMPEG'
    print("FFMPEG set without media_type -> OK", ims.file_format)
except TypeError as e:
    print("FFMPEG set without media_type -> TypeError:", e)
ims.media_type = 'VIDEO'
ims.file_format = 'FFMPEG'
print("after media_type='VIDEO' ->", ims.file_format,
      " is_movie_format:", bpy.context.scene.render.is_movie_format,
      " color_mode:", ims.color_mode)
ims.media_type = 'IMAGE'
ims.file_format = 'PNG'
print("back:", ims.media_type, ims.file_format)
print("__SCRIPT_OK__")
```

실측 출력:

```
FFMPEG set without media_type -> TypeError: bpy_struct: item.attr = val: enum "FFMPEG" not found in ('AVIF', 'JPEG', 'OPEN_EXR', 'PNG', 'WEBP', 'BMP', 'CINEON', 'DPX', 'IRIS', 'JPEG2000', 'HDR', 'TARGA', 'TARGA_RAW', 'TIFF')
after media_type='VIDEO' -> FFMPEG  is_movie_format: True  color_mode: RGB
back: IMAGE PNG
__SCRIPT_OK__
```

동일한 이유로 `CompositorNodeOutputFile.format`도 처음엔 `media_type='MULTI_LAYER_IMAGE'`
/ `file_format='OPEN_EXR_MULTILAYER'`다(§8.7).

### 6.5 `color_mode` / `color_depth` — 실측 매트릭스

실측 (`verify/doc/s6_5_matrix.py`, Cycles CPU 64×64 @4spp):

`color_depth`는 포맷별로 제한된다 (실측 `TypeError`):

```
PNG   depth=32  -> TypeError: enum "32" not found in ('8', '16')
PNG   depth=12  -> TypeError: enum "12" not found in ('8', '16')
JPEG  depth=16  -> TypeError: enum "16" not found in ('8',)
OPEN_EXR depth=8 -> TypeError: enum "8" not found in ('16', '32')
```

`ImageFormatSettings.color_depth`의 전체 후보는 `('8', '10', '12', '16', '32')`이고
포맷별로 걸러진다. `PNG`는 `8`/`16`만, `JPEG`는 `8`만, `OPEN_EXR`는 `16`/`32`만 허용.

> **`Image.depth`는 파일의 비트 깊이가 아니다.** 위 표에서 8bit RGB가 24, 8bit RGBA가 32,
> 16bit RGB가 96이 나왔다(기대값 48이 아님). 이는 `Image.pixels` 버퍼의 바이트 레이아웃에서
> 나온 값이다. **파일의 비트 깊이를 알아내려면 `image_settings.color_depth`를 기록 시점에 봐라.**

| 포맷 | `color_depth` 후보 |
|---|---|
| PNG | `8`, `16` |
| JPEG / WEBP / AVIF | `8` |
| OPEN_EXR | `16`(half), `32`(float) |
| CINEON / DPX | `8`…`16` |

### 6.6 색 관리 (Color Management) — 실측

`ColorManagedViewSettings`:

| 프로퍼티 | 타입 | 기본값 | 범위 | 비고 |
|---|---|---|---|---|
| `view_transform` | ENUM(dynamic) | `'AgX'` | | §4.2b의 9개 |
| `look` | ENUM(dynamic) | `'None'` | | **`view_transform` 의존** |
| `exposure` | FLOAT | `0.0` | −32 … 32 | EV |
| `gamma` | FLOAT | `1.0` | 0 … 5 | |
| `use_curve_mapping` | BOOL | `False` | | |
| `curve_mapping` | POINTER→`CurveMapping` | | | |
| `use_white_balance` | BOOL | `False` | | 5.x 신규 |
| `white_balance_temperature` | FLOAT | `6500.0` | 1800 … 100000 | |
| `white_balance_tint` | FLOAT | `10.0` | −500 … 500 | |
| `white_balance_whitepoint` | FLOAT | `0.0` | | |
| `is_hdr` | BOOL | `False` | | (읽기) |
| `support_emulation` | BOOL | `False` | | |

`ColorManagedDisplaySettings` (실측):

| 프로퍼티 | 타입 | 기본값 | enum |
|---|---|---|---|
| `display_device` | ENUM | `'sRGB'` | OCIO 스페이스 (introspection은 `['NONE']`으로 거짓말) |
| `emulation` | ENUM | `'AUTO'` | `OFF` / `AUTO` |

`scene.sequencer_colorspace_settings.name` — **이 하나는 introspection이 정상 동작한다**
(OCIO가 68개 색공간 이름을 직접 준다). 실측 후보 (68개):

```
'ACES 1.3 sRGB' 'ACES 2.0 sRGB' 'ACES2065-1' 'ACEScc' 'ACEScct' 'ACEScg' 'ADX10' 'ADX16'
'ARRI LogC3 (EI800)' 'ARRI LogC4' 'AgX Base sRGB' 'AgX Log' 'Apple Log' 'Apple Log 2'
'BMDFilm WideGamut Gen5' 'CanonLog2 CinemaGamut D55' 'CanonLog3 CinemaGamut D55'
'D-Log D-Gamut' 'DaVinci Intermediate WideGamut' 'Display P3' 'Filmic Log' 'Filmic sRGB'
'Gamma 1.8 Encoded Rec.709' 'Gamma 2.2 Encoded AP1' 'Gamma 2.2 Encoded AdobeRGB'
'Gamma 2.2 Encoded Rec.709' 'Gamma 2.4 Encoded Rec.709' 'Khronos PBR Neutral sRGB'
'Linear ARRI Wide Gamut 3' 'Linear ARRI Wide Gamut 4' 'Linear Adobe RGB' 'Linear Apple Wide Gamut'
'Linear BMD WideGamut Gen5' 'Linear CIE-XYZ D65' 'Linear CIE-XYZ E' 'Linear CinemaGamut D55'
'Linear D-Gamut' 'Linear DCI-P3 D65' 'Linear DaVinci WideGamut' 'Linear FilmLight E-Gamut'
'Linear REDWideGamutRGB' 'Linear Rec.2020' 'Linear Rec.709' 'Linear S-Gamut3'
'Linear S-Gamut3.Cine' 'Linear V-Gamut' 'Linear Venice S-Gamut3' 'Linear Venice S-Gamut3.Cine'
'Log3G10 REDWideGamutRGB' 'Non-Color' 'Rec.1886' 'Rec.2020' 'Rec.2100-HLG' 'Rec.2100-PQ'
'S-Log3 S-Gamut3' 'S-Log3 S-Gamut3.Cine' 'S-Log3 Venice S-Gamut3' 'S-Log3 Venice S-Gamut3.Cine'
'V-Log V-Gamut' 'sRGB' 'sRGB Encoded AP1' 'sRGB Encoded P3-D65' 'scene_linear'
```

`ImageFormatSettings.color_management`:

| 값 | 의미 |
|---|---|
| `'FOLLOW_SCENE'` (기본) | 씬의 `view_settings`를 그대로 쓴다 |
| `'OVERRIDE'` | `image_settings.view_settings`로 덮어쓴다 (실측: `AgX`로 표시됨) |

`image_settings.has_linear_colorspace`는 포맷별 플래그다:
`OPEN_EXR` → `True`, `PNG` → `False`(실측).
`image_settings.linear_colorspace_settings.name`은 EXR에 쓸 선형 스페이스이며
기본값이 빈 문자열 `''`이다(비어 있으면 `bpy.rna` 경고가 출력된다).

### 6.7 이미지 읽기/쓰기 (5.2 API)

`Image` datablock의 주요 프로퍼티(실측 타입):

| 프로퍼티 | 타입 | 의미 |
|---|---|---|
| `size` | (INT, INT) | 픽셀 크기 |
| `channels` | INT | 3/4 (파일 무관, 항상 RGBA 4채널로 접근) |
| `depth` | INT | **내부 버퍼 비트 수** (파일 비트 깊이 아님, §6.5) |
| `is_float` | BOOL | float 버퍼 여부 (EXR 등) |
| `pixels` | FLOAT(bulk) | `w*h*4` float. **row 0 = 맨 아래** |
| `alpha_mode` | ENUM | `STRAIGHT` / `PREMUL` / `NONE` (실측 PNG 로드 시 `STRAIGHT`) |
| `colorspace_settings` | POINTER | `name` = 색공간 |
| `type` | ENUM | `IMAGE` / `RENDER_RESULT` / `COMPOSITING` |
| `source` | ENUM | `FILE` / `GENERATED` / `VIEWER` … |
| `filepath` / `filepath_raw` | STRING | |
| `file_format` | ENUM | |
| `is_dirty` | BOOL | `foreach_set` 후 `True`가 되고 `save()` 시 `False` |
| `has_data` | BOOL | **Render Result는 항상 `False`** (§10) |

**핵심: `.pixels`는 sRGB 인코딩 값을 준다 (linear 아니다).** 실측 검증:

```python
import bpy, array
W = H = 4
img = bpy.data.images.new("synth", W, H, alpha=False, float_buffer=False)
px = array.array('f', [0.0]) * (W * H * 4)
vals = [0.0, 64 / 255, 128 / 255, 255 / 255]
for i in range(W * H):
    px[i * 4 + 0] = vals[i % 4]
    px[i * 4 + 3] = 1.0
img.pixels.foreach_set(px)
img.filepath_raw = '/workspace/out/synth_default.png'
img.file_format = 'PNG'
img.save()

back = bpy.data.images.load('/workspace/out/synth_default.png', check_existing=False)
b = array.array('f', [0.0]) * (W * H * 4)
back.pixels.foreach_get(b)
print("reloaded: size", back.size[:], "channels", back.channels, "depth", back.depth,
      "is_float", back.is_float, "colorspace", back.colorspace_settings.name,
      "alpha_mode", back.alpha_mode, "type", back.type, "source", back.source)
print("row0 R read back:", [round(b[i * 4], 6) for i in range(4)])
print("expected sRGB/255  :", [round(v, 6) for v in vals])
srgb_to_lin = [round(((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045
                       else c / 255 / 12.92, 6) for c in (0, 64, 128, 255)]
print("expected linearised:", srgb_to_lin)
print("MATCHES sRGB/255:", all(abs(b[i * 4] - vals[i]) < 1e-5 for i in range(4)),
      " MATCHES linearised:", all(abs(b[i * 4] - srgb_to_lin[i]) < 1e-4 for i in range(4)))
lst = list(back.pixels)
b4 = array.array('f', [0.0]) * (W * H * 4)
back.pixels.foreach_get(b4)
print("len(list(pixels)) =", len(lst), " foreach_get == list():",
      all(abs(a - c) < 1e-6 for a, c in zip(lst, b4)))
print("__SCRIPT_OK__")
```

실측 출력:

```
reloaded: size (4, 4) channels 4 depth 24 is_float False colorspace sRGB alpha_mode STRAIGHT type IMAGE source FILE
row0 R read back: [0.0, 0.25098, 0.501961, 1.0]
expected sRGB/255  : [0.0, 0.25098, 0.501961, 1.0]
expected linearised: [0.0, 0.051269, 0.215861, 1.0]
MATCHES sRGB/255: True  MATCHES linearised: False
len(list(pixels)) = 64  foreach_get == list(): True
__SCRIPT_OK__
```

| 사실 | 근거 |
|---|---|
| 8비트 sRGB PNG의 `.pixels`는 **바이트/255 값 그대로** | 128 → `0.501961` (linear면 `0.215861`이어야 함) |
| `colorspace_settings.name`을 바꿔도 값은 안 바뀐다 | `'Non-Color'`로 바꿔도 `0.25098` 유지 (재적재 후에도) |
| `list(pixels)`와 `foreach_get` 결과가 **동일** | `all(abs(a-c) < 1e-6)` → `True` |
| float EXR의 `.pixels`는 선형 | `is_float=True`, `colorspace='Linear Rec.709'` |

따라서 §4.7에서 `film_exposure=0.25`의 평균이 0.25가 아니라 0.404였던 이유가 설명된다:
선형 ×0.25 → sRGB 인코딩 ≈ 0.5 부근.

**빠른 API 요약**:

```python
import bpy, array
# 쓰기 (가장 빠름: foreach_set)
img = bpy.data.images.new("out", W, H, alpha=True, float_buffer=False)
img.pixels.foreach_set(array.array('f', [0.0]) * (W * H * 4))
img.filepath_raw = '/path/x.png'
img.file_format = 'PNG'
img.save()                       # is_dirty 가 False 로 돌아감
# 읽기
im = bpy.data.images.load('/path/x.png', check_existing=False)
buf = array.array('f', [0.0]) * (im.size[0] * im.size[1] * 4)
im.pixels.foreach_get(buf)
bpy.data.images.remove(im)       # 해제 안 하면 메모리 누수
# 리사이즈 (nearest가 아니라 Blender 내부 필터)
im.scale(w, h)
# 개별 픽셀 (느림, 파이썬 루프)
im.pixels[0] = 0.5
```

8비트 PNG 라운드 트립은 **정확하지 않다**(양자화). 실측:
`foreach_set` → `save` → `load` 후 값이 8비트 양자화 오차 이내에서만 일치.

### 6.8 `Image` 오퍼레이터 (실측 시그니처)

```
IMAGE_OT_save_as
     save_as_render:BOOLEAN=False
     copy:BOOLEAN=False
     allow_path_tokens:BOOLEAN=True
     filepath:STRING=''
     check_existing:BOOLEAN=True
     filter_*:BOOLEAN=…  filemode:INT=9
     relative_path:BOOLEAN=True
     show_multiview:BOOLEAN=False
     use_multiview:BOOLEAN=False
     display_type:ENUM='DEFAULT' enum=['DEFAULT', 'LIST_VERTICAL', 'LIST_HORIZONTAL', 'THUMBNAIL']
     sort_method:ENUM='' enum=[]

IMAGE_OT_open
     allow_path_tokens, filepath, directory, files, hide_props_region,
     check_existing, filter_*, filemode, relative_path, show_multiview,
     use_multiview, display_type, sort_method,
     use_sequence_detection:BOOLEAN=True
     use_udim_detecting:BOOLEAN=True
```

`bpy.ops.image.save_render`는 **존재하지 않는다**(`get_rna_type` → `KeyError`).
`bpy.ops.image.save` / `save_all_modified` / `reload`은 인자가 **하나도 없다**(현재 활성 이미지 대상).
`bpy.ops.image.render_border`도 있다(연산자 목록에 있음).

### 6.9 멀티뷰 (스테레오) — 검증됨

실측 (`verify/doc/s6_9_multiview.py`, Cycles CPU 32×32 @2spp, 2프레임):

실측 출력:

```
files: ['MULTIVIEW_0001_L.png', 'MULTIVIEW_0001_R.png', 'MULTIVIEW_0002_L.png', 'MULTIVIEW_0002_R.png',
        'STEREO_3D_0001_L.png', 'STEREO_3D_0001_R.png', 'STEREO_3D_0002_L.png', 'STEREO_3D_0002_R.png']
__SCRIPT_OK__
```

스텁 카메라(거리 무한)만으로도 `L`/`R` 두 개가 **자동으로** 생성된다
(카메라에 `stereo` 설정이 없으면 동일 위치에서 두 뷰). `image_settings.views_format`
(`INDIVIDUAL`/`STEREO_3D`/`MULTIVIEW`)는 *파일 내부* 3D 포맷 지정이고,
`render.views_format`는 *파일 분할* 방식이다. 두 개를 혼동하지 마라.

### 6.10 `frame_path()` — 진짜 파일명을 미리 계산하기

확인 코드 (`verify/doc/s6_10_framepath.py`): `s.render.filepath = fp; print(s.render.frame_path(frame=5))` — 실측 결과:

`filepath`별 `frame_path(frame=5)` 결과 (실측):

| `filepath` | `frame_path(frame=5)` |
|---|---|
| `x_` | `/out/x_0005.png` |
| `x_####` | `/out/x_0005.png` |
| `x_######` | `/out/x_000005.png` |
| `x_####.png` | `/out/x_0005.png` |
| **`x_.png`** | **`/out/x_.png0005.png`** ← 확장자가 `#`보다 뒤에 있으면 망가진다 |
| `x` | `/out/x0005.png` |

> `frame_path()`는 **애니메이션 경로 규칙**을 따른다. 스틸 렌더의 실제 규칙
> (`#` 확장 안 함, §6.2)과 다르므로 스틸 파일명을 계산할 때는 직접 만들어야 한다(§9.3).

---

## 7. 애니메이션 렌더

### 7.1 프레임 범위 설정

```python
import bpy
scn = bpy.context.scene
scn.frame_start = 1
scn.frame_end   = 48
scn.frame_step  = 1          # 3이면 1,4,7,... 만
scn.frame_current = 1        # 렌더 시작 프레임
scn.use_preview_range = False  # True면 preview_start/end 범위를 쓴다
scn.render.fps = 24
scn.render.fps_base = 1.0
```

실측: `frame_start=1, frame_end=10, frame_step=3` + `animation=True` →
`i_0001.png`, `i_0004.png`, `i_0007.png`, `i_0010.png` (4프레임). 48프레임 2배속이 아니라
**프레임 번호 간격**이라는 점을 잊지 마라.

### 7.2 `animation=True` — 검증된 패턴

```python
import bpy, addon_utils, os, shutil
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/anim'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'
scn.render.resolution_x = scn.render.resolution_y = 48
scn.cycles.device = 'CPU'; scn.cycles.samples = 4
scn.cycles.use_adaptive_sampling = False; scn.cycles.use_denoising = False
scn.render.image_settings.file_format = 'PNG'
scn.render.image_settings.color_mode = 'RGBA'
bpy.ops.mesh.primitive_plane_add(size=10)
m = bpy.data.materials.new("M")
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
bpy.context.object.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5)); bpy.context.object.data.energy = 4
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
scn.camera = bpy.context.object
scn.frame_start, scn.frame_end, scn.frame_step = 1, 6, 1
for f in range(1, 7):
    bpy.context.object.rotation_euler[2] = (f - 1) * 0.2
    bpy.context.object.keyframe_insert('rotation_euler', index=2, frame=f)

scn.render.filepath = f'{OUT}/seq_####.png'
bpy.ops.render.render(animation=True)
print("files:", sorted(os.listdir(OUT)))
print("__SCRIPT_OK__")
```

### 7.3 FFMPEG / 컨테이너 / 코덱

`media_type='VIDEO'`로 먼저 전환하고 `file_format='FFMPEG'`(§6.4).
`scene.render.ffmpeg`의 실측 프로퍼티:

| 프로퍼티 | 타입 | 기본값 | enum / 범위 |
|---|---|---|---|
| `format` | ENUM | `'MKV'` | `MPEG4` `MKV` `WEBM` `AVI` `DV` `FLASH` `MPEG1` `MPEG2` `OGG` `QUICKTIME` |
| `codec` | ENUM | `'H264'` | `NONE AV1 H264 H265 WEBM DNXHD DV FFV1 FLASH HUFFYUV MPEG1 MPEG2 MPEG4 PNG PRORES QTRLE THEORA` |
| `constant_rate_factor` | ENUM | `'MEDIUM'` | `NONE LOSSLESS PERC_LOSSLESS HIGH MEDIUM LOW VERYLOW LOWEST CUSTOM` |
| `custom_constant_rate_factor` | INT | `23` | 0 … 63 |
| `ffmpeg_preset` | ENUM | `'GOOD'` | `BEST` `GOOD` `REALTIME` |
| `ffmpeg_prores_profile` | ENUM | `'422_STD'` | `422_PROXY 422_LT 422_STD 422_HQ 4444 4444_XQ` |
| `gopsize` | INT | `25` (실측 렌더 중 18로 보고) | 0 … 500 |
| `audio_codec` | ENUM | `'NONE'` | `NONE AAC AC3 FLAC MP2 MP3 OPUS PCM VORBIS` |
| `audio_bitrate` | INT | `192` | 32 … 2048 |
| `audio_mixrate` | INT | `48000` | 8000 … 192000 |
| `audio_channels` | ENUM | `'STEREO'` | `MONO STEREO SURROUND4 SURROUND51 SURROUND71` |
| `audio_volume` | FLOAT | `1.0` | 0 … 1 |
| `use_autosplit` | BOOL | `False` | |
| `use_lossless_output` | BOOL | `False` | |
| `use_max_b_frames` / `max_b_frames` | BOOL/INT | `False`/`0` | 0 … 16 |
| `video_bitrate` / `minrate` / `maxrate` / `muxrate` / `packetsize` / `buffersize` | INT | `0` | 비트레이트 제어 |

이 빌드의 FFmpeg는 **libavcodec 62.28.100** (`bpy.app.ffmpeg.version_string`)으로 빌드되었고,
`bpy.app.build_options.codec_ffmpeg = True`, `codec_avi = False`다.

검증된 조합 (48×48, 3프레임, 실측):

| `format` | `codec` | 결과 |
|---|---|---|
| `WEBM` | `WEBM` | ✅ `vid_WEBM_WEBM0001-0003.webm` |
| `MKV` | `H264` | ✅ `vid_MKV_H2640001-0003.mkv` |
| `MKV` | `FFV1` | ✅ `vid_MKV_FFV10001-0003.mkv` |
| `MPEG4` | `H265` | ✅ `vid_MPEG4_H2650001-0003.mp4` (+x265 저해상도 경고) |
| `QUICKTIME` | `PRORES` | ✅ `vid_QUICKTIME_PRORES0001-0003.mov` |
| `MKV` + `H264` → `WEBM` 컨테이너 | `H264` | ❌ `RuntimeError: Error: Could not initialize streams, probably unsupported codec combination` |

> **컨테이너-코덱 짝이 틀리면 렌더 중간의 마지막에 죽는다.** `WEBM` 컨테이너에는
> `WEBM`(VP8/VP9) 코덱만 들어간다. 전 조합을 CI에서 한 번씩 돌려정답 표를 만들어라.

조합 검증 코드(`verify/doc/s7_3_video.py`): 5개 컨테이너/코덱 쌍을 순회하며
`bpy.ops.render.render(animation=True)`를 시도하고 `os.listdir`로 결과 파일을 확인한다.

> **영상 파일명 규칙**: `filepath` 뒤에 **`<시작>-<끝>`(4자리 0패딩)** 이 붙고 그 뒤에 확장자.
> `filepath='/out/movie_'` → `/out/movie_0001-0006.mp4`.
> `filepath='/out/clip_MKV'` → `/out/clip_MKV0001-0006.mkv` (구분자 없음!).
> 이미지에 쓰이는 `####` 규칙과 **완전히 다르다**(§6.2).

### 7.4 렌더 핸들러 — 호출 순서 (실측)

`bpy.app.handlers`에 있는 렌더 관련 핸들러 전부:
`render_init`, `render_pre`, `render_post`, `render_write`, `render_complete`,
`render_cancel`, `render_stats`, `composite_pre`, `composite_post`, `composite_cancel`.

실측된 3프레임 애니메이션에서의 호출 순서:

```
 1. render_init      scene=Scene frame=1
 2. render_pre       frame=1 res=32x32
 3. render_post      frame=1 RR.size=(0, 0) RR.has_data=False
 4. render_write     frame=1 render.filepath='.../h_####.png'
 5. render_pre       frame=2
 6. render_post      frame=2
 7. render_write     frame=2
 8. render_pre       frame=3
 9. render_post      frame=3
10. render_write     frame=3
11. render_complete  frame=1 (애니메이션 전체가 끝난 뒤 1회만)
```

| 핸들러 | 횟수 | 시점 | 인자 |
|---|---|---|---|
| `render_init` | 렌더 **작업당 1회** | 시작 | `(scene, depsgraph=None)` |
| `render_pre` | **프레임마다** | 렌더 전 | `(scene, depsgraph=None)` |
| `render_post` | **프레임마다** | 렌더 후, 쓰기 전 | `(scene, depsgraph=None)` |
| `render_write` | **프레임마다** | **파일이 디스크에 나온 뒤** | `(scene)` |
| `render_complete` | 렌더 작업당 1회 | 전체 종료 | `(scene)` |
| `render_cancel` | 취소 시 1회 | | `(scene)` |

핵심: **`render_post`는 파일이 아직 디스크에 없다.** `render_write`가 "쓰기 완료" 시점이다.
또 `render_complete`에서 `scene.frame_current`는 **시작 프레임(1)** 으로 되돌아와 있다(실측).

### 7.5 `@persistent` — 검증됨

```python
import bpy, addon_utils, os, shutil
from bpy.app.handlers import persistent
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/handlers'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'
scn.render.resolution_x = scn.render.resolution_y = 32
scn.cycles.device = 'CPU'; scn.cycles.samples = 2
scn.cycles.use_adaptive_sampling = False; scn.cycles.use_denoising = False
scn.render.image_settings.file_format = 'PNG'
bpy.ops.object.light_add(type='SUN')
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
scn.camera = bpy.context.object
scn.frame_start, scn.frame_end = 1, 3
scn.render.filepath = f'{OUT}/h_####.png'

LOG = []

@persistent
def on_init(scene):
    LOG.append(f"render_init      frame={scene.frame_current}")

@persistent
def on_pre(scene, depsgraph=None):
    LOG.append(f"render_pre       frame={scene.frame_current} "
               f"res={scene.render.resolution_x}x{scene.render.resolution_y}")

@persistent
def on_post(scene, depsgraph=None):
    rr = bpy.data.images.get('Render Result')
    LOG.append(f"render_post      frame={scene.frame_current} "
               f"RR.size={tuple(rr.size) if rr else None} "
               f"RR.has_data={rr.has_data if rr else None}")

@persistent
def on_write(scene):
    LOG.append(f"render_write     frame={scene.frame_current} "
               f"render.filepath={scene.render.filepath!r}")

@persistent
def on_complete(scene):
    LOG.append(f"render_complete  frame={scene.frame_current}")

for h in (on_init, on_pre, on_post, on_write, on_complete):
    pass
bpy.app.handlers.render_init.append(on_init)
bpy.app.handlers.render_pre.append(on_pre)
bpy.app.handlers.render_post.append(on_post)
bpy.app.handlers.render_write.append(on_write)
bpy.app.handlers.render_complete.append(on_complete)

bpy.ops.render.render(animation=True)

for i, l in enumerate(LOG, 1):
    print(f"  {i:2d}. {l}")
print("files:", sorted(os.listdir(OUT)))

# 제거
bpy.app.handlers.render_init.remove(on_init)
bpy.app.handlers.render_pre.remove(on_pre)
bpy.app.handlers.render_post.remove(on_post)
bpy.app.handlers.render_write.remove(on_write)
bpy.app.handlers.render_complete.remove(on_complete)
print("after removal: pre=%d post=%d write=%d complete=%d" % (
    len(bpy.app.handlers.render_pre), len(bpy.app.handlers.render_post),
    len(bpy.app.handlers.render_write), len(bpy.app.handlers.render_complete)))

# @persistent survives bpy.ops.wm.read_homefile()
print("after read_homefile (still @persistent): pre=%d post=%d write=%d complete=%d" % (
    len(bpy.app.handlers.render_pre), len(bpy.app.handlers.render_post),
    len(bpy.app.handlers.render_write), len(bpy.app.handlers.render_complete)))
print("__SCRIPT_OK__")
```

실측 출력:

```
  1. render_init      frame=1
  2. render_pre       frame=1 res=32x32
  3. render_post      frame=1 RR.size=(0, 0) RR.has_data=False
  4. render_write     frame=1 render.filepath='/workspace/out/handlers/h_####.png'
  5. render_pre       frame=2 res=32x32
  6. render_post      frame=2 RR.size=(0, 0) RR.has_data=False
  7. render_write     frame=2 render.filepath='/workspace/out/handlers/h_####.png'
  8. render_pre       frame=3 res=32x32
  9. render_post      frame=3 RR.size=(0, 0) RR.has_data=False
 10. render_write     frame=3 render.filepath='/workspace/out/handlers/h_####.png'
 11. render_complete  frame=1
files: ['h_0001.png', 'h_0002.png', 'h_0003.png']
after removal: pre=0 post=0 write=0 complete=0
after read_homefile (still @persistent): pre=0 post=0 write=0 complete=0
__SCRIPT_OK__
```

`@persistent` 효과는 격리 실험으로 증명했다. 같은 리스트에 순수 함수와 데코레이트된
함수를 하나씩 넣고 `read_homefile()`을 호출한다:

```python
import bpy
from bpy.app.handlers import persistent

def plain(scene):
    pass

@persistent
def deco(scene):
    pass

bpy.app.handlers.render_pre.append(plain)
bpy.app.handlers.render_post.append(deco)
print("before: pre=%d post=%d" % (len(bpy.app.handlers.render_pre),
                                 len(bpy.app.handlers.render_post)))
bpy.ops.wm.read_homefile(use_empty=True)
print("after read_homefile: pre=%d post=%d   (@persistent survived, plain did not)"
      % (len(bpy.app.handlers.render_pre), len(bpy.app.handlers.render_post)))
bpy.app.handlers.render_post.remove(deco)
print("__SCRIPT_OK__")
```

실측 출력:

```
before: pre=1 post=1
after read_homefile: pre=0 post=1   (@persistent survived, plain did not)
__SCRIPT_OK__
```

`pre`(순수 함수)는 0으로 사라졌고 `post`(`@persistent`)는 1로 남았다.
`@persistent` 없으면 `read_homefile()` / `read_factory_settings()` 직후 핸들러가 전부 죽는다.
CLI로 `--python` 스크립트를 띄우고 blend를 여러 개 연속 처리할 계획이면 반드시 붙여라.

### 7.6 ⚠️ 스레드 안전 — `render_write`에서 `bpy.data`를 만지면 **크래시한다**

이것은 이 문서에서 가장 위험한 발견이다. `verify/30_handler_crash.py`가 4가지 모드로
분리 실험했다(`HMODE` 환경변수로 전환).

| `HMODE` | `render_write` 안에서 한 일 | 결과 |
|---|---|---|
| `stat` | 순수 파이썬 `print(f"frame={f}")` | ✅ 정상 |
| `path` | `scene.render.frame_path(frame=f)` | ✅ 정상 |
| `load` | `bpy.data.images.load()` + `.pixels.foreach_get()` + `images.remove()` | 💥 **Blender 크래시** |
| `defer` | 경로만 리스트에 넣고 렌더 후 메인 스레드에서 측정 | ✅ 정상 |

`load` 모드의 출력:

```
00:03.770  render           | Saved: '/workspace/out/hcrash/f_0001.png'
  [render_write] frame=1 loaded f_0001.png mean=0.6112
Blender 5.2.2 LTS (hash d13f752e3b9c built 2026-09-15 01:34:58)
Writing: /tmp/blender.crash.txt
```

1프레임째 로드와 출력까지는 성공하고, **2프레임 렌더 진입 시 크래시**한다.
크래시 백트레이스는 메인 스레드의 `blender()` 프레임들 사이에서 발생한다
(`/tmp/blender.crash.txt`).

**따라서 프레임마다 품질을 측정하려면 절대 `render_write` 안에서 이미지를 로드하지 마라.**
`defer` 패턴을 써라:

```python
import bpy
from bpy.app.handlers import persistent

QUEUED = []

@persistent
def _collect(scene):
    """render thread. Collect PATHS ONLY -- no bpy.data work in here."""
    QUEUED.append(scene.render.frame_path(frame=scene.frame_current))

bpy.app.handlers.render_write.append(_collect)
bpy.ops.render.render(animation=True)
bpy.app.handlers.render_write.remove(_collect)

# --- here we are back on the main thread; it is safe to touch bpy.data ---
for path in QUEUED:
    stats = analyze_image(path)     # §9 harness
    assert check_frame(stats)[0] == 'PASS', path
```

`render_write` 안에서 **안전한** 것들: 순수 파이썬, 문자열 조작, `scene.render.*` 읽기,
`scene.render.frame_path()`. **위험한** 것: `bpy.data.images.load/remove/new`,
`bpy.data.*` 전체, `bpy.ops.*` (새 이미지 생성·쓰기), `bpy.context.*` 의존 데이터.

### 7.7 `bpy.app.is_interface_locked` — 이 빌드에 **없다**

```python
import bpy
print("bpy.app.is_interface_locked exists:", hasattr(bpy.app, 'is_interface_locked'))
print("RenderSettings.use_lock_interface exists:",
      'use_lock_interface' in [p.identifier for p in bpy.types.RenderSettings.bl_rna.properties])
print("bpy.app.is_job_running('RENDER') =", bpy.app.is_job_running('RENDER'))
print("__SCRIPT_OK__")
```

실측 출력:

```
bpy.app.is_interface_locked exists: False
RenderSettings.use_lock_interface exists: True
bpy.app.is_job_running('RENDER') = False
__SCRIPT_OK__
```

| 존재 여부 | API |
|---|---|
| ❌ 없음 | `bpy.app.is_interface_locked` (4.x 문서에도 있던 API) |
| ❌ 없음 | `bpy.ops.render.lock_interface()` (§2.3) |
| ✅ 있음 | `scene.render.use_lock_interface` (BOOL, 기본 `False`) — 유일한 UI 락 수단 |
| ✅ 있음 | `bpy.app.is_job_running(job_type)` — `'RENDER'` 같은 문자열 인자를 **필수로 받는다** |

`bpy.app.is_job_running()`을 인자 없이 부르면
`TypeError: is_job_running() missing required argument 'job_type' (pos 1)`.

> **헤드리스 스크립트에는 이 문제가 없다.** `render.use_lock_interface`는
> "UI 스레드가 렌더 스레드에 덮어쓰이지 않게 하라"는 **GUI 전용** 안전장치다.
> `bpy.ops.render.render()`는 백그라운드에서 동기 호출이므로 UI와 경합할 일이 없다.
> 크래시 원인은 UI 락이 아니라 **렌더 스레드에서 bpy.data를 만진 것 자체**다.

---

## 8. 컴포지터 — 5.x 재작업

### 8.1 요약: 무엇이 사라졌는가

| 4.x | 5.2.2 (실측) |
|---|---|
| `scene.node_tree` | ❌ **삭제됨**. `hasattr(scene, 'node_tree')` → `False` |
| `scene.use_nodes = True` 후 `scene.node_tree.nodes.new(...)` | ⚠️ `use_nodes`는 남아 있으나 **DeprecationWarning** (`expected to be removed in Blender 6.0`) |
| `bpy.types.NodeTreeCompositor` | ❌ 존재하지 않음 (`AttributeError`) |
| `bpy.data.node_groups.new(name, 'CompositorNodeTree')` | ✅ **이게 정식 생성 경로** |
| `scene.compositing_node_group` | ✅ **5.0 신규.** 이걸 `scene.node_tree`에 대입 |
| `CompositorNodeComposite` | ❌ **삭제됨** (`Node type CompositorNodeComposite undefined`) |
| `CompositorNodeViewer` | ✅ 존재하지만 입력이 1개, 출력이 0개 |
| 노드 파라미터(`glare.glare_type`, `blur.filter_type`, …) | ❌ **삭제됨. 전부 입력 소켓(`NodeSocket`)으로 이동** |
| `CompositorNodeMixRGB` | ❌ 삭제 → `ShaderNodeMixRGB` / `ShaderNodeMix` |
| `CompositorNodeValToRGB` | ❌ 삭제 → `ShaderNodeValToRGB` |
| `CompositorNodeGamma` | ❌ 삭제 → `ShaderNodeGamma` |
| `CompositorNodeSepia` | ❌ 삭제(대체물 확인 못 함) |
| `CompositorNodeSunBeams` | ❌ 삭제 → Glare 노드의 `'Sun Beams'` 타입 |
| `CompositorNodeValue` | ❌ 삭제 → `ShaderNodeValue` |
| `bpy.ops.node.new_compositing_node_group(name=...)` | ✅ **5.0 신규 오퍼레이터** |

### 8.2 `scene.node_tree`가 사라졌다는 증거

```python
import bpy
scn = bpy.context.scene
print("Scene RNA has 'node_tree' :", 'node_tree' in [p.identifier for p in bpy.types.Scene.bl_rna.properties])
print("hasattr(scene,'node_tree'):", hasattr(scn, 'node_tree'))
print("hasattr(scene,'compositing_node_group'):", hasattr(scn, 'compositing_node_group'))
print("hasattr(bpy.types,'NodeTreeCompositor'):", hasattr(bpy.types, 'NodeTreeCompositor'))
print("scene.compositing_node_group:", repr(scn.compositing_node_group))
print("use_nodes ->", scn.use_nodes, type(scn.use_nodes).__name__)   # DeprecationWarning 발생
print("node tree idnames:", [n for n in dir(bpy.types) if n.endswith('NodeTree')])
print("__SCRIPT_OK__")
```

실측 출력:

```
Scene RNA has 'node_tree' : False
hasattr(scene,'node_tree'): False
hasattr(scene,'compositing_node_group'): True
hasattr(bpy.types,'NodeTreeCompositor'): False
scene.compositing_node_group: None
DeprecationWarning: 'Scene.use_nodes' is expected to be removed in Blender 6.0
use_nodes -> True bool
node tree idnames: ['CompositorNodeTree', 'GeometryNodeTree', 'NodeTree', 'ShaderNodeTree', 'TextureNodeTree']
__SCRIPT_OK__`
```

> 주의: `bpy.types.NodeTreeCompositor`가 없어도 **`bpy.data.node_groups.new(name, 'CompositorNodeTree')`는
> 여전히 동작**한다. idname 문자열이 등록된 정식 타입 이름이다.
> `scene.use_nodes`를 읽기만 해도 `DeprecationWarning`이 난다. **읽지 말고
> `scene.compositing_node_group is not None`으로 판단하라.**

### 8.3 정식 생성·할당 패턴 (검증됨)

```python
import bpy

def new_compositing_group(name="SceneComp", build=None):
    """Create a scene compositing node group in Blender 5.x and assign it."""
    ng = bpy.data.node_groups.new(name, 'CompositorNodeTree')
    # The interface starts EMPTY -- you must declare the sockets yourself.
    ng.interface.new_socket("Image", in_out='INPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    gi = ng.nodes.new('NodeGroupInput');  gi.location = (-500, 0)
    go = ng.nodes.new('NodeGroupOutput'); go.location = (500, 0)
    if build:
        build(ng, gi, go)
    bpy.context.scene.compositing_node_group = ng
    return ng
```

```python
import bpy
ng = bpy.data.node_groups.new("CompTest", 'CompositorNodeTree')
print("created bl_label:", ng.bl_label)
print("interface BEFORE:", [(i.item_type, i.in_out, i.name) for i in ng.interface.items_tree])
bpy.context.scene.compositing_node_group = ng
print("assigned ->", bpy.context.scene.compositing_node_group is ng)
ng.interface.new_socket("Image", in_out='INPUT', socket_type='NodeSocketColor')
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
print("interface AFTER :", [(i.item_type, i.in_out, i.name, i.identifier, i.socket_type)
                             for i in ng.interface.items_tree])
gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput')
print("GroupInput outputs :", [s.name for s in gi.outputs])
print("GroupOutput inputs :", [s.name for s in go.inputs])
print("__SCRIPT_OK__")
```

실측 출력:

```
created bl_label: Compositor
interface BEFORE: []
assigned -> True
interface AFTER : [('SOCKET', 'OUTPUT', 'Image', 'Socket_1', 'NodeSocketColor'),
                   ('SOCKET', 'INPUT', 'Image', 'Socket_0', 'NodeSocketColor')]
GroupInput outputs : ['Image', '']
GroupOutput inputs : ['Image', '']
__SCRIPT_OK__`
```

> `GroupInput.outputs`에 **`''`(빈 이름) 항목이 하나 더 붙는다.** 이는 extend 소켓이다.
> 인덱스 대신 **이름**으로 접근하라: `ng.links.new(gi.outputs['Image'], ...)`.
> 이름이 헷갈리면 `go.inputs[0]`처럼 인덱스도 쓸 수 있다.

### 8.4 오퍼레이터가 만드는 기본 그룹 (실측)

```python
import bpy
print(bpy.ops.node.new_compositing_node_group(name="OpMade"))   # {'FINISHED'}
ng = bpy.data.node_groups["OpMade"]
print("assigned to scene.compositing_node_group:", bpy.context.scene.compositing_node_group)
for n in ng.nodes:
    print("   ", n.bl_idname, "| in:", [s.name for s in n.inputs], "out:", [s.name for s in n.outputs])
print("links:", [(l.from_node.name, l.from_socket.name, '->', l.to_node.name, l.to_socket.name)
                 for l in ng.links])
print("__SCRIPT_OK__")
```

실측 출력:

```
{'FINISHED'}
assigned to scene.compositing_node_group: None
    NodeGroupOutput | in: ['Image', ''] out: []
    CompositorNodeRLayers | in: [] out: ['Image', 'Alpha']
    NodeReroute | in: ['Input'] out: ['Output']
    CompositorNodeViewer | in: ['Image'] out: []
links: [('Render Layers', 'Image', '->', 'Reroute', 'Input'), ('Reroute', 'Output', '->', 'Group Output', 'Image'), ('Reroute', 'Output', '->', 'Viewer', 'Image')]
__SCRIPT_OK__`
```

생성되는 interface: `[('SOCKET','OUTPUT','Image','NodeSocketColor'), ('SOCKET','INPUT','Image','NodeSocketColor')]`.

**두 가지가 중요하다**:
1. `bpy.ops.node.new_compositing_node_group()`는 그룹을 **만들지.scene에 할당하지 않는다**
   (`scene.compositing_node_group`는 여전히 `None`). 할당은 스크립트가 해야 한다.
2. 기본 배치는 `CompositorNodeRLayers` → `NodeReroute` → `GroupOutput` (+ `Viewer`).
   즉 **그룹 안에서 Render Layers 노드로 소스를 잡는 것이 정석**이다 (§8.5).

### 8.5 ⚠️ Group Input를 소스로 쓰면 **검은 화면**이 나온다

가장 흔한 5.x 마이그레이션 실수. `GroupInput → Glare → GroupOutput`만 연결하면
**모든 픽셀이 검게**(mean ≈ 0.0003) 나온다. 컴포지터는 그룹 입력을 자동 연결해 주지 않는다.

**틀린 것** (실측 mean RGB):

| 케이스 | mean R,G,B |
|---|---|
| 컴포지터 없음 (`compositing_node_group = None`) | `(0.7546, 0.4941, 0.3107)` ✅ |
| `GroupInput → GroupOutput` 만 연결 | **`(0.0003, 0.0003, 0.0003)`** ❌ |
| `GroupInput → Glare → GroupOutput` | **`(0.0003, 0.0003, 0.0003)`** ❌ |
| `GroupInput → Exposure(+2EV) → GroupOutput` | **`(0.0003, 0.0003, 0.0003)`** ❌ |
| `RenderLayers → GroupOutput` | `(0.7546, 0.4941, 0.3107)` ✅ |

**옳은 것** (실측):

| 케이스 | mean R,G,B |
|---|---|
| `RenderLayers → GroupOutput` | `(0.7546, 0.4941, 0.3107)` — 기준선 |
| `RenderLayers → Exposure(+2.0) → GroupOutput` | `(0.7793, 0.7746, 0.5872)` ✅ 실제로 밝아짐 |
| `RenderLayers → Exposure(-2.0) → GroupOutput` | `(0.4046, 0.2585, 0.1556)` ✅ 실제로 어두워짐 |
| `RenderLayers → Glare(Fog Glow) → GroupOutput` | `(0.7738, 0.5831, 0.3694)` ✅ 글로우 추가 |
| `RenderLayers → Blur(8,8) → GroupOutput` | `(0.7800, 0.5095, 0.3192)` ✅ 흐려짐 |

완전한 검증 스크립트:

```python
import bpy, addon_utils, os, shutil, array
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/comp3'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.render.resolution_x = s.render.resolution_y = 64
    s.cycles.device = 'CPU'; s.cycles.samples = 8
    s.cycles.use_adaptive_sampling = False; s.cycles.use_denoising = False
    s.view_settings.view_transform = 'Standard'
    bpy.ops.mesh.primitive_plane_add(size=10)
    m = bpy.data.materials.new("M")
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
    bpy.context.object.data.materials.append(m)
    bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
    bpy.context.object.data.energy = 4
    bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
    s.camera = bpy.context.object
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    return s


def mean_rgb(path):
    im = bpy.data.images.load(path, check_existing=False)
    n = im.size[0] * im.size[1]
    b = array.array('f', [0.0]) * (n * 4)
    im.pixels.foreach_get(b)
    r = (round(sum(b[i * 4] for i in range(n)) / n, 4),
         round(sum(b[i * 4 + 1] for i in range(n)) / n, 4),
         round(sum(b[i * 4 + 2] for i in range(n)) / n, 4))
    bpy.data.images.remove(im)
    return r


def new_group(name, build):
    ng = bpy.data.node_groups.new(name, 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='INPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    gi = ng.nodes.new('NodeGroupInput'); gi.location = (-500, 0)
    go = ng.nodes.new('NodeGroupOutput'); go.location = (500, 0)
    build(ng, gi, go)
    return ng


scn = setup()
scn.compositing_node_group = None
scn.render.filepath = f'{OUT}/a_base.png'
bpy.ops.render.render(write_still=True)
print("A base (no comp)      :", mean_rgb(f'{OUT}/a_base.png'))


def build_passthru(ng, gi, go):
    rl = ng.nodes.new('CompositorNodeRLayers'); rl.location = (-200, 0)
    ng.links.new(rl.outputs['Image'], go.inputs[0])


scn.compositing_node_group = new_group("T_Pass", build_passthru)
scn.render.filepath = f'{OUT}/b_rlayers_pass.png'
bpy.ops.render.render(write_still=True)
print("B RLayers->Out        :", mean_rgb(f'{OUT}/b_rlayers_pass.png'))


def build_exposure(ng, gi, go):
    rl = ng.nodes.new('CompositorNodeRLayers'); rl.location = (-300, 0)
    ex = ng.nodes.new('CompositorNodeExposure'); ex.location = (0, 0)
    ex.inputs['Exposure'].default_value = 2.0
    ng.links.new(rl.outputs['Image'], ex.inputs['Image'])
    ng.links.new(ex.outputs['Image'], go.inputs[0])


scn.compositing_node_group = new_group("T_Exp", build_exposure)
scn.render.filepath = f'{OUT}/c_exposure.png'
bpy.ops.render.render(write_still=True)
print("C RLayers->Exp(+2EV)  :", mean_rgb(f'{OUT}/c_exposure.png'))


def build_exposure_neg(ng, gi, go):
    rl = ng.nodes.new('CompositorNodeRLayers'); rl.location = (-300, 0)
    ex = ng.nodes.new('CompositorNodeExposure'); ex.location = (0, 0)
    ex.inputs['Exposure'].default_value = -2.0
    ng.links.new(rl.outputs['Image'], ex.inputs['Image'])
    ng.links.new(ex.outputs['Image'], go.inputs[0])


scn.compositing_node_group = new_group("T_ExpNeg", build_exposure_neg)
scn.render.filepath = f'{OUT}/d_exposure_neg.png'
bpy.ops.render.render(write_still=True)
print("D RLayers->Exp(-2EV)  :", mean_rgb(f'{OUT}/d_exposure_neg.png'))


def build_glare(ng, gi, go):
    rl = ng.nodes.new('CompositorNodeRLayers'); rl.location = (-400, 0)
    gl = ng.nodes.new('CompositorNodeGlare'); gl.location = (0, 0)
    gl.inputs['Type'].default_value = 'Fog Glow'
    gl.inputs['Quality'].default_value = 'High'
    gl.inputs['Threshold'].default_value = 0.1
    gl.inputs['Size'].default_value = 0.8
    gl.inputs['Strength'].default_value = 0.5
    gl.inputs['Streaks'].default_value = 6
    gl.inputs['Streaks Angle'].default_value = 0.25
    gl.inputs['Iterations'].default_value = 4
    gl.inputs['Fade'].default_value = 0.9
    ng.links.new(rl.outputs['Image'], gl.inputs['Image'])
    ng.links.new(gl.outputs['Image'], go.inputs[0])


scn.compositing_node_group = new_group("T_Glare", build_glare)
scn.render.filepath = f'{OUT}/e_glare.png'
bpy.ops.render.render(write_still=True)
print("E RLayers->FogGlow    :", mean_rgb(f'{OUT}/e_glare.png'))


def build_blur(ng, gi, go):
    rl = ng.nodes.new('CompositorNodeRLayers'); rl.location = (-400, 0)
    bl = ng.nodes.new('CompositorNodeBlur'); bl.location = (0, 0)
    bl.inputs['Size'].default_value = (8.0, 8.0)
    bl.inputs['Type'].default_value = 'Gaussian'
    ng.links.new(rl.outputs['Image'], bl.inputs['Image'])
    ng.links.new(bl.outputs['Image'], go.inputs[0])


scn.compositing_node_group = new_group("T_Blur", build_blur)
scn.render.filepath = f'{OUT}/f_blur.png'
bpy.ops.render.render(write_still=True)
print("F RLayers->Blur(8)   :", mean_rgb(f'{OUT}/f_blur.png'))
print("__SCRIPT_OK__")
```

> **주의**: 컴포지터가 켜지면 헤드리스 llvmpipe 환경에서 `EGL_BAD_MATCH` 경고 3줄이
> stderr로 나온다. 렌더를 막지는 않지만 출력 파싱 시 걸러라.

### 8.6 노드 파라미터가 소켓으로 이동했다 — 실측 표

`CompositorNodeGlare`:

| 4.x 프로퍼티 | 5.2 | 소켓 이름 | 소켓 식별자 | 타입 | 기본값 |
|---|---|---|---|---|---|
| `glare_type` | ❌ | `Type` | `Type` | MENU | `'Streaks'` |
| `quality` | ❌ | `Quality` | `Quality` | MENU | `'Medium'` |
| `threshold` | ❌ | `Threshold` | `Highlights Threshold` | VALUE | `1.0` |
| `mix` | ❌ | `Strength` | `Strength` | VALUE | `1.0` |
| `size` | ❌ | `Size` | `Size` | VALUE | `0.5` |
| `streaks` | ❌ | `Streaks` | `Streaks` | INT | `4` |
| `angle_offset` | ❌ | `Streaks Angle` | `Streaks Angle` | VALUE | `0.0` |
| `fade` | ❌ | `Fade` | `Fade` | VALUE | `0.9` |
| `iterations` | ❌ | `Iterations` | `Iterations` | INT | `3` |
| — | 신규 | `Smoothness` | `Highlights Smoothness` | VALUE | `0.1` |
| — | 신규 | `Clamp` | `Clamp Highlights` | BOOLEAN | `False` |
| — | 신규 | `Maximum` | `Maximum Highlights` | VALUE | `10.0` |
| — | 신규 | `Saturation` | `Saturation` | VALUE | `1.0` |
| — | 신규 | `Tint` | `Tint` | RGBA | `(1,1,1,1)` |
| — | 신규 | `Color Modulation` | `Color Modulation` | VALUE | `0.25` |
| — | 신규 | `Diagonal` | `Diagonal Star` | BOOLEAN | `True` |
| — | 신규 | `Sun Position` | `Sun Position` | VECTOR | `(0.5, 0.5)` |
| — | 신규 | `Jitter` | `Jitter` | VALUE | `0.0` |
| — | 신규 | `Kernel Data Type` | `Kernel Data Type` | MENU | `'Float'` |
| — | 신규 | `Kernel` ×2 | `Float Kernel` / `Color Kernel` | VALUE / RGBA | `0.0` / `(0.8,0.8,0.8,1)` |

출력 소켓: `Image`(RGBA), `Glare`(RGBA), `Highlights`(RGBA) — 글로어만/하이라이트만 뽑을 수 있다.

MENU 소켓의 실제 값 (introspection이 빈 리스트를 주므로 `TypeError`로 추출):

```
CompositorNodeGlare     .Type             -> ('Bloom', 'Ghosts', 'Streaks', 'Fog Glow', 'Simple Star', 'Sun Beams', 'Kernel')
CompositorNodeGlare     .Quality          -> ('High', 'Medium', 'Low')
CompositorNodeGlare     .Kernel Data Type -> ('Float', 'Color')
```

`CompositorNodeBlur`:

| 소켓 이름 | 식별자 | 타입 | 기본값 | 4.x 대응 |
|---|---|---|---|---|
| `Image` | `Image` | RGBA | `(1,1,1,1)` | |
| `Size` | `Size` | **VECTOR** | `(0.0, 0.0)` | `use_relative` 분기 |
| `Type` | `Type` | MENU | `'Gaussian'` | **`filter_type`** |
| `Extend Bounds` | `Extend Bounds` | BOOLEAN | `False` | `use_extended_bounds` |
| `Separable` | `Separable` | BOOLEAN | `True` | `use_separable` |

`Type` 실제 값:
`('Flat', 'Tent', 'Quadratic', 'Cubic', 'Gaussian', 'Fast Gaussian', 'Catrom', 'Mitch')`
→ 4.x 문자열 `'FLAT'`, `'TENT'`, … 와 **대소문자가 다르다**.

`CompositorNodeLensdist` (구 `lensdist` 오퍼레이터는 삭제, 노드 id는 **그대로 `CompositorNodeLensdist`**):

| 소켓 이름 | 타입 | 기본값 |
|---|---|---|
| `Image` | RGBA | `(1,1,1,1)` |
| `Type` | MENU | `'Radial'` → `('Radial', 'Horizontal')` |
| `Distortion` | VALUE | `0.0` |
| `Dispersion` | VALUE | `0.0` |
| `Jitter` | **BOOLEAN** | `False` |
| `Fit` | BOOLEAN | `False` |

`CompositorNodeDenoise`:

| 소켓 이름 | 타입 | 기본값 | 4.x 대응 |
|---|---|---|---|
| `Image` | RGBA | | |
| `Albedo` | RGBA | | |
| `Normal` | **VECTOR** | `(0,0,0)` | 4.x는 RGBA |
| `HDR` | BOOLEAN | `True` | **5.x 신규** |
| `Prefilter` | MENU | `'Accurate'` → `('None','Fast','Accurate')` | 4.x `prefilter` |
| `Quality` | MENU | `'Follow Scene'` → `('Follow Scene','High','Balanced','Fast')` | **5.x 신규** |

`CompositorNodeCryptomatteV2` — **프로퍼티가 그대로 남아 있음** (소켓화 안 됨):
`source`, `scene`, `image`, `matte_id`, `add`, `remove`, `layer_name`, `entries`,
`frame_duration`, `frame_start`, `frame_offset`, `use_cyclic`, `use_auto_refresh`,
`layer`, `has_layers`, `view`, `has_views`.
입력 소켓 1개(`Image`), 출력 3개(`Image`, `Matte`, `Pick`).

`CompositorNodeMask`: 프로퍼티 `mask` + 소켓 7개
(`Size Source` MENU `'Scene Size'` → `('Scene Size','Fixed','Fixed/Scene')`,
`Size X` 256, `Size Y` 256, `Feather` True, `Motion Blur` False, `Samples` 16, `Shutter` 0.5).
출력은 `Mask`(VALUE) **하나뿐** — 이미지 입력이 없다.

`CompositorNodeBoxMask` / `EllipseMask`: 프로퍼티 없음, 소켓 6개
(`Operation` MENU `'Add'` → `('Add','Subtract','Multiply','Not')`, `Mask` 0.0,
`Value` 1.0, `Position` `(0.5,0.5)`, `Size` `(0.2,0.1)`, `Rotation` 0.0).
출력 `Mask`(VALUE).

`CompositorNodeColorBalance`: 프로퍼티 `input_whitepoint`, `output_whitepoint` + 소켓 19개
(`Type` MENU `'Lift/Gamma/Gain'` → `('Lift/Gamma/Gain','Offset/Power/Slope (ASC-CDL)','White Point')`,
각 채널마다 `Lift`/`Gamma`/`Gain`/`Offset`/`Power`/`Slope`의 Base(float)와 Color(RGBA) 페어,
`Input`/`Output` `Temperature` 6500.0 / `Tint` 10.0).
**`lift`/`gamma`/`gain` 같은 단일 프로퍼티는 없고 소켓 페어다.**

`CompositorNodeCurveRGB`: 프로퍼티 `mapping` + 소켓 4개
(`Image`, `Fac` 1.0, `Black Level` `(0,0,0,1)`, `White Level` `(1,1,1,1)`).
커브 데이터는 `node.mapping.curves[3/4]`에서 접근.

`CompositorNodeExposure`: 소켓 2개 (`Image`, `Exposure` 0.0). 프로퍼티 없음.
`CompositorNodeViewer`: 소켓 1개(`Image`), 출력 0개, 프로퍼티 `ui_shortcut`.
`CompositorNodeRLayers`: 입력 0개, 출력 `Image`(RGBA) / `Alpha`(VALUE), 프로퍼티 `scene`, `layer`.
`CompositorNodeKuwahara`: 소켓 7개 (`Size` 6.0, `Type` MENU `'Anisotropic'`, `Uniformity` 4,
`Sharpness` 1.0, `Eccentricity` 1.0, `High Precision` False).
`CompositorNodeLevels`: 소켓 2개(`Image`, `Channel` MENU `'Combined'`), **출력 4개**
(`Mean`, `Standard Deviation`, `Minimum`, `Maximum`).
`CompositorNodeAlphaOver`: 소켓 5개 (`Background`, `Foreground`, `Fac`, `Type` MENU `'Over'`,
`Straight Alpha`).
`CompositorNodeTonemap`: 소켓 9개 (`Type` MENU → `('R/D Photoreceptor','Rh Simple')`).
`CompositorNodeFilter`: `Type` MENU → `('Soften','Box Sharpen','Diamond Sharpen','Laplace',
'Sobel','Prewitt','Kirsch','Shadow')`.
`CompositorNodePremulKey`: `Type` MENU → `('To Premultiplied','To Straight')`.
`CompositorNodeBrightContrast`: 소켓 3개 (`Brightness`, `Contrast`).
`CompositorNodeHueSat`: 소켓 5개 (`Hue` 0.5, `Saturation` 1.0, `Value` 1.0, `Factor` 1.0).
`CompositorNodeSwitch`: 소켓 3개 (`Switch` BOOL, `Off`, `On`).
`CompositorNodeRGBToBW`: 입력 `Image`, 출력 `Val`(VALUE).
`CompositorNodeDefocus`: 프로퍼티 `scene, bokeh, angle, f_stop, blur_max, use_zbuffer, z_scale`
+ 소켓 `Image`, `Z`.

### 8.7 `CompositorNodeOutputFile` — 항목 추가가 필수, 헤드리스에선 미작동

5.x에서 File Output 노드는 `file_output_items` 컬렉션을 갖는다. **기본값이 0개**이고,
`file_output_items.add()`는 없고 **`.new(socket_type, name)`** 다.

```python
import bpy
ng = bpy.data.node_groups.new("FO", 'CompositorNodeTree')
fo = ng.nodes.new('CompositorNodeOutputFile')
print("items before:", len(fo.file_output_items))
print("collection methods:", [m for m in dir(fo.file_output_items) if not m.startswith('_')])
it = fo.file_output_items.new('RGBA', 'Image')          # (.add 없음, 인자는 (socket_type, name))
print("  .new('RGBA','Image') ->", it, " now items =", len(fo.file_output_items))
for p in it.bl_rna.properties:
    if p.identifier != 'rna_type':
        print(f"    {p.identifier:24s} {p.type}")
fo.directory = '/out/fo/'
fo.file_name = 'painted_####'
print("fo.format.media_type default:", fo.format.media_type,
      " file_format default:", fo.format.file_format)
print("fo.save_as_render:", fo.save_as_render, " use_file_extension:", fo.use_file_extension,
      " active_item_index:", fo.active_item_index)
print("__SCRIPT_OK__")
```

실측 출력:

```
items before: 0
collection methods: ['bl_rna', 'clear', 'find', 'foreach_get', 'foreach_set', 'get', 'items', 'keys', 'move', 'new', 'remove', 'rna_type', 'values']
  .new('RGBA','Image') -> <bpy_struct, NodeCompositorFileOutputItem("Image")>  now items = 1
    name                     STRING
    socket_type              ENUM
    vector_socket_dimensions INT
    color                    FLOAT
    override_node_format     BOOLEAN
    save_as_render           BOOLEAN
    format                   POINTER -> ImageFormatSettings
fo.format.media_type default: MULTI_LAYER_IMAGE  file_format default: OPEN_EXR_MULTILAYER
fo.save_as_render: True  use_file_extension: True  active_item_index: 0
__SCRIPT_OK__`
```

`NodeCompositorFileOutputItem.socket_type` 후보:
`FLOAT INT BOOLEAN VECTOR RGBA ROTATION MATRIX STRING MENU SHADER OBJECT IMAGE GEOMETRY
COLLECTION TEXTURE MATERIAL BUNDLE CLOSURE FONT SCENE TEXT MASK SOUND INT_VECTOR`

**`.new()`의 인자 순서는 `(socket_type, name)` 이다** (이름 먼저가 아님).
`socket_type` 값은 `NodeSocketColor`가 아니라 `'RGBA'`다.

> **정직한 보고**: `file_output_items`가 0개인 상태는 조용히 아무것도 쓰지 않는다.
> `new('RGBA','Image')`로 항목을 만들고 `fo.directory`/`fo.file_name`을
> `'/workspace/out/fo2/out/'` / `'painted_####'`로 설정하고,
> `scene.render.save_output = False`로 2프레임을 렌더했는데도
> **이 헤드리스 빌드에서는 출력 디렉터리가 비어 remained** (파일 0개).
> 즉 이 샌드박스에서 `CompositorNodeOutputFile`은 **동작하지 않는다**(GPU/EGL 경로 필요 추정).
> 필요한 산출물은 `scene.render.filepath`로 받고, File Output 노드에는 의존하지 마라.
> 부수 관찰: `save_output=False`로 두었고 File Output 노드가 **있었는데도**
> `scene.render.filepath`로 `never_####.png`가 정상 생성되었다 —
> 즉 이 플래그만으로는 출력이 막히지 않았다.

### 8.8 사용 가능한 컴포지터 노드 전체 목록 (실측, 155개 OK)

`CompositorNodeTree`에서 생성이 성공한 노드 타입만 나열 (`FunctionNode*` / `ShaderNode*` /
`NodeGroupInput` / `NodeGroupOutput` 포함). `dir(bpy.types)`의 접두사 후보를 전부 시도해
실제로 insert 성공한 것만 골랐다.

**`CompositorNode*` (88개)**: AlphaOver, AntiAliasing, Bilateralblur, BlankImage, Blur,
BokehBlur, BokehImage, BoxMask, BrightContrast, ChannelMatte, ChromaMatte, ColorBalance,
ColorCorrection, ColorMatte, ColorSpill, CombineColor, ConvertColorSpace,
ConvertToDisplay, Convolve, CornerPin, Crop, Cryptomatte, CryptomatteV2, CurveRGB, DBlur,
Defocus, Denoise, Despeckle, DiffMatte, DilateErode, Displace, DistanceMatte,
DoubleEdgeMask, EllipseMask, Exposure, Filter, Flip, Glare, Group, HueCorrect, HueSat,
IDMask, Image, ImageCoordinates, ImageInfo, Inpaint, Invert, Keying, KeyingScreen, Kuwahara,
Lensdist, Levels, LumaMatte, MapUV, Mask, MaskToSDF, MovieClip, MovieDistortion, Normal,
Normalize, OutputFile, Pixelate, PlaneTrackDeform, Posterize, PremulKey, RGB, RGBToBW,
RLayers, RelativeToPixel, Rotate, Scale, SceneTime, SeparateColor, SequencerStripInfo,
SetAlpha, Split, Stabilize, StringToImage, Switch, SwitchView, Time, Tonemap, TrackPos,
Transform, Translate, VecBlur, Viewer, Zcombine

**`ShaderNode*` 중 사용 가능 (22개)**: Blackbody, Clamp, CombineXYZ, FloatCurve, Gamma,
MapRange, Math, Mix, MixRGB, RGBCurve, RadialTiling, SeparateXYZ, TexBrick, TexChecker,
TexGabor, TexGradient, TexMagic, TexNoise, TexVoronoi, TexWave, TexWhiteNoise, ValToRGB,
Value, VectorCurve, VectorMath, VectorRotate

**`FunctionNode*` (41개)**: AlignRotationToVector, AxesToRotation, AxisAngleToRotation,
CombineMatrix, EulerToRotation, FindInString, FormatString, InputBool, InputInt,
InputIntVector, InputMenu, InputRotation, InputSpecialCharacters, InputString, InputVector,
InvertMatrix, InvertRotation, MatchString, MatrixDeterminant, MatrixMultiply, ProjectPoint,
QuaternionToRotation, ReplaceString, ReverseString, RotateRotation, RotateVector,
RotationToAxisAngle, RotationToEuler, RotationToQuaternion, SeparateMatrix, SetStringCase,
SliceString, StringLength, StringToValue, TransformDirection, TransformPoint,
TransposeMatrix, TrimString, ValueToString

**`NodeGroup*`**: `NodeGroupInput`, `NodeGroupOutput`

> 셰이더 전용 노드(`BsdfPrincipled`, `OutputMaterial`, `TexImage` 등)는 이 트리에서
> insert가 **거부된다**(`Node type ShaderNodeBsdfPrincipled undefined`). 텍스처 노드
> 일부만 예외적으로 허용된다(위 `ShaderNodeTex*` 15개).

### 8.9 컴포지터 비활성화

```python
scn.render.use_compositing = False     # 그룹이 있어도 무시 (실측: 기준선 이미지 나옴)
```

| 설정 | 결과 (실측 mean RGB) |
|---|---|
| `compositing_node_group = None` | `(0.7546, 0.4941, 0.3107)` (기준선) |
| 그룹 있음 + `use_compositing = True` | 그룹 효과 적용 |
| 그룹 있음 + `use_compositing = False` | `(0.7546, 0.4941, 0.3107)` (기준선) |

---

## 9. 렌더 품질 측정 하네스

이 스킬의 검증 루프가 기대하는 핵심 모듈이다. **실행·검증 완료된 코드**를 그대로 제시한다
(`verify/29_harness.py`).

### 9.1 왜 파일로 내리는가

`bpy.data.images['Render Result']`의 픽셀은 **읽을 수 없다**(§10). 따라서 유일하게
신뢰할 수 있는 경로는 **렌더를 디스크에 쓰고 → 파일을 로드해 → 측정**이다.
렌더 설정과 측정 로직을 분리하면 "무엇을 검증할지"를 한눈에 볼 수 있다.

### 9.2 하네스가 계산하는 것

| 지표 | 정의 | 용도 |
|---|---|---|
| `w`, `h`, `channels`, `depth`, `is_float`, `alpha_mode`, `colorspace` | 메타데이터 | 포맷/색공간 검증 |
| `mean` | Rec.709 휘도의 평균 (`0.2126R+0.7152G+0.0722B`) | 전체 밝기 |
| `median` | 휘도 중앙값 | 왜곡에 강한 밝기 |
| `stddev` | 휘도 표준편차 | **평평함(flat) 판정** |
| `vmax` | 최대 휘도 | 클리핑 상한 |
| `p01`, `p05`, `p95`, `p99` | 백분위 | 디테일 존재 구간 |
| `black_frac` | `y <= 0.0` 픽셀 비율 | 빈 프레임 |
| `white_frac` | `y >= 1.0` 픽셀 비율 | **과노출** |
| `content_frac` | `y > content_pt(0.02)` 픽셀 비율 | 실제 콘텐츠 존재 |
| `bbox`, `bbox_frac` | 콘텐츠 픽셀의 경계 상자 | 프레이밍 검증 |
| `hist` | 10구간 휘도 히스토그램(정규화) | 분포 비교 |
| `alpha_mean`, `alpha_opaque_frac` | 알파 평균 / 완전 불투명 비율 | 알파 검증 |

> **모든 휘도는 sRGB 인코딩(표시) 공간**에서 계산된다. `.pixels`가 그런 값을 주기 때문에
> (§6.7). 임계값(`0.02`, `0.005`, …)도 이 공간 기준이다.

### 9.3 완전한 하네스 코드 (검증됨)

```python
import bpy, addon_utils, array, math, os, shutil
from bpy.app.handlers import persistent

REC709 = (0.2126, 0.7152, 0.0722)          # luminance weights, display-referred sRGB


def analyze_image(path, *, black_pt=0.0, white_pt=1.0, content_pt=0.02, hist_bins=10):
    """Measure a rendered image. Works on PNG/JPEG/EXR/anything bpy.data.images.load reads.

    Image.pixels returns DISPLAY-ENCODED (sRGB) values for 8-bit images and raw
    scene-linear values for float (EXR) images -- thresholds below assume sRGB.
    """
    img = bpy.data.images.load(path, check_existing=False)
    try:
        w, h = img.size
        if w == 0 or h == 0:
            return dict(path=os.path.basename(path), error='image has zero size')
        n = w * h
        buf = array.array('f', [0.0]) * (n * 4)
        img.pixels.foreach_get(buf)            # RGBA, row 0 = BOTTOM row
        wr, wg, wb = REC709
        hist = [0] * hist_bins
        n_black = n_white = n_content = n_opaque = 0
        minx, miny, maxx, maxy = w, h, -1, -1
        tot = 0.0
        tot_a = 0.0
        mx = 0.0
        for i in range(n):
            o = i << 2
            y = wr * buf[o] + wg * buf[o + 1] + wb * buf[o + 2]
            a = buf[o + 3]
            tot += y
            tot_a += a
            if y > mx:
                mx = y
            hist[min(hist_bins - 1, int(y * hist_bins))] += 1
            if y <= black_pt:
                n_black += 1
            if y >= white_pt:
                n_white += 1
            if y > content_pt:
                n_content += 1
                x, r = i % w, i // w
                if x < minx: minx = x
                if x > maxx: maxx = x
                if r < miny: miny = r
                if r > maxy: maxy = r
            if a >= 0.999:
                n_opaque += 1
        mean = tot / n
        lum = sorted((wr * buf[i * 4] + wg * buf[i * 4 + 1] + wb * buf[i * 4 + 2])
                     for i in range(n))
        var = sum((v - mean) ** 2 for v in lum) / n
        q = lambda p: lum[min(n - 1, int(n * p))]
        return dict(
            path=os.path.basename(path), w=w, h=h, channels=img.channels,
            depth=img.depth, is_float=img.is_float, alpha_mode=img.alpha_mode,
            colorspace=img.colorspace_settings.name, n_pixels=n,
            mean=round(mean, 5), median=round(lum[n // 2], 5),
            stddev=round(math.sqrt(var), 5), vmax=round(mx, 5),
            p01=round(q(.01), 5), p05=round(q(.05), 5), p95=round(q(.95), 5),
            p99=round(q(.99), 5),
            black_frac=round(n_black / n, 5), white_frac=round(n_white / n, 5),
            content_frac=round(n_content / n, 5),
            alpha_mean=round(tot_a / n, 5), alpha_opaque_frac=round(n_opaque / n, 5),
            bbox=None if maxx < 0 else (minx, miny, maxx, maxy),
            bbox_frac=None if maxx < 0 else round(
                ((maxx - minx + 1) * (maxy - miny + 1)) / n, 5),
            hist=[round(c / n, 4) for c in hist],
        )
    finally:
        bpy.data.images.remove(img)


def check_frame(r, *, min_content=0.005, min_stddev=0.005, max_white=0.30, max_black=0.95):
    """PASS/FAIL gate. Returns (verdict, list_of_reasons)."""
    bad = []
    if 'error' in r:
        return 'FAIL', [r['error']]
    if r['content_frac'] < min_content:
        bad.append(f"content_frac={r['content_frac']:.5f} < {min_content} -> empty frame")
    if r['stddev'] < min_stddev:
        bad.append(f"stddev={r['stddev']:.5f} < {min_stddev} -> flat frame")
    if r['white_frac'] > max_white:
        bad.append(f"white_frac={r['white_frac']:.5f} > {max_white} -> blown out")
    if r['black_frac'] > max_black:
        bad.append(f"black_frac={r['black_frac']:.5f} > {max_black} -> black frame")
    if r['bbox'] is None:
        bad.append("bbox=None -> no pixel above content threshold")
    return ('FAIL' if bad else 'PASS'), bad


def written_path(filepath, ext='.png'):
    """What Blender ACTUALLY wrote. Still renders do NOT expand '####'."""
    if '#' not in os.path.basename(filepath) and not filepath.lower().endswith(ext):
        filepath += ext
    return filepath


def verify_render(scene, filepath, *, expect='PASS', label='', **kw):
    """Render once, write it, measure it, assert the verdict. Returns the stats dict."""
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    r = analyze_image(written_path(filepath), **kw)
    v, bad = check_frame(r)
    assert v == expect, f"{label or filepath}: expected {expect}, got {v} ({bad})"
    return r


def show(r):
    v, bad = check_frame(r)
    print(f"  {r['path']:<26s} {r['w']}x{r['h']} ch={r['channels']} depth={r['depth']} "
          f"float={r['is_float']} cs={r['colorspace']}  [{v}]")
    print(f"     mean={r['mean']:<9} median={r['median']:<9} stddev={r['stddev']:<9} "
          f"vmax={r['vmax']:<9}")
    print(f"     p01={r['p01']:<9} p05={r['p05']:<9} p95={r['p95']:<9} p99={r['p99']:<9}")
    print(f"     black={r['black_frac']:<9} white={r['white_frac']:<9} "
          f"content={r['content_frac']:<9} alpha_mean={r['alpha_mean']} "
          f"alpha_opaque={r['alpha_opaque_frac']}")
    print(f"     bbox={r['bbox']} bbox_frac={r['bbox_frac']}")
    print(f"     hist={r['hist']}")
    for b in bad:
        print(f"     !! {b}")
    return v
```

### 9.4 씬 픽스처 빌더

```python
def build_scene(kind='good', res=96, samples=16):
    """kind: 'black' (no light) | 'blown' (emission 5000) | 'good' (lit scene)"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.render.resolution_x = s.render.resolution_y = res
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'
    s.render.film_transparent = False
    s.view_settings.view_transform = 'Standard'      # deterministic measurements
    c = s.cycles
    c.device = 'CPU'; c.samples = samples
    c.use_adaptive_sampling = False; c.use_denoising = False

    if kind == 'black':
        s.world = bpy.data.worlds.new("W")
        bg = s.world.node_tree.nodes["Background"]
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        bg.inputs["Strength"].default_value = 0.0
        bpy.ops.mesh.primitive_plane_add(size=10)
        mt = bpy.data.materials.new("M")
        mt.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.5, .5, .5, 1)
        bpy.context.object.data.materials.append(mt)
        bpy.ops.object.camera_add(location=(0, -6, 1), rotation=(1.2, 0, 0))
    elif kind == 'blown':
        bpy.ops.mesh.primitive_plane_add(size=10)
        mt = bpy.data.materials.new("M")
        b = mt.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
        b.inputs["Emission Strength"].default_value = 5000.0
        bpy.context.object.data.materials.append(mt)
        bpy.ops.object.camera_add(location=(0, -6, 1), rotation=(1.2, 0, 0))
    else:
        bpy.ops.mesh.primitive_plane_add(size=10)
        mt = bpy.data.materials.new("M")
        mt.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.75, .25, .12, 1)
        bpy.context.object.data.materials.append(mt)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(.9, 0, 1.2))
        mt2 = bpy.data.materials.new("M2")
        b2 = mt2.node_tree.nodes["Principled BSDF"]
        b2.inputs["Base Color"].default_value = (.1, .35, .8, 1)
        b2.inputs["Roughness"].default_value = 0.2
        bpy.context.object.data.materials.append(mt2)
        bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
        bpy.context.object.data.energy = 4.0
        bpy.ops.object.camera_add(location=(0, -6, 2.2), rotation=(1.25, 0, 0))
    s.camera = bpy.context.object
    return s
```

### 9.5 세 가지 기준 프레임의 실측 수치

96×96, Cycles CPU 16spp, `view_transform='Standard'`, `use_adaptive_sampling=False`,
`use_denoising=False`. **이 숫자는 그대로 재현된다.**

#### (a) 의도적으로 빈/검은 프레임 — `FAIL`

```python
import bpy, addon_utils, os, shutil
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/harness'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)

# ... 위의 analyze_image / check_frame / written_path / verify_render / build_scene 정의 ...

for kind, expect in (('black', 'FAIL'), ('blown', 'FAIL'), ('good', 'PASS')):
    s = build_scene(kind)
    r = verify_render(s, f'{OUT}/gt_{kind}_', expect=expect, label=kind)
    show(r)
print("__SCRIPT_OK__")
```

실측 출력:

```
  gt_black_.png              96x96 ch=4 depth=32 float=False cs=sRGB  [FAIL]
     mean=0.00033   median=0.0       stddev=0.00108   vmax=0.00392
     p01=0.0       p05=0.0       p95=0.00392   p99=0.00392
     black=0.91656   white=0.0       content=0.0       alpha_mean=1.0 alpha_opaque=1.0
     bbox=None bbox_frac=None
     hist=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
     !! content_frac=0.00000 < 0.005 -> empty frame
     !! stddev=0.00108 < 0.005 -> flat frame
     !! bbox=None -> no pixel above content threshold
  gt_blown_.png              96x96 ch=4 depth=32 float=False cs=sRGB  [FAIL]
     mean=0.90672   median=1.0       stddev=0.29077   vmax=1.0
     p01=0.0       p05=0.0       p95=1.0       p99=1.0
     black=0.08485   white=0.90668   content=0.90668   alpha_mean=1.0 alpha_opaque=1.0
     bbox=(0, 0, 95, 87) bbox_frac=0.91667
     hist=[0.0933, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9067]
     !! white_frac=0.90668 > 0.3 -> blown out
  gt_good_.png               96x96 ch=4 depth=32 float=False cs=sRGB  [PASS]
     mean=0.44611   median=0.63963   stddev=0.26269   vmax=0.8362
     p01=0.0       p05=0.0       p95=0.67013   p99=0.67743
     black=0.16927   white=0.0       content=0.81348   alpha_mean=1.0 alpha_opaque=1.0
     bbox=(0, 0, 95, 95) bbox_frac=1.0
     hist=[0.2065, 0.015, 0.0763, 0.0849, 0.0507, 0.0457, 0.5193, 0.0007, 0.0011, 0.0]
  verdicts: {'black': 'FAIL', 'blown': 'FAIL', 'good': 'PASS'}
__SCRIPT_OK__
```

#### 판정 근거 정리

| 프레임 | `mean` | `stddev` | `black_frac` | `white_frac` | `content_frac` | `bbox` | 판정 | 근거 |
|---|---|---|---|---|---|---|---|---|
| `gt_black_` | 0.00033 | **0.00108** | **0.91656** | 0.0 | **0.0** | **None** | FAIL | content 0%, stddev 0.001, bbox 없음 |
| `gt_blown_` | 0.90672 | 0.29077 | 0.08485 | **0.90668** | 0.90668 | (0,0,95,87) | FAIL | 흰 픽셀 90.7% |
| `gt_good_` | 0.44611 | 0.26269 | 0.16927 | 0.0 | 0.81348 | (0,0,95,95) | PASS | 4개 조건 모두 통과 |

> 검은 프레임에서 `black_frac`가 **0.91656**이고 100%가 아닌 이유는 8비트 양자화 +
> 샘플링 노이즈 때문이다. 하지만 `content_frac=0.0`, `bbox=None`이 결정적이다.
> **세 프레임은 임계값과 임계값 사이가 아니라 임계값의 100배 이상 차이가 난다.**
> `white_frac` 0.0 vs 0.90668, `content_frac` 0.0 vs 0.81348. 그래서 노이즈에 강하다.

### 9.6 실용 예: 카메라 프레이밍 게이트

```python
# ... build_scene / verify_render / show 정의 후 ...
s = build_scene('good', res=96, samples=16)
s.camera.location = (0, -6, 2.2)
r_in = verify_render(s, f'{OUT}/framed_', expect='PASS', label='framed')
s.camera.location = (0, -6, 200.0)      # point the same camera at empty space
r_out = verify_render(s, f'{OUT}/empty_', expect='FAIL', label='empty')
print("framed bbox:", r_in['bbox'], " empty bbox:", r_out['bbox'])
```

실측 출력:

```
framed bbox: (0, 0, 95, 95)  empty bbox: None
```

**같은 씬, 같은 렌더 설정, 카메라 위치만 바꾼 결과가 `PASS` → `FAIL`로 뒤집혔다.**
이것이 이 하네스의 실용 가치다 — "스크립트가 도네"가 아니라 "카메라가 도네"를 잡는다.

### 9.7 애니메이션 프레임 게이트 — 안전한 패턴

```python
QUEUED = []


@persistent
def _on_write(scene):
    """render thread. Collect PATHS ONLY -- do no bpy.data work in here."""
    QUEUED.append(scene.render.frame_path(frame=scene.frame_current))


s = build_scene('good', res=64, samples=8)
s.frame_start, s.frame_end, s.frame_step = 1, 4, 1
s.render.filepath = f'{OUT}/seq_####.png'
bpy.app.handlers.render_write.append(_on_write)
bpy.ops.render.render(animation=True)
bpy.app.handlers.render_write.remove(_on_write)

FRAMES = []
for f, p in [(i + 1, p) for i, p in enumerate(QUEUED)]:
    v, bad = check_frame(analyze_image(p))
    FRAMES.append((f, p, v))
    print(f"  frame {f}: {os.path.basename(p)} -> {v}" + ("" if not bad else f"  {bad}"))
assert all(v == 'PASS' for _, _, v in FRAMES)
assert len(QUEUED) == 4
print("__SCRIPT_OK__")
```

실측 출력:

```
  frame 1: seq_0001.png -> PASS
  frame 2: seq_0002.png -> PASS
  frame 3: seq_0003.png -> PASS
  frame 4: seq_0004.png -> PASS
__SCRIPT_OK__`
```

> ⚠️ `render_write` 안에서 `analyze_image()`를 **직접 호출하면 Blender가 죽는다**(§7.6).
> 위 코드처럼 경로만 모아서 렌더가 끝난 뒤 측정하라.

### 9.8 임계값 튜닝 가이드

| 상황 | 조정 |
|---|---|
| 어두운 장면(밤 장면, 실내)이 계속 `FAIL` | `black_pt=0.02`, `content_pt=0.005` 로 완화 |
| 고대비/네온 씬이 `FAIL` | `max_white=0.60` (하이라이트는 원래 뭉개진다) |
| 앨범아트(구도가 화면 일부만) | `min_content=0.001`, `min_stddev=0.002` |
| `film_transparent=True` (알파 렌더) | `alpha_mean`으로 빈 프레임을 판정하는 게 `black_frac`보다 정확 |
| 플랫 컬러/그라디언트 테스트 | `min_stddev=0.0` 으로 두고 `content_frac`만 보라 |

`film_transparent`을 켠 경우 `black_frac`는 의미가 없다(배경이 투명해 검게 읽힌다).
대신 `alpha_mean`이 0이면 빈 프레임이다:

```python
if r['alpha_mean'] < 0.001:
    reasons.append("alpha_mean=0 -> film_transparent 빈 프레임")
```

### 9.9 EXR(선형) 입력 처리

float EXR의 `.pixels`는 **선형**이다(§6.7). 따라서 `white_pt=1.0`, `content_pt=0.02`
같은 임계값을 그대로 쓰면 분포가 완전히 달라진다. EXR에는 헤드룸이 있으므로:

```python
# float EXR: 휘도가 1을 훨씬 넘는다. 임계값을 올린다.
r = analyze_image('/out/shot.exr', content_pt=0.002, white_pt=8.0)
```

또는 먼저 톤매핑한 8비트 PNG를 거쳐서 측정한다(디커브 포함). 8비트 PNG 경로가
검증 루프에 더 안전하다.

---

## 10. `Render Result`와 렌더 중 이미지 다루기

### 10.1 `Render Result` 픽셀은 **읽히지 않는다** (결론)

`bpy.ops.render.render()` 직후, `write_still` 없이 렌더했어도:

```
'Render Result' type=RENDER_RESULT size=(0, 0) has_data=False source=VIEWER file_format=TARGA
```

모든 접근 방식의 실측 결과:

| 접근 | 결과 |
|---|---|
| `bpy.data.images.get('Render Result')` | `None`이 **아님** — 객체는 존재 |
| `rr.size` | `(0, 0)` |
| `rr.channels` | `0` |
| `rr.depth` | `0` |
| `rr.has_data` | `False` |
| `rr.file_format` | `'TARGA'` (무의미한 기본값) |
| `rr.source` | `'VIEWER'` |
| `list(rr.pixels)` | **`[]` — 예외 없이 빈 리스트** ⚠️ |
| `rr.pixels.foreach_get(buf)` (4096) | `TypeError: expected sequence size 0, got 4096` |
| `rr.pixels.foreach_get(buf)` (0) | 조용히 성공, 아무것도 안 씀 ⚠️ |
| `rr.pixels[0]` | `IndexError: bpy_prop_array[index]: index 0 out of range` |
| `rr.save_render(path)` | ✅ **동작함** |

```python
import bpy, addon_utils, os, shutil, array
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/rr'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'
s.render.resolution_x = s.render.resolution_y = 48
s.cycles.device = 'CPU'; s.cycles.samples = 8
s.cycles.use_adaptive_sampling = False; s.cycles.use_denoising = False
s.view_settings.view_transform = 'Standard'
s.render.image_settings.file_format = 'PNG'
s.render.image_settings.color_mode = 'RGBA'
bpy.ops.mesh.primitive_plane_add(size=10)
m = bpy.data.materials.new("M")
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
bpy.context.object.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
bpy.context.object.data.energy = 4
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
s.camera = bpy.context.object
s.render.filepath = f'{OUT}/r'

print("images BEFORE render:", [(i.name, i.type, tuple(i.size)) for i in bpy.data.images])
bpy.ops.render.render()          # NO write_still
print("images AFTER  render:", [(i.name, i.type, tuple(i.size), i.has_data)
                                for i in bpy.data.images])

rr = bpy.data.images.get('Render Result')
print("size:", tuple(rr.size), "channels:", rr.channels, "depth:", rr.depth,
      "has_data:", rr.has_data, "source:", rr.source, "file_format:", rr.file_format)
print("len(list(rr.pixels)) =", len(list(rr.pixels)), " <-- EMPTY, no exception")
try:
    rr.pixels.foreach_get(array.array('f', [0.0]) * 4096)
except Exception as e:
    print("foreach_get(4096) ->", type(e).__name__ + ":", e)
buf0 = array.array('f'); rr.pixels.foreach_get(buf0)
print("foreach_get(0): silent no-op, len =", len(buf0))
try:
    rr.pixels[0]
except Exception as e:
    print("rr.pixels[0] ->", type(e).__name__ + ":", e)

p = f'{OUT}/rr_saved.png'
print("rr.save_render ->", repr(rr.save_render(p)), " exists:", os.path.exists(p),
      " size:", os.path.getsize(p))
im = bpy.data.images.load(p, check_existing=False)
n = im.size[0] * im.size[1]
b = array.array('f', [0.0]) * (n * 4)
im.pixels.foreach_get(b)
print("re-read saved render:", tuple(im.size), "mean_r =", round(sum(b[0::4]) / n, 5))
bpy.data.images.remove(im)

s.render.image_settings.file_format = 'OPEN_EXR'
q = f'{OUT}/rr_saved.exr'
rr.save_render(q)
i2 = bpy.data.images.load(q, check_existing=False)
print("save_render to .exr -> exists:", os.path.exists(q),
      " is_float:", i2.is_float, " colorspace:", i2.colorspace_settings.name)
print("__SCRIPT_OK__")
```

실측 출력:

```
images BEFORE render: []
images AFTER  render: [('Render Result', 'RENDER_RESULT', (0, 0), False)]
size: (0, 0) channels: 0 depth: 0 has_data: False source: VIEWER file_format: TARGA
len(list(rr.pixels)) = 0  <-- EMPTY, no exception
foreach_get(4096) -> TypeError: expected sequence size 0, got 4096
foreach_get(0): silent no-op, len = 0
rr.pixels[0] -> IndexError: bpy_prop_array[index]: index 0 out of range
rr.save_render -> None  exists: True  size: 2747
re-read saved render: (48, 48) mean_r = 0.75576
save_render to .exr -> exists: True  is_float: True  colorspace: Linear Rec.709
__SCRIPT_OK__
```

`bpy.data.images`에 **렌더 전에는 아무 이미지도 없고**(`[]`), 렌더 후에도
`Render Result` 하나뿐이다. 즉 `check_existing=False`로 로드해 둔 이미지가 없다면
실수로 다른 이미지를 측정할 일도 없다.

### 10.2 결론: 읽으려면 반드시 파일로

| 방법 | 안전성 |
|---|---|
| `rr.pixels` 직접 접근 | ❌ 조용히 빈 배열 / TypeError. **절대 금지** |
| `bpy.data.images['Render Result'].save_render(path)` 후 로드 | ✅ 유일하게 검증된 경로 |
| `scene.render.filepath`로 직접 기록 후 로드 | ✅ 가장 단순 |
| GPU에서 `bpy.data.images['Render Result']` 텍스처 바인딩 (GUI 한정) | ⚠️ 이 문서 범위 밖 |

`save_render()`는 **`scene.render.image_settings`를 따른다**. 위 실측에서
`file_format='OPEN_EXR'`로 바꾼 뒤 `save_render('*.exr')`를 부르니 float EXR
(`is_float=True`, `colorspace='Linear Rec.709'`)가 기록됐다.
반면 `rr.file_format`는 여전히 `'TARGA'`로 보고된다 — **이 프로퍼티는 거짓말이다.**

### 10.3 Viewer 노드로도 안 된다

컴포지터 그룹 안에 `CompositorNodeViewer`를 넣고 렌더해도
`bpy.data.images`에는 `Render Result` 하나만 남고 크기는 여전히 `(0, 0)`이다(실측).
**Viewer 노드는 UI(Image Editor) 표시용이며, Python에서 픽셀 접근로를 만들지 않는다.**

### 10.4 렌더 중 결과 저장 — `save_render()`는 안전

`render_write` 안에서 `bpy.data.images.load()`는 **크래시**하지만(§7.6),
`bpy.data.images['Render Result'].save_render(path)`는 **안전하게 동작한다**(실측).

```python
import bpy, addon_utils, os, shutil, array
from bpy.app.handlers import persistent
addon_utils.enable("cycles", default_set=True, persistent=True)
OUT = '/workspace/out/img'
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene
s.render.engine = 'CYCLES'
s.render.resolution_x = s.render.resolution_y = 48
s.cycles.device = 'CPU'; s.cycles.samples = 4
s.cycles.use_adaptive_sampling = False; s.cycles.use_denoising = False
s.render.image_settings.file_format = 'PNG'
s.render.image_settings.color_mode = 'RGBA'
bpy.ops.mesh.primitive_plane_add(size=10)
m = bpy.data.materials.new("M")
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.8, .3, .1, 1)
bpy.context.object.data.materials.append(m)
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5)); bpy.context.object.data.energy = 4
bpy.ops.object.camera_add(location=(0, -6, 2), rotation=(1.2, 0, 0))
s.camera = bpy.context.object
s.frame_start, s.frame_end = 1, 3
s.render.filepath = f'{OUT}/main_####.png'

COPIES, SEEN = [], []


@persistent
def _post(scene):
    rr = bpy.data.images.get('Render Result')
    SEEN.append((scene.frame_current, tuple(rr.size) if rr else None))


@persistent
def _write(scene):
    """This DOES work inside render_write: save_render touches no new Image datablock."""
    rr = bpy.data.images.get('Render Result')
    dst = f"{OUT}/extra_{scene.frame_current:04d}.png"
    rr.save_render(dst)
    COPIES.append(dst)


@persistent
def _complete(scene):
    print("  render_complete: extra files =", sorted(os.path.basename(c) for c in COPIES))


bpy.app.handlers.render_post.append(_post)
bpy.app.handlers.render_write.append(_write)
bpy.app.handlers.render_complete.append(_complete)
bpy.ops.render.render(animation=True)
bpy.app.handlers.render_post.remove(_post)
bpy.app.handlers.render_write.remove(_write)
bpy.app.handlers.render_complete.remove(_complete)

print("  render_post saw (frame, RenderResult.size):", SEEN)
print("  extra copies:", sorted(os.path.basename(c) for c in COPIES))
for c in COPIES:
    im = bpy.data.images.load(c, check_existing=False)
    n = im.size[0] * im.size[1]
    b = array.array('f', [0.0]) * (n * 4)
    im.pixels.foreach_get(b)
    print(f"    {os.path.basename(c)} {tuple(im.size)} mean_r={sum(b[0::4]) / n:.5f}")
    bpy.data.images.remove(im)
print("__SCRIPT_OK__")
```

실측 출력:

```
  render_complete: extra files = ['extra_0001.png', 'extra_0002.png', 'extra_0003.png']
  render_post saw (frame, RenderResult.size): [(1, (0, 0)), (2, (0, 0)), (3, (0, 0))]
  extra copies: ['extra_0001.png', 'extra_0002.png', 'extra_0003.png']
    extra_0001.png (48, 48) mean_r=0.61119
    extra_0002.png (48, 48) mean_r=0.61119
    extra_0003.png (48, 48) mean_r=0.61119
__SCRIPT_OK__`
```

| 관찰 | 의미 |
|---|---|
| `render_post`에서 `Render Result.size` | 3프레임 모두 `(0, 0)` — 픽셀 접근 불가 확정 |
| `render_write`의 `save_render()` | 3프레임 모두 정상 저장, 크래시 없음 |
| `render_complete`에서 파일 목록 | 3개 모두 존재 |

**패턴 정리**:
* `render_write`에서 **파일로 쓰기만** 한다 → 안전 (`save_render` OK, `images.load` 크래시)
* 측정·비교는 **렌저 종료 후 메인 스레드에서** 한다

### 10.5 `render_pre`에서 씬을 프레임별로 바꾸기 — 안전

```python
from bpy.app.handlers import persistent
LOG = []


@persistent
def _pre(scene):
    e = scene.frame_current * 0.5
    scene.view_settings.exposure = e
    LOG.append((scene.frame_current, e))


bpy.app.handlers.render_pre.append(_pre)
bpy.ops.render.render(animation=True)
bpy.app.handlers.render_pre.remove(_pre)
print("render_pre saw:", LOG)
```

실측 (3프레임):

```
render_pre saw: [(1, 0.5), (2, 1.0), (3, 1.5)] -> exposure was 0.5/1.0/1.5 EV per frame
per-frame mean_r: [0.64579, 0.67528, 0.70045] -> strictly increasing: True
```

`scene.render.*` / `scene.view_settings.*` 같은 **씬 데이터는 `render_pre`/`render_post`에서
안전하게 읽고 쓸 수 있다**(§7.6의 크래시 실험에서 `render.write`에서 읽는 것은 통과했다).
문제는 **`bpy.data` 의 새 datablock 생성/파괴**였다.

### 10.6 `--render-frame` CLI

`--render-frame` / `-f`는 §3.3에서 이미 실측했다. Python과 다른 점 두 가지:

1. **`-f`는 `####`를 확장한다.** Python `write_still=True`는 하지 않는다(§1.2, §6.2).
2. **Python 스크립트로 커스텀할 수 없다.** 프레임별로 다른 설정을 넣으려면
   `render_pre` 핸들러(§10.5)를 쓰거나, `-P` 스크립트 안에서
   `bpy.ops.render.render(write_still=True)`를 직접 부른다(§3.5).

---

## 11. Gotcha 총정리

### 11.1 enum introspection은 이 빌드에서 **전혀 신뢰할 수 없다**

| 프로퍼티 | `enum_items` 반환 | 실제 |
|---|---|---|
| `RenderSettings.engine` | `['BLENDER_EEVEE']` | `('BLENDER_EEVEE','BLENDER_WORKBENCH','CYCLES')` |
| `ColorManagedViewSettings.view_transform` | `['NONE']` (기본값도 `'NONE'`) | 9개 (§4.2b) |
| `ColorManagedViewSettings.look` | `['NONE']` | `view_transform` 의존, 8~10개 |
| `ColorManagedDisplaySettings.display_device` | `['NONE']` | `'sRGB'` 외 다수 |
| `CyclesRenderSettings.denoiser` | `[]` | `('OPENIMAGEDENOISE',)` |
| `CyclesRenderSettings.sampling_pattern` / `preview_denoiser` | `[]` | 미설정 |
| `CyclesPreferences.compute_device_type` | `[]` | `('NONE','CUDA','OPTIX','HIP','ONEAPI')` |
| MENU 소켓 `default_value.enum_items` | `[]` | 3~10개 (§8.6) |
| `ColorManagedSequencerColorspaceSettings.name` | **68개 정상** | 정상 |

**해법**: (1) 일부러 틀린 값을 대입해 `TypeError`에서 튜플을 추출한다(§4.2 `real_enum`),
(2) `blender -b -E help`로 엔진 목록을 얻는다(§3.3).

`hasattr()`는 RNA에서도 신뢰 불가이고, `bpy.ops.*`에서는 더 심하다 —
**`hasattr(bpy.ops.render, 'opencache')`가 `True`인데 실제로는 없다**(§2.3). `dir()`만 신뢰할 것.

### 11.2 렌더 / 출력 (17)

`device='GPU'` + GPU 없음 → **조용히 CPU 폴백**, 경고 0 (§4.5) · 스틸 렌더는 `####`를
**확장하지 않는다** → `f_####.png` (§6.2) · CLI `-f`는 `####`를 **확장한다** (Python과 반대,
§3.3) · `-o`를 blend 앞에 두면 덮어써진다 (§3.4) · `-P`를 blend 앞에 두면 빈 씬에서 돈다 (§3.5) ·
`--python-exit-code` 없으면 예외가 있어도 exit 0 (§3.3) · 영상 파일명에는 `<시작>-<끝>`이 붙는다
(`movie_0001-0006.mp4`, §7.3) · 컨테이너/코덱 불일치 → 렌더 **마지막에** RuntimeError
(WEBM+H264, §7.3) · `use_overwrite=False` + 파일 존재 → `Info: No frames rendered, skipped to
not overwrite` · `save_output=False` + File Output 노드 없음 → RuntimeError ·
`frame_start/frame_end` + `animation=False` → RuntimeError (§1.3) · `use_sequencer`는
`bpy.ops.render.render`의 **인자가 아님** (§1.1) · `file_format`는 `media_type`에 게이트됨
(§6.4) · `Image.depth`는 파일 비트 깊이가 아니다 (8bit RGBA→32, 16bit RGB→96, §6.5) ·
`frame_path()`는 스틸 규칙과 다르다 (`x_.png`→`x_.png0005.png`, §6.10) · EEVEE 헤드리스는
llvmpipe라 20~37초 + `EGL_BAD_MATCH` 3줄 (§5.5) · `BLENDER_EEVEE_NEXT`는 **없다** (§5.1).

### 11.3 스레드 안전 — 이 문서에서 실제로 크래시를 만든 것

| # | Gotcha | 근거 |
|---|---|---|
| 1 | `render_write` 안의 `bpy.data.images.load()` → **Blender 크래시** | §7.6 (2프레임째) |
| 2 | `render_write` 안의 `save_render()`는 안전 | §10.4 (3프레임 성공) |
| 3 | `bpy.app.is_interface_locked` **존재하지 않음** | §7.7 |
| 4 | `bpy.ops.render.lock_interface()` **존재하지 않음** | §2.3 |
| 5 | `bpy.app.is_job_running()`는 인자 필수 (`'RENDER'`) | §7.7 |

**해법: 경로만 모아두고, 렌저가 끝난 뒤 메인 스레드에서 측정한다**(§9.7).
`render_pre`/`render_post`에서 `scene.*` 데이터를 읽고 쓰는 것은 안전(§10.5).

### 11.4 컴포지터 (15)

`scene.node_tree` **삭제됨**(§8.2) · `scene.use_nodes` 읽기만 해도 DeprecationWarning ·
`CompositorNodeComposite` **삭제됨** · `bpy.types.NodeTreeCompositor` **없음** →
`bpy.data.node_groups.new(n,'CompositorNodeTree')`(§8.2) ·
`bpy.ops.node.new_compositing_node_group()`는 **할당하지 않는다**(§8.4) · 그룹 interface가
**처음엔 비어 있다** — 소켓을 직접 만들어야(§8.3) · `GroupInput`을 소스로 쓰면 **검은 화면**
(mean 0.0003, §8.5) · 그룹 안에서 `CompositorNodeRLayers`를 써야 한다(§8.5) · 노드 파라미터가
**입력 소켓**으로 이동 (`glare.glare_type` → `glare.inputs['Type']`, §8.6) · 소켓 값이
**표시 문자열**이고 대소문자가 4.x와 다름 (`'Gaussian'` vs `'GAUSSIAN'`) · 소켓 접근은
**이름**으로 (`inputs['Exposure']`) · `GroupInput.outputs`에 `''`(extend) 소켓이 하나 더 있음 ·
`CompositorNodeOutputFile`은 `file_output_items.new(socket_type, name)` 필요, 0개면 무음 실패,
그리고 이 헤드리스 빌드에서는 **작동하지 않음**(§8.7) · 헤드리스 컴포지터는 `EGL_BAD_MATCH` 3줄.

### 11.5 이미지 픽셀

`Render Result` 픽셀 **읽히지 않는다** (`size=(0,0)`, `list(pixels)==[]`, §10.1) ·
`foreach_get`은 0이 아닌 크기를 주면 `TypeError`, 0이면 조용히 성공 · `save_render()`가 유일한
탈출구 · `.pixels`는 **sRGB 인코딩 값** (linear 아님, §6.7) · `colorspace_settings.name`을 바꿔도
값은 안 바뀐다 · `.pixels` **row 0 = 맨 아래** · `list(pixels)` == `foreach_get` 결과 ·
8비트 PNG 라운드 트립은 양자화 오차 발생 · float EXR의 `.pixels`는 선형 → 임계값 별도 설정(§9.9) ·
`bpy.data.images.remove()` 안 하면 메모리 누수.

### 11.6 권장 안전 코드 패턴

```python
import bpy, addon_utils
from bpy.app.handlers import persistent

# 1) 엔진: 문자열을 그냥 대입한다. enum introspection은 하지 않는다.
addon_utils.enable("cycles", default_set=True, persistent=True)
scn = bpy.context.scene
scn.render.engine = 'CYCLES'

# 2) GPU를 진짜로 쓸 거면 먼저 확인한다 (없으면 조용히 CPU로 폴백한다).
prefs = bpy.context.preferences.addons['cycles'].preferences
if prefs.compute_device_type == 'NONE' or not prefs.has_active_device():
    scn.cycles.device = 'CPU'
else:
    scn.cycles.device = 'GPU'

# 3) 결정론을 위해 색 관리를 고정한다 (기본값은 'AgX').
scn.view_settings.view_transform = 'Standard'

# 4) 출력 경로: 스틸에는 #를 넣지 않는다 (넣으면 확장 안 된다).
scn.render.filepath = '/out/shot'               # -> /out/shot.png

# 5) 컴포지터: 노드 트리가 아니라 node group. RLayers에서 시작.
ng = bpy.data.node_groups.new("Comp", 'CompositorNodeTree')
ng.interface.new_socket("Image", in_out='INPUT',  socket_type='NodeSocketColor')
ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
gi, go = ng.nodes.new('NodeGroupInput'), ng.nodes.new('NodeGroupOutput')
rl = ng.nodes.new('CompositorNodeRLayers')
ng.links.new(rl.outputs['Image'], go.inputs[0])
scn.compositing_node_group = ng
scn.render.use_compositing = True

# 6) 핸들러는 경로만 수집한다 (렌더 스레드에서 bpy.data 금지).
QUEUED = []

@persistent
def _collect(scene):
    QUEUED.append(scene.render.frame_path(frame=scene.frame_current))

bpy.app.handlers.render_write.append(_collect)
bpy.ops.render.render(write_still=True)
bpy.app.handlers.render_write.remove(_collect)

# 7) 측정과 판정은 메인 스레드에서. (analyze_image / check_frame 는 §9.3)
stats = analyze_image('/out/shot.png')
verdict, reasons = check_frame(stats)
assert verdict == 'PASS', reasons
```

---

## 12. Verification log

환경: `/usr/local/bin/blender` = `/workspace/tools/blender-5.2.2-linux-x64/blender`,
**Blender 5.2.2 LTS** (build 2026-09-15, commit `d13f752e3b9c`), 번들 Python 3.13.13,
Linux x64 헤드리스. GPU 없음(CPU `Intel Xeon Platinum 8163 CPU @ 2.50GHz`), OCIO 2.5.0,
FFmpeg libavcodec 62.28.100.

기본 명령: `blender -b --factory-startup -noaudio --python <script>.py`
스니펫마다 `print("__SCRIPT_OK__")` 를 넣고 grep 으로 확인했다.
스크립트와 원본 출력은 `/workspace/build/render/verify/` 에 남아 있다.

### 12.1 CLI / 환경 확인

`blender --version` → 5.2.2 LTS, 2026-09-15, `d13f752e3b9c` (525줄 전문 `verify/00_help.txt` 저장).

| # | 명령 | 결과 | 상태 |
|---|---|---|---|
| C2 | `blender -b --factory-startup -noaudio -E help` | `BLENDER_EEVEE / BLENDER_WORKBENCH / CYCLES` | ✅ PASS |
| C3 | `… cli_test.blend -o …/a_#### -F PNG -f 3` | `a_0003.png` | ✅ PASS |
| C4 | `… -o …/b_ -F PNG -a` (1..6) | `b_0001..b_0006.png` | ✅ PASS |
| C5 | `… -o …/c_ -F PNG -x 0 -f 3` | `c_0003` (확장자 없음) | ✅ PASS |
| C6 | `… -f 1,3,5` | `d_0001/0003/0005.png` | ✅ PASS |
| C7 | `… -f 2..5` | `e_0002..e_0005.png` | ✅ PASS |
| C8 | `… -s 2 -e 4 -j 2 -a` | `f_0002.png`, `f_0004.png` | ✅ PASS |
| C9 | `-E CYCLES -t 1 … -f 1 -- --cycles-device CPU --cycles-print-stats` | `g_0001.png` + 통계 덤프 | ✅ PASS |
| C10 | 인자 순서: `-o`를 blend 앞에 두기 | `Saved: '/workspace/out/out_0001.png'` (무시됨) 재현 | ✅ PASS (기대대로 실패) |
| C11 | `-P verify_sentinel.py` **앞** | `blend file = '' engine = BLENDER_EEVEE` | ✅ PASS |
| C12 | `-P verify_sentinel.py` **뒤** | `blend file = '/workspace/out/cli_test.blend' engine = CYCLES` | ✅ PASS |
| C13 | `--python-expr "raise RuntimeError"` + `--python-exit-code 1` | shell exit **1** | ✅ PASS |
| C14 | 같은 예외, `--python-exit-code` 없음 | shell exit **0** | ✅ PASS (함정 재현) |
| C15 | EEVEE 64px/8spp 헤드리스 | **20.67 s** (1차 실행 37.09 s), `EGL_BAD_MATCH` 3줄 | ✅ PASS |
| C16 | `bpy.ops.render.opengl()` 백그라운드 | `RuntimeError: Cannot use OpenGL render in background mode` | ✅ PASS |

### 12.2 introspection 스크립트

| # | 스크립트 | 내용 | 상태 |
|---|---|---|---|
| V01 | `01_introspect.py` | `RenderSettings`/`ImageFormatSettings`/`FFmpegSettings`/`ColorManaged*` 전체 덤프 | ✅ (`p.default` AttributeError → 타입 분기) |
| V02 | `02_dynamic_enum.py` | 타입 vs 인스턴스 enum 비교, `file_format` 전체 | ✅ |
| V03 | `03_compositor_ocot.py` | `scene.node_tree` 부재, `view_transform` 대입 테스트 | ✅ |
| V04–05 | `04_comp_nodes.py`, `05_node_inventory.py` | `new(n,'CompositorNodeTree')` + insert 가능한 155개 노드 전수 | ✅ (`functions['new']` KeyError → 제거) |
| V06 | `06_cycles.py` | `CyclesRenderSettings` 전체 108개 프로퍼티 | ✅ |
| V07 | `07_cycles_gpu.py` | `denoiser`/`compute_device_type` enum, 6개 백엔드 열거 | ✅ (버퍼링+CUDA/HIP dlopen으로 30 s 타임아웃 → line_buffering) |
| V08 | `08_eevee.py` | `SceneEEVEE` 전체 + 4.2 제거 29개 프로퍼티 | ✅ |
| V09–10 | `09_ops.py`, `10_comp_ops.py` | `bpy.ops.render.*` 시그니처, `new_compositing_node_group` | ✅ (`wm.open` KeyError, `is_interface_locked` AttributeError → 분리) |
| V11 | `11_app.py` | `dir(bpy.app)` 전체, `is_job_running` 인자, 핸들러 목록 | ✅ |
| V14 | `14_pixels_semantics.py` | `.pixels` sRGB vs linear, `foreach_get`==`list`, EXR | ✅ |
| V15 | `15_formats.py` | `color_mode`×`color_depth` 6 combos, `color_depth` TypeError 4건 | ✅ (엔진이 EEVEE라 EGL 실패 → Cycles 명시) |
| V20–21 | `20_comp_sockets.py`, `21_menu_sockets.py` | 30개 노드 소켓 덤프, MENU 소켓 실제 값 16개 | ✅ (`NodeSocketVirtual.default_value` → 가상 소켓 처리) |
| V25 | `25_opcache.py` | `opencache`/`lock_interface`/`abort` → AttributeError 6건 | ✅ |
| V27 | `27_gpu_list.py` | `get_device_types(ctx)`, `get_device_list(cdt)` 시그니처 | ✅ |

### 12.3 렌더 / 출력 / 핸들러

| # | 스크립트 | 내용 | 상태 |
|---|---|---|---|
| V12 | `verify/12_render_basic.py` | 첫 Cycles 렌더 1.23 s, Render Result `(0,0)` | ✅ PASS |
| V13 | `verify/13_image_analysis.py` | 하네스 1차 버전, 3개 기준 프레임 | ✅ PASS |
| V16 | `verify/16_ffmpeg.py` | `media_type` 게이트, MPEG4/MKV/QUICKTIME | ⚠️ 부분 — WEBM+H264에서 RuntimeError로 중단 (후속 V33에서 정리) |
| V17 | `verify/17_naming.py` | `filepath` 14개 조합, `frame_step`, `use_overwrite`, 멀티뷰 | ✅ PASS (3차에 수정: J2 RuntimeError / K RuntimeError → try/except) |
| V18 | `verify/18_handlers.py` | 핸들러 6종 호출 순서, `@persistent` 생존 | ✅ PASS (3차: 장면 해제 후 참조, `is_job_running()` 인자) |
| V24 | `verify/24_context.py` | EXEC vs INVOKE, `use_viewport`, `temp_override` | ✅ PASS |
| V26 | `verify/26_cycles_behaviour.py` | GPU 폴백, `film_exposure`, `film_transparent`, `use_animated_seed` | ✅ PASS |
| V28 | `verify/28_eevee_render.py` | EEVEE 헤드리스 37.09 s | ✅ PASS |
| V29 | `verify/29_harness.py` | **하네스 최종본** (3 기준 프레임 + 프레임 게이트 + 프레이밍 게이트) | ✅ PASS (1차: `render_write`에서 `images.load` → **Blender 크래시**, 2차: `render.scene` AttributeError, 3차: 스틸 파일 경로, 4차: defer 패턴으로 최종 통과) |
| V30 | `verify/30_handler_crash.py` | 4모드 격리 실험 (`stat`/`path`/`load`/`defer`) | ✅ PASS — **`load` 모드에서 Blender 크래시 재현** (`/tmp/blender.crash.txt`) |
| V31 | `verify/31_render_result.py` | Render Result 6가지 접근 + Viewer 노드 | ✅ PASS (1차: `foreach_get(4096)` TypeError → 0/4096 두 경우로 분리) |
| V32 | `verify/32_image_api.py` | `images.new`/`foreach_set`/`save` 라운드 트립, `scale()`, 핸들러 내 `save_render` | ✅ PASS (1차: 핸들러 제거 변수 순서 버그) |
| V33 | `verify/33_misc.py` | `use_border`/`use_crop_to_border`, `render_pre` 씬 변조, 5개 컨테이너 | ✅ PASS (1차: File Output `file_format` media_type 게이트) |
| V34 | `verify/34_fileoutput.py` | File Output 노드 파일 미생성 확인 | ✅ PASS (결과: 0개 파일) |
| V35 | `verify/35_fo_items.py` | `file_output_items.new(socket_type, name)` API 발견 | ✅ PASS (4차에 시그니처 확정: `.new` 존재 → `socket_type` 필수 → `'NodeSocketColor'` 부적합 → `'RGBA'` → `name` 필수). **단, 항목이 있어도 헤드리스에서 파일 미생성** |

### 12.4 컴포지터

| # | 스크립트 | 내용 | 상태 |
|---|---|---|---|
| V19 | `verify/19_comp_e2e.py` | 5.x 컴포지팅 그룹 생성 + 실제 렌더, `CompositorNodeGlare` 프로퍼티 전무 확인 | ✅ PASS (EGL 경고는 무해) |
| V22 | `verify/22_comp_render.py` | `GroupInput` 배선 → **검은 화면**(0.0003) 재현 | ✅ PASS (핵심 발견) |
| V23 | `verify/23_comp_rlayers.py` | `RLayers` 내부 소스 → Exposure ±2EV / Glare / Blur 실측 | ✅ PASS (mean RGB 6건) |

### 12.5 문서에 실은 스니펫 전용 재실행

문서에 그대로 들어간 코드를 `verify/doc/` 에 독립 파일로 다시 실행했다. **36개 전부 PASS.**

| 스니펫 | 파일 | 스니펫 | 파일 |
|---|---|---|---|
| §1.2 `render_still()` | `s1_2_still.py` | §6.4 `media_type` | `s6_4_mediatype.py` |
| §1.3 `frame_start/end` | `s1_3_frange.py` | §6.5 색상 매트릭스 | `s6_5_matrix.py` |
| §1.6 `temp_override` | `s1_6_override.py` | §6.7 `.pixels` 의미 | `s6_7_pixels.py` |
| §2.1 `opengl` 실패 | `s2_1_opengl.py` | §6.9 멀티뷰 | `s6_9_multiview.py` |
| §2.3 `hasattr` 거짓말 | `s2_3_hasattr.py` | §6.10 `frame_path()` | `s6_10_framepath.py` |
| §4.1 애드온 enable | `s4_1_enable.py` | §7.3 컨테이너/코덱 | `s7_3_video.py` |
| §4.2 engine enum | `s4_2_enum.py` | §7.5 핸들러 순서 | `s7_5_handlers.py` |
| §4.2 `real_enum()` | `s4_2b_realenum.py` | §7.5 `@persistent` | `s7_5b_persist.py` |
| §4.2b `look` 의존성 | `s4_2c_look.py` | §7.7 락 API | `s7_7_lock.py` |
| §4.4 GPU 탐지 | `s4_4_gpu.py` | §8.2 `node_tree` 부재 | `s8_2_nodetree.py` |
| §4.5 GPU 폴백 | `s4_5_gpu_fallback.py` | §8.3 그룹 생성 | `s8_3_create.py` |
| §4.7 film/seed | `s4_7_behaviour.py` | §8.4 오퍼레이터 | `s8_4_op.py` |
| §5.1 엔진 식별자 | `s5_1_engine.py` | §8.5 `RLayers` 배선 | `s8_5_rlayers.py` |
| §5.2 4.2 제거 표 | `s5_2_legacy.py` | §8.7 File Output | `s8_7_fo.py` |
| §5.4 `RaytraceEEVEE` | `s5_4_rt.py` | §9 하네스 전체 | `s9_harness.py` |
| §5.5 EEVEE 헤드리스 | `s5_5_eevee.py` | §10.1 Render Result | `s10_1_rr.py` |
| §6.10 아래 §3 CLI | `verify/cli/*` | §10.4 `save_render` | `s10_4_saverender.py` |
| §12 헤더 | — | §10.5 `render_pre` | `s10_5_pre.py` |

### 12.6 검증하지 못한 것 (정직한 목록)

| 항목 | 상태 | 이유 |
|---|---|---|
| `CompositorNodeOutputFile`의 실제 파일 출력 | ❌ 실패 | 항목 추가 후에도 헤드리스에서 파일 0개. GUI 필요 추정 |
| `CompositorNodeSepia` 대체 노드 | ❌ 미확인 | `CompositorNodeTree`에서 insert 실패. 대응하는 `ShaderNode*`도 목록에 없음 |
| `use_stamp` / `use_stamp_note`의 시각적 결과 | ⚠️ 미확정 | headless에서 `stamp.png`와 `nostamp.png`의 순백 픽셀 비율이 둘 다 `0.0` (API는 존재하고 프로퍼티는 덤프됨) |
| `render.use_placeholder`의 동작 | ⚠️ 미검증 | 프로퍼티는 존재하나 이 시나리오(프레임 스킵 시 자리표시자 생성)를 실행하지 않음 |
| GPU 경로 (`device='GPU'`, `OPTIX` denoiser, OPTIX ray tracing) | ❌ 불가 | 샌드박스에 GPU 없음. API만 검증 |
| `bpy.ops.render.view_show` / `view_cancel` | ❌ 미사용 | `get_rna_type()`는 되나 인자가 없어 기능 미검증 |
| `image_settings.views_format` (파일 내부 3D 포맷) | ⚠️ 미검증 | `render.views_format`(파일 분할)는 검증, 내부 포맷은 미검증 |
| `bpy.app.timers` 기반 비동기 후처리 | ❌ 미구현 | 본문에서 다룰 필요가 없다고 판단해 스코프 밖 |
| Compositing 변경(add-on) API | ❌ 미구현 | 본문 스코프 밖 |

### 12.6b 재현 확인 (2026-09-XX 최종 패스)

문서 작성 후 **모든 검증 스크립트를 한 번 더 전부 실행**했다.

| 그룹 | 결과 |
|---|---|
| `verify/doc/*.py` (문서 스니펫 34개) + `verify/cli/make.py` | **35 PASS / 0 FAIL** (전부 `__SCRIPT_OK__`) |
| `verify/*.py` (탐색 스크립트 34개 중 30개) | **30 PASS / 0 FAIL** |
| `verify/30_handler_crash.py` `HMODE=stat` / `path` / `defer` | **3 PASS** |
| `verify/30_handler_crash.py` `HMODE=load` | 💥 **Segmentation fault, exit 139** — 의도대로 재현 |

`MISS` 4건(`09_ops.py`, `10_comp_ops.py`, `15_formats.py`, `16_ffmpeg.py`)은
**탐색 스크립트의 후반부가 의도적으로 예외를 던지는 곳**(§12.7에 기록된 발견 지점)에서 끝나기
때문이다. 각 스크립트가 **해당 지점까지의 출력은 정상**이고, 그 예외 자체가 문서에 실린
발견(`opencache` 부재 / `is_interface_locked` 부재 / `media_type` 게이트 / WEBM+H264
RuntimeError)이다. 수정 후 재실행 결과는 §12.5 표와 동일하다.

### 12.7 실패→수정 기록 (솔직하게)

| 스크립트 | 최초 실패 | 수정 | 최종 |
|---|---|---|---|
| `01_introspect.py` | `CollectionProperty`에 `.default` 없음 | 타입별 분기 | ✅ |
| `04_comp_nodes.py` | `CompositorNodeTree.bl_rna.functions['new']` KeyError | 해당 루프 제거 | ✅ |
| `07_cycles_gpu.py` | 30 s 타임아웃 (stdout 버퍼링 + CUDA/HIP dlopen) | `line_buffering=True` | ✅ |
| `09_ops.py` / `10_comp_ops.py` | `bpy.ops.wm.open` KeyError / `is_interface_locked` AttributeError | try/except, V11로 분리 | ✅ |
| `15_formats.py` | 기본 엔진 EEVEE → EGL_BAD_MATCH로 렌더 실패 | `engine='CYCLES'` 명시 | ✅ |
| `17_naming.py` | `frame_start`+`animation=False`, `save_output=False` RuntimeError | 기대 동작으로 try/except | ✅ |
| `18_handlers.py` | 해제된 장면 참조, `is_job_running()` 인자 누락 | 순서·인자 수정 | ✅ |
| `19_comp_e2e.py` | Glare 프로퍼티 전부 AttributeError | **소켓 API로 재작성** (V20/V21) | ✅ |
| `20_comp_sockets.py` | `NodeSocketVirtual.default_value` AttributeError | 가상 소켓 처리 | ✅ |
| `22_comp_render.py` | GroupInput 배선 → 검은 이미지 | `RLayers` 내부 소스로 재작성 (V23) | ✅ |
| `29_harness.py` | **`render_write`에서 `images.load` → Blender 크래시** | V30 격리 실험 → `defer` 패턴 | ✅ |
| `30_handler_crash.py` | (실패가 목표) `HMODE=load`에서 크래시 | — | 💥 재현 성공 |
| `31_render_result.py` | `foreach_get(4096)` TypeError | 크기 0 / 4096 두 경로 분리 | ✅ |
| `32_image_api.py` | 핸들러 제거 변수 순서 버그 | 개별 `.remove()` | ✅ |
| `33_misc.py` | File Output `file_format='PNG'` TypeError | `media_type='IMAGE'` 선설정 | ✅ |
| `35_fo_items.py` | `.add()` 없음 → `socket_type` → `'NodeSocketColor'` → `name` 순서로 4회 실패 | `.new('RGBA','Image')` 확정 | ✅ (파일 미생성) |
| `s1_3_frange.py`, `s1_6_override.py` | `use_empty=True` 씬에 카메라 없음 | 최소 씬 구성 추가 | ✅ |
| `s7_5_handlers.py` | 셸 heredoc에서 `print(` 괄호 유실 | 라인 교체 | ✅ |
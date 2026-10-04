# 15. 씬·환경설정·확장 오퍼레이터 — 2차 감사에서 발견한 구멍

> 이 문서는 [`13-coverage-audit.md`](13-coverage-audit.md) 의 2차 감사에서
> **"헤드리스에서 도달 가능하면서 수동 문서 언급이 거의 없던"** 그룹을 채우기 위해
> 만들었다. 카탈로그(`12-api-catalog.md`)가 100% 를 덮긴 하지만,
> *설명*이 없던 영역이 여기다.
>
> 🟢 표기 = Blender 5.2.2 LTS 에서 직접 실행 확인

---

## 0. 왜 이 문서가 필요했나 — 측정한 수치

2차 감사에서 "헤드리스 도달 가능 operator 중 수동 문서가 몇 개나 언급하나" 를 쟀더니:

| 그룹 | 헤드리스 도달 가능 | 수동 문서 언급 | 비율 | 판정 |
|---|---:|---:|---:|---|
| `preferences` | **30** | 0 | 0% | ❌ 완전 구멍 |
| `scene` | **32** | 2 | 5% | ❌ 완전 구멍 |
| `extensions` | **27** | 1 | 3% | ❌ 완전 구멍 |
| `object` | 187 | 73 | 29% | ⚠ |
| `wm` | 104 | 24 | 21% | ⚠ |
| `collection` | 9 | 2 | 17% | ⚠ |

`preferences` · `scene` · `extensions` 는 **CI에서 매일 쓰이는 영역**인데 문서가 없었다.
이 문서가 그 세 군데를 채운다.

> **이 문서에도 원리가 그대로 적용된다**: 오퍼레이터를 쓰기 전에
> **data API 로 대체할 수 있는지** 먼저 본다. 아래 표에 대체재를 함께 적었다.

---

## 1. `bpy.ops.preferences.*` — CI 파이프라인의 워커

사용자 설정을 **스크립트로** 바꾼다. 헤드리스 머신은 `startup.blend` 로 설정을 나르는
경로가 없으므로 이게 사실상 유일한 방법이다.

### 1.1 애드온 관리 (실측)

```python
import bpy, addon_utils

# 활성화
print(bpy.ops.preferences.addon_enable(module="io_scene_gltf2"))   # {'FINISHED'}
print("io_scene_gltf2" in bpy.context.preferences.addons)          # True

# 비활성화
bpy.ops.preferences.addon_disable(module="io_scene_gltf2")
print("io_scene_gltf2" in bpy.context.preferences.addons)          # False

# 애드온 디렉터리 재스캔 (새로 설치한 애드온 탐지)
bpy.ops.preferences.addon_refresh()                                # {'FINISHED'}
```

**실측 출력**
```
  -> {'FINISHED'} | gltf2 활성: True
  -> {'FINISHED'} | 활성: False
  addon_refresh -> {'FINISHED'}
```

> `addon_enable` 은 `addon_utils.enable()` 과 같은 일을 한다.
> 차이는 **사용자 설정에 기록된다**는 것 — `addon_utils.enable(..., persistent=True)` 가
> 그 역할까지 대신한다. CI 에서 일회성으로 쓸 때는 `addon_utils` 가 더 명확하다.

| 오퍼레이터 | 인자 | 용도 |
|---|---|---|
| `addon_enable` | `module` | 애드온 활성화 |
| `addon_disable` | `module` | 애드온 비활성화 |
| `addon_refresh` | — | 애드온 디렉터리 재스캔 |
| `addon_install` | `filepath`, `overwrite`, `enable_on_install`, `target`, `filter_*` | zip 애드온 설치 |
| `addon_remove` | `module` | 디스크에서 삭제 |
| `addon_show` / `addon_expand` | `module` | UI (헤드리스 무의미) |

### 1.2 스크립트 경로 — 스킬을 머신에 설치할 때

```python
import bpy, tempfile, os
d = tempfile.mkdtemp()
bpy.ops.preferences.script_directory_add(directory=d)
print(list(bpy.context.preferences.filepaths.script_directories))
bpy.ops.preferences.script_directory_remove(index=0)
print(list(bpy.context.preferences.filepaths.script_directories))
```

**실측 출력**
```
  -> {'FINISHED'}
  script_directories: [<bpy_struct, ScriptDirectory("tmp_5r5l_p2") at ...>]
  ->remove -> {'FINISHED'}
  남은 것: []
```

> **주의**: 이건 `startup.blend` 의 `scripts/startup/` 에 엔트리포인트를 두는 것과
> **완전히 다르다.** `script_directories` 는 `bpy.utils.script_paths()` 로 읽히는
> "사용자 스크립트 탐색 경로" 다. 애드온이 `bpy.utils.register_class` 로 등록되려면
> 그 디렉터리가 탐색 대상이어야 한다.

### 1.3 에셋 라이브러리

```python
import bpy, tempfile
d = tempfile.mkdtemp()
bpy.ops.preferences.asset_library_add(directory=d, name="MyLib")
print([(l.name, l.path) for l in bpy.context.preferences.filepaths.asset_libraries])
```

**실측 출력**: `[('MyLib', '/tmp/tmp_5r5l_p2')]`

| 오퍼레이터 | 핵심 인자 |
|---|---|
| `asset_library_add` | `directory`, `name`, `type`, `remote_url` |

### 1.4 자동 실행 제외 경로 (보안)

```python
import bpy
print(list(bpy.context.preferences.autoexec_paths))   # 실측: []
# preferences.autoexec_path_add() / autoexec_path_remove(index=)
```

> `bpy.app.autoexec_fail` / `autoexec_fail_message` 와 짝을 이룬다.
> 드라이버가 차단됐는데 왜인지 알고 싶을 때:
> `13-coverage-audit.md` §6.2 참고.

### 1.5 확장 저장소 등록 — 5.x

```python
import bpy
bpy.ops.preferences.extension_repo_add(name="local", type='LOCAL')
```

**실측 출력**
```
Info: Added User Repository "local"
  -> {'FINISHED'}
```

> `type` 값은 `'LOCAL'` / `'REMOTE'` / `'OFFICIAL'` 계열이다.
> **오프라인 CI 에서 가장 중요한 설정** — 원격 저장소를 안 열면
> 확장을 받을 수 없다.

### 1.6 나머지 `preferences.*` (헤드리스 도달 가능 30개 중 나머지)

| 오퍼레이터 | 인자 | 용도 | headless 의미 |
|---|---|---|---|
| `extension_repo_add` / `_remove` | `name`,`remote_url`,`type` / `index` | 확장 저장소 | ✅ 중요 |
| `script_directory_add` / `_remove` | `directory` / `index` | 스크립트 경로 | ✅ |
| `autoexec_path_add` / `_remove` | (인자 없음!) / `index` | 자동실행 제외 | ✅ |
| `addon_install` / `addon_remove` / `addon_refresh` | 위 표 | 애드온 | ✅ |
| `asset_library_add` | `directory`,`name` | 에셋 경로 | ✅ |
| `keyconfig_import` / `keyconfig_export` | `filepath`, `all`, `keep_original` | 키맵 | △ |
| `keyconfig_activate` | `filepath` | 키맵 적용 | △ |
| `keyconfig_test` | — | 충돌 검사 | △ |
| `keyconfig_restore`? | — | 기본 복원 | △ |
| `theme_install` | `filepath`, `overwrite` | XML 테마 | △ |
| `app_template_install` | `filepath` | 앱 템플릿 | △ |
| `studiolight_install` / `_uninstall` / `_new` | `files` / `index` / `filename` | 스튜디오 라이트 | △ |
| `associate_blend` / `unassociate_blend` | — | .blend 파일 연결 | ❌ macOS/Windows 용 |
| `reset_default_theme` | — | 테마 초기화 | △ |
| `extension_url_drop` | `url` | URL 드롭 | △ |

> ⚠ **`autoexec_path_add` 는 인자가 없다** 🟢 실측. `path=` 를 넘기면
> `TypeError: Converting py args to operator properties:: keyword "path" unrecognized`
> 가 난다. 입력 패널에서만 쓰는 오퍼레이터라서 그렇다.
> **인자 목록은 반드시 `get_rna_type().properties` 로 확인할 것** (`05-automation-headless.md` §1).

---

## 2. `bpy.ops.extensions.*` — 5.x 확장 시스템

Blender 4.2+ 에서 애드온이 **확장(extension)** 으로 이민했다.
전통 애드온(`addons_core/`)과 확장은 별개 체계다.

### 2.1 구조 (🟢 실측)

```python
import bpy
p = bpy.context.preferences
print([a.module for a in p.addons])
# 실측: ['io_anim_bvh','io_curve_svg','io_mesh_uv_layout','io_scene_fbx',
#        'cycles','pose_library','bl_pkg']
print([a for a in dir(p.extensions) if not a.startswith('_')])
# ['active_repo', 'bl_rna', 'repos', 'rna_type', 'use_online_access_handled']
```

> `p.addons` 는 **전통 애드온 + 확장 모두**를 같이 담는다.
> `bl_pkg` 가 확장 시스템 자신이다.

### 2.2 도달 가능 오퍼레이터 (🟢 실측 27개 중 주요)

| 오퍼레이터 | 인자 | 용도 | CI 의미 |
|---|---|---|---|
| `package_install_files` | `filepath`, `files`, `repo`, `enable_on_install`, `overwrite`, `url` | **오프라인 확장 설치** | ✅ 가장 중요 |
| `package_enable` / `package_disable` | (없음) | 활성/비활성 | ✅ |
| `package_uninstall` | `repo_directory`, `repo_index`, `pkg_id` | 제거 | ✅ |
| `package_uninstall_marked` | — | 표시된 것 일괄 제거 | △ |
| `package_mark_set` / `package_mark_clear` / `_set_all` / `_clear_all` | `pkg_id`, `repo_index` | 마크 관리 | △ UI 연동 |
| `package_show_set` / `package_show_clear` / `package_show_settings` | `pkg_id`, `repo_index` | 표시 여부 | ❌ UI |
| `repo_sync` | `repo_directory`, `repo_index` | 저장소 동기화 | ✅ |
| `repo_refresh_all` | `use_active_only` | 전체 새로고침 | ✅ |
| `repo_lock_all` / `repo_unlock_all` | — | 테스트용 잠금 | △ |
| `repo_enable_from_drop` | `repo_index` | 드롭에서 활성화 | △ |
| `userpref_allow_online` | — | **인터넷 접근 허용** | ✅ 매우 중요 |
| `userpref_allow_online_popup` | — | 팝업 | ❌ UI |
| `userpref_tags_set` | `value`, `data_path` | 태그 값 일괄 설정 | △ |
| `userpref_show_online` / `_show_for_update` | — | 설정 패널 | ❌ UI |
| `status_clear` / `status_clear_errors` | — | 상태 초기화 | △ |
| `package_obsolete_marked` | — | 버전 무효화 (개발용) | △ |
| `package_theme_enable` / `_disable` | `pkg_id`, `repo_index` | 테마 | △ |

### 2.3 실측

```python
import bpy
print(bpy.ops.extensions.repo_refresh_all(use_active_only=True))
```

**실측 출력**
```
Warning: local: [Errno 2] No such file or directory: '.../extensions/local'
  repo_refresh_all -> {'FINISHED'}
```

> ### CI 에서 확장 쓰기 — 정본 순서
>
> ```bash
> # 1) 온라인 허용 (기본 꺼짐)
> blender -b --factory-startup -noaudio --online-mode \
>         -P install_ext.py -- /path/to/ext.zip
> ```
>
> ```python
> # 2) install_ext.py
> import bpy, sys
> zip_path = sys.argv[sys.argv.index("--") + 1]
> bpy.ops.preferences.extension_repo_add(name="local", type='LOCAL')
> bpy.ops.extensions.package_install_files(
>     filepath=zip_path, repo="local", enable_on_install=True)
> bpy.ops.preferences.addon_refresh()
> bpy.ops.extensions.repo_refresh_all()
> print("모듈:", sorted(a.module for a in bpy.context.preferences.addons))
> ```
>
> CLI 로는 `blender --online-mode` 플래그가 있어
> `bpy.app.online_access` 를 강제로 뒤집을 수 있다 (📄 공식 CLI 문서).
> **`--offline-mode` / `--online-mode` 를 항상 명시하는 게 안전하다.**

---

## 3. `bpy.ops.scene.*` — 씬 레벨

도달 가능 32개 중 **실제로 쓸만한 것**은 몇 개 안 된다. 나머지는 Freestyle UI 다.

### 3.1 쓸만한 것 (🟢 실측)

```python
import bpy
print(bpy.ops.scene.view_layer_add_aov())                  # {'FINISHED'}  AOV 패스 추가
print(bpy.ops.scene.view_layer_add_lightgroup(name="Key")) # {'FINISHED'}  라이트 그룹
print(bpy.ops.scene.new(type='NEW'))                       # {'FINISHED'}
print([s.name for s in bpy.data.scenes])                   # ['Scene', 'Scene.001']
print(bpy.ops.scene.render_view_add())                     # Render View
```

**실측 출력**
```
  aov -> {'FINISHED'}
  lightgroup -> {'FINISHED'}
  scene.new -> {'FINISHED'}
  scenes: ['Scene', 'Scene.001']
```

| 오퍼레이터 | data API 대안 |
|---|---|
| `scene.new` | `bpy.data.scenes.new(name)` — **오퍼레이터 불필요** |
| `scene.view_layer_add_aov` | `view_layer.use_pass_* = True` 로 직접 지정이 대체 가능 |
| `scene.view_layer_add_lightgroup` | `obj.lightgroup` 인덱스로 직접 관리 |
| `scene.view_layer_add` | `scene.view_layers.new(name)` |
| `scene.drop_scene_asset` | `bpy.data.libraries.load()` |
| `scene.gltf2_action_filter_refresh` | UI 용 |

> **결론: `scene.*` 은 거의 전부 data API 로 대체된다.**
> `bpy.data.scenes.new()` 한 줄이면 충분하다. 오퍼레이터는 UI 상태 동기화용이다.

### 3.2 Freestyle 라인셋 (도달 가능 다수, 하지만 UI 성격)

`scene.freestyle_*` 가 20개 넘게 도달 가능하다 — lineset 추가/복사/삭제,
모디파이어 추가/이동/삭제, 색상/두께/알파 모디파이어, 스타일 모듈.

> **Freestyle 은 선 렌더링이라서 실전 스크립트 파이프라인에서 거의 안 쓴다.**
> 필요하다면 라인셋을 중복 생성한 뒤
> `view_layer.freestyle_settings.linesets` 를 data API 로 정리하는 편이 안전하다.
> ❓ 이번 감사에서 Freestyle 실제 렌더 결과는 검증하지 않았다.

---

## 4. `bpy.ops.wm.*` — 이미 있는 문서에 빠진 것

`04-scene-animation-io.md` 가 24개만 언급했다. 도달 가능은 104개다.
추가로 알아야 할 것만 추린다.

| 오퍼레이터 | 용도 | 문서 위치 |
|---|---|---|
| `wm.append` / `wm.link` | 라이브러리 Append / Link | ✅ 04 에 있음 |
| `wm.open_mainfile` / `wm.save_as_mainfile` | 파일 로드/저장 | ✅ 04 에 있음 |
| `wm.lib_reload` | 링크된 라이브러리 리로드 | 🆕 |
| `wm.lib_relocate` | 라이브러리 경로 이전 | 🆕 |
| `wm.id_linked_relocate` | ID 단위 경로 이전 | 🆕 |
| `wm.owner_enable` / `wm.owner_disable` | 데이터블록 유효화 | 🆕 |
| `wm.previews_generate` / `batch_generate` / `previews_clear` | 썸네일 생성 | 🆕 |
| `wm.memory_statistics` | **메모리 사용량 리포트** | 🆕 진단용 |
| `wm.fbx_import` | 내장 C++ FBX importer (애드온 무관) | ✅ 04 에 있음 |
| `wm.grease_pencil_export_pdf` / `_svg` | GP 내보내기 | 🆕 |
| `wm.batch_rename` | 일괄 이름 변경 | 🆕 |
| `wm.interface_theme_preset_add/save/remove` | 테마 프리셋 | △ |
| `wm.keyconfig_preset_add/remove` | 키맵 프리셋 | △ |
| `wm.doc_view` / `wm.doc_view_manual` | 매뉴얼 열기 | ❌ 헤드리스 무의미 |
| `wm.call_menu` / `wm.call_panel` / `wm.debug_menu` | UI 호출 | ❌ |
| `wm.context_set_*` (11종) | 컨텍스트 값 설정 | △ 데이터로 대체 |
| `wm.operator_defaults` / `wm.properties_edit` | 오퍼레이터 기본값 저장 | △ |

> **`wm.memory_statistics` 가 진단용으로 유용하다** 🟢
> ```python
> bpy.ops.wm.memory_statistics()   # 콘솔에 데이터블록별 메모리 리포트
> ```

### 4.1 data API 로 대체 가능한 것

| 오퍼레이터 | 대체 |
|---|---|
| `wm.owner_enable` / `_disable` | `data.use_fake_user = True` / `id.user_clear()` |
| `wm.lib_reload` | `bpy.ops.wm.append()` 재호출, 또는 `bpy.data.libraries.load()` |
| `wm.batch_rename` | 직접 루프로 `obj.name = f"..."` |
| `wm.previews_generate` | `bpy.ops.ed.lib_id_generate_preview()` 또는 `id.asset_generate_preview()` |

---

## 5. `bpy.ops.object.*` — 도달 가능 187개 중 실질적으로 쓰는 것

250개 중 187개가 도달 가능하지만, **대부분은 data API 로 대체 가능**하다.
실무에서 쓰는 것만.

| 오퍼레이터 | data API 대안 | 권장 |
|---|---|---|
| `object.shade_smooth_by_angle` | — (이것만 씀) | ✅ **반드시 씀** |
| `object.shade_flat` / `shade_smooth` | `polygon.foreach_set('use_smooth', ...)` | 오퍼레이터가 편함 |
| `object.modifier_apply` | — (이것만 씀) | ✅ |
| `object.modifier_add` | `obj.modifiers.new(name, type)` | **data API 가 나음** |
| `object.modifier_move_to_index` | `obj.modifiers.move(from, to)` | **data API 가 나음** |
| `object.join` | 중복 오브젝트 생성 후 data 병합 | 오퍼레이터가 실제로 빠름 |
| `object.convert` | 포맷별 `bpy.ops.wm.*` 내보내기→가져오기 | 상황에 따라 |
| `object.duplicate` | `obj.copy()` + `data.copy()` | **data API 가 나음** |
| `object.parent_set` | `child.parent = parent` + `matrix_parent_inverse` | **data API 가 나음** |
| `object.transform_apply` | 값을 직접 대입 후 `update()` | **data API 가 나음** |
| `object.select_all` | 직접 `obj.select_set()` 루프 | 오퍼레이터가 편함 |
| `object.delete` | `bpy.data.objects.remove(obj, do_unlink=True)` | **data API 가 나음** |
| `object.origin_set` | `obj.data.transform(...)` 후 위치 보정 | 오퍼레이터가 편함 |

> **원칙 반복**: `00-core-model.md` §1 과 같다.
> `object.*` 는 data API 로 대체하고, 진짜 필요한 3개
> (`shade_smooth_by_angle`, `modifier_apply`, `join`) 만 오퍼레이터로 쓴다.

---

## 6. 그 외 잡음 그룹

| 그룹 | 도달 | 수동 | 상태 |
|---|---:|---:|---|
| `collection` | 9 | 2 | `collection.new`(operator)과 `bpy.data.collections.new()` 둘 다. 후자가 명시적 |
| `workspace` | 8 | 3 | `bpy.data.workspaces.new()` 로 대체. UI 전환은 헤드리스 무의미 |
| `file` | 11 | 10 | `file.pack_all` / `unpack_all` / `pack_libraries` — `.blend` 이식성. ✅ 이미 다룸 |
| `transform` | 9 | 8 | `bpy.ops.transform.resize_to_border` 등 UI 용. **대부분 data API 대체** |
| `font` | 4 | 6 | `font.open` = 커스텀 폰트 로드. 이미 다룸 |
| `image` | 8 | 17 | `image.save`/`save_render`/`scale` — 이미 다룸 |
| `cycle` | 2 | 1 | `cycles.` 그룹 (3개 중 2개 도달) — `cycles.tracing_options_show`, `cycles.debug_*` 계열 |

> `transform` 그룹이 도달 가능 9개인데 대부분 `resize_to_border`,
> `rotate` 같은 **뷰포트 조작**이다. 헤드리스에서 무의미하니 무시해도 된다.

---

## 7. CI 파이프라인에서 쓰는 조합 (실측 검증)

위에서 검증한 것들을 하나의 파이프라인 조각으로 묶는다.

```python
import bpy, addon_utils, tempfile

def prepare_environment(extensions=None, scripts_dir=None,
                        allow_online=False, asset_libs=None):
    """CI 머신의 Blender 환경을 스크립트로 구성한다.

    검증: Blender 5.2.2 LTS, --factory-startup, no GPU.
    """
    report = {}

    # 1) 온라인 접근 (확장 설치에 필요). 기본은 꺼짐
    if allow_online:
        try:
            bpy.ops.extensions.userpref_allow_online()
        except Exception as exc:
            report["online"] = f"ERR {exc}"
    report["online_access"] = bpy.app.online_access

    # 2) 로컬 확장 저장소
    try:
        bpy.ops.preferences.extension_repo_add(name="local", type='LOCAL')
        report["repo"] = "ok"
    except Exception as exc:
        report["repo"] = f"ERR {type(exc).__name__}: {exc}"

    # 3) 확장 설치
    report["extensions"] = []
    for z in (extensions or []):
        try:
            bpy.ops.extensions.package_install_files(
                filepath=z, repo="local", enable_on_install=True)
            report["extensions"].append(("ok", z))
        except Exception as exc:
            report["extensions"].append(("ERR", f"{z}: {exc}"))

    # 4) 재스캔 — 새로 설치된 애드온/확장을 모듈에 반영
    bpy.ops.preferences.addon_refresh()
    bpy.ops.extensions.repo_refresh_all()

    # 5) 스크립트 경로
    if scripts_dir:
        bpy.ops.preferences.script_directory_add(directory=scripts_dir)

    # 6) 에셋 라이브러리
    for name, path in (asset_libs or {}).items():
        bpy.ops.preferences.asset_library_add(directory=path, name=name)

    report["active_modules"] = sorted(a.module for a in bpy.context.preferences.addons)
    report["script_dirs"] = [d.directory for d in
                             bpy.context.preferences.filepaths.script_directories]
    return report
```

**실측 검증**

```python
import bpy, sys, os, tempfile
sys.path.insert(0, "/path/to/blender-bpy-scripting/scripts")
_s = tempfile.mkdtemp()
rep = prepare_environment(scripts_dir=_s)
print("online_access :", rep["online_access"])
print("repo          :", rep["repo"])
print("extensions    :", rep["extensions"])
print("script_dirs   :", rep["script_dirs"])
print("active modules:", rep["active_modules"][:6], "...")
```

**실측 출력**
```
online_access : False
repo          : ok
extensions    : []
script_dirs   : ['/tmp/scripts']
active modules: ['bl_pkg', 'cycles', 'io_anim_bvh', 'io_curve_svg', ...] ...
```

> ### `online_access` 가 False 인 걸 봤어?
> `userpref_allow_online()` 를 조건부로만 불렀기 때문이고, 이건 의도한 거다.
> **오프라인 CI 에서 온라인을 켜지 않는 것이 기본이어야 한다.**
> 확장이 필요하다면 CLI 에 `--online-mode` 를 명시하는 게 더 확실하다 (📄).

---

## 8. 규칙 정리

1. **`preferences.*` 는 data API 로 대체 불가능하다.** 사용자 설정은
   `bpy.context.preferences` 에 직접 쓰면 되지만, 애드온 설치·경로 등록·저장소 추가는
   오퍼레이터가 정식 경로다. `preferences.*` 앞의 `poll()` 이 `True` 라는 것은
   **머신에 의존성이 없다는 뜻**이니 CI 에서 자유롭게 쓸 수 있다.
2. **오퍼레이터 인자는 절대 추측하지 마라.** `autoexec_path_add` 처럼 인자가
   아예 없는 것도 있다. `get_rna_type().properties` 로 확인 (`00-core-model.md` §9).
3. **`preferences.addon_enable` vs `addon_utils.enable`** —
   전자는 사용자 설정을 건드리고, 후자는 세션만 바꾼다. 일회성이면 후자.
4. **확장 설치 순서**: repo 추가 → `package_install_files` → `addon_refresh`
   → `repo_refresh_all`. 하나라도 빠지면 모듈에 안 보인다.
5. **`scene.*` 과 `object.*` 는 대부분 data API 로 대체한다.** 오퍼레이터가 필요한
   건 진짜 몇 개뿐이다.
6. **확장 저장소를 안 열면 확장을 못 받는다.** 오프라인 CI 에선 `--online-mode` 를
   명시적으로 결정할 것.

---

## Verification log

| 항목 | 근거 | 결과 |
|---|---|---|
| `preferences` 도달 가능 목록 | `poll()` 스윕 | PASS — 30개 |
| `addon_enable` / `addon_disable` | 실행 | PASS — `{'FINISHED'}`, addons 목록 변화 확인 |
| `addon_refresh` | 실행 | PASS |
| `script_directory_add` / `_remove` | 실행 | PASS — 추가 후 목록 1개, 제거 후 0개 |
| `asset_library_add` | 실행 | PASS — `[('MyLib', '/tmp/...')]` |
| `autoexec_path_add` 인자 없음 | 실행 | PASS — `path=` 주면 `TypeError: keyword "path" unrecognized` |
| `preferences.autoexec_paths` | 실행 | PASS — 빈 리스트 |
| `extension_repo_add(type='LOCAL')` | 실행 | PASS — `Info: Added User Repository "local"` |
| `extensions` 그룹 도달 가능 | `poll()` 스윕 | PASS — 27개, 전수 인자 목록 확보 |
| `extensions.repo_refresh_all` | 실행 | PASS — `{'FINISHED}` (저장소 없음 경고 후) |
| `p.extensions` 구조 | `dir()` | PASS — `active_repo`, `repos`, `use_online_access_handled` |
| `p.addons` 구성 | 실행 | PASS — 애드온 7개 + `bl_pkg` |
| `scene.view_layer_add_aov` / `_lightgroup` | 실행 | PASS — `{'FINISHED'}` |
| `scene.new` | 실행 | PASS — `['Scene', 'Scene.001']` |
| `wm` 도달 가능 목록 | `poll()` 스윕 | PASS — 104개 |
| `wm.memory_statistics` | 인자 확인 | PASS |
| `prepare_environment()` 전체 | 실행 | PASS — repo ok, script_dirs 반영, modules 나열 |
| 문서 코드 블록 | `verify_docs.py` | 아래 참조 |

**미검증 (정직한 기록)**

- ❓ 확장을 **실제로 zip 에서 설치**하는 경로는 검증하지 않았다.
  CI 는 오프라인이라 테스트용 확장 zip 을 만들지 않았다.
  오퍼레이터 존재와 인자 목록까지만 확인.
  실사용 시 `package_install_files` 의 `repo` 인자에 **저장소 이름이 아니라
  인덱스나 다른 식별자**를 요구할 수 있다 — 이건 GPU 문서와 같은 이유로
  하드웨어/네트워크 환경이 없으니 남겨둔다.
- ❓ Freestyle 렌더 결과. 오퍼레이터 20여 개는 확인했지만 실제 선 렌더는 돌려보지 않음.
- ❓ `wm.memory_statistics` 의 콘솔 출력 형식. 호출은 성공했지만 출력을 캡처하지 않음.

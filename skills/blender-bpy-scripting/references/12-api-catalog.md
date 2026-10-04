# Blender 5.2 bpy API 전수 카탈로그 (자동 생성)

> **이 파일은 손으로 쓴 게 아니다.** `scripts/dump_api.py` 가 실행 중인 Blender 에서 직접 읽어 생성한 것이다.
> 재생성:
> ```bash
> blender -b --factory-startup -noaudio -P scripts/dump_api.py -- --out catalog.md
> blender -b --factory-startup -noaudio -P scripts/probe_ops.py -- --out reach.json
> ```
>
> 빌드 `5.2.2 LTS` (`d13f752e3b9c`), Python 3.13.13

## 요약

| 표면 | 개수 |
|---|---|
| `bpy.ops` 오퍼레이터 | **2498** |
| └ 빈 factory 씬에서 `poll()` True | 670 |
| └ `poll()` False | 1828 |
| └ 판정 불가 (애드온 미등록 등) | 0 |
| 노드 타입 | **568** |
| 타입 열거형 | 17 |
| `bpy.data` 컬렉션 | **29** |
| `bpy.types` 클래스 | 4013 |

## ⭐ 헤드리스 도달 가능성 — 이게 진짜 쓸모 있는 숫자

`scripts/probe_ops.py` 가 **오퍼레이터 전부를 실제로 `poll()` 으로 때려봤다.** (빈 factory 씬을 스크립트 친화적으로 채운 뒤, `temp_override` 조합까지 시도)

| 판정 | 개수 | 비율 | 의미 |
|---|---:|---:|---|
| **✅ 그냥 됨** | 625 | 25.0% | `bpy.ops.<g>.<op>(...)` 바로 호출 |
| **⚠ override 필요** | 52 | 2.1% | `temp_override(...)` 를 씌워야 함 |
| **❌ UI 전용** | 1821 | 72.9% | 스크립트로 부를 수 없음. **시도하지 마라** |

> ### 해석이 이게 중요합니다
>
> 오퍼레이터 2498개 중 **스크립트로 실제 호출 가능한 것은 677개(27%) 뿐**입니다.
> 나머지 73% 는 `outliner.*`, `ui.*`, `view3d.*`, `screen.*`, `graph.*`, `clip.*` 같은 **UI 전용**입니다.
>
> **에이전트가 이걸 모르면 실제로 일이납니다.** `bpy.ops.outliner.delete()` 같은 걸 찾아서 쓰려고 하고, 안 된다고 몇 시간씩 디버깅합니다.
> 이 표에서 ❌인 항목을 보지 말고 **애초에 시도하지 마세요.**

> ⚠ 표시(`override 필요`) 항목의 정확한 컨텍스트는 [`05-automation-headless.md`](05-automation-headless.md) §2 를 보세요.

---

## 목차

- [⭐ 헤드리스 도달 가능성](#-헤드리스-도달-가능성--이게-진짜-쓸모-있는-숫자)
- [1. `bpy.ops` 전수](#1-bpyops-전수)  ([그룹별 고득점](#11-그룹별-고득점-랭킹--뭘-배워야-하나))
- [2. 노드 타입 전수](#2-노드-타입-전수)
- [3. 타입 열거형 전수](#3-타입-열거형-전수)
- [4. `bpy.data` 컬렉션 전수](#4-bpydata-컬렉션-전수)
- [5. 최상위 모듈 표면](#5-최상위-모듈-표면)

## 1. `bpy.ops` 전수

| 기호 | 의미 |
|---|---|
| ✅ | 빈 factory 씬에서 `poll()` True — 바로 호출 가능 |
| ⚠ | `temp_override` 로 컨텍스트를 만들어야 함 |
| ❌ | 배경 모드에서 도달 불가 (UI 전용) |

### `action` — 37개 (✅ 0 / ⚠ 0 / ❌ 37)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `action.bake_keys` | Add keyframes on every frame between the selected keyframes | — |
| ❌ | `action.clean` | Simplify F-Curves by removing closely spaced keyframes | `threshold`:FLOAT, `channels`:BOOLEAN |
| ❌ | `action.clickselect` | Select keyframes by clicking on them | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `deselect_all`:BOOLEAN, `column`:BOOLEAN, `channel`:BOOLEAN |
| ❌ | `action.copy` | Copy selected keyframes to the internal clipboard | — |
| ❌ | `action.delete` | Remove all selected keyframes | `confirm`:BOOLEAN |
| ❌ | `action.duplicate` | Make a copy of all selected keyframes | — |
| ❌ | `action.duplicate_move` | Make a copy of all selected keyframes and move them | `ACTION_OT_duplicate`:POINTER, `TRANSFORM_OT_transform`:POINTER |
| ❌ | `action.easing_type` | Set easing type for the F-Curve segments starting from the selected keyframes | `type`=AUTO/EASE_IN/EASE_OUT/EASE_IN_OUT |
| ❌ | `action.extrapolation_type` | Set extrapolation mode for selected F-Curves | `type`=CONSTANT/LINEAR/MAKE_CYCLIC/CLEAR_CYCLIC |
| ❌ | `action.frame_jump` | Set the current frame to the average frame value of selected keyframes | — |
| ❌ | `action.handle_type` | Set type of handle for selected keyframes | `type`=FREE/ALIGNED/VECTOR/AUTO/AUTO_CLAMPED |
| ❌ | `action.interpolation_type` | Set interpolation mode for the F-Curve segments starting from the selected keyframes | `type`=CONSTANT/LINEAR/BEZIER/SINE/QUAD/CUBIC/QUART/QUINT/EXPO/CIRC/BACK/BOUNCE/ELASTIC |
| ❌ | `action.keyframe_insert` | Insert keyframes for the specified channels | `type`=ALL/SEL/GROUP |
| ❌ | `action.keyframe_type` | Set type of keyframe for the selected keyframes | `type`=KEYFRAME/BREAKDOWN/MOVING_HOLD/EXTREME/JITTER/GENERATED |
| ❌ | `action.markers_make_local` | Move selected scene markers to the active Action as local 'pose' markers | — |
| ❌ | `action.mirror` | Flip selected keyframes over the selected mirror line | `type`=CFRA/MARKER/XAXIS |
| ❌ | `action.new` | Create new action | — |
| ❌ | `action.paste` | Paste keyframes from the internal clipboard for the selected channels, starting on the cur | `offset`=START/END/RELATIVE/NONE, `merge`=MIX/OVER_ALL/OVER_RANGE/OVER_RANGE_ALL, `flipped`:BOOLEAN |
| ❌ | `action.previewrange_set` | Set Preview Range based on extents of selected Keyframes | — |
| ❌ | `action.push_down` | Push action down on to the NLA stack as a new strip | — |
| ❌ | `action.select_all` | Toggle selection of all keyframes | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `action.select_box` | Select all keyframes within the specified region | `axis_range`:BOOLEAN, `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB, `tweak`:BOOLEAN |
| ❌ | `action.select_by_type` | Select all keyframes of the given type | `extend`:BOOLEAN, `type`=KEYFRAME/BREAKDOWN/MOVING_HOLD/EXTREME/JITTER/GENERATED |
| ❌ | `action.select_circle` | Select keyframe points using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `action.select_column` | Select all keyframes on the specified frame(s) | `mode`=KEYS/CFRA/MARKERS_COLUMN/MARKERS_BETWEEN |
| ❌ | `action.select_lasso` | Select keyframe points using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB |
| ❌ | `action.select_leftright` | Select keyframes to the left or the right of the current frame | `mode`=CHECK/LEFT/RIGHT, `extend`:BOOLEAN |
| ❌ | `action.select_less` | Deselect keyframes on ends of selection islands | — |
| ❌ | `action.select_linked` | Select keyframes occurring in the same F-Curves as selected ones | — |
| ❌ | `action.select_more` | Select keyframes beside already selected ones | — |
| ❌ | `action.snap` | Snap selected keyframes to the times specified | `type`=CFRA/NEAREST_FRAME/NEAREST_SECOND/NEAREST_MARKER |
| ❌ | `action.stash` | Store this action in the NLA stack as a non-contributing strip for later use | `create_new`:BOOLEAN |
| ❌ | `action.stash_and_create` | Store this action in the NLA stack as a non-contributing strip for later use, and create a | — |
| ❌ | `action.unlink` | Unlink this action from the active action slot (and/or exit Tweak Mode) | `force_delete`:BOOLEAN |
| ❌ | `action.view_all` | Reset viewable area to show full keyframe range | — |
| ❌ | `action.view_frame` | Move the view to the current frame | — |
| ❌ | `action.view_selected` | Reset viewable area to show selected keyframes range | — |

### `anim` — 65개 (✅ 12 / ⚠ 4 / ❌ 49)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `anim.change_frame` | Interactively change the current frame number | `frame`:FLOAT, `snap`:BOOLEAN, `seq_solo_preview`:BOOLEAN, `pass_through_on_strip_handles`:BOOLEAN |
| ❌ | `anim.channel_select_keys` | Select all keyframes of channel under mouse | `extend`:BOOLEAN |
| ❌ | `anim.channel_view_pick` | Reset viewable area to show the channel under the cursor | `include_handles`:BOOLEAN, `use_preview_range`:BOOLEAN |
| ❌ | `anim.channels_bake` | Create keyframes following the current shape of F-Curves of selected channels | `use_scene_range`:BOOLEAN, `range`:INT, `step`:FLOAT, `remove_outside_range`:BOOLEAN, `interpolation_type`=BEZIER/LIN/CONST, `bake_modifiers`:BOOLEAN |
| ❌ | `anim.channels_clean_empty` | Delete all empty animation data containers from visible data-blocks | — |
| ❌ | `anim.channels_click` | Handle mouse clicks over animation channels | `extend`:BOOLEAN, `extend_range`:BOOLEAN, `children_only`:BOOLEAN |
| ❌ | `anim.channels_collapse` | Collapse (close) all selected expandable animation channels | `all`:BOOLEAN |
| ❌ | `anim.channels_delete` | Delete all selected animation channels | — |
| ❌ | `anim.channels_editable_toggle` | Toggle editability of selected channels | `mode`=TOGGLE/DISABLE/ENABLE/INVERT, `type`=PROTECT/MUTE |
| ❌ | `anim.channels_expand` | Expand (open) all selected expandable animation channels | `all`:BOOLEAN |
| ❌ | `anim.channels_fcurves_enable` | Clear 'disabled' tag from all F-Curves to get broken F-Curves working again | — |
| ❌ | `anim.channels_group` | Add selected F-Curves to a new group | `name`:STRING |
| ❌ | `anim.channels_move` | Rearrange selected animation channels | `direction`=TOP/UP/DOWN/BOTTOM |
| ❌ | `anim.channels_rename` | Rename animation channel under mouse | — |
| ❌ | `anim.channels_select_all` | Toggle selection of all animation channels | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `anim.channels_select_box` | Select all animation channels within the specified region | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `deselect`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `anim.channels_select_filter` | Start entering text which filters the set of channels shown to only include those with mat | — |
| ❌ | `anim.channels_setting_disable` | Disable specified setting on all selected animation channels | `mode`=TOGGLE/DISABLE/ENABLE/INVERT, `type`=PROTECT/MUTE |
| ❌ | `anim.channels_setting_enable` | Enable specified setting on all selected animation channels | `mode`=TOGGLE/DISABLE/ENABLE/INVERT, `type`=PROTECT/MUTE |
| ❌ | `anim.channels_setting_toggle` | Toggle specified setting on all selected animation channels | `mode`=TOGGLE/DISABLE/ENABLE/INVERT, `type`=PROTECT/MUTE |
| ❌ | `anim.channels_ungroup` | Remove selected F-Curves from their current groups | — |
| ❌ | `anim.channels_view_selected` | Reset viewable area to show the selected channels | `include_handles`:BOOLEAN, `use_preview_range`:BOOLEAN |
| ✅ | `anim.clear_useless_actions` | Mark actions with no F-Curves for deletion after save and reload of file preserving "actio | `only_unused`:BOOLEAN |
| ✅ | `anim.copy_driver_button` | Copy the driver for the highlighted button | — |
| ❌ | `anim.driver_button_add` | Add driver for the property under the cursor | — |
| ✅ | `anim.driver_button_edit` | Edit the drivers for the connected property represented by the highlighted button | — |
| ✅ | `anim.driver_button_remove` | Remove the driver(s) for the connected property(s) represented by the highlighted button | `all`:BOOLEAN |
| ❌ | `anim.end_frame_set` | Set the current frame as the preview or scene end frame | — |
| ❌ | `anim.keyframe_clear_button` | Clear all keyframes on the currently active property | `all`:BOOLEAN |
| ❌ | `anim.keyframe_clear_v3d` | Remove all keyframe animation for selected objects | `confirm`:BOOLEAN |
| ❌ | `anim.keyframe_clear_vse` | Remove all keyframe animation for selected strips | `confirm`:BOOLEAN |
| ❌ | `anim.keyframe_delete` | Delete keyframes on the current frame for all properties in the specified Keying Set | `type`=DEFAULT |
| ❌ | `anim.keyframe_delete_button` | Delete current keyframe of current UI-active property | `all`:BOOLEAN |
| ❌ | `anim.keyframe_delete_by_name` | Alternate access to 'Delete Keyframe' for keymaps to use | `type`:STRING |
| ❌ | `anim.keyframe_delete_v3d` | Remove keyframes on current frame for selected objects and bones | `confirm`:BOOLEAN |
| ❌ | `anim.keyframe_delete_vse` | Remove keyframes on current frame for selected strips | `confirm`:BOOLEAN |
| ❌ | `anim.keyframe_insert` | Insert keyframes on the current frame using either the active keying set, or the user pref | `type`=DEFAULT |
| ❌ | `anim.keyframe_insert_button` | Insert a keyframe for current UI-active property | `all`:BOOLEAN |
| ❌ | `anim.keyframe_insert_by_name` | Alternate access to 'Insert Keyframe' for keymaps to use | `type`:STRING |
| ❌ | `anim.keyframe_insert_menu` | Insert Keyframes for specified Keying Set, with menu of available Keying Sets if undefined | `type`=DEFAULT, `always_prompt`:BOOLEAN |
| ❌ | `anim.keying_set_active_set` | Set a new active keying set | `type`=DEFAULT |
| ✅ | `anim.keying_set_add` | Add a new (empty) keying set to the active Scene | — |
| ✅ | `anim.keying_set_export` | Export Keying Set to a Python script | `filepath`:STRING, `filter_folder`:BOOLEAN, `filter_text`:BOOLEAN, `filter_python`:BOOLEAN |
| ❌ | `anim.keying_set_path_add` | Add empty path to active keying set | — |
| ❌ | `anim.keying_set_path_remove` | Remove active Path from active keying set | — |
| ❌ | `anim.keying_set_remove` | Remove the active keying set | — |
| ✅ | `anim.keyingset_button_add` | Add current UI-active property to current keying set | `all`:BOOLEAN |
| ✅ | `anim.keyingset_button_remove` | Remove current UI-active property from current keying set | — |
| ⚠ | `anim.merge_animation` | Merge the animation of the selected objects into the action of the active object. Actions  | — |
| ✅ | `anim.paste_driver_button` | Paste the driver in the internal clipboard to the highlighted button | — |
| ❌ | `anim.previewrange_clear` | Clear preview range | — |
| ❌ | `anim.previewrange_set` | Interactively define frame range used for playback | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ⚠ | `anim.replace_action` | Swap all users of one action to another one. The normal action slot assignment rules apply | `old_session_uid`:INT, `new_session_uid`:INT |
| ⚠ | `anim.replace_action_new` | Swap all users of one action to a new action. This ignores the NLA and Action Constraints | `old_session_uid`:INT |
| ❌ | `anim.scene_range_frame` | Reset the horizontal view to the current scene frame range, taking the preview range into  | — |
| ⚠ | `anim.separate_slots` | Move all slots of the action on the active object into newly created, separate actions. Al | — |
| ❌ | `anim.slot_channels_move_to_new_action` | Move the selected slots into a newly created action | — |
| ❌ | `anim.slot_new_for_id` | Create a new action slot for this data-block, to hold its animation | — |
| ❌ | `anim.slot_unassign_from_constraint` | Un-assign the action slot from this constraint | — |
| ❌ | `anim.slot_unassign_from_id` | Un-assign the action slot, effectively making this data-block non-animated | — |
| ❌ | `anim.slot_unassign_from_nla_strip` | Un-assign the action slot from this NLA strip, effectively making it non-animated | — |
| ❌ | `anim.start_frame_set` | Set the current frame as the preview or scene start frame | — |
| ✅ | `anim.update_animated_transform_constraints` | Update f-curves/drivers affecting Transform constraints (use it with files from 2.70 and e | `use_convert_to_radians`:BOOLEAN |
| ✅ | `anim.version_bone_hide_property` | Moves any F-Curves for the `hide` property of selected armatures into the action of the ob | — |
| ✅ | `anim.view_curve_in_graph_editor` | Frame the property under the cursor in the Graph Editor | `all`:BOOLEAN, `isolate`:BOOLEAN |

### `armature` — 49개 (✅ 0 / ⚠ 0 / ❌ 49)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `armature.align` | Align selected bones to the active bone (or to their parent) | — |
| ❌ | `armature.assign_to_collection` | Assign all selected bones to a collection, or unassign them, depending on whether the acti | `collection_index`:INT, `new_collection_name`:STRING |
| ❌ | `armature.autoside_names` | Automatically renames the selected bones according to which side of the target axis they f | `type`=XAXIS/YAXIS/ZAXIS |
| ❌ | `armature.bone_primitive_add` | Add a new bone located at the 3D cursor | `name`:STRING, `space`=OBJECT/WORLD, `align`=UP/AXES/3D_CURSOR/3D_VIEW, `length`:FLOAT, `use_deform`:BOOLEAN |
| ❌ | `armature.calculate_roll` | Automatically fix alignment of select bones' axes | `type`=POS_X/POS_Z/GLOBAL_POS_X/GLOBAL_POS_Y/GLOBAL_POS_Z/NEG_X/NEG_Z/GLOBAL_NEG_X/GLOBAL_NEG_Y/GLOBAL_NEG_Z/ACTIVE/VIEW/CURSOR, `axis_flip`:BOOLEAN, `axis_only`:BOOLEAN |
| ❌ | `armature.click_extrude` | Create a new bone going from the last selected joint to the mouse position | — |
| ❌ | `armature.collection_add` | Add a new bone collection | — |
| ❌ | `armature.collection_assign` | Add selected bones to the chosen bone collection | `name`:STRING |
| ❌ | `armature.collection_create_and_assign` | Create a new bone collection and assign all selected bones | `name`:STRING |
| ❌ | `armature.collection_deselect` | Deselect bones of active Bone Collection | — |
| ❌ | `armature.collection_move` | Change position of active Bone Collection in list of Bone collections | `direction`=UP/DOWN |
| ❌ | `armature.collection_remove` | Remove the active bone collection | — |
| ❌ | `armature.collection_remove_unused` | Remove all bone collections that have neither bones nor children. This is done recursively | — |
| ❌ | `armature.collection_select` | Select bones in active Bone Collection | — |
| ❌ | `armature.collection_show_all` | Show all bone collections | — |
| ❌ | `armature.collection_unassign` | Remove selected bones from the active bone collection | `name`:STRING |
| ❌ | `armature.collection_unassign_named` | Unassign the named bone from this bone collection | `name`:STRING, `bone_name`:STRING |
| ❌ | `armature.collection_unsolo_all` | Clear the 'solo' setting on all bone collections | — |
| ❌ | `armature.copy_bone_color_to_selected` | Copy the bone color of the active bone to all selected bones | `bone_type`=EDIT/POSE |
| ❌ | `armature.delete` | Remove selected bones from the armature | `confirm`:BOOLEAN |
| ❌ | `armature.dissolve` | Dissolve selected bones from the armature | — |
| ❌ | `armature.duplicate` | Make copies of the selected bones within the same armature | `do_flip_names`:BOOLEAN |
| ❌ | `armature.duplicate_move` | Make copies of the selected bones within the same armature and move them | `ARMATURE_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `armature.duplicate_rename` | Make copies of the selected bones within the same armature and replace a part of their nam | `do_flip_names`:BOOLEAN, `search`:STRING, `replace`:STRING |
| ❌ | `armature.extrude` | Create new bones from the selected joints | `forked`:BOOLEAN |
| ❌ | `armature.extrude_forked` | Create new bones from the selected joints and move them | `ARMATURE_OT_extrude`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `armature.extrude_move` | Create new bones from the selected joints and move them | `ARMATURE_OT_extrude`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `armature.fill` | Add bone between selected joint(s) and/or 3D cursor | — |
| ❌ | `armature.flip_names` | Flips (and corrects) the axis suffixes of the names of selected bones | `do_strip_numbers`:BOOLEAN |
| ❌ | `armature.hide` | Tag selected bones to not be visible in Edit Mode | `unselected`:BOOLEAN |
| ❌ | `armature.move_to_collection` | Move bones to a collection | `collection_index`:INT, `new_collection_name`:STRING |
| ❌ | `armature.parent_clear` | Remove the parent-child relationship between selected bones and their parents | `type`=CLEAR/DISCONNECT |
| ❌ | `armature.parent_set` | Set the active bone as the parent of the selected bones | `type`=CONNECTED/OFFSET |
| ❌ | `armature.reveal` | Reveal all bones hidden in Edit Mode | `select`:BOOLEAN |
| ❌ | `armature.roll_clear` | Clear roll for selected bones | `roll`:FLOAT |
| ❌ | `armature.select_all` | Toggle selection status of all bones | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `armature.select_hierarchy` | Select immediate parent/children of selected bones | `direction`=PARENT/CHILD, `extend`:BOOLEAN |
| ❌ | `armature.select_less` | Deselect those bones at the boundary of each selection region | — |
| ❌ | `armature.select_linked` | Select all bones linked by parent/child connections to the current selection | `all_forks`:BOOLEAN |
| ❌ | `armature.select_linked_pick` | (De)select bones linked by parent/child connections under the mouse cursor | `deselect`:BOOLEAN, `all_forks`:BOOLEAN |
| ❌ | `armature.select_mirror` | Mirror the bone selection | `only_active`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `armature.select_more` | Select those bones connected to the initial selection | — |
| ❌ | `armature.select_similar` | Select similar bones by property types | `type`=CHILDREN/CHILDREN_IMMEDIATE/SIBLINGS/LENGTH/DIRECTION/PREFIX/SUFFIX/BONE_COLLECTION/COLOR/SHAPE, `threshold`:FLOAT |
| ❌ | `armature.separate` | Isolate selected bones into a separate armature | — |
| ❌ | `armature.shortest_path_pick` | Select shortest path between two bones | — |
| ❌ | `armature.split` | Split off selected bones from connected unselected bones | — |
| ❌ | `armature.subdivide` | Break selected bones into chains of smaller bones | `number_cuts`:INT |
| ❌ | `armature.switch_direction` | Change the direction that a chain of bones points in (head and tail swap) | — |
| ❌ | `armature.symmetrize` | Enforce symmetry, make copies of the selection or use existing | `direction`=NEGATIVE_X/POSITIVE_X, `copy_bone_colors`:BOOLEAN |

### `asset` — 21개 (✅ 0 / ⚠ 0 / ❌ 21)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `asset.asset_download` | Make the asset available without internet access | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING |
| ❌ | `asset.assets_download` | Download the selected asset(s) | — |
| ❌ | `asset.assign_action` | Set this pose Action as active Action on the active Object | — |
| ❌ | `asset.browse_containing_blend_file` | Open the system's file browser with the blend file that contains the active asset | — |
| ❌ | `asset.bundle_install` | Copy the current .blend file into an Asset Library. Only works on standalone .blend files  | `asset_library_reference`=, `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `asset.catalog_delete` | Remove an asset catalog from the asset library (contained assets will not be affected and  | `catalog_id`:STRING |
| ❌ | `asset.catalog_new` | Create a new catalog to put assets in | `parent_path`:STRING |
| ❌ | `asset.catalog_redo` | Redo the last undone edit to the asset catalogs | — |
| ❌ | `asset.catalog_undo` | Undo the last edit to the asset catalogs | — |
| ❌ | `asset.catalog_undo_push` | Store the current state of the asset catalogs in the undo buffer | — |
| ❌ | `asset.catalogs_save` | Make any edits to any catalogs permanent by writing the current set up to the asset librar | — |
| ❌ | `asset.clear` | Delete all asset metadata and turn the selected asset data-blocks back into normal data-bl | `set_fake_user`:BOOLEAN |
| ❌ | `asset.clear_single` | Delete all asset metadata and turn the asset data-block back into a normal data-block | `set_fake_user`:BOOLEAN |
| ❌ | `asset.library_refresh` | Reread assets and asset catalogs from the asset library on disk | `use_remote_listing`:BOOLEAN, `use_shift_for_remote_listing`:BOOLEAN |
| ❌ | `asset.library_reload_listing` | Re-download the asset listing of a remote library. Only supported when the active asset li | — |
| ❌ | `asset.mark` | Enable easier reuse of selected data-blocks through the Asset Browser, with the help of cu | — |
| ❌ | `asset.mark_single` | Enable easier reuse of a data-block through the Asset Browser, with the help of customizab | — |
| ❌ | `asset.open_containing_blend_file` | Open the blend file that contains the active asset | — |
| ❌ | `asset.screenshot_preview` | Capture a screenshot to use as a preview for the selected asset | `p1`:INT, `p2`:INT, `force_square`:BOOLEAN |
| ❌ | `asset.tag_add` | Add a new keyword tag to the active asset | — |
| ❌ | `asset.tag_remove` | Remove an existing keyword tag from the active asset | — |

### `boid` — 8개 (✅ 8 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `boid.rule_add` | Add a boid rule to the current boid state | `type`=GOAL/AVOID/AVOID_COLLISION/SEPARATE/FLOCK/FOLLOW_LEADER/AVERAGE_SPEED/FIGHT |
| ✅ | `boid.rule_del` | Delete current boid rule | — |
| ✅ | `boid.rule_move_down` | Move boid rule down in the list | — |
| ✅ | `boid.rule_move_up` | Move boid rule up in the list | — |
| ✅ | `boid.state_add` | Add a boid state to the particle system | — |
| ✅ | `boid.state_del` | Delete current boid state | — |
| ✅ | `boid.state_move_down` | Move boid state down in the list | — |
| ✅ | `boid.state_move_up` | Move boid state up in the list | — |

### `brush` — 11개 (✅ 2 / ⚠ 0 / ❌ 9)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `brush.asset_activate` | Activate a brush asset as current sculpt and paint tool | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING, `use_toggle`:BOOLEAN |
| ❌ | `brush.asset_delete` | Delete the active brush asset | — |
| ❌ | `brush.asset_edit_metadata` | Edit asset information like the catalog, preview image, tags, or author | `catalog_path`:STRING, `author`:STRING, `description`:STRING |
| ❌ | `brush.asset_load_preview` | Choose a preview image for the brush | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `brush.asset_revert` | Revert the active brush settings to the default values from the asset library | — |
| ❌ | `brush.asset_save` | Update the active brush asset in the asset library with current settings | — |
| ❌ | `brush.asset_save_as` | Save a copy of the active brush asset into the default asset library, and make it the acti | `name`:STRING, `asset_library_reference`=, `catalog_path`:STRING |
| ✅ | `brush.scale_size` | Change brush size by a scalar | `scalar`:FLOAT |
| ❌ | `brush.stencil_control` | Control the stencil brush | `mode`=TRANSLATION/SCALE/ROTATION, `texmode`=PRIMARY/SECONDARY |
| ❌ | `brush.stencil_fit_image_aspect` | When using an image texture, adjust the stencil size to fit the image aspect ratio | `use_repeat`:BOOLEAN, `use_scale`:BOOLEAN, `mask`:BOOLEAN |
| ❌ | `brush.stencil_reset_transform` | Reset the stencil transformation to the default | `mask`:BOOLEAN |

### `buttons` — 6개 (✅ 2 / ⚠ 0 / ❌ 4)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `buttons.clear_filter` | Clear the search filter | — |
| ❌ | `buttons.context_menu` | Display properties editor context_menu | — |
| ✅ | `buttons.directory_browse` | Open a directory browser, hold Shift to open the file, Alt to browse containing directory | `directory`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ✅ | `buttons.file_browse` | Open a file browser, hold Shift to open the file, Alt to browse containing directory | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `filter_glob`:STRING |
| ❌ | `buttons.start_filter` | Start entering filter text | — |
| ❌ | `buttons.toggle_pin` | Keep the current data-block displayed | — |

### `cachefile` — 5개 (✅ 5 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `cachefile.layer_add` | Add an override layer to the archive | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ✅ | `cachefile.layer_move` | Move layer in the list, layers further down the list will overwrite data from the layers h | `direction`=UP/DOWN |
| ✅ | `cachefile.layer_remove` | Remove an override layer from the archive | — |
| ✅ | `cachefile.open` | Load a cache file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ✅ | `cachefile.reload` | Update objects paths list with new data from the archive | — |

### `camera` — 2개 (✅ 2 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `camera.preset_add` | Add or remove a Camera Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN, `use_focal_length`:BOOLEAN |
| ✅ | `camera.safe_areas_preset_add` | Add or remove a Safe Areas Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |

### `clip` — 92개 (✅ 6 / ⚠ 0 / ❌ 86)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `clip.add_marker` | Place new marker at specified location | `location`:FLOAT |
| ❌ | `clip.add_marker_at_click` | Place new marker at the desired (clicked) position | — |
| ❌ | `clip.add_marker_move` | Add new marker and move it on movie | `CLIP_OT_add_marker`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `clip.add_marker_slide` | Add new marker and slide it with mouse until mouse button release | `CLIP_OT_add_marker`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `clip.apply_solution_scale` | Apply scale on solution itself to make distance between selected tracks equals to desired | `distance`:FLOAT |
| ❌ | `clip.average_tracks` | Average selected tracks into active | `keep_original`:BOOLEAN |
| ❌ | `clip.bundles_to_mesh` | Create vertex cloud using coordinates of reconstructed tracks | — |
| ✅ | `clip.camera_preset_add` | Add or remove a Tracking Camera Intrinsics Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN, `use_focal_length`:BOOLEAN |
| ❌ | `clip.change_frame` | Interactively change the current frame number | `frame`:INT |
| ❌ | `clip.clean_tracks` | Clean tracks with high error values or few frames | `frames`:INT, `error`:FLOAT, `action`=SELECT/DELETE_TRACK/DELETE_SEGMENTS |
| ❌ | `clip.clear_solution` | Clear all calculated data | — |
| ❌ | `clip.clear_track_path` | Clear tracks after/before current position or clear the whole track | `action`=UPTO/REMAINED/ALL, `clear_active`:BOOLEAN |
| ✅ | `clip.constraint_to_fcurve` | Create F-Curves for object which will copy object's movement caused by this constraint | — |
| ❌ | `clip.copy_tracks` | Copy the selected tracks to the internal clipboard | — |
| ❌ | `clip.create_plane_track` | Create new plane track out of selected point tracks | — |
| ❌ | `clip.cursor_set` | Set 2D cursor location | `location`:FLOAT |
| ❌ | `clip.delete_marker` | Delete marker for current frame from selected tracks | `confirm`:BOOLEAN |
| ❌ | `clip.delete_proxy` | Delete movie clip proxy files from the hard drive | — |
| ❌ | `clip.delete_track` | Delete selected tracks | `confirm`:BOOLEAN |
| ❌ | `clip.detect_features` | Automatically detect features and place markers to track | `placement`=FRAME/INSIDE_GPENCIL/OUTSIDE_GPENCIL, `margin`:INT, `threshold`:FLOAT, `min_distance`:INT |
| ❌ | `clip.disable_markers` | Disable/enable selected markers | `action`=DISABLE/ENABLE/TOGGLE |
| ❌ | `clip.dopesheet_select_channel` | Select movie tracking channel | `location`:FLOAT, `extend`:BOOLEAN |
| ❌ | `clip.dopesheet_view_all` | Reset viewable area to show full keyframe range | — |
| ❌ | `clip.filter_tracks` | Filter tracks which has weirdly looking spikes in motion curves | `track_threshold`:FLOAT |
| ❌ | `clip.frame_jump` | Jump to special frame | `position`=PATHSTART/PATHEND/FAILEDPREV/FAILNEXT |
| ❌ | `clip.graph_center_current_frame` | Scroll view so current frame would be centered | — |
| ❌ | `clip.graph_delete_curve` | Delete track corresponding to the selected curve | `confirm`:BOOLEAN |
| ❌ | `clip.graph_delete_knot` | Delete curve knots | — |
| ❌ | `clip.graph_disable_markers` | Disable/enable selected markers | `action`=DISABLE/ENABLE/TOGGLE |
| ❌ | `clip.graph_select` | Select graph curves | `location`:FLOAT, `extend`:BOOLEAN |
| ❌ | `clip.graph_select_all_markers` | Change selection of all markers of active track | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `clip.graph_select_box` | Select curve points using box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `deselect`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `clip.graph_view_all` | View all curves in editor | — |
| ❌ | `clip.hide_tracks` | Hide selected tracks | `unselected`:BOOLEAN |
| ❌ | `clip.hide_tracks_clear` | Clear hide selected tracks | — |
| ❌ | `clip.join_tracks` | Join selected tracks | — |
| ❌ | `clip.keyframe_delete` | Delete a keyframe from selected tracks at current frame | — |
| ❌ | `clip.keyframe_insert` | Insert a keyframe to selected tracks at current frame | — |
| ❌ | `clip.lock_selection_toggle` | Toggle Lock Selection option of the current clip editor | — |
| ❌ | `clip.lock_tracks` | Lock/unlock selected tracks | `action`=LOCK/UNLOCK/TOGGLE |
| ❌ | `clip.mode_set` | Set the clip interaction mode | `mode`=TRACKING/MASK |
| ❌ | `clip.new_image_from_plane_marker` | Create new image from the content of the plane marker | — |
| ✅ | `clip.open` | Load a sequence of frames or a movie file | `directory`:STRING, `files`:COLLECTION, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG |
| ❌ | `clip.paste_tracks` | Paste tracks from the internal clipboard | — |
| ❌ | `clip.prefetch` | Prefetch frames from disk for faster playback/tracking | — |
| ❌ | `clip.rebuild_proxy` | Rebuild all selected proxies in the background | — |
| ❌ | `clip.refine_markers` | Refine selected markers positions by running the tracker from track's reference to current | `backwards`:BOOLEAN |
| ✅ | `clip.reload` | Reload clip | — |
| ❌ | `clip.select` | Select tracking markers | `extend`:BOOLEAN, `deselect_all`:BOOLEAN, `location`:FLOAT |
| ❌ | `clip.select_all` | Change selection of all tracking markers | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `clip.select_box` | Select markers using box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `clip.select_circle` | Select markers using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `clip.select_grouped` | Select all tracks from specified group | `group`=KEYFRAMED/ESTIMATED/TRACKED/LOCKED/DISABLED/COLOR/FAILED |
| ❌ | `clip.select_lasso` | Select markers using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB |
| ❌ | `clip.set_active_clip` | (undocumented operator) | — |
| ❌ | `clip.set_axis` | Set the direction of a scene axis by rotating the camera (or its parent if present). This  | `axis`=X/Y |
| ❌ | `clip.set_origin` | Set active marker as origin by moving camera (or its parent if present) in 3D space | `use_median`:BOOLEAN |
| ❌ | `clip.set_plane` | Set plane based on 3 selected bundles by moving camera (or its parent if present) in 3D sp | `plane`=FLOOR/WALL |
| ❌ | `clip.set_scale` | Set scale of scene by scaling camera (or its parent if present) | `distance`:FLOAT |
| ❌ | `clip.set_scene_frames` | Set scene's start and end frame to match clip's start frame and length | — |
| ❌ | `clip.set_solution_scale` | Set object solution scale using distance between two selected tracks | `distance`:FLOAT |
| ❌ | `clip.set_solver_keyframe` | Set keyframe used by solver | `keyframe`=KEYFRAME_A/KEYFRAME_B |
| ❌ | `clip.set_viewport_background` | Set current movie clip as a camera background in 3D Viewport (works only when a 3D Viewpor | — |
| ❌ | `clip.setup_tracking_scene` | Prepare scene for compositing 3D objects into this footage | — |
| ❌ | `clip.slide_marker` | Slide marker areas | `offset`:FLOAT |
| ❌ | `clip.slide_plane_marker` | Slide plane marker areas | — |
| ❌ | `clip.solve_camera` | Solve camera motion from tracks | — |
| ❌ | `clip.stabilize_2d_add` | Add selected tracks to 2D translation stabilization | — |
| ❌ | `clip.stabilize_2d_remove` | Remove selected track from translation stabilization | — |
| ❌ | `clip.stabilize_2d_rotation_add` | Add selected tracks to 2D rotation stabilization | — |
| ❌ | `clip.stabilize_2d_rotation_remove` | Remove selected track from rotation stabilization | — |
| ❌ | `clip.stabilize_2d_rotation_select` | Select tracks which are used for rotation stabilization | — |
| ❌ | `clip.stabilize_2d_select` | Select tracks which are used for translation stabilization | — |
| ✅ | `clip.track_color_preset_add` | Add or remove a Clip Track Color Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ❌ | `clip.track_copy_color` | Copy color to all selected tracks | — |
| ❌ | `clip.track_markers` | Track selected markers | `backwards`:BOOLEAN, `sequence`:BOOLEAN |
| ❌ | `clip.track_settings_as_default` | Copy tracking settings from active track to default settings | — |
| ❌ | `clip.track_settings_to_track` | Copy tracking settings from active track to selected tracks | — |
| ❌ | `clip.track_to_empty` | Create an Empty object which will be copying movement of active track | — |
| ❌ | `clip.tracking_object_new` | Add new object for tracking | — |
| ❌ | `clip.tracking_object_remove` | Remove object for tracking | — |
| ✅ | `clip.tracking_settings_preset_add` | Add or remove a motion tracking settings preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ❌ | `clip.update_image_from_plane_marker` | Update current image used by plane marker from the content of the plane marker | — |
| ❌ | `clip.view_all` | View whole image with markers | `fit_view`:BOOLEAN |
| ❌ | `clip.view_center_cursor` | Center the view so that the cursor is in the middle of the view | — |
| ❌ | `clip.view_ndof` | Use a 3D mouse device to pan/zoom the view | — |
| ❌ | `clip.view_pan` | Pan the view | `offset`:FLOAT |
| ❌ | `clip.view_selected` | View all selected elements | — |
| ❌ | `clip.view_zoom` | Zoom in/out the view | `factor`:FLOAT, `use_cursor_init`:BOOLEAN |
| ❌ | `clip.view_zoom_in` | Zoom in the view | `location`:FLOAT |
| ❌ | `clip.view_zoom_out` | Zoom out the view | `location`:FLOAT |
| ❌ | `clip.view_zoom_ratio` | Set the zoom ratio (based on clip size) | `ratio`:FLOAT |

### `cloth` — 1개 (✅ 1 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `cloth.preset_add` | Add or remove a Cloth Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |

### `collection` — 12개 (✅ 9 / ⚠ 0 / ❌ 3)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `collection.create` | Create an object collection from selected objects | `name`:STRING |
| ✅ | `collection.export_all` | Invoke all configured exporters on this collection | — |
| ✅ | `collection.exporter_add` | Add exporter to the exporter list | `name`:STRING |
| ✅ | `collection.exporter_export` | Invoke the export operation | `index`:INT |
| ✅ | `collection.exporter_move` | Move exporter up or down in the exporter list | `direction`=UP/DOWN |
| ❌ | `collection.exporter_remove` | Remove exporter from the exporter list | `index`:INT |
| ❌ | `collection.importer_add` | Add Importer | `name`:STRING |
| ❌ | `collection.importer_remove` | Remove Importer | — |
| ✅ | `collection.objects_add_active` | Add selected objects to one of the collections the active-object is part of. Optionally ad | `collection`= |
| ✅ | `collection.objects_remove` | Remove selected objects from a collection | `collection`= |
| ✅ | `collection.objects_remove_active` | Remove the object from an object collection that contains the active object | `collection`= |
| ✅ | `collection.objects_remove_all` | Remove selected objects from all collections | — |

### `console` — 21개 (✅ 0 / ⚠ 0 / ❌ 21)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `console.autocomplete` | Evaluate the namespace up until the cursor and give a list of options or complete the name | — |
| ❌ | `console.banner` | Print a message when the terminal initializes | — |
| ❌ | `console.clear` | Clear text by type | `scrollback`:BOOLEAN, `history`:BOOLEAN |
| ❌ | `console.clear_line` | Clear the line and store in history | — |
| ❌ | `console.copy` | Copy selected text to clipboard | `delete`:BOOLEAN |
| ❌ | `console.copy_as_script` | Copy the console contents for use in a script | — |
| ❌ | `console.delete` | Delete text by cursor position | `type`=NEXT_CHARACTER/PREVIOUS_CHARACTER/NEXT_WORD/PREVIOUS_WORD |
| ❌ | `console.execute` | Execute the current console line as a Python expression | `interactive`:BOOLEAN |
| ❌ | `console.history_append` | Append history at cursor position | `text`:STRING, `current_character`:INT, `remove_duplicates`:BOOLEAN |
| ❌ | `console.history_cycle` | Cycle through history | `reverse`:BOOLEAN |
| ❌ | `console.indent` | Add 4 spaces at line beginning | — |
| ❌ | `console.indent_or_autocomplete` | Indent selected text or autocomplete | — |
| ❌ | `console.insert` | Insert text at cursor position | `text`:STRING |
| ❌ | `console.language` | Set the current language for this console | `language`:STRING |
| ❌ | `console.move` | Move cursor position | `type`=LINE_BEGIN/LINE_END/PREVIOUS_CHARACTER/NEXT_CHARACTER/PREVIOUS_WORD/NEXT_WORD, `select`:BOOLEAN |
| ❌ | `console.paste` | Paste text from clipboard | `selection`:BOOLEAN |
| ❌ | `console.scrollback_append` | Append scrollback text by type | `text`:STRING, `type`=OUTPUT/INPUT/INFO/ERROR |
| ❌ | `console.select_all` | Select all the text | — |
| ❌ | `console.select_set` | Set the console selection | — |
| ❌ | `console.select_word` | Select word at cursor position | — |
| ❌ | `console.unindent` | Delete 4 spaces from line beginning | — |

### `constraint` — 18개 (✅ 13 / ⚠ 0 / ❌ 5)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `constraint.add_target` | Add a target to the constraint | — |
| ✅ | `constraint.apply` | Apply constraint and remove from the stack | `constraint`:STRING, `owner`=OBJECT/BONE, `report`:BOOLEAN |
| ✅ | `constraint.childof_clear_inverse` | Clear inverse correction for Child Of constraint | `constraint`:STRING, `owner`=OBJECT/BONE |
| ✅ | `constraint.childof_set_inverse` | Set inverse correction for Child Of constraint | `constraint`:STRING, `owner`=OBJECT/BONE |
| ✅ | `constraint.copy` | Duplicate constraint at the same position in the stack | `constraint`:STRING, `owner`=OBJECT/BONE, `report`:BOOLEAN |
| ❌ | `constraint.copy_to_selected` | Copy constraint to other selected objects/bones | `constraint`:STRING, `owner`=OBJECT/BONE |
| ✅ | `constraint.delete` | Remove constraint from constraint stack | `constraint`:STRING, `owner`=OBJECT/BONE, `report`:BOOLEAN |
| ❌ | `constraint.disable_keep_transform` | Set the influence of this constraint to zero while trying to maintain the object's transfo | — |
| ✅ | `constraint.followpath_path_animate` | Add default animation for path used by constraint if it isn't animated already | `constraint`:STRING, `owner`=OBJECT/BONE, `frame_start`:INT, `length`:INT |
| ✅ | `constraint.limitdistance_reset` | Reset limiting distance for Limit Distance Constraint | `constraint`:STRING, `owner`=OBJECT/BONE |
| ✅ | `constraint.move_down` | Move constraint down in constraint stack | `constraint`:STRING, `owner`=OBJECT/BONE |
| ✅ | `constraint.move_to_index` | Change the constraint's position in the list so it evaluates after the set number of other | `constraint`:STRING, `owner`=OBJECT/BONE, `index`:INT |
| ✅ | `constraint.move_up` | Move constraint up in constraint stack | `constraint`:STRING, `owner`=OBJECT/BONE |
| ❌ | `constraint.normalize_target_weights` | Normalize weights of all target bones | — |
| ✅ | `constraint.objectsolver_clear_inverse` | Clear inverse correction for Object Solver constraint | `constraint`:STRING, `owner`=OBJECT/BONE |
| ✅ | `constraint.objectsolver_set_inverse` | Set inverse correction for Object Solver constraint | `constraint`:STRING, `owner`=OBJECT/BONE |
| ❌ | `constraint.remove_target` | Remove the target from the constraint | `index`:INT |
| ✅ | `constraint.stretchto_reset` | Reset original length of bone for Stretch To Constraint | `constraint`:STRING, `owner`=OBJECT/BONE |

### `curve` — 51개 (✅ 6 / ⚠ 0 / ❌ 45)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `curve.cyclic_toggle` | Make active spline closed/open loop | `direction`=CYCLIC_U/CYCLIC_V |
| ❌ | `curve.de_select_first` | (De)select first of visible part of each NURBS | — |
| ❌ | `curve.de_select_last` | (De)select last of visible part of each NURBS | — |
| ❌ | `curve.decimate` | Simplify selected curves | `ratio`:FLOAT |
| ❌ | `curve.delete` | Delete selected control points or segments | `type`=VERT/SEGMENT |
| ❌ | `curve.dissolve_verts` | Delete selected control points, correcting surrounding handles | — |
| ❌ | `curve.draw` | Draw a freehand spline | `error_threshold`:FLOAT, `fit_method`=REFIT/SPLIT, `corner_angle`:FLOAT, `use_cyclic`:BOOLEAN, `stroke`:COLLECTION, `wait_for_input`:BOOLEAN |
| ❌ | `curve.duplicate` | Duplicate selected control points | — |
| ❌ | `curve.duplicate_move` | Duplicate curve and move | `CURVE_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `curve.extrude` | Extrude selected control point(s) | `mode`=INIT/DUMMY/TRANSLATION/ROTATION/RESIZE/SKIN_RESIZE/TOSPHERE/SHEAR/BEND/SHRINKFATTEN/TILT/TRACKBALL/PUSHPULL/CREASE/VERTEX_CREASE/MIRROR/BONE_SIZE/BONE_ENVELOPE/BONE_ENVELOPE_DIST/CURVE_SHRINKFATTEN/MASK_SHRINKFATTEN/BONE_ROLL/TIME_TRANSLATE/TIME_SLIDE/TIME_SCALE/TIME_EXTEND/BAKE_TIME/BWEIGHT/ALIGN/EDGESLIDE/SEQSLIDE/GPENCIL_OPACITY |
| ❌ | `curve.extrude_move` | Extrude curve and move result | `CURVE_OT_extrude`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `curve.handle_type_set` | Set type of handles for selected control points | `type`=AUTOMATIC/VECTOR/ALIGNED/FREE_ALIGN/TOGGLE_FREE_ALIGN |
| ❌ | `curve.hide` | Hide (un)selected control points | `unselected`:BOOLEAN |
| ❌ | `curve.make_segment` | Join two curves by their selected ends | — |
| ✅ | `curve.match_texture_space` | Match texture space to object's bounding box | — |
| ❌ | `curve.normals_make_consistent` | Recalculate the direction of selected handles | `calc_length`:BOOLEAN |
| ❌ | `curve.pen` | Construct and edit splines | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `extrude_point`:BOOLEAN, `extrude_handle`=AUTO/VECTOR, `delete_point`:BOOLEAN, `insert_point`:BOOLEAN, `move_segment`:BOOLEAN, `select_point`:BOOLEAN, `move_point`:BOOLEAN, `close_spline`:BOOLEAN, `close_spline_method`=OFF/ON_PRESS/ON_CLICK, `toggle_vector`:BOOLEAN, `cycle_handle_type`:BOOLEAN |
| ✅ | `curve.primitive_bezier_circle_add` | Construct a Bézier Circle | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `curve.primitive_bezier_curve_add` | Construct a Bézier Curve | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `curve.primitive_nurbs_circle_add` | Construct a Nurbs Circle | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `curve.primitive_nurbs_curve_add` | Construct a Nurbs Curve | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `curve.primitive_nurbs_path_add` | Construct a Path | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `curve.radius_set` | Set per-point radius which is used for bevel tapering | `radius`:FLOAT |
| ❌ | `curve.reveal` | Reveal hidden control points | `select`:BOOLEAN |
| ❌ | `curve.select_all` | (De)select all control points | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `curve.select_less` | Deselect control points at the boundary of each selection region | — |
| ❌ | `curve.select_linked` | Select all control points linked to the current selection | — |
| ❌ | `curve.select_linked_pick` | Select all control points linked to already selected ones | `deselect`:BOOLEAN |
| ❌ | `curve.select_more` | Select control points at the boundary of each selection region | — |
| ❌ | `curve.select_next` | Select control points following already selected ones along the curves | — |
| ❌ | `curve.select_nth` | Deselect every Nth point starting from the active one | `skip`:INT, `nth`:INT, `offset`:INT |
| ❌ | `curve.select_previous` | Select control points preceding already selected ones along the curves | — |
| ❌ | `curve.select_random` | Randomly select some control points | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT |
| ❌ | `curve.select_row` | Select a row of control points including active one. Successive use on the same point swit | — |
| ❌ | `curve.select_similar` | Select similar curve points by property type | `type`=TYPE/RADIUS/WEIGHT/DIRECTION, `compare`=EQUAL/GREATER/LESS, `threshold`:FLOAT |
| ❌ | `curve.separate` | Separate selected points from connected unselected points into a new object | — |
| ❌ | `curve.shade_flat` | Set shading to flat | — |
| ❌ | `curve.shade_smooth` | Set shading to smooth | — |
| ❌ | `curve.shortest_path_pick` | Select shortest path between two selections | — |
| ❌ | `curve.smooth` | Flatten angles of selected points | — |
| ❌ | `curve.smooth_radius` | Interpolate radii of selected points | — |
| ❌ | `curve.smooth_tilt` | Interpolate tilt of selected points | — |
| ❌ | `curve.smooth_weight` | Interpolate weight of selected points | — |
| ❌ | `curve.spin` | Extrude selected boundary row around pivot point and current view axis | `center`:FLOAT, `axis`:FLOAT |
| ❌ | `curve.spline_type_set` | Set type of active spline | `type`=POLY/BEZIER/NURBS, `use_handles`:BOOLEAN |
| ❌ | `curve.spline_weight_set` | Set softbody goal weight for selected points | `weight`:FLOAT |
| ❌ | `curve.split` | Split off selected points from connected unselected points | — |
| ❌ | `curve.subdivide` | Subdivide selected segments | `number_cuts`:INT |
| ❌ | `curve.switch_direction` | Switch direction of selected splines | — |
| ❌ | `curve.tilt_clear` | Clear the tilt of selected control points | — |
| ❌ | `curve.vertex_add` | Add a new control point (linked to only selected end-curve one, if any) | `location`:FLOAT |

### `curves` — 31개 (✅ 2 / ⚠ 1 / ❌ 28)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `curves.add_bezier` | Add new Bézier curve | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `curves.add_circle` | Add new circle curve | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `curves.attribute_set` | Set values of the active attribute for selected elements | `value_float`:FLOAT, `value_float_vector_2d`:FLOAT, `value_float_vector_3d`:FLOAT, `value_float_vector_4d`:FLOAT, `value_int`:INT, `value_int_vector_2d`:INT, `value_color`:FLOAT, `value_bool`:BOOLEAN |
| ✅ | `curves.convert_from_particle_system` | Add a new curves object based on the current state of the particle system | — |
| ❌ | `curves.convert_to_particle_system` | Add a new or update an existing hair particle system on the surface object | — |
| ❌ | `curves.curve_type_set` | Set type of selected curves | `type`=CATMULL_ROM/POLY/BEZIER/NURBS, `use_handles`:BOOLEAN |
| ❌ | `curves.cyclic_toggle` | Make active curve closed/open loop | — |
| ❌ | `curves.delete` | Remove selected control points or curves | — |
| ❌ | `curves.draw` | Draw a freehand curve | `error_threshold`:FLOAT, `fit_method`=REFIT/SPLIT, `corner_angle`:FLOAT, `use_cyclic`:BOOLEAN, `stroke`:COLLECTION, `wait_for_input`:BOOLEAN, `is_curve_2d`:BOOLEAN, `bezier_as_nurbs`:BOOLEAN |
| ❌ | `curves.duplicate` | Copy selected points or curves | — |
| ❌ | `curves.duplicate_move` | Make copies of selected elements and move them | `CURVES_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `curves.extrude` | Extrude selected control point(s) | — |
| ❌ | `curves.extrude_move` | Extrude curve and move result | `CURVES_OT_extrude`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `curves.handle_type_set` | Set the handle type for Bézier curves | `type`=AUTO/VECTOR/ALIGN/FREE_ALIGN/TOGGLE_FREE_ALIGN |
| ✅ | `curves.pen` | Construct and edit Bézier curves | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `extrude_point`:BOOLEAN, `extrude_handle`=AUTO/VECTOR, `delete_point`:BOOLEAN, `insert_point`:BOOLEAN, `move_segment`:BOOLEAN, `select_point`:BOOLEAN, `move_point`:BOOLEAN, `cycle_handle_type`:BOOLEAN, `size`:FLOAT |
| ❌ | `curves.sculptmode_toggle` | Enter/Exit sculpt mode for curves | — |
| ❌ | `curves.select_all` | (De)select all control points | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `curves.select_ends` | Select end points of curves | `amount_start`:INT, `amount_end`:INT |
| ❌ | `curves.select_less` | Shrink the selection by one point | — |
| ❌ | `curves.select_linked` | Select all points in curves with any point selection | — |
| ❌ | `curves.select_linked_pick` | Select all points in the curve under the cursor | `deselect`:BOOLEAN |
| ❌ | `curves.select_more` | Grow the selection by one point | — |
| ❌ | `curves.select_random` | Randomize existing selection or create new random selection | `seed`:INT, `probability`:FLOAT |
| ❌ | `curves.separate` | Separate selected geometry into a new object | — |
| ❌ | `curves.set_selection_domain` | Change the mode used for selection masking in curves sculpt mode | `domain`=POINT/CURVE |
| ❌ | `curves.snap_curves_to_surface` | Move curves so that the first point is exactly on the surface mesh | `attach_mode`=NEAREST/DEFORM |
| ❌ | `curves.split` | Split selected points | — |
| ❌ | `curves.subdivide` | Subdivide selected curve segments | `number_cuts`:INT |
| ⚠ | `curves.surface_set` | Use the active object as surface for selected curves objects and set it as the parent | — |
| ❌ | `curves.switch_direction` | Reverse the direction of the selected curves | — |
| ❌ | `curves.tilt_clear` | Clear the tilt of selected control points | — |

### `cycles` — 3개 (✅ 2 / ⚠ 0 / ❌ 1)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `cycles.denoise_animation` | Denoise rendered animation sequence using current scene and view layer settings. Requires  | `input_filepath`:STRING, `output_filepath`:STRING |
| ✅ | `cycles.merge_images` | Combine OpenEXR multi-layer images rendered with different sample ranges into one image wi | `input_filepath1`:STRING, `input_filepath2`:STRING, `output_filepath`:STRING |
| ❌ | `cycles.use_shading_nodes` | Enable nodes on a light | — |

### `dpaint` — 5개 (✅ 5 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `dpaint.bake` | Bake dynamic paint image sequence surface | — |
| ✅ | `dpaint.output_toggle` | Add or remove Dynamic Paint output data layer | `output`=A/B |
| ✅ | `dpaint.surface_slot_add` | Add a new Dynamic Paint surface slot | — |
| ✅ | `dpaint.surface_slot_remove` | Remove the selected surface slot | — |
| ✅ | `dpaint.type_toggle` | Toggle whether given type is active or not | `type`=CANVAS/BRUSH |

### `ed` — 13개 (✅ 4 / ⚠ 0 / ❌ 9)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `ed.flush_edits` | Flush edit data from active editing modes | — |
| ✅ | `ed.lib_id_fake_user_toggle` | Save this data-block even if it has no users | — |
| ❌ | `ed.lib_id_generate_preview` | Create an automatic preview for the selected data-block | — |
| ❌ | `ed.lib_id_generate_preview_from_object` | Create a preview for this asset by rendering the active object | — |
| ❌ | `ed.lib_id_load_custom_preview` | Choose an image to help identify the data-block visually | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `ed.lib_id_override_editable_toggle` | Set if this library override data-block can be edited | — |
| ❌ | `ed.lib_id_remove_preview` | Remove the preview of this data-block | — |
| ✅ | `ed.lib_id_unlink` | Remove a usage of a data-block, clearing the assignment | — |
| ❌ | `ed.redo` | Redo previous action | — |
| ❌ | `ed.undo` | Undo previous action | — |
| ❌ | `ed.undo_history` | Undo or redo specific action in history | `item`:INT |
| ✅ | `ed.undo_push` | Add an undo state (internal use only) | `message`:STRING |
| ❌ | `ed.undo_redo` | Undo and redo previous action | — |

### `export_anim` — 1개 (✅ 0 / ⚠ 0 / ❌ 1)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `export_anim.bvh` | Save a BVH motion capture file from an armature | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_glob`:STRING, `global_scale`:FLOAT, `frame_start`:INT, `frame_end`:INT, `rotate_mode`=NATIVE/XYZ/XZY/YXZ/YZX/ZXY/ZYX, `root_transform_only`:BOOLEAN, `sort_children_by_names`:BOOLEAN |

### `export_scene` — 2개 (✅ 2 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `export_scene.fbx` | Write a FBX file | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_glob`:STRING, `use_selection`:BOOLEAN, `use_visible`:BOOLEAN, `use_active_collection`:BOOLEAN, `collection`:STRING, `global_scale`:FLOAT, `apply_unit_scale`:BOOLEAN, `apply_scale_options`=FBX_SCALE_NONE/FBX_SCALE_UNITS/FBX_SCALE_CUSTOM/FBX_SCALE_ALL, `use_space_transform`:BOOLEAN, `bake_space_transform`:BOOLEAN, `object_types`=EMPTY/CAMERA/LIGHT/ARMATURE/MESH/OTHER, `use_mesh_modifiers`:BOOLEAN, `use_mesh_modifiers_render`:BOOLEAN, `mesh_smooth_type`=OFF/FACE/EDGE/SMOOTH_GROUP, `colors_type`=NONE/SRGB/LINEAR, `prioritize_active_color`:BOOLEAN, `use_subsurf`:BOOLEAN, `use_mesh_edges`:BOOLEAN, `use_tspace`:BOOLEAN, `use_triangles`:BOOLEAN, `use_custom_props`:BOOLEAN, `add_leaf_bones`:BOOLEAN, `primary_bone_axis`=X/Y/Z/-X/-Y/-Z, `secondary_bone_axis`=X/Y/Z/-X/-Y/-Z, `use_armature_deform_only`:BOOLEAN, `armature_nodetype`=NULL/ROOT/LIMBNODE, `bake_anim`:BOOLEAN, `bake_anim_use_all_bones`:BOOLEAN, `bake_anim_use_nla_strips`:BOOLEAN, `bake_anim_use_all_actions`:BOOLEAN, `bake_anim_force_startend_keying`:BOOLEAN, `bake_anim_step`:FLOAT, `bake_anim_simplify_factor`:FLOAT, `path_mode`=AUTO/ABSOLUTE/RELATIVE/MATCH/STRIP/COPY, `embed_textures`:BOOLEAN, `batch_mode`=OFF/SCENE/COLLECTION/SCENE_COLLECTION/ACTIVE_SCENE_COLLECTION, `use_batch_own_dir`:BOOLEAN, `use_metadata`:BOOLEAN, `axis_forward`=X/Y/Z/-X/-Y/-Z, `axis_up`=X/Y/Z/-X/-Y/-Z |
| ✅ | `export_scene.gltf` | Export scene as glTF 2.0 file | `filepath`:STRING, `check_existing`:BOOLEAN, `export_import_convert_lighting_mode`=SPEC/COMPAT/RAW, `gltf_export_id`:STRING, `export_use_gltfpack`:BOOLEAN, `export_gltfpack_tc`:BOOLEAN, `export_gltfpack_tq`:INT, `export_gltfpack_si`:FLOAT, `export_gltfpack_sa`:BOOLEAN, `export_gltfpack_slb`:BOOLEAN, `export_gltfpack_vp`:INT, `export_gltfpack_vt`:INT, `export_gltfpack_vn`:INT, `export_gltfpack_vc`:INT, `export_gltfpack_vpi`=Integer/Normalized/Floating-point, `export_gltfpack_noq`:BOOLEAN, `export_gltfpack_kn`:BOOLEAN, `export_format`=, `ui_tab`=GENERAL/MESHES/OBJECTS/ANIMATION, `export_copyright`:STRING, `export_image_format`=AUTO/JPEG/WEBP/NONE, `export_image_add_webp`:BOOLEAN, `export_image_webp_fallback`:BOOLEAN, `export_texture_dir`:STRING, `export_jpeg_quality`:INT, `export_image_quality`:INT, `export_keep_originals`:BOOLEAN, `export_texcoords`:BOOLEAN, `export_normals`:BOOLEAN, `export_gn_mesh`:BOOLEAN, `export_meshopt_compression_enable`:BOOLEAN, `export_meshopt_extension`=EXT_meshopt_compression/KHR_meshopt_compression, `export_draco_mesh_compression_enable`:BOOLEAN, `export_draco_mesh_compression_level`:INT, `export_draco_position_quantization`:INT, `export_draco_normal_quantization`:INT, `export_draco_texcoord_quantization`:INT, `export_draco_color_quantization`:INT, `export_draco_generic_quantization`:INT, `export_tangents`:BOOLEAN, `export_materials`=EXPORT/PLACEHOLDER/VIEWPORT/NONE, `export_unused_images`:BOOLEAN, `export_unused_textures`:BOOLEAN, `export_vertex_color`=MATERIAL/ACTIVE/NAME/NONE, `export_vertex_color_name`:STRING, `export_all_vertex_colors`:BOOLEAN, `export_active_vertex_color_when_no_material`:BOOLEAN, `export_attributes`:BOOLEAN, `use_mesh_edges`:BOOLEAN, `use_mesh_vertices`:BOOLEAN, `export_cameras`:BOOLEAN, `use_selection`:BOOLEAN, `use_visible`:BOOLEAN, `use_renderable`:BOOLEAN, `use_active_collection_with_nested`:BOOLEAN, `use_active_collection`:BOOLEAN, `use_active_scene`:BOOLEAN, `collection`:STRING, `at_collection_center`:BOOLEAN, `export_extras`:BOOLEAN, `export_yup`:BOOLEAN, `export_apply`:BOOLEAN, `export_shared_accessors`:BOOLEAN, `export_animations`:BOOLEAN, `export_frame_range`:BOOLEAN, `export_frame_step`:INT, `export_force_sampling`:BOOLEAN, `export_sampling_interpolation_fallback`=LINEAR/STEP, `export_pointer_animation`:BOOLEAN, `export_animation_mode`=ACTIONS/ACTIVE_ACTIONS/BROADCAST/NLA_TRACKS/SCENE, `export_nla_strips_merged_animation_name`:STRING, `export_def_bones`:BOOLEAN, `export_hierarchy_flatten_bones`:BOOLEAN, `export_hierarchy_flatten_objs`:BOOLEAN, `export_armature_object_remove`:BOOLEAN, `export_leaf_bone`:BOOLEAN, `export_optimize_animation_size`:BOOLEAN, `export_optimize_animation_keep_anim_armature`:BOOLEAN, `export_optimize_animation_keep_anim_object`:BOOLEAN, `export_optimize_disable_viewport`:BOOLEAN, `export_negative_frame`=SLIDE/CROP, `export_anim_slide_to_zero`:BOOLEAN, `export_bake_animation`:BOOLEAN, `export_merge_animation`=NLA_TRACK/ACTION/NONE, `export_anim_single_armature`:BOOLEAN, `export_reset_pose_bones`:BOOLEAN, `export_current_frame`:BOOLEAN, `export_rest_position_armature`:BOOLEAN, `export_anim_scene_split_object`:BOOLEAN, `export_skins`:BOOLEAN, `export_influence_nb`:INT, `export_all_influences`:BOOLEAN, `export_morph`:BOOLEAN, `export_morph_normal`:BOOLEAN, `export_morph_tangent`:BOOLEAN, `export_morph_animation`:BOOLEAN, `export_morph_reset_sk_data`:BOOLEAN, `export_lights`:BOOLEAN, `export_try_sparse_sk`:BOOLEAN, `export_try_omit_sparse_sk`:BOOLEAN, `export_gpu_instances`:BOOLEAN, `export_action_filter`:BOOLEAN, `export_convert_animation_pointer`:BOOLEAN, `export_nla_strips`:BOOLEAN, `export_original_specular`:BOOLEAN, `will_save_settings`:BOOLEAN, `export_hierarchy_full_collections`:BOOLEAN, `export_extra_animations`:BOOLEAN, `export_loglevel`:INT, `filter_glob`:STRING |

### `extensions` — 32개 (✅ 27 / ⚠ 0 / ❌ 5)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `extensions.package_disable` | Turn off this extension | — |
| ❌ | `extensions.package_install` | Download and install the extension | `repo_directory`:STRING, `repo_index`:INT, `pkg_id`:STRING, `enable_on_install`:BOOLEAN, `url`:STRING, `do_legacy_replace`:BOOLEAN |
| ✅ | `extensions.package_install_files` | Install extensions from files into a locally managed repository | `filter_glob`:STRING, `directory`:STRING, `files`:COLLECTION, `filepath`:STRING, `repo`=, `enable_on_install`:BOOLEAN, `target`=, `overwrite`:BOOLEAN, `url`:STRING |
| ✅ | `extensions.package_install_marked` | (undocumented operator) | `enable_on_install`:BOOLEAN |
| ✅ | `extensions.package_mark_clear` | (undocumented operator) | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_mark_clear_all` | (undocumented operator) | — |
| ✅ | `extensions.package_mark_set` | (undocumented operator) | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_mark_set_all` | (undocumented operator) | — |
| ✅ | `extensions.package_obsolete_marked` | Zeroes package versions, useful for development - to test upgrading | — |
| ✅ | `extensions.package_show_clear` | (undocumented operator) | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_show_set` | (undocumented operator) | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_show_settings` | (undocumented operator) | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_theme_disable` | Reset to the default theme if this theme is active | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_theme_enable` | Turn on this theme | `pkg_id`:STRING, `repo_index`:INT |
| ✅ | `extensions.package_uninstall` | Disable and uninstall the extension | `repo_directory`:STRING, `repo_index`:INT, `pkg_id`:STRING |
| ✅ | `extensions.package_uninstall_marked` | (undocumented operator) | — |
| ❌ | `extensions.package_uninstall_system` | (undocumented operator) | — |
| ❌ | `extensions.package_upgrade_all` | Upgrade installed extensions to their latest version from remote repositories | `use_active_only`:BOOLEAN |
| ✅ | `extensions.repo_enable_from_drop` | (undocumented operator) | `repo_index`:INT |
| ✅ | `extensions.repo_lock_all` | Lock repositories - to test locking | — |
| ✅ | `extensions.repo_refresh_all` | Refresh extension & legacy add-ons, reloading modules & meta-data (similar to restarting) | `use_active_only`:BOOLEAN |
| ✅ | `extensions.repo_sync` | (undocumented operator) | `repo_directory`:STRING, `repo_index`:INT |
| ❌ | `extensions.repo_sync_all` | Refresh the list of extensions for all the remote repositories | `use_active_only`:BOOLEAN |
| ❌ | `extensions.repo_unlock` | Remove the repository file-system lock | — |
| ✅ | `extensions.repo_unlock_all` | Unlock repositories - to test unlocking | — |
| ✅ | `extensions.status_clear` | (undocumented operator) | — |
| ✅ | `extensions.status_clear_errors` | (undocumented operator) | — |
| ✅ | `extensions.userpref_allow_online` | Allow Blender to access the internet. Add-ons that follow this setting will only connect t | — |
| ✅ | `extensions.userpref_allow_online_popup` | Allow Blender to access the internet. Add-ons that follow this setting will only connect t | — |
| ✅ | `extensions.userpref_show_for_update` | Open extensions preferences | — |
| ✅ | `extensions.userpref_show_online` | Show system preferences "Network" panel to allow online access | — |
| ✅ | `extensions.userpref_tags_set` | Set the value of all tags | `value`:BOOLEAN, `data_path`:STRING |

### `file` — 40개 (✅ 11 / ⚠ 0 / ❌ 29)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `file.autopack_toggle` | Automatically pack all external files into the .blend file | — |
| ❌ | `file.bookmark_add` | Add a bookmark for the selected/active directory | — |
| ❌ | `file.bookmark_cleanup` | Delete all invalid bookmarks | — |
| ❌ | `file.bookmark_delete` | Delete selected bookmark | `index`:INT |
| ❌ | `file.bookmark_move` | Move the active bookmark up/down in the list | `direction`=TOP/UP/DOWN/BOTTOM |
| ❌ | `file.cancel` | Cancel file operation | — |
| ❌ | `file.delete` | Move selected files to the trash or recycle bin | — |
| ❌ | `file.directory_new` | Create a new directory | `directory`:STRING, `open`:BOOLEAN, `confirm`:BOOLEAN |
| ❌ | `file.edit_directory_path` | Start editing directory field | — |
| ❌ | `file.execute` | Execute selected file | — |
| ✅ | `file.external_operation` | Perform external operation on a file or folder | `operation`=OPEN/FOLDER_OPEN/EDIT/NEW/FIND/SHOW/PLAY/BROWSE/PREVIEW/PRINT/INSTALL/RUNAS/PROPERTIES/FOLDER_FIND/CMD |
| ❌ | `file.filenum` | Increment number in filename | `increment`:INT |
| ❌ | `file.filepath_drop` | (undocumented operator) | `filepath`:STRING |
| ✅ | `file.find_missing_files` | Try to find missing external files | `find_all`:BOOLEAN, `directory`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `file.hidedot` | Toggle hide hidden dot files | — |
| ❌ | `file.highlight` | Highlight selected file(s) | — |
| ✅ | `file.make_paths_absolute` | Make all paths to external files absolute | — |
| ✅ | `file.make_paths_relative` | Make all paths to external files relative to current .blend | — |
| ❌ | `file.mouse_execute` | Perform the current execute action for the file under the cursor (e.g. open the file) | — |
| ❌ | `file.next` | Move to next folder | — |
| ✅ | `file.pack_all` | Pack all used external files into this .blend | — |
| ✅ | `file.pack_libraries` | Store all data-blocks linked from other .blend files in the current .blend file. Library r | — |
| ❌ | `file.parent` | Move to parent directory | — |
| ❌ | `file.previous` | Move to previous folder | — |
| ❌ | `file.refresh` | Refresh the file list | — |
| ❌ | `file.rename` | Rename file or file directory | — |
| ✅ | `file.report_missing_files` | Report all missing external files | — |
| ❌ | `file.reset_recent` | Reset recent files | — |
| ❌ | `file.select` | Handle mouse clicks to select and activate items | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `fill`:BOOLEAN, `open`:BOOLEAN, `deselect_all`:BOOLEAN, `only_activate_if_selected`:BOOLEAN, `pass_through`:BOOLEAN |
| ❌ | `file.select_all` | Select or deselect all files | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `file.select_bookmark` | Select a bookmarked directory | `dir`:STRING |
| ❌ | `file.select_box` | Activate/select the file(s) contained in the border | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `file.select_walk` | Select/Deselect files by walking through them | `direction`=UP/DOWN/LEFT/RIGHT, `extend`:BOOLEAN, `fill`:BOOLEAN |
| ❌ | `file.smoothscroll` | Smooth scroll to make editable file visible | — |
| ❌ | `file.sort_column_ui_context` | Change sorting to use column under cursor | — |
| ❌ | `file.start_filter` | Start entering filter text | — |
| ✅ | `file.unpack_all` | Unpack all files packed into this .blend to external ones | `method`=USE_LOCAL/WRITE_LOCAL/USE_ORIGINAL/WRITE_ORIGINAL/KEEP/REMOVE |
| ✅ | `file.unpack_item` | Unpack this file to an external file | `method`=USE_LOCAL/WRITE_LOCAL/USE_ORIGINAL/WRITE_ORIGINAL, `id_name`:STRING, `id_type`:INT |
| ✅ | `file.unpack_libraries` | Restore all packed linked data-blocks to their original locations | — |
| ❌ | `file.view_selected` | Scroll the selected files into view | — |

### `fluid` — 14개 (✅ 14 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `fluid.bake_all` | Bake Entire Fluid Simulation | — |
| ✅ | `fluid.bake_data` | Bake Fluid Data | — |
| ✅ | `fluid.bake_guides` | Bake Fluid Guiding | — |
| ✅ | `fluid.bake_mesh` | Bake Fluid Mesh | — |
| ✅ | `fluid.bake_noise` | Bake Fluid Noise | — |
| ✅ | `fluid.bake_particles` | Bake Fluid Particles | — |
| ✅ | `fluid.free_all` | Free Entire Fluid Simulation | — |
| ✅ | `fluid.free_data` | Free Fluid Data | — |
| ✅ | `fluid.free_guides` | Free Fluid Guiding | — |
| ✅ | `fluid.free_mesh` | Free Fluid Mesh | — |
| ✅ | `fluid.free_noise` | Free Fluid Noise | — |
| ✅ | `fluid.free_particles` | Free Fluid Particles | — |
| ✅ | `fluid.pause_bake` | Pause Bake | — |
| ✅ | `fluid.preset_add` | Add or remove a Fluid Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |

### `font` — 23개 (✅ 4 / ⚠ 0 / ❌ 19)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `font.case_set` | Set font case | `case`=LOWER/UPPER |
| ❌ | `font.case_toggle` | Toggle font case | — |
| ❌ | `font.change_character` | Change font character code | `delta`:INT |
| ❌ | `font.change_spacing` | Change font spacing | `delta`:FLOAT |
| ❌ | `font.delete` | Delete text by cursor position | `type`=NEXT_CHARACTER/PREVIOUS_CHARACTER/NEXT_WORD/PREVIOUS_WORD/SELECTION/NEXT_OR_SELECTION/PREVIOUS_OR_SELECTION |
| ❌ | `font.line_break` | Insert line break at cursor position | — |
| ❌ | `font.move` | Move cursor to position type | `type`=LINE_BEGIN/LINE_END/TEXT_BEGIN/TEXT_END/PREVIOUS_CHARACTER/NEXT_CHARACTER/PREVIOUS_WORD/NEXT_WORD/PREVIOUS_LINE/NEXT_LINE/PREVIOUS_PAGE/NEXT_PAGE |
| ❌ | `font.move_select` | Move the cursor while selecting | `type`=LINE_BEGIN/LINE_END/TEXT_BEGIN/TEXT_END/PREVIOUS_CHARACTER/NEXT_CHARACTER/PREVIOUS_WORD/NEXT_WORD/PREVIOUS_LINE/NEXT_LINE/PREVIOUS_PAGE/NEXT_PAGE |
| ✅ | `font.open` | Load a new font from a file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `font.select_all` | Select all text | — |
| ❌ | `font.select_word` | Select word under cursor | — |
| ❌ | `font.selection_set` | Set cursor selection | — |
| ❌ | `font.style_set` | Set font style | `style`=BOLD/ITALIC/UNDERLINE/SMALL_CAPS, `clear`:BOOLEAN |
| ❌ | `font.style_toggle` | Toggle font style | `style`=BOLD/ITALIC/UNDERLINE/SMALL_CAPS |
| ❌ | `font.text_copy` | Copy selected text to clipboard | — |
| ❌ | `font.text_cut` | Cut selected text to clipboard | — |
| ❌ | `font.text_insert` | Insert text at cursor position | `text`:STRING, `accent`:BOOLEAN |
| ❌ | `font.text_insert_unicode` | Insert Unicode Character | — |
| ❌ | `font.text_paste` | Paste text from clipboard | `selection`:BOOLEAN |
| ❌ | `font.text_paste_from_file` | Paste contents from file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ✅ | `font.textbox_add` | Add a new text box | — |
| ✅ | `font.textbox_remove` | Remove the text box | `index`:INT |
| ✅ | `font.unlink` | Unlink active font data-block | — |

### `geometry` — 9개 (✅ 1 / ⚠ 3 / ❌ 5)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ⚠ | `geometry.attribute_add` | Add attribute to geometry | `name`:STRING, `domain`=POINT/EDGE/FACE/CORNER/CURVE/INSTANCE/LAYER, `data_type`=FLOAT/INT/BOOLEAN/FLOAT_VECTOR/FLOAT_COLOR/QUATERNION/FLOAT4X4/STRING/INT8/INT16_2D/INT32_2D/FLOAT2/FLOAT4/BYTE_COLOR |
| ❌ | `geometry.attribute_convert` | Change how the attribute is stored | `mode`=GENERIC/VERTEX_GROUP, `domain`=POINT/EDGE/FACE/CORNER/CURVE/INSTANCE/LAYER, `data_type`=FLOAT/INT/BOOLEAN/FLOAT_VECTOR/FLOAT_COLOR/QUATERNION/FLOAT4X4/STRING/INT8/INT16_2D/INT32_2D/FLOAT2/FLOAT4/BYTE_COLOR |
| ❌ | `geometry.attribute_remove` | Remove attribute from geometry | — |
| ⚠ | `geometry.color_attribute_add` | Add color attribute to geometry | `name`:STRING, `domain`=POINT/CORNER, `data_type`=FLOAT_COLOR/BYTE_COLOR, `color`:FLOAT |
| ❌ | `geometry.color_attribute_convert` | Change how the color attribute is stored | `domain`=POINT/CORNER, `data_type`=FLOAT_COLOR/BYTE_COLOR |
| ❌ | `geometry.color_attribute_duplicate` | Duplicate color attribute | — |
| ❌ | `geometry.color_attribute_remove` | Remove color attribute from geometry | — |
| ⚠ | `geometry.color_attribute_render_set` | Set default color attribute used for rendering | `name`:STRING |
| ✅ | `geometry.geometry_randomization` | Toggle geometry randomization for debugging purposes | `value`:BOOLEAN |

### `gizmogroup` — 2개 (✅ 0 / ⚠ 0 / ❌ 2)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `gizmogroup.gizmo_select` | Select the currently highlighted gizmo | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN |
| ❌ | `gizmogroup.gizmo_tweak` | Tweak the active gizmo | — |

### `gpencil` — 7개 (✅ 0 / ⚠ 0 / ❌ 7)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `gpencil.annotate` | Make annotations on the active data | `mode`=DRAW/DRAW_STRAIGHT/DRAW_POLY/ERASER, `arrowstyle_start`=NONE/ARROW/ARROW_OPEN/ARROW_OPEN_INVERTED/DIAMOND, `arrowstyle_end`=NONE/ARROW/ARROW_OPEN/ARROW_OPEN_INVERTED/DIAMOND, `use_stabilizer`:BOOLEAN, `stabilizer_factor`:FLOAT, `stabilizer_radius`:INT, `stroke`:COLLECTION, `wait_for_input`:BOOLEAN |
| ❌ | `gpencil.annotation_active_frame_delete` | Delete the active frame for the active Annotation Layer | — |
| ❌ | `gpencil.annotation_add` | Add new Annotation data-block | — |
| ❌ | `gpencil.data_unlink` | Unlink active Annotation data-block | — |
| ❌ | `gpencil.layer_annotation_add` | Add new Annotation layer or note for the active data-block | — |
| ❌ | `gpencil.layer_annotation_move` | Move the active Annotation layer up/down in the list | `type`=UP/DOWN |
| ❌ | `gpencil.layer_annotation_remove` | Remove active Annotation layer | — |

### `graph` — 67개 (✅ 0 / ⚠ 0 / ❌ 67)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `graph.bake_keys` | Add keyframes on every frame between the selected keyframes | — |
| ❌ | `graph.blend_offset` | Shift selected keys to the value of the neighboring keys as a block | `factor`:FLOAT |
| ❌ | `graph.blend_to_default` | Blend selected keys to their default value from their current position | `factor`:FLOAT |
| ❌ | `graph.blend_to_ease` | Blends keyframes from current state to an ease-in or ease-out curve | `factor`:FLOAT |
| ❌ | `graph.blend_to_neighbor` | Blend selected keyframes to their left or right neighbor | `factor`:FLOAT |
| ❌ | `graph.breakdown` | Move selected keyframes to an inbetween position relative to adjacent keys | `factor`:FLOAT |
| ❌ | `graph.butterworth_smooth` | Smooth an F-Curve while maintaining the general shape of the curve | `cutoff_frequency`:FLOAT, `filter_order`:INT, `samples_per_frame`:INT, `blend`:FLOAT, `blend_in_out`:INT |
| ❌ | `graph.clean` | Simplify F-Curves by removing closely spaced keyframes | `threshold`:FLOAT, `channels`:BOOLEAN |
| ❌ | `graph.click_insert` | Insert new keyframe at the cursor position for the active F-Curve | `frame`:FLOAT, `value`:FLOAT, `extend`:BOOLEAN |
| ❌ | `graph.clickselect` | Select keyframes by clicking on them | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `deselect_all`:BOOLEAN, `column`:BOOLEAN, `curves`:BOOLEAN |
| ❌ | `graph.copy` | Copy selected keyframes to the internal clipboard | — |
| ❌ | `graph.cursor_set` | Interactively set the current frame and value cursor | `frame`:FLOAT, `value`:FLOAT |
| ❌ | `graph.decimate` | Decimate F-Curves by removing keyframes that influence the curve shape the least | `mode`=RATIO/ERROR, `factor`:FLOAT, `remove_error_margin`:FLOAT |
| ❌ | `graph.delete` | Remove all selected keyframes | `confirm`:BOOLEAN |
| ❌ | `graph.driver_delete_invalid` | Delete all visible drivers considered invalid | — |
| ❌ | `graph.driver_variables_copy` | Copy the driver variables of the active driver | — |
| ❌ | `graph.driver_variables_paste` | Add copied driver variables to the active driver | `replace`:BOOLEAN |
| ❌ | `graph.duplicate` | Make a copy of all selected keyframes | `mode`=INIT/DUMMY/TRANSLATION/ROTATION/RESIZE/SKIN_RESIZE/TOSPHERE/SHEAR/BEND/SHRINKFATTEN/TILT/TRACKBALL/PUSHPULL/CREASE/VERTEX_CREASE/MIRROR/BONE_SIZE/BONE_ENVELOPE/BONE_ENVELOPE_DIST/CURVE_SHRINKFATTEN/MASK_SHRINKFATTEN/BONE_ROLL/TIME_TRANSLATE/TIME_SLIDE/TIME_SCALE/TIME_EXTEND/BAKE_TIME/BWEIGHT/ALIGN/EDGESLIDE/SEQSLIDE/GPENCIL_OPACITY |
| ❌ | `graph.duplicate_move` | Make a copy of all selected keyframes and move them | `GRAPH_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `graph.ease` | Align keyframes on a ease-in or ease-out curve | `factor`:FLOAT, `sharpness`:FLOAT |
| ❌ | `graph.easing_type` | Set easing type for the F-Curve segments starting from the selected keyframes | `type`=AUTO/EASE_IN/EASE_OUT/EASE_IN_OUT |
| ❌ | `graph.equalize_handles` | Ensure selected keyframes' handles have equal length, optionally making them horizontal. A | `side`=LEFT/RIGHT/BOTH, `handle_length`:FLOAT, `flatten`:BOOLEAN |
| ❌ | `graph.euler_filter` | Fix large jumps and flips in the selected Euler Rotation F-Curves arising from rotation va | — |
| ❌ | `graph.extrapolation_type` | Set extrapolation mode for selected F-Curves | `type`=CONSTANT/LINEAR/MAKE_CYCLIC/CLEAR_CYCLIC |
| ❌ | `graph.fmodifier_add` | Add F-Modifier to the active/selected F-Curves | `type`=NULL/GENERATOR/FNGENERATOR/ENVELOPE/CYCLES/NOISE/LIMITS/STEPPED/SMOOTH, `only_active`:BOOLEAN |
| ❌ | `graph.fmodifier_copy` | Copy the F-Modifier(s) of the active F-Curve | — |
| ❌ | `graph.fmodifier_delete` | Remove Modifier(s) from the selected F-Curves | `mode`=ALL/FIRST/TYPE, `type`=NULL/GENERATOR/FNGENERATOR/ENVELOPE/CYCLES/NOISE/LIMITS/STEPPED/SMOOTH |
| ❌ | `graph.fmodifier_paste` | Add copied F-Modifiers to the selected F-Curves | `only_active`:BOOLEAN, `replace`:BOOLEAN |
| ❌ | `graph.frame_jump` | Place the cursor on the midpoint of selected keyframes | — |
| ❌ | `graph.gaussian_smooth` | Smooth the curve using a Gaussian filter | `factor`:FLOAT, `sigma`:FLOAT, `filter_width`:INT |
| ❌ | `graph.ghost_curves_clear` | Clear F-Curve snapshots (Ghosts) for active Graph Editor | — |
| ❌ | `graph.ghost_curves_create` | Create snapshot (Ghosts) of selected F-Curves as background aid for active Graph Editor | — |
| ❌ | `graph.handle_type` | Set type of handle for selected keyframes | `type`=FREE/ALIGNED/VECTOR/AUTO/AUTO_CLAMPED |
| ❌ | `graph.hide` | Hide selected curves from Graph Editor view | `unselected`:BOOLEAN |
| ❌ | `graph.interpolation_type` | Set interpolation mode for the F-Curve segments starting from the selected keyframes | `type`=CONSTANT/LINEAR/BEZIER/SINE/QUAD/CUBIC/QUART/QUINT/EXPO/CIRC/BACK/BOUNCE/ELASTIC |
| ❌ | `graph.keyframe_insert` | Insert keyframes for the specified channels | `type`=ALL/SEL/ACTIVE/CURSOR_ACTIVE/CURSOR_SEL |
| ❌ | `graph.keyframe_jump` | Jump to previous/next keyframe | `next`:BOOLEAN |
| ❌ | `graph.keys_to_samples` | Convert selected channels to an uneditable set of samples to save storage space | — |
| ❌ | `graph.local_view` | Isolate selected F-Curves in Graph Editor view | `frame_selected`:BOOLEAN |
| ❌ | `graph.match_slope` | Blend selected keys to the slope of neighboring ones | `factor`:FLOAT |
| ❌ | `graph.mirror` | Flip selected keyframes over the selected mirror line | `type`=CFRA/MARKER/YAXIS/VALUE/XAXIS |
| ❌ | `graph.paste` | Paste keyframes from the internal clipboard for the selected channels, starting on the cur | `offset`=START/END/RELATIVE/NONE, `value_offset`=LEFT_KEY/RIGHT_KEY/CURRENT_FRAME/CURSOR_VALUE/NONE, `merge`=MIX/OVER_ALL/OVER_RANGE/OVER_RANGE_ALL, `flipped`:BOOLEAN |
| ❌ | `graph.previewrange_set` | Set Preview Range based on range of selected keyframes | — |
| ❌ | `graph.push_pull` | Exaggerate or minimize the value of the selected keys | `factor`:FLOAT |
| ❌ | `graph.reveal` | Make previously hidden curves visible again in Graph Editor view | `select`:BOOLEAN |
| ❌ | `graph.samples_to_keys` | Convert selected channels from samples to keyframes | — |
| ❌ | `graph.scale_average` | Scale selected key values by their combined average | `factor`:FLOAT |
| ❌ | `graph.scale_from_neighbor` | Increase or decrease the value of selected keys in relationship to the neighboring one | `factor`:FLOAT, `anchor`=LEFT/RIGHT |
| ❌ | `graph.select_all` | Toggle selection of all keyframes | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `graph.select_box` | Select all keyframes within the specified region | `axis_range`:BOOLEAN, `include_handles`:BOOLEAN, `tweak`:BOOLEAN, `use_curve_selection`:BOOLEAN, `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `graph.select_circle` | Select keyframe points using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB, `include_handles`:BOOLEAN, `use_curve_selection`:BOOLEAN |
| ❌ | `graph.select_column` | Select all keyframes on the specified frame(s) | `mode`=KEYS/CFRA/MARKERS_COLUMN/MARKERS_BETWEEN |
| ❌ | `graph.select_key_handles` | For selected keyframes, select/deselect any combination of the key itself and its handles | `left_handle_action`=SELECT/DESELECT/KEEP, `right_handle_action`=SELECT/DESELECT/KEEP, `key_action`=SELECT/DESELECT/KEEP |
| ❌ | `graph.select_lasso` | Select keyframe points using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB, `include_handles`:BOOLEAN, `use_curve_selection`:BOOLEAN |
| ❌ | `graph.select_leftright` | Select keyframes to the left or the right of the current frame | `mode`=LEFT/RIGHT/CHECK, `extend`:BOOLEAN |
| ❌ | `graph.select_less` | Deselect keyframes on ends of selection islands | — |
| ❌ | `graph.select_linked` | Select keyframes occurring in the same F-Curves as selected ones | — |
| ❌ | `graph.select_more` | Select keyframes beside already selected ones | — |
| ❌ | `graph.shear` | Affect the value of the keys linearly, keeping the same relationship between them using ei | `factor`:FLOAT, `direction`=FROM_LEFT/FROM_RIGHT |
| ❌ | `graph.smooth` | Apply weighted moving means to make selected F-Curves less bumpy | — |
| ❌ | `graph.snap` | Snap selected keyframes to the chosen times/values | `type`=CFRA/VALUE/NEAREST_FRAME/NEAREST_SECOND/NEAREST_MARKER/HORIZONTAL |
| ❌ | `graph.snap_cursor_value` | Place the cursor value on the average value of selected keyframes | — |
| ❌ | `graph.sound_to_samples` | Bakes a sound wave to samples on selected channels | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `low`:FLOAT, `high`:FLOAT, `attack`:FLOAT, `release`:FLOAT, `threshold`:FLOAT, `use_accumulate`:BOOLEAN, `use_additive`:BOOLEAN, `use_square`:BOOLEAN, `sthreshold`:FLOAT |
| ❌ | `graph.time_offset` | Shifts the value of selected keys in time | `frame_offset`:FLOAT |
| ❌ | `graph.view_all` | Reset viewable area to show full keyframe range | `include_handles`:BOOLEAN |
| ❌ | `graph.view_frame` | Move the view to the current frame | — |
| ❌ | `graph.view_selected` | Reset viewable area to show selected keyframe range | `include_handles`:BOOLEAN |

### `grease_pencil` — 123개 (✅ 7 / ⚠ 0 / ❌ 116)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `grease_pencil.active_frame_delete` | Delete the active Grease Pencil frame(s) | `all`:BOOLEAN |
| ❌ | `grease_pencil.bake_grease_pencil_animation` | Bake Grease Pencil object transform to Grease Pencil keyframes | `frame_start`:INT, `frame_end`:INT, `step`:INT, `only_selected`:BOOLEAN, `frame_target`:INT, `project_type`=KEEP/FRONT/SIDE/TOP/VIEW/CURSOR |
| ❌ | `grease_pencil.brush_stroke` | Draw a new stroke in the active Grease Pencil object | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN |
| ❌ | `grease_pencil.caps_set` | Change curve caps mode (rounded or flat) | `type`=ROUND/FLAT/START/END |
| ❌ | `grease_pencil.clean_loose` | Remove loose points | `limit`:INT |
| ❌ | `grease_pencil.convert_curve_type` | Convert type of selected curves | `type`=CATMULL_ROM/POLY/BEZIER/NURBS, `threshold`:FLOAT |
| ❌ | `grease_pencil.copy` | Copy the selected Grease Pencil points or strokes to the internal clipboard | — |
| ❌ | `grease_pencil.cyclical_set` | Close or open the selected stroke adding a segment from last to first point | `type`=CLOSE/OPEN/TOGGLE, `subdivide_cyclic_segment`:BOOLEAN |
| ❌ | `grease_pencil.delete` | Delete selected strokes or points | `mode`=ALL/STROKES/FILLS |
| ❌ | `grease_pencil.delete_breakdown` | Remove breakdown frames generated by interpolating between two Grease Pencil frames | — |
| ❌ | `grease_pencil.delete_frame` | Delete Grease Pencil Frame(s) | `type`=ACTIVE_FRAME/ALL_FRAMES |
| ❌ | `grease_pencil.dissolve` | Delete selected points without splitting strokes | `type`=POINTS/BETWEEN/UNSELECT |
| ❌ | `grease_pencil.duplicate` | Duplicate the selected points | — |
| ❌ | `grease_pencil.duplicate_move` | Make copies of the selected Grease Pencil strokes and move them | `GREASE_PENCIL_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `grease_pencil.erase_box` | Erase points in the box region | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `grease_pencil.erase_lasso` | Erase points in the lasso region | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT |
| ❌ | `grease_pencil.extrude` | Extrude the selected points | — |
| ❌ | `grease_pencil.extrude_move` | Extrude selected points and move them | `GREASE_PENCIL_OT_extrude`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `grease_pencil.fill` | Fill with color the shape formed by strokes | `invert`:BOOLEAN, `precision`:BOOLEAN |
| ❌ | `grease_pencil.frame_clean_duplicate` | Remove any keyframe that is a duplicate of the previous one | `selected`:BOOLEAN |
| ❌ | `grease_pencil.frame_duplicate` | Make a copy of the active Grease Pencil frame(s) | `all`:BOOLEAN |
| ❌ | `grease_pencil.insert_blank_frame` | Insert a blank frame on the current scene frame | `all_layers`:BOOLEAN, `duration`:INT |
| ❌ | `grease_pencil.interpolate` | Interpolate Grease Pencil strokes between frames | `shift`:FLOAT, `layers`=ACTIVE/ALL, `exclude_breakdowns`:BOOLEAN, `use_selection`:BOOLEAN, `flip`=NONE/FLIP/AUTO, `smooth_steps`:INT, `smooth_factor`:FLOAT |
| ❌ | `grease_pencil.interpolate_sequence` | Generate 'in-betweens' to smoothly interpolate between Grease Pencil frames | `step`:INT, `layers`=ACTIVE/ALL, `exclude_breakdowns`:BOOLEAN, `use_selection`:BOOLEAN, `flip`=NONE/FLIP/AUTO, `smooth_steps`:INT, `smooth_factor`:FLOAT, `type`=LINEAR/CUSTOM/SINE/QUAD/CUBIC/QUART/QUINT/EXPO/CIRC/BACK/BOUNCE/ELASTIC, `easing`=AUTO/EASE_IN/EASE_OUT/EASE_IN_OUT, `back`:FLOAT, `amplitude`:FLOAT, `period`:FLOAT |
| ❌ | `grease_pencil.join_fills` | Join selected strokes into one fill to create holes | — |
| ❌ | `grease_pencil.join_selection` | New stroke from selected points/strokes | `type`=JOINSTROKES/SPLITCOPY/SPLIT |
| ❌ | `grease_pencil.layer_active` | Set the active Grease Pencil layer | `layer`:INT |
| ❌ | `grease_pencil.layer_add` | Add a new Grease Pencil layer in the active object | `new_layer_name`:STRING |
| ❌ | `grease_pencil.layer_duplicate` | Make a copy of the active Grease Pencil layer | `empty_keyframes`:BOOLEAN |
| ❌ | `grease_pencil.layer_duplicate_object` | Make a copy of the active Grease Pencil layer to selected object | `only_active`:BOOLEAN, `mode`=ALL/ACTIVE |
| ❌ | `grease_pencil.layer_group_add` | Add a new Grease Pencil layer group in the active object | `new_layer_group_name`:STRING |
| ❌ | `grease_pencil.layer_group_color_tag` | Change layer group icon | `color_tag`=NONE/COLOR1/COLOR2/COLOR3/COLOR4/COLOR5/COLOR6/COLOR7/COLOR8 |
| ❌ | `grease_pencil.layer_group_remove` | Remove Grease Pencil layer group in the active object | `keep_children`:BOOLEAN |
| ❌ | `grease_pencil.layer_hide` | Hide selected/unselected Grease Pencil layers | `unselected`:BOOLEAN |
| ❌ | `grease_pencil.layer_isolate` | Make only active layer visible/editable | `affect_visibility`:BOOLEAN |
| ❌ | `grease_pencil.layer_lock_all` | Lock all Grease Pencil layers to prevent them from being accidentally modified | `lock`:BOOLEAN |
| ❌ | `grease_pencil.layer_mask_add` | Add new layer as masking | `name`:STRING |
| ❌ | `grease_pencil.layer_mask_remove` | Remove Layer Mask | — |
| ❌ | `grease_pencil.layer_mask_reorder` | Reorder the active Grease Pencil mask layer up/down in the list | `direction`=UP/DOWN |
| ❌ | `grease_pencil.layer_merge` | Combine layers based on the mode into one layer | `mode`=ACTIVE/GROUP/ALL |
| ❌ | `grease_pencil.layer_move` | Move the active Grease Pencil layer or Group | `direction`=UP/DOWN |
| ❌ | `grease_pencil.layer_remove` | Remove the active Grease Pencil layer | — |
| ❌ | `grease_pencil.layer_reveal` | Show all Grease Pencil layers | — |
| ❌ | `grease_pencil.material_copy_to_object` | Append Materials of the active Grease Pencil to other object | `only_active`:BOOLEAN |
| ❌ | `grease_pencil.material_hide` | Hide active/inactive Grease Pencil material(s) | `invert`:BOOLEAN |
| ❌ | `grease_pencil.material_isolate` | Toggle whether the active material is the only one that is editable and/or visible | `affect_visibility`:BOOLEAN |
| ❌ | `grease_pencil.material_lock_all` | Lock all Grease Pencil materials to prevent them from being accidentally modified | — |
| ❌ | `grease_pencil.material_lock_unselected` | Lock any material not used in any selected stroke | — |
| ❌ | `grease_pencil.material_lock_unused` | Lock and hide any material not used | — |
| ❌ | `grease_pencil.material_reveal` | Unhide all hidden Grease Pencil materials | — |
| ❌ | `grease_pencil.material_select` | Select/Deselect all Grease Pencil strokes using current material | `deselect`:BOOLEAN |
| ❌ | `grease_pencil.material_unlock_all` | Unlock all Grease Pencil materials so that they can be edited | — |
| ❌ | `grease_pencil.move_to_layer` | Move selected strokes to another layer | `target_layer_name`:STRING, `target_group_name`:STRING, `add_new_layer`:BOOLEAN |
| ❌ | `grease_pencil.outline` | Convert selected strokes to perimeter | `type`=VIEW/FRONT/SIDE/TOP/CURSOR/CAMERA, `radius`:FLOAT, `offset_factor`:FLOAT, `corner_subdivisions`:INT |
| ❌ | `grease_pencil.paintmode_toggle` | Enter/Exit paint mode for Grease Pencil strokes | `back`:BOOLEAN |
| ❌ | `grease_pencil.paste` | Paste Grease Pencil points or strokes from the internal clipboard to the active layer | `type`=ACTIVE/LAYER, `paste_back`:BOOLEAN, `keep_world_transform`:BOOLEAN |
| ✅ | `grease_pencil.pen` | Construct and edit splines | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `extrude_point`:BOOLEAN, `extrude_handle`=AUTO/VECTOR, `delete_point`:BOOLEAN, `insert_point`:BOOLEAN, `move_segment`:BOOLEAN, `select_point`:BOOLEAN, `move_point`:BOOLEAN, `cycle_handle_type`:BOOLEAN, `size`:FLOAT |
| ✅ | `grease_pencil.primitive_arc` | Create predefined Grease Pencil stroke arcs | `subdivision`:INT, `type`=BOX/LINE/POLYLINE/CIRCLE/ARC/CURVE |
| ✅ | `grease_pencil.primitive_box` | Create predefined Grease Pencil stroke boxes | `subdivision`:INT, `type`=BOX/LINE/POLYLINE/CIRCLE/ARC/CURVE |
| ✅ | `grease_pencil.primitive_circle` | Create predefined Grease Pencil stroke circles | `subdivision`:INT, `type`=BOX/LINE/POLYLINE/CIRCLE/ARC/CURVE |
| ✅ | `grease_pencil.primitive_curve` | Create predefined Grease Pencil stroke curve shapes | `subdivision`:INT, `type`=BOX/LINE/POLYLINE/CIRCLE/ARC/CURVE |
| ✅ | `grease_pencil.primitive_line` | Create predefined Grease Pencil stroke lines | `subdivision`:INT, `type`=BOX/LINE/POLYLINE/CIRCLE/ARC/CURVE |
| ✅ | `grease_pencil.primitive_polyline` | Create predefined Grease Pencil stroke polylines | `subdivision`:INT, `type`=BOX/LINE/POLYLINE/CIRCLE/ARC/CURVE |
| ❌ | `grease_pencil.relative_layer_mask_add` | Mask active layer with layer above or below | `mode`=ABOVE/BELOW |
| ❌ | `grease_pencil.remove_fill_guides` | Remove all the strokes that were created from the fill tool as guides | `mode`=ACTIVE_FRAME/ALL_FRAMES |
| ❌ | `grease_pencil.reorder` | Change the display order of the selected strokes | `direction`=TOP/UP/DOWN/BOTTOM |
| ❌ | `grease_pencil.reproject` | Reproject the selected strokes from the current viewpoint as if they had been newly drawn  | `type`=FRONT/SIDE/TOP/VIEW/SURFACE/CURSOR, `keep_original`:BOOLEAN, `offset`:FLOAT |
| ❌ | `grease_pencil.reset_uvs` | Reset UV transformation to default values | — |
| ❌ | `grease_pencil.sculpt_paint` | Sculpt strokes in the active Grease Pencil object | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN |
| ❌ | `grease_pencil.sculptmode_toggle` | Enter/Exit sculpt mode for Grease Pencil strokes | `back`:BOOLEAN |
| ❌ | `grease_pencil.select_all` | (De)select all visible strokes | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `grease_pencil.select_alternate` | Select alternated points in strokes with already selected points | `deselect_ends`:BOOLEAN |
| ❌ | `grease_pencil.select_by_stroke_type` | Select/Deselect all strokes or fills | `type`=STROKE/FILL, `deselect`:BOOLEAN |
| ❌ | `grease_pencil.select_ends` | Select end points of strokes | `amount_start`:INT, `amount_end`:INT |
| ❌ | `grease_pencil.select_fill` | Select all curves in a fill | — |
| ❌ | `grease_pencil.select_less` | Shrink the selection by one point | — |
| ❌ | `grease_pencil.select_linked` | Select all points in curves with any point selection | `deselect`:BOOLEAN |
| ❌ | `grease_pencil.select_more` | Grow the selection by one point | — |
| ❌ | `grease_pencil.select_random` | Selects random points from the current strokes selection | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT |
| ❌ | `grease_pencil.select_similar` | Select all strokes with similar characteristics | `mode`=LAYER/MATERIAL/VERTEX_COLOR/RADIUS/OPACITY, `threshold`:FLOAT |
| ❌ | `grease_pencil.separate` | Separate the selected geometry into a new Grease Pencil object | `mode`=SELECTED/MATERIAL/LAYER |
| ❌ | `grease_pencil.separate_fills` | Separate the selected strokes from current fill | `individual`:BOOLEAN |
| ❌ | `grease_pencil.set_active_material` | Set the selected stroke material as the active material | — |
| ❌ | `grease_pencil.set_corner_type` | Set the corner type of the selected points | `corner_type`=ROUND/FLAT/SHARP, `miter_angle`:FLOAT |
| ❌ | `grease_pencil.set_curve_resolution` | Set resolution of selected curves | `resolution`:INT |
| ❌ | `grease_pencil.set_curve_type` | Set type of selected curves | `type`=CATMULL_ROM/POLY/BEZIER/NURBS, `use_handles`:BOOLEAN |
| ❌ | `grease_pencil.set_handle_type` | Set the handle type for Bézier curves | `type`=AUTO/VECTOR/ALIGN/FREE_ALIGN/TOGGLE_FREE_ALIGN |
| ❌ | `grease_pencil.set_material` | Set active material | `slot`=DEFAULT |
| ❌ | `grease_pencil.set_selection_mode` | Change the selection mode for Grease Pencil strokes | `mode`=POINT/STROKE/SEGMENT |
| ❌ | `grease_pencil.set_start_point` | Select which point is the beginning of the curve | — |
| ❌ | `grease_pencil.set_stroke_type` | Set the stroke type (stroke, fill, or both) of the selected strokes | `type`=STROKE/FILL/BOTH |
| ❌ | `grease_pencil.set_uniform_opacity` | Set all stroke points to same opacity | `opacity_stroke`:FLOAT, `opacity_fill`:FLOAT |
| ❌ | `grease_pencil.set_uniform_thickness` | Set all stroke points to same thickness | `thickness`:FLOAT |
| ❌ | `grease_pencil.snap_cursor_to_selected` | Snap cursor to center of selected points | — |
| ❌ | `grease_pencil.snap_to_cursor` | Snap selected points/strokes to the cursor | `use_offset`:BOOLEAN |
| ❌ | `grease_pencil.snap_to_grid` | Snap selected points to the nearest grid points | — |
| ❌ | `grease_pencil.stroke_material_set` | Assign the active material slot to the selected strokes | `material`:STRING |
| ❌ | `grease_pencil.stroke_merge_by_distance` | Merge points by distance | `threshold`:FLOAT, `use_unselected`:BOOLEAN |
| ❌ | `grease_pencil.stroke_reset_vertex_color` | Reset vertex color for all or selected strokes | `mode`=STROKE/FILL/BOTH |
| ❌ | `grease_pencil.stroke_simplify` | Simplify selected strokes | `factor`:FLOAT, `length`:FLOAT, `distance`:FLOAT, `steps`:INT, `mode`=FIXED/ADAPTIVE/SAMPLE/MERGE |
| ❌ | `grease_pencil.stroke_smooth` | Smooth selected strokes | `iterations`:INT, `factor`:FLOAT, `smooth_ends`:BOOLEAN, `keep_shape`:BOOLEAN, `smooth_position`:BOOLEAN, `smooth_radius`:BOOLEAN, `smooth_opacity`:BOOLEAN |
| ❌ | `grease_pencil.stroke_split` | Split selected points to a new stroke | — |
| ❌ | `grease_pencil.stroke_subdivide` | Subdivide between continuous selected points of the stroke adding a point half way between | `number_cuts`:INT, `only_selected`:BOOLEAN |
| ❌ | `grease_pencil.stroke_subdivide_smooth` | Subdivide strokes and smooth them | `GREASE_PENCIL_OT_stroke_subdivide`:POINTER, `GREASE_PENCIL_OT_stroke_smooth`:POINTER |
| ❌ | `grease_pencil.stroke_switch_direction` | Change direction of the points of the selected strokes | — |
| ❌ | `grease_pencil.stroke_trim` | Delete stroke points in between intersecting strokes | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT |
| ❌ | `grease_pencil.texture_gradient` | Draw a line to set the fill material gradient for the selected strokes | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT |
| ❌ | `grease_pencil.trace_image` | Extract Grease Pencil strokes from image | `target`=NEW/SELECTED, `threshold`:FLOAT, `turnpolicy`=FOREGROUND/BACKGROUND/LEFT/RIGHT/MINORITY/MAJORITY/RANDOM, `mode`=SINGLE/SEQUENCE, `use_current_frame`:BOOLEAN, `frame_number`:INT |
| ❌ | `grease_pencil.vertex_brush_stroke` | Draw on vertex colors in the active Grease Pencil object | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN |
| ❌ | `grease_pencil.vertex_color_brightness_contrast` | Adjust vertex color brightness/contrast | `mode`=STROKE/FILL/BOTH, `brightness`:FLOAT, `contrast`:FLOAT |
| ❌ | `grease_pencil.vertex_color_hsv` | Adjust vertex color HSV values | `mode`=STROKE/FILL/BOTH, `h`:FLOAT, `s`:FLOAT, `v`:FLOAT |
| ❌ | `grease_pencil.vertex_color_invert` | Invert RGB values | `mode`=STROKE/FILL/BOTH |
| ❌ | `grease_pencil.vertex_color_levels` | Adjust levels of vertex colors | `mode`=STROKE/FILL/BOTH, `offset`:FLOAT, `gain`:FLOAT |
| ❌ | `grease_pencil.vertex_color_set` | Set active color to all selected vertices | `mode`=STROKE/FILL/BOTH, `factor`:FLOAT |
| ❌ | `grease_pencil.vertex_group_normalize` | Normalize weights of the active vertex group | — |
| ❌ | `grease_pencil.vertex_group_normalize_all` | Normalize the weights of all vertex groups, so that for each vertex, the sum of all weight | `lock_active`:BOOLEAN |
| ❌ | `grease_pencil.vertex_group_smooth` | Smooth the weights of the active vertex group | `factor`:FLOAT, `repeat`:INT |
| ❌ | `grease_pencil.vertexmode_toggle` | Enter/Exit vertex paint mode for Grease Pencil strokes | `back`:BOOLEAN |
| ❌ | `grease_pencil.weight_brush_stroke` | Draw weight on stroke points in the active Grease Pencil object | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN |
| ❌ | `grease_pencil.weight_invert` | Invert the weight of active vertex group | — |
| ❌ | `grease_pencil.weight_sample` | Set the weight of the Draw tool to the weight of the vertex under the mouse cursor | — |
| ❌ | `grease_pencil.weight_toggle_direction` | Toggle Add/Subtract for the weight paint draw tool | — |
| ❌ | `grease_pencil.weightmode_toggle` | Enter/Exit weight paint mode for Grease Pencil strokes | `back`:BOOLEAN |

### `image` — 49개 (✅ 8 / ⚠ 0 / ❌ 41)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `image.add_render_slot` | Add a new render slot | — |
| ❌ | `image.change_frame` | Interactively change the current frame number | `frame`:INT |
| ❌ | `image.clear_render_border` | Clear the boundaries of the render region and disable render region | — |
| ❌ | `image.clear_render_slot` | Clear the currently selected render slot | — |
| ❌ | `image.clipboard_copy` | Copy the image to the clipboard | — |
| ❌ | `image.clipboard_paste` | Paste new image from the clipboard | — |
| ❌ | `image.convert_to_mesh_plane` | Convert selected reference images to textured mesh plane | `interpolation`=Linear/Closest/Cubic/Smart, `extension`=CLIP/EXTEND/REPEAT, `use_auto_refresh`:BOOLEAN, `relative`:BOOLEAN, `shader`=PRINCIPLED/SHADELESS/EMISSION, `emit_strength`:FLOAT, `use_transparency`:BOOLEAN, `render_method`=DITHERED/BLENDED, `use_backface_culling`:BOOLEAN, `show_transparent_back`:BOOLEAN, `overwrite_material`:BOOLEAN, `name_from`=OBJECT/IMAGE, `delete_ref`:BOOLEAN |
| ❌ | `image.curves_point_set` | Set black point or white point for curves | `point`=BLACK_POINT/WHITE_POINT, `size`:INT |
| ❌ | `image.cycle_render_slot` | Cycle through all non-void render slots | `reverse`:BOOLEAN |
| ✅ | `image.external_edit` | Edit image in an external application | `filepath`:STRING |
| ❌ | `image.file_browse` | Open an image file browser, hold Shift to open the file, Alt to browse containing director | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `image.flip` | Flip the image | `use_flip_x`:BOOLEAN, `use_flip_y`:BOOLEAN |
| ✅ | `image.import_as_mesh_planes` | Create mesh plane(s) from image files with the appropriate aspect ratio | `interpolation`=Linear/Closest/Cubic/Smart, `extension`=CLIP/EXTEND/REPEAT, `use_auto_refresh`:BOOLEAN, `relative`:BOOLEAN, `shader`=PRINCIPLED/SHADELESS/EMISSION, `emit_strength`:FLOAT, `use_transparency`:BOOLEAN, `render_method`=DITHERED/BLENDED, `use_backface_culling`:BOOLEAN, `show_transparent_back`:BOOLEAN, `overwrite_material`:BOOLEAN, `filepath`:STRING, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `files`:COLLECTION, `directory`:STRING, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_folder`:BOOLEAN, `force_reload`:BOOLEAN, `image_sequence`:BOOLEAN, `offset`:BOOLEAN, `offset_axis`=+X/+Y/+Z/-X/-Y/-Z, `offset_amount`:FLOAT, `align_axis`=+X/+Y/+Z/-X/-Y/-Z/CAM/CAM_AX, `prev_align_axis`=+X/+Y/+Z/-X/-Y/-Z/CAM/CAM_AX/NONE, `align_track`:BOOLEAN, `size_mode`=ABSOLUTE/CAMERA/DPI/DPBU, `fill_mode`=FILL/FIT, `height`:FLOAT, `factor`:FLOAT |
| ❌ | `image.invert` | Invert image's channels | `invert_r`:BOOLEAN, `invert_g`:BOOLEAN, `invert_b`:BOOLEAN, `invert_a`:BOOLEAN |
| ✅ | `image.match_movie_length` | Set the image's frame range to match the video's duration | — |
| ✅ | `image.new` | Create a new image | `name`:STRING, `width`:INT, `height`:INT, `color`:FLOAT, `alpha`:BOOLEAN, `generated_type`=BLANK/UV_GRID/COLOR_GRID, `float`:BOOLEAN, `use_stereo_3d`:BOOLEAN, `tiled`:BOOLEAN |
| ✅ | `image.open` | Open image | `allow_path_tokens`:BOOLEAN, `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `use_sequence_detection`:BOOLEAN, `use_udim_detecting`:BOOLEAN |
| ❌ | `image.open_images` | (undocumented operator) | `directory`:STRING, `files`:COLLECTION, `relative_path`:BOOLEAN, `use_sequence_detection`:BOOLEAN, `use_udim_detection`:BOOLEAN |
| ❌ | `image.pack` | Pack an image as embedded data into the .blend file | — |
| ✅ | `image.project_apply` | Project edited image back onto the object | — |
| ✅ | `image.project_edit` | Edit a snapshot of the 3D Viewport in an external image editor | — |
| ❌ | `image.read_viewlayers` | Read all the current scene's view layers from cache, as needed | — |
| ✅ | `image.reload` | Reload current image from disk | — |
| ❌ | `image.remove_render_slot` | Remove the current render slot | — |
| ❌ | `image.render_border` | Set the boundaries of the render region and enable render region | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `image.replace` | Replace current image by another one from disk | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `image.resize` | Resize the image | `size`:INT, `all_udims`:BOOLEAN |
| ❌ | `image.rotate_orthogonal` | Rotate the image | `degrees`=90/180/270 |
| ❌ | `image.sample` | Use mouse to sample a color in current image | `size`:INT |
| ❌ | `image.sample_line` | Sample a line and show it in Scope panels | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT |
| ❌ | `image.save` | Save the image with current name and settings | — |
| ❌ | `image.save_all_modified` | Save all modified images | — |
| ❌ | `image.save_as` | Save the image with another name and/or settings | `save_as_render`:BOOLEAN, `copy`:BOOLEAN, `allow_path_tokens`:BOOLEAN, `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `image.save_sequence` | Save a sequence of images | — |
| ❌ | `image.tile_add` | Adds a tile to the image | `number`:INT, `count`:INT, `label`:STRING, `fill`:BOOLEAN, `color`:FLOAT, `generated_type`=BLANK/UV_GRID/COLOR_GRID, `width`:INT, `height`:INT, `float`:BOOLEAN, `alpha`:BOOLEAN |
| ❌ | `image.tile_fill` | Fill the current tile with a generated image | `color`:FLOAT, `generated_type`=BLANK/UV_GRID/COLOR_GRID, `width`:INT, `height`:INT, `float`:BOOLEAN, `alpha`:BOOLEAN |
| ❌ | `image.tile_remove` | Removes a tile from the image | — |
| ❌ | `image.unpack` | Save an image packed in the .blend file to disk | `method`=REMOVE/USE_LOCAL/WRITE_LOCAL/USE_ORIGINAL/WRITE_ORIGINAL, `id`:STRING |
| ❌ | `image.view_all` | View the entire image | `fit_view`:BOOLEAN |
| ❌ | `image.view_center_cursor` | Center the view so that the cursor is in the middle of the view | — |
| ❌ | `image.view_cursor_center` | Set 2D cursor to center view location | `fit_view`:BOOLEAN |
| ❌ | `image.view_ndof` | Use a 3D mouse device to pan/zoom the view | — |
| ❌ | `image.view_pan` | Pan the view | `offset`:FLOAT |
| ❌ | `image.view_selected` | View all selected UVs | — |
| ❌ | `image.view_zoom` | Zoom in/out the image | `factor`:FLOAT, `use_cursor_init`:BOOLEAN |
| ❌ | `image.view_zoom_border` | Zoom in the view to the nearest item contained in the border | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `zoom_out`:BOOLEAN |
| ❌ | `image.view_zoom_in` | Zoom in the image (centered around 2D cursor) | `location`:FLOAT |
| ❌ | `image.view_zoom_out` | Zoom out the image (centered around 2D cursor) | `location`:FLOAT |
| ❌ | `image.view_zoom_ratio` | Set zoom ratio of the view | `ratio`:FLOAT |

### `import_anim` — 1개 (✅ 1 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `import_anim.bvh` | Load a BVH motion capture file | `filepath`:STRING, `filter_glob`:STRING, `target`=ARMATURE/OBJECT, `global_scale`:FLOAT, `frame_start`:INT, `use_fps_scale`:BOOLEAN, `update_scene_fps`:BOOLEAN, `update_scene_duration`:BOOLEAN, `use_cyclic`:BOOLEAN, `rotate_mode`=QUATERNION/NATIVE/XYZ/XZY/YXZ/YZX/ZXY/ZYX, `axis_forward`=X/Y/Z/-X/-Y/-Z, `axis_up`=X/Y/Z/-X/-Y/-Z |

### `import_curve` — 1개 (✅ 1 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `import_curve.svg` | Load a SVG file | `filepath`:STRING, `filter_glob`:STRING, `directory`:STRING, `files`:COLLECTION |

### `import_scene` — 2개 (✅ 2 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `import_scene.fbx` | Load a FBX file | `filepath`:STRING, `directory`:STRING, `filter_glob`:STRING, `files`:COLLECTION, `ui_tab`=MAIN/ARMATURE, `use_manual_orientation`:BOOLEAN, `global_scale`:FLOAT, `bake_space_transform`:BOOLEAN, `use_custom_normals`:BOOLEAN, `colors_type`=NONE/SRGB/LINEAR, `use_image_search`:BOOLEAN, `use_alpha_decals`:BOOLEAN, `decal_offset`:FLOAT, `use_anim`:BOOLEAN, `anim_offset`:FLOAT, `use_subsurf`:BOOLEAN, `use_custom_props`:BOOLEAN, `use_custom_props_enum_as_string`:BOOLEAN, `ignore_leaf_bones`:BOOLEAN, `force_connect_children`:BOOLEAN, `automatic_bone_orientation`:BOOLEAN, `primary_bone_axis`=X/Y/Z/-X/-Y/-Z, `secondary_bone_axis`=X/Y/Z/-X/-Y/-Z, `use_prepost_rot`:BOOLEAN, `mtl_name_collision_mode`=MAKE_UNIQUE/REFERENCE_EXISTING, `axis_forward`=X/Y/Z/-X/-Y/-Z, `axis_up`=X/Y/Z/-X/-Y/-Z |
| ✅ | `import_scene.gltf` | Load a glTF 2.0 file | `filepath`:STRING, `export_import_convert_lighting_mode`=SPEC/COMPAT/RAW, `filter_glob`:STRING, `directory`:STRING, `files`:COLLECTION, `loglevel`:INT, `import_pack_images`:BOOLEAN, `merge_vertices`:BOOLEAN, `import_shading`=NORMALS/FLAT/SMOOTH, `bone_heuristic`=BLENDER/TEMPERANCE/FORTUNE, `disable_bone_shape`:BOOLEAN, `bone_shape_scale_factor`:FLOAT, `guess_original_bind_pose`:BOOLEAN, `import_webp_texture`:BOOLEAN, `import_unused_materials`:BOOLEAN, `import_select_created_objects`:BOOLEAN, `import_scene_extras`:BOOLEAN, `import_scene_as_collection`:BOOLEAN, `import_merge_material_slots`:BOOLEAN, `import_point_as_pointcloud`:BOOLEAN |

### `info` — 7개 (✅ 1 / ⚠ 0 / ❌ 6)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `info.report_copy` | Copy selected reports to clipboard | — |
| ❌ | `info.report_delete` | Delete selected reports | — |
| ❌ | `info.report_replay` | Replay selected reports | — |
| ✅ | `info.reports_display_update` | Update the display of reports in Blender UI (internal use) | — |
| ❌ | `info.select_all` | Change selection of all visible reports | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `info.select_box` | Toggle box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `info.select_pick` | Select reports by index | `report_index`:INT, `extend`:BOOLEAN |

### `lattice` — 8개 (✅ 0 / ⚠ 0 / ❌ 8)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `lattice.flip` | Mirror all control points without inverting the lattice deform | `axis`=U/V/W |
| ❌ | `lattice.make_regular` | Set UVW control points a uniform distance apart | — |
| ❌ | `lattice.select_all` | Change selection of all UVW control points | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `lattice.select_less` | Deselect vertices at the boundary of each selection region | — |
| ❌ | `lattice.select_mirror` | Select mirrored lattice points | `axis`=X/Y/Z, `extend`:BOOLEAN |
| ❌ | `lattice.select_more` | Select vertices directly linked to already selected ones | — |
| ❌ | `lattice.select_random` | Randomly select UVW control points | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT |
| ❌ | `lattice.select_ungrouped` | Select vertices without a group | `extend`:BOOLEAN |

### `marker` — 11개 (✅ 0 / ⚠ 0 / ❌ 11)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `marker.add` | Add a new time marker | — |
| ❌ | `marker.camera_bind` | Bind the selected camera to a marker on the current frame | — |
| ❌ | `marker.delete` | Delete selected time marker(s) | `confirm`:BOOLEAN |
| ❌ | `marker.duplicate` | Duplicate selected time marker(s) | `frames`:INT |
| ❌ | `marker.make_links_scene` | Copy selected markers to another scene | `scene`= |
| ❌ | `marker.move` | Move selected time marker(s) | `frames`:INT, `tweak`:BOOLEAN |
| ❌ | `marker.rename` | Rename first selected time marker | `name`:STRING |
| ❌ | `marker.select` | Select time marker(s) | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `camera`:BOOLEAN |
| ❌ | `marker.select_all` | Change selection of all time markers | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `marker.select_box` | Select all time markers using box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB, `tweak`:BOOLEAN |
| ❌ | `marker.select_leftright` | Select markers on and left/right of the current frame | `mode`=LEFT/RIGHT/CLICK_SIDE, `extend`:BOOLEAN |

### `mask` — 40개 (✅ 0 / ⚠ 0 / ❌ 40)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `mask.add_feather_vertex` | Add vertex to feather | `location`:FLOAT |
| ❌ | `mask.add_feather_vertex_slide` | Add new vertex to feather and slide it | `MASK_OT_add_feather_vertex`:POINTER, `MASK_OT_slide_point`:POINTER |
| ❌ | `mask.add_vertex` | Add vertex to active spline | `location`:FLOAT |
| ❌ | `mask.add_vertex_slide` | Add new vertex and slide it | `MASK_OT_add_vertex`:POINTER, `MASK_OT_slide_point`:POINTER |
| ❌ | `mask.copy_splines` | Copy the selected splines to the internal clipboard | — |
| ❌ | `mask.cyclic_toggle` | Toggle cyclic for selected splines | — |
| ❌ | `mask.delete` | Delete selected control points or splines | `confirm`:BOOLEAN |
| ❌ | `mask.duplicate` | Duplicate selected control points and segments between them | — |
| ❌ | `mask.duplicate_move` | Duplicate mask and move | `MASK_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mask.feather_weight_clear` | Reset the feather weight to zero | — |
| ❌ | `mask.handle_type_set` | Set type of handles for selected control points | `type`=AUTO/VECTOR/ALIGNED/ALIGNED_DOUBLESIDE/FREE |
| ❌ | `mask.hide_view_clear` | Reveal temporarily hidden mask layers | `select`:BOOLEAN |
| ❌ | `mask.hide_view_set` | Temporarily hide mask layers | `unselected`:BOOLEAN |
| ❌ | `mask.layer_move` | Move the active layer up/down in the list | `direction`=UP/DOWN |
| ❌ | `mask.layer_new` | Add new mask layer for masking | `name`:STRING |
| ❌ | `mask.layer_remove` | Remove mask layer | — |
| ❌ | `mask.move_to_layer` | Move the active spline to layer | `target_layer_name`:STRING, `add_new_layer`:BOOLEAN |
| ❌ | `mask.new` | Create new mask | `name`:STRING |
| ❌ | `mask.normals_make_consistent` | Recalculate the direction of selected handles | — |
| ❌ | `mask.parent_clear` | Clear the mask's parenting | — |
| ❌ | `mask.parent_set` | Set the mask's parenting | — |
| ❌ | `mask.paste_splines` | Paste splines from the internal clipboard | — |
| ❌ | `mask.primitive_circle_add` | Add new circle-shaped spline | `size`:FLOAT, `location`:FLOAT |
| ❌ | `mask.primitive_square_add` | Add new square-shaped spline | `size`:FLOAT, `location`:FLOAT |
| ❌ | `mask.select` | Select spline points | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `location`:FLOAT |
| ❌ | `mask.select_all` | Change selection of all curve points | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `mask.select_box` | Select curve points using box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `mask.select_circle` | Select curve points using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `mask.select_lasso` | Select curve points using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB |
| ❌ | `mask.select_less` | Deselect spline points at the boundary of each selection region | — |
| ❌ | `mask.select_linked` | Select all curve points linked to already selected ones | — |
| ❌ | `mask.select_linked_pick` | (De)select all points linked to the curve under the mouse cursor | `deselect`:BOOLEAN |
| ❌ | `mask.select_more` | Select more spline points connected to initial selection | — |
| ❌ | `mask.shape_key_clear` | Remove mask shape keyframe for active mask layer at the current frame | — |
| ❌ | `mask.shape_key_feather_reset` | Reset feather weights on all selected points animation values | — |
| ❌ | `mask.shape_key_insert` | Insert mask shape keyframe for active mask layer at the current frame | — |
| ❌ | `mask.shape_key_rekey` | Recalculate animation data on selected points for frames selected in the dopesheet | `location`:BOOLEAN, `feather`:BOOLEAN |
| ❌ | `mask.slide_point` | Slide control points | `slide_feather`:BOOLEAN, `is_new_point`:BOOLEAN |
| ❌ | `mask.slide_spline_curvature` | Slide a point on the spline to define its curvature | — |
| ❌ | `mask.switch_direction` | Switch direction of selected splines | — |

### `material` — 3개 (✅ 2 / ⚠ 1 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ⚠ | `material.copy` | Copy the material settings and nodes | — |
| ✅ | `material.new` | Add a new material | — |
| ✅ | `material.paste` | Paste the material settings and nodes | — |

### `mball` — 8개 (✅ 0 / ⚠ 0 / ❌ 8)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `mball.delete_metaelems` | Delete selected metaball element(s) | `confirm`:BOOLEAN |
| ❌ | `mball.duplicate_metaelems` | Duplicate selected metaball element(s) | — |
| ❌ | `mball.duplicate_move` | Make copies of the selected metaball elements and move them | `MBALL_OT_duplicate_metaelems`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mball.hide_metaelems` | Hide (un)selected metaball element(s) | `unselected`:BOOLEAN |
| ❌ | `mball.reveal_metaelems` | Reveal all hidden metaball elements | `select`:BOOLEAN |
| ❌ | `mball.select_all` | Change selection of all metaball elements | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `mball.select_random_metaelems` | Randomly select metaball elements | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT |
| ❌ | `mball.select_similar` | Select similar metaballs by property types | `type`=TYPE/RADIUS/STIFFNESS/ROTATION, `threshold`:FLOAT |

### `mesh` — 167개 (✅ 11 / ⚠ 6 / ❌ 150)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `mesh.attribute_set` | Set values of the active attribute for selected elements | `value_float`:FLOAT, `value_float_vector_2d`:FLOAT, `value_float_vector_3d`:FLOAT, `value_float_vector_4d`:FLOAT, `value_int`:INT, `value_int_vector_2d`:INT, `value_color`:FLOAT, `value_bool`:BOOLEAN |
| ❌ | `mesh.average_normals` | Average custom normals of selected vertices | `average_type`=CUSTOM_NORMAL/FACE_AREA/CORNER_ANGLE, `weight`:INT, `threshold`:FLOAT |
| ❌ | `mesh.beautify_fill` | Rearrange some faces to try to get less degenerated geometry | `angle_limit`:FLOAT |
| ❌ | `mesh.bevel` | Cut into selected items at an angle to create bevel or chamfer | `offset_type`=OFFSET/WIDTH/DEPTH/PERCENT/ABSOLUTE, `offset`:FLOAT, `profile_type`=SUPERELLIPSE/CUSTOM, `offset_pct`:FLOAT, `segments`:INT, `profile`:FLOAT, `affect`=VERTICES/EDGES, `clamp_overlap`:BOOLEAN, `loop_slide`:BOOLEAN, `mark_seam`:BOOLEAN, `mark_sharp`:BOOLEAN, `material`:INT, `harden_normals`:BOOLEAN, `face_strength_mode`=NONE/NEW/AFFECTED/ALL, `miter_outer`=SHARP/PATCH/ARC, `miter_inner`=SHARP/ARC, `spread`:FLOAT, `vmesh_method`=ADJ/CUTOFF, `release_confirm`:BOOLEAN |
| ❌ | `mesh.bisect` | Cut geometry along a plane (click-drag to define plane) | `plane_co`:FLOAT, `plane_no`:FLOAT, `use_fill`:BOOLEAN, `clear_inner`:BOOLEAN, `clear_outer`:BOOLEAN, `threshold`:FLOAT, `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT |
| ❌ | `mesh.blend_from_shape` | Blend in shape from a shape key | `shape`=, `blend`:FLOAT, `add`:BOOLEAN |
| ❌ | `mesh.bridge_edge_loops` | Create a bridge of faces between two or more selected edge loops | `type`=SINGLE/CLOSED/PAIRS, `use_merge`:BOOLEAN, `merge_factor`:FLOAT, `twist_offset`:INT, `number_cuts`:INT, `interpolation`=LINEAR/PATH/SURFACE, `smoothness`:FLOAT, `profile_shape_factor`:FLOAT, `profile_shape`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR |
| ❌ | `mesh.circularize` | Shape selected geometry into a circle | `factor`:FLOAT, `fit_method`=LEAST_SQUARE/CONTRACT, `angle`:FLOAT, `use_custom_radius`:BOOLEAN, `custom_radius`:FLOAT, `regular`:BOOLEAN, `flatten`:FLOAT, `lock`:BOOLEAN |
| ❌ | `mesh.colors_reverse` | Flip direction of face corner color attribute inside faces | — |
| ❌ | `mesh.colors_rotate` | Rotate face corner color attribute inside faces | `use_ccw`:BOOLEAN |
| ❌ | `mesh.convex_hull` | Enclose selected vertices in a convex polyhedron | `delete_unused`:BOOLEAN, `use_existing_faces`:BOOLEAN, `make_holes`:BOOLEAN, `join_triangles`:BOOLEAN, `face_threshold`:FLOAT, `shape_threshold`:FLOAT, `topology_influence`:FLOAT, `uvs`:BOOLEAN, `vcols`:BOOLEAN, `seam`:BOOLEAN, `sharp`:BOOLEAN, `materials`:BOOLEAN, `deselect_joined`:BOOLEAN |
| ⚠ | `mesh.customdata_custom_splitnormals_add` | Add a custom normals layer, if none exists yet | — |
| ⚠ | `mesh.customdata_custom_splitnormals_clear` | Remove the custom normals layer, if it exists | — |
| ❌ | `mesh.customdata_face_sets_clear` | Clear sculpt face set data from the mesh | — |
| ❌ | `mesh.customdata_mask_clear` | Clear vertex sculpt masking data from the mesh | — |
| ⚠ | `mesh.customdata_skin_add` | Add a vertex skin layer | — |
| ❌ | `mesh.customdata_skin_clear` | Clear vertex skin layer | — |
| ❌ | `mesh.decimate` | Simplify geometry by collapsing edges | `ratio`:FLOAT, `use_vertex_group`:BOOLEAN, `vertex_group_factor`:FLOAT, `invert_vertex_group`:BOOLEAN, `use_symmetry`:BOOLEAN, `symmetry_axis`=X/Y/Z |
| ❌ | `mesh.delete` | Delete selected vertices, edges or faces | `type`=VERT/EDGE/FACE/EDGE_FACE/ONLY_FACE |
| ❌ | `mesh.delete_edgeloop` | Delete an edge loop by merging the faces on each side | `use_face_split`:BOOLEAN |
| ❌ | `mesh.delete_loose` | Delete loose vertices, edges or faces | `use_verts`:BOOLEAN, `use_edges`:BOOLEAN, `use_faces`:BOOLEAN |
| ❌ | `mesh.dissolve_degenerate` | Dissolve zero area faces and zero length edges | `threshold`:FLOAT |
| ❌ | `mesh.dissolve_edges` | Dissolve edges, merging faces | `use_verts`:BOOLEAN, `angle_threshold`:FLOAT, `use_face_split`:BOOLEAN, `use_preserve_quads`:BOOLEAN |
| ❌ | `mesh.dissolve_faces` | Dissolve faces | `use_verts`:BOOLEAN |
| ❌ | `mesh.dissolve_limited` | Dissolve selected edges and vertices, limited by the angle of surrounding geometry | `angle_limit`:FLOAT, `use_dissolve_boundaries`:BOOLEAN, `delimit`=NORMAL/MATERIAL/SEAM/SHARP/UV |
| ❌ | `mesh.dissolve_mode` | Dissolve geometry based on the selection mode | `use_verts`:BOOLEAN, `angle_threshold`:FLOAT, `use_preserve_quads`:BOOLEAN, `use_face_split`:BOOLEAN, `use_boundary_tear`:BOOLEAN |
| ❌ | `mesh.dissolve_verts` | Dissolve vertices, merge edges and faces | `use_face_split`:BOOLEAN, `use_boundary_tear`:BOOLEAN |
| ❌ | `mesh.dupli_extrude_cursor` | Duplicate and extrude selected vertices, edges or faces towards the mouse cursor | `rotate_source`:BOOLEAN |
| ❌ | `mesh.duplicate` | Duplicate selected vertices, edges or faces | `mode`:INT |
| ❌ | `mesh.duplicate_move` | Duplicate mesh and move | `MESH_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.edge_collapse` | Collapse isolated edge and face regions, merging data such as UVs and color attributes. Th | — |
| ❌ | `mesh.edge_face_add` | Add an edge or face to selected | — |
| ❌ | `mesh.edge_rotate` | Rotate selected edge or adjoining faces | `use_ccw`:BOOLEAN |
| ❌ | `mesh.edge_split` | Split selected edges so that each neighbor face gets its own copy | `type`=EDGE/VERT |
| ❌ | `mesh.edgering_select` | Select an edge ring | `delimit_edge_ring`=SEAM/SHARP/MATERIAL/NGONS, `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `object_index`:INT, `edge_index`:INT, `vert_index`:INT, `face_index`:INT |
| ❌ | `mesh.edges_select_sharp` | Select all sharp enough edges | `sharpness`:FLOAT |
| ❌ | `mesh.extrude_context` | Extrude selection | `use_normal_flip`:BOOLEAN, `use_dissolve_ortho_edges`:BOOLEAN, `mirror`:BOOLEAN |
| ❌ | `mesh.extrude_context_move` | Extrude region together along the average normal | `MESH_OT_extrude_context`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.extrude_edges_indiv` | Extrude individual edges only | `use_normal_flip`:BOOLEAN, `mirror`:BOOLEAN |
| ❌ | `mesh.extrude_edges_move` | Extrude edges and move result | `MESH_OT_extrude_edges_indiv`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.extrude_faces_indiv` | Extrude individual faces only | `mirror`:BOOLEAN |
| ❌ | `mesh.extrude_faces_move` | Extrude each individual face separately along local normals | `MESH_OT_extrude_faces_indiv`:POINTER, `TRANSFORM_OT_shrink_fatten`:POINTER |
| ❌ | `mesh.extrude_manifold` | Extrude, dissolves edges whose faces form a flat surface and intersect new edges | `MESH_OT_extrude_region`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.extrude_region` | Extrude region of faces | `use_normal_flip`:BOOLEAN, `use_dissolve_ortho_edges`:BOOLEAN, `mirror`:BOOLEAN |
| ❌ | `mesh.extrude_region_move` | Extrude region and move result | `MESH_OT_extrude_region`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.extrude_region_shrink_fatten` | Extrude region together along local normals | `MESH_OT_extrude_region`:POINTER, `TRANSFORM_OT_shrink_fatten`:POINTER |
| ❌ | `mesh.extrude_repeat` | Extrude selected vertices, edges or faces repeatedly | `steps`:INT, `offset`:FLOAT, `scale_offset`:FLOAT |
| ❌ | `mesh.extrude_vertices_move` | Extrude vertices and move result | `MESH_OT_extrude_verts_indiv`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.extrude_verts_indiv` | Extrude individual vertices only | `mirror`:BOOLEAN |
| ❌ | `mesh.face_make_planar` | Flatten selected faces | `factor`:FLOAT, `repeat`:INT |
| ❌ | `mesh.face_split_by_edges` | Weld loose edges into faces (splitting them into new faces) | — |
| ❌ | `mesh.faces_select_linked_flat` | Select linked faces by angle | `sharpness`:FLOAT |
| ❌ | `mesh.faces_shade_flat` | Display faces flat | — |
| ❌ | `mesh.faces_shade_smooth` | Display faces smooth (using vertex normals) | — |
| ❌ | `mesh.fill` | Fill a selected edge loop with faces | `use_beauty`:BOOLEAN |
| ❌ | `mesh.fill_grid` | Fill grid from two loops | `span`:INT, `offset`:INT, `use_interp_simple`:BOOLEAN |
| ❌ | `mesh.fill_holes` | Fill in holes (boundary edge loops) | `sides`:INT |
| ❌ | `mesh.flatten` | Flatten vertices on a best-fitting plane | `factor`:FLOAT, `method`=BEST_FIT/NORMAL/VIEW, `lock`:BOOLEAN |
| ❌ | `mesh.flip_normals` | Flip the direction of selected faces' normals (and of their vertices) | `only_clnors`:BOOLEAN |
| ❌ | `mesh.flip_quad_tessellation` | Flips the tessellation of selected quads | — |
| ❌ | `mesh.hide` | Hide (un)selected vertices, edges or faces | `unselected`:BOOLEAN |
| ❌ | `mesh.inset` | Inset new faces into selected faces | `use_boundary`:BOOLEAN, `use_even_offset`:BOOLEAN, `use_relative_offset`:BOOLEAN, `use_edge_rail`:BOOLEAN, `thickness`:FLOAT, `depth`:FLOAT, `use_outset`:BOOLEAN, `use_select_inset`:BOOLEAN, `use_individual`:BOOLEAN, `use_interpolate`:BOOLEAN, `release_confirm`:BOOLEAN |
| ❌ | `mesh.intersect` | Cut an intersection into faces | `mode`=SELECT/SELECT_UNSELECT, `separate_mode`=ALL/CUT/NONE, `threshold`:FLOAT, `solver`=FLOAT/EXACT |
| ❌ | `mesh.intersect_boolean` | Cut solid geometry from selected to unselected | `operation`=INTERSECT/UNION/DIFFERENCE, `use_swap`:BOOLEAN, `use_self`:BOOLEAN, `threshold`:FLOAT, `solver`=FLOAT/EXACT |
| ❌ | `mesh.knife_project` | Use other objects outlines and boundaries to project knife cuts | `cut_through`:BOOLEAN |
| ❌ | `mesh.knife_tool` | Cut new topology | `use_occlude_geometry`:BOOLEAN, `only_selected`:BOOLEAN, `xray`:BOOLEAN, `visible_measurements`=NONE/BOTH/DISTANCE/ANGLE, `angle_snapping`=NONE/SCREEN/RELATIVE, `angle_snapping_increment`:FLOAT, `wait_for_input`:BOOLEAN |
| ❌ | `mesh.loop_select` | Select a loop of connected edges | `delimit_edge_loop`=SEAM/SHARP/NGONS/INNER_CORNERS/OUTER_CORNERS, `delimit_face_loop`=SEAM/SHARP/MATERIAL, `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `object_index`:INT, `edge_index`:INT, `vert_index`:INT, `face_index`:INT |
| ❌ | `mesh.loop_to_region` | Select region of faces inside of a selected loop of edges | `select_bigger`:BOOLEAN |
| ❌ | `mesh.loopcut` | Add a new loop between existing loops | `number_cuts`:INT, `smoothness`:FLOAT, `falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR, `object_index`:INT, `edge_index`:INT, `mesh_select_mode_init`:BOOLEAN |
| ❌ | `mesh.loopcut_slide` | Cut mesh loop and slide it | `MESH_OT_loopcut`:POINTER, `TRANSFORM_OT_edge_slide`:POINTER |
| ❌ | `mesh.mark_freestyle_edge` | (Un)mark selected edges as Freestyle feature edges | `clear`:BOOLEAN |
| ❌ | `mesh.mark_freestyle_face` | (Un)mark selected faces for exclusion from Freestyle feature edge detection | `clear`:BOOLEAN |
| ❌ | `mesh.mark_seam` | (Un)mark selected edges as a seam | `clear`:BOOLEAN |
| ❌ | `mesh.mark_sharp` | (Un)mark selected edges as sharp | `clear`:BOOLEAN, `use_verts`:BOOLEAN |
| ❌ | `mesh.merge` | Merge selected vertices | `type`=CENTER/CURSOR/COLLAPSE/FIRST/LAST, `uvs`:BOOLEAN |
| ❌ | `mesh.merge_normals` | Merge custom normals of selected vertices | — |
| ❌ | `mesh.mod_weighted_strength` | Set/Get strength of face (used in Weighted Normal modifier) | `set`:BOOLEAN, `face_strength`=WEAK/MEDIUM/STRONG |
| ❌ | `mesh.normals_make_consistent` | Make face and vertex normals point either outside or inside the mesh | `inside`:BOOLEAN |
| ❌ | `mesh.normals_tools` | Custom normals tools using Normal Vector of UI | `mode`=COPY/PASTE/ADD/MULTIPLY/RESET, `absolute`:BOOLEAN |
| ❌ | `mesh.offset_edge_loops` | Create offset edge loop from the current selection | `use_cap_endpoint`:BOOLEAN |
| ❌ | `mesh.offset_edge_loops_slide` | Offset edge loop slide | `MESH_OT_offset_edge_loops`:POINTER, `TRANSFORM_OT_edge_slide`:POINTER |
| ❌ | `mesh.point_normals` | Point selected custom normals to specified Target | `mode`=COORDINATES/MOUSE, `invert`:BOOLEAN, `align`:BOOLEAN, `target_location`:FLOAT, `spherize`:BOOLEAN, `spherize_strength`:FLOAT |
| ❌ | `mesh.poke` | Split a face into a fan | `offset`:FLOAT, `use_relative_offset`:BOOLEAN, `center_mode`=MEDIAN_WEIGHTED/MEDIAN/BOUNDS |
| ❌ | `mesh.polybuild_delete_at_cursor` | (undocumented operator) | `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `mesh.polybuild_dissolve_at_cursor` | (undocumented operator) | — |
| ❌ | `mesh.polybuild_extrude_at_cursor_move` | (undocumented operator) | `MESH_OT_polybuild_transform_at_cursor`:POINTER, `MESH_OT_extrude_edges_indiv`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.polybuild_face_at_cursor` | (undocumented operator) | `create_quads`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `mesh.polybuild_face_at_cursor_move` | (undocumented operator) | `MESH_OT_polybuild_face_at_cursor`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.polybuild_split_at_cursor` | (undocumented operator) | `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `mesh.polybuild_split_at_cursor_move` | (undocumented operator) | `MESH_OT_polybuild_split_at_cursor`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.polybuild_transform_at_cursor` | (undocumented operator) | `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `mesh.polybuild_transform_at_cursor_move` | (undocumented operator) | `MESH_OT_polybuild_transform_at_cursor`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ✅ | `mesh.primitive_circle_add` | Construct a circle mesh | `vertices`:INT, `radius`:FLOAT, `fill_type`=NOTHING/NGON/TRIFAN, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_cone_add` | Construct a conic mesh | `vertices`:INT, `radius1`:FLOAT, `radius2`:FLOAT, `depth`:FLOAT, `end_fill_type`=NOTHING/NGON/TRIFAN, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_cube_add` | Construct a cube mesh that consists of six square faces | `size`:FLOAT, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `mesh.primitive_cube_add_gizmo` | Construct a cube mesh | `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT, `matrix`:FLOAT |
| ✅ | `mesh.primitive_cylinder_add` | Construct a cylinder mesh | `vertices`:INT, `radius`:FLOAT, `depth`:FLOAT, `end_fill_type`=NOTHING/NGON/TRIFAN, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_grid_add` | Construct a subdivided plane mesh | `x_subdivisions`:INT, `y_subdivisions`:INT, `size`:FLOAT, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_ico_sphere_add` | Construct a spherical mesh that consists of equally sized triangles | `subdivisions`:INT, `radius`:FLOAT, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_monkey_add` | Construct a Suzanne mesh | `size`:FLOAT, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_plane_add` | Construct a filled planar mesh with 4 vertices | `size`:FLOAT, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `mesh.primitive_torus_add` | Construct a torus mesh | `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `major_segments`:INT, `minor_segments`:INT, `mode`=MAJOR_MINOR/EXT_INT, `major_radius`:FLOAT, `minor_radius`:FLOAT, `abso_major_rad`:FLOAT, `abso_minor_rad`:FLOAT, `generate_uvs`:BOOLEAN |
| ✅ | `mesh.primitive_uv_sphere_add` | Construct a spherical mesh with quad faces, except for triangle faces at the top and botto | `segments`:INT, `ring_count`:INT, `radius`:FLOAT, `calc_uvs`:BOOLEAN, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `mesh.quads_convert_to_tris` | Triangulate selected faces | `quad_method`=BEAUTY/FIXED/FIXED_ALTERNATE/SHORTEST_DIAGONAL/LONGEST_DIAGONAL, `ngon_method`=BEAUTY/CLIP |
| ❌ | `mesh.region_to_loop` | Select boundary edges around the selected faces | — |
| ❌ | `mesh.remove_doubles` | Merge vertices based on their proximity | `threshold`:FLOAT, `use_centroid`:BOOLEAN, `use_unselected`:BOOLEAN, `use_sharp_edge_from_normals`:BOOLEAN |
| ⚠ | `mesh.reorder_vertices_spatial` | Reorder mesh faces and vertices based on their spatial position for better BVH building an | — |
| ❌ | `mesh.reveal` | Reveal all hidden vertices, edges and faces | `select`:BOOLEAN |
| ❌ | `mesh.rip` | Disconnect vertices or edges from connected geometry | `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN, `use_fill`:BOOLEAN |
| ❌ | `mesh.rip_edge` | Extend vertices along the edge closest to the cursor | `location`:FLOAT, `direction`:FLOAT |
| ❌ | `mesh.rip_edge_move` | Extend vertices and move the result | `MESH_OT_rip_edge`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.rip_move` | Rip polygons and move the result | `MESH_OT_rip`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `mesh.screw` | Extrude selected vertices in screw-shaped rotation around the cursor in indicated viewport | `steps`:INT, `turns`:INT, `center`:FLOAT, `axis`:FLOAT |
| ❌ | `mesh.select_all` | (De)select all vertices, edges or faces | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `mesh.select_axis` | Select all data in the mesh on a single axis | `orientation`=GLOBAL/LOCAL/NORMAL/GIMBAL/VIEW/CURSOR/PARENT, `sign`=POS/NEG/ALIGN, `axis`=X/Y/Z, `threshold`:FLOAT |
| ❌ | `mesh.select_boundary_loop_multi` | Select entire boundary loop of each selected boundary edge | `extend`:BOOLEAN, `delimit_edge_loop`=SEAM/SHARP/NGONS/INNER_CORNERS/OUTER_CORNERS |
| ❌ | `mesh.select_by_attribute` | Select elements based on the active boolean attribute | — |
| ❌ | `mesh.select_by_pole_count` | Select vertices at poles by the number of connected edges. In edge and face mode the geome | `pole_count`:INT, `type`=LESS/EQUAL/GREATER/NOTEQUAL, `extend`:BOOLEAN, `exclude_nonmanifold`:BOOLEAN |
| ❌ | `mesh.select_edge_loop_multi` | Select loops of connected edges from each selected edge | `delimit_edge_loop`=SEAM/SHARP/NGONS/INNER_CORNERS/OUTER_CORNERS |
| ❌ | `mesh.select_edge_ring_multi` | Select rings of connected edges from each selected edge | `delimit_edge_ring`=SEAM/SHARP/MATERIAL/NGONS |
| ❌ | `mesh.select_face_by_sides` | Select vertices or faces by the number of face sides | `number`:INT, `type`=LESS/EQUAL/GREATER/NOTEQUAL, `extend`:BOOLEAN |
| ❌ | `mesh.select_interior_faces` | Select faces where all edges have more than 2 face users | — |
| ❌ | `mesh.select_less` | Deselect vertices, edges or faces at the boundary of each selection region | `use_face_step`:BOOLEAN |
| ❌ | `mesh.select_linked` | Select all vertices connected to the current selection | `delimit`=NORMAL/MATERIAL/SEAM/SHARP/UV |
| ❌ | `mesh.select_linked_pick` | (De)select all vertices linked to the edge under the mouse cursor | `deselect`:BOOLEAN, `delimit`=NORMAL/MATERIAL/SEAM/SHARP/UV, `object_index`:INT, `index`:INT |
| ❌ | `mesh.select_loose` | Select loose geometry based on the selection mode | `extend`:BOOLEAN |
| ❌ | `mesh.select_mirror` | Select mesh items at mirrored locations | `axis`=X/Y/Z, `extend`:BOOLEAN |
| ❌ | `mesh.select_mode` | Change selection mode | `use_extend`:BOOLEAN, `use_expand`:BOOLEAN, `type`=VERT/EDGE/FACE, `action`=DISABLE/ENABLE/TOGGLE |
| ❌ | `mesh.select_more` | Select more vertices, edges or faces connected to initial selection | `use_face_step`:BOOLEAN |
| ❌ | `mesh.select_next_item` | Select the next element (using selection order) | — |
| ❌ | `mesh.select_non_manifold` | Select all non-manifold vertices or edges | `extend`:BOOLEAN, `use_wire`:BOOLEAN, `use_boundary`:BOOLEAN, `use_multi_face`:BOOLEAN, `use_non_contiguous`:BOOLEAN, `use_verts`:BOOLEAN |
| ❌ | `mesh.select_nth` | Deselect every Nth element starting from the active vertex, edge or face | `skip`:INT, `nth`:INT, `offset`:INT |
| ❌ | `mesh.select_prev_item` | Select the previous element (using selection order) | — |
| ❌ | `mesh.select_random` | Randomly select vertices | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT |
| ❌ | `mesh.select_similar` | Select similar vertices, edges or faces by property types | `type`=VERT_NORMAL/VERT_FACES/VERT_GROUPS/VERT_EDGES/VERT_CREASE/EDGE_LENGTH/EDGE_DIR/EDGE_FACES/EDGE_FACE_ANGLE/EDGE_CREASE/EDGE_BEVEL/EDGE_SEAM/EDGE_SHARP/EDGE_FREESTYLE/FACE_MATERIAL/FACE_AREA/FACE_SIDES/FACE_PERIMETER/FACE_NORMAL/FACE_COPLANAR/FACE_SMOOTH/FACE_FREESTYLE, `compare`=EQUAL/GREATER/LESS, `threshold`:FLOAT |
| ❌ | `mesh.select_similar_region` | Select similar face regions to the current selection | — |
| ❌ | `mesh.select_ungrouped` | Select vertices without a group | `extend`:BOOLEAN |
| ✅ | `mesh.separate` | Separate selected geometry into a new mesh | `type`=SELECTED/MATERIAL/LOOSE |
| ❌ | `mesh.set_normals_from_faces` | Set the custom normals from the selected faces ones | `keep_sharp`:BOOLEAN |
| ❌ | `mesh.set_sharpness_by_angle` | Set edge sharpness based on the angle between neighboring faces | `angle`:FLOAT, `extend`:BOOLEAN |
| ❌ | `mesh.shape_propagate_to_all` | Apply selected vertex locations to all other shape keys | — |
| ❌ | `mesh.shortest_path_pick` | Select shortest path between two selections | `edge_mode`=SELECT/SEAM/SHARP/CREASE/BEVEL/FREESTYLE, `use_face_step`:BOOLEAN, `use_topology_distance`:BOOLEAN, `use_fill`:BOOLEAN, `skip`:INT, `nth`:INT, `offset`:INT, `index`:INT |
| ❌ | `mesh.shortest_path_select` | Select shortest path between two vertices/edges/faces | `edge_mode`=SELECT/SEAM/SHARP/CREASE/BEVEL/FREESTYLE, `use_face_step`:BOOLEAN, `use_topology_distance`:BOOLEAN, `use_fill`:BOOLEAN, `skip`:INT, `nth`:INT, `offset`:INT |
| ❌ | `mesh.smooth_normals` | Smooth custom normals based on adjacent vertex normals | `factor`:FLOAT |
| ❌ | `mesh.solidify` | Create a solid skin by extruding, compensating for sharp angles | `thickness`:FLOAT |
| ❌ | `mesh.sort_elements` | The order of selected vertices/edges/faces is modified, based on a given method | `type`=VIEW_ZAXIS/VIEW_XAXIS/CURSOR_DISTANCE/MATERIAL/SELECTED/RANDOMIZE/REVERSE, `elements`=VERT/EDGE/FACE, `reverse`:BOOLEAN, `seed`:INT |
| ❌ | `mesh.space_edge_loops_evenly` | Space the vertices in a regular distribution on the loop | `factor`:FLOAT, `interpolation`=CUBIC/LINEAR, `lock`:BOOLEAN |
| ❌ | `mesh.spin` | Extrude selected vertices in a circle around the cursor in indicated viewport | `steps`:INT, `dupli`:BOOLEAN, `angle`:FLOAT, `use_auto_merge`:BOOLEAN, `use_normal_flip`:BOOLEAN, `center`:FLOAT, `axis`:FLOAT |
| ❌ | `mesh.split` | Split off selected geometry from connected unselected geometry | — |
| ❌ | `mesh.split_normals` | Split custom normals of selected vertices | — |
| ❌ | `mesh.subdivide` | Subdivide selected edges | `number_cuts`:INT, `smoothness`:FLOAT, `ngon`:BOOLEAN, `quadcorner`=INNERVERT/PATH/STRAIGHT_CUT/FAN, `fractal`:FLOAT, `fractal_along_normal`:FLOAT, `seed`:INT |
| ❌ | `mesh.subdivide_edgering` | Subdivide perpendicular edges to the selected edge-ring | `number_cuts`:INT, `interpolation`=LINEAR/PATH/SURFACE, `smoothness`:FLOAT, `profile_shape_factor`:FLOAT, `profile_shape`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR |
| ❌ | `mesh.symmetrize` | Enforce symmetry (both form and topological) across an axis | `direction`=NEGATIVE_X/POSITIVE_X/NEGATIVE_Y/POSITIVE_Y/NEGATIVE_Z/POSITIVE_Z, `threshold`:FLOAT |
| ❌ | `mesh.symmetry_snap` | Snap vertex pairs to their mirrored locations | `direction`=NEGATIVE_X/POSITIVE_X/NEGATIVE_Y/POSITIVE_Y/NEGATIVE_Z/POSITIVE_Z, `threshold`:FLOAT, `factor`:FLOAT, `use_center`:BOOLEAN, `use_topology`:BOOLEAN |
| ❌ | `mesh.tris_convert_to_quads` | Merge triangles into four sided polygons where possible | `face_threshold`:FLOAT, `shape_threshold`:FLOAT, `topology_influence`:FLOAT, `uvs`:BOOLEAN, `vcols`:BOOLEAN, `seam`:BOOLEAN, `sharp`:BOOLEAN, `materials`:BOOLEAN, `deselect_joined`:BOOLEAN |
| ❌ | `mesh.unsubdivide` | Un-subdivide selected edges and faces | `iterations`:INT |
| ⚠ | `mesh.uv_texture_add` | Add UV map | — |
| ⚠ | `mesh.uv_texture_remove` | Remove UV map | — |
| ❌ | `mesh.uvs_reverse` | Flip direction of UV coordinates inside faces | — |
| ❌ | `mesh.uvs_rotate` | Rotate UV coordinates inside faces | `use_ccw`:BOOLEAN |
| ❌ | `mesh.vert_connect` | Connect selected vertices of faces, splitting the face | — |
| ❌ | `mesh.vert_connect_concave` | Split concave faces by connecting vertices to make them convex | — |
| ❌ | `mesh.vert_connect_nonplanar` | Split non-planar faces that exceed the angle threshold | `angle_limit`:FLOAT |
| ❌ | `mesh.vert_connect_path` | Connect vertices by their selection order, creating edges, splitting faces | — |
| ❌ | `mesh.vertices_smooth` | Flatten angles of selected vertices | `factor`:FLOAT, `repeat`:INT, `xaxis`:BOOLEAN, `yaxis`:BOOLEAN, `zaxis`:BOOLEAN, `wait_for_input`:BOOLEAN |
| ❌ | `mesh.vertices_smooth_laplacian` | Laplacian smooth of selected vertices | `repeat`:INT, `lambda_factor`:FLOAT, `lambda_border`:FLOAT, `use_x`:BOOLEAN, `use_y`:BOOLEAN, `use_z`:BOOLEAN, `preserve_volume`:BOOLEAN |
| ❌ | `mesh.wireframe` | Create a solid wireframe from faces | `use_boundary`:BOOLEAN, `use_even_offset`:BOOLEAN, `use_relative_offset`:BOOLEAN, `use_replace`:BOOLEAN, `thickness`:FLOAT, `offset`:FLOAT, `use_crease`:BOOLEAN, `crease_weight`:FLOAT |

### `nla` — 39개 (✅ 1 / ⚠ 0 / ❌ 38)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `nla.action_pushdown` | Push action down onto the top of the NLA stack as a new strip | `track_index`:INT |
| ❌ | `nla.action_sync_length` | Synchronize the length of the referenced Action with the length used in the strip | `active`:BOOLEAN |
| ❌ | `nla.action_unlink` | Unlink this action from the active action slot (and/or exit Tweak Mode) | `force_delete`:BOOLEAN |
| ❌ | `nla.actionclip_add` | Add an Action-Clip strip (i.e. an NLA Strip referencing an Action) to the active track | `action`= |
| ❌ | `nla.apply_scale` | Apply scaling of selected strips to their referenced Actions | — |
| ✅ | `nla.bake` | Bake all selected objects location/scale/rotation animation to an action | `frame_start`:INT, `frame_end`:INT, `step`:INT, `only_selected`:BOOLEAN, `visual_keying`:BOOLEAN, `clear_constraints`:BOOLEAN, `clear_parents`:BOOLEAN, `use_current_action`:BOOLEAN, `clean_curves`:BOOLEAN, `bake_types`=POSE/OBJECT, `channel_types`=LOCATION/ROTATION/SCALE/BBONE/PROPS |
| ❌ | `nla.channels_click` | Handle clicks to select NLA tracks | `extend`:BOOLEAN |
| ❌ | `nla.clear_scale` | Reset scaling of selected strips | — |
| ❌ | `nla.click_select` | Handle clicks to select NLA Strips | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `deselect_all`:BOOLEAN |
| ❌ | `nla.delete` | Delete selected strips | — |
| ❌ | `nla.duplicate` | Duplicate selected NLA-Strips, adding the new strips to new track(s) | `linked`:BOOLEAN |
| ❌ | `nla.duplicate_linked_move` | Duplicate Linked selected NLA-Strips, adding the new strips to new track(s) | `NLA_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `nla.duplicate_move` | Duplicate selected NLA-Strips, adding the new strips to new track(s) | `NLA_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `nla.fmodifier_add` | Add F-Modifier to the active/selected NLA-Strips | `type`=NULL/GENERATOR/FNGENERATOR/ENVELOPE/CYCLES/NOISE/LIMITS/STEPPED/SMOOTH, `only_active`:BOOLEAN |
| ❌ | `nla.fmodifier_copy` | Copy the F-Modifier(s) of the active NLA-Strip | — |
| ❌ | `nla.fmodifier_paste` | Add copied F-Modifiers to the selected NLA-Strips | `only_active`:BOOLEAN, `replace`:BOOLEAN |
| ❌ | `nla.make_single_user` | Make linked action local to each strip | `confirm`:BOOLEAN |
| ❌ | `nla.meta_add` | Add new meta-strips incorporating the selected strips | — |
| ❌ | `nla.meta_remove` | Separate out the strips held by the selected meta-strips | — |
| ❌ | `nla.move_down` | Move selected strips down a track if there's room | — |
| ❌ | `nla.move_up` | Move selected strips up a track if there's room | — |
| ❌ | `nla.mute_toggle` | Mute or un-mute selected strips | — |
| ❌ | `nla.previewrange_set` | Set Preview Range based on extents of selected strips | — |
| ❌ | `nla.select_all` | Select or deselect all NLA-Strips | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `nla.select_box` | Use box selection to grab NLA-Strips | `axis_range`:BOOLEAN, `tweak`:BOOLEAN, `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `nla.select_leftright` | Select strips to the left or the right of the current frame | `mode`=CHECK/LEFT/RIGHT, `extend`:BOOLEAN |
| ❌ | `nla.selected_objects_add` | Make selected objects appear in NLA Editor by adding Animation Data | — |
| ❌ | `nla.snap` | Move start of strips to specified time | `type`=CFRA/NEAREST_FRAME/NEAREST_SECOND/NEAREST_MARKER |
| ❌ | `nla.soundclip_add` | Add a strip for controlling when speaker plays its sound clip | — |
| ❌ | `nla.split` | Split selected strips at their midpoints | — |
| ❌ | `nla.swap` | Swap order of selected strips within tracks | — |
| ❌ | `nla.tracks_add` | Add NLA-Tracks above/after the selected tracks | `above_selected`:BOOLEAN |
| ❌ | `nla.tracks_delete` | Delete selected NLA-Tracks and the strips they contain | — |
| ❌ | `nla.transition_add` | Add a transition strip between two adjacent selected strips | — |
| ❌ | `nla.tweakmode_enter` | Enter tweaking mode for the action referenced by the active strip to edit its keyframes | `isolate_action`:BOOLEAN, `use_upper_stack_evaluation`:BOOLEAN |
| ❌ | `nla.tweakmode_exit` | Exit tweaking mode for the action referenced by the active strip | `isolate_action`:BOOLEAN |
| ❌ | `nla.view_all` | Reset viewable area to show full strips range | — |
| ❌ | `nla.view_frame` | Move the view to the current frame | — |
| ❌ | `nla.view_selected` | Reset viewable area to show selected strips range | — |

### `node` — 182개 (✅ 8 / ⚠ 0 / ❌ 174)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `node.activate_viewer` | Activate selected viewer node in compositor and geometry nodes | — |
| ❌ | `node.add_closure_zone` | Add a Closure zone | `settings`:COLLECTION, `use_transform`:BOOLEAN, `offset`:FLOAT |
| ❌ | `node.add_collection` | Add a collection info node to the current node editor | `name`:STRING, `session_uid`:INT |
| ❌ | `node.add_color` | Add a color node to the current node editor | `color`:FLOAT, `gamma`:BOOLEAN, `has_alpha`:BOOLEAN |
| ❌ | `node.add_empty_group` | Add a group node with an empty group | `settings`:COLLECTION, `use_transform`:BOOLEAN |
| ❌ | `node.add_foreach_geometry_element_zone` | Add a For Each Geometry Element zone that allows executing nodes e.g. for each vertex sepa | `settings`:COLLECTION, `use_transform`:BOOLEAN, `offset`:FLOAT |
| ❌ | `node.add_group` | Add an existing node group to the current node editor | `name`:STRING, `session_uid`:INT, `show_datablock_in_node`:BOOLEAN |
| ❌ | `node.add_group_asset` | Add a node group asset to the active node tree | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING |
| ❌ | `node.add_group_input_node` | Add a Group Input node with selected sockets to the current node editor | `only_selected_sockets`:BOOLEAN, `all_panel_contents`:BOOLEAN |
| ❌ | `node.add_image` | Add a image/movie file as node to the current node editor | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG, `name`:STRING, `session_uid`:INT |
| ❌ | `node.add_import_node` | Add an import node to the node tree | `directory`:STRING, `files`:COLLECTION |
| ❌ | `node.add_mask` | Add a mask node to the current node editor | `name`:STRING, `session_uid`:INT |
| ❌ | `node.add_material` | Add a material node to the current node editor | `name`:STRING, `session_uid`:INT |
| ❌ | `node.add_node` | Add a node to the active tree | `settings`:COLLECTION, `use_transform`:BOOLEAN, `type`:STRING, `visible_output`:STRING |
| ❌ | `node.add_object` | Add an object info node to the current node editor | `name`:STRING, `session_uid`:INT |
| ❌ | `node.add_repeat_zone` | Add a repeat zone that allows executing nodes a dynamic number of times | `settings`:COLLECTION, `use_transform`:BOOLEAN, `offset`:FLOAT |
| ❌ | `node.add_reroute` | Add a reroute node | `path`:COLLECTION, `cursor`:INT |
| ❌ | `node.add_simulation_zone` | Add simulation zone input and output nodes to the active tree | `settings`:COLLECTION, `use_transform`:BOOLEAN, `offset`:FLOAT |
| ❌ | `node.add_typed_bundle` | Add a Combine Bundle node with a type input | `settings`:COLLECTION, `use_transform`:BOOLEAN |
| ❌ | `node.add_zone` | (undocumented operator) | `settings`:COLLECTION, `use_transform`:BOOLEAN, `offset`:FLOAT, `input_node_type`:STRING, `output_node_type`:STRING, `add_default_geometry_link`:BOOLEAN |
| ❌ | `node.attach` | Attach active node to a frame | — |
| ❌ | `node.backimage_fit` | Fit the background image to the view | — |
| ❌ | `node.backimage_move` | Move node backdrop | — |
| ❌ | `node.backimage_sample` | Use mouse to sample background image | — |
| ❌ | `node.backimage_zoom` | Zoom in/out the background image | `factor`:FLOAT, `use_mouse_pos`:BOOLEAN |
| ❌ | `node.bake_node_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.bake_node_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.bake_node_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.capture_attribute_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.capture_attribute_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.capture_attribute_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.clear_viewer_border` | Clear the boundaries for viewer operations | — |
| ❌ | `node.clipboard_copy` | Copy the selected nodes to the internal clipboard | — |
| ❌ | `node.clipboard_paste` | Paste nodes from the internal clipboard to the active node tree | `offset`:FLOAT |
| ❌ | `node.closure_input_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.closure_input_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.closure_input_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.closure_output_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.closure_output_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.closure_output_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.closure_to_list_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.closure_to_list_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.closure_to_list_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.collapse_hide_unused_toggle` | Toggle collapsed nodes and hide unused sockets | — |
| ❌ | `node.combine_bundle_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.combine_bundle_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.combine_bundle_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.connect_to_output` | Connect active node to the active output node of the node tree | `run_in_geometry_nodes`:BOOLEAN |
| ❌ | `node.cryptomatte_layer_add` | Add a new input layer to a Cryptomatte node | — |
| ❌ | `node.cryptomatte_layer_remove` | Remove layer from a Cryptomatte node | — |
| ❌ | `node.deactivate_viewer` | Deactivate selected viewer node in geometry nodes | — |
| ❌ | `node.default_group_width_set` | Set the width based on the parent group node in the current context | — |
| ❌ | `node.delete` | Remove selected nodes | — |
| ❌ | `node.delete_copy_reconnect` | Copy nodes to clipboard, remove and reconnect them. | `NODE_OT_clipboard_copy`:POINTER, `NODE_OT_delete_reconnect`:POINTER |
| ❌ | `node.delete_reconnect` | Remove nodes and reconnect nodes as if deletion was muted | — |
| ❌ | `node.detach` | Detach selected nodes from parents | — |
| ❌ | `node.detach_translate_attach` | Detach nodes, move and attach to frame | `NODE_OT_detach`:POINTER, `TRANSFORM_OT_translate`:POINTER, `NODE_OT_attach`:POINTER |
| ❌ | `node.duplicate` | Duplicate selected nodes | `keep_inputs`:BOOLEAN, `linked`:BOOLEAN |
| ✅ | `node.duplicate_compositing_modifier_node_group` | Duplicate the currently assigned compositing node group. | — |
| ✅ | `node.duplicate_compositing_node_group` | Duplicate the currently assigned compositing node group. | — |
| ❌ | `node.duplicate_move` | Duplicate selected nodes and move them | `NODE_OT_duplicate`:POINTER, `NODE_OT_translate_attach`:POINTER |
| ❌ | `node.duplicate_move_keep_inputs` | Duplicate selected nodes keeping input links and move them | `NODE_OT_duplicate`:POINTER, `NODE_OT_translate_attach`:POINTER |
| ❌ | `node.duplicate_move_linked` | Duplicate selected nodes, but not their node trees, and move them | `NODE_OT_duplicate`:POINTER, `NODE_OT_translate_attach`:POINTER |
| ❌ | `node.enum_definition_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `item_name`:STRING |
| ❌ | `node.enum_definition_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.enum_definition_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.evaluate_closure_input_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.evaluate_closure_input_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.evaluate_closure_input_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.evaluate_closure_output_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.evaluate_closure_output_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.evaluate_closure_output_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.field_to_grid_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.field_to_grid_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.field_to_grid_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.field_to_list_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.field_to_list_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.field_to_list_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.file_output_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.file_output_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.file_output_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.find_node` | Search for a node by name and focus and select it | — |
| ❌ | `node.foreach_geometry_element_zone_generation_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.foreach_geometry_element_zone_generation_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.foreach_geometry_element_zone_generation_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.foreach_geometry_element_zone_input_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.foreach_geometry_element_zone_input_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.foreach_geometry_element_zone_input_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.foreach_geometry_element_zone_main_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.foreach_geometry_element_zone_main_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.foreach_geometry_element_zone_main_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.format_string_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.format_string_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.format_string_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.geometry_nodes_viewer_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.geometry_nodes_viewer_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.geometry_nodes_viewer_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.gltf_settings_node_operator` | Add a node to the active tree for glTF export | — |
| ❌ | `node.group_edit` | Edit node group | `exit`:BOOLEAN |
| ❌ | `node.group_enter_exit` | Enter or exit node group based on cursor location | — |
| ❌ | `node.group_insert` | Insert selected nodes into a node group | — |
| ❌ | `node.group_make` | Make group from selected nodes | — |
| ❌ | `node.group_separate` | Separate selected nodes from the node group | `type`=COPY/MOVE |
| ❌ | `node.group_ungroup` | Ungroup selected nodes | — |
| ❌ | `node.hide_socket_toggle` | Toggle unused node socket display | — |
| ❌ | `node.hide_toggle` | Toggle collapsing of selected nodes | — |
| ❌ | `node.index_switch_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN |
| ❌ | `node.index_switch_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.index_switch_item_remove` | Remove active item | `index`:INT |
| ❌ | `node.insert_offset` | Automatically offset nodes on insertion | — |
| ❌ | `node.interface_item_duplicate` | Add a copy of the active item to the interface | — |
| ❌ | `node.interface_item_make_panel_toggle` | Make the active boolean socket a toggle for its parent panel | — |
| ❌ | `node.interface_item_new` | Add a new item to the interface | `item_type`=INPUT/OUTPUT/PANEL |
| ❌ | `node.interface_item_new_panel_toggle` | Add a checkbox to the currently selected panel | — |
| ❌ | `node.interface_item_remove` | Remove selected items from the interface | — |
| ❌ | `node.interface_item_unlink_panel_toggle` | Make the panel toggle a stand-alone socket | — |
| ❌ | `node.join` | Attach selected nodes to a new common frame | — |
| ❌ | `node.join_named` | Create a new frame node around the selected nodes and name it immediately | `NODE_OT_join`:POINTER, `WM_OT_call_panel`:POINTER |
| ❌ | `node.join_nodes` | Merge selected group input nodes into one if possible | — |
| ❌ | `node.link` | Use the mouse to create a link between two nodes | `detach`:BOOLEAN, `drag_start`:FLOAT, `inside_padding`:FLOAT, `outside_padding`:FLOAT, `speed_ramp`:FLOAT, `max_speed`:FLOAT, `delay`:FLOAT, `zoom_influence`:FLOAT |
| ❌ | `node.link_drag_operation_test` | Run a node link-drag operation for testing | `find_link_operations`:BOOLEAN, `link_operation_index`:INT |
| ❌ | `node.link_make` | Make a link between selected output and input sockets | `replace`:BOOLEAN |
| ❌ | `node.link_viewer` | Link to viewer node | — |
| ❌ | `node.links_cut` | Use the mouse to cut (remove) some links | `path`:COLLECTION, `cursor`:INT |
| ❌ | `node.links_detach` | Remove all links to selected nodes, and try to connect neighbor nodes together | — |
| ❌ | `node.links_mute` | Use the mouse to mute links | `path`:COLLECTION, `cursor`:INT |
| ❌ | `node.move_detach_links` | Move a node to detach links | `NODE_OT_links_detach`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `node.move_detach_links_release` | Move a node to detach links | `NODE_OT_links_detach`:POINTER, `NODE_OT_translate_attach`:POINTER |
| ❌ | `node.mute_toggle` | Toggle muting of selected nodes | — |
| ✅ | `node.new_compositing_node_group` | Create a new compositing node group and initialize it with default nodes | `name`:STRING |
| ✅ | `node.new_compositor_sequencer_node_group` | Create a new compositor node group for sequencer | `name`:STRING |
| ✅ | `node.new_geometry_node_group_assign` | Create a new geometry node group and assign it to the active modifier | — |
| ❌ | `node.new_geometry_node_group_tool` | Create a new geometry node group for a tool | — |
| ✅ | `node.new_geometry_nodes_modifier` | Create a new modifier with a new geometry node group | — |
| ✅ | `node.new_node_tree` | Create a new node tree | `type`=, `name`:STRING |
| ✅ | `node.node_color_preset_add` | Add or remove a Node Color Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ❌ | `node.node_copy_color` | Copy color to all selected nodes | — |
| ❌ | `node.options_toggle` | Toggle option buttons display for selected nodes | — |
| ❌ | `node.parent_set` | Attach selected nodes | — |
| ❌ | `node.preview_toggle` | Toggle preview display for selected nodes | — |
| ❌ | `node.read_viewlayers` | Read all render layers of all used scenes | — |
| ❌ | `node.render_changed` | Render current scene, when input node's layer has been changed | — |
| ❌ | `node.repeat_zone_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.repeat_zone_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.repeat_zone_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.resize` | Resize a node | — |
| ❌ | `node.sample_attribute_items_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.sample_attribute_items_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.sample_attribute_items_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.select` | Select the node under the cursor | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `location`:INT, `socket_select`:BOOLEAN, `clear_viewer`:BOOLEAN |
| ❌ | `node.select_all` | (De)select all nodes | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `node.select_box` | Use box selection to select nodes | `tweak`:BOOLEAN, `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `node.select_circle` | Use circle selection to select nodes | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `node.select_grouped` | Select nodes with similar properties | `extend`:BOOLEAN, `type`=TYPE/COLOR/PREFIX/SUFFIX |
| ❌ | `node.select_lasso` | Select nodes using lasso selection | `tweak`:BOOLEAN, `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB |
| ❌ | `node.select_link_viewer` | Select node and link it to a viewer node | `NODE_OT_select`:POINTER, `NODE_OT_link_viewer`:POINTER |
| ❌ | `node.select_linked_from` | Select nodes linked from the selected ones | — |
| ❌ | `node.select_linked_to` | Select nodes linked to the selected ones | — |
| ❌ | `node.select_same_type_step` | Activate and view same node type, step by step | `prev`:BOOLEAN |
| ❌ | `node.separate_bundle_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.separate_bundle_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.separate_bundle_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.shader_script_update` | Update shader script node with new sockets and options from the script | — |
| ❌ | `node.simulation_zone_item_add` | Add item below active item | `node_identifier`:INT, `show_dialog`:BOOLEAN, `init_from_active`:BOOLEAN, `socket_type`=FLOAT/INT/BOOLEAN/VECTOR/RGBA/ROTATION/MATRIX/STRING/MENU/SHADER/OBJECT/IMAGE/GEOMETRY/COLLECTION/TEXTURE/MATERIAL/BUNDLE/CLOSURE/FONT/SCENE/TEXT/MASK/SOUND/INT_VECTOR, `item_name`:STRING |
| ❌ | `node.simulation_zone_item_move` | Move active item | `direction`=UP/DOWN, `node_identifier`:INT |
| ❌ | `node.simulation_zone_item_remove` | Remove active item | `node_identifier`:INT |
| ❌ | `node.sockets_sync` | Update sockets to match what is actually used | `node_name`:STRING |
| ❌ | `node.swap_empty_group` | Replace active node with an empty group | `settings`:COLLECTION |
| ❌ | `node.swap_group_asset` | Swap selected nodes with the specified node group asset | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING |
| ❌ | `node.swap_node` | Replace the selected nodes with the specified type | `settings`:COLLECTION, `type`:STRING, `visible_output`:STRING |
| ❌ | `node.swap_typed_bundle` | Swap existing node with a Combine Bundle node with a type input | `settings`:COLLECTION |
| ❌ | `node.swap_zone` | (undocumented operator) | `settings`:COLLECTION, `offset`:FLOAT, `input_node_type`:STRING, `output_node_type`:STRING, `add_default_geometry_link`:BOOLEAN |
| ❌ | `node.test_inlining_shader_nodes` | Create a new inlined shader node tree as is consumed by renderers | — |
| ❌ | `node.toggle_viewer` | Toggle selected viewer node in compositor and geometry nodes | — |
| ❌ | `node.translate_attach` | Move nodes and attach to frame | `TRANSFORM_OT_translate`:POINTER, `NODE_OT_attach`:POINTER |
| ❌ | `node.translate_attach_remove_on_cancel` | Move nodes and attach to frame | `TRANSFORM_OT_translate`:POINTER, `NODE_OT_attach`:POINTER |
| ❌ | `node.tree_path_parent` | Go to parent node tree | `parent_tree_index`:INT |
| ❌ | `node.view_all` | Resize view so you can see all nodes | — |
| ❌ | `node.view_selected` | Resize view so you can see selected nodes | — |
| ❌ | `node.viewer_border` | Set the boundaries for viewer operations (Not implemented) | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `node.viewer_shortcut_get` | Toggle a specific viewer node using 1,2,..,9 keys | `viewer_index`:INT |
| ❌ | `node.viewer_shortcut_set` | Create a viewer shortcut for the selected node by pressing ctrl+1,2,..9 | `viewer_index`:INT |

### `object` — 250개 (✅ 161 / ⚠ 26 / ❌ 63)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `object.add` | Add an object to the scene | `radius`:FLOAT, `type`=MESH/CURVE/SURFACE/META/FONT/CURVES/POINTCLOUD/VOLUME/GREASEPENCIL/ARMATURE/LATTICE/EMPTY/LIGHT/LIGHT_PROBE/CAMERA/SPEAKER, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `object.add_modifier_menu` | (undocumented operator) | — |
| ✅ | `object.add_named` | Add named object | `linked`:BOOLEAN, `name`:STRING, `session_uid`:INT, `matrix`:FLOAT, `drop_x`:INT, `drop_y`:INT |
| ✅ | `object.align` | Align objects | `bb_quality`:BOOLEAN, `align_mode`=OPT_1/OPT_2/OPT_3, `relative_to`=OPT_1/OPT_2/OPT_3/OPT_4, `align_axis`=X/Y/Z |
| ✅ | `object.anim_transforms_to_deltas` | Convert object animation for normal transforms to delta transforms | — |
| ✅ | `object.armature_add` | Add an armature object to the scene | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.assign_property_defaults` | Assign the current values of custom properties as their defaults, for use as part of the r | `process_data`:BOOLEAN, `process_bones`:BOOLEAN |
| ⚠ | `object.bake` | Bake image textures of selected objects | `type`=COMBINED/AO/SHADOW/POSITION/NORMAL/UV/ROUGHNESS/EMIT/ENVIRONMENT/DIFFUSE/GLOSSY/TRANSMISSION, `pass_filter`=NONE/EMIT/DIRECT/INDIRECT/COLOR/DIFFUSE/GLOSSY/TRANSMISSION, `filepath`:STRING, `width`:INT, `height`:INT, `margin`:INT, `margin_type`=ADJACENT_FACES/EXTEND, `use_selected_to_active`:BOOLEAN, `max_ray_distance`:FLOAT, `cage_extrusion`:FLOAT, `cage_object`:STRING, `normal_space`=OBJECT/TANGENT, `normal_r`=POS_X/POS_Y/POS_Z/NEG_X/NEG_Y/NEG_Z, `normal_g`=POS_X/POS_Y/POS_Z/NEG_X/NEG_Y/NEG_Z, `normal_b`=POS_X/POS_Y/POS_Z/NEG_X/NEG_Y/NEG_Z, `target`=IMAGE_TEXTURES/VERTEX_COLORS, `save_mode`=INTERNAL/EXTERNAL, `use_clear`:BOOLEAN, `use_cage`:BOOLEAN, `use_split_materials`:BOOLEAN, `use_automatic_name`:BOOLEAN, `uv_layer`:STRING |
| ✅ | `object.bake_image` | Bake image textures of selected objects | — |
| ✅ | `object.camera_add` | Add a camera object to the scene | `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `object.camera_custom_update` | Update custom camera with new parameters from the shader | — |
| ❌ | `object.clear_override_library` | Delete the selected local overrides and relink their usages to the linked data-blocks if p | — |
| ✅ | `object.collection_add` | Add an object to a new collection | — |
| ✅ | `object.collection_external_asset_drop` | Add the dragged collection to the scene | `session_uid`:INT, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT, `use_instance`:BOOLEAN, `drop_x`:INT, `drop_y`:INT, `collection`= |
| ✅ | `object.collection_instance_add` | Add a collection instance | `name`:STRING, `collection`=, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT, `session_uid`:INT, `drop_x`:INT, `drop_y`:INT |
| ✅ | `object.collection_link` | Add an object to an existing collection | `collection`= |
| ✅ | `object.collection_objects_select` | Select all objects in collection | — |
| ✅ | `object.collection_remove` | Remove the active object from this collection | — |
| ⚠ | `object.collection_unlink` | Unlink the collection from all objects | — |
| ✅ | `object.constraint_add` | Add a constraint to the active object | `type`= |
| ✅ | `object.constraint_add_with_targets` | Add a constraint to the active object, with target (where applicable) set to the selected  | `type`= |
| ✅ | `object.constraints_clear` | Clear all constraints from the selected objects | — |
| ✅ | `object.constraints_copy` | Copy constraints to other selected objects | — |
| ✅ | `object.convert` | Convert selected objects to another type | `target`=CURVE/MESH/POINTCLOUD/CURVES/GREASEPENCIL, `keep_original`:BOOLEAN, `merge_customdata`:BOOLEAN, `thickness`:INT, `faces`:BOOLEAN, `offset`:FLOAT |
| ✅ | `object.copy_global_transform` | Copies the matrix of the currently active object or pose bone to the clipboard. Uses world | — |
| ✅ | `object.copy_relative_transform` | Copies the matrix of the currently active object or pose bone to the clipboard. Uses matri | — |
| ✅ | `object.correctivesmooth_bind` | Bind base pose in Corrective Smooth modifier | `modifier`:STRING |
| ⚠ | `object.curves_empty_hair_add` | Add an empty curve object to the scene with the selected mesh as surface | `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.curves_random_add` | Add a curves object with random curves to the scene | `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.data_instance_add` | Add an object data instance | `name`:STRING, `session_uid`:INT, `type`=ACTION/ARMATURE/BRUSH/CACHEFILE/CAMERA/COLLECTION/CURVE/CURVES/FONT/GREASEPENCIL/GREASEPENCIL_V3/IMAGE/KEY/LATTICE/LIBRARY/LIGHT/LIGHT_PROBE/LINESTYLE/MASK/MATERIAL/MESH/META/MOVIECLIP/NODETREE/OBJECT/PAINTCURVE/PALETTE/PARTICLE/POINTCLOUD/SCENE/SCREEN/SOUND/SPEAKER/TEXT/TEXTURE/VOLUME/WINDOWMANAGER/WORKSPACE/WORLD, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT, `drop_x`:INT, `drop_y`:INT |
| ⚠ | `object.data_transfer` | Transfer data layer(s) (weights, edge sharp, etc.) from active to selected meshes | `use_reverse_transfer`:BOOLEAN, `use_freeze`:BOOLEAN, `data_type`=VGROUP_WEIGHTS/BEVEL_WEIGHT_VERT/COLOR_VERTEX/SHARP_EDGE/SEAM/CREASE/BEVEL_WEIGHT_EDGE/FREESTYLE_EDGE/CUSTOM_NORMAL/COLOR_CORNER/UV/SMOOTH/FREESTYLE_FACE, `use_create`:BOOLEAN, `vert_mapping`=TOPOLOGY/NEAREST/EDGE_NEAREST/EDGEINTERP_NEAREST/POLY_NEAREST/POLYINTERP_NEAREST/POLYINTERP_VNORPROJ, `edge_mapping`=TOPOLOGY/VERT_NEAREST/NEAREST/POLY_NEAREST/EDGEINTERP_VNORPROJ, `loop_mapping`=TOPOLOGY/NEAREST_NORMAL/NEAREST_POLYNOR/NEAREST_POLY/POLYINTERP_NEAREST/POLYINTERP_LNORPROJ, `poly_mapping`=TOPOLOGY/NEAREST/NORMAL/POLYINTERP_PNORPROJ, `use_auto_transform`:BOOLEAN, `use_object_transform`:BOOLEAN, `use_max_distance`:BOOLEAN, `max_distance`:FLOAT, `ray_radius`:FLOAT, `islands_precision`:FLOAT, `layers_select_src`=ACTIVE/ALL/BONE_SELECT/BONE_DEFORM, `layers_select_dst`=ACTIVE/NAME/INDEX, `mix_mode`=REPLACE/ABOVE_THRESHOLD/BELOW_THRESHOLD/MIX/ADD/SUB/MUL, `mix_factor`:FLOAT |
| ⚠ | `object.datalayout_transfer` | Transfer layout of data layer(s) from active to selected meshes | `modifier`:STRING, `data_type`=VGROUP_WEIGHTS/BEVEL_WEIGHT_VERT/COLOR_VERTEX/SHARP_EDGE/SEAM/CREASE/BEVEL_WEIGHT_EDGE/FREESTYLE_EDGE/CUSTOM_NORMAL/COLOR_CORNER/UV/SMOOTH/FREESTYLE_FACE, `use_delete`:BOOLEAN, `layers_select_src`=ACTIVE/ALL/BONE_SELECT/BONE_DEFORM, `layers_select_dst`=ACTIVE/NAME/INDEX |
| ✅ | `object.delete` | Delete selected objects | `use_global`:BOOLEAN, `confirm`:BOOLEAN |
| ✅ | `object.delete_fix_to_camera_keys` | Delete all keys that were generated by the 'Fix to Scene Camera' operator | — |
| ❌ | `object.drop_geometry_nodes` | (undocumented operator) | `session_uid`:INT, `show_datablock_in_modifier`:BOOLEAN |
| ❌ | `object.drop_named_material` | (undocumented operator) | `name`:STRING, `session_uid`:INT |
| ✅ | `object.duplicate` | Duplicate selected objects | `linked`:BOOLEAN, `mode`=INIT/DUMMY/TRANSLATION/ROTATION/RESIZE/SKIN_RESIZE/TOSPHERE/SHEAR/BEND/SHRINKFATTEN/TILT/TRACKBALL/PUSHPULL/CREASE/VERTEX_CREASE/MIRROR/BONE_SIZE/BONE_ENVELOPE/BONE_ENVELOPE_DIST/CURVE_SHRINKFATTEN/MASK_SHRINKFATTEN/BONE_ROLL/TIME_TRANSLATE/TIME_SLIDE/TIME_SCALE/TIME_EXTEND/BAKE_TIME/BWEIGHT/ALIGN/EDGESLIDE/SEQSLIDE/GPENCIL_OPACITY |
| ✅ | `object.duplicate_move` | Duplicate the selected objects and move them | `OBJECT_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ✅ | `object.duplicate_move_linked` | Duplicate the selected objects, but not their object data, and move them | `OBJECT_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ✅ | `object.duplicates_make_real` | Make instanced objects attached to this object real | `use_base_parent`:BOOLEAN, `use_hierarchy`:BOOLEAN |
| ✅ | `object.editmode_toggle` | Toggle object's edit mode | — |
| ✅ | `object.effector_add` | Add an empty object with a physics effector to the scene | `type`=FORCE/WIND/VORTEX/MAGNET/HARMONIC/CHARGE/LENNARDJ/TEXTURE/GUIDE/BOID/TURBULENCE/DRAG/FLUID, `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.empty_add` | Add an empty object to the scene | `type`=PLAIN_AXES/ARROWS/SINGLE_ARROW/CIRCLE/CUBE/SPHERE/CONE/IMAGE, `radius`:FLOAT, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ❌ | `object.empty_image_add` | Add an empty image type to scene with data | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG, `name`:STRING, `session_uid`:INT, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT, `background`:BOOLEAN |
| ✅ | `object.explode_refresh` | Refresh data in the Explode modifier | `modifier`:STRING |
| ✅ | `object.fix_to_camera` | Generate new keys to fix the selected object/bone to the camera on unkeyed frames | `use_location`:BOOLEAN, `use_rotation`:BOOLEAN, `use_scale`:BOOLEAN |
| ✅ | `object.forcefield_toggle` | Toggle object's force field | — |
| ✅ | `object.geometry_node_bake_delete_single` | Delete baked data of a single bake node or simulation | `session_uid`:INT, `modifier_name`:STRING, `bake_id`:INT |
| ✅ | `object.geometry_node_bake_pack_single` | Pack baked data from disk into the .blend file | `session_uid`:INT, `modifier_name`:STRING, `bake_id`:INT |
| ✅ | `object.geometry_node_bake_single` | Bake a single bake node or simulation | `session_uid`:INT, `modifier_name`:STRING, `bake_id`:INT |
| ✅ | `object.geometry_node_bake_unpack_single` | Unpack baked data from the .blend file to disk | `session_uid`:INT, `modifier_name`:STRING, `bake_id`:INT, `method`=USE_LOCAL/WRITE_LOCAL/USE_ORIGINAL/WRITE_ORIGINAL |
| ✅ | `object.geometry_node_tree_copy_assign` | Duplicate the active geometry node group and assign it to the active modifier | — |
| ✅ | `object.geometry_nodes_input_attribute_toggle` | Switch between an attribute and a single value to define the data for every element | `input_name`:STRING, `modifier_name`:STRING |
| ✅ | `object.geometry_nodes_move_to_nodes` | Move inputs and outputs from in the modifier to a new node group | `use_selected_objects`:BOOLEAN |
| ✅ | `object.grease_pencil_add` | Add a Grease Pencil object to the scene | `type`=EMPTY/STROKE/MONKEY/LINEART_SCENE/LINEART_COLLECTION/LINEART_OBJECT, `use_in_front`:BOOLEAN, `stroke_depth_offset`:FLOAT, `use_lights`:BOOLEAN, `stroke_depth_order`=2D/3D, `radius`:FLOAT, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.grease_pencil_dash_modifier_segment_add` | Add a segment to the dash modifier | `modifier`:STRING |
| ✅ | `object.grease_pencil_dash_modifier_segment_move` | Move the active dash segment up or down | `modifier`:STRING, `type`=UP/DOWN |
| ✅ | `object.grease_pencil_dash_modifier_segment_remove` | Remove the active segment from the dash modifier | `modifier`:STRING, `index`:INT |
| ✅ | `object.grease_pencil_time_modifier_segment_add` | Add a segment to the time modifier | `modifier`:STRING |
| ✅ | `object.grease_pencil_time_modifier_segment_move` | Move the active time segment up or down | `modifier`:STRING, `type`=UP/DOWN |
| ✅ | `object.grease_pencil_time_modifier_segment_remove` | Remove the active segment from the time modifier | `modifier`:STRING, `index`:INT |
| ✅ | `object.hide_collection` | Show only objects in collection (Shift to extend) | `collection_index`:INT, `toggle`:BOOLEAN, `extend`:BOOLEAN |
| ✅ | `object.hide_render_clear_all` | Reveal all render objects by setting the hide render flag | — |
| ❌ | `object.hide_view_clear` | Reveal temporarily hidden objects | `select`:BOOLEAN |
| ❌ | `object.hide_view_set` | Temporarily hide objects from the viewport | `unselected`:BOOLEAN |
| ❌ | `object.hook_add_newob` | Hook selected vertices to a newly created object | — |
| ❌ | `object.hook_add_selob` | Hook selected vertices to the first selected object | `use_bone`:BOOLEAN |
| ❌ | `object.hook_assign` | Assign the selected vertices to a hook | `modifier`= |
| ❌ | `object.hook_recenter` | Set hook center to cursor position | `modifier`= |
| ❌ | `object.hook_remove` | Remove a hook from the active object | `modifier`= |
| ❌ | `object.hook_reset` | Recalculate and clear offset transformation | `modifier`= |
| ❌ | `object.hook_select` | Select affected vertices on mesh | `modifier`= |
| ✅ | `object.instance_offset_from_cursor` | Set offset used for collection instances based on cursor position | — |
| ✅ | `object.instance_offset_from_object` | Set offset used for collection instances based on the active object position | — |
| ✅ | `object.instance_offset_to_cursor` | Set cursor position to the offset used for collection instances | — |
| ✅ | `object.isolate_type_render` | Hide unselected render objects of same type as active by setting the hide render flag | — |
| ⚠ | `object.join` | Join selected objects into active object | — |
| ⚠ | `object.join_shapes` | Add the vertex positions of selected objects as shape keys or update existing shape keys w | `use_mirror`:BOOLEAN |
| ⚠ | `object.join_uvs` | Transfer UV Maps from active to selected objects (needs matching geometry) | — |
| ✅ | `object.laplaciandeform_bind` | Bind mesh to system in laplacian deform modifier | `modifier`:STRING |
| ✅ | `object.lattice_add_to_selected` | Add a lattice and use it to deform selected objects | `fit_to_selected`:BOOLEAN, `radius`:FLOAT, `margin`:FLOAT, `add_modifiers`:BOOLEAN, `resolution_u`:INT, `resolution_v`:INT, `resolution_w`:INT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.light_add` | Add a light object to the scene | `type`=POINT/SUN/SPOT/AREA, `radius`:FLOAT, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.light_linking_blocker_collection_new` | Create new light linking collection used by the active emitter | — |
| ✅ | `object.light_linking_blockers_link` | Light link selected blockers to the active emitter object | `link_state`=INCLUDE/EXCLUDE |
| ✅ | `object.light_linking_blockers_select` | Select all objects which block light from this emitter | — |
| ✅ | `object.light_linking_receiver_collection_new` | Create new light linking collection used by the active emitter | — |
| ✅ | `object.light_linking_receivers_link` | Light link selected receivers to the active emitter object | `link_state`=INCLUDE/EXCLUDE |
| ✅ | `object.light_linking_receivers_select` | Select all objects which receive light from this emitter | — |
| ✅ | `object.light_linking_unlink_from_collection` | Remove this object or collection from the light linking collection | — |
| ✅ | `object.lightprobe_add` | Add a light probe object | `type`=SPHERE/PLANE/VOLUME, `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.lightprobe_cache_bake` | Bake irradiance volume light cache | `subset`=ALL/SELECTED/ACTIVE |
| ✅ | `object.lightprobe_cache_free` | Delete cached indirect lighting | `subset`=ALL/SELECTED/ACTIVE |
| ❌ | `object.lineart_bake_strokes` | Bake Line Art for current Grease Pencil object | `bake_all`:BOOLEAN |
| ❌ | `object.lineart_clear` | Clear all strokes in current Grease Pencil object | `clear_all`:BOOLEAN |
| ✅ | `object.link_to_collection` | Link objects to a collection | `collection_uid`:INT, `is_new`:BOOLEAN, `new_collection_name`:STRING |
| ✅ | `object.location_clear` | Clear the object's location | `clear_delta`:BOOLEAN |
| ✅ | `object.make_dupli_face` | Convert objects into instanced faces | — |
| ✅ | `object.make_links_data` | Transfer data from active object to selected objects | `type`=OBDATA/MATERIAL/ANIMATION/GROUPS/DUPLICOLLECTION/FONTS/MODIFIERS/CONSTRAINTS/EFFECTS/LIGHT_LINKING/SHADOW_LINKING |
| ✅ | `object.make_links_scene` | Link selection to another scene | `scene`= |
| ✅ | `object.make_local` | Make library linked data-blocks local to this file | `type`=SELECT_OBJECT/SELECT_OBDATA/SELECT_OBDATA_MATERIAL/ALL |
| ❌ | `object.make_override_library` | Create a local override of the selected linked objects, and their hierarchy of dependencie | `collection`:INT |
| ✅ | `object.make_single_user` | Make linked data local to each object | `type`=SELECTED_OBJECTS/ALL, `object`:BOOLEAN, `obdata`:BOOLEAN, `material`:BOOLEAN, `animation`:BOOLEAN, `obdata_animation`:BOOLEAN |
| ✅ | `object.material_slot_add` | Add a new material slot | — |
| ✅ | `object.material_slot_assign` | Assign active material slot to selection | — |
| ⚠ | `object.material_slot_copy` | Copy material to selected objects | — |
| ✅ | `object.material_slot_deselect` | Deselect by active material slot | — |
| ✅ | `object.material_slot_move` | Move the active material up/down in the list | `direction`=UP/DOWN |
| ⚠ | `object.material_slot_remove` | Remove the selected material slot | — |
| ⚠ | `object.material_slot_remove_all` | Remove all materials | — |
| ⚠ | `object.material_slot_remove_unused` | Remove unused material slots | — |
| ✅ | `object.material_slot_select` | Select by active material slot | — |
| ✅ | `object.meshdeform_bind` | Bind mesh to cage in mesh deform modifier | `modifier`:STRING |
| ✅ | `object.metaball_add` | Add a metaball object to the scene | `type`=BALL/CAPSULE/PLANE/ELLIPSOID/CUBE, `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.mode_set` | Sets the object interaction mode | `mode`=OBJECT/EDIT/POSE/SCULPT/VERTEX_PAINT/WEIGHT_PAINT/TEXTURE_PAINT/PARTICLE_EDIT/EDIT_GPENCIL/SCULPT_GREASE_PENCIL/PAINT_GREASE_PENCIL/WEIGHT_GREASE_PENCIL/VERTEX_GREASE_PENCIL/SCULPT_CURVES, `toggle`:BOOLEAN |
| ✅ | `object.mode_set_with_submode` | Sets the object interaction mode | `mode`=OBJECT/EDIT/POSE/SCULPT/VERTEX_PAINT/WEIGHT_PAINT/TEXTURE_PAINT/PARTICLE_EDIT/EDIT_GPENCIL/SCULPT_GREASE_PENCIL/PAINT_GREASE_PENCIL/WEIGHT_GREASE_PENCIL/VERTEX_GREASE_PENCIL/SCULPT_CURVES, `toggle`:BOOLEAN, `mesh_select_mode`=VERT/EDGE/FACE |
| ✅ | `object.modifier_add` | Add a procedural operation/effect to the active object | `type`=GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY/DATA_TRANSFER/MESH_CACHE/MESH_SEQUENCE_CACHE/NORMAL_EDIT/WEIGHTED_NORMAL/UV_PROJECT/UV_WARP/VERTEX_WEIGHT_EDIT/VERTEX_WEIGHT_MIX/VERTEX_WEIGHT_PROXIMITY/GREASE_PENCIL_COLOR/GREASE_PENCIL_TINT/GREASE_PENCIL_OPACITY/GREASE_PENCIL_VERTEX_WEIGHT_ANGLE/GREASE_PENCIL_TIME/GREASE_PENCIL_TEXTURE/ARRAY/BEVEL/BOOLEAN/BUILD/DECIMATE/EDGE_SPLIT/NODES/MASK/MIRROR/MESH_TO_VOLUME/MULTIRES/REMESH/SCREW/SKIN/SOLIDIFY/SUBSURF/TRIANGULATE/VOLUME_TO_MESH/WELD/WIREFRAME/GREASE_PENCIL_ARRAY/GREASE_PENCIL_BUILD/GREASE_PENCIL_LENGTH/LINEART/GREASE_PENCIL_MIRROR/GREASE_PENCIL_MULTIPLY/GREASE_PENCIL_SIMPLIFY/GREASE_PENCIL_SUBDIV/GREASE_PENCIL_ENVELOPE/GREASE_PENCIL_OUTLINE/ARMATURE/CAST/CURVE/DISPLACE/HOOK/LAPLACIANDEFORM/LATTICE/MESH_DEFORM/SHRINKWRAP/SIMPLE_DEFORM/SMOOTH/CORRECTIVE_SMOOTH/LAPLACIANSMOOTH/SURFACE_DEFORM/WARP/WAVE/VOLUME_DISPLACE/GREASE_PENCIL_HOOK/GREASE_PENCIL_NOISE/GREASE_PENCIL_OFFSET/GREASE_PENCIL_SMOOTH/GREASE_PENCIL_THICKNESS/GREASE_PENCIL_LATTICE/GREASE_PENCIL_DASH/GREASE_PENCIL_ARMATURE/GREASE_PENCIL_SHRINKWRAP/CLOTH/COLLISION/DYNAMIC_PAINT/EXPLODE/FLUID/OCEAN/PARTICLE_INSTANCE/PARTICLE_SYSTEM/SOFT_BODY/SURFACE, `use_selected_objects`:BOOLEAN |
| ✅ | `object.modifier_add_node_group` | Add a procedural operation/effect to the active object | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING, `session_uid`:INT, `use_selected_objects`:BOOLEAN |
| ✅ | `object.modifier_apply` | Apply modifier and remove from the stack | `modifier`:STRING, `report`:BOOLEAN, `merge_customdata`:BOOLEAN, `single_user`:BOOLEAN, `all_keyframes`:BOOLEAN, `use_selected_objects`:BOOLEAN |
| ✅ | `object.modifier_apply_as_shapekey` | Apply modifier as a new shape key and remove from the stack | `keep_modifier`:BOOLEAN, `modifier`:STRING, `report`:BOOLEAN, `use_selected_objects`:BOOLEAN |
| ✅ | `object.modifier_convert` | Convert particles to a mesh object | `modifier`:STRING |
| ✅ | `object.modifier_copy` | Duplicate modifier at the same position in the stack | `modifier`:STRING, `use_selected_objects`:BOOLEAN |
| ❌ | `object.modifier_copy_to_selected` | Copy the modifier from the active object to all selected objects | `modifier`:STRING |
| ✅ | `object.modifier_move_down` | Move modifier down in the stack | `modifier`:STRING |
| ✅ | `object.modifier_move_to_index` | Change the modifier's index in the stack so it evaluates after the set number of others | `modifier`:STRING, `index`:INT, `use_selected_objects`:BOOLEAN |
| ✅ | `object.modifier_move_up` | Move modifier up in the stack | `modifier`:STRING |
| ✅ | `object.modifier_remove` | Remove a modifier from the active object | `modifier`:STRING, `report`:BOOLEAN, `use_selected_objects`:BOOLEAN |
| ✅ | `object.modifier_set_active` | Activate the modifier to use as the context | `modifier`:STRING |
| ✅ | `object.modifiers_clear` | Clear all modifiers from the selected objects | — |
| ✅ | `object.modifiers_copy_to_selected` | Copy modifiers to other selected objects | — |
| ✅ | `object.move_to_collection` | Move objects to a collection | `collection_uid`:INT, `is_new`:BOOLEAN, `new_collection_name`:STRING |
| ⚠ | `object.multires_base_apply` | Modify the base mesh to conform to the displaced mesh | `modifier`:STRING, `apply_heuristic`:BOOLEAN |
| ⚠ | `object.multires_external_pack` | Pack displacements from an external file | — |
| ⚠ | `object.multires_external_save` | Save displacements to an external file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `modifier`:STRING |
| ⚠ | `object.multires_higher_levels_delete` | Deletes the higher resolution mesh, potential loss of detail | `modifier`:STRING |
| ⚠ | `object.multires_rebuild_subdiv` | Rebuilds all possible subdivisions levels to generate a lower resolution base mesh | `modifier`:STRING |
| ⚠ | `object.multires_reshape` | Copy vertex coordinates from other object | `modifier`:STRING |
| ⚠ | `object.multires_subdivide` | Add a new level of subdivision | `modifier`:STRING, `mode`=CATMULL_CLARK/SIMPLE/LINEAR |
| ⚠ | `object.multires_unsubdivide` | Rebuild a lower subdivision level of the current base mesh | `modifier`:STRING |
| ✅ | `object.ocean_bake` | Bake an image sequence of ocean data | `modifier`:STRING, `free`:BOOLEAN |
| ✅ | `object.origin_clear` | Clear the object's origin | — |
| ✅ | `object.origin_set` | Set the object's origin, by either moving the data, or set to center of data, or use 3D cu | `type`=GEOMETRY_ORIGIN/ORIGIN_GEOMETRY/ORIGIN_CURSOR/ORIGIN_CENTER_OF_MASS/ORIGIN_CENTER_OF_VOLUME, `center`=MEDIAN/BOUNDS |
| ✅ | `object.parent_clear` | Clear the object's parenting | `type`=CLEAR/CLEAR_KEEP_TRANSFORM/CLEAR_INVERSE |
| ✅ | `object.parent_inverse_apply` | Apply the object's parent inverse to its data | — |
| ✅ | `object.parent_no_inverse_set` | Set the object's parenting without setting the inverse parent correction | `keep_transform`:BOOLEAN |
| ✅ | `object.parent_set` | Set the object's parenting | `type`=OBJECT/ARMATURE/ARMATURE_NAME/ARMATURE_AUTO/ARMATURE_ENVELOPE/BONE/BONE_RELATIVE/CURVE/FOLLOW/PATH_CONST/LATTICE/VERTEX/VERTEX_TRI, `xmirror`:BOOLEAN, `keep_transform`:BOOLEAN |
| ✅ | `object.particle_system_add` | Add a particle system | — |
| ✅ | `object.particle_system_remove` | Remove the selected particle system | — |
| ✅ | `object.paste_transform` | Pastes the matrix from the clipboard to the currently active pose bone or object. Uses wor | `method`=CURRENT/EXISTING_KEYS/BAKE, `bake_step`:INT, `use_mirror`:BOOLEAN, `mirror_axis_loc`=x/y/z, `mirror_axis_rot`=x/y/z, `use_relative`:BOOLEAN |
| ✅ | `object.paths_calculate` | Generate motion paths for the selected objects | `display_type`=CURRENT_FRAME/RANGE, `range`=KEYS_ALL/KEYS_SELECTED/SCENE/MANUAL |
| ✅ | `object.paths_clear` | (undocumented operator) | `only_selected`:BOOLEAN |
| ❌ | `object.paths_update` | Recalculate motion paths for selected objects | — |
| ✅ | `object.paths_update_visible` | Recalculate all visible motion paths for objects and poses | — |
| ✅ | `object.pointcloud_random_add` | Add a point cloud object to the scene | `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.posemode_toggle` | Enable or disable posing/selecting bones | — |
| ⚠ | `object.quadriflow_remesh` | Create a new quad based mesh using the surface data of the current mesh. All data layers w | `use_mesh_symmetry`:BOOLEAN, `use_preserve_sharp`:BOOLEAN, `use_preserve_boundary`:BOOLEAN, `preserve_attributes`:BOOLEAN, `smooth_normals`:BOOLEAN, `mode`=RATIO/EDGE/FACES, `target_ratio`:FLOAT, `target_edge_length`:FLOAT, `target_faces`:INT, `mesh_area`:FLOAT, `seed`:INT |
| ✅ | `object.quick_explode` | Make selected objects explode | `style`=EXPLODE/BLEND, `amount`:INT, `frame_duration`:INT, `frame_start`:INT, `frame_end`:INT, `velocity`:FLOAT, `fade`:BOOLEAN |
| ⚠ | `object.quick_fur` | Add a fur setup to the selected objects | `density`=LOW/MEDIUM/HIGH, `length`:FLOAT, `radius`:FLOAT, `view_percentage`:FLOAT, `apply_hair_guides`:BOOLEAN, `use_noise`:BOOLEAN, `use_frizz`:BOOLEAN |
| ✅ | `object.quick_liquid` | Make selected objects liquid | `show_flows`:BOOLEAN |
| ✅ | `object.quick_smoke` | Use selected objects as smoke emitters | `style`=SMOKE/FIRE/BOTH, `show_flows`:BOOLEAN |
| ✅ | `object.randomize_transform` | Randomize objects location, rotation, and scale | `random_seed`:INT, `use_delta`:BOOLEAN, `use_loc`:BOOLEAN, `loc`:FLOAT, `use_rot`:BOOLEAN, `rot`:FLOAT, `use_scale`:BOOLEAN, `scale_even`:BOOLEAN, `scale`:FLOAT |
| ❌ | `object.reset_override_library` | Reset the selected local overrides to their linked references values | — |
| ✅ | `object.rotation_clear` | Clear the object's rotation | `clear_delta`:BOOLEAN |
| ✅ | `object.scale_clear` | Clear the object's scale | `clear_delta`:BOOLEAN |
| ✅ | `object.select_all` | Change selection of all visible objects in scene | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ✅ | `object.select_by_type` | Select all visible objects that are of a type | `extend`:BOOLEAN, `type`=MESH/CURVE/SURFACE/META/FONT/CURVES/POINTCLOUD/VOLUME/GREASEPENCIL/ARMATURE/LATTICE/EMPTY/LIGHT/LIGHT_PROBE/CAMERA/SPEAKER |
| ✅ | `object.select_camera` | Select the active camera | `extend`:BOOLEAN |
| ❌ | `object.select_grouped` | Select all visible objects grouped by various properties | `extend`:BOOLEAN, `type`=CHILDREN_RECURSIVE/CHILDREN/PARENT/SIBLINGS/TYPE/COLLECTION/HOOK/PASS/COLOR/KEYINGSET/LIGHT_TYPE |
| ✅ | `object.select_hierarchy` | Select object relative to the active object's position in the hierarchy | `direction`=PARENT/CHILD, `extend`:BOOLEAN |
| ✅ | `object.select_less` | Deselect objects at the boundaries of parent/child relationships | — |
| ✅ | `object.select_linked` | Select all visible objects that are linked | `extend`:BOOLEAN, `type`=OBDATA/MATERIAL/DUPGROUP/PARTICLE/LIBRARY/LIBRARY_OBDATA |
| ✅ | `object.select_mirror` | Select the mirror objects of the selected object e.g. "L.sword" and "R.sword" | `extend`:BOOLEAN |
| ✅ | `object.select_more` | Select connected parent/child objects | — |
| ✅ | `object.select_pattern` | Select objects matching a naming pattern | `pattern`:STRING, `case_sensitive`:BOOLEAN, `extend`:BOOLEAN |
| ✅ | `object.select_random` | Select or deselect random visible objects | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT |
| ✅ | `object.select_same_collection` | Select object in the same collection | `collection`:STRING |
| ✅ | `object.shade_auto_smooth` | Add modifier to automatically set the sharpness of mesh edges based on the angle between t | `use_auto_smooth`:BOOLEAN, `angle`:FLOAT |
| ✅ | `object.shade_flat` | Render and display faces uniform, using face normals | `keep_sharp_edges`:BOOLEAN |
| ✅ | `object.shade_smooth` | Render and display faces smooth, using interpolated vertex normals | `keep_sharp_edges`:BOOLEAN |
| ✅ | `object.shade_smooth_by_angle` | Set the sharpness of mesh edges based on the angle between the neighboring faces | `angle`:FLOAT, `keep_sharp_edges`:BOOLEAN |
| ✅ | `object.shaderfx_add` | Add a visual effect to the active object | `type`=FX_BLUR/FX_COLORIZE/FX_FLIP/FX_GLOW/FX_PIXEL/FX_RIM/FX_SHADOW/FX_SWIRL/FX_WAVE |
| ✅ | `object.shaderfx_copy` | Duplicate effect at the same position in the stack | `shaderfx`:STRING |
| ✅ | `object.shaderfx_move_down` | Move effect down in the stack | `shaderfx`:STRING |
| ✅ | `object.shaderfx_move_to_index` | Change the effect's position in the list so it evaluates after the set number of others | `shaderfx`:STRING, `index`:INT |
| ✅ | `object.shaderfx_move_up` | Move effect up in the stack | `shaderfx`:STRING |
| ✅ | `object.shaderfx_remove` | Remove a effect from the active Grease Pencil object | `shaderfx`:STRING, `report`:BOOLEAN |
| ✅ | `object.shape_key_add` | Add shape key to the object | `from_mix`:BOOLEAN |
| ❌ | `object.shape_key_apply_to_basis` | Apply deformations of selected shape keys to the basis key, removing them | — |
| ✅ | `object.shape_key_clear` | Reset the weights of all shape keys to 0 or to the closest value respecting the limits | — |
| ❌ | `object.shape_key_copy` | Duplicate the active shape key | — |
| ❌ | `object.shape_key_lock` | Change the lock state of all shape keys of active object | `action`=LOCK/UNLOCK |
| ❌ | `object.shape_key_make_basis` | Make this shape key the new basis key, effectively applying it to the mesh. Note that this | — |
| ❌ | `object.shape_key_mirror` | Mirror the current shape key along the local X axis | `use_topology`:BOOLEAN |
| ❌ | `object.shape_key_move` | Move selected shape keys up/down in the list | `type`=TOP/UP/DOWN/BOTTOM |
| ❌ | `object.shape_key_remove` | Remove shape key from the object | `all`:BOOLEAN, `apply_mix`:BOOLEAN |
| ✅ | `object.shape_key_retime` | Resets the timing for absolute shape keys | — |
| ⚠ | `object.shape_key_transfer` | Copy the active shape key of another selected object to this one | `mode`=OFFSET/RELATIVE_FACE/RELATIVE_EDGE, `use_clamp`:BOOLEAN |
| ✅ | `object.simulation_nodes_cache_bake` | Bake simulations in geometry nodes modifiers | `selected`:BOOLEAN |
| ✅ | `object.simulation_nodes_cache_calculate_to_frame` | Calculate simulations in geometry nodes modifiers from the start to current frame | `selected`:BOOLEAN |
| ✅ | `object.simulation_nodes_cache_delete` | Delete cached/baked simulations in geometry nodes modifiers | `selected`:BOOLEAN |
| ⚠ | `object.skin_armature_create` | Create an armature that parallels the skin layout | `modifier`:STRING |
| ❌ | `object.skin_loose_mark_clear` | Mark/clear selected vertices as loose | `action`=MARK/CLEAR |
| ❌ | `object.skin_radii_equalize` | Make skin radii of selected vertices equal on each axis | — |
| ❌ | `object.skin_root_mark` | Mark selected vertices as roots | — |
| ✅ | `object.speaker_add` | Add a speaker object to the scene | `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.subdivision_set` | Sets a Subdivision Surface level (1 to 5) | `level`:INT, `relative`:BOOLEAN, `ensure_modifier`:BOOLEAN |
| ✅ | `object.surfacedeform_bind` | Bind mesh to target in surface deform modifier | `modifier`:STRING |
| ✅ | `object.text_add` | Add a text object to the scene | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.track_clear` | Clear tracking constraint or flag from object | `type`=CLEAR/CLEAR_KEEP_TRANSFORM |
| ✅ | `object.track_set` | Make the object track another object, using various methods/constraints | `type`=DAMPTRACK/TRACKTO/LOCKTRACK |
| ❌ | `object.transfer_mode` | Switches the active object and assigns the same mode to a new one under the mouse cursor,  | `use_flash_on_transfer`:BOOLEAN |
| ✅ | `object.transform_apply` | Apply the object's transformation to its data | `location`:BOOLEAN, `rotation`:BOOLEAN, `scale`:BOOLEAN, `properties`:BOOLEAN, `corrective_flip_normals`:BOOLEAN, `isolate_users`:BOOLEAN |
| ❌ | `object.transform_axis_target` | Interactively point cameras and lights to the surface under the pointer (Ctrl to translate | — |
| ✅ | `object.transform_to_mouse` | Snap selected item(s) to the mouse location | `name`:STRING, `session_uid`:INT, `matrix`:FLOAT, `drop_x`:INT, `drop_y`:INT |
| ✅ | `object.transforms_to_deltas` | Convert normal object transforms to delta transforms, any existing delta transforms will b | `mode`=ALL/LOC/ROT/SCALE, `reset_values`:BOOLEAN |
| ✅ | `object.unlink_data` | (undocumented operator) | — |
| ❌ | `object.update_shapes` | Update existing shape keys with the vertex positions of selected objects with matching nam | `use_mirror`:BOOLEAN |
| ⚠ | `object.vertex_group_add` | Add a new vertex group to the active object | — |
| ❌ | `object.vertex_group_assign` | Assign the selected vertices to the active vertex group | — |
| ❌ | `object.vertex_group_assign_new` | Assign the selected vertices to a new vertex group | — |
| ❌ | `object.vertex_group_clean` | Remove vertex group assignments which are not required | `group_select_mode`=, `limit`:FLOAT, `keep_single`:BOOLEAN |
| ❌ | `object.vertex_group_copy` | Make a copy of the active vertex group | — |
| ❌ | `object.vertex_group_copy_to_selected` | Replace vertex groups of selected objects by vertex groups of active object | — |
| ❌ | `object.vertex_group_deselect` | Deselect all selected vertices assigned to the active vertex group | — |
| ❌ | `object.vertex_group_invert` | Invert active vertex group's weights | `group_select_mode`=, `auto_assign`:BOOLEAN, `auto_remove`:BOOLEAN |
| ❌ | `object.vertex_group_levels` | Add some offset and multiply with some gain the weights of the active vertex group | `group_select_mode`=, `offset`:FLOAT, `gain`:FLOAT |
| ❌ | `object.vertex_group_limit_total` | Limit deform weights associated with a vertex to a specified number by removing lowest wei | `group_select_mode`=, `limit`:INT |
| ❌ | `object.vertex_group_lock` | Change the lock state of all or some vertex groups of active object | `action`=TOGGLE/LOCK/UNLOCK/INVERT, `mask`=ALL/SELECTED/UNSELECTED/INVERT_UNSELECTED |
| ❌ | `object.vertex_group_mirror` | Mirror vertex group, flip weights and/or names, editing only selected vertices, flipping w | `mirror_weights`:BOOLEAN, `flip_group_names`:BOOLEAN, `all_groups`:BOOLEAN, `use_topology`:BOOLEAN |
| ❌ | `object.vertex_group_move` | Move the active vertex group up/down in the list | `direction`=UP/DOWN |
| ❌ | `object.vertex_group_normalize` | Normalize weights of the active vertex group, so that the highest ones are now 1.0 | — |
| ❌ | `object.vertex_group_normalize_all` | Normalize all weights of all vertex groups, so that for each vertex, the sum of all weight | `group_select_mode`=, `lock_active`:BOOLEAN |
| ❌ | `object.vertex_group_quantize` | Set weights to a fixed number of steps | `group_select_mode`=, `steps`:INT |
| ❌ | `object.vertex_group_remove` | Delete the active or all vertex groups from the active object | `all`:BOOLEAN, `all_unlocked`:BOOLEAN |
| ❌ | `object.vertex_group_remove_from` | Remove the selected vertices from active or all vertex group(s) | `use_all_groups`:BOOLEAN, `use_all_verts`:BOOLEAN |
| ❌ | `object.vertex_group_select` | Select all the vertices assigned to the active vertex group | — |
| ❌ | `object.vertex_group_set_active` | Set the active vertex group | `group`= |
| ❌ | `object.vertex_group_smooth` | Smooth weights for selected vertices | `group_select_mode`=, `factor`:FLOAT, `repeat`:INT, `expand`:FLOAT |
| ❌ | `object.vertex_group_sort` | Sort vertex groups | `sort_type`=NAME/BONE_HIERARCHY |
| ❌ | `object.vertex_parent_set` | Parent selected objects to the selected vertices | — |
| ❌ | `object.vertex_weight_copy` | Copy weights from active to selected | — |
| ❌ | `object.vertex_weight_delete` | Delete this weight from the vertex (disabled if vertex group is locked) | `weight_group`:INT |
| ❌ | `object.vertex_weight_normalize_active_vertex` | Normalize active vertex's weights | — |
| ❌ | `object.vertex_weight_paste` | Copy this group's weight to other selected vertices (disabled if vertex group is locked) | `weight_group`:INT |
| ❌ | `object.vertex_weight_set_active` | Set as active vertex group | `weight_group`:INT |
| ✅ | `object.visual_geometry_to_objects` | Convert geometry and instances into editable objects and collections | — |
| ✅ | `object.visual_transform_apply` | Apply the object's visual transformation to its data | — |
| ✅ | `object.volume_add` | Add a volume object to the scene | `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `object.volume_import` | Import OpenVDB volume file | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `use_sequence_detection`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ⚠ | `object.voxel_remesh` | Calculates a new manifold mesh based on the volume of the current mesh. All data layers wi | — |
| ❌ | `object.voxel_size_edit` | Modify the mesh voxel size interactively used in the voxel remesher | — |

### `outliner` — 73개 (✅ 2 / ⚠ 0 / ❌ 71)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `outliner.action_set` | Change the active action used | `action`= |
| ❌ | `outliner.animdata_operation` | (undocumented operator) | `type`=CLEAR_ANIMDATA/SET_ACT/CLEAR_ACT/REFRESH_DRIVERS/CLEAR_DRIVERS |
| ❌ | `outliner.clear_filter` | Clear the search filter | — |
| ❌ | `outliner.collection_color_tag_set` | Set a color tag for the selected collections | `color`=NONE/COLOR_01/COLOR_02/COLOR_03/COLOR_04/COLOR_05/COLOR_06/COLOR_07/COLOR_08 |
| ❌ | `outliner.collection_disable` | Disable viewport display in the view layers | — |
| ❌ | `outliner.collection_disable_render` | Do not render this collection | — |
| ❌ | `outliner.collection_drop` | Drag to move to collection in Outliner | — |
| ❌ | `outliner.collection_duplicate` | Recursively duplicate the collection, all its children, objects and object data | — |
| ❌ | `outliner.collection_duplicate_linked` | Recursively duplicate the collection, all its children and objects, with linked object dat | — |
| ❌ | `outliner.collection_enable` | Enable viewport display in the view layers | — |
| ❌ | `outliner.collection_enable_render` | Render the collection | — |
| ❌ | `outliner.collection_exclude_clear` | Include collection in the active view layer | — |
| ❌ | `outliner.collection_exclude_set` | Exclude collection from the active view layer | — |
| ❌ | `outliner.collection_hide` | Hide the collection in this view layer | — |
| ❌ | `outliner.collection_hide_inside` | Hide all the objects and collections inside the collection | — |
| ❌ | `outliner.collection_hierarchy_delete` | Delete selected collection hierarchies | — |
| ❌ | `outliner.collection_holdout_clear` | Clear masking of collection in the active view layer | — |
| ❌ | `outliner.collection_holdout_set` | Mask collection in the active view layer | — |
| ❌ | `outliner.collection_indirect_only_clear` | Clear collection contributing only indirectly in the view layer | — |
| ❌ | `outliner.collection_indirect_only_set` | Set collection to only contribute indirectly (through shadows and reflections) in the view | — |
| ❌ | `outliner.collection_instance` | Instance selected collections to active scene | — |
| ❌ | `outliner.collection_isolate` | Hide all but this collection and its parents | `extend`:BOOLEAN |
| ❌ | `outliner.collection_link` | Link selected collections to active scene | — |
| ❌ | `outliner.collection_new` | Add a new collection inside selected collection | `nested`:BOOLEAN |
| ❌ | `outliner.collection_objects_deselect` | Deselect objects in collection | — |
| ❌ | `outliner.collection_objects_select` | Select objects in collection | — |
| ❌ | `outliner.collection_show` | Show the collection in this view layer | — |
| ❌ | `outliner.collection_show_inside` | Show all the objects and collections inside the collection | — |
| ❌ | `outliner.constraint_operation` | (undocumented operator) | `type`=ENABLE/DISABLE/DELETE |
| ❌ | `outliner.data_operation` | (undocumented operator) | `type`=DEFAULT |
| ❌ | `outliner.datastack_drop` | Copy or reorder modifiers, constraints, and effects | — |
| ❌ | `outliner.delete` | Delete selected objects and collections | `hierarchy`:BOOLEAN |
| ❌ | `outliner.drivers_add_selected` | Add drivers to selected items | — |
| ❌ | `outliner.drivers_delete_selected` | Delete drivers assigned to selected items | — |
| ❌ | `outliner.expanded_toggle` | Expand/Collapse all items | — |
| ❌ | `outliner.hide` | Hide selected objects and collections | — |
| ❌ | `outliner.highlight_update` | Update the item highlight based on the current mouse position | — |
| ❌ | `outliner.id_copy` | Copy the selected data-blocks to the internal clipboard | — |
| ❌ | `outliner.id_delete` | Delete the ID under cursor | — |
| ❌ | `outliner.id_linked_relocate` | Replace the active linked ID (and its dependencies if any) by another one, from the same o | — |
| ❌ | `outliner.id_operation` | General data-block management operations | `type`=UNLINK/LOCAL/SINGLE/DELETE/REMAP/COPY/PASTE/ADD_FAKE/CLEAR_FAKE/RENAME/SELECT_LINKED |
| ❌ | `outliner.id_paste` | Paste data-blocks from the internal clipboard | — |
| ❌ | `outliner.id_remap` | (undocumented operator) | `id_type`=ACTION/ARMATURE/BRUSH/CACHEFILE/CAMERA/COLLECTION/CURVE/CURVES/FONT/GREASEPENCIL/GREASEPENCIL_V3/IMAGE/KEY/LATTICE/LIBRARY/LIGHT/LIGHT_PROBE/LINESTYLE/MASK/MATERIAL/MESH/META/MOVIECLIP/NODETREE/OBJECT/PAINTCURVE/PALETTE/PARTICLE/POINTCLOUD/SCENE/SCREEN/SOUND/SPEAKER/TEXT/TEXTURE/VOLUME/WINDOWMANAGER/WORKSPACE/WORLD, `old_id`:INT, `new_id`:INT |
| ❌ | `outliner.item_activate` | Handle mouse clicks to select and activate items | `extend`:BOOLEAN, `extend_range`:BOOLEAN, `deselect_all`:BOOLEAN, `recurse`:BOOLEAN |
| ❌ | `outliner.item_drag_drop` | Drag and drop element to another place | — |
| ❌ | `outliner.item_openclose` | Toggle whether item under cursor is open or closed | `all`:BOOLEAN |
| ❌ | `outliner.item_rename` | Rename the active element | `use_active`:BOOLEAN |
| ❌ | `outliner.keyingset_add_selected` | Add selected items (blue-gray rows) to active Keying Set | — |
| ❌ | `outliner.keyingset_remove_selected` | Remove selected items (blue-gray rows) from active Keying Set | — |
| ❌ | `outliner.lib_operation` | (undocumented operator) | `type`=DELETE/RELOCATE/RELOAD |
| ❌ | `outliner.lib_relocate` | Relocate the library under cursor | — |
| ❌ | `outliner.liboverride_operation` | Create, reset or clear library override hierarchies | `type`=OVERRIDE_LIBRARY_CREATE_HIERARCHY/OVERRIDE_LIBRARY_RESET/OVERRIDE_LIBRARY_CLEAR_SINGLE, `selection_set`=SELECTED/CONTENT/SELECTED_AND_CONTENT |
| ❌ | `outliner.liboverride_property_remove` | Remove the selected library override properties, and reset the relevant data to the linked | — |
| ❌ | `outliner.liboverride_troubleshoot_operation` | Advanced operations over library override to help fix broken hierarchies | `type`=OVERRIDE_LIBRARY_RESYNC_HIERARCHY/OVERRIDE_LIBRARY_RESYNC_HIERARCHY_ENFORCE/OVERRIDE_LIBRARY_DELETE_HIERARCHY, `selection_set`=SELECTED/CONTENT/SELECTED_AND_CONTENT |
| ❌ | `outliner.material_drop` | Drag material to object in Outliner | — |
| ❌ | `outliner.modifier_operation` | (undocumented operator) | `type`=APPLY/DELETE/TOGVIS/TOGREN |
| ❌ | `outliner.object_operation` | (undocumented operator) | `type`=SELECT/DESELECT/SELECT_HIERARCHY/REMAP/RENAME |
| ❌ | `outliner.operation` | Context menu for item operations | — |
| ✅ | `outliner.orphans_manage` | Open a window to manage unused data | — |
| ✅ | `outliner.orphans_purge` | Clear all orphaned data-blocks without any users from the file | `do_local_ids`:BOOLEAN, `do_linked_ids`:BOOLEAN, `do_recursive`:BOOLEAN |
| ❌ | `outliner.parent_clear` | Drag to clear parent in Outliner | — |
| ❌ | `outliner.parent_drop` | Drag to parent in Outliner | — |
| ❌ | `outliner.scene_drop` | Drag object to scene in Outliner | — |
| ❌ | `outliner.scene_operation` | Context menu for scene operations | `type`=DELETE |
| ❌ | `outliner.scroll_page` | Scroll page up or down | `up`:BOOLEAN |
| ❌ | `outliner.select_all` | Toggle the Outliner selection of items | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `outliner.select_box` | Use box selection to select tree elements | `tweak`:BOOLEAN, `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `outliner.select_walk` | Use walk navigation to select tree elements | `direction`=UP/DOWN/LEFT/RIGHT, `extend`:BOOLEAN, `toggle_all`:BOOLEAN |
| ❌ | `outliner.show_active` | Open up the tree and adjust the view so that the active object is shown centered | — |
| ❌ | `outliner.show_hierarchy` | Open all object entries and close all others | — |
| ❌ | `outliner.show_one_level` | Expand/collapse all entries by one level | `open`:BOOLEAN |
| ❌ | `outliner.start_filter` | Start entering filter text | — |
| ❌ | `outliner.unhide_all` | Unhide all objects and collections | — |

### `paint` — 55개 (✅ 1 / ⚠ 5 / ❌ 49)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `paint.add_simple_uvs` | Add cube map UVs on mesh | — |
| ⚠ | `paint.add_texture_paint_slot` | Add a paint slot | `type`=BASE_COLOR/SPECULAR/ROUGHNESS/METALLIC/NORMAL/BUMP/DISPLACEMENT, `slot_type`=IMAGE/COLOR_ATTRIBUTE, `name`:STRING, `color`:FLOAT, `width`:INT, `height`:INT, `alpha`:BOOLEAN, `generated_type`=BLANK/UV_GRID/COLOR_GRID, `float`:BOOLEAN, `tiled`:BOOLEAN, `domain`=POINT/CORNER, `data_type`=FLOAT_COLOR/BYTE_COLOR |
| ❌ | `paint.brush_colors_flip` | Swap primary and secondary brush colors | — |
| ❌ | `paint.face_select_all` | Change selection for all faces | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `paint.face_select_hide` | Hide selected faces | `unselected`:BOOLEAN |
| ❌ | `paint.face_select_less` | Deselect Faces connected to existing selection | `face_step`:BOOLEAN |
| ❌ | `paint.face_select_linked` | Select linked faces | — |
| ❌ | `paint.face_select_linked_pick` | Select linked faces under the cursor | `deselect`:BOOLEAN |
| ❌ | `paint.face_select_loop` | Select face loop under the cursor | `select`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `paint.face_select_more` | Select Faces connected to existing selection | `face_step`:BOOLEAN |
| ❌ | `paint.face_vert_reveal` | Reveal hidden faces and vertices | `select`:BOOLEAN |
| ❌ | `paint.grab_clone` | Move the clone source image | `delta`:FLOAT |
| ❌ | `paint.hide_show` | Hide/show some vertices | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `action`=HIDE/SHOW, `area`=OUTSIDE/Inside, `use_front_faces_only`:BOOLEAN |
| ❌ | `paint.hide_show_all` | Hide/show all vertices | `action`=HIDE/SHOW |
| ❌ | `paint.hide_show_lasso_gesture` | Hide/show some vertices | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `action`=HIDE/SHOW, `area`=OUTSIDE/Inside, `use_front_faces_only`:BOOLEAN |
| ❌ | `paint.hide_show_line_gesture` | Hide/show some vertices | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT, `action`=HIDE/SHOW, `area`=OUTSIDE/Inside, `use_front_faces_only`:BOOLEAN, `use_limit_to_segment`:BOOLEAN |
| ❌ | `paint.hide_show_masked` | Hide/show all masked vertices above a threshold | `action`=HIDE/SHOW |
| ❌ | `paint.hide_show_polyline_gesture` | Hide/show some vertices | `path`:COLLECTION, `action`=HIDE/SHOW, `area`=OUTSIDE/Inside, `use_front_faces_only`:BOOLEAN |
| ❌ | `paint.image_from_view` | Make an image from biggest 3D view for reprojection | `filepath`:STRING |
| ❌ | `paint.image_paint` | Paint a stroke into the image | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN |
| ❌ | `paint.mask_box_gesture` | Mask within a rectangle defined by the cursor | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `use_front_faces_only`:BOOLEAN, `mode`=VALUE/VALUE_INVERSE/INVERT, `value`:FLOAT |
| ❌ | `paint.mask_flood_fill` | Fill the whole mask with a given value, or invert its values | `mode`=VALUE/VALUE_INVERSE/INVERT, `value`:FLOAT |
| ❌ | `paint.mask_lasso_gesture` | Mask within a shape defined by the cursor | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `use_front_faces_only`:BOOLEAN, `mode`=VALUE/VALUE_INVERSE/INVERT, `value`:FLOAT |
| ❌ | `paint.mask_line_gesture` | Mask to one side of a line defined by the cursor | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT, `use_front_faces_only`:BOOLEAN, `use_limit_to_segment`:BOOLEAN, `mode`=VALUE/VALUE_INVERSE/INVERT, `value`:FLOAT |
| ❌ | `paint.mask_polyline_gesture` | Mask within a shape defined by the cursor | `path`:COLLECTION, `use_front_faces_only`:BOOLEAN, `mode`=VALUE/VALUE_INVERSE/INVERT, `value`:FLOAT |
| ✅ | `paint.project_image` | Project an edited render from the active camera back onto the object | `image`= |
| ❌ | `paint.sample_color` | Use the mouse to sample a color in the image | `location`:INT, `merged`:BOOLEAN, `palette`:BOOLEAN |
| ⚠ | `paint.texture_paint_toggle` | Toggle texture paint mode in 3D view | — |
| ❌ | `paint.vert_select_all` | Change selection for all vertices | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `paint.vert_select_hide` | Hide selected vertices | `unselected`:BOOLEAN |
| ❌ | `paint.vert_select_less` | Deselect Vertices connected to existing selection | `face_step`:BOOLEAN |
| ❌ | `paint.vert_select_linked` | Select linked vertices | — |
| ❌ | `paint.vert_select_linked_pick` | Select linked vertices under the cursor | `select`:BOOLEAN |
| ❌ | `paint.vert_select_loop` | Select vertex loop under the cursor | `select`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `paint.vert_select_more` | Select Vertices connected to existing selection | `face_step`:BOOLEAN |
| ❌ | `paint.vert_select_ungrouped` | Select vertices without a group | `extend`:BOOLEAN |
| ❌ | `paint.vertex_color_brightness_contrast` | Adjust vertex color brightness/contrast | `brightness`:FLOAT, `contrast`:FLOAT |
| ⚠ | `paint.vertex_color_dirt` | Generate a dirt map gradient based on cavity | `blur_strength`:FLOAT, `blur_iterations`:INT, `clean_angle`:FLOAT, `dirt_angle`:FLOAT, `dirt_only`:BOOLEAN, `normalize`:BOOLEAN |
| ❌ | `paint.vertex_color_from_weight` | Convert active weight into gray scale vertex colors | — |
| ❌ | `paint.vertex_color_hsv` | Adjust vertex color Hue/Saturation/Value | `h`:FLOAT, `s`:FLOAT, `v`:FLOAT |
| ❌ | `paint.vertex_color_invert` | Invert RGB values | — |
| ❌ | `paint.vertex_color_levels` | Adjust levels of vertex colors | `offset`:FLOAT, `gain`:FLOAT |
| ❌ | `paint.vertex_color_set` | Fill the active vertex color layer with the current paint color | `use_alpha`:BOOLEAN |
| ❌ | `paint.vertex_color_smooth` | Smooth colors across vertices | — |
| ❌ | `paint.vertex_paint` | Paint a stroke in the active color attribute layer | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN, `override_location`:BOOLEAN |
| ⚠ | `paint.vertex_paint_toggle` | Toggle the vertex paint mode in 3D view | — |
| ❌ | `paint.visibility_filter` | Edit the visibility of the current mesh | `action`=GROW/SHRINK, `iterations`:INT, `auto_iteration_count`:BOOLEAN |
| ❌ | `paint.visibility_invert` | Invert the visibility of all vertices | — |
| ❌ | `paint.weight_from_bones` | Set the weights of the groups matching the attached armature's bones that have "Deform" op | `type`=AUTOMATIC/ENVELOPES |
| ❌ | `paint.weight_gradient` | Draw a line to apply a weight gradient to selected vertices | `type`=LINEAR/RADIAL, `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT |
| ❌ | `paint.weight_paint` | Paint a stroke in the current vertex group's weights | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN, `override_location`:BOOLEAN |
| ⚠ | `paint.weight_paint_toggle` | Toggle weight paint mode in 3D view | — |
| ❌ | `paint.weight_sample` | Use the mouse to sample a weight in the 3D view | — |
| ❌ | `paint.weight_sample_group` | Select one of the vertex groups available under current mouse position | — |
| ❌ | `paint.weight_set` | Fill the active vertex group with the current paint weight | — |

### `paintcurve` — 8개 (✅ 0 / ⚠ 0 / ❌ 8)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `paintcurve.add_point` | Add New Paint Curve Point | `location`:INT |
| ❌ | `paintcurve.add_point_slide` | Add new curve point and slide it | `PAINTCURVE_OT_add_point`:POINTER, `PAINTCURVE_OT_slide`:POINTER |
| ❌ | `paintcurve.cursor` | Place cursor | — |
| ❌ | `paintcurve.delete_point` | Remove Paint Curve Point | — |
| ❌ | `paintcurve.draw` | Draw curve | — |
| ❌ | `paintcurve.new` | Add new paint curve | — |
| ❌ | `paintcurve.select` | Select a paint curve point | `location`:INT, `toggle`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `paintcurve.slide` | Select and slide paint curve point | `align`:BOOLEAN, `select`:BOOLEAN |

### `palette` — 7개 (✅ 1 / ⚠ 0 / ❌ 6)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `palette.color_add` | Add new color to active palette | — |
| ❌ | `palette.color_delete` | Remove active color from palette | — |
| ❌ | `palette.color_move` | Move the active Color up/down in the list | `type`=UP/DOWN |
| ❌ | `palette.extract_from_image` | Extract all colors used in Image and create a Palette | `threshold`:INT |
| ❌ | `palette.join` | Join Palette Swatches | `palette`:STRING |
| ✅ | `palette.new` | Add new palette | — |
| ❌ | `palette.sort` | Sort Palette Colors | `type`=HSV/SVH/VHS/LUMINANCE |

### `particle` — 37개 (✅ 12 / ⚠ 0 / ❌ 25)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `particle.brush_edit` | Apply a stroke of brush to the particles | `stroke`:COLLECTION, `pen_flip`:BOOLEAN |
| ✅ | `particle.connect_hair` | Connect hair to the emitter mesh | `all`:BOOLEAN |
| ❌ | `particle.copy_particle_systems` | Copy particle systems from the active object to selected objects | `space`=OBJECT/WORLD, `remove_target_particles`:BOOLEAN, `use_active`:BOOLEAN |
| ❌ | `particle.delete` | Delete selected particles or keys | `type`=PARTICLE/KEY |
| ✅ | `particle.disconnect_hair` | Disconnect hair from the emitter mesh | `all`:BOOLEAN |
| ❌ | `particle.duplicate_particle_system` | Duplicate particle system within the active object | `use_duplicate_settings`:BOOLEAN |
| ✅ | `particle.dupliob_copy` | Duplicate the current instance object | — |
| ✅ | `particle.dupliob_move_down` | Move instance object down in the list | — |
| ✅ | `particle.dupliob_move_up` | Move instance object up in the list | — |
| ✅ | `particle.dupliob_refresh` | Refresh list of instance objects and their weights | — |
| ✅ | `particle.dupliob_remove` | Remove the selected instance object | — |
| ❌ | `particle.edited_clear` | Undo all edition performed on the particle system | — |
| ✅ | `particle.hair_dynamics_preset_add` | Add or remove a Hair Dynamics Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ❌ | `particle.hide` | Hide selected particles | `unselected`:BOOLEAN |
| ❌ | `particle.mirror` | Duplicate and mirror the selected particles along the local X axis | — |
| ❌ | `particle.new` | Add new particle settings | — |
| ✅ | `particle.new_target` | Add a new particle target | — |
| ❌ | `particle.particle_edit_toggle` | Toggle particle edit mode | — |
| ❌ | `particle.particle_system_remove_all` | Remove all particle system within the active object | — |
| ❌ | `particle.rekey` | Change the number of keys of selected particles (root and tip keys included) | `keys_number`:INT |
| ❌ | `particle.remove_doubles` | Remove selected particles close enough to others | `threshold`:FLOAT |
| ❌ | `particle.reveal` | Show hidden particles | `select`:BOOLEAN |
| ❌ | `particle.select_all` | (De)select all particles' keys | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `particle.select_less` | Deselect boundary selected keys of each particle | — |
| ❌ | `particle.select_linked` | Select all keys linked to already selected ones | — |
| ❌ | `particle.select_linked_pick` | Select nearest particle from mouse pointer | `deselect`:BOOLEAN, `location`:INT |
| ❌ | `particle.select_more` | Select keys linked to boundary selected keys of each particle | — |
| ❌ | `particle.select_random` | Select a randomly distributed set of hair or points | `ratio`:FLOAT, `seed`:INT, `action`=SELECT/DESELECT, `type`=HAIR/POINTS |
| ❌ | `particle.select_roots` | Select roots of all visible particles | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `particle.select_tips` | Select tips of all visible particles | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `particle.shape_cut` | Cut hair to conform to the set shape object | — |
| ❌ | `particle.subdivide` | Subdivide selected particles segments (adds keys) | — |
| ✅ | `particle.target_move_down` | Move particle target down in the list | — |
| ✅ | `particle.target_move_up` | Move particle target up in the list | — |
| ✅ | `particle.target_remove` | Remove the selected particle target | — |
| ❌ | `particle.unify_length` | Make selected hair the same length | — |
| ❌ | `particle.weight_set` | Set the weight of selected keys | `factor`:FLOAT |

### `pointcloud` — 7개 (✅ 0 / ⚠ 0 / ❌ 7)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `pointcloud.attribute_set` | Set values of the active attribute for selected elements | `value_float`:FLOAT, `value_float_vector_2d`:FLOAT, `value_float_vector_3d`:FLOAT, `value_float_vector_4d`:FLOAT, `value_int`:INT, `value_int_vector_2d`:INT, `value_color`:FLOAT, `value_bool`:BOOLEAN |
| ❌ | `pointcloud.delete` | Remove selected points | — |
| ❌ | `pointcloud.duplicate` | Copy selected points | — |
| ❌ | `pointcloud.duplicate_move` | Make copies of selected elements and move them | `POINTCLOUD_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `pointcloud.select_all` | (De)select all points | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `pointcloud.select_random` | Randomize existing selection or create new random selection | `seed`:INT, `probability`:FLOAT |
| ❌ | `pointcloud.separate` | Separate selected geometry into a new point cloud | — |

### `pose` — 51개 (✅ 5 / ⚠ 0 / ❌ 46)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `pose.armature_apply` | Apply the current pose as the new rest pose | `selected`:BOOLEAN |
| ❌ | `pose.autoside_names` | Automatically renames the selected bones according to which side of the target axis they f | `axis`=XAXIS/YAXIS/ZAXIS |
| ✅ | `pose.blend_to_neighbor` | Blend from current position to previous or next keyframe | `factor`:FLOAT, `prev_frame`:INT, `next_frame`:INT, `channels`=ALL/LOC/ROT/SIZE/BBONE/CUSTOM, `axis_lock`=FREE/X/Y/Z |
| ✅ | `pose.blend_with_rest` | Make the current pose more similar to, or further away from, the rest pose | `factor`:FLOAT, `prev_frame`:INT, `next_frame`:INT, `channels`=ALL/LOC/ROT/SIZE/BBONE/CUSTOM, `axis_lock`=FREE/X/Y/Z |
| ✅ | `pose.breakdown` | Create a suitable breakdown pose on the current frame | `factor`:FLOAT, `prev_frame`:INT, `next_frame`:INT, `channels`=ALL/LOC/ROT/SIZE/BBONE/CUSTOM, `axis_lock`=FREE/X/Y/Z |
| ❌ | `pose.constraint_add` | Add a constraint to the active bone | `type`=CAMERA_SOLVER/FOLLOW_TRACK/OBJECT_SOLVER/COPY_LOCATION/COPY_ROTATION/COPY_SCALE/COPY_TRANSFORMS/LIMIT_DISTANCE/LIMIT_LOCATION/LIMIT_ROTATION/LIMIT_SCALE/MAINTAIN_VOLUME/TRANSFORM/TRANSFORM_CACHE/CLAMP_TO/DAMPED_TRACK/IK/LOCKED_TRACK/SPLINE_IK/STRETCH_TO/TRACK_TO/ACTION/ARMATURE/CHILD_OF/FLOOR/FOLLOW_PATH/GEOMETRY_ATTRIBUTE/PIVOT/SHRINKWRAP |
| ❌ | `pose.constraint_add_with_targets` | Add a constraint to the active bone, with target (where applicable) set to the selected Ob | `type`=CAMERA_SOLVER/FOLLOW_TRACK/OBJECT_SOLVER/COPY_LOCATION/COPY_ROTATION/COPY_SCALE/COPY_TRANSFORMS/LIMIT_DISTANCE/LIMIT_LOCATION/LIMIT_ROTATION/LIMIT_SCALE/MAINTAIN_VOLUME/TRANSFORM/TRANSFORM_CACHE/CLAMP_TO/DAMPED_TRACK/IK/LOCKED_TRACK/SPLINE_IK/STRETCH_TO/TRACK_TO/ACTION/ARMATURE/CHILD_OF/FLOOR/FOLLOW_PATH/GEOMETRY_ATTRIBUTE/PIVOT/SHRINKWRAP |
| ❌ | `pose.constraints_clear` | Clear all constraints from the selected bones | — |
| ❌ | `pose.constraints_copy` | Copy constraints to other selected bones | — |
| ❌ | `pose.copy` | Copy the current pose of the selected bones to the internal clipboard | — |
| ❌ | `pose.flip_names` | Flips (and corrects) the axis suffixes of the names of selected bones | `do_strip_numbers`:BOOLEAN |
| ❌ | `pose.hide` | Tag selected bones to not be visible in Pose Mode | `unselected`:BOOLEAN |
| ❌ | `pose.ik_add` | Add an IK Constraint to the active Bone. The target can be a selected bone or object | `with_targets`:BOOLEAN |
| ❌ | `pose.ik_clear` | Remove all IK Constraints from selected bones | — |
| ❌ | `pose.loc_clear` | Reset locations of selected bones to their default values | — |
| ❌ | `pose.paste` | Paste the stored pose on to the current pose | `flipped`:BOOLEAN, `selected_mask`:BOOLEAN |
| ❌ | `pose.paths_calculate` | Calculate paths for the selected bones | `display_type`=CURRENT_FRAME/RANGE, `range`=KEYS_ALL/KEYS_SELECTED/SCENE/MANUAL, `bake_location`=HEADS/TAILS |
| ❌ | `pose.paths_clear` | (undocumented operator) | `only_selected`:BOOLEAN |
| ❌ | `pose.paths_range_update` | Update frame range for motion paths from the Scene's current frame range | — |
| ❌ | `pose.paths_update` | Recalculate paths for bones that already have them | — |
| ❌ | `pose.propagate` | Copy selected aspects of the current pose to subsequent poses already keyframed | `mode`=NEXT_KEY/LAST_KEY/BEFORE_FRAME/BEFORE_END/SELECTED_KEYS/SELECTED_MARKERS, `end_frame`:FLOAT |
| ✅ | `pose.push` | Exaggerate the current pose in regards to the breakdown pose | `factor`:FLOAT, `prev_frame`:INT, `next_frame`:INT, `channels`=ALL/LOC/ROT/SIZE/BBONE/CUSTOM, `axis_lock`=FREE/X/Y/Z |
| ❌ | `pose.quaternions_flip` | Flip quaternion values to achieve desired rotations, while maintaining the same orientatio | — |
| ✅ | `pose.relax` | Make the current pose more similar to its breakdown pose | `factor`:FLOAT, `prev_frame`:INT, `next_frame`:INT, `channels`=ALL/LOC/ROT/SIZE/BBONE/CUSTOM, `axis_lock`=FREE/X/Y/Z |
| ❌ | `pose.reveal` | Reveal all bones hidden in Pose Mode | `select`:BOOLEAN |
| ❌ | `pose.rot_clear` | Reset rotations of selected bones to their default values | — |
| ❌ | `pose.rotation_mode_set` | Set the rotation representation used by selected bones | `type`=QUATERNION/XYZ/XZY/YXZ/YZX/ZXY/ZYX/AXIS_ANGLE |
| ❌ | `pose.scale_clear` | Reset scaling of selected bones to their default values | — |
| ❌ | `pose.select_all` | Toggle selection status of all bones | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `pose.select_constraint_target` | Select bones used as targets for the currently selected bones | — |
| ❌ | `pose.select_grouped` | Select all visible bones grouped by similar properties | `extend`:BOOLEAN, `type`=COLLECTION/COLOR/KEYINGSET/CHILDREN/CHILDREN_IMMEDIATE/PARENT/SIBLINGS |
| ❌ | `pose.select_hierarchy` | Select immediate parent/children of selected bones | `direction`=PARENT/CHILD, `extend`:BOOLEAN |
| ❌ | `pose.select_linked` | Select all bones linked by connected parent/child relationships from the current selection | — |
| ❌ | `pose.select_linked_pick` | Select bones linked by connected parent/child relationships under the mouse cursor | `extend`:BOOLEAN |
| ❌ | `pose.select_mirror` | Mirror the bone selection | `only_active`:BOOLEAN, `extend`:BOOLEAN |
| ❌ | `pose.select_parent` | Select bones that are parents of the currently selected bones | — |
| ❌ | `pose.selection_set_add` | Create a new empty Selection Set | — |
| ❌ | `pose.selection_set_add_and_assign` | Create a new Selection Set with the currently selected bones | — |
| ❌ | `pose.selection_set_assign` | Add selected bones to Selection Set | — |
| ❌ | `pose.selection_set_copy` | Copy the selected Selection Set(s) to the clipboard | — |
| ❌ | `pose.selection_set_delete_all` | Remove all Selection Sets from this Armature | — |
| ❌ | `pose.selection_set_deselect` | Remove Selection Set bones from current selection | — |
| ❌ | `pose.selection_set_move` | Move the active Selection Set up/down the list of sets | `direction`=UP/DOWN |
| ❌ | `pose.selection_set_paste` | Add new Selection Set(s) from the clipboard | — |
| ❌ | `pose.selection_set_remove` | Remove a Selection Set from this Armature | — |
| ❌ | `pose.selection_set_remove_bones` | Remove the selected bones from all Selection Sets | — |
| ❌ | `pose.selection_set_select` | Select the bones from this Selection Set | `selection_set_index`:INT |
| ❌ | `pose.selection_set_unassign` | Remove selected bones from Selection Set | — |
| ❌ | `pose.transforms_clear` | Reset location, rotation, and scaling of selected bones to their default values | — |
| ❌ | `pose.user_transforms_clear` | Reset pose bone transforms to keyframed state | `only_selected`:BOOLEAN |
| ❌ | `pose.visual_transform_apply` | Apply final constrained position of pose bones to their transform | — |

### `poselib` — 9개 (✅ 0 / ⚠ 0 / ❌ 9)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `poselib.apply_pose_asset` | Apply the given Pose Action to the rig | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING, `blend_factor`:FLOAT, `flipped`:BOOLEAN |
| ❌ | `poselib.asset_delete` | Delete the selected Pose Asset | — |
| ❌ | `poselib.asset_modify` | Update the selected pose asset in the asset library from the currently selected bones. The | `mode`=ADJUST/REPLACE/ADD/REMOVE |
| ❌ | `poselib.blend_pose_asset` | Blend the given Pose Action to the rig | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING, `blend_factor`:FLOAT, `flipped`:BOOLEAN, `release_confirm`:BOOLEAN |
| ❌ | `poselib.copy_as_asset` | Create a new pose asset on the clipboard, to be pasted into an Asset Browser | — |
| ❌ | `poselib.create_pose_asset` | Create a new asset from the selected bones in the scene | `pose_name`:STRING, `asset_library_reference`=, `catalog_path`:STRING |
| ❌ | `poselib.paste_asset` | Paste the Asset that was previously copied using Copy As Asset | — |
| ❌ | `poselib.pose_asset_select_bones` | Select those bones that are used in this pose | `select`:BOOLEAN, `flipped`:BOOLEAN |
| ❌ | `poselib.restore_previous_action` | Switch back to the previous Action, after creating a pose asset | — |

### `preferences` — 37개 (✅ 30 / ⚠ 0 / ❌ 7)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `preferences.addon_disable` | Turn off this add-on | `module`:STRING |
| ✅ | `preferences.addon_enable` | Turn on this add-on | `module`:STRING |
| ✅ | `preferences.addon_expand` | Display information and preferences for this add-on | `module`:STRING |
| ✅ | `preferences.addon_install` | Install an add-on | `overwrite`:BOOLEAN, `enable_on_install`:BOOLEAN, `target`=, `filepath`:STRING, `filter_folder`:BOOLEAN, `filter_python`:BOOLEAN, `filter_glob`:STRING |
| ✅ | `preferences.addon_refresh` | Scan add-on directories for new modules | — |
| ✅ | `preferences.addon_remove` | Delete the add-on from the file system | `module`:STRING |
| ✅ | `preferences.addon_show` | Show add-on preferences | `module`:STRING |
| ✅ | `preferences.app_template_install` | Install an application template | `overwrite`:BOOLEAN, `filepath`:STRING, `filter_folder`:BOOLEAN, `filter_glob`:STRING |
| ✅ | `preferences.asset_library_add` | Add a directory to be used by the Asset Browser as source of assets | `directory`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `name`:STRING, `remote_url`:STRING, `type`=REMOTE/LOCAL |
| ❌ | `preferences.asset_library_remove` | Remove a path to a .blend file, so the Asset Browser will not attempt to show it anymore | `index`:INT |
| ✅ | `preferences.associate_blend` | Use this installation for .blend files and to display thumbnails | — |
| ✅ | `preferences.autoexec_path_add` | Add path to exclude from auto-execution | — |
| ✅ | `preferences.autoexec_path_remove` | Remove path to exclude from auto-execution | `index`:INT |
| ❌ | `preferences.clear_filter` | Clear the search filter | — |
| ❌ | `preferences.copy_prev` | Copy settings from previous version | — |
| ✅ | `preferences.extension_repo_add` | Add a new repository used to store extensions | `name`:STRING, `remote_url`:STRING, `use_access_token`:BOOLEAN, `access_token`:STRING, `use_sync_on_startup`:BOOLEAN, `use_custom_directory`:BOOLEAN, `custom_directory`:STRING, `type`=REMOTE/LOCAL |
| ✅ | `preferences.extension_repo_remove` | Remove an extension repository | `index`:INT, `remove_files`:BOOLEAN |
| ✅ | `preferences.extension_url_drop` | Handle dropping an extension URL | `url`:STRING |
| ✅ | `preferences.keyconfig_activate` | (undocumented operator) | `filepath`:STRING |
| ✅ | `preferences.keyconfig_export` | Export key configuration to a Python script | `all`:BOOLEAN, `filepath`:STRING, `filter_folder`:BOOLEAN, `filter_text`:BOOLEAN, `filter_python`:BOOLEAN |
| ✅ | `preferences.keyconfig_import` | Import key configuration from a Python script | `filepath`:STRING, `filter_folder`:BOOLEAN, `filter_text`:BOOLEAN, `filter_python`:BOOLEAN, `keep_original`:BOOLEAN |
| ❌ | `preferences.keyconfig_remove` | Remove key config | — |
| ✅ | `preferences.keyconfig_test` | Test key configuration for conflicts | — |
| ✅ | `preferences.keyitem_add` | Add key map item | — |
| ❌ | `preferences.keyitem_remove` | Remove key map item | `item_id`:INT |
| ❌ | `preferences.keyitem_restore` | Restore key map item | `item_id`:INT |
| ✅ | `preferences.keymap_restore` | Restore key map(s) | `all`:BOOLEAN |
| ✅ | `preferences.reset_default_theme` | Reset to the default theme colors | — |
| ✅ | `preferences.script_directory_add` | (undocumented operator) | `directory`:STRING, `filter_folder`:BOOLEAN |
| ✅ | `preferences.script_directory_remove` | (undocumented operator) | `index`:INT |
| ❌ | `preferences.start_filter` | Start entering filter text | — |
| ✅ | `preferences.studiolight_copy_settings` | Copy Studio Light settings to the Studio Light editor | `index`:INT |
| ✅ | `preferences.studiolight_install` | Install a user defined light | `files`:COLLECTION, `directory`:STRING, `filter_folder`:BOOLEAN, `filter_glob`:STRING, `type`=MATCAP/WORLD/STUDIO |
| ✅ | `preferences.studiolight_new` | Save custom studio light from the studio light editor settings | `filename`:STRING |
| ✅ | `preferences.studiolight_uninstall` | Delete Studio Light | `index`:INT |
| ✅ | `preferences.theme_install` | Load and apply a Blender XML theme file | `overwrite`:BOOLEAN, `filepath`:STRING, `filter_folder`:BOOLEAN, `filter_glob`:STRING |
| ✅ | `preferences.unassociate_blend` | Remove this installation's associations with .blend files | — |

### `ptcache` — 7개 (✅ 2 / ⚠ 0 / ❌ 5)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `ptcache.add` | Add new cache | — |
| ❌ | `ptcache.bake` | Bake physics | `bake`:BOOLEAN |
| ✅ | `ptcache.bake_all` | Bake all physics simulations in the current scene | `bake`:BOOLEAN |
| ❌ | `ptcache.bake_from_cache` | Bake from cache | — |
| ❌ | `ptcache.free_bake` | Delete physics bake | — |
| ✅ | `ptcache.free_bake_all` | Delete all baked caches of all objects in the current scene | — |
| ❌ | `ptcache.remove` | Delete current cache | — |

### `render` — 16개 (✅ 15 / ⚠ 0 / ❌ 1)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `render.clear_texture_cache` | Delete Cycles texture cache files from disk | — |
| ✅ | `render.color_management_white_balance_preset_add` | Add or remove a white balance preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.cycles_integrator_preset_add` | Add an Integrator Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.cycles_performance_preset_add` | Add an Performance Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.cycles_sampling_preset_add` | Add a Sampling Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.cycles_viewport_sampling_preset_add` | Add a Viewport Sampling Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.eevee_raytracing_preset_add` | Add or remove an EEVEE ray-tracing preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.generate_texture_cache` | Generate Cycles texture cache files for all images used in shader nodes | `generate_sequences`:BOOLEAN |
| ✅ | `render.opengl` | Take a snapshot of the active viewport | `animation`:BOOLEAN, `render_keyed_only`:BOOLEAN, `sequencer`:BOOLEAN, `write_still`:BOOLEAN, `view_context`:BOOLEAN |
| ✅ | `render.play_rendered_anim` | Play back rendered frames/movies using an external player | — |
| ✅ | `render.preset_add` | Add or remove a Render Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `render.render` | (undocumented operator) | `animation`:BOOLEAN, `write_still`:BOOLEAN, `use_viewport`:BOOLEAN, `use_sequencer_scene`:BOOLEAN, `layer`:STRING, `scene`:STRING, `frame_start`:INT, `frame_end`:INT |
| ✅ | `render.shutter_curve_preset` | Set shutter curve | `shape`=SHARP/SMOOTH/MAX/LINE/ROUND/ROOT |
| ✅ | `render.swap_dimensions` | Flip X and Y resolutions | — |
| ❌ | `render.view_cancel` | Cancel showing the render view | — |
| ✅ | `render.view_show` | Toggle show render view | — |

### `rigidbody` — 13개 (✅ 2 / ⚠ 2 / ❌ 9)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `rigidbody.bake_to_keyframes` | Bake rigid body transformations of selected objects to keyframes | `frame_start`:INT, `frame_end`:INT, `step`:INT |
| ❌ | `rigidbody.connect` | Create rigid body constraints between selected rigid bodies | `con_type`=FIXED/POINT/HINGE/SLIDER/PISTON/GENERIC/GENERIC_SPRING/MOTOR, `pivot_type`=CENTER/ACTIVE/SELECTED, `connection_pattern`=SELECTED_TO_ACTIVE/CHAIN_DISTANCE |
| ✅ | `rigidbody.constraint_add` | Add Rigid Body Constraint to active object | `type`=FIXED/POINT/HINGE/SLIDER/PISTON/GENERIC/GENERIC_SPRING/MOTOR |
| ❌ | `rigidbody.constraint_remove` | Remove Rigid Body Constraint from Object | — |
| ❌ | `rigidbody.mass_calculate` | Automatically calculate mass values for Rigid Body Objects based on volume | `material`=DEFAULT, `density`:FLOAT |
| ⚠ | `rigidbody.object_add` | Add active object as Rigid Body | `type`=ACTIVE/PASSIVE |
| ❌ | `rigidbody.object_remove` | Remove Rigid Body settings from Object | — |
| ❌ | `rigidbody.object_settings_copy` | Copy Rigid Body settings from active object to selected | — |
| ⚠ | `rigidbody.objects_add` | Add selected objects as Rigid Bodies | `type`=ACTIVE/PASSIVE |
| ❌ | `rigidbody.objects_remove` | Remove selected objects from Rigid Body simulation | — |
| ❌ | `rigidbody.shape_change` | Change collision shapes for selected Rigid Body Objects | `type`=BOX/SPHERE/CAPSULE/CYLINDER/CONE/CONVEX_HULL/MESH/COMPOUND |
| ✅ | `rigidbody.world_add` | Add Rigid Body simulation world to the current scene | — |
| ❌ | `rigidbody.world_remove` | Remove Rigid Body simulation world from the current scene | — |

### `scene` — 39개 (✅ 30 / ⚠ 2 / ❌ 7)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `scene.delete` | Delete active scene | — |
| ✅ | `scene.drop_scene_asset` | Import scene and set it as the active one in the window | `session_uid`:INT |
| ⚠ | `scene.freestyle_add_edge_marks_to_keying_set` | Add the data paths to the Freestyle Edge Mark property of selected edges to the active key | — |
| ⚠ | `scene.freestyle_add_face_marks_to_keying_set` | Add the data paths to the Freestyle Face Mark property of selected polygons to the active  | — |
| ✅ | `scene.freestyle_alpha_modifier_add` | Add an alpha transparency modifier to the line style associated with the active lineset | `type`=ALONG_STROKE/CREASE_ANGLE/CURVATURE_3D/DISTANCE_FROM_CAMERA/DISTANCE_FROM_OBJECT/MATERIAL/NOISE/TANGENT |
| ✅ | `scene.freestyle_color_modifier_add` | Add a line color modifier to the line style associated with the active lineset | `type`=ALONG_STROKE/CREASE_ANGLE/CURVATURE_3D/DISTANCE_FROM_CAMERA/DISTANCE_FROM_OBJECT/MATERIAL/NOISE/TANGENT |
| ✅ | `scene.freestyle_fill_range_by_selection` | Fill the Range Min/Max entries by the min/max distance between selected mesh objects and t | `type`=COLOR/ALPHA/THICKNESS, `name`:STRING |
| ✅ | `scene.freestyle_geometry_modifier_add` | Add a stroke geometry modifier to the line style associated with the active lineset | `type`=2D_OFFSET/2D_TRANSFORM/BACKBONE_STRETCHER/BEZIER_CURVE/BLUEPRINT/GUIDING_LINES/PERLIN_NOISE_1D/PERLIN_NOISE_2D/POLYGONIZATION/SAMPLING/SIMPLIFICATION/SINUS_DISPLACEMENT/SPATIAL_NOISE/TIP_REMOVER |
| ✅ | `scene.freestyle_lineset_add` | Add a line set into the list of line sets | — |
| ✅ | `scene.freestyle_lineset_copy` | Copy the active line set to the internal clipboard | — |
| ✅ | `scene.freestyle_lineset_move` | Change the position of the active line set within the list of line sets | `direction`=UP/DOWN |
| ✅ | `scene.freestyle_lineset_paste` | Paste the internal clipboard content to the active line set | — |
| ✅ | `scene.freestyle_lineset_remove` | Remove the active line set from the list of line sets | — |
| ✅ | `scene.freestyle_linestyle_new` | Create a new line style, reusable by multiple line sets | — |
| ✅ | `scene.freestyle_modifier_copy` | Duplicate the modifier within the list of modifiers | — |
| ✅ | `scene.freestyle_modifier_move` | Move the modifier within the list of modifiers | `direction`=UP/DOWN |
| ✅ | `scene.freestyle_modifier_remove` | Remove the modifier from the list of modifiers | — |
| ✅ | `scene.freestyle_module_add` | Add a style module into the list of modules | — |
| ❌ | `scene.freestyle_module_move` | Change the position of the style module within in the list of style modules | `direction`=UP/DOWN |
| ❌ | `scene.freestyle_module_open` | Open a style module file | `filepath`:STRING, `make_internal`:BOOLEAN |
| ❌ | `scene.freestyle_module_remove` | Remove the style module from the stack | — |
| ✅ | `scene.freestyle_stroke_material_create` | Create Freestyle stroke material for testing | — |
| ✅ | `scene.freestyle_thickness_modifier_add` | Add a line thickness modifier to the line style associated with the active lineset | `type`=ALONG_STROKE/CALLIGRAPHY/CREASE_ANGLE/CURVATURE_3D/DISTANCE_FROM_CAMERA/DISTANCE_FROM_OBJECT/MATERIAL/NOISE/TANGENT |
| ✅ | `scene.gltf2_action_filter_refresh` | Refresh list of actions | — |
| ✅ | `scene.gpencil_brush_preset_add` | Add or remove Grease Pencil brush preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `scene.gpencil_material_preset_add` | Add or remove Grease Pencil material preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `scene.new` | Add new scene by type | `type`=NEW/EMPTY/LINK_COPY/FULL_COPY |
| ❌ | `scene.new_sequencer` | Add new scene by type in the sequence editor and assign to active strip | `type`=NEW/EMPTY/LINK_COPY/FULL_COPY |
| ✅ | `scene.new_sequencer_scene` | Add new scene to be used by the sequencer | `type`=NEW/EMPTY/LINK_COPY/FULL_COPY |
| ✅ | `scene.render_view_add` | Add a render view | — |
| ❌ | `scene.render_view_remove` | Remove the selected render view | — |
| ✅ | `scene.view_layer_add` | Add a view layer | `type`=NEW/COPY/EMPTY |
| ✅ | `scene.view_layer_add_aov` | Add a Shader AOV | — |
| ✅ | `scene.view_layer_add_lightgroup` | Add a Light Group | `name`:STRING |
| ✅ | `scene.view_layer_add_used_lightgroups` | Add all used Light Groups | — |
| ❌ | `scene.view_layer_remove` | Remove the selected view layer | — |
| ✅ | `scene.view_layer_remove_aov` | Remove Active AOV | — |
| ✅ | `scene.view_layer_remove_lightgroup` | Remove Active Lightgroup | — |
| ✅ | `scene.view_layer_remove_unused_lightgroups` | Remove all unused Light Groups | — |

### `screen` — 43개 (✅ 23 / ⚠ 0 / ❌ 20)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `screen.actionzone` | Handle area action zones for mouse actions/gestures | `modifier`:INT |
| ✅ | `screen.animation_cancel` | Cancel animation, returning to the original frame | `restore_frame`:BOOLEAN |
| ✅ | `screen.animation_pause` | Pause animation, stopping at the current frame | — |
| ✅ | `screen.animation_play` | Play animation | `reverse`:BOOLEAN, `sync`:BOOLEAN |
| ✅ | `screen.animation_step` | Step through animation by position | — |
| ❌ | `screen.area_close` | Close selected area | — |
| ❌ | `screen.area_dupli` | Duplicate selected area into new window | — |
| ✅ | `screen.area_join` | Join selected areas into new window | `source_xy`:INT, `target_xy`:INT |
| ✅ | `screen.area_move` | Move selected area edges | `x`:INT, `y`:INT, `delta`:INT, `snap`:BOOLEAN |
| ✅ | `screen.area_options` | Operations for splitting and merging | — |
| ✅ | `screen.area_split` | Split selected area into new windows | `direction`=HORIZONTAL/VERTICAL, `factor`:FLOAT, `cursor`:INT |
| ✅ | `screen.area_swap` | Swap selected areas screen positions | `cursor`:INT |
| ✅ | `screen.back_to_previous` | Revert back to the original screen layout, before fullscreen area overlay | — |
| ✅ | `screen.delete` | Delete active screen | — |
| ❌ | `screen.drivers_editor_show` | Show drivers editor in a separate window | — |
| ✅ | `screen.edge_merge` | Merge aligned area edges | `cursor`:INT |
| ✅ | `screen.frame_jump` | Jump to first/last frame in frame range | `end`:BOOLEAN |
| ✅ | `screen.frame_offset` | Move current frame forward/backward by a given number | `delta`:INT |
| ❌ | `screen.header_toggle_menus` | Expand or collapse the header pull-down menus | — |
| ❌ | `screen.info_log_show` | Show info log in a separate window | — |
| ✅ | `screen.keyframe_jump` | Jump to previous/next keyframe | `next`:BOOLEAN |
| ✅ | `screen.marker_jump` | Jump to previous/next marker | `next`:BOOLEAN |
| ✅ | `screen.new` | Add a new screen | — |
| ❌ | `screen.quadview_size` | Resize Quad View areas | — |
| ❌ | `screen.redo_last` | Display parameters for last action performed | — |
| ✅ | `screen.region_blend` | Blend in and out overlapping region | — |
| ✅ | `screen.region_context_menu` | Display region context menu | — |
| ❌ | `screen.region_flip` | Toggle the region's alignment (left/right or top/bottom) | — |
| ❌ | `screen.region_quadview` | Split selected area into camera, front, right, and top views | — |
| ❌ | `screen.region_scale` | Scale selected area | — |
| ❌ | `screen.region_toggle` | Hide or unhide the region | `region_type`=WINDOW/HEADER/CHANNELS/TEMPORARY/UI/TOOLS/TOOL_PROPS/ASSET_SHELF/ASSET_SHELF_HEADER/PREVIEW/HUD/NAVIGATION_BAR/EXECUTE/FOOTER/TOOL_HEADER/XR/SCRUBBING |
| ❌ | `screen.repeat_history` | Display menu for previous actions performed | `index`:INT |
| ❌ | `screen.repeat_last` | Repeat last action | — |
| ❌ | `screen.screen_full_area` | Toggle display selected area as fullscreen/maximized | `use_hide_panels`:BOOLEAN |
| ✅ | `screen.screen_set` | Cycle through available screens | `delta`:INT |
| ❌ | `screen.screenshot` | Capture a picture of the whole Blender window | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `screen.screenshot_area` | Capture a picture of an editor | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `screen.space_context_cycle` | Cycle through the editor context by activating the next/previous one | `direction`=PREV/NEXT |
| ❌ | `screen.space_type_set_or_cycle` | Set the space type or cycle subtype | `space_type`=EMPTY/VIEW_3D/IMAGE_EDITOR/NODE_EDITOR/SEQUENCE_EDITOR/CLIP_EDITOR/DOPESHEET_EDITOR/GRAPH_EDITOR/NLA_EDITOR/TEXT_EDITOR/CONSOLE/INFO/TOPBAR/STATUSBAR/OUTLINER/PROPERTIES/FILE_BROWSER/SPREADSHEET/PREFERENCES |
| ✅ | `screen.spacedata_cleanup` | Remove unused settings for invisible editors | — |
| ✅ | `screen.time_jump` | Jump forward/backward by a given number of frames or seconds | `backward`:BOOLEAN |
| ❌ | `screen.userpref_show` | Edit user preferences and system settings | `section`=INTERFACE/VIEWPORT/LIGHTS/EDITING/ANIMATION/EXTENSIONS/ADDONS/THEMES/ASSETS/INPUT/NAVIGATION/KEYMAP/SYSTEM/SAVE_LOAD/FILE_PATHS/DEVELOPER_TOOLS/EXPERIMENTAL |
| ✅ | `screen.workspace_cycle` | Cycle through workspaces | `direction`=PREV/NEXT |

### `script` — 3개 (✅ 3 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `script.execute_preset` | Load a preset | `filepath`:STRING, `menu_idname`:STRING |
| ✅ | `script.python_file_run` | Run Python file | `filepath`:STRING |
| ✅ | `script.reload` | Reload scripts | — |

### `sculpt` — 39개 (✅ 0 / ⚠ 0 / ❌ 39)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `sculpt.brush_stroke` | Sculpt a stroke into the geometry | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN, `override_location`:BOOLEAN, `ignore_background_click`:BOOLEAN |
| ❌ | `sculpt.cloth_filter` | Applies a cloth simulation deformation to the entire mesh | `start_mouse`:INT, `area_normal_radius`:FLOAT, `strength`:FLOAT, `iteration_count`:INT, `event_history`:COLLECTION, `type`=GRAVITY/INFLATE/EXPAND/PINCH/SCALE, `force_axis`=X/Y/Z, `orientation`=LOCAL/WORLD/VIEW, `cloth_mass`:FLOAT, `cloth_damping`:FLOAT, `use_face_sets`:BOOLEAN, `use_collisions`:BOOLEAN |
| ❌ | `sculpt.color_filter` | Applies a filter to modify the active color attribute | `start_mouse`:INT, `area_normal_radius`:FLOAT, `strength`:FLOAT, `iteration_count`:INT, `event_history`:COLLECTION, `type`=FILL/HUE/SATURATION/VALUE/BRIGHTNESS/CONTRAST/SMOOTH/RED/GREEN/BLUE, `fill_color`:FLOAT, `use_immediate`:BOOLEAN, `use_secondary_color`:BOOLEAN |
| ❌ | `sculpt.detail_flood_fill` | Flood fill the mesh with the selected detail setting | — |
| ❌ | `sculpt.dynamic_topology_toggle` | Dynamic topology alters the mesh topology while sculpting | — |
| ❌ | `sculpt.dyntopo_detail_size_edit` | Modify the detail size of dyntopo interactively | — |
| ❌ | `sculpt.expand` | Generic sculpt expand operator | `target`=MASK/FACE_SETS/COLOR, `falloff_type`=GEODESIC/TOPOLOGY/TOPOLOGY_DIAGONALS/NORMALS/SPHERICAL/BOUNDARY_TOPOLOGY/BOUNDARY_FACE_SET/ACTIVE_FACE_SET, `invert`:BOOLEAN, `use_mask_preserve`:BOOLEAN, `use_falloff_gradient`:BOOLEAN, `use_modify_active`:BOOLEAN, `use_reposition_pivot`:BOOLEAN, `max_geodesic_move_preview`:INT, `use_auto_mask`:BOOLEAN, `normal_falloff_smooth`:INT |
| ❌ | `sculpt.face_set_box_gesture` | Add a face set in a rectangle defined by the cursor | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `use_front_faces_only`:BOOLEAN |
| ❌ | `sculpt.face_set_change_visibility` | Change the visibility of the face sets of the sculpt | `mode`=TOGGLE/SHOW_ACTIVE/HIDE_ACTIVE, `active_face_set`:INT |
| ❌ | `sculpt.face_set_edit` | Edits the current active face set | `active_face_set`:INT, `mode`=GROW/SHRINK/DELETE_GEOMETRY/FAIR_POSITIONS/FAIR_TANGENCY, `strength`:FLOAT, `modify_hidden`:BOOLEAN |
| ❌ | `sculpt.face_set_extract` | Create a new mesh object from the selected face set | `add_boundary_loop`:BOOLEAN, `smooth_iterations`:INT, `apply_shrinkwrap`:BOOLEAN, `add_solidify`:BOOLEAN |
| ❌ | `sculpt.face_set_lasso_gesture` | Add a face set in a shape defined by the cursor | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `use_front_faces_only`:BOOLEAN |
| ❌ | `sculpt.face_set_line_gesture` | Add a face set to one side of a line defined by the cursor | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT, `use_front_faces_only`:BOOLEAN, `use_limit_to_segment`:BOOLEAN |
| ❌ | `sculpt.face_set_polyline_gesture` | Add a face set in a shape defined by the cursor | `path`:COLLECTION, `use_front_faces_only`:BOOLEAN |
| ❌ | `sculpt.face_sets_create` | Create a new face set | `mode`=MASKED/VISIBLE/ALL/SELECTION |
| ❌ | `sculpt.face_sets_init` | Initializes all face sets in the mesh | `mode`=LOOSE_PARTS/MATERIALS/NORMALS/UV_SEAMS/CREASES/BEVEL_WEIGHT/SHARP_EDGES/FACE_SET_BOUNDARIES, `threshold`:FLOAT |
| ❌ | `sculpt.face_sets_randomize_colors` | Generates a new set of random colors to render the face sets in the viewport | — |
| ❌ | `sculpt.mask_by_color` | Creates a mask based on the active color attribute | `contiguous`:BOOLEAN, `invert`:BOOLEAN, `preserve_previous_mask`:BOOLEAN, `threshold`:FLOAT, `location`:INT |
| ❌ | `sculpt.mask_filter` | Applies a filter to modify the current mask | `filter_type`=SMOOTH/SHARPEN/GROW/SHRINK/CONTRAST_INCREASE/CONTRAST_DECREASE, `iterations`:INT, `auto_iteration_count`:BOOLEAN |
| ❌ | `sculpt.mask_from_boundary` | Creates a mask based on the boundaries of the surface | `mix_mode`=MIX/MULTIPLY/DIVIDE/ADD/SUBTRACT, `mix_factor`:FLOAT, `settings_source`=OPERATOR/BRUSH/SCENE, `boundary_mode`=MESH/FACE_SETS, `propagation_steps`:INT |
| ❌ | `sculpt.mask_from_cavity` | Creates a mask based on the curvature of the surface | `mix_mode`=MIX/MULTIPLY/DIVIDE/ADD/SUBTRACT, `mix_factor`:FLOAT, `settings_source`=OPERATOR/BRUSH/SCENE, `factor`:FLOAT, `blur_steps`:INT, `use_curve`:BOOLEAN, `invert`:BOOLEAN |
| ❌ | `sculpt.mask_init` | Creates a new mask for the entire mesh | `mode`=RANDOM_PER_VERTEX/RANDOM_PER_FACE_SET/RANDOM_PER_LOOSE_PART |
| ❌ | `sculpt.mesh_filter` | Applies a filter to modify the current mesh | `start_mouse`:INT, `area_normal_radius`:FLOAT, `strength`:FLOAT, `iteration_count`:INT, `event_history`:COLLECTION, `type`=SMOOTH/SCALE/INFLATE/SPHERE/RANDOM/RELAX/RELAX_FACE_SETS/SURFACE_SMOOTH/SHARPEN/ENHANCE_DETAILS/ERASE_DISPLACEMENT, `deform_axis`=X/Y/Z, `orientation`=LOCAL/WORLD/VIEW, `surface_smooth_shape_preservation`:FLOAT, `surface_smooth_current_vertex`:FLOAT, `sharpen_smooth_ratio`:FLOAT, `sharpen_intensify_detail_strength`:FLOAT, `sharpen_curvature_smooth_iterations`:INT |
| ❌ | `sculpt.optimize` | Recalculate the sculpt BVH to improve performance | — |
| ❌ | `sculpt.paint_mask_extract` | Create a new mesh object from the current paint mask | `mask_threshold`:FLOAT, `add_boundary_loop`:BOOLEAN, `smooth_iterations`:INT, `apply_shrinkwrap`:BOOLEAN, `add_solidify`:BOOLEAN |
| ❌ | `sculpt.paint_mask_slice` | Slices the paint mask from the mesh | `mask_threshold`:FLOAT, `fill_holes`:BOOLEAN, `new_object`:BOOLEAN |
| ❌ | `sculpt.project_line_gesture` | Project the geometry onto a plane defined by a line | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT, `use_front_faces_only`:BOOLEAN, `use_limit_to_segment`:BOOLEAN |
| ❌ | `sculpt.sample_detail_size` | Sample the mesh detail on clicked point | `location`:INT, `mode`=DYNTOPO/VOXEL |
| ❌ | `sculpt.sculptmode_toggle` | Toggle sculpt mode in 3D view | — |
| ❌ | `sculpt.set_persistent_base` | Reset the copy of the mesh that is being sculpted on | — |
| ❌ | `sculpt.set_pivot_position` | Sets the sculpt transform pivot position | `mode`=ORIGIN/UNMASKED/BORDER/ACTIVE/SURFACE, `mouse_x`:FLOAT, `mouse_y`:FLOAT |
| ❌ | `sculpt.symmetrize` | Symmetrize the topology modifications | `merge_tolerance`:FLOAT |
| ❌ | `sculpt.trim_box_gesture` | Execute a boolean operation on the mesh and a rectangle defined by the cursor | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `use_front_faces_only`:BOOLEAN, `location`:INT, `trim_mode`=DIFFERENCE/UNION/JOIN, `use_cursor_depth`:BOOLEAN, `trim_orientation`=VIEW/SURFACE, `trim_extrude_mode`=PROJECT/FIXED, `trim_solver`=EXACT/FLOAT/MANIFOLD |
| ❌ | `sculpt.trim_lasso_gesture` | Execute a boolean operation on the mesh and a shape defined by the cursor | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `use_front_faces_only`:BOOLEAN, `location`:INT, `trim_mode`=DIFFERENCE/UNION/JOIN, `use_cursor_depth`:BOOLEAN, `trim_orientation`=VIEW/SURFACE, `trim_extrude_mode`=PROJECT/FIXED, `trim_solver`=EXACT/FLOAT/MANIFOLD |
| ❌ | `sculpt.trim_line_gesture` | Remove a portion of the mesh on one side of a line | `xstart`:INT, `xend`:INT, `ystart`:INT, `yend`:INT, `flip`:BOOLEAN, `cursor`:INT, `use_front_faces_only`:BOOLEAN, `use_limit_to_segment`:BOOLEAN, `location`:INT, `trim_mode`=DIFFERENCE/UNION/JOIN, `use_cursor_depth`:BOOLEAN, `trim_orientation`=VIEW/SURFACE, `trim_extrude_mode`=PROJECT/FIXED, `trim_solver`=EXACT/FLOAT/MANIFOLD |
| ❌ | `sculpt.trim_polyline_gesture` | Execute a boolean operation on the mesh and a polygonal shape defined by the cursor | `path`:COLLECTION, `use_front_faces_only`:BOOLEAN, `location`:INT, `trim_mode`=DIFFERENCE/UNION/JOIN, `use_cursor_depth`:BOOLEAN, `trim_orientation`=VIEW/SURFACE, `trim_extrude_mode`=PROJECT/FIXED, `trim_solver`=EXACT/FLOAT/MANIFOLD |
| ❌ | `sculpt.uv_sculpt_grab` | Grab UVs | `use_invert`:BOOLEAN |
| ❌ | `sculpt.uv_sculpt_pinch` | Pinch UVs | `use_invert`:BOOLEAN |
| ❌ | `sculpt.uv_sculpt_relax` | Relax UVs | `use_invert`:BOOLEAN, `relax_method`=LAPLACIAN/HC/COTAN |

### `sculpt_curves` — 4개 (✅ 1 / ⚠ 0 / ❌ 3)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `sculpt_curves.brush_stroke` | Sculpt curves using a brush | `stroke`:COLLECTION, `mode`=NORMAL/INVERT, `brush_toggle`=None/SMOOTH/ERASE/MASK, `pen_flip`:BOOLEAN |
| ❌ | `sculpt_curves.min_distance_edit` | Change the minimum distance used by the density brush | — |
| ❌ | `sculpt_curves.select_grow` | Select curves which are close to curves that are selected already | `distance`:FLOAT |
| ❌ | `sculpt_curves.select_random` | Randomizes existing selection or create new random selection | `seed`:INT, `partial`:BOOLEAN, `probability`:FLOAT, `min`:FLOAT, `constant_per_curve`:BOOLEAN |

### `sequencer` — 111개 (✅ 1 / ⚠ 0 / ❌ 110)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `sequencer.add_scene_strip_from_scene_asset` | Add a strip using a duplicate of this scene asset as the source | `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING |
| ❌ | `sequencer.box_blade` | Draw a box around the parts of strips you want to cut away | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB, `type`=SOFT/HARD, `ignore_selection`:BOOLEAN, `ignore_connections`:BOOLEAN, `remove_gaps`:BOOLEAN |
| ❌ | `sequencer.change_effect_type` | Replace effect strip with another that takes the same number of inputs | `type`=CROSS/ADD/SUBTRACT/ALPHA_OVER/ALPHA_UNDER/GAMMA_CROSS/MULTIPLY/WIPE/GLOW/COLOR/SPEED/MULTICAM/ADJUSTMENT/GAUSSIAN_BLUR/TEXT/COLORMIX/COMPOSITOR |
| ❌ | `sequencer.change_path` | (undocumented operator) | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `use_sequence_detection`:BOOLEAN, `use_placeholders`:BOOLEAN |
| ❌ | `sequencer.change_scene` | Change Scene assigned to Strip | `scene`= |
| ❌ | `sequencer.connect` | Link selected strips together for simplified group selection | `toggle`:BOOLEAN |
| ❌ | `sequencer.copy` | Copy the selected strips to the internal clipboard | — |
| ❌ | `sequencer.crossfade_sounds` | Do cross-fading volume animation of two selected sound strips | — |
| ❌ | `sequencer.cursor_set` | Set 2D cursor location | `location`:FLOAT |
| ❌ | `sequencer.deinterlace_selected_movies` | Deinterlace all selected movie sources | — |
| ❌ | `sequencer.delete` | Delete selected strips from the sequencer | `delete_data`:BOOLEAN |
| ❌ | `sequencer.disconnect` | Unlink selected strips so that they can be selected individually | — |
| ❌ | `sequencer.duplicate` | Duplicate the selected strips | `linked`:BOOLEAN |
| ❌ | `sequencer.duplicate_move` | Duplicate selected strips and move them | `SEQUENCER_OT_duplicate`:POINTER, `TRANSFORM_OT_seq_slide`:POINTER |
| ❌ | `sequencer.duplicate_move_linked` | Duplicate selected strips, but not their data, and move them | `SEQUENCER_OT_duplicate`:POINTER, `TRANSFORM_OT_seq_slide`:POINTER |
| ❌ | `sequencer.effect_strip_add` | Add an effect to the sequencer, most are applied on top of existing strips | `type`=CROSS/ADD/SUBTRACT/ALPHA_OVER/ALPHA_UNDER/GAMMA_CROSS/MULTIPLY/WIPE/GLOW/COLOR/SPEED/MULTICAM/ADJUSTMENT/GAUSSIAN_BLUR/TEXT/COLORMIX/COMPOSITOR, `move_strips`:BOOLEAN, `frame_start`:INT, `length`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `width`:INT, `height`:INT, `color`:FLOAT |
| ❌ | `sequencer.enable_proxies` | Enable selected proxies on all selected Movie and Image strips | `proxy_25`:BOOLEAN, `proxy_50`:BOOLEAN, `proxy_75`:BOOLEAN, `proxy_100`:BOOLEAN, `overwrite`:BOOLEAN |
| ❌ | `sequencer.export_subtitles` | Export .srt file containing text strips | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `sequencer.fades_add` | Adds or updates a fade animation for either visual or audio strips | `duration_seconds`:FLOAT, `type`=IN_OUT/IN/OUT/CURSOR_FROM/CURSOR_TO |
| ❌ | `sequencer.fades_clear` | Removes fade animation from selected strips | — |
| ❌ | `sequencer.gap_insert` | Insert gap at current frame to first strips at the right, independent of selection or lock | `frames`:INT |
| ❌ | `sequencer.gap_remove` | Remove gap at current frame to first strip at the right, independent of selection or locke | `all`:BOOLEAN |
| ❌ | `sequencer.image_strip_add` | Add an image or image sequence to the sequencer | `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG, `move_strips`:BOOLEAN, `frame_start`:INT, `length`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `fit_method`=FIT/FILL/STRETCH/ORIGINAL, `set_view_transform`:BOOLEAN, `image_import_type`=DETECT/SEQUENCE/INDIVIDUAL, `use_sequence_detection`:BOOLEAN, `use_placeholders`:BOOLEAN |
| ❌ | `sequencer.images_separate` | On image sequence strips, it returns a strip for each image | `length`:INT |
| ❌ | `sequencer.lock` | Lock strips so they cannot be transformed | — |
| ❌ | `sequencer.mask_strip_add` | Add a mask strip to the sequencer | `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `mask`= |
| ❌ | `sequencer.meta_make` | Group selected strips into a meta-strip | — |
| ❌ | `sequencer.meta_separate` | Put the contents of a meta-strip back in the sequencer | — |
| ❌ | `sequencer.meta_toggle` | Toggle a meta-strip (to edit enclosed strips) | — |
| ❌ | `sequencer.movie_strip_add` | Add a movie strip to the sequencer | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG, `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `fit_method`=FIT/FILL/STRETCH/ORIGINAL, `set_view_transform`:BOOLEAN, `adjust_playback_rate`:BOOLEAN, `sound`:BOOLEAN, `use_framerate`:BOOLEAN |
| ❌ | `sequencer.movieclip_strip_add` | Add a movieclip strip to the sequencer | `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `clip`= |
| ❌ | `sequencer.mute` | Mute (un)selected strips | `unselected`:BOOLEAN |
| ❌ | `sequencer.offset_clear` | Clear strip in/out offsets from the start and end of content | — |
| ❌ | `sequencer.paste` | Paste strips from the internal clipboard | `keep_offset`:BOOLEAN, `x`:INT, `y`:INT |
| ❌ | `sequencer.preview_duplicate_move` | Duplicate selected strips and move them | `SEQUENCER_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `sequencer.preview_duplicate_move_linked` | Duplicate selected strips, but not their data, and move them | `SEQUENCER_OT_duplicate`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `sequencer.reassign_inputs` | Reassign the inputs for the effect strip | — |
| ❌ | `sequencer.rebuild_proxy` | Rebuild all selected proxies | — |
| ❌ | `sequencer.refresh_all` | Refresh the sequencer editor | — |
| ❌ | `sequencer.reload` | Reload strips in the sequencer | `adjust_length`:BOOLEAN |
| ❌ | `sequencer.rename_channel` | (undocumented operator) | — |
| ❌ | `sequencer.rendersize` | Set render size and aspect from active strip | — |
| ❌ | `sequencer.retiming_add_freeze_frame_slide` | Add freeze frame and move it | `SEQUENCER_OT_retiming_freeze_frame_add`:POINTER, `TRANSFORM_OT_seq_slide`:POINTER |
| ❌ | `sequencer.retiming_add_transition_slide` | Add smooth transition between 2 retimed segments and change its duration | `SEQUENCER_OT_retiming_transition_add`:POINTER, `TRANSFORM_OT_seq_slide`:POINTER |
| ❌ | `sequencer.retiming_freeze_frame_add` | Add freeze frame | `duration`:INT |
| ❌ | `sequencer.retiming_key_add` | Add retiming Key | `timeline_frame`:INT |
| ❌ | `sequencer.retiming_key_delete` | Delete selected retiming keys from the sequencer | — |
| ❌ | `sequencer.retiming_reset` | Reset strip retiming | — |
| ❌ | `sequencer.retiming_segment_speed_set` | Set speed of retimed segment | `speed`:FLOAT |
| ❌ | `sequencer.retiming_show` | Show retiming keys in selected strips | — |
| ❌ | `sequencer.retiming_transition_add` | Add smooth transition between 2 retimed segments | `duration`:INT |
| ❌ | `sequencer.sample` | Use mouse to sample color in current frame | `size`:INT |
| ❌ | `sequencer.scene_frame_range_update` | Update frame range of scene strip | — |
| ❌ | `sequencer.scene_strip_add` | Add a strip re-using this scene as the source | `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `scene`= |
| ❌ | `sequencer.scene_strip_add_new` | Add a strip using a new scene as the source | `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `type`=NEW/EMPTY/LINK_COPY/FULL_COPY |
| ❌ | `sequencer.select` | Select a strip (last selected becomes the "active strip") | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `center`:BOOLEAN, `linked_handle`:BOOLEAN, `linked_time`:BOOLEAN, `side_of_frame`:BOOLEAN, `ignore_connections`:BOOLEAN |
| ❌ | `sequencer.select_all` | Select or deselect all strips | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `sequencer.select_box` | Select strips using box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB, `tweak`:BOOLEAN, `include_handles`:BOOLEAN, `ignore_connections`:BOOLEAN |
| ❌ | `sequencer.select_circle` | Select strips using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB, `ignore_connections`:BOOLEAN |
| ❌ | `sequencer.select_grouped` | Select all strips grouped by various properties | `type`=TYPE/TYPE_BASIC/TYPE_EFFECT/DATA/EFFECT/EFFECT_LINK/OVERLAP, `extend`:BOOLEAN, `use_active_channel`:BOOLEAN |
| ❌ | `sequencer.select_handle` | Select strip handle | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `ignore_connections`:BOOLEAN |
| ❌ | `sequencer.select_handles` | Select gizmo handles on the sides of the selected strip | `side`=LEFT/RIGHT/BOTH/LEFT_NEIGHBOR/RIGHT_NEIGHBOR/BOTH_NEIGHBORS |
| ❌ | `sequencer.select_lasso` | Select strips using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB |
| ❌ | `sequencer.select_less` | Shrink the current selection of adjacent selected strips | — |
| ❌ | `sequencer.select_linked` | Select all strips adjacent to the current selection | — |
| ❌ | `sequencer.select_linked_pick` | Select a chain of linked strips nearest to the mouse pointer | `extend`:BOOLEAN |
| ❌ | `sequencer.select_more` | Select more strips adjacent to the current selection | — |
| ❌ | `sequencer.select_side` | Select strips on the nominated side of the selected strips | `side`=MOUSE/LEFT/RIGHT/BOTH/NO_CHANGE |
| ❌ | `sequencer.select_side_of_frame` | Select strips relative to the current frame | `extend`:BOOLEAN, `side`=LEFT/RIGHT/CURRENT |
| ❌ | `sequencer.set_range_to_strips` | Set the frame range to the selected strips start and end | `preview`:BOOLEAN |
| ❌ | `sequencer.slip` | Slip the contents of selected strips | `offset`:FLOAT, `slip_keyframes`:BOOLEAN, `use_cursor_position`:BOOLEAN, `ignore_connections`:BOOLEAN |
| ❌ | `sequencer.snap` | Snap strips to the current frame, using the active (or closest) strip as the anchor, and t | `frame`:INT, `side`=LEFT/RIGHT, `keep_offset`:BOOLEAN |
| ❌ | `sequencer.sound_strip_add` | Add a sound strip to the sequencer | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG, `move_strips`:BOOLEAN, `frame_start`:INT, `channel`:INT, `replace_sel`:BOOLEAN, `overlap`:BOOLEAN, `overlap_shuffle_override`:BOOLEAN, `skip_locked_or_muted_channels`:BOOLEAN, `cache`:BOOLEAN, `mono`:BOOLEAN |
| ❌ | `sequencer.split` | Split the selected strips in two | `frame`:INT, `channel`:INT, `type`=SOFT/HARD, `use_cursor_position`:BOOLEAN, `side`=MOUSE/LEFT/RIGHT/BOTH/NO_CHANGE, `ignore_selection`:BOOLEAN, `ignore_connections`:BOOLEAN |
| ❌ | `sequencer.split_multicam` | Split multicam strip and select camera | `camera`:INT |
| ❌ | `sequencer.strip_color_tag_set` | Set a color tag for the selected strips | `color`=NONE/COLOR_01/COLOR_02/COLOR_03/COLOR_04/COLOR_05/COLOR_06/COLOR_07/COLOR_08/COLOR_09 |
| ❌ | `sequencer.strip_jump` | Move playhead to the next or previous edit point, which may be a strip handle or its cente | `next`:BOOLEAN, `center`:BOOLEAN |
| ❌ | `sequencer.strip_modifier_add` | Add a modifier to the strip | `type`= |
| ❌ | `sequencer.strip_modifier_add_node_group` | Add a modifier to the strip | `asset_library_type`=ALL/LOCAL/ESSENTIALS/ONLINE_ESSENTIALS/CUSTOM, `asset_library_identifier`:STRING, `relative_asset_identifier`:STRING, `session_uid`:INT |
| ❌ | `sequencer.strip_modifier_copy` | Copy modifiers of the active strip to all selected strips | `type`=REPLACE/APPEND, `modifier`:STRING |
| ❌ | `sequencer.strip_modifier_duplicate` | Duplicate (active) modifier of the active strip | `modifier`:STRING |
| ❌ | `sequencer.strip_modifier_equalizer_redefine` | Redefine equalizer graphs | `graphs`=SIMPLE/DOUBLE/TRIPLE, `name`:STRING |
| ❌ | `sequencer.strip_modifier_move` | Move modifier up and down in the stack | `name`:STRING, `direction`=UP/DOWN |
| ❌ | `sequencer.strip_modifier_move_to_index` | Change the strip modifier's index in the stack so it evaluates after the set number of oth | `modifier`:STRING, `index`:INT |
| ❌ | `sequencer.strip_modifier_remove` | Remove a modifier from the strip | `name`:STRING |
| ❌ | `sequencer.strip_modifier_set_active` | Activate the strip modifier to use as the context | `modifier`:STRING |
| ❌ | `sequencer.strip_transform_clear` | Reset image transformation to default value | `property`=POSITION/SCALE/ROTATION/ALL |
| ❌ | `sequencer.strip_transform_fit` | (undocumented operator) | `fit_method`=FIT/FILL/STRETCH/ORIGINAL |
| ❌ | `sequencer.swap` | Swap active strip with strip to the right or left | `side`=LEFT/RIGHT |
| ❌ | `sequencer.swap_data` | Swap 2 sequencer strips | — |
| ❌ | `sequencer.swap_inputs` | Swap the two inputs of the effect strip | — |
| ❌ | `sequencer.text_cursor_move` | Move cursor in text | `type`=LINE_BEGIN/LINE_END/TEXT_BEGIN/TEXT_END/PREVIOUS_CHARACTER/NEXT_CHARACTER/PREVIOUS_WORD/NEXT_WORD/PREVIOUS_LINE/NEXT_LINE, `select_text`:BOOLEAN |
| ❌ | `sequencer.text_cursor_set` | Set cursor position in text | `select_text`:BOOLEAN |
| ❌ | `sequencer.text_delete` | Delete text at cursor position | `type`=NEXT_OR_SELECTION/PREVIOUS_OR_SELECTION |
| ❌ | `sequencer.text_deselect_all` | Deselect all characters | — |
| ❌ | `sequencer.text_edit_copy` | Copy text to clipboard | — |
| ❌ | `sequencer.text_edit_cut` | Cut text to clipboard | — |
| ❌ | `sequencer.text_edit_mode_toggle` | Toggle text editing | — |
| ❌ | `sequencer.text_edit_paste` | Paste text from clipboard | — |
| ❌ | `sequencer.text_insert` | Insert text at cursor position | `string`:STRING |
| ❌ | `sequencer.text_line_break` | Insert line break at cursor position | — |
| ❌ | `sequencer.text_select_all` | Select all characters | — |
| ✅ | `sequencer.text_strip_style_preset_add` | Add or remove a text strip style and layout preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ❌ | `sequencer.unlock` | Unlock strips so they can be transformed | — |
| ❌ | `sequencer.unmute` | Unmute (un)selected strips | `unselected`:BOOLEAN |
| ❌ | `sequencer.view_all` | View all the strips in the sequencer | — |
| ❌ | `sequencer.view_all_preview` | Zoom preview to fit in the area | — |
| ❌ | `sequencer.view_frame` | Move the view to the current frame | — |
| ❌ | `sequencer.view_ghost_border` | Set the boundaries of the border used for offset view | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `sequencer.view_selected` | Zoom the sequencer on the selected strips | — |
| ❌ | `sequencer.view_zoom_ratio` | Change zoom ratio of sequencer preview | `ratio`:FLOAT |

### `sound` — 7개 (✅ 5 / ⚠ 0 / ❌ 2)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `sound.bake_animation` | Update the audio animation cache | — |
| ✅ | `sound.mixdown` | Mix the scene's audio to a sound file | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `accuracy`:INT, `container`=AAC/AC3/FLAC/MATROSKA/MP2/MP3/OGG/WAV, `codec`=AAC/AC3/FLAC/MP2/MP3/PCM/VORBIS, `channels`=MONO/STEREO/STEREO_LFE/SURROUND4/SURROUND5/SURROUND51/SURROUND61/SURROUND71, `format`=U8/S16/S24/S32/F32/F64, `mixrate`:INT, `bitrate`:INT, `split_channels`:BOOLEAN |
| ✅ | `sound.open` | Load a sound file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `cache`:BOOLEAN, `mono`:BOOLEAN |
| ✅ | `sound.open_mono` | Load a sound file as mono | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `show_multiview`:BOOLEAN, `use_multiview`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `cache`:BOOLEAN, `mono`:BOOLEAN |
| ❌ | `sound.pack` | Pack the sound into the current blend file | — |
| ❌ | `sound.unpack` | Unpack the sound to the samples filename | `method`=REMOVE/USE_LOCAL/WRITE_LOCAL/USE_ORIGINAL/WRITE_ORIGINAL, `id`:STRING |
| ✅ | `sound.update_animation_flags` | Update animation flags | — |

### `spreadsheet` — 7개 (✅ 0 / ⚠ 0 / ❌ 7)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `spreadsheet.add_row_filter_rule` | Add a filter to remove rows from the displayed data | — |
| ❌ | `spreadsheet.change_spreadsheet_data_source` | Change visible data source in the spreadsheet | `component_type`:INT, `attribute_domain_type`:INT |
| ❌ | `spreadsheet.fit_column` | Resize a spreadsheet column to the width of the data | — |
| ❌ | `spreadsheet.remove_row_filter_rule` | Remove a row filter from the rules | `index`:INT |
| ❌ | `spreadsheet.reorder_columns` | Change the order of columns | — |
| ❌ | `spreadsheet.resize_column` | Resize a spreadsheet column | — |
| ❌ | `spreadsheet.toggle_pin` | Turn on or off pinning | — |

### `surface` — 6개 (✅ 6 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `surface.primitive_nurbs_surface_circle_add` | Construct a NURBS surface circle | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `surface.primitive_nurbs_surface_curve_add` | Construct a NURBS surface curve | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `surface.primitive_nurbs_surface_cylinder_add` | Construct a NURBS surface cylinder | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `surface.primitive_nurbs_surface_sphere_add` | Construct a NURBS surface sphere | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `surface.primitive_nurbs_surface_surface_add` | Construct a NURBS surface patch | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |
| ✅ | `surface.primitive_nurbs_surface_torus_add` | Construct a NURBS surface torus | `radius`:FLOAT, `enter_editmode`:BOOLEAN, `align`=WORLD/VIEW/CURSOR, `location`:FLOAT, `rotation`:FLOAT, `scale`:FLOAT |

### `text` — 43개 (✅ 3 / ⚠ 0 / ❌ 40)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `text.autocomplete` | Show a list of used text in the open document | — |
| ❌ | `text.comment_toggle` | (undocumented operator) | `type`=TOGGLE/COMMENT/UNCOMMENT |
| ❌ | `text.convert_whitespace` | Convert whitespaces by type | `type`=SPACES/TABS |
| ❌ | `text.copy` | Copy selected text to clipboard | — |
| ❌ | `text.cursor_set` | Set cursor position | `x`:INT, `y`:INT |
| ❌ | `text.cut` | Cut selected text to clipboard | — |
| ❌ | `text.delete` | Delete text by cursor position | `type`=NEXT_CHARACTER/PREVIOUS_CHARACTER/NEXT_WORD/PREVIOUS_WORD |
| ❌ | `text.duplicate_line` | Duplicate the current line | — |
| ❌ | `text.find` | Find specified text | — |
| ❌ | `text.find_set_selected` | Find specified text and set as selected | — |
| ❌ | `text.indent` | Indent selected text | — |
| ❌ | `text.indent_or_autocomplete` | Indent selected text or autocomplete | — |
| ❌ | `text.insert` | Insert text at cursor position | `text`:STRING |
| ❌ | `text.jump` | Jump cursor to line | `line`:INT |
| ✅ | `text.jump_to_file_at_point` | Jump to a file for the text editor | `filepath`:STRING, `line`:INT, `column`:INT |
| ❌ | `text.line_break` | Insert line break at cursor position | — |
| ❌ | `text.line_number` | The current line number | — |
| ❌ | `text.make_internal` | Make active text file internal | — |
| ❌ | `text.move` | Move cursor to position type | `type`=LINE_BEGIN/LINE_END/FILE_TOP/FILE_BOTTOM/PREVIOUS_CHARACTER/NEXT_CHARACTER/PREVIOUS_WORD/NEXT_WORD/PREVIOUS_LINE/NEXT_LINE/PREVIOUS_PAGE/NEXT_PAGE |
| ❌ | `text.move_lines` | Move the currently selected line(s) up/down | `direction`=UP/DOWN |
| ❌ | `text.move_select` | Move the cursor while selecting | `type`=LINE_BEGIN/LINE_END/FILE_TOP/FILE_BOTTOM/PREVIOUS_CHARACTER/NEXT_CHARACTER/PREVIOUS_WORD/NEXT_WORD/PREVIOUS_LINE/NEXT_LINE/PREVIOUS_PAGE/NEXT_PAGE |
| ✅ | `text.new` | Create a new text data-block | — |
| ✅ | `text.open` | Open a new text data-block | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=DEFAULT/FILE_SORT_ALPHA/FILE_SORT_EXTENSION/FILE_SORT_TIME/FILE_SORT_SIZE/ASSET_CATALOG, `internal`:BOOLEAN |
| ❌ | `text.overwrite_toggle` | Toggle overwrite while typing | — |
| ❌ | `text.paste` | Paste text from clipboard | `selection`:BOOLEAN |
| ❌ | `text.reload` | Reload active text data-block from its file | — |
| ❌ | `text.replace` | Replace text with the specified text | `all`:BOOLEAN |
| ❌ | `text.replace_set_selected` | Replace text with specified text and set as selected | — |
| ❌ | `text.resolve_conflict` | When external text is out of sync, resolve the conflict | `resolution`=IGNORE/RELOAD/SAVE/MAKE_INTERNAL |
| ❌ | `text.run_script` | Run active script | — |
| ❌ | `text.save` | Save active text data-block | — |
| ❌ | `text.save_as` | Save active text file with options | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ❌ | `text.scroll` | (undocumented operator) | `lines`:INT |
| ❌ | `text.scroll_bar` | (undocumented operator) | `lines`:INT |
| ❌ | `text.select_all` | Select all text | — |
| ❌ | `text.select_line` | Select text by line | — |
| ❌ | `text.select_word` | Select word under cursor | — |
| ❌ | `text.selection_set` | Set text selection | — |
| ❌ | `text.start_find` | Start searching text | — |
| ❌ | `text.to_3d_object` | Create 3D text object from active text data-block | `split_lines`:BOOLEAN |
| ❌ | `text.unindent` | Unindent selected text | — |
| ❌ | `text.unlink` | Unlink active text data-block | — |
| ❌ | `text.update_shader` | Update users of this shader, such as custom cameras and script nodes, with its new sockets | — |

### `text_editor` — 1개 (✅ 1 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `text_editor.preset_add` | Add or remove a Text Editor Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |

### `texture` — 4개 (✅ 3 / ⚠ 0 / ❌ 1)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `texture.new` | Add a new texture | — |
| ❌ | `texture.slot_copy` | Copy the material texture settings and nodes | — |
| ✅ | `texture.slot_move` | Move texture slots up and down | `type`=UP/DOWN |
| ✅ | `texture.slot_paste` | Paste the texture settings and nodes | — |

### `transform` — 27개 (✅ 9 / ⚠ 0 / ❌ 18)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `transform.bbone_resize` | Scale selected bendy bones display size | `value`:FLOAT, `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.bend` | Bend selected items between the 3D cursor and the mouse | `value`:FLOAT, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `gpencil_strokes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.create_orientation` | Create transformation orientation from selection | `name`:STRING, `use_view`:BOOLEAN, `use`:BOOLEAN, `overwrite`:BOOLEAN |
| ❌ | `transform.delete_orientation` | Delete transformation orientation | — |
| ❌ | `transform.edge_bevelweight` | Change the bevel weight of edges | `value`:FLOAT, `snap`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.edge_crease` | Change the crease of edges | `value`:FLOAT, `snap`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.edge_slide` | Slide an edge loop along a mesh | `value`:FLOAT, `single_side`:BOOLEAN, `use_even`:BOOLEAN, `flipped`:BOOLEAN, `use_clamp`:BOOLEAN, `mirror`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `correct_uv`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.from_gizmo` | Transform selected items by mode type | — |
| ✅ | `transform.mirror` | Mirror selected items around one or more axes | `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `constraint_axis`:BOOLEAN, `gpencil_strokes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ✅ | `transform.push_pull` | Push/Pull selected items | `value`:FLOAT, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ✅ | `transform.resize` | Scale (resize) selected items | `value`:FLOAT, `mouse_dir_constraint`:FLOAT, `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `gpencil_strokes`:BOOLEAN, `texture_space`:BOOLEAN, `remove_on_cancel`:BOOLEAN, `use_duplicated_keyframes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ✅ | `transform.rotate` | Rotate selected items | `value`:FLOAT, `orient_axis`=X/Y/Z, `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `gpencil_strokes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.rotate_normal` | Rotate custom normal of selected items | `value`:FLOAT, `orient_axis`=X/Y/Z, `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.select_orientation` | Select transformation orientation | `orientation`= |
| ❌ | `transform.seq_slide` | Slide a sequence strip in time | `value`:FLOAT, `use_restore_handle_selection`:BOOLEAN, `snap`:BOOLEAN, `texture_space`:BOOLEAN, `remove_on_cancel`:BOOLEAN, `use_duplicated_keyframes`:BOOLEAN, `view2d_edge_pan`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.shear` | Shear selected items along the given axis | `angle`:FLOAT, `orient_axis`=X/Y/Z, `orient_axis_ortho`=X/Y/Z, `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `gpencil_strokes`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.shrink_fatten` | Shrink/fatten selected vertices along normals | `value`:FLOAT, `use_even_offset`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.skin_resize` | Scale selected vertices' skin radii | `value`:FLOAT, `orient_type`=, `orient_matrix`:FLOAT, `orient_matrix_type`=, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.tilt` | Tilt selected control vertices of 3D curve | `value`:FLOAT, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ✅ | `transform.tosphere` | Move selected items outward in a spherical shape around geometric center | `value`:FLOAT, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `gpencil_strokes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ✅ | `transform.trackball` | Trackball style rotation of selected items | `value`:FLOAT, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `gpencil_strokes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ✅ | `transform.transform` | Transform selected items by mode type | `mode`=INIT/DUMMY/TRANSLATION/ROTATION/RESIZE/SKIN_RESIZE/TOSPHERE/SHEAR/BEND/SHRINKFATTEN/TILT/TRACKBALL/PUSHPULL/CREASE/VERTEX_CREASE/MIRROR/BONE_SIZE/BONE_ENVELOPE/BONE_ENVELOPE_DIST/CURVE_SHRINKFATTEN/MASK_SHRINKFATTEN/BONE_ROLL/TIME_TRANSLATE/TIME_SLIDE/TIME_SCALE/TIME_EXTEND/BAKE_TIME/BWEIGHT/ALIGN/EDGESLIDE/SEQSLIDE/GPENCIL_OPACITY, `value`:FLOAT, `orient_axis`=X/Y/Z, `orient_type`=GLOBAL/LOCAL/NORMAL/GIMBAL/VIEW/CURSOR/PARENT, `orient_matrix`:FLOAT, `orient_matrix_type`=GLOBAL/LOCAL/NORMAL/GIMBAL/VIEW/CURSOR/PARENT, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `snap_align`:BOOLEAN, `snap_normal`:FLOAT, `gpencil_strokes`:BOOLEAN, `texture_space`:BOOLEAN, `remove_on_cancel`:BOOLEAN, `use_duplicated_keyframes`:BOOLEAN, `center_override`:FLOAT, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN, `use_automerge_and_split`:BOOLEAN |
| ✅ | `transform.translate` | Move selected items | `value`:FLOAT, `orient_type`=GLOBAL/LOCAL/NORMAL/GIMBAL/VIEW/CURSOR/PARENT, `orient_matrix`:FLOAT, `orient_matrix_type`=GLOBAL/LOCAL/NORMAL/GIMBAL/VIEW/CURSOR/PARENT, `constraint_axis`:BOOLEAN, `mirror`:BOOLEAN, `use_proportional_edit`:BOOLEAN, `proportional_edit_falloff`=SMOOTH/SPHERE/ROOT/INVERSE_SQUARE/SHARP/LINEAR/CONSTANT/RANDOM, `proportional_size`:FLOAT, `use_proportional_connected`:BOOLEAN, `use_proportional_projected`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `snap_align`:BOOLEAN, `snap_normal`:FLOAT, `gpencil_strokes`:BOOLEAN, `cursor_transform`:BOOLEAN, `texture_space`:BOOLEAN, `remove_on_cancel`:BOOLEAN, `use_duplicated_keyframes`:BOOLEAN, `view2d_edge_pan`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN, `use_automerge_and_split`:BOOLEAN, `translate_origin`:BOOLEAN |
| ❌ | `transform.vert_crease` | Change the crease of vertices | `value`:FLOAT, `snap`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.vert_slide` | Slide a vertex along a mesh | `value`:FLOAT, `use_even`:BOOLEAN, `flipped`:BOOLEAN, `use_clamp`:BOOLEAN, `direction`:FLOAT, `mirror`:BOOLEAN, `snap`:BOOLEAN, `snap_elements`=INCREMENT/GRID/VERTEX/EDGE/FACE/VOLUME/EDGE_MIDPOINT/EDGE_PERPENDICULAR/FACE_MIDPOINT/FACE_PROJECT/FACE_NEAREST, `use_snap_project`:BOOLEAN, `snap_target`=CLOSEST/CENTER/MEDIAN/ACTIVE, `use_snap_self`:BOOLEAN, `use_snap_edit`:BOOLEAN, `use_snap_nonedit`:BOOLEAN, `use_snap_selectable`:BOOLEAN, `snap_point`:FLOAT, `correct_uv`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN |
| ❌ | `transform.vertex_random` | Randomize vertices | `offset`:FLOAT, `uniform`:FLOAT, `normal`:FLOAT, `seed`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `transform.vertex_warp` | Warp vertices around the cursor | `warp_angle`:FLOAT, `offset_angle`:FLOAT, `min`:FLOAT, `max`:FLOAT, `viewmat`:FLOAT, `center`:FLOAT |

### `ui` — 38개 (✅ 5 / ⚠ 0 / ❌ 33)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `ui.assign_default_button` | Set this property's current value as the new default | — |
| ✅ | `ui.button_execute` | Presses active button | `skip_depressed`:BOOLEAN |
| ❌ | `ui.button_string_clear` | Unsets the text of the active button | — |
| ❌ | `ui.copy_as_driver_button` | Create a new driver with this property as input, and copy it to the internal clipboard. Us | — |
| ❌ | `ui.copy_data_path_button` | Copy the RNA data path for this property to the clipboard | `full_path`:BOOLEAN |
| ❌ | `ui.copy_driver_to_selected_button` | Copy the property's driver from the active item to the same property of all selected items | `all`:BOOLEAN |
| ❌ | `ui.copy_python_command_button` | Copy the Python command matching this button | — |
| ❌ | `ui.copy_to_selected_button` | Copy the property's value from the active item to the same property of all selected items  | `all`:BOOLEAN |
| ❌ | `ui.drop_color` | Drop colors to buttons | `color`:FLOAT, `gamma`:BOOLEAN, `has_alpha`:BOOLEAN |
| ❌ | `ui.drop_material` | Drag material to Material slots in Properties | `session_uid`:INT |
| ❌ | `ui.drop_name` | Drop name to button | `string`:STRING |
| ✅ | `ui.editsource` | Edit UI source code of the active button | — |
| ❌ | `ui.eyedropper_bone` | Sample a bone from the 3D View or the Outliner to store in a property | — |
| ✅ | `ui.eyedropper_color` | Sample a color from the Blender window to store in a property | `prop_data_path`:STRING |
| ❌ | `ui.eyedropper_colorramp` | Sample a color band | — |
| ❌ | `ui.eyedropper_colorramp_point` | Point-sample a color band | — |
| ❌ | `ui.eyedropper_depth` | Sample depth from the 3D view | `prop_data_path`:STRING |
| ✅ | `ui.eyedropper_driver` | Pick a property to use as a driver target | `mapping_type`=SINGLE_MANY/DIRECT/MATCH/NONE_ALL/NONE_SINGLE |
| ❌ | `ui.eyedropper_grease_pencil_color` | Sample a color from the Blender Window and create Grease Pencil material | `mode`=MATERIAL/PALETTE/BRUSH, `material_mode`=STROKE/FILL/BOTH |
| ❌ | `ui.eyedropper_id` | Sample a data-block from the 3D View to store in a property | — |
| ❌ | `ui.jump_to_target_button` | Switch to the target object or bone | — |
| ❌ | `ui.list_start_filter` | Start entering filter text for the list in focus | — |
| ❌ | `ui.override_add_button` | Create an override operation | `all`:BOOLEAN |
| ❌ | `ui.override_idtemplate_clear` | Delete the selected local override and relink its usages to the linked data-block if possi | — |
| ❌ | `ui.override_idtemplate_make` | Create a local override of the selected linked data-block, and its hierarchy of dependenci | — |
| ❌ | `ui.override_idtemplate_reset` | Reset the selected local override to its linked reference values | — |
| ❌ | `ui.override_remove_button` | Remove an override operation | `all`:BOOLEAN |
| ✅ | `ui.reloadtranslation` | Force a full reload of UI translation | — |
| ❌ | `ui.reset_default_button` | Reset this property's value to its default value | `all`:BOOLEAN |
| ❌ | `ui.unset_property_button` | Clear the property and use default or generated value in operators | — |
| ❌ | `ui.view_drop` | Drag and drop onto a data-set or item within the data-set | — |
| ❌ | `ui.view_item_delete` | Delete selected list item | — |
| ❌ | `ui.view_item_focus` | Bring active item into focus by scrolling the view | — |
| ❌ | `ui.view_item_navigate` | Walk and select view items in given direction | `direction`=UP/DOWN/LEFT/RIGHT |
| ❌ | `ui.view_item_rename` | Rename the active item in the data-set view | — |
| ❌ | `ui.view_item_select` | Activate selected view item | `wait_to_deselect_others`:BOOLEAN, `use_select_on_click`:BOOLEAN, `mouse_x`:INT, `mouse_y`:INT, `extend`:BOOLEAN, `range_select`:BOOLEAN |
| ❌ | `ui.view_scroll` | (undocumented operator) | — |
| ❌ | `ui.view_start_filter` | Start entering filter text for the data-set in focus | — |

### `uilist` — 3개 (✅ 3 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `uilist.entry_add` | Add an entry to the list after the current active item | `list_path`:STRING, `active_index_path`:STRING |
| ✅ | `uilist.entry_move` | Move an entry in the list up or down | `list_path`:STRING, `active_index_path`:STRING, `direction`=UP/DOWN |
| ✅ | `uilist.entry_remove` | Remove the selected entry from the list | `list_path`:STRING, `active_index_path`:STRING |

### `uv` — 55개 (✅ 0 / ⚠ 2 / ❌ 53)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `uv.align` | Aligns selected UV vertices on a line | `axis`=ALIGN_S/ALIGN_T/ALIGN_U/ALIGN_AUTO/ALIGN_X/ALIGN_Y, `position_mode`=MEAN/MIN/MAX |
| ❌ | `uv.align_rotation` | Align the UV island's rotation | `method`=AUTO/EDGE/GEOMETRY, `axis`=X/Y/Z, `correct_aspect`:BOOLEAN |
| ❌ | `uv.arrange_islands` | Arrange selected UV islands on a line | `initial_position`=BOUNDING_BOX/UV_GRID/ACTIVE_UDIM/CURSOR, `axis`=X/Y, `align`=MIN/MAX/CENTER/NONE, `order`=LARGE_TO_SMALL/SMALL_TO_LARGE/Fixed, `margin`:FLOAT |
| ❌ | `uv.average_islands_scale` | Average the size of separate UV islands, based on their area in 3D space | `scale_uv`:BOOLEAN, `shear`:BOOLEAN |
| ❌ | `uv.copy` | Copy selected UV vertices | — |
| ❌ | `uv.copy_mirrored_faces` | Copy mirror UV coordinates based on a mirrored mesh | `mesh_axis`=POS_X/POS_Y/POS_Z/NEG_X/NEG_Y/NEG_Z, `uv_axis`=X/Y, `precision`:INT |
| ❌ | `uv.cube_project` | Project the UV vertices of the mesh over the six faces of a cube | `cube_size`:FLOAT, `correct_aspect`:BOOLEAN, `clip_to_bounds`:BOOLEAN, `scale_to_bounds`:BOOLEAN |
| ❌ | `uv.cursor_set` | Set 2D cursor location | `location`:FLOAT |
| ❌ | `uv.custom_region_set` | Set the boundaries of the user region | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `uv.cylinder_project` | Project the UV vertices of the mesh over the curved wall of a cylinder | `direction`=VIEW_ON_EQUATOR/VIEW_ON_POLES/ALIGN_TO_OBJECT, `align`=POLAR_ZX/POLAR_ZY, `pole`=PINCH/FAN, `seam`:BOOLEAN, `radius`:FLOAT, `correct_aspect`:BOOLEAN, `clip_to_bounds`:BOOLEAN, `scale_to_bounds`:BOOLEAN |
| ⚠ | `uv.export_layout` | Export UV layout to file | `filepath`:STRING, `export_all`:BOOLEAN, `export_tiles`=NONE/UDIM/UV, `modified`:BOOLEAN, `mode`=SVG/EPS/PNG, `size`:INT, `opacity`:FLOAT, `check_existing`:BOOLEAN |
| ❌ | `uv.follow_active_quads` | Follow UVs from active quads along continuous face loops | `mode`=EVEN/LENGTH/LENGTH_AVERAGE |
| ❌ | `uv.hide` | Hide (un)selected UV vertices | `unselected`:BOOLEAN |
| ⚠ | `uv.lightmap_pack` | Pack each face's UVs into the UV bounds | `PREF_CONTEXT`=SEL_FACES/ALL_FACES, `PREF_PACK_IN_ONE`:BOOLEAN, `PREF_NEW_UVLAYER`:BOOLEAN, `PREF_BOX_DIV`:INT, `PREF_MARGIN_DIV`:FLOAT |
| ❌ | `uv.mark_seam` | Mark selected UV edges as seams | `clear`:BOOLEAN |
| ❌ | `uv.minimize_stretch` | Reduce UV stretching by relaxing angles | `fill_holes`:BOOLEAN, `blend`:FLOAT, `iterations`:INT |
| ❌ | `uv.move_on_axis` | Move UVs on an axis | `type`=DYNAMIC/PIXEL/UDIM, `axis`=X/Y, `distance`:INT |
| ❌ | `uv.pack_islands` | Transform all islands so that they fill up the UV/UDIM space as much as possible | `udim_source`=CLOSEST_UDIM/ACTIVE_UDIM/ORIGINAL_AABB/CUSTOM_REGION, `rotate`:BOOLEAN, `rotate_method`=ANY/CARDINAL/AXIS_ALIGNED/AXIS_ALIGNED_X/AXIS_ALIGNED_Y, `scale`:BOOLEAN, `merge_overlap`:BOOLEAN, `margin_method`=SCALED/ADD/FRACTION, `margin`:FLOAT, `pin`:BOOLEAN, `pin_method`=SCALE/ROTATION/ROTATION_SCALE/LOCKED, `shape_method`=CONCAVE/CONVEX/AABB |
| ❌ | `uv.paste` | Paste selected UV vertices | — |
| ❌ | `uv.pin` | Set/clear selected UV vertices as anchored between multiple unwrap operations | `clear`:BOOLEAN, `invert`:BOOLEAN |
| ❌ | `uv.project_from_view` | Project the UV vertices of the mesh as seen in current 3D view | `orthographic`:BOOLEAN, `camera_bounds`:BOOLEAN, `correct_aspect`:BOOLEAN, `clip_to_bounds`:BOOLEAN, `scale_to_bounds`:BOOLEAN |
| ❌ | `uv.randomize_uv_transform` | Randomize the UV island's location, rotation, and scale | `random_seed`:INT, `use_loc`:BOOLEAN, `loc`:FLOAT, `use_rot`:BOOLEAN, `rot`:FLOAT, `use_scale`:BOOLEAN, `scale_even`:BOOLEAN, `scale`:FLOAT |
| ❌ | `uv.remove_doubles` | Selected UV vertices that are within a radius of each other are welded together | `threshold`:FLOAT, `use_unselected`:BOOLEAN, `use_shared_vertex`:BOOLEAN |
| ❌ | `uv.reset` | Reset UV projection | — |
| ❌ | `uv.reveal` | Reveal all hidden UV vertices | `select`:BOOLEAN |
| ❌ | `uv.rip` | Rip selected vertices or a selected region | `mirror`:BOOLEAN, `release_confirm`:BOOLEAN, `use_accurate`:BOOLEAN, `location`:FLOAT |
| ❌ | `uv.rip_move` | Unstitch UVs and move the result | `UV_OT_rip`:POINTER, `TRANSFORM_OT_translate`:POINTER |
| ❌ | `uv.seams_from_islands` | Set mesh seams according to island setup in the UV editor | `mark_seams`:BOOLEAN, `mark_sharp`:BOOLEAN |
| ❌ | `uv.select` | Select UV vertices | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `location`:FLOAT |
| ❌ | `uv.select_all` | Change selection of all UV vertices | `action`=TOGGLE/SELECT/DESELECT/INVERT |
| ❌ | `uv.select_box` | Select UV vertices using box selection | `pinned`:BOOLEAN, `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `uv.select_by_winding` | Select UV faces by their winding | `winding`=POSITIVE/NEGATIVE, `extend`:BOOLEAN |
| ❌ | `uv.select_circle` | Select UV vertices using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `uv.select_edge_ring` | Select an edge ring of connected UV vertices | `extend`:BOOLEAN, `location`:FLOAT |
| ❌ | `uv.select_lasso` | Select UVs using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB |
| ❌ | `uv.select_less` | Deselect UV vertices at the boundary of each selection region | — |
| ❌ | `uv.select_linked` | Select all UV vertices linked to the active UV map | `delimit`=SEAM/SHARP/MATERIAL |
| ❌ | `uv.select_linked_pick` | Select all UV vertices linked under the mouse | `extend`:BOOLEAN, `deselect`:BOOLEAN, `delimit`=SEAM/SHARP/MATERIAL, `location`:FLOAT |
| ❌ | `uv.select_loop` | Select a loop of connected UV vertices | `extend`:BOOLEAN, `location`:FLOAT |
| ❌ | `uv.select_mode` | Change UV selection mode | `type`=VERTEX/EDGE/FACE |
| ❌ | `uv.select_more` | Select more UV vertices connected to initial selection | — |
| ❌ | `uv.select_overlap` | Select all UV faces which overlap each other | `extend`:BOOLEAN |
| ❌ | `uv.select_pinned` | Select all pinned UV vertices | — |
| ❌ | `uv.select_similar` | Select similar UVs by property types | `type`=PIN/LENGTH/LENGTH_3D/AREA/AREA_3D/MATERIAL/OBJECT/SIDES/WINDING/FACE, `compare`=EQUAL/GREATER/LESS, `threshold`:FLOAT |
| ❌ | `uv.select_split` | Select only entirely selected faces | — |
| ❌ | `uv.select_tile` | Select UVs in specified tile | `extend`:BOOLEAN, `tile`:INT |
| ❌ | `uv.shortest_path_pick` | Select shortest path between two selections | `use_face_step`:BOOLEAN, `use_topology_distance`:BOOLEAN, `use_fill`:BOOLEAN, `skip`:INT, `nth`:INT, `offset`:INT, `object_index`:INT, `index`:INT |
| ❌ | `uv.shortest_path_select` | Select shortest path between two vertices/edges/faces | `use_face_step`:BOOLEAN, `use_topology_distance`:BOOLEAN, `use_fill`:BOOLEAN, `skip`:INT, `nth`:INT, `offset`:INT |
| ❌ | `uv.smart_project` | Projection unwraps the selected faces of mesh objects | `angle_limit`:FLOAT, `margin_method`=SCALED/ADD/FRACTION, `rotate_method`=AXIS_ALIGNED/AXIS_ALIGNED_X/AXIS_ALIGNED_Y, `island_margin`:FLOAT, `area_weight`:FLOAT, `correct_aspect`:BOOLEAN, `scale_to_bounds`:BOOLEAN |
| ❌ | `uv.snap_cursor` | Snap cursor to target type | `target`=PIXELS/SELECTED/ORIGIN |
| ❌ | `uv.snap_selected` | Snap selected UV vertices to target type | `target`=PIXELS/CURSOR/CURSOR_OFFSET/ADJACENT_UNSELECTED |
| ❌ | `uv.sphere_project` | Project the UV vertices of the mesh over the curved surface of a sphere | `direction`=VIEW_ON_EQUATOR/VIEW_ON_POLES/ALIGN_TO_OBJECT, `align`=POLAR_ZX/POLAR_ZY, `pole`=PINCH/FAN, `seam`:BOOLEAN, `correct_aspect`:BOOLEAN, `clip_to_bounds`:BOOLEAN, `scale_to_bounds`:BOOLEAN |
| ❌ | `uv.stitch` | Stitch selected UV vertices by proximity | `use_limit`:BOOLEAN, `snap_islands`:BOOLEAN, `limit`:FLOAT, `static_island`:INT, `active_object_index`:INT, `midpoint_snap`:BOOLEAN, `clear_seams`:BOOLEAN, `mode`=VERTEX/EDGE, `stored_mode`=VERTEX/EDGE, `selection`:COLLECTION, `objects_selection_count`:INT |
| ❌ | `uv.unwrap` | Unwrap the mesh of the object being edited | `method`=ANGLE_BASED/CONFORMAL/MINIMUM_STRETCH, `fill_holes`:BOOLEAN, `correct_aspect`:BOOLEAN, `use_subsurf_data`:BOOLEAN, `use_original_bounds`:BOOLEAN, `margin_method`=SCALED/ADD/FRACTION, `margin`:FLOAT, `no_flip`:BOOLEAN, `iterations`:INT, `use_weights`:BOOLEAN, `weight_group`:STRING, `weight_factor`:FLOAT |
| ❌ | `uv.weld` | Weld selected UV vertices together | — |

### `view2d` — 14개 (✅ 0 / ⚠ 0 / ❌ 14)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `view2d.edge_pan` | Pan the view when the mouse is held at an edge | `inside_padding`:FLOAT, `outside_padding`:FLOAT, `speed_ramp`:FLOAT, `max_speed`:FLOAT, `delay`:FLOAT, `zoom_influence`:FLOAT |
| ❌ | `view2d.ndof` | Use a 3D mouse device to pan/zoom the view | — |
| ❌ | `view2d.pan` | Pan the view | `deltax`:INT, `deltay`:INT |
| ❌ | `view2d.reset` | Reset the view | — |
| ❌ | `view2d.scroll_down` | Scroll the view down | `deltax`:INT, `deltay`:INT, `page`:BOOLEAN |
| ❌ | `view2d.scroll_left` | Scroll the view left | `deltax`:INT, `deltay`:INT |
| ❌ | `view2d.scroll_right` | Scroll the view right | `deltax`:INT, `deltay`:INT |
| ❌ | `view2d.scroll_up` | Scroll the view up | `deltax`:INT, `deltay`:INT, `page`:BOOLEAN |
| ❌ | `view2d.scroller_activate` | Scroll view by mouse click and drag | — |
| ❌ | `view2d.smoothview` | (undocumented operator) | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `view2d.zoom` | Zoom in/out the view | `deltax`:FLOAT, `deltay`:FLOAT, `use_cursor_init`:BOOLEAN |
| ❌ | `view2d.zoom_border` | Zoom in the view to the nearest item contained in the border | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `zoom_out`:BOOLEAN |
| ❌ | `view2d.zoom_in` | Zoom in the view | `zoomfacx`:FLOAT, `zoomfacy`:FLOAT |
| ❌ | `view2d.zoom_out` | Zoom out the view | `zoomfacx`:FLOAT, `zoomfacy`:FLOAT |

### `view3d` — 68개 (✅ 8 / ⚠ 0 / ❌ 60)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `view3d.bone_select_menu` | Menu bone selection | `name`=, `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN |
| ❌ | `view3d.camera_background_image_add` | Add a new background image to the active camera | `filepath`:STRING, `relative_path`:BOOLEAN, `name`:STRING, `session_uid`:INT |
| ❌ | `view3d.camera_background_image_remove` | Remove a background image from the camera | `index`:INT |
| ❌ | `view3d.camera_to_view` | Set camera view to active view | — |
| ✅ | `view3d.camera_to_view_selected` | Move the camera so selected objects are framed | — |
| ❌ | `view3d.clear_render_border` | Clear the boundaries of the border render and disable border render | — |
| ❌ | `view3d.clip_border` | Set the view clipping region | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ✅ | `view3d.copybuffer` | Copy the selected objects to the internal clipboard | — |
| ❌ | `view3d.cursor3d` | Set the location of the 3D cursor | `use_depth`:BOOLEAN, `orientation`=NONE/VIEW/XFORM/GEOM |
| ❌ | `view3d.dolly` | Dolly in/out in the view | `mx`:INT, `my`:INT, `delta`:INT, `use_cursor_init`:BOOLEAN |
| ✅ | `view3d.drop_world` | Drop a world into the scene | `name`:STRING, `session_uid`:INT |
| ❌ | `view3d.edit_mesh_extrude_individual_move` | Extrude each individual face separately along local normals | — |
| ❌ | `view3d.edit_mesh_extrude_manifold_normal` | Extrude manifold region along normals | — |
| ❌ | `view3d.edit_mesh_extrude_move_normal` | Extrude region together along the average normal | `dissolve_and_intersect`:BOOLEAN |
| ❌ | `view3d.edit_mesh_extrude_move_shrink_fatten` | Extrude region together along local normals | — |
| ❌ | `view3d.fly` | Interactively fly around the scene | — |
| ✅ | `view3d.interactive_add` | Interactively add an object | `primitive_type`=CUBE/CYLINDER/CONE/SPHERE_UV/SPHERE_ICO, `plane_origin_base`=EDGE/CENTER, `plane_origin_depth`=EDGE/CENTER, `plane_aspect_base`=FREE/FIXED, `plane_aspect_depth`=FREE/FIXED, `wait_for_input`:BOOLEAN |
| ❌ | `view3d.localview` | Toggle display of selected object(s) separately and centered in view | `frame_selected`:BOOLEAN |
| ❌ | `view3d.localview_remove_from` | Move selected objects out of local view | — |
| ❌ | `view3d.move` | Move the view | `use_cursor_init`:BOOLEAN |
| ❌ | `view3d.navigate` | Interactively navigate around the scene (uses the mode (walk/fly) preference) | — |
| ❌ | `view3d.ndof_all` | Pan and rotate the view with the 3D mouse | — |
| ❌ | `view3d.ndof_orbit` | Orbit the view using the 3D mouse | — |
| ❌ | `view3d.ndof_orbit_zoom` | Orbit and zoom the view using the 3D mouse | — |
| ❌ | `view3d.ndof_pan` | Pan the view with the 3D mouse | — |
| ❌ | `view3d.object_as_camera` | Set the active object as the active camera for this view or scene | — |
| ❌ | `view3d.object_mode_pie_or_toggle` | (undocumented operator) | — |
| ✅ | `view3d.pastebuffer` | Paste objects from the internal clipboard | `autoselect`:BOOLEAN, `active_collection`:BOOLEAN |
| ❌ | `view3d.render_border` | Set the boundaries of the border render and enable border render | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN |
| ❌ | `view3d.rotate` | Rotate the view | `use_cursor_init`:BOOLEAN |
| ❌ | `view3d.ruler_add` | Add ruler | — |
| ❌ | `view3d.ruler_remove` | (undocumented operator) | — |
| ❌ | `view3d.select` | Select and activate item(s) | `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN, `deselect_all`:BOOLEAN, `select_passthrough`:BOOLEAN, `center`:BOOLEAN, `enumerate`:BOOLEAN, `object`:BOOLEAN, `location`:INT |
| ❌ | `view3d.select_box` | Select items using box selection | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB/XOR/AND |
| ❌ | `view3d.select_circle` | Select items using circle selection | `x`:INT, `y`:INT, `radius`:INT, `wait_for_input`:BOOLEAN, `mode`=SET/ADD/SUB |
| ❌ | `view3d.select_lasso` | Select items using lasso selection | `path`:COLLECTION, `use_smooth_stroke`:BOOLEAN, `smooth_stroke_factor`:FLOAT, `smooth_stroke_radius`:INT, `mode`=SET/ADD/SUB/XOR/AND |
| ✅ | `view3d.select_menu` | Menu object selection | `name`=, `extend`:BOOLEAN, `deselect`:BOOLEAN, `toggle`:BOOLEAN |
| ❌ | `view3d.smoothview` | (undocumented operator) | — |
| ❌ | `view3d.snap_cursor_to_active` | Snap 3D cursor to the active item | — |
| ❌ | `view3d.snap_cursor_to_center` | Snap 3D cursor to the world origin | — |
| ❌ | `view3d.snap_cursor_to_grid` | Snap 3D cursor to the nearest grid division | — |
| ❌ | `view3d.snap_cursor_to_selected` | Snap 3D cursor to the middle of the selected item(s) | — |
| ❌ | `view3d.snap_selected_to_active` | Snap selected item(s) to the active item | — |
| ❌ | `view3d.snap_selected_to_cursor` | Snap selected item(s) to the 3D cursor | `use_offset`:BOOLEAN, `use_rotation`:BOOLEAN |
| ❌ | `view3d.snap_selected_to_grid` | Snap selected item(s) to their nearest grid division | — |
| ✅ | `view3d.toggle_matcap_flip` | Flip MatCap | — |
| ❌ | `view3d.toggle_shading` | Toggle shading type in 3D viewport | `type`=WIREFRAME/SOLID/MATERIAL/RENDERED |
| ❌ | `view3d.toggle_xray` | Transparent scene display. Allow selecting through items | — |
| ❌ | `view3d.transform_gizmo_set` | Set the current transform gizmo | `extend`:BOOLEAN, `type`=TRANSLATE/ROTATE/SCALE |
| ❌ | `view3d.view_all` | View all objects in scene | `use_all_regions`:BOOLEAN, `center`:BOOLEAN |
| ❌ | `view3d.view_axis` | Use a preset viewpoint | `type`=LEFT/RIGHT/BOTTOM/TOP/FRONT/BACK, `align_active`:BOOLEAN, `relative`:BOOLEAN |
| ❌ | `view3d.view_camera` | Toggle the camera view | — |
| ❌ | `view3d.view_center_camera` | Center the camera view, resizing the view to fit its bounds | — |
| ❌ | `view3d.view_center_cursor` | Center the view so that the cursor is in the middle of the view | — |
| ❌ | `view3d.view_center_lock` | Center the view lock offset | — |
| ❌ | `view3d.view_center_pick` | Center the view to the Z-depth position under the mouse cursor | — |
| ❌ | `view3d.view_lock_clear` | Clear all view locking | — |
| ❌ | `view3d.view_lock_to_active` | Lock the view to the active object/bone | — |
| ❌ | `view3d.view_orbit` | Orbit the view | `angle`:FLOAT, `type`=ORBITLEFT/ORBITRIGHT/ORBITUP/ORBITDOWN |
| ❌ | `view3d.view_pan` | Pan the view in a given direction | `type`=PANLEFT/PANRIGHT/PANUP/PANDOWN |
| ❌ | `view3d.view_persportho` | Switch the current view from perspective/orthographic projection | — |
| ❌ | `view3d.view_roll` | Roll the view | `angle`:FLOAT, `type`=ANGLE/LEFT/RIGHT |
| ❌ | `view3d.view_selected` | Move the view to the selection center | `use_all_regions`:BOOLEAN |
| ❌ | `view3d.vr_location_scouting_capture_review` | Interactively review Location Scouting VR Captures | — |
| ❌ | `view3d.walk` | Interactively walk around the scene | — |
| ❌ | `view3d.zoom` | Zoom in/out in the view | `mx`:INT, `my`:INT, `delta`:INT, `use_cursor_init`:BOOLEAN |
| ❌ | `view3d.zoom_border` | Zoom in the view to the nearest object contained in the border | `xmin`:INT, `xmax`:INT, `ymin`:INT, `ymax`:INT, `wait_for_input`:BOOLEAN, `zoom_out`:BOOLEAN |
| ❌ | `view3d.zoom_camera_1_to_1` | Match the camera to 1:1 to the render output | — |

### `wm` — 117개 (✅ 104 / ⚠ 0 / ❌ 13)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `wm.alembic_export` | Export current scene in an Alembic archive | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `filter_glob`:STRING, `start`:INT, `end`:INT, `xsamples`:INT, `gsamples`:INT, `sh_open`:FLOAT, `sh_close`:FLOAT, `selected`:BOOLEAN, `flatten`:BOOLEAN, `collection`:STRING, `uvs`:BOOLEAN, `packuv`:BOOLEAN, `normals`:BOOLEAN, `vcolors`:BOOLEAN, `orcos`:BOOLEAN, `face_sets`:BOOLEAN, `subdiv_schema`:BOOLEAN, `apply_subdiv`:BOOLEAN, `curves_as_mesh`:BOOLEAN, `use_instancing`:BOOLEAN, `global_scale`:FLOAT, `triangulate`:BOOLEAN, `quad_method`=BEAUTY/FIXED/FIXED_ALTERNATE/SHORTEST_DIAGONAL/LONGEST_DIAGONAL, `ngon_method`=BEAUTY/CLIP, `export_hair`:BOOLEAN, `export_particles`:BOOLEAN, `export_custom_properties`:BOOLEAN, `as_background_job`:BOOLEAN, `evaluation_mode`=RENDER/VIEWPORT, `init_scene_frame_range`:BOOLEAN |
| ✅ | `wm.alembic_import` | Load an Alembic archive | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `filter_glob`:STRING, `scale`:FLOAT, `set_frame_range`:BOOLEAN, `validate_meshes`:BOOLEAN, `always_add_cache_reader`:BOOLEAN, `is_sequence`:BOOLEAN, `as_background_job`:BOOLEAN |
| ✅ | `wm.append` | Append from a Library .blend file | `filepath`:STRING, `directory`:STRING, `filename`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `link`:BOOLEAN, `do_reuse_local_id`:BOOLEAN, `clear_asset_data`:BOOLEAN, `autoselect`:BOOLEAN, `active_collection`:BOOLEAN, `instance_collections`:BOOLEAN, `instance_object_data`:BOOLEAN, `set_fake`:BOOLEAN, `use_recursive`:BOOLEAN |
| ✅ | `wm.batch_rename` | Rename multiple items at once | `data_type`=OBJECT/COLLECTION/MATERIAL/MESH/CURVE/META/VOLUME/GREASEPENCIL/ARMATURE/LATTICE/LIGHT/LIGHT_PROBE/CAMERA/SPEAKER/BONE/NODE/SEQUENCE_STRIP/ACTION_CLIP/SCENE/BRUSH, `data_source`=SELECT/ALL, `actions`:COLLECTION |
| ✅ | `wm.blend_strings_utf8_validate` | Check and fix all strings in current .blend file to be valid UTF-8 Unicode (needed for som | — |
| ✅ | `wm.call_asset_shelf_popover` | Open a predefined asset shelf in a popup | `name`:STRING |
| ✅ | `wm.call_menu` | Open a predefined menu | `name`:STRING |
| ✅ | `wm.call_menu_pie` | Open a predefined pie menu | `name`:STRING |
| ✅ | `wm.call_panel` | Open a predefined panel | `name`:STRING, `keep_open`:BOOLEAN |
| ✅ | `wm.clear_recent_files` | Clear the recent files list | `remove`=ALL/MISSING |
| ✅ | `wm.collection_export_all` | Invoke all configured exporters for all collections | — |
| ✅ | `wm.context_collection_boolean_set` | Set boolean values for a collection of items | `data_path_iter`:STRING, `data_path_item`:STRING, `type`=TOGGLE/ENABLE/DISABLE |
| ✅ | `wm.context_cycle_array` | Set a context array value (useful for cycling the active mesh edit mode) | `data_path`:STRING, `reverse`:BOOLEAN |
| ✅ | `wm.context_cycle_enum` | Toggle a context value | `data_path`:STRING, `reverse`:BOOLEAN, `wrap`:BOOLEAN |
| ✅ | `wm.context_cycle_int` | Set a context value (useful for cycling active material, shape keys, groups, etc.) | `data_path`:STRING, `reverse`:BOOLEAN, `wrap`:BOOLEAN |
| ✅ | `wm.context_menu_enum` | (undocumented operator) | `data_path`:STRING |
| ✅ | `wm.context_modal_mouse` | Adjust arbitrary values with mouse input | `data_path_iter`:STRING, `data_path_item`:STRING, `header_text`:STRING, `input_scale`:FLOAT, `invert`:BOOLEAN, `initial_x`:INT |
| ✅ | `wm.context_pie_enum` | (undocumented operator) | `data_path`:STRING |
| ✅ | `wm.context_scale_float` | Scale a float context value | `data_path`:STRING, `value`:FLOAT |
| ✅ | `wm.context_scale_int` | Scale an int context value | `data_path`:STRING, `value`:FLOAT, `always_step`:BOOLEAN |
| ✅ | `wm.context_set_boolean` | Set a context value | `data_path`:STRING, `value`:BOOLEAN |
| ✅ | `wm.context_set_enum` | Set a context value | `data_path`:STRING, `value`:STRING |
| ✅ | `wm.context_set_float` | Set a context value | `data_path`:STRING, `value`:FLOAT, `relative`:BOOLEAN |
| ✅ | `wm.context_set_id` | Set a context value to an ID data-block | `data_path`:STRING, `value`:STRING |
| ✅ | `wm.context_set_int` | Set a context value | `data_path`:STRING, `value`:INT, `relative`:BOOLEAN |
| ✅ | `wm.context_set_string` | Set a context value | `data_path`:STRING, `value`:STRING |
| ✅ | `wm.context_set_value` | Set a context value | `data_path`:STRING, `value`:STRING |
| ✅ | `wm.context_toggle` | Toggle a context value | `data_path`:STRING, `module`:STRING |
| ✅ | `wm.context_toggle_enum` | Toggle a context value | `data_path`:STRING, `value_1`:STRING, `value_2`:STRING |
| ✅ | `wm.debug_menu` | Open a popup to set the debug level | `debug_value`:INT |
| ✅ | `wm.doc_view` | Open online reference docs in a web browser | `doc_id`:STRING |
| ✅ | `wm.doc_view_manual` | Load online manual | `doc_id`:STRING |
| ❌ | `wm.doc_view_manual_ui_context` | View a context based online manual in a web browser | — |
| ✅ | `wm.drop_blend_file` | (undocumented operator) | `filepath`:STRING, `use_scripts`:BOOLEAN |
| ✅ | `wm.drop_import_file` | Operator that allows file handlers to receive file drops | `directory`:STRING, `files`:COLLECTION |
| ✅ | `wm.fbx_import` | Import FBX file into current scene | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `global_scale`:FLOAT, `mtl_name_collision_mode`=MAKE_UNIQUE/REFERENCE_EXISTING, `import_colors`=NONE/SRGB/LINEAR, `use_custom_normals`:BOOLEAN, `use_custom_props`:BOOLEAN, `use_custom_props_enum_as_string`:BOOLEAN, `import_subdivision`:BOOLEAN, `ignore_leaf_bones`:BOOLEAN, `validate_meshes`:BOOLEAN, `use_anim`:BOOLEAN, `anim_offset`:FLOAT, `filter_glob`:STRING |
| ✅ | `wm.grease_pencil_export_pdf` | Export Grease Pencil to PDF | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `use_fill`:BOOLEAN, `selected_object_type`=ACTIVE/SELECTED/VISIBLE, `frame_mode`=ACTIVE/SELECTED/SCENE, `stroke_sample`:FLOAT, `use_uniform_width`:BOOLEAN |
| ✅ | `wm.grease_pencil_export_svg` | Export Grease Pencil to SVG | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `use_fill`:BOOLEAN, `selected_object_type`=ACTIVE/SELECTED/VISIBLE, `frame_mode`=ACTIVE/SELECTED/SCENE, `stroke_sample`:FLOAT, `use_uniform_width`:BOOLEAN, `use_clip_camera`:BOOLEAN |
| ✅ | `wm.grease_pencil_import_svg` | Import SVG into Grease Pencil | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `resolution`:INT, `scale`:FLOAT, `use_scene_unit`:BOOLEAN, `recenter_bounds`:BOOLEAN |
| ✅ | `wm.id_linked_relocate` | Relocate a linked ID, i.e. select another ID to link, and remap its local usages to that n | `id_session_uid`:INT, `filepath`:STRING, `directory`:STRING, `filename`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `link`:BOOLEAN, `do_reuse_local_id`:BOOLEAN, `clear_asset_data`:BOOLEAN, `autoselect`:BOOLEAN, `active_collection`:BOOLEAN, `instance_collections`:BOOLEAN, `instance_object_data`:BOOLEAN |
| ✅ | `wm.interface_theme_preset_add` | Add a custom theme to the preset list | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `wm.interface_theme_preset_remove` | Remove a custom theme from the preset list | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `wm.interface_theme_preset_save` | Save a custom theme in the preset list | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `wm.keyconfig_preset_add` | Add a custom keymap configuration to the preset list | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `wm.keyconfig_preset_remove` | Remove a custom keymap configuration from the preset list | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN |
| ✅ | `wm.lib_reload` | Reload the given library | `library`:STRING, `filepath`:STRING, `directory`:STRING, `filename`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ✅ | `wm.lib_relocate` | Relocate the given library to one or several others | `library`:STRING, `filepath`:STRING, `directory`:STRING, `filename`:STRING, `files`:COLLECTION, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`= |
| ✅ | `wm.link` | Link from a Library .blend file | `filepath`:STRING, `directory`:STRING, `filename`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `link`:BOOLEAN, `do_reuse_local_id`:BOOLEAN, `clear_asset_data`:BOOLEAN, `autoselect`:BOOLEAN, `active_collection`:BOOLEAN, `instance_collections`:BOOLEAN, `instance_object_data`:BOOLEAN |
| ✅ | `wm.memory_statistics` | Print memory statistics to the console | — |
| ✅ | `wm.obj_export` | Save the scene to a Wavefront OBJ file | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `export_animation`:BOOLEAN, `start_frame`:INT, `end_frame`:INT, `forward_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `up_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `global_scale`:FLOAT, `apply_modifiers`:BOOLEAN, `apply_transform`:BOOLEAN, `export_eval_mode`=DAG_EVAL_RENDER/DAG_EVAL_VIEWPORT, `export_selected_objects`:BOOLEAN, `export_uv`:BOOLEAN, `export_normals`:BOOLEAN, `export_colors`:BOOLEAN, `export_materials`:BOOLEAN, `export_pbr_extensions`:BOOLEAN, `path_mode`=AUTO/ABSOLUTE/RELATIVE/MATCH/STRIP/COPY, `export_triangulated_mesh`:BOOLEAN, `export_curves_as_nurbs`:BOOLEAN, `export_object_groups`:BOOLEAN, `export_material_groups`:BOOLEAN, `export_vertex_groups`:BOOLEAN, `export_smooth_groups`:BOOLEAN, `smooth_group_bitflags`:BOOLEAN, `filter_glob`:STRING, `collection`:STRING |
| ✅ | `wm.obj_import` | Load a Wavefront OBJ scene | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `global_scale`:FLOAT, `clamp_size`:FLOAT, `forward_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `up_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `use_split_objects`:BOOLEAN, `use_split_groups`:BOOLEAN, `import_vertex_groups`:BOOLEAN, `validate_meshes`:BOOLEAN, `close_spline_loops`:BOOLEAN, `collection_separator`:STRING, `mtl_name_collision_mode`=MAKE_UNIQUE/REFERENCE_EXISTING, `filter_glob`:STRING |
| ✅ | `wm.open_mainfile` | Open a Blender file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `load_ui`:BOOLEAN, `use_scripts`:BOOLEAN, `display_file_selector`:BOOLEAN, `state`:INT |
| ✅ | `wm.operator_cheat_sheet` | List all the operators in a text-block, useful for scripting | — |
| ✅ | `wm.operator_defaults` | Set the active operator to its default values | — |
| ✅ | `wm.operator_pie_enum` | (undocumented operator) | `data_path`:STRING, `prop_string`:STRING |
| ✅ | `wm.operator_preset_add` | Add or remove an Operator Preset | `name`:STRING, `remove_name`:BOOLEAN, `remove_active`:BOOLEAN, `operator`:STRING |
| ✅ | `wm.operator_presets_cleanup` | Remove outdated operator properties from presets that may cause problems | `operator`:STRING, `properties`:COLLECTION |
| ✅ | `wm.owner_disable` | Disable add-on for workspace | `owner_id`:STRING |
| ✅ | `wm.owner_enable` | Enable add-on for workspace | `owner_id`:STRING |
| ✅ | `wm.path_open` | Open a path in a file browser | `filepath`:STRING |
| ✅ | `wm.ply_export` | Save the scene to a PLY file | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `forward_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `up_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `global_scale`:FLOAT, `apply_modifiers`:BOOLEAN, `export_selected_objects`:BOOLEAN, `collection`:STRING, `export_uv`:BOOLEAN, `export_normals`:BOOLEAN, `export_colors`=NONE/SRGB/LINEAR, `export_attributes`:BOOLEAN, `export_triangulated_mesh`:BOOLEAN, `ascii_format`:BOOLEAN, `filter_glob`:STRING |
| ✅ | `wm.ply_import` | Import an PLY file as an object | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `global_scale`:FLOAT, `use_scene_unit`:BOOLEAN, `forward_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `up_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `merge_verts`:BOOLEAN, `import_colors`=NONE/SRGB/LINEAR, `import_attributes`:BOOLEAN, `filter_glob`:STRING |
| ✅ | `wm.previews_batch_clear` | Clear selected .blend file's previews | `files`:COLLECTION, `directory`:STRING, `filter_blender`:BOOLEAN, `filter_folder`:BOOLEAN, `use_scenes`:BOOLEAN, `use_collections`:BOOLEAN, `use_objects`:BOOLEAN, `use_intern_data`:BOOLEAN, `use_trusted`:BOOLEAN, `use_backups`:BOOLEAN |
| ✅ | `wm.previews_batch_generate` | Generate selected .blend file's previews | `files`:COLLECTION, `directory`:STRING, `filter_blender`:BOOLEAN, `filter_folder`:BOOLEAN, `use_scenes`:BOOLEAN, `use_collections`:BOOLEAN, `use_objects`:BOOLEAN, `use_intern_data`:BOOLEAN, `use_trusted`:BOOLEAN, `use_backups`:BOOLEAN |
| ✅ | `wm.previews_clear` | Clear data-block previews (only for some types like objects, materials, textures, etc.) | `id_type`=ALL/GEOMETRY/SHADING/SCENE/COLLECTION/OBJECT/MATERIAL/LIGHT/WORLD/TEXTURE/IMAGE |
| ✅ | `wm.previews_ensure` | Ensure data-block previews are available and up-to-date (to be saved in .blend file, only  | — |
| ✅ | `wm.properties_add` | Add your own property to the data-block | `data_path`:STRING |
| ✅ | `wm.properties_context_change` | Jump to a different tab inside the properties editor | `context`:STRING |
| ✅ | `wm.properties_edit` | Change a custom property's type, or adjust how it is displayed in the interface | `data_path`:STRING, `property_name`:STRING, `property_type`=FLOAT/FLOAT_ARRAY/INT/INT_ARRAY/BOOL/BOOL_ARRAY/STRING/DATA_BLOCK/PYTHON, `is_overridable_library`:BOOLEAN, `description`:STRING, `use_soft_limits`:BOOLEAN, `array_length`:INT, `default_int`:INT, `min_int`:INT, `max_int`:INT, `soft_min_int`:INT, `soft_max_int`:INT, `step_int`:INT, `default_bool`:BOOLEAN, `default_float`:FLOAT, `min_float`:FLOAT, `max_float`:FLOAT, `soft_min_float`:FLOAT, `soft_max_float`:FLOAT, `precision`:INT, `step_float`:FLOAT, `subtype`=, `default_string`:STRING, `id_type`=ACTION/ARMATURE/BRUSH/CACHEFILE/CAMERA/COLLECTION/CURVE/CURVES/FONT/GREASEPENCIL/GREASEPENCIL_V3/IMAGE/KEY/LATTICE/LIBRARY/LIGHT/LIGHT_PROBE/LINESTYLE/MASK/MATERIAL/MESH/META/MOVIECLIP/NODETREE/OBJECT/PAINTCURVE/PALETTE/PARTICLE/POINTCLOUD/SCENE/SCREEN/SOUND/SPEAKER/TEXT/TEXTURE/VOLUME/WINDOWMANAGER/WORKSPACE/WORLD, `eval_string`:STRING |
| ✅ | `wm.properties_edit_value` | Edit the value of a custom property | `data_path`:STRING, `property_name`:STRING, `eval_string`:STRING |
| ✅ | `wm.properties_remove` | Internal use (edit a property data_path) | `data_path`:STRING, `property_name`:STRING |
| ✅ | `wm.quit_blender` | Quit Blender | — |
| ✅ | `wm.radial_control` | Set some size property (e.g. brush size) with mouse wheel | `data_path_primary`:STRING, `data_path_secondary`:STRING, `use_secondary`:STRING, `rotation_path`:STRING, `color_path`:STRING, `fill_color_path`:STRING, `fill_color_override_path`:STRING, `fill_color_override_test_path`:STRING, `zoom_path`:STRING, `image_id`:STRING, `secondary_tex`:BOOLEAN, `release_confirm`:BOOLEAN |
| ✅ | `wm.read_factory_settings` | Load factory default startup file and preferences. To make changes permanent, use "Save St | `use_factory_startup_app_template_only`:BOOLEAN, `app_template`:STRING, `use_empty`:BOOLEAN |
| ✅ | `wm.read_factory_userpref` | Load factory default preferences. To make changes to preferences permanent, use "Save Pref | `use_factory_startup_app_template_only`:BOOLEAN |
| ✅ | `wm.read_history` | Reloads history and bookmarks | — |
| ✅ | `wm.read_homefile` | Open the default file | `filepath`:STRING, `load_ui`:BOOLEAN, `use_splash`:BOOLEAN, `use_factory_startup`:BOOLEAN, `use_factory_startup_app_template_only`:BOOLEAN, `app_template`:STRING, `use_empty`:BOOLEAN |
| ✅ | `wm.read_userpref` | Load last saved preferences | — |
| ✅ | `wm.recover_auto_save` | Open an automatically saved file to recover it | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `use_scripts`:BOOLEAN |
| ✅ | `wm.recover_last_session` | Open the last closed file ("quit.blend") | `use_scripts`:BOOLEAN |
| ❌ | `wm.redraw_timer` | Simple redraw timer to test the speed of updating the interface | `type`=DRAW/DRAW_SWAP/DRAW_WIN/DRAW_WIN_SWAP/ANIM_STEP/ANIM_PLAY/UNDO, `iterations`:INT, `time_limit`:FLOAT |
| ❌ | `wm.revert_mainfile` | Reload the saved file | `use_scripts`:BOOLEAN |
| ✅ | `wm.save_as_mainfile` | Save the current file in the desired location | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `compress`:BOOLEAN, `relative_remap`:BOOLEAN, `copy`:BOOLEAN, `show_save_modified_images_dialog`:BOOLEAN |
| ✅ | `wm.save_auto_save` | Create an autosave in the temp directory for the current file | — |
| ✅ | `wm.save_homefile` | Make the current file the default startup file | — |
| ✅ | `wm.save_mainfile` | Save the current Blender file | `filepath`:STRING, `hide_props_region`:BOOLEAN, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `compress`:BOOLEAN, `relative_remap`:BOOLEAN, `exit`:BOOLEAN, `incremental`:BOOLEAN, `show_save_modified_images_dialog`:BOOLEAN |
| ✅ | `wm.save_userpref` | Make the current preferences default | — |
| ✅ | `wm.search_menu` | Pop-up a search over all menus in the current context | — |
| ✅ | `wm.search_operator` | Pop-up a search over all available operators in current context | — |
| ✅ | `wm.search_single_menu` | Pop-up a search for a menu in current context | `menu_idname`:STRING, `initial_query`:STRING |
| ✅ | `wm.set_stereo_3d` | Toggle 3D stereo support for current window (or change the display mode) | `display_mode`=ANAGLYPH/INTERLACE/TIMESEQUENTIAL/SIDEBYSIDE/TOPBOTTOM, `anaglyph_type`=RED_CYAN/GREEN_MAGENTA/YELLOW_BLUE, `interlace_type`=ROW_INTERLEAVED/COLUMN_INTERLEAVED/CHECKERBOARD_INTERLEAVED, `use_interlace_swap`:BOOLEAN, `use_sidebyside_crosseyed`:BOOLEAN |
| ✅ | `wm.set_working_color_space` | Change the working color space of all colors in this blend file | `convert_colors`:BOOLEAN, `working_space`= |
| ✅ | `wm.splash` | Open the splash screen with release info | — |
| ✅ | `wm.splash_about` | Open a window with information about Blender | — |
| ✅ | `wm.stl_export` | Save the scene to an STL file | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `ascii_format`:BOOLEAN, `use_batch`:BOOLEAN, `export_selected_objects`:BOOLEAN, `collection`:STRING, `global_scale`:FLOAT, `use_scene_unit`:BOOLEAN, `forward_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `up_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `apply_modifiers`:BOOLEAN, `evaluation_mode`=DAG_EVAL_RENDER/DAG_EVAL_VIEWPORT, `filter_glob`:STRING |
| ✅ | `wm.stl_import` | Import an STL file as an object | `filepath`:STRING, `directory`:STRING, `files`:COLLECTION, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `global_scale`:FLOAT, `use_scene_unit`:BOOLEAN, `use_facet_normal`:BOOLEAN, `forward_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `up_axis`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `use_mesh_validate`:BOOLEAN, `filter_glob`:STRING |
| ✅ | `wm.sysinfo` | Generate system information, saved into a text file | `filepath`:STRING |
| ✅ | `wm.tool_set_by_brush_type` | Look up the most appropriate tool for the given brush type and activate that | `brush_type`:STRING, `space_type`=EMPTY/VIEW_3D/IMAGE_EDITOR/NODE_EDITOR/SEQUENCE_EDITOR/CLIP_EDITOR/DOPESHEET_EDITOR/GRAPH_EDITOR/NLA_EDITOR/TEXT_EDITOR/CONSOLE/INFO/TOPBAR/STATUSBAR/OUTLINER/PROPERTIES/FILE_BROWSER/SPREADSHEET/PREFERENCES |
| ✅ | `wm.tool_set_by_id` | Set the tool by name (for key-maps) | `name`:STRING, `cycle`:BOOLEAN, `as_fallback`:BOOLEAN, `space_type`=EMPTY/VIEW_3D/IMAGE_EDITOR/NODE_EDITOR/SEQUENCE_EDITOR/CLIP_EDITOR/DOPESHEET_EDITOR/GRAPH_EDITOR/NLA_EDITOR/TEXT_EDITOR/CONSOLE/INFO/TOPBAR/STATUSBAR/OUTLINER/PROPERTIES/FILE_BROWSER/SPREADSHEET/PREFERENCES |
| ✅ | `wm.tool_set_by_index` | Set the tool by index (for key-maps) | `index`:INT, `cycle`:BOOLEAN, `expand`:BOOLEAN, `as_fallback`:BOOLEAN, `space_type`=EMPTY/VIEW_3D/IMAGE_EDITOR/NODE_EDITOR/SEQUENCE_EDITOR/CLIP_EDITOR/DOPESHEET_EDITOR/GRAPH_EDITOR/NLA_EDITOR/TEXT_EDITOR/CONSOLE/INFO/TOPBAR/STATUSBAR/OUTLINER/PROPERTIES/FILE_BROWSER/SPREADSHEET/PREFERENCES |
| ❌ | `wm.toolbar` | (undocumented operator) | — |
| ❌ | `wm.toolbar_fallback_pie` | (undocumented operator) | — |
| ✅ | `wm.toolbar_prompt` | Leader key like functionality for accessing tools | — |
| ✅ | `wm.url_open` | Open a website in the web browser | `url`:STRING |
| ✅ | `wm.url_open_preset` | Open a preset website in the web browser | `type`= |
| ✅ | `wm.usd_export` | Export current scene in a USD archive | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `filter_glob`:STRING, `selected_objects_only`:BOOLEAN, `collection`:STRING, `export_animation`:BOOLEAN, `incremental_frames`:INT, `export_hair`:BOOLEAN, `export_uvmaps`:BOOLEAN, `rename_uvmaps`:BOOLEAN, `export_mesh_colors`:BOOLEAN, `export_normals`:BOOLEAN, `export_materials`:BOOLEAN, `export_subdivision`=IGNORE/TESSELLATE/BEST_MATCH, `export_armatures`:BOOLEAN, `only_deform_bones`:BOOLEAN, `export_shapekeys`:BOOLEAN, `use_instancing`:BOOLEAN, `evaluation_mode`=RENDER/VIEWPORT, `generate_preview_surface`:BOOLEAN, `generate_materialx_network`:BOOLEAN, `convert_orientation`:BOOLEAN, `export_global_forward_selection`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `export_global_up_selection`=X/Y/Z/NEGATIVE_X/NEGATIVE_Y/NEGATIVE_Z, `export_textures_mode`=KEEP/PRESERVE/NEW, `overwrite_textures`:BOOLEAN, `relative_paths`:BOOLEAN, `xform_op_mode`=TRS/TOS/MAT, `root_prim_path`:STRING, `export_custom_properties`:BOOLEAN, `custom_properties_namespace`:STRING, `accessibility_label`:STRING, `accessibility_description`:STRING, `author_blender_name`:BOOLEAN, `convert_world_material`:BOOLEAN, `allow_unicode`:BOOLEAN, `export_meshes`:BOOLEAN, `export_lights`:BOOLEAN, `export_cameras`:BOOLEAN, `export_curves`:BOOLEAN, `export_points`:BOOLEAN, `export_volumes`:BOOLEAN, `triangulate_meshes`:BOOLEAN, `quad_method`=BEAUTY/FIXED/FIXED_ALTERNATE/SHORTEST_DIAGONAL/LONGEST_DIAGONAL, `ngon_method`=BEAUTY/CLIP, `usdz_downscale_size`=KEEP/256/512/1024/2048/4096/CUSTOM, `usdz_downscale_custom_size`:INT, `merge_parent_xform`:BOOLEAN, `convert_scene_units`=METERS/KILOMETERS/CENTIMETERS/MILLIMETERS/INCHES/FEET/YARDS/CUSTOM, `meters_per_unit`:FLOAT |
| ✅ | `wm.usd_import` | Import USD stage into current scene | `filepath`:STRING, `check_existing`:BOOLEAN, `filter_blender`:BOOLEAN, `filter_backup`:BOOLEAN, `filter_image`:BOOLEAN, `filter_movie`:BOOLEAN, `filter_python`:BOOLEAN, `filter_font`:BOOLEAN, `filter_sound`:BOOLEAN, `filter_text`:BOOLEAN, `filter_archive`:BOOLEAN, `filter_btx`:BOOLEAN, `filter_alembic`:BOOLEAN, `filter_usd`:BOOLEAN, `filter_obj`:BOOLEAN, `filter_volume`:BOOLEAN, `filter_folder`:BOOLEAN, `filter_blenlib`:BOOLEAN, `filemode`:INT, `relative_path`:BOOLEAN, `display_type`=DEFAULT/LIST_VERTICAL/LIST_HORIZONTAL/THUMBNAIL, `sort_method`=, `filter_glob`:STRING, `scale`:FLOAT, `set_frame_range`:BOOLEAN, `import_cameras`:BOOLEAN, `import_curves`:BOOLEAN, `import_lights`:BOOLEAN, `import_materials`:BOOLEAN, `import_meshes`:BOOLEAN, `import_volumes`:BOOLEAN, `import_shapes`:BOOLEAN, `import_skeletons`:BOOLEAN, `import_blendshapes`:BOOLEAN, `import_points`:BOOLEAN, `import_subdivision`:BOOLEAN, `support_scene_instancing`:BOOLEAN, `import_visible_only`:BOOLEAN, `create_collection`:BOOLEAN, `read_mesh_uvs`:BOOLEAN, `read_mesh_colors`:BOOLEAN, `read_mesh_attributes`:BOOLEAN, `prim_path_mask`:STRING, `import_guide`:BOOLEAN, `import_proxy`:BOOLEAN, `import_render`:BOOLEAN, `import_all_materials`:BOOLEAN, `import_usd_preview`:BOOLEAN, `set_material_blend`:BOOLEAN, `light_intensity_scale`:FLOAT, `mtl_purpose`=MTL_ALL_PURPOSE/MTL_PREVIEW/MTL_FULL, `mtl_name_collision_mode`=MAKE_UNIQUE/REFERENCE_EXISTING, `import_textures_mode`=IMPORT_NONE/IMPORT_PACK/IMPORT_COPY, `import_textures_dir`:STRING, `tex_name_collision_mode`=USE_EXISTING/OVERWRITE, `property_import_mode`=NONE/USER/ALL, `validate_meshes`:BOOLEAN, `create_world_material`:BOOLEAN, `import_defined_only`:BOOLEAN, `merge_parent_xform`:BOOLEAN, `apply_unit_conversion_scale`:BOOLEAN |
| ✅ | `wm.window_close` | Close the current window | — |
| ✅ | `wm.window_fullscreen_toggle` | Toggle the current window full-screen | — |
| ❌ | `wm.window_new` | Create a new window | — |
| ❌ | `wm.window_new_main` | Create a new main window with its own workspace and scene selection | — |
| ❌ | `wm.xr_navigation_fly` | Move/turn relative to the VR viewer or controller | `mode`=FORWARD/BACK/LEFT/RIGHT/UP/DOWN/TURNLEFT/TURNRIGHT/VIEWER_FORWARD/VIEWER_BACK/VIEWER_LEFT/VIEWER_RIGHT/CONTROLLER_FORWARD, `snap_turn_threshold`:FLOAT, `lock_location_z`:BOOLEAN, `lock_direction`:BOOLEAN, `speed_frame_based`:BOOLEAN, `turn_speed_factor`:FLOAT, `fly_speed_factor`:FLOAT, `speed_interpolation0`:FLOAT, `speed_interpolation1`:FLOAT, `alt_mode`=FORWARD/BACK/LEFT/RIGHT/UP/DOWN/TURNLEFT/TURNRIGHT/VIEWER_FORWARD/VIEWER_BACK/VIEWER_LEFT/VIEWER_RIGHT/CONTROLLER_FORWARD, `alt_lock_location_z`:BOOLEAN, `alt_lock_direction`:BOOLEAN |
| ❌ | `wm.xr_navigation_grab` | Navigate the VR scene by grabbing with controllers | `lock_location`:BOOLEAN, `lock_location_z`:BOOLEAN, `lock_rotation`:BOOLEAN, `lock_rotation_z`:BOOLEAN, `lock_scale`:BOOLEAN |
| ❌ | `wm.xr_navigation_reset` | Reset VR navigation deltas relative to session base pose | `location`:BOOLEAN, `rotation`:BOOLEAN, `scale`:BOOLEAN |
| ❌ | `wm.xr_navigation_swap_hands` | Swap VR navigation controls between left / right controllers | — |
| ❌ | `wm.xr_navigation_teleport` | Set VR viewer location to controller raycast hit location | `selectable_only`:BOOLEAN, `force`:FLOAT, `range`:FLOAT, `ray_line_width`:FLOAT, `destination_indicator_width`:FLOAT, `hit_color`:FLOAT, `miss_color`:FLOAT, `fallback_color`:FLOAT |
| ❌ | `wm.xr_session_toggle` | Open a view for use with virtual reality headsets, or close it if already opened | — |

### `workspace` — 8개 (✅ 8 / ⚠ 0 / ❌ 0)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ✅ | `workspace.add` | Add a new workspace by duplicating the current one or appending one from the user configur | — |
| ✅ | `workspace.append_activate` | Append a workspace and make it the active one in the current window | `idname`:STRING, `filepath`:STRING |
| ✅ | `workspace.delete` | Delete the active workspace | — |
| ✅ | `workspace.delete_all_others` | Delete all workspaces except this one | — |
| ✅ | `workspace.duplicate` | Add a new workspace | — |
| ✅ | `workspace.reorder_to_back` | Reorder workspace to be last in the list | — |
| ✅ | `workspace.reorder_to_front` | Reorder workspace to be first in the list | — |
| ✅ | `workspace.scene_pin_toggle` | Remember the last used scene for the current workspace and switch to it whenever this work | — |

### `world` — 2개 (✅ 1 / ⚠ 0 / ❌ 1)

| | 오퍼레이터 | 설명 | 인자 |
|---|---|---|---|
| ❌ | `world.convert_volume_to_mesh` | Convert the volume of a world to a mesh. The world's volume used to be rendered by EEVEE L | — |
| ✅ | `world.new` | Create a new world Data-Block | — |

**소계: ✅ 625 / ⚠ 52 / ❌ 1821**

### 1.1 그룹별 고득점 랭킹 — 뭘 배워야 하나

개수가 아니라 **도달 가능한 비율** 로 정렬했다. 비율이 높고 개수까지 있는 그룹이 실제로 쓸모 있는 영역이다. 비율이 0% 인 그룹은 아예 건드리지 마라.

| 그룹 | 도달가능 | 전체 | 비율 | 판단 |
|---|---:|---:|---:|---|
| `fluid` | 14 | 14 | 100% | **핵심** — 반드시 익혀라 |
| `workspace` | 8 | 8 | 100% | **핵심** — 반드시 익혀라 |
| `boid` | 8 | 8 | 100% | **핵심** — 반드시 익혀라 |
| `surface` | 6 | 6 | 100% | **핵심** — 반드시 익혀라 |
| `dpaint` | 5 | 5 | 100% | **핵심** — 반드시 익혀라 |
| `cachefile` | 5 | 5 | 100% | **핵심** — 반드시 익혀라 |
| `uilist` | 3 | 3 | 100% | **핵심** — 반드시 익혀라 |
| `script` | 3 | 3 | 100% | **핵심** — 반드시 익혀라 |
| `material` | 3 | 3 | 100% | **핵심** — 반드시 익혀라 |
| `import_scene` | 2 | 2 | 100% | **핵심** — 반드시 익혀라 |
| `export_scene` | 2 | 2 | 100% | **핵심** — 반드시 익혀라 |
| `camera` | 2 | 2 | 100% | **핵심** — 반드시 익혀라 |
| `text_editor` | 1 | 1 | 100% | **핵심** — 반드시 익혀라 |
| `import_curve` | 1 | 1 | 100% | **핵심** — 반드시 익혀라 |
| `import_anim` | 1 | 1 | 100% | **핵심** — 반드시 익혀라 |
| `cloth` | 1 | 1 | 100% | **핵심** — 반드시 익혀라 |
| `render` | 15 | 16 | 94% | **핵심** — 반드시 익혀라 |
| `wm` | 104 | 117 | 89% | **핵심** — 반드시 익혀라 |
| `extensions` | 27 | 32 | 84% | **핵심** — 반드시 익혀라 |
| `scene` | 32 | 39 | 82% | **핵심** — 반드시 익혀라 |
| `preferences` | 30 | 37 | 81% | **핵심** — 반드시 익혀라 |
| `collection` | 9 | 12 | 75% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `texture` | 3 | 4 | 75% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `object` | 187 | 250 | 75% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `constraint` | 13 | 18 | 72% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `sound` | 5 | 7 | 71% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `cycles` | 2 | 3 | 67% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `screen` | 23 | 43 | 53% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `world` | 1 | 2 | 50% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `geometry` | 4 | 9 | 44% | 유용 — 필요할 때 위 표에서 찾고 ❌ 항목만 피해라 |
| `transform` | 9 | 27 | 33% | 드묾 — data API 로 대체되는 경우가 많다 |
| `buttons` | 2 | 6 | 33% | 드묾 — data API 로 대체되는 경우가 많다 |
| `particle` | 12 | 37 | 32% | 드묾 — data API 로 대체되는 경우가 많다 |
| `rigidbody` | 4 | 13 | 31% | 드묾 — data API 로 대체되는 경우가 많다 |
| `ed` | 4 | 13 | 31% | 드묾 — data API 로 대체되는 경우가 많다 |
| `ptcache` | 2 | 7 | 29% | 드묾 — data API 로 대체되는 경우가 많다 |
| `file` | 11 | 40 | 28% | 드묾 — data API 로 대체되는 경우가 많다 |
| `sculpt_curves` | 1 | 4 | 25% | 드묾 — data API 로 대체되는 경우가 많다 |
| `anim` | 16 | 65 | 25% | 드묾 — data API 로 대체되는 경우가 많다 |
| `brush` | 2 | 11 | 18% | 드묾 — data API 로 대체되는 경우가 많다 |
| `font` | 4 | 23 | 17% | 드묾 — data API 로 대체되는 경우가 많다 |
| `image` | 8 | 49 | 16% | 드묾 — data API 로 대체되는 경우가 많다 |
| `palette` | 1 | 7 | 14% | 드묾 — data API 로 대체되는 경우가 많다 |
| `info` | 1 | 7 | 14% | 드묾 — data API 로 대체되는 경우가 많다 |
| `ui` | 5 | 38 | 13% | 드묾 — data API 로 대체되는 경우가 많다 |
| `view3d` | 8 | 68 | 12% | 드묾 — data API 로 대체되는 경우가 많다 |
| `curve` | 6 | 51 | 12% | 드묾 — data API 로 대체되는 경우가 많다 |
| `paint` | 6 | 55 | 11% | 드묾 — data API 로 대체되는 경우가 많다 |
| `mesh` | 17 | 167 | 10% | 드묾 — data API 로 대체되는 경우가 많다 |
| `pose` | 5 | 51 | 10% | 드묾 — data API 로 대체되는 경우가 많다 |
| `curves` | 3 | 31 | 10% | 드묾 — data API 로 대체되는 경우가 많다 |
| `text` | 3 | 43 | 7% | 드묾 — data API 로 대체되는 경우가 많다 |
| `clip` | 6 | 92 | 7% | 드묾 — data API 로 대체되는 경우가 많다 |
| `grease_pencil` | 7 | 123 | 6% | 드묾 — data API 로 대체되는 경우가 많다 |
| `node` | 8 | 182 | 4% | 드묾 — data API 로 대체되는 경우가 많다 |
| `uv` | 2 | 55 | 4% | 드묾 — data API 로 대체되는 경우가 많다 |
| `outliner` | 2 | 73 | 3% | 드묾 — data API 로 대체되는 경우가 많다 |
| `nla` | 1 | 39 | 3% | 드묾 — data API 로 대체되는 경우가 많다 |
| `sequencer` | 1 | 111 | 1% | 드묾 — data API 로 대체되는 경우가 많다 |
| `graph` | 0 | 67 | 0% | **배우지 마라** — UI 전용 |
| `armature` | 0 | 49 | 0% | **배우지 마라** — UI 전용 |
| `mask` | 0 | 40 | 0% | **배우지 마라** — UI 전용 |
| `sculpt` | 0 | 39 | 0% | **배우지 마라** — UI 전용 |
| `action` | 0 | 37 | 0% | **배우지 마라** — UI 전용 |
| `console` | 0 | 21 | 0% | **배우지 마라** — UI 전용 |
| `asset` | 0 | 21 | 0% | **배우지 마라** — UI 전용 |
| `view2d` | 0 | 14 | 0% | **배우지 마라** — UI 전용 |
| `marker` | 0 | 11 | 0% | **배우지 마라** — UI 전용 |
| `poselib` | 0 | 9 | 0% | **배우지 마라** — UI 전용 |
| `paintcurve` | 0 | 8 | 0% | **배우지 마라** — UI 전용 |
| `mball` | 0 | 8 | 0% | **배우지 마라** — UI 전용 |
| `lattice` | 0 | 8 | 0% | **배우지 마라** — UI 전용 |
| `spreadsheet` | 0 | 7 | 0% | **배우지 마라** — UI 전용 |
| `pointcloud` | 0 | 7 | 0% | **배우지 마라** — UI 전용 |
| `gpencil` | 0 | 7 | 0% | **배우지 마라** — UI 전용 |
| `gizmogroup` | 0 | 2 | 0% | **배우지 마라** — UI 전용 |
| `export_anim` | 0 | 1 | 0% | **배우지 마라** — UI 전용 |

## 2. 노드 타입 전수

총 **568** 개. 그중 **543** 개를 실제로 인스턴스화해 **입력/출력 소켓 이름과 타입** 을 뽑았다. 인스턴스화가 실패한 25 개는 `⚠` 로 표시되며, 그 자체가 "이 노드는 스크립트로 다루기 어렵다" 는 신호다.

### Compositor 노드 — 92개

| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |
|---|---|---|---|---|
| ⚠ | `CompositorNode` |  | RuntimeError: Error: Node type CompositorNode undefined
 | — |
| ✅ | `CompositorNodeAlphaOver` | Alpha Over | Background:Color, Foreground:Color, Factor:FloatFactor, Type:Menu, Straight Alpha:Bool | Image:Color |
| ✅ | `CompositorNodeAntiAliasing` | Anti-Aliasing | Image:Color, Threshold:FloatFactor, Contrast Limit:Float, Corner Rounding:FloatFactor | Image:Color |
| ✅ | `CompositorNodeBilateralblur` | Bilateral Blur | Image:Color, Determinator:Color, Size:IntPixel, Threshold:Float | Image:Color |
| ✅ | `CompositorNodeBlankImage` | Blank Image | Color:Color, Size:IntVectorPixel2D | Image:Color |
| ✅ | `CompositorNodeBlur` | Blur | Image:Color, Size:VectorPixel2D, Type:Menu, Extend Bounds:Bool, Separable:Bool | Image:Color |
| ✅ | `CompositorNodeBokehBlur` | Bokeh Blur | Image:Color, Bokeh:Color, Size:FloatPixel, Mask:Float, Extend Bounds:Bool | Image:Color |
| ✅ | `CompositorNodeBokehImage` | Bokeh Image | Flaps:Int, Angle:FloatAngle, Roundness:FloatFactor, Catadioptric Size:FloatFactor, Color Shift:FloatFactor | Image:Color |
| ✅ | `CompositorNodeBoxMask` | Box Mask | Operation:Menu, Mask:FloatFactor, Value:FloatFactor, Position:VectorFactor2D, Size:VectorFactor2D, Rotation:FloatAngle | Mask:Float |
| ✅ | `CompositorNodeBrightContrast` | Brightness/Contrast | Image:Color, Brightness:Float, Contrast:Float | Image:Color |
| ✅ | `CompositorNodeChannelMatte` | Channel Key | Image:Color, Minimum:FloatFactor, Maximum:FloatFactor, Color Space:Menu, RGB Key Channel:Menu, HSV Key Channel:Menu, YUV Key Channel:Menu, YCbCr Key Channel:Menu, Limit Method:Menu, RGB Limit Channel:Menu, HSV Limit Channel:Menu, YUV Limit Channel:Menu, YCbCr Limit Channel:Menu | Image:Color, Matte:Float |
| ✅ | `CompositorNodeChromaMatte` | Chroma Key | Image:Color, Key Color:Color, Minimum:FloatAngle, Maximum:FloatAngle, Falloff:FloatFactor | Image:Color, Matte:Float |
| ✅ | `CompositorNodeColorBalance` | Color Balance | Image:Color, Factor:FloatFactor, Type:Menu, Lift:FloatFactor, Lift:Color, Gamma:FloatFactor, Gamma:Color, Gain:FloatFactor, Gain:Color, Offset:FloatFactor, Offset:Color, Power:FloatFactor, Power:Color, Slope:FloatFactor, Slope:Color, Temperature:FloatColorTemperature, Tint:FloatFactor, Temperature:FloatColorTemperature, Tint:FloatFactor | Image:Color |
| ✅ | `CompositorNodeColorCorrection` | Color Correction | Image:Color, Mask:Float, Saturation:FloatFactor, Contrast:FloatFactor, Gamma:FloatFactor, Gain:FloatFactor, Offset:FloatFactor, Saturation:FloatFactor, Contrast:FloatFactor, Gamma:FloatFactor, Gain:FloatFactor, Offset:FloatFactor, Saturation:FloatFactor, Contrast:FloatFactor, Gamma:FloatFactor, Gain:FloatFactor, Offset:FloatFactor, Saturation:FloatFactor, Contrast:FloatFactor, Gamma:FloatFactor, Gain:FloatFactor, Offset:FloatFactor, Midtones Start:FloatFactor, Midtones End:FloatFactor, Red:Bool, Green:Bool, Blue:Bool | Image:Color |
| ✅ | `CompositorNodeColorMatte` | Color Key | Image:Color, Key Color:Color, Hue:FloatFactor, Saturation:FloatFactor, Value:FloatFactor | Image:Color, Matte:Float |
| ✅ | `CompositorNodeColorSpill` | Color Spill | Image:Color, Factor:FloatFactor, Spill Channel:Menu, Limit Method:Menu, Limit Channel:Menu, Limit Strength:FloatFactor, Use Spill Strength:Bool, Strength:Color | Image:Color |
| ✅ | `CompositorNodeCombineColor` | Combine Color | Red:FloatFactor, Green:FloatFactor, Blue:FloatFactor, Alpha:FloatFactor | Image:Color |
| ✅ | `CompositorNodeConvertColorSpace` | Convert Colorspace | Image:Color | Image:Color |
| ✅ | `CompositorNodeConvertToDisplay` | Convert to Display | Image:Color, Invert:Bool | Image:Color |
| ✅ | `CompositorNodeConvolve` | Convolve | Image:Color, Kernel Data Type:Menu, Kernel:Float, Kernel:Color, Normalize Kernel:Bool | Image:Color |
| ✅ | `CompositorNodeCornerPin` | Corner Pin | Image:Color, Upper Left:VectorFactor2D, Upper Right:VectorFactor2D, Lower Left:VectorFactor2D, Lower Right:VectorFactor2D, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color, Plane:Float |
| ✅ | `CompositorNodeCrop` | Crop | Image:Color, X:Int, Y:Int, Width:IntPixel, Height:IntPixel, Alpha Crop:Bool | Image:Color |
| ✅ | `CompositorNodeCryptomatte` | Cryptomatte (Legacy) | Image:Color, Crypto 00:Color, Crypto 01:Color, Crypto 02:Color | Image:Color, Matte:Float, Pick:Color |
| ✅ | `CompositorNodeCryptomatteV2` | Cryptomatte | Image:Color | Image:Color, Matte:Float, Pick:Color |
| ✅ | `CompositorNodeCurveRGB` | RGB Curves | Image:Color, Factor:FloatFactor, Black Level:Color, White Level:Color | Image:Color |
| ⚠ | `CompositorNodeCustomGroup` |  | RuntimeError: Error: Node type CompositorNodeCustomGroup und | — |
| ✅ | `CompositorNodeDBlur` | Directional Blur | Image:Color, Samples:Int, Center:VectorFactor2D, Rotation:FloatAngle, Scale:Float, Amount:FloatFactor, Direction:FloatAngle | Image:Color |
| ✅ | `CompositorNodeDefocus` | Defocus | Image:Color, Z:Float | Image:Color |
| ✅ | `CompositorNodeDenoise` | Denoise | Image:Color, Albedo:Color, Normal:Vector, HDR:Bool, Prefilter:Menu, Quality:Menu | Image:Color |
| ✅ | `CompositorNodeDespeckle` | Despeckle | Image:Color, Factor:FloatFactor, Color Threshold:Float, Neighbor Threshold:FloatFactor | Image:Color |
| ✅ | `CompositorNodeDiffMatte` | Difference Key | Image 1:Color, Image 2:Color, Tolerance:FloatFactor, Falloff:FloatFactor | Image:Color, Matte:Float |
| ✅ | `CompositorNodeDilateErode` | Dilate/Erode | Mask:Float, Size:IntPixel, Type:Menu, Falloff Size:FloatPixel, Falloff:Menu | Mask:Float |
| ✅ | `CompositorNodeDisplace` | Displace | Image:Color, Displacement:Vector2D, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ✅ | `CompositorNodeDistanceMatte` | Distance Key | Image:Color, Key Color:Color, Color Space:Menu, Tolerance:FloatFactor, Falloff:FloatFactor | Image:Color, Matte:Float |
| ✅ | `CompositorNodeDoubleEdgeMask` | Double Edge Mask | Outer Mask:Float, Inner Mask:Float, Image Edges:Bool, Only Inside Outer:Bool | Mask:Float |
| ✅ | `CompositorNodeEllipseMask` | Ellipse Mask | Operation:Menu, Mask:FloatFactor, Value:FloatFactor, Position:VectorFactor2D, Size:VectorFactor2D, Rotation:FloatAngle | Mask:Float |
| ✅ | `CompositorNodeExposure` | Exposure | Image:Color, Exposure:Float | Image:Color |
| ✅ | `CompositorNodeFilter` | Filter | Image:Color, Factor:FloatFactor, Type:Menu | Image:Color |
| ✅ | `CompositorNodeFlip` | Flip | Image:Color, Flip X:Bool, Flip Y:Bool | Image:Color |
| ⚠ | `CompositorNodeGamma` |  | RuntimeError: Error: Node type CompositorNodeGamma undefined | — |
| ✅ | `CompositorNodeGlare` | Glare | Image:Color, Type:Menu, Quality:Menu, Threshold:Float, Smoothness:FloatFactor, Clamp:Bool, Maximum:Float, Strength:FloatFactor, Saturation:FloatFactor, Tint:Color, Size:FloatFactor, Streaks:Int, Streaks Angle:FloatAngle, Iterations:Int, Fade:FloatFactor, Color Modulation:FloatFactor, Diagonal:Bool, Sun Position:VectorFactor2D, Jitter:FloatFactor, Kernel Data Type:Menu, Kernel:Float, Kernel:Color | Image:Color, Glare:Color, Highlights:Color |
| ✅ | `CompositorNodeGroup` | Group | — | — |
| ✅ | `CompositorNodeHueCorrect` | Hue Correct | Image:Color, Factor:FloatFactor | Image:Color |
| ✅ | `CompositorNodeHueSat` | Hue/Saturation/Value | Image:Color, Hue:FloatFactor, Saturation:FloatFactor, Value:FloatFactor, Factor:FloatFactor | Image:Color |
| ✅ | `CompositorNodeIDMask` | ID Mask | ID value:Float, Index:Int, Anti-Alias:Bool | Alpha:Float |
| ✅ | `CompositorNodeImage` | Image | — | Image:Color, Alpha:Float |
| ✅ | `CompositorNodeImageCoordinates` | Image Coordinates | Image:Color | Uniform:Vector2D, Normalized:Vector2D, Pixel:IntVector2D |
| ✅ | `CompositorNodeImageInfo` | Image Info | Image:Color | Dimensions:IntVector2D, Resolution:IntVector2D, Location:Vector2D, Rotation:Float, Scale:Vector2D |
| ✅ | `CompositorNodeInpaint` | Inpaint | Image:Color, Size:IntPixel | Image:Color |
| ✅ | `CompositorNodeInvert` | Invert Color | Color:Color, Factor:FloatFactor, Invert Color:Bool, Invert Alpha:Bool | Color:Color |
| ✅ | `CompositorNodeKeying` | Keying | Image:Color, Key Color:Color, Blur Size:IntPixel, Balance:FloatFactor, Black Level:FloatFactor, White Level:FloatFactor, Size:IntPixel, Tolerance:FloatFactor, Garbage Matte:FloatFactor, Core Matte:FloatFactor, Blur Size:IntPixel, Dilate Size:IntPixel, Feather Size:IntPixel, Feather Falloff:Menu, Strength:FloatFactor, Balance:FloatFactor | Image:Color, Matte:Float, Edges:Float |
| ✅ | `CompositorNodeKeyingScreen` | Keying Screen | Smoothness:FloatFactor | Screen:Color |
| ✅ | `CompositorNodeKuwahara` | Kuwahara | Image:Color, Size:FloatPixel, Type:Menu, Uniformity:Int, Sharpness:FloatFactor, Eccentricity:FloatFactor, High Precision:Bool | Image:Color |
| ✅ | `CompositorNodeLensdist` | Lens Distortion | Image:Color, Type:Menu, Distortion:FloatFactor, Dispersion:FloatFactor, Jitter:Bool, Fit:Bool | Image:Color |
| ✅ | `CompositorNodeLevels` | Levels | Image:Color, Channel:Menu | Mean:Float, Standard Deviation:Float, Minimum:Float, Maximum:Float |
| ✅ | `CompositorNodeLumaMatte` | Luminance Key | Image:Color, Minimum:FloatFactor, Maximum:FloatFactor | Image:Color, Matte:Float |
| ✅ | `CompositorNodeMapUV` | Map UV | Image:Color, UV:Vector, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ✅ | `CompositorNodeMask` | Mask | Size Source:Menu, Size X:IntPixel, Size Y:IntPixel, Feather:Bool, Motion Blur:Bool, Samples:Int, Shutter:FloatFactor | Mask:Float |
| ✅ | `CompositorNodeMaskToSDF` | Mask To SDF | Mask:Bool | SDF:Float, Nearest Pixel:IntVector2D |
| ✅ | `CompositorNodeMovieClip` | Movie Clip | — | Image:Color, Alpha:Float, Offset X:Float, Offset Y:Float, Scale:Float, Angle:Float |
| ✅ | `CompositorNodeMovieDistortion` | Movie Distortion | Image:Color, Type:Menu | Image:Color |
| ✅ | `CompositorNodeNormal` | Normal | — | Normal:VectorDirection |
| ✅ | `CompositorNodeNormalize` | Normalize | Value:Float | Value:Float |
| ✅ | `CompositorNodeOutputFile` | File Output | :Virtual | — |
| ✅ | `CompositorNodePixelate` | Pixelate | Color:Color, Size:IntPixel | Color:Color |
| ✅ | `CompositorNodePlaneTrackDeform` | Plane Track Deform | Image:Color, Motion Blur:Bool, Samples:Int, Shutter:FloatFactor | Image:Color, Plane:Float |
| ✅ | `CompositorNodePosterize` | Posterize | Image:Color, Steps:Float | Image:Color |
| ✅ | `CompositorNodePremulKey` | Alpha Convert | Image:Color, Type:Menu | Image:Color |
| ✅ | `CompositorNodeRGB` | Color | — | Color:Color |
| ✅ | `CompositorNodeRGBToBW` | RGB to BW | Image:Color | Val:Float |
| ✅ | `CompositorNodeRLayers` | Render Layers | — | Image:Color, Alpha:Float |
| ✅ | `CompositorNodeRelativeToPixel` | Relative To Pixel | Value:VectorFactor2D, Value:FloatFactor, Image:Color | Value:Float, Value:Vector2D |
| ✅ | `CompositorNodeRotate` | Rotate | Image:Color, Angle:FloatAngle, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ✅ | `CompositorNodeScale` | Scale | Image:Color, Type:Menu, X:Float, Y:Float, Frame Type:Menu, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ✅ | `CompositorNodeSceneTime` | Scene Time | — | Seconds:Float, Frame:Float |
| ✅ | `CompositorNodeSeparateColor` | Separate Color | Image:Color | Red:Float, Green:Float, Blue:Float, Alpha:Float |
| ✅ | `CompositorNodeSequencerStripInfo` | Sequencer Strip Info | — | Start Frame:Int, End Frame:Int, Location:Vector2D, Rotation:Float, Scale:Vector2D |
| ✅ | `CompositorNodeSetAlpha` | Set Alpha | Image:Color, Alpha:Float, Type:Menu | Image:Color |
| ✅ | `CompositorNodeSplit` | Split | Position:VectorFactor2D, Rotation:FloatAngle, Image:Color, Image:Color | Image:Color |
| ✅ | `CompositorNodeStabilize` | Stabilize 2D | Image:Color, Frame:Int, Invert:Bool, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ✅ | `CompositorNodeStringToImage` | String To Image | String:String, Font:Font, Size:FloatPixel, Horizontal Alignment:Menu, Vertical Alignment:Menu, Wrap:Bool, Width:IntPixel | Image:Float |
| ✅ | `CompositorNodeSwitch` | Switch | Switch:Bool, Off:Color, On:Color | Image:Color |
| ✅ | `CompositorNodeSwitchView` | Switch View | left:Color, right:Color | Image:Color |
| ✅ | `CompositorNodeTime` | Time Curve | Start Frame:Int, End Frame:Int | Factor:Float |
| ✅ | `CompositorNodeTonemap` | Tonemap | Image:Color, Type:Menu, Key:Float, Balance:Float, Gamma:Float, Intensity:Float, Contrast:Float, Light Adaptation:FloatFactor, Chromatic Adaptation:FloatFactor | Image:Color |
| ✅ | `CompositorNodeTrackPos` | Track Position | Mode:Menu, Frame:Int | X:Float, Y:Float, Speed:VectorVelocity4D |
| ✅ | `CompositorNodeTransform` | Transform | Image:Color, X:FloatPixel, Y:FloatPixel, Angle:FloatAngle, Scale:Float, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ✅ | `CompositorNodeTranslate` | Translate | Image:Color, X:FloatPixel, Y:FloatPixel, Interpolation:Menu, Extension X:Menu, Extension Y:Menu | Image:Color |
| ⚠ | `CompositorNodeTree` |  | RuntimeError: Error: Node type CompositorNodeTree undefined
 | — |
| ✅ | `CompositorNodeVecBlur` | Vector Blur | Image:Color, Speed:VectorVelocity4D, Depth:Float, Samples:Int, Shutter:Float | Image:Color |
| ✅ | `CompositorNodeViewer` | Viewer | Image:Color | — |
| ✅ | `CompositorNodeZcombine` | Depth Combine | A:Color, Depth A:Float, B:Color, Depth B:Float, Use Alpha:Bool, Anti-Alias:Bool | Result:Color, Depth:Float |

### Function 노드 — 56개

| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |
|---|---|---|---|---|
| ⚠ | `FunctionNode` |  | RuntimeError: Error: Node type FunctionNode undefined
 | — |
| ✅ | `FunctionNodeAlignEulerToVector` | Align Euler to Vector | Rotation:VectorEuler, Factor:FloatFactor, Vector:Vector | Rotation:VectorEuler |
| ✅ | `FunctionNodeAlignRotationToVector` | Align Rotation to Vector | Rotation:Rotation, Factor:FloatFactor, Vector:VectorXYZ | Rotation:Rotation |
| ✅ | `FunctionNodeAxesToRotation` | Axes to Rotation | Primary Axis:Vector, Secondary Axis:Vector | Rotation:Rotation |
| ✅ | `FunctionNodeAxisAngleToRotation` | Axis Angle to Rotation | Axis:Vector, Angle:FloatAngle | Rotation:Rotation |
| ✅ | `FunctionNodeBitMath` | Bit Math | A:Int, B:Int, Shift:Int | Value:Int |
| ✅ | `FunctionNodeBooleanMath` | Boolean Math | Boolean:Bool, Boolean:Bool | Boolean:Bool |
| ✅ | `FunctionNodeCombineColor` | Combine Color | Red:FloatFactor, Green:FloatFactor, Blue:FloatFactor, Alpha:FloatFactor | Color:Color |
| ✅ | `FunctionNodeCombineMatrix` | Combine Matrix | Column 1 Row 1:Float, Column 1 Row 2:Float, Column 1 Row 3:Float, Column 1 Row 4:Float, Column 2 Row 1:Float, Column 2 Row 2:Float, Column 2 Row 3:Float, Column 2 Row 4:Float, Column 3 Row 1:Float, Column 3 Row 2:Float, Column 3 Row 3:Float, Column 3 Row 4:Float, Column 4 Row 1:Float, Column 4 Row 2:Float, Column 4 Row 3:Float, Column 4 Row 4:Float | Matrix:Matrix |
| ✅ | `FunctionNodeCombineTransform` | Combine Transform | Translation:VectorTranslation, Rotation:Rotation, Scale:VectorXYZ | Transform:Matrix |
| ✅ | `FunctionNodeCompare` | Compare | A:Float, B:Float | Result:Bool |
| ✅ | `FunctionNodeEulerToRotation` | Euler to Rotation | Euler:VectorEuler | Rotation:Rotation |
| ✅ | `FunctionNodeFindInString` | Find in String | String:String, Search:String, Mode:Menu | First Found:Int, Count:Int |
| ✅ | `FunctionNodeFloatToInt` | Float to Integer | Float:Float | Integer:Int |
| ✅ | `FunctionNodeFormatString` | Format String | Format:String, :Virtual | String:String |
| ✅ | `FunctionNodeHashValue` | Hash Value | Value:Int, Seed:Int | Hash:Int |
| ✅ | `FunctionNodeInputBool` | Boolean | — | Boolean:Bool |
| ✅ | `FunctionNodeInputColor` | Color | — | Color:Color |
| ✅ | `FunctionNodeInputInt` | Integer | — | Integer:Int |
| ✅ | `FunctionNodeInputIntVector` | Integer Vector | — | Vector:IntVector3D |
| ✅ | `FunctionNodeInputMenu` | Menu | — | Menu:Menu |
| ✅ | `FunctionNodeInputRotation` | Rotation | — | Rotation:Rotation |
| ✅ | `FunctionNodeInputSpecialCharacters` | Special Characters | — | Line Break:String, Tab:String |
| ✅ | `FunctionNodeInputString` | String | — | String:String |
| ✅ | `FunctionNodeInputVector` | Vector | — | Vector:Vector |
| ✅ | `FunctionNodeIntegerMath` | Integer Math | Value:Int, Value:Int, Value:Int | Value:Int |
| ✅ | `FunctionNodeInvertMatrix` | Invert Matrix | Matrix:Matrix | Matrix:Matrix, Invertible:Bool |
| ✅ | `FunctionNodeInvertRotation` | Invert Rotation | Rotation:Rotation | Rotation:Rotation |
| ✅ | `FunctionNodeMatchString` | Match String | String:String, Operation:Menu, Key:String | Result:Bool |
| ✅ | `FunctionNodeMatrixDeterminant` | Matrix Determinant | Matrix:Matrix | Determinant:Float |
| ✅ | `FunctionNodeMatrixMultiply` | Multiply Matrices | Matrix:Matrix, Matrix:Matrix | Matrix:Matrix |
| ✅ | `FunctionNodeMatrixSVD` | Matrix SVD | Matrix:Matrix | U:Matrix, S:Vector, V:Matrix |
| ✅ | `FunctionNodeProjectPoint` | Project Point | Vector:VectorXYZ, Transform:Matrix | Vector:VectorXYZ |
| ✅ | `FunctionNodeQuaternionToRotation` | Quaternion to Rotation | W:Float, X:Float, Y:Float, Z:Float | Rotation:Rotation |
| ✅ | `FunctionNodeRandomValue` | Random Value | Min:Float, Max:Float, ID:Int, Seed:Int | Value:Float |
| ✅ | `FunctionNodeReplaceString` | Replace String | String:String, Find:String, Replace:String | String:String |
| ✅ | `FunctionNodeReverseString` | Reverse String | String:String | String:String |
| ✅ | `FunctionNodeRotateEuler` | Rotate Euler | Rotation:VectorEuler, Rotate By:VectorEuler | Rotation:Vector |
| ✅ | `FunctionNodeRotateRotation` | Rotate Rotation | Rotation:Rotation, Rotate By:Rotation | Rotation:Rotation |
| ✅ | `FunctionNodeRotateVector` | Rotate Vector | Vector:Vector, Rotation:Rotation | Vector:Vector |
| ✅ | `FunctionNodeRotationToAxisAngle` | Rotation to Axis Angle | Rotation:Rotation | Axis:Vector, Angle:FloatAngle |
| ✅ | `FunctionNodeRotationToEuler` | Rotation to Euler | Rotation:Rotation | Euler:VectorEuler |
| ✅ | `FunctionNodeRotationToQuaternion` | Rotation to Quaternion | Rotation:Rotation | W:Float, X:Float, Y:Float, Z:Float |
| ✅ | `FunctionNodeSeparateColor` | Separate Color | Color:Color | Red:Float, Green:Float, Blue:Float, Alpha:Float |
| ✅ | `FunctionNodeSeparateMatrix` | Separate Matrix | Matrix:Matrix | Column 1 Row 1:Float, Column 1 Row 2:Float, Column 1 Row 3:Float, Column 1 Row 4:Float, Column 2 Row 1:Float, Column 2 Row 2:Float, Column 2 Row 3:Float, Column 2 Row 4:Float, Column 3 Row 1:Float, Column 3 Row 2:Float, Column 3 Row 3:Float, Column 3 Row 4:Float, Column 4 Row 1:Float, Column 4 Row 2:Float, Column 4 Row 3:Float, Column 4 Row 4:Float |
| ✅ | `FunctionNodeSeparateTransform` | Separate Transform | Transform:Matrix | Translation:VectorTranslation, Rotation:Rotation, Scale:VectorXYZ |
| ✅ | `FunctionNodeSetStringCase` | Set String Case | String:String, Case:Menu | String:String |
| ✅ | `FunctionNodeSliceString` | Slice String | String:String, Position:Int, Length:Int | String:String |
| ✅ | `FunctionNodeSplitString` | Split String | String:String, Separator:String | List:String |
| ✅ | `FunctionNodeStringLength` | String Length | String:String | Length:Int |
| ✅ | `FunctionNodeStringToValue` | String to Value | String:String, Base:Int | Value:Float, Length:Int |
| ✅ | `FunctionNodeTransformDirection` | Transform Direction | Direction:VectorXYZ, Transform:Matrix | Direction:VectorXYZ |
| ✅ | `FunctionNodeTransformPoint` | Transform Point | Vector:VectorXYZ, Transform:Matrix | Vector:VectorXYZ |
| ✅ | `FunctionNodeTransposeMatrix` | Transpose Matrix | Matrix:Matrix | Matrix:Matrix |
| ✅ | `FunctionNodeTrimString` | Trim String | String:String, Characters:String, Whitespace:Bool, Start:Bool, End:Bool | String:String |
| ✅ | `FunctionNodeValueToString` | Value to String | Value:Float, Decimals:Int, Base:Int, Padding:Int | String:String |

### Geometry 노드 — 274개

| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |
|---|---|---|---|---|
| ⚠ | `GeometryNode` |  | RuntimeError: Error: Node type GeometryNode undefined
 | — |
| ✅ | `GeometryNodeAccumulateField` | Accumulate Field | Value:Float, Group ID:Int | Leading:Float, Trailing:Float, Total:Float |
| ⚠ | `GeometryNodeApplySimulatedData` |  | RuntimeError: Error: Node type GeometryNodeApplySimulatedDat | — |
| ✅ | `GeometryNodeAttributeDomainSize` | Domain Size | Geometry:Geometry | Point Count:Int, Edge Count:Int, Face Count:Int, Face Corner Count:Int, Spline Count:Int, Instance Count:Int, Layer Count:Int |
| ✅ | `GeometryNodeAttributeStatistic` | Attribute Statistic | Geometry:Geometry, Selection:Bool, Attribute:Float | Mean:Float, Median:Float, Sum:Float, Min:Float, Max:Float, Range:Float, Standard Deviation:Float, Variance:Float |
| ✅ | `GeometryNodeBake` | Bake | :Virtual | :Virtual |
| ✅ | `GeometryNodeBlurAttribute` | Blur Attribute | Value:Float, Iterations:Int, Weight:FloatFactor | Value:Float |
| ✅ | `GeometryNodeBoneInfo` | Bone Info | Armature:Object, Bone Name:String | Pose:Matrix, Local Pose:Matrix, Transform Pose:Matrix, Rest Pose:Matrix, Rest Length:Float, Exists:Bool |
| ✅ | `GeometryNodeBoundBox` | Bounding Box | Geometry:Geometry, Use Radius:Bool | Bounding Box:Geometry, Min:Vector, Max:Vector |
| ✅ | `GeometryNodeCameraInfo` | Camera Info | Camera:Object | Projection Matrix:Matrix, Focal Length:Float, Sensor:Vector2D, Shift:Vector2D, Clip Start:Float, Clip End:Float, Focus Distance:Float, Is Orthographic:Bool, Orthographic Scale:Float |
| ✅ | `GeometryNodeCaptureAttribute` | Capture Attribute | Geometry:Geometry, Selection:Bool, :Virtual | Geometry:Geometry, Selection:Bool, :Virtual |
| ✅ | `GeometryNodeClosureToList` | Closure to List | Count:Int, Closure:Closure | :Virtual |
| ⚠ | `GeometryNodeClosureToListItem` |  | RuntimeError: Error: Node type GeometryNodeClosureToListItem | — |
| ⚠ | `GeometryNodeClosureToListItems` |  | RuntimeError: Error: Node type GeometryNodeClosureToListItem | — |
| ✅ | `GeometryNodeClusterByConnected` | Cluster by Connected | Selection:Bool, Position:Vector, Distance:FloatDistance | Cluster ID:Int |
| ✅ | `GeometryNodeClusterByDistance` | Cluster by Distance | Selection:Bool, Group ID:Int, Position:Vector, Distance:FloatDistance | Cluster ID:Int |
| ✅ | `GeometryNodeCollectionChildren` | Collection Children | Collection:Collection, Recursive:Bool | Collections:Collection, Objects:Object |
| ✅ | `GeometryNodeCollectionInfo` | Collection Info | Collection:Collection, Separate Children:Bool, Reset Children:Bool | Instances:Geometry |
| ✅ | `GeometryNodeConvexHull` | Convex Hull | Geometry:Geometry | Convex Hull:Geometry |
| ✅ | `GeometryNodeCornersOfEdge` | Corners of Edge | Edge Index:Int, Weights:Float, Sort Index:Int | Corner Index:Int, Total:Int |
| ✅ | `GeometryNodeCornersOfFace` | Corners of Face | Face Index:Int, Weights:Float, Sort Index:Int | Corner Index:Int, Total:Int |
| ✅ | `GeometryNodeCornersOfVertex` | Corners of Vertex | Vertex Index:Int, Weights:Float, Sort Index:Int | Corner Index:Int, Total:Int |
| ✅ | `GeometryNodeCubeGridTopology` | Cube Grid Topology | Bounds Min:Vector, Bounds Max:Vector, Resolution X:Int, Resolution Y:Int, Resolution Z:Int, Min X:Int, Min Y:Int, Min Z:Int | Topology:Bool |
| ✅ | `GeometryNodeCurveArc` | Arc | Resolution:IntUnsigned, Start:VectorTranslation, Middle:VectorTranslation, End:VectorTranslation, Radius:FloatDistance, Start Angle:FloatAngle, Sweep Angle:FloatAngle, Offset Angle:FloatAngle, Connect Center:Bool, Invert Arc:Bool | Curve:Geometry, Center:Vector, Normal:Vector, Radius:Float |
| ✅ | `GeometryNodeCurveEndpointSelection` | Endpoint Selection | Start Size:Int, End Size:Int | Selection:Bool |
| ✅ | `GeometryNodeCurveHandleTypeSelection` | Handle Type Selection | — | Selection:Bool |
| ✅ | `GeometryNodeCurveLength` | Curve Length | Curve:Geometry | Length:Float |
| ✅ | `GeometryNodeCurveOfPoint` | Curve of Point | Point Index:Int | Curve Index:Int, Index in Curve:Int |
| ✅ | `GeometryNodeCurvePrimitiveBezierSegment` | Bézier Segment | Resolution:IntUnsigned, Start:VectorTranslation, Start Handle:VectorTranslation, End Handle:VectorTranslation, End:VectorTranslation | Curve:Geometry |
| ✅ | `GeometryNodeCurvePrimitiveCircle` | Curve Circle | Resolution:Int, Point 1:VectorTranslation, Point 2:VectorTranslation, Point 3:VectorTranslation, Radius:FloatDistance | Curve:Geometry, Center:Vector |
| ✅ | `GeometryNodeCurvePrimitiveLine` | Curve Line | Start:VectorTranslation, End:VectorTranslation, Direction:Vector, Length:FloatDistance | Curve:Geometry |
| ✅ | `GeometryNodeCurvePrimitiveQuadrilateral` | Quadrilateral | Width:FloatDistance, Height:FloatDistance, Bottom Width:FloatDistance, Top Width:FloatDistance, Offset:FloatDistance, Bottom Height:FloatDistance, Top Height:FloatDistance, Point 1:VectorTranslation, Point 2:VectorTranslation, Point 3:VectorTranslation, Point 4:VectorTranslation | Curve:Geometry |
| ✅ | `GeometryNodeCurveQuadraticBezier` | Quadratic Bézier | Resolution:IntUnsigned, Start:VectorTranslation, Middle:VectorTranslation, End:VectorTranslation | Curve:Geometry |
| ✅ | `GeometryNodeCurveSetHandles` | Set Handle Type | Curve:Geometry, Selection:Bool | Curve:Geometry |
| ✅ | `GeometryNodeCurveSpiral` | Spiral | Resolution:IntUnsigned, Rotations:Float, Start Radius:FloatDistance, End Radius:FloatDistance, Height:FloatDistance, Reverse:Bool | Curve:Geometry |
| ✅ | `GeometryNodeCurveSplineType` | Set Spline Type | Curve:Geometry, Selection:Bool | Curve:Geometry |
| ✅ | `GeometryNodeCurveStar` | Star | Points:IntUnsigned, Inner Radius:FloatDistance, Outer Radius:FloatDistance, Twist:FloatAngle | Curve:Geometry, Outer Points:Bool |
| ✅ | `GeometryNodeCurveToMesh` | Curve to Mesh | Curve:Geometry, Profile Curve:Geometry, Scale:Float, Fill Caps:Bool | Mesh:Geometry |
| ✅ | `GeometryNodeCurveToPoints` | Curve to Points | Curve:Geometry, Count:Int, Length:FloatDistance | Points:Geometry, Tangent:Vector, Normal:Vector, Rotation:Rotation |
| ✅ | `GeometryNodeCurvesToGreasePencil` | Curves to Grease Pencil | Curves:Geometry, Selection:Bool, Instances as Layers:Bool | Grease Pencil:Geometry |
| ⚠ | `GeometryNodeCustomGroup` |  | RuntimeError: Error: Node type GeometryNodeCustomGroup undef | — |
| ✅ | `GeometryNodeDeformCurvesOnSurface` | Deform Curves on Surface | Curves:Geometry | Curves:Geometry |
| ✅ | `GeometryNodeDeleteGeometry` | Delete Geometry | Geometry:Geometry, Selection:Bool | Geometry:Geometry |
| ✅ | `GeometryNodeDistributePointsInGrid` | Distribute Points in Grid | Grid:Float, Density:Float, Seed:Int, Spacing:VectorXYZ, Threshold:Float | Points:Geometry |
| ✅ | `GeometryNodeDistributePointsInVolume` | Distribute Points in Volume | Volume:Geometry, Mode:Menu, Density:Float, Seed:Int, Spacing:VectorXYZ, Threshold:Float | Points:Geometry |
| ✅ | `GeometryNodeDistributePointsOnFaces` | Distribute Points on Faces | Mesh:Geometry, Selection:Bool, Distance Min:FloatDistance, Density Max:Float, Density:Float, Density Factor:FloatFactor, Seed:Int | Points:Geometry, Normal:Vector, Rotation:Rotation |
| ✅ | `GeometryNodeDualMesh` | Dual Mesh | Mesh:Geometry, Keep Boundaries:Bool | Dual Mesh:Geometry |
| ✅ | `GeometryNodeDuplicateElements` | Duplicate Elements | Geometry:Geometry, Selection:Bool, Amount:Int | Geometry:Geometry, Duplicate Index:Int |
| ✅ | `GeometryNodeEdgePathsToCurves` | Edge Paths to Curves | Mesh:Geometry, Start Vertices:Bool, Next Vertex Index:Int | Curves:Geometry |
| ✅ | `GeometryNodeEdgePathsToSelection` | Edge Paths to Selection | Start Vertices:Bool, Next Vertex Index:Int | Selection:Bool |
| ✅ | `GeometryNodeEdgesOfCorner` | Edges of Corner | Corner Index:Int | Next Edge Index:Int, Previous Edge Index:Int |
| ✅ | `GeometryNodeEdgesOfVertex` | Edges of Vertex | Vertex Index:Int, Weights:Float, Sort Index:Int | Edge Index:Int, Total:Int |
| ✅ | `GeometryNodeEdgesToFaceGroups` | Edges to Face Groups | Boundary Edges:Bool | Face Group ID:Int |
| ✅ | `GeometryNodeExtrudeMesh` | Extrude Mesh | Mesh:Geometry, Selection:Bool, Offset:VectorTranslation, Offset Scale:Float, Individual:Bool | Mesh:Geometry, Top:Bool, Side:Bool |
| ✅ | `GeometryNodeFaceOfCorner` | Face of Corner | Corner Index:Int | Face Index:Int, Index in Face:Int |
| ✅ | `GeometryNodeFieldAtIndex` | Evaluate at Index | Value:Float, Index:Int | Value:Float |
| ✅ | `GeometryNodeFieldAverage` | Field Average | Value:Float, Group ID:Int | Mean:Float, Median:Float |
| ✅ | `GeometryNodeFieldMinAndMax` | Field Min & Max | Value:Float, Group ID:Int | Min:Float, Max:Float |
| ✅ | `GeometryNodeFieldOnDomain` | Evaluate on Domain | Value:Float | Value:Float |
| ✅ | `GeometryNodeFieldToGrid` | Field to Grid | Topology:Float, :Virtual | :Virtual |
| ⚠ | `GeometryNodeFieldToGridItem` |  | RuntimeError: Error: Node type GeometryNodeFieldToGridItem u | — |
| ⚠ | `GeometryNodeFieldToGridItems` |  | RuntimeError: Error: Node type GeometryNodeFieldToGridItems  | — |
| ✅ | `GeometryNodeFieldToList` | Field to List | Count:Int, :Virtual | :Virtual |
| ⚠ | `GeometryNodeFieldToListItem` |  | RuntimeError: Error: Node type GeometryNodeFieldToListItem u | — |
| ⚠ | `GeometryNodeFieldToListItems` |  | RuntimeError: Error: Node type GeometryNodeFieldToListItems  | — |
| ✅ | `GeometryNodeFieldVariance` | Field Variance | Value:Float, Group ID:Int | Standard Deviation:Float, Variance:Float |
| ✅ | `GeometryNodeFillCurve` | Fill Curve | Curve:Geometry, Group ID:Int, Mode:Menu, Fill Rule:Menu | Mesh:Geometry |
| ✅ | `GeometryNodeFilletCurve` | Fillet Curve | Curve:Geometry, Radius:FloatDistance, Limit Radius:Bool, Mode:Menu, Count:Int | Curve:Geometry |
| ✅ | `GeometryNodeFilterList` | Filter List | List:Float, Selection:Bool | Selection:Float, Inverted:Float |
| ✅ | `GeometryNodeFlipFaces` | Flip Faces | Mesh:Geometry, Selection:Bool | Mesh:Geometry |
| ✅ | `GeometryNodeForeachGeometryElementInput` | For Each Geometry Element Input | Geometry:Geometry, Selection:Bool, :Virtual | Index:Int, Element:Geometry, :Virtual |
| ✅ | `GeometryNodeForeachGeometryElementOutput` | For Each Geometry Element Output | :Virtual, Geometry:Geometry, :Virtual | Geometry:Geometry, :Virtual, Geometry:Geometry, :Virtual |
| ✅ | `GeometryNodeGeometryToInstance` | Geometry to Instance | Geometry:Geometry | Instances:Geometry |
| ✅ | `GeometryNodeGetAttributeNames` | Get Attribute Names | Geometry:Geometry, Filter Data Type:Bool, Data Type:Menu, Filter Domain:Bool, Domain:Menu | Names:String |
| ✅ | `GeometryNodeGetGeometryBundle` | Get Geometry Bundle | Geometry:Geometry, Remove:Bool | Geometry:Geometry, Bundle:Bundle |
| ✅ | `GeometryNodeGetGeometryComponent` | Get Geometry Component | Geometry:Geometry, Type:Menu, Remove:Bool | Geometry:Geometry, Component:Geometry, Exists:Bool |
| ✅ | `GeometryNodeGetNamedGrid` | Get Named Grid | Volume:Geometry, Name:String, Remove:Bool | Volume:Geometry, Grid:Float |
| ✅ | `GeometryNodeGizmoDial` | Dial Gizmo | Value:Float, Position:VectorTranslation, Up:VectorXYZ, Screen Space:Bool, Radius:Float | Transform:Geometry |
| ✅ | `GeometryNodeGizmoLinear` | Linear Gizmo | Value:Float, Position:VectorTranslation, Direction:VectorXYZ | Transform:Geometry |
| ✅ | `GeometryNodeGizmoTransform` | Transform Gizmo | Value:Matrix, Position:VectorTranslation, Rotation:Rotation | Transform:Geometry |
| ✅ | `GeometryNodeGreasePencilToCurves` | Grease Pencil to Curves | Grease Pencil:Geometry, Selection:Bool, Layers as Instances:Bool | Curves:Geometry |
| ✅ | `GeometryNodeGridAdvect` | Advect Grid | Grid:Float, Velocity:Vector, Time Step:FloatTimeAbsolute, Integration Scheme:Menu, Limiter:Menu | Grid:Float |
| ✅ | `GeometryNodeGridClip` | Clip Grid | Grid:Float, Min X:Int, Min Y:Int, Min Z:Int, Max X:Int, Max Y:Int, Max Z:Int | Grid:Float |
| ✅ | `GeometryNodeGridCurl` | Grid Curl | Grid:Vector | Curl:Vector |
| ✅ | `GeometryNodeGridDilateAndErode` | Grid Dilate & Erode | Grid:Float, Connectivity:Menu, Tiles:Menu, Steps:Int | Grid:Float |
| ✅ | `GeometryNodeGridDivergence` | Grid Divergence | Grid:Vector | Divergence:Float |
| ✅ | `GeometryNodeGridGradient` | Grid Gradient | Grid:Float | Gradient:Vector |
| ✅ | `GeometryNodeGridInfo` | Grid Info | Grid:Float | Transform:Matrix, Background Value:Float |
| ✅ | `GeometryNodeGridLaplacian` | Grid Laplacian | Grid:Float | Laplacian:Float |
| ✅ | `GeometryNodeGridMean` | Grid Mean | Grid:Float, Width:Int, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeGridMedian` | Grid Median | Grid:Float, Width:Int, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeGridPrune` | Prune Grid | Grid:Float, Mode:Menu, Threshold:Float | Grid:Float |
| ✅ | `GeometryNodeGridToMesh` | Grid to Mesh | Grid:Float, Threshold:Float, Adaptivity:FloatFactor | Mesh:Geometry |
| ✅ | `GeometryNodeGridToPoints` | Grid to Points | Grid:Float | Points:Geometry, Value:Float, X:Int, Y:Int, Z:Int, Is Tile:Bool, Extent:Int |
| ✅ | `GeometryNodeGridVoxelize` | Voxelize Grid | Grid:Float | Grid:Float |
| ✅ | `GeometryNodeGroup` | Group | — | — |
| ✅ | `GeometryNodeImageInfo` | Image Info | Image:Image, Frame:Int | Width:Int, Height:Int, Has Alpha:Bool, Frame Count:Int, FPS:Float |
| ✅ | `GeometryNodeImageTexture` | Image Texture | Image:Image, Vector:Vector, Frame:Int | Color:Color, Alpha:Float |
| ✅ | `GeometryNodeImportCSV` | Import CSV | Path:StringFilePath, Delimiter:String | Point Cloud:Geometry |
| ✅ | `GeometryNodeImportOBJ` | Import OBJ | Path:StringFilePath | Instances:Geometry |
| ✅ | `GeometryNodeImportPLY` | Import PLY | Path:StringFilePath | Mesh:Geometry |
| ✅ | `GeometryNodeImportSTL` | Import STL | Path:StringFilePath | Mesh:Geometry |
| ✅ | `GeometryNodeImportText` | Import Text | Path:StringFilePath | String:String |
| ✅ | `GeometryNodeImportVDB` | Import VDB | Path:StringFilePath | Volume:Geometry |
| ✅ | `GeometryNodeIndexOfNearest` | Index of Nearest | Position:Vector, Group ID:Int | Index:Int, Has Neighbor:Bool |
| ✅ | `GeometryNodeIndexSwitch` | Index Switch | Index:Int, 0:Color, 1:Color, :Virtual | Output:Color |
| ✅ | `GeometryNodeInputActiveCamera` | Active Camera | — | Active Camera:Object |
| ✅ | `GeometryNodeInputCollection` | Collection | — | Collection:Collection |
| ✅ | `GeometryNodeInputCurveHandlePositions` | Curve Handle Positions | Relative:Bool | Left:Vector, Right:Vector |
| ✅ | `GeometryNodeInputCurveTilt` | Curve Tilt | — | Tilt:Float |
| ✅ | `GeometryNodeInputEdgeSmooth` | Is Edge Smooth | — | Smooth:Bool |
| ✅ | `GeometryNodeInputFont` | Font | — | Font:Font |
| ✅ | `GeometryNodeInputID` | ID | — | ID:Int |
| ✅ | `GeometryNodeInputImage` | Image | — | Image:Image |
| ✅ | `GeometryNodeInputIndex` | Index | — | Index:Int |
| ✅ | `GeometryNodeInputInstanceBounds` | Instance Bounds | Use Radius:Bool | Min:Vector, Max:Vector |
| ✅ | `GeometryNodeInputInstanceReference` | Instance Reference | — | Reference Index:Int |
| ✅ | `GeometryNodeInputInstanceRotation` | Instance Rotation | — | Rotation:Rotation |
| ✅ | `GeometryNodeInputInstanceScale` | Instance Scale | — | Scale:Vector |
| ✅ | `GeometryNodeInputMaterial` | Material | — | Material:Material |
| ✅ | `GeometryNodeInputMaterialIndex` | Material Index | — | Material Index:Int |
| ✅ | `GeometryNodeInputMeshEdgeAngle` | Edge Angle | — | Unsigned Angle:Float, Signed Angle:Float |
| ✅ | `GeometryNodeInputMeshEdgeNeighbors` | Edge Neighbors | — | Face Count:Int |
| ✅ | `GeometryNodeInputMeshEdgeVertices` | Edge Vertices | — | Vertex Index 1:Int, Vertex Index 2:Int, Position 1:Vector, Position 2:Vector |
| ✅ | `GeometryNodeInputMeshFaceArea` | Face Area | — | Area:Float |
| ✅ | `GeometryNodeInputMeshFaceIsPlanar` | Is Face Planar | Threshold:FloatDistance | Planar:Bool |
| ✅ | `GeometryNodeInputMeshFaceNeighbors` | Face Neighbors | — | Vertex Count:Int, Face Count:Int |
| ✅ | `GeometryNodeInputMeshIsland` | Mesh Island | — | Island Index:Int, Island Count:Int |
| ✅ | `GeometryNodeInputMeshVertexNeighbors` | Vertex Neighbors | — | Vertex Count:Int, Face Count:Int |
| ✅ | `GeometryNodeInputNamedAttribute` | Named Attribute | Name:String | Attribute:Float, Exists:Bool |
| ✅ | `GeometryNodeInputNamedLayerSelection` | Named Layer Selection | Name:String | Selection:Bool |
| ✅ | `GeometryNodeInputNormal` | Normal | — | Normal:Vector, True Normal:Vector |
| ✅ | `GeometryNodeInputObject` | Object | — | Object:Object |
| ✅ | `GeometryNodeInputPosition` | Position | — | Position:Vector |
| ✅ | `GeometryNodeInputRadius` | Radius | — | Radius:Float |
| ✅ | `GeometryNodeInputSceneTime` | Scene Time | — | Seconds:Float, Frame:Float |
| ✅ | `GeometryNodeInputShadeSmooth` | Is Face Smooth | — | Smooth:Bool |
| ✅ | `GeometryNodeInputShortestEdgePaths` | Shortest Edge Paths | End Vertex:Bool, Edge Cost:Float | Next Vertex Index:Int, Total Cost:Float |
| ✅ | `GeometryNodeInputSplineCyclic` | Is Spline Cyclic | — | Cyclic:Bool |
| ✅ | `GeometryNodeInputSplineResolution` | Spline Resolution | — | Resolution:Int |
| ✅ | `GeometryNodeInputTangent` | Curve Tangent | — | Tangent:Vector |
| ✅ | `GeometryNodeInputVoxelIndex` | Voxel Index | — | X:Int, Y:Int, Z:Int, Is Tile:Bool, Extent X:Int, Extent Y:Int, Extent Z:Int |
| ✅ | `GeometryNodeInstanceOnPoints` | Instance on Points | Points:Geometry, Selection:Bool, Instance:Geometry, Pick Instance:Bool, Instance Index:Int, Rotation:Rotation, Scale:VectorXYZ | Instances:Geometry |
| ✅ | `GeometryNodeInstanceTransform` | Instance Transform | — | Transform:Matrix |
| ✅ | `GeometryNodeInstancesToPoints` | Instances to Points | Instances:Geometry, Selection:Bool, Position:Vector, Radius:FloatDistance | Points:Geometry |
| ✅ | `GeometryNodeInterpolateCurves` | Interpolate Curves | Guide Curves:Geometry, Guide Up:Vector, Guide Group ID:Int, Points:Geometry, Point Up:Vector, Point Group ID:Int, Max Neighbors:Int | Curves:Geometry, Closest Index:Int, Closest Weight:Float |
| ✅ | `GeometryNodeIsViewport` | Is Viewport | — | Is Viewport:Bool |
| ✅ | `GeometryNodeJoinGeometry` | Join Geometry | Geometry:Geometry | Geometry:Geometry |
| ✅ | `GeometryNodeListGetItem` | Get List Item | List:Float, Index:Int | Value:Float |
| ✅ | `GeometryNodeListLength` | List Length | List:Float | Length:Int |
| ✅ | `GeometryNodeMaterialSelection` | Material Selection | Material:Material | Selection:Bool |
| ✅ | `GeometryNodeMenuSwitch` | Menu Switch | Menu:Menu, A:Color, B:Color, :Virtual | Output:Color, A:Bool, B:Bool |
| ✅ | `GeometryNodeMergeByDistance` | Merge by Distance | Geometry:Geometry, Selection:Bool, Mode:Menu, Distance:FloatDistance | Geometry:Geometry |
| ✅ | `GeometryNodeMergeLayers` | Merge Layers | Grease Pencil:Geometry, Selection:Bool, Group ID:Int | Grease Pencil:Geometry |
| ✅ | `GeometryNodeMergePoints` | Merge Points | Geometry:Geometry, Selection:Bool, Merge ID:Int | Geometry:Geometry |
| ✅ | `GeometryNodeMeshBevel` | Mesh Bevel | Mesh:Geometry, Selection:Bool, Affect Kind:Menu, Start Left Offset:FloatDistance, Start Right Offset:FloatDistance, End Left Offset:FloatDistance, End Right Offset:FloatDistance, Offset:FloatDistance, Miter:Bool, Spread:FloatDistance, Segments:Int, Shape:FloatFactor, Profile:Geometry | Mesh:Geometry, Vertex Face:Bool, Edge Face:Bool, Outer Edge:Bool, Mid Edge:Bool |
| ✅ | `GeometryNodeMeshBoolean` | Mesh Boolean | Mesh 1:Geometry, Mesh 2:Geometry, Self Intersection:Bool, Hole Tolerant:Bool | Mesh:Geometry, Intersecting Edges:Bool |
| ✅ | `GeometryNodeMeshCircle` | Mesh Circle | Vertices:Int, Radius:FloatDistance | Mesh:Geometry |
| ✅ | `GeometryNodeMeshCone` | Cone | Vertices:Int, Side Segments:Int, Fill Segments:Int, Radius Top:FloatDistance, Radius Bottom:FloatDistance, Depth:FloatDistance | Mesh:Geometry, Top:Bool, Bottom:Bool, Side:Bool, UV Map:Vector |
| ✅ | `GeometryNodeMeshCube` | Cube | Size:VectorTranslation, Vertices X:Int, Vertices Y:Int, Vertices Z:Int | Mesh:Geometry, UV Map:Vector |
| ✅ | `GeometryNodeMeshCylinder` | Cylinder | Vertices:Int, Side Segments:Int, Fill Segments:Int, Radius:FloatDistance, Depth:FloatDistance | Mesh:Geometry, Top:Bool, Side:Bool, Bottom:Bool, UV Map:Vector |
| ✅ | `GeometryNodeMeshFaceSetBoundaries` | Face Group Boundaries | Face Group ID:Int | Boundary Edges:Bool |
| ✅ | `GeometryNodeMeshGrid` | Grid | Size X:FloatDistance, Size Y:FloatDistance, Vertices X:Int, Vertices Y:Int | Mesh:Geometry, UV Map:Vector |
| ✅ | `GeometryNodeMeshIcoSphere` | Ico Sphere | Radius:FloatDistance, Subdivisions:Int | Mesh:Geometry, UV Map:Vector |
| ✅ | `GeometryNodeMeshLine` | Mesh Line | Count:Int, Resolution:FloatDistance, Start Location:VectorTranslation, Offset:VectorTranslation | Mesh:Geometry |
| ✅ | `GeometryNodeMeshToCurve` | Mesh to Curve | Mesh:Geometry, Selection:Bool | Curve:Geometry |
| ✅ | `GeometryNodeMeshToDensityGrid` | Mesh to Density Grid | Mesh:Geometry, Density:Float, Voxel Size:FloatDistance, Gradient Width:FloatDistance | Density Grid:Float |
| ✅ | `GeometryNodeMeshToPoints` | Mesh to Points | Mesh:Geometry, Selection:Bool, Position:Vector, Radius:FloatDistance | Points:Geometry |
| ✅ | `GeometryNodeMeshToSDFGrid` | Mesh to SDF Grid | Mesh:Geometry, Voxel Size:FloatDistance, Band Width:Int | SDF Grid:Float |
| ✅ | `GeometryNodeMeshToVolume` | Mesh to Volume | Mesh:Geometry, Density:Float, Resolution Mode:Menu, Voxel Size:FloatDistance, Voxel Amount:Float, Interior Band Width:FloatDistance | Volume:Geometry |
| ✅ | `GeometryNodeMeshUVSphere` | UV Sphere | Segments:Int, Rings:Int, Radius:FloatDistance | Mesh:Geometry, UV Map:Vector |
| ✅ | `GeometryNodeObjectInfo` | Object Info | Object:Object, As Instance:Bool | Transform:Matrix, Location:Vector, Rotation:Rotation, Scale:Vector, Geometry:Geometry |
| ✅ | `GeometryNodeOffsetCornerInFace` | Offset Corner in Face | Corner Index:Int, Offset:Int | Corner Index:Int |
| ✅ | `GeometryNodeOffsetPointInCurve` | Offset Point in Curve | Point Index:Int, Offset:Int | Is Valid Offset:Bool, Point Index:Int |
| ✅ | `GeometryNodePoints` | Points | Count:Int, Position:VectorTranslation, Radius:FloatDistance | Points:Geometry |
| ✅ | `GeometryNodePointsOfCurve` | Points of Curve | Curve Index:Int, Weights:Float, Sort Index:Int | Point Index:Int, Total:Int |
| ✅ | `GeometryNodePointsToCurves` | Points to Curves | Points:Geometry, Curve Group ID:Int, Weight:Float | Curves:Geometry |
| ✅ | `GeometryNodePointsToSDFGrid` | Points to SDF Grid | Points:Geometry, Radius:FloatDistance, Voxel Size:FloatDistance | SDF Grid:Float |
| ✅ | `GeometryNodePointsToVertices` | Points to Vertices | Points:Geometry, Selection:Bool | Mesh:Geometry |
| ✅ | `GeometryNodePointsToVolume` | Points to Volume | Points:Geometry, Density:Float, Resolution Mode:Menu, Voxel Size:FloatDistance, Voxel Amount:Float, Radius:FloatDistance | Volume:Geometry |
| ✅ | `GeometryNodeProximity` | Geometry Proximity | Geometry:Geometry, Group ID:Int, Sample Position:Vector, Sample Group ID:Int | Position:Vector, Distance:Float, Is Valid:Bool |
| ✅ | `GeometryNodeRaycast` | Raycast | Target Geometry:Geometry, Attribute:Float, Interpolation:Menu, Source Position:Vector, Ray Direction:Vector, Ray Length:FloatDistance | Is Hit:Bool, Hit Position:Vector, Hit Normal:Vector, Hit Distance:Float, Attribute:Float |
| ✅ | `GeometryNodeRealizeInstances` | Realize Instances | Geometry:Geometry, Selection:Bool, Realize All:Bool, Depth:Int | Geometry:Geometry |
| ✅ | `GeometryNodeRemoveAttribute` | Remove Named Attribute | Geometry:Geometry, Pattern Mode:Menu, Name:String | Geometry:Geometry |
| ✅ | `GeometryNodeRenameAttribute` | Rename Attribute | Geometry:Geometry, Mode:Menu, Old:String, New:String, Overwrite:Bool | Geometry:Geometry |
| ✅ | `GeometryNodeRepeatInput` | Repeat Input | Iterations:Int, :Virtual | Iteration:Int, :Virtual |
| ✅ | `GeometryNodeRepeatOutput` | Repeat Output | :Virtual | :Virtual |
| ✅ | `GeometryNodeReplaceMaterial` | Replace Material | Geometry:Geometry, Old:Material, New:Material | Geometry:Geometry |
| ✅ | `GeometryNodeResampleCurve` | Resample Curve | Curve:Geometry, Selection:Bool, Mode:Menu, Count:Int, Length:FloatDistance | Curve:Geometry |
| ✅ | `GeometryNodeReverseCurve` | Reverse Curve | Curve:Geometry, Selection:Bool | Curve:Geometry |
| ✅ | `GeometryNodeRotateInstances` | Rotate Instances | Instances:Geometry, Selection:Bool, Rotation:Rotation, Pivot Point:VectorTranslation, Local Space:Bool | Instances:Geometry |
| ✅ | `GeometryNodeSDFGridBoolean` | SDF Grid Boolean | Grid 1:Float, Grid 2:Float | Grid:Float |
| ✅ | `GeometryNodeSDFGridFillet` | SDF Grid Fillet | Grid:Float, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeSDFGridLaplacian` | SDF Grid Laplacian | Grid:Float, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeSDFGridMean` | SDF Grid Mean | Grid:Float, Width:Int, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeSDFGridMeanCurvature` | SDF Grid Mean Curvature | Grid:Float, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeSDFGridMedian` | SDF Grid Median | Grid:Float, Width:Int, Iterations:Int | Grid:Float |
| ✅ | `GeometryNodeSDFGridOffset` | SDF Grid Offset | Grid:Float, Distance:FloatDistance | Grid:Float |
| ✅ | `GeometryNodeSampleCurve` | Sample Curve | Curves:Geometry, Value:Float, Factor:FloatFactor, Length:FloatDistance, Curve Index:Int | Value:Float, Position:Vector, Tangent:Vector, Normal:Vector |
| ✅ | `GeometryNodeSampleGrid` | Sample Grid | Grid:Float, Position:Vector, Interpolation:Menu | Value:Float |
| ✅ | `GeometryNodeSampleGridIndex` | Sample Grid Index | Grid:Float, X:Int, Y:Int, Z:Int | Value:Float |
| ✅ | `GeometryNodeSampleIndex` | Sample Index | Geometry:Geometry, Value:Float, Index:Int | Value:Float |
| ✅ | `GeometryNodeSampleNearest` | Sample Nearest | Geometry:Geometry, Sample Position:Vector | Index:Int |
| ✅ | `GeometryNodeSampleNearestSurface` | Sample Nearest Surface | Mesh:Geometry, Value:Float, Group ID:Int, Sample Position:Vector, Sample Group ID:Int | Value:Float, Is Valid:Bool |
| ✅ | `GeometryNodeSampleSoundFrequencies` | Sample Sound Frequencies | Sound:Sound, Time:FloatTimeAbsolute, All Channels:Bool, Channel:Int, Low:FloatFrequency, High:FloatFrequency, FFT Size:Menu, Window Function:Menu | Amplitude:Float |
| ✅ | `GeometryNodeSampleUVSurface` | Sample UV Surface | Mesh:Geometry, Value:Float, UV Map:Vector, Sample UV:Vector | Value:Float, Is Valid:Bool |
| ✅ | `GeometryNodeScaleElements` | Scale Elements | Geometry:Geometry, Selection:Bool, Scale:Float, Center:VectorTranslation, Scale Mode:Menu, Axis:Vector | Geometry:Geometry |
| ✅ | `GeometryNodeScaleInstances` | Scale Instances | Instances:Geometry, Selection:Bool, Scale:VectorXYZ, Center:VectorTranslation, Local Space:Bool | Instances:Geometry |
| ✅ | `GeometryNodeSelfObject` | Self Object | — | Self Object:Object |
| ✅ | `GeometryNodeSeparateComponents` | Separate Components | Geometry:Geometry | Mesh:Geometry, Curve:Geometry, Grease Pencil:Geometry, Point Cloud:Geometry, Volume:Geometry, Instances:Geometry |
| ✅ | `GeometryNodeSeparateGeometry` | Separate Geometry | Geometry:Geometry, Selection:Bool | Selection:Geometry, Inverted:Geometry |
| ✅ | `GeometryNodeSetCurveHandlePositions` | Set Handle Positions | Curve:Geometry, Selection:Bool, Position:Vector, Offset:VectorTranslation | Curve:Geometry |
| ✅ | `GeometryNodeSetCurveNormal` | Set Curve Normal | Curve:Geometry, Selection:Bool, Mode:Menu, Normal:VectorXYZ | Curve:Geometry |
| ✅ | `GeometryNodeSetCurveRadius` | Set Curve Radius | Curve:Geometry, Selection:Bool, Radius:FloatDistance | Curve:Geometry |
| ✅ | `GeometryNodeSetCurveTilt` | Set Curve Tilt | Curve:Geometry, Selection:Bool, Tilt:FloatAngle | Curve:Geometry |
| ✅ | `GeometryNodeSetGeometryBundle` | Set Geometry Bundle | Geometry:Geometry, Bundle:Bundle | Geometry:Geometry |
| ✅ | `GeometryNodeSetGeometryName` | Set Geometry Name | Geometry:Geometry, Name:String | Geometry:Geometry |
| ✅ | `GeometryNodeSetGreasePencilColor` | Set Grease Pencil Color | Grease Pencil:Geometry, Selection:Bool, Color:Color, Opacity:Float | Grease Pencil:Geometry |
| ✅ | `GeometryNodeSetGreasePencilDepth` | Set Grease Pencil Depth | Grease Pencil:Geometry | Grease Pencil:Geometry |
| ✅ | `GeometryNodeSetGreasePencilSoftness` | Set Grease Pencil Softness | Grease Pencil:Geometry, Selection:Bool, Softness:Float | Grease Pencil:Geometry |
| ✅ | `GeometryNodeSetGridBackground` | Set Grid Background | Grid:Float, Background:Float, Update Inactive:Bool | Grid:Float |
| ✅ | `GeometryNodeSetGridTransform` | Set Grid Transform | Grid:Float, Transform:Matrix | Is Valid:Bool, Grid:Float |
| ✅ | `GeometryNodeSetID` | Set ID | Geometry:Geometry, Selection:Bool, ID:Int | Geometry:Geometry |
| ✅ | `GeometryNodeSetInstanceTransform` | Set Instance Transform | Instances:Geometry, Selection:Bool, Transform:Matrix | Instances:Geometry |
| ✅ | `GeometryNodeSetMaterial` | Set Material | Geometry:Geometry, Selection:Bool, Material:Material | Geometry:Geometry |
| ✅ | `GeometryNodeSetMaterialIndex` | Set Material Index | Geometry:Geometry, Selection:Bool, Material Index:Int | Geometry:Geometry |
| ✅ | `GeometryNodeSetMeshNormal` | Set Mesh Normal | Mesh:Geometry, Remove Custom:Bool, Edge Sharpness:Bool, Face Sharpness:Bool | Mesh:Geometry |
| ✅ | `GeometryNodeSetNURBSOrder` | Set NURBS Order | Curves:Geometry, Selection:Bool, Order:Int | Curves:Geometry |
| ✅ | `GeometryNodeSetNURBSWeight` | Set NURBS Weight | Curves:Geometry, Selection:Bool, Weight:Float | Curves:Geometry |
| ✅ | `GeometryNodeSetPointRadius` | Set Point Radius | Points:Geometry, Selection:Bool, Radius:FloatDistance | Points:Geometry |
| ✅ | `GeometryNodeSetPosition` | Set Position | Geometry:Geometry, Selection:Bool, Position:Vector, Offset:VectorTranslation | Geometry:Geometry |
| ✅ | `GeometryNodeSetShadeSmooth` | Set Shade Smooth | Mesh:Geometry, Selection:Bool, Shade Smooth:Bool | Mesh:Geometry |
| ✅ | `GeometryNodeSetSplineCyclic` | Set Spline Cyclic | Curve:Geometry, Selection:Bool, Cyclic:Bool | Curve:Geometry |
| ✅ | `GeometryNodeSetSplineResolution` | Set Spline Resolution | Curve:Geometry, Selection:Bool, Resolution:Int | Curve:Geometry |
| ✅ | `GeometryNodeSimulationInput` | Simulation Input | — | Delta Time:Float |
| ✅ | `GeometryNodeSimulationOutput` | Simulation Output | Skip:Bool, Geometry:Geometry, :Virtual | Geometry:Geometry, :Virtual |
| ✅ | `GeometryNodeSortElements` | Sort Elements | Geometry:Geometry, Selection:Bool, Group ID:Int, Sort Weight:Float | Geometry:Geometry |
| ✅ | `GeometryNodeSortList` | Sort List | List:Float, Selection:Bool, Group ID:Int, Sort Weight:Float | List:Float |
| ✅ | `GeometryNodeSplineLength` | Spline Length | — | Length:Float, Point Count:Int |
| ✅ | `GeometryNodeSplineParameter` | Spline Parameter | — | Factor:Float, Length:Float, Index:Int |
| ✅ | `GeometryNodeSplitEdges` | Split Edges | Mesh:Geometry, Selection:Bool | Mesh:Geometry |
| ✅ | `GeometryNodeSplitToInstances` | Split to Instances | Geometry:Geometry, Selection:Bool, Group ID:Int | Instances:Geometry, Group ID:Int |
| ✅ | `GeometryNodeStoreNamedAttribute` | Store Named Attribute | Geometry:Geometry, Selection:Bool, Name:String, Value:Float | Geometry:Geometry |
| ✅ | `GeometryNodeStoreNamedGrid` | Store Named Grid | Volume:Geometry, Name:String, Grid:Float | Volume:Geometry |
| ✅ | `GeometryNodeStringJoin` | Join Strings | Delimiter:String, Strings:String | String:String |
| ✅ | `GeometryNodeStringToCurves` | String to Curves | String:String, Size:FloatDistance, Font:Font, Align X:Menu, Align Y:Menu, Pivot Point:Menu, Character Spacing:Float, Word Spacing:Float, Line Spacing:Float, Overflow:Menu, Text Box Width:FloatDistance, Text Box Height:FloatDistance | Curve Instances:Geometry, Remainder:String, Line:Int, Word:Int, Pivot Point:Vector |
| ✅ | `GeometryNodeSubdivideCurve` | Subdivide Curve | Curve:Geometry, Cuts:Int | Curve:Geometry |
| ✅ | `GeometryNodeSubdivideMesh` | Subdivide Mesh | Mesh:Geometry, Level:Int | Mesh:Geometry |
| ✅ | `GeometryNodeSubdivisionSurface` | Subdivision Surface | Mesh:Geometry, Level:Int, Edge Crease:FloatFactor, Vertex Crease:FloatFactor, Limit Surface:Bool, Quality:Int, UV Smooth:Menu, Boundary Smooth:Menu | Mesh:Geometry |
| ✅ | `GeometryNodeSwitch` | Switch | Switch:Bool, False:Float, True:Float | Output:Float |
| ✅ | `GeometryNodeTagFilter` | Tag Filter | Tag Filter:String, Tags:String | Match:Bool |
| ✅ | `GeometryNodeTool3DCursor` | 3D Cursor | — | Location:VectorTranslation, Rotation:Rotation |
| ✅ | `GeometryNodeToolActiveElement` | Active Element | — | Index:Int, Exists:Bool |
| ✅ | `GeometryNodeToolFaceSet` | Face Set | — | Face Set:Int, Exists:Bool |
| ✅ | `GeometryNodeToolMousePosition` | Mouse Position | — | Mouse X:Int, Mouse Y:Int, Region Width:Int, Region Height:Int |
| ✅ | `GeometryNodeToolSelection` | Selection | — | Boolean:Bool, Float:Float |
| ✅ | `GeometryNodeToolSetFaceSet` | Set Face Set | Mesh:Geometry, Selection:Bool, Face Set:Int | Mesh:Geometry |
| ✅ | `GeometryNodeToolSetSelection` | Set Selection | Geometry:Geometry, Selection:Bool | Geometry:Geometry |
| ✅ | `GeometryNodeTransferAttributes` | Transfer Attributes | Target:Geometry, Target Point ID:Int, Target Edge ID:Int, Target Face ID:Int, Target Corner ID:Int, Target Curve ID:Int, Target Instance ID:Int, Source:Geometry, Source Point ID:Int, Source Edge ID:Int, Source Face ID:Int, Source Corner ID:Int, Source Curve ID:Int, Source Instance ID:Int, Pattern Mode:Menu, Attribute Names:String, Exclude Names:Bool | Target:Geometry, Transferred Names:String |
| ✅ | `GeometryNodeTransform` | Transform Geometry | Geometry:Geometry, Mode:Menu, Translation:VectorTranslation, Rotation:Rotation, Scale:VectorXYZ, Transform:Matrix | Geometry:Geometry |
| ✅ | `GeometryNodeTranslateInstances` | Translate Instances | Instances:Geometry, Selection:Bool, Translation:VectorTranslation, Local Space:Bool | Instances:Geometry |
| ⚠ | `GeometryNodeTree` |  | RuntimeError: Error: Node type GeometryNodeTree undefined
 | — |
| ✅ | `GeometryNodeTriangulate` | Triangulate | Mesh:Geometry, Selection:Bool, Quad Method:Menu, N-gon Method:Menu | Mesh:Geometry |
| ✅ | `GeometryNodeTrimCurve` | Trim Curve | Curve:Geometry, Selection:Bool, Start:FloatFactor, End:FloatFactor, Start:FloatDistance, End:FloatDistance | Curve:Geometry |
| ✅ | `GeometryNodeUVPackIslands` | Pack UV Islands | UV:Vector, Selection:Bool, Margin:Float, Rotate:Bool, Method:Menu, Bottom Left:VectorXYZ2D, Top Right:VectorXYZ2D | UV:Vector |
| ✅ | `GeometryNodeUVTangent` | UV Tangent | Method:Menu, UV:VectorXYZ2D | Tangent:Vector |
| ✅ | `GeometryNodeUVUnwrap` | UV Unwrap | Selection:Bool, Seam:Bool, Margin:Float, Fill Holes:Bool, Method:Menu, Iterations:Int, No Flip:Bool | UV:Vector |
| ✅ | `GeometryNodeVertexOfCorner` | Vertex of Corner | Corner Index:Int | Vertex Index:Int |
| ✅ | `GeometryNodeViewer` | Viewer | :Virtual | — |
| ✅ | `GeometryNodeViewportTransform` | Viewport Transform | — | Projection:Matrix, View:Matrix, Is Orthographic:Bool |
| ✅ | `GeometryNodeVolumeCube` | Volume Cube | Density:Float, Background:Float, Min:Vector, Max:Vector, Resolution X:Int, Resolution Y:Int, Resolution Z:Int | Volume:Geometry |
| ✅ | `GeometryNodeVolumeToMesh` | Volume to Mesh | Volume:Geometry, Resolution Mode:Menu, Voxel Size:FloatDistance, Voxel Amount:Float, Threshold:Float, Adaptivity:FloatFactor | Mesh:Geometry |
| ✅ | `GeometryNodeWarning` | Warning | Show:Bool, Message:String | Show:Bool |
| ✅ | `GeometryNodeXPBDSolver` | XPBD Solver | World:Bundle, Delta Time:FloatTimeAbsolute, Filter:String, Simulation to World:Matrix, Substeps:Int, Constraint Iterations:Int, Solver Path:String, Begin:Float, End:Float | World:Bundle |

### Shader 노드 — 102개

| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |
|---|---|---|---|---|
| ⚠ | `ShaderNode` |  | RuntimeError: Error: Node type ShaderNode undefined
 | — |
| ✅ | `ShaderNodeAddShader` | Add Shader | Shader:Shader, Shader:Shader | Shader:Shader |
| ✅ | `ShaderNodeAmbientOcclusion` | Ambient Occlusion | Color:Color, Distance:Float, Normal:Vector | Color:Color, AO:Float |
| ✅ | `ShaderNodeAttribute` | Attribute | — | Color:Color, Vector:Vector, Factor:Float, Alpha:Float |
| ✅ | `ShaderNodeBackground` | Background | Color:Color, Strength:Float, Weight:Float | Background:Shader |
| ✅ | `ShaderNodeBevel` | Bevel | Radius:Float, Normal:Vector | Normal:Vector |
| ✅ | `ShaderNodeBlackbody` | Blackbody | Temperature:FloatColorTemperature | Color:Color |
| ✅ | `ShaderNodeBrightContrast` | Brightness/Contrast | Color:Color, Brightness:Float, Contrast:Float | Color:Color |
| ✅ | `ShaderNodeBsdfAnisotropic` | Glossy BSDF | Color:Color, Roughness:FloatFactor, Anisotropy:Float, Rotation:FloatFactor, Normal:Vector, Tangent:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfDiffuse` | Diffuse BSDF | Color:Color, Roughness:FloatFactor, Normal:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfGlass` | Glass BSDF | Color:Color, Roughness:FloatFactor, IOR:Float, Normal:Vector, Weight:Float, Thin Film Thickness:FloatWavelength, Thin Film IOR:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfHair` | Hair BSDF | Color:Color, Offset:FloatAngle, RoughnessU:FloatFactor, RoughnessV:FloatFactor, Tangent:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfHairPrincipled` | Principled Hair BSDF | Color:Color, Melanin:FloatFactor, Melanin Redness:FloatFactor, Tint:Color, Absorption Coefficient:Vector, Aspect Ratio:FloatFactor, Roughness:FloatFactor, Radial Roughness:FloatFactor, Coat:FloatFactor, IOR:Float, Offset:FloatAngle, Random Color:FloatFactor, Random Roughness:FloatFactor, Random:Float, Weight:Float, Reflection:FloatFactor, Transmission:FloatFactor, Secondary Reflection:FloatFactor | BSDF:Shader |
| ✅ | `ShaderNodeBsdfMetallic` | Metallic BSDF | Base Color:Color, Edge Tint:Color, IOR:Vector, Extinction:Vector, Roughness:FloatFactor, Anisotropy:FloatFactor, Rotation:FloatFactor, Normal:Vector, Tangent:Vector, Weight:Float, Thin Film Thickness:FloatWavelength, Thin Film IOR:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfPrincipled` | Principled BSDF | Base Color:Color, Metallic:FloatFactor, Roughness:FloatFactor, IOR:Float, Alpha:FloatFactor, Thin Wall:Bool, Normal:Vector, Weight:Float, Diffuse Roughness:FloatFactor, Subsurface Weight:FloatFactor, Subsurface Radius:Vector, Subsurface Scale:FloatDistance, Subsurface IOR:FloatFactor, Subsurface Anisotropy:FloatFactor, Specular IOR Level:FloatFactor, Specular Tint:Color, Anisotropic:FloatFactor, Anisotropic Rotation:FloatFactor, Tangent:Vector, Transmission Weight:FloatFactor, Coat Weight:FloatFactor, Coat Roughness:FloatFactor, Coat IOR:Float, Coat Tint:Color, Coat Normal:Vector, Sheen Weight:FloatFactor, Sheen Roughness:FloatFactor, Sheen Tint:Color, Emission Color:Color, Emission Strength:Float, Thin Film Thickness:FloatWavelength, Thin Film IOR:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfRayPortal` | Ray Portal BSDF | Color:Color, Position:Vector, Direction:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfRefraction` | Refraction BSDF | Color:Color, Roughness:FloatFactor, IOR:Float, Normal:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfSheen` | Sheen BSDF | Color:Color, Roughness:FloatFactor, Normal:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfToon` | Toon BSDF | Color:Color, Size:FloatFactor, Smooth:FloatFactor, Normal:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfTranslucent` | Translucent BSDF | Color:Color, Normal:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBsdfTransparent` | Transparent BSDF | Color:Color, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeBump` | Bump | Strength:FloatFactor, Distance:Float, Filter Width:FloatPixel, Height:Float, Normal:Vector | Normal:Vector |
| ✅ | `ShaderNodeCameraData` | Camera Data | — | View Vector:Vector, View Z Depth:Float, View Distance:Float |
| ✅ | `ShaderNodeClamp` | Clamp | Value:Float, Min:Float, Max:Float | Result:Float |
| ✅ | `ShaderNodeCombineColor` | Combine Color | Red:FloatFactor, Green:FloatFactor, Blue:FloatFactor | Color:Color |
| ✅ | `ShaderNodeCombineXYZ` | Combine XYZ | X:Float, Y:Float, Z:Float | Vector:Vector |
| ⚠ | `ShaderNodeCustomGroup` |  | RuntimeError: Error: Node type ShaderNodeCustomGroup undefin | — |
| ✅ | `ShaderNodeDisplacement` | Displacement | Height:Float, Midlevel:Float, Scale:Float, Normal:Vector | Displacement:Vector |
| ✅ | `ShaderNodeEeveeSpecular` | Specular BSDF | Base Color:Color, Specular:Color, Roughness:FloatFactor, Emissive Color:Color, Transparency:FloatFactor, Normal:Vector, Clear Coat:FloatFactor, Clear Coat Roughness:FloatFactor, Clear Coat Normal:Vector, Weight:Float | BSDF:Shader |
| ✅ | `ShaderNodeEmission` | Emission | Color:Color, Strength:Float, Weight:Float | Emission:Shader |
| ✅ | `ShaderNodeFloatCurve` | Float Curve | Factor:FloatFactor, Value:Float | Value:Float |
| ✅ | `ShaderNodeFresnel` | Fresnel | IOR:Float, Normal:Vector | Factor:Float |
| ✅ | `ShaderNodeGamma` | Gamma | Color:Color, Gamma:Float | Color:Color |
| ✅ | `ShaderNodeGroup` | Group | — | — |
| ✅ | `ShaderNodeHairInfo` | Curves Info | — | Is Strand:Float, Intercept:Float, Length:Float, Thickness:Float, Tangent Normal:Vector, Random:Float |
| ✅ | `ShaderNodeHoldout` | Holdout | Weight:Float | Holdout:Shader |
| ✅ | `ShaderNodeHueSaturation` | Hue/Saturation/Value | Hue:Float, Saturation:Float, Value:Float, Factor:FloatFactor, Color:Color | Color:Color |
| ✅ | `ShaderNodeInvert` | Invert Color | Factor:FloatFactor, Color:Color | Color:Color |
| ✅ | `ShaderNodeLayerWeight` | Layer Weight | Blend:Float, Normal:Vector | Fresnel:Float, Facing:Float |
| ✅ | `ShaderNodeLightFalloff` | Light Falloff | Strength:Float, Smooth:Float | Quadratic:Float, Linear:Float, Constant:Float |
| ✅ | `ShaderNodeLightPath` | Light Path | — | Is Camera Ray:Float, Is Shadow Ray:Float, Is Diffuse Ray:Float, Is Glossy Ray:Float, Is Singular Ray:Float, Is Reflection Ray:Float, Is Transmission Ray:Float, Is Volume Scatter Ray:Float, Ray Length:Float, Ray Depth:Float, Diffuse Depth:Float, Glossy Depth:Float, Transparent Depth:Float, Transmission Depth:Float, Portal Depth:Float |
| ✅ | `ShaderNodeMapRange` | Map Range | Value:Float, From Min:Float, From Max:Float, To Min:Float, To Max:Float, Steps:Float, Vector:Vector, From Min:Vector, From Max:Vector, To Min:Vector, To Max:Vector, Steps:Vector | Result:Float, Vector:Vector |
| ✅ | `ShaderNodeMapping` | Mapping | Vector:Vector, Location:VectorTranslation, Rotation:VectorEuler, Scale:VectorXYZ | Vector:Vector |
| ✅ | `ShaderNodeMath` | Math | Value:Float, Value:Float, Value:Float | Value:Float |
| ✅ | `ShaderNodeMix` | Mix | Factor:FloatFactor, Factor:VectorFactor, A:Float, B:Float, A:Vector, B:Vector, A:Color, B:Color, A:Rotation, B:Rotation | Result:Float, Result:Vector, Result:Color, Result:Rotation |
| ✅ | `ShaderNodeMixRGB` | Mix (Legacy) | Factor:FloatFactor, Color1:Color, Color2:Color | Color:Color |
| ✅ | `ShaderNodeMixShader` | Mix Shader | Factor:FloatFactor, Shader:Shader, Shader:Shader | Shader:Shader |
| ✅ | `ShaderNodeNewGeometry` | Geometry | — | Position:Vector, Normal:Vector, Tangent:Vector, True Normal:Vector, Incoming:Vector, Parametric:Vector, Backfacing:Float, Pointiness:Float, Random Per Island:Float |
| ✅ | `ShaderNodeNormal` | Normal | Normal:VectorDirection | Normal:VectorDirection, Dot:Float |
| ✅ | `ShaderNodeNormalMap` | Normal Map | Strength:Float, Color:Color | Normal:Vector |
| ✅ | `ShaderNodeObjectInfo` | Object Info | — | Location:Vector, Color:Color, Alpha:Float, Object Index:Float, Material Index:Float, Random:Float |
| ✅ | `ShaderNodeOutputAOV` | AOV Output | Color:Color, Value:Float | — |
| ✅ | `ShaderNodeOutputLight` | Light Output | Surface:Shader | — |
| ✅ | `ShaderNodeOutputLineStyle` | Line Style Output | Color:Color, Color Fac:FloatFactor, Alpha:FloatFactor, Alpha Fac:FloatFactor | — |
| ✅ | `ShaderNodeOutputMaterial` | Material Output | Surface:Shader, Volume:Shader, Displacement:Vector, Thickness:Float | — |
| ✅ | `ShaderNodeOutputWorld` | World Output | Surface:Shader, Volume:Shader | — |
| ✅ | `ShaderNodeParticleInfo` | Particle Info | — | Index:Float, Random:Float, Age:Float, Lifetime:Float, Location:Vector, Size:Float, Velocity:Vector, Angular Velocity:Vector |
| ✅ | `ShaderNodePointInfo` | Point Info | — | Position:Vector, Radius:Float, Random:Float |
| ✅ | `ShaderNodeRGB` | Color | — | Color:Color |
| ✅ | `ShaderNodeRGBCurve` | RGB Curves | Factor:FloatFactor, Color:Color | Color:Color |
| ✅ | `ShaderNodeRGBToBW` | RGB to BW | Color:Color | Val:Float |
| ✅ | `ShaderNodeRadialTiling` | Radial Tiling | Vector:Vector2D, Sides:Float, Roundness:FloatFactor | Segment Coordinates:Vector, Segment ID:Float, Segment Width:Float, Segment Rotation:Float |
| ✅ | `ShaderNodeRaycast` | Raycast | Position:Vector, Direction:Vector, Length:Float, :Virtual | Is Hit:Float, Self Hit:Float, Hit Distance:Float, Hit Position:Vector, Hit Normal:Vector, :Virtual |
| ✅ | `ShaderNodeScript` | Script | — | — |
| ✅ | `ShaderNodeSeparateColor` | Separate Color | Color:Color | Red:Float, Green:Float, Blue:Float |
| ✅ | `ShaderNodeSeparateXYZ` | Separate XYZ | Vector:Vector | X:Float, Y:Float, Z:Float |
| ✅ | `ShaderNodeShaderToRGB` | Shader to RGB | Shader:Shader | Color:Color, Alpha:Float |
| ✅ | `ShaderNodeSqueeze` | Squeeze Value (Legacy) | Value:Float, Width:Float, Center:Float | Value:Float |
| ✅ | `ShaderNodeSubsurfaceScattering` | Subsurface Scattering | Color:Color, Scale:Float, Radius:Vector, IOR:FloatFactor, Roughness:FloatFactor, Anisotropy:FloatFactor, Normal:Vector, Weight:Float | BSSRDF:Shader |
| ✅ | `ShaderNodeTangent` | Tangent | — | Tangent:Vector |
| ✅ | `ShaderNodeTexBrick` | Brick Texture | Vector:Vector, Color1:Color, Color2:Color, Mortar:Color, Scale:Float, Mortar Size:Float, Mortar Smooth:Float, Bias:Float, Brick Width:Float, Row Height:Float | Color:Color, Factor:Float |
| ✅ | `ShaderNodeTexChecker` | Checker Texture | Vector:Vector, Color1:Color, Color2:Color, Scale:Float | Color:Color, Factor:Float |
| ✅ | `ShaderNodeTexCoord` | Texture Coordinate | — | Generated:Vector, Normal:Vector, UV:Vector, Object:Vector, Camera:Vector, Window:Vector, Reflection:Vector |
| ✅ | `ShaderNodeTexEnvironment` | Environment Texture | Vector:Vector | Color:Color |
| ✅ | `ShaderNodeTexGabor` | Gabor Texture | Vector:Vector, Scale:Float, Frequency:Float, Anisotropy:FloatFactor, Orientation:FloatAngle, Orientation:VectorDirection | Value:Float, Phase:Float, Intensity:Float |
| ✅ | `ShaderNodeTexGradient` | Gradient Texture | Vector:Vector | Color:Color, Factor:Float |
| ✅ | `ShaderNodeTexIES` | IES Texture | Vector:Vector, Strength:Float | Factor:Float |
| ✅ | `ShaderNodeTexImage` | Image Texture | Vector:Vector | Color:Color, Alpha:Float |
| ✅ | `ShaderNodeTexMagic` | Magic Texture | Vector:Vector, Scale:Float, Distortion:Float | Color:Color, Factor:Float |
| ✅ | `ShaderNodeTexNoise` | Noise Texture | Vector:Vector, W:Float, Scale:Float, Detail:Float, Roughness:FloatFactor, Lacunarity:Float, Offset:Float, Gain:Float, Distortion:Float | Factor:Float, Color:Color |
| ✅ | `ShaderNodeTexSky` | Sky Texture | Vector:Vector | Color:Color |
| ✅ | `ShaderNodeTexVoronoi` | Voronoi Texture | Vector:Vector, W:Float, Scale:Float, Detail:Float, Roughness:FloatFactor, Lacunarity:Float, Smoothness:FloatFactor, Exponent:Float, Randomness:FloatFactor | Distance:Float, Color:Color, Position:Vector, W:Float, Radius:Float |
| ✅ | `ShaderNodeTexWave` | Wave Texture | Vector:Vector, Scale:Float, Distortion:Float, Detail:Float, Detail Scale:Float, Detail Roughness:FloatFactor, Phase Offset:Float | Color:Color, Factor:Float |
| ✅ | `ShaderNodeTexWhiteNoise` | White Noise Texture | Vector:Vector, W:Float | Value:Float, Color:Color |
| ⚠ | `ShaderNodeTree` |  | RuntimeError: Error: Node type ShaderNodeTree undefined
 | — |
| ✅ | `ShaderNodeUVAlongStroke` | UV Along Stroke | — | UV:Vector |
| ✅ | `ShaderNodeUVMap` | UV Map | — | UV:Vector |
| ✅ | `ShaderNodeValToRGB` | Color Ramp | Factor:FloatFactor | Color:Color, Alpha:Float |
| ✅ | `ShaderNodeValue` | Value | — | Value:Float |
| ✅ | `ShaderNodeVectorCurve` | Vector Curves | Factor:FloatFactor, Vector:Vector | Vector:Vector |
| ✅ | `ShaderNodeVectorDisplacement` | Vector Displacement | Vector:Color, Midlevel:Float, Scale:Float | Displacement:Vector |
| ✅ | `ShaderNodeVectorMath` | Vector Math | Vector:Vector, Vector:Vector, Vector:Vector, Scale:Float | Vector:Vector, Value:Float |
| ✅ | `ShaderNodeVectorRotate` | Vector Rotate | Vector:Vector, Center:Vector, Axis:Vector, Angle:FloatAngle, Rotation:VectorEuler | Vector:Vector |
| ✅ | `ShaderNodeVectorTransform` | Vector Transform | Vector:Vector | Vector:Vector |
| ✅ | `ShaderNodeVertexColor` | Color Attribute | — | Color:Color, Alpha:Float |
| ✅ | `ShaderNodeVolumeAbsorption` | Volume Absorption | Color:Color, Density:Float, Weight:Float | Volume:Shader |
| ✅ | `ShaderNodeVolumeCoefficients` | Volume Coefficients | Weight:Float, Absorption Coefficients:Vector, Scatter Coefficients:Vector, Anisotropy:FloatFactor, IOR:FloatFactor, Backscatter:FloatFactor, Alpha:Float, Diameter:Float, Emission Coefficients:Vector | Volume:Shader |
| ✅ | `ShaderNodeVolumeInfo` | Volume Info | — | Color:Color, Density:Float, Flame:Float, Temperature:Float |
| ✅ | `ShaderNodeVolumePrincipled` | Principled Volume | Color:Color, Color Attribute:String, Density:Float, Density Attribute:String, Anisotropy:FloatFactor, Absorption Color:Color, Emission Strength:Float, Emission Color:Color, Blackbody Intensity:FloatFactor, Blackbody Tint:Color, Temperature:FloatColorTemperature, Temperature Attribute:String, Weight:Float | Volume:Shader |
| ✅ | `ShaderNodeVolumeScatter` | Volume Scatter | Color:Color, Density:Float, Anisotropy:FloatFactor, IOR:FloatFactor, Backscatter:FloatFactor, Alpha:Float, Diameter:Float, Weight:Float | Volume:Shader |
| ✅ | `ShaderNodeWavelength` | Wavelength | Wavelength:FloatWavelength | Color:Color |
| ✅ | `ShaderNodeWireframe` | Wireframe | Size:Float | Factor:Float |

### Texture 노드 — 38개

| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |
|---|---|---|---|---|
| ⚠ | `TextureNode` |  | RuntimeError: Error: Node type TextureNode undefined
 | — |
| ✅ | `TextureNodeAt` | At | Texture:Color, Coordinates:Vector | Texture:Color |
| ✅ | `TextureNodeBricks` | Bricks | Bricks 1:Color, Bricks 2:Color, Mortar:Color, Thickness:FloatUnsigned, Bias:Float, Brick Width:FloatUnsigned, Row Height:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeChecker` | Checker | Color1:Color, Color2:Color, Size:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeCombineColor` | Combine Color | Red:FloatFactor, Green:FloatFactor, Blue:FloatFactor, Alpha:FloatFactor | Color:Color |
| ⚠ | `TextureNodeCompose` |  | RuntimeError: Error: Node type TextureNodeCompose undefined
 | — |
| ✅ | `TextureNodeCoordinates` | Coordinates | — | Coordinates:Vector |
| ✅ | `TextureNodeCurveRGB` | RGB Curves | Color:Color | Color:Color |
| ✅ | `TextureNodeCurveTime` | Time | — | Value:Float |
| ⚠ | `TextureNodeDecompose` |  | RuntimeError: Error: Node type TextureNodeDecompose undefine | — |
| ✅ | `TextureNodeDistance` | Distance | Coordinate 1:Vector, Coordinate 2:Vector | Value:Float |
| ✅ | `TextureNodeGroup` | Group | — | — |
| ✅ | `TextureNodeHueSaturation` | Hue/Saturation/Value | Hue:Float, Saturation:Float, Value:Float, Factor:Float, Color:Color | Color:Color |
| ✅ | `TextureNodeImage` | Image | — | Image:Color |
| ✅ | `TextureNodeInvert` | Invert Color | Color:Color | Color:Color |
| ✅ | `TextureNodeMath` | Math | Value:Float, Value:Float, Value:Float | Value:Float |
| ✅ | `TextureNodeMixRGB` | Mix | Factor:Float, Color1:Color, Color2:Color | Color:Color |
| ✅ | `TextureNodeOutput` | Output | Color:Color | — |
| ✅ | `TextureNodeRGBToBW` | RGB to BW | Color:Color | Val:Float |
| ✅ | `TextureNodeRotate` | Rotate | Color:Color, Turns:Float, Axis:VectorDirection | Color:Color |
| ✅ | `TextureNodeScale` | Scale | Color:Color, Scale:VectorXYZ | Color:Color |
| ✅ | `TextureNodeSeparateColor` | Separate Color | Color:Color | Red:Float, Green:Float, Blue:Float, Alpha:Float |
| ✅ | `TextureNodeTexBlend` | Blend | Color 1:Color, Color 2:Color | Color:Color |
| ✅ | `TextureNodeTexClouds` | Clouds | Color 1:Color, Color 2:Color, Size:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexDistNoise` | Distorted Noise | Color 1:Color, Color 2:Color, Size:FloatUnsigned, Distortion:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexMagic` | Magic | Color 1:Color, Color 2:Color, Turbulence:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexMarble` | Marble | Color 1:Color, Color 2:Color, Size:FloatUnsigned, Turbulence:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexMusgrave` | Musgrave | Color 1:Color, Color 2:Color, H:FloatUnsigned, Lacunarity:FloatUnsigned, Octaves:FloatUnsigned, iScale:FloatUnsigned, Size:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexNoise` | Noise | Color 1:Color, Color 2:Color | Color:Color |
| ✅ | `TextureNodeTexStucci` | Stucci | Color 1:Color, Color 2:Color, Size:FloatUnsigned, Turbulence:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexVoronoi` | Voronoi | Color 1:Color, Color 2:Color, W1:Float, W2:Float, W3:Float, W4:Float, iScale:FloatUnsigned, Size:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexWood` | Wood | Color 1:Color, Color 2:Color, Size:FloatUnsigned, Turbulence:FloatUnsigned | Color:Color |
| ✅ | `TextureNodeTexture` | Texture | Color1:Color, Color2:Color | Color:Color |
| ✅ | `TextureNodeTranslate` | Translate | Color:Color, Offset:VectorTranslation | Color:Color |
| ⚠ | `TextureNodeTree` |  | RuntimeError: Error: Node type TextureNodeTree undefined
 | — |
| ✅ | `TextureNodeValToNor` | Value to Normal | Val:Float, Nabla:FloatUnsigned | Normal:Vector |
| ✅ | `TextureNodeValToRGB` | Color Ramp | Fac:FloatFactor | Color:Color |
| ✅ | `TextureNodeViewer` | Viewer | Color:Color | — |

### 기타 노드 — 6개

| | `bl_idname` | 라벨 | 입력 (이름:타입) | 출력 (이름:타입) |
|---|---|---|---|---|
| ⚠ | `NodeCustomGroup` |  | RuntimeError: Error: Node type NodeCustomGroup undefined
 | — |
| ✅ | `NodeGroupInput` | Group Input | — | :Virtual |
| ✅ | `NodeGroupOutput` | Group Output | :Virtual | — |
| ⚠ | `NodeInternal` |  | RuntimeError: Error: Node type NodeInternal undefined
 | — |
| ⚠ | `NodeInternalSocketTemplate` |  | RuntimeError: Error: Node type NodeInternalSocketTemplate un | — |
| ✅ | `NodeReroute` | Reroute | Input:Color | Output:Color |

## 3. 타입 열거형 전수

| 속성 | 값 |
|---|---|
| `Object.type` | `MESH`, `CURVE`, `SURFACE`, `META`, `FONT`, `CURVES`, `POINTCLOUD`, `VOLUME`, `GREASEPENCIL`, `ARMATURE`, `LATTICE`, `EMPTY`, `LIGHT`, `LIGHT_PROBE`, `CAMERA`, `SPEAKER` |
| `Modifier.type` | `GREASE_PENCIL_VERTEX_WEIGHT_PROXIMITY`, `DATA_TRANSFER`, `MESH_CACHE`, `MESH_SEQUENCE_CACHE`, `NORMAL_EDIT`, `WEIGHTED_NORMAL`, `UV_PROJECT`, `UV_WARP`, `VERTEX_WEIGHT_EDIT`, `VERTEX_WEIGHT_MIX`, `VERTEX_WEIGHT_PROXIMITY`, `GREASE_PENCIL_COLOR`, `GREASE_PENCIL_TINT`, `GREASE_PENCIL_OPACITY`, `GREASE_PENCIL_VERTEX_WEIGHT_ANGLE`, `GREASE_PENCIL_TIME`, `GREASE_PENCIL_TEXTURE`, `ARRAY`, `BEVEL`, `BOOLEAN`, `BUILD`, `DECIMATE`, `EDGE_SPLIT`, `NODES`, `MASK`, `MIRROR`, `MESH_TO_VOLUME`, `MULTIRES`, `REMESH`, `SCREW`, `SKIN`, `SOLIDIFY`, `SUBSURF`, `TRIANGULATE`, `VOLUME_TO_MESH`, `WELD`, `WIREFRAME`, `GREASE_PENCIL_ARRAY`, `GREASE_PENCIL_BUILD`, `GREASE_PENCIL_LENGTH`, `LINEART`, `GREASE_PENCIL_MIRROR`, `GREASE_PENCIL_MULTIPLY`, `GREASE_PENCIL_SIMPLIFY`, `GREASE_PENCIL_SUBDIV`, `GREASE_PENCIL_ENVELOPE`, `GREASE_PENCIL_OUTLINE`, `ARMATURE`, `CAST`, `CURVE`, `DISPLACE`, `HOOK`, `LAPLACIANDEFORM`, `LATTICE`, `MESH_DEFORM`, `SHRINKWRAP`, `SIMPLE_DEFORM`, `SMOOTH`, `CORRECTIVE_SMOOTH`, `LAPLACIANSMOOTH`, `SURFACE_DEFORM`, `WARP`, `WAVE`, `VOLUME_DISPLACE`, `GREASE_PENCIL_HOOK`, `GREASE_PENCIL_NOISE`, `GREASE_PENCIL_OFFSET`, `GREASE_PENCIL_SMOOTH`, `GREASE_PENCIL_THICKNESS`, `GREASE_PENCIL_LATTICE`, `GREASE_PENCIL_DASH`, `GREASE_PENCIL_ARMATURE`, `GREASE_PENCIL_SHRINKWRAP`, `CLOTH`, `COLLISION`, `DYNAMIC_PAINT`, `EXPLODE`, `FLUID`, `OCEAN`, `PARTICLE_INSTANCE`, `PARTICLE_SYSTEM`, `SOFT_BODY`, `SURFACE` |
| `Constraint.type` | `CAMERA_SOLVER`, `FOLLOW_TRACK`, `OBJECT_SOLVER`, `COPY_LOCATION`, `COPY_ROTATION`, `COPY_SCALE`, `COPY_TRANSFORMS`, `LIMIT_DISTANCE`, `LIMIT_LOCATION`, `LIMIT_ROTATION`, `LIMIT_SCALE`, `MAINTAIN_VOLUME`, `TRANSFORM`, `TRANSFORM_CACHE`, `CLAMP_TO`, `DAMPED_TRACK`, `IK`, `LOCKED_TRACK`, `SPLINE_IK`, `STRETCH_TO`, `TRACK_TO`, `ACTION`, `ARMATURE`, `CHILD_OF`, `FLOOR`, `FOLLOW_PATH`, `GEOMETRY_ATTRIBUTE`, `PIVOT`, `SHRINKWRAP` |
| `Light.type` | `POINT`, `SUN`, `SPOT`, `AREA` |
| `Camera.type` | `PERSP`, `ORTHO`, `PANO`, `CUSTOM` |
| `ParticleSettings.type` | `EMITTER`, `HAIR` |
| `ParticleSettings.render_type` | `NONE`, `HALO`, `LINE`, `PATH`, `OBJECT`, `COLLECTION` |
| `ParticleSettings.physics_type` | `NO`, `NEWTON`, `KEYED`, `BOIDS`, `FLUID` |
| `Image.source` | `FILE`, `SEQUENCE`, `MOVIE`, `GENERATED`, `VIEWER`, `TILED` |
| `Image.file_format(deprecated)` | `AVIF`, `JPEG`, `OPEN_EXR`, `PNG`, `WEBP`, `BMP`, `CINEON`, `DPX`, `IRIS`, `JPEG2000`, `HDR`, `TARGA`, `TARGA_RAW`, `TIFF`, `OPEN_EXR_MULTILAYER`, `FFMPEG` |
| `Brush.stroke_method` | `DOTS`, `DRAG_DOT`, `SPACE`, `AIRBRUSH`, `ANCHORED`, `LINE`, `CURVE` |
| `Keyframe.interpolation` | `CONSTANT`, `LINEAR`, `BEZIER`, `SINE`, `QUAD`, `CUBIC`, `QUART`, `QUINT`, `EXPO`, `CIRC`, `BACK`, `BOUNCE`, `ELASTIC` |
| `Keyframe.easing` | `AUTO`, `EASE_IN`, `EASE_OUT`, `EASE_IN_OUT` |
| `ShapeKey.interpolation` | `KEY_LINEAR`, `KEY_CARDINAL`, `KEY_CATMULL_ROM`, `KEY_BSPLINE` |
| `Curve.fill_mode` | `FULL`, `BACK`, `FRONT`, `HALF` |
| `Curve.dimensions` | `2D`, `3D` |
| `Spline.type` | `POLY`, `BEZIER`, `NURBS` |
| `Mesh.mirror_axis` | *(조회 불가 — 런타임 등록 enum)* |
| `MovieClip.tracker.type` | *(조회 불가 — 런타임 등록 enum)* |
| `Sound.pack_method` | *(조회 불가 — 런타임 등록 enum)* |
| `World.node_tree.type` | *(조회 불가 — 런타임 등록 enum)* |

## 4. `bpy.data` 컬렉션 전수

| 컬렉션 | 현재 원소 수 |
|---|---|
| `bpy.data.actions` | 0 |
| `bpy.data.annotations` | 0 |
| `bpy.data.armatures` | 0 |
| `bpy.data.brushes` | 0 |
| `bpy.data.cameras` | 1 |
| `bpy.data.collections` | 1 |
| `bpy.data.curves` | 0 |
| `bpy.data.grease_pencils` | 0 |
| `bpy.data.hair_curves` | 0 |
| `bpy.data.images` | 2 |
| `bpy.data.lattices` | 0 |
| `bpy.data.lightprobes` | 0 |
| `bpy.data.lights` | 1 |
| `bpy.data.linestyles` | 1 |
| `bpy.data.masks` | 0 |
| `bpy.data.materials` | 2 |
| `bpy.data.meshes` | 1 |
| `bpy.data.metaballs` | 0 |
| `bpy.data.node_groups` | 0 |
| `bpy.data.objects` | 3 |
| `bpy.data.palettes` | 1 |
| `bpy.data.particles` | 0 |
| `bpy.data.pointclouds` | 0 |
| `bpy.data.scenes` | 1 |
| `bpy.data.speakers` | 0 |
| `bpy.data.texts` | 0 |
| `bpy.data.textures` | 0 |
| `bpy.data.volumes` | 0 |
| `bpy.data.worlds` | 1 |

## 5. 최상위 모듈 표면

### `bpy` — 9개

```
app
context
data
msgbus
ops
path
props
types
utils
```

### `bpy.app` — 71개

```
alembic
autoexec_fail
autoexec_fail_message
autoexec_fail_quiet
background
binary_path
build_branch
build_cflags
build_commit_date
build_commit_time
build_commit_timestamp
build_cxxflags
build_date
build_hash
build_linkflags
build_options
build_platform
build_system
build_time
build_type
cachedir
count
debug
debug_depsgraph
debug_depsgraph_build
debug_depsgraph_eval
debug_depsgraph_pretty
debug_depsgraph_tag
debug_depsgraph_time
debug_events
debug_freestyle
debug_handlers
debug_io
debug_python
debug_simdata
debug_value
debug_wm
driver_namespace
factory_startup
ffmpeg
handlers
help_text
icons
index
is_job_running
memory_usage_undo
module
n_fields
n_sequence_fields
n_unnamed_fields
ocio
oiio
online_access
online_access_override
opensubdiv
openvdb
portable
python_args
render_icon_size
render_preview_size
sdl
tempdir
timers
translations
usd
use_event_simulate
use_userpref_skip_save_on_exit
version
version_cycle
version_file
version_string
```

### `bpy.utils` — 45개

```
app_template_paths
blend_paths
escape_identifier
execfile
expose_bundled_modules
extension_path_user
flip_name
is_path_builtin
is_path_extension
keyconfig_init
keyconfig_set
load_scripts
load_scripts_extensions
make_rna_paths
manual_language_code
manual_map
modules_from_path
preset_find
preset_paths
refresh_script_paths
register_class
register_classes_factory
register_cli_command
register_manual_map
register_preset_path
register_submodule_factory
register_tool
resource_path
script_path_user
script_paths
script_paths_pref
script_paths_system_environment
smpte_from_frame
smpte_from_seconds
system_resource
time_from_frame
time_to_frame
unescape_identifier
units
unregister_class
unregister_cli_command
unregister_manual_map
unregister_preset_path
unregister_tool
user_resource
```

### `bpy.path` — 17개

```
abspath
basename
clean_name
display_name
display_name_from_filepath
display_name_to_filepath
ensure_ext
extensions_audio
extensions_image
extensions_movie
is_autoexec
is_subdir
module_names
native_pathsep
reduce_dirs
relpath
resolve_ncase
```

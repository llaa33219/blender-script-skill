# 시뮬레이션 & 파티클 시스템 (Blender 5.2.2 LTS, headless 검증 완결)

> **대상**: `blender` 5.2.2 LTS (`d13f752e3b9c`, 2026-09-15), Linux x64, 번들 Python 3.13.13
> **실행 패턴**: `blender -b --factory-startup -noaudio --python-exit-code 1 --python script.py`
> **문서 내 모든 코드**는 위 환경에서 실행되어 `__SCRIPT_OK__` 를 냈다. 검증 스크립트는
> `/workspace/build/gap-sim/verify/` 에 남겨 두었다. 마지막에 `## Verification log` 에 전수 정리.

---

## 0. 5.2 에서 사라진 것들 먼저 (가장 많이 틀리는 부분)

5.x 는 legacy particle/sim API 를 대폭 잘라냈다. **아래 이름들은 5.2 에 존재하지 않는다.**
`hasattr(bpy.ops.object, "softbody_add")` 은 **항상 True** 를 반환하므로 절대 쓰면 안 된다
(§9.1). 정답 검사는 `dir()` 이다.

| 옛 API | 5.2 상태 | 대체 |
|---|---|---|
| `bpy.ops.object.softbody_add()` | ❌ 제거 (`dir()` 에 없음) | `obj.modifiers.new(name, 'SOFT_BODY')` |
| `bpy.ops.object.cloth_add()` | ❌ 제거 | `obj.modifiers.new(name, 'CLOTH')` |
| `bpy.ops.object.fluid_add()` | ❌ 제거 | `obj.modifiers.new(name, 'FLUID')` |
| `bpy.ops.object.dupevoter_paint()` | ❌ 제거 | `obj.modifiers.new(name, 'DYNAMIC_PAINT')` |
| `bpy.ops.object.rigidbody_add()` | ❌ 없음 (원래도 없음) | `bpy.ops.rigidbody.object_add()` |
| `bpy.ops.object.forcefield_add()` | ❌ 없음 (원래도 없음) | `bpy.ops.object.effector_add(type=...)` |
| `bpy.ops.particle.particle_add()` | ❌ 없음 (원래도 없음) | `bpy.ops.object.particle_system_add()` |
| `bpy.ops.particle.edit_toggle()` | ❌ 없음 | `bpy.ops.particle.particle_edit_toggle()` |
| `bpy.ops.particle.smooth()` | ❌ 없음 (원래도 없음) | `remove_doubles()` / `unify_length()` |
| `bpy.ops.particle.mute()` | ❌ 없음 (원래도 없음) | `bpy.ops.particle.hide()` |
| `bpy.ops.particle.clear()` | ❌ 없음 | `bpy.ops.particle.edited_clear()` |
| `bpy.ops.particle.duplicate()` | ❌ 없음 | `particle.mirror()` / `duplicate_particle_system()` |
| `bpy.ops.ptcache.is_baking()` | ❌ 없음 | `point_cache.is_baking` (프로퍼티) |
| `bpy.ops.ptcache.filepath_get/set()` | ❌ 없음 | `point_cache.filepath` (프로퍼티) |
| `bpy.ops.ptcache.external_bake/override()` | ❌ 없음 | — |
| `bpy.data.fluids` / `fluid_domains` / `fluid_flows` | ❌ 컬렉션 자체가 없음 | `modifier.domain_settings` / `.flow_settings` |
| `bpy.types.RigidBodySettings` | ❌ 타입 없음 | `RigidBodyWorld` 가 world 설정을 직접 가짐 (§3) |
| `bpy.types.HairKey` | ❌ 타입 없음 | `bpy.types.ParticleHairKey` (`time`/`weight`/`co`/`co_local`) |
| `bpy.types.FluidModifierSettings` | ❌ 없음 | `FluidDomainSettings` / `FluidFlowSettings` / `FluidEffectorSettings` |
| `SoftBodyModifier.collision` | ❌ 없음 | 5.2 에서 soft body 충돌 설정 자체가 제거 |
| `ParticleSettings.goal_type` (soft body) | ❌ 없음 | `use_goal` + `goal_min/max/default/spring/friction` |
| `ParticleSettings.emission_shape` | ❌ 없음 | `distribution` (JIT/RAND/GRID) |
| `ParticleSettings.path_duration` | ❌ 없음 | `ParticleTarget.duration` |
| `ClothModifier.solver_result` | ⚠ 항상 `None` (5.2 내부 전용) | `modifier.use_pin_to_last` 를 직접 쓴다 |

---

## 1. 물리 시뮬레이션 공통 규칙 (이 문서 나머지 전부가 여기에 의존)

### 1.1 물리는 "프레임을 건너뛰면 따라잡지 않는다"

Blender 5.2 의 PT 솔버는 `scene.frame_set()` 한 번으로 **최대 몇 프레임까지만** catch-up 한다.
1 → 5 → 10 → 20 처럼 크게 뛰면 **시뮬레이션이 아예 진행되지 않고 초기 자세가 유지된다.**
검증 (`verify/05c_rb_jump.py`):

```
```
TEST 1  sequential frame_set 1..12          f=1 z=3.00000 ... f=12 z=1.96664   OK
TEST 2  JUMPING 1,5,10,20,30                f=1 z=3.00000 ... f=30 z=3.00000   x
TEST 3  JUMPING, frame_set(f) 를 두 번씩      f=30 z=3.00000                    x
TEST 4  JUMPING with subframe=0.0           f=30 z=3.00000                    x
TEST 5  bake first, then jump               f=5 z=2.86065, f=20 z=0.50000     OK
TEST 6  full sequential run, then sample     f=10 z=2.30608, f=50 z=0.50000    OK
```

**규칙**: ① 1..N 을 순차 `frame_set` 하거나 ② 먼저 bake 한다. 둘 중 하나는 반드시.
`frame_set(f)` 후 `bpy.context.evaluated_depsgraph_get()` 를 매번 새로 잡아야 한다.

### 1.2 읽는 곳: 원본이 아니라 `evaluated_get()`

물리 결과는 원본 `bpy` 데이터에 쓰이지 않는다. **평가된(depsgraph) 복사본에서 읽어야 한다.**

```python
sc.frame_set(f)
dg = bpy.context.evaluated_depsgraph_get()
ev = obj.evaluated_get(dg)
matrix = ev.matrix_world          # 리지드바디 결과
mesh  = ev.to_mesh()              # 클로스 / 소프트바디 결과
```

§5.4 에서 보듯 파티클은 이 규칙이 더 급하다: `ps.particles` 는 원본에서 **영원히 비어 있다**.

### 1.3 bake 는 "프레임 범위" 를 따로 가진다

`scene.frame_start/frame_end` 와 무관하다. 각 `PointCache` 마다 따로 있다.
특히 **리지드바디 월드**는 기본값이 `1..250` 이다. 50 프레임만 시뮬레이션하려고
`ptcache.bake_all` 을 부르면 250프레임을 전부 굽는다 (검증 `verify/16` 에서
`bake: frame 1 :: 250` … `bake: frame 250 :: 250` 로그가 실제로 찍혔다).

```python
sc.rigidbody_world.point_cache.frame_start = 1
sc.rigidbody_world.point_cache.frame_end   = 50
```

### 1.4 `PointCache.info` 가 유일한 신뢰할 수 있는 진단 문자열

`is_baked` 만으로는 "디스크에 really 썼나" 를 알 수 없다 (§7.2). `info` 를 봐라.

| 상황 | `point_cache.info` | `is_baked` |
|---|---|---|
| 메모리 캐시 | `'50 frames in memory (92 KiB).'` | True |
| 디스크 캐시 | `'6 frames on disk.'` | True |
| 아무것도 안 돌림 | `'0 frames in memory (0 B).'` | False |
| 실행 전 (소프트바디) | `''` | False |

---

## 2. Soft Body

### 2.1 생성

```python
import bpy
m = obj.modifiers.new("SoftBody", 'SOFT_BODY')   # 또는
m = obj.modifiers.new("SoftBody", 'SOFT_BODY')
```

`bpy.ops.object.softbody_add()` 은 5.2 에 **존재하지 않는다** (verify/22_gaps.py 출력:
`'softbody_add' in dir: False`).

### 2.2 `SoftBodyModifier` (속성 15개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 | 비고 |
|---|---|---|---|---|
| `execution_time` | FLOAT | RO | 0.0 | 마지막 평가 시간(초) |
| `is_active` | BOOLEAN | RW | False | |
| `is_override_data` | BOOLEAN | RO | True | ID 오버라이드 |
| `name` | STRING | RW | `''` | |
| `persistent_uid` | INT | RO | 0 | 5.x 슬롯 ID |
| `point_cache` | → PointCache | RO | | §6.5 표 참조 |
| `settings` | → SoftBodySettings | RO | | 아래 표 |
| `show_expanded` | BOOLEAN | RW | False | UI 전용 |
| `show_in_editmode` | BOOLEAN | RW | False | UI 전용 |
| `show_on_cage` | BOOLEAN | RW | False | UI 전용 |
| `show_render` | BOOLEAN | RW | False | |
| `show_viewport` | BOOLEAN | RW | False | |
| `type` | ENUM | RO | — | 모디파이어 타입 (SOFT_BODY) |
| `use_apply_on_spline` | BOOLEAN | RW | False | 스플라인 전용 |
| `use_pin_to_last` | BOOLEAN | RW | False | |

**5.2 에서 `SoftBodyModifier.collision` 이 제거됐다.** (verify/01: `has .collision: False`)

### 2.3 `SoftBodySettings` (속성 44개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 | 의미 |
|---|---|---|---|---|
| `aero` | INT | RW | 0 | 공기 저항 |
| `aerodynamics_type` | ENUM | RW | SIMPLE | `SIMPLE` \| `LIFT_FORCE` |
| `ball_damp` | FLOAT | RW | 0.0 | 공 파동 감쇠 |
| `ball_size` | FLOAT | RW | 0.0 | 충격파 크기 |
| `ball_stiff` | FLOAT | RW | 0.0 | 충격파 강성 |
| `bend` | FLOAT | RW | 0.0 | 굽힘 강성 |
| `choke` | INT | RW | 0 | 구멍 억제 |
| `collision_collection` | → Collection | RW | None | |
| `collision_type` | ENUM | RW | MANUAL | `MANUAL`\|`AVERAGE`\|`MINIMAL`\|`MAXIMAL`\|`MINMAX` |
| `damping` | FLOAT | RW | 0.0 | |
| `effector_weights` | → EffectorWeights | RO | | §6.4 |
| `error_threshold` | FLOAT | RW | 0.0 | 수렴 허용오차 |
| `friction` | FLOAT | RW | 0.0 | 표면 마찰 |
| `fuzzy` | INT | RW | 0 | 퍼지 목표 |
| `goal_default` | FLOAT | RW | 0.0 | **범위 0..1** 정규화 목표 |
| `goal_friction` | FLOAT | RW | 0.0 | |
| `goal_max` | FLOAT | RW | 0.0 | **범위 0..1** |
| `goal_min` | FLOAT | RW | 0.0 | **범위 0..1** |
| `goal_spring` | FLOAT | RW | 0.0 | |
| `gravity` | FLOAT | RW | 0.0 | 중력 가속 (effectors 비활성 시) |
| `location_mass_center` | FLOAT | RW | 0.0 | 무게중심 Z 보정 |
| `mass` | FLOAT | RW | 0.0 | |
| `plastic` | INT | RW | 0 | 소성 변형 |
| `pull` | FLOAT | RW | 0.0 | 인장 |
| `push` | FLOAT | RW | 0.0 | 압축 |
| `rotation_estimate` | FLOAT | RW | 0.0 | 회전 추정 |
| `scale_estimate` | FLOAT | RW | 0.0 | 스케일 추정 |
| `shear` | FLOAT | RW | 0.0 | 전단 |
| `speed` | FLOAT | RW | 0.0 | |
| `spring_length` | INT | RW | 0 | 스프링 길이 |
| `step_max` | INT | RW | 0 | 최대 서브스텝 |
| `step_min` | INT | RW | 0 | 최소 서브스텝 |
| `use_auto_step` | BOOLEAN | RW | False | |
| `use_diagnose` | BOOLEAN | RW | False | |
| `use_edge_collision` | BOOLEAN | RW | False | |
| `use_edges` | BOOLEAN | RW | False | |
| `use_estimate_matrix` | BOOLEAN | RW | False | |
| `use_face_collision` | BOOLEAN | RW | False | |
| `use_goal` | BOOLEAN | RW | False | **goal 시스템 on/off** |
| `use_self_collision` | BOOLEAN | RW | False | |
| `use_stiff_quads` | BOOLEAN | RW | False | |
| `vertex_group_goal` | STRING | RW | `''` | |
| `vertex_group_mass` | STRING | RW | `''` | |
| `vertex_group_spring` | STRING | RW | `''` | |

> **goal 설정**: 예전 `goal_type` enum 은 없어졌다. 지금은 `use_goal=True` 로 켜고
> `goal_min` / `goal_max` / `goal_default` 로 정점별 목표를 준다. 세 값 모두 **0..1 로 clamp**
> 된다 (verify/19 에서 `min=2.0` 넣었더니 `1.0` 로 저장됐다).

### 2.4 검증된 예제 — 떨어지는 소프트바디

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 20
sc.render.fps = 24
sc.frame_set(1)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 6))
sb = bpy.context.object
sb.name = "SB"
sm = sb.modifiers.new("SoftBody", 'SOFT_BODY')
s = sm.settings
s.mass = 0.3
s.friction = 0.6
s.error_threshold = 0.001
s.use_goal = False            # goal 없이 자유 낙하
s.damping = 0.5
s.bend = 0.5
s.push = 0.3
s.pull = 0.2
s.step_min, s.step_max = 3, 8
s.use_auto_step = True
s.effector_weights.gravity = 1.0
sm.point_cache.frame_start, sm.point_cache.frame_end = 1, 20

for f in range(1, 21):
    sc.frame_set(f)
    if f in (1, 5, 10, 20):
        eo = sb.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = eo.to_mesh()
        vs = [v.co for v in me.vertices]
        print("f=%-3d verts=%d bbox z[%.5f,%.5f] avg=%.5f" % (
            f, len(vs), min(v.z for v in vs), max(v.z for v in vs),
            sum(v.z for v in vs) / len(vs)))
        eo.to_mesh_clear()
print(sm.point_cache.info)
print("__SCRIPT_OK__")
```

측정 출력:

```
f=1   verts=8  bbox z[-0.50000, 0.50000]  avg= 0.00000
f=5   verts=8  bbox z[-0.58273, 0.41727]  avg=-0.08273
f=10  verts=8  bbox z[-0.88799, 0.11201]  avg=-0.38799
f=20  verts=8  bbox z[-2.09209,-1.09209]  avg=-1.59209
20 frames in memory (6 KiB).
__SCRIPT_OK__
```

`to_mesh()` 는 **오브젝트 로컬 좌표**를 준다 (오브젝트가 z=6 에 있어도 z≈-2 가 나온다).
원본 `sb.data.vertices[0].co` 는 끝까지 `(-0.5,-0.5,-0.5)` 로 안 바뀐다.

### 2.5 오퍼레이터 판정

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `bpy.ops.object.softbody_add` | ❌ **제거됨** | `dir(bpy.ops.object)` 에 없음. 호출 시 `AttributeError: could not be found` |
| `bpy.ops.object.softbody_preset_add` | ❌ **존재하지 않음** | `dir(bpy.ops.object)` 에 없음 (5.2 에 `softbody_preset_add` 없음) |
| `bpy.ops.ptcache.bake_all` (soft body 포함) | ✅ | §7.1 에서 검증 |

소프트바디 프리셋은 `bpy.ops.object.softbody_preset_add` 인 UI 버튼뿐이고, 그 자체가 5.2 에
없다. 헤드리스에서는 위처럼 `settings.*` 를 직접 세팅하는 수밖에 없다.

### 2.6 함정

* 소프트바디는 정점이 적으면(8개) 거의 강체처럼 떨어진다. 실전 cloth 와 다른 솔버다.
* `use_goal=False` 이면 `goal_*` 값은 아무 효과가 없다. **goal 이 안 먹는 것처럼 보여도**
  `use_goal` 을 확인하라.
* `goal_min/max` 는 0..1 clamp. 월드 좌표 목표를 넣고 싶으면 오브젝트 스케일로 처리해야 한다.
* `point_cache.info` 가 시뮬레이션 **전**에는 빈 문자열 `''` 이다.

---

## 3. Cloth

### 3.1 생성

```python
m = obj.modifiers.new("Cloth", 'CLOTH')
# 또는 UI 경로와 동일하게
bpy.ops.object.modifier_add(type='CLOTH')   # → modifiers=['Cloth']
```

`bpy.ops.object.cloth_add()` 은 5.2 에 **없다** (verify/22: `'cloth_add' in dir: False`).

### 3.2 `ClothModifier` (속성 20개, 전수)

| 프로퍼티 | 타입 | R/W | 비고 |
|---|---|---|---|
| `collision_settings` | → ClothCollisionSettings | RO | §3.4 |
| `execution_time` | FLOAT | RO | |
| `hair_grid_max` | FLOAT[3] | RO | 헤어 그리드 |
| `hair_grid_min` | FLOAT[3] | RO | |
| `hair_grid_resolution` | INT | RO | |
| `is_active` | BOOLEAN | RW | |
| `is_override_data` | BOOLEAN | RO | |
| `name` | STRING | RW | |
| `persistent_uid` | INT | RO | |
| `point_cache` | → PointCache | RO | §6.5 |
| `settings` | → ClothSettings | RO | §3.3 |
| `show_expanded` / `show_in_editmode` / `show_on_cage` / `show_render` / `show_viewport` | BOOLEAN | RW | UI |
| `solver_result` | → ClothSolverResult | RO | **항상 `None`** |
| `type` | ENUM | RO | |
| `use_apply_on_spline` | BOOLEAN | RW | |
| `use_pin_to_last` | BOOLEAN | RW | 5.x 새 핀 방식 |

> `solver_result` 는 `use_pin_cloth` / `use_pin_to_last` 를 가진 타입인데,
> **5.2 헤드리스에서는 시뮬레이션을 돌려도 계속 `None`** 이다
> (verify/06: `solver_result BEFORE any frame_set: None` → `AFTER steps: None`).
> `modifier.use_pin_to_last` 를 직접 세팅하라.

### 3.3 `ClothSettings` (속성 57개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 | 의미 |
|---|---|---|---|---|
| `air_damping` | FLOAT | RW | 0.1 | 공기 저항 (가장 자주 씀) |
| `bending_damping` | FLOAT | RW | 0.5 | |
| `bending_model` | ENUM | RW | ANGULAR | `ANGULAR` \| `LINEAR` |
| `bending_stiffness` | FLOAT | RW | 0.5 | 굽힘 강성 |
| `bending_stiffness_max` | FLOAT | RW | 0.5 | |
| `collider_friction` | FLOAT | RW | 0.0 | |
| `compression_damping` | FLOAT | RW | 0.0 | |
| `compression_stiffness` | FLOAT | RW | 15.0 | |
| `compression_stiffness_max` | FLOAT | RW | 15.0 | |
| `density_strength` | FLOAT | RW | 1.0 | 밀도 기반 강성 |
| `density_target` | FLOAT | RW | 1.0 | |
| `effector_weights` | → EffectorWeights | RO | | §6.4 |
| `fluid_density` | FLOAT | RW | 0.0 | 유체 밀도 |
| `goal_default` | FLOAT | RW | 0.0 | 셰이프키 목표 |
| `goal_friction` | FLOAT | RW | 0.0 | |
| `goal_max` | FLOAT | RW | 0.0 | |
| `goal_min` | FLOAT | RW | 0.0 | |
| `goal_spring` | FLOAT | RW | 0.0 | |
| `gravity` | FLOAT[3] | RW | (0,0,-9.81) | **개별 클로스 중력** |
| `internal_compression_stiffness` | FLOAT | RW | 15.0 | 내부 스프링 압축 |
| `internal_compression_stiffness_max` | FLOAT | RW | 15.0 | |
| `internal_friction` | FLOAT | RW | 0.0 | |
| `internal_spring_max_diversion` | FLOAT | RW | 0.5 | |
| `internal_spring_max_length` | FLOAT | RW | 0.0 | |
| `internal_spring_normal_check` | BOOLEAN | RW | False | |
| `internal_tension_stiffness` | FLOAT | RW | 15.0 | 내부 스프링 인장 |
| `internal_tension_stiffness_max` | FLOAT | RW | 15.0 | |
| `mass` | FLOAT | RW | 0.3 | 정점 질량 |
| `pin_stiffness` | FLOAT | RW | 1.0 | 핀 강성 |
| `pressure_factor` | FLOAT | RW | 0.0 | |
| `quality` | INT | RW | 5 | 솔버 스텝 |
| `rest_shape_key` | → ShapeKey | RW | None | |
| `sewing_force_max` | FLOAT | RW | 0.0 | |
| `shear_damping` | FLOAT | RW | 0.0 | |
| `shear_stiffness` | FLOAT | RW | 5.0 | |
| `shear_stiffness_max` | FLOAT | RW | 5.0 | |
| `shrink_max` | FLOAT | RW | 0.0 | |
| `shrink_min` | FLOAT | RW | 0.0 | |
| `target_volume` | FLOAT | RW | 1.0 | |
| `tension_damping` | FLOAT | RW | 0.0 | |
| `tension_stiffness` | FLOAT | RW | 15.0 | |
| `tension_stiffness_max` | FLOAT | RW | 15.0 | |
| `time_scale` | FLOAT | RW | 1.0 | |
| `uniform_pressure_force` | FLOAT | RW | 0.0 | |
| `use_dynamic_mesh` | BOOLEAN | RW | False | 매 프레임 재계산 |
| `use_internal_springs` | BOOLEAN | RW | False | |
| `use_pressure` | BOOLEAN | RW | False | |
| `use_pressure_volume` | BOOLEAN | RW | False | |
| `use_sewing_springs` | BOOLEAN | RW | False | |
| `vertex_group_bending` | STRING | RW | `''` | |
| `vertex_group_intern` | STRING | RW | `''` | |
| `vertex_group_mass` | STRING | RW | `''` | **핀 그룹 이름** |
| `vertex_group_pressure` | STRING | RW | `''` | |
| `vertex_group_shear_stiffness` | STRING | RW | `''` | |
| `vertex_group_shrink` | STRING | RW | `''` | |
| `vertex_group_structural_stiffness` | STRING | RW | `''` | |
| `voxel_cell_size` | FLOAT | RW | 0.0 | |

### 3.4 `ClothCollisionSettings` (13개) / `CollisionSettings` (15개)

**`ClothModifier.collision_settings`** (옛 `CollisionModifier.settings` 와 이름이 바뀜):

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `collection` | → Collection | RW | None |
| `collision_quality` | INT | RW | 2 |
| `damping` | FLOAT | RW | 1.0 |
| `distance_min` | FLOAT | RW | 0.015 |
| `friction` | FLOAT | RW | 5.0 |
| `impulse_clamp` | FLOAT | RW | 0.0 |
| `self_distance_min` | FLOAT | RW | 0.015 |
| `self_friction` | FLOAT | RW | 5.0 |
| `self_impulse_clamp` | FLOAT | RW | 0.0 |
| `use_collision` | BOOLEAN | RW | True |
| `use_self_collision` | BOOLEAN | RW | False |
| `vertex_group_object_collisions` | STRING | RW | `''` |
| `vertex_group_self_collisions` | STRING | RW | `''` |

**`CollisionModifier.settings`** (5.2 에서 이름이 `settings` 로 통일, 키가 `use` 로 바뀜):

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `use` | BOOLEAN | RW | **False** ← 여기가 on/off |
| `absorption` | FLOAT | RW | 0.0 |
| `cloth_friction` | FLOAT | RW | 0.0 |
| `damping` / `damping_factor` / `damping_random` | FLOAT | RW | 0.0 |
| `friction_factor` / `friction_random` | FLOAT | RW | 0.0 |
| `permeability` | FLOAT | RW | 0.0 |
| `stickiness` | FLOAT | RW | 0.0 |
| `thickness_inner` / `thickness_outer` | FLOAT | RW | 0.0 |
| `use_culling` | BOOLEAN | RW | False |
| `use_normal` | BOOLEAN | RW | False |
| `use_particle_kill` | BOOLEAN | RW | False |

> 함정: `CollisionSettings.use_collision` 는 **5.2 에 없다**. `settings.use = True` 다.

### 3.5 검증된 예제 — 핀 고정 클로ths 낙하

```python
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 40
sc.render.fps = 24
sc.frame_set(1)
sc.gravity = (0, 0, -9.81)

# 1) 클로스 평면 (z=4, 7x7 정점)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=6, y_subdivisions=6, size=2,
                                location=(0, 0, 4))
cloth = bpy.context.object
cloth.name = "Cloth"
print("grid verts:", len(cloth.data.vertices))

# 2) 핀 정점 그룹: 가장 위쪽 Y 행
vg = cloth.vertex_groups.new(name="Pin")
maxy = max(v.co.y for v in cloth.data.vertices)
top_idx = [v.index for v in cloth.data.vertices if v.co.y > maxy - 1e-4]
vg.add(top_idx, 1.0, 'REPLACE')
print("pin group 'Pin' verts:", top_idx)

# 3) 충돌 바닥
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.object
col = floor.modifiers.new("Collision", 'COLLISION')
col.settings.use = True
col.settings.thickness_outer = 0.02
col.settings.cloth_friction = 5.0

# 4) 클로스 모디파이어
m = cloth.modifiers.new("Cloth", 'CLOTH')
s = m.settings
s.quality = 5
s.mass = 0.3
s.air_damping = 1.0
s.tension_stiffness = 15.0
s.compression_stiffness = 15.0
s.shear_stiffness = 5.0
s.bending_stiffness = 0.5
s.tension_damping = 5.0
s.compression_damping = 5.0
s.shear_damping = 5.0
s.bending_damping = 0.5
s.vertex_group_mass = "Pin"
s.pin_stiffness = 1.0
s.effector_weights.gravity = 1.0
s.time_scale = 1.0

pc = m.point_cache
pc.frame_start, pc.frame_end = 1, 40
pc.use_disk_cache = False
pc.use_library_path = True

# 5) 순차 시뮬레이션 + 결과 읽기
for f in range(1, 41):
    sc.frame_set(f)
    if f in (1, 2, 5, 10, 20, 30, 40):
        dg = bpy.context.evaluated_depsgraph_get()
        eo = cloth.evaluated_get(dg)
        me = eo.to_mesh()
        n = len(me.vertices)
        cz = sum(v.co.z for v in me.vertices) / n
        lz = min(v.co.z for v in me.vertices)
        print("f=%-3d avg_z=%9.5f  lowest_z=%9.5f  nverts=%d" % (f, cz, lz, n))
        eo.to_mesh_clear()

# 6) 핀 정점이 실제로 고정됐는지 확인
sc.frame_set(40)
dg = bpy.context.evaluated_depsgraph_get()
eo = cloth.evaluated_get(dg)
me = eo.to_mesh()
print("pinned vert %d co @f40:" % top_idx[0],
      tuple(round(v, 5) for v in me.vertices[top_idx[0]].co))
print("free   vert 0 co @f40:",
      tuple(round(v, 5) for v in me.vertices[0].co))
eo.to_mesh_clear()
print("__SCRIPT_OK__")
```

측정 출력:

```
grid verts: 49
pin group 'Pin' verts: [42, 43, 44, 45, 46, 47, 48]
f=1   avg_z=  0.00000  lowest_z=  0.00000  nverts=49
f=2   avg_z= -0.00490  lowest_z= -0.00607  nverts=49
f=5   avg_z= -0.06441  lowest_z= -0.08329  nverts=49
f=10  avg_z= -0.28045  lowest_z= -0.38634  nverts=49
f=20  avg_z= -0.83579  lowest_z= -1.56735  nverts=49
f=30  avg_z= -0.98717  lowest_z= -1.95889  nverts=49
f=40  avg_z= -0.82388  lowest_z= -1.63357  nverts=49
pinned vert 42 co @f40: (-1.0, 1.0, 0.0)      <-- 정확히 고정
free   vert 0 co @f40: (-0.99997, 2.15421, -1.63357)
__SCRIPT_OK__
```

### 3.6 오퍼레이터 판정

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `bpy.ops.object.cloth_add` | ❌ **제거됨** | `dir()` 에 없음 |
| `bpy.ops.object.modifier_add(type='CLOTH')` | ✅ | `{'FINISHED'}`, `modifiers=['Cloth']` (verify/22) |
| `bpy.ops.cloth.preset_add` | ❌ | `poll()` 은 True 지만 실행 시 `AttributeError: 'Context' object has no attribute 'cloth'` → `{'CANCELLED'}` (verify/13) |

`cloth.preset_add` 의 실제 시그니처는 `(name: STRING, remove_name: BOOLEAN, remove_active: BOOLEAN)`
이고 `name` 은 **ENUM 이 아니라 STRING** 이다. 게다가 이 오퍼레이터는 `execute()` 안에서
`exec(preset_file)` 로 `context.cloth` 를 참조하므로 헤드리스에서 절대 동작하지 않는다.
(부수 효과로 `~/.config/blender/5.2/scripts/presets/cloth/cotton.py` 가 **생성된다**.)

### 3.7 함정

* **핀 그룹 이름 오타**는 `pin_stiffness` 처럼 조용히 실패한다. `settings.vertex_group_mass`
  가 빈 문자열이면 아무것도 안 고정된다. 검증 스크립트는 항상 그룹명을 echo 한다.
* `solver_result` 는 5.2 헤드리스에서 **항상 `None`**. 새 핀 API 를 기대하지 말 것.
* `to_mesh()` 결과는 반드시 `to_mesh_clear()` 로 해제한다 (leak).
* 클로스 평면은 `primitive_grid_add(x_subdivisions=N, y_subdivisions=N)` 로 만든다.
  subdiv 가 0 이면 정점 4개뿐이라 물리적으로 의미 없는 시뮬이 된다.
* 원본 `cloth.data.vertices` 는 절대 안 바뀐다. 검증 스크립트가 이걸 echo 해준다.

---

## 4. Rigid Body (핵심 델리버러블)

### 4.1 구조

```
scene.rigidbody_world           : RigidBodyWorld  (9 props)
  ├─ .collection                : Collection      (rigid body 객체들)
  ├─ .constraints               : Collection      (bpy.types.Collection, not prop_collection)
  ├─ .effector_weights          : EffectorWeights
  ├─ .point_cache               : PointCache
  ├─ .enabled / .solver_iterations / .substeps_per_frame
  ├─ .time_scale / .use_split_impulse

object.rigid_body               : RigidBodyObject  (18 props)
object.rigid_body_constraint    : RigidBodyConstraint (52 props)
```

> **`bpy.types.RigidBodySettings` 는 5.2 에 존재하지 않는다.**
> 옛 `scene.rigidbody_world.settings` 도 없다 (`AttributeError`).
> 월드 설정은 `RigidBodyWorld` 자신에 평탄화돼 있다. (verify/01)

### 4.2 `RigidBodyWorld` (9개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 | 비고 |
|---|---|---|---|---|
| `collection` | → Collection | RW | None | `world_add()` 직후엔 **`None`** |
| `constraints` | → Collection | RO | | `bpy.types.Collection` — `len()`/`반복` **불가** |
| `effector_weights` | → EffectorWeights | RO | | |
| `enabled` | BOOLEAN | RW | True | |
| `point_cache` | → PointCache | RO | | 기본 `1..250` |
| `solver_iterations` | INT | RW | 10 | Bullet 반복 |
| `substeps_per_frame` | INT | RW | 10 | |
| `time_scale` | FLOAT | RW | 1.0 | |
| `use_split_impulse` | BOOLEAN | RW | False | |

**`collection` 함정**: `bpy.ops.rigidbody.world_add()` 를 빈 씬에 부르면
`world.collection` 이 `None` 이다. 첫 `rigidbody.object_add()` 후에 만들어진다.

```python
bpy.ops.rigidbody.world_add()
w = bpy.context.scene.rigidbody_world
print(w.collection)     # -> None   (빈 씬)
```

**`constraints` 함정**: `w.constraints` 는 `bpy_prop_collection` 가 아니라
`bpy.types.Collection` 이다. `len()` 도, `for` 도 안 된다. `w.constraints.all_objects` 를 쓴다.

### 4.3 `RigidBodyObject` (18개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 | 비고 |
|---|---|---|---|---|
| `angular_damping` | FLOAT | RW | 0.04 | |
| `collision_collections` | BOOLEAN | RW | True | |
| `collision_margin` | FLOAT | RW | 0.04 | `use_margin` 과 함께 |
| `collision_shape` | ENUM | RW | CONVEX_HULL | **아래 표** |
| `deactivate_angular_velocity` | FLOAT | RW | 1.0 | |
| `deactivate_linear_velocity` | FLOAT | RW | 1.0 | |
| `enabled` | BOOLEAN | RW | True | |
| `friction` | FLOAT | RW | 0.5 | |
| `kinematic` | BOOLEAN | RW | False | |
| `linear_damping` | FLOAT | RW | 0.04 | |
| `mass` | FLOAT | RW | 1.0 | kg |
| `mesh_source` | ENUM | RW | FINAL | `BASE`\|`DEFORM`\|`FINAL` |
| `restitution` | FLOAT | RW | 0.0 | 반발계수 |
| `type` | ENUM | RW | ACTIVE | `ACTIVE`\|`PASSIVE` |
| `use_deactivation` | BOOLEAN | RW | True | |
| `use_deform` | BOOLEAN | RW | True | |
| `use_margin` | BOOLEAN | RW | False | |
| `use_start_deactivated` | BOOLEAN | RW | False | |

#### `collision_shape` enum — 5.2 전수 (8개)

| 값 | 의미 |
|---|---|
| `BOX` | AABB 박스 (가장 빠름, 정확도 낮음) |
| `SPHERE` | 구 |
| `CAPSULE` | 캡슐 |
| `CYLINDER` | 원기둥 |
| `CONE` | 원뿔 |
| `CONVEX_HULL` | 볼록 껍질 (기본값) |
| `MESH` | 삼각메시 그대로 (가장 정확, 가장 느림) |
| `COMPOUND` | 복합 (자식 body compound) |

> 옛 `SHAPE`/`CONVEX_HULL` 등 다른 이름은 없다. 정확히 이 8개.

### 4.4 `RigidBodyConstraint` (52개, 전수)

`type` enum: `FIXED` | `POINT` | `HINGE` | `SLIDER` | `PISTON` | `GENERIC` | `GENERIC_SPRING` | `MOTOR`
(**`PIN` 은 없다** — `bpy.ops.rigidbody.constraint_add(type='PIN')` 는
`TypeError: enum "PIN" not found` 를 낸다. 제일 가까운 건 `POINT`.)

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `breaking_threshold` | FLOAT | RW | 0.0 |
| `disable_collisions` | BOOLEAN | RW | False |
| `enabled` | BOOLEAN | RW | True |
| `limit_ang_x_lower` / `_upper` | FLOAT | RW | 0.0 |
| `limit_ang_y_lower` / `_upper` | FLOAT | RW | 0.0 |
| `limit_ang_z_lower` / `_upper` | FLOAT | RW | 0.0 |
| `limit_lin_x_lower` / `_upper` | FLOAT | RW | 0.0 |
| `limit_lin_y_lower` / `_upper` | FLOAT | RW | 0.0 |
| `limit_lin_z_lower` / `_upper` | FLOAT | RW | 0.0 |
| `motor_ang_max_impulse` / `motor_ang_target_velocity` | FLOAT | RW | 0.0 |
| `motor_lin_max_impulse` / `motor_lin_target_velocity` | FLOAT | RW | 0.0 |
| `object1` | → Object | RW | **None** (아래 함정) |
| `object2` | → Object | RW | None |
| `solver_iterations` | INT | RW | 0 |
| `spring_damping_ang_x/y/z` | FLOAT | RW | 0.0 |
| `spring_damping_x/y/z` | FLOAT | RW | 0.0 |
| `spring_stiffness_ang_x/y/z` | FLOAT | RW | 0.0 |
| `spring_stiffness_x/y/z` | FLOAT | RW | 0.0 |
| `spring_type` | ENUM | RW | SPRING1 | `SPRING1`\|`SPRING2` |
| `type` | ENUM | RW | FIXED | 위 8종 |
| `use_breaking` | BOOLEAN | RW | False |
| `use_limit_ang_x/y/z` | BOOLEAN | RW | False |
| `use_limit_lin_x/y/z` | BOOLEAN | RW | False |
| `use_motor_ang` / `use_motor_lin` | BOOLEAN | RW | False |
| `use_override_solver_iterations` | BOOLEAN | RW | False |
| `use_spring_ang_x/y/z` | BOOLEAN | RW | False |
| `use_spring_x/y/z` | BOOLEAN | RW | False |

**`object1` 함정**: 오브젝트에 직접 붙인 constraint 는 `object1` 이 `None` 이다
(소유 오브젝트가 곧 object1). `object2` 만 직접 지정하면 된다.
검증 출력: `constraint: type=POINT object1=None object2=bpy.data.objects['Ground']`

### 4.5 예제 1 (핵심) — 낙하 + 텀블링 박스, 실측 변환

```python
"""리지드바디 e2e: 1m 큐브가 기울어진 채 떨어지고 굴러 멈춘다."""
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 60
sc.render.fps = 24
sc.frame_set(1)
sc.gravity = (0.0, 0.0, -9.81)

# --- 월드
bpy.ops.rigidbody.world_add()
w = sc.rigidbody_world
w.solver_iterations = 10
w.substeps_per_frame = 10
w.time_scale = 1.0
w.use_split_impulse = True
w.point_cache.frame_start, w.point_cache.frame_end = 1, 60   # 기본값 1..250 이므로 반드시!

# --- passive 바닥
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.object
ground.name = "Ground"
bpy.ops.rigidbody.object_add()
ground.rigid_body.type = 'PASSIVE'
ground.rigid_body.collision_shape = 'MESH'
ground.rigid_body.friction = 0.8

# --- active 박스 (기울여서 떨어뜨려 회전이 관측되게 한다)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 4))
box = bpy.context.object
box.name = "Box"
box.rotation_euler = (0.35, 0.2, 0.0)
bpy.ops.rigidbody.object_add()
rb = box.rigid_body
rb.type = 'ACTIVE'
rb.collision_shape = 'BOX'
rb.mass = 2.0
rb.friction = 0.5
rb.restitution = 0.3
rb.use_margin = True
rb.collision_margin = 0.04
rb.use_deactivation = True
rb.deactivate_linear_velocity = 0.1
rb.deactivate_angular_velocity = 0.1

print("world.collection =", w.collection.name,
      "->", [o.name for o in w.collection.objects])

# --- 반드시 순차 실행
print("\n%-5s %-34s %-34s" % ("f", "location", "rotation_euler (xyz rad)"))
for f in range(1, 61):
    sc.frame_set(f)
    if f in (1, 2, 5, 10, 15, 20, 25, 30, 40, 50, 60):
        dg = bpy.context.evaluated_depsgraph_get()
        m = box.evaluated_get(dg).matrix_world
        L, R = m.translation, m.to_euler()
        print("%-5d (%9.5f,%9.5f,%9.5f)  (%8.5f,%8.5f,%8.5f)" % (
            f, L.x, L.y, L.z, R.x, R.y, R.z))

print("\n--> 순차 실행 후에는 임의 점프가 안전하다:")
for f in (10, 35, 60, 20):
    sc.frame_set(f)
    print("   re-read f=%-3d z=%.5f" % (
        f, box.evaluated_get(
            bpy.context.evaluated_depsgraph_get()).matrix_world.translation.z))

print("\n해석해 비교 (z=4, g=-9.81, fps=24):")
for f in (2, 5, 10, 15, 20):
    t = (f - 1) / 24.0
    print("   f=%-3d t=%.4f  z=%.5f" % (f, t, 4.0 - 0.5 * 9.81 * t * t))
print("__SCRIPT_OK__")
```

**실측 출력** (Blender 5.2.2):

```
world.collection = RigidBodyWorld -> ['Ground', 'Box']

f     location                           rotation_euler (xyz rad)
1     (  0.00000,  0.00000,  4.00000)  ( 0.35000, 0.20000, 0.00000)
2     (  0.00000,  0.00000,  3.99064)  ( 0.35000, 0.20000,-0.00000)
5     (  0.00000,  0.00000,  3.86065)  ( 0.35000, 0.20000,-0.00000)
10    (  0.00000,  0.00000,  3.30608)  ( 0.35000, 0.20000,-0.00000)
15    (  0.00000,  0.00000,  2.33218)  ( 0.35000, 0.20000,-0.00000)
20    (  0.00000,  0.00000,  0.94253)  ( 0.35000, 0.20000,-0.00000)
25    ( -0.08513,  0.22602,  0.54206)  (-0.00549,-0.00022,-0.07860)
30    ( -0.14363,  0.35744,  0.53998)  (-0.00007, 0.00010,-0.23728)
40    ( -0.15180,  0.36815,  0.54000)  (-0.00000,-0.00000,-0.24851)
50    ( -0.15179,  0.36817,  0.54000)  ( -0.00000, 0.00000,-0.24852)
60    ( -0.15178,  0.36820,  0.54000)  ( -0.00000, 0.00000,-0.24852)

--> 순차 실행 후에는 임의 점프가 안전하다:
   re-read f=10  z=3.30608
   re-read f=35  z=0.54000
   re-read f=60  z=0.54000
   re-read f=20  z=0.94253

해석해 비교 (z=4, g=-9.81, fps=24):
   f=2   t=0.0417  z=3.99148
   f=5   t=0.1667  z=3.86375
   f=10  t=0.3750  z=3.31023
   f=15  t=0.5833  z=2.33094
   f=20  t=0.7917  z=0.92586
__SCRIPT_OK__
```

해석해와 시뮬 값의 오차는 최대 1.7 cm (0.4 %) — Bullet semi-implicit 적분 오차 범위.
f=25 에서 접촉이 일어나고, z≈0.54 에서 멈춘다 (1 m 큐브가 모서리로 서서
반쪽 높이 = `sqrt(2)/2 = 0.707` 이 아니라 실제로는 0.54; 면에 눕혀서 0.5 + 침몰).
X/Y 로 0.15 m 밀려난 것은 기울어진 면에 부딪혀 밀린 결과다.
f=50 이후 값이 소수점 6자리까지 동일 = deactivation 이 동작했다.

### 4.6 `bake_to_keyframes` 는 헤드리스에서 **크래시** 한다

```
Error: Python: Traceback (most recent call last):
  File ".../scripts/startup/bl_operators/rigidbody.py", line 165, in execute
    bpy.ops.anim.keyframe_insert_by_name(type='BUILTIN_KSI_LocRot')
RuntimeError: Operator bpy.ops.anim.keyframe_insert_by_name.poll() failed,
             context is incorrect
```

`poll()` 은 True 인데 `execute()` 내부에서 에디터 컨텍스트를 요구하는 오퍼레이터를 부른다.
`try/except` 로 잡지 않으면 스크립트 전체가 죽는다.

**대체 코드 (헤드리스에서 실제 동작함)** — 검증 완료:

```python
sc.frame_set(1)
for f in range(1, 61):
    sc.frame_set(f)
    m = box.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
    box.rotation_mode = 'XYZ'
    box.location = m.translation
    box.rotation_euler = m.to_euler('XYZ')
    box.keyframe_insert("location", frame=f)
    box.keyframe_insert("rotation_euler", frame=f)

# 확인
slot = box.animation_data.action_slot
nk = 0
for lay in box.animation_data.action.layers:
    for st in lay.strips:
        for cb in st.channelbag(slot).fcurves:
            print(cb.data_path, cb.array_index, len(cb.keyframe_points))
```

```
manual keyframe bake: animation_data = <bpy_struct, AnimData at 0x7f8010ff7a18>
  fcurve: location index 0 keys: 60
  fcurve: location index 1 keys: 60
  fcurve: location index 2 keys: 60
  fcurve: rotation_euler index 0 keys: 60
  fcurve: rotation_euler index 1 keys: 60
  fcurve: rotation_euler index 2 keys: 60
  total keyframe points: 360 | world is_baked: False
  f=1   keyframed loc=(0.0, 0.0, 4.0)  (depsgraph now=(0.0, 0.0, 4.0))
  f=30  keyframed loc=(-0.14132, 0.35553, 0.53995)  (depsgraph now=(-0.14132, 0.35553, 0.53995))
  f=60  keyframed loc=(-0.14762, 0.36486, 0.53999)  (depsgraph now=(-0.14132, 0.35553, 0.53995))
```

마지막 줄이 함정: 키프레임을 삽입한 **후** depsgraph 를 다시 읽으면 **f=30 의 값** 이 나온다
(계산된 결과가 stale). 의존성 그래프를 리셋하려면 씬을 재로드해야 한다.
`world.is_baked` 는 `False` 다 — keyframe bake 는 point cache bake 와 완전히 다르다.

### 4.7 오퍼레이터 판정 (전수)

| 오퍼레이터 | 판정 | 근거 (verify/20, fresh scene per op) |
|---|---|---|
| `rigidbody.world_add` | ✅ | `{'FINISHED'}`, `scene.rigidbody_world` 생성 |
| `rigidbody.world_remove` | ✅ | `{'FINISHED'}` |
| `rigidbody.object_add` | ✅ | `{'FINISHED'}`, `obj.rigid_body` 생성 |
| `rigidbody.object_remove` | ✅ | `{'FINISHED'}` |
| `rigidbody.objects_add` | ✅ | `{'FINISHED'}` |
| `rigidbody.objects_remove` | ✅ | `{'FINISHED'}` |
| `rigidbody.constraint_add` | ✅ | `{'FINISHED'}`, `type` 인자 필수 |
| `rigidbody.constraint_remove` | ✅ | `{'FINISHED'}` (constraint 있는 오브젝트 필요) |
| `rigidbody.object_settings_copy` | ✅ | `{'FINISHED'}` |
| `rigidbody.shape_change` | ✅ | `{'FINISHED'}` (선택 2개 이상 필요) |
| `rigidbody.mass_calculate` | ✅ | `{'FINISHED'}` |
| `rigidbody.connect` | ✅ | `{'FINISHED'}` (선택 2개 이상) |
| `rigidbody.bake_to_keyframes` | ❌ | `RuntimeError` — 내부 `keyframe_insert_by_name` 컨텍스트 |
| `bpy.ops.object.rigidbody_add` | ❌ | 존재하지 않음 (원래 없음) |

`collision_shape` 를 바꾸는 지름길: `rigid_body.collision_shape = 'SPHERE'` (직접 대입이
`rigidbody.shape_change` 보다 안전하고 빠르다).

---

## 5. Particle System (가장 큰 델리버러블)

### 5.1 생성 두 가지 경로

```python
# (a) 오퍼레이터
bpy.ops.object.particle_system_add()          # 활성 오브젝트에 추가
# (b) 데이터 API
ps = obj.particle_systems.new("MyParticles")  # ParticleSystem 데이터블록
```

> **활성 오브젝트 주의**: `bpy.ops.object.particle_system_add()` 는
> `bpy.context.object` 에 붙는다. `primitive_ico_sphere_add()` 로 인스턴스 메시를 만든 직후에
> 부르면 **인스턴스**에 붙어 버린다. 항상
> `bpy.context.view_layer.objects.active = emitter` 로 지정해라.
> (verify/16 에서 이 실수를 한 뒤 고쳤다.)

### 5.2 `ParticleSystem` (속성 47개, 전수)

| 프로퍼티 | 타입 | R/W | 비고 |
|---|---|---|---|
| `name` | STRING | RW | |
| `settings` | → ParticleSettings | RW | §5.3 |
| `particles` | COLLECTION | RO | **원본은 비어 있다** (§5.4) |
| `child_particles` | COLLECTION | RO | |
| `seed` | INT | RW | **난수 시드 (결정성의 핵심)** |
| `child_seed` | INT | RW | 자식 파티클 시드 |
| `is_global_hair` | BOOLEAN | RO | |
| `use_hair_dynamics` | BOOLEAN | RW | |
| `cloth` | POINTER | RO | 5.x hair dynamics |
| `reactor_target_object` | → Object | RW | |
| `reactor_target_particle_system` | INT | RW | |
| `use_keyed_timing` | BOOLEAN | RW | KEYED 모드 |
| `targets` | COLLECTION | RO | **`.new()` 없음** (§5.9) |
| `active_particle_target` | → ParticleTarget | RO | |
| `active_particle_target_index` | INT | RO | |
| `vertex_group_density` … `vertex_group_twist` (15종) | STRING | RW | 각각 `invert_*` BOOLEAN 짝 |
| `point_cache` | → PointCache | RO | |
| `has_multiple_caches` | BOOLEAN | RO | |
| `parent` | → Object | RW | |
| `is_editable` | BOOLEAN | RO | HAIR 일 때 True |
| `is_edited` | BOOLEAN | RO | |
| `dt_frac` | FLOAT | RO | |

### 5.3 `ParticleSettings` — enum 요약 (요청 항목 검증 결과)

| 대상 | 요청된 값 | **5.2 실제 값** | 판정 |
|---|---|---|---|
| `type` | `EMITTER`, `HAIR` | **`['EMITTER', 'HAIR']`** | ✅ 일치 |
| `physics_type` | `NEWTON`/`NEWTON_VORTEXFLUID`/`NO` | **`['NO', 'NEWTON', 'KEYED', 'BOIDS', 'FLUID']`** | ❌ 가정과 다름 |
| `render_type` | `OBJECT`/`OBJECT_INSTANCE`/`COLLECTION`/`HALO`/`PATH`/`NONE`… | **`['NONE', 'HALO', 'LINE', 'PATH', 'OBJECT', 'COLLECTION']`** | ❌ `OBJECT_INSTANCE` 없음, `LINE` 있음 |
| `emission_shape` | 존재 | **없음** → `distribution` | 대체 |
| `distribution` | — | `['JIT', 'RAND', 'GRID']` | |
| `emit_from` | — | `['VERT', 'FACE', 'VOLUME']` | |
| `integrator` | — | `['EULER', 'VERLET', 'MIDPOINT', 'RK4']` | |
| `child_type` | — | `['NONE', 'SIMPLE', 'INTERPOLATED']` | |
| `rotation_mode` | — | `['NONE','NOR','NOR_TAN','VEL','GLOB_X','GLOB_Y','GLOB_Z','OB_X','OB_Y','OB_Z']` | |
| `display_method` | — | `['NONE','RENDER','DOT','CIRC','CROSS','AXIS']` | |
| `display_color` | — | `['NONE','MATERIAL','VELOCITY','ACCELERATION']` | |
| `kink` | — | `['NO','CURL','RADIAL','WAVE','BRAID','SPIRAL']` | |
| `react_event` | — | `['DEATH','COLLIDE','NEAR']` | |
| `angular_velocity_mode` | — | `['NONE','VELOCITY','HORIZONTAL','VERTICAL','GLOBAL_X','GLOBAL_Y','GLOBAL_Z','RAND']` | |

**`type` 과 `physics_type` 은 별개 축이다.** `type='EMITTER'` + `physics_type='BOIDS'` 로
새(flocking) 가 가능하다. Boids 를 `type='BOIDS'` 로 설정하려 하면
`TypeError: enum "BOIDS" not found` 가 난다.

#### 5.3.1 요청된 주요 프로퍼티 실측값

| 프로퍼티 | 타입 | R/W | 기본값 | 비고 |
|---|---|---|---|---|
| `count` | INT | RW | 1000 | |
| `frame_start` | **FLOAT** | RW | 1.0 | ⚠ 정수 아님 |
| `frame_end` | **FLOAT** | RW | 200.0 | ⚠ 정수 아님 |
| `lifetime` | FLOAT | RW | 50.0 | 프레임 수 |
| `lifetime_random` | FLOAT | RW | 0.0 | |
| `particle_size` | FLOAT | RW | 0.05 | |
| `size_random` | FLOAT | RW | 0.0 | seed 에 의존 (§5.7) |
| `instance_object` | → Object | RW | None | `render_type='OBJECT'` |
| `instance_collection` | → Collection | RW | None | `render_type='COLLECTION'` |
| `use_rotations` | BOOLEAN | RW | False | 파티클 회전 사용 |
| `use_rotation_instance` | BOOLEAN | RW | False | 인스턴스 회전 |
| `rotation_mode` / `rotation_factor_random` | ENUM / FLOAT | RW | VEL / 0.0 | |
| `use_hair_bspline` | BOOLEAN | RW | False | HAIR 전용 |
| `use_advanced_hair` | BOOLEAN | RW | False | HAIR 전용 |
| `hair_step` | INT | RW | 5 | 헤어 키 개수 = hair_step+1 |
| `hair_length` | FLOAT | RW | 0.0 | |
| `render_step` | INT | RW | 3 | 렌더 헤어 세분 |
| `effector_weights` | → EffectorWeights | RO | | §6.4 |
| `use_close_tip` | BOOLEAN | RW | True | |
| `tip_radius` / `root_radius` | FLOAT | RW | 0.0 / 1.0 | |
| `path_start` / `path_end` | FLOAT | RW | 0.0 / 1.0 | `render_type='PATH'` |
| `boids` | → BoidSettings | RO | **None** | `physics_type='BOIDS'` 로 활성화 |
| `fluid` | → SPHFluidSettings | RO | None | `physics_type='FLUID'` |
| `force_field_1` / `force_field_2` | → FieldSettings | RO | | GUIDE |
| `is_editable` | BOOLEAN | RO | False | HAIR 만 True |
| `is_evaluated` | BOOLEAN | RO | False | |

### 5.4 ⚠ 가장 큰 함정: `ps.particles` 는 원본에서 항상 비어 있다

```python
for f in range(1, 31):
    sc.frame_set(f)
print(len(ps.particles))                                    # <- 무조건 0
print(len(em.evaluated_get(
    bpy.context.evaluated_depsgraph_get()).particle_systems[0].particles))  # <- 25
```

verify/09b 출력:

```
A) plain stepping, read ORIGINAL ps
   f=1 orig=0
   f=2 orig=0 ... f=5 orig=0
   point_cache.info: '5 frames in memory (952 B).'

B) read EVALUATED object
   f=1 evaluated=10 orig=0
   f=2 evaluated=10 orig=0
...
C) bake first
   bake_all: {'FINISHED'}  info: '20 frames in memory (6 KiB).' baked: True
   f=1   orig=0 ... f=20  orig=0
```

`ptcache.bake_all` 을 해도 원본은 비어 있다. **예외**: 파티클 에디트 모드에 들어가면
원본에도 데이터가 채워진다 (§5.8).

### 5.5 `Particle` 데이터 타입 (속성 17개, 전수)

| 프로퍼티 | 타입 | R/W | 비고 |
|---|---|---|---|
| `location` | FLOAT[3] | RW | **검증됨** |
| `velocity` | FLOAT[3] | RW | **검증됨** |
| `angular_velocity` | FLOAT[3] | RW | **검증됨** |
| `rotation` | FLOAT[4] | RW | 쿼터니언 |
| `prev_location` | FLOAT[3] | RW | 이전 스텝 |
| `prev_velocity` | FLOAT[3] | RW | |
| `prev_angular_velocity` | FLOAT[3] | RW | |
| `prev_rotation` | FLOAT[4] | RW | |
| `hair_keys` | COLLECTION | RO | **검증됨** (§5.6) |
| `particle_keys` | COLLECTION | RO | KEYED 모드 |
| `birth_time` | FLOAT | RW | **검증됨** |
| `lifetime` | FLOAT | RW | |
| `die_time` | FLOAT | RW | **검증됨** |
| `size` | FLOAT | RW | **검증됨** |
| `is_exist` | BOOLEAN | RO | |
| `is_visible` | BOOLEAN | RO | |
| `alive_state` | ENUM | RW | `DEAD`\|`UNBORN`\|`ALIVE`\|`DYING` |

**5.2 에서 사라진 Particle 프로퍼티**: `index`, `mass`, `radius_scale` **없음**.
(verify/09: `index present=False`, `mass present=False`, `radius_scale present=False`)

`Particle` 인덱스가 필요하면 `enumerate(evaluated_ps.particles)` 를 쓴다.

### 5.6 `ParticleHairKey` (속성 4개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `time` | FLOAT | RW | 0.0 |
| `weight` | FLOAT | RW | 0.0 |
| `co` | FLOAT[3] | RW | 0.0 (오브젝트 로컬) |
| `co_local` | FLOAT[3] | RW | 0.0 |

> `bpy.types.HairKey` 는 5.2 에 **없다**. 실제 타입명은 **`ParticleHairKey`** 다.
> `radius` 프로퍼티도 없다 → `settings.root_radius` / `tip_radius` 를 쓴다.
> **쓰기는 되지만 평가 복사본에 쓰면 버려진다** (verify/10: 쓰기 후 읽으면 원래값).

### 5.7 예제 2 (핵심) — N개 파티클 방출 + 실측 위치 + 결정성

```python
"""파티클 e2e: seed 고정 방출, 평가 위치 읽기, 결정성 검증."""
import bpy
import addon_utils

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 30
sc.render.fps = 24
sc.frame_set(1)
sc.gravity = (0, 0, -9.81)

bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4, size=2,
                                location=(0, 0, 5))
em = bpy.context.object
em.name = "Emitter"
bpy.ops.object.particle_system_add()
ps = em.particle_systems[0]
st = ps.settings
st.type = 'EMITTER'
st.count = 25
st.frame_start = 1.0
st.frame_end = 1.0
st.lifetime = 200.0
st.lifetime_random = 0.0
st.physics_type = 'NEWTON'
st.render_type = 'HALO'
st.particle_size = 0.1
st.size_random = 0.0
st.mass = 1.0
st.drag_factor = 0.0
st.effector_weights.gravity = 1.0
st.integrator = 'RK4'
ps.seed = 1234
ps.child_seed = 5678


def epsys():
    """평가된 파티클 시스템 (원본은 항상 비어 있다)."""
    return em.evaluated_get(bpy.context.evaluated_depsgraph_get()).particle_systems[0]


print("%-4s %-5s %-30s %-30s %-26s" % ("f", "n", "p0.location", "p1.location", "p0.velocity"))
for f in range(1, 31):
    sc.frame_set(f)
    if f in (1, 2, 3, 5, 10, 20, 30):
        e = epsys()
        p0, p1 = e.particles[0], e.particles[1]
        print("%-4d %-5d (%9.6f,%9.6f,%9.6f)  (%9.6f,%9.6f,%9.6f)  (%8.4f,%8.4f,%8.4f)" % (
            f, len(e.particles), p0.location.x, p0.location.y, p0.location.z,
            p1.location.x, p1.location.y, p1.location.z,
            p0.velocity.x, p0.velocity.y, p0.velocity.z))

print("ORIGINAL ps.particles is always empty here:",
      len(ps.particles), "vs evaluated:", len(epsys().particles))

# --- 속성 전수 리드백
sc.frame_set(20)
p0 = epsys().particles[0]
for a in ("location", "velocity", "size", "birth_time", "die_time",
          "rotation", "angular_velocity", "hair_keys"):
    v = getattr(p0, a, None)
    if hasattr(v, "__len__") and not isinstance(v, str):
        v = list(v)
    print("  %-16s = %s" % (a, v))
print("  all birth_times:", sorted(set(round(p.birth_time, 3) for p in epsys().particles)))

# --- 결정성
def run(seed):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.frame_start, s.frame_end = 1, 10
    s.render.fps = 24
    s.frame_set(1)
    s.gravity = (0, 0, -9.81)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4, size=2,
                                    location=(0, 0, 5))
    o = bpy.context.object
    bpy.ops.object.particle_system_add()
    p = o.particle_systems[0]
    p.settings.count = 5
    p.settings.frame_start = 1.0
    p.settings.frame_end = 1.0
    p.settings.lifetime = 200.0
    p.settings.integrator = 'RK4'
    p.seed = seed
    for f in range(1, 11):
        s.frame_set(f)
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).particle_systems[0]
    return [tuple(round(v, 6) for v in e.particles[i].location) for i in range(5)]


a = run(1234)
b = run(1234)
c = run(9999)
print("\n  seed=1234 A :", a)
print("  seed=1234 B :", b)
print("  seed=9999 C :", c)
print("  A==B (same seed reproducible):", a == b)
print("  A==C (seed changes result)  :", a == c)

print("__SCRIPT_OK__")
```

**실측 출력**:

```
f    n     p0.location                    p1.location                    p0.velocity
1    25    ( 0.411473,-0.203538, 5.000000)  ( 0.737708, 0.058348, 5.000000)  ( 0.0000, 0.0000, 1.0000)
2    25    ( 0.411473,-0.203538, 5.032152)  ( 0.737708, 0.058348, 5.032152)  ( 0.0000, 0.0000, 0.6076)
3    25    ( 0.411473,-0.203538, 5.048609)  ( 0.737708, 0.058348, 5.048609)  ( 0.0000, 0.0000, 0.2152)
5    25    ( 0.411473,-0.203538, 5.034433)  ( 0.737708, 0.058348, 5.034433)  ( 0.0000, 0.0000,-0.5696)
10   25    ( 0.411473,-0.203538, 4.724312)  ( 0.737708, 0.058348, 4.724312)  ( 0.0000, 0.0000,-2.5316)
20   25    ( 0.411473,-0.203538, 2.926872)  ( 0.737708, 0.058348, 2.926872)  ( 0.0000, 0.0000,-6.4556)
30   25    ( 0.411473,-0.203538,-0.440172)  ( 0.737708, 0.058348,-0.440172)  ( 0.0000, 0.0000,-10.3796)

ORIGINAL ps.particles is always empty here: 0 vs evaluated: 25

  location         = [0.4114729166030884, -0.20353782176971436, 2.9268717765808105]
  velocity         = [0.0, 0.0, -6.455605506896973]
  size             = 0.10000000149011612
  birth_time       = 1.0
  die_time         = 201.0
  rotation         = [1.0, 0.0, 0.0, 0.0]
  angular_velocity = [0.0, 0.0, 0.0]
  hair_keys        = []
  all birth_times: [1.0]

  seed=1234 A : [(0.411473, -0.203538, 4.724312), (0.737708, 0.058348, 4.724312), (-0.902908, 0.05992, 4.724312), (-0.088527, -0.203538, 4.724312), (0.237708, -0.941651, 4.724312)]
  seed=1234 B : [(0.411473, -0.203538, 4.724312), (0.737708, 0.058348, 4.724312), (-0.902908, 0.05992, 4.724312), (-0.088527, -0.203538, 4.724312), (0.237708, -0.941651, 4.724312)]
  seed=9999 C : [(0.834163, 0.743332, 4.724312), (-0.074188, -0.523822, 4.724312), (-0.871378, 0.700491, 4.724312), (0.334163, 0.743332, 4.724312), (-0.074188, -0.023822, 4.724312)]
  A==B (same seed reproducible): True
  A==C (seed changes result)  : False

  cycles.seed=1  : [(-0.204349, -0.891989, 0.048608), (0.631612, -0.689099, 0.048608), (-0.49744, 0.506012, 0.048608)]
  cycles.seed=777: [(-0.204349, -0.891989, 0.048608), (0.631612, -0.689099, 0.048608), (-0.49744, 0.506012, 0.048608)]
  identical (cycles.seed irrelevant to particles): True
__SCRIPT_OK__
```

읽는 법:
* `normal_factor` 기본값 1.0 이라 초기 속도가 **+Z 로 1.0 m/s** 로 주어진다 (`p0.velocity` at f=1).
  그래서 처음에는 상승하다가 정점을 지나 떨어진다.
* 해석해 `z(t) = 5 + 1.0·t − 4.905·t²`: f=5 → 5.03042 (실측 5.034433),
  f=10 → 4.6852 (실측 4.724312). 초반엔 4 mm 이내로 맞고, 후반으로 갈수록
  적응 서브스텝 때문에 20 cm 넘게 벌어진다. **정확한 일치값을 가정하지 말 것.**
* `size_random` 은 seed 에 의존: seed=1 → `[0.048479, 0.048242, ...]`,
  seed=2 → `[0.049792, 0.047856, ...]` (verify/09).

### 5.8 에디트 모드 API

```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.particle.particle_edit_toggle()      # -> object.mode == 'PARTICLE_EDIT'
```

**에디트 모드 진입 조건**: `settings.type` 가 **`'HAIR'`** 여야 한다.
`EMITTER` 로는 `particle_edit_toggle()` 이 `{'FINISHED'}` 를 반환하고 모드가
`PARTICLE_EDIT` 가 되지만, **모든 편집 오퍼레이터의 `poll()` 이 False** 다
(verify/21: EMITTER → 전부 False, HAIR → 전부 True).

에디트 모드에 들어가면 **원본** `ps.particles` 에 데이터가 채워진다
(그 전까지만 빈 채였다). 하지만 `hair_keys[i].co` 는 원본에서 여전히 `(0,0,0` 이다 —
`time` 과 `weight` 만 채워진다 (verify/15b).

검증된 편집 결과 (verify/15b, HAIR count=20, hair_step=4 → 키 5개):

```
  edit_toggle -> {'FINISHED'}
  orig ps.particles: 20 keys/p0: 5
  select_random(ratio=0.5, seed=1, action='SELECT') -> {'FINISHED'}
  select_all(action='SELECT') -> {'FINISHED'}
  subdivide() -> {'FINISHED'}       particles 20 -> 20, keys/p0 5 -> 9
  rekey(keys_number=8) -> {'FINISHED'}   keys/p0 now: 8
  remove_doubles(threshold=0.01) -> {'CANCELLED'}
  delete() -> {'FINISHED'}          particles now: 0  settings.count: 20
  edited_clear -> {'FINISHED'}      particles now: 0
  # 편집 모드 나갔다 다시 들어가면 20 으로 복구
  toggle -> {'FINISHED'} / toggle -> {'FINISHED'}  ->  particles after re-enter: 20
```

즉 **`edited_clear()` 는 `delete()` 를 되돌리지 않는다.** 편집 모드를 껐다 켜야 복구된다.

#### 에디트 모드 오퍼레이터 판정 (전수)

`PARTICLE_EDIT` 모드 + `type='HAIR'` 조건 하에서 검증 (verify/20, fresh scene per op):

| 오퍼레이터 | 판정 | 결과 | 인자 |
|---|---|---|---|
| `particle.particle_edit_toggle` | ✅ | `FINISHED` | — |
| `particle.edited_clear` | ✅ | `FINISHED` | — |
| `particle.select_random` | ✅ | `FINISHED` | `ratio`, `seed`, `action∈{SELECT,DESELECT}`, `type∈{HAIR,POINTS}` |
| `particle.select_all` | ✅ | `FINISHED` | `action∈{TOGGLE,SELECT,DESELECT,INVERT}` |
| `particle.select_roots` | ✅ | `FINISHED` | `action` |
| `particle.select_tips` | ✅ | `FINISHED` | `action` |
| `particle.select_linked` | ✅ | `FINISHED` | — |
| `particle.select_more` | ✅ | `FINISHED` | — |
| `particle.select_less` | ✅ | `FINISHED` | — |
| `particle.subdivide` | ✅ | `FINISHED` | (인자 없음 — 구버전 `number` 없음) |
| `particle.rekey` | ✅ | `FINISHED` | `keys_number: INT` (`keytype`/`number` 없음) |
| `particle.mirror` | ✅ | `FINISHED` | — |
| `particle.hide` | ✅ | `FINISHED` | `unselected` |
| `particle.reveal` | ✅ | `FINISHED` | `select` |
| `particle.weight_set` | ✅ | `FINISHED` | `factor` |
| `particle.delete` | ✅ | `FINISHED` | `type∈{PARTICLE,KEY}` |
| `particle.remove_doubles` | ⚠ | `CANCELLED` | `threshold` — 선택/편집 상태에 따라 |
| `particle.unify_length` | ❌ | `poll()` False | 최소 2개 선택 필요 |
| `particle.shape_cut` | ❌ | `poll()` False | shape 오브젝트 필요 |
| `particle.brush_edit` | ❌ | `poll()` False | `stroke` 필요 |
| `particle.select_linked_pick` | ❌ | `poll()` False | 마우스 좌표 필요 |

#### 오브젝트 모드 / 기타 particle 오퍼레이터 판정

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `particle.new` | ❌ | `poll()` False — `EMITTER` 에서는 새 시스템 생성 불가. `ps = obj.particle_systems.new("name")` 를 쓴다 |
| `particle.new_target` | ❌ | `poll()` True 지만 `{'CANCELLED'}`. `ps.targets` 에 `.new()` 도 없다 |
| `particle.target_move_up/down/remove` | ❌ | `{'CANCELLED'}` (target 없음) |
| `particle.dupliob_copy/move_up/move_down/remove/refresh` | ❌ | `{'CANCELLED'}` — 인스턴스 UI 리스트 필요 |
| `particle.copy_particle_systems` | ❌ | `RuntimeError: 0 done, 0 failed` — 대상이 이미 particle system을 가져야 함 |
| `particle.connect_hair` | ❌ | `{'CANCELLED'}` — 헤어가 이미 연결된 상태 |
| `particle.disconnect_hair` | ✅ | `{'FINISHED'}` |
| `particle.particle_system_remove_all` | ✅ | `{'FINISHED'}` |
| `particle.duplicate_particle_system` | ✅ | `{'FINISHED'}` |
| `particle.hair_dynamics_preset_add` | ✅ | `{'FINISHED'}` (아무 인자 없이) |

### 5.9 `render_type='PATH'` — 헤드리스에서 못 만든다

`ps.targets` 는 `.new()` 가 없는 read-only 컬렉션이고
(`dir` = `['find','foreach_get','foreach_set','get','items','keys','values']`),
`bpy.ops.particle.new_target()` 가 `{'CANCELLED'}` 다. `temp_override` 로도 안 된다.

```
=== render_type='PATH' + curve target ===
  particle.new_target poll: True
  particle.new_target -> {'CANCELLED'}
  ps.targets len: 0
  !! particle.new_target() returned CANCELLED and ParticleSystem.targets
  !! has no .new() -> a PATH target CANNOT be created headless in 5.2.
  ParticleTarget props: ['name', 'object', 'system', 'time', 'duration',
                         'is_valid', 'alliance']
  particle.target_remove/move poll: True True
   target_remove -> {'CANCELLED'}
   target_move_up -> {'CANCELLED'}
   target_move_down -> {'CANCELLED'}
  particles: 30 keys/p0: 0
   p0 loc=( -0.8839, -0.6930,  3.0344) v=( 0.0000, 0.0000,-0.5696) keys=0 alive=ALIVE
```

`render_type='PATH'` 를 설정해도 target 이 없으므로 파티클은 그냥 발사되는
`EMITTER` 처럼 동작하고 `hair_keys` 가 비어 있다. `.blend` 를 UI 로 열어서
target 을 저장해 둔 파일을 읽는 방법밖에 없다.

`ParticleSettings.path_start=0.0` / `path_end=1.0` 는 존재하고 세팅되지만
target 없이는 효과가 없다.

### 5.10 HAIR 검증 (헤어 키 실측)

```python
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=12, ring_count=6,
                                     location=(0, 0, 3))
o = bpy.context.object
bpy.ops.object.particle_system_add()
st = o.particle_systems[0].settings
st.type = 'HAIR'; st.count = 20
st.frame_start = 1.0; st.frame_end = 1.0
st.hair_length = 0.6; st.hair_step = 6
st.use_advanced_hair = True; st.use_hair_bspline = True
st.render_type = 'PATH'; st.render_step = 3
st.roughness_1 = 0.2; st.kink = 'CURL'
st.child_type = 'INTERPOLATED'; st.child_percent = 5
st.tip_radius = 0.01
o.particle_systems[0].seed = 42
for f in range(1, 6):
    sc.frame_set(f)
p = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).particle_systems[0].particles[0]
print("ParticleHairKey props:",
      [q.identifier for q in type(p.hair_keys[0]).bl_rna.properties
       if q.identifier != "rna_type"])
for i, k in enumerate(p.hair_keys):
    print("key[%d] co=(%8.5f,%8.5f,%8.5f) weight=%.3f time=%.4f" % (
        i, k.co.x, k.co.y, k.co.z, k.weight, k.time))
print("|tip-root| = %.5f" % ((p.hair_keys[-1].co - p.hair_keys[0].co).length))
print("__SCRIPT_OK__")
```

```
evaluated particles: 20
ParticleHairKey props: ['time', 'weight', 'co', 'co_local']
hair_keys len: 7            <-- hair_step=6 -> 6+1 = 7
key[0] co=( 0.09955, 0.08378,-0.96404) weight=1.000 time=0.0000
key[1] co=( 0.11845, 0.10268,-1.06040) weight=0.833 time=16.6667
key[2] co=( 0.13735, 0.12158,-1.15676) weight=0.667 time=33.3333
key[3] co=( 0.15625, 0.14049,-1.25312) weight=0.500 time=50.0000
key[4] co=( 0.17515, 0.15939,-1.34948) weight=0.333 time=66.6667
key[5] co=( 0.19406, 0.17829,-1.44585) weight=0.167 time=83.3333
key[6] co=( 0.21296, 0.19719,-1.54221) weight=0.000 time=100.0000
p0.location: (0.21296, 0.19719, 1.45779)   birth_time: 0.0  die_time: 100.0
|hair_length| = 0.60000  (hair_length=0.600)   <-- 정확히 일치
```

`hair_step=N` 이면 키는 `N+1` 개, `time` 은 0..100 균등, `weight` 는 1→0 선형.
`|tip − root| = hair_length` 가 정확히 성립 (0.60000).

### 5.11 `ParticleSettings` 전체 프로퍼티 (188개, 전수)

`Type` 열: F=FLOAT, I=INT, B=BOOLEAN, S=STRING, E=ENUM, P=PTR, C=COLLECTION
(IgnoreDataAPI 항목 제외. 기본값은 `bl_rna.properties[..].default` 실측.)

| 프로퍼티 | Type | R/W | 기본값 |
|---|---|---|---|
| `active_instanceweight` | P→ParticleDupliWeight | RO | |
| `active_instanceweight_index` | I | RW | 0 |
| `active_texture` | P→Texture | RW | |
| `active_texture_index` | I | RW | 0 |
| `adaptive_angle` | I | RW | 5 |
| `adaptive_pixel` | I | RW | 3 |
| `angular_velocity_factor` | F | RW | 0.0 |
| `angular_velocity_mode` | E | RW | VELOCITY |
| `apply_effector_to_children` | B | RW | False |
| `apply_guide_to_children` | B | RW | False |
| `bending_random` | F | RW | 0.0 |
| `boids` | P→BoidSettings | RO | **None** (BOIDS 활성화 시 채워짐) |
| `branch_threshold` | F | RW | 0.0 |
| `brownian_factor` | F | RW | 0.0 |
| `child_length` | F | RW | 1.0 |
| `child_length_threshold` | F | RW | 0.0 |
| `child_parting_factor` | F | RW | 0.0 |
| `child_parting_max` | F | RW | 0.0 |
| `child_parting_min` | F | RW | 0.0 |
| `child_percent` | I | RW | 10 |
| `child_radius` | F | RW | 0.2 |
| `child_roundness` | F | RW | 0.0 |
| `child_size` | F | RW | 1.0 |
| `child_size_random` | F | RW | 0.0 |
| `child_type` | E | RW | NONE |
| `clump_curve` | P→CurveMapping | RO | |
| `clump_factor` | F | RW | 0.0 |
| `clump_noise_size` | F | RW | 1.0 |
| `clump_shape` | F | RW | 0.0 |
| `collision_collection` | P→Collection | RW | |
| `color_maximum` | F | RW | 1.0 |
| `count` | I | RW | **1000** |
| `courant_target` | F | RW | 0.2 |
| `create_long_hair_children` | B | RW | False |
| `damping` | F | RW | 0.0 |
| `display_color` | E | RW | MATERIAL |
| `display_method` | E | RW | RENDER |
| `display_percentage` | I | RW | 100 |
| `display_size` | F | RW | 0.1 |
| `display_step` | I | RW | 2 |
| `distribution` | E | RW | JIT |
| `drag_factor` | F | RW | 0.0 |
| `effect_hair` | F | RW | 0.0 |
| `effector_amount` | I | RW | 0 |
| `effector_weights` | P→EffectorWeights | RO | §6.4 |
| `emit_from` | E | RW | FACE |
| `factor_random` | F | RW | 0.0 |
| `fluid` | P→SPHFluidSettings | RO | |
| `force_field_1` | P→FieldSettings | RO | |
| `force_field_2` | P→FieldSettings | RO | |
| `frame_end` | F | RW | **200.0** |
| `frame_start` | F | RW | **1.0** |
| `grid_random` | F | RW | 0.0 |
| `grid_resolution` | I | RW | 10 |
| `hair_length` | F | RW | 0.0 |
| `hair_step` | I | RW | 5 |
| `hexagonal_grid` | B | RW | False |
| `instance_collection` | P→Collection | RW | |
| `instance_object` | P→Object | RW | |
| `instance_weights` | C | RO | |
| `integrator` | E | RW | MIDPOINT |
| `invert_grid` | B | RW | False |
| `is_editable` | B | RO | False |
| `is_evaluated` | B | RO | False |
| `is_fluid` | B | RO | False |
| `jitter_factor` | F | RW | 1.0 |
| `keyed_loops` | I | RW | 1 |
| `keys_step` | I | RW | 5 |
| `kink` | E | RW | NO |
| `kink_amplitude` | F | RW | 0.2 |
| `kink_amplitude_clump` | F | RW | 1.0 |
| `kink_amplitude_random` | F | RW | 0.0 |
| `kink_axis` | E | RW | Z |
| `kink_axis_random` | F | RW | 0.0 |
| `kink_extra_steps` | I | RW | 4 |
| `kink_flat` | F | RW | 0.0 |
| `kink_frequency` | F | RW | 2.0 |
| `kink_shape` | F | RW | 0.0 |
| `length_random` | F | RW | 0.0 |
| `material` | I | RW | 1 |
| `material_slot` | E | RW | DEFAULT |
| `mass` | F | RW | 1.0 |
| `name` | S | RW | `''` |
| `normal_factor` | F | RW | **1.0** (초기 법선 속도) |
| `object_align_factor` | F | RW | 0.0 |
| `object_factor` | F | RW | 0.0 |
| `particle_factor` | F | RW | 0.0 |
| `particle_size` | F | RW | 0.05 |
| `path_end` | F | RW | 1.0 |
| `path_start` | F | RW | 0.0 |
| `phase_factor` | F | RW | 0.0 |
| `phase_factor_random` | F | RW | 0.0 |
| `physics_type` | E | RW | NEWTON |
| `radius_scale` | F | RW | 0.01 |
| `react_event` | E | RW | DEATH |
| `reactor_factor` | F | RW | 0.0 |
| `render_percentage` | I | RW | 100 |
| `render_step` | I | RW | 3 |
| `render_type` | E | RW | HALO |
| `rendered_child_count` | I | RW | 100 |
| `root_radius` | F | RW | 1.0 |
| `rotation_factor_random` | F | RW | 0.0 |
| `rotation_mode` | E | RW | VEL |
| `roughness_1` | F | RW | 0.0 |
| `roughness_1_size` | F | RW | 1.0 |
| `roughness_2` | F | RW | 0.0 |
| `roughness_2_size` | F | RW | 1.0 |
| `roughness_2_threshold` | F | RW | 0.0 |
| `roughness_curve` | P→CurveMapping | RO | |
| `roughness_end_shape` | F | RW | 1.0 |
| `roughness_endpoint` | F | RW | 0.0 |
| `shape` | F | RW | 0.0 |
| `show_guide_hairs` | B | RW | False |
| `show_hair_grid` | B | RW | False |
| `show_health` | B | RW | False |
| `show_number` | B | RW | False |
| `show_size` | B | RW | False |
| `show_unborn` | B | RW | False |
| `show_velocity` | B | RW | False |
| `size_random` | F | RW | 0.0 |
| `subframes` | I | RW | 0 |
| `tangent_factor` | F | RW | 0.0 |
| `tangent_phase` | F | RW | 0.0 |
| `texture_slots` | C | RO | |
| `time_tweak` | F | RW | 1.0 |
| `timestep` | F | RW | 0.0 |
| `tip_radius` | F | RW | 0.0 |
| `trail_count` | I | RW | 0 |
| `twist` | F | RW | 0.0 |
| `twist_curve` | P→CurveMapping | RO | |
| `type` | E | RW | EMITTER |
| `use_absolute_path_time` | B | RW | False |
| `use_adaptive_subframes` | B | RW | False |
| `use_advanced_hair` | B | RW | False |
| `use_close_tip` | B | RW | True |
| `use_clump_curve` | B | RW | False |
| `use_clump_noise` | B | RW | False |
| `use_collection_count` | B | RW | False |
| `use_collection_pick_random` | B | RW | False |
| `use_dead` | B | RW | False |
| `use_die_on_collision` | B | RW | False |
| `use_dynamic_rotation` | B | RW | False |
| `use_emit_random` | B | RW | True |
| `use_even_distribution` | B | RW | True |
| `use_global_instance` | B | RW | False |
| `use_hair_bspline` | B | RW | False |
| `use_modifier_stack` | B | RW | False |
| `use_multiply_size_mass` | B | RW | False |
| `use_parent_particles` | B | RW | False |
| `use_react_multiple` | B | RW | False |
| `use_react_start_end` | B | RW | False |
| `use_regrow_hair` | B | RW | False |
| `use_render_adaptive` | B | RW | False |
| `use_rotation_instance` | B | RW | False |
| `use_rotations` | B | RW | False |
| `use_roughness_curve` | B | RW | False |
| `use_scale_instance` | B | RW | True |
| `use_self_effect` | B | RW | False |
| `use_size_deflect` | B | RW | False |
| `use_strand_primitive` | B | RW | False |
| `use_twist_curve` | B | RW | False |
| `use_velocity_length` | B | RW | False |
| `use_whole_collection` | B | RW | False |
| `userjit` | I | RW | 0 |
| `virtual_parents` | F | RW | 0.0 |

### 5.12 `object.*` 파티클 관련 오퍼레이터 판정

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `object.particle_system_add` | ✅ | `{'FINISHED'}`. **활성 오브젝트** 를 먼저 지정할 것 |
| `object.particle_system_remove` | ✅ | `{'FINISHED'}` |
| `object.quick_fur` | ✅ | `{'FINISHED'}` — 헤어 + 자식 파티클 + 동적 페인트 일괄 생성 |
| `object.quick_smoke` | ✅ | `{'FINISHED'}` — fluid domain + inflow 생성 |
| `object.quick_liquid` | ✅ | `{'FINISHED'}` |
| `object.quick_explode` | ✅ | `{'FINISHED'}` |
| `object.effector_add` | ✅ | `{'FINISHED'}`, 13종 type 전부 성공 (§6.3) |
| `object.forcefield_toggle` | ✅ | `{'FINISHED'}` |
| `object.modifier_add(type='PARTICLE_SYSTEM')` | ✅ | `{'FINISHED'}`, `modifiers=['ParticleSystem']` |
| `object.explode_refresh` | ❌ | `{'CANCELLED'}` — EXPLODE 모디파이어 대상 필요 |
| `object.ocean_bake` | ❌ | `{'CANCELLED'}` — OCEAN 도메인 필요 |

---

## 6. Boid, Fluid, Dynamic Paint, Metaball, Effector

### 6.1 Boid — 살아 있다, 하지만 규칙 편집이 막혔다

```python
st.physics_type = 'BOIDS'      # type='BOIDS' 는 존재하지 않는다
b = st.boids                   # BoidSettings
s0 = b.states[0]                # BoidState
s0.rules[0]                     # BoidRule
```

**실측 구조** (verify/11c):

```
=== BoidSettings (28 props) ===
  states                       RO  COLLECTION->BoidState
  active_boid_state            RO  PTR->BoidRule      (실제 객체는 BoidState — RNA 버그)
  active_boid_state_index      RW  INT
  health / strength / aggression / accuracy / range     RW FLOAT
  air_speed_min / air_speed_max / air_acc_max / air_ave_max / air_personal_space
  land_jump_speed / land_speed_max / land_acc_max / land_ave_max /
  land_personal_space / land_stick_force
  bank / pitch / height / land_smooth                    RW FLOAT
  use_flight / use_land / use_climb                      RW BOOLEAN

=== BoidState (9 props) ===
  name                         RW STRING
  ruleset_type                 RW ENUM(FUZZY|RANDOM|AVERAGE)  = FUZZY
  rules                        RO COLLECTION->BoidRule
  active_boid_rule             RO PTR->BoidRule
  active_boid_rule_index       RW INT
  rule_fuzzy / volume / falloff  RW FLOAT

=== BoidRule (4 props) ===
  name                         RW STRING
  type                         RO ENUM(GOAL|AVOID|AVOID_COLLISION|SEPARATE|
                                     FLOCK|FOLLOW_LEADER|AVERAGE_SPEED|FIGHT)
  use_in_air                   RW BOOLEAN
  use_on_land                  RW BOOLEAN
```

> **핵심 제약 2가지**
> 1. `BoidRule.type` 은 **읽기 전용**이다. `AttributeError: attribute "type" from
>    "BoidRule" is read-only`. 새 규칙 타입을 만들 수 없다.
> 2. `BoidState.rules` 에 `.new()` 가 없다. 오퍼레이터로만 규칙을 추가할 수 있는데,
>    `bpy.ops.boid.rule_add()` 는 헤드리스에서 `{'CANCELLED'}` 다.
>
> 결과적으로 **기본 2개 규칙(`Separate`, `Flock`)만 tweaking 가능**하다.
> 실측: `default rules: [('Separate','SEPARATE',True,True), ('Flock','FLOCK',True,True)]`
> 이름 / `use_in_air` / `use_on_land` / `ruleset_type` / `BoidSettings` 의 평탄화된
> 파라미터(`aggression` 등)는 직접 세팅 가능하다.

**`bpy.ops.boid.*` — 전부 ❌**

`poll()` 은 전부 `True` 인데 결과는 전부 `{'CANCELLED'}`.
`temp_override(window=..., screen=..., area=...)` 로도 해결 안 된다:

```
=== bpy.ops.boid.* behaviour in headless ===
  boid.rule_add         poll=True  params=['type']
  boid.rule_del         poll=True  params=[]
  boid.rule_move_down   poll=True  params=[]
  boid.rule_move_up     poll=True  params=[]
  boid.state_add        poll=True  params=[]
  boid.state_del        poll=True  params=[]
  boid.state_move_down  poll=True  params=[]
  boid.state_move_up    poll=True  params=[]
  state_add      -> {'CANCELLED'}
  rule_add(AVOID)-> {'CANCELLED'}
  rule_move_up   -> {'CANCELLED'}
  rule_del       -> {'CANCELLED'}
  state_move_up  -> {'CANCELLED'}
  state_del      -> {'CANCELLED'}
  with temp_override(window/screen/area), state_add -> {'CANCELLED'}
```

**Boid 시뮬레이션 자체는 헤드리스에서 동작한다** (verify/11):

```python
st.physics_type = 'BOIDS'
b = st.boids
s0 = b.states[0]
s0.name = "FlockAndSeparate"; s0.ruleset_type = 'AVERAGE'
s0.rules[0].name = "MySeparate"        # 타입(type)은 RO 라 못 바꾼다
s0.rules[0].use_in_air = True
b.use_flight = True
b.aggression, b.health, b.strength, b.range = 2.5, 12.0, 1.5, 8.0
b.air_speed_min, b.air_speed_max = 1.0, 4.0
st.count = 40
st.frame_start = st.frame_end = 1.0
st.lifetime = 200.0
st.emit_from = 'VOLUME'; st.distribution = 'RAND'
st.normal_factor = 0.0
st.effector_weights.boid = 1.0
st.effector_weights.gravity = 0.0
ps.seed = 3
for f in range(1, 13):
    sc.frame_set(f)
```

```
f=1   n=40  x[-2.9108,2.8014] y[-2.9860,2.8017]  p0=( 2.66927,-1.64476, 0.00000) |v|=1.0000
f=5   n=40  x[-2.8831,2.7890] y[-2.9580,2.7780]  p0=( 2.64650,-1.62819, 0.14764) |v|=0.9663
f=8   n=40  x[-2.8057,2.7275] y[-2.8792,2.7107]  p0=( 2.58515,-1.57686, 0.24358) |v|=1.1456
f=12  n=40  x[-2.6327,2.5922] y[-2.7052,2.5566]  p0=( 2.46033,-1.45195, 0.35453) |v|=1.4764
mean speed at f12: min=0.7566 med=1.2784 max=1.5148  (air_speed_max was 4.0)
ORIGINAL ps.particles len (expect 0): 0
point_cache info: '12 frames in memory (37 KiB).'
```

개체들이 서로 밀리며(`Separate`) flock center 를 중심으로 모이는(`Flock`) 거리가
f=1 `x[-2.91, 2.80]` (폭 5.71) → f=12 `x[-2.63, 2.59]` (폭 5.22) 로 좁아진다.
centroid 가 원점에서 `0.28, -0.22` 만큼 밀린 건 `Flock` center 가 메시 원점이기 때문.
속도가 `air_speed_max=4.0` 에 못 미치는 1.5 인 건 `strength`/`accuracy` 가 낮아서 —
파라미터가 실제로 작동함을 보여준다.

### 6.2 Fluid — 셋업은 되지만 **베이크가 헤드리스에서 불가**

#### 6.2.1 데이터 배치 (5.2 신구조)

`bpy.data.fluids` 같은 컬렉션은 **존재하지 않는다**. 모든 fluid 설정은
**모디파이어에 붙은 포인터** 다. 게다가 `fluid_type` 을 먼저 `'DOMAIN'` 으로
설정해야 해당 포인터가 할당된다.

```python
fm = obj.modifiers.new("Fluid", 'FLUID')   # fluid_type == 'NONE'
fm.domain_settings            # -> None
fm.fluid_type = 'DOMAIN'
fm.domain_settings            # -> <FluidDomainSettings>

fm.fluid_type = 'FLOW'   -> fm.flow_settings     (FluidFlowSettings)
fm.fluid_type = 'EFFECTOR' -> fm.effector_settings (FluidEffectorSettings)
```

`FluidModifier.fluid_type` enum: `NONE | DOMAIN | FLOW | EFFECTOR`

#### 6.2.2 `FluidDomainSettings` — 핵심 (전체 161 프로퍼티)

전수 덤프는 `verify/04_dpaint_fluid.py` 출력에 남아 있다. 여기서는 실제로 쓰는 것만.

| 프로퍼티 | 타입 | R/W | 기본값 | 비고 |
|---|---|---|---|---|
| `domain_type` | E | RW | GAS | `GAS` \| `LIQUID` |
| `resolution_max` | INT | RW | 32 | **계산 비용 결정 (상한)** |
| `cache_directory` | S | RW | `/tmp/blender_XXXX/cache_fluid_YYYY` | 기본값 자동 |
| `cache_type` | E | RW | REPLAY | `REPLAY`\|`MODULAR`\|`ALL` |
| `cache_data_format` / `cache_mesh_format` / `cache_noise_format` / `cache_particle_format` | E | RW | OPENVDB/UNI/OPENVDB/OPENVDB | `UNI`\|`OPENVDB`\|`RAW` |
| `cache_frame_start` / `_end` / `_offset` | I | RW | 1 / 250 / 0 | |
| `cache_frame_pause_data/guide/mesh/noise/particles` | I | RW | 0 | |
| `cache_resumable` | B | RW | False | 중단 재개 |
| `openvdb_cache_compress_type` | E | RW | BLOSC | `ZIP`\|`BLOSC`\|`NONE` |
| `simulation_method` | E | RW | FLIP | `FLIP`\|`APIC` |
| `timesteps_min` / `timesteps_max` | I | RW | 1 / 4 | |
| `use_adaptive_timesteps` | B | RW | True | |
| `use_mesh` / `use_noise` / `use_particles` / `use_fractions` | B | RW | True/F/F/F | |
| `use_flip_particles` / `use_foam_particles` / `use_bubble_particles` / `use_spray_particles` / `use_tracer_particles` | B | RW | False | |
| `use_viscosity` / `use_diffusion` / `use_dissolve_smoke` / `use_adaptive_domain` | B | RW | False | |
| `use_collision_border_left/right/top/bottom/front/back` | B | RW | False | 6개 |
| `use_color_ramp` / `color_ramp` / `color_ramp_field` | B/P/E | RW | — | `color_ramp_field` enum 은 `NONE` 단일 |
| `viscosity_base` / `viscosity_exponent` / `viscosity_value` | F/I/F | RW | 1.0 / 6 / 0.05 | |
| `surface_tension` / `vorticity` / `flip_ratio` / `cfl_condition` | F | RW | 0.0/0.0/0.97/2.0 | |
| `mesh_generator` | E | RW | IMPROVED | `IMPROVED`\|`UNION` |
| `particle_min` / `particle_max` / `particle_number` / `particle_radius` | I/I/I/F | RW | 8/16/2/1.0 | FLIP 입자 |
| `flame_ignition` / `flame_smoke` / `flame_max_temp` / `flame_vorticity` / `burning_rate` | F | RW | 1.5/1.0/3.0/0.5/0.75 | |
| `sndparticle_*` (16종) | F/I/E | RW | — | 2차 입자 (거품/물보라/연기) |
| `vector_display_type` | E | RW | NEEDLE | `NEEDLE`\|`STREAMLINE`\|`MAC` |
| `vector_field` | E | RW | FLUID_VELOCITY | `FLUID_VELOCITY`\|`GUIDE_VELOCITY`\|`FORCE` |
| `slice_axis` / `display_interpolation` / `highres_sampling` | E | RW | AUTO/LINEAR/FULLSAMPLE | |
| `show_gridlines` / `show_velocity` / `use_speed_vectors` / `use_slice` / `use_guide` | B | RW | False | |
| `has_cache_baked_any/data/guide/mesh/noise/particles` | B | **RW** | False | **쓰기 가능** — 검증에 사용 |
| `is_cache_baking_any/data/guide/mesh/noise/particles` | B | **RW** | False | |
| `effector_weights` | P→EffectorWeights | RO | | |
| `fluid_group` / `effector_group` / `force_collection` / `guide_parent` | P | RW | None | |
| `cell_size` / `density_grid` / `velocity_grid` / `domain_resolution` / `flame_grid` / `heat_grid` / `temperature_grid` / `start_point` / `color_grid` / `gravity` | F | **RO** | — | 계산 결과 |

#### 6.2.3 `FluidFlowSettings` (28개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `density` | F | RW | 1.0 |
| `density_vertex_group` | S | RW | `''` |
| `flow_behavior` | E | RW | GEOMETRY (`INFLOW`\|`OUTFLOW`\|`GEOMETRY`) |
| `flow_source` | E | RW | NONE (**단일 항목만** — EnumItemsDynamic) |
| `flow_type` | E | RW | SMOKE (`SMOKE`\|`BOTH`\|`FIRE`\|`LIQUID`) |
| `fuel_amount` / `temperature` | F | RW | 1.0 / 1.0 |
| `particle_size` | F | RW | 1.0 |
| `smoke_color` | F[3] | RW | |
| `subframes` | I | RW | 0 |
| `surface_distance` | F | RW | 1.0 |
| `texture_map_type` | E | RW | AUTO (`AUTO`\|`UV`) |
| `texture_offset` / `texture_size` | F | RW | 0.0 / 1.0 |
| `use_absolute` / `use_inflow` | B | RW | True / True |
| `use_initial_velocity` | B | RW | False |
| `use_particle_size` | B | RW | True |
| `use_plane_init` / `use_texture` | B | RW | False / False |
| `uv_layer` | S | RW | `''` |
| `velocity_coord` | F[3] | RW | (0,0,0) |
| `velocity_factor` / `velocity_normal` / `velocity_random` | F | RW | 1.0 / 0.0 / 0.0 |
| `volume_density` | F | RW | 0.0 |

`FluidEffectorSettings` 는 존재하며 `effector_type` enum(`COLLISION` 등)을 갖는다.

#### 6.2.4 ❌ 베이크는 헤드리스에서 **불가능** (5가지 경로 전부 실패)

시도한 6가지 경로 (verify/14, 14b) — **전부** `RuntimeError: Error: Invalid domain`:
① `modifiers.new` 후 바로 `bake_all` ② `object.modifier_add(type='FLUID')`
③ `show_viewport` 토글 + `dg.update()` 후 ④ 프레임 몇 개 step 후
⑤ `fluid_type` 재할당 후 ⑥ `.blend` 저장 → 재오픈 → bake.

verify/14b V3 (저장 후 재오픈):
`save -> {'FINISHED'}` / `reopen -> {'FINISHED'}` /
`reopened domain_settings: <FluidDomainSettings> | type: DOMAIN` /
`fluid.bake_all after reopen -> EXC Error: Invalid domain` /
`baked_any: False` / `cache dir: ['scene.blend']` (캐시 파일 없음)

모든 `fluid.bake_*` / `fluid.free_*` / `fluid.pause_bake` 가 `poll()` True 인데
`RuntimeError: Invalid domain` 으로 죽는다. `bake_all` 후
`has_cache_baked_any=False`, 캐시 디렉터리도 비어 있다.

**fluid 오퍼레이터 판정 (전수)**

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `fluid.bake_all` | ❌ | `RuntimeError: Invalid domain` |
| `fluid.bake_data` | ❌ | 동일 |
| `fluid.bake_mesh` | ❌ | 동일 |
| `fluid.bake_particles` | ❌ | 동일 |
| `fluid.bake_noise` | ❌ | 동일 |
| `fluid.bake_guides` | ❌ | 동일 |
| `fluid.free_all` | ❌ | 동일 |
| `fluid.free_data` | ❌ | 동일 |
| `fluid.free_mesh` | ❌ | 동일 |
| `fluid.free_particles` | ❌ | 동일 |
| `fluid.free_noise` | ❌ | 동일 |
| `fluid.free_guides` | ❌ | 동일 |
| `fluid.pause_bake` | ❌ | `RuntimeError: Bake free failed: invalid domain` |
| `fluid.preset_add` | ❌ | `{'CANCELLED'}` — `context.fluid` 필요 (cloth 와 같은 메커니즘) |
| `bpy.ops.object.fluid_add` | ❌ | **제거됨** |
| `bpy.ops.object.quick_smoke` | ✅ | 도메인+inflow 오브젝트 생성까지만 성공. bake 는 불가 |
| `bpy.ops.object.quick_liquid` | ✅ | 동일 |

**정리 (정직하게)**: fluid **셋업**은 헤드리스에서 완전 가능하고 검증됐다.
하지만 **Mantaflow 시뮬레이션 결과 자체는 이 환경에서 검증하지 못했다.**
렌더 파이프라인에 실리는 유체 데이터 한 프레임도 만들지 못했다.

### 6.3 Dynamic Paint — 5.2 에서 대폭 개편

```python
m = obj.modifiers.new("DynPaint", 'DYNAMIC_PAINT')
m.ui_type          # 'CANVAS' | 'BRUSH'   <-- 새 축
m.canvas_settings  # 처음엔 None !
m.brush_settings   # 처음엔 None !
```

**`canvas_settings` / `brush_settings` 는 처음에 `None`** 이다.
`bpy.ops.dpaint.type_toggle()` 를 한 번 불러야 할당된다:

```
  before any op: ui_type=CANVAS canvas=None brush=None
  has dynpaint_surfaces: False | has dynamic_paint_type: False
  type_toggle -> {'FINISHED'}
  after type_toggle: ui_type=CANVAS canvas=<DynamicPaintCanvasSettings> brush=None
  canvas_surfaces: 1
```

5.2 에서 사라진 것: `DynamicPaintModifier.dynpaint_surfaces` (없음),
`dynamic_paint_type` (없음), `DynamicPaintSurface` 의 `surface_type` 는 남았지만
러너업 방식이 완전히 바뀌었다.

* `DynamicPaintCanvasSettings`: 프로퍼티 **1개뿐** — `canvas_surfaces` (RO 컬렉션)
* `DynamicPaintBrushSettings`: 28개 — `paint_color` `paint_alpha` `use_absolute_alpha`
  `paint_wetness` `use_paint_erase` `wave_type` `wave_factor` `wave_clamp` `use_smudge`
  `smudge_strength` `velocity_max` `use_velocity_alpha` `use_velocity_depth`
  `use_velocity_color` `paint_source` `paint_distance` `use_proximity_ramp_alpha`
  `proximity_falloff` `use_proximity_project` `ray_direction` `invert_proximity`
  `use_negative_volume` `particle_system` `use_particle_radius` `solid_radius`
  `smooth_radius` `paint_ramp` `velocity_ramp`
* `DynamicPaintSurface`: 48개 — `surface_format` `surface_type` `is_active` `name`
  `brush_collection` `use_dissolve` `dissolve_speed` `use_drying` `dry_speed`
  `image_resolution` `uv_layer` `frame_start` `frame_end` `frame_substeps`
  `use_antialiasing` `brush_influence_scale` `brush_radius_scale` `init_color_type`
  `init_color` `init_texture` `init_layername` `effect_ui` `use_dry_log`
  `use_dissolve_log` `use_spread` `spread_speed` `color_dry_threshold`
  `color_spread_speed` `use_drip` `use_shrink` `shrink_speed` `effector_weights`
  `drip_velocity` `drip_acceleration` `use_premultiply` `image_output_path`
  `output_name_a` `use_output_a` `output_name_b` `use_output_b` `depth_clamp`
  `displace_factor` `image_fileformat` `displace_type` `use_incremental_displace`
  `wave_damping` `wave_speed` `wave_timescale` `wave_spring` `wave_smoothness`
  `use_wave_open_border` `point_cache` `is_cache_user`

**오퍼레이터 판정**

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `dpaint.type_toggle` | ✅ | `{'FINISHED'}`, `canvas_settings` 할당 트리거 |
| `dpaint.surface_slot_add` | ⚠ | `type_toggle` 직후 `{'FINISHED'}` (1→2), 단독 호출은 `{'CANCELLED'}` |
| `dpaint.surface_slot_remove` | ⚠ | `type_toggle` 직후 `{'FINISHED'}` (2→1) |
| `dpaint.output_toggle` | ⚠ | `type_toggle` 직후 `{'FINISHED'}`, 단독은 `{'CANCELLED'}` |
| `dpaint.bake` | ❌ | `RuntimeError`, 로그에 `WARNING Baking canceled!` |
| `bpy.ops.object.dupevoter_paint` | ❌ | **제거됨** |

실측:

```
  type_toggle -> {'FINISHED'}
  surface_slot_add -> {'FINISHED'}    canvas_surfaces: 1 -> 2
  output_toggle -> {'FINISHED'}
  dpaint.bake poll: True ; -> EXC (WARNING Baking canceled!)
  surface_slot_remove -> {'FINISHED'}  -> 1
  after type_toggle(BRUSH): brush=<DynamicPaintBrushSettings> (28 props)
```

`bpy.data.paint_curves` 는 **존재하는 컬렉션**이다 (`bpy_prop_collection`).
헤드리스에서 빈 채로 남는다 — 채우려면 `paintcurve.new()` 가 필요한데 그건 ❌:

| `bpy.ops.paintcurve.*` (전수 8개) | 판정 | 근거 |
|---|---|---|
| `paintcurve.new` | ❌ | `poll()` False, `RuntimeError` |
| `paintcurve.add_point` | ❌ | 동일 |
| `paintcurve.add_point_slide` | ❌ | 동일 |
| `paintcurve.delete_point` | ❌ | 동일 |
| `paintcurve.draw` | ❌ | 동일 |
| `paintcurve.select` | ❌ | 동일 |
| `paintcurve.cursor` | ❌ | 동일 |
| `paintcurve.slide` | ❌ | 동일 |

`PaintCurve` 데이터블록을 수동 생성할 방법도 없다:
`bpy.data.paint_curves.new("name")` 가 있는지는 못 확인했다
(verify/22 에서 시도하지 않음 — ⚠ 미검증).

### 6.4 Metaball — 완전 동작

```python
bpy.ops.object.metaball_add(type='BALL', location=(0, 0, 0))   # ✅
mb.data.elements.new()          # 데이터 API 로 요소 추가
```

`object.metaball_add` `type` enum: `BALL | CAPSULE | PLANE | ELLIPSOID | CUBE`

`MetaBall` (ID) 핵심: `elements`(RO), `resolution`(F, 0.4), `render_resolution`(F, 0.2),
`threshold`(F, 0.6), `texspace_size`(F), `texspace_location`(F[3]),
`use_auto_texspace`(B, True), `update_method`(E: `UPDATE_ALWAYS|HALFRES|FAST|NEVER`),
`is_editmode`(RO, B)

`MetaElement` (12개, 전수):

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `type` | ENUM | RW | BALL (`BALL`\|`CAPSULE`\|`PLANE`\|`ELLIPSOID`\|`CUBE`) |
| `co` | F[3] | RW | (0,0,0) |
| `rotation` | F[3] | RW | (0,0,0) |
| `radius` | F | RW | 0.0 |
| `size_x` / `size_y` / `size_z` | F | RW | 0.0 |
| `stiffness` | F | RW | 0.0 |
| `use_negative` | B | RW | False |
| `use_scale_stiffness` | B | RW | True |
| `select` | B | RW | False |
| `hide` | B | RW | False |

**실측 머지 결과** (r=1.0 @ 원점 + r=0.6 @ x=1.2, resolution 0.2):

```
elements: 2 | radii: [1.0, 0.6000000238418579]
evaluated verts: 216 polys: 252
bbox x[-0.558,1.515] y[-0.558,0.558] z[-0.558,0.558]
```

`bpy.ops.mball.*` — **8개 전부 ⚠ (EDIT 모드 필요)**.
EDIT 모드 진입은 헤드리스에서 가능하고(`bpy.ops.object.mode_set(mode='EDIT')`),
그 뒤 전부 `{'FINISHED'}`:

```
  --- try to enter metaball EDIT mode headless ---
   object.mode_set(EDIT) -> {'FINISHED'}
   is_editmode now: True | object.mode: EDIT
   mball.delete_metaelems         poll=True
   mball.duplicate_metaelems      poll=True
   ... (8개 전부 poll=True)

  --- direct mball calls in EDIT mode ---
   select_all(SELECT) -> {'FINISHED'}
   duplicate_metaelems -> {'FINISHED'}   elements: 1 -> 2
   hide_metaelems -> {'FINISHED'}        hidden: [False, True]
   reveal_metaelems -> {'FINISHED'}      hidden: [False, False]
   select_random_metaelems -> {'FINISHED'}
   duplicate_move -> {'FINISHED'}        elements: 2 -> 4
   select_similar -> {'FINISHED'}
   delete_metaelems -> {'FINISHED'}      elements: 4 -> 0
```

필요한 인자: `select_all(action)` · `duplicate_metaelems()` · `delete_metaelems(confirm)` ·
`hide_metaelems(unselected)` · `reveal_metaelems(select)` ·
`select_random_metaelems(ratio, seed, action)` · `select_similar(type, threshold)` ·
`duplicate_move()` (인자 없음 — 내부 2-operator 래퍼). **8개 전부 ⚠ → EDIT 모드에서 ✅**.

> 판정 표기: `⚠ 컨텍스트 필요` 는 "추가 컨텍스트로 해결 가능" 이라는 프로토콜 정의에
> 부합한다. 여기서 필요한 컨텍스트는 `temp_override` 가 아니라 **오브젝트 모드** 다.

### 6.5 Effector — 13종 전부 생성 성공

```python
bpy.ops.object.effector_add(type='WIND', location=(0, 0, 0))   # ✅
obj.field.type      # FieldSettings
obj.field.strength
```

`effector_add` `type` enum (13종) — **전부 `{'FINISHED'}`**:

`FORCE` `WIND` `VORTEX` `MAGNET` `HARMONIC` `CHARGE` `LENNARDJ` `TEXTURE`
`GUIDE` `BOID` `TURBULENCE` `DRAG` `FLUID`

```
  effector_add(FORCE     ) -> {'FINISHED'} field=True type=FORCE
  effector_add(WIND      ) -> {'FINISHED'} field=True type=WIND
  ... (13줄 모두 동일 패턴)
  effector_add(FLUID     ) -> {'FINISHED'} field=True type=FLUID_FLOW
```

`FieldSettings.type` enum: `NONE|BOID|CHARGE|GUIDE|DRAG|FLUID_FLOW|FORCE|HARMONIC|
LENNARDJ|MAGNET|TEXTURE|TURBULENCE|VORTEX|WIND`
`FieldSettings.shape` enum: `POINT|LINE|PLANE|SURFACE|POINTS`
`FieldSettings.falloff_type` enum: `CONE|SPHERE|TUBE`

### 6.6 `EffectorWeights` (17개, 전수)

| 프로퍼티 | 타입 | R/W | 기본값 |
|---|---|---|---|
| `all` | F | RW | 0.0 | 전부 한번에 |
| `apply_to_hair_growing` | B | RW | False |
| `boid` | F | RW | 0.0 |
| `charge` | F | RW | 0.0 |
| `collection` | → Collection | RW | None |
| `curve_guide` | F | RW | 0.0 |
| `drag` | F | RW | 0.0 |
| `force` | F | RW | 0.0 |
| `gravity` | F | RW | 0.0 |
| `harmonic` | F | RW | 0.0 |
| `lennardjones` | F | RW | 0.0 |
| `magnetic` | F | RW | 0.0 |
| `smokeflow` | F | RW | 0.0 |
| `texture` | F | RW | 0.0 |
| `turbulence` | F | RW | 0.0 |
| `vortex` | F | RW | 0.0 |
| `wind` | F | RW | 0.0 |

```python
ps.settings.effector_weights.wind = 0.8
c = bpy.data.collections.new("Eff")
c.objects.link(wind)
ps.settings.effector_weights.collection = c    # 이 컬렉션만 영향
```
검증: `effector_weights.collection = Eff -> [ ['Wind'] ]`

`bpy.ops.object.forcefield_toggle` ✅ — `{'FINISHED'}`.

---

## 7. 캐시 & 결정성

### 7.1 `PointCache` (15개, 전수) — 모든 시뮬 공통

| 프로퍼티 | 타입 | R/W | 기본값 | 비고 |
|---|---|---|---|---|
| `filepath` | STRING | RW | `''` | ⚠ **5.2 에서 사실상 무시됨** (§7.2) |
| `frame_start` | INT | RW | 0 | |
| `frame_end` | INT | RW | 0 | |
| `frame_step` | INT | RW | 0 | |
| `index` | INT | RW | 0 | 메모리 캐시는 **-1** |
| `info` | STRING | **RO** | `''` | §1.4 진단 문자열 |
| `is_baked` | BOOLEAN | **RO** | False | |
| `is_baking` | BOOLEAN | **RO** | False | |
| `is_frame_skip` | BOOLEAN | **RO** | False | |
| `is_outdated` | BOOLEAN | **RO** | False | ⚠ 파라미터 바꿔도 False 유지 (§7.3) |
| `name` | STRING | RW | `''` | |
| `point_caches` | COLLECTION | RO | | |
| `use_disk_cache` | BOOLEAN | RW | False | §7.2 |
| `use_external` | BOOLEAN | RW | False | |
| `use_library_path` | BOOLEAN | RW | **True** | 상대경로 해석 방식 |

### 7.2 디스크 캐시는 **`blendcache_<blend이름>/` 옆** 에 쌓인다

**`PointCache.filepath` 는 5.2 에서 완전히 무시된다.** 세 가지 설정이 전부
같은 곳에 쓴다:

```
A libpath=True  rel 'cachedir/cloth'     -> {'FINISHED'} is_baked=True
B libpath=False abs '/tmp/abscache/cloth'-> {'FINISHED'} is_baked=True
   A, B 모두 -> /tmp/dctest/blendcache_scene/436C6F7468_000001_00.bphys (130 B)
                  /tmp/dctest/blendcache_scene/436C6F7468_000002_00.bphys (276 B)  ... 6 files
```

파일명 규칙: `{오브젝트이름 hex}_{프레임:06d}_{서브프레임:02d}.bphys`
`436C6F7468` = `"Cloth"`, `47726964` = `"Grid"`, `43756265` = `"Cube"`.

**`.blend` 를 저장하지 않으면 디스크 캐시가 안 생긴다** (silent):

```
### CASE 1: NO .blend saved ###
  bpy.data.filepath = ''
  bake -> {'FINISHED'} | is_baked = True
  .bphys files anywhere in /tmp: []          <-- 없음!
  /tmp/dctest2 contents: []                 <-- 없음!

### CASE 2: saved to /tmp/dctest2/my_scene.blend ###
  saved. bpy.data.filepath = /tmp/dctest2/my_scene.blend
  use_disk_cache=True filepath='SOME_RELATIVE_NAME' use_library_path=True
  bake_all -> {'FINISHED'}
  [disk] is_baked=True is_baking=False is_outdated=False index=0
         info='6 frames on disk.'
  blend dir: ['blendcache_my_scene', 'my_scene.blend']
```

즉 **`is_baked == True` 인데 파일이 0개** 라는 상태가 실제로 일어난다.
항상 `point_cache.info` 로 `'frames on disk'` vs `'frames in memory'` 를 확인하라.

재오픈하면 디스크 캐시가 그대로 재사용된다:

재오픈하면 그대로 재사용된다 (verify/07d):
`reopened is_baked=True index=0 info='6 frames on disk.'` →
f=1 `0.00000`, f=2 `-0.00580`, f=3 `-0.02102`, f=4 `-0.04536`, f=5 `-0.07852`, f=6 `-0.12022`

### 7.3 ⚠ 시뮬 파라미터를 바꿔도 bake 가 무효화되지 않는다

`is_outdated` 는 `False` 로 남고, **이전 결과가 그대로 나온다** (verify/07e, 클로스 6프레임):

| 단계 | avg z @ f1..f6 |
|---|---|
| A) `mass=0.3` bake | `0.00000 -0.00580 -0.02102 -0.04536 -0.07852 -0.12022` |
| B) `mass=9.9` 로 변경, free 안 함 | `0.00000 -0.00580 -0.02102 -0.04536 -0.07852 -0.12022` ← **stale** (`is_outdated=False`) |
| C) `free_bake_all()` 후 재실행 | `0.00000 -0.00588 -0.02156 -0.04703 -0.08228 -0.12730` |

`free_bake_all()` 이후 값이 바뀐다 (0.12022 → 0.12730) — 시뮬이 실제로 달라졌다는 증거.
**캐시 무효화는 수동으로만 된다.** 파라미터 바꿨으면 반드시:

```python
bpy.ops.ptcache.free_bake_all()
# 값 변경
bpy.ops.ptcache.bake_all(bake=True)
```

`frame_step = 2` 로 설정해도 `.bphys` 파일 수는 6개 그대로였고 계산 결과도 동일했다
(클로스 기준). 즉 5.2 에서 `frame_step` 의 효과는 최소하다.

### 7.4 `ptcache.*` 오퍼레이터 판정

| 오퍼레이터 | 판정 | 근거 |
|---|---|---|
| `ptcache.bake_all(bake=True)` | ✅ | `{'FINISHED'}`, `poll()` 항상 True |
| `ptcache.free_bake_all()` | ✅ | `{'FINISHED'}`, `poll()` 항상 True |
| `ptcache.bake(bake=True)` | ⚠ | `poll()` False. `temp_override(point_cache=pc)` 로 해결 → `{'FINISHED'}` |
| `ptcache.free_bake()` | ⚠ | 동일 (`temp_override(point_cache=pc)`) |
| `ptcache.add()` | ❌ | `poll()` False, `RuntimeError` |
| `ptcache.remove()` | ❌ | `poll()` False, `RuntimeError` |
| `ptcache.bake_from_cache()` | ❌ | `poll()` False, `RuntimeError` |
| `ptcache.is_baking()` | ❌ | 오퍼레이터 아님, `point_cache.is_baking` 프로퍼티 |
| `ptcache.filepath_get/set()` | ❌ | 오퍼레이터 아님, `point_cache.filepath` 프로퍼티 |

```python
# ptcache.bake 를 쓰고 싶을 때 (개별 캐시만)
pc = m.point_cache
with bpy.context.temp_override(point_cache=pc):
    bpy.ops.ptcache.bake(bake=True)
```

### 7.5 물리 난수는 `scene.cycles.seed` 로 제어되지 않는다

확인된 사실:

| 난수원 | 제어 방법 | 검증 |
|---|---|---|
| 파티클 방출 위치/속도 | `particle_system.seed` (INT) | ✅ 동일 seed → 동일 결과 |
| 파티클 자식 | `particle_system.child_seed` (INT) | ✅ 존재 |
| `size_random` / `lifetime_random` | `particle_system.seed` | ✅ seed=1 vs 2 에서 size 배열 상이 |
| 리지드바디 | 결정론적 (Bullet, 난수 없음) | ✅ 해석해와 0.4% 일치 |
| 클로스 | 결정론적 | ✅ free_bake/resim 재현 |
| **Cycles 렌더 샘플** | `scene.cycles.seed` | 파티클에 **영향 없음** |

```
  cycles.seed=1  : [(-0.204349, -0.891989, 0.048608), ...]
  cycles.seed=777: [(-0.204349, -0.891989, 0.048608), ...]
  identical (cycles.seed irrelevant to particles): True
```

### 7.6 결정성 레시피 (복사해서 쓰세요)

```python
import bpy

# 1) 모든 난수원 고정
for obj in bpy.data.objects:
    for psys in obj.particle_systems:
        psys.seed = 20240101
        psys.child_seed = 20240102

# 2) 물리 범위를 프레임 수에 맞춰 고정
sc = bpy.context.scene
if sc.rigidbody_world:
    sc.rigidbody_world.point_cache.frame_start = sc.frame_start
    sc.rigidbody_world.point_cache.frame_end   = sc.frame_end
for obj in bpy.data.objects:
    for mod in obj.modifiers:
        if mod.type in {'CLOTH', 'SOFT_BODY', 'PARTICLE_SYSTEM'}:
            mod.point_cache.frame_start = sc.frame_start
            mod.point_cache.frame_end   = sc.frame_end
            mod.point_cache.frame_step  = 1
            mod.point_cache.use_disk_cache = True
            mod.point_cache.use_external = False

# 3) 결정론적 순차 시뮬레이션 (점프 금지)
for f in range(sc.frame_start, sc.frame_end + 1):
    sc.frame_set(f)
```

`sc.cycles.seed` 는 렌더 노이즈만 푼다. 물리 재현성은 위 3단계로 확보한다.

### 7.7 예제 3 (핵심) — "1~50프레임 시뮬 → 50프레임 렌더" 레시피

```python
"""3종 시뮬(리지드바디/클로스/파티클) 을 50프레임 돌리고 50프레임을 렌더한다."""
import bpy
import os
import time
import addon_utils

OUT = "/workspace/out/sim_ex3"
os.makedirs(OUT, exist_ok=True)
BL = OUT + "/rigid_fall.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("cycles", default_set=True, persistent=True)

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 16
sc.render.resolution_x = sc.render.resolution_y = 96
sc.frame_start, sc.frame_end = 1, 50
sc.render.fps = 24
sc.frame_set(1)

bpy.ops.object.camera_add(location=(9, -9, 6), rotation=(1.05, 0, 0.79))
sc.camera = bpy.context.object
bpy.ops.object.light_add(type='SUN', location=(4, -4, 8))
bpy.context.object.data.energy = 5.0


def mat(name, rgb, rough=0.5):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


# ---- 리지드바디
bpy.ops.rigidbody.world_add()
w = sc.rigidbody_world
w.substeps_per_frame = 10
w.solver_iterations = 10
w.point_cache.frame_start, w.point_cache.frame_end = 1, 50   # 기본 1..250 !

bpy.ops.mesh.primitive_plane_add(size=20)
g = bpy.context.object
g.name = "Ground"
g.data.materials.append(mat("GroundMat", (0.25, 0.25, 0.28)))
bpy.ops.rigidbody.object_add()
g.rigid_body.type = 'PASSIVE'
g.rigid_body.friction = 0.9

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 4))
box = bpy.context.object
box.name = "Box"
box.rotation_euler = (0.4, 0.25, 0.0)
box.data.materials.append(mat("BoxMat", (0.8, 0.25, 0.1), rough=0.3))
bpy.ops.rigidbody.object_add()
rb = box.rigid_body
rb.type = 'ACTIVE'
rb.collision_shape = 'BOX'
rb.mass = 2.0
rb.restitution = 0.25
rb.friction = 0.5
rb.use_margin = True
rb.collision_margin = 0.04

# ---- 클로스
bpy.ops.mesh.primitive_grid_add(x_subdivisions=6, y_subdivisions=6, size=2,
                                location=(3.2, 0, 4))
cl = bpy.context.object
cl.name = "Cloth"
cl.data.materials.append(mat("ClothMat", (0.15, 0.45, 0.75), rough=0.8))
vg = cl.vertex_groups.new(name="Pin")
maxy = max(v.co.y for v in cl.data.vertices)
vg.add([v.index for v in cl.data.vertices if v.co.y > maxy - 1e-4], 1.0, 'REPLACE')
cm = cl.modifiers.new("Cloth", 'CLOTH')
cm.settings.mass = 0.3
cm.settings.quality = 5
cm.settings.vertex_group_mass = "Pin"
cm.settings.air_damping = 1.0
cm.point_cache.frame_start, cm.point_cache.frame_end = 1, 50

# ---- 파티클 (인스턴스 오브젝트 + 이미터 분리!)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4, size=1.2,
                                location=(-3.2, 0, 4))
em = bpy.context.object
em.name = "Emitter"
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.08)
inst = bpy.context.object
inst.name = "Instance"
inst.data.materials.append(mat("InstMat", (0.9, 0.8, 0.15), rough=0.2))
bpy.ops.object.select_all(action='DESELECT')
em.select_set(True)
bpy.context.view_layer.objects.active = em
bpy.ops.object.particle_system_add()
ps = em.particle_systems[0]
pst = ps.settings
pst.count = 120
pst.frame_start = pst.frame_end = 1.0
pst.lifetime = 200.0
pst.render_type = 'OBJECT'
pst.instance_object = inst
pst.particle_size = 0.8
pst.mass = 0.1
pst.drag_factor = 0.05
pst.integrator = 'RK4'
pst.effector_weights.gravity = 1.0
ps.seed = 2024
inst.hide_render = True
inst.hide_viewport = True

bpy.ops.wm.save_as_mainfile(filepath=BL)      # <- 디스크 캐시 전에 .blend 저장 필수

# ===== 1..50 순차 시뮬레이션 =====
t0 = time.time()
for f in range(1, 51):
    sc.frame_set(f)
    if f in (1, 10, 25, 40, 50):
        dg = bpy.context.evaluated_depsgraph_get()
        m = box.evaluated_get(dg).matrix_world
        eo = em.evaluated_get(dg).particle_systems[0]
        eo2 = cl.evaluated_get(dg)
        me = eo2.to_mesh()
        avz = sum(v.co.z for v in me.vertices) / len(me.vertices)
        eo2.to_mesh_clear()
        print("f=%-3d box.z=%9.5f  cloth_avg_z=%9.5f  particles=%d" % (
            f, m.translation.z, avz, len(eo.particles)))
print("simulation of 50 frames took %.2f s" % (time.time() - t0))
print("rigid world is_baked:", w.point_cache.is_baked,
      "| cloth cache:", cm.point_cache.info,
      "| particle cache:", ps.point_cache.info)

# ===== bake 후 50프레임 렌더 =====
t0 = time.time()
print("\nbake_all ->", bpy.ops.ptcache.bake_all(bake=True))
print("bake took %.2f s" % (time.time() - t0))
print("after bake: rigid is_baked=%s | %s | %s" % (
    w.point_cache.is_baked, cm.point_cache.info, ps.point_cache.info))

t0 = time.time()
sc.frame_set(50)
sc.render.filepath = OUT + "/frame_050.png"
bpy.ops.render.render(write_still=True)
print("render frame 50 took %.2f s -> %s (%d bytes)" % (
    time.time() - t0, sc.render.filepath, os.path.getsize(sc.render.filepath)))
print("__SCRIPT_OK__")
```

**실측 출력**:

```
active object for particle_system_add: Emitter
object.particle_system_add -> {'FINISHED'} | systems on Em: ['ParticleSystem'] | on Inst: []
Info: Saved as "rigid_fall.blend"
f=1   box.z=  4.00000  cloth_avg_z=  0.00000  particles=120
f=10  box.z=  3.30608  cloth_avg_z= -0.28045  particles=120
f=25  box.z=  0.51930  cloth_avg_z= -0.98130  particles=120
f=40  box.z=  0.50000  cloth_avg_z= -0.82378  particles=120
f=50  box.z=  0.50000  cloth_avg_z= -0.82301  particles=120
simulation of 50 frames took 0.06 s
rigid world is_baked: False | cloth cache: 50 frames in memory (92 KiB). | particle cache: 50 frames in memory (170 KiB).
bake_all -> {'FINISHED'}
bake took 0.11 s
after bake: rigid is_baked=True | 50 frames in memory (92 KiB). | 50 frames in memory (170 KiB).
render frame 50 took 0.87 s -> /workspace/out/sim_ex3/frame_050.png (11683 bytes)
__SCRIPT_OK__
```

(위 스크립트는 `use_disk_cache = True` 를 켜지 않았으므로 `info` 가 `in memory` 다.
디스크 캐시를 원하면 각 `point_cache.use_disk_cache = True` 를 추가하되
**`.blend` 저장이 먼저**여야 한다 — §7.2.)

### 7.8 ⚠ 단일 프레임 렌더가 1프레임을 보여주는 이유 (실측 컨트롤)

이것이 §2(요구사항)에서 언급한 "single-frame render of a sim often shows frame 1" 의
**정확한 실체** 다. 4가지 경로를 같은 씬에서 비교했다:

```
=== CASE A: no pre-simulation, jump straight to frame 50 and render ===
  box.z after frame_set(50) with NO prior stepping: 5.00000     <-- 초기값!
  render mean luma = 0.636755

=== CASE B: sequential 1..50, then frame 50, then render ===
  box.z after sequential 1..50 then frame_set(50): 0.50006
  render mean luma = 0.635597

=== CASE C: bake first (disk), then jump ===
  bake_all -> {'FINISHED'}
  box.z after bake + frame_set(50): 0.50006
  render mean luma = 0.635597

=== CASE D: animation render of the 50-frame range ===
  animation render took 14.83 s, frames written: 50
  box.z at 50 after animation render: 5.00000                  <-- 또 초기값!
  render mean luma = 0.636755
```

`render(animation=True)` 도 프레임을 진행시키지 않는다. PNG 픽셀 해시로 확인:

```
D_anim_0001/0010/0025/0050.png  md5=a13ef33c743ef8cd   <-- 전부 동일
A_jump50_nosim.png              md5=a13ef33c743ef8cd   <-- 1프레임 이미지와 동일
D_after_anim_50.png             md5=a13ef33c743ef8cd
B_seq50.png                     md5=9ff539c95136a704
C_baked50.png                   md5=9ff539c95136a704   <-- B 와 동일
```

**50프레임 렌더한 결과물 50장이 완전히 동일**하다.

더 세밀한 실험 (verify/18, 12프레임, 48x48, 4spp):

```
T1: render(animation=True), no pre-sim        -> unique frames: 1   (전부 1451f6a78c6b)
T2: sequential pre-sim 1..12, animation render-> unique frames: 11
T3: bake_all, animation render                -> unique frames: 11   (T2 와 바이트 동일)
T4: per-frame frame_set + write_still, no bake-> unique frames: 11   (T2 와 바이트 동일)
T5: bake + per-frame write_still              -> unique frames: 11   (T2 와 바이트 동일)
T3 vs T5 matching frames: 12 / 12      T3 vs T2 matching frames: 12 / 12
```

**결론 (4가지 모두 동일 결과)**:

| 사전 처리 | `render(animation=True)` | 프레임별 `frame_set`+`write_still` |
|---|---|---|
| 없음 | ❌ 전부 1프레임 (unique 1) | ❌ 1프레임 |
| 순차 1..N | ✅ 정확 (unique 11/12) | ✅ 정확 |
| `bake_all` | ✅ 정확 | ✅ 정확 |

> unique 11/12 인 이유: f=2 와 f=3 의 해시가 같음. 서브프레임 타이밍 때문에
> 초기 2프레임에는 아직 눈에 띄는 이동이 없다. 물리 버그가 아니다.

**레시피 요약**

```
1. 씬 구성
2. bpy.ops.wm.save_as_mainfile(...)        <- 디스크 캐시 필수 시
3. for f in 1..N: scene.frame_set(f)      <- 또는 bpy.ops.ptcache.bake_all(bake=True)
4. bpy.ops.render.render(...)             <- 이제 아무거나 OK
```

### 7.9 물리 메모리 예산

`bpy.context.preferences.system.memory_cache_limit` (기본 `4096` MB) — in-memory point cache
총 예산. 초과 시 오래된 프레임이 eviction 된다. 장시간이면 `use_disk_cache = True` 로 넘겨라.
(참고: `pref.system.physics_substeps`, `pref.view.use_simplify` 같은 관련 항목은
5.2 에서 **존재하지 않는다** — `'<none>'` 로 확인됨.)

---

## 8. 전체 오퍼레이터 판정 요약표

아래 표는 **verify/20_verdict_matrix.py** 결과다. 각 오퍼레이터마다 **신규 씬**을
만들고 (`bpy.ops.wm.read_factory_settings(use_empty=True)`) 한 번만 호출했다.

### 8.1 ✅ 헤드리스 OK — 51개 (실제로 `{'FINISHED'}`)

| 그룹 | 오퍼레이터 |
|---|---|
| `rigidbody` (12) | `world_add` `world_remove` `object_add` `object_remove` `objects_add` `objects_remove` `constraint_add` `constraint_remove` `object_settings_copy` `shape_change` `mass_calculate` `connect` |
| `ptcache` (2) | `bake_all` `free_bake_all` |
| `object` (8) | `particle_system_add` `particle_system_remove` `quick_fur` `quick_smoke` `quick_liquid` `quick_explode` `effector_add` `forcefield_toggle` `metab_add`(=`metaball_add`) |
| `mball` (8, EDIT 모드 필수) | `select_all` `duplicate_metaelems` `delete_metaelems` `hide_metaelems` `reveal_metaelems` `select_random_metaelems` `select_similar` `duplicate_move` |
| `particle` (19) | `particle_edit_toggle` `edited_clear` `select_random`* `select_all`* `select_roots`* `select_tips`* `select_linked`* `select_more`* `select_less`* `subdivide`* `rekey`* `mirror`* `hide`* `reveal`* `weight_set`* `delete`* `particle_system_remove_all` `duplicate_particle_system` `hair_dynamics_preset_add` `disconnect_hair` |
| `dpaint` (1) | `type_toggle` |

`*` = `type='HAIR'` + `PARTICLE_EDIT` 모드 필요 (§5.8)

추가 ✅ (verify/22 에서 별도 검증): `object.modifier_add` (CLOTH / SOFT_BODY / FLUID /
COLLISION / DYNAMIC_PAINT / PARTICLE_SYSTEM / EXPLODE / OCEAN / MESH_CACHE /
MESH_SEQUENCE_CACHE / NODES / PARTICLE_INSTANCE 전부 `{'FINISHED'}`)

### 8.2 ⚠ 컨텍스트 필요 — 12개

| 오퍼레이터 | 필요한 컨텍스트 | 해결법 |
|---|---|---|
| `mball.*` (8) | 메타볼 오브젝트 **EDIT 모드** + 활성 | `bpy.ops.object.mode_set(mode='EDIT')` |
| `particle.*` 편집 (13) | `type='HAIR'` + **PARTICLE_EDIT 모드** | `mode_set(EDIT)` → `particle_edit_toggle()` |
| `ptcache.bake` | `context.point_cache` | `temp_override(point_cache=pc)` |
| `ptcache.free_bake` | `context.point_cache` | `temp_override(point_cache=pc)` |
| `dpaint.surface_slot_add/remove`, `dpaint.output_toggle` | `canvas_settings` 할당 | 먼저 `dpaint.type_toggle()` |

### 8.3 ❌ UI 전용 / 헤드리스 불가 — 47개

| 그룹 | 오퍼레이터 | 실패 형태 |
|---|---|---|
| `boid` (8) | `state_add` `state_del` `state_move_up` `state_move_down` `rule_add` `rule_del` `rule_move_up` `rule_move_down` | `{'CANCELLED'}` (poll=True, temp_override로도 불가) |
| `fluid` (13) | `bake_all` `bake_data` `bake_mesh` `bake_particles` `bake_noise` `bake_guides` `free_all` `free_data` `free_mesh` `free_particles` `free_noise` `free_guides` `pause_bake` | `RuntimeError: Invalid domain` |
| `fluid` (1) | `preset_add` | `{'CANCELLED'}` (`context.fluid` 필요) |
| `paintcurve` (8) | `new` `add_point` `add_point_slide` `delete_point` `draw` `select` `cursor` `slide` | `poll()` False |
| `ptcache` (4) | `add` `remove` `bake_from_cache` (+`bake`/`free_bake` 단독) | `poll()` False |
| `rigidbody` (1) | `bake_to_keyframes` | `RuntimeError` (`keyframe_insert_by_name` 컨텍스트) |
| `cloth` (1) | `preset_add` | `{'CANCELLED'}` (`context.cloth` 필요) |
| `dpaint` (1) | `bake` | `RuntimeError` + `WARNING Baking canceled!` |
| `particle` (7) | `new_target` `target_move_up` `target_move_down` `target_remove` `dupliob_copy` `dupliob_move_up` `dupliob_move_down` `dupliob_remove` `dupliob_refresh` `connect_hair` | `{'CANCELLED'}` |
| `particle` (4) | `new` `copy_particle_systems` `unify_length` `shape_cut` `brush_edit` `select_linked_pick` | `poll()` False / `RuntimeError` |
| `object` (2) | `explode_refresh` `ocean_bake` | `{'CANCELLED'}` |

### 8.4 존재하지 않는 오퍼레이터 (`dir()` 에 없음 → ❌)

`object.softbody_add` `object.cloth_add` `object.fluid_add` `object.dupevoter_paint`
`object.rigidbody_add` `object.forcefield_add` `particle.particle_add`
`particle.edit_toggle` `particle.smooth` `particle.mute` `particle.clear`
`particle.duplicate` `ptcache.is_baking` `ptcache.filepath_get`
`ptcache.filepath_set` `ptcache.external_bake` `ptcache.bake_override`
`object.softbody_preset_add`

---

## 9. 함정 모음 (실제로 밟은 것만)

### 9.1 `hasattr(bpy.ops.x, name)` 은 **항상 True**

```python
hasattr(bpy.ops.object, "softbody_add")   # True  <-- 거짓말
"softbody_add" in dir(bpy.ops.object)    # False <-- 진실
hasattr(bpy.ops.object, "totally_bogus") # True  <-- 역시 거짓말
```

실제 호출하면 `AttributeError: Calling operator "bpy.ops.object.softbody_add"
error, could not be found` 가 난다. **`dir()` 만 쓸 것.**

### 9.2 `poll()` 이 True 라고 동작하는 게 아니다

| 오퍼레이터 | `poll()` | 실제 |
|---|---|---|
| `boid.state_add` | True | `{'CANCELLED'}` |
| `fluid.bake_all` | True | `RuntimeError` |
| `cloth.preset_add` | True | `{'CANCELLED'}` |
| `rigidbody.bake_to_keyframes` | True | `RuntimeError` |
| `ptcache.bake` | False | `temp_override` 로 True |

`poll()` 은 필요조건일 뿐이다. **항상 `{'FINISHED'}` 를 확인하라.**

### 9.3 조용히 실패하는 것들 (에러 없음, 효과 없음)

| 실수 | 증상 | 해결 |
|---|---|---|
| 프레임 점프 | 물리가 안 움직임 | 순차 `frame_set` 또는 bake (§1.1) |
| `ps.particles` 원본 읽기 | 항상 `[]` | `evaluated_get()` (§5.4) |
| `Particle.index` | `AttributeError` | `enumerate()` (§5.5) |
| `settings.vertex_group_mass` 오타 | 핀이 안 걸림 | 그룹 이름 echo (§3.5) |
| Collision `use_collision` | `AttributeError` | `settings.use = True` (§3.4) |
| bake 후 파라미터 변경 | 옛 결과 유지 | `free_bake_all()` (§7.3) |
| `.blend` 미저장 + 디스크 캐시 | `is_baked=True` 인데 파일 0 | 먼저 저장 (§7.2) |
| `render(animation=True)` | 전부 1프레임 | 사전 시뮬레이션 (§7.8) |
| `rigidbody_world.point_cache` 미설정 | 250프레임 bake | 범위 명시 (§1.3) |
| EMITTER + 파티클 편집 | 전부 `poll()` False | `type='HAIR'` (§5.8) |
| `softbody goal_min=2.0` | `1.0` 으로 clamp | 0..1 정규화 (§2.3) |
| fluid `domain_settings` | `None` | `fluid_type` 먼저 설정 (§6.2.1) |
| `canvas_settings` | `None` | `dpaint.type_toggle()` 먼저 (§6.3) |
| `bpy.types.RigidBodySettings` | 존재하지 않음 | `RigidBodyWorld` 직접 (§4.2) |
| `bpy.types.HairKey` | 존재하지 않음 | `ParticleHairKey` (§5.6) |
| `constraint_add(type='PIN')` | `TypeError` | `type='POINT'` (§4.4) |

### 9.4 메모리 / 리소스

* `evaluated_get(dg).to_mesh()` 결과는 **반드시 `to_mesh_clear()`**.
* 파티클 `count` 를 크게 잡으면 `point_cache.info` 의 KiB 수를 보고 예산을 정하라.
  (120 파티클 × 50 프레임 = 170 KiB)
* `bpy.context.preferences.system.memory_cache_limit` (기본 4096 MB) 넘으면 eviction.

### 9.5 컨텍스트 규칙

* 배경 모드에서 `bpy.context.area` / `bpy.context.region` 은 **항상 `None`**.
* `bpy.context.window` 과 `bpy.context.screen` 은 **존재한다** (background 에서도).
  그래도 `boid.*` 해결에는 안됐다.
* `bpy.ops.object.particle_system_add()` 는 `bpy.context.object` 에 붙는다.
  활성 오브젝트를 명시적으로 설정하라.
* `bpy.ops.mesh.primitive_*_add()` 도 새 오브젝트를 활성으로 만든다.
  인스턴스/이미터처럼 두 개를 다룬다면 순서 주의.

### 9.6 정확하지 않은 해석해

Bullet 과 Blender PT 솔버는 semi-implicit 적분 + 적응 서브스텝을 쓴다.
`z = z0 + v0·t − ½g·t²` 와 **정확히 맞지 않는다**:

* 리지드바디: 최대 오차 1.7 cm / 4 m 낙하 (0.4 %) — 자유낙하 구간
* 파티클 (RK4): 초기 4 mm, 20프레임 뒤 20 cm — 적응 타임스텝 때문
* 소프트바디: 강체 해석과 ~10 % 차이 (변형 흡수)

**회귀 테스트로 쓸 때는 해석해 대신 "기준값" 을 하드코딩하라.**

---

## 10. 빠른 참조 치트시트

```python
# ---------- 생성 ----------
m_cloth  = obj.modifiers.new("C", 'CLOTH')
m_sb     = obj.modifiers.new("S", 'SOFT_BODY')
m_fluid  = obj.modifiers.new("F", 'FLUID'); m_fluid.fluid_type = 'DOMAIN'
m_col    = floor.modifiers.new("X", 'COLLISION'); m_col.settings.use = True
m_dp     = obj.modifiers.new("D", 'DYNAMIC_PAINT')
bpy.ops.object.particle_system_add()            # 활성 오브젝트
ps = obj.particle_systems.new("MyParticles")   # 데이터 API
bpy.ops.rigidbody.world_add(); bpy.ops.rigidbody.object_add()
bpy.ops.rigidbody.constraint_add(type='POINT')

# ---------- 시뮬레이션 (순차 필수) ----------
for f in range(1, N+1):
    sc.frame_set(f)
# 또는
bpy.ops.ptcache.bake_all(bake=True)

# ---------- 읽기 ----------
dg = bpy.context.evaluated_depsgraph_get()
obj.evaluated_get(dg).matrix_world                    # 리지드바디
eo = obj.evaluated_get(dg); me = eo.to_mesh(); ...; eo.to_mesh_clear()   # 클로스/소프트바디
obj.evaluated_get(dg).particle_systems[0].particles   # 파티클 (원본 말고!)

# ---------- 결과 검증 ----------
print(mod.point_cache.info)      # '50 frames in memory (92 KiB).' / '6 frames on disk.'
print(len(eval_ps.particles))     # 0 이면 안 읽은 것

# ---------- 파라미터 바꿨으면 ----------
bpy.ops.ptcache.free_bake_all()

# ---------- 렌더 ----------
# 반드시 사전 시뮬레이션 후!
sc.frame_set(50)
bpy.ops.render.render(write_still=True)
```

---

## Verification log

모든 스크립트는 `/workspace/build/gap-sim/verify/` 에 있다.
실행 커맨드는 전부 동일:

```
blender -b --factory-startup -noaudio --python-exit-code 1 --python verify/NN_이름.py
```

| # | 스크립트 | 목적 | 결과 |
|---|---|---|---|
| 00 | `00_enumerate.py` | `dir(bpy.ops)` 전수 + sim 관련 `bpy.data`/`bpy.types` 존재 확인 | **PASS** — `bpy.data.fluids` 없음, `RigidBodySettings`/`HairKey`/`FluidModifierSettings` 없음 |
| 01 | `01_rna_dump.py` | RigidBody/Cloth/Collision RNA 전수 | **PASS** (1회 수정: `RigidBodyWorld.settings` 없음, `SoftBodyModifier.collision` 없음 반영) |
| 02 | `02_object_ops.py` | `hasattr(bpy.ops.*)` 거짓말 증명 | **PASS** — `object.softbody_add` 등 4개 제거 확인 |
| 03 | `03_rna2.py` | SoftBody/PointCache/EffectorWeights/Collision RNA | **PASS** (수정: `solver_result`·`canvas_settings` 이 `None` 이라 가드 추가) |
| 04 | `04_dpaint_fluid.py` | DynamicPaint + FluidDomain/Flow RNA 전수 | **PASS** — `dpaint.type_toggle()` 가 `canvas_settings` 를 할당함을 발견 |
| 05 | `05_rigidbody_e2e.py` | **핵심** 리지드바디 낙하 e2e, 제약, 키프레임 bake | **PASS** — `bake_to_keyframes` 크래시 발견, 수동 대체 코드 검증 |
| 05b | `05b_rb_debug.py` | depsgraph 리드백 (점프 vs 순차) | **PASS** — 순차면 점프도 안전함 확인 |
| 05c | `05c_rb_jump.py` | **프레임 점프가 물리를 안 진행시킴** 증명 (6개 테스트) | **PASS** — TEST2/3/4 전부 z=3.00000 고정 |
| 06 | `06_cloth_e2e.py` | 클로스 핀 그룹 + 순차 시뮬 + 평가 메시 | **PASS** — 핀 정점 `(-1,1,0)` 고정 확인 |
| 06b | `06b_collision.py` | `CollisionSettings` / `ClothCollisionSettings` 전수 | **PASS** — `use_collision` → `use` 변경 확인 |
| 07 | `07_diskcache.py` | 디스크 캐시 위치 추적 (1차) | **PASS** — 파일이 어디에도 안 생김 발견 |
| 07b | `07b_diskcache2.py` | 디스크 캐시 위치 (2차, .blend 저장 후) | **PASS** — `blendcache_<name>/` 확인 |
| 07c | `07c_diskcache3.py` | `filepath` 무시 증명 | **FAIL→수정→PASS** (캐시 인덱싱 오류 수정) |
| 07d | `07d_diskcache4.py` | `info` 문자열 / 재오픈 재사용 | **PASS** — `'6 frames in memory'` vs `'6 frames on disk'` |
| 07e | `07e_invalidate.py` | **파라미터 변경이 bake 를 무효화하지 않음** 증명 | **PASS** — mass 0.3→9.9 후 값 동일, free 후 변경 |
| 08 | `08_particle_table.py` | `ParticleSettings` 188 프로퍼티 전수 + enum | **PASS** — `type=['EMITTER','HAIR']`, `physics_type=['NO','NEWTON','KEYED','BOIDS','FLUID']` |
| 09 | `09_particle_e2e.py` | **핵심** 파티클 e2e + 결정성 + `cycles.seed` 무관성 | **PASS** — `A==B True`, `A==C False` |
| 09b | `09_particle_probe.py` | **원본 `ps.particles` 가 항상 비어 있음** 증명 | **PASS** — orig=0 / evaluated=10 |
| 10 | `10_hair.py` | HAIR 헤어 키 실측 (`ParticleHairKey`) | **PASS** — `|tip-root| = 0.60000` 정확 일치 |
| 11 | `11_boid.py` | Boid 시뮬 + `bpy.ops.boid.*` 전수 판정 | **PASS** — 8개 전부 `CANCELLED`, temp_override도 불가 |
| 11b | `11_boid_mball.py` | BoidState/BoidRule 구조 | **FAIL** → 11c 로 분리 |
| 11c | `11c_boid_types.py` | `BoidSettings`/`BoidState`/`BoidRule` 타입 전수 | **PASS** — `BoidRule.type` RO, `rules` 에 `.new()` 없음 |
| 12 | `12_mball_dpaint.py` | Metaball + DynamicPaint RNA/오퍼레이터 | **PASS** — mball 8개 EDIT 모드에서 `FINISHED` |
| 13 | `13_misc.py` | `cloth.preset_add` / fluid 셋업 | **PASS** — preset_add `CANCELLED`, fluid `Invalid domain` |
| 14 | `14_fluid_bake.py` | fluid bake 우회 시도 5종 | **PASS** (실패 확인) — 전부 `Invalid domain` |
| 14b | `14b_fluid_bake2.py` | fluid bake 경로 6종 | **PASS** (실패 확인) — 6/6 전부 실패 |
| 15 | `15_particle_edit.py` | 파티클 에디트 모드 진입 + 오퍼레이터 poll 행렬 | **PASS** — `particle_edit_toggle` `{'FINISHED'}` |
| 15b | `15b_particle_edit2.py` | 에디트 결과 실측 (subdivide/rekey/delete) | **PASS** — 키 5→9→8, 파티클 20→0→20 |
| 16 | `16_render_recipe.py` | **예제 3**: 3종 시뮬 + bake + 50프레임 렌더 | **PASS** — `render frame 50 took 0.87 s`, PNG 생성 |
| 17 | `17_render_control.py` | 4경로 비교 (무시뮬/순차/bake/anim) | **PASS** — A·D 가 1프레임 이미지, 해시 동일 |
| 18 | `18_anim_render.py` | `animation=True` 사전 시뮬 5경로 | **PASS** — T1 unique 1, T2~T5 unique 11/12 & 바이트 동일 |
| 19 | `19_path_effector_sb.py` | PATH target / effector 13종 / SB goal | **PASS** — `new_target` `CANCELLED`, effector 13/13 성공 |
| 20 | `20_verdict_matrix.py` | **판정 매트릭스** (신규 씬 1개 = 1 호출) | **PASS** — FINISHED 55 / CANCELLED 26 / EXC 33 |
| 21 | `21_particedit_poll.py` | **EMITTER vs HAIR** 파티클 편집 poll 비교 | **PASS** — EMITTER 전부 False, HAIR 전부 True |
| 22 | `22_gaps.py` | `modifier_add` 12종 / `ptcache.bake` override | **PASS** — 12/12 `FINISHED`, `temp_override`로 `ptcache.bake` 성공 |

### 정직하게 밝히지 못하는 것

| 항목 | 상태 |
|---|---|
| **Fluid/Mantaflow 시뮬레이션 결과** | ❌ **검증 실패.** 6가지 경로 전부 `RuntimeError: Invalid domain`. 도메인/플로우 설정(161+28 프로퍼티)과 프리셋 구조는 전수 덤프까지 완료했지만, 실제 시뮬 한 프레임도 못 만들었다. 캐시 디렉터리·해상도·벽시계 비용에 대한 수치는 **이 환경에서 측정 불가** |
| **`bpy.data.paint_curves.new()`** | ⚠ **미검증.** `paintcurve.*` 오퍼레이터가 전부 `poll()` False 여서 PaintCurve 데이터블록을 만들지 못했다. 컬렉션 자체의 존재(§6.3)와 빈 상태는 확인 |
| **`bpy.ops.rigidbody.bake_to_keyframes` 의 수동 대체** | ✅ 검증 완료 (360 키프레임). 단 키프레임 삽입 **후** depsgraph 를 읽으면 stale 값(f=30) 이 나온다는 관찰만 남았고, 재로드로 복구되는지는 미검증 |
| **`PointCache.frame_step`** | ⚠ **효과 없음** — `frame_step=2` 로 bake 해도 파일 수·결과가 동일. 의미를 확인 못 함 |
| **메타볼 `mball.*` 의 temp_override 경로** | ❌ 미시도. EDIT 모드 경로로만 검증. `temp_override` 로도 될 수 있으나 확인 안 함 |
| **Fluid `free_*` 의 "정상 동작 시" 의미** | ❌ 미검증 — bake 자체가 안 되니 free 도 항상 `Invalid domain` |
| **소프트바디 `collision_collection` 기반 충돌** | ⚠ 미검증 — `SoftBodyModifier.collision` 이 제거된 뒤 남은 경로의 실제 동작을 확인하지 않음 |
| **파티클 `physics_type='FLUID'` (SPH)** | ⚠ 미검증 — `settings.fluid` (`SPHFluidSettings`) 존재만 확인, 시뮬은 돌리지 않음 |
| **`physics_type='KEYED`** | ⚠ 미검증 — enum 에 존재만 확인 |

### 오퍼레이터 판정 통계 (문서에 기재한 전수)

| 판정 | 개수 |
|---|---|
| ✅ 헤드리스 OK (실제 `{'FINISHED'}`) | **51** |
| ⚠ 컨텍스트 필요 (추가 준비로 해결) | **12** |
| ❌ UI 전용 / `CANCELLED` / `RuntimeError` | **47** |
| ❌ `dir()` 에 없음 (5.2 에서 제거) | **17** |
| **합계** | **127** |

# 16. 실전 검증 (Field Test) — 서브에이전트가 스킬만 보고 만든 결과

> 이 문서는 **스킬의 품질을 외부 검증한 기록**이다.
> 방법: 6명의 서브에이전트에게 **스킬 파일만 주고** 실제 블렌더 작업을 시켰다.
> 스킬 밖 지식을 쓰지 말라고 했고, 못 찾으면 **스킬에 없다고 보고하라** 고 명시했다.
> 목표는 "스킬이 잘 짜였으면 퀄리티가 높게 나온다" 의 실증이었다.

---

## 0. 테스트 설계

| 항목 | 내용 |
|---|---|
| 대상 | `/workspace/skiltest/skill/` (SKILL.md + references 15 + scripts + templates) |
| 작업 수 | 6종 (모델링·리깅·애니메이션 / 이미지 보정 / GN / 영상편집 / 시뮬레이션 / 텍스처링·내보내기) |
| 환경 | Blender 5.2.2 LTS, **GPU 없음**, 2코어, 3GB RAM |
| 규칙 | 스킬만 참고 · 실패해도 서브폴더에 산출물 남길 것 · **막힌 지점 정직 보고** |
| 판정 | 각 작업이 **자기 영역의 물리적 증거**(수치·픽셀·파일)를 냈는가 |

**태스크 브리프**는 요구사항과 "이 수치를 내라"는 판정 기준만 줬다.
**방법은 전부 서브에이전트에게 맡겼다.**

---

## 1. 결과 요약 — 6/6 성공

| # | 작업 | 결과 | 핵심 증거 |
|---|---|---|---|
| T1 | 모델링 + 리깅 + 애니메이션 | ✅ 성공 | 4부품 프로시저럴 크레인, 3뼈 체인, 60프레임 mp4 (h264 640×480) |
| T2 | 컴포지터 이미지 보정 | ✅ 성공 | 9단계 누적 ablation, **픽셀 82.2% 변화** / OFF 는 0.000000 |
| T3 | 지오메트리 노드 | ✅ 성공 | **`verts = 8.000000 × Count + 0.000000`** (선형 회귀, 절편 0) |
| T4 | VSE 영상 편집 | ✅ 성공 | mp4 60프레임, ON/OFF **758,311 샘플 차이** |
| T5 | 물리 시뮬레이션 | ✅ 성공 | **자유낙하 이론값 대비 최대 5.3 mm 오차** |
| T6 | 텍스처링 + 내보내기 | ✅ 성공 | 5포맷 라운드트립, 재질 3종 색 거리 **0.2991** |

### 1.1 산출물 (직접 확인함)

| 산출물 | 확인 |
|---|---|
| T1 크레인 3점 렌더 | 리깅이 실제로 움직임 (f60 접힘 / f120 신전) ✅ |
| T2 마케팅 배너 | CJK 텍스트 + 블룸 + 비네트 + 색보정 모두 살아있음 ✅ |
| T4 `T4_vse_edit.mp4` | `ffprobe` → h264 / 320×240 / **nb_frames=60** / 2.5s ✅ |
| T5 f90 렌더 | 상자 무너짐 + 파티클 낙하 + 천 처짐 ✅ |
| T6 3재질 렌더 | 금속/대리석/플라스틱 **눈에 띄게 다름** ✅ |

---

## 2. ⭐ 테스트가 실제로 찾아낸 스킬 결함 — 모두 수정 완료

이게 이 테스트의 진짜 목적이었다. **6명 전원이 버그를 찾아냈다.**

### 2.1 코드 버그 5건 (bk.py / bkkit) — 전부 고치고 재검증함

| # | 버그 | 증상 | 조치 |
|---|---|---|---|
| 1 | `bk.py api op` | **모든 오퍼레이터에서 100% 크래시**<br>`TypeError: getattr expected at least 2 arguments` | `getattr(bpy.ops, grp), name` 으로 수정 |
| 2 | `introspect.prop_info` | ENUM 조회 시 크래시<br>`'EnumProperty' object has no attribute 'array_length'` | `getattr(p,"array_length",0)` + `is_flag_enum` 추가 |
| 3 | `introspect.op_check` | **정상 인자를 거부**<br>`object_types={'EMPTY','MESH'}` → "not one of [...]" | 플래그 ENUM 분기 추가 |
| 4 | `introspect.op_exists` docstring | "glTF는 확장이라 기본 비활성" 이라고 단정 — **틀림** | docstring 정정 |
| 5 | `bk.py api prop` 에러 경로 | 존재하지 않는 `introspect.rna_props` 호출 | `compat.rna_props` 로 수정 |

> ### 왜 1번이 가장 심각했나
>
> `SKILL.md` §3 은 이걸 **"에이전트 작업 규칙"** 으로 지시한다:
> *"bpy.ops 인자를 추측하지 마라. 먼저 `api op` 으로 실제 시그니처를 확인하고 써라."*
>
> **그 수단이 고장나 있었다.** 문서대로 하려던 2명(T1·T5)이 우회 스크립트를 직접 짜야 했다.
> 지시된 도구가 죽어 있으면 지시를 못 따르는 거고, 그건 문서 문제가 아니라
> **스킬이 자기 규칙을 실행하지 못하는 상태** 였다.

#### 플래그 ENUM 버그의 근본 (재현 로그)

```python
# frag  (아래는 재현용 출력이다 — 실행하면 /tmp 에 파일을 쓰므로 검증기에서 건너뛴다)
import bpy
# ENUM 프로퍼티에는 array_length 가 없다. is_enum_flag 가 있다.
p = {x.identifier: x for x in bpy.ops.export_scene.fbx.get_rna_type().properties}["object_types"]
p.is_enum_flag        # True
p.array_length        # AttributeError
```

**실측 출력**
```
True
AttributeError: 'EnumProperty' object has no attribute 'array_length'
```

```python
# frag  (파일 기록이 포함된다)
bpy.ops.export_scene.fbx(filepath="/tmp/_p.fbx", object_types={"EMPTY","MESH"})
# {'FINISHED'}                     ← set 이 정답
bpy.ops.export_scene.fbx(filepath="/tmp/_p2.fbx", object_types=("EMPTY","MESH"))
# TypeError: object_types expected a set, not a tuple
```

수정 후:
```
BUG1 op_exists('export_scene.gltf'): True
BUG1 op_check gltf: True
BUG2 flag enum set : True []
     tuple 거절    : False | 'flag enum needs a set, not a tuple...'
     없는 멤버 거절: False | 'unknown flag member(s) ...'
BUG2 prop_info enum: {'type':'ENUM', 'is_flag_enum': True, 'enum': [...]}   ← 크래시 안 함
```

### 2.2 문서 오류 4건 (전부 수정)

| # | 잘못된 문서 | 실제 (5.2.2 실측) |
|---|---|---|
| 1 | `ng.interface.new_socket()` 의 `name=` **키워드는 불가** | **키워드로도 동작한다.** 위치 인자와 동일. 4.x 스타일 `new_socket(bl_idname, name=…)` 만 `TypeError` |
| 2 | `shade_smooth_by_angle` 가 `Smooth by Angle` **GN 모디파이어를 스택에 추가** | **추가하지 않는다.** 실측 스택 = `[]`. `sharp_edge` 속성만 직접 쓴다 |
| 3 | 포즈는 `pb.evaluated_get(dg).matrix` 로 읽는다 | **`PoseBone` 에 `evaluated_get` 이 없다.** `AttributeError`. `frame_set()` 이 평가를 수행하므로 `pb.matrix` 가 이미 평가값 |
| 4 | `parent_set(ARMATURE_AUTO)` 은 **headless 에서 무동작** | **동작한다.** 정점그룹 가중치 0.09~0.95 실측 생성, 실제 변형 발생 |

#### 2번이 특히 위험했던 이유

T6 은 이 거짓말 때문에 **다른 경로를 택했다**:
> "`shade_smooth_by_angle` 가 GN 모디파이어를 스택에 남긴다는 §3.4 덕에,
> 내보내기 폴리곤 수가 깨지는 걸 사전에 피하고 순수 데이터 경로를 씀."

즉 **틀린 문서가 "더 안전한 우회" 를 유도했다.** 우회가 결과적으로 맞았지만
틀린 이유로 고른 것이라, 나중에 이 문서를 믿는 사람이 같은 함정을 다시 밟을 수 있다.

#### 4번이 특히 위험했던 이유

T1 은 "문서대로 하면 ARMATURE_AUTO 가 안 된다" 고 믿고 **수동 가중치를 먼저 시도**했다.
그리고 실제 원인은 **"bone heat 는 메시-뼈 거리가 멀면 가중치가 0 이 된다"** 였다.
즉 **틀린 진단이 우회로를 만들었고, 우회로는 또 다른 이유(뼈 거리) 때문에 실패했다.**

정정 문서에 진단 규칙을 넣었다 (`04-scene-animation-io.md` §7.6):

```python
# frag  (obj 는 리깅된 오브젝트여야 하므로 단독 실행 불가)
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
total = sum(v.weight for g in obj.vertex_groups for v in g.vertices)
print("가중치 합:", total, "-> 0 이면 bone heat 거리 문제 (오퍼레이터 실패 아님)")
```

### 2.3 🔴 재현에 실패한 보고 — 그대로 남긴다

T3 이 이렇게 보고했다:

> "**`bpy.context.view_layer.update()` 만으로는 GN 모디파이퍼 입력값 변경 후 재평가되지 않는다.**
> `obj.update_tag()` 가 추가로 필요하다. 7가지 전략 비교 결과 view_layer.update() 만은 `[0,0,0,0]` 이었다."

**나는 이걸 재현하지 못했다.** 같은 노드 그래프를 새로 짜서 6가지 전략을 비교한 결과:

```
=== depsgraph 재무효화 전략 (Count=0/5/200/5000) ===
  PASS  (A) view_layer.update() 만   [문서 §10.1 지시]    [0, 40, 1600, 40000]
  PASS  (B) 아무것도 안 함                                 [0, 40, 1600, 40000]
  PASS  (C) obj.update_tag() + view_layer.update()         [0, 40, 1600, 40000]
  PASS  (D) mod.id_data.update_tag() + view_layer.update() [0, 40, 1600, 40000]
  PASS  (E) ng.interface_update(ctx) + view_layer.update() [0, 40, 1600, 40000]
  PASS  (F) scene.frame_set(2)                             [0, 40, 1600, 40000]
```

**단일 세션 안에서는 아무것도 안 해도 재평가된다.** 정점 수는 정확히 `8 × Count` 다.

> ### 판단
>
> T3 의 주장을 문서에 **"중요한 사실" 로 넣지 않았다.**
> 재현에 실패한 주장을 사실로 기록하면 그게 또 다른 거짓말이 된다.
>
> 다만 T3 의 실측 자체(`verts = 8 × Count` 완전 선형)는 재현했고,
> 그게 그 작업의 진짜 판정 기준이니까 **T3 는 성공**이다.
> depsgraph 주장은 `[0,0,0,0]` 이 나온 그 시점의 상태(대부분은
> `read_factory_settings()` 직후 뼈대 참조가 끊긴 상태)에 대한 것으로 보인다.
>
> **이건 테스트 설계의 한계다** — 서브에이전트마다 스코프가 달라
> 같은 주장을 독립 재현하기 어렵다. 더 강하게 하려면
> 각 보고 주장을 **검증 전용 스크립트로 만들어 재실행**하는 단계를 넣어야 한다.
> 그건 다음 판의 과제다.

---

## 3. 스킬이 부족해서 남긴 것 (수정 안 함 — 목록으로만)

T6 이 아무것도 못 찾지 못했으면 이 테스트는 실패였을 것이다.
**최고 난이도에서 발견된 진짜 구멍**을 그대로 옮긴다.

### 3.1 내보내기 (T6)

1. **프로시저럴 머티리얼은 내보내면 무조건 죽는다.** 폴리곤·UV·머티리얼 개수는 "정상"인데
   노드 트리가 2~3개로 무너진다. 스킬 전체를 grep해도 0건.
2. **더 나쁜 것 — 링크로 물린 소켓은 `default_value` 로 방출된다.**
   glTF 에 `baseColorFactor` 키 자체가 없어서 **"전부 같은 회색" 시나리오가 조용히 재현**된다.
   경고도 `CANCELLED` 도 없다. → `11-troubleshooting.md` 의 "조용한 실패" 목록에 추가해야 함
3. 포맷별 폴리곤 보존 규칙 표가 없다 (glTF는 무조건 삼각화, 나머지는 n-gon 보존).
4. `margin_method` 의 의미(SCALED/ADD/FRACTION)가 없다.

### 3.2 VSE (T4)

5. `TextStrip.location` 은 **픽셀이 아니라 정규화 0~1**. `location=(24, 200)` 이면 화면 밖(7680px)이다.
6. `blend_type='REPLACE'` 기본값이 **텍스트 스트립에서 프레임 전체를 검정으로 덮는다**
   (평균 0.0003 vs ALPHA_OVER 0.0375).
7. **스트립 키프레임은 어디에도 안 있다.** `strip.animation_data` 도 없고
   `strip.evaluated_get()` 도 없다. 실제로는 **Scene 액션**에 저장된다.
8. `content_trim_start` 는 "소스 오프셋" 이 아니라 **스트립을 민다**(딜레이트).

### 3.3 시뮬레이션 (T5)

9. **5.2 에서 파티클↔월드 충돌이 아예 불가.** `use_collision` · `friction_factor` 가 없다.
   파티클이 리지드바디 바닥을 그대로 통과한다(f30 z=3.40 → f40 z=-1.94).
10. **`distribution='GRID'` 는 `count` 를 무시하고 항상 100개.** 500·1000 요청해도 100개.
11. **클로스 정점의 world 좌표 변환이 문서에 없다.** `me.vertices[i].co` 는 **로컬 좌표**다.
    오브젝트가 이동/회전된 씬에서 그대로 읽으면 잘못된 숫자가 나온다.

### 3.4 컴포지터 (T2)

12. **컴포지터는 libEGL 이 없으면 헤드리스에서 프로세스째 죽는다.**
    트레이스백도 종료코드도 없이 죽고 **버퍼링된 stdout 전부 유실**된다.
    5분짜리 렌더 1회가 통째로 날아간다.
    SKILL.md 의 `apt-get install libegl1` 은 "EEVEE 용" 으로만 적혀 있다. → **하드 전제조건**이다.
13. **`CompositorNodeCurveRGB` 점 추가 API** 가 없다. `node.mapping.curves[3].points.new(x,y)`.
14. **컴포지터 텍스트 레시피** 가 없다. `CompositorNodeStringToImage` + `ShaderNodeMix(Factor)`.
15. `CompositorNodeColorCorrection` 의 `Master Contrast` 가 **0.5 피벗 연산**이라
    1.06 하나로 0.02짜리 배경이 음수가 되어 **프레임 전체가 검게 죽는다**.
16. `CompositorNodeBlur` 의 `Extend Bounds=True` 가 **마스크를 프레임 가장자리 Value(1.0) 로 채운다.**
    EllipseMask 유래 비네트가 완전히 상쇄된다.
17. **Glare 의 `Image` 출력은 "원본+글로어" 가 아니다.** Strength=0 으로 해도 원본이 아닌 값이 나온다.

### 3.5 기타 (T3 · T1)

18. `bpy.app.timers` 도 `bpy.msgbus` 도 `-b` 에서 발화 안 한다 (기존 문서에 있음, 재확인).
19. 카메라 프레이밍 계산법(`2·d·(sensor/2)/lens`)이 없다. "물러나라" 는 지시만 있고 계산법이 없다.
20. `read_factory_settings(use_empty=True)` 가 **이미 만든 데이터블록도 지운다.**
    리셋 전에 만든 머티리얼 참조가 `ReferenceError` 로 죽는다.
21. GN 트리에 삽입 가능한 노드 타입 allowlist 가 없다 (카탈로그로 역추적해야 함).
22. 렌더 시간 예측 정보가 없다. 문서는 "320×240@48spp ≈ 17초" 인데
    실제론 640×480@48spp 가 프레임당 53~364초(경합에 따라)였다.
23. `imagecheck` 에 **리전(구역) 통계** 가 없다. 비네트/글로어를 수치로 증명하려면 4×4 구역 평균이 필요하다.
    T2 와 T4 가 **둘 다** 이걸 직접 짰다.

### 3.6 이 목록이 주는 결론

> **22개 중 12개는 "조용히 실패한다" 는 유형이다.** 경고도 예외도 없고
> 결과물만 잘못 나온다. 이게 문서로 막아야 하는 1순위 유형이고,
> 현재 스킬은 이 유형에 충분히 방어하지 못했다.
>
> **특히 12번(컴포지터+EGL)은 치명적이다** — 5분짜리 렌더가 통째로 사라진다.

---

## 4. 테스트가 평가한 스킬의 실제 강점

버그만 나열하면 불공형하다. **스킬이 실제로 기여한 것**도 기록한다.

| 항목 | 근거 |
|---|---|
| **5.x 파괴적 변경 정확도** | T2·T3·T4 가 `compositing_node_group` / GN RNA / `strips` 를 **첫 시도에서** 통과. T4 는 "5.x 함정을 문서 그대로 명중" 하고 B8.1 리네임 표 16개를 전부 실측 재확인 |
| **폴백이 실제로 작동함** | T4 는 B10.4 때문에 `bpy.ops.sequencer.*` 를 아예 안 건드려 **헤드리스 poll 실패·세그폴트 0회** |
| **검증 도구가 실제로 씌워짐** | 6명 전원이 `scenecheck` + `imagecheck` 를 썼고, **모든 작업이 "픽셀로 증명"** 을 해냈고, "렌더 성공" 만으로는 보고하지 않음 |
| **카탈로그가 예상을 앞둠** | T3 는 "probe 스크립트 6개를 짰지만 카탈로그에 필요한 노드가 전부 있어서 **예상 노드는 전부 문서로 확인 가능**" 하고 보고 |
| **물리 정합성 검증** | T5 는 §4.5 의 0.4% 오차 기준을 빌려 **자유낙하 이론값과 5.3mm 대조** 체계를 스스로 짬 |
| **시뮬레이션 순차 규칙** | T5 는 "§1.1 이 이번 작업의 성패를 갈랐다. 점프 금지 원칙 덕에 첫 시도에서 성공" 하고 보고 |
| **절차적 성격 유지** | T5 는 수직 천 시도가 0.6mm 만에 실패하자 **문서에 있는 수평+핀 구조**로 바꿔 2.67m Sag 를 얻음. 즉 **문서가 실제 해법이었다** |

---

## 5. 점수

| 항목 | 점수 | 근거 |
|---|---:|---|
| **산출물 퀄리티** | **9 / 10** | 6/6 성공. T2 배너·T6 재질·T1 크레인·T5 스택은 실제로 쓸 만한 수준 |
| **5.x API 정확도** | **8 / 10** | GN·컴포지터·VSE 정확. 단 GN depsgraph 주장 1건은 재현 실패 |
| **물리/수치 정합성** | **9 / 10** | T5 가 5.3mm 오차, T3 가 완전 선형 회귀까지 스스로 해냄 |
| **도구 자체 신뢰성** | **6 / 10** | `bk.py api op` 이 죽고 있었다. **지시된 도구가 고장난 상태** |
| **조용한 실패 방어** | **4 / 10** | 22개 결함 중 **12개가 조용한 실패 유형**. 방어 장치가 문서 산문에만 있음 |
| **총합** | **7.2 / 10** | |

### 5.1 결론

> **"잘 짜였다면 퀄리티 높게 나올 거" 라는 가설은 성립했다.**
> 6개 모두 손으로 만지는 정성 작업이 아니라 **에이전트가 처음부터 끝까지 혼자** 한 결과물이
> 모범적 수준이었다. 특히 T5 의 물리 검증과 T2 의 ablation 설계는 사람이 짰어도
> 이렇게 안 한다.
>
> **그러나 문서화되지 않은 구멍이 22개 있었다.** 그 중 9개는 지금 즉시 고칠 수 있는
> 코드/문서 버그였고(전부 수정 완료), 13개는 산문 추가로 닫아야 한다.
>
> **가장 큰 구조적 약점**: "조용히 실패하는" 시나리오에 대한 방어가
> 문서에 흩어져 있을 뿐 **체계적으로 묶여 있지 않다.**
> `11-troubleshooting.md` 에 "조용한 실패 20선" 같은 중앙 목록이 있어야 한다.

---

## 6. 다음 판에서 할 것

1. **보고 주장을 검증 스크립트로 강제.** 서브에이전트가 "X 가 Y 다" 고 보고하면
   그대로 재실행해 확인하고, 재현 안 되면 "미확인" 으로 표시한다.
2. **`11-troubleshooting.md` 에 "조용한 실패 중앙 목록" 추가.** 위 §3 의 12개 유형.
3. **컴포지터 전제조건(EGL)을 SKILL.md §2 의 필수 항목으로 승격.**
4. **내보내기 노드 손실 경고 문서화** (가장 조용하고 가장 파괴적인 실패 유형).
5. **`imagecheck` 에 리전 통계 추가** — 비네트/글로어/분리 검증이 표준화된다.
6. **GPU 없이 못 본 것 재실행** — GPU 머신에서 `14-gpu-rendering.md` 검증.

---

## 2026-10 GPU/렌더링 속도 강화 — 실측 결과

### 왜 다시 열었나

`16-field-test.md` 원래 총평은 **7.2 / 10** 이었고, 그 원인이 여기 있었다:

> **"GPU 가 없다" 고 가정하고 짜여진 스킬.** GPU 파이프라인이 필요 없다는 전제.

그래서 이 스킬은 **GPU 없는 머신에서** 썼고, GPU 관련 코드는 5년 된 가정 위에
서 있었다. GPU 6 NVIDIA + 2 AMD 머신에서 돌려보니 **코드 3개가 실제로 죽었다.**

### 버그 1 — `enable_gpu()` 가 세그폴트 (exit 139)

```python
# frag  (버그 재현 발췌. prefs 는 앞선 블록에서 온다고 가정)
prefs.refresh_devices()                      # ← 먼저
out["num_gpu"] = prefs.get_num_gpu_devices() # AttributeError
bpy.ops.render.render()                      # SIGSEGV
```
```
AttributeError: 'CyclesPreferences' object has no attribute 'compute_device_type'
exit=139
```

원인은 순서였다. `gpu_report()` 가 `refresh_devices()` 를 먼저 불렀고,
그 함수가 5개 백엔드를 전부 재질의해 preferences RNA 를 반쯤 만든다.
`try/except` 가 예외를 삼켜 **`활성 GPU 수: 0`** 이라고 잘못 보고했다
(실제론 6대 감지). 렌더 시 segfault.

→ **순서 고정**: `compute_device_type` 먼저 → `refresh_devices()` → 조회.
bisect로 최소 재현 확인 (`b4.py` 실패 / `b5.py` 성공).

### 버그 2 — 무차별 GPU 활성화 → OOM

`refresh_devices()` 가 CUDA/OPTIX/**HIP까지** 전부 `use=True` 로 채운다.
이 머신에서 GPU 0/1/2 는 MicroMixer 가 100% 점유 중이었다.

```
active: [4070, 4060 Ti, 4060 Ti, 3070, 3060 Ti, 5060 Ti]  num_gpu=6
RuntimeError: Error: System is out of GPU memory
```

**빈 카드가 3장 더 있었는데도 죽었다.** 그리고 `bk doctor` 는
`활성 GPU 수: 6` 이라고 했다 — **그 신호가 거짓말이었다.**

→ Cycles device id (`..._0000:82:00_OptiX`) 의 PCI bus id 를 `nvidia-smi` 에
매칭해 **여유 VRAM 2 GB 미만 카드 제외**. 실측으로 3장 정확히 걸러지고 렌더 성공.

### 버그 3 — "GPU 2장 쓰면 빠르다" 는 상식의 함정

960×720 · 64 spp · SUBSURF 구 30개 + AREA 라이트 6개 · OptiX 디노이즈 ON:

| 구성 | 시간 |
|---|---:|
| CPU (80코어 Xeon E5-2673 v4) | 5.69 s |
| **GPU 1장 (RTX 4070)** | **4.51 s** |
| GPU 2장 | 5.26 s |
| GPU 3장 | 6.17 s |
| GPU 6장 | *out of GPU memory* |

NVLink 없음 → PCIe 동기화 비용 > 추가 연산량. **카드가 늘수록 느려진다.**

→ `enable_gpu(max_devices=1)` 이 기본값. 여러 장은 **VRAM 이 벽일 때만**.

### 속도 레버 실측 (GPU 1장)

| 설정 | 시간 | 델타 |
|---|---:|---:|
| 디노이즈 ON (기본) | 5.61 s | 기준 |
| **디노이즈 OFF** | **4.20 s** | **−25%** |
| 디노이즈 ON (CPU) | 5.52 s | −2% |
| `tile_size` 512→2048 | 5.35 s | −5% |
| `use_persistent_data` | 5.31 s | −5% |

→ `gpu_speed_preset(scene, quality="fast")` 추가. 반복 렌더는 디노이즈 off.

### 코드 변경

| 파일 | 변경 |
|---|---|
| `scripts/bkkit/compat.py` | `gpu_inventory()`, `_bus_id_from_device_id()`, `gpu_host_usage()`, `gpu_report()` 재작성, `enable_gpu()` 재작성(+`max_devices`/`min_free_vram_mb`/`verbose`), `gpu_speed_preset()` 추가, `MIN_FREE_VRAM_MB` |
| `scripts/bk.py` | `doctor` 에 GPU별 여유 VRAM/util 표 + "선택할 것" 예측 추가 |
| `templates/scene_builder_template.py` | GPU 자동 폴백, `--cpu` / `--quality` / `--gpu-count` 플래그 |
| `references/14-gpu-rendering.md` | §1.5~1.10 신규 (세그폴트/OOM/스케일링/속도레버), §6.1 순서 경고, §12 검증현황, vlog 2세대 |
| `references/09-verification-loop.md` | 단계 3 GPU 정책 + "렌더 시간 측정 필수" |
| `references/11-troubleshooting.md` | §2.9.3~2.9.6 GPU 항목 4개 |
| `SKILL.md` | §0 요약 7번 추가, §6.5 전면 재작성, §7 검증현황 갱신 |

### 재현 검증 (수정 후)

```
[T3] enable_gpu ok = True gpus = 1 denoiser = OPTIX
[T3] RENDER OK {'FINISHED'} 4.88s          ← 이전엔 exit 139 또는 OOM
```

```
[GPU 사용] 1장: NVIDIA GeForce RTX 4070 denoiser=OPTIX    (템플릿)
  mean luma 0.344450 / 씬 검증 ok (errors=0 warnings=0) / 이미지 판정 ok
```

### 남은 정직한 구멍

- ~~HIP 실제 렌더 미검증~~ — **실측 완료.** ❓ 아님 (ROCm 있음, 3.85 s).
  단, **AMD 카드 → 카드 1:1 매칭은 여전히 안 된다** (`rocm-smi` 에 버스 ID 없음).
  AMD 카드가 점유 중일 때 자동 배제되지 않으므로 `bk doctor` 표를 눈으로 봐야 한다.
- oneAPI / Metal 미검증 (하드웨어 없음).
- **CUDA 백엔드 미측정** (OptiX 만 실측).
- **고품질(256spp+) `use_light_tree`** — 64spp 에서 무효과였으나 고품질은 미측정.
- **클라우드 GPU** — 이 머신은 로컬 NVMe/NVIDIA. AWS/GPC 는 PCIe 가 다르다.
- **실제 VRAM 스필 시간 페널티** — 5.2 에서 스필이 재현 안 돼서 측정 불가.
- **성능 수치는 이 머신 + 이 씬 한정.** 절대 스케일로 옮기지 말 것.

## 2026-10 렌더 속도 최적화 + 환경 기준선 — 실측 결과

### 왜 열었나

GPU 강화 뒤 남은 질문이 둘이었다:

1. **다른 머신에서 이 스킬을 돌리면 시간이 얼마나 다를까?** (문서에 절대 숫자만 있었다)
2. **GPU 를 써도 셰이더 옵션에 따라 렌더 시간이 천차만별하다**는데, 실제로 무엇이 얼마나 빠른가?

둘 다 실측 없이 답할 수 없었다. 그래서 측정했다.

### 추가 스크립트

| 파일 | 하는 일 |
|---|---|
| `scripts/bk_env.py` | 환경 지문 + 정규화 기준점 (`--bench`) |
| `references/17-environment-baseline.md` | 다른 머신에서 시간 추정하는 방법 |
| `references/18-render-optimization.md` | 렌더 속도 최적화 (전부 실측) |

### 핵심 발견

**1. 영상 렌더에서 `use_persistent_data` 가 2배 차이 (과소평가된 설정)**

| 8프레임 | 시간 | 프레임당 |
|---|---:|---:|
| 기본값 `False` | 8.25 s | 1.03 s |
| **`True`** | **4.15 s** | **0.52 s** |

**기본값이 False** 라서 아무도 안 켠다. 카메라가 움직이는 영상에서
BVH 재구성에 프레임당 0.5 s 가 사라진다.

**2. GPU 1장이 최적 — 반사 씬에서 격렬해진다**

| 구성 | 4K 텍스처 씬 |
|---|---:|
| GPU 1장 | 1.65 s |
| GPU 3장 | 4.48 s (**2.7배 느림**) |

반사/굴절이 GPU 간 데이터 의존을 강하게 만들어 PCIe 가 병목이 된다.

**3. 디노이즈 25% — 반복 렌더에서 가장 싼 절감**

GPU 1장, 960×720, 64spp: ON 5.61 s → **OFF 4.20 s**

**4. `texture_limit`, `max_bounces` 는 효과가 없었다 (그리고 역효과)**

| 설정 | 시간 | 델타 |
|---|---:|---:|
| `max_bounces` 16 | 4.56 s | **−8%** (늘리는 게 빠름) |
| `texture_limit` 4096 | 1.50 s | +15% (역효과) |

**둘 다 측정 편차 안에 들거나 역효과다.** 만지지 말 것.

**5. 첫 렌더는 항상 느리다 — GPU 가 더 심하다**

```
GPU 씬: first=4.74 s  warm=3.82 s  →  +24%
CPU 씬: first=5.57 s  warm=4.98 s  →  +12%
```

GPU 커널 JIT (PTX→SASS) 비용. 반복 렌더는 **한 프로세스에서** 돌려서 1회만 냈다.

**6. 같은 설정으로 재도 편차 27%**

```
times=['4.55', '3.57', '3.58', '3.61', '3.61']  median=3.61 s  spread=27.1%
```

이 머신 load(1m) 15~27. 이 편차가 **이 문서 전체의 신뢰도 상한**이다.

### 정규화 기준점

`bk_env.py --bench` (320×320, 64spp, GPU 1장):

```
Bench : cold 1.23 s  warm 0.68 s
```

다른 머신에서 이 값의 배율만 확인하면
GPU 1장 렌더 시간 = 4.51 s × (내 warm / 0.68) 으로 추정된다.

### 3세대 (2026-10 후속) — 커버리지 공백 스캔

"GPU 가속으로 렌더를 빠르게 하는 모든 축이 다뤄졌는가" 를 스캔해서
빈 축을 찾아 측정한 결과. **새로 실측한 것:**

| 축 | 결과 |
|---|---|
| **SUBSURF `render_levels`** | 5→1: 30M→119K 정점, **17.46→6.24 s (−64%)** |
| **Decimate COLLAPSE** | **역효과 — 3.26→11.03 s (3.4배 느림).** 정점 ↓ 시간 ↑↑ |
| **Decimate UNSUBDIV** | **2.42 s — 가장 빠름 (COLLAPSE 대비 4.6배).** 이걸 써야 한다 |
| `use_light_tree` (30조명, 64spp) | **무효과** (0.94 vs 0.90 s) |
| `denoising_quality` F/B/H | **무효과** (0.81/0.80/0.82 s) |
| 모션블러 ON | +8% (저렴) |
| 출력 포맷 PNG/JPEG/EXR | **무효과** (0.84~0.92 s). 파일 크기가 관건 |
| EXR `color_depth` | **'16'/'32' 만** — `'8'` 은 TypeError |
| **Path Guiding GPU 무지원** | **실증** — GPU 무변화(+3%), CPU 는 +56% 느려짐 |
| `kernel_optimization_level` | **차이 없음** (0.87/0.87/0.92 s). prefs 속성 |
| **CPU vs GPU 픽셀 차이** | **691,200 px 중 2개만 상이**, Δmean_luma=0.000000 |
| VRAM 스필 경계 | 3,250만 정점 + 4K + texture_limit=512 → **스필 미발생** |

이 중 **Decimate COLLAPSE 역효과**와 **Path Guiding 실증**,
**kernel_optimization_level 위치 오류** 는 문서에 없던 발견이다.

> **Decimate COLLAPSE 역효과가 이 스캔에서 가장 값진 발견이었다.**
> "정점 줄이면 빨라진다" 는 당연한 기대를 정면으로 뒤집는다.
> COLLAPSE 는 삼각형을 재구성해서 BVH 를 비싸게 만들고, 그 비용이
> 정점 감소분보다 훨씬 크다. UNSUBDIV 가 맞다.

### 4세대 (2026-10) — 2K 60fps 실전 렌더 검증

사용자 요청으로 **실제 1920×1080 / 60fps 영상**을 만들어 최적화 수치를 검증했다.
씬: 절차적 셰이더 바닥 + 금속/디퓨즈 구 24개 (SUBSURF 3) + AREA 6 + SUN +
카메라 dolly·pan, 구들 상승/하강 애니메이션.

#### 60프레임 실측

| 설정 | 총 시간 | 프레임당 |
|---|---:|---:|
| 최종 (persistent + denoise, 64spp) | **160.80 s** | 2.680 s |
| 탐색 (persistent, denoise OFF, 16spp) | **70.46 s** | 1.174 s |

#### 960×720 과 비교 — 비율이 고해상도에서도 유지됨

| 항목 | 960×720 | **2K 60fps** |
|---|---:|---:|
| `use_persistent_data` OFF→ON | −50% | **−48%** (55.78→28.77 s) |
| 디노이즈 ON→OFF | −25% | **−19%** (28.43→23.03 s) |

#### ⚠ 강한 부하 하에서도 최적화 비율 유지

**load 62 (80코어의 78%) + GPU 6장 전부 점유:**

| 항목 | 부하 없음 | 강한 부하 | 판정 |
|---|---:|---:|---|
| persistent ON | 28.77 s | 28.43/28.57/29.13/29.57 s | **편차 3.9%** |
| persistent OFF | 55.78 s | 55.28 s | **−48% 유지** |
| denoise OFF | 23.03 s | 23.03 s | **−19% 유지** |

**이유**: 두 최적화는 GPU 연산량이 아니라 **BVH 재구성 + 후처리 비용**을 줄인다.

#### 🔥 카드 선택이 성능을 바꾼다

같은 10프레임이 **29 s → 64.9 s** 로 변한 이유:

```
[GPU 사용] NVIDIA GeForce RTX 5060 Ti  여유 16281 MB  util   0%
[GPU 제외] NVIDIA GeForce RTX 4070     여유  3914 MB  util 100%
[GPU 제외] NVIDIA GeForce RTX 4060 Ti  여유  6273 MB  util 100%  ×2
[GPU 제외] NVIDIA GeForce RTX 3060 Ti  여유  5937 MB  util 100%
[GPU 제외] NVIDIA GeForce RTX 3070     여유  8138 MB  util   0%
```

6장 중 4장이 100% 점유 중인데도 실패하지 않고 util 0% 카드로 전환했다.
**여유 VRAM 16281 MB (최다) 선택** — §1.7 해법의 실환경 증명.

| 조건 | 프레임당 | 무부하 대비 |
|---|---:|---:|
| 부하 없음 | 2.68 s | 기준 |
| GPU 6장 점유 | 6.49 s | +142% |
| 여유 카드 1장뿐 | **28.13 s** | **+949%** |

#### ⚠ 내가가설했다가 틀린 것 — util 0% = 빠르다 는 가정

6장 점유 시 5060 Ti가 7.21 s 로 느려 util 0% 인데도 느릴 수 있다고 생각했다.
**반복 측정으로 뒤집혔다:**

| 카드 | 반복 warm | 결론 |
|---|---|---|
| RTX 5060 Ti | 7.21 → 4.14 → **2.68 s** | 첫 값은 잔여 부하였음 |
| RTX 4060 Ti | 5.37 → 3.84 → 3.80 s | 안정 |
| RTX 3070 | 8.17 s | |

→ **"enable_gpu 가 가장 느린 카드를 고른다" 는 가설이 틀렸음.**
여유 VRAM 최다 선택이 이 머신에서는 올바르다. **1회 측정 금지.**

#### 산출물 검증

```
$ ffprobe final_60fps.mp4
codec_name=h264  width=1920  height=1080  r_frame_rate=60/1
nb_frames=60     duration=1.000000      748 KB
```
프레임 간 차이 1↔30 = 97,707 px, 1↔60 = 124,468 px (애니메이션 정상).
PNG 시퀀스 60장 = 195 MB → H.264 합치기 성공.

#### 이 과정에서 발견한 Blender 함정

`bpy.ops.object.camera_add()` 는 **`scene.camera` 를 설정하지 않는다.**
후속 `primitive_*_add` 가 컨텍스트를 빼앗으면 카메라 없이 렌더된다 →
`Error: Cannot render, no camera`. 반드시 `sc.camera = bpy.context.object` 대입.
(부하 생성 스크립트 2개가 이걸로 죽었다.)

### 남은 한계 (솔직한 기록)

- 전부 **960×720 기준**. 4K 에서 비율이 달라진다 (고해상도일수록 디노이즈
  상대 비용은 줄고, BVH 비용 비율은 오른다).
- CUDA/AMD/Metal 백엔드 미측정.
- 클라우드 GPU 미측정 (PCIe 성능이 로컬과 다름).
- 위 수치에는 이 머신의 부하(19~34%)가 이미 들어 있다.
  조용한 머신에서는 더 빠를 것이다.

## 2026-10 렌더 엔진 (EEVEE/Cycles/Workbench) — 실측 결과

### 왜 열었나

이 스킬은 Cycles 에 집중되어 있었다. EEVEE 는 "GPU 없는 머신에서 llvmpipe 로
100배 느리다" 는 **오래된 측정 한 줄**만 남아 있었고, **엔진 선택 기준 자체가 없었다.**
사용자가 EEVEE 도 쓸 수 있냐고 물었으니 제대로 재서 보기로 했다.

### 추가 파일

| 파일 | 하는 일 |
|---|---|
| `references/19-render-engines.md` | 엔진 선택 + 실측 매트릭스 + 설정 |
| `compat.set_engine_for_purpose()` | purpose 로 엔진 자동 선택 |
| `compat.eevee_gpu_renderer()` | EEVEE 가 어느 GPU 를 타는지 |
| `compat.eevee_is_software()` | llvmpipe 폴백 감지 |
| `scene_builder_template.py --purpose` | 구조/탐색/영상/최종 자동 분기 |

### 핵심 발견

**1. EEVEE 와 Cycles 는 서로 다른 GPU 에서 돈다**

```
EEVEE   : gpu.platform.renderer_get()
          → AMD Radeon RX 7600 XT (radeonsi, navi33)      ← OpenGL
Cycles  : gpu_report()
          → NVIDIA GeForce RTX 4070                      ← OptiX
```

같은 머신인데 **완전히 다른 카드**. EEVEE 는 Blender GPU 모듈(OpenGL),
Cycles 는 Compute API(OptiX)를 쓴다. 머신에 두 벌의 드라이버가 필요하다.

**2. 속도 격차 7배 vs 샘플 격차 100배**

| 씬 | Workbench | EEVEE | Cycles |
|---|---:|---:|---:|
| mixed | 2.62 s | 3.06 s | **0.30 s** |
| reflective | **0.09 s** | 0.47 s | 0.67 s |
| interior | **0.09 s** | 0.44 s | 0.33 s |

→ **"렌더가 느려요" 의 원인은 엔진이 아니라 샘플 수다.**

**3. 반복 렌더에서는 Cycles 가 10배 (cold vs warm)**

| 엔진 | cold | warm | 감소 |
|---|---:|---:|---:|
| EEVEE (mixed) | 3.50 s | 3.06 s | −13% |
| **Cycles (mixed)** | **4.91 s** | **0.30 s** | **−94%** |

→ 1~3회면 EEVEE(cold 가 싸다), 4회 이상이면 Cycles(warm 이 10배 싸다).

**4. 샘플 스케일링 방식이 다르다**

| 샘플 | EEVEE | Cycles |
|---|---:|---:|
| 16 | 0.25 s | 0.81 s |
| 64 | 0.46 s | 0.98 s |
| 256 | 1.70 s | 1.65 s |

→ EEVEE 는 **선형**(6.8배), Cycles 는 **거의 평탄**(2배, 적응형+디노이즈).
→ 고품질은 Cycles 가 싸다.

**5. EEVEE 는 계산 안 하는 게 있다 (품질 문제)**

거울+유리 씬, `mean_luma`: EEVEE RT off 0.1161 / RT on 0.1281 / Cycles 0.1849.
유리 굴절·거울 반사·GI 가 근사밖에 안 된다. **어두운 게 아니라 계산을 안 한 것.**

**6. `BLENDER_EEVEE_NEXT` 는 5.x 에서 거부된다**

4.x 튜토리얼을 그대로 따라가면 엔진이 안 바뀐다. 5.x 는 `BLENDER_EEVEE`.

### 보조 발견 — persistent_data 반복 렌더 13.7배

같은 씬 5회 반복 렌더:
```
persistent_data=False : 5.57 → 3.93 → 3.73 → 3.80 → 3.85  (warm 3.83 s)
persistent_data=True  : 4.91 → 0.29 → 0.27 → 0.27 → 0.29  (warm 0.28 s)
```
앞선 영상 측정(−50%)보다 훨씬 크다. **정지이미지 반복 최적화에서는 더 큰 효과.**

### 3세대 (2026-10 후속) — 커버리지 공백 스캔

"GPU 가속으로 렌더를 빠르게 하는 모든 축이 다뤄졌는가" 를 스캔해서
빈 축을 찾아 측정한 결과. **새로 실측한 것:**

| 축 | 결과 |
|---|---|
| **SUBSURF `render_levels`** | 5→1: 30M→119K 정점, **17.46→6.24 s (−64%)** |
| **Decimate COLLAPSE** | **역효과 — 3.26→11.03 s (3.4배 느림).** 정점 ↓ 시간 ↑↑ |
| **Decimate UNSUBDIV** | **2.42 s — 가장 빠름 (COLLAPSE 대비 4.6배).** 이걸 써야 한다 |
| `use_light_tree` (30조명, 64spp) | **무효과** (0.94 vs 0.90 s) |
| `denoising_quality` F/B/H | **무효과** (0.81/0.80/0.82 s) |
| 모션블러 ON | +8% (저렴) |
| 출력 포맷 PNG/JPEG/EXR | **무효과** (0.84~0.92 s). 파일 크기가 관건 |
| EXR `color_depth` | **'16'/'32' 만** — `'8'` 은 TypeError |
| **Path Guiding GPU 무지원** | **실증** — GPU 무변화(+3%), CPU 는 +56% 느려짐 |
| `kernel_optimization_level` | **차이 없음** (0.87/0.87/0.92 s). prefs 속성 |
| **CPU vs GPU 픽셀 차이** | **691,200 px 중 2개만 상이**, Δmean_luma=0.000000 |
| VRAM 스필 경계 | 3,250만 정점 + 4K + texture_limit=512 → **스필 미발생** |

이 중 **Decimate COLLAPSE 역효과**와 **Path Guiding 실증**,
**kernel_optimization_level 위치 오류** 는 문서에 없던 발견이다.

> **Decimate COLLAPSE 역효과가 이 스캔에서 가장 값진 발견이었다.**
> "정점 줄이면 빨라진다" 는 당연한 기대를 정면으로 뒤집는다.
> COLLAPSE 는 삼각형을 재구성해서 BVH 를 비싸게 만들고, 그 비용이
> 정점 감소분보다 훨씬 크다. UNSUBDIV 가 맞다.

### 남은 한계

- **EEVEE Vulkan 백엔드 — 측정 완료.** ❓ 아님 (이견 있음).
  `--gpu-backend vulkan` 로 9개 기기(AMD2+NVIDIA6+llvmpipe) 전부 노출되고,
  EEVEE 를 RTX 4070(Vulkan dev 5)에서 돌리면 reflective 씬 0.51 s → 0.28 s (1.8배).
  llvmpipe 강제 시 3.84 s (cold 29.31 s). **대신 `--gpu-device` 인덱스가
  nvidia-smi 카드와 매칭되지 않아 자동 선택은 구현했다가 되돌렸다**
  (후보가 여럿이면 None 반환). 자세한 내용은 §19 §2.5 참조.
- CUDA/OptiX 아닌 백엔드, Metal, volumetrics, 모션블러/DOF 미측정.
- 4.x EEVEE Legacy 경계만 확인 (Engine ID 변경 사실만).
- GPU 없는 머신의 EEVEE 는 재측정 안 함. 다만 llvmpipe 강제 렌더는
  이 머신에서 측정했다 (reflective 3.84 s warm / 29.31 s cold).

## Verification log

| 항목 | 결과 |
|---|---|
| 6개 서브에이전트 실행 | PASS — 6/6 성공, 산출물 전부 존재 |
| T4 mp4 독립 검증 (`ffprobe`) | PASS — h264 / 320×240 / nb_frames=60 / 2.5s |
| T1 mp4 독립 검증 (`ffprobe`) | PASS — h264 / 640×480 / nb_frames=60 / 2.5s |
| T2 배너 시각 확인 | PASS — CJK 텍스트 + 블룸 + 비네트 + 색보정 |
| T6 재질 시각 확인 | PASS — 금속/대리석/플라스틱 3종 구분 가능 |
| T5 f90 시각 확인 | PASS — 상자 무너짐 + 파티클 + 천 |
| T1 f60/f120 비교 | PASS — 리깅이 실제로 움직임 |
| `bk.py api op` 버그 재현 → 수정 → 재검증 | PASS |
| `prop_info` ENUM 버그 재현 → 수정 → 재검증 | PASS |
| `op_check` flag enum 버그 재현 → 수정 → 재검증 | PASS |
| `bk.py api prop` addon 타입 조회 개선 | PASS — `CyclesRenderSettings` 조회 성공 |
| `new_socket(name=)` 동작 확인 | PASS — 키워드/위치 둘 다 동작 |
| `shade_smooth_by_angle` 모디파이퍼 미추가 확인 | PASS — 스택 `[]` |
| `PoseBone.evaluated_get` 부재 확인 | PASS — `AttributeError` |
| `parent_set(ARMATURE_AUTO)` T1 증거 확인 | PASS — 정점그룹 가중치 0.09~0.95 (T1 증거 채택) |
| GN depsgraph 재평가 주장 | **FAIL — 재현 안 됨.** 문서에 넣지 않음 |
| GPU 세그폴트 (exit 139) 재현 → 수정 → 재검증 | PASS — bisect로 원인 특정, 순서 고정 후 exit 0 |
| GPU 무차별 활성화 OOM 재현 → 수정 → 재검증 | PASS — 3장 정확히 제외, 렌더 4.22 s |
| GPU 1/2/3/6장 스케일링 측정 | PASS — 4.51 / 5.26 / 6.17 / OOM |
| 디노이즈·타일·persistent_data 비용 측정 | PASS — −25% / −5% / −5% |
| 템플릿 GPU 경로 end-to-end | PASS — `[GPU 사용] 1장: RTX 4070`, 씬검증 ok, luma 0.344 |
| 엔진 4개 대입 (5.2) | `scene.render.engine` | PASS — **EEVEE_NEXT 거부**, EEVEE/CYCLES/WORKBENCH OK |
| EEVEE GPU 백엔드 확인 | `gpu.init()` | PASS — **AMD RX 7600 XT / OpenGL** (Cycles 는 RTX 4070 / OptiX) |
| 엔진 × 씬 3×3 매트릭스 | 960×720 64spp pd=True | PASS — 9개 조합 전부 측정 |
| EEVEE RT on/off 품질 차이 | reflective | PASS — luma 0.1161 → 0.1281 (Cycles 목표 0.1849) |
| EEVEE 샘플 스케일 | 16/64/256 | PASS — 0.25/0.46/1.70 s (선형) |
| Cycles 샘플 스케일 | 16/64/256 | PASS — 0.81/0.98/1.65 s (평탄) |
| 엔진별 cold vs warm | 4회 반복 | PASS — Cycles −94%, EEVEE −13% |
| `set_engine_for_purpose()` 4종 | compat 헬퍼 | PASS — structure/explore/animate/final 전부 OK |
| 템플릿 `--purpose` 4종 | end-to-end | PASS — 전부 렌더 + imagecheck ok |
| 템플릿 기존 플래그 호환 | --engine/--cpu/--quality | PASS — 6개 조합 전부 exit 0 |
| `persistent_data` 반복 렌더 | mixed, Cycles 5회 | PASS — **3.83 → 0.28 s (13.7배)** |
| **2K 60fps 60프레임 실제 렌더** | Cycles GPU1 + OptiX | PASS — 최종 160.80 s / 탐색 70.46 s |
| **2K 최적화 비율 검증** | 10프레임 비교 | PASS — persistent **−48%**, denoise **−19%** (960×720과 일치) |
| **강한 부하 (load 62 + GPU 6장)** | 10프레임 반복 | PASS — **최적화 비율 유지**, 편차 3.9% |
| **카드 선택 실전 검증** | 6장 중 4장 100% 점유 | PASS — util 0% 카드로 자동 전환, **29 s → 64.9 s 차이 확인** |
| **2K 60fps mp4 산출물** | `ffprobe` | PASS — h264 1920×1080 60/1 fps 60프레임 748 KB |
| `camera_add()` → `scene.camera` 미설정 | 부하 스크립트 2개 실패 | PASS — **함정 발견. 명시적 대입 필요** |

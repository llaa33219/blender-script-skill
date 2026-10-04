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

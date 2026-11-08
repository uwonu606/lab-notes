# 2026 미분류 저장소 triage — KG·지식 저장소 인접성

조사일은 2026-10-10이다. 대상은 HKUST-KnowComp 저장소 가운데 2026년 이후 push 가 있고 KG 저장소로 아직 확인되지 않은 14개다.

원자료 위치는 아래와 같다. 경로는 `knowcomp-kg-landscape/lab/` 기준이다.

| 자료 | 경로 |
|---|---|
| 저장소 메타·README·커밋·contents | `sources/triage/{meta,readme,commits,contents}/` |
| 논문 abstract 메모 | `sources/triage/papers.md` |
| 설정·통계 발췌 | `sources/triage/extra/` |
| 클론 | `repos/{E-LEDGER-WorldAbduct,skillrevise,rethinkskill,ContextLens}` (`--depth 50`, skillrevise 는 `--filter=blob:limit=2m` 추가) |

아래에서 `readme/X.md:N` 은 `sources/triage/readme/X.md` 의 N번째 줄이다. `repos/...:N` 은 클론한 저장소 파일의 줄이다.

## 분류

분류 기준은 세 가지다. (가)는 KG·구조화 지식을 만들거나 쓴다. (나)는 agent memory·wiki·skill 처럼 지식 저장소와 인접한다. (다)는 무관하다.

| 저장소 | 정체 | 분류 | 근거 |
|---|---|---|---|
| ContextLens | GDPR·EU AI Act compliance 를 질문 checklist 로 판정한다. LLM 이 만든 subsumption KG 두 개를 함께 싣는다. | (가) | `repos/ContextLens/data/updated_kgs/` |
| E-LEDGER-WorldAbduct | agent harness 다. 검증된 world rule 과 동적 상태를 ledger 에 쌓으며 라운드마다 진화한다. | (나) | `repos/E-LEDGER-WorldAbduct/eledger/ledger.py:1` |
| skillrevise | 실행 trace 로 skill 을 고친다. 재사용 repair principle 을 Principle Memory 에 담는다. | (나) | `readme/skillrevise.md:9,16` |
| rethinkskill | self-evolving skill 에서 성공·실패 feedback 의 효과를 통제 실험한다. | (나) | `readme/rethinkskill.md:30-36` |
| amemgym | 대화 assistant memory 를 on-policy 로 평가한다. Write·Read·Utilization 단계별로 진단한다. fork 다(원본 AGI-Eval-Official/amemgym). | (나) | `readme/amemgym.md:18,25` |
| MEMLENS | VLM 의 multimodal 장기 대화 memory benchmark 다. fork 다(원본 xrenaf/MEMLENS). | (나) | `readme/MEMLENS.md:29-32` |
| Awesome-In-Parameter-Memory | in-parameter memory 서베이 목록이다. AtlasKV 1저자 Haoyu Huang 이 커밋했다. | (나) 목록 | `readme/Awesome-In-Parameter-Memory.md:11-14` |
| Awesome-Agent-Harness | agent harness 서베이 목록이다. memory·skill·self-evolving 을 한 층에 묶는다. | (나) 목록 | `readme/Awesome-Agent-Harness.md:20-23` |
| AgentIdeaBench | 과학 아이디어 생성을 Static 과 Active(검색 도구 사용)로 비교하는 benchmark 다. Semantic Scholar 는 검색 API 로만 쓴다. | (다) | `readme/AgentIdeaBench.md:290-297,550` |
| DixitWorld | Dixit 게임으로 VLM 의 abductive reasoning 을 평가한다. | (다) | `readme/DixitWorld.md:3-15` |
| GrandGuard | 노인-챗봇 안전 taxonomy·benchmark·guard 다. 50개 위험 유형 3단 taxonomy 는 라벨 체계일 뿐이다. | (다) | `readme/GrandGuard.md:13` |
| CorrGRPO | 다중 reward GRPO 의 정규화를 상관계수로 바꾼다. | (다) | `readme/CorrGRPO.md:41` |
| RLPF | 실행 성능 feedback 으로 code 생성 RL 을 한다. | (다) | `readme/RLPF.md:20-22` |
| Perfcodebench | code 의 정확성·속도를 재는 실행형 benchmark 다. | (다) | `readme/Perfcodebench.md:5,15` |

## (가)·(나) 공통 틀

칸이 해당 없으면 "해당 없음"으로 적는다. 목록 두 개는 # 목록의 정리 방식에서 따로 다룬다.

### ContextLens

1. **입력 → 출력**: 사례 context 를 받는다. GDPR·EU AI Act 의 permitted/prohibited/not applicable 판정과 모르는 요인을 낸다.
2. **LLM 의 역할**: [확인] 판정 단계에서 LLM 은 고정 질문(scope·special·subject·processor·lawful·principal)에 JSON 으로 답한다(`repos/ContextLens/rule_based_checklist/GDPR/prompts/*.txt`). [확인] KG 구축 단계에서 GPT-4o 가 edge 를 만들었다. role KG 91,876개 edge 중 91,459개, attribute KG 176,999개 중 176,491개가 `source=GPT-4o` 다. 나머지는 WordNet·원 법령 seed 다(직접 집계, `sources/triage/extra/contextlens-kg-stats.txt`).
3. **schema/구조**: [확인] 그래프다. relation 은 `subsume`/`is subsumed by` 하나뿐인 taxonomy 다. role KG 는 8,993 node 다. attribute KG 는 7,875 node 다. 파일명 45k·88k 는 양방향으로 두 번 저장한 subsumption 쌍의 수다. [확인] 별도 regulation KB 는 contextual-integrity 칸(sender·recipient·subject·information_type·purpose·consent_form 등)을 가진 표다(`sources/triage/extra/contextlens-gdpr-kb-info.json`).
4. **품질 관리**: 모르는 것: KG 검증 절차는 README 와 코드에 없다. 논문 본문을 보면 알 수 있다.
5. **저장·질의**: [확인] GraphML 파일과 HF arrow 다. [확인] 공개 코드 경로는 둘 다 쓰지 않는다. `load_law_tree` 는 저장소에 없는 `LawTree_*.graphml` 을 읽는다. 그 결과는 `self.law_tree` 에 대입만 된다(`repos/ContextLens/rule_based_checklist/GDPR/utils.py:9`, `prompts/prompt_prepare.py:11`). `KB_dataset` 도 대입 뒤에 쓰이지 않는다(`GDPR/get_response.py:113-115`). `updated_kgs/` 를 참조하는 코드는 없다.
6. **평가**: [확인] PrivaCI-Bench 의 GDPR·EU AI Act test 를 쓴다(WebSearch 요약, `sources/triage/papers.md`). 모르는 것: 수치는 README 에 없다. arXiv 2604.12308 본문 표를 보면 알 수 있다.
7. **규모·비용**: KG 두 개 약 17k node·27만 edge 다. 판정은 학습 없이 질문 수만큼 LLM 호출을 한다.
8. **지금 쓸 수 있는가**: [확인] `config.py` 의 `DATA_PATH` 등이 placeholder 다. KG 는 파일로 바로 읽을 수 있다. 판정 파이프라인과는 이어져 있지 않다.
9. **핵심 한 문장**: LLM 으로 넓힌 subsumption taxonomy 와 법령 checklist 를 싣지만, 공개된 판정 코드는 KG 없이 고정 질문만으로 돈다.

### E-LEDGER-WorldAbduct

1. **입력 → 출력**: 부분 관측 환경(ScienceWorld·DiscoveryWorld·World of Workflows)의 실행 기록을 받는다. 다음 라운드 harness layer 를 낸다. layer 는 agent 별 지시 md 와 `world_model.json` 이다(`repos/E-LEDGER-WorldAbduct/eledger/harness.py:4-8`).
2. **LLM 의 역할**: [확인] 역할은 넷이다. 실행 기록에서 hidden rule 가설을 제안한다. 새 환경 인스턴스에서 가설을 시험하고 `verified` 를 판정한다(`worldabduct/pipeline.py:93-108`). 검증된 rule 의 중복과 모순을 정리한다. 실행 중 State Tracking Agent 가 도구 feedback 에서 동적 상태 갱신을 뽑는다(`eledger/agents.py:91-120`).
3. **schema/구조**: [확인] 문서형 레코드다. 그래프가 아니다. 정적 지식 W_S 는 `{rule, applicability, action_guide}` 목록이다. 동적 상태 W_D 는 `collection.id.field` path 를 키로 쓰는 평면 저장소다(`eledger/ledger.py:1,21-22`).
4. **품질 관리**: [확인] 장치는 셋이다. 첫째, rule 은 새 인스턴스에서 대조 실험으로 `verified` 를 받아야 들어간다. 그 판정 자체는 LLM 이 내린다. 둘째, 정리 단계는 같은 trigger 에 효과가 모순인 rule 을 모두 버린다(`environment/scienceworld/prompts/evolution/hidden_rule_summary.md:6-8`). 셋째, W_D 갱신은 path 문법과 허용 collection 을 검사한다. 위반하면 같은 agent 에 되돌려 고치게 한다(`eledger/ledger.py:28-39`, `eledger/agents.py:105-114`).
5. **저장·질의**: [확인] JSON 파일이다. 질의는 하지 않는다. rule 목록 전체를 prompt 의 `{{STATIC_WORLD_MODEL}}` 에 넣는다(`environment/scienceworld/prompts/harness/task_agent.md:14-16`). 같은 자리에 "현재 관측과 충돌하면 관측을 따르라"는 지시도 넣는다.
6. **평가**: 모르는 것: 수치와 논문이 없다. 2026-10-08 첫 커밋 1개뿐이다. 제목 검색으로도 논문을 찾지 못했다.
7. **규모·비용**: [확인] 세 benchmark 모두 step limit 50이다(`readme/E-LEDGER-WorldAbduct.md:53`). WoW 는 ServiceNow 인스턴스가 필요하다.
8. **지금 쓸 수 있는가**: [확인] 코드는 완결돼 있다. LICENSE 파일은 없다. 실행은 미검증이다.
9. **핵심 한 문장**: agent 가 실험으로 검증한 rule 을 라운드마다 쌓고 모순을 버리는, 그래프 없는 "쓰면서 고치는" 지식 저장소다.

### skillrevise

1. **입력 → 출력**: LLM 이 처음 쓴 skill 과 task 를 받는다. 예산 안에서 utility 가 가장 높았던 skill 버전을 낸다(`readme/skillrevise.md:9`).
2. **LLM 의 역할**: [확인] skill 초안을 쓴다. principle 을 골라 skill 을 고친다. 진단은 기본 설정에서 LLM 을 쓰지 않고 실행·verifier 근거로 결정적으로 만든다(`readme/skillrevise.md:104-110`).
3. **schema/구조**: [확인] skill 은 문서(md)다. Principle Memory 는 typed 레코드다. 칸은 `trigger`·`repair_rule`·`transfer_constraint`·`supporting_episodes`·`negative_episodes`·`utility_stats`·`provenance`·`version`·`status` 등이다(`repos/skillrevise/skillrevise/core/models.py:129-153`). 그래프는 아니다.
4. **품질 관리**: [확인] 후보마다 재실행한 뒤 utility gate 를 거친다. Diagnosis Gate 는 typed failure label 과 실행 근거가 없으면 수정을 막는다(`repos/skillrevise/docs/overview.md:15`). 평가 중 memory 는 read-only 로 고정한다. 흡수(absorption)는 별도 calibration split 에서만 한다(`readme/skillrevise.md:128`). 흡수 때 episode 고유 literal 이 들어가지 않게 거른다(`skillrevise/method/principles.py:793`).
5. **저장·질의**: [확인] JSON bank 에 저장한다. BM25 와 dense 를 RRF 로 섞어 검색한다(`skillrevise/method/principles.py:1438,1475,1500`). [확인] bank 크기는 작다. BFCL 단계별 bank 가 5~6개 principle 이다(`docs/overview.md:41`).
6. **평가**: [확인] 성공 task 수는 아래 표와 같다(`readme/skillrevise.md:26-28`). baseline 은 No skill 과 Skill-Creator 다.

   | benchmark | executor | No skill | Skill-Creator | SkillRevise |
   |---|---|---|---|---|
   | SkillsBench | GPT-5.5 | 31/86 | 34/86 | 53/86 |
   | SkillLearnBench-Random | Opus-4.7 | 7/50 | 7/50 | 25/50 |
   | SWE-Skills-Bench-Hard | Qwen-3.6-Plus | 22/70 | 24/70 | 35/70 |

   SkillsBench 수치는 abstract 의 36.05% → 61.63% 와 같다.
7. **규모·비용**: [확인] 수정 1회에 LLM 호출 1회다. 최대 3회 수정한다(`readme/skillrevise.md:30,104-110`).
8. **지금 쓸 수 있는가**: [확인] MIT 다. `--mock` smoke test 가 있다. 실제 실행에는 외부 harness 명령이 필요하다(`readme/skillrevise.md:76,126`).
9. **핵심 한 문장**: skill 문서를 실행 근거로 고치고, 고치는 요령은 작은 typed principle memory 에 따로 쌓는다.

### rethinkskill

1. **입력 → 출력**: 초기 `skill.md` 와 benchmark 를 받는다. 라운드별 후보 skill 과 validation best checkpoint 를 낸다(`readme/rethinkskill.md:293-317`).
2. **LLM 의 역할**: optimizer LLM 이 성공·실패 trajectory 를 보고 skill 을 다시 쓴다.
3. **schema/구조**: 문서(markdown skill 하나)다.
4. **품질 관리**: [확인] validation 으로 거른다. 후보 388개 중 55개만 validation best 를 갱신했다(`readme/rethinkskill.md:38-41`).
5. **저장·질의**: 해당 없음. skill 파일 하나를 통째로 prompt 에 넣는다.
6. **평가**: [확인] 14개 setting 중 11개에서 evolved skill 이 선택됐다. 그중 9개가 test 를 개선했다. 11개 모두 실패 trajectory 를 포함한 조건에서 나왔다(`readme/rethinkskill.md:38-46`).
7. **규모·비용**: 3 model × 5 benchmark, 42 run 이다.
8. **지금 쓸 수 있는가**: [확인] MIT 다. CI 가 있다. model 호출 없는 smoke 명령이 있다.
9. **핵심 한 문장**: skill self-evolution 은 꾸준한 개선이 아니라 sparse 하고 validation 으로 거른 탐색이다(abstract 요지).

### amemgym

1. **입력 → 출력**: persona 기반 시뮬레이션 사용자와 상태가 변하는 대화를 받는다. memory 점수와 Write/Read/Utilization 진단을 낸다(`readme/amemgym.md:18-27`).
2. **LLM 의 역할**: 사용자 시뮬레이터, 평가 대상 assistant, memory 쓰기 정책을 맡는다.
3. **schema/구조**: [확인] 비교 대상 넷은 AWI(in-context), AWE(external), RAG, Native 다(`readme/amemgym.md:87-92`). AWE·RAG 설정은 mem0 형식의 milvus vector store 다. 차이는 `enable_llm_mem_policy` 하나다(`sources/triage/extra/amemgym-awe-2-4-30.json`). 그래프는 없다.
4. **품질 관리**: 해당 없음(평가 도구).
5. **저장·질의**: vector top-k 30 이다.
6. **평가**: 모르는 것: README 와 abstract 에 수치가 없다. 논문 Table 3 을 보면 알 수 있다.
7. **규모·비용**: 128K~512K+ context 다(`readme/amemgym.md:27`).
8. **지금 쓸 수 있는가**: [확인] MIT 다. `uv sync` 로 설치한다. HF 데이터셋이 있다.
9. **핵심 한 문장**: memory 를 정적 QA 가 아니라 assistant 자신의 대화 위에서 평가하고 실패를 쓰기·읽기·활용으로 쪼갠다.

### MEMLENS

1. **입력 → 출력**: 이미지가 섞인 다중 세션 대화(32K~256K)와 질문을 받는다. LLM judge 점수를 낸다.
2. **LLM 의 역할**: 평가 대상이다. 채점은 Qwen3-VL-235B judge 가 한다(`readme/MEMLENS.md:209`).
3. **schema/구조**: 해당 없음. 평가 대상 memory agent 7개(M3-Agent·Mem0·MemOS 등)의 구조는 각 원저 몫이다(`readme/MEMLENS.md:90`).
4. **품질 관리**: 해당 없음.
5. **저장·질의**: 해당 없음.
6. **평가**: [확인] 789문항, 5개 ability 다(`readme/MEMLENS.md:32`). [확인] 27 LVLM 과 7 memory agent 를 평가했다. multi-session reasoning 은 대부분 30% 미만이다. memory agent 는 저장할 때 압축하면서 시각 정보를 잃는다(abstract, `sources/triage/papers.md`).
7. **규모·비용**: [확인] agent 추론이 직접 VLM 추론보다 약 60배 느리다. 그래서 agent 평가는 195문항 subset 으로 한다(`readme/MEMLENS.md:90`).
8. **지금 쓸 수 있는가**: [확인] 코드는 MIT, 데이터는 CC-BY-4.0 이다.
9. **핵심 한 문장**: 지금의 memory agent 는 저장할 때 압축하면서 근거를 잃는다. 저자들은 "structured multimodal retrieval" 과의 hybrid 를 다음 방향으로 꼽는다.

## 목록의 정리 방식

두 목록 모두 KG 를 독립 범주로 두지 않는다. KG 는 memory 의 한 재료나 한 형태로 들어간다.

| 목록 | 정리 축 | KG 의 자리 | 근거 |
|---|---|---|---|
| Awesome-In-Parameter-Memory | 두 축이다. 파라미터를 넣는 위치(Embedding/Attention/FFN/Hybrid)와 획득 시점(online/offline)이다. | AtlasKV·KBLaM 이 "Attention — Offline", memory object "Encoded KV Banks", 획득 연산 "Knowledge encoder" 칸에 들어간다. KG 는 파라미터로 encode 할 원료다. | `readme/Awesome-In-Parameter-Memory.md:13-14,125` |
| Awesome-Agent-Harness | 4층 stack 이다(실행·context/trajectory·interaction·guardrail). memory·context compression·self-evolving·skill 은 모두 2층에 있다. | Zep(temporal KG)·HippoRAG 가 Mem0·MemGPT·A-mem 과 같은 "Memory Systems" 표에 섞여 있다. 그 절의 정의는 "Structured, queryable knowledge layers" 다. | `readme/Awesome-Agent-Harness.md:139-151` |

[확인] in-parameter memory 목록은 비구조 memory 와 구조화 KG 를 나누지 않는다. 대신 파라미터냐 아니냐로 나눈다. 비교 대상은 ICL 과 ICL 기반 harness 다. abstract 에 KG·RAG 언급은 없다.

[확인] Quick Index 에 "Insights from the Survey" 절이 있지만 본문에는 그 절이 없다. Citation 블록도 비어 있다(`readme/Awesome-In-Parameter-Memory.md:48,211-216`). 공개 이틀째의 미완성 상태다.

## 팀 [추정] 검증

검증할 판단은 "KnowComp 의 2026 KG 연구가 'KG 한 번 짓기'에서 'agent 가 쓰면서 고치는 지식 저장소(그래프 + wiki)'로 옮겨 간다"이다.

### 방향은 지지된다

[확인] 이 14개 중 3개가 "agent 가 실행 결과로 저장소를 고친다"는 구조를 구현한다. E-LEDGER, skillrevise, rethinkskill 이다. 2개는 그런 memory 를 평가하는 benchmark 다. amemgym 은 self-evolution 실험도 싣는다(`readme/amemgym.md:123-138`). MEMLENS 는 평가만 한다.

[확인] KG 계열 저자가 memory 서베이로 옮겨 왔다. in-parameter memory 서베이 저자에는 AtlasKV 저자 Haoyu Huang, AutoSchemaKG 저자 Jiaxin Bai, Hong Ting Tsang 이 있다(`sources/triage/papers.md`).

### "그래프"는 이 14개에서 지지되지 않는다

[확인] 쓰면서 고치는 저장소 넷은 모두 그래프가 아니다. skill 은 md 다. principle 은 typed JSON 레코드다. E-LEDGER 의 rule 은 JSON 목록이고 상태는 평면 path 저장소다. amemgym 이 평가하는 저장소도 vector store 다.

[확인] 14개 중 그래프는 ContextLens 의 subsumption taxonomy 뿐이다. 그것도 GPT-4o 로 한 번 지은 정적 산출물이다. 공개 코드는 그 그래프를 쓰지 않는다.

[추정] 이 묶음에서 갱신 단위는 "그래프의 triple"이 아니라 "조건·행동·근거를 가진 문서형 레코드"다 — 사례 3개: E-LEDGER `{rule, applicability, action_guide}`, skillrevise `RepairPrinciple`, rethinkskill `skill.md`.

### 세 번째 갈래로 파라미터가 있다

[확인] in-parameter memory 서베이는 KG 를 KV bank 로 encode 할 원료로 둔다. [추정] KnowComp 의 KG 저자들은 KG 를 "agent 가 고치는 문서"와 "모델에 넣는 파라미터"라는 두 저장 형태의 원료로 다시 놓는다 — 사례 2개: AtlasKV 를 Encoded KV Banks 칸에 둔 분류, KG 를 Memory Systems 표에 섞은 harness 목록.

### 공저자 근거는 약하다

[확인] AutoSchemaKG(arXiv 2505.23628) 공저자 Qing Zong·Yauwai Yim·Hongyu Luo 는 skillrevise 에도 있다.

[확인] 그런데 Qing Zong·Yauwai Yim·Jiaxin Bai·Tianshi Zheng 은 KG 와 무관한 DixitWorld 에도 있다(`readme/DixitWorld.md:71`). [추정] 이 연구실에서 공저는 주제를 가로질러 넓게 퍼져 있다. 그래서 공저 겹침만으로는 연구 방향 이동을 보여 주기 어렵다 — 사례 1개: DixitWorld.

### 판정

방향("쓰면서 고친다")은 맞다. 저장 형태("그래프 + wiki")는 이 14개 기준으로 "문서형 레코드 + 파라미터"로 고쳐야 한다. 그래프가 갱신 대상으로 남는지는 다른 팀원의 DeepRefine·EvolvingWorld 결과와 맞춰 봐야 한다.

## 확인 못 한 것

| 항목 | 무엇을 보면 아는가 |
|---|---|
| E-LEDGER 의 수치와 논문 | 논문 공개를 기다린다. 또는 저자(Eason-nuosen)를 확인한다. |
| ContextLens KG 의 생성·검증 절차와 판정 수치 | arXiv 2604.12308 본문을 읽는다. PrivaCI-Bench 원 저장소의 KG 생성 코드를 본다. |
| amemgym 의 결과 수치(AWE vs RAG vs AWI) | 논문 Table 2·3 을 본다. |
| in-parameter memory 서베이 본문이 KG·RAG 를 어디에 놓는지 | arXiv 2610.08630 본문을 읽는다. abstract 만 봤다. |
| 코드 실행 | 어떤 저장소도 실행하지 않았다. 모든 동작 서술은 코드를 읽은 결과다. |
| skillrevise 데이터 | 2MB 넘는 blob 은 받지 않았다. 코드와 문서만 읽었다. |

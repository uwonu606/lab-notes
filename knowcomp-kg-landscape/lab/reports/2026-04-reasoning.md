# 2026 KG reasoning 저장소 — KG 를 만드는 사람의 눈으로

대상은 2026년에 push 가 있는 HKUST-KnowComp 저장소 셋이다. HypoAgent, CtrlHGen, DARK 다.

조사일은 2026-10-10 이다. 세 저장소를 `lab/repos/` 에 `--depth 50` 으로 클론해 읽었다. 논문은 arXiv HTML 을 받아 텍스트로 바꿨다(`lab/sources/04-reasoning/`). 코드를 실행하지는 않았다. 예외는 `GPT2Config` 설정 확인 한 번이다(#논문과 코드가 다른 곳).

근거 라벨:
- `[확인]` 코드·논문을 직접 읽었거나 실행해서 봤다.
- `[추정]` 실행하지 않고 다른 사실에서 끌어냈다. 끌어낸 사례를 옆에 적는다.

줄 번호 표기:
- `repos/X/a.py:12` 는 `lab/repos/X/a.py` 의 12번째 줄이다.
- `sources/2605.31370.txt:204` 는 `lab/sources/04-reasoning/` 아래 논문 텍스트 파일의 204번째 줄이다.

## 결론

셋 다 KG 를 만들거나 고치지 않는다. 고정된 KG 위에서 추론만 한다.

[확인] 세 저장소는 KG 를 PyKEEN 내장 데이터셋에서 읽는다. 읽은 KG 는 networkx 그래프로 바꾼다. 그 뒤에는 질의 실행에만 쓴다(`repos/HypoAgent/akgr/kgdata/load_kg_util.py:74-90`, `:185`). triple 을 추가하거나 지우는 코드는 셋 어디에도 없다.

[확인] 여기서 "가설"은 KG 위의 first-order logic 질의다. projection·intersection·union·negation 으로 이루어진다. 가설을 실행한 답 집합이 관측 엔티티 집합과 얼마나 겹치는지(Jaccard)로 점수를 매긴다(`sources/2505.20948.txt:114-126`).

[확인] 따라서 가설은 새 triple 이 아니다. 관계끼리 엮는 규칙(Horn rule)도 아니다. 특정 엔티티를 anchor 로 박은 "이 엔티티 집합을 설명하는 질의"다. 논문 예시를 보면, 선수 셋이 관측으로 주어지면 "Rockets 에서 뛰었고 MVP 를 받은 선수" 같은 질의를 내놓는다(`sources/2605.31370.txt:79`).

[확인] 데이터셋은 모두 고전 벤치마크다. FB15k-237, WN18RR, DBpedia50, BioKG, PharmKG8k 를 쓴다. LLM 으로 만든 KG 위에서 돈 실험은 셋 다 없다.

[확인] 셋 중 LLM 을 쓰는 곳은 HypoAgent 하나다. 그마저도 LLM 이 논리 구조를 직접 쓰지 않는다. LLM 은 조건을 고르고 진단 도구를 부른다. 구조는 작게 학습한 생성기가 쓴다.

## 공통 바탕 — `akgr` 패키지

세 저장소는 AbductiveKGR(ACL 2024)의 `akgr` 패키지를 복사해 키웠다. 아래는 셋에 공통이다. 저장소별 절에서는 다시 적지 않는다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| KG 적재 | PyKEEN 데이터셋 이름으로만 KG 를 고른다. 원래 split 을 합친 뒤 8:1:1 로 다시 나눈다 | [확인] `load_kg_util.py:74-90`, `:154-156` |
| 그래프 구성 | 누적 그래프 셋을 만든다. `train` 은 학습 간선, `valid` 는 학습+검증, `test` 는 전부다 | [확인] `load_kg_util.py:176-185` |
| 저장 | networkx MultiDiGraph 를 pickle 로 저장한다. 샘플은 jsonl 로 저장한다. graph DB 는 쓰지 않는다 | [확인] `load_kg_util.py:51-63`, `sampling/sample_parallel.py:135-136` |
| 질의 실행 | 재귀 집합 연산으로 답을 구한다. projection 은 out-edge 를 순회하고, intersection 은 집합 교집합이다 | [확인] `kgdata/kgclass.py:274-313` |
| 학습 데이터 | 패턴 13개마다 가설을 샘플링한다. 그 가설의 답 집합을 관측으로 삼는다. 관측은 최대 32개다 | [확인] `sample_parallel.py:149`, `sources/2505.20948.txt:199` |
| 시험 데이터 | 시험 질의는 test 그래프에서 답이 더 늘어나는 것만 남긴다. 숨긴 10% 간선을 거쳐야 닿는 답이 관측에 섞이도록 한 것이다 | [확인] `CtrlHGen/akgr/sampling/sample_parallel.py:48-60`, `sources/2312.15643.txt:245` 부근 |
| 토큰화 | 엔티티 id 와 관계 id 를 그대로 어휘 토큰으로 쓴다. 어휘 크기는 offset + 엔티티 수 + 관계 수다 | [확인] `HypoAgent/akgr/tokenizer.py:96-104` |
| schema | 노드 타입·엣지 타입 구분이 없다. 관계 id 만 쓴다. 이름은 자연어로 풀어 보여 줄 때만 쓴다 | [확인] `kgclass.py`, `agent/getsomesampleFromDB.py:23-31` |

[확인] 데이터셋 크기는 AbductiveKGR 표에 있다(`sources/2312.15643.txt:222-245`).

| KG | 관계 | 엔티티 | 전체 간선 |
|---|---|---|---|
| FB15k-237 | 237 | 14,505 | 620,158 |
| WN18RR | 11 | 40,559 | 185,164 |
| DBpedia50 | 351 | 24,624 | 68,842 |

BioKG 와 PharmKG8k 의 크기는 확인하지 못했다.

[확인] 토큰화 방식 때문에 생성기는 KG 하나에 묶인다. 엔티티 id 가 곧 어휘다. 그래서 KG 를 바꾸거나 엔티티가 늘면 처음부터 다시 학습해야 한다. 이 KG 들을 쓰는 이유는 PyKEEN 이 이 이름들을 지원하기 때문이다. 자기 KG 를 넣으려면 `load_kg_common` 에 분기를 추가해야 한다(`load_kg_util.py:88-90` 은 그 밖의 이름에 `None` 을 돌려준다).

## 한눈에

| 항목 | CtrlHGen | DARK | HypoAgent |
|---|---|---|---|
| 논문 | ICLR 2026 (arXiv 2505.20948) | WWW 2026 (arXiv 2510.11462) | arXiv 2605.31370 (2026-05) |
| 한 줄 | 조건 토큰으로 가설 생성을 제어한다 | masked diffusion 하나로 abduction 과 deduction 을 함께 한다 | LLM agent 가 진단하고, 생성기를 다시 불러 가설을 고친다 |
| KG 를 만들거나 고치는가 | 아니다 | 아니다 | 아니다 |
| 데이터셋 | FB15k-237, WN18RR, DBpedia50 | FB15k-237, WN18RR, DBpedia50 | BioKG, PharmKG8k, DBpedia50 |
| LLM | 없다. 비교 baseline 으로만 쓴다 | 없다. 비교 baseline 으로만 쓴다 | DeepSeek-V4-Flash, Qwen3-235B, GPT-5.4-mini 를 API 로 쓴다. 프롬프팅만 한다 |
| 생성기 | GPT-2 형 decoder. 처음부터 학습한다 | Dream 형 masked diffusion. 10층, hidden 768. 처음부터 학습한다 | CtrlHGen 생성기를 그대로 쓴다 |
| 2026 커밋 내용 | README 1건, config 1줄 | README 2건 | 코드 공개(2026-06, 2026-09) |
| 라이선스 | 없다 | MIT | MIT |
| 데이터·체크포인트 | README 에 링크가 없다. 공개 요청 issue #1 이 열려 있다 | README 에 링크가 없다 | SharePoint 링크가 있다 |

[확인] 2026 push 중 실제 코드 변경은 HypoAgent 뿐이다. CtrlHGen 의 2026 커밋은 README 수정과 `config-dataloader.yml` 수정이다. DARK 의 2026 커밋은 README 수정 둘이다(`sources/meta-*.txt`).

## CtrlHGen

### 입력 → 출력

1. 샘플링 단계에서 관측-가설 쌍을 만든다(`scripts/sample/sample_full.sh` → `akgr/sampling/sample_parallel.py`).
2. sub-logic decomposition 으로 데이터를 늘린다. 복잡한 패턴 다섯 개(up, 3in, pni, pin, inp)를 하위 가설로 쪼갠다. 하위 가설을 KG 에서 실행해 하위 관측을 얻는다(`sources/2505.20948.txt:139`, `:199`).
3. 지도학습은 두 단계다. 먼저 조건 없이 400 epoch 을 돈다. 다음에 조건 토큰을 붙여 50 epoch 을 돈다(`sources/2505.20948.txt:739`).
4. RL 은 GRPO 계열로 그룹당 4개를 샘플한다. 보상은 Jaccard·Dice·Overlap 가중합에 조건 준수 보상을 더한 것이다. 보상 계산은 train 그래프에서 한다(`akgr/abduction_model/main.py:478-489`, `:895`).
5. 출력은 가설 질의 토큰열이다. test 그래프에서 실행해 채점한다(`main.py:877`, `--test_split` 기본값 `test`).

[확인] 조건은 다섯 종류다. pattern, relation-number, entity-number, specific-entity, specific-relation 이다(`sources/2505.20948.txt:160-163`, `:375`).

### 평가

[확인] 기준은 두 가지다. 의미 유사도는 test 그래프에서 실행한 답과 관측의 Jaccard·Dice·Overlap 이다. 조건 준수율은 Accuracy 다. baseline 은 조건 없는 AbductiveKGR 과 LLM 들이다.

| 설정 | Jaccard | 출처 |
|---|---|---|
| FB15k-237, 조건 없음 (AbductiveKGR) | 61.4 | `sources/2505.20948.txt:214-220` |
| FB15k-237, pattern 조건 | 65.5 (조건 준수 98.9) | `:221-227` |
| DBpedia50, 조건 없음 | 64.3 | `:288-294` |
| DBpedia50, pattern 조건 | 73.8 | `:295-301` |
| FB15k-237, GPT-4o + 2-hop subgraph 프롬프트 | 2.4 | `:325-373` |
| FB15k-237, GPT-5 thinking + 2-hop subgraph | 18.7 | `:362-367` |
| FB15k-237, CtrlHGen 5조건 평균 | 64.3 | `:368-373` |

[확인] 논문은 LLM 이 부진한 이유로 둘을 든다(`sources/2505.20948.txt:378`). 하나는 구조화된 질의 그래프를 만들지 못한다는 것이다. 다른 하나는 LLM 의 사전 지식이 KG 와 충돌한다는 것이다.

### 규모·비용

[확인] 실험은 A6000 48GB 4장에서 돌렸다. 논문은 decoder 를 12층이라고 적는다(`sources/2505.20948.txt:203`). 학습 시간은 적혀 있지 않다.

### 지금 쓸 수 있는가

[확인] 바로 쓰기 어렵다. 걸림돌은 넷이다.
- LICENSE 파일이 없다.
- 데이터·체크포인트 링크가 없다(issue #1 "Release CtrlHGen artifacts on Hugging Face" 가 열려 있다).
- `./hug_model` 디렉토리를 요구하는데 저장소에 없다(`akgr/abduction_model/transformer.py:68-70`).
- `__pycache__` 가 커밋되어 있다.

### 이 저장소가 말하는 "LLM 시대 KG"

LLM 은 구조화된 가설을 못 쓰니, KG 전용 소형 생성기에 사람이 원하는 조건을 토큰으로 건네 제어한다.

## DARK

### 입력 → 출력

1. 샘플링은 CtrlHGen 과 같다(`scripts/sample/sample_full.sh`).
2. 통합 사전학습(`--training_mode unify`)에서는 질의와 결론(답 집합)을 한 시퀀스로 두고 무작위로 가린다. 질의를 가리면 abduction 이 되고, 결론을 가리면 deduction 이 된다(`akgr/abduction_model/main.py:157-173`).
3. 과제별 SFT(`--training_mode sft`)를 한다(`main.py:176-191`, `scripts/train/db.sh`).
4. logic-exploration RL 에서는 질의와 결론을 함께 가리고 생성한다. 보상은 train 그래프 Jaccard 다(`main.py:106`, `sources/2510.11462.txt:205-215`).
5. 추론은 self-reflective denoising 이다. k 단계마다 후보 가설 p 개를 만든다. 각 후보의 결론을 deduction 으로 구한다. 관측과 가장 맞는 후보를 남긴다(`sources/2510.11462.txt:184-187`).

[추정] 5단계의 deduction 은 KG 실행이 아니라 같은 diffusion 모델이 결론을 생성하는 것이다.

근거 1개: 논문이 "employ deductive reasoning to derive the corresponding conclusion" 이라고만 쓰고, 이 모델이 deduction 을 겸하도록 학습되었다(`sources/2510.11462.txt:186`).

샘플링 코드(`model/custom_mydream/generation_utils.py`)는 읽지 않았다.

### 평가

[확인] abduction 은 test 그래프 Jaccard 로 잰다. baseline 은 AbductiveKGR 과 LLM(2-hop subgraph 프롬프트)이다. deduction 은 MRR·Hits@k 로 잰다. baseline 은 BetaE, FuzzyQE, ULTRAQUERY, Query2Particles 다.

| 데이터셋 | AbductiveKGR 평균 Jaccard | DARK 평균 Jaccard | LLM 평균 Jaccard | 출처 |
|---|---|---|---|---|
| FB15k-237 | 66.0 | 67.2 | 3.7–4.0 | `sources/2510.11462.txt:266-341` |
| WN18RR | 72.6 | 73.6 | 5.4–6.9 | `:342-417` |
| DBpedia50 | 64.3 | 72.5 | 2.9–3.6 | `:418-493` |

[확인] deduction MRR 에서 DARK 는 FB15k-237 42.0 이고 ULTRAQUERY 43.7 보다 낮다. WN18RR 은 38.7, DBpedia50 은 38.9 로 가장 높다(`sources/2510.11462.txt:502-584`).

[확인] 그 deduction 표의 WN18RR 열에는 산술 모순이 있다. Hits@1 은 MRR 을 넘을 수 없다. 그런데 DARK 는 MRR 38.7 에 H@1 42.3 이고, Query2Particles 는 MRR 34.1 에 H@1 42.2 다(`:558-584`). 열 순서가 틀렸는지, 수치가 틀렸는지는 모른다.

### 규모·비용

[확인] 모델은 10층, hidden 768, attention head 8 이다(`sources/2510.11462.txt:496`, `akgr/abduction_model/model/custom_mydream/configuration_dream.py:31-35`). 학습은 통합 200 epoch, 과제별 200 epoch, RL 은 데이터셋당 10 epoch 이다. A6000 48GB 4장을 썼고 5회 평균이다.

### 지금 쓸 수 있는가

[확인] MIT 라이선스다. 걸림돌은 셋이다.
- 데이터·체크포인트 링크가 없다.
- `custom_gpt.py:463` 에 개발자 홈 절대경로 `/home/zhangziwei/gys/AbductiveKGR/hug_model` 이 박혀 있다.
- `evaluation_deductive.py:2` 의 `nentity` 기본값이 DBpedia50 의 24624 다.

### 이 저장소가 말하는 "LLM 시대 KG"

LLM 계열의 생성 기법(diffusion, GRPO)을 KG 전용 소형 모델에 옮기면, 질의→답과 답→질의를 한 모델이 함께 배울 수 있다.

## HypoAgent

### 입력 → 출력

1. 생성기를 학습한다. CtrlHGen 과 같은 GPT-2 형 생성기를 조건 없이 한 번, 여러 조건을 섞어 한 번 학습한다(`akgr/abduction_model/main.py`, README 3.1–3.2).
2. Proposal 단계에서는 LLM 이 사용자 발화를 조건 JSON 으로 바꾼다(`akgr/agent/loop.py:46-110`). 조건과 관측 엔티티 이름을 토큰열로 바꾼다(`tools.py:197-210`). 생성기가 가설을 낸다(`tools.py:61-67`).
3. 채점 단계에서는 가설을 KG 에서 실행한다. 관측과의 Jaccard 를 잰다(`loop.py:292`). Jaccard 가 0.95 이상이면 멈춘다(`loop.py:315`, 실행 기본값 `:710`).
4. Root-cause analysis 단계에서는 smolagents `CodeAgent` 를 쓴다. 최대 5 step 동안 KG 도구 4개를 파이썬 코드로 호출한다(`loop.py:442-452`).
5. Refiner 단계는 후보를 세 갈래로 낸다. 같은 조건으로 재생성, 바뀐 조건으로 재생성, LLM 이 가설을 직접 고쳐 쓰기다. 각 후보를 실행해 사용자 조건 준수 → Jaccard 순으로 고른다(`loop.py:181-217`, `:625-660`). 최대 3라운드다.
6. 출력은 가장 좋은 가설과 그 자연어 풀이다. 라운드 이력은 JSON 으로 남긴다(`loop.py:725-760`).

### LLM 과 KG 의 상호작용

[확인] LLM 은 KG 를 직접 읽지 않는다. 도구를 거쳐 networkx 그래프에 질의를 실행할 뿐이다. Cypher·SPARQL 같은 질의 언어나 DB 는 없다. 도구는 `akgr/agent/tools.py` 에 있다.

| 도구 | 하는 일 | 위치 |
|---|---|---|
| `graph_validation` | 가설을 조각(단일 atom, 사슬의 중간 hop, 부분 교집합)으로 나눠 각각 실행한다. 조각마다 답 수와 관측과의 겹침을 보고한다 | `:592-709` |
| `incoming_edge_intersection` | 관측 엔티티 모두에 들어오는 간선의 head 를 교집합한다. 1-hop·2-hop 후보 anchor 를 Jaccard 순으로 낸다 | `:716-1044` |
| `intersection_candidates` | 위 후보 중 상위 20개로 2i·2u 를, 상위 10개로 3i 를 조합해 실행하고 순위를 낸다 | `:893-1004`, `:1456-1494` |
| `generate_hypothesis_llm` | 가설을 직접 만든다. `modify` 모드에서는 LLM 이 토큰열을 고쳐 쓴다 | `:1334-1453` |
| `execute_and_diagnose` | 가설 답을 맞은 답(TP)·오답(FP)·놓친 답(FN)으로 가르고 too_broad·too_narrow 를 판정한다. `single.py:129` 가 직접 부른다 | `:1051-1116` |
| `neighborhood_candidates` | 관측과 FP 의 1-hop·2-hop 이웃을 점수화한다. `tools.py` 밖에서 부르는 곳이 없다 | `:1123-1331` |

[확인] 위 도구의 계산은 학습된 모델 없이 그래프 순회와 집합 연산만으로 한다. 그래서 다른 KG 에도 그대로 옮길 수 있다.

[확인] LLM 은 OpenAI 호환 API 로 부른다(`loop.py:715-721`, `deepinfra` 설정). 논문은 백엔드 셋을 쓴다. DeepSeek-V4-Flash, Qwen3-235B, GPT-5.4-mini 다(`sources/2605.31370.txt:208`). 학습은 하지 않는다.

### 평가

[확인] 기준은 test 그래프 Jaccard·Dice·Overlap 과 정답 조건 준수율(Accuracy)이다. baseline 은 다섯이다. Symbolic Search, 같은 도구를 쓰는 ReAct, CtrlHGen 1회, CtrlHGen best-of-k, ReAct + CtrlHGen 이다.

단일 턴 Jaccard(`sources/2605.31370.txt:209-329`):

| 방법 | BioKG | PharmKG8k | DBpedia50 |
|---|---|---|---|
| Symbolic Search | 0.420 | 0.495 | 0.460 |
| ReAct (KG 도구 있음) | 0.224 | 0.216 | 0.409 |
| CtrlHGen | 0.718 | 0.633 | 0.781 |
| CtrlHGen best-of-k | 0.758 | 0.704 | 0.810 |
| HypoAgent (DeepSeek-V4-Flash) | 0.885 | 0.826 | 0.945 |

[확인] 조건 준수율은 크게 오르지 않는다. DBpedia50 에서 HypoAgent 0.746, CtrlHGen 0.730 이다.

[확인] 다회 대화 실험은 실제 사용자 대화가 아니다. 참조 가설에서 대본을 만든 3턴 대화를 데이터셋마다 500개 쓴다(`sources/2605.31370.txt:756-760`).

### 규모·비용

[확인] DBpedia50 단일 턴에서 사례당 비용을 비교했다(`sources/2605.31370.txt:443-470`, `:506-507`).

| 방법 | LLM 호출 | 비용(CNY) | Jaccard |
|---|---|---|---|
| ReAct + CtrlHGen | 9.33 | 0.1440 | 0.839 |
| HypoAgent | 4.27 | 0.014 | 0.945 |

[확인] 실험은 A6000 48GB 1장에서 돌렸다(`:208`).

### 지금 쓸 수 있는가

[확인] MIT 라이선스이고 README 가 셋 중 가장 자세하다. SharePoint 에 데이터·체크포인트가 있다. 걸림돌은 셋이다.
- README 가 복사하라는 `akgr/configs/api_keys.yml.example` 이 저장소에 없다.
- `./hug_model` 도 없다.
- HF 공개 요청 issue #1 이 열려 있다.

### 이 저장소가 말하는 "LLM 시대 KG"

LLM 은 KG 위 논리 구조를 직접 쓰지 말고, KG 실행 결과를 읽어 소형 생성기의 조건을 고치는 감독자 역할을 한다.

## 논문과 코드가 다른 곳

**필수: HypoAgent 공개 코드는 멈춤·선택 판단을 test 그래프로 한다.**

[확인] 논문은 "All inference-time diagnosis, candidate validation, selection, and stopping use only G_train" 이라고 적는다(`sources/2605.31370.txt:204`). 그런데 코드의 `compute_metrics` 는 `searching_split` 기본값이 `"test"` 다(`tools.py:285-290`).

[확인] `loop.py:292`(초기 가설)와 `:635`(후보)가 split 을 넘기지 않고 `compute_metrics` 를 부른다. 그 Jaccard 로 멈추고(`:315`, `:645`) 후보를 고른다(`:656-663`). `multi-turn.py:145`, `uncondition.py:54`, `:217` 도 같다. 이 코드로 재현하면 숨긴 간선 정보가 선택에 새어 들어간다. 표의 수치가 이 코드로 나왔는지는 모른다.

**참고: "GPT2_6" 생성기는 실제로 12층일 가능성이 높다.**

[확인] 설정은 `num_layers: 6` 을 `GPT2Config.from_pretrained('./hug_model', ...)` 에 넘긴다(`config-model.yml:7-8`, `transformer.py:68-73`).

[확인] 고정 버전 transformers 4.50.2 에서 `GPT2Config(num_layers=6)` 을 만들어 봤다. 결과는 `n_layer=12` 였다. `num_layers` 는 별도 속성으로만 붙고 층 수를 바꾸지 않는다(실행 확인함).

[추정] 실제 층 수는 `hug_model/config.json` 의 `n_layer` 를 따른다. 그 파일이 HF gpt2 기본 설정이면 12층이다. 근거 1개: CtrlHGen 논문은 "12 layers" 라고 쓰고(`sources/2505.20948.txt:203`) HypoAgent 논문은 "6-layer" 라고 쓴다(`sources/2605.31370.txt:207`).

**참고: CtrlHGen RL 스크립트의 보상 가중치가 논문과 다르다.**

[확인] 논문은 λ=1.0, 0.5, 0.5 이고 조건 준수 보상이 있다(`sources/2505.20948.txt:739`). 그런데 `scripts/optim/wn-g2.sh` 는 `--rl_factor='[1.0, 1.0, 0.5, 0.0]'` 이다. 넷째 값이 조건 항의 가중치인데 0 이다(`main.py:481-489`). 나머지 스크립트는 열어 보지 않았다.

## KG 를 만드는 사람에게 2026년 이 갈래가 주는 것

**KG 를 만들거나 빈칸을 채우는 도구는 없다.**

[확인] 셋 다 출력이 질의이고, triple 을 내지 않는다. 입력 KG 도 PyKEEN 벤치마크로 고정이다. schema·타입·텍스트 속성은 쓰지 않는다. LLM 으로 만든 KG 처럼 잡음이 있는 KG 에서 시험한 결과는 없다.

**쓸 만한 것 1 — 엔티티 집합을 설명하는 질의 찾기.**

[확인] 사용자가 고른 엔티티 묶음에 대해 "이들이 공통으로 가진 구조"를 FOL 질의로 내놓는다. 그 질의를 KG 에서 실행해 맞는지 확인한다.

[추정] 만든 KG 의 품질 점검에 쓸 수 있다. 같은 부류여야 할 엔티티 묶음을 넣었는데 설명 질의의 Jaccard 가 낮게 나오면, 그 부류를 묶는 관계가 KG 에 빠져 있다는 신호다.

근거는 2개다. 시험 데이터가 일부러 숨긴 간선을 거쳐야 닿는 답을 관측에 섞는다. 그리고 HypoAgent 의 `execute_and_diagnose` 가 놓친 답(FN)을 따로 뽑는다(`tools.py:1051-1091`). 이 FN 을 누락 triple 후보로 바꾸는 코드는 없다.

**쓸 만한 것 2 — 학습 없이 옮길 수 있는 KG 진단 도구.**

[확인] HypoAgent 의 `graph_validation`, `incoming_edge_intersection`, `intersection_candidates` 는 그래프 순회만 한다. networkx 그래프 하나와 id↔이름 표만 있으면 자기 KG 에 붙일 수 있다.

[확인] 학습 모델 없는 Symbolic Search 도 Jaccard 0.42–0.50 을 낸다(`sources/2605.31370.txt:226`). 소형 생성기를 다시 학습하기 전에 출발점으로 쓸 수 있다.

**쓸 만한 것 3 — 역할 분담에 대한 실험 근거.**

[확인] LLM 이 그래프 문맥을 받고 가설을 직접 쓰면 Jaccard 가 매우 낮다. GPT-4o 는 2.4, GPT-5 thinking 은 18.7 이다. 같은 도구를 쥔 ReAct agent 는 0.22–0.41 이다. LLM 이 조건만 고치고 구조는 전용 생성기와 실행기에 맡기면 0.83–0.95 다.

[추정] KG 위 구조 작업은 LLM 이 쓰게 하지 말고 실행 가능한 형식으로 검증하는 편이 낫다. 근거 3개: CtrlHGen 표 2, DARK 표 1, HypoAgent 표 1 이 같은 방향이다. 다만 셋 다 같은 연구실의 같은 과제이고, LLM 쪽 프롬프트 설계도 그 연구실이 했다.

**한계.**

[확인] 생성기는 KG 하나에 묶인다. 엔티티 id 가 어휘이기 때문이다. KG 가 바뀌면 샘플링과 학습을 다시 해야 한다. 샘플링 규모는 학습 간선 수를 scale 로 나눈 값을 패턴마다 뽑는 식이다(`sample_parallel.py:183-187`). 계속 자라는 KG 에는 맞지 않는다.

## 확인 못 한 것

- 코드를 돌려 논문 수치를 재현하지 않았다. 데이터·체크포인트를 받지 않았다.
- HypoAgent 표가 test 그래프로 선택하는 공개 코드로 나왔는지는 모른다. 저자 실행 로그나 이전 커밋(`ca5b5f4` 이전)과 비교하면 알 수 있다.
- `hug_model/config.json` 의 실제 `n_layer` 를 모른다. 공개 체크포인트의 state_dict 키 수를 세면 알 수 있다.
- DARK 의 self-reflective 단계가 KG 를 실행하는지 모델이 결론을 생성하는지는 `generation_utils.py` 를 읽으면 알 수 있다.
- BioKG·PharmKG8k 의 엔티티·관계 수를 확인하지 못했다.
- CtrlHGen 의 다른 RL 스크립트 가중치는 보지 않았다.

## 출처

- 클론: `lab/repos/{HypoAgent,CtrlHGen,DARK,AbductiveKGR}` (HEAD 는 각각 `4c0af3d`, `3f65801`, `612d344`, `23450d1`)
- 논문 원문: `lab/sources/04-reasoning/{2505.20948,2510.11462,2605.31370,2312.15643}.{html,txt}`. txt 는 arXiv HTML 을 텍스트로 바꾼 것이고, 위 줄 번호는 이 txt 기준이다
- 저장소 메타·커밋 이력: `lab/sources/04-reasoning/meta-{HypoAgent,CtrlHGen,DARK}.txt`
- GitHub issues: `gh api repos/HKUST-KnowComp/<name>/issues?state=all` (2026-10-10)

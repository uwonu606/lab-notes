# ISO-RAG는 schema·용어집이 없는 passage 그래프 검색기이고, 허브 억제 장치만 가져올 만하다

ISO-RAG(arXiv 2609.00513)는 multi-hop QA용 그래프 검색 방법이다.
그래프의 node는 passage 하나다.
edge는 "같은 QA 문제의 context에 함께 나온 passage 쌍"이다.
LLM 추출, 엔티티, schema, 용어집이 모두 없다.
그래서 A·B·E·G 축에는 답이 없다.

사용자 목표에 주는 답은 F 하나다.
검색 시점에 node마다 미리 계산한 점수 φ(국소 Cheeger 비율)를 보고, 양 끝의 φ 차이가 큰 edge를 자른다.
그 뒤 남은 국소 그래프에서 PPR을 돌린다.
2WikiMultihopQA에서 이 필터가 recall을 약 71%에서 87%로 올렸다고 한다.
무작위 φ로 자르면 효과가 없었다고 한다.

다만 그 수치는 그대로 믿기 어렵다.
[확인] 공개 코드는 평가 질문과 그래프를 같은 train 인스턴스에서 만든다(`dataset.py:14`, `dataset.py:56-78`).

[추정] 그래서 각 질문의 정답 passage끼리 이미 직접 이어져 있다. 허브 edge를 자르면 "자기 질문의 clique" 안에 머물게 되어 recall이 오를 수 있다. 사례는 이 코드 경로 1개다.

[확인] hyperbolic 부분을 뺀 "개수만 센 Cheeger 비율"은 ablation에 없다. 그래서 학습된 encoder가 꼭 필요한지는 모른다.

[확인] 저장소에는 ISO-RAG 검색 구현이 둘 있다. 논문 식과 맞는 쪽(`retrieval_isorag.py`)은 README의 기본 실행 경로가 아니다. README가 부르는 쪽(`retrieval_utils.py`)은 논문 §3.4가 배제한 random walk 방식이다.

## 한 바퀴 흐름

문서 하나가 들어가 페이지·엔티티가 되는 과정은 없다.
대신 QA 인스턴스 하나가 그래프에 들어가 검색되기까지를 적는다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. 그래프 | 인스턴스의 context passage마다 title을 node로 넣는다. 같은 인스턴스의 passage끼리 모두 edge로 잇는다(clique). | `dataset.py:55-65` |
| 2. node 텍스트 | title을 처음 본 인스턴스의 문장만 저장한다. | `dataset.py:57-58` `if ctx_title not in node_texts:` |
| 3. 평가 정답 | 같은 인스턴스의 question과 supporting_facts title을 평가 질문·정답으로 저장한다. | `dataset.py:74-78` |
| 4. 임베딩 | passage와 질문을 text-embedding-v3로 미리 임베딩한다. | `generate_embeddings.py:38-52`, 논문 §4.1 |
| 5. encoder 학습 | graph edge로 triplet(anchor, 이웃, 비이웃)을 만들어 Poincaré ball 사상 encoder를 학습한다. | `train.py:47-58`, 논문 §3.3 |
| 6. φ 계산 | node마다 닫힌 1-hop 이웃의 부피 합과 2-hop 경계의 부피 합을 구해 비율을 낸다. 부피는 conformal factor `(2/(1-‖x‖²))²`다. | `cheeger_calc.py:8-19`, `cheeger_calc.py:84-104` |
| 7. seed | 질문과 cosine이 높은 top-k passage를 seed로 고르고 softmax로 가중한다. | `retrieval_isorag.py:94-111` |
| 8. 후보 | dense top-N에 seed의 이웃 중 φ가 맞는 것을 더한다. | `retrieval_isorag.py:114-152` |
| 9. edge 필터 | 후보 안의 edge 중 `min(φu,φv)/max(φu,φv) ≥ floor`인 것만 남긴다. | `retrieval_isorag.py:86-91`, `:155-171` |
| 10. PPR + 융합 | 걸러진 그래프에서 PPR을 돌리고 dense 점수와 선형 결합해 top-k를 낸다. | `retrieval_isorag.py:174-235` |

## 축별 분석

### A schema

없음.
[확인] 그래프에는 node 종류도 edge 종류도 하나뿐이다. node는 passage title이고 edge는 무명 co-occurrence다(`dataset.py:16`의 `nx.Graph()`, `:65`의 `G.add_edge`).
[확인] 논문도 "rather than building a traditional entity-relation knowledge graph, we construct a question-induced passage co-occurrence graph"라고 적는다(§4.1).

### B 용어집

없음.
[확인] 별칭·정식 이름을 다루는 코드가 없다. `grep -rn "alias\|schema\|entity"`는 baseline 파일 밖에서 세 곳만 찾았다. 답변 프롬프트 문구(`config.py:209`), 주석 처리된 프롬프트(`generate.py:267`), LLM 모델 이름 별칭(`llm_client.py:89` "Resolve the provider-facing model name from config aliases")이다. 셋 다 용어와 무관하다.
[확인] node의 동일성은 데이터셋이 준 Wikipedia title 문자열 일치뿐이다(`dataset.py:57` `if ctx_title not in node_texts`).

### C 원문 연결 범위

단위는 passage다.
edge는 나온 모든 곳에서 걸린다.
텍스트는 처음 본 곳만 남는다.

- [확인] 인스턴스마다 clique를 새로 더한다. 그래서 한 title이 여러 인스턴스에 나오면 그 모든 인스턴스의 passage와 이어진다(`dataset.py:62-65`).
- [확인] node 텍스트는 첫 등장 것만 저장한다(`dataset.py:57-58`). 같은 title이 다른 문장으로 다시 나와도 버려진다.
- [추정] 사용자의 직전 실험과 모양이 같다. "모든 등장으로 연결"이 허브를 만든다. ISO-RAG의 허브는 여러 질문의 context에 반복해 나오는 passage다. 근거는 논문 §3.1 "such co-occurrence graphs ... inherently introduce noisy shortcuts and hub-like regions" 1개다.

### D 새/기존 연결

새 문서를 기존 그래프에 붙이는 절차가 없다.

- [확인] `build_graph.py`는 실행할 때마다 timestamp 폴더를 새로 만들고 그래프를 처음부터 다시 짓는다(`build_graph.py:19-22`).
- [확인] 새 passage가 기존 node와 이어지는 유일한 경로는 "같은 QA 인스턴스의 context에 함께 나옴"이다. 즉 이미 붙은 질문-context 라벨이 있어야 edge가 생긴다.
- [확인] φ는 2-hop 이웃에 의존한다(`cheeger_calc.py:93-99`). encoder도 graph edge로 학습한다(`train.py:47-58`). 그래서 node 하나가 늘면 주변 φ와 encoder를 다시 계산해야 한다. 증분 갱신 코드는 없다.
- 찾아본 곳: `dataset.py`, `build_graph.py`, `build_cheeger_map.py`, `train.py`, `hub_cache.py`, `retrieval_isorag.py`. `add_node`는 `dataset.py`에만 있다.

### E 새 용어

없음.
[확인] 용어 개념이 없다. 새 title이 나오면 무조건 node로 추가된다(`dataset.py:59` `G.add_node(ctx_title)`). 승인 대기열도 버림 규칙도 없다.

### F 범용어 허브

있다. 이 논문의 본론이다.
장치는 "node마다 φ를 미리 계산 → 검색 때 후보 그래프에서 φ 비율이 floor 미만인 edge 제거"다.

**φ의 정의**
- [확인] φ(v) = 경계 부피 / 내부 부피다. 내부는 v와 1-hop 이웃이다. 경계는 2-hop에 처음 닿는 node다(`cheeger_calc.py:90-104`, 논문 식 8-10).
- [확인] 각 node의 부피는 hyperbolic conformal factor다. 논문은 "generic semantic hubs at the origin are tightly compressed into minimal conformal volumes"라고 주장한다(§3.3).
- [확인] 논문은 허브가 "extremely large values"를 낸다고 쓴다(§3.3 식 10 뒤).

**edge 필터**
- [확인] `is_phi_compatible`는 두 끝의 φ 비율 `lo/hi`가 `phi_ratio_floor` 이상일 때만 edge를 남긴다(`retrieval_isorag.py:86-91`).
- [확인] 필터는 두 곳에 걸린다. seed 이웃을 후보에 넣을 때(`:128-145`)와 후보 사이 edge를 남길 때(`:155-167`)다.
- [확인] 모두 지우면 원 그래프의 부분 그래프로 돌아간다(`:169-170`). 빈 그래프를 막는 안전장치다.
- [확인] floor는 데이터셋마다 손으로 정했다. HotpotQA 0.35, MuSiQue 0.1, 2Wiki 0.30이다(`retrieval_isorag.py:21-55`). 논문은 "validation-tuned tolerance threshold"라고 쓴다(§3.3 식 11).

**전역 차단이 아니다**
- [확인] 허브 node를 지우지 않는다. 비슷한 φ끼리의 edge는 남는다. 그래서 허브끼리는 계속 이어진다.
- [확인] 필터는 질문마다 만든 후보 그래프 안에서만 돈다. 원 그래프는 그대로다.
- [확인] 단순 차수 기준(degree > 50)도 코드에 있다. 하지만 `hub_cache.py:4-9`와 장난감 예제 `retrieval_showdown.py:53-60`에만 있다. 아래 두 검색 경로 어느 쪽도 쓰지 않는다.

**검색 구현이 둘이다**
- [확인] 위 edge 필터(`retrieval_isorag.py`)는 논문 식 11과 §3.4의 deterministic PPR에 맞는다. 이 파일은 `run_hotpotqa_arg_ppr.py`, `ablate_isorag_components.py`, `probe_hyperbolic_signal.py`, `sweep_isorag_*.py`가 부른다.
- [확인] 그런데 README 5단계의 `run_retrieval_pipeline.py`는 ISO-RAG로 `run_full_evaluation.py`를 돌린다(`run_retrieval_pipeline.py:56-66`). 이 파일은 `retrieval_utils.isoperimetric_bounded_ppr`를 쓴다(`run_full_evaluation.py:14`, `:159-168`).
- [확인] `isoperimetric_bounded_ppr`는 Monte Carlo random walk다. 걷다가 다음 node의 φ가 지금보다 상대적으로 γ 넘게 떨어지면 그 걸음을 끊는다(`retrieval_utils.py:22-49`, `relative_delta >= -gamma`). 대칭 비율 floor가 아니라 한 방향 하락 기준이다. γ는 0.9다(`config.py:61`, `:72`).
- [확인] 논문 §3.4는 이 방식을 명시적으로 배제한다. "Rather than relying on stochastic random walks that introduce approximation variance, we compute π(q) deterministically via power iteration."
- [확인] 두 경로는 결과를 같은 파일 이름 `retrieval_results_arg_ppr.json`에 쓴다(`retrieval_isorag.py:258-261`, `run_full_evaluation.py` 저장부). QA 단계도 이 이름을 읽는다(`run_qa_pipeline.py:45`).
- 모르는 것: 표 2의 ISO-RAG 수치가 어느 경로에서 나왔는지는 저장소만으로 알 수 없다. 결과 산출물(artifacts)이 공개되지 않았기 때문이다.

**사용자 설정에 옮길 때**
- [추정] 사용자의 허브는 용어 node(KG, schema, LLM)다. ISO-RAG의 허브는 passage node다. chunk-용어 이분 그래프에 옮기면 용어 node의 φ가 크게 나올 것이다. 2-hop 경계가 거의 모든 chunk이기 때문이다. 근거는 φ 정의 1개이고 실행해 보지 않았다.
- [추정] hyperbolic encoder 없이 부피를 1로 두면 φ는 "2-hop 경계 node 수 / 닫힌 1-hop node 수"가 된다. 이 값은 그래프만으로 계산된다. 하지만 이 변형의 효과는 논문도 코드도 재지 않았다(H 참고).

### G 엔티티·이벤트

없음.
[확인] 엔티티도 이벤트도 시간축도 뽑지 않는다. 그래프는 passage만 다룬다(§3.1 "each node represents a passage").
[추정] 논문 §1의 "Poptropica to Pearson" 같은 "target entity" 표현은 passage title을 가리킨다. 논문은 이를 직접 밝히지 않는다. 근거는 MuSiQue paragraph가 Wikipedia title을 node 이름으로 쓴다는 코드 경로 1개다(`dataset.py:127-136`).

### H 근거 수치

논문 수치는 있다.
재현 조건에는 큰 의문이 네 가지 있다.

**논문이 보고한 수치**

| 항목 | 값 | 출처 |
|---|---|---|
| 2Wiki R@5 | ISO-RAG 88.10, LightRAG 77.93, HippoRAG2 70.18, Vanilla PPR 69.05 | 표 2 |
| 2Wiki P@5 | ISO-RAG 40.10, LightRAG 35.92, Vanilla PPR 31.80 | 표 2 |
| MuSiQue R@5 | ISO-RAG 74.75, Vanilla PPR 70.10, HippoRAG2 63.85 | 표 2 |
| HotpotQA R@5 | ISO-RAG 88.05, LightRAG 87.30 | 표 2 |
| ablation (2Wiki만) | real_phi 최고 recall 87.28%, precision 40.44%. uniform_phi·random_phi는 "stagnate at 71-72%" | §4.4 |
| 잘린 edge 비율 | real_phi는 32% 제거로 최고. shuffled_phi는 최대 75% 제거하고 성능이 크게 떨어짐 | §4.4 |
| 지연 | MuSiQue에서 ISO-RAG 14.2ms/질문, HippoRAG2 117.2ms | 표 3 |

**의문 1: 평가 질문이 그래프를 만든 인스턴스와 같다**
- [확인] 논문은 "randomly sample 1,000 instances from the validation set"과 "passage co-occurrence graphs are constructed exclusively using the training splits"라고 쓴다(§4.1).
- [확인] 공개 코드는 세 데이터셋 모두 `split="train"`만 읽는다(`dataset.py:14`, `:93`, `:174`).
- [확인] 같은 루프에서 그 인스턴스의 context로 clique를 만들고, 그 인스턴스의 question을 평가 질문으로 넣는다(`dataset.py:56-78`).
- [확인] 그래프용 샘플 수는 `TEST_LIMIT` 변수를 그대로 쓴다(`build_graph.py:17` `num_samples = config.TEST_LIMIT`). 값은 1000이다(`config.py:285`). 검색 코드도 같은 `queries.json`을 읽는다(`retrieval_isorag.py:253`, `:280-281`). 그래서 그래프의 모든 인스턴스가 평가 질문이다.
- [확인] 논문은 "randomly sample 1,000 instances"라고 쓴다(§4.1). 코드는 train split을 streaming으로 열어 앞에서부터 차례로 읽는다(`dataset.py:14`, `:22`, `:30-32`). 섞는 코드는 없다.
- [추정] 그러면 각 질문의 정답 passage들은 서로 1-hop 이웃이다. seed 하나만 맞으면 나머지 정답이 바로 옆에 있다. 허브 edge를 자르면 다른 질문의 clique로 새는 것만 막는다. 이 구조가 71% → 87%의 상당 부분을 설명할 수 있다. 사례는 이 코드 경로 1개다. 공개되지 않은 별도 평가 코드가 있을 수도 있다.
- 알 수 있는 방법: train으로 그래프를 짓고 validation 질문으로 평가하는 경로가 저장소에 있는지 본다. 지금 commit에는 없다.

**의문 2: ablation이 한 데이터셋, 한 비교군에 묶여 있다**
- [확인] 논문은 2Wiki를 고른 이유를 "where the impact of geometric guidance is most pronounced"라고 적는다(§4.4). 효과가 가장 큰 곳을 골랐다는 뜻이다.
- [확인] ablation의 최고점은 β=0.40에서 나왔다(§4.4 "87.28% peak recall and 40.44% peak precision at β=0.40"). 코드의 2Wiki 기본 floor는 0.30이다(`retrieval_isorag.py:53`). 표 2의 2Wiki R@5 88.10이 어느 β에서 나왔는지는 본문에 없다.
- [확인] MuSiQue의 floor는 0.1이다(`retrieval_isorag.py:42`). 10배 차이까지 허용하므로 자르는 edge가 적을 것이다. 그런데 MuSiQue의 ablation 수치는 없다.
- [확인] uniform_phi는 φ를 모두 1.0으로 둔다(`ablate_isorag_components.py:68`, `probe_hyperbolic_signal.py:82-83`). 이것은 "필터 없음"이다. "hyperbolic 부피 없이 개수만 센 φ"가 아니다.
- [확인] 그래서 "학습된 hyperbolic encoder가 필요하다"는 주장과 "φ 비율 필터 자체가 효과가 있다"는 주장이 분리되지 않았다.
- [확인] random_phi는 실제 φ의 최소~최대 사이 균등 난수다(`probe_hyperbolic_signal.py:95-104`). shuffled_phi는 실제 값을 섞는다(`:86-92`). 둘 다 seed가 고정된 1회다.

**의문 3: baseline이 원래 시스템이 아니다**
- [확인] GraphRAG baseline은 "each passage node acts as the closest available entity proxy"라고 적는다(`baseline_microsoft_graphrag.py:18-22`, `:130-136`).
- [확인] LightRAG baseline은 "artifact-limited hybrid approximation over the existing passage graph"다(`baseline_lightrag.py:9-12`).
- [확인] HippoRAG2 baseline은 "Simulates the core graph retrieval logic"이다(`baseline_hipporag.py:2-3`).
- [확인] 논문 본문 §4.1의 Baselines 단락은 이 점을 밝히지 않는다. 원 시스템 이름과 인용만 단다. 부록은 HTML에 없어 확인하지 못했다.
- [추정] 따라서 표 1·2의 비교는 "같은 passage co-occurrence 그래프 위의 검색 규칙 비교"다. 엔티티 추출 기반 시스템과의 비교가 아니다. 사례는 baseline 파일 3개다.

**의문 4: README 파이프라인이 논문과 다른 알고리즘을 돌린다**
- [확인] README 5단계는 `retrieval_utils.py`의 Monte Carlo random walk 변형을 돌린다. 논문 식 11의 대칭 φ 비율 필터와 deterministic PPR은 `retrieval_isorag.py`에 따로 있다. 자세한 근거는 F의 #검색 구현이 둘이다에 적었다.
- [확인] 두 경로가 같은 결과 파일 이름에 쓴다. 그래서 표 2가 어느 쪽에서 나왔는지 저장소만으로 가릴 수 없다.

**그 밖의 불일치**
- [확인] 초록은 "training-free"라고 쓴다. 본문 §3.3은 encoder를 "trained offline via a graph-supervised margin-based triplet loss"라고 쓰고, 결론도 "training a geometry-aware encoder"라고 쓴다. 코드에도 `train.py`가 있다.
- [확인] 논문의 부피 지수는 "tunable scaling exponent"다(§3.3). 코드는 2로 고정이다(`cheeger_calc.py:18`).

## 가져올 것

**문제**: 용어집이 이름을 한곳으로 모으자 범용 용어 node가 허브가 됐다. 연결 정밀도가 0.62에서 0.37로 떨어졌다.

**제안: φ 비율 edge 필터를 chunk 그래프에 싸게 시험한다**
- chunk-chunk 그래프(공유 용어로 이음)에서 node마다 φ = |2-hop 경계| / |닫힌 1-hop|을 계산한다. 부피는 1로 둔다.
- 링크 후보 edge마다 `min(φu,φv)/max(φu,φv)`가 floor 미만이면 뺀다. floor는 0.1, 0.2, 0.3을 돌려 본다.
- 직전 실험의 정답 쌍으로 연결 재현율·정밀도를 다시 잰다.
- 근거: [확인] 계산이 그래프 구조만 쓴다(`cheeger_calc.py:86-104`에서 conformal factor를 1로 두면 개수 비율이 된다). [추정] 허브 용어를 공유해서 생긴 edge는 φ 차이가 크다. 사례는 φ 정의 1개다.
- 포기하는 것: hyperbolic encoder 학습이 주는 효과(있다면)를 버린다. 대신 논문 ablation이 재지 않은 칸을 직접 잰다.

**제안: 비교군으로 df 가중을 같이 돌린다**
- `19-tentative-links.md`가 이미 다룬 1/log(df) 가중이나 Block Purging과 같은 데이터에서 비교한다.
- 근거: [추정] φ 필터와 df 가중은 둘 다 "흔한 것을 덜 믿는다"를 다른 단위로 한다. φ는 node 이웃 구조로, df는 용어 등장 수로 본다. 사례는 두 정의 각 1개다.
- 포기하는 것: 실험 한 회차가 늘어난다.

**참고: 가져오지 않을 것**
- passage co-occurrence edge는 QA 라벨이 있어야 생긴다. 사용자의 문서에는 그런 라벨이 없다.
- 이 저장소에는 LICENSE 파일이 없다. 코드를 그대로 복사하면 안 된다. 아이디어와 수식만 다시 구현한다. 논문 본문은 CC BY 4.0이다.

## 출처

| 대상 | 위치 |
|---|---|
| 논문 | ISO-RAG: Isoperimetric Noise Control for Retrieval-Augmented Generation. Siyuan Zhang, Hanchen Wang, Dong Wen, Ying Zhang, Wenjie Zhang. arXiv:2609.00513v1, 2026-09-01. https://arxiv.org/abs/2609.00513 (HTML 본문 https://arxiv.org/html/2609.00513 을 읽음, 부록은 HTML에 없어 읽지 못함) |
| 논문 라이선스 | CC BY 4.0 (arXiv abs 페이지 표기) |
| 코드 | https://github.com/ZaiizaiZHANG/ISO-RAG |
| commit | `8c09dccfcc7816e2569214a39f4d1f3883606944` (2026-04-30, "Initial commit") |
| 로컬 사본 | `llm-wiki-implementations/lab/repos/ZaiizaiZHANG_ISO-RAG` (`git clone --depth 1`, 실행하지 않음) |
| 코드 라이선스 | 없음. 저장소에 LICENSE 파일이 없고 GitHub API의 licenseInfo도 null이다. |
| 관련 노트 | `autoschemakg-kg-construction/lab/reports/19-tentative-links.md:142` (HippoRAG node specificity, df 가중) |

## 검증 기록

검증은 2026-10-11에 했다.
로컬 사본은 commit `8c09dcc`이다.
논문은 arXiv HTML 본문(https://arxiv.org/html/2609.00513)과 abs 페이지를 다시 받아 읽었다.
코드는 읽기만 했고 실행하지 않았다.

**그대로 맞은 것**

| 주장 | 다시 본 곳 |
|---|---|
| schema 없음. node 한 종류, edge 한 종류 | `dataset.py:16`, `:59`, `:65`. 논문 §4.1 "rather than building a traditional entity-relation knowledge graph" |
| 용어집 없음. title 문자열 일치만 | `dataset.py:57`. 그래프를 바꾸는 코드는 `dataset.py`의 `add_node`/`add_edge`와 질문별 필터 그래프(`retrieval_isorag.py:157`, `:167`)뿐 |
| 사람이 정한 schema·용어집도, LLM이 만든 것도 없음 | 위 두 줄. LLM 호출은 임베딩(`generate_embeddings.py`)과 답 생성(`generate.py`)에만 있다 |
| 원문 연결 범위. 인스턴스마다 clique, 텍스트는 첫 등장만 | `dataset.py:55-65`, `:57-58` |
| 증분 연결 없음. 매번 새 폴더에 처음부터 | `build_graph.py:19-22`, `:32-36` |
| φ 정의와 부피 지수 2 고정 | `cheeger_calc.py:8-19`, `:84-104`. 논문 식 6-10, "tunable scaling exponent p" |
| edge 필터와 데이터셋별 floor 0.35/0.1/0.30 | `retrieval_isorag.py:21-55`, `:86-91`, `:155-171`. 논문 식 11 |
| encoder triplet 학습 | `train.py:47-58`. 논문 §3.3 "trained offline via a graph-supervised margin-based triplet loss" |
| train split만 읽고 평가 질문도 같은 인스턴스 | `dataset.py:14`, `:93`, `:174`, `:74-78`. 논문 §4.1 "constructed exclusively using the training splits" |
| ablation 변형 정의 | `ablate_isorag_components.py:68`, `probe_hyperbolic_signal.py:82-83`, `:86-92`, `:95-104` |
| baseline 근사 재구현 | `baseline_microsoft_graphrag.py:18-22`, `:130-136`, `baseline_lightrag.py:9-12`, `baseline_hipporag.py:2-3` |
| 표 2·표 3 수치, §4.4 수치 | 2Wiki R@5 88.10 / LightRAG 77.93 / HippoRAG2 70.18 / Vanilla PPR 69.05, P@5 40.10 / 35.92 / 31.80, MuSiQue R@5 74.75 / 70.10 / 63.85, HotpotQA 88.05 / 87.30, MuSiQue 지연 14.2ms / 117.2ms, ablation 87.28% / 71-72% / 32% / 75% 모두 일치 |
| "training-free" 불일치 | 초록 "a training-free, purely topology-driven RAG framework" vs §3.3, §5 "training a geometry-aware encoder" |
| 라이선스 | abs 페이지가 creativecommons.org/licenses/by/4.0 을 가리킨다. 저장소에 LICENSE 파일이 없다 |

**고친 것**

| 위치 | 전 | 후 | 근거 |
|---|---|---|---|
| B 용어집 | grep이 baseline 밖에서 `config.py:209`만 찾았다 | 세 곳을 찾았고 셋 다 무관하다 | `generate.py:267`, `llm_client.py:89`도 걸린다 |
| F 범용어 허브 | `retrieval_isorag.py`를 유일한 본 파이프라인처럼 적었다 | #검색 구현이 둘이다 를 더했다 | `run_retrieval_pipeline.py:56-66`이 `run_full_evaluation.py`를 부르고, 그 파일은 `retrieval_utils.py:22-49`의 random walk를 쓴다. 논문 §3.4는 random walk를 배제한다 |
| G 엔티티·이벤트 | Poptropica 예가 passage title을 가리킨다고 [확인] | [추정]으로 내렸다 | 논문은 "target entity"라고만 쓴다 |
| H 의문 1 | `TEST_LIMIT`과 그래프 샘플 수가 "둘 다 1000" | 같은 변수다. 논문의 "randomly sample"과 달리 앞에서부터 읽는다 | `build_graph.py:17`, `dataset.py:14`, `:22`, `:30-32` |
| H 의문 2 | floor 0.30만 적었다 | ablation 최고점은 β=0.40이라고 더했다 | §4.4 "at β=0.40" |
| H 의문 3 | §4.1이 baseline 근사를 밝히지 않는다 | 본문 기준이고 부록은 못 읽었다고 한정했다 | 부록이 HTML에 없다 |
| H | 의문 세 가지 | 의문 4(README 경로가 논문과 다른 알고리즘)를 더했다 | 위 F 항목과 같다 |

**판정**

후보는 사람이 정한 schema도 용어집도 쓰지 않는다.
LLM이 자동으로 만드는 schema·용어집도 없다.
허브 억제 장치(F)만 참고 가치가 있다.

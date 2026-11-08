# 관계는 이름보다 근거 붙은 서술로 먼저 남기고, 자주 모이는 서술만 나중에 이름으로 올린다 — 문서 사이 관계를 미리 정하지 않고 찾는 방법은 아직 없다

이 갈래는 관계 종류를 미리 정하지 않고 (1) 열린 관계로 뽑고 (2) 같은 뜻의 관계 표현을 묶고 (3) 관계 목록을 쓰면서 키우는 방법을 찾았다. 문서 사이 관계(원인·후속·반박)도 함께 봤다. 이미 읽은 AutoSchemaKG·EDC·KGGen 등은 비교로만 이름을 든다.

## 출처 한눈에

| # | 이름 | 종류 | 연도 | 묶음 | 확인 상태 |
|---|---|---|---|---|---|
| 1 | ReVerb | 논문 | 2011 | 열린 추출 | 원문 읽음 (초록·1·3절) |
| 2 | CESI | 논문 | 2018 | 관계 표현 정규화 | 원문 읽음 (4·6·7·8절) |
| 3 | CMVC | 논문 | 2022 | 관계 표현 정규화 | 원문 읽음 (초록·1·3·4절) |
| 4 | llm-graph-builder `graph_schema_consolidation` | 레포 | 2026 커밋 | 관계 표현 정규화 | 코드 읽음 |
| 5 | RSN | 논문 | 2019 | 관계 종류 발견 | 초록만 (+3.4절 일부) |
| 6 | TABS (type abstraction) | 논문 | 2022 | 관계 종류 발견 | 원문 읽음 (1~4절) |
| 7 | ORELLM | 논문 | 2024 | 관계 종류 발견 | 원문 읽음 (1·2·3절) |
| 8 | DIAL-KG | 논문 | 2026 | 스키마 키우기 | 원문 읽음 (전체) |
| 9 | LLMs4OL | 논문 | 2023 | 스키마 키우기 | 원문 읽음 (초록·3·4절) |
| 10 | GraphRAG | 논문 | 2024 (v2 2025) | 이름 대신 서술 | 원문 읽음 (3.1절·부록 A) |
| 11 | LightRAG | 레포 | 2026 커밋 | 이름 대신 서술 | 코드 읽음 |
| 12 | Han & Lai, Symbolic → Natural-Language Relations | 논문(입장) | 2026 | 이름 대신 서술 | 원문 읽음 (1~5절) |
| 13 | CST (Radev) | 논문 | 2000 | 문서 사이 관계 | 원문 읽음 (1·4·5절) |
| 14 | Afantenos 외, cross-document relations | 논문 | 2004 | 문서 사이 관계 | 원문 읽음 (PDF 1~3·7~8쪽) |
| 15 | CRAB | 논문 | 2023 | 문서 사이 관계 | 원문 읽음 (1·3·6절) |

## 열린 추출

### 1. ReVerb — Fader, Soderland, Etzioni

- 링크: https://aclanthology.org/D11-1142.pdf (EMNLP 2011)
- 푸는 것: 관계 어휘 없이 문장에서 (명사구, 관계구, 명사구)를 뽑을 때 생기는 엉뚱한 관계구를 줄인다.
- 메커니즘: ReVerb는 관계구를 동사 중심 품사 패턴 `V | VP | VW*P`에 맞는 연속 구간으로만 받는다. 그다음 큰 말뭉치에서 서로 다른 인자 쌍 k개 이상과 함께 나온 관계구만 남긴다(k=20). 관계 목록은 없고, 문장의 동사구가 곧 관계 이름이다.
- 인용: "extracting assertions from massive corpora without requiring a pre-specified vocabulary" (초록). "a binary relation phrase ought to appear with at least a minimal number of distinct argument pairs in a large corpus" (1절). "the relation phrase must be a contiguous span of words in the sentence" (3.1절).
- 수치: 이전 추출기(TextRunner, WOE-pos)보다 precision-recall 곡선 아래 면적이 두 배 넘는다. 추출의 30% 이상이 precision 0.8 이상이다 (초록). 5억 개 웹 문장을 썼다.
- 옮길 때 걸리는 점: 품사 패턴이 영어 어순(동사+전치사)에 묶여 있다. [추정] 한국어는 서술어가 문장 끝에 오고 관계가 조사·어미에 실리므로 패턴을 새로 짜야 한다(사례: 3.1절 패턴이 전치사 P로 끝나는 구조 1개). k=20 빈도 필터는 문서 수가 적은 사내 위키에서는 대부분의 관계를 지운다.

## 관계 표현 정규화

### 2. CESI — Vashishth, Jain, Talukdar

- 링크: https://arxiv.org/pdf/1902.00172 (WWW 2018)
- 푸는 것: 열린 추출로 쌓인 명사구와 관계구를 같은 뜻끼리 묶는다.
- 메커니즘: CESI는 관계구마다 바깥 정보(PPDB 바꿔쓰기, WordNet, AMIE 규칙 마이닝, Stanford KBP 분류)를 모아 "이 둘은 같다"는 약한 신호로 쓴다. 이 신호를 벌점 항으로 넣어 KB 임베딩을 학습한다. 그다음 cosine 기반 계층 군집(HAC, complete linkage)으로 묶는다. 군집 수를 미리 정하지 않고 임계값으로 자른다.
- 인용: "HAC was preferred over other clustering methods because the number of clusters are not known beforehand." (6절). 대표 이름은 "NP or relation phrase which lies closest to the weighted cluster mean is chosen as the representative" (6절) — 빈도 가중 평균에 가장 가까운 표현이다.
- 수치: ReVerb45K(관계구 22K개)에서 관계 군집의 macro/micro/pairwise precision이 77.3/87.8/72.6이다. CESI는 군집 2,116개를 만들었다. AMIE는 51개만 만들었다 (표 3). 관계에는 정답이 없어서 사람 판정으로 precision만 쟀다 (7.2절).
- 옮길 때 걸리는 점: 바깥 정보 다섯 가지가 모두 영어 자원이다. 사내 문서 규모에서는 AMIE 규칙이 거의 나오지 않는다(원문에서도 51개). 관계 평가에 사람 판정이 필요하다는 점은 우리도 같다.

### 3. CMVC — Shen, Yang, Liu

- 링크: https://arxiv.org/pdf/2206.11130 (KDD 2022)
- 푸는 것: 트리플 자체(fact view)와 트리플이 나온 원문 문맥(context view)을 함께 써서 정규화한다.
- 메커니즘: CMVC는 두 관점의 임베딩을 따로 만든다. 두 관점이 서로의 군집 결과를 보강하는 multi-view k-means를 돌린다. 군집 수는 Log-Jump라는 라벨 없는 추정법으로 정한다. 시드 쌍은 바깥에서 자동으로 모으고, 군집 결과로 가짜 라벨을 만들어 문맥 인코더를 다시 학습한다.
- 인용: "two views of knowledge (i.e., a fact view based on the fact triple and a context view based on the fact triple's source context) provide complementary information" (초록). "we propose a Log-Jump algorithm to predict the optimal number of clusters in a data-driven way without requiring any labels" (초록).
- 수치: 관계구 정규화 평균 F1이 ReVerb45K 0.879, NYTimes2018 0.817, OPIEC59K 0.722이다. 같은 표에서 CESI는 ReVerb45K 0.795다 (4.2.2절 표).
- 옮길 때 걸리는 점: 관계구 정답이 어디서 왔는지는 이 원문에서 확인하지 못했다. [추정] 원문 문맥을 같이 쓰는 생각은 그대로 쓸 만하다(사례: 문맥 관점만으로도 평균 F1 0.708, 표 4). 사내 문서는 같은 관계구가 적게 반복되므로 문맥 쪽 비중이 더 커진다.

### 4. llm-graph-builder (Neo4j) — `graph_schema_consolidation`

- 링크: https://github.com/neo4j-labs/llm-graph-builder (로컬 `lab/repos/llm-graph-builder`, 커밋 `5ff7af3`)
- 푸는 것: 스키마 없이 LLM이 만든 관계 타입이 늘어나면, 끝난 뒤 한 번에 묶는다.
- 메커니즘: 그래프에 있는 관계 타입 이름 전체를 LLM 한 번에 넘긴다. LLM은 같은 뜻끼리 묶은 사전을 돌려준다. 코드는 Cypher로 옛 관계를 지우고 새 이름으로 다시 만든다 (`backend/src/post_processing.py:149-186`).
- 인용: "The name of each category must be chosen from the types in the input list ... **Do not create or infer new names for categories**." (`backend/src/shared/constants.py:835`). 같은 프롬프트의 예시는 `"PUBLISHED": ["PUBLISHED_BY", "PUBLISHED_IN", "PUBLISHED_ON"]`로 묶는다 (`constants.py:862`).
- 수치: 없다. 로그로 "Total = N, Reduced to = M"만 남긴다 (`post_processing.py:166-167`).
- 옮길 때 걸리는 점: 예시가 방향(`_BY`)과 대상 종류(`_IN`, `_ON`)가 다른 관계를 한 이름으로 합친다. "A가 B의 원인"과 "A가 B에 의해 생김"이 이렇게 합쳐지면 방향이 사라진다. 두 번째 예시는 입력에 없는 `USED`를 범주 이름으로 써서 자기 규칙을 어긴다 (`constants.py:877`). 기본 모델은 `openai_gpt_5.4_mini`이고 (`post_processing.py:157`), 관계 이름 전체 목록을 한 프롬프트에 넣으므로 작은 모델의 문맥 길이에서 먼저 막힌다.

## 관계 종류 발견 (군집)

### 5. RSN — Wu 외

- 링크: https://aclanthology.org/D19-1021.pdf (EMNLP 2019), 코드 https://github.com/thunlp/RSN
- 푸는 것: 이미 라벨이 있는 관계로 "두 문장이 같은 관계인가"를 배우고, 그 판단을 새 관계 발견에 옮긴다.
- 메커니즘: Siamese 네트워크가 두 관계 사례의 유사도를 배운다. 라벨 없는 말뭉치에서는 이 유사도로 그래프를 만들고 Louvain으로 군집을 찾는다. Louvain은 군집 수를 미리 받지 않는다 (3.4절).
- 인용: "learn similarity metrics of relations from labeled data of pre-defined relations, and then transfer the relational knowledge to identify novel relations in unlabeled data" (초록).
- 수치: TABS 논문 표 3에 따르면 TACRED 새 관계 10종에서 정확도 0.7645, FewRel 새 관계 16종에서 0.4880이다.
- 옮길 때 걸리는 점: 출발점으로 라벨 달린 관계 사례가 있어야 한다. 사내 문서에는 그런 라벨이 없다. [추정] 지금 만든 용어집 연결 결과에 사람이 관계 이름을 몇십 개 달면 그 라벨이 시작점이 될 수 있다(사례: RSN·TABS 모두 "알려진 관계"로 학습한 뒤 새 관계로 옮긴다, 2개).

### 6. TABS — Sha Li, Heng Ji, Jiawei Han

- 링크: https://aclanthology.org/2022.emnlp-main.461.pdf (EMNLP 2022), 코드 https://github.com/raspberryice/type-discovery-abs
- 푸는 것: 관계 사례마다 모델이 이름을 지어 보게 하고, 그 이름끼리의 거리로 새 관계 종류를 묶는다.
- 메커니즘: "⟨tail⟩ is the [MASK] of ⟨head⟩" 프롬프트의 [MASK] 자리 임베딩을 관계 표현으로 쓴다(mask view). 개체 토큰 임베딩(token view)도 따로 만든다. 두 관점이 서로의 군집 결과를 가짜 라벨로 가르치는 co-training을 한다. 한 사례에서 정확한 이름을 맞히길 요구하지 않고 이름 사이 유사도만 쓴다.
- 인용: "we introduce the idea of type abstraction, where the model is prompted to generalize and name the type. Then we use the similarity between inferred names to induce clusters." (초록). "When we assign a name to a cluster, we implicitly define the commonality of instances within the cluster and also the criteria for including new instances" (1절).
- 수치: 새 관계 정확도가 TACRED 0.8896, FewRel 0.8022이다 (표 3). 문제 정의에 "estimated number of unknown types |Cu|"가 들어 있어 군집 수 추정값을 입력으로 받는다 (2절).
- 옮길 때 걸리는 점: BERT 기반이고 알려진 관계로 먼저 학습해야 한다. 한국어에는 한국어 인코더와 시작 라벨이 필요하다. 그래도 "이름을 지어 보게 하고 이름끼리 묶는다"는 생각은 작은 생성 모델에도 옮길 수 있다 — ORELLM이 그 방향이다.

### 7. ORELLM — Jiaxin Wang 외

- 링크: https://aclanthology.org/2024.acl-long.709.pdf (ACL 2024)
- 푸는 것: LLM이 관계구를 직접 쓰고, 두 관계구가 같은 뜻인지를 다른 LLM의 생성 확률로 잰다.
- 메커니즘: API LLM(추출기)이 문장마다 5단어 이하 관계구를 쓴다. 작은 오픈 LLM(추정기, GPT2-XL 1.5B)이 "한 관계구가 다른 관계구를 생성할 확률"로 유사도 행렬을 만든다. 군집 중심에서 애매한 사례는 추출기에게 다시 생각하게 해 관계구를 고치고, 고친 구가 새 중심이 되면 군집을 늘린다. 믿을 만한 사례로 추정기를 미세조정하고, 오류가 늘면 멈춘다.
- 인용: "extracting relational phrases and directly exploiting the knowledge in LLMs to assess the semantic similarity between phrases without relying on any additional metrics" (초록). "assuming a known K is unrealistic, as it is unknown and constantly changes in the open world" (3.2절).
- 수치: ChatGPT가 쓴 관계구를 **문자열 일치**로만 묶으면 FewRel 정확도 13.05%, TACRED 22.81%다 (표 1). ORELLM(ChatGPT+GPT2-XL)은 군집 수를 모를 때 FewRel 46.03%, TACRED 52.55%다 (표 2).
- 옮길 때 걸리는 점: 관계구를 쓰는 쪽이 GPT-3.5/GPT-4다. 확률을 재는 쪽은 1.5B 모델이라 우리 조건에 맞는다. [추정] llama3.1:8b가 관계구 쓰는 쪽을 맡으면 관계구 품질이 떨어지지만 "다시 생각하기" 단계가 일부 메운다(사례: Rethink를 빼면 평균 3.26%/2.20% 하락, 3.3절). 문자열 일치 13%라는 수치는 LightRAG처럼 관계 키워드를 글자 그대로 모으는 방식의 한계를 보여 준다.

## 스키마를 쓰면서 키우기

### 8. DIAL-KG — Weidong Bao 외

- 링크: https://arxiv.org/pdf/2603.20059 (arXiv 2026-03)
- 푸는 것: 문서가 묶음으로 계속 들어올 때 관계·사건 스키마를 데이터에서 올리고, 낡은 사실은 지우지 않고 폐기 표시한다.
- 메커니즘: 첫 묶음은 스키마 없이 few-shot으로 뽑는다. 검증을 통과한 트리플의 관계 이름을 임베딩해 군집으로 묶는다. 군집이 빈도 임계값 θ를 넘고 의미가 고르면 관계 스키마 후보가 된다. LLM이 후보를 심사해 통과하면 Meta-Knowledge Base에 정식 스키마(domain/range 포함)로 올린다. 떨어진 후보는 제안 풀에 남아 데이터가 더 쌓이면 다시 심사받는다. 다음 묶음부터는 입력과 가까운 스키마 30개를 프롬프트에 제약으로 넣는다.
- 인용: "When a cluster's frequency exceeds a threshold θ and exhibits high semantic coherence, a relation schema candidate is generated. ... failed ones are kept in a proposal pool for re-evaluation with more data." (4.3절). "candidates for unseen schemas skip the schema-constraint check and proceed to dynamic induction" (4.2절).
- 수치: WebNLG F1 0.865, Wiki-NRE 0.853로 EDC(0.848, 0.808)보다 높다 (표 1). 관계 타입 수가 EDC보다 최대 15% 적다. EDC가 `acquired_by`와 `acquisition_of`를 따로 두는 반면 DIAL-KG는 하나로 합쳤다고 쓴다 (5.2절). 정확도는 DeepSeek-V3 판정자가 매긴 값이다 (5.4절).
- 옮길 때 걸리는 점: 생성은 Qwen-Max, 판정은 DeepSeek-V3로 둘 다 큰 모델이다. θ 값과 "의미가 고르다"의 기준은 원문에 숫자로 나오지 않는다. 저자도 작은 모델로 증류하는 일을 다음 과제로 남겼다 (6절). 그래도 "후보 풀 → 빈도 문턱 → 심사 → 승격" 구조는 모델 크기와 무관하게 옮길 수 있다.

### 9. LLMs4OL — Babaei Giglou, D'Souza, Auer

- 링크: https://arxiv.org/pdf/2307.16648 (ISWC 2023)
- 푸는 것: LLM이 온톨로지 학습의 세 과제(용어 타입 붙이기, 상하위 분류, 상하위가 아닌 관계)를 zero-shot으로 해낼 수 있는지 잰다.
- 메커니즘: 관계 과제(Task C)는 열린 발견이 아니다. "[h] is [r] [t]. This statement is [MASK]." 형태로 주어진 관계 r이 두 타입 사이에 성립하는지 참/거짓을 묻는다 (3절). 관계 이름은 UMLS의 53개를 그대로 쓴다.
- 인용: "foundational LLMs are not sufficiently suitable for ontology construction that entails a high degree of reasoning skills and domain expertise" (초록).
- 수치: Task C F1은 LLaMA-7B 20.3, GPT-4 41.3, Flan-T5-XL 49.5, 미세조정한 Flan-T5-XL 53.1이다 (표 3).
- 옮길 때 걸리는 점: 7B급 모델이 관계 성립 판정만 해도 F1 20 남짓이다. [추정] 작은 모델에게 관계 이름을 짓게 하기보다 "이 두 서술이 같은 관계인가"처럼 좁은 예/아니오를 묻는 편이 낫다(사례: 이 표에서 작은 모델 중 미세조정한 Flan-T5가 가장 높음 1개, ORELLM이 1.5B 모델로 유사도만 잼 1개).

## 관계를 이름 대신 서술로

### 10. GraphRAG — Edge 외 (Microsoft Research)

- 링크: https://arxiv.org/pdf/2404.16130 (v2, 2025-02)
- 푸는 것: 관계에 타입을 붙이지 않고, 두 개체가 왜 이어지는지 짧은 서술로 남겨 요약·검색에 쓴다.
- 메커니즘: LLM이 조각마다 개체 쌍과 "왜 관련 있는지"의 서술, 관계 강도 점수를 뽑는다. 같은 관계가 여러 번 나오면 하나의 간선으로 모으고, 중복 횟수를 간선 가중치로 쓴다. 서술은 간선마다 다시 요약한다.
- 인용: "relationship description: explanation as to why you think the source entity and the target entity are related to each other" (부록 A 프롬프트). "Relationships are aggregated into graph edges, where the number of duplicates for a given relationship becomes edge weights." (3.1.3절). "our analysis uses exact string matching for entity matching" (3.1.3절).
- 수치: 이 갈래와 관련된 관계 품질 수치는 없다. 평가는 질의 요약 답의 포괄성·다양성이다.
- 옮길 때 걸리는 점: 관계 종류 문제를 풀지 않고 비켜 간다. 서술은 사람이 읽기 좋지만 "원인 관계만 따라가기" 같은 질의는 할 수 없다. 개체 일치를 글자 그대로 하므로 작성자마다 용어가 다른 우리 문서에서는 지금 쓰는 용어집이 그 앞단을 맡아야 한다.

### 11. LightRAG

- 링크: https://github.com/HKUDS/LightRAG (로컬 `lab/repos/LightRAG`, 커밋 `453dce8`)
- 푸는 것: GraphRAG처럼 서술을 남기되, 관계마다 짧은 키워드 몇 개를 같이 붙인다.
- 메커니즘: 추출 프롬프트가 관계마다 `relationship_keywords`(쉼표로 나눈 상위 키워드)와 `relationship_description`을 받는다 (`lightrag/prompt.py:73-74`). 같은 개체 쌍의 관계가 여러 조각에서 나오면 키워드를 쉼표로 쪼개 집합으로 합친다 (`lightrag/operate.py:2170-2177`). 간선 키를 정렬해 저장하므로 그래프는 방향이 없다 (`lightrag/operate.py:3650-3653`).
- 인용: "`relationship_keywords`: One or more high-level keywords summarizing the relationship." (`prompt.py:73`). "# Collect edges with sorted keys for undirected graph" (`operate.py:3650`).
- 수치: 없다(관계 품질 평가 없음).
- 옮길 때 걸리는 점: 키워드를 글자 그대로 합치기만 하므로 "원인", "야기함", "초래"가 따로 남는다. 방향이 없어서 "A가 B의 원인"과 "B가 A의 원인"을 구분하지 못한다. 출력 언어를 `{language}`로 고를 수 있어 한국어 키워드는 받을 수 있다 (`prompt.py:108`).

### 12. Han & Lai — From Symbolic to Natural-Language Relations

- 링크: https://arxiv.org/pdf/2601.09069 (arXiv 2026-01, Walmart Global Tech, 입장 논문)
- 푸는 것: 관계를 고정 라벨로 압축하지 말고 자연어 서술로 남기되, 작은 기호 관계 뼈대를 함께 두자고 주장한다.
- 메커니즘: 세 원칙을 낸다. 목표·범위에서 나온 암묵적 스키마가 서술의 범위를 묶는다 (4.1절). 서술은 필요할 때 기호 관계로 다시 분류될 수 있어야 한다 (4.2절). 일반적이고 적게 약속하는 기호 관계 몇 개가 뼈대가 되고, 세부 뜻은 서술이 맡는다 (4.3절).
- 인용: "because rich relational meaning is preserved in textual form, symbolic relations can be more easily revised, refined, or restructured, such as being split, merged, or redefined, based on insights derived from natural-language descriptions" (4.3절). "This raises open research questions about how to coordinate LLM-driven semantic enrichment with controlled schema evolution" (5.2절).
- 수치: 없다. 실험 없는 입장 논문이다.
- 옮길 때 걸리는 점: 구현이 없다. 우리 문제에 맞는 모양은 이 논문이 가장 직접 말한다 — 관계 이름을 나중에 쪼개고 합칠 수 있도록 근거 서술을 남겨 두라는 것이다.

## 문서 사이 관계

### 13. CST (Cross-document Structure Theory) — Radev

- 링크: https://aclanthology.org/W00-1009.pdf (SIGDIAL 2000)
- 푸는 것: 같은 사건을 다룬 여러 문서의 문장·문서 사이 관계를 RST(한 문서 안 수사 구조 이론)를 문서 사이로 넓혀 분류한다.
- 메커니즘: 관계 종류를 미리 정한다(24개). Identity, Equivalence, Subsumption, Contradiction, Historical background, Follow-up, Elaboration, Refinement, Agreement, Change of perspective 등이다 (그림 5). 링크 찾기는 어휘 거리·어휘 사슬·정보 추출 템플릿으로 하고, 링크 타입은 단서 낱말 기반 기계학습으로 붙이자고 제안한다 (5절).
- 인용: "CST assigns labels such as subsumption, update, and elaboration to cross-document conceptual links." (1절). Follow-up은 "Additional information which reflects facts that have happened since the last account"로 정의한다 (그림 5).
- 수치: 없다. 제안 논문이다.
- 옮길 때 걸리는 점: 관계 종류를 미리 정하는 쪽이다. 하지만 원인·대응·후속·반박 같은 우리 관계 중 다수가 이 24개(후속=Follow-up, 반박=Contradiction, 배경=Historical background)에 이미 있다. 그래서 문서 사이 관계는 도메인 관계와 달리 작은 고정 뼈대로 시작할 수 있다는 근거가 된다.

### 14. Afantenos 외 — Exploiting Cross-Document Relations for Multi-document Evolving Summarization

- 링크: https://arxiv.org/pdf/cs/0404049 (2004)
- 푸는 것: CST 관계를 사람이 붙이기 어렵다는 결과를 받아, 문서 사이 관계를 문장 뜻이 아니라 구조화된 "메시지"의 인자 비교로 정한다.
- 메커니즘: 주제별로 메시지 타입을 정하고(예: `performance(선수, 측면, 회차, 값)`), 같은 타입 메시지끼리 규칙으로 관계를 붙인다. 같은 개체·같은 값이면 Stability, 같은 개체·반대 값이면 Antithesis, 가까운 값이면 Graduation이다 (PDF 7~8쪽). 같은 시점 다른 출처 사이는 synchronic, 같은 출처 다른 시점 사이는 diachronic 관계로 나눈다.
- 인용: CST 검증 실험(Zhang 외 2002)에 대해 "The inter-judge agreement was very low.", "Only a small subset of the proposed relations was used by the judges.", "No new relations were proposed." (PDF 2쪽). 자기 방식에 대해 "our synchronic–diachronic relations are not dependent on the semantics of the sentences in order to be established, because they do not connect sentences" (PDF 7쪽).
- 수치: 없다. Zhang 외(2002)의 실험은 9명이 문서 5쌍을 24개 관계로 표시했고, 새 관계를 제안해도 된다고 안내받았다 (PDF 2쪽). Zhang 외 원문은 읽지 않았고 이 논문의 요약으로만 옮겼다.
- 옮길 때 걸리는 점: 메시지 타입과 "가까운 값"의 기준을 사람이 온톨로지로 정해야 한다. [추정] 작은 모델에는 이 분업이 맞다 — 모델은 "무엇이 언제 어떤 값이었다"만 뽑고, 문서 사이 관계는 코드가 정한다(사례: PDF 7~8쪽 규칙 3개). 사람에게 관계 목록과 "새 관계를 써도 된다"는 자유를 같이 줘도 아무도 새 관계를 만들지 않았다는 결과는 사용자의 걱정(관계를 미리 알 수 없음)과 반대 방향의 증거다.

### 15. CRAB — Romanou 외 (EPFL)

- 링크: https://arxiv.org/pdf/2311.04284 (arXiv v1, 2023-11), 코드 https://github.com/agromanou/CRAB
- 푸는 것: 여러 기사에 흩어진 사건 쌍 사이의 인과 강도를 LLM이 판정할 수 있는지 잰다.
- 메커니즘: 20개 이야기마다 기사 약 20개에서 GPT-3로 주요 사건을 뽑는다. 사람이 이야기별 시간표를 만들며 다르게 표현된 같은 사건을 합친다 (3.3절). Mechanical Turk 작업자 7명이 사건 쌍 2,730개마다 0~100 인과 점수를 매기고, 같은 문서 쌍(360)과 다른 문서 쌍(2,370)을 나눈다 (3.4절). 관계 종류는 "원인" 하나이고, 열린 것은 관계 종류가 아니라 인과의 정도다.
- 인용: "models are able to capture causality when it is explicitly referred to in one context but struggle when it is implicitly inferred across documents" (6절). "GPT-4 wrongly assigns the highest responsibility to events that belong in the same document 33% of the time" (6절).
- 수치: 이진 인과 판정 macro F1이 GPT-4 같은 문서 80.0 / 다른 문서 72.6, Flan-Alpaca(XL) 73.8 / 56.7이다 (표 2).
- 옮길 때 걸리는 점: 같은 사건을 합치는 단계를 사람이 했다. 우리 문서에서는 이 단계를 용어집 연결이 대신해야 한다. 작은 모델은 다른 문서 사이 인과에서 같은 문서보다 17점 떨어진다. [추정] 보고서 A의 사건이 보고서 B의 사건의 원인이라고 모델이 스스로 찾게 하기보다, 작성자가 쓴 명시적 인과 문장을 근거로 붙인 것만 간선으로 두는 편이 안전하다(사례: 같은 문서 쌍이 명시적 인과 표현 덕분에 높다는 6절 해석 1개).

## 우리 문제에 주는 것

**가장 쓸 만한 셋**

1. **DIAL-KG의 후보 풀과 승격** — 관계를 미리 정하지 않아도 되는 이유를 구조로 보여 준다. 관계는 처음에 근거 서술과 짧은 관계구로만 남기고(GraphRAG·LightRAG 방식), 같은 뜻 군집이 문턱을 넘을 때만 이름 붙은 관계로 올린다. 떨어진 후보도 지우지 않는다. 이렇게 하면 Han & Lai가 말한 "나중에 쪼개고 합치기"가 가능해진다.
2. **ORELLM의 "관계구 + 쌍 유사도 판정"** — 이 갈래에서 읽은 출처 가운데 같은 뜻 관계를 묶는 판단을 작은 모델(1.5B)에 맡긴 것은 이것뿐이다. 문자열 일치로 묶으면 13%라는 수치는 LightRAG식 키워드 합치기로는 정규화가 안 된다는 근거다. 작은 모델에게는 이름 짓기보다 "이 두 관계구가 같은 뜻인가"라는 좁은 판정을 맡긴다. 군집 수는 CESI처럼 HAC 임계값으로 열어 둔다.
3. **Afantenos의 "메시지 비교로 문서 사이 관계 계산"과 CST의 작은 뼈대** — 문서 사이 관계는 도메인 관계와 달리 종류가 적고 오래 안정적이다(CST 24개, 사람은 그중 일부만 씀). 원인·후속·반박·배경 정도의 고정 뼈대를 두고, 후속·변화·반박은 "같은 대상·다른 시점·다른 값"을 코드로 비교해 붙이면 작은 모델은 추출만 맡는다. 이는 sage-wiki가 관계 어휘를 코드로 강제한 것과 같은 방향이다.

**아무도 풀지 않은 것**

- 한국어 관계구 정규화를 평가한 출처가 없다. 이 갈래의 모든 수치는 영어 데이터(ReVerb45K, FewRel, TACRED, WebNLG, UMLS)에서 나왔다.
- 10B 이하 생성 모델만으로 관계를 뽑고 묶고 승격하는 전체 흐름을 잰 출처가 없다. DIAL-KG·ORELLM의 추출 쪽은 모두 큰 API 모델이다.
- 정규화가 관계 방향을 지키는지 다룬 출처가 없다. llm-graph-builder 예시는 `PUBLISHED_BY`를 `PUBLISHED`로 합치고, LightRAG는 간선 방향을 버린다. "원인"과 "대응 절차" 같은 관계는 방향이 뜻의 절반이다.
- 문서 사이 관계를 미리 정하지 않고 발견한 출처가 없다. CST는 고정 목록이고, CRAB은 "원인" 하나의 강도만 재며, 같은 사건 합치기를 사람이 했다.
- 발견한 관계 종류의 품질을 사람 판정 없이 재는 방법이 없다. CESI는 관계에 사람 판정을 썼고, DIAL-KG는 큰 LLM 판정자를 썼다.

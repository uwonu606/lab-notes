# 큰 KG 에서 질문 시점 검색 — 무엇이 탐색 범위를 줄이나

- 조사 날짜: 2026-10-25
- 물음: 온톨로지(KG)를 만들어도 질문이 들어오면 키워드·문장·관계에서 데이터를 가져와 조합해야 한다. 데이터가 많아지면 전부 볼 수 없다. 그러면 질문 시점에 무엇이 탐색 범위를 줄이고, 비용은 무엇에 묶이며, 언제 실패하나.
- 다루는 갈래: 열한 개다. 진입점 찾기, 확장과 가지치기, 질의 언어로 바꾸기, 색인과 계층 요약, 에이전트형 탐색, 온톨로지·스키마가 이끄는 검색, 실무 시스템과 규모 벤치마크가 첫 조사다. 필터를 건 벡터 검색, 집계·전수 질문, 질문 유형 라우팅, 갱신과 낡음은 보충 조사로 더했다.
- 이전 조사와의 관계: `autoschemakg-kg-construction/notes.md` 회차 23 은 사용자가 네트워크 검증 문서 680건에서 검색 판 31개를 직접 견준 실험이다(종합 `autoschemakg-kg-construction/lab/reports/net-arch-final.md`). 이번 조사는 그 판들이 바깥 문헌의 어느 기제에 해당하는지 놓을 지도를 만든다(#사용자 실험과의 연결).
- `kg-cognitive-classification/research.md` 는 KG 의 개념과 관계를 *어떤 기준으로 나눌지* 를 다뤘다. 검색은 그 노트의 #11 활성 확산과 E5 로만 닿았다. E5 는 그 노트가 제안한 다섯째 실험으로, 임베딩 top-k 검색과 용어집 seed 에서 퍼지는 활성 확산을 견주는 검색 판이다. 이번 조사는 나눈 뒤에 질문 시점에 *어떻게 찾는지* 를 다룬다.

## 읽는 법

갈래마다 조사 에이전트 하나가 원문(논문, 공식 문서, 저장소 코드)을 열었다. 다른 에이전트가 같은 원문으로 주장을 다시 대조했다. 대조에서 고쳐진 주장은 고친 대로 썼고, 떨어진 주장은 없었다. 대조 에이전트가 기제 설명의 어긋남을 짚은 곳(예: 기본값, 버전 혼동)도 고친 대로 썼다. 열린 물음은 #확인하지 못한 것 으로 보냈다.

#8~#11 은 보충 조사 결과다. 조사 에이전트가 주장마다 원문 위치와 인용을 붙였다. 이 문서를 고치며 그 원문을 다시 열지는 않았다.

근거는 문장 안에 출처(논문과 절·표, 또는 파일:줄)로 적는다. 저장소 경로와 commit, 논문 URL 은 #원문 위치 에 모았다. 원문 없이 사례에서 끌어낸 판단에만 `[추정]` 을 앞에 달고, 사례와 개수를 같은 문장 끝 괄호에 붙인다. 큰따옴표 안은 원문 그대로다.

벤치마크마다 지표가 다르다(R@5, Hits@1, F1, LLM 판정 승률). 다른 표의 숫자끼리는 견주지 않는다.

### 약칭

본문에 쓰는 방법·자료구조 약칭을 여기서 모두 푼다. 시스템 하나의 설정값(ef_search, γ 같은 것)은 그 절에서 푼다.

| 약칭 | 뜻 |
|---|---|
| KB, KG | knowledge base, knowledge graph |
| RAG | retrieval-augmented generation. 검색한 조각을 LLM 입력에 넣어 답하게 하는 방식 |
| seed | 질문에서 고른 출발 노드. 확장·점수 퍼뜨리기가 여기서 시작한다 |
| DPR | dense passage retrieval. 질문과 passage 를 따로 임베딩해 내적으로 찾는 dense 검색기 |
| OpenIE | open information extraction. 정해 둔 relation 목록 없이 문장에서 (주어, 관계, 목적어) triple 을 뽑는 일 |
| HyDE | hypothetical document embeddings. LLM 이 쓴 가상의 답 문서를 임베딩해 검색 질의로 쓴다 |
| SimCSE | 대조 학습으로 만든 문장 임베딩 모델 |
| MCTS | Monte Carlo tree search. rollout 으로 가지의 값을 어림하며 펼칠 가지를 고르는 트리 탐색 |
| GRPO | group relative policy optimization. 질문마다 rollout 여럿을 내고 그 묶음 안의 상대 보상으로 정책을 고치는 RL 방법 |
| AC0 | 회로 복잡도 class. 다항 크기·상수 깊이 회로로 풀리는 문제들이다. OBDA 에서는 데이터 크기에 대해 질의 답이 SQL 평가만큼 쉽다는 뜻으로 쓴다 |
| OWL 2 QL | 웹 온톨로지 언어 OWL 2 의 한 profile. 질의를 SQL 로 옮길 수 있게(first-order rewriting) 표현력을 줄였다 |
| R2RML | 관계형 DB 표를 RDF 로 잇는 W3C mapping 언어 |
| SKOS | W3C 의 시소러스·용어집 표현 규격. prefLabel(대표 이름), altLabel(별칭), hiddenLabel(오타 변형), broader·narrower(상하위)를 둔다 |
| MeSH, ATM | 미국 국립의학도서관의 의학 주제어 시소러스. ATM(automatic term mapping)은 PubMed 가 태그 없는 질의어를 MeSH 등 번역표에 맞춰 바꾸는 장치다 |
| LC | long context. 문서 전체를 LLM 입력에 넣는 방식 |
| UDF | user-defined function. SQL 안에서 부르는 사용자 정의 함수 |
| NER | named entity recognition. 질문에서 이름 있는 대상을 뽑는 일 |
| EL | entity linking. 질문 속 이름을 KB 의 엔티티 하나에 붙이는 일 |
| ANN | approximate nearest neighbor. 근사 최근접 검색. 모든 벡터와 비교하지 않는다 |
| HNSW, IVF | ANN 색인 두 종류. 계층 근접 그래프, 군집별 역파일 |
| BM25 | 낱말 겹침 기반 순위. Lucene 역색인 위에서 돈다 |
| PPR | personalized PageRank. seed 에서 이웃으로 확률을 퍼뜨린 점수 |
| RWR | random walk with restart. PPR 과 같은 원리로 표본 그래프를 뗀다 |
| RRF, MMR | 여러 순위를 합치는 reciprocal rank fusion, 중복을 줄이는 maximal marginal relevance |
| PCST | prize-collecting Steiner tree. 점수 합에서 엣지 비용을 뺀 값이 큰 연결 트리 하나를 고른다 |
| GNN | graph neural network |
| LF | logical form. SPARQL·s-expression 같은 실행 가능한 질의 |
| KBQA, KGQA | KB·KG 위에서 자연어 질문에 답하는 과제 |
| SPARQL, Cypher | RDF 그래프 질의 언어, Neo4j 계열 property graph 질의 언어 |
| CVT | Freebase 의 중간 노드. n항 사실을 이진 관계 여럿으로 쪼갤 때 쓴다 |
| OBDA | ontology-based data access. 온톨로지 위의 질의를 관계형 DB 질의로 다시 쓴다 |
| community report | GraphRAG 가 색인 때 그래프 군집마다 LLM 으로 써 둔 요약 |
| map-reduce | 조각마다 LLM 을 따로 돌리고(map) 결과를 한 번에 합치는(reduce) 방식 |
| beam (N, D) | 단계마다 상위 N 개 후보만 남기는 탐색. D 는 최대 깊이 |
| SFT, RL | supervised fine-tuning, reinforcement learning |

### 지표

| 지표 | 뜻 |
|---|---|
| R@k | 상위 k 개 안에 정답 근거가 든 비율 |
| MRecall@k | 상위 k 개 안에 정답이 *전부* 든 문항의 비율 |
| Hits@1, Hit@1 | 1위가 정답인 비율. 논문마다 표기만 다르다 |
| Hit | 생성한 답에 정답이 하나라도 들면 1. 1위만 보는 Hits@1 과 다르다(SubgraphRAG) |
| EM, F1 | 답이 정답 문자열과 똑같은 비율, 답과 정답의 낱말 겹침에서 낸 정밀도·재현율 조화 평균 |
| EX | execution accuracy. 생성한 질의를 실행한 결과가 정답 질의의 결과와 같은 비율 |
| MRR | mean reciprocal rank. 첫 정답 순위의 역수를 평균한 값 |
| BLEU | 생성문과 참조문의 n-gram 겹침 점수 |
| P@1 | 1위 답의 정밀도 |
| ACC, truthfulness | 정답률. CRAG 의 truthfulness 는 맞은 답을 더하고 틀린 답(환각)을 빼서 셈한다 |
| 승률 지표 | comprehensiveness·diversity 처럼 LLM 판정자가 두 답 가운데 나은 쪽을 고른 비율 |
| recall@k (ANN) | 벡터 색인이 돌려준 상위 k 개가 정확한 최근접 k 개와 겹치는 비율. 5-recall@5 는 상위 5개 기준이다 |
| QPS | queries per second. 초당 처리 질의 수 |
| NACE | AGGBench 의 집계 값 오차 지표. 낮을수록 좋다 |
| Answer Comparison | S-RAG 가 답을 정답과 견줘 매긴 점수 |

### 벤치마크

| 벤치마크 | 무엇을 재나 |
|---|---|
| WebQSP, CWQ, GrailQA, GraphQ | Freebase KBQA |
| MetaQA | 영화 KB 위 1~3-hop QA |
| FactKG | KG 를 근거로 한 사실 검증 |
| MuSiQue, 2Wiki, HotpotQA, MultiHop-RAG | 다중 홉 문서 QA |
| MultihopQA, MultihopSum | Zhou 외 통합 비교의 다중 홉 QA·요약 과제 |
| NQ, NQ-Wiki, TQ-Wiki | 단일 hop 오픈 도메인 QA(Natural Questions, TriviaQA) |
| AIDA, AQUAINT | entity linking |
| GRBench | 도메인 그래프 위 질문(Graph-CoT) |
| BIRD, Spider·SpiderUnion, SocialDB | text-to-SQL |
| BSBM, NPD | RDF·OBDA 질의 성능 |
| Text2Cypher 테스트, CypherBench | text-to-Cypher |
| QASPER | 논문 본문 QA |
| Podcast, News, AP News | GraphRAG 계열 평가 말뭉치 |
| UltraDomain, Soybean, GraphRAG-Bench Novel | LightRAG·LeanRAG 도메인 QA, OG-RAG 농업 QA, 소설 말뭉치 그래프 RAG 평가 |
| LongMemEval | 장기 대화 기억 |
| STaRK(Amazon·MAG·Prime), CRAG | 대규모 반정형 KB 검색, 여러 영역의 RAG |
| LAION-1M, YFCC 10M, SIFT1M, TripClick | 벡터 검색과 필터 검색 |
| TAG 벤치마크, QUEST, AGGBench, Loong, Hotels·WorldCup·FB-Agg | 집계·집합 질문 |
| TimeQuestions, CronQuestions | 시간 조건이 있는 KGQA |

### 예문

갈래마다 같은 질문이 그 방식에서 어떻게 처리되는지 보인다. 질문은 사용자 부서(네트워크 검증)의 말로 썼다. NR 은 5G 무선 접속 기술(New Radio)이고, RAT 는 무선 접속 기술(radio access technology) 종류다. 핸드오버(HO)는 단말이 붙은 기지국을 옮기는 절차다.

> 지난 분기 NR 핸드오버 실패 원인으로 보고된 것 중 펌웨어 버전과 관련된 것은?

이 질문은 신호 다섯 개를 담는다. 기간(지난 분기, 조사일 기준 2026년 7~9월), 기술(NR), 증상(핸드오버 실패), 관계(원인으로 보고된), 속성 제약(펌웨어 버전)이다. 가정한 KG 는 보고서 노드, 증상·원인·펌웨어 버전 엔티티, 그 사이의 '보고함'·'원인'·'관련 펌웨어' 관계다.

각 절의 '예문' 은 작성자가 그 갈래의 기제에 맞춰 손으로 만든 예시다. 실제 시스템을 돌린 결과가 아니다.

## 한 장 결론

질문 시점 검색은 다섯 단계로 놓인다. 단계마다 범위를 줄이는 장치와 비용이 비례하는 것이 다르다.

| 단계 | 범위를 줄이는 장치 | 비용이 비례하는 것 | 여기서 나는 대표 실패 | 갈래 |
|---|---|---|---|---|
| 1 질문 해석 | 엔티티·키워드 추출(LLM 1회), 질의 언어 생성(Cypher·LF), 슬롯·필터 추출, schema linking(class·relation top-10), 질문 분해·관계열 계획, 질문 유형 라우팅 | LLM 호출 수, prompt 에 넣은 스키마 크기. schema linking 은 스키마 원소 수. 라우터는 질문당 작은 분류기나 LLM 1회 | NER 이 맥락 낱말을 버림(HippoRAG 1 오류의 48%), LF 뼈대 오류(ChatKBQA 오답의 40.1%), 작은 모델의 형식·도구 실패, 라우터 오분류(Adaptive-RAG 분류기 정확도 54.52%) | 1, 3, 5, 6, 10 |
| 2 출발점 | ANN·BM25 색인 top-k, alias·prior 표 top-30, fact top-5 + LLM 필터, 타입·label·값 필터와 그 필터를 거는 시점(선필터, 후필터, 탐색 중 필터) | ANN 이면 로그 수준. 전수 내적이면 노드·엣지 수에 선형. 선필터 전수는 통과 집합 크기에 선형 | 정답이 후보에 없으면 뒤에서 되살리지 못함(HippoRAG 2 오류 표본의 26% 는 필터 뒤 정답 구가 0개), 필터가 엄격하면 후필터가 limit 보다 적거나 0건을 돌려줌(pgvector, LanceDB) | 1, 4, 6, 7, 8 |
| 3 확장·가지치기 | k-hop·BFS 깊이 상한, beam N=3·D=3, 관계 먼저 고르기, PCST, MLP triple 점수, GNN, 흐름 가지치기, 계층 위에서부터 가지치기 | seed 수 × 차수^hop 의 국소 그래프, 또는 LLM 호출 수 × prompt 길이(차수에 비례). 전역 PPR 만 그래프 전체 | hub 의 fan-out, 거친 서브그래프의 답 누락(GNN-RAG CWQ 79.3% 만 답 포함), 약한 pruner(ToG WebQSP 76.2 → 66.3) | 2, 4, 5, 6 |
| 4 묶기·순위 | RRF·MMR·cross-encoder(2×limit 후보), token 예산 채우기(8k~12k), 점수 0 버리기, top-K triple·경로 | 후보 수, 예산은 상수. global map-reduce 는 고른 level 의 report 수 | 앞 단계 recall 이 상한이라 rerank 로 못 되찾음(STaRK-Prime GPT-4 reranker Hit@1 18.28%), 펼친 갈래가 예산을 먼저 가져감, 답 집합이 k 보다 크면 k 를 늘려도 못 담음(AGGBench k 5 → 50 에 recall 0.042 → 0.072) | 2, 4, 7, 9 |
| 5 답 | 답 LLM 1회, 실행 결과 그대로, 집계는 형식 질의나 레코드 표를 엔진이 셈, 실패하면 dense 검색이나 LLM 자체 지식으로 물러남 | 입력 token. 엔진이 세면 결과 표 크기 | non-empty 지만 틀린 질의, 최대 깊이에서 KG 없이 답함, 레코드 schema 가 속성을 놓침 | 3, 5, 7, 9 |

### 모든 데이터를 안 보는 원리

범위는 seed 를 고를 때 가장 크게 준다. 시스템 대부분이 질문 하나를 seed 수~수십 개로 바꾼 뒤, 뒤 단계를 seed 주변 국소 그래프에서만 돌린다. Freebase 는 entity 약 8,800만 개인데(DecAF §4), WebQSP 의 topic entity 2-hop 서브그래프는 평균 1,370.89 노드다(RoG 배포판, G-Retriever Table 2).

3단계는 그 국소 그래프를 다시 줄인다. G-Retriever 의 PCST 는 2-hop 서브그래프 평균 100,627 토큰을 610 토큰으로 줄였다(G-Retriever Table 2·4).

질의 비용은 그래프 전체 크기 대신 네 손잡이에 묶인다. seed 수, hop 깊이, beam 폭이나 LLM 호출 상한, token 예산이다. 이웃을 포인터로 바로 가리키는 저장소에서 질의 복잡도는 방문한 부분그래프 크기에 달린다(Besta 외, §6.9.1).

넷을 상수로 묶어도 비용은 데이터와 함께 자란다. 방문 부분그래프는 seed 수 × 차수^hop 이고(#2), 보고서가 쌓이면 hub 의 차수가 커진다(#2 예문). ANN 진입도 벡터 수에 대해 로그 수준으로 는다(#4). 그래서 손잡이가 막는 것은 그래프 전체에 선형으로 붙는 비용이다.

"색인이 있다" 와 "질의가 색인을 탄다" 는 다르다. 여덟 경로가 코드에서 후보 전체를 훑는다. HippoRAG 2 의 fact 매칭, LightRAG 기본 NanoVectorDB, OSS Graphiti 의 Neo4j cosine, RAPTOR collapsed tree, GraphRAG DRIFT primer 는 모든 후보와 유사도를 계산한다(#1, #4).

나머지 셋도 같다. GraphRAG local 의 text unit 순위와 OG-RAG 의 hypernode 정렬은 후보 전체를 선형으로 훑는다. neo4j-graphrag 는 metadata 필터를 받으면 ANN 대신 exact 질의로 바뀐다(#1, #4, #6). 그래서 이 여덟 경로는 데이터가 늘면 선형으로 비싸진다. 필터를 걸 때 선필터 전수로 떨어지는 일은 벡터 DB 에서도 흔하다(#8).

전체를 봐야 하는 질문(개요, 경향 요약)은 seed 로 국소화되지 않는다. 그래서 세 갈래로 푼다. 질의 전에 계층 요약을 만들어 두거나(GraphRAG community report), 질의 때 LLM 판정 예산으로 가지를 치거나(dynamic community selection, LazyGraphRAG), 집계를 DB 엔진에 넘긴다(#3, #6, #9).

'몇 건', '모든 X' 처럼 답 집합이 큰 질문은 순위 검색으로 풀리지 않는다. 고정 top-k 는 k 개를 넘는 근거를 담지 못하고, k 를 늘려도 recall 이 거의 오르지 않는다(AGGBench, #9). 그래서 형식 질의나 색인 때 만든 레코드 표로 엔진에 셈을 맡긴다.

실패는 앞 단계에서 나서 뒤로 번진다. HippoRAG 1 오류의 절반 가까이가 NER 에서, TIARA 오류의 46% 와 Pangu 오류의 62% 가 entity linking 에서 났다(#1, #3). 그래서 시스템들은 안전망을 둔다. 모든 passage 를 낮은 가중으로 seed 에 넣거나(HippoRAG 2), 실행이 실패하면 텍스트 검색으로 물러난다(LinkedIn, DecAF).

LLM 이 탐색을 이끌수록 모델 크기에 민감하다. KG-R1 이 같은 프롬프트 에이전트를 Qwen2.5 크기별로 다시 돌리자 ToG 는 7B 가 72B 보다 WebQSP 9점, CWQ 11점 낮았다(KG-R1 Table 1).

다만 KG-R1 은 anchor entity 와 gold answer 에서 2-hop 으로 잘라 둔 subgraph 위에서 평가했고, 기준선이 전체 Freebase 에서 돌았는지는 확인하지 못했다(#5). 그래서 이 차이는 범위를 미리 좁힌 조건에서 본 방향이다.

같은 일을 학습한 정책(KBQA-o1, KG-R1 의 RL 3B)이나 LLM 이 없는 장치(ANN, alias 표, 실행 엔진)로 옮기면 덜 민감하다(#5). KG-R1 의 RL 3B 수치도 같은 잘라 둔 subgraph 위의 값이다.

질문마다 경로를 고르는 라우터는 경로 수를 하나로 줄이지만, 오분류가 곧 실패다. 원문 세 편 모두 oracle 라우팅이 실제 라우터나 단일 경로보다 크게 높았다(Adaptive-RAG, RAGRouter, HybGRAG, #10). 그래서 경로들의 강점은 서로 겹치지 않고 라우터 정확도가 병목이다.

미리 만든 범위 축소 구조는 데이터가 늘 때 낡는다. 증분 갱신은 새 데이터 수에 비례해 싸지만 전체 재계산과 점점 어긋난다(Zep community, GraphRAG update, #11). 시간 질문은 만료된 사실을 거르는 일까지 맡는데, Graphiti 기본 검색은 만료 edge 를 거르지 않는다(#11).

## 갈래 지도

| # | 갈래 | 맡는 단계 | 대표 시스템 |
|---|---|---|---|
| 1 | 진입점 찾기 | 1, 2 | HippoRAG 1·2, LightRAG, GraphRAG local, Graphiti, BLINK, ReFinED, AutoSchemaKG |
| 2 | 확장과 가지치기 | 3 | HippoRAG PPR, G-Retriever, SubgraphRAG, GNN-RAG, RoG, KG-GPT, PathRAG |
| 3 | 질의 언어로 바꾸기 | 1, 5 | neo4j-graphrag Text2Cypher, TIARA, RnG-KBQA, Pangu, ChatKBQA, KB-BINDER, SPINACH, DecAF |
| 4 | 색인과 계층 요약 | 2, 3, 4 | HNSW, Neo4j 색인, GraphRAG local·global·dynamic·DRIFT, LazyGraphRAG, RAPTOR |
| 5 | 에이전트형 탐색 | 1, 3 | ToG, ToG-2, PoG, StructGPT, KG-Agent, Graph-CoT, Interactive-KBQA, KBQA-o1, KG-R1 |
| 6 | 온톨로지·스키마가 이끄는 검색 | 1, 2, 3 | Ontop, CRUSH4SQL, ORT, DBCopilot, SKOS·PubMed, OG-RAG, OntoRAG |
| 7 | 실무 시스템과 규모 벤치마크 | 전체 | LinkedIn, Neo4j, Bedrock, AWS graphrag-toolkit, Zep, STaRK, CRAG, CypherBench |
| 8 | 필터를 건 벡터 검색 | 2 | pgvector, Qdrant, Weaviate, Milvus, LanceDB, ACORN, Filtered-DiskANN, ParlayANN |
| 9 | 집계·전수 질문 | 4, 5 | TAG, CypherBench, S-RAG, StructRAG, GraphRAG global, DFA(AGGBench), QUEST |
| 10 | 질문 유형 라우팅 | 1 | Adaptive-RAG, Self-Route, LlamaIndex RouterQueryEngine, cognee, RAGRouter, HybGRAG |
| 11 | 갱신과 낡음, 시간 유효성 | 색인 갱신, 2 | Zep/Graphiti, GraphRAG update, LightRAG, FreshDiskANN, EXAQT, CronKGQA |

## 1. 진입점 찾기

질문을 소수의 seed 로 바꾸는 단계다. 줄이는 *단위*(엔티티, fact, 키워드, 엔티티 설명)가 결과를 크게 가르고, 여기서 틀리면 뒤 단계가 되살리지 못한다.

### 기제

| 기제 | 무엇을 몇 개로 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 질문 NER → 엔티티별 근접 노드 | 노드 전체(HippoRAG 1 MuSiQue 91,729개) → 엔티티마다 cosine 1위 노드. fast-graphrag 는 named 엔티티 top-1(문턱 0.7)에 generic 엔티티와 질문 전체의 top-20(문턱 0.5)을 더한다 | LLM 1회 + 엔티티 임베딩. 근접 검색은 전수면 노드 수에 선형, fast-graphrag 는 HNSW | HippoRAG 1 §2.2·Table 1; fast-graphrag `_state_manager.py:192-224` |
| 질문 → fact 매칭 + LLM 필터 | fact 전체 → top-5 → LLM 이 관련 부분집합만 → phrase seed 최대 5개. passage 노드는 전부 seed 로 넣되 가중 0.05 | 코드는 전체 fact 임베딩과 `np.dot`(fact 수 × 차원). LLM 필터는 질문당 1회, 입력 triple 5개 | HippoRAG 2 §3.4–3.5; `HippoRAG.py:1926, 2156-2205` |
| LLM 키워드 2단 추출 → 엔티티·관계 벡터 DB | low-level 키워드 → 엔티티 top-40(cosine 0.2 이상), high-level 키워드 → 관계 top-40, 그 뒤 1-hop | LLM 1회. 기본 NanoVectorDB 는 저장 행렬 전체와 `np.dot` 후 argsort 라 엔티티·관계 수에 선형 | LightRAG §3.2; `operate.py:4759-4767`; nano-vectordb `dbs.py` |
| 질문 전체 → 엔티티 title+description 임베딩 | 엔티티 전체 → k×2=20개 → 제외 목록만 거른다. 10개로 다시 자르지 않아 진입 엔티티는 최대 20개다 | 임베딩 1회 + vector store 1회. LLM 없음 | GraphRAG `entity_extraction.py:62-96`, `mixed_context.py:133-149` |
| BM25 + cosine 병렬 → RRF | 각각 2×limit 후보 → RRF(1/(rank+1) 합) → cross-encoder 를 쓰면 상위 2×limit 만 재순위. 기본 `Graphiti.search` 의 `EDGE_HYBRID_SEARCH_RRF` 는 BM25 와 cosine 만 쓴다 | BM25 는 hit 수. OSS Neo4j 경로의 cosine 은 vector index 없이 모든 RELATES_TO 엣지에 계산해 엣지 수에 선형 | Graphiti `search.py:291-420`, `search_utils.py:418-432` |
| 대규모 EL 후보 생성 | ReFinED 는 mention 마다 Wikipedia 링크 통계·YAGO·Wikidata alias 로 만든 prior 에서 top-30 만 남긴다(Wikidata 9천만 개 이상). BLINK 는 엔티티 5.9M 개 임베딩에서 FAISS top-100 → cross-encoder | 엔티티 임베딩 선계산. 질의당 exact 9.2 ms, HNSW 2.6 ms. 재순위는 후보 수(100 이하)에만 비례 | ReFinED §4.4; BLINK §4.1–4.2·Table 7 |
| seed 가중: specificity, 동의어 엣지 | seed 수는 그대로다. 많은 passage 에 나오는 노드를 1/\|P_i\| 로 누르고, 색인 때 cosine 0.8 이상 노드 쌍을 이어 둔다 | 노드별 passage 수 조회. 동의어 엣지는 색인 때 KNN(topk 2047) | HippoRAG 1 §2.2; `config_utils.py:160-175`; `HippoRAG.py:2064-2065` |
| seed 상한 + seed 별 표본 그래프 PageRank | 엔티티마다 FAISS(IVF1048576_HNSW32) top-k → LLM 이 이름을 거름 → difflib cutoff 0.8 로 노드에 다시 붙임 → seed 를 2×엔티티 수로 자름 → seed 마다 RWR 표본 약 250노드에서만 PageRank | seed 수 × 표본 크기. LLM 2회(NER, 필터) | AutoSchemaKG `lkgr.py:23-296` |
| 링크 실패 대비 dense 안전망 | HippoRAG 2 는 필터 뒤 fact 가 0개면 그래프 검색 없이 DPR 결과를 낸다. HippoRAG 1 은 링크가 불확실하면 dense 점수와 섞는다 | passage 검색 1회 더(코드는 전수) | `HippoRAG.py:762-764`; HippoRAG 1 Appendix F.2 |

### 수치

- 단위가 결과를 가른다. HippoRAG 2 Table 4 에서 MuSiQue·2Wiki·HotpotQA 평균 R@5 는 질문→fact 87.1, NER→노드 74.6, 질문 전체→노드 59.6 이다. 저자는 질문 전체와 짧은 노드 이름의 granularity 가 달라서 마지막이 나쁘다고 설명한다(§6.1).
- 엔티티 중심 질문에서는 순서가 뒤집힌다. 2Wiki 에서만 NER→노드가 91.2 로 기본값 90.4 보다 높다(HippoRAG 2 Table 4).
- 안전망의 몫이 필터의 몫보다 크다. passage 노드를 빼면 평균 R@5 가 87.1 → 81.0 이고, LLM 필터를 빼면 87.1 → 86.4 다(Table 4). passage 가중은 0.05 일 때 MuSiQue dev R@5 80.5, 0.5 일 때 77.9 다(Table 5).
- HippoRAG 1 Table 5 평균 R@5 는 전체 72.9, specificity 를 빼면 70.9, 동의어 엣지를 빼면 70.5 다. dense 앙상블은 ColBERTv2 기준 72.9 → 74.6 이다(Appendix F.2, Table 13).
- LightRAG 는 검색 단계에 100 token 미만과 API 1회를 쓴다고 보고한다(§4.5). seed recall 수치는 원문에 없다.
- BLINK 의 HNSW 는 R@100 을 96.7 → 95.5 로 1.2%p 낮추는 대신 질의 시간을 9.2 → 2.6 ms 로 줄인다(Table 7). zero-shot EL 에서 bi-encoder Recall@64 는 82.06, BM25 는 69.13 이다(Table 1).
- ReFinED 는 AIDA 추론에 15 s 가 걸렸고 BLINK cross-encoder 는 917 s 가 걸렸다(Table 5). prior 를 빼면 AQUAINT F1 이 5.0 떨어진다.

### 실패 조건

- 맥락 신호가 엔티티가 아닌 낱말에 있을 때 실패한다. HippoRAG 1 MuSiQue 오류 100건 중 NER 48%, OpenIE 28%, PPR 24% 다. NER 이 'Windows 8' 만 뽑고 'browsers'·'accessibility' 를 버린 사례가 대표로 실려 있다(Appendix F.1, Table 11).
- LLM 필터가 관련 fact 를 지울 때 실패한다. HippoRAG 2 의 recall@5 가 1.0 미만인 오류 표본 100건에서, 정답 문서의 구가 seed 후보에 하나도 없는 비율은 필터 전 7%, 필터 뒤 26% 다. 18% 는 필터 뒤 fact 가 0개라 dense 로 대체됐다(Appendix E).
- LightRAG 코드는 low-level 키워드를 ", " 로 이어 문자열 하나로 만들고 한 번만 임베딩한다(`operate.py:4766, 5338`). [추정] 엔티티가 여럿인 질문에서는 이 벡터 하나가 섞인 뜻을 대표해서 엔티티별 seed 를 고르지 못한다(사례: 이 이어 붙이기 코드, 1건). 키워드가 둘 다 비고 질문이 50자 이상이면 검색 없이 `fail_response` 를 낸다(`operate.py:6211-6213`).
- Graphiti 는 질문이 128 낱말 이상이면 full-text 질의를 빈 문자열로 만들어 BM25 경로가 빠진다(`search_utils.py:106-109`).
- 정답 엔티티가 후보 목록에 없으면 뒤 단계가 되살리지 못한다. ReFinED 는 Wikidata 에서 당시 최고 성능(SOTA)과 벌어진 차이(92.1 대 92.6)를 후보 생성 방식 차이 탓으로 본다(Appendix C).
- AutoSchemaKG 에서는 LLM 이 내놓은 이름이 후보와 0.8 미만으로 닮으면 그 seed 가 버려진다(`lkgr.py`, `get_close_matches`). [추정] 표본이 250노드라 seed 에서 먼 근거는 잡히지 않는다(사례: `lkgr.py:74` 가 표본 비율을 sampling_area / node_count 로 정함, 1건).
- GraphRAG local 은 대화 이력이 있으면 이전 사용자 질문을 질문 문자열에 덧붙인다(`mixed_context.py:133-137`). [추정] 화제가 바뀐 질문에서 이전 질문이 seed 를 끌어간다(사례: 이 덧붙이기 코드, 1건).
- neo4j-graphrag 는 metadata 필터를 주면 ANN index 대신 label 전체를 MATCH 해 cosine 을 정렬하는 exact 질의로 바뀐다(#8 의 선필터 전수). hybrid 검색에 필터를 주면 예외를 던진다(`neo4j_queries.py:197-224, 493-511`).

### 예문

| 방식 | 처리 |
|---|---|
| 질문 NER | 'NR', '핸드오버 실패', '펌웨어' 를 엔티티로 뽑고 '지난 분기', '원인' 은 버린다. 엔티티마다 노드 하나에 붙는다. 작성자가 'HO fail' 로 쓴 보고서는 동의어 엣지가 있어야 닿는다 |
| 질문 → fact | 질문 전체가 (핸드오버 실패, 원인, 펌웨어 3.2.1 의 타이머 버그) 같은 fact 에 바로 맞는다. LLM 필터가 기간 조건과 무관해 보이는 fact 를 지울 수 있다 |
| LightRAG 키워드 | low-level {NR, 핸드오버 실패, 펌웨어 버전}, high-level {장애 원인, 버전 회귀}. low-level 셋은 한 벡터로 임베딩된다 |
| alias·prior 표 | 'HO 실패', 'handover failure', '핸드오버 실패' 를 한 개념의 별칭으로 두면 LLM 없이 후보가 하나로 묶인다 |

## 2. 확장과 가지치기

seed 에서 어디까지 넓히는지를 정하는 단계다. LLM 이 단계마다 다음 걸음을 고르는 방식은 #5 에 둔다.

조사한 방법 대부분은 두 번에 걸쳐 줄인다. 먼저 seed 주변 거친 서브그래프를 잘라 오고, 그 위에서 정밀한 기제를 돈다. 그래서 비용은 전체 KG 가 아니라 국소 그래프 크기에 비례한다. 예외는 전역 PPR 이다.

### 기제

| 기제 | 무엇을 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| seed + 전역 PPR | 그래프를 잘라 내지 않고 점수로만 좁힌다. seed 에서 확률을 퍼뜨려 passage 노드 점수로 상위 passage 를 고른다 | 질의마다 그래프 전체 정점·엣지. igraph `personalized_pagerank` 를 무방향으로 돈다(damping HippoRAG 2 0.5, fast-graphrag 0.85) | `HippoRAG.py:2204-2211`; fast-graphrag `_gdb_igraph.py:165-179` |
| 거친 서브그래프 | 전체 Freebase → topic entity 2-hop 안의 triple(WebQSP 평균 1,370.89노드·4,252.37엣지, RoG 배포판). GNN-RAG 는 따로 PageRank-Nibble 로 top-2,000 엔티티를 남긴다 | 국소 영역 크기(차수와 hop). 2-hop 만으로 문항당 평균 100,627 토큰 | G-Retriever §4·Table 2; GNN-RAG Appendix |
| 관계열 계획 + 제약 BFS | LLM 이 관계열 top-3 을 beam 으로 생성 → 그 관계와 일치하는 엣지만 BFS. KG-GPT 는 sub-sentence 마다 엔티티에 붙은 관계 후보에서 top-k 를 고른다 | 계획 LLM 1회. BFS 는 프런티어의 차수 합. RoG 코드는 경로 상한 `max_p` 가 주석 처리라 경로 수에 상한이 없다 | RoG §4.4; `graph_utils.py:13-36`; KG-GPT §2.2 |
| PCST | 질의와 가까운 노드 top-3·엣지 top-5 에 내림차순 prize, 엣지 비용 0.5 → 연결 서브그래프 하나 | 국소 그래프 전체와 cosine + near-linear PCST. 코드는 엣지 하나는 고르도록 비용을 min(0.5, 최대 엣지 prize×0.995)로 낮춘다 | G-Retriever §5.3; `retrieval.py:19-73` |
| 가벼운 triple 점수기 | 거친 서브그래프의 모든 triple 을 MLP 하나가 병렬로 점수 매겨 top-K(기본 100, 코드 최대 500)만 LLM 에 넣는다. topic entity 에서 정·역방향 2라운드씩 퍼뜨린 거리 인코딩을 붙인다 | 후보 triple 수에 선형. 질의 임베딩 1회 + MLP + LLM 1회 | SubgraphRAG §1; `retriever.py:97-112` |
| GNN 답 후보 + shortest path | 2,000-엔티티 서브그래프에서 GNN(L=3)이 답 확률을 내고 누적 0.95 까지만 남긴 뒤 seed → 후보 shortest path 만 LLM 에 준다 | GNN 층 수 × 서브그래프 엣지 수. 추가 LLM 없음 | GNN-RAG Appendix, §4.3 |
| 흐름 기반 경로 가지치기 | 키워드로 고른 노드 N=40 쌍마다 resource 1 을 α=0.7 로 감쇠시키며 이웃 수로 나눠 퍼뜨리고 문턱 θ 아래에서 멈춘다 → 경로 top-15 | 출발점당 1/((1−α)θ) 노드, 전체 O(N²/((1−α)θ)). 그래프 크기와 무관 | PathRAG §3.2 |
| 차수 순 1-hop + token 예산 | 엔티티 top-40 의 모든 엣지를 (degree, weight) 순으로 정렬하고 관계 예산 8,000 token 에서 자른다 | seed 40개의 차수 합. 상한은 예산뿐 | LightRAG `operate.py:6211-6311` |

### 수치

- HippoRAG 1 의 단일 단계 PPR 은 2Wiki R@5 89.1(ColBERTv2 68.2), MuSiQue 51.9(49.2)다(Table 2). 1,000 질의에 API $0.1·3분이 들었고 IRCoT 는 $1~3·20~40분이었다(Appendix G, Table 17). 질의 NER 만 LLM 을 쓰기 때문이다.
- HippoRAG 2 코드 경로의 온라인 LLM 호출은 NER 이 아니라 fact rerank 필터다(`HippoRAG.py:757`). 위 10~30배 비용 차이는 HippoRAG 1 근거라 HippoRAG 2 에 그대로 옮기지 않는다.
- PCST 뒤 WebQSP 입력은 평균 100,627 → 610 토큰, 1,371 → 18 노드로 각각 99% 줄었다(G-Retriever Table 4).
- 같은 거친 서브그래프에서 shortest-path triple recall 은 SubgraphRAG 0.883(6 s), RoG 0.713(948 s), GNN-RAG 0.522(68 s), G-Retriever 0.294(672 s)다(WebQSP, SubgraphRAG Table 1). 시간에서 KG 질의 시간은 뺐다.
- SubgraphRAG 는 GPT-4o 와 함께 WebQSP Hit 89.80, CWQ 66.69 를 냈다(Table 3). 네 방법 모두 RoG 가 배포한 topic entity 중심 서브그래프에서 검색한다(Appendix C.1). 그래서 이 비교의 비용은 국소 그래프 위의 비용이다.
- GNN-RAG 는 WebQSP Hits@1 80.6, CWQ 61.7 이다(Table 2). WebQSP 2-hop 질문에서 입력 토큰 중앙값 357 로 답 커버리지 88.5% 를 냈다(RoG 435 토큰·82.1%, §4.3 Table 1).
- RoG(LLaMA2-7B 미세조정)는 WebQSP Hits@1 85.7, CWQ 62.6 이다(Table 1). KG-GPT 는 MetaQA 1·2·3-hop 96.3·94.4·94.0 이고 회수 triple 은 평균 2~4.5개다(Table 2, 13–14).
- PathRAG 는 LightRAG 대비 토큰을 16,728 → 14,438(−13.69%)로 줄였다(Table 6). 실험 그래프는 |V|~10^4 이다.

### 실패 조건

- 거친 서브그래프에 답이 없으면 뒤 단계 전체가 실패한다. GNN-RAG 의 CWQ 서브그래프는 79.3% 문항에만 답을 담는다(Appendix E).
- 전역 PPR 은 비슷한 주제의 passage 가 여럿이면 질의 맥락을 쓰지 못해 헷갈린다(HippoRAG 1 Appendix F).
- PCST 는 연결 트리 하나와 작은 k 로 근거를 덜 덮는다. SubgraphRAG 재평가에서 G-Retriever 의 WebQSP shortest-path triple recall 은 0.294 였다(SubgraphRAG Table 1).
- 관계열 계획은 그 모양에 맞지 않는 근거를 놓친다. GPT-4o 가 고른 관련 triple 기준으로 RoG recall 이 WebQSP 에서 45.6% 떨어진다(SubgraphRAG §4.1). KG-GPT 는 in-context 예시에 크게 좌우되고 FactKG 에서 72.68% 로 지도 모델 GEAR(77.65%)에 못 미친다(Limitations, Table 1).
- PathRAG 는 N² 쌍을 모두 돌아서 seed 가 많은 질의에서 비용이 제곱으로 는다(§3.2 복잡도 식).
- [추정] LightRAG 의 엣지 정렬 키가 질의 관련도가 아니라 차수라서 hub 엣지가 예산을 먼저 차지한다(사례: `operate.py` 의 정렬 키 (rank, weight), 1건).

### 예문

| 방식 | 처리 |
|---|---|
| 차수 순 1-hop | seed '핸드오버 실패' 가 보고서 수백 건에 붙은 hub 면 1-hop 엣지가 수백 개다. 차수 순으로 자르면 펌웨어와 무관한 엣지가 8,000 token 을 먼저 채운다 |
| 관계열 계획 | LLM 이 [원인 → 관련 펌웨어] 관계열을 내고 이 두 관계 엣지만 따라간다. 원인 노드가 펌웨어 노드에 바로 붙지 않고 "3.2.1 에서 재현" 같은 문장에만 있으면 경로가 빈다 |
| PCST | 질문과 가까운 노드 '핸드오버 실패', 'NR', '펌웨어 버전' 을 잇는 최소 트리 하나를 고른다. 트리 밖 원인 보고서는 빠진다 |
| triple 점수기 | 핸드오버 실패 주변 2-hop triple 전부를 MLP 가 점수 매겨 상위 100개를 넣는다. 기간 조건은 triple 속성에 날짜가 있어야 반영된다 |

## 3. 질의 언어로 바꾸기

LLM 이 데이터를 보지 않고 SPARQL·Cypher·LF 를 쓰면 DB 엔진이 인덱스로 답을 찾는다. 그래서 줄일 것은 데이터가 아니라 prompt 에 넣을 스키마와 질의 후보 공간이다.

### 기제

| 기제 | 무엇을 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 전체 스키마 주입 | 스키마는 줄이지 않는다. 생성된 Cypher 가 DB 인덱스로 데이터를 좁힌다 | LLM 1회, prompt 가 label·관계 타입·property 수에 비례. neo4j-graphrag 는 호출자가 스키마도 custom prompt 도 주지 않았을 때만 init 에서 `apoc.meta.data`(sample=1000)를 1회 돈다 | `text2cypher.py:149-202`; `schema.py:32,189` |
| 질문 기반 schema filtering | TIARA 는 class·relation 을 cross-encoder 로 따로 점수 매겨 top-10 씩만 넣는다. Ozsoy 의 exact-match 가지치기는 질문 낱말과 label·관계·property 를 맞춘다 | TIARA 는 schema 원소마다 cross-encoder 라 스키마 크기에 선형. exact-match 는 regex 라 지연이 거의 없다 | TIARA §3.2; Ozsoy §3.2 |
| seed 2-hop 열거 + ranker | linking 된 entity 에서 2-hop 안에 닿는 경로만 LF 후보로 만든다. 비교·최상급은 열거에서 뺀다 | 후보가 hop 에 따라 지수로 늘어 2-hop 에서 자른다. ranker 는 후보마다 BERT 1회 | RnG-KBQA §2.1; TIARA §3.2 |
| 유효 확장만 열거하는 beam | 현재 plan 을 KB 에서 실행해 닿는 relation·class 로만 다음 후보를 만든다. LM 은 생성하지 않고 순위만 매긴다 | LM forward 가 후보 plan 수에 비례. 같은 LM 의 ArcaneQA 보다 약 2배 느리다 | Pangu §3, Limitations |
| 생성 후 검색(generate-then-retrieve) | LLM 이 KB 를 보지 않고 LF 뼈대를 쓴 뒤 슬롯마다 KB 항목을 검색해 바꿔 넣는다. relation 후보는 bound entity 의 이웃(ChatKBQA)이나 2-hop 안 top-10(KB-BINDER)으로 묶는다 | ChatKBQA 유사도 계산 O(b·ne·E + k1·nr·R), 실행 시도 O(b+k1+k2). KB-BINDER 는 초안 하나가 수백 개 SPARQL 로 펼쳐진다 | ChatKBQA §4.4·Appendix B; KB-BINDER §3.2 |
| constrained decoding(trie) | decoding 중 schema 항목 자리에서 KB class·relation trie 안의 토큰만 허용한다 | decoding step 마다 prefix 조회 | TIARA §3.4 |
| 실행 검증·교정·폴백 | beam top-k 질의를 차례로 실행해 결과가 빈 것이 아닌 첫 질의를 쓴다. 방향만 틀린 패턴은 스키마의 (start,type,end) 삼중과 대조해 화살표를 뒤집는다 | 질문당 DB 실행 최대 k회. 방향 교정은 regex 와 대조라 LLM 이 없다 | RnG-KBQA §2.3; langchain-neo4j `cypher_utils.py:204-221` |
| 도구로 스키마 탐색 | LLM 이 검색·항목 조회·1-hop 패턴 조회 도구로 필요한 조각만 가져온다. SPINACH 는 entity 8개·property 4개·결과 첫·끝 5행, Interactive-KBQA 는 1-hop 패턴 top-10 | LLM 호출이 action 수에 비례(SPINACH 15 + rollback 15) | SPINACH §2.2; Interactive-KBQA `actions_fb.py:291-392` |
| KB 를 글로 펴서 검색 | Freebase(entity 약 8,800만, relation 2만, triple 4억 7,200만)를 passage 약 1억 2,600만 개로 바꿔 BM25·DPR 로 100개를 뽑고, LF 와 직접 답을 함께 생성한다 | 검색 1회 + reader | DecAF §4 |

cognee 의 NaturalLanguageRetriever 는 전체 스키마 주입처럼 보이지만 다르다. 모든 노드·엣지를 훑어 스키마를 뽑은 뒤 노드 스키마는 버리고 엣지 property key 목록만 prompt 에 넣는다(`natural_language_retriever.py:92-137`). 노드 label 은 prompt 파일에 손으로 쓴 기본 노드 설명이고, 관계 타입은 주지 않는다. 실패하면 실패한 질의와 오류를 누적해 최대 3회 다시 생성한다.

### 수치

- Ozsoy(Text2Cypher 테스트 2,471개)에서 prompt p95 토큰은 Enhanced Schema 2,697, Base 917, exact-match 가지치기 529, 유사도 가지치기 753 이다(Table 2·3). 20K 질의 입력 비용은 Claude-3.5 Haiku 기준 Enhanced Schema(중앙값 921 토큰) $14.7, exact-match 가지치기(중앙값 344 토큰) $5.5 다(§4.2.1 Table 3, 출력 길이가 같다고 가정).
- 정확도는 모델마다 갈렸다. Llama-3.1-8B 는 짧은 prompt 에서 올랐고, Qwen2.5-7B 와 Gemini-1.5-Flash 는 약 2% 떨어졌다(§4.2.2). 실험 DB 는 가장 긴 스키마가 약 2,700 토큰인 데모 DB 라 대형 스키마 효과는 확인되지 않았다.
- TIARA 의 GrailQA dev top-10 recall 은 class 95.8%, relation 92.0%, zero-shot relation 88.7% 다(Appendix A.2 Table 8). ReTraCk 은 class 100개·relation 150개를 넣었지만 QA 가 더 높지 않았다.
- TIARA ablation 에서 예시 LF 검색을 빼면 zero-shot F1 이 26.5, schema 검색을 빼면 전체 F1 이 2.7 떨어진다. trie 제약은 전체 F1 을 0.4, 다른 context 가 없을 때 5.2 올린다(§5.1).
- RnG-KBQA 는 열거를 넓히면 일부 질의에서 후보가 2,000,000개를 넘는다고 적었다(§2.1). 결과가 빈 것이 아닌 비율은 top-1 88.1%, top-10 90.4% 이고, ranker 를 무작위로 바꾸면 GrailQA dev F1 이 75.1 → 47.6 이다(Table 3·4).
- Pangu 는 BERT-base 로 GrailQA F1 79.9, T5-3B 로 81.7, WebQSP 79.6 을 냈다. Codex 10-shot 은 GrailQA 56.3 이고, 속도 때문에 beam 2·후보 1,000개 상한을 썼다(Table 1, Appendix C).
- ChatKBQA 는 WebQSP F1 79.8, CWQ 77.8 이다(Table 1). entity·relation 을 가린 뼈대는 표본의 91% 넘게 beam 후보 안에 맞는 것을 담았다(§4.3). entity 검색이 F1 을 약 15, relation 검색이 약 5 올렸다(§5.3).
- ChatKBQA 에서 생성 *전에* 검색 조각을 넣으면 WebQSP EM 이 63.5 → 58.5(top1) → 53.1(top10)로 떨어지고 최대 토큰이 512 → 2,012 로 는다(§5.4 Table 2).
- DecAF 에서 실행 가능한 LF 가 하나도 없는 질문은 WebQSP 11.3%, CWQ 30.2%, GrailQA zero-shot(dev) 22.5% 다(§4.2 Table 3·4).
- SPINACH(전체 Wikidata 엔티티 ID(QID) 1억 1,156만 개)는 F1 45.3, 같은 GPT-4o 로 SPARQL 을 한 번에 쓰면 3.9 다. 검색 도구를 빼면 dev F1 46.4 → 25.3 이다(Table 3, §5.4).

### 실패 조건

- linking 이 놓치면 무너진다. TIARA 오류 50개 중 entity retriever 46%(§5.3), Pangu(T5-3B) 오류 200개 중 topic entity 미발견 62% 다(Appendix E).
- 뼈대가 틀리면 검색으로 고칠 수 없다. ChatKBQA 오답의 40.10% 가 뼈대 오류, 27.17% 가 entity 검색, 19.48% 가 relation 검색 오류다(Appendix H). KB-BINDER 의 top-1 초안 logic frame recall 은 0.66 이다(Table 3).
- relation·property 오용과 방향에서 실패한다. SPINACH 오류 20건 중 40% 가 property 문제, 15% 가 action 예산 소진이다(Table 4). Interactive-KBQA 는 LLM 이 CVT 술어 방향을 이해하지 못한 reasoning 오류가 가장 많다(§4.7).
- 열거 범위 밖 질문(3-hop 이상, 비교·최상급)은 seed 2-hop 열거가 만들지 못한다(RnG §2.1, TIARA §3.2).
- [추정] 실행 검증은 결과가 빈 것이 아니지만 틀린 질의를 거르지 못한다(사례: RnG 가 빈 것이 아닌 첫 질의를 고르는 규칙, 1건).
- langchain-neo4j 교정기는 양방향 모두 스키마에 없으면 빈 문자열을 돌려주고, chain 은 context 를 [] 로 둔다(`cypher.py:346-355`).
- neo4j-graphrag Text2Cypher 는 `CypherSyntaxError` 가 나면 재시도 없이 예외를 던진다. 존재하지 않는 relation 을 막는 장치는 prompt 의 "Do not use any properties or relationships not included in the schema" 한 줄이다(`text2cypher.py:218-242`, `prompts.py:127`).
- trie 제약은 항목이 존재하는지만 보장한다. TIARA 는 "Using only discrete schema does not guarantee that generated logical forms are connected" 라고 적는다(§3.4).
- Freebase relation 수는 기준에 따라 다르다. DecAF 는 전체 약 2만 개, KB-BINDER 는 GrailQA 부분집합 3,720개, ChatKBQA 는 '수천' 이라 적는다.

### 예문

```cypher
MATCH (r:Report)-[:REPORTS_SYMPTOM]->(:Symptom {name: '핸드오버 실패'}),
      (r)-[:REPORTS_CAUSE]->(c:Cause)-[:INVOLVES]->(f:FirmwareVersion)
WHERE r.rat = 'NR' AND date('2026-07-01') <= r.date < date('2026-10-01')
RETURN c.name, f.version, count(r) AS reports
```

LLM 은 스키마(Report, Symptom, Cause, FirmwareVersion 과 세 관계)만 보고 이 질의를 쓴다. 데이터를 훑는 일은 DB 의 label·날짜 인덱스가 한다.

| 실패 지점 | 이 예문에서 |
|---|---|
| linking | 증상이 'HO fail' 로 저장돼 있으면 0행이다. 증상 이름을 먼저 검색해 붙이는 단계(ChatKBQA 식)가 필요하다 |
| 방향 | `(c)<-[:INVOLVES]-(f)` 로 쓰면 교정기가 스키마 삼중과 대조해 뒤집는다 |
| 뼈대 | 펌웨어가 Cause 노드가 아니라 Report 의 property 로 저장돼 있으면 뼈대 자체가 틀린다 |

## 4. 색인과 계층 요약

전체를 훑지 않게 하는 자료구조다. 질의를 seed 로 바꾸는 색인(벡터 ANN, 역색인), seed 에서 이웃을 따라가는 adjacency, 그리고 국소화가 안 되는 전체 질문을 위한 계층 요약으로 나뉜다.

### 기제

| 기제 | 무엇을 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 벡터 ANN 색인 | N 개 임베딩 → 질의와 가까운 k 개 | HNSW 는 상위 layer 에서 내려가 N 에 대해 로그 수준. 색인 없이 전수면 N × 차원 | HNSW 초록; Neo4j vector index 문서 |
| 역색인(BM25) | STRING 속성 전체 → 질의 term 이 든 노드·관계만 relevance score 순 | posting list 길이. 전체 노드 수가 아니다 | Neo4j full-text index 문서 |
| adjacency 이웃 확장 | seed → 깊이 d 안 이웃. Graphiti 는 가변 길이 경로 `*1..bfs_max_depth` | 방문한 부분그래프 크기. 이웃을 리스트로 들고 있으면 엣지 수에 선형 | Besta 외 §6.9.1; Graphiti `search_utils.py:450-563` |
| GraphRAG local search | 엔티티 seed 최대 20개 → 속한 community report, 연결 관계, 원문 text unit 을 token 예산 비율로 채운다. config 기본은 12,000 token 을 community 0.15, text unit 0.5, 나머지 0.35 로 나눈다(클래스 기본은 8,000 / 0.25 / 0.5 / 0.25) | 답 LLM 1회. text unit 순위는 선택 엔티티마다 관계 리스트 전체를 훑어 대략 엔티티 수 × 엣지 수 | `mixed_context.py:99-211, 321-329`; `defaults.py:260-272` |
| community 요약 + global map-reduce | 원문 대신 한 level 의 community report 들을 배치로 map 한다. map 은 점수 붙은 point 를 내고, 점수 0 은 버리고 점수순으로 reduce 한다. 배치·reduce 예산은 config 기본 12,000 token(클래스 기본 8,000) | LLM 호출 = 배치 수 + 1. 그래서 고른 level 의 report 수에 비례하고 질의마다 그 level 전체를 본다 | GraphRAG §3.1.6; `search.py:172-198, 333-379` |
| dynamic community selection | root level report 부터 LLM 이 0–10 으로 평정하고 문턱(기본 1) 이상인 report 의 자식만 큐에 넣는다. 관련 없는 subtree 는 통째로 빠진다 | 평정 호출 = 방문 노드 수 × 반복 수. 평정은 싼 모델(GPT-4o-mini) | `dynamic_community_selection.py:92-155` |
| DRIFT | HyDE 로 늘린 질의와 모든 report 의 cosine → top-20 → 5 fold primer 답과 후속 질문 → epoch 마다 후속 질문 최대 20개를 local search 로(n_depth 3) | report 수에 선형인 유사도 + 코드 기본값으로 세면 LLM 최대 약 67회(reduce 포함). 실측 아님 | `drift_context.py:203-229`; `drift_search/search.py:192-300` |
| LazyGraphRAG | 색인 때 LLM 요약 없이 명사구 co-occurrence 그래프와 community 계층만 만든다. 질의 때 chunk 임베딩 순위 → 상위 미검사 chunk 만 LLM 문장 단위 relevance test → 관련 sub-community 로만 재귀 | LLM 호출이 relevance test budget(100·500·1,500)으로 묶인다 | LazyGraphRAG 블로그 |
| RAPTOR 요약 트리 | traversal 은 layer 마다 top-5, 그 자식만 다음 후보. collapsed 는 모든 layer 를 펴서 유사도순으로 top_k(코드 기본 10)를 자른 뒤 token 한도(코드 3,500)까지 채운다 | traversal 은 시작 layer 전체 비교 + top_k × 가지 × layer 수. collapsed 는 모든 노드 cosine | RAPTOR §3; `tree_retriever.py:174-259` |

### 수치

- GraphRAG(Podcast, 약 1M token)에서 report 수는 C0 34, C1 367, C2 969, C3 1,310 이고 원문 요약(TS) chunk 는 1,669 다(§5.1 Table 2). C0 는 TS 보다 질의당 token 이 97% 이상 적고(약 38배, News 약 43배), C3 는 26–33% 적다.
- TS 를 포함한 global 방식은 vector RAG 대비 comprehensiveness 승률이 Podcast 72–83%, News 72–80% 다. C0 만 써도 72% 를 유지했다(§5.1).
- LightRAG 논문은 GraphRAG 가 level-2 community 610개 × 평균 1,000 token = 610,000 token 을 쓴다고 셈했다(Legal 데이터셋, §4.5). 평균에서 셈한 추정치이고 실측이 아니다.
- dynamic selection 은 AP News 50개 global 질문에서 level 1 기준 정적 방식 report 약 1,500개 대신 평균 470개를 골랐다. 비용은 평균 77% 줄었고 품질 차이는 유의하지 않았다. level 3 에서는 비용이 34% 더 들었다(Microsoft Research 블로그, Table 1).
- DRIFT 는 AP 뉴스 local 질문 50개에서 Local Search 대비 comprehensiveness 78%, diversity 81% 승률을 보였다. 비용 수치는 블로그에 없다.
- LazyGraphRAG 의 색인 비용은 vector RAG 와 같고 full GraphRAG 의 0.1% 다. budget 500 에서 GraphRAG C2 global search 질의 비용의 4% 로 경쟁 방법을 이겼고, global 질문에서 비슷한 품질을 질의 비용 700배 이상 낮게 냈다(AP 뉴스 5,590건, 질의 100개). 700배 비교의 community level 은 밝히지 않았다.
- RAPTOR 는 QASPER 20 stories 에서 collapsed tree 가 traversal 보다 일관되게 나았고 2,000 token 에서 가장 좋았다(§3, Figure 3).

### 실패 조건

- 색인이 있어도 질의 경로가 쓰지 않으면 전수 비교로 돌아간다. OSS Graphiti 의 Neo4j cosine 은 모든 RELATES_TO 엣지에 계산하고 저장소 안에 vector index 생성이 없다(`search_utils.py:418-433`, grep 0건). Neptune 경로는 임베딩을 모두 클라이언트로 가져온다.
- 같은 꼴이 셋 더 있다. RAPTOR collapsed 는 트리 모든 노드와 거리를 계산하고(`tree_retriever.py:174-183`), DRIFT primer 는 모든 report 와 cosine 을 한꺼번에 계산하며(`drift_context.py:203-229`), GraphRAG local 의 text unit 순위는 관계 리스트를 선형으로 훑는다(`mixed_context.py:321-329`).
- GraphRAG 기본 LanceDB 는 dummy 1행 테이블에 IVF_FLAT 색인을 만든다(`lancedb.py:58-79`). 데이터가 들어온 뒤 실제 ANN 으로 도는지는 확인하지 못했다.
- ANN 결과는 근사라 정확한 top-k 를 보장하지 않는다(Neo4j vector index 문서).
- 그래프가 메모리를 넘으면 adjacency 탐색의 실행 속도가 캐시에 크게 좌우된다(Besta 외 §6.9.1).
- global search 는 낮은 level 을 고를수록 report 가 많아져 시간과 LLM 자원이 는다(GraphRAG `docs/query/global_search.md:50`). 남은 point 가 없으면 LLM 을 부르지 않고 "모른다" 를 돌려준다(`search.py:333-355`).
- dynamic selection 은 root 에 관련 report 가 하나도 없으면 다음 level 의 report 전체를 평정해 전수 조사로 돌아간다. JSON 파싱이 실패하면 평점 1 로 두어 남긴다(`rate_relevancy.py:66-73`). 자식 확장에는 깊이 제한이 없고, 기본 `keep_parent=False` 라 자식이 관련 있으면 부모 report 는 결과에서 빠진다.
- [추정] dynamic selection 에서 상위 요약이 세부를 덮으면 잘린 가지 아래 근거는 영영 보지 않는다(사례: 문턱 미만 노드의 자식을 큐에 넣지 않는 코드, 1건).
- DRIFT 블로그는 "A future version of DRIFT will incorporate an improved version of Global Search" 라고 적어 전체 질문을 아직 약점으로 둔다.
- LazyGraphRAG 저자는 요약 색인과 lazy 탐색을 결합하면 더 낫다고 적는다. 결과는 Microsoft 자체 평가 하나다.
- RAPTOR 코드의 threshold 모드는 cosine distance 가 문턱보다 *큰* 노드를 골라 덜 비슷한 노드를 남긴다(`tree_retriever.py:226-229`).

### 예문

| 질문 | 처리 |
|---|---|
| 예문 그대로 | local 질문이다. ANN 으로 '핸드오버 실패'·'펌웨어' 관련 claim·엔티티를 seed 로 잡고, 기간은 벡터가 아니라 metadata prefilter 로 거른다(#8). 'FW' 같은 약칭은 BM25 가 놓치고 벡터가 잡는다 |
| "지난 분기 핸드오버 장애 경향을 요약해 줘" | global 질문이다. 정적 global 은 고른 level 의 report 전부를 map 한다. dynamic 은 '이동성' community 아래로만 내려간다. LazyGraphRAG 는 상위 chunk 부터 relevance test 를 budget 까지 돈다 |

## 5. 에이전트형 탐색

LLM 이 도구로 그래프를 한 걸음씩 걷는다. 읽는 양은 호출 하나가 돌려주는 조각(한 엔티티의 관계 목록, 상위 K 개 triple, 잘린 질의 결과)과 단계 상한(beam 폭, 깊이, turn 수)으로 묶인다. 비용은 그래프 크기보다 LLM 호출 수 × 단계당 prompt 길이에 비례한다.

### 기제

| 기제 | 무엇을 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 관계 먼저 고르는 2단 beam | 엔티티 하나의 이웃 관계 전부를 한 prompt 에 넣고 LLM 이 top-N(3)을 고른 뒤, 그 관계의 꼬리 엔티티에서 top-N 을 고른다. ToG 코드는 pruner 가 LLM 일 때 꼬리 후보가 20개 이상이면 LLM 채점 전에 무작위 5개만 남긴다 | LLM 최대 2ND+D+1회(N=D=3 이면 22). 관계 pruning prompt 길이가 현재 엔티티의 관계 차수에 비례 | ToG §2.1; `main_freebase.py:69-71`; `freebase_func.py:108-135` |
| 충분성 판정 + 상한 | hop 마다 LLM 이 지금 경로로 답할 수 있는지 판정해 예면 멈춘다. 끝까지 아니면 깊이 3(ToG), 15 step(Graph-CoT), 20 turn(Interactive-KBQA), 5 turn(KG-R1)에서 끊는다 | hop 마다 판정 1회. turn 마다 history 가 쌓인다. Graph-CoT 는 prompt 10,000 token 을 넘으면 멈춘다 | ToG §2.1.3; Graph-CoT `GraphAgent.py:116, 202` |
| 작은 조각만 돌려주는 도구 | Graph-CoT 의 RetrieveNode 는 top-1 노드, Interactive-KBQA 의 SearchNodes·SearchGraphPatterns 는 10개, SPARQL 결과는 2,000자에서 자른다. KG-Agent 의 count·intersect 는 executor 가 집합을 처리하고 LLM 에는 결과만 준다 | turn 수 × (반환 크기 + 누적 history) | Interactive-KBQA §3.3; KG-Agent §4.1 |
| 관계 임베딩 순위·후보 축소 | Interactive-KBQA 는 엔티티의 1-hop 술어를 술어 벡터 색인 400개 조회로 정렬해 top-10 만 준다. PoG 는 엔티티 후보가 많으면 DistilBERT 로 먼저 recall 한다. ToG-2 는 엔티티를 그 문서 chunk 점수로 가지친다 | 임베딩 조회만. LLM 이 읽는 양은 K 에 고정 | `actions_fb.py:291-392`; PoG §3.2; ToG-2 §3.2.2 |
| 실행 가능한 action 으로 붙이기 | policy 가 쓴 action 을 SimCSE 로 현재 상태에서 실행 가능한 KB action 과 맞춰 top-k → policy 점수로 top-d. KG-R1 은 없는 엔티티·관계에 오류 메시지를 돌려줘 다시 시도하게 한다 | 단계마다 beam 생성 + 매칭 + 채점 | KBQA-o1 §4.2.3; KG-R1 §3.2 |
| MCTS | 모든 경로를 펼치는 대신 rollout 6, 예측 beam 1, top-k 10(WebQSP 3), top-d 3 만 펼친다 | O(N·k·L), rollout 수와 깊이에 선형 | KBQA-o1 Appendix G |
| 질문 분해 | PoG 는 질문을 조건이 담긴 sub-objective 로 나눠 관계 선택과 반성·되돌아가기의 기준으로 쓴다 | 분해 1회 + hop 마다 탐색·평가·반성 | PoG §3.1 |
| 정책 학습 | 후보를 줄이지 않는다. 작은 모델이 깨지는 형식·도구 선택·다단계 유지를 학습으로 메운다 | KG-Agent 10K 샘플 SFT, KG-R1 GRPO(질문당 rollout 3B 16개, 7B 8개) | KG-Agent §5.2; KG-R1 Appendix E.4 |

### 수치

- ToG 의 실제 평균 호출은 CWQ 14.3, WebQSP 11.2, GrailQA 10.4 회로 이론 최대 22 보다 적다(Appendix B.2.1, Table 7). 조기 종료 덕분이다. 깊이 3 을 넘으면 성능 상승이 줄어든다(§3.2.3).
- Freebase 에서 ToG 는 ChatGPT 로 CWQ 57.1·WebQSP 76.2, GPT-4 로 67.6·82.6 이다(Table 1). Llama-2-70B-Chat 은 CWQ 53.6·WebQSP 63.7 이다(Table 2).
- pruner 를 LLM 대신 BM25·SentenceBERT 로 바꾸면 호출은 D+1회로 줄지만 CWQ 평균 8.4%, WebQSP 평균 15.1% 떨어진다(WebQSP ChatGPT 76.2, SBERT 66.3, BM25 58.7). SBERT 에서 폭을 3 → 5 로 늘리면 호출 증가 없이 68.5 로 일부 회복된다(Table 5, Appendix B.2.1).
- ToG 는 같은 질문에서 KG 를 Freebase → Wikidata 로 바꾸면 CWQ 58.8 → 54.9, WebQSP 76.2 → 68.6 이다(Table 3).
- ToG-2 는 관계 pruning 을 iteration 당 1회로 합치고 엔티티 pruning 을 dense 검색 모델로 바꿨다. HotpotQA 질문당 호출이 ToG 16.3회·69.3 s 에서 5.4회·27.3 s 로 줄었다(Table 8·9). 이 감소는 두 변경이 섞인 효과다.
- ToG-2 는 KG 완전도가 30% 로 떨어지면 HotpotQA 100문항에서 23 으로 내려가고, 폭 8·깊이 2 로 바꾸면 29 로 회복된다(Appendix B.7, Table 11).
- PoG 는 ToG 대비 호출을 CWQ 22.6 → 13.3, WebQSP 15.9 → 9.0 회로, CWQ 시간을 96.5 → 23.3 s 로 줄였다. GPT-3.5 정확도는 CWQ 63.2, WebQSP 82.0 이다(Table 4·1). PoG 가 다시 구현한 ToG 의 22.6회는 ToG 논문의 이론 최대 22 보다 커서 설정이 다르다.
- Graph-CoT(GPT-3.5)는 GRBench 에서 36.29 로 1-hop ego-graph RAG 23.09, 2-hop RAG 22.12 를 이긴다. hop 이 선형으로 늘면 노드는 지수로 늘어 context 를 넘기 때문이다(§5.4 Table 4).
- KG-Agent(LLaMA2-7B, 10K SFT)는 WebQSP Hits@1 83.3, CWQ 72.2, GrailQA F1 86.1 로 ChatGPT 기반 StructGPT(72.6/54.3/54.6)보다 높다. 엔티티는 주어졌다고 가정했다(Table 2, Appendix A.4).
- KBQA-o1(40·100-shot 학습)은 Qwen2.5-32B 로 GrailQA F1 80.3, WebQSP 63.7, GraphQ 50.9 를 낸다. Qwen2.5-7B 는 77.9/57.8/49.2 다. GPT-3.5 기반 이전 low-resource 최고치는 GrailQA 48.5 였다(Table 2–4).
- KBQA-o1(Llama-3.1-8B) ablation 에서 GrailQA F1 78.5 는 KB environment 를 빼면 43.0, MCTS 를 빼면 48.5, 초기 SFT 를 빼면 13.1 이다(Table 5).
- KG-R1 이 같은 프롬프트 에이전트를 Qwen 크기별로 다시 돌렸다(WebQSP/CWQ Hits@1). ToG 는 7B 65.00/32.25, 72B 74.47/43.18, PoG 는 7B 64.81/32.00, 72B 72.88/43.62 다. ToG 의 질문당 총 token 은 약 6.5K~9K 다. RL 로 학습한 Qwen2.5-3B 는 82.75/65.31 이다(Table 1). 이 표는 이 절의 실패 조건에 적은, gold answer 로 잘라 둔 subgraph 설정 위에서 쟀다.

### 실패 조건

- 관계 고르기에서 실패한다. StructGPT 의 WebQSP 오류 100건 중 74% 가 LLM 이 관련 정보를 고르지 못한 selection error 이고, 저자는 수천 개 relation 에서 골라야 하기 때문이라고 적는다(§5.4).
- 질문 어휘와 스키마 어휘가 다르면 임베딩 순위가 놓친다. 'locate in' 이 organization.organization.headquarters 를 찾지 못한 사례가 있다(Interactive-KBQA, predicate search 오류 6/100, Table 9).
- 작은 모델은 프롬프트만으로는 다단계 도구 호출을 못 한다. Interactive-KBQA 에서 Mistral-7B 는 미세조정 없이 CWQ 4.76, 뒤에 39.90 이다(Table 8). Graph-CoT 는 시연 예시가 없으면 모든 데이터셋에서 거의 0점이고, LLaMA-2-13b-chat 은 16.04 다(§5.3).
- 최대 깊이에서도 결론이 안 나면 ToG 는 KG 없이 LLM 내부 지식으로 답한다(§2.1.3).
- ToG 코드의 무작위 5개 샘플링은 정답 엔티티를 잘라 낼 수 있다(`main_freebase.py:69-71`). 정량 분석은 없다.
- 반환 상한이 없는 도구는 hub 에서 context 를 터뜨린다. Graph-CoT 의 NeighbourCheck 는 이웃 목록 전체를 문자열로 돌려준다(`tools/graph_funcs.py:24-28`).
- turn 이 길어질수록 F1 이 대체로 떨어진다(Interactive-KBQA Appendix A.6).
- 평가 설정이 범위를 미리 줄여 둔다. KG-R1 은 질문마다 anchor entity *와 gold answer* 에서 2-hop BFS 로 잘라 둔 subgraph 위에서 평가했다(Appendix C.2). StructGPT 공식 WebQSP 실행도 `subgraph_2hop_triples.npy` 를 KG 로 쓴다(`run_webqsp_wo_icl_v1.sh:4`). 운영에는 gold answer 가 없어서 이 수치는 큰 KG 에서 그대로 서지 않는다.
- 학습 분포 밖에서 약하다. KG-Agent 는 NQ-Wiki 33.00, TQ-Wiki 35.89 로 ChatGPT(57.49, 88.68)보다 낮다(Table 4). KG-R1 은 스키마가 크게 다르거나 graph 에 noise 가 많으면 transfer 가 떨어질 수 있다고 적는다.
- KBQA-o1 저자는 큰 도메인으로의 확장성을 한계로 적었다(Impact Statement).

### 예문

| 걸음 | 도구 호출과 결과 | 깨지는 곳 |
|---|---|---|
| 1 | 노드 검색("NR handover failure") → 상위 10개 중 '핸드오버 실패' | 작성자 표기('HO fail')가 노드 이름과 다르면 상위 10개 밖 |
| 2 | 관계 조회 → {원인, 관찰 망, 해결 조치, 재현 조건, …} 수십 개를 한 prompt 에 → LLM 이 '원인' | 관계가 많을수록 prompt 가 길고 작은 모델이 잘못 고른다 |
| 3 | 꼬리 원인 엔티티 37개 | ToG 코드라면 20개 이상이라 무작위 5개만 남는다 |
| 4 | 원인마다 '관련 펌웨어' 조회, 보고서 날짜로 2026년 3분기만 | 날짜가 보고서 property 면 집계를 executor 도구에 넘겨야 LLM 이 집합을 다 읽지 않는다 |
| 5 | 충분성 판정 → 답 | 판정이 틀리면 일찍 멈추거나 깊이 끝까지 간다 |

## 6. 온톨로지·스키마가 이끄는 검색

질의를 데이터가 아니라 크기가 작은 스키마 위에서 먼저 풀고, 그 결과(SQL, label 경로, class)를 데이터 쪽 인덱스나 탐색에 넘긴다. 그래서 질문 시점 비용은 데이터 크기보다 스키마·mapping 의 복잡도와 beam·hop 수를 따른다. text-to-query 일반은 #3 에 있다. 이 절의 장치는 온톨로지의 계층·타입·용어집이 스키마를 작게 만들거나 질의어를 정규화하는 쪽이다.

### 기제

| 기제 | 무엇을 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| OBDA 질의 다시 쓰기 | offline 에서 class·property 계층을 mapping 안에 컴파일(T-mapping)해 두고, 질문 시점에는 SPARQL 1개를 SQL 1개로 바꿔 RDBMS 가 자기 인덱스로 실행한다. 추론된 triple 을 만들어 두지 않는다 | 질의·온톨로지·mapping 복잡도. 데이터 크기에 대해 AC0. rewriting 은 최악의 경우 지수. LLM 0회. 의미 최적화는 T-mapping 에 offline 으로, 생성 SQL 에 online 으로 다시 돈다 | OWL 2 QL §3; Ontop §4.1–4.2 |
| 스키마 부분집합 검색 | TIARA 는 Freebase class 2K·relation 6K 중 top-10 씩. CRUSH4SQL 은 LLM 이 질문에 필요한 최소 스키마를 '환각' 하게 한 뒤 그것으로 여러 번 dense 검색해 실제 스키마 부분집합을 고른다. TrustGraph 는 온톨로지 원소를 임베딩해 top_k=10·문턱 0.3 으로 고르고 domain·range 의존 원소를 따라 붙인다 | 스키마 원소 수에 비례하는 검색. 데이터 크기와 무관 | TIARA §4.1; CRUSH4SQL §5.3; TrustGraph `ontology_selector.py:76-290` |
| 타입·관계 제약 | Pangu 는 현재 plan 에서 닿는 type·relation 만 후보로 열거한다(#3). Graphiti SearchFilters 는 edge_types 와 node_labels 를 Cypher WHERE 에 붙인다 | 한 단계 = beam × 닿는 relation·type 수 | Pangu §3.2; Graphiti `search_filters.py:55-136` |
| 온톨로지 label 경로를 먼저 계획 | ORT 는 label 사이 triple 로 이웃 label 사전을 만들고, 목적 label 에서 조건 label 로 거꾸로 트리를 펼친다. 조건 label 이 없는 경로와 cycle 을 지우고 LLM 이 무관 경로를 자른 뒤, 조건 엔티티에서 출발해 hop 마다 다음 label 을 만족하는 이웃만 남긴다 | label 그래프 = 스키마 크기, 트리 깊이 = 질문 hop 수. 엔티티 단계는 label 을 만족하는 이웃 수 | ORT §2.2 |
| 계층 라우팅 | DBCopilot 은 root → DB → table 스키마 그래프에서 (DB, tables) 경로를 생성하고, 디코딩한 노드에서 닿는 이름만 prefix tree 로 허용한다. PubMed 는 MeSH 상위 term 하나로 하위 term 을 자동 포함한다. LeanRAG 는 seed 엔티티에서 집계 계층의 최소 공통 조상까지 위로 올라가며 최소 부분그래프를 모은다 | 계층 깊이 × beam. 하위 펼치기는 후손 수만큼 질의를 키운다 | DBCopilot §2.1; PubMed User Guide; LeanRAG §4.2 |
| 용어집·시소러스 정규화와 확장 | SKOS 에서 prefLabel·altLabel·hiddenLabel(오타 변형)이 같은 개념을 가리킨다. PubMed 는 tag 없는 질의어를 Subject 번역표 → Journals → Author → Investigator 순으로 맞추고 처음 맞은 표에서 멈춘다. 맞춘 뒤 broader·narrower 로 펼친다 | 사전 조회는 질의어 수, 펼치기는 후손 수. LLM 0회 | SKOS §5.1, §8; PubMed User Guide |
| 온톨로지 원소를 색인 키로 | OG-RAG 는 문서를 온톨로지 속성-값 쌍의 hyperedge 로 바꾸고 key·value 유사도로 hypernode 2k 개를 고른 뒤, 그것을 가장 많이 덮는 hyperedge 를 greedy 로 더한다. OntoRAG 는 질의 핵심어를 지정 수준 class 에 맞추고 그 class 의 원본 chunk 를 앞뒤 문맥과 가져온다 | OG-RAG 공개 코드는 hypernode 전체를 정렬해 선형이고 질문 시점 LLM 이 없다. OntoRAG 는 질의 때 핵심어 추출 LLM 1회 + 색인 1M token 에 300분 | OG-RAG §4.2; `ontograph_query_engine.py:230-236`; OntoRAG §III, §V-C |

### 수치

- Ontop 은 BSBM 2억 triple 에서 SPARQL → SQL 변환이 4~15 ms 였고 시간당 40만 질의를 넘게 처리했다(§4.3). 저자는 성능이 데이터셋 크기보다 온톨로지·mapping 조합의 복잡도에 더 좌우된다고 적는다.
- TIARA 에서 schema 검색을 빼면 GrailQA dev F1 이 81.9 → 79.2 다(Table 3).
- CRUSH4SQL 의 r@10 은 SpiderUnion(원소 4,502)에서 0.83(DPR 0.77), SocialDB(원소 17,844)에서 0.58(DPR 0.49)이다(Table 2). "Very large budget worsens SQL accuracy"(Table 3 캡션). 실험 budget 은 3~100 이고 기본 후보 크기는 100 이다.
- "The Death of Schema Linking?" 에서 스키마가 context 에 들어가면 linking 없이 넣은 파이프라인이 BIRD 실행 정확도 71.83% 로 1위였다. 걸러내기를 세게 할수록 필요한 column 이 빠져 ft:GPT-4o 가 67.35% → 55.78% 로 떨어졌다(Table 1·2). 작은 모델이나 context 를 넘는 스키마에는 여전히 다단계 검색이 필요하다고 적는다.
- Pangu 는 Codex in-context 에서 학습 예시 1개로 GrailQA EM 50% 를 넘었고, 예시 1,000개 미만에서는 모든 미세조정 모델보다 좋았다(§5.2).
- ORT 는 DeepSeek-v3 로 WebQSP Hit@1 89.4, CWQ 72.9 를 냈다(RoG 85.7, 62.6, Table 1). ToG 와 직접 비교하지 않았고 LLM 호출 수도 보고하지 않았다.
- DBCopilot 의 Bird DB R@1 은 88.92, BM25 는 57.11 이다(Table 2).
- LeanRAG 의 검색 context 는 baseline 보다 평균 46% 작았다(UltraDomain 4개 도메인, token 수로 셈, §5.2).
- OG-RAG 의 Soybean context recall 은 0.84 로 RAG 0.22, GraphRAG 0.41 보다 높다(Table 1). OntoRAG 는 1M token 색인에 300분이 걸려 GraphRAG(281분)보다 오래 걸렸고, 저자는 큰 코퍼스나 실시간 용도에 맞지 않는다고 적는다(§V-C, §VI).
- 용어집·시소러스 질의 확장의 효과 수치는 원문으로 확인하지 못했다(#확인하지 못한 것).

### 실패 조건

- linking recall 이 실행 정확도의 상한이다. SLR 은 schema linking recall 이다. "SLR as obtained from schema linking represents an upper bound on possible EX"(Death of Schema Linking §4.3).
- OWL 2 QL 은 first-order rewriting 을 지키려고 SameIndividual 같은 구문을 뺐다(OWL 2 Profiles §3.1). 생성된 SQL 이 subquery 의 큰 UNION 이 되면 Stardog 보다 느리다(Ontop NPD 벤치마크, §4.3).
- 고차수 엔티티는 닿는 relation 이 많아 후보가 폭증한다. Pangu 저자는 후보 1,000개 상한이 성능을 일부 희생한다고 적는다(Appendix C).
- ORT 는 label 을 만족하는 이웃이 너무 많으면 top_k 를 무작위로 뽑는다(§2.2). [추정] 온톨로지를 데이터의 relation label 로 만들어서 사람이 정한 스키마와 데이터 표기가 다르면 경로가 끊긴다(사례: ORT 부록 B 가 데이터셋 relation label 로 온톨로지를 구성, 1건).
- Graphiti 의 Neo4j full-text 경로는 index 가 limit 개를 먼저 돌려준 뒤 WHERE filter 를 적용한다(`search_utils.py:203-206, 273-286`). [추정] 그래서 edge_types 필터를 걸면 결과가 limit 보다 적게 나온다(사례: 이 호출 순서, 1건). #8 의 후필터 실패와 같은 꼴이다.
- PubMed ATM 은 처음 맞은 번역표에서 멈추고, 따옴표 구문·field tag 는 ATM 을 끈다. 다만 Subject 표 매칭은 MeSH term 과 all fields 검색을 OR 로 묶어서 틀린 개념으로만 가지는 않는다(PubMed User Guide).
- `skos:broader` 는 transitive 가 아니라서 펼치기 깊이를 따로 정해야 한다(SKOS §8.6.6).
- 온톨로지가 적재 때만 쓰이고 검색 경로에서 빠지는 구현이 있다. cognee 는 온톨로지 매칭(difflib cutoff 0.8)을 적재 때만 하고 retrieval·search 모듈에는 ontology 참조가 없다. TrustGraph 의 질의 시점 서비스가 부르는 `select_relevant_subset` 은 정의가 없다(`query_service.py:279`, grep 0건).
- OG-RAG 저자는 도메인 온톨로지가 없을 수 있다는 한계를 적는다(§4.1.1). 평가는 문서 149건 이하다.

### 예문

| 장치 | 처리 |
|---|---|
| 용어집 정규화 | '핸드오버 실패' → 개념 HO_FAIL(별칭 'HO fail', 'handover failure', 'HO 실패'). narrower 로 'Xn HO 실패', 'N2 HO 실패' 를 한 단계만 펼친다 |
| 값·타입 제약 | '지난 분기' → 날짜 범위 2026-07-01 ~ 2026-09-30. '펌웨어 버전' → 답 타입 FirmwareVersion |
| label 경로 먼저 | 목적 label FirmwareVersion 에서 거꾸로: FirmwareVersion ← Cause ← Report → Symptom(HO_FAIL). 이 label 경로를 따라 조건 엔티티 HO_FAIL 에서 내려간다 |
| OBDA | 보고서가 관계형 DB 에 있고 mapping 이 있다면 '핸드오버 실패 ⊑ 이동성 장애' 같은 계층을 SQL 로 컴파일해 DB 가 실행한다 |

## 7. 실무 시스템과 규모 벤치마크

배포된 KG 검색 시스템은 하나도 전체 그래프를 보지 않는다. 모두 질문에서 seed 를 고르고, seed 에서 hop·LIMIT 로 묶인 만큼만 넓힌 뒤, 고정된 token 예산에 맞게 잘라 넣는다.

### 시스템

| 시스템 | seed | 확장 | 묶기 | 출처 |
|---|---|---|---|---|
| LinkedIn 고객지원 KG | LLM 이 질문을 key-value 엔티티로 파싱 → 엔티티마다 그래프 노드와 cosine → 같은 티켓 노드 점수를 합해 상위 K 티켓 | 고른 티켓 ID 로 질문을 다시 써 Cypher 로 subgraph. 실행이 실패하면 텍스트 검색으로 물러난다 | — | arXiv 2404.17723 §3.2 |
| Neo4j retriever 들 | vector index 에서 top_k × effective_search_ratio 를 받아 LIMIT top_k. Hybrid 는 vector·full-text 각 top_k 를 각자 최댓값으로 정규화해 UNION 후 노드별 max | VectorCypher 는 seed `node` 에 사용자가 쓴 Cypher 를 이어 붙여 그 패턴만 따라간다 | — | `neo4j_queries.py:38-67, 197-223, 551-579` |
| Amazon Bedrock KB GraphRAG | vector search 로 관련 노드 | 찾은 chunk 에 연결된 노드·chunk 만 traverse. 데이터 소스당 파일 수 기본 1,000(요청 시 10,000), 그래프 구축 방식은 설정 불가 | — | AWS Bedrock User Guide |
| AWS graphrag-toolkit TopicBeamSearch | topic 벡터 검색 50개 | beam 100, 깊이 6. 같은 chunk·인접 chunk 이웃만 기본으로 따르고 공유 엔티티 이웃은 꺼 둔다(켜면 topic 당 100개) | 이긴 topic 만 statement 로 펼침 | `traversal-based-search.mdx:97-120` |
| Zep / Graphiti | cosine, BM25 | BFS 를 설정에 넣으면 앞 결과 source 노드에서 n-hop. 기본 limit 10, 최소 유사도 0.6, BFS 최대 깊이 3 | RRF·MMR·episode 언급 수·노드 거리·cross-encoder 재순위 → constructor 가 문맥 생성 | Zep §3; `search_config.py:29`, `search_utils.py:65-67` |

MS GraphRAG 의 local·global·dynamic·DRIFT 경로는 #4 표에 있다.

### 수치

- LinkedIn KG RAG 는 같은 LLM·임베딩의 텍스트 baseline 보다 MRR 이 0.522 → 0.927(+77.6%), BLEU 가 0.32 높았다. 고객지원팀에 약 6개월 배포하는 동안 티켓 해결 시간 중앙값이 7h → 5h(−28.6%)로 줄었다(Table 1·3). KG 크기는 원문에 없다.
- LongMemEval 에서 full-context 는 평균 115k token 을 쓰고 Zep 은 1.6k token 을 썼다. gpt-4o 정확도는 60.2% → 71.2%, 지연은 28.9 → 2.58 s 다(gpt-4o-mini 55.4 → 63.8%, 31.3 → 3.20 s, Zep Table 2).
- STaRK 의 KB 는 Amazon 1.04M 엔티티·9.4M 관계, MAG 1.87M·39.8M, Prime 129k·8.1M 이다. LLM reranker 를 뺀 검색기 가운데 최고 Hit@1 은 Amazon 46.10%(ColBERTv2), MAG 37.90%, Prime 15.57%(GritLM-7b)다(합성 질의 전체 test, Table 6). LLM reranker 는 test 의 무작위 10% 표본에서만 쟀고, GPT-4 reranker 의 Prime Hit@1 은 18.28% 다(Table 6). ada-002 top-20 을 다시 보는 LLM reranker 를 붙이면 평균 지연이 세 KB 평균 2.83 s 에서 25~26 s 로 는다(Table 8).
- CRAG 는 5개 도메인 2.6M 엔티티 mock KG 를 38개 mock API 로만 열어 준다. LLM 단독은 정확도 34% 이하, 단순 RAG 를 붙여도 44% 이고, 업계 최고 시스템도 truthfulness 51% 다(Table 5·6).
- CypherBench(7.8M 엔티티, property graph 11개)에서 가장 좋은 claude3.5-sonnet 의 execution accuracy 는 61.58% 이고, 10B 미만 모델은 20% 에 못 미친다(§6.2 Table 3). Wikidata 는 엔티티 타입 4백만 개 이상, relation 타입 12,000개라 도메인별 property graph view 를 만들어 스키마를 줄였다(그래프당 relation 타입 평균 7.5개, §2.2·Table 6).
- GraphRAG-Bench("When to use Graphs in RAG") Novel 에서 단순 사실 검색 ACC 는 rerank 붙인 RAG 60.92, HippoRAG2 60.14, MS-GraphRAG 49.29 다. 복잡 추론은 HippoRAG2 53.38, RAG 42.93 이다(Table 2).
- 같은 논문의 prompt 크기는 본문(Obs.8–9)과 그림이 어긋난다. 본문은 HippoRAG2 약 10^3, LightRAG 약 10^4, MS-GraphRAG global 최대 4×10^4 token 이라 적지만, Figure 8–9 의 평균은 global 331,375, LightRAG 100,832, HippoRAG2 1,008 이다.
- RAG vs GraphRAG 비교에서 HotpotQA 로 만든 KG 에는 답 엔티티가 약 65.8% 만 들어 있었다. 단일 hop NQ 는 RAG 가(F1 64.78 대 HippoRAG2 61.03), multi-hop HotpotQA 는 HippoRAG2 가(63.01 대 60.04) 앞섰다. 구축 시간은 RAG 135 s, KG-GraphRAG 7,702 s 다(§4.2, §4.5).
- Zhou 외 통합 비교에서 질의당 비용은 HippoRAG 3.46 s·3,261 token, ToG 69.74 s·16,860 token 이다(MultihopQA, Table 6). global GraphRAG 는 MultihopSum 에서 521 s·353,889 token 이 들었다(Table 10). 저자는 모든 community 를 map-reduce 로 분석해야 해서 실무에서 감당할 수 없다고 적는다(§7.3).
- AWS graphrag-toolkit 문서는 statement 마다 임베딩을 두는 semantic-guided search 가 큰 데이터셋에서 "queries often taking minutes to complete" 라고 적고, chunk 벡터 검색 뒤 그래프를 걷는 방식을 권한다(`traversal-based-search.mdx:18-24`).

### 실패 조건

- 답 엔티티가 KG 에 아예 없으면 seed 가 생기지 않는다(HotpotQA KG 65.8%).
- 변화가 빠른 사실, 인기가 낮은 엔티티, 복잡도가 높은 질문에서 정확도가 특히 낮다(CRAG §5).
- 여러 속성을 섞은 반정형 질의에서 seed 가 빗나간다. 앞 단계 recall 에서 정답이 빠지면 GPT-4 reranker 로도 Prime Hit@1 이 18.28% 다(STaRK §3.2, Table 6 의 10% 표본).
- fan-out 이 큰 엣지는 noise 를 늘린다. AWS toolkit 은 공유 엔티티 이웃을 "large fan-out and tends to add noise" 라서 기본으로 끈다.
- 스키마가 너무 크거나 모델이 작으면 Cypher 가 빗나간다. CypherBench 오류는 관계 방향 반전, entity linking, 질문과 어긋난 패턴 등이다(§6.6).
- Zep 은 single-session-assistant 질문에서 full-context 보다 낮다(gpt-4o 94.6 → 80.4%, Table 3).
- 그래프 크기만 바꿔 가며 품질과 지연을 잰 통제 실험은 찾지 못했다. 규모 효과는 서로 다른 크기의 데이터셋 결과에서 간접으로 읽어야 한다.

### 예문

LinkedIn 식으로 처리하면 질문을 {RAT: NR, 증상: 핸드오버 실패, 기간: 2026 Q3, 관심 속성: 펌웨어 버전} 으로 파싱한다. 보고서마다 섹션 노드 점수를 합해 상위 K 보고서를 고르고, "보고서 R-1021·R-1188 의 원인 섹션과 펌웨어 필드" 를 묻는 Cypher 로 다시 쓴다. 보고서가 티켓처럼 자연스러운 묶음 단위가 된다. Cypher 가 실패하면 텍스트 검색으로 물러난다.

## 8. 필터를 건 벡터 검색

질문의 기간·버전·타입 조건을 metadata 필터로 걸고 그 안에서 ANN 을 돈다. 필터를 언제 거느냐에 따라 전체를 안 보는 방식이 갈린다. 이 절에서 n 은 벡터 수, K 는 돌려줄 개수, 선택도 s 는 필터를 통과하는 행의 비율이다.

비용은 ACORN 이 정리했다(§3.2). 선필터는 통과 집합 전체와 거리를 계산해 O(sn+K) 이다. 후필터는 통과 집합이 고르게 퍼져 있으면 기대 비용이 O(log n + K/s) 다. 그래서 선필터는 데이터 크기와 선택도에 선형으로 커지고, 후필터는 s 가 작을수록 커진다.

### 기제

| 기제 | 무엇을 몇 개로 줄이나 | 비용이 비례하는 것 | 쓰는 곳 | 출처 |
|---|---|---|---|---|
| 후필터 | ANN 이 후보 ef_search 개(탐색 때 들고 다니는 후보 수)를 내고, 필터가 그중 s 만큼 남긴다. pgvector 기본값에서 s=10% 면 40개 중 평균 4개다 | O(log n + K/s). 통과하지 못한 노드에도 거리 계산을 쓴다 | pgvector(iterative scan 끔), LanceDB postfilter, Graphiti full-text 경로(#6) | ACORN §3.2; pgvector README #Filtering |
| 반복 후필터 | 결과가 모자라면 index 를 더 훑는다. pgvector 0.8.0 은 `hnsw.max_scan_tuples`(기본 20,000) 또는 `ivfflat.max_probes` 에서 멈춘다 | 방문 tuple 수가 대략 K/s. 상한이 비용을 묶는다 | pgvector 0.8.0 이상 | pgvector README #Iterative Index Scans |
| 선필터 + exact 전수 | B-tree·inverted·payload index 가 n 을 통과 집합 sn 으로 줄이고, 그 안의 모든 벡터와 거리를 계산한다. recall 은 늘 1 이다 | O(sn+K). 통과 집합 크기에 선형 | neo4j-graphrag 필터 경로(#1), Graphiti `edge_similarity_search`, Qdrant·Weaviate 의 작은 필터 경로, LanceDB `bypass_vector_index()`, ACORN fallback | ACORN §3.2; Graphiti `search_utils.py:324-350, 418-433` |
| 탐색 중 필터(allow-list) | inverted index 가 통과 id 목록(roaring bitmap)을 만든다. HNSW 는 edge 를 평소대로 따라가고 결과에는 목록 안 노드만 넣는다 | graph 를 바꾸지 않아 build 비용이 그대로다. 필터가 엄격할수록 방문 수가 전수에 가깝다 | Weaviate sweeping, Weaviate PathSeer(v1.40) | Weaviate Filtering 문서 |
| predicate subgraph 탐색(ACORN) | 이웃 목록에서 통과 노드만 따라가고, 모자라면 2-hop 이웃까지 펼친다. 그래서 predicate 마다 따로 지은 HNSW 를 흉내 낸다 | ACORN-γ 는 이웃 목록을 M·γ 로 늘려(γ=1/s_min, s_min 은 서비스할 최소 선택도) build 가 HNSW 의 γ·log γ 배다. 펼치기를 탐색 때만 하는 ACORN-1 은 색인 시간이 9–53배 작고 QPS 가 최대 5배 낮다 | ACORN(FAISS 구현), Weaviate(v1.34 부터 기본), Qdrant(v1.16 이상) | ACORN §5.2, §6.2 |
| 필터를 아는 색인 구축 | build 때 label(또는 payload 값)마다 시작점을 두고 같은 label 끼리 연결을 보장한다. 그래서 통과 노드만으로도 graph 가 이어진다 | label 수와 점마다 붙은 label 수에 비례해 edge·build 가 는다. Qdrant 는 payload index 를 적재 뒤에 만들면 HNSW 를 다시 짓는다 | Filtered-DiskANN, Qdrant filterable HNSW | Filtered-DiskANN §1; Qdrant Indexing 문서 |
| partition | 필터 값이 가리키는 partition 하나나 몇 개만 훑는다 | partition 마다 index 를 둬 값이 많을수록 관리 비용이 는다. Milvus 수동 partition 상한 1,024개. partition key 는 hash 를 `partitions_num`(기본 16)으로 나눈 나머지라 한 partition 에 여러 값이 섞인다 | Milvus partition key, pgvector partial index·LIST partitioning, ParlayANN | Milvus Use Partition Key; Big-ANN'23 §4.1 |
| cardinality 기반 계획 | payload index 로 필터 결과 크기를 어림해 위 경로 하나를 고른다. 작으면 exact, 크면 filterable HNSW, 비율은 낮은데 개수가 크면 ACORN 이다 | 어림과 segment 별 계획. 경계값(Qdrant `full_scan_threshold` 10,000 KB 등)은 설정에 묶인다 | Qdrant, ACORN(s_min 규칙), ParlayANN, Weaviate flat-search cutoff | Qdrant Search #Query Planning; ACORN §5.2 |

운영 시스템(Qdrant, Weaviate, ACORN)은 모두 이중 경로다. 필터 결과가 작다고 어림하면 exact 전수로, 크면 그래프 안 필터 탐색으로 간다(Qdrant Search #Query Planning, Weaviate #Flat-Search Cutoff, ACORN §5.2).

### 수치

- LAION-1M 에서 질문과 필터의 상관을 바꾼 세 workload 모두, ACORN-γ 는 0.9 recall 에서 다음으로 좋은 baseline 보다 QPS 가 28–100배 높았다. 후필터는 양의 상관에서도 recall 0.9 를 넘지 못했다(ACORN §7.3.2, Figure 10). 25M 벡터에서는 1,000배 이상이라고 적는다(§1).
- pgvector 는 조건이 10% 를 맞추면 기본 `hnsw.ef_search` 40 에서 평균 4행만 돌려준다(README #Filtering).
- Filtered-DiskANN 은 label 을 가진 점의 비율이 10^-4~10^-6 이어도 recall 을 100% 가까이 맞췄고, IVF·HNSW·NHQ·Milvus baseline 보다 한 자릿수 이상 효율이 좋았다(§1).
- NeurIPS'23 Big-ANN filtered track(YFCC 10M CLIP 벡터, tag 어휘 200,386개, 질문당 tag 1~2개를 AND)에서 1위 ParlayANN 은 recall@10 ≥ 0.9 에서 QPS 37,671, Faiss baseline 은 3,253 이었다(Table 2). ParlayANN 은 흔한 tag 에는 Vamana graph 를 두고 드문 tag 는 순차 저장했다(§4.1).

### 실패 조건

- 후필터는 필터가 엄격하거나 질문 벡터와 음의 상관일 때 무너진다. 통과 노드 쪽으로 route 하지 못하고(ACORN §7.3.2), 결과가 limit 보다 적거나 0건이 된다(pgvector README, LanceDB Filtering 문서).
- 반복 후필터는 필요한 tuple 수가 상한을 넘으면 다시 모자란다. 상한을 올리면 전수에 가까워진다(pgvector README #Iterative Scan Options).
- 선필터 전수는 통과 집합이 크면 선형 비용이 그대로 드러난다. ACORN 은 이를 "scales poorly" 라고 적는다(§1). Graphiti 에서는 group 하나의 edge 수가 커질 때다.
- allow-list 탐색은 필터가 매우 엄격하면 HNSW traversal 이 "exhaustive" 해진다. 그래서 Weaviate 는 flat-search cutoff 아래에서 통과 부분집합만 brute-force 로 훑는다(Weaviate #Efficient Pre-Filtered Searches).
- ACORN 은 선택도가 1/γ 아래면 predicate subgraph 가 끊겨 선필터로 넘긴다. 선택도 어림이 틀리면 품질이 아니라 효율만 잃는다고 논증한다(§5.2). build 때 정한 γ 가 서비스할 최소 선택도를 묶는다.
- 미리 index 해 두지 않은 술어 조합에서 실패한다. Qdrant 의 extra edge 는 payload index 하나씩만 만들어서 strict filter 두 개 이상을 조합하면 graph 가 끊길 수 있다(Qdrant Indexing 문서). Filtered-DiskANN·NHQ 는 술어 종류가 많거나 등호가 아닌 술어에서 돌지 못했고, Milvus 는 regex 와 가변 길이 list 의 contains 술어를 지원하지 않았다(ACORN §7.3).
- partition 은 필터가 partition key 가 아닌 필드이거나 여러 값을 조합할 때 안에서 다시 걸러야 한다. tenant 를 공유 index 에 넣으면 한 tenant 의 벡터가 다른 tenant 의 recall 에 영향을 준다(pgvector README #Multitenancy).
- 남는 빈틈은 두 곳이다. 선택도는 낮은데 통과 개수는 여전히 큰 중간 구간, 그리고 미리 index 하지 않은 필터 조합(등호가 아닌 범위·regex 술어, strict filter 여럿)이다.

### 예문

| 조건 | 처리 |
|---|---|
| 펌웨어 3.2.1 | 매우 선택적이다. 선필터로 그 버전이 붙은 claim 만 꺼내 전수로 순위를 매기면 recall 1 이다 |
| 지난 분기(2026-07-01 ~ 2026-09-30) | 범위 술어다. 수년 치 보고서라면 통과 비율이 중간이라 선필터 전수는 비싸고 후필터는 근처에 통과 노드가 적으면 비게 된다 |
| RAT=NR AND 펌웨어 3.2.1 AND 지난 분기 | strict filter 셋의 조합이다. Qdrant 식 extra edge 는 하나씩만 이어 두어 graph 가 끊길 수 있다. 계획기가 결과 크기를 어림해 exact 로 넘기는 편이 안전하다 |

## 9. 집계·전수 질문

'몇 건', '모든 X' 처럼 답 집합이 k 보다 크면 top-k 검색은 재현율이 막혀 집계 답이 구조적으로 틀린다. S-RAG 는 고정 K 에 대해 "Any question that requires integrating information from more than K sources cannot be fully addressed." 라고 적는다(§2).

원문이 보이는 처리 길은 셋이다. 형식 질의를 DB 엔진이 실행하거나, 색인 때 레코드 표를 만들어 두거나, 순위 대신 조건 필터로 전수를 훑는다.

### 기제

| 기제 | 무엇을 몇 개로 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 고정 top-k 순위 검색(대조군) | 말뭉치 chunk 전체(AGGBench 16,294개)에서 유사도 상위 k 개(5~50)만 남긴다. 근거가 k 개를 넘으면 나머지는 처음부터 후보 밖이다 | 임베딩 검색 1회, context 가 k 에 비례 | AGGBench §1; S-RAG §2 |
| 형식 질의를 DB 엔진이 실행 | LLM 은 질문과 스키마만 보고 질의를 한 번 쓴다. 전수 필터와 count·avg 는 엔진이 모든 행·노드에 돌린다. LLM 에는 결과 표만 들어간다(#3) | LLM 1회, prompt 가 스키마 크기에 비례. TAG 가 LM UDF 를 쓰면 필터를 통과한 행 수만큼 LM 을 부른다 | TAG §2.1; CypherBench §4.1; neo4j-graphrag `text2cypher.py:208-237` |
| 색인 때 레코드 표(S-RAG) | 색인 때 문서 12개와 질문 10개로 schema 를 정하고, 문서 n 개를 레코드 n 개로 바꿔 SQL 표에 넣는다. 질의 때 SQL 한 번이 집계를 끝낸다. Hybrid 모드는 SQL 이 문서 부분집합을 돌려주고 그 위에서 RAG 를 한다 | 색인 때 문서당 LLM 1회 + schema 예측 몇 회. 질의 때 text-to-SQL 1회 + 답 1회 | S-RAG §3.2–3.3 |
| 질의 때 구조화(StructRAG) | router 가 질문과 문서마다 제목·첫 문장만 보고 구조 종류를 고른다(통계면 table). structurizer 가 그 종류로 문서마다 지식을 뽑아 합친다 | 질의마다 문서 수에 비례하는 LLM 호출. 미리 색인하지 않는다 | StructRAG §3 |
| 요약 위 map-reduce(GraphRAG global, #4) | community report 배치마다 map 하고, reduce 는 점수 순으로 `data_max_tokens`(기본 12,000)를 넘기 전까지만 넣는다 | map 호출이 report 배치 수에 비례 | `global_search/search.py:172-181, 373-377`; `defaults.py:201` |
| 조건 필터 + 되돌리기(DFA) | 질문의 모호성을 먼저 푼 뒤 exact·fuzzy matching 도구로 chunk snapshot 을 거듭 거른다. 버린 chunk 를 보존해 지나치게 걸렀으면 되돌린다. 남은 후보를 묶어 배치마다 LLM 판정과 중복 제거를 한다 | 필터 도구는 말뭉치 전체를 LLM 없이 훑는다. LLM 은 필터 반복 수와 후보 배치 수에 비례 | AGGBench §5.2 |

### 수치

- AGGBench-Core 에서 Naive RAG 의 k 를 5 → 50 으로 늘리면 chunk recall 은 0.042 → 0.072 이고 NACE 평균은 0.463 → 1.855 로 나빠진다. LightRAG recall 은 0.033 → 0.147 이다(Appendix A.7.1, Table 7).
- TAG 벤치마크(BIRD 에서 고친 80문항, 유형마다 20개)에서 행 임베딩으로 10행을 가져오는 RAG 는 모든 유형에서 EM 0.00, Text2SQL 은 0.17, 손으로 짠 TAG 파이프라인은 0.55 다(Table 1). aggregation 유형은 정량으로 재지 않았다(Table 1 각주).
- QUEST(3,357문항, 답 entity 최대 20개·평균 10.5개)에서 T5-Large dual encoder 의 R@100 은 0.476, MRecall@100 은 0.142, 분류기를 붙인 끝단 F1 은 0.192 다(Table 3·4). 교집합 질의 F1 은 0.092 로 합집합 0.282 보다 낮다(Table 5).
- CypherBench 는 k-hop 이웃이나 top-k entity 를 가져오는 근사 검색이 entity 가 많은 질문을 원리상 다루지 못한다고 보고 text-to-Cypher 를 택했다(§7, Table 5). 정확도는 #7 에 있다.
- S-RAG 의 Answer Comparison 은 Hotels 에서 VectorRAG 0.331, 추론한 schema 0.518, 정답 schema 0.899 이고, WorldCup 에서 0.676, 0.769, 0.856 이다(Table 3). WorldCup 평균 득점 예시에서 VectorRAG 는 22개 대회 중 13개만 context 에 받았다(§6).
- Loong Clustering 과제 EM 은 StructRAG 가 Set 1~4 에서 0.23, 0.17, 0.10, 0.00, RAG 가 0.05, 0.05, 0.02, 0.00, GraphRAG 가 0.14, 0.00, 0.00, 0.00 이다(StructRAG Table 1). Set 번호가 클수록 문서가 길다.
- DFA 의 AGGBench-Core recall 은 0.623 으로 최고 baseline(LightRAG 0.096)의 5배를 넘는다. 전체 AGGBench 에서 GPT-4o-mini 는 recall 0.211, Qwen3-32B 는 recall 0.482 지만 NACE 평균 1.733 이다(Table 1·2).

### 실패 조건

- 순위 검색은 답 집합이 k 를 넘을 때, 질문과 근거의 낱말이 다를 때, 교집합·부정 조건이 있을 때 실패한다. QUEST 오답 분석에서 모델은 교집합을 합집합처럼 다뤘고 부정 조건에 둔감했다(§5). 여러 번 검색하는 OpenAI Responses 도 언제 멈출지 몰라 근거를 다 모으지 못했다(S-RAG §6, Table 5).
- 형식 질의는 조건이 스키마 속성에 없는 의미 판단일 때 실패한다. TAG 에서 Text2SQL 은 추론이 필요한 질문에서 10% 였다(§4.3). entity linking 과 관계 방향 오류도 그대로 온다(CypherBench §6.6).
- 레코드 표는 schema 가 속성을 놓치거나 단위·표기를 표준화하지 못할 때 무너진다. S-RAG 는 schema 를 추론하게 하면 FB-Agg 에서 0.234 로 VectorRAG 0.598 보다 낮았고, 1M 과 1B 가 둘 다 1 로 기록된 사례를 든다(§6, Table 3). 목록·중첩 속성은 다루지 않는다.
- 질의 때 구조화는 문서 총량이 커질수록 정확 일치가 0 에 가깝고, 질의마다 문서 전체를 다시 읽어야 한다(StructRAG Table 1).
- 요약 map-reduce 는 요약이 레코드를 하나씩 담지 않고, reduce 예산이 다시 top-k 처럼 자른다. S-RAG 는 이 방식이 "not built to handle aggregative queries" 라고 적는다.
- DFA 오류의 약 15% 는 도구 인자를 잘못 준 데서 왔다(§6.4.2). 전체 AGGBench 에서 recall 은 최고지만 오차는 최고가 아니다.

### 예문

> 지난 분기 NR 핸드오버 실패 보고는 몇 건이고, 펌웨어 버전별로 나누면?

| 방식 | 처리 |
|---|---|
| top-k | 보고서가 k 건을 넘으면 그만큼 세지 못한다. k 를 늘리면 무관한 chunk 가 섞인다 |
| 레코드 표 | 보고서마다 {RAT, 증상, 원인, 펌웨어, 날짜} 레코드를 색인 때 만들고 `GROUP BY 펌웨어` 로 센다. 작성자마다 'HO fail', '핸드오버 실패' 로 다르게 쓰면 칸 값을 먼저 정규화해야 한다(S-RAG 의 단위 표준화 실패와 같은 꼴) |
| DFA 식 필터 | '핸드오버'·'HO' 로 chunk 를 문자열 필터하고, 지나치게 걸렀으면 되돌린 뒤 배치마다 LLM 이 해당 여부를 판정해 중복을 뺀다 |

## 10. 질문 유형 라우팅

질문마다 검색 경로를 고른다. 줄이는 대상은 데이터가 아니라 경로다. 원문으로 확인한 기제는 넷이다. 운영 시스템인 GraphRAG·LightRAG 는 자동 라우터 없이 사용자 지정이나 병합을 쓴다.

### 기제

| 기제 | 무엇을 몇 개로 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 검색 전 복잡도 분류기(Adaptive-RAG) | 질문 하나를 세 전략(검색 없음, 한 번 검색, 여러 번 검색) 가운데 하나만 실행한다. 예측 분포는 8.60%, 53.33%, 38.07% 다 | 분류기는 질문당 T5-Large(770M) 1회. 나머지는 고른 경로가 정한다(질문당 0.35, 3.08, 27.18 s) | Adaptive-RAG §3.2, Table 3 |
| 싼 경로 먼저, 'unanswerable' 이면 비싼 경로(Self-Route) | 모든 질문을 top-k chunk(약 1.5k 토큰)로 먼저 풀게 하고, LLM 이 답할 수 없다고 한 질문만 전체 문맥(10k~100k 토큰)으로 넘긴다 | 모든 질문이 RAG 1회, 넘어간 질문만 LC 1회 더 | Self-Route §4.2 |
| LLM selector | 경로 N 개의 설명문과 질문을 LLM 에 주고 하나(또는 `max_outputs` 개 이하)를 고르게 한다. 여럿을 고르면 모두 돌려 TreeSummarize 로 합친다. LlamaIndex 의 EmbeddingSingleSelector 는 설명 임베딩과 질문의 top-1 유사도로 고른다 | 질문당 LLM 1회. 입력은 데이터가 아니라 경로 설명문 크기에 비례 | Han 외 §4.5; LlamaIndex `router_query_engine.py:99, 164-181`; cognee `select_search_type.py:30-53` |
| 학습한 RAG-aware 라우터(RAGRouter) | 질문과 검색 문서를 임베딩해 후보 LLM 15개의 'RAG capability' 벡터와 견줘 답할 모델 하나를 고른다. 검색 경로가 아니라 모델을 고른다 | 라우터 약 136M 모델 1회 | RAGRouter §4 |
| critic 피드백으로 다시 라우팅(HybGRAG) | router 가 질문을 텍스트 측면과 관계 측면으로 나누고, critic 이 검색 결과의 틀린 곳을 짚으면 다시 라우팅한다 | 반복 수 × (router + critic) LLM 호출 | HybGRAG §2.2–2.3 |
| 라우터 없음 | 범위를 줄이지 않는다. GraphRAG CLI 는 사용자가 `--method` 로 고르고 기본값은 global 이다. LightRAG `QueryParam` 기본 mode 는 KG 와 벡터 검색을 함께 쓰는 `mix` 다 | 병합이면 질문마다 모든 경로 비용. global 기본이면 질문마다 report 전체 map-reduce | graphrag `cli/main.py:381-386, 439`; LightRAG `base.py:93-99` |

### 수치

- Adaptive-RAG(FLAN-T5-XL)는 F1 46.94, 상대 시간 3.60 이다. 여러 번 검색은 F1 48.85, 시간 8.81 이고, 같은 파이프라인에 oracle 분류기를 끼우면 F1 56.28, 시간 2.11 이다(Table 1). 시간은 한 번 검색 대비 상대값이다.
- 그 분류기 정확도는 전체 54.52%, '검색 없음' 30.52%, '한 번' 66.28%, '여러 번' 65.45% 다. 60M 모델로 줄여도 전체 53.48% 다(Table 4·6). 여러 번 검색할 질문의 약 31%, 검색이 필요 없는 질문의 약 47% 가 '한 번' 으로 간다(§5, Figure 3).
- Self-Route 에서 Gemini-1.5-Pro 는 질문의 81.74% 를 RAG 단계에서 끝냈다. GPT-4O 는 LC 토큰의 61% 로 46.83(LC 47.04)을 얻었다. 비용은 Gemini-1.5-Pro 65%, GPT-4O 39% 줄었다(§4.2–4.3). k 를 키우면 넘기는 질문이 줄어 전체 비용 곡선이 단조롭지 않다(§4.4).
- RAG vs GraphRAG 비교에서 질문을 fact-based 와 reasoning-based 로 나눠 보내는 Selection 은 최고 baseline 대비 1.1%, 두 경로를 다 돌려 문맥을 합치는 Integration 은 6.4% 올렸다(MultiHop-RAG, Llama 3.1-70B, §4.5·Table 4). 분류 정확도는 보고하지 않았다.
- RAGRouter 는 평균 정확도 64.46% 로 최고 단일 LLM 60.85% 보다 높다. oracle 은 76.77%, GPT-4o 에 meta-prompt 로 고르게 한 라우터는 55.13% 다(Table 2).
- HybGRAG 의 STaRK-MAG 분석에서 질문마다 맞는 retriever 를 고르는 optimal routing 은 Hit@1 0.4522 로 VSS(벡터 유사도 검색) 0.2908, PPR 0.2533 보다 높다(Table 2). LLM 이 뽑은 subgraph 에 정답이 드는 비율은 피드백 없음 0.6769, 단순 재시도 0.7914, 틀린 곳을 짚는 피드백 0.9231 이다(Table 3).

### 실패 조건

- 분류기는 '검색 없음' 을 가장 못 알아본다. 여러 번 검색할 질문이 '한 번' 으로 새면 한 번 검색으로 끝나 답이 빈다(Adaptive-RAG §5). 학습 라벨은 데이터셋 출처(single-hop 이면 B, multi-hop 이면 C)로 자동으로 만들었다(§3.2). 출처 구분이 없는 사내 질문은 라벨 만드는 법부터 다시 정해야 한다.
- Self-Route 는 LLM 이 '답할 수 있다' 를 잘 판단한다는 가정에 기댄다(§1). RAG 문맥으로도 답하려 드는 Gemini-1.5-Pro 는 긴 데이터셋에서 LC 보다 낮았다(§4.3). RAG 가 실패한 질문은 다단계 추론, 일반적인 질문, 길고 복잡한 질문, 암시적 질문의 네 유형이다(§5.2).
- [추정] Self-Route 는 검색이 모자라면 더 큰 문맥으로 가는 구조라서, 전체를 문맥에 넣을 수 없는 큰 KG 에는 그대로 쓸 수 없다(사례: 논문의 fallback 이 full context 투입 하나뿐, 1건).
- selector 는 데이터를 보지 않고 설명문만 본다. 설명이 겹치거나 질문이 여러 유형에 걸치면 고를 근거가 없다. cognee 는 LLM 응답이 유효한 검색 유형이 아니거나 호출이 실패하면 로그만 남기고 RAG_COMPLETION 으로 떨어져서(`select_search_type.py:23, 30-53`), 오분류가 답 품질 저하로만 드러난다.
- 프롬프트만으로 고르는 LLM 라우터는 최고 단일 모델보다 낮았다(RAGRouter Table 2). 학습한 라우터는 질문·문서 분포와 후보 모델 집합이 고정되어야 한다.
- HybGRAG 에서 LLM 은 첫 시도에서 텍스트 측면과 관계 측면을 잘 가르지 못했다(Challenge 2). Table 3 의 재시도는 정답 포함 여부를 아는 oracle 이 지시한 것이라 실제 critic 의 몫은 따로다.
- 라우터가 없으면 사용자가 질문 유형을 잘못 고를 때 그대로 비싸지거나 틀린다. GraphRAG 문서는 기본값 global search 를 "resource-intensive" 라고 적는다(`docs/query/overview.md:20`).

### 예문

| 라우터 | 예문 질문의 처리 |
|---|---|
| 복잡도 분류기 | 기간·속성 조건이 붙은 원인 질문이라 '여러 번 검색' 으로 보낸다. '한 번' 으로 새면 원인 보고서 하나에서 멈춘다 |
| Self-Route 식 | claim 검색을 먼저 돌리고, LLM 이 펌웨어 관련 원인을 다 찾았는지 판단하지 못하면 레코드 표 경로로 넘긴다 |
| LLM selector | "레코드 표: 기간·버전 조건", "claim 검색: 단일 사실" 같은 설명문 가운데 고른다. 두 설명이 다 맞아 보이면 근거 없이 하나를 고른다 |

## 11. 데이터가 늘 때 갱신과 낡음

미리 만든 범위 축소 구조(벡터 색인, community, 동의어 엣지, 별칭 표)는 데이터가 들어올 때마다 고쳐야 한다. 갱신 방식에 따라 비용과 낡는 곳이 다르다. 시간 질문은 낡은 사실을 거르는 일과 맞물린다.

### 기제

| 기제 | 무엇을 몇 개로 줄이나 | 비용이 비례하는 것 | 출처 |
|---|---|---|---|
| 쓰기 시점 bi-temporal invalidation(Zep/Graphiti) | 사실마다 시각 넷을 둔다. 시스템에 기록·무효화된 시각과, 사실이 참이었던 기간의 시작·끝이다. 새 edge 하나마다 같은 group 에서 BM25+cosine 을 RRF 로 묶은 상위 10개만 후보로 잡는다. LLM 판정과 날짜 비교로 모순인 옛 edge 에 무효 시각을 찍는다 | 새 edge 수 × (hybrid search + LLM 판정·날짜 추출). 그래프 크기에는 색인 검색 비용으로만 묶인다 | Zep §2.2.3; Graphiti `edge_operations.py:558-585, 748-787`, `search_config.py:29` |
| 질문 시점 날짜 범위 주입(Zep) | 사실을 "FACT (Date range: from - to)" 꼴로 context 에 넣어 시간 판단을 답 LLM 에 맡긴다 | 질문 시점 추가 비용 없음 | Zep §3 |
| 증분 community 배정 | 새 엔티티를 이웃 다수가 속한 community 에 넣고 그 summary 만 다시 쓴다 | 새 노드마다 이웃 조회 1회 + LLM 2회(summarize_pair, 이름 생성) + 임베딩 1회 | Zep §2.3; Graphiti `community_operations.py:342-357, 397-434` |
| delta 색인 후 이어 붙이기(GraphRAG update) | 이전 documents 표에 없는 title 만 새 문서로 고르고, 표준 파이프라인을 새 문서에만 돌린다. delta community·report 는 id 를 옮겨 기존 표 뒤에 붙이고, 엔티티는 title 로 묶어 설명만 다시 요약한다 | 새 문서 추출 + delta report + 합친 엔티티 설명 재요약. 기존 report 는 다시 만들지 않는다 | `incremental_index.py:46-58`; `update/communities.py:44-72, 135-138` |
| 그래프 합집합 병합(LightRAG) | 새 문서로 부분 그래프를 만들어 노드·엣지 집합을 합집합으로 합친다. 같은 이름의 설명 목록은 8개(`force_llm_summary_on_merge` 기본값) 이상이거나 토큰 한도를 넘을 때만 LLM 으로 요약한다. 문서를 지우면 남은 문서의 캐시된 추출 결과로 영향받은 엔티티를 다시 짓는다 | 새 문서 추출 + 건드린 엔티티 수 × 조건부 요약. 다시 만들 전역 구조가 없다 | LightRAG §3; `operate.py:386-390, 436-441`; `lightrag.py:6727-6735` |
| streaming ANN 갱신(FreshDiskANN) | 삽입·삭제를 메모리 색인에 모았다가 SSD 색인에 merge 하고, 지운 점 주변 이웃을 다시 이어 탐색 가능성을 지킨다 | merge 의 시간·공간이 바뀐 집합 크기에 비례 | FreshDiskANN §1, §3.3 |
| 질문 관련 부분그래프 + 시간 사실 보강(EXAQT) | 질문 엔티티를 NERD(named entity recognition and disambiguation, 이름 인식과 엔티티 연결)로 찾은 뒤 그 KG 사실을 BERT 로 거른다. GST(Group Steiner Tree, 지정한 노드 묶음을 모두 잇는 최소 트리)로 자르고, 시간 사실을 BERT 로 다시 넣는다 | 후보 사실마다 BERT 1회 + GST 계산. LLM 없음 | EXAQT §3.2 |
| temporal KG embedding(CronKGQA) | 후보를 줄이기보다, 시작·끝 시각이 붙은 temporal KG 에서 질문 임베딩과 TComplEx(시각을 넣은 KG embedding) 점수로 엔티티·시각을 고른다 | 엔티티·시각 후보 전체에 점수 계산. 그래프 크기에 비례 | CronQuestions §6 |

### 수치

- Zep 은 LongMemEval_s 의 temporal-reasoning 정답률을 full-context 대비 gpt-4o-mini 36.5% → 54.1%, gpt-4o 45.1% → 62.4% 로 올렸다. knowledge-update 는 gpt-4o-mini 에서 76.9% → 74.4% 로 떨어졌다(Table 3). context 크기와 지연은 #7 에 있다.
- LightRAG 논문은 GraphRAG 가 새 엔티티를 넣으려면 community 를 다시 만들어야 한다고 보고 그 비용을 1,399 × 2 × 5,000 tokens 로 어림했다(§4.5). 실측이 아니고, 현재 GraphRAG 코드는 재생성 대신 이어 붙인다(`update/communities.py`).
- FreshDiskANN 은 SIFT1M 에서 5% 를 지웠다 다시 넣기를 20회 반복하자 그래프 ANN 색인 HNSW·Vamana·NSG 의 단순 삭제 정책 모두 recall 이 꾸준히 떨어졌다고 보고한다(§3.3, Figure 1). FreshDiskANN 은 실시간 갱신을 받으며 5-recall@5 를 95% 넘게 지키고 신선도 유지 비용을 5–10배 줄였다(초록).
- EXAQT 는 TimeQuestions 에서 후보 사실을 2,491 → 48(BERT) → 49(최단 경로 연결) → 13(가장 큰 덩어리의 GST) → 21(모든 덩어리의 GST) → 67(시간 사실 추가)로 바꿨다. answer recall 은 0.758 → 0.719 → 0.720 → 0.613 → 0.671 → 0.724 다(Table 4). 전체 P@1 은 0.565 로 GRAFT-Net 0.452 보다 높고, 순서를 묻는 ordinal 질문은 0.420 이다(Table 6).
- CronQuestions 에서 CronKGQA 의 Hits@1 은 단순 질문 0.987, 복합 질문 0.392 다. before/after 0.288, first/last 0.371, time join 0.511 이다(Table 5·6).

### 실패 조건

- Graphiti 는 모순되는 옛 edge 가 표현이 달라 hybrid search 상위 10개 밖에 있으면 무효화하지 않는다. 날짜를 뽑지 못해 `valid_at` 이 None 이면 날짜 비교를 건너뛴다(`edge_operations.py:748-787`).
- Graphiti 기본 검색은 만료·무효화된 edge 를 거르지 않는다. `SearchFilters` 의 날짜 필터가 모두 기본 None 이고, 검색 질의는 `expired_at`·`invalid_at` 을 돌려주기만 한다(`search_filters.py:55-65`, `graphiti.py:1945-1958`, `search_utils.py:400-402`). 호출 측이 날짜 필터를 넘기지 않으면 낡은 사실이 섞인다.
- Zep 논문은 약한 모델이 Zep 의 시간 데이터를 이해하려면 개발이 더 필요하다고 적는다(§4.3.2).
- 증분 community 는 이미 소속이 있는 노드를 다시 배정하지 않아 전체 label propagation 결과와 점점 어긋난다. Zep 은 "periodic community refreshes remain necessary" 라고 적는다(§2.3). 이웃이 없는 새 노드는 community 를 얻지 못한다(`community_operations.py`).
- GraphRAG update 는 title 로만 새 문서를 가려서 같은 title 로 내용이 바뀐 문서를 다시 색인하지 않는다. 계산한 `deleted_docs` 는 정의한 파일 밖에서 쓰이지 않아 삭제가 반영되지 않는다(`incremental_index.py:46-58`, `load_update_documents.py:61-62`). 옛 report 가 그대로라 global 검색이 낡은 요약과 새 요약을 함께 본다.
- [추정] LightRAG 는 서로 모순되는 설명을 유효 기간 없이 이어 붙이거나 하나로 요약해서, 어느 쪽이 남을지가 LLM 에 달린다(사례: `operate.py` 의 요약 프롬프트 경로에 시간 규칙이 없음, 1건).
- 삭제 때 edge 만 떼고 보정하지 않는 ANN 은 갱신을 거듭할수록 recall 이 떨어져 주기적 재구축이 필요하다(FreshDiskANN §3.3).
- EXAQT 는 엔티티 연결 recall 0.758 이 상한이고, GST 로 자르면 0.613 까지 떨어져 시간 사실을 넣어야 되살아난다(Table 4). CronKGQA 는 before/after 질문에서 0.288 이다(Table 6). 시간 순서를 따지는 질문은 시각이 붙은 KG 위에서도 가장 어렵다.

### 예문

새 보고서가 "펌웨어 3.2.2 에서 핸드오버 타이머 버그를 고쳤다" 고 적었다고 하자.

| 방식 | 처리 |
|---|---|
| Graphiti invalidation | 새 edge 가 옛 edge "3.2.1 타이머 버그가 HO 실패 원인" 과 대조된다. 옛 보고서가 'HO fail' 로 적혀 hybrid 상위 10개 밖이면 무효 시각이 찍히지 않는다 |
| 질문 시점 | 기본 검색은 옛 edge 와 새 edge 를 함께 돌려준다. '지난 분기' 에 참이던 사실을 고르는 일은 답 LLM 이 날짜 범위를 읽어 한다 |
| GraphRAG update | 새 보고서는 delta community 에 들어가고, '3.2.1 타이머 버그 미해결' 이라 적힌 옛 report 는 그대로 남는다 |

## 사용자 실험과의 연결

회차 23 은 네트워크 검증 문서 680건(claim 28,473개), 정답 250문항, 용어집 항목 2,004 로 검색 판 31개를 견줬다(`autoschemakg-kg-construction/lab/reports/net-arch-final.md:22-27, 56`, 아래 줄 번호는 이 파일 기준). 이 절은 그 판들을 위 지도에 놓고, 사내 보고서·Qwen 32B 용도에서 다음에 시험할 구조를 고른다.

이 절의 사용자 쪽 용어는 다음과 같다.

| 용어 | 뜻 |
|---|---|
| 8단계 | 공개 이름(Open5GS, KT 같은)이 그대로인 말뭉치에서 잰 판들. 정답 250문항 가운데 근거 있는 221문항으로 채점한다(`runs/23-arch-a4-table/REPORT.md`) |
| 9단계 | 680건 가운데 584건에서 공개 이름 11,514곳을 문서마다 다른 사내 별칭으로 바꾼 말뭉치에서 다시 잰 판들. 모델이 모르는 이름을 이을 수 있는지 본다. 검색 판은 사내 별칭 질문 가운데 근거 있는 151문항으로 견준다(:98-115) |
| 5000자 재현율 | 판이 낸 단위를 순서대로 원문 5000자까지 채우고, 근거 구간을 50% 이상 덮으면 그 근거 묶음을 찾은 것으로 본다. 문항마다 묶음 재현율을 내 평균한다(:24). 채점 대상은 8단계 221문항, 9단계 151문항이다 |
| 승패 | 같은 문항에서 재현율이 높으면 이긴 것이다. p 는 부호 검정 값이다(:25) |
| 사후 | 앞 판의 결과를 본 뒤 더한 판. 미리 약속한 판보다 낙관적으로 읽힐 수 있다 |
| claim-ctx | 문서에서 뽑은 주장(claim) 하나를 단위로 두고, 찾을 때만 문서 제목·절 종류를 이름표로 붙이는 dense 검색. 질의 때 LLM 이 없다. 두 단계 모두의 기준 판이다 |
| 레코드 표 | 질의를 Haiku 1회로 칸(슬롯)에 나누고 템플릿 넷(filter·list·group·count) 가운데 하나로 레코드 1,978개를 거른다. 결과 행의 칸 발췌를 돌려주고, 모자란 자리는 dense 로 채운다(`runs/23-arch-a4-table/REPORT.md`) |
| 값 개념 필터 | 질문의 연도·3GPP Release·소프트웨어 버전을 Haiku 1회로 개념으로 읽어 claim 을 거르는 판. 3GPP 는 이동통신 표준 기구이고 Release 는 그 표준의 판 번호다 |
| 구심점 카드 | 9단계의 사내 용어 카드 49장. 문서마다 다른 사내 별칭과 확정 사실을 박아 둔다 |
| 관계 목록 | 9단계에서 용어끼리 이을 수 있게 정한 관계 30개의 닫힌 목록 |

### 8단계 판을 지도 위에

공개 이름 말뭉치, 근거 있는 221문항, 기준 claim-ctx 0.530 이다(:33-49). 승패는 claim-ctx 대비다.

| 판 | 5000자 재현율 (승패) | 단계 | 해당 기제 | 바깥 근거 |
|---|---|---|---|---|
| 고정 청크 dense → claim-ctx, 이름표 없는 claim | 0.400 → 0.530 (claim-ctx 가 85승 29패), 이름표 없는 claim 0.380 | 2 출발점: 단위 | 질문 → fact 매칭 | HippoRAG 2 에서 단위만 바꿔도 R@5 가 59.6 → 87.1 이다(#1). 회차 23 에서 짧은 단위는 이름표와 함께일 때만 일했다 |
| 값 개념 필터 | 0.555 (11승 2패, p=0.02) | 1 질문 해석 → 2 제약 | 매우 선택적인 값 필터 + 선필터 | Graphiti SearchFilters, ORT 조건 label(#6). 통과 집합이 작으면 그 안을 전수로 훑는 선필터가 recall 1 이고, Qdrant·Weaviate·ACORN 도 이 경로로 넘긴다(#8) |
| 레코드 표 | 0.557 (69승 58패, p=0.37). 이득의 대부분(+0.120)이 dense 채움 | 1 슬롯 → 칸 필터 + 안전망 | 색인 때 레코드 표 + dense 안전망 | S-RAG 가 같은 꼴이다(#9). HippoRAG 2 passage seed 를 빼면 87.1 → 81.0(#1). LinkedIn·DecAF 의 실행 실패 폴백(#3, #7) |
| 용어집으로 후보 거르기 | 0.391 (20승 59패) | 2 출발점: 문지기 | 안전망 없는 엔티티 진입 | HippoRAG 1 오류의 48% 가 NER, HippoRAG 2 필터 뒤 26%(#1) |
| entry 이름을 질문에 붙이기 | 0.457 (8승 42패) | 1 질문 해석 | 키워드 여럿을 한 벡터로 | LightRAG 가 키워드를 이어 붙여 한 번 임베딩하는 꼴과 같다(#1) |
| 용어집 이름표, 검토 없는 용어집 | 0.538 (24승 22패), 0.519 (16승 23패) | 2 출발점 보조 | 동의어 엣지·별칭을 점수 보조로 | HippoRAG 1 동의어 엣지의 몫이 R@5 2.4점으로 작다(#1) |
| 범주 개념 펼치기 | 0.484 (17승 29패) | 1 → 3 | 시소러스 narrower 펼치기 | SKOS 는 펼치기 깊이를 따로 정해야 한다(#6). 범주를 펼친 61문항 중 29문항이 틀린 개념이었다(:59) |
| 용어집 그래프 PPR → 흐름을 차수²로 나눔(사후) | 0.487 (29승 37패) → 0.547 (22승 20패, p=0.88) | 3 확장 | 전역 PPR + hub 보정 | HippoRAG specificity 1/\|P_i\| 의 몫 72.9 대 70.9(#1). 흐름이 차수 큰 제품 이름으로 쏠렸다(:9) |
| 이슈 구조 트리 | 0.203 (고정 청크 대비 31승 88패) | 3 계층 traversal | RAPTOR tree traversal | RAPTOR 에서도 collapsed 가 traversal 보다 일관되게 나았다(#4) |

답 단계는 지표가 다르다. Opus 가 0/0.5/1 로 채점한 답 정답성은 레코드 표 0.593, 고정 청크 0.457 이고, 근거를 다 가져온 문항은 0.89~0.98 이다(:82-88). 앞 단계 recall 이 답의 상한이라는 바깥 결과(#2 거친 서브그래프의 답 포함률, #6 schema linking recall)와 같은 방향이다.

### 9단계 판을 지도 위에

사내 이름 말뭉치, 근거 있는 alias 151문항, 기준 claim-ctx 0.356 이다(:115-126). 공개 이름을 사내 이름으로 바꾸자 claim-ctx 가 0.489 → 0.356 으로 떨어졌다(:113). 그래서 9단계 숫자는 8단계 숫자와 견주지 않고, 같은 단계의 claim-ctx 와만 견준다.

| 판 | 5000자 재현율 (승패) | 단계 | 해당 기제 | 바깥 근거 |
|---|---|---|---|---|
| 레코드 표, Haiku 슬롯 + 카드(사후), 같은 판에서 카드 없음(사후) | 0.461 (56승 25패), 카드 없음 0.353 (36승 34패) | 1 LLM 슬롯 → 2 별칭 표로 값 풀기 | 생성 후 검색: LLM 이 칸 값을 쓰고 별칭 표가 그 값을 구심점에 붙인다 | ChatKBQA 는 LLM 이 뼈대를 쓴 뒤 슬롯마다 KB 항목을 검색해 바꿔 넣고, entity 검색이 F1 을 약 15 올렸다(#3). 별칭 표 부분은 ReFinED 의 alias·prior 표(#1)와 같지만, 회차 23 은 슬롯을 LLM 이 채운다 |
| 관계 선 그래프, 작은 모델 연결 / 글자 연결 | 0.359 (20승 18패) / 0.347 (21승 20패). 근거의 32.5% 에만 닿고 질문당 선 길 claim 중앙값 322개 | 3 확장 | 관계 제약 없는 fan-out | AWS toolkit 이 공유 엔티티 이웃을 끈 까닭과 같다(#7). RoG 는 관계열을 먼저 정해 엣지를 제약한다(#2) |
| 레코드 표, qwen3:8b 슬롯 + 카드 | 0.309 (34승 40패, Haiku 슬롯 판 대비 9승 50패). 카드 연결은 작은 모델 정밀도 0.310, 글자 매칭 1.000 | 1 질문 해석: 작은 모델 | LLM 슬롯·linking | KG-R1 의 ToG 재실행에서 Qwen2.5-7B 가 72B 보다 크게 낮고(잘라 둔 subgraph 위, #5), Interactive-KBQA 의 Mistral-7B 는 미세조정 없이 CWQ 4.76(#5) |

### 지도가 설명하는 것

크게 진 두 판은 출발점에서 후보를 거르거나 앞자리를 바꿨다. 용어집 거르기는 질문 entry 가 태그된 claim 만 남겨 안전망이 없었고, 놓친 근거 83개 중 72개는 근거 claim 에 질문 entry 가 없어 후보 밖이었다(:68, :73). 범주 펼치기는 claim-ctx 채움을 뒤에 붙였지만 펼친 갈래가 글자 예산을 먼저 가져갔다(:9; `reports/net-arch-progress.md:244`).

[추정] 출발점에서 범위를 줄이는 장치는 안전망이 없거나 안전망이 예산 뒤로 밀리면 진다(사례: 용어집 거르기, 범주 개념 펼치기, 2건). 바깥 문헌도 이 단계의 실패가 뒤로 번진다고 보고하고, 그래서 낮은 가중의 dense seed 나 실행 실패 폴백을 둔다(HippoRAG 2, LinkedIn, DecAF).

entry 이름 질문 넓히기는 후보를 지우지 않았다. net-arch-final 은 붙인 이름이 질문 벡터를 묽게 만든 탓으로 추정한다(:74). LightRAG 가 키워드를 이어 붙여 한 벡터로 만드는 꼴(#1)과 같은 실패다.

이긴 판 가운데 질의 때 LLM 이 없는 것은 claim-ctx 하나다. 값 개념 필터, 레코드 표, 9단계 Haiku 슬롯 + 카드는 Haiku 를 1번 부른다(:37-42, :120). 9단계 판은 슬롯 모델을 qwen3:8b 로 바꾸자 0.461 → 0.309 로 무너졌다(:126). 그래서 LLM 이 한 번만 들어가도 #5 의 모델 크기 민감도가 그대로 온다.

글자 매칭은 카드 연결 정밀도에서만 이겼다(1.000 대 작은 모델 0.310, :134). 다만 alias 질문을 이름 바꾸기 코드로 만들어 글자 매칭에 유리하다(:134). 글자 연결로 검색한 관계 선 그래프 판은 0.347 로 claim-ctx 와 비겼다(:125). 글자 매칭을 검색 진입에 쓴 판은 아직 없다(S1).

질의 실행 단계는 절반만 지났다. 레코드 표는 칸 필터로 레코드를 거르고, 시간 유형에서 claim-ctx 를 15승 6패로 이겼다(:10). 하지만 결과를 행 발췌로 돌려 재현율로 채점했고, count·group 템플릿이 센 값을 답으로 넘기지 않았다. 집계 유형에서 필터의 몫은 0 이었다(`runs/23-arch-a4-table/REPORT.md`). 그래서 엔진이 집계 값을 계산해 답으로 넘기는 길(#3, #9)은 아직 재지 않았다.

지나지 않은 단계가 셋 더 있다. 개요 질문을 위한 계층 요약이나 예산형 탐색(#4), LLM 이 걷는 탐색(#5), 질문 유형 라우터(#10)다(:180). 정답 250문항에는 집계 30, 개요 30 문항이 있다.

용어집 관리의 두 고리(저장 전 충돌 검사, 검색 실패에서 대기열로, :168)는 #11 의 갱신 문제와 닿는다. Graphiti 의 쓰기 시점 invalidation 이 저장 전 충돌 검사와 가장 가깝다. 다만 대조 후보를 hybrid search 상위 10개로 자른다(#11).

[추정] 사내 별칭이 문서마다 다른 말뭉치에서는 표기가 달라 대조 후보에서 빠지는 모순이 많아진다(사례: 9단계 카드 없는 슬롯 값 101개 중 99개가 그 별칭을 쓴 문서의 레코드만 잡은 것, :128, 1건).

규모는 아직 재지 않았다. 회차 23 은 문서 680건, claim 28,473개(:56)에서 돌았고 질의 지연은 기록하지 않았다.

[추정] 사내 보고서가 claim 수십만 개로 늘면 #모든 데이터를 안 보는 원리 의 '색인이 있는데 경로가 안 타는' 여덟 경로가 먼저 병목이 된다(사례: HippoRAG 2 fact 전수 dot, NanoVectorDB, Graphiti Neo4j cosine, RAPTOR collapsed, DRIFT primer, GraphRAG local text unit 순위, neo4j-graphrag 필터 시 exact 질의, OG-RAG hypernode 정렬, 8건).

필터를 함께 거는 판이면 선필터 전수 비용이 통과 집합 크기에 선형으로 붙는다(#8).

## 다음에 시험할 구조

net-arch-final 은 Qwen 32B 로 레코드 표 슬롯을 먼저 채워 보라고 권했다(:185). 그 근거는 9단계에서 사내 이름의 빈틈을 메운 길이 '레코드 표 + 카드' 하나이고, 그 길이 슬롯 모델에 달려 있다는 것이다. 아래 다섯은 그 확인과 함께 또는 그 뒤에 견줄 구조다. 모두 구조가 다른 판끼리 같은 199·250문항으로 견주고, 질문마다 어느 경로가 정답을 가져왔는지 남긴다.

### S1. 별칭 표 진입 + dense 안전망

질문에서 글자 매칭으로 카드 별칭을 찾아 그 구심점의 claim·레코드를 seed 로 삼는다. 동시에 claim-ctx dense 결과를 항상 낮은 가중으로 섞고, 매칭이 0 이면 claim-ctx 를 그대로 쓴다. 진입에 LLM 이 없다.

- 근거: 9단계에서 글자 매칭의 카드 연결은 정밀도 1.000·재현율 0.987, qwen3:8b 고르기는 0.310·0.426 이었다(:134). ReFinED 는 LLM 없이 mention 마다 prior 로 후보를 top-30 에 묶고, Wikidata(9천만 개 이상)에서는 label·alias 로 후보를 만든다(#1).
- 근거: HippoRAG 2 는 모든 passage 를 가중 0.05 seed 로 넣고, 이를 빼면 R@5 가 6.1점 떨어진다(#1). 회차 23 의 용어집 거르기 판은 이 안전망 없이 문지기로만 써서 20승 59패였다.
- 재는 것: alias·fact·pub 묶음별 5000자 재현율, 매칭 0 문항 비율, 사람이 오타·약칭을 섞어 쓴 질문 묶음의 연결 재현율.
- 접을 조건: alias 질문은 이름 바꾸기 코드로 만들어 글자 매칭에 유리하다. 사람이 쓴 질문에서 매칭 재현율이 낮으면 SKOS hiddenLabel 식 오타 변형을 카드에 더하는 판으로 바꾼다.

### S2. 슬롯을 쓰지 말고 고르게 하고, 실행 결과로 고친다

레코드 표의 칸마다 실제 값 후보를 글자·임베딩으로 top-k 열거하고, 작은 모델은 후보 가운데 고르기만 한다. 결과가 0행이면 필터를 하나씩 풀어 다시 실행하고, 그래도 0행이면 claim-ctx 로 물러난다.

- 근거: Pangu 는 LM 이 유효한 후보에 순위만 매기게 해서 BERT-base 로 GrailQA F1 79.9 를 냈다(#3). KBQA-o1 은 실행 가능 action 목록(KB environment)을 빼면 78.5 → 43.0 이다(#5).
- 근거: RnG-KBQA 는 결과가 빈 것이 아닌 첫 질의를 골라 빈 질의 비율을 줄였고, cognee 는 실패한 질의를 다음 생성에 넘긴다(#3). 9단계 qwen3:8b 의 실패는 0행 66%, 틀린 칸, 필터 과다였다(:135).
- 재는 것: qwen3:8b 와 Qwen 32B 에서 0행 비율, 5000자 재현율, 질문당 실행 횟수. 카드 있음·없음 두 판.
- 접을 조건: 고르기에서도 qwen 정밀도가 낮으면 슬롯을 규칙(값 개념 필터, 글자 매칭 카드)만으로 채우는 판으로 줄인다.

### S3. 질문이 묻는 관계만 따라가는 확장

관계 목록 30개를 prompt 에 다 넣고 작은 모델이 관계열 1~2개를 고르게 한다. 그 관계의 선만 BFS 로 따라가고, 선 끝 claim 은 차수로 나눠 점수를 매긴 뒤 claim-ctx 가 비운 자리에만 넣는다.

- 근거: 9단계 관계 선 그래프는 질문당 claim 322개로 claim-ctx 의 근거를 밀어내 2500자에서 14승 31패였다(:129). RoG 는 관계열을 먼저 정해 그 관계 엣지만 BFS 한다(#2). RoG 의 성능 수치는 topic entity 중심 서브그래프 위에서 쟀고 그 서브그래프를 gold answer 로 만들었는지 확인하지 못해서, 큰 그래프에서 범위를 줄이는 효과의 근거로는 쓰지 않는다. 운영 쪽 근거는 AWS toolkit 이 fan-out 큰 공유 엔티티 이웃을 기본으로 끈 것이다(#7).
- 근거: 스키마가 context 에 들어가면 linking 없이 넣는 편이 낫다는 결과가 있다(Death of Schema Linking, #6). [추정] 관계 30개는 StructGPT 가 실패 원인으로 든 '수천 개 relation' 보다 훨씬 작아 고르기 오류가 줄어든다(사례: StructGPT selection error 74% 를 저자가 relation 수 탓으로 본 것, 1건).
- 주의: Interactive-KBQA 의 predicate search 오류는 relation 수가 아니라 질문과 스키마의 어휘가 달라서 났다(#5). 그래서 목록이 작아도 관계 이름이 질문 낱말과 다르면 그 오류는 남는다.
- 근거: 회차 23 에서 흐름을 차수²로 나눈 사후 판은 자기 PPR 기준 0.487 보다 0.547 로 올랐지만, claim-ctx 와는 22승 20패(p=0.88)로 갈리지 않았다(:40). HippoRAG specificity 도 hub 를 누르는 같은 방향이다(#1).
- 재는 것: 다중 홉 유형 재현율(레코드 표가 9승 17패로 진 곳), 고른 관계열의 정확도, 경로 기록.
- 접을 조건: 작은 모델의 관계열 고르기가 맞지 않으면 질문 임베딩으로 관계를 순위 매기는 판(Interactive-KBQA 식)으로 바꾼다.

### S4. 질문 유형 라우터와 개요 질문용 예산형 탐색

질문 유형을 먼저 나눠 길을 고른다. 개요·시간은 레코드 표, 다중 홉은 S3, 단일 사실은 claim-ctx 로 보낸다. 개요 질문은 LazyGraphRAG 식으로 claim 묶음 순위를 매긴 뒤 상위 묶음만 LLM relevance test 를 budget 까지 돈다.

- 근거: 질문마다 경로 하나를 고르는 Selection 은 최고 baseline 대비 1.1%, 두 경로를 다 돌려 합치는 Integration 은 6.4% 올렸다(#10). GraphRAG-Bench Novel 에서 단순 사실은 rerank 붙인 RAG 60.92 가 HippoRAG2 60.14 와 비슷했고, 복잡 추론은 HippoRAG2 53.38 이 RAG 42.93 보다 앞섰다(#7).
- 근거: 라우터 오분류율을 잰 원문은 Adaptive-RAG 하나다. 분류기 정확도가 54.52% 이고, oracle 분류기를 끼우면 F1 이 46.94 → 56.28 이다(#10). GPT-4o 에 프롬프트로 고르게 한 라우터는 최고 단일 모델보다 낮았다(RAGRouter 55.13% 대 60.85%, #10).
- 근거: 회차 23 레코드 표는 개요 16승 5패, 시간 15승 6패, 다중 홉 9승 17패였다(:10). LazyGraphRAG 는 budget 500 으로 GraphRAG C2 global 질의 비용의 4% 를 썼다(#4).
- 주의: net-arch-final 은 라우터를 Qwen 32B 슬롯 확인 뒤로 미뤘다(:190). 유형별 강약을 공개 이름 말뭉치에서 쟀기 때문이다. 이 근거가 사내 이름 말뭉치에서 다시 서는지 먼저 본다.
- 재는 것: 유형 라벨을 단 사내 질문에서 Qwen 32B 라우터의 confusion matrix, 유형별 재현율, 개요 질문의 LLM 호출 수. 레코드 표와 claim-ctx 를 늘 함께 돌려 합치는 Integration 판과 견준다.
- 접을 조건: 라우터 판이 Integration 판보다 낮으면 라우터 대신 병합을 기본으로 둔다.

### S5. 집계 질문은 엔진이 센 값을 넘긴다

집계 질문이면 레코드 표의 count·group 결과를 행 발췌 대신 센 값과 근거 행 목록으로 답에 넘긴다. 칸 값은 색인 때 구심점 카드로 정규화한다.

- 근거: S-RAG 는 색인 때 레코드 표를 만들고 SQL 로 답해, Hotels Answer Comparison 을 VectorRAG 0.331 에서 정답 schema 0.899 로 올렸다(#9). AGGBench 에서는 k 를 5 → 50 으로 늘려도 recall 이 0.042 → 0.072 였다(#9).
- 근거: 회차 23 집계 유형은 정답 구간을 그대로 넣어도 1000자 재현율이 0.774 였다(:24). 레코드 표의 집계 유형 5000자 재현율은 0.304 이고 필터 몫은 0 이었다(`runs/23-arch-a4-table/REPORT.md`).
- 재는 것: 집계 30문항의 답 정답성(센 값이 맞는지), 칸 값 정규화 전후 차이.
- 접을 조건: S-RAG 는 schema 를 추론하게 하면 FB-Agg 에서 0.234 로 VectorRAG 0.598 보다 낮았다(#9). 회차 23 의 집계 근거는 이름 대신 "16 vendors" 같은 요약 문장일 때가 있다(:9). 그래서 먼저 집계 30문항을 count형·목록형·요약문 근거형으로 나눠 레코드 표가 셀 몫이 있는지 본다.

## 확인하지 못한 것

### 갈래별 열린 물음

| 갈래 | 항목 | 볼 곳 |
|---|---|---|
| 1 | 프로덕션 Zep 이 ANN 을 쓰는지. Zep §3.1 은 cosine·BM25 모두 Neo4j Lucene 구현이라 적지만 OSS Graphiti 는 엣지 전수 cosine 이다 | Zep 운영 문서, 엣지 수십만~수백만 latency 측정 |
| 1 | AutoSchemaKG LargeKGRetriever 의 seed recall, LLM 필터가 지우는 비율, 질의당 latency | AutoSchemaKG 논문(arXiv 2505.23628) 본문. 이번에는 코드만 읽었다 |
| 1 | HippoRAG 2 Table 8 의 LightRAG QA 점수(Llama-3.3-70B 평균 EM 4.2)가 낮은 까닭 | 원문에 설명 없음 |
| 1 | HippoRAG 2 식 전수 fact 내적 + 전체 PPR 의 fact 수백만 규모 latency. 대조 에이전트는 Appendix F Table 12(p.19)에 MuSiQue 11,656 passage 기준 QA 질의당 1.2 s 가 있다고 짚었다. 수백만 규모 측정은 없다 | 별도 벤치마크 |
| 1 | GraphRAG local 의 엔티티 description 진입 정확도(정답 엔티티 recall) | 원문 없음 |
| 1, 2 | node specificity 가 정답이 hub 엔티티 자체인 질문에서 손해를 내는지, LightRAG 차수 우선 정렬이 무관한 hub 엣지로 예산을 채우는지 | 직접 실험 |
| 1 | 정규화되지 않은 KG(작성자마다 용어가 다른 보고서)에 BLINK·ReFinED 식 EL 을 붙였을 때 후보 recall. alias 표를 무엇으로 만들지 | 사내 데이터로 측정 |
| 2 | PageRank-Nibble 비용이 국소 영역 크기에 묶이는지 | Andersen, Chung, Lang FOCS 2006 |
| 2 | 질의마다 전역 PPR 을 도는 방식의 노드 10^6~10^7 규모 지연 | HippoRAG 2 본문, 별도 벤치마크 |
| 2 | SubgraphRAG Table 1 Time(s) 가 전체 시간인지 질의당인지 | 원문 표현은 "wall clock time … in seconds" 뿐 |
| 2 | RoG Figure 4(K 별 검색 시간)의 값, RoG `build_graph` 가 무방향 단일 엣지로 다중 관계를 덮어쓰는 영향(`graph_utils.py:5-10`) | 그림 원자료, 코드 실행 |
| 2 | PathRAG 를 Freebase·Wikidata 규모 KGQA 에서 평가한 결과 | 원문 없음 |
| 2 | ToG-R 무작위 pruning 이 ToG LLM pruning 과 비슷하다는 결과(CWQ 58.9 대 57.1)가 차수 큰 엔티티 집합에서도 서는지 | 원문 분석 없음 |
| 3 | Wikidata property 수, Ozsoy 실행 정확도 절대값(그림 5·6), Text2Cypher 데이터셋(arXiv 2412.10064)의 오류 유형 분포 | SPINACH Appendix, 그림 원자료, CypherBench·SyntheT2C |
| 3 | CypherQueryCorrector 의 출처 대회 솔루션이 방향 오류를 얼마나 고쳤는지 | github.com/sakusaku-rich/cypher-direction-competition |
| 3 | Text2SQL schema linking 연구(RESDSQL, CHESS)가 KG 질의 생성에 옮겨지는지 | 원문 |
| 3 | neo4j-graphrag 의 다른 모듈(ToolsRetriever, 예제)에 실행 오류를 LLM 에 돌려주는 재시도가 있는지 | retrievers 밖 코드 |
| 4 | LanceDB IVF_FLAT 색인이 데이터 적재 뒤 실제 ANN 으로 도는지 | LanceDB 소스 |
| 4 | Neo4j index-free adjacency 의 공식 비용 모델(차수 비례, dense node 처리) | Neo4j 공식 문서. graphacademy 페이지가 404 였다 |
| 4 | dynamic selection 의 평정 report 수와 절대 token, DRIFT 의 실제 LLM 호출·token(블로그는 2회 반복, 코드 기본 n_depth 3) | graphrag 를 돌려 `llm_calls_categories` 로 측정 |
| 4 | LazyGraphRAG 의 절대 token·호출 수와 budget 의 관계 | 공개 코드 없음(Microsoft Discovery·Azure Local) |
| 4 | RAPTOR collapsed 가 노드 수만 개 이상에서도 traversal 보다 나은지, community level 을 질문 유형으로 자동 고르는 방법 | 원문 없음 |
| 5 | Qwen2.5-32B 급의 학습 없는 프롬프트 에이전트 수치. KG-R1 Table 1 은 7B·72B·235B 만 있다 | 직접 측정 |
| 5 | KG-R1 Table 1 의 ToG·PoG 기준선이 전체 Freebase 에서 돌았는지 | KG-R1 Appendix D.2 에 설정 없음 |
| 5 | Interactive-KBQA 가 다시 구현한 ToG 의 WebQSP 36.40 이 ToG 논문 76.2 와 크게 다른 까닭 | 원문 설정 대조 |
| 5 | KG-Agent 도구의 반환 상한과 질문당 step 수, Interactive-KBQA Appendix A.5 의 turn 수, KBQA-o1 처리량 | 공개 코드, Table 18, Figure 4(c) |
| 5 | RoG·StructGPT 의 subgraph 가 질문별이고 gold answer 로 만들었는지 | RoG 데이터 생성 코드 |
| 6 | 시소러스·용어집 질의 확장(SKOS, MeSH)의 recall·precision 효과 | "Using SKOS vocabularies for improving Web Search"(univie eprints 3689), Voorhees SIGIR 1994 |
| 6 | OntoRAG 승률이 초록(85%/75%)과 본문(88%/65%)에서 다른 까닭 | 후속 판, 저자 코드 |
| 6 | OG-RAG 를 hypernode 수십만 개에서 ANN 으로 바꿀 때 recall | 직접 측정 |
| 6 | 네트워크 검증 부서 데이터에 OBDA 가 맞는지(원본이 관계형 DB 인지, R2RML mapping 을 쓸 사람, OWL 2 QL 표현력) | 부서 데이터 확인 |
| 6 | Qwen 32B 가 스키마 전체를 prompt 에 넣고 Cypher 를 정확히 쓰는지, schema linking 유무의 차이 | 직접 비교 실험 |
| 6 | 사람이 정한 스키마가 데이터에서 자동 유도한 스키마보다 검색을 얼마나 낫게 하는지. AutoSchemaKG retriever 도 concept 노드를 검색 유도에 쓰지 않는다(`atlas_rag/retriever/hipporag2.py:203`) | 원문 없음 |
| 6 | Pangu GrailQA 전체 test·미세조정 수치, ORT 의 LLM 호출 수 | Pangu Table 1~2, ORT 원문 |
| 7 | 그래프 크기만 바꾼 통제 실험 | GraphRAG-Bench(Xiao 외, arXiv 2506.02404), KET-RAG, HippoRAG 2 본문 |
| 7 | LinkedIn KG 크기와 golden set 크기, 노드 유사도가 전수 비교인지 색인 조회인지 | 원문에 없음 |
| 7 | Zep 의 그래프 크기별 지연. Graphiti README 의 "Typically sub-second latency" 는 측정 조건이 없어 쓰지 않았다 | 별도 측정 |
| 7 | Bedrock·Neptune Analytics 의 hop 수, 확장 상한, 지연·정확도. AWS toolkit `benchmarks/` 에는 결과 수치가 없다 | 공식 문서 미공개 |
| 7 | GraphRAG-Bench 본문 Obs.8 과 Figure 8–9 의 prompt token 값 중 어느 쪽이 맞는지 | 원문 PDF |
| 7 | Neo4j HNSW 에서 effective_search_ratio 를 올릴 때 recall·지연 | 공식 수치 |
| 8 | 기간(범위) 술어를 그래프 안에서 거를 때의 성능. ACORN 은 TripClick 의 날짜 workload(평균 선택도 0.26, §7.1.2)를 평가했지만 날짜 술어만 떼어 낸 수치는 본문에서 확인하지 못했다 | ACORN Figure 8 의 TripClick 곡선 |
| 8 | 최신 Neo4j vector index 가 술어를 건 ANN 을 지원하는지. 지원한다면 neo4j-graphrag 가 필터를 받을 때 exact 전수로 바뀌는 동작을 바꿀 수 있다 | Neo4j Cypher Manual 의 vector index·SEARCH 절 |
| 8 | Weaviate flat-search cutoff 기본값(문서 그림은 데이터셋의 약 15% 로 둔 예), ACORN 의 추가 entrypoint 개수 | Weaviate vectorIndexConfig 참조 문서 |
| 8 | Graphiti 에 Neo4j 밖 `search_interface` 가 붙으면 ANN 을 쓰는지, group 하나의 edge 수가 몇 건부터 지연 문제가 되는지 | 실험 그래프로 edge 수를 늘리며 질의 지연 측정 |
| 8 | Qdrant filterable HNSW 의 extra edge 를 만드는 방식과 메모리 증가량 | 문서가 'our article' 로만 건 원문 |
| 8 | PathSeer(SIGMOD 2026)의 수치와 실패 조건. Weaviate 문서 설명만 봤다 | 논문 본문 |
| 9 | CypherBench 의 RETURN 템플릿별(AGGREGATE·GROUP 등) 정확도. Figure 5 그림에만 있다 | 그림 원본, megagonlabs/cypherbench 결과 파일 |
| 9 | BIRD text-to-SQL 집계(GROUP BY·COUNT) 오류 분석 | BIRD 논문 오류 분석 절, 후속 오류 분류 논문 |
| 9 | 집계 질문에서 Text2SQL 과 TAG 의 정량 차이. TAG 는 aggregation 을 정성으로만 보였다 | 원문 없음 |
| 9 | StructRAG 표의 GraphRAG 가 local 모드인지 global 모드인지 | 원문에 'official code repositories' 만 있다 |
| 9 | S-RAG·DFA 식 schema·레코드 표준화가 작성자마다 용어가 다른 사내 보고서에서 얼마나 무너지는지. 두 논문 모두 영어 공개 말뭉치에서만 쟀다 | 사내 문서 20~30개로 S-RAG 식 schema 예측 |
| 9 | EnterpriseRAG-Bench(arXiv 2605.05253)의 completeness 질문, Weller 외 2025 의 dense embedding 표현 한계 | 원문. 검색 결과로만 봤다 |
| 10 | KG 특화 질문 유형(local entity, global 요약, multi-hop 관계)을 고르는 라우터의 오분류율. RAG vs GraphRAG 의 Selection 도 분류 정확도를 보고하지 않는다 | 사내 질문 수십 개에 라벨을 달고 Qwen 32B 프롬프트 라우터의 confusion matrix |
| 10 | 데이터셋 출처라는 구분이 없는 사내 질문에서 라우터 학습 라벨을 만드는 법. 경로별 정답 여부로 silver label 을 만드는 것이 후보다 | 원문에 답 없음 |
| 10 | Self-Route 의 'unanswerable' 자기 판단이 32B 급 로컬 모델에서도 맞는지. 원문 실험은 Gemini-1.5-Pro, GPT-4O, GPT-3.5-Turbo 뿐이다 | 직접 측정 |
| 10 | LlamaIndex RouterQueryEngine 과 cognee FEELING_LUCKY 의 선택 정확도. cognee `search_type_selector_prompt.txt:5-17` 에 'Best for' 블록이 유형 제목 없이 두 번 이어지는 자리가 있는데 선택에 영향을 주는지 | 실행 |
| 10 | MBA-RAG, Probing-RAG, RouterRetriever, Router-R1 의 라우터 정확도 표 | 원문. 이번에 열지 않았다 |
| 11 | Graphiti invalidation 후보가 상위 10개로 잘릴 때 놓치는 모순의 비율. Zep 논문에 측정이 없다 | 모순 쌍을 심은 작은 데이터로 Graphiti 실행 |
| 11 | `graphiti.py:1948` 의 `search_config.limit = num_results` 가 모듈 전역 recipe `EDGE_HYBRID_SEARCH_RRF` 를 바꿔, 쓰기 시점 invalidation 후보 수까지 바꾸는지. 코드로만 봤다 | 실행 |
| 11 | Graphiti MCP(Model Context Protocol) server 나 Zep 상용 API 가 질문 시점에 만료 edge 를 기본으로 거르는지. 이번에는 graphiti_core 만 읽었다 | 해당 코드·API 문서 |
| 11 | 증분 community 가 전체 재계산과 얼마나 빨리 어긋나는지(drift 크기, refresh 주기) | 원문 없음 |
| 11 | GraphRAG `graphrag update` 공식 설명, period 열을 질문 시점 검색이 쓰는지, 옛 엔티티가 delta community 에도 속할 때 local search 가 두 report 를 어떻게 쓰는지 | microsoft.github.io/graphrag, query 코드 |
| 11 | LightRAG 가 모순되는 설명을 요약할 때 새 정보를 우선하는 규칙이 있는지 | `prompt.py` |
| 11 | alias 표, 동의어 edge KNN 처럼 KG 쪽에 미리 만든 edge 가 삽입 뒤 얼마나 낡는지. FreshDiskANN 의 recall 은 벡터 색인 층 결과다 | 원문 없음 |
| 11 | 보고서에서 LLM 이 뽑은 `valid_at` 의 정확도가 시간 질문 성능을 얼마나 제한하는지. TimeQuestions·CronQuestions 는 시각이 이미 붙은 KG 를 전제한다 | 원문 없음 |
| 연결 | 회차 23 의 값 개념 필터와 시간 질문 40문항의 실제 선택도. 값 필터는 매우 선택적이라 선필터 전수가 맞고 기간 필터는 중간 구간일 것으로 보이지만 세지 않았다 | 레코드 표에서 조건별 통과 행 수 세기 |
| 연결 | 회차 23 집계 30문항이 count형('몇 개'), 목록형('모든 X'), 요약문 근거형('16 vendors') 가운데 어디에 드는지 | 정답 파일을 직접 나누기 |

### 대조 단계가 짚었지만 주장으로 대조하지 않은 값

대조 에이전트가 원문을 다시 열다가 짚은 값이다. 주장 목록으로 대조를 거치지 않아 본문 근거로 쓰지 않았다.

| 값 | 짚은 곳 |
|---|---|
| CRAG 에서 KG API 를 쓰는 Task 2 의 truthfulness 16.2, LLM 단독 20.0(GPT-4 Turbo 행) | CRAG Table 5. 본문은 "Task 2 truthfulness scores are higher than Task 1" 이라고만 비교한다 |
| CypherBench 에 30B 급 행은 없다. 가장 가까운 오픈 모델은 qwen2.5-72b 41.87%, llama3.1-70b 38.84% | CypherBench Table 3. Qwen 32B 의 Text2Cypher 정확도를 짐작할 때 쓸 수 있다 |
| GNN-RAG 서브그래프 평균 엔티티 수 WebQSP 1,429.8, CWQ 1,305.8, 답 포함률 94.9%, 79.3% | GNN-RAG Table 7. RoG 2-hop 서브그래프 통계(1,370.89노드)와 다른 서브그래프다 |
| dynamic selection level 3 의 comprehensiveness 58.8% 는 50개 중 29개 질의만 평가한 값 | Microsoft Research 블로그 |
| ReFinED Table 5 의 89.4·87.2 는 AIDA F1 이 아니라 여러 데이터셋 평균 ED(entity disambiguation) F1 | ReFinED Table 5 |

## 원문 위치

### 논문·문서

| 이름 | URL |
|---|---|
| HippoRAG | https://arxiv.org/abs/2405.14831 |
| HippoRAG 2 (From RAG to Memory) | https://arxiv.org/abs/2502.14802 |
| LightRAG | https://arxiv.org/abs/2410.05779 |
| BLINK | https://arxiv.org/abs/1911.03814 |
| ReFinED | https://arxiv.org/abs/2207.04108 |
| Zep | https://arxiv.org/abs/2501.13956 |
| Think-on-Graph | https://arxiv.org/abs/2307.07697 |
| Think-on-Graph 2.0 | https://arxiv.org/abs/2407.10805 |
| G-Retriever | https://arxiv.org/abs/2402.07630 |
| RoG (Reasoning on Graphs) | https://arxiv.org/abs/2310.01061 |
| SubgraphRAG (Simple is Effective) | https://arxiv.org/abs/2410.20724 |
| GNN-RAG | https://arxiv.org/abs/2405.20139 |
| PathRAG | https://arxiv.org/abs/2502.14902 |
| KG-GPT | https://arxiv.org/abs/2310.11220 |
| Ozsoy, Text2Cypher Schema Filtering | https://arxiv.org/abs/2505.05118 |
| TIARA | https://arxiv.org/abs/2210.12925 |
| RnG-KBQA | https://arxiv.org/abs/2109.08678 |
| Pangu (Don't Generate, Discriminate) | https://arxiv.org/abs/2212.09736 |
| ChatKBQA | https://arxiv.org/abs/2310.08975 |
| KB-BINDER | https://arxiv.org/abs/2305.01750 |
| DecAF | https://arxiv.org/abs/2210.00063 |
| Interactive-KBQA | https://arxiv.org/abs/2402.15131 |
| SPINACH | https://arxiv.org/abs/2407.11417 |
| HNSW | https://arxiv.org/abs/1603.09320 |
| Neo4j vector index | https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/ |
| Neo4j full-text index | https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/full-text-indexes/ |
| Besta 외, Demystifying Graph Databases | https://arxiv.org/html/1910.09017 |
| GraphRAG (From Local to Global) | https://arxiv.org/html/2404.16130v2 |
| dynamic community selection 블로그 | https://www.microsoft.com/en-us/research/blog/graphrag-improving-global-search-via-dynamic-community-selection/ |
| DRIFT 블로그 | https://www.microsoft.com/en-us/research/blog/introducing-drift-search-combining-global-and-local-search-methods-to-improve-quality-and-efficiency/ |
| LazyGraphRAG 블로그 | https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/ |
| RAPTOR | https://arxiv.org/html/2401.18059 |
| StructGPT | https://arxiv.org/abs/2305.09645 |
| KG-Agent | https://arxiv.org/abs/2402.11163 |
| Graph-CoT | https://arxiv.org/abs/2404.07103 |
| KBQA-o1 | https://arxiv.org/abs/2501.18922 |
| PoG (Plan-on-Graph) | https://arxiv.org/abs/2410.23875 |
| KG-R1 | https://arxiv.org/abs/2509.26383 |
| OWL 2 Profiles | https://www.w3.org/TR/owl2-profiles/ |
| Ontop (SWJ 2017) | https://www.inf.unibz.it/~calvanese/papers/calv-etal-SWJ-2017.pdf |
| OG-RAG | https://arxiv.org/html/2412.15235v1 |
| CRUSH4SQL | https://arxiv.org/html/2311.01173 |
| The Death of Schema Linking? | https://arxiv.org/html/2408.07702v2 |
| ORT | https://arxiv.org/html/2502.11491v3 |
| DBCopilot | https://arxiv.org/html/2312.03463 |
| SKOS Reference | https://www.w3.org/TR/skos-reference/ |
| PubMed User Guide | https://pubmed.ncbi.nlm.nih.gov/help/ |
| LeanRAG | https://arxiv.org/html/2508.10391v2 |
| OntoRAG | https://arxiv.org/html/2506.00664v1 |
| LinkedIn 고객지원 KG RAG | https://arxiv.org/abs/2404.17723 |
| CypherBench | https://arxiv.org/html/2412.18702 |
| Amazon Bedrock GraphRAG | https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-build-graphs.html |
| STaRK | https://arxiv.org/html/2404.13207 |
| CRAG | https://arxiv.org/html/2406.04744 |
| When to use Graphs in RAG (GraphRAG-Bench) | https://arxiv.org/html/2506.05690 |
| RAG vs. GraphRAG | https://arxiv.org/html/2502.11371 |
| Zhou 외, Graph-based RAG in a Unified Framework | https://arxiv.org/html/2503.04338 |
| ACORN | https://arxiv.org/html/2403.04871v1 |
| Filtered-DiskANN | https://harsha-simhadri.org/pubs/Filtered-DiskANN23.pdf |
| Big-ANN NeurIPS'23 결과 | https://arxiv.org/pdf/2409.17424 |
| pgvector README | https://github.com/pgvector/pgvector/blob/master/README.md |
| Qdrant Indexing, Search | https://qdrant.tech/documentation/concepts/indexing/, https://qdrant.tech/documentation/search/search/ |
| Weaviate Filtering | https://docs.weaviate.io/weaviate/concepts/filtering |
| Milvus Use Partition Key (v2.5.x) | https://github.com/milvus-io/milvus-docs/blob/v2.5.x/site/en/userGuide/search-query-get/use-partition-key.md |
| LanceDB Filtering | https://lancedb.com/docs/search/filtering/ |
| TAG (Text2SQL is Not Enough) | https://arxiv.org/abs/2408.14717 |
| QUEST | https://aclanthology.org/2023.acl-long.784.pdf |
| StructRAG | https://arxiv.org/abs/2410.08815 |
| S-RAG (Structured RAG for Answering Aggregative Questions) | https://arxiv.org/abs/2511.08505 |
| AGGBench, DFA | https://arxiv.org/abs/2602.01355 |
| Adaptive-RAG | https://arxiv.org/html/2403.14403v2 |
| Self-Route (RAG or Long-Context LLMs?) | https://arxiv.org/html/2407.16833v2 |
| RAGRouter | https://arxiv.org/html/2505.23052v2 |
| HybGRAG | https://arxiv.org/html/2412.16311v1 |
| FreshDiskANN | https://arxiv.org/abs/2105.09613 |
| EXAQT | https://arxiv.org/pdf/2109.08935 |
| CronQuestions, CronKGQA | https://arxiv.org/pdf/2106.01515 |

### 저장소

경로는 `/home/ssafy/workspace/alt/lab-notes/` 기준이다.

| 저장소 | 경로 | commit |
|---|---|---|
| HippoRAG | `autoschemakg-kg-construction/lab/repos/HippoRAG` | d5c8329 |
| LightRAG | `autoschemakg-kg-construction/lab/repos/LightRAG` | 453dce8 |
| microsoft/graphrag | `autoschemakg-kg-construction/lab/repos/graphrag`, `llm-wiki-implementations/lab/repos/microsoft_graphrag` | 5faaaf4 |
| getzep/graphiti | `autoschemakg-kg-construction/lab/repos/graphiti`, `llm-wiki-implementations/lab/repos/getzep_graphiti` | 964bb11 |
| AutoSchemaKG | `autoschemakg-kg-construction/lab/repos/AutoSchemaKG` | d0a1666 |
| cognee | `autoschemakg-kg-construction/lab/repos/cognee` | 0ec7a9f |
| llm-graph-builder | `autoschemakg-kg-construction/lab/repos/llm-graph-builder` | 5ff7af3 |
| fast-graphrag | `llm-wiki-implementations/lab/repos/circlemind-ai_fast-graphrag` | 23b3a1b |
| neo4j-graphrag-python | `llm-wiki-implementations/lab/repos/neo4j_neo4j-graphrag-python` | 523e2b5 |
| ograg2 (OG-RAG) | `llm-wiki-implementations/lab/repos/ograg2` | 768048b |
| trustgraph | `llm-wiki-implementations/lab/repos/trustgraph-ai_trustgraph` | ea19308 |
| RAPTOR | `doc-parsing-chunking/lab/repos/parthsarthi03_raptor` | — |
| ToG | `kg-retrieval-at-scale/lab/repos/ToG`, `kg-retrieval-at-scale/lab/repos/IDEA-FinAI_ToG` | — |
| reasoning-on-graphs (RoG) | `kg-retrieval-at-scale/lab/repos/RManLuo_reasoning-on-graphs` | — |
| G-Retriever | `kg-retrieval-at-scale/lab/repos/XiaoxinHe_G-Retriever` | — |
| SubgraphRAG | `kg-retrieval-at-scale/lab/repos/Graph-COM_SubgraphRAG` | — |
| Interactive-KBQA | `kg-retrieval-at-scale/lab/repos/Interactive-KBQA` | e9e22cc |
| StructGPT | `kg-retrieval-at-scale/lab/repos/StructGPT` | — |
| Graph-CoT | `kg-retrieval-at-scale/lab/repos/Graph-CoT` | — |
| langchain-neo4j | `kg-retrieval-at-scale/lab/repos/langchain-neo4j` | e903fa8 |
| graphrag-toolkit | `kg-retrieval-at-scale/lab/repos/graphrag-toolkit` | 7b32722 |
| nano-vectordb | https://github.com/gusye1234/nano-vectordb (`nano_vectordb/dbs.py`) | main |
| llama_index | https://github.com/run-llama/llama_index (`llama-index-core/llama_index/core/query_engine/router_query_engine.py`, `selectors/`) | 619d746 |

commit 칸이 — 인 저장소는 조사 결과에 commit 이 적히지 않았다.

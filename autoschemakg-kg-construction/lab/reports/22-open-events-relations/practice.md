# 실무 도구는 관계 이름을 자유롭게 뽑게 두고 뒤에서 목록으로 묶지만, 서로 다른 보고서의 같은 사건을 하나로 잇는 일은 아무도 풀지 않았다

조사 갈래: 사건·관계 종류를 미리 정하지 않을 때 실무 구현·발표·글은 어떻게 하는가. 출처 14개(코드 7, 영상 3, 글·문서 4)를 2026-10-11에 읽었다.

읽는 법:
- 저장소 경로는 `autoschemakg-kg-construction/lab/repos/` 기준이다. 커밋은 각 항목에 적었다.
- 웹 글 인용은 WebFetch로 가져온 원문 발췌다. 발췌 단계에서 작은 모델이 끼므로 낱말 하나까지 맞다고 보장하지 않는다.
- Zalando 글과 LinkedIn 논문의 인용은 원문(HTML을 `curl`로 받은 것, arXiv PDF v2를 텍스트로 바꾼 것)과 글자 단위로 대조했다.
- 영상 인용은 whisper large-v3-turbo 전사(`yt-notes` 스크립트)에서 가져왔다. 유튜브 자막 API는 IP 차단으로 실패했다.
- 한국어 실무 글은 두 번 검색했지만 이 주제를 다룬 것을 찾지 못했다. 찾은 한국어 GraphRAG 글(정이태, 2024-11-30, inblog)은 entity type 자동 발견이나 한국어 적용을 다루지 않았다.

## 한눈에

실무가 쓰는 길은 다섯 갈래다. 표는 갈래와 대표 출처만 견준다.

| 갈래 | 하는 일 | 출처 |
|---|---|---|
| 자유 추출 → 뒤에서 묶기 | 관계 이름을 LLM이 마음대로 쓰게 두고, 나중에 비슷한 이름을 기존 이름 하나로 바꾼다 | Neo4j LLM Graph Builder, iText2KG/ATOM |
| 씨앗 목록 + 확장 허용 | 처음 목록을 주되 밖의 이름도 받는다. 맞지 않으면 기본 이름으로 떨군다 | LlamaIndex DynamicLLMPathExtractor, Graphiti, Cognee |
| 표본에서 LLM이 schema 제안 | 문서 일부를 읽혀 종류 목록을 만들고 그 목록으로 추출한다 | GraphRAG prompt-tune, neo4j-graphrag `SchemaFromTextExtractor` |
| 관계에 종류를 안 붙임 | 문서·조각끼리 "관련 있음"만 잇고 이유는 글로 남긴다 | GraphRAG relationship·claim, LinkedIn 티켓 KG, DataStax, Neo4j 발표 |
| 사람이 정하고 승인 | 종류를 사람이 정하거나, 바뀐 것을 사람이 승인·표본 검토한다 | Barrasa·Chalef 발표, Palantir ontology proposal, Zalando |

## 자유 추출 → 뒤에서 묶기

### Neo4j LLM Knowledge Graph Builder

레포 · 2024~ · <https://github.com/neo4j-labs/llm-graph-builder> (커밋 `5ff7af3`, 2026-07-30)

- **무엇**: 문서를 조각내 LangChain `LLMGraphTransformer`로 노드·관계를 뽑아 Neo4j에 쌓는 웹 앱이다.
- **정하지 않을 때**: 허용 노드가 비면 제한 없이 뽑는다(`backend/src/llm.py:257-261`). 뒤처리 `graph_schema_consolidation`이 그래프에 생긴 모든 label·관계 이름 목록을 LLM에 넘겨 무리 짓고, Cypher로 옛 이름을 새 이름으로 바꾼다(`backend/src/post_processing.py:149-186`). 이 뒤처리는 사용자가 schema를 고르지 않았을 때만 돈다(`frontend/src/components/Content.tsx:183-190`). 별도로 표본 글에서 `Person-WORKS_AT->Company` 꼴 schema를 뽑는 API도 있다(`backend/src/shared/schema_extraction.py:20-28`).
- **원문**: "The name of each category must be chosen from the types in the input list"(`backend/src/shared/constants.py:835`). 프런트 설명은 "consolidate many node labels and relationship types into fewer, more relevant ones and apply it to the extracted and existing graph"(`frontend/src/utils/Constants.ts:274`).
- **수치·운영**: 묶기 전후 개수를 로그로만 남긴다(`post_processing.py:166-167`). 묶기 결과를 사람이 승인하는 단계는 없고 바로 그래프를 고친다.
- **우리 쪽에 옮길 때**: 묶기 프롬프트는 "목록에 있는 이름 중에서 고르기"라서 작은 모델이 하기 쉬운 꼴이다. 그러나 기본 묶기 모델은 `openai_gpt_5.4_mini`다(`post_processing.py:157`). 구조화 출력을 못 하는 모델이면 노드·관계 description을 아예 뺀다(`backend/src/llm.py:216-220`). Ollama 모델이 이 경로를 타는지는 확인하지 않았다.
- **확인**: 코드 읽음.

### iText2KG / ATOM

레포 · 2024~2026 · <https://github.com/AuvaLab/itext2kg> (커밋 `840aba2`, 2026-09-04)

- **무엇**: 글을 "atomic fact"로 쪼개 (주어, 관계, 목적어, 시작, 끝) 5-tuple을 뽑고, 작은 그래프들을 둘씩 합쳐 시간 KG를 만든다.
- **정하지 않을 때**: 관계 이름을 미리 정하지 않는다. 합칠 때 관계 이름 embedding의 cosine이 기준을 넘으면 새 관계의 이름을 기존 관계 이름으로 바꾸고, 양 끝 entity는 그대로 둔다(`itext2kg/atom/graph_matching/matcher.py:144-153`). 이름까지 같아진 관계는 관측 시각·시작·끝·근거 fact를 합친다(`matcher.py:156-163`).
- **원문**: "relation resolution merging relation names regardless of endpoints and timestamps using threshold `θ_R = 0.7`"(`README.md:119`). 코드 주석은 "we rename the `rels1[i]` relationship to have the same name as the best-matching relationship from `rels2`"(`matcher.py:115-116`).
- **수치·운영**: 기준은 entity 0.8, 관계 0.7이 `build_graph` 기본값이다(`README.md:196-197`). 함수 자체 기본값은 0.8이다(`matcher.py:109`).
- **우리 쪽에 옮길 때**: LLM 없이 embedding만으로 묶으므로 작은 모델 조건에 맞는다. 짧은 한국어 관계 이름에서 "원인"과 "대응" 같은 다른 뜻끼리 0.7을 넘는지는 모른다. 우리 관계 이름 쌍 몇십 개의 cosine을 재 보면 알 수 있다.
- **확인**: 코드 읽음.

## 씨앗 목록 + 확장 허용

### LlamaIndex PropertyGraphIndex 추출기

레포 · 2024~ · <https://github.com/run-llama/llama_index> (`main` 커밋 `6dd2f3c`, 2026-10-08, 파일 세 개만 받아 읽음)

- **무엇**: 문서 조각에서 (head, relation, tail)을 뽑는 추출기 세 가지를 준다.
- **정하지 않을 때**: `SimpleLLMPathExtractor`는 종류 없이 뽑는다. `DynamicLLMPathExtractor`는 받은 종류 목록을 "initial ontology"로 보고 새 종류를 만들도록 부추긴다(`llama-index-core/.../transformations/dynamic_llm.py:167-185`). 목록이 비면 프롬프트에 "No entity types provided, You are free to define them."를 넣는다(`dynamic_llm.py:318-325`). `SchemaLLMPathExtractor`도 `strict=False`면 schema 밖 값을 받는다(`schema_llm.py:111-113`).
- **원문**: "Use these types as a starting point, but introduce new types if necessary based on the context."(`llama-index-core/llama_index/core/prompts/default_prompts.py:344`)
- **수치·운영**: 없다. 새로 생긴 종류를 나중에 묶는 단계는 이 세 파일에 없다.
- **우리 쪽에 옮길 때**: 씨앗 목록(원인·대응)을 주고 새 이름을 허용하는 꼴은 사용자 안을 그대로 넓힌 모양이다. 대신 새 이름이 쌓이므로 Neo4j·ATOM식 묶기를 따로 붙여야 한다.
- **확인**: 코드 읽음.

### Graphiti (Zep)

레포+문서 · 2024~ · <https://github.com/getzep/graphiti> (커밋 `964bb11`, 2026-10-10), <https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types>

- **무엇**: 대화·문서를 episode 단위로 넣어 시간 속성이 붙은 entity·fact 그래프를 쌓는다.
- **정하지 않을 때**: custom edge type을 주더라도 맞는 것이 없으면 LLM이 술어에서 `SCREAMING_SNAKE_CASE` 관계 이름을 새로 만든다(`graphiti_core/prompts/extract_edges.py:103-107`). `strict_edge_types`일 때만 맞지 않는 관계를 버린다(`extract_edges.py:98-102`). custom type 이름을 썼는데 양 끝 entity 종류가 맞지 않으면 `RELATES_TO`로 이름을 바꾸고 속성을 비운다(`graphiti_core/utils/maintenance/edge_operations.py:671-712`).
- **episode는 사건이 아니다**: `EpisodicNode`는 넣은 원문 한 덩어리다. `valid_at`은 "datetime of when the original document was created"다(`graphiti_core/nodes.py:318-330`). 세상의 사건은 fact edge의 `valid_at`·`invalid_at`으로 표현된다(`extract_edges.py:43-47`).
- **원문**: 문서는 "If an entity pair does not have an edge type mapping, Graphiti keeps the extracted predicate as the edge name."라고 쓴다. 이미 넣은 데이터에 종류를 붙이려면 "you need to re-ingest it with entity types set into a new graph"라고 쓴다.
- **수치·운영**: 문서의 권고는 "Don't make edge types too specific or too general."다. 숫자 상한은 없다.
- **우리 쪽에 옮길 때**: 종류를 나중에 정하면 옛 데이터를 새 그래프로 다시 넣어야 한다는 점이 "나중에 묶기"의 비용이다. 원문과 자유 관계 이름을 남겨 두면 다시 추출하지 않고 이름만 바꿀 수 있다. 자유 이름끼리 묶는 단계는 `edge_operations.py`에서 찾지 못했다.
- **확인**: 코드 읽음, 문서 원문 읽음.

### Cognee

레포 · 2023~ · <https://github.com/topoteretes/cognee> (커밋 `0ec7a9f`, 2026-10-08)

- **무엇**: 문서에서 노드·관계를 뽑고, 선택적으로 RDF ontology에 맞춰 이름을 정규화한다.
- **정하지 않을 때**: 관계 이름은 자유 문자열이다(`cognee/shared/data_models.py:62-71`). ontology가 있어도 strict 모드는 entity만 걸러내고 관계 이름은 검사하지 않는다(`cognee/modules/ontology/construct_data_points_and_edges_with_ontology.py:139-143`). ontology 이름 맞추기는 `difflib` 문자열 유사도 0.8을 쓴다(`cognee/modules/ontology/matching_strategies.py:24-51`).
- **원문**: "relationship names are not checked against the ontology."(`construct_data_points_and_edges_with_ontology.py:143`)
- **수치·운영**: 없다.
- **우리 쪽에 옮길 때**: 문자열 유사도는 한국어 동의어(예: 다른 작성자의 다른 부서명)를 잡지 못한다. 용어집 매칭에는 쓸 수 있지만 관계 종류 문제에는 답이 아니다.
- **확인**: 코드 읽음.

## 표본에서 LLM이 schema 제안

### Microsoft GraphRAG prompt-tune

레포+글 · 2024~ · <https://github.com/microsoft/graphrag> (커밋 `5faaaf4`, 2026-10-08), <https://www.microsoft.com/en-us/research/blog/graphrag-auto-tuning-provides-rapid-adaptation-to-new-domains/> (2024-09-09)

- **무엇**: 문서 표본을 LLM에 읽혀 도메인·persona·entity type·예시를 만들고, 그것으로 추출 프롬프트를 새로 쓴다.
- **정하지 않을 때**: 기본 entity type은 `["organization", "person", "geo", "event"]`다(`packages/graphrag/graphrag/config/defaults.py:42`). `discover_entity_types`가 켜지면 표본에서 종류를 생성한다(`packages/graphrag/graphrag/api/prompt_tune.py:127-135`). 관계 종류는 만들지 않는다. GraphRAG 관계는 원래 종류가 없기 때문이다(다음 절).
- **원문**: 프롬프트는 "Do not generate redundant or overlapping entity types."라고 쓴다(`packages/graphrag/graphrag/prompt_tune/prompt/entity_types.py:12`). 블로그는 표본 크기를 "a sample of text data (e.g., 1% of 10,000 chemistry papers)"로 적는다.
- **수치·운영**: 블로그는 팟캐스트 표본 예시에서 기본 3종이 6종으로 늘었다고 적는다. 품질 수치는 없다.
- **우리 쪽에 옮길 때**: 표본 1%에서 한 번 정하면 나중에 들어오는 새 사건 종류는 놓친다. 주기적으로 다시 돌리는 방법은 문서에 없다.
- **확인**: 코드 읽음, 블로그 원문 읽음.

### neo4j-graphrag Python의 schema 모드

문서 · 2025~ · <https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html>

- **무엇**: Neo4j의 파이프라인 라이브러리가 schema를 직접 받거나, 글에서 뽑거나, 아예 안 쓰는 세 모드를 둔다.
- **정하지 않을 때**: schema를 안 주면 기본 `EXTRACTED` 모드가 입력 글에서 schema를 한 번 뽑는다. `FREE` 모드는 schema 없이 추출한다. `additional_node_types`·`additional_relationship_types`·`additional_patterns`를 `False`로 두면 schema 밖의 것을 지운다.
- **원문**: "The schema is automatically extracted from the input text once using LLM." `FREE`는 "No schema extraction is performed."(User Guide의 schema 절)
- **수치·운영**: 없다.
- **우리 쪽에 옮길 때**: "schema 밖 허용 여부"를 노드·관계·패턴마다 따로 켜는 설계는 "관계는 열고 사건 종류는 닫는다" 같은 섞인 정책을 바로 표현한다.
- **확인**: 원문 읽음(코드는 안 읽음).

## 관계에 종류를 안 붙임

### GraphRAG 추출 단계: relationship과 claim

레포 · 위와 같은 커밋

- **무엇**: GraphRAG의 기본 추출은 entity와 relationship을, 선택 기능 claim(covariate)은 "누가 무엇을 했다"는 주장을 뽑는다.
- **정하지 않을 때**: relationship에는 종류 칸이 없다. source·target·description·weight만 남긴다(`packages/graphrag/graphrag/index/operations/extract_graph/graph_extractor.py:156-171`). claim은 주체·대상·claim type·상태·시작일·종료일·설명·근거 인용을 뽑는데, claim type은 LLM이 자유롭게 짓는다(`packages/graphrag/graphrag/prompts/index/extract_claims.py:17-25`). 뽑힌 claim type을 나중에 묶는 단계는 `extract_covariates` 폴더에 없다(`.../extract_covariates/claim_extractor.py:186`이 그대로 저장).
- **원문**: claim type 지시는 "Name it in a way that can be repeated across multiple text inputs, so that similar claims share the same claim type"이다(`extract_claims.py:19`).
- **수치·운영**: claim 추출은 기본으로 꺼져 있다(`config/defaults.py:132`).
- **우리 쪽에 옮길 때**: claim 한 줄은 사용자의 "사건 종류 + 기간" 키와 거의 같은 모양이다. 근거 인용 칸이 있어 원문 링크와 이어진다. 다만 같은 사건을 다른 작성자가 다른 claim type으로 쓰면 GraphRAG는 그대로 둘로 남긴다.
- **확인**: 코드 읽음.

### LinkedIn 고객지원 티켓 KG

글(논문) · 2024 · <https://arxiv.org/abs/2404.17723> (SIGIR 2024, Xu 외)

- **무엇**: 과거 Jira 티켓마다 안쪽 구조를 나무로 만들고, 티켓끼리 잇는 두 층 그래프로 RAG를 한다.
- **정하지 않을 때**: 티켓 사이 연결에 의미 종류를 붙이지 않는다. 명시 연결은 Jira 필드(clone 등)에서 오고, 암시 연결은 제목 embedding 유사도와 기준값으로 만든다(§3.1.2). 티켓 안쪽은 정해진 필드는 규칙으로, 나머지는 YAML 템플릿을 받은 LLM이 나눈다(§3.1.2).
- **원문**: "Implicit connections ℰimp are inferred from textual-semantic similarities across ticket titles"(§3.1.2). 앞으로 할 일로 "developing an automated mechanism for extracting graph templates"를 적는다(§6).
- **수치·운영**: MRR이 0.522에서 0.927로 올랐다(표 1). 약 6개월 운영했고 팀을 둘로 나눠 중앙 해결 시간이 7시간에서 5시간으로 28.6% 줄었다(§5, 표 3). 유사도 기준값은 논문에 없다.
- **우리 쪽에 옮길 때**: 문서마다 형식이 있다는 전제(YAML 템플릿)가 사용자 상황과 다르다. 그래도 "문서 사이 연결은 종류 없이, 문서 안 구조는 템플릿으로"라는 나눔은 그대로 옮길 수 있다.
- **확인**: 원문 읽음(HTML판).

### DataStax content-centric 그래프

글 · 2024-10-15 · Ben Chambers, <https://hackernoon.com/how-to-save-$70k-building-a-knowledge-graph-for-rag-on-6m-wikipedia-pages> (DataStax 블로그 원 주소는 IBM으로 넘어가 열리지 않음)

- **무엇**: 위키백과 600만 쪽으로 entity 추출 그래프와, 조각끼리만 잇는 그래프의 비용을 견준다.
- **정하지 않을 때**: entity·관계를 뽑지 않는다. 문서에 이미 있는 링크(위키 문단의 언급 id)로 조각 사이 들고 나는 연결만 만든다.
- **원문**: 추가 작업은 "we compute metadata indicating how each page links to other pages"뿐이라고 쓴다. entity 방식은 "it would take 41 weeks to load all 5,989,847 pages"라고 쓴다.
- **수치·운영**: 100행에 LLM 추출 405.93초, 전체 추정 $58,700이었다. content-centric은 약 24시간, 병렬로 2.5시간이었다.
- **우리 쪽에 옮길 때**: 사내 보고서에는 위키 링크 같은 명시 연결이 적다. 메타데이터(부서·기간·참조 문서번호)가 있으면 그것이 이 역할을 한다.
- **확인**: 원문 읽음(재게시본).

### Neo4j "Practical GraphRAG" 발표

영상 · 2025 (AI Engineer World's Fair, 2025-07-22 게시) · Michael Hunger·Stephen Chin·Jesús Barrasa, <https://www.youtube.com/watch?v=XNneh6-eyPg>

- **무엇**: lexical graph(문서·조각) → entity 추출 → 그래프 알고리즘 보강의 3단계를 소개한다.
- **정하지 않을 때**: 조각끼리 유사도 relationship을 점수와 함께 저장해 두고 검색 때 쓴다[09:47-10:14]. 이미 아는 entity 목록을 프롬프트에 넣으면 LLM이 추출 대신 찾기를 한다고 말한다[11:08-11:30]. 커뮤니티 요약이 여러 문서에 걸친 주제를 드러낸다고 말한다[12:26-12:48].
- **원문**: "so that the LLM doesn't do an extraction, but more an recognition and finding approach"[11:19-11:30]. 커뮤니티는 "it looks at which topics are reoccurring across many different documents"[12:33].
- **수치·운영**: 없다.
- **우리 쪽에 옮길 때**: 용어집을 프롬프트에 넣어 "고르기" 과제로 바꾸는 것은 작은 모델에 유리한 방향이다. 다만 용어집이 길면 8B 모델의 문맥을 채운다.
- **확인**: 영상 자막 확인(whisper 전사).

## 사람이 정하고 승인

### Zalando postmortem 분석

글 · 2025-09-25 · Dmitry Kolesnikov, <https://engineering.zalando.com/posts/2025/09/dead-ends-or-data-goldmines-ai-powered-postmortem-analysis.html>

- **무엇**: 여러 팀이 쓴 수천 건의 장애 회고 문서를 요약·분류·분석해 datastore 장애 패턴을 뽑는다.
- **정하지 않을 때**: 문서마다 요약 칸 다섯 개(문제·근본 원인·영향·해결·예방)는 고정한다. 기술 분류도 주어진 목록(Postgres, DynamoDB 등)으로 한다. 패턴은 모든 digest를 한 프롬프트에 넣어 LLM이 "common failure themes" 목록을 내게 한다. 패턴 목록을 미리 정했는지는 글에 없다.
- **원문**: "Postmortems vary widely in depth and clarity."(The Traditional Postmortem Problem 절). "We have observed up to 40% probability for hallucination at summary and analysis phases."(Dead Ends 절). "we still observe approximately 10% attribution, even with advanced models"(같은 절).
- **수치·운영**: 첫 시제품은 3B~12B 모델, 첫 출시는 27B 오픈 모델이었다. 27B 단계는 문서 하나에 90~120초가 걸렸다. 사람 검토는 개발 중에는 출력 묶음 전부를 보았고, 뒤에는 묶음마다 요약 10~20%를 무작위로 뽑아 보았다. 원문은 "we conducted 100% human curation of output batches"와 "we relaxed human curation to 10-20% of randomly sampled summaries from each output batch"다(Human curation 절). 검토는 찬반 표시뿐이었다. 작은 모델의 환각은 사람 주도 검토로 15% 아래로 내렸다(Dead Ends 절). "Surface Attribution Error"는 문서에 이름만 나온 기술을 원인으로 엮는 오류다. Zalando는 "only explicitly stated connections are flagged" 지시와 반례로 막으려 했다(Classification 절).
- **우리 쪽에 옮길 때**: 작성자가 다른 사내 문서 + 작은 모델이라는 조건이 사용자와 가장 가깝다. 작은 모델의 환각 40%와 귀속 오류는 "원인" 관계를 LLM에 고르게 할 때 그대로 나타날 위험이다.
- **확인**: 원문 읽음.

### Palantir Foundry ontology proposal

문서 · 연도 표기 없음 · <https://palantir.com/docs/foundry/ontologies/review-ontology-proposals/>

- **무엇**: ontology(객체 종류·관계 종류) 변경을 branch에서 하고 proposal로 검토받아 합친다.
- **정하지 않을 때**: 종류를 미리 다 정하지 않고, 바꿀 때마다 사람이 과제 단위로 승인·거절한다. 이 문서에는 LLM이 종류를 제안하는 기능이 나오지 않는다.
- **원문**: "An ontology proposal is analogous to a Pull Request in a version control system." 승인자는 기본으로 "an editor or owner of the underlying resource"여야 한다.
- **수치·운영**: 없다.
- **우리 쪽에 옮길 때**: "새 관계 이름 → 대기열 → 사람이 기존 이름에 합치거나 새로 승인"의 운영 모양을 빌릴 수 있다. 도구 자체는 쓸 수 없다.
- **확인**: 원문 읽음.

### Jesús Barrasa "Why Your Agent's Brain Needs a Playbook"

영상 · 2025 (AI Engineer World's Fair, 2025-06-27 게시) · <https://www.youtube.com/watch?v=CbiR9xS2skQ>

- **무엇**: ontology를 구현과 무관한 schema로 두고 추출과 검색을 둘 다 그것으로 몬다는 주장이다.
- **정하지 않을 때**: 다루지 않는다. 비정형 추출에도 schema를 "inject"해야 한다는 입장이다[06:03-06:25]. ontology를 그래프 안에 저장해 두면 ontology를 고쳐 검색 동작을 바꿀 수 있다고 말한다[13:14].
- **원문**: "my take on this is fundamentally be model-driven"[08:16]. "by changing my ontology, which is a data artifact in my graph, I'm changing the behavior of my retriever on the fly"[13:14].
- **우리 쪽에 옮길 때**: 반대편 입장으로 읽는다. 다만 "종류 목록을 데이터로 저장해 두고 바꾼다"는 점은 나중에 묶는 방식과 함께 쓸 수 있다.
- **확인**: 영상 자막 확인(whisper 전사).

### Daniel Chalef "Stop Using RAG as Memory"

영상 · 2025 (AI Engineer World's Fair, 2025-07-22 게시) · <https://www.youtube.com/watch?v=T5IMo5ntyhA>

- **무엇**: Zep이 개발자가 정한 entity type으로 기억을 거르는 시연이다.
- **정하지 않을 때**: 정하지 않으면 업무와 무관한 사실이 기억을 더럽힌다고 말한다[02:18-02:45]. 그래서 개발자가 Pydantic·Zod로 종류를 정하는 쪽을 권한다[04:51-04:59].
- **원문**: "semantic similarity is not business relevance"[03:23]. "We need domain-aware memory, not better semantic search."[03:46]
- **우리 쪽에 옮길 때**: 같은 회사의 Graphiti 코드는 종류 밖 관계도 받는다(위 Graphiti 절). 발표가 말하는 효과는 검색 때 종류로 거르는 쪽이고, 추출 때 닫는 쪽이 아니다.
- **확인**: 영상 자막 확인(whisper 전사).

## 우리 문제에 주는 것

가장 쓸 만한 것은 셋이다.

1. **Neo4j Graph Builder의 "목록 안에서만 고르는" 묶기 + ATOM의 embedding 이름 바꾸기.** 관계 이름을 자유롭게 뽑게 둔 뒤, 쌓인 이름 목록을 기존 이름으로만 합친다(`constants.py:835`). 이 과제는 고르기라서 작은 모델이 하기 쉽다. embedding 기준(ATOM 0.7)으로 먼저 걸러 LLM 호출을 줄일 수 있다.
2. **GraphRAG claim 모양.** (주체, 대상, 자유 claim type, 상태, 시작일, 종료일, 근거 인용)은 사용자의 "사건 종류 + 기간" 키에 근거 칸을 더한 모양이다. claim type을 자유로 받고 1번 묶기를 claim type에도 돌리면 "사건 종류를 미리 다 정하지 않는다"는 요구를 채운다.
3. **종류 없는 문서 연결을 먼저 깐다(LinkedIn·DataStax·Neo4j 발표).** 보고서끼리는 메타데이터와 embedding 유사도로 "관련 있음"만 먼저 잇는다. 원인·대응 같은 종류는 LLM이 확신하는 쌍에만 붙인다. LinkedIn은 이 모양으로 6개월 운영해 해결 시간을 28.6% 줄였다.

사람 검토는 Zalando처럼 처음에 전부 보고 표본으로 줄이는 방식, 바뀐 종류는 Palantir처럼 proposal로 승인하는 방식이 실제 운영 사례다. 오픈소스 도구 중 묶기 결과를 사람 승인 대기열에 넣는 것은 이번에 본 코드에 없었다(Neo4j는 바로 고친다).

아무도 풀지 않은 것:
- **다른 작성자의 같은 사건 합치기.** ATOM은 (주어, 관계, 목적어)가 같아진 triple만 합친다. GraphRAG claim은 합치지 않는다. 기간이 조금 다르고 이름이 다른 두 보고서의 사건을 하나로 보는 규칙은 어느 출처에도 없다.
- **작은 모델·한국어에서 종류 발견·묶기의 품질.** 수치는 Zalando의 3B~12B 모델 환각 최대 40% 하나뿐이다. 묶기 단계 자체의 정확도를 잰 실무 글은 찾지 못했다.
- **묶은 뒤 옛 판단 되돌리기.** Graphiti는 종류를 바꾸면 새 그래프로 다시 넣으라고 한다. Neo4j는 label을 덮어써 옛 이름이 남지 않는다. 묶기 이력을 남겨 되돌리는 설계는 보지 못했다.

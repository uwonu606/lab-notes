# Beever Atlas는 개발자가 정한 엔티티 종류와 이미 저장된 엔티티 레지스트리를 추출 프롬프트에 넣는다. 하지만 원문 연결은 별칭으로 맞춰지지 않는다

Beever Atlas는 Slack·Discord·Teams·Mattermost 대화를 atomic fact로 바꾼다. 그 fact로 채널마다 wiki를 증분으로 다시 짓는 Apache-2.0 저장소다. fact는 Weaviate에, 엔티티 그래프는 Neo4j에 둔다.
사용자 목표에 주는 답은 이렇다. [확인] 엔티티 종류 11개와 관계 동사 목록은 개발자가 프롬프트 문자열에 박아 두었다. 사용자가 편집하는 schema 파일은 없다.
[확인] "용어집" 역할은 Neo4j에 쌓인 엔티티 전체(`name, type, aliases`)가 맡는다. 이 목록을 추출 프롬프트에 그대로 넣는다. 단 한 번의 `process_messages` 호출 안에서 병렬로 도는 배치들은 호출 시작 때 읽은 같은 목록을 받는다. 사람이 쓰는 별칭 목록은 없다. LLM이 뽑은 별칭이 쌓인다.
[확인] 원문 연결은 fact마다, 그 fact의 `entity_tags`에 있는 모든 이름으로 `MENTIONED_IN` 링크를 건다. 처음 본 곳만이 아니다. 사용자 실험에서 재현율을 0.92로 올린 방식과 같다.
[확인] 다만 `entity_tags`는 레지스트리를 받지 않는 fact 추출기가 만든다. 링크는 이름이 글자 그대로 같을 때만 기존 엔티티에 붙는다. 별칭으로 적힌 이름은 `Unresolved` 임시 노드로 갈라진다.
[확인] 범용어 허브를 막는 장치는 프롬프트 금지 문구와 wiki 용어집 페이지의 표시 필터뿐이다. 그래프 링크 단계에는 빈도 기준이나 stoplist가 없다.
[확인] 효과를 잰 정밀도·재현율 수치는 저장소에 없다.

## 한 바퀴 흐름

메시지 묶음(batch) 하나가 wiki 페이지가 되기까지의 경로다. 파일 경로는 `src/beever_atlas/` 기준이다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. 레지스트리 적재 | `process_messages` 호출 시작 때 Neo4j의 모든 `Entity`를 `{name, type, aliases}`로 읽는다. 엔티티를 쓴 배치가 끝나면 다시 읽는다. 하지만 같은 호출의 배치 task는 모두 시작하자마자 첫 목록을 복사해 가므로, 다시 읽은 목록은 다음 호출에서야 쓰인다 | `services/batch_processor.py:519`, `:1993-2001`, `:2046-2047`, `stores/neo4j_store.py:1723-1735` |
| 2. 전처리 | 메시지를 정리하고 `preprocessed_messages`로 둔다 | `agents/ingestion/pipeline.py:31` |
| 3a. fact 추출 | LLM이 메시지마다 fact를 뽑는다. fact마다 `entity_tags`, `fact_type`, `source_message_id`, `message_ts`가 붙는다. 이 프롬프트에는 레지스트리가 들어가지 않는다 | `agents/prompts/fact_extractor.py:36-39`, `:208` |
| 3b. 엔티티 추출 | LLM이 엔티티·관계를 뽑는다. 프롬프트에 엔티티 종류 표와 `known_entities`(1단계 레지스트리)가 들어간다 | `agents/prompts/entity_extractor.py:31-35`, `:42-56` |
| 4. 품질 게이트 | confidence 0.6 미만 관계를 버린다. channel 범위 엔티티 중 남은 관계가 없는 것을 버린다 | `agents/callbacks/quality_gates.py:121-146`, `infra/config.py:161` |
| 5. 결정적 dedup | 이름 정규화 → 레지스트리 이름·별칭과 정확 대조 → 같은 배치 안 임베딩 cosine ≥ 0.92 병합 → 0.85~0.92 구간은 LLM 판정 자리(현재 스텁) | `services/entity_dedup.py:45-51`, `:261-364`, `:161-179` |
| 6. 저장 | fact를 Weaviate에 쓴다. 엔티티를 `(name, type, scope)` 키로 Neo4j에 MERGE한다. 관계 동사를 정규화한다 | `agents/ingestion/persister.py:381-445` |
| 7. 원문 연결 | fact 하나마다 `entity_tags`의 모든 이름 → `Event{weaviate_id}` 노드로 `MENTIONED_IN`을 건다. 기존 노드에 붙는 것은 이름이 같은 `global` 범위 타입 노드뿐이다 | `agents/ingestion/persister.py:650-666`, `stores/neo4j_store.py:1821-1883` |
| 8. 타입 미정 노드 처리 | 큐가 비면 `Unresolved` 노드에 LLM이 타입을 붙인다. 새 타입은 confidence ≥ 0.8일 때만 받는다 | `services/unresolved_classifier.py:1-22`, `:64-66` |
| 9. 토픽 군집 | 아직 군집이 없는 fact를 기존 군집 중심 벡터와 비교한다. cosine > 0.6이면 그 군집에, 아니면 새 군집에 넣는다 | `services/consolidation.py:384-432`, `infra/config.py:293` |
| 10. wiki 증분 갱신 | 새 fact를 페이지로 결정적으로 보낸다. 군집 → topic 페이지, `entity_tags`가 있으면 people·glossary 페이지, `fact_type` → decisions·faq·action-items. `WIKI_MAINTENANCE_MODE=auto`면 60초 debounce 뒤 페이지마다 LLM 한 번으로 해당 섹션만 다시 쓴다. 코드 기본값은 `manual`이고 `.env.example`은 `auto`다 | `services/wiki_maintainer.py:1-35`, `:755-813`, `infra/config.py:755`, `.env.example:504` |

용어 하나를 짚는다. [확인] 그래프의 `Event` 노드는 "fact 하나"를 뜻하는 episodic 노드다(`stores/neo4j_store.py:853`). 엔티티 종류의 `Event`(마감일·출시일 같은 일회성 사건)는 `Entity{type:'Event'}`로 따로 있다. 이름이 같아서 헷갈리기 쉽다.

## 축별 분석

### A schema

[확인] 엔티티 종류는 개발자가 프롬프트 문자열 안의 표로 정한다. Person, Technology, Project, Team, Decision, Meeting, Artifact, Organization, Concept, Location, Event의 11개다. 각각 `global`/`channel` 범위가 붙는다(`agents/prompts/entity_extractor.py:42-59`).
[확인] 관계는 "Preferred types" 12개를 프롬프트로 권한다(`entity_extractor.py:102-104`). 저장 직전에 `verb_normalizer.py`가 정규 동사 집합으로 바꾼다. 이 집합에는 `CANONICAL_VERBS`, 리터럴 대응표 `VERB_NORMALIZATION`, 정규식 버킷이 있다. 어디에도 맞지 않으면 `MENTIONS`로 떨어진다(`agents/ingestion/verb_normalizer.py:44-79`, `:82-137`, `:147-173`). 방향은 뒤집지 않는다(`:13-15`).
[확인] 추출 출력은 강제되지 않는다. 엔티티 추출 agent는 구조화 출력(`output_schema`)을 일부러 끈다. 이유는 ADK가 검증 실패 때 복구 콜백보다 먼저 예외를 던지기 때문이다. 그래서 `response_mime_type="application/json"`만 건다(`agents/ingestion/entity_extractor.py:17-22`, `:33-37`).
[확인] pydantic 모델의 `type`은 그냥 `str`이다(`agents/schemas/extraction.py:137`). 쓰기 직전에 엔티티 타입을 목록과 대조하는 검증은 없다. 관계 동사만 정규화로 닫힌다. fact의 `fact_type`은 5개 값 밖이면 `observation`으로 바꾼다(`persister.py:311-316`).
[확인] 페이지 종류도 코드에 박혀 있다. 필수 8종(overview, topic, people, glossary, decisions, faq, activity, resources)과 조건부 5종이 있다(`wiki/kinds.py:150-188`). 운영자는 채널 정책의 `wiki.force_kinds`·`wiki.suppress_kinds`로 켜고 끈다(`wiki/kinds.py:15-20`).
[확인] 페이지 내용은 종류별 JSON Schema(`wiki/schemas/{topic,entity,decisions,faq,action_items}.json`)로 검증할 수 있다. 실패하면 오류 문장을 재시도 프롬프트에 넣는다(`services/wiki_maintainer.py:97-111`). 즉 "쓰기 직전 검증"은 엔티티가 아니라 wiki 페이지에 있다.
[확인] 다만 이 검증은 기본으로 꺼져 있다. per-kind 경로는 `WIKI_LLM_NATIVE_REDESIGN`이 켜졌고 종류가 위 5개일 때만 탄다(`services/wiki_maintainer.py:67`, `:1571-1572`). 이 플래그의 코드 기본값과 `.env.example` 값은 모두 false다(`infra/config.py:854`, `.env.example:574`). 엔티티가 붙은 fact가 가는 people·glossary 페이지는 5개 안에 없다.
[확인] 문서는 schema를 바꾸려면 코드의 프롬프트를 고치라고 한다. "you can modify prompt templates directly in the codebase"(`docs/content/guides/prompt-tuning.mdx:162-166`). 그런데 그 문서가 가리키는 `src/beever_atlas/llm/prompts.py`는 저장소에 없다. 실제 엔티티 프롬프트는 `agents/prompts/entity_extractor.py`다.
참고: [확인] 프롬프트 안에 숫자가 어긋나 있다. "These 11 types"라고 쓴 뒤 "Prefer the 7 standard types"라고 한다(`entity_extractor.py:61`, `:67-68`). 출력 형식 예시도 7종만 나열한다(`:158`). 종류를 늘리고 문구를 다 고치지 않은 흔적이다.

### B 용어집

[확인] 정식 이름 + 별칭 구조가 있다. 엔티티마다 `name`(canonical)과 `aliases` 배열을 둔다(`agents/schemas/extraction.py:134-168`).
[확인] 쓰는 쪽은 사람이 아니라 LLM이다. 프롬프트가 "가장 완전하고 공식적인 이름을 canonical로, 짧은 형태를 aliases로" 적게 한다(`entity_extractor.py:96-97`). 다른 문자 체계 표기(阿明 / Ah Ming)도 aliases로 묶게 한다(`:9-16`). dedup 병합 때 진 쪽 이름과 별칭이 aliases에 더해진다(`services/entity_dedup.py:135-145`).
[확인] 추출 전에 프롬프트로 준다. 레지스트리 전체가 `known_entities`로 들어가고 "canonical name을 쓰라"고 지시한다(`entity_extractor.py:31-35`, `:88-94`). 그런데 같은 프롬프트의 다른 대목은 반대로 말한다. "Extract names as they appear in messages... your job is accurate extraction, not normalisation"(`:82-84`). 지시가 서로 어긋난다.
[확인] 같은 `process_messages` 호출 안의 배치들은 모두 호출 시작 때의 레지스트리를 받는다. 배치 task가 `list(known_entities)`를 시작하자마자 복사하고, semaphore는 그 뒤에 잡는다(`services/batch_processor.py:1993-1995`, `:828`). 기본 worker tick은 `sync_batch_size × ingest_batch_concurrency` = 25 × 4 메시지를 한 번에 가져온다(`services/extraction_worker.py:393`). 그래서 한 tick 안의 4개 배치는 서로 새로 만든 엔티티를 보지 못한다.
[확인] 추출 뒤에도 정규화한다. 소문자·구두점 제거·공백 정리 뒤 레지스트리의 이름·별칭과 정확히 맞으면 레지스트리 이름으로 바꾼다(`entity_dedup.py:58-70`, `:261-314`). 관계의 source/target도 같은 대응표로 고쳐 쓴다(`:411-417`).
[확인] 사람이 미리 쓰는 용어집 파일은 없다. 사람 개입 지점은 wiki 페이지 정책(`force_kinds`/`suppress_kinds`)뿐이다. 엔티티 이름·별칭을 사람이 편집하는 API는 찾지 못했다. 찾아본 곳: `api/policies.py`, `models/`, `infra/config.py`에서 `entity_types|glossary|ontology|alias` grep.
[확인] 레지스트리의 `resolve_alias`, `fuzzy_match`(Jaro-Winkler), `find_similar_by_embedding`은 정의돼 있다. 하지만 수집 경로에서는 부르지 않는다(`stores/entity_registry.py:22-126`). 실제 호출처는 wiki 위키링크를 엔티티에 잇는 `find_entity_by_name_or_alias` 하나다(`services/wiki_maintainer.py:1880-1892`).
참고: [확인] 엔티티 upsert는 `ON MATCH SET typed.aliases = $aliases`로 별칭을 덮어쓴다(`stores/neo4j_store.py:328`, `:373`). dedup이 기존 엔티티에 맞춰 이름을 바꿀 때 기존 별칭은 새 목록에 넣지 않는다(`entity_dedup.py:305-314`). 그래서 코드상 예전 배치의 별칭이 지워질 수 있다. 실행해서 확인하지는 않았다.
참고: wiki의 "Glossary" 페이지는 출력물이다. 채널 요약의 `glossary_terms`에 Technology·Project 엔티티와 3개 이상 군집에 나온 엔티티를 더한다. 그 목록으로 LLM이 정의를 쓴다(`wiki/compiler.py:5040-5082`). 추출 입력으로 되돌아가지 않는다.

### C 원문 연결 범위

[확인] 원문 단위는 메시지다. fact마다 `source_message_id`(Slack `ts` 등)와 `message_ts`가 있다(`agents/schemas/extraction.py:55-65`). LLM이 id를 빠뜨리면 URL 대조, 단어 겹침 순으로 메시지를 다시 찾는다(`persister.py:242-260`).
[확인] 엔티티 → 원문 연결은 "나온 모든 곳"이다. fact 하나마다 `entity_tags`의 모든 이름으로 `{entity_name, weaviate_fact_id}` 링크를 만든다(`persister.py:650-666`). Neo4j에서 `(Entity)-[:MENTIONED_IN]->(Event{weaviate_id})`로 MERGE한다(`stores/neo4j_store.py:1866-1874`).
[확인] 엔티티 노드 자체의 `source_message_id`는 "처음 식별된 메시지" 하나다(`agents/schemas/extraction.py:173-174`). 사용자 실험의 공식 변환 코드처럼 첫 출현만 남는 필드가 따로 있다. 하지만 링크는 이 필드가 아니라 episodic 링크로 건다.
[확인] 한계가 있다. 링크 이름은 fact 추출기가 뽑은 `entity_tags` 그대로다. fact 추출기 프롬프트에는 레지스트리가 없다(`fact_extractor.py:36-39`). dedup의 이름 대응표(`merges`)도 fact의 `entity_tags`에는 적용되지 않는다. `merges`는 진행 이벤트 표시에만 쓰인다(`services/batch_processor.py:1443-1467`).
[확인] 링크 쓰기는 `name`이 글자 그대로 같은 `Unresolved` 노드를 MERGE한 뒤, 같은 이름의 타입 있는 노드와만 합친다(`stores/neo4j_store.py:1853-1872`). 별칭 대조는 없다. 예를 들어 fact가 `postgres`라고 태그하면 `PostgreSQL` 노드가 아니라 `postgres` 임시 노드에 링크가 붙는다.
[확인] 합칠 대상도 `scope: 'global'` 노드로 한정된다(`stores/neo4j_store.py:1863`). Decision·Meeting·Artifact·Event처럼 `channel` 범위로 저장된 엔티티는 이름이 같아도 링크를 받지 못한다. 대신 같은 이름의 global `Unresolved` 노드가 생긴다. channel 엔티티를 쓸 때의 heal은 같은 channel 범위 형제만 흡수하므로 이 노드와 합쳐지지 않는다(`stores/neo4j_store.py:333-335`). 실행해서 확인하지는 않았다.

### D 새/기존 연결

새 배치가 기존 엔티티와 이어지는 정확한 절차다.

1. [확인] 추출 전: 레지스트리 전체를 프롬프트에 넣는다. LLM이 기존 canonical 이름을 쓰도록 유도한다(`entity_extractor.py:31-35`). 크기 제한이나 관련 엔티티만 고르는 필터는 없다(`stores/neo4j_store.py:1727-1730`는 `MATCH (e:Entity)` 전체). 이 레지스트리는 `process_messages` 호출 시작 때 찍은 사본이다. 같은 호출 안 다른 배치가 만든 엔티티는 들어 있지 않다(B 참고).
2. [확인] Tier 1: 새 이름을 정규화한다. 레지스트리 이름·별칭의 정규화 형태와 같으면 레지스트리 이름으로 바꾸고, 원래 이름은 별칭으로 내린다(`entity_dedup.py:286-314`).
3. [확인] Tier 2: 임베딩 cosine ≥ 0.92면 병합한다. 하지만 비교 대상은 이번 배치의 버킷끼리뿐이다(`entity_dedup.py:325-362`). 모듈 주석도 "graph-stored `find_similar_by_embedding`이 아니라 배치마다 새로 계산"이라고 밝힌다(`:10-15`). 즉 기존 엔티티와는 임베딩으로 비교하지 않는다.
4. [확인] Tier 3: 0.85~0.92 구간 쌍은 배치당 5개까지 LLM 판정으로 보낸다. 그런데 `_llm_resolve_pair`는 항상 `False`를 돌려주는 스텁이다. 주석에 "A future PR may wire a real Gemini call here"라고 적혀 있다(`entity_dedup.py:161-179`). 지금은 사실상 병합하지 않는다.
5. [확인] 저장: global 엔티티는 `(name, type, scope='global')`로, channel 엔티티는 `(name, type, channel_id)`로 MERGE한다(`stores/neo4j_store.py:360`, `:314`). 같은 이름이라도 LLM이 타입을 다르게 붙이면 노드가 둘로 갈린다.
6. [확인] 페이지 쪽 연결은 임베딩이다. 새 fact 벡터를 기존 토픽 군집 중심과 비교한다. 가장 가까운 군집이 cosine > 0.6이면 그 군집 페이지에 들어간다(`services/consolidation.py:405-416`, `infra/config.py:293`).
7. [확인] 그 밖에 엔티티가 붙은 모든 fact는 people·glossary 두 페이지로 간다. 엔티티별 페이지는 폐기됐다. "The legacy `entity:<slug>` page kind is dead"(`services/wiki_maintainer.py:768-772`).

### E 새 용어

[확인] 새 엔티티 이름: 레지스트리에 없으면 LLM이 쓴 이름이 그대로 canonical이 된다. 다음 `process_messages` 호출(기본 경로에서는 다음 worker tick)부터 레지스트리에 들어간다. 같은 호출의 다른 배치에는 들어가지 않는다(`entity_dedup.py:292-294`, `batch_processor.py:1993-1995`, `:2046-2047`). 승인 대기열은 없다.
[확인] 새 엔티티 타입: 프롬프트가 PascalCase 새 타입을 허용한다(`entity_extractor.py:61-68`). 추출 경로에서는 검증 없이 저장된다(A 참고).
[확인] 타입 미정 이름: 관계 끝점이나 `entity_tags`에만 있고 엔티티로 뽑히지 않은 이름은 `type='Unresolved'`, `awaiting_type=true` 임시 노드가 된다(`persister.py:541-631`, `stores/neo4j_store.py:1853-1862`). 관계 끝점 임시 노드는 confidence ≥ 0.8 관계에서만 만든다. 양 끝이 모두 모르는 이름이면 임시 노드를 만들지 않는다(`persister.py:556-580`).
[확인] 이 임시 노드를 큐가 빌 때 `UnresolvedClassifier`가 25개씩 묶어 LLM으로 타입을 붙인다. 기존 타입은 confidence ≥ 0.55, 새 타입은 ≥ 0.8이어야 받는다. 낮으면 7일 뒤 재시도한다(`services/unresolved_classifier.py:5-20`, `:64-66`, `:280`). 여기서 "기존 타입"은 11종만이 아니다. 그 채널에 이미 나온 타입도 포함한다. LLM이 전에 만든 새 타입도 한 번 들어오면 0.55 기준을 받는다(`:245`, `:279`). 사람 승인 단계는 없다.
[확인] 관계 동사: 목록 밖 동사는 대응표 → 정규식 버킷 → `MENTIONS` 순으로 흡수한다(`verb_normalizer.py:181-210`). 원래 동사는 엣지에 남기지 않고 로그 원장(`sync_summary`)에만 남긴다(`:16-20`).

### F 범용어 허브

[확인] 추출 프롬프트가 일반어를 막는다. "Generic words (software, system, tool, code, data) are NOT entities"(`entity_extractor.py:73-74`). 흔한 파일명(image.png 등)도 막는다(`:75-77`).
[확인] "No Orphan Entities" 규칙과 품질 게이트가 관계 없는 엔티티를 버린다(`entity_extractor.py:22-26`, `quality_gates.py:134-146`). 다만 `global` 범위 엔티티는 관계가 없어도 남긴다(`quality_gates.py:145`).
[확인] wiki 출력 단계에만 고정 목록 필터가 있다. `GENERIC_GLOSSARY_TERMS`(windows, slack, github, aws, redis 등)는 Glossary 페이지 후보에서 빠진다(`wiki/compiler.py:712-757`, `:5075-5079`). `_GENERIC_TOOLS`는 overview의 도구 목록에서 빠진다(`wiki/compiler.py:1389-1409`).
[확인] 그래프 연결 단계에는 대책이 없다. `MENTIONED_IN` 링크에 빈도 상한·IDF 가중·stoplist가 없다(`persister.py:650-666`). UI용 `CO_MENTIONED` 엣지는 공유 fact 수 ≥ 2만 본다. 가중치는 `min(1.0, shared/5)`라서 흔한 엔티티일수록 오히려 강해진다(`stores/neo4j_store.py:1155-1192`).
[추정] 사용자 실험의 허브 문제(KG·schema·LLM이 모든 것을 잇는 문제)는 이 설계에서도 그대로 생길 것이다 — 사례 1개: 코드에서 링크 단계 필터를 찾지 못했다. 검색한 것: `stopword|stoplist|GENERIC_|blocklist|denylist` 전체 grep. 실측하려면 채널 하나를 sync한 뒤 엔티티별 `MENTIONED_IN` 차수 분포를 보면 된다.

### G 엔티티·이벤트

[확인] 이벤트를 엔티티 종류로 뽑는다. `Event`(일회성 사건), `Meeting`, `Decision`이 종류 표에 있다(`entity_extractor.py:50-56`). Decision에는 `rationale`, `decided_by` 속성을 둔다(`:138`).
[확인] 관계에 시간축이 있다. 관계마다 `valid_from`(메시지 ISO 시각)을 받는다(`entity_extractor.py:114`). Neo4j 관계에는 `valid_from`·`valid_until`이 저장된다(`stores/neo4j_store.py:639-656`).
[확인] fact에도 시간축이 있다. `message_ts`, `fact_type`(decision/action_item/question/opinion/observation)이 붙는다(`agents/schemas/extraction.py:64-68`). decision fact는 `alternatives_considered`, `consequences_open`도 받는다(`:90-102`).
[확인] fact는 무효화된다. 새 fact가 기존 fact와 모순되면 LLM이 판정해 `superseded_by`·`invalid_at`을 붙인다(`services/contradiction_detector.py:1-5`, `models/domain.py:87-88`). 문서에는 confidence ≥ 0.8이면 자동 대체한다고 적혀 있다(`docs/pipeline-architecture.md:443-444`).
[확인] timeline 페이지는 조건부다. 채널 나이 30일 이상, 활동 구간(7일 넘는 공백으로 나눈 구간) 3개 이상일 때만 만든다(`wiki/kinds.py:55-59`, `:114-120`). 입력은 활동 구간, 날짜순 결정, 구간별 기여자다(`wiki/prompts/timeline.txt` 끝 `## Data`).

### H 근거 수치

[확인] 추출·연결 품질을 잰 수치는 없다. `README.md`, `docs/`, `CHANGELOG.md`, `HANDOFF.md`에서 `precision|recall|benchmark|f1|accuracy`를 찾았다. 수치가 나온 것은 지연 시간 목표표뿐이다(`docs/pipeline-architecture.md:704-718`). `docs/content/guides/prompt-tuning.mdx:305-307`은 "Entity classification accuracy"를 지켜볼 지표로 적지만 값은 없다.
[확인] 측정 도구는 있다. `scripts/qa_test_harness.py`는 QA 답변을 채점한다. `scripts/wiki_bench.py`는 wiki 컴파일 시간·파싱 실패를 잰다. `scripts/bench_ingest.py`는 수집 단계별 시간을 잰다. 셋 다 엔티티 추출이나 원문 연결의 정확도를 재지 않는다.
[확인] 임계값 0.92/0.85는 "architect-approved bands"라고만 적혀 있다(`entity_dedup.py:45`). 근거 문서로 가리키는 `.omc/plans/pipeline-cost-latency-reduction-v2.md`는 저장소에 없다(`ls -a` 결과에 `.omc` 없음).
[확인] 테스트는 동작 단위 테스트다. 예: `tests/unit/test_deterministic_cross_batch_validator.py`. 품질 평가셋은 찾지 못했다.

## 가져올 것

| 무엇 | 왜 사용자 시스템에 맞는가 | 주의 |
|---|---|---|
| fact마다 모든 엔티티로 episodic 링크 | 사용자가 실험으로 찾은 "나온 모든 청크로 링크"와 같은 결론이다. `Event{fact_id}` 중간 노드를 두면 엔티티-원문 다대다가 깔끔해진다 | 링크 이름을 canonical로 바꾼 뒤 걸어야 한다. Beever Atlas는 이 단계를 빠뜨렸다. channel 범위 엔티티에는 링크가 붙지 않는 구멍도 있다(C) |
| 3단 dedup(정규화 정확 대조 → 임베딩 ≥ 0.92 → 애매 구간만 LLM) | 비용이 싼 단계부터 거른다. 애매 구간 쌍 수를 배치당 상한으로 묶는다 | 임베딩 비교를 레지스트리(기존 엔티티)까지 넓혀야 새/기존 연결에 쓸모가 있다(D) |
| 관계 동사 정규화 + 원장 | 사용자 실험의 관계 275종 → 17종 정규화와 같은 일이다. 대응표·정규식·catch-all 순서와 "방향은 뒤집지 않는다" 규칙을 그대로 쓸 만하다 | catch-all `MENTIONS`가 커지면 그 자체가 의미 없는 엣지가 된다 |
| 타입 미정 임시 노드 + 나중 분류 | schema 밖 이름을 버리지 않고 `Unresolved`로 보관한다. 새 타입은 높은 confidence에서만 받는다. 사람 승인 대기열로 바꾸기 쉬운 자리다 | 사용자 목표대로라면 자동 승인 대신 대기열로 돌리는 편이 맞다 |
| 페이지 종류 레지스트리 + 조건부 생성 | 사람이 정한 페이지 종류를 코드 한 곳에 두고, 데이터 신호가 있을 때만 페이지를 연다 | 종류별 JSON Schema 검증을 엔티티에도 걸어야 schema가 실제로 강제된다. 페이지 검증도 기본값에서는 꺼져 있다(A) |
| 결정적 라우팅 → 섹션 단위 재작성 | 새 fact가 영향을 주는 페이지만 LLM으로 고친다. 증분 llm-wiki의 비용을 묶는다 | — |

가져오지 않을 것:
- 범용어 대책은 출력 표시 필터뿐이다. 사용자 문제(허브로 정밀도 하락)의 답이 되지 않는다.
- 레지스트리 전체를 프롬프트에 넣는 방식은 엔티티 수가 늘면 프롬프트가 같이 커진다. [확인] 코드에 상한이 없다(`stores/neo4j_store.py:1727-1730`).

라이선스: Apache-2.0이다. 코드를 가져다 쓰려면 LICENSE·NOTICE를 함께 두고 바꾼 파일에 변경 표시를 한다. "Beever Atlas" 이름과 로고는 상표 정책(`TRADEMARK.md`)이 따로 막는다.

## 출처

- 저장소: https://github.com/Beever-AI/beever-atlas
- commit: `7d791af27ef4aa19644cb385c7ca24619bc4f848` (2026-07-01)
- 라이선스: Apache License 2.0 (`LICENSE`, `NOTICE`), 상표 정책 `TRADEMARK.md`
- 로컬 사본: `lab/repos/Beever-AI_beever-atlas` (`git clone --depth 1`)
- 읽은 주요 파일: `src/beever_atlas/agents/prompts/entity_extractor.py`, `agents/prompts/fact_extractor.py`, `agents/schemas/extraction.py`, `agents/ingestion/{pipeline,entity_extractor,cross_batch_validator,persister,verb_normalizer}.py`, `agents/callbacks/quality_gates.py`, `services/{entity_dedup,batch_processor,unresolved_classifier,consolidation,wiki_maintainer,contradiction_detector}.py`, `stores/{entity_registry,neo4j_store}.py`, `wiki/{kinds,compiler}.py`, `wiki/prompts/timeline.txt`, `wiki/modules/timeline.py`
- 실행: 하지 않았다. 코드만 읽었다.

## 검증 기록

검증자가 같은 commit(`7d791af`)의 로컬 사본을 다시 열어 인용한 파일:줄을 하나씩 대조했다. 코드는 실행하지 않았다.

### 그대로 맞은 것

- 엔티티 종류 11개 표, 선호 관계 12개, PascalCase 새 타입 허용, "7 standard types" 숫자 어긋남(`agents/prompts/entity_extractor.py:42-68`, `:102-104`, `:158`).
- 구조화 출력을 끈 이유와 `type: str`(`agents/ingestion/entity_extractor.py:17-22`, `agents/schemas/extraction.py:137`). 기본 경로는 ADK pipeline이다(`use_batch_api` 기본 false, `infra/config.py:378`). Batch API 경로도 같은 프롬프트를 쓴다(`services/batch_pipeline.py:77-87`).
- schema가 사람이 미리 정한 것인지: 엔티티 종류는 개발자가 코드에 박은 표다. LLM이 만든 것을 사람이 정했다고 부풀리지 않았다. 별칭·레지스트리는 LLM 출력이 쌓인 것이라는 보고서 서술도 맞다. 엔티티를 사람이 고치는 API는 다시 찾아도 없었다(`api/*.py`의 post·put·patch·delete 라우트, `agents/tools/__init__.py:327`의 `upsert_entity`는 `NotImplementedError` 스텁).
- dedup 3단, 배치 안 임베딩 비교, `_llm_resolve_pair` 스텁, 임계값 0.92/0.85, 배치당 5쌍(`services/entity_dedup.py:10-22`, `:45-51`, `:161-179`, `:261-390`).
- fact마다 `entity_tags` 전체로 `MENTIONED_IN` 링크, fact 추출 프롬프트에 레지스트리 없음, `entity_tags`를 canonical로 바꾸는 단계 없음(`agents/ingestion/persister.py:650-666`, `agents/prompts/fact_extractor.py:36-39`). coreference 단계는 대명사만 이름으로 바꾸고 레지스트리를 쓰지 않는다(`agents/prompts/coreference_resolver.py:1-15`).
- 별칭 덮어쓰기(`stores/neo4j_store.py:328`, `:373`; `batch_upsert_entities`도 `upsert_entity`를 부른다, `:481-506`).
- 범용어 프롬프트 금지, `GENERIC_GLOSSARY_TERMS`에 slack·github·aws·redis 포함, `CO_MENTIONED` 가중치 `min(1.0, shared/5)`(`wiki/compiler.py:710-757`, `stores/neo4j_store.py:1152-1195`).
- 관계 `valid_from`·`valid_until`, fact `invalid_at`·`superseded_by`, timeline 조건, 군집 cosine > 0.6(`stores/neo4j_store.py:639-656`, `models/domain.py:87-88`, `wiki/kinds.py:114-120`, `services/consolidation.py:405-416`).
- `.omc` 디렉터리 없음, 지연 시간 표(`docs/pipeline-architecture.md:704-718`).

### 고친 것

1. 레지스트리 갱신 시점. 원래 "다음 배치부터 레지스트리에 들어간다"였다. 같은 `process_messages` 호출의 배치 task는 시작하자마자 `list(known_entities)`로 첫 사본을 가져간다. semaphore는 그 뒤에 잡는다(`services/batch_processor.py:1993-1995`, `:828`). 그래서 `:2047`의 재적재는 다음 호출에서야 쓰인다. 기본 경로에서 한 호출은 worker tick 하나(25 × 4 메시지, `services/extraction_worker.py:393`)다. 제목, 머리말, 흐름 표 1단계, B, D-1, E를 고쳤다.
2. wiki 페이지 JSON Schema 검증. 원래 늘 도는 것처럼 적혀 있었다. 실제로는 `WIKI_LLM_NATIVE_REDESIGN`이 켜졌을 때만 돈다. 이 값은 코드 기본값과 `.env.example`에서 모두 false다(`infra/config.py:854`, `.env.example:574`). 대상도 topic·entity·decisions·faq·action_items 5종뿐이다. people·glossary는 빠진다(`services/wiki_maintainer.py:67`, `:1571-1572`). A와 "가져올 것" 표를 고쳤다.
3. 원문 연결의 범위 한정. 링크가 기존 노드와 합쳐지는 대상은 `scope: 'global'` 타입 노드뿐이다(`stores/neo4j_store.py:1863`). channel 범위 엔티티(Decision·Meeting·Artifact·Event)는 링크를 받지 못한다는 점을 C와 흐름 표 7단계에 더했다.
4. MERGE 키. channel 엔티티는 `(name, type, channel_id)`로 MERGE한다(`stores/neo4j_store.py:314`). D-5를 고쳤다.
5. 프롬프트 지시 충돌. "canonical name을 쓰라"(`:31-35`)와 "not normalisation"(`:82-84`)이 한 프롬프트에 같이 있다는 점을 B에 더했다.
6. Unresolved 분류의 "기존 타입". 11종만이 아니라 채널에 이미 나온 타입도 포함한다(`services/unresolved_classifier.py:245`, `:279`). E를 고쳤다.
7. 수치 축 보강. QA 채점·wiki 벤치·수집 벤치 스크립트가 있지만 추출·연결 정확도는 재지 않는다는 점을 H에 더했다. schema 수정 방법을 안내하는 문서가 없는 파일(`src/beever_atlas/llm/prompts.py`)을 가리킨다는 점을 A에 더했다.
8. wiki 자동 갱신 조건. `WIKI_MAINTENANCE_MODE`의 코드 기본값은 `manual`이고 `.env.example`은 `auto`다(`infra/config.py:755`, `.env.example:504`). 흐름 표 10단계에 조건을 붙였다.

### 판정

[확인] 사람이 미리 정한 schema는 있다. 개발자가 프롬프트에 박은 엔티티 종류 11개와 관계 동사 정규화 표다. 사람이 정한 용어집은 없다. 그래서 후보에서 빼지 않는다.

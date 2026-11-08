# Jonex는 schema(TBox YAML)와 용어집(동의어 묶음)을 지식 그래프 쪽에서 쓰고, llm-wiki 쪽(openkb)에는 사람이 고치는 엔티티 종류 목록만 둔다

Jonex(yuezhiai/jonex)는 중국 기업용 지식 플랫폼이다.
문서를 파싱한 뒤 지식 베이스(KB) 종류에 따라 두 길 중 하나로 보낸다.
첫째 길은 "Ontology 库"(kb_type=lightrag)다. 사람이 정한 TBox(엔티티·관계 종류)와 KB별 동의어 묶음(canonical + terms)으로 LLM이 엔티티·관계를 뽑는다. 결과는 Neo4j에 쌓인다.
둘째 길은 llm-wiki(kb_type=openkb 또는 jonex_wiki)다. 원문을 wiki 페이지로 컴파일한다.
[확인] 두 길은 KB 단위로 서로 배타적이다. llm-wiki KB는 파싱만 하고 LightRAG·Neo4j에 쓰지 않는다 — `capabilities/knowledge_base/services/document_service.py:681-682` "llm-wiki KB 级互斥：llm-wiki 文档只解析产出 markdown，不写 LightRAG/Neo4j".
그래서 사용자 질문("schema+용어집으로 만든 llm-wiki")에 정확히 맞는 구현은 아니다.
[확인] llm-wiki 쪽에도 사람이 정하는 schema가 하나 있다. openkb KB는 KB마다 "LLM-Wiki Schema"(엔티티 종류 통제 어휘·개념 종류·AGENTS.md 추가 규칙)를 화면·API·YAML 가져오기로 고친다 — `capabilities/knowledge_base/services/llm_wiki_schema_service.py:1`, `api_gateway/routes/knowledge_base.py:1562-1620`. 다만 이 길에는 용어집(동의어 묶음)이 없다.
그래도 그래프 쪽 길은 사용자 실험과 아주 닮았다. TBox를 프롬프트에 넣는다. 용어집을 추출 전 프롬프트와 추출 뒤 정규화에 둘 다 쓴다. 추출 뒤 이름 대조로 원문 청크 링크를 다시 채운다.
사용자 목표에 주는 답은 셋이다.
(1) 원문 연결: [확인] 문서 안에서는 이름이 나온 모든 청크로 링크를 채운다(엔티티당 최대 32개). 다만 문서를 넘어가면 엔티티 노드의 청크 링크를 마지막에 쓴 문서 것으로 덮어쓴다. 문서 목록(doc_ids)만 합집합으로 남는다.
(2) 새/기존 연결: 정확한 키로 병합한다. 키는 (entity_type, canonical_name)이다. 관계 끝점만 기존 노드의 aliases까지 대조한다. 그 aliases도 마지막 문서 것으로 덮어쓴다. 임베딩으로 같은 엔티티를 찾지는 않는다.
(3) 범용어 허브: 막는 장치가 없다. 관계 근거를 두 끝 엔티티가 함께 나온 청크로 좁히는 것과 개수 상한(32)이 부분 대책이다.

## 한 바퀴 흐름

그래프 길(kb_type=lightrag)에서 문서 하나가 Neo4j 엔티티가 되기까지의 순서다.

1. 파싱·청크: 문서를 파싱하고 LightRAG 청크 저장소에 넣는다. 청크마다 `chunk-<md5>` id가 붙는다.
2. 청크 읽기: 본체 추출 단계가 그 문서의 청크만 다시 읽는다 — `Reference/Rag-anything/raganything/service/task_manager.py:3366-3420`.
3. schema 준비: KB의 compiled schema(TBox)를 가져온다. 외부로 내보낼 때 KB 동의어 묶음을 `prompt_schema.synonyms`에 끼워 넣는다 — `capabilities/knowledge_base/services/ontology_compiler.py:273-310`, `capabilities/knowledge_base/api/__init__.py:757-761`.
4. LLM 추출: 청크를 묶음(기본 약 8개)으로 나눈다. 묶음마다 한 번 호출해 엔티티와 관계를 함께 뽑는다. 프롬프트에는 TBox 종류·별칭·속성, 대체용 거친 종류(fallback types), 관계 정의, 동의어 규칙이 들어간다 — `jonex_core/capability/atomic/rag/native_ontology_extractor.py:150-186`. 기본 2회 샘플링한 뒤 합집합을 취한다(596행). 놓친 것을 다시 묻는 gleaning을 1회 돈다.
5. 파싱 직후 정규화: 동의어 terms에 정확히 같은 이름을 canonical로 바꾼다(1343행). 종류 별칭도 TBox 종류 이름으로 바꾼다.
6. 문서 안 병합: canonical_name이 같은 엔티티를 합친다(1427행). extraction_skills를 선언한 종류는 대소문자 무시 병합(dedup_merger)과 속성 근거 검사(no_fabrication)를 거친다.
7. 청크 링크 다시 채우기: canonical_name과 LLM이 낸 aliases를 그 문서의 모든 청크 본문과 대조한다. 걸린 청크를 source_chunks에 더한다(1516-1635행).
8. 놓친 청크 재추출: 어떤 엔티티·관계도 가리키지 않는 청크를 청크 하나씩 다시 추출한다(718-768행).
9. 끝점 보충: 관계 끝점인데 엔티티로 안 뽑힌 이름을 `unknown` 종류로 만든다(772-792행).
10. TBox 검사: TBox 밖 종류의 엔티티와 관계를 그래프 저장분에서 뺀다. 빠진 것은 LightRAG 그래프(custom-kg)에만 남는다(798행, `ontology_extractor.py:415-559`).
11. 쓰기 직전 동의어 정규화: kb-service가 DB의 동의어 묶음을 다시 읽는다. canonical_name과 aliases를 대조해 canonical과 종류를 통일한다 — `reconciliation_service.py:1510-1538`, `synonym_normalizer.py`.
12. Neo4j 쓰기: 이 문서의 기존 기여를 먼저 지운다(delete_by_document). 그다음 `(tenant, kb, entity_type, canonical_name)` 키로 MERGE한다 — `ontology_graph_repository.py:150-175`. 관계 끝점은 기존 노드의 canonical → aliases 순으로 찾는다(309-420행).

llm-wiki 길(jonex_wiki)은 따로 돈다. 원문 구절을 이해(understanding)한다. 사실(record)을 페이지에 배치(organization)한다. 결정 규칙이 같은 대상이라고 증명할 때만 기존 페이지에 붙인다. 이 길에는 TBox도 용어집도 없다.

## 축별 분석

### A schema

[확인] 사람이 정한다. TBox YAML이 있고, KB 화면에서 편집하거나 업무 도메인 템플릿에서 만든다.
- 파일 형식: `deploy/config/ontology/default.yaml`(엔티티 9종, 관계 22종), `technology.yaml`(엔티티 24종), `sasseur_fashion.yaml`. 항목은 `entity_types[].{name, aliases, attributes, extraction_skills}`, `relation_types[].{name, source, target, source_types, target_types, inverse_of, cardinality}`, `disambiguation`이다.
- 출처: 편집기 저장(`save_compiled_schema`), YAML 가져오기·내보내기, 템플릿 시나리오(`_compile_from_scenario`), 기본 YAML(`ONTOLOGY_SCHEMA_FALLBACK_PATH`) — `ontology_compiler.py:25-30, 345-855`. [확인] LLM이 문서에서 schema를 제안하는 코드는 grep(`schema_suggest|infer_schema|generate_ontology` 등)으로 찾지 못했다.
- 강제 방식은 세 겹이다.
  1. 프롬프트: 종류·중국어 별칭·속성 설명(40자로 자름)을 넣는다 — `native_ontology_extractor.py:916-938`. [확인] 주석에는 "aliases 丢 → 中文实体被兜底中文粗类型池吸引、档位判出本体，P6 后 30 vs 107 的独立主因之一"이라고 적혀 있다(919-920행). 별칭이 빠지면 중국어 엔티티가 fallback 종류로 빠져 TBox 밖으로 밀린다는 관찰이다. 30 대 107이 무엇의 개수인지, 별칭만 바꾼 비교인지는 적혀 있지 않다.
  2. 구조화 출력: JSON mode다. 스키마 강제가 아니라 형식만 지정한다(`json_mode` 기본 true).
  3. 쓰기 직전 검증: `_post_validate`가 TBox 밖 엔티티 종류를 뺀다. 관계 끝점 종류가 source_types/target_types 집합에 들어가는지도 본다. inverse 이름은 정방향으로 뒤집는다 — `ontology_extractor.py:415-559`.
- [확인] 별칭 하나가 여러 종류에 걸리면 매핑하지 않고 경고만 남긴다 — `ontology_extractor.py:371` "同一别名命中多个类型 → **不映射**并记 warning".
- llm-wiki 쪽: openkb는 AGENTS.md 템플릿과 엔티티 종류 목록을 둔다. 기본 목록은 person, organization, place, product, work, event, other다. [확인] 이 목록은 고정이 아니다. KB마다 사람이 "LLM-Wiki Schema" 화면(`frontends/core-business/src/pages/DomainKnowledgeDetail/llmWikiSchema/VocabSection.tsx`)·저장 API·YAML 가져오기로 고친다(`api_gateway/routes/knowledge_base.py:1562-1620`). 저장하면 종류 code 목록이 OpenKB config의 `entity_types`로, 종류 설명과 사용자 추가 규칙이 AGENTS.md로 들어간다 — `llm_wiki_schema_service.py:102-151, 319-326`. 개념 종류 목록은 AGENTS.md 안내일 뿐 검사하지 않는다(`dtos/llm_wiki_schema.py:57-60`). 목록 밖 엔티티 종류는 조용히 other로 바꾼다 — `Reference/OpenKB/openkb/agent/compiler.py:654-673`, `dtos/llm_wiki_schema.py:6` "超出词表的 type 静默回落 other". jonex_wiki는 종류 목록이 없다. 컴파일 프롬프트 뒤에 붙일 "편집 선호" 문구만 있다 — `llm_wiki_schema_service.py:237-245`.

### B 용어집

[확인] 정식 이름과 별칭을 둔다. KB마다 동의어 묶음 표 `knowledge_base.ontology_synonyms(terms JSONB, canonical)`가 있다. canonical은 terms 안에 있어야 하고, 비우면 terms[0]이다 — `deploy/postgres/migrations/004_knowledge_base.sql:383-394`.
- 누가 쓰는가: 사람이 쓴다. 화면(`frontends/core-business/src/pages/DomainKnowledgeDetail/synonym/SynonymTab.tsx`, `SynonymImportModal.tsx`)과 CRUD·일괄 가져오기 API(`api_gateway/routes/knowledge_base.py:2157-2182`)가 있다. 한 단어가 두 묶음에 들어가면 거부한다(`ontology_synonym_service.py:131-135` "跨组重复词").
- 추출 전에도 쓰고 추출 뒤에도 쓴다.
  - 추출 전(소프트): 묶음 전체를 JSON으로 시스템 프롬프트에 넣는다 — `native_ontology_extractor.py:228-236` "实体命中某组任一词时，name 必须填该组 canonical".
  - 파싱 직후(하드, 정확 일치): `_alias_map`이 term→canonical로 바꾼다. 대소문자를 구분하는 정확 일치다 — 1297-1307, 1343행.
  - Neo4j 쓰기 직전(하드, 정규화 일치): `normalize_ont_data`가 canonical_name과 aliases를 전각→반각·casefold 키로 대조한다. 걸리면 canonical로 바꾸고, 묶음 안 엔티티들의 종류를 하나로 통일한다(canonical 단어 자신의 종류 → 최고 confidence 순) — `synonym_normalizer.py:42-117`. 원래 이름은 aliases에 남긴다.
  - [확인] 이 종류 통일은 한 문서의 추출 결과(`ont_data`) 안에서만 한다(`reconciliation_service.py:1510-1538`이 문서마다 부른다). 그래프에 이미 있는 노드의 종류는 보지 않는다. 그래서 같은 canonical이 문서 A에서 Concept, 문서 B에서 Method로 정해지면 노드가 둘로 갈린다.
- [확인] 종류까지 통일하는 이유가 코드에 적혀 있다. MERGE 키에 종류가 들어가기 때문이다 — `synonym_normalizer.py:8-10` "归并必须同时统一 canonical_name 与 entity_type，否则同名不同类仍是两个节点".
- [확인] 검색 쪽(`search_service.py`)은 동의어 표를 쓰지 않는다. grep으로 synonym이 나오지 않았다.
- [확인] TBox의 `entity_types[].aliases`는 엔티티 이름 별칭이 아니라 종류 이름의 별칭이다(예: "公司", "企业" → Organization). 사용자 실험의 용어집과 대응하는 것은 동의어 묶음 표다.

### C 원문 연결 범위

[확인] 단위는 청크다. 각 항목은 `{source_id: chunk_id, file_path}`이다. 문서 안에서는 나온 모든 청크로 채우지만, 엔티티 노드는 문서를 넘어 누적되지 않는다.
- 문서 안: LLM이 `[C번호]`로 청크를 인용하게 한다(규칙 4, 177행). 그 뒤 `_backfill_source_chunks`가 그 문서의 모든 청크를 대조한다. 걸린 청크를 합집합으로 더하고 LLM 인용은 지우지 않는다 — 1516-1600행.
  - 대조는 세 단계다. 원문에 그대로 있음 → 공백·따옴표를 지우고 있음 → 문장부호로 쪼갠 조각의 절반 이상이 있음 — `ontology_extraction_skills.py:178-216`.
  - [확인] 셋째 단계는 공백·마침표로도 쪼갠다(`_SPLIT_RE = r"[，。；、,;.\s]+"`, 2자 이상 조각만). 판정은 `sum(...) * 2 >= len(parts)`다(213행). 그래서 "CUDA Toolkit" 같은 두 단어 이름은 "CUDA"만 나온 청크에도 걸린다. 띄어쓰기 없는 중국어 이름에는 이 효과가 없다.
  - 바늘(needle)은 canonical_name과 엔티티의 aliases다. [확인] 이 시점의 aliases는 LLM이 낸 별칭뿐이다. 파싱 직후 정규화는 이름만 canonical로 바꾸고 원래 표기를 aliases에 더하지 않는다(1343-1347행). 그래서 동의어 묶음의 나머지 terms는 바늘이 되지 않는다. 사용자 실험(용어집의 모든 별칭으로 대조)보다 좁다.
  - 상한: 엔티티·관계마다 `ONTOLOGY_SOURCE_CHUNKS_MAX` 기본 32개다(1570행). 청크 순서대로 돌다가 32개에서 멈춘다. 그래서 흔한 이름은 문서 앞쪽 32개 청크만 갖는다. [확인] 상한을 둔 이유는 메모리다(1559-1569행 "17MB 文档 … 23.7GB 触发 oom-killer").
  - [확인] 이 단계를 둔 이유가 사용자 관찰과 같다 — 712-714행 "LLM 批量抽取的 chunks 引用常失真——22 chunk 仅 4 个被引用且集中于首尾".
- 관계: 두 끝 엔티티 청크 집합의 교집합을 쓴다. 교집합이 비면 합집합으로 물러난다 — 1608-1620행.
- 문서를 넘어서(Neo4j):
  - 엔티티 노드: ON MATCH에서 `e.source_chunks=$source_chunks`로 덮어쓴다 — `ontology_graph_repository.py:169`. `doc_ids`는 `apoc.coll.toSet(...)`로 합친다(168행). [확인] 그래서 문서 A와 B가 같은 엔티티를 말하면 노드에는 두 문서 id가 다 남는다. 청크 링크는 나중에 쓴 문서 것만 남는다. 의도인지 결함인지는 코드에 적혀 있지 않다.
  - [확인] ON MATCH는 `e.aliases`와 `e.attributes`도 덮어쓴다(162, 164행). 별칭도 마지막에 쓴 문서 것만 남는다.
  - 관계 엣지: source_chunks를 합집합으로 누적한다(266-272행). [확인] 다시 추출할 때 `delete_by_document`는 관계의 doc_ids에서 문서 id만 빼고 source_chunks는 건드리지 않는다(`ontology_graph_repository.py:619-668`). 그래서 문서를 다시 파싱해 청크 id가 바뀌면 옛 청크 링크가 관계에 남는다.
- llm-wiki(jonex_wiki): 사실마다 `SourceSpan(passage_id, chunk_id, start_char, end_char, text)`로 문자 구간까지 가리킨다 — `Reference/JonexWiki/src/jonex_wiki/domain/engine/models/compiler_state.py:427-446`. 페이지 사이 mention 링크는 "the first occurrence of another page's title/alias inside a page body (>= 3 chars; ASCII names require word boundaries)"다 — `mention_index.py:20-22`. 처음 나온 곳 하나만 잇는다.

### D 새/기존 연결

[확인] 정확한 키 병합이다. 순서는 다음과 같다.
1. 추출 프롬프트가 동의어 canonical을 쓰라고 시킨다.
2. 파싱 직후 term→canonical로 정확히 바꾼다.
3. 쓰기 직전 kb-service가 정규화 키(반각·casefold)로 동의어를 다시 대조하고 종류를 통일한다.
4. Neo4j `MERGE (e:OntologyEntity {tenant_id, kb_id, entity_type, canonical_name})`를 실행한다. 키가 같으면 기존 노드에 붙고, 다르면 새 노드가 된다 — `ontology_graph_repository.py:150-175`. 종류가 키에 들어가므로 이름이 같아도 종류가 다르면 다른 노드다.
5. 관계 끝점은 기존 그래프에서 찾는다. 먼저 canonical_name이 같은 정식 노드를 찾는다. 없으면 `$name IN aliases`인 노드를 찾는다. 종류 힌트가 맞는 것과 confidence가 높은 것을 고른다. 못 찾으면 stub 노드를 만든다 — 309-420행, `_resolve_endpoint` 552-580행.
- [확인] 엔티티 임베딩은 만들어 노드에 저장한다(`merge_entity` 108-130행). 이는 검색용이다. 같은 대상을 찾는 데는 쓰지 않는다.
- [확인] 엔티티 노드 자체는 기존 노드의 aliases와 대조하지 않는다. 관계 끝점만 대조한다. 그래서 동의어 표에 없는 표기 변형(예: "GPT4" 대 "GPT-4")은 노드가 둘로 갈린다.
- [확인] 끝점 대조에 쓰는 노드 aliases는 문서를 넘어 쌓이지 않는다. ON MATCH가 마지막 문서의 aliases로 덮어쓰기 때문이다(`ontology_graph_repository.py:162`). 앞 문서에서 나온 별칭으로는 끝점을 못 찾을 수 있다.
- llm-wiki(jonex_wiki)는 더 보수적이다. "a bare name match across different contexts is *undetermined* - two cities with one name are not one entity", "nothing is merged automatically" — `identity.py:10-17`. 판정 순서는 다음과 같다(`organization.py:499-538`).
  1. 같은 출처가 자기 페이지를 이어 쓴다.
  2. 이름이 가리키는 빈 페이지가 하나뿐이면 그 페이지를 쓴다.
  3. 원문이 선언한 별칭·명시 id가 있으면 같다고 본다.
  4. 선행/후속·모회사·브랜드 관계면 다르다고 본다.
  5. 나머지는 묶음당 LLM 판단 1회(후보 4개, 컴파일당 8회 상한)로 정한다. 실패하면 따로 둔다.
  - "Co-occurring names … never assert identity"(158행).

### E 새 용어

[확인] 버리지 않고 두 층으로 나눈다. 승인 대기열은 찾지 못했다.
- TBox 밖 엔티티 종류: LLM에게 fallback 종류(운영 37종, 기본 10종) 중 가장 가까운 것을 고르게 한다 — 90-107, 159-163행. 이 엔티티는 LightRAG 그래프(custom-kg)에만 들어간다. Neo4j 본체에서는 빠진다(`ONTOLOGY_KEEP_FALLBACK_ENTITIES` 기본 off).
- TBox 밖 관계: `relation_type=""`에 자유 keywords 1-4개를 단다(규칙 1, 172-174행). 역시 LightRAG에만 남는다. 선택 옵션 `ONTOLOGY_KEEP_UNTYPED_EDGES`(기본 off)를 켜면 `RELATES_TO`로 낮춰 저장한다. 이때 confidence에 0.7을 곱하고 원래 이름을 `attributes.raw_relation_type`에 남긴다 — `ontology_extractor.py:322, 498-520`. [확인] 다만 함수 주석은 "生产 true、代码默认 false"라고 적는다(`ontology_extractor.py:328`). 공개된 `deploy/docker-compose.yml`은 이 변수를 넘기지 않으므로 공개 배포 기본은 off다.
- 원문이 TBox와 전혀 안 맞을 때(가사 등): 빈 결과를 내지 말라는 "무조건 출구" 규칙 0을 둔다(168-171행). [확인] 근거 수치는 113-147행에 있다. 0/20 → 12/12다.
- 관계 끝점에만 나온 이름: `unknown` 종류 엔티티로 보충한다(789행). `_post_validate`는 `unknown`을 통과시킨다(`ontology_extractor.py:468`).
- 용어집 밖 엔티티 이름: 그 이름이 그대로 canonical_name이 된다. 동의어 표에 자동으로 추가하는 코드는 찾지 못했다(동의어 서비스는 CRUD와 가져오기뿐이다). [확인] stub 비율이 기준을 넘으면 경고 로그를 남긴다(`reconciliation_service.py` "Ontology stub entity ratio over threshold"). 사람이 볼 신호는 이것뿐이다.
- openkb: 목록 밖 엔티티 종류는 other로 바꾼다. jonex_wiki: 종류 목록이 없다.

### F 범용어 허브

[확인] 직접 막는 장치(stoplist, 문서 빈도·IDF 기준, 일반어 계층)는 찾지 못했다. grep(`stopword|停用词|idf|hub|枢纽`)으로 나온 것은 질의어 파싱의 영어 불용어 목록(`search_service.py:3164-3168`)과 쓰기 동시성 분배(`_bucket_relations`, `reconciliation_service.py:312-330`)뿐이다. 후자는 허브 노드에 동시에 쓰다 생기는 deadlock을 피하려는 것이다. 연결 품질과는 관계없다.
간접적으로 효과를 내는 것은 다음과 같다.
- 관계 근거를 두 끝이 함께 나온 청크로 좁힌다(교집합, 1619행). 허브 엔티티가 나온 청크가 모두 관계 근거가 되는 것을 막는다. 다만 교집합이 비면 합집합으로 물러나므로 막는 힘이 약하다.
- 청크 링크 상한 32(1570행). 흔한 이름의 링크 수를 묶는다. 다만 이유는 메모리이고, 앞쪽 32개를 고르는 것이라 무작위성이 없다.
- 숫자·규격 값을 엔티티로 뽑지 말라는 규칙 7(181-184행). 숫자 허브를 막는다.
- [확인] 반대로 허브를 키우는 장치도 있다. 청크 대조 셋째 단계가 여러 단어 이름의 조각 절반만 맞아도 청크를 잇는다(`ontology_extraction_skills.py:213`). 흔한 단어가 이름의 조각이면 그 이름이 많은 청크에 걸린다.
- 종류가 MERGE 키에 들어간다. 같은 "LLM"이라도 Concept와 Method로 뽑히면 노드가 갈린다. [추정] 허브를 쪼개는 효과가 있을 수 있다. 동의어 정규화는 한 문서 안에서만 종류를 통일한다. 그래서 한 문서 안에서는 용어집에 넣은 범용어가 한 노드로 모이고, 문서를 넘어서는 종류가 다르면 다시 갈린다 — 사례: `synonym_normalizer.py:52-67`과 문서별 호출(`reconciliation_service.py:1510-1538`) 하나씩.
- llm-wiki(jonex_wiki): 이름만 같으면 합치지 않는다. 출처당 링크 제안 상한은 4개다(`organization.py:85`). 이름당 후보 상한은 8개다. mention은 처음 나온 곳 하나만 잇는다. [추정] 사용자 실험의 허브 문제(용어집이 범용어를 한 이름으로 모음)를 jonex의 그래프 길은 그대로 겪을 것이다 — 사례: 동의어 대조가 빈도와 무관하게 모든 걸림을 canonical로 모으는 코드 1곳(`synonym_normalizer.py:97-117`).

### G 엔티티·이벤트

[확인] 이벤트는 TBox의 엔티티 종류 하나로 다룬다. 따로 된 시간축 모델은 없다.
- `default.yaml:58-61` Event(aliases "事件", "活动", "会议", 속성 date).
- `technology.yaml`은 Mission(launch_date, landing_date), Incident(incident_date)를 더한다. SoftwareRelease 사이 `SUPERSEDES`·`ADDED_SUPPORT_FOR`·`DEPRECATES` 관계로 버전 시간선을 만든다(헤더 주석 42-55행).
- 절차(procedural) 추출: Skill/Action을 뽑는다. step_no와 `NEXT_STEP` 관계로 순서를 매긴다 — `ontology_extraction_skills.py:406-467`. 기본 off(`ONTOLOGY_PROCEDURAL_EXTRACT_ENABLED`)다.
- 유효 기간(valid_from/to)이나 두 시간축(bitemporal)은 찾지 못했다.
- jonex_wiki의 근거 검사기는 날짜·숫자·부정·비교를 "보호 원자"로 다룬다 — `models/claim.py:1-11`. 시간을 엔티티로 뽑지는 않는다.

### H 근거 수치

[확인] 공개된 평가 보고서는 없다. CHANGELOG에 "Internal planning documents … removed from the public source tree"라고 적혀 있다(`CHANGELOG.md:20-22`). 코드가 가리키는 설계 문서(`docs/ontology/...`)는 저장소에 없다.
코드 주석에 남은 관찰 수치는 다음과 같다. 전부 내부 측정이고 재현 스크립트(`scripts/_diag_*.py`)도 공개본에 없다.

| 무엇 | 수치 | 위치 |
|---|---|---|
| LLM 청크 인용 정확도 | 청크 22개 중 4개만 인용, 앞뒤에 몰림 | `native_ontology_extractor.py:712-714` |
| 무조건 출구 규칙 0 | 도메인 밖 청크 0/20 → 12/12(평균 8.1 엔티티) | 113-147행 |
| 같은 규칙, 도메인 안 회귀 | 엔티티 평균 41.7 → 48.0(3회씩) | 134-135행 |
| temperature=0 반복 편차 | 같은 입력 4회 25/27/31/36 엔티티 | 596행 |
| P6 이후 30 대 107 차이 | 별칭 누락이 "独立主因之一"(무엇의 개수인지 미기재, 별칭만 바꾼 비교인지 불명) | 919-920행 |
| 관계 거부 분포 | no_constraint 약 77/회, endpoint_mismatch 약 60/회 | `default.yaml:157-160` |

- 용어집 정규화나 청크 다시 채우기가 연결 정밀도·재현율을 얼마나 바꾸는지 잰 수치는 없다.
- [확인] `technology.yaml` 헤더는 내부 평가 "V2 进阶测评（100 道计算/推理题）" 실패 사례로 TBox를 늘렸다고 적는다(40행). 그 평가 문서(`docs/technology-kb-retrieval-quality-rootcause-and-optimization-plan.md`)는 공개본에 없다.
- [확인] 측정 함정 경고가 있다. 상위 서버가 같은 요청 본문을 중복 제거하므로 반복 샘플링에 nonce를 붙여야 한다 — 137-142행. 사용자 실험에도 해당할 수 있다.

## 가져올 것

1. 청크 링크 다시 채우기 + 관계는 교집합: 사용자가 이미 한 "모든 청크로 링크"에 더해, 관계 근거를 두 끝이 함께 나온 청크로 좁힌다. 허브가 낳는 엉뚱한 관계 링크를 줄이는 첫 수다. 사용자 실험에서는 교집합이 빌 때 합집합으로 물러나지 않는 쪽도 함께 재 볼 만하다.
2. 용어집을 두 번 적용하되 종류도 통일: 추출 전 프롬프트(소프트) + 추출 뒤 정규화 키 대조(하드). MERGE 키에 종류가 있으면 종류 통일이 없을 때 노드가 갈린다. jonex는 문서 하나 안에서만 통일하므로, 사용자 시스템에서는 그래프에 이미 있는 노드의 종류까지 보고 맞춰야 한다.
3. TBox 밖은 버리지 않고 두 층으로: 본체 그래프에는 TBox 안 것만 넣고, 밖의 것은 fallback 종류·자유 keywords로 보조 저장소에 둔다. 사람이 나중에 TBox를 넓힐 근거가 된다. 다만 jonex에는 그것을 사람에게 보여 줄 대기열이 없다. 사용자 시스템에서는 TBox 밖 이름의 빈도 목록을 만들어 승인 대기열로 쓰는 것을 더해야 한다.
4. llm-wiki 쪽 같은 대상 판정 규칙(jonex_wiki `identity.py`): 이름만 같으면 판정을 미룬다. 원문이 선언한 별칭·id만 같다는 증거로 친다. 선행/후속·모회사 관계는 별칭이 아니다. 범용어가 한 페이지로 모이는 것을 막는 데 쓸 수 있다.
5. 피할 것: 엔티티 노드의 source_chunks와 aliases를 덮어쓰는 방식(`ontology_graph_repository.py:162, 169`). 새/기존 문서 연결이 목적이면 청크 링크와 별칭도 문서를 넘어 누적해야 한다. 조각 절반 일치로 청크를 잇는 셋째 대조 단계(`ontology_extraction_skills.py:213`)도 허브를 키우므로 그대로 가져오지 않는다.
- 라이선스 제약: 저장소 본체는 "amended version of the Apache License 2.0"이다. 상업 사용은 허용하지만, 다중 테넌트 운영과 프런트엔드 로고 제거에는 서면 허가가 필요하다. 프로젝트 소유자가 조건을 바꿀 권리를 둔다(`LICENSE` 1-20행). GitHub API는 `NOASSERTION`으로 표시한다. 같이 들어 있는 LightRAG·Rag-anything(MIT), OpenKB(Apache 2.0)는 각 원본 라이선스를 따른다(`THIRD_PARTY_NOTICES.md`). [추정] 개인 연구용으로 설계를 참고해 다시 쓰는 데는 걸림이 적다. 코드를 그대로 옮기려면 수정 Apache 조항을 지켜야 한다 — 사례: LICENSE 조항 1a·1b 둘.

## 출처

- 저장소: https://github.com/yuezhiai/jonex (stars 1342, 생성 2026-07-19, 마지막 push 2026-10-10)
- commit: `5571db5c682fb3182e968d2e9d34ef415a2638c3` (2026-10-10)
- 로컬 사본: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/yuezhiai_jonex`
- 라이선스: 수정 Apache 2.0(다중 테넌트·브랜드 조항 추가), GitHub 표시 NOASSERTION. 하위 구성요소 LightRAG/Rag-anything MIT, OpenKB Apache 2.0.
- 읽은 핵심 파일
  - `jonex_core/capability/atomic/rag/native_ontology_extractor.py` (추출 본체, 프롬프트, 청크 다시 채우기)
  - `jonex_core/capability/atomic/rag/ontology_extractor.py` (`_post_validate`, 종류 별칭)
  - `jonex_core/capability/atomic/rag/ontology_extraction_skills.py` (대조 3단계, 내장 skill)
  - `capabilities/knowledge_base/services/synonym_normalizer.py`, `ontology_synonym_service.py`, `ontology_compiler.py`, `reconciliation_service.py`
  - `capabilities/knowledge_base/repository/ontology_graph_repository.py` (MERGE, 끝점 찾기)
  - `deploy/config/ontology/{default,technology}.yaml`, `deploy/postgres/migrations/004_knowledge_base.sql`
  - `Reference/JonexWiki/src/jonex_wiki/domain/engine/compile/{identity,organization,mention_index}.py`
  - `Reference/OpenKB/openkb/agent/compiler.py`
- 남의 코드는 실행하지 않았다. 읽기만 했다.

## 검증 기록

반박 검증 에이전트가 commit `5571db5c682fb3182e968d2e9d34ef415a2638c3` 사본(`lab/repos/yuezhiai_jonex`)을 읽어 다시 확인했다. 코드는 실행하지 않았다.

확인한 것(인용한 파일:줄에 그 말이 있었다)
- schema가 사람 손에서 나오는지: `ontology_compiler.py:110-150`의 `compile_for_knowledge_base`는 템플릿 시나리오나 기본 YAML에서 TBox를 만든다. LLM을 부르지 않는다. `document_service.py:1995`의 "凭空生成 schema"도 기본 YAML로 채운다는 뜻이다. 동의어 묶음도 CRUD·가져오기뿐이고 자동 생성 코드는 grep으로 나오지 않았다.
- 동의어: `004_knowledge_base.sql:383-394` 표, `ontology_synonym_service.py:73-80`(canonical은 terms 안), 131-135(묶음 사이 중복 거부), `native_ontology_extractor.py:228-236`(프롬프트), 1297-1307·1343(대소문자 구분 정확 일치), `synonym_normalizer.py:8-10, 42-117`.
- TBox 강제: `native_ontology_extractor.py:150-186, 916-938`, `ontology_extractor.py:371, 415-559`. `default.yaml` 엔티티 9종·관계 22종을 세어 맞췄다.
- 청크 링크: `native_ontology_extractor.py:1516-1635`(32개 상한 1570, 교집합→합집합 1608-1620), `ontology_graph_repository.py:150-175`(ON MATCH `e.source_chunks=$source_chunks` 169행, doc_ids 합집합 168행), 266-272(관계 누적).
- 새/기존 연결: `ontology_graph_repository.py:309-420, 552-580`, jonex_wiki `identity.py:10-17`, `organization.py:85, 92-94, 158, 499-538`, `mention_index.py:20-22`.
- 수치: 0/20→12/12(113-147행), 41.7→48.0(135행), 25/27/31/36(596행), 22개 중 4개(712-714행), no_constraint ~77·endpoint_mismatch ~60(`default.yaml:157-160`), `CHANGELOG.md:20-22`.

고친 것
- 제목과 A·도입: "llm-wiki 쪽에서는 schema를 쓰지 않는다"를 고쳤다. openkb llm-wiki KB에는 사람이 KB마다 고치는 엔티티 종류 통제 어휘(LLM-Wiki Schema)가 있다(`llm_wiki_schema_service.py`, `api_gateway/routes/knowledge_base.py:1562-1620`). 용어집이 없다는 판단은 그대로다.
- `technology.yaml` 엔티티 수를 "약 25종"에서 24종으로 고쳤다.
- B·F: 동의어 정규화의 종류 통일이 문서 하나 안에서만 일어난다는 점을 더했다. "용어집에 넣은 범용어는 다시 한 노드로 모인다"는 문서 안으로 범위를 좁혔다.
- C·D: ON MATCH가 aliases·attributes도 덮어쓴다는 점(162, 164행)과, 다시 추출해도 관계의 옛 청크 링크가 남는다는 점(619-668행)을 더했다.
- C·F: 청크 대조 셋째 단계(조각 절반 일치, `ontology_extraction_skills.py:213`)가 여러 단어 이름의 링크를 넓혀 허브를 키울 수 있다는 점을 더했다.
- E: `ONTOLOGY_KEEP_UNTYPED_EDGES` 주석의 "生产 true" 기록을 더했다.
- H: "별칭을 프롬프트에 넣었을 때 30 vs 107"은 원문보다 강했다. 원문은 30 대 107 차이의 "独立主因之一"가 별칭 누락이라고만 적는다. 무엇의 개수인지, 별칭만 바꾼 비교인지 불명으로 고쳤다. 내부 평가 "V2 进阶测评（100 道计算/推理题）" 언급(`technology.yaml:40`)을 더했다.

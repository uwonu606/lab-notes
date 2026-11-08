# LINK-KG는 사람이 정한 엔티티 종류 7개 안에서 LLM이 문서마다 alias 사전을 키우는 구조다. 문서 사이 연결과 범용어 허브 대책은 거의 없다.

LINK-KG(arXiv 2510.26486)는 법원 판결문에서 인신밀매 네트워크 KG를 만드는 논문이다. 코드는 `dipakmeher/LinkKG-HS`에 있다. 핵심은 "type-specific Prompt Cache"다. 엔티티 종류마다 alias→canonical 이름 사전을 둔다. 이 사전은 청크를 하나 읽을 때마다 LLM이 고쳐 쓰고, 다음 청크 프롬프트에 통째로 들어간다. 끝나면 LLM이 원문을 canonical 이름으로 다시 쓴다. 그 다시 쓴 글을 GraphRAG 0.3.2가 KG로 만든다.

사용자 목표에 주는 답은 셋이다.
- [확인] 사람이 하는 몫은 엔티티 종류 7개와 그 정의, 그리고 "법률·정부 용어는 뽑지 마라"는 금지 목록이다. 용어집 자체는 사람이 쓰지 않는다. LLM이 문서 하나 안에서 만든다(`linkkg/loopcoref.py:150`에서 빈 dict로 시작).
- [확인] 새 문서와 기존 문서의 연결은 설계에 없다. 캐시는 문서·종류마다 새로 만들어진다(`linkkg/run_pipeline.py:172`). 문서 사이를 이을 수 있는 것은 GraphRAG의 이름 일치 병합뿐이다. 논문은 이것을 "exact string and type matches"라고 적는다(III-B). [확인] 하지만 GraphRAG 0.3.2 코드의 병합 키는 대문자로 바꾼 이름 하나다. 종류는 키에 들어가지 않는다(D 참고).
- [확인] 범용어를 노드로 만들지 않게 막는 장치는 프롬프트 안의 고정 금지 목록(court, jury, government …) 하나다. 빈도나 차수(degree)를 보는 장치는 없다. "애매한 명사구는 null" 규칙은 coref 캐시에서 잘못된 병합을 막을 뿐이다. 그 명사구는 원문에 그대로 남고, KG 추출 단계가 다시 뽑을 수 있다(F 참고). [확인] 오히려 PERSON 정의와 few-shot 예시가 `SMUGGLER` 같은 역할 일반명을 PERSON 노드로 뽑게 가르친다(`entity_extraction.txt:10`, `:66`, `:84`, `:112`). [추정] 사용자가 본 허브 문제를 역할어에서 그대로 만들 구조다 — 사례: 위 정의 1곳과 예시 3개.

## 한 바퀴 흐름

문서 하나를 엔티티 종류 하나에 대해 돌리는 단위가 기본이다. 종류 7개를 차례로 돌린다(논문 Fig. 1: "repeated sequentially for each entity type").

| 단계 | 하는 일 | 입력 → 출력 | 근거 |
|---|---|---|---|
| 0 chunk | 문단 경계로 자르고 토큰 상한(README 예시 300)까지 묶는다 | 원문 → `chunk_NN.txt` | `linkkg/chunk.py:17-51` |
| 1 NER | 종류별 프롬프트로 PROPER_NOUN, NOUN_PHRASE, 설명을 JSON으로 뽑는다. 청크마다 독립 | 청크 → `ENTITIES`, `PROPER_NOUN_DESCRIPTION` | `linkkg/ner.py:87`, `prompts/person_nopr_ner_prompt.txt:24-34` |
| 2 Prompt Cache | 지금까지의 캐시 + 이 청크의 NER 결과 + 청크 원문을 Mapping-LLM에 준다. 돌려받은 매핑을 캐시에 덮어쓴다. 선택적으로 같은 과정을 다시 돈다(gleaning). 논문은 "optional second pass"라 하고, 코드는 `--verify-passes` 횟수만큼(기본 0) 돈다 | → `final_memory.json` (`RESOLVED_ENTITIES`, `AUXILIARY_DESCRIPTIONS`) | `linkkg/loopcoref.py:42-50`, `:108-109`, `:155-157` |
| 3 resolve | null 매핑을 버리고 남은 캐시로 Resolve-LLM이 청크를 다시 쓴다. 청크들을 이어 붙인다 | → `<type>_resolved_<doc>.txt` | `linkkg/resolve_coref.py:74`, `:120` |
| 4 KG | 다시 쓴 글을 GraphRAG 0.3.2가 300토큰(overlap 100) 청크로 잘라 엔티티·관계 튜플을 뽑는다. 같은 이름(대문자 변환 후)은 병합한다 | → GraphRAG entities/relationships | `linkkg/kgconstruction/ragtest/settings.yaml:58`, `:92`, 논문 III-B, graphrag 0.3.2 `graph_extractor.py:208-238` |

[확인] 종류 7개를 잇는 드라이버 스크립트는 저장소에 없다. `run_pipeline.py`는 `--entity-type` 하나만 받는다(`run_pipeline.py:141`). README는 저장소에 없는 `run_pipeline5.py`를 부른다(README.md:23). [추정] 앞 종류의 출력 파일을 사람이 다음 종류의 `--input-file`로 넘겼을 것이다 — 근거는 Fig. 1 설명 한 곳뿐이다.

## 축별 분석

### A schema

[확인] 연구자가 정한다. 엔티티 종류는 7개다: PERSON, LOCATION, ORGANIZATION, MEANS_OF_TRANSPORTATION, MEANS_OF_COMMUNICATION, ROUTES, SMUGGLED_ITEMS(논문 III, `settings.yaml:92`). 관계 종류는 없다. 관계는 자유 서술문과 0~10 strength 점수다(`entity_extraction.txt:38-45`). 페이지 종류 개념도 없다.

[확인] 형식은 두 군데다. 종류 이름 목록은 GraphRAG `settings.yaml`의 `entity_types`에 있다. 종류 정의와 예시는 추출 프롬프트 본문에 있다(`entity_extraction.txt:8-16`). coref 단계는 종류마다 프롬프트 파일 3개(ner/coref/resolve)를 따로 둔다. 모두 21개다(`linkkg/prompts/`).

[확인] 강제는 프롬프트 지시뿐이다. "Do NOT infer or create new entity types. If a term does not fit any defined entity type, do NOT extract it."(`entity_extraction.txt:9`).

[확인] 코드가 검사하는 것은 JSON 모양뿐이다. NER은 `{`로 시작하고 파싱되는지 보고, 실패하면 형식 경고를 붙여 재시도한다(`ner.py:20-44`, `:93-135`). coref는 `RESOLVED_ENTITIES`와 `AUXILIARY_DESCRIPTIONS` 키가 있는지만 본다(`loopcoref.py:22-23`).

[확인] 뽑힌 종류가 7개 안에 드는지 쓰기 직전에 검사하는 코드는 찾지 못했다. `linkkg/` 전체와 `kgconstruction/*.py`를 읽었다. `kgconstruction/monkey_patch.py`는 임베딩 호출만 바꾼다. [확인] GraphRAG 0.3.2도 검사하지 않는다. 튜플의 종류 문자열을 대문자로 바꿔 그대로 노드에 넣는다(graphrag 0.3.2 wheel `graphrag/index/graph/extractors/graph/graph_extractor.py:208-209`).

### B 용어집

[확인] 정식 이름+별칭 구조는 있다. 다만 사람이 쓰는 용어집이 아니라 LLM이 문서 안에서 키우는 캐시다. `RESOLVED_ENTITIES`는 alias→canonical dict다. `AUXILIARY_DESCRIPTIONS`는 canonical→한 줄 설명이다(`person_nopr_coref_prompt.txt:44-71` 예시). 정식 이름 규칙은 프롬프트가 정한다: "always use the full name as the canonical reference"(`:36`).

[확인] 추출 전에 들어간다. 캐시는 매 청크 Mapping-LLM 프롬프트에 JSON으로 통째로 붙는다(`loopcoref.py:42-50`). 그다음 Resolve-LLM이 원문의 alias를 canonical 이름으로 바꿔 쓴다(`person_nopr_resolve_prompt.txt:9-18`). KG 추출은 이렇게 정규화된 글에서 돈다. 추출 뒤 정규화는 GraphRAG의 정확 일치 병합뿐이다. 사용자 실험(추출 프롬프트에 용어집 + 추출 뒤 정규화)과 달리, 정규화가 원문 다시 쓰기로 추출 앞에 온다.

[확인] 캐시를 종류별로 나눈 이유는 맥락 길이다. "keeping token usage low in the LLM's context window"(논문 II-B). LLMLINK의 캐시가 커지는 문제를 피하려 했다.

[확인] 같은 alias가 다른 대상을 가리키면 앞뒤 한두 단어를 붙여 새 alias를 만든다. 예는 "the agent from Checkpoint A" vs "the agent from Checkpoint B"다(논문 III-A2, `person_nopr_coref_prompt.txt:38`).

### C 원문 연결 범위

[확인] coref 캐시는 원문 위치를 갖지 않는다. alias와 canonical 이름, 설명만 있다(`loopcoref.py:117-122`의 `final_memory.json` 구조). 청크 번호도, 오프셋도 저장하지 않는다.

[확인] KG 단계의 엔티티는 이름이 뽑힌 모든 GraphRAG text unit(300토큰)을 가리킨다. GraphRAG 0.3.2는 같은 이름이 다시 나오면 `source_id`에 text unit id를 더한다(`graph_extractor.py:224-229`). text unit 사이 병합도 `source_id`를 `concat`, `distinct: True`로 모은다(`graphrag/index/workflows/v1/create_base_extracted_entities.py:58-62`). 최종 엔티티에서 이 값이 `text_unit_ids`가 된다(`create_final_entities.py:78`). 모두 PyPI의 graphrag-0.3.2 wheel에서 읽었다.

[확인] 가리키는 대상은 원문이 아니라 LLM이 다시 쓴 글이다. Resolve-LLM 출력이 그대로 GraphRAG 입력이 된다(`resolve_coref.py:103-117`). 청크 단위 짝은 디스크에 남는다. 원문 청크 `chunk_NN.txt`와 다시 쓴 `chunk_NN_resolved.txt`가 같은 번호를 쓴다(`chunk.py:89`, `resolve_coref.py:114`). 하지만 이 짝은 합친 파일에서 사라진다. 청크들은 빈 줄로 이어 붙여지고(`resolve_coref.py:128-132`), GraphRAG가 그 글을 300토큰·overlap 100으로 다시 자른다. 그래서 KG의 text unit은 원래 청크 경계와 맞지 않는다. 오프셋 대응표는 어디에도 없다. 원문 문장까지 거슬러 갈 길이 끊긴다.

[추정] 사용자가 겪은 "처음 본 청크에만 링크" 문제는 생기기 어렵다. 다시 쓰기가 모든 언급을 canonical 이름으로 바꾸기 때문이다. 그러면 각 청크 추출에서 같은 이름이 나오고, GraphRAG가 그 청크들을 모두 모은다. 실행해 보지는 않았다.

### D 새/기존 연결

[확인] 문서 안에서는 LLM 판단으로 잇는다. Mapping-LLM 프롬프트 1단계는 "If the entity clearly refers to the same individual as one of the resolved entities, link it"이다(`person_nopr_coref_prompt.txt:11-12`). 설명문(`AUXILIARY_DESCRIPTIONS`)이 판단 재료다. 별칭 문자열 대조나 임베딩 비교 코드는 없다. 임베딩 모델(nomic-embed-text)은 설정되어 있지만 "embeddings are unused in our pipeline"(논문 IV-B).

[확인] 문서 사이에서는 잇는 절차가 없다. 캐시는 실행마다 빈 dict에서 시작한다(`loopcoref.py:150`). 출력 폴더도 `output/<문서>/<종류>`로 문서마다 갈린다(`run_pipeline.py:172`). 이전 문서의 `final_memory.json`을 읽어 오는 코드는 없다. GraphRAG 단계의 이름 병합만 남는다. 논문은 이것을 "merging entities with exact string and type matches"라고 쓴다(III-B).

[확인] 코드의 병합 키는 논문 설명과 다르다. GraphRAG 0.3.2는 엔티티 이름을 `upper()`한 문자열을 노드 id로 쓴다(`graph_extractor.py:208`, `:212`). text unit 사이 병합도 노드 id만 비교한다(`graphrag/index/verbs/graph/merge/merge_graphs.py:115-119`). 종류는 키가 아니다. 같은 이름이 다른 종류로 나오면 노드 하나로 합쳐진다. 노드의 `type` 값은 처음 들어온 것이 남는다. 같은 text unit 안에서 다시 나온 종류는 `type`이 아니라 다른 속성 `entity_type`에 쓰인다(`graph_extractor.py:230-231`, `:234-238`). text unit 사이 병합 연산에도 `type`이 없다(`merge_graphs.py:139-156`). 따라서 두 문서가 같은 사람을 같은 full name으로 쓰면 대소문자가 달라도 이어진다. 철자가 하나만 달라도 갈린다. 이 병합이 문서 사이에 작동하려면 두 문서가 같은 GraphRAG `input/`에 함께 들어가야 한다. 논문은 문서마다 따로 그래프를 만들었다.

[확인] 평가도 문서 하나 단위다. 16개 판결문을 각각 그래프로 만들고 문서별 중복률을 쟀다(Table I, II). 문서 사이 연결을 잰 수치는 없다.

### E 새 용어

| 상황 | 처리 | 근거 |
|---|---|---|
| 캐시에 없는 고유명사 | 자동으로 새 canonical 항목을 만든다("singleton") | `person_nopr_coref_prompt.txt:14-16` |
| 캐시에 없는 일반 명사구, 너무 애매한 것 | null로 매핑한다 → resolve 전에 캐시에서 지운다. 원문의 그 명사구는 바뀌지 않고 남는다. KG 추출이 그것을 다시 엔티티로 뽑을 수 있다 | 같은 파일 `:18-19`, `resolve_coref.py:69-74`, `person_nopr_resolve_prompt.txt:18`, `:26` |
| 이름을 모두 나열하지 않은 복수 명사구("the passengers") | null | 같은 파일 `:21-27` |
| 7종류 밖 대상 | KG 추출에서 뽑지 않는다(프롬프트 지시) | `entity_extraction.txt:9` |

[확인] 사람 승인 대기열은 없다. null 매핑은 로그에 이름만 남는다(`resolve_coref.py:69-71`). 이 로그를 사람이 검토하는 절차는 논문에도 없다.

[확인] null은 "버린다"가 아니라 "바꾸지 않는다"다. Resolve-LLM은 캐시에 있는 alias만 바꾸고 나머지 글은 그대로 두라는 지시를 받는다("Do not create or guess new names", `person_nopr_resolve_prompt.txt:18`; "return the paragraph unchanged", `:26`). 그래서 "the officer" 같은 명사구는 다시 쓴 글에도 남는다. 그다음 KG 추출 프롬프트의 PERSON 정의가 "Smugglers, undocumented non citizens, border patrol agents, etc. are also examples of a PERSON entity"라고 말한다(`entity_extraction.txt:10`).

### F 범용어 허브

[확인] 노드 생성을 막는 장치는 하나다. 프롬프트 안의 고정 금지 목록이다: "Do NOT extract entities corresponding to governmental organizations … such as jury, government, law_enforcement, homeland_security, court, district court, juror, verdict …"(`entity_extraction.txt:5`). 같은 지시를 단계 1 끝(`:25`)과 단계 3(`:47`)에서 되풀이한다. 논문은 이것을 "Filtering High-Frequency Irrelevant Entities"라고 부른다(III-B).

[확인] E의 null 규칙은 허브 대책이 아니다. "the officer" 같은 애매한 역할 명사구를 엉뚱한 canonical 이름에 붙이지 않게 할 뿐이다. 그 명사구는 원문에 남는다. KG 추출 단계는 역할 일반명을 PERSON으로 뽑으라고 배운다(아래). 그래서 null 규칙은 잘못된 병합을 줄인다. 역할어 노드가 생기는 것은 막지 못한다.

[확인] 빈도·차수 기준이나 계층은 없다. 금지 목록은 도메인 무관성(법률 절차어)으로 고른 고정 목록이다. LLM이 지키는지 코드가 확인하지 않는다. 논문 평가에서도 LINK-KG의 노이즈 노드가 평균 12.28%(짧은 문서), 17.57%(긴 문서) 남는다(Table I, II).

[확인] LINK-KG의 KG 추출 프롬프트는 이전 논문 CORE-KG의 것과 같다. `diff baseline/core-kg/kgconstruction/ragtest/prompts/entity_extraction.txt linkkg/kgconstruction/ragtest/prompts/entity_extraction.txt`는 끝의 빈 줄 8개만 다르다. 그래서 금지 목록은 LINK-KG가 CORE-KG보다 나아진 이유가 아니다. 논문도 CORE-KG 대비 노이즈 감소를 coref 덕으로 설명한다: "once references are resolved and unified, LLM attention becomes more focused"(V-B).

[확인] 정의와 few-shot 예시가 역할 일반명 노드를 만든다. PERSON 정의는 "Smugglers ... border patrol agents"를 PERSON의 예로 든다(`entity_extraction.txt:10`). 예시 1과 3은 `SMUGGLER`를 PERSON 엔티티로 뽑고, 실명 인물과 "identified as a smuggler" 관계로 잇는다(`entity_extraction.txt:66`, `:70`, `:112`, `:124`). 예시 2는 `SMUGGLERS`를 PERSON으로 뽑고 관계 3개의 중심에 둔다(`:84`, `:92-96`). [추정] 판결문 하나에 밀수범이 여럿이면 `SMUGGLER`가 그들 모두를 잇는 허브가 된다 — 사례: 정의 1곳과 예시 3개. 실제 그래프에서 차수를 보면 알 수 있다.

### G 엔티티·이벤트

[확인] 이벤트와 시간축은 뽑지 않는다. 논문 III은 "identify actors, events, and contextual entities"라고 쓰지만 7종류에 이벤트가 없다. 관계 튜플에도 시간 칸이 없다(`entity_extraction.txt:45`).

[확인] 날짜를 담는 GraphRAG claim extraction 프롬프트는 저장소에 있다("Claim Date" `claim_extraction.txt:17`, `claim_start_date`·`claim_end_date` `:20`). 하지만 설정에서 `#enabled: true`가 주석 처리되어 있다(`settings.yaml:106`). [확인] 그러면 0.3.2에서는 꺼진다. 0.3.2 기본값이 `CLAIM_EXTRACTION_ENABLED = False`다(graphrag 0.3.2 wheel `graphrag/config/defaults.py:55`). 설정을 읽는 쪽은 `reader.bool(Fragment.enabled) or defs.CLAIM_EXTRACTION_ENABLED`다(`create_graphrag_config.py:445`). 결론(VI)은 "temporal analysis, and event prediction"을 다음 활용처로만 든다.

### H 근거 수치

[확인] 판결문 16건(짧은 7, 긴 9)에 Llama 3.3 70B, temperature 0으로 잰 값이다(논문 IV-A, IV-B). 정답 그래프는 없다. 중복은 RapidFuzz `partial_ratio` ≥75%로 후보를 묶고 전문가가 고쳤다. 노이즈는 전문가가 절차·상투 용어를 골랐다(IV-D).

| 지표(평균) | GraphRAG | CORE-KG | LINK-KG |
|---|---|---|---|
| 노드 수, 짧은 문서 | 69.57 | 36.43 | 34.71 |
| 노드 수, 긴 문서 | 143.56 | 59.89 | 58.44 |
| 중복률, 짧은 | 27.02% | 17.00% | 10.61% |
| 중복률, 긴 | 36.01% | 26.10% | 17.78% |
| 노이즈율, 짧은 | 23.59% | 12.41% | 12.28% |
| 노이즈율, 긴 | 40.71% | 22.82% | 17.57% |

[확인] 초록의 "45.21%"와 "32.22%"는 두 기준선 대비 상대 감소율을 문서 길이별로 평균하고 다시 평균한 값이다(V-A, V-B). README는 49.16%와 41.25%라고 적는다. 이 둘은 논문에서 중복 감소율의 짧은/긴 문서 값이다. README가 노이즈 수치 자리에 중복 수치를 잘못 넣었다.

[확인] 빠진 것이 있다. 재현율이나 관계 정확도는 재지 않았다. 캐시와 금지 목록을 따로 끈 ablation도 없다. 검색·질의응답 성능도 재지 않았다. 논문도 CORE-KG의 낮은 노드 수가 "may also limit recall"이라고 인정한다(V-A).

## 가져올 것

| 무엇 | 사용자 시스템에서의 자리 | 조건 |
|---|---|---|
| 종류별 alias 캐시를 매 청크 프롬프트에 넣기 | 사람이 쓴 용어집 150개를 통째로 넣는 대신, 종류별로 잘라 넣는다. 맥락이 짧아진다 | 사람 용어집을 시드로 두고 LLM 추가분은 따로 표시해야 E가 통제된다 |
| canonical 설명(`AUXILIARY_DESCRIPTIONS`)으로 동명이인 가르기 | 용어집 항목마다 한 줄 정의를 두고 연결 판단에 쓴다 | — |
| 애매한 일반 명사구는 null, 복수는 전원 명시일 때만 | 용어집 연결 단계에서 일반어를 엉뚱한 항목에 붙이지 않는 규칙 | LINK-KG에서 이 규칙은 노드 생성을 막지 않는다(F). 허브 대책으로 쓰려면 추출 단계에서 null된 말을 노드로 만들지 않는 규칙을 따로 둬야 한다. 또 "KG", "LLM" 같은 사용자 범용어는 고유명사처럼 보여서 이 규칙에 안 걸린다. 금지 목록이나 빈도 기준을 함께 둬야 한다 |
| 같은 alias가 다른 대상이면 앞뒤 단어를 붙인 새 alias | 용어집의 다의어 처리 | — |
| 원문 다시 쓰기 후 추출 | 가져오지 않는 편이 낫다 | 원문 위치가 끊긴다(C). 사용자 목표인 "raw들을 연결할 수 있는 구조"와 부딪힌다 |

[확인] 저장소에 LICENSE 파일이 없고 GitHub API의 license 값도 null이다. 그래서 코드와 프롬프트 문장을 그대로 복사할 권리가 없다. 아이디어만 가져오고 프롬프트는 새로 써야 한다. 논문 본문은 CC BY 4.0이다(arXiv HTML 머리말). 출처 표시를 하면 인용할 수 있다.

## 출처

| 항목 | 값 |
|---|---|
| 논문 | https://arxiv.org/abs/2510.26486 (v1, 2025-10-30, CC BY 4.0). HTML 본문 https://arxiv.org/html/2510.26486 를 읽었다 |
| 코드 | https://github.com/dipakmeher/LinkKG-HS |
| commit | `89b40423fb911fc170c55d048d739bd5ecd6ef03` (2026-05-29) |
| 로컬 사본 | `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/dipakmeher_LinkKG-HS` |
| 라이선스 | 저장소: 없음(LICENSE 파일 없음, GitHub API `license: null`) |
| 비교에 쓴 GraphRAG | PyPI `graphrag-0.3.2-py3-none-any.whl` (LINK-KG가 쓴 판. 검증 때 읽음). 처음 작성 때는 `microsoft_graphrag@5faaaf4`(현재판)를 읽었다 |
| 읽은 파일 | `linkkg/*.py` 전체, `linkkg/prompts/person_*`, `org_nopr_*`, `kgconstruction/ragtest/settings.yaml`, `prompts/entity_extraction.txt`, `claim_extraction.txt`, `kgconstruction/*.py`, `baseline/*/entity_extraction.txt`(diff) |

## 검증 기록

2026-10-11에 반박 검증 에이전트가 주장을 다시 확인했다. 저장소는 `89b4042`(GitHub API로 main HEAD와 같음을 확인)에서 읽기만 했다. 논문은 arXiv HTML v1을 받아 읽었다. GraphRAG 0.3.2는 PyPI wheel을 스크래치 디렉터리에 풀어 읽었다.

### 그대로 맞은 것

| 주장 | 다시 본 곳 |
|---|---|
| 엔티티 종류 7개를 연구자가 정한다. 사람이 정한 schema가 있다 | `settings.yaml:92`, `entity_extraction.txt:8-16`, 논문 III |
| 용어집(alias 캐시)은 사람이 아니라 LLM이 문서마다 빈 dict에서 키운다. 부풀림 없음 | `loopcoref.py:150-151`, `:108-109`, `:42-50` |
| 프롬프트 지시 인용, 금지 목록 위치 | `entity_extraction.txt:5`, `:9`, `:25`, `:47` |
| 코드는 JSON 모양만 검사한다 | `ner.py:20-44`, `loopcoref.py:22-23` |
| 출력 폴더가 문서·종류마다 갈린다, 종류 하나만 받는다 | `run_pipeline.py:141`, `:172` |
| CORE-KG와 KG 추출 프롬프트가 같다 | diff 결과: 끝의 빈 줄 8개만 다름 |
| 프롬프트 파일 21개 | `ls linkkg/prompts \| wc -l` |
| 논문 인용 문장들 | II-B "keeping token usage low", III-A2 Checkpoint 예, III-B "exact string and type matches", IV-B "embeddings are unused", V-B "more focused", Fig. 1 "repeated sequentially" |
| 수치 전부 | Table I·II 평균 행(노드 수, 중복률, 노이즈율), V-A 49.16/41.25→45.21, V-B 24.51/39.91→32.22, IV-A 16건(7+9), IV-B temperature 0 |
| README 수치 오기 | README.md:5의 49.16/41.25는 V-A의 중복 감소율 짧은/긴 문서 값이다 |
| 라이선스 | GitHub API `license` null, 논문 HTML 머리말 "License: CC BY 4.0" |

### 고친 것

| 축 | 고치기 전 | 고친 뒤 | 근거 |
|---|---|---|---|
| E, F, 가져올 것 | null 매핑된 명사구는 "버려진다". 그래서 null 규칙이 범용어 허브 대책의 하나다 | null은 캐시에서만 지운다. 원문의 그 명사구는 다시 쓴 글에 남는다. KG 추출이 다시 뽑을 수 있다. null 규칙은 잘못된 병합을 막을 뿐, 역할어 노드를 막지 못한다 | `resolve_coref.py:74`, `person_nopr_resolve_prompt.txt:18`, `:26`, `entity_extraction.txt:10` |
| F | 역할어 노드를 가르치는 근거가 예시 2개 | PERSON 정의 1곳과 예시 3개(예시 2의 `SMUGGLERS` 추가). 맺음말 라벨을 [추정]으로 바꿈 | `entity_extraction.txt:10`, `:84`, `:92-96` |
| D, 머리말 | GraphRAG가 이름과 종류가 같을 때 병합한다 | 0.3.2 코드의 키는 대문자로 바꾼 이름뿐이다. 종류가 달라도 합쳐지고, 처음 `type`이 남는다. 논문 III-B 설명과 코드가 다르다 | graphrag 0.3.2 `graph_extractor.py:208-212`, `:230-238`, `merge_graphs.py:115-119`, `:139-156` |
| C | GraphRAG가 모든 text unit을 모은다는 것은 현재판 1곳 근거의 [추정] | 0.3.2에서 확인함. [확인]으로 올림 | `graph_extractor.py:224-229`, `create_base_extracted_entities.py:58-62`, `create_final_entities.py:78` |
| C | 다시 쓴 글과 원문 사이 대응표는 남지 않는다 | 청크 번호 짝(`chunk_NN.txt` ↔ `chunk_NN_resolved.txt`)은 디스크에 남는다. 합친 파일과 GraphRAG 재분할에서 그 경계가 사라진다. 오프셋 대응표는 없다 | `chunk.py:89`, `resolve_coref.py:114`, `:128-132`, `settings.yaml:58-59` |
| G | claim extraction이 꺼졌다는 것은 현재판 기본값 근거의 [추정] | 0.3.2 기본값 False를 확인함. [확인]으로 올림. 날짜 칸 줄 번호를 :17(Claim Date)과 :20(`claim_start_date`)로 나눔 | graphrag 0.3.2 `config/defaults.py:55`, `create_graphrag_config.py:445` |
| A | 종류 검증 코드가 없다(저장소 범위) | GraphRAG 0.3.2도 종류 문자열을 검사 없이 넣는다는 것을 더함 | `graph_extractor.py:208-209` |
| 흐름 표 | gleaning을 "한 번 더" 돈다 | 논문은 "optional second pass", 코드는 `--verify-passes` 횟수(기본 0)만큼 | `loopcoref.py:134`, `:155-157` |
| 흐름 | — | README가 저장소에 없는 `run_pipeline5.py`를 부른다는 것을 더함 | README.md:23 |

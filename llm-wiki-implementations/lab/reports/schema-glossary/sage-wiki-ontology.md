# sage-wiki는 schema를 사람이 config로 정하고 쓰기 직전에 강제하지만, 용어집은 사람이 쓰지 않고 LLM이 만든 별칭을 사람이 승인·되돌리는 구조다

sage-wiki(xoai/sage-wiki)는 Karpathy식 llm-wiki를 Go 바이너리 하나로 구현한 저장소다. raw 문서를 summary → concept 추출 → 문서 작성 순서로 컴파일한다. 여기에 opt-in 그래프 패스(triple 추출, entity resolution)를 붙여 근거 있는 지식 그래프를 만든다.
사용자 목표("사람이 어느 정도 하더라도 raw를 잇고 새/기존 연결고리를 발견하는 구조")에 주는 답은 셋이다.
첫째, schema 강제 방식은 그대로 가져올 만하다. 사람이 `config.yaml`에 엔티티 종류·관계 종류·관계 동의어를 적는다. 프롬프트에 어휘 목록을 넣는다. JSON schema에는 enum을 걸지 않는다. 쓰기 직전에 Go 코드가 어휘 밖 값을 노드·엣지 하나 단위로 버리거나 `concept`로 바꾼다.
둘째, 사람이 쓰는 용어집(정식 이름+별칭 목록)은 없다. 별칭은 LLM이 concept 추출 때 만들거나 entity resolution이 제안한다. 사람의 역할은 제안을 승인·거절·`--unlink`하는 것이다.
셋째, 사용자 실험에서 문제가 된 범용어 허브에 대해서는 장치가 흩어져 있다. resolution 후보 묶기에서 흔한 토큰을 빼는 `max_token_df`, 검색 점수의 Adamic-Adar(1/log degree), 관련 문서 링크 8개 상한이 있다. 다만 그래프에 허브 노드가 생기는 것 자체를 막는 stoplist는 없다.

## 한 바퀴 흐름

문서 하나 `raw/a.md`가 들어가서 페이지·엔티티가 되기까지다. 파일:줄은 저장소 루트 기준이다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| Pass 0 diff | 바뀐 source만 고른다 | `internal/compiler/pipeline.go:324` |
| Pass 1 summarize | raw 원문을 읽고 `wiki/summaries/a.md`를 쓴다 | `internal/compiler/fullpipeline.go:149` |
| Pass 2 concept 추출 | summary(앞 1000자)와 기존 concept 이름 목록을 프롬프트에 넣는다. LLM이 `{name, aliases, sources, type}` 배열을 structured output으로 낸다 | `internal/compiler/concepts.go:124, 176-212`, `internal/prompts/templates/extract_concepts.txt:5-20` |
| 정규화 | 소문자+trim 이름 일치, 별칭 겹침(양방향)으로 접는다. 더 긴 이름이 정식 이름이 된다 | `internal/compiler/concepts.go:318-470` |
| dedup | 임베딩 cosine ≥ 0.85면 기존 concept에 합친다(이름이 완전히 같은 것은 건너뛴다). `dedup_strategy: llm`이면 대신 LLM이 keep/fold/drop을 고른다 | `internal/compiler/fullpipeline.go:318-358`, `internal/compiler/dedup.go:145,162`, `internal/compiler/curate.go` |
| evidence gate | source가 `min_concept_sources`(기본 1)보다 적은 concept은 버린다 | `internal/compiler/evidence_gate.go:13-28` |
| Pass 2b triple 추출(opt-in) | summary 하나당 LLM 1회. 엔티티(이름·종류·한 문장 설명)와 관계(술어·evidence·confidence)를 낸다. Go가 어휘 검증 후 저장한다 | `internal/compiler/extract_triples.go:614-841` |
| Pass 3 문서 작성 | concept마다 raw 원문에서 이름·별칭이 걸리는 절을 뽑아 문서를 쓴다. entity 행, `cites` 엣지(concept→source 문서), 키워드 근접 관계 엣지를 만든다 | `internal/compiler/write.go:212-250, 336-385, 861-910` |
| Pass 4 resolution(opt-in) | 이번 컴파일이 건드린 엔티티를 씨앗으로 후보를 묶는다. LLM이 같은 대상인지 판정한다. 0.85 이상이면 alias→canonical 링크를 걸고, 아니면 검토 대기열에 넣는다 | `internal/compiler/resolve_entities.go:614-790` |
| 이후 | temporal supersession sweep, community 탐지(opt-in) | `internal/compiler/fullpipeline.go:418-430` |

## 축별 분석

### A schema

[확인] 사람이 `config.yaml`의 `ontology.entity_types`, `ontology.relation_types`에 정한다. 근거: `internal/config/config.go:841-850`의 `OntologyConfig`가 `Relations`, `RelationTypes`, `EntityTypes`를 갖는다. 관계 하나는 `name`, `synonyms`, `valid_sources`, `valid_targets`, `functional`을 갖는다(`config.go:1030-1040`).
[확인] 내장 어휘는 지울 수 없고, config는 덧붙이기만 한다. 엔티티 종류 내장 5개는 concept·technique·source·claim·artifact다(`internal/ontology/entities.go:12-18`). 관계 내장 8개는 implements·extends·optimizes·contradicts·cites·prerequisite_of·trades_off·derived_from다(`docs/guides/configurable-relations.md:28-39`). 도메인 묶음은 pack으로 배포한다(`internal/pack/bundled/meeting-organizer/pack.yaml:14-30`).
[확인] 강제는 세 겹이다.
1. 프롬프트: triple 프롬프트에 `type: one of {{.ValidTypes}}`, `predicate: one of {{.ValidPredicates}}`가 들어간다(`internal/prompts/templates/extract_triples.txt:16,27`). 엔티티 종류 설명문은 들어가지 않고 이름만 들어간다(`extract_triples.go:131-135`).
2. 구조화 출력: JSON schema는 필드 모양만 강제한다. enum은 일부러 뺐다. 코드 주석이 이유를 적는다. "an enum violation fails the WHOLE call — so one hallucinated predicate would cost the document's entire graph instead of one edge"(`extract_triples.go:54-63`).
3. 쓰기 직전 검증: `normalizeGraph`가 모르는 엔티티 종류를 `concept`로 바꾸고, 술어를 이름→동의어 순으로 대조해 안 맞으면 엣지를 버린다(`extract_triples.go:175-314`). 저장소 층에서도 `AddEntity`·`AddRelation`이 어휘 밖 값을 거부한다(`internal/ontology/ontology.go:153-155, 308-309`).
[확인] 키워드 경로(Pass 3)는 LLM 없이 schema를 쓴다. 문서 안 `[[wikilink]]`와 관계 동의어가 같은 문단에 있으면 엣지를 만든다. `valid_sources`/`valid_targets`로 엔티티 종류를 거른다(`write.go:861-910`).
[확인] 페이지 종류는 schema로 정하지 않는다. concept 문서 하나(`wiki/concepts/<name>.md`)와 summary가 전부다. frontmatter에 `entity_type`이 들어간다(`write.go:479`).

### B 용어집

[확인] 사람이 쓰는 정식 이름+별칭 파일은 없다. 관계 동의어(`synonyms`)만 사람이 쓴다. 이것은 술어 대조용이고 엔티티 이름용이 아니다(`configurable-relations.md:43-55`).
[확인] 엔티티 별칭은 두 곳에 산다.
- manifest concept의 `Aliases`: Pass 2에서 LLM이 낸다. 정규화·dedup이 진 쪽 이름을 별칭으로 붙인다(`concepts.go:368`, `internal/manifest/manifest.go:220-237`).
- entity alias 표: resolution이 제안하고 사람이 `--apply`/`--reject`/`--unlink`로 결정한다(`cmd/sage-wiki/ontology_resolve.go:34-37`).
[확인] 추출 전 프롬프트에는 기존 concept **이름만** 쉼표로 넣는다. 별칭은 넣지 않는다(`concepts.go:124`, `extract_concepts.txt:5-6`). triple 프롬프트에는 기존 이름 목록조차 없다. "Use the same form the wiki uses for concepts"라는 지시만 있다(`extract_triples.txt:14-15`).
[확인] 추출 뒤 정규화가 주력이다. 소문자+trim 일치, manifest 별칭 대조(rule 2), 배치 안 별칭 겹침(rule 1)을 쓴다(`concepts.go:318-470`). Pass 3은 문서 안 `[[별칭]]`을 정식 이름으로 바꾼다(`write.go:696-755`).
[추정] 사용자의 "용어집을 프롬프트에 주고 추출 뒤 정규화" 설계와 비교하면 sage-wiki는 앞쪽(프롬프트 앵커)이 약하고 뒤쪽(사후 병합·검토)이 강하다 — 사례: concept 프롬프트 1개는 이름만, triple 프롬프트 1개는 앵커 없음, 사후 경로는 정규화·임베딩 dedup·LLM curation·resolution 4개.

### C 원문 연결 범위

[확인] 연결 단위는 문서다. 청크·문장 단위 링크는 엔티티에 붙지 않는다.
- concept → source: Pass 3이 `concept.Sources`의 모든 문서로 `cites` 엣지를 건다(`write.go:365-382`). `Sources`는 Pass 2에서 LLM이 "which source files mention this concept"로 낸 목록이다(`extract_concepts.txt:17`). manifest는 컴파일마다 합집합으로 쌓는다(`manifest.go:220-229`).
- triple 엣지: `source_doc` 열 하나다. 같은 `(source, target, relation)`을 다른 문서가 다시 주장하면 confidence가 **더 높을 때만** evidence·source_doc을 덮는다(`ontology.go:321-327`). 그래서 엣지 하나는 문서 하나만 가리킨다.
- evidence: raw가 아니라 summary에서 인용한다. "`evidence` is quoted from the document's compiled summary, not from the raw source file"(`docs/guides/graph-memory.md:33-34`). 인용이 summary에 실제로 있는지 공백·대소문자 정규화 후 부분 문자열로 확인하고, 없으면 엣지를 버린다(`extract_triples.go:907-940`).
[확인] 그래서 "처음 본 곳만"인지에 대한 답은 경로마다 다르다. concept→문서 `cites`는 LLM이 언급을 인정한 모든 문서로 쌓인다. triple 엣지의 출처는 가장 확신 높은(동률이면 먼저 쓴) 문서 하나만 남는다.
[추정] concept의 `Sources`는 LLM이 summary(1000자로 잘린 것)를 보고 고른 목록이라, 문자열 대조로 찾은 "나온 모든 곳"보다 좁을 수 있다 — 사례: `concepts.go:182-184`가 summary를 1000자로 자른다. 실행해 재현율을 재지는 않았다.
[추정] 임베딩 dedup이 기존 concept(다른 이름)에 합친 concept은 manifest `Sources`에는 새 문서가 들어가지만 `cites` 엣지는 생기지 않는다 — 사례: `fullpipeline.go:327-346`이 합친 concept을 Pass 3 목록에서 빼고, `cites`를 쓰는 곳은 `write.go:378` 한 곳뿐이다. 이 차이는 사용자 실험의 "처음 본 청크에만 링크" 문제와 같은 종류다.
[확인] 청크는 검색용으로만 있다. 잘리는 대상은 raw가 아니라 컴파일된 wiki 문서(article)다. "Articles are split into ~800-token chunks during compilation"(`docs/guides/search-quality.md:41`). 그래서 이 청크도 원문 위치를 가리키지 않는다. Pass 3은 raw 원문을 heading 단위로 나눠 이름·별칭이 걸린 절을 문서 작성 맥락으로 뽑는다(`write.go:1080-1110`). 이 절 선택은 저장되는 링크가 아니다.

### D 새/기존 연결

[확인] 새 문서를 넣으면 다음 순서로 기존 엔티티에 붙는다.
1. 프롬프트 앵커: concept 추출 프롬프트가 기존 concept 이름 목록을 받고 "Merge with existing concepts when appropriate (detect aliases)"라고 지시한다(`extract_concepts.txt:5-6,20`).
2. 이름·별칭 대조: 새 이름이 manifest 별칭과 같으면 정식 concept에 접는다(`concepts.go:375-398`).
3. 임베딩 dedup: concept 이름을 임베딩해 기존 이름과 cosine ≥ 0.85면 합친다. 이름이 정확히 같으면 이 단계를 건너뛰고, 그대로 Pass 3에서 기존 문서를 다시 쓰며 새 source로 `cites`를 더한다(`dedup.go:145,162`, `write.go:215-221`). 숫자 토큰이 다르거나 draft/final 같은 반의어 쌍이면 합치지 않는다(`dedup.go` `neverMergeNames`).
4. entity ID 일치: triple 엔티티 ID는 LLM이 낸 이름 문자열이다. trim만 한다(`extract_triples.go:188`). 같은 ID면 `AddEntity` upsert로 한 행이 된다(`ontology.go:166-173`).
5. entity resolution(opt-in): 이번 컴파일이 건드린 엔티티만 씨앗이다. 같은 종류 안에서 정규화 이름 전체 일치, 또는 흔하지 않은 토큰 하나 이상 공유, 또는(옵션) 임베딩 유사도로 후보를 묶는다(`resolve_entities.go:466-570`). LLM이 E1, E2 라벨로 클러스터·same_referent·broader·confidence를 낸다(`internal/prompts/templates/resolve_entities.txt`). 자동 적용 조건은 threshold < 1.0, same_referent, broader 아님, confidence ≥ threshold, 둘 중 하나에 설명문 있음이다(`resolve_entities.go:323-344`).
[확인] 링크는 행을 합치지 않는다. canonical이 alias의 엣지를 "derived edge" 표로 받는다. `--unlink`는 그 링크가 만든 엣지만 지우고, 쌍을 거절 목록에 넣고, 남은 링크로 다시 유도한다(`graph-memory.md:129-144, 210-227`). canonical은 LLM이 아니라 Go가 고른다. 문서가 있는 행 → 최신 created_at → id 순이다(`resolve_entities.go:251-285`).
[확인] source 종류 엔티티는 resolution하지 않는다(`resolve_entities.go:1036`).

### E 새 용어

[확인] concept 경로에서는 schema 밖 이름이 자동으로 새 concept·새 문서가 된다. 걸러내는 장치는 잡음 필터(2자 미만, `$`·`\`, 숫자만, 경로 모양 이름; `concepts.go:270-310`), evidence gate(source 0개 제거), 선택형 LLM curation(keep/fold/drop, drop은 `allow_drop`일 때만; `curate.go:19-29`, `internal/prompts/templates/curate_concepts.txt`)이다.
[확인] triple 경로에서 모르는 **엔티티 종류**는 `concept`로 바뀌고, 모르는 **술어**는 엣지째 버린다. 관계가 하나도 안 남은 엔티티도 버린다. 모두 개수를 세어 경고 로그를 남긴다(`extract_triples.go:194-205, 223-226, 274-287`).
[확인] 새 이름이 기존 이름과 비슷하면 resolution 후보 묶음에 들어간다. 그중 LLM이 같은 대상으로 묶은 것만 제안이 된다. 묶지 않은 이름은 "A label you omit is never merged"대로 그냥 남는다(`resolve_entities.txt:32-33`). threshold 1.0이면 제안은 전부 사람 검토 대기열로 간다(`resolve_entities.go:1473-1474`). 대기열이 있으면 매 실행마다 경고를 띄운다(`resolve_entities.go:289-303`).
[확인] schema 자체를 늘리는 자동 경로는 없다. 버려진 술어를 모아 "새 관계 종류 후보"로 사람에게 올리는 대기열도 없다. 찾아본 곳: `extract_triples.go`의 unmapped 처리(로그만), `internal/trust`(Q&A 출력과 edge conflict만 다룸), `cmd/sage-wiki/ontology_resolve.go`.

### F 범용어 허브

[확인] resolution 후보 묶기에서만 흔한 토큰을 뺀다. 같은 종류 안에서 `max(min_token_df_floor, max_token_df × 종류 내 엔티티 수)`보다 많은 엔티티에 나오는 토큰은 묶기에 쓰지 않는다. 기본값은 0.05와 20이다(`resolve_entities.go:109-110, 201-240`). 이름 불용어(in, on, the 등)와 1자 토큰도 뺀다(`resolve_entities.go:157-190`).
[확인] 이 장치는 "model" 같은 단어가 수백 엔티티를 한 LLM 호출로 끌어들이는 비용 문제를 막는다(`graph-memory.md:239-244`). 그래프에 범용어 노드가 생기고 모든 것과 이어지는 문제를 막지는 않는다.
[확인] 그래프 허브를 누그러뜨리는 장치는 검색 쪽에 있다.
- 관련 문서 점수의 Adamic-Adar: 공유 이웃마다 1/log(degree)를 더한다. 차수 높은 허브 이웃은 기여가 작다(`internal/graph/relevance.go:201-244`).
- `cites` 엣지는 이웃 수집에서 뺀다(`relevance.go:318`). 그래프 검색 채널에서 `cites` 가중치는 0.7이다. 관계별 가중치를 0으로 두면 그 관계를 끈다(`internal/search/graphleg.go:19-42`).
- 문서마다 "See also" 관련 concept을 공유 source 수 순으로 8개까지만 단다. 주석: "a source cited by many concepts would otherwise flood every article with links"(`write.go:775-779`).
- triple은 문서당 엔티티 40개, 관계 60개 상한이다(`extract_triples.go:587-591`).
[확인] stoplist, 문서 빈도 기준으로 허브 엔티티를 만들지 않는 장치, 계층(broader/narrower) 엣지는 없다. resolution 프롬프트의 `broader` 플래그는 "넓은 개념과 좁은 개념을 합치지 말라"는 경고용이다. 계층 관계를 저장하지 않는다(`resolve_entities.txt:24-28`).
[추정] 사용자 실험의 허브 문제(KG, schema, LLM이 모든 청크를 잇는 것)는 sage-wiki에서는 덜 드러날 것이다 — 사례: concept 1개가 문서 하나가 되고 링크는 LLM이 언급을 인정한 문서로만 걸린다(`extract_concepts.txt:17`). 대신 연결 재현율이 그만큼 낮을 수 있다. 실행해서 재지 않았다.

### G 엔티티·이벤트

[확인] 이벤트를 엔티티로 뽑는 경로는 없다. 내장 엔티티 종류 5개에 event가 없다(`entities.go:12-18`). 저장소 전체에서 `TypeEvent`나 event 엔티티 종류를 찾지 못했다(grep `"event"`, `TypeEvent`, `name: event` 대상 `internal/`). `internal/ontology/events.go`는 엣지 추가·무효화를 알리는 감사 이벤트 스트림이다.
[확인] 시간축은 엣지에 붙는다. 엣지마다 `valid_from`(source frontmatter 날짜 → 파일 mtime → 첫 컴파일 시각), `valid_to`, `invalidated_by`가 있다(`graph-memory.md:305-313`, `extract_triples.go:429-442`). `functional: true` 관계에서 새 엣지가 threshold(기본 0.8) 이상이면 이전 엣지를 무효화하고, 낮으면 conflict로 검토에 올린다(`extract_triples.go:537-577`). `as_of`로 과거 시점 질의가 된다.
[추정] 사용자가 이벤트를 원하면 `entity_types`에 event를 추가하는 것까지는 config로 된다 — 사례: meeting-organizer pack이 `action_item`, `blocker`를 엔티티 종류로 더한다(`pack.yaml:15-21`). 이벤트의 시각·참여자 같은 속성 필드는 엔티티 표에 없다(`ontology.go:166-173`의 열: id, type, name, definition, article_path).

### H 근거 수치

[확인] schema·별칭·resolution의 효과를 따로 잰 수치는 없다. `eval/REPORT.md`는 LOCOMO 대화 10개로 만든 wiki에서 overall 87.4%, Search recall@10 100% 등을 보고한다. 이 값들은 wiki 10개의 중앙값이다(`eval/REPORT.md:15-23`). 이 벤치마크의 컴파일 설정에는 triple·resolve가 언급되지 않는다(`eval/benchmarks/REPORT.md:281-289`; `eval/benchmarks/common/sagewiki.py`에서 ontology·triples 문자열을 찾지 못했다).
[확인] 질적 근거는 있다. 보고서는 "Concept coverage"(중앙값 7.9%, 범위 2.3–14.7%)를 결함이 아니라 통합 비율로 읽으라고 설명한다. 예로 든 conv2 한 건에서 summary가 이름 붙인 concept 190개가 문서 27개로 모였다(`eval/REPORT.md:23, 28-34`). 7.9%는 이 190→27 한 건의 값이 아니다. `retrieval_ab.py`는 두 바이너리의 evidence recall@k를 비교하는 도구다(`eval/benchmarks/retrieval_ab.py:1-22`). schema 유무를 비교한 결과 파일은 찾지 못했다.

## 가져올 것

1. 제안: 어휘 강제를 "프롬프트에 목록 + schema에는 enum 없음 + 쓰기 직전 Go 검증"으로 나눈다. 근거: enum 위반 하나가 문서 전체 그래프를 날리는 문제를 피한다(`extract_triples.go:54-63`). 포기하는 것: 모델이 어휘를 어겨도 호출 단계에서 바로 알 수 없다. 버림 개수 로그를 따로 봐야 한다.
2. 제안: 관계 이름을 동의어 표로 사후 대조한다(`mapPredicate`, `extract_triples.go:296-314`). 사용자 실험의 "관계 이름 275종 → 17종" 정규화와 같은 자리다. sage-wiki는 맞지 않는 술어를 버린다. 버린 술어를 모아 사람에게 새 관계 후보로 보이는 대기열을 덧붙이면 E의 빈자리를 채운다.
3. 제안: 별칭 링크를 "합치지 말고 잇기 + derived edge를 따로 저장 + `--unlink`로 정확히 되돌리기"로 만든다(`graph-memory.md:129-144, 210-227`). 사람이 일부만 검토해도 실수를 싸게 고칠 수 있다. 포기하는 것: 행이 둘 남아 질의 층마다 canonical 해석을 해야 한다.
4. 제안: 후보 묶기에 종류별 문서 빈도 상한 + 하한 floor를 쓴다(`resolve_entities.go:201-240`). 사용자 실험의 범용어 허브에는 같은 식을 **링크 생성** 단계에 적용하는 변형이 필요하다. 예를 들어 전체 청크의 x% 넘게 나오는 이름은 원문 링크를 걸지 않거나 가중치를 낮춘다. sage-wiki에는 이 변형이 없으니 직접 만들어야 한다.
5. 제안: 검색 쪽 허브 감쇠로 Adamic-Adar(1/log degree)와 관계별 가중치(`cites` 0.7, 0이면 끔)를 쓴다(`relevance.go:201-244`, `graphleg.go:19-42`). 사용자 실험의 정밀도 하락(0.62 → 0.37)을 링크 단계가 아니라 순위 단계에서 누그러뜨리는 방법이다.
6. 참고: evidence 인용을 원문(summary) 부분 문자열로 확인해 지어낸 근거를 버린다(`extract_triples.go:907-940`). 사용자 시스템에서는 summary 대신 원문 청크에 대해 같은 검사를 하면 C의 한계(summary 인용)를 피할 수 있다.
7. 참고: 라이선스는 MIT다. 코드·프롬프트를 저작권 표시만 남기고 가져다 쓸 수 있다.

## 출처

- 저장소: https://github.com/xoai/sage-wiki
- commit: `d3ef3a1346405c82eac01b4d7c493c94c1c59169` (2026-10-03)
- 로컬 사본: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/xoai_sage-wiki` (`git clone --depth 1`)
- 라이선스: MIT (`LICENSE`, "Copyright (c) 2026 xoai")
- 주로 읽은 파일: `README.md`, `docs/guides/configurable-relations.md`, `docs/guides/graph-memory.md`, `docs/guides/search-quality.md`, `internal/compiler/{fullpipeline,concepts,dedup,curate,evidence_gate,extract_triples,resolve_entities,write}.go`, `internal/ontology/{ontology,entities}.go`, `internal/prompts/templates/{extract_concepts,extract_triples,resolve_entities,curate_concepts}.txt`, `internal/graph/relevance.go`, `internal/search/graphleg.go`, `internal/config/config.go`, `eval/REPORT.md`
- 코드는 실행하지 않았다. 위 [추정]은 모두 코드 읽기에서 끌어낸 것이다.

## 검증 기록

다른 에이전트가 쓴 위 보고서를 반박 목적으로 다시 확인했다. 로컬 사본 commit은 `d3ef3a1`로 보고서와 같다. 코드는 실행하지 않고 읽기만 했다.

### 다시 열어 맞는 것을 확인한 인용

| 축 | 다시 연 곳 | 결과 |
|---|---|---|
| A | `config.go:841-850, 1030-1040`, `entities.go:12-18`, `configurable-relations.md:28-39`, `extract_triples.txt:16,27`, `extract_triples.go:54-63, 131-135, 175-314`, `ontology.go:153-155, 304-309` | 맞다. config는 사람이 쓰는 YAML이다. entity_types·relation_types를 LLM이 만드는 경로는 찾지 못했다 |
| B | `extract_concepts.txt:5-6,16,20`, `concepts.go:124, 182-184, 318-470`, `manifest.go:220-237`, `cmd/sage-wiki/ontology_resolve.go:34-38` | 맞다. 엔티티 별칭은 LLM이 내고 사람은 승인·거절·되돌리기만 한다 |
| C | `write.go:365-382`(cites를 쓰는 곳은 이 한 곳뿐), `ontology.go:315-327`(confidence가 더 클 때만 덮음), `graph-memory.md:31-34`, `extract_triples.go:749,822,907-940`(evidence 대조 대상은 summary 본문) | 맞다. 임베딩 dedup이 합친 concept은 `mergeConceptIntoManifest`로 manifest만 늘고 Pass 3 목록에서 빠진다(`fullpipeline.go:327-337`, `evidence_gate.go:35-60`). 그래서 [추정]도 코드와 어긋나지 않는다 |
| D | `dedup.go:40,145,162`, `write.go:215-221`, `extract_triples.go:188,485-490`, `resolve_entities.go:251-285, 323-344, 534-563, 1036`, `graph-memory.md:129-144, 210-227` | 맞다 |
| E | `concepts.go:270-303`, `curate.go:17-29`, `evidence_gate.go:13-28`, `config.go:424-429`(기본 1) | 맞다 |
| F | `resolve_entities.go:106-110, 157-240`, `relevance.go:201-244, 318`, `graphleg.go:19-42`, `write.go:775-779`, `extract_triples.go:587-591` | 맞다 |
| G | `entities.go:12-18`, `extract_triples.go:429-442, 537-577`, `graph-memory.md:305-339` | 맞다 |
| H | `eval/REPORT.md:1-34`, `eval/benchmarks/REPORT.md:276-290`, `config.go:1021-1027`(triples `Enabled` 기본 false) | 수치 해석 한 곳을 고쳤다 |

### 고친 것

1. H: 원래 "Concept coverage 7.9%는 concept 190개를 문서 27개로 모은 통합 비율"이라고 적었다. 7.9%는 wiki 10개의 중앙값이다. 190→27은 conv2 한 건의 예시다(27/190은 약 14%). 둘을 나눠 적었다. overall 87.4%와 recall@10 100%도 중앙값이라고 밝혔다.
2. C: "문서를 ~800 토큰으로 잘라"를 "컴파일된 wiki 문서(article)를 잘라"로 고쳤다. 원문은 "Articles are split"이다. raw 청크로 읽히면 원문 연결 범위를 부풀린다.
3. E: "비슷하면 resolution 제안이 된다"를 "후보 묶음에 들어가고 LLM이 묶은 것만 제안이 된다"로 고쳤다. 프롬프트는 확신 없는 이름을 빼라고 하고, 뺀 이름은 대기열에 가지 않는다(`resolve_entities.txt:32-33`).

### 고치지 않은 것

- 인용한 파일:줄은 모두 해당 내용이 그 자리에 있었다. 줄 번호를 고칠 곳은 없었다.
- 결론은 그대로다. schema(엔티티 종류·관계 종류·관계 동의어)는 사람이 config에 정한다. 정식 이름+별칭 용어집은 사람이 쓰지 않는다.


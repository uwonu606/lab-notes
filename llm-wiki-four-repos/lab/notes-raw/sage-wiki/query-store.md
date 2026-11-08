# sage-wiki — query-store 갈래 노트

레포 xoai/sage-wiki, HEAD `d3ef3a1`(2026-10-03), MIT. 경로는 레포 루트 기준 `path:line`이다. 코드는 실행하지 않았다. 읽기 전용 git·grep·sed·cat과 `gh issue view`만 썼다.

표기 규칙은 이렇다. 작성자가 밝힌 이유는 원문을 큰따옴표로 인용하고 출처를 단다. 추론한 이유는 `[추정]`을 앞에 달고 근거 사례와 개수를 괄호에 붙인다. 근거가 없으면 `모르는 것:`으로 적는다.

## 읽은 범위

| 대상 | 정도 |
|---|---|
| `internal/query/{query,graphqa,globalqa}.go` | 끝까지 |
| `internal/search/{run,pipeline,expand,rerank,graphleg,docresult}.go` | 끝까지 |
| `internal/hybrid/search.go` | 끝까지 |
| `internal/memory/{entries,chunks}.go` | 끝까지 |
| `internal/trust/*.go` (10개) | `migrate.go`, `store.go` 일부만 훑음. 나머지 끝까지 |
| `internal/linter/{runner,passes,learning}.go` | 끝까지 |
| `internal/graph/{relevance,serialize}.go` | 끝까지. `graph/community/*` 훑음 |
| `internal/vectors/store.go` | 끝까지. `cache.go`, `ann.go`, `rebuild.go`, `indexfile.go`, `hnsw/*`, `backend_mmap.go` 훑음 |
| `internal/embed/embed.go` | 핵심 경로(cascade, long-text, retry) 읽음. provider별 HTTP 본문 훑음 |
| `internal/storage/{db,open_options,output_index}.go` | 끝까지 |
| `internal/storage/postgres/*` | 함수 목록과 `backend.go` 머리만 훑음 |
| `internal/store/*`, `internal/storedial/dial.go`, `internal/sqlitestore/backend.go`, `internal/app/app.go` | 끝까지 |
| `internal/wiki/{ingest,reconcile}.go` | 끝까지. `status.go`, `doctor.go`, `init.go` 훑음 |
| `internal/scribe/*` | 끝까지 |
| `docs/guides/{search-quality,graph-memory,output-trust,storage-backends,agent-memory-layer,metrics}.md` | 끝까지 |
| 이슈 #74, #104, #125, #144, #145 / commit 메시지 약 25개 | 읽음 |

다른 갈래와의 경계는 이렇다. compile 파이프라인(summary, concept 추출, article 작성, triple 추출, entity resolution, community 요약)은 다른 갈래 몫이라 이 노트에서는 "검색·저장이 그 결과를 어떻게 쓰는가"만 적는다. MCP·web·hub 어댑터는 검색 facade를 부르는 자리만 확인했다.

ADR·spec 문서는 공개 레포에 없다. 코드 주석이 `ADR-036`~`ADR-039`, `decision-035`, `decisions.md`를 가리키지만 `.gitignore`가 `sage/`를 제외하고(`.gitignore:12`), git 이력 전체에서 그런 파일을 찾지 못했다(`git log --all -- '*decisions.md' '*ADR*'` 결과 없음).

그래서 "왜"의 출처는 코드 주석, commit 메시지, docs, 이슈다.

## 모듈 지도

진입점에서 저장소까지 누가 누구를 부르는지다.

```
CLI query / MCP wiki_query / web StreamQuery
  └─ query.Query / StreamQuery              internal/query/query.go:52, :863
       ├─ buildQueryContext                  query.go:212
       │    ├─ search.Run (Granularity=Chunks)        search/run.go:124
       │    │    ├─ buildGraphLeg  (ontology)          search/graphleg.go:53
       │    │    └─ EnhancedSearch                     search/pipeline.go:268
       │    │         ├─ StrongSignal / ExpandQuery    search/expand.go:105, :41   [LLM]
       │    │         ├─ ChunkStore.SearchChunks (FTS5) memory/chunks.go:70
       │    │         ├─ EntryStore.Search (FTS5)       memory/entries.go:128
       │    │         ├─ VectorStore.SearchChunks/Search vectors/store.go:375, :328
       │    │         ├─ fuseLegs (weighted RRF)        search/pipeline.go:98
       │    │         ├─ hydration                      pipeline.go:407-472
       │    │         └─ Rerank → blendResults          search/rerank.go:193, pipeline.go:175  [LLM]
       │    ├─ computeGraphExpansion → graph.ScoreRelevance   query.go:972, graph/relevance.go:73
       │    └─ buildContextFromEnhanced (파일 읽기)   query.go:309
       │         (실패·청크 없음이면 buildDocLevelContext → hybrid.Searcher)  query.go:462
       ├─ LLM synthesis                       query.go:130   [LLM]
       └─ autoFile                            query.go:673
            ├─ trust mode ≠ "true" → trust.ProcessOutput     trust/hooks.go:170
            └─ "true" → outputs/에 쓰고 FTS·vector·ontology·chunk 색인  query.go:718-858

MCP wiki_search / CLI search / web / TUI
  └─ search.Run (Granularity=Docs, LLM 단계 기본 off, IncludeDoc=trust 술어)  mcp/server.go:315-375

MCP wiki_graph_query
  ├─ GraphQA  → hybrid 검색으로 seed → graph.SerializeSubgraph → LLM(구조화 출력)   query/graphqa.go:115
  └─ GlobalQA → community 요약 map-reduce                                         query/globalqa.go:50

sage-wiki verify / outputs …     → trust.Verify / PromoteOutput / RejectOutput   trust/verify.go:31, promote.go:30
sage-wiki lint                   → linter.Runner (8 pass, LLM 없음)               linter/runner.go:95
시작 시 reconcile                → wiki.ReconcileBackend                           wiki/reconcile.go:48
저장소 열기                      → app.Open → storedial.Open → sqlitestore | postgres   app/app.go:66, storedial/dial.go:21
```

## 핵심 자료 구조

### 테이블 (SQLite)

마이그레이션은 V1~V15, 덧붙이기만 한다(`internal/storage/db.go:156-173`).

| 테이블 | 열 | 들어온 곳 |
|---|---|---|
| `entries` (FTS5) | `id, content, tags, article_path`, `tokenize='porter unicode61'`, `prefix='2 3'` | V1 `db.go:280-283`, V8 `db.go:543-552` |
| `vec_entries` | `id, embedding BLOB, dimensions` | V1 `db.go:286-290` ("pure Go, no sqlite-vec") |
| `entities` | `id, type, name, definition, article_path, metadata, created_at, updated_at` | V1, V4에서 type CHECK 제거 `db.go:390-405` |
| `relations` | `id, source_id, target_id, relation, metadata, created_at` + V10의 `evidence, confidence, source_doc, valid_from, valid_to, invalidated_by`. `UNIQUE(source_id,target_id,relation)`, FK CASCADE | `db.go:305-313`, `db.go:606-613` |
| `chunks_meta` | `chunk_id, doc_id, chunk_index, heading, content, start_offset, end_offset` | V3 `db.go:358-366` |
| `chunks_fts` (FTS5) | `chunk_id UNINDEXED, heading, content` | V3 `db.go:371-375` |
| `vec_chunks` | `chunk_id, doc_id, embedding, dimensions` | V3 `db.go:378-383` |
| `learnings` | `id, type, content, tags, created_at, source_lint_pass` | V1 `db.go:320-327` |
| `compile_items` | tier, pass 플래그, `query_hit_count`, `quality_score`, 큐 lease 열 | V5 `db.go:429-475`, V9, V15 |
| `pending_outputs` | `id, question, question_hash, answer, answer_hash, state, confirmations, grounding_score, sources_hash, sources_used, file_path, created_at, promoted_at, demoted_at` | V6 `db.go:479-494` |
| `confirmation_sources` | `output_id, chunk_ids(JSON), answer_hash, confirmed_at` | V6 `db.go:501-507` |
| `pending_questions_vec` | `question_hash, embedding, dimensions` | V6 `db.go:512-516` |
| `output_index` | `output_path, content_hash, indexed_at` | V7 `db.go:526-532` |
| `entity_aliases` | `(alias, canonical_id)` PK, `status`, `confidence, reason, source, decided_by` | V11 `db.go:640-659` |
| `derived_relations` | `alias_id` + relation 열 전부, PK `(alias_id, source_id, target_id, relation)` | V12 `db.go:678-699` |
| `entry_dates` | `id, source_date` | V13 `db.go:216-221` |
| `communities`, `community_members` | level, parent, member_count, summary, summary_hash | V14 `db.go:187-205` |

### 문서 ID 규약

검색 결과의 `DocID`가 무엇을 가리키는지가 조회 경로 전체를 정한다.

| DocID 모양 | 무엇 | 색인하는 곳 | Q&A 문맥에서 읽는 파일 |
|---|---|---|---|
| `concept:<name>` | concept article. tags에 entity type과 **별칭 목록**이 들어간다 | `internal/compiler/write.go:388-392` | `<output>/concepts/<name>.md` (`query.go:602-605`) |
| raw 경로 그대로(예: `raw/a.md`) | summary. ArticlePath는 summary 파일 | `internal/compiler/fullpipeline.go:246-251`, `pipeline.go:1653-1658` | 강화 경로에서는 **읽지 않는다**(아래 #어긋나는 점) |
| `src:<raw 경로>` | tier 0/1 raw 원문 색인 | `internal/compiler/index.go:60-64`, 청크 `index.go:273-298` | raw 파일 자체(`query.go:614-616`) |
| `output:<file>` | Q&A 되저장 답 | `query.go:768-773`, `trust/promote.go:55-60` | `<output>/outputs/<file>` |

청크 ID는 `<docID>:c<i>`다(`query.go:833`, `index.go:290`, `reconcile.go:337`).

### Go 구조체

- `search.Request{Query, Limit, Channels, Expand, Rerank, Tags, FilterTags, Granularity, RerankMinCoverage}` — 영값이 기본이다. 모든 채널, LLM 단계 off, Docs 단위(`search/run.go:37-64`).
- `search.Deps{Mem, Chunks, Vec, Embedder, Client, Model, BM25Weight, VectorWeight, Ont, GraphWeight, GraphRelationWeights, IncludeDoc, Now}` (`run.go:68-96`). `IncludeDoc`가 trust 술어를 받는 seam이다.
- `search.SearchResult{DocID, ChunkID, ChunkText, Heading, RRFScore, RerankScore, FinalScore, Rank, BM25Rank, VectorRank, GraphRank, SourceDate, ArticlePath, Tags, AliasOf}` (`pipeline.go:229-264`).
- `search.RerankResult{ID, Score, Scored, RetrievalRank}` — `Scored`가 "LLM이 0점을 줌"과 "채점 안 함"을 가른다(`rerank.go:169-174`).
- `query.QueryResult{Question, Answer, Sources, ChunksUsed, Format, OutputPath, FilingError}` (`query.go:33-44`).
- `query.GraphQAResult{Answer, Cited []CitedEdge, Truncated, Seeds}`, `CitedEdge`는 edge의 `source_doc, confidence, evidence, valid_from, valid_to`를 그대로 옮긴다(`graphqa.go:46-64`).
- `store.PendingOutput`, `store.Confirmation`, `store.OutputState{pending, confirmed, conflict, stale}` (`store/domain.go:246-278`).
- `store.Backend` — `Entries/Chunks/Vectors/Ontology/Communities/Trust/CompileItems/OutputIndex/Learnings` + `WriteTx/BeginWrite/Health/Close` (`store/interfaces.go:332-362`).
- `linter.Finding{Pass, Severity, Path, Message, Fix}` (`linter/runner.go:24-30`).

## 흐름 1 — 검색 (search.Run)

`internal/search/run.go:124`의 주석이 순서를 적는다: "graph leg → enhanced chunk+doc pipeline → hard tag filter → soft tag boost → Docs shaping → recency tie-breaker → stable re-sort → trust predicate → limit".

| 단계 | 입력 → 처리 → 출력 | 결정적/LLM | 근거 |
|---|---|---|---|
| 0. over-fetch | 태그 필터·trust 술어가 있으면 `limit×3`을 파이프라인에 요청 | 코드 | `run.go:141-148` |
| 1. graph leg | 질의 토큰과 하이픈 bigram/trigram을 entity ID로 정확 대조 → applied alias로 canonical 해석 → 2 hop까지 `Σ 1/relation_weight` 최단 경로 → article 있는 entity만, `limit×5`개 | 코드 | `graphleg.go:61-80, 125-135, 140-194, 213-223` |
| 2. strong signal | doc FTS 상위 2개의 `|s|/(1+|s|)`가 0.4 이상이고 2위의 2배 이상이면 확장 생략 | 코드 | `expand.go:105-123` |
| 3. query expansion | `lex` 2개, `vec` 1개, `hyde` 1개를 구조화 출력으로 받음. 20초 제한, 실패 시 원 질의만 | LLM | `expand.go:36-84`, 스키마 `expand.go:88-100` |
| 4. leg 목록 만들기 | 원 질의+lex 각각에 chunk-FTS, doc-FTS. 원 질의+vec+hyde 각각을 임베딩해 chunk-vector, doc-vector. 각 leg는 `limit×5`개 | 코드 | `pipeline.go:295-393` |
| 5. RRF 융합 | 문서 단위로 `Σ w_channel/(60+rank)`. 같은 list 안에서는 문서당 첫 hit만 셈. 가장 순위 높은 청크가 문서의 대표 청크 | 코드 | `pipeline.go:98-168` |
| 6. hydration | 내용 없는 청크는 `chunks_meta`에서, 그래도 빈 것은 `entries`에서 본문을 채움. 상위 `max(limit,15)`개만 | 코드 | `pipeline.go:407-472` |
| 7. rerank | 상위 15개, 청크 400토큰, 총 8000토큰. 0~10점 JSON 배열. 30초 제한 | LLM | `rerank.go:176-252` |
| 8. blend | RRF를 min-max로 [0,1] 정규화. 채점 비율이 `rerank_min_coverage`(기본 0.5) 미만이면 RRF 순서 유지. 이상이면 순위별 75/60/40% 가중 혼합 | 코드 | `pipeline.go:175-226`, `rerank.go:298-356, 436-447` |
| 9. 태그 | `FilterTags`는 AND 하드 필터(doc-FTS leg 안에도 밀어 넣음), `Tags`는 태그당 +0.03, 상한 0.15 | 코드 | `run.go:216-242`, `pipeline.go:37-42, 320` |
| 10. 날짜 | `source_date`가 있으면 `0.05×2^(−age/14일)` 가산. 없으면 0 | 코드 | `run.go:263-292` |
| 11. trust 술어 | `output:` 문서를 mode에 따라 거름 | 코드 | `run.go:299-307`, `trust/predicate.go:42-58` |

FTS 질의는 공통 규칙을 탄다(`memory/entries.go:128-246`). 소문자화 → `SanitizeFTS`(영숫자, `-`, `_`, 한자·한글·가나만 남김) → 영어 불용어 제거 → 문서 100개 초과 코퍼스에서 문서의 20% 넘게 걸리는 단어 제거(모두 지워지면 앞 3개 유지) → `"term"*` OR 결합이다.

열 가중치는 `bm25(entries, 3.0, 1.0, 1.5, 3.0)`로 id·article_path 3배, tags 1.5배다(`entries.go:155-160`). 청크 FTS에는 열 가중치가 없다(`chunks.go:91-98`).

실패 처리는 "조용히 낮추되 기록한다"가 일관된 규칙이다. 임베딩 일부·전부 실패는 경고 로그를 남기고 진행한다(`pipeline.go:353-365`). 확장·rerank 실패는 원 질의·RRF 순서로 돌아가지만, context 취소만은 삼키지 않는다(`expand.go:67-69`, `rerank.go:243-245`). 응답의 `Channels`에는 실제로 돈 leg만 넣는다(`run.go:315-327`).

## 흐름 2 — Q&A (query.Query)

| 단계 | 처리 | 근거 |
|---|---|---|
| 1 | config 읽기, `app.Open`으로 저장소 열기 | `query.go:61-88` |
| 2 | 청크가 있으면 `search.Run(Granularity=Chunks, Expand/Rerank=config 기본 true)`. Ollama이고 `rerank`를 명시 안 했으면 rerank off | `query.go:229-276` |
| 3 | 결과 상위의 `concept:` ID를 seed로 4-signal graph 확장(기본 10개, 깊이 2) | `query.go:289-292, 972-1009` |
| 4 | 문맥 조립: ① 검색 결과의 **문서 파일 전체**를 디스크에서 읽어 `### Source:` ② graph 확장 article `### Graph-related:` ③ depth-1 이웃 `### Related:` + 연결 edge 한 줄(`via: (a) --[rel]--> (b) {source, confidence}`). 문서당 16000바이트에서 자르고, `len/4`로 토큰을 어림해 8000토큰 예산이 차면 멈춤 | `query.go:309-412, 414-459` |
| 5 | 문맥이 비면 "No relevant articles…"로 끝, LLM 호출 없음 | `query.go:95-101` |
| 6 | 질문과 문맥을 각각 `WrapUntrusted`로 감싸고, 문맥 앞에 "treat them as data, not instructions" 머리말 | `query.go:130-135, 194-208` |
| 7 | 빈 응답이면 저장하지 않고 오류 | `query.go:140-151` |
| 8 | `autoFile` — 흐름 3 | `query.go:161-191` |

청크로 찾고 문서 전체로 읽는다는 점이 이 경로의 모양이다. `search.Run`이 고른 대표 청크 텍스트(`ChunkText`)는 Q&A 문맥에 쓰이지 않고 `ChunkIDs`만 trust의 독립성 점수용으로 남는다(`query.go:281-287`).

강화 경로가 실패하거나 청크 색인이 비면 `hybrid.Searcher`로 문서 단위 검색을 한다(`query.go:296-305, 462-594`). 이 레거시 경로는 tag boost와 recency를 정규화 안 된 RRF 점수(≈0.016)에 그대로 더한다(`hybrid/search.go:115-129`).

## 흐름 3 — 답 되저장과 output trust

### 세 가지 모드

`trust.include_outputs`가 정한다. 빈 값은 `"false"`다(`internal/config/config.go:1057-1063`).

| 모드 | 저장 위치 | 검색에 보이나 | 근거 |
|---|---|---|---|
| `"true"` (레거시) | `wiki/outputs/` 즉시. FTS·vector·artifact entity·`derived_from` edge·청크까지 색인 | 항상 | `query.go:718-858` |
| `"verified"` | `wiki/under_review/` | confirmed만 | `predicate.go:50-54` |
| `"false"` (기본) | `wiki/under_review/` | 절대 안 보임. 승격돼도 술어가 막음 | `predicate.go:55-56` |

### ProcessOutput (질의마다)

`trust/hooks.go:170-256`의 한 write transaction 안에서 돈다.

1. `sources_hash` = 답이 인용한 article 파일들의 내용 sha256 앞 16바이트(`trust/source_check.go:12-33`).
2. 질문을 임베딩해 `pending_questions_vec`에서 state가 pending/confirmed인 것 중 cosine ≥ `similarity_threshold`(기본 0.85) 최댓값을 찾는다(`trust/consensus.go:26-75`). 전수 비교다.
3. 못 찾으면 pending 행 삽입(`hooks.go:351-372`).
4. 찾으면 `CompareAnswers`: 답 임베딩 cosine ≥0.9면 일치, <0.7이면 불일치, 사이면 LLM에 "agree"/"disagree" 한 단어(`consensus.go:77-115`).
5. 일치: 같은 `chunk_ids` 증거면 세지 않는다(멱등). 아니면 `confirmation_sources` 추가, 확인 수 +1, 독립성 = 확인들 사이 청크 집합 Jaccard 거리 평균(`hooks.go:268-326`, `consensus.go:117-145`).
6. 자동 승격 조건: `확인 ≥ threshold(3)` 이고 `독립성 > 0.3`, 또는 `확인 ≥ 2×threshold`. 여기에 **이미** `grounding_score ≥ 0.8`이 있어야 한다(`hooks.go:312-318`).
7. 불일치: 기존 행과 새 행을 모두 `conflict`로(`hooks.go:328-348`). conflict 행은 이후 유사 질문 검색에서 빠진다(`consensus.go:30`).
8. tx 밖에서 승격 색인을 하고, new/conflict일 때만 `under_review/` 파일을 쓴다(`hooks.go:242-253`).

### verify (명시 실행)

`trust.Verify`는 pending을 최신순으로 최대 20개 고른다(`trust/verify.go:31-63`). 답에서 claim을 구조화 출력으로 뽑고(`trust/grounding.go:24-55`), claim마다 "grounded"(1.0)/"inferred"(0.5)/"ungrounded"(0.0) 한 단어를 받는다(`grounding.go:76-106`).

passage는 `sources_used`의 파일 전체를 이어 붙인 한 덩어리다(`grounding.go:117`, `verify.go:121-141`). claim이 0개면 1.0이다(`grounding.go:113-115`).

비용은 답 하나에 claim 수+1회 LLM 호출이다(`output-trust.md:147-149`).

### 승격·강등

- `PromoteOutput`: 파일을 `under_review/`→`outputs/`로 옮기고, FTS·날짜·vector·artifact entity·`derived_from` edge·청크를 색인한 뒤 **마지막에** confirmed로 바꾼다(`trust/promote.go:30-150`).
- compile 때 `verified` 모드면 confirmed 답의 `sources_hash`를 다시 계산해 다르면 stale로 강등하고 색인을 지운다(`source_check.go:35-61`, 호출 `internal/compiler/pipeline.go:560-573`). 강등은 확인 수와 grounding을 0/NULL로 되돌린다(`trust/store.go:101-108`).
- `outputs reject/resolve/clean/migrate` CLI가 사람 결정 경로다(`output-trust.md:194-259`).

## 흐름 4 — 그래프 질의

### GraphQA (local)

1. hybrid 검색(BM25+vector, 5개)으로 seed를 고른다(`graphqa.go:128-141`). 0개면 LLM 없이 끝(`graphqa.go:142-145`).
2. `SerializeSubgraph`: seed를 canonical로 해석, hop마다 edge를 `(source, relation, target)`으로 정렬한 **뒤** `max_edges`(기본 60, 최대 500)로 자르고 `E3: (A) --[rel]--> (B) {source, confidence, evidence, valid}` 줄을 만든다(`graph/serialize.go:52-153, 159-186`). `as_of`가 있으면 그 시점에 살아 있던 edge만(`serialize.go:79`).
3. 시스템 프롬프트가 "Answer ONLY from the listed edges"를 강제하고 `{answer, cited:[int]}` 구조화 출력을 받는다(`graphqa.go:90-110, 171-174`).
4. 범위 밖·중복 인용 번호는 버리고, 인용한 edge의 provenance를 그대로 돌려준다(`graphqa.go:193-213`).

### GlobalQA

community 요약을 map-reduce한다(GraphRAG 패턴, `globalqa.go:16-19`). 요약된 community가 2개 이상인 가장 높은 level을 고르고(`globalqa.go:184-217`), 요약을 hybrid 검색으로 `max(4×max_communities, 20)`개 뽑아 `community:` 접두어로 거른다(`globalqa.go:75-102`).

map은 "2-3 sentences … say IRRELEVANT", reduce는 "[id] inline" 인용이다(`globalqa.go:123-171`). community 생성·요약은 compile 갈래 몫이다.

## 흐름 5 — Q&A 문맥용 그래프 확장 (4-signal)

`graph.ScoreRelevance`(`internal/graph/relevance.go:73-300`)는 검색 순위 채널이 아니라 Q&A 문맥에 article을 **덧붙이는** 장치다.

| 신호 | 기본 가중 | 계산 | 근거 |
|---|---|---|---|
| direct_link | 3.0 | seed에서 `cites`를 뺀 edge로 깊이 2 안에 닿으면 seed마다 +1 | `relevance.go:151-164, 304-336` |
| source_overlap | 4.0 | seed가 `cites`하는 source를 함께 `cites`하는 entity마다 +1, seed source 총수로 나눔 | `relevance.go:166-199` |
| common_neighbor | 1.5 | 공유 이웃마다 `1/ln(degree)` (Adamic-Adar) | `relevance.go:201-246` |
| type_affinity | 1.0 | entity type 쌍 표(같은 type 0.5~0.8, 교차 1.0~1.2) 평균 | `relevance.go:46-52, 248-266` |

article 있는 entity만 남기고 상위 `graph_max_expand`(10)개를 쓴다(`relevance.go:277-297`). `source_overlap`은 source의 인기도로 감쇠하지 않는다. 큰 문서 하나를 많은 concept가 `cites`하면 그 concept들이 모두 같은 크기의 신호를 받는다(`relevance.go:172-184`).

## 흐름 6 — lint

`linter.NewRunner`의 8개 pass는 모두 LLM 없이 돈다(`linter/runner.go:95-108`, `passes.go` 전체).

| pass | 하는 일 | 자동 수정 | 근거 |
|---|---|---|---|
| completeness | concept article의 `[[x]]`가 `concepts/x.md` 파일명과 안 맞으면 경고 | 없음 | `passes.go:27-68` |
| style | frontmatter 없음(경고), `concept:` 필드 없음(info) | frontmatter `concept: <name>`, `confidence: low` 삽입 | `passes.go:77-134` |
| orphans | source가 아닌 entity 중 edge 0개 | 없음 | `passes.go:144-180` |
| consistency | `contradicts` edge를 모두 나열 | 없음 | `passes.go:190-214` |
| connections | concept vector끼리 cosine ≥0.7인데 ontology edge가 없으면 info | 없음 | `passes.go:224-292` |
| impute | `[TODO]`, `[UNKNOWN]`, `[TBD]`, `##` 절 본문 50자 미만 | 없음 | `passes.go:312-358` |
| staleness | 파일 mtime 90일 초과 | 없음 | `passes.go:368-397` |
| quality | `compile_items.quality_score` < 0.5, tier 분포, 오류 수 | 없음 | `passes.go:408-478` |

결과는 `.sage/lintlog/lint-<시각>.{json,txt}`로 남는다(`runner.go:179-214`). `learnings`는 내용 sha256으로 중복을 막고, 180일 TTL과 500개 상한으로 지운다(`linter/learning.go:11-14, 24-88`). `RecallLearnings`는 `LIKE '%q%'` 부분 문자열 검색이다(`learning.go:122-131`).

lint는 사실 대조를 하지 않는다. "새·기존 연결고리" 쪽 신호는 connections pass 하나이고, 결과는 info 등급 메시지로만 나온다(`passes.go:281-286`).

## 흐름 7 — 저장 백엔드와 재조정

### seam

`internal/store`가 인터페이스·도메인 타입·sentinel을 갖고, 구현 패키지를 import하지 않는다(`store/types.go:1-5`). `storedial.Open`이 `storage.backend`(sqlite|postgres)로 분기한다(`storedial/dial.go:21-41`). `sqlitestore`는 기존 concrete store를 Backend로 감싼다(`sqlitestore/backend.go:191-207`).

### SQLite 쓰기 규칙

쓰기 연결 1개, `_txlock=immediate`, WAL, `busy_timeout=5000`, `foreign_keys=ON`, `secure_delete=ON`이다(`storage/db.go:40-63`). 읽기 풀 4개(`db.go:66-82`). `WriteTx`가 프로세스 안 mutex로 직렬화한다(`db.go:108-126`).

### Postgres

pgx stdlib + pgvector, `sage_fts` snowball 설정, HNSW 인덱스, session advisory lock(writer 하나) + tx advisory lock(`storage/postgres/backend.go:1-12`, `storage-backends.md:75-87`).

FTS는 `to_tsquery('sage_fts', …)`와 `ts_rank`, vector는 `<=>` 연산자다(`postgres/entries.go:159-206`, `postgres/vectors.go:50-62`). SQLite→Postgres 데이터 이전은 없고 `compile --fresh`로 다시 짓는다(`storage-backends.md:60-68`).

### 벡터 저장

`vec_entries`, `vec_chunks`에 little-endian float32 BLOB(`vectors/store.go:537-553`). 검색은 프로세스 메모리의 정규화 행렬 위 내적 전수 탐색이 기본이다(`store.go:324-360`, `cache.go:8-23`).

선택지는 HNSW(`search.ann.enabled`, `vectors/ann.go`)와 mmap 스냅숏(`vectors.backend: mmap`, `indexfile.go:10-31`)이다. 둘을 함께 켜면 mmap이 이긴다(`store.go:273-281`). 쿼리 벡터 차원이 캐시와 다르면 결과 없음(`store.go:346-351`).

캐시 무효화는 두 갈래다. Store가 직접 쓴 것은 행렬을 바로 고치고, 호출자 tx로 쓴 것은 `InvalidateChunkCache`로 다음 검색 때 다시 읽는다(`cache.go:13-23`, `store.go:233-242`). 다른 프로세스가 쓴 것은 서버 재시작 전까지 보이지 않는다(`search-quality.md:109-113`).

### embedder

명시 `embed:` 설정 → provider API 기본 모델 → 로컬 Ollama(`nomic-embed-text`) → 없음(벡터 검색 off) 순이다(`embed/embed.go:102-187`). OpenAI 호환 경로는 5000 rune 넘는 입력을 잘라 각각 임베딩하고 평균한다(`embed.go:243-320`). 429/503과 잘린 응답 본문은 지수 backoff로 재시도한다(`embed.go:544-590`).

### reconcile (시작 시)

manifest를 "있어야 할 것" 목록으로 보고 파일과 DB를 맞춘다(`wiki/reconcile.go:33-47`).

| 상태 | 조치 | 근거 |
|---|---|---|
| 파일 있음, 색인 없음 | 재색인 | `reconcile.go:233-234` |
| 파일 내용과 FTS 내용 다름 | 재색인 | `reconcile.go:235-236` |
| article인데 청크 vector 없음(embedder 있을 때) | 재색인 | `reconcile.go:237-238, 255-261` |
| 파일 없음, 색인 있음 | FTS·vector·청크·entity 삭제 | `reconcile.go:200-210, 403-425` |
| 일치 | 온라인일 때만 hash 기록 | `reconcile.go:239-246` |

재색인은 embedding을 manifest lock 밖에서 계산하고 쓰기만 lock 안에서 한다(`reconcile.go:273-292`). `output_index` hash를 마지막에 쓴다(`reconcile.go:361-370`, `storage/output_index.go:47-49`).

### ingest·scribe

`IngestPath`/`IngestURL`은 크기 상한, UTF-16/32 BOM 거부, UTF-8 아니면 바이너리 추출 확장자만 허용, URL은 dial 시점 사설 IP 차단 후 source 폴더에 복사하고 manifest에 등록한다(`wiki/ingest.go:56-79, 81-243, 289-331`). 컴파일은 하지 않는다.

`SessionScribe`는 Claude Code 세션 JSONL에서 thinking·tool 블록을 빼고(`scribe/session.go:201-241`), LLM에 entity 최대 10개를 받아(`session.go:282-334`) kebab-case ID가 아니면 버리고, ID가 같으면 정의만 갱신한다(`session.go:116-174`).

## 설계 결정과 이유

### 검색

| # | 결정 | 이유 | 대안·이력 |
|---|---|---|---|
| S1 | 문서 단위로 doc leg와 chunk leg를 모두 RRF에 넣고 합산 | (a) "agreement across granularities (the same document matching both as a whole and in one passage) ranks above a single strong hit" (`search-quality.md:27-30`). commit `9b1c419`: "doc+chunk agreement accumulates … multi-query vector variants SUM like the BM25 side instead of taking min-rank" | 처음(`c1f1a3d`)은 청크 RRF 후 문서 중복 제거였다. `9b1c419`(2026-07-28)에서 바뀜 |
| S2 | RRF k=60 | (a) "Standard RRF constant (Cormack et al. 2009)" (`hybrid/search.go:13`) | 점수 정규화 융합 |
| S3 | 기본 가중 BM25 0.7, vector 0.3, graph 0.2 | 모르는 것: 수치를 고른 근거. 주석은 "the config defaults (spec §2.2, ADR-037)"만 적는다(`pipeline.go:55-60`). 비공개 ADR-037이나 작성자에게 물어야 안다 | — |
| S4 | vector는 BM25로 거르지 않고 전체 청크를 전수 탐색 | (a) commit `ccab065`: BM25 prefilter가 "silently destroys recall for multilingual corpora"; 폴란드어 질의 재현 사례 | 처음엔 BM25 prefilter(`c1f1a3d` M1). 2026-04-21 변경. `SearchChunksFiltered`는 남아 있으나 파이프라인이 안 씀(`vectors/store.go:406-448`) |
| S5 | ontology graph를 세 번째 RRF 채널로 | (a) "the graph channel reaches documents connected to the query's entities even when neither lexical nor vector similarity finds them" (`search-quality.md:362`). 빈 ontology면 결과가 바이트 단위로 같다(`ee6bf48`, `run.go:150-154`) | 이전엔 graph가 Q&A 문맥 확장에만 쓰였다. `ee6bf48`(2026-07-28, ADR-037) |
| S6 | graph seed = 질의 토큰·하이픈 n-gram을 entity ID에 정확 대조 | (a) "entity IDs are hyphenated slugs: "self attention" → self-attention" (`graphleg.go:61-62`). [추정] 검색 호출 없이 싸고 결정적이라서다(사례: 같은 파일이 entity 조회 memo를 "~85% of this leg's cost"라 적으며 비용을 잰다 1건, `graphleg.go:88-91`) | GraphQA는 hybrid 검색으로 seed를 뽑는다(`graphqa.go:132-141`). 두 방식이 공존 |
| S7 | pending alias는 순위에 영향 없음, applied만 | (a) "pending rows are un-approved proposals and must never influence ranking (F-074)" (`graphleg.go:126-128`); `79bc340` | `ee6bf48`은 active alias(pending 포함)로도 seed했다. `79bc340`에서 삭제 |
| S8 | 2-hop 점수는 layered Bellman-Ford | (a) "a plain per-depth BFS propagated stale scores … plain Dijkstra cannot honor the hop bound" (`graphleg.go:140-147`) | BFS(`ee6bf48`) → `79bc340` |
| S9 | 관계별 가중 contradicts 1.1, cites 0.7, 나머지 1.0, 0이면 제외 | (a) "rare-and-informative edges up, high-volume citation-grade edges down" (`graphleg.go:15-17`); 0 제외는 "users need an off-switch per relation type" (`graphleg.go:25-28`) | — |
| S10 | 검색 표면은 LLM 단계 기본 off, `query`만 on | (a) "they cost an LLM round trip per query, which a search call should not spend without being asked" (`search-quality.md:128-134`); `7223110` | — |
| S11 | strong signal이면 확장 생략 | (a) "This saves an LLM call on simple queries" (`search-quality.md:53`) | — |
| S12 | rerank는 "채점 안 함"과 0점을 구분, 채점률 50% 미만이면 혼합 안 함, [0,1] 정규화 공간에서 혼합 | (a) "the zero-coercion failure sage-memory measured at 25-50pp R@1 (ADR-038)" (`rerank.go:165-168`); "was raw RRF ~0.016 vs LLM [0,1]" (`c83ba58`) | 처음엔 원 RRF와 LLM 점수를 그대로 섞었다. `c83ba58`, `52d39c0`(2026-07-28) |
| S13 | 순위별 혼합 비율 75/60/40 | (a) "protects high-confidence retrieval results from reranker noise" (`search-quality.md:59-67`) | cross-encoder(qmd). [추정] 어떤 provider로도 돌게 하려고 LLM 일괄 채점을 골랐다(사례: 비교표 "Model dependency: Any provider" 1건, `search-quality.md:357`) |
| S14 | Ollama면 rerank 자동 off | (a) "Local models often struggle with the structured JSON output that reranking requires" (`search-quality.md:189`) | — |
| S15 | rerank 전에 hydration | (a) graph-only 문서가 "reached the reranker as blank passages" (`79bc340`; `pipeline.go:430-436` F-072) | — |
| S16 | 필터가 있으면 ×3 over-fetch, 태그 필터를 doc-FTS leg 안에도 | (a) "a post-filter alone silently loses rare tags" (`pipeline.go:37-42`); F-048 (`run.go:141-144`) | — |
| S17 | recency는 5% 상한, 14일 반감, 날짜 없으면 0 | (a) "a made-up date would rank a document it knows nothing about above one it does" (`search-quality.md:262-265`) | — |
| S18 | 날짜는 `entry_dates` 별도 표 | (a) "entries is FTS5 (no ALTER), a rebuild would re-index the corpus, and the sidecar leaves BM25 term statistics untouched" (`9fd0c61`; `db.go:207-215`) | FTS 표 재생성(V8 방식) |
| S19 | 문서 20% 넘게 걸리는 질의어 제거(100문서 초과) | (a) "such a term carries no discriminating signal and only dilutes BM25" (`search-quality.md:312-318`). 청크 leg도 문서 비율로: "the legs must prune on identical doc-ratio semantics or they diverge" (`chunks.go:75-82`) | 청크 행 비율(`b3889aa` 이전) |
| S20 | id·article_path 3배, tags 1.5배 | (a) "A concept's slug and its article path are title proxies" (`search-quality.md:322-326`); `6f0da80` | — |
| S21 | concept 별칭을 FTS tags 칸에 넣음 | 모르는 것: 이유 문장은 못 찾았다. [추정] 별칭으로 질의해도 정식 article이 1.5배 가중으로 걸리게 하려는 것이다(사례: `write.go:390` tags 구성 1건 + `entries.go:159` tags 가중 1건) | — |
| S22 | 청크 800토큰, overlap 기본 0, 바꾸면 `reindex` | (a) "byte-identical to previous versions, so upgrading never re-chunks an existing index" (`search-quality.md:226-229`); `398e9eb` | — |
| S23 | Q&A는 청크로 찾고 문서 전체를 문맥에 넣음 | 모르는 것: 명시 이유 없음. [추정] 답이 `[[wikilinks]]`로 article을 인용하게 하려는 것이다(사례: 시스템 프롬프트 "Cite sources using [[wikilinks]]" 1건, `query.go:131`) | 청크만 문맥에 넣기 |
| S24 | Q&A graph 확장에서 source_overlap 가중이 가장 큼 | (a) "articles generated from the same document are inherently related — and this costs zero compute" (`search-quality.md:84`) | — |
| S25 | 확장 article에는 연결 edge를 적지 않고 depth-1 fallback에만 적음 | (a) "expansion aggregates many signals, and naming a single edge there would be false provenance" (`graph-memory.md:365-367`) | — |
| S26 | 검색 결과 본문을 2000 rune에서 자름(MCP) | (a) 이슈 #104: 한 번의 `wiki_search`가 "up to 10 entire documents"를 돌려 호출자 문맥을 넘김 (`mcp/server.go:410-415`) | snippet 모드는 제안만 |

### 되저장·trust

| # | 결정 | 이유 | 대안·이력 |
|---|---|---|---|
| T1 | 기본값에서 답은 검색에 다시 들어가지 않는다 | (a) 이슈 #74 작성자 댓글: "don't include outputs in retrieval context. That kills the feedback loop at zero cost." 원 보고: "Each subsequent run reinforces the wrong number" | 처음엔 `outputs/`에 바로 색인(현재 `"true"` 레거시). `ff03c42`(2026-05-09) |
| T2 | 승격은 grounding(사후 LLM 판정) + consensus(반복 질의) 둘 다 | (a) #74: "Why verification is structurally easier than generation … a narrow entailment check". consensus만으로는 "deterministic repetition, not independent verification" | 다중 모델 검증·자동 충돌 해결은 "Later (if needed)"로 미룸(#74) |
| T3 | 독립성 = 청크 집합 Jaccard 거리 | (a) #74: "If the same 3 source documents are used every time … that's deterministic repetition" | 다른 모델, 다른 표현 질의 |
| T4 | 같은 청크 증거는 확인으로 세지 않음 | (a) "Idempotency: skip if this exact evidence (same chunks) already recorded" (`hooks.go:276`); `ff03c42` "idempotent confirmations" | — |
| T5 | 색인을 다 끝낸 뒤 confirmed 표시 | (a) "Mark confirmed LAST — only after all artifacts are durable" (`promote.go:144`); `ff03c42` "atomic promotion (index before confirm)" | — |
| T6 | 인용한 파일이 바뀌면 stale로 강등 | (a) #74 원 제안: "Auto-demote confirmed outputs whose sources have changed, so they re-earn consensus against fresh data" | — |
| T7 | trust 규칙을 술어 하나로 모든 표면에 | (a) `3b88975`: 이전엔 "an agent searching the wiki could read what a Q&A answer would refuse to cite". legacy 파이프라인도 "rolls back RANKING only" (`mcp/server.go:304-306`) | — |
| T8 | 빈 synthesis 응답은 저장하지 않음 | (a) "Filing that would write a hollow frontmatter-only answer" (`query.go:140-143`); `e99e460` | — |
| T9 | 질문을 YAML `%q`로 이스케이프, 같은 날 같은 slug는 번호 접미어 | (a) "a raw question with quotes or newlines corrupts/injects YAML" (`query.go:741-743`); "Two DIFFERENT questions must never clobber each other" (`query.go:731-734`) | — |
| T10 | 문맥·질문을 untrusted 틀로 감쌈. trust 판정 프롬프트는 감싸지 않음 | (a) "the trust-judge scoring prompts, whose outputs are metrics, not content" (`agent-memory-layer.md:480-482`) | — |

### 그래프 질의

| # | 결정 | 이유 |
|---|---|---|
| G1 | edge 목록에서만 답하고 edge 번호로 인용 | (a) "the grounding contract is verified to reach the provider, not assumed" (`graphqa.go:87-89`); "An answer the edges cannot support says so and cites nothing" (`graph-memory.md:357`) |
| G2 | 구조화 출력 스키마에 enum 없음 | (a) "StructuredCompletion's fallback validates the same schema, and enums make the fallback brittle" (`graphqa.go:96-98`) |
| G3 | 범위 밖 설정값은 기본값으로(clamp 안 함) | (a) "clamping a typo silently honors it" (`graphqa.go:30-33`) |
| G4 | 정렬 후 자르기 | (a) "truncating during collection would make the retained subset depend on backend return order" (`serialize.go:99-100`) |
| G5 | 잘렸으면 `truncated: true` | (a) "nothing pretends to have read the whole graph" (`graph-memory.md:358-360`) |
| G6 | global은 summary가 2개 이상인 level 우선 | (a) "a one-summary "global" map is not global" (`globalqa.go:184-188`) |

### 저장

| # | 결정 | 이유 | 대안·이력 |
|---|---|---|---|
| D1 | 파일이 진실, DB는 다시 짓는 색인 | (a) "The database is a rebuildable index; **files are the truth**" (`storage-backends.md:62`) | — |
| D2 | 쓰기 프로세스 하나 | (a) SQLite `_txlock=immediate`: "Waiting at begin is safer than failing mid-callback" (`db.go:33-39`). Postgres도 "deliberately keeps single-writer-process semantics" (`storage-backends.md:103-112`) | `SELECT … FOR UPDATE` 다중 writer는 "out of scope" |
| D3 | 인터페이스 seam, 구현은 별 패키지 | (a) "that direction would close an import cycle" (`store/types.go:1-5`); CHANGELOG: "server-grade multi-user deployments" (`CHANGELOG.md:1126-1131`) | `37d4e2c`(2026-07-21). commit 제목 "verification waived per user" — Postgres 적합성 매트릭스는 이 commit 시점에 검증 안 됨, `021db37`에서 녹색 |
| D4 | vector는 BLOB + 순수 Go | (a) "pure Go, no sqlite-vec" (`db.go:285`); CHANGELOG "pure Go via pgx/v5 stdlib, `CGO_ENABLED=0` preserved" (`CHANGELOG.md:1130`) | sqlite-vec 확장 |
| D5 | 메모리 행렬 캐시 기본, HNSW는 선택 | (a) "~11× faster than per-query SQLite scans at 10K+ chunks" (`search-quality.md:107-109`); "brute-force exact search stays the default" (`search-quality.md:117-118`) | — |
| D6 | coder/hnsw를 vendored·수정 | (a) "`heap.Max()` returns the last array slot of a MIN-heap … recall@10 vs exact brute-force was 0–4/10" (`vectors/hnsw/VENDORED.md`); ef=200 이유 `ann.go:34-39` | upstream 그대로 |
| D7 | `entity_aliases`는 쌍 키, FK 없음 | (a) "A single-column key cannot hold rejections"; "A row whose endpoints no longer exist is a fact to report, not one to erase" (`db.go:619-635`) | 단일 키(원 spec) |
| D8 | alias가 만든 edge는 `derived_relations`에 따로 | (a) "a copy is indistinguishable from an original — which is why a link could never be undone" (`db.go:661-666`, decision-035) | 이전엔 `relations`에 복사 |
| D9 | `output_index` hash를 마지막에 기록 | (a) "a crash mid-reindex never leaves a row that looks indexed but is partial" (`output_index.go:47-49`) | manifest 입력 hash와 비교 |
| D10 | embedding은 lock 밖에서 계산 | (a) "network calls must not block other writers" (`reconcile.go:273-274`) | — |
| D11 | 긴 입력은 잘라 평균 | (a) "5000 runes ≈ 4K tokens, leaving headroom for 8K-token limits" (`embed.go:243-247`) | — |
| D12 | 잘린 200 응답도 재시도 | (a) 이슈 #114: "a proxy truncating the embedding response is transient flakiness" (`embed.go:552-556`) | — |

### lint·learning·scribe

| # | 결정 | 이유 |
|---|---|---|
| L1 | lint 전 pass가 LLM 없음 | 모르는 것: lint 전체에 대한 명시 이유는 못 찾았다. 관련 근거는 이슈 #97 제목 "Zero-LLM article quality scorer"(`35169fc`)뿐이다. [추정] 매 실행 비용을 0으로 두려는 것이다(사례: quality pass가 compile 때 매긴 점수를 읽기만 함 1건, `passes.go:430-431`) |
| L2 | learnings 500개, 180일 | 모르는 것: 수치 근거 없음(`learning.go:11-14`). 커밋 `4876ddb`(초기 구현)부터 있다 |
| L3 | scribe는 kebab-case ID 없으면 entity 아님, 세션당 10개 | (a) "No ID = not specific enough to be an entity" (`session.go:292-294`); "Based on @andreasbauer80's proven pattern" (`session.go:68-71`) |

## 이 갈래에서 찾은 문제

실행하지 않고 코드로만 본 것이다. 재현하려면 해당 경로를 돌려 봐야 한다.

| # | 관찰 | 근거 | 영향 |
|---|---|---|---|
| P1 | 강화 Q&A 경로는 summary 문서를 문맥에 넣지 않는다. summary의 DocID는 raw 경로 그대로인데 `docIDToArticlePath`는 `concept:`/`summary:`/`output:`/`src:`만 알아 빈 문자열을 돌려주고, 호출부는 빈 경로를 건너뛴다 | ID: `fullpipeline.go:246-251`; 변환: `query.go:600-618`; 건너뜀: `query.go:325-327`. `summary:` 접두어로 색인하는 곳은 레포에 없다(`grep '"summary:'` 결과 `query.go` 2곳뿐) | summary가 검색 상위여도 Q&A 문맥에서 빠진다. 문서 단위 fallback은 `r.ArticlePath`를 써서 넣는다(`query.go:505`) |
| P2 | `src:` 문서는 raw 파일을 `os.ReadFile`로 그대로 읽는다. PDF·DOCX면 바이너리 앞 16000바이트가 문맥에 들어갈 수 있다 | `query.go:329-337, 614-616`; 테스트가 `src:raw/papers/paper.pdf`→raw pdf 경로를 기대(`query_test.go:81`) | [추정] 추출된 텍스트(`entries.content`)를 쓰지 않아 생긴다(사례: index 경로는 추출 텍스트를 색인 1건, `index.go:50-64`) |
| P3 | trust 승격 색인에 embedder가 전달되지 않아 승격된 답에 vector·청크 vector가 안 생긴다 | `IndexStores{…}`를 만드는 4곳 모두 `Embedder` 필드가 없다: `query.go:701-705`, `cmd/sage-wiki/trust_cmd.go:279-285, 309-315`, `compiler/pipeline.go:563-566`. `promote.go:72, 107`은 nil이면 건너뜀 | `verified` 모드에서도 승격 답은 BM25로만 찾힌다 |
| P4 | 답의 `derived_from` edge 대상은 인용 파일의 basename이다. summary·raw 경로면 entity가 없어 FK로 실패하고 오류는 무시된다 | `query.go:794-803`, `promote.go:89-97`; FK `db.go:307-308`, `foreign_keys=ON` `db.go:50` | 답→근거 그래프 연결이 concept article 인용에만 생긴다 |
| P5 | `query.Query`는 `app.Open`의 backend 핸들 위에 SQLite 전용 store(`memory.NewStore`, FTS5 `MATCH`, `bm25()`)를 새로 만든다 | `query.go:213-220`, SQL `entries.go:158-164` | [추정] Postgres 백엔드에서 `sage-wiki query`·`wiki_query`가 실패한다(사례: 검색 어댑터는 `s.backend.Chunks()`로 backend store를 쓰는데 query는 안 씀 1건, `mcp/server.go:341-346`). 돌려 확인하지 않았다 |
| P6 | 문맥 토큰 어림이 `len(bytes)/4`라 한글은 실제보다 작게 센다. 문서 자르기도 바이트 단위라 UTF-8 글자 중간에서 끊길 수 있다 | `query.go:335-338`; 비교: `extract.EstimateTokens`는 한글 1자=1.5토큰(`extract.go:111-121`) | 한글 문서면 8000토큰 예산의 약 2배가 들어갈 수 있다[추정, 계산만 함: UTF-8 한글 3바이트/4=0.75 vs 1.5] |
| P7 | graph 채널은 차수 감쇠가 없다. seed가 허브면 이웃들이 모두 같은 점수(1/w)를 받고 ID 알파벳순으로 `limit×5`개가 잘린다 | `graphleg.go:178, 202-222` | 범용어 허브가 graph 채널 상위를 알파벳순으로 채운다 |
| P8 | `chunks_meta.start_offset/end_offset` 열이 있으나 색인 경로가 채우지 않는다 | `ChunkEntry` 생성부 4곳(`query.go:832-837`, `index.go:288-293`, `reconcile.go:336-341`, `promote.go:120-125`) 모두 offset 없음 | 청크가 원문 위치를 가리키지 못한다 |
| P9 | `writeUnderReviewFile`이 따옴표를 먼저 `\"`로 바꾼 뒤 `%q`로 다시 감싸 이중 이스케이프된다 | `trust/hooks.go:378, 390` | under_review frontmatter의 질문 문자열이 원문과 달라진다 |
| P10 | 문서 주장 "Graph expansion is applied **before** both … sub-functions"와 달리 강화 경로는 검색 **뒤**에 확장을 계산한다 | `search-quality.md:86` vs `query.go:288-292` | 문서 정확성 문제 |

## 앞선 schema-glossary 보고서와 어긋나는 점

대상: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/reports/schema-glossary/sage-wiki-ontology.md`.

1. **청크 대상(C축).** 앞선 보고서는 "잘리는 대상은 raw가 아니라 컴파일된 wiki 문서(article)다"라고 썼다. 코드상 tier 1 색인이 raw 원문도 `src:<path>:c<i>` 청크와 청크 vector로 넣는다(`internal/compiler/index.go:273-298`). summary·output도 청크된다(`reconcile.go:277, 330-358`, `query.go:805-855`). `reindex` 문서도 "plus raw sources indexed as `src:<path>`"라고 적는다(`search-quality.md:238-240`). 원문 위치를 가리키지 않는다는 결론은 맞다(P8).
2. **Adamic-Adar의 자리(F축, 가져올 것 5).** 앞선 보고서는 Adamic-Adar를 "검색 점수"의 허브 감쇠로 소개했다. Adamic-Adar는 Q&A 문맥에 article을 덧붙이는 `graph.ScoreRelevance`에만 있다(`relevance.go:201-246`, 호출 `query.go:972-1009`). 검색 순위의 graph 채널(`graphleg.go`)은 차수 감쇠가 없다(P7). 그래서 "순위 단계에서 허브를 누그러뜨린다"는 장치는 sage-wiki의 검색 결과 목록에는 적용되지 않는다.
3. **`cites` 가중 0으로 끄기.** 맞다(`graphleg.go:29-41`). 다만 채널 전체의 `hybrid_weight_graph: 0`은 끄기가 아니라 기본값 0.2다(`search-quality.md:305-308`, `pipeline.go:399-402`).
4. **별칭과 검색(B축).** 앞선 보고서는 별칭을 추출·정규화 쪽에서만 다뤘다. 검색 쪽에서도 쓰인다. concept article의 FTS tags에 별칭이 들어가 1.5배 가중으로 걸리고(`write.go:390`, `entries.go:159`), graph 채널은 applied alias를 canonical로 해석한다(`graphleg.go:125-135`). pending alias는 순위에 쓰이지 않는다(S7).
5. **근거 수치(H축).** 검색 채널 조합에 대해서도 수치가 없다. `eval/benchmarks/retrieval_ab.py`는 두 바이너리를 비교하는 도구일 뿐이고(`retrieval_ab.py:1-22`), `eval/benchmarks/results/`의 10개 파일은 LOCOMO·LongMemEval·BEAM 종단 결과다. graph 채널 가중·rerank·확장의 ablation 결과 파일은 찾지 못했다.

## 엔터프라이즈 다중 작성자 용도에 비춰

사용자 조건은 작성자마다 같은 대상을 다른 용어로 쓰고, 문서가 형식을 갖추지 않을 때가 있다는 것이다.

### 쓸 만한 장치

| 장치 | 왜 쓸 만한가 | 근거 |
|---|---|---|
| raw도 청크·vector로 바로 검색 | 컴파일 품질과 무관하게 형식 없는 원문이 검색된다. "raw를 잇는 구조"의 바닥이 된다 | `index.go:273-298` |
| 3채널 RRF + 채널별 순위 노출(`BM25Rank/VectorRank/GraphRank`) + 호출별 `channels` ablation | 용어가 달라 BM25가 놓친 문서를 vector가, 둘 다 놓친 것을 graph가 잡는다. 어느 채널이 찾았는지 결과마다 보여 진단이 쉽다 | `pipeline.go:243-262`, `search-quality.md:284-296` |
| 별칭을 FTS tags에 넣기 | 사람이 승인한 용어집 없이도 "다른 이름으로 검색 → 정식 article"이 된다. 사내 용어집을 여기 넣는 변형이 쉽다 | S21 |
| applied alias만 순위에 반영 | 사람이 승인하기 전 추측이 검색 결과를 바꾸지 않는다 | S7 |
| 답 격리 + 반복 질의 consensus + conflict 상태 | 같은 질문에 다른 답이 나오면 conflict로 드러난다. 작성자마다 말이 다를 때 모순을 발견하는 장치로 쓸 수 있다 | `hooks.go:328-348` |
| 인용 파일 hash가 바뀌면 답 강등 | 보고서가 갱신되면 그걸 근거로 한 답이 자동으로 재검증 대상이 된다 | T6 |
| GraphQA의 edge 번호 인용 + `as_of` | 관계 질문에 근거 문서·신뢰도·유효 기간이 붙어 나온다. "언제 기준 사실인가"를 물을 수 있다 | G1, `serialize.go:172-181` |
| connections lint | vector가 비슷한데 edge가 없는 쌍을 사람에게 보여 준다. "새·기존 연결고리 발견"의 검토 대기열 원형이다 | `passes.go:224-292` |
| `IncludeDoc` 술어 seam | 문서 단위 권한 필터를 꽂을 자리가 이미 있고, over-fetch까지 붙어 있다 | `run.go:87-91, 141-148, 299-307` |
| `source_date` 우선순위(frontmatter `date:` > mtime > 처음 본 시각) | 내보내기·복원으로 mtime이 틀린 사내 문서를 frontmatter로 바로잡을 수 있다 | `search-quality.md:267-278` |
| 파일이 진실, DB는 재구축 | 저장소를 바꾸거나 망가져도 파일에서 다시 짓는다 | D1 |

### 걸리는 점

| 걸림 | 내용 | 근거 |
|---|---|---|
| 권한 | 접근 제어는 bearer token 하나로 전부 열리거나 닫힌다. 문서·사용자별 ACL은 찾지 못했다(찾아본 곳: `docs/guides/{serve-mode,self-hosted-server,team-setup}.md`의 token·permission·role 검색). trust 상태도 wiki 전체에 하나다 | `serve-mode.md:28-39`, `self-hosted-server.md:85-97` |
| 쓰기 동시성 | writer 프로세스 하나. 여러 사람이 동시에 넣으면 serve 모드의 FIFO compile 큐로 줄을 선다 | D2, `serve-mode.md:73-76` |
| 한국어 BM25 | `porter unicode61` 토큰화는 조사를 떼지 않는다. 질의어가 토큰의 앞부분이면(`보고서`→`보고서를`) prefix 질의로 걸리지만 반대는 안 걸린다 | `db.go:280-283, 543-547`, `entries.go:240-246`. [추정] 형태소 분석 없이 재현율이 낮다(사례: 레포 문서 "CJK recall is comparably limited on both backends" 1건, `storage-backends.md:72-73`) |
| 한국어 식별자 | 답 파일명 slug는 한글을 버려 `output`으로 떨어진다. scribe는 한글 ID를 kebab-case가 아니라며 버린다. graph seed는 entity ID 정확 일치라 한국어 concept ID 규칙에 좌우된다 | `query.go:1047-1062`, `hooks.go:398-419`, `session.go:336-341`, `graphleg.go:63-80` |
| 영어 불용어만 | 불용어 목록이 영어뿐이다. DF pruning(20%)이 한국어 범용어를 일부 대신한다 | `entries.go:309-319`, `entries.go:253-287` |
| consensus 전제 | 같은 질문이 3번 이상 반복돼야 자동 승격된다. 사내 보고서 질의는 반복이 드물 수 있다 | `hooks.go:312-313`, `ShouldAutoPromote` `consensus.go:140-145` |
| grounding 대상 | 검증 passage가 raw가 아니라 컴파일된 article 전체다. LLM이 쓴 글로 LLM 답을 검증한다 | `verify.go:121-141`, `query.go:323-344` |
| graph 허브 | 검색 graph 채널에 차수 감쇠가 없다(P7). 범용어가 entity가 되면 그 이웃이 알파벳순으로 채널을 채운다 | `graphleg.go:202-222` |
| lint 깊이 | 사실 모순은 `contradicts` edge가 이미 있을 때만 나열한다. 문서끼리 수치가 다른 것을 찾는 pass는 없다 | `passes.go:190-214` |
| 서버 캐시 | 다른 프로세스가 쓴 vector는 서버 재시작 전까지 안 보인다 | `search-quality.md:109-113` |

## 모르는 것

| 질문 | 볼 곳 |
|---|---|
| 기본 가중 0.7/0.3/0.2, rerank 혼합 75/60/40, connections 0.7, learnings 500·180일을 고른 근거 | 비공개 ADR-036~039, `decisions.md`(레포 `sage/` 아래, gitignore). 작성자에게 묻거나 PR 본문(`gh pr view`) 확인 |
| graph 채널이 실제로 재현율을 올리는가 | graph 채널 on/off로 `eval/benchmarks/retrieval_ab.py`를 돌린 결과. 레포에 없음 |
| P5: Postgres에서 `sage-wiki query`가 도는가 | `TEST_DATABASE_URL`로 `internal/query` 테스트를 돌리거나 Postgres vault에서 `query` 실행 |
| P1: summary가 Q&A 문맥에서 빠지는 것이 의도인가 | 작성자 확인. 의도라면 `summary:` 분기(`query.go:606-609`)가 왜 남았는지 |
| P3: 승격 답에 vector가 없는 것이 의도인가 | `verified` 모드에서 승격 후 `vec_entries`에 `output:` 행이 있는지 조회 |
| 사내 규모(수만 문서)에서 consensus의 질문 vector 전수 비교 비용 | `pending_questions_vec` 크기별 `FindSimilarQuestion` 시간 측정(`consensus.go:26-75`) |
| 한국어 질의의 BM25·graph 재현율 | 한국어 코퍼스로 `--channels bm25`, `--channels graph` ablation |
| hub federated search가 trust·ACL을 어떻게 다루는가 | `internal/hub/search.go` (이 갈래 범위 밖) |
| citation 검증(#144/#145)의 결론 | 이슈 #144는 OPEN. "verification substrate = exact quoted spans (footnote-style `[^n]`)"이 작성자의 현재 방향이다. 후속 spec·PR 확인 |

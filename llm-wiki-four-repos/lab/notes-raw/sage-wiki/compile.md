# sage-wiki compile 갈래 노트

대상은 xoai/sage-wiki, HEAD `d3ef3a1`(2026-10-03), MIT 라이선스다. 파일:줄은 레포 루트 기준이다. 코드는 실행하지 않았고 읽기 전용 git·gh·grep만 썼다.
표기 규칙은 이렇다. 작성자가 밝힌 이유는 원문을 큰따옴표로 인용한다. 코드 읽기로 추론한 것은 `[추정]`을 앞에 달고 문장 끝 괄호에 사례와 개수를 붙인다. 근거가 없으면 `모르는 것:`으로 적는다.

## 0. 범위

끝까지 읽은 파일과 훑은 파일을 나눈다.

| 구분 | 파일 |
|---|---|
| 끝까지 읽음 | `internal/compiler/{fullpipeline,summarize,concepts,dedup,evidence_gate,curate,write,extract_triples,communities,tiers,ondemand,reextract,confidence,diff,compilekey}.go`, `internal/compiler/pipeline.go`(1-2040 전부), `internal/compiler/resolve_entities.go`(1-1649 전부), `internal/manifest/manifest.go`, `internal/extract/split.go`, `internal/extract/extract.go:1-240`, `internal/prompts/templates/*.txt`(capture·caption 제외), `internal/prompts/untrusted.go`, `docs/determinism.md`, `docs/guides/{configurable-relations,customizing-prompts,large-vault-performance,local-models}.md` |
| 훑음 | `internal/compiler/{skip,items,index,backpressure,docbudget,worker,worker_cycle,watch,coordinator,images,typedetect,summary_path}.go`, `internal/manifest/merge.go`, `internal/prompts/{prompts,versions}.go`, `internal/ontology/{ontology,entities,relations,aliases}.go`(관련 함수만), `internal/sourcedate/sourcedate.go`(함수 머리말만), `internal/pack/`(bundled pack.yaml 2개, merge.go의 prompts 복사 부분), `internal/llm/{client,structured}.go`(재시도 부분만), `internal/graph/community/louvain.go`(머리말만), `internal/storage/db.go:50,305-317` |
| 읽지 않음 | `internal/compiler/{backfill,reembed,migrate_checkpoint,batch_state,progress,walk,source_path}.go`, `internal/extract/{pdf,office,email,epub,external}.go`, `internal/ontology/{temporal,derived,community,article,events}.go` |

다른 갈래와 겹치는 곳은 경계만 적는다. 검색·질의(`internal/search`, `internal/graph/relevance.go`, `internal/query`), 그래프 저장소 세부(`internal/ontology/aliases.go`의 derived edge, temporal), LLM 클라이언트·provider(`internal/llm`), 서버·MCP(`internal/serve`, `internal/mcp`)는 다른 갈래 몫이다.

## 1. 구조

### 모듈 지도

진입점은 다섯 개이고, LLM 패스 본체는 `runFullPipeline` 하나를 공유한다. 예외는 batch 재개와 re-extract로, 이 둘은 패스 일부를 따로 조립한다.

| 진입점 | 위치 | 부르는 것 |
|---|---|---|
| CLI `sage-wiki compile` | `internal/compiler/pipeline.go:291` `Compile` | `loadInputs`(760) → `Diff`(diff.go:41) → `runSkipClassification`(skip.go) → `resolveMode`(870) → `setupStores`(915) → `runTiers`(1046) → `runFullPipeline`(fullpipeline.go:139) → 꼬리 처리(497-591) |
| batch 제출·재개 | `pipeline.go:1300` `submitBatch`, `:1447` `resumeBatch` | Pass 1만 batch API로 보내고, 재개 때 Pass 2·3을 직접 조립한다 |
| compile-on-demand (MCP `wiki_compile_topic`) | `internal/compiler/ondemand.go:68` `CompileTopic` | hybrid 검색 → tier 3 승격 → `runFullPipeline` |
| `--re-extract` | `internal/compiler/reextract.go:38` `ReExtract` | 디스크의 summary 파일 → Pass 2·2b·3·4·communities |
| serve worker | `internal/compiler/worker_cycle.go` | 큐 claim → 같은 파이프라인(훑음) |

`runFullPipeline` 안의 호출 순서는 이렇다(fullpipeline.go).

```
Summarize(summarize.go:65)                      Pass 1
ExtractConcepts(concepts.go:82)                 Pass 2
  filterNoisyConcepts / deduplicateConcepts
DedupCache.CheckDuplicate(dedup.go:125)         임베딩 dedup (dedup_strategy != llm)
filterLowEvidence(evidence_gate.go:13)          evidence gate
maybeCurateConcepts(curate.go:261)              LLM curation (dedup_strategy == llm)
mf.AddConcept                                   manifest 갱신
ExtractTriplesPass(extract_triples.go:614)      Pass 2b (opt-in)
WriteArticles(write.go:93)                      Pass 3
ScoreArticle(confidence.go:86) / RetryArticle   품질 점수, 선택적 재작성
defer: ResolveEntitiesPass(resolve_entities.go:614)  Pass 4 (opt-in)
       runSupersessionSweep(extract_triples.go:414)
       CommunitiesPass(communities.go:29)            (opt-in)
```

### 핵심 자료 구조

| 구조 | 위치 | 필드 | 역할 |
|---|---|---|---|
| `SourceInfo` | `internal/compiler/diff.go:33` | Path, Hash(`sha256:`+hex), Type, Size | Diff가 만든 소스 한 개 |
| `DiffResult` | `diff.go:19` | Added, Modified, Removed, Unchanged, Reason | Pass 0 결과. Reason은 "content", "incomplete (resume)", "forced", drift 종류 |
| `SummaryResult` | `internal/compiler/summarize.go:23` | SourcePath, SummaryPath, Summary, Concepts, ChunkCount, Error, Cancelled | Pass 1 결과. Cancelled는 실패도 성공도 아니다 |
| `ExtractedConcept` | `internal/compiler/concepts.go:20` | Name, Aliases, Sources, Type | Pass 2 결과이자 Pass 3 입력 |
| `manifest.Concept` | `internal/manifest/manifest.go:80` | ArticlePath, Sources, Aliases, LastCompiled | `.manifest.json`의 concept. Sources·Aliases는 합집합으로만 늘어난다(manifest.go:220-237) |
| `manifest.Source` | `manifest.go:65` | Hash, Type, SizeBytes, AddedAt, SummaryPath, ConceptsProduced, Tier, SourceType 등 | 소스 기록. CompiledAt·Status는 deprecated |
| `CompileItem` | `internal/store/domain.go:287` | SourcePath, Hash, Tier, TierDefault, TierOverride, Pass{Indexed,Embedded,Parsed,Summarized,Extracted,Written}, ErrorCount, QueryHitCount, LastQueriedAt, CompileKey, CompileKeyParts, QualityScore, 큐 상태(status·lease·attempts) | SQLite `compile_items` 표. 증분·tier·큐·compile key가 모두 여기 산다 |
| `CompileKeyParts` | `internal/compiler/compilekey.go:28` | Source, Pipeline, Templates, Models, Config, Embed | compile key의 구성 요소. drift 원인 설명에 쓴다 |
| `ExtractedGraph` | `internal/compiler/extract_triples.go:49` | Entities{Name,Type,Description}, Relations{Source,Predicate,Target,Evidence,Confidence} | Pass 2b 결과 |
| `store.Entity` | `domain.go:86` | ID, Type, Name, Definition, ArticlePath, CreatedAt, UpdatedAt | 그래프 노드 |
| `store.Relation` | `domain.go:96` | ID, SourceID, TargetID, Relation, Evidence, Confidence, SourceDoc, ValidFrom, ValidTo, InvalidatedBy | 그래프 엣지. Evidence는 raw가 아니라 summary에서 인용한다(domain.go:105-109) |
| `store.EntityAlias` | `domain.go:144` | Alias, CanonicalID, EntityType, Status(pending/applied/rejected), Confidence, Reason, Source(llm/manual), CreatedAt, DecidedAt, DecidedBy(auto/user) | resolution 제안·결정 감사 기록 |
| `articlePayload` | `internal/compiler/write.go:191` | concept, articlePath, content, entityType, conceptVec, chunks, chunkEmbeddings | Pass 3 병렬 준비 결과. 저장은 나중에 순서대로 한다 |

저장 위치는 세 곳이다. 파일은 `wiki/summaries/*.md`, `wiki/concepts/<name>.md`, `wiki/communities/*.md`, `wiki/CHANGELOG.md`다. 상태는 `.manifest.json`과 `.sage/wiki.db`(SQLite: FTS5, 벡터, chunk, entities·relations·entity_aliases, compile_items)에 있다.

## 2. 동작 흐름

### 단계표

| 단계 | 입력 | 처리 | 출력 | LLM 호출과 프롬프트 | 결정적 검사 | 실패 처리 |
|---|---|---|---|---|---|---|
| Pass 0 Diff | `config.yaml`의 sources, manifest | 소스 디렉터리를 걸으며 SHA-256 해시와 type을 구해 manifest와 비교한다(diff.go:41-153) | Added/Modified/Removed, 경로순 정렬(diff.go:135-144) | 없음 | 숨김 파일·ignore 패턴 제외(diff.go:57, 174-200). type이 바뀌어도 Modified(diff.go:119-130) | 해시 실패 파일은 경고 후 건너뜀 |
| skip 분류 | compile_items, DiffResult | compile key로 R0 재개 → R1 force → R2 내용 변경 → R3 채택 → R4 skip → R5 drift를 가른다(docs/determinism.md:88-94, skip.go:64-) | drift·재개 문서를 Modified에 더함(pipeline.go:391-396) | 없음 | key = SHA-256(소스 해시, PipelineVersion, 템플릿 해시, pass별 모델, 출력 영향 config 부분집합, 임베딩 식별자)(compilekey.go:45-55) | `max_compile_batch`(기본 1000, internal/limits/limits.go:20)를 넘으면 처리 전에 typed error(pipeline.go:407-424) |
| tier 배정·claim | Added+Modified | tier를 정하고 compile_items에 upsert한 뒤(pipeline.go:1280-1295) tier 0, 1, 3 순서로 lease를 잡는다(pipeline.go:1082-1147) | toProcess(tier 3만) | 없음 | tier 우선순위: `.wikitier` > `tier_defaults[확장자]` > `default_tier`(tiers.go:33-74) | lease 5분, heartbeat 30초(pipeline.go:222-226). 실패 5회면 dead letter(worker.go:35, worker_cycle.go:489-504) |
| Tier 0/1 | claim된 소스 | 원문을 FTS에 `src:<path>`로 넣고(index.go:60-65), tier≥1은 원문 chunk를 임베딩한다(index.go:100-) | FTS, `src:<path>:c<i>` chunk 벡터 | 없음 | 코드 파일은 정규식·go/ast 파서로 구조 요약을 붙인다(index.go:49-58) | 추출 실패는 MarkError |
| Pass 1 summarize | 소스 1개 | 같은 source_hash를 가진 기존 summary가 100자 이상이면 재사용한다(summarize.go:203-236). 아니면 `extract.Extract`로 텍스트화하고 `maxTokens*2` 넘으면 chunk로 나눈다(summarize.go:259-261) | `wiki/summaries/<이름>.md`(frontmatter: source, source_type, source_hash, compiled_at, chunk_count; summarize.go:351-359), FTS, summary 벡터 | 단일 chunk: 1회, `summarize_<type>.txt` 없으면 `summarize_article.txt`(summarize.go:264-267). 여러 chunk: 그룹당 1회 + 8개씩 계층 합성(summarize.go:414-416, 531-580). 이미지: vision 1회, 인라인 프롬프트(summarize.go:387) | 빈 응답 거부(summarize.go:326-331), 100자 미만 거부(summarize.go:336-342) | 연속 5회 실패면 나머지를 건너뛴다(summarize.go:155-160). 429면 backpressure가 동시성을 반으로 줄인다 |
| Pass 2 concept 추출 | 성공한 summary 전체, manifest concept 이름 | 20개씩 묶어(concepts.go:98-138) summary 앞 1000바이트만 넣는다(concepts.go:182-184) | `[]ExtractedConcept` | 묶음당 1회, `extract_concepts.txt`, structured output `ConceptsSchema`(concepts.go:474-498, enum 없음) | 잡음 필터: 2바이트 미만, `$`·`\`, 숫자만, `/`·`.md` 포함(concepts.go:270-304). 정규화 이름 일치와 별칭 겹침으로 접기(concepts.go:318-471) | 일부 묶음 실패는 `PartialFailureError`로 실패 문서를 이름까지 남기고 계속한다(concepts.go:68-80, 250-263). 전부 실패하면 Pass 3를 건너뛴다(fullpipeline.go:300-306) |
| 임베딩 dedup | 추출 concept, manifest concept 이름 | concept **이름**을 임베딩해 기존 이름과 cosine ≥ 0.85면 기존 concept에 합친다(dedup.go:125-167, fullpipeline.go:318-353) | 합쳐진 concept은 manifest Sources·Aliases에만 더해지고 Pass 3 목록에서 빠진다(evidence_gate.go:35-60) | 없음(임베딩 API만) | never-merge: 숫자 토큰 집합이 다르거나 draft/final, primary/secondary 한쪽만 있으면 합치지 않는다(dedup.go:169-239) | 합칠 때마다 WARN 로그(fullpipeline.go:331-334) |
| evidence gate | concept 목록 | `len(Sources) < min_concept_sources`(기본 1)면 버린다(evidence_gate.go:13-28, internal/config/config.go:424-429) | 남은 concept | 없음 | 위 조건 자체 | 버린 것은 INFO 로그 |
| curation (opt-in) | concept 목록, manifest 이름 전체 | `dedup_strategy: llm`일 때만 임베딩 dedup 대신 돈다(fullpipeline.go:318, curate.go:270) | keep/fold/drop 적용 결과 | 200개 묶음당 1회, `curate_concepts.txt`, `CurateSchema`(action에 enum 있음, curate.go:42) | fold도 never-merge가 거부권을 갖는다(curate.go:162-167). 대상을 못 찾으면 keep(curate.go:211-213). drop은 `allow_drop`일 때만(curate.go:125-131) | 전부 실패해도 오류 1건만 세고 curation 없이 진행(fullpipeline.go:362-367) |
| Pass 2b triple (opt-in) | 성공한 summary, 이번 concept | 문서당 엔티티·관계를 뽑아(extract_triples.go:111-152) 어휘 검증(175-291), evidence 부분 문자열 검증(905-952) 후 저장(447-580) | entities, relations(evidence, confidence, source_doc, valid_from) | 문서당 1회, `extract_triples.txt`, `TriplesSchema`(enum 없음, 54-102) | 모르는 type → concept, 모르는 술어 → 엣지 버림, 자기 루프·끊긴 끝점 버림, 문서당 엔티티 40·관계 60 상한(587-591), confidence 바닥 0.1(161) | 컴파일을 절대 실패시키지 않는다(596-601). 실패 문서는 세고 로그만 남긴다 |
| Pass 3 문서 작성 | concept 목록, manifest 전체 | concept마다 raw 원문에서 맥락을 모아(write.go:1080-1188) 기존 문서와 함께 프롬프트에 넣는다(write.go:212-249) | `wiki/concepts/<name>.md`, entity 행, `cites` 엣지, 키워드 관계 엣지, FTS, 문서 벡터, 문서 chunk | concept당 1회, `write_article.txt` | 코드가 frontmatter를 만든다(write.go:465-491). 바깥 코드펜스·LLM frontmatter 제거, anti-pattern 문장 제거, `[[별칭]]`을 정식 이름으로 바꿈(write.go:264-286) | 개별 실패는 다음 컴파일에 다시 한다. 저장은 병렬 준비 뒤 입력 순서로 한다(write.go:86-187) |
| 품질 점수 | 쓴 문서, raw 원문 | LLM 없이 5개 차원을 잰다(confidence.go:86-104) | `compile_items.quality_score` | `quality.retry: true`면 0.5 미만 문서를 지우고 1회 다시 쓴다(fullpipeline.go:547-586) | format·grounding·coverage·wikilink·anti-pattern, 가중치 0.15/0.30/0.20/0.15/0.20(confidence.go:31-39) | 재작성 뒤에도 낮으면 컴파일 오류 1건 |
| Pass 4 resolution (opt-in) | 이번에 건드린 엔티티 id(touched) | 같은 type 안에서 후보 블록을 만들고(resolve_entities.go:466-532) LLM이 같은 대상인지 판정한다(1085-1117) | entity_aliases 행(applied 또는 pending), canonical로 복사된 derived edge | 블록당 1회, `resolve_entities.txt`, `ResolveSchema`(enum 없음) | canonical은 Go가 고른다(251-277). 자동 적용 조건 5개(323-345). 거절·대기 쌍은 전이 폐포까지 막는다(1301-1334) | 컴파일을 실패시키지 않는다. 승인된 링크 재적용(sweep)은 기능을 꺼도 돈다(608-613) |
| supersession sweep | 이번 functional 엣지 | resolution이 만든 별칭을 반영해 `InvalidateFunctional`을 다시 부른다(extract_triples.go:407-422) | valid_to 갱신 | 없음 | 이미 무효화된 행은 건드리지 않는다 | 실패는 경고 |
| communities (opt-in) | 그래프 전체 | 결정적 Louvain으로 4단계 계층을 찾는다(communities.go:58-79, internal/graph/community/louvain.go:1-4) | `wiki/communities/c<level>-<seq>.md`, FTS, 벡터 | 멤버 해시나 모델이 바뀐 community마다 1회, 인라인 프롬프트(communities.go:286-293) | `cites` 제외, 살아 있는 엣지만, 엣지 40줄 상한(communities.go:262-283) | 빈 요약은 다음 컴파일에 다시 한다(199-201) |
| 꼬리 처리 | 실행 결과 | 끊긴 wikilink 제거(pipeline.go:526-531), 삭제된 소스 처리(1965-2020), manifest 병합 저장(540-544), CHANGELOG, trust 재검증, git auto-commit | 저장 완료 | 없음 | Pass 2·3가 끝나지 않은 실행은 manifest를 저장하지 않는다(pipeline.go:540-541) | 다음 컴파일이 같은 소스를 처음부터 다시 처리한다 |

### Pass 3 원문 맥락은 어떻게 고르나

`buildSourceContext`(write.go:1080-1188)는 concept의 Sources 파일을 `os.ReadFile`로 그대로 읽는다(write.go:1093-1098). Pass 1과 달리 `extract.Extract`를 거치지 않는다.
문서가 `split_threshold`(기본 15000 rune)보다 짧거나 markdown heading이 없으면 절이 하나뿐이다(internal/extract/split.go:23-37). 이때는 문서 앞 4000바이트만 넣는다(write.go:1101-1112).
문서가 길고 heading이 있을 때만 concept 이름·표시명·별칭이 들어 있는 절을 고른다(write.go:1115-1141, split.go:86-98). 절마다 4000바이트에서 자른다.
모은 조각은 일치 수 → 경로 → 위치 순으로 정렬해 `max_source_context_tokens`(기본 100000) 안에서 자른다(write.go:1144-1182). 이 상한은 #146(concept `barium` 하나가 135만 토큰 요청을 만든 사례) 이후 들어왔다(commit `b049d7c`).

[추정] 형식 없는 사내 문서(heading 없음)나 15000자 미만 보고서에서는 concept이 문서 뒤쪽에만 나와도 작성자가 앞 4000바이트만 본다(사례: write.go:1101-1105와 split.go:24-36 두 분기 1건). 한국어는 글자당 3바이트라 약 1300자다.

[추정] PDF·DOCX 소스는 Pass 3에서 바이너리가 그대로 들어간다(사례: Pass 1은 `extract.Extract`로 PDF를 텍스트화하지만(summarize.go:240) Pass 3는 `os.ReadFile`(write.go:1094) 1건). 품질 점수용 원문도 같은 방식으로 읽는다(fullpipeline.go:537-541). 실행해 확인하지 않았다.

### 진입 경로별 차이

같은 패스라도 경로마다 빠지는 것이 있다.

| 경로 | 임베딩 dedup | curation | triple | resolution | communities | 품질 점수 |
|---|---|---|---|---|---|---|
| 표준 compile, on-demand | 있음 | 있음 | 있음 | 있음 | 있음 | 있음(ItemStore 있을 때) |
| batch 재개 | **없음**(pipeline.go:1719-1731) | 있음 | **없음** | **없음**(주석 pipeline.go:1805-1807) | 있음 | 없음 |
| re-extract | **없음**(reextract.go:140-156) | 있음 | 있음 | 있음 | 있음 | 없음 |

batch 제출은 단일 chunk·비이미지 소스만 보낸다. 주석은 "multi-chunk requires sequential synthesis"(여러 chunk는 순차 합성이 필요하다)라고 적는다(pipeline.go:1361-1365).
[추정] re-extract는 summary 파일명(`raw-paper.md`)을 SourcePath로 넘기므로(reextract.go:85-89) LLM이 돌려주는 concept Sources가 원문 경로가 아닌 summary 파일명일 수 있다(사례: reextract.go:85와 concepts.go:191의 `### Source: %s` 1건). 그러면 Pass 3가 원문을 못 읽는다. 실행해 확인하지 않았다.

### 문서 한 개당 LLM 호출 수

| 패스 | 호출 수 | 기본 상태 |
|---|---|---|
| Pass 1 | 1회, 또는 chunk 그룹 수 + 합성 호출 | 켜짐 |
| Pass 2 | 20개 summary당 1회(공유) | 켜짐 |
| curation | 200개 concept당 1회(공유) | 꺼짐 |
| Pass 2b | 문서당 1회 | 꺼짐(commit `a0f743e`) |
| Pass 3 | concept당 1회, 재작성 켜면 최대 2회 | 켜짐 |
| Pass 4 | 후보가 있는 seed 블록당 1회 | 꺼짐 |
| communities | 바뀐 community당 1회 | 꺼짐 |

임베딩 호출은 따로 있다. summary 1회, 문서 1회 + chunk 수만큼, dedup은 concept 이름마다 1회다.

### 실패·재시도 계층

| 층 | 장치 | 근거 |
|---|---|---|
| HTTP 호출 | 429·500·502·503과 잘린 200 응답을 최대 4회 재시도, 지수 backoff + jitter, 60초 상한 | `internal/llm/structured.go:52`, `internal/llm/client.go:546-560` (다른 갈래 영역, 훑음) |
| 동시성 | 429면 동시성 반감, 연속 5회 성공이면 두 배(최대 `max_parallel`) | `internal/compiler/backpressure.go:103-140` |
| 문서 단위 시간 | 문서별 `compile_doc_timeout`(기본 15분)은 그 문서의 Pass 1·2b 실행 시간만 잰다. 대기 시간은 빼고 잰다 | `internal/compiler/docbudget.go:16-20`, `internal/limits/limits.go:27` |
| 패스 내부 | summarize 연속 5회 실패 시 나머지 중단 | `summarize.go:155-160` |
| 실행 단위 | Pass 2·3 미완료면 manifest·compile_items를 저장하지 않아 다음 실행이 다시 한다 | `pipeline.go:1156-1161, 1206-1213, 540-541` |
| 큐 단위 | 실패 시 attempts+1, 5회면 failed(dead letter). `--fresh`가 dead letter를 되살린다 | `worker_cycle.go:489-504`, `pipeline.go:1010-1025`, `items.go:703-746` |
| 비용 | `MaxCost` 초과 시 패스 사이에서 멈춘다. 비용을 모르면(nil) 멈추지 않는다 | `fullpipeline.go:131-137, 268-273, 309-315` |

## 3. 증분·tier·비용 제어

### 증분

증분 판단은 세 겹이다.
첫째, Diff가 파일 해시와 type으로 바뀐 소스를 고른다(diff.go:119-130).
둘째, compile key가 내용은 같아도 파이프라인·템플릿·모델·config·임베딩이 바뀐 문서를 다시 넣고, 바뀌지 않은 문서는 LLM 호출 없이 건너뛴다(docs/determinism.md:66-96).
셋째, Pass 1은 frontmatter의 `source_hash`가 같으면 summary를 다시 사지 않는다(summarize.go:203-236). 주석은 "This is what makes an interrupted compile cheap to resume"(중단된 컴파일을 싸게 재개하게 해 주는 장치)라고 적는다.

concept 쪽 증분은 manifest 합집합이 맡는다. `AddConcept`는 Sources·Aliases를 덮지 않고 합친다(manifest.go:215-237). 주석이 이유를 적는다: "a replace would wipe accumulated evidence and, once aliases exist, the very aliases acronym dedup relies on"(덮어쓰면 쌓인 근거와 약어 dedup이 기대는 별칭이 지워진다).

[추정] 기존 concept과 이름이 정확히 같은 concept이 새 소스에서 다시 나오면, 문서 frontmatter의 `sources`는 이번 실행의 소스만 담는다(사례: deduplicateConcepts는 manifest **별칭**만 대조하고 이름은 대조하지 않으며(concepts.go:321-333) `buildFrontmatter`는 manifest 합집합이 아닌 `concept.Sources`를 쓴다(write.go:471) 1건). manifest에는 합집합이 남는다. 실행해 확인하지 않았다.

### tier

| tier | 처리 | 근거 |
|---|---|---|
| 0 | FTS 색인만 | `pipeline.go:1081-1105`, `index.go:27-73` |
| 1 | FTS + 원문 chunk 임베딩 | `pipeline.go:1107-1132` |
| 2 | 코드 구조 파싱(문서상). CLI는 tier 2 전용 claim을 하지 않고 tier 0·1 claim에서 같이 처리된다 | `items.go:590-603`, `index.go:144-150` |
| 3 | 전체 LLM 파이프라인 | `pipeline.go:1134-1243` |

기본 `default_tier`는 3이다(internal/config/config.go:1119). 대형 vault 가이드는 1로 내리라고 권한다(docs/guides/large-vault-performance.md:59-63).
승격은 검색 적중 수(기본 3)만 본다(tiers.go:79-91, items.go:398-417). 강등은 마지막 질의 뒤 90일이 지나면 tier 1로 내린다(tiers.go:96-111, items.go:422-445). compile-on-demand는 주제 검색 결과 중 tier 3 미완료 소스를 최대 20개 승격해 바로 컴파일한다(ondemand.go:71-153).

### 비용 제어 장치 목록

| 장치 | 기본값 | 근거 |
|---|---|---|
| tier와 on-demand | tier 3, 승격 적중 3회 | 위 표 |
| compile key skip | 항상 | `docs/determinism.md:88-96` |
| summary 재사용 | 항상 | `summarize.go:203-236` |
| batch API | `mode: auto`면 소스 10개 이상에서 batch | `pipeline.go:889-899` |
| prompt cache | 패스마다 system prompt 캐시 | `fullpipeline.go:152-154, 288-290, 454-456` |
| pass별 모델 | summarize·extract·write 따로, triple·resolve·communities도 따로 | `fullpipeline.go:157-160, 281-284, 443-446`, `docs/guides/local-models.md:9-14` |
| 상한 | summary 2000토큰, 문서 4000토큰, extract 8192토큰, 원문 맥락 100000토큰, 관련 concept 8개, dedup 캐시 5만, triple 40/60, resolve 블록 60·임베딩 후보 500 | `fullpipeline.go:161-164, 447-450`, `concepts.go:101-103`, `write.go:779`, `dedup.go:18`, `extract_triples.go:587-591`, `resolve_entities.go:105-113` |
| 실행 상한 | `MaxCost`, `MaxDocs`, `max_compile_batch` 1000, 문서별 15분 | `pipeline.go:68-73, 407-424, 1149-1154` |
| resolution 비용 | 이번에 건드린 엔티티만 seed, 후보가 없으면 호출 0회 | `resolve_entities.go:509-513` |
| communities 캐시 | 멤버 해시와 모델이 같으면 다시 요약하지 않음 | `communities.go:194-197` |

### 문서에는 있지만 코드가 쓰지 않는 tier 설정

`promote_signals`의 `cluster_size`, `manual_tag`, `import_centrality`, `source_recency_days`와 `demote_signals.source_modified`는 config와 compile key에만 나오고 동작 코드에서 쓰이지 않는다(grep `ClusterSize|ManualTag|ImportCentrality|SourceRecencyDays|SourceModified` 결과 config.go·compilekey.go 밖에서 0건). 가이드는 이 신호들로 승격한다고 적는다(large-vault-performance.md:117-131).
frontmatter `tier: 3` 덮어쓰기도 동작하지 않는다. 유일한 호출부가 frontmatter 자리에 nil을 넘긴다(pipeline.go:1283, tiers.go:30-41). 가이드는 우선순위 맨 앞에 frontmatter를 둔다(large-vault-performance.md:102-111).

## 4. 설계 결정과 이유

각 결정은 (a) 작성자가 밝힌 이유인지 (b) 추론인지를 표시한다. 대안과 이력 commit을 함께 적는다.

### 파이프라인 모양

**D1. raw → summary → concept → 문서의 다단 컴파일.** (b) [추정] 요약을 먼저 만들어 concept 추출 입력을 줄이고 한 호출에 20개 문서를 묶기 위해서다(사례: 묶음 크기 20 도입 commit `ca308e3`이 "batch 20 summaries per LLM call instead of all at once (was truncating JSON on large wikis like 1107 sources)"(한 번에 다 넣으면 1107개 소스 wiki에서 JSON이 잘렸다)라고 적은 것 1건). 대안은 raw에서 바로 concept을 뽑는 것이다. 작성자가 단계 구성 자체의 이유를 적은 곳은 찾지 못했다.

**D2. concept 추출은 summary 앞 1000바이트만 본다.** (b) [추정] 20개 묶음의 입력 토큰을 억제하려는 것이다(사례: 같은 commit `ca308e3`에서 묶음과 함께 도입 1건). 걸리는 점은 summary 템플릿이 `Concepts` 목록을 마지막 4번째 절에 두는 것이다(internal/prompts/templates/summarize_article.txt:11, summarize_paper.txt:12). [추정] summary가 1000바이트를 넘으면 concept 목록 절이 잘려 추출기에 닿지 않는다(사례: summary 상한 2000토큰(fullpipeline.go:161-164) 대비 1000바이트 1건). 바이트 단위 자르기라 한국어는 약 330자이고 글자 중간에서 끊길 수 있다.

**D3. 기존 concept 이름을 프롬프트에 넣되 별칭은 넣지 않는다.** (a) 정렬 이유는 적혀 있다: "SPEC-04 D1: sorted — map iteration order must not leak into prompt bytes"(concepts.go:123). 모든 묶음이 같은 스냅숏을 받는 이유도 적혀 있다: "each batch receives the same existingConcepts snapshot as dedup context (not the growing allConcepts), so deduplicateConcepts at the end handles cross-batch merging"(concepts.go:60-62). 별칭을 빼는 이유는 모르는 것이다. #167이 이 구조의 약점을 짚었다: "Every batch is therefore blind to what the other batches propose in the same run"(같은 실행의 다른 묶음이 무엇을 냈는지 모른다).

**D4. concept type은 프롬프트에서 concept·technique·claim 셋으로 고정한다.** (b) `extract_concepts.txt:18`이 세 개만 나열한다. config의 `entity_types`는 triple 프롬프트에만 들어간다(extract_triples.go:131-135). [추정] concept 문서의 `entity_type`은 사용자 정의 종류를 거의 갖지 못한다(사례: write.go:277-280이 LLM type을 통과시키지만 프롬프트가 셋만 알려 줌 1건). 이유는 모르는 것이다. 템플릿 버전 기록을 보면 알 수 있을지 모른다.

### dedup·별칭

**D5. 정규화 + 별칭 겹침 접기, 정식 이름은 더 긴 쪽.** (a) #128 이후 들어왔다(commit `1f91f98`, `7e9f0e9`). 주석: "Canonical = the longer normalized name (the expansion, not the acronym)"(정식 이름은 약어가 아닌 풀어 쓴 쪽)(concepts.go:423-424). 이슈 #128은 Caltrans 토양 정화 사업 문서에서 `wsp`, `rap`, `rdip` 같은 도면 범례 약어가 빈 문서가 된 사례를 들었다. 대안으로 #128이 제시한 것은 프롬프트 지시, 별칭 대조, 작성 전 근거 게이트, CLI 플래그 넷이었고 앞의 셋이 채택됐다.

**D6. 임베딩 dedup은 이름 cosine 0.85, 그 아래에 결정적 never-merge 규칙.** (a) #164가 이유를 측정값으로 적었다. "must-merge and must-not-merge pairs interleave across the whole range and peak at the same 0.982, so no threshold separates them"(합쳐야 할 쌍과 합치면 안 되는 쌍이 전 구간에 섞여 같은 0.982에서 정점을 찍어 어떤 threshold로도 가를 수 없다; commit `456e1d4` 메시지). 코드 주석: "the token carrying the meaning — a digit, a draft/final qualifier — is the least semantically weighted part of the string"(의미를 실은 토큰이 문자열에서 가장 가중치가 낮다)(dedup.go:179-184). 로그를 WARN으로 올린 이유: "an auto-merge deletes a concept as its own entity — that must be discoverable"(fullpipeline.go:331-333). 남은 한계도 적혀 있다: "same-number containment (stockpile-1 vs stockpile-1-mse-wall-footing) and synonym-media pairs (storm-water vs surface-water) remain threshold-governed"(commit `456e1d4`).

**D7. LLM curation은 임베딩 dedup과 둘 중 하나, opt-in, drop은 별도 허가.** (a) "either/or; running both is incoherent — embedding merges would pre-empt judgment"(둘 다 돌리면 임베딩 병합이 판단을 선점한다)(curate.go:19-21). 안전 기본값은 #167의 제안을 따랐다: "Reviewable before destructive", "Opt-in ... an upgrade must not raise anyone's bill unasked"(이슈 #167). 비용 논리: "Suppressing 200 unnecessary articles saves far more than the gate costs"(#167). 이력: 그전에는 `dedup_strategy: llm`이 dedup을 꺼 버리는 버그였다(commit `4c0a708`). 묶음 200은 #166의 출력 토큰 잘림 교훈이다(commit `4c0a708`).

**D8. evidence gate: 소스 0개 concept은 manifest·문서·엔티티·cites 모두에서 지운다.** (a) "A source-less concept is noise everywhere"(evidence_gate.go:10-12). #128 원문은 "unconditionally generates a full templated article regardless of `len(concept.Sources)`"(소스 수와 무관하게 문서를 쓴다)를 문제로 들었다. 대안이던 사후 confidence 필터는 택하지 않았다.

### 쓰기와 그래프

**D9. frontmatter는 코드가, 본문은 LLM이 쓴다.** (a) "Strip any LLM-generated frontmatter — code builds frontmatter from ground-truth data"(write.go:268). 가이드: "Ground-truth fields ... are always accurate — they come from the extraction pass, not the LLM"(customizing-prompts.md:91-92). LLM 판단 필드(`confidence`, `article_fields`)는 본문 마지막 15줄에서 `키: 값`을 긁어 온다(write.go:493-557).

**D10. "See also"는 공유 소스 수 상위 8개.** (a) #106이 원인이었다. 그전에는 관련 concept 함수가 빈 stub이라 140개 문서 wiki에서 문서의 85%가 고아였다. 상한 이유: "a source cited by many concepts would otherwise flood every article with links"(write.go:775-779). 공출현을 고른 이유: "it needs no embeddings, works on a cold compile, and yields real slugs that resolve to article files"(write.go:783-786). 대안으로 벡터 유사도는 "a follow-up"으로 남겼다(write.go:778).

**D11. 끊긴 wikilink는 컴파일 끝에 지운다.** (a) #90 측정: 111개 문서에서 wikilink 대상 841개 중 23개만 실제 문서였다. 주석: "Pass 2 extracts concepts conservatively, so a wiki of a non-ML corpus can end up with the majority of links being phantom"(pipeline.go:526-530). #90이 제시한 세 대안(목록 제약, 사후 제거, stub 생성) 중 사후 제거와 (#106으로) 목록 제공을 택했다. stub 생성은 택하지 않았다.

**D12. 키워드 관계 엣지: 같은 문단에 `[[링크]]`와 동의어가 있으면 엣지.** (a) "This prevents spurious edges from cross-paragraph matches"(configurable-relations.md:107-110). 내장 동의어는 영어와 중국어뿐이다(internal/ontology/relations.go의 `BuiltinRelations`).
[추정] 같은 실행에서 먼저 저장되는 문서가 나중에 저장될 새 concept을 가리키면 키워드 엣지가 사라진다(사례: 저장은 입력 순서로 순차 진행(write.go:172-184), target 엔티티 행이 없으면 외래키 위반(internal/storage/db.go:307-308, `foreign_keys=ON` db.go:50), `AddRelation` 오류를 무시(write.go:898-903) 1건). 테스트는 두 엔티티를 미리 만든 경우만 본다(write_test.go:29-53).

**D13. triple 스키마에 enum을 걸지 않고 Go에서 검증한다.** (a) "an enum violation fails the WHOLE call — so one hallucinated predicate would cost the document's entire graph instead of one edge"(extract_triples.go:56-63). 대안은 enum이 있는 스키마다. curation 스키마는 반대로 action에 enum을 건다(curate.go:42). [추정] 선택지가 셋뿐이고 전체 실패해도 curation 없이 진행하므로 감당할 만하다고 본 것이다(사례: curate.go:42와 fullpipeline.go:362-367 1건).

**D14. triple은 opt-in이고 컴파일을 실패시키지 않는다.** (a) "Off by default: the pass costs one call per document, and an upgrade should not change anyone's bill"(commit `a0f743e`). "this is an additive enrichment pass, and an extraction outage must not stop articles from being written"(extract_triples.go:596-599).

**D15. evidence는 summary에서 인용하고 부분 문자열로 검증한다.** (a) 검증 이유: "compile outputs are data; schema validation alone cannot stop a fabricated evidence span"(extract_triples.go:922-927). summary 인용 이유: "Pass 2 sees summaries, not source content, so a citation rendered as «Evidence» — SourceDoc names a file that does not contain those words"(internal/store/domain.go:105-109). 작성자는 이것을 한계로 인지하고 있다.

**D16. LLM 엣지 confidence 바닥 0.1, 재주장은 confidence가 더 높을 때만 덮는다.** (a) "A model that returns 0 would produce an edge that can never win AddRelation's confidence-guarded upsert against the Pass-3 keyword extractor"(extract_triples.go:156-160). upsert 규칙: "the Pass-3 keyword extractor, which re-asserts the same (source, target, relation) on every compile, can never erase an LLM-extracted edge's evidence"(internal/ontology/ontology.go:290-303).

**D17. 엔티티 upsert는 빈 값으로 덮지 않고 type은 무조건 쓴다.** (a) "Pass 3 re-asserts concept entities without a Definition, which used to erase the descriptions Pass 2 wrote"(ontology.go:139-152). triple 패스는 기존 type을 바꾸지 않는다: "must never overwrite a type an article declared"(extract_triples.go:338-346).

**D18. 엣지·관계 id는 해시로 만든다.** (a) `source-relation-target` 문자열은 단사가 아니어서 기본키가 충돌한다(extract_triples.go:316-329). cites 엣지도 #165 이후 경로 해시 8자리를 붙인다(write.go:925-932).

### resolution

**D19. 합치지 않고 잇는다(link, not collapse).** (a) "Deleting the absorbed row was tried and abandoned across three spec revisions: the row that owns an article and the row that owns a description are different rows with different ids"(internal/ontology/aliases.go:256-264). Pass 3는 slug id에 문서를, triple 패스는 모델의 원래 문자열 id에 설명을 단다(resolve_entities.go:26-31).

**D20. canonical은 LLM이 아니라 Go가 고른다.** (a) "A model-nominated canonical that Go then overrode would make the Broader answer certify a direction that was never used"(resolve_entities.go:36-40). 순서: 문서 있는 행 → 최신 created_at → id(resolve_entities.go:240-250).

**D21. seed 중심 블록, 종류별 DF 상한 + 하한 floor.** (a) 블록: "no call is ever spent on a group that cannot produce a link ... avoids the giant-component problem a shared token like "model" creates"(resolve_entities.go:446-450). floor: "three variants of one name among 45 concepts is 6.7%, over a 5% threshold, so a percentage-only filter discards exactly the token that identifies a small cluster"(resolve_entities.go:195-200). 종류별: "400 techniques named "attention variant N" would otherwise push "attention" over the limit"(resolve_entities.go:220-224).

**D22. 자동 적용에 설명문 한쪽을 요구한다.** (a) "without it a lowered threshold would link entities on surface-name similarity with no grounded evidence at all"(resolve_entities.go:312-320). 그래서 triple이 꺼져 있으면 경고한다(resolve_entities.go:672-678).

**D23. 자동 적용 threshold 0.85, 1.0이면 절대 자동 없음.** 이력이 두 번 바뀌었다. 최초 0.85(commit `dc32afd`) → 1.0으로 리뷰 전용(commit `94dbe1c`) → 다시 0.85(commit `26dba4b`).
(a) 1.0으로 바꾼 이유: "A link is not reversible — there is no un-link command"(commit `94dbe1c`). 되돌린 이유: "now that --unlink makes a mistaken link cost one command"(commit `26dba4b`). 즉 되돌릴 수단이 생기자 자동 적용을 기본으로 했다.

**D24. source 엔티티는 resolution하지 않는다.** (a) "two documents named notes.md in different directories present identically ... linking them would re-point one document's citations at the other. A source entity's identity IS its path"(resolve_entities.go:1028-1032).

### 결정성·증분

**D25. 같은 입력이면 바이트까지 같은 산출물.** (a) "identical inputs produce byte-identical artifacts, and unchanged content is never recompiled"(docs/determinism.md:3-4). 수단은 정렬 순회, 기본 temperature 0(internal/config/config.go:1185-1191), 병렬 결과를 입력 순서로 적용(write.go:86-92), `SOURCE_DATE_EPOCH`를 따르는 시계 하나(config.go:1199-1209)다. 한계도 적었다: "LLM providers are not bit-stable across their own releases"(determinism.md:195-200).

**D26. compile key는 소스 해시만이 아니라 파이프라인·템플릿·모델·config·임베딩을 묶는다.** (a) drift 원인을 설명하려고 구성 요소별 preimage를 저장한다(compilekey.go:25-27). `PipelineVersion` 올리기는 "honor-system"이라고 스스로 적었다(determinism.md:250-253). 업그레이드 뒤 첫 실행은 다시 컴파일하지 않고 key를 채택한다. 이유는 "the never-re-bill pledge applies from run one"(determinism.md:212-219).

**D27. 미완료 실행은 아무 상태도 저장하지 않는다.** (a) "Advancing even the "summarized" flag or saving the manifest would record half-done work — the earlier surgical rollback (RemoveSource on just the sources) left the run's concepts orphaned"(pipeline.go:1206-1211). 대안이던 부분 롤백이 실제로 실패해서 바꾼 것이다.

**D28. manifest는 3-way 병합 저장한다.** (a) 긴 컴파일 도중 MCP·CLI 같은 짧은 쓰기가 끼어들어도 지워지지 않게 하려는 것이다(internal/manifest/merge.go:48-57, manifest.go:156-162). 같은 키 충돌은 컴파일 쪽이 이긴다.

**D29. `max_compile_batch`는 분류 뒤 실제 처리량에 건다.** (a) 원래 raw diff에 걸었더니 "deadlocked any corpus larger than the limit, including fully-compiled ones (issue #186)"(pipeline.go:338-342).

**D30. tier 컴파일.** (a) "A single document takes ~8 minutes to fully compile ... At 100K documents with max_parallel=4: 139 days"(large-vault-performance.md:10-18). 구조 전환: "from "compile everything" to "index fast, compile what matters""(commit `3841287`).

### 품질

**D31. 품질 점수는 LLM 없이 재고 기본은 경고만 한다.** (a) #97: "I'd lean toward surface only with a default threshold of 0.5 for the warning, no gate. Easy to opt into stronger behaviors later; hard to take away." 재작성(retry)은 #144 이후 opt-in으로 들어왔다(commit `ab36031`). 재작성 전에 파일을 지우는 이유: "leaving the bad article there would turn the retry into an 'improve this bad content' call"(commit `ab36031`, fullpipeline.go:547-552).
#144가 요청한 주장 단위 검증(날짜·문서번호를 원문과 대조)은 아직 없다. 이슈 원문은 lexical grounding이 "optimizes for "does this look like it came from the source" rather than "is this specific claim actually true of the source""라고 지적했다.

**D32. 원문은 untrusted 구획으로 감싼다.** (a) "so a hostile document can't hijack the pass with injected instructions"(internal/prompts/untrusted.go:8-11). 경로도 구획 안에 넣는다: "a path in the prompt's trusted region lets a file named to carry instructions steer this pass"(extract_triples.go:123-129). 기존 문서(ExistingArticle)는 감싸지 않는다. 주석은 이를 "accepted risk"로 적는다(untrusted.go:12-14).

**D33. 짧은 chunk 출력 하한 1000토큰, 합성은 8개씩.** (a) "Reasoning models (MiniMax, DeepSeek) can spend many hundreds of tokens on chain-of-thought before emitting any answer text"(summarize.go:403-411). 8개: "Keeps each synthesis step at a manageable compression ratio (~8x)"(summarize.go:414-416).

**D34. summarize 연속 5회 실패 시 중단.** (b) 이유는 적혀 있지 않다. [추정] 인증 오류나 provider 장애 때 나머지 문서 비용을 막으려는 것이다(사례: summarize.go:157-160 1건).

## 5. 앞선 schema-glossary 보고서와 어긋나는 점

대상: `llm-wiki-implementations/lab/reports/schema-glossary/sage-wiki-ontology.md`.

| 앞선 보고서 주장 | 코드에서 본 것 | 판정 |
|---|---|---|
| "이름이 정확히 같으면 이 단계(임베딩 dedup)를 건너뛰고, 그대로 Pass 3에서 기존 문서를 다시 쓰며"(D절) | `CheckDuplicate`는 자기 자신과의 비교만 건너뛴다(dedup.go:144-147). 다른 기존 이름과 0.85 이상이면 같은 이름의 concept도 그 이웃에 합쳐지고 Pass 3에서 빠진다(fullpipeline.go:329-339). 조기 반환 분기는 없다 | 부정확. 정확히 같은 이름은 "건너뜀"이 아니라 "자기 자신 제외 후 일반 비교" |
| "Pass 3: concept마다 raw 원문에서 이름·별칭이 걸리는 절을 뽑아"(흐름표) | 15000 rune 이상이고 markdown heading이 있을 때만 그렇다. 아니면 문서 앞 4000바이트를 통째로 넣는다(write.go:1100-1112, split.go:23-37) | 빠뜨림. 형식 없는 문서에서는 절 선택이 일어나지 않는다 |
| "summary(앞 1000자)"(흐름표, C절) | 1000**바이트**다(concepts.go:182-184) | 단위 오류. 한국어에서 차이가 3배다 |
| "dedup_strategy: llm이면 대신 LLM이 keep/fold/drop"(흐름표) | 맞다. 다만 batch 재개·re-extract 경로에는 임베딩 dedup이 아예 없다(pipeline.go:1719-1731, reextract.go:140-156) | 보충 |
| 자동 적용 0.85(D절) | 맞다. 이력상 0.85 → 1.0 → 0.85로 바뀌었다(D23) | 보충 |
| concept type 언급 없음 | concept 추출 프롬프트는 type을 concept·technique·claim 셋으로 고정한다(extract_concepts.txt:18). config `entity_types`는 triple 경로에만 닿는다 | 보충. A절 "사람이 config로 정한 schema"는 concept 경로에는 거의 닿지 않는다 |

나머지 인용(어휘 강제 세 겹, 술어 동의어 대조, evidence 부분 문자열 검증, upsert 규칙, DF 상한, 관련 8개)은 같은 줄에서 같은 내용을 확인했다.

## 6. 코드와 문서가 어긋나는 곳

| 문서 | 코드 | 근거 |
|---|---|---|
| 품질 점수는 "Source coverage (40%) / Extraction completeness (30%) / Cross-reference density (30%)" | 5차원 0.15/0.30/0.20/0.15/0.20 | large-vault-performance.md:262-266, confidence.go:31-39 |
| 승격 신호 cluster_size·manual_tag·import_centrality·source_recency_days, 강등 source_modified | 검색 적중 수와 90일 정체만 쓴다 | large-vault-performance.md:117-131, 위 #3 tier 절 |
| frontmatter `tier:`가 최우선 | 호출부가 nil을 넘겨 동작하지 않는다 | large-vault-performance.md:102-111, pipeline.go:1283 |
| `curate-concepts.md`도 사용자 덮어쓰기 대상 | 덮어쓰기는 되지만 compile key의 템플릿 목록 6개에 없어 고쳐도 재컴파일이 일어나지 않는다. curation 호출은 temperature도 넘기지 않는다 | customizing-prompts.md:23, internal/prompts/versions.go:17-24, curate.go:298 |
| `buildAliasMap` 주석 "the ontology store and manifest hold no aliases" | 바로 아래에서 manifest 별칭을 쓴다 | write.go:716-717 vs 725-734 |
| 번들 pack의 `prompts/extract_*.md` | 컴파일 경로는 `summarize_<type>`, `extract_concepts`, `extract_triples`, `resolve_entities`, `curate_concepts`, `write_article`만 렌더링한다. [추정] 16개 pack 프롬프트 중 `summarize_*` 3개 외 13개는 컴파일에서 쓰이지 않는다(사례: 8개 pack의 prompts 목록과 렌더링 이름 grep 1건, `extract_meeting`은 pack.yaml 밖에서 참조 0건) | internal/pack/bundled/*/prompts, internal/pack/merge.go:197-216, internal/prompts/prompts.go:246-250 |

[추정] meeting-organizer pack은 `default_tier: 2`를 설정해(internal/pack/bundled/meeting-organizer/pack.yaml:12-13) 회의록이 LLM 컴파일을 받지 못하고, pack이 더한 엔티티 종류(attendee, action_item, blocker)도 채워지지 않는다(사례: LLM 패스는 tier 3만 claim(pipeline.go:1135) 1건).

[추정] 임베딩 dedup 캐시 seed는 벡터 저장소에서 id=concept 이름을 찾지만 문서 벡터는 `concept:<name>`으로 저장된다. 그래서 seed가 매번 빗나가 기존 concept 이름 전부를 매 컴파일 다시 임베딩한다(사례: dedup.go:73과 write.go:414 1건). 가이드는 "The cache loads existing concept embeddings from the vector store (no API calls for seeded concepts)"라고 적는다(large-vault-performance.md:257-258). 설령 찾더라도 문서 본문 벡터라 이름 벡터와 비교 대상이 다르다.

## 7. 엔터프라이즈 다중 작성자 보고서 용도

사용자 조건은 작성자마다 같은 대상을 다른 용어로 쓰는 것, 형식 없는 문서, 여러 사람, 권한이다. 이 레포의 실사용 이슈(#128, #144, #146, #164, #166, #167)가 모두 141개 문서 규모 정부 토양 정화 사건 파일에서 나왔다는 점이 참고가 된다. 사내 보고서와 성격이 가깝다.

### 쓸 만한 장치

| 장치 | 왜 쓸 만한가 | 근거 |
|---|---|---|
| never-merge 결정 규칙 | 사내 보고서의 번호 붙은 대상(과제 3차/4차, 2023/2024 회계연도, 초안/최종)은 임베딩으로 못 가른다는 측정이 있다 | dedup.go:169-239, #164 |
| 전역 curation 패스 | 묶음별 추출의 사각지대(다른 묶음을 모름)를 한 번의 전역 판단으로 메운다. fold는 자동, drop은 허가제 | curate.go, #167 |
| 별칭 겹침 접기 + manifest 별칭 합집합 | 작성자별 약어·풀네임 차이를 접는다. 사람이 별칭을 추가할 자리로 쓸 수 있다 | concepts.go:318-471, manifest.go:215-237 |
| link-not-collapse + `--unlink` + 거절 전이 차단 | 여러 사람이 일부만 검토해도 실수를 정확히 되돌릴 수 있다. 사람이 거절한 쌍은 제3자 경유로도 다시 합쳐지지 않는다 | resolve_entities.go:1285-1334, aliases.go:252-270 |
| evidence 부분 문자열 검증 | 지어낸 근거를 코드로 버린다. 원문 chunk 대상으로 바꾸면 그대로 가져올 수 있다 | extract_triples.go:905-952 |
| 미완료 실행 무저장 + 3-way manifest 병합 | 여러 사람이 동시에 넣어도 긴 컴파일이 짧은 쓰기를 지우지 않는다 | pipeline.go:540-544, merge.go:48-57 |
| compile key와 `--explain` | 프롬프트·모델·config를 바꾸면 어떤 문서가 왜 다시 도는지 설명된다. 운영자가 비용을 예측할 수 있다 | compilekey.go, determinism.md:88-96 |
| tier + on-demand | 전체 보고서를 싸게 색인만 하고, 질의가 모이는 주제만 LLM 컴파일한다 | large-vault-performance.md |
| 원문 맥락 토큰 예산 | 자주 언급되는 사내 용어(제품명·부서명)가 수십 문서에 걸쳐도 400 오류 대신 의도된 잘라내기가 된다 | write.go:1144-1182, #146 |
| 부분 실패 실명 보고 | 몇 개 문서가 빠졌는지 이름까지 남긴다 | concepts.go:68-80, #166 |

### 걸리는 점

| 걸리는 점 | 영향 | 근거 |
|---|---|---|
| 형식 없는 문서에서 Pass 3가 앞 4000바이트만 본다 | heading 없는 보고서, 15000자 미만 보고서에서 뒤쪽 내용으로 문서가 쓰이지 않는다 | §2 원문 맥락 절 |
| concept 추출이 summary 앞 1000바이트만 본다 | 긴 보고서의 concept 재현율이 떨어진다. 새/기존 연결 발견의 입구가 좁다 | concepts.go:182-184 |
| 원문 연결 단위가 문서다 | concept→source `cites`는 문서 단위, triple evidence는 summary 인용. raw chunk(`src:<path>:c<i>`)는 검색용이고 엔티티와 이어지지 않는다 | write.go:364-382, index.go, domain.go:105-109 |
| 사람이 쓰는 용어집 입력 경로가 없다 | 정식 이름+별칭 목록을 프롬프트 앞단에 넣는 장치가 없다. concept 프롬프트에는 이름만, triple 프롬프트에는 목록조차 없다 | concepts.go:124, extract_triples.txt:14-15 |
| 키워드 관계 동의어가 영어·중국어뿐 | 한국어 보고서에서 Pass 3 키워드 엣지는 거의 생기지 않는다. 동의어를 config로 더해야 한다 | relations.go `BuiltinRelations` |
| concept type이 셋으로 고정 | 사내 schema(부서, 제품, 과제, 고객)를 정해도 concept 문서 type에 반영되지 않는다 | extract_concepts.txt:18 |
| 작성자·날짜 메타데이터가 LLM에 닿지 않는다 | raw markdown frontmatter는 떼어 내고(extract.go:202-209) 본문만 summarize에 넣는다. 날짜는 `sourcedate`가 frontmatter `date:`만 읽는다 | extract.go:193-221, sourcedate.go:31-35 |
| 권한 모델이 컴파일에 없다 | 소스·concept·엔티티 어디에도 소유자·접근 범위 필드가 없다. 여러 소스의 내용이 한 concept 문서로 합쳐진다 | §1 자료 구조 표(필드 목록) |
| concept 이름이 파일명이자 id | 한국어 slug, 영어 slug가 섞이면 같은 대상이 두 문서가 된다. LLM 언어 지시는 JSON 템플릿에 붙지 않는다 | write.go:216, internal/prompts/prompts.go:147-155 |
| 품질 점수가 lexical | 날짜·문서번호 같은 구체 값의 오류를 못 잡는다(#144의 LUC 사례) | confidence.go:196-255, #144 |

## 8. 모르는 것

| 질문 | 무엇을 보면 알 수 있나 |
|---|---|
| concept 프롬프트에 별칭을 넣지 않은 이유 | `extract_concepts.txt`의 git 이력(`git log -p -- internal/prompts/templates/extract_concepts.txt`)과 관련 PR 토론 |
| concept type을 세 개로 고정한 이유와 config `entity_types`를 concept 경로에 연결할 계획 | 이슈 검색 "entity_types concept extraction", P3 spec 문서(레포 밖 `.sage/docs`로 보이며 클론에 없음) |
| summary 1000바이트 자르기가 concept 목록 절을 실제로 잘라 먹는지 | 실제 summary 파일 길이 분포. 실행이 필요하다 |
| Pass 3가 PDF·DOCX를 바이너리로 받는지 | PDF 소스 하나로 컴파일하고 `write_article` 요청 본문을 기록. 또는 #146 재현 로그 |
| 정확히 같은 이름의 concept이 이웃 이름에 흡수되는 일이 실제로 생기는지 | 기존 concept과 같은 이름을 재추출시키는 테스트. 현재 테스트(dedup_test.go)에는 없다 |
| 같은 실행 안의 앞→뒤 wikilink 키워드 엣지 손실 | 새 concept 두 개가 서로 링크하는 corpus로 컴파일 후 relations 표 확인 |
| 작성자가 밝힌 "lessons learned" | README가 링크한 글 https://x.com/xoai/status/2040936964799795503 (X는 로그인 없이 읽기 어려워 열지 않았다) |
| resolution 수치 효과 | `eval/` 벤치마크는 triple·resolve를 켜지 않은 설정으로 보인다(앞선 보고서 H절). 켠 결과 파일은 찾지 못했다 |
| batch 재개 경로가 임베딩 dedup·triple을 빼는 것이 의도인지 | `resumeBatch`의 P1-8 주석(pipeline.go:1441-1443)은 store 구성만 설명한다. batch 관련 spec이나 이슈 |

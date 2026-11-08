# sage-wiki — raw를 summary → concept → article로 다패스 컴파일하는 Go 단일 바이너리가, 실사용 말뭉치에서 깨진 가정마다 LLM 판단 아래 결정적 코드 규칙을 깔고, 돈이 들거나 되돌리기 어려운 단계는 opt-in으로 미뤄 왔다

분석 대상은 GitHub `xoai/sage-wiki`, commit `d3ef3a1`(2026-10-03, HEAD)이다.
경로는 레포 루트 기준 `path:line`이다. 코드는 실행하지 않았고 읽기 전용 git·grep·sed·cat과 `gh`만 썼다.

입력은 갈래별 노트 4개(compile, query-store, surfaces-team, sage-why)다. 노트끼리 어긋난 곳은 코드를 다시 열어 가렸고, 그 자리에 "이 보고서 작성 때 다시 열어 확인"이라고 적었다.

표기는 이렇다.
작성자가 밝힌 이유는 원문을 큰따옴표로 옮기고 뒤에 한국어 뜻을 붙인다.
코드 읽기로 추론한 이유는 `[추정]`을 앞에 달고 문장 끝 괄호에 사례와 개수를 붙인다.
근거가 없으면 `모르는 것:`으로 적는다.

## 한눈에

| 항목 | 값 |
|---|---|
| 무엇 | Karpathy llm-wiki 패턴을 "컴파일러"로 구현한 Go 프로그램이다. raw 문서를 summary → concept → article로 컴파일하고, opt-in 그래프 패스(triple 추출, entity resolution, community)를 얹는다. 07-28에 README 정체성을 "LLM-compiled personal knowledge base"에서 "graph memory and knowledge base that AI agents and humans build and query together"로 바꿨다(commit `41ee24c`) |
| 실행 형태 | 바이너리 하나(`CGO_ENABLED=0`, `.github/workflows/ci.yml:53`)가 CLI·MCP(19개 tool, `internal/mcp/server.go:175-203`)·REST `/v1`·web UI·TUI·Go 임베딩(`pkg/engine`)을 모두 낸다. 저장은 파일(`raw/`, `wiki/`)과 `.manifest.json`, `.sage/wiki.db`(SQLite) 한 파일이고, Postgres는 선택이다 |
| 규모 | Go 비테스트 334개 파일 83,709줄, 테스트 437개 파일 87,146줄, `internal/` 패키지 47개, web SPA 1,745줄, `docs/` 8,753줄(`git ls-files … \| xargs cat \| wc -l`). commit 917개, 2026-04-04 ~ 2026-10-03 |
| 이력 밀도 | 월별 commit은 4월 134, 5월 26, 6월 25, 7월 499, 8월 218, 9월 5, 10월 10이다. 7·8월이 약 78%다(sage-why 노트 #3). 917개 중 861개가 작성자 `xoai` 한 명이다(`git shortlog -sn`) |
| 라이선스 | MIT다(`LICENSE`, "Copyright (c) 2026 xoai"). 예외가 셋이다. `eval/benchmarks`의 mem0 유래 코드·프롬프트는 Apache-2.0이고(`eval/benchmarks/NOTICE:1-13`), `internal/vectors/hnsw`는 CC0 사본이며(`VENDORED.md:1`), 원격 pack registry는 별도 레포(`xoai/sage-wiki-packs`, `internal/pack/registry.go:13`)다. #가져올 것 표의 항목은 모두 MIT 범위다 |
| 성숙도 | 태그 23개, v0.1(2026-04-07) ~ v0.2.11(2026-10-03). CI workflow 10개(`.github/workflows/`). `ci.yml`이 build·vet, race 포함 shard 테스트, parity suite replay와 10회 flake loop, golden 변경 표시 검사, fuzz 8개 대상, agent skill drift를 돈다(`ci.yml:36-208`) |
| 개발 방식 | 7월 이후 commit 제목에 "Gate 3 round N", "[V] independent verification"이 반복되고 Claude co-author 꼬리표가 30회 나온다(sage-why 노트 #3). README 9행이 "built with the Sage Framework"(작성자의 에이전트 프레임워크 `xoai/sage`)를 밝힌다 |
| 이유 문서의 자리 | 코드 주석이 가리키는 SPEC-01~09, ADR-036~039, `decision-035`는 레포에 없다. `.gitignore:1-12`가 `.sage/`·`sage/`를 뺀다. 그래서 이 보고서의 "작성자가 밝힌 이유"는 주석·commit 본문·이슈·작성자 X 글에 새어 나온 것뿐이다. P2-1~P2-7 설계 문서 7개만 `git show 3e803d5:.sage/docs/design/<name>.md`로 읽힌다 |

## 큰 구조

층은 넷이다. 표면 아래에 컴파일·질의 엔진이 있고, 엔진은 파일과 SQLite에 쓴다.

표면 가운데 `/v1` REST와 `serve --addr` REST만 MCP tool 레지스트리(`CallTool`)로 보낸다. CLI·TUI·web UI `/api/*`·`pkg/engine`은 compiler·query·search 함수를 직접 부른다(`internal/web/server.go:144-154`, `pkg/engine/search.go:142`, `internal/tui/dashboard/model.go:88`, `cmd/sage-wiki/main.go:1119`).

```
표면    CLI(cmd/sage-wiki) · MCP stdio/SSE · serve --addr(REST+/mcp+/v1) · serve --ui(web /api/* + /v1) · 다중 workspace serve · TUI · pkg/engine · hub(CLI만) · clients/{python,typescript}(/v1 타입 클라이언트)
          ├──── /v1·serve REST 는 (*mcp.Server).CallTool 로 보낸다 ── 19개 tool handler
          └──── CLI·TUI·web /api/*·pkg/engine 은 엔진 함수를 직접 부른다
엔진    compiler(Pass 0~4, tier, compile key, worker)   query·search·graph(3채널 RRF, GraphQA)   trust(답 격리·승격)   linter(8 pass)   wiki(ingest·reconcile)
지원    llm(structured output) · prompts(템플릿 9개 + untrusted 구획) · ontology(어휘·alias) · manifest · extract · embed · config · pack · limits
저장    store 인터페이스 seam ─ sqlitestore(SQLite: FTS5 + BLOB 벡터 + 그래프 + 큐) | storage/postgres(pgvector)   vectors(메모리 행렬·HNSW·mmap)   mirror(S3 백업 + hydrate 복원·PITR)
파일    raw/ (원문, 사람 소유)   wiki/{summaries,concepts,communities,outputs,under_review}/   .manifest.json   .sage/wiki.db
```

| 구성 요소 | 맡는 일 | 대표 파일 |
|---|---|---|
| 컴파일 진입 | diff → skip 분류 → tier → 패스 실행 → 꼬리 처리 | `internal/compiler/pipeline.go:291`(`Compile`) |
| 패스 본체 | Pass 1 → 2 → 임베딩 dedup(기본) → evidence gate → curation(opt-in, dedup 대신) → 2b → 3 → (defer) 4 → sweep → communities | `internal/compiler/fullpipeline.go:139, 317-367` |
| 이름 정리 | 잡음 필터, 정규화·별칭 접기, 임베딩 dedup + never-merge, LLM curation, evidence gate | `concepts.go:270-471`, `dedup.go:125-239`, `curate.go`, `evidence_gate.go` |
| 그래프 | triple 추출과 Go 검증, entity resolution, derived edge, bi-temporal | `extract_triples.go`, `resolve_entities.go`, `internal/ontology/aliases.go` |
| 증분·결정성 | compile key(소스·파이프라인·템플릿·모델·config·임베딩 해시) | `internal/compiler/compilekey.go:45-55`, `docs/determinism.md` |
| 검색 | graph leg + chunk/doc FTS + chunk/doc vector를 RRF로 합치고, 선택적으로 확장·rerank | `internal/search/run.go:124`, `internal/search/pipeline.go:98-226` |
| Q&A | 검색 → 그래프 확장 → 문서 파일 전체로 문맥 → LLM → 답 격리 | `internal/query/query.go:52, 212-459` |
| 답 신뢰 | `under_review/` 격리, consensus·grounding, 승격·강등 | `internal/trust/hooks.go:170-256`, `promote.go`, `verify.go` |
| 표면 | MCP와 REST(`/v1`, serve)가 같은 tool을 공유한다. web `/api/*`·CLI·TUI는 엔진을 직접 부른다 | `internal/mcp/server.go:117-203`, `internal/api/dispatch.go:37-79`, `internal/web/server.go:144-154` |
| 저장 seam | 인터페이스는 `internal/store`, 구현은 `sqlitestore`·`storage/postgres` | `internal/store/types.go:114-145`, `internal/storedial/dial.go:21-41` |

저장 위치마다 진실의 정도가 다르다.

| 자리 | 담는 것 | 성격 |
|---|---|---|
| `raw/` | 사람이 넣은 원문, capture 결과 | 컴파일이 고치지 않는다 |
| `wiki/summaries/*.md` | 문서당 summary. frontmatter에 `source_hash` | Pass 1 산출, 재사용 키 |
| `wiki/concepts/<name>.md` | concept 하나 = article 하나. frontmatter는 코드가 쓴다 | Pass 3 산출 |
| `.manifest.json` | source(hash, tier, summary 경로)와 concept(Sources·Aliases 합집합) | "있어야 할 것" 목록(`internal/wiki/reconcile.go:33-47`) |
| `.sage/wiki.db` | FTS5, 벡터 BLOB, entities·relations·entity_aliases·derived_relations, compile_items 큐, trust 표 | "The database is a rebuildable index; **files are the truth**"(`docs/guides/storage-backends.md:62`) — DB는 다시 짓는 색인이고 파일이 진실이다 |

검색 결과의 문서 ID 모양이 조회 경로를 정한다(query-store 노트 #문서 ID 규약).

| DocID | 가리키는 것 | 색인하는 곳 |
|---|---|---|
| `concept:<name>` | concept article. FTS tags에 별칭이 들어간다 | `internal/compiler/write.go:388-392` |
| raw 경로 그대로 | summary | `internal/compiler/fullpipeline.go:246-251` |
| `src:<raw 경로>` | tier 0/1 raw 원문 색인과 청크 `src:<path>:c<i>` | `internal/compiler/index.go:60-64, 273-298` |
| `output:<file>` | 승격된 Q&A 답 | `internal/trust/promote.go:55-60` |

## 한 바퀴 흐름

### ingest: 원문에서 페이지까지

표시: **코드**는 결정적 Go 코드, **LLM**은 모델 호출, **임베딩**은 임베딩 API만 부른다.

| # | 단계 | 누가 | 하는 일 | 위치 |
|---|---|---|---|---|
| 0 | 넣기 | 코드 | `ingest`·`add-source`는 크기·인코딩을 검사하고 `raw/`에 복사해 manifest에 등록한다. 컴파일은 하지 않는다. MCP `wiki_capture`만 LLM으로 대화를 항목으로 쪼갠다. URL ingest는 SSRF 방어로 loopback·사설·link-local 주소를 거부하고, 끄는 변수 `SkipSSRFCheck`는 테스트 전용이라 config로 열 수 없다. 그래서 인트라넷 문서는 파일로 내려받아 넣어야 한다 | `internal/wiki/ingest.go:34-35, 56-243, 292-320`, `internal/mcp/tools_write.go:427-549` |
| 1 | Pass 0 diff | 코드 | 소스를 걸으며 SHA-256과 type을 manifest와 비교한다. 경로순으로 정렬한다 | `internal/compiler/diff.go:41-153` |
| 2 | skip 분류 | 코드 | compile key로 재개·force·내용 변경·채택·skip·drift를 가른다. 처리량이 `max_compile_batch`(1000)를 넘으면 처리 전에 거부한다 | `docs/determinism.md:88-94`, `pipeline.go:338-342, 407-424` |
| 3 | tier 배정 | 코드 | `.wikitier` > `tier_defaults[확장자]` > `default_tier`(기본 3)로 정하고 tier 0·1·3 순으로 lease를 잡는다 | `tiers.go:33-74`, `pipeline.go:1082-1147` |
| 4 | Tier 0/1 색인 | 코드·임베딩 | 원문을 `src:<path>`로 FTS에 넣고, tier ≥ 1이면 원문 청크를 임베딩한다 | `index.go:60-65, 100-` |
| 5 | Pass 1 summarize | LLM | `source_hash`가 같은 summary가 있으면 재사용한다. 아니면 텍스트화하고, 길면 청크 그룹마다 요약한 뒤 8개씩 계층 합성한다. 빈 응답과 100자 미만은 거부한다 | `summarize.go:203-236, 259-261, 326-342, 414-416` |
| 6 | Pass 2 concept 추출 | LLM | summary 20개를 묶고 각 summary는 앞 **1000바이트**만 넣는다. 기존 concept 이름 스냅샷 하나를 모든 묶음에 준다. `{name, aliases, sources, type}`을 structured output으로 받는다 | `concepts.go:98-138, 121-123, 180-184` |
| 7 | 잡음·정규화 | 코드 | 2바이트 미만·숫자만·경로 모양 이름을 버리고, 정규화 이름 일치와 별칭 겹침으로 접는다. manifest 별칭과 일치하면 manifest의 정식 이름으로, 같은 실행 안의 별칭 겹침이면 정규화 이름이 긴 쪽으로 접는다 | `concepts.go:270-471` |
| 8 | 임베딩 dedup(기본) | 임베딩 + 코드 | concept **이름**을 임베딩해 기존 이름과 cosine ≥ 0.85면 합친다. 숫자 토큰 집합이 다르거나 draft/final·primary/secondary 한쪽만 있으면 막는다 | `dedup.go:125-239`, `fullpipeline.go:317-353` |
| 9a | evidence gate | 코드 | source 수가 `min_concept_sources`(기본 1)보다 적으면 manifest·article·entity·cites 어디에도 만들지 않는다 | `evidence_gate.go:13-28`, `fullpipeline.go:355-357` |
| 9b | curation(opt-in, 8 대신) | LLM + 코드 | evidence gate 뒤에서 200개씩 keep/fold/drop을 받는다. fold는 never-merge가 거부할 수 있고, drop은 `allow_drop`일 때만 적용한다. 주석은 이 자리를 "the post-evidence-gate seam on ALL write paths"(모든 쓰기 경로의 evidence gate 뒤 자리)라 부른다 | `curate.go:125-167, 255-261`, `fullpipeline.go:359-367` |
| 10 | Pass 2b triple(opt-in) | LLM + 코드 | 문서당 1회 entity·relation을 뽑는다. Go가 어휘·evidence 부분 문자열·자기 루프를 검증하고, 문서당 entity 40·relation 60으로 자른다 | `extract_triples.go:111-152, 175-291, 587-591, 905-952` |
| 11 | Pass 3 article | LLM + 코드 | concept마다 raw 원문 맥락(예산 100k 토큰)과 기존 article, 공유 source 상위 8개 관련 concept을 넣어 쓴다. frontmatter는 코드가 만들고, LLM frontmatter·anti-pattern 문장을 지우고, `[[별칭]]`을 정식 이름으로 바꾼다. `cites`·키워드 근접 관계 edge를 만든다 | `write.go:212-249, 264-286, 465-491, 775-786, 1080-1188` |
| 12 | 품질 점수 | 코드 | LLM 없이 5개 차원을 잰다. 기본은 0.5 미만 경고뿐이고, `quality.retry: true`면 파일을 지우고 1회 다시 쓴다 | `confidence.go:31-39, 86-104`, `fullpipeline.go:547-586` |
| 13 | Pass 4 resolution(opt-in, defer) | LLM + 코드 | 이번에 건드린 entity를 seed로 같은 type 안에서 후보 블록을 만들고 LLM이 같은 대상인지 판정한다. canonical은 Go가 고르고 자동 적용 조건 5개를 코드가 본다 | `resolve_entities.go:251-345, 466-532, 1085-1117` |
| 14 | sweep·communities | 코드 / LLM(opt-in) | functional 관계를 alias 반영해 다시 무효화한다. Louvain으로 community를 찾고 바뀐 것만 요약한다 | `extract_triples.go:407-422`, `communities.go:58-79, 194-197` |
| 15 | 꼬리 처리 | 코드 | 끊긴 wikilink 제거, 삭제된 소스 정리, manifest 3-way 병합 저장, CHANGELOG, trust 재검증(`include_outputs: verified`일 때만), git auto-commit. Pass 2·3이 끝나지 않은 실행은 manifest와 compile key를 저장하지 않는다. 이미 쓴 summary·article 파일과 색인 행은 남고 다음 실행이 같은 내용으로 다시 쓰며, CHANGELOG·git auto-commit은 그대로 돈다 | `pipeline.go:497-591, 500-504, 540-544, 561-573, 1206-1213`, `write.go:170-171` |

문서 하나당 LLM 호출 수는 기본 경로에서 summary 1회(긴 문서는 그룹 수 + 합성), 20개당 concept 추출 1회, concept당 article 1회다. triple은 문서당 1회, resolution은 블록당 1회이고 둘 다 기본 꺼짐이다(compile 노트 #문서 한 개당 LLM 호출 수).

Pass 3의 원문 맥락은 문서 모양에 따라 다르다. 문서가 15000 rune 이상이고 markdown heading이 있을 때만 concept 이름·별칭이 든 절을 고르고, 고른 절도 하나당 4000바이트로 자른다. 일치하는 절이 없으면 첫 절만 넣는다(`write.go:1115-1141`, `internal/extract/split.go:23-37`). 그 밖에는 문서 앞 4000바이트만 넣는다(`write.go:1100-1112`, 이 보고서 작성 때 다시 열어 확인).

이 경로는 raw 파일을 `os.ReadFile`로 그대로 읽으므로 frontmatter도 앞부분에 함께 들어간다(`write.go:1092-1111`). Pass 1 summarize만 frontmatter를 떼어 낸다(`internal/extract/extract.go:193-221`).

### query: 질문에서 답까지

| # | 단계 | 누가 | 하는 일 | 위치 |
|---|---|---|---|---|
| 1 | 저장소 열기 | 코드 | config를 읽고 `app.Open`으로 backend를 연다 | `internal/query/query.go:61-88` |
| 2 | graph leg | 코드 | 질의 토큰과 하이픈 n-gram을 entity ID에 정확 대조하고, applied alias를 canonical로 풀고, 2 hop까지 점수를 퍼뜨린다 | `internal/search/graphleg.go:61-80, 125-194` |
| 3 | 확장 | LLM | doc FTS가 강한 신호면 건너뛴다. 아니면 lex 2·vec 1·hyde 1 질의를 받는다 | `internal/search/expand.go:36-123` |
| 4 | leg 검색과 RRF | 코드·임베딩 | chunk FTS·doc FTS·chunk vector·doc vector를 질의마다 돌리고 문서 단위로 `Σ w/(60+rank)`를 더한다. 기본 가중 BM25 0.7, vector 0.3, graph 0.2 | `internal/search/pipeline.go:55-60, 98-168, 295-393` |
| 5 | rerank | LLM | 상위 15개를 0~10점으로 채점하고, 채점률이 50% 미만이면 RRF 순서를 지킨다. 순위별 75/60/40% 혼합 | `internal/search/rerank.go:38, 189-242, 295-305`, `internal/search/pipeline.go:53, 175-226` |
| 6 | 태그·날짜·trust | 코드 | 태그 필터·가산, 14일 반감 recency(상한 5%), `output:` 문서 거르기 | `internal/search/run.go:216-307` |
| 7 | 그래프 확장 | 코드 | 상위 `concept:`을 seed로 direct link·source overlap·Adamic-Adar·type affinity 4신호로 article을 덧붙인다 | `internal/graph/relevance.go:73-300` |
| 8 | 문맥 조립 | 코드 | 검색 결과의 **문서 파일 전체**를 읽어 붙인다. 문서당 16000바이트, `len/4` 어림 8000토큰 예산 | `query.go:309-459` |
| 9 | 합성 | LLM | 질문과 문맥을 untrusted 구획으로 감싸고 `[[wikilinks]]` 인용을 지시한다 | `query.go:130-135, 194-208` |
| 10 | 답 보관 | 코드(+임베딩, 애매하면 LLM 1단어) | 기본은 `wiki/under_review/`에 두고 pending으로 기록한다. 비슷한 질문이 있으면 답을 비교해 확인 수를 올리거나 conflict로 표시한다 | `query.go:645-656, 673`, `internal/trust/hooks.go:165-243`, `consensus.go:26-145` |

검색 표면(`wiki_search`, CLI search, web)은 같은 `search.Run`을 쓰되 확장·rerank를 기본으로 끈다(`internal/mcp/server.go:315-375`, `docs/guides/search-quality.md:128-134`).

관계 질문은 `wiki_graph_query`가 GraphQA(edge 목록에서만 답하고 edge 번호로 인용, `internal/query/graphqa.go:90-213`)나 GlobalQA(community 요약 map-reduce, `globalqa.go:50-217`)로 푼다.

### 유지보수: lint·재컴파일·병합

| # | 일 | 누가 | 하는 일 | 위치 |
|---|---|---|---|---|
| 1 | lint | 코드 | 8개 pass(completeness, style, orphans, consistency, connections, impute, staleness, quality). 자동 수정은 style의 frontmatter 삽입뿐이다 | `internal/linter/runner.go:95-108`, `passes.go` |
| 2 | 답 검증 | LLM | pending 답 최대 20개에서 claim을 뽑고 claim마다 grounded/inferred/ungrounded를 받는다 | `internal/trust/verify.go:31-63`, `grounding.go:24-117` |
| 3 | 답 승격·강등 | 사람(CLI) / 코드 | 확인 ≥ 3 + 독립성 > 0.3(또는 확인 ≥ 6) + grounding ≥ 0.8이면 자동 승격한다. `include_outputs: verified`일 때만 컴파일 끝에 인용 파일 hash를 다시 계산해 바뀐 confirmed 답을 강등한다. 기본값 `"false"`에서는 이 검사가 돌지 않는다 | `internal/trust/consensus.go:140-145`, `internal/trust/hooks.go:183-189`, `pipeline.go:561-573`, `internal/config/config.go:1059-1063`, `source_check.go:35-61` |
| 4 | alias 결정 | 사람(CLI) | `ontology resolve --apply/--reject/--unlink`. 거절은 대칭이고 전이 폐포까지 막는다 | `cmd/sage-wiki/ontology_resolve.go:34-37`, `resolve_entities.go:1301-1334` |
| 5 | 재컴파일 | 코드 | 프롬프트·모델·config가 바뀌면 compile key drift로 영향받는 문서만 다시 돈다. `--explain`이 이유를 보인다. `--re-extract`는 디스크의 summary로 Pass 2 이후만 다시 돈다 | `docs/determinism.md:66-96`, `internal/compiler/reextract.go:38` |
| 6 | 감시 | 코드 | `compile --watch`가 fsnotify 또는 polling으로 다시 컴파일한다 | `internal/compiler/watch.go:23, 109, 163` |
| 7 | 파일·DB 맞추기 | 코드 | serve 시작 때 manifest 기준으로 재색인하거나 고아 색인을 지운다 | `internal/wiki/reconcile.go:48, 200-292` |
| 8 | 병합 | 코드 | concept 병합은 manifest 합집합, entity 병합은 행을 남기고 `derived_relations`로 잇는다. 긴 컴파일 중 끼어든 짧은 쓰기는 manifest 3-way 병합이 살린다 | `internal/manifest/manifest.go:215-237`, `internal/ontology/aliases.go:256-264`, `internal/manifest/merge.go:48-57` |

## 왜 이 구조인가

[추정] 결정 23개를 묶는 모양은 셋이다(사례: 아래 결정 23개).

| 모양 | 뜻 | 대표 결정 |
|---|---|---|
| 결정적 바닥 | LLM이 판단하되 되돌리기 어려운 실수는 코드 규칙이 거부한다 | 6, 8, 9, 11, 13 |
| 비용·되돌리기 비용이 기본값을 정한다 | 돈이 드는 패스는 opt-in, 되돌릴 수 없는 자동화는 꺼 둔다 | 7, 9, 11, 15, 16 |
| 실사용 말뭉치가 설계를 움직였다 | 비ML·규제 문서 보고(#90, #106, #128, #146, #164, #167)가 기본값과 장치를 바꿨다 | 3, 8, 9, 10, 12 |

"결정적 바닥"은 작성자가 직접 쓴 말이다: "the deterministic floor under judgment"(판단 아래의 결정적 바닥; `curate.go:28`, `4c0a708`). 작성자 프레임워크의 원칙도 같은 방향이다: "If a rule matters, make it code. If you can't, don't claim it."(규칙이 중요하면 코드로 만들고, 못 하면 주장하지 말라; `xoai/sage` README 77행).

[추정] 이 원칙이 never-merge 하나를 넘어 다른 결정에도 걸린다(사례 5개: `curate.go:162-166` never-merge 거부권, `extract_triples.go:56-63` Go 어휘 강제, `resolve_entities.go:242` canonical을 Go가 고름, `resolve_entities.go:335-337` threshold 1.0 코드 분기, #128 evidence gate가 LLM 호출 전에 막음).

### 1. Go 단일 바이너리, CGO 없음, SQLite 한 파일

- **결정**: 순수 Go 바이너리 하나와 `modernc.org/sqlite`, 저장은 `.sage/wiki.db` 한 파일이다(`README.md:152, 762`, `Makefile:4-6`).
- **대안**: Go CLI + MCP로 붙는 Python memory server + 별도 API routing gateway의 세 프로세스 구성(작성자가 실제로 거친 이전 설계, X 글), 그리고 외부 벡터 DB(작성자가 처음부터 피한 선택지, 결정 2).
- **작성자가 밝힌 이유**: 첫 commit `4876ddb` "Single Go binary, zero CGO, cross-platform." 작성자 X 글(2026-04-05): "there’s no C compiler needed on the user’s machine. This isn’t aesthetic purism. If I have to debug a Python version mismatch or a broken venv before compiling my notes, I’ve already lost."(사용자 기기에 C 컴파일러가 필요 없다. 노트를 컴파일하기 전에 Python 버전이나 venv를 고쳐야 한다면 이미 진 것이다), "The tool should be as boring as grep."(grep처럼 지루한 도구여야 한다), "Early in the design, I had three separate processes: a Go CLI, a Python memory server communicating over MCP, and a separate API routing gateway." / "I collapsed all three into one binary."(세 프로세스를 바이너리 하나로 합쳤다). X 글 원문은 `api.fxtwitter.com` JSON(`tweet.article.content`)으로 받아 이 보고서의 인용 구절을 모두 그대로 대조했다.
- **[추정] 파급**: CGO 금지가 이후 의존성 선택을 계속 묶었다(사례 5개: `internal/storage/db.go:285` "pure Go, no sqlite-vec", `internal/vectors/hnsw/VENDORED.md:32` "no CGO anywhere", `CHANGELOG.md:668-669` 순수 Go Louvain, `16cbda1` "zalando/go-keyring v0.2.8 (pure Go, CGO_ENABLED=0 build green)", P2-1 설계 "pure Go, `CGO_ENABLED=0` preserved"(`git show aa37245:docs/design/p2-1-storage-abstraction.md` 38행, 지금은 추적 해제 `3c77152`)).
- **이력**: 원칙은 917 commit 동안 그대로다. 뜻은 "한 프로세스 개인 도구"에서 "One Go binary scales it from a personal vault to a team hub to a company knowledge graph."(`README.md:5`)로 넓어졌다.

### 2. 외부 벡터 DB 없이 BLOB 벡터 + 정확 전수 탐색, Postgres는 선택

- **결정**: 벡터는 SQLite BLOB, 검색은 메모리의 정규화 행렬 위 내적 전수 탐색이 기본이다. HNSW·mmap·Postgres+pgvector는 opt-in이다(`internal/vectors/store.go:324-360`, `docs/guides/storage-backends.md`).
- **대안**: sqlite-vec 확장, 외부 벡터 DB, ANN 기본.
- **작성자가 밝힌 이유**: X 글 "I deliberately chose to avoid external vector databases."(외부 벡터 DB를 일부러 피했다), "for personal knowledge bases, “just use SQLite” is the right level of complexity." 메모리 캐시는 "~11× faster than per-query SQLite scans at 10K+ chunks"이고 "brute-force exact search stays the default"다(`search-quality.md:107-118`). Postgres는 "multi-user server mode, pgvector ANN"용 선택이고 SQLite는 "zero-config default"로 남긴다(`git show aa37245:docs/design/p2-1-storage-abstraction.md` 13-14행. 이 문서는 `3c77152`에서 추적을 끊어 HEAD에는 없다).
- **이력**: 04-04 BLOB → 07-21 Postgres(`37d4e2c`, 본문 "NOT VERIFIED: the conformance matrix itself", 07-23 `021db37`에서 PG16 통과) → 07-25 HNSW → 08-01 mmap. vendored HNSW는 upstream 버그("recall@10 vs exact brute-force was 0–4/10")를 고친 사본이다(`internal/vectors/hnsw/VENDORED.md`).

### 3. 한 번의 큰 프롬프트가 아니라 summary → concept → article 다패스

- **결정**: Pass 1이 문서마다 summary를 쓰고, Pass 2는 raw가 아니라 summary를 묶어 concept을 뽑고, Pass 3가 concept마다 article을 쓴다(`fullpipeline.go:125-139`).
- **대안**: 문서 하나를 프롬프트 하나로 페이지까지 쓰는 단일 패스, Karpathy 원안의 index 파일 + LLM 직접 편집.
- **작성자가 밝힌 이유**: X 글 "It’s not one monolithic LLM prompt. It’s a pipeline of focused passes, each with a narrow job", "The summaries are the compiler’s intermediate representation."(summary가 컴파일러의 중간 표현이다), "The key insight: passes 2-4 are incremental."(X 글은 Diff를 Pass 1로 세므로 여기서 2-4는 이 보고서의 summary·concept·article 세 패스다). Pass 2가 summary만 보는 설계는 이 "intermediate representation" 문장에서 시작한다. 뒤에 triple evidence를 설명하면서(`a0f743e`, 07-26) 작성자는 비용 이유를 덧붙였다: "Feeding raw sources to Pass 2 instead would mean re-parsing every PDF a second time per compile, which is the most expensive thing the compiler does."(`docs/guides/graph-memory.md:39-40`) — 컴파일마다 PDF를 다시 파싱하는 것이 가장 비싸다. summary 템플릿 마지막 절도 "formatted as a comma-separated list for easy extraction"으로 Pass 2를 위해 설계됐다(`internal/prompts/templates/summarize_article.txt:11`).
- **이력**: 처음 Pass 3는 원문을 보지 않았다. 작성자는 `3841287`(04-15)의 Phase B "Document splitting (SplitByHeadings) for 3-4x faster article writing on large docs"(큰 문서의 article 쓰기를 3-4배 빠르게 하는 문서 분할)에서 `buildSourceContext`로 concept에 걸린 원문 절만 넣었다. 같은 문제를 다룬 PR #53(04-14, 외부 기여자 andreasbauer80)은 "the LLM never saw the actual source text in Pass 3"이라 진단하고 "summaries are already an interpretation and invite gap-filling"(summary는 이미 해석이라 빈칸 채우기를 부른다)을 근거로 raw 전체를 넣자고 했다. 작성자는 "superseded by main"이라며 "better token efficiency (section-aware context vs full source)"(전체 원문보다 절 단위 문맥이 토큰 효율이 낫다)를 이유로 닫았다(PR #53 리뷰, 2026-04-15). 이후 #146(concept `barium` 하나가 135만 토큰 요청)으로 `max_source_context_tokens` 100,000 예산이 생겼다(`b049d7c`, `write.go:1144-1182`).

### 4. concept 추출: 20개 묶음, summary 앞 1000바이트, 기존 이름 스냅샷 하나

- **결정**: 묶음 20개, summary는 `summary[:1000]`, 모든 묶음이 같은 기존 이름 스냅샷을 받는다(`concepts.go:98-100, 121-123, 180-184`).
- **대안**: 전체를 한 호출에, 또는 묶음마다 앞 묶음 결과를 누적해서 넘기기.
- **작성자가 밝힌 이유**: `ca308e3` "batch 20 summaries per LLM call instead of all at once (was truncating JSON on large wikis like 1107 sources)"(1107개 소스에서 JSON이 잘렸다). 스냅샷을 쓰는 이유는 "each batch receives the same existingConcepts snapshot as dedup context (not the growing allConcepts), so deduplicateConcepts at the end handles cross-batch merging"(`concepts.go:60-62`)이고, 정렬은 "map iteration order must not leak into prompt bytes"(`concepts.go:123`)다.
- **알려진 대가**: #167 원문 "Every batch is therefore blind to what the other batches propose in the same run."(같은 실행의 다른 묶음이 무엇을 냈는지 모른다), "On a from-scratch compile the fold-vs-mint instruction is inert."(처음 컴파일에는 합칠 대상 목록이 비어 지시가 무력하다).
- **[추정] 대가**: 자르기가 바이트 단위라 한국어 summary는 약 330자에서 끊기고, summary 템플릿이 Concepts 목록을 마지막 절에 두므로 긴 summary에서는 그 목록이 추출기에 닿지 않는다(사례: `concepts.go:182-183`의 `len`·슬라이스 1건, `summarize_article.txt:8-11`의 절 순서 1건). 실행해 확인하지 않았다.
- **모르는 것**: 프롬프트에 기존 이름만 넣고 별칭은 넣지 않는 이유. `git log -p -- internal/prompts/templates/extract_concepts.txt`와 관련 PR 토론을 보면 알 수 있다.

### 5. 어휘는 "지울 수 없는 내장 + config 덧붙임", DB CHECK 대신 앱 층 검증

- **결정**: 내장 relation 8종·entity type 5종은 고정이고 config로 동의어·새 종류를 더한다. SQLite CHECK를 지우고 `NewStore(db, validRelations)`가 검증한다(`a61315b`, `5c82067`, `internal/ontology/entities.go:12-18`).
- **대안**: config에서 CHECK를 동적으로 생성(작성자의 첫 제안), 어휘 무제한.
- **작성자가 밝힌 이유**: #19에서 처음엔 "Removing the DB CHECK constraint and relying on app-layer validation introduces risk."라며 동적 CHECK를 제안했다. 구현 뒤 마지막 댓글에서 뒤집었다: "SQLite doesn't support `ALTER TABLE ... DROP CONSTRAINT`, so dynamically regenerating a CHECK whenever the config changes would require table recreation on every open where the set differs."(SQLite는 제약만 지우는 문법이 없어 config가 바뀔 때마다 표를 다시 만들어야 한다). 온톨로지를 1급으로 두는 이유는 X 글 "This makes concept deduplication, contradiction detection, and gap analysis programmatic rather than heuristic."이다.
- **이력**: `c2475db`(04-12)에서 키 이름을 `relation_types`로 맞췄다. 이유는 "Users writing "relation_types:" ... had custom relations silently ignored."다. 내장 어휘가 ML 중심이라는 #92 지적에는 "it's a discoverability problem, not a code one"이라며 pack 8종으로 답했다(`917b3e3`).
- **[추정] 빈 곳**: concept 추출 프롬프트는 type을 concept·technique·claim 셋으로 고정해서, config `entity_types`는 triple 경로에만 닿는다(사례: `extract_concepts.txt:18`, `extract_triples.go:131-135` 1건). 이유는 모르는 것이다.

### 6. JSON schema에 enum을 걸지 않고 Go가 어휘를 강제한다. curation만 예외

- **결정**: TriplesSchema·ConceptsSchema·ResolveSchema에 enum이 없다. 어휘는 프롬프트로 알리고 쓰기 직전 Go가 노드·edge 하나 단위로 버리거나 `concept`로 바꾼다(`extract_triples.go:54-102, 175-291`).
- **대안**: schema enum + 실패 시 재시도, 또는 프롬프트만.
- **작성자가 밝힌 이유**: "an enum violation fails the WHOLE call — so one hallucinated predicate would cost the document's entire graph instead of one edge. The vocabulary is carried by the prompt and enforced in Go, where a bad value costs exactly one node or edge."(`extract_triples.go:56-63`, `a0f743e`) — enum 위반 하나가 문서 그래프 전체를 날리지만 Go에서 막으면 노드·edge 하나만 잃는다. resolution도 같다: "one bad value would cost the entire block's clustering rather than one cluster."(`resolve_entities.go:55-58`).
- **예외**: `CurateSchema`는 action에 enum keep/fold/drop을 건다(`curate.go:42`). 테스트 주석이 알고 고른 것임을 보인다: "Enum-invalid actions are rejected earlier by the schema — a hard call failure, covered by TotalFailureErrors."(`curate_test.go:227-231`). [추정] curation은 실패해도 "아무것도 바꾸지 않음"이라 묶음 전체 실패가 안전한 쪽이어서다(사례 2개: `curate.go:100-109` 실패 시 continue, `curate.go:62-66` "an opt-in advisory pass must not block a compile").
- **이력**: P2-4(07-23)가 provider 네이티브 structured output과 enum까지 검사하는 자체 검증기를 넣었다(`internal/llm/schema.go:158-167`). 같은 날 생긴 ConceptsSchema(`b485bcf`)에도, 사흘 뒤 P3-2(07-26)가 만든 TriplesSchema에도 enum은 처음부터 없었다. schema에 enum이 들어간 것은 08-22 CurateSchema(`4c0a708`)가 처음이다(`git log -S'"enum"' -- internal/compiler/`). enum을 걸지 않은 것은 P2-4 검증기의 엄격함 때문이라고 작성자가 밝혔다: "StructuredCompletion's fallback path validates the schema as strictly as the native one, and an enum violation fails the WHOLE call"(fallback 경로도 네이티브만큼 엄격하게 검증해서 enum 위반 하나가 호출 전체를 실패시킨다; `a0f743e`, `extract_triples.go:56-60`).

### 7. 그래프 패스는 opt-in, 기본 그래프는 LLM 없는 키워드 근접

- **결정**: triple, resolution, community, resolution 임베딩 블로킹이 모두 기본 꺼짐이다. 기본 그래프는 같은 문단의 관계 키워드 + `[[wikilink]]`로 코드가 만든다(`README.md:193-196`, `docs/guides/configurable-relations.md:7-11`, `internal/compiler/write.go:893-903`).
- **대안**: 기본 on + 비용 경고.
- **작성자가 밝힌 이유**: "the pass adds one LLM call per Tier-3 document, so a default-on upgrade would raise every existing user's compile bill without them asking. For a key that costs money, "safe default" means preserving today's spend."(`internal/config/config.go:1007-1010`) — 돈이 드는 키에서 안전한 기본값은 지금의 지출을 지키는 것이다. community·resolve 주석도 "an upgrade must not raise anyone's bill unasked"(`config.go:853-854, 936-937`).
- **묶인 약속**: 작성자는 opt-in을 비용과 산출물 불변 둘로 설명한다: "Default off: advisory behavior byte-identical, no extra LLM cost unasked"(기본 꺼짐이면 동작이 바이트까지 같고 묻지 않은 LLM 비용이 없다; `ab36031`), "Default-path behavior unchanged: parity goldens byte-identical"(`4c0a708`).
- **이력**: `41ee24c`(07-28)가 README 첫 문단까지 "out of the box the graph is keyword-proximity; triples/resolve/citations are labeled opt-in"으로 고쳤다.

### 8. concept dedup은 이름 임베딩 0.85, 그 아래 결정적 never-merge 가드

- **결정**: 새 concept 이름이 기존 이름과 cosine ≥ 0.85면 합친다. 숫자 토큰 집합이 다르거나 draft/final·primary/secondary가 한쪽만 있으면 점수와 상관없이 막는다. 합칠 때마다 WARN 로그다(`dedup.go:125-239`, `fullpipeline.go:331-334`).
- **대안**: threshold 조정, LLM 판정(결정 9).
- **작성자가 밝힌 이유**: 보고자 ivanhyphae가 #164 본문에서 측정했다: 합쳐야 할 쌍과 합치면 안 되는 쌍이 "interleaved across the entire range and **peak at the same value**"(전 구간에 섞여 같은 0.982에서 정점). 보고자는 원인을 "the token that carries the meaning — a digit, a plural, "draft" vs "final" — is the least semantically weighted part of the string."(의미를 실은 토큰이 문자열에서 가장 가볍게 반영된다)로 봤고, 실제 손실은 "`stockpile-1.md` now carries Stockpile 2's and Stockpile 3's sources"였다. 작성자는 답글에서 "you demonstrated **why no threshold can work**"라고 받아들였고, 코드 주석에 같은 원인을 적었다: "least semantically weighted part of the string ... These deterministic guards sit UNDER any similarity decision."(`dedup.go:182-184`). WARN 이유: "an auto-merge deletes a concept as its own entity — that must be discoverable"(`fullpipeline.go:331-333`).
- **남은 한계(작성자 명시)**: "same-number containment (stockpile-1 vs stockpile-1-mse-wall-footing) and synonym-media pairs (storm-water vs surface-water) remain threshold-governed"(`456e1d4`).
- **이력**: `3841287`(04-15) 임베딩 dedup → `456e1d4`(08-22) 가드. 가드가 작성자 테스트 말뭉치에서 8번 터졌고 그중 하나가 일부러 넣은 모순 쌍 `fact-v1`/`fact-v2`였다(#164 작성자 답).
- **[추정] 한국어**: 반의어 목록이 영어 두 쌍뿐이라 "초안/최종", "주/부"는 못 막는다. 숫자 토큰은 구분자(글자·숫자가 아닌 문자)로 나눈 토큰 중 ASCII 숫자를 포함한 것이라 "3호기"가 한 토큰이다. 그래서 "3호기/2호기"는 막고, "3호기"와 "3 호기"처럼 띄어쓰기만 다른 이름도 막는다(사례: `dedup.go:204-211, 231-238` 1건). 실행하지 않았다.

### 9. 전역 LLM curation: 임베딩 dedup과 둘 중 하나, fold는 자동, drop은 허가제

- **결정**: `dedup_strategy: llm`이면 새 concept 전체(이름·type·별칭·source 수)와 기존 이름을 200개씩 보고 keep/fold/drop을 고른다. fold는 자동 적용(source 합집합 + 별칭)이고 never-merge가 거부할 수 있다. drop은 `allow_drop: true`일 때만 적용한다(`curate.go:17-29, 125-167`, `4c0a708`).
- **대안**: #167이 제안한 검토 대기열(`--review/--apply`), 목표 concept 수 지정. 작성자는 둘 다 일부러 v1에서 뺐다: "the current shape (folds auto-apply, drops logged-and-gated) covers the reported failure modes without new UX"(지금 모양만으로 보고된 실패가 다 막혀 새 UX가 필요 없다, #167 작성자 댓글).
- **작성자가 밝힌 이유**: 보고자 ivanhyphae의 #167 측정은 141개 문서에서 concept이 컴파일마다 77 → 85 → 136 → 264 → 315 → 322 → 384로 늘기만 했다는 것이다. 보고자는 "A global selectivity target cannot be enforced by prompting."(묶음 프롬프트로는 전역 선택 기준을 강제할 수 없다)라고 진단했고 작성자는 "On your economics argument — agreed"로 받았다. 비용은 작성자가 "the pass runs immediately before the most expensive stage, so on any corpus where it suppresses articles it's net-negative cost."라고 답했다. 안전 규칙: "Folds auto-apply — they're additive ... a drop deletes a concept, so it stays a logged proposal until you opt in." 둘 다 돌리지 않는 이유: "running both is incoherent — embedding merges would pre-empt judgment"(`curate.go:19-21`).
- **이력**: 그전에는 `llm`이 문서에만 있고 구현이 없어 "setting it **silently disabled concept dedup entirely**"였다(#167 작성자 댓글). 이제 알 수 없는 값은 config 로드에서 실패한다.

### 10. evidence gate와 manifest 별칭 영속

- **결정**: source가 `min_concept_sources`(기본 1)보다 적은 concept은 article·manifest·entity·cites 모두 만들지 않는다. manifest에 별칭을 합집합으로 저장해 다음 컴파일의 약어가 기존 concept으로 접힌다. 추출한 이름이 manifest 별칭과 일치하면 길이와 상관없이 manifest의 정식 이름으로 접고(`concepts.go:379-396`), 같은 실행 안에서 별칭이 겹치면 정규화 이름이 긴 쪽이 정식 이름이 된다(`concepts.go:423-450`; 그 밖 `evidence_gate.go:10-28`, `manifest.go:215-237`).
- **대안**: 사후 confidence 필터, CLI 플래그.
- **작성자가 밝힌 이유**: #128(Caltrans 토양 정화 문서의 도면 범례 약어 `wsp`, `rap`이 빈 article이 된 사례)에 "A concept with no declared sources is fully suppressed *before* any LLM call ... This is the load-bearing fix — it kills both the boilerplate articles and the spend, rather than relying on post-hoc confidence."(LLM 호출 전에 막아 쓸모없는 글과 비용을 함께 없앤다). 별칭: "so "rap" extracted in compile N+1 folds into "remedial-action-plan" extracted in compile N." config로 둔 이유: "this is per-vault policy, not per-invocation." 합집합 이유: "a replace would wipe accumulated evidence and, once aliases exist, the very aliases acronym dedup relies on"(`manifest.go` 주석, compile 노트 #증분).
- **이력**: `486f486`, `1f91f98`, `7e9f0e9`(07-30).

### 11. entity resolution: 합치지 않고 잇는다, 기본값은 되돌리기 비용으로 정한다

- **결정**: 두 entity 행을 모두 남기고 canonical이 alias의 edge를 `derived_relations`로 받는다. `--unlink`가 정확히 되돌린다. canonical은 Go가 고른다(article 있는 행 → 최신 created_at → id). 자동 적용은 threshold < 1.0, same_referent, broader 아님, confidence ≥ threshold, 한쪽에 설명문 있음의 다섯 조건이다(`resolve_entities.go:240-345`, 이 보고서 작성 때 다시 열어 확인).
- **대안**: 행 병합(collapse), 영구 검토 전용.
- **작성자가 밝힌 이유**: 행을 지우는 방식은 "tried and abandoned across three spec revisions: the row that owns an article and the row that owns a description are different rows with different ids"(`internal/ontology/aliases.go:256-264`). canonical을 Go가 고르는 이유: "A model-nominated canonical that Go then overrode would make the Broader answer certify a direction that was never used"(`resolve_entities.go:36-40`). 설명문 요구: "without it a lowered threshold would link entities on surface-name similarity with no grounded evidence at all"(`resolve_entities.go:312-320`). 1.0을 절대로 다루는 이유: "a review-only setting a model can defeat by being confident is not a setting at all."(`resolve_entities.go:324-335`). source type 제외: "A source entity's identity IS its path"(`resolve_entities.go:1028-1032`).
- **이력**: 2026-07-27 하루에 세 번 움직였다. 0.85(`dc32afd`) → 1.0 검토 전용(`94dbe1c`, "A link is not reversible — there is no un-link command ... so it must not happen without someone deciding.") → derived edge를 별도 표로(`4d44eed`, "a copy is indistinguishable from an original — which is why a link could never be undone") → 다시 0.85(`26dba4b`, "now that --unlink makes a mistaken link cost one command"). 문서 표현은 "`--unlink` changed the economics"다(`graph-memory.md:159-162`).
- **[추정] 일반 규칙**: 자동화의 기본값을 되돌리기 비용으로 정한다는 규칙을 실제로 적용한 사례다(사례: 위 commit 3개).

### 12. 깨진 wikilink는 지우고, "See also"는 공유 source로 채운다

- **결정**: 컴파일 끝에 없는 대상의 `[[x]]`를 `x`로 바꾼다(`strip_broken_links` 기본 true, `pipeline.go:526-531`). article 프롬프트의 관련 concept은 같은 source를 인용하는 concept 상위 8개다(`write.go:775-786`).
- **대안**: 링크를 남겨 두고 나중에 채우기(처음 설계), stub article 생성(#93), 벡터 유사도.
- **작성자가 밝힌 이유**: 처음엔 `db1e71d` "Wikilinks kept speculatively (wiki-style) — resolve when target article is created in future compiles"였다. `2260770`(06-04)이 기본을 바꿨다: "the prior design assumption ("future compiles will resolve these naturally") doesn't hold for non-ML corpora — reporter saw 75 % phantom links across 145 articles." #106에서 관련 concept 함수가 `return nil` stub이라 article 85%가 고아였다. 공유 source를 고른 이유: "it needs no embeddings, works on a cold compile, and yields real slugs that resolve to article files"(`write.go:783-786`). 8개 상한: "a source cited by many concepts would otherwise flood every article with links"(`write.go:775-779`).
- **어긋남**: X 글(04-05)은 검색이 "core to how the compiler discovers related concepts"라고 했지만 관련 concept 함수는 07-04(`ab34b19`)까지 stub이었다.
- **미해결**: #93 stub 생성은 "Not implementing in the immediate term", `ConnectionsPass.CanAutoFix()`는 지금도 false다(`internal/linter/passes.go:221`).

### 13. frontmatter는 코드가, 본문만 LLM이 쓴다

- **결정**: 컴파일 경로(Pass 3)에서 concept·aliases·sources·created_at은 코드가 만들고, LLM frontmatter는 지운다. `confidence`와 사용자 정의 필드만 본문 마지막 15줄의 `키: 값`에서 긁는다(`write.go:268, 465-557`). `created_at`은 원문 날짜가 아니라 컴파일 시각(`timeNow(loc)`)이고, 작성자 필드는 없다(`write.go:465-490`).
- **다른 쓰기 경로**: MCP `wiki_write_article`(과 `PUT /v1/articles/{concept}`)은 에이전트가 준 본문을 frontmatter째 그대로 쓰고, manifest에는 sources 없이 concept을 등록한다(`internal/mcp/tools_write.go:272, 296`). 그래서 사실 필드를 지키는 것은 컴파일 경로뿐이다.
- **대안**: LLM이 frontmatter까지 쓰게 하기(처음 방식).
- **작성자가 밝힌 이유**: `f4fd525` "Article frontmatter was duplicated ~60% of the time because the prompt asked the LLM to generate it ... Redesign: ground-truth fields ... are always code-generated."(LLM에게 맡겼더니 60%가 중복됐다). 주석: "code builds frontmatter from ground-truth data"(`write.go:268`).
- **[추정] 빈 곳**: 같은 이름 concept이 새 source에서 다시 나오면 frontmatter `sources`는 manifest 합집합이 아니라 이번 실행의 `concept.Sources`만 담는다(사례: `write.go:471`과 `concepts.go:321-333` 1건). 실행해 확인하지 않았다.

### 14. 결정성과 compile key, 미완료 실행은 manifest·compile key를 남기지 않는다

- **결정**: 같은 입력이면 바이트까지 같은 산출물을 낸다. compile key = SHA-256(소스 해시, PipelineVersion, 템플릿 해시, pass별 모델, 출력에 영향 주는 config, 임베딩 식별자)이고 구성 요소별 preimage를 저장해 drift 원인을 설명한다(`compilekey.go:25-55`). Pass 2·3이 끝나지 않으면 pass 표시·compile key·manifest를 저장하지 않는다(`pipeline.go:500-504, 540-544, 1206-1213`). 이미 쓴 summary·article 파일과 색인 행은 남는데, 작성자는 이를 "an incomplete run persists no new CLAIMS; rows already applied are content-identical on the next run's rewrite"(미완료 실행은 새 claim을 남기지 않고, 이미 적용된 행은 다음 실행이 같은 내용으로 다시 쓴다)로 정리했다(`write.go:170-171`). CHANGELOG와 git auto-commit은 이 조건 없이 돈다(`pipeline.go:546-549, 575-580`).
- **대안**: 소스 해시만 키로 쓰기, 부분 롤백.
- **작성자가 밝힌 이유**: "**identical inputs produce byte-identical artifacts**, and **unchanged content is never recompiled**."(`docs/determinism.md:3-4`). 업그레이드 뒤 첫 실행은 key를 채택만 한다: "the never-re-bill pledge applies from run one"(`determinism.md:212-219`). 미완료 무저장: "the earlier surgical rollback (RemoveSource on just the sources) left the run's concepts orphaned"(`pipeline.go:1206-1211`) — 부분 롤백이 실제로 실패해서 바꿨다. 한계도 적었다: "LLM providers are not bit-stable across their own releases"(`determinism.md:195-200`), `PipelineVersion` 올리기는 "honor-system"이다(`determinism.md:250-253`).
- **이력**: 미완료 실행 무저장은 P1-1 `1c317d3`(07-19)에서 왔다. compile key는 SPEC-04(08-02~08-05)이고 첫 commit은 `5eca17b`(08-03)다. 이후 새 knob마다 compile key 등록을 이슈 답에서 밝힌다(#144 "The knob is in the compile key", #146 "registered in the compile key", #167 "Both knobs are in the compile key").

### 15. 계층형 컴파일: 색인은 싸게, LLM 컴파일은 중요한 것만

- **결정**: tier 0(FTS만), 1(+원문 청크 벡터), 2(코드 구조 파싱), 3(전체 LLM)으로 나눈다. 기본 `default_tier`는 3이다. 검색 적중 3회면 승격한다는 설정이 있다(`tiers.go:79-111`, `internal/config/config.go:1119`). 강등은 마지막 질의 뒤 90일, 질의가 한 번도 없으면 생성 뒤 90일이고 기본 켜짐이다(`internal/compiler/items.go:418-431`, `config.go:503-508`).
- **질의 적중의 실제 경로**: 적중을 세는 곳은 MCP `wiki_search`(와 같은 handler를 부르는 `/v1`) 하나이고, 그것도 아직 컴파일되지 않은 일치가 있을 때만 센다(`internal/mcp/server.go:417-429`). web UI `/api/search`와 Q&A는 세지 않는다(`internal/web/server.go:716`). 넘기는 값은 검색 결과 DocID인데 tier 0/1 문서의 DocID는 `src:<path>`이고(`index.go:60-61`), `IncrementQueryHits`는 접두어 없이 `compile_items.source_path`와 맞춘다(`items.go:214-229`). [추정] 그래서 tier 0/1 문서에는 적중이 쌓이지 않아 질의 기반 승격이 발동하지 않는다(사례: ID 형식 불일치 1건, 미실행).
- **대안**: 모든 문서 컴파일(처음 방식).
- **작성자가 밝힌 이유**: "A single document takes ~8 minutes to fully compile"(문서 하나를 끝까지 컴파일하는 데 약 8분)이고, 같은 문서의 표는 10만 문서·`max_parallel=4`에서 139일로 잡는다(`docs/guides/large-vault-performance.md:10-16`). `3841287` "Architecture shift from "compile everything" to "index fast, compile what matters" for vaults of 10K-100K+ documents."
- **이력**: 기본을 1로 했다가 `ef410eb`에서 3으로 되돌렸다: "default_tier: 1 caused new users to see "0 summarized, 0 articles" with no error"(#57).
- **코드와 문서의 차이**: 가이드는 frontmatter `tier:`를 최우선이라 하지만(`large-vault-performance.md:102-111`) 유일한 호출부가 frontmatter 자리에 nil을 넘긴다(`pipeline.go:1283`, 이 보고서 작성 때 grep으로 호출부가 하나뿐임을 확인). 승격 신호 `cluster_size`·`manual_tag` 등도 config와 compile key 밖에서 쓰이지 않는다(compile 노트 #3).

### 16. Q&A 답은 기본으로 검색에 다시 들어가지 않는다

- **결정**: `trust.include_outputs` 기본 `"false"`. `"true"`가 아니면 답을 `wiki/under_review/`에 두고(`internal/query/query.go:645-656`), consensus(비슷한 질문의 답 일치) + grounding(claim별 LLM 판정)을 거쳐 `outputs/`로 승격한다. 기본 `"false"`에서는 승격되더라도 `output:` 문서가 어떤 검색 표면에도 나오지 않는다. 승격 뒤 검색에 들어가는 것은 `include_outputs: verified`일 때뿐이다. 이 규칙은 하나의 술어로 모든 검색 표면에 걸린다(`internal/trust/predicate.go:15-42`, `internal/search/run.go:299-307`).
- **대안**: 답을 바로 색인(현재 `"true"` 레거시 모드), 다중 모델 검증.
- **작성자가 밝힌 이유**: #74 원 보고 "One wrong answer spreads."에 작성자는 "treat LLM outputs as *claims* rather than *facts*. They need independent verification before entering the trusted corpus"와 "don't include outputs in retrieval context. That kills the feedback loop at zero cost."로 답했다. 검증이 쉬운 이유: "That's a narrow entailment check". 같은 청크 증거를 확인으로 세지 않는 이유는 반복이 "deterministic repetition, not independent verification"이기 때문이다(#74). 모든 표면으로 넓힌 이유: "an agent searching the wiki could read what a Q&A answer would refuse to cite"(`3b88975`).
- **이력**: `ff03c42`(05-09) 도입, 0.2.2에서 모든 검색 표면으로 확장했다.

### 17. 검색은 문서 단위로 doc leg와 chunk leg를 함께 RRF, graph를 세 번째 채널로

- **결정**: chunk FTS·doc FTS·chunk vector·doc vector·graph를 문서 단위로 합산한다. vector는 BM25로 미리 거르지 않고 전수 탐색한다(`search/pipeline.go:98-168`).
- **대안**: 청크 RRF 후 문서 중복 제거(처음), BM25 prefilter(처음).
- **작성자가 밝힌 이유**: "agreement across granularities (the same document matching both as a whole and in one passage) ranks above a single strong hit"(`search-quality.md:27-30`, `9b1c419`). prefilter 제거: "silently destroys recall for multilingual corpora"(`ccab065`, 폴란드어 재현 사례). graph 채널: "the graph channel reaches documents connected to the query's entities even when neither lexical nor vector similarity finds them"(`search-quality.md:362`), "An empty ontology costs nothing and leaves results byte-identical, so the graph earns its place incrementally."(ontology가 비어 있으면 비용이 없고 검색 결과도 바이트까지 같다; `README.md:61-62`). rerank 혼합 75/60/40은 qmd에서 가져왔고(`c1f1a3d` "inspired by qmd analysis"), 목적은 "protects high-confidence retrieval results from reranker noise"(확신 높은 검색 결과를 reranker 잡음에서 지킨다)다(`search-quality.md:59`). pending alias는 순위에 쓰지 않는다: "pending rows are un-approved proposals and must never influence ranking"(`graphleg.go:126-128`).
- **이력**: 0.7/0.3은 첫 commit `4876ddb`의 config 기본값이고(`internal/config/config.go:101-102` 당시), 07-28 `9b1c419`에서 처음 이 경로에 적용됐다("config weights honored on this path for the first time").
- **모르는 것**: 0.7/0.3과 graph 0.2라는 숫자 자체의 근거. 주석은 "spec §2.2, ADR-037"만 가리킨다(`pipeline.go:55-60`). 비공개 ADR을 보거나 작성자에게 물어야 안다.

### 18. 단일 운영자, 쓰기 프로세스 하나, 권한은 레포 밖

- **결정**: `engine.Open`이 `.sage/engine.lock` 배타 flock을 잡는다. Postgres도 advisory lock으로 쓰기 주체를 하나로 둔다. 사용자·문서 단위 권한은 없고, 다중 workspace serve는 root 토큰 하나가 모두를 지킨다(`pkg/engine/doc.go:17-22`, `internal/serve/multi.go:125-127`).
- **대안**: 행 단위 다중 writer, 앱 안 RBAC, OIDC.
- **작성자가 밝힌 이유**: "sage-wiki is a **local-first, single-operator** knowledge base ... There is no multi-user authorization model, and none is attempted"(`docs/security.md:9-14`). "Per-workspace auth is a SPEC-06 non-goal — operators compose tenancy in front; one root token guards every workspace"(`multi.go:126-127`). Postgres도 "the single-writer process model is unchanged"다(`CHANGELOG.md:1130-1142`). X 글은 다중 작성자를 "a genuinely different problem involving merge conflicts, access control, and multi-writer consistency."라고 불렀다. 팀 가이드의 처방은 "Designate one compiler."다(`docs/guides/team-setup.md:727-738`).
- **빈틈**: `serve --ui`와 MCP stdio·SSE는 잠금 없이 쓴다("pre-existing, lock-free", `docs/guides/serve-mode.md:15-17`). bearer 토큰은 여러 개 둘 수 있지만 어느 토큰으로 들어왔는지 요청 context에 싣지 않는다(`internal/serve/auth.go:85-101`).

### 19. REST 표면을 MCP tool 레지스트리로 몬다

- **결정**: `/v1` REST와 serve REST는 자체 로직 없이 `(*mcp.Server).CallTool`로 보낸다. 결과 번역기도 하나다(`internal/api/dispatch.go:37-79`, `internal/serve/server.go:386-406`). web UI `/api/*`·CLI·TUI·`pkg/engine`은 이 레지스트리를 거치지 않고 엔진 함수를 직접 부른다(#큰 구조).
- **대안**: REST용 service 층을 따로 두기.
- **작성자가 밝힌 이유**: "16-route /v1 REST facade over the 18 MCP tools (dispatch via (*mcp.Server).CallTool, zero business logic)"(`d0fd8d6`), "every /v1 route reaches its capability through the same function the tool registers, never a copy"(`dispatch.go:37-39`). 에이전트에게 tool 쓰는 법을 skill 파일로 넣는 이유: "Agents ignore sage-wiki's 17 MCP tools because nothing in their context says when to use them."(`0dd13f5`).
- **치른 것**: tool 결과가 text라 REST가 JSON으로 되돌려 파싱한다(`dispatch.go:66-78`). MCP 쓰기 tool은 컴파일 경로의 정규화·동의어 대조·evidence 검사를 거치지 않는다(#축별 분석의 2번).

### 20. triple evidence는 raw가 아니라 summary에서 인용하고 부분 문자열로 검증한다

- **결정**: evidence 구절은 컴파일된 summary에서 따오고 `source_doc`은 원본을 가리킨다. 구절이 summary에 정규화 후 부분 문자열로 있는지 확인하고 없으면 edge를 버린다(`extract_triples.go:905-952`).
- **대안**: raw 원문 인용, 검증 없이 schema만.
- **작성자가 밝힌 이유**: "compile outputs are data; schema validation alone cannot stop a fabricated evidence span"(`extract_triples.go:922-927`). summary 인용 이유: "Pass 2 sees summaries, not source content"(`internal/store/domain.go:105-109`, `71e0ef1`). 작성자는 한계로 인지한다. X 글: "sage-wiki tracks source-level freshness but not proposition-level."
- **이력**: #144에서 인용 검증 방향을 "verification substrate = exact quoted spans (footnote-style `[^n]`...)"로 정했고 열려 있다. 줄 번호를 쓰지 않는 이유는 "A line reference doesn't prove anything by itself." / "Line references rot under trivial edits."다.

### 21. 품질 점수는 LLM 없이, 기본은 경고만, 재작성은 opt-in

- **결정**: format·grounding·coverage·wikilink·anti-pattern 5차원(가중 0.15/0.30/0.20/0.15/0.20)을 잰다. 0.5 미만이면 경고하고, `quality.retry`면 파일을 지우고 1회 다시 쓴다(`confidence.go:31-39`, `fullpipeline.go:547-586`).
- **대안**: 차단 gate 기본, LLM 판정.
- **작성자가 밝힌 이유**: #97 "I'd lean toward surface only with a default threshold of 0.5 for the warning, no gate. Easy to opt into stronger behaviors later; hard to take away." 파일을 먼저 지우는 이유: "leaving the bad article there would turn the retry into an 'improve this bad content' call"(`ab36031`). lexical grounding의 한계는 #144가 짚었다: "it does **not** catch confidently-written, well-grounded-*sounding* articles that contain specific facts ... which are simply wrong".

### 22. 원문은 untrusted 구획으로 감싼다

- **결정**: 원문·summary·질문을 넣는 프롬프트마다 `<untrusted_source>`로 감싸고 위조 태그를 무력화한다. 파일 경로도 구획 안에 넣는다(`internal/prompts/untrusted.go:8-14`, `extract_triples.go:123-129`).
- **작성자가 밝힌 이유**: "The documents ingested into the wiki are treated as untrusted input. A document may be hostile"(`docs/security.md:16-19`). summary도 2차 주입 경로로 본다: "Summaries are LLM output over untrusted text"(`concepts.go:185-187`). 기존 article은 감싸지 않으며 이를 "accepted risk"로 적었다(`untrusted.go:12-14`).

### 23. 도메인 어휘·프롬프트는 pack으로 묶어 배포한다

- **결정**: `pack.yaml` 하나가 config, ontology overlay(entity_types, relation_types + 동의어), article_fields, prompts, skills, parsers를 함께 묶는다(`internal/pack/manifest.go:22-44`). 내장 pack은 8종이고(`internal/pack/bundled/`), 원격 registry 기본값은 `github.com/xoai/sage-wiki-packs`다(`internal/pack/registry.go:13`). 설치는 기본 merge 모드에서 이미 있는 프롬프트 파일을 건너뛰고(fill-only), replace 모드만 덮어쓴다(`internal/pack/merge.go:197-216`).
- **대안**: 내장 어휘를 도메인별로 늘리기.
- **작성자가 밝힌 이유**: 내장 어휘가 ML 중심이라는 #92 지적에 "it's a discoverability problem, not a code one"(코드 문제가 아니라 찾기 어려운 문제다)이라며 pack 8종으로 답했다(`917b3e3`).
- **[추정] 빈 곳**: 내장 pack 프롬프트 16개 중 `extract_*`·`distill_*` 이름 13개는 컴파일이 렌더하지 않는다(사례: 컴파일이 부르는 템플릿 이름은 `summarize_`+type과 고정 이름 `extract_concepts`·`extract_triples` 등뿐이고, `extract_meeting` 같은 이름을 부르는 Go 코드가 0건, `summarize.go:263-267`, `concepts.go:194` 1건). 실행해 확인하지 않았다.

## 축별 분석

축 이름과 뜻은 앞선 비교 문서(`llm-wiki-implementations/lab/reports/00-comparison.md` #설계 축별 스펙트럼)를 따른다.

#### 1. 실행 형태

비교 문서의 "CLI·SDK 엔진(+MCP)" 칸이고, 그 위에 REST·web UI·다중 workspace 서버까지 얹었다(#큰 구조). 엔진이 LLM을 직접 부르고 산출물은 코드가 쓴다.
치르는 것은 크기다. 비테스트 Go만 83,709줄, 패키지 47개다. 대신 설치는 바이너리 하나다(결정 1).

#### 2. 규칙의 위치

컴파일 경로는 "LLM에게 쓰기 도구 없음"이다. 패스마다 엔진이 LLM을 부르고, frontmatter·어휘·evidence·canonical을 쓰기 직전 Go가 강제한다(결정 6, 11, 13, 20).

비교 문서가 짚은 "gate를 거치지 않는 쓰기 경로"는 여기도 있다. 정규화·동의어 대조·evidence 검사 없이 저장소 층의 어휘 검사 한 겹만 거치는 경로가 다섯이다.

| 경로 | 하는 일 | 위치 |
|---|---|---|
| MCP `wiki_write_article`(+ `PUT /v1/articles`) | 에이전트 본문을 frontmatter째 쓰고 sources 없이 concept 등록 | `internal/mcp/tools_write.go:244-303` |
| MCP `wiki_add_ontology`(+ `/v1/ontology/*`) | entity·relation을 id 그대로 저장 | `tools_write.go:305-364` |
| MCP `wiki_write_summary`(+ `PUT /v1/summaries`) | 에이전트가 쓴 summary를 저장하고 manifest에 compiled 표시를 남긴다 | `tools_write.go:184-241`, `docs/guides/http-api.md:118` |
| CLI `write summary/article`, `ontology add` | 위 둘의 CLI판 | `cmd/sage-wiki/write_cmd.go:26-38`, `ontology_cmd.go:33-34` |
| CLI `scribe` | Claude Code 세션 JSONL을 LLM으로 entity·relation화해 `AddEntity`·`AddRelation`으로 바로 넣는다 | `internal/scribe/session.go:106-125`, `cmd/sage-wiki/main.go:166-170` |

[추정] 에이전트가 직접 쓰면 "Foo Bar"와 "foo-bar"가 별개 entity 행이 된다(사례: `tools_write.go:320`이 id를 그대로 넘김 1건).

#### 3. 저장 구조

디렉터리는 산출물 종류별이다: `wiki/summaries/`, `wiki/concepts/`, `wiki/communities/`, `wiki/outputs/`, `wiki/under_review/`. concept article은 평면 한 단계다.

메타데이터는 코드가 쓰는 YAML frontmatter, `.manifest.json`, SQLite 표 셋에 나뉜다. 파생 상태는 많다(compile_items 큐, entity_aliases, derived_relations, pending_outputs, communities 등 마이그레이션 V1~V15, `internal/storage/db.go:156-173`).

상태가 많은 대가를 "파일이 진실, DB는 재구축"(`storage-backends.md:62`)과 시작 시 reconcile(`internal/wiki/reconcile.go:48`)로 갚는다.

#### 4. Ingest

| 하위 선택 | 이 레포 |
|---|---|
| 사람 참여 | 컴파일 중에는 끼지 않는다. 사람이 미리 정하는 자리는 넷이다: `.wikitier`, `prompts/` 덮어쓰기(9개 전부, `docs/guides/customizing-prompts.md:1-40`), `summarize-{type}.md` + `type_signals`(파일명·본문 키워드로 타입 지정, `summarize.go:263-267`, `internal/config/config.go:830-838`), opt-in 패스. 프롬프트와 `type_signals`는 compile key에 들어가 바꾸면 영향받는 문서만 다시 돈다(`compilekey.go:360`) |
| 형식 변환 | `internal/extract`가 PDF·DOCX·XLSX·PPTX·CSV·EPUB·메일(.eml/.msg)·이미지(vision LLM)·코드를 텍스트로 바꾸고, 목록 밖 확장자는 `parsers/parser.yaml`의 외부 파서로 넘긴다. 외부 파서는 sandbox가 없으면 `trust_external` 없이는 실행을 거부한다(`internal/extract/extract.go:51-84`, `external.go:110-118`) |
| encoding gate | `ingest`는 UTF-16/32와 UTF-8이 아닌 텍스트(EUC-KR·CP949 txt 등)를 거부하고, binary 추출기 목록(.pdf·.docx·.xlsx·.pptx·.epub·이미지)에 없는 binary(.hwp, .msg, 옛 .doc/.xls/.ppt)도 거부한다(`internal/wiki/ingest.go:42-79`) |
| 증분 판정 | 코드가 세 겹으로 본다: 파일 SHA-256, compile key, summary `source_hash` 재사용(`diff.go:119-130`, `determinism.md:66-96`, `summarize.go:203-236`) |
| 실패 복구 | 미완료 실행은 manifest·key 무저장(결정 14), 큐 lease 5분 + heartbeat, 5회 실패면 dead letter, `--fresh`가 되살림(`pipeline.go:222-226, 1206-1213`, `worker_cycle.go:489-504`) |
| 자동 감시 | `compile --watch`(fsnotify·polling, `watch.go:23-163`), serve worker |
| 소스당 페이지 | 상한 없음. concept 수는 evidence gate와 curation이 사후에 줄인다(결정 9, 10) |

#### 5. 근거 추적 단위

비교 문서의 "페이지 단위 출처"에 "edge 단위 literal 일치"를 더한 자리다.

concept → source는 문서 단위 `cites` edge다(`write.go:364-382`). triple edge는 `source_doc` 하나와 summary에서 따온 evidence 구절을 갖고, 코드가 부분 문자열로 확인한다(결정 20).

article 문장이 어느 원문에서 왔는지는 추적하지 않는다. 품질 점수의 grounding은 어휘 겹침이다(`confidence.go:196-255`). 문장 단위 인용 검증은 #144로 설계 중이다.

raw 청크(`src:<path>:c<i>`)는 검색용이고 `chunks_meta.start_offset/end_offset`을 채우지 않아 원문 위치를 가리키지 못한다(query-store 노트 P8, `index.go:288-293`).

#### 6. Link

코드가 거는 링크와 LLM이 거는 링크가 섞인다.

| 링크 | 누가 | 위치 |
|---|---|---|
| article 본문 `[[x]]` | LLM이 쓰고, 코드가 별칭을 정식 이름으로 바꾸고 끊긴 것을 지운다 | `write.go:264-286`, `pipeline.go:526-531` |
| "See also" 후보 | 코드가 공유 source 상위 8개를 골라 프롬프트에 준다 | `write.go:775-786` |
| 키워드 근접 typed edge | 코드(같은 문단의 `[[링크]]` + 관계 동의어) | `configurable-relations.md:7-11`, `write.go:893-903` |
| `cites` edge | 코드(concept → source 문서) | `write.go:364-382` |
| triple typed edge(opt-in) | LLM이 내고 Go가 어휘·evidence를 검증 | `extract_triples.go:175-291, 905-952` |
| alias 링크(opt-in) | LLM이 판정하고 Go가 canonical과 자동 적용을 정함 | `resolve_entities.go:240-345` |

typed 관계는 내장 8종 + config다. 내장 동의어는 영어·중국어뿐이라 한국어 문서에서는 config로 더해야 키워드 edge가 생긴다(`internal/ontology/relations.go` `BuiltinRelations`).

#### 7. Lint

"결정적만, 보고만"이다. 8개 pass 모두 LLM이 없고 자동 수정은 style 하나다(`internal/linter/runner.go:95-108`). sage-why 노트는 7종이라 적었지만 코드는 8개다(이 보고서 작성 때 다시 열어 확인).

의미 문제는 lint 밖이다. consistency는 이미 있는 `contradicts` edge를 나열할 뿐이고, connections는 vector가 비슷한데 edge가 없는 쌍을 info로 낸다(`passes.go:190-292`).
gate 성격은 컴파일 안의 품질 점수(opt-in 재작성)와 evidence gate가 맡는다.

#### 8. stale·모순 처리

| 대상 | 방식 | 위치 |
|---|---|---|
| article | 제자리 재작성. Pass 3가 기존 article을 입력으로 넣는다 | `write.go:212-249` |
| graph edge | bi-temporal(`valid_from`·`valid_to`·`invalidated_by`). functional 관계는 새 edge confidence ≥ 0.8이면 이전 것을 무효화하고 낮으면 검토. `contradicts`는 항상 검토. `as_of` 질의 | `extract_triples.go:537-577`, `graph-memory.md:305-339` |
| Q&A 답 | `include_outputs: verified`일 때만 인용 파일 hash가 바뀐 confirmed 답을 stale로 강등. 같은 질문에 다른 답이면 conflict | `trust/source_check.go:35-61`, `pipeline.go:561-573`, `hooks.go:199-219` |
| 파일 | staleness lint가 mtime 90일을 본다 | `passes.go:368-397` |
| 원문 날짜 | frontmatter `date:` → 파일 mtime → manifest added_at 순으로 정해 edge `valid_from`, article source_date(기여 소스 중 최댓값), 검색 recency 가산에 쓴다. DOCX·PDF의 작성일·작성자 속성은 어떤 추출기도 읽지 않는다(grep 0건). 메일만 From·Date를 본문 텍스트에 넣는다 | `internal/sourcedate/sourcedate.go:30-47`, `extract_triples.go:423-441`, `write.go:396-410`, `search/run.go:268-284`, `internal/extract/email.go:32-43` |

`contradicts`를 자동 무효화하지 않는 이유는 "an A-contradicts-B edge does not identify which specific fact it disputes."다(`graph-memory.md:337-339`). 문서끼리 수치가 다른 것을 찾는 장치는 없다.

#### 9. 사람 개입

기본은 자율이다. 사람이 끼는 자리는 opt-in 리뷰 큐 셋이다.

| 자리 | 사람이 하는 일 | 위치 |
|---|---|---|
| alias 링크 | pending을 `--apply`/`--reject`, 적용된 것을 `--unlink` | `cmd/sage-wiki/ontology_resolve.go:34-37` |
| curation drop | `allow_drop`을 켜기 전까지 로그로만 남는다 | `curate.go:125-131` |
| Q&A 답 | `outputs reject/resolve/clean`, 수동 승격 | `docs/guides/output-trust.md:194-259` |

사람이 미리 정하거나 직접 쓰는 자리도 있다. `prompts/` 덮어쓰기와 `type_signals`(#축별 분석의 4번), CLI `ontology add`·`write article`(#축별 분석의 2번)이다.

사람이 컴파일된 article을 직접 고쳐도 보호 장치(잠금 필드, 편집 표시)는 없다. 그 concept이 다시 컴파일되면 Pass 3가 고친 파일을 "Existing article (update/expand)" 입력으로 넣고 LLM 출력으로 덮어쓰며, frontmatter도 코드가 다시 만든다(`write.go:214-238, 465-490`, `internal/prompts/templates/write_article.txt:7-9`). 사람 편집은 다음 LLM 입력으로만 살아남는다.

결정 기록은 `decided_by` = `auto`/`user`/`unlink`뿐이고 사람 신원이 없다(`internal/store/domain.go:160`). CLI를 돌리는 누구나 `user`가 된다.

비교 문서의 질문 "승인 표시를 agent가 만들 수 있나"에는 "있다"가 답이다. [추정] MCP·CLI 어디에서도 결정 주체를 TTY나 사람 인증에 묶지 않는다(사례: `decided_by`가 문자열 하나 1건, `internal/serve/auth.go:85-101`이 신원을 싣지 않음 1건).

#### 10. 동시성·안전

| 장치 | 위치 |
|---|---|
| workspace 배타 flock(CLI compile·capture·query, serve --addr) | `pkg/engine/lock.go:1-60` |
| SQLite 쓰기 연결 1개, `_txlock=immediate`, WAL, `busy_timeout=5000`, 프로세스 안 mutex | `internal/storage/db.go:33-126` |
| 미완료 실행 무저장, manifest 3-way 병합 | `pipeline.go:540-544`, `internal/manifest/merge.go:48-57` |
| write-then-index 순서 + 시작 시 reconcile | `tools_write.go:184-303`, `cmd/sage-wiki/main.go:702-706` |
| `output_index` hash를 마지막에, trust confirmed를 마지막에 | `internal/storage/output_index.go:47-49`, `trust/promote.go:144` |
| S3 mirror commit pointer를 마지막에, PITR | `docs/guides/remote-mirror.md:37-40` |
| Idempotency-Key(메모리 LRU 1000개·24h) | `internal/api/idempotency.go:11-19, 184-215` |
| 자원 한도를 한 곳에, 0은 "끔"이 아님 | `internal/limits/limits.go:33-43`, `docs/security.md:32-35` |

빈틈은 잠금 없는 표면(`serve --ui`, MCP stdio·SSE)과 MCP `wiki_compile`이 coordinator를 건너뛰는 것이다(`internal/mcp/tools_compound.go:99-121`). [추정] MCP `wiki_capture`는 다른 호출이 같은 제목 slug를 내면 앞 파일을 덮는다(사례: `tools_write.go:527`의 `os.WriteFile` 1건). 실행해 확인하지 않았다.

#### 11. Query·검색

| 하위 선택 | 이 레포 |
|---|---|
| 검색 | hybrid 3채널 RRF(BM25·vector·graph) + 선택적 확장·rerank(결정 17). index 파일은 없다 |
| 원문으로 내려가기 | 부분적이다. tier 0/1의 `src:` 문서가 걸리면 raw 파일을 읽는다(`query.go:614-616`). Q&A는 청크로 찾고 article 파일 전체를 문맥에 넣는다 |
| 되저장 | 저장하되 격리한다. 기본은 `under_review/`이고, 기본 `"false"`에서는 승격된 답도 검색에 들어가지 않는다. consensus·grounding·수동 승격 뒤 검색에 들어가는 것은 `include_outputs: verified`일 때뿐이다(결정 16) |

코드 읽기로 찾은 어긋남이 있다.
summary 문서의 DocID는 raw 경로 그대로인데 `docIDToArticlePath`는 `concept:`·`summary:`·`output:`·`src:` 접두어만 알아서 빈 경로를 돌려준다(`query.go:600-618`, 이 보고서 작성 때 다시 열어 확인). [추정] 그래서 강화 Q&A 경로에서 summary는 검색 상위여도 문맥에서 빠진다(사례: 호출부가 빈 경로를 건너뜀 `query.go:325-327` 1건).

#### 12. index·log 관리

`index.md`가 없다. 색인은 SQLite FTS5·벡터로 코드가 결정적으로 만들고, 어긋나면 reconcile이 고친다.

log는 코드가 남긴다. 컴파일마다 `wiki/CHANGELOG.md`(`pipeline.go:546-548`), 이벤트 JSONL·SSE·서명 webhook(`docs/guides/serve-mode.md:58-69`), lint 결과 `.sage/lintlog/`(`runner.go:179-214`), git auto-commit이다.

이벤트에는 문서 내용·원문 질의·경로가 없다: "Events never contain document content, raw query text (hashed), or filesystem paths"(`docs/webhooks.md:31`).

#### 13. 포맷 표준

OKF 대응이 없다. 레포 전체에서 "okf"·"open knowledge format" 문자열을 찾지 못했다(grep, 일치한 것은 `HookFor` 같은 식별자 조각뿐).
자체 형식은 YAML frontmatter + `[[wikilink]]`이고 Obsidian vault overlay(`init --vault`)를 지원한다(`internal/wiki/init.go:105-226`).

바깥으로 꺼내는 경로는 둘이다. 결정적 tar export(`internal/export/tar.go:1-3`, serve `GET /export` `internal/serve/server.go:226`)와 source↔article provenance 조회(CLI `provenance` `cmd/sage-wiki/main.go:158-163`, MCP `wiki_provenance`)다.

#### 14. 규모·비용

규모 주장은 있고 실측 근거는 문서 안 계산뿐이다: 문서당 약 8분, 10만 문서면 139일(`large-vault-performance.md:10-16`). 레포 안에 컴파일 토큰 측정 결과는 없지만, 아래 usage ledger로 직접 잴 수 있다.
비용 장치는 비교 문서의 9개 구현보다 많다.

| 장치 | 위치 |
|---|---|
| tier + 질의 기반 승격 + compile-on-demand | `tiers.go:79-111`, `ondemand.go:71-153` |
| compile key skip, summary 재사용 | `determinism.md:88-96`, `summarize.go:203-236` |
| batch API(`mode: auto`면 10개 이상), prompt cache, pass별 모델 | `pipeline.go:889-899`, `fullpipeline.go:152-160` |
| 상한: summary 4000(config 기본, 값이 0 이하면 2000)·article 4000·extract 8192 토큰, 원문 맥락 100k, 관련 concept 8, triple 40/60 | `internal/config/config.go:1113, 1265-1266`, `fullpipeline.go:161-164, 447-450`, `write.go:779`, `extract_triples.go:587-591` |
| usage ledger(호출마다 pass·provider·model·tier·입력/캐시/출력 토큰·비용·가격 출처) + `cost report`(모델·pass·tier별 합산)·`cost models` + 선택형 Prometheus `/metrics` | `internal/llm/usage.go:24-60`, `cmd/sage-wiki/cost_cmd.go:19-34`, `internal/web/server.go:171`, `docs/guides/metrics.md:1-4` |
| 실행 상한 `MaxCost`·`MaxDocs`·`max_compile_batch`·문서별 15분 | `pipeline.go:68-73, 407-424`, `limits.go:27` |
| 429면 동시성 반감, 연속 성공이면 두 배 | `backpressure.go:103-140` |

`MaxCost`는 비용을 모르면(nil) 멈추지 않는다(`fullpipeline.go:131-137`). 벤치마크(LOCOMO 92.0% 등, `eval/benchmarks/REPORT.md:14-18`)는 대화 기억 평가이고 작성자 결론은 "retrieval, not compilation, was the binding constraint"다(`REPORT.md:25-35`).

#### 15. frosk1 비판 대응

강도 표기는 비교 문서 #frosk1 비판 7가지 × 구현 대응 표를 따른다.

| 비판 | 강도 | 근거 |
|---|---|---|
| 1 오류 누적 | 부분 | Q&A 답 격리(결정 16), evidence 부분 문자열 검증(결정 20), evidence gate. 그러나 Pass 3가 기존 article을 입력으로 다시 쓰므로 article 안의 오류는 이어진다(`write.go:212-249`) |
| 2 부분 문맥 | 부분 | Pass 3 원문 예산 100k 토큰. 그러나 형식 없는 문서는 앞 4000바이트, Pass 2는 summary 앞 1000바이트, 묶음끼리는 서로 모른다(결정 4) |
| 3 요약 손실 | 부분 | raw는 그대로 남고 tier 0/1로 검색되며 Pass 3가 raw 절을 본다. 그러나 triple evidence는 summary 기준이고, 표 모양 문서의 항목별 정의가 서술형 요약에서 사라진다(#96 열림) |
| 4 가짜 SoT | 부분 | "files are the truth"의 파일은 wiki 산출물이다. Q&A는 article을 인용하고 raw까지 가지 않는다. GraphQA는 edge의 `source_doc`·evidence를 돌려준다(`graphqa.go:193-213`) |
| 5 환각 병합 | 부분(강한 편) | never-merge 가드, link-not-collapse + `--unlink`, 거절 전이 차단, curation drop 허가제. 그러나 같은 숫자 포함·동의어 매체 쌍은 cosine threshold에 남는다(결정 8) |
| 6 운영 복잡도 | 악화(코드), 강(설치) | 비테스트 83.7k줄·패키지 47개·SPEC 9개. 설치는 의존성 없는 바이너리 하나다 |
| 7 ingest 비용 | 이동 + 부분 | tier·on-demand가 비용을 질의 시점으로 옮기고 compile key가 재과금을 막는다. 측정값은 없다 |

#### 16. 성숙도·차용 가능성

MIT라 코드째 가져올 수 있다(예외는 #한눈에의 라이선스 행). 테스트 437개 파일, CI 10개 workflow, record/replay parity suite가 있다(`docs/guides/parity-suite.md:3-10`).

| 떼어 쓰기 좋은 단위 | 크기 | 끌고 오는 것 |
|---|---|---|
| `internal/compiler/dedup.go`의 `neverMergeNames` | 287줄 파일 중 일부 | 없음(문자열 규칙) |
| `internal/compiler/evidence_gate.go` | 60줄 | manifest 타입 |
| `internal/compiler/curate.go` + `curate_concepts.txt` | 307줄 | `internal/llm` structured output |
| `internal/compiler/resolve_entities.go` 블로킹·canonical·`canAutoApply` | 1,649줄 | store·ontology 인터페이스 |
| `internal/ontology/aliases.go` + `derived_relations` 스키마 | 467줄 | storage 마이그레이션 V11·V12 |
| `internal/compiler/compilekey.go` | 678줄 | config·prompts 해시 |
| `internal/search/pipeline.go` `fuseLegs`·blend | 512줄 | memory·vectors store |
| `internal/trust/` | 약 1,500줄(10개 파일) | embed, llm, store |

줄 수는 `wc -l`로 쟀다.

문서와 코드가 어긋난 곳이 많다. 없는 기능을 있다고 적은 곳이 여섯이다.

| 문서 | 코드 | 출처 |
|---|---|---|
| frontmatter `tier:`가 최우선 | 호출부가 nil을 넘겨 동작하지 않는다 | `large-vault-performance.md:102-111`, `pipeline.go:1283` |
| 승격 신호 cluster_size·manual_tag·import_centrality 등 | 검색 적중 수와 90일 정체만 쓴다 | `large-vault-performance.md:117-131`, compile 노트 #3 |
| 품질 점수 "Source coverage (40%) …" 3차원 | 5차원 0.15/0.30/0.20/0.15/0.20 | `large-vault-performance.md:262-266`, `confidence.go:31-39` |
| web UI가 MCP를 `/sse`로 연다 | `web.Handler`에 `/sse` 라우트가 없다 | `serve-mode.md:51-56`, `internal/web/server.go:139-182` |
| `wiki_learn`의 "self-learning loop", 팀 convention이 검색에 나온다 | `learnings` 표를 읽는 운영 코드가 없고 FTS 트리거도 없다. `write_article.txt`의 `{{.Learnings}}`를 채우는 코드가 없다 | `team-setup.md:423-424`, `internal/linter/learning.go`, surfaces 노트 #wiki_learn |
| CLI `capture`가 "extracts knowledge items" | LLM 없이 원문을 저장한다 | `team-setup.md:461-462`, `pkg/engine/methods.go:89-145` |

[추정] 코드 읽기로 찾은 결함 후보가 더 있다(사례: 아래 4건, 모두 미실행).

| 후보 | 위치 |
|---|---|
| 임베딩 dedup 캐시 seed가 id=concept 이름을 찾지만 벡터는 `concept:<name>`으로 저장돼 매번 빗나간다 | `dedup.go:73`, `write.go:414` |
| Pass 3와 품질 점수가 PDF·DOCX 원문을 `os.ReadFile`로 그대로 읽는다 | `write.go:1093-1098`, `fullpipeline.go:537-541` |
| 같은 실행에서 먼저 저장되는 article이 나중 concept을 가리키면 키워드 edge가 FK 위반으로 조용히 사라진다 | `write.go:172-184, 898-903`, `db.go:307-308` |
| 승격 답 색인에 embedder가 전달되지 않아 vector가 생기지 않는다 | `query.go:701-705`, `trust/promote.go:72, 107` |

## 엔터프라이즈 llm-wiki에 비추어

사용자 조건은 "작성자마다 같은 대상을 다른 용어로 쓴다"와 "문서가 형식을 갖추지 않을 때가 있다"이다. 목표 원문은 "어느정도 사람이 하더라도 성능을 보장(raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조)"이다.

참고할 점이 하나 있다. 설계를 움직인 실사용 이슈 #128·#144·#146·#164·#166·#167이 141개 문서짜리 정부 토양 정화 사건 파일에서 나왔고(compile 노트 #7), #90·#92·#106도 비ML 환경·규제 문서 말뭉치에서 나왔다(sage-why 노트 #3). 사내 보고서와 성격이 가깝다.

| 조건 | 이 레포가 주는 답 | 빈 곳 |
|---|---|---|
| 다중 작성자 | 팀 가이드는 두 방식을 함께 싣는다: 각자 컴파일해 git으로 push하는 Pattern A(`team-setup.md:76-81`)와, DB 충돌 해결책으로 든 "Designate one compiler"(`team-setup.md:727-738`). `extends:`로 부서 workspace들이 기본 config 하나를 한 단계 상속한다(`internal/config/config.go:1214-1253`). Idempotency-Key가 재시도 중복을 막는다. `verified` 모드의 답 격리는 한 사람의 오답이 전사 맥락을 오염시키는 것을 막는다: "Prevents one person's wrong query from poisoning everyone's context"(`team-setup.md:281-283`) | 누가 썼는지가 어디에도 없다. `manifest.Source`·edge·이벤트·alias 결정에 작성자·결정자 필드가 없다(`manifest.go:65-76`, surfaces 노트 #누가 썼는지). Pattern A에서 raw를 누가 넣었는지는 git 이력에만 남고, 컴파일러 auto-commit은 `git commit -m`만 불러 작성자를 따로 넣지 않는다(`internal/git/git.go:58`). 작성자별 신뢰도·우선순위를 표현할 자리가 없다 |
| 용어 불일치 | 사후 장치가 두텁다: 별칭 겹침 접기 + manifest 별칭 영속(결정 10), 이름 임베딩 dedup + never-merge(결정 8), 전역 curation(결정 9), resolution link-not-collapse(결정 11). 별칭이 FTS tags에 들어가 별칭으로 검색해도 정식 article이 걸린다(`write.go:390`, `entries.go:159`). pack이 부서 workspace마다 같은 어휘·동의어·프롬프트를 깔 수 있다(결정 23) | 사람이 쓰는 정식 이름 + 별칭 용어집 입구가 없다. concept 프롬프트는 기존 이름만, triple 프롬프트는 목록조차 받지 않는다(`concepts.go:123-124`, `extract_triples.txt:14-15`). [추정] `prompts/extract-concepts.md`를 덮어써 사내 정식 이름 목록을 넣는 우회는 된다(사례: 프롬프트 9개 전부 덮어쓰기 가능 1건, `customizing-prompts.md:1-40`). 묶음끼리 서로 모르고 첫 컴파일엔 목록이 비어 앞단 앵커가 약하다(결정 4). never-merge 반의어는 영어뿐이다. `language` 설정은 JSON 템플릿인 concept 추출에 언어 지시를 붙이지 않아 concept 이름의 언어를 고정하지 않는다(`internal/prompts/prompts.go:146-175`) |
| 형식 없는 문서 | raw가 tier 0/1로 바로 FTS·청크 vector 검색된다(`index.go:273-298`). 원문 맥락 예산이 고빈도 사내 용어의 문맥 폭발을 막는다(#146). `internal/extract`가 Office·PDF·메일·이미지(vision)를 텍스트로 바꾸고 목록 밖 형식은 sandbox 안 외부 파서로 넘긴다(`extract.go:51-84`, `external.go:110-118`). `type_signals` + `summarize-{type}.md`로 "주간보고"·"회의록"처럼 형식이 제각각인 문서를 종류별 요약 틀에 보낼 수 있다(`summarize.go:263-267`, `config.go:830-838`) | heading 없거나 15000자 미만 문서는 Pass 3가 앞 4000바이트(한국어 약 1300자)만 본다(`write.go:1100-1112`). 표 모양 문서 전용 요약은 #96으로 열려 있다. raw frontmatter는 Pass 1 summarize에서 떼어져 summary와 그 뒤 concept 추출에 닿지 않는다(`internal/extract/extract.go:193-221`). Pass 3는 raw 앞부분을 그대로 넣어 frontmatter가 article 프롬프트에 들어가지만 필드가 아니라 본문 텍스트로 들어간다(`write.go:1092-1111`). `ingest`의 encoding gate가 UTF-8이 아닌 텍스트와 .hwp·.doc 같은 미지원 binary를 거부한다(`ingest.go:42-79`). [추정] 그래서 한글 문서는 `raw/`에 직접 두고 외부 파서를 붙여야 들어온다(사례: `EncodingGate` 호출부가 ingest·capture뿐이고 컴파일 diff에는 없음 1건, `grep -rn EncodingGate(`, 미실행). DOCX·PDF 작성일을 읽지 않아 frontmatter 없는 보고서는 파일 mtime이 날짜가 된다(`sourcedate.go:30-47`). [추정] 복사·내려받기로 mtime이 바뀌면 원문 날짜가 아니라 복사한 시각이 남는다(사례: mtime fallback 1건, 미실행) |
| 권한 | 비-loopback에서 토큰 없이는 시작을 거부한다(`internal/serve/auth.go:52-68`). 검색 결과에 거름망을 꽂을 `IncludeDoc` 술어 seam과 over-fetch가 있다(`search/run.go:87-91, 141-148, 299-307`) | 다중 사용자 권한은 의도된 비목표다(결정 18). 토큰 하나가 전권이다: "Anyone with the token can do anything"(`docs/security.md:120-122`). `IncludeDoc`는 `search.Run` 결과에만 걸린다. Q&A 그래프 확장은 article 파일을 직접 읽고 trust 검사만 거치며(`internal/query/query.go:286-293, 345-358`), GraphQA·community 요약·hub 검색도 각자 경로다. article 하나가 여러 원문을 합쳐 쓰이므로(`write.go:226-236`) 권한이 다른 원문을 한 concept에 섞지 않는 규칙이 컴파일 쪽에 따로 필요하다. 부서별로 workspace를 나누면 workspace 사이 연결은 hub 검색뿐이고 entity는 잇지 않는다(`internal/hub/search.go:29-87`). URL ingest는 사설 주소를 거부해 인트라넷 문서를 URL로 넣을 수 없다(`ingest.go:292-320`) |
| 데이터 반출 | 원문·summary가 pass마다 설정된 provider로 나간다. pass별 모델 라우팅으로 원문이 닿는 summarize·extract를 Ollama 같은 로컬 모델로 돌릴 수 있다(`docs/guides/local-models.md:1-15`) | 팀원 각자의 ChatGPT Pro·Claude Max 구독 토큰을 쓰는 subscription auth는 `~/.sage-wiki/auth.json`에 저장한다(`team-setup.md:288-309`). 회사 정책과 맞는지 따로 봐야 한다 |
| 규모 | tier·on-demand·compile key·batch API·실행 상한·usage ledger(#축별 분석의 14번). 10만 문서급을 상정해 설계했다(`large-vault-performance.md`) | 쓰기 프로세스가 하나라 동시 컴파일이 줄을 선다. 서버 모드에서는 서버 자격 하나로 모든 팀원의 LLM 비용이 나가고, usage ledger 행에도 요청자 필드가 없다(`internal/auth/resolve.go:13-45`, `internal/llm/usage.go:24-49`). consensus의 질문 vector 비교는 전수다(`trust/consensus.go:26-75`) |
| raw 연결 | concept → source `cites`, triple `source_doc`, 공유 source 기반 "See also"와 Q&A 확장의 source overlap 신호(가중 4.0, `relevance.go:22-25, 166-199`) | 연결 단위가 문서다. raw 청크는 entity와 이어지지 않고 원문 위치(offset)도 없다(#축별 분석의 5번) |
| 새·기존 연결 발견 | 새 concept이 기존 이름 스냅샷·별칭·임베딩 dedup·resolution으로 기존 것에 붙는다. connections lint가 vector는 비슷한데 edge가 없는 쌍을 보인다(`passes.go:224-292`). 비슷한 질문에 다른 답이면 conflict가 된다 | connections lint는 info 메시지일 뿐 검토 큐나 자동 연결로 이어지지 않는다(`CanAutoFix()` false). 버려진 술어를 새 관계 후보로 올리는 대기열이 없다 |

### 가져올 것

| 아이디어 | 맞는 이유 | 코드 위치 |
|---|---|---|
| 결정적 never-merge 가드를 유사도 판단 **아래**에 깔기 | 사내 보고서의 번호 붙은 대상(과제 3차/4차, 2023/2024 회계연도, 초안/최종)은 임베딩으로 못 가른다는 측정이 있다(#164). 한국어 반의어·차수 규칙으로 다시 써야 한다 | `internal/compiler/dedup.go:169-239` |
| link-not-collapse + derived edge 별도 표 + `--unlink` + 거절 전이 차단 | 사람이 일부만 검토해도 실수를 명령 하나로 되돌린다. "되돌리기 비용이 자동화 기본값을 정한다"는 규칙 자체를 가져온다 | `internal/ontology/aliases.go:252-270`, `resolve_entities.go:1285-1334`, `internal/storage/db.go:619-699` |
| canonical과 자동 적용 조건을 코드가 정하기(LLM은 판정만) | 용어 정규화의 최종 결정권을 재현 가능한 규칙에 둔다. 설명문 요구가 이름만 닮은 병합을 막는다 | `resolve_entities.go:240-345` |
| 전역 curation 한 패스(fold 자동, drop 허가제) | 작성자마다 다른 용어로 concept이 불어나는 것을 비싼 article 쓰기 직전에 줄인다. 승인 대기열은 직접 덧붙여야 한다 | `internal/compiler/curate.go`, `internal/prompts/templates/curate_concepts.txt` |
| evidence gate를 LLM 호출 **전에** | 한 보고서에만 나온 약어·서명자 이름이 concept이 되는 것과 비용을 함께 막는다. 다중 작성자에서는 "source 2개 이상"처럼 올려 쓸 수 있다 | `internal/compiler/evidence_gate.go:13-28` |
| schema enum 없이 Go에서 어휘 강제 | 모델 실수 하나가 문서 그래프 전체를 날리지 않고 노드·edge 하나만 잃는다 | `internal/compiler/extract_triples.go:54-63, 175-314` |
| evidence 부분 문자열 검증 | 지어낸 근거를 코드로 버린다. summary 대신 raw 청크를 대상으로 바꾸면 원문 근거 추적이 된다 | `extract_triples.go:905-952` |
| frontmatter는 코드, 본문만 LLM | concept·aliases·sources·created_at(컴파일 시각)은 코드가 manifest에서 만들어 LLM이 바꾸지 못한다. 작성자·원문 날짜 필드는 sage-wiki에 없으니 같은 방식으로 우리가 더해야 한다. confidence와 사용자 정의 필드는 LLM 출력에서 긁는다. MCP `wiki_write_article`은 이 규칙을 거치지 않으므로 모든 쓰기 경로에서 frontmatter를 코드가 다시 만들어야 한다(결정 13) | `internal/compiler/write.go:465-500`, `internal/mcp/tools_write.go:272` |
| Q&A 답 격리 + 모든 검색 표면에 같은 trust 술어 + 인용 파일 hash 강등 | 사내 Q&A 답이 다음 답의 출처가 되는 오염을 막는다. `include_outputs: verified` 모드를 전제로, 보고서가 고쳐지면 그것을 근거로 한 confirmed 답을 자동 강등한다 | `internal/trust/`, `internal/search/run.go:299-307`, `internal/compiler/pipeline.go:561-573` |
| compile key + `--explain` | 여러 사람이 프롬프트·config를 만질 때 무엇이 왜 다시 도는지 운영자가 설명하고 비용을 예측한다 | `internal/compiler/compilekey.go`, `docs/determinism.md` |
| tier + 질의 기반 승격(아이디어만) | 전체 보고서는 싸게 색인만 하고 사람들이 실제로 묻는 주제부터 깊게 컴파일한다. 다만 이 레포에서는 적중을 MCP·`/v1` `wiki_search`에서만 세고 web UI 검색과 Q&A는 세지 않으며, [추정] `src:` 접두어 불일치로 tier 0/1 문서에는 적중이 쌓이지 않는다(결정 15, 미실행). 사람 질의를 신호로 쓰려면 모든 표면에서 원문 경로로 세야 한다 | `internal/compiler/tiers.go:79-111`, `internal/mcp/server.go:417-429` |
| 3채널 RRF + 채널별 순위 노출, pending alias는 순위에서 제외 | 용어가 달라 BM25가 놓친 문서를 vector·graph가 잡고, 어느 채널이 찾았는지 진단할 수 있다 | `internal/search/pipeline.go:98-262`, `graphleg.go:126-128` |
| `IncludeDoc` 술어 seam + over-fetch | 검색 결과에 문서 단위 권한 필터를 꽂을 자리다. 그러나 그래프 확장·GraphQA·community 요약은 이 술어를 거치지 않고, article이 여러 원문을 합쳐 쓰이므로 권한 경계를 넘는 원문을 한 concept에 섞지 않는 규칙이 컴파일 쪽에 따로 필요하다 | `internal/search/run.go:87-91, 141-148`, `internal/query/query.go:345-358` |
| REST 표면(`/v1`, serve)을 tool 레지스트리 하나로 | 에이전트와 외부 연동이 같은 handler를 거친다. 이 레포는 web UI·CLI를 따로 두었으니, 우리 구현에서는 사람 UI도 같은 레지스트리로 보내야 한다 | `internal/api/dispatch.go:37-79` |
| `type_signals` + 타입별 summarize 프롬프트 | 형식이 제각각인 사내 문서를 종류별로 다른 요약 틀에 보낸다. 신호와 프롬프트가 compile key에 들어가 바꾸면 영향받는 문서만 다시 돈다 | `summarize.go:263-267`, `internal/config/config.go:830-838`, `compilekey.go:360` |
| pack(어휘·동의어·프롬프트·article_fields 묶음, fill-only 설치) | 부서 workspace마다 같은 사내 용어 체계를 깐다. [추정] 내장 pack의 `extract_*` 프롬프트는 컴파일이 부르지 않으니 템플릿 이름 규약을 확인해야 한다(결정 23) | `internal/pack/manifest.go:22-44`, `merge.go:197-216` |

### 피할 것

| 피할 것 | 이유 | 위치 |
|---|---|---|
| summary를 바이트 단위로 앞 1000바이트만 concept 추출에 넣기 | 한국어는 약 330자이고 글자 중간이 끊긴다. 새·기존 연결 발견의 입구가 좁아진다 | `concepts.go:182-184` |
| heading 없는 문서는 앞 4000바이트만 article 맥락에 넣기 | 형식 없는 사내 문서에서 뒤쪽 내용이 article에 반영되지 않는다 | `write.go:1100-1112` |
| 이름 임베딩 cosine 하나로 자동 병합 | 작성자 스스로 "no threshold can work"를 인정했다(#164) | `dedup.go:125-167` |
| triple evidence를 summary에서만 인용 | 감사 때 원문에서 근거를 찾지 못한다. 작성자도 "proposition-level"이 빈 곳이라고 했다 | `internal/store/domain.go:105-109` |
| 결정 주체를 `user` 문자열로만 남기기 | 다중 작성자 환경에서 누가 alias·승격을 결정했는지 재구성할 수 없다 | `internal/store/domain.go:160` |
| 에이전트 직접 쓰기 tool이 컴파일 gate를 건너뛰게 두기 | 용어 불일치가 정규화 없이 그래프에 바로 들어간다. 이 레포에는 이런 경로가 다섯이다(#축별 분석의 2번) | `internal/mcp/tools_write.go:184-364`, `internal/scribe/session.go:106-125` |
| 문서에 적힌 기능을 코드 확인 없이 믿기 | frontmatter tier, 승격 신호, learnings, `/sse` 등 여섯 곳이 코드와 다르다(#축별 분석의 16번) | 위 표 |
| concept 이름을 파일명이자 id로 쓰기 | 한국어 slug와 영어 slug가 섞이면 같은 대상이 두 문서가 된다. `language` 설정은 summary·article에만 언어 지시를 붙이고 JSON 템플릿인 concept 추출에는 붙이지 않으므로 concept 이름의 언어는 모델이 정한다. 답 파일 slug는 한글을 버린다 | `write.go:216`, `internal/prompts/prompts.go:146-175`, `query.go:1047-1062` |
| 식별자·slug를 ASCII로 제한 | MCP `wiki_capture`는 제목이 한글로만 된 항목이 하나라도 있으면 capture 전체를 거부하고, `wiki_write_article`은 한글 concept id를 받지 않는다. URL ingest slug도 영숫자만 남긴다 | `internal/mcp/tools_write.go:253-257, 480-486, 650-669`, `internal/pathsafe/pathsafe.go:128`, `internal/wiki/ingest.go:337-356` |
| MCP capture가 원문을 버리고 LLM 재서술만 남기기 | 대화·보고서 원문 근거가 끊긴다 | `tools_write.go:510-535` |

## 확인하지 못한 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| 비공개 결정 기록의 원문(SPEC-01~09, ADR-036~039, `decision-035`). 예: per-workspace 권한을 비목표로 둔 이유, 검색 기본 가중 0.7/0.3/0.2라는 숫자(75/60/40은 qmd 유래, 결정 17), connections 0.7, learnings 500개·180일의 근거 | 레포에 없다(`.gitignore`). 작성자에게 묻거나 `xoai` 계정의 다른 공개 레포를 찾는다. P2-1~P2-7은 `git show 3e803d5:.sage/docs/design/<name>.md`로 더 읽을 수 있다 |
| concept 프롬프트에 별칭을 넣지 않는 이유, concept type을 셋으로 고정한 이유 | `git log -p -- internal/prompts/templates/extract_concepts.txt`, 관련 PR |
| summary 1000바이트 자르기가 Concepts 절을 실제로 잘라 먹는 비율 | 한국어 문서 몇 개를 컴파일해 `wiki/summaries/*.md` 길이와 Pass 2 프롬프트 비교(실행 필요) |
| Pass 3·Q&A가 PDF·DOCX를 바이너리로 받는지 | PDF 소스 하나로 컴파일하고 `write_article` 요청 본문 기록 |
| 강화 Q&A 경로에서 summary가 빠지는 것이 의도인지, 승격 답에 vector가 없는 것이 의도인지 | 작성자 확인, `verified` 모드에서 승격 후 `vec_entries`의 `output:` 행 조회 |
| Postgres 백엔드에서 `sage-wiki query`가 도는지(SQLite 전용 store를 새로 만든다, `query.go:213-220`) | `TEST_DATABASE_URL`로 `internal/query` 테스트 실행 |
| capture slug 덮어쓰기, 키워드 edge FK 손실, dedup seed 빗나감, tier 0/1 문서의 질의 적중 누락이 실제로 일어나는지 | 각 경로를 stub LLM으로 돌리는 테스트. 적중은 `wiki_search` 뒤 `compile_items.query_hit_count` 조회 |
| batch 재개·re-extract 경로가 임베딩 dedup·triple을 빼는 것이 의도인지 | batch 관련 spec이나 이슈. `resumeBatch` 주석(`pipeline.go:1441-1443`)은 store 구성만 설명한다 |
| graph 채널·resolution·curation이 재현율·중복을 실제로 얼마나 바꾸는지 | `eval/benchmarks/retrieval_ab.py`를 채널 on/off로 돌린 결과. 레포에 ablation 결과 파일이 없다 |
| 한국어 질의의 BM25·graph 재현율 | 한국어 코퍼스로 `--channels bm25`, `--channels graph` ablation. 토큰화는 `porter unicode61`이라 조사를 떼지 않는다(`db.go:280-283`) |
| 팀 규모 운영 사례 | 이슈·토론에 팀 운영 보고가 없다. 사용자 사례 검색 필요 |
| #144 인용 검증과 #96 표 문서 요약의 결론 | 이후 릴리스 노트와 이슈 |

## 검증 기록

검증자 셋이 이 보고서를 서로 다른 관점으로 대조했고, 지적 56건을 반영 전에 레포(`d3ef3a1`)·`gh`·X 글 JSON으로 하나씩 다시 열어 확인했다.

| 관점 | 대조한 주장 수 | 지적 | 대조 방법 |
|---|---|---|---|
| 코드 주장 | 104 | 21 | 인용한 `path:line`을 `sed -n`·`wc -l`·`grep`으로 열었다 |
| "왜" 주장 | 118 | 19 | commit 본문(`git show -s`), 이슈·PR(`gh issue view`, `gh api …/pulls/53/reviews`), X 글 원문(`api.fxtwitter.com` JSON)과 맞췄다 |
| 빠진 하위 체계 | 34 | 16 | 디렉터리별로 코드를 읽어 보고서에 없는 장치를 찾았다 |

### 크게 바뀐 것

| 전 | 후 | 근거 |
|---|---|---|
| 표면 일곱 갈래가 MCP tool 레지스트리 하나로 모인다(큰 구조, 결정 19, 가져올 것) | `/v1`·serve REST만 레지스트리로 가고 web UI `/api/*`·CLI·TUI·`pkg/engine`은 엔진을 직접 부른다. 결정 19 제목도 "REST 표면을 MCP tool 레지스트리로 몬다"로 줄였다 | `internal/web/server.go:144-154, 716, 951`, `grep -rln CallTool` |
| 패스 순서 dedup 또는 curation → evidence gate | 임베딩 dedup → evidence gate → curation. ingest 표의 단계 번호를 8, 9a, 9b로 바꿨다 | `fullpipeline.go:317-367`, `curate.go:255-257` |
| 미완료 실행은 아무것도 저장하지 않는다(ingest 15, 결정 14, 축 4) | manifest·compile key·pass 표시만 남기지 않는다. summary·article 파일과 색인 행, CHANGELOG, git auto-commit은 남거나 돈다 | `pipeline.go:500-504, 540-549, 575-580`, `write.go:170-171` |
| 인용 파일 hash가 바뀌면 답을 강등한다(유지보수 3, 축 8, 가져올 것) | `include_outputs: verified`일 때만 강등한다. 기본 `"false"`에서는 검사가 돌지 않는다 | `pipeline.go:561-573`, `config.go:1059-1063` |
| 승격된 답은 검색에 들어간다(결정 16, 축 11) | 기본 `"false"`에서는 승격돼도 검색에 나오지 않고, `verified`일 때만 들어간다 | `internal/trust/predicate.go:15-42` |
| raw frontmatter가 LLM에 닿지 않는다(엔터프라이즈 형식 없는 문서) | Pass 1에서만 떼고, Pass 3는 raw 앞부분을 frontmatter째 넣는다 | `write.go:1092-1111` |
| frontmatter는 코드가 써서 작성자·날짜를 LLM이 못 바꾼다(결정 13, 가져올 것) | 작성자 필드는 없고 `created_at`은 컴파일 시각이다. MCP `wiki_write_article`은 에이전트 frontmatter를 그대로 쓴다 | `write.go:465-500`, `tools_write.go:272, 296` |
| 검색 적중 3회면 tier 승격(결정 15, 가져올 것) | 적중은 MCP·`/v1` 검색에서만 센다. [추정] `src:` 접두어 불일치로 tier 0/1 문서에는 쌓이지 않는다. 가져올 것은 "아이디어만"으로 낮췄다 | `mcp/server.go:417-429`, `index.go:60-61`, `items.go:214-229` |
| summary 상한 2000토큰(축 14) | config 기본 4000, 값이 0 이하일 때만 2000 | `config.go:1113, 1265-1266` |
| PR #53을 받아 `3841287`에서 원문 절을 넣었다(결정 3) | 작성자는 `3841287` Phase B에서 따로 넣었고, raw 전체를 넣자는 PR #53은 토큰 효율을 이유로 "superseded"로 닫았다 | PR #53 리뷰(2026-04-15T02:42Z), `git show -s 3841287` |
| P3-2가 schema에서 enum을 뺐다(결정 6) | enum은 처음부터 없었다. 08-22 CurateSchema가 처음이다. 이유는 [추정]이 아니라 작성자 원문으로 올렸다 | `git log -S'"enum"'`, `b485bcf`, `a0f743e` |
| 이전 설계는 Python CLI + 외부 벡터 DB(결정 1) | Go CLI + Python memory server + API gateway 세 프로세스. 외부 벡터 DB는 처음부터 피했다 | X 글 원문 |

### 그 밖에 고친 것

출처 줄 번호가 파일 밖이거나 다른 내용을 가리킨 곳 열 군데를 고쳤다: `internal/store/types.go:114-145`, `internal/trust/predicate.go:15-42`, `consensus.go:140-145`, `hooks.go:165-243·183-189·199-219`, `rerank.go:38, 189-242, 295-305`, `docs/webhooks.md:31`, `configurable-relations.md:7-11`, `parity-suite.md:3-10`, `graph-memory.md:39-40`, `relevance.go:22-25`.

P2-1 설계 문서 인용은 HEAD에 없어서 `git show aa37245:docs/design/p2-1-storage-abstraction.md`로 출처를 바꿨다.

"왜" 쪽에서는 인용의 말한 사람과 맥락을 바로잡았다. #164·#167의 측정과 진단은 보고자 ivanhyphae의 말이라고 밝히고 작성자가 받아들인 원문을 붙였다. `README.md:61-62`의 "empty ontology" 문장은 검색 graph 채널 설명이라 결정 7에서 결정 17로 옮겼다.

결정 7의 "묶인 약속"은 `ab36031`·`4c0a708` 원문이 있어 [추정]을 뗐다. "결정적 바닥"도 작성자 표현(`curate.go:28`)이라 원문으로 올렸다.

결정 14의 이력은 P1-1 `1c317d3`(07-19)과 SPEC-04(08-02~08-05)로 나눴다. 결정 17의 75/60/40은 qmd 유래(`c1f1a3d`)라 모르는 것에서 뺐다. 결정 18 인용을 원문 "pre-existing, lock-free"로 고쳤다. X 글은 원문 전체를 받아 대조했으므로 "요약 모델을 거쳐 읽었다"는 단서와 #확인하지 못한 것의 X 글 행을 지웠다.

빠진 하위 체계는 레포를 직접 읽고 해당 절에 채웠다.

| 채운 것 | 자리 |
|---|---|
| 컴파일 gate를 건너뛰는 쓰기 경로 다섯(`wiki_write_summary`, CLI `write`·`ontology add`, `scribe` 추가) | 축 2 표 |
| `internal/extract` 형식 변환, ingest encoding gate, `prompts/` 덮어쓰기, `type_signals` | 축 4, 가져올 것 |
| pack | 결정 23 신설, 가져올 것 |
| `language` 설정이 concept 추출에 닿지 않는 점, ASCII slug 제한 | 엔터프라이즈 용어 불일치, 피할 것 |
| 원문 날짜 사슬 `internal/sourcedate` | 축 8, 엔터프라이즈 형식 없는 문서 |
| 사람이 고친 article이 다음 컴파일에 덮어써지는 점 | 축 9 |
| `IncludeDoc`가 닿지 않는 경로와 원문 혼합 | 엔터프라이즈 권한, 가져올 것 |
| 라이선스 예외(Apache-2.0, CC0) | 한눈에 |
| URL ingest SSRF 제약 | ingest 단계 0 |
| usage ledger·`cost report`·`/metrics` | 축 14 |
| pass별 로컬 모델과 subscription auth | 엔터프라이즈 데이터 반출(새 행) |
| 팀 가이드 Pattern A와 `extends:` | 엔터프라이즈 다중 작성자 |
| export·provenance·`clients/`·mirror hydrate | 큰 구조, 축 13 |

결정이 23개가 되어 #왜 이 구조인가 머리의 개수도 고쳤다.

### 반영하지 않은 것

지적 자체를 기각한 것은 없다. 지적 안의 세부 주장 넷은 확인되지 않아 빼고 반영했다.

| 세부 주장 | 반영하지 않은 이유 |
|---|---|
| MCP `wiki_write_summary`가 manifest에 compiled 표시를 남겨 "Pass 1을 대신한다" | `tools_write.go:235`의 `MarkCompiled`는 확인했다. 그러나 새 소스는 hash `""`로 등록돼(`:233`) 다음 diff가 다시 잡을 수 있어서, Pass 1을 건너뛰는지는 코드 읽기만으로 정할 수 없다. "compiled 표시를 남긴다"까지만 적었다 |
| `internal/mirror` 비테스트 4,828줄 | 같은 명령으로 다시 재면 4,551줄이다. 숫자는 본문에 넣지 않았다 |
| `internal/pack` 비테스트 3,678줄 | Go 비테스트 파일만 재면 2,554줄이다. 검증자는 yaml·md까지 센 것으로 보인다. 숫자는 본문에 넣지 않았다 |
| 75/60/40의 출처로 `tobi/qmd` README 553-558행 | 레포 문서가 링크한 qmd는 `dmayboroda/qmd`라(`search-quality.md:345`) 저장소가 다를 수 있다. commit `c1f1a3d`와 `search-quality.md:59`만 출처로 적었다 |

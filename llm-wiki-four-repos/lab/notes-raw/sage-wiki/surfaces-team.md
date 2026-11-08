# sage-wiki — 쓰는 면과 팀 운영 (surfaces-team 갈래 노트)

기준은 xoai/sage-wiki HEAD `d3ef3a1`(2026-10-03), MIT다. 경로는 모두 레포 루트 기준이다. 코드는 실행하지 않았고 읽기 전용 git·grep·sed·cat과 `gh`만 썼다. 그래서 아래 "확인"은 모두 코드를 읽어서 본 것이다. 실행 결과로 본 것은 없다.

## 요약

sage-wiki의 "팀"은 사람마다 신원을 가진 다중 사용자 시스템이 아니다. 신뢰하는 운영자 한 명과 쓰기 프로세스 하나를 전제로 하고, 그 위에 여러 사람·에이전트가 공유 토큰으로 붙는 구조다. 근거는 셋이다.

- 보안 계약 문서가 "single-operator"와 "No multi-user authz"를 명시한다(`docs/security.md:9-14, 120-122`).
- 다중 workspace 서버도 per-workspace 인증을 "non-goal"로 둔다(`internal/serve/multi.go:125-127`).
- 쓰기 경로(이벤트, alias 결정, capture frontmatter, learnings, git commit) 어디에도 "누가"를 담는 필드가 없다(아래 #누가 썼는지).

대신 쓰는 면은 매우 넓고 단단하다. 같은 19개 MCP tool을 stdio·streamable HTTP(`/mcp`)·REST(`/v1`)·web UI·TUI·CLI가 공유한다. `/v1`과 `serve`의 REST는 tool을 다시 구현하지 않고 `(*mcp.Server).CallTool`로 보낸다.

운영 장치(workspace 잠금, 영속 job ledger, idempotency, 서명 webhook, S3 mirror·PITR, 자원 한도, parity suite)는 2026-07~08월에 SPEC-01~09로 한꺼번에 들어왔다.

엔터프라이즈 다중 작성자 용도에서는 "사람·권한·출처" 층을 직접 만들어야 한다. 차용할 만한 것은 "모든 면을 한 tool 레지스트리로 몰기", "쓰기 프로세스 하나 + 잠금", "LLM 산출물 격리(under_review)", "commit pointer를 마지막에 쓰는 백업"이다.

## 읽은 범위

| 범위 | 깊이 |
|---|---|
| `cmd/sage-wiki/main.go`(init, compile, serve 3종, scribe), `mirror_hook.go`, `capture.go`, `learn.go`, `ontology_resolve.go` 앞부분 | 끝까지 |
| `internal/mcp/{server,tools_write,tools_compound}.go` | 끝까지 |
| `internal/serve/{server,auth,deps,multi,hardened,connlimit,semaphore}.go`, `jobs.go` 앞 200줄 | 끝까지 |
| `internal/serve/{stack,mirror,webhooks,jobs 뒷부분,ratelimit}.go` | 주석·함수 머리만 훑음 |
| `internal/api/{router,dispatch}.go` 전부, `{idempotency,jobs,handlers_write}.go` 주석·검증 부분 | 핵심 경로 |
| `internal/web/server.go` 라우트·보안 미들웨어·`handleQuery`, `web/src/lib/{token,api}.ts` | 핵심 경로. 컴포넌트 tsx는 훑음 |
| `internal/mirror/{types,state,layout,mirror,servelock_unix,shipmutex,changes}.go` 머리 | 자료구조·주석만. `shipper.go`, `hydrate.go`, `verify.go`, `s3/`는 훑지 않음 |
| `internal/auth/{auth,resolve}.go` 전부, `store.go`·`backend.go` 함수 머리 | 핵심 경로. `oauth.go`, `import.go`, `refresh.go`는 훑지 않음 |
| `internal/hub/*`, `internal/git/git.go`, `internal/skill/*`, `internal/limits/limits.go` 앞부분 | 끝까지 |
| `internal/metrics`, `internal/tui`, `internal/cli`, `internal/parity` | 함수 머리만 훑음 |
| `pkg/engine/{lock,doc}.go`, `methods.go` Capture, `pkg/events/payloads.go` | 경계 확인용 |
| `docs/guides/{team-setup,self-hosted-server,remote-mirror,serve-mode,http-api,subscription-auth,parity-suite}.md`, `docs/{security,webhooks}.md` | 끝까지(subscription-auth는 뒷부분 훑음) |
| `eval/README.md`, `eval/REPORT.md`, `eval/benchmarks/{README,REPORT}.md`, `eval/eval.py` 점수 부분 | 핵심 부분 |
| `ci/*.yaml`, `tests/pathological/generator.go`, `clients/`, `skills/` | 훑음 |
| git log(이 범위 전체), 커밋 본문 18개, 이슈 #54 #74 #102 #112 #125, PR #31 #46 | 읽음 |

## 표면 지도

같은 workspace(디렉토리 하나)에 붙는 길이 일곱 갈래다. "잠금"은 `.sage/engine.lock` 배타 flock이다(`pkg/engine/lock.go:1-60`).

| 표면 | 진입 | 인증 | workspace 잠금 | 쓰기 |
|---|---|---|---|---|
| CLI (`compile`, `capture`, `query`, `ingest`) | `cmd/sage-wiki/main.go` → `pkg/engine.Open` | 없음(로컬 프로세스) | 잡음. 잡혀 있으면 "workspace is locked" | 예 |
| CLI (`learn`, `ontology add/resolve`, `write`, `add-source`, `hub`) | 각 `cmd/sage-wiki/*.go` → `storedial` 직접 | 없음 | 안 잡음(`learn.go:35`, `ontology_resolve.go:51-63`) | 예 |
| MCP stdio | `serve --transport stdio` → `mcp.ServeStdio` (`main.go:819-842`) | 없음 | 안 잡음("lock-free", `serve-mode.md:15-16`) | 예(19 tool) |
| MCP SSE | `serve --transport sse` → `127.0.0.1:<port>` 고정 (`internal/mcp/server.go:133-137`) | 없음 | 안 잡음 | 예 |
| Web UI | `serve --ui` → `web.NewWebServer` + `/v1` facade (`main.go:759-814`) | bearer + Host allowlist + Origin 검사 | 안 잡음 | `/v1` 쓰기 라우트로 예. SPA 자체는 읽기·Q&A만 |
| HTTP serve | `serve --addr` 또는 맨 `serve` → `runServeHTTP` (`main.go:1465-1620`) | bearer만 | 잡음(`main.go:1560`) | 예(REST + `/mcp` + `/v1`) |
| 다중 workspace serve | `serve --workspace-root` → `serve.NewMulti` (`main.go:1624-1662`) | root bearer 하나 | workspace마다 Manager가 잡음 | 예 |

그 밖의 면: hub(CLI 전용 federated search, `internal/hub`), `pkg/engine`·`pkg/sagewiki`(Go 임베딩), `clients/{python,typescript}`(`/v1` 타입 클라이언트), TUI(`internal/tui`, browse·search·query·compile 탭; 훑음).

### 호출 관계

```
CLI ─┬─ pkg/engine.Open (lock) ─ compiler / wiki.Ingest / capturefmt
     └─ storedial 직접 (lock 없음) ─ linter.StoreLearning / ontology store

serve --addr ── serve.Server ─┬─ REST(/capture /search /graph/query /docs) ─ callTool ─┐
                              ├─ /compile ─ Queue(.sage/jobs.jsonl) ─ serveJobRunner ─ coord.TryCompile ─ compiler.Compile
                              ├─ /mcp ─ StreamableHTTPServer ───────────────────────────┤
                              └─ /v1 ─ api.Router ─ dispatch ───────────────────────────┤
serve --ui ── web.WebServer ─┬─ /api/* (SPA 전용, 직접 store 접근)                        │
                             └─ /v1 ─ api.Router ────────────────────────────────────────┤
serve --transport stdio|sse ─────────────────────────────────────────────────────────────┤
                                                                                         ▼
                                                              mcp.Server.CallTool → 19 handler
Deps(공유): CompileCoordinator(1-슬롯 세마포어) · Progress hub · compile Worker · MirrorShipper · event Bus
```

`api.TranslateToolResult`가 "ONE result translation"으로 `/v1`과 `serve` REST 양쪽을 맡는다(`internal/api/dispatch.go:73-79`, `internal/serve/server.go:386-406`).

## 19개 MCP tool

등록은 `internal/mcp/server.go:117-119`, 이름→handler 표는 `server.go:175-203`이다. 셋으로 나뉜다.

| 묶음 | tool | 하는 일 | LLM |
|---|---|---|---|
| 읽기 7 | `wiki_search` | hybrid 검색 + trust 거르기 + 미컴파일 source 힌트 | expand·rerank 요청 시만 |
| | `wiki_read` | 파일 읽기, `pathsafe.Contained`로 경계 검사 | 아니오 |
| | `wiki_status`, `wiki_list`, `wiki_provenance`, `wiki_ontology_query` | 통계·entity 목록·source↔article·그래프 순회(alias면 canonical부터) | 아니오 |
| | `wiki_graph_query` | multi-hop 그래프 QA, `as_of`, `mode=global` | 예 |
| 쓰기 9 | `wiki_add_source` | 파일을 manifest에 등록(`manifest.Mutate`) | 아니오 |
| | `wiki_write_summary`, `wiki_write_article` | 에이전트가 쓴 본문을 파일→DB→manifest 순으로 기록 | 아니오 |
| | `wiki_add_ontology` | entity 또는 relation 직접 추가 | 아니오 |
| | `wiki_learn` | `learnings` 표에 한 줄 | 아니오 |
| | `wiki_commit` | `git add . && git commit` | 아니오 |
| | `wiki_compile_diff` | 실제 파일 diff | 아니오 |
| | `wiki_capture` | 대화 텍스트 → 지식 항목 → `raw/captures/*.md` | 예 |
| | `wiki_compile_topic` | 주제 관련 미컴파일 source를 tier 3로 올려 컴파일 | 예 |
| 복합 3 | `wiki_compile`, `wiki_lint`, `wiki_query` | 전체 컴파일 · lint · 질문→답→`under_review/` 보관 | 예 |

## 핵심 자료구조

필드는 코드 그대로다.

| 구조 | 위치 | 필드 |
|---|---|---|
| `serve.Config` | `internal/serve/server.go:32-48` | Workspace, Tokens []string, MaxConcurrentCompiles, DrainTimeout, RateLimit(middleware), Addr, CompileSem, ReadyFn, Bus |
| `serve.Job` | `internal/serve/jobs.go:44-55` | ID, Kind("compile"), Status, Request, Result, Error, CreatedAt, StartedAt, FinishedAt |
| `CompileJobRequest` | `jobs.go:35-42` | Tier *int, Model, MaxDocs, MaxCost *string — "parameters only — never source content" |
| job 상태 | `jobs.go:21-33` | pending, running, done, failed, cancelled, interrupted(재시작 때 running이던 것) |
| `ledgerEvent` | `jobs.go:57-62` | Op(submit/start/finish/transition), Job, Error → `.sage/jobs.jsonl` 한 줄 |
| `api.Route` | `internal/api/router.go:16-23` | Method, Pattern(ServeMux), Path(OpenAPI), Tool, Params, Handler |
| `MultiConfig` | `internal/serve/multi.go:22-30` | Root, Tokens(root 전용), MaxOpen(LRU), IdleClose, MaxConcurrentCompiles, DrainTimeout, RateLimit |
| `serve.Deps` | `internal/serve/deps.go:23-35` | coord, progress, worker, workerApp, mirrorShipper, dir, eventSink |
| `mirror.State` | `internal/mirror/state.go` | FormatVersion, Generation, DB{Snapshot, SnapshotSHA256, CreatedAt, WAL[]{Key,SHA256,SealedAt}}, Objects/Vectors map[path]ObjectRef{Key,SHA256,Deleted,ContentSHA256}, UpdatedAt, RetainGenerations |
| `auth.Credential` | `internal/auth/auth.go:16-23` | AccessToken, RefreshToken, ExpiresAt, AccountID, Source — LLM 공급자 자격이지 사용자 신원이 아니다 |
| `hub.Project` / `FederatedResult` | `internal/hub/hub.go:12-16`, `search.go:21-27` | Path, Description, Searchable / Project, ArticlePath, Content, RRFScore, Tags |
| `skill.TemplateData` | `internal/skill/skill.go:24-32` | Project, SourceTypes, EntityTypes, RelationTypes, HasOntology, DefaultTier, HasGraphExpansion |
| `limits.Limits` | `internal/limits/limits.go:33-43` | MaxDocBytes 10MiB, MaxDocsPerCaptureBatch 10, MaxCompileBatch 1000, MaxQueryBytes 32KiB, MaxGraphTraversalNodes 10000, MaxConcurrentProviderCalls 20, MaxConcurrentRequestsPerConn 8, ProviderTimeout 120s, CompileDocTimeout 15m |
| capture frontmatter | `internal/capturefmt/capturefmt.go:16-41` | source(origin: `mcp-capture`·`cli-capture`), captured_at, [raw: true], tags, context |
| `learnings` 표 | `internal/storage/db.go:320-327` | id, type, content, tags, created_at, source_lint_pass(`mcp`·`cli`) |
| `entity_aliases` 결정 열 | `internal/storage/db.go:641-653` | status, confidence, reason, source, decided_at, decided_by — 값은 `auto`/`user`/`unlink`(`internal/store/domain.go:160`, `resolve_entities.go:1504`, `postgres/aliases.go:357`) |
| event 봉투·payload | `docs/webhooks.md:207-208`, `pkg/events/payloads.go` | {id, time, workspace, type, data}. 예: DocCaptured{doc_id, bytes, content_hash}, EntityResolved{canonical, alias, confidence, auto} |

## 동작 흐름

### wiki_capture (MCP)

대화나 회의록 텍스트를 지식 항목 여러 개로 쪼개 raw source로 저장한다. 컴파일은 하지 않는다.

| 단계 | 처리 | 근거 |
|---|---|---|
| 1 입력 검사(코드) | content 필수, 100KB 상한, UTF-8 검사(`EncodingGate`) | `internal/mcp/tools_write.go:427-444` |
| 2 LLM 호출 | 프롬프트 `internal/prompts/templates/capture_knowledge.txt`, 본문은 `WrapUntrusted`로 감쌈, `StructuredCompletion` + `CaptureSchema`({title, content} 배열), 모델은 `models.summarize`(없으면 gpt-4o-mini), 사용량은 pass "extract"로 기록 | `tools_write.go:571-622, 853-869` |
| 3 실패 처리 | LLM 실패 시 원문 통째로 `raw/captures/raw-<시각>.md`에 `raw: true`로 저장 | `tools_write.go:453-461, 624-648` |
| 4 결정적 검사 | 항목 수 > `max_docs_per_capture_batch`(10)면 전체 거부, 제목이 빈 slug면 전체 거부(부분 저장 없음) | `tools_write.go:468-485` |
| 5 쓰기 | `raw/captures/<slug>.md`, frontmatter `source: mcp-capture` | `tools_write.go:497-535` |
| 6 manifest | 한 번의 `manifest.Mutate`로 모두 등록 | `tools_write.go:538-549` |

프롬프트는 "personal wiki"에 남길 "decisions, discoveries, corrections, technical facts, and insights"를 뽑으라고 한다(`capture_knowledge.txt:1-3`). 기존 용어집·entity 목록은 넣지 않는다.

같은 제목 slug 중복은 한 호출 안에서만 `-2`를 붙인다(`tools_write.go:499-508`). 쓰기는 `os.WriteFile`이라 다른 호출이 같은 slug를 내면 앞 파일을 덮는다(`tools_write.go:527`). 이 덮어쓰기는 코드를 읽어서 본 것이고 실행으로 확인하지는 않았다.

CLI `capture`는 다르다. `engine.Capture`가 LLM 없이 원문 그대로 `raw/captures/capture-<날짜>[-N].md`로 저장하고, 기존 파일은 `-N`으로 피한다(`pkg/engine/methods.go:89-145`, `cmd/sage-wiki/capture.go:84-90`). 그런데 `team-setup.md:461-462`는 "The capture command extracts knowledge items"라고 적는다. 문서와 코드가 어긋난다.

### wiki_learn

`linter.StoreLearning`이 `learnings` 표에 내용 해시를 id로 넣는다(`internal/mcp/tools_write.go:367-380`, `internal/linter/learning.go:24-41`). MCP handler는 type을 검사하지 않는다. `/v1/learnings`만 5종(gotcha, correction, convention, error-fix, api-drift)으로 막는다(`internal/api/handlers_write.go:127-140`).

이 표를 읽는 운영 코드가 없다. `RecallLearnings`·`ListLearnings`·`PruneLearnings`는 `sqlitestore` 어댑터에서만 감싸고, 그 메서드는 `internal/storetest/suite.go`에서만 부른다(grep `Recall(\|ListLearnings(\|PruneLearn` 결과).

`write_article.txt:20-22`에 `{{.Learnings}}` 칸이 있지만 이 필드를 채우는 코드가 없다(grep `Learnings:`·`.Learnings` 결과, 첫 commit `4876ddb`부터 같음). 그래서 180일 TTL·500개 상한(`learning.go:11-14`)도 실제로 돌지 않는다.

`team-setup.md:423-424`의 "Next time any agent on the team deals with timestamps, the wiki search returns this convention"은 코드와 맞지 않는다. `learnings`는 FTS 트리거도 없다(`internal/storage/db.go:319-327`).

skill 템플릿은 에이전트에게 `wiki_learn` type "decision"을 쓰라고 한다(`internal/skill/packs/base.md.tmpl:27`). MCP는 받지만 `/v1`은 400으로 거부한다.

### wiki_add_ontology

entity는 `AddEntity`, relation은 `AddRelation`으로 바로 쓴다(`tools_write.go:305-364`). id는 받은 문자열 그대로이고 정규화·동의어 대조·evidence 검사를 거치지 않는다. 어휘 밖 type/relation은 저장소 층이 거부한다(앞선 보고서가 인용한 `internal/ontology/ontology.go:153-155, 308-309`).

temporal이 켜져 있으면 두 규칙이 붙는다. `contradicts`는 trust conflict로 검토 대기열에 올린다. functional 관계는 이전 값을 바로 무효화한다(`tools_write.go:338-361`). 주석은 그 이유를 "manual adds are explicit user intent"라고 적는다(`tools_write.go:342`) — 수동 추가는 사용자의 명시적 의도이기 때문이다.

### wiki_write_summary / wiki_write_article

에이전트가 LLM 없이 직접 쓴 본문을 넣는 길이다. 순서는 ① 파일 atomic write ② DB 색인(FTS·vector·entity) ③ manifest `Mutate`다. 색인 실패는 반환하지 않고 로그만 남긴다. 다음 시작 때 reconciler가 고친다(`tools_write.go:184-303`, 주석 "Canonical write-then-index order (I2)", "REL-04").

article id는 `pathsafe.ValidConceptID`로 문자셋을 검사한다(`tools_write.go:251-257`). 이 길로 쓴 concept은 manifest에 Sources 없이 들어간다. 컴파일이 같은 key를 쓰면 컴파일 쪽이 이긴다(`tools_write.go:291-294`).

### wiki_search

| 단계 | 처리 | 근거 |
|---|---|---|
| 길이 검사 | `max_query_bytes` 넘으면 거부 + `limit_exceeded` 이벤트 | `server.go:291-293`, `tools_write.go:384-395` |
| trust 거르기 | `trust.include_outputs`가 verified면 확인된 output만 결과에 넣음. 주석: "The trust rule is the wiki's, not the pipeline's" | `server.go:305-312` |
| 검색 | unified 파이프라인(BM25 + vector + graph, LLM 단계 기본 끔) | `server.go:315-376` |
| 잘라내기 | 결과 본문을 `result_max_chars`로 자르고 `wiki_read` 안내를 붙임 | `server.go:410-415, 449-476` (#104) |
| 승격 신호 | 미컴파일 source가 걸리면 `RecordQueryHit`으로 tier 승격 기록 + `compile_hint` 응답 | `server.go:417-443` |

검색 자체가 "어떤 raw를 더 컴파일할지"의 입력이 된다. 많이 질문받는 주제가 먼저 깊게 컴파일된다.

### wiki_query

`query.Query`(CLI와 같은 파이프라인)로 답을 합성한다. 기본 설정에서는 `wiki/under_review/`에, `include_outputs: "true"`일 때만 `wiki/outputs/`에 보관한다(`internal/mcp/tools_compound.go:36-97`, 커밋 `e99e460`). web UI의 `/api/query`는 같은 Q&A를 SSE로 흘리고, 동시 1개만 허용한다(`internal/web/server.go:905-971`).

### serve --addr 시작·종료

| 순서 | 처리 | 근거 |
|---|---|---|
| 1 | 토큰 해석: flag > token-file(줄마다 하나) > `SAGE_WIKI_TOKEN` > config | `internal/serve/auth.go:19-48` |
| 2 | 비-loopback인데 토큰 0개면 시작 거부(`--insecure-no-auth`로만 우회) | `auth.go:52-68` |
| 3 | 이벤트 버스 + webhook 구성. webhook 설정 오류는 시작 실패 | `main.go:1491-1520` |
| 4 | 먼저 bind하고 `/healthz`·`/readyz`(503)만 응답 | `main.go:1522-1553` |
| 5 | `engine.Open`으로 workspace 잠금 | `main.go:1557-1569` |
| 6 | Deps(coordinator·worker·mirror) + MCP 서버 + `serve.New` | `main.go:1572-1600` |
| 7 | 전체 handler로 원자 교체, readyz ready | `main.go:1603-1607` |
| 8 | worker·mirror·job queue 시작 | `main.go:1609-1617` |

종료는 SSE 스트림 취소 → HTTP drain → job queue(진행 중 1개만 끝냄) → MCP → metrics snapshot → deps → 잠금 해제 순이다. 잠금 해제가 마지막이다(`internal/serve/server.go:165-203`, `jobs.go:394-398`).

### async compile job (두 벌)

job 시스템이 두 벌이다. 겹침은 같은 coordinator가 막는다.

| | `serve --addr`의 `POST /compile` | `/v1/jobs/{compile,lint}` (양쪽 stack) |
|---|---|---|
| 저장 | `.sage/jobs.jsonl` 영속, 재시작 시 pending 재개·running→interrupted | 메모리, 재시작하면 사라짐(`docs/guides/http-api.md:257-259`) |
| 상한 | backlog 100이면 409 | 100개 보관(FIFO 축출) |
| 동시성 | workspace당 FIFO, multi 모드는 root 세마포어 | compile 종류 하나만 active, 아니면 409 + active_job_id |
| 실행 | `serveJobRunner.RunCompile` → `coord.TryCompile` | 같은 JobRunner |
| 근거 | `internal/serve/jobs.go`, 커밋 `cac0b9d` | `internal/api/jobs.go:40-157`, 커밋 `d3c43ee` |

MCP `wiki_compile`은 coordinator를 거치지 않고 `compiler.Compile`을 바로 부른다(`internal/mcp/tools_compound.go:99-121`). `wiki_compile_topic`은 `CompileOrWait`로 기다린다(`internal/compiler/ondemand.go:277-278`).

### /v1 dispatch와 idempotency

라우트 표 하나가 등록과 drift 검사를 함께 맡는다(`internal/api/router.go:11-15, 47-92`). OpenAPI(`api/openapi.yaml`) ⇄ 라우트 ⇄ tool 레지스트리를 CI가 대조한다(`http-api.md:97-99`).

쓰기 라우트는 `Idempotency-Key`를 받는다. 저장소는 메모리 LRU(1000개, 24h)이고 재시작하면 사라진다. 같은 key가 동시에 오면 한 번만 실행하고 나머지는 결과를 재생한다(`internal/api/idempotency.go:11-19, 184-215`).

경로가 섞일 수 있는 tool의 500 메시지는 일반 문구로 바꾸고 원문은 서버 로그에만 남긴다(`internal/api/dispatch.go:44-55, 79-112`).

### 다중 workspace serve

`/v1/workspaces`는 root 아래 workspace 목록이고, `/w/{name}/...`은 workspace마다 lazy하게 조립한 SPEC-02 stack이다. 이름 검사는 mux 정리 전에 하고, 잘못된 이름과 없는 이름은 같은 404다(`internal/serve/multi.go:152-260`). 잠금 경합은 503 + Retry-After다(`multi.go:248-253`).

compile 동시성은 root 세마포어 하나가 모든 workspace를 묶는다(`multi.go:111-116`, `semaphore.go`). 살아 있는 stack 수는 LRU(`--max-open`)와 idle close로 제한한다.

### web UI 보안 미들웨어

| 순서 | 검사 | 근거 |
|---|---|---|
| 1 | Host가 loopback 또는 allowlist가 아니면 403. DNS rebinding(악성 도메인을 내부 IP로 다시 가리켜 브라우저로 로컬 서버를 치는 공격) 방어 | `internal/web/server.go:418-429` |
| 2 | 보안 헤더 + CSP | `server.go:408-413, 430-432` |
| 3 | 토큰이 설정돼 있으면 `/api/*`, `/ws`, `/v1/*`, `/metrics`에 bearer 요구(헤더 또는 `?token=`) | `server.go:434-447, 476-478` |
| 4 | POST와 `/v1` PUT/DELETE/PATCH, `/api/query`는 Origin이 Host와 다르면 403 | `server.go:449-469` |

SPA는 토큰을 메모리에만 두고 URL에서 지운다. localStorage는 쓰지 않는다(`web/src/lib/token.ts:1-24`). SPA 화면은 tree·article·search·graph·Q&A·compile 진행이고 편집 기능은 없다(`web/src/components/`, `web/src/lib/api.ts`). tree에는 concepts·summaries·outputs만 보이고 under_review는 보이지 않는다(`server.go:571`).

### mirror(S3 백업)와 hydrate

"the mirror is durability and mobility, never a live query path"(`docs/guides/remote-mirror.md:5-6`) — 백업과 이동용이지 공유 조회 경로가 아니다.

- 보내는 것: `wiki/`, `raw/`, `prompts/`, manifest, `.sage/wiki.db`(snapshot + WAL segment, Litestream 방식), vector index, pack-state. `config.yaml`은 비밀이 있을 수 있어 보내지 않는다(`remote-mirror.md:26-33`).
- 순서: `serve`는 `ship_interval`(기본 1s)마다, CLI는 모든 명령 뒤에 best-effort로 보낸다. 실패해도 명령 종료 코드는 바꾸지 않는다(`cmd/sage-wiki/mirror_hook.go:17-78`).
- 충돌 안전: commit pointer `mirror-state.json`을 마지막에 쓴다. 문서 객체는 content-addressed key(`objects/docs/<sha2>/<sha256>`)다(`internal/mirror/layout.go:9-18`, `state.go`).
- 단일 leader: `.sage/mirror-ship.lock`으로 한 번에 한 shipper만 seal·rotate·commit한다(`internal/mirror/shipmutex.go:11-14`).
- 복원: 빈 디렉토리에만 한다(병합 없음). `--generation`, `--at`으로 PITR(point-in-time restore, 과거 시점 복원)이 되고, 선택적으로 AES-256-GCM을 쓴다(`remote-mirror.md:49-110`).

### webhook·이벤트

이벤트 버스는 JSONL 감사 기록(`events/`), `/events/stream` SSE, 서명 webhook으로 나간다(`docs/guides/serve-mode.md:58-69`). webhook은 HMAC-SHA256 서명, 5xx·timeout만 지수 backoff 재시도, 실패는 `.sage/webhooks-deadletter.jsonl`이다(`docs/webhooks.md:205-220`).

배달은 worker 하나가 순차로 하고, 주석이 이를 "RECORDED DESIGN DECISION"으로 받아들인다(`internal/serve/webhooks.go:34-40`). 이벤트에는 문서 내용·원문 질의·절대 경로가 없다(`docs/webhooks.md:229-230`, `pkg/events/privacy_test.go`). 작성자·요청자 신원도 없다.

### hub federated search

`~/.sage-hub.yaml`에 project 경로를 등록한다(`internal/hub/hub.go:71-74`). 검색하면 project마다 reader 모드로 열어 병렬 hybrid 검색하고, 각자의 RRF 점수로 정렬해 자른다(`internal/hub/search.go:29-87`). 다시 RRF로 재점수하지 않는 이유는 "Do NOT re-score with positional RRF — that would discard magnitude"다(`search.go:76-77`) — 위치 기반으로 다시 매기면 점수 크기 정보가 사라지기 때문이다.

project마다 trust 규칙을 적용한다(`search.go:149-165`). project 사이에서 entity를 잇지는 않는다. hub는 CLI에서만 쓰고 MCP·REST에는 없다(grep `internal/hub` importer = `cmd/sage-wiki/hub.go` 하나).

### LLM 공급자 인증(subscription auth)

`internal/auth`는 사람 인증이 아니라 LLM 공급자 자격이다. 우선순위는 env API key > subscription token(`~/.sage-wiki/auth.json` 또는 OS keychain) > config api_key다(`internal/auth/resolve.go:13-45`). subscription이면 transport가 자동 refresh한다(`resolve.go:66-71`).

serve로 돌리면 서버 프로세스 사용자의 자격 하나로 모든 팀원의 LLM 비용이 나간다(`DefaultStorePath()`가 프로세스 HOME 기준, `resolve.go:23`). "each member can use their own subscription"(`team-setup.md:290-309`)은 각자 로컬에서 컴파일하는 Pattern A에서만 성립한다[추정](사례: 서버 경로에서 자격을 고르는 곳은 `resolve.go:13-45` 하나이고 요청자 정보를 받지 않는다).

### skill 파일

`sage-wiki skill refresh --target <agent>`가 `CLAUDE.md`·`.cursorrules`·`AGENTS.md` 등에 marker 블록을 넣거나 갱신한다(`internal/skill/skill.go:43-51`, `writer.go`). 템플릿은 언제 검색할지, 무엇을 capture할지 알려 주고, config의 entity type·relation type 목록을 넣는다(`internal/skill/packs/base.md.tmpl:36-38`). 이 목록이 "에이전트가 직접 쓸 때 쓰는 어휘"를 전달하는 유일한 길이다.

레포 루트의 `skills/sage-wiki/SKILL.md`는 `tools/skillgen`이 MCP 레지스트리에서 생성하고 CI가 drift를 검사한다(README:334-335, 커밋 `d3c43ee`).

### Obsidian vault overlay

`init --vault`는 vault 최상위 폴더를 훑는다. 파일이 있는 폴더는 모두 source(type article, watch), 빈 폴더는 ignore로 잡고 출력은 `_wiki/`에 둔다(`cmd/sage-wiki/main.go:311-347`, `internal/wiki/init.go:105-187, 190-226`). 숨은 폴더와 `_wiki`는 건너뛴다.

사람이 쓴 노트와 LLM 산출물이 같은 vault에 나란히 놓이고, Obsidian으로 둘 다 본다. "The `ignore` list keeps personal folders private"(`team-setup.md:696-698`)는 컴파일에서 빼는 것일 뿐이다. vault를 공유하면 파일 자체는 다 보인다[추정](사례: ignore는 `config.yaml` 항목 하나이고 파일 권한을 바꾸는 코드가 없음, `init.go:136-140`).

### LLM 호출 지점(이 갈래)

| 지점 | 프롬프트 | 모델 키 |
|---|---|---|
| `wiki_capture` | `capture_knowledge.txt` | `models.summarize` |
| `wiki_search` expand/rerank | search 패키지(다른 갈래) | `models.query` |
| `wiki_query`, `/api/query` | query 패키지(다른 갈래) | `models.query` |
| `wiki_compile_topic`, `wiki_compile`, job | compiler(다른 갈래) | pass별 |
| `wiki_graph_query` | graph QA(다른 갈래) | — |
| `sage-wiki scribe` | `internal/scribe`(다른 갈래), entity 최대 10개 | `models.extract` → summarize (`main.go:1387-1446`) |

## 설계 결정과 이유

(a)는 작성자가 밝힌 이유, (b)는 추론이다.

### S1. 모든 면을 MCP tool 하나로 몬다

REST(`/v1`, serve REST)는 tool을 `CallTool`로 부르기만 하고 자체 로직이 없다.

- (a) "16-route /v1 REST facade over the 18 MCP tools (dispatch via (*mcp.Server).CallTool, zero business logic)"(커밋 `d0fd8d6`). "every /v1 route reaches its capability through the same function the tool registers, never a copy"(`internal/api/dispatch.go:37-39`) — 같은 기능을 복사하지 않고 같은 함수에 닿게 하려는 것이다. "one translator, two route tables"(`internal/serve/server.go:387`, F-036).
- 대안: REST용 service 층을 따로 두는 것. 포기한 것: tool 결과가 text라 REST가 JSON 파싱으로 되돌린다(`dispatch.go:66-78`).
- 이력: MCP는 첫 commit `4876ddb`부터, `/v1`은 `d0fd8d6`(2026-07-30), serve REST는 `7f01e2e`(2026-08-01).

### S2. 쓰기 프로세스 하나(single-writer)와 workspace 잠금

- (a) `engine.Open`이 배타 flock을 잡아 "two processes … cannot write the same workspace concurrently"(`pkg/engine/doc.go:17-22`). CLI capture·query도 잠금을 잡게 바꿨고 "previously they raced lock-free"였다(CHANGELOG:413-414, 커밋 `7939d3c`). Postgres backend도 "advisory locks reproducing the single-writer world"이고 "multi-writer concurrency remains P2-3 scope — the single-writer process model is unchanged"다(CHANGELOG:1130-1142). 팀 가이드의 처방도 "Designate one compiler", "Use the server pattern — only one process writes to the DB"다(`team-setup.md:727-737`).
- (b)[추정] SQLite WAL과 파일 기반 manifest가 한 쓰기 주체를 전제하기 때문이다(사례 2개: 이슈 #102 "database is locked"에서 작성자가 여러 프로세스 동시 실행을 첫 의심으로 물음, `team-setup.md:729-730` "not safe for concurrent writes from multiple machines").
- 대안: 행 단위 동시 쓰기 또는 CRDT. 포기한 것: 여러 사람이 동시에 컴파일할 수 없다. 사람은 capture·검색만 하고 컴파일은 한 곳에서 한다.
- 빈틈: `serve --ui`와 MCP stdio·SSE는 잠금 없이 쓴다("pre-existing lock-free behavior", `serve-mode.md:15-17`). 그 사이 충돌은 manifest 잠금(`internal/manifest/lock.go`)과 프로세스 안 coordinator가 맡는다.

### S3. loopback은 설정 없이, 그 밖은 토큰을 강제

- (a) "Refuse to expose beyond loopback without a token (invariant: loopback stays zero-config; anything wider must be authenticated)"(`main.go:791-795`). 커밋 `d53322d` "The server REFUSES to start on a non-loopback bind without a token; loopback stays zero-config (invariant #7)". 토큰 비교는 sha256 digest 후 constant-time이다 — "raw-token comparison leaks length — F-022"(`internal/serve/auth.go:70-75`). 후보를 모두 비교하는 것은 "timing must not leak the match position"(`auth.go:104-112`) 때문이다.
- 대안: OIDC·사용자 계정. 포기한 것: 사람 구분이 없다. "Anyone with the token can do anything"(`docs/security.md:120-122`).
- `?token=` query 허용은 "web-server precedent"이고 "URLs leak via proxy/browser logs"를 알고 받아들였다(`serve-mode.md:37-40`).

### S4. 사용자별 권한은 범위 밖, 앞단에 붙인다

- (a) "Per-workspace auth is a SPEC-06 non-goal — operators compose tenancy in front; one root token guards every workspace"(`internal/serve/multi.go:125-127`). README: "this repo stays workspace-scoped, with no tenant/quota concepts"(README:586-589). Company 단계는 "front the server with auth"(README:26).
- 대안: 앱 안에 RBAC. 포기한 것: reverse proxy가 workspace 단위 접근만 나눌 수 있다. 문서·entity 단위 권한은 만들 자리가 없다.

### S5. web UI는 Host allowlist·Origin 검사를 더 얹는다

- (a) "Host-header allowlist … defeats DNS rebinding; Origin checked on POST + /api/query and WS upgrades"(커밋 `d53322d`). `hostAllowed`는 "DNS-rebinding defense for browsers; non-browser clients control their own Host, so the bearer token is the real gate"(`internal/web/server.go:480-484`). SPA 토큰을 메모리에만 두는 것은 "per the frontend security constraints"(`web/src/lib/token.ts:3-5`).
- serve `--addr`에는 이 검사가 없다("bearer-only (no Host/Origin checks)", `http-api.md:111-113`). (b)[추정] 그 stack은 브라우저가 아니라 에이전트·서비스가 쓰는 면이라서다(사례 1개: `serve-mode.md:3-6` "so agents and UIs connect to a warm engine").

### S6. 영속 job ledger: 매개변수만 적고, running은 interrupted로

- (a) "parameters only — never source content"(`jobs.go:35-36`). "a job left running when the process died is marked interrupted — never silently "running" forever"(`jobs.go:147-150`). 종료 때는 "Finish the CURRENT job only … Draining the whole backlog would start fresh compiles during shutdown"(`jobs.go:394-398`).
- 이력: `cac0b9d`(SPEC-02 Task 1-2). `/v1/jobs`는 그보다 먼저 메모리 store로 들어왔고(`d3c43ee`) 지금도 따로 있다.

### S7. Idempotency-Key는 메모리에만 둔다

- (a) "agents retry on timeout; a retried write — capture above all — silently duplicates work and re-spends LLM budget"(`internal/api/idempotency.go:11-14`). 메모리만 쓰는 것은 "03 sanctions in-memory for v1 provided the restart semantics are documented"(`idempotency.go:16-19`). singleflight 대신 직접 구현한 것은 "so the REST layer adds no new direct dependency"(`idempotency.go:187-188`).
- 포기한 것: 재시작이나 다중 프로세스 사이에서는 중복을 막지 못한다.

### S8. capture는 LLM 추출 + 실패 시 원문 저장 + 부분 저장 금지

- (a) 원래 목적은 "extracts knowledge items (decisions, discoveries, corrections) via LLM … graceful fallback to raw storage on LLM failure"(커밋 `9547063`). 상한 초과는 "a typed failure with an event — nothing partial persists"(`tools_write.go:468-469`). 빈 slug 거부는 "the old silent timestamped fallback let unnameable content in"(`tools_write.go:478-480`).
- 대안: 원문만 저장하고 컴파일에 맡기는 것(CLI capture가 이 방식). 포기한 것: MCP capture 결과는 LLM이 재구성한 문장이라 원문이 남지 않는다. LLM이 성공하면 원 대화는 저장되지 않는다(`tools_write.go:510-535`는 item.Content만 씀).

### S9. LLM 답은 under_review에 격리한다

- (a) 이슈 #74 "wiki/output used immediately in future searches: data poisoning potential"에서 시작했다. 작성자는 "treat LLM outputs as *claims* rather than *facts*. They need independent verification before entering the trusted corpus"라고 답했다 — LLM 산출물을 사실이 아닌 주장으로 다루라는 것이다. 팀 가이드는 "Prevents one person's wrong query from poisoning everyone's context"(`team-setup.md:281-283`)를 이유로 든다. trust 거르기는 모든 검색 면에 적용한다. "The trust rule is the wiki's, not the pipeline's"(`server.go:305-307`), hub도 같다(`internal/hub/search.go:149-154`).
- 경계: 검증·승격 로직(`internal/trust`)은 다른 갈래다.

### S10. 백업은 commit pointer를 마지막에 쓰는 S3 mirror

- (a) "The commit pointer (`mirror-state.json`) is always written LAST, after every object it references is durably uploaded. A kill at any byte leaves the previous committed generation restorable"(`remote-mirror.md:37-40`). `config.yaml`을 빼는 이유는 "can hold inline secrets"(`remote-mirror.md:30`). verify가 키 없이 되는 것은 hash가 암호문 기준이기 때문이다(`state.go` ObjectRef 주석).
- 대안: git push만 쓰기(Pattern A). 포기한 것: mirror는 한 workspace의 백업이지 여러 사람 사이의 동기화가 아니다. 복원은 빈 디렉토리에만 된다.
- 이력: SPEC-03, 커밋 `eefc031`~`92c326a`(2026-08-01~02, review 라운드 10여 회).

### S11. 자원 한도는 한 곳에, 0은 "끔"이 아니다

- (a) "Every enforceable cap lives in one place — `internal/limits` … A zero value never means "disabled""(`docs/security.md:32-35`). 위협 모델은 "Untrusted corpus. … A document may be hostile"(`security.md:15-18`)이다. 근거는 `tests/pathological`의 1GiB 스트림 문서다(`tests/pathological/generator.go:1-11`).
- `WriteTimeout`을 0으로 둔 것은 "/events/stream SSE and /export streaming would be cut mid-stream"(`internal/serve/hardened.go:180-185`) 때문이다.

### S12. webhook은 at-least-once, 순차 배달

- (a) "At-least-once is the OSS contract — no durable exactly-once"(`webhooks.go:32`). 순차 배달로 생기는 head-of-line 막힘은 "Accepted for OSS scope: the engine never stalls"(`webhooks.go:34-40`)로 받아들였다.

### S13. 이벤트에 내용·경로를 싣지 않는다

- (a) "Events never contain document content, raw query text (hashed), or filesystem paths"(`docs/webhooks.md:229-230`). 구조적으로 강제한다: "a future payload addition that smuggles in a body field fails here"(`pkg/events/privacy_test.go` 머리 주석).
- 포기한 것: 감사 기록으로 "어떤 문서에 무엇이 들어갔나"를 내용 수준에서 재구성할 수 없다.

### S14. skill 파일로 에이전트를 가르친다

- (a) "Agents ignore sage-wiki's 17 MCP tools because nothing in their context says when to use them. Skill templates are behavioral bridges"(커밋 `0dd13f5`, CHANGELOG:1569) — 맥락에 언제 쓰라는 말이 없어서 에이전트가 tool을 쓰지 않았다는 것이다. marker 기반 갱신은 "Marker-based write/refresh to preserve existing file content"(같은 커밋)다.
- 이력: 4개 domain pack이었다가 `917b3e3`(2026-05-10) "skill simplification"으로 `base.md.tmpl` 하나가 됐다.

### S15. hub는 project마다 점수를 그대로 합친다

- (a) PR #31 리뷰 지적("Double RRF")을 고쳐 "Do NOT re-score with positional RRF — that would discard magnitude"(`internal/hub/search.go:76-77`, PR #46)로 정했다. 동기는 "Users with multiple knowledge bases … currently have no way to search across them"(PR #31 본문)다.
- (b)[추정] project마다 embedder·가중치가 다르면 RRF 점수 크기를 서로 비교하기 어렵다(사례 1개: `searchWithStores`가 project config별 embedder·가중치를 따로 씀, `search.go:131-140`). 작성자는 이 문제를 다루지 않았다.

### S16. 같은 workspace에서 serve 시작 때 reconcile

- (a) "Heal any file<->DB drift once at server start … `serve --ui` (which builds both) still reconciles exactly once"(`main.go:702-706`). 쓰기 handler가 색인 실패를 로그로만 남기는 것(S1의 write-then-index)과 짝이다.

### S17. 테스트로 행동을 고정한다(parity suite)

- (a) "proves on every PR that observable behavior is unchanged unless a spec explicitly authorizes a change, and that a workspace is fully portable"(`docs/guides/parity-suite.md:3-5`). LLM 응답은 record/replay stub로 고정하고, golden이 바뀌면 PR에 "Golden changes" 절이 없을 때 CI가 실패한다(`parity-suite.md:189-198`).

### 이유 문서가 레포에 없다

commit과 주석은 SPEC-01~09, ADR-036~039, `decisions.md`, "spec §2.7", "Gate 3/8"을 계속 가리킨다. 이 문서들은 레포에 없다. `.gitignore`가 `.sage/`, `sage/`, `CLAUDE.md`를 뺀다(`.gitignore:1-12`). Sage Framework(https://github.com/xoai/sage)는 "spec.md MUST EXIST on disk"를 상태로 쓰고 `.sage/decisions.md`를 append-only 결정 기록으로 둔다. 그래서 위 (a)는 주석·commit 본문에 새어 나온 이유만이다.

## 누가 썼는지

엔터프라이즈 다중 작성자 용도에서 가장 큰 빈자리다. 쓰기 기록마다 남는 것은 아래와 같다.

| 기록 | 남는 "출처" | 근거 |
|---|---|---|
| capture 파일 | `source: mcp-capture` / `cli-capture`, captured_at, tags, context | `capturefmt.go:28-38` |
| learnings | `source_lint_pass` = `mcp` / `cli` | `tools_write.go:376`, `learn.go:41` |
| alias 결정 | `decided_by` = `auto` / `user` / `unlink` | `store/domain.go:160` |
| git commit | 서버 프로세스의 git identity, 메시지 "compile: +N sources…" 또는 "wiki: update at <시각>" | `internal/git/git.go:71-80`, `compiler/pipeline.go:575-580`, `tools_write.go:686-695` |
| 이벤트 | workspace 이름, type, data. 행위자 없음 | `docs/webhooks.md:207-208` |
| bearer 토큰 | 토큰 파일에 여러 개를 둘 수 있지만 어느 토큰으로 들어왔는지 기록하지 않는다 | `internal/serve/auth.go:79-102` |

토큰 파일의 여러 줄은 팀원별 토큰처럼 쓸 수 있다. 하지만 `authMiddleware`는 통과·거부만 하고 요청 context에 신원을 싣지 않는다(`auth.go:85-101`). 확인한 곳: `internal/serve`, `internal/api`, `internal/mcp`, `pkg/events`에서 grep `actor|user_id|author|reviewer` 결과 없음. `owner`는 compile queue lease 소유 프로세스뿐이었다(`internal/storage/postgres/items.go`).

## 앞선 schema-glossary 보고서와 비교

앞선 보고서(`.../schema-glossary/sage-wiki-ontology.md`)는 컴파일 경로만 다뤘다. 이 갈래 범위에서 보완하거나 어긋나는 점은 넷이다.

1. "강제는 세 겹"(프롬프트·schema·쓰기 직전 Go 검증)은 컴파일 경로에만 맞는다. 에이전트가 `wiki_add_ontology`·`/v1/ontology/*`로 직접 쓰면 프롬프트·`normalizeGraph`·동의어 대조·evidence 검사가 없다. 저장소 층의 어휘 검사 한 겹만 남는다(`tools_write.go:305-364`). entity id도 정규화하지 않아 "Foo Bar"와 "foo-bar"가 별개 행이 된다[추정](사례: `AddEntity`에 id를 그대로 넘김, `tools_write.go:320`).
2. "사람의 역할은 제안을 승인·거절·`--unlink`"는 맞다. 다만 그 결정을 누가 했는지는 `user`로만 남는다(#누가 썼는지).
3. 보고서는 용어집을 사람이 쓰지 않는다고 했다. 에이전트 쪽 어휘 전달도 skill 파일의 entity·relation type 이름 목록뿐이다(`base.md.tmpl:36-38`). 이 목록은 관계 동의어·별칭을 담지 않는다.
4. 문서와 코드가 어긋나는 곳이 셋 있다. 앞선 보고서와 별개로 보고서 작성자가 알아야 한다.
   - web UI가 MCP를 `/sse`로 연다는 설명(`serve-mode.md:51-56`, `self-hosted-server.md:7-13`, `team-setup.md:176-188`, 커밋 `9876487`에서 추가)과 달리 `web.Handler`에는 `/sse` 라우트가 없다(`internal/web/server.go:139-182`). `git log -S'/sse' -- internal/web`에도 추가 이력이 없다. `serve --transport sse`는 `127.0.0.1` 고정이다(`internal/mcp/server.go:133-137`). 원격 에이전트가 실제로 쓸 수 있는 MCP는 `serve --addr`의 `/mcp`다. 실행해 보지는 않았다.
   - "self-learning loop"(`wiki_learn`)는 저장만 하고 읽지 않는다(#wiki_learn).
   - "The capture command extracts knowledge items"(`team-setup.md:461`)와 달리 CLI capture는 LLM 추출 없이 원문을 저장한다(#wiki_capture (MCP)).

## 엔터프라이즈 다중 작성자 용도

조건은 넷이다. 용어 불일치, 형식 없는 문서, 여러 사람, 권한.

### 쓸 만한 장치

| 장치 | 왜 쓸 만한가 | 근거 |
|---|---|---|
| tool 레지스트리 하나 + 얇은 REST·MCP | 사람 UI·에이전트·배치가 같은 검증을 거친다. 새 면을 붙여도 규칙이 갈리지 않는다 | S1 |
| 쓰기 프로세스 하나 + 사람은 capture만 | 여러 사람이 raw를 던지고 한 곳이 컴파일하는 구조가 "형식 없는 문서를 모아 잇기"에 맞는다 | S2, `team-setup.md:732-733` |
| capture의 문서 단위 원자성(상한 넘으면 전부 거부)과 typed 이벤트 | 사람 입력을 대량으로 받아도 반쯤 들어간 상태가 남지 않는다 | S8 |
| `wiki_search`의 `uncompiled_sources` + 질의 기반 승격 | 사람들이 실제로 묻는 주제부터 깊게 컴파일한다. 비용과 품질을 사용 빈도에 맞춘다 | `server.go:417-443` |
| under_review 격리 + 모든 검색 면의 trust 거르기 | 한 사람의 잘못된 LLM 답이 전사 맥락을 오염시키지 않는다 | S9 |
| Idempotency-Key | 에이전트 재시도로 같은 보고서가 두 번 들어가는 것을 막는다 | S7 |
| 서명 webhook·SSE 이벤트 | 컴파일 완료·alias 확정을 다른 시스템(알림, 검토 큐)에 이을 수 있다 | S12 |
| mirror + PITR | 잘못된 대량 입력 뒤에 시점 복원이 된다 | S10 |
| skill 파일로 어휘 전달 | 에이전트에게 entity·relation 어휘를 주는 싼 길이다. 용어집(정식 이름+별칭)을 여기에 넣는 변형을 생각할 수 있다 | S14 |
| config `extends` | 팀 공통 schema를 base config로 두고 project별로 덮는다(단일 단계) | `internal/config/config.go:1214-1260`, PR #31 |
| parity suite(record/replay) | 프롬프트·schema를 바꿀 때 그래프·검색 결과가 어떻게 변하는지 PR마다 볼 수 있다 | S17 |

### 걸리는 점

| 걸림 | 내용 | 근거 |
|---|---|---|
| 사람 신원 없음 | 누가 쓴 보고서인지, 누가 alias를 승인했는지 남지 않는다. 작성자별 용어 차이를 "작성자"로 거를 수 없다 | #누가 썼는지 |
| 권한 없음 | 토큰 하나 = 전권. 문서·entity 단위 접근 제어를 붙일 자리가 없다. reverse proxy로는 workspace 단위까지만 나뉜다 | S4 |
| 컴파일 동시성 | 한 workspace에 쓰기 프로세스 하나다. 부서별로 나누면 workspace가 갈리고, workspace 사이 연결은 hub 검색뿐이다(entity 연결 없음) | S2, S15 |
| MCP capture가 원문을 버림 | 대화·보고서 원문 대신 LLM 재서술만 남는다. 원문 근거 추적이 끊긴다 | S8 |
| capture slug 덮어쓰기 | 다른 사람이 같은 주제로 capture하면 LLM이 같은 slug를 내 앞 파일을 덮을 수 있다. 다중 작성자에서 조용한 손실이다(코드 읽기, 미실행) | `tools_write.go:527` |
| learnings 미사용 | 팀 convention을 `wiki_learn`으로 남겨도 검색·컴파일에 반영되지 않는다 | #wiki_learn |
| 에이전트 직접 쓰기 경로의 어휘 강제 약함 | `wiki_add_ontology`가 정규화·동의어 대조를 건너뛴다. 용어 불일치가 그래프에 바로 들어간다 | 비교 1번 |
| LLM 비용 귀속 | serve 모드에서는 서버 자격 하나로 모든 호출이 나간다. 사용량 ledger에도 요청자가 없다 | #LLM 공급자 인증(subscription auth) |
| 감사 기록에 내용 없음 | 이벤트가 내용·경로를 빼므로 규제 감사용 "무엇이 언제 들어갔나"는 git과 mirror로 따로 봐야 한다 | S13 |
| 문서-코드 불일치 | 팀 가이드의 Pattern B(`/sse`)가 코드와 다르다. 가이드를 그대로 따라 하면 막힐 수 있다 | 비교 4번 |

## 모르는 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| SPEC-01~09, ADR-036~039, `decisions.md`의 원문 이유(예: per-workspace auth를 왜 non-goal로 했는지, `/v1/jobs`와 ledger를 왜 둘로 뒀는지) | 레포에 없다(.gitignore). 작성자에게 묻거나 공개된 Sage cycle 산출물이 있는지 확인. X 글 https://x.com/xoai/status/2040936964799795503 ("lessons learned")은 읽지 못했다 |
| MCP `wiki_compile`이 coordinator를 건너뛸 때 serve worker와 실제로 겹치는지 | `internal/compiler/pipeline.go`의 compile_items lease·manifest 잠금 경로(컴파일 갈래)를 읽거나 `internal/serve` 통합 테스트를 실행 |
| capture slug 덮어쓰기가 실제로 일어나는지 | 같은 제목을 내는 LLM stub로 `wiki_capture`를 두 번 부르는 테스트 실행 |
| web UI에서 `/sse`를 부르면 무엇이 오는지(SPA fallback HTML로 보임) | `serve --ui` 실행 후 `curl /sse` |
| learnings를 읽는 기능을 의도적으로 뺐는지, 미완성인지 | 이슈·작성자 문의. `docs/guides/agent-memory-layer.md`(범위 밖)의 설명 |
| 팀 규모(3~50명) 주장의 실제 운영 사례 | 이슈·토론에 팀 운영 보고가 없다(`gh issue list` 전체 훑음). 사용자 사례 검색 필요 |
| hub의 RRF 점수가 project 사이에 비교 가능한지 | 서로 다른 embedder를 쓰는 두 project로 `hub search` 실행 |
| eval이 다중 작성자·용어 불일치를 재는지 | 재지 않는다. `eval/eval.py`의 9개 점수는 구조 지표이고, recall@k는 concept 이름으로 자기 article을 찾는 것이다(`eval/eval.py:680-708, 855-865`). benchmarks는 대화 기억(LOCOMO 등)이다(`eval/benchmarks/README.md:1-30`). 용어 불일치용 평가는 직접 만들어야 한다 |

## eval이 재는 것

`eval/eval.py`는 읽기 전용으로 compiled wiki를 잰다. 성능(FTS·vector·RRF·graph BFS·쓰기 처리량)과 품질 9개를 잰다(`eval/README.md:43-77`). 품질 9개의 평균이 overall이다(`eval/eval.py:855-875`).

| 품질 지표 | 실제로 재는 것 |
|---|---|
| Fact extraction rate | summary에 `## Key claims` 절이 있는 비율 |
| Concept coverage | summary가 이름 붙인 concept 중 article이 있는 비율(작성자는 통합 비율로 읽으라 함, `eval/REPORT.md:28-34`) |
| Cross-reference integrity | `[[wikilink]]`가 실재 article을 가리키는 비율 |
| Search recall@10 | concept 이름을 FTS에 그대로 넣어 그 article이 10위 안에 오는 비율(`eval.py:688-702`) |
| Source citation rate, Key claims·Definition 절 비율 | 형식 준수 |
| Alias coverage | alias를 가진 concept 비율 |
| Wiki connectivity | inbound link 분포 |

중복 탐지는 이름 유사도 > 0.85(SequenceMatcher)다(`eval.py:798`). 작성자가 고친 이력도 있다. 2026-04 판 숫자는 "described the fixture's own generator parameters"였고 실제 wiki 10개로 다시 쟀다(`eval/REPORT.md:7-10`).

`eval/benchmarks`는 mem0 harness로 LOCOMO 92.0%, LongMemEval-S 93.3%, BEAM 69.1%를 보고한다(gpt-5 judge, top-50/200, `eval/benchmarks/REPORT.md:14-18`). 작성자 결론은 "retrieval, not compilation, was the binding constraint"다(`REPORT.md:25-35`) — 컴파일이 아니라 검색이 병목이었다는 것이다. 보고서 스스로 mem0 표와 직접 비교하지 말라고 적는다(`REPORT.md:470-503`).

## 다른 갈래와의 경계

| 주제 | 이 노트에서 한 것 | 깊게 볼 갈래 |
|---|---|---|
| trust(검증·합의·승격) | 검색 면의 거르기와 under_review 보관만 | trust·query 갈래 |
| entity resolution·alias 링크 | CLI 면과 `decided_by`만 | 컴파일·온톨로지 갈래 |
| compile worker·compile_items lease·tier 승격 | serve Deps에 붙는 자리만 | 컴파일 갈래 |
| search 파이프라인(unified, graph leg) | MCP 진입·trust·잘라내기만 | 검색 갈래 |
| storage backend(Postgres) | single-writer 인용만 | 저장 갈래 |
| scribe, pack | CLI 진입만 | 해당 갈래 |
| `ci/` | 레포 자체 CI 거버넌스(fuzz 목록, 패키지 소유, 배포 정책)라 wiki 동작과 무관. 훑음 | — |

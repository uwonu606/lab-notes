# nashsu/llm_wiki — LLM이 사람 승인 없이 wiki를 쓰고, 앱 코드가 그 출력을 사후에 고치고 걸러 낸다

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/nashsu/llm_wiki |
| clone commit | `48fd970` (2026-09-28, "fix: verify notarized app inside macOS DMG") — shallow clone이라 커밋 1개만 보인다 |
| 별 / fork | 20,422 / 2,307 (`gh api`, 2026-10-11 조회) |
| 최근 push | 2026-09-28 |
| 라이선스 | GPL-3.0. `gh api`는 `NOASSERTION`을 돌려준다. `LICENSE` 파일 첫 줄은 "Copyright (C) 2024-2026 Yong Su"이다. 본문은 GNU GPL v3이다. |
| 형태 | Tauri v2 데스크톱 앱 (React 19 + TypeScript 프런트, Rust 백엔드). 로컬 HTTP API(`127.0.0.1:19828`), 번들 MCP 서버(`mcp-server/`), Chrome 확장(`extension/`)이 붙는다. |
| 버전 | `package.json` 기준 0.6.12 |
| 코드 규모 | TS 비테스트 약 54,500줄(`src/`). Rust 약 35,100줄(`src-tauri/src/`). 가장 큰 파일은 `src/lib/ingest.ts` 3,806줄, `src-tauri/src/agent/runtime.rs` 5,816줄이다. |
| 테스트 | TS 테스트 파일 148개, 약 34,800줄, `it`/`test` 호출 약 1,900개. Rust `#[test]` 369개. 실제 LLM을 부르는 `*.real-llm.test.ts`가 10개 있다. |

[확인] 이 저장소는 "llm-wiki 패턴"을 앱 제품으로 만든 것이다.
[추정] 형식 규칙은 프롬프트가 먼저 지시하고, ingest 쓰기 경로의 TS 후처리가 다시 강제한다. 사례 2개: sanitize 주석(`ingest.ts:2071`)과 언어 검사 주석(`ingest.ts:1607`)이 프롬프트만으로는 형식이 지켜지지 않았다고 적는다. 다만 이 후처리는 ingest 경로에만 걸린다. agent·API·Save to Wiki 쓰기는 거치지 않는다 (#2).
[확인] README는 코드보다 뒤처져 있다. 어긋난 7곳은 #4, #6, #11, #12에서 짚고 #단점에 모은다.

## 한 바퀴 흐름

Ingest

1. Rust `notify` watcher가 프로젝트 전체를 재귀 감시한다 (`src-tauri/src/commands/file_sync.rs:273`). 이벤트를 놓쳐도 Linux 10초, 그 밖 60초 주기로 snapshot과 다시 대조한다 (`file_sync.rs:31`, `file_sync.rs:518`).
2. 변경은 `.llm-wiki/file-change-queue.json`에 쌓인다. 파일별 md5·크기·mtime은 `.llm-wiki/file-snapshot.json`에 남는다 (`file_sync.rs:19-20`, `file_sync.rs:1081`).
3. TS 쪽 `processFileChangeBatch`가 변경 묶음을 받는다 (`src/lib/project-file-sync.ts:243`). 같은 해시의 삭제+생성 한 쌍은 이동으로 보고 메타데이터만 옮긴다 (`project-file-sync.ts:269`). 삭제는 cascade 정리로 간다 (`project-file-sync.ts:389`). 생성·수정은 ingest queue에 넣는다 (`project-file-sync.ts:337`).
4. `src/lib/ingest-queue.ts`가 작업을 `.llm-wiki/ingest-queue.json`에 저장한다 (`ingest-queue.ts:98-115`). `processNext` → `startTask` → `runTask` → `autoIngest` 순서로 돈다 (`ingest-queue.ts:1147`, `1091`, `987`).
5. `autoIngest`는 소스별 lock을 잡는다 (`src/lib/ingest.ts:636-659`). 소스·`schema.md`·`purpose.md`·`wiki/index.md`·`wiki/overview.md`를 읽는다 (`ingest.ts:788`).
6. SHA-256 cache가 맞고 이전에 쓴 파일이 모두 남아 있으면 LLM을 건너뛴다 (`ingest.ts:825`, `src/lib/ingest-cache.ts:70-100`).
7. 이미지를 뽑고 vision LLM으로 caption을 단다 (`ingest.ts:919-1043`). 소스가 예산을 넘으면 의미 단위 chunk로 나눠 chunk별 분석과 global digest를 만든다 (`ingest.ts:1051`, `ingest.ts:3114`).
8. Step 1 분석 호출을 한다 (`ingest.ts:1073`). Step 2 생성 호출이 `---FILE: path---` 블록을 낸다 (`ingest.ts:1120`). 출력이 크면 REVIEW 전용 호출을 한 번 더 한다 (`ingest.ts:1220`).
9. 쓰기 단계는 프로젝트 lock 안에서 돈다 (`ingest.ts:1266`). `writeFileBlocks`가 블록마다 sanitize, 날짜 찍기, `sources` 정규화, schema 경로 교정, 언어 검사, 기존 페이지 merge를 한다 (`ingest.ts:2016-2218`).
10. 잘린 FILE 블록은 한 번 재생성한다 (`ingest.ts:1294`). `index.md`와 `log.md`는 코드가 결정적으로 갱신한다 (`ingest.ts:1395`, `ingest.ts:1413`). 요약 페이지가 없으면 분석문으로 fallback 요약을 쓴다 (`ingest.ts:1448`).
11. 완결성 검사를 통과해야 review 항목 등록, cache 저장, embedding이 이어진다 (`ingest.ts:1504-1590`). 실패하면 throw한다. queue는 한 작업을 최대 3번 시도한다(첫 시도 + 재시도 2번) (`ingest-queue.ts:938`, `ingest-queue.ts:1074-1083`).
12. queue가 비면 `sweepResolvedReviews`가 해결된 review를 규칙과 LLM으로 닫는다 (`ingest-queue.ts:964-985`, `src/lib/sweep-reviews.ts:342`).

Query

13. 채팅은 Rust agent runtime으로 간다 (`src/components/chat/chat-panel.tsx:987`, `chat-panel.tsx:1065`). 도구 목록은 `wiki.search`, `source.search`, `graph.search`, `web.search`, `wiki.write_page`, `shell.exec` 등이다 (`src-tauri/src/agent/tools.rs:433-640`).
14. `wiki.search`는 `search_project_inner`로 간다 (`src-tauri/src/commands/search.rs:327`). `wiki/*.md`만 token 점수로 훑는다 (`search.rs:350`). LanceDB vector 결과와 RRF(k=60)로 합친다 (`search.rs:497`). 결과의 15-30%를 한 단계 이웃으로 채운다. 이웃은 본문 wikilink와 frontmatter `related`로 잇는다 (`search.rs:541-555`, `search.rs:721`).
15. "Faithful" 모드에서는 `raw/sources/`를 직접 grep하는 `source.search`를 먼저 부른다 (`src-tauri/src/agent/runtime.rs:1396`, `tools.rs:2510`). wiki·graph·web 도구는 코드가 막는다 (`runtime.rs:3524-3533`).
16. "Save to Wiki"는 답을 `wiki/queries/`에 쓴다. frontmatter에 `sources`는 없다. 이어서 `index.md`의 `## Queries` 절과 `log.md`에 줄을 직접 붙인다. 그다음 queue를 거치지 않고 `autoIngest`를 바로 부른다 (`src/components/chat/chat-message.tsx:547-625`).

Lint

17. 구조 lint는 Web Worker에서 결정적으로 돈다. orphan, broken-link, no-outlinks만 찾는다 (`src/lib/lint-structural-core.ts:9-10`, `lint-structural-core.ts:102`).
18. 의미 lint는 모든 페이지의 앞 500자를 한 프롬프트에 넣고 LLM을 한 번 부른다 (`src/lib/lint.ts:205-356`). contradiction, stale, missing-page, suggestion을 찾는다.
19. 고치기는 사용자가 버튼을 눌러야 한다. wikilink 추가, 링크 대상 교체, stub 페이지 생성 세 가지다 (`src/components/lint/lint-view.tsx:268-296`, `src/lib/lint-fixes.ts`).

## 축별 분석

#### 1. 실행 형태

[확인] 데스크톱 앱이다. Tauri v2 위에 React UI와 Rust 백엔드가 있다 (`package.json`, `src-tauri/Cargo.toml`).
[확인] 같은 기능을 바깥에 여는 출구가 셋 있다. 로컬 HTTP API (`src-tauri/src/api_server.rs:358-385`), 그 API를 감싼 MCP 서버 (`mcp-server/src/index.ts`), Chrome 확장 (`extension/`)이다.
[확인] README에 없는 `POST /projects/{id}/pages/write` 경로가 API에 있다 (`api_server.rs:380`). 번들 MCP 서버가 이 경로를 쓴다 (`mcp-server/src/api-client.ts:369`). 이 경로는 읽기 API를 무인증으로 열어도 token을 요구한다 (`api_server.rs:427-439`). 쓰기는 agent `wiki.write_page`와 같은 함수로 간다. 기본은 생성 전용이다 (`api_server.rs:1798-1836`, `tools.rs:671`).
[확인] Karpathy 원문은 "복사해 붙이는 패턴 문서"였다. 이 repo는 그것을 사람이 프롬프트를 거의 보지 않는 제품으로 바꿨다 (`README.md:88-96`).

#### 2. 규칙의 위치

[확인] 규칙은 세 겹에 있다. 프롬프트, `schema.md`, 그리고 쓰기 직전의 TS 후처리다.
- 프롬프트: 생성 프롬프트가 frontmatter 형식, `sources` 필수, 출력 블록 문법, 주제 경계 보존을 지시한다 (`src/lib/ingest.ts:2391-2560`). 엔티티 페이지 기준("Page-worthy: yes")도 프롬프트에 있다 (`ingest.ts:2304-2326`).
- `schema.md`: 프로젝트 루트의 사람 편집 문서다. "Page Types" 표의 `type | 디렉터리` 행을 코드가 파싱한다 (`src/lib/wiki-schema.ts:30-66`).
- 코드 강제(write path gate): `writeFileBlocks`가 블록마다 다음을 한다 (`ingest.ts:2016-2218`).
  - 경로 안전 검사 `isSafeIngestPath` (`ingest.ts:447`). 블록 파싱 단계에서 건다 (`ingest.ts:595`). `wiki/`로 시작하지 않는 경로는 거부한다 (`ingest.ts:460-461`). 그래서 ingest 출력은 `raw/sources/`에 닿지 못한다.
  - `index.md`·`overview.md`는 모델이 쓰면 버린다 (`ingest.ts:2059-2064`).
  - frontmatter sanitize (`ingest.ts:2074`, `src/lib/ingest-sanitize.ts`).
  - `created`/`updated`를 오늘 날짜로 덮어쓴다 (`ingest.ts:2075-2079`).
  - `sources`에 현재 소스를 강제로 넣는다 (`ingest.ts:1772-1800`, `ingest.ts:2081`). LLM이 적은 다른 항목은 형식만 거른다. 그 파일이 실제로 있는지는 보지 않는다 (`ingest.ts:1760-1770`).
  - schema 표와 type이 안 맞으면 디렉터리를 옮기거나 버린다 (`ingest.ts:2093-2125`, `wiki-schema.ts:68-130`). type이 비었거나 표에 없는 type이면 그대로 통과한다 (`wiki-schema.ts:76-96`).
  - 목표 언어와 본문 언어가 다르면 페이지를 버린다. entity·source 페이지와 log만 빠지고, concept·query·synthesis·comparison·schema 정의 type이 모두 대상이다 (`ingest.ts:2120-2137`).
  - 여기서 버린 블록은 경고만 남긴다. ingest 실패로 치지 않는다. cache도 그대로 저장된다 (`ingest.ts:2038-2046`, `ingest.ts:1543-1555`).
- merge 후처리: `type`/`title`/`created`는 기존 값으로 되돌린다. `sources`/`tags`/`related`는 합집합으로 강제한다 (`src/lib/page-merge.ts:31`, `page-merge.ts:45`, `page-merge.ts:186-202`). 잠금 필드 복원은 merge 성공과 단일 소스 교체 때만 한다. fallback 경로는 복원하지 않는다 (`page-merge.ts:150-180`).

[확인] 이 gate는 ingest의 `writeFileBlocks`에만 걸린다. 다른 쓰기 경로는 거치지 않는다.
- agent `wiki.write_page`와 API `pages/write`는 경로만 검사한다(`wiki/` 아래 `.md`, 숨김 경로 금지). frontmatter·`sources`·schema 경로·언어 검사가 없다. `allowOverwrite=true`면 `wiki/index.md`도 덮어쓸 수 있다 (`tools.rs:2723-2748`, `tools.rs:687-760`).
- Save to Wiki는 frontmatter를 손으로 조립해 바로 쓴다. `index.md`·`log.md`에도 직접 줄을 붙인다 (`chat-message.tsx:567-611`).
- lint 수정 버튼도 `writeFile`로 바로 쓴다 (`lint-view.tsx:265-296`).

[확인] pre-commit이나 git hook은 없다. Cargo 의존성에 git 라이브러리도 없다 (`src-tauri/Cargo.toml`).
[추정] 코드 주석이 왜 코드로 옮겼는지 밝힌다. 사례 2개: sanitize 이전에는 "~45% of generated entity pages went to disk with unparseable frontmatter" (`ingest.ts:2071`). 언어 이탈은 "observed ~once in 5 real-LLM runs" (`ingest.ts:1607`). 프롬프트만으로는 형식이 지켜지지 않아서 코드 gate가 늘어난 것으로 보인다.

#### 3. 저장 구조

[확인] 디렉터리는 다음과 같다 (`README.md:476-494`, `src-tauri/src/commands/project.rs:180-195`).
- `purpose.md`, `schema.md` — 프로젝트 루트. 사람이 쓴다.
- `raw/sources/` — 원본. `.cache/`에 파싱 결과 텍스트가 붙는다 (`ingest.ts:754-757`).
- `wiki/` — `index.md`, `log.md`, `overview.md`, `entities/`, `concepts/`, `sources/`, `queries/`, `synthesis/`, `comparisons/`, `media/<source-slug>/`.
- `.llm-wiki/` — 앱 상태.

[확인] 페이지 type은 entity, concept, source, query, comparison, synthesis, overview다 (`src/lib/templates.ts:11-17`). 템플릿별로 methodology, findings, thesis 같은 디렉터리가 더 붙는다 (`templates.ts:66-80`).
[확인] frontmatter 필드는 `type`, `title`, `created`, `updated`, `tags`, `related`, `sources`다 (`ingest.ts:2452-2460`). `related`는 slug 목록이고 그래프 edge로도 쓰인다 (`src/lib/graph-relevance.ts:247`).
[확인] 파생 상태 파일은 `.llm-wiki/` 아래에 있다.

| 파일 | 역할 | 근거 |
|---|---|---|
| `ingest-queue.json` | ingest 작업 queue (done 제외) | `ingest-queue.ts:98-115` |
| `ingest-cache.json` | 소스 SHA-256 → 쓴 파일 목록 | `ingest-cache.ts:30` |
| `file-snapshot.json` | 감시 대상 파일의 md5·크기·mtime | `file_sync.rs:19` |
| `file-change-queue.json` | 파일 변경 작업 queue | `file_sync.rs:20` |
| `ingest-progress/…`(checkpoint) | 생성 단계와 긴 소스 chunk 분석의 재개 지점 | `ingest.ts:2918-3040` |
| `ingest-warnings.log` | 버려진 블록과 경고 | `ingest.ts:696-714` |
| `page-history/` | merge fallback·단일 소스 교체 직전 백업 | `ingest.ts:3363-3373`, `page-merge.ts:122` |
| `review.json`, `lint.json`, `chats/*.json` | review 큐, lint 결과, 대화 | `src/lib/persist.ts:17-124` |
| `image-caption-cache.json` | 이미지 해시 → caption | `ingest.ts:957` 주석 |
| `lancedb/` | vector 저장소 (`wiki_chunks_v2` 표) | `src-tauri/src/commands/vectorstore.rs:49`, `vectorstore.rs:66` |
| `history-settings.json` + 버전 저장소 | 파일 버전 이력 (기본 꺼짐) | `src-tauri/src/commands/file_history.rs:43-47` |

#### 4. Ingest

- 사람 참여: [확인] 사실상 없다. 대화형 ingest 진입점 `startIngest`는 호출하는 곳이 없다 (`ingest.ts:3503`). `sources-view.tsx:359-368` 주석이 대화형 경로를 걷어 낸 이유를 적는다. 사람은 끝난 뒤 review 큐에서만 관여한다.
- 증분 추적: [확인] 두 층이다. 파일 층은 md5 snapshot이다 (`file_sync.rs:1081`). 내용 층은 파싱된 텍스트의 SHA-256 cache다 (`ingest-cache.ts:70-100`). cache는 이전에 쓴 파일이 하나라도 사라지면 무효가 된다.
- queue·crash 복구: [확인] 앱이 다시 열리면 `processing` 상태 작업을 `pending`으로 되돌리고 자동으로 재개한다 (`ingest-queue.ts:866-935`). 일반 실패는 최대 3번 시도한 뒤 `failed`로 둔다. `retryCount >= 3`이면 멈추므로 재시도는 2번이다 (`ingest-queue.ts:938`, `ingest-queue.ts:1075-1081`). README의 "auto-retry up to 3 times" (`README.md:127`)와 하나 어긋난다. 429·quota 오류는 queue 전체를 멈추고 15분 뒤 재개한다 (`ingest-queue.ts:939`, `ingest-queue.ts:1054-1072`). 생성 도중 끊기면 이미 쓴 경로를 checkpoint에 남긴다. 재시도 때 LLM에게 그 경로를 다시 내지 말라고 지시한다 (`ingest.ts:1155-1162`, `ingest.ts:1494-1502`).
- queue 병렬성: [확인] README는 "serial processing prevents concurrent LLM calls"라고 쓴다 (`README.md:127`). 코드는 worker 수를 1-64로 설정할 수 있다 (`ingest-queue.ts:87`, `src/lib/concurrency-limits.ts:1-2`). 기본값은 1이다 (`src/lib/source-watch-defaults.json`). 여러 worker여도 쓰기 단계는 시작 순서대로 한 줄로 선다 (`src/lib/ingest-commit-coordinator.ts:12-40`).
- 자동 감시: [확인] 기본으로 켜져 있다. `autoIngest: true`가 기본값이다 (`source-watch-defaults.json`). 감시 확장자, 제외 디렉터리, 제외 glob, 100MB 상한이 같은 JSON에 있다. 기본 감시 확장자에 epub·mobi는 없다. 32MB를 넘는 파일은 md5를 계산하지 않아 해시 이동 감지에서 빠진다 (`file_sync.rs:23`, `file_sync.rs:1046-1050`). 앱이 직접 쓴 파일은 4초 동안 감시에서 뺀다 (`file_sync.rs:25`, `file_sync.rs:446`).
- 멀티포맷: [확인] PDF(pdfium, 선택적 MinerU), DOCX(docx-rs), XLSX(calamine), PPTX, EPUB/MOBI를 Rust에서 변환한다 (`src-tauri/Cargo.toml:33-43`, `src-tauri/src/commands/fs.rs`, `src-tauri/src/commands/ebook.rs`). MinerU가 실패하면 내장 파서로 돌아간다 (`ingest.ts:776-782`).
- 소스 하나가 건드리는 페이지 수: [확인] 코드에 상한이 없다. 생성 프롬프트는 요약 1장, "Page-worthy" 엔티티, concept, log 항목을 요구한다 (`ingest.ts:2428-2434`). 확인하지 못한 것: 실제로 소스 하나가 몇 페이지를 건드리는지, 그 수가 모델이나 소스 길이에 따라 달라지는지 모른다. repo 안에 실행 기록이 없다. 길이가 다른 소스 몇 개를 모델을 바꿔 가며 ingest하고, 작업마다 `wiki/` 아래 새로 생기거나 바뀐 파일 수를 세면 알 수 있다.

#### 5. 근거 추적 단위

[확인] 페이지 단위 출처다. frontmatter `sources: [...]`에 원본 경로(`raw/sources/` 기준 상대 경로)가 들어간다 (`ingest.ts:1772-1800`, `src/lib/source-identity.ts:8-24`).
[확인] 문장·claim 단위 추적은 없다. 원문 글자 일치 검사도 없다. merge 프롬프트는 "attribute a claim to a real source filename only when the supporting file is unambiguous"라고만 지시한다 (`ingest.ts:3338`).
[확인] 채팅 답은 페이지 번호로 인용한다. 인용된 페이지 목록이 메시지에 저장된다 (`README.md:226-229`, `README.md:242-243`).
[확인] 소스를 지우면 그 소스만 가진 페이지는 지운다. 다른 페이지의 wikilink와 `related`에서도 그 페이지를 걷어 낸다 (`source-lifecycle.ts:546-565`, `src/lib/wiki-page-delete.ts:210-240`).
[추정] 공유 페이지는 `sources`에서 그 항목만 뺀다 (`src/lib/source-lifecycle.ts:550`). 본문에서 그 소스가 기여한 문장은 남는다. 그래서 출처 목록과 본문이 어긋날 수 있다. 사례 1개: 이 함수에 본문을 다시 쓰는 단계가 없다.
[추정] 반대 방향의 어긋남도 생긴다. merge fallback은 새 본문만 남기고 `sources`는 합집합으로 둔다 (#8). 그러면 `sources`에 있는 소스의 문장이 본문에서 빠진다. 사례 1개: `page-merge.ts:150-180`의 fallback이 `arrayMerged`(새 본문 + 배열 합집합)를 돌려준다.

#### 6. Link

[확인] wikilink는 LLM이 본문에 건다 (`ingest.ts:2480`). `related` frontmatter도 LLM이 채운다.
[확인] backlink와 그래프는 코드가 매번 파일을 읽어 결정적으로 만든다. 저장된 그래프 파일은 없다 (`src/lib/graph-relevance.ts:202-306`, `src/lib/wiki-graph.ts:170`).
[확인] 4-signal 가중치는 README 표와 같다. direct link 3.0, source overlap 4.0, Adamic-Adar 1.5, type affinity 1.0이다 (`graph-relevance.ts:33-38`, `graph-relevance.ts:308-348`).
[확인] 이 4-signal 점수는 그래프 화면에서만 쓰인다. edge 굵기와 Louvain community 가중치다 (`wiki-graph.ts:311`, `wiki-graph-analysis.ts:30`). `buildWikiGraph`를 부르는 곳은 `graph-view.tsx`뿐이다. 검색은 Rust 쪽에서 wikilink·`related` 한 단계 이웃만 쓴다. 가중치 없이 seed 순위의 역수로 점수를 매긴다 (`search.rs:541-620`). README의 "4-signal relevance model finds related pages"와 "2-hop traversal with decay" (`README.md:216-219`)에 해당하는 코드를 찾지 못했다. `api_server.rs:1932`의 API 설명도 "one-hop knowledge-graph candidates"라고 쓴다.
[확인] Louvain은 wikilink edge에 relevance 가중치를 얹어 `resolution: 1`로 돈다 (`src/lib/wiki-graph-analysis.ts:17-35`).
[확인] README의 "cohesion < 0.15" 경고 (`README.md:168`, `README.md:187`)도 코드와 다르다. cohesion 값은 계산하지만 0.15로 경고하는 코드는 없다. 지금은 평균 내부 차수 2 미만을 sparse로 본다 (`src/lib/graph-insights.ts:160-163`).
[확인] 자동 link 보강 모듈 `enrichWithWikilinks`가 있다. LLM은 `(term → target)` JSON만 내고 치환은 코드가 한다 (`src/lib/enrich-wikilinks.ts:1-26`). 이 함수를 부르는 곳은 테스트 밖에 없다. 제품 경로에 연결되지 않은 죽은 코드다.

#### 7. Lint

[확인] 결정적 lint와 LLM lint가 분리되어 있다.
- 결정적: orphan, broken-link, no-outlinks (`lint-structural-core.ts:9-10`). 끊긴 링크에는 Levenshtein 유사도로 대체 대상을 제안한다 (`lint-structural-core.ts:49-78`).
- LLM: contradiction, stale, missing-page, suggestion (`lint.ts:277-283`). 이미 있는 페이지를 missing-page로 낸 결과는 코드가 버린다 (`lint.ts:330`).

[확인] 의미 lint 입력은 페이지마다 앞 500자다 (`lint.ts:244`). 이 500자는 frontmatter부터 센다. 그래서 본문은 더 적게 들어간다. 모든 페이지를 한 프롬프트에 넣는다 (`lint.ts:262-290`). [추정] 페이지가 수백 장을 넘으면 컨텍스트를 넘거나 뒤쪽 페이지 모순을 놓친다. 사례 1개: 이 함수에 batch 분할이나 예산 계산이 없다.
[확인] 자동 수정은 사용자가 누를 때만 돈다. 범위는 wikilink 추가, 링크 대상 교체, stub 생성이다 (`lint-view.tsx:268-296`, `lint-view.tsx:404-430`).
[확인] lint가 쓰기를 막는 commit gate는 없다. ingest 쓰기 경로의 gate는 #2의 sanitize·routing·언어 검사뿐이다.

#### 8. stale·모순 처리

[확인] 같은 경로에 페이지가 있으면 LLM merge를 한다 (`ingest.ts:2183`, `page-merge.ts:100-212`). merge 결과 본문이 기존·신규 중 긴 쪽의 70%보다 짧으면 버리고 fallback한다 (`page-merge.ts:54`, `page-merge.ts:170-181`). LLM 오류나 frontmatter 없는 출력도 fallback으로 간다 (`page-merge.ts:150-167`).
[확인] fallback이 쓰는 것은 새 본문 + 배열 필드 합집합이다. 기존 본문은 디스크 페이지에서 사라지고 백업에만 남는다 (`page-merge.ts:22-24`, `page-merge.ts:155`, `page-merge.ts:179`). 그래서 70% 검사는 "merge가 내용을 줄였다"를 잡지만, 걸리면 다른 소스의 기여를 통째로 잃는 쪽으로 떨어진다.
[확인] `.llm-wiki/page-history/` 백업은 fallback과 단일 소스 교체 때 한다 (`page-merge.ts:122`, `page-merge.ts:154-178`). 정상 merge 때는 백업하지 않는다.
[확인] 페이지의 `sources`가 지금 소스 하나뿐이면 merge 없이 새 본문으로 덮어쓴다 (`ingest.ts:2176-2182`, `page-merge.ts:121-134`). 주석은 그 이유를 "Merging the old body back into the new generation kept retracted wording alive indefinitely"라고 쓴다.
[확인] 모순은 세 곳에서 다룬다. 분석 프롬프트의 "Contradictions & Tensions" 절 (`ingest.ts:2366`), 생성 출력의 `REVIEW: contradiction` 블록 (`ingest.ts:2491-2498`), merge 프롬프트의 "keep them separated" 지시 (`ingest.ts:3338`)다.
[확인] supersede 관계, `stale_after`, drift 감지는 없다. stale은 의미 lint의 한 type으로만 있다 (`lint.ts:279`).
[확인] 소스 파일이 바뀌면 watcher가 다시 ingest한다. 이것이 사실상의 갱신 경로다 (`project-file-sync.ts:337-381`).

#### 9. 사람 개입

[확인] 자율에 가깝다. 쓰기마다 승인하는 단계가 없다.
[확인] review 큐가 비동기로 붙는다. LLM이 REVIEW 블록을 내면 `review.json`에 쌓인다 (`ingest.ts:1531-1541`). 선택지는 "Create Page"와 "Skip"로 고정된다 (`ingest.ts:2502-2510`). review id는 type+title 해시라 재-ingest 때 해결 상태가 유지된다 (`src/stores/review-store.ts:34-57`).
[확인] queue가 비면 review를 자동으로 닫는다. 규칙 단계는 missing-page와 duplicate만 닫는다. 남은 항목은 type을 가리지 않고 모두 LLM 판정에 넘긴다. contradiction을 남겨 두라는 것은 프롬프트 지시("default to keeping them pending")뿐이다. LLM이 contradiction id를 돌려주면 코드는 그대로 닫는다 (`sweep-reviews.ts:370-397`, `sweep-reviews.ts:417`, `sweep-reviews.ts:229`, `sweep-reviews.ts:266-275`). 파일 머리 주석의 "preserves contradiction / suggestion / confirm"은 코드가 보장하지 않는다.
[확인] Deep Research 확인 창은 그래프 화면의 지식 공백에서 시작할 때만 뜬다 (`graph-view.tsx:840-870`). review 큐의 Deep Research 버튼과 일괄 실행은 확인 없이 바로 queue에 넣는다 (`review-view.tsx:94-114`, `review-view.tsx:366-385`). README는 진입점을 구분하지 않고 "editable confirmation dialog"를 적는다 (`README.md:193`, `README.md:297`).
[확인] agent의 shell 실행은 정확한 명령 단위 승인이 필요하다 (`src-tauri/src/agent/permissions.rs:32-35`, `runtime.rs:467-505`).
[확인] Obsidian vault로 같이 열 수 있다 (`project.rs:197-200`). 앱 밖 편집은 file history에 기록되지 않는다. `record_file_version`을 부르는 곳은 앱의 쓰기 명령과 agent 쓰기뿐이고 watcher에는 없다 (`fs.rs:1253-1260`, `tools.rs:732`). 앱 밖 편집본은 다음 앱 쓰기 직전의 "baseline" 기록으로만 남는다.

#### 10. 동시성·안전

- lock: [확인] 프로젝트 경로 단위 promise-chain mutex가 있다 (`src/lib/project-mutex.ts:24-60`). 소스별 lock과 프로젝트 쓰기 lock 두 단계다 (`ingest.ts:647`, `ingest.ts:734`). JS 메모리 안의 lock이라 Obsidian 같은 앱 밖 쓰기와는 맞물리지 않는다.
- [추정] Save to Wiki의 `index.md`·`log.md` 직접 쓰기는 이 lock을 잡지 않는다. ingest의 index 갱신과 겹치면 한쪽 줄이 사라질 수 있다. 사례 1개: `chat-message.tsx:578-611`이 lock 없이 read → write한다.
- transaction: [확인] 없다. 한 ingest가 여러 파일을 쓰다 멈추면 앞 파일은 남는다. 코드는 이것을 받아들이고 checkpoint와 재시도 merge로 수렴시킨다 (`ingest-queue.ts:1014-1020`, `ingest.ts:1474-1502`).
- 원자적 쓰기: [확인] ingest가 쓰는 `writeFile`은 Rust `fs::write`다. temp+rename이 아니다 (`src/commands/fs.ts:22-24`, `src-tauri/src/commands/fs.rs:1242-1263`). temp+rename인 `write_file_atomic`은 lint 설정 같은 일부 JSON만 쓴다 (`src/lib/lint-config.ts:47`). agent의 `wiki.write_page`만 원자적 교체 뒤 다시 읽어 검증한다 (`tools.rs:687-760`).
- [확인] queue 파일 저장도 `writeFile`이고 실패를 삼킨다 (`ingest-queue.ts:117-134`). 읽다 JSON이 깨지면 빈 queue로 시작한다 (`ingest-queue.ts:136-152`). [추정] 저장 도중 앱이 죽으면 대기 작업이 조용히 사라질 수 있다. 사례 1개: `loadQueue`의 `catch { return [] }`.
- snapshot·undo: [확인] 파일 버전 이력이 Rust에 있다. 쓰기 전후를 기록한다 (`file_history.rs:234`). 기본값은 꺼져 있다 (`file_history.rs:43-47`). 켜도 파일당 최대 30개, 전체 128MB까지다 (`file_history.rs:9-13`).
- 도구 허용 목록: [확인] agent capability enum이 있다 (`permissions.rs:5-15`). API 기본 정책은 wiki 쓰기를 포함해 거의 전부 허용한다 (`permissions.rs:23-39`). `wiki.write_page`는 기본이 생성 전용이다. 덮어쓰려면 `allowOverwrite=true`가 필요하다 (`tools.rs:713`).
- git: [확인] 쓰지 않는다.

#### 11. Query·검색

[확인] hybrid다. token 점수(제목 가중, 구절 가산) + LanceDB chunk vector + RRF + 한 단계 그래프 확장이다 (`search.rs:12-26`, `search.rs:327-495`).
[확인] vector는 기본 꺼짐이다 (`README.md:232`). 켜면 ingest 끝에 페이지를 chunk로 나눠 embedding한다 (`ingest.ts:1562-1585`, `src/lib/embedding.ts:1-20`). `index.md`·`log.md`·`overview.md`는 embedding하지 않는다 (`src-tauri/src/commands/page_embedding.rs:122`).
[확인] 검색 대상은 `wiki/`뿐이다 (`search.rs:350`). 원본은 agent의 `source.search`가 따로 훑는다 (`tools.rs:2510-2560`).
[확인] "Faithful" 모드는 원본 발췌만 근거로 쓴다 (`src-tauri/src/agent/types.rs:20-29`). 코드가 경계를 강제한다. `wiki.search`·`wiki.read_page`·`graph.search`·`web.search`를 호출 단계에서 거부한다. 프롬프트 문맥에서 `overview`와 `schema`를 뺀다 (`runtime.rs:3524-3533`, `runtime.rs:2783-2796`). 모델이 배경 지식을 섞지 않게 하는 것은 프롬프트 지시다 (`runtime.rs:2922`).
[확인] 답을 wiki에 되저장한다. "Save to Wiki"가 `wiki/queries/`에 쓰고 곧바로 ingest한다 (`chat-message.tsx:565-625`).
[확인] Deep Research 결과는 더 이상 ingest하지 않는다. 주석이 "Feeding it back through source ingest creates a second summary page and recursively produces low-value review suggestions"라고 이유를 밝힌다 (`src/lib/deep-research.ts:708-711`). README는 아직 "Auto-ingest — research results automatically processed"라고 쓴다 (`README.md:300`).
[확인] README의 컨텍스트 배분 "60% wiki pages, 20% chat history, 5% index, 15% system" (`README.md:223`)에 해당하는 코드가 채팅 경로에 없다. `context-budget.ts`에 페이지 50%, index 5%, 응답 예약 15% 상수가 있다 (`src/lib/context-budget.ts:55-58`). 그러나 `pageBudget`·`indexBudget`을 읽는 비테스트 코드는 없다. 실제로 쓰이는 것은 응답 예약과 전체 크기뿐이고, ingest와 Anthropic `max_tokens` 계산에 쓰인다 (`llm-providers.ts:908`, `ingest.ts:2574-2757`). 채팅은 Rust agent 루프가 도구 호출 횟수 예산으로 문맥을 모은다 (`runtime.rs:1356-1358`, `runtime.rs:2798-2830`).

#### 12. index·log 관리

[확인] index는 코드가 결정적으로 갱신한다. 모델이 쓴 `index.md`는 버린다 (`ingest.ts:2059-2064`). 새 페이지는 `## Recently Updated` 절 맨 위에 붙는다 (`ingest.ts:1703-1758`).
[확인] 이 절은 200항목으로 잘린다 (`ingest.ts:1756`). 이미 index 어딘가에 있는 페이지는 다시 붙이지 않는다. 그래서 기존 페이지를 고쳐도 위로 올라가지 않는다 (`ingest.ts:1714-1722`). 새 프로젝트의 index는 빈 type 절만 있다. 그래서 재생성 명령을 돌리기 전에는 모든 ingest 페이지가 이 절에만 쌓인다 (`project.rs:154-167`).
[추정] 재생성을 돌리지 않으면 201번째 이후로 밀려난 페이지는 index에서 사라진다. 그러면 다음 ingest 때 LLM이 그 페이지를 모르고 같은 주제의 새 페이지를 만들 수 있다. 사례 1개: 생성 프롬프트에 기존 페이지 정보로 들어가는 것은 index 전문뿐이다 (`ingest.ts:2519`).
[확인] 전체 재생성 명령이 따로 있다. 설정의 유지보수 화면에서 사람이 누른다. frontmatter type별로 묶어 `index.md`를 temp+rename으로 다시 쓴다 (`src-tauri/src/commands/project_maintenance.rs:294-350`, `maintenance-section.tsx:201`). 재생성 뒤에는 모든 페이지가 type 절에 들어가므로 200항목 상한이 적용되지 않는다. 대신 index 전체가 잘리지 않고 분석·생성 프롬프트에 들어간다. index를 줄이는 코드는 없다 (`ingest.ts:788`, `ingest.ts:1045-1046`, `ingest.ts:2384`, `ingest.ts:2519`).
[확인] log는 LLM이 낸 항목을 붙인다. 없으면 코드가 `## [YYYY-MM-DD] ingest | <source>`를 붙인다 (`ingest.ts:2147-2150`, `ingest.ts:685-694`, `ingest.ts:1406-1420`). 소스 삭제도 log에 남는다 (`source-lifecycle.ts:691`).
[확인] 형식이 셋으로 갈린다. ingest는 `## [date] ingest | X`다. Save to Wiki는 `- date: Saved query page`다 (`chat-message.tsx:610`). 기본 schema 문서는 "reverse chronological"이라고 적는다 (`templates.ts:51-56`). 코드는 끝에 붙인다.
[확인] `overview.md`는 프로젝트를 만들 때 한 번 생긴다 (`project.rs:182-194`). 그 뒤로 갱신하는 코드를 찾지 못했다. 모델이 쓴 overview는 버린다 (`ingest.ts:1649-1652`). 그런데 생성 프롬프트는 아직 "Current Overview (update this to reflect the new source)"라고 지시한다 (`ingest.ts:2520`). index도 같다. "Do not generate wiki/index.md"라고 하면서 "Current Wiki Index (preserve all existing entries, add new ones)"라고 지시한다 (`ingest.ts:2436`, `ingest.ts:2519`). README의 "overview.md auto-update — regenerated on every ingest" (`README.md:133`)는 지금 코드와 맞지 않는다.

#### 13. 포맷 표준

[확인] OKF를 언급하는 곳이 repo에 없다.
[확인] OKF v0.2와 겹치는 부분은 `type`, `title`, `tags`, `sources`라는 이름과 `index.md`·`log.md` 예약 파일이다 (`lab/repos/GoogleCloudPlatform_knowledge-catalog/okf/SPEC.md` §4.1, §8, §9).
[확인] 어긋나는 부분은 다음과 같다.
- `sources`가 문자열 목록이다. OKF는 `resource`를 가진 객체 목록이다 (SPEC §5.1).
- `description`, `generated`, `verified`, `status`, `stale_after`가 없다 (SPEC §4.1, §5.2-5.5).
- 링크가 `[[wikilink]]`다. OKF는 표준 markdown 링크를 쓴다 (SPEC §6.1).
- log가 오래된 것부터 붙는다. OKF는 최신이 먼저다 (SPEC §9).
- index 항목은 `- [[target]] — title`이다. OKF는 `* [Title](url) - description`이다 (SPEC §8).

[추정] 준수 정도는 낮다. 다만 frontmatter가 단순해서 변환기는 쉽게 쓸 수 있다. 사례 1개: 필드 7개가 모두 스칼라나 문자열 배열이다.

#### 14. 규모·비용

[확인] 운영 규모를 밝힌 문장이 README에 없다.
[확인] 코드에 박힌 상한은 있다. 검색은 wiki 파일 10,000개에서 멈춘다 (`search.rs:23`). Graph API는 한 번에 1,000 노드다 (`api_server.rs:2475`, `README.md:452`). 소스는 100MB 이하만 감시한다 (`source-watch-defaults.json`).
[확인] 소스 1개 ingest의 LLM 호출 수는 다음과 같다.
- 분석 1회. 긴 소스는 chunk 수만큼 (`ingest.ts:3114-3200`).
- 생성 1회 (`ingest.ts:1120`).
- review 전용 0-1회. 출력이 10,000자 이상이거나 FILE 블록 4개 이상일 때다 (`ingest.ts:65-66`, `ingest.ts:2298-2302`).
- 잘린 블록 복구 0-1회 (`ingest.ts:1294`).
- 기존 페이지와 경로가 겹칠 때마다 merge 1회 (`ingest.ts:2183`).
- 이미지마다 caption 1회. 해시 cache가 있다 (`ingest.ts:957`).
- queue가 빌 때 review sweep 0-5회. 남은 review를 40개씩 묶어 최대 5묶음까지 LLM에 보낸다 (`ingest-queue.ts:964`, `sweep-reviews.ts:182-184`).

[확인] 비용을 줄이는 장치는 SHA-256 cache, caption 해시 cache, 생성 checkpoint, 긴 소스 chunk checkpoint다.
[확인] 컨텍스트 사용 방식: 생성 프롬프트에 schema, purpose, index 전문, overview, 소스(또는 digest)가 들어간다 (`ingest.ts:2391-2520`). 기존 페이지 본문은 들어가지 않는다. 기존 본문은 merge 단계에서 페이지별로 따로 읽힌다.
[확인] README의 "overall recall improved from 58.2% to 71.4%" (`README.md:232`)를 뒷받침하는 benchmark 스크립트나 데이터를 repo에서 찾지 못했다. 근거 없는 주장으로 둔다.

#### 15. frosk1 비판 7가지에 대한 대응

| 비판 | 대응 | 근거 |
|---|---|---|
| 오류 누적 | [확인] 부분 대응. 단일 소스 페이지는 재-ingest 때 새 본문으로 교체한다. 여러 소스 페이지는 LLM merge를 거듭하므로 오류가 계속 실린다. merge가 70% 검사에 걸리면 반대로 다른 소스의 기여가 본문에서 빠진다. [확인] Save to Wiki가 LLM 답을 다시 ingest해서 소스처럼 다룬다. Deep Research는 같은 이유로 이 고리를 끊었는데 Save to Wiki는 남아 있다. | `page-merge.ts:121-134`, `page-merge.ts:170-180`, `chat-message.tsx:619-625`, `deep-research.ts:708-711` |
| 부분 문맥 | [확인] 부분 대응. 긴 소스는 chunk 분석 + global digest로 끝까지 읽는다. 기존 wiki는 index만 본다. 재생성 전에는 index의 최근 절이 200항목으로 잘린다. | `ingest.ts:3114-3256`, `ingest.ts:1756` |
| 요약 손실 | [확인] 부분 대응. 프롬프트가 SQL DDL·표·API 시그니처를 원문 그대로 옮기라고 지시한다. merge는 70% 길이 하한을 둔다. 원본 파싱 결과를 `raw/sources/.cache/`에 남긴다. | `ingest.ts:2360`, `ingest.ts:2487`, `page-merge.ts:54` |
| 가짜 source of truth | [확인] 대응한다. 원본을 지우지 않는다. agent에 원본 검색 도구가 있다. "Faithful" 모드는 원본 발췌만 근거로 쓴다. | `tools.rs:2510`, `runtime.rs:1396`, `types.rs:26-28` |
| 환각 병합 | [확인] 프롬프트와 코드 둘 다로 대응한다. 프롬프트는 주제 경계 보존과 "When in doubt … prefer keeping them separate"를 지시한다. 코드는 merge가 새로 지어낸 example.com URL을 지운다. `type`/`title`/`created`를 잠근다. 중복 엔티티 병합은 LLM이 후보를 내고 사람이 고른다. | `ingest.ts:3328-3360`, `page-merge.ts:186-202`, `page-merge.ts:245-300`, `src/lib/dedup.ts:1-29` |
| 운영 복잡도 | [확인] 앱이 떠안는다. 사용자는 설정 화면만 본다. 대신 코드가 약 9만 줄이다. queue·snapshot·checkpoint·cache 상태 파일이 10개를 넘는다. | #한눈에, #3 |
| ingest 비용 | [확인] cache와 checkpoint로 재실행 비용을 줄인다. 첫 ingest 비용을 잰 숫자는 없다. 기본 worker 1개다. 429 오류 때 15분 쉰다. | `ingest-cache.ts`, `ingest-queue.ts:939` |

[참고] 원본 비판 파일에는 8번째로 staleness가 있다. 이에 대한 대응은 #8에 적었다.

#### 16. 성숙도·차용 가능성

[확인] 테스트가 많다. TS 약 1,900건, Rust 369건이다. property 테스트용 `fast-check`가 devDependency에 있다 (`package.json`). 실제 LLM을 부르는 시나리오 테스트가 따로 있다 (`src/test-helpers/scenarios/`, `src/lib/*.real-llm.test.ts`).
[확인] CI는 테스트를 돌리지 않는다. `vite build`, MCP 빌드, `cargo build`만 한다 (`.github/workflows/ci.yml:50-62`).
[확인] 의존성이 무겁다. npm 런타임 의존성 40여 개(Milkdown, sigma, graphology, mermaid, katex, pdfjs)와 Rust 의존성 34개(lancedb, pdfium-render, notify, tiny_http, calamine, docx-rs)다 (`package.json`, `src-tauri/Cargo.toml:25-70`).
[확인] 라이선스가 GPL-3.0이다. 코드를 내 repo에 옮기면 내 repo도 GPL이 된다. 그래서 코드는 가져오지 않고 설계만 참고한다.
[추정] 활발하게 손보고 있다. 사례 3개: README가 코드보다 뒤처진 곳이 7군데다(#6 2곳, #11 2곳, #12 1곳, #4 2곳). `changelog.ts`가 756줄이다. 코드 주석에 issue 번호(#537)가 붙어 있다 (`lint.ts:235`).

## 장점

- [확인] ingest 경로에는 LLM 출력을 믿지 않는 write path gate가 촘촘하다. sanitize, 날짜 덮어쓰기, `sources` 강제, schema 경로 교정, 언어 검사, aggregate 파일 차단이 한 함수에 모여 있다 (`ingest.ts:2016-2218`). 다만 agent·API·Save to Wiki·lint 수정 쓰기는 이 gate를 거치지 않는다 (#2).
- [확인] 생성 단계의 부분 성공을 성공으로 치지 않는다. 생성 오류·잘림·쓰기 실패가 하나라도 있으면 cache를 저장하지 않고 throw한다 (`ingest.ts:1474-1559`). 그 뒤 checkpoint로 남은 페이지만 다시 생성한다. 단, gate가 버린 블록(언어·schema·경로)은 실패로 치지 않는다. 그 페이지는 소스가 바뀔 때까지 다시 생성되지 않는다 (`ingest.ts:2038-2046`).
- [확인] index와 log를 LLM 손에서 뺐다. 주석이 이유를 "so large wikis are never rewritten through model output"라고 밝힌다 (`ingest.ts:2436`).
- [확인] merge 결과를 길이·frontmatter로 검사하고, 실패하면 백업 후 fallback한다 (`page-merge.ts:158-181`). 다만 fallback은 새 본문만 남긴다. 다중 소스 페이지에서는 다른 소스의 기여가 디스크 페이지에서 빠지고 백업에만 남는다 (#8).
- [확인] 단일 소스 페이지와 다중 소스 페이지를 다르게 갱신한다. 정정된 소스가 옛 문장을 끌고 다니지 않는다 (`ingest.ts:2176-2182`).
- [확인] 파일 감시가 이벤트 유실에 강하다. native 이벤트 + 주기적 snapshot 대조 + 해시 기반 이동 감지 + 앱 자체 쓰기 무시 창이 있다 (`file_sync.rs:27-31`, `project-file-sync.ts:269-312`, `file_sync.rs:25`).
- [확인] 원본으로 돌아가는 경로가 제품 기능으로 있다. "Faithful" 모드와 `source.search`다. 경계는 코드가 강제한다. wiki·graph·web 도구를 거부하고 overview·schema를 문맥에서 뺀다 (`runtime.rs:1396`, `runtime.rs:3524-3533`, `runtime.rs:2783-2796`).
- [확인] LLM에 맡길 일과 코드가 할 일을 다시 나눈 흔적이 있다. 제품에 연결된 예는 review 선택지 고정 목록 (`ingest.ts:2502-2510`), review sweep의 JSON id 목록 (`sweep-reviews.ts:266-275`), dedup의 JSON 후보 그룹이다 (`dedup.ts:1-29`). wikilink 보강의 JSON 치환 설계 (`enrich-wikilinks.ts:1-26`)는 테스트에서만 불리는 죽은 코드다.

## 단점

- [확인] README가 코드와 7곳에서 어긋난다. 4-signal·2-hop decay 검색, cohesion 0.15, 60/20/5/15 배분, Deep Research auto-ingest, overview 자동 갱신, "serial" queue, 재시도 3회(실제는 시도 3회)다. Deep Research 확인 창도 일부 진입점에서만 뜬다. 근거는 #4, #6, #11, #12에 있다. README만 읽고 설계를 베끼면 없는 기능을 베끼게 된다.
- [확인] 근거 추적이 페이지 단위에서 멈춘다. claim과 원문 위치를 잇는 장치가 없다 (#5). `sources`의 다른 항목은 실제 파일인지 검사하지 않는다 (`ingest.ts:1760-1770`).
- [확인] write path gate가 ingest 경로에만 걸린다. agent `wiki.write_page`·API `pages/write`·Save to Wiki는 frontmatter·`sources`·schema 검사 없이 쓴다 (`tools.rs:687-760`, `tools.rs:2723-2748`, `chat-message.tsx:567-611`).
- [확인] merge fallback이 다중 소스 페이지의 기존 본문을 버린다. 70% 검사·LLM 오류·frontmatter 누락 어느 쪽이든 새 본문 + 배열 합집합을 쓴다. 잠금 필드도 복원하지 않는다 (`page-merge.ts:150-180`).
- [확인] gate가 버린 블록은 ingest 실패가 아니다. 경고만 남고 cache가 저장되므로 그 페이지는 소스가 바뀔 때까지 다시 생기지 않는다 (`ingest.ts:2038-2046`, `ingest.ts:1543-1555`).
- [확인] review sweep이 contradiction도 LLM 판정에 넘긴다. 남겨 두는 것은 프롬프트 지시뿐이다 (`sweep-reviews.ts:229`, `sweep-reviews.ts:400-423`).
- [확인] 생성 단계는 기존 페이지 본문을 보지 않는다. 같은 주제가 다른 이름으로 생기면 사후에 LLM dedup을 돌려야 한다 (`dedup.ts:1-10`).
- [확인] ingest 파일 쓰기가 원자적이지 않다. queue 파일이 깨지면 빈 queue로 시작한다 (#10).
- [확인] 파일 버전 이력은 기본으로 꺼져 있다. ingest 쓰기는 이력에 "human"·"ui.write_file"로 기록된다 (`fs.rs:1253-1260`). 켜도 앱 안의 사람 편집과 ingest를 구분하지 못한다. 앱 밖 편집은 기록되지 않는다.
- [확인] Save to Wiki는 LLM 답을 소스로 다시 ingest한다. queue도 거치지 않는다 (`chat-message.tsx:619-625`). Deep Research에서 걷어 낸 되먹임 고리가 여기 남아 있다.
- [확인] 의미 lint는 페이지 앞 500자를 한 프롬프트에 몰아 넣는다. 규모가 커지면 버티지 못한다 (`lint.ts:244`, `lint.ts:262-290`).
- [확인] index 재생성을 사람이 돌리기 전에는 최근 절 200항목 상한 때문에 오래된 페이지가 LLM 시야에서 빠진다 (`ingest.ts:1756`, `project.rs:154-167`). 재생성 뒤에는 반대로 index 전체가 잘리지 않고 프롬프트에 들어간다 (#12).
- [확인] 생성 프롬프트가 overview·index를 갱신하라고 하면서 동시에 쓰지 말라고 한다 (`ingest.ts:2436`, `ingest.ts:2519`, `ingest.ts:2520`).
- [확인] CI가 테스트를 돌리지 않는다 (`.github/workflows/ci.yml`).
- [확인] 대화형 ingest 경로가 죽은 코드로 남아 있다. 그 경로는 `wiki/schema.md`를 읽는데, 실제 schema는 루트 `schema.md`다 (`ingest.ts:3503`, `ingest.ts:3625`, `ingest.ts:788`).

## 내 llm-wiki에 가져올 것 / 피할 것

가져올 것 (설계만, GPL이라 코드는 옮기지 않는다)

- LLM 출력은 FILE 블록 문법으로 받는다. 디스크에 닿기 전에 한 함수에서 경로·frontmatter·`sources`·schema 경로·날짜를 코드로 바로잡는다 (`ingest.ts:2016-2218`). 이 repo와 달리 모든 쓰기 경로(agent·API·답 저장)가 같은 gate를 지나게 한다.
- `index.md`와 `log.md`는 코드가 쓴다. 모델이 쓴 aggregate 파일은 버리고 경고를 남긴다.
- `schema.md`의 "Page Types" 표를 코드가 읽는 계약으로 삼는다. 문서와 gate가 같은 출처를 본다 (`wiki-schema.ts:30-66`).
- "부분 성공 = 실패" 원칙을 둔다. cache 저장은 완결성 검사 뒤에만 한다. 끊긴 생성은 이미 쓴 경로를 checkpoint로 남겨 이어서 한다. gate가 버린 블록도 완결성 검사에 넣는다.
- 단일 소스 페이지는 교체, 다중 소스 페이지는 merge로 갱신 규칙을 가른다.
- merge 결과는 길이 하한과 frontmatter 존재로 검사한다. 잠근 필드는 기존 값으로 되돌리고, 배열 필드는 합집합으로 강제한다. 검사에 걸렸을 때는 이 repo처럼 새 본문으로 덮지 않고 기존 본문을 유지하거나 사람에게 넘긴다.
- LLM에게는 판단만 시키고 편집은 코드가 한다. 예: review 선택지 고정 목록, sweep의 id 목록, link 보강의 `(term → target)` JSON(이 repo에서는 미연결).
- 원본 직접 검색 모드를 둔다. wiki가 파생물이라는 것을 기능으로 드러낸다.
- 파일 감시는 이벤트 + 주기적 snapshot 대조 + 해시 이동 감지로 짠다.

피할 것

- README·설계 문서와 코드를 따로 고치는 것. 이 repo는 7곳이 어긋났다. 내 repo에서는 문서의 수치를 코드 상수에서 생성하거나, 문서에 코드 위치를 박는다.
- LLM 답을 소스처럼 다시 ingest하는 것. 파생물이 원본 자리에 들어간다.
- 길이로 자르는 index에 LLM의 기존 페이지 인식을 맡기는 것. 생성 전에 후보 페이지를 검색해서 본문 일부를 넣거나, 결정적 이름 해석을 둔다.
- gate를 쓰기 경로 하나에만 거는 것. 저장 함수 하나로 모든 쓰기를 모은다.
- "보존한다"는 약속을 프롬프트에만 두는 것. contradiction을 닫지 않는다면 코드에서 type으로 거른다.
- 비원자적 쓰기와 실패를 삼키는 상태 파일. 상태 파일은 temp+rename으로 쓰고, 읽기 실패는 빈 상태가 아니라 오류로 드러낸다.
- 모든 페이지를 한 프롬프트에 넣는 lint. 결정적 lint를 먼저 하고, LLM lint는 batch로 나눈다.
- 데스크톱 앱 형태 자체. 기능 대부분이 UI·멀티포맷 파싱·agent runtime에 들어가 있다. 내 llm-wiki의 핵심 결정과는 거리가 멀다.

## 확인하지 못한 것

- 앱을 실행하지 않았다. 아래 동작은 코드를 읽어서만 판단했다. 실제 ingest 1회의 호출 수, 토큰, 페이지 수는 모른다. 샘플 소스로 한 번 돌리고 `.llm-wiki/ingest-warnings.log`와 activity 패널을 보면 알 수 있다.
- README의 recall 58.2% → 71.4%의 출처를 찾지 못했다. 저자의 별도 benchmark repo나 issue를 보면 알 수 있다.
- shallow clone이라 기능 이력을 git log로 확인하지 못했다. overview 자동 갱신과 Deep Research auto-ingest가 언제 빠졌는지는 전체 clone의 `git log -S` 로 알 수 있다.
- `sweep-reviews.ts`의 LLM 판정 정확도는 모른다. 프롬프트와 type 처리는 읽었다(#9).
- `dedup-runner.ts`의 embedding 사전 필터와 병합 UI 흐름은 머리 주석만 읽었다.
- Rust agent runtime(`runtime.rs` 5,816줄)의 planner 루프와 skill 로딩은 Faithful 분기와 도구 목록만 확인했다.
- 별도 저장소 `nashsu/llm_wiki_skill`(Claude Code·Codex용 skill)은 열어 보지 않았다.
- `src/lib/ingest-sanitize.ts`가 고치는 frontmatter 손상 유형의 전체 목록은 보지 않았다.

## 검증 기록

2026-10-11, clone `48fd970`의 코드를 읽어서 대조했다. 앱은 실행하지 않았다.

- #한눈에: "규칙 대부분이 TS 후처리에 있다"를 `[추정]`으로 내리고, 후처리가 ingest 경로에만 걸린다고 적었다.
- #한 바퀴 흐름 11, #4: "3번 재시도"를 "시도 3번(재시도 2번)"으로 고쳤다. README의 "auto-retry up to 3 times"를 README 불일치 7번째로 더했다.
- #한 바퀴 흐름 14, #6: 검색의 그래프 이웃이 wikilink만이 아니라 frontmatter `related`도 쓴다고 고쳤다 (`search.rs:707-727`).
- #6: "4-signal 점수는 edge 굵기에만"을 "그래프 화면의 edge 굵기와 Louvain 가중치"로 고쳤다.
- #6: cohesion 근거 줄을 `README.md:169`에서 `README.md:168`로 고쳤다.
- #6, #장점, #가져올 것: `enrichWithWikilinks`가 제품 경로에 연결되지 않은 죽은 코드라는 점을 장점·가져올 것에도 반영했다.
- #1: 확인하지 못한 것에 있던 `pages/write`의 인증·덮어쓰기 규칙을 확인해 #1로 옮겼다(항상 token 필요, 생성 전용 기본값, agent와 같은 쓰기 함수).
- #2: write path gate가 ingest 경로에만 걸리고 agent·API·Save to Wiki·lint 수정 쓰기는 우회한다는 점을 더했다.
- #2: 언어 검사 대상을 "concept 페이지"에서 "entity·source·log를 뺀 모든 페이지"로 고쳤다.
- #2: gate가 버린 블록은 ingest 실패가 아니고 cache가 저장된다는 점을 더했다. #장점의 "부분 성공 = 실패"도 이 범위로 좁혔다.
- #2, #5: `sources`의 다른 항목은 실제 파일인지 검사하지 않는다는 점, 표에 없는 type은 schema 검사를 통과한다는 점을 더했다.
- #5: 소스 삭제 때 단독 소스 페이지를 지우고 참조를 걷어 낸다는 점을 더했다. merge fallback으로 생기는 반대 방향 어긋남을 `[추정]`으로 더했다.
- #8: "fallback 때만 백업"을 "fallback과 단일 소스 교체 때 백업"으로 고쳤다. fallback이 새 본문만 남겨 다른 소스의 기여를 버린다는 점을 더했다.
- #2, #8: 잠금 필드 복원이 fallback 경로에서는 일어나지 않는다고 적었다.
- #9: review sweep이 contradiction 등을 남겨 둔다는 주장을 "프롬프트 지시뿐, 코드는 type을 거르지 않는다"로 고쳤다.
- #9: Deep Research 확인 창이 그래프 화면 진입점에서만 뜨고 review 큐에서는 바로 실행된다고 고쳤다.
- #9: "사람 편집은 watcher가 잡아 human으로 남긴다"를 반박했다. watcher는 file history를 기록하지 않는다.
- #10: lock이 JS 메모리 안에만 있다는 점, Save to Wiki의 index·log 쓰기가 lock 밖이라는 `[추정]`을 더했다.
- #11: Faithful 모드의 근거를 코드 강제(도구 거부, overview·schema 제거)로 보강했다.
- #11: "코드는 페이지 50%, index 5%"를 고쳤다. 그 상수를 읽는 비테스트 코드가 없고, 채팅은 agent 도구 호출 예산으로 돈다.
- #12: 200항목 상한이 재생성 전에만 문제라는 조건을 붙였다. 재생성 뒤에는 index 전체가 잘리지 않고 프롬프트에 들어간다는 점을 더했다.
- #12, #단점: 프롬프트의 index 갱신 지시도 overview와 같은 모순이라고 더했다.
- #7: 의미 lint의 500자가 frontmatter부터 센다는 점을 더했다.
- #14: Graph API 1,000 노드 근거에 코드 위치(`api_server.rs:2475`)를 더했다. review sweep 호출 수를 "1회"에서 "0-5회"로 고쳤다.
- #4: 기본 감시 확장자에 epub·mobi가 없다는 점, 32MB 초과 파일은 해시 이동 감지에서 빠진다는 점을 더했다.
- #단점, #피할 것: 위에서 새로 확인한 약점(gate 우회, fallback 본문 손실, soft drop 고착, sweep의 contradiction 처리)을 더했다.
- 비교 검토 단계: #2에 `isSafeIngestPath`가 `wiki/` 밖 경로를 거부해 ingest 출력이 raw에 닿지 못한다는 점을 더했다 (`ingest.ts:460-461`을 열어 확인).
- 비교 검토 단계: #4의 사례 없는 [추정](소스 하나가 건드리는 페이지 수)을 모르는 것과 그것을 알 방법을 적는 "확인하지 못한 것" 형식으로 바꿨다.

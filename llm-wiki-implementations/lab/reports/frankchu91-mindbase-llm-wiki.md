# frankchu91/mindbase-llm-wiki — LLM에게는 JSON 계획만 받고 쓰기는 코드가 하지만, 그 원칙이 온전히 지켜지는 곳은 웹 contribute 한 경로뿐이다

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/frankchu91/mindbase-llm-wiki |
| 분석한 commit | `c5273d2` (shallow clone, 0.4.6 release) |
| 별 · fork | 130 · 17 (`gh api`, 2026-10-11 조회) |
| 최근 push | 2026-10-10 |
| 생성 | 2026-04-26 |
| 커밋 · 기여자 | 92 · 1명 |
| 라이선스 | MIT |
| 형태 | pnpm monorepo. MCP 서버 + Express 서버와 React 웹 UI + Claude Code plugin. CLI, browser extension, android, ios 앱도 있다. |
| 코드 규모 (ts/tsx/js 줄 수, 테스트 포함) | `packages/core` 21.4k, `apps/server` 15.7k, `apps/web` 22.9k, `apps/mcp` 5.0k, plugin markdown 1.3k |
| 테스트 파일 | `*.test.ts(x)` 115개 |

- [확인] 이 repo 안에는 엔진이 둘 있다. 하나는 웹 서버의 ops engine이다 (`apps/server/src/ops/`). 다른 하나는 core의 legacy compile engine이다 (`packages/core/src/compile/l1.ts`).
- [확인] 두 엔진은 서로 다른 디스크 layout을 쓴다. ops engine은 v2 layout(`context.md` + `sources/research/`)에 쓴다. compile engine은 v1 layout(`wiki/notes/` + sqlite index)에 쓴다.
- [확인] README가 말하는 "constrained JSON → human approval → whitelisted executors" 설계는 ops engine에만 있다 (`apps/server/src/ops/runner.ts:1-5`).
- [확인] Claude Code plugin과 MCP 서버의 ingest 도구는 ops engine을 거치지 않는다. 이들은 compile engine을 부른다 (`apps/mcp/src/tools/ingest-plan.ts:87`, `apps/mcp/src/tools/ingest-execute.ts:56`). MCP `ingest_source`는 계획 단계 없이 `compileL1`을 바로 부른다 (`apps/mcp/src/tools/ingest-source.ts:53`).
- [확인] compile engine은 새 concept page를 `wiki/concepts/<slug>.md`에 쓴다 (`packages/core/src/storage/paths.ts:24-30`). 그런데 MCP 서버의 검색 index, `read_wiki_page`, sqlite `reindex`는 `wiki/notes/`만 읽는다 (`apps/mcp/src/context.ts:59`, `apps/mcp/src/tools/read-wiki-page.ts:25`, `packages/core/src/graph/index/reindex.ts:31,94`). #11에서 다룬다.
- [확인] 저장소 루트의 `CLAUDE.md`는 "lint 없음", "file-answer-back 없음" 같은 gap 목록을 아직 싣고 있다. 코드에는 둘 다 이미 있다. 문서가 코드를 따라가지 못한 상태다.

## 한 바퀴 흐름

### 웹 UI 경로 (ops engine, v2 layout)

1. 사용자가 `/contribute`에 글을 넣는다. 웹이 `POST /api/ops/contribute {mode:'plan'}`을 보낸다 (`apps/server/src/routes/ops.ts:65`).
2. `runContributePlan`이 글을 먼저 `sources/contributors/<user>/<date>.md`에 append한다 (`apps/server/src/ops/runner.ts:198`, `apps/server/src/lib/daily-entry.ts`). 같은 글을 곧바로 다시 보내면 중복 append하지 않는다. 이 검사는 파일 끝이 같은 글로 끝나는지만 본다 (`daily-entry.ts:24`). 그 사이에 다른 글이 들어갔으면 다시 append된다.
3. `gatherProjectCore`가 `context.md`, `index.yaml`, 프로젝트 `README.md`를 읽는다 (`apps/server/src/ops/gather.ts:14`). `findRelated`가 hybrid search로 관련 페이지 5개를 찾는다 (`apps/server/src/routes/ops.ts:50-54`).
4. `contributePrompt`가 prompt를 만든다 (`apps/server/src/ops/recipes/contribute.ts:40`). `completeJson`이 LLM을 한 번 부르고 zod schema로 검사한다. 실패하면 한 번만 다시 묻는다 (`apps/server/src/ops/llm.ts:40-68`).
5. `guardDuplicatePages`가 이미 있거나 다른 계획이 만들 예정인 slug를 지운다 (`runner.ts:116`). `ensureCitations`가 `[@<source path>]` 인용을 코드로 덧붙인다 (`runner.ts:149`).
6. 계획은 메모리 `Map`에 10분 동안 보관된다 (`runner.ts:73`). 웹에 takeaways와 action 목록이 checkbox로 뜬다. checkbox는 처음에 모두 체크된 상태다 (`apps/web/src/components/ops/OpRun.tsx:57`).
7. 사용자가 고른 index만 `POST {mode:'apply'}`로 돌아온다. `applyContributePlan`이 `applyActions`를 부른다 (`runner.ts:244-262`). 실행 결과는 `logs/<date>.md`에 한 줄로 남는다 (`runner.ts:165`).
8. Build는 `POST /api/ops/build` → `runBuild`다 (`runner.ts:616`). `context.md`보다 mtime이 새 파일을 모으고 (`gather.ts:163-172`) LLM 한 번으로 `context.md` 전체를 다시 쓴다. 승인 단계 없이 바로 적용한다 (`runner.ts:633`). 웹 UI도 build 창을 열면 확인 없이 바로 시작한다 (`OpRun.tsx:90-98`). 모으는 범위는 `sources/contributors/`와 `sources/research/`뿐이다. `sources/raw/`의 PDF·웹 캡처 추출문은 build 입력에 들어가지 않는다 (`gather.ts:165-168`).
9. Query는 `POST /api/ask` → core `askQuestion`이다 (`packages/core/src/qa/query.ts:160`). BM25 후보를 뽑고 사용자 자료(source layer)에 가중치를 준다. `read_file` 도구 loop를 최대 3번 돈다. 끝나면 query 한 줄을 log에 남긴다 (`apps/server/src/routes/ask.ts:13-31`).
10. Lint는 `POST /api/ops/lint` → `runLint`다 (`runner.ts:558`). LLM findings를 받고, 결정적 kind는 버리고, 인용문을 원문과 대조한다. 그다음 코드로 계산한 findings를 붙여 `artifacts/lint/<date>.json`에 저장한다. wiki 파일은 쓰지 않는다.

### Claude Code plugin 경로 (MCP 서버, 주로 v1 layout)

1. `/mb:contribute`가 짧은 글이면 `mindbase_contribute`를 부른다. 이 도구는 contributor 파일에 append만 한다 (`apps/mcp/src/tools/contribute.ts:49-58`).
2. 긴 source면 `contributor` sub-agent를 띄운다 (`apps/plugin/commands/contribute.md:26`). sub-agent prompt의 순서는 "takeaways 토론 → 계획 제안 → 승인 대기 → 승인되면 `ingest_plan` → `ingest_execute`"다 (`apps/plugin/agents/contributor.md:23-25`).
   - [확인] 즉 사람이 승인하는 것은 sub-agent가 말로 낸 계획이다. 실제로 실행되는 것은 승인 뒤에 `ingest_plan`이 새로 만든 LLM 계획이다. 두 계획을 대조하는 단계는 prompt에도 코드에도 없다.
   - [확인] prompt는 실행 결과가 "`sources/research/`를 갱신한다"고 적는다 (`contributor.md:26`). 실제 compile executor는 `wiki/concepts/`에 쓴다 (`packages/core/src/storage/paths.ts:24-30`).
3. `ingest_plan`은 `compileL1Plan`을 부른다. 이 함수는 tool-use loop를 dry-run으로 최대 10번 돌려 계획을 모은다 (`packages/core/src/compile/l1.ts:398-478`). 이 도구는 `projectId`를 받지 않는다. 프로젝트 범위가 없는 `<dataDir>` 전역 store에 쓴다 (`apps/mcp/src/context.ts:43`).
4. `ingest_execute`는 승인된 action을 실제 executor로 다시 실행한다. 이어서 결정적 cross-link를 자동 모드로 돌린다 (`apps/mcp/src/tools/ingest-execute.ts:86`).
5. `/mb:build`는 `builder` sub-agent를 띄운다. sub-agent는 `mindbase_gather_sources` → `Read` → `mindbase_atomic_write_context` → `mindbase_rebuild_index` → `mindbase_append_log`를 부른다 (`apps/plugin/agents/builder.md:17-24`).
6. `/mb:lint`는 `curator` sub-agent를 띄우고 `mindbase_run_wiki_health`를 부르게 한다 (`apps/plugin/agents/curator.md:14`). 이 이름은 curator 허용 목록과는 맞는다. 실제 MCP 도구 이름 `run_wiki_health`와는 다르다. #10에서 다룬다.
   - [확인] 이름이 맞더라도 `run_wiki_health`는 `projectId`를 받지 않는다. 전역 v1 store와 sqlite만 본다 (`apps/mcp/src/tools/run-wiki-health.ts:9,15-22`). 그래서 plugin lint는 v2 프로젝트의 `context.md`와 `sources/research/`를 검사하지 않는다. 원문 일치 인용을 요구하는 v2 lint는 웹에서만 돈다.

## 축별 분석

#### 1. 실행 형태

입장: MCP 서버 + 웹. 그 위에 Claude Code plugin(slash command, sub-agent, SessionStart hook)을 얹었다.

- [확인] MCP 서버는 도구 50개를 등록한다 (`apps/mcp/src/tools/index.ts:64-113`). README와 marketplace 설명은 49개라고 적는다.
- [확인] 웹 서버는 Express이고 ops 라우트를 SSE로 연다 (`apps/server/src/routes/ops.ts:15-27`).
- [확인] plugin은 `npx -y mindbase-mcp`를 MCP child process로 띄운다 (`apps/plugin/.mcp.json`). SessionStart hook이 현재 프로젝트의 README, context.md, index.yaml을 통째로 context에 넣는다 (`apps/plugin/hooks/session-start:26-45`).
- [확인] LLM adapter는 OpenAI, Anthropic, DeepSeek, Ollama를 지원한다 (`apps/mcp/src/context.ts:9`). 웹 서버에는 Ollama 설치·모델 pull을 돕는 onboarding 라우트가 있다 (`apps/server/src/routes/ollama.ts:38-56`).

#### 2. 규칙의 위치

입장: 쓰기 경계는 코드가 강제한다. 쓰기 분량과 내용 규칙은 prompt에만 있다.

코드가 강제하는 것:
- [확인] action 종류는 zod discriminated union 4개로 닫혀 있다. `create_research_page`, `update_context`, `append_context_section`, `add_wikilinks`다 (`apps/server/src/ops/types.ts:16-21`). 한 계획은 action 20개까지다 (`types.ts:25`).
- [확인] `sources/contributors`나 `sources/raw`에 쓰는 action은 schema에 없다 (`types.ts:3-7` 주석, `types.ts:12-14` 경로 regex).
- [확인] 모든 경로는 project root 밖으로 나가지 못한다 (`apps/server/src/ops/executors.ts:15-21`).
- [확인] `context.md`는 400줄을 넘으면 쓰기를 거부한다 (`executors.ts:38-41`, `types.ts:32`).
- [확인] 중복 slug 차단, 인용 덧붙이기, 결정적 lint kind 필터, lint 인용 검증이 모두 코드다 (`runner.ts:116`, `runner.ts:149`, `runner.ts:586`, `runner.ts:357`).

prompt에만 있는 것:
- [확인] "새 research page는 최대 1개"는 contribute prompt 문장이다 (`recipes/contribute.ts:29-31`). schema는 20개까지 허용한다.
- [확인] build의 "새 페이지 최대 2개", "모순은 ⚠️로 표시"도 prompt 문장이다 (`recipes/build.ts:13-19`).
- [확인] plugin 템플릿 README의 YAML 규칙(`target_pages_per_source`, `max_context_lines`, "5개 넘는 파일을 건드리면 먼저 묻기")은 서버 코드가 읽지 않는다. 웹 UI가 표시용으로만 파싱한다 (`apps/web/src/lib/schema-yaml.ts:12-30`). 서버 ops는 이 README를 "PROJECT RULES"라는 이름으로 prompt에 통째로 넣는다 (`recipes/contribute.ts:60`).
- [확인] plugin sub-agent의 단계 순서("discuss takeaways 필수", "승인을 기다려라")는 agent markdown의 지시다 (`apps/plugin/agents/contributor.md:23-25`). 코드 gate는 없다.

schema 문서:
- [확인] v1 compile engine은 `schema/ingest.md`, `schema/query.md`를 store에서 읽어 prompt에 넣는다 (`packages/core/src/compile/prompts.ts:17`, `packages/core/src/qa/query.ts:94`). 웹 서버는 이 파일을 편집·초기화하는 API를 연다 (`apps/server/test/schema-api.test.ts:20-46`).
- [확인] v2 ops engine은 이 `schema/` 파일을 읽지 않는다. recipe 파일의 상수 문자열이 system prompt다.
- [확인] pre-commit hook이나 git gate는 없다.

#### 3. 저장 구조

입장: 프로젝트별 디렉터리에 "사용자 층 / AI 층 / 파생 층"을 나눈다. AI 층의 중심은 `context.md` 한 장이다.

v2 layout (`apps/plugin/skills/mindbase/SKILL.md:22-35`, README "Where your data lives"):

| 경로 | 소유 | 내용 |
|---|---|---|
| `README.md` | 사용자 | 프로젝트 운영 규칙. prompt에 들어간다. |
| `context.md` | AI | 합성 문서. 섹션은 Current Focus / Active Topics / Key Decisions / Learnings / Open Questions / Blockers (`apps/plugin/templates/context.md.template`) |
| `index.yaml` | 파생 | 기여자별 파일 수, research page 수 (`apps/mcp/src/tools/rebuild-index.ts:64-80`) |
| `sources/contributors/<user>/YYYY-MM-DD.md`, `.../notes/*.md` | 사용자 | append-only 일지와 노트 |
| `sources/research/<slug>.md` | AI | concept·research page |
| `sources/raw/<date>/<id>.{md,meta.json,extracted.md,...}` | 사용자 | PDF, 웹 캡처 원본과 추출문 |
| `state/builder/snapshots/*.md` | 파생 | `context.md` 이전본 |
| `logs/YYYY-MM-DD.md` | 파생 | 연산 로그 |
| `artifacts/lint/<date>.json` | 파생 | lint findings와 dismiss 상태 |

- [확인] v2 research page에는 frontmatter가 없다. executor는 LLM이 준 markdown을 그대로 쓴다 (`executors.ts:29-36`). 출처는 본문 끝 `Sources: [@path]` 줄로만 남는다.
- [확인] v1 layout은 사용자 층 `wiki/notes/`와 LLM 층 `wiki/concepts/`를 나눈다 (`packages/core/src/storage/paths.ts:9-30`). compile이 만드는 page는 `wiki/concepts/<slug>.md` + `<slug>.meta.json` sidecar다. frontmatter는 `title`, `tags`, `sources: [raw_id]`, `created`, `updated`, `captured_*`를 쓴다 (`packages/core/src/tools/executor.ts` `createConcept`). sidecar에는 `edit_state`(`auto`/`human_touched`)가 있다.
- [확인] v1의 파생 상태는 sqlite 하나에 모인다. `pages`, `links`(typed edge), `audit_log`, `confidence_log`, `contradiction_cache` 등이다 (`packages/core/src/graph/index/schema.ts:9-102`). 경로는 `<dataDir>/.index/db.sqlite`다 (`apps/mcp/src/context.ts:74-76`).
- [확인] 서버는 `README.md`가 있으면 v2, 없으면 v1로 판정한다 (`apps/server/src/context.ts:441-446`). v1 프로젝트에서는 ops 라우트가 `V1_LAYOUT_UNSUPPORTED`를 돌려준다 (`apps/server/src/routes/ops.ts:41`).

#### 4. Ingest

입장: 웹 contribute는 "source를 먼저 저장 → LLM 한 번 → 사람이 action을 고름"이다. 그 밖의 ingest 경로는 대부분 자율이다.

- 사람 참여
  - [확인] 웹 contribute는 action마다 checkbox 승인을 받는다 (`runner.ts:244-262`).
  - [확인] MCP `ingest_execute`는 승인 map에 없는 action을 승인으로 본다 (`apps/mcp/src/tools/ingest-execute.ts:21`, `packages/core/src/compile/l1.ts:497`). 웹과 기본값이 반대다.
  - [확인] capture inbox worker는 60초마다 돌며 `compileL1`로 바로 wiki를 쓴다 (`apps/server/src/lib/capture-worker.ts:90`). 서버 시작 때 무조건 켜진다 (`apps/server/src/index.ts:188`). RSS worker도 무조건 켜지고 새 글을 inbox에 넣는다 (`apps/server/src/index.ts:194`).
- 증분·변경 추적
  - [확인] build의 "아직 반영 안 된 source"는 `context.md`보다 mtime이 새 파일이다 (`gather.ts:163-172`). 최신 30개, 파일당 4,000자까지만 본다 (`gather.ts:11-12`).
  - [확인] 이 후보에는 AI가 쓴 `sources/research/`가 들어가고 `sources/raw/` 추출문은 빠진다 (`gather.ts:165-168`). plugin의 `mindbase_gather_sources`도 같다 (`apps/mcp/src/tools/gather-sources.ts:61-64`). PDF·웹 캡처는 contribute에 `sourcePath`로 넘겨야 wiki에 들어간다. 반면 lint의 `uncited_source`는 raw 추출문도 "build에 반영됨"으로 센다 (`gather.ts:143-160`, `runner.ts:485-491`).
  - [추정] 이 mtime 기준은 contribute와 엇갈린다 — 사례: 코드 경로 1개. `append_context_section`이 `context.md`를 고치면 mtime이 갱신된다 (`executors.ts:52-73`). 그 전에 쌓였지만 build되지 않은 노트는 이후 "반영됨"으로 취급된다.
- queue·crash 복구
  - [확인] contribute 계획은 프로세스 메모리에만 있다 (`runner.ts:72`). 서버가 재시작되면 사라진다.
  - [확인] capture inbox는 `queued / processing / compiled / failed` 상태 파일을 쓴다 (`apps/server/src/lib/inbox.ts:9`). worker는 60초마다 queue 폴더의 파일만 집는다 (`inbox.ts:80-84`). 실패한 항목은 failed 폴더로 옮겨지므로 자동으로 다시 돌지 않는다 (`inbox.ts:115-122`). `processOne`이 `failed`를 받아 주는 것은 UI의 Retry 버튼용이다 (`capture-worker.ts:63-64`).
  - [확인] 처리 중에 프로세스가 죽으면 그 항목은 다시 처리되지 않는다. `markProcessing`은 상태만 바꾸고 파일을 queue 폴더에 둔다 (`inbox.ts:98-104`). worker는 `processing` 상태를 건너뛴다 (`capture-worker.ts:64`). 상태를 되돌리는 코드는 찾지 못했다. 실행해 보지는 않았다.
- 자동 감시: [확인] 파일 시스템 watcher는 없다. RSS polling(1시간)과 capture inbox polling(60초)만 있다 (`apps/server/src/lib/rss-worker.ts:24`, `capture-worker.ts:26`).
- 멀티포맷: [확인] PDF(pdfjs-dist), docx(mammoth), 이미지 OCR(tesseract.js), 오디오 전사, YouTube 자막(yt-dlp 외부 실행), HTML 본문 추출(Readability)을 지원한다 (`apps/server/package.json`, `apps/server/src/routes/ingest.ts:34,106,174`).
- 소스 하나가 건드리는 페이지 수
  - [확인] v2 contribute는 prompt상 새 research page 최대 1개 + context 섹션 append + wikilink다 (`recipes/contribute.ts:29-31`).
  - [확인] v2 action 목록에는 기존 research page 본문을 고치는 action이 없다 (`types.ts:16-21`). 중복 차단 메시지는 "Update it instead"라고 말하지만 (`runner.ts:129`) 그 수단이 schema에 없다. 기존 page에 할 수 있는 일은 `See also:` 줄 추가뿐이다 (`executors.ts:74-82`).
  - [확인] v1 compile은 소스 하나에 concept 최대 20개를 허용한다 (`l1.ts:226-233`). `CLAUDE.md`는 실제 평균이 1~4페이지라고 적는다 (`CLAUDE.md` "target 5-15 touches ... current avg: 1-4").

#### 5. 근거 추적 단위

입장: 페이지 단위(또는 context 불릿 단위) 출처 경로다. 원문 글자 일치 검사는 lint finding에만 쓴다.

- [확인] contribute가 만드는 research page와 context 불릿 끝에 `[@<project-relative-path>]`가 붙는다. 모델이 빠뜨려도 코드가 붙인다 (`runner.ts:149-160`).
- [확인] 이 보정은 contribute에만 있다 (`runner.ts:215`). build, research, ask autoSave는 모델 출력을 그대로 쓴다 (`runner.ts:306,633`, `apps/server/src/routes/ask.ts:87-89`). autoSave page에는 인용이 아예 붙지 않는다. research prompt는 `(source: ...)` 괄호 표기와 `[@...]`를 함께 요구한다 (`recipes/research.ts:25-30`). 괄호 표기만 쓰면 lint parser가 인용으로 세지 않는다.
- [확인] 인용 parser는 `[@...]` regex 하나다 (`gather.ts:44-46`). 줄 범위나 문장 단위 anchor는 없다.
- [확인] lint의 contradiction은 원문과 글자 일치하는 인용 2개, stale은 1개가 있어야 살아남는다 (`runner.ts:349-395`). 비교 전에 소문자화, `*_\`` 제거, 공백 정규화를 한다 (`runner.ts:347`).
- [확인] wiki 본문 주장 자체를 원문과 대조하는 검사는 없다.
- [확인] `/mb:ask`는 `[<slug>:<line-range>]` 형식 인용을 요구한다 (`apps/plugin/commands/ask.md:20`). 이것은 prompt 지시이고 검증 코드는 없다.
- [확인] v1 page는 frontmatter `sources: [raw_id]`로 raw 문서 id를 남긴다.

#### 6. Link

입장: v2에서는 LLM이 link action을 제안한다. 그래프와 backlink 수는 코드가 매번 다시 센다. v1에서는 결정적 autolinker가 직접 본문을 고친다.

- [확인] v2 `add_wikilinks`는 대상 페이지 끝에 `See also: [[a]], [[b]]` 줄을 붙인다 (`executors.ts:74-82`). 대상은 research page와 `context.md`로 제한된다 (`types.ts:12-14`).
- [확인] lint 직전에 `[[...]]` regex로 outbound를 뽑고 inbound 수를 센다 (`gather.ts:72-88`). 이 값을 "deterministic — trust these inbound counts"라며 prompt에 준다 (`recipes/lint.ts:82-99`).
- [확인] v1 `crossLink`는 다른 페이지 제목이 본문에 단어 경계로 나오면 첫 등장을 `[[Title]]`로 바꾼다 (`packages/core/src/graph/crosslinker.ts:58-110`). `auto` 모드에서 점수 6 이상이면 바로 파일에 쓴다.
- [확인] v1 LLM `link` 도구는 `contradicts`, `supersedes` 같은 typed edge를 sqlite `links` 표에 넣는다 (`packages/core/src/tools/executor.ts:433-451`, `packages/core/src/graph/index/edge-type.ts:6-11`).

#### 7. Lint

입장: LLM lint와 결정적 lint의 경계를 코드로 나눈 점이 이 repo에서 가장 단단한 부분이다. v2 lint는 고치지 않고 보고만 한다.

- [확인] 코드가 계산하는 kind는 5개다. `unsourced_page`, `uncited_source`, `broken_citation`, `broken_link`, `near_duplicate`다 (`recipes/lint.ts:26-32`, `runner.ts:475-530`).
- [확인] 모델에게 맡기는 kind는 7개다. `contradiction`, `stale`, `orphan`, `missing_page`, `missing_link`, `gap`, `question`이다 (`recipes/lint.ts:9-16`).
- [확인] 모델이 결정적 kind를 내면 버린다 (`runner.ts:583-586`).
- [확인] `near_duplicate`는 slug 토큰의 Jaccard 0.6 이상, 공유 토큰 2개 이상으로 판정한다 (`runner.ts:399-448`).
- [추정] `orphan`은 inbound 수를 코드가 이미 세는데도 모델 kind로 남아 있다 — 사례: `gather.ts:83-86`이 세고 `recipes/lint.ts:59`가 모델에게 판단을 넘긴다. 결정적 kind로 옮길 여지가 있다.
- [확인] lint 입력은 research page 40개, 페이지당 1,200자로 잘린다 (`gather.ts:63-64`). 40개는 최신순이 아니라 디렉터리를 읽은 순서다 (`gather.ts:73`). 잘린 페이지는 모순 검사뿐 아니라 결정적 검사(inbound 수, broken link, near_duplicate, unsourced)에서도 빠진다.
- [확인] v2 lint는 wiki를 쓰지 않는다. 사람이 finding을 dismiss할 수만 있다 (`runner.ts:548-556`). 같은 날 lint를 다시 돌리면 `artifacts/lint/<date>.json`을 통째로 새로 쓴다 (`runner.ts:601-603`). 그날 dismiss한 기록은 사라진다.
- [확인] MCP `run_wiki_health`는 v1 쪽에서 cross-link를 자동 적용하고 `compileL2` lint action도 적용한다 (`apps/mcp/src/tools/run-wiki-health.ts:15-23`). plugin은 이를 "read-only" curator가 부른다고 설명한다 (`apps/plugin/agents/curator.md:3`).
- [확인] commit gate는 없다.

#### 8. stale·모순 처리

입장: 덮어쓰기 + snapshot이다. 모순은 표시만 하고 사람이 정한다는 원칙이 prompt에 있다.

- [확인] build는 `context.md` 전체를 새로 쓴다. 이전본은 `state/builder/snapshots/`에 남는다 (`executors.ts:38-51`).
- [확인] build prompt는 "still-true 내용 보존", "새 결정에 날짜", "모순은 ⚠️로 표시"를 지시한다 (`recipes/build.ts:13-19`). 코드 검사는 없다.
- [확인] v1 executor의 `flag_contradiction`과 `merge`는 페이지나 edge를 고치지 않고 성공만 돌려준다 (`packages/core/src/tools/executor.ts:453-472`).
- [확인] 다만 기록이 전혀 안 남는 것은 아니다. 자율 경로 `compileL1`(capture worker, MCP `ingest_source`)은 두 호출을 sqlite `audit_log`에 action으로 적는다 (`packages/core/src/compile/l1.ts:121-135,214-216,286,314-315`). 서버 `/api/audit-log`가 이를 돌려주고 (`apps/server/src/routes/audit-log.ts:10`) 웹 `ActionChip`이 `flag_contradiction`을 색으로 표시한다 (`apps/web/src/components/ActionChip.tsx:11`).
- [확인] MCP 승인 경로의 `compileL1Execute`는 audit를 남기지 않는다 (`l1.ts:480-505`). 이 경로에서는 두 호출이 정말 흔적 없이 사라진다. `merge`의 `queued_for_review`를 읽어 처리하는 review queue 코드는 찾지 못했다.
- [확인] stale 감지는 lint의 모델 kind(인용 1개 필수)와, 노트가 마지막 build보다 새로우면 켜지는 웹 상태 chip이다 (CHANGELOG 0.4.0 "Wiki-status chip").
- [확인] supersede 체계는 v1 edge type(`supersedes`)으로만 있다. v2에는 없다.

#### 9. 사람 개입

입장: README는 "모든 변경을 사람이 승인한다"고 말한다. 코드에서 그 말이 성립하는 경로는 웹 contribute 하나다.

- [확인] README는 웹 UI가 `/contribute`, `/build`, `/lint`, `/research`를 "approval cards"로 돌린다고 적는다 (`README.md:146`). 웹 UI에서 승인 단계가 있는 것은 contribute뿐이다. build는 창을 열면 자동으로 시작한다. research는 주제를 넣고 누르면 결과를 바로 쓴다 (`OpRun.tsx:39-40,77-98`).

| 경로 | 승인 방식 | 근거 |
|---|---|---|
| 웹 contribute | action별 checkbox. 처음엔 모두 체크됨 | `runner.ts:244-262`, `OpRun.tsx:57` |
| 웹 build | 없음. 창을 열면 바로 실행·적용 | `runner.ts:633`, `routes/ops.ts:92-102`, `OpRun.tsx:90-98` |
| 웹 research | 없음. 바로 적용 | `runner.ts:306`, `routes/ops.ts:104-119` |
| 웹 ask autoSave (설정) | 없음. 모델이 저장 표시를 내면 research page로 저장 | `apps/server/src/routes/ask.ts:76-89` |
| 웹 answer file-back | 결정적 계획 + 승인 map. 빠진 id는 승인으로 간주 | `apps/server/src/routes/answer-file-back.ts:38-93` |
| capture inbox, RSS | 없음. 자율 compile | `capture-worker.ts:90`, `index.ts:188-194` |
| MCP `ingest_execute` | 빠진 id는 승인으로 간주 | `ingest-execute.ts:21`, `l1.ts:497` |
| MCP `ingest_source` | 없음. 계획 없이 바로 compile | `apps/mcp/src/tools/ingest-source.ts:53` |
| plugin contributor | prompt 지시("Wait for user approval"). 승인 대상은 `ingest_plan` 이전의 말로 된 계획 | `apps/plugin/agents/contributor.md:24-25` |
| plugin builder | 없음. 바로 atomic write | `apps/plugin/agents/builder.md:22` |

- [확인] v1에는 `human_touched` 페이지를 LLM이 고치지 못하게 막는 장치가 있다 (`packages/core/src/tools/executor.ts:271,323`). MCP 서버 지시문도 사람 편집 페이지는 `force=true` 전에 사용자에게 물으라고 한다 (`apps/mcp/src/index.ts:42-49`).

#### 10. 동시성·안전

입장: 도구 허용 목록과 경로 검사는 있다. transaction, 낙관적 잠금, 복원 도구는 없다.

- 허용 목록
  - [확인] ops engine은 action 4종 외에는 실행할 수 없다 (`types.ts:16-21`, `executors.ts:27-84`).
  - [확인] plugin sub-agent는 frontmatter `tools:`로 도구를 제한한다. builder에는 Edit/Write/Bash가 없다 (`apps/plugin/agents/builder.md:4`).
  - [확인] 허용 목록의 도구 이름 일부가 실제 MCP 도구 이름과 다르다. curator는 `mcp__mb__mindbase_run_wiki_health`, `mindbase_find_orphans`, `mindbase_find_contradictions`, `mindbase_find_gaps`, `mindbase_suggest_links`를 허용한다 (`apps/plugin/agents/curator.md:4`). 실제 이름은 접두어 없는 `run_wiki_health`, `find_orphans` 등이다 (`apps/mcp/src/tools/run-wiki-health.ts:7` 등). builder의 `mindbase_search_wiki`, researcher의 `mindbase_search_wiki`·`mindbase_ask_wiki`, migrator의 `mindbase_run_wiki_health`도 같은 문제다. 합치면 9건이다.
  - [확인] slash command와 agent 본문도 없는 이름을 부른다. `/mb:ask`는 `mindbase_search_wiki`, `mindbase_ask_wiki`, `mindbase_read_wiki_page`, `mindbase_save_chat_excerpt`를 지시한다 (`apps/plugin/commands/ask.md:17-25`). contributor는 `mindbase_ingest_plan`을 부르라고 하고, 허용 목록에 없는 `mindbase_load_project`도 지시한다 (`apps/plugin/agents/contributor.md:4,21,25`).
  - [추정] 그래서 `/mb:lint`의 curator는 핵심 lint 도구를 부를 수 없다 — 사례: curator 허용 목록 7개 중 5개가 없는 이름이다. 실행해 보지는 않았다. `apps/plugin/scripts/verify-plugin.sh`는 파일 존재만 확인하고 이름은 대조하지 않는다.
  - [확인] 이름을 고쳐도 plugin lint는 v2 프로젝트를 보지 않는다. `run_wiki_health`는 입력이 없고 전역 v1 store만 본다 (`apps/mcp/src/tools/run-wiki-health.ts:9,15-22`). 이 도구는 `wiki/_insights.md`를 쓰고 cross-link와 L2 lint action을 적용한다. "read-only" curator 설명과 맞지 않는다 (`curator.md:3`).
- 원자성
  - [확인] 서버 executor는 `writeFile`로 바로 쓴다 (`executors.ts:35,49,71,80`). tmp + rename이 아니다.
  - [확인] MCP `mindbase_atomic_write_context`는 tmp + rename을 쓴다 (`apps/mcp/src/tools/atomic-write-context.ts:65-67`). `safe-write.ts`의 주석은 fsync를 말하지만 코드에는 fsync가 없다 (`apps/mcp/src/lib/safe-write.ts:6-12`).
  - [확인] `applyActions`는 action을 차례로 실행하고 실패를 모아 둔다 (`executors.ts:86-96`). 중간 실패 시 앞 action을 되돌리지 않는다.
- 동시성
  - [확인] build lock은 프로젝트별 메모리 `Set`이다 (`runner.ts:163`). build끼리만 막는다. contribute apply와 build가 동시에 `context.md`를 쓰는 경우는 막지 않는다.
  - [확인] 계획 적용 시 `context.md`가 계획 생성 후 바뀌었는지 확인하지 않는다 (`runner.ts:244-262`). 최대 10분 묵은 `update_context` 전체 덮어쓰기가 그 사이 변경을 지울 수 있다.
  - [확인] 같은 slug를 두 contribute 계획이 동시에 만드는 경우는 예약 Map으로 막는다 (`runner.ts:80-108`). 테스트가 있다 (`apps/server/src/ops/runner.test.ts:157`).
  - [확인] build, research, autoSave는 이 guard와 예약을 거치지 않는다 (`runner.ts:306,633`, `ask.ts:87`). executor는 같은 slug가 있으면 거절하지 않고 `<slug>-2`로 이름을 바꿔 새로 만든다 (`executors.ts:29-36`). `foo`와 `foo-2`는 slug 토큰 Jaccard가 0.5라서 `near_duplicate`에도 잡히지 않는다 (`runner.ts:399-400,408-415`).
- snapshot·undo
  - [확인] snapshot은 `update_context`(전체 덮어쓰기)에서만 만든다 (`executors.ts:42-48`). `append_context_section`과 `add_wikilinks`는 snapshot 없이 고친다.
  - [확인] snapshot을 읽어 복원하는 코드·라우트·도구는 찾지 못했다 (`grep snapshots` 결과는 쓰는 곳 두 군데뿐). 복원은 사람이 파일을 직접 옮기는 일이다.
- git: [확인] git 연동 코드는 없다. README는 사용자가 직접 `git init` 하라고 권한다.

#### 11. Query·검색

입장: BM25 + 사용자 자료 가중치 + 도구 loop다. hybrid(BM25 + embedding) 검색은 ingest 문맥과 검색 화면에 쓴다. 답을 wiki에 되저장하는 경로는 셋이다.

- [확인] `askQuestion`은 `wiki/hot.md`와 INDEX를 읽고, BM25 상위 6개를 후보로 잡는다 (`packages/core/src/qa/query.ts:166-185`). 사용자 자료에는 점수 가중치를 곱한다 (`query.ts:113-117`).
- [확인] 모델에게 `read_file` 도구를 주고 최대 3번 돈다 (`query.ts:162,322-330`). 본문 예산은 기본 50,000자다 (`query.ts:201`). 잘린 페이지 목록을 답과 함께 돌려준다 (`query.ts:294`).
- [확인] hybrid search는 BM25 순위와 vector 순위를 RRF로 섞고 backlink·최신성 가중치를 더한다 (`packages/core/src/search/hybrid.ts:129-147`). embedding은 `@xenova/transformers`로 로컬 계산한다 (`apps/server/package.json`).
- [확인] MCP `ask_wiki`는 상위 결과와 1-hop wikilink 이웃을 가져온다고 설명한다 (`apps/mcp/src/index.ts:24-26`).
- [확인] 되저장 경로는 (a) ask autoSave → v2 research page (`ask.ts:76-99`), (b) answer file-back plan/execute → v1 note (`answer-file-back.ts`), (c) plugin `/mb:ask` 후 "저장할까요?" → `mindbase_contribute` (`apps/plugin/commands/ask.md:25`)다.
- [확인] MCP 서버의 검색 index는 시작할 때 `<dataDir>/wiki/notes`만 읽는다 (`apps/mcp/src/context.ts:59,107`). v2 프로젝트의 `sources/research/`와 `context.md`는 MCP `search_wiki`에 잡히지 않는다. 웹 서버는 이 둘을 따로 index한다 (`apps/server/src/context.ts:342-363`).
- [확인] MCP 자신의 ingest 결과도 MCP 검색에 잡히지 않는다. compile executor는 `wiki/concepts/`에 쓴다 (`packages/core/src/storage/paths.ts:24-30`). MCP `search_wiki`, `ask_wiki`, `read_wiki_page`와 sqlite `reindex`는 `wiki/notes/`만 읽는다 (`apps/mcp/src/tools/read-wiki-page.ts:25`, `ask-wiki.ts:71`, `packages/core/src/graph/index/reindex.ts:31,94`). 웹 서버는 두 층을 모두 index한다 (`apps/server/src/context.ts:328`, `packages/core/src/storage/paths.ts:85-91`).
- [확인] MCP의 hybrid search는 `embedFn: async () => []`로 부른다 (`apps/mcp/src/tools/ingest-plan.ts:75`, `ingest-source.ts:42`). MCP 쪽에서는 vector 순위가 비어 있다.

#### 12. index·log 관리

입장: log는 코드가 결정적으로 append한다. index는 이름만 index이고 내용 카탈로그가 아니다.

- [확인] 모든 ops는 `logs/<date>.md`에 `## [YYYY-MM-DD HH:MM] <op> | <summary>` 한 줄을 남긴다 (`runner.ts:165-171`). query도 남긴다 (`ask.ts:13-31`). 하루 한 파일이다.
- [확인] `index.yaml`은 MCP `mindbase_rebuild_index`가 결정적으로 다시 만든다. 내용은 프로젝트 이름, 마지막 build 시각, 기여자별 파일 수, research page 수다 (`rebuild-index.ts:64-80`). 페이지별 한 줄 요약은 없다.
- [확인] 웹 ops engine은 `index.yaml`을 읽기만 하고 갱신하지 않는다 (`gather.ts:16`). 읽은 값은 어느 prompt에도 들어가지 않는다 (`recipes/*.ts`에 `indexYaml` 참조 없음). 웹에서는 프로젝트를 만들 때 한 번 쓰고 끝이다 (`packages/core/src/projects/store.ts:103-106`). 웹만 쓰는 사용자의 `index.yaml`은 낡는다.
- [확인] 웹 UI 주석은 `context.md`를 "INDEX.md의 v2 대체물"이라고 부른다 (`apps/web/src/components/WikiHome.tsx:6`).
- [확인] v1에는 LLM 도구 `add_to_index`와 결정적 helper `indexUpsertConcept`가 있다 (`packages/core/src/tools/schema.ts:67`, `packages/core/src/wiki/index-md.ts`).

#### 13. 포맷 표준 (OKF)

입장: OKF를 따르지 않는다.

- [확인] repo 어디에도 OKF 언급이 없다 (`grep -ri okf`가 lockfile 외에 0건).
- [확인] v2 research page에는 frontmatter가 아예 없다. trust, status, `stale_after` 같은 lifecycle 필드도 없다.
- [확인] v1 `schema/conventions.md`는 `provenance: {extracted, inferred, ambiguous}` 비율 필드를 권한다 (`schema/conventions.md:7-18`). 이 필드를 쓰거나 검사하는 executor 코드는 찾지 못했다.
- [확인] `[[wikilink]]`, YAML frontmatter(v1), 일반 markdown이라 Obsidian에서 열 수 있다는 점만 공통 관습과 맞는다.

#### 14. 규모·비용

입장: "개인 규모"를 전제로 모든 입력에 글자 상한을 둔다. 규모·비용 주장의 측정 근거는 repo에 없다.

- [확인] ops는 연산마다 LLM 호출 한 번(+ JSON 실패 시 재시도 한 번)이다 (`llm.ts:1-4,40-68`). 이유는 "multi-step tool loop가 로컬 모델에서 불안정하다"이다.
- [확인] 입력 상한은 다음과 같다.
  - contribute: `context.md` 전체(최대 400줄) + README + 관련 페이지 5개(각 200자) + slug 60개 (`routes/ops.ts:52-54`, `recipes/contribute.ts:36,57-63`)
  - build: 새 파일 30개 × 4,000자 (`gather.ts:11-12`)
  - lint: 페이지 40개 × 1,200자 + source 30개 목록 (`gather.ts:63-64`, `recipes/lint.ts:80`)
  - query: 50,000자 (`query.ts:201`)
  - v1 compile: tool loop 최대 10회, 문맥 예산 16,000 token (`l1.ts:182-183`)
- [확인] README는 "qwen3:14b는 대화형 작업에 약 30초"라고 적는다. 측정 데이터나 benchmark 스크립트는 repo에서 찾지 못했다.
- [확인] MCP 서버는 시작할 때마다 search index를 디스크에서 새로 만든다. 주석은 "personal-scale wikis에서는 싸다"고만 적는다 (`apps/mcp/src/context.ts:56`).
- [확인] 운영 규모(페이지 수, source 수) 주장은 없다.

#### 15. frosk1 비판 7가지에 대한 대응

| 비판 | 대응 | 판단 |
|---|---|---|
| 오류 누적 | 인용 자동 부착, lint 인용 검증, `context.md` snapshot | [추정] 부분 대응이다 — 사례: build가 이전 `context.md` + 새 파일만 보고 전체를 다시 쓴다 (`recipes/build.ts:23-28`). 원문에서 다시 도출하는 경로가 없어서 앞선 오류가 다음 build의 입력이 된다. |
| 부분 문맥 | 검색 결과 clip 보고, query log의 `read=N cited=M` | [확인] 약하다. build는 최신 30개 파일 각 4,000자, contribute는 관련 페이지 발췌 5개 각 200자, lint는 40페이지 각 1,200자만 본다 (#14). |
| 요약 손실 | source 층 append-only 보존, 답할 때 source 층 가중치 (`query.ts:113-117`) | [확인] 원문은 지워지지 않는다. 다만 `context.md` 400줄 상한이 압축을 강제한다. MCP 쪽 overflow는 잘린 꼬리를 research page로 옮긴다 (`apps/mcp/src/tools/atomic-write-context.ts:51-62`). 서버 쪽은 쓰기를 거부한다. 두 표면의 정책이 다르다. |
| 가짜 source of truth | 답의 인용마다 `source`/`wiki` 층 표시 (`query.ts:31-32`) | [확인] 장치는 있다. 그러나 README와 hook은 `context.md`를 "Synthesized truth", "curated truth"라고 부른다 (`apps/plugin/hooks/session-start:36`). 표현은 비판과 반대 방향이다. |
| 환각 병합 | contradiction은 원문 일치 인용 2개 필수, 중복 page 차단, "모순은 해결하지 말고 표시" 지시 | [확인] lint 쪽은 강하다. 병합 쪽은 약하다. v1 `merge`·`flag_contradiction`은 페이지를 고치지 않고 자율 compile의 audit_log에만 남는다 (#8). build의 "해결하지 마라"는 prompt뿐이다. |
| 운영 복잡도 | 연산당 LLM 한 번, action 4종으로 단순화 | [확인] 실제 복잡도는 매우 크다. layout 둘, 엔진 둘, MCP 도구 50개, 백그라운드 worker 7개다 (`apps/server/src/index.ts:188-211`). 도구 이름 불일치(#10), MCP 검색이 v2도 자기 ingest 결과(`wiki/concepts/`)도 못 보는 문제(#11)가 그 복잡도의 비용이다. |
| ingest 비용 | 로컬 Ollama 기본값, 연산당 한 번 호출 | [확인] 웹 contribute는 싸다. capture·RSS worker는 들어오는 항목마다 tool loop compile을 자동으로 돈다 (`capture-worker.ts:90`). cloud key를 쓰면 이 경로가 비용을 키운다. |

- 참고: frosk1 원문에는 8번째 항목(staleness)도 있다. 대응은 #8의 snapshot, 상태 chip, lint `stale`이다.

#### 16. 성숙도·차용 가능성

- [확인] 라이선스는 MIT다. 코드 차용에 제약이 없다.
- [확인] 테스트 파일은 115개다. ops engine 테스트는 가짜 adapter로 계획·적용·lint 검증을 확인한다 (`apps/server/src/ops/runner.test.ts:24-25`, 테스트 34개).
- [확인] CI는 core test, MCP 서버 build·기동, server test, web typecheck·build를 돈다 (`.github/workflows/ci.yml`). 실제 LLM으로 품질을 재는 eval은 없다.
- [확인] 런타임 의존성이 무겁다. core는 `better-sqlite3`(native), `@xenova/transformers`, `graphology`, `minisearch`를 쓴다. server는 여기에 `tesseract.js`, `sharp`, `pdfjs-dist`, `googleapis`, `jsdom` 등을 더한다 (`packages/core/package.json`, `apps/server/package.json`).
- [확인] 기여자 1명, 커밋 92개, 생성 5.5개월이다. 0.4.x beta를 스스로 표방한다.
- [추정] 통째로 가져다 쓰기보다 `apps/server/src/ops/` 한 폴더(약 1,300줄, 테스트 포함 약 2,200줄)를 떼어 오기 좋다 — 사례: 이 폴더의 외부 import는 `zod`, `node:fs`·`node:path`·`node:crypto`, core 타입 2개(`ChatChunk`, `ChatMessage`, `apps/server/src/ops/llm.ts:7`), 폴더 밖 `../lib/daily-entry` 하나다 (`runner.ts:16`).

## 장점

- [확인] LLM 출력과 디스크 쓰기 사이에 닫힌 action 어휘가 있다. 모델은 4종 JSON만 낼 수 있다. slug와 link 경로는 zod regex가, root escape와 줄 수는 executor가 검사한다 (`types.ts:10-21`, `executors.ts:15-84`). 사용자 층에 쓰는 action은 schema에 없다.
- [확인] lint의 경계 설계가 좋다. 코드로 셀 수 있는 것은 코드가 세고, 모델이 그 kind를 내면 버린다 (`runner.ts:583-600`). 모델의 모순 주장은 원문 글자 일치 인용 2개가 있어야 남는다 (`runner.ts:349-395`). 버린 수를 log에 `dropped=N`으로 남긴다 (`runner.ts:604-608`).
- [확인] 사용자 입력이 wiki 연산보다 먼저 source 층에 저장된다. LLM이 실패해도 글은 남고, 오류 메시지가 저장 위치를 알려 준다 (`runner.ts:190-241`).
- [확인] contribute에서는 인용을 모델이 잊어도 코드가 붙인다 (`runner.ts:149-160,215`). 그래서 다음 lint가 방금 쓴 페이지를 "출처 없음"으로 잡는 일을 막는다. build, research, autoSave에는 이 보정이 없다 (#5).
- [확인] "STATE RULE"이 prompt마다 들어 있다. SHA, 개수, "마지막 동기화" 같은 움직이는 값은 쓰지 말고 그 값이 있는 위치를 가리키라는 규칙이다 (`recipes/contribute.ts:34`). wiki가 낡는 흔한 원인을 쓰는 시점에 막는다.
- [확인] 동시 contribute 계획 사이의 중복 page 생성을 예약 Map으로 막는다 (`runner.ts:80-140`). 계획 후 LLM이 생각하는 동안 바뀐 디스크 상태를 다시 확인한다 (`runner.ts:211-214`). build, research, autoSave는 이 guard 밖이다 (#10).
- [확인] query 결과가 "얼마나 읽었고 얼마나 잘렸는지"를 보여 준다 (`query.ts:294`, `ask.ts:22-25`). 부분 문맥 문제를 숨기지 않는다.

## 단점

- [확인] "모든 쓰기를 사람이 승인한다"는 README 주장은 웹 contribute에만 맞다. build, research, autoSave, capture·RSS worker, MCP `ingest_source`, MCP `ingest_execute`(기본 승인)는 승인 없이 쓴다 (#9 표). README는 build·research에도 "approval cards"가 있다고 적지만 웹 UI에는 없다 (`README.md:146`, `OpRun.tsx:90-98`).
- [확인] 엔진과 layout이 둘로 갈라져 있다. plugin의 ingest는 프로젝트 범위가 없는 `<dataDir>/wiki/concepts/`에 쓴다 (`apps/mcp/src/context.ts:43` `FileStore(dataDir)`, `packages/core/src/storage/paths.ts:24-30`). 웹은 v2 프로젝트 폴더에 쓴다 (`apps/server/src/context.ts:106` `ProjectScopedStore`). 같은 plugin 안에서도 `mindbase_contribute`와 builder는 v2 프로젝트에 쓴다 (`apps/mcp/src/tools/contribute.ts:44`).
- [확인] MCP 서버는 자기 ingest가 만든 page를 검색하지 못한다. 쓰는 곳은 `wiki/concepts/`, 검색·읽기·sqlite reindex는 `wiki/notes/`다 (#11). 실행해 보지는 않았다.
- [추정] Claude Code로 ingest한 page는 웹 프로젝트 화면에도 보이지 않는다 — 사례: MCP는 `<dataDir>/wiki/concepts/`, 서버는 `projects/<id>/wiki/...`를 본다. `migrateLegacyData`는 `projects/default/meta.json`이 없을 때 한 번만 돈다 (`packages/core/src/projects/migration.ts:80-83`). 옮겨도 `projects/default`라는 v1 프로젝트로 간다. 실행해 보지는 않았다.
- [확인] plugin `/mb:lint`는 v2 프로젝트를 검사하지 않는다. `run_wiki_health`는 `projectId`를 받지 않고 전역 v1 store만 본다 (#10). 원문 일치 인용을 요구하는 lint는 웹에서만 쓸 수 있다.
- [확인] plugin contributor의 승인은 실행될 계획을 보기 전에 받는다. 사람이 승인한 말로 된 계획과 `ingest_plan`이 새로 만든 계획을 대조하는 단계가 없다 (`apps/plugin/agents/contributor.md:24-25`).
- [확인] plugin sub-agent 허용 목록의 도구 이름 9건(서로 다른 이름 7종)이 실제 MCP 이름과 다르다. slash command와 agent 본문도 없는 이름을 부른다 (#10). 이를 잡는 검사 스크립트가 없다.
- [확인] v2 action 어휘에 "기존 research page 본문 갱신"이 없다 (`types.ts:16-21`). 새 정보는 `context.md`에 append되거나 새 page가 된다. 그래서 개념 page가 소스를 따라 자라지 않는다.
- [확인] 원자성과 복원이 약하다. 서버 쓰기는 tmp+rename이 아니다. snapshot은 전체 덮어쓰기에만 있고 복원 도구가 없다. 계획 적용 때 `context.md` 버전 확인이 없다 (#10).
- [확인] 문서와 코드가 어긋난다. `CLAUDE.md`의 gap 목록은 이미 구현된 lint와 file-back을 없다고 적는다. curator는 "read-only"라는데 그 curator에게 지정된 `run_wiki_health`는 파일을 고친다 (`run-wiki-health.ts:18-22`).
- [확인] v1 `merge`와 `flag_contradiction`은 페이지나 edge를 바꾸지 않는다 (`executor.ts:453-472`). 모델에게는 성공으로 보인다. 자율 `compileL1`은 audit_log에 남기지만 MCP 승인 경로는 그것도 남기지 않는다. merge를 처리하는 review queue는 없다 (#8).
- [확인] 범위가 넓다. SRS, daily brief, RSS, Google Drive, 모바일 앱, OCR, 기기 pairing까지 한 저장소에 있다. llm-wiki 핵심과 무관한 코드가 많다.

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

- 문제: LLM이 아무 파일이나 쓸 수 있으면 사용자 층이 오염된다. → 제안: 쓰기를 닫힌 action 어휘(discriminated union)로만 받고, 경로 regex와 root escape 검사를 executor에 둔다. → 근거: `apps/server/src/ops/types.ts:12-21`, `executors.ts:15-21`. → 포기하는 것: 모델이 새 종류의 편집을 즉흥적으로 할 자유.
- 문제: LLM lint가 없는 모순을 지어낸다. → 제안: 모순·stale finding에 원문 글자 일치 인용을 요구하고 검증 못 한 finding을 버린 뒤 버린 수를 log에 남긴다. → 근거: `runner.ts:349-395,604-608`. → 포기하는 것: 문장을 바꿔 말한 모순(paraphrase)은 놓친다.
- 문제: 코드로 셀 수 있는 lint 항목을 모델에게 맡기면 틀린다. → 제안: 결정적 kind 목록을 두고 모델 출력에서 그 kind를 걸러 낸다. → 근거: `recipes/lint.ts:26-32`, `runner.ts:583-586`. → 포기하는 것: 없다. 다만 orphan처럼 셀 수 있는 항목은 처음부터 결정적 쪽에 둔다.
- 문제: 모델이 인용을 빠뜨린다. → 제안: 쓰기 직전에 코드가 `[@source path]`를 덧붙인다. → 근거: `runner.ts:149-160`. → 포기하는 것: 인용 위치가 문장이 아니라 page 끝이라 정밀도가 낮다.
- 문제: LLM 호출이 실패하면 사용자 입력이 사라진다. → 제안: 입력을 source 층에 먼저 append하고 그다음 wiki 연산을 한다. 재전송은 멱등으로 만든다. → 근거: `apps/server/src/lib/daily-entry.ts`, `runner.ts:190-241`. → 포기하는 것: 버린 시도도 source 층에 남는다.
- 문제: wiki가 SHA·개수 같은 움직이는 값을 박제해 낡는다. → 제안: 쓰기 prompt마다 "STATE RULE"을 넣는다. → 근거: `recipes/contribute.ts:34`. → 포기하는 것: 없다.
- 문제: 답이 무엇을 읽고 무엇을 잘랐는지 보이지 않는다. → 제안: query log에 `read / cited / sent / retrieved / clipped`를 남긴다. → 근거: `ask.ts:13-31`, `query.ts:294`. → 포기하는 것: log 크기.

### 피할 것

- 필수: 승인 원칙을 표면마다 다르게 두지 않는다. 승인 gate는 executor 앞 한 곳에 두고, 모든 쓰기 경로가 그곳을 지나게 한다. 근거: 이 repo는 승인 여부가 경로 10개에서 제각각이다 (#9).
- 필수: 같은 wiki에 쓰는 엔진을 둘 두지 않는다. 근거: v1·v2 엔진이 서로 다른 디렉터리에 써서 검색 범위가 갈렸다 (#11, `apps/mcp/src/context.ts:59`).
- 필수: 에이전트 허용 목록의 도구 이름을 실제 등록 목록과 대조하는 검사를 CI에 둔다. 근거: 이름 불일치가 lint 경로를 막았을 가능성이 크다 (#10).
- 제안: mtime 하나로 "반영됨"을 판정하지 않는다. source별 처리 기록(manifest)을 둔다. 근거: append 연산이 `context.md` mtime을 올리면 미반영 source가 반영된 것으로 보인다 (#4).
- 제안: 전체 덮어쓰기 계획은 계획 시점 버전(hash)을 함께 들고 가서 적용 때 비교한다. 근거: `runner.ts:244-262`에 이 검사가 없다.
- 제안: snapshot을 남긴다면 복원 명령도 함께 만든다. 아니면 git commit으로 대신한다. 근거: snapshot을 읽는 코드가 없다 (#10).
- 참고: 결과를 처리할 곳 없이 성공만 돌려주는 도구(`merge`, `flag_contradiction`)는 모델에게 거짓 신호를 준다. 처리할 queue가 없으면 도구를 빼는 편이 낫다.
- 제안: 쓰는 경로와 읽는(검색·index) 경로를 같은 path helper에서 뽑는다. 근거: 이 repo의 MCP는 `wiki/concepts/`에 쓰고 `wiki/notes/`만 읽는다 (#11).
- 제안: 사람 승인은 실제로 실행될 계획에 받는다. 근거: plugin contributor는 승인 뒤에 실행 계획을 새로 만든다 (#9).

## 확인하지 못한 것

- 실제로 실행하지 않았다. 도구 이름 불일치가 curator를 막는지는 Claude Code에서 `/mb:lint`를 돌려 보면 알 수 있다.
- MCP로 ingest한 v1 page가 웹 프로젝트 화면과 MCP `search_wiki`에 정말 안 보이는지 실행해 보지 않았다. `mindbase-mcp`와 `mindbase-app`를 같은 `MINDBASE_DATA_DIR`로 띄우고 `ingest_execute` 후 `search_wiki`와 웹 트리를 보면 알 수 있다.
- `compileL1Plan`의 dry-run 계획과 실제 실행 결과가 얼마나 어긋나는지 모른다. 사용자가 `create_concept`를 거절하고 같은 concept의 `append_to_concept`만 승인하는 경우를 실행해 보면 알 수 있다.
- README의 "qwen3:14b 약 30초", "Glimmer는 모순 문장을 정확히 인용한다"는 측정 근거를 찾지 못했다.
- `compileL2`(v1 lint)의 동작과 자동 적용 범위는 읽지 않았다 (`packages/core/src/compile/l2.ts`).
- android, ios, browser-ext 앱은 범위 밖이라 읽지 않았다.
- shallow clone이라 커밋 이력으로 설계 변화(2026-05-25 pivot 전후)를 추적하지 않았다. `docs/pivot-plan-2026-05-25.md`를 읽으면 v1 → v2 전환 의도를 더 볼 수 있다.

## 검증 기록

코드를 읽어서 대조했다. 실행은 하지 않았다.

- `ingest-execute.ts:220` 인용을 고쳤다. 파일은 115줄이다. `compileL1Execute` 호출은 56줄이다.
- "plugin ingest는 v1 `wiki/notes`에 쓴다"를 고쳤다. compile executor는 `wiki/concepts/`에 쓴다 (`paths.ts:24-30`).
- 새로 적었다: MCP 검색·`read_wiki_page`·sqlite reindex는 `wiki/notes/`만 읽어서 MCP ingest 결과를 못 본다 (#11, #단점).
- 새로 적었다: `run_wiki_health`는 `projectId`가 없어 plugin lint가 v2 프로젝트를 검사하지 않는다 (#한 바퀴 흐름, #10, #단점).
- 새로 적었다: plugin contributor는 `ingest_plan` 전에 승인을 받아서, 승인한 계획과 실행 계획이 다르다 (#한 바퀴 흐름, #9, #단점).
- #9 표에 MCP `ingest_source`(승인 없음)를 더했다. file-back도 빠진 id를 승인으로 본다고 적었다. 웹 contribute checkbox가 처음에 모두 체크된다고 적었다.
- "확인하지 못한 것"의 웹 build·research 확인 dialog 항목을 지웠다. `OpRun.tsx`를 읽었고 build는 자동 시작, research는 결과 승인 없음을 확인했다. README의 "approval cards" 주장과 어긋난다고 적었다.
- `curator.md:14`는 `run_wiki_health`가 아니라 `mindbase_run_wiki_health`를 지시한다. 흐름 6번 문장을 고쳤다.
- 허용 목록 이름 불일치를 "5건 이상"에서 "9건(7종)"으로 구체화했다. slash command·agent 본문의 없는 이름도 더했다.
- "인용은 모델이 잊어도 코드가 붙인다"를 contribute 한정으로 좁혔다. build·research·autoSave에는 `ensureCitations`가 없다.
- "중복 slug 차단"을 contribute 계획끼리로 좁혔다. 다른 경로는 executor가 `-2`를 붙여 새로 만든다고 적었다.
- `flag_contradiction`·`merge` "아무것도 저장하지 않는다"를 고쳤다. 자율 `compileL1`은 audit_log에 남긴다. MCP 승인 경로만 흔적이 없다.
- capture worker "`failed`를 다시 집는다"를 고쳤다. failed 폴더는 자동 재시도 대상이 아니다. `processing` 고착은 코드를 읽어 `[확인]`으로 올렸다.
- 새로 적었다: build·plugin builder 입력에서 `sources/raw/`가 빠진다. lint `uncited_source`는 raw도 반영됨으로 센다.
- 새로 적었다: lint 40페이지 제한은 디렉터리 순서이고 결정적 검사에도 걸린다. 같은 날 재실행하면 dismiss 기록이 사라진다.
- 새로 적었다: `index.yaml`은 읽기만 하고 prompt에 넣지 않는다. MCP hybrid search는 embedding이 비어 있다.
- daily-entry 멱등성을 "마지막 글과 같을 때만"으로 좁혔다.
- 줄 번호를 고쳤다: `executors.ts:81`→`80`, `hybrid.ts:1-40`→`129-147`, `executor.ts:454-471`→`453-472`.
- ops 폴더 규모를 1,400/2,300줄에서 약 1,300/2,200줄로 고쳤다. import 목록에 `../lib/daily-entry`를 더했다.
- 피할 것에 "쓰기·읽기 경로를 같은 helper에서 뽑기"와 "실행될 계획에 승인 받기"를 더했다.

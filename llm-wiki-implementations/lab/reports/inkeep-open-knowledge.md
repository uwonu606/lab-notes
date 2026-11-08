# inkeep/open-knowledge — wiki 규칙은 skill 프롬프트에 두고, IDE·MCP 서버는 읽기 맥락과 쓰기 안전만 결정적으로 보장한다

## 한눈에

| 항목 | 값 |
| --- | --- |
| URL | https://github.com/inkeep/open-knowledge |
| clone commit | `7e67576` (shallow clone, 이력 1개) |
| 별 · 최근 push | 4,507 · 2026-10-10 (gh api 확인) |
| 라이선스 | GPL-3.0 (모든 package.json이 `GPL-3.0-or-later`), 기여에 CLA 요구 |
| 형태 | Electron 데스크톱 앱 + 웹 UI + MCP 서버 + `ok` CLI. llm-wiki는 그 위의 starter pack 하나(`knowledge-base`) |
| 코드 규모 | 테스트 제외 TS 기준 app 25.4만 줄, server 13.2만 줄, desktop 6.4만 줄, core 5.9만 줄, cli 2.8만 줄. 테스트 파일 3,067개 |
| llm-wiki 부분의 규모 | pack 정의 약 100줄(`packages/server/src/seed/starter.ts:36-135`) + SKILL.md 3개(95·380·167줄) + 플랫폼 skill의 ingest 절차 243줄 |

이 저장소는 범용 markdown IDE다. "LLM wiki"는 IDE가 제공하는 기능(MCP 도구, CRDT 공동 편집, backlink index, shadow git)을 프롬프트로 엮은 사용 패턴이다. 그래서 분석 대상을 두 층으로 나눴다. 하나는 pack이 심는 skill과 시드 파일이다. 다른 하나는 그 skill이 부르는 서버 도구다.

## 한 바퀴 흐름

0. **Seed.** 사용자가 앱에서 Knowledge base 카드를 누르거나 `ok seed --pack knowledge-base`를 실행한다.
   - `applySeed`가 `external-sources/`·`research/`·`articles/` 폴더를 만든다 (`packages/server/src/seed/apply.ts:67-77`).
   - 각 폴더에 `.ok/frontmatter.yml`(title·description·tags 세 필드)과 `.ok/templates/<name>.md`를 쓴다 (`packages/server/src/seed/starter.ts:1498-1509`, `apply.ts:79-105`).
   - 루트에 `log.md`를 쓴다 (`starter.ts:127-135`).
   - 이미 있는 파일은 건너뛴다. `wx` 플래그로 덮어쓰기를 막는다 (`apply.ts:91-100`).
   - SKILL.md 3개를 에이전트 편집기의 skills 폴더에 설치한다 (`apply.ts:107`).
   - 이 pack은 `requiredPlugins`가 없다. 그래서 markdownlint·frontmatter·OKF lint 어느 것도 켜지지 않는다 (`starter.ts:1340-1348`, `apply.ts:121`, `packages/core/src/markdown/lint/plugins.ts:55`, `:78`, `:99`).
1. **Ingest.** 사용자가 "ingest this: URL"이라고 말한다.
   - 에이전트가 플랫폼 skill의 절차를 읽는다 (`packages/server/assets/skills/project/references/ingest-and-sources.md`).
   - `exec("grep -rln <url>")`로 중복을 확인한다 (`ingest-and-sources.md:14`).
   - fetch는 OK 도구가 아니다. 에이전트 호스트의 `WebFetch`나 자기 shell의 `curl`이 한다 (`ingest-and-sources.md:65-77`, `:109`).
   - MCP `write` 도구로 `external-sources/<slug>.md`를 만든다 (`packages/server/src/mcp/tools/write.ts:89-97`).
   - 서버는 Yjs CRDT 문서를 거쳐 임시 파일에 쓰고 rename으로 바꿔 넣는다 (`packages/server/src/persistence.ts:1802`, `:1828`).
   - 같은 쓰기에서 backlink index가 갱신되고 (`packages/server/src/backlink-index.ts:1469`), 응답에 `brokenLinks`가 실린다 (`write.ts:710-720`).
2. **Research.** 사용자가 "research X"라고 말하면 `research-with-sources` skill이 돈다.
   - `exec`의 grep·ls·cat으로 기존 문서를 훑는다 (`packages/server/assets/skills/packs/knowledge-base/research/SKILL.md:105-126`).
   - `exec`는 just-bash의 읽기 전용 OverlayFs 안에서 명령을 돌린다 (`packages/server/src/bash/index.ts:51-63`).
   - 결과 경로마다 frontmatter를 붙인다. 여러 경로면 backlink 수와 comment 수를 더한다 (`packages/server/src/mcp/tools/exec.ts:550-563`).
   - backlink 목록·shadow repo 이력·git 이력은 단일 파일 `cat`일 때만 붙는다 (`exec.ts:503`, `:510`, `packages/server/src/content/enrichment.ts:426-463`).
   - rubric을 사용자에게 승인받는다 (`research/SKILL.md:154-158`).
   - 소스를 하나씩 ingest하고, 글 뼈대를 먼저 쓴 뒤 절마다 `edit`로 채운다 (`research/SKILL.md:67-74`).
   - `audit`으로 검증하고 (`research/SKILL.md:339`), `log.md`에 한 항목을 덧붙인다 (`knowledge-base/SKILL.md:72-91`).
3. **Query.** 사용자가 질문한다.
   - 에이전트가 `search`와 `exec`를 번갈아 부른다 (`packages/server/assets/skills/project/references/corpus-qa.md:3`).
   - `search`는 Orama 기반 BM25·제목 가중·최신성 점수를 쓴다 (`packages/core/src/search/workspace-search.ts:1`, `:374`).
   - 답은 채팅으로 낸다. 저장은 네 조건을 다 만족할 때 제안만 한다 (`corpus-qa.md:5-12`).
4. **Consolidate.** "결정이 났는가"를 묻는 STOP gate를 지난다 (`packages/server/assets/skills/packs/knowledge-base/consolidate/SKILL.md:21-31`).
   - `articles/<slug>.md`를 `status: stable`과 `supersedes:`로 쓴다.
   - 원래 research 문서를 `status: deprecated`와 `superseded_by:`로 고친다 (`consolidate/SKILL.md:143-152`).
5. **Lint.** 결정적 검사는 세 도구다.
   - `links`: backlinks·forward·dead·orphans·hubs·suggest (`packages/server/src/mcp/tools/links.ts:20-28`).
   - `audit`: markdownlint·frontmatter·OKF·깨진 링크 (`packages/server/src/mcp/tools/audit.ts:27-33`).
   - `lint({fix:true})`: markdownlint 자동 수정 (`packages/server/src/mcp/tools/lint.ts:35-39`).
   - 세 lint plugin(markdownlint·frontmatter·OKF)은 모두 기본값이 꺼져 있다 (`packages/core/src/markdown/lint/plugins.ts:55`, `:78`, `:99`). knowledge-base pack은 아무것도 켜지 않는다. 그래서 기본 설정의 `audit`은 본문 깨진 링크만 본다.
   - 모순·낡은 주장 찾기는 문서가 "에이전트에게 부탁하라"고만 적는다 (`docs/content/workflows/karpathy-llm-wiki.mdx:244-246`).

## 축별 분석

#### 1. 실행 형태

입장: 데스크톱 앱·IDE + MCP 서버다. llm-wiki 자체는 prompt-only skill 묶음이다.

- [확인] 서버 도구 19개가 MCP로 노출된다 (`packages/server/src/mcp/tools/index.ts:39-179`, `packages/server/assets/skills/project/SKILL.md:25-45`).
- [확인] `ingest`·`research`·`consolidate`는 도구가 아니다. skill 안의 절차다 (`docs/content/workflows/karpathy-llm-wiki.mdx:174`).
- [확인] server·core·desktop 소스에서 chat completion API를 직접 부르는 코드를 찾지 못했다. LLM은 MCP로 붙는 외부 에이전트(Claude Code, Cursor 등)다.
- [확인] 예외는 선택형 embeddings 호출이다 (`packages/server/src/embeddings/`).
- [확인] 앱은 ACP(agent client protocol)로 Claude Code·Codex·Gemini 같은 에이전트 CLI를 앱 안에서 띄울 수 있다 (`packages/server/src/acp/harness-availability.ts:23-30`, `packages/server/package.json`의 `@agentclientprotocol/sdk`). 이 경로에서도 LLM은 외부 프로세스다.

#### 2. 규칙의 위치

입장: wiki 규율은 거의 전부 프롬프트에 있다. 코드가 강제하는 것은 "쓰기 경로의 안전"이지 "wiki 규율"이 아니다.

- [확인] 프롬프트가 맡는 규칙: `external-sources/` 불변, 모든 주장에 출처, `sources:`와 본문 링크 일치, status 흐름, supersede 체인, log 기록 (`knowledge-base/SKILL.md:53-66`, `:72-91`).
- [확인] "Karpathy의 CLAUDE.md를 폴더별로 나눴다"는 주장은 사실이다. 폴더의 `.ok/frontmatter.yml` description이 `exec ls` 결과에 실려 에이전트에게 간다 (`enrichment.ts:587-591`, `packages/server/src/mcp/tools/exec.ts:186-229`).
- [확인] 그 파일은 title·description·tags만 담는다. 필드 schema가 아니다 (`starter.ts:1500-1509`).
- [확인] 폴더 frontmatter는 자식 문서로 cascade되지 않는다 (`project/SKILL.md:98`).
- [확인] `external-sources/` 불변을 막는 write gate는 없다. 서버 코드에서 `external-sources`는 seed와 `init-project.ts`에만 나온다.
- [확인] frontmatter JSON schema 검사는 존재한다. 다만 기본값이 꺼져 있다 (`packages/core/src/markdown/lint/plugins.ts:72-78`). markdownlint와 OKF도 기본값이 꺼져 있다 (`plugins.ts:55`, `:99`, `docs/content/reference/configuration.mdx:38`).
- [확인] 코드 강제 항목: exec 명령 allowlist (`packages/server/src/bash/parse-command.ts:277-288`, `:393`), 읽기 전용 mount (`bash/index.ts:57-62`), 충돌 문서 쓰기 거부 (`packages/server/src/conflict-errors.ts:67`, `api-extension.ts:2484`), 동시 덮어쓰기 거부 (`packages/server/src/agent-sessions.ts:163`, `concurrent-overwrite-refused-error.ts:7-13`).
- [확인] 앱이 띄운 에이전트(ACP·터미널 handoff)에는 코드 gate가 하나 더 있다. `delete`·`move`·`share_link`·`install`·`import`는 매번 사람 승인을 묻는다. `write`·`edit`는 기본값으로 자동 승인된다 (`packages/core/src/handoff/terminal-launch.ts:269-275`, `packages/server/src/acp/permissions.ts`의 `decide`). wiki 규율과는 무관한 파괴적 동작 gate다.
- [확인] 프롬프트끼리 어휘가 어긋난 자리가 있다. 이를 잡는 검사는 없다.
  - research 템플릿은 `created:`·`author:`를 쓴다 (`starter.ts:93-94`). research skill의 frontmatter와 Step 7 검증은 `date:`를 요구한다 (`research/SKILL.md:248`, `:337`).
  - article 템플릿은 `authored:`를 쓴다 (`starter.ts:114`). consolidate skill은 `date:`를 쓴다 (`consolidate/SKILL.md:88`).
  - 플랫폼 skill은 research 결과를 아직 `status: provisional`로 적는다 (`project/SKILL.md:130`). pack은 `draft`를 쓴다.
  - `ok init`이 쓰는 config 주석은 `ingest`·`research`·`consolidate`를 "MCP tool"이라 부른다 (`packages/server/src/init-project.ts:93-100`). 그런 도구는 없다.
- [추정] 플랫폼 skill은 "native 도구로 md를 읽지 말라"는 STOP 규칙에 긴 분량을 쓴다 (`project/SKILL.md:55-70`). 이 규칙이 지켜져야 attribution과 CRDT가 성립한다. 코드로 막을 수 없는 지점을 프롬프트로 메운 사례다 — 사례: 이 STOP 규칙 1개.

#### 3. 저장 구조

입장: 3층 디렉터리 + 문서별 frontmatter + 폴더별 `.ok/`. 파생 상태는 앱 내부 캐시와 shadow git에 둔다.

- [확인] 디렉터리: `external-sources/`(원문) → `research/`(잠정) → `articles/`(확정), 루트 `log.md` (`starter.ts:36-64`).
- [확인] 페이지 종류는 `type` 값으로 나뉜다. `source`·`research-note`·`article`이다 (`starter.ts:71`, `:89`, `:110`).
- [확인] source frontmatter: `source_url`, `date_fetched`, `preservation`(text-extracted·binary·text-only), binary면 `source_path`·`media_type`·`bytes`·`sha256` (`ingest-and-sources.md:117-137`, `:152-169`).
- [확인] research frontmatter: `status: draft`, `sources: [{resource: ../external-sources/x.md}]`, `date`, `tags` (`research/SKILL.md:240-257`).
- [확인] article frontmatter: `status: stable`, `supersedes: [...]` (`consolidate/SKILL.md:80-96`). 밀려난 research는 `status: deprecated`, `superseded_by:`를 얻는다.
- [확인] 같은 묶음 안 문서는 `cluster:` 값을 공유하라고 한다. 그래프 색칠용이다 (`knowledge-base/SKILL.md:19`).
- [확인] 파생 상태 파일: backlink index는 `.ok/local/cache/<branch>/backlinks.json`에 원자적으로 저장된다 (`backlink-index.ts:1354`, `:2151-2161`).
- [확인] 문서 이력은 shadow git repo에 writer별 `refs/wip/<branch>/` ref로 쌓인다 (`packages/server/src/shadow-repo.ts:242`, `:429`).
- [확인] index.md는 만들지 않는다. manifest·ledger 같은 wiki 전용 상태 파일도 없다.

#### 4. Ingest

입장: 원문 보존만 하는 얇은 ingest다. 합성은 사람이 요청할 때 research로 미룬다.

- 사람 참여: [확인] 사용자가 URL마다 "ingest this"를 말한다 (`karpathy-llm-wiki.mdx:176-182`). ingest가 끝나면 research로 넘어갈지 묻는다 (`ingest-and-sources.md:221`).
- 증분·변경분: [확인] binary 소스는 재ingest 때 sha256을 비교한다. 다르면 날짜 붙은 형제 파일을 새로 만들고 `supersedes:`로 잇는다 (`ingest-and-sources.md:200-213`). 이 비교는 에이전트가 shell로 한다. 코드가 아니다.
- [확인] 이 절차는 binary에만 적힌다. Step 5는 "`external-sources/<slug>.<ext>` already exists when you reach Step 1b"로 시작한다 (`ingest-and-sources.md:202`). text wrapper frontmatter에는 `sha256` 필드가 없다 (`:152-169`). 텍스트 소스가 바뀌었는지 판단하는 규칙은 Step 0의 "already present with current content" 한 줄뿐이다 (`:14`).
- queue·crash 복구: [확인] 코드 queue는 없다. "소스를 받자마자 하나씩 ingest하고 글을 절마다 쓰라"는 규칙이 복구 수단이다 (`research/SKILL.md:67-74`, `project/SKILL.md:76`).
- 자동 감시: [확인] chokidar file-watcher가 새 파일을 index에 반영한다 (`ingest-and-sources.md:103`). 감시가 ingest 절차를 시작하지는 않는다.
- 멀티포맷: [확인] binary는 변환하지 않고 바이트를 보존한다. OCR·전사는 비목표다 (`ingest-and-sources.md:239`). 텍스트는 fetch 결과에서 boilerplate만 걷는다 (`ingest-and-sources.md:148`).
- 소스 하나가 건드리는 페이지: [확인] wrapper 1개(+binary 1개)와 선택적 이웃 1~3개다 (`ingest-and-sources.md:225-231`). Karpathy의 "10~15페이지"와 다르다.
- 안전 gate: [확인] SSRF 방지 curl 플래그, 100MB 상한, 실행 파일 확장자 차단, slug 정규식이 있다 (`ingest-and-sources.md:39`, `:49-55`, `:61`, `:69-77`). 다운로드 단계에서는 전부 프롬프트다. curl은 OK 밖에서 돈다.
- [확인] 실행 파일 확장자 목록 자체는 코드에도 있다 (`packages/core/src/constants/upload.ts:70`). 쓰임새는 asset 서빙과 desktop asset allowlist다 (`packages/server/src/asset-serve-middleware.ts:167`, `packages/desktop/src/main/asset-allowlist.ts:116`). 에이전트의 curl 다운로드를 막지는 않는다. skill도 "the runtime backstop is desktop-only"라고 적는다 (`ingest-and-sources.md:49`).

#### 5. 근거 추적 단위

입장: 페이지 단위 출처다.

- [확인] research는 frontmatter `sources:` 목록과 본문 inline 링크로 소스 문서를 가리킨다 (`research/SKILL.md:222-224`, `:316`).
- [확인] 원문 글자 일치, 줄 범위, claim ledger는 없다.
- [확인] 주장과 소스의 대응을 검사하는 코드는 없다. `audit`은 링크가 실재하는지만 본다 (`audit.ts:27-30`).
- [확인] 그 링크 검사도 본문 링크만 대상이다. `BacklinkIndex`는 frontmatter를 떼어 내고 본문에서만 링크를 뽑는다 (`backlink-index.ts:1471-1482`). 그래서 frontmatter `sources: [{resource}]`·`supersedes:`·`superseded_by:` 경로가 실재하는지는 어떤 코드도 보지 않는다. OKF `frontmatter-provenance`도 모양만 검사한다 (`docs/content/plugins/okf.mdx:47`).
- [확인] 체인은 article → `supersedes` → research → `sources` → external-source → `source_url`/`sha256`로 이어진다 (`knowledge-base/SKILL.md:57`).
- [확인] "근거 없으면 `(TODO: needs source)`로 표시하라"는 규칙이 있다 (`project/SKILL.md:91`).

#### 6. Link

입장: 링크는 LLM이 markdown 링크로 건다. backlink·그래프는 서버가 결정적으로 추출·관리한다.

- [확인] 링크 형식은 표준 markdown 링크다. `[[wiki]]`는 legacy다 (`project/SKILL.md:94`).
- [확인] `BacklinkIndex`가 문서 저장마다 링크를 파싱해 역방향 index를 갱신한다 (`backlink-index.ts:1235`, `:1469`).
- [확인] 서버 시작 때 디스크와 대조해 재구성한다 (`backlink-index.ts:2225`, `:2360`).
- [확인] orphans·hubs 계산이 결정적이다 (`backlink-index.ts:1608`, `:1635`).
- [확인] `links({kind:'suggest'})`는 다른 문서의 제목·alias가 본문에 링크 없이 나오는 자리를 찾는다 (`packages/server/src/suggest-links.ts:51-52`, `:260`). 실제 링크 삽입은 에이전트가 `edit`로 한다 (`links.ts:25`).
- [확인] 쓰기마다 깨진 링크가 응답에 실린다. 쓰기는 막지 않는다 (`packages/server/src/link-advisory-policy.ts:28-32`).
- [확인] `log.md`의 깨진 링크는 기본 설정에서 경고에서 빠진다 (`link-advisory-policy.ts:15-20`).

#### 7. Lint

입장: 결정적 lint는 형식·링크만 본다. 내용 lint는 LLM에게 맡기고 절차도 없다.

- [확인] 결정적 검사: markdownlint(opt-in), frontmatter schema(opt-in), OKF 규칙(opt-in), 깨진 내부 링크, orphan·hub (`audit.ts:28`, `links.ts:20-28`).
- [확인] markdownlint도 기본값이 꺼져 있다 (`packages/core/src/markdown/lint/plugins.ts:55`, `docs/content/reference/configuration.mdx:38`). knowledge-base pack을 seed한 그대로면 `audit`에서 도는 것은 본문 깨진 링크 검사뿐이다. `lint`는 `ran: []`를 돌려줄 것이다 (`project/SKILL.md:47`).
- [확인] 자동 수정은 markdownlint의 fixable 규칙뿐이다 (`lint.ts:36`). markdownlint를 켜야 의미가 있다. OKF 규칙은 자동 수정이 없다 (`docs/content/plugins/okf.mdx:35`). 깨진 링크는 에이전트가 고친다 (`audit.ts:32`).
- [확인] 모순·낡은 주장·빠진 상호참조를 찾는 전용 skill이나 도구는 없다. 문서는 "monthly로 에이전트에게 물어라"고 적는다 (`karpathy-llm-wiki.mdx:244-246`).
- [확인] commit gate는 vault에 설치되지 않는다. `ok audit` CLI는 문제가 있으면 non-zero로 끝나서 CI gate로 쓸 수 있다 (`packages/cli/src/commands/audit.ts:147`).
- [확인] research 마지막 단계는 `audit` 결과를 깨끗하게 만들라고 한다 (`research/SKILL.md:339`). 이것도 프롬프트 gate다.

#### 8. stale·모순 처리

입장: supersede 체인 + 사람 결정 gate다. drift 감지 코드는 없다.

- [확인] 확정 지식은 research를 지우지 않고 deprecated로 남긴다 (`consolidate/SKILL.md:143-152`).
- [확인] binary 소스가 바뀌면 날짜 형제 파일로 supersede한다 (`ingest-and-sources.md:206-213`). 텍스트 소스에는 이 절차가 적혀 있지 않다 (#4).
- [확인] `supersedes`·`superseded_by`·`immutable`을 읽는 서버·core 코드는 없다. grep 결과가 seed 템플릿뿐이다. 체인이 끊기거나 한쪽만 적혀도 알리는 것이 없다.
- [확인] research를 덮어쓰지 말고 Path C로 고치거나 후속 문서를 만들라고 한다 (`research/SKILL.md:380`).
- [확인] 모순은 research에 "가장 값진 부분"으로 기록하라고 한다 (`research/SKILL.md:216`). ingest 직후 기존 문서와의 긴장을 채팅으로 알리라고 한다 (`ingest-and-sources.md:220`).
- [확인] OKF plugin에는 `stale_after`·`verified` 필드의 모양 검사가 있다 (`okf.mdx:47`). 날짜가 지났는지 알리는 코드는 찾지 못했다. knowledge-base pack은 이 plugin을 켜지 않는다.
- [추정] `articles/`가 낡았는지 판단할 신호는 사람의 다음 결정뿐이다. 근거는 drift를 감지하는 코드나 skill 단계를 찾지 못한 것 하나다.

#### 9. 사람 개입

입장: plan 승인 + 공동 편집이다. 매 쓰기 승인은 아니다.

- [확인] research는 rubric 승인 STOP gate를 둔다 (`research/SKILL.md:154-158`).
- [확인] consolidate는 "결정이 났는가" STOP gate를 둔다 (`consolidate/SKILL.md:21-31`).
- [확인] 단계 사이를 자동으로 잇지 말라고 한다 (`knowledge-base/SKILL.md:47`). "멈추지 말고 진행" 같은 세션 지시도 이 gate를 넘지 못한다고 적는다 (`knowledge-base/SKILL.md:49`).
- [확인] headless 모드가 있다. rubric을 제안하고 바로 진행한다 (`research/SKILL.md:29-36`).
- [확인] headless로 들어가는 문구에 "just proceed"·"don't wait for me"가 있다. 사람 없는 컨테이너 환경도 headless다 (`research/SKILL.md:34`). 그래서 research의 rubric gate는 사용자 한마디나 실행 환경으로 건너뛸 수 있다. "세션 지시가 gate를 넘지 못한다"는 문장(`knowledge-base/SKILL.md:49`)과 경계가 흐리다. consolidate의 결정 gate에는 headless 우회가 없다.
- [확인] 앱이 띄운 에이전트는 `delete`·`move`·`share_link`·`install`·`import`를 부를 때마다 사람 승인을 받는다. 코드 gate다 (`packages/core/src/handoff/terminal-launch.ts:269-275`, `packages/server/src/acp/permissions.ts`). 외부에서 MCP로 붙은 에이전트에는 해당 host의 권한 설정이 적용된다.
- [확인] 사람과 에이전트가 같은 Yjs 문서를 동시에 편집한다 (`karpathy-llm-wiki.mdx:12`).
- [확인] 사람이 남긴 미해결 comment는 `exec` 결과에 "열린 리뷰 요청"으로 실린다 (`exec.ts:64`, `:254-261`).
- [확인] 충돌은 MCP로 풀 수 없다. 사람이 앱에서 고른다 (`conflict-resolution.md:21`, `:44`).

#### 10. 동시성·안전

입장: 이 저장소의 실제 투자처다. CRDT·충돌 gate·shadow git·읽기 전용 sandbox가 코드로 있다.

- [확인] Hocuspocus 서버 위의 Yjs CRDT가 동시 편집을 수렴시킨다 (`packages/server/package.json` 의존성 `@hocuspocus/server`, `yjs`).
- [확인] 다른 writer가 최근에 고친 문서의 replace는 거부된다. append·prepend·edit는 통과한다 (`write.ts:92`, `agent-sessions.ts:163`, `concurrent-overwrite-refused-error.ts:7-13`).
- [확인] 충돌 상태 문서에 대한 write·edit·delete·move·restore를 409로 거부한다 (`conflict-resolution.md:3-17`, 코드는 `conflict-errors.ts:67`, `api-extension.ts:2484`).
- [확인] 디스크 쓰기는 임시 파일에 쓴 뒤 rename한다 (`persistence.ts:1802`, `:1828`). index 파일은 `atomicWriteFile`을 쓴다 (`backlink-index.ts:2161`).
- [확인] 모든 쓰기는 shadow git에 writer 구분과 함께 남는다. `history`·`checkpoint`·`restore_version`으로 되돌린다 (`packages/server/src/mcp/tools/checkpoint.ts:19-21`, `restore-version.ts:25-28`, `history.ts:41-44`).
- [확인] `exec`는 명령 10개만 허용한다. 호출 하나에 명령 하나 또는 파이프라인 하나다. 파이프 단계 수 제한은 찾지 못했다. `&&`·`;`·redirection은 금지다 (`bash/parse-command.ts:277-288`, `:296-300`, `:393`, `:430-461`).
- [확인] `exec` 전후로 mtime을 비교한다. 파일이 바뀌었으면 보안 위반으로 실패시킨다 (`exec.ts:487-495`).
- [확인] 읽기 전용 OverlayFs가 symlink를 막는다 (`bash/index.ts:57-62`).
- [확인] seed는 symlink 경유 쓰기를 `wx`로 막는다 (`apply.ts:95-100`).

#### 11. Query·검색

입장: grep + backlink + BM25를 에이전트가 반복 호출하는 agentic loop다. vector는 선택형 hybrid다.

- [확인] `search`는 Orama in-memory index 위에서 BM25·제목 가중·최신성을 섞는다 (`workspace-search.ts:1`, `:374`, `packages/server/src/mcp/tools/search.ts:35`).
- [확인] semantic search는 기본값이 꺼져 있다 (`packages/server/src/embeddings/semantic-config.ts:31`). 켜면 embeddings 신호를 더한다 (`search.ts:36`).
- [확인] 문서는 "no vector database"라고 강조한다 (`karpathy-llm-wiki.mdx:53`). 코드에는 opt-in vector cache가 있다 (`packages/server/src/embeddings/vector-cache.ts`). 두 서술은 "기본값 기준"이라는 점에서 모순은 아니다.
- [확인] `exec cat` 단일 파일 호출은 backlink·forward link·shadow 이력·git 이력·comment를 함께 돌려준다 (`enrichment.ts:449-462`, `exec.ts:503`).
- [확인] 답을 wiki에 되저장하는 기본값은 "제안만"이다. 자동 생성은 금지다 (`corpus-qa.md:12`). headless에서는 네 조건이 명백할 때만 저장한다 (`corpus-qa.md:14`).
- [확인] research 안에서 나온 Q&A는 별도 짧은 페이지로 저장하라고 한다 (`research/SKILL.md:321-328`).

#### 12. index·log 관리

입장: index는 동적이다. log는 LLM이 쓴다. 기계 log는 shadow git이 대신한다.

- [확인] `exec("ls -A <dir>")`가 index 역할을 한다. 폴더 description·tags·template 목록·md 개수·최근 문서·comment 수를 돌려준다 (`exec.ts:186-229`).
- [확인] 파일 항목에는 title·description·tags·status·type·backlink 수·comment 수가 붙는다 (`exec.ts:241-297`, `:550-563`). 이력은 단일 파일 `cat`일 때만 붙는다 (`exec.ts:503`, `:510`).
- [확인] 폴더 스캔은 1,000개 항목에서 끊긴다. 끊기면 "scan truncated"를 표시한다 (`enrichment.ts:24`, `exec.ts:227`).
- [확인] hub 문서를 새로 만들지 말라고 한다. 이미 있으면 자식과 번갈아 갱신하라고 한다 (`references/cadence-and-logs.md:11`).
- [확인] OKF plugin을 켜면 폴더마다 `index.md`를 결정적으로 재생성할 수 있다 (`okf.mdx:27`, `packages/server/src/content/generate-index.ts`). knowledge-base pack은 켜지 않는다.
- [확인] `log.md`는 에이전트가 턴마다 한 항목을 덧붙인다 (`knowledge-base/SKILL.md:74`). 코드는 log.md를 쓰지 않는다. log.md 링크 경고를 감추는 것만 한다 (`link-advisory-policy.ts:15-20`).
- [확인] 에이전트·사람별 쓰기 이력은 shadow git이 자동으로 남긴다. `exec` 결과에 `OK edits:`로 실린다 (`exec.ts:278-289`).

#### 13. 포맷 표준 (OKF)

입장: OKF 호환을 의식했다. 하지만 knowledge-base pack은 OKF 검사를 켜지 않는다.

- [확인] 템플릿이 `type`을 갖고 `status: draft|stable`, `sources: [{resource: ...}]` 모양을 쓴다 (`starter.ts:71-125`, `karpathy-llm-wiki.mdx:146`).
- [확인] knowledge-base와 okf pack을 어느 순서로 seed해도 OKF lint finding이 0개라는 테스트가 있다 (`packages/server/src/seed/okf-conformance.test.ts:318-362`).
- [확인] 모든 pack 템플릿이 비어 있지 않은 `type`을 갖는지 검사한다 (`okf-conformance.test.ts:365-401`).
- [확인] OKF 검사는 경고뿐이다. 저장을 막지 않는다 (`okf.mdx:7`).
- [추정] knowledge-base의 log 규칙은 "append"다 (`knowledge-base/SKILL.md:74`). OKF `log-shape` 규칙은 newest-first를 요구한다 (`packages/core/src/markdown/lint/rules/log-shape.ts:51-56`). 두 pack을 함께 쓰고 날짜가 두 개 이상 쌓이면 경고가 날 것이다. 근거는 두 규칙의 문면 하나다. 테스트는 빈 log.md만 검사한다.

#### 14. 규모·비용

입장: 규모 주장은 있다. 뒷받침하는 측정은 찾지 못했다.

- [확인] 문서는 "thousands of files"를 vector DB 없이 다룬다고 쓴다 (`docs/content/reference/agentic-search.mdx:7`).
- [확인] 그 주장을 재는 벤치마크는 찾지 못했다. 평가 세트는 semantic search용만 있다 (`packages/server/src/embeddings/eval/`).
- [확인] ingest는 "소스당 30초"라고 쓴다 (`karpathy-llm-wiki.mdx:243`). 측정 근거는 없다.
- [확인] 컨텍스트 상한: `exec` 출력은 500줄 또는 약 24KB에서 자른다 (`exec.ts:53-58`). `audit`·`lint`는 10파일 × 10진단으로 자른다 (`audit.ts:31`).
- [확인] ingest는 LLM 합성을 하지 않는다. 비용은 fetch와 write 한 번이다. 합성 비용은 research 요청 때만 든다.
- [추정] 대신 research 한 번은 소스 3~8개를 다 읽는다 (`research/SKILL.md:195`). 이 비용이 질문마다 반복될 수 있다. 근거는 research Path A가 기본값이라는 점 하나다 (`research/SKILL.md:21-25`).
- [추정] `exec` 결과마다 frontmatter와 backlink·comment 수가 붙는다. 단일 파일 `cat`이면 backlink 목록과 이력까지 붙는다 (`exec.ts:503-563`). 호출당 토큰이 native grep보다 클 것이다. 근거는 enrichment 필드 목록(`enrichment.ts:466-485`) 하나다. 실측은 하지 않았다.

#### 15. frosk1 비판 7가지에 대한 대응

| 비판 | 대응 | 근거 |
| --- | --- | --- |
| 오류 누적 | research(잠정)와 articles(확정)를 나누고 사람 결정을 gate로 둔다. 주장마다 소스 링크를 요구한다. 검증은 프롬프트뿐이다. | `consolidate/SKILL.md:21-31`, `project/SKILL.md:80-91` |
| 부분 문맥 | research 전 grep·ls 스캔을 강제한다. consolidate는 `sources:`의 모든 파일을 읽으라고 한다. 전수 읽기를 확인하는 코드는 없다. | `research/SKILL.md:105-126`, `consolidate/SKILL.md:61` |
| 요약 손실 | 원문을 verbatim으로, binary는 바이트째 보존한다. ingest는 요약하지 않는다. 가장 강한 대응이다. | `ingest-and-sources.md:3`, `:183-191` |
| 가짜 source of truth | articles를 스스로 "source of truth"라 부른다. 대신 사람 결정 뒤에만 만들고 원문까지 체인을 남긴다. 비판을 부정하기보다 "결정 기록"으로 의미를 바꿨다. | `knowledge-base/SKILL.md:57`, `consolidate/SKILL.md:23-31` |
| 환각 병합 | research는 "tentative" 어조와 모순 기록을 요구한다. 병합(consolidate)은 사람 결정 뒤에만 한다. 자동 검출은 없다. | `research/SKILL.md:216`, `:301-305` |
| 운영 복잡도 | 사용자에게는 클릭 한 번 seed로 감춘다. 시스템 자체는 40만 줄 넘는 앱과 상시 서버를 요구한다. 대부분 도구가 Hocuspocus 서버 없이는 돌지 않는다. | `karpathy-llm-wiki.mdx:158`, `search.ts:34`, `write.ts:90` |
| ingest 비용 | ingest에서 합성을 빼서 비용을 research 시점으로 옮겼다. 소스 하나가 건드리는 페이지가 1~4개다. | `ingest-and-sources.md:225-231` |

[확인] frosk1의 8번째 항목(staleness)은 #8에서 다뤘다. drift 감지 코드는 없다.

#### 16. 성숙도·차용 가능성

입장: 성숙한 제품 코드다. GPL이라 코드를 가져오면 내 코드도 GPL-3.0으로 내야 한다. 그 조건을 받지 않으면 설계와 프롬프트 구조만 참고할 수 있다.

- [확인] 테스트 파일(`*.test.*`·`*.spec.*`의 ts·tsx 등) 3,067개다. server 702개, core 225개다.
- [확인] seed·OKF 호환·frontmatter guard·skill 목록 drift에 전용 테스트가 있다 (`packages/server/src/seed/*.test.ts`).
- [확인] 버전은 0.85.0이다 (`packages/server/package.json`).
- [확인] 서버 의존성은 Yjs, Hocuspocus, Tiptap, just-bash, simple-git, chokidar, MCP SDK, OpenTelemetry 등 40여 개다.
- [확인] 7개 패키지 모두 `GPL-3.0-or-later`다. skill 텍스트도 `packages/server/assets/` 아래에 있어 같은 라이선스로 배포된다.
- [추정] 코드를 내 저장소에 옮기면 내 저장소도 GPL-3.0 조건을 따라야 한다. 근거는 LICENSE 본문(GPL v3) 하나다. "불가"가 아니라 "조건부"다.
- [확인] SKILL.md 메타데이터는 별도 저장소 `inkeep/open-knowledge-skills`를 가리킨다 (`knowledge-base/SKILL.md:9`). 그 저장소의 라이선스는 확인하지 않았다.

## 장점

- **원문 보존이 철저하다.** [확인] verbatim 텍스트, binary 바이트, sha256, 날짜 형제 supersede까지 정했다 (`ingest-and-sources.md:113-213`). 요약 손실 비판에 가장 직접적으로 답한다. 다만 sha256과 날짜 형제 절차는 binary 소스에만 적혀 있다 (#4).
- **잠정과 확정을 분리했다.** [확인] `research/`(draft)와 `articles/`(stable)을 나누고 사람 결정을 승격 조건으로 둔다 (`consolidate/SKILL.md:21-31`). 이른 확정을 "opt-in"으로 바꾼다.
- **폴더 규칙을 폴더 옆에 둔다.** [확인] 폴더 description(산문 규칙)이 `ls` 결과에 실려 에이전트가 쓰기 직전에 본다 (`exec.ts:186-229`). 중앙 CLAUDE.md를 다 읽지 않아도 된다. 필드 schema는 아니다 (#2).
- **읽기 결과에 맥락을 붙인다.** [확인] `exec`가 frontmatter와 backlink·comment 수를 같이 준다. 단일 파일 `cat`이면 backlink 목록·이력·comment 본문까지 준다 (`exec.ts:503-563`, `enrichment.ts:407-486`). 동적 index와 grep을 한 도구로 묶었다.
- **crash 복구를 절차에 넣었다.** [확인] "wiki가 곧 checkpoint"라는 규칙과 Step 0 task 생성이 있다 (`research/SKILL.md:67-101`).
- **쓰기 안전이 코드로 있다.** [확인] CRDT, 동시 덮어쓰기 거부, 충돌 409, shadow git 복원, 읽기 전용 sandbox와 mtime tripwire가 있다 (#10).
- **STOP gate가 세션 지시를 이긴다고 명시했다.** [확인] "멈추지 말라"는 지시가 one-way door gate를 넘지 못한다 (`knowledge-base/SKILL.md:49`). 다만 research rubric gate는 "just proceed" 한마디나 비대화형 환경에서 headless로 넘어간다 (`research/SKILL.md:34`, #9).

## 단점

- **wiki 규율은 강제되지 않는다.** [확인] `external-sources/` 불변, `sources:` 정합성, status 흐름, log 기록 모두 프롬프트뿐이다 (#2). knowledge-base pack은 markdownlint·frontmatter·OKF lint 어느 것도 켜지 않는다 (`starter.ts:1340-1348`, `plugins.ts:55`). 기본 `audit`은 본문 깨진 링크만 본다. frontmatter `sources:`·`supersedes:` 경로는 그마저 검사 밖이다 (#5).
- **프롬프트끼리 이미 어긋나 있다.** [확인] 템플릿은 `created:`·`authored:`, skill은 `date:`를 요구한다. 플랫폼 skill은 아직 `status: provisional`이라 적는다 (#2). 검사가 없어서 이 어긋남을 아무도 잡지 않는다.
- **내용 lint가 비어 있다.** [확인] 모순·낡은 주장 검사는 "에이전트에게 물어라" 한 줄이다 (`karpathy-llm-wiki.mdx:244-246`).
- **근거 단위가 거칠다.** [확인] 페이지 단위 링크뿐이다. 주장과 원문 구간의 대응은 없다 (#5).
- **Karpathy의 compounding을 일부 포기했다.** [확인] 소스 하나가 1~4페이지만 건드린다. entity·concept 페이지를 자동으로 늘리지 않는다 (#4). [추정] wiki가 "질문별 research 문서 모음"으로 자랄 수 있다. 근거는 research Path A가 질문 단위 문서를 만든다는 점 하나다 (`research/SKILL.md:21`).
- **실행 기반이 무겁다.** [확인] Electron 앱이나 상시 서버가 있어야 도구가 돈다 (`write.ts:90`). 코드 차용에는 GPL 조건이 붙는다 (#16).
- **규모 주장에 측정이 없다.** [확인] "thousands of files"와 "30초"는 근거 자료를 찾지 못했다 (#14).
- **log.md 순서가 OKF와 어긋날 수 있다.** [추정] #13 참조.

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

- 3층 분리와 승격 gate. `sources/` → `drafts/` → `canonical/`로 나누고, canonical 승격에는 사람 결정 문장을 요구한다.
- 원문 wrapper frontmatter 모양. `source_url`, `date_fetched`, `preservation`, `sha256`, `bytes`, 재수집 시 날짜 형제 + `supersedes`. 원 저장소는 binary에만 sha256을 적는다. 내 구현에서는 텍스트 wrapper에도 본문 hash를 둔다.
- 지우지 않는 supersede. `status: deprecated` + `superseded_by`로 과거 판단을 남긴다.
- 폴더별 description 파일. 각 폴더 옆에 짧은 규칙을 두고, 목록 조회 결과에 실어 보낸다. 중앙 schema는 짧게 유지한다.
- 목록·읽기 결과에 frontmatter와 backlink 수를 붙이는 얇은 래퍼. index.md 없이 동적 index를 만드는 방법이다.
- "wiki가 곧 checkpoint" 규칙. 소스 하나 읽으면 바로 쓰고, 글은 뼈대부터 만들어 절마다 채운다.
- 답 되저장의 네 조건(여러 문서 합성, 재사용성, 중복 없음, 출처 있음). 조건을 다 만족할 때만 제안한다.
- STOP gate가 세션 수준 "멈추지 말라" 지시보다 우선한다는 명시.
- log.md 링크 경고 억제 같은 "history 문서는 고치지 않는다" 정책.

### 피할 것

- 불변·정합성 규칙을 프롬프트에만 두는 것. 내 구현에서는 `sources/` 쓰기 차단과 `sources:` 링크 실재 검사를 pre-commit이나 write gate로 옮긴다.
- 내용 lint를 "에이전트에게 물어라"로 남기는 것. 최소한 낡은 주장 후보(`stale_after` 경과, superseded 소스를 인용하는 페이지)는 결정적으로 뽑는다.
- 상시 서버·IDE 의존. 같은 효과(동적 index, backlink)는 CLI 스크립트와 git으로 충분할 수 있다.
- 서로 다른 pack 규칙이 같은 파일(log.md)에 다른 순서를 요구하는 상황. log 형식은 한 곳에서만 정한다.
- 측정 없는 규모·시간 주장.
- 템플릿과 절차 skill이 같은 필드를 다른 이름으로 부르는 상황(`created` 대 `date`). 필드 이름은 schema 한 곳에서 정하고 lint로 검사한다.
- 링크 검사를 본문에만 거는 것. 출처 체인이 frontmatter에 있으면 frontmatter 경로도 같은 검사에 넣는다.

## 확인하지 못한 것

- 앱이 실제로 돌 때의 동작. 코드 실행은 금지 조건이라 하지 않았다. 모든 판단은 정적 읽기 기반이다.
- `search`의 `/api/search` HTTP 라우트와 증분 index 갱신 경로. core의 점수 함수만 읽었다.
- `suggest-links.ts`의 전체 매칭 규칙. 제목·alias 기반이라는 것까지만 확인했다.
- ACP 경로가 skill 규칙을 다르게 적용하는지. 권한 gate(`acp/permissions.ts`)와 skill staging 파일(`acp/project-skill-staging.ts`)이 있다는 것까지만 봤다.
- `inkeep/open-knowledge-skills` 저장소의 존재와 라이선스. skill 텍스트만 다른 라이선스일 가능성이 있다. 그 저장소를 `gh api`로 보면 알 수 있다.
- "thousands of files" 규모 주장의 근거. 공개 벤치마크나 블로그가 있는지 웹에서 찾지 않았다.
- shallow clone이라 설계 변경 이력(예: provisional/canonical → draft/stable 전환 시점)을 볼 수 없었다. 전체 clone의 `git log`로 확인할 수 있다.

## 검증 기록

- markdownlint도 기본값이 꺼져 있음을 반영했다. #한 바퀴 흐름 0·5, #2, #7, #단점을 고쳤다.
- sha256 비교와 날짜 형제 supersede가 binary 소스에만 적혀 있음을 #4, #8, #장점, #가져올 것에 반영했다.
- exec 이력 첨부가 단일 파일 `cat`에만 붙는다는 점을 #한 바퀴 흐름 2, #12, #14, #장점에 반영했다.
- exec allowlist 근거를 설명 문자열(`exec.ts:65`)에서 실제 검사 코드(`bash/parse-command.ts:277-288`, `:393`)로 바꿨다.
- "파이프 하나"를 "파이프라인 하나, 단계 수 제한 못 찾음"으로 고쳤다.
- 충돌 409 근거를 존재하지 않는 줄(`conflict-resolution.md:48`, `:52`)에서 `:3-17`, `:21`, `conflict-errors.ts:67`로 고쳤다.
- 동시 덮어쓰기 거부의 실제 throw 위치(`agent-sessions.ts:163`)를 더했다.
- hub 문서 규칙의 줄 번호를 `cadence-and-logs.md:25`에서 `:11`로 고쳤다.
- 디스크 쓰기 rename 단계(`persistence.ts:1828`)를 확인했다. #확인하지 못한 것에서 뺐다.
- 본문 링크만 backlink·audit 대상이고 frontmatter `sources:`·`supersedes:` 경로는 검사 밖이라는 점을 #5, #단점, #피할 것에 더했다.
- `supersedes`·`superseded_by`를 읽는 코드가 seed 템플릿 말고는 없다는 점을 #8에 더했다.
- 실행 파일 확장자 목록이 코드에 있지만 asset 서빙·desktop에만 쓰인다는 점을 #4에 더했다.
- 템플릿과 skill의 필드 이름 불일치, 플랫폼 skill의 `provisional` 잔존, init config 주석의 없는 MCP 도구 언급을 #2와 #단점에 더했다.
- 앱이 띄운 에이전트의 파괴적 도구 승인 gate(`terminal-launch.ts:269-275`)를 #2, #9에 더했다.
- research rubric gate가 "just proceed"나 비대화형 환경에서 headless로 넘어간다는 점을 #9와 #장점에 더했다.
- ACP로 에이전트 CLI를 띄우는 경로를 #1에 더했다.
- "GPL이라 차용 불가"를 "GPL 조건부 차용"으로 낮췄다.
- 테스트 파일 수 3,067개가 저장소 전체 `*.test.*`·`*.spec.*` 기준임을 밝혔다.

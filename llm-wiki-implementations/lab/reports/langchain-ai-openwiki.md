# langchain-ai/openwiki — 사실(Claim)을 줄 범위 해시에 묶고, 증거가 바뀐 Claim만 다시 쓰게 강제하는 코드 wiki 엔진

## 한눈에

| 항목 | 값 |
| --- | --- |
| URL | https://github.com/langchain-ai/openwiki |
| clone commit | `27b3c76` (2026-10-09, `chore: version packages (#1006)`) |
| 별 / 최근 push / 라이선스 | 17,061 / 2026-10-10 / MIT (`gh api repos/langchain-ai/openwiki`로 확인) |
| 형태 | npm CLI(`openwiki`, v0.7.2) + MCP 서버 + 코딩 에이전트용 skill. LangChain `deepagents` 위에 선다 |
| 대상 | code 모드(저장소 → `openwiki/`)와 personal 모드(connector → `~/.openwiki/wiki`) 두 가지 |
| 코드 규모 | `src` TS 약 61.5k줄, `test` 약 60k줄(`test/`의 테스트 파일 205개, `it`/`test` 약 2,700개), `evals` 약 21k줄(테스트 파일 36개 별도) |

[확인] 저장소가 자기 자신의 wiki를 `openwiki/`에 커밋해 둔다. 페이지 22개(`quickstart.md` 포함, sidecar도 22개), Claim 746개, `.claims/` 1.7MB다. 매일 GitHub Actions가 갱신한다(`.github/workflows/openwiki-update.yml:6`).

[확인] 핵심 설계는 "LLM은 쓰고, 장부는 코드가 쥔다"이다. Claim id, 증거 version, sidecar, index, provenance, 진행 상태는 모두 코드가 소유한다(`integrations/openwiki/SKILL.md:45-47`).

## 한 바퀴 흐름

code 모드 `openwiki --update` 기준이다. host 연동(MCP)도 같은 lifecycle 함수를 부른다.

1. `beginRepositoryRun`(`src/generation/repository-run.ts:388`)이 시작점이다. `.run.json`이 있으면 `resumeRepositoryRun`(`:633`)으로 이어 간다.
2. `prepareClaimsRuntime` → `runClaimsPreflight`(`src/claims/brains/code/preflight.ts:40`)가 모든 sidecar의 증거를 다시 resolve한다. version이 다르면 `stale`, 파일·범위가 사라졌으면 `unresolved`다(`:76-97`).
3. no-op 판정은 Claim 검사 뒤에 온다(`repository-run.ts:478-527`). git이 깨끗하고 issue가 0이면 모델을 부르지 않고 `.last-update.json`만 갱신한다.
4. 아니면 `.run.json`을 원자적으로 쓴다(`:568`). 이 시점이 durability 경계다.
5. planner agent가 `submit_plan`을 부른다. 프롬프트에는 페이지별 baseline 이후 바뀐 경로와 Claim issue 목록이 들어간다(`src/agent/repository-prompts.ts:19-97`).
6. `createRepositoryPlan`(`src/generation/page-jobs.ts:123`)이 계획을 검증한다. planner가 빠뜨린 stale 페이지는 `addRequiredClaimIssueJobs`(`:256`)가 강제로 job에 넣는다.
7. `runPageAgent`(`src/agent/repository-runner.ts:866`)가 페이지 하나에 새 worker 하나를 띄운다. worker의 쓰기는 그 페이지 한 파일로 제한된다(`:924-933`).
8. worker가 `submit_page`를 부르면 `submitRepositoryPage`(`repository-run.ts:1283`)가 받는다. 먼저 frontmatter를 결정적으로 고친다. 다음으로 `reconcilePageClaims`(`page-jobs.ts:402`)가 Claim 결정을 반영한다. sidecar와 `.page-manifest.json`이 durable해진 뒤에야 job이 complete가 된다.
9. 실패한 worker는 페이지와 Claim을 snapshot으로 되돌린다. 2회 실패하면 skip한다(`repository-runner.ts:854`, `:898-901`).
10. `finishRepositoryRun`(`repository-run.ts:1613`)이 `finalizeWikiArtifacts`(`src/agent/wiki-finalizer.ts:248`)를 돌린다. Mermaid 검증 → index 재생성 → link 검증 → `sources` 투영 → `generated` 스탬프 순서다.
11. 전체 Claim을 한 번 더 증명한 뒤 마지막에 `.run.json`을 지운다(`:1700`, `:1748`).
12. query는 별도 경로다. MCP `openwiki_search`가 SQLite FTS5 BM25로 섹션을 찾고 `openwiki_read`가 섹션을 돌려준다(`src/retrieval/wiki.ts:433`, `:543-563`). 모델을 부르지 않는다.
13. 독립된 lint 명령은 없다. 결정적 검사는 10번 finalize에 들어 있다.

## 축별 분석

#### 1. 실행 형태

입장: CLI·SDK 엔진이다. MCP 서버와 skill은 같은 엔진을 host 에이전트에 노출하는 얇은 층이다.

- [확인] native 실행은 자체 Deep Agents가 planner와 page worker를 돌린다(`src/agent/index.ts:187-211`).
- [확인] host 실행은 Codex·Claude Code 등이 생성용 MCP 도구 6개(`openwiki_begin` → `submit_plan` → `next_page` → `submit_page` → `finish`, `inspect_page_claims`)로 같은 queue를 소비한다(`src/integrations/core/protocol.ts:15-24`). MCP 서버 전체는 검색용 4개(`list_workspaces`, `list_wikis`, `search`, `read`)를 더해 10개다.
- [확인] 9개 host 설치기를 제공한다(`src/integrations/install/`). 모델 provider는 14개다(README).

#### 2. 규칙의 위치

입장: 장부 규칙은 코드가 강제하고, 글의 품질과 "본문과 Claim의 일치"는 프롬프트에 맡긴다.

코드가 강제하는 것:

| 규칙 | 위치 |
| --- | --- |
| native worker는 `openwiki/` 아래, 그중 배정된 페이지 한 장만 쓴다 | `src/agent/docs-only-backend.ts:581-597` |
| shell은 `pwd`, `git rev-parse HEAD` 두 개만 허용한다 | `docs-only-backend.ts:75-78` |
| personal 모드는 shell 전면 금지 | `docs-only-backend.ts:544-553` |
| `.claims/`는 읽기·쓰기·grep 모두 거부 | `docs-only-backend.ts:707-713` |
| stale·unresolved Claim은 명시적 결정 없이는 제출 거부 | `page-jobs.ts:498-507` |
| 페이지는 Claim이 최소 1개여야 complete | `page-jobs.ts:511-516` |
| 증거가 resolve 안 되면 Claim 추가 거부 | `src/claims/core/mutations.ts:151-156` |
| issue가 남은 페이지는 sidecar에 쓰지 않는다. finalize는 경고로 넘기고, 이어지는 durability 증명이 submit을 거부한다 | `src/claims/brains/code/session.ts:326-345`, `repository-run.ts:1435-1462` |

프롬프트에만 있는 것:

- [확인] "The final page body and reconciled Claim set must agree"는 프롬프트 문장이다(`src/claims/guidance.ts:24`). 본문에 Claim 문장이 실제로 있는지 대조하는 코드는 찾지 못했다.
- [확인] host 모드의 "Never modify source code"와 "다른 페이지 수정 금지"도 skill 문서 규칙이다(`integrations/openwiki/SKILL.md:183-195`). host는 자기 도구로 쓰기 때문에 docs-only backend가 끼지 않는다.
- [확인] host가 run 도중 소스를 고치면 막지는 못하고 감지만 한다. `finishRepositoryRun`이 source fingerprint를 다시 재서 바뀌었으면 `.last-update.json`을 `interrupted`로 쓴다(`repository-run.ts:1650`, `:1723-1734`). 다음 begin은 fingerprint가 다르면 plan을 버리고 planning으로 돌아간다(`repository-run.ts:658-685`).

#### 3. 저장 구조

입장: Markdown 본문은 깨끗하게 두고, 구조화 상태는 숨김 sidecar 파일로 분리한다.

| 파일 | 내용 | 주인 |
| --- | --- | --- |
| `openwiki/<group>/<page>.md` | OKF frontmatter + 본문 | LLM(본문), 코드(`generated`·`verified`·`sources`) |
| `openwiki/.claims/<page>.json` | `schemaVersion`, `pageVersion`(본문 sha256), `claims[]{id, statement, evidence[]{resource, version}}` | 코드 |
| `openwiki/.page-manifest.json` | 페이지별 `gitHead`, `sourceFingerprint`, `pageVersion`, `completedRunId` | 코드 |
| `openwiki/.run.json` | 진행 중 run의 plan과 job 상태(pending/skipped/complete) | 코드, 끝나면 삭제 |
| `openwiki/.last-update.json` | 마지막 run의 gitHead, model, status | 코드 |
| `openwiki/INSTRUCTIONS.md` | 사용자가 쓰는 brief | 사람 |
| 각 디렉터리 `index.md` | 결정적 생성 목차 | 코드 |

- [확인] 디렉터리 분류는 고정되어 있지 않다. planner가 `architecture/`, `concepts/`, `workflows/` 같은 그룹을 정한다(`repository-prompts.ts:63-70`).
- [확인] 고정 페이지는 `quickstart.md` 하나다. 지울 수 없고 항상 마지막에 쓴다(`page-jobs.ts:141-146`, `:181-187`).
- [확인] personal 모드는 `/quickstart.md`, `/themes.md`, `/commitments.md`, `/open-questions.md`, `/sources/<connector>.md` 같은 canonical 파일을 프롬프트로 권한다(`src/ingestion/ingestion.ts:351-363`).

#### 4. Ingest

입장: code 모드는 "바뀐 것만, 페이지 단위로, 재개 가능하게"를 코드로 구현한다. personal 모드는 24시간 창의 단일 agent run이다.

- 사람 참여: [확인] 없음. 사람은 `INSTRUCTIONS.md`로 범위만 정한다.
- 증분 추적: [확인] 페이지마다 baseline `gitHead`를 manifest에 두고, baseline 이후 바뀐 경로를 planner에 준다(`repository-run.ts:876-913`). 어느 페이지를 다시 쓸지는 planner(LLM)가 고른다.
- fast-forward: [확인] 코드가 모델 없이 넘기는 경우는 좁다. 그 페이지의 baseline 이후 저장소 전체에서 `openwiki/` 밖 변경이 하나도 없을 때만 baseline을 당긴다(`repository-run.ts:915-950`, `src/agent/utils.ts:897-937`). 페이지와 무관한 파일 하나만 바뀌어도 fast-forward는 일어나지 않는다. 주된 용도는 wiki만 바꾼 커밋(예: CI가 연 docs PR merge)을 건너뛰는 것이다.
- 강제 job: [확인] Claim issue 외에 출력 언어가 바뀐 경우에도 기존 페이지 전부를 rewrite job으로 강제한다(`page-jobs.ts:178`, `repository-run.ts:538-539`).
- Claim 단위 증분: [확인] worker는 issue가 있는 Claim만 받는다. issue 없는 Claim은 생략해도 자동 confirm된다(`page-jobs.ts:498-507`).
- queue·crash 복구: [확인] `.run.json`과 manifest는 tmp 파일 + `rename`으로 원자적으로 쓴다(`src/generation/run-state.ts:346-352`, `src/generation/page-manifest.ts:163-169`). 재실행하면 complete가 아닌 job부터 이어 간다.
- init 재실행: [확인] 기존 wiki를 백업하고, run state가 durable해지기 전에 실패하면 복구한다(`repository-run.ts:424-427`, `:598-606`).
- 자동 감시: [확인] 파일 watcher는 없다. CI cron 예제(GitHub Actions, GitLab, Bitbucket)와 macOS launchd(`src/scheduling/schedules.ts:147`, `:196`)로 주기 실행한다. OS 스케줄러 설치는 darwin에서만 된다.
- 멀티포맷: [확인] code 모드는 저장소 텍스트만 읽는다. personal 모드는 connector 9종이 JSON raw dump를 `~/.openwiki/connectors/<id>/raw/`에 쓴다(`ingestion.ts:126-180`).
- personal 증분: [확인] 매번 "최근 24시간" 창이다(`ingestion.ts:36`). 페이지 queue도 Claim도 없다(`src/claims/brains/code/runtime.ts:72-73`).
- 소스 하나가 건드리는 페이지 수: [확인] code 모드는 소스 단위가 아니라 페이지 단위로 계획한다. 한 파일의 변경이 여러 페이지의 Claim을 stale로 만들 수 있고, 그 페이지들이 모두 job이 된다.

#### 5. 근거 추적 단위

입장: claim ledger다. 각 Claim이 `repo://path#Lx-Ly`와 그 범위의 해시 version을 가진다.

- [확인] version은 `repo-lines-v1:sha256:<범위 해시>:<base64 메타>`다. 메타에는 첫 줄·끝 줄 해시와 앞 3줄·뒤 3줄 context 해시가 들어 있다(`src/claims/evidence/repository/resolver.ts:24-69`, `:613-`).
- [확인] 범위가 이동해도 같은 내용이 정확히 한 곳에 있으면 따라간다(`resolver.ts:424-469`). 내용이 바뀌었으면 앞뒤 context 해시로 새 범위를 찾는다(`:479-507`). 후보가 2개 이상이면 `null`로 포기한다.
- [확인] 범위 없는 `repo://path`는 파일 전체 해시다(`resolver.ts:237-239`). 파일의 어느 줄이 바뀌어도 stale이 된다.
- [확인] version은 모델이 쓰지 못한다. 모델은 `resource`만 제안하고 코드가 version을 붙인다(`src/claims/core/types.ts:39-44`, `mutations.ts:138-167`).
- [확인] symlink, 저장소 밖 경로, `.openwikiignore` 대상은 증거로 받지 않는다(`resolver.ts:195-223`, `:255-268`).
- [확인] 증거 범위가 Claim 문장을 실제로 뒷받침하는지는 코드가 보지 않는다. 존재와 해시만 본다.

#### 6. Link

입장: 링크는 LLM이 본문에 쓰고, 검증·목차·그래프는 결정적으로 만든다.

- [확인] planner가 `relatedPages`를 정하고 worker가 상대 경로 링크를 쓴다(`repository-prompts.ts:82-85`, `:147-152`).
- [확인] `validateWikiInternalLinks`가 깨진 링크 위에 `<!-- openwiki: broken internal link ... -->` 주석을 단다. run은 실패시키지 않는다(`src/agent/wiki-link-validator.ts:105-157`).
- [확인] "다음 run이 주석을 보고 고친다"는 지시는 `createSystemPrompt`가 덧붙이는 문단에만 있다(`src/agent/prompt.ts:131-136`, `:49-51`). 이 함수를 쓰는 것은 personal 모드다. code 모드의 planner·page worker 프롬프트(`repository-prompts.ts`)와 host skill에는 없다. `createSystemPrompt`는 code 모드 생성에서 아예 예외를 던진다(`prompt.ts:27-29`). 스탬프된 페이지를 job으로 넣는 코드도 없다. code 모드에서 깨진 링크 수리는 그 페이지가 다른 이유로 job이 되고 worker가 우연히 주석을 볼 때만 일어난다.
- [확인] backlink 파일은 없다. `openwiki visualize`가 Markdown 링크를 읽어 그래프를 그때그때 만든다(`src/visualize/graph.ts:332`).

#### 7. Lint

입장: 별도 lint 명령 없이 매 run의 finalize가 결정적 검사를 돈다. "LLM lint"에 해당하는 것은 stale Claim 재검토 job이다.

| 검사 | 방식 | 자동 수정 |
| --- | --- | --- |
| OKF frontmatter | 결정적 검증·복구, `type` 없으면 본문에서 유도 | 복구, 못 고치면 submit 거부(`repository-run.ts:1326-1342`) |
| Mermaid | 경량 검사 또는 mermaid+jsdom 파서 | 실패 fence를 `text` fence로 강등(`src/mermaid/validate.ts:166`) |
| 내부 링크 | 파일·anchor 존재 확인 | 주석 스탬프만 |
| index | 디렉터리별 재생성 | 전부 재작성 |
| Claim 증거 | preflight 해시 비교 | 없음. 해당 페이지를 job으로 강제 |

- [확인] Karpathy 원문의 "모순·고아 페이지·빠진 개념" 같은 의미 lint는 없다.
- [확인] commit gate는 없다. CI 예제가 docs-only PR을 열고, merge는 branch protection에 맡긴다(README "Auto-merge OpenWiki PRs").

#### 8. stale·모순 처리

입장: code 모드는 drift 감지 + Claim 단위 confirm/update/retract다. personal 모드는 프롬프트의 `## Contested` 절이다.

- [확인] 증거 해시가 바뀌면 그 Claim만 stale이 된다. 그 Claim을 가진 페이지가 job이 된다. worker는 반드시 confirm, update, retract 중 하나를 고른다(`guidance.ts:18-23`, `page-jobs.ts:498-507`).
- [확인] stale은 자동 retract가 아니다. "requirement to recheck"로 다룬다(`guidance.ts:19`).
- [확인] supersede 이력은 남지 않는다. retract는 배열에서 지우고 update는 덮어쓴다(`mutations.ts:113-125`). 이력은 git에 맡긴다.
- [확인] `verified: {by: openwiki/<ver>, at}`는 Claim이 1개 이상이고 issue가 없고 sidecar가 durable할 때만 붙는다(`session.ts:404-417`, `src/okf/claims-verification.ts:35-58`).
- [추정] `verified`의 뜻은 "증거 해시가 현재와 같다"이다. "문장이 참이다"가 아니다. 근거는 confirm 경로 1곳이다. confirm은 LLM 판단 뒤 version만 다시 계산한다(`mutations.ts:86-96`).
- [확인] personal 모드: 출처가 엇갈리면 양쪽을 `## Contested`에 남기고 "recency만으로 해결하지 말라"고 지시한다(`src/agent/prompts/personal.ts:227-230`). 코드 강제는 없다.
- [확인] OKF `status`·`stale_after` 필드는 검증만 하고 OpenWiki가 직접 쓰지는 않는다(`src/okf/frontmatter.ts:231-250`).

#### 9. 사람 개입

입장: 자율이다. 사람은 brief를 쓰고 CI가 만든 PR을 리뷰한다.

- [확인] plan 승인 단계는 없다. planner가 `submit_plan`을 부르면 바로 generating으로 간다.
- [확인] 리뷰 지점은 CI PR이다. auto-merge 예제도 제공한다(`examples/openwiki-update-auto-merge.yml`).
- [확인] 사람 편집은 덮어쓰이지 않게 일부 보호한다. 사람이나 다른 도구가 단 `verified` 이벤트는 보존한다(`claims-verification.ts:45-47`). 생성 페이지를 손으로 고치지 말라는 안내가 AGENTS.md 블록에 들어간다(`src/ingestion/code-mode.ts:647`).

#### 10. 동시성·안전

입장: 원자적 파일 쓰기, 페이지 snapshot 복구, 쓰기 경로·shell allowlist로 안전을 만든다. 프로세스 간 lock은 없다.

- [확인] 원자적 쓰기: `.run.json`, manifest, sidecar 모두 tmp + `rename`이다(`run-state.ts:346-352`, `page-manifest.ts:163-169`, `src/claims/brains/code/store.ts:310-319`).
- [확인] 프로세스 안 동시성: native worker 1~8개가 각자 페이지 하나를 쥔다. 상태 변경은 `withRunMutation`으로 직렬화한다(`repository-run.ts:319-335`). rate limit을 맞으면 동시성을 1 줄인다(`repository-runner.ts:729-734`).
- [확인] 프로세스 간: "Ownership is process-local"이라고 코드 주석이 밝힌다(`repository-run.ts:341`). 파일 lock은 찾지 못했다.
- [추정] native run과 host run을 같은 저장소에서 동시에 돌리면 같은 job을 둘이 쓸 수 있다. 실행해 보지 않았다.
- [확인] undo: worker 실패 시 페이지 Markdown과 Claim을 실행 전 snapshot으로 되돌린다(`repository-runner.ts:872`, `:898`). init은 기존 wiki 백업을 둔다(`src/agent/wiki-replacement.ts:42`).
- [확인] git: OpenWiki는 commit하지 않는다. git은 변경 감지(`ls-files`, `status`, HEAD)에만 쓴다(`src/agent/utils.ts:319-344`).
- [확인] 도구 허용: personal connector MCP는 config의 `allowedTools`에 있거나 서버가 `readOnlyHint`를 단 도구만 허용한다(`src/connectors/mcp-runtime.ts:202-226`). read-only 판정은 MCP 서버의 자기 신고에 기댄다.

#### 11. Query·검색

입장: 섹션 단위 BM25(SQLite FTS5)다. 답을 wiki에 되저장하지 않는다.

- [확인] 매 검색마다 메모리 DB에 FTS5 표를 만든다. title·description·heading·prose·identifiers에 가중치 `8,4,6,1,3`을 준다(`retrieval/wiki.ts:543-563`).
- [확인] 정렬 순서는 BM25가 먼저가 아니다. 소스 경로 힌트 일치 수 → 일치한 질의어 수 → BM25 점수 순이다(`retrieval/wiki.ts:576-584`). 경로 힌트는 페이지 frontmatter `sources`에서 온다(`:719`, `:1037-1050`).
- [확인] vector 검색은 제품에 없다. DeepSWE 평가 하네스에만 local vector 옵션이 있다(`evals/deepswe/README.md:179-181`).
- [확인] `openwiki link`로 여러 저장소 wiki를 workspace로 묶어 함께 검색한다(`src/linking/wiki-workspaces.ts`).
- [확인] 검색 도구는 read-only이고 모델을 부르지 않는다(`integrations/openwiki/SKILL.md:38-39`).
- [확인] 에이전트에게 "작업 시작 때 wiki를 미리 읽지 말라"고 지시한다(`SKILL.md:10-13`). wiki를 필요할 때만 꺼내는 context로 본다.

#### 12. index·log 관리

입장: index는 결정적 재생성, log는 쓰지 않는다. 이력은 git과 상태 파일이 대신한다.

- [확인] `synchronizeWikiIndexes`가 디렉터리마다 `index.md`를 frontmatter의 title·description으로 다시 만든다(`src/okf/index-sync.ts:80-110`, `:300-330`). 루트 index만 `okf_version: "0.2"`를 가진다.
- [확인] `log.md`는 예약 파일로 제외만 한다(`index-sync.ts:16`, `src/agent/okf-middleware.ts:24`). 생성하는 코드는 찾지 못했다.
- [확인] 시간 정보는 `generated.at`(본문이 바뀐 시점), `.last-update.json`, manifest의 `completedRunId`에 흩어져 있다.

#### 13. 포맷 표준

입장: OKF v0.2를 출력 포맷으로 채택하고 코드로 검증한다.

- [확인] 필수 `type` 검사, `status`·`stale_after` 값 검사, ISO 8601 검사를 한다(`frontmatter.ts:152-250`).
- [확인] `generated`, `verified`, `sources`를 코드가 소유한다. `sources`에는 Claim 증거 resource를 투영한다(`src/okf/claim-sources.ts:38`).
- [확인] 알 수 없는 extension 필드는 보존한다(README "Front matter, provenance").
- [추정] OKF의 provenance·trust 필드를 실제 Claim 장부와 연결한 구현은 이번 조사 10개 중 openwiki 하나다 — 사례: OKF 보고서 #13 대응 표에서 native v0.2 producer는 openwiki 하나다. 다른 claim ledger 구현인 AgriciDaniel은 OKF 대응이 없다.

#### 14. 규모·비용

입장: 비용을 줄이는 장치는 코드로 있으나, 비용 수치는 저장소에 없다.

- [확인] 줄이는 장치: no-op은 모델 0회(`repository-run.ts:478-527`), wiki 밖 변경이 없는 페이지 fast-forward(`:915`, 4번 축 참고), issue Claim만 worker에 전달(`repository-prompts.ts:187-188`). 페이지 단위로 무엇을 건너뛸지는 대부분 planner 판단이다.
- [확인] context 방식: 페이지마다 새 worker를 띄운다(`repository-prompts.ts:122`). 긴 대화가 쌓이지 않는다.
- [확인] 밝힌 규모: 자기 wiki 22쪽·Claim 746개. 마지막 갱신 모델은 `z-ai/glm-5.2`다(`openwiki/.last-update.json`).
- [확인] 토큰·비용 수치는 README에도 커밋된 결과에도 없다. DeepSWE 하네스는 OpenWiki 생성 토큰을 수집하지 못한다고 스스로 밝힌다(`evals/deepswe/README.md:203-206`).
- [확인] Claim sidecar가 무겁다. version 문자열 하나가 수백 바이트이고 `.claims/`가 본문보다 크다(1.7MB).

#### 15. frosk1 비판 7가지에 대한 대응

| 비판 | 대응 | 강도 |
| --- | --- | --- |
| 1. 오류 누적 | 증거 해시가 바뀌면 Claim을 강제 재검토한다. LEDGER가 hallucination·stale 비율을 잰다 | [확인] 감지는 코드. [추정] confirm은 LLM 판단이라 잘못된 Claim이 "confirm"으로 굳을 수 있다 — 사례: `mutations.ts:86-96`이 confirm 때 version만 갱신한다 |
| 2. 부분 문맥 | worker가 seed 경로에서 출발해 저장소 전체를 도구로 탐색한다. planner는 baseline 이후 변경 경로 전체를 본다 | [확인] code 모드. personal은 24시간 창이라 대응 약함 |
| 3. 요약 손실 | 원본(소스 코드)이 그대로 남는다. AGENTS.md 블록이 "Treat source code and tests as authoritative"라고 지시한다(`src/ingestion/code-mode.ts:644`) | [확인] |
| 4. 가짜 source of truth | AGENTS.md 블록이 wiki를 "optional just-in-time context"로 규정한다(`src/ingestion/code-mode.ts:638`) | [추정] `verified` 스탬프가 오히려 신뢰를 부풀릴 수 있다 — 사례: 8번 축 confirm 경로 1곳 |
| 5. 환각 병합 | Claim마다 resolve되는 증거가 필수다. 존재하지 않는 파일은 거부한다 | [확인] 존재만 본다. 증거와 문장의 의미 일치는 코드가 보지 않는다 |
| 6. 운영 복잡도 | CI 템플릿 4종, 재개, 원자적 쓰기로 운영 부담을 흡수한다 | [확인] 대신 엔진 자체가 61k줄, 의존성 27개다 |
| 7. ingest 비용 | no-op 0회, 페이지 fast-forward, sparse reconciliation | [확인] 장치는 있다. 수치는 없다 |
| (8. staleness) | Claim drift 감지가 이 저장소의 중심 기능이다 | [확인] |

#### 16. 성숙도·차용 가능성

- 테스트: [확인] `test/`에 테스트 파일 205개, `evals/`에 36개다. CI가 format, lint, typecheck, build, `--dry-run --init`, 전체 vitest를 돈다(`.github/workflows/checks.yml:31-149`).
- 의존성: [확인] `deepagents`, `langchain`, `@langchain/*` 9종, MCP SDK, ink/react, posthog 등 27개다(`package.json:70-97`). Node 22.22 이상이 필요하다.
- 텔레메트리: [확인] 기본 켜짐이다. 끄려면 `OPENWIKI_TELEMETRY_DISABLED=1`이다(README "Telemetry").
- 라이선스: [확인] MIT다. 코드 차용이 가능하다.
- 차용 단위: [확인] `src/claims/core`와 `src/claims/evidence`(약 1.7k줄)는 node 내장과 `OpenWikiIgnore`만 쓴다. 이 층 분리는 테스트가 강제한다(`test/claims/core/architecture.test.ts`). [확인] `src/claims/` 전체(약 3.7k줄)는 그렇지 않다. `brains/code/runtime.ts`가 `okf/claims-verification` → `okf/frontmatter`를 거쳐 `yaml`과 `deepagents` 타입을 끌어온다. [추정] core와 evidence는 떼어 쓰기 쉽다. 근거는 import 목록과 architecture 테스트 2개다.
- 잔재: [확인] `integrations/openwiki/SKILL.md:192`에 "for the Tuesday integration"이라는 맥락 없는 문구가 남아 있다.

## 장점

- [확인] Claim version을 코드가 계산한다. 모델이 출처를 지어낼 수는 있어도 version은 지어낼 수 없다(`mutations.ts:138-167`).
- [확인] 줄 범위 증거가 코드 이동을 따라간다. 내용 해시와 앞뒤 3줄 context 해시로 재배치한다(`resolver.ts:424-507`). 줄 번호 인용의 약점(조금만 바뀌어도 깨짐)을 정면으로 푼다.
- [확인] stale을 숨길 수 없다. preflight가 no-op 판정보다 먼저 돈다. planner가 빠뜨려도 job이 강제된다(`repository-run.ts:478`, `page-jobs.ts:256`).
- [확인] sparse reconciliation이 context를 아낀다. worker는 issue Claim만 받는다(`repository-prompts.ts:187-188`).
- [확인] 페이지 단위 durability가 실제로 구현되어 있다. 페이지 complete = Markdown + Claim + verification + manifest가 모두 durable이다(`repository-run.ts:1367-1416`).
- [확인] native 모드의 쓰기 제한이 backend에서 강제된다. worker 하나가 페이지 하나만 쓴다(`repository-runner.ts:924-933`, `docs-only-backend.ts:582-597`).
- [확인] 평가 프레임워크가 설계 수준에서 정직하다. LEDGER는 supported·stale·invented·unverified를 같은 분모로 보고, unverified를 오류가 아닌 작업 목록으로 다룬다(`evals/ledger/README.md:19-44`).

## 단점

- [확인] 본문과 Claim의 일치를 검사하지 않는다(`guidance.ts:24`가 프롬프트뿐). 본문에서 사라진 주장의 Claim이 남아도, Claim에 없는 주장이 본문에 있어도 통과한다.
- [확인] 증거와 문장의 의미 관계를 검사하지 않는다. 아무 범위나 resolve되면 받는다.
- [확인] 인용 범위 밖의 변경은 Claim으로 잡히지 않는다. 새 파일에 생긴 동작은 planner가 changed paths를 보고 판단해야 한다(`repository-prompts.ts:26-36`).
- [확인] 파일 전체 증거는 너무 민감하다. 무관한 줄 하나로도 stale이 된다(`resolver.ts:237-239`). 다만 기본값은 아니다. 프롬프트가 두 형태를 나란히 예시로 든다(`repository-prompts.ts:177-178`). 자기 wiki에서는 증거 1,669개 중 18개만 범위가 없다.
- [확인] personal 모드에는 Claim, page queue, 재개가 없다. 모두 code 모드 전용이다(`runtime.ts:72-73`, `index.ts:187`). 결정적 finalize(Mermaid, index, link 스탬프)와 shell 금지는 personal 모드에도 돈다(`src/agent/okf-middleware.ts:102-118`).
- [확인] host 모드의 쓰기 제한은 skill 문서뿐이다(`SKILL.md:183-195`).
- [확인] 프로세스 간 lock이 없다(`repository-run.ts:341`).
- [확인] 무겁다. 61k줄, provider 14개, connector 9개, host 9개, 텔레메트리 기본 켜짐이다.
- [확인] 평가 수치를 저장소에서 재현할 근거가 없다. 아래 "확인하지 못한 것"에 적는다.

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

| 무엇 | 왜 | 개인 지식 wiki로 옮길 때 |
| --- | --- | --- |
| `{resource, version}` Claim 모델과 "version은 코드가 붙인다" 규칙 | 출처 위조를 구조로 막는다 | `raw://<file>#L10-L20`. raw 노트·클리핑은 텍스트라 resolver가 그대로 돈다 |
| 줄 범위 + 앞뒤 context 해시 재배치(`resolver.ts:294-507`) | 원문이 조금 고쳐져도 인용이 살아남는다 | 내가 계속 고치는 노트(raw가 불변이 아닌 경우)에서 특히 쓸모 있다. 웹 클리핑처럼 불변이면 이득이 작다 |
| preflight → stale/unresolved → 해당 페이지 강제 job | 원문 수정이 wiki에 반영됐는지 기계적으로 안다 | raw 폴더 변경 후 `lint`의 결정적 단계로 둔다 |
| confirm/update/retract 세 결정만 허용 + 결정 누락 시 거부 | LLM이 stale을 조용히 넘기지 못한다 | 그대로 옮긴다 |
| sparse reconciliation(issue Claim만 프롬프트에) | context와 비용을 아낀다 | 그대로 옮긴다 |
| no-op은 모델 0회 | 매일 돌려도 비용이 0에 가깝다 | 그대로 옮긴다 |
| 페이지 단위 job + tmp/rename 원자적 쓰기 + `.run.json` | 중간에 끊겨도 완료한 페이지는 남는다 | 소스 하나가 여러 페이지를 건드리는 ingest에 그대로 맞는다 |
| index를 frontmatter에서 결정적으로 재생성 | LLM이 목차를 틀리게 고칠 일이 없다 | 그대로 옮긴다 |
| 깨진 링크를 실패 대신 주석 스탬프로 남김 | run을 멈추지 않고 부채를 눈에 보이게 한다 | 스탬프만 가져오면 부족하다. OpenWiki code 모드에서는 "다음 run이 고친다"가 연결되어 있지 않다(6번 축). 스탬프된 페이지를 다음 lint의 job으로 넣는 단계를 함께 만든다 |
| LEDGER의 4상태 단일 분모 지표 | wiki 품질을 한 숫자로 추적한다 | 원문이 git에 있으면 checkpoint replay도 가능하다 |

### 피할 것

- 본문과 Claim을 따로 두는 구조를 그대로 쓰지 않는다. 내 wiki에서는 본문 문장에 Claim id를 각주로 달아 결정적 lint로 대조하는 쪽이 낫다. 대가는 본문이 덜 깨끗해지는 것이다.
- `verified` 같은 이름을 "해시 일치"에 붙이지 않는다. `evidence_current` 같이 실제 뜻대로 부른다.
- 파일 전체 증거를 허용하더라도 경고 없이 받지 않는다. OpenWiki는 기본값으로 두지는 않지만 막지도 않는다. 범위 없는 인용은 lint 경고로 둔다.
- personal 모드의 "24시간 창 + 프롬프트 규칙" 방식은 가져오지 않는다. 이 저장소의 강점이 전부 빠진 경로다.
- 엔진 전체(Deep Agents, provider 14개)를 들여오지 않는다. `src/claims/`만 떼어 쓴다.

## 확인하지 못한 것

- "WikiBench"라는 이름을 저장소, 이슈, PR 어디에서도 찾지 못했다. discovery 단계의 "WikiBench로 평가했다"는 이 저장소로는 뒷받침되지 않는다. 저장소에 있는 평가는 LEDGER(`evals/ledger/`, PR #622)와 DeepSWE paired 평가(`evals/deepswe/`)다. 블로그 등 저장소 밖 자료를 보면 확인할 수 있다.
- LEDGER·DeepSWE의 실제 결과 수치는 저장소에 없다. `results/`, `summaries/`, `evals/ledger/.results/`가 모두 gitignore 대상이다(`.gitignore:23-32`). `evals/ledger/README.md:172`의 "LEDGER score 89%"는 출력 형식 예시로 보인다. 재현하려면 benchmark bundle(calc, taskflow)과 API 비용이 필요하다. 실행하지 않았다.
- LEDGER evaluator가 LLM judge라는 점의 신뢰도는 gold-agreement 0.90 하한으로 관리한다고 적혀 있다(`evals/ledger/meta/README.md`). live tier는 opt-in이라 실제 일치율 기록은 보지 못했다.
- 범위 재배치 알고리즘이 실제 리팩터링에서 얼마나 자주 `null`(unresolved)로 떨어지는지는 실행하지 않아 모른다. `test/claims/evidence/repository/resolver.test.ts`에 이동·확장·삭제·모호 anchor 사례 테스트는 있다. 빈도는 자기 wiki의 git 이력에서 unresolved 수를 세면 알 수 있다. clone이 shallow라 이번에는 셀 수 없었다.
- 사람이 wiki 페이지 본문을 고쳐 커밋했을 때의 동작은 실행하지 않았다. [추정] no-op 경로가 `replaceRepositoryPageManifest`에서 sidecar `pageVersion`과 본문 해시가 다르다고 `Cannot advance page coverage` 오류를 던질 것이다 — 사례: `page-manifest.ts:310-315`가 `buildManifestEntry`를 예외 처리 없이 부르고, `:405-411`이 해시 불일치에서 던지는 경로 1개. 조용히 넘어가지는 않지만 친절한 처리도 아닐 수 있다.
- native run과 host run이 동시에 같은 저장소를 쓸 때의 동작은 실행해 보지 않았다.
- 1회 init·update의 토큰과 비용은 저장소 어디에도 없다. LangSmith trace를 보면 알 수 있다고 README가 말한다.

## 검증 기록

적대적 검증 단계에서 코드와 대조해 고친 것이다. 한 줄에 하나씩 적는다.

- 자기 wiki 페이지 수를 21에서 22로 고쳤다. `openwiki/` 안 비-index 페이지와 `.claims/` sidecar가 모두 22개다.
- 테스트 파일 수 229를 `test/` 205개 + `evals/` 36개로 고쳤다. `test/` 줄 수도 약 57k에서 약 60k로 고쳤다.
- `package.json:840-868` 인용을 `:70-97`로 고쳤다. 파일은 131줄이다. `@langchain/*`는 7종이 아니라 9종이다.
- `README.md:759-761`, `:768` 인용을 `src/ingestion/code-mode.ts:638`, `:647`로 옮겼다. README는 754줄이고 해당 문구가 없다.
- MCP 도구 수를 "6개"에서 "생성용 6개 + 검색용 4개 = 10개"로 보탰다.
- 깨진 링크 "다음 update가 고친다"를 code 모드에서는 연결되어 있지 않다고 고쳤다. 지시문은 personal 모드 프롬프트에만 있고, 스탬프된 페이지를 job으로 넣는 코드가 없다.
- 가져올 것 표의 깨진 링크 행을 "스탬프 + 다음 lint의 job 연결을 함께 만든다"로 바꿨다.
- fast-forward를 "바뀌지 않은 페이지"에서 "그 페이지 baseline 이후 저장소 전체에 wiki 밖 변경이 없을 때만"으로 좁혔다.
- host 소스 수정 감지를 [추정]에서 [확인]으로 올렸다. resume 경로 외에 `finishRepositoryRun`의 fingerprint 재검사가 있다.
- "issue가 남은 페이지는 finalize 거부"를 "finalize는 경고로 넘기고 durability 증명이 submit을 거부한다"로 고쳤다.
- 검색 정렬을 "BM25 + 경로 boost"에서 "경로 일치 → 질의어 일치 수 → BM25" 순서로 고쳤다.
- OS 스케줄러를 "launchd 등"에서 "macOS launchd만"으로 고쳤다.
- personal connector 수를 8종에서 9종으로 맞췄다.
- custom-mcp read-only 제한의 근거를 README에서 `mcp-runtime.ts:202-226`으로 옮겼다. 판정이 서버의 `readOnlyHint` 자기 신고에 기댄다는 점을 보탰다.
- Mermaid 강등 근거를 README에서 `src/mermaid/validate.ts:166`으로 옮겼다.
- `src/claims/`가 LangChain 의존이 없다는 주장을 core·evidence(약 1.7k줄)로 좁혔다. `brains/code/runtime.ts`는 `okf/frontmatter`를 거쳐 `yaml`과 `deepagents` 타입을 끌어온다.
- core·evidence 층 분리를 강제하는 `test/claims/core/architecture.test.ts`를 보탰다.
- 파일 전체 증거 약점에 "기본값은 아니고, 자기 wiki 1,669개 증거 중 18개"를 보탰다. 피할 것 문장도 그에 맞췄다.
- personal 모드 약점에 결정적 finalize와 shell 금지는 personal에도 돈다는 점을 보탰다.
- 언어 변경 시 전체 rewrite job 강제를 4번 축에 보탰다.
- "LEDGER score 89%"의 위치를 README가 아니라 `evals/ledger/README.md:172`로 밝혔다.
- 재배치 테스트(`resolver.test.ts`)가 있다는 점과, 사람이 wiki 본문을 고쳐 커밋했을 때의 [추정] 동작을 확인하지 못한 것에 보탰다.
- 줄 번호를 고쳤다: `.run.json` 삭제 `:1747`→`:1748`, worker 쓰기 제한 `:920-928`→`:924-933`.
- 비교 검토 단계: #13의 "다른 보고서가 아직 없어 사례 0건" [추정]을 다른 9개 보고서와 대조한 결과로 바꿨다.

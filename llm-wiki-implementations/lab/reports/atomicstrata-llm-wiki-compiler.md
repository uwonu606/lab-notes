# atomicstrata/llm-wiki-compiler — LLM은 도구 없는 텍스트 함수로만 쓰고, 모든 쓰기는 코드의 planner·journal을 거치는 "지식 compiler"

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/atomicstrata/llm-wiki-compiler |
| clone commit | `a3eb447` (2026-10-09, shallow clone) |
| 별·fork | 2,177 · 234 (`gh api`, 2026-10-11 조회) |
| 최근 push | 2026-10-10 |
| 라이선스 | MIT |
| 형태 | TypeScript CLI(`llmwiki`) + MCP 서버(`llmwiki serve`) + SDK(`createWiki`) + 로컬 viewer |
| 코드 규모 | `src/` TypeScript 1,100개 파일, 170,980줄. `packages/` 570줄. 테스트 `.test.ts` 1,352개, 167,165줄(helper를 포함한 `test/` 아래 `.ts` 전체는 186,712줄) |
| 버전 | 1.4.2 (`package.json:3`) |

[확인] 코드의 절반 가까이는 wiki compile 자체가 아니다.
`src/preparations/`(30k줄), `src/capability-providers/`(15k줄), `src/operation-bundles/`(11k줄), `src/operations-packs/`(10k줄)이 가장 크다.
[확인] compile 핵심인 `src/compiler/`는 8,946줄이다.
`src/linter/`는 1,690줄, `src/citations/`는 353줄이다.

## 한 바퀴 흐름

1. **ingest** — `llmwiki ingest <url|file>`가 `src/commands/ingest.ts:288` `ingestSource`를 부른다.
   - 형식을 감지한다(`detectSourceType`, `:193`).
   - web은 Readability+turndown, PDF는 pdf-parse, 이미지는 LLM vision, YouTube는 transcript로 바꾼다(`src/ingest/*.ts`).
   - 100,000자를 넘으면 잘라 낸다(`:143` `enforceCharLimit`, `src/utils/constants.ts:7`).
   - frontmatter(`title`, `source`, `ingestedAt`, `truncated`)를 붙여 `sources/`에 저장한다(`:211` `buildDocument`).
   - `log.md`에 한 줄을 덧붙인다(`:259` `journalIngest`).
   - ingest는 LLM으로 wiki를 건드리지 않는다. 원문을 복사·변환할 뿐이다.
2. **compile** — `llmwiki compile`가 `src/compiler/index.ts:119` `compileAndReport`를 부른다.
   - 프로젝트 lock을 잡는다(`:125`).
   - 지난번에 끝나지 않은 쓰기 journal을 먼저 되돌린다(`:140` `recoverJournalBeforeCompile`).
   - `.llmwiki/state.json`의 SHA-256과 비교해 new/changed/deleted를 가른다(`:417` `detectChanges`).
   - 바뀐 source와 concept을 공유하는 다른 source도 다시 처리 대상에 넣는다(`:424`, `src/compiler/deps.ts:126` `findAffectedSources`).
   - **Phase 1 추출**: source 하나마다 LLM을 한 번 부른다(`src/compiler/extraction-phase.ts:143-144`).
     - prompt에는 source 전문과 현재 `wiki/index.md`가 들어간다.
     - LLM은 `extract_concepts` tool로 concept 3~8개를 돌려준다(`src/compiler/prompts.ts:93-191`).
     - concept마다 `confidence`, `provenance_state`, `contradicted_by`를 함께 받는다.
   - **merge**: concept 제목을 `slugify`한 값이 같으면 한 페이지로 합친다(`src/compiler/extraction-merge.ts:38-65`).
     - 합친 concept의 confidence는 최솟값을 쓴다(`:80-108`).
   - **Phase 2 페이지 생성**: concept마다 LLM을 한 번 부른다(`src/compiler/page-renderer.ts:48-83`).
     - prompt에는 줄 번호를 붙인 원문(`src/compiler/prompt-budget.ts:85-91`)이 들어간다.
     - 기존 페이지 전문과 "관련 페이지" 5개, 허용된 wikilink 목록도 들어간다.
     - LLM은 문단 끝마다 `^[file.md:START-END]`를 달도록 지시받는다(`src/compiler/prompts.ts:197-215`).
   - 결정적 후처리가 citation을 고친다(`src/compiler/citation-normalize.ts:145-193`).
     - 파일명 없는 `^[81]`은 source가 하나일 때만 `file.md:81`로 바꾼다. 이때 범위를 넘는 번호는 버린다.
     - source가 여럿이면 파일명 없는 번호를 버린다.
     - 파일명이 이 페이지의 source와 맞는 `^[file.md:N-M]`은 범위를 보지 않고 그대로 둔다(`:91-92`). 범위 초과는 뒤의 lint만 잡는다.
   - review gate를 판단한다(`src/compiler/review-pipeline.ts:61-99`).
     - 생성된 페이지에 schema lint와 citation lint를 바로 돌린다.
     - review policy가 걸리면 `.llmwiki/candidates/`에 후보로 저장한다.
     - 걸리지 않으면 live write로 넘긴다.
   - live write는 trust planner를 거쳐 하나의 journal batch로 적용된다(`src/compiler/index.ts:230-247`, `src/compiler/compile-write.ts:137-151`).
   - 마무리 단계(`src/compiler/index.ts:636-688`)는 아래 순서로 돈다.
     - 제목 문자열로 wikilink를 결정적으로 건다(`resolveAndApplyLinks`, `:655`).
     - LLM이 잘못 쓴 link를 고친다(`repairAndApplyLinks`, `:660`).
     - `state.json`을 단 한 번 flush한다(`:682`).
     - `index.md`와 MOC를 재생성한다(`:685-686`).
     - embedding을 갱신한다(`:687`).
3. **query** — `llmwiki query "q"`가 `src/commands/query.ts`를 부른다.
   - 페이지를 고른다(`src/commands/query-selection.ts:98`).
   - 페이지 선택 순서는 이렇다. chunk embedding 상위 30개를 BM25로 rerank해 12개를 남기고, 그 chunk의 부모 페이지를 최대 5개 고른다(`:197-216`). chunk 결과가 없으면 page embedding 상위 15개를 LLM이 고른다. embedding store가 없으면 LLM이 live 페이지 후보 목록에서 고른다(`:123-133`).
   - 고른 페이지 전문으로 답을 만든다(`src/commands/query.ts:77-108`). 답은 `[[Page]]` wikilink로 출처를 단다.
   - `--save`이면 lock을 잡고 링크를 다시 검증한다(`src/commands/query-publication.ts:68-85`). 그다음 `wiki/queries/`에 저장하거나, `--review`이면 후보로 둔다.
4. **lint** — `llmwiki lint`가 `src/linter/index.ts:148` `lint`를 부른다.
   - 규칙마다 "deterministic / provider-judgement / derived-view" tier를 단다(`:46-73`).
   - citation 검사는 원문 파일 존재와 줄 범위가 파일 길이 안에 드는지만 본다(`src/linter/rules-citations.ts:89-138`).
   - 인용된 줄이 실제로 주장을 뒷받침하는지는 `llmwiki eval --suite full`의 LLM judge가 표본으로 본다(`src/eval/citation-support.ts:1-11`).

## 축별 분석

#### 1. 실행 형태

입장: CLI·SDK 엔진이다. 그 위에 MCP 서버와 읽기 전용 웹 viewer가 붙는다.

- [확인] 실행 파일은 `llmwiki` 하나다. SDK `createWiki`와 MCP 서버가 같은 compiler 서비스를 공유한다(`package.json:16-18`, `ARCHITECTURE.md` "Compiler and query flow").
- [확인] MCP 도구는 `src/mcp/tools.ts`, `okf-tools.ts`, `workflow-action-tools.ts`에 `registerTool`로 등록된다.
- [확인] Agent Skill 파일 `skills/llmwiki/SKILL.md`(68줄)는 "status → context pack → read_page"로 읽는 순서를 안내한다. 쓰기 쪽 주의도 몇 줄 담는다. `ingest_source`·`compile_wiki`는 mutation이라는 것, MCP `compile_wiki`에는 review 인자가 없다는 것, 이 skill을 게시 승인으로 여기지 말라는 것이다(`skills/llmwiki/SKILL.md:47-55`).
- [확인] MCP `compile_wiki`는 입력이 없다(`inputSchema: {}`, `src/mcp/tools.ts:80-84`). 그래서 MCP로 붙은 agent는 `.llmwiki/config.json`에 review policy가 없으면 live 쓰기만 할 수 있다.
- [확인] 페이지 본문 생성 호출은 도구 없이 한다. Claude Agent SDK provider는 `tools: []`, `allowedTools: []`, `settingSources: []`로 부른다(`src/providers/claude-agent.ts:154-158`).
- [확인] 다만 "도구 0개"는 본문 생성에만 맞다. concept 추출과 eval judge는 구조화 출력용 도구 하나(`extract_concepts`, `judge_citation`)를 강제로 부르게 한다(`src/compiler/prompts.ts:93-96`, `src/eval/citation-support.ts:44-46`). Claude Agent SDK에서는 이 도구를 in-process MCP 도구로 만든다. 핸들러는 "ok"만 돌려주고, 내장 도구는 모두 끈다(`src/providers/claude-agent.ts:180-213`). 부수효과가 있는 도구는 없다. 파일을 쓰는 주체는 항상 코드다.

#### 2. 규칙의 위치

입장: 코드 강제가 기본이다. prompt는 생성 품질만 담당하고, 쓰기 허가는 코드가 정한다.

- [확인] prompt 쪽 규칙은 `src/compiler/prompts.ts`에 상수로 박혀 있다. 사용자가 바꿀 수 있는 것은 `--instructions`(system policy)뿐이다.
- [확인] 코드 스스로 prompt 규칙을 "advisory prompt text, not an enforceable boundary"라고 적는다. "Anything that must hold should be a lint rule or a trust gate"라고도 적는다(`src/compiler/prompts.ts:61-64`).
- [확인] 모든 페이지 쓰기는 `planPageMutation`을 지난다(`src/trust/planner.ts:1-24`). 이 planner가 네 가지 mandatory check를 돈다(`src/trust/checks.ts:1-31`).
  - 경로 confinement
  - 덮어쓰기 충돌
  - 크기 제한
  - frontmatter 파싱
- [확인] profile이 이 네 check를 끌 수 없다. check 함수가 profile 인자를 받지 않는 구조로 이를 막는다(`src/trust/checks.ts:4-11`).
- [확인] compile 쓰기에서는 덮어쓰기 충돌 check가 사실상 빠진다. compile은 `allowOverwrite: true`로 planner를 부르고, 이 값이면 기존 파일을 충돌이 아니라 update로 본다(`src/compiler/compile-write.ts:104`, `src/trust/checks.ts:17-20`). 크기 제한도 compile 출처는 500,000자다(`src/utils/constants.ts:25`).
- [확인] typed page(profile entity)의 live write는 `validateLiveTypedPage`를 지난다(`src/trust/typed-page-validate.ts:144-152`). 이 함수가 field contract → lifecycle FSM → relation-count·artifact 존재 조건을 순서대로 검사한다.
- [확인] 호출 지점은 review 승인(`src/trust/promote.ts:112`)과 local workflow host(`src/local-workflow-host/page-operations.ts:32`)다.
- [확인] `trust:` workflow gate의 자동 적용은 환경변수 `LLMWIKI_TRUSTED_WRITE`로만 열린다(`src/trust/trusted-write.ts:1-51`). 설정을 `.llmwiki/`가 아니라 프로세스 환경에 둔 것은 "agent가 sync 가능한 workspace에서 스스로 권한을 줄 수 없게" 하려는 의도다.
- [확인] commit gate도 있다. 이것은 wiki 프로젝트가 아니라 이 저장소 개발용이다. `.husky/pre-commit`은 fallow와 `tsc --noEmit`만 돈다. build와 test는 `.husky/pre-push`가 돈다.
- [확인] **기본 compile 경로(concept 페이지)에는 profile gate가 걸리지 않는다.** compile은 `kind: "raw"` target으로 planner를 부른다(`src/compiler/compile-write.ts:98-105`). 그래서 floor check만 받는다. lifecycle·relation gate는 profile entity 페이지 경로에만 있다.
- [확인] 이것은 README와 어긋나는 것이 아니다. README "Quality and safety model"은 profile floor가 걸리는 쓰기 표면을 "page, lifecycle, workflow, import, and approval"로 적는다. lifecycle·relation·artifact는 profile entity 개념이라 concept 페이지에는 검사할 필드 자체가 없다. 문제는 README 문구가 아니라, 기본 concept 페이지에 내용 gate가 없다는 사실이다.

#### 3. 저장 구조

입장: `sources/`(원문), `wiki/`(생성물), `.llmwiki/`(상태·후보·journal) 세 갈래다. 상태 파일이 많다.

- [확인] 디렉터리 구성은 README "What llmwiki creates"에 있다. `wiki/concepts/`, `wiki/queries/`, profile entity별 `wiki/<entity>/`, `wiki/graph/`(typed relation), `wiki/index.md`, `log.md`, `artifacts/`(hash-pinned 파일)이 있다.
- [확인] `.llmwiki/` 아래 파일은 이렇다.
  - `profile.json`, `config.json`(review policy), `schema.json`(page kind·cross-link 규칙)
  - `state.json`(source hash → concept slug 소유 관계)
  - `candidates/`, `journal/`, `workflows/`, `eval/`
- [확인] concept 페이지 frontmatter는 `title`, `summary`, `sources`, `kind`, `createdAt`, `updatedAt`, tags·aliases(Obsidian용)를 담는다. 거기에 provenance(`confidence`, `provenanceState`, `contradictedBy`)와 model provenance가 붙는다(`src/compiler/page-renderer.ts:89-111`).
- [확인] page kind는 `concept`, `entity`, `comparison`, `overview`다. concept 외 kind는 `schema.json`에 선언한 seed page로만 만들어진다(`src/compiler/prompts.ts:355-377`, `src/compiler/seed-pages.ts`).
- [확인] profile은 entity 타입마다 디렉터리·필드 타입·lifecycle을 선언한다(`src/profile/types.ts:162`, `:365`, `:423`). 예시는 AutoSci의 papers·ideas·experiments다(`src/profile/templates/builtin/autosci/entities.ts`).

#### 4. Ingest

입장: 사람이 source를 넣으면 compile이 자동으로 페이지를 쓴다. 증분 추적과 crash 복구는 강하다. 큰 원문은 잘린다.

- 사람 참여: [확인] 기본 review policy는 `off`다(`src/review/config.ts:17-20`). config가 없으면 생성 페이지가 바로 live로 쓰인다. `--review`나 `review.hold` 설정이 있을 때만 후보로 멈춘다.
- 증분: [확인] SHA-256과 prompt-modifier digest를 함께 비교한다(`src/compiler/index.ts:417-421`). 출력 언어나 system policy가 바뀌면 원문이 같아도 다시 만든다.
- 공유 concept: [확인] 한 concept을 여러 source가 공유하면 그중 하나만 바뀌어도 나머지 소유 source를 다시 읽는다(`src/compiler/deps.ts:1-13`, `:126`). 그래서 merge 페이지가 한쪽 source 내용만으로 다시 쓰이지 않는다.
- crash 복구:
  - [확인] 페이지 쓰기는 pre-state를 기록한 journal batch로 묶인다. 중간에 죽으면 다음 compile 시작 시 전체를 pre-state로 되돌린다(`src/trust/journal.ts:1-27`).
  - [확인] `state.json`은 링크 해석까지 끝난 뒤 한 번만 flush한다(`src/compiler/index.ts:663-683`).
  - [확인] embedding 실패는 별도 pending/retry 큐에 남는다(`src/compiler/index.ts:690-728`).
- 자동 감시: [확인] `llmwiki watch`가 chokidar로 `sources/`를 보고 500ms debounce 뒤 compile을 돈다(`src/commands/watch.ts:1-17`).
- 멀티포맷: [확인] web·PDF·이미지(vision)·YouTube transcript·`.md/.txt`·Claude/Codex/Cursor 세션 export를 받는다(`src/ingest/`, `src/commands/ingest-session.ts`).
- 원문 크기: [확인] ingest 단계에서 100,000자로 자른다(`src/commands/ingest.ts:143-160`). compile 단계에서도 concept당 합친 원문을 기본 200,000자로 자른다. 자르는 방식은 source별 균등 앞부분 절단이다(`src/compiler/prompt-budget.ts:59-79`, `src/utils/constants.ts:44`). 코드 주석도 이것을 "deliberately defensive … rather than smart"라고 적는다(`:11-13`).
- 규칙 추출: [확인] `rules extract`는 compile과 별개 명령이다. 바뀐 source에서 LLM이 규칙을 뽑아 `.llmwiki/rule-candidates/`에 후보로 둔다. 사람이 approve·reject하고 `rules export`로 JSON을 내보낸다(`src/commands/rules.ts:1-15`). compile 코드는 이 후보를 읽지 않는다. `rule-extractor`를 import하는 곳은 `src/commands/rules.ts` 하나다. 코드 주석이 말하는 "learning loop"는 외부 "rule importer" 쪽에서 닫힌다.
- 소스 하나가 건드리는 페이지 수: [확인] 추출 prompt가 3~8개 concept을 요구한다(`src/compiler/prompts.ts:172`). 그 위에 공유 concept 전파와 link resolution이 다른 페이지 본문을 더 고친다.

#### 5. 근거 추적 단위

입장: 줄 범위다. 문단 끝 `^[file.md:N-M]`이 단위다. 형식과 범위는 결정적으로 검사한다. 내용 지지 여부는 선택적 LLM 표본 검사다.

- [확인] LLM에게 줄 번호를 붙인 원문(` 42 | text`)을 보여 주고 `^[file.md:START-END]`를 쓰게 한다(`src/compiler/prompt-budget.ts:85-91`, `src/compiler/prompts.ts:197-215`).
- [확인] 추론한 문단은 citation 없이 두라고 지시한다. 이후 lint가 "uncited = inferred"로 센다(`src/compiler/prompts.ts:212-214`).
- [확인] 결정적 검사는 파일 존재, 문법(`file.md`, `file.md:N-N`, `file.md:N,N-M`, `file.md#LN-LN`), 줄 번호 상한 세 가지다(`src/linter/rules-citations.ts:89-189`).
- [확인] lint는 인용 파일이 `sources/`에 있는지만 본다. 그 파일이 페이지 frontmatter `sources`에 들어 있는지는 보지 않는다(`src/linter/rules-citations.ts:114-116`).
- [확인] compile 때 normalizer가 범위를 보는 것은 파일명 없는 번호뿐이다. 파일명이 맞는 citation은 범위를 넘어도 그대로 쓰인다(`src/compiler/citation-normalize.ts:91-92`).
- [확인] 원문 글자 일치 검사는 없다. 인용 줄이 주장을 뒷받침하는지는 `eval --suite full`이 LLM judge(0/1/2점)로 표본만 본다. 결과는 `.llmwiki/eval/citation-cache.jsonl`에 캐시한다(`src/eval/citation-support.ts:1-11`, `:43-60`).
- [확인] 줄 번호는 `sources/` 안 변환본 기준이다. 변환본 맨 위에는 ingest frontmatter가 있다. 그래서 prompt와 judge 모두 "frontmatter 줄을 근거로 쓰지 마라"는 문장을 따로 둔다(`src/compiler/prompts.ts:207-209`, `src/eval/citation-support.ts:62`).
- [확인] claim ledger는 없다. 근거는 페이지 본문 안의 marker로만 남는다.
- [확인] query 답의 근거 단위는 원문 줄이 아니라 wiki 페이지(`[[Page]]`)다(`src/commands/query.ts:77-80`). ARCHITECTURE.md도 "Citation resolution establishes link validity, not factual support"라고 적는다.

#### 6. Link

입장: LLM이 허용된 목록 안에서 link를 제안한다. 코드가 제목 매칭으로 link를 더 걸고 잘못된 link를 고친다. backlink는 저장하지 않고 필요할 때 계산한다.

- [확인] page prompt에 "이 목록에 있는 페이지에만 link하라"는 허용 목록을 준다(`src/compiler/prompts.ts:225-238`).
- [확인] compile 마무리에서 `resolveAndApplyLinks`가 LLM 없이 제목 언급을 `[[slug|Title]]`로 바꾼다(`src/compiler/resolver.ts:1-10`, `:230`). 비용은 증분일 때 O(changed × total)이고 전체 재compile이면 O(total²)이다.
- [확인] `repairAndApplyLinks`가 LLM이 쓴 짧은 이름 link를 실제 slug로 고친다(`src/compiler/index.ts:656-660`).
- [확인] typed relation은 profile이 선언한다. 저장은 `wiki/graph/`의 relation store가 맡는다(`src/profile/types.ts:200`, `src/relations/`).
- [확인] context pack은 viewer snapshot의 graph로 1~2 hop 이웃을 펼친다(`src/context/graph.ts:1-30`).

#### 7. Lint

입장: lint는 전부 결정적이다. LLM 판단이 필요한 것은 `eval`로 분리했다. 자동 수정은 거의 하지 않는다.

- [확인] `lint`는 LLM을 부르지 않는다. "provider-judgement" tier 규칙(low-confidence, contradicted, inferred-without-citations)도 LLM이 compile 때 써 둔 frontmatter 값을 읽을 뿐이다(`src/linter/index.ts:46-62`).
- [확인] 검사 항목은 다음과 같다(`src/linter/index.ts:46-73`).
  - broken wikilink, orphan page, summary 누락, 중복 제목, 빈 페이지
  - broken·malformed citation, schema cross-link 최소 개수, stale page
  - journal 상태, pending embedding, workflow run 상태
  - non-default profile이면 field·lifecycle·relation·artifact standing 검사를 덧붙인다(`:100-114`).
- [확인] 중복 검사는 제목을 소문자로 바꿔 정확히 같은지만 본다(`src/linter/rules.ts:189-218`). 의미가 같은데 이름이 다른 concept은 잡지 못한다.
- [확인] 자동 수정은 "제목으로 쓴 wikilink를 slug로 바꾸기" 한 종류뿐이다. 그것도 계획(data)으로만 내놓는다. 적용은 일반 리뷰 경로를 거친다(`src/linter/fix-plan.ts:7-19`).
- [확인] commit gate는 없다. 대신 CI용으로 `lint`·`eval` 임계값을 걸 수 있다(`docs/guides/ci-quality-gates.mdx`).
- [확인] compile 중에도 같은 citation·schema lint를 후보 본문에 돌린다. 결과는 review policy 신호로 쓴다(`src/compiler/review-pipeline.ts:102-121`, `:177-189`).

#### 8. stale·모순 처리

입장: drift는 hash로 감지하고 다시 생성한다. 모순은 LLM이 표시한 값을 그대로 flag로 남긴다. supersede 개념은 없다.

- [확인] freshness는 저장하지 않는다. 매번 `state.json` hash와 현재 source hash로 계산한다(`src/freshness/index.ts:1-24`).
- [확인] 상태 값은 fresh / stale / orphaned / unverified다. typed entity 페이지는 source 소유 기록이 없어 항상 `unverified`다(`src/freshness/index.ts:26-35`).
- [확인] `refresh --stale`은 stale 페이지 소유 source만 다시 compile한다(`src/commands/refresh.ts`).
- [확인] `rm <source>`는 그 source만 소유한 페이지를 지운다(`src/commands/rm.ts:1-25`).
- [확인] `rm` 없이 source 파일만 지우고 compile하면 다르게 처리한다. 그 source만 소유한 페이지는 지우지 않고 frontmatter에 `orphaned: true`를 붙인다(`src/compiler/orphan.ts:1-11`).
- [확인] source가 삭제되면 남은 공동 소유 source만으로 페이지를 깨끗이 다시 만든다. 이때 기존 페이지를 prompt에서 빼는 `rebuild` 표시를 쓴다(`src/compiler/page-renderer.ts:61`, `src/compiler/extraction-merge.ts:57`).
- [확인] 일반 업데이트는 덮어쓰기다. 기존 페이지 전문을 prompt에 넣고 LLM이 페이지 전체를 다시 쓴다(`src/compiler/prompts.ts:264-266`, `src/compiler/page-renderer.ts:53-65`). 기존 내용을 문단 단위로 보존하거나 diff하는 장치는 없다.
- [확인] 모순은 extraction 단계에서 LLM이 `contradicted_by`를 채울 때만 생긴다(`src/compiler/prompts.ts:133-144`). 여러 source가 합쳐지면 합집합을 취한다(`src/compiler/extraction-merge.ts:97-106`).
- [확인] `review.hold`에 `contradicted`를 넣으면 그 페이지를 사람 리뷰로 보낸다(`src/review/policy.ts:21-29`).

#### 9. 사람 개입

입장: 기본은 자율이다. 리뷰 큐를 켤 수 있다. profile workflow에서는 human/agent/trust gate를 선언할 수 있다.

- [확인] 기본 compile은 사람 승인 없이 live로 쓴다(`src/review/config.ts:17-20`).
- [확인] 리뷰 큐 명령은 `review list/show/approve/reject`와 batch approve다(`src/commands/review-*.ts`).
- [확인] 큐에 들어가는 이유 코드는 low-confidence, contradicted, schema-violating, provenance-violating, all, manual-review-requested, imported-okf, connector-fetched다(`src/review/policy.ts:21-29`).
- [확인] OKF import와 connector가 가져온 외부 데이터는 기본으로 후보가 된다(README "Open Knowledge Format", `src/review/policy.ts:28-29`).
- [확인] workflow stage는 `gate: "<trust|human|agent>:<id>"`를 가진다(`src/profile/types.ts:232-233`). 예시는 AutoSci의 `synthesize-topic`(`human:curated`)과 `design-experiment`(`agent:reviewed`)다(`src/profile/templates/builtin/autosci/workflows.ts:12-50`).
- [확인] `human:` gate는 `human` actor만 승인할 수 있다. agent는 human gate를 통과시킬 수 없다(`src/local-workflows/gate.ts:1-13`).
- [확인] `human` actor를 만드는 길은 CLI의 대화형 TTY 확인 하나다.
  - CLI `workflow gate approve`는 human gate를 만나면 터미널 확인을 받는다. 확인이 없으면 승인하지 않는다(`src/commands/workflow-gate.ts:38-50`).
  - `--actor` 플래그로는 human을 고를 수 없다(`src/commands/workflow-gate.ts:22-29`).
  - workflow action 경로도 stdin·stdout이 TTY가 아니면 거부한다(`src/local-workflows/run-action.ts:178-195`).
  - SDK는 `actorKind: "human"` 요청을 lock을 잡기 전에 거부한다(`src/sdk/workflow-facade.ts:42-57`).
- [추정] TTY 확인은 사람의 신원 증명이 아니다. pty를 다룰 수 있는 agent라면 확인 프롬프트에 답할 수 있다. 근거는 확인 함수가 TTY 여부와 입력만 본다는 구조 1건이다(`src/local-workflows/approve-human-interactively.ts:10-19`). 실제로 우회되는지는 실행해 보지 않았다.
- [확인] query 답을 저장할 때도 `--save --review`로 리뷰를 거칠 수 있다. profile 프로젝트에서는 리뷰 없는 직접 저장을 막는다(`src/commands/query-publication.ts:44-50`, `:75`).

#### 10. 동시성·안전

입장: 단일 프로세스 lock, journal 기반 batch 원자성, 경로 confinement가 촘촘하다. git과는 엮지 않는다.

- [확인] compile·review·rm·query 저장 같은 wiki mutation은 `.llmwiki/lock`을 잡는다(`src/compiler/index.ts:125`, `src/commands/query-publication.ts:71`, `src/operation-bundles/lock-gate.ts`).
- [확인] ingest는 lock 없이 돈다. `ingestSource`가 `sources/`에 파일을 쓰고 `log.md`에 덧붙이는 동안 lock을 잡지 않는다(`src/commands/ingest.ts:288-310`, `src/utils/source-writer.ts:137`, `src/utils/activity-log.ts:123`). MCP `ingest_source`도 같은 함수를 부른다(`src/mcp/tools.ts:64`).
- [확인] `wiki/index.md`와 MOC는 planner·journal을 거치지 않고 `atomicWrite`로 바로 쓴다(`src/compiler/indexgen.ts:45`, `src/compiler/obsidian.ts:117`). 둘 다 다시 만들 수 있는 파생 파일이라 journal 밖에 둔 것으로 보인다.
- [확인] 페이지 batch는 pre-state journal로 all-or-nothing이다. 다만 코드 스스로 fsync가 없어 "NOT power-loss durable"이라고 적는다(`src/trust/journal.ts:4-9`).
- [확인] symlink 탈출과 경로 confinement 검사가 읽기·쓰기 양쪽에 있다(`src/utils/path-confine.ts`, `src/compiler/confined-wiki-read.ts`, `src/trust/checks.ts`).
- [확인] LLM에게 부수효과가 있는 도구를 주지 않는다. 본문 생성은 도구 0개다(`src/providers/claude-agent.ts:157-158`). 구조화 출력이 필요한 호출만 no-op 도구 하나를 받는다(`src/providers/claude-agent.ts:180-213`). Codex provider는 임시 디렉터리에서 `--sandbox read-only`로 돈다(`src/providers/codex-agent.ts:243-250`).
- [확인] `src/`에서 git을 호출하는 코드를 찾지 못했다(`grep "spawn(\"git"` 등 결과 없음). snapshot·undo는 git이 아니라 journal(크래시 복구)과 review reject로만 한다. 사용자가 과거 버전으로 되돌리는 명령은 찾지 못했다.

#### 11. Query·검색

입장: hybrid 검색이다. query는 chunk embedding + BM25 rerank를 먼저 쓰고, 단계마다 물러난다. context pack은 graph 확장을 더한다. 답은 선택적으로 wiki에 되저장한다.

- [확인] `selectRelevantPages`는 세 갈래로 물러난다(`src/commands/query-selection.ts:123-133`).
  - 1순위: chunk embedding 상위 30개를 BM25로 rerank해 12개를 남긴다. 그 chunk의 부모 페이지를 최대 5개 고른다(`:197-216`, `src/utils/constants.ts:50`, `:499-502`).
  - 2순위: chunk 결과가 없으면 page embedding 상위 15개를 뽑고 LLM이 그중에서 고른다(`:155`, `:177-190`, `src/utils/constants.ts:496`). 이 단계에는 BM25가 없다.
  - 3순위: embedding store가 없으면 LLM이 live 페이지 후보 목록(pageId·title·summary)에서 고른다. 이 목록은 렌더된 `index.md`가 아니다(`src/search/retrieval.ts:1-16`).
- [확인] `llmwiki context`/MCP `get_context_pack`은 LLM 없이 lexical+embedding+graph로 근거 묶음을 만든다(`src/context/build.ts:93`). `includeSources: true`이면 원문 줄도 함께 준다(`src/context/build.ts:85`, `:130`).
- [확인] `query --save`는 답을 `wiki/queries/`에 저장한다. 저장 전 lock 아래에서 링크를 다시 검증한다. 검증이 실패하면 저장을 거부한다(`src/commands/query-publication.ts:53-85`).
- [확인] 저장된 답 페이지의 freshness는 항상 `unverified`다(`src/freshness/index.ts:40-42`).

#### 12. index·log 관리

입장: 둘 다 결정적이다. LLM은 index·log를 쓰지 않는다.

- [확인] `wiki/index.md`는 compile 끝에 frontmatter를 읽어 다시 만든다(`src/compiler/indexgen.ts:1-31`). Obsidian MOC도 같은 방식이다(`src/compiler/obsidian.ts`).
- [확인] `log.md`는 append-only다. `## [ISO시각] operation | 설명` 형식이다(`src/utils/activity-log.ts:1-16`). ingest·compile·query만 남기고 lint는 남기지 않는다.
- [확인] index는 extraction prompt에 전문으로 들어간다(`src/compiler/extraction-phase.ts:143-144`). wiki가 커지면 source마다 내는 extraction 비용도 index 크기만큼 는다.

#### 13. 포맷 표준

입장: OKF producer이자 consumer다. import는 기본으로 리뷰를 거친다.

- [확인] `export --target okf`와 `import --okf`가 있다(`src/export/okf/`, `src/commands/import.ts`).
- [확인] 외부 메타데이터는 `x-okf`에 보존한다(`src/export/collect.ts:85-97`). 자체 provenance를 `x-llmwiki`에 둔다는 것은 README "Open Knowledge Format"의 설명이다. 코드 위치는 확인하지 않았다.
- [확인] JSON, JSON-LD, GraphML, Marp, `llms.txt`로도 내보낸다(`src/export/`).
- 확인하지 못한 것: `export --target okf`의 출력이 OKF 필드를 얼마나 빠짐없이 지키는지 모른다. `src/export/okf/`를 OKF 명세와 대조하지 않았다. 출력 필드를 명세 §11의 conformance 필수 조건 3개와 조건부 family 규칙에 하나씩 맞춰 보면 알 수 있다.

#### 14. 규모·비용

입장: 숫자로 밝힌 운영 규모는 없다. 비용을 줄이는 장치는 여럿 있다.

- [확인] README "Scale and what works"는 "still early software"라고 적는다. 페이지 수나 source 수 같은 운영 규모 숫자는 README·docs에서 찾지 못했다.
- [확인] 비용 구조: source 1개당 extraction 1회, concept 1개당 page 생성 1회다. 공유 concept이 있으면 영향받은 다른 source의 extraction도 다시 돈다. 다만 hash·소유·prompt 계약이 같으면 extraction snapshot을 재사용한다(`src/compiler/extraction-snapshot.ts`, `ARCHITECTURE.md` "Compile").
- [확인] 동시성 기본값은 5, 최대 50이다(`src/utils/constants.ts:53-56`).
- [확인] prompt는 공통 prefix(지시문 → 원문 → 페이지별 부분) 순서로 짜서 provider prefix cache를 노린다(`src/compiler/prompts.ts:244-249`).
- [확인] 컨텍스트 사용: page 생성 prompt에는 원문(≤200k자), 기존 페이지 전문, 관련 페이지 5개 전문, link target 목록이 들어간다. link target 목록은 8,000자에서 잘린다(`src/compiler/link-targets.ts:23`).
- [확인] "관련 페이지 5개"는 관련도로 고르지 않는다. `readdir` 결과의 앞 5개 파일이다(`src/compiler/page-renderer.ts:123-147`).
- [확인] link target 목록은 8,000자 상한이 있어 wiki 크기에 비례해 늘지 않는다(`src/compiler/link-targets.ts:14-23`). 대신 큰 wiki에서는 일부 페이지가 목록에서 빠진다.
- [추정] extraction prompt에 들어가는 `index.md`에는 상한이 없다. 그래서 wiki가 커질수록 source마다 내는 extraction 비용이 선형으로 는다. 근거는 `readConfinedExtractionIndex`가 index 전문을 자르지 않고 넘기는 구조 1건이다(`src/compiler/extraction-phase.ts:143`, `:166-172`). 실제 크기는 측정하지 않았다.
- [확인] `scripts/benchmark-review-batch.mjs`는 review batch 성능용이다. ingest 비용 벤치마크는 찾지 못했다.

#### 15. frosk1 비판 7가지 대응

| 비판 | 대응 | 근거 |
|---|---|---|
| 오류 누적 | 부분 대응이다. 원문 hash가 바뀌면 다시 생성하고, citation 범위를 lint한다. 하지만 일반 업데이트는 기존 페이지를 prompt에 넣고 다시 쓰므로 틀린 문장이 이어질 수 있다. source 삭제 때만 `rebuild`로 기존 페이지를 뺀다. | `src/compiler/page-renderer.ts:61`, `src/compiler/prompts.ts:264-266` |
| 부분 문맥 | 대응한다. concept을 공유하는 모든 source를 다시 읽어 합친다. 다만 200k자 예산을 넘으면 source별 앞부분만 남긴다. | `src/compiler/deps.ts:1-13`, `src/compiler/prompt-budget.ts:59-79` |
| 요약 손실 | 부분 대응이다. 원문은 `sources/`에 남는다. context pack이 원문 줄을 꺼내 줄 수 있다. 다만 ingest 단계에서 100k자를 넘는 부분은 원문 사본에서도 사라진다. | `src/commands/ingest.ts:143-160`, `src/context/build.ts:130` |
| 가짜 source of truth | 대응한다. 문단 단위 줄 범위 citation, freshness 계산, query 답 `unverified` 고정이 있다. "link 유효성 ≠ 사실 지지"를 문서에 명시한다. | `src/freshness/index.ts`, `ARCHITECTURE.md` "Publish" |
| 환각 병합 | 약하다. 병합 기준은 LLM이 붙인 concept 제목의 slug 일치다. 모순은 LLM이 스스로 표시할 때만 잡힌다. lint 중복 검사도 제목 문자열 일치만 본다. | `src/compiler/extraction-merge.ts:38-65`, `src/linter/rules.ts:189-218` |
| 운영 복잡도 | 오히려 커졌다. profile·workflow·artifact·template 서명·connector·preparation 계층이 compile 코어보다 크다. 기본 profile이 없으면 pre-1.0 동작을 유지해 진입 장벽은 낮췄다. | `src/` 디렉터리별 줄 수, README "CLP" |
| ingest 비용 | 대응한다. hash 증분, extraction snapshot 재사용, 병렬 cap, prefix cache 친화 prompt 순서, judge 결과 캐시가 있다. 비용 숫자는 밝히지 않았다. | `src/compiler/extraction-snapshot.ts`, `src/compiler/prompts.ts:244-249`, `src/eval/cache.ts` |

#### 16. 성숙도·차용 가능성

입장: 성숙도는 높다. 코드는 MIT라 차용할 수 있다. 다만 규모가 커서 통째로 가져오기는 어렵다.

- [확인] 테스트 파일(`.test.ts`)은 1,352개, 167,165줄이다. helper를 더한 `test/` 아래 `.ts` 전체는 186,712줄이다. 어느 쪽으로 세도 `src/`(170,980줄)와 비슷하거나 많다.
- [확인] CI workflow 4개가 있다(`.github/workflows/`). husky 훅은 둘이다. pre-commit은 fallow·tsc, pre-push는 build·test를 돈다(`.husky/`). 파일 400줄·함수 40줄 상한 규칙이 있다(`AGENTS.md`).
- [확인] 런타임 의존성은 21개다(`package.json` dependencies). Anthropic SDK, Claude Agent SDK, OpenAI SDK, MCP SDK, jsdom, pdf-parse, chokidar, zod, ajv 등이다. Node 24 이상이 필요하다.
- [확인] 라이선스는 MIT다(`LICENSE`, `gh api`). 코드 차용에 제약이 없다.
- [확인] 릴리스 이력은 0.1.0(2026-04-05)부터 1.4.2(2026-10-02)까지 21개 항목이다(`CHANGELOG.md`). 0.8.0은 2026-05-26이다.

## 장점

- **LLM에게 쓰기 권한이 없다.** 본문 생성은 도구 0개, 구조화 출력은 no-op 도구 하나로 부른다. 파일 쓰기, link, index, log는 전부 코드가 한다(`src/providers/claude-agent.ts:157-158`, `:180-213`, `src/compiler/resolver.ts:1-10`, `src/compiler/indexgen.ts`).
- **페이지 쓰기 경로가 하나다.** compile, review 승인, workflow의 페이지 쓰기가 모두 `planPageMutation` → `applyApprovedMutationsLocked`를 지난다. 끌 수 없는 floor check가 붙는다(`src/trust/planner.ts`, `src/trust/checks.ts:4-11`). 단 `index.md`·MOC·`log.md`·`sources/`는 이 경로 밖에서 쓴다.
- **크래시 일관성이 설계돼 있다.** pre-state journal, 단일 state flush, embedding pending 큐가 있다. 반쯤 쓰인 상태가 남지 않는다(`src/trust/journal.ts:1-27`, `src/compiler/index.ts:663-683`).
- **줄 번호를 보여 주고 줄 범위를 받는다.** LLM이 셀 필요 없이 번호를 읽게 했다. 결정적 normalizer가 흔한 실수(파일명 누락)를 고친다. 다만 파일명이 붙은 citation의 범위는 normalizer가 보지 않는다(`src/compiler/prompt-budget.ts:85-91`, `src/compiler/citation-normalize.ts:91-102`).
- **lint 결과의 성격을 표시한다.** 결정적 사실과 "모델이 매긴 의견"을 tier로 나눠 보여 준다(`src/linter/index.ts:38-62`).
- **공유 concept의 소유 관계를 추적한다.** source↔concept 역색인으로 한 source 변경이 공유 페이지를 한쪽 내용으로 덮지 않게 한다(`src/compiler/deps.ts`).
- **정직한 한계 표기.** prompt 규칙은 "advisory", journal은 "not power-loss durable", budget 절단은 "defensive"라고 코드에 적어 둔다(`src/compiler/prompts.ts:61-64`, `src/trust/journal.ts:4-9`, `src/compiler/prompt-budget.ts:11-13`).

## 단점

- **기본 compile 경로에는 내용 gate가 없다.** profile gate(field·lifecycle·relation·artifact)는 profile entity 페이지용이다. LLM이 만드는 concept 페이지는 경로·크기(500k자)·frontmatter 파싱 검사만 받는다. 덮어쓰기 충돌 검사도 `allowOverwrite: true`로 꺼진다(`src/compiler/compile-write.ts:98-105`). README "Quality and safety model"은 gate가 걸리는 표면을 나열하므로 README와 코드가 어긋나지는 않는다.
- **기본값이 자율 쓰기다.** review policy가 없으면 citation이 깨진 페이지도 live로 쓰인다. compile은 후보 본문에 citation·schema lint를 돌리지만, policy가 꺼져 있으면 그 결과를 버린다. 사람이 나중에 lint로 발견해야 한다(`src/review/config.ts:17-20`, `src/compiler/review-pipeline.ts:69-98`). MCP `compile_wiki`에는 review 인자도 없다(`src/mcp/tools.ts:80`).
- **lint의 citation 검사는 줄 번호가 파일 안에 있는지만 본다.** 엉뚱한 줄을 인용해도 통과한다. 내용 검증은 `eval --suite full`의 LLM 표본뿐이다(`src/linter/rules-citations.ts:126-137`).
- **병합 기준이 제목 slug다.** "LLM Wiki"와 "LLM-based Wiki"는 다른 페이지가 된다. 반대로 같은 이름의 다른 개념은 합쳐진다. 중복 lint도 제목 문자열만 본다(`src/compiler/extraction-merge.ts:38-65`, `src/linter/rules.ts:189-218`). 중복을 막는 장치는 extraction prompt에 index를 주고 "avoid duplicating"을 지시하는 것뿐이다(`src/compiler/prompts.ts:165-167`). 제목에서 별칭(slug, 어순 바꿈, 약어)을 만들기는 하지만 Obsidian frontmatter용이고 병합·중복 검사에 쓰지 않는다(`src/compiler/obsidian.ts:36-66`).
- **업데이트가 전체 재작성이다.** 기존 페이지를 prompt에 넣고 LLM이 처음부터 다시 쓴다. 사람이 손으로 고친 문장도 다음 compile에서 사라질 수 있다(`src/compiler/page-renderer.ts:53-65`).
- **큰 원문을 조용히 자른다.** ingest에서 100k자로 자르고 compile에서 200k자 균등 절단한다. 경고와 `truncated` frontmatter는 남지만 뒷부분은 wiki에도 원문 사본에도 없다(`src/commands/ingest.ts:143-160`, `src/compiler/prompt-budget.ts:59-79`).
- **"관련 페이지" 문맥이 무관할 수 있다.** 디렉터리 앞 5개 파일을 넣는다(`src/compiler/page-renderer.ts:123-147`).
- **코어보다 주변이 크다.** preparations·capability-providers·operation-bundles가 compile 코어의 몇 배다. llm-wiki 패턴만 원하는 사용자에게는 과하다.

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

- **줄 번호를 붙인 원문 → `^[file:N-M]` → 결정적 범위 검사** 3단 구조다. 붙이는 쪽과 검사하는 쪽이 같은 번호 체계를 쓴다(`src/compiler/prompt-budget.ts:85-91`, `src/linter/rules-citations.ts`).
- **citation normalizer.** LLM 출력에서 흔한 실수를 쓰기 전에 결정적으로 고치거나 지운다(`src/compiler/citation-normalize.ts`).
- **추론 문단은 citation을 비워 두게 하는 규칙.** "uncited = inferred"로 세면 추론 비율을 lint로 볼 수 있다(`src/compiler/prompts.ts:212-214`).
- **lint tier 표시.** deterministic / provider-judgement / derived-view를 나눠 보여 준다(`src/linter/index.ts:46-73`).
- **source↔concept 소유 역색인과 공유 concept 전파.** `state.json` 한 파일로 된다(`src/compiler/deps.ts`).
- **prompt-modifier digest를 hash 비교에 넣기.** 출력 언어나 지침이 바뀌면 같은 원문도 다시 만든다(`src/compiler/index.ts:417-421`).
- **pre-state journal + 단일 state flush.** 작은 규모로도 흉내 낼 수 있다(`src/trust/journal.ts`).
- **LLM 호출에 도구 0개.** wiki 파일 쓰기를 코드가 독점하게 한다.
- **trust 승인 권한을 workspace 밖(env)에 두기.** agent가 설정 파일을 고쳐 스스로 권한을 얻지 못하게 한다(`src/trust/trusted-write.ts`).

### 피할 것

- **제목 slug만으로 병합하기.** 병합에 쓰는 별칭 목록이나 사람 확인 단계 없이 쓰면 중복과 오병합이 함께 생긴다. 별칭을 만들었다면 병합 키로도 쓴다.
- **기존 페이지 전체 재작성.** 문단 단위 patch나 사람 편집 보존 표시가 없으면 수동 수정이 사라진다.
- **기본 생성 경로에 내용 gate 없이 live 쓰기.** compile이 이미 계산한 citation lint 결과를 policy가 꺼져 있다고 버리지 않는다. 최소한 경고로 남긴다.
- **원문 사본까지 자르기.** 자르더라도 원본은 보존하고, 자른 부분은 별도 chunk로 처리한다.
- **profile·workflow·template 서명 같은 플랫폼 계층.** 개인 wiki에는 필요 없다.

## 확인하지 못한 것

- 실제 실행은 하지 않았다. citation 정확도, 생성 품질, 비용은 측정하지 않았다. `examples/basic/wiki/`의 예시 페이지는 2026-04 생성본이다. 그 안에는 문단 citation이 없고 `## Sources`만 있다.
- `human:` gate의 TTY 확인을 pty를 다루는 agent가 통과할 수 있는지 실행해 보지 않았다(경로 자체는 #9에서 확인).
- OKF 명세 준수 범위. `src/export/okf/`를 OKF 명세와 대조하지 않았다.
- `src/preparations/`, `src/capability-providers/`, `src/operation-bundles/`(합계 약 56k줄)는 거의 읽지 않았다. product action과 provider 실행 계층으로 보인다. llm-wiki 핵심 흐름과의 관계는 ARCHITECTURE.md 설명에만 기대고 있다.
- 테스트가 실제로 통과하는지 실행하지 않았다. CI 배지 상태도 확인하지 않았다.

## 검증 기록

코드를 다시 열어 보고 고친 것이다. 한 줄에 하나씩 적는다.

- 한눈에: 테스트 186,712줄은 `.test.ts`가 아니라 `test/` 아래 `.ts` 전체였다. `.test.ts`는 167,165줄로 고쳤다.
- 한 바퀴 흐름·#5·장점: normalizer는 파일명 없는 번호만 범위를 본다. "범위를 넘는 줄 번호는 버린다"를 그 범위로 좁혔다.
- 한 바퀴 흐름·#11: query 선택 순서가 틀렸다. BM25는 chunk 단계에만 있고, page embedding 단계는 LLM이 고른다. 세 갈래로 다시 적었다.
- #1·#10·장점·가져올 것: "도구 0개"는 본문 생성에만 맞다. 추출과 judge는 no-op 구조화 도구 하나를 받는다. "부수효과 있는 도구 0개"로 고쳤다.
- #1: SKILL.md가 규칙을 안 담는다는 말을 고쳤다. mutation 주의와 MCP review 인자 부재를 적는다.
- #1·단점: MCP `compile_wiki`에 review 인자가 없다는 점을 추가했다.
- #2: husky pre-commit은 fallow·tsc만 돈다. build·test는 pre-push다.
- #2·단점: compile은 `allowOverwrite: true`라 충돌 check가 사실상 빠지고, 크기 상한이 500k자라는 점을 추가했다.
- #2·단점·피할 것: "README 약속과 코드가 다르다"를 철회했다. README는 gate 표면을 나열하고, profile gate는 concept 페이지에 해당 필드가 없다. 피할 것 항목을 "내용 gate 없는 live 쓰기"로 바꿨다.
- #4: rule-extractor는 compile과 분리된 `rules` 명령이라는 것을 확인해 추가했다. 확인하지 못한 것에서 뺐다.
- #5: lint는 인용 파일이 페이지 `sources`에 속하는지 보지 않는다는 점을 추가했다.
- #8: source 파일만 지우면 페이지를 지우지 않고 `orphaned: true`를 붙인다는 점을 추가했다.
- #9: human gate는 CLI 대화형 TTY 확인으로만 통과한다는 것을 확인해 추가했다. 확인하지 못한 것은 TTY 우회 여부로 좁혔다.
- #10: "모든 mutation이 lock을 잡는다"를 고쳤다. ingest는 lock 없이 `sources/`와 `log.md`를 쓴다.
- #10·장점: `index.md`·MOC는 journal 밖에서 `atomicWrite`로 쓴다는 점을 추가했다. "쓰기 경로가 하나다"를 페이지 쓰기로 좁혔다.
- #11: `query --save`는 citation 검증이 실패하면 저장을 거부한다는 점을 추가했다.
- #13: `x-llmwiki`의 근거가 `collect.ts`가 아니라 README였다. 출처를 고쳤다.
- #14: link target 목록에는 8,000자 상한이 있다. 선형 증가 [추정]을 index에만 남겼다.
- #16: 릴리스 이력 시작은 0.8.0이 아니라 0.1.0(2026-04-05)이다.
- 단점: compile이 계산한 lint 결과를 policy off일 때 버린다는 점을 추가했다.
- 단점·피할 것: 별칭은 만들지만 병합에 쓰지 않는다는 점과, 중복 방지가 index를 보여 주는 prompt 지시뿐이라는 점을 추가했다.
- 비교 검토 단계: #13의 사례 없는 [추정](OKF 필드 준수 정도)을 모르는 것과 그것을 알 방법을 적는 "확인하지 못한 것" 형식으로 바꿨다.

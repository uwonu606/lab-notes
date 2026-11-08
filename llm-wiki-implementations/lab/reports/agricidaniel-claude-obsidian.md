# AgriciDaniel/claude-obsidian — LLM은 초안만 만들고, vault 쓰기는 모두 hash로 묶인 transaction 하나를 거친다

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/AgriciDaniel/claude-obsidian |
| clone commit | `32ac5a0` (v2.2.0 release merge, 2026-09-10). shallow clone이라 로컬 history는 이 커밋 하나뿐이다. |
| 별 · 최근 push · 라이선스 | 15,445★ · 2026-09-10 · MIT (`gh api repos/AgriciDaniel/claude-obsidian`) |
| 기여자 · 커밋 | 기여자 10명, 커밋 약 282개 (`gh api .../contributors`, `.../commits` 페이지 수) |
| 형태 | Claude Code plugin(skill 15개, subagent 3개, hook 2개)과 표준 라이브러리 전용 Python 패키지 `claude_obsidian/`를 함께 쓴다. |
| 코드 규모 | `claude_obsidian/*.py` 19,458줄, `scripts/*.py` 4,153줄, `scripts/*.sh` 1,322줄, `tests/` 37개 파일 19,308줄(Python 테스트 함수 534개), skill·agent 문서 3,358줄 |
| 버전 흐름 | v1.x(2026-04~05)는 prompt 중심이었다. v2.0.0(2026-07-30)이 "Reliability and evidence refoundation"으로 transaction·ledger·결정적 lint를 들였다 (`CHANGELOG.md:223-330`). |

참고: 이 보고서에서 "vault"는 사용자의 Obsidian 폴더(노트 저장소)를 뜻한다. "product"는 이 repo 자체(코드·skill)를 뜻한다. 둘은 코드에서 엄격히 분리된다.

## 한 바퀴 흐름

### Ingest

1. 사용자가 원본을 `inbox/`에 둔다. vault 밖 파일은 durable provenance가 아니라서 먼저 capture를 거치라고 skill이 지시한다 (`skills/wiki-ingest/SKILL.md:48-54`).
2. `capture plan` / `capture apply`가 원본 bytes를 SHA-256 content-addressed 경로 `.raw/captured/`에 create-only로 복사한다 (`claude_obsidian/capture.py:909-1044`, `claude_obsidian/transaction.py:3266-3277`).
3. orchestrator LLM이 `wiki/hot.md`, `wiki/index.md`, 관련 페이지 최대 5개를 읽는다 (`skills/wiki-ingest/SKILL.md:80-82`).
4. 필요하면 `agents/wiki-ingest.md` subagent를 원본 하나당 하나씩 띄운다. subagent는 `Read, Grep, Glob, Bash`만 쓰고 YAML draft packet을 돌려준다 (`agents/wiki-ingest.md:10`, `agents/wiki-ingest.md:72-109`).
5. orchestrator가 draft를 합쳐 `claude-obsidian.transaction.v1` JSON bundle 하나를 만든다. bundle에는 페이지 쓰기, 두 ledger 쓰기, `address_requests`, `source_manifest_updates`, index·log·hot 갱신이 함께 들어간다 (`skills/wiki-ingest/SKILL.md:111-129`).
6. `python3 scripts/claude-obsidian.py transaction inspect BUNDLE --vault V`가 `inspect_bundle()`을 부른다. 이 함수는 경로·범위·provenance를 검증하고 `approval_sha256`을 낸다 (`claude_obsidian/transaction.py:4390-4462`).
7. `transaction apply ... --approved-plan-sha256 H`가 `apply_bundle()`을 부른다. 이 함수는 lock 전에 inspect를 다시 돌려 hash를 비교한다. 그다음 vault 전체 `MutationLock`을 잡고 미완료 transaction을 복구한다. 이어서 journal을 쓰고 파일마다 expected hash를 재확인한 뒤 atomic replace한다 (`claude_obsidian/transaction.py:4465-4803`).
8. 사용자가 원하면 `checkpoint OPERATION_ID`가 그 operation의 경로만 git commit한다. 이때 결정적 lint가 commit gate로 돈다 (`claude_obsidian/checkpoint.py:41-49`, `claude_obsidian/checkpoint.py:1340-1346`).

### Query

1. `skills/wiki-query/SKILL.md`가 `wiki/hot.md`를 orientation으로만 읽는다 (`skills/wiki-query/SKILL.md:8-9`).
2. `contracts --verify --capability wiki-retrieve`로 검색 index가 검증됐는지 본다 (`skills/wiki-query/SKILL.md:46-50`).
3. 검증됐으면 `scripts/retrieve.py`가 BM25 top-K를 뽑는다. query skill은 이 명령을 `--no-rerank`로 부른다. 그래서 query 경로에서는 BM25 순서만 쓴다 (`skills/wiki-query/SKILL.md:56`). Ollama cosine rerank는 `retrieve.py`가 따로 지원하는 기능이다 (`scripts/retrieve.py:1-20`, `scripts/retrieve.py:233`).
4. 검증이 안 됐으면 `wiki/index.md`와 text search로 fallback한다 (`skills/wiki-query/SKILL.md:62-64`).
5. claim ledger의 assessment 값에 따라 답의 확신 정도를 나눠 적는다 (`skills/wiki-query/SKILL.md:71-85`).
6. Query는 아무것도 쓰지 않는다. 답을 남기려면 `save` skill이 별도 transaction을 만든다 (`skills/wiki-query/SKILL.md:97-100`).

### Lint

1. `python3 scripts/claude-obsidian.py lint --vault V`가 `lint_vault()`를 부른다 (`claude_obsidian/lint_engine.py:954`).
2. `lint_vault()`는 wikilink·Markdown link를 직접 파싱해 dead link, ambiguous target, 중복 basename, orphan, frontmatter 누락, 빈 section, stale index entry를 센다 (`claude_obsidian/lint_engine.py:1044-1184`).
3. 같은 함수가 `_provenance_errors()`로 두 ledger를 검증한다 (`claude_obsidian/lint_engine.py:889-923`).
4. `agents/wiki-lint.md` subagent는 이 JSON을 해석만 한다. 수정은 하지 않는다 (`agents/wiki-lint.md:52-55`).
5. 수정은 사용자가 고른 항목만 `lint-fix` 타입 transaction으로 따로 적용한다 (`skills/wiki-lint/SKILL.md:66-80`).

## 축별 분석

#### 1. 실행 형태

입장: skill과 결정적 엔진의 결합이다. 판단은 LLM이 하고, 쓰기·검증·검색은 Python CLI가 한다.

- [확인] skill 15개와 subagent 3개가 prompt 층이다 (`skills/*/SKILL.md`, `agents/*.md`).
- [확인] 모든 vault 변경은 `scripts/claude-obsidian.py` CLI를 거치라고 skill이 지시한다 (`skills/wiki/references/operation-transactions.md:13-18`).
- [확인] 엔진은 표준 라이브러리만 import한다. 외부 패키지 의존이 없다 (`claude_obsidian/package_validation.py:3-7`, import 목록 grep 결과).
- [확인] Codex, OpenCode, Gemini, ZCode, Cursor, Windsurf용 연결도 있다 (`scripts/setup-multi-agent.sh`, `.cursor/rules/claude-obsidian.mdc`, `.windsurf/rules/claude-obsidian.md`).
- MCP 서버나 데스크톱 앱은 없다.

#### 2. 규칙의 위치

입장: "어디에 무엇을 쓸 수 있는가"와 "ledger가 일관된가"는 코드가 강제한다. "언제 무엇을 같이 써야 하는가"와 "Write/Edit을 쓰지 마라"는 prompt에만 있다.

코드가 강제하는 것:
- [확인] operation type마다 쓸 수 있는 경로가 정해져 있다. 예를 들어 `save`는 `wiki/`만, `capture`는 `.raw/captured/*` create만 쓴다 (`claude_obsidian/transaction.py:3172-3277`).
- [확인] lock·journal·검색 cache 경로는 어떤 bundle도 쓸 수 없다 (`claude_obsidian/transaction.py:63-90`).
- [확인] 모든 write에는 `expected_hashes` 항목이 있어야 한다 (`claude_obsidian/transaction.py:3429`).
- [확인] `.md` 파일은 UTF-8이고 frontmatter가 닫혀 있어야 한다 (`claude_obsidian/transaction.py:3130-3142`).
- [확인] ledger가 bundle에 들어 있으면 inspect·apply 단계에서 ledger 규칙 전체를 검증한다 (`claude_obsidian/transaction.py:3550`, `claude_obsidian/transaction.py:3623-3740`).
- [확인] 반대로 bundle에 ledger 쓰기가 없으면 이 검증은 통째로 건너뛴다 (`claude_obsidian/transaction.py:3641-3642`). 코드는 `ingest` bundle에 ledger나 claim이 들어 있기를 요구하지 않는다. 그래서 claim 기록 없이 페이지만 쓰는 ingest도 inspect를 통과한다.
- [확인] 승인 hash 요구는 CLI 층에만 있다. 라이브러리 함수 `apply_bundle()`은 `approved_plan_sha256=None`이면 hash 비교를 건너뛰고 적용한다 (`claude_obsidian/transaction.py:4466-4475`, `claude_obsidian/transaction.py:4521-4531`, `claude_obsidian/transaction.py:4672`). 테스트도 hash 없이 부른다 (`tests/test_transaction.py:71`). `capture_filesystem_batch()`는 승인 없이 `apply_bundle()`을 부른다 (`claude_obsidian/capture.py:1008-1018`). 다만 이 함수를 부르는 product 코드는 없고 테스트만 쓴다.

prompt에만 있는 것:
- [확인] "host Write/Edit을 쓰지 마라"는 skill 문장뿐이다 (`skills/wiki-ingest/SKILL.md:127-129`, `skills/save/SKILL.md:86-87`). hook은 `SessionStart`와 `Stop` 두 개뿐이고 `PreToolUse` 차단이 없다 (`hooks/hooks.json`).
- [확인] "ingest는 index·log·hot을 같은 bundle에서 갱신한다"는 문서 규칙이다 (`skills/wiki/references/operation-transactions.md:103-113`). 코드가 이 묶음을 강제하는 경우는 `fold` 하나뿐이다 (`claude_obsidian/transaction.py:3279-3297`).
- [추정] LLM이 skill을 무시하고 Write로 `wiki/`를 직접 고치면 transaction 장치 전체가 우회된다 — 사례: 위의 hook 목록 1개와 write 차단 코드 부재. 다음 transaction의 expected hash 검사는 이 흔적을 잡지 못한다. expected hash는 agent가 초안을 짤 때 현재 파일에서 읽어 넣는 값이라, 직접 고친 뒤의 상태가 그대로 기준이 된다 (`skills/wiki/references/operation-transactions.md:27-28`). lint는 claim anchor가 깨졌거나 file source의 bytes가 바뀐 경우만 잡는다.
- [확인] Bash가 열린 agent는 Python에서 `apply_bundle()`을 직접 불러 승인 hash 단계도 건너뛸 수 있다. 막는 것은 skill 문장뿐이다 (위 라이브러리 항목).

#### 3. 저장 구조

입장: Markdown 페이지와 JSON ledger를 분리한다. 근거 기록은 페이지 frontmatter가 아니라 ledger가 원본이다.

- [확인] vault 루트는 `inbox/`, `.raw/`, `wiki/`, `.obsidian/`, `.vault-meta/`로 나뉜다 (`WIKI.md:9-31`).
- [확인] `wiki/` 아래는 `sources/`, `entities/`, `concepts/`, `questions/`, `canvases/`, `meta/ledgers/`다 (`WIKI.md:16-28`). `folds/`는 WIKI.md 트리에 없고 transaction 엔진의 fold 범위 검사에만 나온다 (`claude_obsidian/transaction.py:3243-3253`).
- [확인] 페이지 `type`은 `source, entity, concept, question, comparison, session, overview, meta, fold` 9개이고 한 모듈에 선언돼 있다 (`claude_obsidian/page_schema.py:36-46`).
- [확인] 그러나 lint와 transaction 엔진은 이 목록으로 `type` 값을 검사하지 않는다. lint는 `type` 필드가 있는지만 본다. 모듈 docstring도 이를 인정한다 (`claude_obsidian/page_schema.py:7-8`, `claude_obsidian/lint_engine.py:1159-1163`). 이 목록을 쓰는 곳은 `wiki-mode` 라우터와 그 테스트뿐이다 (`grep page_schema` 결과).
- [확인] lint가 요구하는 frontmatter는 `title, type, status, created, updated, tags`다 (`claude_obsidian/lint_engine.py:63`). `address`(`c-000001` 형식)는 transaction 엔진이 counter로 붙인다 (`claude_obsidian/transaction.py:3062-3090`).
- [확인] 파생·상태 파일은 셋으로 나뉜다. `.raw/.manifest.json`은 ingest 해시와 address map이다. `wiki/meta/ledgers/source-ledger.json`은 출처 신원·권위·신선도다. `wiki/meta/ledgers/claim-ledger.json`은 claim 판정이다 (`skills/wiki/references/provenance.md:14-23`).
- [확인] `.vault-meta/`에는 transaction journal, mutation lock, BM25 index, chunk, capture queue가 있다 (`claude_obsidian/transaction.py:63-90`).
- [확인] 문서와 코드가 어긋난 곳이 있다. `frontmatter.md`는 `claim_ids: - claim-example`을 예로 드는데 ledger는 `clm-` 접두사만 받는다 (`skills/wiki/references/frontmatter.md:22-23`, `claude_obsidian/ledgers.py:944-945`). 페이지 frontmatter의 `claim_ids`는 어떤 코드도 읽지 않는다 (`grep claim_ids claude_obsidian/` 결과 없음). 그래서 페이지와 ledger의 claim 연결은 ledger의 `location.path` 한 방향뿐이다. `risk: low` 예시도 ledger의 `{normal, high}`와 다르다 (`skills/wiki/references/frontmatter.md:77-78`, `claude_obsidian/ledgers.py:40`).

#### 4. Ingest

입장: 사람이 범위와 예산을 정하고, LLM이 batch 하나를 transaction 하나로 묶는다. 자동 감시는 없다.

- 사람 참여: [확인] skill이 원본 수·바이트·읽을 페이지 수·네트워크 요청 수 예산을 먼저 합의하라고 한다 (`skills/wiki-ingest/SKILL.md:27-32`). apply 전에 변경 경로와 claim 판정을 보여 주라고 한다 (`skills/wiki-ingest/SKILL.md:140-142`).
- 증분: [확인] capture 단계는 같은 digest가 이미 있으면 다시 복사하지 않는다 (`claude_obsidian/capture.py:893-907`). [확인] ingest 단계의 "이미 처리한 원본인가" 판단은 LLM이 manifest와 hash를 비교하라는 지시뿐이다 (`skills/wiki-ingest/SKILL.md:68-69`). 이를 계산하는 코드는 찾지 못했다.
- crash 복구: [확인] apply 중단은 journal로 rollback되고, 다음 apply나 `transaction recover`가 복구한다 (`claude_obsidian/transaction.py:4054-4118`, `claude_obsidian/transaction.py:4613`). [확인] `Stop` hook이 미완료 journal을 세서 recover를 권한다 (`claude_obsidian/hook_adapter.py:218-320`).
- queue: [확인] capture queue는 `queued, claimed, completed, failed` 상태를 가진다 (`claude_obsidian/capture.py:76`). 이 queue는 URL·OCR 같은 외부 runner 작업용이다.
- 자동 감시: 없다. [확인] `inbox/` watcher 코드가 없다.
- 멀티포맷: [확인] 텍스트 계열만 내용을 읽는다. PDF·EPUB·이미지는 metadata와 hash만 남긴다. URL·YouTube·OCR은 외부 runner가 필요한 계획 객체만 만든다 (`config/adapters.json` `maturity` 필드, `README.md` "Honest capability boundaries" 표).
- 소스 하나가 건드리는 페이지 수: [확인] 기존 페이지 읽기 기본값은 5개다 (`skills/wiki-ingest/SKILL.md:80-82`). [확인] "compilation-value gate"가 있어서 지속 가치가 없으면 source 기록만 남기거나 no-op으로 끝내라고 한다 (`skills/wiki-ingest/SKILL.md:75-79`). 생성 페이지 수의 상한은 코드에 없다. bundle당 write 1,024개가 엔진 한계다 (`claude_obsidian/transaction.py:140`).

#### 5. 근거 추적 단위

입장: claim ledger다. 다만 원문 글자 일치나 줄 범위 검증은 하지 않는다.

- [확인] claim 기록은 `text, risk, assessment, confidence, location{path, anchor}, reviewed_at, notes, supersedes, evidence[]`를 가진다 (`claude_obsidian/ledgers.py:901-1060`).
- [확인] `location.anchor`는 해당 wiki 페이지에 그 heading이나 `^block`이 실제로 있는지 검사한다 (`claude_obsidian/ledgers.py:964-1030`). 즉 claim → wiki 페이지 쪽 연결은 결정적으로 확인된다.
- [확인] 다만 `anchor`는 null이어도 된다. null이면 페이지가 있는지만 본다 (`claude_obsidian/ledgers.py:982-985`, `claude_obsidian/ledgers.py:1002-1008`). claim `text`가 그 페이지 본문에 실제로 있는지도 대조하지 않는다.
- [확인] `evidence[].locator`는 "text or null"인지만 본다 (`claude_obsidian/ledgers.py:1089-1093`). 원문 페이지·줄·인용문과 대조하지 않는다.
- [확인] worker packet에는 `excerpt` 필드가 있다 (`agents/wiki-ingest.md:92`). ledger 검증 코드는 excerpt를 다루지 않는다 (`grep excerpt claude_obsidian/` 결과 없음).
- [확인] source 기록의 `content_sha256`은 실제 파일 bytes와 대조된다. 원본이 바뀌면 lint가 잡는다 (`claude_obsidian/ledgers.py:666-700`). 이 대조는 `origin.kind == "file"`일 때만 돈다. URL source의 hash는 대조할 bytes가 없어 형식만 본다 (`claude_obsidian/ledgers.py:666`).
- [확인] source의 `authority`, `independence_key`, `refresh_due`와 claim의 `risk`는 enum·형식 검사만 받는다. 값은 LLM이 정한다 (`claude_obsidian/ledgers.py:574-582`, `claude_obsidian/ledgers.py:635-637`, `claude_obsidian/ledgers.py:737-744`, `claude_obsidian/ledgers.py:955-957`).
- [확인] source ID는 `kind + 정규화 locator + sha256`의 hash로 결정적이다 (`claude_obsidian/ledgers.py:407-415`).
- [추정] 결과적으로 "이 claim은 이 원본 파일에서 왔다"는 bytes 단위로 확인된다. "이 원본의 어느 문장인가"는 LLM 자기 신고다 — 사례: locator·excerpt 검증 코드 부재 2곳.

#### 6. Link

입장: link는 LLM이 본문에 쓴다. 해석과 검증은 결정적 parser가 한다. backlink 관리는 Obsidian에 맡긴다.

- [확인] wikilink는 LLM이 페이지 본문에 쓴다. "그래프 대칭을 맞추려고 backlink를 지어내지 말라"는 규칙이 있다 (`WIKI.md:107-108`).
- [확인] lint parser는 wikilink, embed, Markdown link, alias, heading·block fragment, code fence를 구분한다 (`claude_obsidian/lint_engine.py:470-528`, `skills/wiki-lint/SKILL.md:41-46`).
- [확인] `.gitignore`된 후보는 ambiguous 해석에서 뺀다 (`claude_obsidian/lint_engine.py:1056-1062`).
- [확인] backlink 파일이나 그래프 저장소는 없다. lint가 매번 incoming map을 계산해 orphan을 낸다 (`claude_obsidian/lint_engine.py:1044`, `claude_obsidian/lint_engine.py:1151-1155`).
- [확인] `scripts/boundary-score.py`가 link 그래프로 (out-degree − in-degree) × 최근성 가중치 점수를 내서 autoresearch의 탐색 지점을 고른다. DragonScale 설정이 있을 때만 쓰인다 (`scripts/boundary-score.py:1-30`).

#### 7. Lint

입장: lint는 전부 결정적이고 읽기 전용이다. LLM은 해석만 한다. 자동 수정은 없다. commit gate는 checkpoint에만 있다.

- [확인] 검사 항목은 dead link, ambiguous target, duplicate basename, orphan, missing frontmatter, empty section, stale index entry, read error, configuration error, provenance error 10개다 (`claude_obsidian/lint_engine.py:1186-1197`).
- [확인] `--as-of` 날짜를 고정하면 결과가 결정적이다 (`claude_obsidian/lint_engine.py:985-998`).
- [확인] 의미 수준 모순 검사는 하지 않는다고 skill이 명시한다 (`skills/wiki-lint/SKILL.md:47-52`).
- [확인] 중복 페이지 후보는 별도 `scripts/tiling-check.py`가 로컬 Ollama embedding으로 낸다. 이것도 읽기 전용이다 (`scripts/tiling-check.py:1-20`).
- [확인] 자동 수정은 없다. 고칠 항목을 사용자가 고르면 `lint-fix` transaction으로 따로 간다 (`skills/wiki-lint/SKILL.md:66-80`).
- [확인] `checkpoint`는 dead link, ambiguous target, missing frontmatter, stale index, read·config error, provenance error가 있으면 commit을 막는다. orphan, duplicate basename, empty section은 막지 않는다 (`claude_obsidian/checkpoint.py:41-49`, `claude_obsidian/checkpoint.py:1338-1356`).
- [확인] 이 gate는 `checkpoint --skip-lint`로 끌 수 있다 (`claude_obsidian/cli.py:1235`, `claude_obsidian/cli.py:913`, `claude_obsidian/checkpoint.py:1196`). lint는 그 operation의 경로가 아니라 vault 전체를 돈다. 그래서 이전부터 있던 문제도 이번 commit을 막는다.

#### 8. stale·모순 처리

입장: 덮어쓰지 않고 상태 값으로 남긴다. 시간 경과에 따른 stale은 결정적으로 감지한다. 모순 판정은 LLM의 라벨에 달려 있다.

- [확인] source는 `refresh_due`를 가져야 active가 된다. 그 날짜가 지나면 stale로 계산된다. 별도 stale 플래그는 저장하지 않는다 (`claude_obsidian/ledgers.py:641-652`, `claude_obsidian/ledgers.py:752-758`, `skills/wiki/references/provenance.md:32`).
- [확인] stale source만 붙은 `accepted` claim은 lint에서 "accepted claims require fresh active support" 오류가 된다 (`claude_obsidian/ledgers.py:1094-1125`).
- [확인] `contradicts` 관계의 신선한 source가 있는데 `accepted`로 두려면 `notes`에 판정 근거가 있어야 한다. 아니면 `contested`로 바꿔야 한다 (`claude_obsidian/ledgers.py:1137-1150`).
- [확인] source 상태 `superseded`와 claim 필드 `supersedes`가 있다 (`claude_obsidian/ledgers.py:39`, `claude_obsidian/ledgers.py:1052`).
- [확인] `.raw/` 원본은 create-only다. 원격 원본이 바뀌면 새 capture를 만든다 (`skills/wiki-ingest/SKILL.md:62-64`).
- [추정] 어떤 source가 claim을 "supports"하는지 "contradicts"하는지는 LLM이 정한다. 코드는 그 라벨이 맞는지 보지 않는다 — 사례: `relation` 검증이 enum 검사뿐이다 (`claude_obsidian/ledgers.py:1073-1075`).
- [추정] stale 기준일과 2-source 규칙도 LLM이 고른 값에 달려 있다 — 사례 2개: `refresh_due`를 먼 미래로 두면 stale이 되지 않는다. claim `risk`를 `normal`로 두면 독립 source 2개 규칙이 걸리지 않는다 (`claude_obsidian/ledgers.py:1127-1135`). 둘 다 형식 검사만 받는다.

#### 9. 사람 개입

입장: plan 승인 모델이다. 그러나 승인 hash는 사람이 아니어도 얻을 수 있다.

- [확인] CLI `transaction apply`는 `--approved-plan-sha256` 없이는 거부한다 (`claude_obsidian/cli.py:168-182`).
- [확인] 그 hash는 vault 경로, vault 디렉터리 inode 정체성, 확장된 bundle, 파일별 내용 hash와 mode를 한꺼번에 묶는다 (`claude_obsidian/transaction.py:1287-1309`).
- [확인] 그래서 승인 뒤 bundle·vault·파일 mode가 하나라도 바뀌면 `PLAN_CHANGED`로 거부된다 (`claude_obsidian/transaction.py:4526-4532`, `claude_obsidian/transaction.py:4665-4680`).
- [확인] 하지만 hash는 같은 agent가 `inspect`를 돌려 얻는다. 사람 확인을 코드로 요구하는 장치는 없다 (`skills/wiki-ingest/SKILL.md:133-138`). capture·mode 같은 CLI는 dry-run 출력에 hash와 "같은 명령을 `--approved-plan-sha256 HASH --apply`로 다시 돌려라"는 안내를 함께 넣는다 (`claude_obsidian/cli.py:72-83`).
- [확인] 이 hash 요구조차 CLI 층의 검사다. `apply_bundle()`을 Python에서 직접 부르면 hash 없이 적용된다 (§2).
- [추정] 이 two-step은 "사람 승인"이라기보다 "검토한 계획과 적용하는 계획이 같다"는 보장이다 — 사례: inspect와 apply가 같은 셸 세션에서 연달아 실행되는 skill 예시 3곳 (`wiki-ingest`, `save`, `operation-transactions`).
- [확인] 파괴적 변경, 외부 요청, canonical merge 제안은 적용 전에 사용자에게 보여 주라고 skill이 요구한다 (`skills/wiki/references/operation-transactions.md:33-34`). canonical 페이지 replace는 ingest skill이 따로 명시적 검토를 요구한다 (`skills/wiki-ingest/SKILL.md:141-142`).
- [확인] `save`는 사용자가 명시적으로 고른 내용만 저장한다 (`skills/save/SKILL.md:8-11`).
- 공동 편집이나 리뷰 큐는 없다.

#### 10. 동시성·안전

입장: 이 갈래에서 가장 두꺼운 층이다. worker는 쓰기를 못 하고, 단일 writer가 journal·rollback 있는 transaction으로 쓴다.

- [확인] apply 한 번이 도는 동안 vault 전체에 `MutationLock` 하나를 잡는다. flock이라 프로세스가 죽으면 lock도 풀린다. `fcntl.flock`과 디렉터리 fd를 쓴다 (`claude_obsidian/transaction.py:1486-1520`, `claude_obsidian/transaction.py:1646-2066`).
- [확인] 각 파일은 같은 디렉터리 temp 파일에 쓰고 `fsync` 후 `os.replace`한다. 부모 디렉터리도 `fsync`한다 (`claude_obsidian/transaction.py:828-890`).
- [확인] 쓰기 직전 파일마다 현재 hash와 mode를 다시 대조한다. 다르면 `EXPECTED_HASH_MISMATCH`로 멈추고 rollback한다 (`claude_obsidian/transaction.py:4720-4737`, `claude_obsidian/transaction.py:4770`).
- [확인] journal 상태는 `prepared → applying → complete`이고 실패하면 `rolled-back` 또는 `rollback-failed`다 (`claude_obsidian/transaction.py:4706`, `claude_obsidian/transaction.py:4111-4115`, `claude_obsidian/transaction.py:4799`).
- [확인] 같은 `operation_id`에 같은 bundle을 다시 적용하면 no-op이다. 다른 bundle이면 `OPERATION_ID_REUSED`로 거부한다 (`claude_obsidian/transaction.py:4571-4611`).
- [확인] symlink, parent swap, case-folding alias, Windows 예약 이름으로 vault 밖에 쓰는 경로를 막는다 (`claude_obsidian/transaction.py:197-358`, 테스트 `tests/test_transaction.py:913-1175`).
- [확인] 도구 허용 목록은 subagent frontmatter에만 있다. worker·lint·verifier 모두 `Read, Grep, Glob, Bash`다 (`agents/wiki-ingest.md:10`). Bash가 열려 있어서 셸로 쓰는 것은 prompt 규칙이 막는다 (`agents/wiki-ingest.md:65-68`).
- [확인] git은 선택이다. `checkpoint`는 임시 index로 tree를 만들고 compare-and-swap으로 ref를 갱신한다. 원본 payload는 기본으로 commit에서 뺀다 (`skills/wiki/references/operation-transactions.md:128-139`, `CHANGELOG.md:299-303`).
- [확인] native Windows에서는 쓰기를 거부하고 WSL을 요구한다 (`claude_obsidian/transaction.py:1388-1419`).

#### 11. Query·검색

입장: 계층 조회(hot → index → 페이지)에 선택적 BM25 hybrid를 얹는다. 답은 wiki에 자동 저장하지 않는다.

- [확인] Quick·Standard·Deep 세 깊이가 있다 (`skills/wiki-query/SKILL.md:31-38`).
- [확인] `scripts/contextual-prefix.py`가 페이지를 chunk로 나누고 chunk마다 문맥 prefix를 붙인다. 기본은 frontmatter와 첫 문단으로 만든 synthetic prefix다. Anthropic API나 `claude -p`는 `--allow-egress`일 때만 쓴다 (`scripts/contextual-prefix.py:11-34`).
- [확인] `scripts/bm25-index.py`가 결정적 BM25 index를 만든다. CJK는 n-gram으로 다룬다 (`CHANGELOG.md:279-282`).
- [확인] `scripts/rerank.py`는 로컬 Ollama embedding으로 cosine rerank한다. 실패하면 BM25 순서로 돌아간다 (`scripts/retrieve.py:5-17`). 그러나 query skill은 `retrieve.py`를 `--no-rerank`로 부른다. 그래서 query 경로의 검색은 BM25뿐이다 (`skills/wiki-query/SKILL.md:56`).
- [확인] query는 BM25 index가 `verified`일 때만 쓴다. index를 다시 만드는 일은 query가 하지 않는다 (`skills/wiki-query/SKILL.md:46-61`). ingest 뒤 index를 자동으로 다시 만드는 연결은 찾지 못했다.
- [확인] query는 cache를 만들거나 갱신하지 않는다 (`skills/wiki-query/SKILL.md:59-61`).
- [확인] 답을 남기려면 `save`로 넘긴다 (`skills/wiki-query/SKILL.md:97-100`). Karpathy 원문의 "좋은 답을 wiki에 되저장" 루프는 사용자의 명시적 요청으로만 돈다.

#### 12. index·log 관리

입장: index·log·hot은 LLM이 bundle 안에서 손으로 갱신한다. 결정적 재생성은 없다. lint가 index의 깨진 항목만 잡는다.

- [확인] `wiki/index.md`는 "curated catalog"이고 LLM이 갱신한다 (`WIKI.md:112-118`).
- [확인] index를 다시 만드는 코드는 없다. `claude_obsidian/` 안 `index.md` 언급은 bootstrap 경로와 fold 범위 검사뿐이다 (`claude_obsidian/transaction.py:118`, `claude_obsidian/transaction.py:3248`).
- [확인] lint는 index 페이지의 dead·ambiguous link를 `stale_index_entries`로 따로 센다 (`claude_obsidian/lint_engine.py:1074`, `claude_obsidian/lint_engine.py:1098`, `claude_obsidian/lint_engine.py:1127`).
- [확인] `wiki/log.md`는 파일 단위가 아니라 operation 단위 기록이고 최신이 위다 (`WIKI.md:120-125`).
- [확인] `wiki-fold` skill은 log 항목 2^k개를 추출식으로 접으라고 한다. ID는 입력에서 정해진 형식으로 만들라고 한다 (`skills/wiki-fold/SKILL.md:30-44`). 이 ID 계산과 추출식 여부는 prompt 규칙이다. 이를 계산하거나 검사하는 코드는 없다 (`grep "fold-k\|child_key"` 결과가 테스트 fixture뿐). 코드는 fold bundle이 fold 페이지 1개와 index·log만 쓰도록 경로 집합만 강제한다 (`claude_obsidian/transaction.py:3279-3297`).
- [확인] `wiki/hot.md`는 다음 세션용 짧은 문맥이다. save는 500단어 이하로 갱신하라고 한다 (`WIKI.md:127-134`, `skills/save/SKILL.md:75`). `SessionStart` hook은 `CLAUDE_OBSIDIAN_SESSION_CONTEXT=1`일 때만 hot.md를 주입한다 (`claude_obsidian/hook_adapter.py:180-184`).

#### 13. 포맷 표준

입장: OKF를 따르지 않는다. 자체 schema와 Obsidian Flavored Markdown을 쓴다.

- [확인] repo 전체에서 `OKF`나 `knowledge-catalog`를 찾지 못했다 (`grep -rni okf`).
- [확인] Obsidian 문법 기준은 kepano/obsidian-skills다 (`README.md` "Lineage" 절, `skills/obsidian-markdown/SKILL.md`).
- [추정] OKF §5가 frontmatter에 두는 provenance·trust·lifecycle을 이 repo는 별도 JSON ledger에 둔다 — 사례: `frontmatter.md` 규칙 8 "frontmatter confidence는 evidence가 아니다" (`skills/wiki/references/frontmatter.md:96-97`)와 ledger 필드 구성. 그래서 OKF로 옮기려면 ledger를 페이지 frontmatter로 펼치는 변환이 필요하다.

#### 14. 규모·비용

입장: 운영 규모나 비용 수치를 주장하지 않는다. 엔진 한계만 숫자로 밝힌다.

- [확인] README에 vault 크기, 페이지 수, ingest 비용 수치가 없다.
- [확인] v2.0.0에서 "Unsupported comparative, performance, and capability claims"를 문서에서 지웠다 (`CHANGELOG.md:319-320`).
- [확인] contextual prefix도 "고정된 이득을 주장하지 않는다"고 적는다 (`scripts/contextual-prefix.py:7-9`).
- [확인] 엔진 한계는 파일당 64 MiB, operation당 128 MiB, write 1,024개, capture queue 4,096개, address 999,999개다 (`claude_obsidian/transaction.py:138-151`, `claude_obsidian/capture.py:68-69`, `claude_obsidian/transaction.py:3037`).
- [확인] 컨텍스트 사용은 예산 방식이다. ingest는 원본당 기존 페이지 5개, save는 5개, fold는 child 페이지 0~10개(상한 15)를 읽는다 (`skills/wiki-ingest/SKILL.md:80-82`, `skills/save/SKILL.md:40-42`, `skills/wiki-fold/SKILL.md:34-35`).
- [확인] worker subagent는 `model: sonnet`, `maxTurns: 60`이다 (`agents/wiki-ingest.md:8-9`).

#### 15. frosk1 비판 7가지

| 비판 | 대응 | 근거 |
|---|---|---|
| 오류 누적 | [확인] `accepted`는 신선한 active 비합성 source가 있어야 한다. high-risk는 독립 source 2개가 필요하다. 독립성은 같은 origin·같은 bytes·같은 `independence_key`를 union-find로 묶어 센다. [추정] 라벨을 LLM이 붙이므로 잘못된 support 라벨은 그대로 쌓인다 — 사례: §8의 relation enum 검사. | `claude_obsidian/ledgers.py:797-837`, `claude_obsidian/ledgers.py:1094-1136` |
| 부분 문맥 | [확인] 기존 페이지 읽기를 기본 5개로 묶고 원본은 끝까지 읽으라고 한다. 다 못 읽으면 `partial`로 표시한다. 전체 vault를 보는 장치는 없다. | `skills/wiki-ingest/SKILL.md:80-85`, `agents/wiki-ingest.md:105-109` |
| 요약 손실 | [확인] 원본은 `.raw/`에 create-only로 남는다. 페이지를 만들 가치가 없으면 만들지 말라는 gate가 있다. [확인] query skill은 원본 재독을 단계로 두지 않는다. 페이지와 ledger까지만 읽는다. | `skills/wiki-ingest/SKILL.md:62-64`, `skills/wiki-ingest/SKILL.md:75-79`, `skills/wiki-query/SKILL.md:69-95` |
| 가짜 source of truth | [확인] hot.md는 "orientation, not evidence", index는 "not evidence by itself"라고 규정한다. ledger가 없으면 없다고 말하라고 한다. | `skills/wiki-query/SKILL.md:8-9`, `WIKI.md:114-115`, `skills/wiki-query/SKILL.md:84-85` |
| 환각 병합 | [확인] 모순은 보존하고 승자를 조용히 고르지 말라는 규칙이 있다. 코드는 신선한 반대 근거가 있는 `accepted`에 notes를 요구한다. worker는 충돌을 해결하지 말고 표시만 한다. | `skills/wiki/references/provenance.md:46`, `claude_obsidian/ledgers.py:1137-1150`, `agents/wiki-ingest.md:61-63` |
| 운영 복잡도 | [확인] 대응하지 않고 받아들였다. 엔진 19k줄, 테스트 19k줄, transaction 모듈 하나가 4,803줄이다. [추정] 이 갈래 구현 중 복잡도 비용이 가장 크다 — 사례: 같은 갈래 Ar9av/obsidian-wiki의 Python 패키지가 약 15k줄이고 쓰기는 agent가 직접 한다. | `claude_obsidian/transaction.py`, `wc -l` 결과 |
| ingest 비용 | [확인] 원본 수·바이트·페이지·요청 예산을 사용자와 먼저 정하라고 한다. 큰 batch는 첫 tranche만 하라고 한다. 측정·기록 장치는 없다. | `skills/wiki-ingest/SKILL.md:27-32` |

참고: frosk1 원문에는 8번째로 staleness가 있다. 이 repo는 `refresh_due` 기반 결정적 stale 감지로 대응한다 (§8).

#### 16. 성숙도·차용 가능성

입장: 테스트가 두껍고 의존성이 없으며 MIT라 코드 차용이 가능하다. 다만 엔진이 크고 POSIX 전용이다.

- [확인] 테스트 파일 37개, Python 테스트 함수 534개다. CI는 Linux·macOS × Python 3.11~3.14 matrix와 Windows smoke job이다 (`.github/workflows/test.yml`).
- [확인] CI는 테스트 뒤 `git status`가 깨끗한지 확인해 테스트가 product 파일을 바꾸지 않았음을 증명한다 (`.github/workflows/test.yml` "Prove tests did not mutate" 단계).
- [확인] transaction 테스트는 rollback, hash 충돌, parent swap, approval의 vault 결속, idempotent replay를 다룬다 (`tests/test_transaction.py:61-2781`의 함수 이름).
- [확인] 런타임 의존은 Python 3.11 표준 라이브러리다. Ollama, Obsidian CLI, defuddle은 선택이다 (`README.md` "Requirements").
- [확인] 라이선스는 MIT다 (`LICENSE`, `gh api`).
- [추정] 떼어 쓰기 가장 쉬운 단위는 `lint_engine.py`(1,381줄)다 — 사례: 모듈 첫머리 import가 `gitignore`, `json_utils` 둘뿐이다. ledger와 transaction은 함수 안에서 늦게 import한다 (`claude_obsidian/lint_engine.py:58-59`, `claude_obsidian/lint_engine.py:827-860`).
- [확인] `ledgers.py`(1,365줄)는 모듈 첫머리에서 `transaction.py`의 `_safe_hash`, `read_vault_regular`를 import한다 (`claude_obsidian/ledgers.py:17`). 그래서 `ledgers.py`만 가져와도 4,803줄짜리 `transaction.py`가 함께 딸려 온다. 떼어 쓰려면 이 두 함수를 바꿔 끼워야 한다.

## 장점

- [확인] worker는 초안만 만들고 쓰기는 orchestrator 하나가 transaction 하나로 한다. 이 원칙이 문서·agent 도구 목록·엔진 범위 검사 세 곳에 함께 있다 (`skills/wiki-ingest/SKILL.md:95-97`, `agents/wiki-ingest.md:10`, `claude_obsidian/transaction.py:3172-3277`).
- [확인] 승인 hash가 bundle 내용뿐 아니라 vault 정체성과 파일 mode까지 묶는다. 다른 vault에 재사용하거나 검토 후 바뀐 계획을 적용할 수 없다 (`claude_obsidian/transaction.py:1287-1309`).
- [확인] 중단된 쓰기는 journal로 복구된다. 턴이 끝날 때 `Stop` hook이 복구가 필요한 journal 수를 `systemMessage`로 알린다 (`claude_obsidian/transaction.py:4215-4387`, `claude_obsidian/hook_adapter.py:218-320`, `hooks/README.md`).
- [확인] source ledger와 claim ledger를 나누고 ingest manifest와도 분리했다. 한 파일에 세 역할을 몰지 않는다 (`skills/wiki/references/provenance.md:14-23`).
- [확인] claim의 wiki 쪽 위치(heading·block)와 source의 bytes hash를 결정적으로 검증한다 (`claude_obsidian/ledgers.py:964-1030`, `claude_obsidian/ledgers.py:666-700`).
- [확인] 시간 경과 stale이 `refresh_due` 하나로 계산된다. 저장된 stale 플래그가 실제와 어긋날 일이 없다 (`claude_obsidian/ledgers.py:752-758`). 다만 `refresh_due` 날짜 자체는 LLM이 정한다 (§8).
- [확인] lint가 결정적이고 `--as-of`로 재현 가능하다. LLM lint와 경계가 분명하다 (`skills/wiki-lint/SKILL.md:47-52`).
- [확인] operation type이 쓰기 권한 경계다. `generic`도 `wiki/`만 쓸 수 있다 (`claude_obsidian/transaction.py:92-98`).
- [확인] 기능 성숙도를 `implemented / metadata-only / external-runner-required`로 표시한다. 못 하는 것을 하는 척하지 않는다 (`config/adapters.json`).

## 단점

- [확인] Write/Edit 직접 쓰기를 막는 hook이 없다. transaction 경로는 LLM이 skill을 따를 때만 지켜진다 (`hooks/hooks.json`, `claude_obsidian/package_validation.py:20-28`에 `PreToolUse`가 허용 목록에만 있다).
- [확인] 승인 hash를 agent가 직접 얻어 넘길 수 있다. "사람이 봤다"는 코드로 보장되지 않는다 (`skills/wiki-ingest/SKILL.md:133-138`). hash 요구도 CLI에만 있다. `apply_bundle()`은 hash 없이 불러도 적용한다 (`claude_obsidian/transaction.py:4521-4531`, `tests/test_transaction.py:71`).
- [확인] ledger 검증은 bundle에 ledger가 있을 때만 돈다. claim 기록 없이 페이지만 쓰는 ingest도 통과한다 (`claude_obsidian/transaction.py:3641-3642`).
- [확인] 페이지 `type` 값은 어디서도 검사하지 않는다. lint는 필드가 있는지만 본다 (`claude_obsidian/page_schema.py:7-8`).
- [확인] checkpoint의 lint gate는 `--skip-lint` 한 번으로 꺼진다 (`claude_obsidian/cli.py:1235`).
- [확인] evidence locator와 excerpt를 원문과 대조하지 않는다. claim이 원본의 어느 문장에서 왔는지는 검증되지 않는다 (`claude_obsidian/ledgers.py:1089-1093`).
- [확인] ingest가 index·log·hot을 함께 갱신해야 한다는 규칙은 prompt뿐이다. 빠뜨려도 inspect를 통과한다 (`claude_obsidian/transaction.py:3279-3297`은 fold만 검사).
- [확인] index를 결정적으로 다시 만들 수 없다. 깨진 항목은 lint로 찾고 LLM이 손으로 고친다 (§12).
- [확인] 엔진에는 PDF·이미지·URL 내용 추출이 없다. URL·OCR은 외부 runner를 사용자가 따로 붙여야 한다 (`config/adapters.json`). skill은 host가 PDF·이미지를 읽을 수 있으면 그 능력을 쓰라고 한다 (`skills/wiki-ingest/SKILL.md:56-58`). 그래서 실제로 읽히는지는 host에 달려 있다.
- [확인] 쓰기는 POSIX 전용이다. native Windows는 WSL이 필요하다 (`claude_obsidian/transaction.py:1388-1419`).
- [확인] 문서와 코드 사이에 작은 어긋남이 있다. `claim-example` vs `clm-` 접두사, `risk: low` vs `{normal, high}`, frontmatter의 `review_state` vs ledger의 `review_status` (`skills/wiki/references/frontmatter.md:22-23`, `skills/wiki/references/frontmatter.md:47`, `claude_obsidian/ledgers.py:576`).
- [추정] LLM이 bundle JSON을 올바르게 짜는 부담이 있다 — 사례: 모든 write에 `expected_hashes`를 맞춰야 하고, `content_file`을 쓰면 `sha256`도 맞춰야 한다 (`claude_obsidian/transaction.py:3426-3430`, `claude_obsidian/transaction.py:3458-3462`). ledger를 넣으면 ledger 규칙 전체도 통과해야 한다. 다만 address counter와 `.raw/.manifest.json`의 쓰기와 expected hash는 엔진이 대신 채운다 (`claude_obsidian/transaction.py:2875-3127`). ledger는 넣지 않아도 된다. 실패율 측정은 찾지 못했다.

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

- worker는 draft packet만 돌려주고 orchestrator 하나가 적용하는 구조. packet 형식(`status, proposals[path, action, expected_sha256, content], evidence, contradictions, partial`)을 그대로 쓸 만하다 (`agents/wiki-ingest.md:72-109`).
- 모든 write에 expected hash를 요구하고 적용 직전 다시 대조하는 optimistic concurrency (`claude_obsidian/transaction.py:3429`, `claude_obsidian/transaction.py:4720-4737`).
- 승인 hash에 vault 정체성과 확장된 계획을 함께 묶는 방식. 단, 사람 확인을 강제하려면 hash를 사람 쪽 채널로만 받게 바꿔야 한다.
- operation type = 쓰기 권한 경계라는 발상 (`claude_obsidian/transaction.py:3172-3277`).
- source ledger / claim ledger / ingest manifest를 세 파일로 나누는 분리 (`skills/wiki/references/provenance.md:14-23`).
- claim assessment 5단계(`accepted, provisional, contested, unsupported, deprecated`)와 "accepted는 신선한 비합성 source 필요, high-risk는 독립 source 2개" 규칙 (`claude_obsidian/ledgers.py:1094-1136`).
- `refresh_due`에서 stale을 계산하고 플래그를 저장하지 않는 방식.
- `independence_key`와 origin·bytes를 union-find로 묶어 독립 source 수를 세는 함수 (`claude_obsidian/ledgers.py:797-837`).
- `--as-of`로 재현되는 결정적 lint와, commit을 막는 범주와 경고만 하는 범주를 나눈 checkpoint gate (`claude_obsidian/checkpoint.py:41-49`).
- "compilation-value gate": 가치가 없으면 페이지를 만들지 않는다 (`skills/wiki-ingest/SKILL.md:75-79`).

### 피할 것

- 쓰기 규칙을 prompt에만 두는 것. 내 repo는 `PreToolUse` hook으로 vault 경로 Write/Edit을 막아 transaction 경로를 유일한 길로 만든다.
- 승인을 agent가 자기 손으로 닫을 수 있는 two-step. plan 승인을 진짜 사람 관문으로 쓰려면 별도 확인 단계가 필요하다.
- 승인 검사를 CLI 층에만 두는 것. 엔진 함수(`apply_bundle`)가 hash 없이도 적용하면 Bash가 열린 agent가 우회한다. 승인 요구는 적용 함수 안에 둔다. Write/Edit용 `PreToolUse` hook만으로는 이 우회를 막지 못한다.
- ledger 기록을 선택으로 두는 것. ingest operation이면 claim·source 기록이 함께 있어야 inspect를 통과하게 한다.
- locator·excerpt를 자기 신고로 두는 것. 원문 글자 일치나 줄 범위 대조를 넣지 않으면 claim ledger가 "이 파일에서 왔다"까지만 보장한다.
- index를 LLM이 손으로 관리하는 것. frontmatter에서 결정적으로 재생성하면 stale index 범주 자체가 사라진다.
- 4,800줄 transaction 엔진을 처음부터 따라 만드는 것. fd confinement와 symlink 방어가 필요한 위협 모델(공개 배포 plugin)이 아니라면 범위를 줄인다.

## 확인하지 못한 것

- 테스트와 CI 통과 여부. 지시에 따라 repo 코드를 실행하지 않았다. GitHub Actions 결과를 보면 알 수 있다.
- 실제 LLM이 bundle을 한 번에 올바르게 짜는 비율. 이슈 목록(GitHub `open_issues_count` 28개, PR 포함 값)이나 사용자 vault 사례를 보면 알 수 있다.
- 실제 운영 vault의 크기와 ingest 비용. repo가 수치를 밝히지 않는다. 사용자 보고나 discussion을 보면 알 수 있다.
- v1.x에서 v2.0.0으로 넘어온 이유의 구체 사례. shallow clone이라 history가 없다. CHANGELOG는 v2.0.0에서 지운 것만 적는다. "Direct shared writes, automatic Git commits, and per-file locks"와 generic `PostToolUse` 동작이다 (`CHANGELOG.md:316-318`). 무엇이 계기였는지는 전체 clone의 `git log`나 v2.0.0 PR을 보면 알 수 있다.
- Claude Code가 `Stop` hook의 `systemMessage`를 모델에게도 보여 주는지. hook 문서를 보면 알 수 있다.
- `contracts.py`(1,365줄)와 `release.py`(2,591줄)는 product 배포 검증용이라 깊이 읽지 않았다. llm-wiki 동작과의 관련은 낮다고 보지만 확인하지 않았다.
- capture queue를 실제로 소비하는 외부 runner 예시. `config/adapters.json`이 runner capability 이름만 적는다.

## 검증 기록

보고서의 경로·줄 번호 인용을 repo 코드(`32ac5a0`)와 대조했다. repo 코드는 실행하지 않았다. 고친 것은 아래와 같다.

- 한 바퀴 흐름 Query 3번과 §11: query skill이 `retrieve.py`를 `--no-rerank`로 부르는 사실을 넣었다. query 경로에 Ollama rerank가 붙는다는 서술을 바로잡았다.
- §2: bundle에 ledger가 없으면 ledger 검증을 건너뛴다는 항목을 더했다.
- §2·§9·단점: 승인 hash 요구가 CLI 층에만 있다는 항목을 더했다. `apply_bundle()`은 hash 없이도 적용한다.
- §2 [추정]: "다음 transaction의 expected hash 검사가 직접 쓰기 흔적을 잡을 수 있다"를 고쳤다. expected hash는 초안 시점 값이라 잡지 못한다.
- §3: `folds/`의 출처를 WIKI.md가 아니라 transaction 엔진으로 고쳤다.
- §3·단점: 페이지 `type` 값을 lint도 엔진도 검사하지 않는다는 항목을 더했다.
- §3: frontmatter `claim_ids`를 읽는 코드가 없다는 점을 더했다.
- §5: `anchor`가 null이면 페이지 존재만 본다는 점과 claim text를 본문과 대조하지 않는다는 점을 더했다.
- §5: bytes hash 대조가 file source에만 적용된다는 점과 authority·risk·refresh_due가 LLM 자기 신고라는 점을 더했다.
- §7·단점: checkpoint lint gate를 `--skip-lint`로 끌 수 있다는 점과 lint가 vault 전체를 돈다는 점을 더했다. 인용 줄을 1338-1356으로 고쳤다.
- §8: `refresh_due`와 `risk` 값으로 stale·2-source 규칙을 피할 수 있다는 [추정]을 더했다.
- §9: operation-transactions.md:33-34의 실제 문구(파괴적·외부·canonical merge)에 맞췄다. canonical replace는 wiki-ingest 인용으로 옮겼다.
- §10: lock을 "프로세스 수명 동안" 잡는다는 표현을 "apply 한 번이 도는 동안"으로 고쳤다.
- §12: fold ID와 추출식 여부가 prompt 규칙이고 코드는 경로 집합만 강제한다고 고쳤다.
- §6: boundary score에 최근성 가중치가 곱해진다는 점을 더했다.
- §16: `ledgers.py`가 첫머리에서 `transaction.py`를 import하므로 떼어 쓰기 쉽다는 [추정]을 `lint_engine.py`로 좁혔다. 테스트 인용 범위를 61-2781로 고쳤다.
- 장점: Stop hook이 "다음 세션 전에" 알린다는 표현을 "턴이 끝날 때 systemMessage로"로 고쳤다. refresh_due 값은 LLM이 정한다는 단서를 붙였다.
- 단점: bundle 작성 부담 [추정]을 고쳤다. address counter와 manifest는 엔진이 채우고 ledger는 선택이다. 멀티포맷 단점은 엔진 한정으로 좁혔다.
- 피할 것: 승인 검사를 엔진 함수 안에 두기와 ingest에서 ledger를 필수로 하기를 더했다.
- 확인하지 못한 것: 열린 이슈 수가 PR을 포함한 값이라는 점, v2.0.0에서 지운 것의 CHANGELOG 인용, Stop hook 메시지가 모델에 닿는지를 더했다.

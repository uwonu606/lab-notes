# Ar9av/obsidian-wiki — 판단은 프롬프트 skill에 두고, 여러 writer가 부딪히는 파일만 Python CLI가 잠그고 다시 만든다

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/Ar9av/obsidian-wiki |
| clone commit | `df54595` (shallow clone, 2026-10-10 커밋) |
| 별 / fork | 3,546 / 359 (`gh api`, 2026-10-11 조회) |
| 생성 / 최근 push | 2026-04-06 / 2026-10-10 |
| 라이선스 | MIT |
| 형태 | skill pack(`.skills/` 아래 디렉터리 40개) + 의존성 없는 Python CLI `obsidian-wiki` + 선택형 HTTP·MCP 서버 + Claude Code hook 2개 |
| 코드 규모 | `obsidian_wiki/*.py` 15,202줄, `scripts/` 약 1,000줄, `tests/*.py` 15,518줄(테스트 함수 1,115개), `SKILL.md`만 11,460줄(references 포함 14,362줄) |

- [확인] README와 문서는 skill 수를 39개라고 적는다(`docs/architecture.md:209`). 실제 `.skills/` 디렉터리는 40개다.
- [확인] 문서는 "No scripts run your knowledge pipeline"이라고 말한다(`docs/architecture.md:5`). `AGENTS.md:3`도 "No scripts or dependencies"라고 적는다.
- [확인] 하지만 핵심 skill들은 CLI를 실제로 부른다. `wiki-ingest` SKILL.md에 CLI 호출이 9군데 있다. `wiki-update`·`wiki-lint`에 7군데씩 있다. skill 전체에서 가장 많이 불리는 명령은 `obsidian-wiki memory sync`(명령 줄 21회)다.
- [확인] `obsidian-wiki setup`은 기본값으로 SessionStart·Stop hook을 사용자 전역 `~/.claude/settings.json`에 등록한다. 끄려면 `--no-hooks`를 줘야 한다(`obsidian_wiki/cli.py:1136-1141`, `:3335-3337`).
- [추정] "스크립트 없음"은 초기 설계의 문구가 남은 것이다 — 사례: 문서 2곳이 그렇게 말하지만, 같은 문서 `docs/architecture.md:140-144`는 manifest와 index를 CLI로만 쓰라고 지시한다.

## 한 바퀴 흐름

### Ingest (`/wiki-ingest`)
1. 에이전트가 config를 찾는다. 순서는 `@name` → CWD에서 위로 올라가며 `.env` → 전역 config다(`AGENTS.md` Configuration 절).
2. 에이전트가 `WIKI_STAGED_WRITES`를 읽는다. 값이 true면 이후 쓰기 경로를 `_staging/`으로 바꾼다(`.skills/wiki-ingest/SKILL.md:17`).
3. 에이전트가 `obsidian-wiki cache-check <vault> <sources…>`를 부른다. `cache.check_sources`가 SHA-256으로 소스를 new/modified/unchanged/missing/unavailable로 나눈다(`obsidian_wiki/cache.py:418-486`).
4. 파일이 20개를 넘는 디렉터리면 `obsidian-wiki batch-plan`이 배치를 나눈다. 에이전트는 배치마다 subagent를 병렬로 띄운다(`.skills/wiki-ingest/SKILL.md:105-126`, `obsidian_wiki/batch.py`).
5. 코드 파일이면 `obsidian-wiki ast-extract`가 정규식(선택 시 tree-sitter)으로 class·function·import 그래프를 뽑는다. 코드 본문은 LLM에 보내지 않는다(`.skills/wiki-ingest/SKILL.md:295-327`, `obsidian_wiki/ast_extractor.py`).
6. LLM이 개념·entity·claim·관계를 뽑는다. claim마다 extracted/inferred/ambiguous를 머릿속으로 구분한다(`.skills/wiki-ingest/SKILL.md:330-344`).
7. LLM이 갱신할 페이지 목록을 세운다. 상한은 `OBSIDIAN_MAX_PAGES_PER_INGEST`(기본 15)다(`.skills/wiki-ingest/SKILL.md:357`).
8. LLM이 페이지를 직접 쓴다. frontmatter, `^[inferred]` 표시, `provenance:` 비율, `base_confidence`, `lifecycle: draft`를 함께 쓴다(`.skills/wiki-ingest/SKILL.md:405-457`).
9. `_raw/` 초안이었다면 원본을 `_raw/_archived/`로 옮긴다. 이어서 `obsidian-wiki snapshots set`이 페이지 frontmatter에 `snapshots:`를 쓴다(`obsidian_wiki/snapshots.py:76`).
10. `obsidian-wiki cache-update`가 lock을 잡고 manifest를 원자적으로 바꾼다(`obsidian_wiki/cache.py:489-610`).
11. `obsidian-wiki memory sync INGEST …`가 log 한 줄 추가, `index.md` 재생성, `hot.md` 재생성을 한 lock 안에서 한다(`obsidian_wiki/memory.py:636-733`, `:1110`, `:1190`).

### Query (`/wiki-query`)
1. 에이전트가 `hot.md`와 `index.md`를 읽는다(`.skills/wiki-query/SKILL.md:28-29`).
2. `obsidian-wiki graph-query`가 frontmatter와 wikilink로 메모리 안 색인을 만든다. 제목·태그·summary 단어 일치와 degree로 후보 점수를 매긴다(`obsidian_wiki/graphrag.py:98`, `:202-229`).
3. 결과의 `index_only`가 true면 summary만으로 답한다. 아니면 grep 구간 읽기, 전체 읽기 순으로 올라간다(`.skills/wiki-query/SKILL.md:84`, `:208-216`).
4. 답을 만든 뒤 `obsidian-wiki memory log QUERY`로 log에 한 줄만 쓴다. 다른 쓰기는 금지다(`.skills/wiki-query/SKILL.md:11-13`, `:294-305`).

### Lint (`/wiki-lint`)
1. 에이전트가 `obsidian-wiki lint --json`을 부른다. `lint.lint_vault`가 결정적 검사를 돌린다(`obsidian_wiki/lint.py:307-654`).
2. LLM이 나머지 검사를 손으로 한다. 모순, 오래된 내용, provenance 비율, 태그 군집, synthesis 공백이 여기에 든다(`.skills/wiki-lint/SKILL.md:90-139`, `:392`).
3. `--consolidate`면 dry-run 목록을 보여 주고 사람 확인을 받는다. 그 전에 vault가 git root면 스냅샷 커밋을 만든다(`.skills/wiki-lint/SKILL.md:485-534`).

## 축별 분석

#### 1. 실행 형태
입장: skill + 결정적 CLI 혼합형이다. 선택형 HTTP·MCP 서버도 있다.
- [확인] 판단(무엇을 뽑고 어디에 합칠지)은 전부 `SKILL.md` 프롬프트에 있다. LLM 호출 코드는 Python 안에 없다(`obsidian_wiki/server.py:3-5` "The container does no LLM work").
- [확인] 반복 가능한 일은 CLI가 한다. hash delta, manifest 쓰기, index·hot·log 재생성, lint, staging 이동, AST 추출, 그래프 질의가 여기에 든다(`obsidian_wiki/cli.py:2785-3282` subparser 목록).
- [확인] 일부 CLI 호출에는 CLI가 없을 때의 fallback이 적혀 있다. 예: `.skills/wiki-ingest/SKILL.md:61`, `:128`, `.skills/wiki-query/SKILL.md:113`, `.skills/wiki-lint/SKILL.md:28`.
- [확인] 하지만 index·log·hot 갱신에는 fallback이 없다. `wiki-ingest`는 `memory sync`를 쓰고 "Never hand-edit those three files"라고 적는다(`.skills/wiki-ingest/SKILL.md:493-496`). `daily-update`도 "do not fall back to hand-editing"이라고 적는다(`.skills/daily-update/SKILL.md:51`). CLI가 없으면 이 세 파일은 갱신되지 않는다.
- [확인] 서버는 FastAPI + MCP다. API key가 없으면 시작을 거부한다(`obsidian_wiki/server.py:36-43`).
- [확인] 그런데 key 검사(`require_key`)는 `/v1/*` route에만 붙어 있다. MCP 앱은 `app.mount("/mcp", _mcp_app)`로 붙고 인증 의존성이 없다(`obsidian_wiki/server.py:303-317`). 문서는 `/mcp`에도 Bearer token이 필요하다고 적는다(`docs/configuration.md:313`, `docs/deployment.md:38`). `/mcp` 인증을 검사하는 테스트도 없다(`tests/test_server.py`).
- [추정] `/mcp`의 `memory_write`·`memory_profile` 등 MCP tool 8개는 key 없이 호출된다 — 사례: 위 코드 1건. 서버를 띄워 key 없이 `/mcp`에 요청해 보면 알 수 있다.
- [확인] 에이전트 bootstrap 파일이 10종이다. `CLAUDE.md`, `GEMINI.md`, `.hermes.md`는 `AGENTS.md`의 symlink다(`docs/architecture.md:215-224`).

#### 2. 규칙의 위치
입장: 내용 규칙은 프롬프트에 있다. 구조 규칙의 일부만 사후 lint가 코드로 잡는다. 쓰기 시점 gate는 없다.
- [확인] 필수 frontmatter 6개, 관계 타입 7개, lifecycle 5개는 코드 기본값이다(`obsidian_wiki/lint.py:38-56`, `obsidian_wiki/trust.py:32`). lifecycle·관계 타입 목록은 vault config(`OBSIDIAN_ALLOWED_LIFECYCLES`, `OBSIDIAN_ALLOWED_RELATIONSHIP_TYPES`)로 바꿀 수 있다(`obsidian_wiki/cli.py:1754-1756`).
- [확인] 이 상수는 `lint`가 읽을 때만 적용된다. 페이지 쓰기는 에이전트의 Write 도구로 바로 일어난다.
- [확인] 예외는 서버 `write_page`다. 이 함수는 필수 6개 필드와 `summary`를 코드로 채운다(`obsidian_wiki/server.py:111-125`). 하지만 `lifecycle`·`base_confidence`는 쓰지 않는다. manifest와 index도 갱신하지 않고 log 한 줄만 남긴다(`:127-132`).
- [확인] `WIKI_STAGED_WRITES`를 읽는 Python 코드는 없다. CLI help 문자열과 docstring에만 나온다(`obsidian_wiki/cli.py:3014`, `obsidian_wiki/staging.py:3`). staging 모드를 지키는 것은 LLM이다.
- [확인] HTTP·MCP `write_page`는 staging을 무시하고 live 경로에 바로 쓴다(`obsidian_wiki/server.py:91-133`).
- [확인] pre-commit hook은 저장소 어디에도 없다. `obsidian-wiki sync`는 lint 없이 `git add -A`, commit, push를 한다(`obsidian_wiki/sync.py:97-121`).
- [확인] lifecycle 전이 규칙("reviewed 이상은 사람만")은 프롬프트에 있다(`.skills/llm-wiki/SKILL.md:459-473`). 코드는 trust ledger에 기록된 이전 값과 비교해 금지 전이 두 부류만 사후에 보고한다. `draft`로 되돌아가는 전이와 `archived`에서 나가는 전이다(`obsidian_wiki/trust.py:40-43`, `:739`). LLM이 `draft→reviewed`로 올리는 것은 이 검사에 걸리지 않는다. fingerprint도 `lifecycle`을 volatile 필드로 빼고 계산한다(`obsidian_wiki/trust.py:48-55`).
- [확인] `trust-record`는 `--approved` 플래그를 필수로 받는다(`obsidian_wiki/cli.py:3115-3119`). 이 플래그는 호출자가 스스로 붙이는 선언이고, 사람이 승인했는지 코드가 확인하지는 않는다.

#### 3. 저장 구조
입장: Karpathy 3계층 위에 카테고리 디렉터리 7개, 도구 소유 디렉터리 5개, 상태 파일 여러 개를 얹었다.
- [확인] 카테고리는 `concepts/ entities/ skills/ references/ synthesis/ journal/ projects/`다(`docs/architecture.md:106-129`).
- [확인] 도구 소유 디렉터리는 `_raw/`(초안 투입구), `_raw/_archived/`(승격된 원본 스냅샷), `_staging/`(리뷰 큐), `_archives/`(rebuild용 전체 스냅샷), `_readouts/`, `_meta/`다.
- [확인] 필수 frontmatter는 `title, category, tags, sources, created, updated`다(`obsidian_wiki/lint.py:38-45`).
- [확인] 선택 frontmatter가 많다. `summary, aliases, relationships, provenance, base_confidence, lifecycle, lifecycle_changed, tier, snapshots, valid_from, valid_until, superseded_by, redirects_to, visibility/ 태그`가 있다(`.skills/llm-wiki/SKILL.md:182-209`, `obsidian_wiki/temporal.py:23-24`).
- [확인] 상태 파일은 `.manifest.json`(소스 ledger), `.manifest.lock`, `.memory.lock`, `index.md`, `log.md`, `hot.md`, `_meta/taxonomy.md`, `_meta/profile.md`, `_meta/todos.md`, `_meta/trust-ledger.json`, `_insights.md`다.
- [확인] manifest 항목은 `content_hash, last_ingested, pages_produced`를 CLI가 쓴다. `source_type, project`는 LLM이 쓰는 참고 필드다(`.skills/wiki-ingest/SKILL.md:466-476`).
- [확인] 같은 단계가 LLM에게 manifest를 손으로 고치라고도 지시한다. 항목 추가·갱신, `stats.total_sources_ingested`·`stats.total_pages` 갱신이 그것이다. `cache-update`를 쓰라는 지시는 "In parallel runs"에 한정된다(`.skills/wiki-ingest/SKILL.md:464`, `:478-480`). `stats`와 `source_type`을 쓰는 Python 코드는 없다.
- [확인] manifest key는 이식 가능한 형태를 기본으로 한다. vault 상대 경로, `~` 상대 경로, `repo:`/`url:`/`agent:` 접두어다(`obsidian_wiki/cache.py:489-523`). 둘 다 해당하지 않으면 경고를 찍고 절대 경로를 그대로 저장한다(`obsidian_wiki/cache.py:516-524`). 강제가 아니다.
- [확인] provenance 필드 이름이 문서끼리 어긋난다. `wiki-ingest`는 `pages_produced`를 쓰라고 한다(`.skills/wiki-ingest/SKILL.md:470`, `:476`). `llm-wiki`는 `pages_created`·`pages_updated`를 쓰라고 한다(`.skills/llm-wiki/SKILL.md:176`). 코드는 `pages_produced`와 `pages_created`만 읽는다(`obsidian_wiki/provenance.py:13`). 여러 기기에서 vault를 sync하려는 목적이다(`docs/architecture.md:146`).
- [확인] 페이지 frontmatter 파서는 PyYAML이 아니다. 정규식 기반 자체 파서다(`obsidian_wiki/memory.py:161`, `obsidian_wiki/lint.py:133`).

#### 4. Ingest
입장: 기본은 자율 실행이다. 증분은 hash로 결정적으로 판정한다. 병렬 fan-out은 CLI를 거치는 manifest·memory 쓰기만 lock으로 받친다. queue·crash 복구는 없다.
- 사람 참여: [확인] 기본 모드는 사람 확인 없이 쓴다. `WIKI_STAGED_WRITES=true`일 때만 리뷰 큐로 간다(`.skills/wiki-ingest/SKILL.md:377-403`).
- 증분: [확인] SHA-256 hash가 판정 신호다(`obsidian_wiki/cache.py:377-403`, `:469-473`). 코드에는 mtime 판정이 없다. 항목에 `content_hash`가 없으면 빈 문자열과 비교되어 "modified"가 된다(`obsidian_wiki/cache.py:220-223`). mtime으로 떨어지는 것은 CLI가 없을 때의 손 fallback뿐이다(`.skills/wiki-ingest/SKILL.md:61`).
- 증분: [확인] 프로젝트 코드는 `last_commit_synced`와 `git log` 차이로 증분 처리한다(`docs/architecture.md:75-100`, `obsidian_wiki/cache.py:669`).
- 수정된 소스: [확인] "modified → re-ingest"만 적혀 있다(`.skills/wiki-ingest/SKILL.md:50`). 옛 버전에서 나온 claim을 찾아 지우는 절차는 문서 소스에는 없다. `pages_produced`는 덮어쓰기만 한다(`obsidian_wiki/cache.py:574-575`).
- 수정된 소스(코드): [확인] 프로젝트 코드는 다르다. `wiki-update`는 기존 페이지의 코드 관계를 현재 focus map과 대조해 사라진 것을 지우라고 "required"로 지시한다(`.skills/wiki-update/SKILL.md:93`, `docs/architecture.md:84`). 이 대조도 LLM이 한다.
- queue·crash 복구: [확인] ingest journal이나 작업 큐는 없다. manifest는 소스 처리가 끝난 뒤 갱신된다. 중간에 끊기면 그 소스는 다음 실행에서 다시 "new/modified"가 된다. 그 사이 반쯤 쓴 페이지는 그대로 남는다.
- 자동 감시: [확인] 파일 감시자는 없다. `scripts/daily-update.sh`와 systemd timer·launchd plist는 "바뀐 소스 수"만 세서 알린다. ingest는 하지 않는다(`scripts/daily-update.sh:70-130`).
- 자동 감시: [확인] 그 카운트는 manifest 최상위 `last_updated`를 읽는다(`scripts/daily-update.sh:95`). 이 필드를 쓰는 Python 코드는 없다. `wiki-status` 문서의 예시 schema에만 나온다(`.skills/wiki-status/SKILL.md:28`). LLM이 그 필드를 안 쓰면 카운트는 항상 0이다.
- 자동 감시: [확인] Claude Code Stop hook이 세션 끝에 `/wiki-capture --quick`을 권한다(`.claude/hooks/wiki-stop-capture.sh:1-12`). 이것이 사실상의 자동 투입 경로다.
- 멀티포맷: [확인] PDF·이미지·JSON·CSV·HTML·채팅 export는 변환기 없이 LLM이 Read 도구로 직접 읽는다(`.skills/wiki-ingest/SKILL.md:161-192`). 결정적 변환기는 Claude JSONL용 `scripts/extract-jsonl.py`와 코드용 `ast-extract`뿐이다. 긴 PDF는 외부 PageIndex를 선택적으로 쓴다(`.skills/wiki-ingest/SKILL.md:211-220`).
- 소스당 페이지 수: [확인] 목표 10, 상한 15다(`.skills/wiki-ingest/SKILL.md:357`). 논문은 예외로 풍부한 한 페이지를 만든다(`:233`).

#### 5. 근거 추적 단위
입장: 페이지 단위 출처 + 문장 단위 provenance 라벨이다. 원문 글자 일치나 줄 범위는 없다.
- [확인] 페이지는 `sources:` frontmatter와 본문 끝 `## Sources` 절에 출처를 적는다(`.skills/llm-wiki/SKILL.md:230-240`).
- [확인] `snapshots:`는 manifest의 `pages_produced`를 뒤집어 "이 페이지가 어떤 보관 원본에서 나왔나"를 적는다. lint가 기대값과 비교해 `snapshot_mismatch` 경고를 낸다(`docs/adr/0001-ledger-invert-for-page-sources.md`, `obsidian_wiki/lint.py:426-452`).
- [확인] `^[inferred]`·`^[ambiguous]` 표시는 claim 단위다. 하지만 표시가 없는 문장이 "extracted"로 간주된다(`.skills/llm-wiki/SKILL.md:314-318`). 어느 소스의 어느 구간인지는 연결하지 않는다.
- [확인] 이 표시를 세는 Python 코드는 없다. `obsidian_wiki/` 전체에서 `inferred` 문자열은 `client.py:291` 한 곳뿐이다. 비율 계산과 drift 판정은 LLM lint 몫이다(`.skills/wiki-lint/SKILL.md:119-137`).
- [확인] 코드 ingest만 `file:line` 근거를 갖는다. `ast-extract`의 node에 `file, line`이 있다(`.skills/wiki-ingest/SKILL.md:307`).

#### 6. Link
입장: link는 LLM이 건다. 해석·검증·그래프 계산은 결정적 코드가 한다.
- [확인] ingest는 새 페이지마다 기존 페이지 2~3개로 link를 걸라고 지시한다(`.skills/wiki-ingest/SKILL.md:408`). 역방향 link도 LLM이 판단한다(`:459-461`).
- [확인] `cross-linker` skill이 "언급됐지만 link 안 된" 곳을 찾는다. 찾기와 점수 매기기 모두 LLM이 grep으로 한다(`.skills/cross-linker/SKILL.md:24-95`).
- [확인] wikilink 해석은 `links.PageIndex`가 한다. 같은 stem이 여럿이면 디렉터리가 가까운 쪽을 고른다(`obsidian_wiki/links.py:55-154`).
- [확인] backlink는 저장하지 않는다. `graphrag.build_index`와 `lint_vault`가 매번 wikilink를 다시 읽어 in-link를 센다(`obsidian_wiki/graphrag.py:98`, `obsidian_wiki/lint.py:340-347`).
- [확인] `relationships:`는 7개 타입의 typed edge다. 대상 존재·모호성·자기참조를 lint가 검사한다(`obsidian_wiki/lint.py:454-510`).

#### 7. Lint
입장: 결정적 lint와 LLM lint가 명확히 나뉜다. 결정적 lint는 report-only다. 자동 수정은 LLM이 사람 확인 뒤에 한다. commit gate는 없다.
- 결정적 검사(`obsidian_wiki/lint.py:563-583`): [확인] broken link, 필수 frontmatter 누락, 제목·stem 중복, summary 누락, 기기 절대 경로 출처, snapshot 불일치, orphan, typed relationship 오류, 날짜 오류, 끊긴 `superseded_by`, trust ledger 검사.
- 판정: [확인] broken link·필수 frontmatter·trust metadata·날짜 오류만 `fail`이다. 나머지는 `warn`이다(`obsidian_wiki/lint.py:610-637`). `--strict-trust`나 `OBSIDIAN_TRUST_STRICT`를 켜면 trust 검사 일부도 `fail`이 된다(`obsidian_wiki/lint.py:600-616`, `obsidian_wiki/cli.py:1877-1881`). `fail`이면 exit 1이다. `--strict`를 주면 snapshot 불일치를 뺀 warn도 exit 1이 된다(`obsidian_wiki/cli.py:1900-1907`).
- LLM 검사: [확인] 모순, stale content, index 정합성, provenance drift, 태그 파편화, visibility 일관성, misc 승격 후보, synthesis 공백(`.skills/wiki-lint/SKILL.md:90-180`, `:392-408`).
- 자동 수정: [확인] `--consolidate`가 broken link 수정, orphan 연결, `draft→reviewed` 자동 승격(30일 경과·confidence>0.7), tier 강등, 태그 alias 정규화, 모순 callout 추가를 한다(`.skills/wiki-lint/SKILL.md:536-575`). 페이지 병합은 하지 않는다.
- [확인] 프롬프트는 "reviewed는 사람만"이라고 적는다(`.skills/llm-wiki/SKILL.md:466`). 같은 프로젝트의 consolidate는 `draft→reviewed`를 자동으로 한다(`.skills/wiki-lint/SKILL.md:555`). 두 규칙이 서로 어긋난다.
- [확인] stale 기준이 두 개다. 일반 규칙은 90일이다(`.skills/wiki-lint/SKILL.md:206`). consolidate의 verified 경고는 180일이다(`.skills/wiki-lint/SKILL.md:556`).
- [확인] `redirects_to:` 검증은 `wiki-dedup`이 lint의 일로 적어 두었다(`.skills/wiki-dedup/SKILL.md:280`). `obsidian_wiki/`에는 `redirect` 문자열이 없다. 즉 결정적 lint는 이것을 검사하지 않는다.
- commit gate: [확인] CI 워크플로는 저장소 코드의 pytest만 돈다(`.github/workflows/`). 사용자 vault에 대한 gate는 `lint` exit code를 사용자가 직접 CI에 묶어야 생긴다.

#### 8. stale·모순 처리
입장: 기본은 LLM 병합 + 모순 표시다. 시간 축은 `valid_from/valid_until/superseded_by`로 supersede를 지원한다. drift 감지는 날짜 기반 overlay다.
- [확인] 페이지 갱신 시 "merge, don't just append"와 "모순을 해소하고 못 하면 적어라"를 지시한다(`.skills/wiki-ingest/SKILL.md:411-416`). 판단은 LLM이 한다.
- [확인] 모순은 `^[ambiguous]` 표시, `relationships: contradicts`, consolidate의 callout으로 드러낸다. 해소는 하지 않는다(`.skills/wiki-lint/SKILL.md:570-575`).
- [확인] supersede는 코드가 읽는다. `valid_until`이 지난 페이지는 `graph-query`에서 빠진다. `--as-of`, `--include-historical`로 과거를 조회한다(`obsidian_wiki/temporal.py:1-14`, `.skills/wiki-query/SKILL.md:105-106`).
- [확인] stale은 저장 상태가 아니다. 질의 시 `today − updated > 90일`로 계산해 인용 옆에 경고를 붙인다(`.skills/wiki-query/SKILL.md:268-285`).
- [확인] 소스 쪽 drift는 hash 비교로 잡는다. 페이지 쪽 drift는 "소스 mtime이 페이지 `updated`보다 늦은가"를 LLM이 본다(`.skills/wiki-lint/SKILL.md:90-96`).
- [확인] trust ledger는 사람이 검토한 페이지의 fingerprint를 저장한다. 페이지가 바뀌면 `confidence_review_stale`로 잡힌다(`obsidian_wiki/trust.py:1-6`, `:219`, `:588`).

#### 9. 사람 개입
입장: 기본은 자율이다. 리뷰 큐는 opt-in이다. 파괴적 작업에는 확인 단계가 있다.
- [확인] `_staging/` 리뷰 큐는 `WIKI_STAGED_WRITES=true`일 때만 켜진다(`.skills/wiki-ingest/SKILL.md:17`).
- [확인] 큐 처리는 결정적이다. `staging promote`는 `os.replace` 한 번이다(`obsidian_wiki/staging.py:167-216`).
- [확인] revision 비교는 호출자가 `--expect-staged`·`--expect-live`·`--expect-new`를 넘길 때만 한다. 기대값이 없으면 검사를 건너뛴다(`obsidian_wiki/staging.py:150-158`). skill은 이 값을 넘기라고 지시하고, 어긋나면 exit 9로 거부된다(`.skills/wiki-stage-commit/SKILL.md:120-129`, `:149-151`). 즉 pin은 코드가 강제하지 않고 프롬프트가 지킨다.
- [확인] 기존 페이지 수정안은 `.patch.md`다. `promote`는 patch를 거부한다. 병합은 LLM이 손으로 한다(`obsidian_wiki/staging.py:190-195`, `.skills/wiki-stage-commit/SKILL.md:140-147`).
- [확인] 승인된 patch를 큐에서 치우는 방법은 `staging discard`다(`.skills/wiki-stage-commit/SKILL.md:147`). `discard`는 파일을 `_raw/rejected-patch-*.md`로 옮긴다(`obsidian_wiki/staging.py:219-248`). log에도 "rejected"로 집계된다(`obsidian_wiki/staging.py:263-271`).
- [추정] 승인된 patch가 다음 Raw 모드 ingest에서 다시 소스로 읽힌다 — 사례: Raw 모드는 `_raw/` 최상위 파일을 모두 소스로 본다고 적혀 있다(`.skills/wiki-ingest/SKILL.md:76`) 1건. 실행해 보지는 않았다.
- [확인] `wiki-dedup` 기본은 audit이다. `--merge`는 쌍마다 확인한다. `--auto`는 점수 0.90 이상이고 merge 판정이 난 쌍을 사람 확인 없이 병합한다(`.skills/wiki-dedup/SKILL.md:22-30`, `:183-185`). 점수는 제목 유사도 공식이지만 "You don't need exact arithmetic"라고 해 LLM 어림값이다(`:58-60`). merge 판정도 LLM이 두 페이지 전문을 읽고 내린다(`:91-104`). 둘 다 LLM 판단이다.
- [확인] lifecycle의 `reviewed`·`verified` 승격은 사람 몫으로 정의돼 있다(`.skills/llm-wiki/SKILL.md:459-473`). trust ledger 기록(`trust-record`)도 사람 승인 뒤에만 하라고 적는다(`.skills/wiki-lint/SKILL.md:286-289`).

#### 10. 동시성·안전
입장: 공유 상태 파일은 advisory lock + 원자적 교체로 지킨다. 페이지 본문 쓰기는 보호가 없다. undo는 git 스냅샷과 `_archives/`에 기댄다.
- [확인] lock은 `O_CREAT|O_EXCL` lockfile이다. 60초 넘은 lock은 훔친다(`obsidian_wiki/cache.py:95-148`). 주석이 "last-writer-wins steal" 경쟁을 스스로 인정한다(`:123-124`).
- [확인] manifest와 memory 파일은 임시 파일 + `os.replace`로 바꾼다(`obsidian_wiki/cache.py:168-182`, `obsidian_wiki/memory.py:131-144`).
- [확인] `memory sync`는 log·index·hot을 한 lock 안에서 쓴다. 그래서 세 파일이 서로 다른 시점을 가리키지 않는다(`docs/architecture.md:144`, `obsidian_wiki/memory.py:120-128`, `obsidian_wiki/cli.py:2536-2561`).
- [확인] 단, 도구가 쓰지 않은 기존 `index.md`·`hot.md`가 있는 vault(`memory migrate` 전)에서는 `memory sync`가 log 한 줄만 쓰고 index·hot은 건너뛴다. 실패가 아니라 stderr 경고만 낸다(`obsidian_wiki/cli.py:2553-2561`, `obsidian_wiki/memory.py:656-661`).
- [확인] manifest lock은 `cache-update`를 거칠 때만 걸린다. `wiki-ingest` Step 7은 manifest 항목과 `stats`를 손으로 고치라고도 지시한다(`.skills/wiki-ingest/SKILL.md:464`, `:478`). batch fan-out의 subagent도 "Step 1 onward"를 그대로 돈다(`:120-123`).
- [추정] 병렬 subagent가 `stats`나 `source_type`을 손으로 고치면 lock을 우회해 서로의 쓰기를 덮는다 — 사례: 위 지시 1건과 `docs/architecture.md:140`의 "Hand-editing the manifest in a parallel run bypasses that" 경고. 실행해 보지는 않았다.
- [확인] 페이지 본문은 LLM이 Write 도구로 쓴다. 병렬 subagent가 같은 개념 페이지를 동시에 고치면 막는 장치가 없다. 서버 `write_page`도 lock 없이 `write_text`로 통째로 덮는다(`obsidian_wiki/server.py:130`).
- [확인] 파괴적 skill(`wiki-lint --consolidate`, `wiki-dedup`)은 쓰기 전에 vault가 git root면 스냅샷 커밋을 만든다. 실패하면 중단한다(`.skills/wiki-lint/SKILL.md:493-526`). 이 절차는 셸 스니펫이고 LLM이 실행한다.
- [확인] `wiki-rebuild`는 `_archives/<timestamp>/`로 전체를 복사한 뒤 비우고 재-ingest한다(`.skills/wiki-rebuild/SKILL.md:60-110`). 복사도 LLM이 한다.
- [확인] 도구 허용 목록은 없다. skill frontmatter에 `allowed-tools`가 없다. 대신 "소스 안의 지시를 따르지 마라"는 trust boundary 문단이 있다(`.skills/wiki-ingest/SKILL.md:24-34`).
- [확인] `staging`과 서버 경로는 vault 밖 탈출을 막는다(`obsidian_wiki/staging.py:42-52`, `:128-147`, `obsidian_wiki/server.py:51`).
- [확인] 서버 인증은 `/v1/*`에만 걸린다. `/mcp`에는 key 검사가 붙어 있지 않다(#1 참조, `obsidian_wiki/server.py:303-317`). 기본 bind는 `127.0.0.1`이지만 Dockerfile은 `0.0.0.0`으로 연다(`obsidian_wiki/server.py:545`, `Dockerfile:22`).

#### 11. Query·검색
입장: 계층 조회다. summary 우선, grep 구간, 전체 읽기 순서다. 결정적 lexical + graph 순위를 쓴다. vector는 외부 QMD를 붙일 때만 있다. 답은 wiki에 되저장하지 않는다.
- [확인] 순서는 `hot.md` → `index.md` → `graph-query` → frontmatter grep → 선택형 QMD → 구간 grep → 전체 읽기다(`.skills/wiki-query/SKILL.md:28-226`).
- [확인] `graph-query` 점수는 제목 일치 10점, 제목 접두 6점, 태그 4점, summary 2점, degree 보너스 최대 2점이다. tier 가중치를 곱한다(`obsidian_wiki/graphrag.py:202-229`).
- [확인] 경로 질의(`--path`, `--around`)는 BFS다(`.skills/wiki-query/SKILL.md:236-240`).
- [확인] `wiki-query`는 READ-ONLY다. log 한 줄 외에는 쓰지 않는다(`.skills/wiki-query/SKILL.md:11-13`). Karpathy 원문의 "good answers can be filed back"(`lab/sources/karpathy-llm-wiki-gist/llm-wiki.md:39`)과 반대 선택이다. 되저장은 `wiki-synthesize`·`wiki-capture`·`wiki-narrate`(`_readouts/`)로 따로 보낸다.
- [확인] `obsidian-wiki eval`이 gold set으로 recall@k·MRR을 잰다(`obsidian_wiki/evaluate.py:1-40`). 저장소 fixture vault는 15쪽 남짓이다(`tests/fixtures/bench/vault/`).
- [확인] `wiki-context-pack`이 토큰 예산 안에서 결정적으로 문맥 묶음을 만든다(`obsidian_wiki/context_pack.py:362`).

#### 12. index·log 관리
입장: 결정적 재생성이다. LLM은 `hot.md`의 `## Key Takeaways` 한 칸만 쓴다.
- [확인] `rebuild_index`가 디스크의 페이지를 훑어 카테고리별 절을 다시 만든다. 카테고리가 아닌 손글씨 절은 보존한다(`obsidian_wiki/memory.py:636-733`).
- [확인] index 항목의 설명은 각 페이지의 `summary:`에서 온다. 없으면 본문 첫 부분에서 뽑는다(`obsidian_wiki/memory.py:434`).
- [확인] 처음 쓰는 vault에서는 `memory migrate`로 백업을 먼저 받게 한다. 도구가 쓰지 않은 `index.md`는 덮지 않는다(`obsidian_wiki/memory.py:656-661`).
- [확인] `log.md`는 `append_log`가 파싱 가능한 형식으로 한 줄씩 붙인다(`obsidian_wiki/memory.py:291-347`).
- [확인] `hot.md`는 500단어 상한을 코드로 강제한다(`obsidian_wiki/memory.py:66`, `:1051`).
- [확인] `wiki-ingest`는 staging 모드에서도 "index를 즉시 갱신"하라고 적는다(`.skills/wiki-ingest/SKILL.md:400`). 그러나 `scan_pages`는 `_staging/`을 건너뛴다(`obsidian_wiki/vault.py:19-22`). staged 페이지는 promote 뒤 `memory sync` 전까지 index에 없다. `wiki-stage-commit`은 "index.md is updated by the ingest that staged the page"라고 적는다(`.skills/wiki-stage-commit/SKILL.md:153`). 바로 아래 Step 4가 promote 뒤 `memory sync`를 부르게 해서 결과적으로 맞춘다(`:157-160`).

#### 13. 포맷 표준 (OKF)
입장: 네이티브 포맷은 OKF와 "구조적으로" 맞을 뿐이다. 진짜 OKF는 export 시 LLM 번역으로 만든다.
- [확인] 네이티브 frontmatter는 `title/category/tags/sources/created/updated`다. OKF는 `type/title/description/tags/generated/sources`다(`docs/architecture.md:198-200`). 필드 이름부터 다르다.
- [확인] 변환은 `wiki-export`·`wiki-import` skill 프롬프트가 한다. Python 변환 코드는 없다.
- [확인] `tests/test_okf_v02.py:1-10`은 에이전트가 한 번 만든 fixture 번들(5쪽)의 모양만 고정해 검사한다. "lossless round-trip" 주장(`docs/architecture.md:202`)의 근거는 이 한 번의 실행이다.

#### 14. 규모·비용
입장: 비용 절감 장치는 많다. 규모 주장은 측정 근거가 없다.
- [확인] 절감 장치: hash로 unchanged 건너뛰기, 코드 본문을 LLM에 안 보내기, 페이지 상한 15, tier별 갱신 생략, summary 우선 조회, `index_only` 즉답, hot cache 500단어(`.skills/wiki-ingest/SKILL.md:325`, `:357-371`).
- [확인] README는 "20 pages or 2000, roughly the same cost"라고 주장한다(`README.md:151`, `docs/architecture.md:190`). 저장소에 그 규모의 benchmark는 없다.
- [추정] 실제 query 비용은 페이지 수에 비례해 는다 — 사례: `wiki-query`가 매번 `index.md` 전체를 읽고(`.skills/wiki-query/SKILL.md:29`), `index.md`는 모든 페이지를 한 줄씩 나열한다(`obsidian_wiki/memory.py:564`). 큰 vault용 `index_folder_hubs` 축약 옵션이 있다(`obsidian_wiki/memory.py:503-541`).
- [확인] manifest 3,000항목 성능 개선 주석이 있다(`obsidian_wiki/cache.py:425-430`). ADR 0001은 10k key fixture를 언급한다. 운영 사례 숫자는 문서에 없다.
- [확인] ingest 1회의 토큰 비용은 어디에도 적혀 있지 않다.

#### 15. frosk1 비판 대응
| 비판 | 대응 | 강도 |
|---|---|---|
| 오류 누적 | `^[inferred]` 표시, hub 페이지의 inferred 20% 초과 경고(`.skills/wiki-lint/SKILL.md:129`), trust ledger의 사람 검토, `_archives/` rebuild | [추정] 약함 — 사례: 표시·비율 검사가 모두 LLM 몫이고 코드 검사가 0건이다 |
| 부분 문맥 | 갱신 전 index·grep으로 기존 페이지 찾기(`.skills/wiki-ingest/SKILL.md:358`), 선택형 QMD로 관련 소스 찾기(`:237-290`) | [확인] 소스를 하나씩 처리하는 구조는 그대로다(`:545`). 전체 재검토 절차는 rebuild뿐이다 |
| 요약 손실 | `_raw/_archived/` 원본 보존, `snapshots:`로 원본 link, 논문은 그림·수식·표를 살린 deep-dive 페이지 | [확인] 원본이 남으므로 복구 경로는 있다. 페이지 → 원문 구간 연결은 없다 |
| 가짜 source of truth | lifecycle `draft` 기본값, 질의 답에 stale·lifecycle 표시, `wiki-query`의 출처 단계 명시(`.skills/wiki-query/SKILL.md:263`) | [추정] 중간 — 사례: 답은 wiki 페이지만 인용하고 원문 재확인 단계가 없다(1건, `.skills/wiki-query/SKILL.md:259-292`) |
| 환각 병합 | dedup 확인 단계, `redirects_to` stub, 모순 callout만 달고 해소는 안 함 | [확인] `--auto` 병합은 사람 확인 없이 LLM 판단(어림 점수 + merge 판정)만으로 실행된다(`.skills/wiki-dedup/SKILL.md:58-60`, `:185`) |
| 운영 복잡도 | 상태 파일을 CLI로 일원화, `doctor`, 설치 스크립트 idempotency CI(`.github/workflows/` setup job), "equilibrium" 모드로 skill 간 충돌 감지(`docs/architecture.md:186`). [확인] oscillation 감지는 코드가 아니라 `wiki-status` 프롬프트 절차다(`.skills/wiki-status/SKILL.md:473-488`). `obsidian_wiki/`에 해당 문자열이 없다 | [추정] 복잡도는 오히려 크다 — 사례: skill 40개, 선택 frontmatter 14종, 상태 파일 11종 |
| ingest 비용 | hash skip, AST 무토큰 추출, 페이지 상한, tier 생략, 병렬 배치 | [확인] 측정치는 없다 |

#### 16. 성숙도·차용 가능성
- [확인] 테스트 15,518줄, 테스트 함수 1,115개다. CI가 Python 3.9와 3.12에서 pytest를 돈다(`.github/workflows/tests.yml:19`).
- [확인] CI는 `pytest`만 설치한다(`.github/workflows/tests.yml:29-30`). 서버 테스트는 fastapi·mcp가 없으면 skip되므로 CI에서 돌지 않는다(`tests/test_server.py:1`, `:12-13`).
- [확인] 테스트 중 상당수는 문서 계약 테스트다. 예: `test_pre_write_snapshot_docs.py`, `test_writing_profile_contract.py`, `test_skill_mirrors.py`. skill 문서끼리 어긋나지 않게 묶는다.
- [확인] 코어 의존성은 0개다(`pyproject.toml:34`). 선택 extra는 tree-sitter, leidenalg/igraph, fastapi/uvicorn/mcp다(`pyproject.toml:38-46`).
- [확인] 라이선스는 MIT다. 코드와 프롬프트 모두 차용할 수 있다.
- [확인] ADR 3개가 결정 근거를 남긴다(`docs/adr/`). 코드 주석에 issue 번호(#28, #132, #146, #238)가 붙어 있다.
- [확인] shallow clone이라 커밋 수는 세지 못했다. 저장소 생성은 2026-04-06이고 PR 번호는 #279까지 보인다.

## 장점

- 결정적 일과 판단을 가르는 선이 선명하다. [확인] `staging.py` docstring이 "Judgment stays with the skill … Promotion never rewrites a page"라고 경계를 스스로 정의한다(`obsidian_wiki/staging.py:9-12`).
- 여러 writer가 공유하는 파일을 정확히 짚어 보호한다. [확인] CLI 경로로 쓸 때 manifest와 index·log·hot은 lock + 원자적 교체를 거친다(`obsidian_wiki/cache.py:151-182`, `obsidian_wiki/memory.py:120-144`). 다만 manifest는 skill이 손 편집도 허용한다(#10 참조).
- index를 LLM이 손으로 고치지 않는다. [확인] `memory sync`가 불릴 때마다 디스크 상태에서 재생성하므로 그 시점의 index는 실제 페이지와 맞는다(`obsidian_wiki/memory.py:636`). 서버 `write_page` 뒤, `memory migrate` 전의 vault, CLI가 없는 환경에서는 갱신되지 않는다(#10, #1 참조).
- 증분 판정이 hash 기반이고 key가 이식 가능하다. [확인] 기기 간 sync에서도 같은 소스로 인식된다(`obsidian_wiki/cache.py:489-523`).
- 리뷰 큐 promote가 낙관적 동시성 검사를 지원한다. [확인] 호출자가 검토 시점 revision을 넘기면 그 뒤 파일이 바뀐 경우 거부한다(`obsidian_wiki/staging.py:150-164`). revision을 넘기지 않으면 검사하지 않는다.
- 원본 스냅샷과 페이지를 잇는 `snapshots:`가 결정적으로 검증된다. [확인] ADR로 설계 근거가 남아 있다(`docs/adr/0001-ledger-invert-for-page-sources.md`).
- 시간 축 모델(`valid_from/valid_until/superseded_by`)을 질의가 실제로 읽는다. [확인] 과거 주장을 지우지 않고 historical로 남긴다(`obsidian_wiki/temporal.py:1-14`).
- CLI가 없어도 일부 단계는 동작한다. [확인] cache-check, batch-plan, graph-query, lint에는 grep·sha256sum fallback이 적혀 있다(`.skills/wiki-ingest/SKILL.md:61`, `:128`, `.skills/wiki-query/SKILL.md:113`, `.skills/wiki-lint/SKILL.md:28`). index·log·hot 갱신은 fallback이 없다(#1 참조).
- 코드 소스는 AST로 먼저 구조를 뽑아 토큰을 아낀다. [확인] `.skills/wiki-ingest/SKILL.md:295-327`.

## 단점

- 쓰기 시점 gate가 없다. [확인] 필수 frontmatter, staging 모드, lifecycle 규칙은 모두 사후 lint나 프롬프트로만 지켜진다(#2 참조). 사후 lint도 LLM의 `draft→reviewed` 승격은 잡지 못한다(`obsidian_wiki/trust.py:40-43`).
- 서버 MCP 경로에 인증이 없다. [확인] `/mcp` mount에 key 검사가 없다. 문서는 Bearer token이 필요하다고 적는다(#1 참조). [추정] key 없이 `memory_write`로 페이지를 쓸 수 있다 — 사례: `obsidian_wiki/server.py:303-317` 1건. 실행해 보지는 않았다.
- provenance 표시가 검증되지 않는다. [확인] `^[inferred]` 비율 계산 코드가 없다. 표시가 없으면 "extracted"로 간주되므로 LLM이 표시를 빼먹으면 추론이 사실로 둔갑한다(`.skills/llm-wiki/SKILL.md:316`).
- 문서와 코드가 어긋난 곳이 여럿이다. [확인] "No scripts"(`AGENTS.md:3`) 대 15k줄 CLI, redirect 처리 미구현(`.skills/wiki-dedup/SKILL.md:248`, `:280`), stale 90일 대 180일, "reviewed는 사람만" 대 consolidate 자동 승격, `last_updated` writer 부재, `/mcp` 인증 문서 대 코드, `pages_produced` 대 `pages_created/pages_updated`.
- 승인된 patch가 "rejected"로 기록되고 `_raw/`로 간다. [확인] `.skills/wiki-stage-commit/SKILL.md:147`, `obsidian_wiki/staging.py:219-271`.
- 페이지 본문 쓰기에는 동시성 보호가 없다. [확인] 병렬 subagent ingest가 같은 페이지를 고치는 경우를 막지 않는다(#10 참조).
- 수정된 문서 소스를 다시 넣을 때 옛 claim을 걷어 내는 절차가 없다. [확인] `.skills/wiki-ingest/SKILL.md:50`, `:411-416`. 코드 프로젝트(`wiki-update`)에는 사라진 관계를 지우는 단계가 있다(`.skills/wiki-update/SKILL.md:93`).
- manifest lock은 관례다. [확인] `wiki-ingest`가 manifest 손 편집(`stats`, 참고 필드)을 지시하고 `cache-update`는 병렬 실행에서만 요구한다(`.skills/wiki-ingest/SKILL.md:464-480`).
- 표면적이 너무 넓다. [추정] 사용자가 schema 전체를 머리에 담기 어렵다 — 사례: 선택 frontmatter 14종, skill 40개, 환경 변수가 `.env.example`에 11KB다.
- 규모·비용 주장에 측정이 없다. [확인] "20 or 2000 same cost" 주장에 benchmark가 없다(#14 참조).

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것
- index·log·hot을 디스크 상태에서 결정적으로 재생성하는 `memory sync` 패턴. LLM에게는 "Key Takeaways" 한 칸만 준다(`obsidian_wiki/memory.py:636`, `:1110`).
- 공유 상태 파일 전용 advisory lock + 임시 파일 `os.replace` 쓰기(`obsidian_wiki/cache.py:95-182`). stdlib만으로 Windows까지 된다.
- 이식 가능한 소스 key 규약(vault 상대, `~` 상대, `repo:`/`url:`/`agent:`)(`obsidian_wiki/cache.py:489-523`).
- `cache-check`의 5분류(new/modified/unchanged/missing/unavailable). 특히 "다른 기기에만 있는 소스"를 missing과 구분하는 unavailable(`.skills/wiki-ingest/SKILL.md:47-53`).
- 리뷰 큐 promote의 revision pin + rename-only 이동(`obsidian_wiki/staging.py:167-216`). patch 병합만 LLM에게 남기는 경계. 단, pin은 선택 인자가 아니라 필수 인자로 만든다.
- 원본을 `_raw/_archived/`에 남기고 페이지에 `snapshots:`로 거는 방식. 요약 손실을 복구할 길이 생긴다.
- `valid_from/valid_until/superseded_by` 시간 축과 `--as-of` 질의(`obsidian_wiki/temporal.py`).
- lint 판정을 fail/warn 두 단계로 나누고 exit code로 CI에 묶을 수 있게 한 것(`obsidian_wiki/lint.py:610-637`).
- 코드 소스는 AST 추출로 대체해 LLM에 본문을 안 보내는 것.
- skill 문서 간 계약을 pytest로 묶는 "docs test" 방식(`tests/test_*_docs.py`).

### 피할 것
- 규칙을 프롬프트에만 두고 쓰기 경로에 gate를 두지 않는 것. staging 같은 안전 모드는 write 경로 코드가 강제해야 한다.
- "표시 없음 = 사실" 기본값. 출처 미표시 문장이 검증 없이 extracted가 된다. 내 wiki는 claim마다 출처 연결을 요구하거나, 최소한 결정적 비율 검사를 둔다.
- 사람 확인 없이 LLM 판단(어림 점수 + merge 판정)만으로 실행되는 자동 병합(`wiki-dedup --auto`).
- 문서와 다르게 인증이 빠진 부가 endpoint(`/mcp`). 인증은 mount 단위로 걸고 테스트로 묶는다.
- 같은 규칙(stale 일수, lifecycle 전이)을 여러 skill 문서에 따로 적는 것. 상수는 코드 한 곳에 두고 skill은 CLI 출력을 읽게 한다.
- skill 40개로 쪼갠 넓은 표면. 핵심 3연산(ingest/query/lint)과 보조 몇 개로 줄인다.
- 측정 없는 규모 주장.

## 확인하지 못한 것

- 실제 ingest 1회의 토큰 비용과 시간. 코드를 실행하지 않았고 저장소에 측정치가 없다. 작은 vault에 `wiki-ingest`를 돌려 transcript를 재면 알 수 있다.
- 병렬 subagent ingest에서 같은 페이지 충돌이 실제로 얼마나 나는지. 배치 fan-out을 재현해 보면 알 수 있다.
- 승인된 patch가 `_raw/rejected-patch-*.md`로 간 뒤 Raw 모드 ingest가 그것을 다시 집는지. `wiki-ingest`와 그 references에 `rejected`라는 문자열이 없다. 즉 거르는 문구는 없다. `wiki-ingest` Raw 모드를 그 상태에서 돌려 보면 알 수 있다.
- `scripts/daily-update.sh`가 list 형태 manifest(`sources`가 배열)에서 어떻게 실패하는지. `.items()`를 부르므로 예외가 날 것으로 보이지만 실행하지 않았다. 이 분기는 아무 코드도 쓰지 않는 `last_updated`가 있을 때만 닿는다.
- `/mcp`가 실제로 key 없이 응답하는지. 코드에는 인증이 없지만 서버를 띄워 보지 않았다. `WIKI_API_KEY`를 주고 서버를 띄운 뒤 Authorization 헤더 없이 `/mcp`에 `tools/list`를 보내면 알 수 있다.
- 커밋 이력 길이와 기여자 수. shallow clone이라 `git log`가 1건이다. `gh api repos/Ar9av/obsidian-wiki/contributors`로 확인할 수 있다.

## 검증 기록

- #한눈에: `memory sync` 호출 수 22 → 21로 고쳤다. setup이 hook을 `~/.claude/settings.json`에 기본 등록한다는 사실을 더했다.
- #1: "모든 skill이 fallback을 적어 둔다"를 고쳤다. index·log·hot 갱신에는 fallback이 없고 손 편집을 금지한다.
- #1·#10: `/mcp` mount에 key 검사가 없다는 사실(문서와 어긋남, 테스트 없음)을 더했다. 실제 응답은 확인하지 못한 것으로 옮겼다.
- #2: 구조 규칙 상수가 vault config로 바뀔 수 있다는 점, 서버 `write_page`가 필수 frontmatter를 코드로 채운다는 점을 더했다.
- #2: lifecycle 사후 검사가 "위반을 보고한다"를 고쳤다. 코드는 draft 복귀와 archived 탈출만 잡고 LLM의 `draft→reviewed` 승격은 잡지 못한다. `trust-record --approved`가 자기 선언이라는 점을 더했다.
- #3: manifest key가 이식 가능한 형태"만 허용"한다를 고쳤다. 해당 없으면 경고 뒤 절대 경로를 저장한다.
- #3·#10: `wiki-ingest` Step 7이 manifest 손 편집(`stats`, 참고 필드)을 지시하고 `cache-update`는 병렬 실행에만 요구한다는 점을 더했다.
- #3: `pages_produced`와 `pages_created/pages_updated` 문서 간 불일치를 더했다.
- #4: "hash가 없을 때만 mtime으로 떨어진다"를 고쳤다. 코드에는 mtime 판정이 없고 hash 없는 항목은 modified가 된다. mtime은 CLI 없을 때의 손 fallback뿐이다.
- #4·단점: "옛 claim 걷어 내는 절차 없음"을 문서 소스로 좁혔다. 코드 프로젝트는 `wiki-update`가 사라진 관계를 지우게 한다.
- #7: `--strict-trust`·`--strict`가 fail/exit 판정을 바꾼다는 점을 더했다.
- #9·장점: promote의 revision 비교가 호출자가 값을 넘길 때만 동작한다는 점을 밝혔다.
- #9·#15·피할 것: `--auto` 병합을 "LLM 점수만"에서 "LLM 어림 점수 + LLM merge 판정, 사람 확인 없음"으로 고쳤다.
- #10: 미이관 vault에서 `memory sync`가 index·hot을 경고만 내고 건너뛴다는 점을 더했다.
- #12: `wiki-stage-commit:153`의 "index는 ingest가 갱신" 문구와 실제 동작의 어긋남을 더했다.
- #15: hub inferred 20% 인용 줄을 128 → 129로 고쳤다. equilibrium oscillation 감지가 프롬프트라는 점을 확인해 확인하지 못한 것에서 뺐다.
- #16: CI Python 버전을 3.9·3.12로 밝혔다. CI가 extra를 설치하지 않아 서버 테스트가 skip된다는 점을 더했다.
- 장점: "index와 실제 페이지가 어긋날 수 없다"를 `memory sync`가 불린 시점으로 좁혔다. "CLI 없어도 동작"을 일부 단계로 좁혔다.
- 확인하지 못한 것: MCP tool 목록·인증 범위 항목을 뺐다(tool 8개, `/mcp` 인증 없음을 읽었다). `rejected-` 필터 문구가 없다는 점을 확인해 적었다.

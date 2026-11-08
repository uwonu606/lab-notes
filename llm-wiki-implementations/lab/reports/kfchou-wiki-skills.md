# kfchou/wiki-skills — 판단은 LLM skill이 하고, 판단의 흔적은 stdlib 스크립트와 git hook이 검사한다

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/kfchou/wiki-skills |
| clone commit | `d9267ec` (shallow clone, 2026-07-03 "allow uers to specify markdown or obsidian link styles on init (#3)") |
| 별 / 최근 push / 라이선스 | 188★ / 2026-07-03 / MIT (`gh api repos/kfchou/wiki-skills`, 2026-10-11 조회) |
| 커밋·fork·이슈 | 커밋 11개, fork 29, open issue 2 (`gh api .../commits`) |
| 형태 | Claude Code plugin. SKILL.md 7개와 stdlib Python 스크립트 4개, shell pre-commit hook 1개 |
| 코드 규모 | Python 스크립트 614줄, 테스트 676줄, skill·설정 문서 1,754줄, 설계 문서(`docs/superpowers/`) 1,959줄 |
| 의존성 | `uv`(필수라고 README가 밝힘), Python 3 표준 라이브러리, git(선택), `codex`/`gemini` CLI(선택) |

- [확인] 이 repo는 wiki 자체가 아니라 wiki를 만드는 도구다. `wiki-init`이 스크립트를 사용자의 wiki 디렉터리 `bin/`으로 복사한다 (`skills/wiki-init/SKILL.md:353-367`).
- [확인] 스크립트는 `skills/wiki-init/assets/bin/` 아래 4개다. 이름은 `generate-index.py`, `render-log.py`, `check-contradictions.py`, `lint-mechanical.py`이다.
- [확인] 설계 문서가 출처를 밝힌다. 개선 roadmap은 "200+ faithful llm-wiki implementations and Google's OKF spec"에서 관찰한 것을 되먹였다고 적는다 (`docs/superpowers/plans/2026-06-21-wiki-skills-improvement-roadmap.md:4`).

## 한 바퀴 흐름

아래 경로는 사용자 wiki 기준이다. `bin/*.py`는 repo의 `skills/wiki-init/assets/bin/*.py`가 복사된 것이다.

1. **init** — `wiki-init` skill이 질문 5개를 하나씩 묻는다 (`skills/wiki-init/SKILL.md:16-30`). 디렉터리를 만든다. `SCHEMA.md`를 쓴다. 스크립트 4개와 hook을 복사한다. git repo면 `git config core.hooksPath bin/hooks`를 건다 (`skills/wiki-init/SKILL.md:391-411`).
2. **ingest 1 — 읽기와 상의** — `wiki-ingest`가 `SCHEMA.md`를 위로 찾아 올라간다. 소스를 `raw/`에 복사한다. 핵심 3-5개를 보여 주고 "Anything specific you want me to emphasize" 를 묻는다. 답을 기다린다 (`skills/wiki-ingest/SKILL.md:20-40`).
3. **ingest 2 — 쓰기** — LLM이 source 요약 페이지를 쓴다 (`:47-83`). 모든 사실 주장에 footnote를 단다. text 소스면 `L142-143` 같은 줄 범위를 붙인다 (`:85-126`). 자기 점검 3단계를 한다 (`:128-146`). entity·concept 페이지를 만들거나 고친다 (`:148-179`). 기존 페이지 전체에 backlink audit을 한다 (`:181-195`).
4. **ingest 3 — 모순 gate** — LLM이 건드린 페이지와 이번에 읽은 이웃 페이지만 비교한다. blocking 모순이면 frontmatter에 `contradiction-check: failed — ...` 한 줄을 쓰고 멈춘다 (`:197-237`).
5. **ingest 4 — index·commit** — `python bin/generate-index.py`가 frontmatter에서 `wiki/index.md`를 다시 만든다 (`:239-251`, 스크립트 `generate-index.py:86-131`). LLM이 `overview.md`를 고친다. commit 메시지를 제안하고 사용자 확인 뒤 commit한다. 메시지에는 `Wiki-Op: ingest` trailer가 붙는다 (`:262-282`).
6. **commit gate** — git이 `bin/hooks/pre-commit`을 부른다. hook은 `uv run check-contradictions.py`와 `uv run lint-mechanical.py --staged`를 차례로 돌린다 (`skills/wiki-init/assets/bin/hooks/pre-commit:7-8`). 둘 다 페이지 내용은 staged blob에서 읽는다 (`check-contradictions.py:29-36,67`, `lint-mechanical.py:230-237,267`). 다만 링크와 slug 충돌을 판정할 slug 집합은 working tree의 파일 목록이다 (`lint-mechanical.py:240-244,262`). 검사 대상은 추가·복사·수정(`--diff-filter=ACM`) 파일뿐이라 삭제는 보지 않는다.
7. **query** — `wiki-query`가 index를 다시 만들고 전부 읽는다. 관련 페이지를 읽는다. 링크를 한 단계만 따라간다. 답한 뒤 "Worth saving as ..." 를 묻는다. 저장하면 `category: Analyses` 페이지와 `Wiki-Op: query` commit이 생긴다 (`skills/wiki-query/SKILL.md:18-75`).
8. **lint** — `wiki-lint` Phase 1이 `python bin/lint-mechanical.py`의 JSON을 받는다 (`skills/wiki-lint/SKILL.md:42-66`). Phase 2가 tag cluster마다 subagent를 띄워 모순·누락 링크·병합 후보를 찾는다 (`:68-94`). Phase 3가 `wiki/pages/lint-<date>.md` 보고서를 허락 없이 쓴다 (`:96-104`). 고침은 diff를 보여 주고 확인 뒤 적용한다 (`:176-185`).
9. **log 보기** — `python bin/render-log.py`가 `git log --name-status`에서 `Wiki-Op:` trailer가 있는 commit만 골라 날짜별 log를 stdout에 낸다 (`render-log.py:28-79`).

## 축별 분석

#### 1. 실행 형태

**skill + 결정적 스크립트.**
- [확인] 플러그인 manifest는 이름·버전·설명만 가진다 (`.claude-plugin/plugin.json:1-13`). MCP 서버, CLI 엔진, 앱은 없다.
- [확인] LLM 작업은 SKILL.md 7개가 지시한다. 결정적 작업은 Python 스크립트 4개가 한다.
- [확인] 결정적 쪽이 맡는 일은 네 가지다. index 생성 (`generate-index.py`), log 렌더링 (`render-log.py`), 모순 flag 검사 (`check-contradictions.py`), 구조 lint (`lint-mechanical.py`)이다.
- [확인] LLM 쪽이 맡는 일은 요약, 링크 쓰기, backlink audit, 모순 판정, 인용 검증(일부 제외), merge/split의 의미 판단이다.
- [확인] 스크립트는 skill이 Bash로 부른다. skill 안 명령은 `python bin/...` 이다 (`skills/wiki-ingest/SKILL.md:246`). hook만 `uv run`을 쓴다 (`hooks/pre-commit:7-8`).

#### 2. 규칙의 위치

**대부분 프롬프트. 코드 강제는 commit 시점의 hook 하나뿐이다.**
- [확인] 규칙의 본문은 wiki마다 생기는 `SCHEMA.md`에 산다. 그 template은 `skills/wiki-init/SKILL.md:84-351`에 있다. frontmatter 필드, slug 규칙, 인용 형식, 모순 처리, commit 규약이 모두 여기 있다.
- [확인] 코드가 강제하는 것은 commit 순간의 두 gate다. 하나는 `contradiction-check: failed` flag의 존재를 막는다 (`check-contradictions.py:39-55`). 다른 하나는 필수 frontmatter 7개 누락, 깨진 링크, slug 충돌을 막는다 (`lint-mechanical.py:23,257-287`).
- [확인] 파일 쓰기 경로에는 gate가 없다. LLM은 working tree에 무엇이든 쓸 수 있다. 막히는 것은 commit뿐이다.
- [확인] hook은 `--no-verify`로 우회된다 (`skills/wiki-init/SKILL.md:286`). `core.hooksPath`는 clone에 따라오지 않는다 (`:284-285`).
- [확인] non-git wiki에는 코드 강제가 하나도 없다. 두 스크립트는 git 밖에서 exit 0으로 끝난다 (`check-contradictions.py:59-62`, `lint-mechanical.py:258-261`).
- [확인] hook과 스크립트는 wiki root가 곧 git top-level이라고 가정한다. hook은 `$(git rev-parse --show-toplevel)/bin/...`을 부른다 (`hooks/pre-commit:6-8`). 스크립트는 staged 경로가 `wiki/pages/`로 시작하는지 본다 (`check-contradictions.py:34`, `lint-mechanical.py:235`). 그런데 init은 "a wiki root nested in an existing git repo"를 명시적으로 받아들인다 (`skills/wiki-init/SKILL.md:66-68`). README도 "initialize a wiki inside a git repo"라고 적는다 (`README.md:44`).
- [추정] 기존 repo 안 하위 디렉터리에 wiki를 두면 gate가 소리 없이 꺼진다. 근거는 위 세 코드 경로다. 상대 경로 `core.hooksPath bin/hooks`는 top-level 기준으로 풀려 hook을 못 찾는다. 찾더라도 staged 경로가 `sub/wiki/pages/...`라 검사 대상이 0개다. `render-log.py`도 같은 접두사 검사라 페이지 목록이 빈다 (`render-log.py:62`). 또 `core.hooksPath`는 repo 전체 설정이라 그 repo의 기존 `.git/hooks`를 대체한다. 실행해 보지는 않았다.
- [확인] 모순 gate가 검사하는 것은 LLM이 스스로 쓴 flag다. LLM이 모순을 못 보면 flag도 없다. 그러면 gate는 통과한다. 즉 코드는 "판정의 기록"을 강제하고, 판정 자체는 강제하지 않는다.
- [확인] SKILL.md frontmatter에 `allowed-tools`가 없다 (`grep allowed-tools skills` 결과 0건).

#### 3. 저장 구조

**`raw/` + 평평한 `wiki/pages/` + 파생 index. manifest·ledger는 없다.**
- [확인] 디렉터리는 `SCHEMA.md`, `config/link-style.md`, `bin/`, `raw/`, `wiki/{index.md, log.md, overview.md, pages/}`, `assets/`이다 (`skills/wiki-init/SKILL.md:34-53`).
- [확인] `wiki/pages/`는 하위 디렉터리를 금지한다 (`:55`). 하위 디렉터리 허용은 roadmap P7에 미구현으로 남아 있다 (`docs/superpowers/plans/2026-06-21-wiki-skills-improvement-roadmap.md:21,163-183`).
- [확인] 페이지 종류는 `category` 값으로 나뉜다. 연구 기본값은 `Sources | Entities | Concepts | Analyses`이다. 코드베이스 기본값은 `Modules | APIs | Decisions | Flows`이다 (`skills/wiki-init/SKILL.md:22-25`, `skills/wiki-init/codebase.md:9-16`). lint 보고서는 `Maintenance`이다 (`skills/wiki-lint/SKILL.md:109`).
- [확인] 필수 frontmatter는 `title, category, summary, tags, sources, created, updated` 7개다 (`skills/wiki-init/SKILL.md:96-105`, `lint-mechanical.py:23`).
- [확인] 선택 frontmatter는 두 가지다. `review:` 블록은 `wiki-audit strong`만 쓴다 (`skills/wiki-init/SKILL.md:218-238`). `contradiction-check:`는 해결 전까지만 존재한다 (`:254-262`).
- [확인] 파생 파일은 `wiki/index.md` 하나다. gitignore되고 매번 다시 만든다 (`:73-80`). audit 보고서 `audit-*.md`도 gitignore된다.
- [확인] source 상태를 기록하는 manifest·hash·ledger 파일은 없다. 어떤 raw 파일이 이미 ingest됐는지는 source 페이지의 `**Source:**` 줄로만 알 수 있다 (`skills/wiki-ingest/SKILL.md:64`).

#### 4. Ingest

**한 번에 소스 하나, 사람과 대화하며. 증분 추적·queue·감시·변환은 없다.**
- 사람 참여: [확인] 쓰기 전에 사용자 답을 기다린다 (`skills/wiki-ingest/SKILL.md:31-40`). 모순이 나오면 해결안 4개를 내고 멈춘다 (`:222-232`). commit은 확인 뒤에만 한다 (`:271`).
- 증분·변경 추적: [확인] 없다. raw 파일의 hash나 처리 여부를 기록하는 코드가 없다. 같은 소스를 두 번 넣는 것을 막는 장치도 찾지 못했다.
- queue·crash 복구: [확인] 없다. 중간에 끊기면 working tree에 반쯤 쓴 페이지가 남는다. git이면 `git status`/`git checkout`으로 사람이 되돌린다. 이를 안내하는 문구는 찾지 못했다.
- 자동 감시: [확인] 없다. 사용자가 skill을 부를 때만 돈다.
- 멀티포맷: [확인] 파일 경로, URL, 붙여 넣은 텍스트를 받는다 (`:22-25`). URL은 `browse` skill로 받으라고 적는다 (`:24`). 이 plugin에는 `browse` skill이 없다. PDF 변환 코드는 없다. PDF는 LLM이 직접 읽고 줄 범위 없이 인용한다 (`:118-120`).
- 건드리는 페이지 수: [확인] skill 설명이 "One ingest may touch 10-15 wiki pages" 라고 적는다 (`skills/wiki-ingest/SKILL.md:3`). 이 수치는 Karpathy gist의 문장을 그대로 옮긴 것이다 (`lab/sources/karpathy-llm-wiki-gist/llm-wiki.md:37`). 측정 근거는 없다.

#### 5. 근거 추적 단위

**footnote 단위, text 소스는 줄 범위 + 원문 문자열 일치.**
- [확인] 인용은 Markdown footnote다. 종류는 verbatim quote와 `[synthesis]` 두 가지다 (`skills/wiki-init/SKILL.md:142-216`).
- [확인] markdown·plaintext·code·cached HTML 소스는 `L<start>-<end>` 줄 범위가 필수다. 줄 번호는 불변인 `raw/` 파일 기준이다 (`:189-207`). PDF·transcript·live URL은 면제다.
- [확인] 검증은 `wiki-audit`이 한다. 줄 범위가 있는 quote footnote는 subagent 없이 그 줄만 읽고 공백을 정규화해 문자열 비교한다 (`skills/wiki-audit/SKILL.md:80-91`). 줄 범위가 있는 synthesis는 그 줄 조각만 subagent에 준다 (`:88-91`).
- [확인] 이 문자열 비교는 스크립트가 아니다. skill 지시문이 LLM에게 `sed -n`으로 읽고 비교하라고 시킨다 (`:84-87`). 결정적 실행을 보장하는 코드는 repo에 없다.
- [확인] 페이지 단위 출처도 frontmatter `sources: [slug]`로 남는다. claim ledger는 없다.
- [확인] 인용 누락 탐지(Phase A)는 subagent 판단이다 (`:53-62`).

#### 6. Link

**LLM이 링크를 쓰고, 스크립트가 해석·검증한다. backlink는 LLM이 쓴다.**
- [확인] 링크 형식은 init에서 고른다. obsidian은 `[[slug]]`, markdown은 `[[slug](pages/slug.md)]`이다 (`skills/wiki-init/config/link-style-obsidian.md:7`, `link-style-markdown.md:7`).
- [확인] 링크 쓰기는 LLM 몫이다. "Links are verified, never invented" 규칙을 프롬프트로 건다. 쓰기 전에 `ls wiki/pages/`로 확인하라고 한다 (`skills/wiki-init/SKILL.md:124-128`).
- [확인] backlink는 ingest 7단계에서 LLM이 전체 페이지를 훑어 추가한다 (`skills/wiki-ingest/SKILL.md:181-195`). 결정적 backlink 생성 코드는 없다.
- [확인] 링크 그래프 계산은 스크립트가 한다. `LINK_RE`가 두 형식을 다 읽는다 (`lint-mechanical.py:28,74-81`). 깨진 링크, orphan, 3회 이상 참조된 없는 페이지를 계산한다 (`:120-178`).
- [확인] roadmap P3는 원래 "make cross-link creation mechanical"을 후보로 적었다 (`roadmap.md:73-77`). 구현된 것은 프롬프트 규칙 + 검증 스크립트 + `wiki-merge`이다 (`roadmap.md:17`).
- [확인] `wiki-merge`만 link style을 읽지 않는다. 다른 skill 6개는 Pre-condition에서 `link_style:`을 읽는데, merge에는 그 문단이 없다 (`grep link_style skills/wiki-merge/SKILL.md` 0건). merge는 `[[<loser-slug>]]` 문자열만 grep해서 고치고, 마지막 확인도 같은 문자열로 한다 (`skills/wiki-merge/SKILL.md:59-60,75-76`). [추정] markdown style wiki의 `[[loser](pages/loser.md)]`나 `[[loser|별칭]]`은 grep에 걸리지 않는다. 그러면 "zero matches"로 통과한 뒤 링크가 깨진 채 남는다. 고치지 않은 페이지는 staged가 아니고 삭제는 gate가 보지 않으므로 commit도 막히지 않는다. 근거는 이 grep 지시 1개와 #7의 staged gate 범위다.
- [확인] 개념 정체성은 slug 자체다. 별도 id는 없다 (`skills/wiki-init/SKILL.md:118-121`). 동음이의어는 `mercury-planet`처럼 수식어를 붙인다 (`:130-137`).
- [확인] markdown 형식 문서는 `wiki/pages/a.md`에서 `pages/b.md`가 "the directory is the same" 이라서 풀린다고 적는다 (`link-style-markdown.md:17`). [추정] 표준 상대 경로 규칙으로는 `wiki/pages/pages/b.md`를 가리킨다. 그러면 GitHub 미리보기에서 페이지 사이 링크가 깨진다. 근거는 이 문장 1개와 상대 URL 해석 규칙이다. 렌더링해 보지는 않았다.

#### 7. Lint

**결정적 6종은 스크립트, 본문 의미 5종은 tag-cluster subagent. 자동 수정 없음. commit gate는 구조 3종만.**
- 결정적 (full mode, `lint-mechanical.py:207-219`): [확인] missing frontmatter, broken links, orphans, slug collision, stale date, missing concept 6종이다.
- [확인] stale date는 `updated`가 90일 넘고 본문에 `current/latest/recent/state-of-the-art`나 2년 넘은 연도가 있을 때다 (`:29-31,151-167`).
- LLM (Phase 2, `skills/wiki-lint/SKILL.md:68-94`): [확인] `contradiction`, `missing-xref`, `merge-candidate`, `chronological-section`, `addable-line-range` 5종이다.
- [확인] cluster는 스크립트가 결정적으로 만든다. 같은 tag를 가진 페이지 2개 이상이 한 cluster다. 부분집합 cluster는 버린다. 25개를 넘으면 알파벳 순으로 자른다 (`lint-mechanical.py:32,181-204`).
- [확인] tag를 다른 페이지와 공유하지 않는 페이지는 본문 검사를 받지 않는다. skill이 이 recall 한계를 스스로 밝힌다 (`skills/wiki-lint/SKILL.md:92-94`).
- [확인] skill template들이 주제와 무관한 고정 tag를 넣는다. entity·concept 페이지는 `tags: [entity | concept]` (`skills/wiki-ingest/SKILL.md:160`), 저장한 query는 `tags: [query, analysis]` (`skills/wiki-query/SKILL.md:52`), lint 보고서는 `tags: [lint, maintenance]` (`skills/wiki-lint/SKILL.md:111`)이다. [추정] 그러면 entity 페이지 전체가 한 cluster가 되고 25개 단위로 알파벳 순 분할된다. 주제가 같은 페이지끼리 비교한다는 cluster의 전제가 약해진다. 근거는 이 template 3개와 `build_clusters`의 분할 규칙이다 (`lint-mechanical.py:194-203`).
- [확인] main thread는 페이지 본문을 읽지 않는다. 본문은 스크립트나 subagent 안에만 있다 (`:21-34`).
- 자동 수정: [확인] 없다. 고침마다 diff를 보이고 확인 뒤 적용한다 (`:185`). slug 충돌과 병합 후보는 `wiki-merge`로 넘긴다 (`:181`).
- commit gate: [확인] `--staged` 모드는 missing frontmatter, broken link, slug collision 3종만 본다 (`lint-mechanical.py:257-287`). orphan·stale·missing concept은 전역 계산이라 뺐다 (`docs/superpowers/specs/2026-06-21-wiki-lint-subagent-scoping-design.md:60-67`).
- commit gate의 범위: [확인] 링크 해석에 쓰는 slug 집합은 staged 상태가 아니라 working tree의 파일 목록이다 (`lint-mechanical.py:240-244`). 검사 대상은 `--diff-filter=ACM`이라 삭제된 페이지는 보지 않는다 (`:232`). staged 페이지의 바깥으로 나가는 링크만 보고, 다른 페이지가 들어오는 링크는 보지 않는다. [추정] 새 페이지 `b`를 디스크에 두고 stage하지 않은 채 `[[b]]`를 가진 `a`만 commit하면 통과한다. 페이지를 지우거나 이름을 바꿔 남은 링크가 깨져도 통과한다. 근거는 이 세 줄이다. 테스트는 이 경우를 다루지 않는다 (`tests/test_lint_mechanical.py:163-232`).
- 결함 후보 1: [확인] lint 보고서 template은 `sources: []`를 쓴다 (`skills/wiki-lint/SKILL.md:112`). 스크립트는 빈 리스트를 누락으로 센다 (`lint-mechanical.py:64-66,108`). 보고서는 깨진 링크를 `[[missing-slug]]` 형태로 그대로 적는다 (`skills/wiki-lint/SKILL.md:127`). [추정] 그래서 lint 보고서를 commit하면 staged gate가 막는다. 코드를 읽어 따라간 결과다. 실행하지는 않았다.
- 결함 후보 2: [확인] lint 보고서는 `wiki/pages/`에 쌓이고 lint 대상에서 빠지지 않는다. 제외는 `audit-*`뿐이다 (`lint-mechanical.py:84-85`). 보고서는 orphan 페이지마다 링크를 건다 (`skills/wiki-lint/SKILL.md:133-135`). [추정] 다음 lint에서 그 페이지들은 inbound 링크가 생겨 orphan이 아니게 된다. 근거는 이 두 코드 경로 1쌍이다. 같은 이유로 보고서가 적은 `[[missing-slug]]`는 다음 full lint에서 보고서 자신의 broken link로 잡힌다. "Missing Concept Pages" 절이 적는 `[[slug]]`는 참조 횟수를 하나씩 늘린다 (`skills/wiki-lint/SKILL.md:154`, `lint-mechanical.py:170-178`).
- 결함 후보 3: [확인] staged 모드의 slug 충돌은 수식된 slug의 첫 토큰이 기존 페이지면 막는다 (`lint-mechanical.py:253-254`). [추정] `attention` 개념 페이지가 있으면 `attention-is-all-you-need` source 페이지 commit이 막힌다. 근거는 이 줄 1개다. 테스트는 `mercury`/`mercury-element` 경우만 다룬다 (`tests/test_lint_mechanical.py:74-83,179-188`). SCHEMA template은 이 경우를 lint가 "warns" 한다고 적는다 (`skills/wiki-init/SKILL.md:136-137`). 실제 staged gate는 commit을 막는다.
- 결함 후보 4: [확인] stale marker는 부분 문자열로 찾는다 (`lint-mechanical.py:163`). [추정] `concurrent`, `currently`도 `current`로 걸린다.

#### 8. stale·모순 처리

**제자리 덮어쓰기 + ingest 시점 모순 gate + 주기적 cluster lint. supersede·drift 감지는 없다.**
- [확인] 페이지는 "living documents"이다. 날짜별 update 섹션을 붙이지 말고 제자리에서 고치라고 한다. 이력은 git log가 맡는다 (`skills/wiki-ingest/SKILL.md:286`, `skills/wiki-update/SKILL.md:92`).
- [확인] ingest 모순은 blocking과 soft로 나눈다. blocking은 transient flag를 쓰고 멈춘다. soft는 요약에만 말하고 어디에도 남기지 않는다 (`skills/wiki-ingest/SKILL.md:212-237`).
- [확인] flag는 해결하면 지운다. committed 페이지는 늘 깨끗하다. 모순의 이력은 페이지에 남지 않는다 (`skills/wiki-init/SKILL.md:254-262`). 처음 설계(P8)는 `severity`/`Status: Unresolved` 토큰을 남기려 했다. 구현에서 버렸다 (`roadmap.md:187-200,22`).
- [확인] `wiki-update`는 바뀐 주장을 전체 페이지에서 찾아 모두 고치라고 한다 (`skills/wiki-update/SKILL.md:51-53`). 링크로 이어진 페이지의 영향도 확인시킨다 (`:43-49`).
- [확인] 원문이 바뀌었는지 감지하는 drift 기능은 없다. `raw/`는 불변이라는 전제가 있다 (`skills/wiki-init/SKILL.md:339`).
- [확인] supersede 관계나 `status` 필드는 없다. lint가 orphan에 `status: orphan`을 붙일지 묻는 제안만 있다 (`skills/wiki-lint/SKILL.md:182`).

#### 9. 사람 개입

**ingest는 plan 상의 + commit 승인, update·merge는 페이지마다 승인, 보고서는 자율.**
- [확인] ingest는 쓰기 전 강조점을 묻는다. 페이지마다 승인받지는 않는다. commit은 확인 뒤다 (`skills/wiki-ingest/SKILL.md:38-40,271`).
- [확인] update는 페이지마다 Current/Proposed/Reason/Source를 보이고 확인받는다. 일괄 적용을 금지한다 (`skills/wiki-update/SKILL.md:26-41`).
- [확인] merge는 survivor 선택, 합친 페이지, 링크 수정 목록을 단계마다 확인받는다 (`skills/wiki-merge/SKILL.md:36-65`). split은 링크 하나하나의 의미 판단을 보여 준다 (`:127-135`).
- [확인] lint·audit 보고서는 허락 없이 쓴다 (`skills/wiki-lint/SKILL.md:101`, `skills/wiki-audit/SKILL.md:165`). `review:` frontmatter도 자동으로 찍는다 (`skills/wiki-audit/SKILL.md:152`).
- [확인] 모든 skill이 "never auto-commit" 이다 (`skills/wiki-init/SKILL.md:291-293`). 리뷰 큐나 공동 편집 기능은 없다.

#### 10. 동시성·안전

**git이 유일한 안전망이다. transaction·lock·snapshot 코드는 없다.**
- [확인] 원자적 쓰기, lock, transaction 코드는 없다. 스크립트는 `index.md` 하나를 `write_text`로 통째로 쓴다 (`generate-index.py:130`).
- [확인] undo는 git이다. 작업 하나가 commit 하나다. `Wiki-Op:` trailer로 작업 종류를 표시한다 (`skills/wiki-init/SKILL.md:311-318`).
- [확인] index를 gitignore한 이유 중 하나가 merge conflict 제거다 (`roadmap.md:94-96`, README.md:108).
- [확인] hook은 staged blob을 읽는다. working tree와 index가 다를 때 commit될 내용만 본다 (`check-contradictions.py:67`, 테스트 `tests/test_check_contradictions.py:85-92`).
- [확인] 도구 허용 목록은 없다 (2번 축 참고). 외부 CLI `codex exec`, `gemini -p`를 Bash로 부른다 (`skills/wiki-audit/SKILL.md:143-146`).
- [확인] 병렬 실행은 subagent 읽기 전용 작업에만 쓴다 (lint cluster, audit source). 병렬 쓰기는 없다.

#### 11. Query·검색

**index.md 전체 읽기 → 페이지 읽기 → 링크 1단계. vector·grep 검색 없음. 답은 물어보고 되저장.**
- [확인] query는 index를 다시 만들고 "scan the full index" 한다 (`skills/wiki-query/SKILL.md:18-23`). 링크는 한 단계만 따라간다 (`:27`).
- [확인] 검색 엔진, embedding, BM25는 없다. 큰 wiki용 계층 index(P5)는 roadmap에만 있다 (`roadmap.md:19,117-136`). 그 문서가 flat index는 "a few hundred pages" 에서 깨진다고 적는다.
- [확인] 답한 뒤 늘 저장을 제안한다. 저장하면 `Analyses` 페이지가 되고 index에 오른다 (`skills/wiki-query/SKILL.md:44-62`).
- [확인] "답을 기억으로 하지 말라"는 프롬프트 규칙이 있다 (`:79`). 이를 검증하는 장치는 없다.

#### 12. index·log 관리

**index는 결정적 재생성, log는 git log 대체. non-git만 LLM이 log.md를 쓴다.**
- [확인] index는 `generate-index.py`가 frontmatter의 `category`, `summary`, `created`로 만든다 (`generate-index.py:86-131`). 카테고리 순서는 `SCHEMA.md`의 Index Categories를 따른다 (`:66-83,108-113`). 카테고리 안은 `created` 최신순, 같으면 title 순이다 (`:121-122`).
- [확인] index는 gitignore된 runtime 산출물이다. skill은 읽기 전과 페이지를 바꾼 뒤마다 다시 만들라고 한다 (`skills/wiki-init/SKILL.md:323-333`). 이 "매번 다시 만들기"는 프롬프트 지시다.
- [확인] log는 git history다. `render-log.py`가 `Wiki-Op:` trailer가 있는 commit만 골라 날짜별로 묶는다. 바뀐 페이지는 commit diff에서 읽는다 (`render-log.py:34-75`). 파일로 저장하지 않고 stdout으로 낸다.
- [확인] trailer 없는 수동 commit은 log에서 빠진다 (`render-log.py:53-54`, `tests/test_render_log.py:68-75`).
- [확인] query를 저장하지 않으면 git wiki에서는 아무 기록도 남지 않는다 (`skills/wiki-query/SKILL.md:69-70`). roadmap이 이 손실을 열린 질문으로 적었다 (`roadmap.md:158-159`).

#### 13. 포맷 표준 (OKF)

**OKF를 영감으로 언급할 뿐, 준수하지 않는다.**
- [확인] OKF 언급은 roadmap 2곳뿐이다 (`roadmap.md:4,148`). skill과 스크립트에는 OKF 언급이 없다.
- [확인] OKF가 유일하게 요구하는 `type` 필드가 없다 (OKF `okf/SPEC.md:165,187`). 비슷한 역할은 `category`가 한다.
- [확인] OKF `sources`는 `resource`를 가진 객체 목록이다 (`okf/SPEC.md:287-310`). 여기 `sources`는 slug 문자열 목록이다.
- [확인] OKF는 표준 markdown 링크를 쓴다 (`okf/SPEC.md:439-457`). 여기 obsidian 형식 `[[slug]]`는 표준 링크가 아니다.
- [확인] OKF는 `index.md`, `log.md`를 예약 파일명으로 둔다 (`okf/SPEC.md:134-145`). 여기 index는 `###` 그룹 + 항목 목록이라 OKF §8 모양과 가깝다. render-log 출력은 `## YYYY-MM-DD` 최신순이라 OKF §9 모양과 가깝다.
- [확인] OKF의 `generated`/`verified`/`status`/`stale_after`에 해당하는 필드는 없다. `review:` 블록이 `verified`와 가장 가깝다.

#### 14. 규모·비용

**운영 규모 수치는 없다. 비용 절감은 설계로 주장하고 측정은 없다.**
- [확인] README와 skill 어디에도 실제 운영한 페이지 수, 소스 수, token 비용이 없다.
- [확인] 규모 관련 수치는 설계 문서의 추정뿐이다. flat index는 "a few hundred pages" 에서 깨진다 (`roadmap.md:119-120`). P5 계층 index의 token 예산은 L0 ~200, L1 ~1-2K, L2 ~2-5K이다 (`roadmap.md:122-125`). 구현되지 않았다.
- [확인] 컨텍스트 절약 장치는 세 가지다. lint 본문을 subagent로 격리한다 (`skills/wiki-lint/SKILL.md:21-34`). audit은 줄 범위만 읽는다 (`skills/wiki-audit/SKILL.md:80-91`). audit은 소스 파일당 subagent 하나로 PDF를 한 번만 읽는다 (`:99,112`).
- [확인] ingest 비용을 줄이는 장치는 없다. 소스 전체를 읽으라고 한다 (`skills/wiki-ingest/SKILL.md:27-29`). backlink audit은 "Scan ALL existing pages" 이다 (`:183`). [추정] 페이지 수에 비례해 ingest 비용이 커진다. 근거는 이 지시 1개다.
- [확인] 규모 대응을 내건 "feat: support scaling (#6)"은 마지막에서 두 번째 commit이다. 마지막은 link style commit(#3)이다. `gh pr view 6`으로 보면 이 PR은 +4,094/−117줄이다. 스크립트 4개, hook, 테스트, 설계 문서, `wiki-merge`가 모두 이 PR로 들어왔다. 그런데도 P5(계층 index)와 P7(하위 디렉터리)은 들어 있지 않다.

#### 15. frosk1 비판 7가지에 대한 대응

| 비판 | 대응 | 근거 |
|---|---|---|
| 오류 누적 | 부분 대응. ingest가 인용을 강제하고 자기 점검을 한다. `wiki-audit`이 페이지 하나를 원문과 대조한다. 다른 provider 모델의 교차 검토도 있다. 다만 audit은 사람이 부를 때만, 한 번에 한 페이지만 돈다. | `skills/wiki-ingest/SKILL.md:85-146`, `skills/wiki-audit/SKILL.md:41,114-161` |
| 부분 문맥 | 부분 대응, 한계를 인정한다. ingest 모순 검사는 일부러 이웃 페이지만 본다. 먼 페이지는 lint에 맡긴다. lint도 tag cluster 안만 본다. | `skills/wiki-ingest/SKILL.md:204-210`, `skills/wiki-lint/SKILL.md:92-94` |
| 요약 손실 | 부분 대응. `raw/`를 불변으로 남긴다. 인용이 원문 줄 범위를 가리킨다. 그래서 손실된 세부를 원문에서 되찾을 길이 있다. query는 원문이 아니라 wiki 페이지만 읽는다. | `skills/wiki-init/SKILL.md:200-202,339`, `skills/wiki-query/SKILL.md:18-27` |
| 가짜 source of truth | 대응 약함. query skill은 wiki를 "the source of truth here" 라고 부른다. 원문으로 내려가는 단계는 query에 없다. | `skills/wiki-query/SKILL.md:21-23` |
| 환각 병합 | 부분 대응. 링크는 존재하는 slug만 쓰라고 하고, commit 때 깨진 링크를 막는다. 개념 병합은 사람 확인을 거치는 `wiki-merge`로만 한다. 내용상 "매끄럽게 덮기"는 audit Phase C의 overreach 검사가 겨냥한다. | `skills/wiki-init/SKILL.md:124-128`, `lint-mechanical.py:257-287`, `skills/wiki-merge/SKILL.md:176-177`, `skills/wiki-audit/SKILL.md:135-138` |
| 운영 복잡도 | 대응. 의존성이 stdlib + uv + git뿐이다. DB·서버가 없다. 버전 관리와 rollback은 git에 맡긴다. 대신 `core.hooksPath`를 clone마다 다시 걸어야 한다. | `README.md:25-40`, `skills/wiki-init/SKILL.md:284-285` |
| ingest 비용 | 대응 없음. 비용 수치도, 증분 처리도 없다. 사람과 상의하며 하나씩 넣는 방식이 비용 상한 역할을 할 뿐이다. | `skills/wiki-ingest/SKILL.md:27-40,183` |

- [추정] 이 repo의 대응은 "검증 가능하게 만든다"에 집중한다. 줄 범위 인용, staged gate, audit이 모두 그 방향이다. 근거는 roadmap 상태표에서 ✅인 7개(P1, P2, P3, P4, P6, P8, P9) 중 P1, P2, P3, P8, P9 5개가 검증 관련이라는 점이다 (`roadmap.md:13-24`). P1·P2는 표에 "spec + implementation plan written"으로만 적혀 있지만 skill에는 들어가 있다.

#### 16. 성숙도·차용 가능성

**작고 읽기 쉽다. 스크립트는 테스트가 있다. MIT라 코드 차용이 가능하다.**
- [확인] 테스트는 `tests/`에 unittest 4개 파일, 676줄이다. 스크립트 4개를 각각 다룬다 (`tests/README.md:20-35`). 테스트는 실제 배포 파일을 임시 wiki에 복사해서 돌린다 (`tests/_harness.py:15-22`). 다만 shell hook `bin/hooks/pre-commit` 자체를 거치는 테스트는 없다. 테스트는 스크립트를 직접 부른다 (`tests/test_lint_mechanical.py:159-161`).
- [확인] skill의 LLM 동작은 테스트하지 않는다. 설계 문서가 이를 명시한다 (`docs/superpowers/specs/2026-06-21-wiki-lint-subagent-scoping-design.md:187-190`).
- [확인] CI 설정 파일(`.github/workflows`)은 없다.
- [확인] 코드 규모는 Python 614줄이다. 외부 import는 없다 (`json, re, subprocess, sys, datetime, pathlib`만).
- [확인] 라이선스는 MIT다 (`LICENSE`, `.claude-plugin/plugin.json:10`).
- [확인] 커밋은 11개다. 마지막 커밋 2개가 2026-07-03이다 ("feat: support scaling (#6)"와 link style 커밋). 그 뒤 push가 없다.
- [확인] 설계 문서의 P1-P10 작업은 "feat: support scaling (#6)" 한 PR로 들어왔다. `gh pr view 6 --json files`가 스크립트·테스트·설계 문서·skill 7개 수정을 모두 나열한다 (2026-10-11 조회).
- [확인] 문서 사이에 어긋남이 있다. SCHEMA template의 Conventions 줄은 hook이 `check-contradictions.py`만 돈다고 적는다 (`skills/wiki-init/SKILL.md:347`). 실제 hook은 두 gate를 돈다. P9 설계 문서는 스크립트를 SKILL.md fenced block에서 추출한다고 적는다 (`docs/superpowers/specs/2026-06-21-p9-pre-commit-gate-design.md:18-21`). 지금은 독립 파일이다. README는 스크립트가 `uv run`으로 돈다고 적는다 (`README.md:29-30`). skill들은 `python bin/...`을 부른다 (`skills/wiki-ingest/SKILL.md:246`).

## 장점

- **결정적 일과 판단할 일의 경계가 선명하다.** [확인] index·log·구조 lint·flag 검사는 스크립트다. 요약·모순 판정·병합 판단은 skill이다. skill은 "Do not re-derive these by reading pages yourself — the script is the source of truth" 라고 못 박는다 (`skills/wiki-lint/SKILL.md:66`).
- **index를 파생물로 만들어 drift와 merge conflict를 없앴다.** [확인] frontmatter가 원본이고 index는 gitignore된 재생성물이다 (`generate-index.py:86-131`, `skills/wiki-init/SKILL.md:73-80`).
- **log를 git으로 대체했다.** [확인] `Wiki-Op:` trailer 하나로 작업 종류를 표시한다. 바뀐 페이지는 diff에서 뽑는다 (`render-log.py:48-65`). 끝없이 자라는 `log.md`가 없다.
- **commit gate가 staged blob을 읽는다.** [확인] working tree가 아니라 commit될 내용을 검사한다. 이를 테스트가 확인한다 (`tests/test_lint_mechanical.py:214-220`). 다만 링크 해석용 slug 집합은 working tree에서 읽는다 (#7 commit gate의 범위).
- **줄 범위 인용으로 검증을 싸게 만들었다.** [확인] quote 인용은 해당 줄만 읽고 문자열 비교한다 (`skills/wiki-audit/SKILL.md:80-87`).
- **lint가 main context를 지킨다.** [확인] 본문은 스크립트나 subagent 안에만 들어간다. recall 한계도 보고서에 적게 한다 (`skills/wiki-lint/SKILL.md:21-34,123-124`).
- **설계 기록이 남아 있다.** [확인] 각 개선마다 결정과 버린 대안이 문서로 있다. 예를 들어 P10의 전제가 P8 구현으로 무너진 과정이 적혀 있다 (`roadmap.md:240-268`).
- **작고 의존성이 없다.** [확인] stdlib Python 614줄이다. MIT다.

## 단점

- **gate가 판단을 강제하지 못한다.** [확인] 모순 gate는 LLM이 쓴 flag만 본다 (`check-contradictions.py:39-55`). skill이 flag가 있으면 commit하지 말라고 이미 지시한다. [추정] 그래서 hook이 실제로 막는 경우는 LLM이 flag를 쓰고도 지시를 어긴 경우뿐이다. 근거는 설계 문서의 "On a healthy repo it never fires" 1개다 (`docs/superpowers/specs/2026-06-21-p9-pre-commit-gate-design.md:13`, `roadmap.md:224`).
- **gate가 우회되기 쉽다.** [확인] `--no-verify`, fresh clone의 `core.hooksPath` 누락, non-git wiki에서 모두 꺼진다 (`skills/wiki-init/SKILL.md:284-286`).
- **자기 산출물과 충돌할 수 있다.** [추정] lint 보고서는 빈 `sources`와 깨진 링크 목록 때문에 staged gate에 막힌다. 근거는 #7의 결함 후보 1이다. 실행 확인은 안 했다.
- **slug 충돌 규칙이 넓다.** [추정] 첫 토큰이 같은 기존 페이지가 있으면 정상 slug도 막는다. 근거는 `lint-mechanical.py:253-254` 1개다.
- **ingest에 증분·중복·복구 장치가 없다.** [확인] source manifest나 hash가 없다. 같은 소스 재ingest를 막는 코드가 없다.
- **query가 원문으로 내려가지 않는다.** [확인] wiki 페이지만 읽는다 (`skills/wiki-query/SKILL.md:18-27`). frosk1의 "derived artifact" 경고를 정면으로 받지 않는다.
- **규모 대책이 미구현이다.** [확인] 계층 index(P5)와 하위 디렉터리(P7)는 roadmap에만 있다 (`roadmap.md:19,21`). query는 index 전체를 읽는다.
- **모순 이력이 사라진다.** [확인] flag는 해결 후 지운다. soft tension은 어디에도 남지 않는다 (`skills/wiki-init/SKILL.md:254-264`). 다시 볼 근거가 commit 메시지에만 남는다.
- **URL ingest가 외부 skill에 기댄다.** [확인] `browse` skill을 부르라고 하지만 plugin에 없다 (`skills/wiki-ingest/SKILL.md:24`).
- **기존 repo 안에 둔 wiki에서는 gate가 꺼질 수 있다.** [추정] hook과 스크립트가 wiki root를 git top-level로 가정한다. init은 중첩 wiki를 허용한다. 근거는 #2의 코드 경로 3개다. 실행 확인은 안 했다.
- **commit gate의 링크 검사가 새는 곳이 있다.** [추정] slug 집합을 working tree에서 읽고 삭제·들어오는 링크를 보지 않는다. stage하지 않은 페이지로 가는 링크, 지운 페이지로 남은 링크가 통과한다. 근거는 `lint-mechanical.py:232,240-244` 2곳이다.
- **merge가 markdown link style을 모른다.** [확인] `wiki-merge`만 `link_style`을 읽지 않고 `[[<loser-slug>]]`만 grep한다 (`skills/wiki-merge/SKILL.md:59-60,75-76`). [추정] markdown style wiki에서 merge 뒤 깨진 링크가 남고 gate도 막지 않는다.
- **OKF와 맞지 않는다.** [확인] `type`이 없다. `sources`가 slug 문자열이다. obsidian 링크는 표준 링크가 아니다.

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

- **index를 frontmatter에서 재생성하고 gitignore한다.** 문제: LLM이 index를 손으로 고치면 drift와 merge conflict가 생긴다. 제안: `generate-index.py`(135줄)의 방식을 그대로 쓴다. 근거: 스크립트가 짧고 테스트가 있다 (`tests/test_generate_index.py`). 포기하는 것: GitHub에서 index를 바로 볼 수 없다.
- **git commit trailer를 log로 쓴다.** 제안: `Wiki-Op:` 같은 trailer 하나만 규약으로 정하고 `render-log.py` 방식으로 렌더한다. 포기하는 것: 저장하지 않은 query 같은 비-쓰기 작업은 기록되지 않는다.
- **pre-commit hook이 staged blob을 읽게 한다.** 제안: `git show :<path>`로 commit될 내용만 검사한다 (`check-contradictions.py:67`). 근거: working tree와 index가 다를 때도 정확하다.
- **lint를 "스크립트 JSON + cluster subagent"로 나눈다.** 제안: 스크립트가 cluster까지 결정적으로 만들어 넘긴다 (`lint-mechanical.py:181-204`). subagent는 본문을 보고 finding만 돌려준다. 포기하는 것: cluster 밖 모순은 놓친다. 그 한계를 보고서에 적는다.
- **줄 범위 인용 `§x L10-20 — "quote"`.** 제안: text 소스 인용에 줄 범위를 필수로 한다. 근거: quote 검증이 문자열 비교로 끝난다. 추가 제안: 이 비교를 skill 지시가 아니라 스크립트로 만든다. 이 repo는 그 부분을 LLM에 맡겼다.
- **transient flag + commit gate 패턴.** 제안: "LLM이 막혔다고 표시한 상태"를 frontmatter 한 줄로 두고 hook이 commit을 막는다. 조건: flag를 쓰는 판단 자체를 별도 검사로 보강해야 의미가 있다.
- **테스트 harness가 배포 파일 자체를 복사해 돌리는 방식.** 근거: 테스트와 배포물이 갈라질 틈이 없다 (`tests/_harness.py:15-22`). 단 hook shell 스크립트는 이 harness 밖이다.

### 피할 것

- **자기 산출물을 lint 대상 디렉터리에 넣기.** lint 보고서가 `wiki/pages/`에 들어가 gate와 orphan 계산을 오염시킨다. 보고서는 별도 디렉터리나 gitignore 대상으로 둔다.
- **첫 토큰 기반 slug 충돌 차단.** 오탐이 commit을 막는다. 경고로만 두거나, 명시적 동음이의어 목록으로 판정한다.
- **부분 문자열 stale marker.** 단어 경계 정규식을 쓴다.
- **query가 wiki만 source of truth로 삼기.** 원문 줄 범위 인용이 있으니, query 답에서 핵심 주장은 원문 줄까지 내려가 확인하게 한다.
- **모순 기록을 지우기만 하기.** 해결 결과는 commit 메시지에만 남는다. 내 wiki에서는 해결 이력을 남길 자리를 따로 둔다.
- **SCHEMA 규칙 문서와 실제 hook의 어긋남.** 규칙 본문은 한 곳에서만 정의하고 나머지는 참조한다.
- **gate가 working tree로 링크를 해석하기.** 내용은 staged blob에서 읽으면서 slug 집합은 디스크에서 읽으면 stage 누락이 통과한다. slug 집합도 `git ls-files -s`(index) 기준으로 만들고, 삭제·rename 때 들어오는 링크도 검사한다.
- **wiki root = git top-level 가정.** hook 경로와 staged 경로 접두사를 wiki root 기준으로 계산한다 (`git rev-parse --show-prefix` 등).
- **주제와 무관한 고정 tag를 cluster 기준으로 쓰기.** `entity`, `query` 같은 tag는 cluster 계산에서 뺀다.

## 확인하지 못한 것

- 스크립트와 테스트를 실행하지 않았다. 과제 조건이 repo 코드 실행을 금지한다. #7의 결함 후보 1-4는 코드를 읽고 따라간 결과다. 확인하려면 임시 디렉터리에 스크립트를 복사해 해당 fixture로 돌려 보면 된다.
- skill이 실제 Claude Code 세션에서 지시대로 도는지 보지 않았다. 특히 ingest 7b의 모순 판정 정확도, backlink audit 누락률, audit fast path가 정말 subagent 없이 도는지는 모른다. 실제 wiki에 소스 몇 개를 ingest하고 commit log와 페이지를 보면 알 수 있다.
- "feat: support scaling (#6)" PR은 파일 목록과 줄 수만 봤다 (`gh pr view 6 --json files`). 줄 단위 diff는 읽지 않았다.
- 중첩 wiki에서 hook이 꺼지는지, `git diff --cached --diff-filter=ACM`이 rename을 R로 빼는지 실행해 보지 않았다. 임시 repo 하위 디렉터리에 init 결과를 복사해 commit해 보면 알 수 있다.
- roadmap이 출처로 든 블로그 글 `2026-06-20-llm-wiki-google-okf.md`와 "200+ implementations" 조사를 읽지 않았다. repo 안에 없다.
- markdown link style의 `pages/<slug>.md` 상대 경로가 GitHub에서 실제로 깨지는지 렌더링해 보지 않았다.
- 실제 운영 규모·비용 자료는 repo에 없다. 이슈는 제목만 봤다 (open 2개: "Managing multiple wikis", "would hybrid raw anchors strengthen wiki-audit's Phase B?"). 본문과 fork 29개는 읽지 않았다.

## 검증 기록

- `tests/test_lint_mechanical.py:317-323`, `:282-291`을 `:214-220`, `:74-83,179-188`로 고쳤다. 파일은 287줄이다.
- `tests/test_render_log.py:296-303`을 `:68-75`로 고쳤다. 파일은 93줄이다.
- `tests/_harness.py:50-57`을 `:15-22`(install_script)로 고쳤다. 두 곳이다.
- `skills/wiki-update/SKILL.md:108-122`, `:124-130`, `:132-134`, `:173`을 `:26-41`, `:43-49`, `:51-53`, `:92`로 고쳤다. 파일은 93줄이다.
- P9 설계 문서 `:211`, `:217-219`를 `:13`, `:18-21`로 고쳤다. 파일은 83줄이다.
- "git commit 마지막 기록이 support scaling" 문장을 고쳤다. 실제로는 마지막에서 두 번째 commit이다.
- "roadmap 완료 항목 6개"를 "✅ 7개"로 고쳤다.
- `generate-index.py` 131줄을 135줄로 고쳤다.
- "둘 다 staged blob만 읽는다"를 좁혔다. 링크 해석용 slug 집합은 working tree에서 읽는다.
- PR #6 내용을 `gh pr view 6`으로 확인했다. P1-P10이 한 PR로 들어왔다는 문장을 [추정]에서 [확인]으로 올렸다.
- #2에 중첩 wiki에서 hook·스크립트 경로 가정이 깨지는 문제를 추가했다.
- #6에 `wiki-merge`가 link style을 읽지 않아 markdown 링크를 놓치는 문제를 추가했다.
- #7에 commit gate 범위(working tree slug 집합, 삭제·들어오는 링크 미검사)와 고정 tag가 cluster를 흐리는 문제를 추가했다.
- #7 결함 후보 2에 lint 보고서가 broken link·missing concept 계산도 오염시키는 경로를 추가했다.
- #7 결함 후보 3에 SCHEMA의 "warns"와 실제 차단의 어긋남을 추가했다.
- #16에 hook shell 스크립트 테스트가 없다는 점과 README `uv run` 대 skill `python` 어긋남을 추가했다.
- 단점·피할 것·확인하지 못한 것에 위 항목을 반영했다. 이슈 제목 2개를 적었다.

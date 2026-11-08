# AutoSci — 설계 이유 갈래 (autosci-why) 노트

- 레포: GitHub `skyllwt/AutoSci`, 로컬 `lab/repos/skyllwt_AutoSci`, HEAD `f5c2fe0` (2026-10-02), 라이선스 MIT.
- 이 노트의 경로 표기는 모두 레포 루트 기준이다. 다른 브랜치 파일은 `origin/paper:경로`처럼 적는다.
- "(a)"는 작성자가 밝힌 이유(원문 인용 + 출처), "[추정]"은 내가 추론한 이유다. 근거가 없으면 "모르는 것:"으로 적는다.
- 코드는 실행하지 않았다. `git log/show/diff`, `gh issue/pr view`, `gh api`(읽기), `grep/sed/cat`만 썼다. 논문 HTML은 스크래치패드에 내려받아 텍스트로 바꾼 뒤 읽었다.

## 0. 읽은 범위

| 대상 | 정도 |
|---|---|
| `git log` 전체 108 commits 메시지 본문 | 끝까지 읽음 |
| `CHANGELOG.md`, `README.md`, 최초 README(`20c61b9:README.md`), 최초 `CLAUDE.md`(`20c61b9:CLAUDE.md`) | 읽음 |
| `CLAUDE.md`, `CONTRIBUTING.md`, `.gitattributes`, `.github/PULL_REQUEST_TEMPLATE.md` | 읽음 |
| `runtime/` 전체(`CLAUDE.md`, `loader.py`, `schema/*.yaml`, `policy/writers.yaml`) | 끝까지 읽음 |
| `tools/research_wiki.py` | 쓰기 경로(`add_edge`), 투영, 대조 도구, BFS, compile-context, set-meta, worktree guard를 읽음. 나머지는 함수 목록만 훑음 |
| `tools/lint.py` | 머리 docstring, 함수 목록, content-quality 부분만 훑음 |
| `tools/serve.py` | docstring과 PATCH 처리부 읽음. 나머지 훑음 |
| `.claude/skills/ingest/**` | `SKILL.md`, `dedup-policy.md`, `cross-references.md`, `init-mode.md` 끝까지 읽음 |
| `.claude/skills/check/SKILL.md`, `.claude/skills/prefill/SKILL.md` | 끝까지 읽음 |
| `.claude/skills/init/**` | fan-in 부분만 훑음 (다른 갈래 영역) |
| `docs/**` (main은 3개 파일) | 목록만 확인. `docs/daily-arxiv-deployment.md`는 이 갈래와 무관해 훑지도 않음 |
| 브랜치 `origin/paper`, 태그 `arxiv-v1` | `git diff --stat`, schema·xref·writers diff, `docs/superpowers/plans/2026-05-29-autosci-schema.md`, `docs/scievolve.md` 머리, `tools/trust_guard.py`, paper판 `add_edge`·`graph_neighbors`, `dream/references/memory-operations.md` 머리 읽음. SciDAG·SciFlow 파이프라인 코드는 훑음 |
| 브랜치 `origin/dev-dcy-biology` | schema diff와 commit 2개(`5e5df95`, `372f7a5`) 메시지 읽음. 나머지 훑음 |
| 그 밖의 원격 브랜치(codex, opencode, hiera, scidag 등) | ahead/behind 수만 확인 |
| GitHub 이슈 #5 #11 #12 #20 #31 #34 #41 #42 #67 #81, PR #1 #3 #6 #8 #10 #18 #22 #23 #26 #30 #32 #33 #40 #63 #64 #73 #84 | 본문·댓글 읽음 |
| 선행 저장소 `DanJoshua/Research-Wiki-experimental`(`skyllwt/Research-Wiki`의 fork) | `README.md`, `future-features.md`, commit 목록 읽음 |
| 논문 arXiv 2605.31468v1 (HTML) | §1~§3, §4.2, §6, §7.2, §8, §9, 부록 B 일부 읽음. §7.3~7.5와 부록 C·D는 훑음 |

경계: ingest 단계별 세부(PDF 전처리, S2 보강, 논문↔논문 엣지 판단), `/init` 계획기·병렬 fan-in, `/check` lint 규칙 세부, 프론트엔드는 다른 갈래가 깊게 본다고 보고 경계만 적었다.

## 1. 구조

### 1.1 층과 파일 지도

```
사용자 ──/skill──▶ Claude Code (LLM)
                     │ reads .claude/skills/<skill>/SKILL.md (+ references/*.md)
                     │ reads runtime/schema/*.yaml, runtime/templates/*.tmpl (프롬프트 지시로)
                     ├─ 페이지 .md 파일은 LLM이 Write/Edit로 직접 씀 (wiki/<kind>/<slug>.md)
                     └─ Bash: python tools/research_wiki.py <cmd>   ← 공유 파일·그래프는 도구로만
                                    │ import runtime.loader  ← schema YAML 5개를 import 시점에 읽음
                                    ▼
                          wiki/graph/edges.jsonl, citations.jsonl, context_brief.md, open_questions.md
                          wiki/index.md, wiki/log.md
          python tools/lint.py (사후 감사) ── import runtime.loader
          python tools/serve.py (SPA API) ── subprocess로 research_wiki.py 호출
```

- 층 이름은 최초 README가 붙였다. "Layer 4: Skills — Orchestrators", "Layer 2: Tools — Executors", "Layer 3: OmegaWiki — Knowledge Hub" (`20c61b9:README.md:46-80`).
- 같은 분업이 지금 규칙 문서에도 있다. "Skills are **orchestrators** that use LLM reasoning and multi-step decisions." / "Skills call tools via `Bash: python3 tools/X.py` -- they do not contain deterministic logic themselves." (`CONTRIBUTING.md:26-27`), "Tools live in `tools/` and are **deterministic Python helpers** (no LLM reasoning)." (`CONTRIBUTING.md:34`).
- skill 원본은 `i18n/en/skills/`이고 `.claude/skills/`는 `setup.sh`가 복사한 사본이다(`CLAUDE.md:3` "Edit `i18n/en/CLAUDE.md`, not the active copy at root."). 두 사본이 어긋난 사례가 실제로 있었다(commit `5568c25`, 그리고 지금도 `.claude/skills/research/SKILL.md`와 `i18n/en/skills/research/SKILL.md`가 다르다 — `diff -r`로 확인).

### 1.2 schema 계약 (`runtime/`)

`runtime/loader.py`가 YAML 5개를 import 시점에 읽고 파생 상수를 만든다(`runtime/loader.py:37-41`, `:62-123`, `:194-198`). 소비자는 `tools/lint.py`, `tools/research_wiki.py`, `tools/serve.py`, `tools/visualize.py`, `tools/reset_wiki.py`다(commit `1b2df1f` 본문 "tools/lint.py and tools/research_wiki.py now import from runtime.loader", "refactor(tools): derive ENTITY_DIRS from runtime.loader").

| 파일 | 담는 것 | 런타임에서 읽히는가 |
|---|---|---|
| `runtime/schema/entities.yaml` | 페이지 종류 9개와 필드(`type`·`required`·`default`·`range`·`values`·`to`·`required_when`), `lifecycle.transitions`, `terminal` | 예 — lint, set-meta 외 도구, transition |
| `runtime/schema/edges.yaml` | 엣지 16종: `endpoints {from,to}`, `direction`, `workflow`, `attributes` | 예 — `add-edge`가 쓰기 전에 거부 |
| `runtime/schema/xref.yaml` | 정방향→역방향 규칙 14개, `terminal_targets: [foundations]` | 예 — lint 검사·`--fix` |
| `runtime/schema/conventions.yaml` | slug 정규식, 경로 패턴, log 문법, 소유 구역, 엣지 저장 위치 | 일부 |
| `runtime/policy/writers.yaml` | skill별 필드·엣지 쓰기 권한 | 아니오 — "STATUS: SPEC, NOT A RUNTIME GATE" (`runtime/policy/writers.yaml:3`) |
| `runtime/templates/<kind>.md.tmpl` | 본문 섹션 뼈대 | 아니오 — LLM이 프롬프트 지시로 읽음 (`.claude/skills/ingest/SKILL.md:18`) |

엣지 레코드 필드(`wiki/graph/edges.jsonl` 한 줄): `from`(`"<kind>/<slug>"`), `to`, `type`, `evidence`(자유 문자열), `date`(UTC 날짜), 선택 `confidence`(high|medium|low), 선택 `symmetric: true` (`tools/research_wiki.py:338-348`). 대칭 엣지는 끝점을 정렬해 한 번만 저장한다(`tools/research_wiki.py:255-263`). 같은 (from,to,type)이 이미 있으면 새 evidence를 버리고 `"exists"`를 돌려준다(`tools/research_wiki.py:316-336`).

투영 엣지(`graph/projected_edges.jsonl`): frontmatter의 `link`/`list_link`/`list_object` 필드를 `type: "fm_<kind>_<field>"`, `source: "frontmatter"`, `field: "<kind>.<field>"` 엣지로 바꾼 파생물이다(`tools/research_wiki.py:586-678`). terminal 종류(foundations)와 `papers.cited_by`는 건너뛴다(`:608-623`). 이 투영은 commit `d89cc72`("project frontmatter links into graph edges and expose them through the SPA graph")에서 들어왔다. main의 `neighbors` BFS는 투영 엣지를 보지 않고 `edges.jsonl`만 읽는다(`tools/research_wiki.py:1192`).

### 1.3 개념 대조 도구의 입출력

`find-similar-concept wiki/ "<title>" --aliases "a,b"` (`tools/research_wiki.py:1090-1118`)

- 입력: 후보 이름 1개 + 별칭 목록.
- 처리: `wiki/foundations/`와 `wiki/concepts/`의 각 페이지 `title`+`aliases`와 모든 쌍을 `_phrase_match_score`로 대조한다(`:1038-1087`). 점수 규칙은 앞선 보고서 #B 용어집 절과 같다(`:1007-1035`).
- 출력 JSON 배열 원소: `entity_type`(foundation|concept), `slug`, `title`, `aliases`, `key_papers`, `maturity`, `score`, `match_reason` (`:1077-1086`).
- 정렬: foundation 먼저, 그 안에서 점수 내림차순(`:1114-1117`).

## 2. 쓰기 경로에서 LLM과 코드가 나뉘는 지점

`/ingest` 한 번(근거: `.claude/skills/ingest/SKILL.md`)을 "누가 무엇을 검사하나"로만 다시 적는다. 단계 세부는 다른 갈래 몫이다.

| 단계 | 쓰는 주체 | 쓰기 전 검사 | 실패 시 |
|---|---|---|---|
| slug 생성 | 코드 `research_wiki.py slug` (`SKILL.md:107-111`) | 결정적 규칙(`tools/research_wiki.py:105-129`) | 같은 slug + 다른 논문이면 멈추고 보고 (`init-mode.md:45`) |
| 논문 페이지 frontmatter·본문 | LLM이 파일 직접 작성 (`SKILL.md:131-150`) | LLM의 자기 "shape check"뿐: 필수 키, enum, YAML 파싱 (`SKILL.md:141-148`) | 없음. 사후 `/check`가 찾음 |
| 개념 생성/병합 | LLM 판단, 대조 점수는 코드 (`dedup-policy.md:19-25`) | `find-similar-concept` 호출 의무 (`SKILL.md:161`) | 한도 초과분은 가까운 항목에 병합하거나 버림 (`dedup-policy.md:52`) |
| 방법 생성/병합 | LLM이 디렉터리를 훑어 판단 (`dedup-policy.md:27`) | 도구 없음 | 같음 |
| 역링크 | LLM이 같은 턴에 반대편에도 씀 (`cross-references.md:84-94`) | 없음 | 사후 `lint --fix`가 결정적으로 채움 (`check/SKILL.md:174`) |
| 그래프 엣지 | 코드 `add-edge` (`SKILL.md:66-68`) | 종류·끝점·자기연결·legacy·confidence·evidence 필수 → `sys.exit(1)` (`tools/research_wiki.py:279-307`) | LLM이 오류 JSON을 보고 고쳐 다시 부름 [추정] (재시도 지시는 SKILL에 없음, 사례 0) |
| 끝점 페이지 존재 | 코드 | 경고만 (`tools/research_wiki.py:309-314`) | 그대로 씀 |
| index·log | LLM append(index) / 코드(log) | 없음 | `.gitattributes` `merge=union` + 사후 `rebuild-index` |
| 사후 감사 | `/check` → `tools/lint.py` | 필수 필드, enum, required_when, 링크 대상 종류, xref 대칭, 그래프 일관성 (`tools/lint.py:4-14`) | `--fix`는 결정적인 것만 고침. 나머지는 보고서로 사람 승인 (`check/SKILL.md:173-174`) |

LLM 호출 지점은 Claude Code 세션 자체다. 별도 프롬프트 파일은 skill 문서(`SKILL.md`와 `references/*.md`)다. ingest 경로 안에서 다른 LLM을 부르는 곳은 없다. `/check` Step 6의 근사 중복 판정은 같은 세션 LLM이 한다(`check/SKILL.md:133-140`). 이슈 #41 답글은 그 LLM 판정이 "not yet implemented in the automated linter -- they remain aspirational"이라고 적는다(https://github.com/skyllwt/AutoSci/issues/41, collaborator Morrow-Yang).

## 3. 이력: OmegaWiki에서 AutoSci까지

| 날짜 | commit / PR | 일 |
|---|---|---|
| 2026-04-07 | `skyllwt/Research-Wiki` 5b8ed04 | 선행 저장소. "spec-first 项目工作区"(설계 먼저 하는 작업 공간)로 시작 (`skyllwt/Research-Wiki@22a4e87:CLAUDE.md`) |
| 2026-04-09 | `20c61b9` | "Initial release: OmegaWiki v0.1.0". skill 20개, 페이지 8종(claims 포함), 엣지 9종(`extends`, `supports` 등 끝점 무관 일반 이름), schema는 `CLAUDE.md` 391줄 안의 프롬프트 + 도구 안의 하드코딩 상수 (`20c61b9:CLAUDE.md`, `20c61b9:tools/research_wiki.py:62-73`) |
| 04-10 | PR #1 `070d5e1` | `/init` 병렬 ingest (worktree 격리) |
| 04-10 | PR #3 `f6f34fc` | foundations 9번째 종류, `/prefill` — 선행 실험 fork에서 이식 |
| 04-11 | PR #6 `5f904b1` | test6 사고 → `find-similar-concept`/`find-similar-claim`, 논문당 생성 한도, `.gitattributes` merge=union |
| 04-12 | PR #8 `1fc7738` | 중복 schema 상수를 `tools/_schemas.py`로 모음 |
| 04-15 | PR #14 `46cad0d` | linked worktree 안에서 그래프 재생성 금지 |
| 04-16 | PR #18 | CLAUDE.md의 schema를 `docs/runtime-*.md`로 뺌 |
| 04-24 | PR #23 `0366aea`, `b36c1df` | ingest 재작성: `references/` 분리, `dedup-policy.md` 신설. 엣지를 끝점별 종류로 바꾸고 confidence 필수화. 테스트 대부분 삭제 |
| 04-28 | `8233e0c` | 태그 `v1.0.0` (경량 태그) |
| 05-06 | PR #33 `1b2df1f` v1.1.0 | schema SSOT를 `runtime/` YAML로, codegen 제거, claims→methods |
| 05-26 | PR #60 `d89cc72` | 논문↔논문 엣지 8→4, frontmatter 투영 엣지, `parent_topic` 등 필드 추가 |
| 05-29~06-01 | `origin/paper` 65 commits | SciMem·SciFlow·SciDAG·SciEvolve. 태그 `arxiv-v1`=`6bc834a` |
| 05-30 | `d9ef6f1` | README를 OmegaWiki에서 AutoSci로 개명 |
| 06-01 | `03a78ee` | "main = stable, paper = paper snapshot" 브랜치 모델 명시 |
| 07~09 | codex/opencode 브랜치, Hiera(`40f5220`) | 런타임 이식과 실험 반복 도구. wiki 계약은 바뀌지 않음 |

이름이 바뀐 지점은 README뿐이다. 코드 안 이름은 여전히 OmegaWiki다(`tools/research_wiki.py:2` "OmegaWiki — Wiki Knowledge Engine.", `runtime/loader.py:1`, `CONTRIBUTING.md:1`). main의 wiki 계약은 `d89cc72`(05-26) 이후 바뀌지 않았다(`git log -- runtime/`의 마지막 main commit).

## 4. 설계 결정과 이유

### Q1. 왜 skill(LLM 프롬프트) + Python 도구 구조인가

**결정 1-1. 판단은 skill 문서의 LLM이, 결정적 일은 `tools/*.py`가 한다.**

- (a) 규칙으로 명시: "**Skills** = orchestrators (LLM reasoning). **Tools** = executors (deterministic)." (`CONTRIBUTING.md:76`).
- (a) 방향성: 이슈 #11 답글에서 collaborator DanJoshua가 "we're working to make skills leaner and introduce coded tools to replace LLM reasoning where possible."라고 썼다(https://github.com/skyllwt/AutoSci/issues/11). — 가능하면 LLM 추론을 코드 도구로 바꿔 skill을 가볍게 하겠다는 뜻이다.
- (a) 계기가 된 사고: PR #6 본문 "15 papers → 45 claims + 37 concepts because subagents deduped from memory and missed paraphrases. `find-similar-*` are the deterministic gate to prevent this." (https://github.com/skyllwt/AutoSci/pull/6). commit `5f904b1` 본문은 정답이 "~15 / ~15"였다고 적는다(PR #6 Summary: "45 claims / 37 concepts where ~15 / ~15 were correct").
- (a) 프롬프트 규율만으로 부족하다는 판단: commit `46cad0d` "The guard is defense-in-depth against subagent prompt drift — init/SKILL.md already tells agents to SKIP these commands in INIT MODE, but that relied on prompt discipline alone." 이슈 #12 답글도 "Now it's enforced at the tool level, so a prompt-drifted subagent can't reproduce this conflict even if it tries."라고 적는다(https://github.com/skyllwt/AutoSci/issues/12).
- (a) 논문판 문서가 이 분업을 가장 길게 정당화한다. "The policy runtime provides semantic judgment, while deterministic tools provide sensors and effectors: signal collection, context construction, evidence validation, write-boundary enforcement, provenance ledgers, and accepted mutations. Keeping reasoning pluggable across Claude Code, OpenAI-compatible APIs, local models, or supplied agent-response JSON makes the evolution loop reproducible, inspectable, and model-agnostic." (`origin/paper:docs/scievolve.md:9-17`) — LLM은 의미 판단만, 도구는 감지·실행·검증·기록을 맡겨야 재현 가능하고 점검 가능하며 모델에 묶이지 않는다는 뜻이다.
- (a) 논문의 한계 절: "the current implementation is built as a skill package on top of general-purpose coding and reasoning agents. This makes the system easy to deploy and inspect, but it is not yet a science-specialized agent foundation." (arXiv 2605.31468 §9) — 범용 코딩 에이전트 위의 skill 묶음이라 배포와 점검이 쉽다는 이유다.
- 반대 방향 사례 (a): PR #22 "Agent-first PDF title extraction —— deterministic tools struggles to infer correct titles." (https://github.com/skyllwt/AutoSci/pull/22) — PDF 제목 추출은 코드가 못해서 LLM 쪽으로 옮겼다. 분업 기준은 "결정적으로 풀리는가"이지 "무조건 코드"가 아니다.
- 대안: 하나의 Python 앱이 LLM API를 직접 부르는 구조(SciDAG가 그 모양이다 — `origin/paper` PR #63 "the LLM layer speaks the OpenAI-compatible endpoint"). [추정] main이 이 길을 택하지 않은 이유는 Claude Code 세션(도구 사용·파일 편집·하위 에이전트·worktree)을 그대로 실행기로 쓰기 위해서다(사례: `/init`이 `run_in_background`+`isolation: "worktree"` 하위 에이전트를 쓴다 — PR #1 본문, 1건).
- 이력: 분업 원칙은 처음부터 있었다(`20c61b9:README.md:53-71`). 바뀐 것은 경계의 위치다. 개념 중복 판정이 LLM 기억에서 도구로 옮겨 갔고(`5f904b1`), 그래프 재생성 금지가 프롬프트에서 도구로 옮겨 갔다(`46cad0d`).

**결정 1-2. 공유 파일과 그래프는 도구로만 쓴다. 페이지 본문은 LLM이 직접 쓴다.**

- (a) "`wiki/graph/` is derived. Modify only via `tools/research_wiki.py`" (`CLAUDE.md:21`). 병렬 안전 근거: "Every shared-file write goes through a tool. ... The tool layer uses append semantics and the repository's `.gitattributes` declares `merge=union` for these paths, so parallel worktrees can merge without conflict." (`.claude/skills/ingest/references/init-mode.md:33`).
- (a) "Never lock or in-place-rewrite a shared file. Rewriting ... as a block replaces parallel peers' work when the worktrees merge." (`init-mode.md:35`).
- [추정] 페이지 본문을 도구 뒤로 숨기지 않은 이유는 본문이 자유 서술이라 도구 API로 표현하기 어렵기 때문이다(사례: `set-meta`가 frontmatter 한 필드 단위로만 동작 — `tools/research_wiki.py:2404-2443`, 1건). 페이지 생성 도구(create-page 같은 명령)는 `research_wiki.py` 명령 목록에 없다(`tools/research_wiki.py:10-50`).

**결정 1-3. SPA(웹 화면)는 skill을 흉내 내지 않고 명령 문자열만 만들어 준다.**

- (a) "The SPA cannot run /skill X — slash-commands need a Claude Code LLM session. Naive UX would silently call a different code path and produce results that diverge from /skill X's actual behavior. ... no silent skill faking." (`tools/serve.py:42-51`) — 같은 일을 하는 두 번째 코드 경로를 만들지 않으려는 이유다.

### Q2. 왜 YAML schema를 쓰기 도구에서만(엣지만) 강제하나

먼저 사실: main에서 쓰기 직전에 코드가 막는 것은 엣지뿐이다(`tools/research_wiki.py:279-307`). 페이지 frontmatter는 LLM이 직접 쓰고, 도구 경유 쓰기인 `set-meta`조차 schema를 검사하지 않는다(`tools/research_wiki.py:2404-2443` — enum·타입 검사 코드 없음). PR #30 본문은 "`PATCH /api/entities/{type}/{slug}` proxies to `set-meta` with schema validation."이라고 썼지만(https://github.com/skyllwt/AutoSci/pull/30), 현재 `serve.py`의 PATCH 처리부는 종류·slug·필드 존재만 확인하고 set-meta로 넘긴다(`tools/serve.py:588-644`). 그래서 이 문장은 지금 코드와 맞지 않는다.

**결정 2-1. schema를 YAML 한 곳에 두고 loader가 모든 소비자에게 나눠 준다. codegen은 없다.**

- (a) "Single source of truth for what is structurally legal in the wiki. ... **No codegen step** — edit YAML, restart the tool." (`runtime/CLAUDE.md:3-6`), "Every change below is **YAML-only, zero Python change**." (`runtime/CLAUDE.md:21`).
- (a) 이력상의 이유: commit `1fc7738` "Schema constants (ENTITY_DIRS, VALID_EDGE_TYPES, REQUIRED_FIELDS, VALID_VALUES, FIELD_DEFAULTS) were duplicated between lint.py and research_wiki.py — extracted to tools/_schemas.py as single source of truth." 이어서 `1b2df1f`가 `_schemas.py`(-321줄)와 파생 문서를 지웠다: "Eliminate the codegen pipeline and its derived docs", "Make consumers data-driven (zero hardcoded entity/edge name lists)", "Fix doc/spec drift: - 7 entries in writers.yaml whose declared writer did not match the skill's actual SKILL.md behavior".
- (a) 문서도 같은 이유로 지웠다: "Mirrors the SSOT refactor's code-as-source-of-truth principle" (commit `1b2df1f` 안 "docs: retire frontend-design + runtime-visualization, fold into code").
- (a) 이슈 #34 owner 답글: "The schema is now YAML-driven (as of the latest dev branch), making it much easier to extend link types and entity kinds." (https://github.com/skyllwt/AutoSci/issues/34).
- 한계 (a): "Only when extending the **schema language itself**, not when adding more data" 때 Python을 고친다(`runtime/CLAUDE.md:65-71`). 실제로 생물 도메인 브랜치는 엣지에 `metadata:` 블록을 넣으려고 `runtime/loader.py::validate_edge_attributes`를 66줄 고쳤다(commit `372f7a5`, `origin/dev-dcy-biology`). 프론트엔드는 YAML을 못 읽어 손으로 복제한다: "The frontend's app/modules/schema.js stays a hand-mirrored copy because JavaScript cannot import from runtime/loader.py" (commit `1b2df1f`).
- 대안과 이력: (1) 프롬프트 안 schema(`20c61b9:CLAUDE.md:92-275`), (2) 맥락 비용 때문에 문서로 분리 — PR #18 "Extract CLAUDE.md: split runtime schema into `docs/runtime-*.md` to reduce context window cost" (https://github.com/skyllwt/AutoSci/pull/18), (3) Python 상수(`_schemas.py`, `1fc7738`), (4) YAML + loader(`1b2df1f`). 네 번 옮겨 다녔다.

**결정 2-2. 엣지는 쓰기 직전에 거부한다.**

- (a) 직접 이유를 적은 문장: "Hard validation for new writes. Legacy graph rows remain lint-readable." (`tools/research_wiki.py:249`). ingest 문서: "`tools/research_wiki.py add-edge` rejects missing confidence/evidence for paper-paper and paper-concept semantic edges, and rejects legacy paper-to-concept or paper-to-paper types on new writes." (`.claude/skills/ingest/SKILL.md:66-68`).
- 이력: v0.1의 `add_edge`는 종류 이름만 막았다(`20c61b9:tools/research_wiki.py:175-182`). 끝점·confidence·evidence 강제는 `b36c1df`("Rebuild ingest. Deleted tests.")에서 `_schemas.py`의 `EDGE_TYPE_SPECS` 레지스트리와 함께 들어왔다(`git show b36c1df -- tools/_schemas.py`). commit 메시지에 이유는 없다.
- [추정] 엣지만 쓰기 전에 막는 이유는 세 가지가 겹친다. 첫째, 엣지는 이미 도구로만 쓰므로 막을 자리가 있다(사례: `CLAUDE.md:21` 1건). 둘째, 엣지 형태는 짧은 구조라 결정적으로 검사할 수 있다. 셋째, 잘못된 엣지는 `edges.jsonl`에 append되어 섞이면 찾기 어렵다(사례: `/check`의 dangling-node 검사가 사후에만 있다 — `check/SKILL.md:117-124`, 1건).
- 모르는 것: 왜 끝점 페이지 부재는 경고에 그치는가(`tools/research_wiki.py:309-314`). [추정] 병렬 worktree에서 형제 에이전트가 만들 페이지를 먼저 가리킬 수 있기 때문이다(사례: `init-mode.md:16` "Record the relationship via `tools/research_wiki.py add-edge` instead", `_resolve_target_kind`의 주석 "orphan edges that point at a not-yet-created entity — still useful for visualization" `tools/research_wiki.py:581-582`, 2건).

**결정 2-3. 페이지는 쓰기 전에 "형태만" 보고, 의미 감사는 `/check`로 미룬다.**

- (a) "The shape check is intentionally narrow. Backlink symmetry, dangling-node detection, and cross-entity consistency are `/check`'s job, not this skill's." (`.claude/skills/ingest/SKILL.md:148`).
- (a) 비용 이유: "Running those audits inside `/ingest` slows the skill down and duplicates work." (`.claude/skills/ingest/references/dedup-policy.md:63`), "Do not read the entire `wiki/` to look for broken back-references during ingest — the time and token cost is large and the work is redundant with `/check`." (`.claude/skills/ingest/references/cross-references.md:98`).
- (a) 하위 호환 이유: 새 필드 `tldr`·`contribution_type`·`datasets`를 lint 필수로 만들지 않은 까닭은 "so existing pages do not break, but new ingests must" (`.claude/skills/ingest/SKILL.md:135`).
- 대안: 페이지 쓰기 도구에 schema 검사를 붙이는 것(PR #30 본문이 그렇게 주장했으나 구현되지 않음). 논문판은 쓴 뒤 검사인 Trust Guard를 붙였다(Q4 참고).
- [추정] 이 결정은 "LLM이 파일을 직접 쓴다"는 결정 1-2의 결과다. 페이지 쓰기가 도구를 지나지 않으니 쓰기 전 검사를 걸 자리가 없다(사례: 페이지 생성 명령 부재 `tools/research_wiki.py:10-50`, 1건).

**결정 2-4. skill별 쓰기 권한(`writers.yaml`)은 명세로만 두고 런타임에서 막지 않는다.**

- (a) "We deliberately did not plumb a `--skill` arg through set-meta / add-edge: research workflows are fluid, and `/edit` exists as a designed escape hatch for "per user request" overrides — runtime enforcement here would either fight `/edit` or grow a long exception list." (`runtime/policy/writers.yaml:8-11`) — 연구 흐름이 유동적이고, `/edit`라는 탈출구와 싸우거나 예외 목록이 길어지기 때문이다.
- (a) "When this file disagrees with reality, update the file (or the offending SKILL.md) — do not add runtime checks." (`runtime/policy/writers.yaml:13-14`), 신원 필드 잠금이 필요하면 "put it in tools/research_wiki.py::set_meta as a data-integrity check, not as a permission check driven by this file." (`:21-25`).
- 엔터프라이즈 관점은 #6에서 다룬다.

**결정 2-5. 논문↔논문 엣지를 8종에서 4종으로 줄였다.**

- (a) "`improves_on ⊆ builds_on` (subset; merged)", "`compares_against ⊆ cites` (every comparison already cites)", "`surveys ⇐ papers.contribution_type contains "survey"` (derivable)", "`complementary_to ≈ same_problem_as` (boundary fuzzy in practice)" (`runtime/schema/edges.yaml:17-23`, commit `d89cc72`). — 부분집합·이미 있는 엣지·파생 가능·경계 모호를 이유로 지웠다.
- (a) 의미 엣지를 드물게 두는 이유: "Graph noise is worse than a missing edge." (`cross-references.md:79`), "If the same statement would be true for dozens of papers in the wiki, skip the paper-to-paper edge" (`cross-references.md:58-60`).
- 이력: v0.1 일반 엣지 9종(`20c61b9:README.md:192-194`) → `b36c1df`에서 끝점별 12종(논문↔논문 8, 논문→개념 4) + legacy 표시 → `d89cc72`에서 논문↔논문 4종.
- 모르는 것: v0.1의 끝점 무관 `extends`/`supports`를 끝점별 이름으로 바꾼 이유. commit `b36c1df` 메시지는 "Rebuild ingest. Deleted tests."뿐이다. PR #23·#26 본문도 템플릿 그대로다. 알려면 작성자(DanJoshua)에게 묻거나 당시 대화 기록이 필요하다.

### Q3. 왜 foundation 계층과 "만들기 전에 병합"인가

**결정 3-1. 교과서 지식을 `foundations/`라는 별도 종류로 둔다.**

- (a) 원래 동기(선행 실험 fork의 할 일 목록): "增加 prefill skill。这个 skill 将特定领域的基本知识（包括奠基性论文，common practice等）作为 background 保留在 wiki 中。Why do this: 一个研究员在读论文时，对于Transformer, RL, CoT等基本知识的反应，和对特定 concept（比如 adversial training, outlier）的反应应当是不同的。且这些基础知识的处理可能会在 wiki 创建的前期不必要地分散 llm 的注意力。" (`DanJoshua/Research-Wiki-experimental:future-features.md`) — 뜻: 연구자는 Transformer·RL·CoT 같은 기초 지식과 특정 개념(adversarial training, outlier)에 다르게 반응해야 한다. 기초 지식 처리가 wiki 초기에 LLM의 주의를 쓸데없이 흩뜨릴 수 있다.
- (a) 이식 PR: "the whole point of `/prefill` is to keep foundational background separate from research concepts so `/ingest` doesn't pollute `concepts/` with textbook material." (PR #3 https://github.com/skyllwt/AutoSci/pull/3).
- (a) 논문 부록 B: "Textbook background that newer research builds on, separated from active-research concepts/ so the rest of the wiki can wikilink to "well-known prerequisites" without inflating the concept list." (arXiv 2605.31468 부록 B, Foundation entry 설명).
- (a) 통계에서 빼는 이유: "**Excluded from research-maturity totals** — background knowledge shouldn't inflate research progress scores." (PR #3).
- (a) orphan 검사에서 빼지 않은 이유: "Under correct usage every foundation receives an inward link via `/ingest` dedup, so orphan is a real diagnostic signal" (PR #3).
- 대안: foundation을 일반 개념에 `maturity: stable`로 섞는 것. [추정] 섞으면 범용어가 개념 중복 대조에서 "병합 대상"이 되어 `key_papers`가 무한히 커진다(사례: 병합 시 "Append this paper to the existing page's `key_papers`" `dedup-policy.md:36`, 1건).

**결정 3-2. foundation은 terminal이다(역링크를 쓰지 않는다) — main만.**

- (a) PR #3: "**Terminal by design**: receives inward links from papers/concepts/etc., writes no reverse link." `check_xref_asymmetry` docstring에 "no `foundations` source branch and no `foundations/` target lookup may ever be added"를 적어 두었다(PR #3 본문).
- 근거 문장에 "왜 terminal인가"는 직접 없다. [추정] 기초 개념은 거의 모든 논문이 가리키므로 역링크 목록이 끝없이 커지기 때문이다(사례: foundation 페이지에 `key_papers` 필드 자체가 없다 `runtime/schema/entities.yaml:171-183`, 투영에서 terminal 제외 `tools/research_wiki.py:610`, 2건).
- 이력: 논문판은 이 결정을 뒤집었다. "Foundations stops being terminal: remove `terminal: true` (entities.yaml) and drop `foundations` from `terminal_targets` (xref.yaml) so its reverse sections are checked/repaired." (`origin/paper:docs/superpowers/plans/2026-05-29-autosci-schema.md:26`). 지금 `origin/paper:runtime/schema/xref.yaml`은 `terminal_targets: []`이고 foundation에 `## Contributed by papers`, `## Grounds concepts`, `## Grounds methods` 역방향 섹션을 둔다. commit `c8a8d05` "docs(schema): correct stale foundations-terminal comments (SciMem-5)". 뒤집은 이유는 논문 §3.1의 모델 — "Paper entities ... contribute to Foundation entities. Foundation entities provide stable background knowledge that grounds Concept and Method entities." — 을 schema로 옮기려는 것이다. [추정] 즉 논문판은 foundation을 "허브 차단 장치"보다 "근거 계층"으로 다시 정의했다(사례: `grounded_in` 필드와 `contributes_to_foundation` 엣지 추가, plan 문서 Task A1·A2, 2건).

**결정 3-3. 개념은 "만들기 전에" 결정적 도구로 대조하고, 기본값은 병합이다.**

- (a) 핵심 이유: "Over-merging is cheap to undo: a wrongly-merged entry can be split later with its history preserved. Over-creating is expensive: a sea of near-duplicates silently poisons every downstream skill and is hard to detect post-hoc." (`dedup-policy.md:42`).
- (a) 건강한 상태의 모습: "A healthy ΩmegaWiki has far fewer concepts and methods than papers. ... When `/ingest` creates a new concept or method per paper by default, the wiki quickly devolves into a pile of near-duplicates that breaks every downstream skill — survey generation, gap detection, idea novelty, citation reasoning." (`dedup-policy.md:7`).
- (a) 기억 대신 도구를 쓰는 이유: "Skipping the dedup step is the single most common cause of wiki bloat. If you think you already have the answer from reading pages earlier in the session, you still verify — paraphrases slip past human scanning." (`dedup-policy.md:29`). 계기는 test6 사고(PR #6, 결정 1-1 참고).
- (a) 결정적이고 재현율 쪽으로 맞춘 이유: "tuned for high recall — the LLM caller does the final semantic judgment from a small ranked list. Designed to be invoked from /ingest BEFORE any concept is created, to prevent the "subagent A and subagent B both create textual-gradient-descent under different slugs" failure mode." (`tools/research_wiki.py:963-967`).
- (a) foundation을 먼저 정렬하는 이유: "foundations are terminal — prefer reference over create" (commit `5f904b1` 본문), 코드 주석 "foundations with high score first (they're terminal — prefer them)" (`tools/research_wiki.py:1112`).
- 대안: (1) 사후 일괄 정규화 — AutoSci는 `/check`의 LLM 근사 중복 판정을 "merge recommendations"로만 둔다(`check/SKILL.md:134`). 논문판은 `/dream` 통합(consolidation)으로 사후 병합을 추가했다(아래 Q4). (2) 임베딩 유사도 — 쓰지 않는다. 모르는 것: 임베딩을 거부한 이유. 저장소·이슈·PR 어디에도 비교 근거가 없다. 작성자에게 묻는 것 말고는 알 길이 없다.
- 이력:
  - `5f904b1`: Branch 0(foundation 연결)은 "foundation and score >= 0.80"이었고, 0.40~0.80 foundation은 정의를 읽고 판단했으며, 새 메커니즘이면 개념 쪽으로 가되 "link `derived_from` to the foundation in addition"이었다(`git show 5f904b1:i18n/en/skills/ingest/SKILL.md` 257-267행).
  - `0366aea`(ingest 재작성): foundation 문턱이 0.40으로 내려가고(`git log -S'foundation with score ≥ 0.40'`이 이 commit을 가리킴) "추가로 derived_from도 단다"는 갈래가 사라졌다. 이유는 commit에 없다.
  - 한도: `5f904b1`은 importance <5 / ==5로 1·3이었다. 지금은 <4 / ≥4로 1·3(개념), 1·2(방법)다(`dedup-policy.md:48-49`). 바뀐 commit은 `0366aea`다(같은 재작성). 이유는 적혀 있지 않다.
  - 동의어 표: claim 대조에는 "outperform/beat/exceed" 같은 정규화 표가 있었다(`git show 5f904b1:tools/research_wiki.py:492-524` `_CLAIM_CANONICAL_MAP`). 개념 대조에는 처음부터 없었다. claims가 사라질 때(`1b2df1f`) 함께 지워졌다.

**결정 3-4. 논문당 새 개념·방법 수에 한도를 둔다.**

- (a) "The purpose of the limit is to keep the default behavior conservative. It is not a quota to fill." (`dedup-policy.md:46`). 병렬 충돌 면을 줄이는 효과도 적혀 있다: "the per-paper creation limit ... keeps the collision surface small" (`init-mode.md:41`).
- 한도 초과 처리 (a): "merge them into the nearest existing entry even if its score is below the usual merge threshold. If no candidate is close enough to merge safely, skip writing that entity — `/check` will surface the resulting gaps, and the user can decide whether to `/edit` them in." (`dedup-policy.md:52`). 그런데 이슈 #41 답글은 `/check`가 "can't assert that an ingest should have created more (or less) pages than it did. This is a known blind spot"이라고 적는다(https://github.com/skyllwt/AutoSci/issues/41). 두 문장은 어긋난다. 버려진 후보를 `/check`가 찾아 준다는 약속은 지켜지지 않는다.

**결정 3-5. 방법(methods)에는 대조 도구가 없다.**

- 사실: "There is **no** `find-similar-method` tool." (`dedup-policy.md:27`). methods에는 `aliases` 필드도 없다(`runtime/schema/entities.yaml:103-120`).
- 모르는 것: 왜 개념용 도구를 방법에 재사용하지 않았는가. `_scan_entity_dir_for_similar`는 `title`과 `aliases`만 읽는데(`tools/research_wiki.py:1052-1053`) methods의 이름 필드는 `name`이라 그대로는 못 쓴다. [추정] methods가 늦게(`1b2df1f`) claims 자리를 대신하며 들어와 도구가 따라오지 못했다(사례: claims용 `find-similar-claim`이 같은 commit에서 지워짐, 1건).

**결정 3-6. methods를 1급 종류로 만들고 claims를 없앴다.**

- (a) "OmegaWiki 当前的 9 实体模型里 `claims` 和 `ideas` 语义重叠（两者都是「可验证的命题」），同时更有价值的 `methods`（跨论文复用的具名技术）没有实体 —— 目前只是加入 paper 的 `## Method` 章节。" (이슈 #31, TomWhite-tgz) — 뜻: claims와 ideas가 둘 다 "검증 가능한 명제"라 의미가 겹치고, 더 가치 있는 methods(논문을 넘어 재사용되는 이름 붙은 기법)는 종류가 없어 논문의 `## Method` 절에만 있었다.
- (a) methods 페이지를 만드는 조건: "A `methods/` page is only justified when the technique is **named**, **reusable**, and **citable** by a future paper." (`.claude/skills/ingest/SKILL.md:255`).

### Q4. 논문판(paper 브랜치)과 main의 차이와 그 이유

**결정 4-1. main은 가벼운 안정판, paper는 논문 시점 스냅샷으로 나눈다.**

- (a) "main is the lean stable version; the full SciMem/SciFlow/SciDAG/SciEvolve system from the paper lives on the paper branch (tag arxiv-v1), which is a research snapshot still under active iteration — not a finished product." (commit `03a78ee`).
- (a) 태그 메시지: "AutoSci paper snapshot — arXiv:2605.31468 ... Branch: paper. main remains the lean stable version (without these modules)." (`git cat-file -p arxiv-v1`).
- 구조 사실: paper는 main의 `d89cc72`(05-26)에서 갈라져 65 commits 앞서 있다(`git merge-base origin/main origin/paper`, `git log origin/main..origin/paper`). `arxiv-v1`(=`6bc834a`) 이후 paper에는 README 변경만 있다(`git diff --stat arxiv-v1 origin/paper` → README.md 1개). 차이는 260개 파일, +22094/-16675줄이다(`git diff --stat origin/main origin/paper`). 이 중 상당 부분은 paper가 `.claude/skills` 사본 추적을 끊은 것이다(commit `8033f7b` "stop tracking setup.sh-generated CLAUDE.md and .claude/skills (ship i18n sources only)").
- 기간: paper 쪽 SciMem·SciEvolve·Trust Guard commit은 2026-05-29~06-01의 나흘에 몰려 있고, 논문 v1 제출일은 2026-05-29다(arXiv 2605.31468v1 머리). [추정] paper 브랜치는 논문에 적은 기능을 짧은 기간에 구현한 것이라 main에 합칠 만큼 다듬어지지 않았다(사례: plan 문서가 "No test framework — verification is via `py_compile`..."라고 적음 `origin/paper:docs/superpowers/plans/2026-05-29-autosci-schema.md:9`, 커밋 메시지 "research snapshot ... not a finished product" `03a78ee`, 2건).

**paper와 main의 wiki 계약 차이** (출처: `git diff d89cc72 origin/paper -- runtime/`)

| 항목 | main | paper |
|---|---|---|
| 페이지 종류 | 9 (Summary 포함, manuscripts·reviews 없음) | 10 (Summary 삭제, manuscripts·reviews 추가) — 논문 Table 2 "10 typed entities"와 맞음 |
| foundation | terminal | 비terminal, 역방향 섹션 3개 |
| topic 소속 | `concepts.parent_topic`(link 1개) | 모든 장기 종류에 `parent_topics`(list) |
| 근거 연결 | 없음 | `concepts.grounded_in`, `methods.grounded_in` → foundations |
| 엣지 종류 | 16 | 24: 논문→방법 3(`proposes_method`, `applies_method`, `extends_method`), 논문→foundation 1(`contributes_to_foundation`), 개념↔개념 대칭 4(`shares_mechanism_with`, `shares_assumption_with`, `related_problem_formulation`, `contrasts_with_concept`) |
| 근거 위치 | `evidence` 자유 문자열 | 4개 workflow 엣지(`supports`, `contradicts`, `tested_by`, `invalidates`)에 `source_path`, `source_span`, `metric_name`, `metric_value`, `artifact_hash` 선택 속성 |
| 쓰기 검사 | `add-edge` 내장 검사 | 같음 + `add-edge --gate`(opt-in, Trust Guard form-check, BLOCK 시 격리) + 페이지 쓴 뒤 `trust_guard.py check` |
| 사후 병합 | `/check` 추천만 | `/dream` 통합·잊기 제안, safe apply는 frontmatter 메타데이터만 |

**결정 4-2. 논문판: 근거를 지닌 관계는 frontmatter 필드가 아니라 엣지로.**

- (a) "**Paper→Foundation = edge, not field.** §3.2 lists a frontmatter field `papers.contributes_to_foundations`; §3.4 defines a typed edge `contributes_to_foundation`. Per §1.2 (evidence-bearing relations ⇒ edges) and example §11.1, implement the **edge only**" (`origin/paper:docs/superpowers/plans/2026-05-29-autosci-schema.md:17`). — 근거를 지닌 관계는 엣지로 둔다는 원칙("evidence-bearing relations ⇒ edges")이 상위 명세 `newIdea.md` §1.2에 있다고 적는다.
- (a) 논문↔방법 역방향을 세 섹션으로 나눈 이유: "the xref fixer writes only the source slug, so one shared section would lose the relation type" (같은 문서 :22).
- 모르는 것: `newIdea.md` 본문. 저장소 어느 브랜치에도 없다(`git ls-tree -r --name-only origin/paper | grep -i newidea` 결과 없음). 원칙 §1.2의 전체 근거를 알려면 이 파일이 필요하다.

**결정 4-3. 논문판: Trust Guard — 결정적 form check + 독립 리뷰 LLM content check.**

- (a) 논문: "All SciMem writes pass through Trust Guard before entering the usable graph, since memory errors can propagate to future projects." (arXiv 2605.31468 §3.3) — 기억 오류가 다음 프로젝트로 번지기 때문이다.
- (a) 코드 docstring: "Form validity is deterministic and reuses tools/lint.py. Content validity is an independent Review-LLM check" (`origin/paper:tools/trust_guard.py:4-5`).
- 실제 동작: 페이지 `check()`는 파일이 있어야 돌고(`:100-102`) BLOCK이면 `raw/tmp/quarantine/`에 사본을 쓴다(`:125-137`). 즉 페이지는 쓴 뒤 검사다. 엣지 `check_edge()`는 쓰기 전 검사다(`:172-186`, `add_edge` 첫머리에서 호출 `origin/paper:tools/research_wiki.py:325-336`). 단 `--gate`는 opt-in이고 검사 내용은 `add_edge` 자체 검사와 대부분 겹친다(`_semantic_edge_errors` 재사용, `:152`). 새로 더해지는 것은 미선언 속성 거부, 격리 파일, `trust_events.jsonl` 기록이다.
- ingest skill은 "Step 6.5: Trust Guard (required before write)"라는 제목 아래, 실제로는 페이지를 이미 쓴 뒤 log 전에 돌리라고 지시한다(commit `7d5415c`, `origin/paper:i18n/en/skills/ingest/SKILL.md:199-204`). 리뷰 LLM이 없으면 content check는 PASS로 건너뛴다(`origin/paper:tools/trust_guard.py:111-112`).

**결정 4-4. 논문판: 자기 진화는 "제안 먼저", 적용은 되돌릴 수 있는 메타데이터만.**

- (a) "Requiring the agent to rewrite arbitrary core runtime code would confuse self-evolution with unsafe self-modification ... Core runtime and schema rewrites therefore belong to a higher-risk code-review path, while automatic evolution targets reversible or bounded surfaces with validation and ledgers." (`origin/paper:docs/scievolve.md:19-28`).
- (a) `/dream` safe apply: "only medium/high-confidence proposals may become actual memory changes, and only as reversible frontmatter metadata plus an append-only audit note. This gives `/dream` a closed loop without letting it rewrite scientific content." (`origin/paper:i18n/en/skills/dream/references/memory-operations.md:26-29`). 잊기는 삭제가 아니라 `scievolve_memory_weight: downweighted`다(`:54-55`). 통합은 `scievolve_consolidates_with`로 정식 페이지를 가리키고 compile-context가 이를 따른다(`origin/paper:tools/research_wiki.py:1446-1470`).
- 관련: "만들기 전에 병합"(main)에 "나중에 묶기"(paper `/dream`)가 더해진 모양이다. 원본 페이지는 지우지 않는다.

**결정 4-5. 논문판의 그래프 탐색도 허브를 거르지 않는다.**

- 사실: paper판 `graph_neighbors`는 main `neighbors`와 같은 BFS이고 투영 엣지를 선택적으로 더할 뿐 노드 종류·연결 수로 거르지 않는다(`origin/paper:tools/research_wiki.py:1303-1351`). paper판은 foundation을 비terminal로 바꿨으므로 [추정] foundation을 지나는 엉뚱한 연결은 main보다 늘어난다(사례: foundation 역방향 섹션 3개 추가 `origin/paper:runtime/schema/xref.yaml`, `contributes_to_foundation` 엣지, 2건).

### 기타 결정

**결정 5-1. 병렬 ingest와 worktree 격리, `merge=union`.**

- (a) 병렬화의 이유와 원래 직렬이었던 이유: "The previous design ingested N papers sequentially ... taking ~40 minutes for 10 papers. The bottleneck was intentional — later papers needed to read wiki state from earlier ones for concept dedup. This dedup can instead be handled at merge time by Claude" (PR #1 https://github.com/skyllwt/AutoSci/pull/1). — 직렬은 개념 중복 제거를 위해 일부러 둔 병목이었고, 병렬화하면서 그 일을 병합 시점으로 미뤘다.
- (a) union 병합: "`merge=union` is git's built-in driver for exactly this case: on conflict, both sides are concatenated ... Without this driver, /init's Phase B fan-in fails on the first merge" (`.gitattributes:15-23`).
- 결과 (a): PR #1 뒤 하루 만에 test6 사고가 났고(PR #6) 결정적 대조 도구가 들어왔다. 그런데 형제 worktree끼리는 서로의 새 개념을 볼 수 없다. fan-in 절차에는 같은 slug 충돌만 다루는 지시가 있고(`init-mode.md:42`), 다른 slug로 만든 근사 중복을 찾는 단계는 없다(`.claude/skills/init/references/parallel-ingest.md:51-70` — `find-similar-concept` 호출 없음). [추정] 병렬 모드에서는 "만들기 전에 병합"이 형제 간에 작동하지 않는다(사례: 위 fan-in 명령 목록 1건, PR #1의 "handled at merge time by Claude" 1건).
- 문서 어긋남: README는 "ingest the final paper set serially by default, with optional parallel worktree mode"(`README.md:482`)라고 하고, init skill은 "all paper ingest must run through parallel `/ingest` subagents with worktree isolation"(`.claude/skills/init/SKILL.md:234`)라고 한다.

**결정 5-2. 테스트를 거의 다 지웠다.**

- 사실: v0.1은 "2125 tests"(`20c61b9:README.md:249`), PR #8 시점 2327개(commit `1fc7738`). `b36c1df`가 `tests/` 대부분(예: `test_research_wiki.py` 2000줄, `test_lint.py` 795줄)을 지웠다. 지금 main `tests/`에는 `test_hiera_local.py` 하나뿐이다. `CONTRIBUTING.md:16`은 여전히 "`python -m pytest tests/ -v` must pass"를 요구하고, PR #73 작성자는 "this repo currently has no `tests/` directory, and local pytest exits with `no tests ran`"라고 적었다(https://github.com/skyllwt/AutoSci/pull/73).
- 모르는 것: 지운 이유. commit 메시지는 "Deleted tests."뿐이고 PR #23·#26·#40("test cleanup") 본문은 템플릿 그대로다. [추정] 기존 테스트 상당수가 SKILL.md 문구를 문자열로 검사했기 때문에 ingest 재작성마다 깨졌다(사례: `5f904b1` "tests/test_skill_init.py: +40 lines verifying the new Step 4.5 / sanity check / absolute-path ban language is present in all three copies", `5243790` "Renamed test_raw_readonly → test_raw_append_only_constraint and relaxed it to accept the new two-tier phrasing", 2건).

**결정 5-3. 그래프 재생성 파일은 linked worktree 안에서 만들지 못하게 막는다.**

- (a) "These files are full rebuilds, not append-only, so they can't be merge=union'd; parallel /init subagents running them in their worktrees produced add/add merge conflicts on Phase B fan-in (issue #12)." (commit `46cad0d`), 구현 `tools/research_wiki.py:791-818`.

**결정 5-4. 위키 중심이 RAG보다 낫다는 주장과 그 근거의 수준.**

- (a) 최초 README 표 "Why Wiki-Centric, Not RAG?": "Compiled once, maintained forever", "Bidirectional wikilinks + typed graph", "Yes — each paper enriches the whole graph" (`20c61b9:README.md:32-42`).
- (a) 측정은 없다고 작성자가 인정했다: "To our knowledge, there is no such benchmarks to measure the performance of LLM-wiki maintained by agent and an organized set of markdown files. ... The specific wiki maintenance paradigm has not been evaluated head-to-head." (이슈 #42, collaborator Morrow-Yang, https://github.com/skyllwt/AutoSci/issues/42). 같은 답글이 든 이유: "A human maintaining 200+ interlinked markdown files will inevitably let reverse links and cross-references decay." / "a well-organized markdown folder starts out equivalent, but diverges as the collection grows."
- (a) 논문도 같다: "evaluation remains underdeveloped. ... We therefore rely on end-to-end case studies and automated review as a paper-level proxy." (arXiv 2605.31468 §9).

## 5. 앞선 schema-glossary 보고서와 어긋나는 점

대상: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/reports/schema-glossary/autosci-omegawiki-schema.md`.

1. #H 근거 수치 절 마지막 문단과 #A의 논문 브랜치 설명: "main에는 이 도구가 없다", "쓴 뒤 검사다". 페이지 `check()`에 대해서는 맞다. 하지만 paper에는 엣지용 쓰기 전 게이트 `check_edge()`와 `add-edge --gate`가 있다(`origin/paper:tools/trust_guard.py:172-186`, `origin/paper:tools/research_wiki.py:325-336`, commit `13a5409`, `c6c3003`). 앞선 보고서는 `arxiv-v1`의 이 부분을 읽지 않았다. 다만 `--gate`는 opt-in이라 "모든 쓰기가 관문을 지난다"는 논문 문장보다는 여전히 약하다.
2. #F 범용어 허브 절은 foundation을 "terminal 종류"로만 설명한다. 이는 main 기준으로 맞다. 하지만 논문(§3.1 "Paper entities ... contribute to Foundation entities. Foundation entities ... ground Concept and Method entities")과 paper 브랜치는 foundation을 비terminal로 바꿨다(`origin/paper:runtime/schema/xref.yaml` `terminal_targets: []`). 논문을 근거로 foundation을 인용할 때는 main과 모델이 다르다는 점을 함께 적어야 한다.
3. #C 원문 연결 범위 절 "청크·문장 위치를 가리키는 필드는 어느 종류에도 없다": main 기준으로 맞다. paper 브랜치는 workflow 엣지 4종에 `source_path`·`source_span`을 선택 속성으로 더했다(commit `9c792ef`, `origin/paper:runtime/schema/edges.yaml`). 논문→개념 엣지에는 여전히 없다.
4. #A 강제 방식 절 "페이지 frontmatter: 쓰기 전 코드 검증이 없다": 맞다. 덧붙일 점이 있다. 도구 경유인 `set-meta`와 SPA PATCH도 schema를 검사하지 않는다(`tools/research_wiki.py:2404-2443`, `tools/serve.py:588-644`). PR #30 본문의 "with schema validation" 주장은 코드와 다르다.
5. #D 새/기존 연결 절의 foundation 문턱 0.40은 현재 코드와 맞다. 덧붙일 이력: 처음(`5f904b1`)에는 0.80이었고 0.40~0.80은 정의를 읽고 판단했으며 새 메커니즘이면 개념 페이지와 `derived_from`을 둘 다 다는 갈래가 있었다. `0366aea`에서 0.40으로 내려가며 그 갈래가 사라졌다. 앞선 보고서가 [추정]으로 지적한 "개념 1.0 일치보다 foundation 0.42가 먼저 적용될 수 있다"는 이 변경에서 생겼다.
6. #E 새 용어 절 "승인 대기열 파일은 없다. 보고서가 대기열 역할을 한다": 한도 초과로 버린 후보는 `/check`가 찾아 준다고 `dedup-policy.md:52`가 약속하지만, 이슈 #41 답글은 `/check`가 "should have created more ... pages"를 판정하지 못한다고 인정한다. 그래서 보고서도 그 후보를 담지 못한다.
7. #A "규칙 14개"(xref)는 맞다. 이슈 #41 답글은 "10 bidirectional rules"라고 적었는데 이는 `d89cc72` 이전 수다.

## 6. 엔터프라이즈 다중 작성자 보고서 용도에 비춰

조건: 작성자마다 같은 대상을 다른 용어로 쓴다. 형식 없는 문서가 섞인다. 여러 사람이 쓰고, 권한이 있다.

### 쓸 만한 장치

1. 쓰기 전 거부를 도구 한 곳에 모으는 구조(`add-edge` + `runtime/loader.py`). 관계 종류, 끝점 종류, `evidence`·`confidence` 필수를 YAML로 선언하면 쓰기 직전에 막힌다. 다중 작성자 환경에서 관계 이름이 흩어지는 것을 추출 뒤가 아니라 쓰기 시점에 끊는다. 단 AutoSci는 페이지 쪽을 막지 않았다. 우리 쪽은 페이지 생성도 도구 뒤로 보내야 한다(결정 2-3의 원인이 결정 1-2였으므로).
2. "만들기 전에" 결정적 대조 + "기본은 병합" + 비대칭 비용 논리(`dedup-policy.md:42`). 사내 용어집(정식 이름 + 별칭)을 foundations처럼 미리 심어 두는 방식(`/prefill`)과 잘 맞는다. 대조 결과에 `match_reason`이 붙어 사람이 판정을 검토하기 쉽다(`tools/research_wiki.py:1068-1085`).
3. 동의어 정규화 표. claims용으로 있었다가 사라진 `_CLAIM_CANONICAL_MAP`(`5f904b1:tools/research_wiki.py:492-524`)은 작성자별 동사·표현 차이를 결정적으로 접는 장치다. 개념 대조에는 없었으니 우리가 되살릴 만하다.
4. 외부 ID 앵커. 생물 브랜치는 단백질 개념에 `gene_symbol`, `uniprot_id`를 붙였다(`origin/dev-dcy-biology:runtime/schema/entities.yaml` concepts 블록). 사내라면 사번·제품 코드·프로젝트 코드가 같은 역할을 한다. 다만 AutoSci 대조 도구는 이 ID를 쓰지 않는다(`git show origin/dev-dcy-biology:tools/research_wiki.py | grep uniprot` 결과 없음). 우리는 ID 일치를 이름 대조보다 먼저 보는 규칙으로 써야 한다.
5. 도메인 확장 경로. 생물 브랜치는 YAML만으로 `datasets` 종류와 엣지 14종을 더했다(commit `5e5df95`). 엣지 속성에 타입 있는 `metadata`가 필요해지자 loader를 고쳤다(`372f7a5`). 부서별 schema 확장도 같은 두 단계를 밟을 것이다.
6. 논문판의 근거 위치 속성(`source_path`, `source_span`)과 "근거를 지닌 관계는 엣지로" 원칙. 보고서 문장 단위 근거가 필요한 사내 용도에 맞다.
7. 사후 병합을 삭제 없이 메타데이터로 하는 `/dream` safe apply. 다중 작성자 환경에서는 누가 쓴 페이지를 함부로 지우면 안 되므로, "정식 페이지를 가리키는 표시 + 검색 가중치 낮춤"은 되돌리기 쉬운 병합 방식이다.
8. 병렬 쓰기 규율: 공유 파일은 append만, `merge=union`, 재생성 파일은 주 작업 공간에서만(`.gitattributes`, `tools/research_wiki.py:791-818`). 여러 사람이 동시에 ingest하는 상황에 그대로 쓸 수 있다.

### 걸리는 점

1. 권한이 명세뿐이다. `writers.yaml`은 런타임에서 읽히지 않는다(`runtime/policy/writers.yaml:3-11`). 작성자들은 "연구 흐름이 유동적"이라는 단일 사용자 전제로 이를 택했다. 사내 다중 작성자·권한 요구와 정면으로 부딪힌다. 이 결정은 우리 조건에서 근거를 잃는다.
2. 원문 단위가 문서 전체다. 형식 없는 보고서는 절·쪽 구조가 없으니, "어느 문서" 수준 연결로는 근거 추적이 약하다. main에는 위치 필드가 없다.
3. 방법·사람 쪽에는 대조 도구도 별칭 필드도 없다(`dedup-policy.md:27`, `runtime/schema/entities.yaml:63-120`). 사내 보고서에서는 사람·조직·제품 이름의 불일치가 개념보다 흔할 것이다 [추정](사례: 이 갈래에서 본 사례 없음 — 사용자 조건 문장 1건뿐).
4. 대조가 영어 토큰 전제다. `_normalize_text`와 `_content_tokens`는 `[^a-z0-9\s]`를 모두 공백으로 바꾼다(`tools/research_wiki.py:987`, `:999`). 한글 제목은 정규화 뒤 빈 문자열이 되어 점수 0이 된다. 그러면 모든 한글 후보가 "만들어도 된다"로 판정된다. 한국어 보고서에는 그대로 쓸 수 없다.
5. 허브 차단이 그래프 탐색에 없다(main·paper 모두 BFS가 노드를 거르지 않음 — `tools/research_wiki.py:1184-1237`, `origin/paper:tools/research_wiki.py:1303-1351`). 논문판은 foundation을 비terminal로 바꿔 오히려 허브를 키웠다.
6. 병렬 ingest에서는 형제 간 근사 중복을 잡지 못한다(결정 5-1). 여러 사람이 동시에 넣는 상황이 바로 이 경우다.
7. 한도 초과로 버린 후보가 아무 데도 남지 않는다(결정 3-4). "어느 정도 사람이 하더라도"라는 사용자 목표에는 대기열 파일이 필요하다.
8. 품질 측정이 없다(이슈 #42, 논문 §9). 문턱 0.40/0.80/0.85와 한도 1·3·2에 보정 근거가 없다. 그대로 가져오면 우리 데이터로 다시 맞춰야 한다.
9. 테스트가 없다(결정 5-2). 코드를 가져오면 우리가 테스트를 새로 써야 한다.

## 7. 모르는 것과 알아낼 방법

1. `newIdea.md`(논문판 schema 확장의 상위 명세)의 본문, 특히 §1.2 "evidence-bearing relations ⇒ edges"의 근거. 저장소에 없다. 작성자 Tom White(TomWhite-tgz)나 owner에게 요청해야 한다.
2. `b36c1df`에서 엣지를 끝점별 이름으로 바꾸고 confidence를 필수로 만든 이유, 같은 commit에서 테스트를 지운 이유. 메시지·PR 본문이 비어 있다. DanJoshua에게 묻거나 PR #23·#26의 리뷰 대화(현재 댓글 없음)를 보면 된다.
3. `0366aea`에서 foundation 문턱을 0.80→0.40으로 내리고 한도 기준을 importance 5→4로 바꾼 이유. 같은 방법으로만 알 수 있다.
4. 임베딩 기반 대조를 쓰지 않은 이유. 어디에도 언급이 없다. 작성자에게 물어야 한다.
5. 방법 대조 도구를 만들지 않은 이유. 이슈·PR에 언급이 없다.
6. 선행 저장소 `skyllwt/Research-Wiki`의 `spec/`(vision, ADR). `CLAUDE.md`가 `spec/06-decisions/` ADR을 언급하지만 공개 commit 트리에는 `spec/`이 없다(`gh api repos/skyllwt/Research-Wiki/git/trees/22a4e87?recursive=1`). 작성자가 비공개로 두었을 수 있다.
7. 논문 Table 2의 "v1.0.0, May 2026"과 태그 `v1.0.0`(=`8233e0c`, 2026-04-28)의 관계. 표가 가리키는 코드가 main인지 paper인지 확인하려면 작성자 확인이 필요하다. 표의 "10 typed entities"는 paper 브랜치와 맞는다.
8. Trust Guard content check와 `/dream`이 실제 wiki에서 얼마나 잡고 합쳤는지. `wiki/graph/trust_events.jsonl` 실데이터가 저장소에 없다(`.gitignore`가 wiki 데이터를 뺀다 — commit `1b2df1f` ".gitignore: enforces per-user data boundary"). 사례 위키를 받아야 알 수 있다.
9. `docs/extending.md`. `CONTRIBUTING.md:21`과 PR 템플릿이 가리키지만 파일이 없다(`ls docs`). `git log --all -- docs/extending.md` 결과도 비어 있어 공개 이력의 어느 브랜치에도 존재한 적이 없다. 선행 저장소나 비공개 작업본에 있었는지는 작성자에게 물어야 안다.

## 8. 출처 모음

- 저장소 https://github.com/skyllwt/AutoSci, main `f5c2fe0`, paper `5e1bfc8`, 태그 `arxiv-v1`→`6bc834a`, 태그 `v1.0.0`→`8233e0c`, 생물 브랜치 `origin/dev-dcy-biology` `11bf94d`.
- 논문 https://arxiv.org/abs/2605.31468 (HTML https://arxiv.org/html/2605.31468, v1 2026-05-29).
- 선행 저장소 https://github.com/DanJoshua/Research-Wiki-experimental (`future-features.md`), https://github.com/skyllwt/Research-Wiki.
- 이슈 https://github.com/skyllwt/AutoSci/issues/11, /12, /31, /34, /41, /42. PR /pull/1, /3, /6, /18, /22, /30, /73.

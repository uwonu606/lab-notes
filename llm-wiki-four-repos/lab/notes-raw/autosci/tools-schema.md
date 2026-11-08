# AutoSci — tools·schema 갈래 노트

- 레포: skyllwt/AutoSci (구 OmegaWiki), main HEAD `f5c2fe0` (2026-10-02), MIT
- 로컬: `lab/repos/skyllwt_AutoSci`
- 이 갈래가 맡은 것: Python 도구(`tools/`), 계약층(`runtime/`), 예시 데이터(`wiki/`, `raw/`), 프런트(`app/`), 설정(`config/`), 테스트(`tests/`, `.sleepcode/tests/`).
- 맡지 않은 것: `.claude/skills/*` 프롬프트 흐름(다른 갈래). 여기서는 skill이 도구를 어떻게 부르는지 경계만 적는다.
- 코드는 실행하지 않았다. 아래 "코드 추적"이라고 쓴 판단은 코드를 읽고 따라간 결과이고, 실행해서 확인하지 않았다.
- 줄 번호는 레포 루트 기준이다.

## 읽은 범위

| 파일 | 줄 수 | 읽은 정도 |
|---|---|---|
| `runtime/loader.py` | 237 | 끝까지 |
| `runtime/schema/{entities,edges,xref,conventions}.yaml` | 183/157/78/30 | 끝까지 |
| `runtime/policy/writers.yaml` | 96 | 끝까지 |
| `runtime/templates/*.md.tmpl` (9개) | 각 9~21 | 끝까지 |
| `runtime/CLAUDE.md`, 루트 `CLAUDE.md` | 77/40 | 끝까지 |
| `tools/research_wiki.py` | 2861 | 끝까지 |
| `tools/lint.py` | 1170 | 끝까지 |
| `tools/backfill_citations.py`, `tools/reset_wiki.py` | 168/179 | 끝까지 |
| `tools/wiki2dag.py` | 1110 | 1~600, 891~1110 읽음. 600~890(LaTeX 헬퍼)은 훑음 |
| `tools/discover.py` | 1255 | 1~120, 426~830, 963~1060 읽음. 나머지(외부 API 수집·출력) 훑음 |
| `tools/fetch_s2.py` | 239 | 1~90(재시도) 읽음, 나머지 훑음 |
| `tools/fetch_arxiv.py`, `fetch_deepxiv.py`, `fetch_wikipedia.py`, `_env.py` | | 머리말·함수 목록만 훑음 |
| `tools/serve.py` | 1075 | 1~160, 211~227, 500~720 읽음. 나머지 훑음 |
| `tools/visualize.py` | 726 | 머리말·함수 목록만 훑음 |
| `tools/daily_arxiv.py` | 1534 | LLM 호출부(1182~1290)만 읽음. 범위 밖이라 나머지 안 읽음 |
| `tools/hiera/*.py` | | `__init__`, `adapter.py` 80~189, `ledger.py` 25~60 읽음. 나머지 머리말만 훑음 |
| `app/modules/schema.js`, `graph.js` | | schema.js 1~60 읽음, graph.js는 grep만 |
| `config/visualize.json`, `config/README.md` | | 훑음 |
| `wiki/index.md`, `wiki/log.md`, `raw/*` | | 끝까지(빈 골격뿐) |
| `tests/test_hiera_local.py`, `.sleepcode/tests/test_discover_from_venue.py` | | 머리말만 |
| `.gitattributes`, `CHANGELOG.md` | | 끝까지 |
| 이력 | 108 commit | `git log` 전체, 핵심 commit 12개 본문 |
| 이슈·PR | | 이슈 #12, #20, #31, #34, #41, #42, #11 본문·댓글 |
| `origin/paper` 브랜치 | | schema·도구 diff 목록과 머리말만 훑음(부록) |

---

## 1. 구조

### 1.1 한 장 그림

```
runtime/schema/*.yaml ─┐
runtime/policy/writers.yaml ─┤  (yaml.safe_load, import 시점)
                       ▼
                runtime/loader.py  ──────────────┐
                 │ ENTITIES / EDGES / XREF        │
                 │ REQUIRED_FIELDS, VALID_VALUES  │
                 │ EDGE_TYPE_SPECS, 헬퍼 함수     │
                 ▼                                ▼
     tools/research_wiki.py (쓰기·질의 엔진)   tools/lint.py (사후 검사·--fix)
       ▲         ▲           ▲                     ▲
       │         │           │                     │
  .claude/skills  tools/serve.py(SPA API)  tools/backfill_citations.py
  (Bash로 CLI 호출) (subprocess로 CLI 호출)   (subprocess로 CLI 호출)

  tools/reset_wiki.py, tools/visualize.py → loader.ENTITIES/ENTITY_DIRS만 import
  tools/discover.py, fetch_*.py, daily_arxiv.py → loader 안 씀(외부 수집, 자체 정규식으로 frontmatter 읽음)
  tools/wiki2dag.py → wiki와 무관(LaTeX → 포스터용 DAG)
  tools/hiera/ → wiki 읽기 전용, runs/hiera/에만 씀
```

근거:
- `runtime/CLAUDE.md:3-6` "YAML in `schema/` and `policy/` is the contract; `loader.py` is the Python access API consumed by `tools/lint.py` and `tools/research_wiki.py`. **No codegen step**"
- `tools/research_wiki.py:68-88`, `tools/lint.py:33-56`가 `runtime.loader`를 import한다.
- `tools/serve.py:135-146` `_run_research_wiki`가 CLI를 subprocess로 부른다.
- `tools/backfill_citations.py:87-131`이 `fetch_s2.py references`와 `research_wiki.py add-citations-batch`를 subprocess로 잇는다.
- `tools/reset_wiki.py:197-199`, `tools/visualize.py:39`가 loader에서 이름 목록만 가져온다.
- skill이 부르는 CLI 하위 명령 빈도(`.claude/skills` 전체 grep): `log` 59, `add-edge` 24, `slug` 20, `set-meta` 20, `rebuild-context-brief` 20, `rebuild-open-questions` 17, `init` 8, `maturity` 7, `transition` 6, `rebuild-index` 6, `dedup-edges` 3, `dedup-citations` 3, `find-similar-concept` 2, `add-citation` 2. `lint.py`는 `/check`·`/init` 등에서 7회.

### 1.2 저장소 세 층

| 층 | 파일 | 누가 쓰나 | 형식 |
|---|---|---|---|
| 페이지 | `wiki/<kind>/<slug>.md` | LLM이 직접 파일을 쓴다. 도구는 `set-meta`·`transition`·`_append_lines_to_section`·lint `--fix`만 | YAML frontmatter + 템플릿 H2 섹션 |
| 그래프 | `wiki/graph/edges.jsonl`, `citations.jsonl` | `research_wiki.py add-edge` / `batch-edges` / `add-citation` / `add-citations-batch`만 | JSON Lines, 한 줄에 엣지 하나 |
| 파생물 | `wiki/index.md`, `graph/context_brief.md`, `graph/open_questions.md`, `graph/projected_edges.jsonl` | `rebuild-*` 명령이 통째로 다시 씀 | md / jsonl |
| 기록 | `wiki/log.md` | `research_wiki.py log` (append) | `## [YYYY-MM-DD] <message>` |
| 작업 상태 | `wiki/.checkpoints/<task_id>.json` | `checkpoint-*` | `{task_id, completed[], failed[], metadata{}}` |

- 루트 `CLAUDE.md:21` Hard Rule 2는 "`wiki/graph/` is derived"라고 한다. 그러나 `edges.jsonl`의 의미 엣지(evidence·confidence 포함)는 페이지에서 다시 만들 방법이 없다. `rebuild-*` 명령 중 edges.jsonl을 만드는 것은 없다(`research_wiki.py:2583-2768` 명령 목록). 그래서 edges.jsonl은 사실상 원본 데이터다. 진짜 파생물은 `projected_edges.jsonl`, `context_brief.md`, `open_questions.md`, `index.md`뿐이다.
- `wiki/index.md`, `wiki/log.md`는 저장소에 빈 골격만 있다(`wiki/index.md:1-19`는 종류 이름 9줄, `wiki/log.md:1-3`은 머리말). 실제 데이터는 `.gitignore`로 사용자별로 뺀다(v1.1.0 commit `1b2df1f` 본문 "`.gitignore`: enforces per-user data boundary — wiki/{papers,...}/* ... are ignored").
- `raw/{papers,notes,web,discovered,tmp}`는 `.gitkeep`뿐이다. `conventions.yaml:20-22` `ownership.user_owned: [raw/papers, raw/notes, raw/web]`.

### 1.3 페이지 종류 9개 (`runtime/schema/entities.yaml`)

필드 문법(`entities.yaml:3-15`): `type`은 `str|int|float|bool|date|enum|object|link|list_str|list_int|list_link|list_object`, 그 밖에 `required`, `default`, `range`, `values`, `to`, `required_when`, `fields`, `item`. `terminal: true`는 "writes no outward links".

| 종류 | 필수 필드 | 링크 필드(`to`) | 그 밖 | lifecycle |
|---|---|---|---|---|
| papers (`:17-34`) | title, slug, tags, importance(1~5, 기본 3) | cited_by→papers | arxiv, venue, year, date_added, source_type(tex/pdf), s2_id, tldr, contribution_type, datasets, code_url | 없음 |
| concepts (`:36-50`) | title, tags, maturity(stable/active/emerging/deprecated), key_papers | key_papers→papers, related_concepts→concepts, linked_ideas→ideas, parent_topic→topics(단일) | **aliases**, definition, first_introduced, date_updated | 없음 |
| topics (`:52-61`) | title, tags | related_topics, key_people, key_papers, linked_ideas | key_venues | 없음 |
| people (`:63-76`) | name | 없음 | affiliation, research_areas, homepage, scholar, type{kind: researcher/team/organization, subtype} | 없음 |
| ideas (`:78-101`) | title, slug, status, origin, tags, priority | origin_gaps→[concepts,topics], linked_experiments | failure_reason(`required_when: {status: failed}`), novelty_score(1~5) 등 | proposed→in_progress→tested→validated/failed |
| methods (`:103-120`) | name, slug, type(11값 enum), tags | source_papers, parent_methods, child_methods, realizes_concepts | code_repo | 없음 |
| experiments (`:122-160`) | title, slug, status, linked_idea, hypothesis, tags | linked_idea→ideas, evaluates_methods→methods | setup{model,dataset,hardware,framework}, outcome, remote{...} | planned→running→completed/abandoned |
| Summary (`:162-169`) | title, scope, key_topics | key_topics→topics | paper_count | 없음 |
| foundations (`:171-183`) | title, slug, domain, status(mainstream/historical) | 없음 | **aliases**, source_url | 없음. `terminal: true` |

- 별칭 필드는 concepts와 foundations에만 있다(`:40`, `:180`). methods·people·topics에는 없다.
- 원문 위치를 가리키는 필드는 어느 종류에도 없다. 원문과의 연결은 papers의 `arxiv`·`s2_id`와 다른 종류의 `key_papers`·`source_papers` 같은 "논문 목록"뿐이다.
- 본문 섹션 골격은 `runtime/templates/<kind>.md.tmpl`이다. 예: papers는 `## Problem & Context / Key idea / Method / Experiment & Results / Limitations / Open questions / My take / Related`(`papers.md.tmpl:5-19`). 도구가 이 섹션 이름에 의존한다(1.6 참고).

### 1.4 엣지 16종 (`runtime/schema/edges.yaml`)

| 무리 | 엣지 | endpoints | direction | 필수 속성 |
|---|---|---|---|---|
| 논문↔논문 의미 (`:25-55`) | same_problem_as, similar_method_to | papers→papers | symmetric | confidence(high/medium/low), evidence |
| | builds_on, challenges | papers→papers | directed | confidence, evidence |
| 논문→개념 의미 (`:61-91`) | introduces_concept, uses_concept, extends_concept, critiques_concept | papers→concepts | directed | confidence, evidence |
| 작업 흐름 (`:98-145`) | supports, contradicts (workflow evidence), tested_by, invalidates (experiment), addresses_gap, inspired_by (idea), derived_from (provenance) | `*`→`*` | directed | 없음(evidence 선택) |
| 서지 (`:151-157`) | cites | papers→papers | directed | source(semantic_scholar/parsed_bib/manual) |

- 저장 위치: `conventions.yaml:27-30` `edge_storage.default: wiki/graph/edges.jsonl`, `exceptions.cites: wiki/graph/citations.jsonl`.
- edges.jsonl 한 줄의 필드(`research_wiki.py:338-348`): `from`("kind/slug"), `to`, `type`, `evidence`(문자열, 비어도 됨), `date`(UTC YYYY-MM-DD), 선택 `confidence`, 대칭이면 `symmetric: true`.
- citations.jsonl 한 줄(`research_wiki.py:414-420`): `from`, `to`, `type: "cites"`, `source`, `date`.
- 노드 ID는 `"<kind>/<slug>"`다. 종류는 `/` 앞부분 문자열로만 판단한다(`research_wiki.py:204-205` `_node_kind`).

### 1.5 역링크 규칙 14개 (`runtime/schema/xref.yaml`)

`forward`는 원천 종류와 링크 자리(frontmatter 필드 / 본문 섹션 / 엣지 종류) 중 하나와 대상 종류다. `reverse`는 대상 쪽 자리와 `action: append_slug | append_record`다(`xref.yaml:1-20`).

| # | forward | reverse |
|---|---|---|
| 1 | papers `## Related` → concepts | concepts.key_papers |
| 2 | papers 본문 어디든(`*`) → people | people `## Recent work` |
| 3 | topics.key_people → people | people `## Research areas` |
| 4 | concepts.key_papers → papers | papers `## Related` |
| 5,6 | ideas.origin_gaps → concepts / topics | concepts.linked_ideas / topics.linked_ideas |
| 7 | experiments.linked_idea → ideas | ideas.linked_experiments |
| 8 | methods.source_papers → papers | papers `## Related` |
| 9,10 | methods.parent_methods ↔ child_methods | 서로 |
| 11 | experiments.evaluates_methods → methods | methods `## Evaluated by` |
| 12 | methods.realizes_concepts → concepts | concepts `## Realized by` |
| 13 | topics.key_papers → papers | papers `## Related` |
| 14 | concepts.parent_topic → topics | topics `## Concepts` |

`terminal_targets: [foundations]`(`xref.yaml:78`). `edge_type` forward 자리는 문법에 있지만 main의 14개 규칙 중 쓰는 것이 없다.

### 1.6 쓰기 권한 표 (`runtime/policy/writers.yaml`)

필드 17개와 엣지 16개에 대해 "어느 skill이 써야 하는가"를 적는다. 예: `papers.importance: { writers: [ingest], frozen_after_first_write: true }`(`:30`), `ideas.status: { writers: [ideate, exp-eval, exp-pilot-eval, refine] }`(`:51`), 논문↔논문 의미 엣지는 `[ingest]`만(`:75-78`).
코드는 이 파일을 읽지 않는다. `loader.py:41`이 `WRITERS`로 읽어 두지만 import하는 곳이 없다(`grep WRITERS` 결과 loader 자신뿐).

### 1.7 `conventions.yaml`도 코드가 읽지 않는다

`slug_rule`, `path_pattern`, `log_grammar`, `ownership`, `edge_storage`(`conventions.yaml:5-30`)를 코드가 쓰는 곳이 없다. `research_wiki.py:73`이 `CONVENTIONS`를 import만 한다. 저장 경로는 코드에 박혀 있다(`research_wiki.py:300` `edges.jsonl`, `:388` `citations.jsonl`). slug 검사 정규식도 따로 있다(`serve.py:110` `^[a-z0-9][a-z0-9-]*$`, `hiera/common.py` `SLUG_RE`). 그래서 `runtime/CLAUDE.md:42-43`의 "Different storage location — list it under `conventions.yaml::edge_storage::exceptions`"는 지금 코드에서는 효과가 없다.

---

## 2. 동작 흐름

### 2.1 엣지 쓰기: `add-edge` (`research_wiki.py:275-357`)

입력: `--from kind/slug --to kind/slug --type T [--evidence] [--confidence] [--symmetric]`.

1. 종류 검사: `VALID_EDGE_TYPES`(= edges.yaml 키 − cites + legacy `extends`·`supersedes`, `loader.py:198`)에 없으면 `"Unknown edge type"` JSON을 찍고 `sys.exit(1)`(`:279-284`).
2. confidence 값 검사(`:285-290`). argparse `choices`도 같은 값을 건다(`:2603-2604`).
3. 대칭 정규화: 대칭 엣지면 from/to를 정렬한다. 대칭이 아닌 종류에 `--symmetric`을 주면 에러(`:255-263`, `:292-297`).
4. 강한 검사 `_semantic_edge_errors`(`:246-252`): legacy 조합(papers→papers의 `extends/supersedes/inspired_by/contradicts/supports`, papers→concepts의 `supports/extends`, `loader.py:56-58`), endpoint 종류 불일치(`loader.py:165-172`), 논문 자기 연결, 필수 속성 누락·enum 위반(`loader.py:203-220`). 하나라도 있으면 exit 1(`:303-307`).
5. 약한 검사: 끝점 파일이 없으면 stderr 경고만 내고 진행한다(`:208-215`, `:309-314`).
6. 중복 검사: edges.jsonl 전체를 읽어 `(from, to, type)`(대칭이면 정렬) 키가 있으면 `"exists"`로 끝(`:316-336`).
7. 파일 끝에 한 줄 append(`:350-351`). 잠금은 없다.

`batch-edges`(`:1711-1816`)는 stdin JSON 배열을 같은 규칙으로 검사한다. 항목 하나라도 에러면 아무것도 쓰지 않고 exit 1이다(`:1804-1808`). 전부 아니면 전무다.

코드 추적(실행 안 함):
- `*` endpoint 엣지(supports 등)는 `/`가 없는 ID(`"foo"`)도 받는다. `_node_kind("foo")`는 `""`이고 `*`는 무엇이든 맞으며, `_validate_node_refs`는 `/`가 없으면 건너뛴다(`:210-211`). 경고조차 없다.
- 끝점 종류 문자열에 오타가 있어도(`paper/x`) `*` 엣지면 통과하고 파일 없음 경고만 난다.

### 2.2 frontmatter 쓰기: `set-meta`, `transition`

`set-meta <path> <field> <value> [--append]`(`research_wiki.py:2404-2443`):
- 값을 `_parse_scalar`로 타입 추측한다(`:2101-2125`). 따옴표 제거, `[a, b]` 인라인 리스트, true/false, 실수, 정수.
- 필드가 frontmatter에 없으면 `--append`가 아닐 때 에러다(`:2347-2348`). 새 필드를 만들 수 없다.
- schema 검사가 없다. enum 값, `to` 종류, writers 권한 어느 것도 보지 않는다.
- 쓰기는 frontmatter 전체를 다시 직렬화하고(`_serialize_frontmatter`, `:2274-2327`) `.tmp`에 쓴 뒤 `replace`로 바꾼다(`:2432-2438`). 주석은 Windows에서 `rename`이 실패해 `replace`를 쓴다고 밝힌다(`:2428-2431`).
- frontmatter 파서는 PyYAML이 아니라 손으로 짠 것이다(`:2155-2271`, docstring "no PyYAML dependency"). 여러 줄 문자열, 중첩 깊이 2 이상, 따옴표 안 쉼표를 다루지 못한다. [추정] set-meta 한 번에 frontmatter 서식(따옴표, 블록/인라인 리스트, 주석)이 바뀔 수 있다(근거 사례: 직렬화가 원문을 보존하지 않고 dict에서 새로 쓰는 코드 1곳 `:2371-2372`).

`transition <path> --to <status> [--reason]`(`:1607-1704`):
- 허용 전이표 `TRANSITIONS`는 entities.yaml `lifecycle.transitions`에서 만든다(`:1593-1597`).
- 그러나 전제 조건은 Python에 박혀 있다: ideas→in_progress는 `linked_experiments`가 비어 있으면 거부(`:1640-1646`), ideas→failed는 `--reason` 필수(`:1648-1652`), experiments→completed는 `key_result` 필수(`:1654-1659`). 자동 날짜 필드도 Python 표다(`AUTO_FIELDS`, `:1600-1604`).
- `loader.validate_lifecycle_transition`(`loader.py:225-237`)은 import만 되고 불리지 않는다(`research_wiki.py:87`).

### 2.3 개념 중복 검사: `find-similar-concept` (`research_wiki.py:956-1118`)

입력: 후보 제목 + `--aliases "a,b,c"`. 출력: JSON 리스트 `{entity_type: foundation|concept, slug, title, aliases, key_papers, maturity, score, match_reason}`.

1. 후보 이름 목록 = 제목 + 별칭(`:1104`).
2. `wiki/foundations/`와 `wiki/concepts/`의 모든 페이지에서 `title`+`aliases`를 읽는다(`:1038-1056`).
3. 이름 쌍마다 `_phrase_match_score`(`:1007-1035`):
   - 정규화(소문자, `[^a-z0-9\s]` → 공백, 공백 압축) 뒤 같으면 1.0.
   - 한쪽이 다른 쪽에 포함되고 짧은 쪽이 2단어 이상이면 0.85.
   - 아니면 내용어(3글자 이상, STOP_WORDS 34개 제외) Jaccard j. j ≥ 0.7이면 j, 0.4 ≤ j < 0.7이면 `0.4 + (j-0.4)*0.5`(0.40~0.55), 그 밑은 0.
4. 페이지별 최고점이 0.40 이상인 것만 남긴다(`:1067`). `match_reason`에 어느 이름끼리 맞았는지 적는다(`:1068-1076`).
5. 정렬: foundation을 점수와 무관하게 먼저, 그다음 점수 내림차순(`:1114-1117`).

판단은 호출한 LLM이 한다. 주석 "tuned for high recall — the LLM caller does the final semantic judgment from a small ranked list"(`:963-965`). 문턱(≥0.80 병합, 0.40~0.80 LLM 판단, <0.40 생성)은 skill 쪽 `ingest/references/dedup-policy.md:35-38`에 있다(다른 갈래).

주석과 코드의 어긋남: 주석 "0.40-0.84 Jaccard similarity of content tokens, scaled"(`:978`). 이 어긋남은 처음 도입한 commit `5f904b1`부터 있었다. 그 commit 본문도 "content-token Jaccard (0.40-0.84)"라고 쓰지만 같은 commit의 코드가 이미 지금과 같은 두 구간 식이다(`git show 5f904b1:tools/research_wiki.py` 551-555줄).

한국어에 대한 코드 추적(실행 안 함): 정규화가 `[^a-z0-9\s]`를 지우므로(`:987`, `:999`) 한글 제목·별칭은 빈 문자열이 되고 점수 0이 된다(`:1015-1016`). 결과가 빈 리스트면 skill 규약상 "safe to create"(`:982`)다. `slugify`도 같은 정규식이라 한글 제목은 `"untitled"`가 된다(`:120-127`).

### 2.4 서지 인용: `add-citation`, `add-citations-batch`, `backfill_citations.py`

- `add-citations-batch --citer papers/<slug>`(`research_wiki.py:451-550`)는 stdin으로 S2 참고문헌 배열을 받는다. 위키 논문들의 `arxiv`·`s2_id`로 색인을 만들고(`:431-448`) 맞는 것만 `cites` 행으로 붙인다. 출력은 `received/matched/added/skipped_existing/unmatched/unmatched_samples`.
- 맞추기는 외부 ID 완전 일치뿐이다. 제목 유사도는 쓰지 않는다.
- `backfill_citations.py`는 모든 논문에 대해 `fetch_s2.py references` → `add-citations-batch`를 돌리고 끝에 `dedup-citations`를 돈다(`:78-157`). 이유는 docstring에 있다: "The bootstrap `/init` workflow skips `fetch_s2.py references` in parallel mode for safety and never reinstates it at fan-in. As a result, freshly-bootstrapped wikis have an empty `citations.jsonl`."(`:5-9`).

### 2.5 파생물 재생성

| 명령 | 입력 | 처리 | 출력 | LLM |
|---|---|---|---|---|
| `rebuild-index` (`:1823-1885`) | 모든 종류 디렉터리 frontmatter | 종류별로 slug + title/tags/status/importance/... 나열 | `index.md` 통째 덮어쓰기 | 없음 |
| `rebuild-context-brief` = `compile-context --for general` (`:821-824`, `:1264-1417`) | methods, open_questions.md, ideas, papers, experiments, edges.jsonl | 목적별 예산표(`CONTEXT_BUDGETS`, `:1244-1251`)에 따라 7개 절을 잘라 붙임 | `graph/context_brief.md` 덮어쓰기 | 없음 |
| `rebuild-open-questions` (`:831-885`) | papers `## Open questions`, topics `## Open problems`(H3 포함), concepts `## Open problems` | 해당 H2 블록 안의 `-` 글머리만 모아 `- [paper/<slug>] <항목>` | `graph/open_questions.md` 덮어쓰기 | 없음 |
| `rebuild-projected-edges` (`:586-691`) | 모든 비terminal 종류의 link/list_link/list_object 필드 | `fm_<kind>_<field>` 타입 엣지로 투영 | `graph/projected_edges.jsonl` | 없음 |
| `topic-backfill` (`:1892-2003`) | papers.tags, importance / topics.tags | 태그 교집합이면 importance ≥4 → `## Seminal works`, 아니면 `## SOTA tracker`에 `- [[slug]]` | topic 페이지 본문에 삽입(섹션 안 중복 제거) | 없음 |

`compile_context` 세부(`:1264-1417`):
- 예산 순서는 (Methods, Gaps, Failed, Papers, Experiments, Edges, Stale)이다. general은 (2000, 1500, 1500, 2000, 0, 1000, 0)(`:1250`).
- Methods는 edges.jsonl 연결 수 내림차순(`:1288-1291`). Papers는 연결 수 상위 15개(`:1341-1342`). Recent edges는 파일 끝 25줄(`:1370-1371`). Stale은 30일 넘은 페이지 10개(`:1378`, `:1398`).
- Failed ideas 절은 status `failed` 또는 `rejected`를 찾는다(`:1314`). `rejected`는 ideas.status enum에 없다(`entities.yaml:84`). `git log -S'"rejected"' -- tools/research_wiki.py` 결과 첫 릴리스 `20c61b9`부터 있었다. 그 뒤 enum이 바뀌며 남은 죽은 분기다.
- 전체가 `max_chars`(기본 8000)를 넘으면 절 단위로 자르고 `...(truncated)`(`:1404-1412`).

`open_questions` 세부:
- 템플릿 섹션 이름에 정확히 의존한다. 정규식 `^##\s+{섹션}\s*$`(대소문자 무시, `:875`).
- 글머리(`-`)로 시작하는 줄만 모은다(`:882-885`). 문단으로 쓴 질문은 빠진다.
- 중복 제거·LLM 요약·출처 위치가 없다. 출처는 `[kind/slug]`까지다.

언제 재생성되나(경계): `/ingest`, `/ask`, `/ideate`, `/exp-design`, `/exp-eval`, `/refine`, `/research`, `/init`이 두 명령을 부른다(`.claude/skills` grep). 읽는 쪽은 그 외 `/novelty`, `/paper-plan`, `/rebuttal`, `/review`, `/survey`도 포함한다. 도구 쪽 자동 트리거는 없다.

### 2.6 lint (`tools/lint.py`)

`lint()`(`:733-750`)가 아래 순서로 돈다. 등급은 🔴(필수)·🟡(경고)·🔵(정보)다. 🔴이 하나라도 있으면 exit 1(`:1166`).

| 검사 | 함수 | 등급 | 자동 수정 | schema 구동 여부 |
|---|---|---|---|---|
| 필수 필드 누락 | `check_missing_fields` `:173-200` | 🔴 | 기본값이 있으면 그 값 삽입 | `REQUIRED_FIELDS`, `FIELD_DEFAULTS` (YAML) |
| 깨진 위키링크 | `check_broken_links` `:203-221` | 🟡 | 없음 | 아님(`[[...]]` 정규식) |
| 고아 페이지(들어오는 위키링크 0) | `check_orphan_pages` `:224-239` | 🔵 | 없음 | 아님 |
| enum·범위 값 | `check_field_values` `:242-279` | 🔴 | 없음 | **부분**. 검사할 필드 목록을 `enum_checks` dict로 코드에 박았다(`:251-258`). novelty_score 범위도 코드다(`:267-277`) |
| 조건부 필수 | `check_required_when` `:282-310` | 🔴 | 없음 | YAML |
| 단일 link 대상 존재 | `check_link_field_targets` `:313-340` | 🟡 | 없음 | YAML(`type: link`만. list_link는 안 봄) |
| 역링크 비대칭 | `check_xref_asymmetry` `:451-498` | 🟡 | 있음(`_fix_xref` `:835-890`) | YAML(xref.yaml) |
| edges.jsonl 일관성 | `check_graph_edges` `:518-604` | JSON 깨짐 🔴, 나머지 🟡 | 없음 | YAML |
| citations.jsonl 일관성 | `check_graph_citations` `:607-681` | JSON 깨짐·필드 누락 🔴, 나머지 🟡 | 없음 | 일부 |
| 내용 품질 | `check_content_quality` `:684-730` | 🔵 | 없음 | 아님(importance=5 논문을 개념이 안 가리킴, stable 개념의 key_papers ≤1, 빈 Open problems) |

lint가 보지 않는 것(코드 근거):
- list_link 값이 맞는 종류를 가리키는지(`to`). `check_link_field_targets`는 `type: link`만 본다(`:329-330`).
- date 형식, int/str 타입, slug 규칙. `conventions.yaml`의 `slug_rule`은 어디서도 쓰지 않는다(1.7).
- 개념·방법 중복. 이것은 `/check` skill의 LLM 단계가 맡는다(경계).
- 파생물이 최신인지. 이슈 #41 메인테이너 답변: "no process **validates** whether they've fallen out of sync. Manual wiki edits bypass rebuild triggers entirely, and there's no staleness detection."

lint 내부의 구멍(코드 추적, 실행 안 함):
1. 블록형 리스트를 forward로 인식하지 못한다. `_extract_forward_targets`(`:363-406`)는 `extract_frontmatter_value`가 빈 값이면 `_extract_list_field_slugs`(`:343-360`, 흐름형 `field: [...]`만)로 간다. `field:\n  - a` 형태는 아무것도 못 뽑는다. 이슈 #20("regex only matches inline YAML list form, so it misses block-form origin_gaps")이 2026-05-06에 닫혔지만, 이슈에 제안된 `extract_frontmatter_list` 헬퍼는 지금 코드에 없다.
2. 여러 개짜리 위키링크 리스트(`key_papers: [[a]], [[b]]` 꼴)를 바르게 쪼개지 못한다. `extract_frontmatter_value`는 바깥 `[`·`]`만 반복해서 벗긴다(`:155-156`). `_extract_list_field_slugs`의 `\[(.*?)\]`는 첫 `]`에서 멈춘다(`:354`). skill 문서는 `key_papers: [[paper-P]]` 꼴을 쓰라고 한다(`.claude/skills/ingest/references/cross-references.md:13`). 같은 문제가 `research_wiki._parse_scalar`(`:2109-2113`) + `_clean_link_slug`(`:553-567`)에도 있어 `projected_edges`의 slug가 `a]`·`[b`처럼 깨질 수 있다.
3. 본문 섹션 forward 규칙이 섹션을 무시한다. `sect = forward['body_section']`을 읽고 쓰지 않는다(`:377`). 규칙 1("papers `## Related` → concepts")은 실제로 "papers 본문·frontmatter 어디든 concepts로 가는 위키링크"를 센다.
4. 역링크 존재 판정이 부분 문자열이다. `source_slug in body`(`:438-439`), `source_slug in match.group(1)`(`:420`). slug `lora`는 `lora-v2`가 있으면 있다고 본다.
5. 자동 수정이 쓰는 형식과 다른 검사가 읽는 형식이 다르다. `_append_slug_to_fm_list`는 맨 slug(`[a, b]`)를 붙인다(`:962`, `:973`). 그러나 깨진 링크·고아 검사는 `[[...]]`만 센다(`:58`, `:212`). 그래서 `--fix`로 채운 frontmatter 역링크는 고아 판정에서 들어오는 링크로 세지 않는다.
6. 블록형 리스트에는 자동 수정을 거부한다. 주석 "Refuse to convert a block-style list — too risky without a real YAML parser"(`:968-972`).
7. `find_all_pages`가 slug만 키로 쓴다(`:160-170`). 두 종류에 같은 slug가 있으면 뒤의 것이 앞을 덮는다. 위키링크 `[[slug]]`도 종류 없이 풀린다. 프런트는 같은 문제를 우선순위 표로 푼다(`app/modules/schema.js:19-25` `TYPE_PRECEDENCE`).
8. frontmatter 파서가 도구마다 다르다. `research_wiki._parse_yaml_block`(`:2155`), `lint.extract_frontmatter`(`:114-141`), `visualize._parse_yaml_block`(`visualize.py:151`), `discover.py`의 줄 정규식(`:428-430`), `backfill_citations._parse_arxiv_id`(`:37-54`), `hiera/adapter._fallback_frontmatter`. 같은 파일을 도구마다 다르게 읽을 수 있다.

lint를 언제 돌리나(경계): `/check`(수동)와 `/init` fan-in(`.claude/skills/init/...`). 자동 수집 CI는 lint를 돌리지 않는다. 이슈 #41 메인테이너: "Our daily-arxiv CI workflow auto-commits wiki changes without running /check at all." `.github/workflows/daily-arxiv.yml`에도 lint 단계가 없다(grep).

### 2.7 병렬 ingest를 받치는 장치

`/init`은 논문마다 git worktree를 하나씩 만들고 그 안에서 `/ingest`를 돌린 뒤 순서대로 merge한다(`.claude/skills/init/references/parallel-ingest.md:24-67`, 다른 갈래). 도구 쪽 장치:

| 장치 | 위치 | 하는 일 |
|---|---|---|
| append-only JSONL + `merge=union` | `.gitattributes` | `log.md`, `edges.jsonl`, `citations.jsonl`, `index.md`를 merge할 때 양쪽 줄을 모두 남김 |
| `dedup-edges` | `research_wiki.py:711-751` | merge 뒤 `(from,to,type)` 중복 제거, 깨진 JSON 줄은 보존 |
| `dedup-citations` | `:754-784` | `(from,to)` 중복 제거 |
| worktree 안 재생성 거부 | `:791-818` | `git rev-parse --git-dir` ≠ `--git-common-dir`면 `rebuild-context-brief`·`rebuild-open-questions`가 exit 2 |
| checkpoint | `:2452-2578` | `wiki/.checkpoints/<task>.json`에 완료·실패 목록과 메타데이터(예: stash ref) |
| 결정적 slug | `:105-129` | 같은 제목 → 같은 slug |

문서와 코드가 다른 곳: `ingest/references/init-mode.md:34` "Collisions are resolved by numeric suffix via the tool, not by ad-hoc renaming." `slugify`에는 기존 파일을 보는 코드도 숫자 접미사 코드도 없다(`:105-129`, `grep suffix` 결과 없음).

`compile_context` 자체(`--for ideation` 등)에는 worktree 가드가 없다. 가드는 `rebuild_context_brief` 별칭과 `rebuild_open_questions`에만 있다(`:823`, `:839`).

### 2.8 웹 프런트의 쓰기 경로 (`tools/serve.py`)

- stdlib `ThreadingHTTPServer`, 기본 `127.0.0.1:8765`(`:1046`, `:1054`). "loopback-only"(`:21`)는 기본 host 값일 뿐 `--host`로 바꿀 수 있고 인증은 없다.
- 쓰기 API는 모두 같은 CLI를 subprocess로 부른다: PATCH 엔티티 → `set-meta`, POST edges → `add-edge`, POST citations → `add-citation`, POST regenerate → `rebuild-*`, POST `/api/lint/fix` → lint(`:21-36`, `:586-720`).
- 성공한 쓰기마다 `log.md`에 `frontend | <verb> <subject>`를 남긴다(`:149-155`). 사람 이름은 남지 않는다.
- skill은 웹에서 실행하지 않는다. `/api/intent/{skill}`은 붙여 넣을 `/skill ...` 명령 문자열만 돌려준다. 이유(`:42-52`): "Naive UX would silently call a different code path and produce results that diverge from /skill X's actual behavior. ... The boundary is explicit in the API surface itself — no silent skill faking."
- `/api/graph`는 edges.jsonl + 실시간 frontmatter 투영 + citations.jsonl을 합쳐 준다(`:503-530`). 엣지 메타는 loader의 `EDGE_TYPE_SPECS`에서 뽑아 보낸다(`:533-551`). 이유: "without hardcoding a parallel copy of runtime/schema/edges.yaml"(`:534-535`).
- 실시간 갱신: 1.5초마다 `wiki/` 아래 파일 mtime을 훑어 SSE로 알린다(`:53-60`, `:211-226`).

### 2.9 외부 수집: `discover.py`, `fetch_*.py`

- `discover.py`는 후보 논문 shortlist를 만든다. 네 모드: from-anchors, from-topic, from-wiki, from-venue(`:1-24`). LLM 호출 없음.
- 위키 중복 제거: 위키 논문의 arxiv ID(버전 접미사 제거)와 정규화 제목으로 거른다(`:426-520`). `_title_key`는 `一-鿿`(한자)만 남기고 한글은 지운다(`:463-465`).
- venue 모드는 위키 문서(papers·concepts·topics)로 BM25 색인을 만들어 후보의 "위키 관련도"를 잰다(`:523-677`). 제목 4.0, frontmatter 1.5, 본문 1.0 가중, k1=1.2, b=0.75, 상위 3개 문서 점수를 0.5 비율로 줄여 더하고 `1-exp(-x/8)`로 0~1에 맞춘다(`:667-670`). 어휘가 20개 미만이면 거부한다(`:1029-1032`). 점수 식은 `0.50*rel + 0.20*influence + 0.15*fresh + 0.10*rating + 0.05*status`(`:808-821`).
- 이 BM25는 "어느 외부 논문을 넣을까"에만 쓴다. 새 페이지를 기존 페이지와 잇는 데는 쓰지 않는다.
- `fetch_s2.py`: 요청 전 1초(API 키 있음) 또는 3초 대기, 429면 60·120·180초 기다리며 3회 재시도, 그 뒤 RuntimeError(`:49-80`). 다른 HTTP 에러는 바로 raise(`:78`).
- `fetch_wikipedia.py`: 404면 exit 2, 네트워크·파싱 오류는 exit 3(`:13-16`). `/prefill`이 404일 때 LLM 지식으로 대체한다(commit `f6f34fc` 본문 "falls back to LLM knowledge on 404").
- `fetch_deepxiv.py`: SDK가 없으면 조용히 빠진다(`:26-50`, `discover.py:45-49`).

### 2.10 `wiki2dag.py`는 위키 그래프 도구가 아니다

이름과 달리 LaTeX 논문 디렉터리(`paper/main.tex`, `sections/*.tex`, `figures/`)를 PaperX 포스터 파이프라인용 `dag.json`으로 바꾼다(`wiki2dag.py:1-23`). 노드는 루트(제목·저자)·섹션·그림 세 단계다(`:6-18`, `:1022-1033`). 위키 페이지를 읽지 않는다. docstring "This bridge is LaTeX-only. Wiki entity enrichment happens in the /poster SKILL.md"(`:20-22`). `/poster` skill이 부른다(`.claude/skills/poster/SKILL.md:110`). commit `1fd1e58`(v1.4.0)에서 들어왔다. 엔터프라이즈 위키 설계와는 관계가 없다.

### 2.11 `tools/hiera/` — 실험 탐색 사이드카

- "deliberately sidecar-only: it owns ``runs/hiera`` artifacts and never writes wiki files"(`hiera/__init__.py:1-6`).
- 위키에서 experiment와 linked idea 페이지를 읽고(`adapter.py:101-163`) 원본 파일 sha256을 `wiki_snapshot`으로 남긴다(`:166-173`). 평가 전에 원본이 바뀌었으면 거부한다(`evaluator.py:109-117`).
- 기록은 `ledger.jsonl`에 append하고, 이벤트 번호를 연속으로 검사하며, 쓸 때 잠금 파일을 만든다(`ledger.py:25-60`, `common.py:163`).
- 위키 본체(`research_wiki.py`)에는 이런 잠금·원본 해시가 없다. 같은 저장소 안에서 나중에 들어온 코드(commit `40f5220`, 2026-09-28)가 더 엄격하다.

### 2.12 LLM 호출 지점 (이 갈래 범위 안)

- `research_wiki.py`, `lint.py`, `loader.py`, `discover.py`, `serve.py`, `backfill_citations.py`, `reset_wiki.py`, `visualize.py`, `wiki2dag.py`: LLM 호출 없음(grep `anthropic|openai|chat/completions` 결과 없음).
- `tools/daily_arxiv.py:1231-1287` `_call_openai_compatible`(범위 밖이라 이 부분만 읽음): OpenAI 호환 API에 `response_format: json_object`로 추천 판정을 받는다. 400대 응답이면 `response_format`을 빼고 한 번 더, 실패하면 fallback 모델로 넘어간다. 결과는 `_normalize_llm_decisions`(`:1182-1230`)가 허용된 arXiv ID만 남기고, enum 밖 값은 기본값으로 바꾼다. 시스템 프롬프트 "This is inform mode: never select or request ingestion."이고 `ingest` 판정은 `strong_recommend`로 강등한다(`:1196-1197`).
- `mcp-servers/llm-review/server.py`: 교차 모델 리뷰용(읽지 않음, 다른 갈래).
- 위키 내용을 만드는 LLM 호출은 전부 Claude Code 세션 안의 skill 프롬프트다. 도구는 그 LLM이 Bash로 부르는 결정적 함수 묶음이다. 이슈 #11 메인테이너: "we're working to make skills leaner and introduce coded tools to replace LLM reasoning where possible."

### 2.13 실패·재시도 처리 요약

| 자리 | 처리 |
|---|---|
| 엣지 쓰기 | 규칙 위반이면 JSON 에러 + exit 1. 재시도는 호출한 LLM 몫. batch는 전부 아니면 전무 |
| 끝점 페이지 없음 | 경고만, 그대로 씀 |
| frontmatter 파싱 실패 | 빈 dict로 취급(`_parse_frontmatter` `:2143-2150`). 질의에서 조용히 빠진다 |
| JSONL 깨진 줄 | 읽을 때 건너뜀(`load_edges` `:704-707`). dedup은 보존(`:745-746`). lint는 🔴 |
| checkpoint 깨짐 | 쓰기 경로는 조용히 비우고 다시 씀, `checkpoint-load`는 `"corrupt checkpoint"`를 알림(`:2456-2489`, `:2560-2566`) |
| S2 429 | 60/120/180초 대기 3회 |
| worktree 안 재생성 | exit 2 |
| serve 감사 기록 실패 | 무시하고 쓰기는 성공 처리(`:149-155`) |

---

## 3. 설계 결정과 이유

각 항목: 결정 → 이유(작성자 원문이면 (a), 추론이면 [추정]) → 생각할 수 있던 대안 → 이력.

### 3.1 schema를 YAML로 두고 loader가 import 시점에 읽는다 (코드 생성 없음)

- (a) commit `1b2df1f` 본문: "Eliminate the codegen pipeline and its derived docs: delete tools/_schemas.py (-321 lines) ... Make consumers data-driven (zero hardcoded entity/edge name lists)". `runtime/CLAUDE.md:21` "Every change below is **YAML-only, zero Python change**."
- (a) 그 전 단계 이유: commit `1fc7738` "Schema constants (ENTITY_DIRS, VALID_EDGE_TYPES, REQUIRED_FIELDS, VALID_VALUES, FIELD_DEFAULTS) were duplicated between lint.py and research_wiki.py — extracted to tools/_schemas.py as single source of truth."
- 이력: 두 도구에 상수 중복(초기) → `tools/_schemas.py`(`1fc7738`, 2026-04-12) → `runtime/*.yaml` + `loader.py`(`1b2df1f`, 2026-05-06).
- 대안: Python 상수 파일(이전 방식), JSON Schema + 생성 코드, Pydantic 모델.
- 실제로 남은 Python 하드코딩(코드 근거): lint enum 목록(`lint.py:251-258`), experiments.outcome의 빈 값 허용(`loader.py:74-75`), transition 전제 조건(`research_wiki.py:1640-1659`), legacy 엣지 집합(`loader.py:56-58`), `CONTEXT_BUDGETS`, 프런트 종류 목록(`app/modules/schema.js:11-14`), `config/visualize.json`의 엣지 이름 목록. 그래서 "YAML만 고치면 된다"는 말은 페이지 종류·필드·엣지 종류 추가에는 맞고, enum 검사·전이 조건·저장 위치에는 맞지 않는다.
- 참고: `origin/paper` 브랜치 commit `fefa4df` 본문 "lint enum validation made schema-driven"으로 lint 쪽 하드코딩은 그 브랜치에서 고쳤다. main에는 아직 들어오지 않았다.

### 3.2 엣지는 쓰기 직전 도구가 거부하고, 페이지는 사후 lint로만 잡는다

- (a) 엣지 쪽: `ingest/references/cross-references.md:45`, `:76` "The tool rejects missing confidence/evidence and legacy ... edge types"(경계 문서). `research_wiki.py:249` docstring "Hard validation for new writes. Legacy graph rows remain lint-readable."
- 페이지 쪽 이유는 적힌 곳이 없다. 모르는 것: 왜 페이지 쓰기 도구를 두지 않았는지. 이슈·PR 토론에서 찾지 못했다. [추정] LLM이 Write 도구로 본문 전체를 한 번에 쓰는 흐름을 유지하려고 페이지는 도구 밖에 뒀다(근거 사례: frontmatter를 고치는 `set-meta`조차 schema 검사를 하지 않음 `:2404-2443` 1건, skill이 페이지를 "CREATE (new) or EDIT"로 직접 쓰라고 함 `ingest/SKILL.md:47` 1건).
- 대안: 페이지 생성도 `create-page --kind --fields-json` 같은 도구로만 하게 하고 schema 검사.
- 이력: edges의 hard reject는 v1.1.0 이후 `d89cc72`에서 legacy 처리와 함께 다듬어졌다(`git log -S LEGACY_PAPER_CONCEPT_EDGE_TYPES` → `b36c1df`, `1b2df1f`).

### 3.3 쓰기 권한표(writers.yaml)는 명세일 뿐 강제하지 않는다

- (a) `writers.yaml:3-14`: "STATUS: SPEC, NOT A RUNTIME GATE. ... We deliberately did not plumb a `--skill` arg through set-meta / add-edge: research workflows are fluid, and `/edit` exists as a designed escape hatch for 'per user request' overrides — runtime enforcement here would either fight `/edit` or grow a long exception list. When this file disagrees with reality, update the file (or the offending SKILL.md) — do not add runtime checks."
- (a) 정체성 필드에 대한 단서: "if you ever want a hard runtime lock, put it in tools/research_wiki.py::set_meta as a data-integrity check, not as a permission check driven by this file."(`:22-25`)
- 이력: v1.1.0(`1b2df1f`)에서 "declared writer permissions (advisory)"로 들어왔고, 같은 commit이 "7 entries in writers.yaml whose declared writer did not match the skill's actual SKILL.md behavior"를 고쳤다. 즉 명세와 실제가 이미 7곳에서 어긋났었다.
- 대안: CLI에 `--actor` 인자를 받아 표로 거부, 또는 정체성 필드만 동결.

### 3.4 그래프는 페이지 frontmatter와 별도의 JSONL에 둔다 (의미 엣지 / 서지 인용 / frontmatter 투영 세 갈래)

- (a) 서지 인용 분리: `add_citation` docstring "Append a deterministic bibliographic paper citation"(`:379`). [추정] LLM 판단 엣지(confidence·evidence 필수)와 외부 ID로 기계적으로 생기는 인용을 섞지 않으려는 분리다(근거 사례: citations에는 confidence가 있으면 lint가 경고 `lint.py:654-657` 1건, cites는 `EDGE_TYPE_SPECS`에서 빠짐 `loader.py:110` 1건).
- (a) frontmatter 투영: `project_frontmatter_edges` docstring "type: fm_<field> (fm_ prefix avoids collision with edges.yaml)"(`:593`), `:668-672` "fm_<kind>_<field> disambiguates fields that share a name across entities ... adding a new entity that uses the same field name never collides". 들어온 commit은 `d89cc72` "project frontmatter links into graph edges and expose them through the SPA graph".
- (a) JSONL·append 이유: `.gitattributes` 주석 "When 10 parallel subagents ... write to these files in their own git worktrees ... git's default line-based merge sees concurrent appends ... `merge=union` is git's built-in driver for exactly this case". `ingest/references/init-mode.md:35` "Never lock or in-place-rewrite a shared file."
- 결과(코드 근거): 세 갈래를 합쳐 보는 곳은 `serve.py /api/graph`뿐이다(`:503-530`). `neighbors`(`:1192`), `query orphans`(`:1158`), `compile_context` 연결 수(`:1256`)는 edges.jsonl만 본다. 그래서 frontmatter로만 이어진 연결(예: concept.key_papers)은 CLI 그래프 탐색에 안 잡힌다.
- 대안: 그래프 DB, 페이지 frontmatter만을 원본으로 두고 그래프는 매번 투영.

### 3.5 개념은 "만들기 전에" 결정적 별칭 대조를 거친다

- (a) commit `5f904b1` 본문 "Production incident (test6, 15 papers): /init parallel run produced 45 claims (4 expressing the same 'LLM prompts beat human prompts' proposition) and 37 concepts (3 for 'LLM as gradient', 2 for 'LLM as evolutionary operator'). Cause: every subagent did concept/claim dedup from memory, which silently fails on paraphrase." 해법: "find-similar-concept ... No LLM — high recall, caller does final semantic judgment from a top-k list."
- (a) 코드 주석: "Designed to be invoked from /ingest BEFORE any concept is created, to prevent the 'subagent A and subagent B both create textual-gradient-descent under different slugs' failure mode."(`:965-967`)
- 대안: 임베딩 유사도, LLM에게 전체 목록을 주고 판단, 생성 뒤 일괄 병합.
- 이력: 같은 commit에 `find-similar-claim`(동의어 표·태그 가중 포함)도 있었으나 claims 종류를 지우면서 v1.1.0에서 삭제(CHANGELOG `:62` "removes `find-similar-claim`, `query weak-claims`, `query evidence-for`").
- 모르는 것: 0.40/0.80/0.85 문턱과 Jaccard 구간 식의 근거. 보정 데이터가 commit·이슈 어디에도 없다. 이슈 #42 메인테이너 "To our knowledge, there is no such benchmarks to measure the performance of LLM-wiki".

### 3.6 foundation은 terminal 종류이고 대조 결과에서 맨 앞에 온다

- (a) commit `f6f34fc` "foundations/ — background knowledge pages seeded by /prefill. Terminal by design: receives inward links from papers/concepts/etc., writes no reverse link." "Excluded from research-maturity totals (background != research output)."
- (a) 정렬: `research_wiki.py:1112-1113` "foundations with high score first (they're terminal — prefer them)". `:969-973` "so that /ingest cannot accidentally create a concept that duplicates an existing foundation page".
- (a) 고아 판정에서는 빼지 않는다: `lint.py:228-232` "Foundations are NOT exempt: ... An orphan foundation is a real signal — either /prefill seeded background that no paper references, or /ingest is failing to dedup against it."
- 이력: `origin/paper` 브랜치 commit `fefa4df` "foundation grounding: concepts/methods.grounded_in; foundations no longer terminal", `contributes_to_foundation` 엣지 추가, `terminal_targets: []`. 즉 논문용 브랜치에서는 이 결정을 뒤집었다. 뒤집은 이유는 그 commit에 "foundation grounding" 외에 적혀 있지 않다.
- 대안: 빈도 기반 stoplist, 허브 노드 가중치 낮추기, 탐색 시 terminal 경유 경로 제외.

### 3.7 context_brief·open_questions는 매번 통째로 다시 만든다 (LLM 없이)

- (a) `compile_context` docstring "Replaces the old one-size-fits-all rebuild_context_brief with budget allocations tuned per skill category."(`:1266-1269`)
- (a) 병렬 ingest에서 이 두 파일만 문제가 된 이유: commit `46cad0d` "These files are full rebuilds, not append-only, so they can't be merge=union'd; parallel /init subagents running them in their worktrees produced add/add merge conflicts on Phase B fan-in (issue #12)." "The guard is defense-in-depth against subagent prompt drift — init/SKILL.md already tells agents to SKIP these commands in INIT MODE, but that relied on prompt discipline alone."
- (a) open_questions 출처 변경: claims를 지우면서 "open_questions now collects from papers (## Open questions), topics (## Open problems including ### Known/Methodological gaps), and concepts (## Open problems). Context-brief replaces Claims budget with Methods."(`1b2df1f`)
- [추정] 통째 재생성을 고른 것은 파생물을 손으로 고치지 못하게 해서 원본(페이지)과 어긋날 일을 없애려는 것이다(근거 사례: 두 파일 머리말 "_Auto-generated ... Do not edit._" `:164`, `:166` 2건). 다만 재생성 트리거가 skill 프롬프트에만 있어 사람이 직접 고친 뒤에는 낡는다(이슈 #41 답변).
- 대안: 페이지별 해시를 기록해 바뀐 것만 갱신, 또는 읽을 때마다 즉석 계산.

### 3.8 역링크는 "같은 턴에 같이 쓰기"가 원칙이고, 빠지면 lint `--fix`가 결정적으로 채운다

- (a) 루트 `CLAUDE.md` Hard Rule 4 "Forward link → write reverse simultaneously. Rules in `runtime/schema/xref.yaml`." `xref.yaml:1-3` "Whenever entity A writes a forward link to entity B, the reverse update on B is required."
- (a) 메인테이너 근거(이슈 #42): "A human maintaining 200+ interlinked markdown files will inevitably let reverse links and cross-references decay."
- (a) 자동 수정이 구조화 payload로 도는 이유: `LintIssue` docstring "lets a fixer dispatch on schema metadata ... instead of regex-parsing the human-readable message back into structure"(`lint.py:62-71`).
- 이력: 하드코딩 5+ 분기 → `check_xref_asymmetry` 일반화(`1b2df1f` "generic check_required_when, check_link_field_targets, check_xref_asymmetry replace 5+ hardcoded branches"). 이슈 #20의 블록형 리스트 문제는 그 뒤에도 남아 있다(2.6 구멍 1).
- 대안: 역링크를 저장하지 않고 질의 시점에 계산(backlink index).

### 3.9 병렬 수집은 잠금 대신 git worktree 격리 + union merge + 사후 중복 제거

- (a) commit `070d5e1` "Replace sequential subagent ingest with parallel execution ... Fan-in phase: sequential git merge of worktree branches ... Estimated speedup: ~3-5x for 10-paper inits (40 min → 8-12 min)". `dedup-edges` docstring "multiple agents may have added identical edges in their isolated worktrees"(`:714-716`).
- (a) "Never lock or in-place-rewrite a shared file."(`init-mode.md:35`)
- 대안: 단일 쓰기 큐(한 프로세스만 그래프를 씀), 파일 잠금, DB 트랜잭션.
- 걸리는 점(코드 근거): worktree 밖에서 동시에 두 프로세스가 `add-edge`를 부르면 잠금이 없다(`:350-351`). `set-meta`는 읽고-고치고-통째 쓰기라 동시 쓰기에서 한쪽 변경이 사라질 수 있다(`:2411-2438`). [추정] 이 설계는 "한 사람이 한 세션에서 쓰거나, 병렬일 때는 반드시 worktree"를 전제한다(근거 사례: worktree 가드 `:791-818` 1건, merge=union 4파일 1건, hiera ledger만 잠금을 씀 `ledger.py:56` 1건).

### 3.10 웹 프런트는 skill을 흉내 내지 않고 명령 문자열만 돌려준다

- (a) `serve.py:42-52` 위 2.8 인용.
- (a) 프런트가 schema를 따로 들고 있지 않게: `:534-535` "without hardcoding a parallel copy of runtime/schema/edges.yaml". 그러나 `app/modules/schema.js:1-14`는 종류 목록을 복제해 두고 "extend it here in one place"라고 한다. 엣지 색·묶음은 서버 값 우선, 로컬 상수는 fallback(`d89cc72` "Use server-provided edge workflow metadata as the graph color source of truth, with local schema constants only as fallback").

### 3.11 claims 종류를 지우고 methods 종류를 만들었다

- (a) 이슈 #31(PR #32/#33): "`claims` 和 `ideas` 语义重叠（两者都是「可验证的命题」），同时更有价值的 `methods`（跨论文复用的具名技术）没有实体 —— 目前只是加入 paper 的 `## Method` 章节。" (뜻: claims와 ideas가 둘 다 "검증 가능한 명제"라 의미가 겹치고, 더 가치 있는 methods(여러 논문에서 재사용되는 이름 있는 기법)는 종류가 없이 논문의 `## Method` 절에만 있었다.)
- (a) methods를 뽑는 조건: "只在「具名 + 可复用 + 可 cite」时抽出 method 实体" (뜻: 이름이 있고, 재사용되고, 인용할 수 있을 때만 method 페이지를 뽑는다).
- 이력: v1.1.0 `1b2df1f`, CHANGELOG `:52`. 마이그레이션은 하지 않았다(CHANGELOG `:67`).
- 엔터프라이즈 관점 참고: "주장(claim)" 종류를 없앤 결정은 연구용 맥락(아이디어가 곧 검증할 명제)에 맞춘 것이다. 보고서 위키에서 "누가 무엇을 주장했나"를 잇고 싶다면 이 결정은 그대로 가져올 근거가 약하다.

### 3.12 논문↔논문 의미 엣지 8종을 4종으로 줄였다

- (a) `edges.yaml:17-23`: "The 4 removed in this round (improves_on / compares_against / surveys / complementary_to) were judged redundant: improves_on ⊆ builds_on (subset; merged); compares_against ⊆ cites (every comparison already cites); surveys ⇐ papers.contribution_type contains 'survey' (derivable); complementary_to ≈ same_problem_as (boundary fuzzy in practice)".
- 이력: commit `d89cc72`(PR #60, 2026-05-26).
- 대안: 세분화 유지 + 상위 종류로 묶기(계층형 관계).
- [추정] 줄인 기준은 "다른 엣지·필드에서 유도할 수 있으면 없앤다"와 "LLM이 경계를 일관되게 못 긋는 둘은 합친다"다(근거 사례: 위 4개 사유 원문 중 유도 가능 2건, 포함 관계 1건, 경계 모호 1건).

### 3.13 lint는 등급(🔴/🟡/🔵)과 "결정적인 것만 자동 수정" 원칙

- (a) `/check` 쪽 원칙(경계, 앞선 보고서 인용 `check/SKILL.md:174`): `--fix`는 결정적 문제만, 나머지는 사용자 승인으로.
- (a) 코드: `fix_issues`는 `xref-asymmetry`와 `missing-field`만 고친다(`lint.py:815-832`). 기본값이 없는 필수 필드는 "needs manual value"(`:189-190`).
- [추정] 자동 수정을 두 종류로 묶은 것은 손으로 짠 YAML 편집이 위험해서다(근거 사례: 블록형 리스트 변환 거부 주석 `:968-972` 1건, 비어 있지 않은 흐름형 리스트를 블록형으로 바꾸기 거부 `:1028-1032` 1건).

### 3.14 PyYAML 없이 손으로 짠 frontmatter 파서

- (a) `research_wiki.py:2156` "Parse a block of YAML text into a dict (no PyYAML dependency)."
- 그런데 loader는 v1.1.0부터 PyYAML을 쓴다(`loader.py:27`, commit `1b2df1f` "Add PyYAML>=6.0 to requirements.txt (loader dependency)"). 그래서 "의존성 없음"이라는 이유는 지금은 성립하지 않는다.
- 모르는 것: 페이지 파서를 PyYAML로 바꾸지 않은 이유. [추정] 이력상 손 파서가 먼저 있었고 바꾸지 않았을 뿐이다(근거 사례: 손 파서는 `20c61b9` 첫 릴리스부터, PyYAML은 `1b2df1f`부터 1건).

### 3.15 테스트를 지웠다

- 첫 릴리스 "2125 tests"(CHANGELOG `:86`), `5f904b1` "All 2300 tests passing", `1fc7738` "2327 tests passing".
- commit `b36c1df` "Rebuild ingest. Deleted tests." — `tests/test_research_wiki.py` 2000줄, `test_lint.py` 795줄 등 삭제. 이유 원문은 제목뿐이다.
- 지금 main: `tests/test_hiera_local.py` 1개(88줄), `.sleepcode/tests/test_discover_from_venue.py` 1개(417줄, v1.3.0).
- 모르는 것: 왜 지웠는지. PR #23/#26 본문을 보면 알 수 있을 수 있다(`gh pr view 23 -R skyllwt/AutoSci`, 이번에는 열지 않음).

### 3.16 `/discover` venue 모드는 위키에 아무것도 쓰지 않는다

- (a) CHANGELOG `:41` "Venue mode is stricter than other `/discover` modes: it does **not** write to `wiki/` at all, including `wiki/log.md`. Sparse wikis (< 20 unique relevance terms) fail with an actionable error rather than returning an unpersonalized ranking."

### 3.17 hiera는 위키에 쓰지 않는 사이드카

- (a) `hiera/__init__.py:3-5` "deliberately sidecar-only ... never writes wiki files. Formal validation remains an explicit handoff to the existing experiment workflow."

---

## 4. 앞선 schema-glossary 보고서와 어긋나거나 보태는 점

대상: `llm-wiki-implementations/lab/reports/schema-glossary/autosci-omegawiki-schema.md`(같은 commit). 대부분 코드와 맞는다. 아래는 다르거나 빠진 것이다.

| # | 앞선 보고서 | 이번에 본 것 | 근거 |
|---|---|---|---|
| 1 | schema는 "YAML-only, zero Python change"로 강제된다는 인상(#A) | 페이지 종류·필드·엣지 추가는 YAML만으로 되지만, lint enum 검사 목록·novelty 범위·outcome 빈 값·전이 전제 조건·저장 위치는 Python에 박혀 있다. 새 enum 필드를 YAML에 추가해도 lint는 검사하지 않는다 | `lint.py:251-258`, `:267-277`, `loader.py:74-75`, `research_wiki.py:1640-1659`, `:300`, `:388` |
| 2 | `conventions.yaml`을 schema 파일로 소개 | 코드가 읽지 않는다(import만). `edge_storage`·`slug_rule`·`log_grammar` 모두 효과 없음 | `research_wiki.py:73`, grep 결과 |
| 3 | "역링크: 빠지면 `/check --fix`가 결정적으로 채운다"(#D 7) | 흐름형 리스트·단일 위키링크일 때만이다. 블록형 리스트는 검출도 수정도 안 되고(이슈 #20이 닫혔지만 코드에 남음), 여러 개 위키링크 리스트는 잘못 쪼갤 수 있고(코드 추적), 본문 섹션 규칙은 섹션을 무시하며, 존재 판정은 부분 문자열이다 | `lint.py:343-406`, `:377`, `:438-439`, `:968-972` |
| 4 | 엣지 구멍은 "끝점 페이지 없음 경고"와 legacy 두 개 | 하나 더: `*` endpoint 엣지는 `/` 없는 ID도 경고 없이 받는다 | `research_wiki.py:204-215` (코드 추적) |
| 5 | (언급 없음) | `find-similar-concept`·`slugify`가 `[^a-z0-9\s]`로 정규화해서 한글 이름은 점수 0, slug는 `untitled`가 된다. discover의 제목 키도 한자만 남기고 한글을 지운다 | `research_wiki.py:120`, `:987`, `:999`, `:1015-1016`, `discover.py:463-465` (코드 추적) |
| 6 | Jaccard 주석과 코드가 다르다 | 맞다. 덧붙임: 처음 도입한 commit `5f904b1`부터 본문·주석·코드가 이미 달랐다. 나중에 바뀐 것이 아니다 | `git show 5f904b1:tools/research_wiki.py` 551-555 |
| 7 | foundation 계층은 허브를 그래프에서 막지 못한다(#F) | 맞다. 덧붙임: `neighbors`는 edges.jsonl만 보므로 frontmatter 링크(key_papers 등)로 생긴 연결은 아예 탐색에 안 들어간다. 또 `origin/paper` 브랜치는 foundation을 terminal에서 빼서(`fefa4df`) 이 계층 설계를 스스로 뒤집었다 | `research_wiki.py:1192`, `git show origin/paper:runtime/schema/xref.yaml` 끝 `terminal_targets: []` |
| 8 | tests는 hiera 하나뿐(#H) | 맞다. 덧붙임: 2000줄짜리 `test_research_wiki.py`, 795줄 `test_lint.py` 등이 `b36c1df`에서 이유 없이 지워졌다. `.sleepcode/tests/`에 discover 테스트 1개가 더 있다 | `git show --stat b36c1df` |
| 9 | (언급 없음) | 문서는 slug 충돌을 "numeric suffix via the tool"로 푼다고 하지만 그 코드는 없다 | `ingest/references/init-mode.md:34`, `research_wiki.py:105-129` |
| 10 | (언급 없음) | `rebuild_index`는 `title`만 적는다. methods·people은 `name`을 쓰므로 index.md에 이름이 빠진다. skill이 index.md로 기존 slug를 훑는다면(앞선 보고서 `ingest/SKILL.md:36`) 방법 중복 판단에 이름이 없다 | `research_wiki.py:1843-1845`, `entities.yaml:66`, `:106` |
| 11 | "`wiki/graph/`는 derived" 규칙 인용 | edges.jsonl은 페이지에서 재생성할 수 없는 원본이다. reset은 이것을 지운다 | `research_wiki.py` 명령 목록, `reset_wiki.py:205`, `:278-284` |

---

## 5. 엔터프라이즈 다중 작성자 보고서 용도에 비춰

조건 상기: 작성자마다 같은 대상을 다른 용어로 쓴다. 문서가 형식을 갖추지 않을 때가 있다. 여러 사람이 쓴다. 권한이 있다. 목표 원문 "어느정도 사람이 하더라도 성능을 보장(raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조)".

### 5.1 쓸 만한 장치

1. YAML schema → loader → 쓰기 직전 거부(`edges.yaml` + `loader.py:165-220` + `add_edge`). 관계 종류·endpoint·필수 근거(evidence)를 "쓰기 전에" 막는다. 다만 페이지(엔티티) 쪽도 같은 관문을 둬야 한다. AutoSci는 페이지를 사후 lint에 맡겨 구멍이 많다(2.6).
2. 단일 쓰기 경로. 에이전트(skill)와 웹 UI(`serve.py`)가 같은 CLI를 부른다. 사람이 UI에서 고쳐도 같은 검사를 지난다. 여러 사람이 쓰는 환경에서 가장 바로 가져올 만한 구조다.
3. 생성 직전 결정적 대조(`find-similar-concept`) + `match_reason` + 최종 판단은 LLM. 사내 용어집(정식 이름 + 별칭)을 foundations처럼 미리 넣고, 새 용어마다 이 대조를 먼저 거치게 하면 "같은 대상 다른 용어" 문제의 1차 방어선이 된다. 단 한글 정규화를 고쳐야 한다(5.2-1).
4. 서지 인용처럼 "외부 ID로 기계적으로 생기는 연결"과 "LLM이 판단한 의미 연결"을 다른 파일로 나눈 것(`citations.jsonl` vs `edges.jsonl`). 사내에서는 문서 번호·프로젝트 코드·티켓 번호 같은 결정적 키로 생기는 연결을 따로 둘 수 있다.
5. 의미 엣지에 `confidence`·`evidence` 필수. 사람이 검토할 때 "왜 이었나"를 볼 수 있다. 이슈 #41 메인테이너: "You can trace who wrote an edge and when."(단 "who"는 실제로 기록되지 않는다. 5.2-4)
6. 파생 요약을 통째로 결정적으로 재생성(`open_questions`, `context_brief`). LLM 없이 섹션을 긁어 모으므로 비용이 없고 재현된다. 템플릿을 강제할 수 있는 문서 종류에 쓸 만하다.
7. 병렬 수집용 worktree 가드(`_refuse_in_linked_worktree`). "프롬프트로 금지했지만 도구로도 막는다"(commit `46cad0d` "defense-in-depth against subagent prompt drift")는 원칙은 그대로 가져올 만하다.
8. hiera의 원본 해시 스냅샷(`adapter.py:166-189`). 파생물·요약이 어느 원본 버전에서 나왔는지 sha256으로 남기고, 원본이 바뀌면 거부한다. AutoSci 본체가 못 푼 "silent staleness"(이슈 #41)를 푸는 데 그대로 쓸 수 있다.
9. `discover.py`의 위키 BM25 색인(`:562-677`). 지금은 외부 논문 순위에만 쓰지만, 새 보고서가 들어올 때 "기존 위키 중 어느 문서와 가까운가" 후보를 결정적으로 뽑는 데 재활용할 수 있다. IDF를 쓰므로 흔한 용어(허브)의 무게가 자연히 줄어든다.
10. LLM 출력 화이트리스트 정규화(`daily_arxiv._normalize_llm_decisions` `:1182-1230`). 허용된 ID 밖이면 버리고, enum 밖 값은 기본값으로. LLM이 존재하지 않는 페이지를 잇는 것을 막는 작은 패턴이다.
11. 전부 아니면 전무인 batch 쓰기(`batch_edges` `:1804-1808`). 문서 하나에서 나온 엣지 묶음이 반쯤만 들어가는 상태를 막는다.

### 5.2 걸리는 점

1. 한글을 지운다. `[^a-z0-9\s]` 정규화(`research_wiki.py:120`, `:987`, `:999`) 때문에 한글 개념 이름은 대조 점수 0, slug는 `untitled`(코드 추적). 사내 한국어 보고서에 그대로 쓰면 중복 방지가 완전히 꺼지고 slug가 충돌한다. 가져온다면 정규화·토큰화를 유니코드 기준으로 다시 짜야 한다.
2. 형식 없는 문서에 약하다. 원문 연결 단위가 "문서 전체"이고 위치 필드가 없다. `open_questions`는 정확한 H2 섹션 이름과 `-` 글머리에만 반응한다(`:875`, `:882`). 형식 없는 보고서는 이 수집에서 통째로 빠진다. [추정] 형식 없는 문서는 수집 단계에서 템플릿 섹션으로 다시 쓰게 하거나(LLM), 섹션 대신 청크 ID로 원문 위치를 잡는 장치를 따로 둬야 한다(근거 사례: 이 레포는 논문 원문을 청크로 자르지 않고 템플릿 섹션에 요약을 채우는 방식 1건 — 앞선 보고서 #흐름 1단계).
3. 별칭이 개념·foundation에만 있다. methods·people·topics에는 없다(`entities.yaml`). 사내에서는 사람(작성자·담당자)·조직·프로젝트의 별칭 문제가 더 클 수 있다. 별칭 필드를 모든 엔티티 종류에 두는 쪽이 낫다.
4. 권한·작성자 기록이 없다. writers.yaml은 명세일 뿐이고(`writers.yaml:3`), `log.md`에는 skill 이름이나 `frontend`만 남는다(`serve.py:153`). 엣지 행에도 작성자 필드가 없다(`research_wiki.py:338-348`). 다중 작성자·권한 환경에서는 CLI가 actor를 받아 엣지·로그·페이지 변경에 남기고, 정체성 필드 동결을 실제로 거부해야 한다. AutoSci 작성자도 그 자리를 짚었다: "put it in tools/research_wiki.py::set_meta as a data-integrity check"(`writers.yaml:22-25`).
5. 동시 쓰기. 잠금 없음, set-meta는 통째 덮어쓰기(3.9). 여러 사람이 동시에 쓰는 서비스라면 단일 쓰기 큐나 DB가 필요하다. git worktree + union merge는 "배치 수집"에는 맞지만 상시 다중 사용자에는 맞지 않는다.
6. 그래프가 세 갈래로 나뉘고 CLI 탐색은 edges.jsonl만 본다(3.4). "새 데이터와 기존 데이터의 연결고리 발견"을 그래프 탐색에 맡기려면 하나의 질의 계층에서 세 갈래를 합쳐야 한다.
7. 허브 문제. foundation terminal은 역링크만 끊고 BFS는 막지 못한다(앞선 보고서 #F). 사내 문서의 흔한 용어(회사명, 제품명, "보고서")를 허브로 두면 연결 정밀도가 떨어진다. IDF 가중이나 terminal 경유 경로 제외를 탐색에 넣어야 한다.
8. 사후 lint의 신뢰도. 블록형 리스트·다중 위키링크·부분 문자열 판정 등 구멍(2.6)이 있고, 테스트가 지워졌다(3.15). lint를 가져온다면 진짜 YAML 파서로 다시 짜고 테스트를 함께 가져와야 한다.
9. 문턱 값 근거 없음. 0.40/0.80/0.85, 문서당 생성 한도에 보정 데이터가 없다(3.5). 사내 데이터로 다시 재야 한다.

### 5.3 가져온다면의 최소 조합 (이 갈래가 보는 범위에서)

YAML schema + loader + 엔티티·엣지 모두 쓰기 직전 검사 + 단일 쓰기 CLI/API(actor 필수) + 유니코드 대응 별칭 대조(모든 엔티티 종류) + 외부 키 기반 결정적 연결 파일 분리 + 원본 해시로 파생물 신선도 검사. AutoSci에서 그대로 쓸 수 있는 코드는 `loader.py`(237줄)와 `find_similar_concept` 주변(~130줄)이고, 나머지는 설계만 참고한다.

---

## 6. 모르는 것과 확인 방법

1. 페이지 쓰기에 도구 관문을 두지 않은 이유. 확인: PR #33·#60 리뷰 댓글(`gh pr view 33 --comments -R skyllwt/AutoSci`), `origin/paper`의 `trust_guard.py` 도입 commit 본문.
2. 테스트 삭제(`b36c1df`) 이유. 확인: PR #23·#26 본문과 댓글.
3. `find-similar-concept` 문턱·구간 식의 근거. 확인: 실행 로그나 실험 기록. 저장소에 없다. 메인테이너에게 묻는 수밖에 없다(이슈 #42 답변으로 보아 측정 없음 가능성이 크다).
4. 실제 위키 데이터에서 frontmatter 리스트를 흐름형·블록형·위키링크형 중 무엇으로 쓰는지. 이 형식에 따라 2.6의 구멍이 실제로 터지는지가 갈린다. 확인: `assets/papers/*.pdf`로 공개된 결과물의 위키(공개돼 있다면)나 `8e6af2d`에 섞여 들어온 ingest 결과 diff(`git show 8e6af2d -- wiki/`).
5. (해결) `compile_context`의 `rejected`는 첫 릴리스 `20c61b9`부터 있었다. 첫 릴리스 당시 ideas.status에 `rejected`가 있었는지는 확인하지 않았다(`git show 20c61b9:CLAUDE.md` 등으로 확인 가능).
6. 코드 추적으로만 적은 판단(한글 정규화, 다중 위키링크 파싱, `*` 엣지의 `/` 없는 ID 수용)은 실행해 보지 않았다. 확인: 레포 밖 임시 디렉터리에서 해당 함수를 불러 보는 실험(이번 규칙상 하지 않음).
7. `origin/paper` 브랜치의 schema(10종, 엣지 24종, foundation 비terminal, 승인 후 적용하는 consolidation)가 main으로 돌아올 계획인지. 확인: README "branch model" 절(`03a78ee` "main = stable, paper = paper snapshot"), 메인테이너 답변.
8. `/check` skill의 LLM 단계(중복 개념 탐지 등)가 lint 밖에서 무엇을 보는지. 다른 갈래(skills) 노트에서 확인.

---

## 부록 A. `origin/paper` 브랜치 경계 (훑음)

- 마지막 commit `5e1bfc8`(2026-07-30). main 대비 `runtime`·`tools`에 +7851/−4287줄(`git diff --stat main origin/paper -- runtime tools`).
- schema: 종류 10개(papers, concepts, topics, people, ideas, methods, experiments, foundations, manuscripts, reviews; Summary 삭제). 엣지 24개: 개념↔개념 대칭 4종(`shares_mechanism_with`, `shares_assumption_with`, `related_problem_formulation`, `contrasts_with_concept`), 논문→방법 3종(`proposes_method`, `applies_method`, `extends_method`), `contributes_to_foundation` 추가. 모두 confidence·evidence 필수.
- xref에 `edge_type` forward 규칙이 실제로 쓰인다(예: `proposes_method` → methods `## Proposed by`). `terminal_targets: []`.
- 새 도구: `trust_guard.py`, `trust_content_review.py`, `evidence.py`("read-only claim/evidence coverage check", PASS/WARN/BLOCK/INFO), `consolidate_memory.py`("generates candidate patches ... `apply` ... applies an approved patch file through Trust Guard. Patches are NOT auto-applied."), `wiki_events.py`, `scievolve.py`, `research_pipeline.py`.
- `research_wiki.py`에 `scievolve-*`, `dream`, `forge`, `morph`, `concerns`, `append-event`, `validate-pipeline` 명령 추가.
- 엔터프라이즈에 관련된 점: "제안 → 승인 → 관문 통과 후 적용"(`consolidate_memory.py`)은 사용자가 원한 승인 대기열 모양이다. 다른 갈래가 paper 브랜치를 맡지 않았다면 보고서 작성자가 따로 볼 가치가 있다.

## 부록 B. 이 노트에서 쓴 핵심 commit

| commit | 날짜 | 내용 |
|---|---|---|
| `20c61b9` | 2026-04-09 | 첫 릴리스 v0.1.0 |
| `070d5e1` | 2026-04-10 | 병렬 ingest + worktree + `dedup-edges` |
| `f6f34fc` | 2026-04-10 | foundations 종류(terminal), `/prefill`, `reset_wiki.py` |
| `5f904b1` | 2026-04-11 | `find-similar-concept`/`-claim` 도입, 생성 한도 |
| `1fc7738` | 2026-04-12 | `tools/_schemas.py`로 상수 통합, `topic-backfill` |
| `46cad0d` | 2026-04-15 | worktree 안 재생성 거부(이슈 #12) |
| `b36c1df` | 2026-04-24 | ingest 재작성, 테스트 삭제 |
| `1b2df1f` | 2026-05-06 | v1.1.0: `runtime/` SSOT, claims→methods, 프런트 |
| `d89cc72` | 2026-05-26 | 의미 엣지 8→4, frontmatter 투영, 스키마 확장 |
| `1fd1e58` | 2026-05-18 | v1.4.0 `/poster`, `wiki2dag.py` |
| `40f5220` | 2026-09-28 | hiera 사이드카 |
| `fefa4df` | 2026-05-29 | (`origin/paper`) schema 확장, foundation 비terminal |

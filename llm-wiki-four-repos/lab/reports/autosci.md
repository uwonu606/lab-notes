# autosci — Claude Code skill이 논문을 읽고 페이지와 index를 쓰되, 프롬프트 규율이 깨진 자리마다 YAML schema를 읽는 Python 도구로 엣지·인용·로그 쓰기와 개념 중복 대조를 옮겨, 연구 수명주기 전체를 기억하는 llm-wiki

AutoSci(구 OmegaWiki, GitHub `skyllwt/AutoSci`)는 논문 wiki를 연구 수명주기 전체(아이디어 → 실험 → 논문 집필)의 기억으로 쓰는 Claude Code skill 묶음이다.

판단과 서술은 skill 문서를 따르는 LLM이 하고, slug·대조·엣지 쓰기·lint·재생성은 Python 도구가 한다.

이 경계는 처음부터 있었지만, 사고가 날 때마다 프롬프트 쪽에서 도구 쪽으로 옮겨 갔다. 이 보고서의 "왜"는 대부분 그 이동의 기록이다.

출처 표기는 레포 루트 기준 `path:line`이다. `.claude/skills/X/...`는 `research` 하나를 빼고 `i18n/en/skills/X/...`와 내용이 같다. 그래서 `research`만 `i18n/en/...` 줄 번호로 적는다.

"(a)"는 작성자가 밝힌 이유의 원문 인용이고, "[추정]"은 이 조사가 추론한 이유다. 코드는 실행하지 않았다.

## 한눈에

| 항목 | 내용 |
|---|---|
| 무엇 | 연구용 llm-wiki + 연구 수명주기 skill 묶음. 저장소 설명은 "Karpathy's LLM-Wiki vision, fully realized — wiki-centric full-lifecycle AI research platform powered by Claude Code"다(`gh repo view skyllwt/AutoSci`). 코드 안 이름은 아직 OmegaWiki다(`tools/research_wiki.py:2`, `runtime/loader.py:1`) |
| 실행 형태 | Claude Code 세션에서 `/skill` 29개를 부른다(`ls .claude/skills`는 30개 항목이고 그중 `shared-references`는 skill이 아니다). skill은 Bash로 Python CLI를 부른다. 그 밖에 로컬 웹 SPA(`tools/serve.py`), Review LLM용 MCP 서버(`mcp-servers/llm-review/server.py`), 매일 도는 GitHub Actions(`.github/workflows/daily-arxiv.yml`)가 있다 |
| 규모 | Python 21,202줄(그중 `tools/` 20,076줄, `runtime/` 1,013줄), 활성 skill 문서 10,199줄(`i18n/en` 10,227줄, `i18n/zh` 10,101줄은 원본), JS 3,682줄. 세는 데 쓴 명령은 `git ls-files … \| xargs cat \| wc -l`이다. 핵심 파일은 `tools/research_wiki.py` 2,861줄, `tools/lint.py` 1,170줄, `runtime/loader.py` 237줄이다 |
| 이력 | main 108 commits, 2026-04-09(`20c61b9` "Initial release: OmegaWiki v0.1.0")부터 2026-10-02(`f5c2fe0`)까지다. 기여자는 9명 이상이다(`git shortlog -sn`: corin 38, DanJoshua 21, Weitong Qian 20, Zhongao Xie 13, Tom White 7 …). 별 1,698개, fork 214개(`gh repo view`, 2026-10-11) |
| 라이선스 | MIT, "Copyright (c) 2026 OmegaWiki Contributors"(`LICENSE:3`). 저작권 고지를 남기면 코드째 가져올 수 있다 |
| 테스트 | main에는 `tests/test_hiera_local.py`(88줄)와 `.sleepcode/tests/test_discover_from_venue.py`(417줄) 둘뿐이다. 한때 2,327개였던 테스트를 `b36c1df`("Rebuild ingest. Deleted tests.")가 지웠다. `CONTRIBUTING.md:16`은 아직 "`python -m pytest tests/ -v` must pass"를 요구한다 |
| CI | `daily-arxiv.yml` 하나다. 논문 추천과 선택적 auto-ingest를 돌리고, 테스트·lint 단계는 없다(이슈 #41 메인테이너 Morrow-Yang 답 "Our daily-arxiv CI workflow auto-commits wiki changes without running /check at all.") |
| 릴리스 | GitHub Release는 없다(`gh release list` 빈 결과). 태그는 `v1.0.0`(`8233e0c`)과 `arxiv-v1`(`6bc834a`)이다. CHANGELOG 최신은 1.4.0(2026-05-18, `CHANGELOG.md:9`)이다. main의 wiki 계약(`runtime/`)은 `d89cc72`(2026-05-26) 뒤로 바뀌지 않았다 |
| 갈래 | `paper`(논문 arXiv 2605.31468 시점 스냅숏, `03a78ee` "main = stable, paper = paper snapshot"), `autosci-codex`·`autosci-opencode`(다른 에이전트 런타임 이식), `dev-dcy-biology`(생물 도메인 schema)가 main 밖에 있다 |
| 분석 기준 | main `f5c2fe0`. 다른 브랜치 파일은 `origin/paper:경로`처럼 적는다 |

## 큰 구조

다섯 층이다. 사람이 고치는 원본(`i18n/`), LLM이 따라가는 skill, 계약(`runtime/`), 결정적 도구(`tools/`), 저장소(`wiki/`, `raw/`)다.

```
i18n/{en,zh}/CLAUDE.md, skills/*            ← 사람이 고치는 원본 (English is canonical)
        │ setup.sh --lang en|zh  (복사)
        ▼
CLAUDE.md, .claude/skills/<skill>/SKILL.md + references/*.md   ← Claude Code가 읽는 활성 사본
        │ 사용자가 /skill 호출 → 주 LLM이 단계를 따라감
        ├─ Read/Write/Edit ─────────────▶ wiki/<kind>/<slug>.md   (페이지는 LLM이 직접 씀)
        ├─ Bash: tools/research_wiki.py ─▶ wiki/graph/*.jsonl, index.md, log.md, 파생물
        │          └ import runtime/loader.py ◀── runtime/schema/*.yaml, policy/writers.yaml
        ├─ Bash: tools/lint.py (사후 감사, 같은 loader)
        ├─ Bash: tools/fetch_*.py, discover.py, daily_arxiv.py (외부 수집: S2·arXiv·DeepXiv·Wikipedia)
        ├─ MCP: mcp__llm-review__chat (두 번째 LLM, 독립 심사)
        ├─ Skill: 다른 skill 호출 (/research → /ideate → /exp-* → /paper-*)
        └─ Agent: 병렬 subagent (/init 병렬 ingest, git worktree 격리)
tools/serve.py (웹 SPA) ── subprocess로 같은 research_wiki.py·lint.py·visualize.py CLI를 부름
tools/hiera/ ── wiki 읽기 전용, runs/hiera/ 에만 씀
```

근거는 `CLAUDE.md:3`("Edit `i18n/en/CLAUDE.md`, not the active copy at root."), `runtime/CLAUDE.md:3-6`("`loader.py` is the Python access API consumed by `tools/lint.py` and `tools/research_wiki.py`"), `tools/serve.py:135-146`(`_run_research_wiki`), `.mcp.json`이다.

| 구성 요소 | 맡는 일 | 대표 파일 |
|---|---|---|
| skill 29개 | 단계와 판단. 지식(`ingest`·`init`·`prefill`·`ask`·`check`·`edit`·`discover`·`daily-arxiv`), 아이디어(`ideate`·`novelty`·`review`·`exp-pilot-*`), 실험(`exp-design`·`exp-run`·`exp-eval`·`exp-status`·`refine`·`hiera-experiment`), 집필(`survey`·`paper-*`·`rebuttal`·`poster`), 운영(`setup`·`reset`·`visualize`), 오케스트레이터(`research`)로 나뉜다 | `.claude/skills/ingest/SKILL.md`, `.claude/skills/ingest/references/dedup-policy.md` |
| 계약층 | 페이지 종류 9개·엣지 16종·역링크 규칙 14개·쓰기 권한 명세·본문 템플릿을 YAML로 선언한다. loader가 import 시점에 읽어 검사 상수를 만든다 | `runtime/schema/{entities,edges,xref,conventions}.yaml`, `runtime/policy/writers.yaml`, `runtime/templates/*.md.tmpl`, `runtime/loader.py` |
| 쓰기·질의 엔진 | slug, 개념 대조, 엣지·인용 쓰기, frontmatter 필드 쓰기, 상태 전이, 로그, 파생물 재생성, checkpoint | `tools/research_wiki.py` |
| 사후 감사 | 필수 필드·enum·역링크 대칭·그래프 일관성 검사와 결정적 자동 수정 | `tools/lint.py` |
| 외부 수집 | 논문 메타·참고문헌·추천 후보. LLM을 부르지 않는다(`daily_arxiv.py`의 추천 LLM 호출만 예외) | `tools/fetch_s2.py`, `tools/discover.py`, `tools/daily_arxiv.py`, `tools/backfill_citations.py` |
| 웹 SPA | 그래프 보기, 필드 편집, lint·재생성 버튼. 쓰기는 skill이 쓰는 것과 같은 도구 CLI(`research_wiki.py`·`lint.py`·`visualize.py`)로만 한다(W16) | `tools/serve.py`, `app/modules/*.js` |
| Review LLM | 두 번째 모델로 아이디어·실험·원고를 심사한다 | `mcp-servers/llm-review/server.py`, `.claude/skills/shared-references/cross-model-review.md` |
| 사이드카 | 실험 후보 탐색. wiki에 쓰지 않는다 | `tools/hiera/`, `.claude/skills/hiera-experiment/SKILL.md` |
| 집필·포스터 산출 | LaTeX 원고를 poster용 DAG·HTML·PNG로 바꾼다. wiki는 읽기만 한다(`tools/wiki2dag.py:1-4`). PDF 원문 정규화(`prepare_paper_source.py`)와 메일 발송도 이 무리다. 합계 4,463줄(`wc -l`, 아래 원격 실행 포함) | `tools/poster.py`, `tools/wiki2dag.py`, `tools/rasterize_latex.py`, `tools/prepare_paper_source.py`, `tools/send_email.py` |
| 원격 실험 실행 | SSH로 GPU 서버 상태 확인, 코드 동기화, 실행, 결과 회수를 한다(`tools/remote.py:1-12`). 858줄 | `tools/remote.py` |

### 저장소

| 층 | 파일 | 누가 쓰나 | 형식 |
|---|---|---|---|
| 원문 | `raw/{papers,notes,web}`(사용자 소유), `raw/{discovered,tmp}`(skill용) | 사람 / skill | PDF·tex·md. `conventions.yaml:20-22` `ownership.user_owned` |
| 페이지 | `wiki/<kind>/<slug>.md` | LLM이 직접 쓴다. 도구는 `set-meta`·`transition`·lint `--fix`만 고친다. topic 본문에 덧붙이는 `topic-backfill`(`tools/research_wiki.py:1892`)도 있지만 어느 skill도 부르지 않는다(`grep -rn topic-backfill .claude/skills` 결과 0) | YAML frontmatter + 템플릿 H2 절 |
| 그래프 | `wiki/graph/edges.jsonl`(의미·작업 흐름 엣지), `citations.jsonl`(서지 `cites`) | `research_wiki.py add-edge`·`add-citation`만 | JSON Lines, 한 줄에 엣지 하나 |
| 파생물 | `wiki/index.md`, `graph/context_brief.md`, `graph/open_questions.md`, `graph/projected_edges.jsonl`(명령은 있으나 호출처 없음) | `rebuild-*` 명령이 통째로 다시 쓴다. index는 ingest 때 LLM도 직접 덧붙인다(`ingest/SKILL.md:190`) | md / jsonl |
| 기록 | `wiki/log.md` | `research_wiki.py log`(append) | `## [YYYY-MM-DD] <message>`(`tools/research_wiki.py:2080-2094`) |
| 작업 상태 | `wiki/.checkpoints/<task>.json`, `wiki/outputs/pipeline-progress.md` | `checkpoint-*` 명령 / `/research` | JSON / frontmatter |

실제 wiki 데이터는 레포에 없다. `1b2df1f` 본문이 "`.gitignore`: enforces per-user data boundary"라고 밝히고, `wiki/index.md`·`wiki/log.md`는 빈 골격뿐이다.

이 `.gitignore`는 사용자 자신의 wiki에도 그대로 걸린다. `wiki/<kind>/*`와 `wiki/graph/*`가 무시 대상이라(`.gitignore:57-79`, `git check-ignore -v`로 확인) 페이지와 엣지 장부는 git에 들어가지 않는다. git 위에 선 병렬 ingest와 CI auto-ingest가 이 때문에 깨진다(W10).

`CLAUDE.md:21` Hard Rule 2는 "`wiki/graph/` is derived"라고 적는다. 하지만 `edges.jsonl`의 의미 엣지(evidence·confidence 포함)를 페이지에서 다시 만드는 명령은 없다(`tools/research_wiki.py:2583-2768` 명령 목록). 그래서 edges.jsonl은 사실상 원본이다.

### 페이지 종류와 엣지

| 종류 | 무엇 | 별칭 필드 | 상태 기계 |
|---|---|---|---|
| papers | 논문 1편. `importance`(1~5), `tldr`, `contribution_type` | 없음 | 없음 |
| concepts | 연구 개념. `key_papers`, `maturity`, `parent_topic` | `aliases`(`entities.yaml:40`) | 없음 |
| foundations | 교과서 배경지식. `terminal: true`(역링크를 쓰지 않음) | `aliases`(`entities.yaml:180`) | 없음 |
| methods | 이름 있고 재사용되는 기법. `source_papers`, `parent_methods` | 없음 | 없음 |
| topics, people, Summary | 주제·사람·전체 요약 | 없음 | 없음 |
| ideas | 사용자의 연구 아이디어. `failure_reason`은 `status: failed`일 때 필수 | 없음 | proposed → in_progress → tested → validated/failed |
| experiments | 실험. `linked_idea`, `hypothesis`, `setup` | 없음 | planned → running → completed/abandoned |

엣지 16종은 네 무리다(`runtime/schema/edges.yaml`). 논문↔논문 의미 4종(`same_problem_as`, `similar_method_to`, `builds_on`, `challenges`)과 논문→개념 4종(`introduces_concept`, `uses_concept`, `extends_concept`, `critiques_concept`)은 `confidence`·`evidence`가 필수다.

작업 흐름 7종(`supports`, `contradicts`, `tested_by`, `invalidates`, `addresses_gap`, `inspired_by`, `derived_from`)은 끝점이 `*`이고 필수 속성이 없다. 서지 `cites` 1종은 `source`가 필수이고 `citations.jsonl`에 따로 저장된다(`conventions.yaml:27-30`).

## 한 바퀴 흐름

### ingest — 논문 1편 → 페이지 묶음

입력은 arXiv URL, 로컬 `.tex`/`.pdf`, 또는 `/init`이 넘긴 `canonical_ingest_path`다(`.claude/skills/ingest/SKILL.md:20-24`). 원문은 `.tex` 하나로 정규화하고(`ingest/SKILL.md:96-103`, `pdf-preprocessing.md:7`), 청크로 나누는 단계는 없다(`grep -rni chunk .claude/skills/ingest` 결과 0). 페이지 작성은 LLM이 그 원문을 읽고 한다.

1. **원문 확정** [코드 + LLM]. arXiv면 `fetch_s2.py paper`로 제목을 얻고 `init_discovery.py download`로 tex를 우선 받는다(`ingest/SKILL.md:96-103`). PDF는 LLM이 먼저 제목을 읽고(`ingest/references/pdf-preprocessing.md:15-19`), 도구가 합성 `.tex`로 정규화한다(`pdf-preprocessing.md:7`).
2. **정체 확인** [코드 + LLM]. `research_wiki.py slug`가 결정적 slug를 만든다(`tools/research_wiki.py:105-129`). 같은 slug 페이지가 있고 arXiv ID나 제목이 맞으면 LLM이 멈춘다(`ingest/SKILL.md:113`). 둘 다 다르면 slug 충돌로 보고 멈춘다(`error-handling.md:20`). 이 판정은 도구가 아니라 LLM이 한다. S2로 venue·year를 채우고, `importance`(1~5)는 LLM이 정한다(`ingest/SKILL.md:105-129`).
3. **논문 페이지 작성** [LLM]. LLM이 `entities.yaml`과 `templates/papers.md.tmpl`을 열고 frontmatter와 본문을 쓴다. 쓰기 전 검사는 LLM 자신의 "shape check"(필수 키, enum, YAML 파싱)뿐이다(`ingest/SKILL.md:131-148`).
4. **개념 대조와 결정** [코드 점수 → LLM 결정]. 개념 후보마다 `find-similar-concept`가 기존 concepts·foundations의 제목·별칭과 대조해 점수를 낸다(`tools/research_wiki.py:1090-1118`). LLM이 점수 구간에 따라 foundation 연결 / 병합 / 판단 / 생성을 고른다(`ingest/references/dedup-policy.md:33-38`).
5. **방법·사람** [LLM]. 방법은 대조 도구 없이 LLM이 `wiki/methods/`를 훑는다(`dedup-policy.md:27`). 사람 페이지는 importance ≥ 4일 때만 만든다. 생성 한도는 importance < 4면 새 개념 1·방법 1, ≥ 4면 3·2다(`ingest/SKILL.md:251-254`).
6. **엣지 쓰기** [코드 검사]. LLM이 `add-edge`를 부르면 도구가 모르는 종류, endpoint 위반, `confidence`·`evidence` 누락을 `sys.exit(1)`로 거부한다(`tools/research_wiki.py:275-307`). 자기 연결은 논문↔논문 종류에서만 거부하고, legacy 종류(`extends`·`supersedes` 등)는 끝점이 papers→papers·papers→concepts일 때만 거부한다(`tools/research_wiki.py:231-234`, `runtime/loader.py:175-180`). 다른 끝점의 legacy 종류와 `*` 엣지의 자기 연결은 통과한다(`runtime/loader.py:165-168`, `:198`). 끝점 페이지가 없으면 경고만 내고 쓴다(`:309-314`).
7. **논문↔논문** [코드 + LLM]. LLM이 `fetch_s2.py references/citations` 결과를 arXiv ID나 제목으로 기존 논문과 맞춰 `cites`를 붙인다(`ingest/SKILL.md:178`). 원문 단서가 분명할 때만 LLM이 의미 엣지를 고른다(`ingest/SKILL.md:169-181`). INIT MODE에서는 이 단계를 통째로 건너뛰고(`:171`), fan-in의 `backfill_citations.py`가 arXiv·S2 ID로 `cites`만 결정적으로 되채운다(`tools/research_wiki.py:431-451`, `tools/backfill_citations.py:1-9`).
8. **역링크·주제·색인** [LLM]. 정방향 링크를 쓰면 같은 턴에 반대편도 쓴다(`ingest/references/cross-references.md:18`). 단 INIT MODE의 병렬 subagent는 기존 페이지에 역링크와 topic 쓰기를 하지 않고 `add-edge`만 남긴다. 빠진 역링크는 fan-in의 `lint.py --fix`가 채운다(`ingest/SKILL.md:249`, `init-mode.md:15-16`). 태그가 맞는 기존 topic에만 덧붙이고 topic은 만들지 않는다. `index.md`에 한 줄 더한다(`ingest/SKILL.md:183-190`).
9. **로그·재생성** [코드]. `log`, `rebuild-context-brief`, `rebuild-open-questions`를 부른다(`ingest/SKILL.md:192-203`). 마지막에 LLM이 `Wiki: +1 paper, +{N} methods, +{M} concepts, +{K} edges`를 보고한다(`:218-224`).

직접 ingest는 실패해도 되돌리지 않는다(`error-handling.md:38`). INIT MODE에서는 부분 실패한 worktree를 커밋하지 않아 fan-in에서 merge되지 않는다(`error-handling.md:41`, `init/references/parallel-ingest.md:55`).

원문 확보는 tex → PDF → vision → 사람 순으로 내려가고, S2가 죽으면 importance 3으로 둔다(`ingest/references/error-handling.md:5-14`).

이유는 (a) "a partial ingest that preserves a well-shaped paper page is more useful than a clean abort"(`error-handling.md:57`) — 모양을 갖춘 논문 페이지를 남긴 부분 ingest가 깨끗한 중단보다 쓸모 있다는 뜻이다.

`/init`은 빈 wiki를 세운다. LLM이 PDF 제목을 적고 → 도구가 후보를 계획하고 → LLM이 8~10편으로 자르고 → notes/web에서 임시 scaffold를 만든 뒤 → 논문마다 git worktree에서 subagent `/ingest`를 병렬로 돌린다(`init/SKILL.md:77-175`). 병합은 아래 유지보수 3단계에서 한다.

INIT MODE가 건너뛴 연결 중 둘은 fan-in에서도 채워지지 않는다. 논문↔논문 의미 엣지와 `cited_by`(Step 5, `ingest/SKILL.md:171`)는 fan-in이 `cites`만 되채우므로 생기지 않는다(`init/SKILL.md:184-197`).

topic 소속은 INIT MODE가 "Let the parent handle topic updates after fan-in"이라며 미루지만(`init-mode.md:15`), 이를 메우던 `topic-backfill`은 `7090a22`에서 fan-in 목록에서 빠졌다. 그래서 `/init`으로 만든 wiki에는 논문 간 의미 연결과 주제 소속이 비어 있다.

### query — 질문 → 답 (`/ask`)

1. **요약 읽기** [LLM, 없으면 코드가 재생성]. `context_brief.md`와 `open_questions.md`를 읽는다(`ask/SKILL.md:65-73`).
2. **페이지 고르기** [LLM]. `index.md`에서 질문 낱말과 slug를 맞추고, context_brief에서 관련 ideas·methods·papers를 고른다. 상위 K ≤ 15 페이지를 전문으로 읽는다. "X와 Y의 차이" 질문이면 `edges.jsonl`에서 X-Y 엣지를 읽는다(`ask/SKILL.md:75-81`).
3. **답 합성** [LLM]. 핵심 문장마다 `[[slug]]`를 달고, 근거가 약하면 "insufficient evidence in wiki"라고 쓴다(`ask/SKILL.md:83-94`).
4. **결정화(crystallize)** [LLM, 사람 확인]. 기본은 쓰지 않는다. `--crystallize`나 사용자 확인이 있을 때만 `wiki/outputs/`에 답을 쓰거나 새 concept(`maturity: emerging`)를 만든다(`ask/SKILL.md:96-148`, `:182`).

검색은 전부 LLM 판단이다. 임베딩·BM25·그래프 탐색 도구를 부르지 않는다.

`research_wiki.py`에 있는 `neighbors`(BFS)와 `compile-context`(목적별 예산)는 어느 skill도, `app/`도, 다른 도구도 부르지 않는다(`grep -rln "research_wiki.py neighbors" .claude/skills` 결과 0).

`index.md`에는 aliases가 없어서(`tools/research_wiki.py:1823-1885`) `/ask`의 slug 대조는 별칭을 보지 못한다.

### 유지보수 — lint, 재생성, 병합

1. **사후 감사 `/check`** [코드 + LLM]. `lint.py`가 필수 필드, 깨진 wikilink, 고아 페이지, enum, `required_when`, 역링크 대칭, 엣지·인용 일관성을 본다(`tools/lint.py:733-750`). 🔴가 하나라도 있으면 exit 1이다(`:1166`). 근사 중복·모순·낡은 SOTA는 같은 세션 LLM이 보고 "recommendations"만 낸다(`check/SKILL.md:133-140`).
2. **자동 수정 `--fix`** [코드]. 역링크 대칭과 기본값 있는 필수 필드 두 종류만 고친다(`tools/lint.py:815-832`). 나머지는 "recommendations (`--suggest`) for user approval"이다(`check/SKILL.md:174`).
3. **`/init` fan-in 병합** [코드 + LLM]. worktree 브랜치를 순서대로 merge한다. `.gitattributes`의 `merge=union`이 `log.md`·`edges.jsonl`·`citations.jsonl`·`index.md`의 양쪽 줄을 다 남긴다. 그 뒤 `dedup-edges`, `dedup-citations`, `rebuild-*`, `lint.py --fix`, `backfill_citations.py`를 돈다(`init/SKILL.md:177-221`).
4. **같은 slug 충돌** [LLM]. 두 subagent가 같은 slug 개념을 만들면 부모가 "picking the earlier write and re-running `find-similar-concept` on the later one at fan-in"으로 푼다(`ingest/references/init-mode.md:42`). fan-in에는 "Resolve true concept/method conflicts conservatively: merge, do not multiply near-duplicates."라는 LLM 지시가 있지만(`init/references/parallel-ingest.md:54`), 다른 slug로 만든 근사 중복을 찾는 결정적 명령은 없다(`:51-70`).
5. **파생물 재생성** [코드, LLM 없음]. `rebuild-index`, `rebuild-context-brief`, `rebuild-open-questions`가 매번 통째로 덮어쓴다(`tools/research_wiki.py:1823-1885`, `:821-824`, `:831-885`). 트리거는 skill 프롬프트와 SPA의 수동 재생성 버튼(`tools/serve.py:701-731`)뿐이다. 파일이 바뀌어도 자동으로 다시 만드는 장치는 없어서, 사람이 파일을 직접 고치면 낡는다(이슈 #41).
6. **배경지식 심기 `/prefill`** [코드 + LLM]. catalog나 `--add`로 받은 범용어를 Wikipedia에서 가져와 foundation 페이지로 쓴다. 출처 없는 절에는 `(LLM analysis)`를 단다(`prefill/SKILL.md:42-134`).
7. **상태 전이** [코드]. `transition`이 `entities.yaml` lifecycle 표에 없는 전이와 전제 조건 위반(`failed`인데 reason 없음 등)을 거부한다(`tools/research_wiki.py:1607-1660`).

연구 수명주기 skill도 wiki를 키운다. `/ideate`는 탈락 아이디어를 `status: failed`와 `failure_reason`으로 남기고 다음 `/ideate`가 banlist로 읽는다(`ideate/SKILL.md:318`, `:507-509`).

`rebuild-open-questions`는 papers `## Open questions`, topics·concepts `## Open problems`의 글머리를 모아 아이디어 생성의 gap 지도로 쓴다(`tools/research_wiki.py:831-855`, `ideate/SKILL.md:15`).

## 왜 이 구조인가

결정 대부분은 사고 하나가 규칙을 프롬프트에서 도구로 옮긴 기록이다. 그 이동은 OmegaWiki v0.1(`20c61b9`, 2026-04-09)부터 v1.1.0(`1b2df1f`, 05-06), 엣지 축소(`d89cc72`, 05-26) 사이에 몰려 있다.

### W1. 판단은 skill, 결정적 일은 tools

- 결정: SKILL.md는 단계와 판단만 적고, slug·대조·엣지 쓰기·lint·재생성은 Python 도구가 한다.
- 대안: 전부 프롬프트(Karpathy 원형), 또는 하나의 Python 앱이 LLM API를 직접 부르는 구조(paper 브랜치 SciDAG의 모양, `origin/paper:scidag/README.md:10` "the LLM call layer is rewired to AutoSci's OpenAI-compatible" endpoint. 같은 코드의 PR #63은 contest 브랜치 대상으로 열렸다가 닫혔다).
- 이유 (a): "Skills are **orchestrators** that use LLM reasoning and multi-step decisions." / "Skills call tools via `Bash: python3 tools/X.py` -- they do not contain deterministic logic themselves."(`CONTRIBUTING.md:26-27`). 이슈 #11 메인테이너 DanJoshua의 답은 "we're working to make skills leaner and introduce coded tools to replace LLM reasoning where possible."이다.
- 이유 (a), 논문(한계로 밝힘): "the current implementation is built as a skill package on top of general-purpose coding and reasoning agents. This makes the system easy to deploy and inspect, but it is not yet a science-specialized agent foundation."(arXiv 2605.31468 §9) — 배포와 점검이 쉽다는 이점과, 과학 전용 에이전트 기반이 아니라는 한계를 함께 적었다. 설계를 고른 이유가 아니라 한계 목록의 첫 항목이다.
- [추정] 기준은 "무조건 코드"가 아니라 "결정적으로 풀리는가"다. 작성자는 "where possible"이라고만 적었다(이슈 #11). PR #22는 반대로 PDF 제목 추출을 LLM에 넘겼다("deterministic tools struggles to infer correct titles.")(사례: PR #22, 1건).
- [추정] 하나의 Python 앱 대신 Claude Code 세션을 실행기로 쓴 것은 파일 편집·하위 에이전트를 그대로 빌리기 위해서다(사례: PR #1(`070d5e1`) 시점의 `/init`은 `run_in_background`·`isolation: "worktree"` subagent를 썼다, 1건). 지금은 worktree를 skill이 `git worktree add`로 직접 만든다(`init/references/parallel-ingest.md:29`).
- 이력: 분업은 처음부터 있었다(`20c61b9:README.md:46-80` "Layer 4: Skills — Orchestrators", "Layer 2: Tools — Executors"). 바뀐 것은 경계의 위치다. 개념 중복 판정(`5f904b1`)과 그래프 재생성 금지(`46cad0d`)가 프롬프트에서 도구로 옮겨 갔다.

### W2. 프롬프트 규칙이 깨진 자리는 도구 거부로 바꾼다

- 결정: subagent가 금지된 명령을 실행해도 도구가 거부한다. 예: linked worktree 안에서 `rebuild-context-brief`·`rebuild-open-questions`는 exit 2로 끝난다(`tools/research_wiki.py:791-818`).
- 범위: 이 가드를 부르는 곳은 두 명령뿐이다(`tools/research_wiki.py:823`, `:839`). 같은 `context_brief.md`를 덮어쓰는 `compile-context`(`:2830-2831`, `:1414-1416`)와 `rebuild-index`·`topic-backfill`(`:2840-2843`)은 막히지 않는다. per-subagent `rebuild-index` 금지는 지금도 프롬프트 규칙뿐이다(`init/SKILL.md:170`).
- 대안: 프롬프트 지시를 더 세게 쓴다.
- 이유 (a): "init/SKILL.md already told agents to SKIP these commands in INIT MODE, but that relied on prompt discipline alone. Now it's enforced at the tool level, so a prompt-drifted subagent can't reproduce this conflict even if it tries."(이슈 #12, 레포 소유자 skyllwt의 답). commit `46cad0d`는 같은 장치를 "defense-in-depth against subagent prompt drift"라고 부른다.
- 이유 (a), 그 두 파일만 문제인 까닭: "These files are full rebuilds, not append-only, so they can't be merge=union'd"(`46cad0d`).
- 이력: PR #14(2026-04-15). 같은 무렵 PR #6은 subagent가 프롬프트에 적힌 절대 경로로 main 저장소에 쓰던 사고("silently wrote to the main repo")를 겪고 상대 경로만 쓰게 했다(`init/SKILL.md:165`).

### W3. 페이지와 index는 LLM이 직접 쓰고, 엣지·인용·log만 도구를 거친다

- 결정: 쓰기 직전 코드 검사는 엣지와 `transition`(lifecycle 상태 전이, `tools/research_wiki.py:1630-1659`)에만 있다. 그 밖의 페이지 frontmatter·본문은 LLM이 Write/Edit로 쓰고, 도구 경유인 `set-meta`도 enum·타입·권한을 보지 않는다(`tools/research_wiki.py:2404-2443`). 페이지 생성 명령은 없다(`tools/research_wiki.py:10-50`).
- 대안: `create-page --kind --fields-json` 같은 도구로 페이지도 schema 검사 뒤에만 쓰게 한다.
- 이유 (a), 엣지: "Hard validation for new writes. Legacy graph rows remain lint-readable."(`tools/research_wiki.py:249`). 공유 파일: "Every shared-file write goes through a tool. … The tool layer uses append semantics"(`init-mode.md:33`), "Never lock or in-place-rewrite a shared file."(`:35`).
- 문서와 코드의 어긋남: `init-mode.md:33`은 index도 "index updates" 도구로 쓴다고 적지만 그런 명령은 없다(`tools/research_wiki.py:2772-2853` 명령 분기에는 통째로 다시 쓰는 `rebuild-index`만 있다). `/ingest`(`ingest/SKILL.md:55`, `:190`)와 `/ask`(`ask/SKILL.md:51`, `:152`)는 LLM이 index를 직접 고치고, `/edit`(`edit/SKILL.md:48-49`)은 log까지 도구 없이 쓴다. 그래서 공유 파일 가운데 도구를 거치는 것은 `edges.jsonl`·`citations.jsonl`, 그리고 `/edit` 밖의 `log.md`다.
- 이유 (a), 페이지를 사후에 보는 까닭: "The shape check is intentionally narrow. Backlink symmetry, dangling-node detection, and cross-entity consistency are `/check`'s job"(`ingest/SKILL.md:148`), "Running those audits inside `/ingest` slows the skill down and duplicates work."(`dedup-policy.md:63`).
- [추정] 페이지 쓰기 도구를 두지 않은 근본 이유는 자유 서술 본문을 도구 API로 표현하기 어렵기 때문이다. 그래서 쓰기 전 검사를 걸 자리가 없다(사례: `set-meta`가 frontmatter 한 필드 단위로만 동작 `:2404-2443`, `ingest/SKILL.md:47`이 페이지를 "CREATE (new) or EDIT"로 직접 쓰라고 함, 2건).
- 이력: v0.1의 `add_edge`는 종류 이름만 막았다(`20c61b9:tools/research_wiki.py:175-182`). 끝점·confidence·evidence 강제는 `b36c1df`에서 들어왔고 메시지에 이유가 없다. PR #30 본문은 SPA PATCH가 "with schema validation"이라고 썼지만 지금 `tools/serve.py:588-644`는 필드 존재만 확인한다.

### W4. schema는 YAML 한 곳, loader가 import 시점에 나눠 준다

- 결정: `runtime/schema/*.yaml`이 유일한 원본이고, `runtime/loader.py`가 `REQUIRED_FIELDS`·`VALID_VALUES`·`EDGE_TYPE_SPECS` 같은 상수를 만들어 lint·research_wiki·serve·visualize·reset에 준다. 코드 생성 단계는 없다.
- 대안: 프롬프트 안 schema, Python 상수 파일, JSON Schema + codegen, Pydantic 모델.
- 이유 (a): "Single source of truth for what is structurally legal in the wiki. … **No codegen step** — edit YAML, restart the tool."(`runtime/CLAUDE.md:3-6`), "Every change below is **YAML-only, zero Python change**."(`runtime/CLAUDE.md:21`).
- 이유 (a), 이력에서: `1fc7738` "Schema constants … were duplicated between lint.py and research_wiki.py — extracted to tools/_schemas.py as single source of truth." 이어서 `1b2df1f` "Eliminate the codegen pipeline and its derived docs", "Make consumers data-driven (zero hardcoded entity/edge name lists)".
- 이력: schema는 두 갈래로 갈라졌다가 하나로 합쳐졌다. 처음에는 `20c61b9:CLAUDE.md:92-275`(프롬프트 안)에 있었다. 이후 도구용 상수는 `tools/_schemas.py`(`1fc7738`, 04-12)로 빠졌고, LLM용 서술은 PR #18(04-16 merge)이 `docs/runtime-*.md`로 옮겼다("to reduce context window cost"). 두 사본은 나란히 있었다: `_schemas.py`는 스스로를 "the machine-facing copy that the tools actually consume"이라 불렀다(`1b2df1f^:tools/_schemas.py` 머리 docstring). `1b2df1f`(05-06)가 두 사본을 모두 지우고 `runtime/*.yaml` + loader로 합쳤다.
- 한계: "YAML만"은 종류·필드·엣지 추가에만 맞다. lint enum 검사 목록(`tools/lint.py:251-258`), 전이 전제 조건(`tools/research_wiki.py:1640-1659`), 저장 경로(`:300`, `:388`)는 Python에 박혀 있다. `conventions.yaml`은 `tools/research_wiki.py:73`에서 import만 되고 쓰이지 않는다(`grep -rn CONVENTIONS tools runtime`). 프런트는 `app/modules/schema.js`에 손으로 복제한다(`1b2df1f` "JavaScript cannot import from runtime/loader.py").

### W5. 개념은 "만들기 전에" 결정적으로 대조하고, 기본은 병합, 문서당 생성 한도

- 결정: `/ingest`에서는 개념 후보마다 `find-similar-concept`를 반드시 부른다. 점수 ≥ 0.80이면 병합, 0.40~0.80이면 LLM이 정의를 읽고 판단하되 기본은 병합, 0.40 미만이면 한도 안에서 생성한다(`dedup-policy.md:33-38`).
- 대조 방법: 정규화 뒤 완전 일치 1.0, 2단어 이상 포함 0.85, 그 밖은 내용어 Jaccard j(≥ 0.7이면 j, 0.4~0.7이면 `0.4 + (j-0.4)*0.5`)다(`tools/research_wiki.py:1007-1035`). LLM과 임베딩은 쓰지 않는다.
- 대안: 임베딩 유사도, LLM에게 전체 목록을 주고 판단, 생성 뒤 일괄 병합, 사람 승인 대기열.
- 이유 (a), 계기: "Production incident (test6, 15 papers): /init parallel run produced 45 claims … and 37 concepts (3 for 'LLM as gradient', 2 for 'LLM as evolutionary operator'). Cause: every subagent did concept/claim dedup from memory, which silently fails on paraphrase."(`5f904b1`). PR #6은 정답이 "~15 / ~15"였다고 적는다.
- 이유 (a), 비대칭 비용: "Over-merging is cheap to undo … Over-creating is expensive: a sea of near-duplicates silently poisons every downstream skill and is hard to detect post-hoc."(`dedup-policy.md:42`). 생략한 부분은 과병합을 "split later with its history preserved"할 수 있다는 전제다. 그런데 main에는 페이지 분리·이름 바꾸기·병합·엣지 삭제 명령이 없고(`tools/research_wiki.py:2772-2853` 명령 분기), 기본 `.gitignore`가 페이지 이력을 git에서 뺀다(`.gitignore:57-79`). 이 전제를 받쳐 줄 장치가 기본 설정에 없다.
- 이유 (a), 도구 설계: "tuned for high recall — the LLM caller does the final semantic judgment from a small ranked list. Designed to be invoked from /ingest BEFORE any concept is created"(`tools/research_wiki.py:963-967`). 한도는 "not a quota to fill"(`dedup-policy.md:46`).
- 한계: 이 의무는 `/ingest`에만 있다(`grep -rln find-similar-concept .claude/skills` → ingest 묶음 세 파일뿐). `/ask` 결정화 Case B(`ask/SKILL.md:135-140`)와 `/init` notes/web scaffold(`init/SKILL.md:146`)는 대조 없이 concept를 만들고, `/edit`도 대조 도구를 부르지 않는다(`edit/SKILL.md:29-49`).
- 이력: `5f904b1`(04-11)의 한도는 importance < 5 / == 5로 1·3이었다. foundation은 0.80 이상이면 자동 연결했고, 0.40~0.80이면 LLM이 정의를 읽고 판단했다(`0366aea^:.claude/skills/ingest/SKILL.md:260`, `:270`). `0366aea`(04-24) 재작성에서 한도 기준이 importance < 4 / ≥ 4로 바뀌고, foundation 판단 구간이 없어져 0.40 이상이면 자동 연결로 바뀌었다(`dedup-policy.md:35`). 이 바뀐 이유는 commit에 없다.
- 모르는 것: 0.40/0.80/0.85 문턱의 보정 근거와 임베딩을 쓰지 않은 이유. 레포·이슈·PR에서 찾지 못했고 작성자에게 물어야 안다. 이슈 #42 메인테이너 답 "there is no such benchmarks to measure the performance of LLM-wiki maintained by agent and an organized set of markdown files"는 wiki 전체와 markdown 묶음을 비교한 벤치마크에 관한 말이라 문턱 보정과는 직접 관계가 없다.

### W6. 범용어는 foundation이라는 terminal 계층으로, `/prefill`만 만든다

- 결정: Transformer·gradient descent 같은 교과서 지식을 `foundations/`에 따로 둔다. foundation은 역링크를 쓰지 않고(`xref.yaml:78` `terminal_targets: [foundations]`), 대조 결과에서 점수와 무관하게 맨 앞에 오며(`tools/research_wiki.py:1114-1117`), 성숙도 통계에서 빠진다. `/ingest`는 foundation을 만들지 못한다(`cross-references.md:27`).
- 대안: 빈도 기반 stoplist, 개념 페이지에 `generic` 표시, 일반 개념에 `maturity: stable`로 섞기.
- 이유 (a), 원래 동기: "一个研究员在读论文时，对于Transformer, RL, CoT等基本知识的反应，和对特定 concept…的反应应当是不同的。且这些基础知识的处理可能会在 wiki 创建的前期不必要地分散 llm 的注意力。"(`DanJoshua/Research-Wiki-experimental:future-features.md`) — 연구자는 기초 지식과 특정 개념에 다르게 반응해야 하고, 기초 지식 처리는 wiki 초기에 LLM의 주의를 쓸데없이 흩뜨린다는 뜻이다.
- 이유 (a), 이식 PR: "the whole point of `/prefill` is to keep foundational background separate from research concepts so `/ingest` doesn't pollute `concepts/` with textbook material."(PR #3). 통계 제외는 "background knowledge shouldn't inflate research progress scores."(PR #3).
- 이유 (a), 고아 검사에서는 빼지 않음: "An orphan foundation is a real signal — either /prefill seeded background that no paper references, or /ingest is failing to dedup against it."(`tools/lint.py:228-232`).
- 이유 (a), terminal: "foundations 不参与双向链接：foundation 是 background context，不维护反向引用。"(`DanJoshua/Research-Wiki-experimental:CLAUDE.md:204`) — foundation은 배경 맥락이라 역참조를 유지하지 않는다는 뜻이다. 같은 fork의 prefill은 "foundation 不绑定具体论文（无 `key_papers` 字段）"(특정 논문에 묶지 않는다, `key_papers` 필드 없음)라고 적는다(`.claude/skills/prefill/SKILL.md:106`).
- [추정] 역링크 목록이 끝없이 커지는 것을 피하려는 뜻도 있다. 거의 모든 논문이 기초 개념을 가리키기 때문이다(사례: foundation 페이지에 `key_papers` 필드가 없음 `entities.yaml:171-183`, 투영에서 terminal 제외 `tools/research_wiki.py:610`, 2건).
- 이력: `f6f34fc`(04-10)에 들어왔다. paper 브랜치는 이 결정을 뒤집었다: "Foundations stops being terminal"(`origin/paper:docs/superpowers/plans/2026-05-29-autosci-schema.md:26`). 논문 §3.1 "Foundation entities provide stable background knowledge that grounds Concept and Method entities"를 schema로 옮기려는 것이다.
- 한계: terminal은 페이지 역링크만 끊는다. `neighbors` BFS(`tools/research_wiki.py:1184-1237`)는 foundation을 그대로 지난다. 다만 그 BFS를 지금 부르는 skill은 없다(#query — 질문 → 답).

### W7. 의미 엣지는 드물게 두고, 서지 층과 나눈다

- 결정: 논문↔논문 의미 엣지는 원문 단서가 분명할 때만 단다. `cites`는 외부 ID 일치로 기계적으로 만들어 `citations.jsonl`에 따로 둔다. 논문↔논문 의미 엣지는 8종에서 4종으로 줄였다.
- 대안: 인용마다 의미 엣지, 세분화 유지 + 상위 종류로 묶기.
- 이유 (a), 드물게: "Graph noise is worse than a missing edge."(`cross-references.md:79`), "If the same statement would be true for dozens of papers in the wiki, skip the paper-to-paper edge"(`:58-60`), "When in doubt, skip."(`:81`).
- 이유 (a), 층 분리: "The bibliographic layer is separate from the semantic layer … do not force every citation into a semantic edge"(`cross-references.md:50-54`).
- 이유 (a), 축소: "improves_on ⊆ builds_on (subset; merged); compares_against ⊆ cites (every comparison already cites); surveys ⇐ papers.contribution_type contains "survey" (derivable); complementary_to ≈ same_problem_as (boundary fuzzy in practice)"(`runtime/schema/edges.yaml:17-23`).
- 이유 (a), 기준: 남긴 4종은 "irreducible"이고 지운 4종은 "judged redundant"다(`runtime/schema/edges.yaml:17-19`). 사유는 다른 엣지에 포함됨 2건(improves_on ⊆ builds_on, compares_against ⊆ cites), 필드에서 유도됨 1건(surveys), 경계 모호 1건(complementary_to)이다.
- 이력: v0.1은 끝점 무관 일반 엣지 9종(`extends`, `supports` 등, `20c61b9:README.md:192-194`) → `b36c1df`에서 끝점별 12종 + legacy 표시 → `d89cc72`(PR #60)에서 논문↔논문 4종. 끝점별 이름으로 바꾼 이유는 `b36c1df` 메시지에 없다.

### W8. 정방향 링크를 쓰면 같은 턴에 역방향도, 빠지면 lint가 채운다

- 결정: `xref.yaml` 규칙 14개대로 정방향을 쓰는 순간 반대편도 쓴다. 빠진 것은 `lint.py --fix`가 결정적으로 채운다(`tools/lint.py:835-890`).
- 대안: 역링크를 저장하지 않고 질의 때 계산하는 backlink index.
- 이유 (a): "Writing a forward link without its reverse is the most common way `/check` surfaces `missing-field` errors. Doing both together eliminates the class entirely."(`cross-references.md:18`). 이슈 #42 메인테이너 Morrow-Yang의 답은 "A human maintaining 200+ interlinked markdown files will inevitably let reverse links and cross-references decay."다.
- 이유 (a), 자동 수정 구조: `LintIssue` payload가 "lets a fixer dispatch on schema metadata … instead of regex-parsing the human-readable message back into structure"(`tools/lint.py:62-71`).
- 이력: 하드코딩 분기 5개 이상을 `check_xref_asymmetry`로 일반화했다(`1b2df1f`). 블록형 YAML 리스트를 못 읽는 문제(이슈 #20)는 이슈가 닫혔지만 코드에 남아 있다(`tools/lint.py:343-406`).

### W9. 쓰기 권한표는 명세일 뿐 강제하지 않는다

- 결정: `runtime/policy/writers.yaml`이 필드 23개·엣지 16종마다 "어느 skill이 써야 하는가"를 적지만, 코드는 이 파일을 읽지 않는다. loader가 `WRITERS`로 읽어 두기만 한다(`runtime/loader.py:41`).
- 대안: CLI에 `--skill`이나 `--actor`를 받아 표로 거부, 또는 정체성 필드만 동결.
- 이유 (a): "We deliberately did not plumb a `--skill` arg through set-meta / add-edge: research workflows are fluid, and `/edit` exists as a designed escape hatch for "per user request" overrides — runtime enforcement here would either fight `/edit` or grow a long exception list."(`runtime/policy/writers.yaml:8-11`). 덧붙여 "When this file disagrees with reality, update the file (or the offending SKILL.md) — do not add runtime checks."(`:13-14`).
- 이유 (a), 남긴 문: 정체성 필드 잠금이 필요하면 "put it in tools/research_wiki.py::set_meta as a data-integrity check, not as a permission check driven by this file."(`writers.yaml:22-25`).
- 이력: v1.1.0(`1b2df1f`)에서 "declared writer permissions (advisory)"로 들어왔다. 같은 commit이 "7 entries in writers.yaml whose declared writer did not match the skill's actual SKILL.md behavior"를 고쳤다. 지금도 `derived_from: [ingest]`인데 `/ask`·`/paper-plan`·`/survey`가 쓰는 식으로 어긋난다(`writers.yaml:95`, `ask/SKILL.md:55-57`).

### W10. 병렬 수집은 잠금 대신 worktree 격리 + union merge + 사후 중복 제거

- 결정: `/init`은 논문마다 git worktree에서 subagent `/ingest`를 돌리고 순서대로 merge한다. 공유 파일은 append만 하고, `.gitattributes`가 4개 파일에 `merge=union`을 건다. merge 뒤 `dedup-edges`·`dedup-citations`가 중복 줄을 지운다.
- 대안: 단일 쓰기 큐, 파일 잠금, DB 트랜잭션, 직렬 ingest.
- 이유 (a): "The previous design ingested N papers sequentially … taking ~40 minutes for 10 papers. The bottleneck was intentional — later papers needed to read wiki state from earlier ones for concept dedup. This dedup can instead be handled at merge time by Claude"(PR #1). 기대치는 "Estimated speedup: ~3-5x for 10-paper inits (40 min → 8-12 min)"(`070d5e1`)이다.
- 이유 (a), union: "git's default line-based merge sees concurrent appends … reports add/add or content conflicts on EVERY merge — even though the resolution is always "keep both sides"."(`.gitattributes` 주석).
- [추정] 병렬 모드에서는 "만들기 전에 병합"이 형제 worktree 사이에서 작동하지 않는다. 형제는 서로의 새 개념을 볼 수 없다. fan-in에는 "Resolve true concept/method conflicts conservatively: merge, do not multiply near-duplicates."(`parallel-ingest.md:54`)라는 지시가 있지만 결정적 대조 명령은 없고, PR #1이 말한 merge 시점 해소는 "Claude resolves git conflicts"다. 그래서 slug가 다른 근사 중복은 LLM의 눈에만 맡겨진다(사례: fan-in 명령 목록에 `find-similar-concept` 없음 `parallel-ingest.md:51-70`, PR #1의 "handled at merge time by Claude", PR #1 본문의 "git conflicts", 3건).
- 한계: main의 기본 `.gitignore`(`1b2df1f`)는 `wiki/<kind>/*`와 `wiki/graph/*`를 추적하지 않는다(`.gitignore:57-79`). 그래서 scaffold commit(`parallel-ingest.md:14`의 `git add wiki/ …`)과 worktree commit은 페이지·엣지를 옮기지 못한다. worktree는 페이지가 빠진 commit에서 갈라지므로 subagent의 개념 대조도 빈 wiki를 상대로 돈다. merge=union이 실제로 걸리는 파일은 추적되는 `index.md`·`log.md` 둘뿐이고, fan-in의 `git worktree remove`(`:59-62`)가 worktree 안의 페이지를 함께 지운다.
- 한계, CI: CI auto-ingest(`.github/workflows/daily-arxiv.yml:283`)도 같은 이유로 페이지를 커밋하지 못하고, checkout된 wiki가 비어 있어 대조와 `build_wiki_profile`(`tools/daily_arxiv.py:487-493`)이 빈 wiki를 상대로 돈다. 이 장치를 쓰려면 사용자가 `.gitignore`를 고쳐 wiki 데이터를 추적해야 한다.
- 재현: 레포 밖 scratch 저장소에 같은 `.gitignore`를 두고 git 명령만으로 재현했다(레포 코드는 실행하지 않음). `git add wiki/`는 `wiki/index.md`만 stage했고, worktree commit에는 `wiki/log.md`만 들어갔으며, `git worktree remove`는 exit 0으로 무시된 페이지와 함께 worktree를 지웠다. 덧붙여 scaffold 명령은 무시된 `.checkpoints/*.json`을 명시적으로 넘기므로 `git add`가 exit 1로 끝났다.
- 이력: PR #1(`070d5e1`, 04-10)이 들어간 다음 날, test6 사고를 고친 `5f904b1`(PR #6, 04-11)이 들어왔다(W5).
- 이력, 이식 브랜치: Codex·OpenCode 이식 브랜치는 둘 다 직렬을 기본으로 되돌렸고 이유도 적었다. Codex는 "Use the parallel worktree contract only when the runtime can guarantee subagent working directories, per-paper commits, and fan-in merge control."이라고 적는다(`origin/autosci-codex:i18n/en/skills/init/references/parallel-ingest.md:3`) — 실행기가 subagent 작업 디렉터리, 논문별 commit, fan-in merge를 보장할 때만 병렬을 쓴다는 뜻이다. PR #6의 절대 경로 사고(W2)가 바로 작업 디렉터리를 보장하지 못해 격리가 깨진 사례다. OpenCode는 "Do **not** attempt in sandboxed environments where these operations are blocked."라고 적는다(`origin/autosci-opencode:i18n/en/skills/init/references/parallel-ingest.md:3`) — worktree·merge 같은 git 조작이 막힌 sandbox에서는 시도하지 말라는 뜻이다.
- 이력, 문서 충돌: main README도 "serially by default"라고 적지만(`README.md:482`) `init/SKILL.md:234`는 "all paper ingest must run through parallel `/ingest` subagents"다.

### W11. 파생 요약은 LLM 없이 통째로 다시 만든다

- 결정: `context_brief.md`, `open_questions.md`, `index.md`는 페이지 frontmatter와 정해진 H2 절을 긁어 매번 덮어쓴다. LLM 요약은 끼지 않는다.
- 대안: 바뀐 페이지만 갱신, 읽을 때마다 즉석 계산, LLM 요약.
- 이유 (a)는 없다. `compile_context` docstring "Replaces the old one-size-fits-all rebuild_context_brief with budget allocations tuned per skill category."(`tools/research_wiki.py:1266-1269`)는 skill마다 예산을 나눈 이유만 말하고, LLM 없이 통째로 다시 만드는 이유는 적지 않았다. `46cad0d`도 이 방식을 "full rebuilds, not append-only"라고 서술만 한다. 게다가 skill과 SPA는 `general` 예산 하나만 부른다(`:821-824`, `tools/serve.py:703`).
- 모르는 것: 이 방식을 고른 이유. v0.1(`20c61b9:tools/research_wiki.py:258-260`)부터 이 구조였으므로 작성자에게 물어야 안다.
- [추정] 통째 재생성은 사람이 파생물을 고쳐 원본과 어긋나는 일을 막으려는 것이다(사례: 두 파일 머리말 "_Auto-generated ... Do not edit._" `tools/research_wiki.py:164`, `:166`, 2건).
- 대가 (a): "no process **validates** whether they've fallen out of sync. Manual wiki edits bypass rebuild triggers entirely, and there's no staleness detection."(이슈 #41 메인테이너 Morrow-Yang의 답).
- 이력: claims를 지우면서 open_questions의 출처를 papers·topics·concepts 절로 바꿨다(`1b2df1f`).

### W12. 실패한 아이디어를 지우지 않고 기억한다

- 결정: 탈락·실패한 아이디어를 `status: failed` + `failure_reason`으로 남긴다. 다음 `/ideate`와 `/novelty`가 banlist로 읽는다(`ideate/SKILL.md:318`, `novelty/SKILL.md:165`). lint는 `failed`인데 reason이 빈 것을 🔴로 잡는다(`entities.yaml` `required_when`).
- 대안: 실패 아이디어 삭제, 실험 기록을 wiki 밖에 두기.
- 이유 (a): "one of the reasons we decided to include experiment executions in a "wiki" is that we figured out we could store failures and learned lessons … so we don't cold-start each experiment and watch it repeat the same mistakes."(이슈 #11 메인테이너 DanJoshua의 답). `check/SKILL.md:98`은 이를 "anti-repetition memory"라고 부른다.
- 이력: `failure_reason` 접두어가 `[filter]`(ideate), `[pilot]`(exp-pilot-eval), 없음(exp-eval) 세 갈래다(`ideate/SKILL.md:311-318`). `exp-pilot-eval`이 부르는 `proposed → failed` 전이는 lifecycle 표가 허용하지 않아 도구가 거부한다(`exp-pilot-eval/SKILL.md:82`, `entities.yaml:99`, `tools/research_wiki.py:1630-1637`). Codex 브랜치만 표를 고쳤다(`92f397e`).

### W13. 두 번째 LLM을 독립 심사자로 두고, 엇갈리면 보수적으로

- 결정: `/review`·`/novelty`·`/ideate`·`/exp-eval` 등은 MCP로 다른 모델(Review LLM)을 부른다(`grep -ln "Review LLM" .claude/skills/*/SKILL.md` → 이 넷 말고도 exp-run, paper-plan, paper-draft, research, poster, rebuttal, survey, setup). 주 에이전트의 점수는 보내지 않는다. 점수가 엇갈리면 낮은 쪽을 고른다.
- 대안: 같은 모델의 자기 검토(Review LLM이 없을 때 폴백으로만 허용, `[Claude self-review — no independent second opinion]` 표시, `cross-model-review.md:73-88`).
- 이유 (a): "Anchoring bias: If the Review LLM sees "Claude rated this 7/10", its review will cluster around 7." "Diversity of perspective: The entire value of cross-model review is that different models have different biases."(`shared-references/cross-model-review.md:26-28`).
- 이유 (a), 보수성: "When combining novelty or quality scores, take the **lower** score. Better to underestimate than to overcommit to a flawed idea."(`shared-references/cross-model-review.md:55`). `/novelty`("Take the lower of Claude's search-based score and Review LLM's score (conservative principle)", `novelty/SKILL.md:164`)와 `/exp-eval`("when Claude and Review LLM verdicts disagree, use the more conservative verdict.", `exp-eval/SKILL.md:285`)이 이 규칙을 따른다.
- 논문과의 관계: 논문 §3.3이 말하는 "independent reviewer agent"는 이 Review LLM이 아니라 paper 브랜치의 Trust Guard다(축 15). 논문은 novelty·idea 심사에 다른 모델을 쓴다고 적지 않는다(WebFetch arxiv.org/html/2605.31468).

### W14. 질의 답을 wiki로 되돌리되 기본은 끈다

- 결정: `/ask`는 답을 `outputs/`나 새 개념으로 쓸 수 있지만 `--crystallize`나 사용자 확인이 있을 때만 쓴다.
- 대안: 모든 답을 자동 저장, 답을 소스처럼 재-ingest.
- 이유 (a): "Good answers can be crystallized back into the wiki … so exploration compounds like ingestion does."(`ask/SKILL.md:9-11`). 쓰지 않을 신호는 "The answer relies primarily on inference rather than wiki evidence"(`:107`)다.
- 한계: `outputs`는 `entities.yaml` 9종에 들지 않아 lint가 보지 않는다.

### W15. claims 종류를 지우고 methods 종류를 만들었다

- 결정: v0.1의 claims(검증할 명제) 페이지를 없애고, 이름 있고 재사용되는 기법을 methods 페이지로 올렸다. 검증할 명제는 ideas가 맡는다.
- 이유 (a): "`claims` 和 `ideas` 语义重叠（两者都是「可验证的命题」），同时更有价值的 `methods`（跨论文复用的具名技术）没有实体"(이슈 #31) — claims와 ideas는 둘 다 "검증 가능한 명제"라 뜻이 겹치고, 더 가치 있는 methods(논문을 넘어 재사용되는 이름 붙은 기법)는 종류가 없었다는 뜻이다.
- 이유 (a), 생성 조건: "A `methods/` page is only justified when the technique is **named**, **reusable**, and **citable** by a future paper."(`ingest/SKILL.md:255`).
- 이력: v1.1.0 `1b2df1f`(05-06). 기존 claims는 "not migrated"(CHANGELOG 1.1.0). `find-similar-claim`과 동의어 정규화 표 `_CLAIM_CANONICAL_MAP`(`git show 5f904b1:tools/research_wiki.py:492-524`)도 함께 지워졌다. methods용 대조 도구는 만들지 않았다(`dedup-policy.md:27` "There is **no** `find-similar-method` tool.").
- 모르는 것: methods에 대조 도구와 `aliases` 필드를 두지 않은 이유. 이슈 #31 본문 전체(Open questions 포함)에도 이유가 없다. Open questions 네 항목은 `methods.type` enum 여부, `people.type` 구조, `/novelty --write` 기록, CHANGELOG 번호만 묻는다(`gh issue view 31 --json body`). 이슈 작성자 TomWhite-tgz에게 물어야 안다. 덧붙여 이슈 #31은 `methods.type`을 enum으로 고른 이유를 "优先可校验性"(검증 가능성 우선)이라고 적는다.

### W16. 웹 SPA는 skill을 흉내 내지 않고 같은 CLI만 부른다

- 결정: SPA의 쓰기 API는 skill이 부르는 것과 같은 도구 CLI를 subprocess로 부른다. PATCH 엔티티, POST 엣지·인용·로그, index·context-brief·open-questions 재생성은 `research_wiki.py`를 부른다(`tools/serve.py:586-733`). lint fix는 `tools/lint.py --fix`를(`:903-925`, `:172-176`), visualize 재생성은 `tools/visualize.py`를 부른다(`:705-706`, `:724-725`). lint fix는 페이지 frontmatter와 본문을 직접 고친다(`tools/lint.py:772`, `:811`, `:976`). skill 실행 버튼 대신 붙여 넣을 `/skill ...` 명령 문자열만 돌려준다(`tools/serve.py:21-36`, `:586-720`).
- 대안: SPA가 LLM API를 직접 불러 skill을 재현.
- 이유 (a): "Naive UX would silently call a different code path and produce results that diverge from /skill X's actual behavior. … no silent skill faking."(`tools/serve.py:42-52`). 엣지 메타도 "without hardcoding a parallel copy of runtime/schema/edges.yaml"(`:534-535`).
- 한계: 쓰기마다 `log.md`에 `frontend | <verb> <subject>`가 남지만 사람 이름은 없다(`tools/serve.py:149-155`). 기본 `127.0.0.1`이지만 인증은 없다(`:1046`, `:1054`).
- 한계, 접근 제한: docstring은 쓰기 API가 "loopback-only"라고 적지만(`tools/serve.py:21`) 코드는 요청 출처를 보지 않는다. `--host`로 바인딩 주소를 바꿀 수 있고(`:1046`), 요청 본문 파서는 Content-Type을 보지 않으며(`:366-381`), `client_address`·`Origin` 검사는 없다(`grep -n "client_address\|Origin" tools/serve.py` 결과 0).

### 그 밖의 결정 한 줄씩

| 결정 | 이유 원문 | 출처 |
|---|---|---|
| main은 가벼운 안정판, paper는 논문 스냅숏 | "main is the lean stable version; the full SciMem/SciFlow/SciDAG/SciEvolve system from the paper lives on the paper branch … not a finished product." | `03a78ee` |
| 원문은 `.tex` 우선, PDF는 합성 tex로 정규화 | "A PDF on its own is a poor ingest source … we still normalize the PDF into a synthetic `.tex` so the rest of `/ingest` works from one uniform input shape." | `pdf-preprocessing.md:7` |
| `raw/`는 사용자 소유, skill은 `raw/discovered/`·`raw/tmp/`에만 | "`raw/` deletes are irreversible: PDFs are not in git history." | `CLAUDE.md` Hard Rule 1, `reset/SKILL.md:97` |
| notes/web에서 나온 scaffold는 "임시" 표시 | "notes/web are authoritative for user intent, not for literature confidence" | `init/SKILL.md:137` |
| auto-ingest는 사용자·설정이 명시해야만 켠다 | "Never infer `auto-ingest` from repository state, branch name, existing workflow, or available credentials. The user/config/workflow input must choose it." 규칙만 있고 이유는 적혀 있지 않다 | `daily-arxiv/references/recommendation-and-ingest-policy.md:59-60` |
| skill 문서를 SKILL.md + references로 쪼갬 | "Added level 3 references. It's no longer a single verbose SKILL.md." | PR #22, `ingest/SKILL.md` 434줄(`e37d86a`) → 230줄(`0366aea`) |
| 테스트 전부 삭제(이후 일부 다시 씀) | 메시지는 "Rebuild ingest. Deleted tests."뿐이다 | `b36c1df`, `git ls-tree -r b36c1df tests/` 결과 없음 |

`b36c1df`가 지운 `tests/` 16,172줄 가운데 9,770줄은 skill 문구 테스트(`test_skill_*`·shared_references·conftest)이고, 6,402줄은 도구 테스트다(`test_research_wiki.py` 2,000, `test_init_discovery.py` 1,244, `test_lint.py` 795 등; `git show --numstat b36c1df -- tests/` 집계).

[추정] skill 문구를 문자열로 검사하던 테스트는 ingest를 다시 쓸 때마다 깨졌기 때문에 지운 것으로 보인다(사례: `5f904b1` "tests/test_skill_init.py: +40 lines verifying the new Step 4.5 … language is present in all three copies", `5243790` "relaxed it to accept the new two-tier phrasing", 2건). 도구 테스트까지 지운 일은 이 추정으로 설명되지 않는다.

모르는 것: 도구 테스트를 지운 이유. PR #26 작성자에게 물어야 안다.

## 축별 분석

축 이름과 뜻은 앞선 9개 구현 비교 문서(`llm-wiki-implementations/lab/reports/00-comparison.md` #설계 축별 스펙트럼)를 따른다.

### 1. 실행 형태

비교 문서의 "skill + 결정적 CLI·스크립트" 칸에 든다. Claude Code `/skill` 29개가 `tools/research_wiki.py` CLI를 Bash로 부른다.

여기에 웹 SPA(`tools/serve.py`), Review LLM MCP 서버, GitHub Actions 일일 추천이 붙는다. 쓰기 표면은 셋(skill, SPA, CI)이지만 SPA는 같은 도구 CLI를 부르고 CI는 `/ingest` skill을 부른다(W16, `daily-arxiv/SKILL.md:59-79`).

치르는 것은 런타임 의존이다. 병렬 ingest가 Claude Code의 subagent 기능과 git worktree에 묶여, Codex·OpenCode 이식에서는 직렬로 되돌렸다(W10).

### 2. 규칙의 위치

엣지는 쓰기 직전 코드 거부, 페이지는 프롬프트 + 사후 lint다(W3).

lint는 🔴가 있으면 exit 1이지만(`tools/lint.py:1166`) 도는 곳은 셋이다: 수동 `/check`, `/init` fan-in, 웹 SPA의 `/api/lint`·`/api/lint/fix`(`tools/serve.py:340-343`, `:409-410`, `:903-925`)다. 셋 다 사람이나 skill이 직접 불러야 돈다. CI auto-ingest는 lint 없이 커밋한다(이슈 #41).

규칙을 코드로 옮긴 이유를 작성자가 직접 적은 곳이 둘이다: 개념 중복(`5f904b1` "dedup from memory, which silently fails on paraphrase")과 worktree 재생성(`46cad0d` "relied on prompt discipline alone").

### 3. 저장 구조

페이지 종류 9개를 디렉터리로 나누고(`wiki/<kind>/`), 메타데이터는 frontmatter에, 그래프는 별도 JSONL에 둔다. 그래프는 세 갈래다: 의미·작업 흐름 엣지(`edges.jsonl`), 서지 인용(`citations.jsonl`), frontmatter 링크 투영(`tools/research_wiki.py:586-691`).

세 번째 갈래인 투영은 파일로 저장되지 않는다. `rebuild-projected-edges`를 부르는 skill·SPA·CI가 없고(`grep -rl rebuild-projected-edges .claude/skills tools app .github` → `research_wiki.py`뿐), SPA `/api/graph`가 요청마다 계산한다(`tools/serve.py:520-525`).

세 갈래를 합쳐 보는 곳은 SPA `/api/graph`뿐이다(`tools/serve.py:503-530`). CLI의 `neighbors`·`compile_context`는 edges.jsonl만 본다(`tools/research_wiki.py:1192`).

실제로 쓰이는 파생 상태 파일은 셋(index, context_brief, open_questions)이고 작업 상태 파일(checkpoints, pipeline-progress)이 따로 있다.

### 4. Ingest

사람 참여는 없다(`/init`도 최종 선택을 LLM이 한다). 증분 판정은 같은 slug 페이지에 arXiv ID나 제목이 맞으면 "이미 있으면 멈춤"뿐이고, 이 판정도 LLM이 한다. 원문 해시는 보지 않는다(`ingest/SKILL.md:113`).

직접 ingest는 실패해도 되돌리지 않고 부분 결과를 남긴다(`error-handling.md:38`, `:57`). INIT MODE는 부분 실패한 worktree를 커밋하지 않아 merge되지 않는다(`:41`). 감시(watch)는 없다. 대신 `/discover`와 `/daily-arxiv`가 새 후보를 고른다.

입력은 arXiv URL·`.tex`·`.pdf`뿐이다(`ingest/SKILL.md:22`). PDF는 `tools/prepare_paper_source.py`(758줄)가 합성 tex로 바꾸는데, 문서 구조를 복원하지 않는다. 추출 텍스트를 12만 자에서 자르고(`:463`), 본문을 6만 자에서 잘라 `\section{Recovered Text}` 절 하나에 넣는다(`:476`, `:484`).

notes/web 같은 비논문 문서는 `/init` Step 4에서 한 번 scaffold로만 읽힌다(`init/SKILL.md:131-150`). `/edit`은 웹 문서를 `raw/web/`에 저장하고 "can later be incorporated into the wiki via `/ingest`"라고 권하지만(`edit/SKILL.md:34`, `:42`) `/ingest`는 그 형식을 받지 않는다. `/init` 뒤 비논문 문서의 증분 경로는 없다.

소스당 페이지 수는 상한이 있다: 새 개념 1~3, 새 방법 1~2(`ingest/SKILL.md:251-254`). 상한을 넘는 후보는 가까운 항목에 병합하거나 버린다.

`dedup-policy.md:52`는 버린 후보를 "`/check` will surface the resulting gaps"라고 적지만, `/check`가 보는 것은 importance 5 논문에 개념이 없는 경우뿐이다(`check/SKILL.md:129`). 메인테이너도 이를 "known blind spot"이라고 인정했다(이슈 #41). 그래서 버린 후보는 어디에도 남지 않는다.

### 5. 근거 추적 단위

논문 단위다. 개념은 `key_papers`, 방법은 `source_papers`로 논문 목록을 가리킨다(`entities.yaml:45`, `:115`). 청크·문장·줄 위치를 가리키는 필드는 main의 어느 종류에도 없다.

의미 엣지는 `evidence`를 필수로 받지만 자유 문자열이다(`edges.yaml:31`). 형식이 인용인지 위치인지 정하지 않는다.

paper 브랜치는 작업 흐름 엣지 4종에 `source_path`·`source_span`·`artifact_hash`를 선택 속성으로 더했다(`9c792ef`). 논문→개념 엣지에는 여전히 없다.

### 6. Link

링크는 LLM이 건다. 페이지 사이 wikilink `[[slug]]`와 frontmatter 링크 필드, 그리고 타입 있는 엣지(16종)가 있다.

엣지 종류는 schema가 닫아 두고 도구가 거부한다(W3). 역링크는 LLM이 같은 턴에 쓰고 lint가 채운다(W8).

그래프 계산은 결정적이다(투영·BFS·연결 수). wikilink는 종류 없이 slug만으로 풀린다. 두 종류에 같은 slug가 있으면 lint는 뒤의 것으로 덮어쓴다(`tools/lint.py:160-170`). 프런트는 우선순위 표로 푼다(`app/modules/schema.js:19-25`).

frontmatter 파서가 도구마다 따로 있다(`research_wiki._parse_yaml_block`, `lint.extract_frontmatter`, `visualize._parse_yaml_block`, `discover.py` 줄 정규식 등). 같은 파일을 도구마다 다르게 읽을 수 있다.

### 7. Lint

결정적 lint(`tools/lint.py`)와 LLM 판단(`/check` Step 6)을 나눈다. 결정적 lint는 🔴/🟡/🔵 등급과 exit code를 갖는다. 자동 수정은 역링크 대칭과 기본값 있는 필수 필드 둘뿐이다(`tools/lint.py:815-832`).

LLM 판단(근사 중복, 모순, 낡은 SOTA)은 "not yet implemented in the automated linter -- they remain aspirational"(이슈 #41)이다.

코드 추적으로 본 구멍이 있다(실행 안 함): 블록형 YAML 리스트를 forward로 못 읽고(`:343-406`), 본문 절 규칙이 절 이름을 무시하며(`:377`), 역링크 존재를 부분 문자열로 판정한다(`:438-439`). 자동 수정이 쓰는 맨 slug는 고아 검사가 세는 `[[...]]`와 형식이 달라서 고친 뒤에도 고아로 남을 수 있다(`:962`, `:58`).

enum 검사 목록은 YAML이 아니라 코드에 박혀 있어(`:251-258`), YAML에 새 enum 필드를 더해도 lint가 보지 않는다.

### 8. stale·모순 처리

페이지는 제자리 덮어쓰기이고 이력은 git에 맡긴다. 낡음 표시는 사실상 둘이다: concept `maturity: deprecated` 값과 `/check` LLM의 "6개월 넘은 SOTA·Recent work" 판단(`check/SKILL.md:133-140`)이다.

context_brief에 "Stale" 절 코드(30일, 10개, `tools/research_wiki.py:1375-1399`)가 있지만, `ideation`·`review` 예산에서만 켜진다. skill과 SPA가 부르는 `general` 예산은 Stale 예산이 0이라(`:1250`, `:1376` `if b_stale > 0:`) 이 절은 만들어지지 않는다.

모순은 `contradicts` 엣지(작업 흐름 무리)로 표현할 수 있고, `/check` LLM이 페이지 간 모순을 찾아 보고만 한다. 해소를 강제하는 코드는 없다.

원문 변경 감지는 없다. 메인테이너도 "What drifts undetected: a concept's definition evolving while linking papers still describe the old version."이라고 인정했다(이슈 #41).

같은 레포의 Hiera 사이드카만 run 시작 때 읽은 wiki 입력 페이지(experiment·idea·design)의 sha256 스냅숏을 남기고, 실행 중 바뀌면 그 run을 거부한다(`tools/hiera/adapter.py:140-189`, `evaluator.py:109-117`). 낡은 파생 페이지를 표시하거나 퍼뜨리지는 않는다. paper 브랜치 `/dream`은 지우지 않고 `scievolve_memory_weight: downweighted`로 낮춘다.

### 9. 사람 개입

비용이 크거나 되돌릴 수 없는 일 앞에만 게이트가 있다. 실험 코드 배포 전(`exp-run/SKILL.md:9`), pilot 실행 전(`exp-pilot-run/SKILL.md:10`), 설계 확정(`exp-design/SKILL.md:272`), `/reset`(`reset/SKILL.md:59`)이 그 자리다.

`/ask` 결정화(`ask/SKILL.md:182`), `/check` 비결정 수정(`check/SKILL.md:174`), auto-ingest opt-in(`daily-arxiv/SKILL.md:26`)에도 사람 확인이 있다.

`/research --auto`는 Gate 1·2를 자동으로 넘기지만(`i18n/en/skills/research/SKILL.md:23`), `/exp-run`의 수동 검사는 "No matter which operation mode it is"(`exp-run/SKILL.md:9`)다.

ingest 안의 병합 판단(0.40~0.80 구간)에는 사람이 없다. 승인 대기열 파일도 없고, `/check` 보고서가 그 역할을 한다.

본체 wiki는 승인을 대화에서만 받는다. 승인 표시를 데이터로 남기지 않으니 agent가 승인 표시를 위조할 자리도 없다. 대신 승인 기록도 없다.

같은 레포 Hiera는 승인을 데이터로 남긴다. `--approve` 때 계약 내용의 digest를 고정하고(`tools/hiera/contract.py:231`, `tools/hiera/cli.py:347-357`), 실행 전에 승인 여부와 digest 변화를 검사해 "run has no approved contract"·"approved contract changed after approval"로 거부한다(`contract.py:242-248`).

기본 설정은 `Bash(*)`·`Edit(*)`·`WebFetch(*)`·`MCP(*)`를 모두 허용해 skill 실행 중 권한 프롬프트가 나오지 않는다(`config/settings.local.json.example`, 이슈 #45).

### 10. 동시성·안전

worktree 격리 + `merge=union` + 사후 dedup이 유일한 동시성 장치다(W10). 잠금은 없다: `add-edge`는 파일 끝에 append만 하고(`tools/research_wiki.py:350-351`), `set-meta`는 읽고-고치고-통째로 쓴다(`.tmp` 뒤 `replace`, `:2411-2438`).

batch 엣지 쓰기는 하나라도 틀리면 아무것도 쓰지 않는다(`batch-edges` `:1804-1808`). 다만 어느 skill도 `batch-edges`를 부르지 않는다.

[추정] 이 설계는 "한 사람이 한 세션에서 쓰거나, 병렬이면 반드시 worktree"를 전제한다(사례: worktree 가드 `:791-818`, `merge=union` 4파일, 잠금을 쓰는 곳은 Hiera ledger뿐 `tools/hiera/ledger.py:56`, 3건).

도구 제한은 없다(축 9의 허용 설정).

### 11. Query·검색

LLM이 `index.md`·`context_brief.md`를 읽고 상위 15쪽을 고르는 방식이다. 임베딩·BM25·그래프 탐색을 쓰지 않는다(#query — 질문 → 답). 원문으로 내려가지 않고 wiki 페이지까지만 읽는다.

답은 기본으로 저장하지 않고, 결정화할 때만 `outputs/`나 개념으로 되돌린다(W14).

BM25는 `discover.py` venue 모드에만 있다(`tools/discover.py:523-677`, 제목 4.0·frontmatter 1.5·본문 1.0 가중). 이것은 "어느 외부 논문을 넣을까"에만 쓰고, 새 페이지를 기존 페이지와 잇는 데는 쓰지 않는다.

### 12. index·log 관리

index는 두 길로 생긴다. ingest 때 LLM이 한 줄 덧붙이고, `rebuild-index`가 frontmatter에서 결정적으로 통째 다시 만든다(`tools/research_wiki.py:1823-1885`). `rebuild_index`는 `title`만 적어서 `name`을 쓰는 methods·people은 index에 이름이 빠진다(`:1843-1845`).

log는 도구 `log` 명령이 `## [YYYY-MM-DD] {message}`로 append한다(`:2080-2094`). 행위자 필드는 없다. `conventions.yaml:18`의 `log_grammar`는 코드가 읽지 않는다.

둘 다 `merge=union` 대상이다.

### 13. 포맷 표준

OKF 대응은 없다. 형식은 YAML frontmatter + `[[slug]]` wikilink + Obsidian 호환이다(`/visualize`가 `.obsidian/*`, `canvases/*`를 쓴다).

OKF의 `generated`/`verified` 구분, `stale_after`, `sources[].id` footnote에 해당하는 필드가 없다. 대조한 범위는 `runtime/schema/entities.yaml`의 9종 전 필드와 `edges.yaml`의 엣지 속성이다. 근거가 엣지 장부(`edges.jsonl`)에 있으므로 OKF로 옮기려면 엣지를 frontmatter `sources`로 펼치는 투영이 필요하다.

### 14. 규모·비용

ingest 1회의 토큰·시간·금액 측정값은 없다. 유일한 수치는 PR #1의 추정 "~40 minutes for 10 papers" → "8-12 min"이다.

비용을 누르는 장치: ingest 안에서 wiki 전체를 읽지 않게 한다("Do not read the entire `wiki/` … the time and token cost is large", `cross-references.md:98`). `/ask`는 15쪽 상한, context_brief는 8,000자 상한이다(`tools/research_wiki.py:1404-1412`). skill 문서를 references로 쪼개 필요할 때만 연다(PR #22).

페이지 수에 비례하는 단계: `find-similar-concept`는 부를 때마다 concepts·foundations 전체 파일을 읽는다(`:1038-1056`). `rebuild-*`는 매번 전 페이지를 읽는다. 둘 다 LLM을 쓰지 않아 토큰 비용은 아니다.

규모 한계는 실측이 없다. 메인테이너 Morrow-Yang의 답은 "a well-organized markdown folder starts out equivalent, but diverges as the collection grows."(이슈 #42)다.

### 15. frosk1 비판 대응

| 비판 | 강도 | 이 레포의 대응 | 근거 |
|---|---|---|---|
| 1 오류 누적 | 부분 | 엣지는 쓰기 전 거부, Review LLM 독립 심사. 페이지 내용 오류는 main의 사후 lint로도 못 잡는다. paper 브랜치는 ingest마다 모든 새·수정 페이지에 Trust Guard(결정적 form check + 독립 LLM content check, BLOCK이면 `raw/tmp/quarantine/` 격리와 `trust_events.jsonl` 기록)를 필수로 돌린다. 다만 페이지는 쓴 뒤 검사이고, 엣지 `--gate`만 opt-in이다 | W3, W13, `origin/paper:i18n/en/skills/ingest/SKILL.md:73`, `:199-210`, `origin/paper:tools/trust_guard.py:1-8` |
| 2 부분 문맥 | 부분 | 개념 대조는 전체 concepts·foundations를 결정적으로 훑는다. 나머지 판단은 index·context_brief와 개별 페이지만 본다 | W5, `tools/research_wiki.py:1038-1056`, `ask/SKILL.md:75-81` |
| 3 요약 손실 | 부분 | `raw/`는 사용자 소유로 보존한다. query는 원문으로 내려가지 않는다 | `conventions.yaml:20-22`, #query — 질문 → 답 |
| 4 가짜 SoT | 약 | 답은 `[[slug]]`로 wiki를 인용한다. 원문 위치 인용과 낡음 표시가 없다. README가 wiki를 "Compiled once, maintained forever"라고 부른다 | `ask/SKILL.md:83-94`, 축 5·8, `20c61b9:README.md:32-42` |
| 5 환각 병합 | 부분 | 의미 엣지에 evidence·confidence 필수, "Graph noise is worse than a missing edge". 0.40~0.80 병합 판단은 LLM 혼자 한다 | W7, `cross-references.md:79`, `dedup-policy.md:33-38` |
| 6 운영 복잡도 | 악화 | skill 29개, Python 2만 줄, MCP 서버, 두 언어 사본. 사본끼리 어긋난 사례가 있다 | #한눈에 규모 행, `.claude/skills/research/SKILL.md:10`과 `i18n/en/skills/research/SKILL.md:10` |
| 7 ingest 비용 | 부분 | 병렬 ingest, wiki 전체 읽기 금지, 생성 한도. 측정값은 없다 | W10, `cross-references.md:98`, `ingest/SKILL.md:251-254`, 축 14 |

### 16. 성숙도·차용 가능성

MIT라 코드째 가져올 수 있다. 단독으로 떼어 쓸 만한 코드는 `runtime/loader.py`(237줄)와 `find_similar_concept` 주변(약 130줄)이다. 나머지는 테스트가 없어(`b36c1df`) 가져오면 테스트를 새로 써야 한다.

활동은 활발하다(마지막 push 2026-10-02, 별 1,698). 다만 wiki 계약은 5월 말 뒤로 멈췄고, 최근 작업은 런타임 이식과 Hiera 쪽이다.

문서와 코드가 어긋난 곳이 많다. 아래 표는 보고서에 영향이 큰 것만 고른다.

| 어긋남 | 출처 |
|---|---|
| `exp-pilot-eval`이 `proposed → failed` 전이를 부르지만 lifecycle 표가 허용하지 않아 도구가 거부한다 | `exp-pilot-eval/SKILL.md:82,133`, `entities.yaml:99`, `tools/research_wiki.py:1630-1637` |
| `.claude/skills/research/SKILL.md`(활성)와 `i18n/en/skills/research/SKILL.md`(원본)가 다르다. 활성본은 빈 wiki에서 5편을 자동 ingest하고, 원본은 `/init`으로 넘긴다 | `diff -r .claude/skills i18n/en/skills`, `9b00adf` |
| README는 `/init`이 직렬이 기본이라 하고 skill은 병렬이 필수라 한다 | `README.md:482`, `init/SKILL.md:234` |
| 문서는 slug 충돌을 "numeric suffix via the tool"로 푼다고 하지만 그 코드가 없다 | `init-mode.md:34`, `tools/research_wiki.py:105-129` |
| `find-similar-concept` 주석의 "0.40-0.84 Jaccard"와 코드의 두 구간 식이 다르다. 처음 도입한 `5f904b1`부터 달랐다 | `tools/research_wiki.py:978`, `:1030-1035` |
| `CONTRIBUTING.md`가 가리키는 `docs/extending.md`와 테스트 파일이 없다 | `CONTRIBUTING.md`, `git log --all -- docs/extending.md` 빈 결과 |
| PR #30은 SPA PATCH에 schema 검사가 있다고 했지만 코드에 없다 | PR #30, `tools/serve.py:588-644` |
| 문서는 index도 "index updates" 도구로 append한다고 하지만 그런 명령이 없고, skill은 LLM에게 index를 직접 고치게 한다 | `init-mode.md:33`, `tools/research_wiki.py:2772-2853`, `ingest/SKILL.md:190` |
| INIT MODE는 논문↔논문 단계와 topic 쓰기를 "부모가 fan-in에서 처리"한다며 건너뛰지만, fan-in은 `cites`만 되채우고 `topic-backfill`은 `7090a22` 이후 어느 skill도 부르지 않는다 | `ingest/SKILL.md:171`, `init-mode.md:15`, `init/SKILL.md:184-197`, `tools/research_wiki.py:1892-1912` |
| 한도를 넘어 버린 개념 후보를 "`/check` will surface"한다고 하지만 `/check`는 importance 5 논문의 개념 누락만 본다 | `dedup-policy.md:52`, `check/SKILL.md:129` |
| `parallel-ingest.md`의 `git add wiki/`와 merge=union 4파일 설계가 기본 `.gitignore`와 맞지 않아 페이지·엣지를 옮기지 못한다 | `.gitignore:57-79`, `init/references/parallel-ingest.md:14`, W10 |
| 손으로 짠 frontmatter 파서의 이유("no PyYAML dependency")는 loader가 PyYAML을 쓰기 시작한 뒤 성립하지 않는다 | `tools/research_wiki.py:2156`, `runtime/loader.py:27` |

## 엔터프라이즈 llm-wiki에 비추어

조건은 회사 안 여러 사람이 쓴 보고서를 넣고 잇는 것이다. 작성자마다 같은 대상을 다른 용어로 쓰고, 형식이 없는 문서가 섞인다. 사용자 목표는 "어느정도 사람이 하더라도 성능을 보장(raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조)"이다.

| 조건 | 이 레포가 주는 답 | 빈 곳 |
|---|---|---|
| 다중 작성자 | 공유 파일은 append, `merge=union`, 사후 dedup으로 다룬다(W10). 엣지·인용은 SPA와 skill이 같은 도구 CLI로 쓴다(W16) | 행위자 기록이 없다. `log.md`는 날짜와 자유 문자열뿐이고(`tools/research_wiki.py:2088`), 엣지 행에도 작성자 필드가 없다(`:338-348`). 잠금이 없어 상시 동시 쓰기에 맞지 않는다. linked worktree에서 도구가 거부하는 명령은 둘뿐이고, 같은 파일을 쓰는 `compile-context`·`rebuild-index`는 프롬프트 규칙으로만 금지된다(W2). index는 LLM이 직접 고친다(W3). 기본 `.gitignore`가 wiki 데이터를 추적하지 않아 git 기반 병렬 수집은 그대로는 페이지·엣지를 옮기지 못한다(W10). 사람 요청 경로 `/edit`은 도구를 부르지 않아(`edit/SKILL.md:29-49`), 개념 대조·엣지 검사·행위자 기록 없이 페이지·index·log를 LLM이 직접 고친다. 사람이 끼는 경로가 가장 약하다 |
| 용어 불일치 | `/ingest`는 개념을 만들기 전에 결정적 별칭 대조를 하고, 기본은 병합이며, 문서당 생성 한도를 둔다(W5). 범용어는 foundation 계층으로(W6). `match_reason`이 판정 근거를 보여 준다(`tools/research_wiki.py:1068-1076`) | `/ask` 결정화(`ask/SKILL.md:135-140`), `/init` scaffold(`init/SKILL.md:146`)는 대조 도구 없이 concept를 만들고, `/edit`도 대조 도구를 부르지 않는다. 별칭은 concepts·foundations에만 있다. methods·people·topics에는 없다. `tags`(6종 필수, `entities.yaml:25` 등)는 통제 어휘도 정규화도 없는데, 논문→topic 소속이 태그 일치로 정해진다(`ingest/SKILL.md:185`; 도구 쪽 규칙도 소문자화만 한 교집합이다, `research_wiki.py:1899-1902`). 대조가 `[^a-z0-9\s]` 정규화라 한글 이름은 점수 0, slug는 `untitled`가 된다(`:120-127`, `:987`, `:999`; 코드 추적, 실행 안 함). `/ask`는 별칭을 보지 못한다. 동의어 정규화 표는 claims와 함께 지워졌다 |
| 형식 없는 문서 | notes/web 출처 페이지를 "Provisional note"로 표시하고 논문 근거가 앞선다고 정했다(`init/SKILL.md:137`, `:233`). PDF는 LLM이 먼저 정체를 잡고 합성 tex로 정규화한다(#그 밖의 결정 한 줄씩) | `/ingest`는 arXiv·tex·pdf만 받아, notes/web 같은 비논문 문서는 `/init` 때 한 번 scaffold로만 들어오고 그 뒤 증분 경로가 없다(`ingest/SKILL.md:22`, `init/SKILL.md:131-150`, `edit/SKILL.md:42`). PDF 정규화(`tools/prepare_paper_source.py:469-487`)는 본문을 절 하나로 뭉치고 6만 자에서 잘라 문서 구조와 뒷부분을 잃는다. 임시 → 확인 승격 절차가 없다. `open_questions`는 정확한 H2 이름과 `-` 글머리에만 반응해(`tools/research_wiki.py:875`, `:882`) 형식 없는 문서는 통째로 빠진다. 근거 단위가 문서 전체라 위치 추적이 안 된다. 외부 정체 확인처(arXiv·S2)가 사내에는 없다 |
| 연결 후보 생성 | 논문↔논문 의미 엣지는 S2 references/citations로 찾은 후보 안에서 LLM이 고른다(`ingest/SKILL.md:173-181`) | 서로 인용하지 않는 두 문서 사이의 연결을 찾는 후보 생성 단계가 없다. ingest에는 임베딩·BM25로 기존 페이지를 고르는 단계가 없고, INIT MODE는 이 단계 자체를 건너뛴다(`:171`). 외부 인용 그래프가 없는 사내 문서에는 개념 대조와 태그→topic 두 길만 남는다. 기존 wiki를 상대로 BM25 점수를 내는 코드는 `discover.py`에 있지만(`tools/discover.py:562-677`) 외부 후보 선별에만 쓰인다 |
| 권한 | `writers.yaml`에 누가 무엇을 써야 하는지 적는 형식은 있다(W9) | 일부러 강제하지 않았다. 근거("research workflows are fluid")는 단일 연구자 전제라 사내 조건에서는 성립하지 않는다. 기본 설정이 모든 도구를 허용하고 SPA에 인증이 없다. SPA docstring의 "loopback-only"는 강제되지 않는다(W16, `serve.py:21`, `:1046`, `:366-381`) |
| 규모 | 파생물 결정적 재생성, 질의 15쪽 상한, ingest 중 wiki 전체 읽기 금지(축 14) | 측정이 없다(이슈 #42). 검색이 LLM의 index 읽기라 index가 커지면 버틸 근거가 없다. 그래프 탐색에 허브 차단이 없다(`tools/research_wiki.py:1184-1237`). 테스트가 없다 |

### 가져올 것

| 아이디어 | 맞는 이유 | 코드 위치 |
|---|---|---|
| schema를 YAML로 선언하고 loader가 검사 상수를 만들어 쓰기 직전에 거부 | 관계 이름·endpoint·근거 필수를 "추출 뒤 정리"가 아니라 쓰기 시점에 끊는다. 작성자가 많아도 관계 종류가 흩어지지 않는다. 단 페이지 쓰기에도 같은 관문을 둬야 한다 | `runtime/schema/edges.yaml`, `runtime/loader.py:165-220`, `tools/research_wiki.py:246-307` |
| 생성 직전 결정적 별칭 대조 + "기본은 병합" + 비대칭 비용 논리 | 용어 불일치는 곧 근사 중복 폭증이다. PR #6의 45/37 사례가 사내 상황과 같다. 사내 용어집(정식 이름 + 별칭)을 입력으로 쓰고, 한글 토큰화와 모든 엔티티 종류·태그의 별칭을 더한다. 개념을 만드는 모든 경로(질의·초기화·사람 편집)가 같은 대조를 거치게 한다. "기본은 병합"은 분리·병합 취소 도구와 페이지 이력을 함께 둘 때만 싸다(W5) | `tools/research_wiki.py:956-1118`, `ingest/references/dedup-policy.md:33-52` |
| 범용어 terminal 계층을 사람이 미리 심기 | 회사명·"프로젝트"·"고객" 같은 사내 범용어가 허브가 되는 것을 막는다. foundation 문턱을 개념 병합 문턱보다 낮게 둔다. 그래프 탐색에서도 terminal 경유를 빼야 효과가 난다. 시드 목록 파일이 용어집 입력 자리다. 다만 `slug`·`title`·`summary`만 있고 별칭 필드가 없으며(`grep -c aliases` 결과 0), 본문 출처가 Wikipedia라(`prefill/SKILL.md:55-62`) 별칭과 사내 출처를 더해야 한다 | `runtime/schema/entities.yaml:171-183`, `xref.yaml:78`, `.claude/skills/prefill/foundations-catalog.yaml`(74줄) |
| 프롬프트 규칙이 깨진 자리를 도구 거부로 승격 | 사람이 섞여 쓰면 프롬프트 규율은 더 쉽게 깨진다. 권한 검사도 같은 자리(쓰기 CLI)에 둔다. 여기서는 두 명령에만 걸렸으니(W2), 같은 파일을 쓰는 모든 명령에 걸어야 한다 | `tools/research_wiki.py:791-818`, commit `46cad0d` |
| 서지(결정적 키) 연결과 의미(LLM 판단) 연결을 다른 파일로 | 문서 번호·티켓·프로젝트 코드로 생기는 연결과 "같은 문제를 다룸"을 섞지 않는다. 결정적 연결은 재현되고, 의미 연결만 검토하면 된다. 단 의미 연결의 후보를 서지 연결에서만 뽑으면 인용 없는 문서끼리는 이어지지 않는다. `discover.py`의 wiki 대상 BM25를 ingest 안의 후보 생성으로 옮기는 것이 차용 후보다 | `tools/research_wiki.py:379-550`, `conventions.yaml:27-30`, `tools/discover.py:562-677` |
| 의미 엣지에 `confidence`·`evidence` 필수 + "의심되면 잇지 않는다" | 검토자가 "왜 이었나"를 볼 수 있다. 허브성 근거("둘 다 LLM을 씀")를 프롬프트에서 막는다 | `edges.yaml:25-91`, `cross-references.md:56-82` |
| SPA·에이전트가 같은 도구 CLI를 부르는 쓰기 경로 | 엣지·인용은 UI에서 써도 같은 검사를 지난다. 비교 문서가 짚은 "쓰기 표면마다 규칙이 갈라지는" 문제를 엣지에서는 피한다. 단 frontmatter PATCH(`set-meta`)는 검사가 없고(`tools/research_wiki.py:2404-2443`), 본문·index는 LLM·`/edit`·Obsidian이 CLI 밖에서 고친다. 단일 경로가 되려면 페이지 쓰기 명령이 먼저 있어야 한다 | `tools/serve.py:42-52`, `:586-733` |
| 공유 파일 append-only + union merge + 재생성은 주 작업 공간에서만 | 배치 수집을 여러 명이 동시에 해도 log·edges가 깨지지 않는다. 단 wiki 데이터를 git에 추적한다는 전제에서만 맞다. 이 레포의 기본 `.gitignore`는 그 전제를 깬다(W10) | `.gitattributes`, `tools/research_wiki.py:711-784` |
| 쓰기 관문의 PASS/WARN/BLOCK 판정 + 격리 폴더 + 판정 이벤트 로그(paper 브랜치 Trust Guard) | 페이지마다 결정적 form check(lint 재사용)와 독립 LLM content check를 돌리고, BLOCK이면 격리하고 모든 판정을 로그로 남긴다. "페이지 쓰기에도 같은 관문"의 구현 예다. 다만 쓴 뒤 검사이므로 사내에서는 쓰기 전으로 옮긴다. paper 브랜치도 MIT다 | `origin/paper:tools/trust_guard.py`(247줄), `origin/paper:i18n/en/skills/ingest/SKILL.md:199-210` |
| 실패 기억(`failure_reason` 필수 + banlist) | "이미 해 봤는데 안 된 것"이 보고서끼리 이어진다. 사내 결정 문서에 그대로 맞는다. 단 main은 pilot 실패(`proposed → failed`)를 lifecycle 표가 막아 기록이 끊긴다(`entities.yaml:99`, W12). 상태 표를 호출부와 함께 맞춘다 | `entities.yaml:78-101`, `ideate/SKILL.md:318`, `:507-509` |
| 질의 답 결정화(기본 off, 확인 뒤 저장) | 질의가 찾은 새 연결고리를 wiki에 남긴다. 사용자 목표의 "연결고리 발견"에 바로 닿는다. 저장 대상도 schema 안에 넣는다 | `ask/SKILL.md:96-148` |
| Hiera의 입력 sha256 고정 | 작업이 읽은 wiki 페이지의 해시를 시작 때 남기고, 바뀌면 그 작업을 거부한다. 낡음 표시·전파는 하지 않으므로, 파생 페이지마다 `sources[].hash`를 남기고 비교하는 장치로 넓혀야 낡음 감지가 된다 | `tools/hiera/adapter.py:166-189`, `evaluator.py:109-117` |
| 승인 = 내용 digest 고정 + 실행 전 재검사(Hiera) | 승인을 대화가 아니라 데이터로 남기고, 승인 뒤 내용이 바뀌면 실행을 거부한다. 사내 승인 기록과 "승인 뒤 몰래 바뀐 문서" 방지에 바로 쓴다. paper 브랜치 `consolidate_memory.py`의 propose → 승인 → apply와 견주어 고른다 | `tools/hiera/contract.py:76`, `:231`, `:242-248`, `tools/hiera/cli.py:347-357` |
| paper 브랜치의 "제안 → 승인 → 되돌릴 수 있는 메타데이터로만 적용" 사후 병합 | 남이 쓴 페이지를 지우지 않고 정식 페이지를 가리키는 표시와 가중치 낮춤으로 병합한다. 승인 대기열 모양이다 | `origin/paper:i18n/en/skills/dream/references/memory-operations.md:26-29`, `origin/paper:tools/consolidate_memory.py` |

### 피할 것

- 권한을 명세로만 두는 것(`writers.yaml` "SPEC, NOT A RUNTIME GATE"). 근거가 단일 연구자 전제라 사내 조건에서 무너진다. 쓰기 CLI가 actor를 받아 거부하고 로그·엣지에 남겨야 한다.
- 페이지를 LLM이 직접 쓰게 두고 사후 lint에 맡기는 것. 엣지만 막으면 frontmatter 오류는 수동 `/check` 때까지 남는다. CI auto-ingest처럼 lint 없이 커밋하는 경로가 생긴다.
- 사람 편집 경로를 도구 밖에 두는 것. `/edit`은 대조·검사·기록 없이 고친다. "어느 정도 사람이 하더라도"에서는 사람 경로가 같은 쓰기 CLI를 지나야 한다.
- 영어 전용 정규화(`[^a-z0-9\s]`). 한국어 보고서에서는 중복 방지가 통째로 꺼지고 slug가 충돌한다.
- 생성 한도를 넘는 후보를 버리는 것. "어느 정도 사람이 하더라도"에 맞게 대기열 파일로 보내야 한다.
- 병렬 수집 때 형제 사이 근사 중복을 fan-in에서 다시 대조하지 않는 것.
- 연결 단계를 건너뛰고 "부모가 나중에 처리"라고만 적는 것. 여기서는 fan-in이 의미 엣지와 topic 소속을 채우지 않는다. 건너뛴 단계마다 되채우는 명령을 짝으로 둔다.
- 그래프를 두 파일과 즉석 투영으로 나누고 탐색은 한 파일만 보는 것. 연결고리 발견을 그래프에 맡기려면 한 질의 계층에서 합쳐야 한다.
- 도구마다 따로 짠 frontmatter 파서. 실제 YAML 파서 하나로 모으고 테스트를 함께 둔다.
- 근거 없는 문턱(0.40/0.80/0.85, 한도 1·3·2)을 그대로 쓰는 것. 사내 데이터로 다시 재야 한다.
- claims 종류를 없앤 결정을 그대로 따르는 것. 이것은 "아이디어가 곧 검증할 명제"인 연구 맥락에 맞춘 결정이다. 보고서 wiki에서 "누가 무엇을 주장했나"를 이으려면 근거가 약하다.

## 확인하지 못한 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| `b36c1df`가 `tests/` 16,172줄(도구 테스트 6,402줄 포함)을 모두 지운 이유, 같은 commit에서 엣지를 끝점별 이름으로 바꾸고 confidence를 필수로 만든 이유 | PR #23·#26의 리뷰 대화(지금 본문은 템플릿뿐), 작성자 DanJoshua에게 질문 |
| `0366aea`에서 foundation 0.40~0.80 판단 구간을 없애 0.40 이상을 자동 연결로 바꾸고, 한도 기준을 importance 5 → 4로 바꾼 이유 | 같은 방법. commit 메시지에 없다 |
| 대조 문턱·Jaccard 구간 식의 보정 근거, 임베딩을 쓰지 않은 이유 | 작성자 실험 기록. 레포·이슈·PR 어디에도 없다 |
| methods에 대조 도구와 `aliases`를 두지 않은 이유 | 이슈 #31 본문 전체에 없다(W15). 이슈 작성자 TomWhite-tgz에게 질문 |
| 실제 wiki에서 LLM이 0.40~0.80 구간에서 얼마나 병합을 고르는지, frontmatter 리스트를 어떤 형식으로 쓰는지 | 실행 기록. 레포는 wiki 데이터를 `.gitignore`로 뺀다. `8e6af2d`의 squash 이전 commit이나 공개 사례 wiki가 필요하다 |
| 실험 배포 전 수동 검사 게이트를 넣은 이유 | PR #53/#54 리뷰 토론, 원 브랜치 `refactor/wuxinzhe-exp-idea`의 "update detailed restriction of design run and pilot-run" commit |
| `/research --auto`가 `/exp-design`의 사람 게이트를 실제로 어떻게 넘는지 | 실행 기록이나 이슈. 문서끼리 충돌한다 |
| 한글 정규화, 다중 wikilink 파싱, `*` 엣지가 `/` 없는 ID를 받는 문제의 실제 동작 | 레포 밖 임시 디렉터리에서 해당 함수를 불러 보는 실험. 이번 규칙상 실행하지 않았다 |
| paper 브랜치 schema(10종, 엣지 24종, foundation 비terminal, Trust Guard)가 main으로 돌아올 계획 | 작성자 답변. README 브랜치 모델 절은 "main = stable"만 적는다 |
| paper 브랜치 확장의 상위 명세 `newIdea.md`(§1.2 "evidence-bearing relations ⇒ edges")의 본문 | 어느 브랜치에도 없다. 작성자 Tom White에게 요청 |
| Codex·OpenCode 이식이 무인 auto-ingest를 없앤 "왜"(직렬로 되돌린 이유는 이식 브랜치 `parallel-ingest.md:3`에 있다, W10) | commit 메시지에 결과만 있다. 이식 PR 토론 |
| 비학술 입력(사내 문서)에 대한 작성자 계획 | 이슈 #11 답의 "nano-wiki … accepting various kinds of info"가 이후 생겼는지. 원격 브랜치에는 없다. 작성자의 다른 저장소 |

## 검증 기록

검증자 세 관점이 낸 지적 58건을 레포 HEAD `f5c2fe0`에서 하나씩 다시 확인했다. 58건 모두 근거가 맞아 반영했고, 기각한 것은 없다. 두 건은 검증자의 세부가 달라 고쳐서 반영했다(아래 #부분 수정).

| 관점 | 대조한 주장 수 | 지적 수 | 반영 |
|---|---|---|---|
| 코드 주장(code-claims) | 92 | 19 | 19 |
| "왜" 주장(why-claims: W1~W16, 그 밖의 결정 표, [추정]) | 105 | 21 | 21 |
| 빠진 것(completeness) | 46 | 18 | 18 |

확인 방법은 `sed`·`grep`·`git show`·`git log -S`·`git check-ignore`, `gh issue/pr view`, `gh api`(DanJoshua/Research-Wiki-experimental), WebFetch(arxiv.org/html/2605.31468)다. `.gitignore` 영향은 레포 밖 scratch 저장소에서 git 명령만으로 재현했다. 레포 코드는 실행하지 않았다.

### 크게 바뀐 것

| 자리 | 전 | 후 |
|---|---|---|
| W10, #저장소, 가져올 것 | worktree 격리 + union merge가 동작하는 설계로 소개 | 기본 `.gitignore`가 페이지·엣지를 git에서 빼서, 병렬 ingest와 CI auto-ingest가 페이지를 옮기지 못한다는 한계와 재현 결과를 더함. 차용 조건에 "wiki 데이터를 git에 추적할 때만"을 붙임 |
| 제목, W3, 엔터프라이즈 다중 작성자 행 | "엣지와 공유 파일만 도구를 거친다" | index는 LLM이 직접 쓰고(`init-mode.md:33`이 말하는 index 도구는 없음), 도구를 거치는 것은 엣지·인용·log뿐. `transition`도 쓰기 전 검사임을 더함 |
| W2, 다중 작성자 행 | "재생성은 주 작업 공간에서만"을 도구가 보장 | worktree 가드는 `rebuild-context-brief`·`rebuild-open-questions` 두 명령에만 있고, `compile-context`·`rebuild-index`는 프롬프트로만 금지 |
| W16, 구성 요소 표, 다이어그램, 가져올 것 | SPA 쓰기는 모두 `research_wiki.py`를 부른다 | lint fix는 `lint.py --fix`(페이지 직접 수정), visualize는 `visualize.py`를 부른다. "단일 쓰기 경로"는 엣지·인용에만 맞다고 좁힘. "loopback-only"가 강제되지 않음을 더함 |
| 축 8 | 낡음 표시 셋(context_brief Stale 절 포함) | 사실상 둘. Stale 절은 `general` 예산이 0이라 만들어지지 않음 |
| 축 2, 유지보수 5 | lint는 `/check`·fan-in에서만, 재생성 트리거는 skill에만 | SPA의 lint·재생성 버튼을 더함. 자동 트리거가 없다는 결론은 그대로 |
| 축 15 1행, 가져올 것 | paper 브랜치 Trust Guard는 opt-in | 페이지 Trust Guard는 ingest마다 필수, 엣지 `--gate`만 opt-in. 가져올 것에 PASS/WARN/BLOCK + 격리 + 이벤트 로그 행을 더함. 축 15에 근거 열을 더함 |
| W13 | 논문 §3.3을 Review LLM의 이유로 인용 | 그 문단은 Trust Guard 이야기라 지움. 보수성 이유를 공용 문서 `cross-model-review.md:55`로 바꾸고 skill 목록을 "등"으로 넓힘 |
| W4 이력 | 네 번 한 줄로 옮김(PR #18 → `_schemas.py` 순) | 도구용(`_schemas.py`, 04-12)과 LLM용(`docs/runtime-*.md`, 04-16) 두 갈래가 나란히 있다가 `1b2df1f`에서 합쳐짐 |
| W9 | 필드 17개 | 필드 23개 |
| W5, 엔터프라이즈 용어 불일치 행 | 개념 후보마다 대조 | `/ingest`에만 의무. `/ask` 결정화·`/init` scaffold·`/edit`은 대조 없음. `tags`가 통제 어휘 없이 topic 소속을 정한다는 점, 비대칭 비용 논리의 "split later" 전제를 받칠 도구가 없다는 점을 더함 |
| W5 이력 | foundation 문턱 0.80 → 0.40 | 0.40~0.80 LLM 판단 구간이 없어지고 0.40 이상 자동 연결로 바뀜 |
| ingest 2·6·7·8단계, 실패 처리, `/init` 문단 | 직접 ingest 기준으로만 서술 | 제목 일치도 멈춤 조건, 자기 연결·legacy 거부의 범위, INIT MODE에서 Step 5·역링크·topic을 건너뛰고 fan-in이 `cites`만 되채운다는 점, 부분 실패 worktree는 merge되지 않는다는 점을 더함 |
| 축 4, 엔터프라이즈 형식 없는 문서 행 | PDF는 합성 tex로 정규화 | `prepare_paper_source.py`가 절 하나로 뭉치고 6만 자에서 자른다는 점, 비논문 문서는 `/init` 뒤 증분 경로가 없다는 점을 더함 |
| 엔터프라이즈 표 | 다섯 행 | "연결 후보 생성" 행을 더함. 의미 엣지 후보가 S2 인용 목록에서만 나와 인용 없는 사내 문서끼리 이을 후보 생성 단계가 없다 |
| 축 3, #저장소 | 파생 파일 넷(projected_edges 포함) | `projected_edges.jsonl`은 호출처가 없고 SPA가 즉석 계산. 실제 파생 파일은 셋 |
| 축 9, 가져올 것 | 승인 기록이 없다 | 본체는 없지만 Hiera는 승인 digest를 고정하고 실행 전 재검사. 가져올 것에 행을 더함 |
| 축 8, 가져올 것 Hiera 행 | 원본 sha256 스냅숏이 낡음 감지를 푼다 | 입력 wiki 페이지를 고정하고 바뀌면 run을 거부할 뿐, 낡음 표시·전파는 없다 |
| 구성 요소 표 | skill 25개만 분류, 산출·원격 실행 하위 체계 없음 | `exp-status`와 운영 무리(`setup`·`reset`·`visualize`)를 더함. 집필·포스터 산출(4,463줄)과 `remote.py` 행을 더함 |
| W1 | 논문 §9를 설계 이유처럼 인용, PR #22 기준을 원문처럼 서술, `/init`이 `run_in_background`를 쓴다고 현재형 | §9를 한계 문단으로 다시 인용, 기준 문장에 [추정]과 사례 수, `run_in_background`는 PR #1 시점 것이고 지금은 `git worktree add` |
| W6, W7 | terminal 이유와 엣지 축소 기준을 [추정]으로 | 실험 fork `CLAUDE.md:204`와 `edges.yaml:17-19` 원문으로 (a)를 세움. W7 사례 수(포함 2, 유도 1, 모호 1)도 바로잡음 |
| W10 | test6 사고가 PR #1 다음 날 났다, 이식 브랜치의 직렬 복귀 이유 없음 | 다음 날 들어온 것은 사고를 고친 `5f904b1`. Codex·OpenCode 브랜치 `parallel-ingest.md:3`의 이유 원문을 더하고 #확인하지 못한 것 행을 고침 |
| W11, W15 | docstring을 (a)로, 이슈 #31 Open questions에 단서가 있을 수 있다 | 통째 재생성의 이유 (a)는 없음으로. 이슈 #31 본문 전체에도 이유가 없다고 확인 |
| 그 밖의 결정 표 | 테스트 "대부분" 삭제, 사람 게이트 일반화 | `tests/` 전부 삭제와 도구 테스트 6,402줄을 [추정]이 설명하지 못한다는 점. auto-ingest 행은 규칙만 있고 이유는 없다고 좁힘 |
| 문서 곳곳 | "이슈 #N 작성자 답" | 답한 사람과 역할(skyllwt 소유자, DanJoshua·Morrow-Yang 메인테이너)로 바꿈 |
| 축 9 | `:182`, `:174`를 `reset/SKILL.md`의 줄로 읽히게 적음, `--auto` 출처 없음 | 파일 이름을 붙이고 `i18n/en/skills/research/SKILL.md:23` 출처를 더함 |
| 축 16 어긋남 표, 피할 것 | — | index 도구 부재, INIT MODE 연결 누락, `dedup-policy.md:52`와 `/check`의 어긋남, `.gitignore` 충돌 네 줄을 더함. 피할 것에 사람 경로 우회와 "부모가 나중에 처리" 미이행을 더함 |

### 부분 수정

W10 [추정]의 fan-in 근사 중복 지시는 검증자가 `parallel-ingest.md:52`라고 했지만 실제 줄은 `:54`라서 `:54`로 적었다. 빠진 것 관점은 `/edit`이 "대조 없이 개념을 만든다"고 했지만 `edit/SKILL.md`는 개념 생성을 명시하지 않는다. 그래서 "`/edit`도 대조 도구를 부르지 않는다"로 좁혀 적었다.

재현 중 검증자가 말하지 않은 사실 하나를 더 봤다. `/init` scaffold commit의 `git add`는 무시 대상인 `.checkpoints/*.json`을 명시적으로 넘겨 exit 1로 끝난다. W10 재현 항목에 적었다.

### 문서 구조

doc-style 규약(제목 3단까지)에 맞춰 축별 분석의 `####` 제목을 `###`으로 올렸다. 260자를 넘는 문단 몇 개를 주장 단위로 나눴다.

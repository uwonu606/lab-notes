# AutoSci — skills-runtime 갈래 노트

이 노트는 AutoSci(구 OmegaWiki)의 에이전트 쪽, 곧 Claude Code skill 묶음이 wiki를 어떻게 읽고 쓰고 키우는지를 다룬다.
보고서 작성자가 이 파일만 보고 쓸 수 있게 출처를 문장마다 붙였다.

## 0. 범위와 기준

- 레포: GitHub `skyllwt/AutoSci`, 로컬 `lab/repos/skyllwt_AutoSci`, HEAD `f5c2fe0`(2026-10-02), 라이선스 MIT.
- 경로는 레포 루트 기준이다. `.claude/skills/X/...`와 `i18n/en/skills/X/...`는 `research`를 빼고 모두 내용이 같다(`diff -rq .claude/skills i18n/en/skills` 결과 `research/SKILL.md`만 다름). 그래서 `research`는 `i18n/en/...` 줄 번호로, 나머지는 `.claude/skills/...` 줄 번호로 적는다.
- 코드는 실행하지 않았다. 읽기 전용 git·grep·sed·cat과 `gh issue/pr view`, arXiv HTML WebFetch 1회만 썼다.
- 다른 갈래와의 경계: schema YAML(`runtime/schema/*`)과 `tools/research_wiki.py`·`lint.py` 내부는 다른 갈래가 깊게 본다. 여기서는 skill이 그 도구를 "어떻게 부르는지"와 skill 문서와 도구가 어긋나는 지점만 적는다. 시각화(`app/`, `tools/visualize.py`)와 Hiera 내부(`tools/hiera/`)도 경계만 적는다.

### 읽은 정도

| 대상 | 정도 |
|---|---|
| `CLAUDE.md`, `i18n/en/CLAUDE.md`, `i18n/zh/CLAUDE.md` | 끝까지 |
| `setup.sh` | 끝까지 |
| `ingest` SKILL + references 5개 | 끝까지 |
| `init` SKILL + references 3개 | 끝까지 |
| `check`, `edit`, `ask`, `prefill`(+catalog 앞부분), `reset`, `discover`(+references 3개), `daily-arxiv`(+references 2개) | 끝까지 |
| `research`(i18n/en), `ideate`, `novelty`, `refine`, `exp-eval` | 끝까지 |
| `review` | 앞 120줄 + wiki 관련 줄 grep — 훑음 |
| `exp-design`, `exp-run`, `exp-status`, `exp-pilot-run`, `exp-pilot-eval` | Outputs·Wiki Interaction 절 + 사람 게이트·상태 변경 줄 grep — 훑음 |
| `paper-plan`, `paper-draft`, `paper-compile`, `survey`, `rebuttal`, `poster`, `visualize`, `setup` | Outputs·Wiki Interaction·Constraints 절만 — 훑음 |
| `hiera-experiment` SKILL | 앞 120줄 + README wiki 관련 줄 — 훑음 |
| `shared-references` 3개 | `cross-model-review.md`, `citation-verification.md` 끝까지, `academic-writing.md` 제목만 |
| `mcp-servers/llm-review/server.py` | 1-250줄 끝까지, 나머지 grep |
| `runtime/policy/writers.yaml`, `runtime/CLAUDE.md` 앞 60줄, `runtime/schema/edges.yaml`, `conventions.yaml`, `.gitattributes` | 끝까지(경계 확인용) |
| 원격 브랜치 `autosci-codex`, `autosci-opencode` | `git diff --stat` + 핵심 파일 몇 개 — 얕게 |
| `paper` 브랜치 전용 skill `dream`/`forge`/`morph` | 앞 40줄 — 훑음 |
| 이슈 #5, #11, #12, #19, #31, #41, #42, #45, #67 / PR #1, #3, #6, #18, #22, #23, #24, #26, #40 | 본문·댓글 |

## 1. 구조

### 1.1 파일 지도 — 무엇이 무엇을 부르는가

```
i18n/{en,zh}/CLAUDE.md, skills/*, shared-references/*   ← 사람이 고치는 원본
        │  setup.sh --lang en|zh  (cp)
        ▼
CLAUDE.md, .claude/skills/*/, .claude/skills/shared-references/   ← Claude Code가 읽는 활성 사본
        │  사용자가 /skill 호출 (Claude Code 런타임)
        ▼
SKILL.md (오케스트레이터: LLM이 단계를 따라감)
   ├─ Bash: tools/research_wiki.py  (slug, find-similar-concept, add-edge, add-citation, set-meta, transition, log, rebuild-*, maturity, init, dedup-*, checkpoint-*)
   ├─ Bash: tools/lint.py           (/check, /init fan-in)
   ├─ Bash: tools/fetch_s2.py / fetch_deepxiv.py / fetch_arxiv.py / fetch_wikipedia.py / init_discovery.py / prepare_paper_source.py / discover.py / daily_arxiv.py / remote.py / reset_wiki.py / visualize.py / backfill_citations.py
   ├─ MCP: mcp__llm-review__chat / chat-reply  (.mcp.json → mcp-servers/llm-review/server.py → OpenAI 호환 API)
   ├─ Skill: 다른 skill 호출 (research → ideate → novelty/review/exp-pilot-*, research → exp-design → exp-run → exp-eval → refine → paper-*)
   ├─ Agent: 병렬 subagent (/init 병렬 ingest, /ideate·/novelty 병렬 검색)
   └─ Read/Edit/Write: wiki 페이지 frontmatter·본문 직접 작성
```

- 원본과 활성 사본의 관계: `CLAUDE.md:3` "Edit `i18n/en/CLAUDE.md`, not the active copy at root. Run `./setup.sh --lang en` to sync." `setup.sh`는 `i18n/$LANG/CLAUDE.md`를 루트로, `skills/*/`를 `.claude/skills/`로, `shared-references/*.md`를 `.claude/skills/shared-references/`로 복사하고 `.claude/.current-lang`을 쓴다(`setup.sh` "Step 3b: Activate language files" 블록).
- skill과 tool의 역할 분담은 기여 규칙에 적혀 있다. `CONTRIBUTING.md` "Skills are **orchestrators** that use LLM reasoning and multi-step decisions.", "Skills call tools via `Bash: python3 tools/X.py` -- they do not contain deterministic logic themselves.", "Every skill must read from and/or write back to the wiki.", tools는 "**deterministic Python helpers** (no LLM reasoning)".
- `CONTRIBUTING.md`가 가리키는 `docs/extending.md`는 HEAD에 없고 이력에도 없다(`git log --all -- docs/extending.md` 결과 없음). 깨진 참조다.
- `.mcp.json`은 `llm-review` 서버 하나만 등록한다(`python3 mcp-servers/llm-review/server.py`).
- `config/settings.local.json.example`(setup.sh가 `.claude/settings.local.json`으로 복사)은 `Bash(*)`, `Read(*)`, `Edit(*)`, `WebSearch`, `WebFetch(*)`, `MCP(*)`, `enableAllProjectMcpServers: true`를 허용한다. 곧 skill 실행 중 사람 승인 프롬프트가 나오지 않는다(이슈 #45).

### 1.2 skill 30개 — wiki에서 무엇을 읽고 쓰는가

각 SKILL.md는 `## Wiki Interaction` 절에 `### Reads` / `### Writes` / `### Graph edges created`를 적는 공통 형식을 쓴다. 이 형식은 삭제된 테스트가 강제하던 것이다(`git show 5f904b1:tests/test_skill_ingest.py` `REQUIRED_SECTIONS = ["Inputs","Outputs","Wiki Interaction","Workflow","Constraints","Error Handling", ...]`). 아래 표는 그 절을 옮긴 것이다.

| 단계 | skill | 주로 읽는 것 | 쓰는 것 | 엣지 | LLM 외부 호출 | 사람 게이트 |
|---|---|---|---|---|---|---|
| 설정 | `setup` | `.env` | `.env` | — | — | 대화형 |
| 설정 | `reset` | 전체 | 삭제·초기화 | — | — | 실행 전 확인 필수(`reset/SKILL.md:59`) |
| 지식 | `prefill` | `topics` 태그, catalog | `foundations/*`(신규만) | — | Wikipedia API | 도메인 모호하면 질문 |
| 지식 | `init` | `raw/*`, 기존 wiki | scaffold(Summary·topics·ideas·concepts), raw/tmp·discovered, manifests | scaffold용만 | S2·DeepXiv·arXiv | 없음(최종 선택은 LLM) |
| 지식 | `ingest` | index, papers, concepts, foundations, methods, people, topics, open_questions | papers(C), concepts(C/E), methods(C/E), people(C/E), topics(E만), index, log, graph | paper→concept 4종, paper→foundation `derived_from`, paper↔paper 4종, `cites` | S2·DeepXiv | 없음 |
| 지식 | `discover` | papers frontmatter·mtime | log(venue 모드는 없음), `.checkpoints/` | — | S2·DeepXiv·Paper Copilot | 사용자가 고름 |
| 지식 | `daily-arxiv` | index, papers, topics, concepts, methods, ideas, log | `.daily-arxiv/` scratch, auto-ingest 시 `/ingest` 경유 | — | Review LLM(CI) | `auto-ingest`는 명시 opt-in |
| 지식 | `edit` | 관련 페이지 | raw 추가·삭제, 아무 wiki 페이지 | 역링크 | — | 삭제 전 확인 |
| 지식 | `ask` | context_brief, open_questions, index, 관련 페이지 ≤15, edges.jsonl | `--crystallize` 때만 outputs/concepts/ideas/methods, edges | `derived_from`, `supports` | — | crystallize는 확인 필요 |
| 지식 | `check` | 전 entity + graph | 기본 없음, `--fix` 때 결정적 수정, log | — | — | 비결정적 수정은 승인 대상 |
| 아이디어 | `ideate` | context_brief, open_questions, 전 ideas(banlist), papers, concepts, methods, topics, experiments | ideas(proposed + failed), edges, rebuild, log | `addresses_gap`, `inspired_by` | Review LLM 브레인스톰, WebSearch | `--auto` 아니면 순위 확인, pilot 대상 선택 |
| 아이디어 | `novelty` | papers, concepts, methods, ideas, context_brief | `--write` 때 ideas.novelty_score만 | — | Review LLM, WebSearch | — |
| 아이디어 | `review` | 산출물 + 관련 페이지 | 없음(읽기 전용) | — | Review LLM(최대 3라운드) | — |
| 아이디어 | `exp-pilot-run` | Pilot Spec, papers | `experiments/pilot/code/*`(wiki 밖) | — | — | 코드·설정 수동 검사 필수(`exp-pilot-run/SKILL.md:105`) |
| 아이디어 | `exp-pilot-eval` | idea, pilot 결과 | ideas.pilot_result/failure_reason/status | — | — | `--auto` 아니면 확인 |
| 실험 | `exp-design` | idea, pilot report, papers, concepts, topics, methods, experiments | experiments(planned), `experiments/designs/*`, ideas.linked_experiments | `tested_by` | — | 후보 선택(`:88`), 설계 승인(`:270-272`) |
| 실험 | `exp-run` | experiment, idea, papers | `experiments/code/*`, experiments 상태·결과 | — | — | 배포 전 수동 검사(`exp-run/SKILL.md:9`, `:137`) |
| 실험 | `exp-status` | experiments, pipeline-progress | `--collect-ready` 때 experiments | — | — | — |
| 실험 | `exp-eval` | experiment, idea, 형제 실험 | ideas.status 등, experiment `## Idea updates` | `supports`, `invalidates` | Review LLM 판정 | `--auto` 아니면 확인(`exp-eval/SKILL.md:140`) |
| 실험 | `refine` | 산출물 + 관련 페이지 | 산출물 제자리 수정, ideas/methods/experiments/outputs, edges | 상황에 따라 | `/review` 경유 | — |
| 실험 | `hiera-experiment` | experiment·design(읽기 전용) | `runs/hiera/*`만 | — | — | approve 단계 명시 승인 |
| 집필 | `survey` | papers, concepts, topics, ideas, methods, index, edges | `outputs/related-work-*` | `derived_from` | DBLP·CrossRef | — |
| 집필 | `paper-plan` | ideas, experiments, methods, papers, concepts, topics, edges | `outputs/paper-plan-*` | `derived_from` | Review LLM 필수 | — |
| 집필 | `paper-draft` | plan + 거의 전부 | `paper/*`, log | — | DBLP·CrossRef | — |
| 집필 | `paper-compile` | plan | `paper/main.pdf`, log | — | — | — |
| 집필 | `rebuttal` | ideas, methods, experiments, papers, concepts, edges | `outputs/rebuttal-*`, ideas/methods에 Risks·Limitations 덧붙임 | — | Review LLM | — |
| 집필 | `poster` | `paper/*`, plan, ideas, experiments | `poster/*`, log | — | — | 그림 선택 |
| 오케스트레이터 | `research` | context_brief, open_questions, ideas, experiments, methods, papers, pipeline-progress | `outputs/pipeline-progress.md`, `outputs/PIPELINE_REPORT.md`, log | 직접 없음 | 하위 skill | Gate 1(아이디어 선택), Gate 2(논문 준비) |
| 도구 | `visualize` | graph, 전 entity frontmatter | `.obsidian/*`, `canvases/*` | — | — | — |

출처: 각 SKILL.md의 `## Outputs` / `## Wiki Interaction` 절. 예: `ingest/SKILL.md:32-68`, `ask/SKILL.md:29-58`, `check/SKILL.md:23-41`, `ideate/SKILL.md:29-50`, `exp-eval/SKILL.md` Outputs·Wiki Interaction 절, `research`는 `i18n/en/skills/research/SKILL.md:40-58`.

### 1.3 skill이 실제로 부르는 `research_wiki.py` 명령과 안 부르는 명령

`grep -rln "research_wiki.py <cmd>" .claude/skills`로 셌다.

- 부르는 것: `slug`, `find-similar-concept`(ingest만), `add-edge`, `add-citation`, `set-meta`, `transition`, `log`, `rebuild-context-brief`, `rebuild-open-questions`, `rebuild-index`, `maturity`, `init`, `dedup-edges`, `dedup-citations`, `checkpoint-*`, `stats`(1개 파일).
- 어느 skill도 부르지 않는 것: `neighbors`, `compile-context`(목적별 예산), `batch-edges`, `query ready-to-test`, `query orphans`, `find`, `read-meta`, `topic-backfill`, `rebuild-projected-edges`, `add-citations-batch`(모두 0개 파일). `app/modules/*.js`, 다른 `tools/*.py`, `docs/`, `README.md`에서도 `neighbors`·`compile-context`를 부르는 곳이 없다(grep 결과 `tools/discover.py:858`의 주석 낱말 하나뿐).
- 뜻: skill이 wiki 맥락을 얻는 길은 `context_brief.md`(= `compile_context(..., "general")`, `tools/research_wiki.py:821-824`), `open_questions.md`, `index.md`, 그리고 파일 직접 읽기다. 그래프 BFS 탐색은 skill 경로에 없다.

### 1.4 핵심 자료 구조

**(1) `wiki/outputs/pipeline-progress.md` frontmatter** — `/research` 진행 상태, 세션을 넘는 재개용(`i18n/en/skills/research/SKILL.md:99-127`).

```yaml
slug, direction, status: running, current_stage: stage1, started: YYYY-MM-DD,
mode: auto|interactive, skip_paper, venue, idea_slug: "", experiment_slugs: [],
stage3a_deployed: [], linked_idea_slugs: [], iteration_count: 0
# 본문 "## Stage Log": Stage 0 … Stage 5 / Gate 1·2 각각 pending|completed|passed
```
`research/SKILL.md:93`은 `monitoring_cron_id`도 복원한다고 적지만 위 템플릿에는 그 필드가 없다.

**(2) `/init` manifest 3종** — `.checkpoints/init-pdf-titles.json`(LLM이 PDF를 보고 쓴 `{path: title}` 또는 `{path: {title, arxiv_id}}`, `init/SKILL.md:91`), `.checkpoints/init-prepare.json`(prepare 결과, `canonical_ingest_path`·경고), `.checkpoints/init-plan.json`(shortlist), `.checkpoints/init-sources.json`(최종 목록, 항목마다 `origin=user_local|introduced`, `canonical_ingest_path`, `shortlist_rank`; `init/references/prepare-and-discovery.md:42-47`). LLM이 만드는 "final selection artifact"는 `shortlist_count`, `final_count`, `candidate_id` 목록을 가진다(`init/SKILL.md:116`).

**(3) ideas 페이지 frontmatter** — `/ideate`가 쓰는 형태(`ideate/SKILL.md:258-275`).

```yaml
title, slug, status: proposed, origin: "ideate: …", origin_gaps: [], tags: [],
target_venue: "", novelty_score: "", priority: 3, pilot_result: "",
failure_reason: "", linked_experiments: [], date_proposed, date_resolved: ""
```
탈락 아이디어는 같은 틀에 `status: failed`, `priority: 1`, `failure_reason: "[filter] …"`를 넣는다(`ideate/SKILL.md:311-318`). `failure_reason` 접두어는 `[filter]`(ideate), `[pilot]`(exp-pilot-eval), 접두어 없음(exp-eval) 세 갈래다.

**(4) Pilot Spec** — `experiments/pilot/{slug}.yaml`, wiki 밖(`ideate/SKILL.md:408-454`). `pilot_spec.{hypothesis, approach_sketch, implementation{repo, entry_point, modifications, files_to_create}, setup{model, dataset, hardware, framework, batch_size, max_steps, learning_rate, seeds, other_hparams}, metrics[{name, why}], baseline{method, source, expected_value}, success_criterion{pass, fail, inconclusive}}`.

**(5) `/ask` 결정화(crystallize) 페이지** — `wiki/outputs/{query-slug}.md`, frontmatter `title, slug, query, source_pages: [], date_created`(`ask/SKILL.md:120-128`). `outputs`는 `entities.yaml`의 9종에 들지 않는 자리다(entity 목록: papers, concepts, topics, people, ideas, methods, experiments, Summary, foundations).

**(6) `/daily-arxiv` LLM 판정 레코드** — `.daily-arxiv/run/llm-decisions.json`, 후보마다 `{arxiv_id, decision: strong_recommend|maybe|skip|ingest, confidence: high|medium|low, score, rationale, wiki_connections[], signals_used[]}`(`daily-arxiv/references/recommendation-and-ingest-policy.md:34-43`).

**(7) Review LLM MCP 도구** — `chat{prompt (필수), model, system}` → `threadId` 반환, `chat-reply{threadId, prompt}`, `web_search{query, system}`(`mcp-servers/llm-review/server.py:181-218`). thread는 프로세스 메모리 dict `_threads`에만 있다(`server.py:55`, `:246-248`). 호출은 `temperature: 0.3`, `max_completion_tokens: 16384`, 최대 3회 시도(504·429면 지수 대기, 세 번째는 `LLM_FALLBACK_MODEL`, 폴백 응답 앞에 `[Fallback: …]`; `server.py:110-148`).

**(8) `/review` 보고서 필드** — Overall Score 1-10, Strengths, Weaknesses(심각도 순), Questions, Actionable Suggestions, Wiki Entity Mapping, Verdict `ready|needs-work|major-revision|rethink`(`review/SKILL.md:32-40`). `/refine`은 이 출력을 파싱해 `score`, `verdict`, `weaknesses(critical/major/minor)`, `actionable_items`, `wiki_entity_mapping`을 뽑는다(`refine/SKILL.md` Step 2a).

**(9) `wiki/log.md` 줄** — `## [YYYY-MM-DD] {message}`(`tools/research_wiki.py:2080-2094`). 날짜와 skill 이름이 담긴 자유 문자열만 있고 행위자(사람·세션) 필드는 없다. 형식 규정은 `conventions.yaml:18` `log_grammar: "## [{date}] {skill} | {details}"`.

## 2. 동작 흐름

### 2.1 `/ingest` — 논문 1편 → 페이지 묶음

입력: arXiv URL, 로컬 `.tex`/`.pdf`, 또는 `/init`이 넘긴 `canonical_ingest_path`(`ingest/SKILL.md:20-24`).

| 단계 | 입력 → 처리 → 출력 | LLM / 결정적 |
|---|---|---|
| 0 | Python 해석기 결정. worktree에서도 `.venv`를 찾도록 `git rev-parse --git-common-dir`로 루트를 찾는다(`:72-94`) | 결정적 |
| 1 원문 확정 | arXiv면 `fetch_s2.py paper`로 제목 → `init_discovery.py download`(tex 우선, PDF 폴백). PDF면 `pdf-preprocessing.md` 절차(`:96-103`) | PDF 제목 인식은 LLM(`pdf-preprocessing.md:15-19`), 나머지 도구 |
| 2 정체 | `research_wiki.py slug` → 기존 페이지·arXiv ID 대조 → 같으면 종료. S2로 venue·year·s2_id·importance 근거. DeepXiv `brief/head/social` 선택(`:105-129`) | slug는 결정적, importance(1-5) 판단은 LLM |
| 3 논문 페이지 | `entities.yaml`·`templates/papers.md.tmpl`을 열고 LLM이 frontmatter·본문 작성. `tldr`, `contribution_type`(닫힌 집합), `datasets` 필수 취급. 쓰기 전 "shape check"(필수 키·enum·YAML 파싱)(`:131-155`) | 작성·shape check 모두 LLM 자기검사 |
| 4 개념·방법·사람 | 개념 후보마다 `find-similar-concept` → 점수로 foundation 연결/병합/판단/생성. 방법은 도구 없이 `wiki/methods/` 훑기. 사람 페이지는 importance≥4만. 역링크는 같은 턴에(`:157-167`, `dedup-policy.md:31-40`) | 점수는 결정적, 결정은 LLM |
| 5 논문↔논문 | `fetch_s2.py references/citations` → wiki에 있는 논문에 `cites`. 원문 단서가 분명할 때만 의미 엣지. `cited_by` 채움(`:169-181`) | 대조는 결정적(ID·제목), 의미 엣지 선택은 LLM |
| 6 주제·색인 | 태그 맞는 기존 topic에만 덧붙임(importance≥4면 `key_papers`에도), topic 생성 금지, index 추가(`:183-190`) | LLM |
| 7 로그·재생성 | `log`, `rebuild-context-brief`, `rebuild-open-questions`(INIT MODE면 생략)(`:192-203`) | 결정적 |
| 7.5/9 | `--visualize`, `--discover` 플래그가 있을 때만(`:205-241`) | 결정적 + 보고 |
| 8 보고 | `Wiki: +1 paper, +{N} methods, +{M} concepts, +{K} edges`(`:218-224`) | LLM |

- 결정적 검사 지점: `add-edge`가 모르는 엣지 종류·endpoint 위반·필수 속성 누락을 거부한다(`ingest/SKILL.md:66-68`, 세부는 schema 갈래). frontmatter 쪽은 쓰기 전 도구 검사가 없고 LLM shape check뿐이다(`:141-148`, `:256`).
- 실패 처리(`references/error-handling.md`): tex → PDF → vision API → 사람에게 넘김(`:5-10`). S2가 죽으면 importance 3, 인용 보강 생략(`:14`). DeepXiv가 죽으면 조용히 생략(`:15`). dedup 호출 일시 실패는 "retry once; if it still fails, skip that candidate"(`:55`). 중간 실패는 되돌리지 않고 log에 남기고 보고한다(`:34-41`) — "a partial ingest that preserves a well-shaped paper page is more useful than a clean abort"(`:57`).
- 논문 단위 생성 한도: importance<4면 새 개념 1·새 방법 1, ≥4면 3·2(`ingest/SKILL.md:251-254`).

### 2.2 `/init` — 빈 wiki 부트스트랩 + 병렬 ingest

| 단계 | 내용 | 출처 |
|---|---|---|
| 1 | `research_wiki.py init wiki/` | `init/SKILL.md:77-83` |
| 2 prepare | LLM이 각 PDF를 보고 제목·arXiv ID를 `init-pdf-titles.json`에 적음 → `init_discovery.py prepare` | `:85-100` |
| 3 plan/trim/fetch | `plan`(seeded/bootstrap 자동) → LLM이 shortlist를 8-10편으로 잘라 final selection artifact를 냄 → `fetch` | `:102-129` |
| 4 scaffold | notes/web에서 Summary·topics·ideas·concepts 임시 페이지. 모두 "Provisional note: seeded from raw/notes or raw/web during /init; pending validation from ingested papers." 줄을 붙임 | `:131-149` |
| 5 병렬 ingest | scaffold 커밋 → 논문마다 `git worktree` + subagent `/ingest`(INIT MODE) → worktree 안에서 커밋 | `:151-175`, `references/parallel-ingest.md` |
| 6 fan-in | 순차 merge → `dedup-edges`, `dedup-citations`, `rebuild-index`, `rebuild-context-brief`, `rebuild-open-questions`, `lint.py --fix` → `backfill_citations.py` → 시각화 | `:177-221` |

- INIT MODE에서 subagent가 건너뛰는 것: S2 references/citations, `rebuild-*`, topic 쓰기, 기존 페이지에 역링크 쓰기(`ingest/references/init-mode.md:9-16`). 기존 페이지 관계는 `add-edge`로만 남기고 부모가 fan-in 때 역링크를 채운다.
- 같은 slug 개념을 두 subagent가 만들면: 부모가 순차 merge 중 충돌을 "picking the earlier write and re-running `find-similar-concept` on the later one at fan-in"으로 푼다(`init-mode.md:42`). worktree 사이 조정은 하지 않는다(`:43`).
- 결정적 방어: `rebuild-context-brief`/`rebuild-open-questions`는 linked worktree 안에서 실행을 거부한다(`tools/research_wiki.py:791-824`, PR #14).
- 실패: 논문 하나 실패는 체크포인트에 남기고 계속(`init/SKILL.md:247`). detached HEAD면 fan-out 전에 멈춤(`:248`). 시각화 실패는 경고만(`:250`).
- 실제 실행 흔적: squash commit `8e6af2d` 메시지에 `/init` 실행 결과가 남아 있다. "Entities: 9 papers, 23 concepts, 3 topics, 1 idea, 2 methods / Graph edges: 36 edges (deduped) / Lint: 0 red, 0 yellow, 7 blue". 같은 메시지에 "ideate: 4 ideas proposed, 4 filtered out"도 있다. PR #31 검증 기록은 "5 papers + 7 methods + 14 concepts + 20 people + 12 edges", "跨论文的 `godel-machine` 概念在 fan-in 时正确合并"(논문을 가로지르는 `godel-machine` 개념이 fan-in 때 올바르게 병합되었다)이다.

### 2.3 `/ask` — 질의와 결정화

1. `context_brief.md`·`open_questions.md`를 읽는다. 없으면 재생성(`ask/SKILL.md:65-73`).
2. `index.md`에서 질문 낱말과 slug를 맞추고, context_brief에서 관련 ideas·methods·papers를 고른다. 상위 K≤15 페이지 전문을 읽는다. "X와 Y의 차이" 질문이면 `edges.jsonl`에서 X-Y 엣지를 읽는다(`:75-81`).
3. 답 합성: 핵심 문장마다 `[[slug]]`, 근거 약하면 "insufficient evidence in wiki", 알려진 gap이면 표시(`:83-94`).
4. 결정화 가치 판단과 권고(`:96-111`). 기본은 쓰지 않는다. `--crystallize`나 사용자 확인 때만 `outputs/`에 쓰거나(기본), 새 concept(`maturity: emerging`)를 만들거나, 기존 ideas/methods/outputs에 단락을 덧붙인다(`:113-148`).

- 검색은 전부 LLM 판단이다. 임베딩·BM25·그래프 탐색 도구를 부르지 않는다.
- `index.md`에는 slug·title·tags·status 등만 있고 aliases가 없다(`tools/research_wiki.py:1823-1885` `rebuild_index`가 넣는 키 목록). 그래서 `/ask`의 index 대조는 별칭을 보지 못한다.

### 2.4 `/check`

- `lint.py --json`(기본), `--fix`, `--fix --dry-run`(`check/SKILL.md:48-67`). 자동 검사는 깨진 wikilink, 고아 페이지, 필수 필드, enum, xref 대칭, 엣지 JSON·종류·confidence·dangling(`:69-124`).
- LLM 판단 항목: 개념·방법 근사 중복 → 병합 "recommendations", 페이지 간 모순, 6개월 넘은 SOTA·Recent work, novelty_score와 논증 강도 불일치, 오래 멈춘 high-priority idea(`:133-140`).
- `--fix`는 결정적 문제만 고친다. 나머지는 "recommendations (`--suggest`) for user approval"(`:174`). 보고서는 🔴/🟡/🔵 세 등급(`:161-164`).
- 작성자 답(이슈 #41): "/check is a manual report … it only runs when someone remembers to run it. Our daily-arxiv CI workflow auto-commits wiki changes without running /check at all." 또 LLM 품질 검사는 "not yet implemented in the automated linter -- they remain aspirational."

### 2.5 `/prefill` — 범용어 계층 미리 심기

catalog(`prefill/foundations-catalog.yaml`, `domains.{general,NLP,CV,ML Systems,Robotics}`) 또는 `--add` 하나 → 이미 있으면 건너뜀 → `fetch_wikipedia.py summary/sections/section` → 페이지 작성(Wikipedia 출처 없는 절에는 `(LLM analysis)` 표시) → `rebuild-index`, `log`(`prefill/SKILL.md:42-134`). foundation에는 역링크 필드를 쓰지 않는다(`:138`). catalog의 `summary`는 중국어다(예: `foundations-catalog.yaml` gradient-descent "一阶优化算法家族…"(1차 최적화 알고리즘 계열…)).

### 2.6 `/discover`와 `/daily-arxiv` — 새 자료 후보를 고르는 쪽

- `/discover`: 네 모드(anchor/topic/wiki/venue) 중 하나 → `tools/discover.py`가 수집·wiki dedup·순위를 결정적으로 처리 → 사용자에게 shortlist. "Do not ingest anything yourself. The user picks."(`discover/SKILL.md:118`). anchor 모드는 S2 `recommend`+`references`+`citations` 세 채널(`:98`).
- `/daily-arxiv`: `daily_arxiv.py prepare`(결정적 증거 묶음) → LLM 판정 JSON → `finalize`(digest). `auto-ingest`는 `decision: ingest`+`confidence: high`만, `max_auto_ingest`까지, `/ingest`를 순차 호출(`daily-arxiv/SKILL.md:59-79`). 제3자 LLM은 추천만 하고 `ingest` 판정은 `strong_recommend`로 강등(`references/recommendation-and-ingest-policy.md:49-51`). "Missing enrichment is never evidence for ingestion."(`:28`).

### 2.7 연구 수명주기 — wiki가 어떻게 자라는가

`/research`가 하위 skill을 순서대로 부른다(`i18n/en/skills/research/SKILL.md`).

```
Stage 0  maturity cold & papers<3 → /init 으로 넘김(:141-183)
Stage 1  /ideate --auto  → ideas(proposed·failed) + addresses_gap/inspired_by 엣지(:185-197)
Gate 1   --auto면 top-1, 아니면 AskUserQuestion; idea proposed→in_progress(:199-212)
Stage 2  /exp-design → experiments(planned) + tested_by + ideas.linked_experiments(:214-225)
Stage 3a /exp-run(deploy) 각 실험, 실패해도 계속(:231-258)
Stage 3b ETA 계산 후 세션 종료(:260-295)
Stage 3c /research --start-from stage3-collect → /exp-run --collect; baseline 실패면 중단; idea in_progress→tested(:297-328)
Stage 4  /exp-eval --auto → supports/invalidates + idea validated/failed; 부족하면 /refine 후 3→4 반복, 최대 2회(:330-356)
Gate 2   --auto면 진행, 아니면 준비/추가실험/중단 질문(:358-375)
Stage 5  /paper-plan → /paper-draft --review → /refine paper/main.tex → /paper-compile(:377-407)
Final    PIPELINE_REPORT + maturity 전후 비교(:409-478)
```

wiki가 자라는 방식을 entity로 보면:

| 무엇이 생기나 | 누가 | 다음에 누가 그것을 읽나 |
|---|---|---|
| papers, concepts, methods, people, topics 갱신, paper 엣지 | `/ingest`(`/init`, `/daily-arxiv` 경유 포함) | 거의 모든 skill |
| ideas(proposed) + 탈락 ideas(failed, `[filter]`) | `/ideate` | 다음 `/ideate`·`/novelty`의 banlist(`ideate/SKILL.md:76-78`, `novelty/SKILL.md:92-94`) |
| ideas.pilot_result, `[pilot]` 실패 | `/exp-pilot-eval` | `/exp-design`(pilot report), banlist |
| experiments(planned→running→completed) | `/exp-design`, `/exp-run` | `/exp-eval`, `/paper-plan`, `/rebuttal` |
| ideas.status validated/failed + `supports`/`invalidates` | `/exp-eval` | `/paper-plan`(validated만), banlist, `context_brief`의 Failed 절 |
| outputs(plan, related-work, rebuttal, ask 답) + `derived_from` | `/paper-plan`, `/survey`, `/rebuttal`, `/ask` | `/paper-draft`, `/poster` |
| ideas `## Risks`·`## Lessons learned`, methods `## Limitations` 덧붙임 | `/rebuttal`, `/ask` Case C, `/refine` Category C | 다음 `/ideate`(Path B는 `method.limitations`를 읽음, `ideate/SKILL.md:126`) |

- 되먹임 고리 1 — 실패 기억: 탈락·실패한 아이디어를 지우지 않고 `status: failed`+`failure_reason`으로 남기고, 다음 `/ideate`가 banlist로 읽는다(`ideate/SKILL.md:318`, `:507`, `:509`). `/novelty`는 겹치는 실패 아이디어가 있으면 점수를 1 깎는다(`novelty/SKILL.md:165`).
- 되먹임 고리 2 — gap 지도: `rebuild-open-questions`가 papers `## Open questions`, topics `## Open problems`(H3 포함), concepts `## Open problems`를 모아 `open_questions.md`를 만든다(`tools/research_wiki.py:831-855`). `/ideate`는 방향이 없으면 이 파일에서 방향을 고른다(`ideate/SKILL.md:15`).
- 되먹임 고리 3 — methods 필드가 아이디어 생성 경로가 된다. Path B는 `method.limitations`, C는 `tradeoff_profile`, D는 `assumptions` 교집합, E는 `mechanism` 유사성(`ideate/SKILL.md:123-131`).
- `maturity`(cold/warm/hot)가 `/ideate`의 외부 검색량과 gap 가산점을 바꾼다(`ideate/SKILL.md:56-65`). maturity 계산은 foundation을 뺀다(`tools/research_wiki.py` `get_maturity`의 `if not e.get("terminal")`).

### 2.8 LLM 호출 지점 정리

| 종류 | 자리 | 프롬프트가 있는 파일 |
|---|---|---|
| 주 에이전트(Claude Code 세션) | 모든 skill의 판단·작성 | 각 `SKILL.md` + references |
| Review LLM 단발 | `/review` Step 2, `/novelty` Step 3, `/ideate` Phase 2, `/exp-eval` Step 2, `/paper-plan`, `/rebuttal` stress-test | system/message 문안이 SKILL.md 안에 코드블록으로 있음. 예: `novelty/SKILL.md:107-124`, `exp-eval/SKILL.md` Step 2(약 `:82-118`), `ideate/SKILL.md:140-179`, `review/SKILL.md:84-107` |
| Review LLM 다회 | `/review --difficulty hard|adversarial`(최대 3라운드, 점수 변화<0.5면 수렴) | `review/SKILL.md:136-166` |
| CI 추천 LLM | `daily_arxiv.py recommend-llm` | 코드 쪽(다른 갈래) |
| subagent | `/init` 병렬 ingest, `/ideate`·`/novelty` 병렬 검색 | `init/references/parallel-ingest.md:35-47` |

- skill 문서의 MCP 호출 예시는 `system:`과 `message:` 키를 쓰지만(`novelty/SKILL.md:107-113`), 서버의 입력 스키마 키는 `prompt`와 `system`이다(`server.py:186-192`). [추정] 문서 예시는 의사 코드이고 에이전트가 키를 맞춰 부른다고 본다(사례: 같은 `system/message` 형식이 novelty·ideate·exp-eval·review 4곳에 있음).
- 독립성 규칙: Review LLM에게 주 에이전트의 점수·판단을 보내지 않는다(`shared-references/cross-model-review.md:9-20`). 합치는 규칙은 "1점 안이면 평균, 2점 이상 차이면 표시, 보수적으로 낮은 쪽, 치명적 발견은 평균으로 지우지 않는다"(`:51-56`). Review LLM이 없으면 조용히 건너뛰지 말고 묻고, 진행하면 `[Claude self-review — no independent second opinion]` 표시(`:73-88`).

### 2.9 결정적 검사 지점 정리

| 지점 | 무엇을 막나 | 출처 |
|---|---|---|
| `add-edge` | 모르는 엣지 종류, endpoint 위반, legacy 종류, 의미 엣지의 confidence·evidence 누락 | `ingest/SKILL.md:66-68`(도구 세부는 schema 갈래) |
| `transition` | lifecycle 표에 없는 전이, `failed`에 reason 없음, `in_progress`에 linked_experiments 없음, experiment `completed`에 key_result 없음 | `tools/research_wiki.py:1607-1660` |
| `set-meta` | 없는 필드 생성(`exp-design/SKILL.md:327` "set-meta refuses to create fields that don't already exist"). lifecycle 검사는 없음 | `tools/research_wiki.py:2404-2443` |
| `rebuild-*` worktree 거부 | subagent가 전체 재생성 파일을 worktree에서 다시 쓰는 것 | `tools/research_wiki.py:791-824`, PR #14 |
| `slug` | 결정적 slug(불용어 제거, 최대 6낱말) | `tools/research_wiki.py:105-130` |
| `lint.py`(사후) | 필수 필드·enum·xref·엣지 | `/check`, `/init` fan-in |
| `.gitattributes merge=union` | 병렬 append 파일의 merge 충돌 | `.gitattributes` |
| `discover.py` wiki dedup | 이미 있는 논문 재추천 | `discover/references/wiki-dedup.md` |
| `paper-compile` `[UNCONFIRMED]` | 검증 안 된 BibTeX가 제출물에 남는 것 | `shared-references/citation-verification.md:20-27` |

### 2.10 Hiera(경계만)

`/hiera-experiment`는 기존 experiment를 읽기 전용 입력으로 삼아 후보 탐색을 `runs/hiera/<experiment>/<run-id>/`에서만 한다. "It never creates wiki entities, changes wiki schema or experiment status, rewrites wiki/log.md, or writes search results back to the wiki."(`hiera-experiment/SKILL.md:15`). approve는 명시적 사람 승인이 있어야 하고 "Follow-up text narrows the operation; it is not approval by itself."(`SKILL.md` User interaction protocol 절). 내부 구현은 `tools/hiera/`(다른 갈래).

## 3. 설계 결정과 그 이유

(a) = 작성자가 밝힌 이유(원문 인용). (b) = [추정].

### D1. skill은 오케스트레이터, 결정적 로직은 tools로

- 결정: SKILL.md는 단계와 판단만 적고, slug·대조·엣지 쓰기·lint·재생성은 Python 도구가 한다.
- (a) `CONTRIBUTING.md` "Skills are **orchestrators** … they do not contain deterministic logic themselves." 이슈 #11 작성자 답 "we're working to make skills leaner and introduce coded tools to replace LLM reasoning where possible." 논문 §9 "built as a skill package on top of general-purpose coding and reasoning agents" — "This makes the system easy to deploy and inspect, but it is not yet a science-specialized agent foundation." (arXiv 2605.31468, WebFetch 인용).
- 이력: PR #18(`refactor: toolize init pipeline`) "replace inline SKILL.md scripts with `tools/init_discovery.py`". `init/references/planner-policy.md:25-27` "`tools/init_discovery.py` is the implementation authority for exact weights … Do not duplicate numeric planner constants here".
- 대안: 전부 LLM 프롬프트로(Karpathy 원형), 또는 전부 코드 파이프라인으로.

### D2. 프롬프트 규칙이 깨진 자리를 도구 거부로 옮긴다

- 결정: subagent가 금지 명령을 실행해도 도구가 거부하게 한다.
- (a) 이슈 #12 작성자 답 "init/SKILL.md already told agents to SKIP these commands in INIT MODE, but that relied on prompt discipline alone. Now it's enforced at the tool level, so a prompt-drifted subagent can't reproduce this conflict even if it tries." 코드 주석 `tools/research_wiki.py:792-794` "Used to block graph rebuilds from /init subagents: their worktree rebuilds collide on merge with the orchestrator's final one."
- 이력: PR #14(2026-04-15).
- 대안: 프롬프트만 강화.

### D3. 개념은 "만들기 전에" 결정적 대조, 기본은 병합, 논문당 생성 한도

- (a) `dedup-policy.md:7` "When `/ingest` creates a new concept or method per paper by default, the wiki quickly devolves into a pile of near-duplicates that breaks every downstream skill". `:29` "Skipping the dedup step is the single most common cause of wiki bloat. … paraphrases slip past human scanning." `:42` "Over-merging is cheap to undo … Over-creating is expensive". `:46` 한도는 "not a quota to fill".
- (a) 계기 사건: PR #6 "test6 bloat: 15 papers → 45 claims + 37 concepts because subagents deduped from memory and missed paraphrases. `find-similar-*` are the deterministic gate to prevent this." 같은 PR 본문 "(… where ~15 / ~15 were correct)".
- 이력: 처음 한도(`5f904b1`, 2026-04-11)는 importance<5면 새 개념 1, ==5면 3이었고 넘치면 점수<0.40이라도 가장 가까운 것에 강제 병합, 넘긴 파일은 "undo"하라고 했다(`git show 5f904b1:i18n/en/skills/ingest/SKILL.md:210-214`, `:290`, `:306`). `0366aea`(2026-04-24) 재작성에서 importance<4: 1/1, ≥4: 3/2로 바뀌고 "If no candidate is close enough to merge safely, skip writing that entity"가 생겼다(`git show 0366aea:…/dedup-policy.md`). `1b2df1f`에서 claims가 methods로 바뀌었다.
- 대안: 사후 일괄 병합, 임베딩 유사도, 사람 승인 대기열.

### D4. 방법(method) 중복은 도구 없이 LLM이 훑는다

- 결정: `find-similar-method`가 없다(`dedup-policy.md:27`).
- 모르는 것: 왜 개념용 도구를 방법에 확장하지 않았는지 적힌 곳이 없다. PR #31 "Open questions" 절(본문이 잘려 "1. **`metho…"까지만 읽음)에 단서가 있을 수 있다. `gh issue view 31`의 body 전체를 9000자 넘게 읽으면 알 수 있다.
- [추정] methods 엔티티가 늦게(v1.1.0, `1b2df1f`) 들어와 도구가 아직 못 따라왔다(사례: CHANGELOG 1.1.0이 `find-similar-claim` 제거만 적고 method용 추가는 없음 1건).

### D5. ingest는 모양만, 의미 감사는 `/check`로

- (a) `dedup-policy.md:63` "Running those audits inside `/ingest` slows the skill down and duplicates work." `cross-references.md:98` "Do not read the entire `wiki/` to look for broken back-references during ingest — the time and token cost is large and the work is redundant with `/check`."
- 대안: 쓰기마다 전체 lint.
- 대가: 이슈 #41 작성자 답 "It can't assert that an ingest should have created more (or less) pages than it did. This is a known blind spot".

### D6. 범용어는 foundation이라는 terminal 계층으로, `/prefill`만 만든다

- (a) PR #3 "the whole point of `/prefill` is to keep foundational background separate from research concepts so `/ingest` doesn't pollute `concepts/` with textbook material." foundation은 maturity에서 뺀다: "background knowledge shouldn't inflate research progress scores." 고아 검사에서 빼지 않는 이유: "Under correct usage every foundation receives an inward link via `/ingest` dedup, so orphan is a real diagnostic signal".
- (a) `/ingest`가 foundation을 만들지 않는 규칙: `cross-references.md:27` "route the candidate through the ordinary concept path … and let the user seed a foundation later if they want to."
- 대안: 빈도 기반 stoplist, 개념 페이지에 `generic` 표시.

### D7. 논문↔논문 의미 엣지는 드물게

- (a) `cross-references.md:56-60` "intentionally sparse … If the same statement would be true for dozens of papers in the wiki, skip the paper-to-paper edge". `:79` "Graph noise is worse than a missing edge." `:81-82` "When in doubt, skip. … not clustering by field."
- (a) 엣지 종류 축소 이유: `edges.yaml:17-23` "improves_on ⊆ builds_on", "compares_against ⊆ cites", "surveys ⇐ papers.contribution_type contains "survey"", "complementary_to ≈ same_problem_as (boundary fuzzy in practice)".
- 대안: 인용마다 의미 엣지.

### D8. 서지(cites)와 의미 엣지를 다른 파일로

- (a) `cross-references.md:50-54` "The bibliographic layer is separate from the semantic layer … do not force every citation into a semantic edge". `conventions.yaml:27-30` 저장 위치 분리.

### D9. 정방향 링크를 쓰면 같은 턴에 역방향도

- (a) `cross-references.md:18` "Writing a forward link without its reverse is the most common way `/check` surfaces `missing-field` errors. Doing both together eliminates the class entirely." `:94` "It also makes rollbacks straightforward". 이슈 #42 작성자 답 "A human maintaining 200+ interlinked markdown files will inevitably let reverse links and cross-references decay."

### D10. `/init`은 worktree 병렬 ingest, 충돌은 fan-in에서

- (a) PR #1 "The previous design ingested N papers sequentially … taking ~40 minutes for 10 papers. The bottleneck was intentional — later papers needed to read wiki state from earlier ones for concept dedup. This dedup can instead be handled at merge time". "Estimated speedup: ~3–5x".
- (a) `merge=union` 이유: `.gitattributes` 주석 "git's default line-based merge sees concurrent appends … reports add/add or content conflicts on EVERY merge — even though the resolution is always "keep both sides"."
- (a) 경험에서 나온 방어: PR #6 "Worktree isolation bypass: subagent prompts contained `Working directory: /home/...`; agents used that for every Read/Write/Edit and silently wrote to the main repo." → 상대 경로만 쓰게 함(`init/SKILL.md:165`).
- 대안과 바뀐 이력: Codex·OpenCode 브랜치는 직렬을 기본으로 되돌렸다(§7). README main도 "serially by default, with optional parallel worktree mode"라고 적는다(`README.md:482`, 이 문구는 `9b00adf`에서 들어옴). 그러나 main의 `init/SKILL.md:234`는 "all paper ingest must run through parallel `/ingest` subagents with worktree isolation"이다 — §6 불일치.

### D11. raw는 사용자 소유·읽기 전용, skill은 `raw/discovered/`·`raw/tmp/`에만

- (a) `CLAUDE.md` Hard Rule 1. `reset/SKILL.md:97` "`raw/` deletes are irreversible: PDFs are not in git history."
- [추정] 원문을 손대지 않아야 다시 ingest해도 같은 입력이 보장된다(사례: `pdf-preprocessing.md:58` "Do not re-copy the PDF into `raw/papers/`; the original path remains the user-owned artifact." 1건).

### D12. PDF 제목은 LLM이 먼저 본다(agent-first)

- (a) PR #22 "Agent-first PDF title extraction —— deterministic tools struggles to infer correct titles." `pdf-preprocessing.md:41` 메타데이터·파일명 제목을 권위로 쓰면 "poisons the Semantic Scholar lookup". `:49` "letting a parsed-TeX title overwrite it creates subtle identity drift."
- D1과 반대 방향의 결정이다. 결정적 도구가 못하는 일만 LLM에 둔다는 점에서 일관된다.

### D13. notes/web에서 나온 페이지는 "임시"로 표시

- (a) `init/SKILL.md:137` "notes/web are authoritative for user intent, not for literature confidence". `:233` "paper evidence outranks notes/web for concept consolidation and method extraction".
- 개념은 notes/web에서 두 번 나오거나 notes/web 한 번 + 논문 한 번일 때만 만든다(`:146`).

### D14. 실패한 아이디어를 지우지 않고 기억한다

- (a) 이슈 #11 작성자 답 "one of the reasons we decided to include experiment executions in a "wiki" is that we figured out we could store failures and learned lessons … so we don't cold-start each experiment and watch it repeat the same mistakes." `check/SKILL.md:98` "failure_reason: must be non-empty when status=failed (anti-repetition memory)". `ideate/SKILL.md:509` "Eliminated ideas are also written to wiki". 논문 §4.2 "providing the evidence, prior failures or lessons needed for that skill"(WebFetch 인용).

### D15. 두 번째 LLM(Review LLM)을 독립 심사자로

- (a) `cross-model-review.md:26-28` "Anchoring bias: If the Review LLM sees "Claude rated this 7/10", its review will cluster around 7." "Diversity of perspective: The entire value of cross-model review is that different models have different biases." 논문 §3.3 "content checks are handled by an independent reviewer agent", "since memory errors can propagate to future projects".
- 대안: 같은 모델 자기검토(폴백으로만 허용, `cross-model-review.md:84-88`).

### D16. 판정이 엇갈리면 보수적으로

- (a) `novelty/SKILL.md:164` "Take the lower of Claude's search-based score and Review LLM's score (conservative principle)". `:184` "underestimate novelty rather than overestimate to avoid wasting effort on known work". `exp-eval/SKILL.md:285`.

### D17. 사람 게이트는 "돌이킬 수 없는 일·비용이 큰 일" 앞에

- 게이트 자리: 실험 코드 배포 전(`exp-run/SKILL.md:9`), pilot 실행 전(`exp-pilot-run/SKILL.md:10`), 설계 확정 전(`exp-design/SKILL.md:272`), `/reset` 실행 전(`reset/SKILL.md:59` "Never proceed without explicit approval"), `/ask` 결정화(`ask/SKILL.md:182`), `/check` 비결정 수정(`:174`), `/daily-arxiv auto-ingest` opt-in(`daily-arxiv/SKILL.md:26`), `/discover` 후보 선택, Hiera approve.
- (a) 이유가 적힌 것은 일부다: `/reset` — "destructive and `raw/` deletions are not tracked by git"(`:59`). `/daily-arxiv` — "Never infer `auto-ingest` from repository state, branch name, existing workflow, or available credentials."(`recommendation-and-ingest-policy.md:59-60`). 플래그 일반 — `CLAUDE.md` Hard Rule 5 "User-facing skill flags … are user-owned. Do not invent, flip, or drop them based on repo state."
- 모르는 것: 실험 배포 전 수동 검사 게이트의 이유는 문서에 없다. 논문도 이유를 말하지 않는다(WebFetch 결과 "The document does not explain this."). 게이트가 들어온 commit은 `8e6af2d` 안의 "update detailed restriction of design run and pilot-run"이다. 그 PR(#53/#54) 토론이나 원 브랜치 commit diff를 보면 알 수 있다.
- [추정] GPU 비용·데이터 경로·API 키처럼 에이전트가 틀리면 시간·돈이 새는 자리라서다(사례: 게이트 문구가 "Dataset paths, interface parameter selection, API configuration"을 직접 꼽음, `exp-run/SKILL.md:9` 1건).
- `--auto`의 한계: `/research --auto`는 Gate 1·2를 건너뛰지만(`research/SKILL.md:23`), `/exp-design`에는 `--auto`가 없고(argument-hint `<idea-slug>`) 사용자 선택·승인 게이트가 있다(`:88`, `:272`). `/exp-run`의 수동 검사도 "No matter which operation mode it is"(`:9`). 그래서 "fully automatic" 경로에서도 사람이 실험 앞에서 멈춘다.

### D18. 실험 결과를 받는 쪽은 `/exp-eval`만, 탐색 결과(Hiera)는 wiki에 쓰지 않는다

- (a) `exp-run/SKILL.md:373` "Do not update the linked idea's status: … idea updates are handled by /exp-eval". `rebuttal` Constraints "status transitions are reserved for `/exp-eval`". Hiera README:321 "It does not write wiki pages or turn exploratory evidence into a formal claim." `:358` "Its ledger and reports are sidecar evidence; the normal AutoSci workflow remains available for confirmation."
- [추정] 탐색적 결과와 확인된 결과를 섞지 않으려는 분리다(사례: Hiera 문서가 "formal claim"·"confirmatory"를 3곳에서 씀, `SKILL.md:17`, `README.md:321`, `:332`).

### D19. 쓰기 권한(writers.yaml)은 명세일 뿐 강제하지 않는다

- (a) `runtime/policy/writers.yaml:3-14` "STATUS: SPEC, NOT A RUNTIME GATE. … We deliberately did not plumb a `--skill` arg through set-meta / add-edge: research workflows are fluid, and `/edit` exists as a designed escape hatch … runtime enforcement here would either fight `/edit` or grow a long exception list." `:13-14` "When this file disagrees with reality, update the file (or the offending SKILL.md) — do not add runtime checks."
- 엔터프라이즈 관점에서 가장 중요한 결정 중 하나다(§5).

### D20. 공유 파일은 도구로만, append로만

- (a) `init-mode.md:31-35` "Every shared-file write goes through a tool", "Never lock or in-place-rewrite a shared file. … replaces parallel peers' work when the worktrees merge." 또 "batch ingest is already on the roadmap"(`:31`).

### D21. 인용은 외부 권위 출처에서만, 못 구하면 `[UNCONFIRMED]`

- (a) `citation-verification.md:12` "LLMs hallucinate citation details (wrong year, wrong venue, wrong authors, non-existent papers)." `:90` "wrong venue/year is worse than [UNCONFIRMED]". `:91` "Never cite a paper not in the wiki".

### D22. 재검색 도구 둘을 일부러 따로 둔다(`/init` planner vs `/discover`)

- (a) `discover/references/ranking-signals.md:3` "documents … **why it differs from `/init`**, so that future edits do not accidentally re-converge the two." `:57` "prefer keeping two implementations rather than extracting a shared scorer. The objectives genuinely differ".
- (a) `/init`의 최신성 편향 수정 계기: 이슈 #5 "papers are ranked by citation count … that structurally favor older work". 반영 자리: `planner-policy.md:11` "freshness should dominate and older external non-survey papers should not pile up via citation advantage."

### D23. skill 문서를 SKILL.md + references로 쪼갠다(필요할 때만 열기)

- (a) PR #22 "Added level 3 references. It's no longer a single verbose SKILL.md." PR #18 "Extract CLAUDE.md: split runtime schema into `docs/runtime-*.md` to reduce context window cost".
- 이력: `ingest/SKILL.md` 줄 수 434(`e37d86a`) → 230(`0366aea`), references 5개 신설(`git show --stat 0366aea`).

### D24. 원문은 `.tex` 우선, PDF는 합성 tex로 정규화

- (a) `pdf-preprocessing.md:7` "A PDF on its own is a poor ingest source: text extraction quality varies, equations and captions are easy to miss, and the reference list is often unreliable. … we still normalize the PDF into a synthetic `.tex` so the rest of `/ingest` works from one uniform input shape."

### D25. 질의 답을 wiki로 되돌린다(crystallize), 단 기본은 쓰지 않음

- (a) `ask/SKILL.md:9-11` "Good answers can be crystallized back into the wiki … so exploration compounds like ingestion does." 쓰지 않을 신호: "The answer relies primarily on inference rather than wiki evidence"(`:107`). 기본 비활성: `:182`.

### D26. 영어가 원본, 중국어는 번역, 활성 사본은 생성물

- (a) `CONTRIBUTING.md` "English is canonical." 이력: PR #74(`5568c25`) "i18n/en is the documented source of truth … but contributors had also hand-edited the active .claude copy directly, so the two drifted apart." 그 뒤에도 `research`는 다시 어긋나 있다(§6).

### D27. claims 엔티티를 버리고 methods를 넣었다

- (a) 이슈 #31 "`claims` 和 `ideas` 语义重叠（两者都是「可验证的命题」）"(claims와 ideas는 둘 다 "검증 가능한 명제"라 뜻이 겹친다), "更有价值的 `methods`（跨论文复用的具名技术）没有实体"(더 가치 있는 methods — 논문을 가로질러 재사용되는 이름 붙은 기법 — 에 엔티티가 없었다). CHANGELOG 1.1.0 "verifiable hypotheses now live on `ideas` pages".
- 이력: `1b2df1f`(v1.1.0, 2026-05-06). 기존 claims는 "not migrated".

## 4. 앞선 schema-glossary 보고서와 어긋나거나 보탤 점

앞선 보고서: `llm-wiki-implementations/lab/reports/schema-glossary/autosci-omegawiki-schema.md`.

1. **F 절 "`neighbors` BFS가 foundation을 통과해 허브 문제를 못 푼다"** — 코드 사실은 맞다. 그러나 main의 어느 skill도, `app/`·다른 `tools/`도 `neighbors`를 부르지 않는다(§1.3 grep). 그래서 이 구멍은 지금 사용 경로에서 드러나지 않는 잠재 구멍이다. skill이 "연결"을 보는 길은 `context_brief.md`·`index.md`·`edges.jsonl` 직접 읽기다. `/ask`는 X-Y 사이 엣지만 읽는다(`ask/SKILL.md:81`). 보고서의 "이 탐색 방식이면 엉뚱한 연결은 그대로 생긴다"는 `neighbors`를 실제로 쓰는 경우의 가정으로 낮춰 적어야 한다. 웹 SPA 그래프 화면(`app/modules/graph.js`)이 foundation을 어떻게 다루는지는 이 갈래에서 보지 않았다.
2. **F 절 "`compile_context`가 방법을 연결 수 내림차순으로 보여 준다"** — 맞다. 다만 skill은 `rebuild-context-brief`(= `general` 예산)만 부르고, 목적별 예산 표 `CONTEXT_BUDGETS`(`tools/research_wiki.py:1244-1251`, ideation/experiment/writing/review/general)는 skill에서 쓰이지 않는다.
3. **G 절 상태 기계** — 보고서는 `transition`이 YAML 표를 쓴다고 정확히 고쳤다. 보탤 점: skill들이 그 표와 어긋난다. `exp-pilot-eval`은 `proposed` 아이디어를 `transition --to failed`로 보낸다(`exp-pilot-eval/SKILL.md:82`, `:133` "`proposed → failed`"). 표는 `proposed: [in_progress]`만 허용한다(`runtime/schema/entities.yaml:99`). 도구는 이 전이를 "Invalid: proposed -> failed"로 거부한다(`tools/research_wiki.py:1630-1637`). Codex 브랜치는 표를 `proposed: [in_progress, failed]`로 고쳤다(`92f397e`, `git diff origin/main origin/autosci-codex -- runtime/schema/entities.yaml`). main과 OpenCode 브랜치는 그대로다.
4. **E 절 "사람 승인: 승인 대기열 파일은 없다. 보고서가 대기열 역할"** — 맞다. 보탤 점: 작성자 스스로 `/check`가 사람이 기억할 때만 도는 수동 보고서이고, CI auto-ingest는 `/check` 없이 커밋한다고 밝혔다(이슈 #41). 이슈 #41에서 작성자는 PR 댓글형 검증기를 선호한다고 답했다.
5. **B 절 "추출 전 프롬프트에 용어 목록 전체를 넣지 않는다"** — 맞다. 보탤 점: 질의 쪽(`/ask`)도 별칭을 보지 않는다. `index.md`에 aliases가 없기 때문이다(§2.3).
6. **H 절 "효과 수치 없음"** — 저장소 밖 근거로 보탤 것: 이슈 #42 작성자 답 "To our knowledge, there is no such benchmarks to measure the performance of LLM-wiki maintained by agent and an organized set of markdown files." 반대로 정성 수치 2건이 commit·PR에 있다: PR #6 test6(15편 → claims 45 + concepts 37, 정답은 약 15/15), `8e6af2d` 메시지(9편 → 개념 23). 둘 다 측정 설계가 없는 실행 기록이다.
7. 보고서는 테스트가 `tests/test_hiera_local.py` 하나뿐이라고 적었다. 이유는 `b36c1df`("Rebuild ingest. Deleted tests.", 2026-04-24)가 tests 16,400줄(73파일)을 지운 것이다. 지운 이유는 commit 메시지에 없다.

## 5. 엔터프라이즈 다중 작성자 보고서 용도에 비춰

조건: 작성자마다 용어가 다르다, 형식 없는 문서가 있다, 여러 사람이 쓴다, 권한이 필요하다.

### 쓸 만한 장치

| 장치 | 왜 맞나 | 가져갈 때 손볼 점 |
|---|---|---|
| 생성 직전 결정적 대조 + "기본은 병합" + 문서당 생성 한도(D3) | 용어 불일치가 곧 근사 중복 개념 폭증이다. PR #6의 45/37 사례가 그대로 겹친다 | 대조 입력에 사내 용어집(정식 이름+별칭)을 넣는다. 한도 초과분은 버리지 말고 대기열 파일로 |
| `raw/notes`·`raw/web` → "Provisional note" 표시(D13) | 형식 없는 사내 문서를 "의도는 믿되 사실 확인 전"으로 넣는 틀이다 | 엔터프라이즈에서는 형식 없는 보고서가 다수다. "임시 → 확인" 승격 절차를 명시해야 한다. AutoSci는 승격 절차가 없다(임시 표시 줄을 누가 지우는지 적힌 곳이 없음) |
| PDF는 LLM이 먼저 정체를 잡고 도구가 정규화(D12, D24) | 사내 PDF·docx는 메타데이터가 엉망이다 | arXiv·S2 같은 외부 정체 확인처가 사내에는 없다. 문서 ID 체계가 필요하다 |
| `foundation` terminal 계층 + `/prefill`(D6) | 사내 범용어(우리 회사 이름, "프로젝트", "고객")가 허브가 되는 것을 막는다 | catalog를 도메인 팀이 관리하게 한다 |
| 실패 기억(banlist, D14) | "이미 해 봤는데 안 된 것"이 보고서끼리 이어진다 | `failure_reason` 같은 필드를 결정 문서에 둔다 |
| 공유 파일은 도구·append만 + `merge=union`(D20) | 여러 사람이 동시에 넣어도 log·edges가 깨지지 않는다 | git 기반이라 동시 편집이 잦으면 병목. 서버형 저장소로 옮길 때 같은 불변식만 유지 |
| 프롬프트 규칙 → 도구 거부로 승격(D2) | 사람이 섞여 쓰면 프롬프트 규율은 더 쉽게 깨진다 | 엔터프라이즈 권한 검사도 이 자리에 둔다 |
| 사람 게이트를 비용 큰 일 앞에만(D17) | "어느 정도 사람이 하더라도"와 맞다 | 병합 결정(0.40~0.80 구간)에도 게이트를 둘지 정해야 한다. AutoSci는 이 구간을 LLM 혼자 판단한다 |
| `/ask` 결정화(D25) | 질의가 새 연결고리를 wiki에 남긴다 — 사용자 목표의 "연결고리 발견"에 직접 닿는다 | 결정화 페이지(`outputs/`)는 schema 밖이다. lint가 보지 않는다 |
| 서지 층과 의미 층 분리(D8) | 보고서 간 "참조" 와 "같은 문제를 다룸"을 섞지 않는다 | 사내 문서의 "참조"를 뽑는 결정적 방법(링크·문서번호)이 필요하다 |
| Review LLM 독립 심사(D15) | 병합·연결 판단을 두 모델로 교차 확인 | 비용. 사내 모델 정책 |

### 걸리는 점

- **권한이 없다(필수 확인 사항).** 쓰기 권한 파일은 "SPEC, NOT A RUNTIME GATE"이고 일부러 강제하지 않았다(`writers.yaml:3-14`). 기본 설정은 `Bash(*)`·`Edit(*)`를 모두 허용한다(이슈 #45, 작성자가 문서를 실제에 맞췄을 뿐 범위는 줄이지 않음). 이 상태로는 작성자별·팀별 쓰기 제한이나 열람 제한이 불가능하다.
- **행위자 기록이 없다.** `log.md` 줄은 날짜와 자유 문자열뿐이다(`tools/research_wiki.py:2088`). 누가 병합했는지, 어느 작성자의 문서에서 왔는지 남지 않는다. 엣지에도 작성자 필드가 없다(`edges.yaml` attributes는 confidence·evidence·source·date).
- **질의가 별칭을 못 본다.** `/ask` 검색은 index의 slug·title·tags와 LLM 판단뿐이다(§2.3). 작성자마다 다른 용어로 물으면 놓친다.
- **사후 검사가 수동이다.** `/check`는 사람이 돌릴 때만 돈다(이슈 #41). 여러 사람이 수시로 넣는 환경에서는 CI 검증이 필요하다.
- **"얼마나 만들었어야 했나"를 아무도 검사하지 않는다.** 작성자 답 "known blind spot"(이슈 #41).
- **개념 정의가 바뀌어도 감지하지 못한다.** 작성자 답 "What drifts undetected: a concept's definition evolving while linking papers still describe the old version."(이슈 #41). 사내 용어 정의는 자주 바뀐다.
- **도메인 고정.** 엔티티(papers·venue·arXiv·S2)와 외부 API가 학술 논문 전용이다. 이슈 #67에서 작성자는 "AutoSci is currently focused on CS/AI research and we'd like to keep the core lean."이라고 일반화 요청을 보류했다.
- **skill 문서끼리·skill과 도구가 어긋난다**(§6). 사람이 여러 명 쓰면 어긋남이 더 빨리 쌓인다. 작성자 자신도 `5568c25`에서 drift를 한 번 정리했고 다시 생겼다.
- **병렬 경로 이식성.** worktree 병렬 ingest는 Claude Code의 subagent·worktree 기능에 기대고, Codex·OpenCode 브랜치는 직렬로 되돌렸다(§7).

## 6. 레포 안 불일치 목록 (skill ↔ skill, skill ↔ 도구, 문서 ↔ 문서)

| # | 내용 | 출처 | 강도 |
|---|---|---|---|
| 1 | `exp-pilot-eval`이 `proposed → failed` 전이를 부르지만 lifecycle 표가 허용하지 않는다. 도구가 거부한다 | `exp-pilot-eval/SKILL.md:82,133`, `entities.yaml:99`, `research_wiki.py:1630-1637`; Codex 브랜치 `92f397e`에서 표 수정 | 필수: 이대로면 pilot 실패 기록이 실패한다 |
| 2 | `/ideate`가 탈락 아이디어를 frontmatter에 `status: failed`로 직접 쓴다. `exp-eval`은 "Use `tools/research_wiki.py transition` (not direct frontmatter writes)"라고 한다 | `ideate/SKILL.md:311-316`, `exp-eval/SKILL.md:283` | 참고: 도구 검사를 우회하지만 데이터는 lint 통과 |
| 3 | `/research` Gate 1이 "proposed → in_progress"를 하라는데, 그 시점에는 `/exp-design`(Stage 2)이 아직 `linked_experiments`를 채우기 전이다. `transition`은 빈 `linked_experiments`면 거부한다 | `i18n/en/skills/research/SKILL.md:212`, `research_wiki.py:1641-1646` | [추정] 도구 대신 `set-meta`나 직접 편집으로 처리될 것이다(사례: Gate 1 문장에 도구 이름이 없음 1건) |
| 4 | `/ideate` Phase 3이 `/novelty <idea-slug> --write`를 부르지만 idea 페이지는 Phase 4에서야 생긴다. `/novelty --write`는 페이지가 있어야 동작한다 | `ideate/SKILL.md:220-226` vs `:247-257`, `novelty/SKILL.md:21`, `:197` | 참고 |
| 5 | `/research` 활성 사본(`.claude/`)은 빈 wiki에서 자동 부트스트랩(5편 자동 ingest), 원본(`i18n/en`)은 `/init`으로 넘김. `9b00adf`가 i18n만 고치고 `setup.sh`를 다시 돌리지 않았다 | `diff .claude/skills/research/SKILL.md i18n/en/skills/research/SKILL.md`, `git log -1 -- .claude/skills/research/SKILL.md` → `8e6af2d` | 필수(사용 시): 클론 직후 Claude Code가 읽는 것은 옛 동작 |
| 6 | README는 `/init`이 "serially by default"라 하고 main `init/SKILL.md:234`는 병렬 필수 | `README.md:482`, `init/SKILL.md:234` | 참고 |
| 7 | `ingest/SKILL.md:263` "slug collisions append a numeric suffix" vs `error-handling.md:20` 논문 slug 충돌은 "stop and report. Do not append a numeric suffix silently"(개념·방법만 접미사, `:22`) | 두 곳 | 참고 |
| 8 | `/edit`이 arXiv URL을 `raw/papers/`에 내려받고 raw 파일을 지운다. Hard Rule 1은 skill이 `raw/discovered/`·`raw/tmp/`에만 쓴다고 한다 | `edit/SKILL.md:19`, `:33-35`, `CLAUDE.md` Hard Rule 1; 단 `edit/SKILL.md:58`은 "may add files to `raw/`" | 참고: `/edit`은 사람 요청 탈출구라는 설계(D19)와는 맞음 |
| 9 | `writers.yaml`의 쓰기 주체와 skill이 다르다: `derived_from: [ingest]`인데 `/ask`·`/paper-plan`·`/survey`도 씀. `ideas.status` writers에 `research`가 없는데 `/research`가 Gate 1·Stage 3c에서 바꾼다. `refine`은 writers에 있지만 SKILL에는 status 변경 단계가 없다 | `writers.yaml:51`, `:95`, `ask/SKILL.md:55-57`, `research/SKILL.md:212,326` | 참고: 명세이고 강제 아님 |
| 10 | `/research` 제약 "Orchestrator does not directly modify wiki entities"와 Gate 1·Stage 3c의 idea status 변경 | `research/SKILL.md:482` vs `:212`, `:326` | 참고 |
| 11 | skill 문서의 MCP 호출 키 `message`와 서버 스키마 키 `prompt` | `novelty/SKILL.md:107-113`, `server.py:186-192` | 참고 |
| 12 | `CONTRIBUTING.md`가 `docs/extending.md`와 `tests/test_skill_validation.py`를 가리키지만 둘 다 HEAD에 없다 | `CONTRIBUTING.md`, `ls docs tests` | 참고 |
| 13 | `research`의 progress 템플릿에 `monitoring_cron_id`가 없는데 복원 대상에 있다 | `research/SKILL.md:93` vs `:99-115` | 참고 |
| 14 | `exp-eval` "Take the more conservative verdict (supported > partially_supported > not_supported)" — 괄호 순서가 보수성 순서인지 반대인지 문장만으로 모호 | `exp-eval/SKILL.md:132` | 참고 |

## 7. Codex·OpenCode 브랜치와 갈리는 점 (얕게)

두 브랜치 모두 merge-base가 `a01841d`(main의 2026-07 초)다.

| | `autosci-codex` (`215d45c`, 2026-09-28) | `autosci-opencode` (`4564250`, 2026-07-12) |
|---|---|---|
| 규모 | 209파일 +4640/−4005 | 203파일 +2292/−20179 |
| skill 자리 | `.claude/skills/*` → `.agents/skills/*`(rename), `CLAUDE.md` → `AGENTS.md`, 호출 `$skill` | `.claude/skills` 삭제, `.opencode/skills`는 setup이 만들고 gitignore. `AGENTS.md` |
| `/init` 병렬 ingest | "Codex should use the serial contract by default"(`.agents/skills/init/references/parallel-ingest.md`), `init-handoff.json`, INIT MODE SERIAL, 직렬 모드는 커밋 안 함, detached HEAD 허용. `ingest/references/init-mode.md` 삭제. commit `d9d32fc` | "SANDBOX GATE — … Do **not** attempt in sandboxed environments … Use the default sequential ingest"(`i18n/en/skills/init/references/parallel-ingest.md` 첫 줄) |
| lifecycle | `proposed: [in_progress, failed]`(`92f397e`) | main과 같음 |
| daily-arxiv | `codex exec --output-schema` 추천, CI auto-ingest는 Claude Code Action 경로 유지(`e0cf1fd`) | "Simplified daily-arXiv into a recommendation-only pipeline: removed … automatic ingestion"; CI는 읽기 전용 권한, 커밋 안 함(`4564250` 메시지) |
| 권한·샌드박스 | `tools/_sandbox.py` 추가(78줄), `config/codex.config.toml.example` | "Replaced legacy Claude/Codex sandbox escalation logic with OpenCode permission configuration" |
| 검증 | `docs/codex-smoke-test-matrix.md` "The local migration suite is not enough to mark the Codex migration complete."(`25d30c0`) | "verified it loads correctly in a real OpenCode session" |
| 문구 | "Claude" → "the primary agent"(`cross-model-review.md`) | OpenCode 고유 frontmatter(`name:` 필드 추가) |

- 갈리는 방향: 두 이식 모두 Claude Code 고유 기능(백그라운드 subagent + worktree 격리)에 기댄 병렬 ingest를 기본에서 내렸다. [추정] 런타임 이식성이 병렬 속도보다 우선이었다(사례: 두 브랜치가 독립적으로 같은 선택을 함 2건, codex 문구 "Use the parallel worktree contract only when the runtime can guarantee subagent working directories, per-paper commits, and fan-in merge control").
- OpenCode는 무인 auto-ingest 자체를 없앴다. 이유는 commit 메시지에 결과만 있고 "왜"는 없다.
- `paper` 브랜치(논문 스냅숏, `README` "main = stable, paper = paper snapshot", `03a78ee`)에는 main에 없는 `dream`(기억 망각·통합·연관 제안), `forge`(skill 문서 자체 패치), `morph`, `*-dag` skill이 있다. `dream`은 "useful latent associations become reviewable proposals"(`git show origin/paper:i18n/en/skills/dream/references/memory-operations.md`)라고 해서 사용자 목표의 "연결고리 발견"과 가장 가깝다. 자동 적용은 "only as reversible frontmatter metadata plus an append-only audit note"로 제한한다. 훑음.

## 8. 모르는 것과, 무엇을 보면 알 수 있는지

1. 실험 배포 전 수동 검사 게이트를 넣은 이유 — PR #53/#54의 리뷰 토론, 또는 원 브랜치(`refactor/wuxinzhe-exp-idea`)의 "update detailed restriction of design run and pilot-run" commit diff와 메시지.
2. `b36c1df`가 테스트 16,400줄을 지운 이유 — 같은 날 PR #23 본문은 "A preliminary version."뿐이다. PR #23·#26 리뷰 댓글이나 작성자에게 물어야 안다.
3. method 대조 도구가 없는 이유 — 이슈 #31 본문 전체("Open questions" 절)를 끝까지 읽으면 단서가 있을 수 있다.
4. `exp-pilot-eval`의 `proposed → failed`가 실제 실행에서 어떻게 처리되었는지(에이전트가 `set-meta`로 우회했는지) — 실제 사용자 wiki의 `log.md`나 이 skill로 만든 ideas 페이지. 레포에는 실행 산출물이 지워져 있다(`8667bd7` "clean log for main").
5. 0.40~0.80 구간에서 LLM이 실제로 병합을 얼마나 고르는지 — 실행 기록이 없다. `8e6af2d`의 squash 이전 commit들(이미 squash되어 레포에 없음) 또는 작성자 실험 로그.
6. 웹 SPA 그래프(`app/modules/graph.js`)가 foundation 경유 경로를 어떻게 그리는지 — 시각화 갈래 노트.
7. `/research --auto`가 `/exp-design`의 사람 게이트를 실제로 어떻게 넘는지(멈추는지, 자동 선택하는지) — 실행 기록이나 이슈. 문서만으로는 둘이 충돌한다.
8. 사내 문서 같은 비학술 입력에 대한 작성자 계획 — 이슈 #11 답의 "nano-wiki … accepting various kinds of info"가 이후 생겼는지. 원격 브랜치 목록에는 없다(`git branch -r`). 작성자 다른 저장소를 찾아봐야 한다.

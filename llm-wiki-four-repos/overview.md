# llm-wiki 네 구현의 큰 구조와 기능 — jonex·AutoSci·sage-wiki·gd4ai

jonex, AutoSci, sage-wiki, gd4ai 네 레포가 llm-wiki를 어떻게 짰는지 큰 구조와 기능만 한 장에서 견준다.
레포별 보고서(`lab/reports/<repo>.md`)보다 먼저 읽는다. 다 읽으면 어느 보고서의 어느 절을 더 열지 고를 수 있다.

사실은 모두 검증을 마친 레포별 보고서에서 옮겼다. 이 문서를 쓰며 레포 코드를 실행하지 않았고, 검증 때 경로와 줄 번호를 확인하려고만 열었다.
사내 보고서용 llm-wiki에 비춘 판단은 #엔터프라이즈 조건별 지도와 #차용 지도에 모았다.

## 표기와 말

| 표기 | 뜻 |
|---|---|
| `결정 7`, `W5` | 그 레포 보고서 #왜 이 구조인가의 결정 번호. jonex·sage-wiki는 숫자를, AutoSci·gd4ai는 W번호를 쓴다 |
| `축 5` | 그 레포 보고서 #축별 분석의 5번 축. 축 16개의 이름은 앞선 비교 문서 `../llm-wiki-implementations/lab/reports/00-comparison.md` #설계 축별 스펙트럼을 따른다 |
| `#한눈에`, `#한 바퀴`, `#엔터프라이즈`, `#가져올 것`, `#확인하지 못한 것` | 그 레포 보고서의 #한눈에, #한 바퀴 흐름, #엔터프라이즈 llm-wiki에 비추어, 그 아래 #가져올 것, #확인하지 못한 것. 이 문서 자신의 절은 "이 문서 #…"로 쓴다 |
| 표 칸 안의 위 표기 | 그 칸이 속한 열이나 행의 레포 보고서를 가리킨다 |
| `[LLM]`, `[코드]` | 그 단계를 모델이 판단하는가, LLM 없이 결정적 코드가 하는가 |
| `[추정]` | 레포 여럿을 견주어 이 문서가 끌어낸 판단. 사례와 개수를 붙인다 |
| `path:line` | 그 레포 루트 기준 줄. 분석 commit은 `lab/README.md` 표에 있다 |
| jonex 경로 `JW/`·`C/`·`SP/`·`M/`·`Q/`·`KB/` | jonex 보고서 머리의 줄임표를 따른다. 예: `C/` = `Reference/JonexWiki/src/jonex_wiki/domain/engine/compile/` |
| AutoSci 경로 `ingest/SKILL.md` | `.claude/skills/ingest/SKILL.md`. 다른 skill도 같다 |
| sage-wiki의 디렉터리 없는 `.go` | `internal/compiler/` 아래 파일 |
| `D1`~`D12` | 앞선 비교 문서 #내 llm-wiki를 설계할 때 정해야 할 결정들이 매긴 결정 12개. #차용 지도에서 뜻과 함께 쓴다 |

| 말 | 뜻 |
|---|---|
| 결정적 | LLM을 부르지 않고, 같은 입력이면 같은 결과를 내는 처리 |
| gate | 조건을 못 맞추면 쓰기나 발행을 거부하는 코드 검사 |
| 정체 판정 | 새로 뽑은 이름이 기존 페이지와 같은 대상인지 정하는 일. 보고서마다 dedup·identity·entity resolution이라 부른다 |
| 근거 장부 | 사실 한 건마다 원문 위치를 페이지와 따로 적어 두는 기록 |
| passage | jonex가 LLM 호출 하나에 넣는 원문 단위. 파싱 블록 여러 개를 약 4,000 token으로 묶는다 |
| summary, concept, article | sage-wiki 패스의 산출물. 문서당 요약, 거기서 뽑은 대상 이름, 대상마다 쓴 페이지 |
| BM25, FTS5 | 낱말 빈도로 순위를 매기는 검색. FTS5는 SQLite의 전문 검색 기능이다 |
| RRF | 검색 갈래 여럿의 순위를 `Σ w/(60+rank)`로 더해 합치는 방법 |
| PPR | Personalized PageRank. 시작 페이지에서 링크를 따라 걷다가 확률적으로 돌아오기를 되풀이해 가까운 페이지를 고른다 |
| bundle | jonex의 발행본 한 벌. 내용 해시를 이름으로 단 불변 디렉터리다 |
| compile key | sage-wiki가 문서마다 계산하는 입력 해시. 원문·프롬프트·모델·config가 같으면 다시 컴파일하지 않는다 |
| tier | sage-wiki가 문서마다 정하는 처리 깊이. 0은 색인만, 3은 LLM 전체 컴파일이다 |
| skill | Claude Code가 읽고 따르는 단계 문서 `SKILL.md` |
| 작은 모델 | 사용자 로컬 Ollama에 있는 exaone3.5:2.4b, gemma4:e2b-it-qat, llama3.1:8b 같은 모델 |

## 네 레포 한 줄

| 짧은 이름 | 저장소 | 한 줄 | 보고서 |
|---|---|---|---|
| jonex | yuezhiai/jonex의 JonexWiki 엔진 | 기업용 지식 플랫폼 안의 엔진. LLM은 원문 발췌 고르기와 규칙이 못 정한 정체 판정만 맡고(수리 라운드 예외, jonex 축 2), 사실 검증·페이지 작성·링크는 코드 규칙이 정해서, 페이지 줄마다 원문 문자 구간으로 되돌아간다 | `lab/reports/jonex.md` |
| AutoSci | skyllwt/AutoSci(구 OmegaWiki) | 연구 수명주기용 Claude Code skill 29개. LLM이 논문을 읽고 페이지를 직접 쓰지만, 프롬프트 규율이 깨진 자리마다 엣지·인용·log 쓰기와 개념 대조를 YAML schema를 읽는 Python 도구로 옮겼다 | `lab/reports/autosci.md` |
| sage-wiki | xoai/sage-wiki | Go 바이너리 하나. raw를 summary → concept → article로 다패스 컴파일하고, 깨진 가정마다 LLM 판단 아래 결정적 규칙을 깔며, 돈이 들거나 되돌리기 어려운 패스는 opt-in으로 둔다 | `lab/reports/sage-wiki.md` |
| gd4ai | GD4AI/obsidian-llm-wiki | Obsidian 플러그인 하나. LLM은 읽기·판정·문장만 맡고 이름 연결·출처·문턱은 코드가 쥐며, 그 경계를 작성자들의 vault 실측이 한 칸씩 옮겨 왔다 | `lab/reports/gd4ai.md` |

jonex 레포에는 엔진이 셋(lightrag 그래프, OpenKB 복사본, JonexWiki) 있고, 이 문서는 JonexWiki만 본다(jonex #한눈에).

## 한눈에

첫 표는 형태와 가져다 쓸 조건이다. 출처는 각 보고서 #한눈에다.

| 항목 | jonex | AutoSci | sage-wiki | gd4ai |
|---|---|---|---|---|
| 형태 | Docker 플랫폼 안 Python 엔진, 단일 인스턴스 강제 | Claude Code `/skill` + Python CLI, 로컬 웹 SPA, 심사용 MCP 서버 | Go 바이너리 하나가 CLI·MCP·REST·web UI를 낸다 | Obsidian 플러그인. 서버·DB·임베딩 없음 |
| 규모 | JonexWiki Python 57,603줄, commit 38개 | Python 21,202줄 + skill 문서 10,199줄, commit 108개 | Go 비테스트 83,709줄, commit 917개 | TS 비테스트 66,084줄, commit 1,224개 |
| 라이선스 | 수정 Apache-2.0. 서면 허가 없이 다중 테넌트 운영 금지(`LICENSE:6`) | MIT | MIT. 예외 셋(eval 일부 Apache-2.0, HNSW CC0, 별도 pack registry) | Apache-2.0. 2026-07-03 전 판은 MIT |
| 차용 방식 | 설계만 참고해 다시 쓴다 | 고지를 남기고 코드째 | 코드째 | LICENSE·NOTICE를 두고 코드째 |
| 성숙도 | 공개 테스트·CI·태그 없음. 엔진 전체가 commit 하나로 들어옴 | main의 테스트 파일 2개(`b36c1df`가 `tests/`를 지움). CI는 일일 추천 하나 | 테스트 437 파일, CI 10개, 태그 23개 | 테스트 327 파일, PR마다 5단 CI, 태그 89개 |

둘째 표는 일의 나눔과 저장이다.

| 항목 | jonex | AutoSci | sage-wiki | gd4ai |
|---|---|---|---|---|
| LLM이 맡는 일 | 원문 발췌 고르기, 미정 정체 판정, open Blocking이 있을 때 Error Book 수리안(받아들여지면 페이지 스냅숏을 통째로 바꿈, 축 2), 조회 탐색·답 | 페이지·index 쓰기, 병합 판단, 엣지 고르기, 조회 | summary, concept 추출, article 본문, 조회 답 | 추출, 좁은 창 정체 판정, 페이지 문장, 모순 확인, 조회 답 |
| 코드가 맡는 일 | 신원·근거 구간·지지 판정, 페이지 본문, 링크, 발행 | slug, 대조 점수, 엣지 검사, lint, 파생물 재생성 | 증분, 이름 접기, 병합 가드, frontmatter, 검색 합산 | 대조, 문턱, 경로·출처 값, 어휘, 재작성 guard, 검색 |
| 저장 구조 | PostgreSQL 표 5개 + 불변 bundle 디렉터리 | 종류별 md + 엣지 JSONL 두 파일 | 파일(진실) + SQLite 한 파일(색인) | vault 안 md + `index.md`·`log.md` |
| 근거 단위 | claim마다 원문 문자 구간 | 논문 한 편 | 원문 문서 + summary 안 구절 | 페이지 + 원문 인용 문장 |

셋째 표는 기능의 성격이다. 기제는 #기능 지도에 있다.

| 항목 | jonex | AutoSci | sage-wiki | gd4ai |
|---|---|---|---|---|
| 같은 대상 판정 | 규칙 먼저, 미정만 상한 있는 LLM, 의심되면 떼어 둠 | 결정적 점수 + LLM, 의심되면 합침 | 이름 임베딩 + 결정적 가드, LLM 판정은 opt-in | 결정적 대조 + 좁은 창 LLM + 별칭 학습 |
| 연결 | LLM은 이름만, 코드가 유일할 때만 건다 | LLM이 타입 엣지, 도구가 schema로 거부 | LLM 링크 + 코드의 공유 출처·키워드 링크 | LLM 이름 → 코드 해석, 관계 타입 없음 |
| 조회 | 에이전트 도구 탐색 + BM25 | LLM이 index를 읽고 고름 | BM25·vector·graph를 RRF로 합산 | 글자 매칭 + 링크 그래프 PPR |
| 사람 개입 | 설정 수준뿐 | 비싼 일 앞 게이트, 제안 승인 | opt-in 검토 큐 셋 | lint·schema 묶음 승인, 페이지 잠금 |

## 큰 구조와 한 바퀴

레포마다 구조 그림, 구성 요소 표, 넣기부터 묻기까지의 한 바퀴를 둔다. 구성 요소 표의 출처는 그 레포 보고서 #큰 구조의 구성 요소 표이고, 단계 칸의 출처는 그 레포 보고서 #한 바퀴 흐름이 든 `path:line`이다.

### jonex

```
플랫폼 업로드 → MinerU 파싱 → 30초 순찰이 KB 단위로 묶어 넘김
        ▼
[jonex-wiki 프로세스 하나, 단일 인스턴스]
  source_prep   체검·passage 패킹                        [코드]
  이해          passage → 원문 발췌 사실                  [LLM]
  evidence gate 문자 구간 고정·지지 판정 → 사실 장부       [코드]
  배치          규칙으로 페이지 결정, 미정만 제한 LLM      [코드 + LLM]
  발행 꼬리     링크·렌더·색인 → versions/{sha} + symlink [코드]
  query         index 강제 읽기 → 도구 탐색 → 인용 복원    [코드 + LLM]
저장: PostgreSQL 표 5개 + 파일 시스템의 불변 bundle
```

| 구성 요소 | 맡는 일 |
|---|---|
| 입력 채널·순찰 | 웹 업로드·MCP·데이터 소스가 `upload_document`로 합류하고, 순찰이 `stale` 문서를 KB 단위로 묶어 넘긴다 |
| source_prep | 파싱 결과를 블록과 passage로 바꾸고, 패킹에 안 들어가는 단위를 체검한다 |
| 이해 | passage에서 원문 발췌 사실을 뽑고 checkpoint로 캐시한다 |
| 배치·동일성 | 사실을 페이지에 놓고 같은 대상인지 판정한다 |
| evidence gate·사실 장부 | 발췌의 문자 구간을 고정해 지지 판정하고, 페이지와 떨어진 사실 기록에서 출처별로 철회한다 |
| Error Book | 문제를 기록하고 등급을 매기고 수리한다 |
| 링크·렌더·발행 | 이름 제안을 페이지로 풀고, Markdown·index를 만들고, 불변 bundle을 원자 발행한다 |
| query·reading·outline | 탐색 루프·검색·인용 복원, 페이지 읽기, 목차 초안과 사람 수정 보호 |

| # | 단계 | 누가 | 출처 |
|---|---|---|---|
| 1 | 파싱 뒤 문서를 `stale`로만 표시하고, 업로드가 조용해지면 KB의 문서를 한 번에 엔진에 넘긴다 | [코드] | `KB/reconciliation_service.py:3072-3137` |
| 2 | 패킹에 안 들어가는 단위만 격리·보관하고 블록을 passage로 묶는다. 입력이 그대로면 이전 발행본을 재사용한다(호출 0회) | [코드] | `SP/chunking.py:35-49`, `C/engine.py:494-540` |
| 3 | passage와 그 메타만 보고 원문 그대로의 발췌·이름·별칭·관계를 낸다. checkpoint가 맞으면 부르지 않는다 | [LLM] | `C/understanding.py:933-1053` |
| 4 | 모델이 준 id를 지우고, 발췌 위치를 찾아 문자 구간을 고정하고, 지지 판정을 거쳐 사실 장부에 넣는다 | [코드] | `C/understanding.py:545-777` |
| 5 | 대표 이름과 규칙으로 페이지를 정하고, 규칙이 못 정한 정체 판정만 제한된 LLM에 묻는다 | [코드 + 조건부 LLM] | `C/organization.py:499-538, 620-657` |
| 6 | 링크·렌더·색인을 만들고, 페이지 급감 관문을 지나면 symlink 교체로 원자 발행한다 | [코드] | `C/engine.py:779-1116`, `JW/domain/compile_task.py:147-212` |
| 7 | 조회는 발행본 버전을 고정하고, 정규식으로 갈래를 정하고, `index.md`를 먼저 읽힌다 | [코드] | `Q/router.py:46-120`, `Q/algorithm.py:1827-1850` |
| 8 | 모델이 도구로 탐색하고 근거 handle로 답을 쓰면, 코드가 handle을 원문 근거로 되살리고 모르는 handle은 버린다 | [LLM → 코드] | `Q/synthesis_orchestration.py:719-757, 945-1105` |

### AutoSci

```
i18n/{en,zh}/ 원본 ──setup.sh 복사──▶ CLAUDE.md, .claude/skills/<skill>/SKILL.md
사용자 /skill 호출 → 주 LLM이 단계를 따라감
  ├ Read/Write/Edit ─────────▶ wiki/<kind>/<slug>.md, index.md   (LLM이 직접 씀)
  ├ Bash: tools/research_wiki.py ─▶ graph/edges.jsonl, citations.jsonl, log.md, 파생물
  │        └ runtime/loader.py ◀── runtime/schema/*.yaml       (검사 상수)
  ├ Bash: tools/lint.py                                      (사후 감사)
  ├ Bash: tools/fetch_*·discover.py                         (외부 수집, LLM 없음)
  ├ Skill: 다른 skill 호출 (/research → /ideate → /exp-* → /paper-*)
  ├ MCP: Review LLM                                          (두 번째 모델의 심사)
  └ Agent: /init 병렬 ingest (git worktree 격리)
tools/serve.py 웹 SPA ── 같은 CLI를 subprocess로 부름
```

| 구성 요소 | 맡는 일 |
|---|---|
| skill 29개 | 단계와 판단. 지식(`ingest`·`init`·`ask`·`check`·`edit`·`discover` 등), 아이디어, 실험, 집필, 운영, 오케스트레이터(`research`)로 나뉜다 |
| 계약층 `runtime/` | 페이지 종류 9개·엣지 16종·역링크 규칙·쓰기 권한 명세를 YAML로 선언하고, loader가 검사 상수로 만든다 |
| `tools/research_wiki.py` | slug, 개념 대조, 엣지·인용 쓰기, 상태 전이, log, 파생물 재생성 |
| `tools/lint.py` | 필수 필드·역링크 대칭·그래프 일관성 사후 감사와 결정적 자동 수정 |
| 외부 수집 | 논문 메타·참고문헌·추천 후보를 LLM 없이 모은다(`fetch_s2.py`, `discover.py`, `daily_arxiv.py`) |
| 웹 SPA | 그래프 보기·필드 편집. 쓰기는 skill과 같은 도구 CLI로만 한다(W16) |
| Review LLM | 두 번째 모델로 아이디어·실험·원고를 심사한다 |
| 사이드카·집필·원격 실행 | Hiera 실험 후보 탐색(wiki에 쓰지 않음), LaTeX 원고의 poster 산출, SSH로 GPU 서버 실험 |

| # | 단계 | 누가 | 출처 |
|---|---|---|---|
| 1 | 원문을 `.tex` 하나로 정규화한다. PDF면 LLM이 제목을 읽고 도구가 합성 tex로 바꾼다 | [코드 + LLM] | `ingest/SKILL.md:96-103` |
| 2 | 도구가 결정적 slug를 만들고, 같은 slug 페이지가 있으면 LLM이 같은 논문인지 보고 멈춘다 | [코드 + LLM] | `tools/research_wiki.py:105-129`, `ingest/SKILL.md:113` |
| 3 | LLM이 schema와 템플릿을 열고 논문 페이지를 Write로 직접 쓴다 | [LLM] | `ingest/SKILL.md:131-148` |
| 4 | 개념 후보마다 도구가 기존 개념과의 대조 점수를 내고, LLM이 점수 구간에 따라 병합·생성을 고른다 | [코드 → LLM] | `tools/research_wiki.py:1090-1118`, `ingest/references/dedup-policy.md:33-38` |
| 5 | LLM이 `add-edge`를 부르면 도구가 종류·끝점·근거 누락을 거부한다 | [LLM → 코드] | `tools/research_wiki.py:275-307` |
| 6 | LLM이 역링크와 index 한 줄을 직접 쓴다 | [LLM] | `ingest/SKILL.md:183-190` |
| 7 | 도구가 log를 덧붙이고 요약 파일을 통째로 다시 만든다 | [코드] | `ingest/SKILL.md:192-203` |
| 8 | `/ask`에서 LLM이 index와 요약 파일을 읽고 15쪽 이하를 골라 `[[slug]]`로 인용해 답한다 | [LLM] | `ask/SKILL.md:65-94` |

### sage-wiki

```
표면   CLI · MCP · /v1 REST · web UI · TUI · pkg/engine
         ├ /v1·serve REST → MCP tool 레지스트리(19개)
         └ CLI·web·TUI → 엔진 함수 직접
엔진   compiler(Pass 0~4, tier, compile key)  search(3갈래 RRF)  trust(답 격리)  linter(8 pass)
저장   store seam → SQLite(FTS5 + BLOB 벡터 + 그래프 + 큐) | Postgres(선택)
파일   raw/ (사람 소유)  wiki/{summaries,concepts,communities,outputs,under_review}/  .manifest.json
```

| 구성 요소 | 맡는 일 |
|---|---|
| 컴파일 진입 | diff → skip 분류 → tier → 패스 실행 → 꼬리 처리 |
| 패스 본체 | Pass 1 → 2 → 임베딩 dedup → evidence gate → curation(opt-in) → 2b → 3 → 4 |
| 이름 정리 | 잡음 필터, 정규화·별칭 접기, 임베딩 dedup + never-merge, LLM curation |
| 그래프 | triple 추출과 Go 검증, entity resolution, bi-temporal edge |
| 증분 | compile key로 다시 돌 문서를 고른다 |
| 검색·Q&A | graph·FTS·vector 갈래를 RRF로 합치고, 문서 전문으로 답한 뒤 `under_review/`에 격리한다 |
| 표면·저장 seam | MCP와 REST는 tool 레지스트리를 공유하고 web·CLI·TUI는 엔진을 직접 부른다. 저장은 SQLite·Postgres를 같은 인터페이스 뒤에 둔다 |

| # | 단계 | 누가 | 출처 |
|---|---|---|---|
| 1 | `ingest`가 원문을 `raw/`에 복사하고 manifest에 등록한다. 컴파일은 따로 돈다 | [코드] | `internal/wiki/ingest.go:56-243` |
| 2 | 해시와 compile key로 다시 돌 문서만 고르고 tier를 정한다. tier 0은 FTS 색인만, tier 1은 원문 청크 임베딩까지 한다 | [코드·임베딩] | `diff.go:41-153`, `tiers.go:33-74`, `index.go:60-65` |
| 3 | Pass 1이 문서마다 summary를 쓴다. 같은 `source_hash`면 재사용한다 | [LLM] | `summarize.go:203-236` |
| 4 | Pass 2가 summary 20개씩 묶어 concept 이름·별칭을 뽑는다 | [LLM] | `concepts.go:98-138` |
| 5 | 잡음 필터·정규화·별칭 접기 뒤 이름 임베딩 dedup과 never-merge 가드, evidence gate를 지난다 | [코드·임베딩] | `concepts.go:270-471`, `dedup.go:125-239`, `evidence_gate.go:13-28` |
| 6 | Pass 3이 concept마다 원문 절·기존 article·관련 concept으로 본문을 쓰고, frontmatter와 링크 정리는 코드가 한다 | [LLM + 코드] | `write.go:212-286, 465-491` |
| 7 | 끊긴 링크 제거, manifest 저장, CHANGELOG, git commit. 미완료 실행은 manifest와 key를 남기지 않는다 | [코드] | `pipeline.go:497-591` |
| 8 | 조회는 갈래별 검색을 RRF로 합치고 문서 전문으로 답한 뒤, 답을 `under_review/`에 둔다 | [코드 → LLM → 코드] | `internal/search/pipeline.go:98-168`, `internal/query/query.go:309-459, 645-656` |

### gd4ai

```
Obsidian
 └ 플러그인 껍데기 (명령 12개, 오른쪽 패널)
     ├ WikiEngine        ingest 지휘 + 페이지 쓰기 관문 writeFileWithIntent
     │   ├ SourceAnalyzer   LLM 추출 루프
     │   ├ 후보 gate        위치·coverage 문턱                [코드]
     │   ├ PageFactory      경로 결정·생성·병합 + 재작성 guard
     │   └ index·log 생성                                    [코드]
     ├ QueryView         seed 선택 → PPR → 문맥 → 답
     ├ Lint              결정적 스캐너 9종 + LLM 중복 검증·수리
     └ SchemaManager     config.md 절 배달, diff 승인
LLM 계층  Vercel AI SDK 어댑터 4종 + task별 정책·계측
```

| 구성 요소 | 맡는 일 |
|---|---|
| 플러그인 껍데기 | 명령 12개(수집 4·질의·lint·index 재생성·취소·기록 보기·Welcome 재생성·PDF 캐시 비우기·API 키 되돌리기)와 리본 2개 |
| WikiEngine | 문서 하나의 ingest를 지휘한다. 쓰기 관문 `writeFileWithIntent`를 두지만 모든 쓰기가 지나지는 않는다 |
| SourceAnalyzer | 노트 전체를 라운드마다 LLM에 보내 이름 JSON을 모으고, 멈춤·재시도를 한다 |
| 후보 gate | 위치와 coverage로 페이지 후보를 거른다 |
| PageFactory·재작성 guard | 기존 페이지를 찾아 새로 쓰거나 병합하고, 재작성에서 사라진 섹션·남의 문단·H1을 되살린다 |
| Query·Lint | seed 선택과 링크 그래프 PPR로 답하고, 결정적 스캐너 9종과 LLM 중복 검증·수리를 돈다 |
| SchemaManager·LLM 계층 | `config.md` 절을 task마다 배달하고, 어댑터 4종 위에서 task별 정책과 계측을 한다 |

| # | 단계 | 누가 | 출처 |
|---|---|---|---|
| 1 | 빈 본문·확장자·본문 해시 중복을 거른다. PDF는 markdown으로 바꿔 같은 함수에 다시 넣는다 | [코드] | `src/wiki/wiki-engine.ts:584-599, 1032-1043` |
| 2 | 노트 전체를 라운드마다 보내 이름·요약·인용·coverage를 JSON으로 뽑는다. 기존 위키 목록은 넣지 않는다 | [LLM] | `src/wiki/source-analyzer.ts:301-312, 343-757` |
| 3 | 이름을 기존 제목·별칭 slug와 대조하고, 이름만 언급된(`named`) 후보를 뺀다 | [코드] | `src/wiki/source-analyzer.ts:767-779`, `src/core/candidate-gate.ts:384-678` |
| 4 | source 요약 페이지를 쓴다. 해시·경로·인용 출처는 코드가 덮어쓴다 | [LLM + 코드] | `src/wiki/wiki-engine.ts:1743-1935` |
| 5 | 후보마다 slug·별칭을 대조하고, 여러 페이지에 맞으면 LLM이, 아무 데도 안 맞으면 30개 창에서 LLM이 판정하고, 판정된 표기를 별칭에 더한다 | [코드 → LLM] | `src/wiki/page-factory/path-resolution.ts:114-361` |
| 6 | 새 페이지는 생성하고, 있으면 분류 뒤 섹션 보완이나 재작성을 한다. 재작성은 guard가 사라진 섹션과 남의 문단을 되살린다 | [LLM + 코드] | `src/wiki/page-factory/merge-page.ts:159-264`, `src/core/paragraph-provenance.ts:241-251` |
| 7 | index 전체를 다시 만들고 log에 덧붙인다 | [코드] | `src/wiki/wiki-engine.ts:2277-2305` |
| 8 | 조회는 index에서 seed를 고르고(약하면 LLM 키워드) 링크 그래프 PPR로 10쪽을 골라 답한다 | [코드 → LLM] | `src/wiki/query-engine/pipeline/select-seeds.ts:106-161`, `src/core/ppr-cascade.ts:355-583` |

## 기능 지도

첫 표는 페이지를 만드는 기능이다.

| 기능 | jonex | AutoSci | sage-wiki | gd4ai |
|---|---|---|---|---|
| 입력 형식 | MinerU 파싱 결과와 xlsx 원본. 표는 compile 밖 표 도구로(#한 바퀴) | arXiv·tex·pdf만. 비논문은 `/init` 때 한 번(축 4) | PDF·Office·메일·이미지·코드, 외부 파서. UTF-8 아닌 텍스트와 .hwp는 거부(축 4) | md·pdf, MinerU를 설정하면 Office·이미지. 고르기 창은 md·txt·pdf만(축 16) |
| ingest 단위 | passage 하나가 LLM 호출 하나(축 4) | 논문 한 편 통째, 청크 없음(#한 바퀴) | 문서 → summary → 20개 묶음 → concept마다(결정 3, 4) | 노트 전체를 라운드마다, 청크 없음(축 4) |
| 정체 판정 | 명시 id → 관계면 다름 → 선언 별칭 + 같은 context면 같음 → 나머지는 호출당 8건, compile당 8회까지 LLM. 판정을 저장하지 않는다(결정 7) | 점수 ≥ 0.80 병합, 0.40~0.80 LLM이 판단하되 기본 병합, 미만은 한도 안에서 생성. `/ingest`에만 의무(W5) | 이름 임베딩 cosine ≥ 0.85면 병합하되 숫자·초안/최종이 다르면 막음. opt-in으로 전역 LLM curation, 합치지 않고 잇는 resolution(결정 8, 9, 11) | 같은 slug → slug·별칭 키(한 페이지면 병합, 여럿이면 LLM) → 키가 안 맞으면 30개 창 LLM → 판정 표기를 별칭으로. 3글자 미만 라틴 이름은 LLM에 안 묻는다(W6) |
| 근거 | 문자 구간 + 숫자·날짜·부정을 따로 보는 결정적 지지 판정 + 페이지와 떼어 둔 사실 장부(결정 6, 10) | `key_papers` 논문 목록, 엣지 `evidence`는 자유 문자열(축 5) | concept → 문서 `cites`, triple 근거는 summary 안 부분 문자열로 확인(결정 20) | `sources:` + verbatim 인용 2~4개를 코드가 누적, 인용 실재는 lint가 원본과 대조(축 5) |
| 연결 | 모델은 대상 이름만, 이름이 페이지 하나에만 맞으면 연결, 아니면 pending. 관계 5종(결정 9) | 타입 엣지 16종을 도구가 schema로 검사. 역링크는 lint가 채움. `cites`는 외부 ID로(W7, W8) | 본문 `[[x]]`는 LLM, 정리는 코드. 공유 출처 상위 8개와 키워드 근접 edge는 코드(결정 12) | `[[Name]]`을 코드가 제목 → 별칭 순으로 해석. 관련 목록은 같은 문서 안으로 한정(축 6, W14) |
| 증분 | source fingerprint + 이해 checkpoint. 배치는 매번 처음부터(축 4) | 같은 slug면 멈출 뿐, 원문 해시를 보지 않음(축 4) | 파일 해시 + compile key + summary 재사용, `--explain`으로 이유(결정 14) | 본문 해시로 중복만 거름. 재컴파일 없음(축 4) |

둘째 표는 운영 기능이다.

| 기능 | jonex | AutoSci | sage-wiki | gd4ai |
|---|---|---|---|---|
| lint | 별도 명령 없음. compile 안 gate와 Error Book 등급이 대신함(축 7) | 결정적 lint + exit code, 자동 수정 둘. LLM 판단은 권고뿐(축 7) | 결정적 8 pass, 보고만(축 7) | 결정적 스캐너 9종 + LLM 중복 검증과 버튼별 수리(W13) |
| 원문 변경 | 그 출처가 받치던 사실만 철회, 다른 출처가 받치면 남음(결정 10) | 감지 없음(축 8) | compile key가 바뀐 문서만 재컴파일, 답 강등은 `verified` 모드만(축 8) | 해시 drift를 보고만 함(W12) |
| 모순 | 기본 모드에는 검사 없음(축 8) | `/check`의 LLM이 보고만(축 8) | functional 관계는 유효 기간으로 무효화하고 `contradicts`는 늘 사람 검토(축 8) | 인용 실재 + "스스로 주장" 확인을 지난 것만 별도 파일로(W10) |
| 되돌리기 | 불변 bundle + symlink 롤백. 플랫폼 화면에는 없음(결정 12) | git에 맡기지만 기본 `.gitignore`가 페이지를 뺌(W10) | `--unlink`, DB는 파일에서 재구축, S3 mirror(결정 11, 축 10) | Obsidian 휴지통, 사용자 git, schema 백업 3개(축 3) |
| 사람 개입 | compile 선호 문구, 목차 조정, 일시정지. 페이지·정체 승인 없음(축 9) | 실험 배포·reset 앞 게이트, 답 결정화 확인, lint 제안 승인(축 9) | alias 적용·거절·되돌리기, curation drop 허가, Q&A 답 승격(축 9) | 연결 테스트, lint 분류 단위 버튼, schema diff Apply, `reviewed: true` 잠금, 답 Save(축 9) |
| 동시성 | 단일 인스턴스, KB당 queued compile 하나로 합침(결정 18) | worktree 격리 + union merge, 잠금 없음(W10) | 쓰기 프로세스 하나, 일부 표면은 잠금 없음(결정 18) | 전역 잠금 없음(축 10) |
| 멀티유저 | 업로드 묶음 compile과 조회 버전 고정. 업로더는 엔진에 안 감(#엔터프라이즈) | 행위자 기록 없음(#엔터프라이즈) | "single-operator"가 명시한 범위, 팀 가이드는 "Designate one compiler"(결정 18) | 대상 아님, "no shared state"(W1) |
| 권한 | 플랫폼의 KB 단위 RBAC, 문서 단위 없음(#엔터프라이즈) | `writers.yaml`은 명세뿐, 강제하지 않음(W9) | 토큰 하나가 전권, 검색 결과 필터 seam `IncludeDoc`(#엔터프라이즈) | 문서 권한 없음, API 키는 OS keychain(#엔터프라이즈) |

## 공통된 흐름

아래 흐름은 모두 [추정]이고, 개수 칸이 사례 수다.

| 흐름 | jonex | AutoSci | sage-wiki | gd4ai | 개수 |
|---|---|---|---|---|---|
| 신원과 값은 코드가 쓴다 | 모델 id 11개 필드를 지움(#한 바퀴) | slug를 도구가 결정적으로 | LLM frontmatter를 지우고 코드가 씀(결정 13) | 해시·경로·`sources:`는 코드(W8) | 4 |
| 사고·실측 뒤 규칙이 프롬프트에서 코드로 옮겨 감 | "真实事故"(실제 사고)·"实测"(실측)를 근거로 든 결정 6개 | test6 개념 중복 `5f904b1`, worktree 사고 `46cad0d`(W2, W5) | frontmatter 60% 중복 `f4fd525`, #164 cosine 겹침(결정 8, 13) | 목록이 프롬프트의 91%(#482), 모순 9건 중 진짜 2건(W5, W10) | 4 |
| 정체 판정은 결정적 대조가 먼저, LLM은 남은 좁은 경우만 | 규칙 → 미정만 64건 상한(결정 7) | 점수 → 0.40~0.80만 LLM(W5) | 정규화·별칭 접기 → 임베딩 → opt-in LLM(결정 8~11) | slug·별칭 → 30개 창(W6) | 4 |
| 관계는 같음이 아니다 | 관계(선행·모회사 등)면 다름(결정 7) | — | 자동 적용 조건에 "broader 아님"(결정 11) | "a relationship is not sameness"(W6) | 3 |
| 비싸거나 되돌리기 어려운 단계에 상한·opt-in | 정체 판정 compile당 8회(결정 7) | 문서당 새 개념 1~3, 방법 1~2(축 4) | 그래프 패스 opt-in, "an upgrade must not raise anyone's bill unasked"(결정 7) | 호출 크기를 vault 크기와 떼어 냄(W5) | 4 |
| 모든 쓰기를 한 gate로 모으지 못함 | 예외. 쓰기 표면이 compile 엔진 하나(축 1) | 페이지·index는 LLM 직접, `/edit`은 도구를 안 거침(W3) | gate를 건너뛰는 쓰기 경로 다섯(축 2) | 관문을 새는 곳 여덟(축 2) | 3 |
| 작성자를 남기지 않음 | 엔진에 업로더 없음 | log·엣지에 행위자 없음 | 작성자 필드 없음, 결정자는 `user` 문자열뿐 | 작성자 필드 없음 | 4 |
| 새·기존 연결 후보 생성이 비었거나 보고만 함 | 출처 넘는 후보는 정확 일치뿐 | 서로 인용 안 하는 문서 사이 후보 단계 없음 | connections lint는 info 메시지뿐 | "the write path can confirm a name but can never discover one"(W14) | 4 |
| 한국어가 규칙 밖 | 후보·지지 판정 토큰이 한글을 버림 | `[^a-z0-9\s]` 정규화로 한글 이름 점수 0 | summary 앞 1,000바이트 자르기, 영어 반의어, ASCII slug | 교차 언어 중복 정규화가 한글을 지움 | 4 |

출처는 각 행이 가리킨 절과 각 보고서 #엔터프라이즈다.

[추정] 위 다섯 행은 네 레포가 따로 사고를 겪고 같은 쪽으로 옮겨 간 자리라서 가져올 자리이고, 아래 네 행은 넷이 함께 비운 자리라서 우리가 처음부터 설계해야 할 자리다(사례: 앞 다섯 행의 사례 19개, 뒤 네 행의 사례 15개).

[추정] "모든 쓰기를 한 gate로"를 지킨 jonex는 사람이 페이지를 고치는 경로를 아예 두지 않아서 지켰다(사례: 사람 편집 API 없음 jonex 축 1, 1개). 사람이 고치는 경로를 열면 그 경로도 같은 gate를 지나게 설계해야 한다.

## 갈린 곳과 이유

이유 칸의 큰따옴표는 보고서가 옮긴 작성자 원문이다.

### 페이지 본문을 누가 쓰나

| 레포 | 선택 | 이유 |
|---|---|---|
| jonex | 코드. 본문은 gate를 지난 발췌 문장의 글머리표 목록이다 | "No LLM rewrites the page"(결정 5). 대가로 읽기 좋은 문장과 출처를 넘는 요약을 잃었다 |
| AutoSci | LLM이 Write로 직접 쓰고, 엣지·인용·log만 도구를 지난다 | 원문 이유는 없다. 보고서는 자유 서술 본문을 도구 API로 표현하기 어렵다고 추정한다(W3) |
| sage-wiki | 본문은 LLM, frontmatter는 코드 | LLM에게 맡기자 frontmatter가 "~60% of the time" 중복됐다(결정 13) |
| gd4ai | LLM이 쓰되, 분류 뒤 필요할 때만 재작성하고 결정적 guard를 지난다 | "Regeneration is intrinsically lossy for weaker models"(W9) — 약한 모델은 재생성 때마다 세부를 흘린다 |

### 애매하면 합치나 떼어 두나

| 레포 | 선택 | 이유 |
|---|---|---|
| jonex | 떼어 둔다. 증명될 때만 합친다 | "two cities with one name are not one entity"(결정 7) — 이름이 같은 두 도시는 한 대상이 아니다 |
| AutoSci | 합친다 | "Over-merging is cheap to undo … Over-creating is expensive"(W5). 다만 분리 명령과 페이지 이력이 기본 설정에 없어 이 전제가 서지 않는다 |
| sage-wiki | 되돌리기 비용으로 기본값을 정한다 | `--unlink`가 생기자 자동 연결 문턱을 1.0에서 0.85로 되돌렸다. "`--unlink` changed the economics"(결정 11) |
| gd4ai | 1위 후보로 합치되 별칭은 배우지 않는다 | "a new page is the one answer that is certainly wrong"(W6) — 새 페이지는 확실히 틀린 답이다 |

### 근거를 어디까지 좁히나

| 레포 | 선택 | 이유 |
|---|---|---|
| jonex | claim마다 문자 구간과 결정적 판정 | 논문 Algorithm 1을 뼈대로 하고, 판정은 "a small, auditable language"만 증명한다(결정 3, 6). 대가로 2,743개 중 792개만 SUPPORTED였다 |
| AutoSci | 논문 단위 | 원문 이유는 없다. 문장 위치 필드는 paper 브랜치 작업 흐름 엣지에만 선택으로 있다(축 5) |
| sage-wiki | 문서 단위 + summary 구절 | "Pass 2 sees summaries, not source content"(결정 20). 작성자도 "not proposition-level"을 빈 곳으로 인정했다 |
| gd4ai | 페이지 + 원문 인용 문장 | 위키를 원문의 대체가 아닌 "complementary query surface"로 정의했다(W14) |

### 검색에 임베딩을 쓰나

| 레포 | 선택 | 이유 |
|---|---|---|
| jonex | 에이전트 탐색 + BM25. dense는 있지만 기본 꺼짐 | 탐색 첫 행동과 인용 일치를 "code, rather than prompt wording"으로 강제한다(결정 15). dense를 끈 이유는 모른다(jonex #확인하지 못한 것) |
| AutoSci | 검색 도구 없이 LLM이 index를 읽는다 | 원문 이유는 없다(#한 바퀴) |
| sage-wiki | BM25·vector·graph 기본 hybrid | BM25로 미리 거르면 "silently destroys recall for multilingual corpora"(결정 17) |
| gd4ai | 임베딩 없이 링크 그래프 PPR | 사용자가 많이 쓰는 provider에 임베딩 엔드포인트가 없고, 2,000쪽이면 약 12MB 상태를 관리해야 한다. 측정자도 장점은 품질이 아니라 "cost"라고 적었다(W3) |

### 어디서 돌리나

| 레포 | 선택 | 이유 |
|---|---|---|
| jonex | 기업 플랫폼 안 KB 종류 하나, 단일 인스턴스 | "单实例强制"(단일 인스턴스 강제), KB 단위로 묶어 비싼 compile을 한 번만(결정 1, 18) |
| AutoSci | Claude Code 세션 | "Skills are orchestrators", 결정적 일은 tools로(W1) |
| sage-wiki | Go 바이너리 하나 | "The tool should be as boring as grep"(결정 1) |
| gd4ai | Obsidian 플러그인 | "Obsidian is the runtime"(W1) |

### 원문이 바뀌면

| 레포 | 선택 | 이유 |
|---|---|---|
| jonex | 출처 버전으로 사실을 철회한다 | 장부가 페이지와 떨어져 있어 한 페이지를 지워도 사실이 지워지지 않는다(결정 10) |
| AutoSci | 감지하지 않는다 | 메인테이너가 정의 변화가 감지되지 않는다고 인정했다(축 8) |
| sage-wiki | 바뀐 문서만 재컴파일한다 | "identical inputs produce byte-identical artifacts"(결정 14) |
| gd4ai | 보고만 한다 | "a re-ingest is additive, so acting on drift automatically would duplicate content"(W12) — 재ingest가 가산적이라 자동으로 하면 중복만 쌓인다 |

[추정] 갈린 이유는 대부분 실행 자리와 쓰는 사람에서 나왔다. 기업 플랫폼인 jonex는 원자 발행과 문자 구간 근거로, 개인 vault인 gd4ai는 서버·임베딩 없음으로, 연구 세션인 AutoSci는 Claude Code 위 skill로, 개인 도구에서 팀으로 넓힌 sage-wiki는 단일 쓰기 프로세스 + opt-in 확장으로 갔다(사례 4개, 위 #어디서 돌리나 표).

## 엔터프라이즈 조건별 지도

조건은 사용자가 정했다. 작성자마다 같은 대상을 다른 용어로 쓰고, 문서가 형식을 갖추지 않을 때가 있다.
목표 원문은 "어느정도 사람이 하더라도 성능을 보장(raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조)"이다.

각 칸의 출처는 그 레포 보고서 #엔터프라이즈 표의 같은 조건 행이고, 다른 절이면 따로 적는다.

### 용어 불일치

| 레포 | 주는 답 | 빈 곳 |
|---|---|---|
| jonex | 원문 표기와 원문이 선언한 별칭을 따로 기록한다. 관계는 별칭이 아니다. 확신이 없으면 따로 두고 센다 | 후보가 정확 일치뿐이라 "매출"과 "수익"은 판정 후보조차 안 된다. 사람이 넣는 용어집 입구가 없다. 판정을 저장하지 않는다 |
| AutoSci | 개념을 만들기 전 결정적 별칭 대조, 기본 병합, 문서당 생성 한도. 범용어는 foundation 계층으로 뺀다(W5, W6) | 대조 의무가 `/ingest`에만 있다. 별칭 필드는 concepts·foundations에만 있다. 한글 이름은 점수 0, slug는 `untitled`가 된다 |
| sage-wiki | 별칭 접기와 manifest 별칭 영속, 이름 임베딩 dedup + never-merge, 전역 curation. 별칭이 검색 tag에 들어간다. pack으로 부서 workspace마다 같은 어휘를 깐다 | 사람이 쓰는 정식 이름 + 별칭 입구가 없다. 묶음끼리 서로 모른다. never-merge 반의어가 영어뿐이다 |
| gd4ai | 결정적 대조 → 좁은 창 판정 → 별칭 학습. 분류 어휘는 사람 쪽에서만 늘어난다. 이름은 원문 언어로 둔다 | 관계 타입이 없어 "비슷하지만 다른 것"이 별칭으로 뭉개진다. 별칭 충돌 61건 중 손으로 본 12건이 모두 중복이 아니었다. 교차 언어 대조가 한글을 지운다 |

[추정] 사람이 관리하는 정식 이름 + 별칭 목록을 정체 판정 입력으로 받는 레포는 없다. 가장 가까운 것은 jonex 플랫폼의 그래프 길 전용 동의어 묶음과 sage-wiki의 pack이다(사례 2개).

### 형식 없는 문서

| 레포 | 주는 답 | 빈 곳 |
|---|---|---|
| jonex | 패킹에 안 들어가는 단위만 격리하고 원문을 남긴다. passage 단위로 실패를 가둔다. claim이 떨어져도 원문 구간이 근거로 남는다. 표는 격자 저장과 제한 계산으로 다룬다(#한 바퀴) | 표 속 사실이 claim·링크가 되지 않는다. 빈 표·반복 같은 품질 문제는 그대로 들어간다 |
| AutoSci | notes·web 출처 페이지를 "Provisional note"로 표시한다 | 입력이 논문 형식뿐이고 비논문 증분 경로가 없다. PDF 정규화가 본문을 6만 자에서 자른다 |
| sage-wiki | tier 0·1로 원문을 바로 검색한다. Office·메일·이미지를 텍스트로 바꾼다. `type_signals`로 "주간보고"·"회의록" 같은 종류별 요약 틀에 보낸다 | heading이 없거나 15,000자 미만이면 Pass 3이 앞 4,000바이트(한국어 약 1,300자)만 본다. EUC-KR 텍스트와 .hwp를 거부한다. DOCX 작성일을 읽지 않아 파일 mtime이 날짜가 된다 |
| gd4ai | 위치 × coverage로 나열·괄호 속 이름을 거른다. 빈 문서를 거른다. opt-in 이미지 분석이 도표를 텍스트 증거로 바꾼다 | 청크가 없어 1라운드가 실패하면 문서 전체가 실패한다. 파일 이름을 페이지 후보로 더하는 단계를 끌 수 없어 "주간보고" 같은 페이지가 생긴다 |

### 여러 작성자와 권한

| 레포 | 주는 답 | 빈 곳 |
|---|---|---|
| jonex | 업로드 묶음 compile, 원자 발행과 조회 버전 고정. 사실 장부 덕에 보고서 하나가 빠져도 다른 보고서가 받친 사실은 남는다. 플랫폼은 KB 단위 RBAC를 둔다 | 작성자 정보가 엔진에 가지 않는다. 문서 단위 권한이 없다. 사람이 페이지를 고치는 경로가 없다 |
| AutoSci | 공유 파일 append + union merge. SPA와 skill이 같은 CLI로 엣지를 쓴다 | 행위자 기록이 없고 권한은 명세뿐이다. SPA에 인증이 없다. `/edit`이 대조·검사·기록을 모두 건너뛴다 |
| sage-wiki | 재시도 중복을 막는 Idempotency-Key, `extends:`로 부서 config 상속, 한 사람의 오답이 남의 문맥을 오염시키지 않게 답을 격리, 검색 필터 seam | 다중 사용자 권한이 명시한 비목표다. 토큰 하나가 전권이다. 사람이 고친 article을 다음 컴파일이 덮어쓴다(축 9) |
| gd4ai | 주제를 정의한 "주 문서"가 본문을 주도한다. 각주 규칙을 정하면 남의 문단이 재작성에서 복원된다. 모순은 별도 파일로 남는다 | 작성자 필드, 문서 권한, 승인자, 전역 잠금이 없다 |

[추정] "누가 이 주장을 했나"를 사실 단위로 붙일 자리는 jonex 사실 장부가 가장 가깝다. 장부 레코드가 출처 버전과 위치를 이미 품고 있어서 작성자 필드 하나를 더하면 된다(사례: 장부 신원 `C/source_contribution.py:70-89`, 업로더가 플랫폼에만 남음 jonex #엔터프라이즈, 2개).

### 원문 링크와 기준별 조각 임베딩

사용자 설계 판단 원문은 "원문을 링크하되 임베딩할 것들은 원문을 주제별이나 어떤 기준으로 나눠서 임베딩을 진행하는 것이 적절하다고 봐. 다만 이것을 어떤 기준으로 나눌지는 추가적인 논문을 통해 여러 방법을 고려해보고 테스트해볼 필요가 있어."(2026-10-11)이다.
아래 표는 네 레포가 원문을 어디까지 가리키고, 무엇을 기준으로 나누고, 무엇을 임베딩하는지다.

| 레포 | 원문 링크 | 나누는 기준 | 임베딩 |
|---|---|---|---|
| jonex | 출처 해시 + `start_char`·`end_char` 문자 구간(결정 6) | 파싱 구조 블록을 약 4,000 token으로 패킹. 이것은 LLM 입력 단위다. 표는 따로 둔다(#한 바퀴) | dense 색인은 있지만 기본 꺼짐(축 11) |
| AutoSci | 논문 단위(축 5) | 없음. 논문 통째 | 없음 |
| sage-wiki | 원문 경로 `src:<path>`. 청크 offset을 채우지 않아 문서 안 위치는 못 가리킨다(축 5) | tier 1 원문 청크(기준은 보고서에 없다. `internal/extract/extract.go:133-191`에서 확인할 것). Pass 3은 15,000 rune 이상이고 heading이 있는 문서만 heading 절로 나눈다(#한 바퀴) | 청크 vector와 문서 vector를 함께 RRF, concept 이름 임베딩으로 dedup(결정 8, 17) |
| gd4ai | 인용의 `source_path` + verbatim 문장(축 5) | 없음. 조회 때 페이지의 Description 절만 잘라 쓴다(#한 바퀴) | 없음. 53쪽 합성 fixture에서 R@5는 PPR 27.1%, bge-m3 kNN 24.1%였고, 실제 vault 링크 예측 MRR은 kNN 0.172, PPR 0.088이었다(W3) |

[추정] 주제로 원문을 나누는 레포는 없다. 있는 기준은 파싱 구조 블록 묶음(jonex), heading 절(sage-wiki), 위키 페이지 절(gd4ai) 셋이다(사례 3개). 이 셋이 주제 기준과 견줄 첫 비교군이 된다.

[추정] 원문 링크를 문자 구간까지 내린 곳은 jonex 하나이고, sage-wiki는 청크를 갖고도 offset을 비웠다(사례 2개). 조각마다 원문 offset을 채우면 "원문 링크"와 "조각 임베딩"이 같은 단위를 나눠 쓴다.

sage-wiki는 같은 문서가 통째로도, 한 구절로도 맞으면 한쪽만 맞는 것보다 위에 둔다: "agreement across granularities … ranks above a single strong hit"(결정 17).
[추정] 조각과 문서를 함께 임베딩할 이유가 된다(사례: sage-wiki 결정 17, 1개).

gd4ai의 측정에 쓴 bge-m3는 사용자 로컬 Ollama에도 있어서, 같은 비교를 사내 문서로 다시 잴 수 있다.

### 낮은 모델

사용자 조건 원문은 "낮은 모델로 해야 돼."다. 레포 사실은 보고서에서 왔고, 어느 레포도 사용자 로컬 모델로 돌려 보지 않았다.

| 레포 | LLM 부담을 줄이는 장치 | 작은 모델에서 걸릴 자리 |
|---|---|---|
| jonex | 호출 하나에 passage 하나, 일은 발췌 고르기 하나. 지지·정체 규칙은 코드. 미정 판정은 case 8개·후보 4개 이하. compile 호출은 thinking을 끈다(축 2, 결정 7) | 조회가 도구 24회·360,000 token·180초까지 도는 에이전트 루프다(#한 바퀴 query). 지지 판정 규칙이 영어·중국어용이다(결정 6) |
| AutoSci | 개념 대조 점수, 엣지 검사, 파생물 재생성이 LLM 없이 돈다(W1, W11) | 실행기가 Claude Code 세션이고 skill 문서가 1만 줄이다. 페이지를 LLM이 직접 쓴다(#한눈에, W3) |
| sage-wiki | pass마다 모델을 따로 골라 원문이 닿는 summarize·extract를 로컬 모델로 돌릴 수 있다(`docs/guides/local-models.md:1-15`). schema에 enum을 걸지 않아 잘못된 값 하나는 노드 하나만 잃는다(결정 6). 품질 점수에 LLM이 없다(결정 21) | Pass 3 원문 맥락 예산이 100k token이다. Pass 2는 summary 20개를 한 호출에 묶는다(결정 3, 4) |
| gd4ai | 호출 크기가 vault 크기와 무관하다(W5). 모델은 coverage만 보고하고 문턱은 코드다(W7). 30개 창에서는 동의어 대상을 9번 중 9번 찾았고 긴 목록에서는 18번 중 0번 찾았다(W6). 구조화 출력을 400 오류마다 한 단계씩 낮추고 (baseURL, model) 쌍으로 기억한다(W15). 반복 루프·잘림을 감지해 재시도한다(축 4). ollama·lmstudio를 키 없이 붙인다 | 노트 전체를 매 라운드 보낸다(축 4). 작성자 스스로 약한 모델의 재생성이 세부를 흘린다고 적었다(W9) |

[추정] 작은 모델의 짐을 가장 많이 덜어 낸 설계는 두 가지다. 하나는 모델에게 관찰만 묻고 결정은 코드 상수로 두는 것이고, 다른 하나는 후보를 좁힌 뒤에 묻는 것이다(사례: gd4ai coverage 문턱과 30개 창, jonex 발췌 고르기와 8×4 판정, 4개).

[추정] 반대로 LLM이 도구를 오래 부르는 에이전트 루프나 페이지 전체를 직접 쓰는 단계가 작은 모델에 가장 무겁다(사례: jonex 조회 루프, AutoSci 페이지 쓰기, gd4ai 재작성, 3개).

모르는 것: exaone3.5:2.4b, gemma4:e2b-it-qat, llama3.1:8b가 각 단계의 구조화 출력과 문맥 길이를 버티는지. 같은 사내 문서를 단계별로 넣어 보면 안다. 참고로 gd4ai는 한 게이트웨이 안에서도 모델마다 grammar 제약 출력이 달랐다고 적는다(`src/llm-sdk/output-mode-prober.ts:42-52`).

### 새 문서와 기존 문서의 연결 발견

사용자 목표의 뒤 절반이다. 네 레포 모두 이 자리를 열린 문제로 남겼다.

| 레포 | 새 문서가 기존 문서에 닿는 길 | 빈 곳 |
|---|---|---|
| jonex | 같은 출처는 자기 페이지를 이어 쓰고, 선언 별칭 + 같은 context면 기존 페이지에 붙는다 | 출처를 넘는 후보가 정확 일치뿐이다. 링크는 이름이 유일할 때만 걸려서, 같은 대상이 출처별로 갈라질수록 링크가 끊길 수 있다 |
| AutoSci | 개념 대조, 태그 → topic, S2 인용 목록 안에서 고른 의미 엣지 | 서로 인용하지 않는 문서 사이 후보 단계가 없다. wiki를 상대로 BM25 점수를 내는 코드가 외부 논문 선별에만 쓰인다 |
| sage-wiki | 기존 이름 스냅샷·별칭·임베딩 dedup·resolution, 질의 때 graph 갈래와 공유 출처 신호 | vector는 비슷한데 edge가 없는 쌍을 lint가 info로 낼 뿐, 검토 큐나 자동 연결로 잇지 않는다 |
| gd4ai | 이름이 기존 제목·별칭과 같을 때 `sources:` 덧붙임, 질의 때 PPR 확산 | edge 95%가 같은 노트 출신 페이지끼리다. 단순 co-citation은 교차 recall을 34% 낮춰 기각됐다(W14) |

[추정] 연결 후보를 낼 부품은 네 레포에 하나씩 있지만 어느 것도 검토 대기열에 이어지지 않았다(사례: jonex의 부르는 곳 없는 퍼지 후보 함수 `C/identity.py:143-162`, AutoSci `tools/discover.py:562-677` BM25, sage-wiki connections lint `internal/linter/passes.go:224-292`, gd4ai 30개 후보 창, 4개).

[추정] 네 레포의 빈자리를 메우려면 후보 생성 → 판정 → 판정 저장을 ingest 안에 두는 안이 가장 가깝다(사례: 위 표 4개). 이 안은 `curriculum.md` 7단원의 결정 E14(새·기존 연결 후보 생성)로 시험한다.

## 차용 지도

라이선스가 가져오는 방식을 먼저 정한다.

| 레포 | 라이선스 | 가져오는 방식 |
|---|---|---|
| jonex | 수정 Apache-2.0 | 설계만 참고해 다시 쓴다. 코드를 옮기면 다중 테넌트 서면 허가 조항이 따라오고, 부서별 workspace가 그 "multi-tenant"에 드는지는 소유자에게 물어야 안다(jonex #한눈에) |
| AutoSci | MIT | 고지를 남기고 코드째 가져온다. 테스트가 없어 새로 써야 한다(축 16). paper 브랜치도 MIT다 |
| sage-wiki | MIT | 코드째 가져온다. eval 일부와 HNSW 사본은 라이선스가 다르다(#한눈에) |
| gd4ai | Apache-2.0 | LICENSE·NOTICE를 함께 두고 바꾼 파일에 표시한다(#한눈에) |

아래 부분마다 앞선 비교 문서의 결정 번호를 붙인다. 앞선 결정 12개 가운데 정체 판정을 다룬 것은 없어서, 정체 판정은 이번에 새로 연 결정이다.

### ingest

앞선 결정: D1 원문이 바뀌는가, D2 LLM에게 파일 쓰기를 맡기는가, D12 실행 형태와 연산당 비용 상한.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 추출 호출에 기존 위키를 넣지 않고, 연결은 추출 뒤 코드로 | gd4ai `src/wiki/source-analyzer.ts:301-312`(W5) | 같은 대상이 다른 표기로 나오므로 정체 판정이 받아 줘야 한다 |
| 원문 읽기와 페이지 배치를 떼고, 읽기 캐시 key에서 배치를 뺀다 | jonex `C/understanding.py:115-117, 399-459`(결정 4) | 설계만. jonex는 사용자 프롬프트를 key에 넣어 용어 규칙을 바꾸면 읽기를 다시 한다. 용어 규칙은 배치 단계 입력으로 둔다 |
| 패킹에 안 들어가는 단위만 격리하고 원문은 보관 | jonex `SP/inspect.py:3-15`(결정 14) | 설계만 |
| evidence gate를 LLM 호출 전에 | sage-wiki `evidence_gate.go:13-28`(결정 10) | 다중 작성자에서는 "출처 2개 이상"으로 올려 쓸 수 있다 |
| tier(색인만 ↔ 전체 컴파일)와 compile key | sage-wiki `tiers.go:79-111`, `compilekey.go`(결정 14, 15) | 질의 적중으로 승격하는 장치는 아이디어만. 적중 집계가 tier 0·1 문서에 쌓이지 않는다는 추정이 있다 |
| 문서 종류 신호 + 종류별 요약 프롬프트 | sage-wiki `summarize.go:263-267`(축 4) | 신호와 프롬프트가 compile key에 들어간다 |
| 모델은 coverage 관찰만, 문턱은 코드 상수 | gd4ai `src/core/candidate-gate.ts:17-21`(W7) | 측정 언어가 독일어뿐이고 한국어 프로필은 추정치다 |

### 정체 판정

앞선 결정: 없음. 이번에 새로 여는 결정이다.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 결정적 대조 → 좁은 창 LLM → 판정 표기를 별칭으로 학습. 모호하면 별칭을 배우지 않고, 짧은 라틴 약어는 LLM에 묻지 않는다 | gd4ai `src/wiki/page-factory/path-resolution.ts:109-361`, `src/wiki/page-factory/aliases.ts:103-118`(W6) | 한글 정규화를 새로 써야 한다 |
| 같음·다름·미정 3값, 관계면 다름, 미정은 따로 두고 센다 | jonex `C/identity.py:99-132`(결정 7) | 설계만. 판정 결과를 저장해 다음 compile이 다시 묻지 않게 바꾼다 |
| never-merge 가드를 유사도 판단 아래에 | sage-wiki `dedup.go:169-239`(결정 8) | 한국어 반의어·차수 규칙으로 다시 쓴다 |
| 합치지 않고 잇기 + `--unlink` + 거절 전이 차단. canonical과 자동 적용은 코드가 정한다 | sage-wiki `internal/ontology/aliases.go:252-270`, `resolve_entities.go:240-345, 1285-1334`(결정 11) | 결정자 필드를 사람 신원으로 바꾼다 |
| 생성 직전 결정적 별칭 대조, 범용어 terminal 계층 | AutoSci `tools/research_wiki.py:956-1118`, `runtime/schema/entities.yaml:171-183`(W5, W6) | "기본 병합"은 분리 도구와 이력이 함께 있을 때만 싸다 |
| 전역 curation(합침은 자동, 지움은 허가제) | sage-wiki `curate.go`(결정 9) | 승인 대기열은 덧붙여야 한다 |

### 근거 장부

앞선 결정: D5 근거를 어떤 단위로 추적하는가, D6 메타데이터를 어디에 어떤 형식으로 두는가.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 사실 장부를 진실로 두고 페이지는 투영. 장부 신원에 페이지 경로를 넣지 않는다 | jonex `C/source_contribution.py:3-6, 70-89, 384-508`(결정 10) | 설계만. 작성자 필드를 더한다 |
| 문자 구간 + 숫자·날짜·부정을 따로 보는 지지 판정 | jonex `M/claim.py`(결정 6) | 설계만. 한국어 토큰·부정·날짜 규칙을 새로 쓴다. 바꿔 말한 사실은 판정 밖으로 빠진다 |
| 모델이 낸 id를 지우고 코드가 신원을 매긴다 | jonex `C/understanding.py:545-575`(결정 9) | 설계만 |
| 코드가 아는 값(경로·해시·출처·날짜)은 모델에게 묻지 않는다 | gd4ai `src/wiki/page-factory/create-page.ts:298-307`(W8) | 대화 저장 경로에는 아직 안 닿았다(W17) |
| 근거 구절의 부분 문자열 검증 | sage-wiki `extract_triples.go:905-952`(결정 20) | 대상을 summary에서 원문 조각으로 바꿔야 원문 추적이 된다 |
| 인용 근거 스캐너(원본 노트와 literal 대조) | gd4ai `src/wiki/lint/scanners.ts:287-388`(#가져올 것) | drift 해시가 페이지당 하나라 출처마다 해시를 따로 둬야 한다 |

### 연결

앞선 결정: D11 Link를 누가 걸고 타입을 붙이는가.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 결정적 키(문서 번호·티켓) 연결과 LLM 의미 연결을 다른 파일로. 의미 엣지에 confidence·evidence 필수 | AutoSci `runtime/schema/edges.yaml`, `tools/research_wiki.py:379-550`(W7) | 의미 후보를 서지에서만 뽑으면 인용 없는 보고서끼리 안 이어진다 |
| 엣지 schema를 YAML로 두고 쓰기 직전 거부 | AutoSci `runtime/loader.py:165-220`(W3, W4) | 페이지 쓰기에도 같은 관문을 둔다 |
| 모델은 대상 이름만 제안하고 링크는 코드가 건다 | jonex `C/relation_increment.py:3-5`(결정 9) | 설계만. "유일할 때만 건다"는 규칙은 가져오지 않는다 |
| 관련 후보를 공유 출처로 고른다 | sage-wiki `write.go:775-786`(결정 12) | 임베딩 없이 첫 컴파일에서도 돈다 |
| 중복 병합 때 전체 링크를 재지정하고 옛 이름을 별칭으로 | gd4ai `src/wiki/lint/merge-duplicates.ts:42-75`, `src/core/link-retarget.ts`(#가져올 것) | 재작성 guard를 이 경로에도 건다 |
| vector는 비슷한데 edge가 없는 쌍을 후보로 | sage-wiki `internal/linter/passes.go:224-292`(축 7) | 검토 대기열로 잇는다 |

### 조회

앞선 결정: D10 검색 방식과 답 되저장.

| 후보 | 어디서 | 조건 |
|---|---|---|
| BM25·vector·graph RRF, 갈래별 순위 노출, 승인 안 된 별칭은 순위에서 뺀다 | sage-wiki `internal/search/pipeline.go:98-262`(결정 17) | 한국어 토큰화(조사)를 따로 봐야 한다(sage-wiki #확인하지 못한 것) |
| 읽은 근거만 인용, 모델에게는 handle만 준다 | jonex `Q/controller/evidence_state.py`(결정 15) | 설계만. 에이전트 루프는 작은 모델에 무겁다(이 문서 #낮은 모델) |
| 답 격리 + 모든 검색 표면에 같은 신뢰 술어 | sage-wiki `internal/trust/`(결정 16) | `verified` 모드를 전제로 한다 |
| 표는 격자로 저장하고 계산 결과에 원 셀을 붙인다 | jonex `Q/table_query.py:1-6`(#한 바퀴) | 설계만 |
| 검색 경로 표시를 답마다 남긴다 | gd4ai `src/wiki/query-engine/pipeline/select-seeds.ts:12-20`(축 11) | 못 찾으면 일반 지식으로 답하는 기본값은 가져오지 않는다 |
| 답 결정화(기본 꺼짐, 확인 뒤 저장) | AutoSci `ask/SKILL.md:96-148`(W14) | 저장 대상도 schema 안에 넣는다 |

### 발행과 되돌리기

앞선 결정: D3 이력과 되돌리기를 git에 맡기는가, D9 lint를 어디까지 결정적으로, gate로 쓰는가.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 불변 bundle + symlink 원자 발행 + 조회 버전 고정 + 0페이지·50% 급감 관문 | jonex `JW/storage/layout.py:119-162`, `JW/domain/compile_task.py:147-186`(결정 12, 13) | 설계만. 롤백을 운영 화면까지 잇는다 |
| 미완료 실행은 manifest와 key를 남기지 않는다 | sage-wiki `pipeline.go:1206-1213`(결정 14) | 이미 쓴 파일은 남으므로 다음 실행이 같은 내용으로 덮어야 한다 |
| 쓴 뒤 완료 도장, 시작 점검이 미완 페이지를 치운다 | gd4ai `src/wiki/wiki-engine.ts:1971-2063`(축 4) | 없음 |
| 재작성 guard(섹션·소유 문단·H1 복원)와 잘린 출력 거부 | gd4ai `src/core/paragraph-provenance.ts:241-251`(W9) | 문단 복원은 각주 규칙이 있을 때만 돈다 |

### 거버넌스

앞선 결정: D4 사람은 어디서 승인하는가, D7 낡음과 모순을 어떻게 다루는가.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 문제 등급(발행을 막을 것, 인용에서 뺄 것, 기록만 할 것) | jonex `C/error_book.py:71-138`(결정 11) | 설계만 |
| 승인 = 내용 digest 고정 + 실행 전 재검사 | AutoSci `tools/hiera/contract.py:231, 242-248`(축 9) | 본체가 아니라 사이드카 Hiera의 장치다 |
| 쓰기 관문 PASS/WARN/BLOCK + 격리 폴더 + 판정 이벤트 로그 | AutoSci paper 브랜치 `tools/trust_guard.py`(#가져올 것) | 쓴 뒤 검사라서 쓰기 전으로 옮긴다 |
| schema 변경 = diff 미리보기 + 전체 적용 + 자동 백업 | gd4ai `src/schema/apply-suggestion.ts:55-99`(W11) | 승인 단위가 본문 전체라 항목별 승인이 안 된다 |
| 쓰기마다 거칠 검사를 기본값 없이 선언 | gd4ai `src/types.ts:1072-1235`(축 2) | 선언했어도 새는 경로가 여덟이다 |
| 분류 어휘는 사람 쪽 세 곳에서만 들어온다 | gd4ai `src/core/vocabulary.ts:45-59`(W8) | 없음 |
| 모순 기록 전 인용 실재 + "스스로 주장" 확인 | gd4ai `src/wiki/page-factory/contradiction-gates.ts:1-240`(W10) | 없음 |
| 실패한 시도를 지우지 않고 이유와 함께 남긴다 | AutoSci `runtime/schema/entities.yaml:78-101`(W12) | 상태 전이 표를 호출부와 맞춘다 |
| 검색 결과 권한 필터 seam | sage-wiki `internal/search/run.go:87-91`(#엔터프라이즈) | 그래프 확장·관계 질의는 이 필터를 지나지 않는다 |
| 호출마다 토큰·비용 장부 + 합산 보고 | sage-wiki `internal/llm/usage.go:24-60`(축 14) | 요청자 필드를 더한다 |

### 낮은 모델 운용

앞선 결정: D12 실행 형태와 연산당 비용 상한.

| 후보 | 어디서 | 조건 |
|---|---|---|
| 구조화 출력을 400 오류마다 한 단계씩 낮추고 (baseURL, model) 쌍으로 기억한다. task 라벨마다 출력 모드·thinking을 고정하고 시간을 잰다 | gd4ai `src/llm-sdk/output-mode-prober.ts:1-68`, `src/llm-client-wrapper.ts:173-212`(W15) | 강등 계기는 provider가 돌려준 400이다. 로컬 Ollama에서 강등이 일어나는지는 `curriculum.md` 1단원 실험이 본다 |
| pass마다 모델을 따로 골라 원문이 닿는 summarize·extract만 로컬 모델로 | sage-wiki `docs/guides/local-models.md:1-15`(#엔터프라이즈 데이터 반출 행) | 호출 장부는 이 문서 #거버넌스의 토큰·비용 장부 행과 함께 쓴다 |
| compile 호출은 thinking을 끈다 | jonex `C/understanding.py:960`(축 2) | 설계만 |

### 가져오지 말 것

| 피할 것 | 어디서 |
|---|---|
| 이름이 페이지 하나에만 맞을 때만 링크 걸기 | jonex 결정 9 |
| 관련 목록을 같은 문서 안 이름으로 한정 | gd4ai W14 |
| 이름 임베딩 cosine 하나로 자동 병합. 작성자가 "no threshold can work"를 인정했다 | sage-wiki 결정 8 |
| 권한을 명세로만 두기 | AutoSci W9 |
| 사람 편집 경로를 쓰기 도구·gate 밖에 두기 | AutoSci #엔터프라이즈, sage-wiki 축 9 |
| 바이트 단위 자르기와 영어 전제 정규화 | 네 레포 #엔터프라이즈 |
| 가산적 재ingest만 두고 철회 경로를 두지 않기 | gd4ai W12 |

## 다음에 읽을 것

| 알고 싶은 것 | 갈 곳 |
|---|---|
| 레포 하나의 설계 이유와 이력 | `lab/reports/<repo>.md` #왜 이 구조인가 |
| 16축 세부 | 같은 파일 #축별 분석 |
| 우리 조건에 비춘 가져올 것·피할 것 전체 | 같은 파일 #엔터프라이즈 llm-wiki에 비추어 |
| 보고서도 모르는 것과 알아낼 방법 | 같은 파일 #확인하지 못한 것 |
| 보고서 문장의 원재료 | `lab/notes-raw/<repo>/` |
| 앞선 9개 구현 비교와 결정 12개 | `../llm-wiki-implementations/lab/reports/00-comparison.md` |
| 이해해 나갈 순서와 실험 | 이 폴더의 `curriculum.md`. 진행은 `checklist.md`, 생각은 `my-thinking.md`에 남긴다 |

[추정] 보고서는 sage-wiki → gd4ai → jonex → AutoSci 순으로 읽는 편이 우리 조건에 빠르다. #차용 지도 후보가 이 순서로 많기 때문이다(사례: 후보 수 sage-wiki 15, gd4ai 14, jonex 12, AutoSci 7, 4개 레포).

근거 장부를 먼저 정하고 싶으면 jonex를 맨 앞에 둔다. 근거 장부 후보 여섯 가운데 셋이 jonex에서 왔다(#근거 장부).

# llm-wiki 구현 비교 — 갈림길은 규칙을 프롬프트에서 코드로 얼마나 옮기느냐이고, 옮긴 구현도 모든 쓰기 경로를 한 gate로 모으지 못한 곳에서 샌다

Karpathy의 llm-wiki 패턴을 구현한 저장소 9개와 형식 명세 1개를 같은 16개 축으로 견준다.
이 문서는 설계 공간과 각 선택의 trade-off를 보여 준다.
어느 설계를 고를지는 정하지 않는다.
#내 llm-wiki를 설계할 때 정해야 할 결정들이 결정 순서와 어울리는 조합을 정리한다.

근거 라벨은 이렇게 쓴다.

| 라벨 | 뜻 |
|---|---|
| `[확인]` | repo별 보고서가 코드·문서를 읽고 확인한 사실을 옮겼다. 보고서들도 repo 코드를 실행하지는 않았다. 이 문서가 코드를 직접 다시 연 곳은 #확인하지 못한 것 끝에 적는다. |
| `[추정]` | repo 사이를 견주어 끌어낸 판단이다. 사례가 된 repo와 그 개수를 붙인다. |

다룬 대상과 이 문서에서 쓰는 짧은 이름은 아래와 같다.

| 짧은 이름 | 저장소 | 한 줄 | 보고서 |
|---|---|---|---|
| Astro-Han | Astro-Han/karpathy-llm-wiki | skill 하나와, 숫자·날짜·인용을 원문에서 grep하는 보고용 스크립트 | [보고서](astro-han-karpathy-llm-wiki.md) |
| Ar9av | Ar9av/obsidian-wiki | skill 40개와, 공유 상태 파일만 잠그고 다시 만드는 Python CLI | [보고서](ar9av-obsidian-wiki.md) |
| AgriciDaniel | AgriciDaniel/claude-obsidian | LLM은 초안만 내고, hash로 묶인 transaction 엔진이 vault에 쓴다 | [보고서](agricidaniel-claude-obsidian.md) |
| kfchou | kfchou/wiki-skills | skill 7개와 stdlib 스크립트 4개, git pre-commit hook | [보고서](kfchou-wiki-skills.md) |
| atomicstrata | atomicstrata/llm-wiki-compiler | LLM에게 쓰기 도구를 주지 않고 코드가 모든 페이지를 쓰는 compiler CLI | [보고서](atomicstrata-llm-wiki-compiler.md) |
| openwiki | langchain-ai/openwiki | 주장(Claim)을 원문 줄 범위의 hash에 묶는 코드 wiki 엔진 | [보고서](langchain-ai-openwiki.md) |
| mindbase | frankchu91/mindbase-llm-wiki | MCP 서버와 웹 UI. LLM에게 닫힌 4종 JSON action만 받는다 | [보고서](frankchu91-mindbase-llm-wiki.md) |
| nashsu | nashsu/llm_wiki | Tauri 데스크톱 앱. 파일 감시와 영구 ingest queue로 자율 ingest한다 | [보고서](nashsu-llm-wiki.md) |
| inkeep | inkeep/open-knowledge | markdown IDE 위의 starter pack. 원문 → 잠정 → 확정 3층 | [보고서](inkeep-open-knowledge.md) |
| OKF | GoogleCloudPlatform/knowledge-catalog의 `okf/` | Open Knowledge Format v0.2 형식 명세와 PoC agent. 구현이 아니라 규약이다 | [보고서](okf-spec-and-methodologies.md) |

기준 문서는 넷이다.

| 문서 | 무엇 | 위치 |
|---|---|---|
| Karpathy gist | 원본 idea file. 에이전트에게 붙여 넣어 맞춤 구현하게 하는 패턴 문서 | `lab/sources/karpathy-llm-wiki-gist/llm-wiki.md` |
| frosk1 댓글 | gist 댓글에 달린 비판 7가지와 8번째 항목 staleness | `lab/sources/frosk1-critique-comments.md` |
| rohitg00 v2 gist | confidence 점수, supersession, typed graph, hybrid 검색, hook 자동화를 더한 확장 idea file | `lab/sources/rohitg00-llm-wiki-v2-gist/llm-wiki.md` |
| cablate | raw → atom(주장 하나) → wiki 3층 방법론과 bash 3개. OKF 보고서 안에서 다뤘다 | [OKF 보고서](okf-spec-and-methodologies.md) |

이 문서에서 자주 쓰는 말은 아래 뜻이다.

| 말 | 뜻 |
|---|---|
| gate | 조건을 못 맞추면 쓰기나 commit을 거부하는 코드 검사 |
| 결정적 | LLM을 부르지 않고, 같은 입력이면 같은 결과를 내는 처리 |
| claim ledger | 주장 하나마다 근거 위치를 따로 기록한 장부 파일 |
| drift | 원문이 바뀌어 wiki 내용과 어긋나는 것 |
| supersede | 새 주장이 옛 주장을 대체했다고 지우지 않고 표시하는 것 |
| 쓰기 경로 | LLM 출력이 디스크 파일이 되기까지 거치는 코드 경로 하나. 한 구현에 여럿 있을 수 있다 |
| PoC | proof of concept. 동작을 보이려고 만든 시험 구현 |
| TTY | 사람이 직접 입력하는 터미널. 프로그램은 표준 입출력이 TTY인지 검사할 수 있다 |
| CRDT | 여러 사람이 동시에 고친 내용을 충돌 없이 합치는 자료 구조 |
| hot.md | 다음 세션이 먼저 읽도록 최근 맥락을 짧게 모아 둔 파일(Ar9av, AgriciDaniel, mindbase v1) |
| context pack | atomicstrata가 질문 하나에 맞춰 페이지·원문 줄·이웃 페이지를 모아 주는 근거 묶음 |
| LEDGER | openwiki의 평가 도구. Claim을 supported·stale·invented·unverified로 나눠 센다 |

## 원본이 정한 것과 비워 둔 것

원본은 3계층, 3연산, 특수 파일 둘을 정한다.
나머지는 원문이 스스로 열어 둔다: "This document is intentionally abstract."
[추정] 열어 둔 자리가 곧 구현이 갈라진 자리다 — 사례: 아래 표의 12개 항목이 모두 이 문서의 설계 축 하나 이상으로 이어진다.

| 항목 | 원본이 정한 것 | 비워 둔 것 | 구현이 갈라진 축 |
|---|---|---|---|
| raw 층 | "These are immutable — the LLM reads from them but never modifies them. This is your source of truth." | 불변을 누가 어떻게 지키는가 | 규칙의 위치, 동시성·안전 |
| wiki 층 | LLM이 전부 쓴다. "You never (or rarely) write the wiki yourself" | 디렉터리, 페이지 형식, 메타데이터 | 저장 구조, 포맷 표준 |
| schema | CLAUDE.md나 AGENTS.md를 사람과 LLM이 함께 고친다 | 규칙을 문서에만 둘지 코드로 옮길지 | 규칙의 위치, 실행 형태 |
| ingest | "I prefer to ingest sources one at a time and stay involved". "A single source might touch 10-15 wiki pages." | 증분 추적, 실패 복구, 자동화, 승인 | Ingest, 사람 개입 |
| 근거 | 답은 "synthesizes an answer with citations" | 인용 단위(페이지·문장·줄), 누가 검증하나 | 근거 추적 단위 |
| query | index를 먼저 읽고 페이지로 내려간다. "good answers can be filed back into the wiki as new pages." | 검색 도구, 원문으로 내려가는가, 되저장 조건 | Query·검색 |
| lint | 모순, 낡은 주장, orphan, 빠진 개념, 빠진 상호 참조, 데이터 공백을 LLM에게 점검시킨다 | 결정적 검사와 LLM 검사의 경계, 자동 수정, gate | Lint |
| 모순·낡음 | "noting where new data contradicts old claims" | 표시 형식, 해소 주체, 원문 변경 감지 | stale·모순 처리 |
| index.md | 내용 카탈로그. "The LLM updates it on every ingest." "This works surprisingly well at moderate scale (~100 sources, ~hundreds of pages)" | 결정적 재생성, 규모를 넘을 때 | index·log 관리, Query·검색 |
| log.md | append-only. 항목이 `## [2026-04-02] ingest \| Article Title`처럼 시작한다 | 누가 쓰나, git과의 관계 | index·log 관리 |
| 이력 | "The wiki is just a git repo of markdown files." | git 연동, 되돌리기 | 동시성·안전 |
| 사람 | 팀 용도에 "Possibly with humans in the loop reviewing updates." | 승인 지점과 그 강제 | 사람 개입 |

[추정] 원본이 문장 하나로만 정한 자리에서 구현이 가장 크게 갈렸다 — 사례: raw 불변 규칙 하나를 두고 9개 구현이 세 갈래로 나뉜다. 모든 쓰기 경로에서 코드로 막는 곳이 2개, 한 경로에서만 막는 곳이 3개, 프롬프트로만 지키는 곳이 4개다.

| raw 불변을 지키는 방식 | repo |
|---|---|
| LLM 출력이 닿는 모든 쓰기 경로가 raw를 받지 않는다 | atomicstrata(엔진이 부르는 LLM에 부수효과 있는 도구가 없다), nashsu(ingest 블록은 `wiki/` 아래 경로만 받는다. agent `wiki.write_page`와 API `pages/write`도 `wiki/` 아래 `.md`만 쓴다. agent `shell.exec`는 명령마다 사람 승인을 받는다) |
| 한 경로에서만 코드로 막는다 | openwiki(native worker는 배정된 페이지 한 장만 쓴다. host 실행은 skill 문서뿐이다), mindbase(웹 ops engine의 action 어휘에 source 층 쓰기가 없다. plugin 경로는 Claude Code 본 세션에서 돌고, plugin hook은 SessionStart 하나뿐이다), AgriciDaniel(엔진 경로에서 `.raw/`는 create-only operation이다. host Write/Edit을 막는 hook이 없다) |
| 프롬프트 문장뿐이다 | Astro-Han, Ar9av, kfchou, inkeep |

nashsu의 경로 검사와 mindbase plugin hook은 이 문서가 코드를 다시 열어 확인했다(#확인하지 못한 것 끝의 표).

[확인] Astro-Han은 저장소 스스로 예시 raw 본문을 검사기에 맞게 고쳤다(커밋 9340c1f).

[확인] Astro-Han의 README는 raw가 불변이라는 전제로 source hash를 거절했다.

[추정] 프롬프트로만 지키는 불변 규칙은 그 규칙을 근거로 한 다른 결정까지 흔든다 — 사례 1개: 위 Astro-Han의 hash 거절.

두 반론 문서가 원본의 빈자리를 서로 다르게 채운다.

- frosk1은 wiki를 파생물로 본다. 결론은 "use the wiki to guide and structure answers, but always ground responses in the original documents."다. 비판 7가지는 #frosk1 비판 7가지 × 구현 대응 표에서 한 줄씩 정의한다.
- rohitg00은 기능을 더한다. fact마다 confidence 점수, supersession, forgetting curve, typed graph, BM25+vector+graph 검색, 이벤트 hook을 처방한다.
- [확인] OKF는 rohitg00의 저장형 confidence를 명시적으로 거부한다. 점수가 주관적이고 consumer 사이에 옮길 수 없고 시간이 지나면 낡는다는 이유다.

## 한눈에 표

| repo | 형태 | 규칙 위치 | 근거 단위 | 사람 개입 | Link 방식 | Lint 방식 | 라이선스 | 성숙도 |
|---|---|---|---|---|---|---|---|---|
| Astro-Han | skill 1개 + 보고용 스크립트 | 거의 전부 프롬프트. 검사기는 exit 0 | 페이지 Raw 링크 + 숫자·날짜·인용의 원문 글자 일치 | 자율. 처분만 선언 | LLM이 건다. 추출 없음 | LLM 수정 / 스크립트 보고 / LLM 보고 세 권한 | MIT | 테스트 52개, CI 없음, 7월 이후 정지 |
| Ar9av | skill 40개 + CLI(+선택 MCP) | 내용은 프롬프트, 상태 파일은 CLI. 쓰기 gate 없음 | 페이지 출처 + `^[inferred]` 라벨(검증 없음) | 자율. 리뷰 큐 opt-in | LLM이 걸고 코드가 해석. typed 관계 7종 | 결정적 fail/warn + exit 1, 의미는 LLM | MIT | 테스트 1,115개, CI |
| AgriciDaniel | plugin skill + stdlib 엔진 | 경로·hash·ledger는 엔진. 엔진을 거치라는 건 프롬프트 | claim ledger(위치·bytes만 검증) | plan hash 승인. agent가 스스로 얻는다 | LLM이 쓰고 parser가 검증 | 결정적 10종, 읽기 전용, 선택형 commit gate | MIT | 테스트 534개, CI matrix |
| kfchou | plugin skill 7개 + 스크립트 4개 + hook | 프롬프트 + commit 시점 gate | footnote. text 소스는 줄 범위 필수(대조는 LLM) | ingest 상의, update·merge 건별 승인 | LLM이 쓰고 스크립트가 검증 | 결정적 6종 + cluster subagent, pre-commit 3종 | MIT | 스크립트 614줄, 테스트 676줄, CI 없음 |
| atomicstrata | CLI·SDK + MCP | 코드가 쓰기 독점. 내용 gate는 profile 페이지만 | 문단 줄 범위 `^[file:N-M]`(존재·범위만) | 자율 기본. 리뷰 큐 opt-in, human gate는 TTY | LLM 제안 + 코드 제목 매칭·수리 | 전부 결정적 + 성격 tier. 내용 지지는 LLM 표본 eval | MIT | 테스트 파일 1,352개, CI 4개 |
| openwiki | CLI 엔진 + MCP + skill | 장부는 코드. 본문↔Claim 일치는 프롬프트 | claim ledger. 줄 범위 hash를 코드가 계산 | 자율. CI가 연 PR을 리뷰 | LLM이 쓰고, 깨진 링크에 주석 스탬프 | 독립 lint 없음. 매 run finalize + Claim preflight | MIT | 테스트 파일 241개, CI, 텔레메트리 기본 켜짐 |
| mindbase | MCP + 웹 + plugin | 쓰기 경계는 코드(action 4종). 분량은 프롬프트 | 페이지 `[@path]`. 원문 일치는 lint에만 | 웹 contribute만 action 승인. 나머지 자율 | v2는 LLM이 See also, v1은 결정적 autolinker | 결정적 kind 5종 + LLM kind는 인용 검증 | MIT | 테스트 파일 115개, 기여자 1명, 엔진 2개 공존 |
| nashsu | Tauri 데스크톱 앱 | 프롬프트 + ingest 경로의 쓰기 직전 gate | 페이지 `sources[]` | 자율 + 비동기 review 큐 | LLM이 쓰고 그래프는 코드가 계산 | 결정적 3종 + 전 페이지 LLM 1회 | GPL-3.0 | 테스트 약 2,300건, CI는 build만 |
| inkeep | Electron IDE + MCP 19개 | wiki 규율은 프롬프트, 쓰기 안전은 코드 | 페이지 링크 | 단계별 STOP gate + 공동 편집 | LLM이 쓰고 backlink는 저장마다 결정적 추출 | 기본은 본문 깨진 링크·orphan만 | GPL-3.0 | 테스트 파일 3,067개, v0.85 |
| OKF | 형식 명세 + PoC agent | consumer를 너그럽게 하는 규칙. PoC 코드 강제 4개 | 주장 footnote → `sources[].id`(검사 도구 없음) | `verified`의 `human:` 접두사(인증 없음) | 타입 없는 markdown link | 없음. inkeep이 따로 구현 | Apache-2.0 | 명세 1,006줄, PoC test 39개 |

### repo별 한 바퀴

원본의 세 연산이 repo마다 어떤 순서로 도는지 한 줄씩 줄인다.
각 칸은 repo별 보고서의 #한 바퀴 흐름을 그 보고서 #검증 기록의 정정에 맞춰 줄인 것이다.
`→`는 단계 순서다.
openwiki는 code 모드, mindbase는 웹 UI 경로 기준이다.
OKF 줄은 PoC가 아니라 명세가 처방하는 것을 적는다.

| repo | ingest 한 줄 | query 한 줄 | lint 한 줄 | 보고서 |
|---|---|---|---|---|
| Astro-Han | agent가 원문을 `raw/`에 저장 → 처분 선언 → article 작성(숫자·날짜·인용은 raw에서 grep) → wiki 전체 cascade → index·log 손 갱신 | index 읽기 + wiki full-text 검색 → article 경로로 인용해 답. 쓰지 않는다. archive는 요청 때만 | agent가 링크·index를 고친다 → `check_evidence.py`가 숫자·날짜·인용을 raw와 대조해 보고(exit 0) → 모순·낡음은 agent가 보고만 | [보고서](astro-han-karpathy-llm-wiki.md#한-바퀴-흐름) |
| Ar9av | `cache-check`가 hash로 분류 → LLM이 페이지를 직접 씀(상한 15쪽은 프롬프트) → `cache-update` → `memory sync`가 log·index·hot 재생성 | hot·index 읽기 → `graph-query` 점수 → summary·grep·전문 순으로 올라감 → log 한 줄만 씀 | `lint --json` 결정적 검사 → 모순·낡음은 LLM → `--consolidate`는 사람 확인 | [보고서](ar9av-obsidian-wiki.md#한-바퀴-흐름) |
| AgriciDaniel | `capture`가 원본을 `.raw/`에 create-only 복사 → subagent가 draft → orchestrator가 transaction bundle → `inspect`가 승인 hash 발급 → `apply`가 hash 비교 후 lock·journal로 적용 → 선택 checkpoint commit | hot 읽기 → 검색 index가 검증됐으면 BM25 top-K(rerank 없음), 아니면 index + text 검색 → ledger 평가로 확신 정도 구분. 쓰지 않는다 | `lint_vault()` 결정적 검사 + ledger 검증 → subagent는 해석만 → 사용자가 고른 항목만 `lint-fix` transaction | [보고서](agricidaniel-claude-obsidian.md#한-바퀴-흐름) |
| kfchou | 원문을 `raw/`에 복사 → 핵심을 보여 주고 상의 → LLM이 footnote를 달아 씀 → 모순 gate → `generate-index.py` → 사용자 확인 뒤 commit(pre-commit hook이 staged 내용 검사) | index 재생성 후 전부 읽기 → 페이지와 링크 1단계 → 답 → 저장할지 묻기 | `lint-mechanical.py` JSON → tag cluster마다 subagent → 보고서 페이지를 허락 없이 씀 → 수정은 확인 뒤 | [보고서](kfchou-wiki-skills.md#한-바퀴-흐름) |
| atomicstrata | `ingest`는 원문 변환·저장만(LLM 없음). `compile`이 hash로 변경 분류 → source당 추출 1회 → concept당 생성 1회 → citation 정규화 → review gate → journal 적용 → link·index 결정적 생성 | chunk embedding + BM25 → 없으면 page embedding 후 LLM 선택 → 고른 페이지 전문으로 답. `--save`는 검증 뒤 저장 | 전부 결정적 규칙에 성격 tier. citation은 파일 존재·범위만. 내용 지지는 `eval`의 LLM judge 표본 | [보고서](atomicstrata-llm-wiki-compiler.md#한-바퀴-흐름) |
| openwiki | Claim preflight가 근거 재계산 → 할 일 없으면 모델 0회 → planner 계획 + stale 페이지 job 강제 추가 → 페이지당 worker 1개(그 파일만 씀) → Claim 반영 → finalize | MCP `openwiki_search`가 SQLite FTS5로 섹션 검색 → `openwiki_read`. 모델을 부르지 않는다 | 독립 명령 없음. 매 run의 finalize와 Claim preflight가 결정적 검사 | [보고서](langchain-ai-openwiki.md#한-바퀴-흐름) |
| mindbase | 글을 contributor 파일에 append → LLM 1회로 action 계획 → 코드가 중복 slug 제거·인용 덧붙임 → 사용자가 고른 action만 적용. build는 승인 없이 `context.md` 재작성 | BM25 후보 + 사용자 자료 가중치 → `read_file` loop 최대 3회 → 답 → log 한 줄 | LLM findings의 인용을 원문과 대조 → 코드 findings를 붙여 `artifacts/lint/`에 저장. wiki는 쓰지 않는다 | [보고서](frankchu91-mindbase-llm-wiki.md#한-바퀴-흐름) |
| nashsu | 파일 감시 → 영구 queue → hash cache가 맞으면 건너뜀 → 분석·생성 LLM 호출 → 쓰기 직전 gate(경로·schema·merge) → index·log 코드 갱신 → 완결성 검사 → review 등록. 사람 승인 없음 | agent가 token 점수 + vector RRF + 이웃 1단계로 검색. Faithful 모드는 원문 grep만. Save to Wiki는 답을 저장하고 곧바로 재-ingest | 결정적 3종(orphan·broken-link·no-outlinks) + 전 페이지 앞 500자로 LLM 1회 → 수정은 버튼 | [보고서](nashsu-llm-wiki.md#한-바퀴-흐름) |
| inkeep | agent가 중복 grep → host 도구로 fetch → MCP `write`로 `external-sources/`에 저장 → 서버가 backlink 갱신, 깨진 링크를 응답에 실음 | `search`(BM25)와 읽기 전용 `exec`를 번갈아 → 채팅으로 답. 네 조건을 다 맞을 때만 저장 제안 | `links`·`audit`·`lint` 도구. 기본 설정은 lint plugin이 모두 꺼져 본문 깨진 링크만 본다. 모순은 agent에게 부탁 | [보고서](inkeep-open-knowledge.md#한-바퀴-흐름) |
| OKF | 처방하지 않는다. producer가 사람이든 agent든 export 파이프라인이든 상관없다 | `index.md` 계층을 따라 필요한 만큼 내려가 읽는다(progressive disclosure). 검색 방식은 비목표. 되저장 규칙 없음 | 처방하지 않는다. conformance 필수 조건 3개는 결정적으로 검사할 수 있는 모양이지만 검사기는 없다 | [보고서](okf-spec-and-methodologies.md#한-바퀴-흐름) |

## 설계 축별 스펙트럼

축 16개는 [00-discovery](00-discovery.md)에서 정했다.
번호는 repo별 보고서의 절 번호와 같다.
각 축은 관찰한 선택지, 그 자리의 repo, 얻는 것과 치르는 것 순으로 적는다.

### 1. 실행 형태

선택지는 프롬프트 skill부터 데스크톱 앱까지 다섯 갈래다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| 프롬프트 skill + 보고용 스크립트 | Astro-Han | 의존성 0. 어느 에이전트에서나 돈다 | 강제가 없다 |
| skill + 결정적 CLI·스크립트 | Ar9av, AgriciDaniel, kfchou | 판단은 LLM, 반복 일은 코드로 가른다 | CLI를 부를지 말지가 프롬프트에 달린다 |
| CLI·SDK 엔진(+MCP) | atomicstrata, openwiki | 쓰기 경로를 코드가 쥔다 | 엔진이 크다(171k줄, 61.5k줄). 대화하며 쓰는 원형에서 멀어진다 |
| MCP 서버 + 웹 UI | mindbase | 승인 UI를 붙이기 쉽다 | 표면마다 엔진이 갈렸다 |
| 데스크톱 앱·IDE | nashsu, inkeep | 사용자는 설정만 본다. 감시·공동 편집이 된다 | 앱이나 상시 서버가 있어야 돈다. 둘 다 GPL |

[추정] 쓰기 표면이 여럿인 구현일수록 표면 사이에 규칙이 갈라진다 — 사례 4개: mindbase는 웹과 plugin이 다른 엔진과 다른 디렉터리를 쓴다. nashsu는 ingest만 gate를 지나고 agent·API·답 저장은 지나지 않는다. openwiki는 native 실행만 backend가 쓰기를 막고 host 실행은 skill 문서뿐이다. Ar9av는 서버 `write_page`가 staging 설정을 무시한다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#1-실행-형태) · [Ar9av](ar9av-obsidian-wiki.md#1-실행-형태) · [AgriciDaniel](agricidaniel-claude-obsidian.md#1-실행-형태) · [kfchou](kfchou-wiki-skills.md#1-실행-형태) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#1-실행-형태) · [openwiki](langchain-ai-openwiki.md#1-실행-형태) · [mindbase](frankchu91-mindbase-llm-wiki.md#1-실행-형태) · [nashsu](nashsu-llm-wiki.md#1-실행-형태) · [inkeep](inkeep-open-knowledge.md#1-실행-형태) · [OKF](okf-spec-and-methodologies.md#1-실행-형태)

### 2. 규칙의 위치

한쪽 끝은 "규칙은 프롬프트에만"이고 다른 끝은 "LLM에게 쓰기 수단을 주지 않는다"이다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| 프롬프트 + 사후 보고 | Astro-Han, inkeep | 가볍다. 규칙을 고치기 쉽다 | 위반이 남는다. Astro-Han 검사기는 "The exit code carries no information" |
| 프롬프트 + 사후 lint(exit code) | Ar9av | CI에 묶을 수 있다 | 쓰는 순간은 막지 못한다 |
| 프롬프트 + commit gate | kfchou | git만 있으면 된다 | `--no-verify`, fresh clone, non-git, 기존 repo 안의 하위 디렉터리 wiki에서 꺼진다 |
| 쓰기 직전 gate(한 경로) | nashsu(ingest), mindbase(웹 ops engine), OKF PoC(`type`, concept id 정규식, 축소 금지 guard) | LLM 출력 형식을 코드가 바로잡거나 거부한다 | gate를 거치지 않는 다른 쓰기 경로가 남았다. OKF PoC guard는 web pass에만 걸린다 |
| 엔진 transaction(CLI 층) | AgriciDaniel | 경로·expected hash·ledger를 엔진이 검사한다 | host Write/Edit 직접 쓰기와 라이브러리 직접 호출이 우회한다 |
| LLM에게 쓰기 도구 없음 | atomicstrata, openwiki(native) | LLM 출력이 코드를 거치지 않고 디스크에 닿을 길이 없다 | 엔진이 LLM을 직접 불러야 한다 |

[확인] 프롬프트에서 코드로 옮긴 이유를 코드가 직접 밝힌 곳이 둘이다.
nashsu 주석은 sanitize 이전에 "~45% of generated entity pages went to disk with unparseable frontmatter"였다고 적는다.
atomicstrata 주석은 프롬프트 규칙을 "advisory prompt text, not an enforceable boundary"라고 부르고 "Anything that must hold should be a lint rule or a trust gate"라고 적는다.

[추정] 코드 gate를 둔 구현 가운데 LLM이 쓴 wiki 페이지가 gate를 거치지 않고 디스크에 닿는 길이 없는 곳은 atomicstrata 하나다 — 사례: 아래 5개 구현이 우회 경로를 남겼다.

[확인] atomicstrata도 페이지 밖 파일은 planner 밖에서 쓴다. `index.md`·MOC·`log.md`·`sources/`가 그렇다. 이미지 소스는 LLM vision 출력이 변환본이 되어 `sources/`에 그대로 저장된다.

| repo | gate를 거치지 않는 쓰기 경로 |
|---|---|
| nashsu | agent `wiki.write_page`, API `pages/write`, Save to Wiki, lint 수정 버튼 |
| mindbase | MCP `ingest_source`·`ingest_execute`와 capture worker(ops engine 밖의 v1 compile engine). 웹 build·research·autoSave는 action executor는 지나지만 승인·인용 보정·중복 guard를 건너뛴다 |
| AgriciDaniel | host Write/Edit 직접 쓰기, Python에서 `apply_bundle()` 직접 호출 |
| Ar9av | 서버 `write_page`(staging 무시), skill이 지시하는 manifest 손 편집 |
| openwiki | host 실행(쓰기 제한이 skill 문서뿐) |

[확인] 대신 atomicstrata의 기본 concept 페이지는 경로·크기·frontmatter 파싱 검사만 받는다.

[추정] 쓰기 경로를 하나로 모으는 일과 gate가 내용을 보는 일은 따로 풀어야 한다 — 사례 2개: atomicstrata는 경로는 모았지만 내용 gate가 약하다. nashsu는 내용 gate가 촘촘하지만 경로가 갈렸다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#2-규칙의-위치) · [Ar9av](ar9av-obsidian-wiki.md#2-규칙의-위치) · [AgriciDaniel](agricidaniel-claude-obsidian.md#2-규칙의-위치) · [kfchou](kfchou-wiki-skills.md#2-규칙의-위치) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#2-규칙의-위치) · [openwiki](langchain-ai-openwiki.md#2-규칙의-위치) · [mindbase](frankchu91-mindbase-llm-wiki.md#2-규칙의-위치) · [nashsu](nashsu-llm-wiki.md#2-규칙의-위치) · [inkeep](inkeep-open-knowledge.md#2-규칙의-위치) · [OKF](okf-spec-and-methodologies.md#2-규칙의-위치)

### 3. 저장 구조

갈라지는 것은 셋이다: 디렉터리 분류, 메타데이터를 두는 자리, 파생 상태 파일의 양.

| 하위 선택 | 선택지와 repo |
|---|---|
| 디렉터리 분류 | topic 한 단계(Astro-Han) / 평면 `pages/` + category 필드(kfchou) / entity·concept 등 type 디렉터리(Ar9av 7개, AgriciDaniel, nashsu) / 원문 → 잠정 → 확정 3층(inkeep) / planner가 그때 정함(openwiki) / 합성 문서 `context.md` 한 장 + research 페이지(mindbase v2) / raw → atom → wiki(cablate) |
| 메타데이터 자리 | H1 아래 blockquote(Astro-Han) / YAML frontmatter(대부분) / 페이지 밖 JSON ledger(AgriciDaniel) / 숨김 sidecar `.claims/`(openwiki) / sidecar + sqlite(mindbase v1) / 없음(mindbase v2 research 페이지, cablate wiki 페이지) |
| 파생 상태 파일 | index·log 말고는 없음(Astro-Han, kfchou) / 페이지 밖 `index.yaml`·snapshot 몇 개(mindbase v2) / manifest·ledger·journal 묶음(Ar9av 상태 파일 11종, AgriciDaniel manifest + ledger 2개 + `.vault-meta/` journal·BM25 index, atomicstrata `state.json` + candidates·journal) / sidecar + run state(openwiki) / queue·cache·snapshot 10여 개(nashsu) / backlink cache + shadow git(inkeep) |

| 얻는 것과 치르는 것 | 사례 |
|---|---|
| 상태 파일이 없으면 증분 추적과 실패 복구도 없다 | Astro-Han, kfchou |
| 상태 파일이 많으면 디스크와 어긋날 자리가 는다 | Ar9av는 lock 경로와 손 편집 지시를 함께 둔다. nashsu는 queue JSON이 깨지면 빈 queue로 시작한다 |
| 근거를 페이지 밖 장부에 두면 본문은 깨끗하지만 장부가 무겁다 | openwiki `.claims/` 1.7MB가 본문 0.6MB보다 크다 |
| 합성 문서 한 장은 읽기 쉽지만 개념 페이지가 자라지 않는다 | mindbase는 `context.md` 400줄 상한이 압축을 강제한다. v2 action에 기존 research 페이지 갱신이 없다 |
| 잠정과 확정을 나누면 이른 확정을 막는다 | inkeep `research/`(draft)와 `articles/`(stable) |

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#3-저장-구조) · [Ar9av](ar9av-obsidian-wiki.md#3-저장-구조) · [AgriciDaniel](agricidaniel-claude-obsidian.md#3-저장-구조) · [kfchou](kfchou-wiki-skills.md#3-저장-구조) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#3-저장-구조) · [openwiki](langchain-ai-openwiki.md#3-저장-구조) · [mindbase](frankchu91-mindbase-llm-wiki.md#3-저장-구조) · [nashsu](nashsu-llm-wiki.md#3-저장-구조) · [inkeep](inkeep-open-knowledge.md#3-저장-구조) · [OKF](okf-spec-and-methodologies.md#3-저장-구조)

### 4. Ingest

사람 참여, 증분 판정, 실패 복구, 감시, 소스당 페이지 수가 따로 움직인다.

| 하위 선택 | 선택지와 repo |
|---|---|
| 사람 참여 | 쓰기 전 상의(kfchou 강조점 질문, AgriciDaniel 예산 합의, mindbase 웹 action 선택, inkeep URL마다 지시) / 자율(Astro-Han, Ar9av, atomicstrata, openwiki, nashsu, OKF PoC) |
| 증분 판정 | 없음(Astro-Han·kfchou: raw 불변 전제, inkeep 텍스트 소스, OKF PoC) / LLM이 manifest hash를 보고 판단(AgriciDaniel. 코드는 capture 단계의 같은 digest 복사만 막는다) / 원문 hash를 코드가 비교(Ar9av 5분류, atomicstrata hash + prompt 지침 digest, nashsu md5 snapshot + SHA-256 cache) / git baseline(openwiki) / mtime(mindbase build) |
| 실패 복구 | journal rollback(AgriciDaniel, atomicstrata) / 영구 queue + 생성 checkpoint(nashsu) / 페이지 단위 run state(openwiki) / "wiki가 곧 checkpoint"라는 절차 규칙(inkeep) / 없음(Astro-Han, Ar9av, kfchou, mindbase 계획은 메모리) |
| 자동 감시 | 파일 watcher(nashsu 기본 켜짐, atomicstrata `watch`) / cron·launchd(openwiki) / polling(mindbase RSS·capture) / 없음(나머지) |
| 소스당 페이지 | 원본 10~15 / Ar9av 목표 10·상한 15 / atomicstrata concept 3~8 / inkeep 1~4 / mindbase 새 research 페이지 최대 1 / Astro-Han 상한 없음 |

[확인] 얇은 소스로 억지 페이지를 만들지 않는 정지 경로를 둔 곳은 둘이다: Astro-Han의 No material 처분, AgriciDaniel의 compilation-value gate.

[확인] atomicstrata는 prompt 지침의 digest를 증분 키에 넣는다. 출력 언어나 지침이 바뀌면 같은 원문도 다시 만든다.

| 얻는 것과 치르는 것 | 사례 |
|---|---|
| 소스당 페이지를 줄이면 싸지만 entity·concept 페이지의 누적을 포기한다 | inkeep 1~4쪽 |
| 자동 감시만 남기면 쓰기 전 사람 검토가 없다 | nashsu는 대화형 ingest 진입점 `startIngest`가 호출되지 않는 죽은 코드다. 사람은 끝난 뒤 review 큐에서만 관여한다 |
| mtime 판정은 다른 쓰기와 엇갈린다 | mindbase는 `context.md`에 섹션을 덧붙이면 build 안 된 노트가 반영된 것으로 보일 수 있다 |
| 원문을 자르면 요약 손실이 원문 사본까지 번진다 | atomicstrata는 ingest에서 100k자, compile에서 200k자로 자른다 |

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#4-ingest) · [Ar9av](ar9av-obsidian-wiki.md#4-ingest) · [AgriciDaniel](agricidaniel-claude-obsidian.md#4-ingest) · [kfchou](kfchou-wiki-skills.md#4-ingest) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#4-ingest) · [openwiki](langchain-ai-openwiki.md#4-ingest) · [mindbase](frankchu91-mindbase-llm-wiki.md#4-ingest) · [nashsu](nashsu-llm-wiki.md#4-ingest) · [inkeep](inkeep-open-knowledge.md#4-ingest) · [OKF](okf-spec-and-methodologies.md#4-ingest)

### 5. 근거 추적 단위

네 단계가 있다.
단위가 잘수록 코드가 확인할 수 있는 것이 는다.
어느 단계도 "인용이 문장을 뒷받침하는가"를 쓰기 경로의 코드로 보지 않는다(아래 [추정]).

| 단위 | repo | 코드가 확인하는 것 | 확인하지 못하는 것 |
|---|---|---|---|
| 페이지 단위 출처 | inkeep, nashsu, mindbase, Ar9av, cablate. OKF는 명세가 주장마다 footnote → `sources[].id`를 처방하지만 검사 도구가 없어 실제로는 이 칸이다 | 링크 대상 존재(일부) | 어느 문장이 어느 원문에서 왔나 |
| 페이지 + literal 글자 일치 | Astro-Han(숫자·ISO 날짜·15자 이상 인용), mindbase lint finding | 값이 그 페이지가 가리킨 원문에 글자 그대로 있다 | 맞는 값을 틀린 주장에 붙였는가. 3자리 이하 정수, Status block 안 |
| 줄 범위 | atomicstrata(`^[file:N-M]`), kfchou(text 소스 필수) | 파일 존재, 줄 번호가 파일 길이 안 | 그 줄이 주장을 뒷받침하는가. kfchou의 quote 대조는 LLM 지시다 |
| claim ledger | AgriciDaniel, openwiki | AgriciDaniel: wiki 쪽 anchor와 원문 bytes hash. openwiki: 인용 범위 hash를 코드가 계산하고 바뀌면 stale | 범위·locator가 주장을 뒷받침하는가. 본문과 장부가 일치하는가 |

[추정] 9개 구현 중 쓰기 경로에서 인용과 주장의 의미 관계를 코드로 보는 곳은 없다 — 사례 4개: Astro-Han은 값의 존재만, atomicstrata는 줄 번호 상한만, openwiki는 범위 hash만, AgriciDaniel은 anchor와 bytes만 본다.

[확인] 내용 지지를 보는 장치는 사후 평가에만 있다: atomicstrata `eval --suite full`의 LLM judge 표본, openwiki LEDGER 평가.

| 얻는 것과 치르는 것 | 사례 |
|---|---|
| literal 일치는 싸고 어느 형태에나 붙는다 | Astro-Han 검사기 431줄, 의존성 0 |
| 줄 범위는 원문이 고쳐지면 조용히 어긋난다. 재배치 장치가 필요하다 | openwiki는 앞뒤 3줄 context hash로 범위를 따라간다. 모호하면 unresolved로 둔다 |
| 장부는 무겁고 쓰는 쪽 부담이 크다 | openwiki sidecar가 본문보다 크다. AgriciDaniel은 ledger를 선택으로 둬서 claim 기록 없는 ingest가 통과한다 |
| 라벨 없는 문장의 기본값이 결과를 가른다 | Ar9av는 라벨 없음을 "extracted"로 본다. atomicstrata는 citation 없는 문단을 inferred로 센다 |

[확인] Astro-Han은 줄 번호 인용을 거절했다. 근거는 관찰한 오류가 모두 "value absent from the source"였다는 운영 경험이다. 표본 크기는 밝히지 않았다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#5-근거-추적-단위) · [Ar9av](ar9av-obsidian-wiki.md#5-근거-추적-단위) · [AgriciDaniel](agricidaniel-claude-obsidian.md#5-근거-추적-단위) · [kfchou](kfchou-wiki-skills.md#5-근거-추적-단위) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#5-근거-추적-단위) · [openwiki](langchain-ai-openwiki.md#5-근거-추적-단위) · [mindbase](frankchu91-mindbase-llm-wiki.md#5-근거-추적-단위) · [nashsu](nashsu-llm-wiki.md#5-근거-추적-단위) · [inkeep](inkeep-open-knowledge.md#5-근거-추적-단위) · [OKF](okf-spec-and-methodologies.md#5-근거-추적-단위)

### 6. Link

누가 링크를 거는가와 누가 그래프를 계산하는가가 갈린다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| LLM이 걸고 검사는 LLM | Astro-Han | 의존성 없음 | 깨진 링크 수리도 프롬프트 |
| LLM이 걸고 코드가 해석·검증 | Ar9av, AgriciDaniel, kfchou, openwiki, nashsu, inkeep, mindbase v2(`See also` 줄을 action으로 붙이고 lint가 inbound 수를 센다) | 깨진 링크·orphan이 결정적으로 나온다 | 빠진 링크는 LLM 판단에 남는다 |
| 코드가 직접 링크를 건다 | atomicstrata(제목 매칭 + 수리), mindbase v1(점수 6 이상 자동 기록) | 언급을 놓치지 않는다 | 제목 문자열 일치에 기댄다. atomicstrata는 증분일 때 O(바뀐 수 × 전체) |
| typed 관계 | Ar9av 7종, atomicstrata profile, mindbase v1 sqlite edge | "supersedes"·"contradicts"를 기계가 읽는다 | 타입을 LLM이 붙인다 |
| 타입 없음 | Astro-Han(명시적 거절), OKF | 지어낼 칸이 적다 | 관계 의미가 문장에만 있다 |

[추정] 링크 parser가 둘 이상이면 형식 처리가 갈라진다 — 사례 2개: kfchou는 `wiki-merge`만 link style 설정을 읽지 않는다. OKF는 명세·생성 prompt·viewer가 `/` 절대 경로 링크를 셋 다 다르게 다룬다.

[확인] openwiki code 모드는 깨진 링크에 주석을 달지만, 그 주석을 다음 run의 job으로 넣는 연결이 없다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#6-link) · [Ar9av](ar9av-obsidian-wiki.md#6-link) · [AgriciDaniel](agricidaniel-claude-obsidian.md#6-link) · [kfchou](kfchou-wiki-skills.md#6-link) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#6-link) · [openwiki](langchain-ai-openwiki.md#6-link) · [mindbase](frankchu91-mindbase-llm-wiki.md#6-link) · [nashsu](nashsu-llm-wiki.md#6-link) · [inkeep](inkeep-open-knowledge.md#6-link) · [OKF](okf-spec-and-methodologies.md#6-link)

### 7. Lint

결정적 lint와 LLM lint를 나누는 것은 대부분이 같다. 갈리는 것은 gate 여부, 자동 수정 권한, LLM lint의 입력 예산이다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| 결정적 lint가 거의 없다 | Astro-Han(literal만, exit 0), inkeep 기본(plugin 3개 꺼짐), OKF PoC | 설정이 없다 | 위반을 아무도 막지 않는다 |
| 결정적 + LLM, 보고만 | Ar9av, mindbase, nashsu, kfchou | 사실과 모델 의견이 갈린다 | 보고는 읽히지 않으면 끝이다 |
| 결정적만, 보고만. LLM은 결과 해석이나 사후 eval만 | AgriciDaniel(의미 모순 검사는 하지 않는다고 명시), atomicstrata(내용 지지는 `eval`로 분리) | lint 결과가 재현된다 | 모순·낡은 주장 같은 의미 문제는 lint 밖이다 |
| commit을 막는다 | kfchou pre-commit(구조 3종 + 모순 flag), AgriciDaniel checkpoint(선택, `--skip-lint`), Ar9av·inkeep exit code(사용자가 CI에 묶을 때) | 깨진 상태가 이력에 들어가지 않는다 | 우회 스위치가 있다 |
| 수정 경로 | LLM이 바로 고침(Astro-Han Safe Fixes, Ar9av `--consolidate`) / 사람이 고른 항목만 적용(nashsu 버튼, AgriciDaniel lint-fix transaction, kfchou diff 확인) / 계획만 냄(atomicstrata) | 부채가 줄어든다 | Ar9av consolidate는 "reviewed는 사람만" 규칙과 부딪치는 `draft→reviewed` 자동 승격을 한다 |

빌려 쓸 만한 장치가 여럿 있다.

| 장치 | repo |
|---|---|
| 모델이 결정적 kind를 내면 버리고, 모순 finding은 원문 일치 인용 2개가 있어야 남기고, 버린 수를 log에 남긴다 | mindbase |
| lint 결과마다 deterministic / provider-judgement / derived-view 성격을 단다 | atomicstrata |
| 스크립트가 tag cluster를 만들고 cluster마다 subagent가 본문을 읽는다. recall 한계를 보고서에 적는다 | kfchou |
| `--as-of` 날짜로 결과를 재현한다 | AgriciDaniel |
| safe fix / mechanical report / judgment report 세 권한 | Astro-Han |

[추정] LLM lint 입력을 한 프롬프트에 몰거나 앞에서 자르면 규모가 커질 때 뒤쪽을 놓친다 — 사례 2개: nashsu는 모든 페이지의 앞 500자를 한 번에 넣는다. mindbase는 디렉터리 순서로 40쪽만 넣고 결정적 검사도 그 범위에서만 돈다.

[확인] kfchou는 lint 보고서를 lint 대상 디렉터리 `wiki/pages/`에 쓴다. 보고서는 orphan 페이지마다 링크를 건다.

[추정] 그래서 다음 lint에서 그 페이지들이 orphan으로 잡히지 않는다 — 사례 1개: kfchou 보고서 #7의 결함 후보 2. 실행해 보지는 않았다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#7-lint) · [Ar9av](ar9av-obsidian-wiki.md#7-lint) · [AgriciDaniel](agricidaniel-claude-obsidian.md#7-lint) · [kfchou](kfchou-wiki-skills.md#7-lint) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#7-lint) · [openwiki](langchain-ai-openwiki.md#7-lint) · [mindbase](frankchu91-mindbase-llm-wiki.md#7-lint) · [nashsu](nashsu-llm-wiki.md#7-lint) · [inkeep](inkeep-open-knowledge.md#7-lint) · [OKF](okf-spec-and-methodologies.md#7-lint)

### 8. stale·모순 처리

덮어쓰기, 지우지 않는 표시, drift 감지, 시간 기반 낡음이 섞여 쓰인다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| 제자리 덮어쓰기, 이력은 git | kfchou, openwiki, atomicstrata(전체 재작성), mindbase(`context.md` + snapshot) | 페이지가 깨끗하다 | 옛 주장을 보려면 git을 뒤진다. 전체 재작성은 사람 손 편집을 지운다 |
| 소스 수로 규칙을 가른다 | nashsu: 단일 소스 페이지는 교체, 다중 소스는 LLM merge | 정정된 소스가 옛 문장을 끌고 다니지 않는다 | merge가 70% 길이 검사에 걸리면 다른 소스의 기여가 본문에서 빠진다 |
| 지우지 않고 표시 | Astro-Han Status Outdated/Disputed block, inkeep `deprecated` + `superseded_by`, Ar9av `valid_from`/`valid_until`/`superseded_by`, AgriciDaniel `superseded` 상태, cablate atom `_archive/` | 판단 이력이 페이지에 남는다 | 표시 안을 검사 밖에 두기 쉽다. Astro-Han은 Status block 안을 검사하지 않는다 |
| 원문 hash drift 감지 | openwiki(인용 범위 hash → 그 페이지를 강제 job, Claim마다 confirm/update/retract), atomicstrata(fresh/stale/orphaned/unverified 계산), AgriciDaniel(file source bytes), Ar9av(사람 검토 페이지 fingerprint) | 원문 변경이 wiki에 반영됐는지 기계가 안다 | 원문이 불변이면 이득이 작다 |
| 시간 기반 낡음 | AgriciDaniel `refresh_due`, OKF `stale_after`, Ar9av 90일, kfchou 90일 + 단어 | 날짜만으로 계산된다 | 기준일을 LLM이 정하면 피할 수 있다 |

[확인] nashsu 주석이 소스 수로 가른 이유를 적는다: "Merging the old body back into the new generation kept retracted wording alive indefinitely".

[확인] openwiki의 confirm은 LLM 판단 뒤 version만 다시 계산한다. 그래도 `verified` 스탬프가 붙는다.

[추정] stale을 계산 값으로 두고 저장하지 않는 쪽이 저장 플래그보다 어긋남이 적다 — 사례 3개: AgriciDaniel `refresh_due`, atomicstrata freshness, OKF trust tier가 모두 매번 계산한다.

[확인] 모순을 해소까지 코드로 강제한 곳은 없다. openwiki는 drift가 난 Claim에 대해서만 결정을 강제한다. inkeep consolidate는 사람 결정을 STOP gate로 둔다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#8-stale모순-처리) · [Ar9av](ar9av-obsidian-wiki.md#8-stale모순-처리) · [AgriciDaniel](agricidaniel-claude-obsidian.md#8-stale모순-처리) · [kfchou](kfchou-wiki-skills.md#8-stale모순-처리) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#8-stale모순-처리) · [openwiki](langchain-ai-openwiki.md#8-stale모순-처리) · [mindbase](frankchu91-mindbase-llm-wiki.md#8-stale모순-처리) · [nashsu](nashsu-llm-wiki.md#8-stale모순-처리) · [inkeep](inkeep-open-knowledge.md#8-stale모순-처리) · [OKF](okf-spec-and-methodologies.md#8-stale모순-처리)

### 9. 사람 개입

건별 승인부터 완전 자율까지 있다. 또 하나 갈리는 것은 승인 표시를 agent가 스스로 만들 수 있느냐다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| 건별·action별 승인 | mindbase 웹 contribute(체크박스가 처음에 모두 체크), kfchou update·merge | 오류가 들어오기 전에 본다 | 원본의 "유지비가 0에 가깝다"는 이점이 준다 |
| 계획 승인 | AgriciDaniel plan hash, kfchou ingest 상의, inkeep research rubric, mindbase plugin | 한 번 보고 묶음을 적용한다 | 승인한 계획과 실행 계획이 다를 수 있다(mindbase plugin) |
| 승격 결정 gate | inkeep consolidate, atomicstrata human gate | 확정 지식만 사람이 본다 | 잠정 층이 쌓인다 |
| 리뷰 큐(opt-in) | Ar9av `_staging/`, atomicstrata review policy, nashsu 비동기 review | 쓰기를 멈추지 않는다 | 기본값이 꺼져 있다 |
| PR 리뷰 | openwiki CI PR | git 도구를 그대로 쓴다 | auto-merge 예제도 함께 있다 |
| 자율 | Astro-Han, nashsu, openwiki, Ar9av·atomicstrata 기본 | 사람 시간이 들지 않는다 | 오류 누적을 막을 사람이 없다 |

[추정] 사람 승인을 데이터나 플래그로 표시하는 구현에서 그 표시를 agent가 만들 수 있다 — 사례: 아래 4개.

| repo | 승인 표시 | agent가 만드는 길 |
|---|---|---|
| AgriciDaniel | `--approved-plan-sha256` | 같은 agent가 inspect로 hash를 얻는다 |
| Ar9av | `trust-record --approved` | 호출자가 스스로 붙이는 플래그다 |
| OKF | `verified`의 `human:` 접두사 | 인증 장치가 없고, PoC 쓰기 도구는 LLM이 넘긴 값을 그대로 쓴다 |
| mindbase | MCP `ingest_execute` 승인 map | 빠진 id를 승인으로 본다 |

[확인] wiki 쓰기 승인의 주체를 코드로 사람에게 묶은 곳은 atomicstrata 하나다. human gate는 CLI 대화형 TTY 확인으로만 통과한다. SDK·비-TTY 경로는 거부한다.

[확인] 사람 승인을 코드로 받는 곳이 둘 더 있지만 wiki 내용 승인은 아니다. inkeep 앱이 띄운 agent는 `delete`·`move` 같은 파괴적 도구마다 승인을 받는다. nashsu agent의 `shell.exec`는 명령마다 승인을 받는다.

[확인] inkeep research rubric gate는 "just proceed" 한마디나 비대화형 환경에서 건너뛴다. consolidate gate에는 우회 문구가 없다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#9-사람-개입) · [Ar9av](ar9av-obsidian-wiki.md#9-사람-개입) · [AgriciDaniel](agricidaniel-claude-obsidian.md#9-사람-개입) · [kfchou](kfchou-wiki-skills.md#9-사람-개입) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#9-사람-개입) · [openwiki](langchain-ai-openwiki.md#9-사람-개입) · [mindbase](frankchu91-mindbase-llm-wiki.md#9-사람-개입) · [nashsu](nashsu-llm-wiki.md#9-사람-개입) · [inkeep](inkeep-open-knowledge.md#9-사람-개입) · [OKF](okf-spec-and-methodologies.md#9-사람-개입)

### 10. 동시성·안전

보호 범위는 "아무것도 없음"부터 "transaction + journal"까지다.

| 선택지 | repo | 얻는 것 | 치르는 것 |
|---|---|---|---|
| 장치 없음 | Astro-Han(git 언급도 없다) | 코드가 없다 | 쓰다 끊기면 반쯤 쓴 페이지가 남는다. 되돌릴 길이 없다 |
| git에 맡김 | kfchou(작업 1개 = commit 1개), OKF(명세가 git 배포를 권장한다. PoC는 임시 파일 없이 바로 쓴다) | 코드가 없다 | 쓰다 끊기면 반쯤 쓴 페이지가 남는다 |
| 공유 상태 파일만 lock + 원자적 교체 | Ar9av(O_EXCL lock, 60초 지나면 빼앗음), openwiki(tmp + rename, 프로세스 안 직렬화) | 여러 writer가 부딪히는 파일만 지킨다 | 페이지 본문과 프로세스 간 경합은 막지 못한다 |
| transaction | AgriciDaniel(vault flock, fsync, expected hash 재대조, journal rollback, operation id 멱등), atomicstrata(lock + pre-state journal, fsync 없음) | 반쯤 쓴 상태가 남지 않는다 | AgriciDaniel `transaction.py`만 4,803줄이다 |
| CRDT + 충돌 gate + shadow git | inkeep | 사람과 agent가 같은 문서를 동시에 편집한다 | 상시 서버가 필요하다 |
| 메모리 lock + 재시도 수렴 | nashsu(`fs::write`), mindbase(메모리 Set, 복원 도구 없는 snapshot) | 구현이 쉽다 | 프로세스가 죽으면 상태가 깨진다. nashsu는 깨진 queue를 빈 queue로 읽는다 |

도구 제한도 갈린다.

| 장치 | repo |
|---|---|
| 본문 생성 LLM에 도구 0개, Codex는 read-only sandbox | atomicstrata |
| shell 2개 명령만, `.claims/` 읽기·쓰기 거부, worker는 페이지 한 장만 | openwiki native |
| exec 명령 10개 allowlist, 읽기 전용 overlay, 실행 전후 mtime 비교 | inkeep |
| subagent 도구 목록 Read·Grep·Glob·Bash(Bash가 열려 있다) | AgriciDaniel |
| sub-agent allowlist의 도구 이름 9건이 실제 MCP 이름과 다르다 | mindbase |

[추정] 적용 직전 expected hash를 다시 대조하는 optimistic concurrency는 transaction 엔진 없이도 떼어 쓸 수 있는 가장 싼 장치다 — 사례 2개: AgriciDaniel의 write마다 `expected_hashes`, Ar9av staging promote의 revision pin.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#10-동시성안전) · [Ar9av](ar9av-obsidian-wiki.md#10-동시성안전) · [AgriciDaniel](agricidaniel-claude-obsidian.md#10-동시성안전) · [kfchou](kfchou-wiki-skills.md#10-동시성안전) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#10-동시성안전) · [openwiki](langchain-ai-openwiki.md#10-동시성안전) · [mindbase](frankchu91-mindbase-llm-wiki.md#10-동시성안전) · [nashsu](nashsu-llm-wiki.md#10-동시성안전) · [inkeep](inkeep-open-knowledge.md#10-동시성안전) · [OKF](okf-spec-and-methodologies.md#10-동시성안전)

### 11. Query·검색

검색 방식, 원문으로 내려가는가, 답을 되저장하는가가 따로 갈린다.

| 하위 선택 | 선택지와 repo |
|---|---|
| 검색 | index + grep(Astro-Han: index와 full-text가 둘 다 비었을 때만 "없다") / index 전체 읽기 + 링크 1단계, grep 없음(kfchou) / 계층 조회(Ar9av hot → index → graph-query → grep, AgriciDaniel hot → index → BM25) / BM25(openwiki SQLite FTS5 섹션 단위, inkeep Orama + exec loop) / hybrid(atomicstrata, mindbase, nashsu) |
| 원문으로 내려가기 | 코드가 강제하는 원문 전용 모드(nashsu Faithful: wiki·graph·web 도구 거부) / 원문 줄을 문맥에 포함(atomicstrata context pack) / source 층 가중치(mindbase) / 내려가지 않음(Astro-Han, Ar9av, AgriciDaniel, kfchou) |
| 되저장 | 안 함(Ar9av, openwiki) / 요청 시(Astro-Han archive, AgriciDaniel `save`, atomicstrata `--save` 검증 후) / 매번 제안(kfchou) / 네 조건 만족 시 제안(inkeep) / 승인 없이 저장하고 다음 합성의 입력이 됨(mindbase autoSave: research 페이지로 쓰고, build가 그 디렉터리를 입력으로 모은다) / 저장 즉시 소스로 재-ingest(nashsu Save to Wiki) |

[확인] nashsu는 Deep Research 결과의 재-ingest를 끊었다. 이유는 "Feeding it back through source ingest creates a second summary page and recursively produces low-value review suggestions"다.

[확인] 같은 저장소의 Save to Wiki는 아직 답을 바로 재-ingest한다.

[추정] 답을 소스처럼 다시 넣으면 파생물이 원본 자리에 들어간다 — 사례 1개: 위 nashsu 주석.

[확인] index만으로 버티는 규모를 여러 문서가 말한다. 잰 곳은 없다.

| 문서 | 말한 규모 |
|---|---|
| Karpathy 원본 | "~100 sources, ~hundreds of pages"에서 잘 된다 |
| rohitg00 | "maybe 100-200 pages"까지 된다 |
| cablate | 100~200쪽이 index-only의 한계다 |
| kfchou 설계 문서 | flat index는 "a few hundred pages"에서 깨진다 |
| Astro-Han | "50K–100K tokens" 크기 wiki에서는 vector보다 grep이 더 믿을 만하다 |

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#11-query검색) · [Ar9av](ar9av-obsidian-wiki.md#11-query검색) · [AgriciDaniel](agricidaniel-claude-obsidian.md#11-query검색) · [kfchou](kfchou-wiki-skills.md#11-query검색) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#11-query검색) · [openwiki](langchain-ai-openwiki.md#11-query검색) · [mindbase](frankchu91-mindbase-llm-wiki.md#11-query검색) · [nashsu](nashsu-llm-wiki.md#11-query검색) · [inkeep](inkeep-open-knowledge.md#11-query검색) · [OKF](okf-spec-and-methodologies.md#11-query검색)

### 12. index·log 관리

index를 만드는 방식은 네 갈래, log를 남기는 방식도 네 갈래다.

| 하위 선택 | 선택지와 repo |
|---|---|
| index | LLM이 손으로(Astro-Han: lint가 맞춤, AgriciDaniel: bundle 안에서) / frontmatter에서 결정적 재생성(Ar9av `memory sync`, kfchou `generate-index.py` + gitignore, atomicstrata, openwiki 디렉터리별, nashsu 수동 전체 재생성) / 동적 목록(inkeep `exec ls`) / 개수만(mindbase `index.yaml`, `context.md`가 대신) |
| log | LLM이 쓴다(Astro-Han append, inkeep append, AgriciDaniel는 bundle 안에서 최신을 위에) / 코드가 append(Ar9av, atomicstrata, mindbase, nashsu. nashsu는 LLM이 낸 항목을 코드가 붙이고, 없으면 코드가 만든다) / git commit trailer를 렌더(kfchou `Wiki-Op:`) / 쓰지 않음(openwiki, OKF PoC) |

[추정] index를 결정적으로 만드는 쪽으로 수렴한다 — 사례 5개: Ar9av, kfchou, atomicstrata, openwiki, nashsu. OKF PoC는 항목은 frontmatter에서 결정적으로 만들지만 하위 디렉터리 설명 한 줄을 LLM이 쓴다(아래 표).

[확인] nashsu 주석이 이유를 적는다: "so large wikis are never rewritten through model output".

| 얻는 것과 치르는 것 | 사례 |
|---|---|
| 결정적 index는 drift가 없다. 설명은 frontmatter `summary`·`description`에서 온다 | Ar9av는 LLM에게 hot.md의 Key Takeaways 한 칸만 준다 |
| index를 gitignore하면 merge conflict가 사라진다. GitHub에서 index를 바로 볼 수 없다 | kfchou |
| index를 잘라 프롬프트에 넣으면 오래된 페이지가 시야에서 빠진다 | nashsu Recently Updated 200항목 상한 |
| index 전문을 프롬프트에 넣으면 비용이 wiki 크기에 비례한다 | atomicstrata extraction, nashsu 재생성 뒤, Ar9av query |
| index 생성에 LLM을 섞으면 실행마다 diff가 난다 | OKF PoC 하위 디렉터리 설명 |
| git trailer log는 쓰지 않은 query를 남기지 못한다 | kfchou |

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#12-indexlog-관리) · [Ar9av](ar9av-obsidian-wiki.md#12-indexlog-관리) · [AgriciDaniel](agricidaniel-claude-obsidian.md#12-indexlog-관리) · [kfchou](kfchou-wiki-skills.md#12-indexlog-관리) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#12-indexlog-관리) · [openwiki](langchain-ai-openwiki.md#12-indexlog-관리) · [mindbase](frankchu91-mindbase-llm-wiki.md#12-indexlog-관리) · [nashsu](nashsu-llm-wiki.md#12-indexlog-관리) · [inkeep](inkeep-open-knowledge.md#12-indexlog-관리) · [OKF](okf-spec-and-methodologies.md#12-indexlog-관리)

### 13. 포맷 표준

OKF v0.2 대응은 다섯 수준이다.

| 수준 | repo |
|---|---|
| native v0.2 출력 + 코드 검증 | openwiki |
| v0.2 결정적 lint plugin(llm-wiki pack은 켜지 않음) | inkeep |
| export/import 다리 | Ar9av(프롬프트 skill), atomicstrata(v0.1, import는 리뷰 큐로) |
| 일부러 따르지 않음 | Astro-Han("v0.1 draft"라 추적만) |
| 대응 없음 | kfchou(설계 문서에 언급만), AgriciDaniel, mindbase, nashsu |

OKF가 정한 것은 아래와 같다.

| OKF 결정 | 내용 |
|---|---|
| 필수 필드 | `type` 하나. consumer는 optional 필드 누락이나 깨진 link로 bundle을 거부하면 안 된다 |
| 신뢰 | `generated`(누가 썼나)와 `verified`(누가 확인했나)를 나눈다. trust tier는 저장하지 않고 신호에서 계산한다 |
| 낡음 | `status`(draft/stable/deprecated)와 절대 시각 `stale_after` |
| 근거 | 본문 footnote label을 `sources[].id`에 맞춘다. 위치 번호는 고쳐 쓸 때 조용히 틀어져서 피한다 |
| 없는 것 | `superseded_by`, 모순 표현, typed link |

[확인] OKF 자기 PoC와 샘플이 명세를 어긴 곳이 있다. 에이전트가 만든 stackoverflow 샘플은 명세가 피하라는 위치형 `[^1]` footnote를 쓴다. viewer와 index 생성기는 예약 파일 `log.md`를 concept으로 다룬다.

[추정] 형식 규칙도 검사기가 없으면 만든 쪽부터 어긴다 — 사례 1개: 위 OKF 샘플.

[추정] 근거를 frontmatter가 아니라 장부·sidecar에 두는 구현은 OKF로 옮길 때 투영이 필요하다 — 사례 2개: openwiki는 Claim 증거를 `sources`로 투영하는 코드를 따로 두었다. AgriciDaniel은 그런 변환이 없어서 보고서가 ledger를 frontmatter로 펼치는 변환이 필요하다고 판단했다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#13-포맷-표준) · [Ar9av](ar9av-obsidian-wiki.md#13-포맷-표준-okf) · [AgriciDaniel](agricidaniel-claude-obsidian.md#13-포맷-표준) · [kfchou](kfchou-wiki-skills.md#13-포맷-표준-okf) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#13-포맷-표준) · [openwiki](langchain-ai-openwiki.md#13-포맷-표준) · [mindbase](frankchu91-mindbase-llm-wiki.md#13-포맷-표준-okf) · [nashsu](nashsu-llm-wiki.md#13-포맷-표준) · [inkeep](inkeep-open-knowledge.md#13-포맷-표준-okf) · [OKF](okf-spec-and-methodologies.md#13-포맷-표준-okf-준수-정도)

### 14. 규모·비용

[확인] 9개 구현 어디에도 ingest 1회의 토큰·시간·금액 측정값이 없다.

| 주장 상태 | repo와 주장 |
|---|---|
| 규모 주장, 검증 불가 | Astro-Han(article 94, 소스 99, 비공개 wiki), cablate(630 atoms, 83 pages, 비공개), inkeep("thousands of files", "소스당 30초"), Ar9av("20 pages or 2000, roughly the same cost"), nashsu(recall 58.2% → 71.4%), mindbase(qwen3:14b 약 30초), rohitg00("thousands of sessions") |
| 주장하지 않거나 지웠다 | AgriciDaniel(v2.0.0에서 성능 주장 삭제), atomicstrata("still early software"), openwiki(자기 wiki 22쪽·Claim 746개만 공개) |

비용을 줄이는 장치는 많다.

| 장치 | repo |
|---|---|
| 원문 hash가 같으면 건너뜀 | Ar9av, atomicstrata, nashsu |
| 할 일이 없으면 모델 0회 | openwiki |
| 바뀐 Claim만 프롬프트에 넣음 | openwiki |
| prefix cache를 노린 프롬프트 순서, extraction 결과 재사용 | atomicstrata |
| 코드 소스는 AST로 구조만 뽑아 본문을 LLM에 보내지 않음 | Ar9av |
| 원문 수·바이트·페이지 예산을 사람과 먼저 합의 | AgriciDaniel |
| 연산당 LLM 1회 + 실패 시 1회 재시도, tool loop 없음 | mindbase 웹 ops engine(v1 compile은 tool loop 최대 10회, query는 `read_file` loop 최대 3회) |
| ingest에서 합성을 빼고 research 요청 때로 미룸 | inkeep |

[추정] 한 연산 안에 wiki 전체를 읽는 단계가 하나라도 있으면 그 연산의 비용이 페이지 수에 비례한다 — 사례 4개: ingest에서는 atomicstrata extraction의 index 전문, kfchou의 전 페이지 backlink 점검, Astro-Han cascade의 wiki 전체 검색이다. query에서는 Ar9av가 매번 index 전체를 읽는다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#14-규모비용) · [Ar9av](ar9av-obsidian-wiki.md#14-규모비용) · [AgriciDaniel](agricidaniel-claude-obsidian.md#14-규모비용) · [kfchou](kfchou-wiki-skills.md#14-규모비용) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#14-규모비용) · [openwiki](langchain-ai-openwiki.md#14-규모비용) · [mindbase](frankchu91-mindbase-llm-wiki.md#14-규모비용) · [nashsu](nashsu-llm-wiki.md#14-규모비용) · [inkeep](inkeep-open-knowledge.md#14-규모비용) · [OKF](okf-spec-and-methodologies.md#14-규모비용)

### 15. frosk1 비판 대응

#frosk1 비판 7가지 × 구현 대응 표에서 따로 다룬다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#15-frosk1-비판-7가지) · [Ar9av](ar9av-obsidian-wiki.md#15-frosk1-비판-대응) · [AgriciDaniel](agricidaniel-claude-obsidian.md#15-frosk1-비판-7가지) · [kfchou](kfchou-wiki-skills.md#15-frosk1-비판-7가지에-대한-대응) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#15-frosk1-비판-7가지-대응) · [openwiki](langchain-ai-openwiki.md#15-frosk1-비판-7가지에-대한-대응) · [mindbase](frankchu91-mindbase-llm-wiki.md#15-frosk1-비판-7가지에-대한-대응) · [nashsu](nashsu-llm-wiki.md#15-frosk1-비판-7가지에-대한-대응) · [inkeep](inkeep-open-knowledge.md#15-frosk1-비판-7가지에-대한-대응) · [OKF](okf-spec-and-methodologies.md#15-frosk1-비판-7가지에-대한-대응)

### 16. 성숙도·차용 가능성

라이선스가 먼저 갈린다.
MIT 7곳은 코드째 가져올 수 있다.
GPL-3.0 2곳은 코드를 가져오면 내 저장소도 GPL-3.0 조건을 따라야 한다. 그 조건을 받지 않으면 설계만 참고한다.
OKF는 Apache-2.0이다. cablate는 라이선스가 없어 스크립트 복사 권리가 불분명하다.

| repo | 라이선스 | 테스트·CI | 떼어 쓰기 좋은 단위 |
|---|---|---|---|
| Astro-Han | MIT | unittest 52개, CI 없음 | `check_evidence.py` 431줄 + 테스트 |
| Ar9av | MIT | 테스트 1,115개, CI(서버 테스트는 skip) | `memory.py` 재생성, `cache.py` lock |
| AgriciDaniel | MIT | 테스트 534개, Linux·macOS matrix CI | `lint_engine.py` 1,381줄. `ledgers.py`는 `transaction.py`를 끌고 온다 |
| kfchou | MIT | 테스트 676줄, CI 없음, hook 자체 테스트 없음 | `generate-index.py` 135줄, `render-log.py`, `lint-mechanical.py` |
| atomicstrata | MIT | 테스트 파일 1,352개, CI 4개, husky | citation normalizer, `deps.ts` 소유 역색인, journal. 전체 171k줄은 통째로 가져오기 어렵다 |
| openwiki | MIT | 테스트 파일 241개, CI | `src/claims/core` + `evidence` 약 1.7k줄. 층 분리를 테스트가 강제한다 |
| mindbase | MIT | 테스트 파일 115개, CI(MCP는 build·기동, web은 typecheck·build만), 기여자 1명 | `apps/server/src/ops` 약 1,300줄 |
| nashsu | GPL-3.0 | TS 약 1,900건 + Rust 369건, CI는 build만 | 설계만 |
| inkeep | GPL-3.0, CLA | 테스트 파일 3,067개 | 설계와 프롬프트 구조만. 코드는 GPL 조건부 |
| OKF | Apache-2.0 | PoC test 39개 | 형식 자체, `document.py`의 trust tier·stale 계산 |

[확인] Astro-Han과 kfchou는 2026-07 이후 push가 없다.

[확인] 문서와 코드가 어긋난 곳을 기록한 보고서는 10개 중 8개다. 없는 것은 atomicstrata와 openwiki 둘이다.

[확인] 그중 없는 기능을 있다고 적은 곳은 셋이다. nashsu는 README가 7곳에서 코드와 다르다. Ar9av는 "No scripts"라고 적었지만 15k줄 CLI가 있고, `/mcp` 인증도 문서와 코드가 다르다. mindbase는 README가 "모든 쓰기 승인"을 말하지만 승인이 있는 경로는 1개다.

보고서: [Astro-Han](astro-han-karpathy-llm-wiki.md#16-성숙도차용-가능성) · [Ar9av](ar9av-obsidian-wiki.md#16-성숙도차용-가능성) · [AgriciDaniel](agricidaniel-claude-obsidian.md#16-성숙도차용-가능성) · [kfchou](kfchou-wiki-skills.md#16-성숙도차용-가능성) · [atomicstrata](atomicstrata-llm-wiki-compiler.md#16-성숙도차용-가능성) · [openwiki](langchain-ai-openwiki.md#16-성숙도차용-가능성) · [mindbase](frankchu91-mindbase-llm-wiki.md#16-성숙도차용-가능성) · [nashsu](nashsu-llm-wiki.md#16-성숙도차용-가능성) · [inkeep](inkeep-open-knowledge.md#16-성숙도차용-가능성) · [OKF](okf-spec-and-methodologies.md#16-성숙도차용-가능성)

## repo별 장단점 요약

| repo | 강점 | 약점 | 가져올 만한 것 |
|---|---|---|---|
| [Astro-Han](astro-han-karpathy-llm-wiki.md) | 숫자·날짜·인용을 그 페이지가 가리킨 원문에서 글자 그대로 찾는다. 검사 범위를 닫힌 목록으로 적었다. 거절한 기능 11개마다 운영상 이유를 남겼다 | 강제가 없다. 검사기 exit code가 항상 0이다. Status block 안과 자기 선언 archive는 검사 밖이다. 예시 raw를 검사기에 맞게 고쳤다 | locate-before-write 규칙과 검사기 코드, No material 처분, Status block, "만들지 않은 것과 이유" 문서 |
| [Ar9av](ar9av-obsidian-wiki.md) | 여러 writer가 부딪히는 파일만 정확히 골라 lock과 결정적 재생성으로 지킨다. hash 증분과 이식 가능한 소스 key가 있다. 시간 축 필드를 질의가 실제로 읽는다 | 쓰기 시점 gate가 없다. `^[inferred]` 라벨이 없으면 사실로 간주한다. `/mcp` 경로에 인증이 없다. skill 40개로 표면이 넓다 | `memory sync`식 index·log 재생성, O_EXCL lock + `os.replace`, fail/warn exit code, `valid_until` + `--as-of` |
| [AgriciDaniel](agricidaniel-claude-obsidian.md) | worker는 초안만 내고 orchestrator 하나가 transaction 하나로 쓴다. 승인 hash가 vault 정체성과 파일 mode까지 묶는다. source ledger·claim ledger·manifest를 나눴다 | Write/Edit을 막는 hook이 없다. 승인 hash를 agent가 스스로 얻는다. ledger가 선택이다. index를 LLM이 손으로 고친다 | draft packet 형식, expected hash 재대조, "accepted는 신선한 비합성 source" 규칙, 계산형 stale |
| [kfchou](kfchou-wiki-skills.md) | 결정적 일과 판단의 경계가 선명하다. index를 재생성하고 gitignore한다. log를 git trailer로 대체한다. hook이 staged blob을 읽는다 | gate가 LLM이 쓴 flag만 본다. 링크 대상은 working tree로 해석한다. 중첩 repo에서 gate가 꺼질 수 있다. ingest 증분이 없다 | `generate-index.py`, `Wiki-Op:` trailer, staged gate, cluster subagent lint |
| [atomicstrata](atomicstrata-llm-wiki-compiler.md) | LLM에게 부수효과 있는 도구가 없다. 줄 번호 붙인 원문 → 줄 범위 citation → 결정적 범위 검사가 한 번호 체계를 쓴다. pre-state journal로 크래시 일관성이 있다 | 기본 concept 페이지에 내용 gate가 없고 기본값이 자율 live 쓰기다. 병합 키가 제목 slug다. 업데이트가 전체 재작성이다. 원문 사본을 자른다 | citation 3단 구조, "uncited = inferred", lint tier, prompt digest 증분 키, 승인 권한을 workspace 밖 env에 두기 |
| [openwiki](langchain-ai-openwiki.md) | 증거 version을 코드가 계산해 위조할 수 없다. 줄 범위가 앞뒤 context hash로 이동을 따라간다. drift가 난 Claim마다 결정을 강제한다 | 본문과 Claim 일치는 프롬프트뿐이다. hash 일치를 `verified`라 부른다. host 모드와 personal 모드에서 강점이 빠진다. 엔진이 무겁다 | Claim `{resource, version}` 모델, context hash resolver, preflight → 강제 job, 바뀐 Claim만 프롬프트에 넣기 |
| [mindbase](frankchu91-mindbase-llm-wiki.md) | LLM 출력을 닫힌 action 4종으로만 받는다. lint가 결정적 kind와 LLM kind를 코드로 나누고 모순은 원문 일치 인용을 요구한다. 입력을 source 층에 먼저 저장한다 | 승인과 인용 보정이 웹 contribute 한 경로에만 있다. 엔진·layout이 둘이라 MCP가 자기 ingest 결과를 검색하지 못한다. 도구 이름 9건이 어긋난다 | discriminated union action, lint 인용 검증 + `dropped=N`, STATE RULE("움직이는 값 대신 위치를 적어라") |
| [nashsu](nashsu-llm-wiki.md) | ingest 경로의 쓰기 직전 gate가 촘촘하다. "부분 성공 = 실패"로 cache를 다룬다. 원문 전용 Faithful 모드를 코드가 강제한다. 파일 감시가 이벤트 유실에 강하다 | gate가 ingest 경로에만 걸린다. merge fallback이 다른 소스의 기여를 버린다. Save to Wiki가 답을 재-ingest한다. README가 코드와 7곳에서 어긋난다 | 설계만(GPL): FILE 블록 + 한 함수 gate, 소스 수로 갱신 규칙 가르기, 원문 모드 |
| [inkeep](inkeep-open-knowledge.md) | 원문을 verbatim, binary는 바이트째 보존한다. 잠정과 확정을 나누고 승격에 사람 결정을 요구한다. CRDT·충돌 거부·shadow git으로 쓰기 안전이 코드에 있다 | wiki 규율은 전부 프롬프트이고 lint plugin이 기본 꺼짐이다. frontmatter 출처 경로는 검사 밖이다. 상시 서버가 필요하다 | 설계만(GPL 조건부): 3층 + 승격 gate, 폴더 옆 규칙 파일, 답 되저장 네 조건 |
| [OKF](okf-spec-and-methodologies.md) | 신뢰와 신선도를 저장하지 않고 계산한다. `generated`와 `verified`를 나눴다. footnote를 id로 묶는 이유를 적었다. 진입 장벽이 `type` 하나다 | supersede·모순·typed link가 없다. `human:` 접두사를 인증하지 않는다. 자기 PoC와 샘플이 명세를 어긴다 | frontmatter 바닥, 계산형 trust·stale, keyed footnote + 결정적 대조 lint |

## frosk1 비판 7가지 × 구현 대응 표

frosk1 댓글의 항목은 아래와 같다.
8번째 staleness는 #8. stale·모순 처리에서 다뤘다.

| 번호 | 이름 | 원문 |
|---|---|---|
| 1 | 오류 누적 | "Once incorrect information is merged into the wiki, future updates build on top of it." |
| 2 | 부분 문맥 | "Updates are typically done using only a subset of documents (e.g., top-k retrieval)." |
| 3 | 요약 손실 | "Summarization is compression." |
| 4 | 가짜 source of truth(SoT) | "A curated wiki feels authoritative, but it is still a derived artifact." |
| 5 | 환각 병합 | "LLMs may “smooth over” contradictions or even invent connections between concepts." |
| 6 | 운영 복잡도 | "You’re introducing a full new layer" |
| 7 | ingest 비용 | "You shift cost from query time to ingestion time." |

칸의 강도 표기는 이렇다.

| 표기 | 뜻 |
|---|---|
| 강 | 코드가 막거나 구조상 일어나지 않는다 |
| 부분 | 코드 장치가 일부 경우만 덮는다 |
| 프롬프트 | 지시문뿐이다 |
| 약 | 대응이 거의 없다 |
| 악화 | 대응하면서 그 비판이 가리킨 비용을 키웠다 |
| 재정의 | 비판을 막지 않고, 비판이 문제 삼은 대상의 뜻을 바꿨다 |
| 이동 | 비용을 다른 연산으로 옮겼다 |
| 명세 | 형식 명세가 처방만 하고 강제하는 코드는 없다(OKF 행) |
| 다루지 않음 | 문서가 그 비판에 해당하는 내용을 정하지 않는다(OKF 행) |

| repo | 1 오류 누적 | 2 부분 문맥 | 3 요약 손실 | 4 가짜 SoT | 5 환각 병합 | 6 운영 복잡도 | 7 ingest 비용 |
|---|---|---|---|---|---|---|---|
| Astro-Han | 부분: literal만 grep | 프롬프트: 동의어 전체 검색 | 부분: raw 보존, query는 raw로 안 감 | 부분: 답은 wiki 인용 | 프롬프트: Disputed 표시 | 강: 의존성 0, 기능 11개 거절 | 약: No material 정지뿐 |
| Ar9av | 약: 라벨·비율이 LLM 몫 | 약: 소스별 처리 그대로 | 부분: 원본 스냅샷 + `snapshots:` | 부분: draft 기본, 원문 재확인 없음 | 약: `--auto` 병합에 사람 확인 없음 | 악화: skill 40개 | 부분: hash·AST·상한 15 |
| AgriciDaniel | 부분: accepted 규칙은 코드, 라벨은 LLM, ledger 선택 | 부분: 예산 + partial 표시 | 부분: `.raw/` create-only, query는 원본 안 감 | 프롬프트: hot·index는 근거 아님 | 부분: 반대 근거 있는 accepted에 notes 요구 | 악화: 엔진 19k줄 | 프롬프트: 예산 합의 |
| kfchou | 부분: 인용 강제, audit은 수동 | 부분: 이웃 페이지만, 한계 명시 | 부분: raw 불변 + 줄 범위 | 약: query가 wiki를 SoT라 부름 | 부분: 링크 gate, merge는 사람 확인 | 강: stdlib + git | 약: 대응 없음 |
| atomicstrata | 부분: hash 재생성, 전체 재작성이 오류를 잇는다 | 강: 공유 소스 전파(200k자 절단) | 부분: 원문 보존, 단 100k자 절단 | 강: 줄 citation, freshness, 답은 unverified | 약: 제목 slug 일치 병합 | 악화: 플랫폼 계층 | 강: 증분·캐시(수치 없음) |
| openwiki | 부분: drift 강제 재검토는 코드. confirm은 LLM 판단이고, 증거가 그대로인 Claim은 다시 보지 않는다 | 부분: code 모드 탐색, personal은 24시간 창 | 강: 원본이 소스 코드 그대로 | 부분: wiki는 선택 문맥, `verified` 스탬프가 부풀림 | 부분: 증거 존재만 | 악화: 61k줄, 의존성 27개 | 강: no-op 0회, 바뀐 Claim만(수치 없음) |
| mindbase | 부분: 인용 부착·snapshot, build가 이전본 위에 재작성 | 약: 입력 상한이 작다 | 부분: source 층 append-only, 400줄 상한 | 부분: 답에 층 표시, 단 `context.md`를 "truth"라 부름 | 부분: lint는 강, 병합은 약 | 악화: 엔진 2개, 도구 50개 | 부분: 로컬 모델, 연산당 1회. worker는 자동 compile |
| nashsu | 부분: 단일 소스 교체, Save to Wiki 재-ingest | 부분: 긴 소스 chunk, wiki는 index만 | 부분: 원문 보존 지시, 70% 하한 | 강: Faithful 모드 코드 강제 | 부분: 필드 잠금, 사람이 고르는 dedup | 악화: 약 9만 줄, 상태 파일 10여 개 | 부분: cache·checkpoint(수치 없음) |
| inkeep | 프롬프트: 잠정/확정 + 사람 결정 | 프롬프트: 스캔 지시 | 강(설계): verbatim·바이트 보존. 강제는 프롬프트 | 재정의: articles를 결정 기록으로 | 프롬프트: 사람 결정 뒤 병합 | 악화: 상시 서버 | 이동: 합성을 research 시점으로 |
| OKF | 명세: `generated`/`verified` 분리, attestation 미연결 | 다루지 않음 | 명세: per-claim footnote | 명세: advisory tier, `human:` 미인증 | 명세: untyped link | 강: 필수는 `type` 하나 | 다루지 않음 |

[추정] 가장 덜 풀린 비판은 부분 문맥과 ingest 비용이다 — 사례: 부분 문맥에 "강"인 곳은 atomicstrata 1개, ingest 비용 측정값은 0개다.

[추정] 요약 손실은 원문 보존으로 거의 모두 대응하지만, query가 원문으로 내려가지 않으면 보존이 답에 닿지 않는다 — 사례 4개: Astro-Han, Ar9av, AgriciDaniel, kfchou의 query는 wiki 페이지까지만 읽는다.

[추정] 운영 복잡도는 다른 6개와 맞바꾸는 축이다 — 사례: "강"이 많은 openwiki·atomicstrata가 6번에서 "악화"이고, 6번 "강"인 Astro-Han·kfchou는 1·7번이 약하다.

## 내 llm-wiki를 설계할 때 정해야 할 결정들

결정 12개를 앞 결정이 뒤 결정을 묶는 순서로 놓는다.
정답은 적지 않는다.
각 결정에 선택지, 그 선택지의 참고 repo, 그 선택이 뒤에 거는 제약을 적는다.

| 순서 | 결정 | 앞 결정에서 받는 제약 | 뒤 결정에 거는 제약 |
|---|---|---|---|
| D1 | 원문이 바뀌는가 | 없음. 내 자료의 성격이 정한다 | D5 근거 단위, D7 stale 처리, D2 증분 |
| D2 | LLM에게 파일 쓰기를 맡기는가 | D1 | D3, D4, D5, D9, D11 — 거의 모든 것 |
| D3 | 이력과 되돌리기를 git에 맡기는가 | D2 | D4 승인 지점, D8 log, D9 gate |
| D4 | 사람은 어디서 승인하는가 | D2, D3 | D7 모순 해소 주체 |
| D5 | 근거를 어떤 단위로 추적하는가 | D1, D2 | D6 저장 형식, D7 drift 감지, D10 원문 회귀, D12 실행 형태 |
| D6 | 메타데이터를 어디에 어떤 형식으로 두는가 | D5 | D8 index 생성, D11 typed 관계 저장 자리 |
| D7 | 낡음과 모순을 어떻게 다루는가 | D1, D4, D5 | D9 lint 항목 |
| D8 | index와 log를 누가 만드는가 | D3, D6 | D10 검색, D12 연산 비용 |
| D9 | lint를 어디까지 결정적으로, gate로 쓰는가 | D2, D3, D7 | — |
| D10 | 검색 방식과 답 되저장 | D5, D8 | D12 실행 형태·연산 비용 |
| D11 | Link를 누가 걸고 타입을 붙이는가 | D2, D6 | — |
| D12 | 실행 형태와 연산당 비용 상한 | D5, D8, D10 | — |

### D1. 원문이 바뀌는가

| 선택지 | 참고 repo | 뒤에 거는 제약 |
|---|---|---|
| 불변(웹 클리핑, 논문) | Astro-Han, kfchou, inkeep | hash drift 감지의 이득이 작다. 줄 범위 인용이 깨지지 않는다. 단 불변을 코드로 지켜야 이 전제가 선다 |
| 가변(내가 고치는 노트, 코드) | openwiki, atomicstrata, Ar9av 코드 프로젝트 | 증분 hash와 drift 감지가 필요하다. 줄 범위를 쓰면 재배치 장치가 필요하다 |

[추정] 불변이라고 정하면 그 불변을 hook이나 쓰기 도구 제한으로 지켜야 한다 — 사례 1개: Astro-Han은 불변을 이유로 hash를 거절했고 저장소 스스로 raw를 고쳤다.

### D2. LLM에게 파일 쓰기를 맡기는가

가장 많은 것을 묶는 결정이다.

| 선택지 | 참고 repo | 뒤에 거는 제약 |
|---|---|---|
| 가. agent가 직접 쓰고 사후 검사 | Astro-Han, Ar9av, inkeep | skill만으로 된다. 대화하며 쓰는 원형에 가깝다. 막을 곳은 lint와 commit뿐이다 |
| 나. agent가 직접 쓰고 commit gate | kfchou | D3에서 git이 필수가 된다. gate는 우회 스위치를 가진다 |
| 다. agent는 초안·계획만, 코드가 적용 | AgriciDaniel, mindbase 웹 ops, nashsu ingest | CLI 엔진이 필요하다. 승인 지점(D4)이 적용 직전에 자연스럽게 생긴다. 직접 쓰기를 막는 hook이 없으면 우회된다 |
| 라. LLM은 텍스트 함수, 코드가 모든 쓰기 | atomicstrata, openwiki native | 엔진이 LLM을 직접 부른다. Claude Code 세션 안에서 대화하며 ingest하는 방식과 부딪힌다. 근거 version·줄 번호를 코드가 붙일 수 있다 |

[추정] 어느 선택지든 모든 쓰기 경로가 같은 gate를 지나게 하지 않으면 그 선택의 이득이 샌다 — 사례 5개: #2. 규칙의 위치 절의 우회 경로 표.

[추정] '다'를 Claude Code 위에서 고르면 PreToolUse hook으로 wiki·raw 경로의 Write/Edit을 막아야 엔진이 유일한 길이 된다 — 사례 1개: AgriciDaniel 보고서의 피할 것. 이 hook은 Bash로 엔진 함수를 직접 부르는 길을 막지 못한다. 그래서 승인 검사도 적용 함수 안에 둬야 한다.

### D3. 이력과 되돌리기를 git에 맡기는가

| 선택지 | 참고 repo | 뒤에 거는 제약 |
|---|---|---|
| 작업 1개 = commit 1개 | kfchou, AgriciDaniel checkpoint(선택) | commit이 승인 지점이 된다. log를 trailer로 대체할 수 있다. pre-commit gate를 쓸 수 있다 |
| git은 변경 감지에만, commit은 사람이나 CI | openwiki | 이력은 git에 있고 엔진은 상태 파일만 쥔다 |
| 자체 journal·snapshot | atomicstrata, mindbase, nashsu | 크래시 복구는 되지만 사용자용 되돌리기가 없거나 약하다 |
| 자체 shadow git | inkeep | 상시 서버가 필요하다 |

[확인] kfchou gate는 wiki root가 git top-level이라고 가정한다. 기존 repo 안에 wiki를 두면 hook 경로와 staged 경로 접두사를 wiki root 기준으로 다시 계산해야 한다.

### D4. 사람은 어디서 승인하는가

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| ingest 전 상의 | kfchou, AgriciDaniel(예산) | 원본 Karpathy 방식이다. 자동 감시와 함께 두면 두 경로를 따로 유지해야 한다(nashsu는 대화형 경로를 걷어 냈다) |
| 실행될 계획에 승인 | AgriciDaniel | 승인 표시를 사람 채널로만 받아야 한다. agent가 hash를 얻어 스스로 넘기면 "검토한 계획 = 적용한 계획" 보장만 남는다 |
| 잠정 → 확정 승격 gate | inkeep, atomicstrata human gate | 3층 저장 구조(D6)를 요구한다 |
| commit·PR 리뷰 | kfchou, openwiki | D3에서 git을 골라야 한다 |
| 자율 + 사후 리뷰 큐 | nashsu, Ar9av staging, atomicstrata review | 큐를 비우는 LLM이 보존 약속을 지키는지는 코드로 걸러야 한다(nashsu sweep 사례) |

[추정] 승인 표시를 필드나 플래그로 둔다면 agent가 그 값을 쓸 수 없게 해야 한다 — 사례 4개: #9. 사람 개입 절의 승인 표시 표. 참고할 반례는 atomicstrata의 TTY 전용 human gate와 승인 권한을 workspace 밖 환경 변수에 둔 trust gate다.

### D5. 근거를 어떤 단위로 추적하는가

| 선택지 | 참고 repo | 앞 결정과 맞는 조합 |
|---|---|---|
| 페이지 링크만 | inkeep, nashsu | 어느 D2와도 맞는다. 검증은 링크 실재까지다 |
| 페이지 링크 + literal 글자 일치 | Astro-Han | D1 불변과 맞는다. D2 가·나에서도 돈다. 맞는 값을 틀린 주장에 붙인 오류는 남는다 |
| 줄 범위 + 결정적 대조 | atomicstrata(범위 검사), kfchou(인용 형식) | D1 불변이면 단순하다. 가변이면 재배치가 필요하다. 줄 번호를 원문에 붙여 보여 주려면 D2 라가 유리하다 |
| claim ledger + 코드 계산 version | openwiki, AgriciDaniel | D1 가변과 D2 다·라에 맞는다. 장부를 필수로 두지 않으면 규칙이 걸리지 않는다 |

[추정] 결정적 검사는 "인용한 값이 원문에 있다"까지가 현재 관찰된 한계다 — 사례 4개: #5. 근거 추적 단위 절의 단위 표. 그 너머를 원하면 LLM judge 표본 평가(atomicstrata eval)를 사후 장치로 붙이는 길만 관찰됐다.

### D6. 메타데이터를 어디에 어떤 형식으로 두는가

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| OKF frontmatter 바닥 + 확장 필드 | openwiki, OKF, inkeep 템플릿 | supersede는 확장 필드로 넣는다. OKF는 모르는 키를 보존해야 한다 |
| 자체 frontmatter | Ar9av, kfchou, nashsu | 나중에 내보내려면 변환기가 필요하다 |
| frontmatter 없이 blockquote | Astro-Han | 의존성 없이 읽힌다. frontmatter 기반 도구와 안 맞는다 |
| 페이지 밖 장부·sidecar | AgriciDaniel, openwiki | D5 claim ledger와 짝이다. 본문과 장부를 잇는 결정적 대조가 따로 필요하다 |
| 잠정/확정 디렉터리 | inkeep | D4 승격 gate와 짝이다 |

[추정] 필드 이름은 한 곳에서 정하고 lint로 검사해야 한다 — 사례 3개: inkeep 템플릿 `created` 대 skill `date`, AgriciDaniel 문서 `review_state` 대 ledger `review_status`, Ar9av `pages_produced` 대 `pages_created`.

### D7. 낡음과 모순을 어떻게 다루는가

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| 덮어쓰기 + git 이력 | kfchou, openwiki | D3 git이 필요하다. 모순 해결 이력이 페이지에서 사라진다 |
| 지우지 않는 표시 | Astro-Han Status block, inkeep `superseded_by`, Ar9av `valid_until` | 표시 안의 값도 검사 대상에 넣어야 한다 |
| drift 강제 재검토 | openwiki | D1 가변 + D5 hash 단위가 있어야 한다 |
| 시간 기반 stale 계산 | AgriciDaniel `refresh_due`, OKF `stale_after` | 기준일을 누가 정하는지 정해야 한다. LLM이 정하면 피할 수 있다 |
| 소스 수로 갱신 규칙 가르기 | nashsu | merge 실패 때 기존 본문을 유지하거나 사람에게 넘겨야 한다 |
| 신뢰 점수 저장 | rohitg00 처방, Ar9av `base_confidence` | OKF가 든 반대 이유(주관적, 옮길 수 없음, 낡음)를 받아들일지 정해야 한다 |

### D8. index와 log를 누가 만드는가

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| frontmatter에서 결정적 재생성 | Ar9av, kfchou, atomicstrata, openwiki | D6에 `summary`·`description` 필드가 있어야 한다 |
| 동적 목록 | inkeep | 목록 결과에 frontmatter를 붙이는 도구가 있어야 한다 |
| LLM 손 갱신 | Astro-Han, AgriciDaniel | lint로 어긋남을 찾아야 한다 |
| log를 코드가 append | Ar9av, atomicstrata, mindbase | 형식을 한 곳에서 정한다(nashsu는 세 갈래로 갈렸다) |
| log를 git trailer로 | kfchou | D3 git이 필요하다. 쓰지 않은 query는 기록되지 않는다 |

### D9. lint를 어디까지 결정적으로, gate로 쓰는가

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| 결정적 lint + exit code + pre-commit | kfchou, Ar9av exit code | D3 git. gate는 staged 내용과 staged 링크 대상을 함께 봐야 한다 |
| 결정적 lint + 선택형 commit gate | AgriciDaniel checkpoint | 우회 스위치를 둘지 정한다 |
| LLM lint는 근거를 요구하고 못 대면 버림 | mindbase | 원문 글자 일치 인용 같은 결정적 검증이 짝으로 있어야 한다 |
| LLM lint를 cluster로 나눔 | kfchou | 고정 tag는 cluster 계산에서 뺀다. lint 보고서는 lint 대상 밖에 둔다 |

### D10. 검색 방식과 답 되저장

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| index 읽기(+ grep) | Astro-Han(index + full-text grep), kfchou(index 전체 + 링크 1단계) | 측정된 한계는 없다. 여러 문서가 수백 쪽을 한계로 짐작한다 |
| BM25·FTS | openwiki, inkeep, AgriciDaniel | 인덱스 갱신 시점을 ingest와 잇는다(AgriciDaniel은 연결을 찾지 못했다) |
| hybrid(vector 포함) | atomicstrata, mindbase, nashsu | embedding 갱신 실패를 따로 다룬다(atomicstrata pending 큐) |
| 원문으로 내려가는 모드 | nashsu Faithful, atomicstrata context pack | D5에서 줄 범위나 원문 링크가 있어야 내려갈 자리가 생긴다 |
| 되저장은 별도 페이지, 소스로 재-ingest하지 않음 | Astro-Han archive, inkeep 네 조건, AgriciDaniel `save` | 되저장 페이지에 근거 검사를 어떻게 걸지 정한다(Astro-Han archive는 검사 밖) |

### D11. Link를 누가 걸고 타입을 붙이는가

D2와 D6에 묶인다.
코드가 링크를 직접 걸려면 D2에서 코드가 페이지를 쓰는 경로가 있어야 한다.
typed 관계를 둘 자리는 D6에서 정한 메타데이터 자리를 따른다.
설계 축은 #6. Link다.

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| 걸기 가. LLM이 걸고 검사도 LLM | Astro-Han | D2 가에서도 돈다. 깨진 링크 수리도 프롬프트에 남는다 |
| 걸기 나. LLM이 걸고 코드가 해석·검증 | Ar9av, AgriciDaniel, kfchou, openwiki, nashsu, inkeep, mindbase v2 | 어느 D2와도 맞는다. 깨진 링크와 orphan은 결정적으로 나온다. 빠진 링크는 LLM 판단에 남는다 |
| 걸기 다. 코드가 걸 자리를 찾고 agent가 넣는다 | inkeep `links({kind:'suggest'})` | D2 가에서 코드가 쓰기 권한 없이 거들 수 있는 자리다. 넣을지는 agent가 정한다 |
| 걸기 라. 코드가 제목 매칭으로 직접 건다 | atomicstrata(LLM 제안 + 결정적 매칭·수리), mindbase v1(점수 6 이상 자동 기록) | D2 다·라처럼 코드가 쓰는 경로가 있어야 한다. 제목 문자열 일치에 기댄다. atomicstrata는 증분에서 O(바뀐 수 × 전체), 전체 재compile에서 O(전체²)다 |
| 타입 가. 타입 없음 | Astro-Han(명시적 거절), OKF | 지어낼 칸이 적다. 관계의 뜻은 문장에만 남는다 |
| 타입 나. frontmatter 필드에 관계를 둔다 | Ar9av `relationships:` 7종, inkeep `supersedes`·`superseded_by` | D6에서 frontmatter를 골라야 한다. Ar9av lint는 대상 존재·모호성·자기참조를 본다. inkeep은 frontmatter 경로를 backlink·audit에서 보지 않는다 |
| 타입 다. 페이지 밖 store에 관계를 둔다 | atomicstrata profile relation store(`wiki/graph/`), mindbase v1 sqlite `links` 표 | D6의 페이지 밖 장부와 짝이다. 본문 링크와 store를 잇는 대조가 따로 필요하다 |

[추정] 코드가 링크를 직접 넣는 곳은 코드가 페이지를 쓰는 경로를 가진 구현뿐이다 — 사례 3개: atomicstrata와 mindbase v1은 코드가 쓰는 경로에서 링크를 넣는다. agent가 직접 쓰는 inkeep은 걸 자리를 코드가 찾아도 agent가 `edit`로 넣는다.

[추정] 관계의 타입은 관찰한 곳에서 LLM이 고른다 — 사례 2개: Ar9av `relationships:`는 ingest에서 LLM이 쓰는 frontmatter다. mindbase v1은 LLM `link` 도구가 `contradicts`·`supersedes` edge를 넣는다.
그래서 typed 관계를 D7의 supersede·모순 판단에 쓰려면 타입 값도 검사 대상에 넣어야 한다.
D7의 "표시 안의 값도 검사 대상에 넣어야 한다"와 같은 조건이다.

[추정] link parser는 한 곳에 둬야 한다 — 사례 2개: #6. Link 절의 kfchou `wiki-merge`와 OKF 명세·생성 prompt·viewer 세 갈래.

### D12. 실행 형태와 연산당 비용 상한

D5·D8·D10에 묶인다.
D5에서 줄 범위나 코드 계산 version을 고르면 근거를 붙이는 코드가 LLM 출력 경로에 있어야 한다.
D8에서 결정적 재생성을 고르면 스크립트나 CLI가 있어야 한다.
D10에서 hybrid를 고르면 embedding을 갱신할 자리가 있어야 한다.
여기서 비용 상한은 연산 하나가 LLM을 몇 번 부르고 프롬프트에 무엇을 얼마나 넣는지의 상한이다.
설계 축은 #1. 실행 형태와 #14. 규모·비용이다.

[확인] 9개 구현 어디에도 ingest 1회의 토큰·시간·금액 측정값이 없다(#14. 규모·비용).

| 선택지 | 참고 repo | 조건 |
|---|---|---|
| 형태 가. 프롬프트 skill + 보고용 스크립트 | Astro-Han | D5 literal 일치, D8 LLM 손 갱신, D10 index + grep과 맞는다. 상한도 프롬프트 문장뿐이다 |
| 형태 나. skill + 결정적 CLI·스크립트 | Ar9av, AgriciDaniel, kfchou | D8 결정적 재생성을 스크립트로 둘 수 있다. CLI를 부를지는 프롬프트에 달린다. LLM 호출은 host agent가 쥔다 |
| 형태 다. CLI·SDK 엔진(+MCP) | atomicstrata, openwiki | D5 줄 범위·코드 version을 코드가 붙인다. 연산당 호출 수를 코드가 정한다(atomicstrata는 source당 추출 1회, concept당 생성 1회) |
| 형태 라. MCP 서버 + 웹 UI | mindbase | 웹 ops engine은 연산당 LLM 1회 + 실패 시 재시도 1회로 묶었다. 같은 저장소의 v1 compile은 tool loop 최대 10회, query는 최대 3회다 |
| 형태 마. 데스크톱 앱·IDE | nashsu, inkeep | D10 hybrid와 감시 ingest를 붙이기 쉽다. 앱이나 상시 서버가 돌아야 한다 |
| 상한 가. 연산당 호출 수 | mindbase 웹 ops(1회 + 재시도 1회), openwiki(할 일 없으면 0회, worker 2회 실패 시 skip), nashsu(queue 작업당 시도 3번) | 코드가 LLM을 부르는 경로에서만 코드로 센다 |
| 상한 나. 연산당 페이지 수 | Ar9av `OBSIDIAN_MAX_PAGES_PER_INGEST` 기본 15(skill 문서가 지시), mindbase lint 40페이지 | 무엇을 남길지 기준을 함께 정한다. nashsu는 소스 하나가 건드리는 페이지 수에 코드 상한이 없다 |
| 상한 다. 프롬프트 입력 크기 | atomicstrata(원문 100,000자, link target 목록 8,000자), OKF PoC(markdown 40KB) | 넘친 부분이 빠진다. atomicstrata는 원문 자르기를 frontmatter `truncated`로 남기지만, link 목록에서는 큰 wiki의 일부 페이지가 빠진다 |
| 상한 라. 사람과 예산을 먼저 합의 | AgriciDaniel(원문 수·바이트·페이지) | D4의 ingest 전 상의와 짝이다 |
| 상한 마. 할 일이 없으면 건너뜀 | Ar9av·atomicstrata·nashsu(원문 hash), openwiki(모델 0회) | 원문 hash나 변경 baseline을 상태 파일에 둬야 한다 |

[추정] 호출 수 상한을 코드로 강제하려면 엔진이 LLM을 직접 불러야 한다 — 사례 4개: 호출 수를 코드로 묶은 mindbase 웹 ops, openwiki, atomicstrata는 모두 엔진이 LLM을 부른다. host agent가 LLM을 쥔 Ar9av는 페이지 상한 15를 skill 문서에 둔다.

[추정] 상한은 호출 수만이 아니라 wiki 전체를 읽는 단계에도 걸어야 한다 — 사례 5개: #14. 규모·비용 절 끝의 4개(atomicstrata extraction의 index 전문, kfchou 전 페이지 backlink 점검, Astro-Han cascade, Ar9av query의 index 전체 읽기)와 nashsu 의미 lint(전 페이지 앞 500자를 한 프롬프트에 넣는다).

[추정] 입력을 개수로 자를 때는 무엇을 남길지 기준을 같이 정해야 한다 — 사례 2개: atomicstrata page prompt의 "관련 페이지 5개"는 `readdir` 결과의 앞 5개다. mindbase lint의 40페이지는 디렉터리 순서다.

### 어울리는 조합과 부딪히는 조합

관찰한 장치를 엮어 만들 수 있는 조합 셋을 예로 든다.
조합 그대로 돌아가는 구현은 없다. 각 조합은 여러 repo의 장치를 모은 것이다.
[추정] 세 조합은 각 결정이 서로의 전제를 깨지 않는다 — 사례: 조합마다 참고 repo 안에서 같은 결정끼리 함께 쓰인 예가 하나 이상 있다(kfchou의 commit gate + 결정적 index, AgriciDaniel의 초안 + 엔진 적용, openwiki의 코드 version + drift 재검토).
결정마다 섞어 고를 수 있다.

| 조합 | 결정 | 참고 repo | 약한 곳 |
|---|---|---|---|
| 가벼운 skill + git gate | D1 불변, D2 나, D3 commit, D5 literal 또는 줄 범위 + 스크립트 대조, D8 결정적 index + trailer log, D9 pre-commit | Astro-Han 검사기 + kfchou 스크립트·hook + Ar9av `memory sync` | raw 불변을 hook으로 지켜야 한다. `--no-verify`가 남는다 |
| agent는 초안, 엔진이 적용 | D2 다, D3 checkpoint, D4 계획 승인(사람 채널), D5 claim ledger 필수, D9 결정적 lint | AgriciDaniel + mindbase action 어휘 + nashsu 쓰기 직전 gate 설계 | 엔진과 bundle 작성 부담. PreToolUse hook과 적용 함수 안 승인 검사가 둘 다 필요하다 |
| 엔진이 LLM을 부르는 compiler | D1 가변, D2 라, D5 claim ledger + 코드 version, D7 drift 강제 재검토, D8 전부 결정적 | openwiki claims core + atomicstrata citation·journal | 대화하며 ingest하는 원형을 잃는다. 엔진 규모 |

관찰한 실패에서 부딪히는 조합은 아래와 같다.

| 부딪히는 조합 | 무엇이 깨지나 | 사례 |
|---|---|---|
| 자동 감시 ingest + 쓰기 전 대화형 ingest | 두 경로에 같은 기능을 따로 엮어야 한다. 한쪽을 걷어 내면 쓰기 전 사람 검토가 사라진다 | nashsu는 대화형 경로를 걷어 냈다. 주석은 이유로 기능 이중 연결과 사용자 혼란을 든다(`sources-view.tsx:361-367`). 남은 사람 개입은 사후 review 큐다 |
| 프롬프트로만 지키는 raw 불변 + "불변이라 hash 불필요" | 전제가 깨지면 근거도 무너진다 | Astro-Han |
| 선택형 claim ledger + ledger 기반 규칙 | 장부를 빼면 규칙이 안 걸린다 | AgriciDaniel |
| agent가 쓸 수 있는 승인 필드 + 그 필드로 매긴 신뢰 등급 | 등급을 스스로 올린다 | OKF `human:`, Ar9av `--approved` |
| 줄 범위 인용 + 계속 고치는 원문 + 재배치 없음 | 인용이 조용히 어긋난다 | openwiki가 context hash로 푼 문제 |
| 답 되저장 + 그 답을 소스로 재-ingest | 파생물이 원본 자리에 들어간다 | nashsu Save to Wiki |
| 같은 wiki에 쓰는 엔진·layout 둘 | 검색이 자기 결과를 못 찾는다 | mindbase |
| 전체 재작성 업데이트 + 사람 손 편집 | 손 편집이 다음 compile에서 사라진다 | atomicstrata |
| lint 보고서를 lint 대상 디렉터리에 | 보고서가 다음 lint와 gate를 오염시킨다 | kfchou |
| index를 길이로 잘라 프롬프트에 넣기 + 생성이 기존 페이지 인식을 index에 맡김 | 같은 주제의 중복 페이지가 생긴다 | nashsu |

## 확인하지 못한 것

| 무엇 | 왜 모르나 | 무엇을 보면 아나 |
|---|---|---|
| 테스트 통과 여부, 생성 품질, ingest 비용 | 이 문서와 repo별 보고서 모두 repo 코드를 실행하지 않았다 | 같은 소스 묶음을 구현마다 ingest하고 transcript·토큰을 잰다 |
| LLM이 프롬프트 규칙을 실제로 얼마나 지키는가 | 프롬프트 규칙이 대부분이지만 위반 빈도 자료가 없다 | 같은 소스로 여러 번 ingest해 diff를 비교한다 |
| literal grep과 줄 범위 인용의 오류 포착률 차이 | Astro-Han의 "value absent from the source" 관찰은 표본 크기가 없다 | 오류를 심은 fixture wiki에 두 검사기를 돌린다 |
| index만으로 버티는 규모 한계 | 모든 수치가 짐작이다 | 페이지 수를 늘려 가며 query recall을 잰다(Ar9av `eval`이 도구로 쓰일 수 있다) |
| openwiki 재배치가 실제 편집에서 unresolved로 떨어지는 빈도 | shallow clone이라 이력을 셀 수 없었다 | 전체 clone의 자기 wiki 이력에서 unresolved 수를 센다 |
| 사람 승인 우회의 실제 가능성 | atomicstrata TTY gate를 pty를 다루는 agent가 통과하는지, Ar9av `/mcp`가 key 없이 응답하는지 실행하지 않았다 | 각 경로를 격리 환경에서 실행한다 |
| 보고서가 읽지 않은 코드 | atomicstrata 플랫폼 계층 약 56k줄, nashsu agent runtime, inkeep 앱 실행 동작, mindbase v1 lint(`compileL2`) | 해당 디렉터리를 읽는다 |
| 00-discovery의 고려 후보 | CodeWiki, sage-wiki, kytmanov(사람 손 편집 보존, 작업마다 git commit) 등은 분석하지 않았다. 사람 손 편집 보존 축은 이 10개에서 mindbase v1 `human_touched` 말고는 사례가 적다 | 해당 저장소를 같은 16축으로 본다 |

이 문서가 repo 코드를 직접 다시 연 곳은 아래 표의 아홉 줄이다.
나머지 `[확인]`은 repo별 보고서의 확인을 옮겼다.

| 다시 연 곳(`lab/repos/` 아래) | 본 것 |
|---|---|
| `Astro-Han_karpathy-llm-wiki/scripts/check_evidence.py:28`, `:427` | docstring의 "The exit code carries no information; the report is the interface."와 `main()`의 `return 0` |
| `AgriciDaniel_claude-obsidian/claude_obsidian/transaction.py:4521-4531` | `approved_plan_sha256 is not None`일 때만 hash를 비교한다 |
| `langchain-ai_openwiki/src/claims/core/mutations.ts:86-96` | confirm은 기존 evidence를 다시 resolve해 version만 새로 계산한다 |
| `atomicstrata_llm-wiki-compiler/src/compiler/compile-write.ts:98-105` | compile이 `kind: "raw"`, `allowOverwrite: true`로 planner를 부른다 |
| `nashsu_llm_wiki/src/lib/ingest.ts:447-463` | `isSafeIngestPath`가 `wiki/`로 시작하지 않는 경로를 거부한다. 주석은 "the only tree the ingest pipeline writes to"라고 적는다 |
| `nashsu_llm_wiki/src/components/sources/sources-view.tsx:361-367` | 대화형 ingest를 걷어 낸 이유로 auto-pipeline과의 기능 이중 연결, 그리고 다시 돌리기를 기대한 사용자의 혼란을 든다 |
| `frankchu91_mindbase-llm-wiki/apps/plugin/hooks/hooks.json` | plugin hook은 `SessionStart` 하나뿐이다. `PreToolUse`가 없다 |
| `frankchu91_mindbase-llm-wiki/apps/server/src/ops/runner.ts:306`, `:633`, `apps/server/src/routes/ask.ts:87-89` | research·build·autoSave가 모두 `applyActions`로 쓴다. 즉 action executor는 지난다 |
| `langchain-ai_openwiki/openwiki/` | `du`로 `.claims/` 1.7MB를 확인했다. `.claims/` 밖 markdown 본문은 합쳐서 약 0.6MB(608,359바이트)다 |

## 검증 기록

repo 코드는 다시 열지 않았다. 아래 항목은 같은 폴더의 repo별 보고서와 대조해 고친 것이다.

- #한눈에 표 아래에 #repo별 한 바퀴 표를 더했다. 각 칸은 repo별 보고서의 #한 바퀴 흐름을 그 보고서 #검증 기록의 정정에 맞춰 줄였다. OKF 줄은 명세가 처방하는 것을 적었다.
- #내 llm-wiki를 설계할 때 정해야 할 결정들에 D11(Link를 누가 걸고 타입을 붙이는가)을 더했다. 근거는 #6. Link와 repo별 보고서의 #6이다.
- #내 llm-wiki를 설계할 때 정해야 할 결정들에 D12(실행 형태와 연산당 비용 상한)를 더했다. 근거는 #1. 실행 형태, #14. 규모·비용, repo별 보고서의 #14다.
- 결정 순서 표에 D11·D12 줄을 더했다. D2·D5·D6·D8·D10의 "뒤 결정에 거는 제약" 칸에 두 결정을 넣었다. 결정 수를 10개에서 12개로 고쳤다.

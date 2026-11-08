# llm-wiki 네 구현 깊이 읽기 — lab

jonex, AutoSci, sage-wiki, GD4AI 네 레포가 llm-wiki를 어떻게 구현했고 왜 그 구조를 골랐는지 코드·이력·외부 자료로 조사한 자료다.
사내 다중 작성자 보고서를 잇는 엔터프라이즈 llm-wiki를 설계할 때 차용할 것을 찾으려고 모았다.

## 읽는 순서

1. `../overview.md` — 네 레포의 큰 구조와 기능을 한 장에서 견준다. 레포별 보고서보다 먼저 읽는다.
2. `reports/<repo>.md` — 레포 하나의 큰 구조, 한 바퀴 흐름, 설계 이유, 축 16개, 엔터프라이즈 관점. 끝의 `## 검증 기록`은 반박 검증이 고친 내용이다.
3. `notes-raw/<repo>/<갈래>.md` — 보고서의 원재료. 보고서 문장의 근거를 더 캐고 싶을 때만 연다.

보고서의 `path:line`은 아래 commit 기준이고 레포 루트에서 센다.
보고서는 코드를 읽고 쓴 것이고, 어떤 레포도 실행하지 않았다.

## repos/ — 참고 저장소 (gitignore 됨)

`repos/` 아래 네 항목은 `../../llm-wiki-implementations/lab/repos/`의 클론을 가리키는 심볼릭 링크다.
앞선 schema·용어집 조사와 같은 클론을 쓴다.
2026-10-11에 네 클론 모두 전체 이력과 원격 브랜치·태그를 받았다(`git fetch --unshallow`).

링크가 깨졌거나 처음부터 받을 때는 `../../llm-wiki-implementations/lab/repos/`에서 실행한다.

```sh
for r in yuezhiai/jonex skyllwt/AutoSci xoai/sage-wiki GD4AI/obsidian-llm-wiki; do
  git clone "https://github.com/$r.git" "$(echo "$r" | tr / _)"
done
```

| 디렉터리 | 분석 시점 commit | 이력 | 라이선스 | 먼저 볼 곳 |
|---|---|---|---|---|
| `yuezhiai_jonex` | 5571db5 (2026-10-10) | 38 commits, 기본 브랜치 `mian` | Apache-2.0 수정판 | `Reference/JonexWiki/src/jonex_wiki/domain/engine/compile/`, `capabilities/knowledge_base/services/` |
| `skyllwt_AutoSci` | f5c2fe0 (2026-10-02) | 108 commits, 논문판은 태그 `arxiv-v1`·브랜치 `paper` | MIT | `.claude/skills/ingest/SKILL.md`, `tools/research_wiki.py`, `runtime/schema/` |
| `xoai_sage-wiki` | d3ef3a1 (2026-10-03) | 917 commits | MIT | `internal/compiler/`, `docs/guides/` |
| `GD4AI_obsidian-llm-wiki` | f41a39d (2026-10-09) | 1224 commits | Apache-2.0 | `src/wiki/wiki-engine.ts`, `src/core/` |

## 개요·커리큘럼 검증 기록

2026-10-11에 `../overview.md`, `../curriculum.md`, `../checklist.md`, `../my-thinking.md`를 세 관점으로 검증하고 고쳤다. 지적마다 근거를 레포 파일·보고서 줄·실행 결과로 다시 확인했다.

| 관점 | 대조 수 | 지적 | 반영 |
|---|---|---|---|
| 출처 대조(경로·줄·보고서 문장) | 293 | 13 | 13 |
| 새 세션 모의 진행(체크리스트 절차와 0·1단원을 lab-notes 규칙대로) | 46 | 23 | 23. auto-memory 수정 제안 1건은 이 폴더 밖이라 하지 않았다 |
| 내용(사용자 조건·목표에 비춘 빈자리) | 66 | 21 | 20. 1건은 일부만 반영 |

세 관점이 같은 문제를 짚은 것이 7쌍이라 실제로 고친 자리는 50곳이다.

고친 것은 아래와 같다.

| 무엇 | 어디 |
|---|---|
| 없는 경로 `internal/compiler/passes.go`를 `internal/linter/passes.go`로, 주장을 받치지 않던 `engine.py:58-60`과 `application.py:54-64`를 맞는 줄로, 디렉터리 없는 경로 셋을 전체 경로로 | overview, curriculum |
| GD4AI 0.9~13.9%를 "문구 사이 갈림"이 아니라 "문구마다 걸러진 비율"로. 성공 기준도 그 비율로만 견준다 | curriculum 2단원 |
| jonex LLM 몫에 Error Book 수리안, GD4AI 정체 판정 사다리, sage-wiki tier 0·1 차이를 보고서대로 | overview, curriculum 1단원 |
| 실험 묶음에 긴 혼합 문서·결정적 키 참조를 더하고, `docs.json`·`truth.json`·`glossary.json` 모양을 정함 | curriculum #실험 문서 묶음 |
| 0단원을 준비(corpus) + 기준선 회차 하나로. 회차 물음·지도 첫 줄·체크 칸을 맞춤 | curriculum 0단원, checklist |
| 1단원 실험의 어휘·검사기 셋(하나만 바꾸기)·enum 없는 schema·출력 모드 성공 기준(로컬 Ollama는 강등이 안 일어남) | curriculum 1단원 |
| Ollama 규칙: 갈림 실험은 temperature 0.7·seed 셋, 생성은 `think: false`, `done_reason` 기록 | curriculum #로컬 Ollama 모델 |
| 결정 E22 품질 측정과 회귀를 더함. E5에 입력 변환을 넣음. D10·D11·D12·D9 행을 my-thinking과 맞춤 | curriculum #결정 표, my-thinking |
| E 입장을 D 행에 옮기던 규칙을, 앞선 트랙 생각 기록에 덧붙이는 규칙으로(대신 쓰지 않기 위해) | curriculum, checklist, my-thinking |
| 4·6·8·9·10단원 읽을 것에 curation·pack·판 추적, 병합 guard·주 문서, 표 격자, 관문을 모은 예, Error Book·회귀 점검을 더함 | curriculum |
| 레포마다 구성 요소 표, #차용 지도 > 낮은 모델 운용 절, 판단 문장의 [추정] 표시 | overview |
| 세션 시작 절차: 경로를 붙인 시작 말, 공통 절 읽기, 레포 이름이 찍히는 hash 명령과 checkout, `:latest` 이름 | checklist |

기각한 것은 하나다. 10단원의 목록 크기(0·50·500개) 측정을 1단원으로 옮기자는 제안이다. 1단원이 정하는 E4(실패 단위)는 목록 크기에 기대지 않고, 창 크기 근거는 3단원 `lab/03-window/`가 이미 잰다. 목록을 추출 프롬프트에 넣을지는 E21의 물음이라 10단원에 둔다. 같은 제안의 뒤 절반(7단원 조각 유사도 갈래를 조각 방식 넷으로 돌리기)은 반영했다.

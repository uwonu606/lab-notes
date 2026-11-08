# llm-wiki 커리큘럼 — 결정 12개를 앞 결정이 뒤를 묶는 순서로 단원 10개에 나눠 익히고, 마지막에 내 llm-wiki 첫 버전을 만든다

이 커리큘럼은 내 llm-wiki repo를 설계하려고 짰다.
단원 순서는 `lab/reports/00-comparison.md` #내 llm-wiki를 설계할 때 정해야 할 결정들의 결정 순서 표를 따른다.
그 표는 결정 12개(D1~D12)를 앞 결정이 뒤 결정을 묶는 순서로 놓았다.
앞 단원의 결정이 뒤 단원의 선택지를 줄인다.

## 단원 하나가 도는 방식

단원 하나는 lab-notes 스킬의 회차 1~2개다.

1. 단원의 **회차 물음**을 보고, 보고서나 코드를 읽기 전에 예측을 `notes.md`에 쓴다.
2. **읽을 것**을 읽고 **실험 후보** 가운데 하나를 돌린다. 실험 파일은 `lab/NN-이름/`에 둔다.
3. 예측과 결과를 견주고, 코드를 가리고 기제를 내 말로 설명한다. 여기까지가 lab-notes 회차다.
4. **생각 물음**에 답한다. 답은 `my-thinking.md` #생각 기록에 낱말 그대로 남는다.
5. 그 단원이 다루는 결정의 지금 입장을 `my-thinking.md` #지금 입장에 적는다. 정하지 못하면 `미정`과 그 이유를 적는다.
6. `checklist.md`의 그 단원에 체크한다.

입장은 그때의 근거로 세운 가설이다.
뒤 단원에서 근거가 흔들리면 그 결정을 다시 열고, `my-thinking.md`에 다시 연 이유를 적는다.

## 실험 규칙

- `lab/repos/` 아래 코드는 남의 코드다. 실행하기 전에 그 스크립트를 끝까지 읽는다.
- 남의 Python 스크립트는 `python3 -I <스크립트 경로> <인자>`로 돌린다. `-I`는 현재 디렉터리의 모듈을 끌어오지 않게 한다.
- 실험용 wiki(`raw/`, `wiki/` 같은 폴더)는 `lab/NN-이름/` 안에 내가 만든다. `lab/repos/` 안에서는 아무것도 만들지 않는다.
- npm install이나 앱 빌드가 필요한 실험은 하지 않는다. LLM 호출이 필요한 실험도 기본에서 뺀다. 필요하면 그 단원에서 따로 정한다.

---

## 0. 줄기 — 왜 RAG 대신 wiki인가

- 다루는 결정: 없음. 이 단원은 과제를 정한다.
- 회차 물음: (lab-notes 줄기 단계) 이 패턴은 어떤 문제 때문에 생겼을까? 그 문제는 지금도 있을까? 그때 대안은 무엇이었을까? 내 llm-wiki로 당장 하려는 것을 한 문장으로 쓰면?
- 읽을 것
  - `lab/sources/karpathy-llm-wiki-gist/llm-wiki.md` — 원본 idea file 전체
  - `lab/sources/frosk1-critique-comments.md` — 한계 7가지
  - `lab/reports/00-comparison.md` #원본이 정한 것과 비워 둔 것
- 실험 후보: 없음. 이 단원은 출처 대조다.
- 생각 물음
  - 내 자료는 무엇이고, 얼마나 자주 바뀌는가?
  - frosk1의 7가지 가운데 내 용도에서 가장 아픈 것은 무엇인가?
- 완료 기준: `notes.md`의 줄기와 과제가 채워졌다.

## 1. 원문과 쓰기 주체 — D1, D2

- 다루는 결정: D1 원문이 바뀌는가, D2 LLM에게 파일 쓰기를 맡기는가
- 회차 물음: LLM이 wiki 파일을 직접 쓰는 구현에서 "숫자는 원문에 있어야 한다"는 규칙이 깨지면 무엇이 그것을 알아차리는가? 아무것도 없다면 언제 드러나는가?
- 읽을 것
  - `00-comparison.md` #2 규칙의 위치, #D1, #D2
  - `lab/reports/astro-han-karpathy-llm-wiki.md` #한 바퀴 흐름, #2
  - `lab/reports/atomicstrata-llm-wiki-compiler.md` #2. 그리고 `lab/repos/atomicstrata_llm-wiki-compiler/src/compiler/prompts.ts:61-64`
  - `lab/reports/agricidaniel-claude-obsidian.md` #한 바퀴 흐름
- 실험 후보: `lab/01-evidence-check/`에 `raw/`와 `wiki/`를 손으로 만든다. 글 형식, 특히 원문을 가리키는 `Raw` 필드는 `lab/repos/Astro-Han_karpathy-llm-wiki/examples/`를 따른다. 글 한 편에서 원문 숫자 하나를 바꾼다. 그다음 `python3 -I lab/repos/Astro-Han_karpathy-llm-wiki/scripts/check_evidence.py lab/01-evidence-check`를 돌린다. 이 검사가 무엇을 잡고 무엇을 놓치는지, exit code가 몇인지 본다.
- 생각 물음
  - 내 wiki에서 LLM이 직접 파일을 써도 되는가? 안 된다면 무엇이 대신 쓰는가?
  - 원문은 한 번 넣으면 고정인가, 계속 고치는가?
- 완료 기준: D1·D2에 입장이나 `미정`이 적혔다.

## 2. 이력과 승인 — D3, D4

- 다루는 결정: D3 이력과 되돌리기를 git에 맡기는가, D4 사람은 어디서 승인하는가
- 회차 물음: pre-commit hook이 깨진 링크를 막는 구조에서, LLM이 막힌 commit을 통과시킬 길은 무엇인가?
- 읽을 것
  - `00-comparison.md` #9 사람 개입, #10 동시성·안전, #D3, #D4
  - `lab/reports/kfchou-wiki-skills.md` #한 바퀴 흐름, #2, #10
  - `lab/repos/kfchou_wiki-skills/skills/wiki-init/assets/bin/hooks/pre-commit` (8줄)
  - `lab/repos/AgriciDaniel_claude-obsidian/claude_obsidian/transaction.py:4516-4531` — 승인 hash가 주어졌을 때만 비교하는 자리
- 실험 후보: `lab/02-commit-gate/`에서 `git init`을 하고 kfchou의 `skills/wiki-init/assets/bin/`을 통째로 `bin/`에 복사한다. 스크립트는 `bin/`의 부모를 wiki 루트로 보고 `wiki/pages/*.md`와 `SCHEMA.md`를 찾는다. 그래서 이 둘을 손으로 만든다. 링크가 깨진 페이지를 stage한 뒤 `python3 -I bin/lint-mechanical.py --staged`의 exit code를 본다. 그다음 hook을 걸고 `git commit`이 막히는지, `git commit --no-verify`로 지나가는지 본다. hook 원본은 `uv run`을 부르니 `python3 -I`로 바꿔 쓴다.
- 생각 물음
  - 나는 매 쓰기마다 승인하고 싶은가, commit 때 한 번이면 되는가, 나중에 리뷰 큐로 보면 되는가?
  - 승인 표시를 agent가 스스로 만들 수 있다면 그 승인은 무엇을 막는가?
- 완료 기준: D3·D4에 입장이나 `미정`이 적혔다.

## 3. 근거 추적 단위 — D5

- 다루는 결정: D5 근거를 어떤 단위로 추적하는가
- 회차 물음: 원문 맨 위에 다섯 줄을 끼워 넣으면 `^[file:10-12]` 같은 줄 범위 인용은 어떻게 되는가? 원문에 글자 그대로 있는지 보는 검사는 어떻게 되는가?
- 읽을 것
  - `00-comparison.md` #5 근거 추적 단위, #D5
  - `lab/reports/atomicstrata-llm-wiki-compiler.md` #5
  - `lab/reports/langchain-ai-openwiki.md` #5. 그리고 그 보고서가 가리키는 context hash resolver 코드
- 실험 후보: 1단원의 `lab/01-evidence-check/`를 복사해 `lab/03-citation-drift/`를 만든다. 원문 앞에 줄을 끼워 넣는다. 줄 범위 인용이 가리키는 내용이 바뀌는 것을 손으로 확인한다. `check_evidence.py` 결과가 그대로인지도 본다. openwiki resolver는 코드를 읽고 같은 입력에서 무엇을 할지 예측한다.
- 생각 물음
  - 내 wiki에서 "이 문장의 근거"를 어디까지 거슬러 올라가야 하는가? 페이지인가, 원문 글자인가, 줄인가, 주장 하나인가?
  - 그 추적을 유지하는 비용(장부 파일, 갱신 작업)을 낼 만한가?
- 완료 기준: D5에 입장이나 `미정`이 적혔다.

## 4. 메타데이터와 포맷 — D6

- 다루는 결정: D6 메타데이터를 어디에 어떤 형식으로 두는가
- 회차 물음: OKF가 신뢰도와 낡음을 필드로 저장하지 않고 계산하게 한 이유는 무엇일까?
- 읽을 것
  - `lab/repos/GoogleCloudPlatform_knowledge-catalog/okf/SPEC.md` §4.1, §5 전체, §11
  - `lab/reports/okf-spec-and-methodologies.md`
  - `00-comparison.md` #3 저장 구조, #13 포맷 표준, #D6
- 실험 후보: `lab/04-frontmatter/`에 내 wiki 페이지 하나를 손으로 쓴다. frontmatter를 OKF §11 준수 조건과 한 줄씩 대조한다. 같은 페이지를 Ar9av의 출처 태그 방식으로도 써 보고 두 방식을 견준다. Ar9av 방식은 `lab/reports/ar9av-obsidian-wiki.md` #5에 있다.
- 생각 물음
  - frontmatter에 꼭 있어야 하는 필드는 무엇이고, 없어도 되는 필드는 무엇인가?
  - 장부를 페이지 밖 파일로 두는 것과 frontmatter 안에 두는 것 중 무엇이 내게 맞는가?
- 완료 기준: D6에 입장이나 `미정`이 적혔다. 내 frontmatter 초안이 `lab/04-frontmatter/`에 있다.

## 5. 낡음과 모순 — D7

- 다루는 결정: D7 낡음과 모순을 어떻게 다루는가
- 회차 물음: 새 소스가 기존 페이지의 주장과 어긋날 때, 덮어쓰기·supersede·사람 리뷰 가운데 무엇을 고르면 frosk1의 1번 한계(오류 누적)를 줄이는가?
- 읽을 것
  - `00-comparison.md` #8 stale·모순 처리, #D7
  - `lab/reports/langchain-ai-openwiki.md` #8 — drift가 난 주장마다 결정을 강제한다
  - `lab/sources/rohitg00-llm-wiki-v2-gist/llm-wiki.md` — supersession, 망각
  - `lab/repos/kfchou_wiki-skills/skills/wiki-init/assets/bin/check-contradictions.py`
- 실험 후보: 2단원의 뼈대(`bin/`, `wiki/pages/`, `SCHEMA.md`)를 복사해 `lab/05-contradiction/`을 만든다. 거기서 모순 flag가 달린 페이지와 해소된 페이지를 만든다. `check-contradictions.py`가 무엇을 근거로 막는지 본다. 이 검사가 LLM이 단 flag를 보는지, 내용을 보는지 가른다.
- 생각 물음
  - 낡은 주장을 지울 것인가, 남겨 두고 "대체됨"으로 표시할 것인가?
  - 모순을 최종 판정하는 것은 누구인가?
- 완료 기준: D7에 입장이나 `미정`이 적혔다.

## 6. index·log·lint — D8, D9

- 다루는 결정: D8 index와 log를 누가 만드는가, D9 lint를 어디까지 결정적으로 하고 gate로 쓰는가
- 회차 물음: index를 LLM이 손으로 고치는 방식과 스크립트로 다시 만드는 방식은 페이지 100개에서 각각 어떻게 어긋나기 시작할까?
- 읽을 것
  - `00-comparison.md` #7 Lint, #12 index·log 관리, #D8, #D9
  - `lab/reports/kfchou-wiki-skills.md` #12
  - `lab/reports/ar9av-obsidian-wiki.md` #12 — `memory sync`
  - `lab/repos/kfchou_wiki-skills/skills/wiki-init/assets/bin/generate-index.py`, `render-log.py`, `lint-mechanical.py`
- 실험 후보: 2단원의 뼈대를 복사해 `lab/06-index-log/`를 만든다. `wiki/pages/`에 페이지 몇 개를 만들고 `generate-index.py`를 두 번 돌린다. 출력이 같은지(결정적인지) 본다. git commit에 `Wiki-Op:` trailer를 달고 `render-log.py`가 log를 어떻게 그리는지 본다. 같은 폴더에서 `lint-mechanical.py`가 무엇을 잡는지도 본다.
- 생각 물음
  - log.md 파일을 따로 둘 것인가, git 이력으로 대신할 것인가?
  - lint 가운데 commit을 막아야 하는 것과 보고만 하면 되는 것은 무엇인가?
- 완료 기준: D8·D9에 입장이나 `미정`이 적혔다.

## 7. 검색, 답 되저장, link — D10, D11

- 다루는 결정: D10 검색 방식과 답 되저장, D11 Link를 누가 걸고 타입을 붙이는가
- 회차 물음: Karpathy는 "~100 sources"까지는 index.md만으로 충분하다고 했다. 내 wiki에서 그 한계는 페이지 몇 개쯤일까?
- 읽을 것
  - `00-comparison.md` #6 Link, #11 Query·검색, #D10, #D11
  - `00-comparison.md` #어울리는 조합과 부딪히는 조합 — 답 되저장 + 재-ingest 행
  - `lab/reports/nashsu-llm-wiki.md` #11 — Save to Wiki
- 실험 후보: `lab/07-index-scale/`에 페이지 N개짜리 가짜 wiki를 만드는 스크립트를 쓴다. N을 50, 200, 1000으로 바꾸며 `generate-index.py`가 만든 index의 크기를 잰다. 그 크기를 내가 쓸 모델의 컨텍스트와 견준다.
- 생각 물음
  - 질문에 대한 좋은 답을 wiki에 다시 저장할 것인가? 저장한다면 원문과 어떻게 구별하는가?
  - 링크는 LLM이 거는가, 코드가 제목을 맞춰 거는가? 링크에 타입(예: 반박한다, 확장한다)을 붙일 것인가?
- 완료 기준: D10·D11에 입장이나 `미정`이 적혔다.

## 8. 실행 형태와 비용, 그리고 설계 종합 — D12

- 다루는 결정: D12 실행 형태와 연산당 비용 상한
- 회차 물음: 지금까지 적은 입장들을 모으면 skill 하나로 되는가, CLI 엔진이 필요한가?
- 읽을 것
  - `00-comparison.md` #1 실행 형태, #14 규모·비용, #D12, #어울리는 조합과 부딪히는 조합
  - `00-comparison.md` #frosk1 비판 7가지 × 구현 대응 표
- 실험 후보: 없음. `my-thinking.md` #지금 입장 12줄을 부딪히는 조합 표와 한 줄씩 대조한다.
- 생각 물음
  - 내 입장 조합이 부딪히는 조합 표의 어느 행에 걸리는가? 걸린다면 어느 결정을 다시 여는가?
  - 소스 하나 ingest에 쓸 비용의 상한은 얼마인가?
- 완료 기준: D12에 입장이 적혔다. `my-thinking.md` #설계 한 장이 채워졌다.

## 9. 과제 시험 — 내 llm-wiki 첫 버전

- 다루는 결정: 없음. 앞 단원의 입장을 시험한다.
- 할 것: `my-thinking.md` #설계 한 장대로 새 repo의 뼈대를 만든다. 내 실제 소스 3개를 ingest하고, query 하나를 던지고, lint를 한 번 돌린다.
- 생각 물음
  - 설계대로 안 된 곳은 어디인가? 그것은 어느 결정의 근거가 흔들린 것인가?
- 완료 기준: 소스 3개가 ingest됐고 lint가 돈다. 흔들린 결정은 `my-thinking.md`에서 다시 열었다. lab-notes 스킬이 `notes.md`의 status를 `done`으로 바꾼다.

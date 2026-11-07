# 에이전트 planning·reasoning — 구조와 과정 조사

- 조사 날짜: 2026-10-25
- 물음: planning과 reasoning은 어떤 구조로 되어 있고 어떤 과정을 거쳐 나가는가. Qwen 32B로 사내 보고서를 잇는 과업에는 어떤 계획 자료형·판정 신호·replan 트리거·thinking 설정에서 출발해야 하나.
- 다루는 갈래: 여덟 개다. 처음 다섯은 추론 패턴(한 호출·짧은 루프), 에이전트 수준 계획, 학습된 추론(thinking 모델), 구현(프레임워크 소스·프롬프트), 질문 경로 계획(RAG·KG)이다. 보충 셋은 첫 수집을 검토한 비평가가 빈 곳으로 짚은 자리를 채웠다. 하나는 외부 검증기 결론의 원 출처, 하나는 30B급 오픈 모델의 deep research 에이전트, 하나는 산출물이 결과인 과제(위키 글쓰기·용어 정규화·KG 구축)다.
- 방법: 조사 에이전트 다섯이 갈래 하나씩 자료를 모아 항목 131개가 모였다. 반박 검증 에이전트가 갈래마다 원문(논문 HTML·PDF, 저장소 소스, 공식 문서)을 다시 열어 항목마다 판정했다. 48개는 수집한 서술 그대로 맞았고, 83개는 서술을 고쳐야 맞았다. 틀렸거나 끝내 열지 못한 항목은 없었다. 그다음 완결성 비평가가 빈 곳 셋을 짚었고, 보충 에이전트 셋이 그 자리에서 36개를 더 모았다. 같은 방식의 검증 결과는 외부 검증기 원 출처 14개(맞음 9, 고침 5), 30B급 오픈 deep research 12개(맞음 4, 고침 8), 산출물 과제 10개(맞음 1, 고침 9)였다. 보충에서도 틀림과 못 엶은 없었다. 작성 뒤에는 대조 에이전트가 본문의 인용 93개와 수치를 검증 결과와 맞춰 16곳을 고쳤다. 작성자(메인 세션)는 결론을 받치는 출처 여섯 개(Stechly 등 Table A2의 Graph Coloring F.N.R 113/118, Valmeekam 등의 VAL backprompt 41/50, CoG Table 2의 Qwen3-32B 33.36→57.15, IterResearch Table 2의 49.1 대 36.5, MiniMax-M2 블로그의 Tau^2 87 대 64, Qwen3-32B `tokenizer_config.json`의 `last_query_index` 규칙)를 저장된 원문에서 직접 다시 열어 맞는 것을 확인했다.

## 읽는 법

- 출처는 문장이나 표 안에 링크로 적는다. 링크가 붙은 서술은 반박 검증이 원문을 다시 열어 확인한 내용이다. 수집 때 서술이 틀렸던 항목은 고친 내용만 옮겼다.
- 수치는 검증 결과에 있는 것만 쓴다. 표의 수치에는 모델·과제·조건을 붙인다.
- 큰따옴표 안은 영어 원문 그대로이고, 괄호에 위치(절, 표, 파일:줄)를 붙인다.
- 실행하지 않고 여러 사례에서 끌어낸 판단에는 `[추정]`을 앞에 달고, 사례와 개수를 같은 문장 끝 괄호에 붙인다.
- "단서:"는 그 근거를 옮겨 쓸 때 함께 들고 가야 할 조건이다.
- 앞 조사 [로컬 LLM 에이전트 하네스](../local-llm-agent-harness/research.md)가 이미 다룬 수치는 다시 쓰지 않고 그 노트의 절을 가리킨다. 이 노트에서는 그 노트를 "앞 노트"라 부른다.
- 이 노트에 나오는 바깥 분야 용어는 아래 표에서 한 줄로 정의한다.

| 용어 | 뜻 |
|---|---|
| BFS · DFS · beam search | 트리를 층마다 넓게 훑기 / 한 가지를 끝까지 파고 막히면 되돌아오기 / 층마다 점수 상위 몇 개만 남기며 넓히기 |
| MCTS | 선택·확장·시뮬레이션·역전파를 되풀이해 유망한 가지에 탐색을 몰아주는 트리 탐색 |
| UCT | 평균 보상과 방문 횟수로 다음에 내려갈 자식을 고르는 MCTS의 선택 식 |
| bandit(LinUCB) | 선택지 하나를 고르고 받은 보상으로 다음 선택을 고쳐 가는 탐색-활용 알고리즘 |
| PDDL | 계획 문제를 상태와 행동의 선행조건·효과로 적는 형식 언어 |
| VAL · Fast Downward | PDDL 계획을 실행해 보고 맞는지 판정하는 검증기 / PDDL 문제를 푸는 기호 planner |
| HTN | 큰 작업을 미리 적어 둔 method로 하위 작업까지 쪼개 가는 계층 계획 |
| SFT · 증류 | 정답 예시를 따라 쓰게 하는 미세조정 / 큰 모델 출력을 작은 모델의 SFT 데이터로 쓰기 |
| RL · PPO · GRPO | 보상으로 정책을 고치는 학습 / critic 모델로 advantage를 추정하는 RL / 같은 질문에서 뽑은 출력 묶음의 보상 평균을 기준으로 advantage를 만드는, critic 없는 RL |
| DPO | 좋은 답·나쁜 답 쌍으로 보상 모델 없이 선호를 학습하는 방법 |
| REINFORCE | 샘플한 행동의 보상으로 그 행동의 확률을 직접 올리고 내리는 가장 단순한 정책 경사 |
| LoRA | 원래 가중치는 얼리고 작은 저랭크 행렬만 학습하는 미세조정 |
| 30B-A3B(MoE) | 전체 약 30B 중 토큰마다 약 3B만 켜지는 mixture-of-experts 모델 |
| PRM | 해답의 단계마다 맞는지 점수를 매기는 보상 모델 |
| Best-of-N · self-consistency | N개를 뽑아 검증기 점수가 가장 높은 것 고르기 / N개를 뽑아 답 다수결 |
| Pass@k · EM · F1 · Hits@1 | k번 중 하나라도 맞힌 비율 / 정답과 글자가 같은 비율 / 낱말 겹침 점수 / 1위 답이 정답인 비율 |
| BM25 | 낱말 빈도로 문서 순위를 매기는 고전 검색 점수 |
| entity linking | 문장 속 이름을 KG의 특정 노드에 잇는 일 |
| OpenIE | schema 없이 문장에서 (주어, 관계, 목적어)를 뽑는 정보 추출 |
| PPR(Personalized PageRank) | 시작 노드에서 그래프를 따라 확률을 퍼뜨려 노드 순위를 매기는 방법 |

## 결론

planning과 reasoning은 갈래가 달라도 같은 부품으로 돈다. 계획 생성기가 계획을 만들고, 선택자가 다음 행동을 고르고, executor가 실행하고, 판정기가 결과를 보고 계속·재시도·replan·종료 중 하나로 보낸다(#공통 골격).

방법들의 차이는 그 부품을 채우는 방식에서 난다. 계획 자료형, 계획이 사는 곳, 다음 행동을 고르는 주체, replan 트리거, 종료 조건, 다음 step에 생각을 넘기는가가 그 자리다.

판정기는 같은 모델의 자기평가보다 바깥 신호를 쓸 때 효과가 컸고, 이번에는 원 출처로 확인했다. [Stechly 등](https://arxiv.org/abs/2402.08115)에서 GPT-4 검증기는 Graph Coloring의 맞는 해답 113/118개를 틀렸다고 버렸다. [Valmeekam 등](https://arxiv.org/abs/2305.15771)에서는 VAL의 오류 되먹임으로 GPT-4가 이미 실패한 Blocksworld 50개 중 41개가 살아났다.

단서: compute를 맞춰 비교하면 낮은 예산에서는 다수결이 생성형 검증보다 효율적이었다([When To Solve](https://arxiv.org/abs/2504.01005)). sound 검증기 아래에서는 피드백을 길게 다듬는 것보다 재시도 횟수가 대부분 도메인에서 더 중요했다(#외부 검증기 결론의 원 출처).

계획을 문맥 밖 자료구조(DAG, 파일, outline, report)에 두면 경로 기록이 저절로 남는다. 그런데 30B급 모델에 그 형식을 프롬프트로만 시킨 근거는 엇갈린다. [WebWeaver](https://arxiv.org/abs/2509.13312)의 Qwen3-30B-A3B는 프롬프트만으로 인용 정확도 25.00이었다(검색 안의 URL 선택·요약·증거 추출은 GPT-oss-120b가 맡은 조건). 반대로 [CoG](https://arxiv.org/html/2609.12791)는 학습 없이 Qwen3-32B non-thinking의 평균 EM을 33.36에서 57.15로 올렸다.

[추정] 그래서 계획 형식은 짧게 두고, 형식과 불변식 검사는 코드가 맡는 쪽에서 출발한다(사례: WebWeaver 25.00, HiPER의 학습 없는 형식 부착 8.3%→2.9%, PlanRAG의 Llama2 0점, Gemini CLI tracker의 코드 검사 — 4개).

생각 보존에는 하나의 정답이 없다. 보존하도록 학습한 모델은 생각을 지우면 손해였다(MiniMax-M2 Tau^2 87 대 64). 생각을 버리고 report만 넘기도록 학습한 IterResearch는 같은 Qwen3-30B-A3B에서 이력을 쌓는 쪽(Mono)보다 높았다(평균 49.1 대 36.5).

[추정] 하네스는 모델이 학습된 보존 규칙을 그대로 따라야 한다(사례: MiniMax-M2, AutoForge, IterResearch, DeepSeek-V3.2의 user 메시지 흉내 경고 — 4개). 운영 후보인 Qwen3-32B의 템플릿은 도구 루프 안의 생각만 남긴다(#생각이 놓이는 자리와 보존 규칙).

산출물(위키 글, 정규화한 용어, KG 링크)이 결과인 과제에도 계획 단위로 outline, mind map, 용어 정의, task DAG를 쓰는 연구가 있다. 종료는 대부분 LLM 자기 선언에 고정 상한을 겹친 형태이고, '충분함' 판정의 정확도를 잰 연구는 찾지 못했다(#산출물이 결과인 과제).

사용자 맥락에서는 이 순서로 손댄다(#사용자 과업에 옮기기).

1. 판정 신호를 먼저 코드로 만든다. 용어집 일치, 스키마, 원문 문단 대조를 hard critic으로 둔다. 판정기가 약하면 그 위의 replan과 재시도가 모두 흔들리기 때문이다.
2. 단계는 코드로 고정한 파이프라인으로 두고, 노드마다 검증 함수와 재시도·replan 상한을 붙인다. LLM은 좁힌 후보 중에서 고르게만 한다.
3. 경로 기록은 도구 호출·관찰·인용을 1차 증거로 두는 그래프로 남기고, 생각 텍스트는 보조 필드로 둔다.
4. thinking 보존, 계획 형식(프롬프트 대 문맥 밖 구조), 검증기 모델은 실험축으로 두고 사내 정답셋에서 잰다.

## 공통 골격

아래 그림은 여덟 갈래가 공통으로 가진 부품과, 각 설계 축이 그림의 어느 자리에서 갈리는지를 한 장에 묶는다.

```
질문·과제
   │
   ▼
[입구 라우터] ── 바로 답 / 한 번 조회 / 계획 경로        ← (구조를 정하는 주체)
   │
   ▼
[계획 생성기] ──► 계획                                    ← (계획 자료형) (계획이 사는 곳)
   │
   ▼
[선택자] 다음 행동 하나를 고른다                          ← (다음 행동을 고르는 주체)
   │
   ▼
[executor] 도구·검색·코드 실행 ──► 관찰
                                     │
                                     ▼
                                 [판정기]                 ← (판정 신호)
              ┌──────────────────────┼───────────────────────┐
            통과                  노드 실패             정체·반복·불합격
              │                      │                       │
              ▼                      ▼                       ▼
         [종료 판정]           노드 재시도 ──► executor    replan ──► 계획 생성기
     ← (종료 조건)                                          ← (replan 트리거)

[생각 상태] step마다 다음 입력에 무엇을 넘길지 정한다     ← (생각 보존)
```

한 호출 안의 추론도 같은 모양이다. [Tree of Thoughts](https://arxiv.org/abs/2305.10601)가 붙인 이름으로 generator가 계획 생성기, evaluator가 판정기, search가 선택자 자리에 들어간다.

| 축 | 선택지 → 대표 항목 |
|---|---|
| 계획 자료형 | 자연어 텍스트(Plan-and-Solve, Magentic-One 계획) · 상태 붙은 목록(write_todos, Codex update_plan) · 변수 참조 목록(ReWOO #E) · DAG(LLMCompiler, Plan*RAG, VeriMAP) · 코드(AdaPlanner, LPKG, MindSearch) · 형식 언어(LLM+P의 PDDL, ChatHTN의 HTN) · relation path(RoG) · outline·mind map(STORM, Co-STORM, WebWeaver) · 매 round 다시 쓰는 report(IterResearch) |
| 계획이 사는 곳 | 프롬프트 안 텍스트(Self-Ask, ADK PlanReAct) · 그래프 상태 필드(LangGraph, CrewAI) · 도구가 든 목록(Codex, OpenHands task_tracker) · 파일(Gemini CLI plansDir·tracker, OpenHands PLAN.md) · 문맥 밖 그래프(Plan*RAG, MindSearch, Argus, GraphRAG DRIFT) |
| 다음 행동 주체 | 코드 router(LangGraph 조건 엣지, CrewAI decide_next_action) · LLM 구조화 출력을 코드가 따름(Magentic-One next_speaker, LLMCompiler joiner) · LLM 도구 호출(Claude Code, Codex, OpenHands) · 고정 탐색 알고리즘(ToT, LATS) · 학습된 정책(AutoMR, HiPER) |
| 판정 신호 | 자기평가(ToT value, Self-Refine) · 답 일치(Self-Consistency, rStar) · 문맥을 격리한 검증(CoVe) · sound 외부 검증기(VAL, Python assert, 단위 테스트) · 학습한 검증기(GenRM, ThinkPRM) · 약한 검증기 앙상블(Weaver) · 사람 승인(plan mode) |
| replan 트리거 | 없음(ReWOO, Plan*RAG, EAGLET) · 고정 주기(smolagents, Plan-and-Act) · 실행·assert 실패(ADaPT, AdaPlanner, DEPS) · 외부 검증 불합격(LLM-Modulo, VeriMAP) · 진척 정체 카운터(Magentic-One) · 관찰기 판정(CrewAI) · 모델 판단(write_todos, ADK REPLANNING) · 학습된 시점(HiPER switch) |
| 종료 조건 | 답 태그(Search-R1) · 판정 통과(LLM-Modulo hard critic) · 모델 선언(STORM, WebWeaver) · 횟수·토큰·시간 상한(Tongyi 추론 코드) · 새 결과 없음(KGGen, Infini Memory) · 자원 기반 조건(VMAO) · 학습된 종료 토큰(Argus) |
| 생각 보존 | 모두 보존(MiniMax-M2, RITE) · 도구 루프 안만(Qwen3-32B, DeepSeek-V3.2, harmony) · 모두 삭제(QwQ-32B) · 버리고 report·요약만(IterResearch, AgentFold) |
| 구조를 정하는 주체 | 설계자가 과제마다(ToT, GoT의 GoO) · 과제 시작 때 한 번(Self-Discover, MRP) · 단계마다(Meta-Reasoner, CoT2-Meta, AGoT) |

[추정] 시간이 지나며 두 축이 한쪽으로 움직였다. 구조를 정하는 주체는 설계자에서 단계마다 정하는 모델·학습 정책으로 옮겨 갔고, 생각 보존은 지우는 쪽에서 남기는 쪽으로 옮겨 갔다(사례: ToT·GoT → Self-Discover → CoT2-Meta·AutoMR, R1·QwQ 템플릿 → DeepSeek-V3.2·MiniMax-M2·OpenAI GPT-5.6 기본값 — 2개 흐름, 항목 10개).

## 층 한눈에

| 층 | 계획 단위 | 판정 신호 | replan·종료 | 절 |
|---|---|---|---|---|
| 추론 패턴 | 생각 문장, 트리·그래프 노드 | 자기평가, 다수결, 격리 검증 | 탐색 알고리즘의 가지치기·예산 | #추론 패턴 |
| 에이전트 계획 | 목록·DAG·코드·PDDL | 실행 결과, assert, 외부 검증기, 진척 판정 | 실패·검증 불합격·정체 카운터 | #에이전트 수준 계획 |
| 학습된 추론 | `<think>` 구간 | 학습 때 결과 보상 | 정책 안에서 결정, 답 태그·budget | #학습된 추론 |
| 구현 | 상태 필드·도구 목록·파일 | 코드 불변식 검사, 사람 승인 | stall counter·관찰기·사람 거부 | #구현 |
| 질문 경로 | 하위 질문·relation path·DAG | 충분성 판단, KG 실체화 | Judge·reflection·깊이 상한 | #질문 경로 계획 |
| 산출물 과제 | outline·mind map·정의·task DAG | LLM judge, 임계값 | 자기 선언 + 상한 | #산출물이 결과인 과제 |

## 추론 패턴

이 층은 한 질문 안에서 생각을 어떻게 펼치고 고르는지를 다룬다. 평가는 거의 모두 수학·퍼즐·멀티홉 QA처럼 답이 정해진 과제다.

### 사슬과 분해

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [CoT](https://arxiv.org/abs/2201.11903) | 중간 추론 문장이 적힌 예시 8개 | 호출 1번, 분기·검증 없음 | GSM8K standard 18 → CoT 57(PaLM 540B, 8-shot). 효과는 약 100B 이상에서만 |
| [Zero-shot CoT](https://arxiv.org/abs/2205.11916) · [Plan-and-Solve](https://arxiv.org/abs/2305.04091) | trigger 한 줄. PS는 plan을 먼저 쓰게 함 | 추론 호출과 답 추출 호출 2번 | GSM8K Zero-shot CoT 56.4 / PS 58.2 / PS+ 59.3 / 8-shot Manual-CoT 58.4(text-davinci-003, temperature 0) |
| [Least-to-Most](https://arxiv.org/abs/2205.10625) | 분해 프롬프트와 하위 문제 풀이 프롬프트 | 분해 한 번 → 앞 답을 붙여 차례로 풂 | last-letter 길이 12: CoT 31.8% 대 74.0%(code-davinci-002) |
| [PoT](https://arxiv.org/abs/2211.12588) · [PAL](https://arxiv.org/abs/2211.10435) | LLM은 코드를 쓰고 인터프리터가 계산 | 코드 생성 → 실행 → 값이 답 | PoT가 CoT보다 평균 약 12% 높음(수학 5개 + 금융 QA 3개) |
| [Self-Consistency](https://arxiv.org/abs/2203.11171) | 경로 m개 샘플 → 답 다수결 | 경로끼리 정보 교환 없음 | GSM8K 56.5 → 74.4(PaLM-540B, 40 샘플) |

Least-to-Most의 과정은 이렇다.

1. 분해 프롬프트로 원 문제를 쉬운 하위 문제 목록으로 나눈다.
2. 원 문제를 목록 맨 끝 하위 문제로 붙인다.
3. 첫 하위 문제부터 푼다. 답을 프롬프트 뒤에 덧붙이고 다음 하위 문제를 묻는다.
4. 마지막(원 문제) 답을 최종 답으로 낸다. 분해를 고치는 되돌아감은 없다.

CoT 저자들은 작은 모델에서 "We qualitatively found that models of smaller scale produced fluent but illogical chains of thought, leading to lower performance than standard prompting."라고 적었다(§3.2).

단서: Plan-and-Solve의 plan은 생성 텍스트 안에만 있어 아무도 따랐는지 검사하지 않는다. 프롬프트로 plan 단계를 붙이면 작은 모델이 떨어진 사례는 앞 노트 #고정 워크플로 대 자율 루프에 있다.

### 탐색 — 트리·그래프

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Tree of Thoughts](https://arxiv.org/abs/2305.10601) | 같은 LLM이 생성(sample/propose)과 평가(value/vote), BFS 또는 DFS | 단계마다 후보 k개 → 점수 → 상위 b개, DFS는 임계값 아래면 가지치고 부모로 | Game of 24 CoT 4% → ToT 74%(GPT-4, b=5). GPT-3.5는 3% → 19%. GPT-4 생성+GPT-3.5 평가 64%, GPT-3.5 생성+GPT-4 평가 31% |
| [Graph of Thoughts](https://arxiv.org/abs/2308.09687) | Prompter·Parser·Scoring·Controller. 정적 연산 그래프(GoO)와 추론 상태(GRS) | Generate·Aggregate·Refine·KeepBest를 GoO 순서로 | 정렬 중앙값 오류가 ToT2 대비 P=64에서 약 61%, P=128에서 약 69% 낮음(ChatGPT-3.5) |
| [RAP](https://arxiv.org/abs/2305.14992) | 같은 LLM이 agent와 world model, MCTS(UCT) | 선택 → 확장 → 시뮬레이션 → 역전파 | Blocksworld 평균 64%(LLaMA-33B). GSM8K RAP(10)+aggr 51.6 대 CoT+SC(10) 46.8 |
| [LATS](https://arxiv.org/abs/2310.04406) | ReAct를 MCTS 확장기로, value = LM 점수 + self-consistency, 실패 반성 메모리 | 아래 번호 목록 | HotpotQA EM ReAct 0.32 → LATS(CoT+ReAct) 0.71(GPT-3.5, k=50). HumanEval GPT-3.5 CoT 46.9 → 83.8 |
| [rStar](https://arxiv.org/abs/2408.06195) | 작은 모델 MCTS, 사람다운 행동 5종, 중간 자기평가 없음, 두 번째 작은 모델이 앞부분을 받아 이어 풀어 일치 확인 | 32 rollout → 후보 → 판별 → 선택 | GSM8K LLaMA2-7B 12.51% → 63.91%, LLaMA3-8B 47.23% → 85.52%(판별 Phi3-mini) |
| [Cumulative Reasoning](https://arxiv.org/abs/2308.04371) | Proposer·Verifier·Reporter, 검증된 명제만 DAG로 쌓음 | 제안 → 검증 → 답 가능하면 종료 | Game of 24 98%(GPT-4). MATH level 5 22.4% → 32.1%(GPT-4, 도구 없음) |
| [Atom of Thoughts](https://arxiv.org/abs/2502.12018) | 질문을 DAG로 분해 → 독립 노드는 풀고 나머지는 답이 같은 새 질문으로 수축, 이력 버림, judge가 셋 중 고름 | 수축한 질문이 뽑히지 않으면 멈춤 | GPT-4o-mini MATH 78.3 → 83.6, LongBench 57.6 → 68.5 |

LATS의 과정은 이렇다.

1. Selection: UCT로 루트에서 leaf까지 고른다.
2. Expansion: 행동 n개를 샘플하고, 환경이 각각 관찰을 돌려줘 자식 n개를 만든다.
3. Evaluation: 새 자식마다 LM 점수와 self-consistency로 value를 매긴다.
4. Simulation: value가 가장 높은 자식을 따라 terminal까지 간다. 성공이면 탐색을 끝낸다.
5. Backpropagation: 경로 위 노드의 방문 수와 value를 보상으로 갱신한다.
6. Reflection: 실패 terminal이면 LM이 반성을 써서 메모리에 넣고, 이후 agent와 value 함수의 문맥에 넣는다.
7. 예산(k 궤적)에 닿거나 과제를 성공하면 끝난다.

LATS 저자들은 ToT와의 차이를 "Our key distinction from ToT is that we obtain this value after obtaining the environmental feedback, improving value assignment."라고 적는다(§4).

한계는 "LATS assumes the ability to revert to earlier states in decision-making environments, which may not be universally applicable in all possible environments."다(§6).

rStar 저자들은 "Methods like RAP (Hao et al., 2023) use self-rewarding, but our study shows SLMs perform near-random self-rewarding (Appendix A.1)."라고 적는다(§3.1). 근거는 RAP 자기평가 보상을 무작위 값으로 바꿔도 GSM8K LLaMA2-7B가 24.34에서 22.90으로만 바뀐 실험이다(부록 Table 6).

AoT 저자들은 이력을 버린 대가를 "Unlike CoT-based approaches, which can recover from early errors by leveraging accumulated context, our Markov chain lacks such a fallback due to its memoryless nature."라고 적는다(§3.2).

단서: ToT 부록 B.2의 교차 실험은 GPT-3.5의 병목이 평가보다 생성이라고 결론 낸다.

단서: ToT 저자들은 "Deliberate search such as ToT might not be necessary for many existing tasks that GPT-4 already excels at"라고도 적었고(Limitations), GSM8K에서는 CoT 86 → ToT 90에 그쳤다.

단서: LangGraph의 [LATS 튜토리얼](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/lats/lats.ipynb)은 value를 이미 평균으로 저장한 뒤 UCT에서 visits로 한 번 더 나눠서(cell 6), 이름과 달리 평균의 평균을 쓴다.

[추정] 작은 모델로 탐색할 때 가지를 고르는 신호는 같은 모델의 자기평가가 아닌 쪽(환경 관찰, 다른 모델, 기호 검증)에서 와야 한다(사례: rStar 무작위 보상 실험, LATS의 관찰 뒤 평가, Huang et al.의 자기수정 하락 — 3개). 반대 사례: ToT 부록 B.2는 GPT-3.5의 병목을 생성 쪽으로 봤다. Cumulative Reasoning의 Verifier는 실험에서 같은 GPT-4를 역할 프롬프트로 쓴 것이라 사례에서 뺐다.

### 구조를 누가 고르나

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Self-Discover](https://arxiv.org/abs/2402.03620) | reasoning module 설명 39개에서 과제마다 SELECT → ADAPT → IMPLEMENT로 JSON 구조를 만듦 | 구조는 과제당 한 번, 문제마다 key를 채움 | GPT-4가 찾은 구조를 Llama2-70B에 적용: disambiguation QA 52% 대 CoT 42% |
| [MRP](https://arxiv.org/abs/2406.11698) · [RTR](https://arxiv.org/abs/2505.19435) | 시작 때 같은 LLM이 방법을 고름 / 학습된 predictor가 (모델, 전략) 조합의 정확도·토큰을 예측해 고름 | 선택은 한 번, 풀이 도중 전환 없음 | RTR 평균 82.5%, QwQ-32B 단독 대비 정확도 +2.5점·출력 토큰 60% 이상 감소 |
| [Meta-Reasoner](https://arxiv.org/abs/2502.19918) · [CoT2-Meta](https://arxiv.org/abs/2603.28135) | 생각을 펼치는 object-level과 조종하는 meta-level 분리. bandit이 전략을 고름 / controller가 Expand·Prune·Repair·Stop·Abstain | 아래 번호 목록 | Game of 24 GPT-4o-mini CoT 4 → Meta-Reasoner 89, Qwen3-8B 87(보상은 gemini-2.5-flash) |
| [AutoMR](https://arxiv.org/abs/2510.04116) | 작은 MLP가 hidden state를 보고 DAG skeleton의 edge 전략(Next, Reflect, Explore, Decompose 등)을 고름, REINFORCE로 학습 | 추가 LLM 호출 없음 | MATH-500 Qwen2.5-3B: CoT 61.6, MRP 63.8, Meta-Reasoner 65.4, rStar 67.0, AutoMR 69.6 |
| [Chain of Mindset](https://arxiv.org/abs/2602.10063) | Meta-Agent + mindset 네 개 + Context Gate(독립 LLM 두 개가 문맥을 골라 넘기고 결과를 요약해 돌려줌) | Plan-Call-Internalize 루프 | 63.28%, MRP 대비 +4.96(Qwen3-VL-32B). Context Gate를 빼면 −8.24 |
| [AGoT](https://arxiv.org/abs/2502.05078) · [FoT](https://arxiv.org/abs/2602.16512) | 'complex' 노드면 중첩 그래프를 재귀로 엶 / 실행 그래프와 reasoning 그래프 분리, 병렬·캐시 | 층마다 노드·edge·전략 생성 | AGoT 답 위치를 섞은 GPQA Diamond gpt-4o 39.4 → 57.6, 원판 gpt-4o-mini 54.6 → 55.1. FoT 평균 10.7배 가속 |
| [Buffer of Thoughts](https://arxiv.org/abs/2406.04271) | problem distiller → template 검색(유사도 δ 0.5~0.7) → 채움 → 새 template 증류 | 유사도가 δ 아래면 새 과제로 봄 | 다중 질의 방법 비용의 평균 12% |

CoT2-Meta의 과정은 이렇다.

1. frontier에서 UCB 점수로 노드를 고른다.
2. 전략 태그(Direct/Decompose/Verify)별로 다음 생각을 만든다.
3. oracle 프롬프트 하나가 정답 없이 경로만 보고 단계 점수를 매긴다(r_i = 0.2·Sem + 0.5·Log + 0.3·Fix).
4. controller가 Expand·Prune·Repair·Stop·Abstain 중 하나를 고른다.
5. 최고 가지가 τ_stop을 넘으면 멈춘다. confidence가 τ_abs 아래로 남으면 Abstain해 fallback으로 보낸다. 생성·평가·수리·제어 호출을 모두 센 예산이 떨어져도 끝난다.

CoT2-Meta 저자들은 결정 trace를 "The controller concentrates expansion at shallow depths, shifts toward pruning in mid-search, and increases repair and stop actions near trajectory completion."라고 요약한다(§3.4.1).

MRP 저자들은 작은 모델이 스스로 전략을 고를 때의 한계를 "when the model’s capabilities are limited, it cannot have sufficient awareness of its own reasoning abilities and the meta-issues behind the reasoning problems."라고 적는다(§3.2). Self-Discover 저자들도 "We tried zero-shot meta prompting Llama2 but observed low-quality structure outputs."라고 적었다(§5 각주 3).

Chain of Mindset 저자들은 Context Gate를 둔 이유를 "Directly transmitting the complete history leads to context pollution, while transmitting only instructions results in context starvation."라고 설명한다(§2.4).

FoT는 실행 그래프가 "It retains the full history of how an answer came together and which operations were involved."라고 적는다(§3.1).

[Demystifying Chains, Trees, and Graphs of Thoughts](https://arxiv.org/abs/2401.14295)는 이 축에 이름을 붙였다. "Specifically, derivation of a multi-prompt topology can be manual (fixed by user before the LLM reasoning), automatic (decided dynamically by the LLM), or semi-automatic"(§IV-E1).

단서: AGoT의 큰 이득은 답 위치를 섞은 판에서만 나왔다. 멀티홉 검색 QA에서는 EM이 IO보다 대개 낮았고(HotpotQA 51 대 54) 이득은 LLM 판정 지표에 몰렸다. Meta-Reasoner의 Qwen3-8B 결과는 보상 모델을 다른 모델이 맡은 조건이다.

[추정] 작은 모델에는 구조를 큰 모델이나 학습된 작은 정책이 정하고, 작은 모델은 그 구조를 채우게 하는 분업이 맞다(사례: Self-Discover의 Llama2 각주와 GPT-4 구조 전이, MRP의 GPT-3.5 분석, RTR, AutoMR — 4개).

### 자기평가와 자기수정

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Self-Refine](https://arxiv.org/abs/2303.17651) | 한 LLM이 생성·feedback·refine | feedback의 멈춤 지표나 반복 수로 종료 | 수학 GPT-4 92.9 → 93.1. ChatGPT feedback의 94%가 'everything looks good'. Vicuna-13B 단독 24.18% → feedback·refine만 ChatGPT로 바꾸면 40.5% |
| [Reflexion](https://arxiv.org/abs/2303.11366) | Actor·Evaluator·Self-Reflection, 반성 문장을 장기 메모리로 | 아래 번호 목록 | HumanEval pass@1 91%(GPT-4). starchat-beta는 기준선 0.26 = Reflexion 0.26 |
| [Chain-of-Verification](https://arxiv.org/abs/2309.11495) | 검증 질문마다 처음 답을 넣지 않은 별도 프롬프트로 답함 | 초안 → 검증 질문 → 따로 답 → 고친 답 | Wikidata 목록 precision 0.17 → 0.36(two-step, Llama 65B). 틀린 개체 2.95 → 0.68, 맞는 개체도 0.59 → 0.38 |
| [Huang et al.](https://arxiv.org/abs/2310.01798) | 외부 feedback 없는 자기수정을 그대로 재현 | 처음 답 → 자기 검토 → 다시 답(2회) | GSM8K Llama-2-70b-chat 62.0 → 43.5 → 36.5, GPT-4 95.5 → 91.5 → 89.0. 응답 6개: debate 83.2 대 self-consistency 85.3(gpt-3.5-turbo) |
| [Myopic Planning](https://arxiv.org/abs/2605.06840) | four-in-a-row 추론 trace를 탐색 트리로 바꿔 실제 수 선택과 견줌 | 트리 추출 → 계산 모델 적합 → CoT 문단 지우기 | 승률 회귀에서 폭을 통제하면 깊이는 유의하지 않음(depth β=−0.015, p=0.82; breadth β=0.075, p=0.0025) |

Reflexion의 과정은 이렇다.

1. Actor가 환경과 상호작용해 궤적을 만든다.
2. Evaluator가 점수를 매긴다(정답 일치, 휴리스틱, 단위 테스트, LLM 판정).
3. 실패면 Self-Reflection이 '무엇을 잘못했고 다음엔 무엇을 할지'를 써서 메모리에 넣는다. 메모리는 마지막 반성 3개로 자른다.
4. 환경을 리셋하고 Actor가 메모리를 문맥에 넣은 채 다시 시도한다.
5. 통과하거나 최대 시도 수에 닿으면 끝난다. ALFWorld에서는 같은 행동·응답이 3회 넘게 반복되거나 행동이 30개를 넘으면 반성을 일으킨다.

Huang et al.은 "The fundamental issue is that LLMs cannot properly judge the correctness of their reasoning."라고 결론 낸다(§3.3). Reflexion 저자들도 "We found that the ability to specify self-corrections is an emergent quality of stronger, larger models."라고 적었다(부록 A).

CoVe 저자들은 문맥을 격리한 이유를 "models that attend to existing hallucinations in the context from their own generations tend to repeat the hallucinations."라고 설명한다(§1).

Myopic Planning 저자들은 "Crucially, although LLMs expanded deep nodes, their move choices were best explained by a myopic model that ignores those nodes entirely."라고 적는다(§1). 보이는 깊은 생각이 결정에 들어가지 않을 수 있다는 뜻이다.

단서:

- Huang et al.의 결론은 도구·테스트 같은 외부 feedback을 쓰는 수정에는 해당하지 않는다고 저자들이 밝혔다.
- Reflexion의 HotpotQA 이득 상당 부분은 정답 label로 멈춤을 정한 설정에서 왔다.
- LangGraph의 [Reflexion 튜토리얼](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/reflexion/reflexion.ipynb)은 비판을 missing·superfluous 필드로 쪼개 쓰게 하지만 외부 evaluator는 빼고 반복 횟수(MAX_ITERATIONS=5)로만 멈춘다.

이 결론의 원 출처 검증은 #외부 검증기 결론의 원 출처에 모았다.

## 에이전트 수준 계획

이 층에서는 계획이 행동 열을 정하고, executor가 환경에서 그 행동을 실행한다. 항목들은 계획을 언제 만드는가(한 번, 실패할 때, 매 step, 모델이 고른 때)와 무엇이 replan을 일으키는가로 갈린다.

### 한 번 세우고 실행하기

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [ReWOO](https://arxiv.org/abs/2305.18323) | Planner가 (Plan, #E) 쌍을 한 번에 씀. Worker가 실행, Solver가 종합 | 아래 번호 목록 | HotpotQA 정확도 42.4·토큰 1,986.2 대 ReAct 40.8·9,795.1(gpt-3.5-turbo). 모든 도구가 'No evidence found.'를 주면 ReAct −40.8, ReWOO −29.2 |
| [LLMCompiler](https://arxiv.org/abs/2312.04511) | Planner가 DAG를 내고 Task Fetching Unit이 병렬 디스패치, Joiner가 Finish/Replan | 아래 번호 목록 | 지연 HotpotQA 1.80×, Movie Rec. 3.74× 단축(gpt-3.5-turbo). ParallelQA 정확도 59.59 → 68.14(LLaMA-2 70B) |
| [HuggingGPT](https://arxiv.org/abs/2303.17580) | JSON 작업 그래프(task, id, dep, args), `<resource>-task_id` 자리표시자 | 계획 → 모델 선택 → 실행 → 응답, replan 없음 | single task 계획 정확도 GPT-3.5 52.62 / Vicuna-7b 23.86 / Alpaca-7b 6.48 |
| [LLM+P](https://arxiv.org/abs/2304.11477) | LLM은 problem PDDL을 쓰고 Fast Downward가 풂, LLM이 다시 자연어로 | 번역 → 탐색 → 번역, 루프 없음 | Blocksworld 90% 대 LLM-as-P 15%·20%(gpt-4). 예시 없는 LLM+P는 7개 도메인 모두 0% |
| [Routine](https://arxiv.org/abs/2507.14447) | 전문가 초안을 번호 단계·분기 템플릿으로. 실행 모델은 도구 호출 하나씩, 단계를 건너뛰지 않음 | 유사도로 Routine 검색 → 단계 실행 → 요약 도구 | Qwen3-14B 32.6% → 83.3%(학습 없음), 증류 학습 뒤 95.5%. GPT-4o 41.1% → 96.3% |
| [EAGLET](https://arxiv.org/abs/2510.05608) | 학습한 전역 planner가 작업당 한 번 `<plan>`. 보상은 계획이 executor 완료율을 올렸는가 | 실행 중 planner 개입 없음 | Llama-3.1-8B-Instruct executor 평균 39.5 → 59.4 |
| [AdaPlan-H](https://arxiv.org/abs/2604.23194) | 난이도에 따라 층 수가 바뀌는 계층 계획을 한 번 생성 | SFT + DPO, replan 없음 | ALFWorld Unseen 0.5896 대 ReAct 0.1866(Llama-3.1-8B actor) |
| [Agentic Plan Caching](https://arxiv.org/abs/2506.14852) | (keyword, plan template) 캐시. 적중하면 작은 planner가 템플릿을 고쳐 씀 | 성공 실행 로그에서 엔티티명·수치를 지워 템플릿화 | 비용 50.31%·지연 27.28% 감소, 정확도는 최적의 96.61%. GAIA 비용 $69.02 → $16.27 |

ReWOO의 과정은 이렇다([LangGraph 판](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/rewoo/rewoo.ipynb) 포함).

1. Planner가 질문만 보고 'Plan: … #E1 = Tool[args]' 형식의 전체 blueprint를 한 번에 쓴다. 뒤 단계 인자는 '#E2 = LLM[What is x , given #E1]'처럼 앞 변수를 참조한다.
2. LangGraph 판은 정규식 하나로 계획을 (plan, #E, tool, input) 튜플로 자른다(cell 13).
3. Worker가 #E 순서대로 도구를 실행하고 앞 #E 값을 인자에 치환한다. 다음 단계는 코드(_route)가 결과 개수로 정한다.
4. Solver가 계획 문장과 채워진 증거 전체로 답을 쓴다.
5. replan은 없다. 저자들은 Solver가 "partially compensate for failures in the Planner or Worker"할 뿐이라고 적는다(§2.1).

LLMCompiler의 과정은 이렇다([저장소](https://github.com/SqueezeAILab/LLMCompiler) 커밋 a00c9d3).

1. Planner가 작업 DAG를 낸다. 의존 입력은 '$1' 같은 앞 작업 id 자리표시자다. 스트리밍이면 작업이 생성되는 대로 큐에 넣어 실행을 겹친다.
2. Task Fetching Unit이 LLM 없이 의존이 풀린 작업을 greedy하게 Executor로 넘기고, 자리표시자를 실제 값으로 바꾼다.
3. 작업이 끝나면 thought-action-observation이 스크래치패드에 쌓인다.
4. Joiner가 'Finish(답)' 또는 'Replan(이유)'을 낸다.
5. Replan이면 이전 계획·관찰·Joiner thought를 묶어 Planner를 다시 부른다.
6. `for i in range(self.max_replans):`(llm_compiler.py:242)가 전체 계획 횟수를 센다. 그래서 hotpotqa·parallelqa·movie 설정의 max_replans=1은 replan이 0회라는 뜻이다.

HuggingGPT 저자들은 "we cannot ensure that the generated plan will always be feasible and optimal"이라고 적는다(§5).

LLM+P 저자들은 예시의 역할을 "Therefore, the context is important for LLM+P to work."라고 정리한다(§V-C).

Routine 저자들은 "Without Routine guidance, all baseline models performed poorly, with none exceeding 50% overall accuracy."라고 적는다(§5.2.1).

단서: ReWOO는 계획이 '틀린 기대' 때문에 무력해질 수 있다고 저자가 App. A.2에서 인정했다. LLMCompiler의 replan은 DAG 전체가 끝난 뒤에만 일어난다. Routine은 HR 시나리오 하나(하위 시나리오 7개)로만 쟀다. 저자들은 새 도구나 절차 변경에 일반화가 약하다고 §6에 적었다.

### 실패할 때 쪼개거나 고치기

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [ADaPT](https://arxiv.org/abs/2311.05772) | executor가 'task completed/failed'를 스스로 보고. 실패하면 planner가 And/Or 하위 작업으로 쪼갬. controller는 LLM이 아닌 재귀 알고리즘 | 아래 번호 목록 | ALFWorld 71.6 대 ReAct 43.3, Plan-and-Execute 43.3, Reflexion 57.5(d_max=3). LLaMA-2-70B executor 단독 20.4 → GPT-3.5 planner를 붙이면 43.3 |
| [AdaPlanner](https://arxiv.org/abs/2305.16653) | 계획이 Python solution() 함수. 하위 계획 끝에 assert | assert가 맞으면 계획 유지, 실패하면 코드를 고쳐 중단점부터 이어 실행 | ALFWorld 91.79%(text-davinci-002). 코드 인터페이스를 빼면 ALFWorld 81% → 46% |
| [DEPS](https://arxiv.org/abs/2302.01560) | 하위 goal 실패 시 Descriptor가 상황 요약 → Explainer가 오류 위치 설명 → Planner 재계획 | goal마다 선행조건·효과 | Minecraft 71개 작업 평균 48.56% 대 CaP 25.77%(code-davinci-002) |
| [ChatHTN](https://arxiv.org/abs/2505.11814) | HTN planner가 적용할 method가 없을 때만 ChatGPT에 분해를 물음. 분해 뒤 verifier task 실행 | 검증 실패 가지는 버리고 다음 method로 backtrack | Full Domain 세 도메인 모두 ChatGPT 호출 0회. Unsolvable 문제는 해를 내지 않음 |
| [Voyager](https://arxiv.org/abs/2305.16291) | curriculum이 다음 작업 제안, 성공 코드를 skill library에, 별도 GPT-4 critic | 4라운드 막히면 다른 작업 요청 | self-verification 제거 −73%. 코드 생성을 GPT-3.5로 하면 고유 아이템 5.7배 적음 |

ADaPT의 과정은 이렇다.

1. controller가 executor에게 작업을 통째로 맡긴다.
2. executor가 성공을 보고하면 끝난다.
3. 실패를 보고하면 planner가 보통 3~5개의 하위 작업과 And/Or 논리를 만든다.
4. 하위 작업마다 깊이 k+1로 재귀한다. Or는 앞 하위 작업이 성공하면 뒤를 실행하지 않는다.
5. 깊이가 d_max를 넘으면 실패로 돌아온다. d_max=1이면 executor만 쓰는 ReAct 기준선과 같다.

ADaPT 저자들은 "ADaPT recursively decomposes sub-tasks to adapt to both task complexity and LLM capability."라고 적는다(Abstract).

AdaPlanner는 "If the assertion fails, AdaPlanner performs out-of-plan refinement."라고 replan 트리거를 계획 안에 심었다(§3.2).

ChatHTN 저자들은 "providing piecemeal queries provides better results than a single query with all requirements"라고 적는다(§4).

단서: ADaPT의 replan 트리거는 executor의 자기 성공 판정이다. WebShop에서는 그 판정이 환경 보상보다 30점 넘게 부풀어(App. F) 더 쪼개야 할 때 멈췄다. ChatHTN은 operator와 작업의 선행조건·효과를 사람이 미리 써 둬야 한다.

### 매 step 다시 쓰기와 계획 시점

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Plan-and-Execute](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/plan-and-execute/plan-and-execute.ipynb)(LangGraph) | 상태 {input, plan: List[str], past_steps, response}. planner(gpt-4o) → ReAct executor(gpt-4-turbo-preview) → replanner | 아래 번호 목록 | 튜토리얼에 수치 없음 |
| [Plan-and-Act](https://arxiv.org/abs/2503.09572) | Planner와 Executor를 따로 fine-tune, 매 Executor step 뒤 planner가 계획을 다시 씀 | 궤적에서 계획을 역으로 만든 학습 데이터 | WebArena-Lite: planner 없음 36.97% → 정적 43.63% → 동적 replan 53.94% → +CoT 57.58%(LLaMA-3.3-70B). QwQ-32B로 WebArena-Lite 54.88% |
| [Learning When to Plan](https://arxiv.org/abs/2509.03581) | 모델이 매 step 첫 토큰을 `<plan>`으로 낼지로 계획 여부를 정함, SFT → PPO | 새 계획이 없으면 직전 계획을 따름 | 성능이 중간 계획 빈도에서 가장 높음('Goldilocks', Llama-3.3-70B, POGS·Crafter). SFT 없이 RL만 하면 계획 안 하는 쪽보다 나쁨 |
| [HiPER](https://arxiv.org/abs/2602.16165) | 매 턴 `<switch>`(KEEP/SWITCH), `<subgoal>`, `<action>`. 계층 advantage로 학습 | SWITCH가 곧 replan | ALFWorld 97.4%, WebShop 83.3%(Qwen2.5-7B). 학습 없는 Qwen2.5-1.5B에 형식만 붙이면 ALFWorld 8.3% → 2.9% |

Plan-and-Execute의 과정은 이렇다.

1. planner가 목표에서 단계 목록을 structured output으로 만든다.
2. executor는 번호 붙은 계획 전체와 'You are tasked with executing step 1, {task}'를 받아 plan[0] 하나만 실행하고, (task, 결과)를 past_steps에 더한다.
3. 매 단계 뒤 replanner가 입력·원래 계획·past_steps를 보고 Response 또는 남은 단계만 담은 새 Plan을 낸다.
4. 코드(should_end)가 response 유무로 END와 executor를 가른다.
5. replan 상한은 없고 recursion_limit=50(cell 24)이 막는다.

replanner 프롬프트는 "Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."이다(cell 19).

튜토리얼은 이 구조의 장점으로 "Ability to use smaller/weaker models for the execution step, only using larger/better models for the planning step"을 든다(cell 0).

Learning When to Plan 저자들은 "the base model cannot learn to plan effectively through RL alone"이라고 적는다(§5.3). 프롬프트로 '필요할 때만 계획하라'고 시키면 모델이 늘 계획하거나 전혀 안 하는 쪽으로 쏠렸다고도 적었다(§5.1).

단서: Plan-and-Act의 동적 replan은 매 step 호출이 늘고, 학습 파이프라인(시연 에이전트, 필터, 교사 모델)이 무겁다. HiPER에서 형식의 이득은 RL 학습과 함께일 때만 나왔다(PPO +13.1%p, GiGPO +4.4%p). 저자는 학습 없는 1.5B의 하락을 지시 따르기 능력 부족으로 추정했다.

### 진척 판정과 외부 검증기

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Magentic-One](https://arxiv.org/abs/2411.04468) · [autogen](https://github.com/microsoft/autogen) | Orchestrator가 Task Ledger(사실 시트 네 칸 + 계획)와 Progress Ledger(JSON 다섯 필드)를 씀, 작업자 넷 | 아래 번호 목록 | GAIA test 38.00%(GPT-4o + Orchestrator outer loop·Coder에 o1-preview) 대 GPT-4o 단독 32.33%. ledger 없는 GroupChat식으로 바꾸면 31% 하락(GAIA validation) |
| [VeriMAP](https://arxiv.org/abs/2510.17109) | Planner가 하위 작업 DAG와 노드별 검증 함수(Python assert 또는 자연어 기준)를 함께 씀. Executor는 전역 작업을 못 봄 | 노드 검증 실패 → 노드 재시도 최대 3회 → 다 쓰면 실행 trace로 전체 replan, 상한 5회 | MultiHopRAG 78.20% 대 ReAct(gpt-4.1) 68.40%, replan을 뺀 판 75.40%. Olympiads 41.20% 대 40.80%(planner gpt-4.1, executor gpt-4o-mini) |
| [VMAO](https://arxiv.org/abs/2603.11445) | 하위 질문 DAG, verifier가 status·completeness·빠진 측면·recommendation을 냄 | 검증 뒤마다 종료 조건 다섯 중 하나라도 맞으면 합성 | 완결성 3.1 → 4.2(1–5, 질의 25개). 토큰 850K 대 100K. 75% 넘는 질의가 자원 기반 조건으로 멈춤 |
| [LLM-Modulo](https://arxiv.org/abs/2402.01817) | Generate-Test-Critique. hard critic(정합성), soft critic(선호), constructive critic, reformulator, meta controller | 최소한 모든 hard critic이 승인하면 출력 | 이 논문의 수치는 모두 다른 논문 인용이다. 원 출처 검증은 #외부 검증기 결론의 원 출처 |

Magentic-One의 바깥 루프와 안쪽 루프는 이렇게 돈다(커밋 004749e).

1. 바깥 루프: Orchestrator가 사실 시트(GIVEN OR VERIFIED FACTS / FACTS TO LOOK UP / FACTS TO DERIVE / EDUCATED GUESSES)를 쓰고, 팀 구성을 보고 짧은 bullet 계획을 쓴다.
2. 모든 작업자에 GroupChatReset을 보내고 Orchestrator 대화 스레드를 비운 뒤 Task Ledger를 방송한다(_magentic_one_orchestrator.py:262-272).
3. 안쪽 루프: 매 턴 Progress Ledger JSON {is_request_satisfied, is_in_loop, is_progress_being_made, next_speaker, instruction_or_question}을 각각 reason과 answer로 채운다. 파싱이 실패하면 최대 10회 다시 시도하고, 그래도 실패하면 실행이 끊긴다.
4. is_request_satisfied면 최종 답을 준비해 끝낸다.
5. 진척이 없거나 loop면 n_stalls를 1 올리고, 아니면 1 내린다(0 아래로는 안 감).
6. n_stalls가 max_stalls(코드 기본 3)에 닿으면 사실 시트를 고치고 '무엇이 잘못됐는지'를 쓴 새 계획으로 1번에 돌아간다(:402-403).
7. 아니면 next_speaker에게 instruction을 보내고 응답을 받아 3번으로 간다. max_turns(코드 기본 20)를 넘으면 끝난다.

loop 판정 질문은 "Are we in a loop where we are repeating the same requests and / or getting the same responses as before?"이다(_prompts.py:71).

replan 프롬프트는 "Please briefly explain what went wrong on this last run (the root cause of the failure), and then come up with a new plan that takes steps and/or includes hints to overcome prior challenges and especially avoids repeating the same mistakes."이다(_prompts.py:133).

논문은 재계획 때 문맥을 비우는 이유를 "we force all agents to clear their contexts and reset their states after each plan update"라고 적는다(§4.1). 논문의 '임계 2까지는 진행, 넘으면 replan'과 코드의 '3에 닿으면 replan'은 같은 동작이다.

VeriMAP은 "If a node fails verification after all retries, the coordinator will collect execution traces and trigger replanning"이라고 retry와 replan의 경계를 정했다(§2.4).

VMAO는 "When any condition is met, the system proceeds to synthesis."라고 종료를 정했다(§3.3). 조건은 하위 질문 80% 완료, 신뢰 75%+완료 50%, 개선 5% 미만, 1M 토큰, 3회 반복이다.

LLM-Modulo는 "If at least all the hard critics sign off on the current candidate"를 종료로 둔다(§3.1).

단서: Magentic-One의 31% 하락은 ledger·계획·진척 추적·loop 탐지·명시적 지시를 한꺼번에 뺀 ablation이라 재계획만의 효과는 분리되지 않았다. 상대값인지 절대값인지도 적혀 있지 않다. VMAO는 질의 25개이고 평가자(Opus 4.5)와 실행자(Sonnet 4.5)가 같은 계열이다.

### 평가 벤치가 말하는 것

| 출처 | 무엇을 쟀나 | 과정 | 수치(조건) |
|---|---|---|---|
| [LLMs Still Can't Plan; Can LRMs?](https://arxiv.org/abs/2409.13373) | PlanBench Blocksworld와 이름만 바꾼 Mystery판, o1 | 계획 출력 → 자동 검증 | Mystery Blocksworld에서 5% 넘는 LLM 없음. o1-preview Blocksworld 97.8%, Mystery 52.8%, Randomized Mystery 37.3%. 6~20블록 110문제 23.63% |
| [TravelPlanner](https://arxiv.org/abs/2402.01622) | 닫힌 sandbox와 제약 세 부류 | ReAct 수집 → 계획 작성, 30 step 상한 | two-stage 최종 통과율 0.6%, sole-planning Direct 4.4%(GPT-4-Turbo) |
| [NATURAL PLAN](https://arxiv.org/abs/2406.04520) | 도구 출력을 문맥에 넣고 계획 능력만 | 5-shot → EM 채점 | Trip 31.1/34.8(GPT-4/Gemini 1.5 Pro). 도시 10개면 다섯 모델 모두 5% 미만 |

NATURAL PLAN 저자들은 "Self-correction leads to significant model performance drop across all models."라고 적는다(§4.4). TravelPlanner 저자들은 "Agents struggle to align their actions with their reasoning."라고 적는다(§5.3).

단서: Mystery Blocksworld는 의미가 같은 문제의 이름만 바꾼 것이다. 작성자마다 용어가 다른 보고서는 이와 같은 모양이다.

[추정] replan 트리거는 같은 모델의 자기 판정보다 바깥 신호로 일으키는 쪽이 낫다(사례: ADaPT의 WebShop 자기 판정 부풂, NATURAL PLAN의 self-correction 하락, VeriMAP의 replan 기여, Learning When to Plan의 프롬프트 시점 선택 실패 — 4개). 반대 사례: Magentic-One의 진척 판정은 같은 LLM이 하지만 ledger를 빼면 크게 떨어졌다.

## 학습된 추론

이 층에서는 계획과 반성이 모델 가중치 안에 있다. 하네스가 정하는 것은 생각이 놓이는 자리, 생각의 양, 다음 요청에 생각을 넘기는가다.

### 생각이 생기는 곳

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [DeepSeek-R1](https://arxiv.org/abs/2501.12948) | R1-Zero: base 모델 + `<think>`/`<answer>` 템플릿 + 규칙 보상(정답·형식) + GRPO | 아래 번호 목록 | R1-Zero AIME 2024 pass@1 15.6% → 71.0%(v1), 같은 지표 개정판 v2 77.9%. R1 AIME 79.8%, MATH-500 97.3% |
| R1 증류(같은 논문) | R1이 만든 800k 샘플로 dense 모델을 SFT만 | 같은 Qwen2.5-32B base에 RL 10K step 이상과 비교 | AIME 2024 / MATH-500 / LiveCodeBench: Distill-Qwen-32B 72.6 / 94.3 / 57.2, R1-Zero-Qwen-32B 47.0 / 91.6 / 40.2, QwQ-32B-Preview 50.0 / 90.6 / 41.9 |
| [Qwen3](https://arxiv.org/abs/2505.09388) | 한 모델에 thinking/non-thinking. /think·/no_think 플래그, budget은 정지 문구를 끼우는 디코딩 개입 | long-CoT cold start → reasoning RL → thinking mode fusion → general RL | ThinkFollow 88.7 → 98.9(Qwen3-32B). Qwen3-8B on-policy 증류 1,800 대 RL 17,920 GPU hours(같은 증류 체크포인트에서 출발, math·code 질의만) |
| [QwQ-32B](https://huggingface.co/Qwen/QwQ-32B) · Qwen3-2507 | QwQ는 thinking 전용. 2507판은 Instruct와 Thinking으로 나눴고 크기는 235B-A22B, 30B-A3B, 4B | QwQ RL: math/coding 결과 보상 → 일반 reward model | Thinking-2507 권장 출력 32,768(어려운 과제 81,920) 토큰 |
| [s1](https://arxiv.org/abs/2501.19393) | Qwen2.5-32B-Instruct를 1,000개로 SFT. budget forcing: 상한이면 구분자를 붙여 끝내고, 너무 일찍 멈추면 'Wait'를 붙임 | 억제 6회 근처에서 평탄, 반복 루프 | AIME24 50.0 → 56.7(budget forcing 유무). SFT 26분, H100 16장 |
| [Snell et al.](https://arxiv.org/abs/2408.03314) | test-time compute를 proposer(revision)와 verifier(PRM)로 나누고 난이도로 배분 | 쉬운 질문은 순차 revision, beam search는 어려운 질문·낮은 예산에 | compute-optimal이 best-of-N보다 최대 4배 적은 compute(PaLM 2-S*, MATH) |
| [L1](https://arxiv.org/abs/2503.04697) | 프롬프트의 목표 길이를 따르도록 RL(GRPO) | 정답 − α·길이 편차 | L1-Max가 L1-Exact보다 비슷한 성능에 최대 2배 적은 토큰(1.5B) |
| [AdaptThink](https://arxiv.org/abs/2505.13417) | 첫 토큰에서 Thinking과 NoThinking(빈 생각)을 고르게 RL | 성능 제약 아래 NoThinking에 보너스 | 길이 −50.9% / −63.5% / −44.7%, 정확도 +4.1 / +1.4 / +1.6(1.5B, GSM8K / MATH500 / AIME2024) |

R1-Zero의 과정은 이렇다.

1. 질문마다 G개 출력을 샘플링한다(개정판 v2: 16개, 최대 32,768 토큰, 8.2k step 뒤 65,536).
2. 규칙으로 정답과 형식(`<think>` 태그 사용)을 채점한다. neural reward model은 쓰지 않는다.
3. 그룹 안 보상으로 advantage를 만들고 정책을 갱신한다.
4. RL이 진행되며 응답 길이가 스스로 늘고, 중간 체크포인트에서 처음 접근을 다시 따지는 'aha moment'가 나타난다.
5. R1은 가독성·언어 혼용을 고치려 cold start 데이터로 시작하고, CoT 안 목표 언어 단어 비율을 보상에 더한다.

R1 저자들은 템플릿을 "We intentionally limit our constraints to this structural format, avoiding any content-specific biases—such as mandating reflective reasoning or promoting particular problem-solving strategies"라고 설명한다(§2.2.3).

실패한 시도로 PRM과 MCTS를 들었고, PRM에 대해 "First, it is challenging to explicitly define a fine-grain step in general reasoning."라고 적었다(§4.2).

증류에 대해서는 "Using Qwen2.5-32B (Qwen, 2024b) as the base model, direct distillation from DeepSeek-R1 outperforms applying RL on it."라고 정리한다(§1).

Qwen3 보고서는 통합의 비용을 "for challenging tasks like AIME’24 and LiveCodeBench, the performance in thinking mode actually decreases after these two training stages."라고 인정했다(§4.7). 2507판에서 모델을 다시 나눴지만 32B dense가 없어서, 운영 크기의 thinking 후보는 QwQ-32B와 하이브리드 Qwen3-32B다.

s1 저자들은 "Token-conditional control fails without budget forcing, as our model cannot reliably count tokens - even when trained to do so."라고 적는다(§5.2). 프롬프트로 생각 길이를 지시하는 방식을 피할 근거다.

단서: R1 v1과 v2의 R1-Zero 끝값이 다르다(71.0 대 77.9). Qwen3-32B의 thinking 켜고 끈 도구 호출 수치는 앞 노트 #thinking 모드에 있다.

### 생각이 놓이는 자리와 보존 규칙

| 모델·API | 생각이 놓이는 자리 | 도구 루프 안 | 새 user 메시지 뒤 | 출처 |
|---|---|---|---|---|
| OpenAI o1 · o3 | 숨긴 CoT, 사용자에게는 요약만. o3는 생각 안에서 도구 호출 | — | — | [o1 카드](https://arxiv.org/abs/2412.16720) · [o3 카드](https://cdn.openai.com/pdf/2221c875-02dc-4789-800b-e7758f3722c1/o3-and-o4-mini-system-card.pdf) |
| OpenAI Responses API | 불투명 reasoning item(store=false면 암호화) | item을 되돌림 | reasoning.context가 current_turn/all_turns를 정함. GPT-5.6부터 기본 렌더링 | [reasoning 가이드](https://platform.openai.com/docs/guides/reasoning) |
| gpt-oss harmony | analysis 채널 | 다음 샘플링에 그대로 넣음 | final 채널로 끝난 응답의 CoT는 지움 | [harmony](https://github.com/openai/openai-cookbook/blob/main/articles/openai-harmony.md) |
| DeepSeek-V3.2 | `<think>`, API의 reasoning_content | 보존 | 지움(2026 API는 tools가 있으면 모든 이전 턴을 되돌려야 함) | [V3.2](https://arxiv.org/abs/2512.02556) |
| Qwen3-32B | 응답 맨 앞 `<think>` | 보존(`<tool_response>`로만 감싼 user 메시지는 질문으로 치지 않음) | 마지막 진짜 user 질문 이전 턴의 생각은 지움 | [Qwen3](https://arxiv.org/abs/2505.09388) 템플릿 |
| QwQ-32B | `<think>`, 생성 프롬프트에 `<think>\n`을 미리 붙임 | 지움 | 지움 | [QwQ-32B](https://huggingface.co/Qwen/QwQ-32B) 템플릿 |
| Claude | thinking 블록 + signature, 보이는 텍스트는 다른 모델의 요약 | 반드시 수정 없이 되돌림 | 모델별로 모두 보존 또는 마지막 턴만 | [Claude thinking](https://platform.claude.com/docs/en/build-with-claude/thinking) |
| Gemini | steps 배열의 thought step + signature, 원문 비공개 | 그대로 다시 보냄 | stateless 모드는 모두 다시 보냄, 모델을 바꿔도 | [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking) |
| MiniMax-M2 · Kimi K2 Thinking | `<think>` / reasoning_content | MiniMax는 보존 | MiniMax는 보존(지우면 성능 하락), Kimi 카드는 규칙을 적지 않음 | [Kimi 카드](https://huggingface.co/moonshotai/Kimi-K2-Thinking) |

DeepSeek-V3.2 저자들은 R1 방식을 버린 이유를 "We observed that replicating DeepSeek-R1’s strategy—discarding reasoning content upon the arrival of the second round of messages—results in significant token inefficiency. This approach forces the model to redundantly re-reason through the entire problem for each subsequent tool call."라고 적는다(§3.2.1).

이어서 "certain agent frameworks, such as Roo Code or Terminus, simulate tool interactions via user messages. These frameworks may not fully benefit from our enhanced reasoning persistence"라고 경고한다(§3.2.1).

V3.2는 검색 에이전트 평가에서 토큰이 문맥 창(128K)의 80%를 넘으면 이전 도구 이력을 버리고 계속하는 문맥 관리를 썼다. 이 Discard-all로 BrowseComp가 51.4에서 67.6이 됐다.

Claude 문서는 "When Claude calls a tool, it pauses construction of its response to await external information. When you return the tool result, Claude continues building that same response, so its earlier reasoning must still be present."라고 적는다(thinking-overview.md:939).

또 "A block stays valid only while the top-level `system` prompt, the `tools`, and the messages before it are unchanged."라고 적어 이력을 append-only로 다루게 한다(:1077).

OpenAI 문서는 "Persisted reasoning provides continuity; it does not expose the model’s raw reasoning."라고 적는다(reasoning-guide.txt:1496). o1 카드는 "We surface CoT summaries to users in ChatGPT."라고 적는다(§4.3.2).

단서: 상용 API에서는 원문 생각을 받을 수 없어서, 경로 기록에는 요약만 남는다. 로컬 Qwen은 원문 생각을 남길 수 있다. 보존 대 삭제의 수치 비교는 #30B급 오픈 deep research에 모았다.

[추정] 하네스는 생각 보존 규칙을 모델별 설정값으로 들고 있어야 한다(사례: Qwen3-32B와 QwQ-32B 템플릿의 차이, DeepSeek-V3.2의 user 메시지 흉내 경고, Claude의 prefix 변경 무효화, Tongyi 추론 코드가 서버 설정에 따라 생각을 잃는 문제 — 4개).

### 생각과 도구의 교차 학습

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Search-R1](https://arxiv.org/abs/2503.09516) | 한 시퀀스에 `<think>`, `<search>`, `<information>`(환경이 붙인 검색 결과), `<answer>`. 검색 토큰은 loss에서 가림, 보상은 EM 하나 | 아래 번호 목록 | 7개 QA 평균 EM 0.431 대 최고 기준선 0.348(Qwen2.5-7B Base, PPO). 검색 토큰 마스킹을 빼면 0.343. 14B 0.479 |
| [ReTool](https://arxiv.org/abs/2504.11536) | 생각 안 `<code>` → 샌드박스 → `<interpreter>` 결과 삽입, 결과 보상만(PPO) | cold start → RL | AIME2024 67.0(400 step) 대 텍스트 RL 40.0(1080 step), Qwen2.5-32B-Instruct. 응답 길이 약 40% 감소 |
| [RITE](https://arxiv.org/abs/2510.11184) | Plan → Action → Reflection 순환을 형식 보상으로 강제, 이전 생각 모두 보존 | SFT 없이 RL(Qwen2.5-7B/32B) | RITE-32B AIME 24 71.3%. reflection 순환을 빼면 WebInstruct −4.2%(상대·절대 미기재) |
| [DeepTool](https://arxiv.org/abs/2605.29568) | step schema 고정(생각, 코드, 피드백), 행동만 채점하는 process 보상, 생각 상태 보존 비교 | step별 롤아웃 → GRPO | AIME 2025 생각 상태 버림 25.8% → 보존 30.0%(backbone 미기재). Qwen2.5-7B AIME24 3.2% → 40.4% |
| [DART](https://arxiv.org/abs/2602.00994) | reasoning 토큰과 도구 토큰을 다른 LoRA로 라우팅 | backbone 고정 | 개별 수치는 표에만 있어 옮기지 않음 |

Search-R1의 생각-검색 교차는 이렇게 돈다.

1. 템플릿이 "Answer the given question. You must conduct reasoning inside <think> and </think> first every time you get new information. After reasoning, if you find you lack some knowledge, you can call a search engine by <search> query </search>, and it will return the top searched results between <information> and </information>."라고 지시한다(Table 1).
2. 생성 중 `</search>`가 나오면 질의를 뽑아 검색한다(E5, 2018 Wikipedia, top-3).
3. 결과를 `<information>`으로 시퀀스에 붙이고 생성을 이어 간다.
4. 유효한 태그가 없으면 'My action is not correct. Let me rethink.'를 붙여 다시 생성시킨다.
5. `<answer>`가 나오거나 최대 행동 수(B=4)에 닿으면 끝난다.
6. 학습 때는 롤아웃 전체에 EM 보상을 주고, 모델이 생성한 토큰에만 정책 경사를 건다.

DeepTool 저자들은 "Preserving the interleaved thinking state consistently improves performance on all seven benchmarks."라고 적는다(§3.3).

그리고 "When the budget is too small, explicit interleaved reasoning can be ineffective and may even fall below the non-thinking baseline, especially on harder benchmarks"라고 하한을 밝혔다(§3.4).

DART 저자들은 생각과 도구를 한 파라미터로 배우는 가정에 반대 증거를 낸다. "We identify a clear gradient misalignment: the two types of gradients are nearly orthogonal"(§1).

단서: 이 항목들은 수학·QA 정답 보상이고 대부분 3B~32B 학습 결과다. Search-R1은 같은 논문 안에서 개선율을 24%(Abstract)와 41%(§1)로 다르게 적는다.

### 생각의 실패와 생각 밖 기록

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Overthinking](https://arxiv.org/abs/2412.21187) | 긴 생각을 solution 라운드로 잘라 첫 정답 이후 반복을 잼 | 첫 정답 solution만 남긴 짧은 응답으로 선호 학습 | QwQ-32B-Preview MATH500 쉬운 문제 3.7 대 어려운 문제 3.0 라운드. 토큰 −48.6%, 정확도 유지 |
| [Underthinking · TIP](https://arxiv.org/abs/2501.18585) | 생각을 너무 자주 바꾸는 문제, 전환 토큰 logit에 페널티 | thought 시작 뒤 β 토큰 동안만 | QwQ-32B-Preview AIME2024 Pass@4 43.7% → 51.4%(Self-Consistency + TIP) |
| [Reasoning Models Don't Always Say What They Think](https://arxiv.org/abs/2505.05410) | 힌트 때문에 답이 바뀐 경우 CoT가 힌트를 말하는지 | RL 체크포인트마다 반복 | 전체 faithfulness 25% / 39%(Claude 3.7 Sonnet / DeepSeek R1). 보상 해킹을 말한 비율 2% 미만(6개 환경 중 5개) |
| [Coconut](https://arxiv.org/abs/2412.06769) | 생각을 토큰이 아닌 hidden state로 되먹임 | 커리큘럼으로 CoT 단계를 latent로 바꿈 | GSM8k 34.1% 대 No-CoT 16.5%, 일반 CoT 42.9%(GPT-2) |
| [think 도구](https://www.anthropic.com/engineering/claude-think-tool) | 입력이 thought 하나인 빈 도구, 생각을 도구 호출 기록으로 남김 | 도구 결과 뒤 think로 규칙·정보 충분성 점검 | τ-bench airline pass^1 표: think+최적화 프롬프트 0.584 / think 0.404 / extended thinking 0.412 / baseline 0.332(본문은 0.570 대 0.370). retail think 0.812 대 baseline 0.783(Claude 3.7 Sonnet) |

faithfulness 저자들은 "CoTs reveal their usage of hints in at least 1% of examples where they use the hint, but the reveal rate is often below 20%"라고 적는다(Abstract). Coconut처럼 생각이 벡터로만 있으면 읽을 수 없어 경로 기록 목표와 정면으로 부딪힌다.

think 도구 글에는 갱신 안내가 붙었다. "Extended thinking capabilities have improved since its initial release, such that we recommend using that feature instead of a dedicated think tool in most cases."(글 상단).

단서: faithfulness 실험은 CoT 없이도 풀 수 있는 객관식 과제 위주다. TIP의 전환 토큰 목록은 영어 낱말이라 한국어로 생각시키면 다시 정해야 한다.

[추정] 질문 경로 기록의 1차 증거는 생각 텍스트가 아니라 도구 호출·관찰·인용이어야 한다(사례: faithfulness 25%·39%, Myopic Planning의 깊은 노드 무시, 상용 API 세 곳의 원문 생각 비공개 — 3개).

## 구현

이 절은 수집·검증 에이전트가 프레임워크 소스와 프롬프트 파일을 커밋 단위로 열어 확인한 구현을 다룬다.

[Anthropic의 Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)는 구조를 '누가 경로를 정하나'로 가른다. 미리 정한 코드 경로로 LLM과 도구를 엮으면 workflow, LLM이 과정을 동적으로 정하면 agent다. 글은 "we recommend finding the simplest solution possible, and only increasing complexity when needed."라고 권한다(When and when not to use agents).

LangGraph 판 ReWOO·LLMCompiler·Plan-and-Execute·LATS·Reflexion과 Magentic-One은 #추론 패턴과 #에이전트 수준 계획에서 다뤘다. 아래 표는 그 밖의 구현이 계획을 어디에 두고 무엇으로 다시 세우는지 정리한다.

| 구현 | 계획이 사는 곳·형태 | 다음 행동 | replan 트리거 | 종료 | 파일:줄 |
|---|---|---|---|---|---|
| [smolagents](https://github.com/huggingface/smolagents) planning_interval(96f33fa) | memory의 PlanningStep 문자열. 첫 계획은 facts survey(주어진/찾을/유도할 사실) + 고수준 계획 | LLM이 Thought → Code | 고정 주기. 갱신 때 이전 계획과 Thought 텍스트를 지우고 도구 호출·관찰만 봄 | final_answer, max_steps 초과면 메모리로 강제 답 | agents.py:550-551, code_agent.yaml:178 |
| [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk)(d2ee0cd) | task_tracker의 목록 {title, notes, status}, TASKS.json | LLM 도구 호출 | 모델 판단(plan 명령으로 목록 전체 교체). StuckDetector가 반복 패턴을 규칙으로 감시 | FinishAction, 예산 초과, max_iteration_per_run 500, STUCK | definition.py:65, stuck_detector.py:28-30 |
| OpenHands Planning preset | PLAN.md 다섯 섹션(OBJECTIVE … TESTING AND VALIDATION) | LLM, 도구는 glob·grep·PLAN.md 편집뿐 | 사용자 피드백 | 사용자 만족 | planning_file_editor/definition.py:54 |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python)(0dc4cf1) | SDK에는 planner가 없음. research_bot 예제는 WebSearchPlan{searches: [{reason, query}]} 구조화 출력 1회 | LLM, handoff는 transfer_to_<agent> 도구 | 없음 | 도구 호출 없는 원하는 타입 출력, max_turns | examples/research_bot/agents/planner_agent.py:7-14 |
| [Claude Code](https://code.claude.com/docs/en/permission-modes) plan mode | 계획 파일(~/.claude/plans 또는 plansDirectory. 문서는 저장 규칙으로 명시하지 않음) | LLM, 편집은 권한 시스템이 승인 전까지 막음 | 사람이 'No, keep planning' | 사람 승인 뒤 고른 권한 모드로 실행 | permission-modes, model-config 문서 |
| [Claude Code](https://code.claude.com/docs/en/tools-reference) Task 도구 | TaskCreate·TaskUpdate·TaskList의 task list | LLM 도구 호출 | 모델 판단 | — | tools-reference 'Task tool availability' |
| [Google ADK](https://github.com/google/adk-python) PlanReActPlanner(da35ca7) | 대화 이력의 텍스트 part, /*PLANNING*/ /*ACTION*/ /*REASONING*/ /*REPLANNING*/ /*FINAL_ANSWER*/ 태그 | LLM이 같은 응답 안에서 | 모델이 REPLANNING 태그 아래 수정 계획 | FINAL_ANSWER 태그 | plan_re_act_planner.py:182, 190 |
| ADK BuiltInPlanner | 모델 내부 thinking뿐 | LLM | 정책 안 | 일반 루프 | built_in_planner.py:33 |
| [Codex](https://github.com/openai/codex) update_plan(970111f) | 도구 인자 {explanation?, plan: [{step, status}]}, 서버 쪽 판단 없음 | LLM | 프롬프트의 'Scope pivots' 규칙 | 모든 항목 completed 또는 취소·연기 | plan_spec.rs:44-46, gpt_5_2_prompt.md:46 |
| Codex Plan Mode | `<proposed_plan>` 블록, 수정 요청이면 블록 전체 교체 | LLM, request_user_input으로 객관식 질문 | 사람 거부 | decision complete일 때만 블록 출력 | collaboration-mode-templates/templates/plan.md:3, 128 |
| [LangChain write_todos](https://github.com/langchain-ai/langchain/blob/8d34066/libs/langchain_v1/langchain/agents/middleware/todo.py) · [deepagents](https://github.com/langchain-ai/deepagents) | 그래프 상태 todos [{content, status}], 도구 호출로 통째 교체 | LLM | 모델 판단(3단계 미만이면 쓰지 말라는 지침뿐) | 마지막 write_todos 다음 메시지에 실제 답 | todo.py:54, 70, 117, 131 |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) Plan Mode(cd1b45c) | plansDir의 Markdown, 승인되면 approvedPlanPath | Plan 모드는 Pro, 승인된 계획 실행은 Flash로 라우팅(auto 모델일 때) | 사람 | exit_plan_mode 승인 | approvalModeStrategy.ts:25-26 |
| Gemini CLI Task Tracker | 작업 하나가 <id>.json 파일, dependencies로 DAG | LLM, 의존·순환은 서비스 코드가 검사 | — | 의존이 모두 closed여야 닫힘 | trackerService.ts:196, 216 |
| [Cline](https://github.com/cline/cline) Plan/Act(40c5d99) | 대화 응답 | LLM, plan 모드의 변경 명령은 command-guard가 오류로 돌려줌 | 사람 | 사람이 명시 승인한 뒤 switch_to_act_mode | sdk/packages/shared/src/prompt/cline.ts:43 |
| [CrewAI](https://github.com/crewAIInc/crewAI) PlanningConfig(38db11e) | state.todos {step_number, description, depends_on, status, result} | 코드 router(decide_next_action) | 관찰기의 needs_full_replan, 단계 실패, 의존 교착 | 모두 완료, 또는 max_replans(기본 3)에서 부분 결과로 마무리 | agents/planner_observer.py:7-8, agent_executor.py:1294-1297 |
| [Aider](https://github.com/Aider-AI/aider) architect(5dc9490) | architect 모델의 응답 텍스트 하나 | — | 없음 | editor가 한 번 편집 | architect_coder.py:38-39 |
| [Anthropic 다중 에이전트 리서치](https://www.anthropic.com/engineering/multi-agent-research-system) | LeadResearcher가 계획을 Memory에 저장 | lead LLM이 subagent 생성 | lead 판단 | 충분하면 CitationAgent로 | 글 Architecture overview |
| [open_deep_research](https://github.com/langchain-ai/open_deep_research)(1b7d2e8) | research brief(구조화 출력 하나) + think_tool 기록 | supervisor LLM이 ConductResearch·ResearchComplete·think_tool 중 고름 | — | 반복 > 6, 도구 호출 없음, ResearchComplete | deep_researcher.py:247, prompts.py:92 |

CrewAI의 관찰기 분기는 이렇게 돈다.

1. 계획을 함수 호출로 받아 {plan, steps, ready}를 얻고, ready가 아니면 refine한다(max_attempts 기본 None이라 ready가 될 때까지).
2. 의존이 풀린 todo가 0개인데 미완료가 남으면 교착으로 보고 replan한다. 1개면 순차, 여러 개면 병렬로 실행한다.
3. StepExecutor가 todo 하나를 격리 실행한다. 시스템 프롬프트는 이 한 단계만 하라고 한다(단계당 max_step_iterations 기본 15).
4. reasoning_effort가 관찰 비용을 정한다. low는 휴리스틱만, medium(기본)은 LLM 관찰 후 실패 때만 재계획, high는 decide_next_action으로 보낸다.
5. high의 분기: goal_already_achieved면 조기 종료, needs_full_replan이거나 단계 실패면 replan, 계획이 유효하고 수정 제안이 있으면 뒤 단계 설명만 바꾸고 계속(LLM 추가 호출 없음), 그 밖엔 계속.
6. replan_count가 max_replans에 닿으면 재계획하지 않고 지금까지 결과로 마무리한다.
7. 모든 todo의 result를 모아 LLM 한 번으로 최종 답을 합성한다.

CrewAI 관찰기 프롬프트는 "Be conservative about triggering full replans — only do so when the remaining plan is fundamentally wrong, not just suboptimal."라고 지시한다(translations/en.json:88).

코드 주석은 관찰기가 "This is NOT an error detector — it runs on every step, including successes, to incorporate runtime observations into the remaining plan."이라고 적는다(planner_observer.py:7-8).

계획과 실행을 떼는 방식은 세 갈래다.

| 분리 방식 | 구현 | 코드가 강제하나 |
|---|---|---|
| 권한 | Claude Code plan mode, Codex Plan Mode, Gemini CLI, Cline, OpenHands Planning preset | Gemini plan.toml 정책, Cline command-guard, OpenHands allowed_edits_files, Codex의 update_plan 차단(plan.rs:87-90)은 코드. Codex의 편집 금지는 프롬프트 규칙 |
| 모델 | Claude Code opusplan(plan은 opus, 실행은 sonnet), Gemini ApprovalModeStrategy, Cline 모드별 모델, Aider architect/editor, CrewAI planning_config.llm | 라우팅·설정 코드 |
| 문맥 | CrewAI StepExecutor, Magentic-One 재계획 리셋, deepagents의 상태 없는 subagent, open_deep_research의 압축, Claude Code showClearContextOnPlanAccept, Aider editor 이력 비우기 | 코드 |

수치가 있는 구현은 셋이다.

| 출처 | 무엇을 했나 | 수치(조건) |
|---|---|---|
| [Aider architect](https://aider.chat/2024/09/26/architect.html) | architect가 변경 방법을 서술, editor가 편집 형식으로 바꿈 | gpt-4o-mini 자기 짝 60.2% 대 단독 55.6%. o1-preview + deepseek editor 85.0% 대 o1-preview 단독 79.7%(aider code editing pass_rate_2) |
| Anthropic 다중 에이전트 리서치 | Opus 4 lead + Sonnet 4 subagent | 단일 Opus 4보다 내부 eval 90.2% 높음. BrowseComp 분산의 80%를 토큰 사용량이 설명. 다중 에이전트는 채팅 대비 약 15배 토큰 |
| OpenHands StuckDetector | 반복 패턴 규칙 감시 | 기본 임계 action_observation 4, action_error 3, monologue 3, alternating_pattern 6(types.py:150-161) |

Gemini CLI Task Tracker는 계획 불변식을 서비스 코드가 막는다. 의존이 남은 작업을 닫으면 "`Cannot close task ${task.id} because dependency ${depId} is still ${dep.status}.`"(trackerService.ts:196), 순환이면 "`Circular dependency detected involving task ${currentId}.`"(:216)를 던진다.

프롬프트도 "6.  **STATE OVER CHAT**: If the user says \"I think we finished that,\" but the tool says it is 'pending', trust the tool--or verify explicitly before updating."라고 적는다(snippets.ts:592).

Claude Code 문서는 Task 도구를 신형 모델에서 기본으로 끈 이유를 "On newer models, Claude keeps track of multi-step work without a written checklist, and the tools' definitions and reminders take up context."라고 적는다(tools-reference 'Task tool availability').

이 도구들은 Opus 4.7, Sonnet 4.6, Haiku 4.5와 그 이전 모델에서만 기본 제공된다. Claude Code가 모르는 모델 ID(LLM gateway로 띄운 사용자 정의 모델 등)도 기본으로 빠져서, `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`로 켜야 한다.

open_deep_research의 supervisor 프롬프트는 "**CRITICAL: Use think_tool before calling ConductResearch to plan your approach, and after each ConductResearch to assess progress. Do not call think_tool with any other tools in parallel.**"이다(prompts.py:92).

researcher 프롬프트는 단순 질의 2–3회, 복잡 질의 최대 5회 검색 뒤 멈추고, "- Your last 2 searches returned similar information"이면 즉시 멈추게 한다(prompts.py:164-173). 코드는 max_react_tool_calls(기본 10)로 한 번 더 막는다.

단서: 이 구현들은 저장소 안에 효과 수치가 거의 없다. Claude Code와 deepagents가 todo 도구를 기본에서 뺀 결정의 근거 수치도 찾지 못했다. Gemini tracker 프롬프트는 'pending'이라 적지만 상태 enum에는 pending이 없고 open이다.

[추정] 작은 모델로 옮길 때는 계획 불변식(의존 완료, 순환 금지, 한 번에 한 도구 호출, 편집 금지)을 프롬프트가 아니라 코드로 검사하는 구현이 맞다(사례: Gemini tracker 서비스 검사, Cline command-guard, OpenHands allowed_edits_files, LangChain after_model의 병렬 write_todos 차단 — 4개).

## 질문 경로 계획

이 층의 계획 단위는 하위 질문, 검색어, KG relation path, 탐색 frontier다. 계획과 경로를 문맥 밖 자료구조에 두는지가 경로 기록이 남는지를 거의 결정한다.

### 하위 질문 사슬

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Self-Ask](https://arxiv.org/abs/2210.03350) | 'Follow up:'·'Intermediate answer:' scaffold, 하위 질문 전체를 검색 API로 | LM이 최종 답을 낼 때까지 반복, 되돌아감 없음 | Bamboogle Direct 17.6 / CoT 46.4 / Self-ask 57.6 / Self-ask+Search 60.0(Davinci-002) |
| [IRCoT](https://arxiv.org/abs/2212.10509) | 방금 쓴 CoT 문장 하나가 다음 검색어 | 아래 번호 목록 | retrieval recall +11.3/+22.6/+12.5/+21.2(GPT3, HotpotQA/2Wiki/MuSiQue/IIRC). Flan-T5-XL(3B)+IRCoT QA가 GPT3(175B)+한 번 검색 QA를 앞섬 |
| [DSP](https://arxiv.org/abs/2212.14024) · [DSPy](https://arxiv.org/html/2310.03714) | hop 모양은 프로그램이 고정, 맞힌 trace를 demonstration으로 bootstrap | HotPotQA 2 hop 고정 | HotPotQA EM DSP 51.4 대 Self-ask 25.2(text-davinci-002). Llama2-13b-chat multihop bootstrap 42.0(dev) 대 react bootstrap×2 40.0 |
| [Question Decomposition](https://arxiv.org/html/2507.00355v1) | 최대 5개 독립 하위 질문 + 원 질문으로 검색, 원 질문 기준 rerank | 한 번 돌고 끝 | MultiHop-RAG MRR@10 0.464 → 0.635. HotpotQA EM/F1 25.4/31.3 → 28.1/35.0(generator Qwen2.5-32B-Instruct). 하위 질문이 거의 늘 정확히 5개(93.3%, 98.6%) |
| [RQ-RAG](https://arxiv.org/html/2404.00610) | 7B가 rewrite·decompose·disambiguate 토큰을 골라 tree로 분기 | 경로 선택은 perplexity·confidence·ensemble | multi-hop 평균 F1 49.7 대 GPT-3.5+CoT 44.9(Llama2-7B, 데이터셋이 준 후보 문서 안). 어느 경로든 맞으면 정답으로 세는 상한 HotpotQA 80.5 |
| [Adaptive-RAG](https://arxiv.org/html/2403.14403) | T5-Large가 질문을 A(검색 없음)·B(한 번)·C(IRCoT)로 분류 | 라우팅은 처음 한 번 | GPT-3.5 평균 F1 50.91 대 multi-step 50.87, 상대 시간 1.46 대 3.33. classifier 정확도 54.52%. oracle 라우팅이면 62.80 |
| [Search-o1](https://arxiv.org/html/2501.05366) | QwQ-32B가 생각 도중 검색, Reason-in-Documents가 문서를 걸러 정제 지식만 넣음 | 최대 32,768 토큰, 답이 없으면 직접 추론 결과로 back-off | HotpotQA EM 45.2 대 문서 정제 없는 agentic RAG 43.0 대 직접 추론 25.4 |
| [PlanRAG](https://arxiv.org/html/2406.12430) | Plan → SQL/Cypher 검색 → 매 관찰 뒤 Re-plan 여부 판단 | LM이 분석이 더 필요 없다고 보면 결정 | GPT-4 Building 45.0 대 IterRAG 37.6, 재계획 제거 44.1. 재계획은 Building 38%, Locating 6%에서 일어남 |
| [Plan*RAG](https://arxiv.org/html/2410.20753) | 계획을 문맥 밖 DAG로, 노드는 부모 답과 자기 문서만 봄 | 아래 번호 목록 | HotpotQA 40.44 대 ReAct 33.15(Llama3.1-8B 실행). 미세조정 8B planner 31.28 대 GPT-4o planner 31.97 |
| [LPKG](https://arxiv.org/html/2406.14282) | Wikidata 패턴 9종으로 만든 코드형 계획(Search, Get_Answer, Intersection, {Ans_1} placeholder)을 학습 | 계획 코드 한 번 → 실행기가 채움 | HotPotQA EM: Llama3-8B ICL 0.369 → LPKG 0.376, CodeQwen1.5-7B ICL 0.110 → LPKG 0.338(QA는 GPT-3.5) |

IRCoT의 과정은 이렇다.

1. 질문 자체로 K개 문단을 검색한다.
2. 질문, 모은 문단, 이전 CoT로 다음 CoT를 생성하되 첫 문장만 취한다.
3. 그 문장으로 K개 문단을 더 검색해 누적한다(누적 상한 15개).
4. 2~3을 반복한다. 재계획과 backtrack은 없다.
5. 'answer is:'가 나오거나 8 step에 닿으면 멈추고, reader가 누적 문단으로 답한다.

IRCoT 저자들은 결합의 이유를 "Here, what to retrieve depends on what has already been derived, which in turn may depend on what was previously retrieved."라고 적는다(§1).

Plan*RAG의 과정은 이렇다.

1. planner가 질문과 예시로 (부모 질문, 하위 질문) 튜플 리스트, 곧 DAG를 한 번에 만든다.
2. root 노드를 찾고 깊이를 계산한다.
3. 깊이 단위로 처리하고, 같은 깊이 노드는 병렬로 돈다.
4. 노드마다 ⟨AI.J⟩ 태그에 부모 답을 채워 구체 질의를 만들고, 검색한 뒤 답한다.
5. 최대 깊이까지 돈 뒤 데이터셋별 연산자가 노드 답들을 합친다. 재계획은 구현되지 않았다.

Plan*RAG 저자들은 "Our key insight is that by isolating the reasoning plan as a directed acyclic graph (DAG) outside the LM's working memory, we can enable (1) systematic exploration of reasoning paths, (2) atomic subqueries enabling precise retrievals and grounding, and (3) efficiency through parallel execution and bounded context window utilization."라고 적는다(Abstract).

한계는 "A key limitation in Plan∗RAG is reliance on a static plan generated a priori."다(§6).

PlanRAG는 작은 모델에서 무너졌다. GPT-3.5에서는 PlanRAG가 IterRAG보다 낮았고, Llama 2 70B·13B와 Phi-2는 두 방식 모두 0점이었다(Table 11).

저자는 "By GPT-3.5, IterRAG-LM shows batter performance rather than PlanRAG-LM. It is because the prompt of PlanRAG is too complex for GPT-3.5 to understand instructions and generate proper answers."라고 적는다(Appendix A.7, 원문 철자 'batter' 그대로).

단서: Question Decomposition의 하위 질문은 서로 의존을 표현하지 못한다. RQ-RAG의 multi-hop 수치는 열린 검색이 아니라 데이터셋이 준 후보 문서 안의 BM25 검색이라 실제보다 쉽다. LPKG의 미세조정 효과는 백본에 따라 크게 다르다.

### KG 위 경로

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [StructGPT](https://arxiv.org/html/2305.09645) | 인터페이스(이웃 relation 읽기, triple 읽기)가 잘라 준 조각만 LLM이 고름 | 호출 순서는 과제별 고정, entity linking은 가정 | WebQSP Hits@1 61.2 → 72.6, MetaQA 3-hop 43.2 → 80.2(ChatGPT) |
| [Think-on-Graph](https://arxiv.org/html/2307.07697) | LLM이 KG 위에서 beam search(N=3, 최대 깊이 3) | relation 고르기 → entity 고르기 → 충분성 판단 | CWQ 39.1 → 53.6(ToG)·57.6(ToG-R), Llama-2-70B-Chat. LLM 호출 최대 22회 |
| [Think-on-Graph 2.0](https://arxiv.org/html/2407.10805) | KG가 문서 검색 범위를 좁히고 문서 점수가 다음 frontier를 정함 | 깊이 3을 넘으면 평탄 | AdvHotpotQA EM 17.9 → 30.8(Qwen2-7B). KG 완전도 100/80/50/30%에서 EM 43/41/35/23. 질의당 호출 5.4회 대 ToG 16.3회 |
| [RoG](https://arxiv.org/html/2310.01061) | planning(relation path) → retrieval(constrained BFS) → reasoning, 한 모델 | 아래 번호 목록 | WebQSP Hits@1 85.7, CWQ 62.6(LLaMA2-Chat-7B). planner를 ChatGPT에 꽂으면 WebQSP 66.77 → 81.51 |
| [KG-Agent](https://arxiv.org/html/2402.11163) | 7B planner가 도구 함수 호출 한 줄씩, executor가 실행, memory에 program 누적 | end 도구로 멈춤, entity는 주어진다고 가정 | WebQSP Hits@1 83.3(LLaMA2-7B, 학습 1만 개). out-of-domain NQ-Wiki 33.00 대 ChatGPT 57.49 |
| [Plan-on-Graph](https://arxiv.org/html/2410.23875) | Guidance(조건 붙은 하위 목표) · Memory · Reflection(경로 수정, backtrack) | 탐색 깊이 상한 4 | CWQ Hits@1 63.2 대 ToG 57.1(GPT-3.5). 호출 13.3 대 22.6. Memory 빼면 58.9 |
| [CoG](https://arxiv.org/html/2609.12791) | Planning → Exploration(KG·텍스트) → Synthesis → Reflection, 기억 셋(Notebook, 후보 entity pool, history) | 깊이 4, 폭 5 | 평균 EM Qwen3-8B 23.91 → 50.97, Qwen3-32B non-thinking 33.36 → 57.15. 질문당 중앙값 토큰 14,204~38,876, 지연 80.7~285.1초 |
| [KAG](https://arxiv.org/html/2409.13731) | logical form 계획 → KG 우선 hybrid 추론 → Judge → SupplyQuery 재계획, synonym·isA 정렬 | 최대 3회차 | F1 HotpotQA 76.2(DeepSeek-V2). 1회차로 줄이면 F1 0.2% / 1.2% / 4.4% 하락, 1회차에 끝난 질문 98.3% / 95.2% / 84.1% |

RoG의 planning-retrieval-reasoning은 이렇다.

1. planning: 질문에서 relation 순서열(relation path) 3개를 beam search로 만든다.
2. retrieval: 질문 entity에서 출발해 계획된 relation 순서를 따라 constrained BFS로 KG에서 실제 경로를 가져온다.
3. reasoning: 질문과 가져온 경로로 답과 설명을 쓴다. 설명은 특정 경로를 인용한다.
4. 학습 때는 질문-답 entity 사이 최단 KG 경로를 planning 정답으로 쓴다. 반복과 재계획은 없다.

KG에서 실체화되지 않는 relation path는 경로를 못 가져오므로 hallucination이 저절로 걸러진다.

CoG의 과정은 이렇다.

1. 질문에서 초기 계획을 만든다. 하위 질의마다 anchor entity가 붙는다.
2. 턴마다 하위 질의별로 KG 경로(entity linking → relation → fact 가지치기)와 텍스트 경로(페이지 → 목차 → 섹션 정독)를 탐색하고 합친다.
3. 판정이 충분이면 답한다. 부족하지만 쓸모 있으면 남은 빈 곳을 겨냥해 새 계획을 세운다. 막다른 길이면 history로 전략 오류를 진단하고 후보 pool의 미뤄 둔 entity로 backtrack하거나 질의를 다시 쓴다.
4. 턴마다 (계획, 요약)을 history에 쌓는다. 답은 Notebook의 확인된 사실로 만든다.

KAG 저자들은 문제를 "Due to the diversity of language expressions, there are numerous synonymous or similar nodes, resulting in low connectivity between knowledge elements, making the retrieval recall incomplete."라고 정의한다(§1).

Plan-on-Graph는 "Since the reasoning capability of the LLM does not always guarantee the correctness of path exploration, there is a need to self-correct erroneous reasoning paths."라고 Reflection의 이유를 적는다(§3.4).

단서: ToG 논문은 Table 1과 Table 2에서 CWQ의 ToG·ToG-R 라벨이 서로 바뀌어 있다. StructGPT와 KG-Agent는 entity linking을 가정으로 빼 두었다. CoG의 비용은 ToG-2의 4~10배 토큰이고 저자도 실시간 배포를 막을 수 있다고 적었다.

[추정] 질문 경로에서는 재계획 회차보다 첫 계획과 용어 정렬이 결과를 더 크게 가른다(사례: KAG의 1회차 종료 비율, PlanRAG의 재계획 발생 6%·38%, Plan*RAG의 정적 계획 이득, ToG-2의 KG 완전도 하락 — 4개).

### 그래프 확산과 요약

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [GraphRAG](https://arxiv.org/html/2404.16130) · [코드](https://github.com/microsoft/graphrag)(c600ff80) | global: community report map-reduce. local: entity 이웃. DRIFT: primer가 follow-up 질문을 내고 networkx QueryState에 질문-답 그래프를 쌓음 | DRIFT는 n_depth(기본 3) 동안 미완 action 앞 20개를 local search | comprehensiveness 승률 72–83%(Podcast), 72–80%(News), LLM judge. 질의당 토큰 26,657(C0) 대 1,014,611(원문 map-reduce) |
| [HippoRAG 2](https://arxiv.org/html/2502.14802) | OpenIE KG + 유사도 0.8 이상 synonym 엣지 + passage 노드, PPR 한 번 | 반복 루프 없음 | 평균 F1 59.8 대 NV-Embed-v2 57.0, GraphRAG 49.6, LightRAG 6.6(Llama-3.3-70B) |
| [Graph-R1](https://arxiv.org/html/2507.21892) · [HyperGraphPro](https://arxiv.org/html/2601.17755) | hypergraph 위 `<think>`/`<query>`/`<knowledge>` 루프, entity 경로와 사실 직접 검색을 순위 융합, GRPO / step 진전 보상 | 평균 2.3–2.5턴 | 평균 F1 40.09 / 51.26 / 57.82(Qwen2.5-1.5B/3B/7B). 7B는 RL을 빼면 63.87 → 17.79(2Wiki·HotpotQA 평균) |

GraphRAG 논문은 global의 종료를 "Answers with score 0 are filtered out."와 "Intermediate community answers are sorted in descending order of helpfulness score and iteratively added into a new context window until the token limit is reached."로 정한다(§3.1.6).

단서: 현재 GraphRAG 코드는 DRIFT의 다음 follow-up을 LLM 점수 순이 아니라 무작위로 고른다. search.py:243이 scorer 없이 rank_incomplete_actions()를 부르고, state.py:75의 "# shuffle the list if no scorer"가 섞는다. HippoRAG 2는 계획이 명시적이지 않아 '왜 이 문단인가'가 PPR 점수로만 설명된다.

### 경로를 문맥 밖 자료구조로 두기

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [MindSearch](https://arxiv.org/html/2407.20183) · [코드](https://github.com/InternLM/MindSearch)(7952c5f) | WebPlanner가 Python 코드로 WebSearchGraph를 조작, 노드마다 WebSearcher | 아래 번호 목록 | 평균 28.9(검색 없음) / 42.9(ReAct) / 49.2(MindSearch), InternLM2.5-7B-Chat. GPT-4o는 53.5 / 55.1 / 59.8 |
| [Argus](https://arxiv.org/html/2605.16217v3) | 상태 없는 Searcher와 Navigator. Navigator가 trajectory를 evidence 그래프(출처 URL 붙은 증거, 잠정 claim, support/contradict 호)로 파싱 | 빈 곳 유형별 검증 질의 → 학습된 종료 토큰 → (질문, 그래프)만 보고 합성 | BrowseComp 42.1(기반 재현) → 55.0(Searcher) → 62.2(Solo) → 74.5(Parallel K=8), Qwen3.5-35B-A3B. 같은 rollout에서 텍스트만 69.3 대 그래프 74.5 |
| [SearchAtlas](https://arxiv.org/html/2609.10901) | 검색 trajectory를 사후에 typed 그래프로 재구성: 노드(원 질문, query, 사전 지식 PK, 답), 엣지 4종(constraint-use, evidence-use, failure-response, prior-knowledge) | 결정적 추출 → LLM 귀속 → 최소 부모 집합 | edge macro F1 0.860(GPT-5.2), 귀속 LLM 4종 범위 0.814–0.860(Claude-4.5-Haiku 포함). 그래프로 정답 예측 0.776 대 전체 trajectory를 본 judge 0.738 |

MindSearch의 과정은 이렇다.

1. planner가 원 질문으로 root 노드를 추가한다.
2. planner가 생각을 쓰고, 하위 질문 노드와 엣지를 추가하는 코드 블록 하나를 낸다(한 출력에 블록 하나, 노드 하나에 질문 하나).
3. 코드가 Python 인터프리터에서 실행되며 새 노드마다 WebSearcher가 돈다. 부모 노드의 (질문, 답)이 history로, root 질문이 topic으로 넘어간다.
4. 결과를 보고 planner가 다음 노드를 더한다. 그래프가 점점 자란다.
5. add_response_node가 나오면 summary 프롬프트로 최종 답을 쓴다. 코드 없이 답하거나 max_turn=10에 닿아도 끝난다.

MindSearch 저자들은 "By integrating with the Python interpreter, WebPlanner interacts with the graph through unified code actions, dynamically constructing the reasoning path."라고 적는다(§2.1).

Argus는 결과를 "Every factual claim in y⋆ traces back to specific evidence nodes and their source URLs so the pair y⋆ and 𝒢 is a fully auditable answer."라고 적는다(§2.2).

SearchAtlas 저자들은 "High-scoring errors illustrate that well-organized reasoning is necessary but not sufficient for trajectory success."라고 경고한다(§5.5).

그리고 "For sequential-constraint questions, effective strategies address one constraint at a time rather than wasting effort in unused evidence dispersed across side branches or abandoned paths."라고 관찰했다(§4.2).

단서: Argus는 Navigator RL과 대량 연산(질문당 Searcher 출력 0.4M~25.6M 토큰)이 필요하다. SearchAtlas는 계획 방법이 아니라 사후 분석이고 영어 정답형 과제만 다룬다. MindSearch는 노드 실패 뒤 되돌아가는 기능이 없고 포기(response 노드)만 있다.

[추정] 작은 모델에 코드형·긴 형식 계획을 프롬프트로만 시키면 무너질 수 있다(사례: PlanRAG Table 11, LPKG의 CodeQwen 0.110 — 2개). 반대 사례: 같은 표의 Llama3-8B는 0.369로 버텼고, CoG·MindSearch·ToG-2는 7~8B에서 이득을 냈다. 갈리는 조건(백본 세대, 계획 형식 길이, 미세조정 여부)은 이 자료로 판단할 수 없다.

## 보충 갈래

### 외부 검증기 결론의 원 출처

비평가가 짚은 빈 곳은 이랬다. '자기평가·자기수정은 약하니 외부 검증기가 replan을 일으켜야 한다'는 결론을 가장 세게 받치는 수치가 LLM-Modulo의 2차 인용으로만 들어와 있었다. 보충 갈래가 원 출처 14개를 다시 열었다.

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [PlanBench](https://arxiv.org/abs/2206.10498) | planner(Fast Downward)와 validator(VAL)로 LLM 계획을 기계 채점, 이름을 난독화한 도메인 | translator가 PDDL↔자연어, plan-end tag까지 잘라 VAL로 | GPT-4 Blocksworld plan generation 206/600(34.3%), plan verification 352/600(58.6%), one-shot, temperature 0 |
| [Valmeekam 등 2023](https://arxiv.org/abs/2305.15771) | autonomous 대 LLM+LPG(LLM 계획을 sound planner의 seed로) 대 VAL backprompting | VAL이 승인하거나 15라운드면 끝 | VAL backprompt: Blocksworld 41/50(82%), Logistics 35/50(70%), Mystery BW 5/50(10%), GPT-4. 분모는 one-shot에서 이미 실패한 50개 |
| [Gundawar 등 2024](https://arxiv.org/abs/2405.20625) | LLM-Modulo를 TravelPlanner에. Reformatter가 JSON으로, 이진 critic들이 backprompt를 붙임 | 모든 critic 동의 또는 10회 | final pass rate GPT-4-Turbo 4.4% → 20.6%(4.6배). GPT-3.5-Turbo 0.0% → 5%(validation 180, sole-planning) |
| [Stechly 등 2024](https://arxiv.org/abs/2402.08115) | 같은 GPT-4가 답·검증·비판(LLM+LLM) 대 sound 검증기, 피드백 상세도, 비판 없는 재샘플링 | 아래 번호 목록 | Blocksworld: 한 번 40 / LLM+LLM 55 / sound 이진 60 / 첫 오류 87 / 모든 오류 83 / 재샘플링 k=15 68, k=25 72. Graph Coloring: LLM+LLM 2 / sound 이진 38. GPT-4 검증기 FNR Graph Coloring 95.8%(113/118) |
| [Valmeekam 등 2023b](https://arxiv.org/abs/2310.08118) | LLM+LLM planning, 피드백 형식 무제한 | verifier LLM이 승인하거나 15회 넘으면 멈춤 | LLM+LLM 55/100 대 LLM+VAL 88/100 대 generator 단독 40/100. verifier LLM이 틀린 plan 45개 중 38개를 유효로 판정 |
| [SCORE](https://arxiv.org/abs/2404.17140) | verifier(self·gpt-4·oracle)와 refiner(LoRA)를 분리, 첫 오류 step만 고치게 학습 | refine 1회 고정 | LLaMA-2-13B GSM8K 초기 37.2 → self-verifier 37.5 / gpt-4 verifier 41.4 / oracle 46.0. self-verifier F1 36.0~56.8. CSQA 수치는 앞 노트 #검증·test-time compute·cascade |
| [CRITIC](https://arxiv.org/abs/2305.11738) | 같은 모델이 검색·인터프리터와 상호작용해 critique, 수정 | QA는 최대 3회, 두 번 연속 같은 답이면 멈춤 | GSM8k ChatGPT PoT 72.5 → 78.2, 도구 없는 판 77.0. QA에서 자기 critique만 쓰면 F1 −0.03 / +2.33 |
| [Tyen 등](https://arxiv.org/abs/2311.08516) | 오류 찾기와 고치기를 분리. 오류 위치가 주어지면 그 step만 다시 뽑는 backtracking | 아래 번호 목록 | 오류 위치 찾기 최고 GPT-4 52.87. oracle 위치로 backtracking: tracking shuffled objects 원래 오답 +43.92 / 원래 정답 −6.67(PaLM 2 Unicorn) |
| [Olausson 등](https://arxiv.org/abs/2306.09896) | 코드 self-repair를 같은 샘플 수의 i.i.d. 샘플링과 비교 | 생성 → 테스트 → 피드백 → 수정 | GPT-4 피드백 대신 사람 피드백이면 repair 성공 33.3% → 52.6%. 명백히 틀린 피드백 GPT-4 32/80, 사람 7/80 |
| [GenRM](https://arxiv.org/abs/2408.15240) | 검증을 'Yes' 토큰 확률로, 검증 CoT K=32개 평균, Best-of-N | 고르기만, 루프 없음 | GSM8K Best-of-N 73% → 93.4%(Gemma2-9B 검증기, Gemini 1.0 Pro 해답) |
| [ThinkPRM](https://arxiv.org/abs/2504.16828) | long CoT 모델을 생성형 step 검증기로 가볍게 fine-tune | 형식·gold label 일치·길이로 거른 1K chain | 학습 1K chain(8K step label) 대 DiscPRM 712K label. QwQ-32B-Preview fine-tune에 A100 80GB 한 장 4.5시간 |
| [Weaver](https://arxiv.org/abs/2506.18203) | 약한 검증기 33개 점수를 라벨 거의 없이 가중 결합 | weak supervision으로 검증기별 정확도 추정 | 평균 87.7% 대 다수결 72.2%(Llama 3.3 70B 생성, K=100). 8B 설정 다수결 57.2% → 70.0% |
| [When To Solve, When To Verify](https://arxiv.org/abs/2504.01005) | 해답 수 S와 검증 수 V를 compute로 맞춰 비교 | C(S,V)=S(1+λV) | GenRM-FT가 self-consistency와 같아지려면 compute 8배(Llama-3.1-8B, MATH). QwQ-32B GenRM-Base는 4배. S_opt ∝ C^0.57, V_opt ∝ C^0.39 |

LLM-Modulo의 2차 수치는 이렇게 바로잡는다.

- 82%/70%/10%는 Valmeekam 2023 Table 4이고, 분모는 이미 실패한 50개라서 전체 인스턴스 대비 정확도가 아니다.
- '6배'는 Gundawar 본문·표에 없다. Gundawar는 4.6배(GPT-4-Turbo)와 0→5%(GPT-3.5-Turbo)를 보고한다.
- LLM-Modulo position 논문은 0.7%를 GPT-3.5-Turbo 최선 전략 수치라고 밝히지만, '6x of baselines'가 어느 모델·기준선끼리의 비율인지는 적지 않았다.

Stechly 등의 LLM+LLM 루프는 이렇게 돈다.

1. 하드코딩된 translator가 인스턴스를 프롬프트로 만들어 LLM에 보낸다.
2. 응답을 도메인별 critique 프롬프트로 감싸 별도 LLM 호출로 검증한다.
3. 검증 응답이 맞다고 하면 멈추고 그 답을 낸다.
4. 아니면 critique를 지시문으로 감싸, 지금까지의 상호작용 전체가 담긴 프롬프트에 덧붙여 다시 보낸다.
5. 15라운드에서 timeout으로 멈춘다.
6. ablation은 검증·비판을 sound 검증기로 바꾸고, 피드백 상세도를 줄이고, 끝으로 비판을 없앤다(재샘플링).

Stechly 저자들은 "In essence, even when the LLM generates a valid solution, the verifier LLM rejects it often enough that overall performance suffers."라고 적는다(§1).

상세도에 대해서는 "Perhaps surprisingly, Table 1 shows very little difference between these three conditions."라고 적었다(§5.2).

단서: 그 결론은 Graph Coloring(38/37/34), Game of 24(36/38), Mystery BW(10/8/6)에는 맞지만 Blocksworld(이진 60, 첫 오류 87)에는 맞지 않는다. Valmeekam 2023b의 Blocksworld도 이진 74% 대 첫 오류 86%(분모 50)였다.

Tyen 등의 backtracking은 이렇다.

1. 모델이 초기 CoT를 temperature 0으로 생성한다.
2. 오류 위치를 정한다(oracle 주석 또는 분류기).
3. 오류가 있으면 그 step 직전까지의 부분 trace로 그 step만 temperature 1로 다시 생성한다. 원래와 같은 step이 나오면 최대 8회 다시 뽑는다.
4. 새 step을 넣고 남은 step을 temperature 0으로 다시 생성한다. 되돌아감은 한 번이다.

Tyen 등은 "This suggests that the main bottleneck in self-correction methods is the identification of mistakes, rather than the correction process."라고 적는다(§4.2).

SCORE도 "3) The self-correction performance is largely bottlenecked by the verifier rather than the refiner."라고 적는다(§5.1).

Olausson 등은 "the most important factor determining whether self-repair will lead to a correct program or not is the diversity of the base samples that are generated up-front, rather than the diversity of the repairs sampled."라고 적는다(§4.1).

[Kamoi 등의 survey](https://arxiv.org/abs/2406.01297)는 이 결과들을 묶어 "Consequently, we conclude that no major work shows successful self-correction of responses from LLMs using feedback generated by prompting themselves under fair settings in general tasks."라고 정리한다(§4).

동시에 "These prior studies widely agree that self-correction can improve LLM responses when reliable external tools or knowledge suitable for improving feedback are available."라고 적는다(§5.1).

When To Solve 저자들은 "Interestingly, we find that SC is more compute-efficient than GenRM for most practical inference budgets across diverse models and datasets."라고 적는다(Abstract). 다만 MATH 가장 어려운 문제에서는 GenRM-FT가 self-consistency보다 최대 30% 상대 향상을 냈다.

단서: 14개 모두 계획 검증·수학·코드·객관식·정답 QA다. 정답이 하나로 정해지지 않는 엔티티 연결·KG 관계에서 검증기 강도별 결과를 잰 자료는 없다. Qwen 32B급을 검증기로 쓴 수치는 ThinkPRM의 QwQ-32B-Preview와 When To Solve의 QwQ-32B뿐이다. ThinkPRM 부록 C.1은 QwQ가 LoRA로 학습이 어렵고 학습 뒤에도 invalid 판정이 많다고 적는다.

[추정] 병목은 고치는 능력이 아니라 오류를 찾는 능력이고, 그래서 판정 자리에 sound 신호를 두는 것이 재시도·replan보다 먼저다(사례: SCORE §5.1, Tyen §4.2, Olausson Abstract, Stechly의 FNR, Kamoi §7 — 5개).

### 30B급 오픈 deep research

비평가가 짚은 두 번째 빈 곳은 30B급 오픈 모델로 planning·thinking 구조를 비교한 근거가 없다는 것이었다. 보충 갈래는 Qwen3-30B-A3B·QwQ-32B 계열의 긴 과제 에이전트 12개를 열었다. 항목들은 '다음 step에 무엇을 넘기는가'로 네 무리로 나뉜다.

| 무리 | 다음 step 입력 | 항목 |
|---|---|---|
| 단일 문맥 누적형 | 생각·행동·관찰을 모두 이력에 쌓음 | Tongyi ReAct 모드, WebSailor, WebDancer, MiniMax-M2, AutoForge |
| 문맥 재구성형 | 질문 + 매 round 다시 쓴 report(또는 접은 요약) + 직전 행동·관찰, 생각은 버림 | IterResearch, WebResearcher, Tongyi Context Management·Heavy 모드, AgentFold |
| 산출물 자료구조형 | 문맥 밖 계획·산출물 객체를 도구로 고침 | WebThinker, WebWeaver(#산출물이 결과인 과제) |
| 역할 분리형 | planner·caller·summarizer를 다른 모델 사본으로 | α-UMi |

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [Tongyi DeepResearch](https://arxiv.org/abs/2510.24701) | 30B-A3B를 ReAct와 Context Management(report + 직전 상호작용만) 두 형식으로 함께 학습. Heavy는 n개 병렬 후 report와 답만 모아 종합 | Agentic CPT → SFT → GRPO 변형(0/1 정답 보상) → model merging | HLE 32.9 / BrowseComp 43.4 / GAIA 70.9(어느 추론 모드인지 보고서에 없음). Heavy BrowseComp 58.3 |
| [Tongyi 추론 코드](https://github.com/Alibaba-NLP/DeepResearch/blob/main/inference/react_agent.py)(f72f75d) | ReAct 루프, 도구 결과는 `<tool_response>`로 감싼 user 역할 | 문맥이 110×1024 토큰을 넘으면 '지금 정보로 가장 그럴 법한 답'을 강제 | MAX_LLM_CALL_PER_RUN 100, 시간 상한 150분 |
| [IterResearch](https://arxiv.org/abs/2511.07327) | 상태 = (질문, evolving report, 직전 행동·도구 응답). 이전 궤적과 생각은 버림 | 아래 번호 목록 | 평균 49.1 대 이력 누적(Mono) 36.5, Qwen3-30B-A3B, 40K 대 64K 문맥. 학습 없이 프롬프트만: BrowseComp ReAct 대비 o3 +12.7pp, DeepSeek-V3.1 +19.2pp |
| [WebResearcher](https://arxiv.org/abs/2509.13309) | Think(다음 round에 안 넘김) · Report · Action, 병렬 n + Synthesis Agent | n은 1→8에서 이득이 가장 큼 | heavy HLE 36.7, BrowseComp 51.7(Synthesis는 Qwen3-235B-A22B) |
| [WebThinker](https://arxiv.org/abs/2504.21776) | QwQ-32B가 한 시퀀스 안에서 검색·섹션 쓰기·점검·편집 토큰. 계획은 처음 한 번(최대 8단계), 보고서는 문맥 밖 article 객체 | 쓰기는 보조 모델(Qwen2.5-32B)이 BM25 top 3 문서로 | 보고서 평균 8.0(프롬프트만) / 8.1(DPO). 자동 초안을 빼면 6.6 |
| [WebSailor](https://arxiv.org/abs/2507.02592) | 교사 LRM의 긴 생각을 버리고 행동-관찰만 남긴 뒤 짧은 생각으로 다시 씀 | 32k 토큰 넘는 궤적 제외 | BrowseComp-en 10.5, GAIA 53.2(Qwen2.5-32B) |
| [WebDancer](https://arxiv.org/abs/2505.22648) | 짧은 생각(GPT-4o) 대 긴 생각(QwQ-Plus) 궤적으로 학습 비교 | 긴 생각 데이터는 이전 생각을 빼고 생성 | Qwen2.5-32B Pass@3 42.72 대 45.63, invalid 4.20% 대 13.59%. Qwen2.5-7B invalid 0.65% 대 21.36% |
| [MiniMax-M2](https://www.minimax.io/news/why-is-interleaved-thinking-important-for-m2) | 생각 보존(interleaved thinking) 학습, 이전 round 생각을 남김 대 버림 | 매 turn Plan → Act → Reflect | SWE-Bench Verified 69.4 대 67.2, Tau^2 87 대 64, BrowseComp 44.0 대 31.4, GAIA 75.7 대 67.9(총 229.9B, 활성 9.8B) |
| [AutoForge](https://arxiv.org/abs/2512.22857) | Qwen3-Thinking-30B-A3B를 보존·삭제 각각으로 학습·추론 | 환경 합성 + RL | τ²-Bench Retail 74.8 대 71.05, Airline 62.0 대 59.5, Telecom 76.3 대 73.3(그림 벡터 좌표로 환산) |
| [α-UMi](https://arxiv.org/abs/2401.07324) | 같은 backbone 사본 셋. planner가 'Next: caller / conclusion / give up'으로 분기 | 전체 과제로 학습 → 역할별로 이어 학습 | Plan ACC 88.92 대 단일 모델 81.92(LLaMA-2-chat-7B). 역할별로 바로 학습하면 Act. EM 45.11로 오히려 나쁨. 실시간 ToolBench 수치는 앞 노트 #역할 분리와 오케스트레이션 |
| [AgentFold](https://arxiv.org/abs/2510.24699) | 매 step 생각 끝에 접기 지시 {"range":[k, t-1], "summary"}를 내 이력을 multi-scale 요약으로 다듬음. 생각은 버리고 explanation만 남김 | 막다른 길의 step 묶음을 결론 한 줄로 접음 | BrowseComp 36.2, GAIA 67.0(Qwen3-30B-A3B-Instruct-2507, SFT만). 100턴에 문맥 약 7k 토큰, ReAct보다 92% 작음 |

IterResearch의 과정은 이렇다.

1. 상태를 (질문, 빈 report, 없음)으로 시작한다.
2. 정책이 (생각, 새 report, 행동)을 낸다. report에는 'Progress Achieved' 다섯 항목(사실·증거, 분석 결론, 출처와 검증 상태, 불확실성·빈틈, 이전 진행과의 통합)과 'Next Steps Plan'을 함께 쓴다.
3. 프롬프트의 결정 질문 "Are you certain that no further verification or information gathering is needed to provide the final answer?"(Appendix E.2)에 YES면 `<answer>`로 끝낸다. NO면 `<tool_call>`을 낸다.
4. 환경이 도구 응답을 돌려준다.
5. workspace를 (질문, 새 report, 이번 행동·응답)으로 다시 짓는다. 되돌아감은 없고, 앞 round의 오류는 report 개정으로 고친다.
6. round 수가 T_max에 닿으면 강제로 끝난다(추론 때 GAIA 32, BrowseComp 256).

Tongyi 보고서는 계획에 대해 "Planning refers to problem decomposition and first-step action prediction. A key insight is that planning accuracy is highly correlated with whether an agent can successfully complete a task."라고 적는다(§3.3.2).

IterResearch는 생각을 버리는 설계를 "is deliberately discarded, with only the synthesized knowledge preserved in"이라고 적는다(§3.1.2).

MiniMax는 보존이 깨지는 원인을 "The root cause is that the widely-used OpenAI Chat Completion API does not support passing reasoning content back in subsequent requests."라고 짚는다(공식 글).

AutoForge는 Qwen3 기본 템플릿이 "which discards previous reasoning content when a new user query is received"라고 적고, "we modify both the training and inference procedures to preserve all thinking content"라고 바꿨다(§3.4).

AgentFold 저자들은 "We find that even the most advanced LLMs cannot reliably produce AgentFold’s accurate, structured, multi-part responses through prompt engineering alone."라고 적는다(§3.4).

단서:

- 보존 대 삭제 수치는 모두 그 형식으로 학습한 모델에서 나왔다.
- IterResearch의 Mono 비교는 report 유무, 생각 삭제, 문맥 크기(40K 대 64K)가 한꺼번에 바뀌었고, 식 (4)는 Mono가 생각까지 쌓는지 밝히지 않는다.
- Tongyi 공개 코드는 서버가 `<think>`를 content에 담아 줄 때만 생각을 보존한다. OpenRouter처럼 생각을 별도 필드로 주는 서버에서는 주석 처리된 react_agent.py:86-88을 풀어야 한다.
- WebDancer Table 3 캡션은 벤치마크를 적지 않아, Pass@3 값이 모두 103 분모와 맞는다는 점에서 GAIA로 추정했다.

[추정] 결과를 가르는 것은 생각을 남기느냐 자체보다 다음 step이 받는 입력이 학습 분포와 맞느냐다(사례: MiniMax-M2의 보존 학습 모델에서 삭제 손해, AutoForge의 형식별 학습, IterResearch의 report 학습, WebDancer의 데이터 생성 때 이전 생각 제외 — 4개).

### 산출물이 결과인 과제

비평가가 짚은 세 번째 빈 곳은 결과가 행동이 아니라 산출물(위키 문서, 정규화한 용어, KG 링크)인 과제의 planning 근거였다. 보충 갈래는 10개를 열었다.

| 출처 | 무엇을 했나·구조 | 과정 | 수치(조건) |
|---|---|---|---|
| [STORM](https://arxiv.org/abs/2402.14207) · [코드](https://github.com/stanford-oval/storm) | perspective별 질문 대화로 자료를 모으고 outline을 계획 단위로 | 아래 번호 목록 | heading soft recall 86.26 / entity recall 40.52 대 Direct Gen 80.23 / 32.39(GPT-3.5, FreshWiki 100편) |
| [Co-STORM](https://arxiv.org/abs/2408.15232) | 공유 mind map(concept tree)에 정보 조각을 insert, 쌓이면 reorganize. moderator가 새 방향 질문 | insert: embedding으로 후보를 뽑고 LLM이 'insert / step / create'로 한 층씩 내려감 | 첫 층 insert 정확도 39.39% 대 embedding만 24.24%, LM만 3.03%. 논문값 expert 3·reorganize 10개·moderator 2턴, 코드 기본값은 expert 2·3턴 |
| [OmniThink](https://arxiv.org/abs/2501.09751) | information tree 확장 + conceptual pool(모은 insight) reflection | leaf마다 확장 필요를 LLM이 판정, 최대 깊이에서 멈춤 | Qwen-Plus backbone Relevance 4.00 / Depth 4.06 대 STORM 2.72 / 3.00(WildSeek, Prometheus2 judge) |
| [WriteHERE](https://arxiv.org/abs/2503.08275) | retrieval·reasoning·composition 유형이 붙은 task DAG를 재귀로, 노드 상태 Active·Suspended·Silent | 모든 노드가 Silent면 종료 | Depth 4.79 대 STORM 4.30(GPT-4o, o1-preview judge 1–5) |
| [WebWeaver](https://arxiv.org/abs/2509.13312) | planner가 증거 ID 인용이 달린 outline을 다시 씀, 상세 증거는 memory bank. writer는 섹션마다 증거를 꺼내 쓰고 지움 | planner·writer 각각 LLM 호출 최대 40회, 84,000·100,000 토큰 상한 | Claude-sonnet-4 인용 정확도 93.37. Qwen3-30B-A3B-Instruct 프롬프트만 25.00 → SFT 85.90%. outline 재작성 1→3회 품질 81.9 → 92.3 |
| [EDC](https://arxiv.org/abs/2404.03868) | Extract(OpenIE) → Define(relation마다 정의) → Canonicalize(정의 embedding으로 후보 → 객관식) + refinement 1회 | 아래 번호 목록 | WebNLG precision 0.956, relation 200 대 CESI 0.724, 280(OIE GPT-3.5-turbo, 사람 평가) |
| [KGGen](https://arxiv.org/abs/2502.09956) | 추출 → 집계 → embedding cluster(128개) 안에서 top-16 후보로 LLM이 정확한 중복을 판정 | cluster에 남은 항목이 없으면 멈춤 | MINE-1 평균 66.07% 대 GraphRAG 47.80%, OpenIE 29.84%. 소설 1M자에서 entity 22.4%, edge 23% 감소 |
| [iText2KG](https://arxiv.org/abs/2409.03284) | 문서 순서대로 global entity 집합에 cosine 임계값(0.7)으로 맞춰 넣음 | 입력 소진이면 멈춤 | 미해결 entity 비율 Websites 0 대 OpenAI Function 0.31(GPT-4). global entity 문맥이면 triplet precision 0.83 대 local 0.94 |
| [Infini Memory](https://arxiv.org/abs/2606.10677) | buffer → 정규화 초안 → update planning(기존 문서 갱신 대 새 문서) → rewrite → split/merge | buffer 5000 토큰에서 flush, 5000 넘는 문서 split, 1000 미만 merge | 구조 정비를 끄면 76.0% → 69.3%(LongMemEval). selective forgetting 단일 hop 81.0% 대 다중 hop 35.0% |
| [KARMA](https://arxiv.org/abs/2502.06472) | agent 여덟 종류: 수집(ingestion), 읽기, 요약, entity 추출·정규화, relation, schema alignment, conflict resolution, evaluator | 한 번 통과, schema에 없으면 사람 검토 후보 | Genomics correctness GLM-4(9B) 0.623 대 single-agent 0.493, GPT-4o 0.880(DeepSeek-v3 judge) |

STORM의 과정은 이렇다.

1. 관련 주제 Wikipedia 목차를 모아 perspective N개를 만들고 'basic fact writer'를 더한다.
2. perspective마다 대화를 병렬로 돌린다. writer가 질문 하나를 만들고, expert가 검색어 여러 개로 검색해 인용 붙은 답을 쓴다.
3. writer가 'Thank you so much for your help!'로 시작하는 발화를 내거나 max_turn(코드 기본 3, 논문 5)에 닿으면 대화가 끝난다.
4. LLM이 주제만 보고 draft outline을 만든다.
5. draft와 모든 대화를 넣어 outline을 한 번 refine한다.
6. 섹션마다 검색해 병렬로 쓰고, 이어 붙인 뒤 중복을 지우고 lead를 쓴다. outline으로 되돌아가지 않는다.

EDC의 과정은 이렇다.

1. 텍스트마다 6-shot OIE로 open triplet을 뽑는다.
2. triplet의 relation마다 그 문맥에서의 정의를 쓴다.
3. 정의 embedding(E5-Mistral-7b)으로 schema에서 top-5 후보를 찾는다.
4. target schema가 있으면 LLM이 후보 중 하나 또는 'None of the above'를 고른다. 타당하지 않으면 그 성분과 triplet을 버린다.
5. target schema가 없으면 빈 schema에서 시작해, 합칠 수 없는 성분을 새로 더해 schema를 키운다.
6. refinement는 canonical 결과와 Schema Retriever 결과로 hint를 만들어 1단계부터 한 번 더 돈다. 2회째도 좋아졌지만 수익 체감으로 1회만 보고했다.

EDC 저자들은 "To prevent issues of over-generalization, LLMs assess the feasibility of each potential transformation. If a transformation is deemed unreasonable, indicating no semantic equivalent in the target schema, the component, and its related triplets are excluded."라고 적는다(§3.1).

KGGen 최신판은 LLM에게 "Then, the LLM is prompted to identify exact duplicates from this set, considering variations in tense, plurality, case, abbreviations, and shorthand forms."라고 판정 기준을 준다(§4.3).

정답이 없는 산출물 과제의 종료 판정은 네 종류로 모인다.

| 종류 | 예 |
|---|---|
| LLM 자기 선언 | STORM의 'Thank you so much for your help!', WebWeaver의 `<terminate>`, OmniThink의 '확장 필요 없음', WriteHERE의 IsAtomic |
| 소진·새 결과 없음 | KGGen(cluster 소진), iText2KG(문서 소진), Infini Memory retrieval(새 증거 없음) |
| 고정 상한 | STORM max_turn, OmniThink 최대 깊이, Co-STORM 평가의 검색 30회, EDC refinement 1회, Infini Memory retrieval 7라운드 |
| 수치 임계값 | Co-STORM reorganize 10개, Infini Memory 5000·1000 토큰, iText2KG cosine 0.7 |

WriteHERE는 분해 종료를 실패가 아닌 유형으로 정한다. "Unlike traditional as-needed decomposition methods that rely on execution failure to stop further planning, our approach introduces a different termination criterion. We only continue planning if certain subtask types necessitate further decomposition, ensuring that the final operations are always executable without redundant decomposition."(§4.1).

WebWeaver 저자들은 30B급의 한계를 "While 30B-scale LLMs (e.g., Qwen3-30b-a3b-Instruct-2507) possess strong foundational capabilities, they often exhibit deficiencies in stability and instruction-following when executing complex, multi-turn tool-calling sequences over long contexts."라고 적는다(§4.3).

Infini Memory는 병합을 늦추는 이유를 "Such eager maintenance may also introduce unstable edits before enough related evidence is available."라고 적는다(§3.3).

단서:

- WebWeaver의 Qwen3-30B 실험은 검색 안의 URL 선택·요약·증거 추출을 GPT-oss-120b가 맡아서 30B 단독 결과가 아니다.
- WriteHERE judge는 o1-preview다.
- 10개 모두 공개 Wikipedia·웹·PubMed·합성 데이터로 평가했고, 병합 결과의 정보 보존과 중복을 점수로 매긴 연구는 없다.
- KGGen 최신판은 'exact duplicates'를 고르게 해서 작성자마다 다른 낱말로 쓴 동의어는 덜 합칠 수 있다(원문 실험으로 확인되지 않음).

[추정] 정답 없는 산출물 과제의 종료는 LLM 자기 선언에 고정 상한을 겹친 형태가 표준이고, 충분함 판정 자체의 정확도는 아무도 재지 않았다(사례: STORM, OmniThink, WebWeaver — 3개). 반대 사례: WriteHERE는 IsAtomic 자기 판정만으로 분해를 멈추고, Limitations가 재귀 깊이 상한을 앞으로 할 일로 적어 고정 상한이 없었던 것으로 읽힌다.

## 사용자 과업에 옮기기

맥락: 운영 모델은 Qwen 32B, 실험은 Haiku, 검토는 Opus다. 과업은 네트워크 검증 부서에서 작성자마다 용어가 다르고 형식이 없는 보고서를 잇는 것이다. 단계는 용어 정규화와 링크 판단이고, 질문이 어떤 경로로 답에 닿았는지 기록하려 한다.

### 출발점

| 결정 | 출발점 | 근거 |
|---|---|---|
| 판정 신호 | [추정] 용어집 일치, 그래프 스키마, 출처 문단이 주장을 담는지를 이진 critic 코드로 만든다. LLM 판정은 재시도 신호로만 쓰고, 최종 승인은 critic 통과나 Opus 검토에 둔다 | 사례: Gundawar의 이진 critic + backprompt, Stechly의 GPT-4 검증기 FNR, Valmeekam 2023b의 FPR 38/45, SCORE의 gpt-4 verifier — 4개 |
| 계획 자료형 | [추정] 정규화는 EDC식 고정 단계(추출 → 정의 쓰기 → embedding으로 후보 좁히기 → 객관식 + 'None of the above')로 둔다. LLM 자유 계획은 '어느 보고서를 더 볼까' 같은 열린 질문에만 쓴다 | 사례: EDC, KGGen의 cluster 안 판정, Routine의 Qwen3-14B 32.6% → 83.3%, Co-STORM의 LM 단독 insert 3.03% — 4개 |
| 계획이 사는 곳 | [추정] 계획은 문맥 밖 파일·그래프(노드별 의존과 검증 함수)에 두고, 의존·순환·형식 검사는 코드가 한다 | 사례: VeriMAP의 노드 검증 함수, Gemini CLI tracker, Plan*RAG의 DAG, WebWeaver Qwen3-30B 프롬프트만 25.00 — 4개 |
| replan 트리거 | [추정] 노드 검증 실패 → 노드 재시도(상한 3) → 그래도 실패하면 실행 trace로 전체 replan(상한 5)에서 출발한다. 전체 replan은 보수적으로 일으키고, 정체는 규칙(반복 행동·응답)으로 감지한다 | 사례: VeriMAP 기본값, CrewAI의 'conservative' 지시와 max_replans 3, OpenHands StuckDetector 임계, KAG의 1회차 종료 비율 — 4개 |
| 피드백 형식 | [추정] 첫 오류 위치를 피드백에 넣을지와 같은 프롬프트로 다시 뽑을지는 사내 과제에서 직접 잰다 | 사례: Stechly Blocksworld 이진 60 대 첫 오류 87, 다른 세 도메인은 차이 작음, Tyen의 오류 위치 backtracking — 3개 |
| thinking | [추정] Qwen3-32B는 도구 결과를 tool 역할(또는 `<tool_response>`로만 감싼 user 메시지)로 넣어 템플릿의 보존 규칙이 맞물리게 한다. 서빙이 생각을 content에서 빼 이력에서 조용히 잃지 않는지 로그로 확인한다. 쉬운 매핑 판정은 non-thinking으로 둔다 | 사례: Qwen3-32B 템플릿, DeepSeek-V3.2의 user 메시지 흉내 경고, Tongyi 코드의 서버 의존, Overthinking의 쉬운 문제 라운드 증가, AdaptThink — 5개 |
| 긴 조사 문맥 | [추정] 여러 보고서를 훑는 조사는 IterResearch식 report 재구성(사실·증거 / 결론 / 출처와 검증 상태 / 불확실성 / 통합 + 다음 계획)을 프롬프트로 먼저 시험한다 | 사례: IterResearch 40K workspace와 프롬프트만 비교, AgentFold 문맥 크기, Chain of Mindset의 Context Gate — 3개 |
| 입구 라우터 | [추정] 질문 입구에서 '바로 조회 / 한 번 검색 / 계획 경로'를 나누고 그 결정을 경로 기록 첫 필드로 남긴다 | 사례: Adaptive-RAG oracle 62.80 대 classifier 54.52% 정확도, Gemini CLI의 Inquiry 분기, RTR — 3개 |
| 경로 기록 스키마 | [추정] SearchAtlas식 노드(질문, query, 사전 지식, 답)와 엣지 4종에 보고서 ID·작성자를 출처로 붙이고, support/contradict 라벨(Argus)을 더한다. 생각 텍스트는 보조 필드로 둔다 | 사례: SearchAtlas의 그래프 예측력과 Haiku 귀속, Argus 그래프 대 텍스트, faithfulness 25%·39% — 3개 |
| 산출물 종료 | [추정] 위키 병합은 Infini Memory식 buffer 임계값으로 늦추고, 종료는 새 결과 없음 + 고정 상한 + 자기 선언을 겹친다 | 사례: Infini Memory, KGGen, STORM — 3개 |

### 실험 순서

1. 평가셋과 판정자를 먼저 세운다. 아래 모든 비교가 같은 정답셋 위에서 이뤄져야 하기 때문이다. 방법은 앞 노트 #평가를 먼저 세우는 법에 있다.
2. 서빙과 템플릿을 확인한다. Qwen3-32B로 도구 루프를 한 번 돌려, 생각이 이력 어디에 남고 어디서 지워지는지 원문 프롬프트를 로그로 본다. 보존 규칙이 어긋나면 뒤 실험의 thinking 결과를 해석할 수 없다.
3. 기준선을 세운다. 고정 파이프라인 + hard critic 코드 + 경로 기록 스키마를 붙이고, LLM 판정과 replan은 넣지 않는다. 이후 모든 구조는 이 기준선과 견준다.
4. 판정 신호를 비교한다. (a) critic만 두고 재시도, (b) 첫 오류 위치 피드백, (c) Qwen 자기 판정, (d) Haiku·Opus 판정을 같은 호출 수의 다수결과 견준다. 이때 Qwen을 검증기로 쓴 FPR·FNR이 나온다. 이 수치는 조사 자료에 없던 값이다.
5. replan 트리거를 비교한다. 노드 재시도만, 전체 replan 상한 1·5, 정체 규칙 감지를 켜고 끄며 잰다. 전체 replan의 기여가 작으면(KAG처럼) 첫 계획과 정규화에 노력을 옮긴다.
6. thinking을 역할별로 잰다. 계획·링크 판단 자리와 추출·정규화 자리에서 non-thinking, thinking 보존, thinking 삭제(템플릿만 바꿈)를 따로 돌린다. 학습 없이 템플릿만 바꾼 보존 대 삭제 비교는 조사 자료에 없던 실험이다.
7. 계획 형식을 비교한다. 같은 Qwen 32B로 프롬프트 안 계획(write_todos식), 문맥 밖 DAG(코드 검증), report 재구성을 나란히 잰다. 비평가가 짚은 30B급 빈 곳을 직접 채우는 실험이다.
8. 학습은 마지막에 둔다. 검토된 연결 예시가 쌓이면 Qwen급 이하 검증기를 학습한다(GenRM식 Yes/No + 이유, ThinkPRM은 1K chain). 형식이 무너지는 자리(인용 ID, 접기 JSON)는 SFT 후보다(WebWeaver, AgentFold).

## 반대 증거와 열린 질문

### 반대 증거

| 주장 | 반대 증거 |
|---|---|
| 외부 검증기가 늘 낫다 | compute를 맞추면 낮은 예산에서는 다수결이 이긴다(When To Solve). 수정보다 초기 샘플 다양성이 중요했다(Olausson). 비판 없이 다시 뽑기만 해도 대부분 도메인에서 이득이 남았다(Stechly) |
| 피드백 상세도는 차이가 작다 | Blocksworld에서는 이진 60 대 첫 오류 87로 컸다(Stechly Table 1) |
| 계획을 먼저 세우면 낫다 | Plan-and-Solve 이득은 GSM8K 1.8~2.9점, 학습 없는 1.5B에 계획 형식을 붙이면 8.3% → 2.9%(HiPER), GPT-3.5에서 PlanRAG가 IterRAG보다 낮음, 항상 계획하는 에이전트도 나빴음(Learning When to Plan) |
| 생각을 보존하면 낫다 | 생각을 버리고 report만 넘긴 IterResearch가 누적보다 높았다. 긴 생각 학습은 Qwen2.5-7B의 invalid를 21.36%로 올렸다(WebDancer) |
| 재계획을 반복할수록 낫다 | KAG는 질문 대부분이 1회차에 끝났고 회차를 줄여도 F1이 0.2~4.4%만 떨어졌다 |
| 구조화 탐색이 늘 깊이를 더한다 | AGoT 이득은 원판 GPQA에서 +0.9%였고 검색 QA EM은 IO가 대개 높았다. LLM 수 선택은 깊은 노드를 무시하는 모델로 가장 잘 설명됐다(Myopic Planning) |
| 다중 에이전트가 낫다 | Anthropic 리서치 시스템은 BrowseComp 분산의 80%를 토큰 사용량이 설명했다. VMAO는 단일 에이전트의 약 8.5배 토큰을 썼다 |
| 생각 텍스트는 근거를 보여 준다 | faithfulness 25%·39%, 보상 해킹을 말한 비율 2% 미만 |

### 열린 질문

| 질문 | 지금 근거 | 무엇을 보면 알 수 있나 |
|---|---|---|
| Qwen 32B에서 프롬프트 계획과 문맥 밖 자료구조 계획 중 무엇이 나은가 | 같은 조건 수치 없음. WebWeaver Qwen3-30B 25.00(120B 보조 포함), IterResearch 프롬프트만은 o3·DeepSeek-V3.1뿐, WebThinker QwQ-32B ablation | 같은 Qwen 32B로 세 형식을 나란히 재기(#실험 순서 7) |
| 학습 없이 Qwen3-32B 템플릿만 바꿔 생각을 보존·삭제하면 어떻게 되나 | 1차 자료 없음. 수치는 모두 형식별 학습 모델 | 템플릿 수정 실험(#실험 순서 6) |
| Qwen 32B를 프롬프트 검증기로 쓸 때 FPR·FNR은 | ThinkPRM은 QwQ가 LoRA 학습이 어렵다고 적음, When To Solve의 QwQ-32B GenRM-Base | 사내 정답셋으로 측정(#실험 순서 4) |
| 정답이 하나가 아닌 과제(엔티티 연결, KG 관계)에서 검증기 강도별 효과는 | 14개 원 출처 모두 정답형 과제 | 사내 연결 정답셋에서 critic·LLM·Opus 판정 비교 |
| entity linking이 빗나갈 때 계획·탐색이 어떻게 무너지나 | ToG-2 KG 완전도 실험, CoG의 후보 pool backtrack, KAG 정렬. 모두 공개 Wikipedia·Wikidata | 사내 문서에서 linking 오류를 넣어 경로 기록으로 붕괴 지점 보기 |
| PlanRAG는 작은 모델에서 무너지고 CoG·MindSearch는 7~8B에서 이득을 낸 조건 차이는 | 백본 세대, 계획 형식, 미세조정이 섞임 | 같은 백본에서 계획 프롬프트 길이만 바꾸기 |
| replan 트리거(고정 주기, 실패 기반, 검증기 기반, 학습된 시점)를 통제 비교하면 | Learning When to Plan의 빈도 비교, VeriMAP의 replan 제거, Plan-and-Act의 정적 대 동적뿐 | 같은 과제에서 트리거만 바꾸는 실험(#실험 순서 5) |
| 병합 결과의 정보 보존과 중복을 어떻게 점수 매기나 | GoT document merging(LLM 점수) 외에 2025~2026 연구 없음 | GoT 인용 논문을 'merge'로 거르기 |
| 정답 없는 과제에서 '충분함' 판정은 얼마나 맞나 | 자기 선언 + 상한뿐, 정확도를 잰 연구 없음 | 사람이 '충분' 라벨을 단 표본으로 종료 판정 정확도 재기 |
| 한국어로 생각시킬 때 전환 토큰·언어 혼용은 | TIP 목록은 영어, R1의 언어 일관성 보상은 성능 소폭 하락 | 한국어 사내 질의에서 생각 언어 고정 여부 비교 |
| 에이전트 궤적에서 생각이 실제 행동 근거를 드러내나 | faithfulness 실험은 객관식 힌트뿐 | 경로 그래프의 PK 엣지와 생각 텍스트 대조 |
| 피드백 상세도의 효과가 사내 과제에서 어느 쪽인가 | Stechly에서 도메인마다 다름 | #실험 순서 4의 (a)와 (b) |
| 원문 안의 불일치는 어느 쪽이 맞나 | ToG Table 1·2의 CWQ 라벨 뒤바뀜, IterResearch 스케일링 수치 세 판(3.5→42.5, 5.5→50.1, 15.2/42.5), WebThinker 평균 45.4 대 44.9, Graph-R1 57.82 대 57.28, Search-R1 24% 대 41%, Weaver 98.7% 대 98.2% | 저자 저장소·정오표 |
| Tongyi Table 1·Pass@3은 어느 추론 모드인가 | 보고서에 없음, README로 ReAct 모드로 보일 뿐 | 저장소의 평가 스크립트와 vLLM reasoning parser 설정 |
| Claude Code와 deepagents가 todo 도구를 기본에서 뺀 근거는 | 문서·docstring의 이유 문장뿐, 수치 없음 | 변경 이력(PR, changelog) |
| Codex·Claude Code plan mode의 편집 금지는 코드 차단인가 | Codex는 update_plan 차단만 코드로 확인 | ModeKind::Plan을 참조하는 도구 핸들러와 sandbox 정책 |

## 확인하지 못한 자료

| 자료 | 왜 못 봤나 | 어디서 볼 수 있나 |
|---|---|---|
| OpenAI 'Learning to reason with LLMs', 'Introducing o3 and o4-mini' 블로그 | WebFetch·curl 모두 403 | 시스템 카드로 대신 열었다 |
| Qwen3-2507 분리 동기 문구('train Instruct and Thinking models separately') | 1차 출처(Qwen 팀 X 게시물)를 못 찾고 2차 보도로만 봄 | Qwen 팀 X 게시물 |
| Kimi K2 Thinking 기술보고서, MiniMax-M2 기술 문서, Kimi k1.5 | 열지 않음. Kimi의 보존 정책은 미확인 | 각 기술 문서 |
| DeepSeek-R1 v2 Appendix의 실패 시도 상세 | 읽지 않고 v1 §4.2로 대신함 | arXiv 2501.12948 최신판 |
| Thinkless, Learning When to Think(2505.10832) | 검색으로만 확인 | arXiv |
| Valmeekam 2023(2305.15771) Appendix A.10의 VAL backprompt 실제 문구 | 이미지로 보이고, 이 환경에 PDF 텍스트 추출 도구가 없음 | PDF |
| 그림에만 있는 수치: Gundawar Fig. 3, ThinkPRM Fig. 1·11·17~19, Weaver Fig. 3~5, When To Solve Fig. 1·4·5, Learning When to Plan 성공률, NATURAL PLAN self-correction, ReWOO Planner 7B(Fig. 7), AdaPlanner 수정 횟수별(Fig. 4a), Qwen3 thinking budget(Fig. 2), WebResearcher n별(Fig. 5) | 표가 없음 | 저자 저장소나 PDF 벡터 좌표 |
| TravelPlanner 원 논문의 GPT-3.5 0.6% 재확인, Kamoi의 CRITIC Fair/Unfair 판정, Kamoi Self-Detection 목록의 Tyen | 보충 검증에서 열지 않음 | 각 원문 |
| Self-Debug(2304.05128), RCI, FLARE, RARR, Self-Edit, Baldur, SCoRe | 열지 않음(Self-Debug는 lab/repos/papers/2304.05128에 받아 둠) | arXiv |
| ChatHTN 후속(2511.12901) 본문 | 초록만 열었음 | arXiv |
| 추론 패턴 2025~2026 후보: 2605.06040, 2605.28566, 2606.03883, 2601.11340, 2511.14772, 2510.06774 | 제목과 요약만 봄 | arXiv |
| 고전 변형: Skeleton-of-Thought, Step-Back, Algorithm of Thoughts, XoT, Thought Propagation, Forest-of-Thought, Decomposed Prompting, Chain-of-Draft | 다루지 않음 | arXiv |
| tree-of-thought-llm, graph-of-thoughts, LATS, rStar, framework-of-thoughts 저장소 | clone하지 않음 | GitHub |
| 계획 갈래 2025~2026 후보: 2606.20014, 2602.00929, 2512.09897, 2511.20993, 2501.08068, 2604.27859, 2608.14590 | 열지 않음 | arXiv |
| 계획 세부값: AdaPlanner refinement 상한, Plan-and-Act step 상한, AdaPlan-H 부록 A 프롬프트, APC template 예시, EAGLET 계획 예시 | 본문에서 못 찾음 | 부록·저장소 |
| LLMCompiler joiner 프롬프트(hub 'wfh/llm-compiler-joiner') | 노트북 출력에 없음 | LangChain hub |
| Claude Code plan mode·Task 도구 시스템 프롬프트, Agent SDK todo-tracking 문서 | 공개 저장소 없음 / 열지 않음 | Anthropic 문서 |
| OpenAI Agents SDK hosted_multi_agent_beta, OpenHands CodeAct 메인 프롬프트, Codex ext/goal | 열지 않음 | 각 저장소 |
| LlamaIndex StructuredPlannerAgent, DSPy ReAct, Semantic Kernel planner, AutoGen SelectorGroupChat, SWE-agent | 열지 않음 | 각 저장소 |
| GraphRAG DRIFT 공식 블로그 | 열지 않음. DRIFT의 논문 수치는 없음 | Microsoft Research 블로그 |
| AgentIR(2603.04384), S1-DeepResearch(2606.15367), 2508.09755, Deep Research survey(2508.12752) | 열지 않음 | arXiv |
| Chain-of-Knowledge, ReSP, EfficientRAG, LightRAG·PathRAG의 질의 경로 | 다루지 않음(LightRAG는 기준선으로만 봄) | arXiv |
| ReSum(2509.13313), WebSailor-V2, ParallelMuse, NestBrowse, WebLeaper | 저장소에서 이름만 봄 | Alibaba-NLP/DeepResearch |
| 'AgentForge' 동명 자료 둘(2601.13383, ICAART 2025) | 주제가 달라 넣지 않았고 검증도 열지 않음 | arXiv, ICAART |
| Tongyi 공식 vLLM 실행 스크립트의 reasoning parser 설정, Context Management 모드 단독 추론 코드 | 찾아보지 않음 | Alibaba-NLP/DeepResearch |
| OmniThink 최대 깊이 값·early stopping 조건·Expand/Reflect 프롬프트 | HTML에 기호로만 나오고 PDF를 열 도구가 없음 | github.com/zjunlp/OmniThink |
| WebWeaver planner 프롬프트 원문 | 보충 검증이 상한과 덧붙이는 문장만 확인 | lab/repos/DeepResearch/WebAgent/WebWeaver |
| EDC(clear-nus/edc), KGGen(stair-lab/kg-gen) 저장소의 프롬프트와 반복 코드 | 열지 않음 | GitHub |
| Co-STORM 논문 실험을 재현한 설정 파일 | 확인하지 않음 | stanford-oval/storm |
| KARMA 임계값 δ, ρ, θ_r, Θ의 실제 값 | 원문에 없음. 초록은 agent 아홉, 본문은 여덟 | 저자 문의 |
| Tracing the Thoughts of a Coding Agent Playing ARC-AGI-3(2610.11450) | 학습된 reasoning이 아니라 넣지 않음. 생각을 파일로 외재화하는 기록 연구 | lab/repos/papers/2610.11450/page.txt |

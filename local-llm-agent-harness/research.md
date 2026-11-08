# 로컬 LLM 에이전트 하네스 — 강연·방법·연구 조사

- 조사 날짜: 2026-10-22
- 물음: Qwen·Gemma 같은 로컬 LLM의 성능을 가중치보다 그 둘레의 에이전트(하네스)로 끌어올리는 강연·방법·연구에는 무엇이 있나. 사내 보고서를 위키·지식그래프로 잇는 과업에는 어떤 에이전트 구성이 맞나.
- 다루는 갈래: 여덟 개다. 처음 여섯은 강연·발표, 하네스 구조 연구, 학습 연구(SFT·증류·RL), 서빙·도구 생태계, 벤치마크와 실사용 사례, 사용자 용도에 가까운 연구(통신 문서 RAG·GraphRAG·엔티티 해석)다. 보충 둘은 첫 수집을 검토한 에이전트가 빈 곳으로 짚은 자리를 채웠다. 하나는 평가·판정자 신뢰도·문서 추출이고, 다른 하나는 한국어 도구 호출·엔티티 매칭·서빙 처리량이다.
- 방법: 조사 에이전트 여섯이 갈래 하나씩 자료를 모았고, 보충 에이전트 둘이 빈 곳을 채워 항목 153개가 모였다. 반박 검증 에이전트 여덟이 갈래마다 원문(논문 PDF·자막·전사·모델 카드·저장소)을 다시 열어 항목마다 판정했다. 81개는 수집한 서술 그대로 맞았고, 72개는 서술을 고쳐야 맞았다. 틀렸거나 끝내 열지 못한 항목은 없었다. 작성 뒤에는 대조 에이전트가 본문 수치를 검증 결과와 맞췄고, 작성자(메인 세션)가 결론을 받치는 출처 여섯 개(Harness-Bench, Same Model Different Harness, Small Agents, aider, Gemma 4 함수 호출 문서, TWIX)를 직접 다시 열었다. 그 대조에서 Harness-Bench의 2026-10-15 개정판(v2)이 로컬 백엔드를 넣어 결론이 바뀐 것을 찾아 반영했다.

## 읽는 법

- 출처는 문장 안에 링크로 적는다. 링크가 붙은 서술은 반박 검증이 원문으로 다시 확인한 내용이다. 수집 때 서술이 틀렸던 항목은 고친 내용만 옮겼다.
- 수치는 반박 검증이 원문에서 다시 찾은 것만 쓴다. 표의 수치에는 모델·과제·조건을 붙인다.
- 큰따옴표 안은 원문 그대로다. 자동 자막에서 온 인용은 오기를 그대로 두고 옆에 밝힌다.
- 실행하지 않고 여러 사례에서 끌어낸 판단에는 `[추정]`을 앞에 달고, 사례와 개수를 같은 문장 끝 괄호에 붙인다.
- "단서:"는 그 근거를 옮겨 쓸 때 함께 들고 가야 할 조건이다.
- 하네스는 모델 둘레에서 프롬프트·도구·루프·검증·컨텍스트를 짜는 코드를 말한다.

## 결론

로컬 모델 성능을 올리는 손잡이는 여섯 자리에 있다. 하네스 구조, 가중치를 건드리지 않는 프롬프트·컨텍스트 최적화, 출력 형식, 바깥 검증과 cascade, 서빙 설정, 학습이다.

[추정] 32B급에서 가장 싸고 확실한 이득은 서빙 설정을 바로잡고 하네스로 모델이 판단할 폭을 좁히는 데서 나온다(사례: Ollama 2k 컨텍스트에서 aider 점수 71.4→51.9, 좁은 창에서 처치 묶음만으로 완전 해결 43→72, 도구 46개를 19개로 줄이자 실패가 성공으로 바뀐 질의, 프롬프트로 단계를 나누자 시험한 네 모델이 모두 떨어진 결과 — 4개).

학습은 과제가 좁고 형식이 고정되며 검증 가능한 보상이 있을 때 큰 폭으로 이긴다. 다만 [Qwen3-Coder-Next 보고서](https://arxiv.org/abs/2603.00729)가 "Models trained on trajectories from one scaffold do not transfer strongly to others."라고 적었듯 학습한 능력은 학습 때의 하네스에 묶이기 쉽다. 단서: 이 관찰은 mid-training 토큰 양을 늘리는 분석에서 나왔고 방향에 따라 다르다(OpenHands→SWE-Agent는 나쁘고, 반대 방향은 어느 정도 된다). 그래서 학습은 하네스를 굳힌 뒤에 둔다.

사용자 맥락에서는 이 순서로 손댄다.

1. 한국어 사내 보고서로 작은 정답셋을 만들고, Opus 판정자를 사람 라벨에 맞춰 검증한다. 하네스를 바꿀 때마다 그 판정으로 나아졌는지 재야 하기 때문이다(#평가를 먼저 세우는 법).
2. 운영 체크포인트에 맞춰 파서·thinking·컨텍스트·샘플링을 고정한다. "Qwen 32B"가 Qwen3-32B인지 Qwen3.5 이후 27B인지에 따라 설정이 모두 달라진다(#서빙 설정의 함정).
3. 용어집을 결정적 단계로 두고, LLM은 용어집이 좁힌 후보 중에서 고르게만 한다(#사내 보고서 연결에 옮기기).
4. 학습은 마지막에, 판정이 반복되고 정답을 만들 수 있는 좁은 단계(동의어 판정 같은)에만 둔다.

## 손잡이 한눈에

| 손잡이 | 무엇을 바꾸나 | 이득이 나온 조건 | 절 |
|---|---|---|---|
| 하네스 구조 | 역할 분리, 고정 워크플로, 도구 수, 컨텍스트 | 모델이 약하거나 창·도구 예산이 빡빡할 때 | #하네스 구조 |
| 가중치 없는 최적화 | 시스템 프롬프트, 경험 규칙, playbook | 피드백 신호(정답·실행 결과)가 믿을 만할 때 | #가중치를 건드리지 않는 최적화 |
| 출력 형식 | 스키마, constrained decoding, 형식 문구 | 추론 자리를 남기고 답만 묶을 때 | #출력 형식과 구조화 생성 |
| 검증·cascade | 외부 verifier, 다회 샘플, step 단위 승격 | 검증자가 transcript 밖 신호를 볼 때 | #검증·test-time compute·cascade |
| 서빙 설정 | 샘플링, 템플릿·파서, 컨텍스트, 양자화, thinking | 늘 — 실패가 에러 없이 숨는다 | #서빙 설정의 함정 |
| 학습 | SFT·증류·RL | 좁은 과제, 검증 가능한 보상, 하네스를 굳힌 뒤 | #학습이 값을 하는 때 |

## 하네스 구조

### 하네스 효과의 크기

같은 모델에서 하네스만 바꿔도 점수가 수 점에서 사십 점 가까이 갈리고, 로컬 모델에서 가장 크게 갈렸다.

| 출처 | 모델 | 무엇을 바꿨나 | 수치(조건) |
|---|---|---|---|
| [Harness-Bench 논문 v2](https://arxiv.org/html/2605.27922v2) | 백엔드 10개(로컬 Gemma-4-31B·Qwen3.8-27B 포함) | 하네스 7개 | 일반 과제에서 하네스 간 점수 차가 나머지 9개 모델은 5.0~9.5점, Qwen3.8-27B는 39.2점. 평균 점수와 하네스 간 편차의 Spearman ρ = −0.76(Qwen 제외 −0.67) |
| [Etsy 강연](https://www.youtube.com/watch?v=2e9ANoOEn28)이 인용한 Harness-Bench v1 | API 모델 백엔드 8개 | 하네스 6개 | 과제 106개에서 NanoBot 76.2, OpenClaw 52.4, 23.8점 차(백엔드 8개 평균) |
| [SWE-bench 리더보드 원자료](https://github.com/SWE-bench/swe-bench.github.io/blob/master/data/leaderboards.json) | Qwen3-Coder-480B-A35B | 스캐폴드 | SWE-bench Verified: OpenHands 69.6 대 mini-SWE-agent 1.0.0 55.4 |
| [Tmax](https://arxiv.org/abs/2606.23321) | Qwen3.5 9B | 하네스 4종 | TB-Lite: 자체 41.9, OpenHands 36.0, mini-SWE-agent 44.1, Terminus-2 36.4(3회 평균) |
| [Same Model, Different Harness](https://arxiv.org/abs/2608.26218) | Qwen3.6-35B-A3B(Q4_K_XL, llama-server, greedy) | 같은 하네스의 처치 묶음(오래된 tool result 축약, 반복 감지, 명령 안전장치) | Verified 169과제, 20,480 창, 480초: 완전 해결 43→72. 262,144 창: 102→101(공통 169과제로 사후에 맞춘 비교) |

Etsy 발표자는 "Um, and the really interesting thing is that for weaker models, the harness matters more."라고 말한다. 발표가 인용한 v1의 23.8점은 모델 하나에서 하네스만 바꾼 값이 아니라 API 백엔드 8개 평균끼리의 비교였다.

2026-10-15에 개정된 v2는 로컬 백엔드를 넣고 발표자의 말을 모델별로 확인한다. 4.2절은 "General-task score gaps across harnesses range from 5.0 to 9.5 points within nine models, and reach 39.2 for Qwen."이라고 적고, 5.1절은 "Higher mean performance is associated with smaller variation"이라고 적는다. 로컬 백엔드 중 Gemma-4-31B는 9개 모델 쪽(5.0~9.5점)에 들고, Qwen3.8-27B만 하네스에 크게 흔들렸다. 단서: 종합 점수에 LLM judge의 과정 평가가 섞인다. 39.2점은 Qwen3.8-27B 한 체크포인트의 값이고, 이 노트의 v2 수치는 조사 에이전트가 아니라 작성 뒤 대조에서 본문을 직접 열어 확인했다.

Same Model, Different Harness의 처치는 창이 넓으면 Verified·Pro에서 거의 효과가 없었다. 다만 FeatureBench는 262,144 창에서도 F2PF가 23.9%→30.7%로 올랐다. 단서: 단일 저자 프리프린트이고, 저자 자신의 하네스(Yuj) 하나에서 쟀으며, 처치 규칙 하나하나의 효과는 분리되지 않았다. 모든 결과는 480초 고정 예산 조건이다. Pro·FeatureBench의 262K 행은 이전 캠페인과의 과거 비교라 지금의 처치 묶음을 그대로 재현한 값이 아니다. 다른 모델로 옮기면 해결 수가 모두 늘었지만, Nemotron-Cascade 2의 증가(16→25)는 McNemar p=0.0636으로 유의하지 않았다.

SWE-bench 리더보드의 두 값은 서로 다른 제출이다. 같은 OpenHands라도 [Nebius](https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b)가 잰 Qwen3-Coder-480B는 64.7(100턴)/66.5(500턴)로 리더보드의 69.6과 달라서, 스캐폴드 버전·설정에 따라서도 수치가 갈린다.

반대쪽 증언도 있다. [Graham Neubig](https://www.youtube.com/watch?v=eSJexCW-43Y)은 "you often don't need, you know, a whole lot of scaffolding to get the core capability of being really good at, uh, software engineering."이라고 말한다.

단서: 이 영상은 NeurIPS 2025 DL4C 초청 강연의 녹화본이 아니고 2026년 초에 같은 제목으로 다시 한 세미나다.

[추정] 하네스 효과는 모델이 약하거나 창·도구 예산이 빡빡할 때 커진다(사례: Harness-Bench v2의 Qwen3.8-27B 39.2점 대 나머지 5.0~9.5점, Same Model의 좁은 창 한정 효과, Tmax 저자가 Terminus-2를 작은 모델에 더 취약하다고 본 점, Neubig의 강한 모델 증언 — 4개). Qwen 32B는 프론티어보다 약하므로 구조에 투자할 값이 있다.

### 역할 분리와 오케스트레이션

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [Can Small Agents Collaborate…](https://arxiv.org/abs/2601.11327) | Qwen3-1.7B/8B/32B | 학습 없이 orchestrator 하나와 sub-agent 셋(웹 검색·코드 실행·파일 해석)으로 나누고, 공유 구조화 메모리는 orchestrator만 읽음 | orchestrator만 thinking일 때 8B 다중 에이전트 대 32B 단일: GAIA 23.0 대 23.0, AIME 55.0 대 45.0, GPQA 58.6 대 60.1. thinking 없으면 AIME 20.0 대 28.3. sub-agent를 1.7B/8B/32B로 바꿔도 GAIA 23.0/23.0/23.6 |
| 같은 논문 | Qwen3-8B | 구조화 메모리 제거 | AIME −18.3pp, GPQA −8.1pp |
| [α-UMi](https://arxiv.org/abs/2401.07324) | LLaMA-2-chat-7B/13B | planner·caller·summarizer로 나누고 2단계 미세조정(GLPFT) | 실시간 ToolBench pass rate가 ChatGPT보다 +6.1, ToolLLaMA보다 +10.2. 7B 구성이 13B 단일 모델을 대부분의 지표에서 넘음(Act. EM 58.94 대 59.67처럼 지는 지표도 있음) |
| [ToolOrchestra](https://arxiv.org/abs/2511.21689) | Qwen3-8B, Orchestrator-8B(RL) | 작은 모델이 큰 모델을 도구로 부름 | HLE(text-only)/FRAMES/τ²-Bench: Qwen3-8B 기본 도구 4.7/26.5/40.7, Qwen3-8B에 LLM 도구를 붙이면 30.6/68.9/72.3, Orchestrator-8B 37.1/76.3/80.2, GPT-5 기본 도구 35.1/74.0/77.7. 비용 9.2 대 30.2센트(HLE·FRAMES 평균) |
| [카카오 그래프 에이전트 발표](https://www.youtube.com/watch?v=XQo0DHuqgVM) | 모델 게이트웨이(Claude·GPT·Gemini를 비교), 쿼리 리라이트용으로 파인튜닝한 LLM | 툴이 많아지자 도메인별 에이전트로 쪼개고, 쿼리 리라이트 같은 일은 서브 LLM에 맡김 | 그래프 8개·릴리즈 73회 → 그래프 15개·릴리즈 383회. 다음 서비스 개발 시간 약 50% 단축(발표자 보고) |
| [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | — | 에이전트 질의 중 특화 SLM이 맡을 몫 추정 | MetaGPT 약 60%, Open Operator 약 40%, Cradle 약 70%(저자 추정, 측정값 아님) |

카카오 발표는 쪼갠 이유를 "하나의 LM에 너무 많은 툴이 주어지면 토큰을 불필요하게 소비하고 툴 선택의 정확도까지 떨어지는 문제가 있었습니다."라고 설명한다. 단서: 툴 선택 정확도가 얼마나 나아졌는지는 수치로 나오지 않는다.

Small Agents 논문은 "Overall system performance is driven primarily by orchestrator capacity rather than sub-agent capacity."라고 정리한다. 단서: ICLR 2026 워크숍 논문이고 Qwen3 한 계열만 실험했다. 43% 프롬프트 토큰 감소는 Direct+Think 대비 수치다.

[로컬 AI 패널](https://www.youtube.com/watch?v=KB41dTlX1Uc)에서도 같은 분업이 나온다. "local models are great at writing code, but maybe we offload the actual top-level planning to one of the frontier models, and you, you save a bunch, you control more of the workflow."

[Peter Belcak](https://www.youtube.com/watch?v=9xgRTznP21E)은 코드로 짠 에이전트의 개별 호출이 '자주(quite often)' 프롬프트가 고정되고 payload만 바뀌는 좁은 일이라, 여기에 범용 모델을 쓰는 건 '최선의 쓰임이 아닐 수 있다'고 말한다. 그는 "agentic systems are naturally heterogeneous."라고 보고, 에이전트가 여러 조각으로 이뤄져 있으니 조각마다 다른 모델을 쓸 수 있다고 본다.

[추정] 구조의 이득은 계획·조율 자리에 몰리고 실행 자리의 모델 크기는 덜 중요하다(사례: Small Agents의 sub-agent 크기 무관, ToolOrchestra의 8B orchestrator, 로컬 AI 패널의 계획-실행 분업, 카카오의 메인 LLM-서브 LLM 분리 — 4개).

단서: α-UMi의 역할 분리 이득은 미세조정을 전제로 하므로 학습 없는 하네스의 근거로 쓰면 안 된다. ToolOrchestra의 도구 목록에는 GPT-5 같은 상용 모델이 들어 있다. τ²-Bench의 GPT-5 77.7은 저자 재현치이고, 저자들은 GPT-5 보고치 84.2를 재현하지 못했다고 각주에 적었다. Orchestrator-8B의 80.2는 그 보고치보다 낮다.

### 고정 워크플로 대 자율 루프

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [Agentless](https://arxiv.org/abs/2407.01489) | GPT-4o | LLM이 다음 행동을 정하지 않는 고정 단계 파이프라인 | SWE-bench Lite 32.00%(96/300), 문제당 $0.70 |
| [Progressive Crystallization](https://arxiv.org/abs/2607.07052) | 미공개 | 자율 에이전트로 탐색한 경로를 hybrid로, 다시 결정 규칙으로 승격 | 8개월 동안 결정적 실행 0%→약 45%, 장애당 에이전트 비용 70% 넘게 감소(장애 건수는 대략 두 배). hybrid→결정적 승격 조건: 성공 50회 이상, LLM 분류 일관성 99% 이상 등 |
| [Behavioral Controllability](https://arxiv.org/abs/2607.15715) | openPangu-Embedded-7B(vLLM) | 고정 워크플로(S0), 규칙 반성 에이전트(S1a), LLM 반성 에이전트(S1b) | 레코드/논문(링크율): S0 158/42(0.190), S1a 165/43(0.164), S1b 168/43(0.185). 조건마다 1회 실행 |
| [Dissecting Agentic RAG](https://arxiv.org/abs/2606.21553) | Qwen2.5-7B-Instruct(Ollama) | agentic RAG 부품 하나씩 끄기 | HotpotQA 5,000문항: baseline EM 43.1 → full 53.2. 검색 1회로 줄이면 −7.1, 2회면 −0.3, 고정 하이브리드 검색만 쓰면 EM 55.0 |
| [AgentFloor](https://arxiv.org/abs/2605.00334) | 오픈 모델 16개(0.27B~32B, Ollama), GPT-5 | plan/execute/submit 단계를 프롬프트에 적음 | gemma4:26b −5pp, qwen3:32b-nothink −6pp, nemotron-3-nano:4b −14pp, ministral-3:8b −33pp |
| [OAgents](https://arxiv.org/abs/2506.15741) | GPT-4.1 | 계획 구성 비교 | GAIA 평균: 기준 51.52, 정적 workflow 47.88, +subtask 53.94, +plan tips 66.06 |

Progressive Crystallization의 원칙은 "every action is typed and schema-validated, so the LLM decides understanding, not what to do."다. 이 논문은 Microsoft Azure Networking의 장애 처리 사례(월 수만 건)라 사용자 도메인(네트워크 검증)과 가깝다. 단서: 단독 저자가 자기 시스템을 보고했고, 통제 비교군이 없으며, 쓴 LLM을 밝히지 않았다.

AgentFloor는 소제목에서 "Structured prompts hurt every model tested."라고 못박는다. 단서: plan/execute/submit 결론은 네 모델에서 나왔고 temperature 0·Ollama 조건이다. 단계를 프롬프트가 아니라 코드로 나눈 하네스에도 같은 결과가 나오는지는 확인한 출처에 없다.

Behavioral Controllability의 저자들은 "LLM reflection changes process signals substantially while producing only modest output gains under a fixed retry budget."이라고 적는다. 단서: 정답셋이 없어 정밀도·재현율이 없고, 7B 모델 하나를 한 번씩만 돌렸다.

[추정] 작은 로컬 모델에서는 단계를 프롬프트로 지시하기보다 코드로 고정하고, LLM에게는 '이해·분류'만 맡기는 쪽이 안정적이다(사례: Agentless, Progressive Crystallization, AgentFloor의 프롬프트 단계 분해 하락, Dissecting Agentic RAG의 짧은 고정 루프 — 4개). 단서: OAgents에서는 정적 workflow가 기준보다 낮았으므로, 고정한 단계가 과제에 맞아야 한다.

### 도구 수 줄이기·도구 검색

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [Less is More](https://arxiv.org/abs/2411.15399) | Llama3.1-8b, Qwen2-7b 등(Ollama 양자화, Jetson AGX Orin) | 질의마다 도구를 골라서 줄임 | Llama3.1-8b-q4_K_M, 16K 컨텍스트, 질의 하나: 도구 46개면 실패, 19개면 성공. BFCL에서 Llama3.1-8b 실행 시간 −72%. 초록 기준 실행 시간 최대 70%, 전력 최대 40% 감소 |
| [RAG-MCP](https://arxiv.org/abs/2505.03275) | qwen-max-0125(상용) | MCP 설명을 검색해 관련 도구만 넣음 | 도구 선택 정확도 43.13%(전부 넣기 13.62%, 키워드 거르기 18.20%). 프롬프트 토큰 2133.84→1084 |
| [TinyAgent](https://arxiv.org/abs/2409.00608) | 1.1B, 7B(LoRA) | DeBERTa Tool RAG로 도구 선별 | 평균 3.97개 도구로 recall 0.998. Tool RAG를 붙이면 1.1B 80.06%, 7B 84.95%(GPT-4-Turbo 79.08%) |
| [Cormac Brick 강연](https://www.youtube.com/watch?v=-TiET_K-E_g) | Gemma 4 4B | 스킬 목록만 먼저 주고 세부는 필요할 때 불러옴 | 4B는 기본 스킬 약 8개에서 잘 고름. 턴마다 하나씩은 안정적이고 한 답에서 여러 스킬을 엮는 건 가끔만 됨 |
| [IFFC](https://arxiv.org/abs/2608.22472) | Qwen-3 4B Think, Phi-4 Mini 등 | 도구 호출을 도구 문맥 대신 지시 문맥으로 물음 | BFCL V3 Live: Qwen-3 4B Think IFFC 86.7 대 PFC 82.8 대 NFC 81.5. Phi-4 Mini는 IFFC 44.3 대 PFC 62.5 |
| [smolagents](https://github.com/huggingface/smolagents) · CodeAct | LLM 17종 | 도구 호출을 JSON 대신 코드로 씀 | README: 단계 30% 감소(CodeAct 인용). CodeAct: 성공률 최대 20% 향상 |

Less is More 초록은 "selectively reducing the number of tools available to LLMs significantly improves their function-calling performance, execution time, and power efficiency on edge devices."라고 적는다.

단서: 46개 대 19개는 질의 하나의 예시이고, 2024년 Ollama 양자화 모델 실험이다. RAG-MCP는 로컬 오픈 모델 결과가 아니고, 저자도 MCP가 수천 개로 늘면 검색 정밀도가 떨어진다고 밝혔다.

IFFC는 표마다 결과가 섞여서 저자 초록의 'consistently outperforms'를 그대로 옮기면 안 된다. 표 수치로만 인용한다.

[추정] 한 호출에 보이는 도구를 줄이고 필요한 것만 검색해 넣는 구조가 작은 모델의 도구 선택을 가장 직접 올린다(사례: Less is More, RAG-MCP, TinyAgent Tool RAG, Gemma 4 스킬 지연 로딩, 카카오 도메인 분리 — 5개). Qwen 32B급이 한 노드에서 안정적으로 고르는 도구 수의 실측은 찾지 못했다. 4B·약 8개가 유일한 수치다.

### 컨텍스트 관리

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [Context Rot](https://research.trychroma.com/context-rot) | LLM 18개 | 같은 질문을 관련 조각만(focused)과 전체(full)로 줌 | LongMemEval 306개: focused 약 300토큰, full 평균 약 113k토큰. distractor는 하나만 있어도 성능을 떨어뜨렸고 넷이면 더 떨어졌다 |
| [Qwen3.5-27B 카드](https://huggingface.co/Qwen/Qwen3.5-27B) | Qwen3.5-27B | 검색 에이전트의 context-folding | 누적 tool response가 임계에 닿으면 앞의 응답을 잘라냄(아래 인용) |
| [OAgents](https://arxiv.org/abs/2506.15741) | GPT-4.1 | 메모리 방식 비교 | GAIA: 요약 52.12, 검색 53.33, 장기 기억 55.76 |
| [Manus 글](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) | Claude Sonnet | KV-cache 적중을 위한 고정 prefix, 도구는 지우지 않고 logit masking | 입력:출력 토큰 약 100:1. 캐시 입력 0.30 USD/MTok 대 비캐시 3 USD/MTok |
| [Obsidian 지식그래프 워크숍](https://www.youtube.com/watch?v=Ndp5VaqFrl0) | GLiNER, Qwen3 | 파싱·추출을 자체 클러스터의 오픈 모델에 맡기고 에이전트에는 작은 markdown만 돌려줌 | 40쪽 PDF를 닫힌 모델 API에 올리면 턴마다 약 80k 토큰을 다시 과금한다는 슬라이드 어림값 |

Context Rot 저자들은 "We verify that the models are highly capable of succeeding on the focused inputs, then observe consistent performance degradation with the full inputs."라고 적는다. 단서: 벡터 DB 회사의 보고서로 동료 심사를 거치지 않았다. distractor는 저자가 직접 쓴 오답 문장 4개다.

Qwen3.5-27B 카드의 각주는 "once the cumulative Tool Response length reaches a preset threshold, earlier Tool Responses are pruned from the history to keep the context within limits."라고 적는다.

Manus 저자는 "If I had to choose just one metric, I'd argue that the KV-cache hit rate is the single most important metric for a production-stage AI agent."라고 본다.

[추정] 작성자마다 같은 대상을 비슷한 말로 쓰는 사내 보고서는 Context Rot의 distractor 상황과 모양이 같아서, 관련 조각만 골라 주는 쪽이 32B에도 이득일 것이다(사례: Context Rot focused 대 full, Same Model의 tool result 축약, Small Agents의 구조화 메모리 제거 하락 — 3개). 한국어에서 같은 효과가 나는지는 확인한 출처에 없다.

## 가중치를 건드리지 않는 최적화

프롬프트를 진화시키거나, 실행에서 뽑은 경험 규칙·playbook을 컨텍스트에 쌓는 방법이다. 결과는 피드백 신호의 질에 따라 갈렸다.

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [GEPA 논문](https://arxiv.org/abs/2507.19457) | Qwen3 8B | 궤적을 읽고 프롬프트를 반성적으로 고침, GRPO(LoRA)와 비교 | 6개 과제 종합: Baseline 45.23, GRPO 48.91, MIPROv2 47.84, GEPA 54.85. IFBench: GEPA 678 rollouts에서 38.61%, GRPO 24,000 rollouts에서 35.88%. AIME-2025는 GRPO 38.00 대 GEPA 32.00. Qwen3-8B로 최적화한 프롬프트를 GPT-4.1-Mini에 옮기면 종합 +9.00% |
| [GEPA 강연](https://www.youtube.com/watch?v=OA-Mc60Rboo) | Qwen3 8B 외 | 외부 교사 없이 자기 최적화 | 반성 1회(데이터 3개)로 GRPO 25,000 롤아웃 향상폭의 2배(발표자 도메인 과제, 비공개) |
| [Training-Free GRPO](https://arxiv.org/abs/2510.08191) | Qwen3-32B, DeepSeek-V3.1-Terminus | 그룹 rollout 비교로 뽑은 경험을 프롬프트에 넣음 | Qwen3-32B non-thinking, 코드 인터프리터: AIME24 29.1→33.5, AIME25 19.5→25.4, 학습비 약 $4. 같은 표의 RL 학습 32B: ReTool 67.0/49.3, AFM 66.7/59.8(약 $10,000) |
| 같은 논문 | QwQ-32B | WebWalkerQA 부분집합 ablation | pass@1 25.5로 자체 ReAct 27.5보다 낮음(pass@3는 43.1→45.1) |
| [ACE](https://arxiv.org/abs/2510.04618) | DeepSeek-V3.1(671B) | 증분 갱신하는 playbook 컨텍스트 | agent 벤치 +10.6%, 금융 +8.6%. 라벨 없이 실행 피드백만으로 AppWorld 최대 +17.1% |
| [Lease End 강연](https://www.youtube.com/watch?v=4loPnxvWWhg) | 프론티어 모델(재구축 후) | 미세조정 모델을 버리고 컨텍스트로 행동 바꾸기 | 문제 발견→수정 배포 1시간 미만(재구축 전 재학습 주기 약 1주). 정확도 향상은 수치 없음 |

GEPA 논문 초록은 "Across six tasks, GEPA outperforms GRPO by 6% on average and by up to 20%, while using up to 35x fewer rollouts."라고 적는다. 단서: 전체 미세조정 GRPO와는 과제 하나(2-hop HoVer)에서만 비교했다. GEPA의 실제 총 rollout은 과제별 1,839~7,051개이고, 678은 IFBench에서 최적 프롬프트에 닿은 시점이다.

Training-Free GRPO 저자들은 "This may suggest that the effectiveness of our method is dependent on the underlying model’s reasoning and tool-use capabilities in complex tool use scenarios, indicating that model capability is a prerequisite for effective experience-based optimization."라고 적는다.

단서: 32B급에서는 학습비만 크게 낮고 성능은 RL로 학습한 32B보다 30점 이상 뒤진다. 수학과 웹 탐색 QA에서만 검증했다.

ACE 저자들은 정답 라벨이나 실행 결과 같은 믿을 만한 피드백이 없으면 ACE도 성능이 떨어질 수 있다고 적었다. Lease End 강연의 슬라이드는 "The AHA moment: change behavior through context, without fine-tuning or retraining."이라고 적는다. 단서: Lease End가 재구축 뒤 쓴 모델은 프론티어 API 모델이고, $12M 매출·50배 ROI는 회계 근거가 공개되지 않았다.

### 반대 증언

[Kyle Corbitt(OpenPipe)](https://www.youtube.com/watch?v=yYZBd25rl4Q)는 자기 과제에서 GEPA가 소폭에 그쳤다고 말한다. "our naive prompt with our model gets maybe like 50% on this benchmark, and like Jeppa got to 56, and we do RL and we get to like 96."(자막 철자 'Jeppa'는 GEPA).

단서: 즉흥적 어림값이고 과제·모델이 공개되지 않았으며, 본인도 'maybe we were holding it wrong'이라고 단서를 단다.

[추정] 경험·playbook 누적은 사내 용어집 갱신과 같은 축이지만, 정답 없는 과제에서는 갱신 신호가 약해 오히려 성능을 깎을 위험이 크다(사례: ACE 저자 경고, Training-Free GRPO의 QwQ-32B 하락, OpenPipe 50→56, 진보 신기루 연구([When Do Agent Loops Mistake Stagnation for Progress?](https://arxiv.org/abs/2607.25152), #자기 판정 편향)에서 자기 판정 게이트가 18 cycle을 모두 받아들인 결과 — 4개). 그래서 용어집 갱신을 이 방법으로 돌리려면 #평가를 먼저 세우는 법의 판정자 검증이 먼저다.

## 출력 형식과 구조화 생성

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [Let Me Speak Freely?](https://arxiv.org/abs/2408.02442) | LLaMA-3-8B, GPT-3.5 Turbo, Claude 3 Haiku | 형식 제약 유무 비교 | LLaMA-3-8B Last Letter: JSON 파싱 오류율 0.148%인데 성능 차이 38.15%. GPT-3.5 Turbo JSON-mode는 Last Letter에서 100% 'answer' 키를 'reason' 키보다 먼저 둠. JSON-mode는 분류 과제 정확도를 올림 |
| [Say What You Mean(.txt 반론)](https://blog.dottxt.ai/say-what-you-mean.html) | Llama-3-8B-Instruct | 같은 프롬프트로 다시 잼 | 비구조화 대 구조화: GSM8K 0.77 대 0.78, Last Letter 0.73 대 0.77, Shuffle Object 0.41 대 0.44 |
| [CRANE](https://arxiv.org/abs/2502.09061) | Qwen2.5-1.5B/Math-7B, Llama-3.1-8B 등 | 추론 구간은 풀고 답만 문법으로 묶음 | GSM-Symbolic: Qwen2.5-Math-7B CRANE 38% 대 제약 29% 대 비제약 CoT 29%. Qwen2.5-1.5B 31% 대 22% 대 26% |
| [JSONSchemaBench](https://arxiv.org/abs/2501.10868) | Llama-3.1-8B-Instruct | 제약 엔진 비교 | Last Letters/Shuffle Objects/GSM8K: LM only 50.7/52.6/80.1%, Guidance 54.0/55.9/83.8%, XGrammar 51.2/52.7/83.7% |
| [BFCL V4 원자료](https://gorilla.cs.berkeley.edu/leaderboard.html) | Qwen3-32B 등 | 네이티브 FC 대 프롬프트 방식 | Overall FC/Prompt: Qwen3-32B 48.71/46.78(multi-turn 47.87/43.25), Qwen3-235B-A22B-Instruct-2507 47.99/52.15 |
| [BFCL 형식 민감도 글](https://gorilla.cs.berkeley.edu/blogs/17_bfcl_v4_prompt_variation.html) | 여러 모델 | 프롬프트 형식 변형 26가지 | Prompt 모드 max delta: Gemma-3-27b-it 34.0, Qwen3-32B 15.5(원자료 CSV) |

.txt 글은 "The prompts used for unstructured (NL) generation are markedly different than the ones used for structured generation, so the comparisons are not apples-to-apples to begin with."라고 반박한다. 단서: 구조화 생성 라이브러리(Outlines)를 만드는 회사의 글이고 모델 하나·과제 셋으로 재현했다.

CRANE은 "strict enforcement of formal constraints often diminishes the reasoning capabilities of LLMs"라는 관찰에서 출발한다. 단서: 출력이 형식 문법을 갖는 과제의 결과다. 문법 오류 0%(Parse 100)는 Qwen2.5-1.5B 한 모델의 수치이고, 다른 모델에서 CRANE의 Parse 비율은 92~95%였다. 비교 대상인 '제약' 조건은 CoT 없이 최종 답만 문법으로 묶은 것이다.

엔진과 프레임워크 문서도 같은 쪽을 가리킨다.

| 출처 | 내용 |
|---|---|
| [vLLM Tool Calling](https://docs.vllm.ai/en/latest/features/tool_calling.html) | named 호출에 대해 "You are guaranteed a validly-parsable function call - not a high-quality one." 스키마를 프롬프트에도 적으라고 권한다 |
| [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html) | 커스텀 텍스트 문법이 경계 토큰을 일반 토큰으로 내면 "A tool invocation can then remain in `reasoning` without producing `tool_calls`." |
| [PydanticAI Output](https://ai.pydantic.dev/output/) | 프롬프트로만 형식을 정하는 방식은 "This is usable with all models, but is often the least reliable approach as the model is not forced to match the schema." |
| [DSPy TwoStepAdapter](https://github.com/stanfordnlp/dspy/blob/main/dspy/adapters/two_step_adapter.py) | "Uses a smaller LM with chat adapter to extract structured data from the response of main LM" — 판단과 형식화를 다른 모델로 나눈다 |
| [Gemma 4 함수 호출 문서](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4) | 자동 스키마 변환이 커스텀 객체를 generic 'object'로 뭉갤 수 있어 수동 JSON 스키마를 권한다 |
| [goose toolshim](https://goose-docs.ai/blog/2025/04/11/finetuning-toolshim) | 판단은 주 모델이, 도구 호출 해석은 mistral-nemo shim이 맡자 phi4(14b)·gemma3(27b)가 llama3.3(70b)에 가까웠다(수치 없음) |

[추정] 구조화 출력의 손해는 제약 자체보다 추론 자리를 없앤 스키마와 어긋난 프롬프트에서 나오므로, 근거·이유 필드를 답 필드보다 앞에 두고 답(용어 ID·관계 유형)만 제약하는 것이 기본값이다(사례: Let Me Speak Freely의 키 순서, .txt 재현, CRANE, JSONSchemaBench, DSPy TwoStep — 5개). 한국어 enum 값이나 한국어 용어집 ID를 문법으로 묶을 때의 품질은 찾은 출처 어디에도 없다.

## 검증·test-time compute·cascade

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [SLM은 강한 verifier가 필요하다](https://arxiv.org/abs/2404.17140) | Gemma-7B-it, LLaMA-2-13B | 자기교정 refiner(LoRA)에 verifier를 바꿔 붙임 | Gemma CSQA: 초기 67.2, self-verifier 67.5, GPT-4 verifier 75.0, oracle 85.4. LLaMA-2-13B: 69.7, 69.7, 72.4, 86.2 |
| [1B가 405B를 넘나](https://arxiv.org/abs/2502.06703) | Llama-3.2-3B, Qwen2.5-0.5B 등 | PRM을 쓰는 compute-optimal TTS | MATH-500/AIME24: Llama-3.2-3B(TTS) 75.6/30.0 대 Llama-3.1-405B(CoT) 71.4/23.3. 7B 미만은 어려운 문제에 beam search, 7B~32B는 쉬움·중간에 DVTS, 72B는 모든 난이도에 BoN |
| [Step-level cascade](https://arxiv.org/abs/2604.27151) | EvoCUA-8B, Qwen3-VL-8B 등 + Claude Sonnet 4.5 | 막힘·체크포인트를 감시하는 ModernBERT monitor로 step마다 큰 모델 승격 | OSWorld: Sonnet 4.5 단독 58.1%·과제당 $0.881, cascade 55.4%·$0.224. 비용 최대 74.6%, 지연 최대 45.8% 감소. 실패 궤적은 성공보다 EvoCUA-8B 2.8배, Qwen3-VL-8B 2.5배 길다 |
| [Semantic Agreement Cascades](https://arxiv.org/abs/2509.21837) | 500M~70B, target Llama3.1-70B | 작은 모델 앙상블의 의미 합의로 넘길지 결정 | target FLOPs 40% 예산에서 SQuAD 84.3% 대 82.7%. 품질 98% 도달 지연 SQuAD 60%, CNN/DM 39% 감소 |
| [SWE-Gym](https://arxiv.org/abs/2412.21139) | Qwen2.5-Coder-32B | 학습한 verifier로 후보 중 고르기 | Verified: 20.6@1 → 29.8@8 → 32.0@16 |
| [R2E-Gym](https://arxiv.org/abs/2504.07164) | Qwen-2.5-Coder 32B | 실행·비실행 hybrid verifier | pass@1 34.4%, 검증기 각각 약 42~43%에서 포화, hybrid 51% |
| [DeepSWE 카드](https://huggingface.co/agentica-org/DeepSWE-Preview) | Qwen3-32B(RL) | 다회 샘플 + 검증기 | Pass@1 42.2%, Hybrid Best@16 59% |
| [Verifying Tool-Using Agent Interventions](https://neurips.cc/virtual/2026/173060) | Qwen2.5-1.5B | 학습 없는 하네스 대 SFT | BFCL 100개 exact match: 하네스 없음 18.0%, 전체 하네스 36.0%, 검증된 데모 SFT 74.7 ± 0.6% |
| [Flat Score, Amplified Failures](https://arxiv.org/abs/2607.27275) | Gemma-4·Qwen-3.6·Qwen-3.5 | 양자화 실패에 검증-재시도(repair) 루프 | 실패량 최대 2.5배(과제당 +17.6 points)가 repair 루프로 피해가 있던 곳에서 사라짐(재시도 최대 3회). 단서: repair는 telecom 도메인 다섯 모델에서만 돌림 |
| [Kimchi 소개문](https://ai.engineer/worldsfair/2026/sessions.json) | 오픈 가중치 + 프론티어 | 단계마다 평가해 다시 하거나 상위 모델로 올림 | 상용 모델만 쓸 때보다 약 2.5배 낮은 비용(소개문 주장, 조건 미공개) |

SLM verifier 논문은 "The upper bound performance suggested by an oracle verifier demonstrate great potential for self-correction, yet a weak self-verifier can only bring minor improvements, if not misguiding the refiner."라고 정리한다.

단서: 큰 향상은 모두 외부 GPT-4 verifier나 oracle 조건에서 나왔다.

Verifying Tool-Using Agent Interventions는 "On a held-out 100 example BFCL subset, the unadapted model reaches 18.0% exact match on its own and 36.0% with our full harness."라고 적는다. 단서: NeurIPS 2026 본 트랙이 아니라 워크숍 포스터이고, 본문을 열지 못해 하네스 구성은 확인하지 못했다. 모델은 1.5B 하나다.

Kimchi 소개문은 "Kimchi evaluates every step, automatically reworking or escalating tasks when needed to maintain quality while minimizing the use of expensive frontier models."라고 적는다. 단서: 스폰서가 쓴 소개문이고 발표 영상은 찾지 못했다. 원문은 'Powered by Ferment, Kimchi evaluates every step, ...'으로 시작하고 인용은 그 일부다. 라우팅 방식과 2.5배의 측정 조건은 공개되지 않았다.

[추정] 작은 모델의 자기 검증은 약하므로 검증 신호는 transcript 밖(외부 verifier, 실행 결과, 결정 규칙, 정답 참조)에서 가져와야 한다(사례: SLM verifier, Behavioral Controllability의 LLM 반성, Training-Free GRPO의 QwQ-32B, 진보 신기루 연구 — 4개).

[추정] 승격은 질의 단위보다 step 단위로 막힘·체크포인트를 볼 때 비용이 덜 든다(사례: Step-level cascade, Kimchi, 로컬 AI 패널의 계획 위임 — 3개).

## 서빙 설정의 함정

로컬 운영에서는 모델보다 서빙 층에서 에러 없이 성능이 깎이는 일이 잦다.

### 모델 카드 권장값

| 모델 | 모드 | 권장 샘플링 | 출처 |
|---|---|---|---|
| Qwen3-32B | thinking | Temperature=0.6, TopP=0.95, TopK=20, MinP=0 | [카드](https://huggingface.co/Qwen/Qwen3-32B) |
| Qwen3-32B | non-thinking | Temperature=0.7, TopP=0.8, TopK=20, MinP=0 | 같은 카드 |
| Qwen3.8-27B | thinking | temperature=1.0, top_p=0.95, top_k=20, presence_penalty=0.0 | [카드](https://huggingface.co/Qwen/Qwen3.8-27B) |
| Qwen3.8-27B | non-thinking | temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5 | 같은 카드 |
| Gemma 4 | — | temperature=1.0, top_p=0.95, top_k=64 | [카드](https://ai.google.dev/gemma/docs/core/model_card_4) |

Qwen3-32B 카드는 "**DO NOT use greedy decoding**, as it can lead to performance degradation and endless repetitions."라고 적는다. 반면 Ollama 구조화 출력 팁은 temperature 0을 권하고, AgentFloor와 Flat Score는 temperature 0·greedy로 쟀다. 실험 조건이 운영 권장과 다르면 결론이 그대로 옮겨지지 않는다.

[Rating Roulette](https://arxiv.org/abs/2510.27106)에서는 sampling을 끈 Qwen 3 판정이 단일 실행 79.4±0.32에서 79.2로 조금 낮았다. 단서: 그 차이는 작아서 방향만 맞다.

### 템플릿·파서·thinking 이력

| 대상 | 규칙 | 출처 |
|---|---|---|
| Qwen3 | Hermes 형식 권장. vLLM은 `--tool-call-parser hermes --reasoning-parser deepseek_r1`(vllm >= v0.8.5) | [Qwen Function Calling](https://qwen.readthedocs.io/en/latest/framework/function_call.html) |
| Qwen3·QwQ + Qwen-Agent | 서버 쪽 `--enable-auto-tool-choice --tool-call-parser hermes`를 켜지 말 것(Qwen-Agent가 직접 파싱) | [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) |
| Qwen3.6-27B | vLLM·SGLang 모두 `--reasoning-parser qwen3 --tool-call-parser qwen3_coder`. preserve_thinking 선택 가능 | [카드](https://huggingface.co/Qwen/Qwen3.6-27B) |
| Qwen3.8-27B | thinking·preserve_thinking 기본 켬. 기본 도구 파서 qwen3_coder. reasoning_effort 기본 xhigh | [카드](https://huggingface.co/Qwen/Qwen3.8-27B) |
| Gemma 4 | 도구용 특수 토큰 6개. 이전 턴 thought는 지우되 도구 호출 턴 안에서는 남김 | [카드](https://ai.google.dev/gemma/docs/core/model_card_4) · [형식 문서](https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4) |
| vLLM Qwen3 스트리밍 | `<think>`, `</think>`, `<tool_call>`, `</tool_call>`을 전용 토큰 ID로 알아봄 | [vLLM Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html) |

Qwen 함수 호출 가이드는 "We recommend using Hermes-style tool use for Qwen3 to maximize function calling performance."라고 하면서도, 운영 코드에서는 형식이 깨질 때의 대응책을 마련해 두라고 적는다.

Gemma 4 형식 문서는 "If a single model turn involves function or tool calls, thoughts must NOT be removed between the function calls."라고 적는다.

Qwen3.8 카드의 Ascend 절은 `--reasoning-parser qwen3`를 빼면 추론 블록이 message.content로 새고, 2048토큰 예산이 답 전에 바닥날 수 있다고 적는다. 단서: Huawei Ascend 950PR·W8A8 체크포인트 절의 문장이다.

[Gemma 4 SWE-bench 사례](https://ai-muninn.com/en/blog/dgx-spark-gemma4-swe-bench-scaffold-engineering)에서는 vLLM 공식 권장 플래그(`--reasoning-parser`, `--chat-template`)를 켜자 패치가 나빠졌고, `--tool-call-parser`만 쓴 쪽이 안정적이었다. 저자는 "small models aren't bad at editing — the tool-calling protocol is too brittle for them."이라고 본다.

단서: 한 인스턴스를 28번 고친 일화다.

[vLLM 강연(Michael Goin)](https://www.youtube.com/watch?v=AZcJJbBBgLc)은 "there still isn't exactly an open source standard for tool calling"이라고 말한다.

[llama.cpp 문서](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md)의 네이티브 형식 목록에는 Qwen3·Gemma 4가 없다.

단서: 문서 기준이며 코드 지원은 따로 봐야 한다.

### thinking 모드

| 출처 | 모델 | 수치(조건) |
|---|---|---|
| [AgentFloor](https://arxiv.org/abs/2605.00334) | Qwen3 | thinking을 끄면 tier B(순차 2-도구 연결)에서 32B +12pp [+6,+18], 8B −9pp [−16,−2], 14B −12pp [−18,−6] |
| [Qwen3 기술보고서](https://arxiv.org/abs/2505.09388) | Qwen3-32B | BFCL v3 thinking 70.3, non-thinking 63.0. 사내 ToolUse는 non-thinking 86.5 대 thinking 85.5 |
| [LightRAG PR #3599](https://github.com/HKUDS/LightRAG/pull/3599) | gemma4:12b(Ollama) | thinking이 출력 예산을 먹어 5/5 chunk에서 엔티티 0개(적재 2회). 같은 프롬프트에 think=False면 3/3 정상 |
| [Small Agents](https://arxiv.org/abs/2601.11327) | Qwen3-8B 다중 에이전트 | 지연: sub-agent thinking +77%, orchestrator thinking +8% |

Qwen3.8 카드는 "In multi-turn agentic tasks, lower reasoning effort does not always reduce overall task completion time. Although it may produce faster per-turn responses, it can also lead to insufficient analysis, more failures, and repeated retries, which may increase total latency and token consumption."라고 경고한다.

LightRAG PR의 메인테이너는 qwen3 4B/8B에서 thinking을 끄면 추출 품질이 떨어진다며 기본값 변경을 거절했다. 병합된 PR은 기본값을 바꾸지 않고 역할별 설정(EXTRACT_OLLAMA_LLM_THINK 등)만 노출한다. 단서: 메인테이너 주장에는 수치가 없고, 병합 직전 재시험(Ollama v0.32.6)에서는 원래 실패가 재현되지 않았다.

[추정] thinking은 모델·크기·역할마다 효과의 부호가 바뀌므로, 계획 자리와 추출 자리에서 따로 켜고 끄며 재야 한다(사례: AgentFloor의 32B 대 8B·14B 부호 반전, Qwen3 BFCL 대 사내 ToolUse, LightRAG PR의 gemma4 대 qwen3, Small Agents의 orchestrator 한정 thinking — 4개).

### 컨텍스트 길이

| 출처 | 내용(조건) |
|---|---|
| [Ollama 문서](https://docs.ollama.com/context-length) | 기본 컨텍스트: VRAM 24GiB 미만 4k, 24~48GiB 32k, 48GiB 이상 256k. 에이전트는 64000 이상 권장. FAQ는 아직 4096이라고 적어 문서끼리 어긋남 |
| [aider 양자화 글](https://aider.chat/2024/11/21/quantization.html) | Qwen2.5-Coder-32B, Ollama fp16: 최소 8k 창 71.4 대 2k 창 51.9(올바른 편집 형식 46.2%) |
| [nano-graphrag FAQ](https://github.com/gusye1234/nano-graphrag/blob/main/docs/FAQ.md) | Ollama 기본 num_ctx 2048이면 추출 프롬프트가 잘려 그래프가 빌 수 있음. 예시 해결은 num_ctx 32000 |
| [Qwen3.6-27B 카드](https://huggingface.co/Qwen/Qwen3.6-27B) | 기본 262,144. OOM이 나면 줄이되 thinking을 지키려면 128K 이상 유지 권고 |
| [Qwen3-32B 카드](https://huggingface.co/Qwen/Qwen3-32B) | 네이티브 32,768, YaRN으로 131,072까지 검증 |

aider 글은 2k 창을 두고 "Such a small window has catastrophic effects on performance, without throwing obvious hard errors."라고 적는다.

Ollama 문서는 "Tasks which require large context like web search, agents, and coding tools should be set to at least 64000 tokens."라고 권한다.

### 양자화

| 출처 | 모델 | 수치(조건) |
|---|---|---|
| [aider](https://aider.chat/2024/11/21/quantization.html) | Qwen2.5-Coder-32B | 코드 편집 벤치마크: BF16 72.2, mlx 4bit 72.2, Ollama fp16 71.4, q4_K_M 66.9, q2_K 61.7(단일 실행, ±1~2%) |
| [Docker 도구 호출 평가](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/) | Qwen3, Llama3.1 | 도구 선택 F1: qwen3:14B-Q4_K_M 0.971, Q6_K 0.943, llama3.1:8B F16 0.835, Q4_K_M 0.793 |
| [Flat Score, Amplified Failures](https://arxiv.org/abs/2607.27275) | Gemma-4, Qwen-3.6(INT4 AWQ, vLLM) | τ²-bench 점수는 그대로인데 실패량 최대 2.5배. Gemma-4 dense telecom 도구 이름 환각 19.5%→38.3% |
| [IFFC](https://arxiv.org/abs/2608.22472) | Qwen-3, Gemma-3, Phi-4 Mini | Q4KM 손실이 Qwen-3 계열은 작고 Gemma-3·Phi-4 Mini는 큼 |

Flat Score 논문은 "The score stays flat because the benchmark's ten-error budget absorbs the extra failures."라고 원인을 짚는다. 오류 예산을 10에서 2로 줄이면 17점 차가 드러났다. 단서: 점수 손해가 드러난 곳은 한 셀(Gemma-4 dense telecom)이고, Qwen-3.6은 BF16에서 도구 환각이 거의 없어 양자화 영향이 평평했다.

KV 캐시 양자화는 따로 본다. llama.cpp 문서는 "Beware of extreme KV quantizations (e.g. `-ctk q4_0`), they can substantially degrade the model's tool calling performance."라고 경고한다. Ollama FAQ는 KV q8_0이 f16의 약 1/2, q4_0이 약 1/4 메모리라고 적는다.

[추정] 집계 점수만 보면 4비트 손실이 작아 보이므로, 사내 평가에서는 호출 단위 실패(도구 이름 환각, 형식 오류)를 따로 세야 한다(사례: Flat Score, aider q4_K_M 대 mlx 4bit, Docker Q4 대 Q6 역전, IFFC 계열별 차이 — 4개).

### 처리량

| 출처 | 내용(조건) |
|---|---|
| [vLLM prefix caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html) | enable_prefix_caching 기본 True. "APC only reduces the time of processing the queries (the prefilling phase) and does not reduce the time of generating new tokens (the decoding phase)." |
| [SGLang RadixAttention](https://arxiv.org/abs/2312.07104) | 처리량 최대 6.4배, 캐시 적중률 50~99%. 멀티턴 짧은 출력(4~8토큰)에서 이득 |
| [CacheScout](https://arxiv.org/abs/2608.14624) | 에이전트가 시스템 프롬프트·도구 정의·few-shot을 되풀이해 실행함. 적중률 10~18%p 향상(초록) |
| [Continuum](https://arxiv.org/abs/2511.02230) | 도구 대기 사이의 KV를 TTL로 붙잡아 평균 작업 완료 시간 8배 이상 개선(초록) |
| [Qwen3-32B EAGLE-3 recipe](https://github.com/vllm-project/recipes/blob/main/models/Qwen/Qwen3-32B.yaml) | Red Hat EAGLE-3 draft, 3토큰 투기. 수용 길이 k=3: 코딩 2.29, 수학 2.49, 요약 2.15(요약이 가장 낮음). EAGLE-3 논문: SGLang batch 64에서 처리량 1.38배 |
| [vllm run-batch](https://github.com/vllm-project/vllm/blob/main/examples/features/openai_batch/README.md) | OpenAI Batch 파일 형식으로 오프라인 일괄 처리. "Responses are written in input order as the batch runs." |
| [Qwen3 속도 벤치](https://qwen.readthedocs.io/en/latest/getting_started/speed_benchmark.html) | H20 1장, SGLang, batch 1, 입력 1토큰: Qwen3-32B BF16 20.72, FP8 46.17, AWQ-INT4 47.67 tokens/s |

단서: Continuum과 CacheScout은 초록만 확인했다. Qwen3 속도 벤치의 속도에는 입력 토큰이 포함되고, 동시성별 처리량은 없다. run-batch는 출력 파일을 실행 시작 때 비우므로 재개할 때 출력 경로를 따로 둬야 한다.

[추정] 대화형 질의와 대량 적재를 같은 서버 설정으로 돌리면 둘 다 손해를 본다. 고정 prefix(시스템 프롬프트·도구 정의·용어집)를 앞에 두고, 대량 적재는 일괄 처리로 떼는 편이 낫다(사례: Manus의 100:1과 고정 prefix, prefix caching이 prefill만 줄인다는 문서, EAGLE-3의 낮은 동시성 이득, run-batch — 4개).

## 학습이 값을 하는 때

| 출처 | 모델 | 무엇을 했나 | 수치(조건) |
|---|---|---|---|
| [AgentFlow](https://arxiv.org/abs/2510.05592) | Qwen2.5-7B-Instruct planner | 4모듈 하네스 고정, planner만 교체·SFT·RL | 6개 벤치 평균: frozen 38.5, GPT-4o planner 44.3, GPT-4o 궤적 SFT 19.5, Flow-GRPO 55.7 |
| [DeepSWE](https://www.together.ai/blog/deepswe) | Qwen3-32B | RL만 | SWE-bench Verified Pass@1 23→42.2%. 데이터 4.5K 문제, 64×H100 6일 |
| [SWE-smith](https://arxiv.org/abs/2504.21798) | Qwen2.5-Coder-32B | Claude 3.7 Sonnet 궤적 5,016개 전체 미세조정 | SWE-agent-LM-32B Pass@1 40.2%. 32B 궤적의 25% 넘게 길이 10 이상 반복(Claude 3.7 Sonnet은 4% 미만) |
| [SWE-Gym](https://arxiv.org/abs/2412.21139) | Qwen2.5-Coder-32B | OpenHands 성공 궤적 491개 SFT | Verified 7.0→20.6%, Lite 3.0→15.3%. 자기 궤적 재학습 시 Lite 15.3→8.7% |
| [Nebius OpenHands 궤적](https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b) | Qwen3-30B-A3B-Instruct-2507 | Qwen3-Coder-480B 궤적 미세조정 | SWE-bench Verified 484개, 100턴: 25.2→49.7 |
| [KG-R1](https://arxiv.org/abs/2509.26383) | 3B 단일 에이전트 | KG 1-hop 조회 서버 위에서 RL | WebQSP Hits@1 82.75(ReKnoS-Qwen3-235B 84.73, RoG-Qwen3-235B 81.68). 4×H100, 400 step |
| [ReSearch](https://arxiv.org/abs/2503.19470) | Qwen2.5-32B/7B | 검색 추론 RL | 32B 평균 EM +14.82%. MuSiQue 19,938개, 8×8 H800 |
| [ToolRL](https://arxiv.org/abs/2504.13958) | Qwen2.5 등 | 도구 호출 보상 설계 GRPO | 데이터 4K, base 대비 +17%, SFT 대비 +15%. A100 80G 2장 |
| [ART·E](https://openpipe.ai/blog/art-e-mail-agent) · [강연](https://www.youtube.com/watch?v=gEDl9C8s_-4) | Qwen2.5-14B | 이메일 검색 에이전트 GRPO | o3 90% 대 RL 96%. 학습 약 $80, H100 1장에서 하루 미만 |
| [RULER](https://openpipe.ai/blog/ruler) | Qwen2.5-14B, Qwen3-14B | LLM judge 상대 순위를 보상으로 | ART-E: 손 보상 96%, RULER(Qwen3 32B judge) 95% |
| [SkyRL-SQL](https://github.com/NovaSky-AI/SkyRL) | Qwen2.5-Coder-7B-Instruct | multi-turn RL | 653개 샘플로 base 대비 최대 8.7% |
| [TinyAgent](https://arxiv.org/abs/2409.00608) | 1.1B, 7B | GPT-4-Turbo 합성 80K로 LoRA | 1.1B 12.71→78.89%, 7B 41.25→83.09%. 데이터 약 $500 |
| [FireAct](https://arxiv.org/abs/2310.05915) | Llama-2-7B | GPT-4 궤적 500개 | HotpotQA EM +11.4점(상대 +77%). LoRA는 RTX 4090 1장 |
| [APIGen-MT](https://arxiv.org/abs/2504.03601) | xLAM-2 | 검증된 과제 청사진 + 시뮬레이션 사용자로 궤적 합성 | τ-bench: 32b 54.6%, 8b 46.7%(GPT-4o 52.9%). 데이터를 평가와 같은 τ-bench 도메인·API로 합성 |
| [FunctionGemma](https://deepmind.google/models/gemma/functiongemma/) · [강연](https://www.youtube.com/watch?v=-TiET_K-E_g) | Gemma 3 270M | 과업별 미세조정 | Mobile Actions 58%→85%. 강연의 앱 인텐트: 약 46% → 10개 함수 중 8개 90% 이상 |
| [Labonne 강연](https://www.youtube.com/watch?v=fLUtUkqYHnQ) | LFM2.5 1.2B Thinking | 단계별 doom loop 비율 | 사전학습 후 약 15%, SFT 후 거의 그대로, DPO 후 크게 줄고 RL 후 거의 없음 |
| [Verifying Interventions](https://neurips.cc/virtual/2026/173060) | Qwen2.5-1.5B | 하네스 대 SFT | 전체 하네스 36.0% 대 SFT 74.7 ± 0.6% |

AgentFlow는 GPT-4o 궤적 SFT를 두고 "This results in a catastrophic performance collapse, with an average accuracy drop of 19.0% compared to the frozen baseline."이라고 적는다. 단서: SFT 궤적 수와 필터링은 이 대목에 없고, planner 하나만 학습한 결과다.

[Tongyi DeepResearch 보고서](https://arxiv.org/abs/2510.24701)는 "SFT teaches the model to reliably imitate curated demonstrations, establishing a stable behavioral baseline for research workflows and tool use. However, behavior cloning alone tends to produce mimicry without exploration."이라고 적는다.

SWE-smith는 "Simple interventions from the agent scaffold can mitigate repetitive actions, but do not seem to improve resolve rates (see §F.5)."라고 적는다.

[Kyle Corbitt 강연](https://www.youtube.com/watch?v=gEDl9C8s_-4)은 RL 전에 프롬프트 기준선부터 만들라고 권한다. 학습 중 턴 수 보상이 마지막 도구 호출을 반복하는 reward hacking을 낳았다는 대목도 있다. 단서: 이메일 검색 하나의 결과이고, 질문은 Gemini 2.5 Pro로 합성했다.

유지비를 경고하는 증언도 있다. [Sovereign Escape Velocity](https://www.youtube.com/watch?v=SS-A8sE7hkw)는 이미 그 언어를 잘하는 모델의 언어별 미세조정을 두고 "So you might spend a lot of time to get like 1%."라고 말한다. Lease End는 재학습 주기가 약 1주였던 미세조정 모델을 기술 부채로 본다.

[추정] 학습은 다음 셋이 갖춰질 때 값을 한다(사례: KG-R1, SkyRL-SQL, ToolRL 4K 포화, FireAct 500개, SWE-Gym 491개, TinyAgent, FunctionGemma — 7개).

| 조건 | 이유 |
|---|---|
| 과제가 좁고 출력 형식이 고정됨 | 수백~수천 개 데이터로 포화한다(ToolRL은 4K를 넘겨도 개선 없음) |
| 검증 가능한 보상이 있음 | 실행 결과·KG 조회·정답 비교가 보상을 만든다. 강한 모델 궤적 모방은 무너진 사례가 있다 |
| 하네스를 먼저 굳힘 | 한 scaffold의 궤적으로 학습한 능력이 다른 scaffold로 잘 옮겨지지 않는다(Qwen3-Coder-Next, 방향에 따라 정도가 다름) |

[추정] 32B를 RL로 학습하는 비용은 사내 서버 한 대의 예산을 넘기 쉽다(사례: DeepSWE 64×H100 6일, ReSearch 8×8 H800, ReTool 32B 재현 약 $10,000 추정 — 3개). 반면 ART·E의 14B RL 학습은 H100 1장에서 하루 미만, 총 약 $80이었다. 사용자 과업에서 학습은 32B 전체가 아니라 작은 전용 모델(동의어 matcher 같은)에 두는 쪽이 맞다.

## 강연·발표 목록

볼 순서대로 놓았다. 앞쪽은 사용자 과업의 설계 질문에 바로 닿는 것, 뒤쪽은 모델·생태계 배경이다.

| 순서 | 제목 | 발표자 | 무대 | 날짜 | 한 줄 요지 |
|---|---|---|---|---|---|
| 1 | [What if the harness mattered more than the model?](https://www.youtube.com/watch?v=2e9ANoOEn28) | Aditya Bhargava(Etsy) | AI Engineer 채널 | 2026-07-07 업로드 | 하네스만 바꿔 52.4~76.2로 갈리고(논문 v1 기준), 약한 모델일수록 하네스가 중요하다 |
| 2 | [Turning My Obsidian Vault Into a Local AI Engineer](https://www.youtube.com/watch?v=Ndp5VaqFrl0) | Filip Makraduli(Superlinked) | AIE World's Fair 2026 워크숍 날 스폰서 세션 | 2026-06-29 | 문서 폴더를 비공개 지식그래프로: 추출은 GLiNER·Qwen3+grammar, 에이전트엔 작은 markdown. 원본 선행 읽기 경로라는 한계도 짚음 |
| 3 | [사용자 발화에서 응답까지: 그래프 기반 에이전트로 동작하는 AI 서비스](https://www.youtube.com/watch?v=XQo0DHuqgVM) | 홍보미·길민호(카카오) | kakao tech 채널 | 2025-09-24 업로드 | 툴이 많아지자 도메인별 에이전트로 쪼개고, 좁은 일은 파인튜닝한 서브 LLM에 맡김 |
| 4 | [NVIDIA's Peter Belcak Explains Why SLMs are the Future of Agentic AI](https://www.youtube.com/watch?v=9xgRTznP21E) | Peter Belcak(NVIDIA) | Arize AI 인터뷰 | 2025-09-05 업로드 | 고정 프롬프트 호출은 좁은 일이라 조각마다 다른 모델, 출력 형식 하나만 익힌 작은 모델 |
| 5 | [State of the Union: Why Local, Why Now](https://www.youtube.com/watch?v=KB41dTlX1Uc) | 패널, 사회 Nader Khalil(NVIDIA) | AIE World's Fair 2026 Local AI 트랙 | 2026-07-02 | 계획은 프론티어, 실행은 로컬. 라우팅할 때 문맥 넘기기와 trace 수집이 과제 |
| 6 | [Beating RL With Reflection: GEPA and Optimize Anything](https://www.youtube.com/watch?v=OA-Mc60Rboo) | Lakshya A. Agrawal | AIE World's Fair 2026 Main Stage | 2026-07-01 | 궤적을 읽고 프롬프트를 고치는 GEPA가 적은 데이터로 GRPO보다 크게 올림 |
| 7 | [Why RL Won](https://www.youtube.com/watch?v=yYZBd25rl4Q) | Kyle Corbitt(OpenPipe) | Latent Space | 2025-10-16 업로드 | 자기 과제에서 GEPA는 소폭, RL은 크게. 가장 어려운 건 재현 가능한 RL 환경 |
| 8 | [How to Train Your Agent: Building Reliable Agents with RL](https://www.youtube.com/watch?v=gEDl9C8s_-4) | Kyle Corbitt(OpenPipe) | AI Engineer 채널 | 2025-07-19 업로드 | 프롬프트 기준선부터. Qwen2.5-14B RL로 o3를 넘고, 보상 해킹과 '모른다' 보상 |
| 9 | [Your Fine-Tuned Model Is Tech Debt](https://www.youtube.com/watch?v=4loPnxvWWhg) | Dan Bjornn(Lease End) | AIE World's Fair 2026 | 2026-06-30 | 미세조정 모델을 버리고 컨텍스트로 행동을 바꾸자 수정이 1시간 안으로 |
| 10 | [From 46% to 90%: Fine-Tuning Tiny LLMs for On-Device Agents](https://www.youtube.com/watch?v=-TiET_K-E_g) | Cormac Brick(Google) | AI Engineer Europe 2026 | 2026-04-08~09 | 스킬 목록을 먼저 주고 세부는 필요할 때. 4B는 스킬 약 8개. FunctionGemma 미세조정 |
| 11 | [Everything I Learned Training Frontier Small Models](https://www.youtube.com/watch?v=fLUtUkqYHnQ) | Maxime Labonne(Liquid AI) | AI Engineer Europe 2026 | 2026-04-09 | 작은 모델은 에이전트 과제에 맞고, doom loop는 DPO·RL에서 줄어듦 |
| 12 | [Lessons from the Trenches in Building Agents for Software Development](https://www.youtube.com/watch?v=eSJexCW-43Y) | Graham Neubig | AI Agent Frontier 세미나 | 2026-03-17 업로드 | 강한 모델에는 스캐폴딩이 많이 필요 없다. MiniMax M2.5가 Opus 가격 약 1/8로 경쟁력 |
| 13 | [The Future of Qwen: A Generalist Agent Model](https://www.youtube.com/watch?v=b0xlsQ_6wUQ) | Junyang Lin(Qwen) | AI Engineer World's Fair 2025 | 2025-06-03 업로드 | 생각하며 도구 쓰기, 32B를 RL·로컬 배포용으로 권함, 모델 학습에서 에이전트 학습으로 |
| 14 | [Kanana: Agentic AI를 향한 카나나 모델의 진화](https://www.youtube.com/watch?v=_kHA74m13fI) | 김병학(카카오) | if(kakao)25 Day2 | 2025-11-17 업로드 | 다단계 지시 이행·툴 사용을 위한 MLA·MoE 30B-A3B |
| 15 | [Gemma, DeepMind's Family of Open Models](https://www.youtube.com/watch?v=_gVFUEdhCyI) | Omar Sanseviero(Google DeepMind) | AI Engineer Europe 2026 | 2026-04-10 | Gemma 4 온디바이스 스킬 에이전트, 140개 넘는 언어와 다국어 토크나이저 |
| 16 | [Sovereign Escape Velocity: Ownership with Open Models](https://www.youtube.com/watch?v=SS-A8sE7hkw) | Gus Martins·Ian Ballantyne(Google DeepMind) | AI Engineer Europe 2026 | 2026-04-09 | 단순 작업에 가장 똑똑한 모델이 필요한가 — 아마 아니다. 언어 미세조정 이득은 1% 남짓일 수 있음 |
| 17 | [Accelerating Open-Source RL and Agentic Inference with vLLM](https://www.youtube.com/watch?v=AZcJJbBBgLc) | Michael Goin(Red Hat·vLLM) | PyTorch 채널 | 2025-11-04 업로드 | vLLM의 툴 호출·구조화 출력. 오픈소스 툴 호출 표준이 아직 없음 |
| 18 | [Self-Training Agents: Hermes Agent, HF Traces, Skills, MCP & Finetuning](https://www.youtube.com/watch?v=OV56RddyFuU) | Merve Noyan(Hugging Face) | AI Engineer Europe 2026 | 2026-04-09 | 오픈 모델에는 Hermes agent, trace를 Hub에 쌓아 특화의 출발점으로 |
| 19 | [Frontier models for the hard parts, open weights for the rest](https://ai.engineer/worldsfair/2026/sessions.json) | 미표기(Kimchi) | AIE World's Fair 2026 Expo Stage | 2026-06-30 | 단계마다 평가해 다시 하거나 프론티어로 올림. 소개문만 있고 영상은 못 찾음 |

단서: 업로드일만 확인한 강연은 '업로드'로 적었다. 패널·발표의 수치는 대부분 측정 조건 없이 나온 발언이다. Etsy·로컬 AI 패널·GEPA·Obsidian·Lease End 영상은 YouTube 자막이 막혀 ai.engineer 페이지의 전사로 대조했다.

## 평가를 먼저 세우는 법

하네스를 바꿀 때마다 나아졌는지 재는 장치가 없으면, 앞의 손잡이 어느 것도 고를 수 없다. 사용자는 사람 검토를 Opus로 대체하므로 판정자의 신뢰도가 모든 비교의 바닥이 된다.

### 자기 과업 평가셋

| 출처 | 권고 |
|---|---|
| [Hamel Husain, LLM-as-a-Judge 가이드](https://hamel.dev/blog/posts/llm-judge/) | 판정을 합격/불합격 이진 분류로 둔다. 전문가 라벨을 train 10~20%, dev·test 각 40~45%로 나누고 세트마다 라벨별 30~50개를 둔다. 오류가 5%면 항상 Pass를 내는 judge도 일치율 95%라 일치율만 보면 안 된다 |
| [Hamel Husain·Shreya Shankar, Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) | 처음엔 trace 최소 30개를 직접 메모하고, 다양한 trace 약 100개를 작업 풀로 둔다. LLM judge는 실패 모드마다 라벨 100~200개 |
| [EvalGen(Who Validates the Validators?)](https://arxiv.org/abs/2404.12272) | 출력을 보면서 기준이 바뀐다(criteria drift). 판정 출력 16개로 만든 단언 집합이 SPADE보다 절반 이하 크기에 coverage 49%→73% |

Hamel 가이드는 "Treat the judge as a binary classifier. Ask a trusted domain expert to label examples, then split them into train, dev, and test sets."라고 적는다. Evals FAQ는 "Error analysis is the most important activity in evals."라고 본다.

단서: 둘 다 실무자 글이고, 90% 일치율은 한 사례의 값이다.

### LLM 판정자 신뢰도

| 출처 | 판정자 | 수치(조건) |
|---|---|---|
| [Judge's Verdict](https://arxiv.org/abs/2510.09738) | judge 54개 | 영어 RAG 응답 채점 1,994문항, 사람끼리 평균 κ 0.801. Qwen3-30B-A3B-Instruct-2507 κ 0.780, Qwen2.5-32B-Instruct κ 0.753, gemma-3-27b-it κ 0.812, Qwen3-4B-Instruct-2507 κ 0.749(탈락) |
| [Rating Roulette](https://arxiv.org/abs/2510.27106) | Qwen3-32B 등 | 3회 실행 사이 Krippendorff's α: SummaC에서 Qwen-3 0.7883, MTBench에서 0.563. MTBench에서 3회 모두 같은 판정 61.3%. SummaC 3회 다수결 80.6 대 단일 79.4 |
| [No Free Labels](https://arxiv.org/abs/2503.05061) | GPT-4o, Qwen 2.5 7B 등 | GPT-4o pairwise κ, 자기가 못 맞힌 문항: 참조 없음 0.30, 자기 답 참조 0.16, 사람 참조 0.83 |
| [2603.22214](https://arxiv.org/abs/2603.22214) | Qwen2.5 7B, Gemma2 9B 등 | LLM 출력의 유해성·품질 판정 534항목, 2차 judge를 붙이자 F1 하락: Qwen2.5 7B(2 Basic 프롬프트) 0.87→0.59, Gemma2 9B(4 CoT 프롬프트) 0.9→0.72 |
| [Ethernet 스위치 KG 추출](https://arxiv.org/abs/2605.19180) | GPT-5 | 실제 Ethernet 스위치 설정 매뉴얼 50개, judge와 사람 κ 0.72~0.80(사람끼리 0.90~0.96) |
| [GraphRAG 편향 보정 평가](https://arxiv.org/abs/2506.06331) | GPT-4o-mini | Agriculture 데이터에서 LightRAG 대 NaiveRAG 승률이 원 보고 66.70%, 위치·길이·시행 편향 보정과 무승부 허용, KG로 만든 새 질문 150개로 다시 재면 39.06%(질문 세트가 달라 같은 조건 비교는 아님) |

No Free Labels는 "Notably, providing a human reference to a relatively small model (such as Qwen 2.5 7B) can yield better judgments than using a larger model without human references (such as GPT-4o) on the same set of responses."라고 적는다.

단서: 영어 재무 QA이고, 살짝 틀린 참조는 참조가 없는 것보다 나쁠 수 있다고 원문이 경고한다.

2603.22214는 "The evaluation shows that the results of nearly all model/prompt combinations deteriorate when using a second-level judge."라고 적는다. 단서: 2차 judge 실험에 32B 이상 모델이 없어 32B급에 그대로 옮기면 안 된다. GPT-4o 같은 상용 모델은 F1이 0.01만 줄었다.

### 자기 판정 편향

| 출처 | 내용(조건) |
|---|---|
| [When Do Agent Loops Mistake Stagnation for Progress?](https://arxiv.org/abs/2607.25152) | 평가자 arm 3개 × 3회 반복 × cycle 예산 6을 합친 54 cycle 모두에서 에이전트가 개선을 주장했지만 oracle로 56%가 delta 0 이하. 가장 강한 in-band judge가 받아들인 cycle의 44%가 실제 회귀였고, 실제 개선의 38%를 거부 |
| [Telco-oRAG](https://arxiv.org/abs/2505.11856) | judge를 바꾸면 같은 시스템 점수가 크게 달라짐: Qwen3-32B judge 78.2%, GPT-5-mini 74.9%, GPT-OSS-120B 58.8%. 저자들이 같은 계열을 높게 주는 편향을 밝히고 MCQ가 낫다고 적음 |
| [GraphMERT](https://arxiv.org/abs/2510.09580) | Qwen3-32B가 만든 KG를 같은 모델로 검증해도 ValidityScore 43.0 — 자기 오류를 많이 잡음 |

진보 신기루 연구는 "For open-ended real-world objectives whose success signal lives in the state of the world outside the transcript, scaling up the judge is not enough; out-of-band evaluation with access to the real world is a structural requirement for preventing the progress mirage."라고 결론짓는다.

단서: 에이전트·judge 모델 이름을 공개하지 않은 예비 원고이고, 반복은 3회뿐이다.

GraphMERT 저자들은 "Surprisingly, the Qwen3-32B LLM KG scores poorly even when validated by the same model, which flags many of its own errors."라고 적는다.

[추정] 같은 모델이라도 '만들기'와 '검사하기'를 다른 단계로 나누면 검사가 쓸모 있다(사례: GraphMERT의 Qwen3-32B 자기 검증 — 1개).

### 한국어 평가 자료

| 출처 | 무엇을 재나 | 수치(조건) |
|---|---|---|
| [KOPA-Bench](https://arxiv.org/abs/2609.05395) | 한국 공공 API 다단계 도구 호출 145과제 | pass@1: Qwen3.5-27B 0.4482, Claude Sonnet 4.6 0.4655, gemma-4-26B-A4B-it 0.3534, EXAONE-4.5-33B 0.2586. 8 seed 재평가 Qwen3.5-27B 0.4681±0.0146(95% 신뢰구간 반폭) |
| [FunctionChat-Bench](https://arxiv.org/abs/2411.14054) | 한국어 단일 턴 500개 + 대화 45개·200턴 | Solar: 단일 턴 83.6인데 Slot Question 0.08, Relevance Detection 0.13. gpt-4o는 0.86/0.91 |
| [Ko-LongRAG](https://aclanthology.org/2025.findings-emnlp.938.pdf) | 한국어 장문 RAG(GPT-4o 판정) | 다중 문서 Answerable: EXAONE 3.5 32B 72.8, Qwen 2.5 32B 48.4, Gemma 2 27B 27.6(Gemma 2는 문맥 8k 제한으로 돌려 평균 14k토큰 문맥이 잘렸을 수 있음). LG AI Research가 자사 EXAONE을 함께 평가 |
| [K-BrowseComp](https://arxiv.org/abs/2606.02404) | 한국 맥락 웹 탐색 300문항 | Gemma-4-31B-it 23.33, Qwen3.6-35B-A3B 12.00, 국가 사업 모델 0.00~10.33(1회 실행) |
| [MLCL](https://arxiv.org/abs/2601.05366) | 다국어 도구 호출 실패 유형 | 인자 값을 사용자 언어로 쓰는 실패가 중국어·힌디어에서 지배적(한국어 없음, 수치는 그림) |

KOPA-Bench 저자들은 "However, open-source models consistently underperform in this multi-step setting, and no existing benchmark measures the gap."이라고 적는다.

MLCL은 "We identify parameter value language mismatch as a dominant failure mode, where models generate semantically appropriate parameter values in the user's language, violating language-invariant execution conventions."라고 본다.

[추정] 한국어 문서라도 지시문·도구 스키마·enum은 영어로 고정하고, 한국어 표현을 정규 ID로 바꾸는 일은 모델 대신 용어집 층에 맡기는 편이 안전하다(사례: MLCL의 인자 값 언어 불일치, KOPA-Bench 저자가 꼽은 엔티티 코드 조회 실패, [MASSIVE-Agents](https://aclanthology.org/2025.findings-emnlp.1099.pdf)에서 작은 모델이 번역 지시에 더 떨어진 결과 — 3개).

[추정] 한국어 특화 모델이 도구 호출에서 자동으로 유리하지는 않다(사례: KOPA-Bench EXAONE-4.5-33B, K-BrowseComp 국가 사업 모델, Kanana-2 카드의 BFCL-v3 Multi-Turn 35.38 대 Qwen3-30B-A3B-Instruct-2507 38.77 — 3개).

### 사용자가 세울 평가

[추정] 아래 절차는 위 자료들을 사내 보고서 연결에 맞춰 엮은 제안이다(사례: Hamel 가이드, Evals FAQ, No Free Labels, Rating Roulette, 진보 신기루 연구 — 5개).

| 단계 | 하는 일 | 기대는 근거 |
|---|---|---|
| 정답셋 | 판정 유형마다 30~50개가 모이도록 보고서 청크를 골라 사람이 용어 span·정규 ID·링크를 라벨링한다. 템플릿 문서와 형식 없는 문서를 섞는다 | Hamel(라벨별 30~50개), Evals FAQ(trace 30→100) |
| 판정 형태 | 링크·동일성은 합격/불합격 이진 판정으로 묻고, 용어집 항목과 원문 위치를 참조로 함께 준다 | Hamel, No Free Labels |
| Opus 검증 | Opus 판정과 사람 라벨의 κ를 dev·test에서 따로 잰다. 기준을 고치면 버전을 올린다 | Judge's Verdict, EvalGen |
| 흔들림 기록 | 같은 입력을 3회 판정해 α와 다수결 효과를 기록한다 | Rating Roulette |
| 결정적 검사 | 원문 위치 존재, 용어집 ID 존재, 허용 관계 유형 같은 검사는 judge 앞에 코드로 둔다 | 진보 신기루 연구, LangExtract |

## 사내 보고서 연결에 옮기기

사용자 요청의 "필요한 작업에 맞는 에이전트 구축"을 사내 보고서 연결 과업에 맞춰 짠 구성이다. 과업을 다섯 단계로 나누고, 단계마다 고정 단계·작은 전용 모델·에이전트 중 무엇을 둘지와 기대는 근거를 적는다.

### 왜 단계별로 나누나

[추정] 하나의 자율 에이전트에 다섯 일을 다 맡기기보다, 대부분을 고정 단계로 두고 판단이 필요한 두 자리(엔티티 해석의 애매한 경우, 링크 판단)에만 Qwen 32B를 두는 편이 맞다(사례: Progressive Crystallization, Agentless, AgentFloor 프롬프트 단계 분해 하락, Small Agents의 orchestrator 지배, 카카오의 서브 LLM 분리 — 5개).

### 단계별 구성

| 단계 | 담당 | 하는 일 | 기대는 근거 |
|---|---|---|---|
| 1. 문서 유형·템플릿 판별 | 고정 단계 + 짧은 분류 호출 | 제목 계층·표 구조로 템플릿을 추론하고, 템플릿이면 필드 위치 규칙으로 뽑는다. 형식 없는 문서만 다음 단계의 LLM 추출로 보낸다 | [TWIX](https://arxiv.org/abs/2501.06659)(필드 추론에만 LLM에 좁은 질문을 하고, 템플릿을 추론한 뒤 추출은 LLM 없이 함. 2,000쪽 넘는 대형 문서 모음에서 가장 강한 비교 도구보다 520배 빠르고 3,786배 쌈), Let Me Speak Freely(분류에는 JSON-mode가 도움) |
| 2. 구조화 추출과 원문 위치 연결 | Qwen 32B 또는 작은 전용 모델 + 결정적 정렬 | 스키마에 근거 필드를 앞에 두고 용어 span만 뽑는다. 추출값을 원문 문자 위치에 정렬하고, 위치를 못 찾은 값은 버린다. 다회 패스로 재현율을 올린다 | [LangExtract](https://github.com/google/langextract), [DocETL](https://arxiv.org/abs/2410.12189) gleaning, CRANE, [Reference-Aligned RAG](https://arxiv.org/abs/2502.19596)(슬라이드·장 단위 Markdown 청크, 문장별 근거 매칭) |
| 3. 용어 정규화·엔티티 해석 | 결정적 후보 검색 + Qwen 32B가 후보 중 고르기 + 불확실한 것만 사람·Opus | 용어집 별칭 색인·BM25·임베딩으로 후보를 좁히고, LLM은 '이 표현이 후보 중 어느 항목인가'만 고른다. 후보가 없거나 애매하면 새 용어 대기열로 보낸다 | [ComEM](https://arxiv.org/abs/2405.16884), [LogMapLLM](https://arxiv.org/abs/2508.08500), [HippoRAG 2](https://arxiv.org/abs/2502.14802)(동의어 엣지 임계 0.8), [Telco-RAG](https://arxiv.org/abs/2404.15939), [Wikontic](https://arxiv.org/abs/2512.00590), [RAGU](https://arxiv.org/abs/2607.11683) |
| 4. 링크 판단 | Qwen 32B 에이전트(짧은 고정 루프) | 정해 둔 관계 어휘 안에서 두 문서·엔티티를 이을지 판단한다. 근거 청크를 짧게 2회 정도 검색해 붙인다. 그래프는 원문 청크를 대체하지 않고 보탠다 | [Dissecting Agentic RAG](https://arxiv.org/abs/2606.21553), [RAG vs GraphRAG](https://arxiv.org/abs/2502.11371), [GraphRAG-Bench](https://arxiv.org/abs/2506.05690), [KG-R1](https://arxiv.org/abs/2509.26383)(1-hop 조회 서버) |
| 5. 검증 | 코드 검사 + 별도 판정 단계 | 원문 위치·용어집 ID·관계 유형을 코드로 검사한다. 통과한 것만 Opus(실험 땐 Haiku) 판정에 참조와 함께 넘긴다. 같은 Qwen 32B도 별도 검사 단계로는 쓸 수 있다 | 진보 신기루 연구, No Free Labels, GraphMERT, [Ethernet KG](https://arxiv.org/abs/2605.19180) |

### 단계 1 — 템플릿 판별

TWIX 저자들은 "The key insight of our tool, TWIX, is to infer the underlying template used to create such documents, and then extract the data, rather than extracting directly from documents."라고 적는다.

단서: TWIX 평가는 PDF 레이아웃 좌표에 기댄다. 워드·HWP 보고서에서 제목 계층이나 표 구조로 대체할 수 있는지는 아무 출처도 답하지 않는다.

### 단계 2 — 추출과 원문 위치

LangExtract README는 "LangExtract automatically detects this: extractions that cannot be located in the source text will have `char_interval = None`."이라고 적는다. 이것이 judge 없는 결정적 게이트가 된다.

단서: 토크나이저에 Hangul 패턴은 있지만 한국어 정렬 품질은 측정된 적이 없다. README는 "Ollama does not currently support output_schema"라고 적어서, Qwen 32B는 vLLM OpenAI 호환 경로로 붙여 시험해야 한다(미확인).

[Obsidian 워크숍](https://www.youtube.com/watch?v=Ndp5VaqFrl0)은 도구마다 모델을 나눴다: extract_entities=GLiNER, redact_pii=GLiNER PII, extract_structured=Qwen3 + grammar.

[추정] 엔티티 후보 span은 GLiNER 같은 작은 전용 모델로, 필드 추출은 32B + 문법으로 나누는 분업이 사용자 과업에 맞을 것이다(사례: Obsidian 도구 표, 카카오 서브 LLM, RAGU의 7B 추출 모델 — 3개).

[LightRAG 이슈 #2720](https://github.com/HKUDS/LightRAG/issues/2720)은 30~32B급 로컬 모델(주범은 nemotron-3-nano:30b)이 엔티티 이름에 자기 교정 독백·구분자·제어 토큰을 섞었다고 보고한다: "We found 15 malformed entities across 3 ingested books (all produced by similarly sized models around 32B)." temperature 0.2에서 같은 chunk가 3회 연속 같은 오염으로 실패해 재시도가 소용없었다.

단서: 같은 사용자는 qwen2.5:32b-instruct가 522쪽 PDF를 잘 처리했다고 적었고, 메인테이너는 Qwen3-30B-A3B-Instruct를 안정적인 최소 모델로 권했다. [LightRAG README](https://github.com/HKUDS/LightRAG)도 "For local deployment, Qwen3-30B-A3B-Instruct is a reasonable minimum."이라고 적는다.

### 단계 3 — 용어 정규화

ComEM은 "Experimental results verify the effectiveness of incorporating record interactions through the selecting strategy, with an average 16.02% improvement in F1 over the current matching strategy."라고 적는다. 8개 데이터셋 평균 F1은 Llama-3.1-8B가 matching 47.75에서 selecting 76.33으로, Qwen2-7B가 62.11에서 74.93으로 올랐다(comparing은 78.34).

단서: 후보는 Flan-T5-XL이 먼저 걸렀고, Qwen2-7B에서는 고르기보다 비교하기가 높았다.

LogMapLLM은 "LLMs are used only in the validation of a subset of correspondences for which there is high uncertainty."라는 구조다. anatomy 과제에서 Qwen3-8b의 Youden 지수는 0.590이었다. 단서: 오픈 모델 평가는 저자들이 '예비'라 부르고, Qwen3 로컬 실행은 M2 노트북에서 요청당 평균 125초를 넘겼다.

Telco-RAG는 "For each question, we enriched the embedding with the definitions of relevant terms from the dictionaries."라고 용어집을 질의에 붙인다. Telco-oRAG에서 Qwen3-32B MCQ는 Telco-oRAG 전체로 56.0%→82.4%였다.

단서: 이 비교는 RAG를 아예 쓰지 않은 모델 대 전체 시스템이라 용어집만의 효과가 아니다. 질의 보강(LLM 재작성과 용어집)의 효과를 따로 잰 lexicon 500문항은 생성 모델 GPT-3.5로 Benchmark RAG 84.8% 대 Telco-oRAG 90.8%다. 같은 숫자(80.2/84.8/90.8)가 Telco-RAG Table II에도 있어 새로 쟀는지는 알 수 없다.

RAGU는 엔티티를 먼저 뽑아 스키마로 검증하고, 관계의 양 끝이 검증된 엔티티 이름과 맞아야 한다고 묶는다("every source_entity and target_entity in a relation must match a validated entity name").

Wikontic은 "performs alias-aware entity normalization and deduplication to reduce redundancy, yielding ontology-consistent KGs"라고 적는다.

[추정] 용어집을 인덱싱 시점 정규화, 질의 시점 확장, 동의어 엣지 중 어디에 둘지는 비교 연구가 없어서 사내 평가셋으로 재야 한다(사례: Wikontic·KGGen의 인덱싱 시점, Telco-RAG의 질의 시점, HippoRAG 2의 동의어 엣지 — 3개).

### 단계 3 — 대량 동의어 판정

[Labeling Training Data for Entity Matching Using Large Language Models](https://arxiv.org/abs/2606.28823)(아래 '엔티티 매칭 라벨링 연구')는 "An open-weight teacher trains competitive students, so distillation requires no closed-weight models."라고 적는다. Abt-Buy에서 Qwen3 zero-shot은 0.6B 35.74, 8B 85.31로 갈렸지만, GPT-5.2 라벨로 학습하면 88.42와 89.58로 거의 같아졌다.

단서: 이 비교는 Abt-Buy 한 벤치마크의 예시다. 처음 보는 상품이 많은 WDC Products에서는 teacher(Kimi K2.6 87.20)가 자기 학생(72.09)보다 크게 높았다.

[추정] 학습한 matcher는 처음 보는 항목에 약하므로 새 용어는 LLM 경로로 돌려야 한다(사례: WDC Products와 billiger.de에서 teacher가 자기 학생보다 6.44~16.07 F1 높았던 결과 — 2개).

### 단계 4 — 링크 판단

Dissecting Agentic RAG 저자는 "most of the gain comes from running a short retrieval loop, not from adaptive routing or from many iterations."라고 적는다.

RAG vs GraphRAG는 "We found that only around 65.8% of answer entities exist in the constructed KG for the Hotpot dataset and 65.5% for the NQ dataset."라고 경고한다.

GraphRAG-Bench는 "GraphRAG exhibits a higher sensitivity to model capacity than Standard RAG."라고 적는다.

단서: 65.8%는 triplet만 쓰는 KG 방식의 한계이고, GraphRAG-Bench의 크기 비교는 생성 모델 Qwen2.5 3B~14B에서 했다.

### 단계 5 — 검증

[Ethernet KG 논문](https://arxiv.org/abs/2605.19180)은 네트워크 장비 매뉴얼에서 judge와 사람의 일치를 "Cohen’s kappa scores range from 0.72 to 0.80, indicating substantial agreement between human evaluation and the LLM-as-a-Judge."라고 보고한다.

단서: judge가 GPT-5이고, 사람 2명은 저자이며 합의본과 비교했다. 오픈 모델로 κ가 유지되는지는 재지 않았다.

### 실험 순서

[추정] 아래 순서는 위 근거를 사용자 환경(운영 Qwen 32B급, 실험 Ollama 작은 모델·Haiku, 검토 Opus)에 맞춰 엮은 제안이다(사례: Hamel 가이드의 평가 우선, ART·E의 프롬프트 기준선 우선, Qwen3-Coder-Next의 scaffold 묶임, AgentFloor의 크기별 부호 반전 — 4개).

| 순서 | 할 일 | 끝났다고 볼 기준 | 근거 |
|---|---|---|---|
| 0 | 운영 체크포인트(Qwen3-32B인지 Qwen3.5 이후 27B인지)와 서빙 엔진을 정하고, 파서·reasoning 파서·컨텍스트(Ollama의 에이전트 권고 64000 이상, Qwen3.6-27B 카드는 128K 이상 권고)·샘플링을 카드대로 고정한다 | 같은 입력을 넣었을 때 tool_calls가 비거나 추론이 content로 새지 않는다 | #서빙 설정의 함정 |
| 1 | 정답셋과 Opus 판정자를 세운다 | Opus와 사람의 κ를 dev·test에서 잰다 | #평가를 먼저 세우는 법 |
| 2 | 기준선: 단일 프롬프트로 Qwen 32B가 추출·정규화·링크를 한 번에 한다 | 단계별 점수가 기록된다 | ART·E·Corbitt 강연 |
| 3 | 구조를 한 번에 하나씩 바꾼다: (a) 용어집 후보 고르기 대 자유 정규화 (b) 고정 단계 대 자율 루프 (c) 근거 필드 + 답만 제약 대 자유 출력 (d) 다회 패스 (e) 원문 위치 게이트 | 각 변경의 이득과 비용이 같은 판정으로 비교된다 | #하네스 구조, #출력 형식과 구조화 생성 |
| 4 | 굳힌 하네스 위에서 GEPA류 프롬프트 최적화를 돌린다 | 판정자 검증이 끝난 신호로만 최적화한다 | GEPA, OpenPipe 반대 증거 |
| 5 | 작은 모델·Haiku에서 얻은 결론을 운영 32B에서 다시 확인한다 | 순위가 유지되는지 본다 | AgentFloor의 thinking 부호 반전, [Strings to Things](https://arxiv.org/abs/2607.00003)의 Gemma-3 대 Qwen3 차이 |
| 6 | 남은 병목 중 좁고 정답을 만들 수 있는 단계(동의어 판정)만 작은 matcher로 증류하거나 LoRA로 학습한다 | 새 용어 경로가 따로 있다 | 엔티티 매칭 라벨링 연구, #학습이 값을 하는 때 |

순서 5의 근거: Strings to Things에서 5-shot 전체 F1은 Gemma-3 12B 0.6617, Qwen3 8B 0.1680이었다.

단서: 영화 추천 대화 도메인이고 Qwen3의 thinking 설정이 논문에 적혀 있지 않다.

[추정] 실험 모델과 운영 모델의 계열이 다르면 구조 비교의 순위가 뒤집힐 수 있다(사례: Strings to Things, AgentFloor의 thinking 부호 반전, 엔티티 매칭 라벨링 연구의 Qwen3 0.6B 대 8B zero-shot 차이 — 3개).

## 반대 증거와 열린 질문

### 반대 증거

| 주장 | 반대 증거 | 출처 |
|---|---|---|
| 하네스가 모델보다 중요하다 | 강한 모델에는 스캐폴딩이 많이 필요 없다. Harness-Bench v2에서도 Qwen3.8-27B를 뺀 9개 모델은 하네스 간 차이가 5.0~9.5점에 그친다 | Neubig 강연, Harness-Bench v2 |
| 프롬프트 최적화가 RL을 이긴다 | OpenPipe 과제 50→56(GEPA) 대 96(RL). AIME-2025는 GRPO 38.00 대 GEPA 32.00. Training-Free GRPO의 Qwen3-32B는 RL 학습 32B보다 30점 넘게 낮음 | Why RL Won, GEPA 논문, Training-Free GRPO |
| 경험·playbook 누적이 개선한다 | QwQ-32B WebWalkerQA 부분집합 pass@1 25.5 대 27.5. 피드백이 약하면 ACE도 떨어진다고 저자가 경고 | Training-Free GRPO, ACE |
| 고정 워크플로가 낫다 | OAgents에서 정적 workflow 47.88이 기준 51.52보다 낮음 | OAgents |
| 학습 없는 하네스로 충분하다 | 1.5B에서 하네스 36.0% 대 SFT 74.7%. 미세조정 FunctionGemma 58%→85% | Verifying Interventions, FunctionGemma |
| 강한 모델 궤적을 SFT하면 된다 | GPT-4o 궤적 SFT 19.5(frozen 38.5). SWE-smith 32B 궤적의 25% 넘게 반복 루프 | AgentFlow, SWE-smith |
| GraphRAG가 기본 RAG보다 낫다 | Novel 사실 검색 ACC(GPT-4o-mini 생성): rerank 붙인 RAG 60.92 대 MS-GraphRAG 49.29. 편향 보정·무승부 허용·새 질문으로 다시 재자 LightRAG 승률 66.70%→39.06% | GraphRAG-Bench, 편향 보정 평가 |
| 양자화는 거의 손해가 없다 | 집계 점수는 평평하지만 실패량 최대 2.5배 | Flat Score |

### 열린 질문

| 질문 | 무엇을 보면 알 수 있나 |
|---|---|
| 하네스 효과가 코딩 밖(문서 연결, 용어 정규화)에서도 같은 크기로 나는가. 찾은 통제 실험은 거의 SWE-bench·Terminal-Bench다 | 사내 평가셋으로 하네스 여러 개를 비교한다 |
| Qwen 32B급이 한 노드에서 안정적으로 고르는 도구 수는 얼마인가 | 도구 수를 단계적으로 늘리며 같은 과제를 잰다 |
| 한국어 문서에서 Context Rot의 distractor 효과, constrained decoding 품질, 양자화 손실이 영어와 같은가 | 한국어·영어 혼용 장비명이 든 사내 청크로 같은 실험을 반복한다 |
| 한국어 엔티티 동일성 판정에서 오픈 judge·Opus와 사람의 κ는 얼마인가. 엔티티 매칭을 오픈 judge로 판정하고 사람 일치도를 잰 연구는 찾지 못했다 | 사내 쌍을 사람이 라벨링해 잰다(Evals FAQ는 실패 모드당 100~200개를 권함) |
| 용어집을 인덱싱 시점 정규화, 질의 시점 확장, 동의어 엣지 중 어디에 둘 때 병합 실수와 재색인 비용이 가장 작은가 | 세 방식을 같은 평가셋으로 비교한다 |
| 용어집을 ACE식 playbook으로 갱신할 때 어떤 신호가 충분히 강한가(Opus 검토, 작성자 확인, 그래프 일관성 검사) | 각 신호로 갱신한 용어집의 정밀도를 정답셋으로 잰다 |
| LangExtract의 fuzzy 정렬(토큰 coverage 0.75 이상)이 한국어 조사·띄어쓰기 변이에서 얼마나 맞는가 | 사내 문서로 정렬 실패율을 센다 |
| TWIX식 템플릿 추론을 PDF 좌표 없는 워드·HWP에서 할 수 있는가 | 사내 템플릿 문서로 제목 계층·표 구조 신호를 시험한다 |
| Qwen3.5 이후 hybrid 구조에서 vLLM prefix caching이 블록 경계에서만 재개되어 고정 prefix 이득이 줄어드는가 | 모델 config의 layer 종류와 vLLM 시작 로그를 본다 |
| 사내 GPU에서 Qwen 32B의 동시성별 처리량은 얼마인가. 공식 자료는 batch 1뿐이다 | vllm bench serve에 사내 프롬프트 길이 분포를 넣는다 |
| Qwen3.5·3.6·3.8과 Gemma 4를 같은 중립 하네스에서 잰 독립 비교가 있는가. Qwen3.6 카드의 Gemma4-31B 대 Qwen3.6-27B(SWE-bench Verified 52.0 대 77.2)는 Qwen 자기 하네스 값이다 | 공식 BFCL 갱신이나 제3자 평가를 기다리거나 직접 잰다 |
| 카카오 그래프 에이전트가 운영에 쓰는 메인 모델과, 쿼리 리라이트용으로 파인튜닝한 LLM의 기반 모델은 무엇인가 | if(kakao)25 세션 페이지의 발표자료를 연다(주소는 확인하지 못함) |

## 확인하지 못한 자료

반박 검증에서 틀렸거나 열지 못한 항목은 없었다. 아래는 조사 중에 찾아보았지만 1차 출처로 확인하지 못했거나, 초록만 보고 본문 주장에 쓰지 않은 자료다.

| 자료 | 상태 |
|---|---|
| Junyang Lin NeurIPS 2025 DL4C 초청 강연 'Qwen3: Towards a Generalist Model / Agent' | 페이지에 초록·영상이 없음 |
| Google I/O 2025·2026 Gemma 에이전트 세션, Google Cloud 'The Agent Factory' Gemma 4 편 | 세션 카탈로그를 못 찾음 / 자막 없음 |
| Kimchi(Ferment) 세션 영상 | 일정표 소개문만 있음 |
| Latent Space의 Qwen 팀 인터뷰 | 찾지 못함 |
| NAVER DEVIEW/DAN25, 토스 SLASH 25, 우아콘 2025, 삼성SDS, LG AI연구원, 업스테이지의 온프레미스 오픈 모델 에이전트 세션 | 찾지 못함 |
| vLLM·SGLang 밋업(한국 vLLM 밋업 2025-08 포함) 슬라이드 | 찾지 못함 |
| Verifying Tool-Using Agent Interventions 본문 | OpenReview PDF가 브라우저 검증에 막혀 초록만 확인 |
| Continuum, CacheScout, KVFlow 본문 | 초록만 확인 |
| Large Language Monkeys(arXiv 2407.21787), More Agents Is All You Need(arXiv 2402.05120), R2V-Agent(arXiv 2605.16604) | 초록·일부만 확인해 목록에서 뺌 |
| ACBench(arXiv 2505.19433), 'Compression Breaks Discipline'(NeurIPS 2026 SLM-Agents 워크숍) | 초록·학회 페이지만 확인 |
| Stop Comparing LLM Agents Without Disclosing the Harness(arXiv 2605.23950) | 초록만 확인, Qwen·Gemma 수치 없음 |
| Qwen3.5·Qwen3.6 텍스트 모델 기술보고서 | arXiv에서 찾지 못함 |
| HyperCLOVA X THINK(arXiv 2506.22403), EXAONE 4.0(arXiv 2507.11407) 기술보고서의 agent/tool 표 | 초록만 확인 |
| HyperCLOVAX-SEED-Think-32B 카드의 Tau² 수치 | 이미지라 옮기지 못함 |
| FunctionChat-Bench의 Qwen3 이후·Gemma 3/4·EXAONE 4.0·Kanana-2 점수 | 1차 자료에 없음 |
| τ²-bench τ-i18n 한국어 언어 팩 결과 | README에 점수 없음 |
| Beyond Scale and Generation(arXiv 2607.24688, Qwen3 entity matching 요인 실험) | HTML 404로 초록만 확인 |
| Zep/Graphiti 논문(arXiv 2501.13956) 엔티티 해석 절차 | README만 확인 |
| GraphJudge(arXiv 2411.17388), Judging the Judges(arXiv 2406.07791) | 초록만 보거나 열지 않음 |
| 국내 통신사 네트워크 문서 RAG 기술 자료, Allganize 한국어 RAG 리더보드 원표, 한국어 사내 문서 LightRAG·GraphRAG 적용 후기 | 보도 기사만 찾음 |
| Microsoft GraphRAG를 로컬 Qwen으로 돌린 정량 비교 | 찾지 못함 |
| Terminal-Bench 2.0 공식 리더보드 행 | URL이 4.0 보드로 바뀜 |
| Tongyi DeepResearch GitHub README의 GAIA 수치 | 결과가 이미지 |
| Codex CLI + Gemma 4 로컬 운영 글 | 404 |
| Qwen3.8-27B 공식 출시일 | vLLM recipe 추가일(2026-08-14)과 HF 저장소 생성일(2026-08-05)만 확인 |
| DeepSWE·SkyRL-SQL Notion 원문 | JS 렌더링으로 열지 못함(Together AI 블로그, NovaSky 블로그 원본으로 대신) |
| OneKE 구성요소별 수치 | 그림에만 있음 |
| Gemma 3 문서의 'Gemma does not output a tool specific token' 문장 | 옛 함수 호출 주소가 Gemma 4 페이지로 연결되어 1차 출처로 확인하지 못함. Gemma 3와 Gemma 4의 도구 토큰 대비에는 쓰지 않음 |
| SkyRL-SQL의 '+9.2%' | 1차 출처에서 찾지 못해 NovaSky 블로그의 '최대 8.7%'로 대신함 |
| R2E-Gym의 NeurIPS 2025, OAgents의 ICML 2025, KGGen의 NeurIPS 2025, SGLang의 NeurIPS 2024, EvalGen의 UIST 2024 게재 표기 | arXiv 페이지·PDF에 표기가 없어 확인하지 못함. 본문에는 학회명을 쓰지 않음 |
# 사건·관계를 미리 정하지 않기: 조사 종합

조사일 2026-10-11. 사용자 물음: "사건과 관계는 미리 알아두지 못할거 같은데, 이것들을 해결하기 위한 논문이나 사람들의 영상 및 글이 있는지 조사."

## 답

미리 다 정하지 않는 방법은 논문과 코드에 있다. 공통 모양은 하나다. 처음에는 자유 이름과 근거 서술로 남기고, 같은 뜻으로 자주 모이는 것만 나중에 정식 이름으로 올린다.

빈 곳도 셋 있다. 한국어·사내 문서·8B 이하 모델로 잰 출처가 없다. 사건이 다루는 기간과 사건이 일어난 때를 나눈 출처가 없다. 다른 작성자가 쓴 같은 사건을 하나로 합치는 규칙도 없다.

반대 방향의 근거도 하나 있다. 문서 사이 관계(후속·반박·배경)는 작은 고정 목록으로 시작해도 된다. 사람 판정자 9명에게 새 관계를 만들어도 된다고 했지만 "No new relations were proposed."였다(Afantenos 2004, PDF 2쪽, Zhang 외 2002 실험의 요약).

## 표시

- `[대조]`: 메인 세션이 원문 텍스트나 코드 줄을 직접 열어 수치·인용을 맞췄다.
- 표시가 없는 것은 갈래 파일의 확인 상태를 따른다. 갈래 파일은 #갈래 파일 에 있다.

## 세 층

"2026년 결산"은 세 층으로 갈린다. 사건 종류("결산"), 때가 붙은 사건 하나("2026년 결산"), 그 사건과 다른 문서 사이 관계("J가 H의 원인이다")다. 층마다 미리 정하지 않는 방법이 다르다.

| 층 | 미리 정하지 않는 방법 | 대표 출처 | 작은 모델 근거 |
|---|---|---|---|
| 사건 종류 | 술어+대상 쌍이나 LLM이 쓴 짧은 개념 이름을 군집한다 | ETypeClus(EMNLP 2021), ConceptE(arXiv 2606.21048) | 발견 단계에 LLM을 쓴 출처는 모두 Qwen3-32B 이상이다. 7~13B few-shot 종류 붙이기 F1은 10 안팎이다(TextEE) |
| 사건 하나 | 특정 날짜에 몰린 구절을 군집하거나, "날짜: 한 문장 요약"끼리 검색·날짜 필터·예/아니오로 잇는다 | EvMine(KDD 2022), EpiMine(arXiv 2408.04873), LLM-TLS(ACL 2024) | EpiMine은 LLM을 마지막 이름 짓기 한 곳에서만 부른다 `[대조]` `epimine.py:315`. LLaMA-2-7B 제로샷 같은 사건 판정은 GVC B3 53.5, 증류한 Longformer는 84.3이다 `[대조]` (Nath 2024 Table 2) |
| 기간 풀기 | 모델은 `This(DCT, YEAR)` 같은 연산자만 고르고 날짜는 코드가 계산한다 | SCATE(arXiv 2507.06450), HeidelTime | 7B가 날짜 값을 바로 내면 TempEval-3 48.1이다 `[대조]` (Gautam 2024 Table 1). 연산자로 미세조정한 0.5B는 0.59로 Claude 3.7(0.49)을 넘었다 `[대조]`. 단, 큰 LLM이 만든 학습 예 8,583개가 들었다 `[대조]` |
| 관계 | 자유 관계구로 뽑고, 유사도로 묶고, 빈도 문턱을 넘은 묶음만 승격한다 | DIAL-KG(arXiv 2603.20059), ORELLM(ACL 2024), Neo4j LLM Graph Builder, ATOM | 관계구를 문자열 일치로만 묶으면 FewRel 13.05%다. 1.5B 모델이 쌍 유사도를 재면 군집 수를 몰라도 46.03%다 `[대조]` (ORELLM Table 1·2) |

## 공통 모양

네 갈래의 출처를 이으면 순서 하나가 나온다. 단계마다 그 일을 하는 출처가 있다.

| 순서 | 하는 일 | 출처 |
|---|---|---|
| 1 | 관계·사건 종류를 자유 이름과 근거 서술로 남긴다 | GraphRAG claim(주체·대상·자유 claim type·시작일·종료일·근거 인용) `[대조]` `extract_claims.py:19`, Han & Lai(arXiv 2601.09069) |
| 2 | 임베딩 유사도로 같은 뜻 후보를 묶는다 | ATOM `θ_R = 0.7` `[대조]` `README.md:119`, `matcher.py:144-153`. CESI의 임계값 HAC |
| 3 | 작은 모델에게는 "이 둘이 같은가" 예/아니오만 맡긴다 | ORELLM(1.5B 유사도), LLM-TLS(같은 사건 판정) |
| 4 | 빈도 문턱을 넘은 묶음만 정식 이름으로 올린다. 떨어진 후보는 지우지 않는다 | DIAL-KG "failed ones are kept in a proposal pool for re-evaluation with more data." `[대조]` (4.3절) |
| 5 | 합칠 때는 이미 있는 이름 안에서만 고른다 | Neo4j "Do not create or infer new names for categories" `[대조]` `constants.py:835` |

이 모양은 지난 계획을 이렇게 바꾼다. 용어집은 이름 층을 맡는다. 사건 키는 사건 하나 층의 후보 고르기를 맡는다. 고정 관계 목록 세 개는 씨앗 목록으로 낮추고, 목록 밖 이름은 후보 풀로 보낸다.

## 원인 관계는 조심

작은 모델이 문서 사이 원인을 스스로 찾게 하면 약하다. CRAB에서 Flan-Alpaca의 이진 인과 판정 macro F1은 같은 문서 73.8, 다른 문서 56.7이다 `[대조]` (Table 2). LLMs4OL에서 LLaMA-7B의 관계 성립 판정 F1은 20.3이다.

실무에서도 같은 오류가 보고됐다. Zalando는 여러 팀의 장애 회고를 분석하면서 "The earlier prototypes were built with small models from 3B to 12B parameters." 바로 뒤에 "We have observed up to 40% probability for hallucination at summary and analysis phases."라고 적었다 `[대조]`. 문서에 이름만 나온 기술을 원인으로 엮는 오류는 "only explicitly stated connections are flagged" 지시를 넣고도 Claude Sonnet 4에서 약 10% 남았다 `[대조]`.

그래서 원인·대응 관계는 작성자가 쓴 명시 문장을 근거로 붙일 수 있을 때만 화살표로 남긴다. 나머지 쌍은 종류 없는 "관련 있음"으로 둔다. LinkedIn은 종류 없는 티켓 연결(제목 임베딩 유사도)로 약 6개월 운영하며 중앙 해결 시간을 28.6% 줄였다 `[대조]` (arXiv 2404.17723 초록·§5, 표 3의 P50 7시간 → 5시간).

## 같은 사건 판정

사용자 안의 "사건 종류 + 기간" 키는 X-AMR의 `EIDlt`(행위자+술어+장소+시간)와 같은 모양이다. X-AMR은 이런 키만으로는 "A CoNLL F1 of 80% seems to be an upper bound for a purely symbolic approach for ECR."라고 적었다 `[대조]` (§5). 그래서 키는 후보를 고르는 데 쓰고, 키가 같은 쌍과 빗나간 쌍은 2단계 판정에 넘긴다.

GPT-4도 상대 시간과 이름 일관성에서 무너져 사람 주석보다 15~25점 낮았다(X-AMR §7, §8.2). 이 두 일은 모델 밖의 규칙과 용어집이 맡는 쪽이 맞다.

## 지금 안을 고치면

| 지금 안 | 조사 뒤 | 근거 |
|---|---|---|
| 사건 종류를 용어집에 둔다 | 종류는 자유 이름으로 뽑고, 나중에 묶어 용어집 후보로 올린다 | ConceptE(기존 온톨로지를 데이터로 넓힘), GraphRAG claim type |
| 기간 규칙을 손으로 쓴다 | 규칙 표는 회사 달력 설정으로 남기고, 모델은 연산자만 고른다 | SCATE. HeidelTime 자동 한국어 자원에는 "올해·작년·내년"이 없다 `[대조]` |
| 사건에 기간 칸 하나 | 대상 기간과 작성일을 두 칸으로 둔다 | 읽은 출처 모두 시간 칸이 하나다. 2027-01의 "이번 결산"은 2026년이 대상이다 |
| 관계 목록 세 개 고정 | 씨앗 목록 + 목록 밖 허용 + 후보 풀 → 문턱 넘으면 승격 | DIAL-KG, LlamaIndex `DynamicLLMPathExtractor` |
| LLM이 쌍마다 관계를 고른다 | 예/아니오 판정으로 좁히고, 원인은 명시 문장이 있을 때만 | ORELLM, CRAB, Zalando |
| 키가 같으면 같은 사건 | 키는 후보 고르기, 같은 사건인지는 따로 판정 | X-AMR 상한 80, lemma 휴리스틱 + 판정기(ECB+ 76.4 → 81.7) |

## 아무도 안 푼 것

| 빈 곳 | 우리에게 왜 걸리나 | 본 범위 |
|---|---|---|
| 한국어·사내 문서 | 모든 수치가 영어 뉴스·벤치마크다. HeidelTime 자동 한국어 자원에 상대 연도 낱말이 없다 | 네 갈래 전부 |
| 8B 이하로 도는 전체 흐름 | 발견·승격 단계는 모두 32B 이상이나 API 모델을 썼다 | 사건·관계 갈래 |
| 대상 기간과 발생 시점 | "이번 결산"(2027-01 작성)이 2026년 결산과 묶여야 한다 | 시간 갈래 12개 출처 |
| 다른 작성자의 같은 사건 합치기 | ATOM은 triple이 같아질 때만, GraphRAG claim은 아예 합치지 않는다 | 실무 갈래 |
| 묶기 이력과 되돌리기 | Neo4j는 이름을 덮어쓰고, Graphiti는 다시 넣으라고 한다. 19번 조사의 "지우지 말고 표식"과 이어 붙일 자리다 | 실무 갈래 |
| 정규화할 때 관계 방향 지키기 | Neo4j 예시는 `PUBLISHED_BY`·`_IN`·`_ON`을 `PUBLISHED` 하나로 합친다. LightRAG는 간선 방향을 버린다 | 관계 갈래 |
| 회사 회계 달력 | HeidelTime은 "fiscal first quarter"를 달력 분기 Q1로 바꾼다. 회계연도 시작 월을 설정으로 받는 도구가 없다 | 시간 갈래 |

## 갈래 파일

| 파일 | 다룬 것 | 출처 |
|---|---|---|
| `22-open-events-relations/events.md` | 사건 종류·사건 하나 발견 | 14개(원문 11, 코드 2, 초록 1) |
| `22-open-events-relations/relations.md` | 열린 관계, 관계 정규화, 스키마 키우기, 문서 사이 관계 | 15개(원문 12, 일부 1, 코드 2) |
| `22-open-events-relations/time-identity.md` | 상대 시간 풀기, 같은 사건 판정, 문서 흐름 묶기 | 12개(원문 11, 초록 1) |
| `22-open-events-relations/practice.md` | 실무 레포·발표 영상·엔지니어링 글 | 14개(코드 7, 영상 3, 글·문서 4) |

새로 받은 저장소는 `lab/repos/`의 `heideltime`, `ETypeClus`, `epimine`, `llm-graph-builder`, `graphrag`, `itext2kg`다. 발표 영상 인용은 whisper 전사에서 왔고 공식 자막과 맞추지 못했다.

## 대조 기록

메인 세션이 직접 맞춘 것:

- 코드: `llm-graph-builder/backend/src/shared/constants.py:835`, `epimine/epimine.py:304`·`:315`(`claude-2.1`), `itext2kg/itext2kg/atom/graph_matching/matcher.py:144-153`, `itext2kg/README.md:119`, `graphrag/.../prompts/index/extract_claims.py:19`, `graphrag/.../config/defaults.py:132`(claim 기본 꺼짐). HeidelTime `resources/auto-korean`에서 "올해|작년|내년"은 0건, "어제"는 2개 파일에 있다.
- 논문 원문 텍스트: ORELLM 13.05(문자열 일치 기준선임을 본문에서 확인)·46.03, DIAL-KG 4.3절 후보 풀 문장, Afantenos "No new relations were proposed.", X-AMR 80% 상한 문장, SCATE 0.59·0.49·8,583, Nath 2024 GVC 53.5·84.3, EpiMine "without any LLM summarization", ConceptE 군집 수 = 미지 종류 수, LLM-TLS 같은 날짜 필터, CRAB Table 2(같은 문서 73.8·다른 문서 56.7, 열 이름 확인), Gautam 2024 Zephyr-7B 48.1·GPT-3.5 72.6.
- 웹 원문: 실무 갈래 에이전트가 Zalando 글 HTML과 LinkedIn 논문 PDF를 내려받아 텍스트로 바꿨다. 메인 세션이 그 텍스트에서 40%·10%·3B~12B·10~20% 문장과 28.6% 문장을 다시 찾았다. 이 과정에서 `practice.md`의 사람 검토 비율이 바로잡혔다. 10~20%는 결과 묶음의 비율이 아니라 각 묶음에서 뽑은 요약의 비율이다.
- 대조하지 않은 것: TextEE의 7~13B F1 수치, X-AMR의 GPT-4 15~25점 차이, lemma 휴리스틱의 76.4 → 81.7. 갈래 파일의 확인 상태를 따른다.

# 상대 시간은 작성일 기준 규칙이나 코드로 풀 수 있고, 같은 사건은 "참여자+행위+시간" 식별자에 작은 모델의 예/아니오 판정을 얹어 가린다 — 반복 사건의 "대상 기간"과 사내 회계 달력은 아무도 따로 풀지 않았다

조사 갈래: 시간 표현 풀기와, 여러 문서가 같은 사건을 말하는지 가리기. 조사일 2026-10-11.

DCT(document creation time)는 문서 작성일이다. 상대 시간 표현("작년", "이번")을 절대 날짜로 바꿀 때 기준점이 된다.

## 출처 한눈에

| 묶음 | 출처 | 종류 | 연도 | 확인 상태 |
|---|---|---|---|---|
| 시간 | HeidelTime (자동 다국어 확장) | 논문 + 레포 | 2015 | 원문 읽음, 코드 읽음 |
| 시간 | SUTime | 논문 | 2012 | 원문 읽음 |
| 시간 | Korean TimeML / Korean TimeBank | 논문(데이터) | 2016 | 원문 읽음 |
| 시간 | Discourse-Aware ICL for TE Normalization | 논문 | 2024 | 원문 읽음 |
| 시간 | SCATE 코드 생성 시간 정규화 | 논문(프리프린트) | 2025 | 원문 읽음 |
| 사건 | ECB+ | 논문(데이터) | 2014 | 원문 읽음 |
| 사건 | 2\*n is better than n² (lemma heuristic) | 논문 | 2023 | 원문 읽음 |
| 사건 | X-AMR 선형 사건 상호참조 | 논문 | 2024 | 원문 읽음 |
| 사건 | 생성 근거 지식 증류 (Okay, Let's Do This!) | 논문 | 2024 | 원문 읽음 |
| 흐름 | Multilingual Clustering of Streaming News | 논문 | 2018 | 원문 읽음 |
| 흐름 | SCStory | 논문 | 2023 | 초록만 (실험 표 1 추가 확인) |
| 흐름 | LLM-TLS (From Moments to Milestones) | 논문 | 2024 | 원문 읽음 |

## 시간 표현을 작성일 기준으로 풀기

TimeML은 시간 표현과 사건을 표시하는 마크업 언어다. 그 안의 TIMEX3 태그는 시간 표현마다 `type`(DATE, TIME, DURATION, SET)과 `value`(ISO 8601 꼴 값)를 붙인다. 아래 도구는 모두 TIMEX3 `value`를 만들거나, 그 한계를 넘으려 한다.

### HeidelTime

Strötgen & Gertz, "A Baseline Temporal Tagger for all Languages", EMNLP 2015. https://aclanthology.org/D15-1063/ · 코드 https://github.com/HeidelTime/heideltime (로컬: `lab/repos/heideltime`)

**푸는 것.** 규칙 기반 시간 태거를 사람 손 없이 200개 넘는 언어로 넓힌다.

**메커니즘.** HeidelTime은 언어별 자원(패턴 파일, 정규화 파일, 규칙 파일)과 코드를 떼어 둔다. 자동 확장은 영어 패턴을 Wiktionary 번역표로 옮기고, 언어와 무관한 규칙(어순을 여러 가지로 허용)을 붙인다.

문서 종류(news, narrative, colloquial, scientific)에 따라 기준 시점이 달라진다. 코드에서 news·colloquial·scientific은 DCT를 쓰고, narrative는 앞서 언급된 날짜를 쓴다(`src/de/unihd/dbs/uima/annotator/heideltime/HeidelTime.java:685`, `:705`의 `getLastMentionedX`).

**인용.**
- "For processing news-style documents, a publication date is additionally needed." (§2.1, p.542)
- "issues with morphology-rich languages and those without white-space tokenization have to be addressed." (§4.2, p.545)

**수치.** 영어 TempEval-3 TimeBank에서 손으로 만든 자원의 value F1은 79.6이고, 자동 자원은 54.7이다(Table 1). 자동 자원의 중국어 relaxed 추출 F1은 17.3이다. 논문은 한국어를 평가하지 않았다.

**옮길 때 걸리는 점.**
- 레포에 `resources/auto-korean`이 있다. `resources_repattern_reDateWord.txt`에는 "어제", "오늘", "내일"이 있지만, "올해", "작년", "내년"은 자동 한국어 자원 어디에도 없다(`grep -rn "올해|작년|내년"` 결과 없음).
- 자동 자원은 띄어쓰기 단위로 토큰을 자른다. [추정] "작년에", "올해의"처럼 조사가 붙은 낱말은 패턴과 바로 맞지 않는다(사례: 논문이 형태소가 많은 언어를 미해결로 적은 것 1개).
- 영어 정규화 파일은 "fiscal first quarter"를 그냥 `Q1`로 바꾼다(`resources/english/normalization/resources_normalization_normPartOfYear.txt`). 회계연도가 달력 연도와 다를 수 있다는 것을 반영하지 않는다.
- 규칙 파일 문법이 공개되어 있어서, 사내 표현("FY26", "상반기 결산")을 규칙으로 더할 수 있다. 다만 Java + UIMA 파이프라인이다.

### SUTime

Chang & Manning, "SUTime: A Library for Recognizing and Normalizing Time Expressions", LREC 2012. http://www.lrec-conf.org/proceedings/lrec2012/pdf/284_Paper.pdf

**푸는 것.** 영어 시간 표현을 찾고 TIMEX3 값으로 바꾼다.

**메커니즘.** SUTime은 토큰 위 정규식(TokensRegex)으로 숫자 → 단순 시간 → 복합 시간 순서로 패턴을 쌓는다. 찾은 표현마다 시간 객체를 만들고, 기준 날짜에 대해 휴리스틱 규칙으로 절대 시간으로 푼다. 규칙 파일을 더해 넓히도록 설계되었다.

**인용.**
- "SUTIME uses document dates as references." (§2, p.3735)
- "SUTIME resolves all temporal expressions to one reference date, the document date. In some cases, it may be more appropriate to resolve a particular temporal expression to a nearby date in the text instead." (한계 절)

**수치.** TempEval-2 영어 평가에서 추출 F1 0.92, value 정확도 0.82다(Table 1). 같은 표에서 HeidelTime1은 추출 F1 0.86, value 0.85다.

**옮길 때 걸리는 점.** SUTime은 영어만 다룬다. 기준 시점이 문서 날짜 하나로 고정이라, 본문에서 "2025년 결산을 보면 … 그해 4분기"처럼 앞 문장이 기준이 되는 경우를 못 푼다.

### Korean TimeML과 Korean TimeBank

Jeong et al., "Korean TimeML and Korean TimeBank", LREC 2016. https://aclanthology.org/L16-1055/

**푸는 것.** 한국어 시간·사건 표시 규약을 고치고, 그 규약으로 만든 말뭉치를 낸다. 정규화 도구는 이 논문에 없다.

**메커니즘.** 이전 KTimeML은 형태소 단위로 표시해서 형태소 분석기가 바뀌면 데이터를 다시 써야 했다. 개정판은 글자 위치로 표시한다. `timex3`에 `calendar` 속성(LUNAR 등)을 더하고, "초중반"·"중후반" 같은 막연한 시기를 `mod` 값으로 표시한다. 문서마다 DCT를 `date`로 저장한다.

**인용.** "the Korean dataset of TempEval-2 is small in size (e.g., totally 26 documents) and has many annotation errors." (§3, p.358)

**수치.** 문서 1,078개, `timex3` 2,552개, `event` 11,522개다(Table 1). `timex3` 일치도 Kappa는 0.9983이다(Table 2).

**옮길 때 걸리는 점.** 원천이 위키백과 문서와 손으로 만든 질문-답 쌍이다. 사내 보고서의 "이번 결산", "FY26" 같은 표현은 이 말뭉치에 거의 없을 것이다. [추정] 사내 표현 평가셋은 따로 만들어야 한다(사례: 말뭉치 도메인이 인물·음악·대학·역사 4개뿐인 것 1개). 데이터가 지금 어디서 배포되는지는 확인하지 않았다.

### LLM in-context learning 정규화

Gautam, Lange & Strötgen, "Discourse-Aware In-Context Learning for Temporal Expression Normalization", NAACL 2024. https://aclanthology.org/2024.naacl-short.27/

**푸는 것.** 학습 없이 LLM 프롬프트만으로 이미 찾은 시간 표현의 TIMEX3 `value`를 낸다.

**메커니즘.** 대상 문장과 비슷한 학습 문장을 임베딩(`multilingual-e5-base`)으로 골라 예시로 넣는다. 같은 문서에서 앞서 낸 정규화 값들을 "문맥 창"으로 함께 넣어서, 상대 표현이 DCT나 앞 날짜에 기댈 수 있게 한다. 창 길이는 3문장이 가장 좋았다. 추출은 별도 NER 모델이 한다.

**인용.**
- "Most challenging are relative and under-specified expressions, where the model lacks enough context or fails to incorporate context information." (§4.2 Error Analysis, p.310)
- "The GPT model also considerably outperforms the smaller open-source Zephyr model, which only achieves good performance on the simplest ECHR dataset." (§4.1, p.309)

**수치.** TempEval-3 정규화 정확도는 GPT-3.5 + 예시 + 문맥 창이 72.6이고, Zephyr-7B가 48.1이며, 학습한 MLM 모델이 79.0이다(Table 1). TempEval-3 오류 표에서 상대 표현은 23개 맞고 8개 틀렸다(Table 3).

**옮길 때 걸리는 점.** 7B 모델은 예시가 적으면 JSON을 깨뜨리고, 예시가 많으면 입력 길이를 넘겼다(§4.2). 평가 언어 7개에 한국어는 없다. 이 논문은 7B 모델이 상대 표현 정규화에 약하다는 근거다.

### SCATE 코드 생성 정규화

Su, Yu, Howard & Bethard, "A Semantic Parsing Framework for End-to-End Time Normalization", arXiv 2507.06450, 2025 (프리프린트, 심사 중). https://arxiv.org/abs/2507.06450

**푸는 것.** 시간 표현을 값 대신 실행되는 연산 코드로 바꿔서, TIMEX3가 못 담는 표현까지 계산한다.

**메커니즘.** SCATE는 `This`, `Last`, `Next`, `Before`, `Intersection` 같은 시간 연산자로 표현을 조립하는 틀이다. 저자들은 SCATE를 Python 라이브러리로 구현했다. 모델은 `Last(interval=DCT, shift=...)` 같은 코드를 내고, 라이브러리가 날짜 구간을 결정론적으로 계산한다.

큰 LLM(Claude 3.7)이 뉴스 문장에 코드를 달고, 실행해서 깨지는 코드를 걸러 8,583개 학습 예를 만든다. 이 데이터로 Qwen2.5-0.5B를 미세조정한다.

**인용.**
- "small, locally deployable models trained on this augmented data can achieve strong performance, outperforming even their LLM parents" (Abstract)
- ISO-TimeML이 못 다루는 것으로 "Event-relative expressions, such as “three weeks postoperative”"를 든다 (§1, p.1).
- 프롬프트 부록: "The fiscal year may differ from the calendar year depending on the company" (부록 프롬프트, p.26)

**수치.** 테스트 정확도는 Qwen2.5-0.5B(증강 + 원래 학습셋)가 0.59, Claude 3.7 SCATE 프롬프트가 0.49, Claude 3.7이 날짜를 바로 내는 프롬프트가 0.38이다(Table 2). Qwen2.5-0.5B를 원래 학습셋으로만 학습하면 0.01이다. 0.5B 모델 오류 20개 중 70%가 표현을 놓친 경우다.

**옮길 때 걸리는 점.**
- 계산을 코드가 하므로, 사내 회계 달력은 라이브러리 쪽 설정으로 둘 수 있다. [추정] 모델은 "올해 → `This(DCT, YEAR)`"만 고르면 된다(사례: 코드 생성이 직접 날짜 생성보다 11점 높았던 것 1개).
- 작은 모델 학습에 큰 LLM이 만든 데이터 8천여 개가 들었다. 로컬 작은 모델만 쓰는 조건이면 이 증강 단계를 다르게 풀어야 한다.
- 영어 뉴스만 평가했다. 프리프린트라 수치가 바뀔 수 있다.

## 사건 종류를 정하지 않고 같은 사건 가리기

cross-document event coreference는 여러 문서의 사건 언급이 같은 실제 사건을 가리키는지 묶는 일이다. 여기 출처들은 사건 종류 목록 없이, 언급마다 트리거 낱말과 주변 정보로 판정한다.

### ECB+

Cybulska & Vossen, "Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution", LREC 2014. http://www.lrec-conf.org/proceedings/lrec2014/pdf/840_Paper.pdf

**푸는 것.** 같은 종류의 다른 사건 인스턴스를 섞어 넣어서, 사건 상호참조 평가를 현실에 가깝게 만든다.

**메커니즘.** 저자들은 사건을 행위(action), 시간(time), 장소(location), 참여자(participant) 네 성분으로 본다. 원래 ECB는 주제마다 사건 인스턴스가 대개 하나라서, 낱말만 맞춰도 점수가 높았다. ECB+는 주제마다 같은 종류의 다른 인스턴스 기사를 더한다. 예로 1번 주제에는 Tara Reid의 2008년 재활원 입소와 Lindsay Lohan의 2013년 재활원 입소가 함께 들어 있다(Table 3).

**인용.**
- "a system will also have to make a distinction between mentions of different instances of an event type." (§3.3, p.4547)
- "By that the event coreference task becomes simplified to topic classification." (§3.2, p.4547)

**수치.** 기사 502개를 더해 43개 주제를 넓혔다. 원래 ECB에서 낱말 일치만으로 CoNLL F1 52.52(주제 경계 무시), 64.76(주제 안)이 나왔다(Table 2).

**옮길 때 걸리는 점.** 우리 문제("2025 결산" 대 "2026 결산")가 바로 ECB+가 만든 "같은 종류, 다른 인스턴스" 상황이다. 이 구분에서 시간과 참여자가 행위 낱말보다 결정적이라는 것이 이 논문의 가설이다.

### 낱말 일치 휴리스틱 + 쌍 판정기

Ahmed, Nath, Martin & Krishnaswamy, "2\*n is better than n²: Decomposing Event Coreference Resolution into Two Tractable Problems", Findings of ACL 2023. https://aclanthology.org/2023.findings-acl.100/ · 코드 https://github.com/ahmeshaf/lemma_ce_coref

**푸는 것.** 모든 쌍을 비교하는 비용을 줄이면서 상호참조 성능을 지킨다.

**메커니즘.** 1단계는 트리거 원형(lemma)이 같거나, 학습 데이터에서 모은 동의 원형 쌍에 들거나, 문장 원형이 겹치는 쌍만 남긴다. 2단계는 남은 쌍을 RoBERTa나 Longformer cross-encoder로 판정한다. 1단계가 거른 쌍 분포가 균형이 맞아서 판정기 학습도 쉬워진다.

**인용.** "Most mention pairs are not coreferent, yet many that are coreferent can be identified through simple techniques such as lemma matching of the event triggers or the sentences in which they appear." (Abstract)

**수치.** ECB+ CoNLL F1은 휴리스틱만 76.4, 휴리스틱 + Longformer 81.7, 정답 동의쌍 휴리스틱 + Longformer 87.4다(Table 2). GVC(총기 사건 말뭉치)에서는 휴리스틱만 51.8, + Longformer 75.0이다. RoBERTa 예측은 1~2분 걸렸다(§6).

**옮길 때 걸리는 점.** 원형 추출에 spaCy를 쓴다. 한국어는 형태소 분석기가 이 자리를 맡아야 한다. 동의 원형 쌍은 정답 데이터에서 모은다. 사내 용어 불일치("결산", "마감", "클로징")는 바로 이 동의쌍 문제다. GVC처럼 같은 종류 사건이 많은 말뭉치에서 휴리스틱만으로는 51.8에 그친다.

### X-AMR 사건 식별자

Ahmed et al., "Linear Cross-document Event Coreference Resolution with X-AMR", LREC-COLING 2024. https://aclanthology.org/2024.lrec-main.920/ · 코드 https://github.com/ahmeshaf/gpt_coref

**푸는 것.** 사건마다 비교 가능한 식별자를 만들어, 쌍 비교 없이 선형 시간에 상호참조를 푼다.

**메커니즘.** 사건 언급마다 PropBank 술어 의미(roleset), 행위자(ARG-0), 대상(ARG-1), 장소(ARG-Loc), 시간(ARG-Time)을 채운다. 식별자 `EID`는 술어 + ARG-0 + ARG-1이고, `EIDlt`는 ARG-0 + 술어 + 장소 + 시간이다. 같은 식별자끼리 바구니에 담아 묶는다. 동의 술어는 VerbNet 부류로, 참여자 이름은 위키백과 링크로 맞춘다. GPT-4가 이 슬롯을 채우는 실험도 한다.

**인용.**
- "A CoNLL F1 of 80% seems to be an upper bound for a purely symbolic approach for ECR." (§5, p.10522)
- "the machine-created annotations G1 and G2 suffered heavily from their inability to access external resources to resolve relative times, locations, and references to entities, in addition to inconsistent annotations" (§8.2, p.10524)

**수치.** 사람 주석으로 `EIDlt`를 쓰면 ECB+ dev CoNLL F1 79.8이다(Table 2). 작은 dev에서 사람 주석 최고는 83.6이고, GPT-4 주석은 25점(G1)과 15점(G2) 모자랐다(§7). GPT-4 실행 비용은 4달러와 6달러였다.

**옮길 때 걸리는 점.** 사용자 안("사건 종류 + 기간" 키)이 이 `EIDlt`와 같은 모양이다. 이 논문은 그런 키만으로 약 80이 상한이라고 본다. GPT-4가 실패한 원인 두 가지(상대 시간을 못 풂, 같은 대상을 다른 이름으로 씀)는 LLM 밖에서 풀어야 한다는 신호다. 논문은 ECB+ 정답이 Jim O'Brien의 두 해고를 한 사건으로 잘못 묶은 사례도 적었다(§8.2).

### LLM 근거 생성 + 작은 모델 증류

Nath, Manafi, Chelle & Krishnaswamy, "Okay, Let's Do This! Modeling Event Coreference with Generated Rationales and Knowledge Distillation", NAACL 2024. https://aclanthology.org/2024.naacl-long.218/ · 코드 https://github.com/csu-signal/llama_cdcr

**푸는 것.** LLM이 쓴 판정 근거를 작은 인코더에 옮겨서, 추론 때 LLM 없이 상호참조를 판정한다.

**메커니즘.** 교사 LLaMA 2-7B-Chat이 사건 쌍마다 참여자·시간·장소를 따지는 근거 글을 쓴다. 학생 Longformer-base는 근거와 사건 쌍을 같은 공간에 맞추는 군집 학습을 하고, 교사 분포를 부드러운 정답으로 삼아 증류한다. 후보 쌍은 위의 낱말 일치 휴리스틱으로 고른다.

**인용.**
- "we prompt the language model to ground its rationale to event coreference-specific arguments such as participants, times, entities, and locations." (§3, p.3934)
- "Rationales provide an additional soft supervisory signal through which we train the student model … but are not required at inference" (§1, p.3932)

**수치.** B3 F1은 학생 모델이 ECB+ 86.8, GVC 84.3, AIDA Phase 1 64.5다(Table 2). 같은 표에서 LLaMA 2-7B-Chat 제로샷은 77.7, 53.5, 47.8이고, GPT-3.5-Turbo 제로샷은 79.8, 49.6, 56.0이다.

**옮길 때 걸리는 점.** 7B 제로샷 예/아니오 판정은 같은 종류 사건이 많은 GVC에서 53.5에 그친다. 근거 생성 프롬프트는 정답 라벨을 함께 받는다(Figure 2 설명 "FTR generation conditioned on the gold label", p.3934). 그래서 정답 쌍이 어느 정도 있어야 이 방식을 쓸 수 있다.

## 문서 흐름에서 사건 묶기

여기 출처들은 문서가 하나씩 들어올 때마다 기존 묶음에 붙이거나 새 묶음을 연다. 묶음 수를 미리 정하지 않는다.

### 다국어 뉴스 흐름 군집화

Miranda, Znotiņš, Cohen & Barzdins, "Multilingual Clustering of Streaming News", EMNLP 2018. https://aclanthology.org/D18-1483/

**푸는 것.** 끝없이 들어오는 다국어 뉴스를 스토리 묶음으로 실시간 나눈다.

**메커니즘.** 문서는 낱말·원형·개체명 TF-IDF 벡터로 표현된다. 새 문서와 각 묶음 중심의 유사도가 문턱 τ를 넘으면 붙이고, 아니면 새 묶음을 연다. 유사도에는 문서 시각과 묶음의 최신·평균·최초 시각 차이를 가우스 함수로 바꾼 세 특징이 더해진다. 가중치는 순위 학습으로 정한다.

**인용.** "time is a valuable indicator that a news story has changed, even if a cluster representation has a reasonable match in the textual features with the incoming document." (§4.1, p.4539)

**수치.** 시각 특징을 더하면 F1이 영어 92.7 → 94.1, 독일어 90.7 → 97.1, 스페인어 88.8 → 94.2로 오른다(Table 2).

**옮길 때 걸리는 점.** 여기 시각은 기사 발행 시각이다. 사내 보고서는 발행 시각과 사건 시각이 벌어진다. "작년 결산"(2026-02 작성)은 작성 시각으로 묶으면 2026년 결산 쪽에 붙는다. 그래서 발행 시각 대신 정규화한 사건 시간을 이 특징 자리에 넣어야 한다.

### SCStory

Yoon, Meng, Lee & Han, "SCStory: Self-supervised and Continual Online Story Discovery", WWW 2023. https://arxiv.org/abs/2312.03725

**푸는 것.** 라벨 없이 뉴스 흐름에서 스토리를 찾고, 스토리가 변해도 표현을 따라 고친다.

**메커니즘.** Sentence-BERT 문장 임베딩 위에 가벼운 기사 인코더를 둔다. 슬라이딩 창(예: 7일 창을 하루씩 민다)마다 확신 높은 기사-스토리 배정을 가짜 라벨로 삼아 대조 학습으로 인코더를 갱신한다. 어느 스토리와도 확신이 문턱을 넘지 않으면 새 스토리를 연다.

**인용.** 기존 방식은 "the generic article embeddings do not effectively reflect the story-indicative semantics in an article and cannot adapt to the rapidly evolving news article streams." (Abstract)

**수치.** News14에서 B3-F1 0.872로, 가장 좋은 기존 방식(BatClus+SBERT) 0.764보다 높다(Table 1).

**옮길 때 걸리는 점.** 스토리는 사건보다 굵은 단위다. 해마다 돌아오는 결산은 창 밖으로 밀려서 다른 스토리가 될 것이다. [추정] 그 구분은 시간 창 덕분이지 사건 동일성 판정 덕분이 아니다(사례: 이 방식에 사건 시간 슬롯이 없는 것 1개). 원문은 초록과 표만 봤다.

### LLM-TLS

Hu, Moon & Ng, "From Moments to Milestones: Incremental Timeline Summarization Leveraging Large Language Models", ACL 2024. https://aclanthology.org/2024.acl-long.390/ · 코드 https://github.com/nusnlp/LLM-TLS

**푸는 것.** 기사 흐름에서 사건을 하나씩 묶어 타임라인을 만든다.

**메커니즘.** LLM(Llama2-13B)이 기사마다 "2002-07-17: Apple CEO Steve Jobs announces the iPod …" 꼴로 날짜 + 한 문장 사건 요약을 쓴다. GTE 임베딩으로 비슷한 요약 N개를 찾고, 날짜가 같은 후보만 남긴다.

LLM이 몇 개 예시를 보고 "같은 사건인가"에 예/아니오로 답하고, 예면 간선을 잇는다. 간선으로 이어진 묶음이 사건 하나다. 날짜 태깅에는 HeidelTime을 함께 쓴다(hybrid 입력).

**인용.**
- "we propose using LLMs as pseudo-oracles to resolve queries such as “Do events i and j refer to the same event?”" (§1, p.7233)
- "we also apply a date heuristic that filters candidates to ensure they share the same date with the query event." (§4.2.2, p.7236)

**수치.** 트윗 흐름 사건 묶기에서 검색 모드가 정밀도 89.63, F1 81.94를 7분에 냈다. 전체 비교 모드는 F1 82.54에 35분이 걸렸다(Table 3). 트윗 쪽 판정 LLM은 CrisisLTLSum으로 미세조정했고, 기사 쪽은 few-shot 프롬프트만 썼다.

**옮길 때 걸리는 점.** 한 호출이 짧은 두 요약의 예/아니오라서, 작은 모델에 맞는 크기다. 다만 이 논문은 13B를 썼고 8B 이하는 시험하지 않았다. "같은 날짜" 필터는 사건 날짜가 정확해야 작동한다. 그래서 앞 절의 시간 정규화가 이 필터의 입력이 된다.

## 우리 문제에 주는 것

### 가장 쓸 만한 셋

1. **X-AMR식 식별자 + 바구니 묶기.** 사용자 안의 "사건 종류 + 기간" 키가 `EIDlt`(행위자 + 술어 + 장소 + 시간)와 같은 모양이다. 이 논문은 그 키에 참여자를 넣고, 술어 동의어는 VerbNet으로, 이름은 위키백과 링크로 맞춘다. GPT-4조차 상대 시간과 이름 일관성에서 무너졌으므로, 이 둘은 모델 밖(규칙·사전)에서 채우는 것이 맞다. 키만으로 약 80이 상한이라는 수치는, 키가 빗나간 쌍을 판정할 2단계가 필요하다는 뜻이다.
2. **SCATE식 "연산자만 고르고 계산은 코드".** "올해", "작년", "이번", "FY26"을 작은 모델이 `This(DCT, YEAR)` 같은 연산자로 바꾸고, 사내 회계 달력을 아는 코드가 실제 기간을 낸다. 7B 모델이 TIMEX3 값을 바로 내면 48.1에 그쳤다(Gautam 2024). 반면 코드 생성은 0.5B로도 큰 LLM을 넘었다. [추정] 사내 표현은 종류가 적어서 연산자 몇 개와 규칙으로 덮인다(사례: 사용자 예시 4개가 `This`/`Last` 두 연산자로 모두 표현되는 것 1개).
3. **LLM-TLS식 "정규화 요약 → 검색 → 날짜 필터 → 예/아니오".** 사건 종류를 미리 몰라도 된다. 작은 모델이 맡는 일은 짧은 요약 하나와 예/아니오 판정 하나뿐이다. 정답 쌍이 쌓이면 Nath 2024처럼 작은 인코더로 판정기를 증류할 수 있다. 그쪽 근거는 7B 제로샷(GVC 53.5)보다 증류한 Longformer(84.3)가 크게 높았다는 것이다.

### 아무도 안 푼 것

- **반복 사건의 "대상 기간"과 "발생 시점".** "이번 결산"(2027-01 작성)은 2027년에 하는 일이지만 대상은 2026 회계연도다. 이번에 읽은 12개 출처는 사건에 시간 슬롯을 하나만 둔다(ECB+ time slot, X-AMR ARG-Time, LLM-TLS 날짜). 사건이 다루는 기간을 발생 시점과 따로 두는 표현은 보지 못했다. SCATE의 "사건 기준 상대 표현"은 사건을 기준으로 시간을 재는 것이라 이 문제와 다르다.
- **회사별 회계 달력.** HeidelTime은 "fiscal"을 버리고 달력 분기로 바꾼다. SCATE는 프롬프트에 회계연도가 다를 수 있다고만 적는다. 회계연도 시작 월을 설정값으로 받는 도구는 보지 못했다.
- **한국어.** HeidelTime 자동 한국어 자원에 "올해", "작년"이 없다. 두 LLM 정규화 논문은 한국어를 평가하지 않았다. 한국어 사건 상호참조 데이터셋은 이번 조사에서 찾아보지 않았다.
- **작성 시각과 사건 시각의 차이.** 흐름 군집화 논문들은 발행 시각을 쓴다. 사내 보고서처럼 지난 일을 나중에 쓰는 문서에서 이 신호가 얼마나 틀어지는지 잰 출처는 없었다.

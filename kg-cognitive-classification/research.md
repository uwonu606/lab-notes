# 언어 인지과학 관점의 KG 분류 — 연구와 방법론 조사

- 조사 날짜: 2026-10-18
- 물음: 언어 인지과학 관점에서 지식 그래프(knowledge graph, KG)를 어떻게 나눌 수 있나. 그 분류는 어떤 근거로 세우고 어떻게 검증하나.
- 다루는 갈래: 열한 개다. 범주화 이론, 어휘 의미 자원, 인지 지향 상위 온톨로지, 용어학, 상식·사건 지식, 공학 쪽 KG 유형론, 분류 방법론, 한국어 어휘·용어 자원, 통신 도메인 표준 어휘, 질문 유형론, 의미 기억 모델.
- 이전 조사와의 관계: `concept-extraction-papers/research.md` 는 문장에서 개념을 *뽑는* 계보를 다뤘다. 이번 조사는 뽑힌 개념·관계를 *어떤 기준으로 나누고 묶을지*를 다룬다. Probase typicality, ConceptNet, AbstractATOMIC, TaxoGlimpse, LLMs4OL 은 그 노트에 이미 있어서 여기서는 분류 근거로 쓰인 부분만 적는다.

## 읽는 법

갈래마다 조사 에이전트 하나가 원문을 열었고, 다른 에이전트가 같은 원문으로 주장을 다시 대조했다. 대조에서 틀린 것으로 판정된 주장은 이 문서에 쓰지 않았다. 고쳐야 한다고 판정된 주장은 고친 대로 썼다. 원문으로 확인할 수 없다고 판정된 주장은 본문에 쓰지 않고 #확인하지 못한 것 으로 보냈다.

근거는 문장 안에 출처(논문, 절, 쪽)로 적는다. 원문 없이 사례에서 끌어낸 판단에만 `[추정]` 을 앞에 달고, 사례와 개수를 문장 끝 괄호에 붙인다.

큰따옴표 안은 원문 그대로다. 그 밖은 요약이다. 작은따옴표는 예시 낱말이나 작성자의 풀이를 감싼다.

### 약칭

한 장 결론과 갈래 지도에 먼저 나오는 약칭을 여기서 푼다. 나머지는 처음 나오는 절에서 푼다.

| 약칭 | 뜻 |
|---|---|
| DL | description logic. 개념과 관계를 형식 논리로 적는 지식 표현 언어 계열 |
| CQ | competency question. 온톨로지가 답해야 할 질문으로 적은 요구 |
| PDTB | Penn Discourse Treebank. 문장 사이 담화 관계를 주석한 영어 코퍼스 |
| QUEST | Graesser 의 질문 응답 인지 모형. arc 는 이 모형의 지식 그래프 간선이다 |
| SWOW | Small World of Words. 대규모 단어 연상 규범 |
| CSKG | CommonSense Knowledge Graph. 상식 자원 7개를 합친 KG |
| ORKG | Open Research Knowledge Graph. 학술 논문 내용을 담는 KG |
| DUL | DOLCE+DnS Ultralite. DOLCE 의 OWL 경량판 |
| SKOS, TBX | 시소러스를 웹에 게시하는 W3C 표준, 용어 데이터를 주고받는 ISO 표준 |
| X.733, 3GPP | ITU-T 의 alarm 보고 표준, 이동통신 표준화 단체 |
| TTA | 한국정보통신기술협회 |
| KGQA | KG 위에서 자연어 질문에 답하는 과제 |
| RCA | root cause analysis. 장애의 근본 원인을 찾는 일 |
| RAG | retrieval-augmented generation. 검색한 문서를 LLM 입력에 붙여 답하게 하는 방식 |

### 예문

갈래마다 같은 예문을 그 갈래의 분류로 나눠 본다.

> 5G NR 단말이 SKT 기지국 핸드오버 중 RRC 재설정 실패로 호가 끊겼다.

각 절의 '예문 분해'는 작성자가 그 갈래의 칸 정의에 맞춰 손으로 만든 예시다. 실제 시스템을 돌린 결과가 아니다.

## 한 장 결론

인지 관점의 KG 분류는 세 축으로 정리된다. 갈래마다 세 축 위의 다른 칸을 차지한다.

| 축 | 칸 | 대표 이론·자원 |
|---|---|---|
| A. 무엇을 나누나 | 개념(노드 범주) | WordNet unique beginner, DOLCE·BFO 최상위 범주, 세종 의미 부류 |
| | 관계 | Winston 부분-전체 6유형, FrameNet frame 관계, PDTB 담화 관계, QUEST arc, Mirman 의 taxonomic·thematic |
| | 지식 유형 | ATOMIC 의 사실 대 추론, Tulving·Ortony 의 episodic·semantic, Soar·CoALA 의 semantic·episodic·procedural 기억 |
| | 맥락 | Hogan 의 context, Cyc microtheory 의 12 차원, Barsalou 의 ad hoc 범주 |
| | 이름(표기) | ISO 25964 의 개념·용어 분리, OntoLex 의 변이 관계, TBX 의 termSec |
| B. 범주 구조의 모양 | 엄격한 계층 | 고전적 범주, Collins & Quillian 상속 계층, OntoClean, BFO 의 monohierarchy, Z39.19 계층 3유형 |
| | 정도 있는 소속 | Rosch prototype, Smith·Shoben·Rips 특징 모형, Probase typicality, fuzzy DL, typicality DL |
| | 맥락 의존 | Barsalou ad hoc 범주, Fillmore frame, Cyc microtheory, Cabré 의 용어 이론 |
| C. 분류 근거 | 실험 | Rosch 1975·1976, Medin, Collins & Quillian 1969, Rips 외 1973, SWOW, GLUCOSE 파일럿, QUEST 답 생성 실험 |
| | 언어 자료 | WordNet 시험 문장 틀, FrameNet corpus, 세종 적정 술어, PDTB |
| | 철학 논증 | DOLCE, BFO, OntoClean, Murphy & Medin 1985 |
| | 공학 편의 | Hogan 2021, Pan 2024, X.733, 3GPP, CSKG |

축 B 에서 정답 하나를 주는 이론은 없다. 고전적 계층은 형식 검사가 쉽고, prototype 은 사람 판단과 맞으며, 맥락 의존 범주는 질문이 그때그때 만드는 묶음을 설명한다. [추정] 그래서 갈래 전체가 가리키는 구성은 엄격한 계층 위에 정도와 맥락을 *따로 층으로* 얹는 것이다(사례: Probase 가 크리스프 isA 위에 typicality 를 얹은 것, NORIA-O 가 SKOS 계층 위에 관점별 scheme 을 둔 것, EcoLexicon 이 계층 관계 위에 명제 단위 문맥 제약을 건 것, 3건).

축 C 에서 실험 근거가 있는 것은 인지심리학 쪽 갈래(범주화 이론, 분류 방법론, 질문 유형론, 의미 기억 모델)뿐이다. KG 쪽 분류(공학 쪽 KG 유형론, 통신 도메인 표준)는 대부분 공학 편의에 서 있고, 인지 이름을 단 KG(ORKG 의 cognitive KG)도 인지과학 근거를 대지 않는다(Rabby et al. 2024 §3.1).

이 조사가 찾은 가장 직접적인 다리는 질문 쪽이다. Lehnert(1977)와 Graesser 의 QUEST(1992)는 질문 범주를 처음부터 그래프 위의 경로 모양으로 정의했다(#10 질문 유형론). 질문 범주가 따라갈 관계 유형과 방향을 정한다는 뜻이다(QUEST p.742–743).

검색 과정 쪽 다리는 활성 확산이다. 연상망 위 감쇠 random walk 는 사람 유사도·관련도 판단을 견준 세 척도 가운데 늘 가장 낫거나 같게 예측했고(De Deyne 외 2019 원고 p.18), 같은 원리를 KG 기반 RAG 검색에 쓴 구현이 있다(Pavlovic 외 2025, #11 의미 기억 모델).

## 갈래 지도

| # | 갈래 | 무엇을 분류하나 | 대표 문헌 | 근거 종류 | KG 에 쓰인 곳 |
|---|---|---|---|---|---|
| 1 | 범주화 이론 | 범주 소속의 정도, 계층의 특권 수준, 범주가 응집하는 까닭 | Rosch & Mervis 1975, Rosch et al. 1976, Barsalou 1983, Murphy & Medin 1985 | 실험, 철학 논증 | Probase typicality, Wang 2015 basic level, Hollink 2019 |
| 2 | 어휘 의미 자원 | 낱말 뜻의 단위와 그 사이 관계 | WordNet, FrameNet, VerbNet, PropBank, Generative Lexicon, OntoLex-Lemon | 언어 자료, 이론 논증 | BabelNet, Framester, Predicate Matrix |
| 3 | 인지 지향 상위 온톨로지 | 최상위 범주와 기본 관계, is-a 검사 | DOLCE, BFO, OntoClean, UFO, Gärdenfors | 철학 논증, 언어 자료 | DUL, OBO Foundry, Wikidata 진단 |
| 4 | 용어학 | 개념과 이름의 분리, 용어 관계, 변이 | ISO 1087·704, Z39.19, ISO 25964, SKOS, TBX, Temmerman, Faber | 표준 합의, 언어 자료 | 시소러스 게시, EcoLexicon |
| 5 | 상식·사건 지식 | 관계의 지식 유형, 개체 대 사건, 사건 사이 관계 | Ilievski 2021, ATOMIC 2020, GLUCOSE, ASER, PDTB, Cyc | 언어 자료, 공학 편의, 일부 실험 | CSKG, COMET, EventKG |
| 6 | 공학 쪽 KG 유형론 | KG 의 층, 담긴 정보, 기억 체계 | Hogan 2021, Pan 2024, Soar, CoALA, Zep | 공학 편의 | 에이전트 기억 KG |
| 7 | 분류 방법론 | 분류를 세우고 검증하는 절차 | Grüninger CQ, METHONTOLOGY, NeOn, OntoClean, Artstein & Poesio, McRae, SWOW | 실험, 공학 편의 | 온톨로지 공학 일반 |
| 8 | 한국어 자원 | 한국어 의미 부류, 사전 관계, 전문용어 표준화 | KorLex, 세종 의미 부류, 표준국어대사전, 우리말샘, 국어기본법, TTA | 언어 자료, 규범 | 세종-KorLex 매핑 |
| 9 | 통신 도메인 표준 | 용어 지위, 장애 속성, 관리 대상, 시험 판정 | 3GPP TR 21.905·21.801, X.733, RFC 8632·9940, ETSI EG 202 237 | 공학 편의 | NORIA-O, Tele-KG, TN-AutoRCA |
| 10 | 질문 유형론 | 질문 범주와 그래프 경로의 대응 | Lehnert 1977, Graesser & Person 1994, QUEST, Bolotova 2022, PolyG | 실험, 공학 구현 | KGQA 벤치마크 |
| 11 | 의미 기억 모델 | 기억 체계, 개념 사이 관계 종류, 검색 과정 | Tulving 1972, Collins & Quillian 1969, Collins & Loftus 1975, Smith 외 1974, Mirman 2017, SWOW 2019 | 실험, 개념 논증 | CoALA 기억 구분, 활성 확산 RAG(Pavlovic 2025), HippoRAG |

## 1. 범주화 이론

is-a 를 몇 개의 값으로 보느냐를 나누는 갈래다.

### 분류의 칸

| 이론 | 칸 (원문 이름) | 한 줄 정의 |
|---|---|---|
| 고전적 범주 | criterial features | 필요충분조건으로 소속을 정한다 |
| Rosch & Mervis 1975 | prototype, family resemblance, cue validity | 소속에 정도가 있고, 모든 멤버가 공유하는 속성이 없을 수 있다 |
| Rosch et al. 1976 | superordinate, basic level, subordinate | 계층의 세 수준 가운데 basic level 이 정보를 가장 많이 준다 |
| Medin & Schaffer 1978 | exemplar | 범주 요약이 아니라 저장된 사례와의 유사도로 분류한다 |
| Barsalou 1983 | common categories, ad hoc categories | 목표가 그때 만드는 범주도 정도 구조를 갖지만 기억에 고정되지 않는다 |
| Murphy & Medin 1985 | similarity-based, theory-based | 범주는 유사도가 아니라 인과·설명 지식에 맞아서 응집한다 |
| Straccia 2001 (fuzzy DL) | fuzzy concept, fuzzy assertion | 소속을 [0,1] 진리값으로 둔다 |
| Lieto & Pozzato 2020 (typicality DL) | strict inclusion, typicality inclusion | '전형적인 C 는 D' 를 예외를 허용하는 포함으로 적는다 |

prototype 은 범주의 가장 좋은 예다. basic level 은 사람이 사물을 가장 먼저 부르는 수준(가구가 아니라 의자)이다. cue validity 는 한 속성이 그 범주를 얼마나 잘 가리키는지의 확률이다.

### 근거

- Rosch & Mervis 1975 는 6개 상위 범주 멤버의 속성을 피험자에게 나열시켜 family resemblance 점수를 냈다. 이 점수와 prototypicality 평정의 Spearman 상관은 basic measure 로 furniture 0.88, vehicle 0.92 이고, logarithmic measure 로 0.84, 0.90 이다(p.581–582).
- 원문은 family resemblance 를 "a descriptive, not a processing principle" 이라고 한정한다(p.600).
- Rosch et al. 1976 의 근거는 Part I 실험 4개가 수렴 조작 정의로 basic level 을 정하고, Part II 실험 8개가 그 함의를 탐색한 것이다(Abstract). 생물 분류에서는 예상보다 한 단계 위(tree, fish)가 basic 으로 나왔다(p.392–393).
- 전문가일수록 basic level 이 아래로 내려간다는 주장은 Rosch 1976 에서 비행기 정비사 1명을 informant 로 쓴 관찰에 기댄다(p.430). 실험 근거는 Tanaka & Taylor 1991 이 표준 출처지만 이번에 열지 않았다.
- Medin, Wattenmaker & Hampson 1987 은 사람이 범주를 직접 만들면 대개 한 차원으로만 나눈다고 보고했다. 속성끼리 상관되고 인과로 이어질 수 있으면 한 차원 분류를 버렸고, 속성 사이 관계를 드러내는 개념 지식을 더하면 family resemblance 정렬이 "fairly common" 해진다(Abstract).
- Murphy & Medin 1985 는 새 실험 없이 논증으로 선다. Table 1(p.298)은 개념 사이 구조를 similarity 쪽은 공유 속성 계층으로, theory 쪽은 인과·설명 링크의 네트워크로 대비한다.

### KG 적용

- Probase(Wu et al. 2012 §4.2)는 isA 간선마다 두 방향 typicality 를 단다. 개념이 주어졌을 때 인스턴스의 확률과, 인스턴스가 주어졌을 때 개념의 확률이다. 사람 평정과 비교하지는 않았다.
- Wang et al. 2015(CIKM)는 두 확률의 곱 Rep(e,c) 로 basic-level 개념을 고른다. Bing 질의에서 만든 1,683쌍을 쌍마다 3명이 4단계(Excellent/Good/Fair/Bad)로 라벨했다(§4).
- Hollink et al. 2019 는 WordNet synset 518개를 저자 2명이 basic / not basic 으로 라벨했고(κ 0.73), Random Forest 로 분류했다. 새 도메인에는 도메인별 정규화가 있어야 의미가 있다고 적는다(§7).
- Misra et al. 2021 은 LM 확률과 Rosch(1975, JEP: General)의 10개 범주 typicality norms 의 상관을 "positive but modest" 로 보고했다(ρ 0.24–0.41).
- Pedrotti et al. 2025 는 LLM 이 basic level 귀납은 잘하지만 superordinate 로 올리는 일은 약하다고 보고했다(§6).
- Sawyer et al. 2025 는 VLM(이미지와 글을 함께 다루는 언어 모델)에 전문가 프롬프트를 주면 basic level 사용이 3–6%p 줄었다고 보고했다. 저자는 이를 사람의 전문가 basic level 이동과 맞는다고 읽는다. 같은 조건에서 VQA(이미지에 대한 질문 응답) 정확도는 떨어졌다(Table 6: 56.90% 대 42.76%·45.91%).

### 한계

- fuzzy DL 은 fuzzy ALC 의 첫 제안이 아니다. Straccia 2001 이 스스로 Yen 1991 을 처음으로, Tresp & Molitor 1998 을 ALC 확장으로 든다. JAIR 2001 판은 의미론과 계산법을 정리한 저널판이다.
- fuzzy 정도(경계 모호성)와 typicality(대표성)를 다른 칸에 두자는 주장은 논쟁 중인 입장이다. Osherson & Smith 1997, Kamp & Partee 1995 는 둘을 나누고, Hampton 2007 은 prototype 유사도 하나에 문턱을 둔 Threshold Model 로 둘을 함께 설명한다(Hampton 2007 초록).
- Lieto & Pozzato 는 pet fish 같은 결합 사례를 fuzzy logic 으로 모델링하기 어렵다고 앞선 연구를 인용해 적는다(§4 도입). 추론 복잡도는 ExpTime 이다.

### 예문 분해

- 범주 '통화 장애'의 멤버로 '호 끊김'이 놓인다. 부서의 basic level 은 일반인의 '통화 끊김'보다 아래인 'RRC 재설정 실패'일 수 있다.
- 'SKT' 는 '통신사'의 전형적 멤버(높은 typicality)로, MVNO 는 주변 멤버로 둔다.
- '핸드오버 중 끊긴 호'는 질문이 그때 만든 ad hoc 범주다. 용어집 계층에는 넣지 않는다.
- theory-based 관점에서는 'RRC 재설정 실패 → 호 끊김'이라는 인과 링크가 이 문장을 '핸드오버 장애' 범주에 묶는 근거다.

## 2. 어휘 의미 자원

낱말 뜻의 단위와 관계 목록이 자원마다 다르다.

### 분류의 칸

| 자원 | 단위 | 관계의 칸 |
|---|---|---|
| WordNet (Miller 외 1990) | synset | 명사 is-a(25개 unique beginner), 동사 entailment·troponymy, 형용사 양극 attribute 공간. 형태 관계(antonymy)와 뜻 관계(hyponymy)를 나눈다 |
| Winston, Chaffin & Herrmann 1987 | 부분-전체 쌍 | component/integral object, member/collection, portion/mass, stuff/object, feature/activity, place/area |
| FrameNet (Baker 1998, Ruppenhofer 2006) | frame 과 frame element(FE) | Inheritance, Perspective_on, Subframe, Precedes, Inchoative_of, Causative_of, Using, See_also |
| VerbNet (Kipper 2008) | 같은 통사 교체를 보이는 동사 묶음 | thematic role, selectional restriction, 시간 단계가 붙은 semantic predicate |
| PropBank (Palmer 2005) | 동사 쓰임(roleset) | Arg0–Arg5(동사마다 정의), ArgM 부가 역할 |
| Generative Lexicon (Pustejovsky 1991) | 낱말 뜻의 네 층 | qualia: formal, constitutive, telic, agentive |
| OntoLex-Lemon (W3C 2016) | LexicalEntry, LexicalSense, reference, LexicalConcept | lexicalRel(형태), senseRel(뜻), 그 하위의 TerminologicalRelation |

troponymy 는 '어떤 방식으로 하는 것'이라는 동사 상하 관계다(걷다 → 터벅터벅 걷다). qualia 는 한 낱말 뜻을 이루는 네 측면으로, 무엇의 한 종류인지(formal), 무엇으로 이루어지는지(constitutive), 무엇에 쓰이는지(telic), 어디서 생기는지(agentive)다. frame 은 낱말이 불러내는 장면 지식이고, FE 는 그 장면 안의 역할이다.

### 근거

- WordNet 의 관계 판정은 원어민이 "An x is a (kind of) y" 같은 시험 문장 틀을 받아들이는지로 한다(Introduction p.8). 품사마다 조직이 다르다는 근거는 Fillenbaum & Jones 1965 단어 연상 자료다(p.2–3).
- 25개 unique beginner 는 lexicographer 작업을 파일로 나누는 공학 편의도 함께 이유로 든다(Nouns p.16). 원문 스스로 이 위계들이 서로 배타적이지 않다고 적는다(p.16).
- Winston 1987 은 실험 논문이 아니다. 분류는 'part of' 시험 문장과 부분-전체 삼단논법에 대한 개념 분석으로 세웠고, sorting 실험은 Chaffin & Herrmann 1984 의 결과를 인용할 뿐이다(§7.2, p.437). 유형이 다른 부분-전체를 이어 붙이면 transitivity 가 깨진다는 것이 핵심 결과다(Abstract).
- FrameNet 은 같은 frame 의 LU(lexical unit, 낱말 하나와 그 뜻 하나의 짝)가 같은 수와 종류의 FE 를 가져야 한다는 명시 기준으로 frame 을 나누고 합친다(Ruppenhofer 2006 Ch.2, p.11). 다른 연구자가 다르게 나눌 수 있다고 스스로 인정하고, frame 관계가 그 차이를 잇는다고 적는다(p.103).
- PropBank 는 보편 역할 목록을 세우기 어려워 동사마다 역할을 정의한다(§3, p.75). 두 사람이 따로 주석했고 역할 분류 κ 는 .93–.96 이다(p.86).
- Generative Lexicon 의 근거는 이론 논증과 다의 예문이다. qualia 인용은 §5(p.417–418)와 §6(p.426)에 있다.

### KG 적용

- BabelNet(Navigli & Ponzetto 2010)은 WordNet synset 과 Wikipedia 를 잇고, 관계 이름이 없는 Wikipedia 링크를 ε 로 따로 표시한다(§2). 매핑 F1 은 79.6 이다(§4).
- Framester(Gangemi 2016)는 frame 을 D&S(Descriptions and Situations) 패턴으로 형식화한다. 같은 개체와 관계로 이루어진 *서로 다른* situation 이 각각 다른 description 을 만족한다는 모형이다(§4.1).
- Predicate Matrix(López de Lacalle 2016)는 FrameNet, VerbNet, PropBank, WordNet 을 lexical 수준과 role 수준 두 단계로 맞춘다. SemLink 를 gold 로 두고 precision 을 우선한다(§3). PB-FN 매핑 P 89.8 / R 52.4 는 predicate 수준 값이다.
- VerbNet 1.0 은 PropBank 사례 약 50,000개에 맞춰 봤을 때 정확히 일치한 경우의 78% 넘게를 자기 frame 으로 설명했다(Kipper 2008 p.5). 이것은 범위 보고다.
- OntoLex 는 LexicalSense 에 사용 조건(usage)을 붙이고, TerminologicalRelation 의 범주 예로 diatopic(지역), diaphasic(사용역 register: 'headache' 대 'cephalalgia'), diachronic(시대), diastratic(담화·문체), dimensional(같은 개념의 다른 측면 부각)을 든다(§6.1). 약어·이표기는 lexicalRel 쪽(예: initialismFor)이고, TerminologicalRelation 은 표면 형태가 직접 관련되지 않은 용어들의 뜻 사이 변이다.

### 한계

- WordNet 은 부분-전체 6유형 가운데 셋만 코딩했다(Nouns p.21). 전문 용어 범위가 좁다. `concept-extraction-papers/research.md` 가 인용한 AbsPyramid(추상 개념 entailment 벤치마크)는 명사구의 6.3% 만 WordNet 이 덮는다고 보고했다.
- Fillmore 1985 는 "sharing semantic content is no guarantee of membership in a single interpretive frame" 이라고 적는다(p.229 각주 11). [추정] 의미 유사도만으로 용어를 합치면 frame 이 다른 용어를 잘못 합칠 수 있다(사례: Fillmore 1985 각주 11, 1건).
- VerbNet 은 영어 통사 교체에 기대어 한국어에 그대로 옮기기 어렵다(Break Verbs 예).
- NSM(Natural Semantic Metalanguage, 모든 언어에 있다고 보는 기본 의미 낱말로 뜻을 풀어 쓰는 이론, Wierzbicka 2021)의 65개 semantic prime 은 p.326 Figure 1 에 그림으로 실려 있다. 범주 이름 글자는 그림에 없다.

### 예문 분해

- WordNet 식: '단말' is-a '장치', '기지국' is-a '시설'. 'SKT'/'SK텔레콤' 은 같은 synset 의 다른 표기다.
- 부분-전체: 'RRC 재설정'은 '핸드오버'의 feature/activity 부분이다. '기지국'은 '망'의 component 다. 두 관계를 한 '포함'으로 이으면 경로 추론이 틀린다.
- FrameNet 식: 실패 사건 frame 에 FE 로 참여자(단말), 장소(SKT 기지국), 시간 배경(핸드오버 중), 원인(RRC 재설정 실패), 영향 대상(호)이 놓인다.
- PropBank 식: '끊기다' 의 Arg1 = 호, ArgM-CAU = RRC 재설정 실패, ArgM-TMP = 핸드오버 중.
- qualia 식: '단말' formal = 장치, telic = 통신, constitutive = 모뎀·안테나.
- OntoLex 식: LexicalEntry 'SKT' → LexicalSense(이 보고서에서 통신사를 가리킴) → reference SK텔레콤 개체. 'SKT'와 'SK텔레콤'은 lexicalRel 로 잇는다.

## 3. 인지 지향 상위 온톨로지

KG 최상위 유형과 관계를 나누는 갈래다. 근거를 어디에 두느냐로 두 입장이 갈린다.

### 분류의 칸

| 체계 | 최상위 칸 | 기본 관계 | 범주의 근거 |
|---|---|---|---|
| DOLCE (Masolo 외 2003, Borgo 외 2022) | Endurant, Perdurant, Quality, Abstract(Region) | participation, inherence, quale, constitution, temporary parthood | 자연어와 상식(descriptive) |
| BFO (BFO 2.0 Specification 2015) | continuant, occurrent 와 그 하위(quality, role, disposition, process 등) | instance-level, type-level, instance-type 세 무리 | 최선의 과학이 이해하는 실재(realist) |
| UFO (Guizzardi & Wagner 2010) | Kind, Phase, Role, Mixin, Relator | formal relation, relator 가 매개하는 material relation | sortal 이론, 인지심리학 |
| Generalized Upper Model (Bateman) | 문법 실현에 결과가 있는 범주 | process-participant, generalized possession | 문법 |

endurant 는 시간 속에서 통째로 지속하는 것(장비)이고, perdurant 는 시간에 걸쳐 펼쳐지는 것(사건)이다. quale 은 개별 성질이 conceptual space 안에서 차지하는 위치다(1Gbps 라는 값). sortal 은 개체를 세고 같은지 가리는 기준을 주는 유형이다.

### 근거

- DOLCE 는 범주를 사람의 지각, 문화, 사회 관습에 기대는 "cognitive artifacts" 로 본다(D18 §3.1, p.13). quality 와 quale 을 나누는 근거로 자연어 문장 6개(Table 2)를 든다(§3.2.2, p.17).
- BFO 는 universal 을 정하는 일을 도메인 전문가에게 맡기고(§2.6, p.10), asserted hierarchy 를 부모가 하나인 monohierarchy 로 짓게 한다(§2.7, p.11). SNAP/SPAN 두 관점(한 시점의 스냅숏으로 보는 관점과 시간에 걸친 펼쳐짐으로 보는 관점) 문장은 §3.2, p.21 에 있다.
- Smith & Ceusters 2010 은 온톨로지 용어가 concept 를 가리킨다는 ISO TC37 용어학 전통을 직접 비판한다(§3.1). 그러면서도 concept orientation 을 통째로 버려야 한다는 논증은 아니라고 적는다(§3.3).
- ISO/IEC 21838 은 Part 2 에 BFO, Part 3(2023)에 DOLCE 를 둔다. 표준을 따른다는 것만으로 두 입장 가운데 하나가 정해지지 않는다.

### is-a 를 검사하는 법

OntoClean(Guarino & Welty 2004)은 클래스에 메타속성을 붙이고 subsumption 제약을 건다. rigidity 는 어떤 속성이 그 개체에게 본질적인지다. rigid 속성(사람)은 개체가 존재하는 한 늘 참이고, anti-rigid 속성(학생)은 개체가 잃을 수 있다.

| 메타속성 | 제약 |
|---|---|
| rigidity (+R, -R, ~R) | anti-rigid 속성은 rigid 속성을 subsume 할 수 없다 |
| identity (+I, +O) | 상위가 identity 기준을 가지면 하위도 같은 기준을 가진다 |
| unity (+U, ~U) | 상위가 unity 기준이나 anti-unity 를 가지면 하위도 같다 |
| dependence (+D) | 이 장에서는 형식화하지 않는다 |

원문은 OntoClean 이 메타속성 판정을 돕는 도구가 아니라 선택의 논리적 결과를 보여 주는 도구라고 적는다(p.153).

UFO 는 같은 생각으로 모든 개체가 Kind 하나를 instantiate 하고, rigid 유형은 anti-rigid 유형 아래에 올 수 없다고 정한다(§2.4, p.9). Role 은 다른 개체와의 관계로 정해지는 anti-rigid sortal 이다.

### KG 적용

- WordNet top-level 을 DOLCE 에 정렬하면서 Gangemi 2002 는 오류 다섯 유형을 찾았다. concept/individual 혼동, object/meta 수준 혼동, OntoClean 위반(role 이 type 을 subsume), 다의어 미검출, 일반성 수준 불균형이다(§3).
- Borgo 2022 는 DUL 을 DBpedia 에 적용해 불일치 수백만 건을 찾은 사례(Paulheim & Gangemi 2015 재인용)를 들고, 상위 온톨로지의 쓸모로 데이터 일관성 검사를 꼽는다(§4, p.23).
- Dadalto 외(Semantic Web 저널 투고본 swj3480)는 Wikidata 의 instance-of 와 subclass-of 층을 깨는 두 anti-pattern 을 SPARQL 로 셌다. AP1(anti-pattern 1)은 같은 항목이 다른 항목에 instance-of 와 subclass-of 를 (직접 또는 간접으로) 함께 가질 때다. AP2 는 한 항목이 두 항목의 subclass 인데 그 둘 가운데 하나가 다른 하나의 instance 일 때다(§3.1). AP1 쌍이 2,035,434개였다(§3.3, 심사본 기준).
- Hois 2010 은 GUM-Space(Generalized Upper Model 의 공간 언어 확장) 범주를 비전문 annotator 2명과 전문가 1명에게 주석시켜 Cohen's κ 0.657–0.78 을 얻었다. 범주 수가 가장 많은 그룹은 modality 였고, κ 가 가장 낮은 그룹은 영어에서 configuration, 독일어에서 modification 이었다(Table 1). 저자는 일치도가 인간 개념 구조의 증거는 아니고 범주가 배울 수 있고 구별된다는 증거라고 적는다(§2).
- Gärdenfors 2004 는 자연 개념을 conceptual space 의 convex region 으로 본다(Criterion P, §5). conceptual space 는 색·크기 같은 품질 차원들이 이루는 공간이고, convex region 은 그 안에서 두 점을 잇는 선분이 늘 영역 안에 남는 영역이다. DOLCE 의 quale 과 UFO 의 quality 가 이 생각을 인용한다.
- image schema(CONTAINMENT, PATH 같은 몸 경험에서 온 반복 패턴)는 ISAAC 온톨로지에서 FrameNet frame 으로 형식화됐다(De Giorgis 2022 §1). 원 이론의 기준이 형식화되지 않았다고 저자들이 적는다(§3.1).

### 한계

- 상위 온톨로지가 설계의 어느 단계에서 왜 쓸모 있는지는 널리 합의되지 않았다(Borgo 2022 §4, p.22).
- Bechberger & Kühnberger 2017 은 Manhattan 거리로 영역(domain)을 합치면 convex region 이 영역 사이 상관(아이의 나이와 키)을 표현하지 못한다고 보인다(§2.2).
- 상위 범주를 LLM 추출 파이프라인에 넣고 정확도를 견준 실험은 이 갈래에서 찾지 못했다.

### 예문 분해

- endurant: 단말, 기지국. perdurant: 핸드오버(process), RRC 재설정(event), 호(process), 끊김(event). quale: '5G NR' 은 기술 규격이라 정보 객체로 두는 편이 맞다.
- SKT 는 Kind '회사'를 instantiate 하고 Role '통신사'를 수행한다. '통신사' 아래에 rigid 유형을 두면 OntoClean 제약을 어긴다.
- 'SKT instance-of 통신사' 와 '통신사 subclass-of 사업자' 는 함께 둘 수 있다. 'SKT subclass-of 통신사' 를 함께 적으면 AP1 이 된다.
- 보고서 자체는 BFO 의 generically dependent continuant(정보 내용)다. 문서 노드와 문서가 말하는 장비·사건 노드를 다른 범주로 둔다.

## 4. 용어학

개념과 이름을 따로 두는 갈래다.

### 분류의 칸

Wüster 계열 일반 용어학은 onomasiological 접근을 쓴다. onomasiological 은 개념을 먼저 세우고 이름을 뒤에 붙이는 방향이다(사전처럼 낱말에서 뜻으로 가는 semasiological 의 반대).

| 출처 | 칸 |
|---|---|
| ISO 1087:2019 | individual concept, general concept, generic relation, partitive relation, criterion of subdivision, intension, delimiting characteristic |
| Z39.19-2005 | 동의 5유형: synonym, lexical variant, near-synonym, generic posting, compound 교차 참조. 계층 3유형: generic(BTG), instance(BTI), whole-part(BTP). 연관(RT)은 Table 1 의 11종과 지역 코드 |
| ISO 25964-1 | ThesaurusConcept, PreferredTerm, SimpleNonPreferredTerm, 계층·연관은 개념 사이, 동의는 용어 사이 |
| SKOS | Concept, prefLabel/altLabel/hiddenLabel, broader/narrower/related, exactMatch(전이)/closeMatch(비전이). SKOS-XL 은 라벨을 자원으로 만든다 |
| TBX | conceptEntry, langSec, termSec. administrativeStatus(preferred/admitted/deprecated/superseded), termType(fullForm/acronym/abbreviation/variant) |
| Temmerman 1997 | clear-cut concept, prototype 구조 범주, umbrella unit / entity / activity |
| Faber 2009 (FBT), EcoLexicon | domain event 의 역할(AGENT, PROCESS, PATIENT, RESULT, LOCATION), 관계 17종 |
| Freixa 2006 | 변이 원인 5영역: dialectal, functional, discursive, interlinguistic, cognitive |
| Daille 2003, Jacquemin 1997 | 변이 형태: graphical, inflexional, syntactic(삽입·등위), morphosyntactic, paradigmatic, anaphorical |

### 근거

- ISO 문서는 표준 합의다. ISO 704:2022 는 정의를 intensional definition(직속 상위 개념 + 구별 특성)으로 쓰라고 권한다(3.3 Note 1). 같은 표준은 지식 모델링·정보 모델링·데이터 모델링·분류를 범위에서 뺀다(0.1).
- Z39.19 는 계층 검사로 "[narrower term] is a [broader term]." 문장과 all-and-some test 를 둔다(§8.3.1). 상위어와 하위어는 같은 기본 종류(사물, 행위, 속성)여야 한다(§8.3, p.47). 선호어는 literary, organizational, user warrant 로 고른다. user warrant 는 사용자 질의 빈도다(§4, p.10).
- Z39.19 는 약어를 §8.2.2 에서 lexical variant 로 두지만 Table 1 에서는 'UN / United Nations' 를 synonymy 로 둔다. 표준 안에서도 분류가 갈린다.
- Temmerman 1997 은 생명과학 문헌을 시간 순으로 읽어 prototype 구조 범주에서는 한 개념 한 이름이 불가능하다고 보인다(Abstract, p.51). 동의어는 다른 관점을 반영한다고 본다(Figure 10, p.67).
- Cabré 2003 은 용어 단위를 인지·언어·소통 세 면을 가진 다면체로 본다(PT 번역 p.543). Wüster 지지자들은 Wüster 사후 저작부터 통제된 동의어를 인정했다고 반론한다고 Cabré 가 전한다(PT p.514).
- Daille 2003 은 변이가 문서에서 15–35% 나타난다고 인용하고(§3.1), 삽입 변이가 하위 개념을 만드는 예를 든다(§3.2). Jacquemin 1997 은 공기 후보 가운데 진짜 변이가 Type 1 55%, Type 2 52% 였다고 보고했다(§5).

### KG 적용

- ISO 25964 대응표는 BTG/BTI/BTP 를 SKOS 확장 iso-thes:broaderGeneric/Instantial/Partitive 로 옮긴다(p.10). SKOS 자체는 세 계층을 나누지 않는다.
- SKOS 는 closeMatch 를 비전이로 둔다. 둘 넘는 개념 체계를 이을 때 오류가 연쇄되지 않게 하려는 것이다(§10.1). exactMatch 는 전이다.
- TBX-Basic 은 개념 관계 전용 칸이 없다. TBX 2008 default XCS 에는 broaderConceptGeneric/Partitive, temporallyRelatedConcept 같은 개념 관계 data category 가 있지만 XML 구조로 강제되지는 않는다.
- qSKOS(Mader 2012)는 공개 SKOS 어휘 15개 모두에서 품질 문제를 찾았다. 두 개념의 라벨(prefLabel·altLabel·hiddenLabel)이 겹치는 Label Conflicts, Orphan Concepts, Cyclic Hierarchical Relations 를 검사한다(§3). 두 개념의 라벨 충돌은 SKOS 무결성 조건이 아니라 SKOS Primer 권고라서 qSKOS 같은 도구가 따로 잡는다.
- EcoLexicon 화면의 관계 선택 목록은 hyponymic 1, meronymic 6, non-hierarchical 10 이다(저장한 `ecolexicon-relation-checkboxes.txt`). Reimerink 2010 은 part_of 에 transitivity 를 줘 간접 관계를 추론한다고 적는다(§3.1). 문맥 제약은 개념이나 관계가 아니라 명제 단위에 건다(§5).
- Roche 2012 는 ASTECH 프로젝트에서 공유 개념을 먼저 세우고 파트너마다 자기 용어(변이 포함)를 붙였다(§5, p.2628). 원문은 코퍼스에서 뽑은 어휘 구조가 전문가가 정의한 개념 구조와 맞지 않는다고 적는다(§4, p.2628).

### 한계

- ISO 1087·704 는 SIS 공개 미리보기만 열어서 연관 관계 하위 유형과 정의 작성 규칙 본문을 확인하지 못했다.
- Faber 2009 는 Termontography(Temmerman & Kerremans 2003, p.118)가 온톨로지 공학으로 바뀌며 prototype 을 잃었다고 비판한다(p.119).
- Daille·Jacquemin 은 프랑스어·영어 명사구 패턴 중심이라 한영 혼용에 그대로 옮길 수 없다.

### 예문 분해

- 개념 entry 'RRC 재설정': 선호어 'RRC 재설정', 허용어 'RRC Reconfiguration'(interlinguistic 변이). 'SKT'/'SK텔레콤' 은 lexical variant 다.
- 'SKT' 는 individual concept 이라 '통신사'와 BTI(instance)로 잇는다. generic posting 으로 'SKT' 를 '통신사'에 녹이면 어휘의 구체성이 떨어진다(Z39.19 §8.2.4 는 이 기법을 주변 분야로 한정하고 신중히 쓰라고 경고한다).
- 'RRC 재설정 실패' BTG 'RRC 실패'. 'SKT 기지국' 에서 'SKT 코어망' 은 삽입 변이처럼 보이지만 다른 하위 개념이다.
- FBT 식 사건 template: PROCESS 핸드오버, cause RRC 재설정 실패, RESULT 호 끊김, LOCATION SKT 기지국.

## 5. 상식·사건 지식

KG 를 노드 종류가 아니라 관계 종류로 나누는 갈래다.

### 분류의 칸

| 축 | 칸 | 출처 |
|---|---|---|
| 사실 대 추론 | taxonomic 지식 대 if-then 추론 지식 | ATOMIC (Sap 2019) |
| 관계의 지식 유형 | 13 차원(lexical, similarity, taxonomic, part-whole, spatial, temporal, utility 등) | Ilievski 2021 |
| 관계의 의미 범주 | physical-entity, social-interaction, event-centered | ATOMIC 2020 |
| 인과 설명 | X 앞 5 차원, 뒤 5 차원, specific statement 와 general rule 짝 | GLUCOSE |
| 사건 사이 관계 | TEMPORAL, CONTINGENCY, COMPARISON, EXPANSION (+Co-Occurrence) | PDTB 2.0, ASER |
| 시간 모양 | state, activity, accomplishment, achievement | Vendler 1957 (Friedrich 외 정리) |
| 정형 대 새 상황 | script, plan, what-if(obstacle, error, distraction) | Schank & Abelson 1975 |
| 상황 변화 | DynamicEvent, StaticEvent, pre/post/during situation | ESO(Event and Implied Situation Ontology, Segers 2016) |
| 맥락 | 12 차원(Absolute Time, Type Of Place, Granularity, Justification 등) | Lenat 1998 (Cyc) |

aktionsart 는 동사가 전제하는 시간의 모양이다. state 는 끝이 없는 상태, activity 는 끝점 없는 진행, accomplishment 는 과정 뒤 끝점이 있는 사건, achievement 는 순간에 끝나는 사건이다.

### 근거

- Ilievski 2021 의 13 차원은 저자들이 손으로 분류했다(§4). 차원별로 합성 QA 를 만들어 RoBERTa 를 학습시킨 뒤 상식 질문 벤치마크 CSQA(CommonsenseQA)와 SIQA(SocialIQA)에서 zero-shot 정확도를 쟀다. temporal 차원이 기준선보다 CSQA +22.3, SIQA +15.3 을 냈고, CSQA 최고는 utility 차원(+22.4)이었다(Table 10).
- 같은 논문의 LM 임베딩 군집과 차원 군집의 일치도는 ARI(adjusted Rand index, 두 군집 결과가 얼마나 겹치는지를 우연 수준으로 보정한 값) 0.226·0.235 로 낮았다(§5). 그래서 이 실험은 차원 분류를 받쳐 주지 않는다.
- GLUCOSE 는 이야기 이해 연구(Kintsch & van Dijk 1978 등)에서 차원 후보를 내리고, 크라우드 파일럿으로 겹침은 줄이고 일치는 늘렸다(§3.1).
- PDTB 2.0 의 sense 일치도는 class 94%, type 84%, subtype 80% 다(§3, Table 3). 하위 단계에서 갈리면 바로 위 단계 태그를 주었고, class 수준 불일치는 전문가 3명이 판정했다.
- Lenat 1998 은 100개 넘는 차원 후보를 가장 가까운 둘씩 묶기를 되풀이해 12개로 줄였다(§2.6, p.23). 차원을 고르는 기준으로 철학·언어 모델 부합을 일부러 뺐다.

### KG 적용

- CSKG 는 7개 자원을 합치며 노드 종류(개체, 클래스, 낱말, 행위, frame, 상태)의 경계를 일부러 흐리고(P1), edge type 을 ConceptNet 중심 58개로 줄였다(§3.1, §6). 같은 'scene' 라벨 노드가 18개 남는 등 노드 해소는 남은 과제다(§6).
- ConceptNet 5.5 는 core 36 관계라고 적지만 실제 목록은 35개이고, 공식 위키는 34개라고 한다. 사건 관계(Causes, HasPrerequisite)와 개체 관계가 한 집합에 섞여 있다.
- ATOMIC 2020 의 Causes 관계는 376개뿐이다(Table 1). [추정] 사건 인과를 외부 상식 KG 로 메우기 어렵다(사례: ATOMIC 2020 Causes 376개, 1건).
- ASER 는 접속사로 eventuality 관계를 뽑고, ConceptNet Causes 와 자기 Precedence 가 강하게 겹친다고 보였다(§5.3).
- EventKG 는 사건을 노드로 두고 시간을 관계의 유효 기간 속성으로 둔다(§3).
- ESO 는 FrameNet frame 103개를 전후 상황 추론에 차이가 없으면 합쳐 63개 클래스로 줄였다(§3). MEANTIME 코퍼스에서 손으로 살핀 사건 52개 가운데 21개만 맞았다. Table 8 과 초록은 이를 50% 로 적지만 21/52 는 40% 다. 원문은 gold 대비 술어 정밀도 36.1%·재현율 68.2% 가 낮은 까닭의 일부로 도메인 불일치(ESO 는 자동차 산업용, MEANTIME 은 항공·증시 등 다른 산업 뉴스)를 든다. 21/52 검사의 오류는 파이프라인 모듈별로 따로 분석한다(Table 9).

### 한계

- 이 갈래 자원은 모두 영어 일상·뉴스 텍스트다. 네트워크 장애 보고서에 적용한 1차 연구는 찾지 않았다.
- PDTB 는 성립하는 의미 관계 가운데 적어도 하나를 달 뿐 전부를 달지는 않는다(§3).
- Vendler 원문은 열지 못했다. 네 범주는 Friedrich 외의 2차 정리로만 확인했다.

### 예문 분해

- 관계 차원: '실패로 끊겼다' 는 temporal 이 아니라 인과 관계다. '핸드오버 중' 은 temporal(Synchronous)이다.
- ASER 식: ⟨'RRC 재설정 실패', Synchronous, '단말 핸드오버'⟩, ⟨'호 끊김', Reason, 'RRC 재설정 실패'⟩. ASER 의 ⟨E1, Reason, E2⟩ 는 E2 때문에 E1 이 일어난다는 뜻이다(Table 3).
- aktionsart: 핸드오버 accomplishment, RRC 재설정 실패 achievement, 호 끊김 achievement. state 는 이 문장에 없다.
- ESO 식: pre-situation '호 연결됨', post-situation '호 해제됨'.
- GLUCOSE 식 general rule: '단말A 가 핸드오버 중 RRC 재설정에 실패한다 → 호A 가 끊긴다'.
- Cyc 맥락 차원: Type Of Place = SKT 망, Absolute Time = 미상, Justification = 보고(관찰인지 추정인지 적히지 않음).
- Schank 식: 정상 script '핸드오버' 의 error what-if 가 'RRC 재설정 실패' 다.

## 6. 공학 쪽 KG 유형론

공학 분류는 출처·형식·용도를 축으로 쓰고, 인지 아키텍처 쪽은 기억 체계를 축으로 쓴다.

### 분류의 칸

| 출처 | 칸 |
|---|---|
| Hogan et al. 2021 | 데이터 모델(edge-labelled, property graph 등), schema 3종(semantic, validating, emergent), identity, context, deductive/inductive 지식 |
| Pan et al. 2024 | encyclopedic, commonsense, domain-specific, multi-modal |
| Ji et al. 2022 | 데이터셋 general, domain-specific, task-specific (temporal 은 예고만 하고 비어 있다) |
| Paulheim 2017 | KG 의 최소 기준 4개, 정제 목표(completion / error detection), internal/external 방법 |
| Soar (Laird 2022), CoALA (Sumers 2024) | working memory, semantic memory, episodic memory, procedural memory |
| Zep (2025) | Episode, Semantic Entity, Community subgraph, 두 시간축 |
| Hu et al. 2025 | factual, experiential, working memory |

Soar 와 ACT-R 은 인지 아키텍처(사람 인지를 모사하는 계산 모형)다. CoALA(Cognitive Architectures for Language Agents)는 그 기억 구분을 LLM 에이전트 설계에 옮긴 틀이다.

### 근거

- Hogan 은 context 를 "scope of truth" 로 정의한다(§3.3). semantic schema 는 추론을, validating schema(SHACL·ShEx shape)는 검증을 맡는다(§3.1.2).
- Hogan 은 commonsense 와 domain knowledge 를 그 지식을 공유하는 사람 수로 한 문장에서 가른다(§4 도입).
- Pan 2024 는 네 칸을 저장된 정보로 나눈다고 적는다. 그러나 칸마다 기준이 다르다. encyclopedic·commonsense 는 내용, domain-specific 은 범위, multi-modal 은 매체가 기준이다(§2.2). 'linguistic KG' 칸은 Pan 에도 Ji 에도 없다.
- Paulheim 기준으로는 WordNet(낱말 관계)과 단일 영역 데이터가 KG 가 아니다(§2).
- Soar 는 semantic memory 를 그래프 구조로 두고 WordNet 이나 DBpedia 로 초기화할 수 있다고 적는다. 자동 학습 기제는 아직 없고 의도적 저장만 한다(§6).
- Chella, Frixione & Lieto(AAAI Fall Symposium 2017)는 인지 아키텍처 기억이 classical 정의만 담고 prototype·exemplar 성분을 못 담는다고 비판한다.

### KG 적용

- ORKG 의 'cognitive knowledge graph' 는 재사용 패턴(graphlet)을 얹은 KG 다. 저자 스스로 graphlet 을 SHACL shape 집합이나 SPARQL graph pattern 으로도 볼 수 있다고 적는다(Rabby 2024 §3.1). [추정] 그래서 Hogan 의 validating schema 와 형식상 다르지 않다(사례: Rabby §3.1 의 SHACL shape 해석, 1건).
- Zep 은 보고서 같은 원문을 episode 로 손실 없이 두고, 거기서 엔티티와 사실을 뽑는다(§2). 시간이 겹치는 모순이 생기면 옛 edge 의 무효 시점을 새 edge 의 시작 시점으로 맞추고 옛 edge 는 이력으로 남긴다(§2.2.3).
- AriGraph(IJCAI 2025)는 같은 관찰에서 나온 삼항을 episodic edge 로 묶는다. 텍스트 게임과 함께 MuSiQue·HotpotQA 문서 QA 로도 실험했다(§5.3).
- ACT-R 의 activation 식에서 한 항목에 붙은 사실이 많을수록 연관 강도가 S − ln(fan) 으로 줄어든다(Anderson 2004, p.1042).

### 한계

- Hogan 은 지식 유형(사실·사건·절차)을 따로 나누지 않는다.
- Zep 의 무효화는 '현재 상태'를 판정할 때 수집 순서상 새 정보를 우선한다(§2.2.3). [추정] 측정 조건이 달라 생긴 상충을 시간 상충으로 잘못 읽을 수 있다(사례: §2.2.3 의 시간 겹침 모순 처리 규칙, 1건).
- 1980년대 네덜란드 Knowledge Graph theory(Nurdiati & Hoede 2008 요약)는 정신 속 표상을 그래프로 보고 관계를 8종으로 고정했다. 검증에서 빠진 중심 문헌으로 지목됐고 원문은 `lab/sources/kg-typology/nurdiati2008.txt` 에 있다. 본문 분석은 하지 않았다.

### 예문 분해

- Pan 식: 사내 보고서 KG 는 domain-specific KG 다.
- Hogan 식: 예문은 data graph 의 edge 묶음이다. 작성자·작성일·시험망은 context 로 붙인다. '통신사' 계층은 semantic schema, 보고서 템플릿 칸 검사는 validating schema 다.
- 기억 체계 식: 이 문장이 든 보고서는 episode, '핸드오버 중 RRC 재설정 실패는 호 끊김을 일으킨다'는 semantic 사실, 이 사실을 찾은 질문 경로는 experiential memory 다.

## 7. 분류 방법론

분류를 세우는 법과 검증하는 법이다. 단계별 정리는 #방법론 에 모았다. 여기서는 각 방법이 원문에서 무엇을 보였는지만 적는다.

### 세우는 법

- competency question(CQ)은 온톨로지가 답해야 할 질문으로 요구를 적는 방법이다. Uschold & Gruninger 1996 §6.4 는 모든 CQ 가 단순 조회면 잘 설계된 온톨로지가 아니라고 적고, CQ 집합에 대응하는 온톨로지가 하나가 아니라고도 적는다.
- METHONTOLOGY 는 conceptualization 의 첫 산출물로 Glossary of Terms 를 두고 용어를 concepts·instances·verbs·properties 로 나눈다(§4.3). 명세 문서에는 concision, partial completeness, consistency 를 요구한다(§4.1).
- NeOn 방법론의 ORSD(Ontology Requirements Specification Document, 온톨로지 요구 명세서)에 든 pre-glossary 는 CQ 에 나온 용어와 빈도, 답에 나온 용어와 빈도, 답에 나온 개체를 따로 모은다. 공공 구직 포털 사례 SEEMP 의 예시에서 CQ 에는 'Job Seeker', 답에는 회사 이름이 나온다.
- eXtreme Design 은 CQ 마다 SPARQL 과 기대 결과를 짝지은 unit test 를 둔다. 모든 test 를 통과해야 다음 이야기로 간다.

### 사람에게서 범주를 끌어내는 법

- free listing 은 생각나는 항목을 적게 하고 순위와 빈도로 현저성을 잰다. Chaves 2019 는 Monte Carlo 귀무 분포로 216개 항목 가운데 38개만 우연보다 현저하다고 판정했다.
- card sorting 은 카드를 묶게 해 항목 쌍 유사도를 잰다. Tullis & Wood 2004 결과로 15명이면 168명 결과와 상관 0.90, 30명이면 0.95 다(Nielsen 2004 전달).
- 특징 규범(McRae 2005)은 개념당 30명에게 특징을 적게 하고 5명 이상이 적은 특징만 남긴다. 동의어 특징은 한 이름으로 기록했다.
- 단어 연상(SWOW 2019)은 단서당 100명에게 떠오르는 말 3개를 받아 약한 연상까지 잡는다. random walk 관련도가 사람 관련도 판단을 r = .81 로 예측했다.
- triad 과제는 셋 가운데 더 가까운 둘을 고르게 해 taxonomic(종류)과 thematic(같은 상황에 함께 나옴) 선호를 잰다. Mirman 2017 은 여러 연구의 북미 대학생 300명 넘게 가운데 약 80% 가 어느 한쪽을 통계적으로 믿을 만하게 선호했고 두 쪽이 대체로 반반이었다고 정리한다. 전문가 집단은 훈련·목적·문화에 따라 어느 쪽으로도 기운다.

### 검증하는 법

- 주석 일치도: Krippendorff 는 3명 이상 독립 코더와 미리 고정한 지침을 요구한다(Artstein & Poesio 2008 §4.1.1 이 옮김). A&P 자신은 전문가 코더를 허용하고(§5.1) 코더 수를 늘리라고 권한다(§5.2). 범주가 계층이면 Krippendorff α 를 권하고, 문턱이 필요하면 0.8 을 든다(§5.2–5.3).
- 계층 검사: OntoClean 제약, 온톨로지 설계 오류 검사기 OOPS!(OntOlogy Pitfall Scanner!)의 pitfall 목록(동의어를 클래스로 만들기 P02, 다의어 요소 P01, '기타' 클래스 P21), SKOS 무결성 조건, qSKOS, Wikidata anti-pattern SPARQL.
- 평가 층: Brank 2005 는 평가를 lexical(어휘·데이터), hierarchy·taxonomy, 다른 의미 관계, 맥락·응용, syntactic, 구조·설계의 여섯 수준으로 나눈다.
- LLM 대조: TaxoGlimpse(PVLDB 17(11), 2024)는 LLM 정확도가 뿌리에서 잎으로, 공통 분야에서 전문 분야로 갈수록 떨어진다고 보고하고, 부모의 형제를 오답으로 넣은 hard negative 질문을 쓴다. GPT-3 특징 규범은 사람과 비슷한 유형 분포를 보였다(Hansen & Hebart 2022). 임베딩 유사도는 반의어를 가깝게 놓는 경우가 있다(Digutsch & Kosinski 2023 Table 1, 반대 방향 쌍도 있음). LLM 이 만든 CQ 는 평균 90자가 넘어 다른 방법(42–52자)의 약 두 배이고, 저자들은 다듬기 단계가 더 필요하다고 본다(Alharbi 2025, arXiv v2 에 ESWC 2026 채택 표기, Table 4).

### 예문 분해

- CQ: '핸드오버 중 호 끊김의 원인은 무엇인가' → 기대 답 'RRC 재설정 실패'. 상위 CQ: '2026년 SKT 망에서 재발한 RRC 장애는 무엇인가'.
- OntoClean 검사: '5G NR 단말' 은 rigid, '시험 대상 단말' 은 anti-rigid role 이다.
- card sort: 엔지니어 15명이 'RRC 재설정 실패' 카드를 'RRC 문제' 더미에 넣는지 '핸드오버 문제' 더미에 넣는지 본다.
- triad: 'RRC 재설정 실패' 와 더 가까운 것은 'RRC 연결 실패'(taxonomic)인가 '핸드오버'(thematic)인가.

## 8. 한국어 어휘·용어 자원

한국어 자원은 범주 정의 방식, 분류 잇기, 변이 거버넌스를 준다.

### 분류의 칸

| 자원 | 칸 |
|---|---|
| KorLex 1.5 (윤애선 외 2008) | WordNet 식 synset 계층, 분류사 망의 도량성·개체성·중립성·사건성 |
| 세종 의미 부류 (이성헌 2007) | 최상위 <구체물>, <집단>, <장소>, <추상적 대상>(논항 명사) 대 <사태>(술어 명사), 2–7층위 |
| U-WIN (옥철영 2007) | 상하·동의·유의·반의·부분전체 + 분야 특화 개념 관계(포함, 운용, 측정, 증상 등) |
| 표준국어대사전 | 기본 표제어와 ≒(모든 변이 나열)/=(정규형 하나 가리킴), 전문 분야 67개 |
| 우리말샘 | 관련 어휘: 비슷한말, 본말·준말, 상위어·하위어, 이형태, 동류 개념 등 |
| 국립국어원 보고서 | 어종 조합 8유형, 번역 4유형(일대일·축소·확대·기타) |
| 최기선·박정원 2007 | -율/-률, 두음법칙, 띄어쓰기, 외래어 표기, 동일 원어 상이 번역, 상이 원어 동일 번역 |

### 근거

- 세종 부류는 적정 술어로 정의한다. 적정 술어는 특정 의미 영역의 명사와만 제한적으로 결합하는 술어다(§2, p.52–53). 명사가 그 술어와 결합하는지로 소속을 판정해서, 원문은 체계를 언어 내적이고 형식적이라고 부른다(§4.2, p.59).
- KorLex 는 『표준국어대사전』의 의미 구분을 기준으로 삼았다(§3, p.43). 1.0 대역은 어휘 전문가 또는 해당 분야 전공자 10명이 했고, 1.5 확장은 4명이 교차 검토한 뒤 의미론 박사 2명이 검증했다(p.44–45). 특수 전문용어는 뺐다(§3.2).
- 국어기본법 제17조와 시행령 제12조의2 는 부처 표준화협의회 심의 → 국어심의회 확정 → 고시 → 법령·교과서·공문서 활용 의무를 정한다.
- 최기선 2007 은 대역어 심의 지침 7조를 둔다. 주 원칙(수준 일치, 순 우리말, 성분 일관성, 개념 정확성)으로 후보를 만들고, 경쟁하면 고빈도와 사전 등재로 고른다. 'interoperability → 상호 운용성' 이 [제6조] 예다(p.21).

### KG 적용

- Park 외 2010(ALR8)은 세종 부류에 속한 단어들이 KorLex 에서 공유하는 최소 공통 상위 노드(LUB)를 찾아 부류를 synset 에 잇는다. 정답은 계산의미론 박사 1명의 수작업 매핑(Bae, Im & Yoon 2010, Korean Journal of Cognitive Science 21(1))이고, 최고 F1 0.773 이다(§5).
- So 외 2009 는 두 분류가 어긋나는 세 유형을 든다. 1:n 대응, 한쪽은 상하인 쌍이 다른 쪽은 형제인 경우(<약>/<마약>), 범주 크기 차이다(§2.3).
- 우리말샘 사전 통계(2026년 9월)의 관련 어휘 구축 수는 상위어 135,577, 하위어 12,359, 이형태 1,128, 동류 개념 21,766 이다. 전문어는 706,422개(58.2%)이고, 정보·통신 전문어는 54,997개다. 『표준』의 정보·통신 전문어는 2,268개다.
- 우리말샘은 표제어·뜻풀이·분류를 필수 입력으로 두고, 관리자 승인 전 비공개, 전문가 감수 중 편집 금지, 사용자 요청에 따른 관리자 편집 금지, 편집 이력을 둔다(도움말).
- TTA 정보통신용어사전은 표제어 한 줄에 한글 정규형, 한자, 영문, 약어를 묶고 약어의 한글 음차('브이오엘티이')를 동의어로 단다(VoLTE 항목). 같은 개념의 사전 정의와 단체표준 정의를 검색 결과에 나란히 보여 준다. '용어 플러스' 항목에는 생성형 AI 로 만든 정의가 섞여 있다고 사이트가 밝힌다.

### 한계

- 세종 부류 수는 문헌마다 581, 582, 623, 약 650 으로 다르다. 판본 차이로 설명되는지는 확인하지 못했다.
- TTA 사전의 분야 필드는 현재 화면에서 비어 있어 분야 체계를 확인하지 못했다.
- 이 자원들은 통신 전문용어를 거의 담지 않는다(KorLex §3.2).

### 예문 분해

- 세종 식: '단말', '기지국', '호' 는 논항 명사(<구체물>, <추상적 대상>). '핸드오버', '재설정', '실패' 는 술어 명사 <사태>다.
- 적정 술어: '통신사' 부류는 '~에 가입하다', '~의 망', '~이 상용화하다' 와 결합하는 명사로 정의할 수 있다. 'SKT' 는 셋 다 자연스럽다.
- 어종: '핸드오버' 는 원어 음차, 'RRC 재설정' 은 약어 + 한자어, '단말' 은 한자어다.
- 변이 유형: '핸드오버'/'handover' 는 원어와 음차, 'RRC 재설정'/'RRC Reconfiguration' 은 번역 변이다.

## 9. 통신 도메인 표준 어휘

사용자 도메인의 표준은 용어, 장애 지식, 관리 대상, 시험 판정의 네 축을 준다.

### 분류의 칸

| 축 | 출처 | 칸 |
|---|---|---|
| 용어 | 3GPP TR 21.905 V19.2.0 | 알파벳순 정의·약어·식, CR 단위 변경 이력 |
| 용어 지위 | 3GPP TR 21.801 Annex C | preferred, admitted, deprecated/obsolete/superseded, subject field |
| 장애 속성 | X.733, 3GPP TS 32.111·28.111 | event type(5+보안 5), probable cause, perceived severity 6단계, trend, specific problem |
| 장애 개념 | IETF RFC 9940 | Event, State, Fault, Problem, Cause, Symptom, Incident, Alert, Alarm |
| alarm 모델 | IETF RFC 8632 | 계층적 alarm type identity, resource, root-cause-resource, impacted-resource |
| 관리 대상 | ITU-T M.3100, RFC 8345, TM Forum SID | fragment, NE·Network·Service 시점 / network·node·link·termination point·supporting / 도메인과 ABE |
| 시험 판정 | X.290(ISO/IEC 9646-1), TTCN-3 | pass, fail, inconclusive (+none, error) |
| 상호운용 시험 | ETSI EG 202 237 | EUT(Equipment Under Test, 시험 대상 장비), QE(Qualified Equipment, 이미 검증된 짝 장비), SUT(EUT 하나와 QE 를 합친 시험 대상 시스템), MoC(둘을 잇는 통신 수단), RQ(요구) → TP(시험 목적) → TC(시험 케이스) → verdict → report |

### 근거

- 표준 분류는 모두 공학 편의다. 3GPP TS 32.111-1 4.5 는 alarm 대응을 사람의 인지 과정으로 보고 alarm 품질 요건을 설명하지만 실험 근거는 아니다.
- 3GPP TR 21.801 C.1.4 는 한 명세에 정의된 개념에 다른 명세가 새 동의어를 들이는 것을 강하게 막는다. C.2.1 은 독립 어휘집을 개념 계층 순으로 배열하라고 권하지만 21.905 는 알파벳순이다.
- RFC 9940 은 Fault 를 순간에 일어나는 원치 않는 일로, Problem 을 조치가 필요할 수 있는 원치 않는 상태로 정의한다(§3.2). 이중화 망에서 링크 다운은 서비스 관점에서 Problem, 자원 관리 관점에서 Fault 라는 예를 든다. Symptom 은 문제의 징후로 *간주되는* 관찰이다.
- RFC 9940 이 다른 문서에 대문자로 쓰라고 권하는 주요 정의어는 Event, State, Fault, Problem, Symptom, Cause, Alert, Alarm 이다(§2). 'State 와 Problem 은 지속' 이라는 구분은 원문 정의가 아니라 해석이다. 원문의 시간 대비는 Event(순간)와 Change(기간) 사이에 있다.
- RFC 8632 는 X.733 의 평면 probable cause 를 계층 identity 로 바꿨고, 'clear' 를 심각도가 아니라 alarm 의 별도 상태로 둔다(Appendix F.2.1).
- 3GPP 는 같은 alarm 을 객체, 유형, 원인, 세부 문제(있으면) 네 속성으로 가린다(32.111-2). RFC 8632 F.2.3 은 이 키와 alarmId 가 겹치고 충돌할 수 있다고 비판한다.
- 3GPP 32.111-2 Table B.4 는 출처 표준별로 이름만 다른 같은 원인을 참고용으로 나열한다(예: 'Call Establishment Error' 와 'Call Setup Failure').
- ETSI EG 202 237 은 Fail 판정을 확정하기 전에 원인이 SUT 안인지 시험 연결 수단(MoC) 쪽인지 조사하라고 한다(8.6.2.2).

### KG 적용

- NORIA-O(Tailhardat 외, ESWC 2024, LNCS 14665)는 SKOS concept scheme 으로 표면형 변이("active", "up", "enabled")를 개념 하나에 묶는다(§3.2). 같은 개념을 여러 관점에서 해석하려고 scheme 을 여럿 둔다. 사전 분류(ticket category)와 사후 분류(problem category)를 나눈다(§4.3). 클래스 59개, 객체 속성 107개다. 26개 CQ 가운데 16개는 SPARQL 만으로 답했고, 원인 분석 질문은 AI 기법이 더 필요했다(§5).
- KTeleBERT(Chen 외, ICDE 2023)의 Tele-KG 는 Event 와 Resource 를 뿌리로 두고, 'Alm' 대 'Alarm' 같은 표면형 불일치를 문제로 짚는다(뿌리는 §II.A, 표면형은 §I).
- TN-AutoRCA(2025)는 기지국 alarm 시나리오 KG 의 간선을 dependOn(장비 계층), generate(장비 → alarm), causedBy(원인 가설)로 둔다. 원인에서 alarm 으로 역추적해 정답을 만들고, 순방향 추론이 원인 하나로 모이는지로 난이도를 매긴다. 530개 가운데 501개가 어려운 시나리오다.
- Yaman 외(ISWC 2025 Companion)는 RCA 사례를 이벤트·엔터티·개념 유형 9개 클래스로 구현하고, OpenSPG 가 RDF+SHACL 만큼 검증 능력이 성숙하지 않다고 적는다(§3).
- NORIA-O 는 X.733 을 이름으로 인용하지 않고 X.735 와 X.721 을 인용한다. [추정] event type 값과 심각도 문구는 X.733 계열과 같다(사례: NORIA-O §3.2 의 integrityViolation 분류 예, 1건). 값 목록을 하나씩 대조하지는 않았다.

### 한계

- X.733 probable cause 목록에는 관찰 증상(loss of signal), 원인 영역(power problem), 환경 사건(fire detected)이 한 열거에 섞여 있다.
- 28.111 은 QoS alarm type 이 장애가 난 영역을 가리키지 않고 서비스 품질 저하를 알린다고 적는다. 같은 장애에 다른 유형 alarm 과 함께 나오는 일이 많다고도 적는다(6.3). 다른 alarm type 은 영역을 가리키므로 기준이 다르다.
- TM Forum SID 의 ABE 목록과 ITU 용어 DB 의 항목 필드는 열지 못했다.

### 예문 분해

- RFC 9940 식: 'RRC 재설정 실패' 는 Fault(순간), '호 끊김' 은 Symptom 으로 간주될 관찰이다. 원인 가설은 Cause 노드로 따로 둔다.
- RFC 8345 식: node 'SKT 기지국', termination point 는 무선 인터페이스, 단말은 다른 network 의 node 다.
- TN-AutoRCA 식: 기지국 –generate→ alarm, '호 끊김' –causedBy→ 'RRC 재설정 실패'.
- X.733 식: event type 은 communications alarm 에 가깝다. probable cause 값은 X.733·3GPP 표를 대조해 고르고 skos:closeMatch 로 잇는다. 어느 값이 맞는지는 이번에 대조하지 않았다.
- 용어 지위: 'RRC Reconfiguration' 은 3GPP 쪽 preferred, 'RRC 재설정' 은 사내 admitted 로 둔다.
- 상호운용 보고서라면 SUT 는 단말과 기지국, verdict 는 원인 위치를 가린 뒤 Fail 로 확정한다.

## 10. 질문 유형론

질문을 인지 범주로 나누는 계보와 KG 경로 패턴으로 나누는 계보다.

### 분류의 칸

| 출처 | 칸 |
|---|---|
| Lehnert 1977 | 13개 Conceptual Category: Causal Antecedent, Goal Orientation, Enablement, Causal Consequent, Verification, Disjunctive, Instrumental/Procedural, Concept Completion, Expectational, Judgemental, Quantification, Feature Specification, Request |
| Graesser & Person 1994 | 18개 내용 범주(short answer / long answer), deep-reasoning 6범주, 생성 기제 4개, 명세 정도 3단 |
| QUEST (Graesser 외 1992) | 구조 4종(taxonomic, spatial, goal, causal), arc 범주(Isa, HAP, Property, Consequence, Reason, Outcome, Initiate, Manner 등), 질문 범주별 합법 경로 |
| Bolotova 2022 | 비사실형 6범주: INSTRUCTION, REASON, EVIDENCE-BASED, COMPARISON, EXPERIENCE, DEBATE |
| Li & Roth 2002 | 답 유형 coarse 6 / fine 50 |
| LC-QuAD 2.0, CWQ, GrailQA | SPARQL 템플릿: single fact, multi-fact, qualifier, count, ranking, temporal / composition, conjunction, superlative, comparative / 관계 수 1–4, 함수 |
| TimeQuestions | Explicit, Implicit, Ordinal, Temporal Answer |
| PolyG 2025 | 삼항 ⟨s,p,o⟩ 에서 빠진 요소에 따른 4 기본 패턴 + 중첩 |

### 근거

- Lehnert 학위논문(Yale Research Report #88)은 범주를 Conceptual Dependency 그래프 위의 판별 특징으로 정의한다. 인과 사슬이 있는지, 링크가 LEADTO·REASON·ENABLE 중 무엇인지, 미지수가 앞뒤 어느 개념인지를 차례로 묻는 판별망이다(Ch.2). 처리 절차가 같은 두 범주는 나눌 근거가 없다고 적는다(§2.0, p.42).
- Lehnert 는 Expectational 질문(기대가 어긋난 일을 묻는 질문)이 이야기 표상만으로는 답할 수 없다고 적는다(IJCAI 논문 §6.1, p.162).
- QUEST 는 질문 해석 결과를 (질문 범주, 질의 노드, 정보원) 삼항으로 두고(p.734), 범주마다 따라갈 arc 와 방향을 정한다. how(goal)은 backward Reason + forward Manner 이고(p.742), 인과 망의 why 는 인과 선행 사슬이다(p.743).
- 설명문 실험(Graesser & Hemphill 1991 계열, 1990 ONR 보고서가 요약)에서 경로 방향과 거리 감쇠로 된 단순 모형이 답 생성 점수 분산의 89% 를 설명했다. 거리 1–4 에서 점수가 .42, .28, .21, .20 으로 줄었다. 기술 도메인의 why 질문 답은 인과 선행 쪽(.08)보다 인과 결과 쪽(.20)에서 더 나왔다. 보고서는 이를 기술·생물 텍스트에 목적(teleological) 목표 구조가 얹힌 결과로 읽는다.
- Graesser & Person 1994 는 문항의 51% 만 단일 범주였다고 보고한다(p.119). 범주 부여 신뢰도는 spot-sample .96 이상이다.
- Bolotova 2022 는 예비 연구에서 Tawfik, Graesser 외(2020) 분류를 연구 조정자끼리 적용했더니 일치가 매우 낮았다고 적는다(§1, 수치 없음). 그래서 문헌 통합, 800문항 포화, 크라우드 라벨(Fleiss κ 0.54), 자유 군집과 V-measure 0.6 비교로 6범주를 다시 세웠다(§3).

### KG 적용

- KGQA 벤치마크 분류는 Lehnert·Graesser 계보를 인용하지 않는다(저장 원문 grep 0건). 구조 패턴과 연산만으로 질문을 나눈다.
- GrailQA 의 온톨로지 순회 생성법은 Su et al. 2016(GraphQuestions)의 것을 재사용했다(§3). 학습에 없던 관계를 쓰는 질문을 zero-shot 일반화 수준으로 둔다(§2).
- TimeQuestions 의 범주는 저자가 손으로 붙였다. 규칙 태거는 모델 입력용이고 정확도 약 90% 다. '언제부터' 는 범주가 아니라 시간 신호 START 로 표현된다.
- PolyG 는 중첩 질문의 안쪽이 ⟨s,p,*⟩ 패턴만 될 수 있다고 관찰한다(§3). 기존 벤치마크가 8 패턴 가운데 2개만 덮는다고 분석한다.
- Typed-RAG(XLLM@ACL 2025)는 Bolotova 6범주마다 다른 검색·분해 전략을 쓴다. Reason 과 Instruction 은 여러 측면으로 쪼갠다(§3.4).
- Cardona-Rivera 외 2016 은 계획기가 만든 서사 표상을 QUEST 구조로 바꾸고 사람 답 판단을 예측하는지 실험했다. 기계가 만든 그래프에 QUEST 경로 규칙을 얹은 후속 사례다.

### 한계

- QUEST 의 why(goal) 경로는 답 집합 넷 가운데 상위 목표와 형제 노드 둘만 논문이 다룬다(p.742). enable·when 질문 경로는 이 논문에서 명세하지 않고 다른 보고서로 미룬다(p.743).
- Lehnert 범주는 Conceptual Dependency 파싱을 전제한다.
- Bolotova 의 EXPERIENCE 범주는 분류 F1 0.653 으로 낮다(Table 6).

### 예문 분해

예문에 대해 사람이 물을 법한 질문을 범주와 경로로 나눈다.

| 질문 | Lehnert 범주 | QUEST 식 경로 | KG 패턴 |
|---|---|---|---|
| 왜 호가 끊겼나 | Causal Antecedent | 인과 사슬 역방향(backward Consequence) | ⟨호 끊김, causedBy, *⟩ |
| 어느 통신사에서 났나 | Concept Completion | 장소 arc 뒤 Isa 로 '통신사' 확인 | ⟨이슈, 망, *⟩ + 답 타입 통신사 |
| 언제 끊겼나 | Concept Completion (시간) | Temporal arc (during 핸드오버) | TimeQuestions Implicit |
| 왜 핸드오버를 했나 | Goal Orientation | forward Reason(상위 목표) | 보고서에 없으면 답 없음 |
| 왜 재설정이 성공하지 않았나 | Expectational | 기대 규격 노드가 필요 | 보고서 밖 지식 |
| 몇 건이 이랬나 | Quantification | 집합 뒤 count | LC-QuAD count |

## 11. 의미 기억 모델

개념이 기억 속에 어떻게 놓이고 어떻게 꺼내지는지를 다루는 심리학 갈래다. 기억 체계, 관계 종류, 검색 과정의 세 축을 준다.

### 분류의 칸

| 모형 | 칸 (원문 이름) | 한 줄 정의 |
|---|---|---|
| Tulving 1972 | episodic memory, semantic memory | 날짜가 붙은 사건과 그 시간·공간 관계를 담는 기억과, 낱말·뜻·관계·규칙을 담는 "mental thesaurus" 를 나눈다 |
| Ortony 1975 | 사건 중심 지식, 개념 중심 지식 | episodic/semantic 을 기억 장치가 아니라 지식 내용의 차이로 본다 |
| Collins & Quillian 1969 | is-a 계층, 속성, 상속 (원문 미열람, 2차 기술의 이름) | 속성은 참인 가장 일반적인 수준에 한 번 적고 아래 노드가 물려받는다. 예외는 아래 노드에 적어 덮어쓴다 |
| Smith, Shoben & Rips 1974 | defining feature, characteristic feature | 개념은 특징 집합이다. 1단계는 모든 특징의 유사도를, 2단계는 defining 특징만 비교한다 |
| Collins & Loftus 1975 | spreading activation, 연결 강도 | 엄격한 계층 조건을 떼고, 활성이 가중치 있는 연결을 따라 퍼지며 거리에 따라 약해진다고 본다 |
| Mirman, Landrigan & Britt 2017 | taxonomic, thematic | 공유 특징에 기반한 유사 관계(dog–bear)와 사건 속 공동 출현에 기반한 인접 관계(dog–leash) |
| Estes, Golonka & Jones 2011 | temporal, spatial, causal, functional | thematic 관계의 하위 유형이다. 단순 연상, script, ad hoc 범주와 구별한다 |
| McRae 외 2005 | 지식 유형 9종: 시각 3, 다른 감각 4, function, encyclopedic | 사람이 나열한 개념 특징을 처리 영역별 유형으로 나눈다 |
| Wu & Barsalou 2009 | taxonomic category, entity, situational, introspective property(37 세부 코드) | 속성을 분류, 개체 자체, 상황 속 관계, 평가·내성으로 나눈다 |
| Steyvers & Tenenbaum 2005 | small-world, scale-free, hub | 관계를 나누지 않고 망 전체의 모양을 잰다 |
| Rogers & McClelland 2008 | Relation 문맥(ISA, is, can, has), progressive differentiation | 명시 노드 없이 분산 표상의 가중치에서 계층이 넓은 구분부터 좁은 구분으로 생겨난다 |

상속 계층은 같은 속성을 여러 노드에 되풀이해 적지 않아 저장을 아낀다. Steyvers & Tenenbaum 은 이 구조를 기본 지식을 적는 "particularly economical system" 이라고 적는다(투고 원고 서론). spreading activation(활성 확산)은 한 개념이 활성되면 이웃, 이웃의 이웃으로 활성이 번지는 검색 과정이다.

small-world 는 연결이 드문데도 평균 경로가 짧고 이웃끼리 잘 뭉친 망이다. scale-free 는 소수 hub 가 연결 대부분을 가진 망이다.

### 근거

- Tulving 1972 는 개념 논증이다. episodic memory 가 "temporally dated episodes or events" 를 담는다고 정의하고 두 체계의 차이 다섯 가지를 든다(p.385). 어느 과제가 어느 쪽인지는 질의의 종류, 꺼낼 정보의 성격, 기억 주장의 성격에 달렸다고 적는다(p.386).
- Tulving 은 1987 Citation Classic 에서 이 구분이 "not at all original" 이었고 철학자와 기억 병리 연구자가 이미 비슷한 생각을 했다고 스스로 적는다.
- Ortony 1975 도 실험 없는 입장 논문이고, Schank 의 반론에 답한다. 두 기억의 차이를 "a difference not so much between different kinds of memory but between different kinds of knowledge in memory" 로 본다(p.56).
- Ortony 는 semantic 지식을 사건 중심으로 부호화된 지식을 개념 중심으로 재조직한 것으로 정의하고(p.57), 이 변환을 "produce an encyclopaedia from his personal diary" 에 빗댄다.
- Collins & Quillian 1969 는 문장 참·거짓 검증 반응시간으로 섰다. 교재 해설(Computers and Thought 6장 Table 6.1)이 옮긴 근삿값은 'is a canary' 1.00초, 'is a bird' 1.17초, 'is an animal' 1.23초, 'can sing' 1.3초, 'can fly' 1.38초, 'has skin' 1.47초다. 거칠 링크가 많을수록 느려진다. 원문 표와는 대조하지 못했다.
- 같은 교재는 Conrad 1972 와 Smith, Shoben & Rips 1974 가 이 모형의 당시 형태에 "raised doubts" 라고 적는다. Cedrus 실험 해설은 Rips 외 1973 이 범주 경계를 넘는 문장에서 거리 효과가 늘 나오지는 않았다고 보고했고, bird 대신 mammal 범주를 쓴 경우 "the effect was reversed" 였다고 적는다.
- Shoben 외 1978(ERIC ED159662)은 Glass & Holyoak 의 Marker-Search 모형에 대한 응답이다. 특징 모형의 1단계는 "compares all of the features" 하고(p.14), 2단계는 "considers only the more defining features" 한다(p.15). 저자들은 부분집합 명제를 미리 저장하는지 그때 계산하는지로 Computation 모형과 Pre-storage 모형을 가른다.
- Collins & Loftus 1975 는 이론 논문이다. ERIC 초록은 이 논문이 Quillian 의 이론을 "reviewed ... while trying to correct some common misunderstandings" 했고 Smith, Shoben & Rips 1974 의 특징 모형과 비교했다고 적는다. Pavlovic 외 2025 §2.3 은 이 수정판이 망이 엄격한 계층이어야 한다는 조건을 떼고 연결 강도 차이와 거리에 따른 활성 감쇠를 넣었다고 기술한다. 위 표의 Collins & Loftus 정의는 이 2차 기술에 기댄다.
- SWOW(De Deyne 외 2019)는 단서 12,292개에 83,864명이 낸 연상으로 망을 만들었다. 받은 파일은 저자 원고라서 이 절의 SWOW 쪽 번호는 원고 쪽이고 학술지 쪽(987–1006)과 다르다. 직접 연상 강도, PPMI, 감쇠 random walk 세 척도로 유사도·관련도 판단 자료 일곱 개를 예측했고, random walk 는 "always performs at least as well as the PPMI measure, but usually performs better" 였다(p.18). PPMI(positive pointwise mutual information)는 한 단서에 대한 반응 분포 전체를 고려하지만 그 단서의 반응만 보는 국소 연관 척도다(p.16).
- SWOW 의 random walk 는 길이 최대 3, 감쇠 계수 α<1 로 짧은 경로를 크게 센다. 저자는 이것이 Katz index(길이별로 감쇠한 모든 경로 수를 더한 노드 유사도)와 가깝다고 적는다(p.17). 같은 논문은 Collins & Loftus 를 인용하며 활성 확산을 "a node activates not only its neighboring nodes, but also the neighbors of these neighbors" 로 기술한다(p.16).
- Mirman 2017 은 행동·계산·신경 증거를 모은 체계적 리뷰다. "about a dozen independent studies" 가 ATL(앞 측두엽)–taxonomic, TPC(측두-두정 피질)–thematic 해리를 지지한다. 저자 스스로 이것이 검토한 28개 연구의 절반이 안 된다고 적는다(Summary of Neural Evidence 절). triad 선호 결과는 #7 분류 방법론 에 있다.
- McRae 2005 의 수집 절차는 #7 분류 방법론 에 있다. 원문은 dog 와 table 에서 뜻이 다른 'has legs' 의 이름을 나누지 않으면서 "we did not alter feature names to avoid potential ambiguity" 라고 적고, 선을 어디에 그을지 분명하지 않았다고 덧붙인다(p.551).
- Wu & Barsalou 2009 는 두 코더가 37 세부 코드 수준에서 91% 일치했다고 보고한다. 속성 나열 지시와 단어 연상 지시는 다른 속성 분포를 냈다(초록). 각주 2 는 이 코딩 체계가 그 뒤 "has evolved" 했다고 적는다.
- Steyvers & Tenenbaum 2005 는 Nelson 자유 연상, WordNet, Roget 시소러스가 모두 small-world·scale-free 라고 보였다. 저자는 이 구조가 "not consistent with many conventional models of semantic organization, based on inheritance hierarchies" 라고 적는다(초록). 같은 문장은 상속 계층과 함께 임의 구조 망(Collins & Loftus 식)과 고차원 벡터 공간 모형도 든다.
- 같은 논문의 무방향 연상망은 5천여 낱말에서 평균 경로가 3, 최대가 5 다(투고 원고 p.10). 받은 파일은 게재본이 아니라 "(Submitted to Cognitive Science)" 원고라서 쪽 번호가 학술지 쪽(41–78)과 다르다.
- Rogers & McClelland 2008 은 연결주의 시뮬레이션을 발달·의미 치매 자료와 대조한다. 내부 표상 단위는 "have no explicit content in themselves" 다(p.693). 새 사물의 표상은 해마의 빠른 학습 체계에 먼저 저장되고, 되풀이되면 신피질 연결 가중치에 서서히 통합된다고 본다(§5 원리 7, p.713).
- 이 2단 저장의 이름인 complementary learning systems 는 Rogers & McClelland 본문에 없고 참고문헌의 McClelland 외 1995 제목에만 나온다.

### KG 적용

- CoALA(Sumers 외, TMLR 2024)는 episodic·semantic 구분을 에이전트 기억에 쓴다. "Episodic memory stores experience from earlier decision cycles."(§4.1, p.9). 받은 원문은 이 구분을 Soar 의 기억 체계에서 가져오고 Tulving 을 인용하지 않는다(§2). Generative Agents 의 reflection, 곧 episodic 기억에서 일반화한 문장을 semantic 기억에 쓰는 일을 이 틀로 분류한다(p.14). 다른 칸은 #6 공학 쪽 KG 유형론 에 있다.
- CoALA 는 procedural 기억 쓰기가 episodic·semantic 쓰기보다 "significantly riskier" 하다고 본다(p.10).
- Tulving 은 "any act of retrieval constitutes an input into episodic memory" 라고 적는다(p.386). [추정] 이 말대로면 질문 경로 로그는 보고서와도 용어집과도 다른 episodic 층(검색 사건)이다(사례: CoALA 가 경험 궤적을 episodic 기억으로 둔 것, Zep 이 원문을 episode 로 따로 둔 것, 2건).
- Pavlovic, Krész & Hajdu 2025(arXiv 2512.15922v2)는 활성 확산을 KG 기반 RAG 검색에 썼다. 질의와 맞는 seed 엔티티에서 BFS 로 활성을 넘기고 임계값 τa 를 넘은 노드만 활성으로 본다(Algorithm 1). BFS(breadth-first search)는 가까운 이웃부터 한 겹씩 넓혀 가며 도는 그래프 탐색이다. 간선 가중치는 "the cosine similarity between the query and the link embedding" 이고(§5.4), 확산 전에 계수 c 로 재조정한다(c = 0.4, §5.5).
- 같은 논문 §2.3 은 제약 없는 활성 확산이 "converges to a fixed state and retrieval results become nearly independent of the input query" 라는 선행 결과를 들고, 그래서 hop 제한 같은 제약이 질의에 맞는 결과에 필수라고 정리한다. 이 논문 자신은 n-hop 부분 그래프(§5.4), 가중치 재조정 c, 임계값 τa(§5.5)로 확산을 묶는다. §2.3 은 관계 유형별로 가중치를 두는 온톨로지 기반 활성 확산 변형도 소개한다.
- Pavlovic 은 MuSiQue 와 2WikiMultiHopQA 에서 chain-of-thought 반복 검색과 결합한 결과를 낸다. 둘은 여러 문서를 거쳐야 답이 나오는 multi-hop 질문 벤치마크다. 초록은 naive RAG 대비 "up to a 39% absolute improvement in answer correctness" 라고 적고, 기여 목록은 그 폭을 25%–39% 로 적는다. 초록은 이 방식이 "avoids LLM-guided graph traversal" 한다고 적는다. [추정] 그래서 같은 질문과 같은 그래프면 같은 확산 경로가 나온다(사례: Algorithm 1 이 고정 가중치·임계값과 BFS 로만 도는 것, 1건).
- HippoRAG(Gutiérrez 외 2024, arXiv 2405.14831)는 KG 위 Personalized PageRank 를 "inspired by the hippocampal indexing theory" 라고 소개한다(초록). Personalized PageRank 는 seed 노드로 되돌아가는 확률을 둔 random walk 로 노드 점수를 매기는 알고리즘이다. 본문은 열지 않았다.
- Hansen & Hebart 2022 는 GPT-3 로 THINGS(구체 사물 개념 1,854개를 모은 데이터베이스)의 개념마다 특징을 만들었다. 사람 특징 규범(McRae 와 CSLB, 곧 Centre for Speech, Language and the Brain 규범)과 겹치는 개념 317개에서 특징 500개, 그 밖의 개념에서 500개를 뽑아 특징 유형을 손으로 표지했다. 결과는 #7 분류 방법론 에 있다.
- [추정] 연상 간선과 특징·사건 간선은 같은 간선 종류로 섞지 않는 편이 맞다(사례: Wu & Barsalou 에서 속성 나열과 단어 연상이 다른 분포를 낸 것, Estes 외가 thematic 관계를 단순 연상과 구별한 것, 2건).

### 한계

- Collins & Quillian 1969, Rips 외 1973, Smith 외 1974, Collins & Loftus 1975 원문은 열지 못했다. 반응시간은 교재의 근삿값이고, Collins & Loftus 는 ERIC 초록과 2차 기술(SWOW, Pavlovic)로만 읽었다.
- Steyvers & Tenenbaum 은 상속 계층이 "clearly appropriate only for certain taxonomically organized concepts" 라고 적는다(투고 원고 서론).
- 실험 자료는 거의 구체 사물 개념이다(McRae 541개, Hansen & Hebart 의 THINGS 1,854개). 장애·절차 같은 추상 개념은 없다.
- Mirman 의 신경 해리 증거는 혼재한다. 지지 연구가 검토한 28개의 절반이 안 된다.
- Tulving 1972 와 Ortony 1975 는 개념 논증이고 실험이 없다. Tulving 은 24쪽 이미지 가운데 p.385–386 두 쪽만 읽었다.
- SWOW 간선에는 관계 유형이 없어 taxonomic 과 thematic 이 섞이고, 어휘는 영어 일반어다. 원문은 한국어 연상 규범(Jung, Na & Akama 2010, 단서 3,900개)을 언급한다(원고 p.2).
- Pavlovic 의 KG 는 LLM 이 자동으로 만들고, 엔티티 사이 간선은 related_to 한 종류에 관계 설명 문자열을 속성으로 붙인 것이다(§5.3). 저자는 기성 임베딩 모델의 cosine 값을 선형 재조정만 해서 가중치로 쓴 점을 한계로 든다(결론). 평가는 벤치마크마다 무작위 100문항이고, 실험 모델은 phi4 와 gemma3 다(결론, Table 1). [추정] 그래서 사내 운영 모델(Qwen 32B 급, #사내 보고서 용어집에 비추어)에 결과를 그대로 옮길 근거로는 약하다(사례: 100문항 표본, 다른 모델 두 개, 2건).
- Rogers & McClelland 의 내부 표상은 사람이 읽을 수 없어서 감사 가능한 용어집과 성격이 반대다. 모형 규모도 나무·새·물고기 명제 수준이다.

### 예문 분해

아래 분해도 작성자가 이 갈래의 칸에 맞춰 손으로 만든 예시이고, 실제 시스템을 돌린 결과가 아니다.

- 기억 체계: 이 문장이 든 보고서는 작성자·날짜·장비에 묶인 episodic 항목이다. 'RRC 재설정 실패는 호 끊김을 일으킬 수 있다' 는 여러 보고서에서 끌어올린 semantic 명제이고, 근거 보고서 링크를 붙여 둔다(Ortony 의 재조직).
- 상속 층(taxonomic): 'SKT' → '통신사', '5G NR 단말' → '단말'. '통신사' 수준에 '망 운영 주체' 같은 공통 속성을 한 번 적고, MVNO 처럼 어긋나는 경우는 아래 노드에 예외로 적는다.
- 사건 층(thematic, Estes 하위 유형): '기지국'–'핸드오버' 는 공간, '핸드오버'–'RRC 재설정 실패' 는 시간(중에), 'RRC 재설정 실패'–'호 끊김' 은 인과다.
- 속성(Wu & Barsalou 식): 'RRC 재설정 실패' 의 entity 속성은 'RRC 계층의 절차 실패', situational 속성은 '핸드오버 중에 난다' 다. 보고서에 '단말 쪽 원인으로 보인다' 가 있으면 introspective(작성자 판단)로 두고 사실 간선과 가른다.
- defining/characteristic: '핸드오버 장애' 의 defining 특징은 '셀 전환 절차 중 실패', characteristic 특징은 'RRC 재설정 실패를 동반' 이다.
- 활성 확산: 질문 '왜 SKT 에서 호가 끊겼나' 는 용어집 항목 'SKT', '호 끊김' 을 seed 로 삼는다. 활성은 '호 끊김' → 'RRC 재설정 실패'(1 hop) → '핸드오버'(2 hop) 로 퍼진다. seed, hop 별 활성값, 통과 간선이 그대로 질문 경로 기록이 된다.
- [추정] '기지국', '단말' 같은 hub 를 감쇠나 정규화 없이 지나면 질문과 무관한 노드가 대량으로 활성된다(사례: Pavlovic §2.3 의 고정 상태 수렴, Steyvers & Tenenbaum 의 hub 구조, 2건).

## 갈래 비교

| # | 나누는 대상 | 구조 모양 | 근거 종류 | 검증 방법 | 사용자 문제와 닿는 곳 |
|---|---|---|---|---|---|
| 1 | 범주 소속, 계층 수준 | 정도 있음, 맥락 의존 | 실험 | 사람 평정 상관, 4단계 라벨 | 추상화 수준(basic level), 대표 예 |
| 2 | 낱말 뜻과 관계 | 엄격 계층 + frame 지역 역할 | 언어 자료 | 시험 문장 틀, 이중 주석 κ, gold 매핑 P/R | 형태 관계와 뜻 관계 분리, 부분-전체 유형 |
| 3 | 최상위 범주 | 엄격 계층 | 철학 논증 | OntoClean, anti-pattern SPARQL, 일치도 | type/role, instance/subclass 구분 |
| 4 | 개념과 이름 | 엄격 계층 + 변이 기술 | 표준 합의, 언어 자료 | 무결성 조건, qSKOS, warrant | 선호어·변이어, 거버넌스 |
| 5 | 관계의 지식 유형, 사건 | 위계 + 맥락 차원 | 언어 자료, 공학, 일부 실험 | 하위 과제 ablation, 일치도 | 원인·순서·조치 관계, 맥락 차원 |
| 6 | KG 층, 기억 체계 | 층 구분 | 공학 편의 | 벤치마크 | 원문 episode 와 정규화 사실 분리 |
| 7 | (절차) | — | 실험, 공학 | α, CQ test, 카드 상관 | 분류를 시험하는 절차 |
| 8 | 한국어 의미 부류, 변이 | 엄격 계층 + 결합 정의 | 언어 자료, 규범 | 수작업 매핑 F1 | 한국어 변이 유형, 승인 절차 |
| 9 | 장애·자원·판정 | 직교 속성 + 계층 identity | 공학 편의 | CQ, RCA 벤치마크 | 장애 노드 유형, 표준 어휘 |
| 10 | 질문 | 범주 → 경로 | 실험, 공학 | 답 생성 분산, κ | 질문 경로 기록의 라벨 |
| 11 | 기억 체계, 관계 종류, 검색 | 상속 계층 → 가중 연상망 | 실험, 개념 논증 | 검증 반응시간, 코더 일치, 연상망의 유사도 예측 | 보고서·용어집 층 구분, taxonomic/thematic 간선, 활성 확산 검색과 경로 기록 |

### 표 밖 해석

엄격 계층 쪽(3, 4, 9)은 검사 도구가 많지만, 근거는 철학 논증과 합의에 그친다. 정도·맥락 쪽(1, 5, 11)은 실험 근거가 있다. [추정] 그러나 KG 에 들어간 형태는 점수 칸이나 맥락 태그 정도로 얇다(사례: Probase 의 typicality 칸, EventKG 의 관계 유효 기간 속성, Hogan 의 context 주석, 3건).

[추정] 두 쪽은 경쟁하지 않고 층을 나눠 함께 쓰인다(사례: Probase 가 크리스프 isA 위에 typicality 를 얹은 것, NORIA-O 가 SKOS 계층 위에 관점별 scheme 을 둔 것, EcoLexicon 이 계층 관계 위에 명제 단위 문맥 제약을 건 것, 3건).

[추정] 인지 실험과 KG 경로를 직접 잇는 갈래는 10 과 11 이다(사례: QUEST 의 질문 범주별 arc 규칙, SWOW 연상망 random walk 의 유사도 예측, Pavlovic 의 KG 위 활성 확산, 3건). 10 은 질문 범주로 경로의 모양을 정하고, 11 은 seed 에서 경로를 펼치는 검색 과정을 준다. [추정] 질문 범주가 관계 유형을 정한다는 QUEST 의 결과는 갈래 2·5·9 의 관계 목록을 '어느 질문이 이 관계를 쓰나'로 정당화할 길을 준다(사례: QUEST 의 질문 범주별 arc 규칙, Cardona-Rivera 외 2016 의 계획기 그래프 적용, 2건).

변이(같은 개념, 다른 이름)는 갈래 2·4·8·9 가 따로따로 다룬다. 넷 다 개념과 표기를 다른 자원으로 두는 데는 일치한다. 차이는 변이에 종류 라벨을 다느냐(OntoLex, Freixa, 최기선·박정원)와 정규형을 누가 정하느냐(국어기본법, 3GPP, 우리말샘)에 있다.

갈래 6 의 층 구분(원문 episode 와 정규화 사실)은 공학 편의로 분류했다. CoALA 는 이 구분을 Soar 에서 가져오고 Tulving 을 인용하지 않는다(CoALA §2). 같은 구분의 심리학 쪽 논증은 11 의 Tulving 1972 와 Ortony 1975 에 있지만, 둘 다 실험이 아니라 개념 논증이라서 갈래 6 의 근거 종류는 바뀌지 않는다.

[추정] taxonomic/thematic 구분(11, Mirman 2017)은 갈래 5 의 개체 대 사건 구분과 #7 의 triad 과제를 같은 축 위에 놓는다(사례: Mirman 이 thematic 을 사건·장면 속 공동 출현으로 정의한 것, Estes 외가 thematic 을 시간·공간·인과·기능 관계로 나눈 것, Mirman 이 triad 선호를 이 두 쪽으로 정리한 것, 3건). 신경 근거는 검토 연구의 절반이 안 되는 지지로 혼재한다.

## 방법론

분류를 세우고 검증하는 단계를 원문 수치로 정리한다. 사람·건수 칸은 원문이 쓴 규모다.

| 단계 | 방법 | 재는 것 | 사람·건수 | 잡는 실패 |
|---|---|---|---|---|
| 1 범위 | CQ, ORSD pre-glossary | 분류가 답해야 할 질문과 그 용어 빈도 | 도메인 전문가 패널(NORIA-O 26 CQ) | 질문에 쓰이지 않는 범주 |
| 2 후보 | free listing + Monte Carlo 현저성 | 우연보다 현저한 항목 | 예: 153개 목록 | 개인 특유 용어를 상위 범주로 올림 |
| 3 특징 | 특징 규범 | 범주를 가르는 특징, 정의 초안 | 개념당 30명, 5/30 컷오프 | 정의가 없는 표제어 |
| 4 연관 | 단어 연상 R1/R123 | 약한 연상, 빠진 관련어 | 단서당 100명 × 3응답 | 용어집에 없는 동의어·관련어 |
| 5 묶음 | open card sort, 이어서 closed sort | 사람 머릿속 범주와 제안 범주의 일치 | 15명 r .90, 30명 r .95 | 작성자 범주와 어긋난 추상화 |
| 6 축 성향 | triad 과제 | taxonomic 대 thematic 선호 | 북미 대학생 약 80% 가 한쪽 선호 | is-a 와 '같이 나옴'을 한 관계로 섞음 |
| 7 계층 검사 | OntoClean, OOPS!, SKOS 무결성, qSKOS, AP1/AP2 SPARQL | 구조 위반 수 | 자동(메타속성 태깅은 사람) | role 이 type 을 subsume, instance/subclass 혼동, 라벨 충돌, 순환 |
| 8 주석 일치 | 지침 + 독립 코더 + Krippendorff α | 범주를 배울 수 있고 구별되나 | 3명 이상, α ≥ .8 기준 | 정의가 흐린 범주(낮은 α 항목) |
| 9 질문 정답 | CQ → SPARQL unit test, 역추적 정답 + 난이도 | 경로가 답에 닿나 | CQ 수십 개 | 분류는 맞는데 질문을 못 푸는 구조 |
| 10 LLM 대조 | hard negative 질문, Spearman ρ, 30회 실행 빈도 | LLM 이 사람 판단을 대신할 수 있나 | 소수 항목 사람 평정 | 전문 분야·잎 수준 오류, 반의어 병합 |
| 11 정규형 | warrant, 대역어 지침 순서 | 어느 표기를 선호어로 둘지 | 부서 담당자 + 확정 위원 | 근거 없는 선호어, 강제 병합 |
| 12 망 모양 | 평균 경로, 군집 계수, 차수 분포 | 만든 KG 가 사람 의미망처럼 small-world 인가, hub 가 어디인가 | 연상망 5천여 낱말에서 평균 경로 3 | tree 계층만으로 짠 망, 확산을 흐리는 hub |

단계 8 에서 범주가 계층이면 상위만 맞힌 경우를 부분 일치로 보는 가중 α 가 맞다(Artstein & Poesio §5.2). 계층 거리를 반영한 표준 척도는 아직 없다고 Hois 2010 이 적는다(§4).

PDTB 2.0 은 하위 단계에서 두 주석자가 갈리면 바로 위 단계 태그를 주었다(§3). 두 해석이 모두 가능하다고 보았기 때문이다. 단계 8 에서 이 규칙을 빌릴 수 있다.

단계 3·4·6 의 원문(McRae 2005, SWOW 2019, Mirman 2017)이 무엇을 나누는지는 #11 의미 기억 모델 에 있다. 단계 3 의 특징 유형 체계 자체도 코더 일치로 검증할 수 있다. Wu & Barsalou 2009 는 두 코더의 세부 코드 일치율 91% 를 보고했다. 단계 8 의 α 기준으로 다시 재려면 코더를 셋 이상으로 늘려야 한다. 단계 12 의 기준값은 Steyvers & Tenenbaum 2005(투고 원고 p.10)다.

## 사내 보고서 용어집에 비추어

조건은 다음과 같다. 여러 작성자가 쓴 네트워크 검증 보고서를 잇는다. 용어가 작성자마다 다르고 형식 없는 문서가 섞여 있다. 사람이 용어집을 관리하고 추상화(skt·kt·verizon → 통신사, 2025 → 연도)를 둔다. 질문이 정답을 찾은 경로를 기록한다. 운영 모델은 Qwen 32B 급이다.

### 권하는 축

[추정] 분류 노력을 *관계 유형* 축에 쓰고, 질문 경로가 따라가는 관계를 기준으로 관계 목록을 세우기를 권한다(사례: QUEST 가 질문 범주마다 합법 arc 를 정하고, 그 위에서 경로 방향과 거리 감쇠만 둔 세 매개변수 모형이 답 생성 점수 분산의 89% 를 설명한 것(1990 ONR 보고서), Lehnert 가 범주마다 다른 탐색 heuristic 을 둔 것, TN-AutoRCA·NORIA-O 가 장애 질문을 dependOn·generate·causedBy 같은 소수 관계로 푼 것, 3건).

이유는 세 가지다.

- 사용자가 기록하려는 질문 경로는 곧 관계 경로다. 관계 유형을 질문 범주에서 정하면 경로 기록이 분류 검증 데이터가 된다. Z39.19 의 user warrant 와 같은 자료를 쓰는 셈이다.
- [추정] 노드 범주와 이름 쪽은 이미 표준이 정해 준 칸이 있어 새로 분류할 일이 적다(사례: ISO 25964 개념·용어 분리, TBX entry, 3GPP 용어 지위, OntoClean type/role, 4건). 이것들은 분류 축이라기보다 용어집이 따라야 할 기반 규칙이다.
- [추정] 원인과 시간 순서, 조치와 선행조건을 한 관계로 섞는 것이 이 도메인의 가장 흔한 오답 경로가 될 것이다(사례: ASER 의 Precedence–Causes 겹침, Lehnert 의 Instrumental 과 Enablement 혼동 예, Winston 의 부분-전체 transitivity 실패, 3건).

[추정] #11 의미 기억 모델 을 더해도 권하는 축은 바뀌지 않는다. Mirman 2017 의 taxonomic·thematic 구분이 관계 유형의 첫 가름에 행동·신경 근거를 대서 이 축을 받치기 때문이다(사례: triad 선호에서 북미 대학생 약 80% 가 한쪽을 믿을 만하게 고른 것, 십여 개 독립 연구("about a dozen")의 ATL–TPC 해리, 2건). 다만 신경 근거는 검토 연구 28개의 절반이 안 된다.

이 축을 흔드는 쪽은 SWOW 다. 관계 유형이 없는 연상망에서 감쇠 random walk 가 사람 유사도·관련도 판단을 견준 세 척도 가운데 늘 가장 낫거나 같게 예측했다(De Deyne 외 2019 원고 p.18). [추정] 무표지 확산은 질문 낱말과 보고서 낱말 사이 후보를 넓히는 데 맞고, 답에 이르는 경로는 관계 유형이 정한다(사례: SWOW 가 예측한 대상이 유사도·관련도 판단이었던 것, QUEST 가 질문 범주마다 arc 를 정한 것, 2건). 아래 #시험할 실험 의 검색 판(E5)이 이 갈림을 시험한다.

권하는 축 아래에 둘 기반 규칙은 다음과 같다. 개별 통신사·연도는 instance 로 잇고 subclass 로 두지 않는다. '통신사' 는 회사의 role 로 둔다. 용어집 추상화는 taxonomic 상속 층에, 보고서 속 사건 관계는 thematic 간선에 따로 둔다. 표기 변이는 개념이 아니라 라벨 쪽에 두고 변이 종류를 단다. 원문 보고서는 episode 로 보존하고 맥락(작성자, 날짜, 망, 펌웨어, 관찰/추정)은 명제 단위로 붙인다.

### 다른 선택을 할 조건

| 조건 | 고를 축 |
|---|---|
| 질문 로그 대부분이 조회·집계(Concept Completion, count)다 | 노드 범주 축. 답 타입(Li & Roth 식) 정리로 충분하다 |
| 우산 개념('상호운용 이슈')을 두고 작성자 사이 정의 다툼이 잦다 | 범주 구조 축. 대표 예와 대표성 점수를 얹는다(Temmerman, Probase) |
| 같은 진술이 통신사·펌웨어·시험 환경마다 참·거짓이 갈리는 일이 많다 | 맥락 축. Cyc 식 차원이나 Hogan context 를 1급으로 둔다 |
| 사람이 관계 라벨에 합의하지 못한다(α 가 낮다) | 관계를 2단 위계로 줄이고 확신 없으면 상위로 물러선다(PDTB) |

### 시험할 실험

모두 구조가 다른 판끼리 같은 질문 세트로 견준다. 질문 세트는 실제 보고서에서 뽑은 질문에 Lehnert 범주를 붙인 것이다. 실험 비교 모델은 Haiku, 운영 확인은 Qwen 32B, 결과 검토는 Opus 로 둔다.

| 실험 | 판 | 재는 것 |
|---|---|---|
| E1 관계 판 | (a) 관계 하나(related) (b) 담화 4범주 2단 위계 + 상위 물러서기 (c) 장애 개념 판(Event/State/Symptom/Cause 노드 + dependOn·generate·causedBy) | 질문 범주별 정답률, 경로 길이, 잘못된 경로 유형(인과와 순서 혼동 등) |
| E2 용어집 표현 판 | (a) 평면 동의어 목록 (b) 개념·라벨 분리 + 변이 종류 태그(형태 변이, 번역 변이, 관점 변이) (c) (b) + instance 와 generic 계층 분리 | 병합 정밀도·재현, 잘못 합친 쌍(약어 다의, 상이 원어 동일 번역), 추상화 질문 정답률 |
| E3 맥락 판 | (a) 맥락 없이 사실 병합 (b) 두 시간축 + 새 사실 우선 무효화(Zep 식) (c) 명제 단위 맥락 태그(망, 펌웨어, 시험 환경, 관찰/추정) | 상충 보고서 질문 정답, 잘못 지운 사실 수 |
| E4 범주 소속 판 | (a) 크리스프 계층만 (b) (a) + 대표성 점수와 basic-level 표시 | 추상화 질문 답의 수준 적합성(Wang 2015 의 4단계 라벨로 사람 판정) |
| E5 검색 판 | (a) 임베딩 top-k 문서 검색 (b) 용어집 seed + 제약된 활성 확산(hop, 임계값, 감쇠), 간선 무표지 (c) (b) + 간선 종류별 가중치(taxonomic·thematic 을 질문 범주로 고름) (d) (c) + 되풀이된 질문 경로 빈도로 가중치 갱신 | 질문 범주별 정답률, 질문과 무관하게 활성된 노드 수(hub 경유), 같은 질문 재실행 때 경로 일치율, (d) 갱신 전후 정답률 |

E1 과 E2 는 권한 축을 직접 시험한다. E1 의 (a) 가 (b)·(c) 와 질문 범주별로 차이가 없으면 관계 축 권고는 접는다. E5 의 (c) 가 (b) 보다 낫지 않으면 관계 유형은 검색 가중치에 쓰지 않고 답 경로 해석에만 쓴다.

E5 를 더한 까닭은 활성 확산의 seed, hop 별 활성값, 통과 간선이 그대로 질문 경로 기록이 되기 때문이다. 검색과 기록이 같은 자료 구조를 쓰고, LLM 이 순회를 이끌지 않아 같은 질문을 다시 돌려 경로를 견줄 수 있다.

(d) 는 되풀이된 경로만 가중치로 굳히는 판이다. [추정] 이 판은 Ortony 의 사건 중심 → 개념 중심 재조직과, Rogers & McClelland 가 기술한 빠른 저장 → 되풀이 뒤 느린 통합에 대응한다(사례: Ortony p.57 의 일기 → 백과사전 비유, Rogers & McClelland §5 원리 7, 2건). 이 2단 저장 근거의 원전(McClelland 외 1995)은 읽지 않았고, 검색 로그로 간선 가중치를 갱신해 효과를 잰 연구도 찾지 못했다.

Pavlovic 2025 결과는 phi4·gemma3 와 벤치마크당 100문항에서 나왔다. 그래서 E5 는 Haiku 비교 뒤 Qwen 32B 에서 다시 잰다.

## 읽는 순서

| 순서 | 문헌 | 읽는 까닭 |
|---|---|---|
| 1 | Hogan et al. 2021 Knowledge Graphs §3 ([arXiv 2003.02320](https://arxiv.org/abs/2003.02320)) | 공학 쪽 기준선. schema·identity·context 의 칸 |
| 2 | Rosch & Mervis 1975, 이어서 Rosch et al. 1976 | prototype 과 basic level 의 실험 근거 |
| 3 | Graesser, Gordon & Brainerd 1992 QUEST | 질문 범주와 그래프 경로를 잇는 원조 |
| 4 | Lehnert 1977 IJCAI 논문, 필요하면 학위논문 Ch.2 | 범주를 처리 절차로 정당화하는 기준 |
| 5 | Guarino & Welty 2004 OntoClean | is-a 검사의 원리 |
| 6 | Z39.19-2005 §8 | 동의·계층·연관 관계와 warrant |
| 7 | OntoLex-Lemon §3, §6 | 낱말·뜻·개체 분리와 변이 관계 |
| 8 | RFC 9940 | 장애 개념의 정의 사슬 |
| 9 | NORIA-O (swj3502) | 통신 장애 KG 에서 SKOS 용어집을 쓴 선례 |
| 10 | Artstein & Poesio 2008 §4–5 | 분류를 일치도로 검증하는 법 |
| 11 | Mirman, Landrigan & Britt 2017 ([PMC5393928](https://pmc.ncbi.nlm.nih.gov/articles/PMC5393928/)) | taxonomic·thematic 관계를 가르는 근거와 그 혼재 |
| 12 | Pavlovic 외 2025 §2.3, §5.4 ([arXiv 2512.15922](https://arxiv.org/abs/2512.15922)) | 활성 확산을 KG 검색에 쓴 구현과 확산을 묶는 제약 |

## 확인하지 못한 것

### 검증에서 원문으로 확인할 수 없던 주장

| 갈래 | 주장 | 까닭 |
|---|---|---|
| 2 | Framester 가 FrameNet Inheritance 를 subclass 로 해석한다 | Framester 원문에 그 문장이 없다 |
| 4 | individual concept 은 generic relation 이 아니라 instance 관계로 두는 것이 ISO 1087 정의와 맞다 | 미리보기 범위에 근거 문장이 없다. Z39.19 §8.3.2 에서 끌어온 추론이다 |
| 4 | Wüster 1979 의 편집자·출판사 | 표제지나 도서관 목록을 열지 못했다 |
| 5 | Lenat 1998 이 Cycorp technical report 다 | 문서 안에 보고서 분류나 번호가 없다 |
| 6 | Rabby et al. 2024 의 게재처 | arXiv 판과 기관 기록만 찾았다 |
| 3 | Dadalto 외 Wikidata 논문의 게재 연도 | 저장본은 Semantic Web 저널 심사본(swj3480)이고 게재 연도가 적혀 있지 않다 |
| 7 | Hansen & Hebart 2022 의 CogSci 2022 게재 | arXiv 페이지와 검색에서 수록 기록을 찾지 못했다 |
| 8 | 권정현 2015 의 자료가 우리말샘 계열이다 | 초록에 근거가 없다 |
| 11 | Rips 외 1973 의 mammal 범주에서 animal 이 mammal 보다 빨리 검증되었다 | 받아 둔 Cedrus 해설과 Shoben 1978 보고서에는 '효과가 뒤집혔다' 까지만 있고 방향이 없다 |
| 11 | Collins & Quillian 1969 가 속성을 한 번만 적는 원리를 cognitive economy 라고 부른다 | 받은 자료(교재 해설, Steyvers & Tenenbaum, Pavlovic)에 그 이름이 없다. Steyvers & Tenenbaum 은 "particularly economical" 이라고만 적는다 |
| 11 | Collins & Loftus 1975 의 호수 (6) | 받은 자료(세 문헌의 참고문헌)는 권과 쪽(82, 407–428)만 적는다 |
| 11 | Ortony 1975 의 쪽 범위 55–60 | 받은 원문의 인쇄 쪽은 59에서 끝난다. ACL Anthology 메타데이터로 확인할 수 있다 |
| 11 | Rogers & McClelland 2008 의 DOI | 파일 안에 S0140525X0800589X 와 S0140525X08005980 두 값이 있다 |
| 11 | Pavlovic 외 2025 의 동료 심사 여부 | arXiv v2 만 받았다 |

### 갈래별로 열지 못한 것

| 갈래 | 항목 | 까닭 |
|---|---|---|
| 1 | Rosch 1975 JEP: General 원문, Rosch 1978, Lakoff 1987 원 책, Wittgenstein §66–67 | 유료이거나 경로 404, 합법 공개본 없음 |
| 1 | Tanaka & Taylor 1991, Hampton 2007 본문, Osherson & Smith 1981, Fuzzy OWL 2 | 열지 않았거나 초록만 봤다 |
| 1 | 운영 KG(Wikidata 등)가 typicality·basic level 을 저장하는지, exemplar 이론을 KG 에 쓴 연구 | 사례를 찾지 못했다 |
| 2 | Miller 1995 CACM, Fillmore 1976·1982, FrameNet 2016 개정판, Levin 1993, Pustejovsky 1995 책, BabelNet 2012 판 | 403·404·응답 없음, 공개본 없음 |
| 2 | Cruse 1986, EuroWordNet top ontology, Mel'čuk lexical functions, Murphy 2003, ISO LMF | 검증이 빠진 중심 문헌으로 지목했다 |
| 3 | Arp, Smith & Spear 2015, CACM OntoClean 2002, ISO 21838 본문, Gärdenfors 2000·2014 책, UFO 2022 판 | 유료·Cloudflare 차단 |
| 3 | Paulheim & Gangemi 2015, ImageSchemaNet 원 논문 | PDF 를 찾지 못했다 |
| 3 | 상위 온톨로지 범주가 LLM 추출 정확도를 높이는지에 대한 실증 | 찾지 못했다 |
| 3 | DOLCE social roles(Masolo 2004), MLT·Brasileiro 2016, SUMO-WordNet 정렬 | 검증이 빠진 문헌으로 지목했다 |
| 4 | ISO 704 5.5 이후 본문, ISO 1087 3.2.23 이후, ISO 25964 본문, ISO 30042 본문 | 유료, 미리보기 범위 밖 |
| 4 | Temmerman 2000 책, Cabré 2003 영어 원문, Freixa 2006 본문, Daille 2005·2017, EcoLexicon 관계별 정의 | 유료·봇 차단 |
| 4 | Sager 1990, Nuopponen 2010, Meyer 1997, L'Homme 2020, Reineke & Romary 2019 | 검증이 빠진 문헌으로 지목했다 |
| 5 | Vendler 1957 원문, Bach 1986, Mourelatos 1978, Schank & Abelson 1977 책, Minsky memo 원본 PDF | 404, 유료, JS 페이지 |
| 5 | PDTB 3.0 위계, ATOMIC 2020 Figure 3, Ilievski 차원 매핑 파일 | 열지 않았다 |
| 5 | TimeML, Richer Event Description, CaTeRS, Talmy 1988, Gordon & Hobbs 2017 | 검증이 빠진 문헌으로 지목했다 |
| 5 | 네트워크 장애·시험 보고서에 사건 분류를 적용한 1차 연구 | 찾지 않았다 |
| 6 | Noy et al. 2019 CACM, ACT-R·Soar 와 대규모 KG 를 결합한 원 논문, Laird 2008 | 403, PDF 없음, TLS 실패 |
| 6 | Laird, Lebiere & Rosenbloom 2017 Standard Model, Sowa 1984 | 검증이 빠진 문헌으로 지목했다 |
| 7 | Grüninger & Fox 1995 원문 | 스캔 이미지라 텍스트를 뽑지 못했다 |
| 7 | Gangemi 2005 ODP, NeOn 2012 책, Tullis & Wood 2004 원 발표, free listing 표본 크기 기준, Krippendorff 2004 책 | 유료·404 |
| 7 | GPT-4 이후 LLM 의 typicality·특징 규범 재현 연구 | 찾지 않았다 |
| 7 | Noy & McGuinness 2001, Pustejovsky & Stubbs 2012, Dellschaft & Staab 2006, Rugg & McGeorge 1997, Ren 2014 | 검증이 빠진 문헌으로 지목했다 |
| 8 | 국립국어원 현행 전문용어 표준화 지침, TTA 분야 체계, 세종 부류 수 불일치 해소, KorLexNoun 최상위 노드 수(9 대 11) | 찾지 못했거나 원문끼리 엇갈린다 |
| 8 | 우리말샘 감수 절차 세부, 『표준』 67개 분야 채택 시점, 권정현 2015 본문 | 공개 문서 없음, 유료 |
| 8 | 한국어 전문용어 변이를 한 체계로 다룬 단일 연구 | 검색 세 번에 찾지 못했다 |
| 8 | CoreNet(Choi & Bae 2004), KorLex 학술지판(2009), 강범모 외 2001, 이동혁 2007 | 검증이 빠진 문헌으로 지목했다. CoreNet 원문은 저장했다 |
| 9 | ITU 용어 DB 항목 필드, TM Forum GB922 본문, TEDDI–21.905 동기화, ISO 9646-2, 21.905 machine-readable 배포 | JS SPA, Cloudflare, 유료 |
| 9 | RFC 8632 생애주기 세부, RFC 9940 §4, draft-mackey-nmop-kg-for-netops, M.3100 GDMO | 열지 않았다 |
| 9 | IEC 60050-192, ITU-T M.20·G.806, draft-ietf-nmop-network-incident-yang, ETSI TDL, E.800 | 검증이 빠진 문헌으로 지목했다 |
| 10 | Lehnert 1978 책, Lehnert 1977 Cognitive Science 논문, 'question transformation' 이라는 용어 | 대출용, 403. 학위논문에서는 Inference Conversion Rules 로만 나온다 |
| 10 | Graesser, Person & Huber 1992 장, QUEST Table 1 철자 원본 대조, TempQuestions 2018 원 논문 | 열지 못했다 |
| 10 | Graesser & Franklin 1990, Graesser & Hemphill 1991, Pomerantz 2005, Su et al. 2016 | 검증이 빠진 문헌으로 지목했다 |
| 10 | 실제 사내 질문에 범주·경로 라벨을 붙여 일치도를 잰 결과 | #예문 분해 의 대응은 모두 손으로 만든 예시다 |
| 11 | Collins & Quillian 1969 원문과 반응시간 표, Collins & Loftus 1975, Rips 외 1973, Smith 외 1974 원문 | 유료. 교재 해설, ERIC 초록, Shoben 1978 ERIC 보고서(OCR 품질 낮음), 2차 기술로 대신 읽었다 |
| 11 | Conrad 1972, Estes 외 2011 본문, HippoRAG 본문 | 서지나 초록만 확인했다. Estes 는 WRAP 저장소에 원문이 없다 |
| 11 | Tulving 1972 의 p.385–386 밖 쪽 | `tulving1972_pages/` 에 24쪽 이미지가 모두 있지만 두 쪽만 읽었다. 바로 열어 볼 수 있다 |
| 11 | SWOW 의 14개 언어에 한국어가 드는지 | 원문이 언어 목록을 주지 않는다. smallworldofwords.org 의 언어 목록으로 확인할 수 있다 |
| 11 | 질문 경로 로그로 KG 간선 가중치를 갱신하고 효과를 잰 연구 | 찾지 못했다. click graph 기반 query expansion, adaptive spreading activation 계열 IR 문헌을 보면 알 수 있다 |
| 11 | Kumar 2021 리뷰, McClelland 외 1995, Binder 외 2016, Devereux 외 2014(CSLB), Lambon Ralph 외 2017 | 검증이 빠진 중심 문헌으로 지목했다. McClelland 외 1995 는 E5 (d) 의 2단 저장 근거의 원전이다 |

## 원문 위치

- 갈래별 원문: `/home/ssafy/workspace/alt/lab-notes/kg-cognitive-classification/lab/sources/<갈래키>/`. 갈래키는 categorization, lexical-resources, foundational-ontology, terminology, commonsense-event, kg-typology, methodology, korean-lexical-terminology, telecom-domain-vocabulary, question-typology, semantic-memory 다.
- 조사 결과와 검증 결과 대조용 사본: `/home/ssafy/workspace/alt/lab-notes/kg-cognitive-classification/lab/findings.json`. 갈래 1~11 의 조사·검증 결과와 빈칸 비평 결과를 담는다. 갈래 1~10 은 첫 워크플로(wf_b4f9f64d-6b6)의 journal 에서, 갈래 11 은 재조사 워크플로(wf_00dde37b-6d7)에서 옮겼다.
- 검증 대조 스크립트: 세션 scratchpad 의 `verify/` 폴더. 세션이 끝나면 지워진다.

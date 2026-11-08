# 사건 종류도, 때가 붙은 사건 하나도 말뭉치를 묶어서 미리 정하지 않고 찾을 수 있지만, 묶음에 이름을 붙이고 사건 사이 관계를 세우는 일은 아직 사람이나 큰 모델이 맡는다

조사일: 2026-10-11. 갈래: "사건을 미리 정하지 않고 발견하기".

## 읽는 법

**확인 상태.**

- `원문 읽음`: 논문 PDF를 받아 본문·표·한계 절을 읽었다. 인용은 그 PDF 텍스트에서 옮겼다.
- `코드 읽음`: 원문에 더해 공식 저장소를 `lab/repos/` 에 받아 해당 줄을 열어 봤다.
- `초록만`: 원문을 열지 못했다. 초록만 읽었다.

쪽 번호는 PDF의 쪽 순서다. 학회 논문집의 인쇄 쪽 번호와 다를 수 있다.

**두 층을 나눠 읽는다.** 문헌은 "사건"을 두 층으로 다룬다. 한 층은 사건 종류(type)다. "결산", "체포", "자금 지원"처럼 여러 번 일어나는 일의 갈래다. 다른 층은 때와 곳이 붙은 사건 하나다. "2026년 결산", "8월 12~14일 홍콩 공항 시위"가 여기에 든다. 문헌은 이 층을 key event 또는 episode라고 부른다. 사용자가 든 "2026년 결산"은 둘째 층의 사례이고, 그 종류는 첫째 층의 "결산"이다. 아래 묶음 A·C는 첫째 층을, 묶음 B는 둘째 층을 푼다.

**영상·글.** 이 갈래에서 저자 발표 영상이나 블로그 글은 찾지 못했다. 검색에서는 Heng Ji의 AKBC 2020 발표 초록 페이지(https://www.akbc.ws/2020/virtual/speaker_hji.html)만 나왔다. 그 페이지도 열어서 확인하지 않았다. 그래서 아래 출처는 모두 논문과 코드다.

---

## 묶음 A. 말뭉치를 묶어서 사건 종류를 찾는다 (LLM 이전, 비지도)

이 묶음의 공통 메커니즘은 이렇다. 문장에서 사건을 가리키는 낱말(동사, 동사+목적어)을 뽑는다. 그 낱말들을 어떤 유사도로 군집한다. 군집 하나를 사건 종류 하나로 본다.

### A1. Template-Based Information Extraction without the Templates

- 종류: 논문 (Chambers & Jurafsky, ACL 2011)
- 링크: https://aclanthology.org/P11-1098/
- 푸는 것: 템플릿(사건 종류와 그 역할 칸)을 모르는 상태에서 뉴스 말뭉치로부터 템플릿을 배우고, 그 템플릿으로 칸을 채운다.
- 미리 정하지 않는 방법: 사건 패턴(동사, WordNet 사건 명사, 동사:목적어 머리말)을 뽑는다. 두 패턴이 같은 문서 안에서 가까이 자주 나오면 같은 사건에 속한다고 본다. 이 거리 가중 PMI로 응집 군집을 하고, 군집 크기가 40을 넘으면 멈춘다. 역할 칸은 같은 대상을 가리키는(상호참조) 논항 위치끼리 묶어서 만든다.
- 인용:
  - "performs extraction without knowing the template structure in advance" (초록, 1쪽)
  - "We hypothesize that two patterns are related if they occur near each other in a document more often than chance." (§4.1.2, 3쪽)
- 수치 (MUC-4 테러 말뭉치 1300문서): 시스템은 77개 군집을 배웠다. 사람이 만든 MUC-4 칸에 대해 칸 재현율 92%, 정밀도 14/16을 보고한다(§4.3, 7쪽). 문서 분류 F1은 Bombing 0.72, Attack 0.46이다(Figure 4). 칸 채우기 F1은 0.40이다(초록).
- 작은 모델·한국어: LLM을 쓰지 않는다. 대신 구문 분석기, 개체명 인식기, 상호참조 해소기, WordNet이 필요하다. 저자는 결론에서 군집 멈춤 조건 같은 매개변수가 많다고 적는다. [추정] 한국어 사내 문서에서는 상호참조 해소기의 품질이 역할 칸 품질을 좌우할 것이다(사례: 이 논문의 역할 유도가 상호참조 논항에 기댄다, 1개).
- 확인 상태: 원문 읽음

### A2. Liberal Event Extraction and Event Schema Induction

- 종류: 논문 (Huang 외, ACL 2016)
- 링크: https://aclanthology.org/P16-1025/
- 푸는 것: 어떤 말뭉치를 받아도 사건 추출과 사건 schema 발견을 한 번에 한다.
- 미리 정하지 않는 방법: 낱말 뜻 구분(WSD)을 거친 명사·동사를 사건 후보로 삼는다. AMR 의미 관계로 후보의 논항을 고르고, 낱말 뜻 임베딩과 논항 임베딩을 합쳐 사건 구조 표현을 만든다. 사건 후보와 논항을 함께 spectral clustering으로 묶는다. 군집 중심에 가장 가까운 낱말을 사건 종류 이름으로 쓴다.
- 인용:
  - "It automatically discovers a complete event schema, customized for a specific input corpus." (§1, 1쪽)
  - "we utilize the trigger which is nearest to the centroid of the cluster as the event type name" (§2.6, 5쪽)
- 수치 (ERE에서 뽑은 100문장, 전문가 두 명이 고친 정답): 정답 AMR을 쓰면 사건 종류 붙이기 F1 74.5, 논항 역할 F1 68.2다. 자동 AMR 파서를 쓰면 각각 58.6, 52.9로 떨어진다(Table 6, 8쪽). AMR 대신 의존 구문을 쓰면 사건 종류 F1이 52.7로 떨어진다(Table 7).
- 작은 모델·한국어: LLM을 쓰지 않는다. AMR 파서, OntoNotes 낱말 뜻 체계, FrameNet·VerbNet·PropBank 역할 사전이 핵심 부품이다. [추정] 이 부품들은 영어 자원이어서 한국어 사내 문서에 그대로 옮기기 어렵다(사례: Table 7에서 AMR을 의존 구문으로 바꾸기만 해도 F1이 약 6점 떨어진다, 1개).
- 확인 상태: 원문 읽음

### A3. Open Domain Event Extraction Using Neural Latent Variable Models (ODEE)

- 종류: 논문 + 코드 (Liu 외, ACL 2019)
- 링크: https://arxiv.org/abs/1906.06947 , 코드 https://github.com/lx865712528/ACL2019-ODEE
- 푸는 것: 같은 사건을 다룬 여러 기사(news cluster)에서 종류 제한 없는 사건과 그 schema를 뽑는다.
- 미리 정하지 않는 방법: 기사 묶음마다 잠재 사건 종류 벡터를 하나 둔다. 개체 하나하나가 잠재 칸(slot)에 배정되는 생성 모델을 신경망 변분 추론으로 학습한다. 같은 개체가 묶음 안 여러 기사에 나오는 횟수(redundancy)를 특징으로 넣는다. 칸 수만 30으로 미리 정한다.
- 인용:
  - "to extract unconstraint types of events and induce universal event schemas from clusters of news reports" (§1, 1쪽)
  - "different news agencies can report the same events, redundancy can be leveraged for better event extraction" (§1, 1쪽)
- 수치 (GNBusiness, Google Business News 기사 묶음): schema 맞추기 F1 49.8로, 이전 최고 생성 모델 46.7보다 높다(Table 4). 칸 일관성(NPMI)은 0.18 대 0.10이다(Table 5). redundancy 특징을 뺀 모델은 F1 48.3이다.
- 작은 모델·한국어: LLM을 쓰지 않는다. ELMo와 Stanford 파서를 쓰고, 같은 사건을 다룬 문서 묶음이 입력으로 주어져야 한다. [추정] 사내 보고서에서 "여러 작성자가 같은 일을 각자 쓴 보고서 묶음"이 이 입력 조건과 같은 모양이다(사례: 이 논문의 입력이 여러 언론사의 같은 사건 기사 묶음이다, 1개).
- 확인 상태: 원문 읽음

### A4. Corpus-based Open-Domain Event Type Induction (ETypeClus)

- 종류: 논문 + 코드 (Shen 외, EMNLP 2021)
- 링크: https://arxiv.org/abs/2109.03322 , 코드 https://github.com/mickeystroller/ETypeClus
- 푸는 것: 주어진 말뭉치에서 두드러진 사건 종류 집합을 찾는다.
- 미리 정하지 않는 방법: 사건 종류 하나를 ⟨술어 뜻, 목적어 머리말⟩ 쌍(P-O 쌍)의 군집으로 정의한다. 배경 말뭉치 대비 두드러진 술어와 목적어만 남긴다. 동사 뜻 사전(VerbNet, OntoNotes)의 예문과 견주어 술어 뜻을 가른다. P-O 쌍을 구 모양 잠재 공간에 임베딩하면서 동시에 군집한다.
- 인용:
  - "we propose to represent each event type as a cluster of ⟨predicate sense, object head⟩ pairs" (초록, 1쪽)
  - "On ACE, we recover 24 out of 33 event types" (§4.1, 7쪽)
- 수치: 후보 군집 100개를 만든 뒤 사람이 손으로 대조해서 ACE 33개 중 24개, ERE 38개 중 28개 종류를 되찾았다(§4.1). 사람이 정의하지 않은 Build(ACE), Bombing(ERE) 종류도 찾았다. 정답 군집 수를 알려 준 사건 언급 군집에서 ACE BCubed-F1 51.58로, 직전 방법 JCSC(A2) 43.83보다 높다(Table 4).
- 코드에서 본 것 (`lab/repos/ETypeClus`, 커밋 `81c79ea`):
  - `latent_space_clustering.py:306` — 군집 수 `--n_clusters`의 기본값이 30이다. 군집 수는 사용자가 정해야 한다.
  - `extract_svo_new.py:5` — 주어·동사·목적어 추출에 spaCy `en_core_web_trf`를 쓴다.
  - `generate_po_mention_features.py:10` — 표현 학습에 `bert-large-uncased-whole-word-masking`을 쓴다.
  - README의 데이터·동사 뜻 사전은 Google Drive에서 따로 받아야 한다.
- 작은 모델·한국어: LLM 없이 BERT-large와 spaCy로 돈다. 영어 동사 뜻 사전이 필수 부품이다. 저자는 주어를 일부러 뺐다고 적는다(2쪽 각주 4). [추정] 한국어로 옮기려면 동사 뜻 구분 단계를 빼거나 다른 사전으로 바꿔야 한다(사례: `disambiguate_verb_sense.py:132`가 VerbNet에서 만든 사전 파일을 기본 입력으로 받는다, 1개). [추정] 사내 보고서는 "실적을 집계했다"처럼 명사화된 서술이 많아서 동사 중심 P-O 쌍이 덜 걸릴 것이다(사례: 없음. 사내 문서 표본에서 동사·명사 서술 비율을 세어 보면 알 수 있다).
- 확인 상태: 코드 읽음

---

## 묶음 B. 때가 붙은 사건 하나를 찾는다 (key event, episode)

이 묶음은 사건 "종류"가 아니라 특정 시점의 사건 "하나"를 찾는다. "2026년 결산"이 이 층에 든다. 공통 메커니즘은 특정 날짜·구간에 유난히 몰린 구절을 사건의 표지로 쓰는 것이다.

### B1. Unsupervised Key Event Detection from Massive Text Corpora (EvMine)

- 종류: 논문 + 코드 (Zhang 외, KDD 2022)
- 링크: https://arxiv.org/abs/2206.04153 , 코드 https://github.com/yzhan238/EvMine
- 푸는 것: 한 주제의 뉴스 말뭉치(예: 2019 홍콩 시위)에서 특정 때와 곳에 일어난 key event들과 그 문서들을 찾는다.
- 미리 정하지 않는 방법: tf-idf를 시간 축으로 바꾼 ttf-itf 점수로 "말뭉치 전체에는 흔하지만 특정 날에만 몰린" peak phrase를 뽑는다. 문서 공동 출현, BERT 기반 의미 유사도, 날짜 가까움을 간선으로 하는 그래프를 만들고 community detection으로 peak phrase를 묶는다. 묶음 하나가 key event 하나다. 묶음의 구절로 의사 레이블을 만들어 문서 분류기를 학습하고, 분류 결과로 묶음을 다시 고치는 고리를 돈다.
- 인용:
  - "We assume each document has a publication date in the corpus" (§1, 2쪽)
  - "there are always delays and back referencing in news articles" (§3, 3쪽) — 저자는 이 때문에 ttf를 그날 하루가 아니라 뒤따르는 며칠의 빈도를 합쳐 계산한다.
  - "All key events in this paper are manually named for easy understanding." (각주 2, 2쪽)
- 수치: HK Protest(1675문서, 정답 key event 36개)에서 5-F1 0.776으로, S-BERT 군집 0.582보다 높다. Ebola(741문서, 17개)에서 0.748 대 0.615다(Table 2, 7쪽).
- 작은 모델·한국어: LLM을 쓰지 않는다. 문서마다 발행일이 있어야 한다. 사건 이름은 사람이 붙였다(각주 2). [추정] 사내 보고서의 작성일·보고 기간이 이 발행일 자리를 채울 수 있다(사례: 없음. 사내 보고서 표본에 작성일 메타데이터가 몇 할이나 있는지 보면 알 수 있다). [추정] 한국어 peak phrase 추출에는 형태소 분석기가 앞단에 필요하다(사례: 없음. 구절 추출기를 한국어 표본에 돌려 보면 알 수 있다).
- 확인 상태: 원문 읽음

### B2. Synergizing Unsupervised Episode Detection with LLMs for Large-Scale News Events (EpiMine)

- 종류: 논문 + 코드 (Kargupta 외, arXiv 2408.04873 v2, 2025-06)
- 링크: https://arxiv.org/abs/2408.04873 , 코드 https://github.com/pkargupta/epimine
- 푸는 것: key event 하나(예: 7월 1일 입법회 점거)의 기사들 안에서 그보다 잘게 나뉜 episode들과 해당 문단을 찾는다.
- 미리 정하지 않는 방법: 말뭉치 수준에서 함께 나오는 두드러진 낱말 조합(discriminative co-occurrence)을 센다. 기사 안에서 이 조합이 바뀌는 자리를 episode 경계로 본다. 기사들의 조각을 거리 문턱값 기반 응집 군집으로 합쳐 후보 episode를 만든다. 마지막에 LLM이 후보 묶음을 읽고 episode 제목·핵심어·예문을 쓴다.
- 인용:
  - "Episodes are not timestamped." (§1, 2쪽) — key event와 달리 문단에는 날짜가 따로 붙지 않는다는 뜻이다.
  - "without any LLM summarization—still yields significantly better performance than all baselines" (실험 분석, 8쪽)
- 수치 (직접 모은 뉴스 3주제, 30개 key event): 5-F1이 테러 32.43, 자연재해 34.53, 정치 29.23이다. 가장 강한 기준선은 K-means로 각각 21.23, 28.14, 16.04다(Table 2). LLM을 뺀 변형은 24.77, 17.52, 19.06이다. 그래서 LLM 없는 변형은 테러·정치에서는 기준선을 넘지만 자연재해에서는 K-means보다 낮다. 저자는 LLM에 군집 없이 기사를 바로 주면 주요 episode를 대부분 놓친다고 적는다(8쪽).
- 코드에서 본 것 (`lab/repos/epimine`, 커밋 `d46f064`):
  - `epimine.py:304` — 후보 episode 군집은 `AgglomerativeClustering(n_clusters=None, ..., distance_threshold=mean_track - std_track)`이다. 군집 수를 미리 주지 않고 거리 분포에서 문턱값을 잡는다.
  - `epimine.py:315`–`320` — LLM 호출은 `text_LLM` 클래스 하나에 모여 있고 `claude-2.1`을 부른다.
- 작은 모델·한국어: LLM은 마지막 이름·요약 단계에만 한 번 들어간다. [추정] `text_LLM` 클래스 하나만 바꾸면 로컬 모델로 갈아 끼울 수 있다(사례: 호출 지점이 `epimine.py:315` 한 곳뿐이다, 1개). 작은 모델이 이 단계를 얼마나 잘하는지는 실험한 사례가 없다. 논문의 모든 실험은 영어 뉴스다.
- 확인 상태: 코드 읽음

---

## 묶음 C. 묶은 뒤 LLM으로 개념을 붙이고 이름을 짓는다 (2024~2026)

이 묶음은 묶음 A의 군집 위에 LLM을 얹는다. LLM은 문장마다 짧은 개념 이름을 만들거나, 군집마다 이름을 붙인다.

### C1. Event Ontology Expansion via LLM-Based Conceptualization (ConceptE)

- 종류: 논문 + 코드 (Ren 외, arXiv 2606.21048, 2026-06)
- 링크: https://arxiv.org/abs/2606.21048 , 코드 https://github.com/ICT-KCG/ConceptE
- 푸는 것: 이미 있는 사건 온톨로지에 데이터에서 새로 나온 사건 종류를 찾아 알맞은 자리에 붙이고 이름을 짓는다.
- 미리 정하지 않는 방법: LLM이 문장과 사건 낱말(trigger)을 받아 짧은 개념 이름과 한 줄 설명을 만든다. BERT가 문장·trigger·개념 이름·설명을 함께 인코딩한다. 이 표현으로 K-means 군집을 하고, 군집을 기존 계층의 부모 노드에 방향 있는 분류기로 붙인다. 이름은 군집의 대표 개념 여러 개와 예측된 계층 경로를 LLM에 주어 짓는다.
- 인용:
  - "Existing methods typically cluster contextualized trigger representations" (초록, 1쪽) — 저자는 이 방식이 문맥의 겉모습에 흔들린다고 본다.
  - "producing a concise concept name and a natural-language description" (초록, 1쪽)
  - "our experiments assume that event triggers are given" (Limitations, 9쪽)
- 수치: ACE 사건 군집 BCubed-F1 83.25로, 직전 최고 HALTON 75.06, ETypeClus(A4) 38.69보다 높다. MAVEN에서는 51.72 대 39.35다(Table 1). 이름 짓기는 ACE에서 ROUGE-L 30.43, BERTScore 53.33이다(Table 3).
- 전제 조건: 알려진 종류의 레이블 예문이 있어야 한다(§2). 군집 수는 정답의 미지 종류 수로 둔다(부록 F, 13쪽, "with the number of clusters set to the number of unknown event types"). trigger도 주어진다.
- 작은 모델·한국어: 개념화와 이름 짓기에 Qwen3-32B를 썼다(§4.4). 8B 이하 모델로 돌린 결과는 없다. [추정] 우리 용어집이 "알려진 종류"와 레이블 예문 자리를 채울 수 있어서, 이 논문의 설정이 순수 비지도보다 우리 상황에 가깝다(사례: 이 논문의 입력이 기존 온톨로지 + 레이블 예문 + 미표시 문장이다, 1개). 군집 수를 정답에서 가져온 점은 실제 적용에서 그대로 쓸 수 없다.
- 확인 상태: 원문 읽음

### C2. Collaboration of Large and Small Models for Event Type Discovery in Completely Open Domains

- 종류: 논문 (Li 외, Mathematics 2024)
- 링크: https://doi.org/10.3390/math12182928
- 푸는 것: 레이블 없는 사건 문장에서 사건 종류를 찾는다.
- 미리 정하지 않는 방법 (초록 기준): LLM이 문장마다 종류에 관련된 행위 정보를 뽑는다. LLM이 군집 결과를 다듬고, 그 다듬기를 작은 사전학습 모델의 fine-tuning 과제로 옮긴다. 군집이 끝나면 LLM이 군집마다 종류 이름을 짓는다.
- 인용: "we use LLM to guide the clustering of event texts and distill this process into a fine-tuning task for training smaller pre-trained language models" (초록)
- 수치: 초록은 기존 최고 방법보다 낫다고만 적는다. 데이터셋과 수치는 원문을 열지 못해 확인하지 못했다.
- 작은 모델·한국어: 큰 모델의 판단을 작은 모델로 옮긴다는 방향이 우리 조건과 맞는다. 어떤 크기의 LLM과 작은 모델을 썼는지는 확인하지 못했다. MDPI 원문 페이지가 403을 돌려줘서 Semantic Scholar API로 초록만 읽었다.
- 확인 상태: 초록만

---

## 묶음 D. LLM의 상식으로 사건 schema를 먼저 그린다 (top-down)

이 묶음은 말뭉치를 묶지 않는다. 시나리오 이름 하나("전염병 발생")를 LLM에 주고, 그 시나리오의 하위 사건과 사건 사이 시간·포함 관계를 LLM에게 묻는다. 사건 사이 관계를 만드는 방법이 이 묶음에만 있다.

### D1. Zero-Shot On-the-Fly Event Schema Induction

- 종류: 논문 + 코드 (Dror, Wang, Roth, Findings of EACL 2023)
- 링크: https://arxiv.org/abs/2210.06254 , 코드 https://github.com/CogComp/Zero_Shot_Schema_Induction
- 푸는 것: 복합 사건의 이름만 받아 그 사건의 하위 사건, 논항, 관계를 담은 schema를 만든다.
- 미리 정하지 않는 방법: GPT-3가 그 주제로 뉴스 기사(30편), 절차 설명 같은 여러 장르의 글을 생성한다. 기존 IE 도구로 그 글에서 사건·논항·시간 관계·포함 관계를 뽑는다. 시간 관계에서 논리 관계(AND, OR)를 유도해 schema 그래프를 짓는다.
- 인용:
  - "taking as input only the name of the complex event of interest" (§1, 1쪽)
  - "when we use inferior LMs such as GPT-2, we see a decline in performance" (Limitations, 9쪽)
- 수치 (LDC2020E25 schema): GPT-3 생성 글로 만든 schema가 정답 사건의 23.73%를 정확히, 37.84%를 동의어까지 덮는다. 실제 기사로 학습한 지도 학습 모델은 54.84%다. GPT-2로 바꾸면 14.88%, 29.55%로 떨어진다(Table 3, 7~8쪽).
- 작은 모델·한국어: 저자는 schema 품질이 언어 모델 품질과 그 주제가 학습 데이터에 얼마나 있었는지에 달렸다고 적는다(Limitations). [추정] 회사 고유 절차는 공개 학습 데이터에 거의 없어서 이 방식이 사내 사건 schema를 잘 그리지 못할 것이다(사례: 저자가 "unexplored territory" 고고학 발굴을 학습 데이터에 드문 주제의 예로 들며 결과를 의심한다, 1개).
- 확인 상태: 원문 읽음

### D2. Open-Domain Hierarchical Event Schema Induction by Incremental Prompting and Verification (IncSchema)

- 종류: 논문 + 코드 (Li 외, ACL 2023)
- 링크: https://aclanthology.org/2023.acl-long.312/ , 코드 https://github.com/raspberryice/inc-schema
- 푸는 것: 시나리오 이름(과 선택적인 장 구조)에서 시간 관계와 포함 관계를 함께 가진 사건 schema 그래프를 만든다.
- 미리 정하지 않는 방법: 사건을 고정 종류가 아니라 자유 서술 문장으로 나타낸다. 세 단계로 LLM에 묻는다. 먼저 주요 사건 목록을 받고, 각 사건의 앞뒤·하위 사건을 더 물어 넓히고, 사건 쌍마다 관계를 검증한다. 관계 검증은 "e1이 e2보다 먼저 시작하는가", "먼저 끝나는가", "더 오래 가는가" 세 질문으로 쪼개고, Allen 구간 대수로 선후·포함을 판정한다. 새 사건은 SBERT·문자열 유사도로 중복을 걸러 낸다.
- 인용:
  - "we propose to treat event schemas as a form of commonsense knowledge that can be derived from large language models" (초록, 1쪽)
  - "we decompose the decision of a temporal relation into questions about start time, end time, and duration" (§3.4, 4쪽)
- 수치: ODIN(저자가 새로 만든 18개 시나리오)에서 사건 F1 53.3, 시간 관계 F1 28.1, 포함 관계 F1 48.5다. 그래프를 한 번에 생성하게 한 GPT-DOT은 47.4, 20.9, 17.5다(Table 4). RESIN-11에서는 사건 F1이 41.7 대 41.8로 비슷하다(Table 3).
- 주의: ODIN 정답 schema는 사람이 이 알고리즘의 출력을 고쳐서 만들었다("by asking human annotators to curate the schemas generated by our algorithm", §4.1, 5쪽). 저자도 RESIN-11 점수가 더 낮은 이유를 이것으로 든다.
- 작은 모델·한국어: text-davinci-003을 썼다(§4.3). 관계 검증은 "yes/no/unknown" 토큰의 log probability를 읽는다. 사건 쌍마다 세 질문을 순서와 표현을 바꿔 여러 번 묻는다. [추정] 사건이 n개면 호출이 n²에 비례해서 늘어나므로, 작은 로컬 모델에서도 속도가 먼저 걸림돌이 될 것이다(사례: §3.4의 쌍별 검증 설계, 1개). 작은 모델로 돌린 결과는 없다.
- 확인 상태: 원문 읽음

---

## 묶음 E. 정의만 주면 그 종류를 뽑는다 (zero-shot, 작은 모델 수치)

이 묶음은 종류를 발견하지 않는다. 사람이든 묶음 A~C든 누군가 종류와 정의를 쓰면, 모델이 학습 없이 그 종류를 문서에서 뽑는다. 발견한 종류를 문서 전체에 다시 적용하는 단계에 해당한다. 8B 근처 모델의 수치가 이 묶음에 있다.

### E1. GoLLIE: Annotation Guidelines Improve Zero-Shot Information-Extraction

- 종류: 논문 + 코드 + 모델 (Sainz 외, ICLR 2024)
- 링크: https://arxiv.org/abs/2310.03668 , 코드 https://github.com/hitz-zentroa/GoLLIE
- 푸는 것: 학습 때 보지 못한 schema의 IE 과제를 annotation 지침만 보고 푼다.
- 미리 정하지 않는 방법: 사건 종류를 Python dataclass로 쓰고, 지침을 docstring과 주석으로 붙인다. Code-LLaMA를 여러 IE 데이터셋의 지침 따르기로 fine-tuning한다. 학습 중에 레이블 이름을 가리고 정의를 바꿔 써서 모델이 이름 대신 정의를 읽게 만든다.
- 인용:
  - "IE tasks require more information than just label names, they require annotation guidelines." (§1, 2쪽)
  - "GoLLIE with a 7B parameter backbone already exhibits strong zero-shot capabilities." (Model scaling 문단, 8쪽)
- 수치 (보지 못한 데이터셋 zero-shot F1, Table 3): 7B 평균 55.3, 13B 56.0, 34B 57.2, 지침 없는 기준선 42.3이다. 사건 추출만 보면 CASIE EE 7B 59.3이다. WikiEvents EE에서는 7B 43.0으로 기준선 47.5보다 낮다. 평균에는 NER이 많이 섞여 있다.
- 작은 모델·한국어: 7B 모델이 공개돼 있다. 종류와 지침은 사람이 미리 써야 한다. 학습 데이터는 영어다. [추정] 한국어 사내 문서에서는 영어로 학습된 지침 따르기 능력이 얼마나 옮겨 가는지 따로 재야 한다(사례: 없음. 한국어 문장 수십 개에 GoLLIE-7B를 돌려 보면 알 수 있다).
- 확인 상태: 원문 읽음

### E2. Improving Event Definition Following For Zero-Shot Event Detection (DivED)

- 종류: 논문 (Cai 외, ACL 2024)
- 링크: https://aclanthology.org/2024.acl-long.157/
- 푸는 것: 보지 못한 사건 정의를 주면 그 사건의 trigger를 찾는 zero-shot event detection을 개선한다.
- 미리 정하지 않는 방법: LLM으로 사건 종류 3000개 이상, 종류마다 정의 10개와 예문 10개를 생성한다(DivED). 정의에 부모·형제 사건 이름을 넣는다. LLaMA-2-7B를 이 데이터로 fine-tuning해서 추론 때 새 정의를 따르게 한다.
- 인용:
  - "a large number of event types (200) and diverse event definitions can significantly boost event extraction performance" (초록, 1쪽)
  - "the performance does not scale with over ten examples per event type" (초록, 1쪽)
- 수치 (Table 4, trigger 분류 F1): LLaMA-2-7B(DivED)가 ACE 29.1, M2E2 22.0, MEE 26.0이다. GPT-3.5는 ACE 6.6이다. 세 데이터셋 평균은 25.7이다.
- 작은 모델·한국어: 7B로 GPT-3.5를 넘지만 절대 수치는 30 F1 아래다. 학습 때 정의를 빼면 trigger 식별 F1이 52%, trigger 분류 F1이 59% 떨어진다(Table 5). [추정] 작은 모델에서는 사건 정의 문장의 품질이 결과를 크게 좌우한다(사례: 정의 제거 실험, 1개).
- 확인 상태: 원문 읽음

### E3. TextEE: Benchmark, Reevaluation, Reflections, and Future Challenges in Event Extraction

- 종류: 논문 + 벤치마크 (Huang 외, arXiv 2311.09562 v3, 2024-06)
- 링크: https://arxiv.org/abs/2311.09562
- 푸는 것: 사건 추출 방법들을 같은 조건으로 다시 재고, LLM이 사건 추출을 풀었는지 본다.
- 미리 정하지 않는 방법: 해당 없음. 이 출처는 종류가 주어진 상태에서 작은·큰 LLM의 few-shot 수치를 재는 기준점으로 넣었다.
- 인용:
  - "there is a large gap between LLMs and the baselines for both the ED and EAE tasks" (§5, 8쪽)
  - "LLMs might rely heavily on the format of the in-context examples" (§5.1, 8쪽)
- 수치 (여러 데이터셋 평균, 데이터셋마다 250문서 표본, Table 6): 사건 종류 분류 F1이 Zephyr-7B 6-shot 8.0, Llama-2-13B 6-shot 10.4, Mixtral-8x7B 64-shot 14.6, GPT-3.5 16-shot 12.3이다. 지도 학습 모델 TagPrime-C는 69.5다.
- 작은 모델·한국어: 7~13B 모델이 few-shot 예시만으로 사건 종류를 붙이면 F1이 10 안팎이다. 저자가 든 주된 오류는 한 낱말에 여러 종류를 붙이는 과잉 예측이다. 예로 든 "detained"에 모델이 Attack, Die, Transport, Arrest-Jail을 모두 붙였다.
- 확인 상태: 원문 읽음

---

## 묶음 F. 종류를 두지 않고 사건 노드를 바로 잇는다

### F1. EventRAG: Enhancing LLM Generation with Event Knowledge Graphs

- 종류: 논문 (Yang 외, ACL 2025)
- 링크: https://aclanthology.org/2025.acl-long.830/
- 푸는 것: 여러 문서에 흩어진 사건을 사건 지식 그래프로 묶어서 시간·논리 추론이 필요한 RAG 답을 낫게 한다.
- 미리 정하지 않는 방법: LLM이 청크마다 사건, 개체, 날짜, 사건 사이 관계(원인, 선후)를 자유 형식으로 뽑는다. 사건 종류 체계는 두지 않는다. 문서마다 따로 뽑힌 같은 사건·개체는 임베딩 코사인 유사도가 문턱값 θ를 넘으면 합친다. 합칠 때 원래 항목을 지우지 않고 "similar" 관계로 잇는다.
- 인용:
  - "A candidate with the highest similarity score above θ is selected as the merge target." (§2.2, 3쪽)
  - "The framework heavily relies on multiple LLM calls for event extraction, relationship identification, and knowledge expansion." (Limitations, 9쪽)
- 수치: 본문 §3.1은 UltraDomain 세 분야와 bioprotocol에서 NaiveRAG, GraphRAG, LightRAG와의 쌍 비교 승률로 생성 품질을 보고한다. 사건 추출 자체를 정답과 맞춘 표는 읽은 범위에 없다.
- 작은 모델·한국어: 모든 LLM 단계에 gpt-4o-2024-08-06을, 임베딩에 text-embedding-3-small을 썼다(부록 A.2). 저자는 문서마다 LLM을 여러 번 불러서 느리다고 적는다. 작은 모델 결과는 없다.
- 확인 상태: 원문 읽음

---

## 우리 문제에 주는 것

사용자의 사내 보고서 상황은 이렇다. 작성자마다 용어가 다르다. 형식이 없는 문서가 있다. 모델은 8B 이하 로컬 모델이다. 지금은 용어집 꼬리표로 이름 붙은 대상만 잇는다. 이 상황에 가장 쓸 만한 세 가지와 그 이유는 다음과 같다.

**1. "2026년 결산" 같은 때 붙은 사건은 EvMine(B1)·EpiMine(B2) 방식이 가장 가깝다.** 두 방법은 사건을 종류가 아니라 "특정 때에 몰린 구절 묶음"으로 찾는다. 그래서 사건 종류 목록이 없어도 된다. 핵심 부품은 날짜별 빈도 점수, 임베딩 유사도, 군집이다. 이 부품들은 LLM이 필요 없다. EpiMine에서 LLM은 마지막 이름·요약 한 번에만 들어가고, 코드에서 호출 지점이 한 곳이다(`epimine.py:315`). 사내 보고서에는 작성일과 보고 기간이 있어서 발행일 조건을 채울 가능성이 높다. [추정] 다만 사내 보고서는 뉴스처럼 하루 단위로 몰리지 않고 분기·연 단위로 몰릴 것이어서 ttf의 시간 창을 다시 정해야 한다(사례: 없음. 사내 보고서 작성일 분포를 그려 보면 알 수 있다).

**2. 사건 종류("결산" 자체)는 ConceptE(C1)의 설정이 우리 상황에 가장 가깝다.** ConceptE는 순수 비지도가 아니라 "이미 있는 온톨로지를 데이터로 넓히는" 설정이다. 우리 용어집이 그 "이미 있는 온톨로지"와 레이블 예문 자리에 들어갈 수 있다. LLM이 하는 일은 문장마다 짧은 개념 이름과 한 줄 설명을 쓰는 것이다. 이 출력은 짧아서 작은 모델이 감당할 만한 크기다. 군집과 계층 붙이기는 BERT급 인코더가 한다. [추정] 작성자마다 다른 용어("결산", "연말 마감", "FY 정산")가 LLM 개념화를 거치면 같은 개념 이름으로 모일 수 있다(사례: 저자가 개념 표현이 문맥이 다른 trigger들을 "Start Company", "Merge Organization" 같은 같은 뜻의 개념으로 모은다고 설명한다(§1, 2쪽), 1개). 단, 논문은 Qwen3-32B를 썼고 군집 수를 정답에서 가져왔다. 그래서 8B 모델 품질과 군집 수 정하기는 우리가 직접 재야 한다.

**3. 같은 일을 여러 작성자가 쓴 중복은 ODEE(A3)가 신호로 쓴다.** ODEE는 같은 사건을 다룬 여러 기사를 한 입력으로 받고, 개체가 여러 기사에 반복되는 정도를 특징으로 쓴다. redundancy 특징을 넣으면 schema 맞추기 F1이 48.3에서 49.8로 오른다. 사내 보고서에서 "같은 결산을 재무팀과 사업부가 각각 쓴 보고서"가 같은 모양이다. 이 신호는 용어가 달라도 같은 숫자·날짜·사람 이름이 겹치는 데서 나온다.

발견한 종류를 문서 전체에 다시 적용하는 단계에는 GoLLIE-7B(E1)나 DivED(E2) 방식이 후보다. 그러나 7~13B 모델의 사건 종류 분류 F1은 few-shot으로 10 안팎(E3), 정의 따르기 fine-tuning을 해도 30 아래(E2)다. 그래서 이 단계는 꼬리표를 확정하는 용도보다 사람이 검토할 후보를 내는 용도에 맞는다.

**아무도 안 푼 것.**

- **한국어·사내 문서.** 이 갈래에서 원문을 읽은 출처 13개 모두 영어 뉴스, 영어 생성 글, 영어 벤치마크(ACE, ERE, MAVEN, MUC-4 등)로 실험했다. A2는 영어 AMR 파서에, A4는 영어 동사 뜻 사전에 기댄다. 비정형 사내 보고서로 실험한 출처는 없었다.
- **사건 종류에 이름 붙이기.** EvMine은 key event 이름을 사람이 붙였다. ETypeClus는 100개 후보 군집을 사람이 정답과 대조했다. Huang 외는 군집 중심 낱말을 그대로 이름으로 썼다. 자동 이름 짓기를 따로 잰 출처는 ConceptE 하나였고, ACE에서 ROUGE-L 30.43에 그쳤다.
- **말뭉치에서 사건 사이 관계 찾기.** 시간·포함 관계를 만드는 출처(D1, D2)는 모두 LLM의 일반 상식에서 관계를 꺼낸다. 특정 회사 문서들 사이의 실제 선후·인과를 찾는 방법은 아니다. EventRAG(F1)는 문서에서 관계를 뽑지만 gpt-4o를 썼고, 관계 추출의 정확도를 정답과 맞춰 보지 않았다.
- **반복되는 사건의 두 층을 함께 다루기.** "2025년 결산"과 "2026년 결산"은 같은 종류의 다른 사건이다. 묶음 A·C는 종류만, 묶음 B는 한 주제 안의 사건 하나만 찾는다. [추정] 한 말뭉치에서 종류 층과 사건 하나 층을 함께 세우고 둘을 잇는 방법은 읽은 범위에 없다(사례: B1은 입력을 한 주제 말뭉치로 한정하고, A4는 날짜를 쓰지 않는다, 2개).
- **군집 수 정하기.** ETypeClus는 군집 수를 사용자가 준다(`latent_space_clustering.py:306`). ConceptE는 정답의 미지 종류 수를 쓴다. 군집 수를 미리 주지 않는 출처는 Chambers & Jurafsky(크기 상한 40으로 멈춤)와 EpiMine(거리 분포에서 문턱값을 잡음, `epimine.py:304`)이다.
- **8B 이하 모델로 한 발견 실험.** 발견 단계(묶음 A~D)에서 LLM을 쓴 출처는 모두 GPT-3, text-davinci-003, Claude-2.1, Qwen3-32B, gpt-4o 가운데 하나를 썼다. 7B 수치가 있는 출처(E1, E2, E3)는 모두 종류가 주어진 추출 과제다.

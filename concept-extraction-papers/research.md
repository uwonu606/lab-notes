# 문장에서 개념 추출 — 논문·방법 조사

- 조사 날짜: 2026-10-09
- 물음: 문장이나 짧은 텍스트에서 "개념(concept)"을 뽑는 방법에는 어떤 연구 계보가 있나. AutoSchemaKG 의 개념 생성 단계는 그중 어디에 놓이나.
- 다루는 갈래: 일곱 개다. 요청받은 여섯 갈래에 임상 NLP 의 concept extraction 을 더했다. 이 갈래는 "concept extraction" 이라는 이름을 글자 그대로 쓴다.

## 읽는 법

근거 라벨은 문장 앞에 붙인다.

| 라벨 | 뜻 |
|---|---|
| `[확인]` | 이 조사에서 원문을 열어 그 대목을 읽었다. |
| `[추정]` | 근거는 있으나 원문에서 직접 확인하지 못했다. 이유를 함께 적는다. |
| `[감]` | 근거가 없다. 무엇을 보면 확정되는지 함께 적는다. |

원문은 조사 에이전트 넷이 갈래별로 나눠 열었다. 작성자는 핵심 인용 20여 개를 받아 온 원문 텍스트에서 다시 대조했다. 다르게 옮겨진 인용 하나(Sha Li 2023 임계값)는 원문 각주 문장으로 바꿨다.

논문 표의 "원문" 칸은 그 행의 서지·방법·평가를 어디까지 읽었는지 적는다. `전문`은 본문 전체를 열었다는 뜻이다. `초록`은 초록이나 서지 레코드만 봤다는 뜻이다. `못 엶`은 열지 못했다는 뜻이다. 표 안의 사실은 원문 칸이 `전문`이면 `[확인]` 이다.

큰따옴표 안은 원문 그대로다. PDF 줄 끝 하이픈과 합자(ﬁ)만 되돌렸다.

### 예문

모든 갈래에 같은 예문을 넣어 출력 모양을 견준다.

> Apple released the iPhone 15 at an event in Cupertino.

각 갈래의 "예문 → 출력"은 작성자가 그 갈래의 입출력 정의에 맞춰 손으로 만든 예시다. 실제로 시스템을 돌린 결과가 아니다.

## 갈래 지도

"개념"이라는 말은 갈래마다 다른 것을 가리킨다.

| # | 갈래 | "개념"이 가리키는 것 | 예문 → 출력 (손으로 만든 예시) |
|---|---|---|---|
| 1 | Conceptualization | 인스턴스(개체·사건)를 묶는 더 추상적인 범주 | "iPhone 15" → smartphone, device, product / 사건 "Apple released the iPhone 15" → product launch, release |
| 2 | Keyphrase·term extraction | 문서 주제를 대표하는 구, 또는 도메인 개념을 나타내는 용어 | → "iPhone 15", "Apple", "Cupertino" (원문에 있는 구) |
| 3 | Entity typing | 문맥 속 mention 에 붙는 유형 이름 | mention "Apple" → {organization, company} (정해진 어휘 안에서) |
| 4 | Ontology learning 개념층 | 용어와 그 사이 is-a(hypernym) 관계 | 예문 한 줄로는 패턴이 없다. 코퍼스의 "smartphones such as the iPhone 15" → hyponym(iPhone 15, smartphone) |
| 5 | LLM KG 구축·canonicalization | 추출한 노드·관계를 같은 뜻끼리 묶은 대표 이름, 또는 유도한 schema 유형 | "iPhone 15", "Apple iPhone 15", "the iPhone15" → 노드 하나 "iPhone 15" |
| 6 | 임상 concept extraction·normalization | 의료 문서 속 problem·test·treatment 구간, 또는 UMLS Metathesaurus 개념 | (의료 문장이 필요하다) "CXR" → test 구간 → Metathesaurus 개념 "chest x-ray" |
| 7 | 해석가능성 | 모델 활성 공간의 방향(feature)이나 사람이 정한 속성 | 텍스트 출력이 없다. "Apple 제품"에 반응하는 내부 방향 하나 |

`[확인]` 갈래 6의 "CXR" 예는 i2b2 2010 보고서가 가장 어려운 사례로 든 것을 그대로 가져왔다.

## 1. Conceptualization

인스턴스를 그것을 덮는 개념으로 올리는 일이다.

`[확인]` KnowComp 서베이는 이렇게 정의한다. "conceptualization refers to the process of consolidating specific instances with shared properties or characteristics into a cohesive concept that represents a vast collection of instances." ([Wang et al. 2024/2025 서베이](https://arxiv.org/abs/2406.10885) §1)

입력은 짧은 텍스트·개체·사건이다. 출력은 개념 목록이다. 개념에 확률이나 점수가 붙기도 한다.

### 방법의 세 계열

`[확인]` 같은 서베이는 획득 방법을 셋으로 나눈다(§4).

| 계열 | 하는 일 | 대표 |
|---|---|---|
| Extraction | "is a" 같은 패턴으로 텍스트에서 개념-인스턴스 쌍을 뽑는다 | Probase |
| Retrieval | 미리 있는 개념 taxonomy 에서 가까운 개념을 찾는다 | Song 2011, AbstractATOMIC |
| Generative | 모델이 개념을 직접 생성한다. fine-tuning 방식과 zero-shot LLM 방식으로 나뉜다 | CAT 생성기, CANDLE, AutoSchemaKG |

`[확인]` 서베이는 zero-shot 생성에 후처리 필터를 권한다. "it is recommended to implement quality control mechanisms such as human evaluation or discriminators as post-filters." (§4.3.2)

`[확인]` 서베이 §4.2.2 는 AbstractATOMIC 이 GlossBERT 로 개념과 인스턴스를 인코딩해 cosine 유사도로 고른다고 적는다. AbstractATOMIC 원문은 GlossBERT 를 WordNet synset 판별에 쓰고, Probase 개념은 mutual information 순으로 고른다. 서베이 요약과 원문이 다르다.

### 대표 논문

| 논문 | 방법 | 평가 | 코드·리소스 | 원문 |
|---|---|---|---|---|
| Probase. Wu, Li, Wang, Zhu. SIGMOD 2012. [full 판 PDF](https://pages.cs.wisc.edu/~wentaowu/papers/probase-full.pdf), DOI 10.1145/2213836.2213891 | 웹 1.68B 쪽에서 Hearst 패턴으로 isA 를 뽑는다. 이미 얻은 지식으로 다음 추출을 돕는다. isA 마다 plausibility 와 typicality 를 붙인다 | 개념 40개, 개념당 최대 50쌍을 사람이 판정. 평균 precision 92.8% | 공개 경로 없음(#확인하지 못한 것) | 전문 |
| Song, Wang, Wang, Li, Chen. "Short Text Conceptualization Using a Probabilistic Knowledgebase". IJCAI 2011. [PDF](https://www.ijcai.org/Proceedings/11/Papers/388.pdf) | 짧은 텍스트에서 Probase 개체를 찾는다. naive Bayes 로 개념 순위를 낸다 | 트윗 군집화. purity, ARI, NMI | — | 전문 |
| Hua, Wang, Wang, Zheng, Zhou. "Short text understanding through lexical-semantic analysis". ICDE 2015. [PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/conceptualization.pdf) | 분할 → 유형 판별 → 개념 라벨링. Probase 개념을 K-Medoids 로 5,000개 클러스터에 묶어 쓴다 | 쿼리 1,478개, 사람 판정. query 정확도 0.890 | — | 전문 |
| ConceptNet 5.5. Speer, Chin, Havasi. AAAI 2017. [arXiv 1612.03975](https://arxiv.org/abs/1612.03975) | 여러 출처를 합친 의미망. 노드는 정규화한 단어·구다 | 단어 유사도(MEN, RW, WS353 등) Spearman ρ, SAT 유추 | [commonsense/conceptnet5](https://github.com/commonsense/conceptnet5) | 전문 |
| AbstractATOMIC. He, Fang, Wang, Song. Artificial Intelligence 333, 2024. [arXiv 2206.01532](https://arxiv.org/abs/2206.01532) | ATOMIC 사건 속 인스턴스를 WordNet·Probase 개념에 잇는다. 후보를 RoBERTa 검증기로 거른다 | AUC, BLEU-2, zero-shot QA | [atomic-conceptualization](https://github.com/HKUST-KnowComp/atomic-conceptualization) | 전문 |
| CAT. Wang, Fang, Xu, Bo, Song, Chen. ACL 2023. [arXiv 2305.04808](https://arxiv.org/abs/2305.04808) | 문맥을 넣은 개념화·인스턴스화를 semi-supervised 로 학습한다 | AbstractATOMIC 위 판별 과제 AUC, 생성 과제 BLEU 등 | [HKUST-KnowComp/CAT](https://github.com/HKUST-KnowComp/CAT) | 전문 |
| CANDLE. Wang 외. ACL 2024 ([2024.acl-long.128](https://aclanthology.org/2024.acl-long.128/)) | ChatGPT few-shot 으로 사건당 개념 20개를 만든다. critic 모델(임계값 0.9)로 거른다 | 전문가 판정 수용률. 필터 뒤 97.2% / 94.5% | [HKUST-KnowComp/CANDLE](https://github.com/HKUST-KnowComp/CANDLE) | 전문 |
| AbsPyramid. Wang 외. Findings NAACL 2024. [arXiv 2311.09174](https://arxiv.org/abs/2311.09174) | 명사·동사·사건 전체의 추상 개념 221K 를 모은 entailment 벤치마크. 명사·사건 후보는 ChatGPT 가 만든다 | Acc, Macro-F1, AUC | [HKUST-KnowComp/AbsPyramid](https://github.com/HKUST-KnowComp/AbsPyramid) | 전문 |

`[확인]` CANDLE 은 개념이 단순 상위어가 되지 않도록 지시한다. "Make sure that the generated abstract concepts are general and not simply hypernyms of the instance." 그래서 갈래 4의 hypernym 과 겨냥이 다르다.

`[확인]` AbsPyramid 는 기존 사전의 빈 곳을 수치로 보인다. "only 6.3% of nominal phrases ... covered by WordNet". Probase 는 29.6% 를 덮는다.

### 원문이 밝힌 한계

- `[확인]` Song 2011: "sometimes we end up conceptualizing into very general, vague concepts (such as topic, factor, etc.) which make the features not discriminative."
- `[확인]` CAT: "Decontextualized conceptualization, such as observe, may yield wrong abstract commonsense knowledge that cannot be instantiated within the corresponding context."
- `[확인]` AbstractATOMIC: "groups of concepts with certain logical or quantifying relationships (e.g. "doctor and nurse," "a cup of tea") ... not precisely handled in our implementation."
- `[확인]` CANDLE: "The major limitation of CANDLE lies in the significant cost of distilling LLMs" 그리고 "CANDLE has only been validated on ATOMIC."
- `[확인]` AbsPyramid: "Experimental results demonstrate that current LLMs face challenges comprehending abstraction knowledge in zero-shot and few-shot settings."

### AutoSchemaKG 가 잇는 선행 연구

`[확인]` AutoSchemaKG(ACL 2026, [2026.acl-long.942](https://aclanthology.org/2026.acl-long.942/), arXiv 2505.23628)는 §1 에서 개념화를 핵심으로 내세운다. 근거로 여섯 편을 단다.

"Central to our innovation is conceptualization (Wang et al., 2023c; Bai et al., 2024c; Wang et al., 2023b; He et al., 2024; Wang et al., 2024a,c)"

| 인용 키 | 논문 | 무엇을 물려받았나 |
|---|---|---|
| Wang 2023c | CAT (ACL 2023) | 사건 개념화의 틀. `[확인]` 이벤트 프롬프트 예시 "Sam playing with his dog → relaxing event" 가 CAT·서베이의 "relaxing event" 예시와 같은 계열이다 |
| Bai 2024c | Intention KG (arXiv 2412.11500, EACL 2026) | 프롬프트 문면. `[확인]` AutoSchemaKG 의 엔티티·관계 프롬프트에 "These abstract intention words should fulfill the following requirements" 가 그대로 남아 있다. 같은 Llama-3-8B-Instruct 를 쓴다 |
| Wang 2023b | CAR (Findings EMNLP 2023) | 개념화를 QA distractor 생성에 쓴 사례 |
| He 2024 | AbstractATOMIC (AIJ) | 사건 개념화 데이터와 검증기 |
| Wang 2024a | CANDLE (ACL 2024) | LLM 으로 개념을 생성하는 방식 |
| Wang 2024c | AbsInstruct (ACL 2024) | LLM 의 추상화 능력 instruction tuning |

`[확인]` 같은 문단 뒤쪽은 AbsPyramid 와 서베이를 근거로 단다. "provides hierarchical organization supporting both specific and abstract reasoning (Wang et al., 2024d,b)."

`[확인]` 이벤트 프롬프트의 예시 두 개는 AbsPyramid Figure 1 의 예시와 같은 문장이다. "A man retreats to mountains and forests", "A cat chased a prey into its shelter".

`[확인]` 바꾼 점도 있다. Intention KG 프롬프트는 "The ABSTRACT INTENTION phrases of the same INTENTION cannot be semantically similar to each other." 라는 조건을 둔다.

`[확인]` AutoSchemaKG 프롬프트에는 이 조건이 없다. 대신 "Write at least 3 or more phrases at different abstract level if possible." 가 들어갔다.

`[확인]` 문맥은 엔티티에만 붙는다. "Events and relations ... rely solely on their textual descriptions without additional context" (부록 B.2.2). CAT 가 경고한 문맥 없는 개념화가 사건·관계 쪽에 그대로 남는다.

`[추정]` 서베이 분류로는 zero-shot generative 계열이다. 근거는 학습 없이 프롬프트만으로 개념 구를 생성한다는 §3·부록 B.2 의 서술이다. 서베이가 권하는 후처리 필터는 AutoSchemaKG 본문에 나오지 않는다.

## 2. Keyphrase·term·concept mention extraction

문서 안의 구를 골라 주제를 대표하게 하는 일이다.

`[확인]` CopyRNN 의 정의: "A keyphrase or keyword is a piece of short, summative content that expresses the main semantic meaning of a longer text." 같은 논문은 원문에 없는 것을 "absent keyphrases" 로, 원문 구간과 맞는 것을 "present keyphrases" 로 나눈다.

`[확인]` 용어 추출(ATE)은 용어와 개념을 나눈다. TermEval 2020 은 용어를 "lexical items that represent concepts of a domain" 로 인용해 정의한다.

### 대표 논문

| 논문 | 방법 | 지도 | 평가 | 코드 | 원문 |
|---|---|---|---|---|---|
| TextRank. Mihalcea, Tarau. EMNLP 2004. [W04-3252](https://aclanthology.org/W04-3252/) | 명사·형용사로 공기 그래프를 만들고 PageRank 를 돌린다. 인접한 상위 단어를 이어 구로 만든다 | 없음 | Inspec 500 초록. P 31.2 / R 43.1 / F 36.2 | — | 전문 |
| RAKE. Rose, Engel, Cramer, Cowley. Text Mining (Wiley), 2010, pp.1–20. DOI 10.1002/9780470689646.ch1 | — (원문을 못 열어 방법 주장을 적지 않는다) | — | — | 저자 저장소 못 찾음 | 못 엶 |
| YAKE. Campos 외. ECIR 2018 short paper, LNCS 10772 pp.684–691. [INESC TEC 사본](https://repositorio.inesctec.pt/items/9efb636a-2d52-4573-9cfc-2e56845e0a4a) | 단어마다 통계 특징 다섯(대소문자, 위치, 빈도, 문맥 관련도, 문장 분산)을 매긴다. 1~3-gram 후보에 점수를 준다. 낮을수록 중요하다 | 없음 | SemEval2010 등 4종. top-10 정확 일치 P/R/F1 | [INESCTEC/yake](https://github.com/INESCTEC/yake) | 전문 |
| KeyBERT. Grootendorst. 논문 없음, Zenodo DOI 10.5281/zenodo.4461265 | 문서 임베딩과 n-gram 임베딩의 cosine 으로 고른다. MMR·MaxSum 으로 다양화한다 | 사전학습 임베딩만 | 평가 없음 | [MaartenGr/KeyBERT](https://github.com/MaartenGr/KeyBERT) | 저장소 |
| Sahrawat 외. "Keyphrase Extraction as Sequence Labeling Using Contextualized Embeddings". ECIR 2020. [arXiv 1910.08840](https://arxiv.org/abs/1910.08840) | 고정한 문맥 임베딩 위 BiLSTM-CRF 로 B/I/O 를 단다 | 지도 | Inspec, SemEval-2010/2017 초록. P/R/F1 | 데이터만 확인 | 전문(arXiv 판) |
| CopyRNN. Meng 외. "Deep Keyphrase Generation". ACL 2017. [P17-1054](https://aclanthology.org/P17-1054/) | copy 기구가 있는 encoder-decoder 가 present·absent keyphrase 를 생성한다 | 지도(2.78M 쌍) | KP20k 등 5종. present F1@5/10, absent R@10/50 | [memray/seq2seq-keyphrase](https://github.com/memray/seq2seq-keyphrase) | 전문 |
| TermEval 2020 / ACTER. Rigouts Terryn, Hoste, Drouin, Lefever. COMPUTERM@LREC 2020. [2020.computerm-1.12](https://aclanthology.org/2020.computerm-1.12/) | 3개 언어·4개 도메인 용어 주석 데이터와 shared task | 참가 시스템마다 다름. 1위는 BERT 이진 분류 | P/R/F1. 영어 1위 F1 46.7 | [AylaRT/ACTER](https://github.com/AylaRT/ACTER) | 전문 |
| Pan, Wang, Li, Li, Tang. "Course Concept Extraction in MOOCs via Embedding-Based Graph Propagation". IJCNLP 2017. [I17-1088](https://aclanthology.org/I17-1088/) | 명사구 후보를 백과사전 코퍼스 임베딩으로 잇고, 시드에서 신뢰도를 전파한다 | 라벨 없음. 정답 10% 를 종료 조건에만 쓴다 | Coursera·XuetangX 4종. R-precision, MAP | 공개 예정이라고만 적음 | 전문 |
| Song 외. "Is ChatGPT A Good Keyphrase Generator? A Preliminary Study". [arXiv 2303.13001](https://arxiv.org/abs/2303.13001) | ChatGPT zero-shot 프롬프트 6종을 지도 생성기와 견준다 | ChatGPT 는 없음 | KP20k 등. F1@5, F1@M | 데이터만 | 전문 |
| ConExion. Norouzi, Hertling, Sack. NSLP@ESWC 2025. [arXiv 2504.12915](https://arxiv.org/abs/2504.12915) | 오픈 LLM zero/few-shot 으로 도메인 개념을 뽑고, 문서에 없는 것은 버린다 | 없음 | Inspec F1 0.451(TextRank 0.287), SemEval2017 0.311 | [concept_extraction](https://github.com/ISE-FIZKarlsruhe/concept_extraction) | 전문 |

`[확인]` 교육 분야는 출력을 "concept" 라고 부른다. Pan 2017 의 정의: "we use course concepts to refer to the knowledge concepts taught in the course videos". MOOCCube(ACL 2020)는 이 방법으로 영상마다 개념 10개를 뽑아 쓴다.

`[확인]` ConExion 은 목표를 키프레이즈와 다르게 잡는다. "extracting all present concepts related to the specific domain, not just the important ones"

### 변형 표기 처리

갈래 안에서도 같은 개념의 다른 표기를 다루는 방식이 다르다.

| 방법 | 처리 |
|---|---|
| TextRank, Sahrawat | 없다 |
| YAKE | Levenshtein 거리로 비슷한 후보를 지운다. 실험 임계값 0.8. 저장소는 v0.6.0 부터 lemmatization 도 지원한다 |
| ACTER | "all terms are lowercased, and only identical lowercased terms are merged in a single entry, without lemmatisation." |
| CopyRNN, ChatGPT 평가 | Porter stemmer 로 평가 때만 맞춘다 |
| ConExion | 문서에 글자 그대로 있는지로만 거른다 |

`[확인]` Pan 2017 은 표기 분산을 문제로 짚기만 하고 병합은 하지 않는다. "a disambiguated course concept tends to be expressed in various ways, which produces many scattered infrequent terms. For example, "Q sort" is a colloquial expression referring to quick sort, and "partition exchange sort" is another name for quick sort."

### 원문이 밝힌 한계

- `[확인]` TextRank: "the maximum recall that can be achieved on this collection is less than 100%, since indexers were not limited to keyword extraction – as our system is – but they were also allowed to perform keyword generation"
- `[확인]` YAKE: "an exact match between the ground-truth and the methods keyword is usually used as a rule-of-thumb thus impeding partial matches."
- `[확인]` CopyRNN: "Our current model does not fully consider correlation among target keyphrases."
- `[확인]` TermEval 2020: "it remains a challenging task, not in the least because terms are so difficult to define."
- `[확인]` Pan 2017: "many highly technical course concepts are not covered by generic semantic resources, including Wikipedia and WordNet."
- `[확인]` ChatGPT 평가: "ChatGPT still faces challenges when it comes to generating absent keyphrases."
- `[확인]` ConExion: "One limitation of this work is its reliance on exact lexical matching to filter concepts ... it fails to account for situations where an LLM generates semantically accurate concepts that do not have an exact match in the text."

## 3. Entity typing

문맥 속 mention 에 유형 이름을 붙이는 일이다. 유형 이름이 곧 개념 이름표다.

`[확인]` Ultra-fine typing 의 정의: "given a sentence with an entity mention, the goal is to predict a set of free-form phrases (e.g. skyscraper, songwriter, or criminal) that describe appropriate types for the target entity" ([Choi et al. 2018](https://aclanthology.org/P18-1009/))

`[확인]` 같은 논문은 유형이 문장 속 역할에 달렸다고 적는다. "appropriate types for the role the target entity plays in the sentence"

`[확인]` "free-form" 이라 해도 평가와 학습은 약 10K 어휘 안에서 한다. "a type vocabulary of about 10K frequent noun phrases"

### 대표 논문

| 논문 | 방법 | 유형 어휘 | 평가 | 코드 | 원문 |
|---|---|---|---|---|---|
| FIGER. Ling, Weld. "Fine-Grained Entity Recognition". AAAI 2012. [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/8122) | CRF 로 구간을 찾고 perceptron 이 여러 태그를 고른다. Wikipedia anchor → Freebase 로 distant 감독 | 112개, 손으로 병합 | 뉴스 434문장. Strict/Loose F1 | ai.cs.washington.edu/pubs/310 | 전문 |
| Gillick 외. "Context-Dependent Fine-Grained Entity Type Tagging". [arXiv 1412.1820](https://arxiv.org/abs/1412.1820) | 문맥에서 추론되는 유형만 허용한다. 3단 트리, maxent | Freebase 유래 계층 | OntoNotes 77문서. 층별 P/R/F1 | — | 전문 |
| Choi, Levy, Choi, Zettlemoyer. "Ultra-Fine Entity Typing". ACL 2018. [P18-1009](https://aclanthology.org/P18-1009/) | 모든 명사구·대명사를 대상으로 한다. 크라우드 6K 와 head word·위키 정의 distant 감독. BiLSTM+attention | 약 10K, 계층 없음 | macro P/R/F1, MRR. 테스트 F1 32.0 | [nlp.cs.washington.edu/entity_type](http://nlp.cs.washington.edu/entity_type) | 전문 |
| Onoe, Durrett. "Learning to Denoise Distantly-Labeled Data for Entity Typing". NAACL 2019. [N19-1250](https://aclanthology.org/N19-1250/) | distant 데이터를 filter 와 relabeler 로 정제한다 | UFET 어휘 | UFET macro F1 40.2 | [DenoiseET](https://github.com/yasumasaonoe/DenoiseET) | 전문 |
| MLMET. Dai, Song, Wang. ACL 2021. [2021.acl-long.141](https://aclanthology.org/2021.acl-long.141/) | 문장에 "[MASK] such as M" 같은 Hearst 패턴을 끼우고 BERT 가 채운 단어를 약한 라벨로 쓴다 | 10,331 | UFET F1 49.1 | [HKUST-KnowComp/MLMET](https://github.com/HKUST-KnowComp/MLMET) | 전문 |
| LITE. Li, Yin, Chen. TACL 2022. [2022.tacl-1.35](https://aclanthology.org/2022.tacl-1.35/) | "[ENTITY] is a [LABEL]" 를 hypothesis 로 둔 NLI 로 어휘 전체에 순위를 매긴다 | 어휘 전체 | UFET F1 50.6 | [luka-group/lite](https://github.com/luka-group/lite) | 전문 |
| CASENT. Feng, Pratapa, Mortensen. Findings EMNLP 2023. [2023.findings-emnlp.1040](https://aclanthology.org/2023.findings-emnlp.1040/) | 어휘 제약 beam search 로 유형을 생성하고 확률을 calibration 한다. ChatGPT 를 견준다 | 10,331 | UFET F1 51.3. ChatGPT 0-shot 17.6, 16-shot 41.5 | [yanlinf/CASENT](https://github.com/yanlinf/CASENT) | 전문 |
| P2GT. Chen, Zhang, Wang, Roth. CoNLL 2020. [arXiv 2010.06724](https://arxiv.org/abs/2010.06724) | 사건 과정(단계 목록)에 action·object 두 축의 free-form 유형을 붙인다 | action 1,000+, object 10,000+ | wikiHow 과정 | — | 전문 |

`[확인]` MLMET 은 갈래 3과 갈래 4를 잇는다. 이 방법은 "context dependent hypernyms of the mention" 을 예측해 유형 라벨로 쓴다.

`[확인]` P2GT 는 AutoSchemaKG 가 사건 개념 평가에 쓴 데이터의 출처다(AutoSchemaKG 부록 C.1).

### 유형 정규화

`[확인]` 이 갈래는 모두 닫힌 어휘로 개념을 정규화한다. 어휘 밖 이름은 버리거나 가장 가까운 어휘로 바꾼다.

| 방법 | 처리 |
|---|---|
| FIGER | "manually merging too specific types, e.g. /olympics/olympic games and /soccer/football world cup are merged into Sports Event" |
| Gillick | "Whenever there was any ambiguity in the mapping, we backed off to a common parent in the hierarchy." |
| Choi | 크라우드 라벨을 WordNet 가장 흔한 의미의 동의어·상위어로 넓힌다. distant 라벨은 소문자화와 단수화를 거친다 |
| MLMET | "we first sigularize the most probable words that are plural. Then, remove those that are not in the type vocabulary of the dataset." |

`[확인]` CASENT 는 열린 어휘를 LLM 에 그대로 줄 수 없다고 적는다. "For the UFET dataset, it is not feasible to provide the model with the entire type vocabulary."

### 원문이 밝힌 한계

- `[확인]` Choi 2018: "Despite our efforts to annotate a comprehensive type set, the gold labels still miss many potentially correct labels"
- `[확인]` Choi 2018: "sometimes “location” and “place” are annotated interchangeably"
- `[확인]` MLMET: "the model cannot produce multi-word types (e.g., football player) or single word types that are not present in the BERT MLM vocabulary."
- `[확인]` LITE: 어휘 10K 이상에서 "it takes about 35 seconds per new sentence for our model to do inference"
- `[확인]` CASENT: "ChatGPT exhibits poor zero-shot performance with significantly low recall."

## 4. Ontology learning 의 개념층

텍스트에서 용어(개념)와 그 사이 is-a 관계를 뽑아 taxonomy 를 만드는 일이다.

`[확인]` Hearst 1992 의 정의: "a concept represented by a lexical item L0 is said to be a hyponym of the concept represented by a lexical item L1 if native speakers of English accept sentences constructed from the frame An L0 is a (kind of) L1." ([C92-2082](https://aclanthology.org/C92-2082/))

`[확인]` OntoLearn Reloaded 는 개념과 용어를 구분하지 않는다. "we use the words concepts and terms interchangeably"

### 대표 논문

| 논문 | 방법 | 입출력 | 평가 | 코드·데이터 | 원문 |
|---|---|---|---|---|---|
| Hearst. "Automatic Acquisition of Hyponyms from Large Text Corpora". COLING 1992. [C92-2082](https://aclanthology.org/C92-2082/) | "NP such as NP", "NP and other NP" 등 손으로 만든 패턴 6개 | 텍스트 → hyponym 쌍 | Grolier 백과사전. WordNet 과 대조 | — | 전문(OCR) |
| Snow, Jurafsky, Ng. NIPS 2004. [proceedings](https://proceedings.neurips.cc/paper/2004/hash/358aee4cc897452c00244351e4d91f69-Abstract.html) | 의존 경로 특징을 WordNet distant 라벨로 학습해 Hearst 패턴을 일반화한다 | 명사 쌍 → 이진 판정 | 수동 5,387쌍. 최대 F 0.3592 | — | 전문 |
| Roller, Kiela, Nickel. "Hearst Patterns Revisited". ACL 2018. [P18-2057](https://aclanthology.org/P18-2057/) | 대형 코퍼스 Hearst 추출 + PPMI·SVD 점수가 분포 기반 방법을 이긴다 | 쌍 → 점수 | BLESS 등. AP, Acc, Spearman | [hypernymysuite](https://github.com/facebookresearch/hypernymysuite) | 전문 |
| SemEval-2018 Task 9. Camacho-Collados 외. [S18-1115](https://aclanthology.org/S18-1115/) | hypernym discovery 공유 과제 | 용어 + 코퍼스 → 어휘 안 hypernym 최대 15개 순위 | MAP. 최고 영어 19.78, 의학 34.05, 음악 40.97 | [CodaLab](https://competitions.codalab.org/competitions/17119) | 전문 |
| OntoLearn Reloaded. Velardi, Faralli, Navigli. Computational Linguistics 39(3), 2013. [J13-3007](https://aclanthology.org/J13-3007/) | 용어 추출 → 정의문에서 genus(상위어) 추출 → 그래프 가지치기로 DAG taxonomy | 도메인 코퍼스 → taxonomy | 6개 도메인. WordNet·MeSH 와 비교 | 데이터 페이지 404 | 전문(핵심 절) |
| Text2Onto. Cimiano, Völker. NLDB 2005. DOI 10.1007/11428817_21 | 학습한 객체마다 confidence 를 붙여 Probabilistic Ontology Model 에 둔다 | 코퍼스 → 온톨로지 | — | — | 초록 |
| LLMs4OL. Babaei Giglou, D'Souza, Auer. ISWC 2023. [arXiv 2307.16648](https://arxiv.org/abs/2307.16648) | LLM zero-shot 프롬프트로 term typing·taxonomy discovery·비분류 관계를 푼다 | 용어 → 유형 / 유형 쌍 → 참·거짓 | MAP@1, F1. GeoNames typing 39.4(GPT-4) | [LLMs4OL](https://github.com/HamedBabaei/LLMs4OL) | 전문 |
| LLMs4OL 2024 Challenge. Babaei Giglou 외. Open Conference Proceedings 4. [arXiv 2409.10146](https://arxiv.org/abs/2409.10146) | 같은 과제의 공개 경진. 처음 보는 온톨로지로 zero-shot 단계를 둔다 | 위와 같음 | 집합 P/R/F1. UMLS 비분류 관계 F1 0.0783 | [Challenge](https://github.com/HamedBabaei/LLMs4OL-Challenge-ISWC2024) | 전문 |
| Chain-of-Layer. Zeng 외. CIKM 2024. [arXiv 2402.07386](https://arxiv.org/abs/2402.07386) | LLM 이 위층부터 층 단위로 taxonomy 를 짓고, Hearst 템플릿 기반 순위 필터로 거른다 | 개념 목록 → taxonomy | WordNet 등. ancestor·edge F1 | [chain-of-layer](https://github.com/qingkaizeng/chain-of-layer) | 전문 |

`[확인]` LLMs4OL 의 WordNet term typing 에서 "type" 은 품사다. 원문은 "four term types (noun, verb, adverb, adjective)" 라고 적는다. 개념 typing 성적으로 읽으면 안 된다.

`[확인]` LLM taxonomy 논문(Chen 2023, Chain-of-Layer, LLMs4OL Task B)은 개념 목록을 입력으로 받는다. 문장에서 개념을 뽑는 단계는 이 논문들의 범위 밖이다.

`[확인]` SemEval-2018 Task 9 는 너무 일반적인 상위어를 막으려고 "a blacklist of very general terms" 를 둔다.

### 원문이 밝힌 한계

- `[확인]` Hearst 1992: "A more common problem is underspecification."
- `[확인]` Roller 2018: "a well-known problem of Hearst-like patterns is their extreme sparsity: words must co-occur in exactly the right configuration, or else no relation can be detected."
- `[확인]` OntoLearn Reloaded: "When both concepts and relations are unknown, it is almost impossible to replicate a reference taxonomy accurately."
- `[확인]` SemEval-2018 Task 9: "this newly-proposed task proved to be challenging for all participating systems, leaving considerable room for improvement."
- `[확인]` LLMs4OL: "foundational LLMs are not sufficiently suitable for ontology construction that entails a high degree of reasoning skills and domain expertise"
- `[확인]` Chain-of-Layer: "the performance of our proposed approach on large-scale taxonomies is constrained by the limitations in instruction-following capabilities and the context window size of LLMs."

## 5. LLM 시대 KG 구축·canonicalization·schema induction

LLM 이 텍스트에서 노드·관계를 뽑은 뒤, 같은 뜻의 다른 표현을 하나로 묶는 일(canonicalization)과 유형 체계를 유도하는 일(schema induction)이다.

`[확인]` EDC 는 이 문제를 이렇게 적는다. "the resulting triplets typically contain redundant and ambiguous information, e.g., multiple semantically equivalent relation phrases such as ‘profession’, ‘job’, and ‘occupation’"

`[확인]` 이 갈래의 canonicalization 은 LLM 이전 Open KB 연구에서 시작했다. Galárraga 2014 와 CESI 2018 이 그 기준점이다.

### 대표 논문

| 논문 | 방법 | 평가 | 코드 | 원문 |
|---|---|---|---|---|
| Galárraga, Heitz, Murphy, Suchanek. "Canonicalizing Open Knowledge Bases". CIKM 2014. [PDF](https://suchanek.name/work/publications/cikm2014.pdf) | 명사구는 손으로 만든 유사도 특징 + HAC 로 묶는다. 동사구는 AMIE 규칙으로 동치를 찾는다 | ReVerb 기반 Base·Ambiguous. P/R/F1 | 없음 | 전문 |
| CESI. Vashishth, Jain, Talukdar. WWW 2018. [arXiv 1902.00172](https://arxiv.org/abs/1902.00172) | side information(PPDB, WordNet, 개체 연결 등)을 soft constraint 로 넣은 KG 임베딩 위에서 HAC | ReVerb45K. macro/micro/pairwise F1 | [malllabiisc/cesi](https://github.com/malllabiisc/cesi) | 전문 |
| CMVC. Shen, Yang, Liu. KDD 2022. [arXiv 2206.11130](https://arxiv.org/abs/2206.11130) | fact view(TransE)와 context view(BERT)를 함께 k-means 로 군집화한다 | ReVerb45K 등. 평균 F1 0.812 | [Yang233666/cmvc](https://github.com/Yang233666/cmvc) | 전문 |
| EDC. Zhang, Soh. EMNLP 2024. [arXiv 2404.03868](https://arxiv.org/abs/2404.03868) | LLM OIE → LLM 이 관계 정의를 쓴다 → 정의 임베딩으로 후보를 찾고 LLM 이 검증해 관계를 정규화한다 | WebNLG, REBEL, Wiki-NRE. Partial/Strict/Exact F1 | [clear-nus/edc](https://github.com/clear-nus/edc) | 전문 |
| Sha Li 외. "Open-Domain Hierarchical Event Schema Induction by Incremental Prompting and Verification". ACL 2023. [2023.acl-long.312](https://aclanthology.org/2023.acl-long.312) | GPT-3 로 사건 schema 뼈대를 만들고 늘린 뒤 관계를 검증한다 | RESIN-11, ODIN, ProScript. Event·Relation F1 | [inc-schema](https://github.com/raspberryice/inc-schema) | 전문 |
| Dror, Wang, Roth. "Zero-Shot On-the-Fly Event Schema Induction". Findings EACL 2023. [arXiv 2210.06254](https://arxiv.org/abs/2210.06254) | GPT-3 로 문서를 생성하고 SRL·NER·coref 결과의 빈도로 schema 를 만든다 | Schema-11 등. coverage, HITS@1 | CogComp 저장소(검색 결과로만) | 전문 |
| iText2KG. Lairgi 외. [arXiv 2409.03284](https://arxiv.org/abs/2409.03284), 2024 | 문서마다 KG 를 만들고 전역 KG 에 증분으로 합친다. cosine 임계값으로 개체를 맞춘다 | CV·웹·논문 각 5. 일관성, triplet precision | [AuvaLab/itext2kg](https://github.com/AuvaLab/itext2kg) | 전문 |
| KGGen. Mo 외. [arXiv 2502.09956](https://arxiv.org/abs/2502.09956), v2 는 NeurIPS 2025 | LLM 추출 뒤 개체·관계를 군집화해 대표 이름을 고른다. v1 과 v2 의 군집화 절차가 다르다 | MINE-1·MINE-2, SemEval-2010 | [stair-lab/kg-gen](https://github.com/stair-lab/kg-gen) | 전문(v1, v2) |
| GraphRAG. Edge 외. [arXiv 2404.16130](https://arxiv.org/abs/2404.16130) | LLM 이 개체·관계를 뽑고 커뮤니티 요약을 만든다 | — (이 조사에서는 병합 방식만 읽었다) | microsoft/graphrag | 전문 |

`[확인]` LLM 프롬프트로 "concept extraction" 을 목표로 내건 논문은 ConExion(갈래 2)을 찾았다.

`[확인]` LLM 으로 Open KB canonicalization 을 다룬 2024–25 논문은 두 번 검색해도 찾지 못했다. 검색에 걸린 COMBO(EACL 2023)와 MulCanon(arXiv 2403.14733)은 원문을 열지 않았다. 둘 다 미확인이다.

### 병합 방식

이 갈래의 핵심은 무엇을 기준으로 같다고 보느냐다.

| 방식 | 논문 | 원문 |
|---|---|---|
| 정확 문자열 | GraphRAG | "our analysis uses exact string matching for entity matching" |
| 손으로 만든 유사도 + HAC | Galárraga 2014 | "we use Hierarchical Agglomerative Clustering (HAC) on the set of mentions" / "the IDF token overlap is the strongest signal of synonymy for noun phrases on the Web" |
| 학습 임베딩 + HAC | CESI | "HAC using cosine similarity over the embeddings" / "The threshold value for HAC was chosen based on held out validation dataset." |
| 두 view 군집화 | CMVC | "we leverage Caliński-Harabasz (CH) index [10] as the weight of each view" |
| 임베딩 임계값 한 번 | iText2KG | "An upper threshold (e.g., 0.7) was chosen to ensure high precision" |
| 문자열·임베딩 임계값으로 새 항목 버림 | Sha Li 2023 | "If the event description, event name, or the embedding of the event description is sufficiently similar to an existing event in the schema, we will discard the new event." 각주: "This threshold is determined empirically, and we set it to 0.9 for Jaro-Winkler string similarity, 0.85 for embedding cosine similarity." |
| 임베딩 후보 + LLM 검증 | EDC | "searching for potential consolidation candidates through vector similarity and LLM verification" |
| 임베딩 군집 + 검색 + LLM 판정 | KGGen v2 | "cluster using k-means into clusters of 128 items" → "we retrieve the top-k most semantically similar items, where k=16, using a fused BM25 and semantic embedding approach" → "the LLM is prompted to identify exact duplicates from this set, considering variations in tense, plurality, case, abbreviations, and shorthand forms" |
| LLM 만으로 반복 군집 | KGGen v1 | "The entire entities list is passed in context to the LLM, and it attempts to extract a single cluster." |

`[확인]` EDC 는 LLM 검증을 넣은 까닭을 과잉 병합으로 든다. "by allowing the LLMs to verify if a transformation can be performed (instead of solely relying on the embedding similarity), EDC alleviates the over-generalization issue faced by previous methods."

`[확인]` EDC 의 정규화 대상은 관계(schema)뿐이다. 엔티티 중복 제거는 하지 않는다.

`[확인]` GraphRAG 는 중복을 그대로 둬도 괜찮다고 본다. "GraphRAG is generally resilient to duplicate entities since duplicates are typically clustered together for summarization in subsequent steps."

`[추정]` KGGen 의 대표 수치 66.07% 는 GPT-4o 로 낸 값으로 보인다. 근거: §4.1 은 Gemini 2.0 Flash 를 쓴다고 적는데, Table 1 의 Gemini 2.0 Flash 는 44%, GPT-4o 는 66% 다.

### 원문이 밝힌 한계

- `[확인]` CESI: "Toyota and Nissan have been embedded together although the two being different companies."
- `[확인]` Galárraga 2014: "In general, we can cluster only a very small portion of the verbal phrases."
- `[확인]` EDC: "We only considered schema canonicalization within the scope of this paper, it is of great interest to incorporate an entity de-duplication mechanism in the future"
- `[확인]` EDC: "EDC is a costly framework, involving a large number of LLM calls."
- `[확인]` iText2KG: "Future research will focus on enhancing metrics such as cosine similarity ..., eliminating the necessity to define a threshold as a hyperparameter, and integrating the entity type as a parameter of the matching process."
- `[확인]` KGGen(v2): "its graphs still exhibit problems, like over or under de-duplication of entities and relations"
- `[확인]` Sha Li 2023: "LMs ... sometimes show inconsistent behavior between different runs or when using different prompts with the same meaning"

## 6. 임상 concept extraction 과 concept normalization

의료 문서에서 개념 구간을 찾고, 그 구간을 표준 용어 체계의 개념에 잇는 일이다. 요청 목록에 없던 갈래다. "concept extraction" 이라는 이름을 글자 그대로 쓰는 분야라서 더했다.

| 논문 | 무엇을 개념이라 부르나 | 방법·평가 | 원문 |
|---|---|---|---|
| Uzuner, South, Shen, DuVall. "2010 i2b2/VA challenge on concepts, assertions, and relations in clinical text". JAMIA 18(5), 2011. [PMC3168320](https://pmc.ncbi.nlm.nih.gov/articles/PMC3168320/) | "Given unannotated text of patient reports, systems had to identify and extract the text corresponding to patient medical problems, treatments, and tests." | 학습 394, 테스트 477 보고서. 최고 exact F 0.852 | 전문(부록 제외) |
| Aronson. "Effective Mapping of Biomedical Text to the UMLS Metathesaurus: The MetaMap Program". Proc AMIA Symp 2001. [PDF](https://lhncbc.nlm.nih.gov/system/files/pub2001032.pdf) | "MetaMap is a highly configurable program that maps biomedical text to concepts in the UMLS Metathesaurus." | 명사구 → 약어·동의어·파생·굴절 변형 생성 → 후보 점수 → 매핑. 정량 평가 없음 | 전문 |

`[확인]` i2b2 2010 은 구간과 유형까지만 요구한다. UMLS 정규화는 본문 과제에 없다.

`[확인]` MetaMap 은 이 조사에서 표기 변형을 온톨로지 개념 하나로 모으는 유일한 방법이다.

`[확인]` 원문의 변형 정의: "A variant consists of a phrase word (called a generator) together with all its acronyms, abbreviations, synonyms, derivational variants, meaningful combinations of these, and finally inflectional and spelling variants"

### 원문이 밝힌 한계

- `[확인]` i2b2 2010: "The concept extraction systems benefited the most from textual features and reported disappointing gains from the inclusion of knowledge-rich resources such as the UMLS."
- `[확인]` i2b2 2010: "The most challenging examples for the concept extraction systems were abbreviations, for example, CXR for chest x-ray, and descriptive concept phrases"
- `[확인]` MetaMap: "The mappings for complications illustrate MetaMap's most difficult problem: ambiguity."

## 7. 해석가능성의 concept·feature

이름만 같은 다른 문제다. 입력은 문장이 아니라 학습된 모델이다. 출력은 텍스트 속 구가 아니라 모델 내부의 방향이나 중간층이다.

`[확인]` TCAV 와 Concept Bottleneck Model(CBM)은 사람이 개념을 미리 정한다.

`[확인]` TCAV 는 예시 집합으로 정한다. "to define concept 'curly', a set of hairstyles and texture images can be used" ([Kim et al. ICML 2018](https://proceedings.mlr.press/v80/kim18d.html))

`[확인]` CBM 은 학습 데이터에 개념 라벨을 단다. "an intermediate set of human-specified concepts c like 'joint space narrowing' and 'bone spurs' ... trained on data points (x, c, y)" ([Koh et al. ICML 2020](https://arxiv.org/abs/2007.04612))

`[확인]` Sparse autoencoder 연구는 개념을 미리 정하지 않는다. 활성 공간에서 비지도로 방향을 찾고, 그것을 "feature" 라 부른다. "We call these directions features" ([Bricken et al. 2023, Towards Monosemanticity](https://transformer-circuits.pub/2023/monosemantic-features/index.html)) 같은 계열의 [Cunningham et al. ICLR 2024](https://arxiv.org/abs/2309.08600)는 Pythia 의 residual stream 에서 같은 일을 한다.

`[확인]` 이 갈래도 자기 개념의 실재를 유보한다. Bricken 2023: "are models in some fundamental sense composed of features or are features just a convenient post-hoc description? ... we take an agnostic position" CBM: "A drawback of concept bottleneck models is that they require annotated concepts at training time."

`[추정]` 갈래 1~6과 닿는 자리는 하나다. SAE feature 에 사람이 붙이는 설명이 1~2단어 개념 이름표와 비슷한 모양이 된다. 근거: Cunningham 2023 은 feature 설명을 언어 모델로 자동 생성해 평가한다(autointerpretability). 이 방향을 문장 개념 추출에 쓴 논문은 찾지 않았다.

## 갈래 비교

| 갈래 | 개념의 정의 | 출력 모양 | 지도 필요 | 대표 방법 | 대표 리소스 |
|---|---|---|---|---|---|
| 1 Conceptualization | 인스턴스를 덮는 추상 범주 | 개체·사건 → 개념 목록(+점수) | 방법마다 다름. Probase 는 없음, CAT 는 semi, CANDLE 은 LLM + critic | Probase, Song 2011, CAT, CANDLE | Probase, AbstractATOMIC, AbsPyramid |
| 2 Keyphrase·term | 문서 주제를 대표하는 구 / 도메인 개념을 나타내는 용어 | 문서 → 순위 매긴 구 목록, 또는 BIO 구간 | TextRank·YAKE·KeyBERT 는 없음. CopyRNN·sequence labeling 은 지도 | TextRank, YAKE, CopyRNN | Inspec, KP20k, ACTER |
| 3 Entity typing | 문맥 속 mention 의 유형 | mention → 닫힌 어휘 안 유형 집합 | 지도 또는 distant | FIGER, UFET, MLMET, LITE | UFET(10,331 유형), FIGER(112) |
| 4 Ontology learning | 용어와 is-a 계층 | 쌍 또는 taxonomy(DAG) | Hearst 는 없음. Snow 는 distant | Hearst, OntoLearn, LLMs4OL | WordNet, SemEval-2018 Task 9 |
| 5 LLM KG·canonicalization | 같은 뜻 표현을 묶은 대표 이름 / 유도한 schema 유형 | 정규화한 노드·관계, schema 그래프 | LLM zero/few-shot. CESI 는 임베딩 학습 | EDC, KGGen, CESI | ReVerb45K, MINE |
| 6 임상 concept | 의료 문서 속 problem·test·treatment / UMLS 개념 | 유형 붙은 구간 / 개념 매핑 | i2b2 1위는 지도. MetaMap 은 지식 기반 | i2b2 2010 시스템, MetaMap | i2b2 2010, UMLS |
| 7 해석가능성 | 사람이 정한 속성 / 활성 공간 방향 | 모델 내부 벡터·층 | CBM 은 개념 라벨 필요. SAE 는 없음 | TCAV, CBM, SAE | — |

## AutoSchemaKG 방식의 자리

AutoSchemaKG 의 개념 단계는 갈래 1의 zero-shot 생성 방식이다. 출력 모양은 갈래 3의 ultra-fine typing 과 닮았지만 어휘가 닫혀 있지 않다. 병합은 이 조사의 여러 갈래 중 가장 단순한 쪽인 정확 문자열 일치다.

### 흐름

1. AutoSchemaKG 는 그래프의 엔티티·사건·관계마다 LLM 에 1~2단어 개념 구를 3개 이상 쓰게 한다.
2. 이 일은 갈래 1의 zero-shot generative conceptualization 이다.
3. 출력이 자유로운 짧은 명사구 집합이라는 점은 갈래 3의 UFET 와 닮았다.
4. 갈래 3은 그 구를 닫힌 어휘로 정규화한다. AutoSchemaKG 에는 닫힌 어휘가 없다.
5. 그래서 같은 개념인지는 글자로만 정해진다.
6. 선행 연구는 표기 변형, 너무 일반적인 개념, 다의어를 각자 다른 장치로 다뤘다.
7. AutoSchemaKG 에는 이 세 장치가 모두 없다. 이전 회차 실험에서 그 결과가 실제로 보였다.

### 세부

**1. AutoSchemaKG 는 그래프의 엔티티·사건·관계마다 LLM 에 1~2단어 개념 구를 3개 이상 쓰게 한다.**

`[확인]` "The LLM generates at least three phrases per element that encapsulate its type or related concepts at varying abstraction levels." (ACL 판 §3)

`[확인]` 엔티티 프롬프트는 "several phrases containing 1-2 words for the ABSTRACT ENTITY of this ENTITY" 를 요구한다. 예시 출력은 "Thinkpad X60 → Thinkpad, laptop, machine, device, hardware, computer, brand" 다. (부록 B.2, Figure 6)

**2. 이 일은 갈래 1의 zero-shot generative conceptualization 이다.**

`[확인]` AutoSchemaKG 는 갈래 1의 KnowComp 논문 여섯 편을 개념화의 근거로 단다(#1 AutoSchemaKG 가 잇는 선행 연구).

`[추정]` 서베이 분류의 zero-shot generative 계열에 해당한다. 근거: 학습이나 개념 사전 없이 프롬프트 출력만 쓴다. AutoSchemaKG 가 이 분류를 스스로 쓰지는 않는다.

**3. 출력이 자유로운 짧은 명사구 집합이라는 점은 갈래 3의 UFET 와 닮았다.**

`[확인]` UFET 의 출력은 "a set of free-form phrases (e.g. skyscraper, songwriter, or criminal)" 다. 위 Thinkpad 예시 출력도 같은 모양이다.

`[확인]` AutoSchemaKG 의 개념 평가도 typing 데이터를 쓴다. 개체는 FB15kET·YAGO43kET 유형("3,584 and 45,182 entity types"), 사건은 P2GT 가 모은 wikiHow 유형이다(ACL 판 부록 C.1).

**4. 갈래 3은 그 구를 닫힌 어휘로 정규화한다. AutoSchemaKG 에는 닫힌 어휘가 없다.**

`[확인]` MLMET 은 단수화 뒤 어휘 밖 단어를 버린다. LITE 는 어휘 전체에 순위를 매긴다. CASENT 는 어휘 제약 생성을 한다(#3 유형 정규화).

`[확인]` AutoSchemaKG 프롬프트에는 후보 어휘가 없다. "Post-processing aggregates these phrases to compute the unique concepts in C" (부록 B.2.3)

**5. 그래서 같은 개념인지는 글자로만 정해진다.**

`[확인]` 공식 코드는 LLM 응답을 쉼표로 자르고 소문자화·strip 만 한다. `answers.append([x.strip().lower() for x in answer.split(",")])` (`atlas_rag/kg_construction/concept_generation.py`, main `d0a1666`)

`[확인]` 개념 노드 ID 는 개념 문자열의 SHA-256 이다. `text = text + '_concept'` 다음 `hashlib.sha256(text.encode('utf-8'))` (`concept_to_csv.py` `compute_hash_id`) 글자가 같으면 같은 노드가 되고, 한 글자라도 다르면 다른 노드가 된다.

`[확인]` 개념 사이의 상하위 관계 엣지를 만드는 코드는 이전 회차에서 찾지 못했다(`autoschemakg-kg-construction/lab/sources/INDEX.md` #2.1 수집자 메모).

**6. 선행 연구는 표기 변형, 너무 일반적인 개념, 다의어를 각자 다른 장치로 다뤘다.**

표기 변형을 묶는 장치는 갈래마다 다르다.

| 출처 | 장치 |
|---|---|
| Probase | 라벨이 같은 노드를 sense 별로 나누고, 자식 집합이 겹치는 개수로 합친다. "Similarity defined in a relative manner, such as the Jaccard metric, can often lead to unreasonable results." |
| Microsoft 후속(Wang 2015, Hua 2015) | 인스턴스 분포 cosine 거리로 Probase 개념을 K-Medoids 5,000개 클러스터에 묶는다. "individual concepts such as animal, wild animal, exotic animal, jungle animal, etc. are all grouped into the concept cluster animal." |
| ConceptNet 5.5 | NFKC 정규화, 소문자화, 토큰화. "ConceptNet 5.5 removes the lemmatizer, and instead relates inflections of words using the FormOf relation." |
| AbstractATOMIC | 원형과 spaCy 표제어형을 함께 쓴다. 개념끼리 병합하지는 않는다 |
| 갈래 3 | 닫힌 어휘로 보낸다 |
| 갈래 5 | 임베딩 군집, 임베딩 후보 + LLM 검증(#5 병합 방식) |
| MetaMap | 변형을 생성해 온톨로지 개념 하나에 잇는다 |

`[추정]` CAT·CANDLE·AbsPyramid 등 KnowComp 계열은 개념 병합 단계를 두지 않는다. 근거: 원문에서 병합 절차를 찾지 못했다. CANDLE 은 고유 개념 수를 셀 뿐이다(6,181K 중 853.5K). AutoSchemaKG 의 글자 병합은 이 계열의 관행을 이은 것으로 보인다.

`[확인]` 너무 일반적인 개념은 거르거나 경고했다. AbstractATOMIC: "Over-general or meta concepts like "word," "noun," "concept," etc. are excluded." SemEval-2018 Task 9 는 일반어 blacklist 를 둔다. Song 2011 은 "topic, factor" 같은 모호한 개념을 한계로 적는다.

`[확인]` 다의어는 문맥으로 다뤘다. CAT 는 문맥 없는 개념화가 틀린 지식을 만든다고 적는다. MetaMap 은 ambiguity 를 "most difficult problem" 이라 부른다. Probase 는 같은 라벨을 sense 별로 나눈다.

**7. AutoSchemaKG 에는 이 세 장치가 모두 없다. 이전 회차 실험에서 그 결과가 실제로 보였다.**

`[확인]` 이전 회차는 공식 프롬프트와 조립 방식을 llama3.1:8b 로 다시 돌렸다. 입력은 우산 이야기 한국어 그래프였다(`autoschemakg-kg-construction/lab/03_concepts.py`, `lab/runs/03-seed*.txt`, 2026-10-08).

`[확인]` 표기 변형이 다른 개념 노드로 갈렸다. 같은 사건의 갈라진 두 노드가 seed 0 에서 "forgotten"·"work" 와 "forgetting"·"working" 을 받았다. seed 1 에서는 "purchase" 와 "umbrella purchase" 가 갈렸다(`autoschemakg-kg-construction/notes.md`).

`[확인]` 필터가 없어서 LLM 의 덧붙인 말이 개념 노드가 됐다. seed 0 의 한 노드는 "i don't see an event provided. please provide the event so i can give you the phrases in the required format." 를 개념으로 받았다(`lab/runs/03-seed0.txt` 21줄).

`[감]` 다의어 충돌("apple" 과일 대 회사가 개념 "apple" 하나로 모이는 경우)은 이 실험에서 보지 못했다. 영어 다의어가 섞인 입력으로 개념 노드의 이웃을 세어 보면 확정된다.

`[추정]` 갈래 5의 방법을 개념 노드에 붙이면 변형 분산은 줄 것이다. 근거: KGGen v2 의 LLM 판정 조건이 "variations in tense, plurality, case" 를 명시한다. 같은 연구가 "over or under de-duplication" 을 한계로 적으므로 과잉 병합 위험이 따라온다. 개념 노드에 적용해 잰 연구는 찾지 못했다.

### 정리

- `[확인]` AutoSchemaKG 의 개념 단계는 KnowComp conceptualization 계열의 프롬프트(Intention KG)와 예시(CAT, AbsPyramid)를 직접 물려받았다.
- `[확인]` 병합은 소문자화·strip 뒤 글자 일치다. 선행 연구의 sense 분리(Probase), 군집화(Microsoft 후속, CESI), 닫힌 어휘(entity typing), LLM 검증(EDC, KGGen v2) 가운데 어느 것도 쓰지 않는다.
- `[추정]` AutoSchemaKG 의 설계 의도는 "semantic bridges" 다. 개념을 잘게 맞추기보다 노드 사이 연결을 늘리는 쪽에 무게가 있다. 근거는 §1·§5 의 서술이다. 병합 정밀도를 잰 실험은 논문에 없다.
- 덜어낸 것: WordNet synset 매핑, 개념 사이 상하위 관계 유도(taxonomy induction), sense 별 개념 분리

## 읽는 순서

입문에서 깊이 쪽으로 간다.

| 순서 | 논문 | 읽는 까닭 |
|---|---|---|
| 1 | Wang et al. 서베이, Findings EMNLP 2025 ([arXiv 2406.10885](https://arxiv.org/abs/2406.10885)) | 갈래 1의 지도와 세 계열 분류. AutoSchemaKG 와 같은 연구실이다 |
| 2 | Hearst 1992 ([C92-2082](https://aclanthology.org/C92-2082/)) | 7쪽. "is-a 를 텍스트에서 뽑는다" 는 발상의 원점이다. Probase·MLMET 이 이 패턴을 쓴다 |
| 3 | Song et al. IJCAI 2011 ([PDF](https://www.ijcai.org/Proceedings/11/Papers/388.pdf)) | 6쪽. 짧은 텍스트 conceptualization 을 처음 문제로 세웠다 |
| 4 | Choi et al. ACL 2018 Ultra-Fine Entity Typing ([P18-1009](https://aclanthology.org/P18-1009/)) | 자유 형식 유형 이름표의 정의·데이터·평가 어려움 |
| 5 | CAT, ACL 2023 ([arXiv 2305.04808](https://arxiv.org/abs/2305.04808)) | 문맥이 왜 필요한가. AutoSchemaKG 예시의 출처 계열 |
| 6 | CANDLE, ACL 2024 ([2024.acl-long.128](https://aclanthology.org/2024.acl-long.128/)) | LLM 으로 개념을 생성하고 critic 으로 거르는 방식 |
| 7 | CESI, WWW 2018 ([arXiv 1902.00172](https://arxiv.org/abs/1902.00172)) | canonicalization 의 표준 기준점과 평가 데이터 |
| 8 | EDC, EMNLP 2024 ([arXiv 2404.03868](https://arxiv.org/abs/2404.03868)), 이어서 KGGen v2 ([arXiv 2502.09956](https://arxiv.org/abs/2502.09956)) | LLM 시대 병합. 임베딩 후보에 LLM 검증을 붙인다 |

## 확인하지 못한 것

| 항목 | 상태 | 막힌 까닭 |
|---|---|---|
| RAKE 본문 (Wiley 2010) | 못 엶 | Wiley 403, 발췌 PDF 520. 방법 주장을 적지 않았다 |
| C-value/NC-value (Frantzi 외 2000) | 못 엶 | 유료, 봇 차단 |
| YAKE Information Sciences 2020 판 | 초록 | ScienceDirect 403 |
| Alzaidy 외 WWW 2019 (Bi-LSTM-CRF) | 초록 | ACM 403 |
| Sahrawat ECIR 판 | 못 엶 | arXiv 판만 읽었다. 저자 표기가 판마다 다르다 |
| Text2Onto 본문 | 초록 | 저자 PDF 404, 미러 봇 차단 |
| Li et al. CIKM 2013 (Probase K-Medoids 원 출처) | 못 엶 | 저자 PDF 가 HTML 로 응답, ACM 유료 |
| Kim, Wang, Oh IJCAI 2013 "Context-Dependent Conceptualization" | 초록 | 시간 부족 |
| Onoe, Durrett EMNLP Findings 2020 | 못 엶 | 같은 저자 NAACL 2019 로 대신했다 |
| Wang et al. 2015 교과서 개념 추출, Martínez-Cruz 외 ChatGPT keyphrase | 못 엶 | 시간 부족 |
| COMBO (EACL 2023), MulCanon (arXiv 2403.14733) | 못 엶 | LLM 이전 방식이라 우선순위를 낮췄다 |
| LLM 으로 Open KB canonicalization 을 한 2024–25 논문 | 못 찾음 | 검색 두 번에 걸리지 않았다 |
| CANDLE·AbsInstruct 외 KnowComp 밖의 LLM conceptualization 평가 | 일부 | Step-Back(ICLR 2024)과 TaxoGlimpse(PVLDB 2024)만 열었다. ChatGPT 로 Probase isA 를 직접 평가한 논문은 못 찾았다 |
| Microsoft Concept Graph(Probase) 현재 배포 | 못 받음 | 2026-10-09 기준 concept.research.microsoft.com 접속 실패, probase.msra.cn DNS 실패. Wayback 2022 기록에는 "only for academic use" 배포가 있었다 |
| DBLP 서지 교차 확인 | 전부 못 함 | ECONNRESET·봇 차단. 서지는 ACL Anthology, Crossref, PDF 머리말, 학회 페이지로 확인했다 |
| 세부 서지 | 일부 | Snow 2004 쪽수, FIGER DOI, LLMs4OL LNCS 쪽수, iText2KG 의 WISE 2024 게재, Carta 외(arXiv 2307.01128) 게재처, Gillick 2014 심사 게재처, Cunningham 2023 ICLR 판 저자 순서 |
| KeyBERT 인용 정보 | 불일치 | README 는 v0.3.0·2020 이라 적는다. Zenodo 4461265 레코드는 v0.1.3·2021-01-25 다 |
| i2b2 2010 inexact F 0.924 | 요약으로만 | 표를 직접 읽지 않아 본문에 쓰지 않았다 |
| AutoSchemaKG 식 글자 병합과 임베딩·LLM 병합을 개념 노드에서 견준 연구 | 못 찾음 | 이 물음을 다룬 1차 출처를 찾지 못했다 |

## 원문 위치

- 이번에 받은 PDF·추출 텍스트: 세션 scratchpad `dl/a`(갈래 1), `dl/b`(갈래 2·6), `dl/c`(갈래 3·4), `dl/d`(갈래 5·7). 세션이 끝나면 지워진다.
- AutoSchemaKG 원문·코드·참조 논문: `autoschemakg-kg-construction/lab/sources/` (색인 `INDEX.md`), `autoschemakg-kg-construction/lab/repos/AutoSchemaKG/`

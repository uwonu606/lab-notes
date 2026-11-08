# 작은 모델로는 임베딩 유사도 분할과 2~8B 모델의 경계 판정을, 평균 크기가 같은 고정 길이 분할과 같은 토큰 예산에서 견줘 시험한다

- 작성: 2026-10-11
- 범위: arXiv 논문 25편, 블로그·보고서 3건, 공개 저장소 15곳(`lab/repos/`)
- 남의 코드는 실행하지 않았다. 로컬 Ollama에는 `logprobs` 확인 요청을 한 번 보냈다(#후보 3).
- 라벨: `[확인]` 원문·코드를 읽거나 실행해서 봤다. `[추정]` 실행하지 않고 사례에서 끌어냈다. 사례와 개수를 붙인다.

## 요약

- [확인] 나누는 방식 사이의 차이는 대부분 작다. 문장 경계를 지키는 고정 길이 분할이 여러 비교에서 동률이거나 이긴다. 사례: 2410.13070 표 1·2, 2602.16974 표 3, 2601.14123 F2, Chroma 보고서.
- [확인] 순위는 과제에 따라 뒤집힌다. 여러 문서에서 관련 문서를 찾을 때는 문단·고정 길이가 앞선다. 한 문서 안에서 근거 자리를 찾을 때는 LLM 분할(LumberChunker)이 앞선다(2602.16974 §4.2–4.3). 위키 연결은 두 과제를 다 쓴다.
- [확인] bge-m3에는 late chunking을 쓰지 않는다. bge-m3는 CLS pooling이다(`1_Pooling/config.json`). late chunking을 붙이면 NDCG@5가 0.246에서 0.070으로 떨어졌다(2504.19754 표 3). Ollama 임베딩 API는 토큰별 벡터를 주지 않는다.
- [추정] 주제 기반 분할이 이길 여지는 한 글에 주제가 여럿 섞인 경우와 대화형 글이다. 사례 2개: 짧은 문서를 이어 붙인 자료에서 Miracl F1 69.45→81.89(2410.13070 표 1). 대화 메모리에서 GPT4Score 57.99→66.37(SeCom 표 11, Mistral-7B 분할기).
- [확인] 한국어 청킹을 평가한 논문은 찾지 못했다(검색 4회). 가까운 근거는 중국어(Meta-Chunking, MoC)와 폴란드어+bge-m3(2606.00881)다.

## 용어

| 용어 | 뜻 |
|---|---|
| 조각 (chunk) | 임베딩 한 개로 바뀌는 글 단위 |
| 경계 (boundary) | 한 조각이 끝나는 문장 사이 자리 |
| in-corpus 검색 | 여러 문서 가운데 관련 문서를 찾는 과제. 문서 점수는 그 문서 조각 중 최고 점수로 둔다(MaxP) |
| in-document 검색 | 긴 문서 하나 안에서 답이 든 자리를 찾는 과제 |
| 토큰 예산 | 생성 모델에 넘기는 검색 결과의 총 토큰 수 |
| PPL (perplexity) | 언어 모델이 다음 토큰을 얼마나 못 맞히는지 나타내는 값. 여기서는 문장별 평균 토큰 손실 |
| logprob | 모델이 고른 토큰 확률의 로그 |
| Pk, WindowDiff | 정답 경계와 예측 경계를 창 단위로 견주는 분할 지표. 낮을수록 좋다 |
| IoU | 검색된 글자 구간과 정답 근거 구간의 겹침 ÷ 합집합 |

## 비교 표

| # | 방법 | 나누는 기준 | 모델 (논문) | 비용 사례 | 보고된 효과 | 코드 |
|---|---|---|---|---|---|---|
| 1 | 고정 길이·재귀 | 토큰 수, 문단→줄→문장 구분자 | 없음 | 책 한 권 0.1–0.6초 | 대부분 비교에서 동률 이상 | Chroma, LangChain |
| 2 | 문장·문단 복원 (SaT) | 글자마다 줄바꿈 확률 | 3층 XLM-R (작음) | 1,000문장 약 0.5초 | 한국어 문장 F1 99.6 (UD) | wtpsplit, MIT |
| 3 | 임베딩 거리 경계 | 이웃 문장 창의 cosine 거리 분위수 | 임베딩만 | 책 212–4,978초 (API) | 이어 붙인 문서에서만 이김 | Kamradt 노트북, Chroma |
| 4 | 임베딩 군집 DP | 연속 구간 유사도 합 최대화 | 임베딩만 | 미측정 | recall 91.3 vs 재귀 89.5 (크기 다름) | Chroma, MIT |
| 5 | Max-Min | 새 문장의 최대 유사도 vs 조각 최소 응집도 | 임베딩만 | 평균 2.44분 | 고정 길이와 비슷 | ApriiM (라이선스 없음) |
| 6 | LLM 경계 번호 지목 | "내용이 바뀌는 첫 문단 ID" 또는 split_after 목록 | Gemini, GPT-4o, Llama 3 8B, Mistral-7B | 책 95–1,628초, 1.11 문서/초 | in-document 1위, in-corpus 중위 | LumberChunker, Chroma, SeCom |
| 7 | 경계 확률 (PPL) | 문장 PPL 극소점 | Qwen2-0.5B~7B | 0.5B 140초 vs 유사도 416초 | F1 11.89→13.56 (같은 길이) | Meta-Chunking, Apache-2.0 |
| 8 | 경계 확률 (MSP) | "나눈다/붙인다" 답의 확률 차 | Qwen2-0.5B~7B | 0.5B 1,471초, 7B 8,782초 | F1 9.45→11.37 (Qasper, 7B) | Meta-Chunking |
| 9 | 학습된 소형 분할기 | 미세조정 모델이 조각 머리·끝 생성 | 0.5B~4B | 4,166단어 문서 1.5초 (HiChunk) | 0.5B~4B가 14B~72B와 비슷하거나 앞섬 | MoC, HiChunk, Jina |
| 10 | 명제 단위 (Dense X) | 문장을 원자 사실로 다시 씀 | Flan-T5-large 780M | 평균 15.05시간, 다수 실패 | Wiki 검색에서 이김, in-corpus 15–27% 하락 | factoid-wiki |
| 11 | Late chunking | 문서 전체 토큰 임베딩 후 구간 평균 | 긴 문맥·mean pooling 임베딩 | 임베딩 1회 | nDCG@10 +1.5~1.9, bge-m3에서는 붕괴 | jina late-chunking |
| 12 | Contextual Retrieval | 조각마다 문서 맥락 50–100토큰 덧붙임 | Claude Haiku, Phi-3.5-mini | 조각마다 LLM 1회 | 실패율 −35~−67% (Anthropic) | anthropic-cookbook |
| 13 | 계층 (RAPTOR) | 군집→요약을 재귀로 쌓은 나무 | gpt-3.5 요약 | 문서 길이에 선형 | +0.5~+1.7점 | raptor, MIT |
| 14 | 문서별 방법 고르기 | 내재 지표 5개 평균으로 방법 선택 | GPT-5 (regex 분할기) | 210초/코퍼스 | 정답률 62–64%→72% | adaptive-chunking, MIT |

## 방법별 근거

### 1. 고정 길이·재귀 분할 (대조군)

- 기준: 토큰 수로 자른다. 재귀형은 `\n\n`→`\n`→`.`→공백 순으로 자르고 크기 상한을 지킨다.
- 효과: [확인] Chroma 보고서에서 재귀 200토큰·겹침 0이 "consistently strong" 했다. recall 88.1, IoU 6.9다.
- 효과: [확인] 2601.14123은 문장 보존 분할을 기본으로 권한다. 겹침(overlap)은 이득이 없고(|ΔBERTScore| ≤ 0.004), 조각 크기는 150–300이 기본값이다(표 1).
- 함정: [확인] 고정 길이를 아주 작게 잡은 비교는 고정 길이를 불리하게 만든다. 2603.06976은 100자·50토큰 고정 길이를 2문단 묶음과 견줬다(표 1).

### 2. 문장·문단 경계 복원 (SaT)

- 기준: 글자마다 "뒤에 줄바꿈이 올 확률"을 내고, 임계값을 넘으면 경계로 친다(2406.16678 §2.2). 구두점이 없어도 동작한다.
- 문단: [확인] 같은 확률로 문단도 나눈다. `sat.split(text, do_paragraph_segmentation=True)`, `paragraph_threshold` 로 조절한다(wtpsplit README "Paragraph Segmentation").
- 한국어: [확인] 문장 분할 F1은 UD Korean에서 SaT 99.6, SaT+SM 100.0이다. 잡음 많은 OPUS100에서는 72.4, 78.9, LoRA 적응 81.8이다(표 29).
- 쓰임: 다른 모든 방법의 입력 단위(문장)를 정한다. 제목·문단이 없는 보고서에서 첫 단계다.

### 3. 임베딩 거리 경계 (semantic chunking, TextTiling 계열)

- 알고리즘: 문장 i에 앞뒤 한 문장을 붙인 창을 임베딩한다(`buffer_size=1`). 이웃 창의 cosine 거리가 95분위수를 넘으면 경계다(Kamradt 노트북 cell 102).
- 변형: [확인] 2410.13070은 분위수 [10–90], 표준편차 [1–3], IQR, 2차 차분, 절대 거리 [0.1–0.5]를 시험했다(부록 B). 임계값은 결국 조각 크기를 정한다(부록 E.3).
- 효과: [확인] 이어 붙인 문서에서는 이겼다. Miracl F1 69.45→81.89, NQ 43.79→63.93이다. 원래 문서에서는 고정 길이가 이겼다. HotpotQA 90.59 vs 87.37이다(표 1). 근거 문장 찾기는 5개 중 3개에서 고정 길이가 1위였다(표 2).
- 효과: [확인] Chroma에서 기본값(95분위)은 평균 660토큰, recall 83.6으로 가장 낮았다. 이진 탐색으로 크기를 맞춘 KamradtModified는 87.1이었다.
- 비용: [확인] 제목과 달리 2410.13070은 시간을 재지 않았다. LumberChunker 표 10에서 OpenAI 임베딩 API로 212초(710문단), 4,978초(14,339문단)였다.
- 대화·회의: [확인] TextTiling은 DialSeg711에서 Pk 0.470, GPT-4 zero-shot은 0.093이었다(SeCom 표 4).

### 4. 임베딩 군집 DP (ClusterSemanticChunker)

- 알고리즘: 글을 50토큰 조각으로 자르고 임베딩한다. 유사도 행렬에서 평균을 빼고 대각을 0으로 둔다. 연속 구간의 유사도 합이 최대가 되게 DP로 자른다. 구간 상한은 `max_chunk_size/50` 조각이다(`cluster_semantic_chunker.py:51`).
- 효과: [확인] Chroma 표에서 Cluster 400은 recall 91.3, 재귀 400(겹침 0)은 89.5다. 평균 크기는 182 vs 276토큰이라 크기 효과가 섞여 있다. Cluster 200은 IoU 8.0으로 표에서 가장 높다.
- 2410.13070의 군집형: 위치 거리와 의미 거리를 λ로 섞는다(식 1). λ가 1(고정 길이)에 가까울수록 근거 찾기 F1이 올랐다(부록 E.3).
- 한계: [확인] 2607.01852(학위논문 코퍼스)에서는 군집형이 단순 방법을 넘지 못했다.

### 5. Max-Min

- 알고리즘: 새 문장과 현재 조각 문장들의 최대 유사도가 `max(조각 최소 유사도 × c × sigmoid(크기−1), 고정 임계)` 보다 크면 붙인다. 기본값은 고정 임계 0.6, c 0.9, 첫 문장 상수 1.5다(`ApriiM_Chunking-Research/src/chunking/strategies/max_min_chunking.py:11`).
- 효과: [확인] 2606.00881에서 Accuracy@5 85.75, 고정 길이 87.71이었다(표 1). 실패 없이 모든 데이터를 끝낸 방법 중 하나다.
- 출처 주의: 원 논문은 Springer 출판이다. 원문은 읽지 못했다.

### 6. LLM 경계 번호 지목 (LumberChunker 계열)

- LumberChunker: 문단에 `ID XXXX:` 를 붙이고, 누적 토큰이 θ를 넘을 때까지 묶어 LLM에 준다. 프롬프트 요지는 "Find the first paragraph (not the first one) where the content clearly changes" 다. 답한 ID가 다음 조각의 시작이 된다(2406.17526 §3.1, 부록 B).
- θ: [확인] 450–1,000을 시험했고 550이 최고, 1,000이 최저였다(§5.1). 코드는 토큰을 `1.2 × 단어 수` 로 어림한다(`LumberChunker-Segmentation.py:70`).
- 효과: [확인] GutenQA DCG@20 62.09, 재귀 54.72다(표 1). 평균 크기는 334 vs 399토큰으로 비슷하다(표 9). 재현 연구도 순위를 확인했다(2602.16974 표 1).
- 효과: [확인] in-corpus(BEIR 6종)에서는 문단 분할보다 낮거나 같았다. 처리량은 1.11 vs 1,854 문서/초다(2602.16974 §4.2).
- Chroma 변형: 50토큰 조각에 `<|start_chunk_X|>` 태그를 달고 약 800토큰씩 넘긴다. 답은 `split_after: 3, 5` 형식이다(`llm_semantic_chunker.py:84`). [확인] 보고서는 GPT-4o와 Llama 3 8B Instruct가 "both followed the format" 했다고 적었다.
- 문장 번호판: 문장 사이에 `[1]` 을 끼우고 경계 번호 목록만 받는다. 창은 최대 조각의 2배(1,500토큰)씩 겹친다. 조각은 50–500단어로 자르거나 합친다(2601.03276 §3.3).
- 대화: [확인] SeCom은 교환마다 번호를 붙이고 JSONL로 구간을 받는다(`instructions/segment_with_exchange_number.md`). 파싱에 실패하면 3교환씩 고정 분할한다(`secom.py:281`).
- 모델 크기: [확인] SeCom 분할기를 GPT-4→Mistral-7B로 바꿔도 이득 대부분이 남았다. LOCOMO GPT4Score 69.33→66.37, 턴 단위 57.99다. RoBERTa 분할기는 Long-MT-Bench+에서 턴 단위보다 낮았다(81.52 vs 84.91, 표 11).
- 실패: [확인] 2606.00881은 GPT-OSS-20B로 LumberChunker를 돌렸다. 11개 데이터 중 다수가 48시간 제한에 걸렸다(표 1–3). 2601.03276은 잡음 많은 입력에서 GPT-3.5가 "[1, 15, 22, ..., 79, 82, 85, ...]" 같은 규칙 수열을 냈다고 적었다(§4.3).
- 형식 없는 글: [확인] 저자들은 구조가 뚜렷한 글이면 markdown 분할과 결과가 비슷하고 비용만 크다고 적었다(Limitations). 2602.16974는 논증·포럼 글(ArguAna, FiQA)에서 하위권이었다.

### 7. 경계 확률: PPL Chunking

- 알고리즘: 문장 i의 평균 토큰 손실을 앞 문장 전부를 조건으로 잰다(2410.12788 식 1). 양옆보다 낮은 극소점 중 한쪽 차이가 θ 이상인 곳을 경계로 둔다(§3.1.1, `ppl_chunking.py:40`). 그 문장이 조각의 끝이 된다(`ppl_chunking.py:179-193`).
- θ: [확인] PPL 분포가 평탄하면 0, 요동이 크면 0.4가 좋았다. 기본 시험값은 0.5다(부록 G).
- 크기 맞춤: 극소점으로 만든 작은 조각을 목표 길이 L까지 이어 붙인다(§3.1.3 dynamic merging).
- 효과: [확인] 조각 길이를 112–178자로 맞춘 비교에서 Qwen2-0.5B PPL이 2WikiMultihopQA F1 13.56, 고정 길이 11.89, 유사도 분할 12.00이었다. 시간은 140초 vs 416초다(표 1).
- 모델 크기: [확인] 0.5B와 7B의 차이가 작다. MultiFieldQA-zh 23.52 vs 23.20이다(표 1). 부록 F는 Qwen2-1.5B가 Qwen2-7B를 자주 앞섰다고 적었다.
- 긴 문서: KV 캐시를 앞에서부터 버리며 이어 간다(§3.1.1).
- 언어: [확인] 코드의 문장 분할은 `zh`(jieba)와 그 밖(nltk `sent_tokenize`)만 있다(`ppl_chunking.py:10`). 한국어 경로는 없다.

### 8. 경계 확률: Margin Sampling (MSP)

- 알고리즘: "1. 나눈다 / 2. 붙인다" 이지선다 프롬프트에서 첫 토큰 확률을 읽는다. margin = P("2") − P("1") 이다. margin이 θ보다 크면 문장을 현재 조각에 붙인다(`margin_sampling_chunking.py:36`, `:76`).
- sentence1: 코드는 현재까지 쌓인 조각 전체를 sentence1로 넣는다(`margin_sampling_chunking.py:88`).
- θ: 처음 0이다. 이후 최근 5개 margin의 평균으로 바뀐다(`margin_sampling_chunking.py:100-102`). 논문 본문은 "historical" 평균이라고만 적었다(§3.1.2).
- 프롬프트: 2410.12788 표 6 원문이다. "This is a text chunking task. You are a text analysis expert. ... 1. Split sentence1+sentence2 into sentence1 and sentence2 two parts; 2. Keep sentence1+sentence2 unsplit in its original form; Please answer 1 or 2."
- 효과: [확인] Qwen2-7B MSP가 Qasper F1 11.37, 고정 길이 9.45였다. Qwen2-0.5B MSP는 10.15다(표 1).
- 비용: [확인] 문장마다 한 번 호출한다. 0.5B 1,471초, 7B 8,782초로 PPL보다 10배쯤 느리다(표 1).
- 지시 따르기: [확인] MSP는 지시 조정 모델이 낫고 PPL은 기본 모델도 된다(표 3). 작은 모델은 더 자세한 프롬프트에서 이득을 봤다(그림 2).

### 9. 학습된 소형 분할기

| 모델 | 크기 | 출력 | 보고된 효과 | 공개 |
|---|---|---|---|---|
| Meta-chunker (MoC) | Qwen2.5-1.5B 전체 미세조정, GPT-4o 데이터 2만 건 | 조각마다 "머리[MASK]끝" 목록. 편집 거리로 원문 위치 복원 | CRUD BLEU-1 0.3754, Qwen2.5-72B 0.3721, 고정 0.3515 (표 1) | `Robot2050/Meta-chunker-1.5B`, Apache-2.0 |
| HiChunk | Qwen3-4B 미세조정 | 문장 번호로 다단계 경계. Auto-Merge 검색 | HiCBench 근거 recall 74.06→81.03 (Qwen3-32B 답변기, 표 4) | 코드 MIT. 가중치 링크 비어 있음 (README:8) |
| text-seg-lm (Jina) | Qwen2-0.5B | 조각 머리만 생성 | 블로그 8편 ROUGE-L 0.398 vs Segmenter API 0.352 | HF 공개, 라이선스 미확인 |
| QChunker | 3B | 질문 개요 기반 분할 + 지식 보완 | MoC보다 소폭 앞섬 | `Robot2050/QChunker` |

- 언어: [확인] MoC 데이터(CRUD, DuReader, WebCPM)는 모두 중국어다. 저자는 "not yet undergone adequate multi-language adaptation" 이라고 적었다(Limitations).
- 출력 방식: 조각 전체를 다시 쓰게 하면 원문을 바꾼다. 그래서 머리·끝만 생성하고 원문에서 찾는다(MoC §3.2.3–3.2.4, Chroma "naive approach ... hallucinated").

### 10. 명제 단위 (Dense X)

- 기준: 문단을 "interpretable out of context" 한 원자 사실로 다시 쓴다. 대명사를 실명으로 바꾼다(2312.06648 그림 8 프롬프트).
- 모델: GPT-4로 4.2만 문단을 만들고 Flan-T5-large에 증류했다(§2). 명제 평균 11.2단어다(표 1).
- 효과: [확인] Wikipedia QA에서 비지도 검색기 Recall@5가 +12.0, +9.3 올랐다(§5.1).
- 반대 결과: [확인] BEIR in-corpus에서는 모든 임베딩 모델에서 최하위였다. 문단 대비 15–27% 낮다(2602.16974 §4.2). 2606.00881에서는 평균 15.05시간이 걸렸고 다수가 시간 초과였다(표 3).
- 언어: [확인] 영어 Wikipedia만 다뤘다(Limitations).

### 11. Late chunking

- 알고리즘: 문서 전체를 긴 문맥 임베딩 모델에 한 번 넣는다. 토큰 벡터를 조각 경계대로 평균한다. 문맥 창을 넘으면 겹치는 큰 창으로 나눈다(2409.04701 알고리즘 1·2, `chunked_pooling/__init__.py:32`).
- 효과: [확인] 고정·문장·의미 경계 모두에서 평균 nDCG@10이 1.5~1.9점 올랐다(§4.1). 무관한 글 속에 답을 숨긴 합성 데이터에서는 이득이 없었다(§4.2).
- 반대 결과: [확인] in-document 검색에서는 모든 설정에서 떨어졌다. 평균 −3.83%~−53.17%다(2602.16974 표 4).
- bge-m3: [확인] 2504.19754 표 3에서 bge-m3 고정 512자 Early 0.246, Late 0.070이다. 논문은 mean pooling 모델을 전제로 한다(§3). bge-m3는 `pooling_mode_cls_token: true` 다.
- Ollama: [확인] `/api/embed` 는 입력마다 벡터 하나만 준다(Ollama api.md). 토큰 벡터가 필요하면 transformers로 직접 돌려야 한다.

### 12. Contextual Retrieval

- 알고리즘: 문서 전체와 조각을 함께 주고 "short succinct context to situate this chunk" 를 받는다. 보통 50–100토큰이다. 이를 조각 앞에 붙여 임베딩과 BM25에 넣는다(Anthropic 블로그).
- 효과: [확인] 상위 20개 검색 실패율이 contextual embedding으로 35%, BM25를 더해 49%, 재순위까지 67% 줄었다. 비용은 prompt caching을 써서 문서 토큰 백만 개당 1.02달러다(같은 블로그).
- 작은 모델: [확인] 2504.19754는 Phi-3.5-mini 4bit로 맥락을 만들었다. Jina-V3 고정 분할 NDCG@5가 0.303→0.312, 융합·재순위까지 0.317이었다(표 2). 50개 질문·300개 문서 규모다. 긴 문서에서 VRAM을 약 20GB 썼다(§4).
- 성격: 경계를 정하는 기준이 아니다. 조각마다 문서 수준 정보를 덧붙인다.

### 13. 계층 (RAPTOR)

- 알고리즘: 100토큰 조각(문장 단위 보존)을 SBERT로 임베딩한다. UMAP으로 차원을 줄이고 GMM으로 군집한다. 군집 수는 BIC로 정한다. 군집마다 gpt-3.5로 요약하고 이를 재귀로 쌓는다. 검색은 모든 층을 한꺼번에 보는 collapsed tree, 예산 2,000토큰이다(2401.18059 §3).
- 효과: [확인] SBERT 기준 이득이 작다. NarrativeQA ROUGE 29.26→30.87, QuALITY 54.9→56.6, QASPER F1 36.23→36.70이다(표 1·2). 요약의 약 4%에 사소한 환각이 있었다(§3).

### 14. 문서별 방법 고르기, 레이아웃 기반

- Adaptive Chunking: 문서마다 후보 분할기를 돌리고 내재 지표 5개의 평균이 가장 높은 것을 고른다. 정답률 72%, 기준선 62–64%다(2603.25333 초록). 지표는 #평가 방법론 의 내재 지표 표에 적었다.
- 요소 기반(2402.05131), 시각 기반(2506.16035): 제목·표 같은 레이아웃 요소에 기댄다. 제목 없는 보고서에는 맞지 않는다. 시각 기반은 내부 데이터 한 벌에서 0.78→0.89 한 줄이고, 조각 수가 약 5배 달라 크기 효과와 섞여 있다(§6.2).

## 평가 방법론

### 정답은 조각 번호가 아니라 근거 위치로 둔다

- 이유: 나누기 방식마다 조각이 다르다. 조각 번호를 정답으로 두면 방식끼리 견줄 수 없다.
- 방법 1 (글자 구간): Chroma는 질문마다 원문과 정확히 일치하는 근거 발췌를 받고 시작·끝 위치를 저장한다. 검색된 조각 구간과의 겹침으로 recall·precision·IoU를 잰다. [확인] 이름은 "token-level" 이지만 코드는 글자 위치로 계산한다(`base_evaluation.py:219-275`).
- 방법 2 (겹치면 정답): 조각이 정답 문단·답 구간과 조금이라도 겹치면 정답으로 친다(2602.16974 §3.3.1, 2606.00881 §3.1). 큰 조각일수록 유리하므로 크기 대조군이 꼭 필요하다.
- 방법 3 (근거 문장 수): 검색된 조각에 든 근거 문장 수를 센다(2410.13070 §3.2).
- 피할 것: 조각을 문서로만 되돌려 매기면 조각 크기 효과가 사라진다. 2410.13070은 이 이유로 문서 검색에서 크기 차이가 안 보였다(부록 E.3).

### 같은 개수가 아니라 같은 토큰 예산으로 견준다

- 문제: 상위 k개를 고정하면 큰 조각을 쓰는 방식이 더 많은 글을 넘긴다.
- 사례: Dense X는 생성 모델 입력을 100·500토큰으로 잘라 비교했다(EM@l, §4). SeCom은 4k·1k 토큰으로 맞췄다(표 1). HiChunk는 4,096토큰으로 자르고 2k–4k 곡선도 그렸다(§5.3, 부록 A.2). 2601.14123은 순위대로 채워 예산에 닿으면 멈춘다("fill-to-budget", §2).
- 반례: Chroma(상위 5개), 2603.06976(상위 5개), 2606.00881(상위 5개, 4,000토큰 상한)은 개수를 고정했다.
- 예산 크기: [확인] Ministral-8B에서 2.5k토큰을 넘으면 품질이 떨어졌다("context cliff", 2601.14123 F3). 작은 모델로 답을 만들 때는 예산을 여러 개 잰다.

### 같은 평균 크기의 고정 길이를 대조군으로 둔다

- 문제: 새 방식의 이득이 경계 덕인지 크기 덕인지 가려야 한다.
- 좋은 사례: Meta-Chunking과 MoC는 모든 방식의 평균 길이를 데이터마다 같게 맞췄다(2410.12788 부록 D, 2503.09600 §4.3). KamradtModified는 이진 탐색으로 평균 크기를 맞춘다(Chroma).
- 나쁜 사례: [확인] 2603.06976의 고정 길이는 100자·50토큰이었다(표 1). LumberChunker 표 1의 의미 분할은 평균 185토큰, LumberChunker는 334토큰이었다(표 9). 2606.00881은 크기를 "not normalized" 로 두었다(§3).
- 재는 법: [확인] 2602.16974는 질문별 조각 크기와 점수의 상관을 냈다. in-document에서 r=0.52–0.57, in-corpus에서 r=0.07–0.16이었다(그림 2).
- 함께 보고할 것: 조각 수, 평균·최소·최대 크기, 처리 시간, 색인 크기.

### 근거가 촘촘한 질문을 넣는다

- 문제: 답이 한두 문장에 있는 질문은 어떤 방식으로 잘라도 그 문장이 같은 조각에 든다.
- 사례: [확인] GutenQA에서 FC200과 HiChunk의 근거 recall은 64.5 vs 65.53이었다. 근거가 촘촘한 HiCBench T1에서는 74.06 vs 81.03이었다(HiChunk §5.5). 2410.13070도 상위 조각에 같은 근거 문장이 반복해서 들어 차이가 작았다고 적었다(§4.3).
- 질문 종류: 나열·요약형, 여러 문단에 걸친 근거, 여러 보고서에 걸친 근거를 섞는다.

### 두 과제를 따로 잰다

- [확인] in-corpus와 in-document에서 순위가 뒤집힌다(2602.16974 §4.3). Late chunking도 한쪽에서 오르고 다른 쪽에서 떨어진다(표 4).
- 위키 연결에서는 "이 보고서와 관련된 다른 보고서" 가 in-corpus, "보고서 안 근거 자리" 가 in-document에 해당한다.

### 지표

| 지표 | 재는 것 | 쓴 곳 |
|---|---|---|
| 글자 구간 recall·precision·IoU | 검색된 글이 근거를 얼마나 덮고 얼마나 군더더기인가 | Chroma |
| 근거 recall | 근거 문장 중 검색된 비율 | HiChunk, 2410.13070 |
| nDCG@k, DCG@k, MRR, Hit@k | 순위 품질 | 2602.16974, 2603.06976, LumberChunker |
| 문서 F1@k | 조각→문서로 되돌린 검색 | 2410.13070 |
| EM@l, BERTScore, ROUGE, LLM 판정 | 답변 품질 | Dense X, 2601.14123, MoC, 2606.00881 |
| NONE 비율 | 근거 부족으로 답을 거부한 비율 | 2601.14123 |
| Pk, WindowDiff, 경계 F1, boundary similarity | 정답 경계가 있을 때 분할 자체 | SeCom 표 4, 2601.03276, survey 2411.16613 |
| 시간, 메모리, 조각 수, 색인 크기 | 비용 | 2603.06976 표 3, 2606.00881 표 3, HiChunk 표 5 |

- 분할 지표 주의: [확인] Pk와 WindowDiff는 특정 오류를 더 벌하고 경계 사례에서 일관성이 없다. survey는 boundary similarity를 대안으로 든다(2411.16613 §3).
- LLM 판정 주의: 2603.06976은 질문을 숨기고 정답과 조각만 Mixtral-8x22B에 보여 0/1/2로 매겼다. 이상 DCG는 같은 질문의 모든 방식 점수를 모아 정한다(§Relevance Evaluation).

### 정답 없이 재는 내재 지표

| 지표 | 계산 | 필요 모델 | 근거 |
|---|---|---|---|
| Boundary Clarity | ppl(q\|d) ÷ ppl(q). 1에 가까울수록 이웃 조각과 독립 | 언어 모델 PPL | MoC §3.1.1 |
| Chunk Stickiness | 조각 그래프(간선 = PPL 감소율 > K)의 구조 엔트로피 | 언어 모델 PPL | MoC §3.1.2 |
| Intrachunk Cohesion | 조각 안 문장 임베딩과 조각 임베딩의 평균 cosine | 임베딩 | Adaptive §2.3.3, `metrics.py:69` |
| Document Contextual Coherence | 조각과 3,000토큰 주변 창 임베딩의 평균 cosine | 임베딩 | Adaptive §2.3.4, `metrics.py:166` |
| Size Compliance | 100–1,100토큰 안에 든 조각 비율 | 없음 | Adaptive §2.3.5, `metrics.py:32` |
| References Completeness | 대명사와 선행어가 같은 조각에 있는 비율 | 영어 상호참조 모델 | Adaptive §2.3.1 (영어만) |
| HOPE | 개념 단일성·의미 독립성·정보 보존의 평균 | Nemotron-70B, Qwen2.5 | 2505.02171 |

- [확인] HOPE는 RAG 지표와 상관이 ρ > 0.13 수준이다. 의미 독립성이 가장 중요했고 개념 단일성은 영향이 작았다(초록).
- [추정] 내재 지표는 정답 질문을 만들기 전 거르기용으로만 쓴다. 사례 2개(HOPE ρ > 0.13, MoC는 상관을 부록 A.7에만 보고)에서 상관이 약하거나 검증이 얇다.

### 이 프로젝트에 맞춘 실험 틀

- 문제: 한국어·사내 보고서로 청킹을 평가한 공개 자료가 없다. 남의 수치를 옮겨 올 수 없다.
- 제안: 사내 보고서 20–50편으로 작은 평가 세트를 만든다. LLM이 질문과 "원문과 정확히 일치하는 근거 발췌" 를 내게 하고, 일치하지 않으면 버린다(Chroma 방식). 질문은 보고서 안 질문과 보고서를 건너는 질문을 섞는다. 같은 토큰 예산(예: 1k·2k)에서 글자 구간 recall·IoU와 관련 보고서 recall@k를 잰다.
- 근거: 위 #근거 위치 #같은 토큰 예산 #크기 대조군 #두 과제 의 사례들.
- 포기하는 것: 사람이 단 정답 경계, 표준 벤치마크와의 직접 비교. LLM이 만든 질문은 문체가 한쪽으로 쏠린다(Chroma caveats).

## 작은 모델로 시험할 후보

로컬 모델: `exaone3.5:2.4b`(Q4_K_M), `gemma4:e2b-it-qat`, `llama3.1:8b`(Q4_K_M), 임베딩 `bge-m3`. [확인] Ollama 0.31.2 (`/api/version`).

| 순위 | 후보 | 쓰는 모델 | 핵심 파라미터 | 이유 | 포기하는 것 |
|---|---|---|---|---|---|
| 0 | 대조군: 문장 보존 재귀 분할 | 없음 | 200·400 bge-m3 토큰, 겹침 0 | 모든 비교에서 동률 이상. 크기 효과를 가르는 기준 | 없음 (필수) |
| 1 | 임베딩 유사도 분할 (군집 DP, 거리 경계) | bge-m3 | DP: 50토큰 조각, 상한 200·400 / 거리: buffer 1, 평균 크기를 대조군에 맞춤 | Ollama만으로 됨. LLM 호출 0. "주제별로 나누면 낫다" 가설을 가장 싸게 시험 | 이득 근거가 약함. 원래 문서에서는 고정 길이가 자주 이김 |
| 2 | 소형 LLM 경계 번호 지목 | 세 모델 모두 | 문장 번호판, 창 약 800토큰, JSON 스키마 출력, 조각 50–500단어 | 대화·주제 전환·in-document에서 근거 있음. 8B·7B가 형식을 지킨 사례 | 2.4B 근거 없음. 창 수만큼 순차 호출 |
| 3 | MSP (경계 확률 차) | exaone3.5:2.4b, gemma4 | 문장마다 1회, `num_predict=1`, `top_logprobs=5`, θ=최근 5개 margin 평균 | 0.5B에서도 동작. Ollama logprobs로 바로 구현 확인 | 문장 수만큼 호출. 한국어 프롬프트 검증 없음 |
| 4 | PPL 분할 | Qwen2.5-0.5B 또는 EXAONE-3.5-2.4B 원본 가중치 (transformers) | 문장별 평균 손실, 극소점 θ ∈ {0, 0.2, 0.4}, 목표 길이까지 병합 | 작은 모델 근거가 가장 강하고 LLM 방식 중 가장 쌈 | Ollama 밖 런타임이 필요. 한국어 문장 분할을 직접 붙여야 함 |
| 5 | 덧붙일 축: 소형 모델 맥락 접두 | exaone3.5:2.4b | Anthropic 프롬프트, 50–100토큰, 접두 포함 BM25 병행 | 작성자마다 다른 용어·생략된 주어를 조각에 보충 | 경계 기준이 아님. 조각마다 문서 전체를 넣는 호출 |

### 공통 입력: 문장 단위

- SaT `sat-3l-sm` 으로 문장을 나눈다. 줄바꿈이 없는 보고서는 `do_paragraph_segmentation=True` 로 문단 후보도 얻는다(wtpsplit README).
- [추정] 한국어 보고서의 문단 복원 품질은 모른다. 사례 1개(OPUS100 한국어 문장 F1 72.4–81.8)에서 잡음 많은 글은 문장 분할부터 흔들린다.

### 후보 1. 임베딩 유사도 분할

- 군집 DP: 50토큰 재귀 조각 → bge-m3 임베딩(`/api/embed` 에 목록으로 한 번에) → 유사도 행렬에서 평균 빼기, 대각 0 → 연속 구간 합 최대화 DP. 상한 4·8조각(200·400토큰)이다(`cluster_semantic_chunker.py:51-81`).
- 거리 경계: 문장 i와 앞뒤 한 문장을 붙여 임베딩 → 이웃 cosine 거리 → 임계값을 이진 탐색해 평균 크기를 대조군과 같게 한다(KamradtModified, `kamradt_modified_chunker.py:15`, `avg_chunk_size`, `min_chunk_size=50`).
- 보는 것: 대조군 대비 글자 구간 recall·IoU 차이와 크기 상관.
- [추정] bge-m3 cosine 분포에서 Max-Min 고정 임계 0.6이 맞는지는 모른다. 사례 0개라 시험 전 분포를 먼저 본다.

### 후보 2. 소형 LLM 경계 번호 지목

- 입력: 문장(대화·메모면 발화)마다 `[12] ...` 번호를 붙인다. 누적 약 800토큰까지 한 창에 넣는다(Chroma). 다음 창은 마지막 경계 다음 문장부터 시작한다.
- 프롬프트 요지: "주제가 바뀌는 문장 번호 바로 앞에서 나눈다. 번호만 오름차순으로 낸다. 적어도 하나." (Chroma `llm_semantic_chunker.py:84-103` 의 지시를 한국어로).
- 출력: Ollama `format` 에 JSON 스키마 `{"split_after": [int]}` 를 준다. 창 범위 밖·역순이면 한 번 다시 묻고, 그래도 실패하면 고정 길이로 대신한다(SeCom `secom.py:281` 의 폴백 방식).
- 후처리: 50단어 미만 조각은 이웃과 합치고, 500단어 초과는 같은 방식으로 다시 나눈다(2601.03276 §3.3).
- 보는 것: 모델별 형식 준수율, 같은 문서에서 세 모델 경계의 일치도, 검색 지표.
- 대안 형식: LumberChunker식 "첫 전환 문단 ID 하나" 에 θ=550토큰. 한 창에 답이 하나라 작은 모델에 더 쉬울 수 있다. 대신 창마다 순차 호출이라 병렬화가 안 된다(2406.17526 부록 G).

### 후보 3. MSP

- 호출: `/api/generate`, `options.num_predict=1`, `temperature=0`, `logprobs=true`, `top_logprobs=5`.
- [확인] 문장 쌍 하나로 시험했다. exaone3.5:2.4b가 "2" logprob −0.73, "1" −1.16을 냈다. margin은 약 +0.17(붙인다)이다. 표 6 영어 프롬프트에 한국어 문장 두 개를 넣었다.
- 규칙: sentence1 = 현재 조각 누적, sentence2 = 다음 문장. margin > θ면 붙이고, 아니면 새 조각을 연다. θ는 0에서 시작해 최근 5개 margin의 평균이 된다. 끝나면 대조군 평균 크기까지 병합한다.
- [추정] 누적 조각이 길어지면 프롬프트가 커진다. 상한(예: 400토큰)을 넘으면 끊는 규칙을 둔다. 사례 0개라 시험으로 정한다.

### 후보 4. PPL 분할

- 런타임: transformers로 모델 로짓을 직접 받는다. `ppl_calculate.py` 의 `get_ppl_batch` 처럼 문장을 이어 붙여 한 번에 넣고 토큰 손실을 문장별로 평균한다(`tools/utils/ppl_calculate.py:9`).
- 문장 분할: 코드의 `zh`·`en` 분기 대신 SaT 결과를 넣는다.
- θ: {0, 0.2, 0.4}를 돌린다. 분포가 평탄하면 낮은 값이 좋았다(2410.12788 부록 G).
- [추정] Ollama로는 안 된다. 사례 1개: api.md는 입력 토큰 확률을 주는 옵션을 적지 않았고, 2차 자료는 logprobs가 출력 토큰용이라고 적었다.

### 후보 5. 맥락 접두

- 프롬프트: Anthropic 블로그 원문. `<document>{{WHOLE_DOCUMENT}}</document>` 와 `<chunk>{{CHUNK_CONTENT}}</chunk>` 뒤에 "Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."
- 대조: 같은 경계에서 접두 유무만 바꾼다. 후보 0–4 중 가장 나은 경계 하나와 대조군에 붙인다.
- [추정] 2.4B 모델의 맥락 품질은 Phi-3.5-mini보다 낮을 수 있다. 사례 1개: 2504.19754 결론이 "smaller and more efficient models performing worse" 라고 적었다.

## 모르는 것

| 모르는 것 | 무엇을 보면 아나 |
|---|---|
| 한국어 보고서에서 어떤 방식이 이기는지 | #이 프로젝트에 맞춘 실험 틀 의 평가 세트 |
| 2.4B·e2b 모델이 경계 번호 형식을 지키는 비율 | 후보 2를 문서 20편에 돌려 형식 오류율 세기 |
| MSP에서 "1"·"2"가 top 5 밖일 때 처리 | 후보 3 로그에서 빈도 세기 |
| Ollama가 입력 토큰 logprob을 주는지 | 공식 문서·릴리스 노트, 또는 `raw` 모드 시험 |
| SaT의 한국어 문단 복원 품질, kss 같은 한국어 전용 분할기와의 차이 | 줄바꿈을 지운 사내 문서로 복원율 재기 (kss는 조사하지 않음) |
| 작성자마다 다른 용어를 분할이 풀어 주는지 | 같은 내용을 다른 용어로 묻는 질문을 평가 세트에 넣기 |
| 2603.06976이 실제로 LLM을 썼는지 | 공개 설정(`chunker_config.json:228`)은 LLM 없이 돈다. 저자 확인 필요 |
| HiChunk 가중치 공개 여부 | README 모델 링크가 비어 있음 |
| Jina text-seg-lm 라이선스와 한국어 동작 | HF 모델 카드 |
| Max-Min 원 논문의 실험 조건 | Springer 원문 |

## 출처

### 논문

| arXiv | 제목 (줄임) | 이 보고서에서 쓴 곳 |
|---|---|---|
| 2410.13070 | Is Semantic Chunking Worth the Computational Cost? | 표 1–3, 부록 A·B·E |
| 2406.17526 | LumberChunker | §3.1, §5, 부록 B·F·G |
| 2410.12788 | Meta-Chunking | §3.1, 표 1·3, 부록 D·F·G |
| 2503.09600 | MoC | §3, 표 1–4 |
| 2409.04701 | Late Chunking | 알고리즘 1·2, 표 2, §4.2·4.5 |
| 2602.16974 | Beyond Chunk-Then-Embed (재현 연구) | 표 1–5, 그림 2 |
| 2504.19754 | Reconstructing Context | 표 2–5, §4 |
| 2603.06976 | Systematic Investigation of Chunking (36개) | 표 1–3 |
| 2606.00881 | Chunking Methods on RAG (KES 2026) | 표 1–4, §3 |
| 2312.06648 | Dense X Retrieval | 표 1·3·5, 그림 8, Limitations |
| 2401.18059 | RAPTOR | §3, 표 1·2 |
| 2506.16035 | Vision-Guided Chunking | 표 1, §6 |
| 2406.16678 | Segment Any Text | §2.2, 표 29 |
| 2502.05589 | SeCom | 표 1·4·11, 그림 6 |
| 2601.03276 | Topic Segmentation Using Generative LMs | §3.3, 표 1 |
| 2411.16613 | Linear Text Segmentation survey | §2.2.4, §3 |
| 2601.14123 | Chunking for Reliable QA | F1–F4, 표 1 |
| 2509.11552 | HiChunk | 표 3–5, §5.3 |
| 2603.25333 | Adaptive Chunking | §2.3, 표 2 |
| 2505.02171 | HOPE | 초록, §4 |
| 2505.21700 | Rethinking Chunk Size | §4.1 |
| 2607.01852 | Chunking on Academic Texts | 초록 |
| 2603.11650 | QChunker | 표 (Qwen 비교) |
| 2510.20356 | FreeChunker | 초록 |
| 2402.05131 | Financial Report Chunking | 표 3·4 |

### 블로그·문서

- Anthropic, "Introducing Contextual Retrieval" (2024-09): https://www.anthropic.com/news/contextual-retrieval
- Chroma, "Evaluating Chunking Strategies for Retrieval" (2024-07): https://www.trychroma.com/research/evaluating-chunking
- Jina AI, "Finding Optimal Breakpoints in Long Documents Using Small Language Models": https://jina.ai/news/finding-optimal-breakpoints-in-long-documents-using-small-language-models
- bge-m3 pooling 설정: https://huggingface.co/BAAI/bge-m3/raw/main/1_Pooling/config.json
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- Meta-chunker-1.5B 모델 카드: https://huggingface.co/Robot2050/Meta-chunker-1.5B

### 저장소 (`lab/repos/`)

| 디렉토리 | 라이선스 | 핵심 위치 |
|---|---|---|
| `joaodsmarques_LumberChunker` | 파일 없음 | `Code/LumberChunker-Segmentation.py:85` 프롬프트, `:175-178` 창 묶기(550), `:205-217` 답 파싱 |
| `IAAR-Shanghai_Meta-Chunking` | Apache-2.0 | `tools/ppl_chunking.py:40` 극소점, `:134` PPL 분할, `:444` 병합 포함 진입점 / `tools/margin_sampling_chunking.py:36` margin, `:76` MSP 루프 / `MoC/chunk_MoC.py:190` MoC 프롬프트, `:232` 원문 위치 복원 |
| `jina-ai_late-chunking` | Apache-2.0 | `chunked_pooling/__init__.py:32` 구간 평균, `chunked_pooling/chunking.py:16` 경계 생성 |
| `brandonstarxel_chunking_evaluation` | MIT | `chunking/cluster_semantic_chunker.py:51` DP, `chunking/llm_semantic_chunker.py:84` 프롬프트, `chunking/kamradt_modified_chunker.py:15` 크기 맞춤, `evaluation_framework/base_evaluation.py:219` 구간 지표 |
| `microsoft_SeCom` | MIT | `secom/secom.py:240` 분할, `:281` 폴백, `secom/instructions/segment_with_*.md` 프롬프트 |
| `segment-any-text_wtpsplit` | MIT | `wtpsplit/__init__.py:643` `SaT`, `:1089` `split` |
| `TencentYoutuResearch_HiChunk` | MIT (일부 제3자) | `pipeline/chunking/HiChunk/HiChunk.py:133` 입력 지시, `:370` 추론 엔진, `retrieval_algo.py:17` Auto-Merge |
| `ekimetrics_adaptive-chunking` | MIT | `src/adaptive_chunking/metrics.py:32·69·166·280` SC·ICC·DCC·BI, `splitters.py:556` regex 분할기 |
| `ApriiM_Chunking-Research` | 파일 없음 | `src/chunking/strategies/max_min_chunking.py:11`, `text_tiling.py:67`, `sequential_hac_chunker.py:30` (기본 bge-m3) |
| `TheOpenSI_chunkbench` | MIT | `chunking_strategies/chunking/chunker_config.json:228`, `chunkers/llm/llm_boundary_detection_chunking.py:31` |
| `disi-unibo-nlp_rag-when-how-chunk` | MIT | `Early&Late/Early&Late.ipynb`, `Early&Contextual/ContextualRetrieval.ipynb` |
| `parthsarthi03_raptor` | MIT | `raptor/cluster_utils.py:60` GMM, `:69` 군집, `raptor/utils.py:22` 100토큰 분할 |
| `chentong0_factoid-wiki` | Apache-2.0 | README:18 `chentong00/propositionizer-wiki-flan-t5-large` |
| `FullStackRetrieval-com_RetrievalTutorials` | 파일 없음 | `tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb` cell 84(buffer), 102(95분위) |
| `fraunhofer-iais_chunking-strategies` | 파일 없음 | 2505.21700 코드. 내부는 보지 않음 |

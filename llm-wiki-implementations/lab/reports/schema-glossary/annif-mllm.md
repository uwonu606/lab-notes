# Annif는 사람이 관리하는 어휘 밖으로 나가지 않고, 흔한 용어는 학습된 점수와 문서당 개수 제한으로 깎는다

Annif는 핀란드 국립도서관이 만든 자동 주제 색인 도구다. 문서를 넣으면 사람이 관리하는 SKOS 어휘(YSO, GND 같은 주제명표목) 안에서 주제를 골라 점수를 붙인다. wiki도 지식 그래프도 아니다. 엔티티 간 관계를 새로 만들지 않고, 문서→주제 링크만 낸다.

사용자 목표에 주는 답은 셋이다.

- [확인] 닫힌 용어집이 곧 추출기다. MLLM backend는 용어집의 정식 이름과 별칭을 문장 안에서 사전 대조로 찾는다(`annif/lexical/mllm.py:81-104`). 용어집 밖 이름은 애초에 후보가 되지 않는다.
- [확인] 범용어 허브는 "찾았다"와 "링크한다"를 나눠서 막는다. 찾은 후보마다 idf·doc_freq·처음/마지막 등장 위치·모호도 같은 특징 15개를 만들고, 사람이 붙인 정답으로 학습한 분류기가 점수를 낸다(`annif/lexical/mllm.py:107-137`). 그 뒤 문서당 상위 `limit`개만 남긴다(`annif/backend/mllm.py:44`).
- [확인] LLM은 본선 코드에 없다. LLM 재점수는 실험 브랜치와 닫힌 PR #859에만 있다. LLM 코드가 든 원격 브랜치는 넷이다(`experiment-llm-rescoring`, `experiment-llm-keyword-extraction`, `llms4subjects-natlibfi-germeval2025`, `llm-ensemble-backend`). 이 보고서는 뒤의 셋 중 `llm.py`·`llm_ensemble.py` 두 파일을 읽었다. 거기서도 LLM은 후보 목록에 점수만 매기고, 목록 밖 출력은 버린다.

직전 실험의 정밀도 하락(0.62 → 0.37)에 대해 [추정] Annif 방식이 주는 처방은 "이름이 나온 모든 청크에 링크"를 유지하되, 청크마다 후보에 점수를 매겨 상위 k개와 임계값을 넘는 것만 링크로 남기는 것이다. 사례: Annif의 후보 생성은 모든 문장을 훑지만(재현율 쪽), 출력은 점수·limit·threshold로 자른다(정밀도 쪽). 이 둘이 한 파이프라인 안에 갈라져 있는 구조가 1개 있다.

## 한 바퀴 흐름

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. 어휘 적재 | 사람이 관리하는 SKOS(Turtle 등) 또는 TSV/CSV 주제 파일을 `annif load-vocab`으로 읽는다. 주제마다 정수 id·URI·prefLabel을 둔다 | `annif/vocab/vocab.py:117`, `annif/vocab/skos.py:58,84-98` |
| 2. 색인 만들기 | 활성 주제의 prefLabel(is_pref=True)과 altLabel(선택적으로 hiddenLabel)을 analyzer로 토큰화한다. 이름마다 토큰 집합을 만들고, 가장 드문 토큰을 열쇠로 색인에 넣는다 | `annif/lexical/mllm.py:202-259` |
| 3. 후보 생성 | 문서를 문장으로 자른다. 문장의 토큰 집합이 어떤 이름의 토큰을 모두 포함하면 그 주제를 매치로 적는다(문장 번호 포함) | `annif/lexical/mllm.py:81-104`, `annif/lexical/tokenset.py:66-80` |
| 4. 후보 합치기 | 주제별로 매치를 모아 freq·first_occ·last_occ·spread·is_pref 평균·ambiguity 평균을 낸다 | `annif/lexical/mllm.py:61-78` |
| 5. 특징 만들기 | 코퍼스 통계(doc_freq, subj_freq, idf)와 어휘 관계(broader/narrower/related/collection 공존 비율)를 더해 15차원 특징을 만든다 | `annif/lexical/mllm.py:107-137` |
| 6. 점수 | BaggingClassifier(결정나무)가 "사람이 이 주제를 붙였을 확률"을 낸다 | `annif/lexical/mllm.py:140-147, 357-362` |
| 7. 자르기 | 점수 상위 `limit`개만 남긴다. 호출 쪽에서 `threshold`로 한 번 더 자른다 | `annif/backend/mllm.py:36-44`, `annif/suggestion.py:28-48` |
| 8. (선택) LLM 재점수 | 여러 backend 결과를 합친 상위 `sources_limit`개 후보의 prefLabel과 본문을 LLM에 준다. LLM은 0~100 점수를 JSON으로 낸다. 기존 점수와 가중 평균한다 | 브랜치 `llm-ensemble-backend`의 `annif/backend/llm_ensemble.py:163-271` |

출력은 `(주제 id, 점수)` 목록이다. [확인] 문장 위치는 출력에 남지 않는다. 링크는 문서 단위다.

## 축별 분석

### A schema

[확인] schema 역할은 사람이 관리하는 SKOS 어휘가 맡는다. 엔티티 종류·관계 종류를 정의하는 KG식 schema는 없다. 대신 SKOS의 `broader`·`narrower`·`related`·`member`(collection)를 읽어 특징으로 쓴다(`annif/lexical/mllm.py:227-231`, `annif/lexical/util.py:28-58`).

[확인] 파일 형식은 RDF(SKOS) 또는 TSV/CSV 주제 파일이다. 프로젝트 설정은 `projects.cfg`의 `vocab=yso` 한 줄이다(`projects.cfg.dist:88-93`).

[확인] 부분 어휘만 쓰려면 `vocab=dummy(en,exclude=http://example.org/dummy)`처럼 URI·type·scheme·collection 단위로 빼고 넣는다(`tests/projects.cfg:50`, `annif/vocab/rules.py:62-106`).

[확인] 강제 방식은 "구성상 닫힘"이다. 후보는 색인에서만 나온다. LLM 브랜치는 `response_format={"type": "json_object"}`로 구조화 출력을 요구한다(`llm_ensemble.py:229`).

[확인] 그 뒤 `if llm_label in labels` 검사로 후보 밖 이름을 점수 0으로 바꾼다(`llm_ensemble.py:249-261`). 점수 0 이하는 결과 행렬에 들어가지 않는다(`annif/suggestion.py:101-102`).

### B 용어집

[확인] 정식 이름과 별칭을 둔다. prefLabel은 `is_pref=True`, altLabel은 `is_pref=False`다. hiddenLabel은 `use_hidden_labels=True`일 때만 별칭에 들어간다(`annif/lexical/mllm.py:191-225`). 용어집은 도서관이 쓴다. Annif는 읽기만 한다.

[확인] 용어집은 프롬프트가 아니라 추출기 자체다. 대조는 analyzer(snowball 어간, voikko 원형 등)로 정규화한 토큰의 집합 포함이다. 그래서 어순이 달라도, 한 문장 안에 흩어져 있어도 매치된다(`annif/lexical/tokenset.py:38-42`). 한 주제가 정식 이름과 별칭 둘 다로 매치되면 정식 이름 쪽을 남긴다(`tokenset.py:74-78`).

[확인] 별칭 충돌은 `ambiguity` 특징으로 다룬다. 같은 문장에서 함께 매치된 이름 가운데, 이 이름의 토큰을 모두 품은 다른 주제의 수다(`tokenset.py:82-102`). 분류기가 모호한 매치를 깎는 데 쓴다.

[확인] LLM 브랜치에서 LLM이 보는 것은 후보의 prefLabel 하나뿐이다(`llm_ensemble.py:273-282`). `Subject.labels`는 언어별 정식 이름 하나만 담는다. prefLabel이 없으면 `rdfs:label`을 쓴다(`annif/vocab/skos.py:58, 84-98`). 별칭은 LLM에게 가지 않는다.

### C 원문 연결 범위

[확인] 매치 단위는 문장이다. 이름이 나온 모든 문장을 매치로 적는다(`annif/lexical/mllm.py:91-102`). 처음 본 곳만이 아니다.

[확인] 그러나 이 위치들은 특징으로 접혀 사라진다. 등장 비율 `freq`, 처음 위치 `first_occ`, 마지막 위치 `last_occ`, 퍼짐 `spread`가 된다(`mllm.py:65-77`). 최종 링크는 문서→주제다. 문장 근거를 돌려주는 API는 없다.

### D 새/기존 연결

[확인] 새 문서와 기존 주제는 URI 동일성으로만 이어진다. 새 문서에서 나온 매치는 어휘의 주제 id에 바로 붙는다. entity resolution이나 임베딩 대조 단계가 없다. 같은 주제를 받은 문서끼리 이어지는 것은 Annif 바깥(도서관 목록)의 일이다.

[확인] 어휘가 바뀔 때는 기존 id를 지킨다. `load-vocab` 갱신은 옛 주제 순서를 유지한다. 사라진 주제는 `labels=None`으로 deprecated 처리한다. 새 주제는 뒤에 붙인다(`annif/vocab/vocab.py:49-66`). deprecated 주제는 결과에서 빠진다(`annif/suggestion.py:103-106`).

[확인] 코퍼스 통계는 학습 때 한 번 고정된다. `doc_freq`·`subj_freq`·`idf`는 `annif train` 때 계산하고 모델 파일에 저장한다(`mllm.py:261-300`). MLLM은 `learn`(온라인 학습)을 구현하지 않는다(`annif/backend/mllm.py:110`의 부모가 `AnnifHyperoptBackend`이고 `AnnifLearningBackend`가 아니다).

### E 새 용어

[확인] 버린다. 대기열은 없다.

- MLLM: CountVectorizer를 어휘 이름으로만 학습한다(`mllm.py:243-246`). 이름에 없는 단어는 문서 토큰화 때 사라진다. 그래서 용어집 밖 이름은 흔적도 남지 않는다.
- LLM 재점수 브랜치: 후보 밖 이름은 점수 0이 된다(`llm_ensemble.py:257-258`).
- LLM 키워드 추출 브랜치(`experiment-llm-keyword-extraction`): LLM이 자유 키워드를 내면 정규화·단어 정렬 뒤 이름 색인에서 찾는다. 못 찾은 것은 `not_matched`로 debug 로그에만 남긴다(`annif/backend/llm.py:191-218`). 참고로 이 커밋에서는 색인 쪽 정규화가 주석 처리돼 있다(`llm.py:126` `# label = self._normalize_label(label)`). 색인 열쇠는 원래 이름 그대로이고 조회 열쇠만 정규화된다. 그래서 여러 단어 이름은 잘 안 맞았을 것이다. 실험 코드라 동작은 확인하지 않았다.
- 본선 YAKE backend: 통계 키워드 추출 뒤 같은 방식으로 어휘에 대조한다. 못 찾은 키워드는 역시 debug 로그뿐이다(`annif/backend/yake.py:143-165`).

[추정] 마지막 로그가 "새 용어 후보 목록"에 가장 가깝다. 사례: `llm.py:204-212`와 `yake.py:156-164`의 debug 출력 2곳. 이를 사람 승인 대기열로 잇는 코드는 찾지 못했다(main의 `annif/` 전체에서 `not_matched` 검색, 결과는 `yake.py` 하나).

### F 범용어 허브

[확인] 장치가 넷 있다.

| 장치 | 무엇을 깎나 | 근거 |
|---|---|---|
| 코퍼스 빈도 특징 | `doc_freq`(학습 코퍼스에서 후보로 나온 문서 수), `tfidf = freq × idf`, `idf = log((N+1)/(df+1))+1` | `mllm.py:123-125, 293-300` |
| 정답 빈도 특징 | `subj_freq`: 사람이 실제로 붙인 횟수("domain keyphraseness"). 자주 후보로 나오지만 사람이 안 붙이는 용어를 분류기가 깎는다 | `mllm.py:124, 266-267` |
| 위치·모호도·응집 특징 | first/last/spread, ambiguity, 같은 문서 다른 후보와의 broader/narrower/related 공존 비율 | `mllm.py:126-136` |
| 출력 개수 제한 | 문서당 상위 `limit`개, 그다음 `threshold` | `annif/backend/mllm.py:44`, `annif/suggestion.py:28-48` |
| 수동 제외 | 설정의 `exclude`·`exclude_type`·`exclude_scheme`·`exclude_collection`로 특정 주제를 결과에서 뺀다 | `annif/vocab/rules.py:62-106`, `annif/project.py:220-228` |

[확인] 고정 stoplist나 빈도 상한은 없다. 흔한 용어를 얼마나 깎을지는 분류기가 정답 데이터에서 배운다. 그래서 문서마다 사람이 붙인 주제가 있는 학습 코퍼스가 필요하다. 학습 데이터에 양성이나 음성 중 한쪽이라도 없으면 학습을 거부한다(`mllm.py:349-355`).

[확인] 수동 제외는 후보 생성 뒤에 걸린다. MLLM 색인은 `vocab.subjects.active`를 쓴다(`mllm.py:212`). 제외 필터는 `project.subjects`에만 있다(`annif/project.py:220-228`). 결과를 행렬로 만들 때 제외 주제가 `IndexError`로 빠진다(`annif/suggestion.py:103-106`).

### G 엔티티·이벤트

[확인] 이벤트·시간축은 뽑지 않는다. 출력은 주제 id와 점수뿐이다. 특징 목록에도 시간 관련 항목이 없다(`mllm.py:52-58`). 어휘가 인명·지명·사건명을 담아도 Annif는 종류를 구분하지 않는다.

### H 근거 수치

[확인] LLM 재점수의 효과는 GermEval-2025 논문(arXiv 2508.15877) Table 2에 있다. 테스트셋 nDCG@20이 LLM 없는 앙상블 0.5507에서 Qwen3 4B 재점수 0.5631, Mistral-Small-3.1-24B 재점수 0.5697로 올랐다. 후보는 100개를 줬다(Appendix B).

[확인] LLM 가중치는 작고 지수는 크다. 영어 `w=0.1592, p=7.898`, 독일어 `w=0.0921, p=9.328`이다(Appendix G). 논문은 이 값을 "we used"라고만 적는다. 어떻게 골랐는지는 적지 않는다. 다른 앙상블 가중치는 `annif hyperopt`로 400개 조합을 돌려 골랐다(§4.5). 브랜치에 `LLMEnsembleOptimizer`가 있어서 같은 방식일 수 있지만 unknown이다. 식은 `f = w·r^p + (1−w)·x`다. [추정] 지수가 크면 LLM이 100점 가까이 준 후보만 올라간다. LLM은 "확실한 것을 끌어올리는" 역할만 한다. 사례: 두 언어의 튜닝 결과 2개.

[확인] MLLM 단독은 학습형 backend보다 낮다. GermEval 개발셋 nDCG@20이 MLLM 0.4437(de)/0.4180(en), Omikuji Bonsai 0.5701/0.5985다(Table 5). SemEval-2025 논문(arXiv 2504.19675) Table 3에서도 MLLM nDCG@10 0.4245/0.4005, Bonsai 0.5144/0.5532다.

[확인] SemEval 쪽은 "we did not use one for the core task of choosing subjects"(§2)라고 적는다. LLM은 번역·합성 데이터에만 썼다.

[확인] MLLM 특징 하나하나(idf, ambiguity 등)를 빼 본 ablation은 두 논문 어디에도 없다. 범용어 허브 대책의 효과를 따로 잰 수치는 unknown이다.

## 가져올 것

| 문제 | 제안 | 근거 | 포기하는 것 |
|---|---|---|---|
| 모든 청크 링크가 범용어 허브를 만든다 | 링크 후보는 모든 청크에서 만들고, 청크마다 점수를 매겨 상위 k개와 임계값을 넘는 것만 링크로 쓴다 | Annif의 후보 생성/점수/limit 분리(`mllm.py:81-137`, `backend/mllm.py:44`) | 짧은 청크에서 흔한 용어가 유일한 연결이면 그 연결을 잃는다 |
| 점수를 무엇으로 매기나 | 학습 없이 시작하려면 `tf × idf`(청크 안 빈도 × 코퍼스 역빈도)와 ambiguity만 쓴다. 정답 링크가 쌓이면 Annif처럼 특징 15개 + 결정나무로 옮긴다 | `mllm.py:123-128, 293-300` | 문서 3개·청크 57개에선 idf가 거칠다. 학습형은 정답 쌍이 있어야 한다 |
| KG·schema·LLM 같은 메타 용어 | 용어집에 `exclude` 목록(또는 `link: false` 플래그)을 두고 링크 단계에서만 뺀다. 이름 정규화에는 계속 쓴다 | `annif/vocab/rules.py`, `project.py:220-228`이 색인과 출력 필터를 나눈 방식 | 사람이 목록을 관리해야 한다 |
| 별칭 충돌 | 한 토큰 묶음이 몇 개 주제에 걸리는지(ambiguity)를 특징으로 남긴다 | `tokenset.py:82-102` | 계산 비용(문장마다 후보 쌍 비교) |
| LLM을 어디에 쓰나 | 추출이 아니라 후보 재점수에만 쓴다. 후보의 정식 이름 목록을 주고, JSON 모드로 받고, 목록 밖 이름은 버리고, 기존 점수와 작은 가중치로 섞는다 | `llm_ensemble.py:189-271`, GermEval Appendix B·G | 문서·청크마다 LLM 호출 1번. Annif 팀은 PR #859를 닫고 더 효율적인 decision model 재정렬(PR #966)로 옮겨 가는 중이다. #966은 2026-10-11 현재 OPEN·WIP이고 병합되지 않았다 |
| 새 용어 | 용어집 밖 이름은 링크에서 버리되, 로그 대신 승인 대기열 파일로 모은다 | `llm.py:195-212`의 `not_matched`가 출발점 | 대기열을 사람이 비워야 한다 |

라이선스: [확인] Apache-2.0이다(`LICENSE.txt`). 코드를 옮겨 쓸 수 있다. 저작권 고지와 라이선스 사본을 남기고, 바꾼 파일에 변경 사실을 적어야 한다. NOTICE 파일은 저장소에 없다.

## 출처

- 저장소: https://github.com/NatLibFi/Annif, main commit `93ba3f90e8c98ab9363f2238bc6dff226c441453` (2026-10-05). 로컬 사본 `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/NatLibFi_Annif`
- LLM 브랜치(`git fetch --depth 1`로 받아 `git show`로만 읽음)
  - `llm-ensemble-backend` `2013e9cc7abd3afe18c31ade44a36fc1054c6bdf` (2025-07-10): `annif/backend/llm_ensemble.py`
  - `experiment-llm-keyword-extraction` `cfc7a0aad284f09fe4b83ffc010e16baef86e708` (2025-02-03): `annif/backend/llm.py`
- PR #859 "WIP LLM ranking/scoring backend", 2026-10-09 CLOSED. 마지막 댓글: "The `dm_rerank` backend of #966 implements the idea of this with much more efficiently by utilizing Jev-like models." 이슈 #856은 아직 OPEN. PR #966 "WIP: Decision model reranking backend"은 2026-10-09에 열렸고 아직 OPEN이다
- 논문
  - Suominen et al. 2025, "Annif at SemEval-2025 Task 5: Traditional XMTC augmented by LLMs", https://arxiv.org/abs/2504.19675
  - Suominen et al. 2025, "Annif at the GermEval-2025 LLMs4Subjects Task: Traditional XMTC Augmented by Efficient LLMs", https://arxiv.org/abs/2508.15877
- 라이선스: Apache License 2.0

## 검증 기록

2026-10-11, 다른 에이전트가 반박 검증으로 다시 열어 봤다. 로컬 사본 HEAD는 `93ba3f90`이고 보고서의 커밋과 같다. 두 브랜치 커밋(`2013e9cc`, `cfc7a0aa`)도 같다. 코드는 읽기만 했다.

### 그대로 맞은 것

- [확인] 사람이 정한 용어집이라는 주장은 맞다. 이름은 `vocab.subjects.active`와 SKOS 그래프의 prefLabel/altLabel/hiddenLabel에서만 온다(`mllm.py:191-225`). LLM이나 코드가 어휘를 만드는 경로는 본선에 없다. 학습 정답도 문서에 사람이 붙인 `subject_set`이다(`mllm.py:282-289`).
- [확인] 원문 연결 범위는 맞다. 모든 문장을 돌며 매치를 적고(`mllm.py:91-102`), `conflate_matches`가 위치를 비율 특징으로 접는다(`mllm.py:61-78`). 출력은 `(subject_id, score)`뿐이다(`backend/mllm.py:36-44`).
- [확인] 새/기존 연결은 맞다. 어휘 갱신은 옛 URI 순서를 지키고 사라진 주제를 `labels=None`으로 둔다(`vocab.py:49-66`). `SubjectIndexFile.__getitem__`이 이 주제에 `IndexError`를 던진다(`subject_index.py:40-44`). `MLLMBackend`의 부모는 `AnnifHyperoptBackend`이고 `AnnifLearningBackend`가 아니다(`backend/mllm.py:110`, `hyperopt.py:157`, `backend.py:158`).
- [확인] 수동 제외가 후보 생성 뒤에 걸린다는 주장은 맞다. `SubjectIndexFilter.__getitem__`이 제외 URI에 `IndexError`를 던진다(`subject_index.py:126-130`).
- [확인] LLM 브랜치의 닫힌 출력은 맞다. `response_format={"type": "json_object"}`(`llm_ensemble.py:229`), `if llm_label in labels`(`:257`), 점수 0 이하 제거(`suggestion.py:101-102`, 브랜치에서도 같은 줄).
- [확인] 수치는 모두 원문과 같다. arXiv HTML에서 직접 읽었다. GermEval Table 2 테스트(de+en 합친 예측) nDCG@20 0.5507/0.5631/0.5697, Appendix B `K=100`과 `f=w·r^p+(1−w)x`, Appendix G 0.1592/7.898·0.0921/9.328, Table 5 MLLM 0.4437/0.4180·Bonsai 0.5701/0.5985. SemEval Table 3("all" 어휘) MLLM 0.4245/0.4005·Bonsai 0.5144/0.5532, §2 인용문. 두 논문 본문에 "ablat"라는 낱말은 없다.
- [확인] PR #859는 2026-10-09 CLOSED이고, 인용한 마지막 댓글이 그대로 있다. 본선 `annif/`에서 `not_matched`는 `yake.py`에만 있다. `LICENSE.txt`는 있고 NOTICE는 없다.

### 고친 것

- PR #966: "옮겼다" → "옮겨 가는 중". `gh pr view 966`에서 state OPEN, mergedAt null이다. 제목도 "WIP"다. "더 싼"은 #859 마지막 댓글의 "much more efficiently"에 맞춰 "더 효율적인"으로 바꿨다.
- H의 "튜닝된 LLM 가중치": Appendix G는 "we used an LLM weight of 0.1592 (exponent 7.898)"라고만 적는다. 고른 방법은 unknown으로 바꿨다.
- F의 학습 거부 조건: "양성·음성이 모두 없으면" → "한쪽이라도 없으면". `n_classes_ != 2` 검사다(`mllm.py:349`).
- B의 ambiguity 정의를 코드에 맞게 좁혔다. 같은 문장의 매치 중 토큰 집합이 상위집합인 다른 주제 수다(`tokenset.py:95-100`).
- B의 `Subject.labels`: prefLabel이 없으면 `rdfs:label`도 쓴다(`skos.py:58`).
- E의 키워드 추출 브랜치: 색인 쪽 정규화가 주석 처리된 사실을 덧붙였다(`llm.py:126`).
- LLM 코드가 든 원격 브랜치가 넷이라는 사실을 덧붙였다. GermEval 제출 시점 브랜치는 `llms4subjects-natlibfi-germeval2025`(2025-06-04)다. 보고서가 읽은 `llm-ensemble-backend`(2025-07-10)는 그 뒤 커밋이라 논문 수치를 낸 코드와 다를 수 있다. 이 차이는 확인하지 않았다.


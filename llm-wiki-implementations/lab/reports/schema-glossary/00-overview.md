# 사람이 정한 schema로 llm-wiki를 만든 사례는 여럿이다. 사람이 미리 쓴 용어집까지 넣는 llm-wiki는 12개 중에 없었다

[확인] 사람이 정한 엔티티·관계·페이지 종류로 추출을 묶는 llm-wiki는 sage-wiki, AutoSci, GD4AI, jonex(openkb 경로)다.
[확인] 사람이 쓴 정식 이름+별칭 표를 추출에 쓰는 곳은 llm-wiki가 아닌 쪽에만 있었다.
jonex의 그래프 경로, OntoGPT, Annif가 그렇다.

[확인] llm-wiki 쪽 별칭은 대부분 LLM이 쓴다.
사람은 사후에 고치거나(synto의 blessed alias, sage-wiki의 resolution 승인) 아예 손대지 않는다.

이 문서는 후보 12개의 정독 보고서를 한데 모은 것이다.
보고서는 모두 이 디렉토리(`lab/reports/schema-glossary/`)에 있다.
각 판단 끝의 파일 이름이 근거 보고서다.

## 직전 실험과 축

직전 실험은 AutoSchemaKG(atlas-rag)로 문서 3개(청크 57개)에서 KG를 뽑은 것이다.
추출 모델은 llama3.1:8b였다.
사람이 미리 정한 schema(엔티티 종류 10, 관계 16)와 용어집(정식 이름+별칭 150개)을 프롬프트에 주었다.
추출 뒤에도 용어집으로 이름을 정규화했다.
그 결과 문제 넷이 남았다.

| 번호 | 문제 | 실험에서 본 것 |
|---|---|---|
| 1 | 원문 연결이 처음 본 곳에만 걸린다 | 공식 변환 코드는 이름을 처음 본 청크에만 링크를 걸었다. 새 문서와 기존 문서의 연결이 0쌍이었다. 모든 청크로 걸자 연결 재현율이 0.92가 됐다 |
| 2 | 새/기존 연결 발견 | 연결 재현율은 올랐다. 질문 40개 recall@5는 원문 임베딩 검색과 비슷하거나 낮았다 |
| 3 | 범용어 허브 | 용어집이 KG·schema·LLM 같은 범용어를 한 이름으로 모았다. 그 이름이 허브가 되어 연결 정밀도가 0.62에서 0.37로 떨어졌다 |
| 4 | 새 용어 승인 | 용어집·schema 밖 이름을 어떻게 받을지 정하지 않았다 |

후보는 다음 여덟 축으로 읽었다.

| 축 | 묻는 것 |
|---|---|
| A schema | 누가 정하는가, 어떤 형식인가, 추출 때 어떻게 강제하는가 |
| B 용어집 | 정식 이름과 별칭을 두는가, 누가 쓰는가, 추출 전에 주는가 추출 뒤에 정규화하는가 |
| C 원문 연결 | 엔티티·페이지가 원문의 어느 단위를 가리키는가, 처음 본 곳만인가 나온 모든 곳인가 |
| D 새/기존 연결 | 새 문서를 넣을 때 기존 엔티티와 어떻게 잇는가 |
| E 새 용어 | 용어집·schema 밖 이름을 버리는가, 자동 추가하는가, 승인 대기열에 두는가 |
| F 범용어 허브 | 흔한 용어가 모든 것을 잇는 문제를 막는 장치가 있는가 |
| G 이벤트 | 엔티티 말고 이벤트·시간축도 뽑는가 |
| H 근거 수치 | 이 설계의 효과를 잰 수치가 있는가 |

## 비교 표

모든 칸은 [확인]이다.
각 행의 보고서에 파일:줄 근거가 있다.
DEG-RAG와 ISO-RAG는 schema·용어집이 없어 질문 축을 통과하지 못했다.
범용어 허브(F) 참고로만 남긴다.

### A~D

| 후보 (보고서) | 무엇인가 | A schema | B 용어집 | C 원문 연결 | D 새/기존 연결 |
|---|---|---|---|---|---|
| jonex (`yuezhiai-jonex.md`) | 기업 KB. 그래프 경로와 llm-wiki 경로가 KB마다 배타 | 사람이 TBox YAML. 프롬프트 + 쓰기 전 검증 | 사람이 쓴 동의어 묶음. 추출 전 프롬프트 + 추출 뒤 정규화(문서 안만) | 청크. 문서 안 모든 청크(엔티티당 32). 다음 문서가 덮어씀 | 정확 키 MERGE. 관계 끝점만 별칭 대조 |
| beever-atlas (`beever-atlas.md`) | 대화 → fact·그래프 → 채널 wiki | 개발자가 프롬프트에 박음. 쓰기 전 검증 없음 | LLM이 씀. 기존 엔티티 전부 프롬프트 + 추출 뒤 대조 | 메시지. 나온 모든 곳 | 정확 → 임베딩 0.92 → LLM(스텁) |
| sage-wiki (`sage-wiki-ontology.md`) | Go llm-wiki + opt-in 그래프 | 사람이 config. 프롬프트 + 쓰기 직전 검증 | 사람은 관계 동의어만. 엔티티 별칭은 LLM, 제안은 사람이 승인 | 문서. cites는 모든 문서 누적, triple은 하나 | 이름 앵커 → 별칭 → 임베딩 0.85 → opt-in LLM resolution |
| synto (`synto-concept-registry.md`) | 로컬 LLM llm-wiki | 엔티티 종류 없음. 관계 18종 코드 고정 | LLM이 채우는 레지스트리. 사람은 사후 blessed alias·tombstone | 문서. 뽑힌 모든 문서(문서당 상한) | 층층 정확 대조. 임베딩 없음 |
| AutoSci (`autosci-omegawiki-schema.md`) | 연구용 llm-wiki(Claude Code) | 사람이 YAML(페이지 9·엣지 16). 엣지 쓰기 직전 거부 | 페이지 aliases(주로 LLM). 생성 직전 결정적 대조 도구 | 논문. 후보로 뽑힌 모든 논문 | 토큰 점수 ≥0.80 병합, 0.40~0.80 LLM 판단 |
| GD4AI (`gd4ai-obsidian-llm-wiki.md`) | Obsidian llm-wiki 플러그인 | 사람이 config.md. 프롬프트 + 쓰기 직전 삭제 | 페이지 제목 + aliases. 추출 뒤 대조 | 문서 + 인용문 2~4개 | slug·별칭 → 후보 30개 LLM 판정 → 별칭 학습 |
| Wikontic (`wikontic.md`) | KG 구축 논문 | Wikidata 제약 고정. 추출 뒤 정렬·검증 | 자동으로 자라는 alias 표. 추출 뒤만 | 문단. 처음 본 곳만(Mongo) | type 필터 임베딩 top-10 → LLM |
| LINK-KG (`link-kg.md`) | 판결문 KG 논문 | 연구자가 종류 7개. 프롬프트뿐 | LLM이 문서마다 키우는 캐시. 추출 전에 원문을 다시 씀 | 다시 쓴 글의 text unit. 원문 위치 끊김 | 문서 사이 없음. upper() 이름 일치 |
| OntoGPT (`ontogpt-spires.md`) | schema 기반 추출 도구 | 사람이 LinkML YAML. 프롬프트 + grounding 뒤 검증 | 온톨로지 + 사람 사전. 추출 뒤만 | 문서. label 출현 전부(첫 표면형만) | 같은 외부 ID일 때만 |
| Annif (`annif-mllm.md`) | 도서관 자동 색인 | 엔티티 schema 없음. SKOS 어휘가 닫힌 집합 | SKOS 정식·별칭 이름이 추출기 자체 | 모든 문장 → 특징으로 접힘. 링크는 문서→주제 | 어휘 id에 바로 붙음 |
| DEG-RAG (`deg-rag-denoise.md`) | KG 후처리 논문 | 없음(기본 4종) | 없음. 추출 뒤 이름 임베딩 병합 | 청크. 모든 청크 합집합 | 문자열 일치 + cosine 예산 안 union-find |
| ISO-RAG (`iso-rag-hub-pruning.md`) | passage 그래프 검색 | 없음 | 없음 | passage | 증분 없음. 매번 새로 지음 |

### E~H

| 후보 | E 새 용어 | F 범용어 허브 | G 이벤트 | H 근거 수치 |
|---|---|---|---|---|
| jonex | fallback 종류·보조 그래프로. 대기열 없음 | 직접 대책 없음. 관계 근거를 두 끝이 함께 나온 청크로 좁힘 | Event 종류 + date | 공개 평가 없음 |
| beever-atlas | 승인 없이 canonical. 타입 없는 이름은 Unresolved로 두고 LLM이 분류 | 프롬프트 금지어. 링크 단계 장치 없음 | Event·Meeting·Decision. 관계 valid_from/until | 추출 품질 수치 없음 |
| sage-wiki | concept 자동 생성. 모르는 술어는 버리고 로그만 | df 상한은 resolution 후보에만. 검색에서 Adamic-Adar | 이벤트 없음. 엣지 bi-temporal | LOCOMO 87.4%. 단 triple·resolve 꺼진 설정 |
| synto | 자동 새 entity. 사후 merge 후보 | 직접 없음. 문서당 개념 상한 | 없음 | 순서 무관성 테스트뿐 |
| AutoSci | 자동 생성. 논문당 한도, 넘으면 병합하거나 버림 | foundation 종말 계층. 그래프 탐색은 그 계층을 지나감 | 없음(속성만) | 없음 |
| GD4AI | 자동 새 페이지. schema 변경만 사람이 적용 | 위치 gate(기본 꺼짐). 문서 단위만 봄 | event 하위 종류. 날짜 필드 없음 | 후보 창 0/18 → 9/9. PPR recall@5 27.1% |
| Wikontic | 자동 새 label. 제약 위반 triplet은 사유와 보관 | 없음 | 시점 qualifier. 중복 키에 없어 버려짐 | MuSiQue EM 42.6, alias 없이 36.5 |
| LINK-KG | 고유명사는 자동 추가. 애매한 일반 명사구는 null | 프롬프트 고정 금지 목록 | 없음(claim 추출 꺼짐) | 긴 문서 중복률 36.01 → 17.78% |
| OntoGPT | `AUTO:` 접두 ID + 검증 리포트 | 전용 장치 없음. 부분 일치에 길이 비율 0.66 가드 | 템플릿이 정의할 때만 | GO grounding 98/100(SPIRES 없이 3) |
| Annif | 버림. debug 로그만 | idf·doc_freq·ambiguity 특징 + 문서당 limit + exclude | 없음 | LLM 재점수 nDCG@20 0.5507 → 0.5697 |
| DEG-RAG | 해당 없음 | 없음. union-find가 오히려 허브를 만듦 | 종류 하나 | 축소율을 올리면 승률이 봉우리 뒤 꺾임 |
| ISO-RAG | 해당 없음 | φ 비율로 edge 가지치기(검색 때) | 없음 | 2Wiki R@5 88.10 vs 69.05. 데이터 누수 의심 |

## 직전 실험의 네 문제에 대한 답

### 1. 원문 연결이 처음 본 곳에만 걸린다

[확인] 정독한 llm-wiki는 모두 "나온 모든 곳"으로 링크를 쌓는다. 사용자가 고친 방향이 다수의 설계와 같다.
- beever-atlas는 fact마다 엔티티 태그 전부로 `MENTIONED_IN` 링크를 건다(`beever-atlas.md` #C).
- sage-wiki는 concept→문서 cites를 컴파일마다 쌓는다(`sage-wiki-ontology.md` #C).
- AutoSci는 병합 때마다 논문을 `key_papers`에 덧붙인다(`autosci-omegawiki-schema.md` #C).
- GD4AI는 `sources:`에 "Append new sources, never overwrite"로 덧붙인다(`gd4ai-obsidian-llm-wiki.md` #C).

[확인] 단위는 대부분 문서다. 청크 단위로 거는 곳은 jonex와 DEG-RAG뿐이다. 메시지·fact 단위는 beever-atlas다.

[확인] jonex만 용어집 별칭으로 원문을 다시 훑어 링크를 채운다. 정식 이름과 LLM이 낸 별칭을 문서의 모든 청크와 3단계로 대조한다(`yuezhiai-jonex.md` #C). 사용자 실험의 "모든 청크 링크"와 가장 가깝다.

"처음 본 곳만"을 되살리는 함정이 셋 있었다.

| 후보 | 함정 | 근거 |
|---|---|---|
| Wikontic | 같은 triplet이 다시 나오면 `$setOnInsert`로 처음 문단만 남긴다 | `wikontic.md` #C, `mongo_backend.py:269-270` |
| jonex | 문서를 넘으면 엔티티 노드의 `source_chunks`·`aliases`를 덮어써 마지막 문서 것만 남는다 | `yuezhiai-jonex.md` #C, `ontology_graph_repository.py:162, 168-169` |
| OntoGPT | CLI가 "이미 본 ID" 캐시를 비우지 않아 뒤 문서의 span에서 빠진다. span은 첫 표면형 하나로만 찾는다 | `ontogpt-spires.md` #C, `cli.py:525-537` |

[확인] 정밀도 쪽 경고도 있다. synto는 PDF 문서에서 개념을 낸 큰 unit 안의 모든 segment에 출현을 붙인다(`synto-concept-registry.md` #C). jonex의 셋째 대조 단계는 조각 절반 일치라 여러 단어 이름이 넓게 걸린다(`ontology_extraction_skills.py:213`). 둘 다 사용자 실험의 정밀도 하락과 같은 방향이다.

### 2. 새/기존 연결 발견

[확인] 공통 순서는 "정확 일치·별칭 대조 → 임베딩 또는 토큰 점수 → 애매한 것만 LLM 판정"이다.
beever-atlas, sage-wiki, Wikontic, GD4AI가 이 모양이다.
synto와 AutoSci는 임베딩 없이 결정적 대조로 끝낸다.

후보마다 다른 점이 가져올 거리다.

| 장치 | 후보 | 쓸모 |
|---|---|---|
| 판정 뒤 새 표기를 기존 페이지 별칭에 더한다 | GD4AI(`path-resolution.ts:349`) | 다음 문서부터는 LLM 없이 붙는다 |
| 합치지 않고 derived edge로 잇는다. `--unlink`로 정확히 되돌린다 | sage-wiki(`graph-memory.md:129-144`) | 사람이 일부만 검토해도 실수 비용이 낮다 |
| 이름만 같으면 판정을 미루고, 원문이 선언한 별칭·id만 증거로 친다 | jonex_wiki(`identity.py:10-17`) | 범용어 동명 병합을 막는다 |
| 이름+별칭 결정적 대조 도구(약 120줄) | AutoSci `find-similar-concept` | 사용자 용어집 150개를 그대로 입력으로 쓸 수 있다 |
| type 계열로 좁힌 alias 표 대조 | Wikontic | 뿌리 type(`entity`)이 거의 모든 type의 조상이라 필터가 넓다 |

[확인] 잰 수치는 둘뿐이다.
- Wikontic 소거 실험에서 MuSiQue EM은 전체 42.6, alias 없이 36.5였다(`wikontic.md` #H).
- GD4AI는 중복 판정에 전체 목록을 주면 동의어 대상을 18번 중 0번 찾았다. 30개 창이면 9번 중 9번 찾았다(`gd4ai-obsidian-llm-wiki.md` #H).

[확인] 문서 사이 연결의 정밀도·재현율을 잰 후보는 없다. 사용자 실험의 0.92/0.37과 비교할 숫자가 없다.

[확인] 함정도 있다. beever-atlas는 임베딩 비교를 같은 배치 안끼리만 한다. LLM 판정 함수는 항상 False를 돌려주는 스텁이다(`beever-atlas.md` #D). 이름만 3단 절차이고 기존 엔티티와의 임베딩 대조는 없다.

### 3. 범용어 허브

[확인] llm-wiki 쪽에서 링크를 만드는 단계에 범용어 장치를 둔 곳은 없다.
가장 가까운 장치는 세 갈래다.

| 갈래 | 후보 | 하는 일 | 한계 |
|---|---|---|---|
| 링크 점수에 흔함을 넣는다 | Annif | doc_freq·tf-idf·ambiguity를 특징으로 학습된 분류기가 점수를 매긴다. 문서당 limit로 자른다. exclude 목록으로 수동 제외한다 | 정답 링크가 있어야 학습한다. 특징별 ablation이 없다 |
| 범용어를 따로 받는 계층 | AutoSci | foundation 종류(`terminal: true`)가 범용어를 받는다. 역링크와 엣지 투영에서 빠진다 | `neighbors` BFS가 terminal을 보지 않아 foundation을 거쳐 엉뚱한 논문이 이어진다 |
| 검색 때 허브를 약하게 | sage-wiki, ISO-RAG | sage-wiki는 Adamic-Adar 1/log(degree)와 관계별 가중치를 쓴다. ISO-RAG는 양 끝 φ 비율이 floor 미만인 edge를 자른다 | 그래프의 허브 자체는 남는다. ISO-RAG 수치는 평가 질문과 그래프를 같은 인스턴스로 만들어 부풀었을 수 있다 |

근거 보고서는 `annif-mllm.md` #F, `autosci-omegawiki-schema.md` #F, `sage-wiki-ontology.md` #F, `iso-rag-hub-pruning.md` #F다.

[확인] 나머지 장치는 부분 대책이다.
- sage-wiki의 `max_token_df`(기본 0.05, floor 20)는 resolution 후보 묶기에서만 흔한 토큰을 뺀다.
- jonex는 관계 근거를 두 끝이 함께 나온 청크 교집합으로 좁힌다. 비면 합집합으로 물러난다.
- OntoGPT는 사전 부분 일치에 길이 비율 0.66 초과 조건을 걸어 짧은 범용어의 흡수를 막는다.
- beever-atlas와 LINK-KG는 프롬프트 금지어 목록만 있다.

[확인] 반대로 허브를 키우는 장치도 있다. DEG-RAG의 union-find는 사슬 병합으로 "Naive Bayes Model and Support Vector Machine Model being merged into Decision Tree" 같은 상위 개념 허브를 만든다(`deg-rag-denoise.md` #F). LINK-KG의 few-shot 예시는 SMUGGLER(S) 같은 역할 일반명을 노드로 가르친다(`link-kg.md` #F).

[확인] 반대쪽에서 막는 장치가 하나 있다. GD4AI는 두 페이지가 같은 이름을 가지면 결정론 병합을 멈추고 LLM 판정으로 넘긴다(`gd4ai-obsidian-llm-wiki.md` #D). 단 엔진이 더하는 별칭에만 중복 검사를 건다.

[확인] 병합 강도를 정하는 데 쓸 곡선은 DEG-RAG에 있다. 축소율을 올리면 LLM judge 승률이 봉우리를 그린 뒤 떨어진다. 봉우리는 CS 0.3, Legal 0.5, Agriculture 0.2, Mix 0.5였다(`deg-rag-denoise.md` #H). 사용자 실험에서 용어집이 범용어를 모아 정밀도가 떨어진 현상과 같은 방향이다.

### 4. 새 용어 승인

[확인] 새 엔티티 이름을 사람 승인 대기열에 두는 후보는 없다. 12개 모두 자동 추가하거나 버린다.

대기열을 직접 만들 때 입력이 될 장치는 있다.

| 장치 | 후보 | 근거 |
|---|---|---|
| 어휘 밖 이름에 `AUTO:` 접두 ID를 붙이고 검증 리포트에서 UNRESOLVED로 센다 | OntoGPT | `ontogpt-spires.md` #E |
| schema 밖이거나 제약을 어긴 triplet을 사유와 함께 따로 보관한다 | Wikontic | `wikontic.md` #E |
| 타입 없는 이름을 Unresolved 노드로 두고 나중에 분류한다 | beever-atlas | `beever-atlas.md` #E |
| 사람이 뗀 별칭을 다음 추출이 되살리지 못하게 tombstone을 남긴다 | synto | `synto-concept-registry.md` #E |
| threshold를 1.0으로 두면 resolution 제안이 전부 대기열로 간다 | sage-wiki | `sage-wiki-ontology.md` #E |
| 문서당 생성 한도. 넘는 후보는 가장 가까운 항목에 병합하거나 버린다 | AutoSci | `autosci-omegawiki-schema.md` #E |
| schema 변경 제안을 `suggestions.md`에 쌓고 사람이 적용한다 | GD4AI | `gd4ai-obsidian-llm-wiki.md` #E |

[확인] sage-wiki의 대기열은 별칭 제안용이다. 새 용어나 새 관계 종류를 올리는 대기열은 아니다.

[추정] AutoSci의 문서당 한도를 "넘는 후보는 대기열 파일로"로 바꾸는 것이 사용자 목표에 가장 짧은 길이다 — 사례: AutoSci가 이미 한도를 넘는 후보를 골라내는 지점 1곳(`dedup-policy.md:52`).

## 엔티티·이벤트 추출

[확인] 문서를 넣으면 엔티티를 만드는 것은 12개 모두 한다. 이벤트는 셋 중 하나의 모양으로 다룬다.

| 모양 | 후보 | 내용 |
|---|---|---|
| 이벤트를 schema의 엔티티 종류로 둔다 | jonex, beever-atlas, GD4AI | jonex는 Event+date, Mission·Incident+날짜를 둔다. beever-atlas는 Event·Meeting·Decision을 뽑는다. GD4AI는 event 하위 종류만 있고 날짜 필드가 없다 |
| 시간을 관계(엣지)에 붙인다 | sage-wiki, beever-atlas | sage-wiki는 엣지마다 valid_from/valid_to를 두고, functional 관계에 새 엣지가 오면 이전 엣지를 무효화한다. beever-atlas는 관계 valid_from·valid_until과 fact 무효화(`superseded_by`)를 둔다 |
| 시점을 triplet 수식어로 둔다 | Wikontic | point in time qualifier다. 중복 키에 없어 같은 사실의 다른 시점이 버려진다 |

[확인] synto, AutoSci, Annif, LINK-KG는 이벤트를 뽑지 않는다. OntoGPT는 템플릿 작성자가 이벤트 클래스를 정의할 때만 뽑는다.

[확인] 이벤트 추출 품질을 잰 후보는 없다.

[추정] 사용자 시스템에서는 이벤트를 schema의 엔티티 종류로 두고 날짜 속성을 붙이는 것이 가장 쉽다 — 사례: jonex, beever-atlas 2개가 프롬프트와 종류 목록만으로 이렇게 한다. 사용자 schema의 엔티티 종류 10개에 Event를 더하면 지금 파이프라인을 그대로 쓸 수 있다. 사실이 바뀌는 것(직책, 버전)을 다루려면 sage-wiki처럼 관계에 유효 기간을 붙여야 한다.

## 가져올 것과 라이선스

| 후보 | 가져올 것 | 피할 것 | 라이선스 | 코드 복사 |
|---|---|---|---|---|
| jonex | 모든 청크 링크 + 관계 근거는 두 끝 공존 청크로 좁히기. 용어집을 프롬프트와 정규화 키 대조에 둘 다. 이름만 같으면 보류하는 identity 규칙 | 노드 `source_chunks`·`aliases` 덮어쓰기. 조각 절반 일치 대조 | 수정 Apache 2.0 | 다중 테넌트·브랜드 조항을 지키면 가능. 소유자가 조건을 바꿀 수 있다 |
| beever-atlas | fact마다 모든 엔티티로 거는 링크. 관계 동사 정규화 표(대응표 → 정규식 → catch-all). Unresolved 보관 후 분류 | 배치 안끼리만 임베딩 비교. 레지스트리 사본 공유 | Apache-2.0 | 가능. LICENSE·NOTICE 동봉, 이름·로고 금지 |
| sage-wiki | 프롬프트 목록 + enum 없는 schema + 쓰기 직전 검증. 술어 동의어 사후 대조. 되돌릴 수 있는 derived edge. 종류별 df 상한 | evidence가 summary 인용이고 검색 청크가 article 단위인 점 | MIT | 가능. 저작권 고지 |
| synto | alias 출처 등급(weak/blessed). 거부 tombstone. 충돌은 merge 후보 목록으로 | unit 전체 segment로 출현 퍼뜨리기 | MIT | 가능. 저작권 고지 |
| AutoSci | YAML → loader → 엣지 쓰기 직전 거부. `find-similar-concept`. 범용어 종말 계층. 문서당 한도 | terminal 우선 정렬이 정확 일치를 덮는 점. 논문 단위 연결 | MIT | 가능. 저작권 고지 |
| GD4AI | 어휘를 한 함수에서 만들어 프롬프트와 검사에 같이 쓰기. 목록 밖 type 재선택. 판정 뒤 별칭 학습. 같은 이름 두 페이지면 LLM 판정 | LLM이 쓴 별칭에 중복 검사가 없는 점 | Apache-2.0 | 가능. LICENSE·NOTICE, 변경 표시 |
| Wikontic | label+alias+embedding 표. 정확 일치는 바로, 나머지만 LLM. 위반 triplet 보관 | `$setOnInsert` 중복 처리. 중복 키에 없는 qualifier | MIT | 가능. 저작권 고지 |
| LINK-KG | 종류별 alias 캐시를 청크마다 프롬프트에. canonical 한 줄 설명. 애매한 일반 명사구 null 규칙 | 원문을 다시 쓴 뒤 추출 | 저장소 라이선스 없음. 논문 CC BY 4.0 | 불가. 아이디어만 |
| OntoGPT | 종류마다 허용 어휘·ID 형식. 정확 → 길이 비율 0.66 부분 일치 → 외부 어휘. `AUTO:` + 검증 리포트. 예시와 같은 이름은 hallucination 후보 | "이미 본 ID" 캐시. 첫 표면형만 span 찾기 | BSD-3-Clause, 템플릿 CC0 | 가능. 저작권 고지 |
| Annif | 모든 청크에서 후보 → 청크마다 tf×idf·ambiguity 점수 → 상위 k·threshold. 메타 용어 exclude 목록을 링크 단계에만 | 없음 | Apache-2.0 | 가능. 고지·사본·변경 표시 |
| DEG-RAG | 병합 강도를 sweep 곡선으로 고르기. 엔티티 종류 blocking. 합친 이름을 별칭으로 기록 | union-find 사슬 병합 | 코드 라이선스 없음. 논문 CC BY 4.0 | 불가. 설계만 |
| ISO-RAG | 부피=1로 둔 φ 비율 edge 필터를 링크 후보에 시험 | random walk 구현(`retrieval_utils.py`) | 코드 라이선스 없음. 논문 CC BY 4.0 | 불가. 수식만 다시 구현 |

[추정] 범용어 허브에는 세 장치를 함께 시험할 만하다 — 사례: Annif의 idf 점수, AutoSci의 종말 계층, sage-wiki의 df 상한 3개가 각자 다른 단계에서 같은 문제를 건드린다. 링크 단계에서 이들을 사용자 데이터로 잰 곳은 없다. 기존 보고서 `autoschemakg-kg-construction/lab/reports/19-tentative-links.md`의 1/log(df) 가중과 같은 정답 쌍으로 비교하면 된다.

## 모르는 것

| 모르는 것 | 무엇을 보면 알 수 있는가 |
|---|---|
| 사람 용어집이 문서 사이 연결의 정밀도·재현율을 얼마나 바꾸는가. 12개 중 잰 곳이 없다 | 사용자 실험의 정답 쌍으로 용어집 있음/없음, 범용어 제외 있음/없음을 직접 잰다 |
| jonex 내부 평가(별칭 누락 "30 대 107", "V2 进阶测评")가 무엇을 셌는가 | 공개본에서 지워졌다(`CHANGELOG.md:20-22`). 저자에게 묻는 것 말고는 길이 없다 |
| Annif의 범용어 대책 특징(doc_freq, ambiguity)이 각각 얼마나 기여하는가 | 두 논문에 특징별 ablation이 없다. Annif에서 특징을 하나씩 빼고 학습해 보면 안다 |
| ISO-RAG 수치가 데이터 누수로 부풀었는가 | 평가 질문과 그래프를 다른 인스턴스로 나눈 재실험 |
| sage-wiki에서 임베딩 dedup으로 합쳐진 concept에 cites 엣지가 생기는가. [추정] 안 생긴다 — 사례: cites를 쓰는 곳 1곳(`write.go:378`) | 합쳐지는 문서 쌍으로 컴파일을 돌려 cites 엣지를 센다 |
| beever-atlas upsert가 예전 별칭을 지우는가 | 코드만 읽었다. 같은 엔티티를 두 번 upsert해 aliases를 본다 |
| llama3.1:8b 같은 작은 로컬 모델로 이 설계들이 도는가 | 정독한 후보 누구도 작은 모델 품질을 보고하지 않았다. synto만 로컬 LLM을 전제로 한다 |
| 제외한 Jiwei/auto_archivist의 큐레이션 seed 우선(`alias_map.py:51-53`)이 사람 용어집 경로인가 | 정독하지 않았다. 그 파일과 seed 입력 경로를 읽는다 |
| EventRAG, E²RAG, DyG-RAG가 schema·용어집을 쓰는가 | 초록만 확인했다. 본문 방법 절과 코드 공개 여부를 본다 |
| Tana가 별칭(B)과 기존 노드 연결(D)을 하는가 | 제품 문서에서 확인하지 못했다. 직접 써 보거나 API 문서를 본다 |

## 제외한 후보

| 이름 | URL | 이유 |
|---|---|---|
| atomicstrata/llm-wiki-compiler | https://github.com/atomicstrata/llm-wiki-compiler | 기존 보고서 `../atomicstrata-llm-wiki-compiler.md`가 정독했다. 별칭을 병합 키로 쓰지 않는다 |
| Ar9av/obsidian-wiki | https://github.com/Ar9av/obsidian-wiki | 기존 보고서 `../ar9av-obsidian-wiki.md`가 다뤘다. 통제 어휘가 태그에 걸려 있다 |
| seominpapa/llm-wiki-for-team | https://github.com/seominpapa/llm-wiki-for-team | 용어집이 없다. 관계 상태·typed 엣지 분리는 요약으로 충분하다 |
| balukosuri/llm-wiki-karpathy | https://github.com/balukosuri/llm-wiki-karpathy | 프롬프트만 쓰는 템플릿이다. 사용자 실험이 이미 더 강하게 해 봤다 |
| mpashka/llm-wiki-tags | https://github.com/mpashka/llm-wiki-tags | 규칙 문서뿐이고 대상이 코드베이스 문서다 |
| gentslava/brainmd | https://github.com/gentslava/brainmd | 용어집이 없다. 끌개 노드 A/B 수치는 n=6/arm이고 요약에 있다 |
| Jiwei/auto_archivist | https://github.com/Jiwei/auto_archivist | 한 번에 돌리는 파이프라인이라 D·E가 약하다. 용어집을 LLM이 사후에 만든다 |
| Lambenthan/empiricalwiki | https://github.com/Lambenthan/empiricalwiki | AutoSci 파생이다. 원본을 골랐다 |
| zby/commonplace | https://github.com/zby/commonplace | 별칭 대조·엔티티 추출이 없다 |
| SrsBlack/ict-knowledge-library | https://github.com/SrsBlack/ict-knowledge-library | 도구가 아니라 내용 저장소다 |
| Retrieval as Reasoning (arXiv 2605.25480) | https://arxiv.org/abs/2605.25480 | 코드가 없다. schema 결정 주체와 새 용어 처리가 적혀 있지 않다 |
| EDC (arXiv 2404.03868) | https://arxiv.org/abs/2404.03868 | 관계 schema 사후 정규화만 다룬다. 사용자 실험과 겹친다 |
| SPIRES / OntoGPT (논문 항목) | https://arxiv.org/abs/2304.02711 | OntoGPT 항목과 중복이다 |
| ODKE+ (arXiv 2509.04696) | https://arxiv.org/abs/2509.04696 | 코드가 없다. alias 사전 언급이 없다 |
| iText2KG + ATOM (arXiv 2409.03284) | https://arxiv.org/abs/2409.03284 | 정식 이름·alias 사전이 없는 임베딩 병합 대조군이다 |
| LLM-Assisted French Legal KG (arXiv 2607.24551) | https://arxiv.org/abs/2607.24551 | 제약이 프롬프트뿐이다. 사람 alias 사전·범용어 장치가 없다 |
| KGGen (arXiv 2502.09956) | https://arxiv.org/abs/2502.09956 | 사람 schema가 없다. 비교 수치는 Wikontic 논문에 있다 |
| Zep / Graphiti (arXiv 2501.13956) | https://arxiv.org/abs/2501.13956 | 사람 별칭 표가 없다. `../00-discovery.md:114`에 이미 있다 |
| OG-RAG (arXiv 2412.15235) | https://arxiv.org/abs/2412.15235 | alias·정규화·원문 연결 단위가 적혀 있지 않다 |
| Ontology-grounded AKGC (arXiv 2412.20942) | https://arxiv.org/abs/2412.20942 | 코드가 없다. 관계 정규화만 다룬다 |
| HippoRAG (arXiv 2405.14831) | https://arxiv.org/abs/2405.14831 | node specificity는 `19-tentative-links.md:142`가 이미 다뤘다 |
| OntoKGen (arXiv 2412.00608) | https://arxiv.org/abs/2412.00608 | 초록만 확인했다. 코드가 없다 |
| DIAL-KG (arXiv 2603.20059) | https://arxiv.org/abs/2603.20059 | 초록만 확인했다. 코드가 없다 |
| MAGG (arXiv 2608.28642) | https://arxiv.org/abs/2608.28642 | 코드가 없다. 검토자가 LLM 에이전트다 |
| OntoGPT / SPIRES (저장소 항목) | https://github.com/monarch-initiative/ontogpt | OntoGPT 항목과 중복이다 |
| mattpocock/skills domain-modeling (papers 항목) | https://github.com/mattpocock/skills | 추출 코드가 없다. "일반 용어는 용어집에 넣지 말라" 규칙(`CONTEXT-FORMAT.md:29`)만 인용할 만하다 |
| Cognee ontology resolver | https://github.com/topoteretes/cognee | `skos:altLabel`을 읽지 않는다. 처음 본 청크 링크는 사용자가 이미 고쳤다 |
| KARMA (arXiv 2502.06472) | https://arxiv.org/abs/2502.06472 | 코드·임계값·효과 수치가 없다 |
| Golden-Retriever (arXiv 2408.00798) | https://arxiv.org/abs/2408.00798 | 용어집을 검색 질의 확장에 쓴다. 코드가 없다 |
| Telco-oRAG (arXiv 2505.11856) | https://arxiv.org/abs/2505.11856 | 검색 쪽 용어집이다. 용어집 ablation이 아니다 |
| Terminology Augmented Generation (CEUR Vol-3990) | https://ceur-ws.org/Vol-3990/short10.pdf | 과제가 번역·용어 교정이다 |
| getzep/graphiti | https://github.com/getzep/graphiti | 사람 별칭 표가 없다. 시간축은 beever-atlas로 본다 |
| WhyHow Knowledge Graph Studio | https://github.com/drahnreb/knowledge-graph-studio | 원본이 404이고 사본은 2024-11에 멈췄다 |
| trustgraph-ai/trustgraph (OntoRAG) | https://github.com/trustgraph-ai/trustgraph | 별칭 사전이 없다. 정규화는 소문자화뿐이다 |
| neo4j/neo4j-graphrag-python | https://github.com/neo4j/neo4j-graphrag-python | 별칭 사전이 없는 범용 프레임워크다 |
| neo4j-labs/llm-graph-builder | https://github.com/neo4j-labs/llm-graph-builder | 별칭 사전이 없다. 승인형 dedup은 sage-wiki와 겹친다 |
| HKUDS/LightRAG | https://github.com/HKUDS/LightRAG | 관계 schema·용어집이 없다. 엔티티당 청크 200개 상한만 참고한다 |
| microsoft/graphrag | https://github.com/microsoft/graphrag | 별칭 처리가 없다. 대문자 정확 일치로만 합친다 |
| LlamaIndex SchemaLLMPathExtractor | https://github.com/run-llama/llama_index | 용어집이 없다 |
| LangChain LLMGraphTransformer | https://github.com/langchain-ai/langchain-experimental | 별칭·entity resolution이 없다 |
| SciPhi-AI/R2R | https://github.com/SciPhi-AI/R2R | 종류 목록을 프롬프트에만 넣는다. 2025-11 이후 멈췄다 |
| junhewk/simple-graph-builder | https://github.com/junhewk/simple-graph-builder | D 순서가 sage-wiki·beever-atlas와 겹친다. 용어집이 없다 |
| Crokily/MyWiki | https://github.com/Crokily/MyWiki | `taxonomy.md` 통제 어휘는 좋은 형식이지만 강제가 프롬프트뿐이다 |
| basicmachines-co/basic-memory | https://github.com/basicmachines-co/basic-memory | 정식 이름+별칭 용어집이 없다. AGPL이다 |
| Aldeia-IT/anytype-llm-wiki | https://github.com/Aldeia-IT/anytype-llm-wiki | 저장된 별칭 목록이 없다. C가 문서 단위다 |
| TrueHOOHA/LLM-Wiki | https://github.com/TrueHOOHA/LLM-Wiki | skill 체크리스트뿐이고 중앙 용어집이 없다 |
| mattpocock/skills domain-modeling (wiki 항목) | https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling | papers 항목과 중복이다 |
| tsipotU/glossary-skill | https://github.com/tsipotU/glossary-skill | 용어집 형식만 있다. 추출·wiki가 없다 |
| terrylica/cc-skills glossary-management | https://github.com/terrylica/cc-skills/tree/main/plugins/doc-tools/skills/glossary-management | 쓴 뒤 lint하는 docs-as-code다. 추출·wiki가 없다 |
| Egonex-AI/Understand-Anything understand-knowledge | https://github.com/Egonex-AI/Understand-Anything/tree/main/understand-anything-plugin/skills/understand-knowledge | 엔티티 중복 제거가 소문자·공백뿐이다 |
| Vault-LD spec | https://github.com/The-Knowledge-Graph-Guys/vault-ld | 형식 명세다. LLM 추출기가 없다 |
| Tana supertags + AI | https://outliner.tana.inc/learn/features/supertags | 상용 제품이다. B·D를 확인하지 못했다 |
| ProfessionalWiki/MediaWiki-MCP-Server | https://github.com/ProfessionalWiki/MediaWiki-MCP-Server | 추출·별칭·entity resolution이 없다 |
| OpenAI Cookbook Temporal Agents with KG | https://github.com/openai/openai-cookbook/tree/main/examples/partners/temporal_agents_with_knowledge_graphs | 술어 목록 절차가 사용자 실험과 거의 같다. 별칭 표가 없다 |
| AuvaLab/itext2kg (ATOM) | https://github.com/AuvaLab/itext2kg | iText2KG 항목과 중복이다 |
| ATOM (arXiv 2510.22590) | https://arxiv.org/abs/2510.22590 | iText2KG 항목과 중복이다. 수치를 PDF로 확인하지 못했다 |
| vectorize-io/hindsight | https://github.com/vectorize-io/hindsight | 대화 기억용이라 wiki·별칭 표가 없다 |
| swarmclawai/swarmvault | https://github.com/swarmclawai/swarmvault | schema 강제가 프롬프트뿐이다. `../00-discovery.md:126`에서 이미 뺐다 |
| EventRAG (ACL 2025) | https://aclanthology.org/2025.acl-long.830/ | 초록만 확인했다 |
| E²RAG (arXiv 2506.05939) | https://arxiv.org/abs/2506.05939 | 초록만 확인했다. 코드·수치가 없다 |
| DyG-RAG (arXiv 2507.13396) | https://arxiv.org/abs/2507.13396 | schema·용어집 유무를 알 수 없다 |
| max-fluff/obsidian-glossary-linker | https://github.com/max-fluff/obsidian-glossary-linker | LLM 추출이 없는 링커다. excluded terms와 Candidates 승인 대기열은 README 인용으로 요약에 있다 |
| vschroeter/obsidian-virtual-linker | https://github.com/vschroeter/obsidian-virtual-linker | `19-tentative-links.md` #1.2가 다뤘다 |
| kdnk/obsidian-automatic-linker | https://github.com/kdnk/obsidian-automatic-linker | F 장치가 노트별 exclude 플래그뿐이다 |
| sawhney17/logseq-automatic-linker | https://github.com/sawhney17/logseq-automatic-linker | 2024-08에 멈췄다. LLM 추출이 없다 |
| Jonatan-Jurado/ObsidianGlossaryLinker | https://github.com/Jonatan-Jurado/ObsidianGlossaryLinker | stoplist·빈도 기준·entity resolution이 없다 |
| Wikipedia MOS:OVERLINK / DUPLINK | https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Linking | 편집 규칙 문서다. 필요한 규칙은 요약에 있다 |
| Milne & Witten 2008 | https://doi.org/10.1145/1458082.1458150 | `19-tentative-links.md` #1.4가 다뤘다 |
| Mihalcea & Csomai 2007, Wikify! | https://doi.org/10.1145/1321440.1321475 | `19-tentative-links.md` #1.4가 다뤘다 |
| Gerlach 외 2021 + research-mwaddlink | https://arxiv.org/abs/2105.15110 | `19-tentative-links.md` #1.2가 일부 다뤘다. llm-wiki 쪽 후보를 우선했다 |
| HippoRAG 2 (arXiv 2502.14802) | https://arxiv.org/abs/2502.14802 | synonym edge ablation이 없다 |
| RAG vs. GraphRAG (arXiv 2502.11371) | https://arxiv.org/abs/2502.11371 | 정규화·별칭 병합 ablation이 없다 |
| GraphRAG-Bench (arXiv 2506.05690) | https://arxiv.org/abs/2506.05690 | 엔티티 병합이나 그래프 정오를 재지 않는다 |
| In-depth Analysis of Graph-based RAG (arXiv 2503.04338) | https://arxiv.org/abs/2503.04338 | 엔티티 병합 효과를 따로 재지 않는다 |
| Youtu-GraphRAG (arXiv 2508.19855) | https://arxiv.org/abs/2508.19855 | 용어집·별칭이 없다. 새 schema 요소를 승인 없이 더한다 |
| LiteRAG (arXiv 2609.10239) | https://arxiv.org/abs/2609.10239 | 코드가 없다. 질문 32개, recall 지표가 없다 |
| LinearRAG (arXiv 2510.10114) | https://arxiv.org/abs/2510.10114 | schema·용어집이 없다 |
| GAAMA (arXiv 2603.27910) | https://arxiv.org/abs/2603.27910 | hub dampening 효과가 정성 서술뿐이다 |
| Annif at GermEval-2025 (arXiv 2508.15877) | https://arxiv.org/abs/2508.15877 | Annif 저장소 항목에 합쳤다 |
| SemEval-2025 Task 5 overview | https://arxiv.org/abs/2504.07199 | 대회 개요 논문이다 |
| DNB-AI-Project at SemEval-2025 (arXiv 2504.21589) | https://arxiv.org/abs/2504.21589 | altLabel 임베딩 사후 정규화가 사용자 실험과 같은 자리다. F는 미해결이다 |
| NLM MEDLINE MTIX와 Check Tags | https://www.nlm.nih.gov/pubs/techbull/ma24/ma24_mtix.html | 코드가 없는 제품 문서다. 근거 Q&A PDF가 404다 |
| MeSH 신규 용어 제안·연간 갱신 | https://www.nlm.nih.gov/mesh/meshsugg.html | 절차 문서다. E 설계는 요약으로 충분하다 |
| VocBench 3 | https://vocbench.uniroma2.it/doc/vb2_vs_vb3.jsf | 코드가 없는 제품 문서다 |
| MTI scoping review 2000–2025 (JMLA) | https://jmla.pitt.edu/ojs/jmla/article/view/2406 | 리뷰 논문이다. "1/3은 사람 검수" 수치만 쓸 만하다 |

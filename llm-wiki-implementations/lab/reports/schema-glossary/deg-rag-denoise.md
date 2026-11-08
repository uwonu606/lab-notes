# DEG-RAG는 용어집 없이 뒤늦게 노드를 합치는 후처리이고, 과하게 합치면 효과가 꺾인다는 곡선만 줄 뿐 연결 품질은 재지 않았다

DEG-RAG(arXiv 2510.14271, "Less is More: Denoising Knowledge Graphs For Retrieval Augmented Generation")는 LLM이 이미 만든 KG를 두 단계로 청소한다.
첫 단계 entity resolution은 임베딩이 비슷한 노드 쌍을 골라 하나로 합친다.
둘째 단계 triple reflection은 LLM judge가 매긴 점수가 낮은 edge를 지운다.
사람이 정한 schema나 용어집은 없다.
엔티티 종류 4개(`organization, person, geo, event`)는 DIGIMON에서 물려받은 기본값이다.

사용자 목표("raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조")에 주는 답은 셋이다.
- [확인] 합치기는 "몇 %를 줄일지"라는 예산으로 돈다. 유사도 임계값 δ_ER은 논문 식에만 있고 코드에는 없다. 논문도 δ_ER 값을 보고하지 않는다.
- [확인] 공개 코드에서 쌍의 유사도는 사실상 이름만 임베딩해 구한다. 임베딩 문장 틀에는 종류와 설명 자리가 있지만, 그 값을 읽어 오는 파일에 두 필드가 없다(#축별 분석의 A 참조). 코드를 읽어서 본 것이고 실행하지는 않았다.
- [확인] 줄이는 비율을 올리면 LLM judge 승률이 봉우리를 그린 뒤 떨어진다. CS는 30%에서 64.3, 80%에서 39.6이다. 사용자 실험에서 용어집이 범용어를 한 이름으로 모아 정밀도가 떨어진 현상과 같은 방향이다.
- [확인] 범용어 허브를 막는 장치는 없다. 막는 것은 같은 엔티티 종류 안에서만 합치는 blocking 하나다. 연결의 정밀도·재현율도 재지 않았다. 사용자 실험의 연결 재현율·정밀도 같은 수치와 직접 비교할 숫자는 없다.

## 한 바퀴 흐름

문서 하나가 노드가 되기까지의 순서다. 1~2는 DIGIMON 원본 코드, 3~7은 이 저장소가 더한 `denoise_kg/` 코드다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. 청크 | 1,200 token, overlap 100으로 자른다 | `Option/Method/LGraphRAG.yaml` `chunk_token_size: 1200`, 논문 C.1 |
| 2. 추출 | 청크마다 LLM이 `("entity"<|>이름<|>종류<|>설명)`, `("relationship"<|>…)` 레코드를 낸다. 이름은 `clean_str`로 소문자화하고 영숫자 밖 문자를 공백으로 바꾼다. 같은 문자열이면 한 노드로 합치고 `source_id`(청크 id)를 합집합한다 | `Core/Graph/RKGraph.py:33-50`, `Core/Common/Utils.py:34-45`, `Core/Graph/BaseGraph.py:72-100` |
| 3. blocking | 노드 설명을 임베딩해 k-means(k=10 고정) 또는 `entity_type`별 묶음(512개 넘으면 k-means) 또는 연결 요소로 나눈다 | `denoise_kg/cluster.py:125-177`, `scripts/run_all.sh:38` |
| 4. 쌍 고르기 | `"Entity: {id}. Type: {type}. Description: {desc}"`를 임베딩한다. 다만 type·desc를 읽는 `node_data_map`이 3단계 출력(`node_id`, `source_text`, `similar_nodes`만 있음)이라 실제 문장은 `"Entity: {id}. Type: N/A. Description: "`가 된다. 같은 block 안 모든 쌍의 cosine을 구해 전체를 내림차순 정렬한다. union-find로 합쳐 가며 합친 수가 `노드 수 × reduction`에 닿으면 멈춘다 | `denoise_kg/similar_percentage.py:32-35`, `:160-165`, `:254-320`, `denoise_kg/cluster.py:185-189`, `scripts/run_all.sh:44`, `:83` |
| 5. triple reflection | edge마다 LLM이 0~1 점수와 analysis를 JSONL로 낸다 | `denoise_kg/edge_clean.py:84-115` |
| 6. 합치기 | union-find root(id 문자열이 가장 작은 노드)로 나머지를 옮긴다. 설명·`source_id`는 합집합, 종류는 최빈값, edge는 root로 다시 잇고 합쳐진 노드는 지운다. 2,000 token 넘는 설명은 LLM이 요약한다(논문 C.3은 4,000). 점수가 임계값 미만인 edge와 self-loop를 지운다 | `denoise_kg/merge.py:28-89`, `:210-300`, `Core/Utils/MergeSum.py:105-144` |
| 7. 평가 | 원래 KG와 청소한 KG로 각각 답을 만들고 LLM judge가 쌍대 비교한다 | `denoise_kg/winrate.py`, 논문 C.5 |

## 축별 분석

### A schema

[확인] 사람이 정한 schema는 없다.
엔티티 종류는 상수 `DEFAULT_ENTITY_TYPES = ["organization", "person", "geo", "event"]`(`Core/Common/Constants.py:65`)이다.
이 목록은 추출 프롬프트의 `entity_type: One of the following types: [{entity_types}]`(`Core/Prompt/GraphPrompt.py:14`) 자리에 들어간다.
관계는 자유 문장 설명과 keywords이고 종류 목록이 없다.

[확인] 쓰기 직전 검증도 없다.
LLM이 낸 종류 문자열은 `clean_str`만 거쳐 그대로 저장된다(`RKGraph.py:43-48`).
구조화 출력도 쓰지 않는다. 구분자로 이은 텍스트를 정규식으로 쪼갠다(`RKGraph.py:105-123`).

[확인] 추출 뒤 종류가 실제로 쓰이는 곳은 entity_type blocking 하나다(`cluster.py:140-144`).
종류를 쓰려는 자리는 두 곳 더 있지만 공개 코드에서는 값이 비어 있다.
- 쌍 임베딩 문장 `"Entity: {node_id}. Type: {entity_type}. Description: {desc}"`(`similar_percentage.py:32-35`)는 `node_data_map`에서 값을 읽는다. 이 맵은 `cluster.py` 출력 파일로 만든다(`similar_percentage.py:160-165`, `run_all.sh:44`, `:83`). 그 파일 항목은 `node_id`, `source_text`, `similar_nodes`뿐이다(`cluster.py:185-189`). 그래서 문장은 `Type: N/A`, 빈 Description이 된다.
- type-aware neighbor 유사도(`similar_percentage.py:89-98`)도 같은 맵에서 종류를 읽어 비어 있다.
triple reflection 프롬프트에 `"Entity Type Compatibility: Verify that the relationship makes sense given the types of entities involved"`(`edge_clean.py:95`)가 있다. 그러나 프롬프트에 넣는 값은 source, destination, relationship 설명뿐이다(`edge_clean.py:32-37`, `:123`). 종류는 주지 않는다. LLM이 이름만 보고 종류를 짐작해야 한다.

[확인] 논문 Figure 3에서 entity_type blocking이 CS·Agriculture에서 가장 높았다(그림에서 읽은 값으로 약 64, 63).
논문은 이를 `"entity type is a better and more natural inductive bias for entity resolution"`(§5.3)이라 해석한다.
[추정] 사람이 정한 엔티티 종류가 합치기 범위를 좁히는 데 쓸모 있다는 간접 근거다 — 사례: Figure 3 blocking 비교 4개 데이터셋 중 2개.
LGraphRAG·HippoRAG 설정은 `enable_entity_type: False`다(`Option/Method/LGraphRAG.yaml:31`, `HippoRAG.yaml:33`). LGraphRAG는 종류를 `""`로 저장한다(`BaseGraph.py:94-95`). 그래서 entity_type blocking이 종류 하나짜리 묶음이 된다. 노드가 512개를 넘으면 그 안에서 k-means(k=√(n/10))로 다시 나눈다(`cluster.py:143-164`). `run_all.sh`의 기본 방법이 LGraphRAG라서(`run_all.sh:2`) 기본 실행에서는 종류가 아무 데도 쓰이지 않는다.
HippoRAG는 `RKGraph`가 아니라 `ERGraph`(NER 뒤 OpenIE)를 쓴다(`HippoRAG.yaml:27`). OpenIE 경로의 엔티티는 종류 없이 만들어진다(`Core/Graph/ERGraph.py:141-145`).

### B 용어집

[확인] 용어집은 없다. 정식 이름도 사람이 고르지 않는다.
논문은 정식 엔티티를 `"we use random selection for φ(·)"`(§4.1 Direct Merging)라고 쓴다.
코드는 무작위가 아니다. union-find에서 id 문자열이 작은 쪽을 root로 삼는다(`merge.py:39`, `similar_percentage.py:314-317`). 논문과 코드가 다르다.

[확인] 별칭은 남지 않는다.
기본값 `reduction_only`는 합쳐진 노드를 `G.remove_node`로 지운다(`merge.py:88`). 원래 이름은 어디에도 기록되지 않는다.
`synonym_only`는 `synonym_of` edge로 두 이름을 이어 남긴다(`merge.py:149-169`). 이것이 이 저장소에서 별칭 목록에 가장 가까운 구조다.
`reduction_synonym`도 먼저 쌍마다 `synonym_of` edge를 단다(`merge.py:96-111`). 그 뒤 합치기에서 root와 직접 synonym 쌍인 노드만 건너뛰고 나머지는 지운다(`merge.py:125-146`). 지워진 노드의 edge는 root로 옮겨진다. 옮겨진 synonym edge의 설명 문자열 `"{n1} is the synonym of {n2}"`(`merge.py:110`)에 원래 이름이 글자로만 남는다.

[확인] 추출 전에 이름 목록을 주지 않는다. 정규화는 추출 뒤 두 번이다.
첫째는 `clean_str` 문자열 정규화다(`Utils.py:45`). 이름뿐 아니라 종류와 설명도 거친다(`RKGraph.py:44-46`).
둘째는 DEG-RAG의 임베딩 합치기다. 앞 A에서 본 대로 공개 코드의 쌍 임베딩에는 사실상 이름만 들어간다.

참고: `clean_str`는 `re.sub('[^A-Za-z0-9 ]', ' ', result.lower())`로 영숫자 밖 문자를 지운다. [추정] 한국어 엔티티 이름은 빈 문자열이 되어 `if not entity_name.strip(): return None`(`RKGraph.py:40-41`)에서 버려진다 — 사례: 코드 경로 1개를 읽었다. 실행해서 확인하지는 않았다.

### C 원문 연결 범위

[확인] 엔티티는 청크 단위로 원문을 가리키고, 나온 모든 청크를 가리킨다.
추출 때 `source_id=chunk_key`로 청크 id를 단다(`RKGraph.py:47`, `:137`).
같은 이름이 여러 청크에서 나오면 `MergeEntity.merge_source_ids`가 합집합을 만든다(`BaseGraph.py:91-92`, `Core/Utils/MergeER.py:11-14`).
DEG-RAG가 노드를 합칠 때도 `source_id`를 합집합한다(`MergeSum.py:109-113`). 그래서 합친 노드는 양쪽 노드가 나온 모든 청크를 가리킨다.

[확인] 문서·문장 단위 연결은 없다. 문장 offset도 저장하지 않는다.
사용자 실험의 공식 변환 코드처럼 "처음 본 청크에만" 거는 문제는 이 코드에 없다.

### D 새/기존 연결

[확인] 증분 추가 절차는 없다. 전부 일괄 처리다.
`build_graph`는 저장된 그래프가 있으면 불러오고, 없거나 `force`면 지우고 처음부터 다시 만든다(`BaseGraph.py:43-48`).
DEG-RAG 후처리도 그래프 전체를 다시 묶고 쌍을 다시 고른다(`cluster.py`, `similar_percentage.py`). `run_all.sh`는 결과 파일이 있으면 단계를 건너뛴다(`scripts/run_all.sh:30`, `:47`, `:71`).

[확인] 새 문서와 기존 엔티티가 이어지는 경로는 둘이다.
1. 추출 직후: `clean_str` 뒤 문자열이 같으면 한 노드가 된다(`BaseGraph.py:230-248`).
2. 후처리: 같은 block 안에서 cosine 순위가 예산 안에 들면 합쳐진다(`similar_percentage.py:291-320`). block은 설명 임베딩 k-means로 나누지만(`cluster.py:105-128`), block 안 쌍의 cosine은 사실상 이름만 임베딩해 구한다(#A). 별칭 대조는 없다.

[추정] 새 문서를 넣으면 전체 순위가 바뀌어 기존 합치기 결과도 달라질 수 있다 — 사례: 예산이 전체 노드 수 비율이고(`similar_percentage.py:155`) 쌍 순위가 전역 정렬이다(`:291`). 실행해서 확인하지는 않았다.

### E 새 용어

[확인] 해당 없음. 용어집·schema 밖이라는 개념이 없다. LLM이 낸 모든 이름이 노드가 된다.
[확인] 4개 종류 밖의 종류 문자열도 거르지 않는다(`RKGraph.py:43-48`). 사람 승인 대기열도 없다.

### F 범용어 허브

[확인] stoplist, 빈도·차수 기준, 묶음 크기 상한은 없다.
찾아본 곳은 `denoise_kg/*.py` 전체와 `Core/Graph/BaseGraph.py`, `RKGraph.py`다. `degree`, `frequency`, `stop` 같은 장치를 찾지 못했다.

[확인] 오히려 union-find가 사슬처럼 묶는다.
A~B, B~C가 각각 예산 안에 들면 A~C가 멀어도 한 노드가 된다(`similar_percentage.py:296-320`, `merge.py:28-42`). 묶음 크기 상한이 없다.
논문 B.3 case study가 그 결과를 보여 준다: `"K-means Algorithm being merged into Clustering models, and Naive Bayes Model and Support Vector Machine Model being merged into Decision Tree"`. 저자들은 이것을 `"generally reasonable"`이라 불렀다.
[추정] 사용자 실험의 범용어 허브와 같은 현상이다. 하위 개념이 상위 개념 노드로 빨려 들어가 그 노드가 허브가 된다 — 사례: B.3의 합치기 예 2건.

[확인] 허브를 간접으로 누르는 장치는 둘이다.
1. entity_type blocking: 다른 종류끼리는 합치지 않는다(`cluster.py:140-164`).
2. triple reflection: 프롬프트가 `"Specificity: Determine if the relationship provides clear, specific information … rather than being vague or overly general"`(`edge_clean.py:93`)를 요구한다. 범용 관계 edge는 점수가 낮게 나올 수 있다.
다만 `run_all.sh`의 기본값은 `edge_threshold=0.00`이다(`scripts/run_all.sh:5`). 점수가 0 미만인 edge만 지우므로 사실상 끈 상태다. 논문 기본값은 δ_TR=0.2다(§5.1).
참고: 임계값을 켜도 빠지는 edge가 있다. triple reflection은 합치기 전 그래프의 (이름, 이름) 쌍으로 점수를 매긴다(`run_all.sh:95`, `edge_clean.py:32-37`). 삭제는 합친 뒤 그래프에서 `G.has_edge(u, v)`로 찾는다(`merge.py:284-290`). 합쳐져 사라진 노드에 붙어 있던 edge는 root로 옮겨져 이 검사에 걸리지 않는다. 또 `run_all.sh`는 점수 파일 이름에 `edge_threshold` 문자열을 그대로 쓰고(`:91`), `merge.py`는 `{:.2f}` 형식으로 찾는다(`:274`). `edge_threshold=0.2`로 주면 파일을 못 찾는다. 코드를 읽어서 본 것이고 실행하지는 않았다.

### G 엔티티·이벤트

[확인] `event`는 엔티티 종류 4개 중 하나일 뿐이다(`Constants.py:65`). 시간 속성·시간축은 없다.
[확인] `edge_clean.py`에는 `"Temporary event"`를 낮게 매기는 `PROMPT_COMMONSENSE`(`:45-82`)가 있다. 실제로 쓰는 것은 `PROMPT_REASON`이다(`:123`).

### H 근거 수치

[확인] 지표는 LLM judge 쌍대 승률뿐이다.
judge는 Comprehensiveness, Diversity, Empowerment, Overall 네 기준으로 두 답 중 하나를 고른다. 순서를 바꿔 두 번 돌린다(C.5). 데이터는 UltraDomain 4개, 질문은 각 125개다(표 2).
retrieval 지표(recall@k), 정답 대조, 합치기 정밀도 같은 측정은 없다.

[확인] 주요 수치는 다음과 같다. Figure 3~5의 값은 그림 SVG를 렌더링해 읽었다.

| 실험 | 결과 | 출처 |
|---|---|---|
| 본 결과(40% 축소, δ_TR 0.2) | LightRAG Agriculture Overall 42.40 → 57.60. HippoRAG Legal 50.00 vs 50.00 | 표 1 |
| 축소 비율 sweep | CS: 0.3에서 64.3 → 0.7에서 48.8 → 0.8에서 39.6. Agriculture: 0.2에서 64.9 → 0.6에서 46.3. Legal: 0.5에서 53.5 → 0.8에서 40.4. Mix: 0.5에서 60.7 → 0.8에서 41.7 | Figure 4 |
| ablation | 전체 방법이 entity resolution 없음·triple reflection 없음보다 높다. 무작위 합치기는 47.6~49.6 정도 | Figure 5 |
| 합치기 방식 | direct merging이 CS·Agriculture·Mix에서 높다. Legal은 synonym linking이 높다(약 55 vs 51.6). merging + synonym linking은 CS·Legal·Agriculture에서 가장 낮다 | Figure 3 |
| token | 논문은 원래 KG와 큰 차이가 없다고 쓴다. 숫자로는 20~40%에서 prompt token이 오르고 60~80%에서 내린다. 80%에서는 CS 1,084,623 → 779,191, Agriculture 1,273,710 → 911,124로 약 28% 줄었다 | 표 4, B.2 |

[추정] Figure 3~5는 LightRAG 결과다 — 사례: Figure 4의 0.4 값 4개(CS 59.6, Legal 51.3, Agriculture 57.6, Mix 55.5)가 표 1 LightRAG Clean 네 기준 평균과 모두 같다. Figure 5의 Full Method 막대와 Figure 3의 Semantic·Ego node·Direct Merging 막대도 같은 높이로 보인다. 논문 본문은 어느 방법인지 밝히지 않는다.

[확인] 이 수치를 읽을 때 걸리는 한계가 있다.
- δ_ER을 보고하지 않았다. 코드에도 그 값이 없다. 합치기는 예산 `target_reduction_percent`로 멈춘다(`similar_percentage.py:155`, `:306-308`).
- 무작위로 노드 40%를 합쳐도 승률이 47.6~49.6이다. [추정] judge 승률이 KG 구조 변화에 둔하다 — 사례: Figure 5의 무작위 합치기 막대 4개가 모두 50 근처다.
- 표 1 Legal LightRAG의 Orig 열(43.60, 41.60, 42.00, 42.40)이 Agriculture Orig 열과 같다. Clean 열과 더하면 100이 안 된다(43.60 + 50.80 = 94.40). 표 3 Qwen Legal 값은 Agriculture 값과 같다. 표에 옮겨 적은 오류가 있다.
- 공개 코드 그대로는 돌지 않는다. `run_all.sh:74`가 부르는 `denoise_kg/similar_test.py`가 저장소에 없다. 있는 것은 `similar_percentage.py`다.
- 논문과 코드가 다른 곳이 더 있다. semantic blocking k는 논문이 `k=√(|E|/10)`(§4.1), 스크립트는 `k=10`(`run_all.sh:38`)이다. structural blocking은 논문이 이웃 집합, 코드가 연결 요소(`cluster.py:165-177`)다. 설명 요약 기준은 논문이 4,000 token(C.3), 코드가 2,000 token(`Core/Utils/MergeSum.py:46`)이다. 쌍 임베딩에 종류·설명이 빠지는 문제(#A)도 논문에는 드러나지 않는다.
- 저자 스스로 `"Triple reflection depends on LLM prompting and the LLM-as-judge setup, which can introduce calibration bias"`와 `"graphs with only short names without rich descriptions limit resolution quality"`를 한계로 적었다(§6).

## 가져올 것

| 가져올 것 | 왜 | 조건 |
|---|---|---|
| 합치기를 예산(축소 비율)이 아니라 sweep 곡선으로 고른다 | Figure 4는 데이터셋마다 봉우리가 다르다(CS 0.3, Legal 0.5, Agriculture 0.2, Mix 0.5). 고정 40%는 네 데이터셋 어디에서도 봉우리가 아니다 | 사용자 실험의 연결 재현율·정밀도를 축으로 같은 sweep을 그린다 |
| 엔티티 종류를 합치기 범위(blocking)로 쓴다 | 사람이 정한 종류 10개가 있으니 다른 종류끼리는 합치지 않게 할 수 있다. Figure 3에서 type blocking이 4개 중 2개 데이터셋에서 가장 높다 | 범용어가 같은 종류 안에 있으면 못 막는다 |
| 합치되 원래 이름을 별칭으로 남긴다 | `reduction_only`는 이름을 지워 되돌릴 수 없다. `synonym_only`의 `synonym_of` edge처럼 남기면 사람이 검토하고 되돌릴 수 있다 | 논문은 synonym 방식이 대체로 낮다고 보고했다. 별칭은 검색 경로가 아니라 기록으로만 둔다 |
| 사슬 합치기를 막는다 | union-find의 전이 합치기가 상위 개념 허브를 만든다(B.3 사례) | 묶음 크기 상한, 또는 묶음 안 모든 쌍이 임계값을 넘어야 합치는 complete-link로 바꾼다. 이 저장소에는 없는 장치다 |
| edge 점수에 "범용성" 기준을 둔다 | `PROMPT_REASON`의 Specificity 항목이 범용 관계 edge를 걸러 낼 수 있다 | 임계값을 실제로 켠다(논문 0.2). 효과는 judge 승률로만 쟀다 |
| `source_id` 합집합 | 합친 노드가 양쪽 청크를 모두 가리킨다. 사용자가 고친 "모든 청크로 링크" 방향과 같다 | 이미 사용자 실험에 있다 |

라이선스: 코드 저장소에 LICENSE 파일이 없다. GitHub API도 license를 null로 돌려준다. fork 원본 DIGIMON(JayLZhou/GraphRAG)도 GitHub에서 라이선스가 잡히지 않는다. 코드를 복사하지 말고 설계만 가져온다. 논문은 CC BY 4.0이다.

## 출처

| 항목 | 값 |
|---|---|
| 논문 | https://arxiv.org/abs/2510.14271 (v1, 2025-10-16). HTML 본문 https://arxiv.org/html/2510.14271 을 읽었다. Figure 3~5는 HTML의 SVG를 렌더링해 읽었다 |
| 코드 | https://github.com/157114/Denoise |
| commit | `802a1bbdd4b8f7d109ad43b9abfe03bc08b559ac` (2025-11-10) |
| 로컬 사본 | `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/157114_Denoise` |
| 코드 라이선스 | 없음 (LICENSE 파일 없음, GitHub API `license: null`) |
| 논문 라이선스 | CC BY 4.0 (arXiv HTML 표기) |
| fork 원본 | DIGIMON https://github.com/JayLZhou/GraphRAG |
| 실행 여부 | 코드를 실행하지 않았다. 읽기만 했다 |

## 검증 기록

검증 날짜는 2026-10-11이다. 로컬 사본(commit `802a1bb`)의 인용 파일·줄을 다시 열었다. 논문은 arXiv HTML(v1)과 PDF(v1)를 다시 받았다. Figure 3·5는 SVG를 PNG로 렌더링해 읽었다. Figure 4 수치는 PDF 본문에서 데이터 라벨 텍스트로 뽑았다. 코드는 실행하지 않았다.

### 그대로 맞은 것

| 주장 | 다시 본 곳 |
|---|---|
| 엔티티 종류 4개 상수가 추출 프롬프트에 들어간다. 사람이 정한 schema·용어집은 없다 | `Constants.py:65`, `RKGraph.py:147`, `GraphPrompt.py:14` |
| 구조화 출력 없이 구분자 텍스트를 정규식으로 쪼갠다. 종류 문자열을 거르지 않는다 | `RKGraph.py:33-50`, `:105-123` |
| `source_id`는 청크 id이고, 같은 이름·병합 노드에서 합집합한다 | `RKGraph.py:47`, `:137`, `BaseGraph.py:91-92`, `MergeER.py:11-14`, `MergeSum.py:109-113` |
| 증분 추가 없이 불러오거나 처음부터 다시 만든다 | `BaseGraph.py:43-48` |
| 예산으로 멈추는 전역 정렬 + union-find, root는 id 문자열이 작은 쪽 | `similar_percentage.py:155`, `:291-320`, `merge.py:28-42` |
| 논문 "random selection" | §4.1 Direct Merging |
| `reduction_only`가 기본이고 합쳐진 노드를 지운다 | `run_all.sh:12`, `merge.py:88` |
| `edge_threshold` 기본 0.00, 논문 δ_TR 0.2 | `run_all.sh:5`, §5.1 |
| `PROMPT_COMMONSENSE`는 정의만 있고 쓰이지 않는다 | `edge_clean.py:45`가 저장소 안 유일한 등장, `:123`은 `PROMPT_REASON` |
| `similar_test.py`가 저장소에 없다 | `run_all.sh:74`, `denoise_kg/` 목록 |
| 표 1 Legal LightRAG Orig 열 = Agriculture Orig 열, 43.60 + 50.80 = 94.40. 표 3 Qwen Legal = Agriculture | 표 1, 표 3 |
| Figure 4 수치(CS 0.3에서 64.3, 0.8에서 39.6 등)와 0.4 값 = 표 1 LightRAG Clean 평균 | PDF p.9 데이터 라벨 |
| Figure 3 type blocking이 CS·Agriculture에서 가장 높고, Legal·Mix는 Structural이 가장 높다 | Figure 3 렌더링 |
| Figure 5 무작위 합치기 47.6~49.6 | Figure 5 렌더링 |
| B.3 인용, §5.3 "inductive bias", §6 한계 인용 | 논문 해당 절 |
| 코드 LICENSE 없음, DIGIMON도 license null. 논문 CC BY 4.0 | `gh api repos/157114/Denoise`, `gh api repos/JayLZhou/GraphRAG`, arXiv HTML 표기 |

### 고친 것

| 원래 주장 | 실제 | 근거 |
|---|---|---|
| 종류는 triple reflection 프롬프트에서도 쓰인다 | 프롬프트에 종류 값을 넣지 않는다. source·destination·relationship 설명만 넣는다 | `edge_clean.py:32-37`, `:123` |
| 쌍 고르기는 `Entity/Type/Description` 문장을 임베딩한다 | 그 문장의 type·desc를 읽는 맵이 `cluster.py` 출력이라 두 필드가 없다. 실제로는 `Type: N/A`, 빈 Description이다. type-aware neighbor 유사도도 종류가 비어 있다 | `similar_percentage.py:32-35`, `:89-98`, `:160-165`, `cluster.py:185-189`, `run_all.sh:44`, `:83` |
| LGraphRAG·HippoRAG에서는 blocking이 한 덩어리가 된다 | 종류 하나짜리 묶음이 되고, 512개를 넘으면 그 안에서 k-means로 나뉜다. HippoRAG는 `ERGraph`를 쓴다. 기본 실행(LGraphRAG)에서는 종류가 아무 데도 쓰이지 않는다 | `cluster.py:143-164`, `HippoRAG.yaml:27`, `run_all.sh:2`, `BaseGraph.py:94-95` |
| 별칭은 `synonym_only`의 edge로만 남는다 | `reduction_synonym`도 `synonym_of` edge를 단다 | `merge.py:96-111` |
| δ_ER을 보고하지 않은 것은 코드에 없기 때문이다 | 인과는 확인할 수 없다. 둘 다 사실이라는 것까지만 남겼다 | §4.1, `similar_percentage.py` |
| Figure 3~5는 LightRAG 결과다([확인]) | 수치 일치에서 끌어낸 추정이라 [추정]으로 바꿨다 | 표 1, Figure 4 |
| token 소비는 크게 달라지지 않는다 | 논문 주장은 그렇다. 숫자로는 80%에서 CS·Agriculture prompt token이 약 28% 줄었다 | 표 4 |
| 고정 40%는 CS·Agriculture에서 최적이 아니다 | 네 데이터셋 모두에서 봉우리가 아니다(CS 0.3, Legal 0.5, Agriculture 0.2, Mix 0.5) | Figure 4 |

### 덧붙인 것

- 설명 요약 기준이 논문 4,000 token(C.3), 코드 2,000 token(`MergeSum.py:46`)으로 다르다.
- triple reflection 점수는 합치기 전 이름 쌍으로 매기고, 삭제는 합친 뒤 그래프에서 찾는다. 합쳐진 노드에 붙은 edge는 삭제를 비켜 간다(`run_all.sh:95`, `merge.py:284-290`). 점수 파일 이름 형식도 `run_all.sh:91`과 `merge.py:274`가 다르다.
- `clean_str`는 이름뿐 아니라 종류·설명에도 적용된다(`RKGraph.py:44-46`).

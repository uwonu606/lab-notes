# Wikontic은 Wikidata schema와 자라는 alias 표로 엔티티를 묶지만, 원문 연결은 사실(triplet) 단위로 처음 본 곳만 남고 허브 대책은 없다

Wikontic은 텍스트에서 triplet을 뽑아 Wikidata 온톨로지로 검증하는 KG 구축 파이프라인이다. 논문은 EACL 2026(arXiv 2512.00590)이고 코드는 `screemix/Wikontic`(MIT)이다. schema는 사용자가 쓰지도, LLM이 만들지도 않는다. Wikidata 편집자들이 property에 달아 둔 type 제약을 스크립트가 SPARQL로 거둬 entity type 3,726개와 property 2,492개의 고정 schema로 만든다(기본 로드 경로 `ontology_mappings_en_en/`). 용어집 자리에는 추출하면서 자라는 `entity_aliases` 표(정식 label + 표면형 alias)가 있다.

사용자 목표에 주는 답은 셋이다.
- [확인] "새 데이터와 기존 데이터의 연결고리"를 만드는 장치는 있다. 새 mention을 같은 type 계열의 기존 alias top-10과 임베딩으로 대조한다. 그다음 LLM이 그중 하나를 고르거나 "None"을 답한다(`structured_inference_with_db.py:318-342`).
- [확인] 원문 연결은 사용자가 겪은 문제와 같은 꼴이다. 같은 triplet이 다른 문단에서 다시 나오면 Mongo backend는 처음 것만 남긴다(`mongo_backend.py:269-270`, `$setOnInsert`). 엔티티 자체는 원문 id를 갖지 않는다.
- [확인] 범용어 허브를 막는 장치는 코드에 없다. stoplist·빈도 기준·차수 제한을 찾지 못했다.

## 한 바퀴 흐름

입력은 `{sample_id: [문단, 문단, ...]}` JSON이다. 문단마다 `source_text_id`가 리스트 index로 붙는다(`inference_and_eval/dataset_inference.py:376-403`). 이미 그 `(sample_id, source_text_id)`로 저장된 triplet이 있으면 건너뛴다.

| 단계 | 하는 일 | 코드 |
|---|---|---|
| 1 추출 | LLM이 문단 하나에서 `subject, relation, object, qualifiers, subject_type, object_type`을 JSON으로 낸다. 자유 텍스트 이름이다. | `openai_utils.py:187-211`, `prompts/triplet_extraction/propmt_1_types_qualifiers.txt` |
| 2 type 정렬 | 뽑힌 type 이름을 Wikidata type alias 인덱스에서 top-10으로 찾는다. 그대로 있으면 통과하고, 없으면 LLM이 후보 중에서 고른다. | `structured_inference_with_db.py:41-130` |
| 3 relation 정렬 | 고른 두 type 사이에 Wikidata 제약상 허용되는 property만 모은다. 원래 relation과 임베딩 유사도로 순위를 매기고, 목록에 없으면 LLM이 고른다. 역방향도 후보다. | `structured_inference_with_db.py:166-243`, `structured_aligner.py:227-281` |
| 4 이름 정규화 | subject·object 이름을 기존 KG alias와 대조해 정식 label로 바꾸고, 원래 표기를 alias로 저장한다. | `structured_inference_with_db.py:293-352` |
| 5 검증 | type·relation이 온톨로지에 있고 domain·range 제약을 만족하는지 본다. 통과하면 `triplets`, 아니면 `ontology_filtered_triplets`로 간다. | `structured_inference_with_db.py:245-291, 513-555` |
| 6 저장 | 네 컬렉션(`initial_triplets`, `triplets`, `filtered_triplets`, `ontology_filtered_triplets`)에 upsert한다. | `structured_inference_with_db.py:580-615` |

결과물은 wiki 페이지가 아니라 triplet 컬렉션과 alias 컬렉션이다. 페이지 종류 같은 llm-wiki 개념은 없다. QA는 질문 엔티티에서 1-hop 이웃을 최대 5번 넓혀 triplet만 LLM에 준다(`base_inference_with_db.py:206-227`).

## 축별 분석

### A schema

[확인] schema는 추출 전에 고정되고, LLM이 만들지 않는다. `preprocessing/constraint-preprocessing_batch.py`가 Wikidata SPARQL로 property의 subject type constraint(Q21503250)와 value-type constraint(Q21510865)를 받는다(`:274-294`). type 목록은 이 제약에 등장한 type과 그 P31·P279 조상이다(`:383`, `:394`). 즉 내용은 Wikidata 편집자가 손으로 쓴 제약이다. 어느 type·property를 둘지는 사용자가 고르지 않고 스크립트가 정한다. 논문 §2.1은 "Properties required solely for linking external data ... were excluded, leaving 2,464 factual properties"라고 적는다.

| 파일 (`src/wikontic/utils/ontology_mappings_en_en/`) | 내용 | 항목 수 |
|---|---|---|
| `entity_type2label.json`, `entity_type2aliases.json` | type id → label, alias | 3,726 |
| `entity_type2hierarchy.json` | type id → 조상 type id 전체 | 3,726 |
| `prop2label.json`, `prop2aliases.json` | property id → label, alias | 2,492 |
| `prop2constraints.json` | property id → subject/value type 제약 | 2,492 |
| `subj_constraint2prop.json`, `obj_constraint2prop.json` | type id → 그 type을 받는 property | 2,405 / 2,286 |

[확인] 로더는 `ontology_mappings_{language}_{fallback}` 디렉터리를 읽는다(`language_config.py:43-48`, `create_wikidata_ontology_db.py:294-302`). README 표도 DB 구축용 매핑을 `ontology_mappings_en_en/`이라고 적는다(`README.md:340`). 확장자 없는 `ontology_mappings/`(type 3,476, property 2,445)는 내용이 다르다. 로더가 요구하는 `subj_constraint2prop.json`·`obj_constraint2prop.json`도 없어 그대로는 로드되지 않는다(`create_wikidata_ontology_db.py:372-376`).

[확인] 강제는 세 겹이다. 프롬프트는 type 목록을 주지 않고 "Wikidata-style"이라고만 말한다. 대신 추출 뒤에 임베딩 후보 + LLM 선택으로 schema 안 이름으로 끌어온다. 마지막에 `_validate_backbone`이 계층을 펼쳐 domain·range를 검사한다(`structured_inference_with_db.py:273-291`).

[확인] 구조화 출력(`response_format`, JSON schema)은 쓰지 않는다. `temperature=0`으로 부르고 정규식으로 JSON을 꺼낸다(`openai_utils.py:127-184`). LLM이 후보 밖 이름을 내도 예외를 던지지 않는다. `# do not raise an exception - save triplet in ontology filtered collection`(`openai_utils.py:292`, `:352`).

[확인] 다른 schema로 바꾸는 입구는 있다. `create_wikidata_ontology_db.py`의 `--mappings_dir`가 같은 형식의 JSON 디렉터리를 받는다(`:372-393`, `:498-503`). 논문 Limitations도 "can be adapted to any domain and ontology with a matching format"이라고 적는다. [추정] 사람이 손으로 쓴 작은 schema를 이 형식으로 넣을 수 있다 — 근거는 로더가 파일 형식만 요구한다는 점 하나다. 해 본 사례는 저장소에 없다.

### B 용어집

[확인] 엔티티 용어집은 `entity_aliases` 컬렉션이다. 문서 한 줄은 `{label, entity_type, alias, sample_id, alias_text_embedding}`이다(`structured_aligner.py:387-405`). label이 정식 이름이고 alias가 실제로 본 표기다. 같은 label에 alias 줄이 여러 개 붙는다.

[확인] 쓰는 주체는 파이프라인뿐이다. 사람이 미리 채우는 입구나 편집 화면은 찾지 못했다(`approv|manual|curat` grep 결과 없음). 처음 보는 이름은 자기 자신을 label이자 alias로 해서 들어간다(`structured_inference_with_db.py:340-350`).

[확인] 추출 전 프롬프트에는 용어집을 넣지 않는다. 추출 뒤 정규화만 한다. 정규화 프롬프트는 "If an exact or semantically appropriate match ... return the corresponding name exactly as it appears in the list" / "If no suitable match for object exists, return the string \"None\""이다(`prompts/name_refinement/rank_object_names.txt:15-17`).

[확인] type과 relation에도 Wikidata label + alias 표가 있다. 이 표는 고정이고 추출 중에 자라지 않는다(`entity_type_aliases`, `property_aliases` 컬렉션, `structured_aligner.py:47-53`). ontology 없는 dynamic 모드에서는 relation alias 표도 자란다(`dynamic_aligner.py:187-200`).

### C 원문 연결 범위

[확인] 원문 단위는 문단이다. 데이터셋 리스트의 한 원소가 `source_text_id` 하나가 된다(`dataset_inference.py:380-403`). 문장 단위 offset은 없다.

[확인] 링크를 갖는 것은 triplet이다. 엔티티 alias 문서에는 `source_text_id` 필드가 없다(`structured_aligner.py:395-403`). 그래서 엔티티 → 원문은 그 엔티티가 들어간 triplet들의 `source_text_id`를 모아야 나온다.

[확인] 같은 triplet이 여러 문단에 나오면 하나만 남는다. 중복 판정 키는 `subject, relation, object, subject_type, object_type, sample_id`다(`structured_aligner.py:414-422`).

| backend | 동작 | 근거 |
|---|---|---|
| MongoDB (논문 설정) | 처음 본 문단만 남는다 | `mongo_backend.py:269-270` "Insert only when unique_fields are new; never overwrite existing docs." |
| Qdrant | 키로 만든 결정적 id에 덮어써서 마지막 문단만 남는다 | `qdrant_backend.py:320-328` |

[추정] 사용자 실험의 "처음 본 청크에만 링크" 문제가 Wikontic에도 사실 단위로 있다. 근거는 위 두 코드 경로다. 다른 사실(다른 relation·object)로 나온 문단은 각자 triplet을 가지므로 엔티티 단위로는 여러 문단에 이어진다. 같은 사실을 되풀이한 문단만 끊긴다.

### D 새/기존 연결

[확인] 새 mention 하나를 기존 엔티티에 붙이는 절차는 다음과 같다(`structured_inference_with_db.py:293-352`, `structured_aligner.py:337-385`).

1. 이름을 `unidecode`로 음역한다(영어 모드).
2. object의 type 계열에 point in time(Q186408)이나 quantity(Q309314)가 있으면 대조 없이 그대로 쓴다.
3. 그 type과 조상 type 라벨로 필터하고, 같은 `sample_id` 안에서, alias 임베딩 top-10을 벡터 검색한다(Contriever).
4. 결과 alias 중 표기가 정확히 같으면 그 label을 쓴다. LLM은 부르지 않는다.
5. 정확히 같은 것이 없으면 후보 label 목록을 문단·triplet과 함께 LLM에 준다. LLM이 하나를 고르거나 "None"을 낸다.
6. 결과를 label로, 원래 표기를 alias로 `entity_aliases`에 upsert한다.

[확인] 유사도 문턱값은 없다. 후보가 하나라도 있으면 LLM이 판정한다. 그래서 정확 일치가 아닌 mention마다 LLM 호출이 하나씩 든다.

[확인] type 필터는 mention의 type과 그 조상 type 전부다(`structured_aligner.py:339-353`). 조상에는 `entity`처럼 아주 넓은 type이 들어간다. `entity`는 3,726개 type 중 3,715개의 조상이다(`entity_type2hierarchy.json`을 세었다). 그래서 넓은 type으로 저장된 엔티티는 거의 모든 mention의 후보가 된다. 방향은 한쪽이다. 하위 type으로 저장된 엔티티는 상위 type mention의 후보가 되지 않는다.

[확인] 대조 범위는 `sample_id`로 갈린다. `sample_id`가 있으면 그 샘플 안에서만 찾는다(`structured_aligner.py:363-371`). 논문 실험은 MuSiQue·HotpotQA 질문마다 따로 그래프를 만든다. `sample_id`를 비우면 `"all"`로 저장되고 필터 없이 전체에서 찾는다.

[확인] 이름 정규화는 type이 schema에 맞았을 때만 돈다(`structured_inference_with_db.py:472-482`). type이 후보 밖이면 이름은 원문 그대로 남고 alias 표에도 안 들어간다. 논문 §2.2는 misaligned triplet이 "remain linked to the main KG through the entity name refinement step"이라고 적는다. 코드상으로는 엔티티별로 갈린다. type이 schema에 맞은 쪽 엔티티는 정규화되어 KG에 이어진다. type이 어긋난 쪽 엔티티는 이어지지 않는다(`:472-482`가 subject와 object를 따로 검사한다).

[확인] 병렬 변형(`structured_inference_with_db_doc_parallelized.py:1-60`)은 read-then-write 경쟁을 막으려고 type 계열이 겹치는 엔티티끼리 묶어 순서대로 처리한다. 주석은 동시에 돌리면 "silently minting two canonical entities that should have been one"이 된다고 적는다.

### E 새 용어

| 무엇이 schema·용어집 밖인가 | 처리 | 근거 |
|---|---|---|
| 처음 보는 엔티티 이름 | 새 label로 자동 추가한다. 사람 승인은 없다. | `structured_inference_with_db.py:340-350` |
| schema에 없는 type·relation, domain·range 위반 | 버리지 않고 `ontology_filtered_triplets`에 `exception_text`와 함께 남긴다 | `structured_inference_with_db.py:554-555` |
| 처리 중 예외(JSON 깨짐 등) | `filtered_triplets`에 남긴다 | `structured_inference_with_db.py:557-566` |
| Wikidata에 없는 새 type·property | schema에 추가하는 경로가 없다 | `create_wikidata_ontology_db.py`만 schema를 쓴다 |

[확인] 남긴 misaligned triplet은 QA에서 기본으로 안 쓴다. `use_filtered_triplets=False`가 함수 기본값이고(`base_inference_with_db.py:126`), 평가 스크립트 기본값도 같다(`inference_and_eval/qa_eval_musique.py:113`, `qa_eval_hotpot.py:118`). 논문은 보관 이유를 "provides interpretable cues for identifying or revising schema-inconsistent facts"라고 적는다(§2.2). 검토 대기열 UI는 없다.

### F 범용어 허브

[확인] 장치가 없다. `stop`, `frequen`, `degree`, `hub`, `threshold`, `min_count`로 `src/`를 찾았지만 해당 로직은 없었다. QA 확장도 이웃 수 제한 없이 5 hop을 넓힌다(`base_inference_with_db.py:206-227`).

[확인] 허브를 간접으로 줄이는 구조는 둘 있다. 엔티티 대조 후보를 mention의 type과 조상 type으로 저장된 것으로 좁힌다(`structured_aligner.py:339-371`). 다만 조상에 `entity`·`abstract entity` 같은 넓은 type이 들어가므로, 넓은 type으로 저장된 엔티티와는 다른 계열 mention도 합쳐질 수 있다. 날짜·수량 object는 정규화하지 않는다(`structured_inference_with_db.py:313-315`).

[추정] 이 둘로는 사용자 실험의 허브("KG", "LLM" 같은 개념어)를 못 막는다. 근거는 두 가지다. 같은 type 안에서 같은 개념어가 하나로 모이는 것이 바로 정규화의 목적이다. 그리고 그렇게 모인 노드를 걸러내는 단계가 없다. Wikontic 실험 데이터(MuSiQue·HotpotQA 위키 문단)는 개념어보다 고유명사가 많아 이 문제가 드러나지 않았을 수 있다. 확인하려면 덤프한 KG에서 차수 분포를 봐야 한다.

### G 엔티티·이벤트

[확인] 별도 이벤트 레코드는 없다. 이벤트는 Wikidata type(`event` Q1656682, `battle` Q178561 등)을 가진 엔티티로 들어올 수 있다. 시간은 두 길로 들어간다.
- object 자리의 날짜: "date of birth → 7 November 1867" 같은 triplet이다.
- qualifier: `{"relation": "point in time", "object": "1903"}`처럼 triplet에 붙는다(추출 프롬프트 예시 `:76`).

[확인] qualifier는 정렬도 검증도 안 한다. 추출 결과를 그대로 복사한다(`structured_inference_with_db.py:471`). `rank_object_qualifiers.txt` 프롬프트는 로드만 되고 부르는 코드가 없다.

[확인] qualifier는 중복 판정 키에 없다(`structured_aligner.py:414-422`). 그래서 Mongo backend에서는 같은 (subject, relation, object)가 다른 시점 qualifier로 다시 나오면 뒤의 것이 버려진다. 예: 같은 직책을 두 번 맡은 경우.

[확인] 논문은 qualifier 효과를 크게 잰다. Table 6에서 qualifier를 빼면 MuSiQue EM이 42.6에서 23.9로 떨어진다. 본문 §3.6은 같은 차이를 "–15.9 EM, –15.7 F1"로 적어 표의 차이(−18.7, −16.5)와 맞지 않는다.

### H 근거 수치

| 측정 | 결과 | 출처 |
|---|---|---|
| MINE-1 정보 보존 | Wikontic 84%(gpt-4o)·86%(gpt-4.1-mini), KGGen 최고 73%(Claude Sonnet 3.5)·66%(GPT-4o), GraphRAG 48% | 논문 §3.1 Table 1 |
| 그래프 크기(MuSiQue 80샘플 평균) | 엔티티 248.8 / relation 104.8. ontology·정규화 둘 다 빼면 273.0 / 140.9 | §3.2 Table 2 |
| 엔티티당 relation 다양성 | relation당 고유 엔티티 2.5. 둘 다 빼면 2.3 | Table 2 |
| 온톨로지 부합률 | 96.5%. ontology 단계를 빼면 15.2% | §3.3 Table 3 |
| 정답 엔티티 포함률 | 96.2%. ontology만 빼면 97.5% | Table 3 |
| QA 소거 실험(MuSiQue EM/F1) | 전체 42.6/55.9, alias 없이 36.5/50.0, ontology 없이 36.3/48.8, ontology·정규화 없이 27.0/36.9 | §3.6 Table 6 |
| 구축 비용 | 문단당 prompt 12,687 / completion 881 토큰 | §3.4 Table 5 |

[확인] 엔티티 병합의 정밀도(잘못 합친 비율)나 문서 간 연결 재현율은 재지 않았다. Table 2는 엔티티 수가 줄었다는 것만 보인다. 사용자 실험의 연결 정밀도 0.37 문제와 맞댈 수치는 없다.

[확인] schema 단계는 정답 포함률을 조금 깎는다(97.5% → 96.2%). 논문은 이를 "avoiding mismatches between Wikidata and MuSiQue entities"로 설명한다.

## 가져올 것

| 문제 | 가져올 것 | 근거 | 포기하는 것 |
|---|---|---|---|
| 별칭이 사람 손으로만 늘어난다 | alias 표를 추출 중에 자라게 한다. 정식 label 옆에 본 표기와 임베딩을 함께 저장한다. | [확인] `structured_aligner.py:387-405`. 논문 Table 6에서 alias를 빼면 EM −6.1 | 사람이 정한 용어집과 자동 alias가 섞인다. 출처 필드(사람/LLM)를 따로 두어야 한다. |
| 범용어가 엉뚱하게 합쳐진다 | 엔티티 대조를 type 계열 안으로 좁힌다 | [확인] `structured_aligner.py:339-371` | type 오분류가 나면 같은 엔티티가 영영 안 합쳐진다. Wikontic처럼 조상 type을 모두 열면 `entity` 같은 뿌리 type 때문에 좁히는 효과가 줄어든다. 뿌리 근처 type은 필터에서 빼야 한다. |
| 정확 일치에도 LLM을 부른다 | alias 정확 일치는 LLM 없이 바로 붙이고, 나머지만 LLM 판정 | [확인] `structured_inference_with_db.py:323-325` | 없음 |
| schema 밖 사실이 사라진다 | 버리지 말고 사유(`exception_text`)와 함께 별도 컬렉션에 남긴다. 사람 검토 대기열의 입력으로 쓴다. | [확인] `:554-555` | 저장 공간. 대기열 UI는 직접 만들어야 한다. |
| 시간 정보가 사라진다 | 시점을 triplet qualifier로 붙인다 | [확인] 논문 Table 6 qualifier 제거 시 EM −18.7 | qualifier도 정규화·중복 키에 넣어야 한다. Wikontic은 안 했다. |

가져오면 안 되는 것도 있다.
- 필수: 중복 판정을 `$setOnInsert`로 하면 사용자가 겪은 "처음 본 곳만 링크" 문제가 그대로 돌아온다. 근거는 `mongo_backend.py:269-270`이다. `source_text_id`를 리스트로 두고 `$addToSet`으로 쌓아야 모든 곳에 링크가 걸린다.
- 제안: 허브 대책은 Wikontic에서 얻을 것이 없다. 차수 상한이나 type별 stoplist는 따로 설계해야 한다.

라이선스는 MIT다. 코드를 옮길 때 저작권 표시만 남기면 된다. LICENSE 파일의 저작권 줄은 "Copyright (c) 2018 The Python Packaging Authority"로 템플릿이 그대로 남아 있다. `pyproject.toml`은 `license = "MIT"`다.

## 출처

| 항목 | 값 |
|---|---|
| 논문 | https://arxiv.org/abs/2512.00590 (v2, 2026-01-29). 본문은 https://arxiv.org/html/2512.00590 에서 읽었다. EACL 2026 판: https://aclanthology.org/2026.eacl-long.388.pdf |
| 코드 | https://github.com/screemix/Wikontic |
| commit | `c4e3e5db991480c4bc642b41a6b9b350db6d0678` (2026-09-23) |
| 로컬 사본 | `lab/repos/Wikontic` (이미 있던 clone을 썼다. 디렉터리 이름이 `owner_repo` 규칙과 다르다.) |
| 라이선스 | MIT (`LICENSE`, `pyproject.toml`) |
| 읽은 파일 | `src/wikontic/utils/structured_inference_with_db.py`, `structured_aligner.py`, `inference_with_db.py`, `dynamic_aligner.py`, `openai_utils.py`, `base_inference_with_db.py`, `structured_inference_with_db_doc_parallelized.py`(머리 주석), `db/mongo_backend.py`, `db/qdrant_backend.py`, `create_wikidata_ontology_db.py`, `inference_and_eval/dataset_inference.py`, 프롬프트 `triplet_extraction/`, `name_refinement/` |
| 실행 | 코드는 실행하지 않았다. 매핑 JSON의 항목 수만 셌다. |
| 검증 시 추가로 읽은 파일 | `utils/language_config.py`, `utils/ontology_mappings_en_en/`, `preprocessing/constraint-preprocessing_batch.py`(함수 목록·SPARQL), `inference_and_eval/qa_eval_musique.py`, `qa_eval_hotpot.py`, `README.md` |

## 검증 기록

반박 검증은 commit `c4e3e5d` 사본과 arXiv HTML 본문을 다시 열어 했다. 코드는 실행하지 않았다.

### 그대로 맞은 것

| 주장 | 다시 본 곳 |
|---|---|
| 추출 프롬프트에 type 목록이 없고, 추출 뒤 임베딩 후보 + LLM 선택으로 type·relation을 맞춘다 | `structured_inference_with_db.py:41-243`, `prompts/triplet_extraction/propmt_1_types_qualifiers.txt` |
| `_validate_backbone`이 조상 type을 펼쳐 domain·range를 검사한다 | `structured_inference_with_db.py:245-291` |
| 구조화 출력 없이 `temperature=0`, 정규식으로 JSON을 꺼낸다 | `openai_utils.py:127-184`. "do not raise an exception" 주석은 `:292`, `:352` |
| alias 표 문서 모양과 unique 키 | `structured_aligner.py:387-405` |
| 사람이 alias를 넣는 입구가 없다 | `src/`에서 `approv|manual|curat` 결과 없음. 데모 앱도 세션 그래프 삭제만 있다(`demo_app/app_pages/3_Current_KG.py:26-39`) |
| 정확 일치면 LLM을 부르지 않고, 아니면 LLM이 후보 label 중 하나나 "None"을 고른다. 문턱값은 없다 | `structured_inference_with_db.py:313-350` |
| triplet만 `source_text_id`를 갖고, Mongo는 처음 것을, Qdrant는 마지막 것을 남긴다 | `mongo_backend.py:269-270`, `qdrant_backend.py:320-328`, `structured_aligner.py:414-422` |
| qualifier는 복사만 되고 중복 키에 없다. `rank_object_qualifiers.txt`는 `openai_utils.py:85`에서 등록만 되고 부르는 곳이 없다 | `structured_inference_with_db.py:471`, `grep quailfier_object_ranker` |
| 허브 장치가 없다. QA는 5 hop을 제한 없이 넓힌다 | `src/` grep, `base_inference_with_db.py:183-228` |
| 논문 수치(Table 1, 2, 3, 5, 6)와 §3.6의 "–15.9 EM" 불일치, Limitations "matching format" | arXiv HTML 본문 |

### 고친 것

| 축 | 원래 주장 | 고친 내용 | 근거 |
|---|---|---|---|
| A | schema 위치는 `ontology_mappings/`, type 3,476·property 2,445 | 기본 로드 경로는 `ontology_mappings_en_en/`이고 type 3,726·property 2,492다. `ontology_mappings/`는 로더가 요구하는 파일 둘이 빠진 다른 사본이다. | `language_config.py:43-48`, `create_wikidata_ontology_db.py:294-302, 372-376`, `README.md:340`, 항목 수를 셌다 |
| A | "schema는 사람이 정하지 않는다" | 사용자가 고르지 않는 것은 맞다. 다만 LLM 생성이 아니다. 내용은 Wikidata 편집자가 쓴 property type 제약(P2302)을 스크립트가 거둔 것이고, 추출 전에 고정된다. | `constraint-preprocessing_batch.py:274-294, 383` |
| B | 정규화 프롬프트 인용 "If no suitable match exists" | 원문은 "If no suitable match for object exists"다. 인용을 원문대로 고쳤다. | `rank_object_names.txt:17` |
| D | §2.2의 "remain linked"는 relation 제약만 어긴 triplet에만 맞다 | 엔티티별로 갈린다. type이 맞은 쪽 엔티티는 정규화되고, 어긋난 쪽은 안 된다. | `structured_inference_with_db.py:472-482` |
| D·F | type 계열 안에서만 병합해 다른 type끼리는 합쳐지지 않는다 | 후보 필터는 mention type과 그 조상 type 전부다. `entity`가 3,715/3,726개 type의 조상이라, 넓은 type으로 저장된 엔티티는 거의 모든 mention의 후보가 된다. | `structured_aligner.py:339-371`, `entity_type2hierarchy.json`을 세었다 |
| E | `use_filtered_triplets=False` 근거가 함수 기본값뿐 | 평가 스크립트 기본값도 False임을 근거에 더했다. 결론은 같다. | `qa_eval_musique.py:113`, `qa_eval_hotpot.py:118` |

### survives 판정

[확인] 사용자가 정한 schema·용어집은 아니다. 그러나 schema는 사람(Wikidata 편집자)이 쓴 제약을 추출 전에 고정해 쓰고, `--mappings_dir`로 다른 사람이 쓴 schema로 바꿀 입구도 있다. 그래서 "사람이 정한 schema를 아예 안 쓴다"에는 해당하지 않는다. 용어집(alias 표)은 자동으로만 자란다.

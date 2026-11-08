# OntoGPT/SPIRES는 사람이 쓴 schema와 동의어 사전으로 추출 결과를 사후 정규화한다. 문서 사이 연결은 외부 ID 공유에만 맡긴다

OntoGPT는 Monarch Initiative가 만든 Python 도구다. SPIRES는 그 안의 추출 알고리즘이다(Bioinformatics 2024, arXiv 2304.02711).
사람이 LinkML YAML로 schema를 쓴다. 클래스마다 grounding할 어휘와 허용 ID prefix를 적는다.
LLM은 이름 문자열만 뽑는다. 정식 ID는 추출 뒤에 사전·온톨로지 대조로 붙는다.

사용자 목표에 주는 답은 둘이다.
첫째, "사람이 정한 구조로 이름을 고정한다"는 절반은 이 설계가 가장 성숙하게 풀었다. 클래스별 어휘 지정, 우선순위가 있는 사전 대조, 쓰기 직전 검증 리포트까지 있다.

둘째, "새 데이터와 기존 데이터의 연결고리"는 풀지 않는다. 누적 KB, 문서 간 entity resolution, 범용어 허브 대책이 없다. 오히려 CLI의 named entity 캐시는 사용자 실험의 "처음 본 청크에만 링크" 함정과 같은 모양이다.

## 한 바퀴 흐름

`ontogpt extract -t gocam.GoCamAnnotations -i docs/ --dictionary syn.yaml` 한 번을 따라간다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. schema 읽기 | LinkML YAML을 SchemaView와 pydantic 클래스로 올린다 | `knowledge_engine.py:287-296` |
| 2. 입력 나누기 | 디렉터리면 `.txt` 파일마다 결과 하나. 엔진(`ke`)은 파일 전체에 하나다 | `cli.py:471`(docstring), `cli.py:521-527` |
| 3. 청킹(선택) | 문자 수(`max_text_length`)나 문장 창(`sentences_per_window`)으로 자른다 | `spires_engine.py:168-174` |
| 4. 프롬프트 | `"From the text below, extract the following entities in the following format:"` 뒤에 slot마다 `name: <설명>` 한 줄. enum이면 `"Must be one of: …"`를 붙인다 | `spires_engine.py:506-532` |
| 5. 파싱 | pseudo-YAML을 줄 단위로 읽는다. 필드명을 소문자·밑줄로 바꾸고 복수형 `s`를 떼어 slot과 맞춘다. 맞는 slot이 없으면 버린다 | `spires_engine.py:704-723` |
| 6. 재귀 | range가 inlined 클래스면 그 값 문자열로 같은 절차를 다시 돈다 | `spires_engine.py:749-758` |
| 7. grounding | NamedEntity 값마다 사전 → 온톨로지 annotator 순으로 ID 후보를 낸다 | `knowledge_engine.py:702-811` |
| 8. ID 검증 | 후보가 클래스의 `id_prefixes`, id pattern, `values_from` 값 집합을 통과해야 한다. prefix만 틀리면 mapper(Translator NodeNormalizer)로 바꿔 본다 | `knowledge_engine.py:561-644` |
| 9. 실패 처리 | 통과한 후보가 없으면 `AUTO:<이름>` ID를 준다 | `knowledge_engine.py:537-545` |
| 10. 청크 병합 | 청크 결과의 리스트 필드를 합집합으로 합친다. 어느 청크에서 왔는지는 남기지 않는다 | `spires_engine.py:78-90`, `176-193` |
| 11. span | 문서 전체에서 엔티티 label 문자열의 출현을 모두 찾는다 | `spires_engine.py:201-204`, `parse_utils.py:111-136` |
| 12. 쓰기 직전 검증 | 모든 ID를 온톨로지에 다시 묻는다. 없거나 obsolete면 대체하거나 `AUTO:`로 다시 쓴다 | `term_validator.py:419-550` |
| 13. 출력 | 문서마다 결과 레코드 하나를 같은 출력 스트림(`-o`, 기본 stdout)에 차례로 쓴다. YAML이면 `---`로 나뉜다. 문서 사이 병합은 없다 | `cli.py:306-308`, `cli.py:525-537`, `cli.py:85-140` |

## 축별 분석

### A schema

[확인] 사람이 LinkML YAML 파일로 schema를 쓴다. 저장소에 템플릿이 71개 있다(`src/ontogpt/templates/*.yaml`, 파일 143개 중 절반이 생성된 `.py`).
[확인] 저장소는 코딩 에이전트용 skill `ontogpt-author-template`도 준다(`skills/ontogpt-author-template/SKILL.md`). 사람이 요청하면 에이전트가 템플릿 YAML을 대신 쓰고 검증 스크립트로 확인한다. 이 경우에도 템플릿은 추출 전에 파일로 고정된다. 추출하는 LLM이 데이터를 보고 schema를 만들거나 늘리는 경로는 없다. `suggest-templates` 명령도 LLM이 기존 템플릿 중에서 고르게 할 뿐이다(`cli.py:2265-2300`).
[확인] 논문 초록은 schema를 "user-defined knowledge schema"라고 부른다. §2.2는 MeSH 값 집합을 "configured ... manually"했다고 쓴다.
논문 §2는 schema를 "a collection of classes or templates"로 정의한다. 각 속성에 Name, Multivalued, Identifier, Prompt, Range, ValueSets, Inlined가 있다.

클래스 하나의 모양은 이렇다(`gocam.yaml:73-80`).

```yaml
Gene:
  is_a: NamedEntity
  id_prefixes: [HGNC, PR, UniProtKB]
  annotations:
    annotators: gilda:, bioportal:hgnc-nr
```

[확인] 강제는 세 겹이다. 구조화 출력(JSON schema, function calling)은 쓰지 않는다.

| 겹 | 방법 | 근거 |
|---|---|---|
| 프롬프트 | slot 설명과 enum 허용값을 프롬프트에 넣는다 | `spires_engine.py:512-530` |
| 파싱 | schema에 없는 필드는 `"Cannot find slot"` 경고 뒤 버린다. enum 밖 값은 `None`이 된다 | `spires_engine.py:718-723`, `915-917` |
| ID 검증 | `id_prefixes`, id slot `pattern`, `values_from`(온톨로지 가지 질의)를 통과해야 ID로 인정한다 | `knowledge_engine.py:574-609` |

[확인] 논문 §5.3은 function calling을 언급한다. 그것이 구조는 지켜도 "do not alleviate the issue of hallucination"이라고 쓴다.

### B 용어집

[확인] 정식 이름·별칭 층이 둘 있다. 둘 다 추출 뒤 정규화에만 쓴다. `get_completion_prompt`는 사전을 읽지 않는다(`spires_engine.py:499-548`).

| 층 | 정식 이름 / 별칭 | 누가 쓰나 | 근거 |
|---|---|---|---|
| 외부 온톨로지 | 온톨로지 label / synonym | 온톨로지 커뮤니티(GO, MeSH 등). OAK adapter로 붙는다 | `docs/custom.md:78`, 논문 §4 |
| 로컬 사전 `--dictionary` | `- id: … / synonym: …` 평면 목록 | 사용자 | `knowledge_engine.py:405-418`, `cli.py:516-517` |

[확인] 대조 순서는 고정이다(`knowledge_engine.py:702-811`).
1. 이미 CURIE 모양이면 그대로.
2. 소문자로 바꾸고 단수형으로도 시도한다(`inflection.singularize`).
3. 괄호 안과 괄호 밖을 따로 시도한다.
4. 사전 정확 일치.
5. 사전 부분 일치. 사전 항목이 이름의 부분 문자열이고 길이 비율이 0.66을 넘어야 한다(`knowledge_engine.py:766-771`).
6. annotator 전체 일치(label 일치를 synonym 일치보다 앞에), 그다음 부분 일치. 부분 일치는 BioPortal 같은 OntoPortal annotator만 한다. `sqlite:obo:*`·`gilda:`는 건너뛴다(`knowledge_engine.py:782-798`).

[확인] BC5CDR 평가는 훈련셋 주석으로 사전을 만들었다. 논문 §2.2: "The training set was used to enhance our mappings of named entity spans to MeSH identifiers; after building this lexicon, the training set was discarded." 그 파일은 `src/ontogpt/evaluation/ctd/database/synonyms.yaml`(18,592줄)이다.

[확인] 한 synonym이 두 ID를 가리키면 경고만 하고 뒤 것으로 덮는다(`knowledge_engine.py:415-417`).

### C 원문 연결 범위

[확인] 연결 단위는 문서다. 결과 하나(`ExtractionResult`)가 입력 파일 하나이고 `input_text` 전체를 담는다(`spires_engine.py:206-216`). 청크·문장 단위 출처는 남지 않는다. 관계(triple)에도 출처 필드가 없다(`core.yaml:156-178`).

[확인] 엔티티는 `original_spans`로 문자 위치를 가리킨다. 문서 전체에서 label 문자열의 **모든** 출현을 대소문자 무시로 찾는다(`parse_utils.py:126-134`).

[확인] 그런데 "모든 곳"에 구멍이 둘 있다. 코드를 읽어서 본 것이고 실행하지는 않았다.

| 구멍 | 무엇이 빠지나 | 근거 |
|---|---|---|
| label이 첫 표면형 하나 | `NamedEntity(id, label=text)`는 그 ID를 처음 grounding한 문자열로 만든다. 같은 ID의 다른 별칭 출현은 span 검색에서 빠진다 | `knowledge_engine.py:531-533`, `spires_engine.py:939` |
| 엔진 수명 캐시 | `named_entities`는 엔진에 쌓이고 CLI는 지우지 않는다. 앞 문서에서 본 ID는 뒤 문서의 `named_entities` 목록에 다시 들어가지 않아 span도 없다 | `knowledge_engine.py:241-246`, `531-534`, `spires_engine.py:130`, `cli.py:521-527` |

[확인] 평가 스크립트는 이 캐시를 문서마다 손으로 비운다. `eval_ctd.py:221`의 `ke.named_entities = []  # This stores the NEs the extractor knows about`가 그 자리다. `eval_ctd_ner.py:282`, `eval_maxo.py:234`도 같다. CLI `extract`에는 이 줄이 없다.
[추정] 그래서 CLI로 여러 문서를 돌리면 엔티티 목록 쪽은 "처음 본 문서에만 출처"가 된다 — 사례: 위 코드 경로 1개, 사용자 실험의 atlas-rag 변환 코드 1개가 같은 모양이다. 다만 `extracted_object` 안의 CURIE 값은 문서마다 남으므로 ID로는 계속 이어진다.

### D 새/기존 연결

[확인] 새 문서와 기존 엔티티를 잇는 장치는 **같은 외부 ID로 grounding되는 것**뿐이다. 누적 저장소, 문서 간 entity resolution, 임베딩 대조가 없다. 문서마다 결과 레코드를 따로 만들어 같은 출력 스트림에 차례로 쓴다(`cli.py:525-537`).

[확인] 절차는 이렇다.
1. 새 문서의 이름이 #B의 대조 순서를 거쳐 CURIE가 된다(예: `GO:0008907`).
2. 기존 문서 결과에도 같은 CURIE가 있으면 둘은 그 ID를 공유한다.
3. 실제 병합은 사용자가 따로 한다. 논문 §4.2의 레시피 파이프라인은 결과를 LinkML-OWL로 OWL로 바꾸고 ROBOT으로 FOODON과 합친 뒤 Elk reasoner로 분류한다.

[확인] 어휘 밖 이름의 ID는 `AUTO:{quote(text)}`다(`knowledge_engine.py:539`). 표면 문자열을 그대로 인코딩하므로 대소문자까지 같아야 같은 ID가 된다. 그래서 `AUTO:Beta-catenin`과 `AUTO:beta-catenin`은 서로 다른 노드다.

[확인] `merge_resultsets`라는 병합 함수는 있다(`knowledge_engine.py:817-866`). 같은 대상에 대한 결과 여러 개의 필드를 합친다. 사용처는 `eval_hpoa.py:236` 하나다.

### E 새 용어

[확인] 어휘 밖 이름은 버리지 않고 `AUTO:` 접두사로 남긴다. CLI 기본값이 `"AUTO"`다(`cli.py:321-324`).
쓰기 직전 검증도 대체 ID를 못 찾으면 `AUTO:`로 다시 쓴다. 그 수는 리포트의 `unresolved_terms`에 남는다(`term_validator.py:543-550`, `core.yaml:73-77`).

[확인] 사람 승인 대기열이나 사전 자동 추가는 없다. `AUTO:` ID는 출력에만 있다.
에이전트 skill `ontogpt-troubleshoot`가 "Half the diseases came back as AUTO: ids. Why?" 같은 질문을 받도록 되어 있다(`docs/agent_skills.md`). 원인을 사람이 찾는 구조다.

[확인] 다른 처리도 있다.

| 경우 | 처리 | 근거 |
|---|---|---|
| schema에 없는 필드 | 버림 | `spires_engine.py:718-723` |
| enum 밖 값 | `None` | `spires_engine.py:915-917` |
| 클래스의 `prompt.examples`와 같은 이름 | `"LIKELY HALLUCINATION: "` 접두사 | `knowledge_engine.py:520-527`, `ctd.yaml:76` |
| ID는 맞는데 label이 synonym도 아님 | 정확히 그 label인 다른 term이 있으면 교체, 없으면 `LABEL_DIFFERS`로 남김 | `term_validator.py:505-531` |

### F 범용어 허브

[확인] 전용 장치는 없다. `src/ontogpt`(템플릿 제외)에서 `stopword|stoplist|blacklist|denylist|frequency|idf`를 찾았고 결과가 없었다. OntoGPT는 그래프를 쌓지 않으므로 허브를 재는 단계도 없다.

[확인] 허브를 줄이는 쪽으로 작동할 수 있는 장치는 셋이다.

| 장치 | 동작 | 근거 |
|---|---|---|
| 부분 일치 길이 비율 | 사전 항목이 이름 길이의 66%를 넘어야 부분 일치로 인정한다. 짧은 범용어가 긴 구체 용어를 삼키지 못한다 | `knowledge_engine.py:766-771` |
| `values_from` + `reachable_from` | ID가 온톨로지의 특정 가지 아래에 있어야 한다. 예: `GeneLocation`은 GO cellular_component 아래만 허용 | `gocam.yaml:108-200`, `knowledge_engine.py:590-609` |
| 클래스별 `id_prefixes` | 같은 문자열이라도 클래스가 다르면 다른 어휘로만 간다 | `knowledge_engine.py:574-580` |

[추정] 길이 비율 가드는 사용자 실험의 허브 하나를 직접 막는다 — 사례: "LLM agents"는 "LLM"과 비율 0.3이라 부분 일치로 묶이지 않는다. 그러나 이름이 정확히 "LLM"인 언급은 그대로 한 ID로 모인다. 정확 일치 허브는 막지 못한다.
[추정] `reachable_from` 가지 제한이 가지 뿌리 노드 자체(예: `GO:0005575`)를 포함하는지는 모른다. LinkML `ValueSetExpander`의 `include_self` 기본값을 보면 알 수 있다.

### G 엔티티·이벤트

[확인] 범용 이벤트·시간축 모델은 없다. 템플릿 작성자가 이벤트 클래스를 만들면 그것을 뽑는다.
`adverse_outcome_pathway.yaml:71-98`은 `MolecularInitiatingEvent`, `KeyEvent`를 자유 텍스트로 받는다. 이벤트 사이 관계 slot은 주석 처리돼 있다(`"# TODO: process key event relationships"`, 29행).
날짜는 문자열 slot이다(`storms.yaml:64` `methods_relevant_dates`). 시간 정규화 코드는 찾지 못했다.

### H 근거 수치

[확인] 논문 §4.3 grounding 실험이다. 온톨로지마다 term 100개를 한 프롬프트에 주고 ID를 맞히게 했다(§2.1). 모델은 gpt-3.5-turbo-16k와 gpt-4-1106-preview다.

| 온톨로지 | SPIRES + GPT-3.5-turbo | SPIRES + GPT-4-turbo | SPIRES 없이 |
|---|---|---|---|
| GO | 98/100 | 97/100 | GPT-3.5 3/100, GPT-4-turbo는 답을 거부 |
| EMAPA | 100/100(모델 명시 없음) | (모델 명시 없음) | GPT-3.5는 EHDAA2 ID를 냄, GPT-4-turbo 거부 |
| MONDO | 97/100 | 18/100 | 둘 다 많아야 1 |

[추정] 이 수치는 "LLM에게 ID를 외우게 하지 말고 어휘 대조로 붙여라"의 근거다 — 사례: 위 표 3행. 본문에서 이름을 뽑는 단계의 정확도나 사전 유무의 ablation은 아니다.

[확인] 논문 §4.4 BC5CDR(초록 500개, CID triple 1,066개) 관계 추출이다.

| 설정 | F | P | R |
|---|---|---|---|
| chunking, gpt-3.5-turbo | 41.16 | 0.43 | 0.39 |
| no chunking, gpt-3.5-turbo | 36.64 | 0.63 | 0.26 |
| no chunking, 모델명 미기재(§2.2로 보아 gpt-4) | 43.80 | 0.69 | 0.32 |

[확인] 논문은 이를 "just below the average of all 18 teams"라고 쓴다.
[추정] 청킹이 재현율을 올리고 정밀도를 내린 방향은 사용자 실험(링크 범위를 넓히자 재현율 0.92, 정밀도 0.37)과 같다 — 사례: 위 표 1·2행 1쌍.
[확인] 문서 간 연결, 허브, 순위 검색을 잰 수치는 없다.

## 가져올 것

| 무엇 | 사용자 시스템에서 | 근거 |
|---|---|---|
| 클래스별 grounding 규칙을 schema 안에 둔다 | 엔티티 종류 10개마다 허용 어휘(용어집 구역)와 ID 형식을 적는다 | #A |
| 용어집을 `id`/`synonym` 평면 목록으로 둔다 | 정확 일치 → 길이 비율 부분 일치 → 외부 어휘 순서를 그대로 쓴다 | #B |
| 부분 일치 길이 비율 가드 | "KG", "LLM" 같은 짧은 항목이 긴 구체 용어를 흡수하지 못하게 한다. 정확 일치 허브는 따로 막아야 한다 | #F |
| `AUTO:` 표시 + 검증 리포트 | 어휘 밖 이름을 버리지 말고 표시한다. 리포트 집계를 사람 승인 대기열의 입력으로 쓴다(대기열은 직접 만들어야 한다) | #E |
| `prompt.examples` 대조 | 프롬프트 예시와 똑같은 이름은 hallucination 후보로 표시한다 | #E |
| 피할 것: 엔진 수명 캐시 | 엔티티 출처는 문서·청크마다 새로 기록한다. "이미 본 ID"로 출처를 건너뛰지 않는다 | #C |
| 피할 것: 첫 표면형 하나로 span 검색 | span은 그 ID의 별칭 전체로 찾는다 | #C |

[확인] 라이선스는 코드가 BSD-3-Clause(`LICENSE`, `pyproject.toml:10`), 템플릿 YAML이 CC0(`core.yaml:4` 등)이다. 코드를 가져다 쓰려면 저작권 고지를 남겨야 한다. 템플릿은 조건 없이 쓸 수 있다.

## 출처

- 논문: Caufield et al., "Structured prompt interrogation and recursive extraction of semantics (SPIRES)", Bioinformatics 40(3), 2024, doi:10.1093/bioinformatics/btae104. arXiv: https://arxiv.org/abs/2304.02711 (v2, 2023-12-22). 본문은 Europe PMC 전문(PMC10924283)으로 읽었다.
- 코드: https://github.com/monarch-initiative/ontogpt, commit `9224d33f84cce7097c3519e1d9f0e2be46cec056` (2026-09-10). 로컬 사본은 `lab/repos/monarch-initiative_ontogpt`.
- 라이선스: BSD-3-Clause(코드), CC0(템플릿).
- 남의 코드는 실행하지 않았다. 위 동작 설명은 모두 코드를 읽어서 얻었다.

## 검증 기록

반박 검증 에이전트가 2026-10-11에 다시 확인했다. clone은 `lab/repos/monarch-initiative_ontogpt`, commit `9224d33f84cce7097c3519e1d9f0e2be46cec056`이다. 논문은 Europe PMC 전문 XML(PMC10924283)로 다시 읽었다. 코드는 실행하지 않았다.

### 그대로 맞은 것

- [확인] 인용한 줄 번호는 모두 그 자리에 있었다. `spires_engine.py:506-532`(프롬프트), `718-723`(slot 없음 경고), `917`(enum 밖 None), `939`(span), `130`(문서마다 비우는 것은 `extracted_named_entities`뿐), `knowledge_engine.py:405-418`(사전), `520-545`(hallucination·grounding·AUTO), `574-609`(prefix·pattern·values_from), `766-771`(비율 0.66), `term_validator.py:543-550`, `cli.py:321-324`, `eval_ctd.py:221`을 다시 열었다.
- [확인] 엔진 수명 캐시 주장은 맞다. CLI 루프(`cli.py:525-537`)는 `ke.named_entities`를 비우지 않는다. `knowledge_engine.py:531`은 이미 본 ID를 `extracted_named_entities`에 다시 넣지 않는다.
- [확인] 사전은 프롬프트에 들어가지 않는다. `get_completion_prompt`(`spires_engine.py:499-548`)는 `self.dictionary`를 읽지 않는다.
- [확인] `src/ontogpt`(템플릿 제외) `.py`에서 `stopword|stoplist|blacklist|denylist|frequency|idf`를 다시 찾았고 결과가 없었다.
- [확인] 논문 수치는 맞다. §4.3 GO 98/97, SPIRES 없이 GPT-3.5 3, GPT-4-turbo 거부. MONDO 97/18, SPIRES 없이 많아야 1. §4.4 F41.16(P0.43, R0.39), F36.64(P0.63, R0.26), F43.80(P0.69, R0.32). §2.2 "after building this lexicon, the training set was discarded." `synonyms.yaml`은 18,592줄이다.
- [확인] 라이선스: `pyproject.toml:10` `license = {text = "BSD-3"}`, `core.yaml:4` CC0 URL.

### 고친 것

| 자리 | 전 | 후 | 근거 |
|---|---|---|---|
| #A 템플릿 수 | 70개쯤 | 71개 | `ls src/ontogpt/templates/*.yaml` |
| #A 작성자 | 사람이 쓴다 | 사람이 쓰거나, 사람의 요청으로 코딩 에이전트가 skill을 따라 쓴다. 어느 쪽이든 추출 전에 고정된다 | `skills/ontogpt-author-template/SKILL.md` |
| 한 바퀴 13단계, #D | 문서마다 따로 쓴다 | 문서마다 레코드를 만들어 같은 출력 스트림에 차례로 쓴다 | `cli.py:306-308`, `525-537` |
| #B 대조 6단계 | annotator 부분 일치 | 부분 일치는 OntoPortal annotator만 한다 | `knowledge_engine.py:782-798` |
| #H EMAPA | GPT-3.5 열에 100/100 | 논문 문장에 모델 이름이 없다 | 논문 §4.3 "SPIRES returned correct identifiers for all 100 term descriptions" |

[확인] schema와 사전을 사람이 미리 정한다는 핵심 주장은 살아남았다. LLM이 schema나 용어집을 자동으로 만드는 경로는 찾지 못했다. BC5CDR 사전은 사람이 손으로 쓴 것이 아니다. 사람이 단 훈련셋 주석에서 뽑았고, 보고서도 그렇게 적고 있다.

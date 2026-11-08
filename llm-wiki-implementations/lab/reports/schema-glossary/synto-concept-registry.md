# synto는 용어집을 사람이 고치는 entity 레지스트리로 굴리지만, 엔티티 종류 schema와 범용어 허브 대책은 없다

synto(kytmanov/synto)는 Karpathy llm-wiki를 로컬 LLM으로 구현한 Python CLI다. `raw/*.md`를 읽어 개념(concept)을 뽑고, 개념마다 위키 글을 하나씩 쓴다. 용어집은 SQLite의 `concept_entities` + `concept_labels`다. 개념 하나가 entity_id 하나이고, 이름은 그 id를 가리키는 label(preferred 1개 + alias 여러 개)이다.

용어집 항목 자체는 사람이 미리 정하지 않는다. preferred label은 LLM 추출 결과로 `source='extracted'`가 되어 자동 발급된다(`state.py:2585-2596`). 사람이 정하는 부분은 사후 교정(rename·merge·split·alias add/remove/move)으로 생긴 blessed alias와 tombstone이다.

사용자 목표에 주는 답은 셋이다.
- [확인] "사람이 어느 정도 해도 성능을 보장"하는 장치는 synto에서 가장 잘 갖춰진 부분이다. alias에 출처 등급(LLM이 붙인 weak, 사람이 붙인 blessed)을 두고, 사람이 지운 alias는 tombstone으로 다시 못 붙게 막는다.
- [확인] 새 문서와 기존 문서는 "같은 entity_id에 묶인다"는 한 가지 방식으로만 이어진다. 임베딩은 쓰지 않는다. 이어진 결과는 그 개념의 위키 글이 두 문서를 함께 원문으로 삼는 것이다.
- [확인] 엔티티 종류(사람·조직·방법 같은 type) schema는 없다. 모든 것이 `kind='concept'`다. 범용어가 허브가 되는 문제를 직접 막는 stoplist·빈도 기준도 없다. 문서당 개념 수 상한이 간접적으로만 작용한다.

## 한 바퀴 흐름

PDF 한 편을 `synto add paper.pdf --type paper`로 넣고 `synto run`을 돌릴 때를 따라간다. 근거 줄 번호는 모두 commit `91ac6a3` 기준이다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. import | PDF를 heading 기준 segment로 자르고 `source_segments`에 저장한다. id는 `<source_id>:section:<slug>:<hash8>`이다. 이어 `raw/<source_id>.md`를 쓴다. md·txt를 `add`하면 segment를 만들지 않는다. | `cli.py:5037` "Extract segments (PDF only)", `extractors/pdf.py:240-248` |
| 2. 프롬프트 조립 | 기존 canonical 이름과 alias(개념당 최대 3개)를 프롬프트에 넣는다. 본문에 나오는 개념을 앞에 두고 30개에서 자른다. | `pipeline/ingest.py:87-112`, `:163-181`, `:213` "Existing wiki concepts (reuse these names where applicable)" |
| 3. 추출 | fast 모델이 segment 묶음(unit, fast ctx×1.5자)마다 `AnalysisResult`(summary, concepts[name, aliases], suggested_topics, named_references, quality)를 낸다. JSON schema는 system 프롬프트에 붙는다. | `ingest.py:320-345`, `:523-552`, `models.py:56-77`, `structured_output.py:291-292` |
| 4. 거르기 | 잡음 이름("document", "unknown …")을 버린다. quality가 low·medium이면 본문에 글자 그대로 없는 개념도 버린다. quality별 상한(high 8, medium 4, low 2; paper 15, textbook 25)으로 자른다. | `ingest.py:737-747`, `:811-835`, `:1739-1742`, `config.py:461` |
| 5. 사전 접기 | 사람이 승인한(blessed) alias와 같은 이름이면 그 canonical로 바꾼다. 후보가 LLM이 붙인 alias 중 하나로 blessed alias 하나에만 맞아도 바꾼다. | `ingest.py:1736-1757`, `:1166-1200` |
| 6. 정규화 | 이름마다 순서대로 대조한다: preferred label → blessed alias → 동음이의 stub → 약어 휴리스틱 → 새 entity 발급. | `ingest.py:1202-1345` |
| 7. 기록 | `concepts`(entity_id, source_path)에 문서 단위 연결을 쓴다. 개념별 compile 상태를 pending으로 둔다. alias를 weak(`source='extracted'`)로 저장한다. | `state.py:2418-2500`, `ingest.py:1766-1790` |
| 8. segment 연결 | 개념을 낸 unit에 든 모든 segment에 그 개념을 기록한다(`concept_occurrences`). | `ingest.py:348-380`, `:1794-1800` |
| 9. 관계(선택) | `relation_extraction = true`일 때만 unit마다 관계를 뽑는다. 끝점이 알려진 개념이 아니면 버린다. | `ingest.py:383-448`, `:1804-1840` |
| 10. compile | heavy 모델이 개념마다 글을 쓴다. 그 개념의 entity에 묶인 모든 원문 문서를 재료로 쓴다. | `pipeline/compile.py:1032-1140`, `state.py:2507-2525` |
| 11. 검토 | 초안은 `wiki/.drafts/`에 간다. 사람이 approve·reject한다. reject 사유는 다음 compile 프롬프트에 들어간다. | README:100-114, `compile.py:974-978` |

## 축별 분석

### A schema

[확인] 엔티티 종류 schema는 없다. `concept_entities.kind`는 기본값 `'concept'`만 쓰인다(`state.py:422-430`). 추출 schema `AnalysisResult`는 type 칸 없이 `name`과 `aliases`만 받는다(`models.py:43-53`).

[확인] 관계 schema는 코드에 고정된 `Literal` 18개다. `depends_on`, `part_of`, `causes`, … `cites`, `cited_by`가 있다(`models.py:410-434`). 사람이 파일로 바꿀 수 없다.

[확인] 관계 schema는 두 겹으로 강제된다.
- 프롬프트: system에 "predicate must be exactly one of: …"를 넣는다(`ingest.py:2004-2010`).
- 쓰기 직전 검증: 목록 밖 predicate를 버린다(`ingest.py:2063-2065`). 끝점이 알려진 개념·alias로 풀리지 않으면 `relations`에 쓰지 않는다. 원본 LLM 출력은 `relation_candidates`에 감사 기록으로 남긴다(`ingest.py:427-445`).

[확인] 페이지 종류는 `WikiArticleRecord.kind`의 `concept | synthesis | disambiguation` 셋이다(`models.py:268`). 사람이 고쳐 쓰는 `vault-schema.md`가 있다. `synto init`이 폴더 구조·frontmatter·wikilink 규칙을 적은 기본 stub을 만들고, 사람이 내용을 바꾼다(`cli.py:941-956`). 하지만 compile 프롬프트에 앞 1500자를 "VAULT CONVENTIONS"로 붙일 뿐이다(`compile.py:121-128`, `:950-951`). ingest에는 들어가지 않는다.

[확인] 원문 종류(source_type)별로 system 프롬프트를 바꾼다. `notes`, `paper`, `textbook`, `sql` 등 10종이다(`pipeline/prompts/*.md`). 추출 대상을 바꾸는 장치이지 엔티티 schema는 아니다.

### B 용어집

[확인] 정식 이름과 별칭을 둔다. `concept_labels`의 한 줄이 (entity_id, label, label_key, match_key, role, source)다(`state.py:432-449`). role은 `preferred`와 `alias` 둘이다. preferred는 vault 전체에서 label_key가 유일하다(`idx_concept_labels_preferred_global`).

[확인] 이름 비교 키는 둘이다.
- `concept_key`: NFKC, casefold, 구두점을 공백으로 바꾼다(`concept_text.py:28-33`).
- `match_key`: 그 위에 복수형을 접는다. 4자 미만 토큰과 대문자 약어는 접지 않는다(`concept_text.py:48-85`).

[확인] 누가 쓰는가는 `source` 칸이 기록한다. `extracted`·`legacy_backfill`은 LLM이 쓴 weak alias다. `user`·`rename`은 사람이 쓴 blessed alias다(`state.py:440-441`). 사람은 `synto concept rename|merge|split|alias add|remove|move`로 고친다(README:163-185).

[확인] 추출 전 주입과 추출 뒤 정규화를 둘 다 한다.
- 주입: 기존 canonical과 alias를 "reuse these names" 문구와 함께 넣는다(`ingest.py:213`). 이 단계는 weak alias도 보여 준다(`ingest.py:1662-1665`가 `list_alias_map()` 전체를 쓴다).
- 사후 정규화: blessed alias만 이름을 바로 접는다(`ingest.py:1736-1738` "Only BLESSED aliases pre-fold a candidate"). 후보 이름이 아니라 후보에 LLM이 붙인 alias가 blessed alias 하나에만 맞아도 접는다(`ingest.py:1182-1188`). weak alias와 같은 이름이 개념으로 나오면 접지 않고 새 entity를 만든다(E 참고).

[추정] 사람이 미리 용어집을 채워 넣는 import 경로는 없다. 사례: `alias add`는 이미 있는 개념에만 붙는다(`state.py:3897-3899` "Concept not found"). INDEX.json seed 복원(`ingest.py:1061-1105`)은 rebuild용이다. 사용자 실험처럼 150개 용어집을 먼저 넣으려면 개념이 ingest로 생긴 뒤 alias를 붙이거나 seed 파일을 손으로 만들어야 한다.

### C 원문 연결 범위

[확인] 연결은 두 층이다.

| 층 | 단위 | 범위 | 근거 |
|---|---|---|---|
| `concepts` | 문서(source_path) | LLM이 그 개념을 뽑았고 상한 안에 든 모든 문서 | `state.py:177-182`, `:2473-2477` |
| `concept_occurrences` | segment | 개념을 낸 unit 안의 모든 segment. PDF import에만 있다 | `ingest.py:348-380`, `:1670-1681` |

[확인] "처음 본 곳만"이 아니라 "LLM이 뽑은 모든 곳"이다. 문서마다 따로 추출하고, 같은 entity로 풀리면 그 문서에 연결을 하나씩 쓴다. compile은 entity의 모든 문서를 재료로 쓴다(`state.py:2519-2525`).

[확인] 대신 "이름이 나온 모든 곳"도 아니다. 문자열 대조로 연결을 늘리지 않는다. 문서에 이름이 나와도 LLM이 그 문서의 상위 N개 개념으로 고르지 않으면 연결이 없다(`ingest.py:1739-1742`).

[확인] segment 단위는 거칠다. 한 unit은 여러 section을 묶은 fast ctx×1.5자 덩어리다(`ingest.py:311-317`). 그 unit에서 나온 개념은 unit 안의 모든 segment에 붙는다. docstring이 이를 밝힌다: "attributed to every segment in that chunk"(`ingest.py:357`).

[확인] 관계 근거는 반대로 unit의 첫 segment에만 건다: "fanning the quote out to every member segment would fabricate attributions"(`ingest.py:1812-1815`).

[확인] 그냥 `raw/`에 넣은 md 노트는 segment가 없다. 이 경우 연결은 문서 단위뿐이다(`cli.py:5037`, `ingest.py:1671-1674`).

### D 새/기존 연결

[확인] 새 문서의 이름 하나는 `_normalize_concepts`(`ingest.py:1256-1343`)에서 이 순서로 풀린다.

1. preferred label 대조: label_key 정확 일치, 없으면 match_key(복수형 접기) 일치(`state.py:2710-2740`). 둘 이상이면 동음이의다. 그 문서가 이미 한쪽에 묶여 있으면 그쪽을 쓴다(sticky, `state.py:2881-2903`). 아니면 모호 출현으로 기록하고 연결하지 않는다.
2. blessed alias 대조(`state.py:2742-2756`).
3. 분리(split)로 생긴 동음이의 stub이 있으면 모호 출현으로 보낸다.
4. 그 이름을 weak alias로 가진 entity가 없을 때만 메모리 색인을 본다. 색인은 모든 canonical 이름과 모호하지 않은 alias 전체(weak 포함)로 만든다. 키는 원래 이름, 괄호를 뗀 base 이름, 괄호 약어, 소문자형이다. "Extreme Programming (XP)" ↔ "XP" 같은 경우가 여기서 접힌다(`ingest.py:917-935`, `:1309-1323`, `state.py:4162-4181`).
5. 같은 실행 안에서 이미 발급한 match_key면 건너뛴다. 그 밖이면 새 entity를 발급한다(`ingest.py:1326-1343`).

[확인] 쓰기 단계에 두 검사가 더 있다.
- 새 preferred 이름이 다른 entity의 weak alias와 같으면, 그 alias를 지우고 merge 후보를 남긴다(`state.py:2566-2584`, `:2497-2498` reason "promoted-from-alias").
- 뽑힌 alias가 다른 entity의 preferred 이름과 같으면, alias를 버리고 merge 후보를 남긴다(`ingest.py:1775-1788` reason "alias-collides-preferred").

[확인] 임베딩·LLM 판정에 의한 entity resolution은 없다. RAG 경로는 "Phase 2" 자리만 있고 기본값은 꺼져 있다(`ingest.py:1640` `if rag is not None`). query도 "No embeddings"를 내건다(README:118).

[확인] 이 규칙은 ingest 순서와 무관하게 같은 결과를 내도록 설계됐다. 테스트가 논문 집합의 모든 순열로 ingest를 돌려 identity 구조가 같은지 본다(`tests/test_ingest_convergence.py:1-7`).

### E 새 용어

[확인] 용어집 밖 이름은 자동으로 새 entity가 된다. 승인 대기열을 거치지 않는다(`ingest.py:1330-1343`, `state.py:2585-2597`). 사람의 판단은 사후에 들어간다.

| 상황 | 처리 | 사람이 보는 곳 |
|---|---|---|
| weak alias였던 이름이 개념으로 나옴 | 새 entity + merge 후보 | `synto doctor`, `concept inspect` (`cli.py:3399`) |
| 동음이의(같은 이름, entity 둘 이상) | 모호 출현으로 기록, 연결 안 함 | `concept keep SURFACE ENTITY` (README:189) |
| 틀린 alias | `alias remove`가 지우고 tombstone을 남김 | 다음 ingest가 `_is_alias_denied`로 막음 (`state.py:2228-2240`, `:4123-4127`) |
| 사람·조직·사건 같은 고유명 | `named_references`로 받아 본문에 글자 그대로 있을 때만 `knowledge_items`에 `status='candidate'`로 둠 | `synto items audit` (`pipeline/items.py:174-205`, `:208-228`) |

[확인] 마지막 대기열은 반쯤만 있다. `items audit`는 "suggested: classify / ignore / keep candidate"를 출력한다(`cli.py:4374`). 하지만 `items` 그룹에는 `audit`와 `show`만 있다(`cli.py:4346-4395`). 분류·무시 명령은 없다.

[확인] 사람이 붙인 alias가 LLM 출력에 밀리지 않는 장치는 확실하다. blessed alias는 자동 강등 대상이 아니다(`state.py:2569-2573`). tombstone은 `.synto/INDEX.json` seed로 state.db 재생성 뒤에도 살아남는다(CHANGELOG:251-254).

### F 범용어 허브

[확인] 직접 대책은 없다. 개념의 문서 수·연결 수(degree)를 보고 막는 코드를 찾지 못했다. 찾아본 곳은 `pipeline/lint.py`의 `graph_noise`·`graph_connectivity` 검사(`:474-575`), `compile.py`의 링크 단계, `query.py`, `state.py`의 alias 집계다. `graph_noise`는 Welcome.md·미디어 노드·제목 중복만 본다.

[확인] 간접 장치는 넷이다.

| 장치 | 효과 | 근거 |
|---|---|---|
| 문서당 개념 상한(high 8, medium 4, low 2; paper는 high 15, textbook은 high 25) | 범용어가 문서마다 상위 N개 자리를 다툰다 | `ingest.py:1739-1742` |
| 잡음 이름 목록 | "document", "file" 같은 7개 이름과 "unknown"으로 시작하거나 끝나는 이름만 막는다 | `ingest.py:737-747`, `:789-797` |
| 여러 entity가 가진 alias 배제 | 한 alias가 entity 둘 이상에 붙으면 이름 접기·export·query 연결에서 뺀다 | `state.py:4162-4181`, `:4233-4249`, `pack_export.py:144-146` |
| query 그래프 확장 제한 | 관계 confidence 0.7 이상, 추가 페이지 전체 2개 | `query.py:60-61`, `:768-790` |

[추정] 사용자 실험의 허브 문제(KG, LLM 같은 범용어가 모든 문서를 이음)는 synto에서도 생긴다 — 사례: 코드 경로 1개. 문서마다 LLM이 "LLM"을 상위 개념으로 고르면 `concepts`에 그 문서들이 모두 묶인다. 그러면 `LLM.md` 글이 그 문서 전부를 재료로 삼는다(`state.py:2519-2525`). 막아 주는 것은 상한뿐이다.

얼마나 자주 생기는지는 모른다. 범용어가 많은 문서 묶음으로 ingest를 돌려 `concepts` 테이블의 entity별 문서 수를 세어 보면 알 수 있다.

[확인] 위키 글 안의 결정론적 링크는 첫 출현에만, 대소문자를 구분해 건다(`vault.py:139-181` "first occurrence only"). 글 한 편이 범용어로 링크를 도배하지는 않는다.

### G 엔티티·이벤트

[확인] 이벤트와 시간축은 뽑지 않는다. 추출 결과에 시간·사건 칸이 없다(`models.py:56-77`). `named_references`가 "events"를 받지만 이름 문자열로만 저장한다(`ingest.py:218-221`, `items.py:208-228`).

[확인] `Theorem`, `PaperCitation`, `TermRecord` 모델과 `extract_terms` 함수는 정의만 있다. models.py가 "V6 abstractions (added in Phase 0; not yet used by any code path)"라고 밝힌다(`models.py:319-322`). `extract_terms`를 부르는 곳은 없다(grep 결과 정의 1곳뿐).

### H 근거 수치

[확인] 이 설계의 효과를 잰 수치는 없다. README·CHANGELOG에 precision·recall·중복률 같은 숫자가 없다(`CHANGELOG.md` grep).

[확인] 있는 것은 정확성 테스트와 구조 평가다.
- 순서 무관성: 모의 LLM으로 모든 ingest 순열을 돌려 identity가 같은지 본다(`tests/test_ingest_convergence.py`).
- `synto eval`: article coverage, citation coverage, INDEX.json 유효성, wikilink 해석률을 잰다. term_recall은 건너뛴다(`pipeline/eval.py:35-60` "metrics_skipped": ["term_recall"]).
- 벤치마크는 compile 시간만 잰다(`scripts/benchmark.sh:2`).

## 가져올 것

| 무엇 | 왜 | 비용 |
|---|---|---|
| alias에 출처 등급(weak/blessed) 두기 | 사람이 정한 용어집은 이름을 바로 접는다. LLM이 붙인 alias는 후보로만 쓴다. 사용자 실험에서 용어집이 범용어를 한 이름으로 모은 것과 같은 과잉 병합을 줄인다 | `concept_labels`에 `source` 칸 하나 |
| tombstone(alias 거부 기록) | 사람이 뗀 연결을 다음 추출이 되살리지 못한다. "사람이 손대도 성능 유지"의 핵심이다 | 테이블 하나 + 모든 alias 쓰기 경로에서 검사 |
| 충돌을 merge 후보로 남기기 | 자동 병합 대신 사람의 작업 목록을 만든다. 정밀도를 지키면서 재현율 손실을 눈에 보이게 한다 | 테이블 하나 |
| 끝점 닫기(관계 끝점이 등록된 개념이 아니면 버림) + 원본 출력 감사 기록 | 관계 schema를 쓰기 직전에 강제하는 간단한 방법이다 | 코드 몇 줄 |
| 쓰지 말 것: unit 전체 segment로 출현을 퍼뜨리기 | 연결 재현율은 오르지만 정밀도가 떨어진다. 사용자 실험의 0.62 → 0.37 하락과 같은 방향이다 | — |

[추정] 사용자의 허브 문제는 synto에서 가져올 답이 없다 — 사례: F에서 찾은 장치 4개가 모두 간접 장치다. 문서 빈도 상한이나 범용어 목록은 따로 설계해야 한다.

라이선스는 MIT다. 코드를 가져다 쓸 때 저작권 고지와 라이선스 문구만 남기면 된다.

## 출처

- 저장소: https://github.com/kytmanov/synto
- commit: `91ac6a3681df0552b6c9baef159439c7ebd780c9` (2026-10-07)
- 라이선스: MIT (`LICENSE`)
- 로컬 사본: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/kytmanov_synto`
- 읽은 파일: `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `src/synto/pipeline/ingest.py`, `src/synto/state.py`, `src/synto/models.py`, `src/synto/concept_text.py`, `src/synto/pipeline/items.py`, `src/synto/pipeline/compile.py`, `src/synto/pipeline/query.py`, `src/synto/pipeline/lint.py`, `src/synto/vault.py`, `src/synto/config.py`, `src/synto/cli.py`(add, items, vault-schema 부분), `src/synto/extractors/pdf.py`, `tests/test_ingest_convergence.py`
- 실행: 하지 않음(읽기만 함)

## 검증 기록

다른 에이전트가 반박 검증을 했다. 로컬 사본 `kytmanov_synto`의 HEAD가 보고서의 commit `91ac6a3681df0552b6c9baef159439c7ebd780c9`와 같은 것을 확인했다. 코드는 읽기만 했다.

### 다시 열어 맞다고 확인한 것

- A: `concept_entities.kind` 기본값 `'concept'`(`state.py:424-432`), `Concept`·`AnalysisResult`에 type 칸 없음(`models.py:46-77`), `RelationCandidate.predicate` Literal 18개(`models.py:414-434`), system 프롬프트 "predicate must be exactly one of"(`ingest.py:2007`), 목록 밖 predicate 제거(`ingest.py:2063-2065`), 끝점 미해결 시 버리고 `relation_candidates`에 원본 기록(`ingest.py:427-445`), vault-schema 앞 1500자(`compile.py:121-128`).
- B: `concept_labels`의 role·source CHECK 제약(`state.py:434-444`), 프롬프트 alias 3개·전체 30개 자르기(`ingest.py:111`, `:172`), "reuse these names" 문구(`ingest.py:213`), 프롬프트에 weak alias까지 넣음(`ingest.py:1664` `db.list_alias_map()`), `add_alias`가 없는 개념에 "Concept not found"를 냄(`state.py:3897`).
- C: unit 크기 `max(ctx * 3 // 2, 4096)`(`ingest.py:311-317`), "attributed to every segment in that chunk"(`ingest.py:357`), 관계 근거는 unit 첫 segment(`ingest.py:1812-1815`), segment 추출은 PDF만(`cli.py:5037-5039`).
- D: `_normalize_concepts`의 대조 순서(`ingest.py:1256-1343`), sticky 해소(`state.py:2881-2903`), merge 후보 reason 두 가지(`state.py:2498`, `ingest.py:1785`), RAG 분기(`ingest.py:1640`), README "No embeddings"(README:118).
- E: tombstone 검사(`state.py:2228-2240`)와 alias 쓰기 경로의 검사(`state.py:4127-4131`), `items` 그룹의 audit·show 두 명령(`cli.py:4345-4395`), named_references는 본문 증거가 있을 때만 `status='candidate'`(`items.py:174-228`).
- F: query 상수 0.7·2(`query.py:60-61`), 여러 entity의 alias 배제(`state.py:4162-4181`, `pack_export.py:144-146`).
- G: "not yet used by any code path"(`models.py:320`), `extract_terms` 호출처 없음(grep).
- H: 순열 테스트 docstring(`tests/test_ingest_convergence.py:1-7`), `"metrics_skipped": ["term_recall"]`(`pipeline/eval.py:57`), benchmark는 compile 시간(`scripts/benchmark.sh:2`), README·CHANGELOG에 precision·recall 수치 없음(grep).

### 고친 것

- 용어집이 사람이 미리 정하는 것이 아니라는 점을 머리말에 밝혔다. preferred label은 LLM 추출로 `source='extracted'`가 되어 자동 발급된다(`state.py:2585-2596`). 사람이 정하는 것은 사후 교정으로 생긴 blessed alias와 tombstone이다. 원래 보고서도 import 경로가 없다고 적었지만, 머리말만 읽으면 용어집을 사람이 운영하는 것처럼 읽혔다.
- 사전 접기(5단계)에 빠진 경로를 더했다. 후보 이름이 아니라 후보에 LLM이 붙인 alias가 blessed alias 하나에만 맞아도 접는다(`ingest.py:1182-1188`).
- D 4단계 메모리 색인을 넓혀 적었다. 색인은 괄호 약어만이 아니라 base 이름·소문자형도 키로 쓴다. 대상에는 weak alias도 들어간다(`state.py:4162-4181` `list_alias_map`은 source를 거르지 않는다). 같은 실행 안의 중복 제거 단계도 더했다.
- 잡음 이름은 7개 고정 목록에 더해 "unknown"으로 시작하거나 끝나는 이름도 막는다(`ingest.py:789-797`).
- 문서당 상한에 source_type별 기본값(paper 15, textbook 25)을 F 표에도 적었다(`config.py:461`, `ingest.py:1739`).
- vault-schema.md는 `synto init`이 기본 stub을 쓰고 사람이 고치는 파일이라고 밝혔다(`cli.py:941-956`).
- 줄 번호를 바로잡았다. `state.py:2486-2491` → `:2473-2477`, `:2575-2589` → `:2566-2584`, `:2495-2496` → `:2497-2498`, `:2590-2597` → `:2585-2597`.

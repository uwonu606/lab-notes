# AutoSci는 사람이 쓴 YAML schema를 엣지 쓰기 도구로 강제하고, 별칭 대조로 "만들기 전에 병합"한다. 다만 원문 연결은 논문 단위이고 범용어 허브는 그래프 탐색에서 막지 못한다

AutoSci(구 OmegaWiki)는 Claude Code skill 묶음과 Python 도구로 된 연구용 llm-wiki다.
논문 하나를 `/ingest`하면 LLM이 papers·concepts·methods·people 페이지를 쓰고 `wiki/graph/edges.jsonl`에 엣지를 붙인다.
페이지 종류 9개와 엣지 종류 16개는 사람이 `runtime/schema/*.yaml`에 적는다.
사용자 목표("raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조")에 주는 답은 세 가지다.
첫째, [확인] 엣지는 도구가 schema로 검사한다. 모르는 엣지 종류, endpoint 위반, evidence·confidence 누락은 쓰기 전에 거부된다.
둘째, [확인] 새 개념은 "만들기 전에" 결정적(LLM 없는) 별칭 대조 도구를 거친다. 기본값은 병합이다.
셋째, [확인] 범용어는 foundation이라는 별도 계층으로 보낸다. 하지만 이 계층은 페이지 역링크만 끊는다. `neighbors` 그래프 탐색은 foundation을 그대로 통과한다. 그래서 사용자가 겪은 허브 문제를 그래프 쪽에서는 풀지 못한다.
[확인] 원문 연결은 페이지가 "어느 논문들"을 가리키는 수준이다. 청크·문장 위치는 없다.
[확인] 이 설계의 효과를 잰 수치는 논문에도 저장소에도 없다.

## 한 바퀴 흐름

논문 하나(`.tex` 우선, 없으면 PDF→tex 변환)가 페이지가 되는 순서다. 근거는 `.claude/skills/ingest/SKILL.md`다.

1. 원문 확정 (Step 1). arXiv URL이면 `raw/discovered/`로 내려받는다. 로컬 PDF면 `raw/tmp/`에 tex를 만든다. 청크로 자르지 않는다. 논문 전체를 LLM이 읽는다.
2. 논문 정체 확정 (Step 2). `research_wiki.py slug "<title>"`가 slug를 만든다. 같은 slug에 arXiv ID나 제목이 같으면 멈춘다. Semantic Scholar로 venue·year·importance(1~5)를 채운다.
3. 논문 페이지 작성 (Step 3). LLM이 `entities.yaml`의 papers 필드와 `templates/papers.md.tmpl` 섹션을 채운다. 쓰기 전 검사는 "shape check"(필수 키, enum 범위, YAML 파싱)뿐이다. 이 검사도 LLM이 스스로 한다.
4. 개념·방법·사람 (Step 4). 개념 후보마다 `find-similar-concept`를 먼저 부른다. 점수에 따라 foundation 연결 / 병합 / 생성 중 하나를 고른다. 방법은 도구 없이 `wiki/methods/`를 LLM이 훑어서 판단한다. 사람 페이지는 importance ≥ 4일 때만 만든다.
5. 논문↔논문 (Step 5). Semantic Scholar 참고문헌 중 wiki에 이미 있는 논문에 `cites`를 붙인다. 원문에 분명한 단서가 있을 때만 의미 엣지(`builds_on` 등)를 붙인다.
6. 주제·색인 (Step 6). 태그가 맞는 기존 topic 페이지에만 붙인다. `/ingest`는 topic을 만들지 않는다.
7. 로그·재생성 (Step 7). `log.md`에 한 줄을 붙이고 `context_brief.md`, `open_questions.md`를 다시 만든다.
8. 사후 감사. `/check`가 `tools/lint.py`로 필수 필드·enum·역링크 대칭·엣지 endpoint를 검사한다. 중복 개념은 LLM이 찾아 병합을 "추천"만 한다.

## 축별 분석

### A schema

- 누가 정하나: [확인] 사람이 YAML을 고친다. `runtime/CLAUDE.md:21` "Every change below is **YAML-only, zero Python change**." 코드 생성 단계도 없다(`runtime/CLAUDE.md:5` "No codegen step").
- 파일·형식:
  - `runtime/schema/entities.yaml` — 페이지 종류 9개(papers, concepts, topics, people, ideas, methods, experiments, Summary, foundations). 필드마다 `type`·`required`·`values`·`range`·`to`(링크 대상 종류)·`required_when`을 적는다. ideas·experiments에는 `lifecycle.transitions` 상태 기계가 있다(`entities.yaml:97-101`, `:157-160`).
  - `runtime/schema/edges.yaml` — 엣지 16종. 논문↔논문 4, 논문→개념 4, 작업 흐름 7, `cites` 1. 각 엣지는 `endpoints {from, to}`, `direction`, `attributes`를 갖는다. 의미 엣지 8종은 `confidence`와 `evidence`가 `required: true`다(`edges.yaml:25-91`).
  - `runtime/schema/xref.yaml` — 정방향 링크를 쓰면 반대편에 무엇을 써야 하는지 규칙 14개.
  - `runtime/policy/writers.yaml` — skill별 쓰기 권한. 단 "STATUS: SPEC, NOT A RUNTIME GATE"(`writers.yaml:3`)다. 코드는 이 파일을 읽지 않는다.
- 강제 방식:
  - 엣지: [확인] 쓰기 직전 코드 검증이다. `research_wiki.py add_edge`(`:275-309`)는 `VALID_EDGE_TYPES`에 없는 종류를 `"Unknown edge type"`으로 거부한다. endpoint 위반·자기 자신 연결·legacy 종류·필수 속성 누락도 `_semantic_edge_errors`(`:246-252`)로 모아 `sys.exit(1)`한다. 검사 규칙은 `runtime/loader.py:165-220`이 YAML에서 바로 만든다.
  - 구멍 1: [확인] 엣지 끝점 페이지가 없어도 경고만 내고 쓴다(`research_wiki.py:311-315` `_validate_node_refs` → stderr).
  - 구멍 2: [확인] `VALID_EDGE_TYPES`에 legacy `extends`·`supersedes`가 들어 있다(`loader.py:56`, `:198`). 이 둘은 spec이 없어서 endpoint 검사를 통과한다(`loader.py:166-168` "if not spec: return True"). 단 새 쓰기에서는 `legacy_check=True`가 papers→papers 연결의 두 종류와 papers→concepts 연결의 `extends`를 막는다(`loader.py:57-58`, `:175-180`, `research_wiki.py:225-226`). 그래서 통과하는 경로는 그 밖의 종류 조합(예: concepts→concepts)뿐이다.
  - 페이지 frontmatter: [확인] 쓰기 전 코드 검증이 없다. LLM이 파일을 직접 쓴다. 검사는 사후 `lint.py`(`check_missing_fields :173`, `check_field_values :242`)뿐이다. 추출 프롬프트 쪽은 skill 문서가 schema 파일을 열라고 지시하는 방식이다(`ingest/SKILL.md:18`, `:133`). 구조화 출력(JSON schema)은 쓰지 않는다.
  - 논문용 `paper` 브랜치(tag `arxiv-v1`)에는 `tools/trust_guard.py`가 있다. [확인] 이 도구는 lint 결과와 별도 리뷰 LLM 판정을 PASS/WARN/BLOCK으로 합친다(`trust_guard.py:2-7`). 그러나 대상 파일이 이미 있어야 돌고(`:98-102`), BLOCK이면 `raw/tmp/quarantine/`에 "Copy"할 뿐 원본을 지우지 않는다(`:125-137`). 즉 쓴 뒤 검사다. main에는 이 파일이 없다.

### B 용어집

- [확인] 별도 용어집 파일은 없다. 별칭은 페이지 frontmatter의 `aliases: list_str`에 산다. 이 필드는 concepts(`entities.yaml:40`)와 foundations(`:180`)에만 있다. methods·people·topics에는 없다(`:103-120`, `:63-76`, `:52-61`). 그런데 `ingest/SKILL.md:162`는 방법 중복을 "manual title/alias compare"로 하라고 한다. 방법 쪽에는 대조할 별칭 필드가 없다.
- 누가 쓰나: [확인] 개념 별칭은 `/ingest`의 LLM이 쓴다. 병합할 때 "append `key_papers`, aliases, variants"(`ingest/SKILL.md:47`). foundation 별칭은 `/prefill`의 LLM이 "list any common aliases the LLM is confident about"(`prefill/SKILL.md:79`)으로 쓴다. 사람은 `/edit`로 고칠 수 있다. 사람이 미리 쓰는 시드는 foundation 목록 23개(`prefill/foundations-catalog.yaml`)뿐이다. 이 목록에는 별칭이 없다.
- 언제 쓰나: [확인] 추출 전 프롬프트에 용어 목록 전체를 넣지 않는다. LLM은 `wiki/index.md`로 기존 slug를 읽는다(`ingest/SKILL.md:36`). 개념 후보가 나올 때마다 `find-similar-concept`가 후보 이름+별칭을 기존 제목+별칭과 대조한다(`research_wiki.py:1090-1122`). 추출 "중", 생성 "직전"의 대조다. 추출 뒤 일괄 정규화 단계는 없다. 엣지는 이름이 아니라 slug를 가리키므로 관계 이름이 흩어질 여지 자체가 schema로 막힌다.
- 대조 방법: [확인] 결정적 토큰 매칭이다. 정규화 후 완전 일치 1.0, 짧은 쪽이 2단어 이상이고 포함되면 0.85다. 나머지는 내용어 Jaccard로 매긴다. Jaccard가 0.7 이상이면 그 값을 그대로 쓴다. 0.4~0.7이면 0.40~0.55로 줄인다. 0.4 미만은 버린다(`research_wiki.py:1030-1035`). 주석은 "0.40-0.84 Jaccard similarity of content tokens, scaled"(`:978`)라고 적지만 코드와 다르다. 그래서 Jaccard만으로 0.80 병합 문턱을 넘으려면 내용어 Jaccard가 0.8 이상이어야 한다. 임베딩은 쓰지 않는다. 주석이 "tuned for high recall — the LLM caller does the final semantic judgment"(`:964`)라고 밝힌다.

### C 원문 연결 범위

- [확인] 단위는 논문이다. 개념 페이지는 `key_papers: list_link to papers`(`entities.yaml:45`)로 논문 목록을 가리킨다. 방법은 `source_papers`(`:115`)다. 청크·문장 위치를 가리키는 필드는 어느 종류에도 없다.
- 처음 본 곳만인지 모든 곳인지: [확인] 모든 논문이 원칙이다. 병합 경로는 "Append this paper to the existing page's `key_papers`"(`dedup-policy.md:36`)다. 그래서 개념을 쓰는 논문마다 `key_papers`가 늘어난다. 단 [추정] "모든 곳"은 LLM이 그 논문에서 그 개념을 후보로 뽑았을 때만이다. 언급된 개념을 빠짐없이 후보로 올리라는 지시는 없다(`ingest/SKILL.md:161` "For each candidate concept"). 논문당 생성 한도 때문에 빠지는 논문도 생길 수 있다 — 사례: 한도 초과 후보는 "skip writing that entity"(`dedup-policy.md:52`) 1건. ("When in doubt, skip"(`cross-references.md:81`)은 논문↔논문 의미 엣지 규칙이라 개념 연결과는 무관하다.)
- 원문 파일 연결: [확인] 논문 페이지에는 raw 경로 필드가 없다. 정체는 `arxiv`·`s2_id`·slug로 잡는다(`entities.yaml:20-34`). 엣지의 `evidence`는 자유 문자열이다(`edges.yaml:31`). 원문 인용인지 위치인지 형식을 정하지 않는다.

### D 새/기존 연결

새 논문을 넣을 때 기존 페이지와 잇는 절차는 다음과 같다. [확인] 근거는 `ingest/SKILL.md:105-190`과 `dedup-policy.md:31-52`다.

1. 논문 자체: slug와 arXiv ID·제목이 같으면 멈춘다(`SKILL.md:113`).
2. 개념: 후보 제목과 `--aliases`로 `find-similar-concept`를 부른다. 이 도구는 `wiki/foundations/`와 `wiki/concepts/`를 함께 훑는다(`research_wiki.py:1107-1110`).
   - 1위가 foundation이고 점수 ≥ 0.40 → foundation에 `derived_from` 엣지만 붙인다.
   - 점수 ≥ 0.80 → 병합. 기존 개념의 `key_papers`에 붙인다. `uses_concept`(기본) / `extends_concept` / `critiques_concept` 엣지를 붙인다. 논문 쪽 `## Related`에 역링크를 쓴다.
   - 0.40~0.80 → LLM이 기존 `## Definition`을 읽고 판단한다. 기본은 병합이다. 하위 종류면 `## Variants`에 한 줄 붙인다.
   - < 0.40 → 생성 가능(한도 안에서).
   - [확인] 도구는 foundation 결과를 점수와 무관하게 맨 앞에 정렬한다(`research_wiki.py:1114-1117`). 반환되는 결과는 모두 0.40 이상이다(`:1067`). 그래서 foundation이 하나라도 걸리면 1위는 언제나 foundation이다. [추정] 정책을 위에서부터 적용하면, 개념과 1.0으로 일치해도 foundation과 0.42로 겹치면 foundation 연결로 간다 — 사례: 정렬 코드 1개와 정책 첫 줄(`dedup-policy.md:35`) 1개. 실제 LLM이 그렇게 고르는지는 실행 기록을 봐야 안다.
3. 방법: 도구가 없다. LLM이 `wiki/methods/*.md`의 이름·태그·`## Mechanism`을 읽고 판단한다(`dedup-policy.md:27`).
4. 사람: 기존 저자 페이지의 `## Recent work`에 붙인다. 새 페이지는 importance ≥ 4일 때만이다.
5. 주제: 논문 태그와 기존 topic 페이지 태그를 맞춘다(`SKILL.md:185`).
6. 논문↔논문: Semantic Scholar 참고문헌의 arXiv ID·제목이 기존 논문 페이지로 풀리면 `cites`를 붙인다(`SKILL.md:178`). 원문 단서가 분명할 때만 의미 엣지를 붙인다.
7. 역링크: 정방향을 쓰면 같은 턴에 반대편도 쓴다(`xref.yaml`). 빠지면 `/check --fix`가 결정적으로 채운다.

[확인] 임베딩 검색이나 확률적 entity resolution은 없다. 연결은 별칭 토큰 대조, 태그 일치, 외부 ID(arXiv·S2) 일치 세 가지로 생긴다.

### E 새 용어

- 개념: [확인] 대기열 없이 LLM이 바로 만든다. 단 논문당 한도가 있다. importance < 4면 새 개념 1·새 방법 1, ≥ 4면 3·2다(`ingest/SKILL.md:251-254`, `dedup-policy.md:48-50`). 한도를 넘는 후보는 "merge them into the nearest existing entry even if its score is below the usual merge threshold"이거나 버린다(`dedup-policy.md:52`).
- 근거: [확인] 과다 병합이 과다 생성보다 싸다는 판단이다. "Over-merging is cheap to undo ... Over-creating is expensive"(`dedup-policy.md:42`).
- topic·foundation: [확인] `/ingest`는 만들지 못한다. topic은 `/init`·`/edit`만(`SKILL.md:189`), foundation은 `/prefill`만 만든다(`init/SKILL.md:230`). foundation 후보로 보이는 새 용어도 일반 개념으로 처리한다(`cross-references.md:27`).
- 새 엣지 종류: [확인] 도구가 거부한다(A 참고). `contribution_type` 값은 닫힌 집합이고 "Do not invent new values"(`SKILL.md:138`)지만 프롬프트 규칙일 뿐이다.
- 사람 승인: [확인] `/check`가 중복 개념·방법을 LLM으로 찾아 "merge recommendations"를 낸다(`check/SKILL.md:134-135`). `--fix`는 결정적 문제만 고치고 나머지는 "for user approval"로 남긴다(`check/SKILL.md:174`). 승인 대기열 파일은 없다. 보고서가 대기열 역할을 한다.

### F 범용어 허브

- foundation 계층: [확인] 교과서 수준 개념을 `terminal: true` 종류로 둔다(`entities.yaml:173`). 장치는 넷이다.
  1. 페이지 역링크를 쓰지 않는다. `xref.yaml:78` `terminal_targets: [foundations]`. foundation 페이지에는 `key_papers`가 없다.
  2. frontmatter 링크를 그래프 엣지로 투영할 때 foundation을 건너뛴다(`research_wiki.py:610`).
  3. 대조 결과 정렬에서 foundation을 점수와 무관하게 앞에 둔다(`research_wiki.py:1114-1117`). foundation으로 보내는 문턱(0.40)이 개념 병합 문턱(0.80)보다 낮다(`dedup-policy.md:35-36`). 범용어가 개념 페이지로 들어오기 어렵게 기운 설계다.
  4. 성숙도 통계에서 뺀다(`research_wiki.py:1515-1520`).
- 막지 못하는 곳: [확인] `derived_from` 엣지는 `edges.jsonl`에 그대로 쌓인다. `neighbors`(`research_wiki.py:1184-1236`)는 terminal 여부를 보지 않고 모든 엣지로 BFS한다. 그래서 논문 A → foundation X ← 논문 B는 depth 2 탐색에서 A와 B를 잇는다. [추정] 사용자 실험의 "KG, schema, LLM" 허브를 foundation으로 옮겨도 이 탐색 방식이면 엉뚱한 연결은 그대로 생긴다 — 사례: 위 BFS 코드 1개.
- 반대로 작동하는 곳: [확인] `compile_context`는 방법을 연결 수 내림차순으로 보여 준다(`research_wiki.py:1278-1291`). 허브를 앞에 세운다.
- 프롬프트 규칙: [확인] 논문↔논문 의미 엣지에 "If the same statement would be true for dozens of papers in the wiki, skip the paper-to-paper edge"(`cross-references.md:58-60`)가 있다. "attention", "uses transformers" 같은 넓은 영역 근거를 금지한다(`:64-65`). 이것은 LLM 판단에 맡긴 규칙이다.
- 없는 것: [확인] 빈도 기반 stoplist나 문서 빈도 문턱은 없다. `STOP_WORDS`(`research_wiki.py:92-97`)는 "the", "of" 같은 기능어 34개뿐이다. foundation 목록 23개는 사람이 고른 것이고 "catalog is advisory"(`prefill/SKILL.md:141`)다.

### G 엔티티·이벤트

- [확인] 원문에서 이벤트를 뽑지 않는다. 페이지 종류는 모두 엔티티(논문·개념·방법·사람·주제)거나 사용자 자신의 연구 작업(idea·experiment)이다.
- 시간축은 속성으로만 있다. 논문 `year`·`date_added`, 엣지 `date`(`research_wiki.py:343`), 개념 `first_introduced`. idea·experiment는 상태 기계가 있다. `research_wiki.py transition`이 불법 전이를 거부한다. 이 명령은 `entities.yaml`의 `lifecycle.transitions`에서 바로 만든 `TRANSITIONS` 표를 쓴다(`research_wiki.py:1591-1595`, `:1630-1637`). `loader.py:225-237`의 `validate_lifecycle_transition`은 import만 되고 이 명령에서 불리지 않는다.
- `wiki/log.md`는 wiki 조작 기록이다. 원문 속 사건 기록이 아니다.

### H 근거 수치

- [확인] 없다. 논문 "AutoSci: A Memory-Centric Agentic System for the Full Scientific Research Lifecycle"(arXiv 2605.31468)을 읽었다. §7.2 "Structured Memory Construction"은 메모리 그래프 예시 그림만 보인다. Table 2는 "10 typed entities; 20+ typed relations" 같은 schema 규모다. 메모리 유무 ablation, 중복률, 링크 정밀도, 검색 성능 측정은 찾지 못했다. Trust Guard도 설명만 있고 평가가 없다.
- [확인] 대조 점수 문턱(0.40/0.80/0.85)과 생성 한도(1/3)에 보정 데이터가 붙어 있지 않다. 저장소 `tests/`에는 `test_hiera_local.py` 하나뿐이고 품질 측정은 없다.
- [확인] 논문 §3.3은 "All SciMem writes pass through Trust Guard before entering the usable graph"라고 쓴다. 그러나 `arxiv-v1`의 `trust_guard.py`는 이미 쓴 파일을 검사하고 BLOCK이면 사본만 격리한다(A 참고). main에는 이 도구가 없다. 논문의 "쓰기 전 관문" 서술은 코드보다 강하다.
- 확인 방법: 처음에는 arXiv HTML 본문을 WebFetch로 두 번 읽었다. 검증 단계에서 HTML을 내려받아 텍스트로 바꾼 뒤 §7.2 전문, Table 2, "ablation"·"duplicate"·"merge" 등장 위치를 직접 확인했다. ablation은 GPU kernel 실험(metric feedback)에만 있고 메모리 쪽에는 없다.

## 가져올 것

라이선스는 MIT다. 코드와 문서를 고지만 남기고 가져와도 된다.

1. schema를 YAML로 두고 loader가 검사 규칙을 만드는 구조. `edges.yaml`의 `endpoints`+`required` 속성 → `loader.py` → `add_edge` 거부. 사용자 실험의 관계 17종을 이 형식으로 옮기면 관계 이름 정규화를 "추출 뒤"가 아니라 "쓰기 직전 거부"로 바꿀 수 있다. 단 페이지 쪽도 쓰기 직전에 검사해야 한다. AutoSci는 페이지 검사를 사후 lint에 맡겨서 구멍이 있다.
2. 생성 직전 대조 도구. `find-similar-concept`는 120줄 남짓의 결정적 코드다. 이름+별칭을 함께 대조하고 판단 근거(`match_reason`)를 돌려준다. 사용자의 용어집(정식 이름+별칭 150개)을 그대로 입력으로 쓸 수 있다.
3. 범용어 계층과 낮은 문턱. 사용자 허브(KG, schema, LLM, 용어 추출)를 foundation처럼 terminal 종류로 미리 등록한다. 그 용어로 가는 문턱을 일반 개념 병합 문턱보다 낮게 둔다. 단 AutoSci가 놓친 부분을 채워야 한다. 새/기존 연결을 셀 때와 그래프 탐색을 할 때 terminal 노드를 경유하는 경로를 빼야 한다. 그래야 정밀도 0.37 문제가 풀린다.
4. 문서당 생성 한도와 "기본은 병합". 새 용어가 마구 늘어나는 것을 막는 단순한 장치다. 사용자의 "어느정도 사람이 하더라도" 목표와 맞게, 한도 초과분을 버리지 말고 승인 대기열 파일로 보내는 쪽이 낫다. AutoSci는 보고서로만 남긴다.
5. 원문 연결은 가져오지 않는다. AutoSci는 논문 단위다. 사용자의 "이름이 나온 모든 청크로 링크" 방식이 더 세밀하다. 대신 `key_papers`처럼 "만날 때마다 목록에 붙인다"는 원칙은 사용자의 재현율 0.92 수정과 같은 방향이다.

## 출처

- 저장소: https://github.com/skyllwt/AutoSci (main)
- 읽은 commit: `f5c2fe009c6683b6aa5b668de759a0610c938aaf` (2026-10-02)
- 로컬 사본: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/skyllwt_AutoSci`
- 논문 브랜치: tag `arxiv-v1`, commit `6bc834a805a1744959a9983809e5d6f0263ef791`. `tools/trust_guard.py`, `i18n/en/skills/dream/references/memory-operations.md`만 `gh api`로 읽었다.
- 논문: https://arxiv.org/abs/2605.31468 (HTML 본문 https://arxiv.org/html/2605.31468)
- 라이선스: MIT (`LICENSE`, "Copyright (c) 2026 OmegaWiki Contributors")
- 코드는 실행하지 않고 읽기만 했다.

## 검증 기록

2026-10-11에 다른 에이전트가 반박 검증을 했다. main `f5c2fe0`(원격 main과 같음)과 tag `arxiv-v1`(→ `6bc834a`)을 다시 열었다. 논문 HTML은 내려받아 직접 검색했다. 코드는 실행하지 않았다.

### 그대로 확인된 것

- schema는 사람이 정한다. 페이지 9종(`entities.yaml`), 엣지 16종(`edges.yaml:25-151`, 4+4+7+1), 의미 엣지 8종의 confidence·evidence `required: true`, "YAML-only, zero Python change"(`runtime/CLAUDE.md:21`), "No codegen step"(`:5`)이 모두 원문 그대로다. LLM이 schema를 만드는 단계는 없다.
- 별칭은 LLM이 쓴다. 사람이 미리 쓰는 것은 foundation 23개 목록(별칭 없음)뿐이다. 보고서가 이를 부풀리지 않았다.
- `add_edge`의 거부(`research_wiki.py:275-309`), 끝점 페이지 부재 시 경고만(`:311-315`), `writers.yaml:3` "SPEC, NOT A RUNTIME GATE", frontmatter 투영에서 terminal 제외(`:610`), foundation 우선 정렬(`:1114-1117`), terminal 무시 BFS(`:1184-1236`), 연결 수 정렬(`:1278-1291`)이 원문과 맞다.
- 새/기존 연결 절차: `ingest/SKILL.md`(:113, :161-165, :178, :185, :189, :251-254)와 `dedup-policy.md`(:27, :35-38, :42, :48-52)의 인용이 모두 맞다. `check/SKILL.md:134-135`, `:174`, `init/SKILL.md:230`, `prefill/SKILL.md:79`, `:141`도 맞다.
- 원문 연결이 논문 단위라는 점(`key_papers`, `source_papers`, 위치 필드 없음, `evidence`는 자유 문자열)이 맞다.
- 논문에 메모리 품질 수치가 없다는 점이 맞다. §7.2는 정성 설명과 그림 하나뿐이다.

### 고친 것

| 자리 | 원래 | 고친 뒤 | 근거 |
|---|---|---|---|
| B 대조 방법 | Jaccard를 0.40~0.84로 "늘린다" | ≥0.7은 그대로, 0.4~0.7은 0.40~0.55로 줄인다. 주석의 0.40-0.84는 코드와 다르다 | `research_wiki.py:1030-1035`, `:978` |
| A 구멍 2 | legacy `extends`·`supersedes`가 endpoint 검사를 통과한다 | papers→papers 연결과 papers→concepts 연결의 `extends`는 legacy 검사가 막는다. 그 밖의 조합만 통과한다 | `loader.py:57-58`, `:175-180`, `research_wiki.py:225-226` |
| C 빠지는 논문 근거 | "When in doubt, skip"(`cross-references.md:154`)을 개념 누락 이유로 듦 | 이 규칙은 논문↔논문 엣지용이라 뺐다. 그 대신 "모든 개념을 후보로 올리라"는 지시가 없다는 점을 적었다 | `cross-references.md:81` |
| D 개념 결정 | foundation ≥0.40이면 foundation 연결 | 덧붙임: foundation이 하나라도 걸리면 1위가 되므로, 개념 1.0 일치보다 foundation 연결이 먼저 적용될 수 있다 | `research_wiki.py:1067`, `:1114-1117`, `dedup-policy.md:35` |
| G 상태 기계 | `transition`이 `validate_lifecycle_transition`(`loader.py:225-237`)으로 검증 | `transition`은 YAML에서 만든 `TRANSITIONS` 표를 직접 쓴다. `validate_lifecycle_transition`은 import만 된다 | `research_wiki.py:1591-1595`, `:1630-1637` |
| F 기능어 수 | `STOP_WORDS` 32개 | 34개 | `research_wiki.py:92-97` |
| 줄 번호 | `cross-references.md:131-133`, `:137-138`, `:100`, `:154`, `xref.yaml:235` | `:58-60`, `:64-65`, `:27`, `:81`, `xref.yaml:78` | 파일이 각각 98줄, 78줄이다 |
| H | Trust Guard는 설명만 있다 | 덧붙임: 논문은 "쓰기 전에 통과"라고 쓰지만 코드는 쓴 뒤 검사다 | 논문 §3.3, `trust_guard.py:100-137` (`arxiv-v1`) |

결론은 바뀌지 않는다. 사람이 정한 YAML schema는 실재하고 엣지 쓰기에서 강제된다. 용어집은 따로 없고, 별칭은 LLM이 쓴다.

# 7단계 아키텍처 실행 약속

이 글은 7단계(아키텍처별 실행)를 맡은 에이전트가 모두 따르는 약속이다. 공통 조건(모델, 임베딩, 채점, 프로세스 정리)은 `net-arch-progress.md` #공통 조건 이 정한다. 안의 설계는 `net-arch-menu.md` #조합안 이 정한다. 여기서는 그 둘 사이의 실행 약속만 적는다.

## 입력

| 입력 | 위치 | 비고 |
|---|---|---|
| 말뭉치 | `inputs/net-corpus/docs.jsonl` v2 (680건) | 합성 문서가 나오면 `docs-all.jsonl` 로 바꿔 다시 돌린다 |
| 정답 | `inputs/net-corpus/gold/questions.jsonl` (250문항, 근거 있는 것 221) | 정답·`answer`·`answer_path` 는 색인과 질의 코드에 넣지 않는다. 채점에만 쓴다 |
| 단위 | `runs/23-net-units/{fixed,doc,section,claim}.jsonl`, `section-tree.jsonl` | 단위마다 `doc_id,start,end` 가 docs v2 문자 위치다 |
| 단위 벡터 | `runs/23-net-units/idx/emb-<단위>.npy` + `.ids.json` | st-cuda bge-m3, 행 노름 1 |
| 용어집 | `inputs/net-corpus/glossary/` (6단계, 나오는 중) | 안 1·2·4·5·6 이 쓴다 |
| 공유 코드 | `lab/23_arch_common.py` (arch-base 가 만든다) | 단위·벡터 읽기, dense 검색, 글자 예산 담기, 결과 쓰기, fallback |

### 공유 코드 함수

`lab/` 에서 `.venv-hr2/bin/python`(numpy)으로 돌리고 `arch = importlib.import_module("23_arch_common")` 로 부른다. 쓰는 예는 `lab/23_arch_b0.py`.

| 함수 | 하는 일 |
|---|---|
| `read_questions()` | `Question(qid, question, lang)` 목록. answer·answer_path·evidence·type 은 읽지 않는다 |
| `write_questions_only(path, qs)` | 질문만 담은 `{id, question}` jsonl (외부 스크립트 입력용) |
| `read_docs()`, `span_text(doc, s, e)` | docs v2 를 doc_id 로, 문자 위치의 글 |
| `load_units(kind)` | `Units`: 단위 행 + idx 벡터. ids 순서가 다르면 jsonl 순서로 맞추고, 집합이 다르거나 노름이 1 이 아니면 멈춘다 |
| `Units.search(qvec, among=None, top=None)` | cosine 내림차순 `[(행, 점수)]`. `among` 은 unit_id 나 행 번호 모음(후보 부분집합) |
| `Units.dense_units(qvec, path_stages, among, top)` | 위 결과를 단위 dict(`doc_id,start,end,score,path,unit_id`)로. path 끝에 `unit=<종류>` 를 붙인다 |
| `Units.covering(doc, s, e)`, `Units.as_unit(i, score, path)` | 구간과 겹치는 단위(부모 청크 찾기), 행 하나를 단위 dict 로 |
| `embed_questions(qs)` | `embed_client.embed` 로 질문 벡터 (캐시 공유) |
| `path(*stages, unit=)`, `FALLBACK_PATH` | `glossary=AMF>abstraction=NF>unit=claim`, `fallback=dense>unit=fixed` |
| `fill_budget(ranked, 5000, 5)` | 같은 구간 빼고 글자 5000 이상·5단위 이상까지 앞에서 담기 |
| `without_overlaps(units)` | 앞서 담은 단위와 글자 구간이 겹치는 단위를 뺀다 |
| `rrf(*rankings, k=60)` | 순위 목록 여럿을 RRF 로 합친다. 같은 구간은 한 번, 먼저 나온 목록의 path 를 남긴다. B2 섞기 기준선이 쓴다 |
| `fill_with_fallback(own, qvec)` | 안의 단위로 못 채우면 dense fixed 를 `fallback=dense>unit=fixed` 로 덧붙임. `(단위, fallback 단위 수)` |
| `llm_record(client, prompt, system)` | ClaudeClient 캐시 항목의 첫 호출 초·비용 (질문별 trace 용) |
| `Run(name)` → `.add(qid, variant, units, **trace)`, `.write()`, `.score()` | `runs/23-arch-<name>/` 에 retrieval·trace jsonl, `23_score.py` 로 score.txt·detail.jsonl |
| `report_tables(run_dir, variant)` | 유형별 표, B0(`23-arch-b0-dense` 의 `dense`) 대비 유형×예산 승패와 p, 첫 단계별·unit 종류별 찾은 묶음, fallback 만 찾은 묶음, trace 요약. 다른 기준과 견주려면 `compare_table(run_dir, variant, base_dir, base_variant)`. CLI: `.venv-hr2/bin/python 23_arch_common.py <run_dir> <variant>` |

## 산출

판마다 `runs/23-arch-<이름>/` 하나를 쓴다. 이름은 `b0-dense`, `b1-hr2`, `a1-glossary`, `a2-abstraction`, `a3-section`, `a4-table`, `a5-pprglossary`, `a6-page`, `a7-router`, `a8-agent`, `o1-ontology` 다.

| 파일 | 내용 |
|---|---|
| `CONFIG.md` | 실행 전에 적은 설정값(상위 몇 개, 문턱, 배율, 프롬프트 파일). 실행 뒤에 바꾸면 바꾼 이유와 함께 새 판으로 적는다 |
| `retrieval.jsonl` | `23_score.py` 입력 형식. 단위는 순위 순으로 최소 5000자 예산을 채울 만큼 낸다 |
| `trace.jsonl` | 질문마다 경로 기록: 질문 파싱 결과, 연결된 용어집 entry·개념, 각 단계 후보 수, 빈 단계, fallback 여부, LLM 호출 수·비용·초 |
| `score.txt` | `python3 23_score.py retrieval.jsonl ../../inputs/net-corpus/gold/questions.jsonl --detail detail.jsonl` 의 출력 |
| `REPORT.md` | 유형별 결과, B0 대비 문항 승패, 경로별로 정답을 가져온 수, fallback 이 가져온 수, 색인·질의 비용, Opus 검토 호출 수와 판단 수 |

## path

path 는 단계를 `>` 로 잇고 첫 단계 종류는 메뉴 표의 "path 첫 단계" 다. 마지막에 단위 종류를 `unit=<fixed|section|claim|doc|record|page>` 로 붙인다. fallback 으로 온 단위는 `fallback=dense>unit=fixed` 처럼 첫 단계를 `fallback` 으로 쓴다. 채점기는 첫 단계 종류로 묶어 세므로, 이 규칙을 지켜야 "그 안의 경로가 찾았나" 와 "fallback 이 찾았나" 가 갈린다.

## 비교

- 주된 비교는 B0(dense 고정 청크) 대비 같은 문항 승패다. claim·record 같은 짧은 단위를 고정 청크와 섞는 판은 B2(`runs/23-arch-b2-mix/`) 대비 승패도 낸다. 처음에는 안 4 이득의 약 3/4 이 섞기에서 왔다고 봤지만(`runs/23-arch-a4-table/REPORT.md` #섞기 대조 판), claim·fixed RRF 섞기(B2 `mix-claim-fixed`)는 B0 를 넘지 못했다(5000자 0.373 대 0.400). 그래서 지금 가설은 "무엇을 임베딩하는가"(제목·한국어 칸 값·발췌 묶음을 함께 임베딩하고 원문 구간을 돌려줌)다. 분해 판은 `a4-embedtext-*`, `b2-mix` 의 `claim-ctx*` 이다. 유형마다 따로 낸다. 집계 유형은 2500/5000자 예산을 주된 값으로 본다.
- 안 안에서 문턱·배율을 여러 값으로 돌리지 않는다. 한 판에 한 설정이다. 구조를 바꾼 변형(예: 부모 청크를 붙임/안 붙임)은 이름을 달리해 별도 판으로 낸다.
- 안의 장치가 실제로 일했는지를 함께 적는다: 경로가 빈 문항 수, fallback 이 정답을 가져온 수.

## 비용과 정리

- LLM 은 `lab/llm_cache.py` 의 `ClaudeClient` 로만 부른다(디스크 캐시 공유). Haiku 는 색인·질의, Opus 는 사람 검토 대리.
- 판 하나에 LLM 비용이 $30 을 넘을 것 같으면 실행 전에 team-lead 에 추정과 함께 알린다.
- 임베딩은 `lab/embed_client.py` 의 `embed()` 로만 부른다. 질문 벡터도 같은 캐시를 쓴다.
- 자기가 띄운 PID 와 그 자식만 멈춘다.
- 하네스가 보고 파일 쓰기를 막으면 Bash 로 돌아가지 않는다. 본문 전체를 team-lead 에 메시지로 보내면 team-lead 가 쓴다.
- 끝나면 `net-arch-progress.md` 의 7단계 기록에 판마다 한 묶음을 덧붙이고 team-lead 에 보고한다.

## 용어집 판 약속 (2026-10-13 추가)

- 기준은 `claim-ctx`(`runs/23-arch-b2-mix/` variant `claim-ctx`, 5000자 0.530, 벡터 `runs/23-arch-b2-mix/idx/emb-claim-ctx.npy`)다. 용어집 판은 이 위에 얹고, 주된 비교는 claim-ctx 대비 문항 승패다(유형별·언어별). B0 대비 표도 함께 낸다. claim-ctx 를 쓰지 않는 판(안 4 `a4-table`)은 자기 raw 판이 기준이다.
- 용어집은 `inputs/net-corpus/glossary/glossary.json`·`hierarchy.json`, 태거는 `lab/23_glossary_tag.py` 의 `GlossaryTagger`(`tag_span`, `tag_text`)다. 용어집은 Opus 가 사람 대리로 관리했다(`CURATION.md`). 용어집을 만든 쪽은 정답·질문을 보지 않았다.
- 판마다 trace 에 질문에서 연결된 entry·개념, 펼친 하위 항목, 용어집이 바꾼 것(후보 거르기·질의 확장·태그)과 그 결과가 빈 경우를 남긴다. path 첫 단계는 메뉴 표의 `glossary`·`abstraction`·`ppr:glossary` 다.
- "용어집이 일했나" 를 따로 센다: 질문에 entry 가 하나도 안 걸린 문항, 걸렸지만 결과가 claim-ctx 와 같은 문항, 결과가 달라진 문항과 그 승패.
- 사람 검토(Opus) 값을 재는 대조로 "검토 없는 용어집"(Haiku 후보 묶음 `runs/23-glossary/aggregated.jsonl` 을 Opus 없이 그대로 쓴 판)을 하나 둔다. 같은 질의 구조에서 용어집만 바꾼다.

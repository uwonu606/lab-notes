# 9단계 약속: 모르는 용어 층 + 관계 용어집 + 작은 모델 문맥 카드

작성 2026-10-13, team-lead. 9단계를 맡은 에이전트가 함께 따르는 약속이다. 결과 해석은 `reports/net-arch-final.md` 에 따로 쓴다. 공통 조건(임베딩 `lab/embed_client.py`, Claude 호출 `lab/llm_cache.py`, 정답은 색인·질의 코드에 넣지 않음, 패턴 pkill 금지, 설정값은 실행 전에 적기)은 `reports/net-arch-progress.md` #공통 조건 그대로다.

## 왜 하나

8단계까지는 용어집을 검색 코드의 거르개·그래프로 시험했다. 그런데 용어집 항목 2,004개가 모두 모델이 이미 아는 공개 용어였다. 정의도 말뭉치에서 뽑은 일반 설명이었고, 답 프롬프트에는 카드가 들어가지 않았다. 그래서 "작은 LLM 이 아는 것과 우리 지식이 만나는 점" 이라는 용어집의 일은 재지 못했다.

사용자 요구(2026-10-13, 원문):

- "카드를 문맥에 넣는 쪽을 먼저쪽으로 해주고 작은 모델로 돌려봐줘."
- "claim 이름표와 레코드 표 v2 용어집 비교."
- "용오집은 그래프DB가 어떤 관계로 묶을지 모르니까 그 관계를 연결해주는 사전 관계 용어집이라고 보면 돼. 그리고 그 용어는 구심점이 되는 용어와 관계를 이을 때 관련된 용어 2 종류가 잇어. 항상 구심점 되는 용어랑만 묶일 필요는 없지만, 관계를 이을 용어에 정의되지않은 관계로는 묶일 수 없어."
- "구심점 용어는 명확한 사실을 미리 박아두는거야."

## 용어 (team-lead 의 해석, 사용자 확인 전)

| 이름 | 뜻 |
|---|---|
| 구심점 용어 (hub) | 사람이 미리 박아 둔 사실을 가진 용어. 카드 = 이름·별칭·종류·박아 둔 사실 3~6개. 박아 둔 사실은 문서보다 우선하는 권위 있는 사실로 다룬다 |
| 관계 용어 (relation) | 그래프에서 두 용어를 이을 수 있는 관계의 목록. 관계마다 이름(ko/en)·정의·앞뒤에 올 수 있는 용어 종류·예. 이 목록에 없는 관계로는 선을 만들지 않는다. 추출기가 낸 미정의 관계는 버리고 `undefined-relations.jsonl` 대기열에 센다 |
| 일반 항목 | 기존 용어집 항목 2,004개. 선의 끝이 될 수 있다. 선은 구심점 용어와만 이어질 필요가 없다(예: 결함 → 고친 버전) |
| 모르는 용어 층 | 공개 말뭉치에 씌우는 가상 사내 이름. 구심점 용어의 공개 이름을 문서에서 지우고 사내 별칭으로 바꾼다. 작은 모델과 bge-m3 가 용어집 없이는 잇지 못하게 하려는 것이다 |

## 산출 위치

| 무엇 | 경로 | 맡은 이 |
|---|---|---|
| 구심점 카드·관계 목록·관리 기록 | `inputs/net-corpus/relglossary/{hubs.json,relations.json,CURATION.md}` | rel-glossary |
| 사내화 말뭉치·단위·레코드 | `inputs/net-corpus-cf/docs.jsonl`, `runs/23-cf-units/{claim,fixed,section,doc}.jsonl`, `runs/23-cf-units/idx/`, `runs/23-cf-table/table.sqlite` | cf-layer(문서·단위·정답), arch-table(레코드) |
| 사내화 정답 | `inputs/net-corpus-cf/gold/{questions-pub,questions-alias,questions-fact}.jsonl`, `GOLD.md`, sha256 | cf-layer |
| 관계 선 | `runs/23-cf-relgraph/edges.jsonl`, `undefined-relations.jsonl` | rel-glossary |
| 작은 모델 호출 | `lab/ollama_cache.py`(캐시·재시도·호출 초 기록, `llm_cache.py` 와 같은 꼴) | small-model(arch-answer) |
| 판 | `runs/23-cf-<판>/` | 판마다 |

## 순서

1. rel-glossary: 구심점 용어 고르기 → Opus 가 카드·관계 목록을 쓴다.
2. cf-layer: 카드의 사내 별칭으로 말뭉치·단위·정답 구간을 바꾸고, 새는 공개 이름을 0 으로 확인하고, 정답을 고정한다. 동시에 small-model 은 작은 모델 실행 틀과 속도를 잰다.
3. rel-glossary 는 사내화 claim 에서 관계 선을 뽑고, arch-table 은 사내화 레코드 표를 만든다.
4. 검색 판 → 답 판 → Opus 채점 → team-lead 종합.

## 1 구심점 용어와 카드

- 고르기: 기존 용어집의 software·vendor·operator·test-event·organization·ran-component 항목 가운데, 3개 이상 문서에 나오고 정답 질문 글이나 근거 문서에 나오는 것. 40~60개. 고르는 규칙과 목록을 `CURATION.md` 에 먼저 적는다.
- 카드(Opus, 사람 대리): 사내 이름 하나 + 사내 별칭 2~3개(한국어 별명·약칭·팀 은어). 별칭은 모델이 뜻을 짐작할 수 없는 낱말로 한다(공개 이름의 철자를 비튼 것은 안 된다). 박아 둔 사실 3~6개 중 1개는 반드시 공개 정체("Open5GS 기반 5G 코어")다. 나머지는 말뭉치에서 참인 사실(만든 곳, 쓰인 행사, 다른 구심점과의 관계)이고, 사내에서만 아는 가짜 사실을 넣으면 `invented: true` 로 표시한다.
- 관계 선 뽑기(Haiku, 색인 때 일이라 운영 Qwen 32B 대리): 사내화 claim 을 문서마다 묶어 주고, 관계 목록 id 와 두 끝 용어(구심점·일반 항목·값)만 내게 한다. 선마다 나온 claim id 를 남긴다.
- 관계 목록(Opus): 20~30개. 말뭉치 표본과 구심점 목록을 보고 쓴다. 레코드 표 칸 14개(`runs/23-arch-a4-table/schema.json`)와 겹치는 관계는 칸 이름을 `record_column` 으로 적는다. 그래서 레코드 표 판이 같은 관계 목록을 쓸 수 있다.

## 2 모르는 용어 층

- 바꾸기: 구심점 용어의 정식 이름·별칭(용어집) 글자를 문서마다 사내 별칭 하나로 바꾼다. 어느 별칭을 쓸지는 문서 id 해시로 정한다(작성자마다 부르는 이름이 다른 것을 흉내 냄). 식별자·경로 안의 글자(`open5gs-ausf`, `/etc/open5gs`)도 바꾼다.
- 위치 대응: 바꾼 뒤의 문자 위치로 단위(claim·fixed·section·doc)와 레코드 칸 발췌, 정답 근거 구간을 옮긴다. claim·레코드의 LLM 글(요약·칸 값)도 같은 표로 바꾼다. 다시 추출하지 않는다. 그래서 8단계 판과 같은 단위로 견줄 수 있다.
- 새는 이름 검사: 바꾼 뒤 문서·단위·레코드에 남은 구심점 공개 이름을 센다. 0 이 아니면 정답 고정 전에 고친다.
- 정답 세 묶음:
  - `questions-pub`: 원래 250문항 글 그대로(공개 이름으로 묻는다), 근거 구간만 옮긴다.
  - `questions-alias`: 질문 속 공개 이름을 사내 별칭으로 바꾼다. 근거 문서에서 가장 많이 쓴 별칭과 다른 별칭을 고른다.
  - `questions-fact`: Opus 가 새로 쓰는 30~50문항. 구심점을 이름 대신 박아 둔 사실로 가리킨다("KT 과제용 코어 시험 베드에서 …"). 근거 구간과, 풀이에 필요한 카드 id(`needs_hubs`)를 함께 낸다.
  - 문항마다 `gold_hubs`(질문이 가리키는 구심점 id)를 둔다. pub·alias 는 바꾼 이름에서 코드로 채우고, fact 는 Opus 가 쓴다. 연결 정확도 채점에만 쓴다.
- 채점 묶음: 질문 글이나 근거 문서에 구심점이 나오는 문항(`hub_touch`)과 전체를 따로 낸다.

## 3 검색 판 (사내화 말뭉치, 정답 cf v1)

| 판 | 무엇 | 질의 LLM | 맡은 이 |
|---|---|---|---|
| `cf-orig` | 원래 말뭉치 claim-ctx(8단계 그대로, 같은 문항으로 다시 채점) | 0 | cf-layer |
| `cf-claimctx` | 사내화 claim-ctx, 용어집 없음 — 빈틈 | 0 | cf-layer |
| `cf-rewrite` | 작은 모델이 질문 + 연결된 카드를 읽고 사내 말로 검색 질의를 다시 쓴다 → claim-ctx | 작은 모델 2번(연결, 다시 쓰기) | small-model |
| `cf-relgraph` | 질문 → 구심점 연결 → 정의된 관계 선 → 선이 나온 claim, claim-ctx 와 RRF | 작은 모델 1번(연결) | rel-glossary |
| `cf-table` | 레코드 표 v2 구조, 칸 값을 구심점·관계 목록으로 정규화, 슬롯은 작은 모델이 카드를 보고 채움 | 작은 모델 1번 | arch-table |

- 질문 연결(구심점 잇기)은 모든 판이 같은 함수를 쓴다: 글자 매칭 + bge-m3 로 고른 카드 후보 20개 → 작은 모델이 고른다. 연결 정확도(`gold_hubs` 대비 정밀도·재현율)를 따로 낸다. 글자 매칭만 쓴 연결도 함께 적는다.
- 사용자가 청한 "claim 이름표와 레코드 표 v2 용어집 비교" 는 `cf-rewrite`·`cf-relgraph`(claim 길) 대 `cf-table`(레코드 길)로 낸다.

## 4 답 판 (작은 모델, 카드 문맥)

| 판 | 검색 | 카드 |
|---|---|---|
| `S-orig` | cf-orig | 없음 |
| `S0` | cf-claimctx | 없음 |
| `S1` | cf-claimctx | 연결된 카드를 답 프롬프트에 |
| `S2` | cf-rewrite | 카드 |
| `S3` | cf-relgraph | 카드 |
| `S4` | cf-table | 카드 |

- 작은 모델: `qwen3:8b`(ollama, 4비트, thinking 끔, temperature 0, num_ctx 는 입력이 잘리지 않게). 운영 Qwen 32B 의 같은 계열 작은 판이다. 8GB GPU 라서 32B 는 못 돌린다.
- 카드는 `[G1]` 처럼 번호를 달아 넣고, 박아 둔 사실은 자료보다 우선한다고 알린다. 답 형식은 8단계 free 형식에 카드 번호 인용을 더한다.
- 채점: Opus, 8단계 채점과 같은 0/0.5/1. 채점자에게 사내 별칭 ↔ 공개 이름 표와 카드를 준다(사내 이름으로 답해도 맞게 보려고).
- 문항 범위: 작은 모델 속도를 잰 뒤, 답 판 6개 × 문항 수가 하룻밤 안에 끝나는지로 정한다. 줄여야 하면 `hub_touch` 문항 + fact 전부로 줄이고, 그 규칙을 실행 전에 `CONFIG.md` 에 적는다.

## 비교와 보고

- 빈틈: `S-orig` 대 `S0`. 빈틈이 작으면 그 자체가 결과다(이 층이 모델에게 모르는 용어를 만들지 못한 것).
- 카드가 일했나: `S0` 대 `S1`(답에서만), `S1` 대 `S2`·`S3`·`S4`(검색까지). 같은 문항 승패와 부호 검정 p.
- 경로: 판마다 답을 받친 근거가 어느 path(카드, 관계 선, claim-ctx, 레코드)에서 왔는지 센다.
- 관계 용어집의 비용: 관계 목록 밖이라 버린 선 수와 종류, 카드 작성 판단 수.

## 예산

Opus 합계 $150 이하(카드·관계 약 $15, fact 문항 약 $10, 채점 약 $90~120), Haiku $15 이하. 넘을 것 같으면 실행 전에 team-lead 에 알린다.

## 인터페이스 (만든 이가 채운다)

함수·파일 형식은 만든 이가 이 절에 적는다. 팀원끼리 직접 묻고 답해도 되지만, 정한 형식은 여기에 남긴다.

- 공유 코드 경로(team-lead 결정): `23_arch_common.py` 의 `DOCS`·`UNITS_DIR`·`GOLD` 상수는 기본값을 그대로 두고, cf-layer 가 사내화 말뭉치로 바꾸는 스위치를 더한다(예: 환경 변수 `NET_CORPUS=cf` 또는 함수 인자). 기본 동작이 바뀌면 안 된다. 8단계 판을 다시 채점해 같은 점수가 나오는지 확인한다.
- 공유 코드 스위치(cf-layer, 만듦): `NET_CORPUS=cf` 를 `23_arch_common` import 전에 정하면 `DOCS`=`inputs/net-corpus-cf/docs.jsonl`, `UNITS_DIR`=`runs/23-cf-units`, `GOLD`=`inputs/net-corpus-cf/gold/questions-cf.jsonl`(pub+alias+fact), `Run(name)` 폴더=`runs/23-cf-<name>/`, 기준 판=`runs/23-cf-claimctx` 의 `cf-claimctx` 다. `NET_GOLD=<lab 기준 경로>` 는 정답 파일만 바꾼다. `Run(name, run_dir=...)` 로 폴더를 직접 줄 수 있다. `GROUP_LABEL` 에 `set`·`hub_touch` 를 더해 `type_table(run_dir, variant, by="set")` 이 된다. 기본값에서 8단계 b2-mix 를 다시 채점한 score.txt·detail.jsonl 이 바이트까지 같다.
- 위치 대응·바꾸기·새는 이름 검사(cf-layer, 만듦): `cf = importlib.import_module("23_cf_layer"); layer = cf.Layer.load()`. 모든 doc_id 인자는 원래 id 다.
  - `layer.cf_doc_id(orig_id)` / `layer.orig_doc_id(cf_id)`: doc_id 대응. 사내화 doc_id 는 `issue-001` 꼴이다(원래 id 에 공개 이름이 들어 있어서). unit_id 는 앞의 doc_id 만 바뀐다: `layer.map_unit_id(unit_id, orig_doc_id)`.
  - `layer.map_span(orig_id, start, end)` → `(cf_doc_id, start, end)`. 바꾼 이름 안에 떨어지는 끝은 바깥쪽으로 넓힌다(시작은 새 이름의 시작, 끝은 새 이름의 끝). 거꾸로는 `layer.orig_span(cf_doc_id, start, end)`.
  - `layer.replace_text(text, orig_id)`: 그 문서가 쓰는 사내 이름으로 바꾼 글. 레코드 칸 값 같은 LLM 글에 쓴다. 문서에 묶이지 않은 글은 아무 고정 문자열을 key 로 준다.
  - `layer.leaks(text)` → `[Found(start, end, hub, form)]`: 남은 공개 이름. 바꾸기보다 느슨한 규칙(4글자 이상 대소문자 무시 부분 문자열)이다. 0 이어야 한다.
  - `layer.hubs_in(orig_id, start=0, end=None)`: 그 구간에서 바꾼 구심점 id.
  - 대응표 `inputs/net-corpus-cf/layer/posmap.jsonl` 과 `Layer` 는 공개 이름을 담고 있어서 색인·질의 코드에서 쓰지 않는다. 옮기는 코드와 채점·보고 코드만 쓴다. 설정은 `runs/23-cf-units/CONFIG.md`.
- 문항 표시 옆 파일(cf-layer, 만듦): `inputs/net-corpus-cf/gold/labels.jsonl` 은 고정 정답에 qid 로 잇는 표시다(고정 해시에 들지 않음, sha256 `031d156c41a58d1c…`). 한 줄 `{qid, set, trace_hint, trace_kinds, trace_docs, rewritten}`. `trace_hint` 는 근거·near 문서(사내화)에 공개 이름 밖의 정체 흔적(`ogs_`·`ogs-` 접두, `acetcom`, `srs`+라틴 2자 이상 접두, 대소문자 무시, `23_cf_gold.TRACE_PATTERNS`)이 있음이다. `rewritten` 은 판정 메모를 본 뒤 고쳐 쓴 fact 문항이다. 채점·보고만 읽고 색인·질의 코드에 넣지 않는다. 다시 만들기 `python3 23_cf_gold.py labels`.
- `hubs.json`·`relations.json` 필드(rel-glossary, 만듦). 관리 기록은 `inputs/net-corpus/relglossary/CURATION.md`, 만드는 코드는 `lab/23_relglossary.py build`.
  - `hubs.json` = `{"meta", "hubs": [카드]}`, 카드 49장. 카드 칸: `id`(= 용어집 항목 id, 예 `open5gs`. `gold_hubs` 도 이 id), `glossary_id`(지금은 `id` 와 같음), `type`(용어집 항목 종류: software·vendor·operator·test-event·organization·ran-component), `internal_name`(사내 이름 하나), `internal_aliases`(사내 별칭 2~3개), `public_name`(용어집 정식 이름), `public_aliases`(용어집 별칭 전부), `facts`. slug 칸은 없고 cf-layer 가 `default_slug` 로 만든다.
  - `facts[]` 칸: `id`(`<카드 id>#f<n>`), `text`(한국어 한 문장), `kind`(`identity` 공개 정체 · `corpus` 말뭉치에서 참 · `invented` 사내 가짜), `invented`(bool), `source_claims`(원래 claim unit_id, 공개 이름을 품으니 프롬프트에 넣지 않는다), `related_hubs`(사실이 가리키는 다른 카드 id). 첫 사실이 늘 `identity` 이고 그 문장에만 자기 공개 이름이 있다. 나머지 사실은 다른 카드를 사내 이름(`internal_name`)으로 쓴다.
  - `relations.json` = `{"meta", "relations": [관계]}`, 관계 30개. 관계 칸: `id`(snake_case), `name_ko`, `name_en`, `definition`(한국어, 언제 성립하는지), `head_types`·`tail_types`(용어집 항목 종류 + 값 종류 `version`·`year`·`date`·`spec-id`·`test-case-id`·`error-text`·`measurement`; 구심점은 자기 항목 종류로 센다), `examples`(`"앞 | 뒤"` 2개), `record_column`(레코드 표 칸 이름 또는 null). 방향은 앞 → 뒤 하나뿐이고 거꾸로 관계는 두지 않는다.
  - `record_column` 이 있으면 늘 뒤 끝이 그 칸 값이고 앞 끝이 레코드 주체(문제나 시험 행사)다. 13개 관계가 칸 12개를 덮는다. `제품` 칸은 `affects_product`(문제 → 제품)와 `tested_product`(시험 → 제품) 둘이다. `영역`·`증상유형` 은 분류라 관계가 없다. `제조사` 칸은 `has_participant`(시험 → 참가 주체)다. 만든 곳 `made_by`, 주최 `organized_by`, 연동 `integrates_with`, 버전 `has_version` 은 칸이 없다.
  - 관계 선(`runs/23-cf-relgraph/edges.jsonl`) 한 줄: `edge_id`, `rel`, `head`·`tail`(`{node, text, type, how}`; node 는 `hub:<id>`·`entry:<용어집 id>`·`term:<정규화 글>`·`<값 종류>:<정규화 글>`), `doc_id`(사내화 id), `claims`(사내화 unit_id), `head_type_ok`·`tail_type_ok`(true·false·null). 설정은 `runs/23-cf-relgraph/CONFIG.md`.
- `lab/ollama_cache.py` 호출 꼴, 질문 연결 함수의 모듈·이름·반환 꼴, 글자 매칭만 쓴 연결(arch-answer). 아래가 정한 꼴이다.
  - `OllamaClient(model="qwen3:8b", num_ctx=8192, num_predict=1024, json_output=False, max_concurrency=1)`. `ask(prompt, system, tag)` 와 `ask_many(prompts, system, tag)` 는 `llm_cache.ClaudeClient` 와 같은 꼴이고, `Reply(text, metadata, cache_hit)` 와 실패 자리의 `LLMCallFailed` 를 돌려준다. thinking 끔·temperature 0·seed 0 은 고정이다. `json_output=True` 는 ollama `format="json"` 을 켠다. 입력이 `num_ctx - num_predict` 토큰에 닿거나 입력 초과는 다시 시도하지 않고 `ContextOverflow`(`LLMCallFailed` 의 하위)로 실패한다. 출력이 `num_predict` 에서 끊긴 답은 실패가 아니라 `metadata["finish_reason"] == "length"` 로 남는다. 캐시는 `runs/23-cache/ollama/` 이고 키는 모델·options·format·system·prompt 다. 질문별 초는 `arch.llm_record(client, prompt, system)` 로 읽고, metadata 에 `prompt_tokens`, `completion_tokens`, `prompt_eval_seconds`, `eval_seconds` 가 있다. GPU 가 하나라 동시는 1 로 둔다.
  - 질문 연결: `link = importlib.import_module("23_cf_link")`, `linker = link.Linker(link.read_cards())`, `linker.link_many([(qid, 질문 글), ...])` 가 `[Link]` 를 돌려준다. `Link` 의 칸은 `qid`, `text_hubs`(글자 매칭만 쓴 연결, 카드 id 목록), `candidates`·`candidate_scores`(글자 매칭 카드를 먼저 두고 bge-m3 cosine 순으로 채운 후보 20개와 그 cosine), `hubs`(작은 모델이 고른 카드 id), `reply`, `error`, `seconds`, `cached` 다. 작은 모델 호출은 `OllamaClient(num_predict=256, json_output=True)` 로 캐시되고, 프롬프트는 `lab/prompts/cf-link.txt` 다. 글자 매칭만 필요하면 `link.text_match(질문 글, linker.cards)` 를 쓴다. ASCII 표면은 낱말 경계로 보고(`KTX` 는 `KT` 가 아니다), 한글 표면은 부분 문자열로 본다.
  - 카드 렌더: `link.render_cards(cards, prefix="G")` 가 `[G1] 이름 (별칭: …; 종류: …)` 과 `- 박아 둔 사실` 줄을 넣은 순서대로 낸다. 답 판과 슬롯 프롬프트가 같은 꼴을 쓴다. 연결 프롬프트만 `prefix="H"` 다.
  - 명령줄: `.venv-hr2/bin/python 23_cf_link.py <질문 jsonl> [--scope scope.txt] [--score]` 는 `runs/23-cf-link/<파일 이름>.jsonl` 에 연결을 쓴다. `--score` 는 같은 파일의 `gold_hubs` 로 방법(text·model·candidates)마다 정밀도·재현율·다 맞힌 비율·정답 구심점 없는 문항에서 고른 비율을 낸다. 연결 코드는 질문 글만 보고, `gold_hubs` 는 `score_links` 만 읽는다.
  - 카드 형식: rel-glossary 꼴(`id, internal_name, internal_aliases, type, public_name, public_aliases, facts[{text, kind, invented, source_claims, related_hubs}]`)을 `card_from_row` 가 읽는다. 처음 제안한 꼴(`name, aliases, kind, public{name, aliases}`)도 받는다. 카드 글과 프롬프트에는 `facts[].text` 만 넣는다. `source_claims` 의 claim id 는 원래 doc_id 라 공개 이름을 품기 때문이다. 글자 매칭은 사내 이름·별칭과 공개 이름·별칭을 다 쓰고, 모두 대문자인 5자 이하 ASCII 약어(`BIRD`, `FRR`, `KT`)만 대소문자를 가린다.
- 문항 범위(team-lead 결정, 2026-10-13): 작은 모델을 부르는 모든 단계(연결, 다시 쓰기, 슬롯, 답)는 같은 문항 집합을 쓴다. 집합은 arch-answer 가 속도를 잰 뒤 약속 #4 규칙으로 하나 정해 `inputs/net-corpus-cf/gold/scope.txt`(qid 목록)에 적고, 실행 전에 고정한다. 작은 모델이 없는 판(cf-orig, cf-claimctx)은 전체와 이 집합을 둘 다 채점한다. GPU 순서는 연결 → 슬롯·다시 쓰기 → 답 판이고, cf-layer 의 벡터 만들기와 겹치지 않게 한다.
- 묶음 쓰임(team-lead 결정, cf v1 결과를 본 뒤): 검색 빈틈과 검색 판 승패의 주된 비교는 alias 묶음으로 한다. fact 묶음은 카드 없이도 5000자 0.744 로 찾혀서(질문이 로그 문구·숫자를 담음) 질문 연결 정확도와 답 판에 쓰고, 검색 표에는 참고로만 싣는다. pub 묶음은 작은 모델 없는 검색 판에서 공개 이름 질문의 빈틈으로 싣는다.
- GPU 차례(team-lead, 2026-10-13): ollama 를 부르는 일은 시험·smoke 를 포함해 차례를 받은 팀원만 한다. 차례는 연결(arch-answer) → 슬롯(arch-table) → 다시 쓰기·답 판(arch-answer)이고, 끝낸 팀원이 다음 팀원에게 알린다. 임베딩 서버(st-cuda)를 오래 쓰는 일(벡터 만들기)도 차례 밖에서는 하지 않는다.
- 검색 범위 넓히기(team-lead 결정, 2026-10-13, 검색 판 결과를 보기 전): 답 판 범위는 `scope.txt` 80문항 그대로다. 작은 모델을 쓰는 검색 단계(연결, 다시 쓰기, 슬롯)는 `scope-retrieval.txt` 로 넓힌다. 이 집합은 scope 80 + 근거 있는 alias 문항 전부(151 중 scope 밖)다. 이유: scope 의 alias 는 근거 있는 문항이 32개뿐이라 검색 판 승패가 갈리기 어렵다. 검색 단계는 문항당 약 75초라 넓혀도 약 2.5시간이 더 든다. 만드는 이는 arch-answer, 순서는 scope 문항을 먼저 끝낸 뒤 나머지를 sha256(qid) 순으로 잇는다. 검색 표의 주된 비교는 근거 있는 alias 151문항이다.
- 연결 결과 쓰임(team-lead 결정, 2026-10-13, 연결 80 정확도를 본 뒤): 다시 쓰기·슬롯·관계 선·답 판 S1~S4 의 카드는 실행 전 설정대로 작은 모델 고르기 `hubs` 를 쓴다. 이것이 주된 판이다. 답 판 S1-union 하나를 더한다. 이 판은 S1 과 같고 카드만 `text_hubs ∪ hubs` 에서 가져온다. 결과를 본 뒤 더한 사후 판이라 이름에 `link=union` 을 달고 보고에서 따로 적는다. 근거: 연결 80 에서 작은 모델 고르기는 alias 정밀도 0.402·재현율 0.593, fact 재현율 0.398 로 글자 매칭(fact 0.545)보다 낮았고, 합치면 alias 1.000·fact 0.909 다. 주된 판은 "작은 모델이 고른 카드"를 재고, S1-union 은 "맞는 카드가 들어가면 일하는가"를 잰다. 연결 파일이 두 방법을 다 담아 새 호출은 없고, 답 80문항(약 1.3시간)과 채점 80건이 는다.
- 답 되풀이(사용자 결정, 2026-10-14, S-orig 결과를 본 뒤): S-orig 답 80개 가운데 22개가 num_predict 768 에서 끊겼다. 원인은 답 끝 "근거 문서:" 줄에서 qwen3:8b 가 같은 문서 번호를 되풀이한 것이고, 답 본문은 멀쩡했다(3건 확인). 생성 옵션은 바꾸지 않고 7판 모두 같은 설정으로 간다. 근거: 판끼리 조건이 같아 비교가 공정하고, 반복 벌점·멈춤 조건은 답 본문이나 인용 번호를 바꿀 수 있다. 잃는 것: 판마다 약 50분, 전체 약 2.5시간. 보고에서 판별 끊김 수를 따로 싣는다.

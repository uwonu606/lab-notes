# GoogleCloudPlatform/knowledge-catalog (OKF v0.2) — 에이전트가 쓴 지식의 출처·신뢰·신선도를 런타임 없이 frontmatter 필드 몇 개로 드러내자는 형식 규약

이 보고서는 구현체가 아니라 규약 세 개를 다룬다.
주 대상은 OKF(Open Knowledge Format) v0.2 명세다.
비교 대상은 cablate/llm-atomic-wiki의 방법론과 rohitg00의 LLM Wiki v2 gist다.
축마다 각 문서가 무엇을 **처방하는지** 적는다.
처방이 코드로 실제 구현된 곳이 있으면 따로 표시한다.

경로 표기는 다음과 같다.

| 표기 | 기준 디렉터리 |
|---|---|
| `okf/SPEC.md:315` | knowledge-catalog 저장소 루트 |
| `cablate:CLAUDE.md:216` | cablate/llm-atomic-wiki 저장소 루트 |
| `rohitg00:llm-wiki.md:17` | `lab/sources/rohitg00-llm-wiki-v2-gist/` |
| `Ar9av:`, `inkeep:` 등 | `lab/repos/` 아래 해당 저장소 루트 |

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/GoogleCloudPlatform/knowledge-catalog (OKF는 `okf/` 하위) |
| 정본 위치 | https://github.com/GoogleCloudPlatform/open-knowledge-format — `okf/`는 "frozen snapshot, no longer maintained" (`okf/README.md:1-11`) |
| clone commit | `58b3370` (shallow clone, 커밋 1개만 보임) |
| 별 / 최근 push / 라이선스 | 9,437 / 2026-10-09 / Apache-2.0 (저장소 전체 기준. 별 대부분은 Knowledge Catalog 제품 몫으로 보인다) |
| 정본 저장소 | 904 / 2026-08-21 / Apache-2.0 |
| 형태 | 명세 문서 + proof-of-concept reference agent(CLI) + HTML viewer + 샘플 bundle 4개 |
| 명세 규모 | `okf/SPEC.md` 1,006줄 |
| reference agent 규모 | Python 약 1,875줄, prompt 2개 375줄, viewer JS 320줄, test 39개 926줄 |
| 샘플 | `okf/bundles/` 아래 md 78개 (ga4, stackoverflow, crypto_bitcoin, acme_retail) |
| 무관한 부분 | `toolbox/mdcode`(TypeScript 약 46,500줄), `samples/discovery` 등은 Knowledge Catalog 제품 도구다. 예외는 `toolbox/mdcode/demo/okf/`다. 이 demo는 OKF bundle을 Dataplex(Knowledge Catalog) entry로 push하고 다시 pull한다 (`toolbox/mdcode/demo/README.md:121-160`) |
| 비교 대상 1 | cablate/llm-atomic-wiki `eaf5e1d`, 별 149, push 2026-04-20, 라이선스 없음(gh api `license: null`) |
| 비교 대상 2 | rohitg00 LLM Wiki v2 gist `266b020` (2026-06-03) |

[확인] 이 저장소의 `okf/SPEC.md`는 정본 저장소의 `SPEC.md`와 한 글자도 다르지 않다.
gh api로 정본을 받아 `diff`를 돌린 결과다.

[확인] 명세에는 "conformance level"이 여러 단계로 나뉘어 있지 않다.
§11은 conformant 여부 하나만 정의한다 (`okf/SPEC.md:736-762`).
필수 조건은 세 개뿐이다.
나머지 family는 "있으면 SHOULD 따른다"는 조건부 규칙이다.

## 한 바퀴 흐름

OKF 자체는 흐름을 정하지 않는다 (`okf/SPEC.md:60-67`).
아래는 reference agent가 bundle을 만드는 실제 경로다.

1. `okf/src/reference_agent/cli.py:188-211` — `enrich` 명령이 BigQuery source와 web seed를 모아 `ReferenceRunner`를 만든다.
2. `okf/src/reference_agent/runner.py:264-279` — `enrich_all`이 source가 내놓은 concept마다 새 ADK session을 연다 (`runner.py:211-220`).
3. 각 session은 `prompts/reference_instruction.md:5-19`의 순서를 따른다. `read_existing_doc` → `read_concept_raw` → `sample_rows` → `list_concepts` → `write_concept_doc` 한 번.
4. `okf/src/reference_agent/tools/bundle_tools.py:90-191` — `write_concept_doc`이 쓰기 직전에 끼어든다. `generated`를 자동으로 채우고 (113-124), `type`만 검사하고 (126-137), web pass라면 축소 금지 guard를 건다 (143-183). 그다음 `path.write_text`로 덮어쓴다 (185-187).
5. `runner.py:281` — `run_web_pass`가 session 하나에서 web 에이전트를 돌린다. 에이전트는 `tools/web_tools.py:10-101`의 `fetch_url`로 crawl한다. 페이지마다 기존 concept 보강, `references/<slug>` 신설, 건너뛰기 중 하나를 고른다 (`prompts/web_ingestion_instruction.md:34-78`).
6. `runner.py:283-284` — `regenerate_indexes`가 디렉터리마다 `index.md`를 다시 만든다 (`bundle/index.py:49-103`). 하위 디렉터리 설명 한 줄은 LLM이 쓴다 (`bundle/synthesizer.py:26-50`).
7. Query 경로는 저장소에 없다. 명세가 소비 방식을 informative로만 적는다 (`okf/SPEC.md:505-529`, `699-719`).
8. Lint 명령도 없다. CLI 하위 명령은 `enrich`와 `visualize` 둘뿐이다 (`cli.py:63-160`). `visualize`는 `viewer/generator.py`로 trust tier, stale 여부, link graph를 계산해 HTML 한 장에 담는다.
9. `log.md`를 쓰는 코드는 없다. [확인] `okf/src` 전체에서 `log.md`를 grep해도 결과가 없다.

## 축별 분석

세 문서의 입장을 먼저 한 표로 본다.
각 축의 근거는 아래 절에 있다.

| 관심사 | OKF v0.2 | cablate | rohitg00 v2 |
|---|---|---|---|
| 정체 | 교환 형식 규약 | 개인 지식 파이프라인 방법론 + bash 3개 | 아이디어 문서 |
| 진실의 자리 | 각 concept의 `sources` + `verified` | 불변 atom 층 | 신뢰도 점수가 붙은 fact |
| 신뢰 표현 | 저장하지 않고 신호에서 유도 | `confidence` 선택 필드 | 저장된 점수, 시간에 따라 감쇠 |
| 낡음 처리 | `stale_after` 절대 시각, `status: deprecated` | atom 교체 + `superseded_by` + `_archive/` | supersession, forgetting curve |
| 링크 | 타입 없는 markdown link | `[[slug]]` | typed relationship graph |
| 강제 수단 | consumer 쪽 해석 규칙 | `lint.sh` 보고서 | 없음 |

#### 1. 실행 형태

[확인] OKF는 실행물이 아니라 형식이다.
명세는 "no required tooling"을 내세운다 (`okf/SPEC.md:10-13`).
저장·서빙·질의 인프라는 비목표로 못박았다 (`okf/SPEC.md:60-67`).

[확인] reference agent는 CLI 엔진이다.
Google ADK `Agent` 두 개로 이루어진다. BigQuery pass용과 web pass용이고, 각각 tool 5개를 묶는다 (`okf/src/reference_agent/agent.py:27-54`).
README는 이 에이전트를 "proof of concept"라고 부른다 (`okf/README.md:34-38`).

[확인] cablate는 prompt-only schema에 결정적 bash 스크립트 3개를 더한 형태다 (`cablate:CLAUDE.md`, `cablate:scripts/*.sh`).
[확인] rohitg00은 코드 없는 아이디어 문서다.

#### 2. 규칙의 위치

[확인] OKF의 규칙은 문서에 있다.
규칙의 방향은 producer를 묶기보다 consumer를 너그럽게 만드는 쪽이다.
consumer는 optional 필드 누락, 모르는 `type`, 깨진 link, `index.md` 부재를 이유로 bundle을 거부하면 안 된다 (`okf/SPEC.md:755-762`).

[확인] reference agent가 코드로 강제하는 규칙은 네 가지뿐이다.

| 규칙 | 위치 |
|---|---|
| `type` 필수 | `bundle/document.py:10`, `75-80` |
| concept id 조각은 정규식 `[A-Za-z0-9_][A-Za-z0-9_.\-]*`만 허용 | `bundle/paths.py:6-20` |
| web pass에서 `BigQuery Table`의 `# Schema` 필드 이름 집합과 `sources` 개수 축소 금지 | `tools/bundle_tools.py:139-183` |
| crawl 범위(host, path, depth, page 수)와 "crawl에서 나오지 않은 URL"의 fetch 거부 | `tools/web_tools.py:40-78` |

[확인] 축소 금지 guard는 한 방향으로만 걸린다.
web state가 없으면 guard가 꺼진다 (`tools/bundle_tools.py:143`).
그래서 BQ pass는 기존 문서를 아무 제약 없이 덮어쓸 수 있다. 테스트가 이 동작을 고정한다 (`okf/tests/test_bundle_tools.py:149`).
`enrich`를 다시 돌리면 BQ pass가 먼저 돈다 (`runner.py:276-281`).
[추정] 재실행 때 web pass가 붙인 `# Metrics`, `# Joins` 절이 BQ pass에서 사라질 수 있다 — 근거는 위 코드 경로 1건이다. 막는 것은 "refine rather than rewrite"라는 prompt 문장뿐이다 (`prompts/reference_instruction.md:7-8`).

[확인] `sources` guard는 개수만 센다 (`tools/bundle_tools.py:53-59`, `169-171`).
기존 항목 하나를 지우고 새 항목 하나를 넣으면 통과한다.
`# Schema` guard는 개수가 아니라 backtick으로 감싼 필드 이름 집합을 비교한다 (`tools/bundle_tools.py:29`, `46-50`, `149-151`).

나머지는 전부 prompt에 있다.
link는 `list_concepts` 결과만 가리킨다, URL을 지어내지 않는다, 고아 reference를 남기지 않는다 같은 규칙이다 (`prompts/reference_instruction.md:88-96`, `prompts/web_ingestion_instruction.md:86-91`, `259-263`).

[확인] cablate의 규칙은 `CLAUDE.md`에 있다.
`lint.sh`는 보고서만 쓴다.
스크립트 끝에 `exit`가 없어서 오류가 있어도 종료 코드는 0이다 (`cablate:scripts/lint.sh:156-161`).

[확인] rohitg00은 "the schema is the real product"라고 쓴다 (`rohitg00:llm-wiki.md:122-134`).
규칙의 자리를 prompt 문서로 본다는 뜻이다.

#### 3. 저장 구조

[확인] OKF bundle은 markdown 디렉터리 트리다 (`okf/SPEC.md:109-149`).
`index.md`와 `log.md`는 모든 층에서 예약된 이름이다.
디렉터리 분류는 producer가 정한다.
`references/`만 관례로 제시된다 (`okf/SPEC.md:479-485`).

OKF frontmatter 필드는 다음과 같다.

| family | 필드 | 근거 |
|---|---|---|
| 기본 | `type`(필수), `title`, `description`, `resource`, `tags` | `okf/SPEC.md:161-207` |
| provenance | `sources[]`{`id`, `resource`(필수), `title`, `author`, `usage_count`, `last_modified`}, `usage_window` | `okf/SPEC.md:287-341` |
| trust | `generated`{`by`(필수), `at`}, `verified[]`{`by`, `at`} | `okf/SPEC.md:366-399` |
| lifecycle | `status`(draft/stable/deprecated), `stale_after` | `okf/SPEC.md:412-433` |
| computation | `runtime`(필수), `parameters`, `computation`, `executor`, `attester` | `okf/SPEC.md:584-606` |

[확인] OKF에는 manifest, ledger, 해시 같은 파생 상태 파일이 없다.
신뢰 상태는 모두 각 파일의 frontmatter에 산다.

[확인] reference agent가 만드는 디렉터리는 `datasets/`, `tables/`, `references/`, `references/metrics/`, `references/joins/`다.
`datasets/`와 `tables/`는 코드가 정한다. BigQuery source가 concept id를 그렇게 만든다 (`sources/bigquery.py:65`, `85`, `106`).
`references/` 아래는 prompt가 정한다 (`prompts/web_ingestion_instruction.md:66-67`, `184-243`).

[확인] join 파일 이름 규칙도 prompt에만 있다. 두 테이블 이름을 알파벳순으로 놓고 `__`로 잇는다 (`prompts/web_ingestion_instruction.md:225-229`).
샘플은 이 규칙을 일관되게 지키지 않는다.
stackoverflow는 `comments__posts.md`처럼 밑줄 2개를 쓴다.
crypto_bitcoin은 `blocks___transactions.md`처럼 밑줄 3개를 쓴다. `blocks`에는 끝 밑줄이 없으니 규칙대로라면 2개여야 한다.
[추정] prompt 예시 `events___users`(테이블 이름 `events_`에 `__`를 붙인 것)를 LLM이 모양째 따라 한 결과다 — 근거는 crypto_bitcoin의 join 파일 3개다.

[확인] cablate는 `raw/` → `atoms/<branch>/`(+`_archive/`) → `wiki/`(평면) 3층이다 (`cablate:CLAUDE.md:11-26`).

atom frontmatter는 `id`, `type`, `depth`, `source_type`, `source_ids`, `reuse_score`, `tags`, `created`다 (`cablate:CLAUDE.md:34-56`).
선택 필드로 `confidence`, `superseded_by`, `archived`가 있다 (`cablate:CLAUDE.md:58`).

wiki 페이지에는 frontmatter가 없다. 첫 줄 `# 제목`만 요구한다 (`cablate:CLAUDE.md:100-102`).

[확인] rohitg00은 working → episodic → semantic → procedural 4단 memory tier를 제안한다 (`rohitg00:llm-wiki.md:23-29`).
페이지 위에 typed entity graph를 얹으라고 한다 (`rohitg00:llm-wiki.md:31-41`).

#### 4. Ingest

[확인] OKF는 ingest를 처방하지 않는다.
producer가 사람이든 에이전트든 export 파이프라인이든 상관없다는 입장이다 (`okf/README.md:25-32`).

reference agent의 ingest 특성은 다음과 같다.

| 항목 | 입장 | 근거 |
|---|---|---|
| 사람 참여 | 없음. 끝까지 자율 실행 | `runner.py:264-285` |
| 증분 추적 | 없음. 매번 전체 concept을 다시 돈다. `--concept`로 범위만 좁힌다 | `cli.py:80-85`, `runner.py:264-273` |
| 기존 문서 | 덮어쓰기 전에 읽고 "refine"하라는 prompt 지시 | `prompts/reference_instruction.md:7-8` |
| queue·crash 복구 | 없음. session은 `InMemorySessionService` | `runner.py:194`, `204` |
| 자동 감시 | 없음 | — |
| 멀티포맷 | BigQuery metadata와 HTML만. HTML이 아니면 거부, markdown은 40KB에서 자름 | `web/fetcher.py:11`, `72-73`, `85-86` |
| 소스 하나가 건드리는 페이지 | BQ pass는 concept 1개당 문서 1개. web pass는 페이지 1개가 여러 concept을 고칠 수 있다 | `prompts/reference_instruction.md:1-3`, `prompts/web_ingestion_instruction.md:41-42`, `254-257` |

[확인] cablate의 ingest는 segment를 extract/skip/deferred로 먼저 거른다 (`cablate:METHODOLOGY.md:88-111`).
atom 하나에는 주장 하나만 담는다 (`cablate:METHODOLOGY.md:138-144`).

wiki 페이지 하나는 atom 3~8개를 묶는다 (`cablate:METHODOLOGY.md:310`).
첫 10~20개 segment는 사람이 보고 기준을 맞춘다 (`cablate:METHODOLOGY.md:225-231`).

[확인] rohitg00은 "on new source" hook으로 자동 ingest하라고 한다 (`rohitg00:llm-wiki.md:56-69`).
ingest 단계에서 비밀값을 걸러 내라고도 한다 (`rohitg00:llm-wiki.md:93-95`).

#### 5. 근거 추적 단위

[확인] OKF의 근거 단위는 "주장 → source id"다.
본문 문장 끝에 footnote를 달고, footnote label을 `sources[].id`와 맞춘다 (`okf/SPEC.md:350-364`).
위치 번호가 아니라 id로 묶는 이유도 적혀 있다.
에이전트가 문서를 계속 다시 쓰면 순서가 바뀌어 위치 번호가 조용히 틀어지기 때문이다.
원문 글자 일치나 줄 범위는 다루지 않는다.

[확인] 숫자에 한해서는 더 강한 단위가 있다.
Attested Computation은 실행 receipt의 SQL이 승인된 computation과 같은지 결정적으로 비교한다 (`okf/SPEC.md:662-670`).
샘플 attester는 주석·공백·키워드 대소문자를 정규화해 비교한다 (`okf/bundles/acme_retail/attesters/sql_equality.py:39-49`, `81-92`).

[확인] 다만 샘플 attester는 receipt를 믿는다.
결과 값은 receipt 안의 `result`와 비교한다 (`sql_equality.py:94-109`).
명세는 결과 값을 job id로 다시 읽으라고 한다 (`okf/SPEC.md:713-716`).
attester는 "Never makes network calls"라서 다시 읽지 않는다 (`sql_equality.py:11-17`).
bind 변수 값도 보지 않는다 (`sql_equality.py:8-9`). 잘못된 `year` 값으로 돌린 실행도 통과한다.
receipt를 만드는 executor는 markdown Skill이다. 에이전트가 이 지시를 따라 receipt를 조립한다 (`okf/bundles/acme_retail/skills/run-on-bq.md:28-36`).
[확인] 저장소 안에서 `attest()`를 부르는 코드도, attester 테스트도 없다. `okf/src`와 `okf/tests`에서 `attest`를 grep한 결과다.
즉 Attested Computation은 명세와 손으로 쓴 예시로만 있고, 실행 경로에 연결되어 있지 않다.

[확인] reference agent는 footnote와 `sources[].id`의 대응을 검사하지 않는다.
`okf/src`에 footnote를 파싱하는 코드가 없다.
[확인] 에이전트가 만든 샘플에서 이 대응이 실제로 깨진다.
stackoverflow의 `tables/votes.md`는 `sources[].id`가 `bq-table`, `meta_schema_doc`인데 본문은 위치 번호 `[^1]`을 쓴다 (`okf/bundles/stackoverflow/tables/votes.md:13-16`, `21`, `78`).
명세가 "silently misattributes"라며 피하라고 한 바로 그 위치형 label이다 (`okf/SPEC.md:361-364`).
`tables/posts_questions.md`도 같다.
references 문서 9개는 `[^1]`을 정의만 하고 본문에서 쓰지 않는다. 예: `references/joins/posts__votes.md:31`.
손으로 쓴 acme 샘플에도 흔적이 있다. `okf/bundles/acme_retail/metrics/gross-margin.md:52`는 `[^revenue-policy]`를 정의하지만 본문 어디에서도 쓰지 않는다. `computations/gross-margin-period.md`도 같다.
위 수치는 샘플 bundle의 footnote label과 `sources[].id`를 대조하는 스크립트를 따로 짜서 센 것이다.

[확인] cablate의 근거 단위는 atom의 `source_ids`(페이지 단위)다 (`cablate:CLAUDE.md:53`).
wiki 페이지 꼬리에는 재료가 된 atom id를 나열한다 (`cablate:CLAUDE.md:131-132`).
원문 변경을 잡으려면 `sha256:` id를 쓰라고 한다 (`cablate:CLAUDE.md:273-277`).
그 해시를 계산하거나 비교하는 스크립트는 없다.

[확인] rohitg00은 fact마다 "몇 개 source가 지지하는지"를 붙이라고 한다 (`rohitg00:llm-wiki.md:17`).
형식은 정하지 않는다.

#### 6. Link

[확인] OKF link는 표준 markdown link이고 타입이 없다 (`okf/SPEC.md:439-466`).
관계의 종류는 주변 문장이 말한다.
`/`로 시작하는 bundle 기준 절대 경로를 "recommended"로 둔다 (`okf/SPEC.md:444-446`).
깨진 link는 "아직 안 쓴 지식"으로 허용한다 (`okf/SPEC.md:464-466`).
backlink는 저장하지 않는다. consumer가 계산한다.

[확인] reference agent는 LLM이 link를 건다.
그런데 prompt는 명세 권장과 반대로 `/` 시작 link를 금지한다 (`prompts/reference_instruction.md:88-91`).
GitHub 렌더링이 깨진다는 이유다.
같은 저장소의 web prompt 예시는 다시 `/references/x.md`를 쓴다 (`prompts/web_ingestion_instruction.md:58`).

[확인] viewer는 link를 정규식으로 결정적으로 뽑는다 (`viewer/generator.py:18`, `68-86`).

`/`로 시작하는 link는 건너뛴다 (`viewer/generator.py:74`).
그래서 acme 샘플이 손으로 적은 "Cited by" 절의 절대 경로 link는 graph edge가 되지 않는다 (`okf/bundles/acme_retail/policies/margin-standard.md:49-53`).
backlink는 viewer JS가 역방향 index로 만든다 (`viewer/static/viz.js:16-20`).

[확인] viewer는 `sources[].resource`도 edge로 만들지 않는다. 본문 link만 본다 (`viewer/generator.py:125`).
명세는 `resource`가 다른 concept을 가리키면 "the derivation edge already exists in the bundle graph"라고 한다 (`okf/SPEC.md:343-346`).
acme의 metric과 computation은 `sources`로 `policies/*.md`를 가리킨다 (`okf/bundles/acme_retail/metrics/gross-margin.md:15-25`).
그런데 커밋된 `acme_retail/viz.html`의 edge 6개 중 policies에 닿는 것은 하나도 없다.
절대 경로 link와 `sources` 경로가 둘 다 버려져서 policy 노드가 고립된다.

[확인] 고아 reference 방지는 prompt 지시뿐이다 (`prompts/web_ingestion_instruction.md:86-91`, `190-206`).
join reference는 양쪽 테이블 문서가 모두 link해야 한다고 prompt가 정한다 (`prompts/web_ingestion_instruction.md:234-240`).
stackoverflow 샘플에서 `references/joins/comments__posts.md`와 `post_links__posts.md`는 `tables/posts_questions.md` 한 곳에서만 link된다. `tables/comments.md`와 `tables/post_links.md`에는 `# Joins` 절이 없다.

[확인] cablate는 LLM이 `[[slug]]`를 걸고 `lint.sh`가 ghost link와 orphan을 센다 (`cablate:scripts/lint.sh:26-90`).
[확인] rohitg00은 "uses", "contradicts", "supersedes" 같은 typed relationship과 graph traversal을 처방한다 (`rohitg00:llm-wiki.md:37-39`).

#### 7. Lint

[확인] OKF는 lint를 처방하지 않는다.
conformance 조건 세 개는 결정적으로 검사할 수 있는 모양이다 (`okf/SPEC.md:738-744`).
그러나 그 검사기는 이 저장소에 없다.

[확인] reference agent의 검사는 쓰기 시점 검사뿐이다 (축 2 표).
commit gate는 없다.
[확인] 다른 저장소인 inkeep/open-knowledge가 OKF v0.2 결정적 lint plugin을 따로 구현했다 (`inkeep:packages/core/src/markdown/lint/okf-rules.ts:14-17`, `okf-frontmatter/schemas.ts:5-7`).

[확인] cablate는 lint를 두 층으로 나눈다.

| 층 | 검사 | 근거 |
|---|---|---|
| 결정적 `lint.sh` | ghost link, orphan, 첫 줄 `# 제목`, 파일명 대소문자·밑줄, 시점 표현 regex | `cablate:scripts/lint.sh:26-154` |
| LLM lint | 모순, 개념 공백, 만료된 주장, 약한 orphan | `cablate:CLAUDE.md:233-239` |

자동 수정은 없다.
"errors가 있으면 끝났다고 하지 말라"는 prompt 문장이 gate 역할을 한다 (`cablate:CLAUDE.md:258`).

[확인] `lint.sh`는 `index`와 `log`만 건너뛴다 (`cablate:scripts/lint.sh:22`).
그래서 저장소에 들어 있는 `wiki/_template.md`도 검사 대상이 된다.
[추정] 막 fork한 저장소에서 `lint.sh`를 돌리면 `_template`이 파일명 밑줄 오류와 ghost link 오류를 낸다 — 근거는 스크립트와 template 본문을 읽은 것 1건이다. 실행하지 않았다.

[확인] rohitg00은 lint가 고칠 수 있는 것은 자동으로 고치라고 한다 (`rohitg00:llm-wiki.md:77`).

#### 8. stale·모순 처리

[확인] OKF는 낡음을 세 필드로 나눈다.
`status`는 draft/stable/deprecated다 (`okf/SPEC.md:412-422`).
`stale_after`는 상대 TTL이 아니라 절대 시각이다 (`okf/SPEC.md:424-433`).
`verified`는 `generated`와 따로 기록한다 (`okf/SPEC.md:388-393`).
내용이 바뀌어도 재확인이 없을 수 있고, 재확인만 있고 내용이 그대로일 수도 있기 때문이다.

[확인] OKF에는 `superseded_by` 같은 대체 관계 필드가 없다.
acme 샘플은 옛 정의를 `status: deprecated`로 남기고 본문 link로 새 정의를 가리킨다 (`okf/bundles/acme_retail/metrics/gross-margin-legacy.md:9-16`).

모순 처리 규칙도 없다.
acme 샘플은 producer 확장 필드 `not:`으로 "이 정의가 아니다"를 적는다 (`okf/bundles/acme_retail/metrics/gross-margin.md:11-14`).

[확인] OKF는 신뢰도 점수 저장을 명시적으로 거부한다.
점수는 주관적이고, consumer 사이에 옮길 수 없고, 시간이 지나면 낡는다는 이유다 (`okf/SPEC.md:315-320`).
대신 `author`, `usage_count`, `last_modified` 같은 객관적 신호를 남기고 consumer가 판단한다.

[확인] reference agent는 `stale_after`와 `verified`를 쓰지 않는다.
코드가 자동으로 채우는 것은 `generated`뿐이다 (`tools/bundle_tools.py:113-123`).
viewer는 stale 배지와 deprecated 취소선을 그린다 (`viewer/static/viz.js:57`, `206-209`, `viewer/static/viz.css:116`).

[확인] cablate는 atom을 고치지 않는다고 정한다.
새 atom을 만들고 옛 atom에 `superseded_by`를 단 뒤 `_archive/`로 옮긴다 (`cablate:CLAUDE.md:74-84`).
바뀐 견해는 지우지 않고 "evolved"로 남긴다 (`cablate:METHODOLOGY.md:473`).
[확인] 이 규칙은 문서 안에서 서로 부딪친다.
"Do not edit after creation"이라고 하면서 옛 atom의 frontmatter에 `superseded_by`를 추가하라고 한다 (`cablate:CLAUDE.md:76`, `80`).
wiki가 틀리면 "fix the underlying atom"하라고도 한다 (`cablate:CLAUDE.md:24`, `287`).
[확인] 어느 쪽이든 검사하는 코드가 없다. 세 스크립트는 `wiki/`와 루트 `log.md`만 다루고 `atoms/`는 읽지 않는다 (`cablate:scripts/lint.sh:6`, `gen-index.sh:8`, `log-append.sh:6-7`).
atom id 중복, 빈 `source_ids`, 없는 atom을 가리키는 `superseded_by`는 결정적 검사 밖에 있다.

[확인] rohitg00은 OKF와 정반대 처방을 한다.
fact마다 0.85 같은 confidence를 저장하고, 시간에 따라 감쇠시킨다 (`rohitg00:llm-wiki.md:17`, `21`).
모순은 source 최신성·권위·지지 수로 LLM이 판정한다 (`rohitg00:llm-wiki.md:79`).

#### 9. 사람 개입

[확인] OKF는 사람 개입을 workflow가 아니라 데이터로 표현한다.
`verified`에 `human:<id>` actor가 있으면 trust tier가 human-reviewed가 된다 (`okf/SPEC.md:401-410`).
consumer는 이 `human:` 접두사로 등급을 가르므로 producer는 반드시 써야 한다 (`okf/SPEC.md:500-501`).
[확인] 이 접두사를 인증하는 장치는 없다.
명세는 trust tier를 "advisory signals, not access control"이라고 부른다 (`okf/SPEC.md:410`).
reference agent의 쓰기 도구는 `generated`만 손대고, LLM이 넘긴 `verified`는 그대로 쓴다 (`tools/bundle_tools.py:113-124`).
[추정] 에이전트가 `verified: {by: human:x}`를 스스로 적으면 viewer는 human-reviewed로 표시한다 — 근거는 `trust_tier`가 문자열 접두사만 보는 코드 1건이다 (`bundle/document.py:99-113`). 실행하지 않았다.

[확인] reference agent는 승인 단계 없이 자율로 돈다.
acme 샘플의 `log.md`는 사람이 bundle 전체를 검토한 기록을 보여 준다 (`okf/bundles/acme_retail/log.md:8-10`).
이것은 손으로 쓴 예시다.

[확인] cablate는 첫 batch 보정, 새 branch 생성 승인을 사람에게 맡긴다 (`cablate:METHODOLOGY.md:225-231`, `cablate:CLAUDE.md:200`, `285`).
[확인] rohitg00은 사람은 큐레이션만 하고 bookkeeping은 전부 자동화하라고 한다 (`rohitg00:llm-wiki.md:69`).

#### 10. 동시성·안전

[확인] OKF는 git 배포를 권장한다 (`okf/SPEC.md:129-130`).
transaction, 잠금, undo는 다루지 않는다.
Attested Computation에서 에이전트는 parameter 값만 채우고 computation은 쓰지 못한다 (`okf/SPEC.md:662-663`).
도구 허용 목록과 비슷한 경계다.

[확인] reference agent의 안전 장치는 다음과 같다.

| 장치 | 근거 |
|---|---|
| concept id 조각을 정규식으로 검사해 경로 탈출을 막는다 | `bundle/paths.py:6-20` |
| crawl에서 나오지 않은 URL의 fetch를 거부한다. 지어낸 URL을 `sources`에 적는 것은 막지 않는다 (`write_concept_doc`은 `sources[].resource`를 방문 기록과 대조하지 않는다) | `tools/web_tools.py:65-74`, `tools/bundle_tools.py:90-187` |
| 쓰기는 원자적이지 않다. 임시 파일 없이 바로 `write_text` | `tools/bundle_tools.py:185-187` |
| 도구 상태가 module 전역 변수라 병렬 실행을 전제하지 않는다 | `tools/context.py:28-29` |

[확인] cablate의 병렬 compile 대책은 "slug 목록을 먼저 잠근다"이다 (`cablate:README.md:31`, `cablate:CLAUDE.md:216`, `288`).
이 잠금을 구현한 스크립트는 없다.
coordinator 에이전트가 손으로 지키는 규칙이다.

[확인] rohitg00은 last-write-wins mesh sync, audit trail, 되돌릴 수 있는 bulk 작업을 처방한다 (`rohitg00:llm-wiki.md:85`, `97-99`).

#### 11. Query·검색

[확인] OKF의 조회 모델은 `index.md` 계층을 따라 내려가는 progressive disclosure다 (`okf/SPEC.md:505-529`).
검색 방식은 비목표다.
답을 bundle에 되저장하는 규칙은 없다.
숫자 답에 한해 Discover → Load → Parameterize → Execute → Attest → Gate 흐름을 informative로 적는다 (`okf/SPEC.md:699-719`).

[확인] 이 저장소에는 OKF bundle을 질의하는 에이전트가 없다.
`samples/discovery`는 Knowledge Catalog 검색 API를 쓰는 별개 에이전트다 (`samples/discovery/SKILL.md:1-15`).
[확인] 다만 서빙 다리는 있다. `toolbox/mdcode/demo/okf/`가 bundle의 각 `.md`를 Dataplex entry로 올린다.
OKF 필드는 custom `okf` aspect로 옮기고, 모델에 없는 키는 `extra` 필드에 담아 pull 때 되살린다 (`toolbox/mdcode/demo/README.md:136-160`).
README는 "a catalog-wide search can pick out OKF documents"라고 쓴다 (`toolbox/mdcode/demo/README.md:142-144`).
[추정] 이렇게 올린 bundle은 Knowledge Catalog 검색, 곧 `samples/discovery`로 찾을 수 있다 — 근거는 README 문장 1건이다. demo도 discovery도 실행하지 않았다.

[확인] cablate는 `index.md`로 범위를 정하고 해당 페이지만 읽는다 (`cablate:CLAUDE.md:218-225`).
쓸 만한 합성은 atom으로 되저장하자고 "제안"한다.

[확인] rohitg00은 BM25 + vector + graph를 RRF로 섞으라고 한다 (`rohitg00:llm-wiki.md:47-54`).
완료된 작업 흐름을 요약해 페이지로 되저장하는 "crystallization"도 처방한다 (`rohitg00:llm-wiki.md:101-107`).

#### 12. index·log 관리

[확인] OKF `index.md`는 선택이다.
frontmatter를 두지 않는다. 예외는 bundle 루트의 `okf_version` 하나다 (`okf/SPEC.md:512-514`).
항목에는 각 concept의 `description`을 쓰는 것이 SHOULD다 (`okf/SPEC.md:527-529`).
`log.md`는 최신순, `## YYYY-MM-DD` 제목이다 (`okf/SPEC.md:533-552`).

[확인] reference agent의 `regenerate_indexes`는 frontmatter에서 항목을 결정적으로 만든다 (`bundle/index.py:67-91`).
하위 디렉터리 설명은 LLM이 쓴다. 실패하면 제목 나열로 대체한다 (`bundle/synthesizer.py:39-50`).
그래서 index 재생성 결과가 실행마다 달라질 수 있다.


[확인] `regenerate_indexes`는 `okf_version`을 쓰지 않는다 (`bundle/index.py:89-90`).
게다가 기존 `index.md`를 통째로 덮어쓴다 (`bundle/index.py:89-90`). 사람이 루트 index에 `okf_version`을 적어 두어도 다음 실행에서 지워진다.
[확인] 샘플 bundle 넷 중 어느 루트 `index.md`에도 `okf_version`이 없다 (grep 결과 0건).

[확인] `index.md`만 건너뛰고 `log.md`는 건너뛰지 않는다 (`bundle/index.py:70-81`).
viewer도 같다. `index.md`만 건너뛴다 (`viewer/generator.py:92`).
[확인] 커밋된 `acme_retail/viz.html`에는 `log.md`가 `"id": "log"`, `"type": "Log"`인 concept 노드로 들어 있다.
명세는 `log.md`를 concept 문서로 쓰면 안 된다(MUST NOT)고 정한다 (`okf/SPEC.md:134-144`).
[추정] `log.md`가 있는 bundle에서 재생성하면 `log.md`가 concept 항목으로 index에 들어간다 — 근거는 같은 판정을 쓰는 viewer의 결과물 1건이다. index 재생성은 실행하지 않았다. acme 샘플의 루트 index에는 `log.md`가 없고 항목 순서도 생성기의 제목순 정렬과 다르다. acme index는 손으로 쓴 것으로 보인다.

[확인] cablate의 `gen-index.sh`는 각 페이지 첫 줄 제목으로 index를 결정적으로 만든다.
그런데 작성자의 branch 11개가 배열로 박혀 있다 (`cablate:scripts/gen-index.sh:16-28`).
배열이 비어 있지 않으면 자동 탐색을 하지 않는다 (`cablate:scripts/gen-index.sh:31`).
[추정] fork한 사람이 배열을 고치지 않으면 다른 접두사의 페이지가 index에서 조용히 빠진다 — 근거는 스크립트 읽기 1건이다.
`log-append.sh`는 2번째 줄 뒤에 끼워 넣어 최신순을 만든다 (`cablate:scripts/log-append.sh:22`).

[확인] rohitg00은 100페이지를 넘으면 `index.md`를 사람용 목록으로만 두라고 한다 (`rohitg00:llm-wiki.md:54`).

#### 13. 포맷 표준 (OKF 준수 정도)

이 저장소가 표준 자체다.
다만 명세와 그 reference 구현 사이에 어긋난 곳이 있다.

| 어긋남 | 근거 |
|---|---|
| 명세는 `/` 절대 link를 권장하고, reference agent prompt는 금지하고, viewer는 무시한다 | `okf/SPEC.md:444-446`, `prompts/reference_instruction.md:90-91`, `viewer/generator.py:74` |
| 명세는 루트 `okf_version`을 허용하지만 생성기는 쓰지 않는다 | `okf/SPEC.md:776-778`, `bundle/index.py:89-90` |
| 명세 예시의 `author: team:ga4-docs`는 §7의 actor 형식 세 가지에 없다 | `okf/SPEC.md:297`, `489-501`. inkeep도 같은 점을 지적한다 (`inkeep:packages/core/src/markdown/lint/okf-frontmatter/schemas.ts:90`) |
| acme `log.md`에 `type: Log` frontmatter가 있다. 예약 파일은 concept이 아니라는 §3.1과 읽기에 따라 부딪친다 | `okf/bundles/acme_retail/log.md:1-4`, `okf/SPEC.md:134-144` |
| viewer와 index 생성기가 `log.md`를 concept으로 다룬다. acme `viz.html`에 `log` 노드가 있다 | `viewer/generator.py:92`, `bundle/index.py:70-81` |
| 명세는 `sources[].resource`가 concept을 가리키면 graph edge라고 하지만 viewer는 본문 link만 edge로 만든다 | `okf/SPEC.md:343-346`, `viewer/generator.py:125` |
| 명세는 위치형 footnote를 피하라고 하지만 생성 샘플이 `[^1]`을 쓴다 | `okf/SPEC.md:361-364`, `okf/bundles/stackoverflow/tables/votes.md:21` |

다른 9개 저장소와 이 저장소 안 mdcode demo의 OKF 대응은 다음과 같다.

| 저장소 | 주장 | 실제 수준 | 근거 |
|---|---|---|---|
| langchain-ai/openwiki | v0.2 bundle을 기본 출력으로 낸다 | native v0.2 producer. 루트 `okf_version: "0.2"`, family 검증, claim 재확인 뒤에만 `verified` 기록 | `langchain-ai_openwiki/README.md:370-385`, `src/okf/index-sync.ts:288`, `src/okf/frontmatter.ts:186` |
| inkeep/open-knowledge | OKF v0.2 지원 | v0.2 결정적 lint plugin + OKF skill pack + `ok seed --pack okf` | `inkeep:packages/core/src/markdown/lint/okf-rules.ts:14-17`, `packages/server/assets/skills/packs/okf/SKILL.md:1-20` |
| Ar9av/obsidian-wiki | vault가 v0.2에 "structurally conformant", 왕복 무손실 | export/import 다리(prompt skill)로만 v0.2. native 페이지는 `type` 대신 `category`를 써서 §11 조건 2를 그대로는 못 맞춘다 | `Ar9av:AGENTS.md:179`, `.skills/wiki-export/SKILL.md:358-404`, `.skills/llm-wiki/SKILL.md:88`, `tests/test_okf_v02.py:1-12` |
| atomicstrata/llm-wiki-compiler | OKF producer이자 consumer | v0.1 export/import. 외부 bundle import는 review queue로 들어간다 | `atomicstrata_llm-wiki-compiler/src/export/okf/index-log.ts:15`, `README.md:236-244` |
| Astro-Han/karpathy-llm-wiki | 일부러 맞추지 않음 | 미준수. "v0.1 draft"라 추적만 한다 | `Astro-Han_karpathy-llm-wiki/README.md:126`, `137` |
| kfchou/wiki-skills | — | 로드맵 문서에 언급만. 구현 없음 | `kfchou_wiki-skills/docs/superpowers/plans/2026-06-21-wiki-skills-improvement-roadmap.md:4`, `148` |
| knowledge-catalog 자신의 `toolbox/mdcode/demo/okf` | OKF bundle을 Dataplex로 push/pull, "round-tripping the signal losslessly" | v0.2 필드 전체를 typed aspect로 옮기는 TypeScript demo. 기본 대상은 acme 샘플 | `toolbox/mdcode/demo/README.md:121-160`, `toolbox/mdcode/demo/okf/okf.ts:1-20` |
| cablate, AgriciDaniel, frankchu91, nashsu | 언급 없음 | 대응 없음 | grep 결과 0건 |

#### 14. 규모·비용

[확인] OKF 명세는 규모나 비용을 주장하지 않는다.

[확인] reference agent의 비용 통제는 상한값뿐이다.
web pass는 기본 100페이지, depth 2다 (`cli.py:104-137`).
기본 모델은 `gemini-flash-latest`다 (`agent.py:16`).
컨텍스트는 concept마다 새 session으로 끊긴다 (`runner.py:211-220`).
web pass는 session 하나에 페이지(최대 40KB)를 계속 쌓는다.
ingest 비용 측정값은 없다. 샘플 recipe는 BigQuery 과금 경고만 적는다 (`okf/samples/stackoverflow/README.md:26-29`).

[확인] cablate는 584 posts + 8,668 replies → 630 atoms → 83 pages, 11 branches를 주장한다 (`cablate:README.md:6`, `37-46`).
내용은 비공개라 검증할 수 없다 (`cablate:README.md:111`).
100~200페이지를 index-only의 한계로 본다 (`cablate:METHODOLOGY.md:21`).

[확인] rohitg00은 "thousands of sessions" 운영 경험을 근거로 든다 (`rohitg00:llm-wiki.md:11`).
데이터는 제시하지 않는다.

#### 15. frosk1 비판 7가지에 대한 대응

| 비판 | OKF 명세 | reference agent 코드 | cablate | rohitg00 |
|---|---|---|---|---|
| 오류 누적 | `generated`와 `verified`를 분리해 "누가 썼나"와 "누가 확인했나"를 따로 본다. 숫자는 attestation | web pass가 BQ schema와 `sources`를 줄이지 못하게 막는다. 산문 오류는 못 막는다 | atom 불변. 틀리면 atom을 고치고 재compile | confidence 감쇠, self-healing lint |
| 부분 문맥 | 다루지 않음 | concept마다 원 metadata 전체를 주지만 web 페이지는 40KB에서 자른다 | 다루지 않음 | hybrid 검색, graph traversal |
| 요약 손실 | per-claim footnote로 원 source를 가리킨다. computation은 원문 SQL 그대로 | schema 축소 금지 guard | atom 층이 raw와 wiki 사이 완충. 원문 인용은 선택 | 다루지 않음 |
| 가짜 source of truth | trust tier는 "advisory signals, not access control". attestation이 실패하면 숫자를 보여 주지 말라 | trust tier와 stale을 viewer에 표시만. LLM이 넘긴 `verified`를 거르지 않아 human 접두사도 그대로 통과한다 | "wiki는 파생 cache, atom이 진실" | 점수로 확신 정도를 드러냄 |
| 환각 병합 | link는 타입이 없어 관계를 지어낼 칸이 적다 | crawl에 없는 URL의 fetch 거부(인용은 막지 않음), `list_concepts` 밖 link 금지(prompt) | LLM lint가 모순 표시 | contradiction resolution을 LLM에 맡김 |
| 운영 복잡도 | 필수는 `type` 하나. 대신 v0.2 family와 executor·attester가 consumer 부담으로 넘어간다 | 대응 없음 | bash 3개로 최소화 | 단계별 도입 스펙트럼 |
| ingest 비용 | 다루지 않음 | page·depth 상한 | 첫 batch 보정 후 무인 실행, 단계별 모델 차등 | 다루지 않음 |

근거 경로는 다음과 같다.
OKF: `okf/SPEC.md:366-410`, `350-364`, `662-670`, `717-719`, `458-462`.
reference agent: `tools/bundle_tools.py:139-183`, `web/fetcher.py:11`, `tools/web_tools.py:65-74`, `prompts/reference_instruction.md:93`.
cablate: `cablate:README.md:25`, `cablate:CLAUDE.md:24`, `289`, `cablate:METHODOLOGY.md:225-231`, `484`.
rohitg00: `rohitg00:llm-wiki.md:17-21`, `43-54`, `77-79`, `136-152`.

[확인] cablate README는 atom 층이 frosk1의 "loss of information"과 "false sense of source of truth"를 푼다고 직접 주장한다 (`cablate:README.md:25`).
[추정] atom도 LLM이 원문을 다시 쓴 요약이므로 요약 손실을 없애지는 못하고 한 단계 미룰 뿐이다 — 근거는 atom 규칙 "Extract, don't copy" 1건이다 (`cablate:METHODOLOGY.md:140`).

frosk1의 8번째 항목(staleness)은 축 8에서 다뤘다.

#### 16. 성숙도·차용 가능성

| 대상 | 테스트 | 의존성 | 라이선스 | 차용 |
|---|---|---|---|---|
| OKF 명세 | 해당 없음 | 없음 | Apache-2.0 | 형식 그대로 채택 가능 |
| reference agent | test 39개 (미실행) | google-adk>=2.0, google-cloud-bigquery, pyyaml, pydantic, markdownify (`okf/pyproject.toml`) | Apache-2.0 | 코드 차용 가능. 단 동결된 사본이다 |
| cablate | 없음 | bash 4+ (`declare -A`) | 없음 | 아이디어만. 라이선스가 없어 스크립트 복사는 권리가 불분명하다 |
| rohitg00 gist | 해당 없음 | 없음 | 표시 없음 | 아이디어만 |

[확인] reference agent에서 테스트가 덮는 것은 문서 parse·serialize, index 생성, web 도구 제한, 쓰기 guard, viewer, BigQuery source, HTML fetcher다 (`okf/tests/test_bundle_tools.py:49-166`, `okf/tests/test_viewer.py:92-187`, `okf/tests/test_bigquery_source.py`, `okf/tests/test_web_fetcher.py`).
LLM이 낀 경로는 테스트하지 않는다. index 테스트는 LLM 요약 함수를 stub으로 바꿔 끼운다 (`okf/tests/test_index.py:9-10`).
acme의 `sql_equality.py` attester를 검사하는 테스트는 없다.

[확인] 정본 저장소의 `src/`, `tests/`는 이 사본과 라이선스 헤더만 다르다.
gh api로 정본 tree를 받아 `src/`, `tests/` 파일 35개를 하나씩 비교한 결과다.
정본에만 있는 것은 저장소 문서 파일과 `connectors/gcp-knowledge-catalog.md`다.
샘플은 stackoverflow 8개 파일의 `tags` 표기(YAML list ↔ 쉼표 문자열)만 다르다. 정본에도 `[^1]` footnote가 그대로 있다.

## 장점

- [확인] 신뢰를 저장하지 않고 유도한다. trust tier는 `verified`의 `human:` 접두사에서, 신선도는 `stale_after` 비교에서 나온다 (`okf/SPEC.md:401-433`). 구현도 20줄 남짓이다 (`bundle/document.py:83-133`).
- [확인] "누가 썼나"와 "누가 확인했나"를 분리했다 (`okf/SPEC.md:366-399`). LLM이 쓴 것과 사람이 본 것을 한 필드로 섞지 않는다.
- [확인] footnote를 위치가 아니라 id로 묶는 이유를 명세에 적었다 (`okf/SPEC.md:360-364`). 에이전트가 문서를 계속 고쳐 쓰는 환경을 정면으로 전제한다.
- [확인] Attested Computation은 "LLM이 숫자를 지어내는" 문제에 결정적 대조라는 답을 낸다. SQL 동일성과 receipt 값 비교는 LLM 없이 돈다 (`okf/bundles/acme_retail/attesters/sql_equality.py:54-115`). 다만 샘플 attester는 에이전트가 조립한 receipt를 믿고, 저장소 안에서 이 attester를 부르는 코드는 없다 (축 5).
- [확인] 진입 장벽이 낮다. `type` 하나만 있으면 conformant이고, consumer는 거부하지 말아야 한다 (`okf/SPEC.md:187-188`, `755-762`).
- [확인] reference agent의 쓰기 guard는 "보강은 줄이지 못한다"를 코드로 박았다 (`tools/bundle_tools.py:139-183`). 거부 메시지가 에이전트에게 고치는 법을 알려 준다. 범위는 좁다. web pass의 `BigQuery Table` 문서에만 걸리고, `sources`는 개수만 센다 (축 2).
- [확인] `fetch_url`은 crawl에서 나오지 않은 URL의 fetch를 거부한다 (`tools/web_tools.py:65-74`). 지어낸 URL로 crawl하는 것은 도구가 막는다. 지어낸 URL을 `sources`에 적는 것은 prompt만 막는다 (`prompts/web_ingestion_instruction.md:261-262`).
- [확인] 생태계가 이미 이 형식을 쓴다. 다른 저장소 넷이 export, lint, native 출력 중 하나로 대응한다. 이 저장소 안에도 Dataplex로 올리는 demo가 있다 (축 13 표).

## 단점

- [확인] 명세와 reference 구현이 link 형식에서 서로 어긋난다 (축 13 표 첫 줄). 처음 따라 하는 사람은 어느 쪽을 믿어야 할지 모른다.
- [확인] footnote ↔ `sources[].id` 대응을 검사하는 도구가 없다. 에이전트가 만든 stackoverflow 샘플은 명세가 금지 취지로 든 위치형 `[^1]`을 쓴다 (`okf/bundles/stackoverflow/tables/votes.md:21`, `78`). 손으로 쓴 acme 샘플에도 쓰이지 않는 footnote가 있다 (`okf/bundles/acme_retail/metrics/gross-margin.md:52`).
- [확인] supersede와 모순을 표현할 필드가 없다. `status: deprecated`와 본문 link가 전부다 (`okf/SPEC.md:412-422`).
- [확인] link에 타입이 없다 (`okf/SPEC.md:458-462`). "supersedes", "contradicts"를 기계가 읽을 수 없다.
- [확인] `log.md`는 형식만 있고 누가 언제 쓰는지는 없다. reference agent도 쓰지 않는다. 오히려 viewer와 index 생성기가 `log.md`를 concept으로 다뤄 §3.1을 어긴다 (`viewer/generator.py:92`, `bundle/index.py:70-81`, acme `viz.html`의 `log` 노드).
- [확인] `human:` 접두사를 인증하는 장치가 없다. reference agent의 쓰기 도구는 LLM이 넘긴 `verified`를 그대로 쓴다 (`tools/bundle_tools.py:113-124`). trust tier는 producer가 정직하다는 가정 위에 있다.
- [확인] Attested Computation은 실행 경로에 연결되어 있지 않다. attester를 부르는 코드도 테스트도 없고, 샘플 attester는 receipt의 값을 다시 읽지 않는다 (축 5).
- [확인] reference agent는 증분 추적, crash 복구, 원자적 쓰기가 없다 (축 4, 10 표). PoC라는 자기 설명과 맞는다.
- [확인] index 재생성에 LLM 호출이 섞여 있다 (`bundle/synthesizer.py:39-47`). 같은 bundle에서 diff가 생길 수 있다.
- [확인] 동결된 사본이다 (`okf/README.md:1-11`). 이 경로에 기대는 다른 저장소 링크는 낡을 수 있다. openwiki와 Ar9av는 아직 이 경로를 가리킨다.
- [확인] cablate의 핵심 차별점인 slug 잠금은 구현이 없다 (축 10). `lint.sh`는 gate가 아니다 (축 2). 진실의 자리라는 atom 층은 어떤 스크립트도 읽지 않는다 (축 8).

## 내 llm-wiki에 가져올 것 / 피할 것

### 가져올 것

| 무엇 | 출처 | 메모 |
|---|---|---|
| frontmatter 바닥을 OKF에 맞춘다. `type` 필수, `generated`/`verified`/`status`/`stale_after`/`sources` | `okf/SPEC.md:161-433` | 다른 도구로 내보낼 때 변환이 필요 없다 |
| trust tier와 stale을 저장하지 말고 계산한다 | `bundle/document.py:83-133` | Apache-2.0이라 함수 차용 가능 |
| `sources[].id` + keyed footnote | `okf/SPEC.md:350-364` | 여기에 결정적 lint를 더한다. 모든 footnote label이 `sources[].id`로 풀리는지, 쓰이지 않는 id가 있는지 |
| "보강은 줄이지 못한다" 쓰기 guard | `tools/bundle_tools.py:139-183` | 대상을 `sources` 목록과 사람이 확인한 절로 넓힌다 |
| 도구가 지어낸 URL을 거부하는 방식 | `tools/web_tools.py:65-74` | OKF는 fetch 시점에만 막는다. 나는 쓰기 시점에도 막는다. `sources`의 경로가 등록된 raw 파일이나 실제로 읽은 URL인지 쓰기 도구가 대조한다 |
| 정확해야 하는 것은 승인된 원문을 두고 결정적으로 대조한다 | `okf/SPEC.md:556-732` | 숫자 대신 명령어·설정값·인용문에 적용한다 |
| 불변 atom 층과 `superseded_by` | `cablate:CLAUDE.md:74-84` | OKF 확장 필드로 넣는다. OKF는 모르는 키를 보존해야 한다 (`okf/SPEC.md:205-207`) |
| 결정적 lint 먼저, LLM lint 나중 | `cablate:CLAUDE.md:227-239` | 결정적 lint는 종료 코드를 내서 pre-commit gate로 쓴다 |
| 병렬 작성 전 slug 잠금 | `cablate:CLAUDE.md:216` | 문장 대신 예약 파일이나 스크립트로 구현한다 |

### 피할 것

| 무엇 | 이유 |
|---|---|
| fact마다 신뢰도 숫자를 저장하기 (rohitg00 방식) | OKF가 든 이유가 타당하다. 점수는 주관적이고 낡는다 (`okf/SPEC.md:315-320`). 필요하면 신호에서 계산한다 |
| 명세와 도구가 서로 다른 link 형식 쓰기 | OKF가 보여 준 실패다. 형식을 하나로 정하고 linter와 viewer가 같은 parser를 쓰게 한다 |
| 고아 방지·footnote 정합을 prompt로만 지키기 | reference agent가 그렇게 해서 생성 샘플에 흔적이 남았다. stackoverflow의 위치형 `[^1]`, 한쪽만 link된 join reference, crypto_bitcoin의 밑줄 3개 join 파일 이름이다 (축 3, 5, 6) |
| index 생성에 LLM 끼우기 | 재생성할 때마다 diff가 생긴다. 설명은 frontmatter `description`에서만 가져온다 |
| 작성자 고유 값을 스크립트에 박기 | cablate `gen-index.sh`의 branch 배열이 예다 |
| 종료 코드 없는 lint | 보고서는 읽히지 않는다. cablate STORY도 노이즈 많은 보고서는 무시된다고 적는다 (`cablate:STORY.md:43-45`) |
| 개인 wiki에 executor·attester·receipt 전체 도입 | Attested Computation 전체 구조는 숫자 대시보드용이다. 개인 wiki에는 "원문 대조" 원리만 가져온다 |

## 확인하지 못한 것

- reference agent를 실행하지 않았다. test 39개도 돌리지 않았다. 지시대로 코드를 실행하지 않았기 때문이다.
- 샘플 bundle(ga4, stackoverflow, crypto_bitcoin)이 지금 코드로 그대로 재현되는지 모른다. 실행 기록이 없다. 샘플 `generated.by` 모델은 섞여 있다. ga4와 crypto_bitcoin은 각 9개 문서가 `gemini-3.5-flash`다. stackoverflow는 17개가 `gemini-2.5-flash`, 9개가 `gemini-3.5-flash`다. acme는 `gemini-2.5-pro`와 `human:` actor가 섞인 손 작성 예시로 보인다. reference agent 도구로는 attester `.py`를 쓸 수 없기 때문이다.
- shallow clone이라 `okf/`의 변경 이력과 v0.1 → v0.2 이행 과정을 git으로 보지 못했다. 정본 저장소 이력을 보면 알 수 있다.
- 정본 저장소의 `connectors/gcp-knowledge-catalog.md`는 읽지 않았다. 이 사본에는 없는 파일이다. `src/`와 `tests/`는 라이선스 헤더만 다르다는 것을 확인했다 (축 16).
- cablate의 운영 수치(630 atoms, 83 pages)는 내용이 비공개라 검증할 수 없다.
- rohitg00의 "thousands of sessions"는 근거가 없다. agentmemory 저장소의 별은 현재 29,284개다(gh api). 그 엔진이 gist의 처방을 실제로 구현했는지는 보지 않았다.
- `_template.md` lint 오류와 `gen-index.sh` 누락은 스크립트를 읽고 추론한 것이다. 빈 fork에서 스크립트를 돌려 보면 확인할 수 있다.
- Ar9av의 "왕복 무손실" 주장은 fixture 테스트 파일 머리말만 읽었다. 테스트를 돌리지 않았다.

## 검증 기록

적대적 검증에서 인용한 path:line을 열어 대조했다. 바꾼 것은 다음과 같다.

- 한눈에: `toolbox/mdcode`가 OKF와 무관하다는 서술을 고쳤다. `demo/okf/`가 OKF ↔ Dataplex 다리다.
- 축 1: agent가 하나가 아니라 BQ용과 web용 두 개라고 고쳤다.
- 축 2: 코드 강제 규칙에 concept id 정규식을 더해 네 가지로 고쳤다.
- 축 2: 축소 금지 guard가 web pass에만 걸리고 BQ pass 재실행은 막지 못한다는 점을 더했다.
- 축 2: `sources` guard가 개수만 센다는 점을 더했다.
- 축 3: `datasets/`·`tables/`의 근거를 prompt에서 `sources/bigquery.py`로 바로잡았다.
- 축 3: join 파일 이름 규칙이 prompt 규칙이고 crypto_bitcoin 샘플이 어긴다는 점을 더했다.
- 축 5: 샘플 attester가 receipt를 믿고, 값을 job id로 다시 읽지 않고, 어디서도 호출되지 않는다는 점을 더했다.
- 축 5: footnote 불일치의 근거를 손 작성 acme에서 에이전트 생성 stackoverflow의 위치형 `[^1]`로 보강했다.
- 축 6: viewer가 `sources[].resource`를 edge로 만들지 않아 acme policy 노드가 고립된다는 점을 더했다.
- 축 6: join reference의 양쪽 back-link 규칙이 stackoverflow 샘플에서 깨진 사례를 더했다.
- 축 8: cablate의 atom 불변 규칙이 문서 안에서 부딪치고, atom 층을 읽는 스크립트가 없다는 점을 더했다.
- 축 9: `human:` 접두사를 인증하는 장치가 없고 쓰기 도구가 `verified`를 거르지 않는다는 점을 더했다.
- 축 10: `fetch_url`은 fetch만 막고 `sources`에 지어낸 URL을 적는 것은 막지 않는다고 고쳤다.
- 축 11: mdcode demo를 통한 Knowledge Catalog 서빙 경로를 더했다.
- 축 12: `regenerate_indexes`가 루트 index를 통째로 덮어써 `okf_version`을 지운다는 점을 더했다.
- 축 12: `log.md`가 concept으로 다뤄진다는 근거로 viewer 코드와 acme `viz.html`의 `log` 노드를 더했다.
- 축 13: 명세와 구현의 어긋남 표에 세 줄(log.md, sources edge, 위치형 footnote)을 더했다. 대응 표에 mdcode demo를 더했다.
- 축 14: cablate의 index 한계를 "약 200"에서 원문대로 "100~200"으로 고쳤다.
- 축 15: 환각 병합 칸과 가짜 source of truth 칸의 reference agent 서술을 위 내용에 맞췄다.
- 축 16: 테스트 범위에 BigQuery source와 fetcher를 더했다. attester 테스트가 없다는 점을 더했다.
- 축 16: 정본 저장소와 `src/`·`tests/`를 gh api로 비교해 라이선스 헤더만 다르다는 것을 확인했다.
- 장점: Attested Computation, 쓰기 guard, `fetch_url` 항목에 범위 한정을 붙였다.
- 단점: footnote 근거를 보강했다. `log.md` concept 처리, `human:` 미인증, attester 미연결, cablate atom 층 미검사를 더했다.
- 가져올 것: 지어낸 URL 거부를 쓰기 시점 대조로 넓혔다.
- 피할 것: prompt-only 규칙의 근거를 생성 샘플 사례로 바꿨다.
- 확인하지 못한 것: 샘플 모델이 `gemini-3.5-flash` 하나라는 서술을 고쳤다. stackoverflow는 `gemini-2.5-flash` 17개가 섞여 있다.
- 확인하지 못한 것: 정본 코드 diff 항목을 확인한 결과로 바꾸고 `connectors/` 미확인만 남겼다.

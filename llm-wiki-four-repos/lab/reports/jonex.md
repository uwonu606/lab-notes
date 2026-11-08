# jonex — JonexWiki는 LLM에게 원문 발췌 고르기만 맡기고 사실 검증·페이지 작성·같은 대상 판정·링크 해석을 코드 규칙으로 옮겨서, 모든 페이지 줄이 원문 문자 구간으로 되돌아가는 llm-wiki를 만든다

분석 대상은 GitHub `yuezhiai/jonex`, commit `5571db5`(2026-10-10, 브랜치 `mian`의 HEAD)이다.

jonex는 중국 기업용 지식 플랫폼이고, KB(지식 베이스)를 만들 때 엔진 셋 중 하나를 고른다. llm-wiki 엔진은 그중 둘이다: 레포 안에 복사해 둔 OpenKB(`kb_type=openkb`)와 자체 엔진 JonexWiki(`kb_type=jonex_wiki`).
이 보고서는 JonexWiki를 중심으로 본다. 플랫폼과 OpenKB는 JonexWiki를 이해하는 데 필요한 만큼만 다룬다.

입력은 갈래별 노트 4개(jonexwiki-compile, jonexwiki-runtime, jonex-platform, jonex-why)다. 노트끼리 어긋난 곳은 레포 코드를 다시 열어 가렸고, 그 자리에 "이 보고서 작성 때 다시 열어 확인"이라고 적었다. 코드는 실행하지 않았다.

표기는 이렇다.
작성자가 밝힌 이유는 원문을 큰따옴표로 옮기고 뒤에 한국어 뜻을 붙인다.
코드 읽기로 추론한 이유는 `[추정]`을 앞에 달고 문장 끝 괄호에 사례와 개수를 붙인다.
근거가 없으면 `모르는 것:`으로 적는다.

경로는 레포 루트 기준이고, 자주 나오는 앞부분은 아래처럼 줄인다.

| 줄임 | 원래 경로 |
|---|---|
| `JW/` | `Reference/JonexWiki/src/jonex_wiki/` |
| `C/` | `JW/domain/engine/compile/` |
| `SP/` | `C/source_prep/` |
| `M/` | `JW/domain/engine/models/` |
| `Q/` | `JW/domain/engine/query/` |
| `KB/` | `capabilities/knowledge_base/services/` |
| `ADP/` | `jonex_core/capability/atomic/jonex_wiki/` |

## 한눈에

| 항목 | 값 |
|---|---|
| 무엇 | 문서를 KB 단위로 세 엔진(`lightrag` 그래프, `openkb`, `jonex_wiki`) 중 하나에 보내는 기업용 플랫폼이다(`KB/kb_type_service.py:35-40`). JonexWiki는 그중 "新一代 LLM Wiki 引擎"(차세대 LLM Wiki 엔진)으로 소개된다(`frontends/core-business/src/locales/zh.json:1528`). 엔진의 뼈대는 Tencent WeChat 논문 arXiv 2605.25480의 Algorithm 1·Error Book이고, 기본 모드 `layered`는 그 위에 원문 읽기와 페이지 배치를 떼어 낸 jonex 개조다(`JW/infra/settings.py:80-84`, `C/understanding.py:3-7`) |
| 실행 형태 | Docker compose 다중 컨테이너다. JonexWiki는 `jonex-wiki` 컨테이너 안에서 플랫폼 능력(capability)이 `import jonex_wiki`로 `WikiApplication`을 같은 프로세스에서 부른다(`ADP/jonex_wiki_adapter.py:196-202`, `deploy/docker-compose.yml:1157-1181`). 독립 FastAPI 서비스로도 돈다(`JW/main.py:36-121`). 단일 인스턴스를 강제한다(`JW/application.py:98-113`) |
| 저장 | 메타데이터는 PostgreSQL 표 5개, wiki 내용은 파일 시스템의 불변 bundle 디렉터리다(`JW/storage/models.py:18-113`, `JW/storage/layout.py:47-141`) |
| 규모 | commit 38개, 2026-07-19 `0682461` "init" ~ 2026-10-10 `5571db5`(`git log`). JonexWiki는 Python 157개 파일 57,603줄이고 그중 compile 20,274줄, query 25,007줄이다(`find … -name '*.py' \| xargs wc -l`, 이 보고서 작성 때 다시 셈). `Reference/` 밖 플랫폼 Python은 123,780줄이다. JonexWiki 전체가 commit `a8bee87`(2026-10-10, 186개 파일 +62,467줄) 하나로 들어왔다 |
| 공개 활동 | stars 1,344, forks 240, 이슈 31개(열림 30), PR 5개다(`gh api`, `gh issue list --state all`). JonexWiki를 다룬 이슈·PR은 없다 |
| 라이선스 | "amended version of the Apache License 2.0"(`LICENSE:2`)이다. 상업 사용은 허용한다. 다만 "Multi-tenant deployment: You may not deploy or operate a multi-tenant environment based on the Jonex source code without prior explicit written authorization from Jonex"(`LICENSE:6`) — 서면 허가 없이 다중 테넌트 운영을 못 한다. 테넌트는 "independent workspace"로 정의된다(8행). GitHub는 `NOASSERTION`으로 표시한다. `Reference/JonexWiki`에는 따로 LICENSE가 없고, 복사본 OpenKB는 Apache-2.0 원문을 지닌다(`Reference/OpenKB/LICENSE`) |
| 차용 조건 | 코드를 옮기면 위 조항이 걸린다. 설계를 참고해 다시 쓰면 걸리지 않는다. 조항이 둘 더 있다. 1b는 Jonex 프런트엔드를 쓰면 로고·저작권 표시를 지우거나 고치지 못하게 한다(`LICENSE:10-12`). 그 정의는 `web/` 디렉터리인데 레포에는 `web/`이 없고 `frontends/`만 있어서(`git ls-files`), 읽기 화면을 가져올 때 범위를 소유자에게 확인해야 한다. 2a는 소유자가 라이선스를 "at its sole discretion" 조이거나 풀 수 있다고 적는다(`LICENSE:16`). 그래서 코드를 가져온다면 가져온 commit의 LICENSE 사본을 남긴다. 모르는 것: 한 회사가 부서별 workspace를 여럿 운영하는 것이 1a 조항의 "multi-tenant deployment"에 드는지. 라이선스 소유자에게 물어야 안다 |
| 성숙도 | JonexWiki 테스트는 공개본에 없다. `pyproject.toml`은 `testpaths = ["tests"]`를 두지만 폴더가 없고, `.gitignore:99-101`이 "Test files — keep local, never commit"이라고 적는다. CI workflow가 없다(`.github/`에는 `ISSUE_TEMPLATE`와 PR 템플릿뿐). 태그·릴리스가 없다(`git tag` 결과 없음). 플랫폼 테스트는 `capabilities/knowledge_base/tests/` 파일 2개뿐이다 |
| 이유 문서의 자리 | 코드 주석이 가리키는 내부 계획서(S5~S7, AC-00x, §n, "Wave 3")는 공개본에서 빠졌다: "Internal planning documents … removed from the public source tree"(`CHANGELOG.md:20-22`). 공개 이력도 squash되어 있다(`f6205dc` "Squashed several dozen commits"). 그래서 이 보고서의 "작성자가 밝힌 이유"는 코드 주석·docstring·마이그레이션 머리말·이슈 답글에서 나온다 |

## 큰 구조

층은 셋이다. 플랫폼이 KB 종류로 갈래를 나누고, `jonex-wiki` 컨테이너 안의 한 프로세스가 작업 큐로 compile·query·outline을 돌리고, 결과는 DB 메타데이터와 불변 bundle 디렉터리에 남는다.

```
[플랫폼]  브라우저 → api_gateway(8000) → sidecar /invoke → knowledge-base-service(8003)
           ├ kb_type 갈래: lightrag(그래프) | openkb(OpenKB 복사본) | jonex_wiki
           ├ task center 편성 parse_1 → compile_1
           ├ 파싱: atomic-rag + MinerU, parse_only → 공유 볼륨에 content_list.json
           └ 30초 순찰: jonex_wiki 문서를 KB 단위로 묶어 엔진에 넘기고 종단 상태를 회수
                     │ sidecar /invoke (atomic.jonex_wiki.v1)
[jonex-wiki 컨테이너, 프로세스 하나]
  JonexWikiCapability ─ import ─▶ WikiApplication (JW/application.py)
     TaskExecutor (asyncio, 세마포어 parse 2 / compile 2 / query 4 / outline 2)
       ├ parse_runner   → source_prep (체검·패킹) → source_artifacts.jsonl          [코드]
       ├ compile_runner → LLMWikiV1Engine.compile (C/engine.py)
       │     ├ layered(기본): 이해 UnderstandingStage [LLM] → 배치 organize_sources [코드 + 제한된 LLM]
       │     ├ legacy:        passage마다 select_and_compile [LLM] + Error Book 고리
       │     └ 공통 발행 꼬리: 관계·링크·렌더·색인·bundle 쓰기                          [코드]
       ├ query_runner   → run_query_algorithm: 탐색 루프 [LLM] + 근거 상태·인용 복원 [코드]
       └ outline_runner → 목차 초안 [LLM] + 정리 sanitize [코드]
     reading API (bundle_reader, page_merge)                                         [코드]
  모델 호출: ModelPortAdapter → MeteredGw → GwClient → llm-gateway(8787)
  저장: PostgreSQL schema jonex_wiki 표 5개 + {data_root}/{tenant}/{kb}/ 파일 트리
```

출처: 플랫폼 경로는 `deploy/docker-compose.yml:1126-1200`, `KB/task_runner_service.py:26-38`, `KB/reconciliation_service.py:3056-3147`. 엔진 쪽은 `JW/tasks/executor.py:31-34`, `C/engine.py:711-777`, `JW/adapters/model_port.py:206-210`이다.

| 구성 요소 | 맡는 일 | 대표 파일 |
|---|---|---|
| 입력 채널 | 웹 업로드, MCP 쓰기 Key 직전송, 데이터 소스(`api` 외부 REST 끌어오기, `storage` 고객 버킷, `api_push` ingest key로 밀어넣기)가 모두 `upload_document`로 합류한다. 데이터 소스 동기화는 external_id로만 중복을 거르고 삭제된 문서도 다시 넣지 않아서, 원 시스템에서 고친 문서는 다시 들어오지 않는다 | `mcp_server/tools.py:299-450`, `KB/data_source_service.py:40, 224-260, 282-329, 359-372` |
| KB 종류 서비스 | 종류를 고르고 생성 뒤 못 바꾸게 막는다 | `KB/kb_type_service.py`, `KB/knowledge_info_service.py:439-452` |
| 순찰(reconciliation) | `stale` 문서를 모았다가 업로드가 조용해지면 KB 단위로 한 번에 넘긴다 | `KB/reconciliation_service.py:3056-3147` |
| 능력 어댑터 | 엔진 상태어·페이지 종류를 플랫폼(OpenKB) 어휘로 바꾼다 | `ADP/jonex_wiki_adapter.py:21-34` |
| `WikiApplication` | ingest·삭제·재컴파일·query·읽기 같은 도메인 동작 | `JW/application.py` |
| `TaskExecutor` | asyncio 작업 큐, 일시정지·취소·재시작 복구 | `JW/tasks/executor.py` |
| kernel ports | 엔진이 의존하는 추상 경계 7종(source·모델·저장소·bundle 보기·취소·진행 보고·시계) | `JW/kernel/ports.py:18-405` |
| source_prep | 파싱 결과 → 블록 → passage, 체검 | `SP/chunking.py`, `SP/screening.py`, `SP/inspect.py` |
| compile 오케스트레이터 | 모드 분기, 이전 bundle 재사용 판정, 발행 꼬리 | `C/engine.py` |
| 이해(understanding) | passage → 원문 발췌 사실, checkpoint 캐시 | `C/understanding.py` |
| 배치(organization) + 동일성 | 사실 → 페이지, 같은 대상 판정 | `C/organization.py`, `C/identity.py` |
| evidence gate + 지지 판정 | 발췌 위치를 찾아 문자 구간 고정, SUPPORTED 판정 | `C/content_validation.py`, `M/claim.py` |
| 사실 장부 | 페이지와 무관한 사실 기록, 출처 철회 | `C/source_contribution.py` |
| Error Book | 문제 기록·등급·수리 | `C/error_book.py` |
| 링크 | 이름 제안 → 페이지 결정, 역링크 색인 | `C/relation_increment.py`, `C/mention_index.py` |
| 렌더 | Markdown·frontmatter·index·backlink | `C/rendering.py` |
| bundle·발행 | 불변 bundle 쓰기, 원자 발행, 버전 정리 | `C/bundle_codec.py`, `JW/adapters/artifact_store.py`, `JW/storage/layout.py` |
| query | route, 탐색 루프, 검색, 근거 상태, 인용 복원 | `Q/router.py`, `Q/algorithm.py`, `Q/retrieval.py`, `Q/controller/evidence_state.py`, `Q/synthesis_orchestration.py` |
| reading | 페이지 목록·읽기·역링크·claims, 같은 제목 병합 투영 | `JW/domain/reading/bundle_reader.py`, `JW/domain/reading/page_merge.py` |
| outline | 읽기 목차 초안·조정·사람 수정 보호 | `JW/domain/outline/` |

저장소는 넷이다.

| 저장소 | 담는 것 | 출처 |
|---|---|---|
| 플랫폼 PG `knowledge_base` | KB 행(`kb_type`), 문서 행의 `llm_wiki_compile_status`(NULL/compiling/compiled/stale/failed), LLM-Wiki Schema 판 | `deploy/postgres/migrations/004_knowledge_base.sql:69-83, 164-199, 600-644` |
| 엔진 PG schema `jonex_wiki` | `documents`, `tasks`, `prompt_templates`, `query_tasks`, `wiki_outlines` | `JW/storage/models.py:18-113` |
| 파일 `{data_root}/{tenant}/{kb}/` | `parse/{doc}/gen-{N}/`(파싱 세대), `checkpoints/`(이해 결과), `compile/staging/`, `compile/versions/{bundle_sha}/`, `published` symlink | `JW/storage/layout.py:47-141` |
| bundle 한 벌 | `wiki/**.md`, `claims.jsonl`, `query/navigation.json`, `query/source_index.json`, `indexes/lexical.sqlite`(FTS5), `indexes/dense.json`, `indexes/links.json`, `revision.json`, `indexes/manifest.json` | `C/bundle_codec.py:452-485`, runtime 노트 #1.5 |

핵심 자료 구조는 신원(identity)이 어디에 묶이는지로 갈린다.

| 자료 구조 | 신원 | 뜻 | 출처 |
|---|---|---|---|
| `ArchivedPassage` | `passage_id` | LLM 호출 하나의 입력 단위. `context_text`는 "must never be used as evidence" | `M/compiler_state.py:385-424` |
| `SourceSpan` | 출처·passage 해시 + `start_char`/`end_char` | 근거의 문자 구간. frozen, `len(text)==end-start` 검사 | `M/compiler_state.py:427-483` |
| `ValidatedClaim` | `claim_id` = sha256(페이지 경로, 문장, 근거)[:24] | 페이지에 실린 사실 한 줄과 판정 | `C/content_validation.py:154-239, 490-507` |
| `SourceContributionRecord` | `record_id` = 출처 버전 + span 위치 + 정규화 명제의 해시 | 페이지 경로를 뺀 사실 한 건. `displays`에 (페이지, claim_id)를 단다 | `C/source_contribution.py:70-89, 131-153` |
| `ErrorBookEntry` | sha256(분류, 코드, 현상, 영향 경로)[:24] | 문제 하나와 등급·constraint·수리 이력 | `C/error_book.py:290-375, 545-557` |

## 한 바퀴 흐름

### ingest: 원문에서 페이지까지

기본 `layered` 모드 기준이다. 표시 `[LLM]`은 모델이 판단하는 단계, `[코드]`는 결정적 단계다.

1. [코드] 플랫폼 업로드가 storage_key의 테넌트 구간, 쿼터, 같은 KB 안 md5 중복을 검사하고 task center 편성 `definition-file-processing-jonex-wiki`(parse_1 → compile_1)에 넘긴다(`KB/document_service.py:427-679`, `KB/task_runner_service.py:26-38`).
2. [코드] atomic-rag가 MinerU로 파싱해 `parsed/{doc}/content_list.json`을 공유 볼륨에 쓴다. xlsx·xlsm은 원본 이진 파일을 넘긴다(`KB/task_runner_service.py:205-206`, `KB/jonex_wiki_service.py:67-104`).
3. [코드] compile 단계는 컴파일하지 않는다. 문서를 `stale`로 표시만 한다(`KB/jonex_wiki_service.py:427-477`).
4. [코드] 30초 순찰이 KB마다 업로드 창이 조용한지 본다. 파싱 중 문서가 없고 5초 안에 `stale`이 된 문서가 없으면, ready+stale 문서 전부를 한 번의 `compile_parsed_documents`로 엔진에 넘긴다(`KB/reconciliation_service.py:3072-3137`).
5. [코드] 엔진 `ingest_parsed_document`가 경로를 검사하고, 파일 이름으로만 입력 경로를 정하고, 체검으로 담을 수 없는 단위를 `gen-N/source-archive/`에 격리하고, 블록을 패킹(목표 4,000 추정 token, 상한 5,000)해 `source_artifacts.jsonl`에 원자적으로 쓴다. 그 KB에 queued compile이 있으면 거기에 합친다(`JW/application.py:246-398`, `SP/chunking.py:35-49`).
6. [코드] compile runner가 KB compile lock을 잡고, 같은 KB의 파싱이 끝날 때까지 기다리고, manifest와 문서 스냅숏을 고정한다(`JW/domain/compile_task.py:41-119`).
7. [코드] 엔진이 source마다 fingerprint를 만든다. 입력이 하나도 안 바뀌었으면 원문을 다시 읽어 재확인한 뒤 이전 revision을 그대로 재사용한다. 이때 모델 호출은 0회다(`C/engine.py:494-540, 615-659`, `C/digest.py:73-124`).
8. [LLM] 이해: passage마다 최대 2회(첫 시도 + 재시도 1회) 부른다(`C/understanding.py:93, 1010-1053`). 모델은 passage와 그 메타만 보고, 원문 그대로의 발췌와 `topic_hint`·`original_names`·`aliases`·`mentions`·`relations`를 낸다. checkpoint 캐시가 맞으면 부르지 않는다(`C/understanding.py:399-459, 933-1053`).
9. [코드] 모델이 준 id 11개 필드를 지운다. 발췌가 passage 안에 있는지 보고, evidence gate로 `SourceSpan`을 고정하고, 지지 판정을 해서 `SourceContributionRecord`를 만든다(`C/understanding.py:545-777`, `C/content_validation.py:446-487`, `M/claim.py`).
10. [코드] 배치: record마다 대표 이름(topic_hint → 가장 긴 원표기 → 대문자 연속 → 명제 앞 80자)을 고르고 규칙으로 페이지를 정한다(`C/organization.py:295-315, 499-538`).
11. [LLM, 조건부] 규칙이 정하지 못한 case만 한 호출에 8개씩, 후보 페이지 4개 이하로 묻는다. compile당 호출은 8회까지다. `same`이면서 제시한 후보 경로를 정확히 댈 때만 합치고, 나머지는 독립 페이지가 된다(`C/organization.py:92-94, 620-657, 740-758`).
12. [코드] materialize: 페이지 본문은 evidence gate를 통과한 claim 문장의 글머리표 목록이다. 새 페이지 경로는 `pages/<ASCII>-<sha256(source_id, 이름)[:12]>.md`다(`C/organization.py:279-283, 350-409, 761-841`).
13. [코드] 엔진이 사실 장부를 이전 장부와 재조정하고(출처가 사라진 사실 철회), Error Book을 정리한다(`C/engine.py:1306-1363`, `C/source_contribution.py:384-508`). 이전 발행본이 있으면 원문을 한 번 더 읽어 바뀌었을 때 실패시킨다(`C/engine.py:1328-1348`). 첫 compile에서는 이 재확인이 없고 15단계의 셸 관문만 입력 변화를 본다(`C/engine.py:724, 1335`).
14. [코드] 공통 발행 꼬리: 관계 투영(링크 결정), 디렉터리 shard, SUPPORTED가 아닌 claim의 격리(Quarantine), query corpus, claim 정책, lexical 색인, revision id, bundle 파일을 만든다. dense 색인은 `QUERY_DENSE=on`일 때만 임베딩을 부른다(`C/engine.py:779-1116`).
15. [코드] 셸 관문: 원천이 있는데 0페이지이거나, 원천 수가 늘었는데 페이지가 50% 넘게 줄면 발행을 거부한다. 발행 직전 입력을 다시 보고, 바뀌었으면 같은 작업 안에서 다시 돈다. 이때 발행하지 않은 후보를 이전 bundle로 넘겨 바뀌지 않은 source는 재사용한다(`JW/domain/compile_task.py:276-286`). 통과하면 `os.replace`와 symlink 교체로 발행하고, 옛 버전을 정리하고, outline 작업을 따로 넣는다(`JW/domain/compile_task.py:147-212, 276-286`, `JW/storage/layout.py:119-162`).
16. [LLM] outline: 페이지 목록(500개까지)으로 목차 초안을 받고, [코드] `sanitize_outline`이 목록에 있는 경로만 남기고 제목을 엔진 제목으로 덮어쓴다(`JW/domain/outline/service.py:147-188`, `JW/domain/outline/outline.py:240-362`).

`legacy` 모드는 8~12 대신 논문 Algorithm 1을 돈다. [코드] 페이지 메타와 passage 토큰 겹침으로 후보 페이지를 고르고, [LLM] passage마다 한 번 페이지 선택(5개 이하)과 수정안·claim을 함께 받고, [코드] 구조 gate·evidence gate를 지난 것만 받아들인다(`C/repair/acceptance.py:152-781`, `C/repair/blocking.py:124, 142-232`).

문제는 Error Book에 기록되고, open constraint(12개 이하)가 다음 passage 프롬프트에 들어가고, 50 batch마다 [LLM] 수리 라운드가 돈다(`C/error_book.py:609-718, 1104-1234`, `JW/infra/settings.py:91`).

표(`table_observation` 블록)는 LLM compile에 들어가지 않는다. `compile_table_values: False`라서 passage 순서에서 빠지고 `tables.sqlite`·표 보기 페이지·원문 페이지로만 발행된다(`SP/blocks.py:272`, `C/pipeline.py:424`, `C/understanding.py:1108-1111`).

이것은 MinerU·xlsx 입력 경로 기준이다. 그 밖의 파일이 타는 TEXT_DIRECT 경로(`JW/application.py:260-271`)에서는 markdown 표가 passage에 남고, 지지 판정이 표 행 단위와 합계 파생 규칙으로 따로 본다(`M/claim.py:521-538, 541-590`).

표는 compile 밖에서 따로 다룬다. 이 하위 체계는 JonexWiki의 약 9,200줄(파일 11개, 전체의 16%)이고(`wc -l`로 셈), 세 장치로 이뤄진다.

| 장치 | 하는 일 | 출처 |
|---|---|---|
| 머리글 해석 | 다층 머리글은 원문 병합 셀이 받칠 때 두 모양만 승격한다. 제목처럼 보인다고 행을 건너뛰지 않는다 | `SP/header_interpretation.py:1-40` |
| 제한 실행 `table_compute` | 모델은 표 handle·열·필터·작은 연산 하나만 고르고 SQL이나 식은 못 낸다. "Every result carries the source rows/cells that produced it"(결과마다 그것을 만든 원 행·셀이 붙는다) | `Q/table_query.py:1-6` |
| Decimal 계산 | 수치 계산과 단위·일관성 검사를 Decimal로 한다 | `Q/numeric_calculate.py`, `Q/numeric_units.py`, `Q/numeric_consistency.py` |

### query: 질문에서 답까지

1. [코드] 질문(1~4096자)을 받으면 그 순간의 발행본 `bundle_sha`를 `query_tasks` 행에 박는다. 삭제된 문서가 든 발행본이면 409를 낸다(`JW/application.py:599-616`, `JW/domain/source_visibility.py:18-23`). 결과는 비동기이고, 플랫폼은 0.5초 간격으로 240초까지 폴링한다(`ADP/jonex_wiki_adapter.py:43-47`).
2. [코드] 고정한 버전 디렉터리를 열고 소유자·revision·체크섬을 확인한 뒤 조회용 투영을 읽는다. query가 받는 claim은 SUPPORTED이고 격리되지 않은 것뿐이다(`Q/published_projection.py:43-99`, `C/publication.py:48-52`).
3. [코드] 질문 문자열을 정규식 표에 대 route를 정한다: SUMMARY, CHAPTER_TREE, LEXICAL, 나머지 PROPOSITION(`Q/router.py:46-120`).
4. [코드] 첫 행동을 코드가 강제한다. 모델에게 묻지 않고 `wiki_read(["index.md"])`를 실행한다(`Q/algorithm.py:1827-1850`).
5. [LLM] 탐색 루프: 모델이 도구 6종(`wiki_search`, `wiki_read`, `table_inspect`, `table_locate`, `table_read`, `table_compute`)을 부른다. 상한은 도구 24회, 총 360,000 token, 180초다(`Q/algorithm.py:1931-2236`, `JW/infra/settings.py:138-148`).
6. [코드] `wiki_search`는 jieba 분절 + FTS5 BM25(열 가중치 title 8, alias 6, tag 4, description 3, body 1)다. 결과는 후보일 뿐 근거 handle을 받지 않는다(`Q/retrieval.py:530-551, 892-944`, `Q/traversal_executor.py:5409-5417`).
7. [코드] `wiki_read`는 읽은 페이지의 SUPPORTED claim 근거와 원문 구간 레코드를 근거 사건으로 등록한다. claim이 하나도 승인되지 않은 페이지는 그 페이지를 만든 원문 구간을 대신 준다. active 창은 12개, 문서당 6개다(`Q/traversal_executor.py:1205-1220, 5599-5760`).
8. [LLM] 답 쓰기 턴(기본 natural 모드): 탐색 메시지를 물려받지 않은 새 대화에서 전달된 근거만 보고 `[E#]` handle로 인용한 답을 쓴다(`Q/synthesis_orchestration.py:945-1105`).
9. [코드] `[E#]`를 근거 대장에서 여섯 필드(`claim_id`, `passage_id`, `source_id`, `document_id`, `chunk_id`, `excerpt`)로 되살리고 모르는 handle은 버린다. 답의 숫자가 `table_compute` 결과와 어긋나고 그 불일치가 정해진 종류(비교 방향 충돌, 단일 단계 결과를 직접 인용한 경우 등)일 때만 `incomplete=True`로 바꾸고, 나머지는 advisory로 trace에 남긴다(`Q/synthesis_orchestration.py:719-757, 875-942`, `Q/algorithm.py:2418-2446`).
10. [코드] 플랫폼으로 내보내는 trace는 허용 목록의 이벤트·필드만 남긴다(`JW/domain/query/query_task.py:36-93`).

SUMMARY route는 모델 답을 버리고 검증된 인용 발췌를 1,500자까지 나열한 결정적 요약으로 바꾼다. "No RAPTOR, no extra model call."(`Q/traversal_executor.py:555-633`).

### 유지보수: lint·재컴파일·병합

별도 lint 명령은 없다. compile 안의 gate(구조 검증, evidence gate, Error Book 등급)가 그 일을 한다.

1. [코드] 원문이 바뀌면 그 문서의 파싱 세대가 오르고 compile이 예약된다. 재ingest는 내용이 같아도 세대를 올린다(`JW/application.py:289`). 이해 cache key와 checkpoint 검사에 세대와 위치가 들어가므로(`C/understanding.py:428-434, 801-806`) 재파싱한 문서는 passage 전부를 다시 이해한다. 바뀌지 않은 다른 문서의 passage만 checkpoint로 LLM 호출을 건너뛴다.
2. [코드] 지지 규칙만 바뀐 경우 LLM 없이 저장된 발췌로 판정만 다시 한다(`C/understanding.py:813-850`).
3. [코드] 배치는 매 compile마다 처음부터 다시 돈다. 출처가 모두 그대로이고 record 집합이 같은 페이지만 이전 스냅숏을 쓴다(`C/organization.py:982-995, 1036`).
4. [LLM, 조건부] 동일성 미정 case는 매 compile마다 다시 묻는다. 판정 결과를 저장하는 곳이 없다(`C/organization.py:441, 656`).
5. [코드] 출처가 삭제되면 그 출처만 받치던 사실은 철회되고 Error Book에 Advisory로 남는다. 다른 출처가 받치는 사실은 남는다(`C/source_contribution.py:384-508`, `C/engine.py:74-111`).
6. [LLM, 조건부] 끝에 Error Book 정리(최대 3라운드)가 돈다. open Blocking이 없으면 LLM을 부르지 않는다(`C/error_book.py:900-919, 1242-1310`).
7. [코드] 누락 수리는 사람이 확인한 누락만 원문 구간 그대로 덧붙인다. 확인서를 넘기는 생산 경로는 연결되어 있지 않다(`C/omission_repair.py:3-23`, `C/engine.py:382`).
8. [코드] 병합: compile은 출처를 넘는 자동 병합을 하지 않는다. 읽기 화면만 정규화 제목이 같은 페이지를 한 묶음으로 보여 준다(`JW/domain/reading/page_merge.py:43-149`).
9. [코드] 롤백은 대상 bundle의 무결성을 다시 계산한 뒤 symlink만 바꾼다. 재컴파일은 없다(`JW/api/routers/compile.py:68-114`). 다만 이 라우터는 엔진을 독립 FastAPI로 띄울 때만 있다. 플랫폼 배포의 `jonex-wiki` 컨테이너는 `deploy/start_capability.py`만 띄우고(`deploy/docker/jonex-wiki.Dockerfile` 마지막 줄), 능력 어댑터의 action 목록에 rollback이 없다(`ADP/jonex_wiki_adapter.py:183-192`). 그래서 플랫폼 사용자는 롤백할 수 없다.
10. [코드] 사용자 compile 선호 문구를 바꾸면 compile이 자동 예약되고, 그 해시가 manifest에 들어가 재사용이 무효가 된다(`JW/application.py:816-817`, `JW/adapters/manifest.py:65-72`).

## 왜 이 구조인가

[추정] 결정 19개를 묶는 모양은 셋이다(사례: 모양마다 대표 결정 칸의 결정들, 각 4~7개).

| 모양 | 뜻 | 대표 결정 |
|---|---|---|
| LLM의 권한을 좁힌다 | 모델은 발췌를 고르고 이름을 제안할 뿐이고, 신원·페이지·판정·링크는 코드가 정한다 | 4, 5, 6, 7, 8, 9, 15 |
| 아무것도 조용히 잃지 않는다 | 거부한 사실·빠진 단위·지지 안 된 claim을 버리지 않고 기록하거나 원문으로 남긴다 | 10, 11, 14, 16 |
| 운영 사고가 기본값을 정했다 | 주석이 "真实事故"(실제 사고)·"实测"(실측)를 근거로 든 결정이 많다 | 2, 6, 12, 13, 14, 19 |

이력으로 바뀐 이유를 추적하기는 어렵다. JonexWiki가 commit 하나로 들어왔기 때문이다(`git log -- Reference/JonexWiki` 결과 1개). 그래서 "이력" 칸은 코드 주석·마이그레이션·규칙 버전 문자열이 가리키는 변경만 적는다.

### 1. 엔진을 KB 종류 셋으로 나누고, 종류는 생성 뒤 못 바꾼다

- **결정**: KB는 `lightrag`·`openkb`·`jonex_wiki` 중 하나다. llm-wiki 문서는 "只解析产出 markdown，不写 LightRAG/Neo4j"(파싱으로 markdown만 내고 LightRAG/Neo4j에 쓰지 않는다)(`KB/document_service.py:681-682`). 종류 변경은 거부한다.
- **대안**: 한 KB에서 그래프와 wiki를 둘 다 만들기. KB마다 본체 추출을 켜고 끄는 토글(이슈 #31이 물은 것).
- **작성자가 밝힌 이유**: 배타의 이유는 "KB 级互斥，避免与 OpenKB 双写"(KB 단위 상호 배제로 OpenKB와 이중 쓰기를 피한다)다(`Reference/Rag-anything/raganything/service/task_manager.py:2414, 2959`, `f6205dc`). 불변의 이유는 "改类型意味着旧数据全部失效 … 没有安全的原地切换路径"(종류를 바꾸면 옛 데이터가 전부 무효가 되고 안전한 제자리 전환 길이 없다)다(`KB/knowledge_info_service.py:439-442`). 유지보수자는 이슈 #31 답글(2026-09-16)에서 대가를 인정했다: "kb_type is immutable after KB creation, and openkb has no LightRAG vector index—what is lost is not just the graph, but vector retrieval itself"(그래프만이 아니라 벡터 검색 자체를 잃는다).
- **[추정] 이중 쓰기를 피한 이유**: 문서마다 컴파일 상태의 원천을 하나로 두고, 화면에서 두 길을 다른 쓰임새로 내놓으려 했다(사례 3개: 상태 열 분리 `KB/document_service.py:102-106`, 화면 문구 "适合实时问答" 대 "适合知识沉淀与深度理解" `zh.json:1524-1526`, 이슈 #31 답의 "coarser than expected"). LLM 비용을 두 번 쓰지 않으려 했다는 직접 근거는 없다.
- **이력**: "KB 级互斥"와 `kb_type_immutable`은 둘 다 `f6205dc`(2026-08-12)에 처음 나온다(`git log -S`). 못 찾은 종류를 `lightrag`로 떨어뜨리던 함수 때문에 wiki 문서가 "编译成功"으로 잘못 판정된 뒤 엄격판 `get_kb_type_or_none`을 "2026-10-09 加"(더했다)(`KB/kb_type_service.py:148-156`).

### 2. OpenKB를 들여오고도 JonexWiki를 따로 만들었다

- **결정**: OpenKB(문서 하나씩 `compile_short_doc`)를 플랫폼에 붙인 뒤, 별도 엔진 JonexWiki를 세 번째 종류로 더했다.
- **대안**: OpenKB에 claim 근거와 증분 컴파일을 덧붙여 고쳐 쓰기.
- **작성자가 밝힌 이유**: 없다. `a8bee87`의 메시지는 제목 "feat(jonex-wiki): wiki engine integration with outline and page references"와 Co-Authored-By 한 줄뿐이다. 엔진 설계 문서 `docs/jonex_wiki/*.md`는 `.gitignore:307-312`로 빠졌다.
- **[추정] 동기 1, 인용 추적**: OpenKB 인용은 약했고 JonexWiki는 claim마다 문자 구간을 단다(사례 3개: `f6205dc`의 openkb 설명 "暂不支持引用溯源"(아직 인용 출처 추적을 지원하지 않음)이 `a8eb6f6`에서 지워짐, OpenKB 인용은 에이전트가 읽은 경로에서 문서를 거꾸로 찾는 문서 단위 `KB/search_service.py:7157-7175`, JonexWiki `SourceSpan` `M/compiler_state.py:427-483`).
- **[추정] 동기 2, 표·구조 문서**: JonexWiki는 MinerU 구조 배열과 xlsx 원본을 직접 받는다(사례 2개: `KB/jonex_wiki_service.py:31-35, 67-76`, 산출물이 `content.md`로 조용히 물러나 표·캡션이 사라졌던 "真实事故" `JW/application.py:54-64`). OpenKB 경로는 `content.md`만 받는다.
- **[추정] 동기 3, 재컴파일 안정성**: OpenKB는 페이지를 제자리에서 고쳐 쓰고 JonexWiki는 불변 revision을 다시 만든다(사례 2개: 이슈 #22 재컴파일 때 중복 concept 페이지 보고(재현 확인 안 됨), `C/engine.py:1152-1155` "Unchanged pages are reused only when their source versions and record sets still match").
- **이력**: 플랫폼 코드의 `"jonex_wiki"` 문자열은 `0541be3`(2026-09-23)에, 엔진 소스는 `a8bee87`(2026-10-10)에 처음 나온다. [추정] 엔진은 그 전부터 따로 개발되었다(사례 3종: `JW/application.py:3-6` "独立引擎 FastAPI 服务", `JW/domain/compile_task.py:1-5` "旧 dev 的 allocator/page_compiler/gates/incremental/indexes 编译管线整体替换为 LLMWikiV1Engine.compile", "Extracted verbatim from engines/llm_wiki_plus/…"가 모듈 13개에 있고 "Ported from ``llm_wiki_plus/…``"가 `Q/read_views.py:3`에 한 번 더 나옴). README는 그보다 앞선 `3587e4e`(2026-09-08)에서 이미 "Dual Engines of Jonex Wiki and Graph Ontology"라고 적는다(`README.md:7`). 모르는 것: 그때 코드의 llm-wiki 종류는 openkb뿐이어서, 이 이름이 JonexWiki를 가리켰는지 openkb를 가리켰는지는 모른다. 그 무렵 화면 문구나 문서에서 "Jonex Wiki"가 무엇을 부르는지 보면 알 수 있다.

### 3. compile 뼈대로 논문 Algorithm 1과 Error Book을 썼다

- **결정**: `legacy` 모드는 passage마다 SELECTPAGES(기존 페이지 5개 이하) → COMPILEWIKIPAGES(active constraint 포함) → 구조·내용 검증 → Error Book 기록 → 주기 수리로 돈다(`M/compiler_state.py:1-17, 30`, `C/error_book.py:4-9`).
- **대안**: Karpathy 원형처럼 LLM이 페이지를 읽고 고쳐 쓰는 대화형 ingest.
- **작성자가 밝힌 이유**: 코드는 논문 이름을 적지 않고 "Paper-required behaviour/behavior fixed here"(`C/rendering.py:9`, `C/content_validation.py:11`, `C/structural.py:9`), "Paper-required facts fixed here"(`M/compiler_state.py:8`), "the paper pipeline"(`C/error_book.py:4-5`)이라고만 쓴다. 논문(Ming·Li·Wu·Que, WeChat, Tencent, arXiv 2605.25480)은 "flat chunks reduce retrieval to matching, not reasoning"(평평한 청크는 검색을 추론이 아닌 맞추기로 만든다), "the bottleneck lies in how knowledge is organized and exposed to the agent"(병목은 지식을 어떻게 조직해 에이전트에게 내보이느냐다)라고 적는다(https://arxiv.org/html/2605.25480v2, why 노트 J4). Jonex가 더한 부분은 따로 밝힌다: "Passage IDs, stable claim IDs, issue schemas and line-ending-only normalization are Jonex engineering adaptations"(`C/content_validation.py:19-20`).
- **[추정] 구현한 논문**: 2605.25480이다(사례 5개: 함수 이름 `SELECTPAGES`/`COMPILEWIKIPAGES` `M/compiler_state.py:3-4`, 선택 상한 k=5 30행, Error Book 필드 "phenomenon, root cause, constraint, verification" `C/error_book.py:290-303`, 최종 3라운드 수리 1263행, 논문의 "re-validation period of every 10 compilation batches"(10 batch마다 재검증)에 맞춘 듯한 수리 라운드 간격 함수 기본값 10 `C/error_book.py:1114`). 논문은 LLM 주기 수리 간격을 "every NN articles"로만 적고 값을 주지 않는다(https://arxiv.org/html/2605.25480v2 §3.3, §4.4).
- **논문에서 바꾼 곳**: 선택과 컴파일을 한 호출로 합쳤다: "Collapses SELECTPAGES + COMPILEWIKIPAGES into a single model call per passage (2 → 1)"(`M/repair_models.py:122-123`). 원인 분석을 LLM에서 틀 문구로 바꿨다: "The detector already supplies a typed category, object and reason. Preserve that finding; a second model call cannot prove its cause."(탐지기가 이미 분류·대상·이유를 준다. 두 번째 모델 호출은 원인을 증명할 수 없다)(`C/error_book.py:1181-1182`). 내용 검증을 결정적 규칙으로 바꿨다(결정 6). 등급을 더했다(결정 11).
- **이력**: [추정] 예전에는 LLM 원인 귀속 호출이 있었다(사례 3개: 쓰이지 않는 `ErrorAttributionBatch` 스키마 `C/error_book.py:260-271`, docstring에 남은 "attribute new errors" 단계 7행, 대체 주석 "a second model call cannot prove its cause" 1181-1182행). 수리 간격 기본값은 50인데(`JW/infra/settings.py:91`) 함수 기본값은 10이다(`C/error_book.py:1114`). 모르는 것: 50으로 늘린 이유. 내부 계획서가 있어야 안다.

### 4. 원문 읽기와 페이지 배치를 두 단계로 떼었다(layered, 기본)

- **결정**: 이해 단계는 페이지를 모른 채 passage에서 사실을 읽고, 배치 단계는 코드 규칙과 제한된 LLM으로 페이지를 정한다. 이해 결과는 페이지와 무관한 key로 캐시한다.
- **대안**: `legacy`의 결합 호출. 지금도 `JONEX_WIKI_COMPILE_MODE=legacy`로 고를 수 있다(`deploy/.env.jonex_wiki.example:222-224`).
- **작성자가 밝힌 이유**: "a page layout change re-asks the model about unchanged source text, and a failed page organization throws away a perfectly good reading of the source"(페이지 배치가 바뀌면 그대로인 원문을 다시 묻고, 페이지 조직이 실패하면 멀쩡한 원문 읽기를 버린다)(`C/understanding.py:3-7`). "page paths, page titles and target-page choices are deliberately absent from the cache identity, so reorganising pages never invalidates source understanding"(115-117행). 순서: "organization commits in stable input order … so completion order cannot change the published fact set"(완료 순서가 발행 사실 집합을 바꾸지 못한다)(`C/organization.py:27-29`). 꼬리: "Layered does not get its own copy of the engine."(`C/engine.py:701-705`).
- **key에 남는 것**: 페이지 배치는 빠지지만 compile 선호 문구는 들어간다: "the instruction body and the caller's compile prompt are model input, and editing either must make a stored understanding a miss"(`C/understanding.py:373-385`). 문서 세대와 passage 위치도 들어간다(428-434행). 그래서 문구를 고치거나 문서를 다시 파싱하면 그만큼 이해를 다시 한다.
- **포기한 것**: 논문이 효과를 잰 constraint 주입 고리가 layered에서는 돌지 않는다. `build_state`가 `active_constraints=[]`로 시작하고 layered에는 되먹이는 코드가 없다(`C/pipeline.py:431`). 논문 ablation은 Error Book을 빼면 F1이 3.4~4.0 떨어진다고 적는다(compile 노트 #논문 출처).
- **이력**: 공개 이력에는 처음부터 둘 다 있다. 주석의 단계 번호로 보면 legacy(AC-00x) 다음에 layered(S7.x)가 왔다. 모드는 컴파일 신원에 들어간다: "legacy and layered compile different things, so switching modes must invalidate a previous bundle"(`C/engine.py:68-71`).

### 5. 페이지 본문을 LLM이 쓰지 않는다

- **결정**: layered 본문은 evidence gate를 통과한 claim 문장의 글머리표 목록이고, 순서는 입력 순서다. legacy도 본문을 코드가 덧붙인다.
- **대안**: Karpathy 원형처럼 LLM이 페이지를 요약·재작성하기.
- **작성자가 밝힌 이유**: "No LLM rewrites the page: the body is the ordered list of the claims the evidence gate already accepted, one bullet each"(`C/organization.py:361-364`). legacy 프롬프트: "Do not output page prose or repeat old facts. The compiler appends admitted facts itself."(`C/repair/acceptance.py:325-327`). 원문이 바뀔 때: "Draft page prose is discarded on a source change: published facts are the source-grounded claims, not an old model-written paragraph."(`C/block_replay.py:42-43`).
- **포기한 것**: 사람이 읽기 좋은 문장, 여러 출처를 엮은 요약. 출처를 넘는 종합은 query 단계 몫이 된다.

### 6. claim 지지 판정을 결정적 규칙으로 한다

- **결정**: claim이 원문 발췌의 정확한 부분 문자열(대소문자·공백·문장부호 접기)이거나 좁은 변형일 때만 SUPPORTED다. 날짜·숫자·단위·부정·비교 방향은 "보호 원자"로 따로 대조한다. 나머지는 NOT_ENOUGH_INFO다.
- **대안**: 논문처럼 LLM 판정, 또는 NLI 모델. LLM semantic review는 남아 있지만 기본 off다(`JW/infra/settings.py:129`).
- **작성자가 밝힌 이유**: "The checker intentionally proves a small, auditable language instead of pretending to solve unrestricted natural-language inference. … Anything outside those bounded rules is NOT_ENOUGH_INFO."(작고 감사 가능한 언어만 증명하고 자연어 추론을 푸는 척하지 않는다)(`M/claim.py:3-8`). 보호 원자를 둔 이유: "收入为15万元" collapses into "收入为1.5万元" and "支持离线部署" collapses into "官方明确否认支持离线部署"(문장부호를 지우면 15만 위안이 1.5만 위안과 겹치고, "오프라인 배포 지원"이 "공식적으로 지원을 부인함" 안에 들어간다)(`M/claim.py:214-222`).
- **포기한 것**: 바꿔 말한 사실과 여러 문장에서 끌어낸 사실은 NOT_ENOUGH_INFO가 되어 조회 근거에서 빠진다. 읽기 화면은 판정과 무관하게 전부 보여 준다. 실측 2,743개 중 792개만 SUPPORTED였다: "否则 References 会只剩 792 条 supported 支撑的那一部分"(`JW/domain/reading/bundle_reader.py:478-480`, 2,743개는 같은 파일 24행). 규칙의 언어 범위는 영어·중국어뿐이다(부정어 `M/claim.py:90-98`, 날짜 43-48, 토큰 36-39).
- **이력**: "claim-support-v1 was the punctuation-folded substring fast path without protected-atom checks"(v1은 보호 원자 검사 없는 부분 문자열 경로였다). 현재 `claim-support-v3`은 "retains trailing percent units in matched windows"(퍼센트 단위를 유지한다). 옛 규칙의 bundle은 판정을 동결해 둔다(`M/claim.py:25-34`, 이 보고서 작성 때 다시 열어 확인).

### 7. 같은 대상은 증명될 때만 합친다

- **결정**: `decide_identity`의 순서는 명시 id → 관계(선행·후속·모회사·자회사·브랜드)면 다름 → 같은 종류(엔티티/토픽)에서 이름이나 별칭이 맞고 context가 같으면 같음 → 나머지 미정이다(`C/identity.py:99-132`). layered 배치는 그중 "이름 + 같은 context"도 미정으로 낮춘다(`C/organization.py:520-526`). 미정은 제한된 LLM 판정으로 보내고, 그래도 안 되면 따로 둔다.
- **대안**: 이름 일치 병합. 같은 레포의 그래프 길이 그렇게 한다(MERGE 키 `(tenant, kb, entity_type, canonical_name)`). 임베딩 유사도. 후보 함수 `lexical_candidates`는 정의만 있고 부르는 곳이 없다(`C/identity.py:143-162`).
- **작성자가 밝힌 이유**: "a bare name match across different contexts is *undetermined* - two cities with one name are not one entity"(이름이 같은 두 도시는 한 대상이 아니다)(`C/identity.py:11-12`). "Fuzzy names are only *proposed* as candidates … nothing is merged automatically"(퍼지 이름은 후보로 제안될 뿐 자동으로 합쳐지지 않는다)(12-15행). 이름이나 별칭에 같은 context가 붙은 경우는 규칙이 SAME으로 판정한다(122-126행). 낮춘 이유: "Matching source qualifiers may be only a year or a unit. They do not establish that two cross-source entities are one."(겹치는 수식어가 연도나 단위뿐일 수 있다)(`C/organization.py:521-522`). "Co-occurring names (including regex-extracted mentions) never assert identity. Only source understanding's explicit, subject-bound aliases do."(158-159행). "Relations that look like names are not names"(`C/identity.py:17-18`). 상한: "The bound is what keeps 'semantic organization' from becoming an unbounded classification pass."(`C/organization.py:90-91`).
- **실제로 남는 결정적 SAME 경로**: 명시 id를 채우는 코드가 `identity.py` 밖에 없다(`grep explicit_id` 결과 0, 이 보고서 작성 때 다시 확인). 그래서 layered에서 규칙으로 합쳐지는 경우는 "선언 별칭 + 같은 context 문자열"과, 같은 출처가 자기 페이지를 이어 쓰는 경우뿐이다(`C/identity.py:122-126`, `C/organization.py:504-512`). context는 결정적 추출기가 뽑은 기간·퍼센트·금액·단위와 모델 notes를 이은 문자열이다(`C/organization.py:174-179`).
- **판정 상한**: 한 호출에 case 8개, 후보 4개, compile당 호출 8회다. 그래서 compile당 판정되는 case는 최대 64개다(`C/organization.py:92-94, 625-635`, 이 보고서 작성 때 다시 확인). 상한을 넘은 case는 독립 페이지가 되고 `compile_organization_identity_judgment_limited`로 센다.
- **모르는 것**: wiki 길을 그래프 길보다 보수적으로 둔 까닭이 되돌림 비용인지는 모른다. compile 코드에서 되돌림 비용을 말하는 원문을 찾지 못했다(`grep -i 'irreversib\|wrong merge\|false merge\|误合并'` 결과 0). 원문은 동명 이실체("two cities with one name are not one entity", `C/identity.py:11-12`)와 조용한 병합("a silent merge", `C/organization.py:281-283`)만 이유로 든다. 내부 S6/S7 계획서가 있으면 알 수 있다.
- **앞선 schema-glossary 보고서와 다른 점**: 그 보고서는 "원문이 선언한 별칭·명시 id가 있으면 같다"와 "묶음당 LLM 판단 1회"로 적었다. 코드로는 별칭만으로는 부족하고 같은 context가 필요하며, 호출 수는 미정 case 수에 따라 늘어난다.

### 8. 페이지 경로를 (출처, 이름)의 해시로 만든다

- **결정**: 새 페이지 경로는 `pages/<읽을 수 있는 ASCII>-<sha256(source_id, 정규화 이름)[:12]>.md`다.
- **대안**: 이름 slug만 쓰기, LLM이 경로를 고르기(legacy).
- **작성자가 밝힌 이유**: "the wiki path normalizer slugs non-ASCII characters away, so a name-only readable part would let two different Chinese names from one source collide onto one page -- a silent merge."(경로 정규화가 비ASCII 문자를 지우므로 이름만 쓰면 서로 다른 중국어 이름 둘이 한 페이지로 조용히 합쳐진다)(`C/organization.py:279-283`).
- **결과**: 같은 이름이라도 출처가 다르면 처음에는 다른 경로다. 출처를 넘는 합침은 결정 7의 판정을 거쳐야만 일어난다.
- **포기한 것**: 사람이 읽을 수 있는 경로. 한글·한자 이름은 해시만 남는다.

### 9. 모델이 낸 신원을 믿지 않고, 링크도 이름만 제안하게 한다

- **결정**: record·passage·source·document id, 근거 참조는 프로그램이 정한다. 모델은 링크 대상의 경로가 아니라 이름(`target_mention`)만 낸다. 코드는 그 이름이 페이지 하나에만 맞을 때 연결하고, 없거나 여럿이면 클릭할 수 없는 pending으로 둔다(`C/relation_increment.py:111-124, 169-245`).
- **대안**: legacy처럼 모델이 경로를 쓰고 코드가 오타를 고치는 방식(`C/repair/mutation.py:85-123`).
- **작성자가 밝힌 이유**: "the program assigns every identity … and never trusts a model-supplied id"(`C/understanding.py:16-17`). "The model cannot know the internal passage/document ids it must cite, so its identity fields are unreliable. Locate the excerpt within the SAME document only — a coincidental sentence match in a different document must never rebind the evidence to the wrong source."(우연히 다른 문서에 같은 문장이 있어도 근거를 엉뚱한 출처에 묶지 않는다)(`C/content_validation.py:532-535`). "A model may propose a *mention*, a reason to visit and the evidence it saw; it may not name an identity."(`C/relation_increment.py:3-4`).
- **관계 승격**: 타입이 붙은 `supported_relation`은 원문 구간에 "{주어 제목} is the {relation} of {대상 제목}." 문장이 통째로 있고 지지 판정을 통과할 때만 된다. 아니면 navigation 링크로 낮춘다(`C/relation_increment.py:138-166, 192-195`). 관계 종류는 predecessor·successor·parent·subsidiary·brand 다섯이다(`C/identity.py:35`). 모르는 것: 왜 이 다섯인지.

### 10. 사실 장부를 페이지와 떼어 둔다

- **결정**: `record_id`는 출처 버전 + 근거 위치 + 정규화 명제의 해시이고 페이지 경로를 품지 않는다. 페이지는 장부를 투영한 결과이고, 장부의 `displays`가 (페이지, claim_id)를 가리킨다(`C/source_contribution.py:70-89, 131-153`).
- **대안**: 페이지 경로를 품은 `claim_id`만 두기.
- **작성자가 밝힌 이유**: "The same source fact shown on two pages therefore has two unrelated identities, and removing one page deletes 'the fact' as far as the compiler can tell."(같은 사실이 두 페이지에 나오면 무관한 신원이 둘 생기고, 한 페이지를 지우면 컴파일러는 사실이 지워졌다고 본다)(`C/source_contribution.py:3-6`). 이해 단계도 같은 장부로 들어간다: "exactly one contribution ledger and no second source-of-truth"(`C/understanding.py:11-26`). 거부도 기록한다: "One Error Book row per refused contribution, never a silent drop"(`C/engine.py:75-80`).
- **효과**: 출처가 삭제되면 그 출처만 받친 사실이 철회되고, 다른 출처가 받치는 사실은 남는다(`C/source_contribution.py:384-508`).

### 11. Error Book을 등급으로 나누고 Blocking만 발행을 막는다

- **결정**: Blocking(발행 차단·수리 대상), Quarantine(인용 제외), Advisory(기록만), Transient(제자리 재시도) 넷이다. 다음 passage에 넣는 constraint는 Blocking 우선, Quarantine은 code당 하나, 최대 12개다(`C/error_book.py:609-718`).
- **Quarantine의 효과**: 규칙 판에 따라 다르다. 주석은 "keeps unsupported content out of the query corpus"(지지되지 않은 내용을 조회 코퍼스에서 뺀다)라고 적지만(`C/error_book.py:73-74`), 이것은 옛 evidence-disposition 규칙의 동작이다. 현재 기본 keep-and-search-v1(결정 16)에서는 항목이 가리키는 claim과, 가리키는 source·passage를 인용한 claim만 인용 가능 집합에서 빠진다(`C/publication.py:33-50`, `Q/retrieval.py:1826-1834`). 페이지 본문과 원문 구간은 코퍼스에 남는다(`C/publication.py:134-139`).
- **대안**: 논문처럼 등급 없이 모든 오류를 constraint로 쓰기(논문에는 등급이 없다, WebFetch 요약 기준).
- **작성자가 밝힌 이유**: "A dangling link and a malformed page are both structural issues, but only the latter must stop publication."(`C/error_book.py:71-75`). 등급은 코드가 정한다: "The mapping is deterministic and code-based so a model cannot downgrade a hard structural failure by returning a friendly attribution."(모델이 친절한 원인 설명으로 심각한 구조 실패를 낮출 수 없게)(84-86행). 옛 bundle 항목은 "intentionally Blocking so old bundles fail safe"(297-299행). 주입 상한: "One representative rule per Quarantine code is then injected so recurring grounding errors influence later batches without sending thousands of instance rows to every model call."(700-704행).

### 12. 발행본을 불변 디렉터리로 두고 symlink 교체로 발행하며, 조회는 그 버전에 고정한다

- **결정**: DB에는 상태와 버전 포인터만 둔다. 페이지·claim·색인은 `versions/{bundle_sha}/`에 쓰고, `published` symlink를 바꿔 발행한다. 조회는 제출 때의 `bundle_sha`를 끝까지 쓴다. 버전 정리는 활성본, 최신 이력 2개, 조회가 고정한 버전을 남긴다(`JW/storage/layout.py:119-162`).
- **대안**: 페이지·claim을 DB 행으로 두고 버전 열을 다는 방식, git 저장소.
- **작성자가 밝힌 이유**: "staging→versions(os.replace)+ symlink 切换(单步原子)"(한 단계 원자 전환)(`JW/storage/layout.py:120`). 조회 고정: "Its identity includes owner, revision and manifest checksum, so later reads cannot silently follow a newly published ``current`` pointer."(`JW/kernel/ports.py:305-311`). SQLite를 `mode=ro&immutable=1`로 여는 이유: "so a published bundle can never be mutated by a query"(`JW/adapters/bundle_view.py:152-157`). 손상본 재활용 거부: "Never report success by reactivating the damaged directory while silently discarding the healthy stage."(`JW/adapters/artifact_store.py:123-128`). 정리: "an invalid pointer must never authorize deletion"(`JW/storage/layout.py:151`).
- **[추정]**: 발행본 전체를 원자적으로 바꾸고 롤백을 symlink 교체 하나로 만들려고 이 구조를 골랐다(사례 3개: `publish_bundle`·`activate_version` 2곳, 롤백 라우터가 재컴파일 없이 symlink만 바꿈 1곳).
- **이력**: blob 하나를 저장하는 `put_bundle`이 "Legacy compatibility hook for older test stores"(옛 테스트 저장소용 호환 hook)로 남아 있고 adapter는 "dev layout stores directory revisions, not blob bundles"라며 `NotImplementedError`로 막는다(`JW/kernel/ports.py:129-131`, `JW/adapters/artifact_store.py:57-60`). [추정] 예전 테스트 저장소나 dev 이전 레이아웃은 bundle을 blob 하나로 저장했다(사례 2개). 모르는 것: 운영 경로가 blob이었는지. 비공개 이전 이력이 있어야 안다. `navigation.json`에서 `source_index.json`을 떼어 낸 변경은 이전 스크립트로 확인된다: "大库实测 source_locations 达 258MB"(큰 KB에서 258MB)(`C/bundle_codec.py:446-450`), "接口从 15s+ 降到 <1s"(응답이 15초 넘게 걸리다 1초 아래로)(`Reference/JonexWiki/scripts/migrate_split_source_index.py:5-7`).

### 13. 발행 전에 관문을 두고, 재사용은 다시 증명한 뒤에만 한다

- **결정**: 원천이 있는데 0페이지면, 또는 원천 수가 늘었는데 페이지가 50% 넘게 줄면 발행을 거부하고 옛 bundle로 계속 서비스한다. 이전 revision을 재사용하기 전에 원문을 다시 읽고 발행 head를 다시 본다.
- **대안**: 사람 승인 뒤 발행. 입력이 바뀌었으면 옛 입력으로 발행한 뒤 다음 compile에서 고치기.
- **작성자가 밝힌 이유**: "core 的 publishable 不判页面数"(core 엔진의 발행 판정은 페이지 수를 보지 않는다)라서 셸에서 막는다(`JW/domain/compile_task.py:147-148`). 급감 관문을 원천 수가 늘 때로 좁힌 이유: "源数不变 = 纯重编译/reparse，页面波动来自 LLM 非确定性与解析粒度差异 … （本次 5 → 2 即属此类）"(원천 수가 같으면 페이지 변동은 LLM 비결정성과 파싱 입도에서 온다. 이번 5 → 2가 그 예다)(156-160행). 재사용: "'Unchanged' is a claim about the input this run read. Returning the previous revision republishes it, so the claim is re-proved before it is made"(`C/engine.py:621-626`). 경합: "A parse or prompt edit can commit while the model is working. Keep the task alive and compile the latest inventory; the publication check remains mandatory."(`JW/domain/compile_task.py:277-279`).
- **신원에서 뺀 것**: "调并发/调度器/失败率容忍/修复间隔都不该让上一版 bundle 作废(那会把一次配置调整变成全量重编)"(동시성·스케줄러 설정을 바꿨다고 전체를 다시 컴파일하면 안 된다)(`C/engine.py:58-60`). 반대로 사용자 접미사를 포함한 유효 프롬프트는 신원에 넣는다: "Omitting it makes an explicit compile incorrectly reuse the previous publication"(`JW/adapters/manifest.py:68-70`).

### 14. 패킹에 들어가지 않는 단위만 격리하고 원문은 보관한다(체검)

- **결정**: 패킹 예산을 넘을 단위만 compile 대상에서 빼고, 원문 구간은 `source-archive/`에 남긴다. 체검의 규칙은 "패킹이 터지는가" 하나다.
- **대안**: 문서 전체를 실패시키기. 빈 표·반복·깨진 글자 같은 품질 판정까지 체검에 넣기.
- **작성자가 밝힌 이유**: "一份 296 页文档里某个 OCR 退化的表格行有 6,933 字符，守卫把整份文档判死，而真正该做的是把那一个单元挡在编译面之外、其余照常编译"(296쪽 문서의 OCR 깨진 표 한 행 6,933자 때문에 문서 전체가 실패했고, 그 단위 하나만 빼야 했다)(`SP/inspect.py:3-5`). 범위를 일부러 좁혔다: "内容质量类问题（空表、复读、乱码……）不进这里"(12-15행). 원문을 남기는 이유: "让判据可复核、后续接 VLM 判官时能只对被摘除的部分重跑"(판정을 다시 확인할 수 있고, 나중에 VLM 판정기를 붙이면 빠진 부분만 다시 돌린다)(`JW/application.py:358-359`).
- **이력**: 판정 v1→v2에서 빈 표·반복 판정을 지웠다(`SP/inspect.py:33-35`). 파싱 위치도 한 번 옮겼다가 돌아왔다. `SP/raw_manifest.py:1-4`는 아직 "解析只负责「原样拿到」,归一化/打包/投影全部推迟到 compile"(파싱은 원문만 받고 정규화·패킹·투영은 compile로 미룬다)이라고 적지만, `JW/domain/parsing/parse_task.py:29-31`은 "解析期已恢复 core 的归一化/结构打包/投影"(파싱 단계에서 정규화·구조 패킹·투영을 되살렸다)이라고 적는다(이 보고서 작성 때 다시 열어 확인. why 노트 J10은 raw-only를 현재 동작으로 적었지만 현재 코드는 파싱 단계에서 패킹한다). 모르는 것: 되돌린 직접 이유. 내부 "方案 §12 / §8" 문서가 있으면 안다.

### 15. 조회의 첫 행동·읽기 의무·인용 일치를 프롬프트가 아니라 코드로 강제한다

- **결정**: browse-first 조회의 첫 행동은 코드가 `index.md`를 읽는 것이다. 근거를 등록한 읽기가 없으면 답을 내지 않는다. 모델은 `[E#]` handle만 쓰고 백엔드가 여섯 필드로 되살린다. 답 쓰기는 탐색 메시지를 물려받지 않는 새 경계에서 한다.
- **대안**: 모델이 쓴 인용 문자열을 그대로 믿기. 사후 LLM 검증.
- **작성자가 밝힌 이유**: "The code, rather than prompt wording, must force the first traversal action, require a successful Wiki read before answering, and retain only citations that exactly match evidence exposed by those reads."(`Q/algorithm.py:1-6`). "a fact becomes citable only after a successful read registers its exact six-field evidence record"(`Q/controller/evidence_state.py:3-5`). 경계를 새로 여는 이유: "Final answer generation must not inherit traversal messages: search snippets, old reads, and dropped evidence would otherwise remain visible"(`Q/controller/synthesis.py:1-12`). 목차 읽기는 답을 풀지 않는다: "only a read that registered citable evidence unlocks an answer."(`Q/traversal_executor.py:5735-5737`).
- **작성자가 밝힌 관측**: "A model that keeps issuing distinct ``wiki_search`` calls but never reads a hit wastes the whole tool budget (observed: 13 searches / 1 read)"(모델이 검색만 거듭하고 결과를 읽지 않아 도구 예산을 다 썼다), 옛 상한 6은 "allowed a query to finish without reading any hit"(아무것도 읽지 않고 조회가 끝날 수 있었다)(`Q/traversal_executor.py:225-232`). 모르는 것: 읽지 않은 근거를 인용하는 실패도 있었는지. 직접 근거가 없고, 내부 Wave 3 계획서가 있으면 알 수 있다.
- **이력**: 인용만 따로 뽑는 `CitationExtraction`을 둔 이유: "on long answers made the model emit a large output near the token budget (slow, truncated JSON, all citations dropped)"(긴 답을 다시 쓰게 하니 인용이 전부 사라졌다)(`M/query_models.py:326-339`). [추정] 모델이 여섯 필드를 직접 쓰던 방식에서 handle 방식으로 옮겼다(사례 2개: `CitationDraft`와 부분 문자열 대조 `Q/synthesis_orchestration.py:116-137`가 함께 남아 있음).

### 16. 지지되지 않은 claim도 지우지 않고 원문 구간을 근거로 남긴다(keep-and-search)

- **결정**: 생성 본문을 그대로 두고 모든 원문 구간을 `source-evidence/` 페이지와 검색 레코드로 더한다. claim이 하나도 승인되지 않은 페이지를 읽으면 그 원문 구간을 근거로 준다(`C/publication.py:134-148`, `Q/traversal_executor.py:1205-1220`).
- **대안**: 조회 트리에 SUPPORTED claim 문장만 남기기(옛 규칙).
- **작성자가 밝힌 이유**: "Nothing is deleted because a Claim is missing, unsupported or quarantined: semantic findings are recorded in the Error Book, never turned into a text gate."(`Q/retrieval.py:1785-1791`).
- **이력**: `evidence-disposition-v1` → `v2` → `keep-and-search-v1`(`C/publication.py:14-16`). 옛 두 규칙은 "retained only so previously published bundles can still be cold-opened byte-for-byte"(18-20행). [추정] 지지 판정이 엄격해 쓸 만한 내용이 조회에서 사라지는 문제를 풀려고 바꿨다(사례 2개: `evidence_fallback` 주석 `M/query_models.py:203-216`, 바뀐 기본 규칙). `Q/algorithm.py:10-12` docstring은 아직 옛 규칙을 설명한다.

### 17. 사용자에게 여는 프롬프트는 compile_main 뒤 접미사 하나다

- **결정**: 사용자는 고정 골격 `COMPILE_MAIN_SKELETON` 뒤에 붙는 "编译偏好"(compile 선호) 문구만 고친다. 나머지 18개 프롬프트는 코드 상수다. 플랫폼 "LLM-Wiki Schema" 화면도 jonex_wiki KB에서는 이 접미사만 편집한다(`KB/llm_wiki_schema_service.py:236-246`, `ADP/jonex_wiki_adapter.py:707-721`).
- **대안**: OpenKB처럼 AGENTS.md 전체와 엔티티 종류 통제 어휘를 열기(`KB/llm_wiki_schema_service.py:233-245`).
- **작성자가 밝힌 이유**: "唯一开放的是 compile_main（固定骨架 + 用户「编译偏好」suffix）。其余 18 个全是引擎正确性约束 … 仅消除「暴露但不生效」的入口"(나머지 18개는 엔진 정확성 제약이고, 보이지만 효과 없는 입구를 없앴다)(`JW/domain/prompts.py:18-26`). 골격은 "Every claim must be SUPPORTED by its cited source evidence … never add an unsupported number, date, unit, negation, comparison, table relation, or derived fact"를 고정한다(59-72행).
- **[추정]**: jonex_wiki가 종류 어휘를 두지 않은 것은 신원·근거를 코드 규칙으로 정하기 때문이다(사례 2종: 결정 6·7의 규칙). 근거가 약하다.
- **이력**: 초기 jonex_wiki KB의 schema 행이 openkb 내용으로 잘못 만들어진 적이 있다: "早期创建的 jonex_wiki KB 因 _create_default 未正确按 kb_type 分流"(`deploy/postgres/update/001_repair_jonex_wiki_schema.sql` 머리말).

### 18. 프로세스 하나에서 돌리고, KB마다 compile을 하나로 합친다

- **결정**: 엔진은 PostgreSQL advisory lock으로 단일 인스턴스를 강제하고, 외부 큐 없이 asyncio로 작업을 돌린다. KB마다 queued compile은 하나이고, 문서 추가·삭제·재컴파일·프롬프트 변경이 모두 거기에 합쳐진다(`JW/application.py:98-113, 387-398`). 플랫폼은 업로드 창이 조용해질 때까지 기다렸다가 KB 단위로 넘긴다.
- **대안**: Celery·Redis 큐와 분산 잠금. OpenKB처럼 문서마다 compile.
- **작성자가 밝힌 이유**: "单实例强制(spec §8)"(`JW/application.py:99`). "The deployed service is single-instance; this lock protects its coroutine interleavings"(`JW/storage/layout.py:25-31`). 합치기: "A compile waiting for its KB's compile lock must remain queued so later parse completions can coalesce into it"(`JW/tasks/executor.py:81-83`). "Let an upload batch finish parsing before starting another expensive compile"(`JW/domain/compile_task.py:42`). 플랫폼: "Parsing success is not a KB-wide batch-complete signal"(`KB/reconciliation_service.py:2616-2618`). KB 바쁨을 실패가 아니라 `stale`로 돌리는 이유: "否则文档会永久停在 failed（巡检只捞 compiling，不会自愈）"(failed로 두면 순찰이 되살리지 않는다)(`KB/jonex_wiki_service.py:572-574`).
- **이력**: 마이그레이션 0001의 "queued 또는 compiling compile은 KB당 하나"를 0006이 "queued 하나"로 바꿨다: "Allow one queued follow-up while one compile is running."(`JW/storage/migrations/versions/0006_compile_followup_indexes.py:1`). 파싱 쪽 이유: "已有 compiling 的输入快照已固定，必须另排一个 follow-up"(이미 compiling인 작업은 입력이 고정됐으므로 후속을 따로 둔다)(`JW/domain/parsing/parse_task.py:202-203`).
- **포기한 것**: 수평 확장. 재시작하면 실행 중이던 parse·compile·outline은 failed("interrupted")가 된다(`JW/tasks/executor.py:318-345`).

### 19. 같은 제목 병합은 읽기 화면에서만 투영한다

- **결정**: 정규화 제목이 같은 페이지를 디렉터리와 상관없이 한 묶음으로 보여 주고, 역링크·references를 합친다. 발행본과 검색은 건드리지 않는다(`JW/domain/reading/page_merge.py:43-149`).
- **대안**: compile에서 같은 대상 판정으로 합치기(결정 7이 보수적으로 막는다).
- **작성자가 밝힌 이유**: "``build_query_corpus`` 产出的 corpus **同时喂检索树与阅读树**，在那一层归并会改变检索产物。本模块只被 ``domain/reading``（展示链路）调用：发布 bundle 一字不动，随时可回滚，且不需要重新编译。"(corpus는 검색과 읽기가 함께 쓰므로 그 층에서 합치면 검색이 바뀐다. 읽기에서만 합치면 발행본을 안 바꾸고 언제든 되돌리며 재컴파일이 필요 없다)(`JW/domain/reading/page_merge.py:18-22`). 근거 실측: 3,835페이지 중 같은 제목 묶음 19개(66페이지), 그중 16개가 디렉터리를 넘었다(7-12행). "实测这 19 簇语义上都是同一实体；同音不同人这类真正的同名歧义在本库未出现"(이 KB에서는 19개 모두 같은 대상이었고 동명이인은 없었다)(14-15행).
- **작성자가 밝힌 원인**: "LLM 在编译期给同一实体生成了多个不同 slug，并且会在「实体目录」（``artists/``）与每个「主题目录」（``lingnan*/``）下各建一份页面"(LLM이 컴파일 때 같은 실체에 서로 다른 slug를 만들고, 실체 디렉터리와 주제 디렉터리마다 페이지를 하나씩 만들었다)(`JW/domain/reading/page_merge.py:3-6`).
- **[추정]**: 실측 KB(revision 95404d13)는 LLM이 경로를 고르는 legacy 모드로 컴파일되었다(사례 1개: `artists/`·`lingnan*/` 디렉터리 경로. layered의 `page_path_for`는 디렉터리 없이 `pages/<ascii>-<sha>.md`를 만든다 `C/organization.py:276-283`). 모르는 것: layered의 출처별 해시 경로(결정 8)가 같은 현상을 내는지. 같은 입력을 layered로 컴파일한 bundle의 같은 제목 묶음 수를 보면 알 수 있다.
- **대가**: compile은 이름만 같으면 합치지 않는데 화면은 제목만 같으면 묶는다. 두 층이 반대 방향이다.

## 축별 분석

축 이름과 뜻은 비교 문서 `llm-wiki-implementations/lab/reports/00-comparison.md`의 #설계 축별 스펙트럼을 따른다.

#### 1. 실행 형태

서버형 엔진이다. 플랫폼 웹 UI·API·MCP 검색·업로드 도구(`mcp_server/tools.py:299-450, 771-884`)와 데이터 소스 동기화가 같은 엔진으로 이어진다(#큰 구조의 입력 채널 행). 비교 문서의 "CLI·SDK 엔진(+MCP)"와 "MCP 서버 + 웹 UI" 사이에 있고, 다중 테넌트 플랫폼에 붙은 점이 다르다.

쓰기 표면은 하나다. 모든 wiki 쓰기가 compile 엔진을 지나고, 사람이 페이지를 고치는 API는 없다(플랫폼 라우트 `api_gateway/routes/knowledge_base.py:1383-1520`에서 쓰기는 목차 draft/adjust와 compile 일시정지·재개뿐). 비교 문서가 짚은 "표면마다 규칙이 갈라지는" 문제는 wiki 쓰기에는 생기지 않는다.

#### 2. 규칙의 위치

"LLM에게 쓰기 수단을 주지 않는다" 쪽에 있지만 끝은 아니다. layered에서 LLM이 하는 일은 넷이다.

| LLM이 하는 일 | 언제 | 출처 |
|---|---|---|
| passage에서 발췌 고르기 | 늘 | `C/understanding.py:933-966` |
| 미정 동일성 판정 | 미정 case가 있을 때 | `C/organization.py:669-721` |
| Error Book 수리 제안 | open Blocking이 있을 때 | `C/error_book.py:925-950` |
| 수리안 semantic review | 수리안이 구조·claim 검증을 통과했을 때 | `C/error_book.py:1018-1036` |

뒤의 둘은 layered도 compile 끝에서 legacy와 같은 정리 단계를 돌기 때문에 생긴다(`C/engine.py:1353-1362`).

수리 호출은 영향받은 페이지 스냅숏을 받아 `PageMutation`(update/delete)을 낸다(`C/error_book.py:931-937`, `M/repair_models.py:37-42`). 받아들여지면 모델이 쓴 스냅숏이 페이지를 통째로 대체한다(`C/error_book.py:983-989`).

받아들이는 조건은 셋이다. 해결한다고 한 id가 open이고, mutation 경로가 그 항목의 `affected_paths` 안이고(`C/error_book.py:726-814`), 구조 검증과 제안 claim 검증을 통과해야 한다. 그 밖의 경우에는 페이지 본문, 경로, 신원, 지지 판정, 링크, index, 등급을 코드가 정한다.

모든 compile 호출은 `thinking={"type": "disabled"}`다(`C/repair/planner.py:77`, `C/understanding.py:960`, `C/error_book.py:525`).

#### 3. 저장 구조

| 하위 선택 | 이 레포의 선택 |
|---|---|
| 디렉터리 분류 | layered 페이지는 `pages/<slug>-<hash>.md` 평평한 목록이다. 디렉터리 index와 `by-id` shard는 렌더가 만든다(`C/rendering.py:47-66`). 원문 페이지는 `wiki/sources/`, 근거 구간은 `source-evidence/`, 표는 `tables/`·`table-views/`다 |
| 메타데이터 | 페이지 frontmatter(`C/rendering.py`)와 bundle JSON(`query/navigation.json`, `claims.jsonl`)에 함께 둔다. 문서·작업·목차·프롬프트 상태는 DB다 |
| 파생 상태 양 | 많다. bundle 한 벌에 색인 3종, navigation, source_index, corpus 해시, manifest가 있고 디렉터리 이름이 내용 해시다(`JW/adapters/artifact_store.py:35-48`). 이해 checkpoint는 bundle 밖에 따로 둔다(`JW/storage/layout.py:60-65`) |

#### 4. Ingest

| 하위 선택 | 이 레포의 선택 |
|---|---|
| 사람 참여 | 없다. 업로드 뒤 자동이다 |
| 증분 판정 | source fingerprint(청크 텍스트·메타·프롬프트·manifest·엔진 id 포함)와 이해 checkpoint key(`C/digest.py:73-124`, `C/understanding.py:399-459`). 배치는 매번 처음부터 다시 돈다 |
| 실패 복구 | passage 단위로 가둔다: "a single noisy rejection must not discard an hours-long compile"(`C/pipeline.py:716-717`). 실패율 5% 관문은 benchmark 정책에서만 막고 production은 degraded로 발행한다(`C/pipeline.py:606-669`). layered는 설명 안 된 실패를 허용하지 않는다(`C/organization.py:250-253`) |
| 감시 | 파일 감시는 없다. 플랫폼 업로드 이벤트와 30초 순찰이 묶어서 넘긴다 |
| 소스당 페이지 수 | 사실의 대표 이름마다 페이지 하나다. 표 사실은 페이지가 되지 않는다 |
| 단위 | passage(블록 여러 개를 목표 4,000 추정 token, 상한 5,000으로 묶은 단위, `SP/chunking.py:35-49`) 하나가 LLM 호출 하나다: "every passage issues its own complete() call so scene → call-site stays one-to-one"(`C/engine.py:672-673`) |

#### 5. 근거 추적 단위

claim ledger에 문자 구간과 결정적 지지 판정을 더한 단계다. 비교 문서의 네 단계보다 한 칸 더 간다.

각 claim은 `SourceSpan`(출처 sha256, passage 텍스트 sha256, `start_char`, `end_char`, 원문 텍스트)을 갖고(`M/compiler_state.py:427-483`), 지지 판정이 문장과 근거의 관계를 좁은 언어 안에서 본다(`M/claim.py`).

비교 문서의 [추정] "9개 구현 중 쓰기 경로에서 인용과 주장의 의미 관계를 코드로 보는 곳은 없다"에 대한 반례다. 다만 보는 범위는 부분 문자열·보호 원자까지이고, 바꿔 말한 문장은 판정하지 않고 NOT_ENOUGH_INFO로 둔다.

query 답의 인용은 여섯 필드 + `page_path`이고, `evidence_id = "ev_" + sha256(정렬된 여섯 필드)`다(`Q/controller/evidence_state.py:23-106`). 문자 구간은 읽기 API의 claims·references에서 드러난다(`JW/domain/reading/bundle_reader.py:430-440, 508-525`).

#### 6. Link

LLM이 이름만 제안하고 코드가 그래프를 계산한다.

| 층 | 무엇 | 출처 |
|---|---|---|
| 제안 | 모델이 `target_mention`·이유·근거를 낸다. 경로는 못 정한다 | `C/relation_increment.py:3-5` |
| 결정 | 이름이 페이지 하나에만 맞을 때 연결, 아니면 pending | `C/relation_increment.py:111-124, 200-203` |
| 타입 | 다섯 관계 중 하나이고, 원문에 정해진 영어 문장 틀이 있을 때만 `supported_relation` | `C/relation_increment.py:138-166` |
| 역방향 | 렌더가 양방향으로 잇는다: "a page-to-page relation is navigable in both directions" | `C/rendering.py:9-15` |
| 읽기 색인 | 다른 페이지 제목·별칭(3자 이상, ASCII는 단어 경계)이 처음 나온 곳을 mention으로 | `C/mention_index.py:94-240` |
| 그래프 투영 | 페이지=노드, frontmatter links=간선, source·raw 페이지는 빼고 OpenKB와 같은 그래프 계약으로 화면에 낸다 | `ADP/jonex_wiki_adapter.py:480-530` |
| 주제 지도 | 목차 주제끼리 공유 태그×2 + 공유 분류로 잇는다. "刻意不做全库页面级力导向图"(전체 페이지 그래프는 일부러 그리지 않는다) | `JW/domain/outline/outline.py:197-237` |

두 층이 같은 이름에 다르게 반응한다. 발행 링크는 이름이 페이지 둘에 맞으면 끊기고, mention 색인은 같은 제목 페이지 전부에 걸린다(`C/mention_index.py:171-185, 219-222`).

#### 7. Lint

별도 lint 명령은 없고 compile 안의 gate다.

| 검사 | 성격 | 출처 |
|---|---|---|
| 구조 gate | 결정적, Blocking이면 발행 차단 | `C/structural.py`, `C/error_book.py:1299-1301` |
| evidence gate | 결정적, SUPPORTED가 아니면 Quarantine | `C/content_validation.py`, `C/publication.py:207-274` |
| 경로 오타 보정 | 결정적 자동 수정(같은 부모, 12자 이상, 편집거리 4 이하) | `C/repair/mutation.py:85-123` |
| LLM semantic review | 숫자·표·같은 페이지 상충일 때만 또는 항상. 기본 off이고 legacy 경로에서만 읽힌다 | `C/repair/blocking.py:56-65`, `C/repair/acceptance.py:639`, `JW/infra/settings.py:129` |
| LLM 수리 라운드 | open Blocking이 있을 때, 검증을 통과해야만 닫음 | `C/error_book.py:1012-1077` |
| 페이지 급감·0페이지 | 셸 관문 | `JW/domain/compile_task.py:147-165` |

#### 8. stale·모순 처리

stale은 출처 버전으로 다룬다. 출처가 바뀌면 그 출처의 사실이 철회되고 다시 이해된다(`C/source_contribution.py:384-508`). 지운 원천은 옮기지 않는다: "a deleted source cannot survive as a stale page snapshot and no page is ever the union of old and new snapshots"(`C/engine.py:1164-1168`).

삭제 문서가 든 발행본은 조회를 거부한다(`JW/domain/source_visibility.py:18-23`). 플랫폼 문서 행에는 `stale` 상태가 있다.
모순은 약하다. 장치는 둘이고, 출처를 넘는 쪽은 기본 모드에서 켤 수 없다.

| 장치 | 무엇을 잡나 | 결과 | 출처 |
|---|---|---|---|
| 지지 판정 REFUTED | claim과 자기 근거 사이의 보호 원자 충돌, 표 행 충돌, 합계 파생 불일치. 모델이 근거를 왜곡한 경우이지 출처 사이 모순이 아니다 | 인용 가능 집합에서 빠진다 | `M/claim.py:23, 590, 636-672` |
| semantic review의 `CROSS_PAGE_CONTRADICTION` | 서로 다른 claim 둘 이상의 상충 | 등급이 Quarantine이라 해당 claim이 인용에서 빠진다 | `C/content_validation.py:55-56, 269-270, 836-837`, `C/error_book.py:100-101` |

semantic review는 legacy 모드에서만 돌고 기본값은 off다(`C/repair/acceptance.py:639`, `JW/infra/settings.py:129`). 그래서 기본 layered 모드에는 설정으로 켤 수 있는 모순 검사가 없다. 모순을 나란히 보여 주는 장치도 없다.

#### 9. 사람 개입

설정 수준에 머문다.

| 개입 지점 | 출처 |
|---|---|
| compile 선호 문구(접미사) | `JW/domain/prompts.py:18-26` |
| 목차 조정. 사람의 지시문으로 LLM이 고친 목차(source=adjust)는 자동 재생성이 덮지 않고 stale 여부만 읽기 쪽이 계산한다. 목차를 직접 편집하는 API는 없다 | `JW/domain/outline/task.py:8-16, 63-70`, `JW/domain/outline/service.py:190-208`, `JW/api/routers/outline.py:22-50` |
| compile 일시정지·재개, 취소 | `JW/tasks/executor.py:118-141, 270-290` |
| 롤백. 엔진을 독립 FastAPI로 띄울 때만 쓸 수 있고 플랫폼 능력 어댑터에는 없다 | `JW/api/routers/compile.py:68-114`, `ADP/jonex_wiki_adapter.py:183-192` |
| 답 피드백(like/dislike + 사유 6종 `inaccurate`·`not_answered`·`incomplete`·`wrong_reference`·`missing_knowledge`·`other` + 코멘트). 저장만 하고 compile·Error Book으로 돌아가지 않는다 | `KB/answer_feedback_service.py:1-8, 24-35` |
| 누락 확인서(사람이 확인한 누락만 원문 덧붙임). 생산 경로 미연결 | `C/omission_repair.py:3-7`, `C/engine.py:382` |

페이지 승인·수정, 동일성 판정 승인은 없다. 미정 동일성은 `compile_organization_identity_unresolved`로 세기만 한다(`C/organization.py:558-562`).

#### 10. 동시성·안전

| 장치 | 출처 |
|---|---|
| 단일 인스턴스 advisory lock(730203) | `JW/application.py:98-113` |
| KB별 `compile_lock`, `version_lock` | `JW/storage/layout.py:21-31` |
| DB 부분 unique index(queued compile 하나, 이름 유일, active 목차 하나) | `JW/storage/models.py:40-42`, `JW/storage/migrations/versions/0006_compile_followup_indexes.py:16-21`, `0001_initial.py:73-76`, `0005_create_wiki_outlines.py:38-44` |
| 원자 발행, 발행 부모 재확인, 손상본 재활용 거부 | `JW/storage/layout.py:119-141`, `C/engine.py:964-993`, `JW/adapters/artifact_store.py:123-128` |
| 조회 버전 고정 | `JW/kernel/ports.py:305-311` |
| stream 스케줄러, 같은 세대 snapshot끼리만 병합 | `C/pipeline.py:725-732, 1229-1231` |
| 읽을 때마다 파일 sha256 대조 | `JW/adapters/bundle_view.py:122-127` |

모델 호출·checkpoint I/O·재시도는 commit lock 밖에서 하고 lock 안에서는 version 확인과 쓰기만 한다(`C/organization.py:30-32, 946-979`).

#### 11. Query·검색

| 하위 선택 | 이 레포의 선택 |
|---|---|
| 검색 방식 | 에이전트 탐색(browse-first). 검색 도구는 jieba + FTS5 BM25다. dense는 RRF(k=60)로 합치지만 기본 off다(`Q/retrieval.py:948-963`, `JW/infra/settings.py:131`). LIKE 대체 검색은 일부러 두지 않았다(`Q/retrieval.py:606-609`) |
| 원문으로 내려가는가 | 내려간다. 원문 구간 레코드를 근거로 쓰고, 표는 `table_*` 도구로 셀까지 읽는다. 계산은 Decimal이다(`Q/traversal_executor.py:806-898`, `Q/numeric_calculate.py`) |
| 답 되저장 | wiki로 되저장하지 않는다. 엔진은 결과를 `query_tasks.result`에 두고(`JW/storage/models.py:67-86`), 플랫폼은 사용자별 검색 이력에 답·references·reasoning을 따로 남긴다(`capabilities/knowledge_base/models/search_history.py:47-67`). 둘 다 compile 입력으로 돌아가지 않는다 |
| 결정적 route | 정규식 표가 SUMMARY·목차·식별자 질문을 가른다: "the first match wins, so the same question always resolves to the same route"(`Q/router.py:16-18`) |

#### 12. index·log 관리

index는 코드가 렌더한다. 전역 `wiki/index.md`, 디렉터리 index, `by-id` shard index가 있다(`C/rendering.py:47-66, 226-262`). 읽기용 목차(outline)는 LLM 초안 + 코드 정리로 따로 만들고 DB에 둔다(`JW/domain/outline/`).

`log.md`는 없다(`grep log.md` 결과 0, 이 보고서 작성 때 확인). log 역할은 넷으로 흩어져 있다: bundle 안 Error Book, DB `tasks.summary`(단계별 시간·reuse_mode, `JW/domain/compile_task.py:214-241`), 게이트웨이 scene별 계량 로그(`JW/infra/metering.py:83-114`), 플랫폼 감사 로그.

#### 13. 포맷 표준

OKF 대응은 없다(`grep -i okf` 결과 0, 이 보고서 작성 때 확인). bundle은 자체 형식 `{"format": "llm-wiki-plus", "schema_version": 3, "engine_id": "llm_wiki", …}`이다(`C/bundle.py:1-30, 51`).

[추정] OKF로 옮기려면 장부를 frontmatter `sources`로 투영하는 변환이 필요하다(사례 1개: 근거가 frontmatter가 아니라 `claims.jsonl`과 장부에 있음).

#### 14. 규모·비용

ingest 1회의 토큰·금액 측정값은 공개되지 않았다. 호출 수 모양은 정해져 있다: 이해는 passage당 1~2회(캐시 hit면 0회, `C/understanding.py:933-1053`), 동일성 판정은 compile당 8회 이하(`C/organization.py:92-94, 625-635`), 수리는 open Blocking이 있을 때만이다(`C/error_book.py:900-919`).
주석에 남은 실측은 아래와 같다.

| 무엇 | 수치 | 출처 |
|---|---|---|
| 큰 bundle | 165.8MiB. 준비 캐시를 128MiB → 768MiB로 늘림 | `Q/prepared_revision.py:175-181` |
| `source_locations` | 258MB. 분리 뒤 응답 15초+ → 1초 미만 | `C/bundle_codec.py:452-456`, `Reference/JonexWiki/scripts/migrate_split_source_index.py:5-7` |
| `navigation.json` | 4.7MB, 파싱 뒤 메모리 24MB, 110ms | `JW/domain/reading/bundle_reader.py:167-193` |
| 페이지·claim | 3,835페이지(KB `bec1ef09…`). claim 2,743개 중 SUPPORTED 792개. 두 수치가 같은 KB에서 나왔는지는 적혀 있지 않다 | `JW/domain/reading/page_merge.py:7-12`, `JW/domain/reading/bundle_reader.py:24-27, 478-481` |
| 상태 복사 | 깊은 복사가 8GiB cgroup을 다 써서 얕은 복사로 바꿈 | `C/error_book.py:1137-1139` |
| thinking | 질의 30회 중 9회가 추론 token으로 출력이 잘림 | `deploy/.env.jonex_wiki.example:100-101` |
| 상한 | KB당 문서 1,000개(`compile_max_documents`) | `JW/api/routers/documents.py:58-59` |

#### 15. frosk1 비판 대응

강도 표기는 비교 문서 #frosk1 비판 7가지 × 구현 대응 표를 따른다.

| 비판 | 강도 | 근거 |
|---|---|---|
| 1 오류 누적 | 부분~강 | 이해와 배치에서는 LLM이 기존 페이지를 읽지 않고(`C/understanding.py:11-12`), 본문은 검증된 발췌 목록이다(결정 5). 예외는 open Blocking이 있을 때 도는 Error Book 수리 라운드다. 이 라운드는 기존 페이지를 보여 주고 고친 페이지를 받으며, 구조·claim 검증을 통과하면 반영한다(`C/error_book.py:931-937, 983-989`). legacy에서도 원문이 바뀌면 모델이 쓴 문장을 버린다(`C/block_replay.py:42-43`) |
| 2 부분 문맥 | 부분 | 이해는 passage 하나만 본다. 이것은 의도다. 출처를 넘는 판단은 정확 일치 후보와 compile당 64 case 판정뿐이다(결정 7). legacy는 후보 페이지 메타 12개까지만 본다(`C/repair/acceptance.py:310-353`) |
| 3 요약 손실 | 강 | 요약하지 않는다. 본문은 원문 발췌이고, keep-and-search가 모든 원문 구간을 검색 대상으로 남긴다(결정 16). 대가는 종합의 부재다 |
| 4 가짜 SoT | 강 | 모든 claim에 문자 구간과 출처 해시가 있다. 조회 답의 인용은 이번 조회에서 실제로 읽은 근거로만 되살아난다(결정 15). 다만 읽기 화면은 지지되지 않은 claim도 references로 보여 준다(`JW/domain/reading/bundle_reader.py:24-27`) |
| 5 환각 병합 | 부분 | compile은 이름만으로 합치지 않고 관계를 별칭으로 바꾸지 않는다(결정 7). 그러나 읽기 화면은 제목만 같으면 묶는다(결정 19). 출처를 넘는 모순 검사는 legacy에서만 돌고 기본 off다(#8 stale·모순 처리) |
| 6 운영 복잡도 | 악화 | 컨테이너 여럿, DB 2곳, bundle·checkpoint·작업 큐·순찰이 있다. JonexWiki만 57.6k줄이다 |
| 7 ingest 비용 | 부분 | checkpoint 캐시·입력 그대로면 재사용·bounded 판정이 비용을 묶는다. 측정값은 없고, 배치와 발행 꼬리는 KB 전체를 매번 다시 돈다 |

#### 16. 성숙도·차용 가능성

라이선스는 수정 Apache 2.0이고 다중 테넌트 운영에 서면 허가가 필요하다(`LICENSE:6`). 프런트엔드 표시 조항과 소유자의 일방 변경 조항도 있다(#한눈에의 차용 조건 행). 테스트·CI·릴리스가 공개본에 없다(#한눈에). 그래서 코드를 통째로 가져오기보다 설계를 참고해 다시 쓰는 편이 맞다.

떼어 보기 좋은 단위는 아래와 같다.

| 단위 | 크기 | 끌고 오는 것 |
|---|---|---|
| 결정적 지지 판정 `M/claim.py` | 681줄 | 영어·중국어 규칙. 한국어 토큰·부정·날짜를 새로 써야 한다 |
| 동일성 규칙 `C/identity.py` | 258줄 | 거의 없다. `NameForm`만 정의하면 된다 |
| 사실 장부 `C/source_contribution.py` | 612줄 | `EvidenceRef`·`SourceSpan` 모델 |
| 근거 사건 축약기 `Q/controller/evidence_state.py` | 407줄 | 조회 루프의 사건 타입 |
| 발행 레이아웃 `JW/storage/layout.py` | 162줄 | asyncio 잠금, 단일 인스턴스 전제 |

레포 안 설명과 코드가 어긋나는 곳이 많다. 문서만 보고 동작을 판단하면 틀린다.

| 항목 | 설명 | 코드 | 출처 |
|---|---|---|---|
| 도구 호출 상한 | docstring "the 15-call limit", `.env.example` "[默认: 32]" | Settings 기본 24가 주입되어 실효 24 | `Q/algorithm.py:17-19`, `JW/infra/settings.py:138` |
| dense 기본 | "Whether hybrid retrieval (BM25 + dense) is enabled (default on)" | 기본 off | `Q/retrieval.py:249-256`, `JW/infra/settings.py:131` |
| semantic review | `.env.example` "[默认: selective]" | 기본 off | `Reference/JonexWiki/.env.example:171-172`, `JW/infra/settings.py:129` |
| thinking | 설정 설명은 조회 탐색·합성 thinking 기본 off | natural 모드면 enabled로 강제 | `JW/infra/settings.py:185-196`, `Q/algorithm.py:1586-1589`(이 보고서 작성 때 다시 확인) |
| 질의 분해 | `.env.example` `QUERY_QUERY_DECOMPOSE=on` | 정의만 있고 호출 0 | `Q/traversal_executor.py:6518-6545` |
| SUPPORTED만 렌더 | `Q/algorithm.py:10-12` docstring | 기본 규칙 keep-and-search-v1은 생성 본문을 그대로 둠 | `Q/retrieval.py:1785-1791` |
| raw-only 파싱 | `SP/raw_manifest.py:1-4` | 파싱 단계에서 패킹 | `JW/domain/parsing/parse_task.py:29-31` |
| 링크 상한 4 | 상수 `MAX_SOURCE_LINK_TARGETS = 4` | 쓰이지 않음. "navigation no longer enforces these cardinality limits" | `C/organization.py:85`, `M/compiler_state.py:225-226` |
| schema 판 회수 | 순찰이 `applied_schema_version=task.wiki_schema_version`을 씀 | 엔진 task에 그 키가 없어 채워지지 않음 | `KB/reconciliation_service.py:2897`, `grep wiki_schema_version Reference/JonexWiki/src` 0건 |
| 원격 bundle 경로 | `from ...storage.directory_bundle import MemoryBundleView` | 그 모듈이 없음 | `C/engine.py` query 메서드 |

부르는 곳 없이 정의만 남은 코드도 있다.

| 코드 | 상태 | 출처 |
|---|---|---|
| `lexical_candidates` | 퍼지 후보 함수, 호출 없음 | `C/identity.py:143-162` |
| `ErrorAttributionBatch` | 원인 귀속 스키마, 호출 없음 | `C/error_book.py:260-271` |
| `candidate_retrieval` 모듈 | 참조만 있고 파일 없음 | `C/repair/acceptance.py:287-292` |
| `GwClient.rerank`, `MeteredGw.rerank` | 호출 없음 | `JW/infra/gateway.py:315`, `JW/infra/metering.py:160` |
| `verify_answer_bindings` | import만 함. 그래서 답 문장과 인용의 결속을 프로그램으로 검증하는 단계는 운영 경로에 없다 | `Q/answer_binding.py:305`, `Q/algorithm.py:321` |

## 엔터프라이즈 llm-wiki에 비추어

사용자 조건은 "작성자마다 같은 대상을 다른 용어로 쓴다"와 "문서가 형식을 갖추지 않을 때가 있다"이다. 목표 원문은 "어느정도 사람이 하더라도 성능을 보장(raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조)"이다.
jonex는 두 목표에 정반대의 답을 준다. raw 연결은 강하고, 새·기존 연결 발견은 보수적 판정 때문에 약하다.

| 조건 | 이 레포가 주는 답 | 빈 곳 |
|---|---|---|
| 다중 작성자 | 업로드 창 묶음 compile과 KB당 queued 하나가 동시 업로드를 한 번의 compile로 모은다(결정 18). 원자 발행과 조회 고정으로 읽는 사람은 일관된 버전을 본다(결정 12). 사실 장부는 한 보고서가 빠져도 다른 보고서가 받치는 사실을 남긴다(결정 10) | 작성자 정보가 엔진에 가지 않는다. 문서 행에 업로더 열이 없고(`capabilities/knowledge_base/models/document.py:56-108`) 엔진 artifact·claim에도 없다. 업로더는 플랫폼 감사 로그와 task center의 `operator_id`(`KB/document_service.py:566-591, 678`), 데이터 소스 문서의 `extra_metadata.external_id`(`KB/data_source_service.py:325, 353`)에만 남는다. 그래서 "누가 이 주장을 했나"를 엔진이 쓸 수 없다. 사람이 페이지를 고치는 경로와 페이지 수정 이력이 없다 |
| 용어 불일치 | 원문 표기(`original_names`)와 원문이 별칭이라고 밝힌 이름(`declared_alias`)을 나눈다(`C/understanding.py:650-667`). 관계는 별칭이 아니다(결정 7). 확신 없으면 따로 두고 센다. 이해 cache key에서 페이지 배치는 빠진다(결정 4) | 이해 cache key에 compile 선호 문구(플랫폼 LLM-Wiki Schema가 투영되는 자리)가 들어간다(`C/understanding.py:373-385`, `ADP/jonex_wiki_adapter.py:18-19`). 그래서 용어 규칙을 프롬프트로 넣으면 바꿀 때마다 이해 LLM을 전부 다시 부른다. 재호출을 피하려면 용어 규칙을 배치 단계 코드 입력으로 따로 두어야 하는데, jonex에는 그 입구가 없다. 배치 후보가 정규화 이름·선언 별칭의 정확 일치뿐이라(`C/organization.py:454-497`) "매출"과 "수익"은 LLM 판정 후보조차 안 된다. JonexWiki에는 사람이 넣는 용어집 입구가 없다(결정 17). 같은 플랫폼의 ontology(lightrag) 길에는 KB 단위 동의어 묶음이 있어 추출 엔티티를 canonical 이름으로 합치지만, jonex_wiki로는 이어지지 않는다(`004_knowledge_base.sql:383-394`, `KB/synonym_normalizer.py:1-12`, `KB/reconciliation_service.py:1510-1525, 1630`). 판정을 저장하지 않는다. 링크가 유일할 때만 걸려서 같은 대상이 출처별로 갈라질수록 링크가 끊긴다(`C/relation_increment.py:123-124`). 검색 질의는 jieba 분절 단어의 OR이고 동의어 확장이 없으며(`Q/retrieval.py:530-551`), dense는 기본 off다(`Q/retrieval.py:249-256`, `JW/infra/settings.py:131`) |
| 형식 없는 문서 | packer에 들어가지 않는 구조 초과 단위만 격리하고 원문을 보관한다(결정 14). 빈 표·반복·깨진 글자 같은 품질 문제는 걸러지지 않고 compile에 들어간다(`SP/inspect.py:1-16`). 산출물 모양 계약이 조용한 품질 저하를 경고로 돌려준다(`JW/application.py:54-74`). passage 단위로 실패를 가둔다. claim이 실패해도 원문 구간이 검색·인용 대상으로 남는다(결정 16) | 표는 compile에서 빠져 표 속 사실이 claim·링크가 되지 않는다(`SP/blocks.py:272`). 한국어가 규칙 밖이다. 후보 점수 토큰 `[a-z0-9]+\|[一-鿿]`와 지지 판정 토큰이 한글을 버리고(`C/repair/blocking.py:33`, `M/claim.py:36-39`), 부정어·날짜는 영어·중국어뿐이고, mention은 3자 이상이라 2자 한글 약칭이 안 걸린다(`C/mention_index.py:47`) |
| 권한 | tenant·kb를 경로·캐시 key·bundle 소유 검사에 넣는다(`JW/storage/layout.py:60-65`, `C/understanding.py:426-427`). 플랫폼은 KB 단위 RBAC(`kb_manager`/`member`)를 둔다(`KB/kb_permission_service.py:24-38`). 삭제 문서가 든 발행본 조회를 거부한다. 외부로 나가는 trace는 허용 목록이다. 신원은 IdP 사용자 동기화로 들어오고, 동기화는 external_id로만 맞추며 동명이인을 합치지 않는다("同名不同人 → 记失败明细，拒绝合并", `capabilities/platform/services/identity_integration_sync.py:14-21`) | 문서 단위 권한이 없다. 권한 표는 공간·KB 둘뿐이다(`004_knowledge_base.sql:31-66`). KB 아래 한 단계 폴더가 있고(`004_knowledge_base.sql:454-476`) MCP 쓰기 Key는 폴더 단위 grant를 정의하지만(`capabilities/platform/dtos/mcp_key_dto.py:37`), MCP 업로드는 그 모드를 거부하고(`mcp_server/tools.py:349-355`) 엔진에는 폴더가 가지 않는다. 엔진의 `document_scope` 필터는 애플리케이션이 넘기지 않는다(`JW/domain/query/query_task.py:149`). KB를 쪼개면 KB 사이 링크·병합이 없고 답만 LLM이 합친다(`KB/search_service.py:7918-8095`). `tenant_id`·`kb_id`를 경로에 쓰기 전 검사가 없다(`JW/storage/layout.py:9` 정규식 미사용) |
| 규모 | checkpoint 캐시, passage 단위 호출, 동일성 판정 상한, navigation 분리, 준비 캐시가 있다(#축별 분석의 14번) | 단일 인스턴스와 프로세스 안 큐(결정 18), KB당 문서 1,000개, 준비 캐시 1개다. 배치는 매번 KB 전체를 다시 돈다. [추정] 문서가 많은 KB에서는 미정 case가 64개 상한을 넘어 대부분 독립 페이지로 남는다(사례 1개: 상한 상수 `C/organization.py:92-94`, 실측 없음) |
| raw 연결 | 모든 페이지 줄이 `SourceSpan`으로 원문 문자 구간까지 돌아간다. 장부의 `record_id`가 출처 버전과 위치를 품는다. keep-and-search가 원문 구간 전부를 근거로 남긴다 | 표 사실은 원문 페이지로만 남는다 |
| 새·기존 연결 발견 | 같은 출처는 자기 페이지를 이어 쓰고, 선언 별칭 + 같은 context면 기존 페이지에 붙는다. 미정은 제한된 LLM이 판정한다 | 출처를 넘는 연결 후보 생성이 정확 일치뿐이다. 퍼지·임베딩 후보 함수는 막혀 있다(`C/identity.py:143-162`). [추정] 같은 이름이 출처별로 갈라진 뒤 링크가 pending이 되어, 새 보고서와 옛 보고서 사이 연결이 오히려 사라질 수 있다(사례 2개: 출처별 경로 `C/organization.py:279-283`, 유일 일치 링크 `C/relation_increment.py:123-124`) |

### 가져올 것

| 아이디어 | 맞는 이유 | 코드 위치 |
|---|---|---|
| 사실 장부를 진실로 두고 페이지는 투영으로 만들기. 장부 신원에 페이지 경로를 넣지 않기 | 보고서가 바뀌거나 지워질 때 그 출처의 사실만 철회되고, 여러 작성자가 같은 사실을 말하면 남는다 | `C/source_contribution.py:3-6, 70-89, 384-508` |
| 이해 캐시 key에서 페이지 배치를 빼기 | 용어집·병합 규칙을 이해 프롬프트 밖(배치 단계 입력)에 두면, 자주 고쳐도 원문을 LLM에 다시 묻지 않는다. jonex는 사용자 프롬프트를 key에 넣으므로(`C/understanding.py:373-385`) 이 분리를 직접 해야 한다 | `C/understanding.py:115-117, 399-459` |
| 동일성 3값(same/different/undetermined)과 "미정은 따로 두고 센다" | 미정 목록을 사람 승인 대기열로 바로 쓴다. 승인 결과는 용어집으로 저장해야 한다(jonex는 저장하지 않는다) | `C/identity.py:99-132`, `C/organization.py:558-562` |
| 관계는 별칭이 아니다 | 구·신 제품명, 모회사·자회사를 한 페이지로 잘못 합치지 않는다 | `C/identity.py:17-18, 111-115` |
| 원문 표기와 선언 별칭을 따로 기록 | 작성자별 표기 차이를 지우지 않고 용어 정규화의 원료로 남긴다 | `C/understanding.py:650-667` |
| evidence gate + 문자 구간 + 보호 원자 | 수치·날짜·부정이 섞여 왜곡되는 것을 코드로 막고, 검토자가 원문 위치로 바로 간다. 한국어 규칙은 새로 써야 한다 | `C/content_validation.py:446-487`, `M/claim.py:127-222` |
| 모델이 낸 id를 지우고, 링크는 이름만 제안하게 하기 | 엉뚱한 출처에 근거가 묶이는 사고를 막는다 | `C/understanding.py:545-575`, `C/relation_increment.py:3-5` |
| 체검 + 원문 보관 + 산출물 모양 계약 | 형식 없는 문서 하나가 전체 compile을 죽이지 않고, 뺀 것이 남는다 | `SP/inspect.py:3-15`, `SP/source_archive.py`, `JW/application.py:54-74, 309-367` |
| 불변 bundle + symlink 발행 + 조회 고정 + 발행 관문 | 여러 사람이 동시에 넣고 빼도 일관된 버전을 보고, 잘못된 compile은 symlink 하나로 되돌린다. jonex는 이 롤백을 독립 FastAPI에만 두고 플랫폼에는 내놓지 않았으니, 가져온다면 운영 화면까지 이어야 한다 | `JW/storage/layout.py:119-162`, `JW/domain/compile_task.py:147-186` |
| Error Book 등급(막을 것과 기록할 것을 나눔) | 사람이 볼 문제와 발행을 막을 문제가 나뉜다 | `C/error_book.py:71-138` |
| 조회 근거를 사건 축약기로 관리하고 handle만 모델에 주기 | 답의 모든 인용이 이번 조회에서 실제로 읽은 원문 레코드로 되돌아간다 | `Q/controller/evidence_state.py`, `Q/synthesis_orchestration.py:719-757, 875-942` |
| 사람이 개입한 결과를 자동 재생성이 덮지 않게 하기 | "어느정도 사람이 하더라도"의 사람 손을 지킨다. jonex에서 보호받는 것은 사람의 지시문으로 LLM이 고친 목차이고, 사람이 직접 편집하는 경로는 없다. 직접 편집에도 같은 보호를 걸어야 한다 | `JW/domain/outline/task.py:8-16, 63-70` |
| 표를 claim으로 만들지 않고 격자 저장 + 병합 셀 근거 머리글 해석 + 제한된 `table_compute`(Decimal, 원 셀 동반)로 다루기 | 사내 수치 보고서의 숫자를 LLM 요약으로 흐리지 않고, 답의 숫자마다 원 셀이 붙는다 | `SP/header_interpretation.py:1-40`, `Q/table_query.py:1-6` |
| 사람이 관리하는 동의어 묶음 + 한 낱말은 한 묶음에만 | 작성자별 용어를 사람이 정한 canonical 이름으로 모은다. jonex에서는 그래프 길에만 쓰인다. 앞선 schema-glossary 보고서(`llm-wiki-implementations/lab/reports/schema-glossary/yuezhiai-jonex.md`)와 함께 본다 | `KB/ontology_synonym_service.py:1-6`, `KB/synonym_normalizer.py:18-30` |
| 판을 매긴 설정 + 문서별 target/applied 판 + 펜싱(플랫폼 LLM-Wiki Schema) | 용어집을 고칠 때마다 어느 문서가 옛 판으로 compile됐는지 추적한다. OpenKB 갈래에서만 끝까지 이어지고, jonex_wiki에서는 applied 판이 채워지지 않는다(#16 성숙도·차용 가능성의 schema 판 회수 행) | `KB/llm_wiki_schema_service.py:262-424`, `jonex_core/capability/atomic/openkb/openkb_adapter.py:419-442` |
| 답 피드백의 사유(`wrong_reference`, `missing_knowledge`)를 Error Book 항목으로 잇기 | 사람이 남기는 거의 유일한 품질 신호를 compile 쪽으로 되돌린다. jonex는 피드백을 저장만 한다 | `KB/answer_feedback_service.py:24-35` |
| 업로드 창 묶음 compile | 한꺼번에 올라온 보고서를 함께 보고 판단한다 | `KB/reconciliation_service.py:3056-3147` |
| 문구가 아니라 기계 코드로 오류 분기 | 현지화·문구 수정에 자가 치유가 조용히 죽지 않는다 | `KB/jonex_wiki_service.py:37-41` |

### 피할 것

| 피할 것 | 이유 | 위치 |
|---|---|---|
| 이름이 페이지 하나에만 맞을 때만 링크 걸기 | 같은 대상이 출처별로 갈라지면 그 이름으로 가는 링크가 사라진다. 모두에 걸고 모호함을 표시하는 쪽이 연결 발견에 맞다 | `C/relation_increment.py:123-124, 200-203` |
| 정확 일치만으로 동일성 후보 만들기 | 용어가 다르면 판정 후보조차 되지 않는다. 퍼지·임베딩 후보를 "후보 제안"으로만 살려야 한다 | `C/organization.py:454-497`, `C/identity.py:143-162` |
| 동일성 판정을 저장하지 않기 | 비용이 반복되고 같은 입력에서 배치가 흔들릴 수 있다 | `C/organization.py:441, 656` |
| 읽기 화면에서 제목만으로 병합 | 사내 보고서에는 같은 이름의 다른 프로젝트·사람이 흔하다. compile 판정과 반대 방향이다 | `JW/domain/reading/page_merge.py:43-52` |
| 표 사실이 페이지·링크 그래프에 오르지 않게 두기 | 사내 보고서의 수치는 표에 많다. 표 수치는 표 도구로 답할 수 있지만(#가져올 것의 표 행), 표 속 대상이 다른 보고서의 페이지와 이어지지 않는다 | `SP/blocks.py:272`, `C/pipeline.py:424` |
| 영어·중국어 전용 규칙과 도메인 하드코딩 | 한글 토큰이 버려지고, 검색 코어에 식당 메뉴("早餐/午餐/晚餐/菜单") 가중치가 박혀 있다 | `C/repair/blocking.py:33`, `M/claim.py:36-48, 90-98`, `Q/retrieval.py:934-936, 1001-1003` |
| 그래프 KB와 wiki KB를 배타로 두기 | 한 문서를 두 엔진에 넣을 수 없어 그래프 엔티티와 wiki 페이지를 잇는 저장된 다리가 없다. 하나의 사실 장부를 두고 둘을 투영하는 편이 낫다 | `KB/document_service.py:681-682`, `KB/knowledge_info_service.py:439-452` |
| 단일 인스턴스 + 프로세스 안 큐 + KB당 문서 1,000개 | 전사 규모에서 먼저 막힌다 | `JW/application.py:98-113`, `JW/api/routers/documents.py:58-59` |
| 같은 설정의 기본값과 설명을 여러 곳에 두기 | 작성자 스스로 "两份默认值:改了一处、另一处静默生效,谁也看不见"(기본값이 두 곳이면 한쪽만 바뀌어 아무도 모른다)라고 경고했지만(`C/pipeline.py:86-90`) 레포에는 설정 기본값과 설명이 어긋난 곳이 5곳 남았고, 설명과 동작이 어긋난 곳까지 세면 10곳이다(#축별 분석의 16번) | `JW/infra/settings.py`, `.env.example` |

## 확인하지 못한 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| JonexWiki를 따로 만든 공식 이유 | 비공개 `docs/jonex_wiki/*.md`, `docs/llmwiki-schema-settings-execution-plan.md`. 또는 yuezhiai/jonex 이슈로 묻기 |
| 주석이 가리키는 내부 계획서(S5~S7, AC-00x, §14, Wave 3~6)의 원래 근거와 측정 수치 | 공개본에 없다(`CHANGELOG.md:20-22`). 비공개 원본 저장소나 저자 문의 |
| layered가 legacy보다 품질·비용이 나은지 | 주석에 "verified by A/B (F1 must not regress)"(`C/pipeline.py:735`)만 있고 수치가 없다. 엔진 telemetry 키(`C/engine.py:1246-1268`)를 실제 배포에서 모으면 잴 수 있다 |
| 실제 KB에서 동일성 미정 case가 몇 개이고 몇 개가 판정되는지 | compile 로그의 `layered_organization_identity_judgments`, `compile_organization_identity_unresolved`, `..._judgment_limited` 계수 |
| 같은 KB를 두 번 compile할 때 페이지 배치가 같은지 | 같은 입력으로 두 번 돌려 `state/compiler.json`의 pages 키 비교. 이번 조사는 실행하지 않았다 |
| `source_ids`가 legacy에서는 passage id, layered에서는 source id인 것이 의도인지 | 저자 문의. 렌더 `## Sources`에 그대로 찍힌다(`C/rendering.py:456`) |
| semantic review와 조회 thinking의 의도된 기본값 | 게이트웨이 요청 로그(`gw_call`의 thinking 필드, reasoning_tokens) |
| dense 검색을 운영 기본 off로 둔 이유 | `QUERY_DENSE` 변경 이력이나 내부 평가(주석의 Wave 5 실험) |
| raw-only 파싱에서 파싱 단계 패킹으로 되돌린 이유 | 내부 "方案 §12 / §8" 문서 |
| 수리 간격 50(함수 기본값 10, 논문은 재검증 10 batch·수리 간격 미기재), 실질 passage 40자, 후보 가중치 8/6/4/3, 관계 종류 5개, 업로드 창 5초의 근거 | 내부 계획서. 코드에 이유가 없다 |
| 논문 저자(WeChat, Tencent)와 Jonex 팀의 관계, k=5의 근거, 원 코드 `engines/llm_wiki_plus/`의 출처 | 논문 PDF 본문(이번에 추출 실패), 저자 GitHub, 후속 버전의 코드 링크 |
| 한 회사가 부서별 workspace를 여럿 운영하는 것이 라이선스 1a에 드는지 | 라이선스 소유자 문의 |
| 재시작 뒤 queued 조회 행이 쌓이는지 | 운영 DB `query_tasks` status 분포. `recover_queries`가 queued를 건드리지 않고 TTL 정리도 고르지 않는다(`JW/tasks/executor.py:338`, `JW/storage/repos.py:107-123`) |
| 표 도구(`table_reader`, `table_query`, `read_views`)의 세부 동작 | 검증 단계에서 모듈 머리말과 줄 수까지 읽었다(#ingest 표 문단). 함수 본문은 읽지 않았다. 사내 엑셀 보고서가 많다면 따로 읽어야 한다 |
| `delete_kb`가 실행 중 compile·query를 취소하지 않고 디렉터리를 지울 때 compile이 디렉터리를 다시 만드는지 | 실행해 보거나 `JW/application.py:687-703`와 compile runner의 디렉터리 생성 경로를 끝까지 따라가기 |

## 검증 기록

검증자 셋이 같은 commit `5571db5`를 기준으로 보고서를 대조했다. 지적 53건을 하나씩 레포에서 다시 열어 확인했고, 52건을 반영하고 1건은 고칠 것이 없어 그대로 두었다. 지적 4쌍(다중 작성자, 용어집, 목차 보호, 모순 처리)은 두 관점이 같은 곳을 짚어서 한 번에 고쳤다.

| 관점 | 대조한 주장 수 | 지적 | 반영 |
|---|---|---|---|
| 코드 주장(줄 번호·동작) | 74 | 24 | 24 |
| 이유 주장(인용 원문·[추정] 근거·이력) | 98 | 14 | 14 |
| 빠진 것(하위 체계·엔터프라이즈 조건·라이선스) | 34 | 15 | 14 |

### 크게 바뀐 판단

| 전에 쓴 것 | 고친 것 | 근거 |
|---|---|---|
| layered에서 LLM이 하는 일은 셋이고 페이지 본문은 코드가 정한다 | 넷이다. open Blocking이 있을 때 Error Book 수리가 기존 페이지를 보고 고친 스냅숏을 내며, 받아들여지면 본문을 대체한다. frosk1 오류 누적 강도를 '강'에서 '부분~강'으로 낮췄다 | `C/engine.py:1353-1362`, `C/error_book.py:931-937, 983-989` |
| 이해 캐시가 배치와 무관해서 용어 규칙을 바꿔도 LLM을 다시 부르지 않는다 | compile 선호 문구(플랫폼 Schema가 투영되는 자리)가 cache key에 들어가서, 용어 규칙을 프롬프트로 넣으면 이해를 전부 다시 한다 | `C/understanding.py:373-385`, `ADP/jonex_wiki_adapter.py:18-19, 707-721` |
| 원문이 바뀌어도 바뀌지 않은 passage는 checkpoint로 건너뛴다 | 재파싱한 문서는 세대·위치가 key에 들어가서 passage 전부를 다시 이해한다. 건너뛰는 것은 다른 문서의 passage뿐이다 | `C/understanding.py:428-434, 801-806`, `JW/application.py:289` |
| 재시도 최대 2회 | 첫 시도 + 재시도 1회, 합쳐 최대 2회 | `C/understanding.py:93, 1010-1053` |
| 배타의 이유는 적혀 있지 않다([추정]) | 작성자가 "KB 级互斥，避免与 OpenKB 双写"라고 적었다. [추정]은 이중 쓰기를 피한 이유로 좁혔다 | `Reference/Rag-anything/raganything/service/task_manager.py:2414, 2959` |
| 같은 제목 병합은 '출처마다 페이지' 원칙 때문이다([추정]) | 작성자가 원인을 LLM의 slug·디렉터리 중복으로 적었다. 실측 KB가 legacy로 컴파일되었다는 새 [추정]을 달았다 | `JW/domain/reading/page_merge.py:3-6` |
| "nothing is merged automatically"를 일반 원칙으로 인용 | 이 구절의 주어는 퍼지 이름 후보임을 밝히고, 이름·별칭 + 같은 context는 SAME으로 판정된다고 덧붙였다 | `C/identity.py:12-15, 122-126` |
| wiki 길이 보수적인 이유는 되돌림 비용이다([추정]) | 사례가 이 이유를 받치지 않아서 '모르는 것'으로 바꿨다 | `grep` 결과 0, `C/identity.py:11-12` |
| 프롬프트만으로는 근거 없이 답했다([추정]) | 작성자 관측 "observed: 13 searches / 1 read"로 바꿨다 | `Q/traversal_executor.py:225-232` |
| 롤백은 운영 수단이다 | 독립 FastAPI에만 있고 플랫폼 능력 어댑터에는 없다 | `deploy/docker/jonex-wiki.Dockerfile`, `ADP/jonex_wiki_adapter.py:183-192` |
| 사람이 고친 목차를 보호한다 | 보호받는 것은 사람의 지시문으로 LLM이 고친 목차다. 직접 편집 경로는 없다 | `JW/domain/outline/service.py:190-208`, `JW/api/routers/outline.py:22-50` |
| 모순 검사는 semantic review(기본 off)뿐이다 | 그 review는 legacy에서만 읽혀서 기본 layered에는 켤 수단이 없다. REFUTED가 잡는 것과 `CROSS_PAGE_CONTRADICTION` → Quarantine 결과를 표로 더했다 | `C/repair/acceptance.py:639`, `M/claim.py:590, 636-672`, `C/error_book.py:100-101` |

### 새로 채운 하위 체계

빠졌다고 지적된 장치를 레포에서 직접 읽고 해당 절에 넣었다.

| 장치 | 넣은 자리 | 출처 |
|---|---|---|
| 입력 채널(MCP 업로드, 데이터 소스 api·storage·api_push)과 external_id 중복 거름 | #큰 구조 구성 요소 표, #1 실행 형태 | `mcp_server/tools.py:299-450`, `KB/data_source_service.py:40, 359-372` |
| 표 하위 체계(머리글 해석, 제한 실행, Decimal) | #ingest 표 문단, #가져올 것, #피할 것의 표 행을 좁힘 | `SP/header_interpretation.py:1-40`, `Q/table_query.py:1-6` |
| 플랫폼 동의어 묶음(그래프 길 전용) | #엔터프라이즈 용어 불일치 행, #가져올 것 | `004_knowledge_base.sql:383-394`, `KB/synonym_normalizer.py:1-12` |
| 답 피드백 | #9 사람 개입, #가져올 것 | `KB/answer_feedback_service.py:24-35` |
| 플랫폼 검색 이력의 답 저장 | #11 Query·검색 | `capabilities/knowledge_base/models/search_history.py:47-67` |
| 업로더가 남는 자리(감사 로그, operator_id, external_id) | #엔터프라이즈 다중 작성자 행 | `KB/document_service.py:566-591, 678` |
| KB 폴더와 MCP 폴더 grant, IdP 동기화의 동명이인 거부 | #엔터프라이즈 권한 행 | `004_knowledge_base.sql:454-476`, `capabilities/platform/services/identity_integration_sync.py:14-21` |
| 그래프 투영과 주제 지도 | #6 Link 표 | `ADP/jonex_wiki_adapter.py:480-530`, `JW/domain/outline/outline.py:197-237` |
| 라이선스 1b(프런트엔드 표시)·2a(일방 변경) | #한눈에 차용 조건 행 | `LICENSE:10-12, 16` |
| 운영 경로에 없는 `verify_answer_bindings` | #16 정의만 남은 코드 목록 | `Q/answer_binding.py:305`, `Q/algorithm.py:321` |

### 줄 번호·수치 정정

줄 번호가 파일 끝을 넘거나 다른 줄을 가리키던 곳을 고쳤다. `C/repair/blocking.py`(232줄)의 258-265·368-414·259·279-299행은 각각 124·142-232·33행과 `C/repair/acceptance.py:287-292`로, `C/repair/mutation.py`(123줄)의 154-226행은 85-123행으로 옮겼다.

나머지 정정은 아래와 같다. `GwClient.rerank`는 315행으로, `Q/retrieval.py:923-925`(BM25 SQL 줄)는 dense 기본값 249-256행과 질의 구성 530-551행으로, 792 인용은 `bundle_reader.py:478-480`으로, 258MB 인용은 `bundle_codec.py:446-450`으로 고쳤다. unique index 출처는 지금 상태를 만든 마이그레이션 0006·0001·0005로 나눴다.

kernel ports는 6종에서 7종(Clock 포함)으로 고쳤다. "Extracted verbatim" 모듈 수는 9개에서 13개로 고쳤다. "Paper-required" 인용은 파일마다 다른 원문 그대로 옮겼다. 논문 값은 WebFetch로 다시 확인했다. 재검증 주기 10 batch는 논문에 있고, LLM 수리 간격은 "every NN articles"로 값이 없다.

passage는 블록 하나가 아니라 블록 여러 개를 묶은 단위로 고쳤다. 질의 incomplete 조건, 발행 직전 재시작의 후보 재사용, 엔진 재확인이 이전 발행본이 있을 때만 도는 점, 체검이 구조 초과만 격리한다는 점을 본문에 맞췄다. 결정 14의 제목도 이에 맞춰 바꿨다.

'운영 사고' 모양의 대표 결정을 12·13·14·18에서 2·6·12·13·14·19로 바꿨다. 결정 18 인용에는 사고·실측 원문이 없고, 2·6·19에는 있다. 설정 어긋남은 '10곳'을 '기본값 5곳, 설명과 동작까지 10곳'으로 나눴다. `put_bundle` 인용에는 빠졌던 한정어 "for older test stores"를 되살렸다.

### 검증자와 다르게 고친 것

- 라이선스 줄 번호: 파일이 빈 줄로 시작해서(`od -c LICENSE`) 보고서의 `LICENSE:1`·`:5`·7행은 각각 2·6·8행이다. 검증자가 든 1b `11-13`·2a `17`도 한 줄씩 밀려서 10-12·16으로 적었다.
- 표 하위 체계 크기: 검증자가 든 파일 11개를 다시 세니 9,174줄이라서(`wc -l`) '약 9,200줄'로 적었다. 검증자의 9,472줄은 재현되지 않았다.
- Quarantine 효과: 검증자는 keep-and-search에서 "해당 claim만" 빠진다고 했다. 그런데 `quarantine_scope`는 항목이 가리키는 source·passage를 인용한 claim도 빼므로(`C/publication.py:33-50`) 그렇게 적었다.

### 기각한 것

- #13 포맷 표준을 '근거 1개'라고 밝히라는 지적은 반영하지 않았다. 그 절의 [추정]에 이미 "사례 1개"가 붙어 있어서 근거가 얇다는 표시가 되어 있다. OKF 필드와 frontmatter를 나란히 놓는 보강은 OKF 명세를 따로 읽어야 해서 이번 범위 밖으로 두었다.

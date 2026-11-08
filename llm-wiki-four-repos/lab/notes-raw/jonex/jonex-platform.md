# jonex-platform 갈래 노트 — Jonex 플랫폼은 wiki 엔진을 어떻게 품는가

- 레포: yuezhiai/jonex, HEAD `5571db5` (2026-10-10), 로컬 `lab/repos/yuezhiai_jonex`. 아래 경로는 모두 레포 루트 기준이다.
- 이 노트는 다음 단계 보고서 작성자의 유일한 입력이다. 사실 문장에는 `path:line`·commit·이슈 번호를 붙였다. 작성자가 밝힌 이유는 원문을 큰따옴표로 인용했다. 추론한 이유에는 `[추정]`과 근거 사례 개수를 붙였다.
- 레포 코드는 실행하지 않았다. 읽기 전용 git 명령, grep/sed/cat, `gh api`만 썼다. 업스트림 OpenKB 비교를 위해 `gh api repos/VectifyAI/OpenKB/tarball/<ref>`로 v0.4.5, v0.5.0-rc1, main(ff54396) 세 벌을 스크래치패드에 받아 `diff -r`만 돌렸다.

## 0. 범위와 읽은 정도

| 영역 | 정도 | 비고 |
|---|---|---|
| `capabilities/knowledge_base/services/kb_type_service.py`, `ingest_backend.py`, `openkb_service.py`, `jonex_wiki_service.py`, `llm_wiki_schema_service.py`, `llm_wiki_artifacts.py`, `wiki_outline_service.py` | 끝까지 읽음 | |
| `capabilities/knowledge_base/models/llm_wiki_schema.py`, `dtos/llm_wiki_schema.py` | 끝까지 읽음 | |
| `jonex_core/capability/atomic/openkb/{client,openkb_adapter}.py` | 끝까지 읽음 | |
| `jonex_core/capability/atomic/jonex_wiki/{client,jonex_wiki_adapter}.py` | adapter 끝까지, client는 앞 120줄 + 시그니처 | |
| `document_service.py` | wiki 분기(업로드 427-785, chunks 1269-1381, reparse 1657-1810, delete 2393-2445, 목록 술어 95-129)만 읽음 | 나머지 훑음 |
| `reconciliation_service.py` | wiki 관련(55-80, 1853-1858, 2489-3190) 읽음 | ontology 부분은 앞선 보고서 영역, 훑지 않음 |
| `task_runner_service.py` | 머리 문서(1-200), 분기(681-892) 읽음 | 나머지 훑음 |
| `task_watch_service.py` | wiki 분기 주석(600-720)만 훑음 | task center 갈래와 경계 |
| `search_service.py` (8592줄) | `search` 1890-1912, `search_llmwiki` 7613-7830, `_build_openkb_references` 7153-7260, `_build_jonex_wiki_references` 7408-7450, `search_jonex_wiki` 7877-7900, `search_mix` 8148-8300 읽음 | ontology 검색은 훑지 않음 |
| `jonex_core/common/ontology_llm.py` | `fuse_rag_answers` 673-768, `anchor_answer_to_references` 770-840 읽음 | |
| `capability.py` (KB 능력) | 권한 집합 300-410, `execute` 1436-1600 읽음 | |
| `jonex_core/security/permission.py`, `kb_permission_service.py`, `space_permission_service.py` 앞 120줄 | 읽음 | |
| `jonex_core/llm_gateway/{auth,context,metering,router(앞 80줄),upstream(앞 60줄)}.py` | 읽음 | |
| `jonex_core/sidecar/main.py`, `hooks.py` | 앞부분과 AuditForwarder만 훑음 | |
| `jonex_core/task_runtime/*` | 훑지 않음 | task center 갈래 |
| `mcp_server/tools.py` | wiki 검색 도구(771-926)만 읽음 | |
| `api_gateway/routes/knowledge_base.py` | wiki 라우트(785-805, 1383-1520, 1558-1670) 읽음 | |
| `deploy/` | compose openkb·jonex-wiki 블록(1126-1200), `.env.example` 940-975, `postgres/migrations/004_knowledge_base.sql` 해당 표, `update/001,032,033,044,045` 머리말 읽음 | |
| `Reference/OpenKB` | `JONEX_CHANGES.md` 끝까지, `schema.py`·`agent/query.py` 앞부분, `agent/compiler.py` 1-130·727-757 읽음, 업스트림과 diff | 컴파일러 내부는 훑음 |
| `Reference/JonexWiki` | `application.py` 머리, `storage/layout.py` 47-81, `storage/repos.py` grep, `domain/prompts.py` 1-75만 훑음 | 엔진 내부는 jonex-wiki 엔진 갈래와 경계 |
| `frontends/core-business` wiki 화면 | 파일 목록과 `WikiReaderShell.tsx`·`JonexWikiPromptTab.tsx` 머리 주석만 훑음 | |
| LightRAG/Rag-anything/ontology 추출 | 다루지 않음 | 앞선 schema-glossary 보고서와 다른 갈래 영역 |

경계: JonexWiki 엔진의 이해·배치·같은 대상 판정(`identity.py`, `organization.py` 등)과 OpenKB 컴파일러 내부 단계는 다른 갈래가 깊게 읽는다. 이 노트는 플랫폼이 두 엔진을 부르는 접점까지만 다룬다.

## 1. 구조

### 1.1 컨테이너와 호출 경로

`jonex-platform-architecture.md`는 wiki 엔진을 한 번도 언급하지 않는다(`grep -ci "wiki\|openkb"` 결과 0). 이 문서의 서비스 표(43-118행)는 wiki 엔진이 들어오기 전 모양이다. 실제 wiki 경로는 compose와 코드에서 읽었다.

```text
브라우저 → frontend-gateway(nginx) → api_gateway(8000) → sidecar(8001) /invoke
   → knowledge-base-service(8003)   capability_id = business.knowledge_base.v1
        ├─ KnowledgeCompilerService (openkb_service.py)
        │     └─ RemoteOpenKBClient → sidecar /invoke (capability_id atomic.openkb.v1)
        │            → openkb 컨테이너(7566): OpenkbCapability(openkb_adapter.py)
        │                 └─ 프로세스 안에서 vendored `openkb` 패키지 import (compile_short_doc, run_query …)
        ├─ JonexWikiService (jonex_wiki_service.py)
        │     └─ RemoteJonexWikiClient → sidecar /invoke (atomic.jonex_wiki.v1)
        │            → jonex-wiki 컨테이너(8007): JonexWikiCapability(jonex_wiki_adapter.py)
        │                 └─ 프로세스 안에서 `jonex_wiki.application.WikiApplication` 호출
        ├─ atomic-rag(8004) 파싱 (parse_only 모드로 content.md 또는 content_list.json을 공유 볼륨에 씀)
        └─ task-center-service(8007, 다른 컨테이너) 편성 → 다시 knowledge-base 운행자 handler 호출
모든 LLM 호출 → llm-gateway(8787) → 상위 OpenAI 호환 엔드포인트
```

- openkb 컨테이너는 `deploy/docker/openkb-source.Dockerfile`로 `Reference/OpenKB/openkb/`와 `jonex_core/`를 함께 복사하고 `CAPABILITY_NAME=openkb`로 `deploy/start_capability.py`를 띄운다(Dockerfile 끝 25행, `deploy/docker-compose.yml:1126-1155`).
- jonex-wiki 컨테이너는 "단일 컨테이너(B1)：引擎 + Jonex Atomic Capability 同进程 pydantic v2"(엔진과 능력이 같은 프로세스)이다 — `deploy/docker-compose.yml:1157-1162`, `jonex_core/capability/atomic/jonex_wiki/jonex_wiki_adapter.py:1, 196-202`.
- 두 엔진 컨테이너는 공유 볼륨 `jonex-rag-inputs`를 마운트해 파싱 산출물을 읽는다(openkb는 `/app/data/inputs`, jonex-wiki는 `/app/inputs`) — `deploy/docker-compose.yml:1142-1143, 1180-1181`. 그래서 플랫폼은 절대경로 대신 "相对 inputs 卷根" 경로를 넘긴다(`reconciliation_service.py:2621-2635`의 `_relativize_input_path`).
- openkb 저장소 볼륨은 `jonex-openkb-storage:/app/data/kb_storage`, jonex-wiki는 `jonex-wiki-storage:/data/jonex-wiki`이다(compose 1142, 1180).

### 1.2 모듈 지도 (누가 누구를 부르나)

| 호출하는 쪽 | 부르는 쪽 | 무엇을 |
|---|---|---|
| `knowledge_info_service.create` | `resolve_creatable_kb_type`, `KnowledgeCompilerService.init_kb`(openkb만), `LlmWikiSchemaService.get_schema(auto_create=True)` | KB 생성 + 기본 schema + apply (`knowledge_info_service.py:63, 104-127`) |
| `document_service.upload_document` | `kb_type_service.get_kb_type`, `ingest_backend.resolve_backend`, `task_runner_service._upload_via_task_center` | 업로드 → 편성 제출 (`document_service.py:602-679`) |
| task center → `TaskRunnerService._on_parse/_on_compile` | `_submit_insert`(parse_only) / `_submit_wiki_compile` / `_submit_jonex_wiki_compile` | 단계별 하류 제출 (`task_runner_service.py:681-711`) |
| `_submit_wiki_compile` | `KnowledgeCompilerService.recompile_openkb(from_task_chain=True)` | openkb 컴파일 (`task_runner_service.py:834-881`) |
| `_submit_jonex_wiki_compile` | `JonexWikiService.queue_task_compile` | jonex_wiki 컴파일 대기열 표시 (`task_runner_service.py:883-890`) |
| `ReconciliationService.patrol_openkb_compile` (30초) | `list_compile_tasks` → `_record_openkb_status_by_id` | openkb 종단 상태 회수 (`reconciliation_service.py:2677-2791`) |
| `ReconciliationService.patrol_jonex_wiki_compile` (30초) | `list_compile_tasks`/`get_compile_status` → `_patrol_stale_recompile(kb_type="jonex_wiki")` → `_resubmit_jonex_wiki_stale` → `JonexWikiService.compile_documents` | jonex_wiki 종단 상태 회수 + KB 단위 묶음 제출 (`reconciliation_service.py:2793-2927, 3056-3147`) |
| `TaskWatchService` | `llm_wiki_compile_status` 열 | task center에 종단 보고(두 wiki 종류가 같은 열을 본다) (`task_watch_service.py:613-615, 701-704`) |
| `LlmWikiSchemaService.save_schema` | `apply_schema_to_engine` → `get_openkb_client().apply_schema` 또는 `get_jonex_wiki_client().apply_schema` | schema 투영 (`llm_wiki_schema_service.py:262-406`) |
| `SearchService.search` | `_search_openkb` 또는 `search_jonex_wiki` | KB 하나 검색 (`search_service.py:1890-1912`) |
| `SearchService.search_llmwiki` | `KnowledgeCompilerService.search_compiled_knowledge` → openkb `run_query` | openkb 검색 (`search_service.py:7613-7830`) |
| `SearchService.search_mix` | `query_with_ontology` / `search_llmwiki` / `search_jonex_wiki` 병렬 | 섞인 KB 검색 (`search_service.py:8148-8300`) |
| `WikiOutlineService` | `JonexWikiService.get_outline/draft_outline/adjust_outline` | 읽기용 목차 (`wiki_outline_service.py:1-71`) |
| `DocumentService.get_document_chunks` | `llm_wiki_artifacts.load_llm_wiki_blocks` | 원문 보기 블록 (`document_service.py:1286-1288, 1322-1381`) |
| `mcp_server/tools.py:search_llmwiki/search_jonex_wiki` | gateway `search_llmwiki`/`search_jonex_wiki`, 실패하면 `search_mix` | 외부 에이전트 검색 (`mcp_server/tools.py:771-884`) |

### 1.3 핵심 자료 구조

**`knowledge_base.knowledge_info`** (`deploy/postgres/migrations/004_knowledge_base.sql:69-83`)
- `id, tenant_id, space_id, name, description, data_source_types, document_count, status, owner_id, kb_type VARCHAR(16) NOT NULL DEFAULT 'lightrag', created_at, updated_at, is_deleted`.
- `kb_type` 주석: "知识库类型 lightrag / openkb / jonex_wiki"(79행).
- `ingest_backend`는 `update/045_knowledge_info_ingest_backend.sql`로 나중에 붙은 열이다. 값은 `rag` 하나, NULL은 "跟随服务端开关"(서버 스위치를 따른다)이다.

**`knowledge_base.knowledge_documents`의 wiki 열** (`004_knowledge_base.sql:164-199`, `capabilities/knowledge_base/models/document.py:56-108`)
- `llm_wiki_compile_status` — "NULL/compiling/compiled/stale/failed"(191행).
- `llm_wiki_compile_error`, `llm_wiki_compile_warnings JSONB`, `llm_wiki_compile_requested_at`(UTC, patrol 시한 기준), `llm_wiki_compiled_at`, `llm_wiki_task_id`(엔진 컴파일 task id).
- `llm_wiki_target_schema_version`(claim 때 쓰는 목표 schema 판) / `llm_wiki_applied_schema_version`(완료 때 patrol이 씀).
- `content_generation` — "reparse 代次：每次 reparse 原子递增，旧代次任务结果作废"(재파싱 세대, 181행).
- `content_hash` — 같은 KB 안 md5 중복 업로드 거부용(`document_service.py:510-526`).
- `extra_metadata JSONB` — wiki 쪽은 `ingest_backend`, `kb_type`, `jonex_wiki_compile_execution_id`, `jonex_wiki_compile_parse_execution_id`, 옛 호환 키 `openkb_compile_status`를 담는다.
- 작성자(업로더) 열은 없다. `Column` 목록(`models/document.py:56-108`)에 `created_by`·`uploader`·`author`가 없고, grep으로 찾은 `created_by`는 `tag.py:23`, `folder.py:24`뿐이다. 업로드한 사람은 감사 로그(`schedule_emit`의 `user_id`)에만 남는다(`document_service.py:566-579`).

**`knowledge_base.llm_wiki_schemas`** (`004_knowledge_base.sql:600-644`, `models/llm_wiki_schema.py:30-79`)
- `id, tenant_id, knowledge_base_id, schema_version, status(active/archived), sync_status(synced/apply_failed), schema_name, language(기본 zh-CN), model, entity_types JSONB, concept_types JSONB, agents_md_extra TEXT, agents_md TEXT, config_snapshot JSONB, edited_by, edited_at, applied_at, created_at, updated_at`.
- 부분 유일 인덱스 `uq_llm_wiki_schema_active (tenant_id, knowledge_base_id) WHERE status='active'` — KB마다 active는 하나다.
- `entity_types[]` 항목: `{code, name, description, examples[]}`. `code`는 `^[a-z0-9 _-]+$`(`dtos/llm_wiki_schema.py:18, 41-55`).
- `concept_types[]` 항목: `{code, name, description}`(`dtos/llm_wiki_schema.py:58-73`).

**openkb 쪽 디스크 배치** (`openkb_adapter.py:121-125, 326-339, 528-552, 970-1011`)
- KB 디렉터리: `$OPENKB_KB_ROOT/{tenant_id}__{kb_id}/{kb_name}`(kb_name = kb_id).
- `.openkb/config.yaml`(model, language, entity_types), `.openkb/hashes.json`(HashRegistry), `.openkb/tasks/{task_id}.json`, `.openkb/jonex_schema.json`, `wiki/AGENTS.md`, `wiki/sources/{document_id}.md`, `wiki/sources/images/{document_id}/`, `wiki/summaries/`, `wiki/concepts/`, `wiki/entities/`, `wiki/index.md`, `wiki/log.md`.
- task 파일: `{task_id: "t_<uuid hex>", document_id, status: pending|running|completed|failed, error, warnings[], created_at, started_at, updated_at, wiki_schema_version}`(`openkb_adapter.py:394-400`).
- `jonex_schema.json`: `{schema_version, schema_hash: sha256(agents_md + "\n" + json(config, sort_keys)), applied_at, source: "jonex.llm_wiki_schemas"}`(`openkb_adapter.py:330-339`).
- 페이지 frontmatter의 `sources: ["summaries/{doc_id}.md", …]`가 개념·엔티티 페이지의 문서 귀속 판단 근거다(`openkb_adapter.py:709-735`).

**jonex-wiki 쪽 배치** (훑음)
- 엔진 산출물 루트: `{root}/{tenant_id}/{kb_id}`(`Reference/JonexWiki/src/jonex_wiki/storage/layout.py:47-48`). 엔진 DB 행도 `(tenant_id, kb_id)`로 거른다(`storage/repos.py:9-90`).
- 페이지 종류 `source | table | concept`를 플랫폼은 OpenKB 어휘 `summaries | entities | concepts`로 바꿔 보여 준다(`jonex_wiki_adapter.py:30-34`).
- 정규화한 citation: `{document_id, chunk_id, passage_id, source_id, claim_id, excerpt, page_path, evidence_ref}`(`jonex_wiki_adapter.py:155-180`).

**능력 호출 봉투** (`openkb/client.py:85-106`)
- 요청: `{capability_id, payload: {action, knowledge_base_id, data}, tenant_id}` + 헤더 `X-Tenant-ID`, `X-API-Key: GATEWAY_API_KEY`.
- 응답: `{success, data}` 또는 `{success:false, message, details:{error_code}}`. 클라이언트는 `PATH_OUT_OF_SCOPE`/`MISSING_PARAM`을 400, `PAGE_NOT_FOUND`를 404로 되돌린다(`openkb/client.py:97-105`). jonex_wiki 클라이언트는 엔진 코드를 `details.engine_error_code`로 실어 보낸다(`jonex_wiki/client.py:113-120`).

**그래프 계약 (`list_graph`)** — 두 엔진이 같은 모양을 낸다: `{entities:[{id, name, type, description, section, sources}], relationships:[{source, target}], entities_count, relationships_count}`(`openkb_adapter.py:877-882`, `jonex_wiki_adapter.py:525-530`).

## 2. 동작 흐름

### 2.1 KB 생성

1. 입력: `kb_type` 문자열. `resolve_creatable_kb_type`이 두 단계로 막는다. 모르는 값은 `err.kb.invalid_kb_type`, 이 배포에서 꺼 둔 값은 `err.kb.kb_type_disabled`다. 빈 값은 `lightrag`가 된다(`kb_type_service.py:99-128`).
2. KB 행을 같은 트랜잭션에서 만들고 기본 파서 설정 5종을 넣는다(`knowledge_info_service.py:100-102`).
3. 커밋 뒤 openkb는 `init_kb`(KB 디렉터리 + 기본 AGENTS.md)를 부른다. jonex_wiki는 "首次 ingest 即建"(첫 ingest 때 만든다)이라 건너뛴다(`knowledge_info_service.py:104-121`, `jonex_wiki_service.py:120-130`).
4. 두 종류 다 `LlmWikiSchemaService.get_schema(auto_create=True)`로 기본 schema 행(v1)을 만들고 곧바로 `apply_schema_to_engine`을 부른다(`llm_wiki_schema_service.py:218-260`). apply 실패는 KB 생성을 막지 않고 `sync_status=apply_failed`로 남는다(`knowledge_info_service.py:108, 122-127`).
5. `kb_type`은 생성 뒤 바꿀 수 없다(`knowledge_info_service.py:439-452`). 옛 이름 `pipeline_type`도 함께 막는다(443행).

### 2.2 업로드 → 파싱 → 컴파일 (세 종류 공통 틀)

1. `upload_document`(`document_service.py:427-679`)가 차례로 검사한다. 모두 결정적(코드) 검사다.
   - storage_key의 테넌트·KB·문서 구간이 현재 맥락과 같은지(433-467) — 어긋나면 `PermissionDeniedError`.
   - 데이터 소스 귀속(471-475), 쿼터 정적 검사(파일 종류·크기, 506-508).
   - 같은 KB 안 md5 중복(510-526) — 같으면 `ResourceConflictError`.
   - 쿼터 계수 검사는 INSERT와 같은 트랜잭션에서 advisory lock으로 한다(531-533).
   - 행을 `status=PARSING, ontology_status=PENDING`으로 만들고 감사 로그 두 줄(OPERATION `upload_document`, TASK `document.parse`)을 비동기로 낸다(566-591).
2. `kb_type`과 KB의 `ingest_backend`를 한 번만 읽는다(606-611). llm-wiki 종류는 ontology compiled schema 계산을 통째로 건너뛴다(615-632).
3. 파서 preset을 고른다(638-642). `kb_type in SUPPORTED_KB_TYPES`(세 종류 모두, `task_runner_service.py:239`)면 `_upload_via_task_center`로 넘기고 끝낸다(661-679). 아래 옛 경로(`get_rag_client().insert`, 681-785)는 이제 세 종류 모두 타지 않는다.
4. task center 편성은 종류마다 하나다. 셋 다 `parse_1 → compile_1` 두 단계다(`task_runner_service.py:26-38`).
   - lightrag: `definition-file-processing-ontology`
   - openkb: `definition-file-processing-ontology-wiki` — parse는 atomic-rag `parse_only`로 `content.md`를 쓴다.
   - jonex_wiki: `definition-file-processing-jonex-wiki` — parse는 `parse_only`로 `content_list.json`을 쓴다.
   - 두 wiki 종류의 parse 모드는 `insert_mode_for`의 표 `(STEP_PARSE,"openkb")→"parse_only"`, `(STEP_PARSE,"jonex_wiki")→"parse_only"`로 정한다(205-206행). 산출물 모양은 atomic-rag가 요청에 실린 `kb_type`을 보고 정한다(`Reference/Rag-anything/raganything/service/task_manager.py:1841-1863, 1949`).
5. handler는 "我收下了"(받았다)만 뜻하는 `ApiResponse.ok()`를 돌려준다. 종단 상태는 `TaskWatchService`(30초)가 문서 열을 보고 보고한다(`task_runner_service.py:13-25, 101-108`).
6. 업로드 때 wiki 종류는 `ontology_status=READY`로 바로 둔다. 옛 경로의 이유는 "避免对账巡检前 30s 窗口内 ontology_status=PENDING … 导致前端显示误导的「知识抽取入库中」"(대조 순찰 전 30초 동안 '지식 추출 중'으로 잘못 보이는 것을 피한다)이다 — `document_service.py:755-762`. task center 경로는 처음에 이 처리를 빠뜨렸다. 주석은 그 결과를 "实测 7/7 份 openkb 文档全部停在 `ontology_status=failed`"(실측으로 openkb 문서 7개 모두 failed에 멈췄다)라고 적는다. 본체 대조가 wiki KB에 본체 추출을 시도해 schema를 새로 만들고 실패했기 때문이다 — `document_service.py:918-937`.

### 2.3 openkb 컴파일 단계

1. `_submit_wiki_compile` → `KnowledgeCompilerService.recompile_openkb(from_task_chain=True)`(`task_runner_service.py:858-867`).
2. `recompile_openkb`(`openkb_service.py:194-284`)의 검사는 다음과 같다.
   - 체인에서 왔으면 `DELETING`만 막는다. 사용자가 누른 경우는 `PARSING/PENDING/INGESTING/DELETING`을 막는다(221-239).
   - 공유 볼륨에 `parsed/{doc}/content.md`가 없으면 claim 전에 바로 실패한다(242-247).
   - active schema 판을 읽는다(252).
   - `claim_compile`: 조건부 UPDATE `... WHERE coalesce(llm_wiki_compile_status,'') <> 'compiling' RETURNING knowledge_base_id, content_generation`로 원자 점유한다. 같은 UPDATE에서 옛 task_id·error·warnings를 지우고 `target_schema_version`을 쓴다(297-374). 같은 트랜잭션 안에서 처리 task 계측 행도 쓴다(363-372).
   - 제출이 실패하면 `failed`로 되돌린다(273-278). "投递失败必须回滚 claim，否则永久卡 compiling"(264).
3. 제출 artifact: `{document_id, source_file_path, parsed_markdown_path: "parsed/{doc}/content.md", assets_dir, parser, metadata:{pages, title, recompile}, wiki_schema_version}`(`openkb_service.py:162-171`).
4. openkb 어댑터 `_handle_compile_parsed_document`(`openkb_adapter.py:352-409`)의 처리는 다음과 같다.
   - 경로 검증: `OPENKB_INPUT_ROOT` 밖이면 `PATH_OUT_OF_SCOPE`(911-937).
   - KB가 없으면 `initialize_kb(model=env_llm_model())`(378-380).
   - `OPENKB_LANGUAGE`가 있으면 config에 맞춘다(383-388).
   - task 파일을 `pending`으로 쓰고 백그라운드 task로 `_run_compile_task`를 띄운 뒤 곧바로 `{task_id, status:"pending"}`을 돌려준다(394-409).
5. `_run_compile_task`(`openkb_adapter.py:413-467`)는 KB별 `asyncio.Lock` 안에서 돈다.
   - 펜싱 ②: 디스크 `jonex_schema.json`의 판을 다시 읽는다. 없으면 `SCHEMA_NOT_APPLIED`, 다르면 `SCHEMA_VERSION_MISMATCH`로 task를 실패 처리한다(419-442).
   - 컴파일 본체는 `asyncio.to_thread`로 따로 띄운 스레드의 이벤트 루프에서 돈다(443-454).
   - 실패는 `logger.exception` 뒤 task 파일에 `failed`로 남긴다(457-467).
6. `_compile_parsed_markdown`(`openkb_adapter.py:939-1013`)의 처리는 다음과 같다.
   - LLM 모델을 고른다: config 값 > `OPENKB_LLM_MODEL` > `ModelNotConfiguredError`. 모델 이름에 `/`가 없으면 `openai/`를 붙인다(896-909, 963-968).
   - `kb_ingest_lock` 파일 락 안에서 registry의 옛 기록을 지우고 `wiki/sources/{doc}.md`를 원자적으로 덮어쓴다. 이미지 폴더는 통째로 바꾼다(975-987).
   - **vendored OpenKB의 `compile_short_doc`를 바로 부른다**(990-997). 주석은 "不经过 converter/indexer，不触发 PageIndex"(OpenKB 자체 변환기·색인기를 거치지 않고 PageIndex도 부르지 않는다)이다(943).
   - 성공하면 HashRegistry에 등록한다(1000-1011).
7. `compile_short_doc`의 LLM 단계(OpenKB 원래 동작, 훑음): "Step 2: A → generate summary. Step 3: A + summary → concepts plan (create/update/related). Step 4: Concurrent LLM calls … generate new + rewrite updated concepts. Step 5: Code adds cross-ref links"(`Reference/OpenKB/openkb/agent/compiler.py:1-8`). 시스템 프롬프트에는 `wiki/AGENTS.md` 전체가 `{schema_md}`로 들어간다(compiler.py:53-56, 2225-2234). 계획 프롬프트는 기존 개념·엔티티의 한 줄 요약 목록 전체를 보여 주고 "Prefer "update" over "create" … Do NOT create a concept/entity that overlaps an existing one"을 시킨다(compiler.py:90-127, 727-757).
8. 플랫폼 `patrol_openkb_compile`(30초, `reconciliation_service.py:2677-2791`)이 종단 상태를 회수한다.
   - `kb_type='openkb'`이고 `compiling`인 문서를 50개까지 골라 `(tenant, kb)`별로 `list_compile_tasks`를 한 번씩 부른다.
   - completed는 `compiled`로 바꾸고 warnings와 `applied_schema_version=task.wiki_schema_version`을 쓴다.
   - failed는 `failed`로 바꾼다.
   - running은 `started_at`부터 `OPENKB_COMPILE_TIMEOUT_SEC`(기본 1800초)를 넘기면 시한 초과 실패로 한다.
   - task가 목록에 없으면 `OPENKB_TASK_LOST`로 실패 처리한다.
   - task_id가 비어 있으면 `requested_at` 기준 시한만 본다.
   - 컨테이너에 닿지 않으면 판정을 미룬다. "容器不可达：保持现状不判死（对账降级，不误杀）"(2729).
   - 마지막에 `stale`인 ready 문서를 다시 제출한다(`_patrol_stale_recompile`, 2786, 2929-3039).

### 2.4 jonex_wiki 컴파일 단계 (KB 단위 묶음)

1. `_submit_jonex_wiki_compile` → `queue_task_compile`(`jonex_wiki_service.py:427-477`)은 컴파일하지 않는다.
   - task center 소유 행을 `FOR UPDATE`로 잠그고 execution_id가 같은지 본다(436-447).
   - 문서를 `llm_wiki_compile_status='stale'`로 두고 `jonex_wiki_compile_execution_id`를 남긴 뒤 끝난다(469-477).
   - 같은 execution이 다시 오면 아무것도 하지 않는다(454-455).
2. 옛 경로(`_handle_completed` → `_dispatch_jonex_wiki_compile`, `reconciliation_service.py:1853-1858, 2567-2619`)도 결과는 같다. 산출물이 있는지 확인한 뒤 `stale`로 둔다. 주석은 다음과 같다. "Parsing success is not a KB-wide batch-complete signal. Keep this source durable and waiting; the patrol drains all ready sources once the platform has no pending parses and the upload window is quiet."(2616-2618)
3. `patrol_jonex_wiki_compile` → `_patrol_stale_recompile(kb_type="jonex_wiki")` → `_resubmit_jonex_wiki_stale`(`reconciliation_service.py:3056-3147`).
   - KB마다 `pg_try_advisory_xact_lock(hashtext('jonex-upload-window:{tenant}:{kb}'))`를 잡는다.
   - 다음 중 하나라도 있으면 이번 회차는 건너뛴다(3072-3092): 같은 KB에 `pending/parsing/ingesting` 문서가 있다. 5초 안에 `stale`이 된 문서가 있다. 아직 컴파일 단계에 들어서지 않은 task center 소유 행이 있다.
   - 조용하면 ready+stale 문서 전부를 `claim_compile(batch=True)`로 점유한다. `.xlsx/.xlsm`은 원본 이진 파일을 `parsed/{doc}/source{ext}`로 옮기고, 나머지는 `content_list.json → raw.md → content.md` 순으로 찾는다(3042-3054, 3108-3126).
   - **한 번의 `compile_parsed_documents`로 엔진에 넘긴다**(3130). 받은 task_id를 모든 문서에 같이 쓴다(3133-3137).
   - 실패 메시지에 엔진 유일 인덱스 이름(`uq_tasks_queued_compile`, `uq_tasks_running_compile`)이 보이면 "KB 바쁨"으로 보고 `stale`로 되돌려 다음 회차에 다시 낸다. 그 밖의 실패는 `failed`다(3139-3144, `_JONEX_WIKI_COMPILE_BUSY_MARKERS` 69-79).
4. 엔진 쪽(어댑터 → `app.ingest_parsed_documents`, `jonex_wiki_adapter.py:289-290`)의 내부 처리는 jonex-wiki 엔진 갈래가 맡는다.
5. 종단 상태 회수는 openkb와 같은 틀이다.
   - 엔진 상태어를 바꾼다: `done→completed`, `cancelled→failed`(`jonex_wiki_adapter.py:21-28`).
   - 목록에 task가 없으면 단건 조회를 한 번 더 한 뒤에야 잃어버림으로 판정한다(`reconciliation_service.py:2864-2879`).
   - 50개 창을 커서로 돌린다(2825-2826).
   - 완료 때 `warnings=None`을 넘겨 제출 때 쓴 진단 결과를 지우지 않는다(2888-2897).

### 2.5 재파싱 · 재컴파일 · 삭제

- 재파싱: 두 wiki 종류는 lightrag의 `reparse_strict` 분기가 없다. 같은 `parse_only`를 다시 낸다(`task_runner_service.py:60-66, 700-707`). 재파싱을 시작할 때 컴파일 상태를 `stale`로 두고 옛 task_id를 지운다(`document_service.py:1798-1810`). 산출물이 사라졌으면 "源文件未变也不能无条件 skip"(원본이 그대로여도 무조건 건너뛰지 않는다, 1705-1713).
- 재컴파일 버튼: task center의 `retry_subtask_for_step("compile")`로 `compile_1`만 다시 돌린다. 새 task를 만들지 않는다(`task_runner_service.py:47-56`).
- 삭제: `kb_type`별로 엔진 `remove_document`를 부른다. 실패하면 warning만 남기고 플랫폼 행은 지운다(`document_service.py:2397-2422`). llm-wiki는 Neo4j 정리를 건너뛴다(2436-2443). openkb 쪽 삭제는 `run_remove_for_api(kb_dir, document_id, keep_raw=True)`가 source·assets·registry·파생 페이지를 정리한다(`openkb_adapter.py:1015-1033`).
- 삭제 전파 실패의 후유증(jonex_wiki): 엔진에 남은 같은 이름 문서가 이름을 붙잡아 다시 올린 문서가 "同知识库已存在同名文档"로 막힌다. `compile_document`가 이를 자가 치유한다(`jonex_wiki_service.py:143-191`).
  - 엔진이 `conflict` 코드를 내고 같은 KB에 같은 이름의 *soft-delete된* 플랫폼 문서가 있을 때만 움직인다.
  - 그 id로 엔진 `remove_document`를 부른 뒤 한 번만 다시 시도한다.

### 2.6 LLM-Wiki Schema 저장 · 투영 · 펜싱

1. `save_schema`(`llm_wiki_schema_service.py:262-349`)는 차례로 처리한다.
   - ① `expected_schema_version`이 현재 active 판과 같아야 한다(CAS). 다르면 `LLM_WIKI_SCHEMA_VERSION_CONFLICT`(271-289).
   - ② openkb면 entity_types에 `other`가 있어야 한다(291-301).
   - ②b code가 겹치면 안 된다(303-307).
   - ③ AGENTS.md를 렌더링한다(309-327).
   - ④ 옛 행을 archived로, 새 행을 v+1 active로 같은 트랜잭션에서 바꾼다(329-338).
   - ⑤ 엔진에 투영한다. 실패해도 막지 않는다(340-341).
   - ⑥ 그 KB의 ready 문서 전부에 `llm_wiki_target_schema_version=v+1`을 쓴다(343-345, 408-424).
2. `render_agents_md`(102-152)는 다음을 이어 붙인다: `AGENTS_MD_SNAPSHOT`(OpenKB `schema.py` AGENTS_MD 복사본, 37-97) + "## Entity Types (受控词表)" + 있으면 "## Concept Types" + 사용자 추가 블록 원문. 결과는 "同一配置渲染结果 byte 级一致（确定性）"(같은 설정이면 바이트까지 같다)이다(109).
3. openkb 투영 `_handle_apply_schema`(`openkb_adapter.py:290-350`)는 컴파일과 같은 KB mutation 락 안에서 돈다.
   - config.yaml의 model/language/entity_types를 합친다. None이나 []는 키를 지운다.
   - `wiki/AGENTS.md`를 원자적으로 쓰고 `jonex_schema.json`(판+hash)을 쓴다.
   - 다시 읽어 다르면 고쳐 쓴다.
4. jonex_wiki 투영 `_apply_schema`(`jonex_wiki_adapter.py:707-721`)는 agents_md(= 사용자 "编译偏好" 접미사) 하나를 엔진 prompt 키 `compile_main`에 넣는다. 엔진 prompt는 따로 판을 매긴다. 처음은 0, 그 뒤로는 엔진 현재 판을 넘긴다(710-717).
5. 펜싱은 두 겹이다(openkb만). ① claim 때 목표 판을 문서 열에 묶고 같은 판을 task 파일에 싣는다. ② 실행 시작 때 디스크 판과 비교한다. 완료 때 patrol이 `applied_schema_version`을 쓴다(`openkb_service.py:249-261`, `openkb_adapter.py:419-442`, `reconciliation_service.py:2754-2760`).
6. 전체 재컴파일 `recompile_outdated_documents`(519-578)는 `applied IS DISTINCT FROM target`인 ready 문서를 한꺼번에 모두 낸다. "一次性提交全部匹配文档，不分批不限流"(나누거나 속도를 제한하지 않는다)이다(523-524).

### 2.7 검색

- KB 하나(`search`, `search_service.py:1890-1912`): openkb는 `_search_openkb`, jonex_wiki는 `search_jonex_wiki`로 보낸다. 주석은 "原先这里直接抛「即将上线」——但 DomainService.search 是**逐个 KB 调本方法**的，于是任何含 jonex_wiki KB 的领域服务检索都被判失败"(원래 '곧 공개'를 던졌는데 도메인 서비스 검색이 KB마다 이 메서드를 불러 실패가 났다)이다(1900-1903).
- openkb(`search_llmwiki`, 7613-7830):
  1. 종류가 다른 KB가 섞이면 맞는 엔드포인트를 알려 주며 거부한다(7628-7652).
  2. 문서 0개인 KB는 엔진을 부르지 않는다. "不烧 openkb agent 的 50 轮"(에이전트 50턴을 태우지 않는다)이다(7662).
  3. KB마다 OpenKB `run_query`(OpenAI Agents SDK 에이전트, `MAX_TURNS=50`, `Reference/OpenKB/openkb/agent/query.py:24, 550`)를 세마포어 3개로 병렬 실행한다(`OPENKB_SEARCH_MAX_CONCURRENCY`, 480).
  4. 에이전트 프롬프트는 index.md → summaries → concepts → entities → 원문 순서로 탐색하라고 시키고 AGENTS.md 전체를 앞에 붙인다(query.py:26-58, 67-68).
  5. 출처: 에이전트가 읽은 파일 경로 궤적에서 문서를 거꾸로 찾는다. `summaries/<uuid>.md`는 그 uuid가 곧 문서다. 개념·엔티티 페이지는 frontmatter `sources`로 문서를 찾는다(`_build_openkb_references` 7153-7260).
  6. 답에 `[n]` 표시가 없어서 LLM이 "문서 이름 목록"만 보고 표시를 끼워 넣는다(`anchor_answer_to_references`, `jonex_core/common/ontology_llm.py:770-840`).
  7. KB가 여럿이면 상위 3개(`ONTOLOGY_RAG_FUSION_TOPN`, `search_service.py:474`) 답을 LLM으로 융합한다(`fuse_rag_answers`, ontology_llm.py:673-768).
- jonex_wiki(`search_jonex_wiki` 7877-): 어댑터가 엔진 비동기 query task를 0.5초 간격, 최대 240초 동안 polling한다(`jonex_wiki_adapter.py:43-47, 353-398`). 엔진이 검증한 citation(문서·chunk·passage·claim·발췌·page_path)을 늘 돌려준다. 플랫폼은 문서별로 묶고 요청 KB 밖 문서를 뺀다(`_build_jonex_wiki_references` 7408-7450).
- 섞인 선택(`search_mix` 8148-): 세 통으로 나눈다. 한 통뿐이면 그쪽 검색에 위임하고, 여럿이면 병렬로 돌린 뒤 융합한다. 하위 호출은 `save_history=False`다(8237-8243).
- MCP: `search_llmwiki`/`search_jonex_wiki` 도구가 파이프라인 불일치(-32602)나 사용 불가(-32000)를 받으면 `search_mix`로 돌아간다(`mcp_server/tools.py:771-884`).

### 2.8 읽기 화면 API

- openkb `read_page`(`openkb_adapter.py:589-637`): 경로를 `(summaries|concepts|entities)/[\w\-]+(/[\w\-]+)*` 정규식과 resolve 뒤 wiki 디렉터리 안인지로 검증한다. frontmatter를 떼고 `{path, section, name, title, type, description, sources, content}`를 돌려준다. 문서 귀속은 검사하지 않는다(594-595).
- openkb `list_graph`(827-882): 개념·엔티티 페이지가 노드다. 본문 `[[...]]` wikilink가 간선이다. 요약 페이지는 뺀다.
- openkb `list_wiki_contents`(769-792): 페이지 머리 64KB만 읽어 frontmatter와 H1을 뽑는다(639-707). `view=counts`는 개수만 준다.
- jonex_wiki `read_page`(`jonex_wiki_adapter.py:532-626`)가 돌려주는 것:
  - 정본 경로와 옛 `{section}/{stem}` 경로를 둘 다 준다.
  - 메타데이터: aliases, tags, why_visit, limitations, interpretation_status, fields, scope.
  - 링크: related, links, link_meta(kind, why_visit).
  - 페이지 수준 references: 문서별 발췌, claim 수, chunk_id, 문자 구간.
- jonex_wiki 전용: `get_wiki_backlinks`(링크와 본문 언급을 합친 역링크, 30개 상한, 628-676), `get_wiki_claims`(claim 단위 출처 감사, 500개 상한, 678-705), 목차 `list/draft/adjust_wiki_outline`(엔진으로 위임, `wiki_outline_service.py`), 컴파일 일시정지·재개(`api_gateway/routes/knowledge_base.py:1397-1416`).
- 원문 보기(`llm_wiki_artifacts.py`): jonex_wiki는 `content_list.json → raw.md → content.md`, openkb는 `content.md`를 읽는다. 빈 줄로 블록을 나누고 블록 id를 `{doc}#{kb_type}-{i}`로 매긴다(45-47, 188-224, `document_service.py:1350-1381`).

### 2.9 LLM 호출 지점

| 지점 | 파일 | 프롬프트 | 비고 |
|---|---|---|---|
| openkb 요약·계획·개념/엔티티 페이지 생성 | `Reference/OpenKB/openkb/agent/compiler.py` (`compile_short_doc`, 2225·2313 부근) | `_SYSTEM_TEMPLATE`(53-56)+AGENTS.md, `_CONCEPTS_PLAN_USER`(90-127) | litellm 경유, 동기 호출이라 to_thread로 감쌌다 |
| openkb 질의 에이전트 | `Reference/OpenKB/openkb/agent/query.py:26-58, 550` | `_QUERY_INSTRUCTIONS_TEMPLATE`+AGENTS.md | 최대 50턴 |
| openkb 답 인용 표시 끼우기 | `jonex_core/common/ontology_llm.py:770-840` | "citation anchoring assistant" | temperature 0 |
| 여러 KB 답 융합 | `ontology_llm.py:673-768` | "RAG answer fusion assistant" | temperature 0, 실패하면 `---`로 이어 붙인다 |
| jonex_wiki 컴파일·질의·목차 | `Reference/JonexWiki` 엔진 | 공개 키는 `compile_main` 하나, 나머지 18개는 고정(`domain/prompts.py:14-53`) | 다른 갈래 |
| openkb lint | OpenKB `linter.py` | 플랫폼에서 부르는 곳은 찾지 못했다 | scene 열거에만 `openkb_lint`가 있다(`Reference/OpenKB/JONEX_CHANGES.md:29-36`) |

모든 호출은 llm-gateway로 간다. OpenKB는 contextvar에 담은 `X-Jonex-Tenant-Id/Kb-Id/Scene/Trace-Id`를 litellm `extra_headers`로 싣는다(`Reference/OpenKB/openkb/jonex_metering.py`, `openkb_adapter.py:127-136, 1053-1063`). 게이트웨이는 이 헤더로 `metering.llm_usage_log`에 테넌트·KB·문서·장면별 사용량을 남긴다(`jonex_core/llm_gateway/context.py:22-50`).

### 2.10 결정적(코드) 검사 지점 모음

- KB 종류 화이트리스트와 생성 차단(`kb_type_service.py:47-128`). 생성 뒤 불변(`knowledge_info_service.py:439-452`).
- 업로드: storage_key 테넌트 구간, 쿼터, md5 중복(`document_service.py:433-533`).
- 컴파일 점유: 조건부 UPDATE(`openkb_service.py:313-352`). 산출물 존재(242-247). 문서 상태 바쁨(221-239).
- 경로 탈출 방지(`openkb_adapter.py:911-937, 604-618`).
- schema: code 형식·유일성, `other` 필수, CAS 판(`llm_wiki_schema_service.py:169-193, 271-307`). YAML `format_version==1`(463-473).
- 펜싱 판 비교(`openkb_adapter.py:419-442`). apply 뒤 AGENTS.md 다시 읽기(341-348).
- openkb 엔티티 type이 목록 밖이면 `other`로 바꾼다(OpenKB 컴파일러 원래 동작, `compiler.py:650-676`. 앞선 보고서가 확인).
- 출처 단계에서 요청 KB 밖 문서를 뺀다(`search_service.py:7414-7420`).

### 2.11 실패 · 재시도

| 상황 | 처리 | 출처 |
|---|---|---|
| 엔진 컨테이너 재시작 | 시작 때 `pending/running` task를 `failed: task lost after restart`로 바꾼다 | `openkb_adapter.py:222-243` |
| task 잃어버림 | `OPENKB_TASK_LOST`/`JONEX_WIKI_TASK_LOST` 실패 | `reconciliation_service.py:2745-2752, 2872-2879` |
| 실행 시간 초과 | running부터 1800초가 지나면 실패. 대기 시간은 세지 않는다 | 2766-2785 |
| 제출 실패 | claim을 `failed`로 되돌린다 | `openkb_service.py:273-278` |
| jonex_wiki KB 바쁨 | `stale`로 되돌려 다음 순찰 때 다시 낸다 | `jonex_wiki_service.py:572-589`, `reconciliation_service.py:3139-3144` |
| 엔진에 닿지 않음 | 판정을 미룬다 | 2724-2729 |
| 재파싱 뒤 stale에 갇힘 | 순찰 때 다시 낸다 | 2929-2939 |
| 모델 미설정 | `MODEL_NOT_CONFIGURED`(400). 대체 모델로 넘어가지 않는다 | `openkb_adapter.py:176-191` |
| 출처 반추적 실패 | 직접 맞은 문서만 남긴다 | `search_service.py:7232-7235` 부근 |
| 융합 LLM 실패 | 답을 이어 붙인다 | `ontology_llm.py:763-767` |
| 자동 재컴파일 | 없음. 실패한 문서는 사람이 다시 누르거나 재파싱해야 한다(stale만 자동으로 다시 낸다) | 순찰 SQL 조건이 `stale`만 고른다(`reconciliation_service.py:2951`) |

## 3. kb_type 세 가지가 갈리는 곳

| 갈림점 | lightrag (화면 이름 "Ontology") | openkb ("Ontology Wiki") | jonex_wiki ("Jonex Wiki") |
|---|---|---|---|
| 화면 이름 출처 | `deploy/.env.example:961-964` | 같음 | 같음. 설명은 "新一代 LLM Wiki 引擎"(새 세대 LLM Wiki 엔진) |
| 파싱 모드 | `full`(파싱+청크를 LightRAG에 넣음), 재파싱은 `reparse_strict` | `parse_only` → `content.md` | `parse_only` → `content_list.json`(MinerU 구조 배열). xlsx는 원본 |
| 둘째 단계 | atomic-rag `ontology_only` → Neo4j | OpenKB `compile_short_doc`, 문서 하나씩 | 엔진 묶음 ingest, KB 전체 한 번 |
| 직렬화 단위 | (ontology 갈래) | KB별 asyncio.Lock + 파일 락 | 엔진 유일 인덱스 "실행 1 + 대기 1"(`reconciliation_service.py:55-68`) |
| 사람이 쓰는 설정 | TBox YAML + 동의어 묶음(앞선 보고서) | LLM-Wiki Schema: entity_types(통제 어휘), concept_types(안내만), 자유 추가 블록 → AGENTS.md | `compile_main` 접미사 하나(빈 값 가능) |
| schema 펜싱 | ontology 판(별도) | 두 겹, applied 회수 | 목표 판만 쓰고 applied는 회수하지 않는다(4.2 참고) |
| 그래프 | Neo4j `OntologyEntity` | 페이지 + wikilink를 그래프로 투영 | 페이지 + frontmatter links를 투영 |
| 검색 | ontology+RAG | 에이전트 탐색 + 궤적으로 출처 + LLM 인용 표시 | 엔진 검색 + 검증된 citation |
| 출처 단위 | chunk | 문서(요약 페이지 수준) | claim/chunk/문자 구간 |
| 삭제 | LightRAG + Neo4j 정리 | `run_remove_for_api` | 엔진 `remove_document` |
| 상태 열 | `ontology_status` | `llm_wiki_compile_status` | 같은 열 |

KB 단위 배타성: llm-wiki 문서는 "只解析产出 markdown，不写 LightRAG/Neo4j"이다(`document_service.py:681-682`). 종류는 바꿀 수 없다. 종류를 가로지르는 연결은 질의 때 답 융합에서만 생긴다(2.7).

`get_kb_type`은 못 찾으면 `lightrag`로 떨어진다. 이 동작이 wiki 문서를 잘못 '컴파일 성공'으로 판정한 일이 있어서, 엄격판 `get_kb_type_or_none`이 따로 있다(`kb_type_service.py:131-168`).

## 4. Reference/OpenKB: 원 저장소, 라이선스, Jonex가 바꾼 것

### 4.1 원 저장소

- VectifyAI/OpenKB, Apache-2.0, 2026-04-04 생성, 마지막 push 2026-07-22, stars 4774(`gh api repos/VectifyAI/OpenKB`).
- 원 README: "compiles raw documents into a structured, interlinked wiki-style knowledge base using LLMs, powered by PageIndex's vectorless, reasoning-based retrieval". Karpathy 개념에 기댄다고 밝힌다(`Reference/OpenKB/README.md` 앞부분).
- `THIRD_PARTY_NOTICES.md`는 "Vendored version: `0.4.5`"라고 적는다. diff 결과(내가 실행함): 업스트림 태그 v0.4.5(ac11840, 2026-07-20)와는 `openkb/` 아래 34개 파일, 3195줄이 다르다. v0.5.0-rc1과는 20개 파일, 753줄이 다르다. **main ff54396(2026-07-22)과는 11개 파일, 482줄만 다르고 그 차이가 모두 Jonex 변경으로 설명된다.** 그래서 실제 기반은 0.4.5 태그가 아니라 업스트림 main 최신본이다. `JONEX_CHANGES.md:263`은 "上游 vendored 进来时 772 行（`5cec22c4`，2026-07-30）"이라고 적는다. `5cec22c4`는 공개 이력에 없다. 공개 이력은 squash되어 있다(`f6205dc` 메시지 "Squashed several dozen commits").
- 공개 이력에서 `Reference/OpenKB`가 처음 보이는 커밋은 `f6205dc`(2026-08-12)다. 같은 커밋이 "pipeline_type -> kb_type terms are now consistent everywhere"라고 적는다.

### 4.2 Jonex가 바꾼 것 (업스트림 main 대비 diff, 내가 실행함)

| 파일 | 바뀐 것 | 문서화 여부 |
|---|---|---|
| `openkb/jonex_metering.py` | 새 파일: contextvar + `build_metering_headers()` | `JONEX_CHANGES.md` §三(A) |
| `openkb/config.py` | `DEFAULT_CONFIG["model"]`를 `"gpt-5.4"`에서 `None`으로. `_read_env`, `env_llm_model`, `ModelNotConfiguredError`, `resolve_llm_model` 추가. `OPENKB_LLM_BASE_URL/API_KEY` 우선 | §三(B), §六~§九 |
| `cli.py, api.py, api_helpers.py, indexer.py, agent/chat.py` | `config.get("model", …)`을 `resolve_llm_model(config)`로 | §六 |
| `agent/compiler.py, agent/query.py, agent/linter.py` | "Write all content in {language} language"를 "the same language as the source document/user's question/wiki content"로 | §五 2026-08-10 |
| `agent/query.py` | `return_trace`, `_extract_run_trace`(턴별 thinking, LLM ms, 도구 호출 미리보기 200자), `_TurnTimingHooks` | §五 |
| `schema.py` | AGENTS_MD 끝에 중국어 블록 "## 输出要求（最高优先级，必须严格遵守）" 6줄과 예시("七月份的最佳投资公司是什么？ → 张三投资有限公司", "1+1等于多少？ → 2") 추가 | **문서화 안 됨, `[jonex]` 표시도 없음**. 들어온 커밋은 `41e1ff3`(2026-08-21) |

- `JONEX_CHANGES.md:3-4`의 규칙은 "所有改动均以 `# [jonex]` 注释标记"(모든 변경에 표시를 단다)이다. `schema.py` 변경은 이 규칙을 어긴다(grep `\[jonex\]`가 schema.py에서 0건).
- `JONEX_CHANGES.md` §四(46-53행)는 "不修改 `api.py`、`compiler.py`"라고 적는다. 그러나 뒤 절(§五·§六)에서 두 파일을 바꿨다. 요약 표가 낡았다.
- `JONEX_CHANGES.md` §十·10.3이 가리키는 수호 테스트 `tests/unit/test_openkb_model_resolution.py` 등은 공개 레포에 없다(루트에 `tests/`가 없다. find 결과 0건).
- 플랫폼은 OpenKB의 변환기·색인기·PageIndex·자체 웹 UI를 쓰지 않는다. Jonex 파싱 결과 markdown을 `compile_short_doc`에 바로 넣는다(`openkb_adapter.py:939-944`). 이미지는 Jonex 쪽이 만든 `images/{doc}/` 상대 경로를 그대로 쓴다(986-987).
- 업스트림 `iter_recompile(refresh_schema=True)`는 AGENTS.md를 영어 기본판으로 덮어쓴다. 플랫폼은 이것을 금지한다(`openkb_adapter.py:801-808`).

### 4.3 라이선스

- 본체: "Jonex Open Source License", Apache 2.0 수정판(`LICENSE:1-20`).
  - 상업 사용은 허용한다.
  - "Multi-tenant deployment: You may not deploy or operate a multi-tenant environment based on the Jonex source code without prior explicit written authorization", "each tenant corresponds to an independent workspace"(1a).
  - 프런트엔드 로고·저작권 표시를 지우면 안 된다(1b). 다만 정의된 경로 "`web/` directory"는 레포에 없고 실제 경로는 `frontends/`다.
  - 기여 코드는 프로젝트 소유자가 라이선스를 바꿀 수 있고 상업적으로 쓸 수 있다(2a, 2b).
  - GitHub API는 `NOASSERTION`으로 표시한다(`gh api repos/yuezhiai/jonex`).
- `Reference/OpenKB`는 Apache-2.0 원문을 보존한다(`Reference/OpenKB/LICENSE`).
- `Reference/JonexWiki`에는 LICENSE 파일이 없고 `THIRD_PARTY_NOTICES.md`에도 없다. `pyproject.toml`에도 license 필드가 없다. [추정] Jonex 자체 코드라 본체 라이선스를 따른다(사례: 서드파티 고지 목록에 LightRAG·RAG-Anything·OpenKB 셋만 있고 JonexWiki가 빠진 것 1건, 첫 커밋 `a8bee87`의 작성자가 본체 기여자 `sdhazwhy`인 것 1건).

## 5. 엔터프라이즈 기능

### 5.1 테넌트 격리

- 원칙: "所有业务数据必须有合法 `tenant_id`", "禁止租户：空字符串、`default`…", "Sidecar `/invoke` body 中的 `tenant_id` 只允许作为一致性校验，不是新的租户来源"(`jonex-platform-architecture.md:437-447`). 서비스와 레포지토리는 `require_tenant()`로 막는다.
- wiki 저장소 격리는 경로와 키로 한다.
  - openkb: `{tenant}__{kb}` 디렉터리(`openkb_adapter.py:123-125`).
  - jonex_wiki: `{root}/{tenant}/{kb}`(`layout.py:47-48`), DB 행은 `(tenant_id, kb_id)`.
- 플랫폼 관리자 테넌트가 코드에 `PLATFORM_ADMIN_TENANT_IDS = frozenset({"tenant_jonex_demo"})`로 박혀 있다(`jonex_core/security/permission.py:20`).

### 5.2 권한(RBAC + 자원 신분)

- 권한 코드: `platform.user_roles → role_permissions → permissions`. Redis에 30초 캐시하고, Redis가 실패하면 DB를 바로 본다(`permission.py:45-96`).
- 공간 신분: `space_manager | member`(`space_permission_service.py:24-31`). KB 신분: `kb_manager | member`(`kb_permission_service.py:26-30`).
  - "**写权限与人员管理权限都只属于 kb_manager，member 只读**"(쓰기와 사람 관리는 kb_manager만, member는 읽기만)(kb_permission_service.py:7-12).
  - 옛 값(editor/viewer)은 권한 없음으로 판정한다(36-38).
- 동작별 묶음(`capabilities/knowledge_base/capability.py:313-405`):
  - 쓰기(`_SPACE_WRITE_ACTIONS`): 업로드·삭제·재파싱, LLM-Wiki Schema 저장·apply·import·전체 재컴파일, 목차 draft/adjust, 컴파일 일시정지·재개. "LLM 调用有成本，按写口径"(LLM 비용이 드니 쓰기로 친다, 358행). 공간 manager나 KB kb_manager만 할 수 있다.
  - 읽기(`_SPACE_READ_ACTIONS`): wiki 페이지·목록·목차·역링크·claims·schema 보기. 공간 member도 볼 수 있다.
  - KB 탐색 5종은 KB 구성원으로 좁혔다(`_KB_MEMBER_READ_ACTIONS`, 377-381). schema·wiki 읽기는 "既是管理页 tab、又被检索增强复用的读 action，收紧它们会牵连检索体验，本批不动"(관리 탭이면서 검색에도 쓰여 좁히지 않았다, 371-373)이다.
- 공간 판정 건너뛰기: "无 user_id / "anonymous"（测试 token、内部链路）或 MCP Key 认证 → 不走空间判定"(`capability.py:1456-1463`). MCP 키는 자체 범위(`write_grants`, 서비스 범위)로 막는다(`mcp_server/tools.py:223-300`).
- **문서 수준 접근 제어는 없다.** 권한 표는 `space_permissions`, `kb_permissions` 둘뿐이다(`004_knowledge_base.sql:31-66`). grep(`document_permission|doc_permission|folder_permission`)으로 0건이다. KB를 볼 수 있으면 그 KB wiki 페이지 전부를 볼 수 있다. openkb `read_page`는 일부러 문서 귀속을 검사하지 않는다(`openkb_adapter.py:594-595`).

### 5.3 감사

- `platform.audit_logs`(`deploy/postgres/migrations/002_platform.sql:224-254`) 열: tenant_id, user_id, username, ip, action, resource, resource_id, status_code, duration_ms, request_params, response_body, error_stack, trace_id, log_type(OPERATION/TASK/SECURITY), service_name, outcome, log_level, error_message, method, path.
- 남기는 길은 둘이다.
  - ① 서비스 코드의 `schedule_emit`: 막지 않고 예외를 삼킨다(`jonex_core/common/audit.py:168-195`). platform 밖 컨테이너는 `AUDIT_INGEST_URL`로 넘긴다(31-50).
  - ② Sidecar `AuditForwarder`: 쓰기 HTTP 메서드와 키워드에 맞는 invoke action을 모아 platform으로 보낸다(`jonex_core/sidecar/hooks.py:190-236`).
- wiki 관련 action은 자원 유형 `compiled_schema`로 묶인다(`jonex_core/common/audit_enums.py:469-476`).
- schema 행 자체에 `edited_by`와 판 이력(archived 행)이 남는다(`llm_wiki_schema_service.py:331-338`).
- **wiki 페이지 단위로 "누가 언제 무엇을 바꿨는지"는 남지 않는다.** 페이지는 LLM이 쓰고, 사람이 페이지를 고치는 API는 찾지 못했다(라우트 목록 `api_gateway/routes/knowledge_base.py:1383-1520`에 쓰기 API는 목차 draft/adjust와 일시정지·재개뿐이다).

### 5.4 계량 · 쿼터 · 피드백

- LLM 사용량: 게이트웨이가 테넌트·사용자·장면·KB·문서·trace로 기록한다. 같은 호출을 재시도하면 `request_id = trace|scene|model|body` 해시로 중복을 막는다(`llm_gateway/context.py:53-83`). 게이트웨이 쿼터 훅은 "TODO(G5a) … 默认放行"(아직 비어 있고 기본 통과)이다(`llm_gateway/router.py:29-35`).
- 게이트웨이 인증: `LLMGW_INTERNAL_TOKENS`가 비면 빈 토큰이 아닌 아무 토큰이나 통과한다(`llm_gateway/auth.py:36-43`의 조건 `valid_tokens and incoming not in valid_tokens`).
- 문서 쿼터: KB별 문서 수, 테넌트 문서 수, 테넌트 용량을 advisory lock으로 원자적으로 센다(`quota_service.py:1-13`).
- 답 피드백(좋아요·싫어요·사유)을 저장한다(`answer_feedback_service.py:1-30`). 컴파일 쪽으로 되돌아가는 고리는 없다(grep `feedback`을 wiki 서비스·어댑터에 돌려 0건).

### 5.5 인증

- Keycloak OIDC RS256 검증. issuer는 화이트리스트에서만 받는다(`jonex_core/security/oidc.py:1-30`). 테넌트마다 realm을 둔다(`2c8527d` "Keycloak OIDC single sign-on with per-tenant realms").
- 외부 신원 동기화(`1df2031`), 로그인 잠금·세션 시한(`a8eb6f6` 15번 항목).

## 6. 설계 결정과 이유

표기: (a) 작성자가 밝힌 이유, (b) 추론한 이유. 공개 이력이 squash된 큰 커밋 몇 개뿐이라(`f6205dc` "Squashed several dozen commits", `41e1ff3`·`a8eb6f6`·`36f8e05`는 번호 매긴 변경 목록) 이유는 주로 코드 주석에서 나온다. 주석이 가리키는 설계 문서(`docs/llmwiki-schema-settings-execution-plan.md`, `docs/jonex_wiki/*.md`, `docs/openkb/llmwiki-reasoning/*.md`, `docs/permissions/PERMISSIONS_REDESIGN.md`)는 공개본에 없다(`find docs -type f`는 6개 파일만 보인다). 공개본에 없는 이유는 `CHANGELOG.md:20-22` "Internal planning documents … removed from the public source tree"다.

D1. **KB 종류를 셋으로 두고 KB 단위로 배타적이며 생성 뒤 바꿀 수 없게 했다.**
- (a) "改类型意味着旧数据全部失效（openkb→lightrag 要清空 Wiki 重推 LightRAG；lightrag→openkb 要清空 Neo4j 重编译），没有安全的原地切换路径"(종류를 바꾸면 기존 데이터가 모두 무효가 되고 안전한 제자리 전환 경로가 없다) — `knowledge_info_service.py:439-442`.
- 대안: 한 KB에서 그래프와 wiki를 둘 다 만든다. 이력: 공개 이력에는 처음부터 이 모양이다(`f6205dc`).

D2. **"코드가 아는 종류 / wiki 의미 종류 / 이 배포가 만들 수 있는 종류"를 세 집합으로 나눴다.**
- (a) "混了会出两类错：把 lightrag 放进 llm-wiki 语义、或把「运维配置禁用」误报成「调用方拼错」"(섞으면 두 종류의 오류가 난다) — `kb_type_service.py:7-18`.
- 생성 화이트리스트(`KB_ENABLED_TYPES`)는 "只作用于「创建」一个动作 … 也**不隐藏存量库**"(생성 하나에만 걸리고 기존 KB를 숨기지 않는다)이다(16-18).

D3. **잘못된 `KB_ENABLED_TYPES` 값은 서비스 시작을 실패시킨다.**
- (a) "静默丢一半的失败方式最难查：客户现场少显示一个选项，没人知道为什么"(조용히 반만 버리는 실패가 가장 찾기 어렵다) — `kb_type_service.py:55-58`, `.env.example:965-968`. 대안은 유효한 값만 쓰는 것이다.

D4. **엄격판 `get_kb_type_or_none`을 따로 둬서 종류를 못 찾았을 때 lightrag로 떨어지지 않게 했다.**
- (a) "wiki 类文档的 `ontology_status` 被上传路径写成 `READY` —— … 一份 wiki 文档会落进 lightrag 那条分支、被当场判成「编译成功」，而 Wiki 根本没生成"(wiki 문서가 lightrag 분기로 빠져 컴파일 성공으로 판정됐지만 Wiki는 생성되지 않았다) — `kb_type_service.py:148-156`. 이력: "2026-10-09 加"(같은 주석).

D5. **입력 백엔드를 제출할 때 정해 문서 행에 고정하고, 조회 쪽은 그 값만 읽는다.**
- (a) "查询侧各读一次环境变量的写法，会在翻转那一刻把在途文档永远卡在 PARSING"(조회 때마다 환경변수를 읽으면 스위치를 바꾸는 순간 진행 중 문서가 PARSING에 영원히 갇힌다) — `ingest_backend.py:7-10`. KB 단위 값은 `update/045` 머리말이 "入库链路由全局 env 单选，无法按库区分"(전역 스위치 하나라 KB별로 나눌 수 없었다)이라고 적는다. 이력 `d4ec3fb`(2026-10-09).

D6. **wiki 엔진을 플랫폼 프로세스 밖 별도 컨테이너에 두고 Sidecar `/invoke` 능력으로 부른다.**
- (a) 의존성 충돌: "不要 pip install -r requirements.txt（根 requirements.txt 含 pydantic<2，会与 OpenKB 的 openai-agents / litellm 冲突降级）"(루트 requirements는 pydantic<2라 OpenKB 의존성과 충돌한다) — `deploy/docker/openkb-source.Dockerfile:44`.
- (b) [추정] 엔진을 바꾸거나 늘리기 쉬운 seam을 노렸다(사례: 두 엔진이 같은 클라이언트 인터페이스와 같은 `list_graph`·`list_wiki_contents` 계약을 지키는 것 2건 — `openkb/client.py:12-53`, `jonex_wiki/client.py:9-80`).

D7. **jonex_wiki는 별도 HTTP 서비스 대신 능력 프로세스 안에서 엔진을 import한다(B1).**
- (a) "B1 单容器：与 OpenKB 一致，进程内 `import jonex_wiki` 直接调 `WikiApplication`，不经 FastAPI 路由 / HTTP 转调；引擎与能力共享同一 pydantic v2 进程"(OpenKB와 같게 같은 프로세스에서 부르고 HTTP 재전달을 없앴다) — `jonex_wiki_adapter.py:196-202`.
- 이력: client 주석이 "原 JonexWikiEngineClient 已移除"(옛 엔진 HTTP 클라이언트를 없앴다)라고 적는다(`jonex_wiki/client.py:3-5`). 공개 이력에는 최종본 한 커밋(`a8bee87`)만 있다.

D8. **OpenKB를 레포 안에 복사(vendoring)해 그 자리에서 고치고, 변경을 `[jonex]` 표시와 `JONEX_CHANGES.md`로 추적한다.**
- (a) "便于后续升级 OpenKB 时快速定位、重新 apply"(나중에 OpenKB를 올릴 때 빨리 찾아 다시 적용하려고) — `JONEX_CHANGES.md:3-4`. "上游不是本仓的 remote，没有可比的基线"(업스트림이 remote가 아니라 비교 기준이 없다, 228).
- 대안: fork나 패치 파일. 지켜지지 않은 곳은 4.2의 `schema.py`다.

D9. **OpenKB의 변환기·색인기·PageIndex를 건너뛰고 Jonex 파싱 결과를 `compile_short_doc`에 바로 넣는다.**
- (a) "以 document_id 为稳定键；重复提交是 update/overwrite … 不经过 converter/indexer，不触发 PageIndex"(document_id를 안정 키로 쓰고 다시 내면 덮어쓴다) — `openkb_adapter.py:940-944`. "语义是「以 Jonex parsed artifact 为权威源重编译 Wiki」"(Jonex 파싱 결과를 권위 있는 원본으로 삼는다) — `openkb_service.py:133-137`.
- (b) [추정] 파서를 MinerU 하나로 통일해 표·이미지·영상 처리를 세 종류가 공유하려 했다(사례: 세 종류 모두 atomic-rag를 parse 단계로 쓰는 편성 표 1건, `task_runner_service.py:32-36`).

D10. **컴파일을 task로 만들었다. 제출하면 곧바로 task_id를 돌려주고, 30초 순찰이 종단 상태를 회수한다.**
- (a) "终态（compiled/failed）由 patrol_openkb_compile 轮询任务状态回写，sidecar 同步超时不再能打断编译"(종단 상태는 순찰이 쓰고, 이제 sidecar 동기 시한이 컴파일을 끊지 못한다) — `reconciliation_service.py:2523-2525`.
- handler가 기다리지 않는 이유는 (a) "handler 里等它跑完会占着派活请求不放 … 超时就被判 `DELIVERY_UNKNOWN` → 重发 → 同一个 `execution_id` 被调三次"(기다리면 배달 불명으로 판정돼 같은 실행이 세 번 불린다) — `task_runner_service.py:101-108`.

D11. **동기 litellm 컴파일을 `asyncio.to_thread`의 별도 이벤트 루프에서 돌린다.**
- (a) "直接 await 会阻塞主事件循环 → 编译期间的提交/查询请求全部排队 → sidecar 120s 代理超时 500"(바로 await하면 메인 루프가 막혀 컴파일 중 요청이 모두 줄 서고 120초 시한에 500이 난다) — `openkb_adapter.py:444-448`.

D12. **KB별 mutation 락 하나로 compile/remove/delete/recompile/apply를 줄 세운다.**
- (a) "kb_ingest_lock（openkb.locks）的重入判定是线程级，asyncio 同线程并发下不互斥"(OpenKB 파일 락은 스레드 단위라 같은 스레드 안의 asyncio 동시 실행을 막지 못한다) — `openkb_adapter.py:52-55`.
- apply도 같은 락이어야 하는 이유는 (a) "新建第二个锁字典会绕过 §6 的版本 fencing"(두 번째 락을 만들면 판 펜싱을 우회한다) — 293-295.

D13. **엔진 재시작 때 진행 중이던 task를 실패로 판정한다.**
- (a) "启动时扫描各 KB tasks/，把 pending/running 判死（容器重启恢复）" — `openkb_adapter.py:222-225`.
- (b) [추정] task가 프로세스 메모리의 asyncio task라 재시작하면 되살릴 수 없다(사례: `_pending_compile_tasks` 모듈 집합 1건, 59-60).

D14. **LLM-Wiki Schema의 권위 원본을 플랫폼 DB에 두고 판을 매겨 엔진으로 투영한다(CAS 저장, archived 이력, sync_status 분리).**
- (a) "留档模型：每次保存递增 schema_version，旧 active 行转 archived … sync_status 与 status 分开"(저장할 때마다 판을 올리고 옛 행을 보관한다) — `models/llm_wiki_schema.py:6-9`.
- 펜싱 두 겹의 이유는 (a) "防线②：执行开始时再核对磁盘 jonex_schema.json 版本——防 submit 与执行之间 schema 又变了"(제출과 실행 사이에 schema가 바뀌는 것을 막는다) — `openkb_adapter.py:419-421`.
- 이력: `41e1ff3` 11번 항목 "OpenKB/LLM-Wiki schema — compile settings & version fencing".

D15. **AGENTS.md 렌더링을 플랫폼 쪽에서 하려고 OpenKB AGENTS_MD를 복사해 둔다.**
- (a) "knowledge-base-service 容器无法 import vendored OpenKB 源码（跨容器），render 在 KB 侧执行需要本快照"(KB 서비스 컨테이너는 OpenKB를 import할 수 없다) — `llm_wiki_schema_service.py:31-35`. 대가: 두 벌을 손으로 맞춰야 한다.

D16. **엔티티 type code를 소문자 ASCII로 강제하고 `other`를 필수로 둔다. 개념 종류는 안내만 한다.**
- (a) "`resolve_entity_types` 对畸形词表静默回落 DEFAULT_ENTITY_TYPES（仅 warning）——Jonex 侧保存时必须显式拒绝"(OpenKB는 잘못된 목록을 조용히 기본값으로 되돌리므로 저장할 때 막아야 한다) — `dtos/llm_wiki_schema.py:4-6`.
- `other`는 "兜底类型"(받침 종류) — `llm_wiki_schema_service.py:296-298`.
- 개념 종류는 "OpenKB 代码不消费该词表；仅渲染进 AGENTS.md 作分类引导" — `dtos/llm_wiki_schema.py:59-60`.

D17. **기본 추가 규칙을 "软约束"(부드러운 제약)으로 둔다: 문서당 개념 8개, 엔티티 15개 상한, wikilink 필수.**
- (a) "以下规则由模型自觉遵循，非硬性限制" — `dtos/llm_wiki_schema.py:31-38`.

D18. **jonex_wiki는 사용자에게 `compile_main` 접미사 하나만 연다.**
- (a) "唯一开放的是 compile_main（固定骨架 + 用户「编译偏好」suffix）。其余 18 个全是引擎正确性约束，冻结在 Layer 2 … 仅消除「暴露但不生效」的入口"(나머지는 엔진 정확성 제약이라 얼렸다) — `Reference/JonexWiki/src/jonex_wiki/domain/prompts.py:18-26`.
- 플랫폼 쪽: "固定骨架 COMPILE_MAIN_SKELETON（路径/证据/JSON 输出硬约束，代码维护、不可改）+ 用户 suffix" — `llm_wiki_schema_service.py:158-161`.
- 이력: jonex_wiki KB의 schema 행이 openkb 내용으로 잘못 쓰인 적이 있다. `update/001_repair_jonex_wiki_schema.sql` 머리말은 "早期创建的 jonex_wiki KB 因 _create_default 未正确按 kb_type 分流"(초기 생성 때 종류별로 나누지 않았다)라고 적는다.

D19. **모델 이름을 KB config.yaml에 드러나게 적고, 게이트웨이의 숨은 별칭 재작성을 없애고, 없으면 크게 실패한다.**
- (a) "这层隐藏改写有两个问题：① 模型名在 KB 的 `config.yaml` 里看不出真实值，不可审计；② 排查「模型名对不上」要跨三层"(숨은 재작성은 감사할 수 없고 문제를 찾을 때 세 층을 넘나들어야 한다) — `JONEX_CHANGES.md:127`. `jonex_core/llm_gateway/upstream.py:26-43`에도 같은 이유가 있다.
- `DEFAULT_LLM_MODEL`로 떨어지지 않게 한 이유는 (a) "那条回落**只会把「没配」这个一眼能看懂的错误，换成一个看不懂的上游错误**"(대체 경로는 바로 알아볼 오류를 알아보기 어려운 상위 오류로 바꿀 뿐이다) — `JONEX_CHANGES.md:193`.
- 이력: `5fb1feb`(2026-10-08). 같은 날 §七을 §九가 뒤집었다(`JONEX_CHANGES.md:100-105`). 이슈 #34(2026-09-15)는 별칭 재작성이 응답과 계량 기록의 모델 이름을 바꾼다고 지적했다. 이 이슈가 삭제를 이끌었다는 직접 연결 기록은 없다.

D20. **생성 언어를 "원문과 같은 언어"로 바꿨다.**
- (a) "不再依赖 config.yaml 的 `language` 字段。原文中文→输出中文，原文英文→输出英文" — `JONEX_CHANGES.md:67`(2026-08-10).
- (b) [추정] 중국어·영어가 섞인 기업 문서를 하나의 KB에 넣었다(사례: 기본 schema `language="zh-CN"`인데도 이렇게 바꾼 것 1건, `llm_wiki_schema_service.py:245, 251`).

D21. **AGENTS.md에 중국어 "출력 요구(최우선)" 블록을 넣었다. 질의 결과의 실제 값만 내고 출처·설명·괄호를 넣지 말라는 내용이다.**
- 모르는 것: 이유가 커밋(`41e1ff3`)·주석·문서에 없다.
- (b) [추정] 짧은 정답을 요구하는 내부 질의응답 평가에 맞추려 했다(사례: 예시 2개가 "七月份的最佳投资公司 → 张三投资有限公司", "1+1 → 2"로 평가 문항 꼴인 것 1건, `Reference/OpenKB/openkb/schema.py:61-75`).
- 부작용: 이 블록이 컴파일 시스템 프롬프트에도 들어간다(`compiler.py:53-56, 2225-2234`). 질의 에이전트 지시 "Synthesize a clear, concise, well-cited answer"(`query.py:51`)와도 부딪친다.

D22. **openkb `read_page`는 문서 귀속을 검사하지 않는다.**
- (a) "wikilink 天然跨文档，从文档 A 的正文可跳到文档 B 贡献的实体页。这是设计，不是漏洞"(wikilink는 원래 문서를 넘나든다) — `openkb_adapter.py:594-595`.

D23. **그래프에서 요약 페이지를 뺀다.**
- (a) "若摘要页混入 entities，entity_count 会按文档数虚高 … 且摘要页正文挂满全文档 wikilink，关系数跳变"(요약 페이지가 섞이면 엔티티 수가 문서 수만큼 부풀고 관계 수가 튄다) — `openkb_adapter.py:846-851`. jonex_wiki도 같은 규칙을 따른다(`jonex_wiki_adapter.py:484-485`).

D24. **jonex_wiki 컴파일을 문서별이 아니라 KB 단위 묶음으로 한다. 업로드 창이 조용해질 때(파싱 중 문서 없음 + 5초)까지 기다린다.**
- (a) "Parsing success is not a KB-wide batch-complete signal" — `reconciliation_service.py:2616-2618`. "Drain each ready KB in one engine invocation" — 3057.
- (b) [추정] 엔진의 배치·같은 대상 판정이 여러 문서를 함께 볼 때 더 낫고, 엔진이 KB당 "실행 1 + 대기 1"만 허락해서 문서마다 내면 충돌이 잦았다(사례: 유일 인덱스를 `uq_tasks_running_compile`에서 `uq_tasks_queued_compile`로 넓힌 이력 1건, `reconciliation_service.py:61-68`, 엔진 마이그레이션 0006 2026-09-24. KB 바쁨을 stale로 되돌리는 처리 2곳).
- 대안: openkb처럼 문서마다 낸다. 5초라는 값의 이유는 적혀 있지 않다.

D25. **jonex_wiki "KB 바쁨"을 실패가 아니라 stale로 되돌린다.**
- (a) "「KB 忙」不是真失败 … 否则文档会永久停在 failed（巡检只捞 compiling，不会自愈）"(KB 바쁨은 진짜 실패가 아니고, failed로 두면 순찰이 되살리지 않는다) — `jonex_wiki_service.py:572-574`.
- 두 인덱스 이름을 모두 보는 이유는 (a) "只认旧名字的话，判据对现网引擎等于失效" — `reconciliation_service.py:67-68`.

D26. **엔진 오류를 문구가 아니라 안정적인 기계 코드로 판정한다.**
- (a) "引擎或适配器一旦做本地化/改词，靠文案分支的自愈就会**静默失效**（变死代码）"(현지화나 문구 수정이 있으면 문구 기반 자가 치유가 조용히 죽는다) — `jonex_wiki_service.py:37-41`, `jonex_wiki/client.py:116-119`.

D27. **같은 이름 고아 문서의 자가 치유는 플랫폼 자신의 soft-delete 기록으로만 판단한다.**
- (a) "「本 KB 内已软删的同名文档」就是孤儿的唯一合法来源。全程不读引擎报错文案" — `jonex_wiki_service.py:151-154`.
- 원인 기록: `document_service.delete_document`가 엔진 삭제 예외를 warning으로 삼키고 플랫폼 행은 지운다(같은 주석 143-150, 실제 코드 `document_service.py:2416-2422`).

D28. **jonex_wiki 엔진의 상태어와 페이지 종류를 OpenKB 어휘로 바꿔 내보낸다.**
- (a) "不归一化会让「编译成功(done)」永远卡在 llm_wiki_compile_status=compiling" — `jonex_wiki_adapter.py:21-24`. "前端 WikiPageBrowser 只认 summaries/concepts/entities 三类 section" — 30-31.
- (b) [추정] 화면·순찰·검색 코드를 openkb 하나에 맞춰 두고 새 엔진을 그 계약 뒤에 끼웠다(사례: 순찰 함수가 "仅替换 client 为 JonexWikiService + kb_type 过滤"인 것 1건, `reconciliation_service.py:2794-2798`, 서비스 docstring "与 OpenKB 镜像" 1건, `jonex_wiki_service.py:5`).

D29. **jonex_wiki citation은 trace 요청 여부와 관계없이 늘 돌려준다.**
- (a) "引用是答案的证据，不是调试信息" — `jonex_wiki_adapter.py:359-360`.

D30. **openkb 출처를 에이전트 탐색 궤적에서 거꾸로 찾고, 개념·엔티티 페이지도 frontmatter sources로 문서에 연결한다(방안 B).**
- (a) "A 把「页面本身不是用户上传的文档」误当成「页面无法定位到文档」 … 概念性提问下 agent 往往只读 concepts/，A 会导致引用为零条——实测如此"(개념 질문에서는 에이전트가 concepts만 읽어 방안 A는 출처가 0이 됐다) — `search_service.py:7168-7171`.

D31. **openkb 답의 인용 표시를 LLM이 나중에 끼운다.**
- (a) "用于 openkb（llm-wiki）这类「答案无 [n]/[E#] 内联标记」的管线 … 锚定素材是文档名 + 知识库名（openkb 引用为文档级，无 excerpt）" — `ontology_llm.py:778-783`.
- 걸리는 점: 근거 대조 없이 문서 이름만 보고 붙인다.

D32. **여러 KB 질의는 KB별로 답을 내고 상위 N개를 LLM이 융합한다. 융합 프롬프트에는 KB 표시 이름만 준다.**
- (a) "此前 json.dumps(per_kb) 会把 kb_id（UUID 不可读）和内部 source 字段 … 直接暴露给 LLM，产出「知识库 `llm-wiki`」… 这类错误标注" — `ontology_llm.py:720-723`.

D33. **문서 0개인 KB는 엔진을 부르지 않는다.**
- (a) "空库没有 wiki 产物，agent 会反复读页直到 MaxTurnsExceeded，误报成「引擎异常」" — `search_service.py:7662-7663`.

D34. **읽기 목차를 플랫폼 DB에서 엔진으로 옮겼다.**
- (a) "目录功能（LLM 起草/调整/存储/自动触发）已整体下沉到 jonex_wiki 引擎 … 本迁移 DROP 平台旧表" — `deploy/postgres/update/033_drop_wiki_outline.sql` 머리말. 목차는 "纯展示投影 … 不参与检索" — `update/032_wiki_outline.sql`.
- 이력: 032에서 표를 만들고 033에서 지웠다. 프런트 주석은 아직 옛 표를 가리킨다(`frontends/core-business/src/pages/DomainKnowledgeCompileResults/wiki/WikiReaderShell.tsx:5`).

D35. **KB 권한을 두 단계(kb_manager/member)로 줄였다. 쓰기와 사람 관리를 한데 묶었다.**
- (a) "两级模型下没有「能写但不能管人」这一档 —— 这是 D1 的取舍：存量 editor 按 E4 全量升为 kb_manager（保住写权限，代价是额外获得管人能力）" — `kb_permission_service.py:7-12`.
- 모르는 값은 권한 없음으로 판정하는 이유는 (a) "把 editor 当成 kb_manager 会让「迁移没跑」变成一次静默提权" — 36-38. 이력: `41e1ff3`(viewer/editor 덧붙임 권한)에서 현재 두 단계로 왔다(`a8eb6f6` 17번 항목).

D36. **테넌트 관리자 표지를 `tenant:write`에서 `tenant:admin`으로 바꿨다.**
- (a) "tenant:write 语义过载（既是租户 CRUD 又是"全租户知识库超级开关"）" — `space_permission_service.py:34-37`.

D37. **schema·wiki 읽기 action은 KB 구성원으로 좁히지 않았다.**
- (a) "收紧它们会牵连检索体验，本批不动，留待业务确认" — `capability.py:373`.

D38. **목차 draft/adjust와 컴파일 일시정지를 쓰기 권한으로 둔다.**
- (a) "LLM 调用有成本，按写口径" — `capability.py:358`.

D39. **감사 로그를 막지 않고 실패를 삼킨다.**
- (a) "无论是否存在运行中的事件循环都不会抛异常，避免审计逻辑拖垮业务方法" — `jonex_core/common/audit.py:171-173`.

D40. **OpenKB 내부 LLM 호출에 계량 헤더를 contextvar로 싣는다.**
- (a) "让 OpenKB 内部发起的 LLM 调用带上 `X-Jonex-*` 头，使 llm-gateway 能记录 tenant/kb/doc/scene/trace 维度" — `JONEX_CHANGES.md:16`.

D41. **업로드 때 storage_key의 테넌트 구간을 fail-closed로 검사한다.**
- (a) "防止构造他租户的 storage_key 触发 RAG 解析造成跨租户数据泄露" — `document_service.py:433-436`.

D42. **업로드 때 같은 KB 안 md5 중복을 거부한다. hash를 못 구하면 통과시킨다.**
- (a) "fail-open：hash 取不到 → 放行，不因临时存储错误阻塞上传" — `document_service.py:510-511`.

D43. **llm-wiki 업로드는 ontology compiled schema 계산을 건너뛴다.**
- (a) "`auto_compile=True` 有副作用（凭空生成一份 ontology schema）" — `document_service.py:615-619`.

D44. **체인에서 온 컴파일은 바쁨 검사를 건너뛴다.**
- (a) "看门狗是「先上报、后把文档置 READY」… 那一刻文档行可能还停在 `parsing`，忙校验会把一个其实已经解析成功的活**当场拒掉**" — `openkb_service.py:209-213`.

D45. **claim할 때 옛 task_id·error·warnings를 지운다.**
- (a) "残留的旧 task_id 会让 patrol 读到旧任务 completed 而误回写 compiled" — `openkb_service.py:303-305`.

D46. **failed 상태에서는 warnings를 남긴다.**
- (a) "保留 warnings 不动（旧警告仍有诊断价值）" — `openkb_service.py:416`.

D47. **jonex_wiki 순찰은 커서로 창을 돌린다.**
- (a) "排队/暂停任务可能长期不退出 compiling；轮转扫描避免它们一直占满窗口" — `reconciliation_service.py:2825`.

D48. **rag 편성을 세 단계에서 두 단계로 합쳤다.**
- (a) "那两步拆的是**本来就在同一个引擎调用里**的事 … 拆开只为了任务中心多显示一行" — `task_runner_service.py:42-46`(2026-09-29).
- wiki 두 종류는 처음부터 두 단계로 같은 틀을 쓴다.

D49. **jonex_wiki 목록 응답에서 아무도 쓰지 않는 필드를 뺐다.**
- (a) "实测 6 文档的库响应体 1.6MB，其中一半是那份重复、另一半大部分是这些无人消费的字段" — `jonex_wiki_adapter.py:410-419`.
- `view=counts`는 "50 文档的库传 4.75MB（约 3.5s）" 때문에 만들었다(461-464).

D50. **openkb 모델 이름에 provider 접두사를 붙인다.**
- (a) "litellm 需要 `openai/<model>` 形式才能确定 provider，否则报 "LLM Provider NOT provided"" — `openkb_adapter.py:900-903`.

## 7. 앞선 schema-glossary 보고서와 어긋나거나 보태는 점

대상: `lab/reports/schema-glossary/yuezhiai-jonex.md`(같은 commit).

1. 보태기: 앞선 보고서는 openkb LLM-Wiki Schema를 "엔티티 종류 통제 어휘·개념 종류·AGENTS.md 추가 규칙"으로만 설명했다(9, 47행). 실제 AGENTS.md에는 Jonex가 표시 없이 넣은 중국어 "输出要求" 블록이 고정으로 들어간다(`Reference/OpenKB/openkb/schema.py:61-75`, 플랫폼 복사본 `llm_wiki_schema_service.py:82-96`). 사용자가 편집 화면에서 지울 수 없고, 컴파일 프롬프트와 질의 프롬프트에 모두 들어간다. schema 관점에서 빠진 사실이다.
2. 정정에 가까운 보태기: 앞선 보고서는 OpenKB를 "OpenKB(Apache 2.0)"로만 적었다(152, 159행). vendored 판은 고지된 0.4.5 태그가 아니라 업스트림 main(ff54396)에 가깝다(4.1).
3. 보태기: 앞선 보고서는 "두 길은 KB 단위로 서로 배타적"이라고 했다(7행). 이 배타성은 생성 뒤 종류를 바꿀 수 없다는 규칙으로 굳어 있다(`knowledge_info_service.py:439-452`). 종류를 가로지르는 연결은 질의 때 LLM 답 융합뿐이다. wiki 페이지나 그래프 수준의 KB 간 연결은 없다.
4. 보태기: 앞선 보고서 C절은 jonex_wiki의 문자 구간 출처를 적었다. openkb 쪽 출처는 **문서 단위**다. 에이전트가 읽은 페이지 경로로 문서를 찾고, 답에는 LLM이 문서 이름만 보고 `[n]`을 끼운다(D30, D31). 청크나 claim 수준의 근거 대조는 없다.
5. 보태기: 앞선 보고서 D절은 openkb의 새/기존 연결을 다루지 않았다. openkb는 기존 개념·엔티티의 한 줄 요약 목록 **전체**를 계획 프롬프트에 넣고 LLM이 create/update/related를 고른다(`compiler.py:90-127, 727-757`). 결정적 대조(이름·별칭 키)는 없다. 이슈 #22는 같은 문서를 재컴파일하면 `concepts/attention-mechanism-2.md` 같은 중복 개념 페이지가 생긴다고 보고했다(2026-09-14, 열림).
6. 일치 확인: 앞선 보고서의 "jonex_wiki는 종류 목록이 없다. 편집 선호 문구만 있다 — `llm_wiki_schema_service.py:237-245`"는 코드와 맞는다. 엔진 쪽 이유는 D18이다.
7. 일치 확인: 앞선 보고서의 라이선스 요약은 맞다. 다만 1b의 `web/` 경로가 레포에 없다는 점을 보탠다.

## 8. 엔터프라이즈 다중 작성자 보고서 용도에 비춰

용도 조건: 작성자마다 같은 대상을 다른 용어로 쓴다. 형식 없는 문서가 섞인다. 여러 사람이 쓴다. 권한이 필요하다.

### 8.1 쓸 만한 장치

- **schema를 DB에 두고 판을 매겨 엔진에 투영하는 틀**(D14): 사람이 고치는 설정(종류 목록, 규칙)을 판·편집자·CAS·이력과 함께 저장한다. 문서마다 "어느 판으로 컴파일됐나"(`target`/`applied`)를 기록하고, 판이 낡은 문서만 골라 다시 컴파일한다. 용어집을 고칠 때마다 영향 받는 문서를 추적하는 데 그대로 쓸 수 있다.
- **펜싱 두 겹**(제출 때 판을 묶고 실행 때 디스크 판과 비교): 설정이 바뀌는 중간에 낡은 설정으로 컴파일된 결과가 "성공"으로 기록되는 것을 막는다.
- **KB 단위 직렬화 + task 파일 + 30초 순찰 회수 + 재시작 때 실패 판정**: LLM 컴파일처럼 길고 실패하기 쉬운 일을 HTTP 시한과 떼어 놓는 패턴이다. 여러 사람이 동시에 올려도 같은 wiki 디렉터리를 동시에 쓰지 않는다.
- **업로드 창 묶음 컴파일**(D24): 여러 사람이 한꺼번에 올린 보고서를 한 번에 엔진에 넣어 문서 사이 연결을 함께 판단하게 한다. "새 데이터와 기존 데이터의 연결고리"를 찾으려면 문서별 증분보다 이쪽이 유리할 수 있다. 판단 근거는 엔진 갈래 결과로 확인해야 한다.
- **재파싱 세대(`content_generation`)와 stale 표시**: 원문이 바뀌면 옛 wiki를 stale로 두고 다시 컴파일한다. 화면에도 낡았다는 것이 보인다.
- **원문 산출물을 권위 원본으로 두고 wiki는 다시 만들 수 있는 파생물로 취급**(D9): raw를 다시 연결할 수 있는 구조라는 사용자 목표와 맞는다.
- **페이지 수준 references, claim 감사 표, 역링크**(jonex_wiki 화면): 사람이 결론에서 원문으로 돌아가 확인하는 길이다. 사람이 품질을 보증하는 데 바로 쓸 수 있는 화면 계약이다.
- **엔진 교체 seam**: 같은 클라이언트 인터페이스와 같은 그래프·페이지 목록 계약 뒤에 엔진 두 개를 끼웠다(D6, D28). 자체 엔진을 붙일 때 그대로 흉내 낼 만하다.
- **계량 헤더**: 테넌트·KB·문서·장면별 LLM 비용을 남긴다. 부서별 비용 배분에 쓸 수 있다.
- **문구 대신 오류 코드로 분기**(D26), **실패 대신 stale로 되돌리기**(D25): 운영 안정성 원칙으로 가져올 만하다.

### 8.2 걸리는 점

- **용어 불일치를 처리하는 장치가 llm-wiki 쪽에 없다.** 동의어 묶음은 lightrag(그래프) 종류에만 있다(앞선 보고서 B절). openkb는 LLM이 기존 페이지 요약 목록을 보고 update냐 create냐를 고르는 것뿐이다. jonex_wiki는 결정 규칙이 엔진 안에 있다(앞선 보고서 D절). 두 종류를 한 KB에서 같이 쓸 수 없으므로 용어집을 쓰려면 wiki를 포기해야 한다.
- **openkb 계획 프롬프트는 기존 페이지 요약 목록 전체를 넣는다.** 문서가 쌓이면 프롬프트가 KB 크기에 비례해 커진다. [추정] 수백 개 개념을 넘으면 비용과 판단 품질이 함께 나빠진다(사례: `_read_concept_briefs`가 상한 없이 모든 페이지를 한 줄씩 넣는 코드 1건, `compiler.py:727-757`). 측정값은 없다.
- **작성자 정보가 엔진에 가지 않는다.** 문서 행에 업로더 열이 없고, 엔진 artifact(`{document_id, source_file_path, parsed_markdown_path, …}` / `{source_path, source_name, document_id}`)에도 작성자가 없다. "누가 이 주장을 했나"나 작성자별 용어 차이를 엔진이 쓸 수 없다. 폴더·태그도 컴파일에 가지 않는다.
- **권한이 KB 단위다.** 문서별 접근 제어가 없고 wiki 페이지는 여러 문서를 합쳐 쓴다. 그래서 "일부 보고서만 볼 수 있는 사람"을 표현하려면 KB를 나눠야 한다. KB를 나누면 wiki 연결도 끊긴다(종류를 가로지르는 연결도, KB를 가로지르는 연결도 질의 때 융합뿐이다).
- **사람이 wiki 페이지를 고치는 경로가 없다.** 바꿀 수 있는 것은 schema·접미사·목차뿐이다. "어느 정도 사람이 하더라도"의 사람 개입 지점이 설정 수준에 머문다. 페이지 수정 이력과 감사도 없다.
- **openkb 출처가 약하다.** 문서 단위 출처에 LLM이 나중에 끼우는 `[n]`이라, 문장과 근거가 맞는지 코드로 검사하지 않는다.
- **AGENTS.md에 숨은 출력 규칙**(D21): 사용자 설정과 무관하게 짧은 답을 강제하고 출처 표기를 막는다. 보고서 용도에서는 거꾸로 작동할 수 있다.
- **jonex_wiki 판 추적이 반쯤만 있다.** 순찰은 `applied_schema_version=task.get("wiki_schema_version")`을 넘긴다(`reconciliation_service.py:2897`). 그러나 엔진 코드에는 `wiki_schema_version`이라는 키가 없다(`grep -rn wiki_schema_version Reference/JonexWiki/src` 0건). 어댑터는 엔진 task 사전을 상태어만 바꿔 그대로 넘긴다(`jonex_wiki_adapter.py:133-139, 337-340`). 그래서 `applied_schema_version`이 채워지지 않는다. 값이 None이면 열을 건드리지 않으므로(`reconciliation_service.py:3176-3177`) 오류는 나지 않는다. 또 `recompile_outdated_documents`는 종류와 관계없이 `recompile_openkb`를 부른다(`llm_wiki_schema_service.py:555-563`). jonex_wiki KB에서는 `content.md`가 없어 실패한다. jonex_wiki 화면은 이 버튼을 쓰지 않는다(grep 결과 `LlmWikiSchemaTab.tsx`만 부른다). `only_outdated` 요청 값은 읽기만 하고 쓰지 않는다(530행).
- **라이선스**: 사내에서 여러 workspace(테넌트)를 운영하면 1a의 "multi-tenant deployment" 서면 허가 조항에 걸릴 수 있다. 코드를 가져다 쓰기보다 설계를 참고해 다시 쓰는 편이 안전하다.
- **이유 기록이 공개본에 없다.** 설계 문서(§번호로 가리키는 "方案")가 빠져 있다. 결정의 근거 측정치(예: 5초 창, 1800초 시한, 상위 3개 융합)를 확인할 수 없다.

## 9. 모르는 것

- AGENTS.md "输出要求" 블록을 넣은 이유와 대상. `41e1ff3` 이전 내부 이력이나 빠진 설계 문서를 보면 알 수 있다. 이슈·PR에는 없다(`gh issue list`, `gh pr list` 전체 확인).
- openkb와 jonex_wiki의 관계 계획(대체인지 공존인지). `.env.example:964`의 "新一代"와 "藏掉 Ontology Wiki" 예시가 대체를 암시한다. 결정 문서가 없다. 로드맵이나 메인테이너 답변을 보면 알 수 있다.
- jonex_wiki 업로드 창 5초, 컴파일 시한 1800초, 융합 상위 3개의 근거 측정치. 빠진 `docs/jonex_wiki/*.md`를 보면 알 수 있다.
- 이슈 #22(openkb 재컴파일 때 개념 중복)의 실제 원인. 보고자는 "단독 재컴파일이라 기존 개념을 못 본다"고 추정했다. 그러나 코드는 기존 개념 요약을 읽는다(`compiler.py:727-757`). slug 정규화나 registry 처리 차이일 수 있다. 재현 실행이나 메인테이너 답변을 보면 알 수 있다(현재 답변 없음).
- 옛 경로(`_handle_completed` → `_dispatch_*_compile`, `reconciliation_service.py:1853-1858`)가 세 종류 모두 task center로 옮긴 뒤에도 실제로 타는 경우가 있는지. `task_watch_service.py`와 `reconciliation_service.py:978-1061`의 "被接管的文档不归这两趟管" 조건을 끝까지 따라가면 알 수 있다(task center 갈래).
- jonex_wiki 엔진이 묶음 ingest 안에서 새 문서와 기존 페이지를 어떻게 잇는지, 묶음 크기 상한이 있는지. jonex-wiki 엔진 갈래의 `application.ingest_parsed_documents`와 compile_task를 보면 알 수 있다.
- `Reference/JonexWiki`의 라이선스 확정. 메인테이너에게 묻거나 저장소 정책 문서를 봐야 한다.
- `JONEX_CHANGES.md`가 가리키는 수호 테스트(`tests/unit/test_openkb_*`)가 내부에만 있는지 아예 없는지. 공개 레포에는 없다.
- 사내 단일 회사가 여러 workspace를 운영하는 것이 1a 조항의 "multi-tenant deployment"에 들어가는지. 라이선스 소유자에게 물어야 한다.

## 10. 출처

- 레포 https://github.com/yuezhiai/jonex — `gh api` 기준 stars 1344, 생성 2026-07-19, push 2026-10-10, topics에 `llm-wiki`가 있다. 열린 이슈 34개.
- 커밋: `5571db5`(HEAD), `a8bee87`(jonex-wiki 통합, 2026-10-10), `d4ec3fb`(KB별 입력 백엔드), `9ae7d64`(task center), `5fb1feb`(모델 해석), `41e1ff3`(LLM-Wiki schema·RBAC, AGENTS_MD 출력 규칙), `f6205dc`(OpenKB 처음 등장, squash), `a8eb6f6`, `36f8e05`.
- 이슈: #22(openkb 재컴파일 개념 중복), #34(MODEL_ALIAS_MAP 모델 이름 재작성).
- 업스트림: https://github.com/VectifyAI/OpenKB — 태그 v0.4.5 `ac11840`(2026-07-20), v0.5.0-rc1 `9036c2c`(2026-07-20), main `ff54396`(2026-07-22). diff는 스크래치패드에서만 했다.

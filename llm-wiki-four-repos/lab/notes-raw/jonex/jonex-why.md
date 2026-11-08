# jonex-why — Jonex가 세 엔진을 왜 이렇게 나눴고, JonexWiki 컴파일을 왜 이렇게 짰나

- 대상: yuezhiai/jonex, HEAD `5571db5c682fb3182e968d2e9d34ef415a2638c3`(2026-10-10), 브랜치 `mian`, 커밋 38개.
- 로컬 사본: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-four-repos/lab/repos/yuezhiai_jonex`. 아래 경로는 모두 레포 루트 기준이다.
- 이 갈래(jonex-why)의 몫: 이력과 설계 이유. 핵심 물음 셋을 맡는다.
  1. 왜 OpenKB를 들여오고도 JonexWiki를 따로 만들었나.
  2. 왜 그래프 KB와 wiki KB를 KB 단위로 배타적으로 갈랐나.
  3. 왜 JonexWiki compile 단계가 이런 구성인가.
- 표기: "원문" 뒤 → 한국어 뜻. `[추정]`은 내가 사례에서 끌어낸 판단이다. `모르는 것:`은 근거가 없는 자리다.
- 실행한 것: 읽기 전용 git(`log`, `show`, `log -S`, `log -L`), grep/sed/cat, `python3 -I`로 docstring만 뽑는 ast 파싱, `gh issue/pr/api` 조회, 웹 검색 3회와 arXiv 페이지 읽기 2회. 레포 코드는 실행하지 않았다.

## 0. 한눈 요약

- Jonex는 문서를 KB(지식 베이스) 단위로 세 엔진 중 하나에 보낸다. 엔진은 `lightrag`(그래프 KB, 화면 이름 "Ontology"), `openkb`("Ontology Wiki"), `jonex_wiki`("Jonex Wiki")이다(`capabilities/knowledge_base/services/kb_type_service.py:35-40`, `frontends/core-business/src/locales/zh.json:1523-1528`).
- 세 엔진은 파싱(atomic-rag + MinerU)만 같이 쓴다. 파싱 뒤에는 서로 다른 저장소에 서로 다른 산출물을 만든다. 엔진을 섞는 일은 질의할 때 `search_mix`가 KB별로 나눠 보낸 뒤 답과 인용을 합치는 것뿐이다(`capabilities/knowledge_base/services/search_service.py:8155-8188`).
- 물음 1의 답: 작성자는 이유를 글로 남기지 않았다. 다만 정황이 세 가지로 모인다. 첫째, OpenKB는 처음에 화면에서 "暂不支持引用溯源"(아직 인용 출처 추적을 지원하지 않음)이라고 적혀 나왔다(commit `f6205dc`). 둘째, 나중에 붙인 OpenKB 인용도 문서 단위로 역산한 것이다(`search_service.py:7157-7175`). 셋째, JonexWiki는 Tencent WeChat 팀의 논문 "Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki"(arXiv 2605.25480)의 Algorithm 1과 Error Book을 claim 단위 근거 구간(SourceSpan)과 함께 구현한 별도 엔진이다. 코드 docstring이 "Paper-required behavior"라고 반복해 적는다(아래 #3 J3·J4).
- 물음 2의 답: 작성자가 밝힌 이유는 "kb_type 불변"의 이유뿐이다. "改类型意味着旧数据全部失效 … 没有安全的原地切换路径"(유형을 바꾸면 옛 데이터가 전부 무효가 되고, 안전하게 제자리에서 바꾸는 길이 없다)라고 적혀 있다(`capabilities/knowledge_base/services/knowledge_info_service.py:439-442`). 배타 자체의 이유는 적혀 있지 않다. 유지보수자는 이슈 #31에서 그 대가를 인정했다. "kb_type is immutable after KB creation, and openkb has no LightRAG vector index—what is lost is not just the graph, but vector retrieval itself"(kb_type은 생성 뒤 못 바꾸고, openkb에는 LightRAG 벡터 색인이 없다. 잃는 것은 그래프만이 아니라 벡터 검색 자체다)라는 답이다.
- 물음 3의 답: 작성자가 이유를 적어 두었다. 논문의 원래 방식(legacy)은 passage마다 LLM 한 번에 "어느 페이지에 넣을지"와 "무엇을 말하는지"를 같이 묻는다. JonexWiki는 이를 "이해(understanding) → 조직(organization)" 두 단계로 갈랐다. 이유는 둘이다. 페이지 배치가 바뀌면 그대로인 원문을 다시 묻게 된다. 페이지 조직이 실패하면 멀쩡한 원문 읽기까지 버린다(`Reference/JonexWiki/src/jonex_wiki/domain/engine/compile/understanding.py:3-7`). 기본값은 `layered`다(`Reference/JonexWiki/src/jonex_wiki/infra/settings.py:80-84`).

## 1. 구조

### 1.1 세 엔진 지도

| kb_type | 화면 이름(zh/en) | 파싱 모드 | 파싱 산출물 | 컴파일 | 저장소 | 질의 경로 |
|---|---|---|---|---|---|---|
| `lightrag` | Ontology | `full` | LightRAG 청크·벡터 + `ontology_data` | Stage4 본체 추출 → Neo4j MERGE | Milvus, LightRAG KV, Neo4j | `/search/ontology`·`query_with_ontology` |
| `openkb` | Ontology Wiki | `parse_only` | `parsed/{doc}/content.md`(다시 엮은 markdown) | vendored OpenKB `compile_short_doc` | 컨테이너 `jonex-openkb`의 `kb_storage` 볼륨(파일 wiki) | `/search/llmwiki`(OpenKB agent query) |
| `jonex_wiki` | Jonex Wiki | `parse_only` | `parsed/{doc}/content_list.json`(MinerU 구조 배열), xlsx/xlsm은 원본 바이너리 | JonexWiki 엔진 KB 단위 compile(불변 bundle) | 컨테이너 `jonex-wiki`의 `/data/jonex-wiki` + PG schema `jonex_wiki` | `/search/jonex_wiki` |

출처:
- 표의 kb_type 집합: `kb_type_service.py:35`(`KB_TYPE_ORDER`), 37(`VALID_KB_TYPES`), 40(`LLM_WIKI_TYPES = frozenset({"openkb", "jonex_wiki"})`).
- 파싱 모드 분기: `capabilities/knowledge_base/services/document_service.py:681-682`, `capabilities/knowledge_base/services/task_runner_service.py:189-206`.
- 산출물 형태: `task_runner_service.py:35-36`, `capabilities/knowledge_base/services/llm_wiki_artifacts.py:6,19,47,66`, `capabilities/knowledge_base/services/jonex_wiki_service.py:33-35, 67-76`.
- 컨테이너·볼륨: `deploy/docker-compose.yml:1126-1143`(openkb), `1164-1181`(jonex-wiki).
- 질의 경로 분기: `search_service.py:7613-7640`(search_llmwiki가 jonex_wiki KB를 거부), `7877-7903`(search_jonex_wiki가 openkb KB를 거부), `8155-8178`(search_mix 세 갈래).

### 1.2 모듈·파일 지도(무엇이 무엇을 부르나)

```
frontend (core-business)
  └─ /api/v1/knowledge-base/**  → api_gateway/routes/knowledge_base.py
       └─ Sidecar /invoke → knowledge-base-service (capabilities/knowledge_base/capability.py)
            ├─ knowledge_info_service.create()        # kb_type 확정(resolve_creatable_kb_type), llm-wiki면 init_kb + 기본 LLM-Wiki Schema 생성
            ├─ knowledge_info_service.update()        # kb_type 변경 거부(err.kb.kb_type_immutable)
            ├─ document_service.upload_document()     # kb_type 조회 → (lightrag만) compiled schema → task center 제출
            │    └─ task_runner_service               # 편성: parse_1 → compile_1 (kb_type별 정의 id)
            │         ├─ parse 단계 → atomic-rag insert(execution_mode = parse_only | full, kb_type)
            │         └─ compile 단계
            │              ├─ lightrag   → _submit_ontology_only (본체 추출)
            │              ├─ openkb     → openkb_service.KnowledgeCompilerService.recompile_openkb
            │              │                 └─ jonex_core/capability/atomic/openkb/client.py → (Sidecar) → openkb 컨테이너
            │              │                       └─ openkb_adapter._handle_compile_parsed_document
            │              │                             └─ Reference/OpenKB/openkb/agent/compiler.py::compile_short_doc
            │              └─ jonex_wiki → jonex_wiki_service.JonexWikiService (DB 보조는 KnowledgeCompilerService 재사용)
            │                                └─ jonex_core/capability/atomic/jonex_wiki/client.py → (Sidecar) → jonex-wiki 컨테이너
            │                                      └─ jonex_wiki_adapter.JonexWikiCapability (프로세스 안에서 import)
            │                                            └─ Reference/JonexWiki/src/jonex_wiki/application.py::WikiApplication
            │                                                  ├─ ingest_parsed_document → source_prep(체검·블록·매니페스트) → KB compile 작업 1개로 합침
            │                                                  └─ tasks/executor → domain/compile_task.py → domain/engine/compile/engine.py::LLMWikiV1Engine.compile
            ├─ reconciliation_service (30초 대사·순찰: patrol_openkb_compile 등)
            ├─ llm_wiki_schema_service               # openkb: AGENTS.md·entity_types 투영 / jonex_wiki: compile_main 뒤에 붙는 suffix 투영
            └─ search_service                        # search_mix: 세 갈래로 나눠 보내기 + 인용 병합 + 답 융합
```

출처:
- 생성 시 일괄 처리: `knowledge_info_service.py:104-128`.
- 업로드 분기: `document_service.py:602-708`.
- 편성 정의: `task_runner_service.py:29-36, 237-239, 277-292`, `deploy/postgres/update/044_task_center_jonex_wiki.sql`.
- compile 단계 갈래: `task_runner_service.py:687-702, 835-885`.
- JonexWiki를 프로세스 안에 둔 방식("B1 단일 컨테이너"): `jonex_wiki_adapter.py:1, 197-201`, `Reference/JonexWiki/src/jonex_wiki/application.py:1-9`.
- JonexWiki 서비스가 OpenKB 서비스의 DB 보조 메서드를 재사용함: `jonex_wiki_service.py:13-15, 111-115`.

훑음: `api_gateway/routes/knowledge_base.py`, `capabilities/knowledge_base/capability.py`, `reconciliation_service.py`는 grep으로 분기 지점만 봤다. 끝까지 읽지 않았다.

### 1.3 핵심 자료 구조

**플랫폼 PG(`knowledge_base` schema)**
- `knowledge_info.kb_type VARCHAR(16) NOT NULL DEFAULT 'lightrag'`(`deploy/postgres/migrations/004_knowledge_base.sql:79`, 모델 `capabilities/knowledge_base/models/knowledge_info.py:31`).
- `knowledge_info.ingest_backend`(NULL = 서버 스위치를 따름). 2026-10-09에 추가됐다(`deploy/postgres/update/045_knowledge_info_ingest_backend.sql`, `kb_type_service.py:171-194`).
- `knowledge_documents`의 wiki 열(`004_knowledge_base.sql:188-199`):
  - `llm_wiki_compile_status`(NULL/compiling/compiled/stale/failed), `llm_wiki_compile_error`, `llm_wiki_compile_warnings JSONB`.
  - `llm_wiki_compile_requested_at`(UTC, 순찰 시간 초과 기준), `llm_wiki_compiled_at`.
  - `llm_wiki_task_id`(엔진 쪽 compile 작업 id).
  - `llm_wiki_target_schema_version` / `llm_wiki_applied_schema_version`(schema 버전 fencing).
  - 두 wiki 엔진이 이 열들을 같이 쓴다(`jonex_wiki_service.py:13-15`).
- `knowledge_documents.extra_metadata`에 `kb_type`, `rag_result`, `ingest_backend`(제출할 때 고정되는 값)를 넣는다(`document_service.py:758-766`).
- `knowledge_base.llm_wiki_schemas`(`004_knowledge_base.sql:600-640`, 열 설명 `deploy/postgres/migrations/007_comments.sql:270-287`):
  - `schema_version`(저장할 때마다 +1), `status`(active/archived, KB마다 active는 하나), `sync_status`(synced/apply_failed).
  - `entity_types JSONB`, `concept_types JSONB`, `agents_md_extra`, `agents_md`(렌더한 전문), `config_snapshot`.
  - 표 주석: "Jonex DB 权威源，OpenKB 文件系统为运行时投影"(Jonex DB가 권위 원천이고, OpenKB 파일 시스템은 실행 시점의 투영이다).
- wiki 문서는 `ontology_status`를 업로드 때 곧바로 READY로 둔다. 컴파일 상태의 유일한 원천은 `llm_wiki_compile_status`다(`document_service.py:102-106, 758-765`).

**JonexWiki 엔진**(필드 단위 세부는 compile 갈래 몫이다. 여기서는 이유와 맞물리는 것만 적는다)
- `SourceContributionRecord`: 페이지와 무관한 원천 기여 기록이다. 정체성은 "source version + evidence location + normalized proposition"이다. 그래서 두 페이지에 나온 같은 사실이 기록 하나에 display 둘로 남는다(`Reference/JonexWiki/src/jonex_wiki/domain/engine/compile/source_contribution.py` docstring).
- `SourceSpan(passage_id, chunk_id, start_char, end_char, text)`: 문자 구간 근거다(앞선 보고서가 인용한 `models/compiler_state.py:427-446`). claim 판정은 `SUPPORTED / REFUTED / NOT_ENOUGH_INFO` 셋이다(`models/claim.py:23`, `compile/content_validation.py` docstring).
- 컴파일 산출물 bundle은 `{"format": "llm-wiki-plus", "schema_version": 3, "engine_id": "llm_wiki", "revision_id", "provenance", "checksums", "files"}` 형태의 불변 canonical JSON이다(`compile/bundle.py:1-30, 51`).
- 엔진 설정(`infra/settings.py:72-91`): `compile_mode`(legacy|layered, 기본 layered), `compile_concurrency`(기본 10), `compile_scheduler`(stream|window), `compile_max_passage_failure_rate`(0.05), `compile_repair_interval`(50), `compile_page_drop_threshold`(0.5).

## 2. 동작 흐름

### 2.1 KB 생성
1. `knowledge_info_service.create()`가 `resolve_creatable_kb_type()`을 부른다. 오류 코드는 둘이다. 모르는 값이면 `err.kb.invalid_kb_type`, 아는 값이지만 이 배포에서 금지했으면 `err.kb.kb_type_disabled`다(`kb_type_service.py:99-128`, `knowledge_info_service.py:58-63`).
2. llm-wiki 유형이면 커밋 뒤에 세 가지를 한다(`knowledge_info_service.py:104-128`).
   - (1) openkb만 `init_kb`로 KB 디렉터리와 AGENTS.md를 만든다. jonex_wiki는 첫 ingest 때 만든다.
   - (2) 기본 LLM-Wiki Schema DB 행을 만든다.
   - (3) `apply_schema`로 엔진에 투영한다.
   - 실패해도 KB 생성은 막지 않는다. `sync_status=apply_failed`로 남기고 나중에 보정한다.

### 2.2 업로드 → 파싱
1. `upload_document`가 kb_type과 `ingest_backend`를 한 번만 읽는다(`document_service.py:602-611`).
2. lightrag만 compiled schema를 준비한다. llm-wiki KB는 이 단계를 통째로 건너뛴다(`document_service.py:613-633`). 이유는 #3 J13에 적었다.
3. 세 유형 모두 task center에 넘긴다(`document_service.py:653-673`). 편성은 `parse_1 → compile_1` 두 단계다. 파싱 단계는 atomic-rag `insert`에 `execution_mode`와 `kb_type`을 함께 보낸다.
   - wiki 두 유형은 `parse_only`다. LightRAG에 청크를 넣지 않고 본체도 뽑지 않는다(`task_runner_service.py:189-206`).
   - openkb 산출물은 `content.md`, jonex_wiki 산출물은 `content_list.json`이다.
4. task center를 쓰지 않는 옛 경로도 아직 코드에 있다(`document_service.py:681-708`). 거기서도 같은 `execution_mode` 분기를 쓴다.

### 2.3 compile — openkb
1. `KnowledgeCompilerService.recompile_openkb`가 열 claim → adapter `compile_parsed_document`를 부른다. adapter는 작업 파일을 만든 뒤 백그라운드 태스크로 돌린다(`openkb_adapter.py:352-407`).
2. KB마다 asyncio mutation lock으로 직렬화한다(`openkb_adapter.py:52-58, 411`).
3. schema 버전 fencing 2차 방어를 한다. 디스크의 `jonex_schema.json` 버전이 목표 버전과 다르면 작업을 failed로 둔다(`openkb_adapter.py:413-438`).
4. `_compile_parsed_markdown`이 Jonex 파싱 markdown을 `wiki/sources/{document_id}.md`로 쓰고 OpenKB `compile_short_doc`을 부른다. "不经过 converter/indexer，不触发 PageIndex"(converter·indexer를 거치지 않고 PageIndex를 켜지 않는다)라고 적혀 있다(`openkb_adapter.py:940-943`).
5. `compile_short_doc`의 LLM 호출 순서(`Reference/OpenKB/openkb/agent/compiler.py:1-15, 2205-2217`):
   - 문서 + schema로 기본 문맥 A를 만들고 summary를 쓴다.
   - concepts plan(create/update/related)을 세운다.
   - concept 페이지를 동시에 생성하거나 다시 쓴다.
   - 상호 참조 링크와 index는 코드가 붙인다.
6. 컴파일은 `asyncio.to_thread`로 돌린다. vendored 컴파일러가 동기 `litellm.completion`을 불러 메인 이벤트 루프를 막았기 때문이다(`openkb_adapter.py:440-450`).
7. 순찰(`patrol_openkb_compile`)이 작업 파일을 읽어 DB 열에 다시 쓴다(`007_comments.sql:65`).

### 2.4 compile — jonex_wiki
1. 플랫폼이 `stage_jonex_wiki_ingest_source`로 원천 경로를 정한다. xlsx/xlsm이면 원본 바이너리를 공유 볼륨에 둔다. 그 밖에는 MinerU `content_list.json` 경로를 준다(`jonex_wiki_service.py:67-104`).
2. 엔진 `ingest_parsed_document`가 받은 원천을 정리한다.
   - "raw-only parse"로 원문만 디스크에 둔다. 정규화·packing·투영은 compile로 미룬다(`compile/source_prep/raw_manifest.py` docstring).
   - 체검(inspect·screening)으로 packer에 들어갈 수 없는 단위만 빼서 `gen-N/source-archive/`에 남긴다.
   - 그 KB의 대기 중 compile 작업이 있으면 거기에 합친다. 없으면 새로 만든다(`application.py:385-397`).
   - 응답에 산출물 형태 계약(`contract`)과 경고를 담아 돌려준다(`application.py:398-413`).
3. compile 작업(`domain/compile_task.py`)은 KB 전체를 대상으로 한다. `engine.compile`이 `sources.get_artifacts(context_id, tenant_id)`로 KB의 모든 artifact를 읽는다(`compile/engine.py:409-411`).
   - 입력 지문으로 revision id를 만든다. 지문에는 원천 지문, manifest, prompt checksum, 엔진 버전, 런타임 스냅샷, bundle schema 버전이 들어간다(`engine.py:413-458`).
4. `compile_mode == "layered"`이면 `_layered_compile`로 간다(`engine.py:711-712, 1118-1265`).
   - 증분 관문: 원천이 모두 살아 있고 바뀌지 않은 페이지만 이전 bundle에서 다시 쓴다(`engine.py:1158-1199`).
   - `UnderstandingStage`: passage마다 LLM 1회. LLM은 원천 passage만 보고 페이지 본문은 보지 않는다. 결과는 체크포인트로 저장한다. 캐시 정체성에서 페이지 배치는 일부러 뺐다(`understanding.py:9-26`).
   - `organize_sources`: 페이지 배정은 가능한 한 프로그램 규칙으로 정한다. 규칙으로 못 정한 같은 이름만 묶음당 LLM 판정 1회로 정한다. 후보는 4개 이하, compile당 8회 이하다(`organization.py:1-37, 85-94`).
   - 그 뒤 공용 publication tail로 합친다. 관계, 링크 해석, query corpus, index, bundle staging, 발행이 두 모드에서 같은 코드다(`engine.py:701-710`).
5. `legacy`이면 논문 Algorithm 1을 그대로 돈다. passage마다 `SELECTPAGES(x, I)`(기존 페이지 5개 이하) → `COMPILEWIKIPAGES(x, S, C)` → 구조·내용 검증 → Error Book → 주기적 수리 순서다(`compile/pipeline.py:1-9`, `models/compiler_state.py:1-17, 30`, `compile/error_book.py:1-16`).
6. 발행 전 외곽 관문(`compile_task.py:147-165`):
   - 원천이 있는데 0페이지면 발행을 거부한다.
   - 원천 수가 늘었는데 페이지가 50% 넘게 줄면 발행을 거부하고 이전 bundle로 계속 서비스한다.
7. 발행은 원자적 디렉터리 + symlink 전환으로 한다(`compile_task.py:167`).

### 2.5 LLM 호출 지점과 결정적(코드) 검사 지점(jonex_wiki, 이유와 맞물리는 것만)

| 지점 | LLM? | 프롬프트·scene | 출처 |
|---|---|---|---|
| source understanding | O, passage당 1회(+재시도) | scene `jonex_wiki_source_understanding`, prompt version `understand-source-prompt-v4-source-excerpts` | `understanding.py:56-69` |
| organization 정체성 판정 | O, 묶음당 1회, compile당 ≤8 | scene `jonex_wiki_compile_organization_identity`, 시스템 프롬프트 `_ORGANIZATION_JUDGMENT_SYSTEM` | `organization.py:85-130` |
| claim 근거 검사 | X | `claim-support-v3` 규칙(보호 원자: 날짜·숫자·단위·부정·비교) | `models/claim.py:1-33` |
| 구조 검증·결정적 수리 | X | — | `compile/structural.py` docstring |
| Error Book 수리 라운드 | O, N batch마다(기본 50) | `compile_structured` 등 내부 프롬프트(사용자에게 안 보임) | `error_book.py:1-16`, `domain/prompts.py:11-48` |
| 누락 수리 | X, 검증된 원문을 결정적으로 덧붙임 | — | `compile/omission_repair.py` docstring |
| 렌더링(frontmatter·index·backlink) | X | — | `compile/rendering.py` docstring |
| compile_main 골격 | 사용자 suffix만 덧붙일 수 있음 | `COMPILE_MAIN_SKELETON` | `domain/prompts.py:50-67` |

실패·재시도:
- passage가 끝내 실패한 비율이 `max_passage_failure_rate`(0.05)를 넘으면 fail closed다(`pipeline.py:615-667`, `.env.jonex_wiki.example:218-219`).
- understanding 실패 passage는 그 자리에서 건너뛰고 셈한다. "one bad source never blocks the rest"(나쁜 원천 하나가 나머지를 막지 않는다)라고 적혀 있다(`organization.py:33-36`).
- 쓰기 경합: 모델 호출·체크포인트 I/O·재시도는 commit lock 바깥에서 한다(`organization.py:30-32`).

## 3. 설계 결정과 이유

각 결정은 (a) 작성자가 밝힌 이유, (b) [추정], 대안, 이력 순으로 적는다.

### J1. OpenKB를 fork가 아닌 vendored 사본으로 들여오고, 바꾼 곳을 문서로 따로 관리한다
- 사실: `Reference/OpenKB/`는 upstream VectifyAI/OpenKB 0.4.5의 사본이고 Apache 2.0이다(`THIRD_PARTY_NOTICES.md:60-69`). 바꾼 곳은 `# [jonex]` 표식과 `Reference/OpenKB/JONEX_CHANGES.md`로 관리한다.
- (a) "本文件记录Jonex 平台对 vendored OpenKB 源码的所有改动点，便于后续升级 OpenKB 时快速定位、重新 apply"(이 파일은 Jonex가 vendored OpenKB 소스에 가한 모든 변경점을 적어, 나중에 OpenKB를 올릴 때 빨리 찾아 다시 적용하게 한다)(`Reference/OpenKB/JONEX_CHANGES.md:3-4`).
- (a) "上游不是本仓的 remote，没有可比的基线。以本文档各节的'改动'清单为准"(upstream은 이 저장소의 remote가 아니어서 비교할 기준선이 없다. 이 문서의 변경 목록을 기준으로 삼는다)(`JONEX_CHANGES.md:228`).
- 바꾼 범위: 처음 계획은 "~80 行改动/新增。不修改 `api.py`、`compiler.py`"(약 80줄, api.py·compiler.py는 안 고침)였다(`JONEX_CHANGES.md:53`). 그 뒤 query trace, 출력 언어, 모델 해석 변경이 쌓였다(§五~§九).
- 어긋남(참고): 2026-08-10에 바꾼 출력 언어 변경("Write all content in the same language as the source document.")은 `compiler.py:58`에 들어가 있다. 그런데 `[jonex]` 표식이 없다(`grep -rn '\[jonex\]' Reference/OpenKB/openkb` 결과에 compiler.py가 없다). 그래서 "`[jonex]`로 전역 검색하면 찾을 수 있다"(`JONEX_CHANGES.md:4`)는 약속이 이 한 곳에서는 지켜지지 않는다.
- 대안: 일반 의존성으로 설치(`pip install openkb`)하거나 GitHub fork로 두는 것. [추정] vendoring을 고른 것은 metering 헤더 주입과 모델 해석처럼 엔진 안쪽에 손을 대야 했기 때문이다(사례: JONEX_CHANGES §(A) metering, §六·§七·§九 모델 해석, 3곳).
- 이력: `Reference/OpenKB`가 공개 이력에 처음 나온 것은 `f6205dc`(2026-08-12)다. JONEX_CHANGES는 내부 hash `5cec22c4`(2026-07-30)에 772줄로 vendored됐다고 적는다(`JONEX_CHANGES.md:263`). 이 hash는 공개 이력에 없다. 공개 이력이 squash됐기 때문이다(`f6205dc` 메시지 "Squashed several dozen commits from the source branch into this one").

### J2. OpenKB에는 Jonex가 파싱한 markdown만 넣고, OpenKB의 converter·PageIndex는 우회한다
- (a) 사실 서술: "将 Jonex parsed markdown 写入 wiki/sources 并复用 compile_short_doc 编译 … 不经过 converter/indexer，不触发 PageIndex"(Jonex 파싱 markdown을 wiki/sources에 쓰고 compile_short_doc을 재사용해 컴파일한다. converter·indexer를 안 거치고 PageIndex를 안 켠다)(`jonex_core/capability/atomic/openkb/openkb_adapter.py:940-943`).
- 이유 원문은 없다.
- (b) [추정] 파싱을 세 엔진이 한 파이프라인으로 같이 쓰려 한 것이다(사례: task center 편성 표에서 세 유형의 첫 단계가 모두 atomic-rag `parse`다. `task_runner_service.py:29-36`, 1곳).
- 대가(참고): OpenKB README가 내세우는 "Scales to long documents … via PageIndex tree indexing"(`Reference/OpenKB/README.md:45`)이 Jonex 안에서는 꺼진다. 긴 문서도 `compile_short_doc` 하나로 들어간다.
- 모르는 것: 긴 문서에서 `compile_short_doc`이 문맥 한도에 걸리는지. `compile_short_doc`의 입력 자르기 로직(`compiler.py:2205-2290`)과 Jonex 쪽 문서 길이 제한을 읽으면 알 수 있다. 이 갈래에서는 읽지 않았다.

### J3. OpenKB가 있는데도 JonexWiki를 따로 만들었다(핵심 물음 1)
- (a) 작성자가 밝힌 "왜"는 없다.
  - 커밋 `a8bee87`(2026-10-10)은 186파일, +62,467줄을 한 번에 들였다. 메시지는 제목 "feat(jonex-wiki): wiki engine integration with outline and page references"와 Co-Authored-By 한 줄뿐이다.
  - 엔진을 설명하는 README·설계 문서도 공개본에 없다. 코드가 가리키는 `docs/jonex_wiki/*.md`, `docs/llm-wiki-plus/compiler-candidate-hybrid-retrieval-plan.md`는 `.gitignore:307-312`("docs/ 下为内部设计文档与执行计划"(docs/ 아래는 내부 설계 문서와 실행 계획))로 빠졌다.
- (a) 화면 문구로 밝힌 위치 설정(왜 만들었는지가 아니라 무엇으로 내놓았는지):
  - lightrag: "向量检索 + 知识图谱，支持片段级引用溯源，适合实时问答"(벡터 검색 + 지식 그래프, 조각 단위 인용 추적, 실시간 질의응답에 맞음).
  - openkb: "LLM 将文档编译为结构化 Wiki，适合知识沉淀与深度理解"(LLM이 문서를 구조화 wiki로 컴파일, 지식 축적과 깊은 이해에 맞음).
  - jonex_wiki: "新一代 LLM Wiki 引擎，将文档编译为可检索的结构化知识库"(차세대 LLM Wiki 엔진, 문서를 검색 가능한 구조화 지식 베이스로 컴파일).
  - 출처: `frontends/core-business/src/locales/zh.json:1524-1528`. README 부제도 "Powered by the Dual Engines of Jonex Wiki and Graph Ontology"(Jonex Wiki와 그래프 본체의 이중 엔진)로 JonexWiki를 그래프와 나란한 주력으로 내세운다(`README.md:7`).
- (b) [추정] 동기 1, 인용 추적: OpenKB는 처음에 "인용 추적 없음"으로 나왔고, 나중에 붙인 인용도 문서 단위 역산이다. JonexWiki는 claim마다 문자 구간을 단다.
  - 사례 1: commit `f6205dc`의 zh.json에서 openkb 설명은 "…适合知识沉淀与深度理解；暂不支持引用溯源"(…아직 인용 추적을 지원하지 않음)이었다. `a8eb6f6`(2026-08-28)에서 뒷부분이 빠졌다(`git log -L` 결과).
  - 사례 2: OpenKB 인용은 agent의 wiki 탐색 궤적에서 문서를 거꾸로 찾는다. concept/entity 페이지는 frontmatter `sources`로 문서를 찾는다. "为什么改 B：A 把「页面本身不是用户上传的文档」误当成「页面无法定位到文档」"(B로 바꾼 이유: A안은 "페이지가 사용자가 올린 문서가 아니다"를 "페이지로 문서를 찾을 수 없다"로 잘못 다뤘다)(`search_service.py:7157-7175`). 단위는 문서다.
  - 사례 3: JonexWiki는 claim마다 `SourceSpan`과 `SUPPORTED/REFUTED/NOT_ENOUGH_INFO` 판정을 단다(`content_validation.py` docstring, `models/claim.py:23`).
  - 사례 3개.
- (b) [추정] 동기 2, 재컴파일 안정성: OpenKB는 문서 단위로 페이지를 제자리에서 고쳐 쓴다. JonexWiki는 KB 단위로 불변 revision을 다시 만들고, 바뀐 원천만 다시 처리한다.
  - 사례 1: 외부 사용자 이슈 #22(2026-09-14, 유지보수자 답 없음, 재현 확인 안 됨). 같은 문서를 다시 컴파일하면 `concepts/attention-mechanism-2.md` 같은 중복 concept 페이지가 생긴다는 보고다.
  - 사례 2: JonexWiki `_layered_compile` docstring "Unchanged pages are reused only when their source versions and record sets still match"(원천 버전과 기록 집합이 그대로일 때만 바뀌지 않은 페이지를 다시 쓴다)(`engine.py:1152-1155`).
  - 사례 2개.
- (b) [추정] 동기 3, 표·구조 문서: JonexWiki는 MinerU 구조 배열과 xlsx 원본을 직접 받는다. 표 머리글 해석, 표 view 페이지, 표 질의를 따로 둔다.
  - 사례: `jonex_wiki_service.py:31-35, 67-76`, `compile/source_prep/header_interpretation.py`, `compile/table_views.py`, `query/table_*.py`. 4곳.
  - 이것이 중요하다는 근거: `application.py:57-59`가 "解析产物从 content_list.json 静默退回 content.md，表格资产 / caption / footnote 全部不可用 … （真实事故）"(파싱 산출물이 content_list.json에서 조용히 content.md로 물러나면 표 자산·caption·footnote를 전부 못 쓴다 … (실제 사고))라고 적는다. content.md만 쓰는 openkb 경로가 바로 그 제약을 안고 있다.
- (b) [추정] 동기 4, 논문 구현: JonexWiki 안쪽 이름은 "llm-wiki-plus"다(`bundle.py:51`, `pipeline.py:103`). 코드 docstring이 논문 요구를 "Paper-required behavior"로 6곳에 적는다(`rendering.py`, `content_validation.py`, `compiler_state.py`, `structural.py`, `error_book.py`의 "paper pipeline", `pipeline.py`의 "Algorithm-1"). 사례 6곳. 논문은 J4에 적었다.
- 대안: OpenKB를 고쳐 쓰기(claim 근거, 증분 컴파일 추가). [추정] 고르지 않은 까닭은 OpenKB 컴파일러가 문서 전체를 한 문맥에 넣고 summary → concept 순으로 가는 구조이기 때문이다. passage 단위 근거와 맞지 않는다(사례: `Reference/OpenKB/openkb/agent/compiler.py:1-15`, 1곳).
- 이력:
  - 플랫폼 코드에 `"jonex_wiki"` 문자열이 처음 나온 것은 `0541be3`(2026-09-23)이다. 엔진 소스(`Reference/JonexWiki`)는 그보다 늦게 `a8bee87`(2026-10-10)에 공개됐다(`git log -S '"jonex_wiki"'`, `git log -- Reference/JonexWiki`).
  - [추정] 엔진은 그전부터 독립 서비스로 따로 개발되고 있었다(사례: `application.py:3-6` "独立引擎 FastAPI 服务"(독립 엔진 FastAPI 서비스), `compile_task.py:3` "旧 dev 的 allocator/page_compiler/gates/incremental/indexes 编译管线整体替换为 LLMWikiV1Engine.compile"(옛 dev의 컴파일 파이프라인 전체를 LLMWikiV1Engine.compile로 바꿨다), "Extracted verbatim from engines/llm_wiki_plus/…"가 9개 모듈에 있음. 3종류).

### J4. JonexWiki compile 골격 = 논문 "LLM-Wiki"의 Algorithm 1 + Error Book
- 논문: Haoliang Ming, Feifei Li, Xiaoqing Wu, Wenhui Que(WeChat, Tencent Inc.), "Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki", arXiv 2605.25480, v1 2026-05-25, v2 2026-05-26. https://arxiv.org/abs/2605.25480 , HTML https://arxiv.org/html/2605.25480v2
  - Algorithm 1은 입력으로 원천 묶음 X, 현재 Wiki W, 디렉터리 index I, 원천 archive A, 활성 Error Book 제약 C를 받는다. passage x마다 `S ← SelectPages(x, I)`, `U ← CompileWikiPages(x, S, C)`, 구조·내용 검증, 오류 집합이 있으면 Error Book 갱신 + CodeAutoFix, 마지막으로 W 적용 순서로 돈다. 주기마다 LLMPeriodicFix와 VerifyAndClose를 돈다. §4.4가 SelectPages를 "at most k=5 pages"로 정한다(위 HTML을 WebFetch로 읽은 요약).
  - 논문이 내세운 이유: "flat chunks reduce retrieval to matching, not reasoning"(평평한 청크는 검색을 추론이 아닌 맞추기로 만든다), "the bottleneck lies in how knowledge is organized and exposed to the agent"(병목은 지식을 어떻게 조직해 agent에게 내보이느냐다). Karpathy의 LLM Wiki가 "remains an abstract design pattern"(아직 추상적 설계 패턴이다)이라서 컴파일·품질 보증·조합 검색으로 구체화한다고 한다.
  - 논문 페이지에는 코드 공개 링크가 없다. Jonex·yuezhiai·OpenKB 언급도 없다.
- 코드가 논문과 맞물리는 곳(a):
  - `compiler_state.py:1-17` "SELECTPAGES(x, I) and COMPILEWIKIPAGES(x, S, C) … at most five existing pages may be selected", 상수 `MAX_SELECTED_EXISTING_PAGES = 5`(30행).
  - `error_book.py:4-9` "composing the paper pipeline as:: compile batch -> discover errors -> attribute new errors -> persist constraints -> inject open constraints into the next batch -> periodic bounded repair -> revalidate before close"(배치 컴파일 → 오류 발견 → 새 오류 원인 귀속 → 제약 저장 → 다음 배치에 열린 제약 주입 → 주기적 수리 → 닫기 전 재검증).
  - `content_validation.py:11-17` "every factual claim has evidence; referenced document/chunk content exists in source archive A; evidence excerpts are exact normalized substrings"(모든 사실 claim에 근거가 있고, 가리킨 내용이 원천 archive A에 있고, 근거 발췌는 정규화한 정확 부분 문자열이다).
  - 같은 docstring들이 Jonex가 덧붙인 부분을 따로 밝힌다. "Passage IDs, stable claim IDs, issue schemas and line-ending-only normalization are Jonex engineering adaptations"(`content_validation.py:19-20`). "The exact Markdown layout … are Jonex engineering adaptations"(`rendering.py:17-18`).
- 논문에 없는데 JonexWiki가 더한 것: "exact substring" 검사(논문 요약에 없다고 WebFetch가 보고), 결정적 claim 지지 규칙(`claim.py`), 원천 기여 기록(`source_contribution.py`), 정체성 규칙(`identity.py`), layered 분리(J5).
- (b) [추정] 이 논문을 고른 것은 같은 Tencent 생태계 안이기 때문일 수 있다(사례: 배포가 Tencent COS·MPS·TokenHub를 씀. `jonex-platform-architecture.md:37, 374`, `.env.jonex_wiki.example:102` "腾讯 tokenhub 格式", 3곳). 연결을 보여 주는 직접 증거는 없다.
- 모르는 것: 저자와 Jonex 팀의 관계, 논문 원 코드가 있는지. 논문 v3이나 저자 GitHub, `engines/llm_wiki_plus/` 원 저장소를 찾으면 알 수 있다.

### J5. legacy(논문식 passage 1회 호출)에서 layered(이해 → 조직)로 나눴다(핵심 물음 3의 중심)
- (a) "The legacy compile chain asks one model, once per passage, to *both* decide which pages a passage belongs to and restate its facts. That coupling has two costs the plan targets: a page layout change re-asks the model about unchanged source text, and a failed page organization throws away a perfectly good reading of the source."(legacy는 passage마다 모델 한 번에 페이지 배정과 사실 재진술을 같이 시킨다. 이 결합의 비용은 둘이다. 페이지 배치가 바뀌면 그대로인 원문을 다시 묻고, 페이지 조직이 실패하면 멀쩡한 원문 읽기를 버린다.)(`understanding.py:3-7`).
- (a) understanding 단계의 규칙(`understanding.py:11-26`):
  - 모델은 원천 passage만 본다. "never the wiki's page bodies"(wiki 페이지 본문은 절대 안 본다).
  - 모든 정체성(record_id, passage/source/document id, 근거 참조)은 프로그램이 정한다. "never trusts a model-supplied id"(모델이 낸 id는 믿지 않는다).
  - 결과는 legacy와 같은 evidence gate를 지나 같은 `SourceContributionRecord`가 된다. "exactly one contribution ledger and no second source-of-truth"(기여 장부는 하나뿐이고 두 번째 진실 원천은 없다).
  - 체크포인트 캐시 정체성은 원천·파서·프롬프트·모델을 덮는다. "deliberately *not* the page layout"(페이지 배치는 일부러 넣지 않는다).
- (a) organization 단계의 치우침: "**pages are projected from validated contributions**. Assignment is program-determined wherever it can be"(페이지는 검증된 기여에서 투영한다. 배정은 가능한 한 프로그램이 정한다)(`organization.py:7-9`).
  - 규칙이 못 정한 것만 bounded LLM 판정에 맡긴다. "The bound is what keeps 'semantic organization' from becoming an unbounded classification pass"(이 상한이 "의미 조직"이 끝없는 분류 작업이 되는 것을 막는다)(`organization.py:89-91`).
- (a) 순서 보장: "organization commits in **stable input order** … so completion order cannot change the published fact set"(조직은 입력 순서대로 커밋한다. 그래서 완료 순서가 발행 사실 집합을 바꾸지 못한다)(`organization.py:27-29`).
- (a) 두 모드는 꼬리를 같이 쓴다. "Layered does not get its own copy of the engine"(layered가 엔진 사본을 따로 갖지 않는다)(`engine.py:701-705`, `1144-1150`).
- (a) 모드는 컴파일 정체성에 들어간다. "legacy and layered compile different things, so switching modes must invalidate a previous bundle"(두 모드는 다른 것을 컴파일하므로 모드를 바꾸면 이전 bundle을 무효로 해야 한다)(`engine.py:68-70`, `settings.py:80-84`).
  - 반대로 동시성·스케줄러·실패율·수리 간격은 "只影响「怎么调度」、不影响「编译出什么」"(어떻게 스케줄하느냐만 바꾸고 무엇을 컴파일하느냐는 안 바꾼다)라서 정체성 비교에서 뺀다. 넣으면 설정 조정 하나가 전량 재컴파일이 된다(`engine.py:56-66`).
- 대안: 논문 그대로(legacy). 지금도 `JONEX_WIKI_COMPILE_MODE=legacy`로 고를 수 있다(`.env.jonex_wiki.example:222-224` "默认采用分层编译；旧链路仅在显式指定 legacy 时启用"(기본은 분층 컴파일, 옛 경로는 legacy를 명시할 때만 켠다)).
- 이력: 공개 이력에는 처음부터 둘 다 있다(`a8bee87`). 내부 단계명 "S7.0/S7.1/S7.2"(`settings.py:80`, `understanding.py:1`, `organization.py:1`)가 내부 계획 문서의 절 번호로 보이지만 그 문서는 없다.

### J6. 정체성(같은 대상) 판정은 보수적이고, "모른다"를 허용한다
- (a) "a bare name match across different contexts is *undetermined* - two cities with one name are not one entity … nothing is merged automatically"(맥락이 다른 곳에서 이름만 같으면 미정이다. 이름이 같은 두 도시는 한 대상이 아니다. 아무것도 자동으로 합치지 않는다)(`compile/identity.py:9-15`).
- (a) "Relations that look like names are not names: a predecessor, successor, parent, subsidiary or brand stays a relation and never becomes an alias"(이름처럼 보이는 관계는 이름이 아니다. 전신·후신·모회사·자회사·브랜드는 관계로 남고 별칭이 되지 않는다)(`identity.py:17-18`).
- (a) layered 조직은 identity.py보다 한 단계 더 보수적이다. identity.py docstring은 "a name plus its context can be enough"(이름 + 맥락이면 충분할 수 있다)라고 한다(`identity.py:10-11`). 그런데 `organization.py:521-526`은 `basis == "name_and_context"` 판정을 undetermined로 낮춘다. 주석은 "Matching source qualifiers may be only a year or a unit. They do not establish that two cross-source entities are one"(겹치는 수식어가 연도나 단위뿐일 수 있다. 그것으로 두 원천의 대상이 같다고 세울 수 없다)다.
- (a) "Topic pages are first-class: not every fact has to belong to an entity"(토픽 페이지도 일급이다. 모든 사실이 엔티티에 속할 필요는 없다)(`identity.py:20`).
- 대안: 이름 정규화로 합치기. 그래프 길의 MERGE 키 `(tenant, kb, entity_type, canonical_name)`이 이 방식이다(`jonex-platform-architecture.md:388`). [추정] wiki 길이 그래프 길보다 보수적인 것은 잘못 합친 페이지를 사람이 되돌리기 어려워서다(사례: `organization.py:21-23` "Nothing is merged on resemblance alone", 1곳). 근거가 약하다.

### J7. claim 근거 검사는 결정적이고 좁은 언어만 증명한다
- (a) "The checker intentionally proves a small, auditable language instead of pretending to solve unrestricted natural-language inference … Anything outside those bounded rules is NOT_ENOUGH_INFO"(검사기는 일부러 작고 감사 가능한 언어만 증명한다. 제약 없는 자연어 추론을 푸는 척하지 않는다. 그 밖은 NOT_ENOUGH_INFO다)(`models/claim.py:3-8`).
- (a) 보호 원자: 날짜·숫자·단위·부정·비교. 표 사실은 한 행에 머물게 하고, 표 합계만 계산을 허용한다(`claim.py:5-7`).
- 같은 제약을 compile_main 골격 프롬프트도 건다. "never add an unsupported number, date, unit, negation, comparison, table relation, or derived fact"(근거 없는 숫자·날짜·단위·부정·비교·표 관계·파생 사실을 더하지 마라)(`domain/prompts.py:64-67`).
- 이력: 규칙 버전 `claim-support-v1`(구두점 접기 + 부분 문자열, 보호 원자 검사 없음) → v3(퍼센트 단위 유지)(`claim.py:25-33`). 옛 규칙으로 만든 bundle은 판정을 동결해 둔다.

### J8. Error Book과 bounded 수리, 좁은 누락 수리
- (a) Error Book은 논문 장치다(J4). Jonex는 "one bounded repair round"(수리 라운드 하나로 묶음)만 둔다. 외부 세계(저장소·시계·난수·네트워크)를 건드리지 않는 순수 모듈로 둔다(`error_book.py:3-16`).
- (a) 누락 수리는 확인된 누락 하나에만 쓴다. "A missing answer is not automatically a compilation omission"(답이 없다고 곧 컴파일 누락은 아니다)(`compile/coverage_diagnostic.py` docstring). "No model is called anywhere in this module: the repair is a deterministic append of verified source text"(이 모듈은 모델을 부르지 않는다. 수리는 검증된 원문을 결정적으로 덧붙이는 것이다)(`omission_repair.py` docstring).
- (a) 거부한 기여는 조용히 버리지 않는다. "One Error Book row per refused contribution, never a silent drop"(거부한 기여마다 Error Book 행 하나, 조용히 버리지 않음)(`engine.py:75-80`).

### J9. KB 단위 불변 bundle + compile 작업 합치기 + 증분 재사용 + 발행 관문
- (a) bundle은 "one immutable, portable byte blob"(불변·이식 가능한 바이트 덩어리 하나)이고, "Decode is the trust boundary"(decode가 신뢰 경계다)라서 경로·checksum을 다시 검증하고 fail closed한다(`bundle.py:3-30`).
- (a) "Changing any compile instruction changes this and forces a recompile, not a replay"(컴파일 지시를 바꾸면 checksum이 바뀌어 재생이 아닌 재컴파일이 된다)(`pipeline.py:100-103`).
- (a) 지운 원천이 낡은 페이지로 살아남지 않게 한다. "a removed source is not carried at all, so a deleted source cannot survive as a stale page snapshot and no page is ever the union of old and new snapshots"(지운 원천은 아예 옮기지 않는다. 그래서 낡은 스냅샷으로 남지 못하고, 어떤 페이지도 옛것과 새것의 합집합이 되지 않는다)(`engine.py:1164-1168`).
- (a) compile 작업 합치기: 같은 KB에 대기 중 compile 작업이 있으면 새로 만들지 않는다(`application.py:385-397`). executor 주석은 "queued so later parse completions can coalesce into it"(뒤이은 파싱 완료가 이 작업으로 합쳐지게 대기에 둔다)이다(`tasks/executor.py:82`). 업로드 묶음은 파싱이 다 끝난 뒤 컴파일한다(`compile_task.py:41-53` "Let an upload batch finish parsing before starting another expensive compile"(비싼 컴파일을 또 시작하기 전에 업로드 묶음의 파싱을 끝내게 한다)).
- (a) 빈 산출물 관문: "源数不变 = 纯重编译/reparse，页面波动来自 LLM 非确定性与解析粒度差异 … （本次 5 → 2 即属此类）"(원천 수가 같으면 순수 재컴파일이다. 페이지 수 변동은 LLM 비결정성과 파싱 입도 차이에서 온다. 이번 5 → 2가 그 예다)(`compile_task.py:155-160`). 그래서 원천 수가 늘었는데 페이지가 급감할 때만 막는다.
- 대안: OpenKB식 문서 단위 제자리 수정. [추정] KB 단위 revision을 고른 것은 발행 원자성과 되돌리기 때문이다(사례: `compile_task.py:147-150` "拒绝发布并保留旧 bundle 继续服务"(발행을 거부하고 옛 bundle로 계속 서비스), `.env.jonex_wiki.example:247-248` 지난 bundle 2개 보관. 2곳).

### J10. 파싱은 "원문만 받기", 정규화는 compile로. 체검은 단위만 격리하고 원문은 보관한다
- (a) "解析只负责「原样拿到」,归一化/打包/投影全部推迟到 compile"(파싱은 "있는 그대로 받기"만 맡고, 정규화·packing·투영은 모두 compile로 미룬다)(`source_prep/raw_manifest.py` docstring).
- (a) 체검이 있는 이유: "一份 296 页文档里某个 OCR 退化的表格行有 6,933 字符，守卫把整份文档判死"(296쪽 문서에서 OCR이 망가진 표 행 하나가 6,933자여서 가드가 문서 전체를 실패시켰다)(`source_prep/inspect.py` docstring). 그래서 그 단위만 compile 면에서 빼고 나머지는 컴파일한다.
- (a) 체검 범위를 일부러 좁혔다. "只收'结构超限'与它的两个前因 … '内容质量'类问题（空表、复读、乱码……）**不进这里**"(구조 초과와 그 두 원인만 다룬다. 빈 표·반복·깨진 글자 같은 내용 품질 문제는 넣지 않는다). 이유는 "多出一种'半失败态'"(반쯤 실패한 상태가 하나 더 생긴다)이다.
- (a) 원문을 보관하는 이유: "① 人工无法核对判据是否误杀 ② … 没有'当时按什么判的'的底稿"(① 사람이 판정이 좋은 내용을 잘못 버렸는지 확인할 수 없고 ② 당시 무엇으로 판정했는지 원본이 없다)(`source_prep/source_archive.py` docstring).
- (a) "前置筛查"(앞단 선별)를 고른 이유: packer의 본문 로직을 "一行不改"(한 줄도 안 고치고) 두기 위해서다. 선별이 놓치면 `PackingError`로 "响亮失败"(크게 실패)하도록 남긴다(`source_prep/screening.py` docstring).

### J11. jonex_wiki에는 다시 엮은 markdown이 아닌 MinerU 구조 산출물을 준다
- (a) 산출물 형태 계약이 있는 이유는 J3 동기 3의 "真实事故"(실제 사고) 인용이다(`application.py:55-60`). 그 계약이 플랫폼의 `llm_wiki_compile_warnings`로 돌아온다.
- 이력: 내부 hash `74b76989`에서 jonex_wiki 산출물을 `content_list.json`으로 바꿨다. 2026-09-18에 회귀 수정을 했다(`document_service.py:1330-1346`). 이 hash는 공개 이력에 없다.

### J12. compile_main은 고정 골격 + 사용자 suffix만 열고, 나머지 18개 프롬프트는 동결한다
- (a) "唯一开放的是 compile_main（固定骨架 + 用户「编译偏好」suffix）。其余 18 个全是引擎正确性约束 … 冻结后行为不变，仅消除「暴露但不生效」的入口"(열어 둔 것은 compile_main 하나다. 나머지 18개는 모두 엔진 정확성 제약이다. 동결해도 동작은 같고, "보이지만 효과 없는" 입구만 없앤다)(`domain/prompts.py:18-26`).
- (a) 플랫폼 화면 문구: "jonex_wiki compile settings are a compile preference appended after the engine's fixed compile_main skeleton (page-path / evidence / JSON-output constraints, not editable)"(`frontends/core-business/src/locales/en.json:1847`).
- 대조: openkb는 KB마다 사람이 고치는 entity_types 통제 어휘 + AGENTS.md 추가 블록을 둔다(`llm_wiki_schema_service.py:233-245`). jonex_wiki는 어휘 없이 "편집 선호" 문구만 받는다.
- [추정] jonex_wiki가 종류 어휘를 두지 않은 것은 정체성·근거를 코드 규칙으로 정하기 때문이다(사례: J6·J7 규칙, 2종류). 근거가 약하다.

### J13. 그래프 KB와 wiki KB를 KB 단위로 배타시킨다(핵심 물음 2)
- 사실: wiki 두 유형은 `parse_only`다. 그래서 LightRAG 청크·벡터, 본체 추출, Neo4j를 하나도 쓰지 않는다(`document_service.py:681-682`, 주석 "llm-wiki KB 级互斥：llm-wiki 文档只解析产出 markdown，不写 LightRAG/Neo4j"(llm-wiki KB 단위 배타: llm-wiki 문서는 파싱으로 markdown만 내고 LightRAG/Neo4j에 쓰지 않는다)).
  - 삭제도 Neo4j 정리를 건너뛴다. "llm-wiki 文档从不写 Neo4j（parse_only 管线），跳过——纯多余调用"(llm-wiki 문서는 Neo4j에 쓴 적이 없어 건너뛴다, 순전히 쓸데없는 호출이다)(`document_service.py:2436-2438`).
- (a) 배타 자체를 왜 골랐는지 적은 원문은 찾지 못했다(grep `互斥|parse_only|LLM_WIKI_TYPES` 전체를 봤다).
- (a) 따라 나온 결정의 이유는 적혀 있다.
  - compiled schema를 건너뛰는 이유: "`auto_compile=True` 有副作用（凭空生成一份 ontology schema）… 否则一次 openkb 上传会顺手给这个库凭空造一份本体 schema（有副作用、且与它的产物口径无关）"(auto_compile=True에는 부작용이 있다. 근거 없이 본체 schema를 만든다. 그러면 openkb 업로드 한 번이 이 KB에 쓸데없는 본체 schema를 만든다. 부작용이고 산출물과도 무관하다)(`document_service.py:615-621`).
  - 업로드 때 `ontology_status=READY`로 두는 이유: "避免对账巡检前 30s 窗口内 ontology_status=PENDING … 导致前端显示误导的「知识抽取入库中」"(대사 순찰 전 30초 동안 PENDING이면 화면에 "지식 추출 중"이라고 잘못 나온다)(`document_service.py:758-765`). 같은 자리에 `emit_task=False`를 둔 이유는 "这条路径**没有跑过**知识抽取 … 落一行 extract/success 会让「知识抽取任务数」凭空多出来"(이 경로는 지식 추출을 돌지 않는다. extract/success 행을 남기면 지식 추출 작업 수가 근거 없이 늘어난다)다.
  - 엄격한 kb_type 조회 함수를 따로 둔 이유: "wiki 类文档的 `ontology_status` 被上传路径写成 `READY` —— 拿回落值去选「这一步的终态从哪一列看」时，一份 wiki 文档会落进 lightrag 那条分支、被当场判成「编译成功」，而 Wiki 根本没生成"(wiki 문서의 ontology_status는 READY라서, 기본값 lightrag로 떨어지면 wiki를 만들지도 않았는데 컴파일 성공으로 판정된다)(`kb_type_service.py:147-156`).
  - 프런트 규칙: "禁止用否定式判 kb_type（如 `kbType !== 'openkb'`）——三引擎下会把 jonex_wiki 误兜进 lightrag 桶"(부정형으로 kb_type을 판정하지 마라. 엔진이 셋이면 jonex_wiki가 lightrag 쪽으로 잘못 들어간다)(`frontends/core-business/src/utils/kbType.ts:4-7`).
- (a) 유지보수자가 밝힌 대가: 이슈 #31 답글(jonexai999, 2026-09-16). "The switch is `kb_type` (`lightrag | openkb`), not an ontology-specific flag … `kb_type` is immutable after KB creation, and `openkb` has no LightRAG vector index—what is lost is not just the graph, but vector retrieval itself."(스위치는 본체 전용 플래그가 아니라 kb_type이다. 생성 뒤 못 바꾸고, openkb에는 벡터 색인이 없다. 잃는 것은 그래프만이 아니라 벡터 검색 자체다.)
- (a) 화면 문구가 두 길을 다른 쓰임새로 나눈다. lightrag는 "适合实时问答"(실시간 질의응답에 맞음), openkb는 "适合知识沉淀与深度理解"(지식 축적과 깊은 이해에 맞음)(`zh.json:1524-1526`).
- (b) [추정] 배타의 이유는 세 가지로 보인다.
  - 첫째, LLM 비용이 두 배로 드는 것을 피한다. 한 문서에 본체 추출과 wiki 컴파일을 둘 다 돌리는 길이 없다.
  - 둘째, 문서 상태 기계를 하나로 둔다. lightrag는 `ontology_status`, wiki는 `llm_wiki_compile_status`가 컴파일 상태의 유일한 원천이다(`document_service.py:102-106`, 4묶음 판정 `2134-2160`).
  - 셋째, 화면이 두 길을 다른 쓰임새로 내놓는다.
  - 사례: 상태 열 분리 1곳, 화면 문구 1곳, 이슈 #31 답의 "coarser than expected"(생각보다 거친 스위치) 1곳. 비용에 대한 직접 근거는 없다.
- 대안:
  - 한 KB 안에서 문서마다 두 길을 다 돌리기.
  - KB에 본체 추출 on/off 플래그를 따로 두기. 이슈 #31이 바로 이 "per-KB toggle"을 물었다.
  - 같은 문서를 두 KB(lightrag 하나, wiki 하나)에 따로 올려 `search_mix`로 묶기. 지금 구조에서 가능한 유일한 우회다.
- 이력: "KB 级互斥" 문자열과 `kb_type_immutable`은 둘 다 `f6205dc`(2026-08-12)에 처음 나온다(`git log -S`). 그 커밋 메시지는 "the pipeline_type -> kb_type terms are now consistent everywhere"(pipeline_type을 kb_type으로 통일)라고 적는다. 3번째 엔진 `jonex_wiki`가 들어오면서 `LLM_WIKI_TYPES` 집합이 생겼다(`kb_type_service.py:1-5` "替代此前分散在 4 个 service … 中各写一份的 _get_pipeline_type"(서비스 4곳에 따로 쓰던 _get_pipeline_type을 대신한다)).

### J14. kb_type은 생성 뒤 바꿀 수 없다
- (a) "改类型意味着旧数据全部失效（openkb→lightrag 要清空 Wiki 重推 LightRAG；lightrag→openkb 要清空 Neo4j 重编译），没有安全的原地切换路径。如需更换请新建知识库。连旧名 pipeline_type 一起拦"(유형을 바꾸면 옛 데이터가 전부 무효가 된다. openkb→lightrag는 Wiki를 비우고 LightRAG에 다시 넣어야 하고, lightrag→openkb는 Neo4j를 비우고 다시 컴파일해야 한다. 안전한 제자리 전환 길이 없다. 바꾸려면 새 KB를 만든다. 옛 이름 pipeline_type도 같이 막는다)(`knowledge_info_service.py:439-452`).
- (a) 기본값도 같은 관문을 지난다. "缺省值也走同一道闸门：`kb_type` 创建后不可变，**不能替用户改选**成别的类型"(기본값도 같은 관문을 지난다. kb_type은 생성 뒤 바꿀 수 없으니 사용자 대신 다른 유형을 골라 줄 수 없다)(`kb_type_service.py:107`).

### J15. `KB_ENABLED_TYPES`는 "생성"만 막고, 갈래 나누기에는 쓰지 않는다
- (a) "**第三个只作用于「创建」一个动作** —— 它不参与任何链路分流判定，也**不隐藏存量库**"(세 번째 집합은 "생성"에만 작용한다. 어떤 갈래 판정에도 끼지 않고 기존 KB를 숨기지 않는다)(`kb_type_service.py:16-18`).
- (a) 모르는 값이 섞이면 설정 전체를 무효로 한다. 이유는 "静默丢一半的失败方式最难查：客户现场少显示一个选项，没人知道为什么"(조용히 절반을 버리는 실패가 가장 찾기 어렵다. 고객 현장에서 선택지 하나가 덜 보여도 아무도 이유를 모른다)(`kb_type_service.py:55-56`).

### J16. 엔진을 넘는 연결은 질의 시점에만 한다(search_mix)
- 사실: search_mix가 kb_type별로 묶어 각 엔진에 보내고, 인용을 doc_id로 합친 뒤 답을 융합한다(`search_service.py:8155-8420`).
- (a) 인용 병합 순서: "传入顺序即优先级 … 把证据更强的一侧放前面（OntoRAG 的 chunk 级引用带 locations，信息比派生引用多）"(넘긴 순서가 우선순위다. 근거가 더 강한 쪽을 앞에 둔다. OntoRAG의 chunk 단위 인용은 위치 정보가 있어 파생 인용보다 정보가 많다)(`search_service.py:7133-7138`).
- (a) jonex_wiki가 느리면 버린다. "最慢一路决定整体延迟，超时返回空 + 标记 source 降级，不拖垮 lightrag/openkb"(가장 느린 쪽이 전체 지연을 정한다. 시간 초과면 빈 결과 + source 강등 표시로 lightrag/openkb를 끌어내리지 않는다)(`search_service.py:490-492`, 기본 90초).
- 귀결(참고): 그래프 엔티티와 wiki 페이지 사이에 저장된 연결은 없다. 한 문서가 두 엔진에 동시에 들어갈 수 없으므로(J13), 새 문서와 옛 문서의 연결은 각 엔진 안에서만 생긴다.

### J17. 입수(ingest) 백엔드는 제출할 때 정해 문서 행에 고정한다
- (a) "一个按某个后端提交、还没跑完的文档，在开关翻转后必须继续从**当初那个**后端取状态。查询侧各读一次环境变量的写法，会在翻转那一刻把在途文档永远卡在 PARSING"(어떤 백엔드로 제출해 아직 안 끝난 문서는 스위치가 바뀐 뒤에도 원래 백엔드에서 상태를 읽어야 한다. 조회 쪽에서 환경 변수를 따로 읽으면 바뀌는 순간 진행 중 문서가 PARSING에 영원히 걸린다)(`capabilities/knowledge_base/services/ingest_backend.py:5-8`).
- 현재 등록된 백엔드는 `rag` 하나다(`ingest_backend.py:10, 26`). 문서 주석에 "spec §5.8 / D9"라는 내부 사양 번호가 있지만 문서는 없다.

### J18. OpenKB 모델 이름은 KB config.yaml에 보이게 두고, 전역 기본값으로 물러나지 않는다
- (a) 게이트웨이의 숨은 별칭 재작성을 없앴다. 이유는 둘이다. "① 模型名在 KB 的 config.yaml 里看不出真实值，不可审计；② 排查「模型名对不上」要跨三层"(① 실제 모델 이름이 KB config.yaml에서 안 보여 감사할 수 없다. ② 모델 이름 불일치를 찾으려면 세 층을 넘나들어야 한다)(`Reference/OpenKB/JONEX_CHANGES.md:127-129`).
- (a) `DEFAULT_LLM_MODEL` 기본값을 없앴다. 이유는 "这条回落**只会把「没配」这个一眼能看懂的错误，换成一个看不懂的上游错误**。故删除 —— 缺失即响亮失败"(이 기본값은 "설정 안 함"이라는 한눈에 보이는 오류를 알아볼 수 없는 upstream 오류로 바꿀 뿐이다. 그래서 지웠다. 없으면 크게 실패한다)(`JONEX_CHANGES.md:182-193`). 원인은 LiteLLM이 `provider/` 앞부분을 떼어 내는 것이다.
- 이력: §七(기본값 추가) → §九(같은 날 2026-10-08 밤에 뒤집음). 공개 이력에서는 `5fb1feb`에 한꺼번에 들어 있다.
- 관련 이슈: #34 "MODEL_ALIAS_MAP silently rewrites model names"(2026-09-15)가 같은 문제를 외부에서 보고했다. 2026-10-08 변경이 이 이슈를 해결했는지 이슈에 표시는 없다(열려 있음).

### J19. OpenKB 인용은 탐색 궤적에서 문서를 역산한다(B안)
- (a) J3 동기 1의 사례 2와 같다(`search_service.py:7157-7175`). 처음에는 A안("concept/entity 페이지는 인용에 넣지 않음")이었다가 B안으로 바꿨다. "概念性提问（「XX 是什么」）下 agent 往往只读 concepts/，A 会导致引用为零条——实测如此"(개념형 질문에서는 agent가 concepts/만 읽는 일이 많아 A안이면 인용이 0개가 된다. 실측도 그랬다).
- 근거 문서 `docs/openkb/llmwiki-reasoning/03-references-and-images.md`는 공개본에 없다.

### J20. 읽기 목차(outline)를 플랫폼 DB에서 엔진으로 내렸다
- (a) "目录功能（LLM 起草/调整/存储/自动触发）已整体下沉到 jonex_wiki 引擎 … 平台侧仅保留透传门面"(목차 기능(LLM 초안·조정·저장·자동 실행)을 통째로 jonex_wiki 엔진으로 내렸다. 플랫폼에는 그대로 전달하는 겉면만 남겼다)(`deploy/postgres/update/033_drop_wiki_outline.sql:6-8`).
- (a) 목차는 "纯展示投影，不参与检索"(순수 표시용 투영이고 검색에 쓰지 않는다)(`032_wiki_outline.sql:7-8`).
- 이력: 032(플랫폼 표 생성) → 033(DROP). 둘 다 `a8bee87`에 들어 있다.

### J21. thinking(추론 토큰)은 기본 off
- (a) "reasoning token **计入** max_tokens …, 实测 30 次查询里 9 次因思考把预算吃光 → stop_reason=model_output_truncated"(추론 토큰이 max_tokens에 포함된다. 실측 30회 질의 중 9회가 추론으로 예산을 다 써서 출력이 잘렸다)(`deploy/.env.jonex_wiki.example:100-101`).

### J22. 공개본에서 내부 설계 문서와 테스트를 뺐다
- (a) `CHANGELOG.md:20-22` "Internal planning documents, temporary comparison projects, and runtime artifacts from the public source tree"(내부 계획 문서, 임시 비교 프로젝트, 실행 산출물을 공개 소스에서 뺐다).
- `.gitignore:99-101`("Test files — keep local, never commit", `tests/unit/`), `.gitignore:307-312`(`/docs/*`, 단 `assets`·`dev`·`examples`만 남김).
- 그래서 JONEX_CHANGES §10.3이 "必须跑"(반드시 돌려라)라고 적은 `tests/unit/test_openkb_*.py`도, JonexWiki `pyproject.toml`의 `testpaths = ["tests"]`도 공개본에는 없다.
- 영향(참고): 이 갈래가 찾는 "왜"의 상당 부분이 공개본에서 빠졌다. 코드가 가리키는 계획 문서가 60종이 넘는다(grep `docs/…\.md` 결과).

## 4. 앞선 schema-glossary 보고서와 어긋나거나 보탤 점

앞선 보고서: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/reports/schema-glossary/yuezhiai-jonex.md`.

1. jonex_wiki 흐름 서술(그 보고서 33행 "원문 구절을 이해(understanding)한다. 사실(record)을 페이지에 배치(organization)한다")은 기본 `layered` 모드에만 맞는다. 엔진에는 논문식 `legacy` 모드(passage마다 SELECTPAGES + COMPILEWIKIPAGES를 한 번에)도 있고 설정으로 고른다(`settings.py:80-84`, `engine.py:68-71`). 모드가 컴파일 정체성에 들어가는 것도 빠져 있다.
2. 정체성 판정 순서(그 보고서 89-95행)는 identity.py 규칙을 옮긴 것이다. layered 조직은 identity.py가 "충분할 수 있다"고 한 "이름 + 맥락" 판정을 undetermined로 낮춘다(`organization.py:521-526`). 그래서 실제로는 그 보고서가 적은 것보다 한 단계 더 보수적이다. 같은 대상으로 확정되는 것은 명시 별칭·id뿐이고, 나머지는 bounded LLM 판정으로 간다.
3. 그 보고서는 jonex_wiki를 "TBox도 용어집도 없다"(33행)로만 적었다. 이 엔진이 arXiv 2605.25480(WeChat/Tencent) 논문 구현이라는 출처는 다루지 않았다. 이 출처가 jonex_wiki 설계 대부분(Error Book, k=5 페이지 선택, 구조·내용 검증)을 설명한다.
4. 그 보고서는 OpenKB를 entity_types 통제 어휘 관점으로만 봤다. Jonex가 OpenKB의 PageIndex/converter를 우회하고 `compile_short_doc`만 쓴다는 점(`openkb_adapter.py:940-943`)은 빠져 있다. OpenKB가 Jonex 안에서 "짧은 문서용 컴파일러"로만 쓰인다는 뜻이다.
5. 그 보고서 9행이 인용한 `llm_wiki_schema_service.py:1`의 docstring은 "kb_type=openkb 编译设置权威源"이다. 그런데 같은 서비스가 지금은 jonex_wiki도 다룬다(`llm_wiki_schema_service.py:233-245`, `apply_schema_to_engine`이 kb_type으로 나눔). 그 보고서 47행에 jonex_wiki 쪽이 적혀 있으므로 사실은 맞다. docstring이 낡았다는 점만 덧붙인다.
6. 그 보고서 116행 "출처당 링크 제안 상한은 4개(`organization.py:85`)"는 상수로는 맞다. 다만 understanding 쪽 주석은 "Historical constants; model output is no longer restricted by target counts"(옛 상수다. 모델 출력은 더 이상 대상 수로 제한되지 않는다)라고 적는다(`understanding.py:85`). 상한 4가 layered 경로에서 실제로 어디서 적용되는지는 이 갈래에서 확인하지 않았다(모르는 것 #6.4).
7. 그 보고서의 다른 줄 번호(`organization.py:85, 92-94, 158, 499-538`, `mention_index.py:20-22`, `identity.py:10-17`)는 같은 commit에서 다시 확인했고 맞았다.

## 5. 엔터프라이즈 다중 작성자 보고서 용도에 비춰

조건: 작성자마다 용어가 다르다. 형식 없는 문서가 섞인다. 여러 사람이 쓴다. 권한이 있다.

### 쓸 만한 장치
- 이해 → 조직 분리(J5): 원천 읽기 결과를 페이지 배치와 떼어 캐시한다. 그래서 용어집·페이지 구조를 바꿔도 원문을 다시 LLM에 묻지 않는다. 용어집을 자주 고칠 사내 환경에 바로 맞는다. 캐시 정체성에서 "페이지 배치"를 빼는 규칙(`understanding.py:22-26`)을 그대로 가져올 만하다.
- 보수적 정체성 + bounded 판정(J6): 작성자마다 같은 이름을 다른 대상에 쓰는 경우(예: 부서마다 "플랫폼"이 가리키는 것이 다름)에 이름만으로 합치지 않는다. 명시 별칭·id만 확정한다. 모호한 것은 상한이 있는 LLM 판정으로 넘기고, 그래도 안 되면 따로 둔다. 다만 jonex_wiki에는 사람이 관리하는 용어집 입력이 없다. 사내 용어집은 "원문이 선언한 별칭"과 같은 위치의 명시 증거로 넣는 길을 새로 만들어야 한다.
- claim 단위 근거 구간 + 결정적 검사(J7): 여러 사람이 쓴 보고서에서 수치·날짜·부정이 섞여 왜곡되는 것을 코드로 막는다. 감사 가능한 인용(문자 구간)이 남아 검토자가 원문을 바로 확인할 수 있다.
- 형식 없는 문서 대응(J10·J11): 망가진 단위만 격리하고 원문을 보관한다. 표 머리글은 병합 셀 증거가 있을 때만 승격한다. 사내 엑셀·스캔 PDF에 필요한 방어다.
- 불변 bundle + 발행 관문(J9): 한 사람이 문서를 잘못 올려 페이지가 급감해도 이전 판으로 계속 서비스한다. 지운 원천이 낡은 페이지로 남지 않는다.
- 거부·누락을 기록으로 남기기(J8): "조용히 사라지는 사실"을 없앤다. 사람이 Error Book을 보고 원인을 고칠 수 있다.
- 권한·테넌트: 플랫폼 쪽에 KB 단위 RBAC(viewer/editor/kb_manager)와 테넌트 격리가 있다(`41e1ff3`, `a8eb6f6` 커밋 메시지 17번 항목). wiki 엔진 호출에도 `X-Tenant-ID`를 넘긴다(`.env.jonex_wiki.example:14-16`). 다만 수정 Apache 라이선스가 다중 테넌트 운영에 서면 허가를 요구한다(`LICENSE:6`). 코드를 옮겨 쓰면 이 조항에 걸리고, 설계만 참고하면 걸리지 않는다.

### 걸리는 점
- 엔진 배타(J13): 한 문서를 그래프와 wiki에 동시에 넣을 수 없다. 사용자 목표 "raw들을 연결할 수 있는 구조"를 그래프 엔티티와 wiki 페이지 양쪽으로 잇는 저장된 다리가 없다. 질의 때 융합(J16)만 있다. 우리 설계에서는 하나의 원천 기여 장부를 두고 그래프와 wiki가 같은 장부를 투영하는 쪽이 낫다. JonexWiki의 `SourceContributionRecord` 개념을 엔진 사이로 넓히는 것이다.
- KB 단위 재컴파일: 문서 하나만 올려도 KB 전체 revision을 만든다. 증분 재사용이 있지만 organization·발행 꼬리는 KB 전체를 다시 돈다. 문서 수천 건 규모의 비용은 공개 수치가 없다(모르는 것 #6.3).
- 용어 불일치를 직접 다루는 장치가 wiki 길에는 없다. 그래프 길의 동의어 묶음(canonical + terms)은 wiki 엔진에 전달되지 않는다. jonex_wiki 설정은 "편집 선호" 문구 하나뿐이다(J12).
- 근거 문서·테스트가 비공개라서 수치 근거(예: layered가 legacy보다 얼마나 나은지)를 확인할 수 없다(J22).
- OpenKB 경로는 우리 용도에 약하다. 인용이 문서 단위이고, 재컴파일 때 페이지가 중복된다는 외부 보고가 있고(#22, 확인 안 됨), PageIndex도 우회한다.

## 6. 모르는 것과, 무엇을 보면 알 수 있나

1. JonexWiki를 따로 만든 공식 이유. 무엇을 보면 아는가: 비공개 `docs/jonex_wiki/*.md`, `docs/llm-wiki-plus/*`. 또는 yuezhiai 팀의 블로그·발표(jonex.ai). 이번 웹 검색으로는 찾지 못했다. Trendshift에 "YZGlobal/jonex"라는 다른 이름 목록이 있었지만, `gh api repos/YZGlobal/jonex`는 404였다.
2. 그래프/wiki 배타를 고른 이유(비용·상태 기계·제품 위치 가운데 무엇인지). 무엇을 보면 아는가: 비공개 `docs/llmwiki-schema-settings-execution-plan.md`, "方案 §15"가 가리키는 llm-wiki 연동 계획 문서. 또는 이슈로 직접 묻기.
3. layered와 legacy의 품질·비용 비교 수치. 무엇을 보면 아는가: 비공개 테스트·평가 보고서. 엔진 telemetry 키(`layered_understanding_*`, `engine.py:1246-1263`)를 실제 배포에서 모으면 잴 수 있다. 코드 실행 금지라 이번에는 하지 않았다.
4. `MAX_SOURCE_LINK_TARGETS = 4`가 layered 경로에서 실제로 적용되는 위치. 무엇을 보면 아는가: `organization.py`에서 이 상수를 쓰는 곳 전부, `understanding.py:80-95`. compile 갈래 몫으로 넘긴다.
5. 논문 저자(WeChat, Tencent)와 Jonex 팀의 관계, 원 코드 `engines/llm_wiki_plus/`의 출처. 무엇을 보면 아는가: 논문 후속 버전의 코드 링크, 저자 GitHub, `lwp-arch-001` 같은 내부 이름이 다른 공개 저장소에 있는지.
6. vendored OpenKB가 upstream 0.4.5와 정확히 어디가 다른지. 무엇을 보면 아는가: PyPI `openkb==0.4.5` sdist를 스크래치 디렉터리에 내려 diff를 뜨면 된다. 이 갈래에서는 하지 않았다. `[jonex]` 표식이 없는 변경이 최소 1곳 있다(J1).
7. 이슈 #22(OpenKB 재컴파일 중복 concept 페이지)가 사실인지. 무엇을 보면 아는가: `Reference/OpenKB/openkb/agent/compiler.py`의 concepts plan과 slug 충돌 처리. OpenKB 갈래 몫이다.
8. `f6205dc` 이전 내부 이력(OpenKB를 2026-07-30에 vendoring, 내부 hash `5cec22c4`·`fae774d2`·`74b76989`·`32cefb4a`). 무엇을 보면 아는가: 비공개 원본 저장소. 공개본은 squash돼 있다.

## 7. 다른 갈래와의 경계(깊게 들어가지 않은 곳)
- JonexWiki compile 내부(understanding·organization 프롬프트 본문, Error Book 항목 필드, structural 검사 목록, rendering frontmatter): compile 갈래 몫이다. 여기서는 docstring의 이유만 썼다.
- JonexWiki 질의(`domain/engine/query/**`, S2G-RAG controller arXiv 2604.23783 인용 `models/query_models.py:340`): 질의 갈래 몫이다.
- OpenKB 컴파일러 본문(`compiler.py` 2,372줄): OpenKB 갈래 몫이다. 헤더와 `compile_short_doc` 서명만 봤다.
- 그래프 길(native_ontology_extractor, synonym, Neo4j): 앞선 schema-glossary 보고서와 그래프 갈래 몫이다.

## 8. 출처 목록(이 노트가 직접 쓴 외부 자료)
- GitHub 메타데이터: `gh repo view yuezhiai/jonex`. 생성 2026-07-19, stars 1,344, forks 240, topics에 llm-wiki·ontology·graph-rag, license "Other".
- 이슈: #22 https://github.com/yuezhiai/jonex/issues/22 , #31 https://github.com/yuezhiai/jonex/issues/31 (유지보수자 답글 2026-09-16), #34 https://github.com/yuezhiai/jonex/issues/34 . PR은 5개이고 모두 wiki와 무관하다(#2~#6).
- 논문: https://arxiv.org/abs/2605.25480 , https://arxiv.org/html/2605.25480v2
- OpenKB upstream: https://github.com/VectifyAI/OpenKB (vendored README `Reference/OpenKB/README.md:14-52`)
- Trendshift 목록(YZGlobal/jonex): https://trendshift.io/repositories/84889 (확인 못 한 다른 이름)

# jonex · JonexWiki compile 갈래 노트

JonexWiki의 compile은 원문을 "검증된 사실(claim) 장부"로 먼저 만들고, wiki 페이지는 그 장부를 코드로 투영한 결과로 다룬다.
기본 모드(`layered`)에서 LLM은 원문 구절을 읽어 원문 그대로의 발췌(excerpt)를 고르는 일만 하고, 페이지 본문은 그 발췌를 글머리표로 이어 붙인 것이다.
같은 대상 판정은 "이름이 같다"를 증거로 치지 않아서, 출처가 다르면 기본적으로 페이지를 따로 둔다.
legacy 모드는 Tencent WeChat 논문(arXiv 2605.25480)의 Algorithm 1·Error Book을 거의 그대로 옮긴 것이고, layered 모드는 그 위에 "읽기"와 "배치"를 떼어 낸 jonex 자체 개조다.

## 읽는 법

| 표기 | 뜻 |
|---|---|
| `C/` | `Reference/JonexWiki/src/jonex_wiki/domain/engine/compile/` (레포 루트 기준) |
| `M/` | `Reference/JonexWiki/src/jonex_wiki/domain/engine/models/` |
| `SP/` | `C/source_prep/` |
| `JW/` | `Reference/JonexWiki/src/jonex_wiki/` (갈래 범위 밖, 경계 확인용) |
| commit | 모든 인용은 HEAD `5571db5`. JonexWiki 전체가 commit `a8bee87` 하나로 들어와서(`git log -- Reference/JonexWiki` 결과 1개) 이력으로 바뀐 이유를 추적할 수 없다 |
| legacy / layered | compile 모드 두 가지. 기본값은 `layered` (`C/engine.py:398`, `JW/infra/settings.py:84`, `Reference/JonexWiki/.env.example:212`) |
| passage | 파서가 만든 블록 하나 = LLM 호출 하나의 입력 단위 (`M/compiler_state.py:385-424` `ArchivedPassage`) |
| claim | 페이지에 실린 사실 한 줄과 그 근거 (`C/content_validation.py:154-239` `ValidatedClaim`) |
| contribution record | 페이지 경로를 뺀 사실 한 건 (`C/source_contribution.py:131-153`) |
| 주석 속 `S5`, `S6.1`, `S7-B`, `AC-006`, `Wave 3 P0.3`, `lwp-arch-001` | 공개되지 않은 내부 계획서의 단계 번호. `CHANGELOG.md:22` "Internal planning documents ... removed from the public source tree" |

읽은 깊이: 아래 "읽은 범위" 표에 파일마다 `끝까지` / `훑음`을 적었다.
레포 코드는 실행하지 않았다. 한글 토큰화 확인 한 번만 레포 정규식 문자열을 내 스크립트에 옮겨 돌렸다(`python3 -I -c` 로 정규식 리터럴만 실행).

## 논문 출처

legacy 경로의 뼈대는 논문 "Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki"(Ming, Li, Wu, Que — WeChat, Tencent Inc., arXiv 2605.25480, 2026-05-25)의 Algorithm 1이다.
코드는 논문 이름을 적지 않고 "Paper-required facts fixed here"라고만 쓴다(`M/compiler_state.py:8-14`, `C/content_validation.py:11-20`, `C/rendering.py:9-18`, `C/structural.py:9-15`).

[추정] jonex가 구현한 논문은 2605.25480이다(사례 5개: 함수 이름 `SELECTPAGES`/`COMPILEWIKIPAGES`(`M/compiler_state.py:3-4`), 선택 상한 k=5(`M/compiler_state.py:30`), Error Book 항목 필드 "phenomenon, root cause, constraint, verification"(`C/error_book.py:290-303`), 최종 3라운드 수리(`C/error_book.py:1263`), 10 batch마다 재검증(`C/error_book.py:1114` 기본값 10, `C/engine.py:321` `llmReviewEveryBatches: 10`)).

논문 쪽 사실(https://arxiv.org/html/2605.25480 를 WebFetch로 읽음):
- 구절마다 SelectPages(최대 k=5) → CompileWikiPages(active constraints 포함) → 구조·내용 검증 → 오류면 Error Book 갱신·constraint 재계산·코드 auto-fix → 적용.
- Error Book 항목은 "the error phenomenon, root cause analysis, generated constraint rule, verification method"와 open/closed 상태를 갖고 `error_book.yaml`에 저장한다. "All open constraint rules are appended to the Step 2 compilation prompt."
- 내용 검증은 논문에서 LLM 기반(unsupported fact, cross-page contradiction)이다.
- Error Book ablation: 빼면 F1이 HotpotQA 0.839→0.801, MuSiQue 0.739→0.699, 2WikiMHQA 0.911→0.877.
- 논문은 같은 이름 페이지의 동일성·병합을 다루지 않는다. k=5의 이유도 적지 않는다.

jonex가 논문에서 바꾼 것은 "#설계 결정과 이유"의 D1, D3, D5, D9에 있다.

## 읽은 범위

| 파일 | 줄 수 | 깊이 | 역할 |
|---|---|---|---|
| `C/engine.py` | 1772 | 끝까지 (query 메서드 1587-1772는 훑음) | 오케스트레이터. 모드 분기·이전 bundle 재사용·발행 꼬리 |
| `C/pipeline.py` | 1304 | 끝까지 | legacy 실행: passage 스케줄러(stream/window), 병합, claim 정책, revision id |
| `C/error_book.py` | 1336 | 끝까지 | Error Book 모델, 발견→기록→constraint, 수리 라운드, 3라운드 finalize |
| `C/repair/acceptance.py` | 781 | 끝까지 | legacy의 passage 1건 처리(LLM 호출과 gate 전부) |
| `C/repair/blocking.py` | 232 | 끝까지 | 후보 페이지 점수(결정적), semantic review 발동 조건, state 얕은 복사 |
| `C/repair/planner.py` | 103 | 끝까지 | 메시지 조립, 출력 token 예산 |
| `C/repair/mutation.py` | 123 | 끝까지 | 경로 오타 보정 |
| `C/understanding.py` | 1314 | 끝까지 | layered 1단: 원문 이해 + checkpoint 캐시 |
| `C/organization.py` | 1223 | 끝까지 | layered 2단: 페이지 배치, 동일성 판정, bounded window |
| `C/identity.py` | 258 | 끝까지 | 같은 대상 판정 규칙 |
| `C/source_contribution.py` | 612 | 끝까지 | 페이지 독립 사실 장부와 출처 철회 |
| `C/content_validation.py` | 868 | 끝까지 | evidence gate (발췌 위치 찾기, SourceSpan 고정) |
| `M/claim.py` | 681 | 끝까지 | 결정적 지지 판정(SUPPORTED/REFUTED/NOT_ENOUGH_INFO) |
| `M/compiler_state.py` | 635 | 끝까지 | 상태·페이지·경로 자료 구조 |
| `M/repair_models.py` | 191 | 끝까지 | legacy 응답 스키마 |
| `C/relation_increment.py` | 567 | 끝까지 | link 결정(navigation / supported_relation / pending) |
| `C/mention_index.py` | 240 | 끝까지 | 읽기 API용 backlink·mention 색인 |
| `C/publication.py` | 274 | 끝까지 | 원문 구간 보관(keep-and-search), Error Book 재조정 |
| `C/rendering.py` | 619 | 끝까지 | Markdown 렌더, 디렉터리 shard |
| `C/structural.py` | 740 | 앞 220줄·링크 검사·repair 읽음, 트리 비교 본문은 훑음 | 구조 gate |
| `C/incremental.py` | 441 | 자료 구조와 `plan_mutation_impact` 읽음 | 렌더 의존 색인(증분 컴파일이 아니라 증분 렌더) |
| `C/block_replay.py` | 99 | 끝까지 | legacy 증분: 바뀌지 않은 블록 claim 재검증 |
| `C/digest.py` | 171 | 끝까지 | source fingerprint, 변경 분류 |
| `C/omission_repair.py` | 371 | 끝까지 | 확인된 누락을 원문 발췌로 덧붙이는 결정적 수리 |
| `C/coverage_diagnostic.py` | 342 | 끝까지 | 질문 기준 누락 진단(4층) |
| `C/build_identity.py` | 16 | 끝까지 | 코드 트리 checksum |
| `C/bundle.py`, `C/bundle_codec.py` | 508, 1381 | 훑음 (파일 목록·`PreviousBundle`) | 불변 bundle 쓰기/읽기. 저장 갈래와 경계 |
| `C/table_views.py`, `C/raw_collection.py`, `C/html_evidence.py`, `C/dense_units.py` | 648, 377, 55, 75 | 훑음 (docstring·함수 목록) | 표 보기 페이지, 원문 페이지, HTML 표 인용 위치, 임베딩 |
| `SP/blocks.py`, `SP/chunking.py`, `SP/screening.py`, `SP/inspect.py`, `SP/classify.py`, `SP/direct_ingest.py`, `SP/source_archive.py`, `SP/raw_manifest.py` | 375, 453, 187, 195, 92, 146, 89, 46 | 끝까지 | 파싱 결과 → 블록 → passage |
| `SP/tables.py`, `SP/table_artifact.py`, `SP/spreadsheet_view.py`, `SP/header_interpretation.py`, `SP/reading_materials.py` | 118, 404, 411, 472, 436 | 훑음 | 표 격자 저장·머리글 해석·읽기 자료 목록 |
| `M/query_models.py`, `util/*` | 357, 261 | 훑음 | query 쪽 모델·호출 배관. compile과 공유하는 것은 `PageIndexEntry`·`RawWikiPage` 정도 |

경계(다른 갈래 몫, 깊이 안 들어감): `JW/domain/compile_task.py`(페이지 급감 차단·발행 lock), `JW/adapters/model_port.py`(json_schema→json_object 강등), `JW/domain/parsing/*`(source_prep 호출자), `engine/query/*`(검색·답변), `JW/storage/*`.

## 모듈 지도

```
JW/domain/compile_task.py  ──▶  C/engine.py  LLMWikiV1Engine.compile
                                   │  (fingerprint·이전 bundle 재사용 판단)
                ┌──────────────────┴───────────────────┐
        compile_mode=layered (기본)              compile_mode=legacy
   _layered_compile (engine.py:1118)        _full_compile / _incremental_compile
     ├ understanding.UnderstandingStage        └ pipeline.compile_passages
     │    └ understand_one_passage  [LLM]           └ error_book.run_compiler_batch
     │    └ build_understanding                         └ repair/acceptance.run_algorithm1_batch
     │         └ content_validation.validate_claim_evidence     ├ repair/blocking.derive_page_candidates
     └ organization.organize_sources                            ├ select_and_compile          [LLM]
          └ Organizer.add / _determined_target                  ├ triage / 재시도              [LLM]
               └ identity.decide_identity                       ├ content_validation + structural
          └ Organizer.resolve_identity          [LLM]          └ semantic_review (기본 off)   [LLM]
          └ Organizer.materialize → content_validation      └ run_error_repair_round        [LLM]
     └ source_contribution.reconcile_publication          └ finalize_error_book (3라운드)  [LLM 조건부]
     └ _finalize_layered → error_book.finalize_error_book
                └────────────── 공통 발행 꼬리 ──────────────┘
   omission_repair.apply_confirmed_omissions (확인서가 있을 때만)
   relation_increment.project_state_relations
   rendering.stabilize_directory_shards
   publication.reconcile_claim_issues · query.retrieval.build_query_corpus
   pipeline.enforce_claim_policy · lexical/dense 색인 [임베딩 호출]
   source_contribution 장부 · derive_revision_id · bundle_codec.iter_bundle_files
   발행 부모 재확인 → store.stage_revision
```

공통 꼬리가 한 벌인 이유는 작성자가 밝혔다: `C/engine.py:701-705` "relations, link resolution, query corpus, indexes, immutable Bundle staging and publication are the *same* code for both modes (S7.2). Layered does not get its own copy of the engine." — 발행 기준이 두 모드에서 갈라지지 않게 하려는 것이다.

## 자료 구조

### 상태와 페이지

| 모델 | 위치 | 핵심 필드 | 메모 |
|---|---|---|---|
| `CompilerState` | `M/compiler_state.py:486-564` | `batch_number`, `pages{path→WikiPageSnapshot}`, `index{path→PageIndexEntry}`, `source_archive{passage_id→ArchivedPassage}`, `processed_passage_ids`, `active_constraints`, `passage_failures`, `claim_compilation_dispositions`, `recovered_retries`, `directory_shards`; private `_rendered_wiki_files`, `_publication`, `_fact_mentions` | `index[path]`는 `pages[path].index`와 같아야 한다(543-546). private 필드는 bundle에 직렬화되지 않는다(502-507) |
| `ArchivedPassage` | `M/compiler_state.py:385-424` | `passage_id`, `source_id`, `document_id`, `chunk_id`, `text`, `context_text`, `sha256`, `position`, `source_metadata` | "`context_text` ... must never be used as evidence because it can contain text from a neighbouring interval" (388-392) |
| `PageIndexEntry` | `M/compiler_state.py:159-222` | `path`, `title`(≤200), `aliases`(≤20), `tags`(≤20), `description`(500자에서 자름), `why_visit`(120자), `object_id`, `scope`, `fields`, `limitations`, `capabilities`, `interpretation_status` | 긴 description은 거절이 아니라 자른다: "LLM 常生成长描述，截断而非拒绝" (190) — LLM이 긴 설명을 자주 내므로 거절 대신 자른다 |
| `WikiPageSnapshot` | `M/compiler_state.py:259-300` | `index`, `content`, `related_pages`, `links[PageLink]`, `link_mentions[LinkMention]`, `source_ids`, `version` | `source_ids`의 뜻이 모드마다 다르다(legacy는 passage id, layered는 source id). "#설계 결정과 이유" 아래 "참고" 참조 |
| `PageLink` | `M/compiler_state.py:239-256` | `relation`, `target_id`(정규 경로), `why_visit`, `evidence_refs`, `kind ∈ {navigation, supported_relation}` | |
| `LinkMention` | `M/compiler_state.py:231-236` | `target_mention`(이름 문자열), `why_visit`, `evidence_refs`, `relation` | LLM이 내는 것은 경로가 아니라 이름이다 |
| 경로 규칙 | `M/compiler_state.py:43-140` | 소문자 kebab ASCII, `category/name.md`, ≤240자, `_index` 예약 | `normalize_wiki_path`는 LLM 출력을 관대하게 고치되 경로 탈출은 거절한다(44-50) |

### 근거와 claim

| 모델 | 위치 | 핵심 필드 |
|---|---|---|
| `EvidenceRef` | `C/content_validation.py:114-130` | `passage_id`, `source_id`, `document_id`, `chunk_id`, `excerpt`(≤4000자) |
| `SourceSpan` | `M/compiler_state.py:427-483` | 위 id 4개 + `source_sha256`, `passage_text_sha256`, `start_char`(포함), `end_char`(미포함), `text`. frozen. `len(text)==end-start` 검사 |
| `ClaimDraft` | `C/content_validation.py:133-151` | `page_path`, `text`, `evidence`(1~20) |
| `ValidatedClaim` | `C/content_validation.py:154-239` | `claim_id`(= sha256(page_path, text, 정렬된 evidence)[:24], 490-507), `evidence`, `unresolved_evidence`, `source_spans`, `support_status`, `support_reason`. SUPPORTED/REFUTED는 span 필수, SUPPORTED는 unresolved 금지(216-239) |
| `SourceContributionRecord` | `C/source_contribution.py:131-153` | `record_id`(= 출처 버전+span 위치+정규화 명제의 해시, 70-89), `proposition`, `normalized_proposition`, `evidence`, `source_spans`, `unresolved_evidence`, `qualifiers[{kind,value}]`, `entity_mentions`, `topic_hint`, `original_names{정규형→원표기}`, `link_proposals`, `support_status/reason`, `displays[(page_path, claim_id)]`, `provenance{필드→출처}`, `unbound` |
| `SourceContributionSet` | `C/source_contribution.py:179-204` | `records`, `by_source`, `fact_index{정규 명제→record_ids}`, `source_versions`, `rebuilt_from_legacy` |

`claim_id`는 페이지 경로를 품고 `record_id`는 품지 않는다.
작성자 이유: `C/source_contribution.py:3-6` "The same source fact shown on two pages therefore has two unrelated identities, and removing one page deletes 'the fact' as far as the compiler can tell." — 그래서 페이지를 빼낸 장부를 따로 둔다.

### layered 전용

| 모델 | 위치 | 핵심 필드 |
|---|---|---|
| `UnderstandingFact` | `C/understanding.py:141-171` | `excerpt`, `topic_hint`, `original_names`, `aliases`, `notes`, `mentions`, `relations[{kind,subject,target}]`, `unbound` |
| `SourceUnderstandingCheckpoint` | `C/understanding.py:197-234` | `cache_key`, `tenant_id`, `kb_id`, passage·source·document·chunk id, `content_generation`, `artifact_sha256`, `text_sha256`, `parser_id/version`, `asset_digest`, `prompt_version/checksum`, `schema_version`, `understanding_model`, `config_fingerprint`, `support_rule`, `produced_at`, `records`, `facts_seen`, `facts_accepted`, `rejected_reasons` |
| `NameForm` | `C/identity.py:50-75` | `name`, `kind ∈ {entity, topic}`, `context`, `explicit_id`, `aliases`, `relations{kind→[target]}`, `page_path` |
| `IdentityCandidate` | `C/identity.py:78-89` | `left`, `right`, `decision ∈ {same, different, undetermined}`, `basis`, `context_match`, `relation`, `score` |
| `LayeredCompilation` | `C/organization.py:189-233` | `state`, `claims`, `contributions`, 각종 계수(pages_reused, identity_judgments 등) |

### Error Book

| 모델 | 위치 | 핵심 필드 |
|---|---|---|
| `ErrorBookEntry` | `C/error_book.py:290-375` | `id`(= sha256(category, code, phenomenon, affected_paths)[:24], 545-557), `category`(8종, 60-69), `code`, `phenomenon`, `error_class ∈ {Blocking, Quarantine, Advisory, Transient}`, `root_cause`, `constraint`, `verification`, `affected_paths/claim_ids/source_ids/passage_ids`, `first/last_seen_batch`, `status ∈ {open, closed}`, `rule_version`, `source_versions`, `omission_*` 5개, `resolution`, `repair_history`(최근 20개, 853) |
| `ErrorRepairProposal` | `C/error_book.py:400-446` | `resolved_error_ids`(1~100), `mutations`(update/delete만, ≤10), `claims` |

### legacy 응답 스키마

| 모델 | 위치 | 메모 |
|---|---|---|
| `CombinedCompileResponse` | `M/repair_models.py:118-130` | `selection` + `proposal`. "Collapses SELECTPAGES + COMPILEWIKIPAGES into a single model call per passage (2 → 1)" |
| `PageSelection` | `M/compiler_state.py:348-382` | `existing_paths`(≤5), `new_pages`(≤5) |
| `CompileProposal` | `M/repair_models.py:79-115` | `mutations`(≤10), `claims`(≤100) |
| `PageMutation` | `M/repair_models.py:37-76` | `operation ∈ {create, update, delete, facts}` |
| `NoClaimDecision` | `M/repair_models.py:133-159` | `accept_source_only`는 `model_protocol_failure`와 짝지을 수 없다 |

## 동작 흐름

### 0. 원문 준비 (source_prep, 파싱 시점)

호출자는 compile이 아니라 `JW/domain/parsing/parse_task.py`다(`grep "source_prep\."` 결과). 출력은 `ParseResult.blocks` → `SourceArtifact` 목록이고(`SP/blocks.py:156-215`), compile은 이것을 passage로 바꾼다(`C/pipeline.py:364-406`).

| 단계 | 입력 → 출력 | 위치 | 결정적 검사 |
|---|---|---|---|
| 경로 분류 | 파일 확장자 → `TEXT_DIRECT` / `STRUCTURED_DIRECT` / `SPREADSHEET_NATIVE` / `MINERU` | `SP/classify.py:58-75` | 확장자와 컨테이너 머리 바이트 충돌 거절(78-92) |
| MinerU 항목 → 블록 | content_list 항목 → 텍스트는 `pack_text`, 표는 `table_observation` 블록 | `SP/blocks.py:232-297` | 표 블록에 `compile_table_values: False` (272) |
| 직접 형식 | json/jsonl/csv/tsv는 레코드·행 단위 unit, csv는 Markdown 표로 직렬화 | `SP/direct_ingest.py:20-133` | 레코드를 넘어 합치지 않음(35) |
| 구조 단위 식별 | 본문 → code / html_table / table / text 단위 | `SP/chunking.py:147-191` | |
| 체검(screening) | 패킹 예산을 넘을 단위만 빼고 원문은 `source-archive/`에 보관 | `SP/screening.py:56-99`, `SP/source_archive.py`(파일 3-17줄 docstring) | 규칙은 "패킹이 터지는가" 하나 |
| 패킹 | 단위 → 블록(목표 4000, 상한 5000 추정 token, 문자 상한 32000) | `SP/chunking.py:35-49, 198-453` | 표는 머리글을 조각마다 반복, 앞 문단(≤256 token)·뒤 각주를 한정어로 붙임(314-364). 긴 문단은 강제 분할하고 앞부분을 `contextual_text`로 붙임(386-394) |

token 추정은 "ASCII 4자=1, 비ASCII 1자=1"이다(`SP/chunking.py:29-32`). 한글은 1자=1 token으로 센다.

표는 LLM compile에 들어가지 않는다.
`table_observation` 블록은 `compile_table_values: False`라서 passage 순서에서 빠지고(`C/pipeline.py:424`, `C/understanding.py:1108-1111`) `tables.sqlite`·표 보기 페이지·원문 페이지로만 발행된다(`C/raw_collection.py`, `C/table_views.py` 훑음).

### 1. 엔진 진입 (`C/engine.py:364-1015`)

| 순서 | 무엇 | 위치 |
|---|---|---|
| 1 | `compile_mode` 확정, 모르는 값은 예외 | 393-404 |
| 2 | source마다 fingerprint 1개(모든 청크 텍스트·메타·prompt checksum·manifest checksum·엔진 id·출력 token 예산 포함) | `C/digest.py:73-124`, 엔진 340-361 |
| 3 | 1차 revision id | 442-459 |
| 4 | 이전 bundle이 있고 inventory·runtime·manifest가 같으면 무결성 검사 후 원문을 다시 읽어 재확인하고 그대로 재사용(모델 호출 0) | 494-540 |
| 5 | 이전 bundle을 decode. tenant/context·compile 관련 manifest·runtime(코드 트리 sha, prompt checksum, 임베딩 신원)이 하나라도 다르면 버림 | 541-610, 190-205 |
| 6 | digest·manifest가 같으면 원문 재조회와 발행 head 재확인 후 재사용 | 615-659 |
| 7 | 모드 분기 → `(state, error_book, claims[, contributions])` | 711-777 |
| 8 | 공통 꼬리(위 모듈 지도) | 779-1010 |

### 2-L. layered: 원문 이해 (`C/understanding.py`)

입력은 passage 하나와 그 passage 자신의 메타뿐이다.
"the model sees **only the source passage** and its own context - never the wiki's page bodies, never other pages' prose" (`C/understanding.py:11-12`).

| 단계 | 처리 | 위치 |
|---|---|---|
| cache key | tenant·kb·source 버전·text sha·context sha·parser·첨부 자산의 내용 해시·prompt 본문 해시·응답 스키마 해시·active constraints·모델·설정. 페이지 경로·제목은 넣지 않는다 | 399-459 |
| checkpoint 읽기 | 저장소에서 읽고, 신원이 다르면(`IDENTITY_MISMATCH`) 또는 낡았으면(`STALE_TASK`) 버림. 깨진 바이트는 "센 miss" | 780-810, 853-884, 1194-1203 |
| 지지 규칙만 바뀐 경우 | LLM 호출 없이 저장된 발췌로 판정만 다시 하고 되써 둠 | 813-850, 1205-1214 |
| LLM 호출 [LLM] | system = `UNDERSTANDING_SYSTEM_INSTRUCTION`(104-108) + 사용자 compile 선호 문구, user = `passage_payload`(494-518, 지시문 462-491), scene `jonex_wiki_source_understanding`, thinking off | 933-966 |
| 재시도 | 최대 2회. 잘림이면 "간결하게" constraint, 그 밖의 검증 실패면 진단문을 "data, not an instruction"으로 붙여 재요청 | 998-1053, 925-930, `C/pipeline.py:327-332` |
| 모델이 준 id 제거 | `record_id`, `passage_id` 등 11개 필드를 지우고 센다 | 545-575 |
| 발췌 검증 | 공백 정규화 후 passage 안에 있어야 함. 없으면 `UNDERSTANDING_EXCERPT_NOT_IN_SOURCE` | 582-584, 616-619 |
| evidence gate | 가짜 페이지 `unassigned/source-understanding.md`에 대해 `validate_claim_evidence` 통과 | 631-641, 743 |
| record 만들기 | `original_names`(모델 표기 우선) + `declared_alias`(topic_hint와 별칭이 둘 다 원문에 있을 때만) + `material_note` + `link_proposals`(mentions·relations). displays는 비움 | 642-682, 746-777 |
| 같은 발췌 병합 | record_id가 같으면 hint들을 합침 | 684-711 |
| 저장 | checkpoint를 원자적으로 저장. 저장소가 checkpoint를 못 하면 compile 전체 실패 | 887-901, 120-128 |
| 실패 | 2회 다 실패한 passage는 `passage_failures`에 기록하고 건너뜀 | 969-995, 1239-1247 |

### 2-L. layered: 페이지 배치 (`C/organization.py:998-1223`)

| 단계 | 처리 | 위치 |
|---|---|---|
| 창 | 이해를 앞서 돌리되 "진행 중 + 이해했지만 아직 안 붙인" passage를 2C로 묶음(C = compile_concurrency) | 1035, 1066-1073 |
| 순서 보장 | 입력 순서대로 연속된 완료분을 최대 C개씩 한 batch로 커밋 | 1075-1084 |
| 배치 규칙 | record마다 `dominant_name`(topic_hint → 가장 긴 원표기 → 대문자 연속 → 명제 80자) → `_determined_target` | 295-315, 499-538, 566-587 |
| 동일성 LLM 판정 [LLM] | 규칙이 미정으로 남긴 case를 8개씩 한 호출에, 후보 페이지 ≤4개, compile당 호출 ≤8회. scene `jonex_wiki_compile_organization_identity`, max_tokens 1200 | 92-94, 599-657, 669-759 |
| 판정 반영 | `same`이면서 제시한 후보 경로를 정확히 댈 때만 합침. `different`/`undetermined`/오류/상한 초과는 모두 독립 페이지 | 740-758, 640-647 |
| 재사용 | 이전 발행에서 그 페이지의 모든 출처가 그대로이고 record 집합이 똑같으면 스냅숏을 그대로 씀 | 982-995, 1113-1122 |
| materialize | 페이지마다 record를 evidence gate에 다시 통과시키고(결과는 키로 캐시) 본문 = claim 텍스트 글머리표 | 761-841, 350-409 |
| 커밋 | lock 안에서는 version 확인과 쓰기만 | 946-979, 1124-1130 |
| 끝 | `processed_passage_ids`, `passage_failures` 기록 → 실패율 gate | 1176-1222 |

이어서 엔진이 장부를 이전 장부와 재조정하고, 원문을 한 번 더 읽어 바뀌었으면 실패시키고, legacy와 같은 finalize를 돌린다(`C/engine.py:1306-1363`).

### 2-G. legacy: passage 1건 (`C/repair/acceptance.py:152-781`)

| 단계 | 처리 | LLM | 위치 |
|---|---|---|---|
| 사전 검사 | 중복·미보관·이미 처리된 passage id면 예외 | | 170-179 |
| 후보 페이지 | 페이지 메타(title×8, alias×6, tag×4, description×3)와 passage 토큰 겹침 점수, 상위 50 + 원문에 정확히 나온 사실 이름의 페이지 | | `C/repair/blocking.py:258-265, 368-414` |
| hybrid 후보 | 모듈 `candidate_retrieval`이 없으면 결정적 점수로 대체 | | 279-299. 레포에 해당 파일 없음(`find -name 'candidate_retrieval*'` 결과 0) |
| 선택+컴파일 | payload: `stage=select_and_compile`, instructions(323-338), passage, 후보 목록, 후보 페이지 메타(본문 제외, ≤12), active_constraints. scene `jonex_wiki_compile_page_edit`, 출력 ≤16384 token | 예 | 310-353, `C/repair/planner.py:84-88` |
| 응답 보정 | `mutation.path`와 `page.index.path` 오타 차이를 같은 부모·12자 이상·편집거리 ≤4일 때만 고침 | | `C/repair/mutation.py:154-226` |
| 선택 해석 | 후보 아닌 기존 경로·충돌하는 새 경로는 걸러냄(전체 실패 아님) | | `M/compiler_state.py:585-619` |
| 빈 선택 | 40자 미만이면 출처만 보관. 그 이상이면 triage 호출 → 재시도 1회 → 여전히 비면 실패 기록 | 예(triage, 재시도) | 370-466, 225-274 |
| 빈 proposal | 한 번 더 `compile_wiki_pages` 호출 | 예 | 470-503 |
| facts 물질화 | `facts` mutation을 기존 페이지 본문 뒤에 claim 텍스트를 덧붙이는 update/create로 바꿈 | | 505-558 |
| 대상 gate | 선택 안 한 기존 페이지 수정(`UNSEEN_OVERWRITE`), 없는 대상 등 | | 560-594, `C/structural.py:128-213` |
| 후보 상태·렌더·구조 검증 | 영향받는 산출물만 증분 렌더하고 검증 | | 596-628, `C/incremental.py:337-430` |
| evidence gate | | | 630 |
| semantic review | 숫자·표·같은 페이지 상충일 때만(`selective`) 또는 항상. 기본은 `off` | 예(조건부) | 632-712, `C/repair/blocking.py:282-288` |
| 수용 | 구조 검증 통과 + `CLAIM_PAGE_MISSING` 없음. evidence 미해결·semantic findings는 막지 않음 | | 714-719 |
| 수용 후 | `_fact_mentions`(이름→페이지) 갱신 | | 720-726 |

passage마다 2회까지 시도하고(`C/pipeline.py:796`), 그래도 안 되면 원인 분류(`legitimate_no_claim`, `duplicate_covered`, `evidence_rejected`, `model_protocol_failure`)를 남기고 건너뛴다(`C/pipeline.py:863-897`).

### 2-G. legacy: Error Book 고리 (`C/error_book.py:1104-1234`)

1. passage 결과의 구조·내용 issue를 `discover_errors`로 안정 id의 발견으로 바꾼다(560-601).
2. 새 발견에 원인·constraint·검증 문구를 붙인다. 논문은 LLM이 원인을 분석하지만 jonex는 문자열 틀로 채운다(1180-1187).
3. `record_discoveries`로 기록하고 `open_constraints`(Blocking 우선, Quarantine은 code당 1개, 최대 12개)를 다음 passage의 `active_constraints`로 넘긴다(609-718, 1194).
4. batch 번호가 `repair_interval`의 배수이고 open Blocking이 있으면 수리 라운드 1회(1198-1213). 병렬 스케줄러는 batch별 수리를 미루고 병합 지점에서 1회 돈다(`C/pipeline.py:1139-1155, 1249-1264`).
5. 수리 라운드: open Blocking 항목과 영향 페이지 스냅숏을 보내 `ErrorRepairProposal`을 받는다(scene `jonex_wiki_compile_repair`, 939-950). 해결한다고 한 id가 open이어야 하고 mutation 경로가 그 항목의 `affected_paths` 안이어야 한다(726-814). 구조·근거 검증 + 조건부 semantic review(scene `jonex_wiki_compile_review`)를 통과해야만 닫는다(1012-1077).
6. 끝에 3라운드 finalize. open Blocking이 없으면 라운드는 LLM을 부르지 않는다(900-919, 1242-1310). 발행 가능 = 전체 트리 구조 검증 통과 + open Blocking 없음(1299-1301).

### 3. 증분 재컴파일

| 경우 | layered | legacy |
|---|---|---|
| 입력이 하나도 안 바뀜 | revision 통째 재사용, 모델 호출 0 (`C/engine.py:494-540, 615-659`) | 같음 |
| 일부 source 바뀜 | 바뀌지 않은 passage는 checkpoint hit라 이해 LLM 호출 0. 배치는 매번 처음부터 다시 돌고(`Organizer()`가 새로 생김, `C/organization.py:1036`), 출처가 모두 그대로이고 record 집합이 같은 페이지만 스냅숏 재사용 | `replay_blocks`: 옛 passage와 새 passage를 의미 키(source·document·text·위치 뺀 메타·context)로 1:1 짝짓고, 짝지은 passage의 claim만 새 아카이브에 다시 검증. 페이지 본문은 남은 claim으로 다시 쓰고 related/links는 비움. 짝 없는 passage만 다시 컴파일 (`C/block_replay.py` 파일 16-34, 38-98줄) |
| 동일성 판정 | 매 compile마다 미정 case를 다시 LLM에 물음. 판정 결과를 저장하는 곳이 없다(`C/organization.py:441`의 `_deferred`는 메모리 dict, 656에서 비움) | 해당 없음(LLM이 후보 중 페이지를 고름) |
| 출처 삭제 | 그 출처만 낸 record는 철회되고 Error Book에 Advisory로 남김. 다른 출처가 받치는 record는 남음(`C/source_contribution.py:384-508`, `C/engine.py:74-111`) | 같은 장부를 claim에서 유도해 재조정(`C/engine.py:869-890`) |
| 경합 | 원문을 발행 직전에 다시 읽어 바뀌었으면 실패(`C/engine.py:1335-1348`), 발행 head가 부모와 다르면 거절(964-993) | 같음 |

`C/incremental.py`는 이름과 달리 증분 컴파일이 아니라 증분 렌더용 의존 색인이다(`C/incremental.py:1-7`).

### 4. 링크

링크는 세 층이다.

| 층 | 무엇 | 대상 결정 | 위치 |
|---|---|---|---|
| 제안 | LLM이 낸 `target_mention`(이름)·why_visit·evidence_refs·relation | LLM은 경로를 못 정함 | `C/relation_increment.py:3-5`, `C/understanding.py:746-777` |
| 결정(발행되는 links/related) | 이름을 정규화해 페이지 제목·별칭과 맞춤. 그 이름의 페이지가 정확히 하나일 때만 연결, 없으면 pending(클릭 불가) | `_target_index` | `C/relation_increment.py:111-124, 169-245` |
| 관계 승격 | `supported_relation`은 원문 span에 "{주어 제목} is the {relation} of {대상 제목}." 문장이 통째로 있고 지지 판정을 통과할 때만. 아니면 navigation으로 강등하고 근거를 떼어 냄 | `_relation_supported` | `C/relation_increment.py:138-166, 192-195` |
| 읽기 색인 | 페이지 본문에 다른 페이지 제목·별칭(≥3자, ASCII는 단어 경계)이 처음 나온 곳을 mention으로, `links`를 역방향 in_link로 | 같은 이름이면 그 이름의 모든 페이지에 mention | `C/mention_index.py:94-240` |

관계 종류는 다섯 개로 닫혀 있다: predecessor, successor, parent, subsidiary, brand(`C/identity.py:35`).

### 5. 발행 꼬리의 결정적 검사

| 검사 | 막는가 | 위치 |
|---|---|---|
| 확인된 누락 수리 | 확인서가 있을 때만. 원문 구간을 그대로 덧붙이고 3중 검증(원문 결합·보임·기존 내용 유지) | `C/omission_repair.py:211-228, 287-352` |
| 관계 투영 | 막지 않음 | `C/relation_increment.py:530-567` |
| `reconcile_claim_issues` | SUPPORTED 아닌 claim = Quarantine(검색 코퍼스에서 빠짐), claim 없는 passage = Advisory | `C/publication.py:207-274`, 48-52 |
| `enforce_claim_policy` | `benchmark`면 실질 passage(40자 이상)에 SUPPORTED claim이 하나도 없을 때 실패, `production`이면 degraded로 기록하고 발행 | `C/pipeline.py:290-314` |
| 실패율 | `benchmark`에서만 5% 초과 시 실패 | `C/pipeline.py:606-669` |
| 장부의 끊긴 display | 발행 claim에 없는 display는 떼고 Error Book에 기록 | `C/engine.py:114-150, 891-893` |
| 원문 보관 | 모든 passage 구간을 `source-evidence/` 페이지로(keep-and-search) | `C/publication.py:134-148` |
| 페이지 급감 | 경계(범위 밖): 원문 수가 늘었는데 페이지가 50% 넘게 줄면 발행 거절 | `JW/domain/compile_task.py`의 runner 4단계 |

## LLM 호출 지점 모음

| 모드 | stage / scene | 출력 스키마 | 기본 상태 | 위치 |
|---|---|---|---|---|
| layered | `understand_source` / `jonex_wiki_source_understanding` | `SourceUnderstandingResponse` | 켜짐, passage당 1~2회, 캐시됨 | `C/understanding.py:933-966` |
| layered | `identity_assignment` / `jonex_wiki_compile_organization_identity` | `_ORGANIZATION_JUDGMENT_SCHEMA` | 미정 case가 있을 때, compile당 ≤8회 | `C/organization.py:669-721` |
| legacy | `select_and_compile` / `jonex_wiki_compile_page_edit` | `CombinedCompileResponse` | passage당 1회(+재시도) | `C/repair/acceptance.py:318-353` |
| legacy | `claim_failure_triage` / `jonex_wiki_compile_triage` | `NoClaimDecision` | 빈 선택일 때 | 240-266 |
| legacy | `compile_wiki_pages` / `jonex_wiki_compile_pages` | `CompileProposal` | 빈 proposal일 때 | 478-503 |
| legacy | `semantic_review` / `jonex_wiki_compile_review` | `SemanticReview` | 기본 off | 671-682 |
| 둘 다 | `repair_error_book` / `jonex_wiki_compile_repair` | `ErrorRepairProposal` | open Blocking이 있을 때 | `C/error_book.py:939-950` |
| 둘 다 | `repair_semantic_review` / `jonex_wiki_compile_review` | `SemanticReview` | 수리 제안이 claim을 낼 때 | 1030-1041 |
| 둘 다 | 임베딩 / `jonex_wiki_compile_embed` | 벡터 | `QUERY_DENSE` off면 생략 | `C/engine.py:1074-1116` |

프롬프트는 파일이 아니라 코드 상수다.
system 골격 `COMPILE_MAIN_SKELETON`(`JW/domain/prompts.py:59-72`)에 사용자가 고칠 수 있는 "编译偏好"(compile 선호) suffix만 붙는다(같은 파일 18-26, 55-58). 그 밖의 18개 프롬프트는 "引擎正确性约束，冻结"(엔진 정확성 제약이라 동결) 상태다(18-26).
모든 compile 호출은 `thinking={"type": "disabled"}`다(`C/repair/planner.py:77`, `C/understanding.py:960`, `C/error_book.py:525`).

## 설계 결정과 이유

### D1. 읽기와 배치를 떼어 낸다 (layered)

- 결정: 원문 이해(페이지 모름)와 페이지 배치(코드 규칙 + 제한된 LLM)를 두 단계로 나누고, 이해 결과를 페이지와 무관한 key로 캐시한다.
- (a) "a page layout change re-asks the model about unchanged source text, and a failed page organization throws away a perfectly good reading of the source" (`C/understanding.py:3-7`) — legacy처럼 한 호출에 둘을 묶으면 배치가 바뀔 때마다 같은 원문을 다시 읽히고, 배치 실패가 좋은 읽기까지 버린다.
- (a) "page paths, page titles and target-page choices are deliberately absent from the cache identity, so reorganising pages never invalidates source understanding" (`C/understanding.py:115-117`).
- 대안: legacy의 결합 호출(`M/repair_models.py:118-130`). layered는 기본값이지만 legacy는 남아 있고 모드 전환은 이전 bundle을 무효로 한다 — "legacy and layered compile different things, so switching modes must invalidate a previous bundle" (`C/engine.py:68-71`).
- 이력: 공개 이력에는 바뀐 commit이 없다. 주석의 단계 번호로 보면 legacy(AC-00x) → layered(S7.x) 순서다.

### D2. 페이지 본문을 LLM이 쓰지 않는다

- 결정(layered): 본문 = evidence gate를 통과한 원문 발췌의 글머리표 목록. 순서는 입력 순서.
- (a) "No LLM rewrites the page: the body is the ordered list of the claims the evidence gate already accepted, one bullet each" (`C/organization.py:361-364`).
- 결정(legacy): 프롬프트가 "Do not output page prose or repeat old facts. The compiler appends admitted facts itself." (`C/repair/acceptance.py:325-327`)
- (a) 원문 변경 시: "Draft page prose is discarded on a source change: published facts are the source-grounded claims, not an old model-written paragraph." (`C/block_replay.py` 파일 42-43줄)
- 대안: Karpathy 원형처럼 LLM이 페이지를 요약·재작성. 포기한 것: 읽기 좋은 문장, 여러 출처를 엮은 요약.

### D3. 지지 판정을 결정적 규칙으로 (논문은 LLM)

- 결정: claim은 원문 발췌의 정확한 부분 문자열(대소문자·공백·문장부호 접기)이거나 좁은 변형이어야 SUPPORTED. 날짜·숫자·단위·부정·비교 방향은 "보호 원자"로 따로 대조한다.
- (a) "The checker intentionally proves a small, auditable language instead of pretending to solve unrestricted natural-language inference. ... Anything outside those bounded rules is NOT_ENOUGH_INFO." (`M/claim.py:3-8`)
- (a) 보호 원자를 둔 이유: "收入为15万元" collapses into "收入为1.5万元" and "支持离线部署" collapses into "官方明确否认支持离线部署" (`M/claim.py:214-222`) — 문장부호를 지우면 15만 위안이 1.5만 위안과 겹치고, "지원한다"가 "공식적으로 지원을 부인했다" 안에 들어가 버린다.
- (a) 버전 기록: "claim-support-v1 was the punctuation-folded substring fast path without protected-atom checks" (`M/claim.py:28-34`) → 현재 `claim-support-v3`. v1에서 보호 원자 검사를 더한 것이 확인된 변경이다(commit은 공개 이력에 없음).
- 논문과의 차이: 논문은 내용 검증을 LLM 기반으로 둔다. jonex는 semantic review를 남겨 두되 기본값이 off다(`C/repair/blocking.py:283`, `.env.example:172`).
- 대안: NLI 모델, LLM 판정. 포기한 것: 바꿔 말한 사실, 여러 문장에서 추론한 사실은 NOT_ENOUGH_INFO로 남아 검색 코퍼스에서 빠진다.

### D4. 같은 대상은 증명될 때만 합친다

- 결정: 판정 순서 = 명시 id > 관계(선행/후속/모회사/자회사/브랜드)면 다름 > 이름이나 선언 별칭 + 같은 context면 같음 > 나머지 미정(`C/identity.py:101-130`). layered 배치에서는 "이름 + 같은 context"도 미정으로 낮춘다(`C/organization.py:520-526`).
- (a) "a bare name match across different contexts is *undetermined* - two cities with one name are not one entity" (`C/identity.py:11-12`), "nothing is merged automatically" (15).
- (a) 낮춘 이유: "Matching source qualifiers may be only a year or a unit. They do not establish that two cross-source entities are one." (`C/organization.py:521-522`)
- (a) "Co-occurring names (including regex-extracted mentions) never assert identity. Only source understanding's explicit, subject-bound aliases do." (`C/organization.py:158-159`)
- (a) "Relations that look like names are not names: a predecessor, successor, parent, subsidiary or brand stays a relation and never becomes an alias." (`C/identity.py:17-18`)
- 미정은 제한된 LLM 판정으로: (a) "The bound is what keeps 'semantic organization' from becoming an unbounded classification pass." (`C/organization.py:90-91`)
- 대안: 이름 일치 병합(jonex 그래프 길이 하는 방식), 임베딩 유사도. `lexical_candidates`(`C/identity.py:143-162`)는 정의만 있고 부르는 곳이 없다(`grep` 결과 identity.py 밖 0건).
- 포기한 것: 출처를 넘어선 자동 통합. "#엔터프라이즈 용도에 비춘 평가"에서 결과를 따진다.

### D5. 페이지 경로를 (출처, 이름)의 해시로

- 결정: `pages/<읽을 수 있는 ASCII>-<sha256(source_id, 정규화 이름)[:12]>.md`.
- (a) "the wiki path normalizer slugs non-ASCII characters away, so a name-only readable part would let two different Chinese names from one source collide onto one page -- a silent merge." (`C/organization.py:279-283`)
- 결과: 같은 이름이라도 출처가 다르면 처음에는 다른 경로다. 출처를 넘은 합침은 D4의 판정을 거쳐야만 일어난다.
- 대안: 이름 slug만(충돌), LLM이 고른 경로(legacy). 포기한 것: 사람이 읽을 수 있는 경로(한글·한자 이름은 해시만 남는다).

### D6. 모델이 준 신원은 믿지 않는다

- (a) "the program assigns every identity - record_id, passage/source/document ids, versions, evidence references - and never trusts a model-supplied id" (`C/understanding.py:16-17`), 지우는 필드 목록 545-575.
- (a) legacy 쪽: "The model cannot know the internal passage/document ids it must cite, so its identity fields are unreliable. Locate the excerpt within the SAME document only — a coincidental sentence match in a different document must never rebind the evidence to the wrong source." (`C/content_validation.py:532-535`)
- (a) 링크: "A model may propose a *mention*, a reason to visit and the evidence it saw; it may not name an identity." (`C/relation_increment.py:3-4`)

### D7. Error Book을 등급으로 나누고 Blocking만 발행을 막는다

- 결정: Blocking(발행 차단·수리 대상) / Quarantine(검색 코퍼스에서 제외) / Advisory(기록만) / Transient(제자리 재시도).
- (a) "A dangling link and a malformed page are both structural issues, but only the latter must stop publication." (`C/error_book.py:71-75`)
- (a) 등급은 코드가 정한다: "The mapping is deterministic and code-based so a model cannot downgrade a hard structural failure by returning a friendly attribution." (`C/error_book.py:84-86`)
- (a) 옛 bundle 항목은 Blocking으로 읽는다: "intentionally Blocking so old bundles fail safe" (`C/error_book.py:297-299`).
- (a) 끝 정리: "none of these should force a three-round global repair of an otherwise valid wiki" (`C/error_book.py:1295-1298`).
- 논문과의 차이: 논문은 등급이 없다(WebFetch 요약 기준).

### D8. 원인 분석을 LLM에 묻지 않는다

- (a) "The detector already supplies a typed category, object and reason. Preserve that finding; a second model call cannot prove its cause." (`C/error_book.py:1181-1182`) — 논문의 "root cause analysis" 단계를 틀 문구로 바꿨다.
- `ErrorAttributionBatch` 모델(`C/error_book.py:260-271`)은 남아 있지만 부르는 곳이 없다. 예전에 LLM 귀속 호출이 있었다는 흔적이다 [추정] (사례 1개: 쓰이지 않는 스키마).

### D9. constraint 주입은 상한을 둔다

- (a) "One representative rule per Quarantine code is then injected so recurring grounding errors influence later batches without sending thousands of instance rows to every model call. Advisory and Transient findings remain operational records, not prompt rules." (`C/error_book.py:700-704`), 상한 12.
- 참고: layered에서는 이 고리가 돌지 않는다. `build_state`가 `active_constraints=[]`로 시작하고(`C/pipeline.py:431`) layered는 Error Book을 constraint로 되먹이는 코드가 없다(`grep active_constraints` 결과 understanding.py는 state 값을 읽기만 함). 논문의 핵심 장치(ablation 3.4~4.0 F1)가 기본 모드에서는 빠져 있다.

### D10. passage 하나 = LLM 호출 하나

- (a) "Physical batching removed (§14 de-batching): every passage issues its own complete() call so scene → call-site stays one-to-one." (`C/engine.py:672-673`)
- (a) 선택과 컴파일을 한 호출로: "Collapses SELECTPAGES + COMPILEWIKIPAGES into a single model call per passage (2 → 1)" (`M/repair_models.py:122-123`). 논문은 두 단계다.

### D11. 실패를 passage 단위로 가둔다

- (a) "Per-passage tolerance matters under a real LLM: a single noisy rejection must not discard an hours-long compile." (`C/pipeline.py:716-717`)
- (a) "Catch them here so one malformed mutation does not abort the whole gather and make the durable worker repeat thousands of already successful passages." (`C/pipeline.py:786-789`)
- (a) production은 degraded로도 발행: "publishing degraded is a policy decision, not a silent one" (`C/pipeline.py:619-621`). 반대로 layered는 설명 안 된 실패를 허용하지 않는다: "Publishing a wiki that is silently missing a contribution the failure gate never saw is exactly the dishonesty the layered contract forbids" (`C/organization.py:250-253`).
- (a) 빈 응답을 쉽게 "근거 없음"으로 받지 않는다: 트리아지 지시문 "Never judge source-only merely because the first model response was empty." (`C/repair/acceptance.py:252-253`)

### D12. 체검은 "패킹이 터지는가" 하나만 본다

- (a) "一份 296 页文档里某个 OCR 退化的表格行有 6,933 字符，守卫把整份文档判死，而真正该做的是把那一个单元挡在编译面之外、其余照常编译" (`SP/inspect.py:3-5`) — 296쪽 문서의 OCR 깨진 표 한 행(6,933자) 때문에 문서 전체가 실패했고, 그 단위 하나만 빼야 했다.
- (a) 범위를 일부러 좁힘: "内容质量类问题（空表、复读、乱码……）不进这里" (`SP/inspect.py:12-15`) — 빈 표·반복·깨진 글자 같은 품질 문제는 여기서 다루지 않는다. 판정 v1→v2에서 빈 표·반복 판정을 지웠다(`SP/inspect.py:33-35`).
- (a) 뺀 것은 버리지 않고 원문 구간을 보관: 사람이 오판을 확인하고 나중에 VLM 판정으로 다시 돌릴 수 있게(`SP/source_archive.py` 파일 3-6줄).

### D13. 누락 수리는 사람 확인 뒤, LLM 없이

- (a) "it exists for exactly one situation: a *confirmed* compile omission - the source holds the information, the generated page does not express it, and someone verified that against the original content" (`C/omission_repair.py:3-7`), "No model is called anywhere in this module" (22-23).
- (a) 진단은 후보만 낸다: "A missing answer is not automatically a compilation omission: the source may never have contained the information, the page may exist unread, or the text may have been delivered and the answer still wrong." (`C/coverage_diagnostic.py:11-14`)
- 참고: 확인서를 넘기는 생산 경로가 없다. `omission_confirmations`는 `compile_task.py`가 넘기지 않고(`grep` 결과 compile 폴더 밖 0건) 기본값 `()`다(`C/engine.py:382`).

### D14. 재사용은 재확인 뒤에만

- (a) "'Unchanged' is a claim about the input this run read. Returning the previous revision republishes it, so the claim is re-proved before it is made" (`C/engine.py:621-626`).
- (a) "a newer publication that landed meanwhile makes it a refusal below, never an overwrite of someone else's revision with an older one" (`C/engine.py:625-626`), "a store that cannot report its head is counted as unavailable rather than assumed safe" (968-969).
- (a) 스케줄 손잡이는 revision 신원에서 뺀다: "调并发/调度器/失败率容忍/修复间隔都不该让上一版 bundle 作废(那会把一次配置调整变成全量重编)" (`C/engine.py:58-60`) — 동시성·스케줄러 같은 설정을 바꿨다고 전체를 다시 컴파일하면 안 된다.

### D15. 메모리 때문에 상태를 얕게 복사

- (a) "A full deep copy here was repeated once per passage worker and exhausted the 8 GiB cgroup on full corpora." (`C/error_book.py:1137-1139`), 같은 이유 `C/repair/blocking.py:315-323`, `C/pipeline.py:1271-1275`.

### D16. 스케줄러: stream 기본, window는 되돌리기용

- (a) window는 "A slow passage in a window forces the whole window to wait (barrier)" (`C/pipeline.py:725-726`), stream은 "Stream snapshot freshness is therefore closer to serial than window" (731-732).
- (a) 같은 세대 snapshot을 본 batch끼리만 병합: "merging while a same-generation passage is still in flight would leave it with a stale snapshot base and the merge would corrupt page deletions" (`C/pipeline.py:1229-1231`).
- (a) 기본값을 엔진에 두지 않음: "两份默认值:改了一处、另一处静默生效,谁也看不见(2026-09-17 的模板/默认值漂移就是这么来的)" (`C/pipeline.py:86-90`) — 기본값이 두 곳에 있으면 한쪽만 바뀌어 아무도 모르게 어긋난다.

### 참고: 작성자가 이유를 적지 않은 것

| 결정 | 위치 | 모르는 것 / 볼 곳 |
|---|---|---|
| 실질 passage 기준 40자 | `C/content_validation.py:53` | 왜 40인지 없음. 내부 계획서(공개 안 됨) |
| 후보 메타 가중치 8/6/4/3 | `C/repair/blocking.py:262-265` | 근거 수치 없음 |
| 동일성 판정 상한 4·8·8 | `C/organization.py:92-94` | 상한 이유는 있으나(90-91) 숫자 근거 없음 |
| 관계 종류 5개로 닫음 | `C/identity.py:35` | 왜 이 다섯인지 없음 |
| 기본 repair_interval 50 (논문 10, 함수 기본 10) | `C/pipeline.py:94`, `C/error_book.py:1114`, `.env.example:206` | 50으로 늘린 이유 없음 |
| `source_ids` 의미가 모드마다 다름 | legacy `C/repair/acceptance.py:543-546`(passage id), `C/block_replay.py` 파일 92줄(passage id), layered `C/organization.py:373-374`(source id) | 의도인지 결함인지 없음. 렌더 결과 `## Sources`에 그대로 찍힌다(`C/rendering.py:456`) |

## 앞선 보고서와 어긋나는 점

대상: `llm-wiki-implementations/lab/reports/schema-glossary/yuezhiai-jonex.md`의 jonex_wiki 관련 문장.

| 앞선 보고서 | 코드로 본 것 |
|---|---|
| "원문이 선언한 별칭·명시 id가 있으면 같다고 본다" (D절 3번) | 명시 id 경로는 쓰이지 않는다. `NameForm.explicit_id`를 채우는 곳이 identity.py 밖에 없다(`grep explicit_id` 결과 0). 선언 별칭만으로도 같다고 하지 않는다. 별칭 일치 + 같은 context 문자열이어야 SAME이고(`C/identity.py:122-126`), context가 다르면 미정이다(127-129). context는 결정적 추출기가 뽑은 기간·퍼센트·금액·단위와 모델 notes를 이어 붙인 문자열이다(`C/organization.py:174-179`, `C/source_contribution.py:51-56`) |
| "묶음당 LLM 판단 1회(후보 4개, 컴파일당 8회 상한)" | 한 호출에 case 8개까지, 한 batch에 case가 8개를 넘으면 호출을 더 한다. 상한 8은 compile 전체의 호출 수다(`C/organization.py:625-635`). 그래서 compile당 판정되는 case는 최대 64개다 |
| "출처당 링크 제안 상한은 4개다(organization.py:85)" | 상수는 있으나 쓰이지 않는다. `mention_limits`는 중복·자기 링크만 걸러 낸다(`C/organization.py:318-347`). `M/compiler_state.py:225-226` "Historical constants kept for old callers; navigation no longer enforces these cardinality limits." `MAX_UNDERSTANDING_FACTS = 24`도 config 해시에만 들어가고 응답 스키마를 제한하지 않는다(`C/understanding.py:81, 915`, `SourceUnderstandingResponse` 174-194에 상한 없음) |
| "판정 순서 ... 1. 같은 출처가 자기 페이지를 이어 쓴다 2. 빈 페이지가 하나뿐이면 ..." | 맞다(`C/organization.py:504-512`). 다만 2번은 "이미 record가 실린 페이지가 없을 때"라서 실제로는 legacy 잔재 페이지에만 해당한다 [추정] (사례 1개: layered 배치가 페이지를 만들 때 바로 record를 싣는다 `_assign` 589-597) |
| jonex_wiki의 mention 링크 = "처음 나온 곳 하나만 잇는다" | `mention_index`는 읽기 API용 색인이다. 발행되는 `links`/`related`는 `relation_increment`가 정하고, 그쪽은 이름이 페이지 하나에만 맞을 때만 연결한다(`C/relation_increment.py:123-124`). 두 층이 같은 이름에 다르게 반응한다(mention은 같은 제목 페이지 전부에 걸림 `C/mention_index.py:171-185, 219-222`) |
| "근거 검사기는 날짜·숫자·부정·비교를 보호 원자로" | 단위도 보호 원자다(`M/claim.py:127-167, 470-471`). 그리고 언어 범위가 영어·중국어뿐이다(부정어 `M/claim.py:90-98`, 날짜 형식 43-48, 토큰 정규식 36-39) |

## 엔터프라이즈 용도에 비춘 평가

조건: 작성자마다 같은 대상을 다른 용어로 쓴다, 형식 없는 문서가 섞인다, 여러 사람이 쓴다, 권한이 있다. 목표: "raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조".

### 쓸 만한 장치

| 장치 | 왜 맞는가 | 위치 |
|---|---|---|
| 페이지 독립 사실 장부(`record_id`가 출처 버전+위치+명제) | 보고서가 바뀌거나 지워질 때 그 출처의 사실만 철회되고, 다른 출처가 받치는 사실은 남는다. 여러 작성자 문서가 같은 사실을 말할 때 그대로 맞는다 | `C/source_contribution.py:70-89, 384-508` |
| 원문 구간 고정(`SourceSpan`) | 페이지의 모든 줄이 문자 구간까지 원문으로 돌아간다. "raw를 연결"의 가장 강한 형태 | `M/compiler_state.py:427-483`, `C/content_validation.py:446-487` |
| 이해 결과 캐시(페이지 배치와 무관한 key) | 동일성 규칙·배치 규칙을 고쳐도 LLM 재호출이 없다. 용어집을 나중에 넣어 배치를 다시 돌리는 운영에 맞다 | `C/understanding.py:399-459` |
| `original_names` / `declared_alias` 분리 | 원문 표기를 보존하고, "같은 문장에 함께 나온 이름"과 "원문이 별칭이라고 밝힌 이름"을 구분한다. 용어 불일치를 다룰 원료가 된다 | `C/understanding.py:650-667` |
| 관계는 별칭이 아니다 | "구 제품명→신 제품명", "모회사↔자회사"를 같은 페이지로 합치지 않는다 | `C/identity.py:17-18, 113-116` |
| 확신 없으면 따로 두기 + 그 횟수 세기 | 잘못 합친 것은 되돌리기 어렵고 따로 둔 것은 나중에 합칠 수 있다. `compile_organization_identity_unresolved` 계수가 사람 검토 대기열의 씨앗이 된다 | `C/organization.py:558-562` |
| 체검 + 원문 보관 | 형식 없는 문서(OCR 깨짐, 거대 표)가 전체 compile을 죽이지 않고, 뺀 부분이 남는다 | `SP/screening.py`, `SP/source_archive.py` |
| Error Book 등급 | 사람이 볼 것(Advisory·Quarantine)과 막을 것(Blocking)이 나뉜다 | `C/error_book.py:71-138` |
| 누락 수리의 "확인서" 계약 | 사람이 확인한 누락만 원문 그대로 덧붙인다. 사람이 끼어드는 지점이 계약으로 정해져 있다 | `C/omission_repair.py`, `C/coverage_diagnostic.py:292-327` |
| tenant·kb 신원을 캐시 key·bundle 소유 검사에 넣음 | 다른 테넌트의 checkpoint·bundle을 재사용하지 않는다 | `C/understanding.py:426-427, 796-797`, `C/engine.py:505-506, 1709-1710` |

### 걸리는 점

| 걸림 | 근거 | 영향 |
|---|---|---|
| 다른 용어는 후보조차 안 된다 | 배치 후보는 정규화한 이름·선언 별칭의 정확 일치뿐이다(`C/organization.py:454-497`). 퍼지·임베딩 후보 함수는 쓰이지 않는다(`C/identity.py:143-162`) | "매출"과 "수익"을 쓴 두 보고서는 서로 다른 페이지가 되고, LLM 판정에도 올라가지 않는다. 용어 불일치가 사용자 조건의 핵심이라 그대로는 연결을 못 찾는다 |
| 같은 이름도 출처가 다르면 대부분 갈라진다 | 결정적 SAME은 "별칭 + 같은 context 문자열"뿐이고(`C/identity.py:122-126`, `C/organization.py:520-526`), 나머지는 compile당 64 case까지만 LLM이 판정한다(`C/organization.py:92-94`) | 문서가 많은 KB에서는 대부분 독립 페이지로 남는다 [추정] (사례 1개: 상한 상수, 실측 수치 없음) |
| 갈라질수록 링크가 끊긴다 | 발행 링크는 이름에 맞는 페이지가 정확히 하나일 때만 연결되고 둘 이상이면 pending이다(`C/relation_increment.py:123-124, 200-203`) | 같은 이름 페이지가 출처별로 둘이 되면 그 이름으로 가는 링크가 오히려 사라진다. "새 데이터와 기존 데이터의 연결고리"와 정면으로 부딪힌다 |
| 동일성 판정이 저장되지 않는다 | 매 compile마다 미정 case를 다시 묻는다(`C/organization.py:441, 656, 1036`) | 비용이 반복되고, 같은 입력에서도 판정이 흔들리면 페이지 배치가 바뀔 수 있다 [추정] (사례 0개, 실행 안 함. 같은 KB를 두 번 compile해 `layered_organization_identity_judgment_applied` 계수와 페이지 목록을 비교하면 알 수 있다) |
| 한국어가 규칙 밖이다 | 후보 점수 토큰 `[a-z0-9]+|[一-鿿]`와 지지 판정 토큰 `...|[㐀-鿿]+`가 한글을 버린다(`C/repair/blocking.py:259`, `M/claim.py:36-39`; 내 스크립트로 정규식 리터럴만 실행해 `'삼성전자 매출 2024 增长'` → `['2024','增','长']` 확인). 부정어는 영어·중국어뿐(`M/claim.py:90-98`), 날짜는 ISO·年月日뿐(43-48), 결정적 개체 추출은 ASCII 대문자 연속뿐(`C/source_contribution.py:50`), 관계 승격은 영어 문장 틀(`C/relation_increment.py:155`), mention은 3자 이상(`C/mention_index.py:47`) | legacy 후보 점수는 한글 문서에서 0점이 된다. 지지 판정은 정확 부분 문자열 경로(`M/claim.py:614-621`, 한글도 `\w`라 접기는 됨)만 통한다. "않다/아니다" 부정은 보호되지 않는다. 2자 한글 이름(예: 회사 약칭)은 mention이 안 걸린다 |
| 페이지가 원문 발췌 목록이다 | `C/organization.py:361-364` | 사람이 읽는 보고서 요약이 아니다. 출처를 넘은 종합은 query 단계 몫이 된다 |
| 표는 compile에서 빠진다 | `SP/blocks.py:272`, `C/pipeline.py:424` | 표에 든 사실은 claim·페이지 링크가 되지 않는다(검색용 원문으로만 남음) |
| layered에서 Error Book 고리가 꺼져 있다 | "D9" 참고 | 논문이 효과를 잰 장치(ablation 3.4~4.0 F1)가 기본 모드에 없다 |
| 권한은 KB 단위다 | compile 신원은 tenant_id·context_id(=kb_id)뿐이다(`C/engine.py:364-383`). 문서별 열람 권한 필드는 compile 자료 구조에 없다. 삭제 문서는 질의 시점에 막는다(`JW/domain/source_visibility.py:18-23`, 범위 밖) | 한 KB 안에서 작성자·부서별 권한을 나누려면 KB를 쪼개야 한다. KB를 쪼개면 KB 사이 연결이 없다 |
| 라이선스 | 앞선 보고서 기준 Apache-2.0 수정판(다중 테넌트 운영·로고 제거에 서면 허가). LICENSE는 이 갈래에서 다시 읽지 않음 | 코드를 그대로 옮기기보다 설계를 참고해 다시 쓰는 쪽이 안전하다 |

### 차용 아이디어

1. 장부와 화면의 분리: 사실 장부(record_id = 출처 버전+위치+정규 명제)를 진실로 두고 페이지는 투영으로 만든다. 사람이 페이지를 손봐도 장부는 그대로다.
2. 이해 캐시 key에서 배치를 빼기: 용어집·동일성 규칙을 바꿔도 LLM 비용이 다시 들지 않게 한다.
3. 동일성 3값(same/different/undetermined)과 "미정은 따로 두고 센다": 미정 목록을 사람 승인 대기열로 바로 쓴다. jonex는 판정을 저장하지 않으므로 우리 쪽에서는 승인된 판정을 용어집처럼 저장해야 한다.
4. 미정 후보 생성을 넓히기: jonex가 막아 둔 퍼지·임베딩 후보(`lexical_candidates`)를 "후보 제안"으로만 살리면(자동 병합 없음) 용어 불일치를 찾는 장치가 된다.
5. 링크 해석을 "유일할 때만"에서 "모두에 걸되 모호 표시"로 바꾸기: jonex의 pending 처리는 갈라진 페이지를 서로 끊는다.
6. 체검과 원문 보관: 형식 없는 문서 대응으로 그대로 가져올 만하다.
7. 한국어 토큰·부정·날짜 규칙 추가: 결정적 판정을 가져온다면 필수다.

## 앞선 비교 문서 축에 대응

`llm-wiki-implementations/lab/reports/00-comparison.md` #설계 축별 스펙트럼의 축 이름을 따른다. 이 갈래가 본 부분만 적는다.

| 축 | JonexWiki compile |
|---|---|
| 2. 규칙의 위치 | 대부분 코드. 지지 판정·동일성·경로·링크 해석이 결정적. LLM은 발췌 고르기와 제한된 동일성 판정 |
| 4. Ingest | passage 단위, 표 제외, 체검 후 패킹 |
| 5. 근거 추적 단위 | 문자 구간(`SourceSpan`) + 출처 버전 해시 |
| 6. Link | LLM은 이름만 제안, 코드가 유일 일치로 해석, 관계는 원문 문장 일치로만 승격 |
| 7. Lint | 구조 gate·evidence gate·Error Book 등급 |
| 8. stale·모순 처리 | 출처 버전이 바뀌면 record 철회·재이해. 모순은 semantic review(기본 off)만 |
| 9. 사람 개입 | compile 선호 문구, 누락 확인서(생산 경로 미연결) |
| 10. 동시성·안전 | stream 스케줄러, 세대 단위 병합, 발행 부모 재확인 |
| 14. 규모·비용 | passage당 1~2회 호출, 캐시 hit면 0회, 동일성 판정 compile당 ≤8회 |

## 모르는 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| 주석의 S5~S7, AC-00x, Wave 3/4, §14 계획서 내용(결정의 원래 근거와 측정 수치) | 공개본에 없음(`CHANGELOG.md:22`). yuezhiai/jonex 이슈·토론(`gh issue list -R yuezhiai/jonex`)이나 저자 문의 |
| `candidate_retrieval` 모듈과 계획서 `docs/llm-wiki-plus/compiler-candidate-hybrid-retrieval-plan.md` | 레포에 없음. 비공개 저장소나 이후 공개 commit |
| layered가 legacy보다 품질이 나은지(F1 등) | 코드 주석에 "verified by A/B (F1 must not regress)"(`C/pipeline.py:735`)만 있고 수치 없음 |
| 실제 KB에서 동일성 미정 case가 몇 개이고 그중 몇 개가 판정되는지 | compile 로그의 `layered_organization_identity_judgments`·`compile_organization_identity_unresolved`·`..._judgment_limited` 계수(`C/engine.py:1264-1268`) |
| 같은 KB를 두 번 compile할 때 페이지 배치가 같은지 | 같은 입력으로 두 번 돌려 `state/compiler.json`의 pages 키 비교 |
| `source_ids` 의미 불일치가 의도인지 | 저자 문의, 또는 query 쪽에서 `source_ids`를 어떻게 읽는지(다른 갈래) |
| `.env.example:171-172` 주석은 "[默认: selective]"인데 값과 코드 기본은 off인 이유 | 운영 기록. 어느 쪽이 의도인지 코드만으로는 모름 |
| 논문의 k=5 근거와 Error Book 외 장치별 효과 | 논문 본문(PDF 텍스트 추출 실패. pdftotext가 없음). 다른 환경에서 PDF 본문 확인 |
| `LayeredCompilation` docstring "This stage never reuses a previous publication"(`C/organization.py:228-233`)이 `pages_reused`(207)와 어긋나는 것 | docstring이 S7-B 이전 문장이 남은 것으로 보이지만 [추정] (사례 1개) 이력이 없어 확인 불가 |
| LICENSE 추가 조항의 정확한 문구 | `LICENSE` 직접 읽기(이 갈래에서는 안 읽음) |

## 출처

- 저장소: https://github.com/yuezhiai/jonex, HEAD `5571db5`, JonexWiki 도입 commit `a8bee87` (2026-10-10)
- 논문: Ming, Li, Wu, Que, "Retrieval as Reasoning: Self-Evolving Agent-Native Retrieval via LLM-Wiki", arXiv 2605.25480 (https://arxiv.org/abs/2605.25480, https://arxiv.org/html/2605.25480). HTML판을 WebFetch 요약으로 읽었고 PDF 본문은 추출하지 못했다.
- 실행한 명령: `git log`, `git show --stat`, `grep`, `sed`, `cat`, `find`, 그리고 정규식 리터럴 확인용 `python3 -I -c`(레포 코드 import 없음)

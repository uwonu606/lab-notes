# GD4AI obsidian-llm-wiki — ingest-engine 갈래 노트

- 저장소: GitHub `GD4AI/obsidian-llm-wiki`, HEAD `f41a39d` (2026-10-09), Apache-2.0 (Copyright Greener-Dalii)
- 로컬: `lab/repos/GD4AI_obsidian-llm-wiki`. 아래 모든 경로는 레포 루트 기준이다.
- 코드는 실행하지 않았다. 근거는 모두 파일 읽기, `git log/show`, `gh issue view`로 얻었다.
- 표기: [확인] 코드·문서에서 직접 본 것. (a) 작성자가 밝힌 이유는 원문 인용 + 출처. [추정] 은 사례와 개수를 문장 끝 괄호에 단다. `모르는 것:` 은 #모르는 것 절에 모았다.

## 읽은 범위

| 파일 | 줄 수 | 읽은 정도 |
|---|---|---|
| `src/wiki/wiki-engine.ts` | 2323 | 끝까지 |
| `src/wiki/source-analyzer.ts` | 1238 | 끝까지 |
| `src/wiki/page-factory/*` (index, create-page, path-resolution, merge-page, merge-triage, complementary-appends, contradiction-gates, related-page, related-links, aliases, mentions-integration, note-window, contextualize, stub-page) | 약 3000 | 끝까지 |
| `src/wiki/page-write-guard.ts`, `src/wiki/system-prompts.ts`, `src/wiki/contradictions.ts` | | 끝까지 |
| `src/prompts.ts`, `src/wiki/prompts/{ingestion,generation,merge,pdf,constraints}.ts` | | 끝까지 |
| `src/wiki/prompts/{conversation,fixes,lint,seed-selection}.ts` | | 훑음 |
| `src/schema/schema-manager.ts`, `src/schema/analyze.ts` | | 끝까지 |
| `src/schema/auto-maintain.ts` | 771 | 훑음 (watcher 경로 116-260만 읽음) |
| `src/schema/apply-suggestion.ts`, `parse-suggestion.ts` | | 훑음 |
| `src/wiki/conversation-ingest.ts`, `engine-internals/{index-generator,log-writer,graph-cache,dedup-pages}.ts` | | 훑음 |
| `engine-internals/page-batch-runner.ts` | 220 | 끝까지 |
| ingest가 부르는 `src/core/*`: candidate-gate, candidate-window, conflict-resolver, related-shaping, index-search, source-lemma, batch-merger, batch-limits, convergence-detector, source-requirements, source-slug, vocabulary, tag-vocab, paragraph-provenance, pdf-converter, mentions-injector, mentions-integration | | 끝까지 |
| `src/core/{frontmatter,section-header-canonicalizer,slug,related-sections,related-link-corrector,mineru-converter,mentions-formatter,sources-normalizer,provenance-marker}.ts` | | 핵심 함수만 (줄 번호는 인용마다 적음) |
| `src/llm-sdk/output-schemas.ts` | 364 | 150-300 (ingest 스키마) |

경계: lint(`src/wiki/lint/**`), query(`src/wiki/query-engine/**`, PPR), LLM SDK 클라이언트, UI는 다른 갈래다. 이 노트는 그쪽을 부르는 지점만 적는다.

## 한눈에

- [확인] 문서 하나는 "추출(LLM, 여러 라운드) → 코드 정리(gate·어휘·관련 목록) → source 페이지 1장 → 후보마다 경로 결정(결정론 → LLM) → 생성 또는 병합 → 관련 페이지 `sources:` 갱신 → 링크 재지정 → index·log 재생성" 순으로 흐른다 (`src/wiki/wiki-engine.ts:944-1662`).
- 설계 축은 하나로 모인다. LLM은 "읽기·판정·문장"만 맡고, 이름 연결·태그·인용 출처·날짜·섹션 존재·링크 경로는 코드가 쓴다. 작성자 표현: "Extraction is reading, not linking" (`src/wiki/source-analyzer.ts:310`), "The schema, not the model, decides which sections exist" (`src/core/section-header-canonicalizer.ts:415`), "Injected programmatically — the LLM can't be trusted to emit it" (`src/wiki/wiki-engine.ts:1825`).
- 거의 모든 장치가 저자들 vault 측정에서 나왔다. 측정값은 코드 주석과 CHANGELOG에 있다. 대부분 독일어 의료 vault(@DocTpoint)다.
- 사용자 목표와 맞닿는 한계는 저장소 스스로 적었다. Related 그래프는 "intra-source by construction"이고, 새 문서와 기존 문서의 연결은 같은 이름 페이지를 공유할 때만 생긴다 (issue #729, `ROADMAP.md:56`).

## 1. 구조

### 모듈 지도

```
WikiEngine.ingestSource (wiki-engine.ts:944)
 ├─ [pdf / MinerU 확장자] ingestConversionSource (:739) → core/pdf-converter.convertPdfToMarkdown
 │      ├─ native: LLM file part (pdf-converter.ts:175-195) + pdf-cache
 │      └─ mineru: core/mineru-converter.convertPdfWithMineru (mineru-converter.ts:137)
 │      └─ 다시 ingestSource(file, {contentOverride}) (wiki-engine.ts:941)
 ├─ checkRequirements (:584) → core/source-requirements (빈 문서·확장자·contentHash 중복)
 ├─ SourceAnalyzer.analyzeSource (source-analyzer.ts:183)
 │      ├─ analyzeEmbeddedImages (opt-in, :839)
 │      ├─ 배치 루프: callLlm(task 'extract') + parseJsonResult + repair(task 'extract-retry')
 │      │     core/batch-limits, batch-merger, convergence-detector, repetition-loop
 │      ├─ core/index-search.matchExtractedToExisting → related_pages (:767-779)
 │      ├─ ensureSourceLemma → core/source-lemma + LLM 'lemma-classify' (:1001)
 │      └─ repairTypesAgainstVocabulary → core/tag-vocab.foldToVocabulary + LLM 'type-repair' (:1105)
 ├─ core/candidate-gate: applyOutcomeTable | gateCandidates + applyCoverageThreshold (wiki-engine.ts:1139-1236)
 ├─ core/domain-axis.selectDomains (어휘 검증, :1240-1248)
 ├─ core/related-shaping.shapeRelatedLists (:1255-1282)
 ├─ page-factory/stub-page.createDissentStubs (opt-in, :1317-1341)
 ├─ createSummaryPage (:1743) → LLM 'source-page'
 ├─ Stage 3: runBatchedWithRetry → PageFactory.createOrUpdate{Entity,Concept}Page
 │      └─ create-page.createOrUpdatePage (create-page.ts:80)
 │            ├─ path-resolution.resolvePagePath (path-resolution.ts:114)
 │            │     core/conflict-resolver, core/candidate-window, LLM 'dedup', aliases.appendAliases
 │            ├─ 새 파일 → createNewPage (create-page.ts:173) → LLM 'page-generate'
 │            ├─ reviewed:true → merge-page.appendToReviewedPage (merge-page.ts:457) → LLM 'reviewed-append'
 │            └─ 그 밖 → merge-page.mergePage (merge-page.ts:91)
 │                  ├─ merge-triage.classifyMergeNeed → LLM 'merge-triage'
 │                  │     └─ contradiction-gates → LLM 'source-stance'
 │                  ├─ complementary-appends → LLM 'complementary' (섹션마다)
 │                  └─ LLM 'merge-body' → guardBodyRewrite
 ├─ Stage 4: runBatchedWithRetry → related-page.updateRelatedPage → LLM 'related-page'
 ├─ repointLinksAfterRun (:1701)
 ├─ generateIndexFromEngine (:2277) → engine-internals/index-generator
 └─ updateLog (:2305) → engine-internals/log-writer
모든 쓰기: createOrUpdateFile → writeFileWithIntent (:1993) → page-write-guard.applyPageGuard → rawWrite (:2069) → markPageComplete / notify
```

[확인] `PageFactory`는 얇은 facade다. 2026-07-12에 1297줄 god class를 모듈 함수로 쪼갰다 (`src/wiki/page-factory/index.ts:1-26`, commit `6dadf18`).

### 핵심 자료 구조

| 구조 | 필드 | 위치 |
|---|---|---|
| `SourceAnalysis` | source_file, source_title, summary, entities[], concepts[], related_pages[], key_points[], created_pages[], updated_pages[], source_note_aliases?, mentions_in_source?(문서 전체 인용 풀), embedded_image_analysis? | `src/types.ts:61-99` |
| `EntityInfo` | name, type(7종 union이지만 실제로는 어휘 문자열), aliases?, summary, mentions_in_source[], mentions_with_provenance?, related_entities?, related_concepts?, coverage?(defined/discussed/named), domains? | `src/types.ts:128-148` |
| `ConceptInfo` | EntityInfo와 같고 related_concepts가 필수 | `src/types.ts:150-164` |
| `MentionWithProvenance` | quote, translation?, source_path, source_slug, extracted_at | `src/types.ts:20-36` |
| `SourceContext` | sourceTitle, summary, sourcePath, noteAliases? — 병합 판정에 "이 문서가 이 페이지의 주 문서인가"를 넘긴다 | `src/types.ts:46-59` |
| `ConflictResolution` | action(create/merge/flag/disambiguate), targetPath, confidence, reason, candidates?, crossFolderCandidates? | `src/core/conflict-resolver.ts:35-59` |
| `ComplementaryItem` | kind(complementary/contradictory), content, target_section, reason?, existing_statement? | `src/wiki/page-factory/merge-triage.ts:43-50` |
| `MergeTriageResult` | strategy(merge/skip/complementary/contradictory), items[], reason, demoted[] | `merge-triage.ts:60-66` |
| `StubCandidate` | kind, cell('prose+named'/'aside+covered'), item | `src/core/candidate-gate.ts:587-593` |
| `WriteIntent` | guard, notify, create, cancel('ingest'/'lint'/'none') — 기본값 없음 | `src/types.ts:1081-1114`, 상수 `:1121-1235` |
| frontmatter 정식 키 | type, created, updated, sources, tags, reviewed, aliases. 그 밖 키는 passthrough로 보존 | `src/core/frontmatter.ts:290-292`, `:306-335` |

[확인] LLM 출력 스키마는 느슨하다. `type`은 `z.string().optional()`이고 entities·concepts 배열만 필수다 (`src/llm-sdk/output-schemas.ts:175-188`, `:215-216`). 작성자 이유: "Making them required on Tier 0 would turn a single entity missing one field into a whole-response `NoObjectGeneratedError` → repair roundtrip" (`output-schemas.ts:160-163`).

### vault에 남는 것

| 경로 | 쓰는 쪽 | 비고 |
|---|---|---|
| `wiki/entities/<slug>.md`, `wiki/concepts/<slug>.md` | create/merge/related/stub | slug는 `computeSlug` (`src/core/slug.ts:19-44`), 기본 소문자 (`slugCase: 'lower'`) |
| `wiki/sources/<basename>_<6hex>.md` | `createSummaryPage` | 경로 FNV-1a 지문 (`src/core/source-slug.ts:153-162`) |
| `wiki/contradictions/<claim-slug>-<date>.md` | 항목 단위 모순 | `merge-page.ts:418-450` |
| `wiki/schema/config.md`, `suggestions.md` | SchemaManager | `src/schema/schema-manager.ts:15-16` |
| `wiki/index.md`, `wiki/log.md` | 매 ingest 끝 | 전체 재생성 (`wiki-engine.ts:2277-2295`) |
| `.obsidian/plugins/karpathywiki/pdf-cache/` | PDF·MinerU 변환 | 옵션을 켜면 `<원본>.pdf.md` sidecar (`wiki-engine.ts:899-914`) |

## 2. 동작 흐름

### 단계별

| # | 단계 | 입력 → 처리 → 출력 | LLM | 근거 |
|---|---|---|---|---|
| 0 | 변환 분기 | `.pdf` 또는 (MinerU 설정 시) 이미지·Office → 변환 → markdown을 `contentOverride`로 재진입 | native는 `pdf-convert` 1회 | `wiki-engine.ts:1002-1023`, `:739-942` |
| 1 | 요건 gate | 빈 문서/확장자/본문 해시 중복 → skip 보고. 대화형 ingest만 중복 재수집을 물어본다 | 없음 | `wiki-engine.ts:1032-1043`, `:584-599` |
| 2 | 추출 | 노트 전체 + 지침 → 라운드별 JSON → 누적 | `extract` ×N, `extract-retry` | `source-analyzer.ts:343-757` |
| 3 | 기존 이름 대조 | 뽑은 모든 이름 slug ↔ 기존 페이지 제목·별칭 slug → `related_pages` | 없음 | `source-analyzer.ts:767-779`, `src/core/index-search.ts:46-66` |
| 4 | 개수 상한·제목 | custom 상한 자르기, 노트 제목은 H1 또는 파일 이름(PDF만 모델 제목) | 없음 | `source-analyzer.ts:785-799` |
| 5 | lemma 보장 | 노트 주제가 후보에 없으면 추가, entity/concept만 LLM에 묻기 | `lemma-classify` | `source-analyzer.ts:1001-1058` |
| 6 | type 보정 | 어휘 밖 type → 접기 → LLM 재선택 | `type-repair` | `source-analyzer.ts:1105-1186` |
| 7 | 후보 gate | 위치 gate(opt-in) + coverage `named` 제거, 또는 결정표 → stub | 없음 | `wiki-engine.ts:1139-1236` |
| 8 | 도메인 태그 검증 | 항목의 `domains` 중 어휘 밖 값 제거 | 없음 | `wiki-engine.ts:1240-1248` |
| 9 | 관련 목록 정리 | 기존 페이지 이름으로 교정, 태그 값 제거, 고아 페이지에만 형제 최대 3 | 없음 | `wiki-engine.ts:1255-1282`, `src/core/related-shaping.ts:67-145` |
| 10 | stub 쓰기 | 결정표 이견 후보를 LLM 없이 stub으로 | 없음 | `wiki-engine.ts:1317-1341` |
| 11 | source 페이지 | 본문 앞 500자 + analysis JSON → 요약 페이지. 코드가 hash·경로·제목·인용을 덮어씀 | `source-page` | `wiki-engine.ts:1743-1935` |
| 12 | 엔티티·개념 페이지 | 후보마다 경로 결정 → 생성/병합/reviewed append. 동시성 기본 3 | `dedup`, `page-generate`, `merge-triage`, `source-stance`, `complementary`, `merge-body`, `reviewed-append` | `wiki-engine.ts:1367-1430`, `src/types.ts:1579` |
| 13 | 관련 페이지 | `related_pages`의 각 페이지에 `sources:` 추가, 이번 추출에 같은 이름 항목이 있으면 본문 재작성 | `related-page` | `wiki-engine.ts:1461-1496`, `related-page.ts:61-203` |
| 14 | 링크 재지정 | 이번 run에서 쓴 페이지끼리 폴더가 틀린 링크를 고침, reviewed 페이지는 건너뜀 | 없음 | `wiki-engine.ts:1701-1741` |
| 15 | index·log | index 전체 재생성, log에 시간·모델·바이트 기록 | 없음 | `wiki-engine.ts:1540-1550` |

### 추출 루프 세부

- [확인] 프롬프트는 "정적 prefix + 라운드 문맥 + 뒷부분"으로 쪼개 prefix를 캐시에 태운다 (`source-analyzer.ts:331-341`, `cacheBreakpoint: staticPrefix.length` `:445`).
- [확인] 1라운드는 "가장 중요한 것", 2라운드부터는 이미 뽑은 이름·별칭을 주고 "Do NOT extract them again" 한다 (`source-analyzer.ts:347-370`). 이유: "small models that cannot reliably remember their own previous output" (`:352`).
- [확인] 언어 지시: 요약은 wiki 언어, 이름은 원어, 인용은 verbatim (`source-analyzer.ts:379`). 노트 frontmatter `language:`가 wiki 언어와 다를 때만 번역 필드를 요구한다 (`:391-394`).
- [확인] 배치 크기·라운드 수는 길이와 granularity로 정한다. standard는 첫 배치 20, 최대 50항목. 2만 자 미만 문서는 600자당 1항목으로 상한을 낮춘다 (`src/core/batch-limits.ts:27-33`, `:70-75`, `src/constants.ts:881`, `:887`).
- [확인] 멈춤 조건: 빈 배열, 새 항목 0, 수율 50% 미만이 두 번, 누적 상한 (`source-analyzer.ts:655-709`, `src/core/convergence-detector.ts:39-76`, `:123-138`).
- [확인] 라운드 간 같은 이름(대소문자 무시)은 새 항목이 아니라 기존 항목에 인용·domains를 합친다 (`src/core/batch-merger.ts:157-193`).

### 실패·재시도

| 상황 | 처리 | 근거 |
|---|---|---|
| `finish_reason=length` | 배치 반으로 + max_tokens를 retryCap으로 올려 1회 재시도. 재시도 예산이 남았으면 JSON repair 생략 | `source-analyzer.ts:283-290`, `:527-529`, `:591-594` |
| 반복 루프 감지 | 원문에 같은 반복이 있으면 echo로 보고 통과, 아니면 손상 배치로 보고 반으로 재시도 | `source-analyzer.ts:491-509` |
| `{"": ""}` placeholder | 1라운드만 반으로 줄이지 않고 1회 재시도 | `source-analyzer.ts:606-611` |
| 그 밖 파싱 실패 | repair 호출(LLM). 실패하면 1라운드는 문서 전체 실패(null), 이후 라운드는 지금까지 결과 유지 | `source-analyzer.ts:529-567`, `:612-614` |
| 1라운드 호출 예외 | 오류 문구로 원인을 분류해 안내 메시지를 붙여 throw | `source-analyzer.ts:716-744` |
| 페이지 단위 실패 | 배치마다 실패 작업 2초 뒤 1회 재시도, 429 감지 시 동시성·지연 권고 | `src/wiki/engine-internals/page-batch-runner.ts:111-164` |
| 병합 triage 실패 | 예외를 삼키고 전체 본문 병합으로 | `merge-page.ts:260-264` |
| 본문 재작성이 토큰 한도에서 잘림 | 채택하지 않고 기존 본문 유지 | `merge-page.ts:339-342`, `:520-523`, `related-page.ts:158-164` |
| dedup 응답 판독 불가 | "match 아님"으로 읽지 않고 실패로 기록, fallback 경로 | `path-resolution.ts:306-327` |
| 취소 | 진행 중 모델 호출까지 abort. source 페이지를 지워 다음 trigger가 다시 수집하게 함, 내용 페이지는 남김 | `wiki-engine.ts:1600-1637` |

### LLM 호출 지점

| task 라벨 | 프롬프트 | 구조화 출력 | 실패 시 | 근거 |
|---|---|---|---|---|
| `pdf-convert` | `PDF_CONVERSION_SYSTEM_PROMPT` | 없음, fence 제거 후처리 | 제공자 거부는 skip 보고 | `pdf-converter.ts:175-205`, `src/wiki/prompts/pdf.ts:36-67` |
| `embedded-image-analysis` | `analyzeEmbeddedImages` | json_object | vision 거부면 텍스트만 계속 | `source-analyzer.ts:911-979`, `prompts/ingestion.ts:4-9` |
| `extract` / `extract-retry` | `analyzeSource` / 인라인 repair | `SourceAnalysisLLMSchema` | 위 표 | `source-analyzer.ts:438-567`, `prompts/ingestion.ts:11-105` |
| `lemma-classify` | 인라인 | `LemmaClassifyLLMSchema` | 의심 시 추가 안 함 | `source-analyzer.ts:1197-1237` |
| `type-repair` | 인라인 | `TypeRepairLLMSchema` | 의심 시 원래 값 유지 | `source-analyzer.ts:1146-1186` |
| `source-page` | `generateSummaryPage` | 없음 (markdown) | ingest 실패 | `wiki-engine.ts:1791-1813`, `prompts/generation.ts:127-173` |
| `dedup` | `resolveEntityDedup` | `PathResolutionLLMSchema` | fallback 경로 | `path-resolution.ts:276-302`, `prompts/ingestion.ts:116-140` |
| `page-generate` | `generateEntityPage` / `generateConceptPage` | 없음 | 항목 실패로 기록 | `create-page.ts:186-218`, `prompts/generation.ts:4-125` |
| `merge-triage` | `mergeAnalysis` | `MergeTriageSchema` | 전체 병합으로 | `merge-triage.ts:105-153`, `prompts/merge.ts:30-75` |
| `source-stance` | `sourceStance` | `SourceStanceSchema`, system prompt 없음 | `unverified` → 모순 유지 | `contradiction-gates.ts:106-166`, `prompts/merge.ts:83-96` |
| `complementary` | 인라인 (섹션 1개) | 없음, thinking 강제 끔 | NO_NEW_CONTENT 취급 → New Information 절 | `complementary-appends.ts:208-273` |
| `merge-body` | `mergeEntityPage` / `mergeConceptPage` | 없음 | 잘리면 기존 유지 | `merge-page.ts:310-335`, `prompts/merge.ts:98-171` |
| `reviewed-append` | `appendToReviewedPage` | 없음 | 잘리면 기존 유지 | `merge-page.ts:497-523`, `prompts/merge.ts:174-198` |
| `related-page` | `updateRelatedPage` | 없음 | 잘리면 frontmatter만 | `related-page.ts:133-164`, `prompts/merge.ts:207-227` |

[확인] system prompt는 `언어 지시 + schema/config.md 중 task별 절 + 런타임 어휘 절`로 조립한다 (`src/wiki/system-prompts.ts:237-262`). task별 절 표는 `src/schema/schema-manager.ts:122-138`이다.

[확인] 쓰이지 않는 프롬프트가 둘 있다. `preserveReviewedEntityPage`, `preserveReviewedConceptPage`는 src 안에 호출처가 없다 (`src/wiki/prompts/generation.ts:176-254`, `grep` 결과 정의만 있음).

### 결정적 검사 지점

| 시점 | 검사 | 근거 |
|---|---|---|
| 수집 전 | 빈 본문, 확장자 허용 목록, 본문 해시(배치 내·위키 내) | `src/core/source-requirements.ts:38-86`, `wiki-engine.ts:584-599` |
| 추출 직후 | 이름 없는 항목 제거, `[[x|y]]` 형태 related_pages 벗기기, 인용의 source_path·extracted_at을 코드가 덮어씀 | `source-analyzer.ts:69-95`, `:117-154` |
| 추출 직후 | 이름 위치 gate(괄호·나열·짧은 목록), coverage 임계, 작성자 링크 예외 | `src/core/candidate-gate.ts:384-415`, `:551-575` |
| 경로 결정 | slug·별칭 일치 개수, 반대 폴더 일치, 짧은 이름 floor | `path-resolution.ts:145-232` |
| 별칭 추가 | 페이지 이름과 같은 별칭, 최소 길이, 다른 페이지가 이미 가진 이름 제거 | `src/core/slug.ts:159-189`, `aliases.ts:46-94` |
| 생성 후 | frontmatter 재직렬화(`type`은 pageType으로 고정, created는 호출자 값만, 어휘 밖 태그 제거, 자기 별칭 제거) | `src/core/frontmatter.ts:698-876` |
| 생성·병합 후 | 섹션 헤더 오타 교정, 모르는 섹션 제거, Related 섹션을 목록에서 다시 렌더 | `section-header-canonicalizer.ts:134-142`, `:415-430`, `related-links.ts:26-51` |
| 병합 후 | 사라진/절반 이하로 줄어든 섹션 복원, 다른 source가 각주로 소유한 문단 복원, H1 복원 | `src/core/paragraph-provenance.ts:241-251` |
| 병합 후 | Mentions 절을 코드가 다시 씀(기존 ∪ 이번), 파싱 못하면 원문 보존 | `mentions-integration.ts:60-128` |
| 모순 | 인용한 페이지 문장이 실제로 있는가(정확·6단어 연속), source가 그 주장을 스스로 하는가(증거 문장이 발췌에 있는가) | `contradiction-gates.ts:74-87`, `:106-166` |
| 쓰기 직전 | 링크 오염 2종 교정, `sources:` 정규화, 헤딩 간격, provenance 각주 괄호 수리 | `src/wiki/page-write-guard.ts:68-130` |
| 쓰기 후 | `generation_complete: true` 도장 (fire-and-forget, update-only) | `wiki-engine.ts:355-381` |

## 3. 설계 결정과 이유

### D1. 추출 프롬프트에 기존 위키를 넣지 않는다

- [확인] 결정: 추출 프롬프트는 "instructions plus the note"뿐이다. 기존 페이지 대조는 추출 뒤 코드로 한다 (`source-analyzer.ts:301-312`).
- (a) "The slug catalog that used to sit at the top of this prompt (#116) was ~91% of it on a mature vault, grew without bound, and duplicated work the later stages already do per item" (`source-analyzer.ts:304-309`). commit `57099b7` 측정: 2,838페이지 vault에서 catalog 판은 매번 2라운드를 출력 한도로 잃었고(398–421 s), 새 판은 두 라운드를 다 돌았다(80–110 s).
- 대안: 기존 목록을 프롬프트에 넣어 모델이 연결까지 하게 하는 방식(#116, 이전 구현).
- 이력: #116 catalog 도입 → `9359cdf`(#452, run마다 catalog 고정) → `57099b7`(#482 stage 1+2, 제거).

### D2. 생성·병합 프롬프트에도 페이지 목록을 주지 않고, 링크는 생성 후 전체 vault로 푼다

- [확인] 생성 프롬프트는 "write [[Name]] ... Do NOT write a folder path ... the system resolves every name to its real page after generation" (`prompts/generation.ts:21`). 해석은 `applyRelatedLinks`가 title → alias 순 전체 index로 한다 (`related-links.ts:26-51`, `src/core/related-link-corrector.ts:41-90`).
- (a) "the target is often outside it, a sibling created in the same run is outside it at any cap" (commit `57099b7`). 측정: 8,800 related 링크 중 해결률 90.48% → 93.08%.
- 참고: 프롬프트 안에 옛 지시가 남아 있다. 같은 템플릿이 "[[path|display]] format"과 "Reference related entities using full paths from the list above"도 요구한다 (`prompts/generation.ts:22`, `:56`). `UNIVERSAL_LINK_CONSTRAINTS`는 없어진 `{{existing_pages}}` 목록을 언급한다 (`prompts/constraints.ts:7`). 기본 schema의 Naming Conventions도 full path를 요구한다 (`schema-manager.ts:197`). 코드가 뒤에서 다시 렌더하므로 결과에는 덜 영향 준다 [추정] (사례: Related 섹션을 목록에서 다시 쓰는 `related-sections.ts:1-14` 1건).

### D3. 정체 판정은 결정론 먼저, LLM은 좁은 창에서만

- [확인] 순서: 같은 폴더 같은 slug 파일 → ConflictResolver(같은 종류 제목·별칭 slug, 1개면 병합) → 2개 이상이거나 반대 폴더에도 있으면 LLM → 아무것도 없고 짧은 이름이면 생성 → 그 밖은 후보 30개 창으로 LLM (`path-resolution.ts:114-361`).
- (a) 후보 창: "the model found a synonym's target in that list 0 of 18 times while it found the same targets 9 of 9 times in a 30-entry window that contained them" (`path-resolution.ts:57-62`). 창 순위는 제목 3·별칭 2·본문 키워드 1점, 문서 절반 넘게 나오는 키워드 버림 — "the cap replaces a language-specific stop list" (`src/core/candidate-window.ts:216-224`).
- (a) 모호한 이름: "`find` returned whichever the page list happened to hold first ... and nothing recorded that the question had been open" (`conflict-resolver.ts:152-156`). 23개 사례/2,838페이지 (commit `455f295`).
- (a) 판정 기준: "Never match a page about a related, broader, narrower, or component thing — a relationship is not sameness." (`prompts/ingestion.ts:132`)
- (a) 짧은 이름: "`Cr` was merged into `Kreatinin` by two different window builders on the same vault" (commit `8ff0b3d`). floor는 라틴·그리스·키릴 문자 이름에만 걸린다. "A two-character Han, Kana or Hangul name is a complete word and keeps its model call" (같은 commit, `path-resolution.ts:109-112`).
- (a) prompt 배치: 기존 목록을 앞에, 후보를 뒤에 두어 연속 dedup 호출이 KV prefix 캐시를 공유하게 한다 (`prompts/ingestion.ts:110-115`). 같은 이유로 목록을 ctime 순으로 정렬한다 (`path-resolution.ts:248-254`).
- 대안: 임베딩 유사도. README는 임베딩을 일부러 버렸다고 쓴다 — "We deliberately rejected the embedding path in Issue #175" (`README.md:255`). 이유는 검색 쪽 논리다(경계: query 갈래).

### D4. 폴더(entity/concept)는 정체를 결정하지 않는다

- [확인] 반대 폴더에 같은 이름이 있으면 결정론 병합도 생성도 하지 않고 LLM 판정으로 보낸다. 판정이 match면 분류를 다시 묻고, 필요하면 페이지를 다른 폴더로 옮기고 `type_confirmed: true`를 박는다 (`path-resolution.ts:164-197`, `:387-447`).
- (a) "merging on it blindly mistakes a shared designator for a shared referent (the KHK case), ignoring it blindly mints a twin page ... (measured: 18 twin pairs in one 83-note batch, every one the same referent)" (`path-resolution.ts:13-17`). ratchet 이유: "the page cannot ping-pong between the folders on later draws" (`:372-375`).
- 이력: 바뀐 적이 있다. `7aed9eb`(2026-08-19, #499) "a designator is (letters, type) — stop consulting the opposite folder" → `2bd4a6d`(2026-09-02, #589) "route cross-folder designators through the semantic call — the folder never decides". `create-page.ts:8-11` 머리 주석은 아직 첫 결정("the opposite folder is not consulted")을 적고 있다.

### D5. 판정된 새 표기를 별칭으로 배우되, 모호할 때는 배우지 않는다

- [확인] 결정론 단일 일치나 LLM match면 새 이름을 그 페이지 별칭에 더한다. 다른 페이지가 이미 가진 제목·별칭이면 넣지 않는다 (`path-resolution.ts:185`, `:349`, `aliases.ts:103-118`).
- (a) "a duplicated claim would silently merge every future occurrence of the name into whichever page matches first" (`path-resolution.ts:181-184`).
- 이력: 모호한 경우의 fallback에서 별칭을 붙였다가(`b824c80`, 2026-08-16) 이틀 뒤 뺐다(`2806d24`). (a) "the designator accumulates as an alias on every candidate that ever ranked first — an unanswered question spreading as a global claim about the vault" (commit `2806d24`).
- (a) 모호한 경우 LLM이 "아니다"라고 해도 새 페이지 대신 1위 후보로 간다: "a new page is the one answer that is certainly wrong" (`path-resolution.ts:125-131`).

### D6. 타입·태그 어휘는 사람 쪽에서만 들어온다

- [확인] 어휘 = 설정 목록 ∪ 감시 폴더 노트 태그 ∪ 위키 페이지 태그. 프롬프트가 보여 주는 목록과 쓰기 직전 검사 목록이 같은 함수에서 나온다 (`src/core/vocabulary.ts:45-59`, `system-prompts.ts:276-303`, `create-page.ts:227-232`).
- (a) "A term enters the vocabulary through a note's frontmatter, a page's frontmatter, or the settings list — never through the model." (`vocabulary.ts:16-17`) 계기: 두 목록이 달라 903페이지 중 69페이지(7.6%)가 빈 `tags:`로 태어났다 (`vocabulary.ts:3-12`, commit `170205b`).
- (a) 구조화 출력에 enum을 걸지 않고 사후 보정한다: "about one item in ten arrives with a type the active vocabulary does not admit. Resolve that here, while the source's own words are still at hand" (`source-analyzer.ts:823-827`). 측정 10.0%/10,669항목 (`CHANGELOG.md:184`). 대안이던 "retag가 나중에 페이지 본문 400자로 결정"을 버렸다 (`source-analyzer.ts:1094-1097`).
- [확인] 기본 추출 프롬프트 안내는 `location`, `technology`를 쓰라고 하지만 기본 목록은 `place`이고 `technology`가 없다 (`prompts/ingestion.ts:79`, `:91`, `src/types.ts:1040-1041`).

### D7. "이 문서가 그 이름을 다루는가"는 위치는 코드가, 다룸의 정도는 모델이 관찰하고 임계는 코드가 정한다

- [확인] 위치 gate(opt-in), coverage `named` 제거(항상), 둘을 합친 결정표(opt-in, 이견은 stub) (`candidate-gate.ts:384-415`, `:426`, `:629-678`).
- (a) "The threshold lives here, in code, not in a prompt ... Three prompt-side formulations of the same question were stable within a formulation (91–100 % self-agreement over three draws) and inconsistent between formulations (0.9 % to 13.9 % filtered)" (`candidate-gate.ts:17-21`).
- (a) 기본 꺼짐: "it changes which pages an ingest writes, so it is the user's choice, not an upgrade's" (`candidate-gate.ts:25-26`). 측정 언어는 독일어 하나다 (`:105-111`).
- (a) 작성자 링크 예외: "the author linking a name is a stronger statement about relevance than the model's reading" (`candidate-gate.ts:546-549`, commit `6a5ba34`).
- (a) gate가 버린 이름이라도 기존 페이지가 있으면 링크를 남긴다: "The gate decides whether THIS note earns a page for a name; it cannot decide that a link to a page another note already earned is dead" (`candidate-gate.ts:471-475`). 계기: 켜자 2612페이지 중 782개가 나가는 링크 0 (`CHANGELOG.md:114`).
- (a) 결정표: "their dissent is mixed content — neither may hold a veto alone" (`candidate-gate.ts:578-584`). 1,153항목 측정에서 full-page 집합은 직렬 gate와 같다 (`:582-583`).
- (a) 받아들인 부작용: "a thing that fails here in source A and passes in source B gets its page with B, and A is not among its sources" (`candidate-gate.ts:50-52`).
- [확인] 결정표 경로는 `applyOutcomeTable`에 `isKnownPage`를 넘기지 않는다 (`wiki-engine.ts:1145-1150`, 함수 시그니처 `candidate-gate.ts:629-635`). 그래서 이 경로에서 `absent`·`aside+named`로 버린 이름은 기존 페이지가 있어도 관련 목록에서 빠진다 [추정] (사례: 직렬 경로만 `isKnownPage`를 넘김 `wiki-engine.ts:1183-1189`, `:1222-1227` 2건).

### D8. 문서 주제(lemma) 페이지를 보장한다

- [확인] 노트 파일 이름이 후보·별칭에 없으면 후보로 추가한다. LLM은 entity/concept 둘 중 고르기만 한다 (`source-analyzer.ts:1001-1058`, `src/core/source-lemma.ts:64-81`).
- (a) "The extraction prompt asks what a text mentions, never what it is about, so the note's own topic is regularly absent from both lists" (`source-analyzer.ts:816-820`). 보수적 이유: "A node that is not created costs nothing; a wrongly created one is permanent." (`src/core/source-lemma.ts:53-54`, `source-analyzer.ts:993-995`)
- (a) 이름은 파일 이름을 따른다: "incoming dead links point at the filename; a divergent model title can suppress the addition but never rename the page" (commit `95268eb`).

### D9. 관련 목록은 코드가 다듬고, Related 섹션은 목록에서 렌더한다

- [확인] 기존 페이지 이름으로 교정, 태그 값 제거, 고아일 때만 형제 3개 (`related-shaping.ts:67-145`, `RELATED_SIBLING_CAP` `src/constants.ts:269`).
- (a) "676 dead related entries on 870 pages ... 101 of 103 pages without a single live outgoing link had at least one sibling page born from the same note" (`related-shaping.ts:6-11`).
- (a) 형제를 고아에만 쓰는 이유: "Written for every page they were 99 % of the live edges on a 537-page rebuild ... a graph of co-birth, not content" (`related-shaping.ts:115-120`).
- (a) 섹션 렌더: 모델이 넘겨받은 이름을 "misspelt" 했다 (`H₂O₂` 재인코딩 등) (`src/core/related-sections.ts:4-10`).

### D10. 병합은 분류 후 경로를 고른다 (전체 재작성 최소화)

- [확인] triage 4전략 → skip은 frontmatter만, complementary는 섹션별 append, merge·contradictory는 본문 재작성 (`merge-page.ts:159-264`).
- (a) issue #216: "Regeneration is intrinsically lossy for weaker models: they re-summarize the Description and silently drop detail." 제안: "the Description is never blindly regenerated (corruption surface removed), and the expensive/strong path fires only on the contradictory minority". 이미 있던 `mergeAnalysis` 프롬프트가 "never called anywhere"였다는 것도 적었다. 연결 commit `b7bf5f0`(2026-07-09).
- (a) 불확실하면 merge: "Default to "merge" if uncertain — better to rewrite than to silently drop new info." (`prompts/merge.ts:73`)
- (a) complementary 호출에 thinking을 끈 이유: "appending a formatted fragment is a mechanical text task — reasoning here only adds latency, and on backends that emit visible <think> it used to leak verbatim into the wiki body" (`complementary-appends.ts:248-253`).

### D11. 병합에 "주 문서" 개념과 노트 원문 발췌를 넣는다

- [확인] 노트 파일명·제목·별칭이 페이지 이름·별칭과 slug로 맞으면 그 노트를 페이지의 주 문서로 보고 triage의 `skip`을 `merge`로 바꾼다. stub 페이지도 skip하지 않는다 (`merge-triage.ts:250-271`, `merge-page.ts:177`).
- (a) issue #312: 개념 페이지가 무관한 노트에서 먼저 생기고, 정의하는 노트가 나중에 오자 bullet append만 되었다 — "The page describing a topic no longer contains that topic's definition, while the source page beside it does."
- [확인] 병합 호출에 노트 문단 중 페이지 이름·별칭이 나오는 것만(4000자), 주 문서면 노트 전체(12000자)를 넣는다 (`note-window.ts:38-40`, `:71-105`).
- (a) "measured on a real ingest, 5 of 7 merges added nothing but links" (`merge-page.ts:128-134`). triage와 merge 둘 다에 넣는 이유: "enriching only the merge would leave the triage routing to "skip" on the thin payload" (`note-window.ts:108-111`).

### D12. 모순 기록은 두 결정론 검사를 통과해야 한다

- [확인] 항목 단위 모순은 (1) 페이지 문장 인용이 실제로 페이지에 있어야 하고 (2) 별도 LLM 호출로 source가 그 주장을 "스스로 하는지" 증거 문장과 함께 확인한다. 떨어진 항목은 일반 사실로 append된다 (`contradiction-gates.ts:1-29`, `:199-240`).
- (a) "of nine contradictions the triage recorded in one night, two were real, three were positions the source only REPORTED ... and four conflicted with nothing the page says" (`contradiction-gates.ts:4-8`). 프롬프트 규칙 대안을 시도했다: "A prompt rule ... removed the false positives and the planted true positive alike" (`:9-11`).
- (a) 범위를 일부러 좁혔다: page 단위 `contradictory` 전략은 같은 결함이 있지만 "deliberately left as they are here — one lane measured, one lane changed" (`contradiction-gates.ts:24-27`). page 단위는 기록 파일 없이 frontmatter 표시만 한다 (`merge-page.ts:244-258`).
- (a) 기록을 본문이 아닌 별도 파일로 두는 이유: "a body block is not a durable carrier, stripUnknownSections removes it on the next rewrite" (`merge-page.ts:192-198`).

### D13. 모델의 본문 재작성은 그대로 받지 않고 결정론 층을 통과시킨다

- [확인] `guardBodyRewrite` = 섹션 복원 → 각주 소유 문단 복원 → H1 복원 (`paragraph-provenance.ts:241-251`).
- (a) 섹션 축소: "nine `## Beschreibung` blocks of 800–8400 characters came back from a rewrite at under half their size — 5046 → 335 in the worst case" (`section-header-canonicalizer.ts:195-201`).
- (a) 문단: "Ownership, not size, is the variable: a paragraph footnoted to X may only disappear when X itself is the source being merged" (`paragraph-provenance.ts:18-20`). 571 재작성 쌍 측정 (`CHANGELOG.md:105`).
- (a) H1: 파일 이름에서 제목을 다시 만들지 않는다 — "677 (35%) have a title the file name cannot reproduce" (`section-header-canonicalizer.ts:296-300`).
- (a) 잘린 재작성 거부: "one page going 32 KB → 127 KB with 300–760 provenance footnotes" (`CHANGELOG.md:67`, commit `1428b5d`).
- [확인] 각주 형식(`^[Quelle: [[X]]]`)은 기본 프롬프트·기본 schema가 요구하지 않는다. "the vault's config decides how the marker is worded" (`src/core/provenance-marker.ts:4-6`). 그래서 기본 설정에서는 문단 guard가 no-op이다 — "the footnote convention itself (no-op without it)" (`CHANGELOG.md:105`).

### D14. 코드가 아는 값은 모델에게 묻지 않는다

- [확인] `contentHash`, `source_file`, source 페이지 H1·Source 절, 인용의 `source_path`·`extracted_at`, `created:`, `sources:`는 코드가 쓴다 (`wiki-engine.ts:1824-1837`, `source-analyzer.ts:69-95`, `frontmatter.ts:733-741`, `create-page.ts:298-307`).
- (a) "measured copies were a typo, a control character for `α`, and a translation of the file name" (`source-analyzer.ts:61-67`). 생성 경로의 `sources:`: "observed: 5 of 8 "multi-source" pages were born with a second source whose note does not exist ... fabricated provenance is worse than none" (`create-page.ts:298-304`).
- 이력: `98b82af`, `872508f`(2026-09-12)로 코드가 쓰게 바꾼 뒤 `4ae0f39`(#774)에서 프롬프트 요구도 지웠다 — "a declared property is a request" (commit `4ae0f39`).

### D15. Mentions 절(verbatim 인용)은 코드가 쓰고 누적한다

- [확인] 모델이 쓴 Mentions 절을 지우고 `(quote, source_path)` 키로 합친 목록을 다시 쓴다. 예산은 기존 길이 + 500자 (`mentions-integration.ts:87-127`, `src/core/batch-merger.ts:35-62`).
- (a) "Effect 2 dies at source" — 생성·병합 프롬프트에서 Mentions 지시를 뺐다 (commit `1c1db3a`). 누적: 이전 판은 "re-capped the accumulated block at that size on every rewrite" (`mentions-integration.ts:115-121`).
- [확인] 인용이 원문에 실제 있는지는 ingest에서 검사하지 않는다. 검사는 lint의 quote grounding이다 (`src/wiki/lint/phases/programmatic.ts:72-108`, 경계: lint 갈래).

### D16. 쓰기 경로를 layer로 나누고 의도를 기본값 없이 선언한다

- [확인] `guard`(오염 교정)·`notify`·`create`·`cancel`을 쓰기마다 선언한다 (`src/types.ts:1081-1235`).
- (a) "The gate used to offer all of its four concerns or none ... There is no default. A default is how the ambiguity this type exists to remove would come back." (`src/types.ts:1072-1079`) 계기: PDF sidecar의 의도된 우회 (`wiki-engine.ts:886-891`).

### D17. PDF·OCR은 "markdown으로 바꾼 뒤 같은 경로"로 처리한다

- [확인] 변환 결과를 `contentOverride`로 넘겨 ingestSource를 다시 탄다. 캐시 키는 `sha256:model:version` (`pdf-converter.ts:145-158`), MinerU는 `sha256:mineru:vlm:v1` (`mineru-converter.ts:164-171`).
- (a) 기본은 vault에 산출물을 남기지 않는다: "the vault contains no implementation artifacts from PDF ingestion" (`wiki-engine.ts:730-734`).
- (a) 제공자 gate를 캐시보다 먼저: "a user who switches from `anthropic` to `ollama` cannot silently receive a cached conversion" (`pdf-converter.ts:10-12`).
- (a) 소형 모델용 변환 프롬프트: "OCR-style verbatim transcriber" + `[illegible]`, `[figure: …]` 표식 — "gives the model an explicit alternative to hallucination" (`prompts/pdf.ts:10-17`).
- (a) force 옵션: "the user is the authoritative source on what their endpoint supports" (`pdf-converter.ts:241-244`).
- [확인] 문서 위치 고지: MinerU는 "uploaded to `https://mineru.net/api/v4` ... treat an upload there as leaving your control" (`docs/PDF-OCR-GUIDE.md` "Where your document is processed" 표).

### D18. No chunking — 노트 전체를 매 라운드 보낸다

- [확인] 청크 단위가 없다. 긴 노트는 라운드 수만 늘린다 (`batch-limits.ts:77-82`). 1000줄 넘으면 경고만 띄운다 (`wiki-engine.ts:1058-1070`).
- (a) README: "Karpathy's argument against RAG is that chunking breaks the LLM's ability to reason across your whole knowledge graph" (`README.md:233`). 이 문장은 검색 이유이고, ingest에서 청크를 안 쓰는 이유를 따로 적은 곳은 찾지 못했다.

### D19. Related 그래프가 문서 안에 갇히는 것은 프롬프트 지시의 결과다 (미해결)

- [확인] 추출 프롬프트가 관련 항목을 "other items extracted from this same source file"로 한정한다 (`prompts/ingestion.ts:33`).
- (a) issue #729: "95 % of edges connect pages born from the same note ... Nine of ten pages have no incoming link from a page with another source" (413노트 재구축). "the write path can **confirm** a name but can never **discover** one."
- (a) 결정 상태: 2026-10-05 "direction A" — 측정 먼저, 그다음 co-citation projection(M0) (`ROADMAP.md:109-160`). 아직 코드 없음.
- (a) 상위 원칙: "Model-independent mechanisms hold the **floor** ... model-dependent mechanisms exist to explore the **ceiling** and are **deferred, never rejected**" (`ROADMAP.md:306`, 상태는 proposed).

### D20. 사용자 schema 편집이 닿는 범위는 정해진 절 이름까지다

- [확인] `config.md`는 `## 제목`으로 쪼개 task별로 정해진 이름의 절만 넣는다 (`schema-manager.ts:122-138`, `:315-323`). 새 이름의 절은 `full` 호출(lint 쪽 fill-empty-page 등)에만 간다.
- [확인] 페이지 섹션은 코드 상수 `SECTION_LABELS`만 인정한다. 모델이 다른 `##` 절을 쓰면 지운다 (`system-prompts.ts:15-150`, `section-header-canonicalizer.ts:415-430`).
- (a) 절 배달 범위를 넓힌 이유(#491): "A user writing merge policy into the section named Multi-Source Merge Rules was editing the one task that would not see it" (`CHANGELOG.md:163`).
- (a) 3층 분리 원칙: "schema file MUST NOT bake runtime parameters" (`AGENTS.md:416-429`).
- [추정] 사용자가 schema에 새 페이지 섹션(예: "## 결정 이력")을 정의해도 생성 후 지워진다 (사례: `stripUnknownSections`가 `SECTION_LABELS` 밖 헤더를 버림 `section-header-canonicalizer.ts:420-428` 1건, 기본 schema의 "add to ## Contradictions section" 지시 `schema-manager.ts:245`가 같은 이유로 남지 않는다고 작성자가 적음 `src/core/contradiction-record.ts:7-9` 1건).

### D21. reviewed 페이지는 잠근다 — 다만 잠금은 모델 복사에 기댄다

- [확인] `reviewed: true`면 생성·병합 대신 `appendToReviewedPage`로 가고 Mentions를 건드리지 않는다 (`create-page.ts:115-121`, `related-page.ts:121-124`, `mentions-injector.ts:65-66`).
- [확인] 그러나 이 경로의 출력은 "[existing content preserved exactly]\n\n## New Information" 형태로 모델이 기존 본문까지 다시 써서 낸다 (`prompts/merge.ts:191-198`). 코드는 그 출력을 `frontmatter + 출력`으로 쓴다 (`merge-page.ts:556-557`). 이 경로에는 `guardBodyRewrite`가 없다.
- [추정] reviewed 본문의 보존은 모델의 충실한 복사와 잘림 검사(`merge-page.ts:520-523`)에만 기댄다 (사례: 위 두 줄 1건). 실행해서 확인하지 않았다.

### D22. 감시 자동 수집은 markdown만, 기본은 알림만

- [확인] watcher는 `.md`만 보고(`src/schema/auto-maintain.ts:140`), 기본 `autoWatchMode`는 notify다(`src/types.ts:1563`). auto 모드면 debounce 후 순차 ingest한다 (`auto-maintain.ts:212-259`).
- (a) 이유를 적은 곳은 찾지 못했다. 모르는 것 절 참고.

## 4. 앞선 schema-glossary 보고서와 어긋나는 점

대상: `llm-wiki-implementations/lab/reports/schema-glossary/gd4ai-obsidian-llm-wiki.md` (같은 commit).

| 보고서 위치 | 보고서 주장 | 이번에 본 것 | 근거 |
|---|---|---|---|
| 한 바퀴 흐름 9단계 | 관련 페이지의 `sources:`를 더하고 "본문을 LLM으로 고쳐 쓴다" | 본문 재작성은 이번 추출에 `name === 페이지 basename`인 항목이 있을 때만이다. basename은 slug라서 기본 설정(`slugCase: 'lower'`)에서는 대부분 frontmatter만 바뀐다 | `related-page.ts:100-117`, `index-search.ts:63` (`match.title`), `get-existing-pages.ts:57` (`title: file.basename`) |
| 위와 같은 곳 (보완) | — | [추정] 공백 없는 소문자 이름·한중일 단어(예: "트랜스포머")는 basename과 같아서 Stage 3 병합 뒤 Stage 4에서 한 번 더 본문을 재작성한다 (사례: 위 세 줄의 조합 1건). 실행 확인 안 함 | 같음 |
| #A 강제 3겹 표 | 쓰기 직전 태그 삭제 근거 `core/frontmatter.ts:676-688` | 그 줄은 옵션 문서 주석이다. 실제 삭제는 `:825-842` | `frontmatter.ts:825-842` |
| #D 4번 | "3글자 미만 로마자" | 라틴·그리스·키릴·숫자·부호로만 된 이름이다. 한중일 2글자는 LLM 판정으로 간다 | `path-resolution.ts:109-112`, commit `8ff0b3d` |
| #F coverage 기준 "항상" | `named`면 버린다 | 작성자 링크(`[[X]]`)에 정확히 나오는 이름은 `named`여도 남는다 (#607) | `candidate-gate.ts:556-564` |
| #H 위치 gate 연결 손실 | "기존 페이지 이름은 링크를 남기도록 고쳤다" | 직렬 경로만이다. 결정표 경로(`gateDissentStubs` on)는 `isKnownPage`를 안 넘긴다 | `wiki-engine.ts:1145-1150` |
| 흐름 6단계 | "형제 페이지를 최대 3개 잇는다" | 자기 관련 이름이 하나도 살아 있는 페이지에 닿지 않을 때만 붙는다 | `related-shaping.ts:115-127` |
| #A schema | "사람이 고치는 Markdown 파일 하나" | 고칠 수 있지만, ingest에 닿는 것은 정해진 이름의 절뿐이고 페이지 섹션 구성은 코드 상수다 (D20) | `schema-manager.ts:122-138`, `section-header-canonicalizer.ts:415-430` |
| #C | gate가 버린 문서도 기존 페이지면 `sources:`에 들어간다 | 맞다. 추가로, reviewed 페이지가 Stage 4로 갱신되면 `sourceSlug`를 안 넘겨 `sources:`가 지문 없는 `sources/<slug>`로 정규화된다 [추정] (사례: `related-page.ts:122` 인자 누락, `src/core/sources-normalizer.ts:71-76` 지문 없는 remap, `source-slug.ts:153-162` 지문 형식 3건) | 같음 |

나머지 인용(`source-analyzer.ts:304-312`, `prompts/ingestion.ts:38-71`, `:79`, `:91`, `:132`, `path-resolution.ts:114-360`, `candidate-window.ts:5-27`, `frontmatter.ts:860`, `wiki-engine.ts:1872-1877` 등)은 다시 열어 맞는 것을 확인했다.

## 5. 엔터프라이즈 다중 작성자 보고서 용도

### 가져올 만한 장치

| 장치 | 왜 맞나 | 근거 |
|---|---|---|
| 추출은 노트만 보고, 연결은 추출 뒤 코드로 | 문서가 수만 건이어도 추출 비용이 vault 크기와 무관하다 | D1 |
| 결정론 → 좁은 후보 창 LLM → 판정 후 별칭 학습 | 작성자마다 다른 표기가 판정 한 번 뒤로는 slug 대조로 붙는다. 용어 불일치를 점진적으로 흡수한다 | D3, D5 |
| 별칭 전역 유일성 + 모호하면 배우지 않음 | "한 이름이 두 대상"(약어 충돌)이 흔한 사내 문서에서 잘못된 병합 확산을 막는다 | D5, `slug.ts:159-189` |
| 어휘는 사람 쪽에서만 | 부서별 분류 체계를 설정·문서 태그로 관리하고 모델이 새 분류를 못 만든다 | D6 |
| 결정표(위치 × 다룸) + stub | 형식 없는 문서의 나열·괄호 속 이름을 페이지로 만들지 않으면서 이견은 stub으로 남긴다 | D7 |
| 주 문서 개념 + 노트 발췌 | 같은 주제를 여러 사람이 쓸 때, 그 주제를 정의한 보고서가 페이지 본문을 주도한다 | D11 |
| 모순 2-gate + 기록 파일 | 작성자 간 상충 주장을 "인용 가능한 문장"과 "그 문서가 스스로 주장" 두 조건으로 걸러 별도 파일로 남긴다 | D12 |
| 재작성 guard + 잘림 거부 + reviewed | 여러 문서가 한 페이지를 계속 고쳐도 다른 문서가 쓴 내용이 지워지지 않게 한다 | D13, D21 |
| 코드가 쓰는 provenance (경로·해시·인용 출처) | 감사 추적: 어느 보고서에서 어느 문장이 왔는지 페이지마다 남는다 | D14, D15 |
| 경로 지문 slug + 본문 해시 | 같은 파일명 보고서가 폴더만 달라도 충돌하지 않고, 같은 내용 재업로드는 건너뛴다 | `source-slug.ts:87-104`, `source-requirements.ts:68-86` |
| task 라벨별 LLM 시간 집계 | 단계별 비용을 보고 어디를 줄일지 정할 수 있다 | `wiki-engine.ts:1573-1580`, `AGENTS.md:408-410` |

### 걸리는 점

- [확인] **새/기존 연결 발견 장치가 없다.** Related는 문서 안에서만 생기고, 문서 간 연결은 "같은 이름 페이지 공유"에 기댄다 (D19). 사용자 목표의 "새로운 데이터와 기존 데이터의 연결고리를 발견"에 직접 맞는 부품은 이 저장소에서 설계 단계(#729)다.
- [확인] **보고서 수정본을 다루지 않는다.** 본문이 바뀌면 해시가 달라 다시 수집된다 (`wiki-engine.ts:592-595`). 병합은 추가·보완만 하므로 이전 판에서 빠진 사실을 거두는 경로가 없다 [추정] (사례: `mergeFrontmatter`가 sources를 합치기만 함 `frontmatter.ts:584-596`, triage 4전략에 "철회"가 없음 `prompts/merge.ts:47-55` 2건).
- [확인] **작성자·권한 개념이 없다.** provenance는 노트 경로뿐이고 작성자·부서·접근 권한 필드가 없다 (`src/types.ts:20-36`, frontmatter 정식 키 `frontmatter.ts:290-292`). Obsidian vault 단일 사용자 전제다.
- [확인] **형식 없는 긴 문서에 약하다.** 청크 없이 전체를 매 라운드 보내고, 1라운드가 실패하면 문서 전체가 실패한다 (`source-analyzer.ts:612-613`, `:716-744`). source 페이지 요약은 본문 앞 500자만 본다 (`wiki-engine.ts:1796`).
- [확인] **사내 템플릿 섹션을 쓸 수 없다.** 페이지 섹션은 코드 상수 10여 개다 (D20).
- [확인] **한국어는 추정 프로필이다.** 위치 gate의 `ko` 프로필은 "estimated"이고 측정은 독일어 하나다 (`candidate-gate.ts:146-151`, `:105-111`). 기본 꺼짐이라 영향은 켤 때만이다.
- [확인] **페이지가 자동으로 이동한다.** 교차 폴더 판정이 분류를 바꾸면 `renameFile`로 옮긴다 (`path-resolution.ts:420-446`). 여러 사람이 링크를 거는 환경에서는 이동 이력이 필요하다 [추정] (사례: 이동은 log에 남지 않고 console.debug만 함 `path-resolution.ts:443-445` 1건).
- [확인] **외부 OCR 업로드.** MinerU는 외부 서버에 원문을 올린다. 작성자도 통제 밖이라고 적었다 (D17).
- [확인] **LLM이 쓴 별칭은 중복 검사를 안 받는다** (앞선 보고서 #B와 같은 결론, `frontmatter.ts:859-861`).
- [추정] **Office·이미지 ingest가 변환 뒤 요건 gate에서 막힐 수 있다** (사례: 재진입 때 `checkRequirements`가 원본 확장자 `docx`를 `COMPATIBLE_SOURCE_EXTENSIONS`(md, markdown, txt, text, pdf)로 검사 `wiki-engine.ts:1032-1033`, `:584-590`, `src/constants.ts:35` 1건; 관련 테스트는 변환 호출만 확인 `src/__tests__/wiki/wiki-engine-pdf.test.ts:701-719` 1건). 실행 확인 안 함.
- [추정] **긴 PDF가 잘릴 수 있다.** native 변환은 max_tokens 8000 한 번이고 잘림 검사가 없다 (사례: `src/constants.ts:102` 주석 "Sized for typical research papers (5-30 pages)", `pdf-converter.ts:175-205`에 finish_reason 확인 없음 2건).

## 6. 모르는 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| docx·png를 MinerU로 변환한 뒤 실제로 페이지가 생기는지 | 테스트 하네스에서 `ingestSource(docxFile)` 후 `writtenPaths`에 wiki 페이지가 있는지 단언하는 테스트를 돌리거나, 실제 vault에서 docx 1개 수집 |
| Stage 3 병합 + Stage 4 재작성이 같은 페이지에 겹치는 빈도 | 한국어·중국어 단어 이름이 많은 vault에서 `[LLM time by step]` 로그(`wiki-engine.ts:1576-1580`)의 `related-page` 호출 수와 대상 경로 |
| 동시성 3에서 같은 대상 페이지를 두 후보가 동시에 병합할 때 덮어쓰기가 나는지 | 같은 페이지로 풀리는 두 이름을 가진 노트로 재현. 작성자 측 기록은 `MEMORY.md:843-845`의 다른 race뿐 |
| 결정표 경로에서 `isKnownPage`를 안 넘긴 것이 의도인지 | PR #607 토론, `applyOutcomeTable` 테스트(`src/__tests__/core/candidate-gate.test.ts`) |
| reviewed append가 기존 본문을 그대로 복사하는 비율 | reviewed 페이지 재수집 전후 diff 측정 |
| 감시 수집이 `.md`만 보는 이유, PDF를 감시에서 뺀 이유 | `auto-maintain.ts` 이력(`git log -S"endsWith('.md')" -- src/schema/auto-maintain.ts`), PDF 도입 commit `145f364` 메시지 |
| 청크 없는 ingest를 고른 ingest 쪽 이유 | issue #175, #330 본문 전체, README FAQ "No chunking" 주변 |
| 작성자들 vault의 provenance 각주 규칙(`Quelle:`)이 어떤 schema 문구에서 나오는지 | @DocTpoint의 `config.md` (#330에서 일부 인용됨), issue #631 토론 |
| 측정치(91%, 0/18 vs 9/9, 7/9 오탐 등)의 재현성 | 측정은 대부분 작성자 vault·로그이며 저장소에 데이터가 없다. `scripts/`, `tools/llm-wiki-cli/`의 측정 스크립트와 원자료 요청 |

## 7. 다른 갈래와 겹치는 곳

- lint: quote grounding, 중복 병합(`merge-duplicates`), dead link → stub, retag, hub-link lint. ingest는 이것들에 뒷정리를 맡긴다.
- query: PPR·seed 선택. #729의 "reader가 병목"이라는 측정(arm C가 5문항 중 3개 손실)은 query 갈래 소관이다.
- schema 진화: `suggestSchemaUpdate` → `suggestions.md` → diff modal Apply(백업 후 본문 교체) (`schema-manager.ts:446-507`, `src/schema/analyze.ts:47-94`, `apply-suggestion.ts:1-19`). lint 결과를 맥락으로 쓰므로 lint 갈래와 공유한다.
- conversation ingest: 질의 대화를 위키로 되돌리는 경로. 같은 PageFactory를 쓰지만 `sourceSlug`를 넘기지 않아 모델이 쓴 `sources:`에 기댄다 (`src/wiki/conversation-ingest.ts:267`, `:285`, commit `4ae0f39` 메시지). 훑음.

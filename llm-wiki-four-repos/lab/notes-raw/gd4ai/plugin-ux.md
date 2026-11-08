# gd4ai — plugin-ux 갈래 노트

대상: GD4AI/obsidian-llm-wiki, HEAD `f41a39d` (2026-10-09), Apache-2.0 (Copyright Greener-Dalii). manifest 이름은 "Karpathy LLM Wiki", id `karpathywiki`, 버전 1.28.0, `isDesktopOnly: false`, `minAppVersion: 1.11.4`다(manifest.json:2-9).

이 노트의 모든 경로는 레포 루트 기준이다. 코드는 실행하지 않았다. "코드로 본 것"은 파일을 읽어서 확인한 것이고, 동작을 돌려 본 것은 하나도 없다.

## 0. 범위와 읽은 정도

| 범위 | 읽은 정도 |
|---|---|
| `src/main.ts` | 끝까지 읽음 |
| `src/main-commands/*` | ingest·query-lint·schema·connection·pdf-cache·secret-storage·command-registry 끝까지 읽음. codex-auth 앞 60줄만 훑음 |
| `src/ui/settings.ts` | 끝까지 읽음 (Codex·Bedrock 로그인 메서드는 훑음) |
| `src/ui/settings-sections/*` | wiki-config·auto-maintain·advanced-settings·advanced·language·status·test-connection 끝까지 읽음. provider·model 섹션은 동시성 슬라이더 부분만 읽고 나머지는 훑음 |
| `src/ui/modals/*` | Lint·Fix·Ingest 보고서, Confirm, suggest, multi-file-row-state 끝까지 읽음. MultiFileSuggestModal은 열기·버튼·취소·디스크 스캔 부분을 읽고 트리 렌더링은 훑음 |
| `src/ui/schema-diff-modal.ts` | 끝까지 읽음. `schema-diff-modal-classes.ts`는 훑음 |
| `src/ui/history-modal/*` | HistoryModal-class 앞 120줄과 types 앞 80줄 읽음. renderers·render-state는 훑음 |
| `src/ui/tag-chip-input.ts`, `settings-helpers.ts`, `settings-per-task-helpers.ts`, `bedrock-auth-controls.ts`, `openai-codex-auth-controls.ts` | 훑음 |
| `src/types.ts` | `LLMWikiSettings` 전체(259-669), `DEFAULT_SETTINGS`(1527-1650), 보고서·schema·WriteIntent 타입 읽음. provider 표는 키 목록만 봄 |
| `src/constants.ts` | 전체 목록을 보고 성능·추출·lint·query 상수를 읽음. Bedrock·MinerU 상수는 훑음 |
| `src/texts/**` | en.ts에서 설정 설명 문구를 grep으로 읽음. 다른 10개 언어는 키 이름만 비교 |
| `docs/MODEL-GUIDE.md` | 끝까지 읽음 |
| `docs/PDF-OCR-GUIDE.md` | 머리말·MinerU 절·캐시 절 읽음. 나머지는 훑음 |
| `docs/contributions/openai-codex-oauth-proposal.md` | 끝까지 읽음 |
| `tools/dev-instrument/` | README와 measurement-arms 끝까지 읽음. engine-runner·vault-fs·shim은 훑지 않음 |
| `scripts/` | 네 파일 머리말만 읽음 |
| `.github/` | 워크플로 3개와 dependabot·이슈 템플릿 읽음 |

범위 밖이지만 사용자 면의 동작을 정하기 때문에 일부 읽은 파일이 있다. `src/schema/auto-maintain.ts`(감시·주기 lint·시작 점검), `src/wiki/lint/controller.ts`(버튼 콜백·자동 lint 분기), `src/schema/analyze.ts`·`apply-suggestion.ts`(schema 제안 흐름), `src/core/ingest-queue.ts`·`ingest-state.ts`·`progress-notification.ts`·`batch-limits.ts`·`tag-vocab.ts`·`settings-migrations.ts`가 그 대상이다.

다른 갈래와의 경계는 다음과 같다. 추출·후보 gate·경로 결정·병합은 ingest 갈래가 맡는다. 중복 판정 알고리즘과 fix runner의 내부는 lint 갈래가 맡는다. QueryView·PPR은 query 갈래가 맡는다. 이 노트는 그 기능들을 "사용자가 어디서 켜고, 무엇을 누르고, 무엇을 승인하는가"까지만 다룬다.

## 1. 구조

### 1.1 파일 지도와 호출 관계

```
main.ts  LLMWikiPlugin (Obsidian Plugin)
 ├─ onload()
 │   ├─ loadSettings() → core/settings-migrations.applySettingsMigrations
 │   │                  → SecretStorage 이관(apiKey, MinerU 토큰)
 │   ├─ new CodexAuthManager / BedrockAuthManager
 │   ├─ cleanupVocabularyTags() → core/tag-vocab.normalizeVocabularyCsv
 │   ├─ initializeLLMClient() → core/create-plugin-llm-client
 │   ├─ new SchemaManager, new WikiEngine(콜백 5개), new AutoMaintainManager
 │   ├─ wikiEngine.onConfirmReingest = ConfirmModal
 │   ├─ performPdfCacheHousekeeping()        (main-commands/pdf-cache-commands)
 │   ├─ autoMaintainManager.startWatching()   (autoWatchSources일 때)
 │   ├─ autoMaintainManager.schedulePeriodicLint()
 │   ├─ autoMaintainManager.runStartupCheck() (항상)
 │   ├─ registerView(QueryView)
 │   └─ registerWikiCommands(this)            (main-commands/command-registry)
 │        ├─ 명령 11개, 리본 아이콘 2개, 상태 표시줄 1개
 │        └─ addSettingTab(LLMWikiSettingTab)  (ui/settings.ts)
 ├─ saveSettings() → initializeLLMClient, schemaManager/wikiEngine.updateSettings,
 │                   autoMaintainManager.stop() → startWatching/schedulePeriodicLint
 └─ Object.assign(prototype, mixin 7개)   (main.ts:456-457)
      pdf-cache / connection / schema / query-lint / ingest / codex-auth / secret-storage
```

명령 등록은 `command-registry.ts:49-142`에 있다. 명령 id와 하는 일은 다음과 같다.

| 명령 id | 부르는 것 | 근거 |
|---|---|---|
| `ingest-source` | FileSuggestModal → `wikiEngine.ingestSource(file, {interactive:true})` | `command-registry.ts:49-53`, `ingest-commands.ts:84-103` |
| `ingest-folder` | FolderSuggestModal → `runBatchIngest` | `ingest-commands.ts:128-161` |
| `ingest-multiple-files` | MultiFileSuggestModal → `runBatchIngest(files, ids)` | `ingest-commands.ts:163-179` |
| `ingest-active-file` (리본 sticker 아이콘도 같음) | 열린 파일을 `interactive:true`로 ingest | `ingest-commands.ts:105-126`, `command-registry.ts:144-146` |
| `query-wiki` (리본 message-circle 아이콘도 같음) | 오른쪽 사이드 패널 QueryView 열기 | `query-lint-commands.ts:45-66` |
| `lint-wiki` | `runLintWiki` (wiki/lint/controller.ts) | `query-lint-commands.ts:77-95` |
| `regenerate-index` | `wikiEngine.generateIndexFromEngine()` | `command-registry.ts:79-94` |
| `cancel-ingestion` | ingest 중이면 ingest를, 아니면 lint를 취소 | `command-registry.ts:96-106` |
| `view-ingestion-history` | HistoryModal (log.md를 읽어 보여 줌) | `command-registry.ts:114-123` |
| `recreate-welcome-note` | `autoMaintainManager.recreateWelcomeNote()` | `command-registry.ts:125-129` |
| `clear-pdf-cache` | PDF 변환 캐시 삭제 | `command-registry.ts:131-136` |
| `migrate-api-key-to-settings` | SecretStorage의 키를 settings로 되돌려 쓰는 복구 명령 | `command-registry.ts:138-142`, `secret-storage-commands.ts` |

명령 이름은 등록할 때 한 번 UI 언어로 정해진다(`command-registry.ts:47`). [추정] 그래서 설정에서 UI 언어를 바꿔도 명령 팔레트의 이름은 Obsidian을 다시 열 때까지 그대로다(사례: 등록 시점에 `TEXTS[language]`를 한 번 읽는 줄 1개).

schema 제안 명령은 명령 팔레트에 없다. 진입점은 Lint 보고서 창의 "Analyze schema" 버튼 하나다(`controller.ts:261`, `LintReportModal-class.ts:157-164`). `schema/analyze.ts:4-5`의 주석은 아직 "command palette + Lint Report Modal button" 두 곳이라고 적지만, `command-registry.ts`에는 그 명령이 없다. 이슈 #97의 마지막 답글이 이를 확인한다: "The "Update Schema" button is now accessed from the Lint Modal."

### 1.2 mixin 구조

`main.ts`는 459줄이다. 나머지 메서드는 7개 mixin 객체로 나뉘어 `Object.assign(LLMWikiPlugin.prototype, ...)`로 붙는다(`main.ts:451-457`). 각 mixin은 필요한 필드만 적은 `*Host` 인터페이스를 `this` 타입으로 쓴다(예: `ingest-commands.ts` `IngestHost`). commit `7f37905`(2026-07-20)의 제목은 "refactor(main): split main.ts 1304→300 LOC into 6 main-commands modules (#313)"다. [추정] 대안은 서비스 클래스를 따로 두고 plugin이 위임하는 방식이었을 것이다. 저자는 테스트가 `plugin.testLLMConnection()`을 그대로 부르는 호출면을 지키려고 mixin을 골랐다: "the mixin pattern preserves this call surface with zero sites changed"(`connection-commands.ts:7-10`).

### 1.3 핵심 자료 구조

#### `LLMWikiSettings` (types.ts:259-669) — 전 항목

data.json에 그대로 저장되는 설정이다. "UI"는 설정 탭에서 그 값을 바꿀 수 있는 자리다. "UI 없음"은 data.json을 직접 고쳐야만 바뀐다는 뜻이다.

**LLM 연결**

| 필드 | 기본값 | UI | 하는 일 |
|---|---|---|---|
| `provider` | `anthropic` | provider 섹션 | 17개 preset 중 하나(`types.ts:1290-1523`: openai, openai-codex, anthropic, gemini, openrouter, deepseek, minimax, kimi, glm, opencode, bedrock-anthropic, bedrock-openai, ollama, lmstudio, custom, custom-responses, anthropic-compatible) |
| `apiKey` | `''` | provider 섹션 | 평문 필드. v1.25.3부터 SecretStorage로 옮기고 비운다(`main.ts:225-248`) |
| `providerApiKeySecretId` | `karpathywiki-provider-api-key` | 없음 | OS keychain 슬롯 이름. 모든 provider가 한 슬롯을 같이 쓴다(`types.ts:263-269`) |
| `openAICodexSecretId`, `openAICodexModels`, `openAICodexModelsFetchedAt`, `openAICodexUnavailableModels` | | Codex 로그인 UI | ChatGPT Plan(Codex OAuth) 전용 |
| `baseUrl` | `''` | provider 섹션 | |
| `customHeaders` | 없음 | provider 섹션 | 한 줄에 `Name: value`. 원문 문자열로 저장한다. 이유: "so a half-typed line survives a settings round-trip"(`types.ts:274-282`) |
| `model` | `''` | model 섹션 | 기본값이 없다. 원문 "No hardcoded default — user must fetch models or enter manually"(`types.ts:1539`) |
| `availableModels`, `useCustomModel` | | model 섹션 | 받아온 모델 목록과 드롭다운/직접 입력 전환 |
| `usePerTaskModels`, `ingestModel`, `lintModel`, `queryModel`, `*ModelUseCustom` | false/빈값 | model 섹션 | 작업 셋(ingest·lint·query)마다 모델만 다르게. provider·키는 공유. 이유: "per-provider split would 4× the credentials UI and break Test Connection's contract"(`types.ts:622-627`) |
| `bedrockRegion`, `bedrockAuthMethod`(api-key/sso/iam), `bedrockSsoStartUrl`, `bedrockSsoAccountId`, `bedrockSsoRoleName` | us-east-1 / api-key | provider 섹션 | AWS Bedrock 인증. 비밀값은 SecretStorage에만(`types.ts:302-315`) |
| `llmReady` | false | 상태 줄 | Test Connection을 통과해야 true. ingest·lint·query·schema 진입점이 모두 이 값을 본다(§2.2) |
| `thinkingControlCache` | 없음 | 없음 | @deprecated, 읽지 않음(`types.ts:408-428`) |
| `maxTokensPerCall` | 0 | model 섹션 | 0이면 상한 없음. 로컬 모델용(`en.ts:89-90`) |

**LLM 고급(LLM Advanced 섹션, `advancedSettingsMode: 'custom'`일 때만 보임)**

| 필드 | 기본값 | 하는 일 |
|---|---|---|
| `advancedSettingsMode` | `default` | `default`로 돌리면 아래 값을 모두 초기화한다(`advanced-section.ts:64-85`) |
| `disableThinking` | false | 켜면 provider에 thinking 끄기 지시를 보낸다(`types.ts:431-441`) |
| `taskPolicies` | 없음 | 단계별 출력 모드·thinking. 형식 `step=mode:thinking`. 읽을 수 없는 입력은 저장하지 않는다(`advanced-section.ts:102-130`) |
| `extractionTemperature`, `chatTemperature`, `repetitionPenalty` | 없음 | 비우면 provider 기본값 |
| `forcePdfSupport` | false | native PDF 목록 밖 provider에도 PDF를 보낸다. native provider에서는 안 보인다(`advanced-section.ts:150-159`) |
| `extractionTopP`, `samplingSeed` | 없음 | **UI 없음.** `llm-client-wrapper.ts:150-152`에서만 읽는다. seed는 일부 로컬 서버에만 닿는다는 설명이 `types.ts:488-508`에 있다 |

**위키 구성(Wiki Configuration 섹션)**

| 필드 | 기본값 | 하는 일 |
|---|---|---|
| `wikiFolder` | `wiki` | 생성 페이지 폴더. 바꾸면 Obsidian 재시작을 권한다: "Restart Obsidian after changing — engine caches and open Query Wiki panels need to rebind."(`en.ts:221`) |
| `markdownConversionBackend` | `native` | `native`(provider의 PDF 처리) 또는 `mineru`(mineru.net API로 업로드). MinerU를 고르면 토큰 입력칸이 나온다(`wiki-config-section.ts:56-79`) |
| `extractionGranularity` | `standard` | fine/standard/coarse/minimal/custom. §4 참고 |
| `customEntityLimit`, `customConceptLimit` | 5 | custom일 때만. 1~500으로 잘라 넣는다(`wiki-config-section.ts:105-161`, `constants.ts:71`, `:146`) |
| `tagVocabularyMode` | `default` | `custom`일 때만 아래 두 목록이 쓰인다(`core/tag-vocab.ts:4-20`) |
| `customEntityTags`, `customConceptTags` | `''` | chip 입력. CSV로 저장(`tag-chip-input.ts:1-6`) |
| `enableSchema` | true | **아무도 읽지 않는다.** grep 결과 `types.ts`에만 있다. 읽던 줄은 commit `3f8e63e`(v1.8.1, 2026-05-18)에서 지워졌다: `-    if (!this.settings.enableSchema) return '';`(schema-manager.ts). 그런데 UI 문구 `enableSchemaDesc`는 schema 관리 줄의 설명으로 아직 쓰인다(`wiki-config-section.ts:237`, `en.ts:347`) |

**언어**

| 필드 | 기본값 | 하는 일 |
|---|---|---|
| `language` | `en` | UI 언어. 11개(`texts.ts`) |
| `wikiLanguage`, `useCustomWikiLanguage` | `en`, false | 위키 출력 언어. "All generated wiki pages, index, log, and query responses use this language"(`en.ts:355`). 목록 밖 언어는 직접 입력(`language-section.ts:66-104`) |

**자동 유지(Auto Maintenance 섹션, BETA 표시)**

| 필드 | 기본값 | 하는 일 |
|---|---|---|
| `autoWatchSources` | false | 감시 폴더의 `.md` 생성·이름변경·수정을 감지 |
| `watchedFolders` | `[]` | 감시 폴더 목록. "Web Clipper preset" 토글은 `Clippings/`를 넣고 뺀다(`auto-maintain-section.ts:122-135`) |
| `autoWatchMode` | `notify` | `notify`는 알림만, `auto`는 바로 ingest(§2.6) |
| `autoIngestNotificationLevel` | `notice` | auto 모드 완료 알림. `modal`이면 보고서 창(`main.ts:432-445`) |
| `autoWatchDebounceMs` | 5000 | UI는 초 단위 1~60(`auto-maintain-section.ts:159-183`). 첫 변경 뒤 최대 60초 상한(`auto-maintain.ts:31`) |
| `periodicLint` | `off` | off/daily/weekly/monthly. hourly는 v1.22.2에서 뺐다(`settings-migrations.ts:68-73`, commit `0490f71`) |
| `autoSmartFix` | false | 자동 lint가 끝나면 Smart Fix All을 승인 없이 돌린다(`controller.ts:634-637`) |
| `startupCheck` | true | 더는 읽지 않는다. 시작 점검은 항상 돈다(commit `e0b8ca8`) |
| `startupCheckNoticeLevel` | `visible` | 시작 점검 결과 알림을 보일지 |

**하단 "Advanced settings" 패널(`showAdvancedSettings`일 때만 보임)**

| 필드 | 기본값 | 하는 일 |
|---|---|---|
| `showAdvancedSettings` | false | 끄면 아래 값 대부분을 기본값으로 되돌린다(`advanced-settings-section.ts:52-72`) |
| `maxConversationHistory` | 30 | Query 대화 기록 길이. 1/10/30/50/100/500 중 고름 |
| `writePdfMarkdownToVault` | false | PDF 변환 결과를 `<basename>.pdf.md`로 vault에도 쓴다 |
| `analyzeEmbeddedImages`, `saveEmbeddedImageEvidence` | false | 노트에 박힌 로컬 이미지를 LLM에 보내 분석 |
| `slugCase` | `lower` | 파일 이름 소문자화 여부. 새 파일에만 적용(`types.ts:597-602`) |
| `minAliasLength` | 없음(=2) | 2~6. 패널을 닫아도 초기화하지 않는다(`advanced-settings-section.ts:52-72`에 없음) |
| `createWelcomeNote` | true | 첫 실행 환영 노트. 패널을 닫아도 유지 |
| `skipMentionOnlyCandidates` | false | 원문에서 괄호·나열에만 나온 후보를 버리는 gate(ingest 갈래). 패널을 닫으면 false로 돌아간다(`advanced-settings-section.ts:68-69`) |
| `createStubsForUnresolvableLinks` | true | Fix Dead Links가 빈 placeholder 페이지를 만들지 |
| `lintJaccardLinkThreshold`, `lintJaccardBodyGate`, `lintBigramThreshold` | 없음(0.4/0.2/0.4) | lint 중복 후보 임계값(`constants.ts:614`, `:629`, `:642`) |
| `lintDedupIncludeSources` | 없음(=켬) | sources/ 페이지도 중복 검사에 넣을지 |
| `gateDissentStubs` | false | **UI 없음.** `wiki-engine.ts:1140`에서만 읽는다 |

**그 밖**

| 필드 | 하는 일 |
|---|---|
| `pageGenerationConcurrency` (기본 3), `batchDelayMs` (기본 500, UI 초깃값 300) | provider 섹션 슬라이더. §5 참고 |
| `customQueryInstructions` | Query 패널에서만 편집. 5000자 상한(`constants.ts:552`) |
| `queryHistory`, `lastOfferedQueryHash` | Query 대화 기록과 "위키에 저장?" 제안 중복 방지 해시 |
| `_migrated_*` 4개 | 이관 표시. UI에 안 보이게 밑줄로 시작(`types.ts:383-400`) |

`batchDelayMs`의 기본값은 `DEFAULT_SETTINGS`에서 500인데(`types.ts:1580`), 슬라이더와 엔진의 fallback은 300이다(`provider-section.ts:353`, `wiki-engine.ts:1359`). 새로 설치하면 500이 쓰인다.

#### 보고서·작업 상태 구조

- `IngestReport`(types.ts:725-751): `sourceFile`, `createdPages[]`, `updatedPages[]`, `entitiesCreated`, `conceptsCreated`, `failedItems[{type,name,reason}]`, `contradictionsFound`, `success`, `errorMessage?`, `trigger?: 'auto'|'manual'`, `elapsedSeconds?`, `skippedFiles?`, `totalFilesInFolder?`, `cancelled?`, `skipped?`, `rejectedFiles?[{path,reason,detail?}]`, `embeddedImageAnalysis?`. `trigger`는 #204를 고치며 들어왔다(types.ts:735-741).
- `IngestOptions`(types.ts:762-783): `batchCtx?`, `interactive?`, `forceReingest?`, `trigger?`, `contentOverride?`. `interactive`가 true일 때만 중복 내용에서 재수집 확인 창을 띄운다.
- `BatchRequirementsContext`(types.ts:754-759): `seen`(이번 batch에서 본 내용 해시), `ingested`(이미 위키에 있는 해시 스냅샷).
- `IngestJob`(core/ingest-queue.ts): `id`, `file`, `status`(pending/running/completed/failed), `error?`, `addedAt`, `startedAt?`, `finishedAt?`, `abortController`. 메모리에만 있고 다시 열면 비어 있다.
- `RowState`(ui/modals/multi-file-row-state.ts:27-34): `checked`, `disabled`, `classes`, `labelKey`('multiFileRowIngested'|'multiFileRowDrifted'|null).
- `IngestDiskState`(core/ingest-state.ts:24): `'none'|'ingested'|'drifted'`.
- `LintCounts`(ui/modals/types.ts:22-33): `deadLinks`, `emptyPages`, `orphans`, `duplicates`, `pagesMissingAliases`, `pollutedPages`, `tagViolations`, `ungroundedQuotes`.
- `LintFixCallbacks`(ui/modals/types.ts:8-20): `onCompleteAliases`, `onFixDeadLinks`, `onFillEmptyPages`, `onDeleteEmptyStubs`, `onLinkOrphans`, `onAnalyzeSchema`, `onMergeDuplicates`, `onFixAll`, `onFixPollutedPages`, `onRetagViolations`.
- `SchemaSuggestion`(types.ts:697-706): `timestamp`, `source`, `changes_needed`, `suggestions`, `newSchemaBody?`.
- `WriteIntent`(types.ts:1081-1114): `guard`, `notify`, `create`, `cancel('ingest'|'lint'|'none')`. 쓰기마다 어느 층을 거칠지 이름으로 밝힌다. 원문 "There is no default. A default is how the ambiguity this type exists to remove would come back."(types.ts:1078-1079)
- `ProgressScope`(core/progress-notification.ts:16-23): IngestManual, IngestAutoWatch, LintManual, LintPeriodic, SmartFixManual, AutoMaintenance. 앞의 하나·셋을 뺀 배경 작업은 상태 표시줄에만 진행을 보인다(`:31-46`).

## 2. 동작 흐름

### 2.1 플러그인 시작

1. `loadSettings()`: 이관을 적용하고, 평문 API 키를 SecretStorage로 옮긴다. 옮기기가 실패하면 평문을 지우지 않는다(`main.ts:225-248`). 원문 "Phase 2 (commitSettingsMigrationV1_25_3) runs here ONLY after the IO write succeeds. On failure, plaintext survives in memory and on disk — no data loss."(`main.ts:220-224`)
2. 예전 사용자(`llmReady` 키가 없는 data.json)는 설정이 갖춰졌으면 `llmReady=true`로 믿어 준다(`main.ts:292-316`).
3. 매니저들을 만들고 시작 점검을 부른다(`main.ts:155-161`).
4. 시작 점검(`auto-maintain.ts:355-533`)은 3초 기다린 뒤 다섯 단계를 돈다. Phase 0 환영 노트(필요하면 비동기로 LLM 번역), Phase 1 폴더 구조 확인, Phase 2 `sources:` 필드 정규화(쓰기 있음), Phase 3 `generation_complete: false`로 멈춘 페이지 보관 처리(휴지통), Phase 4.5 log.md 머리말 이관. 결과 알림은 `startupCheckNoticeLevel`이 `visible`일 때만 10초 보인다(`:530-533`). 이 점검은 끌 수 없다. commit `e0b8ca8`의 메시지: "startupCheck toggle is permanently on. The user-facing control is now a new startupCheckNoticeLevel dropdown"

### 2.2 설정과 연결 테스트

- 설정 탭은 `tempSettings` 사본을 편집한다(`settings.ts:47-54`). 탭을 떠날 때 바뀐 것이 있으면 자동 저장한다(`settings.ts:99-116`). 언어 섹션의 Save 버튼으로도 저장한다(`language-section.ts:54-63`).
- provider·모델을 바꾸면 `llmReady=false`가 된다(`settings.ts:597-599`). 그러면 다시 Test Connection을 눌러야 한다.
- Test Connection(`connection-commands.ts:62-195`)은 결정적 검사를 먼저 한다. Codex 자격, Bedrock 자격, API 키, 빈 모델을 차례로 본다. 빈 모델 검사가 따로 있는 이유: "A blank model still goes on the wire as `"model": ""`, and the provider answers with its own routing error ... so a model that was never selected reads as a broken Base URL."(`:104-112`)
- 그다음 LLM을 실제로 부른다. 작업별 모델을 쓰면 ingest·lint·query 모델을 하나씩 부른다(`:95-100`). 프롬프트는 `'Test connection. Please reply "Connection successful".'`이고 `max_tokens`는 `TOKENS_QUERY_MODEL_DETECT`(2000)다(`:123-131`).
- Codex에서 404가 나면 그 모델을 사용 불가 목록에 넣고 다른 모델로 한 번 더 시도한다(`:132-152`).
- 성공하면 `llmReady=true`, 위키 폴더 구조가 없으면 만든다(`:154-170`).
- `requireLLMReady()`가 false를 돌려주면 명령은 알림만 띄우고 끝난다(`:196-200`). 이 검사는 ingest 진입점 넷, query, lint, schema 분석이 모두 첫 줄에서 한다.

이 gate의 이유는 commit `9798a5d`(2026-05-26)가 밝힌다: "Users must now complete Provider → API Key → Fetch Models → Test Connection before ingest, lint, query, or schema features are available. This prevents silent failures from stale default models (especially Ollama's llama3) and guides new users through proper setup." 대안이었던 "기본 모델을 하드코딩해 바로 쓰게 하기"를 같은 commit에서 버렸다.

### 2.3 단일 파일 ingest

1. 사용자가 명령 `ingest-source`로 파일을 고르거나, 리본 아이콘으로 지금 연 파일을 넣는다.
2. 결정적 검사: `llmReady`, `llmClient` 존재(`ingest-commands.ts:85-89`, `:106-110`).
3. 진행 알림(Notice, 닫히지 않음)과 상태 표시줄을 연다(`main.ts:399-410`).
4. `wikiEngine.ingestSource(file, {interactive:true})`(ingest 갈래). 엔진의 요구 조건 gate가 빈 본문·지원하지 않는 확장자·내용 해시 중복을 거른다(`wiki-engine.ts:584-599`). 중복이면 interactive일 때만 `onConfirmReingest`를 불러 확인 창을 띄운다(`wiki-engine.ts:1035-1036`, `main.ts:136-145`). 문구: "The content of "{filename}" is already in the wiki. Re-ingest it anyway?"(`en.ts:795`)
5. 끝나면 `onIngestDoneDispatch`가 Query 그래프 캐시를 비우고, 수동이면 `IngestReportModal`을 연다(`main.ts:422-430`).
6. 실패하면 오류 알림을 8초 띄운다(`ingest-commands.ts:96-101`).

보고서 창(`IngestReportModal-class.ts:48-162`)은 정보만 보인다. 버튼은 Close 하나다. 만든 페이지·고친 페이지·실패 항목·거절된 파일·모순 수를 보여 준다. 실패 항목 안내 문구는 "You can manually create the corresponding pages, or lower the extraction granularity and re-ingest the source file."(`en.ts:525`)이다.

### 2.4 여러 파일 ingest (`runBatchIngest`, `ingest-commands.ts:181-326`)

1. PDF 캐시 정리를 비동기로 시작한다(`:182`).
2. 파일마다 `isAlreadyIngested`를 본다(`:190-199`). 이 함수는 `wiki/sources/<slug>.md`가 있고 그 페이지가 이 노트에서 만들어졌는지(`source_file:` 또는 `sources:`)를 본다(`:57-82`, `core/ingest-state.ts:42-48`). 맞으면 건너뛴다. 기록된 출처가 없는 페이지는 "있으면 이미 수집됨"으로 친다. 원문: "absence of evidence is not proof of a different owner"(`ingest-state.ts:35-36`)
3. 건너뛴 수를 6초 알림으로 알린다(`:205-214`). 전부 건너뛰면 끝낸다.
4. 엔진의 완료 콜백을 잠시 빌려 보고서를 모은다(`:224-230`). 끝나면 되돌린다(`:274`). 되돌리는 이유: "kept, every later single or watcher ingest of the session reported into this array — no report, the Notice never closed."(`:224-226`)
5. 파일을 **하나씩 차례로** ingest한다(`:246-272`). 한 파일 안에서 페이지 생성 LLM 호출만 `pageGenerationConcurrency`만큼 병렬이다(`wiki-engine.ts:1358-1381`).
6. 파일 하나가 실패해도 다음 파일로 간다(`:266-271`). 사용자가 취소하면(`wikiEngine.wasCancelled`) 멈춘다(`:257-262`).
7. 모은 보고서를 합쳐 보고서 창을 하나 연다(`:278-318`).

폴더 ingest는 `isIngestableSource`로 고른 폴더 아래만 받는다. 위키 폴더와 `.obsidian`은 뺀다(`:137-151`). 이유는 이슈 #364·#383·#502에서 나온다. 맨 문자열 접두사 비교가 형제 폴더를 새게 하고, vault 루트를 고르면 위키 폴더 자신을 다시 수집했다(`ingest-commands.ts:137-142` 주석).

### 2.5 여러 파일 고르기 창 (MultiFileSuggestModal)

- 왼쪽은 폴더 트리와 체크박스, 오른쪽은 실시간 작업 큐다. 체크 → "Add to queue" 두 단계다(`MultiFileSuggestModal-class.ts:179-209`). 창을 닫아도 ingest는 계속된다(`:206-208`).
- 창을 열면 디스크를 읽어 행마다 상태를 정한다(`:506-526`). 이미 수집했고 바뀌지 않은 노트는 회색 체크로 잠근다. 수집한 뒤 본문이 바뀐 노트는 "Note changed since ingest" 표시만 하고 잠그지 않는다(`multi-file-row-state.ts:36-66`, `en.ts:971-972`). 바뀜 판정은 source 페이지의 `contentHash`와 노트 본문 해시를 비교한다. 출처가 둘 이상인 페이지는 판정하지 않는다(`ingest-state.ts:70-77`).
- 바뀐 노트에 재수집 버튼을 일부러 두지 않았다. 이슈 #598 원문: "No re-ingest action on the changed rows. A re-ingest is additive rather than revising (#220 Tier 1/2), so offering a button there would invite exactly the operation that damages the page."
- "Cancel all"과 행마다 ✕ 버튼이 있다(`:166-178`, `:620-635`). §8 결함 F1을 볼 것.

### 2.6 폴더 감시 (auto-maintain.ts:64-259)

1. `autoWatchSources`가 켜져 있으면 레이아웃이 준비된 뒤 이벤트 넷을 등록한다. vault `create`·`rename`·`modify`, metadataCache `resolved`(`:64-96`).
2. 이벤트마다: `.md`만, 감시 폴더 안만, 최근 플러그인이 쓴 파일(120초)은 빼고, 같은 mtime은 한 번만 받는다(`:133-160`).
3. debounce가 끝나면 모은 파일을 처리한다(`:172-192`).
4. `notify` 모드: "Wiki: {count} file(s) changed in sources/. Run "Ingest Sources" to process." 알림을 8초 띄운다(`:225-229`, `en.ts:459`). 버튼은 없다. 사용자가 직접 ingest 명령을 불러야 한다.
5. `auto` 모드: 파일마다 `ingestSource(file, {batchCtx, trigger:'auto'})`를 차례로 부른다(`:230-258`). `isAlreadyIngested`를 거치지 않는다. 그래서 수정된 노트는 다시 수집된다. 내용이 같으면 엔진의 해시 gate가 조용히 건너뛴다(interactive가 아님).
6. 완료 알림은 `autoIngestNotificationLevel`을 따른다(`main.ts:432-445`).

감시는 `.md`만 본다(`auto-maintain.ts:140`). PDF·Office 파일은 감시로 들어오지 않는다.

### 2.7 Lint와 사용자 승인

`lintWiki`(query-lint-commands.ts:77-95)가 `runLintWiki`를 부른다(lint 갈래). 끝나면 보고서를 log.md에 쓰고(`controller.ts:627-628`), 트리거에 따라 갈린다(`controller.ts:634-655`).

- 수동: `LintReportModal`을 연다.
- 자동 + `autoSmartFix`: 알림 하나를 띄우고 Smart Fix All을 승인 없이 돌린다.
- 자동 + autoSmartFix 꺼짐: 발견 수만 알림으로 알린다.

`LintReportModal`(LintReportModal-class.ts:32-166)은 Markdown 보고서를 50vh 높이로 보이고 버튼을 네 층으로 둔다.

| 층 | 버튼 | 근거 |
|---|---|---|
| 1 사전 작업 | 별칭 채우기(N), 목록 밖 태그 다시 달기(N) | `:87-109` |
| 1b | 오염된 페이지 고치기(N) | `:111-120` |
| 2 인과 순서 | 중복 병합 → 죽은 링크 → 고아 연결 → 빈 페이지 채우기 / 빈 stub 삭제 | `:122-141` |
| 3+4 | Smart Fix All(강조, 전체 수) / Analyze schema | `:143-165` |

승인 단위는 **분류 하나 전체**다. 예를 들어 "중복 병합" 버튼은 찾은 중복 쌍 전부를 병합한다(`controller.ts:387-399`). 쌍을 하나씩 고르는 UI는 없다. 다시 달기 버튼에 대한 저자 주석도 같은 말을 한다: "The user gets a single bulk button "Retag N page(s) with LLM" — no per-page approval."(`controller.ts:402-404`) 버튼을 누르면 창은 바로 닫힌다(`LintReportModal-class.ts:79-82`). 결과는 알림과 log.md에 남는다.

Smart Fix All의 순서는 오염 페이지 → 별칭 → 중복 → 죽은 링크 → 고아 → 빈 페이지다(`controller.ts:448-470` 이하). 별칭을 먼저 채우는 이유: "Aliases are required for Tier 1 duplicate signals (crossLang) → Missing aliases → duplicate detection misses true duplicates → downstream fixes incomplete"(`controller.ts:466-468`)

README FAQ는 "Lint shows counts before running fixes — nothing is charged without your approval."라고 한다(README.md:352). 이 말은 수동 lint에만 맞다. `autoSmartFix`를 켜면 승인 없이 고친다(`controller.ts:634-637`).

### 2.8 Schema 제안과 적용

1. Lint 보고서 창에서 "Analyze schema"를 누른다. lint 요약을 문맥으로 넘긴다(`controller.ts:261`).
2. `runSchemaAnalyze`(schema/analyze.ts:47-)가 `llmReady`를 보고, lint 취소 장치를 빌려 쓰고, "analyzing" 알림을 띄운 채 `schemaManager.suggestSchemaUpdate`를 부른다(LLM 호출 1회, 상한 `TOKENS_SCHEMA_SUGGESTION` 4096, `constants.ts:482`).
3. 결과가 오면 변경 필요 여부와 관계없이 `SchemaDiffModal`을 연다. 이유: "Without the Modal, the user is left wondering "what did the LLM think?" after a flash of Notice."(`analyze.ts` 주석, 위 출력)
4. 창은 LLM의 이유 문장, 줄 단위 LCS diff(왼쪽 현재·오른쪽 제안), +/− 줄 수를 보인다(`schema-diff-modal.ts:160-305`). 현재 본문은 창을 연 뒤 비동기로 채운다(`schema-commands.ts:98-101`).
5. 버튼은 Open file, Cancel, Apply 셋이다. 변경이 없으면 Apply가 꺼진다(`schema-diff-modal.ts:290-292`).
6. Apply는 `config.md`를 읽고 `config.md.bak.<iso>` 백업을 만든 뒤 최근 3개만 남기고, frontmatter는 두고 본문만 LLM의 새 본문으로 바꾼다. `auto_suggestion_count`를 1 올리고 `applied_suggestion:`에 제안 시각을 적는다(`apply-suggestion.ts:6-22`, `:55-99`, `:168`). 알림이 백업 경로와 복구 방법을 10초 보인다(`schema-commands.ts:76-80`).
7. "Regenerate"(힌트를 주고 다시 생성) 버튼은 코드는 연결돼 있지만 UI에서 주석으로 숨겼다(`schema-diff-modal.ts:217-237`, `:265-282`). 원문: "we're only hiding the UI to ship a minimal v1.22 release." v1.23에 다시 켜겠다고 했지만 HEAD에서도 숨겨져 있다.

적용 단위는 본문 전체다. 제안 중 일부만 받는 길은 없다. 일부만 원하면 Open file로 열어 손으로 고친다(`schema-diff-modal.ts:242-255` 주석).

이 흐름의 설계 이유는 commit `4692a4f`(v1.22.0)가 밝힌다: "'Suggest Schema Updates' was a silent command-palette invocation that wrote suggestions.md without showing the user what would change. Admins had to read the suggestions markdown, then manually edit schema/config.md, with no preview and no undo." 또 "The apply path is a verbatim replace, not a patch — the LLM owns the full new body so the diff is meaningful." 대안이었던 "제안 목록을 patch로 적용"은 diff가 의미를 잃는다는 이유로 버렸다.

설정 탭에는 schema 버튼이 둘 더 있다(`wiki-config-section.ts:234-259`). "View schema"는 파일을 연다. "Regenerate Default Schema"는 확인 창 없이, 백업 없이 `config.md`를 기본 본문으로 덮어쓴다(`schema-manager.ts:412-440`: `vault.process(existing, () => content)`). §8 F4를 볼 것.

### 2.9 기록 패널 (HistoryModal)

`wiki/log.md`를 읽어 파싱하고(`HistoryModal-class.ts:68-84`), 검색어·종류(전체/ingest/maintenance/fix/contradictions)·기간(1일·3일·1주·1달·직접)으로 거른다(`:93-119`, `history-modal/types.ts:22-25`). 항목마다 한 줄 요약과 이전 같은 종류 항목 대비 KPI 변화를 보인다(`types.ts:39-80`). 기록의 원천은 vault 안의 Markdown 파일 하나다. 별도 DB는 없다. log.md 쓰기는 page guard를 거치지 않는다(`LOG_WRITE_INTENT`, `types.ts:1196-1220`).

자동 ingest·자동 lint의 완료 알림은 이 패널을 가리킨다(`main.ts:443-444`, `controller.ts:639`). 이 결정은 #204에서 나왔다. 사용자가 "The modal steals focus from the active writing/editing context"라고 보고했고, 저자는 "A fix completed in the background should report, not block."이라고 답했다.

### 2.10 주기 lint (auto-maintain.ts:271-347)

`setInterval`로 매일·매주·매월 돈다. 돌 때 감시 폴더 안 파일의 mtime이 마지막 lint 이후 바뀌었는지 본다. 안 바뀌었으면 건너뛴다. 감시 폴더가 비어 있으면 항상 돈다(`:336-347`). Obsidian이 켜져 있는 동안만 돈다. 시각은 플러그인을 불러온 시점부터 센다. §8 F2·F3을 볼 것.

### 2.11 취소

- 상태 표시줄을 클릭하거나 `cancel-ingestion` 명령을 쓴다. ingest가 돌고 있으면 ingest를, 아니면 lint를 취소한다(`command-registry.ts:96-106`, `:156-162`).
- 엔진은 ingest용과 lint용 AbortController를 따로 둔다. `lint-wiki`는 ingest 중인지 검사하지 않는다(types.ts:1105-1113 원문 "they overlap, because `lint-wiki` is registered without an `isIngesting()` guard").
- `ingestSource`는 이미 컨트롤러가 있으면 새로 만들지 않는다(`wiki-engine.ts:974-978`). 그래서 수동 ingest와 감시 ingest가 동시에 돌면 같은 취소 신호를 나눠 쓴다. [추정] 전역 잠금이 없어서 두 경로가 같은 페이지를 동시에 쓸 수 있다(사례: 진입점 넷과 감시 경로 어디에도 `isIngesting()` 대기나 거절이 없다. `ingest-commands.ts:84-179`, `auto-maintain.ts:212-259`).

### 2.12 이 갈래의 LLM 호출 지점

| 지점 | 프롬프트·상한 | 근거 |
|---|---|---|
| Test Connection | 고정 문장, 2000 토큰 | `connection-commands.ts:123-131` |
| 환영 노트 번역 | 시작 점검 Phase 0, 비동기 | `auto-maintain.ts:363-389`, commit `e0b8ca8` |
| Schema 제안 | `PROMPTS.suggestSchemaUpdate`, 4096 토큰 | `schema/analyze.ts`, `constants.ts:482` |
| Query "위키에 저장?" 평가 | 대화를 저장할 가치가 있는지 JSON으로 판정 → `SuggestSaveModal` | `QueryView-class.ts:400-433` (query 갈래) |

나머지 LLM 호출(추출·병합·lint fix)은 다른 갈래다. 버튼이 그 호출을 시작할 뿐이다.

### 2.13 결정적(코드) 검사 지점

| 검사 | 어디서 | 근거 |
|---|---|---|
| LLM 준비 | 모든 핵심 진입점 | `connection-commands.ts:196-200` |
| 빈 모델 | Test Connection | `connection-commands.ts:104-112` |
| 이미 수집됨(소유권) | 폴더·여러 파일 ingest | `ingest-commands.ts:57-82`, `ingest-state.ts:42-48` |
| 본문 바뀜(해시) | 여러 파일 창 표시 | `ingest-state.ts:70-77` |
| 빈 본문·확장자·내용 중복 | 모든 ingest | `wiki-engine.ts:584-599` |
| 폴더 경계 | 폴더 ingest, 감시, 파일 고르기 | `core/folder-scope.ts`, `ingest-commands.ts:145-151`, `auto-maintain.ts:116-128` |
| 숫자 범위 잘라 넣기 | 설정 입력 | `wiki-config-section.ts:113-125`, `auto-maintain-section.ts:166-177`, `advanced-settings-section.ts:154-174` |
| taskPolicies 형식 | 설정 입력 | `advanced-section.ts:115-128` |
| 최근 쓴 파일 무시(120초) | 감시 | `auto-maintain.ts:195-201` |

### 2.14 실패·재시도

- LLM 호출 재시도: 5xx/429에 최대 2회, 지수 backoff 1초 기준(`constants.ts:495-499`).
- batch 안 일시 실패 재시도: 2초 뒤 한 번(`constants.ts:84-95`).
- batch 지연 `batchDelayMs`: 병렬 묶음 사이 대기. 최대 10초(`constants.ts:82`). 상한을 2초에서 10초로 올린 이유는 이슈 #318: Gemini 무료 등급에서 "too much 429 because of by minute rate limit".
- 파일 단위 실패는 batch를 멈추지 않는다(`ingest-commands.ts:266-271`). 실패 항목은 보고서의 `failedItems`·`rejectedFiles`에 남는다.
- 감시 ingest의 실패는 성공/실패 수만 알린다(`auto-maintain.ts:246-257`).
- 설정 저장 실패(SecretStorage IO 실패)는 평문 키를 지우지 않고 저장을 건너뛴다(`settings.ts:171-186`). 원문 "Returns false when SecretStorage IO failed and the caller must NOT commit."

## 3. 사용자가 누르는 것과 승인하는 것

| 결정 | 누가 정하나 | 승인 단위 | 근거 |
|---|---|---|---|
| 어떤 문서를 넣을지 | 사람(수동 ingest) 또는 감시 폴더(auto) | 파일 | §2.3-2.6 |
| 같은 내용을 다시 넣을지 | 사람 (단일 ingest만) | 파일 | `main.ts:136-145` |
| 무엇이 페이지가 될지, 어느 기존 페이지와 같은지, 별칭 | LLM과 코드. 사람에게 묻지 않음 | 없음 | 이슈 #330 §1 원문 "There is no confirmation point in `analyzeSource` → `resolvePagePath` → `createNewPage`." |
| 결과 확인 | 사람이 보고서 창·기록 패널을 읽음 | 읽기만 | `IngestReportModal-class.ts:48-162` |
| lint 고치기 | 사람(수동) 또는 자동(autoSmartFix) | 분류 하나 전체 | `LintReportModal-class.ts:122-141` |
| schema 변경 | 사람이 diff를 보고 Apply | 본문 전체 | §2.8 |
| 대화를 위키에 저장 | LLM이 제안, 사람이 예/아니오 | 대화 하나 | `SuggestSaveModal-class.ts:38-60` |
| 페이지 덮어쓰기 막기 | 사람이 frontmatter에 `reviewed: true` | 페이지 | README.md:324. 막는 방식은 다른 갈래(병합) 영역이다. `merge-page.ts:10-12`는 "The page's existing content is locked; we only ask the LLM to draft a small new block."이라고 쓴다 |

프로젝트 원칙과 실제 사이에 간극이 있다. AGENTS.md:300은 "Human-in-the-loop — LLM suggests, user decides"라고 쓴다. 기여자 DocTpoint가 이슈 #330에서 이를 짚었다: "All four hold in the query path. **None of them holds in the ingest path.**" 저장소는 이 간극을 인정하고 "Preview-Confirm gate"를 미완성 설계 항목으로 둔다. ROADMAP.md:375 원문: "UX cost evaluation is still pending discussion — the gate is named as the smallest kernel of the Karpathy cycle". AGENTS.md:439도 같은 말을 한다.

## 4. 설정으로 바뀌는 동작

| 설정 | 바뀌는 것 | 근거 |
|---|---|---|
| `extractionGranularity` | ingest: batch 크기·batch 수·문서당 최대 항목(fine 100, standard 50, coarse 10, minimal 5) + 추출 프롬프트 문구. 2만 자 미만 문서는 600자당 1개로 상한을 더 낮춘다. 빈 페이지 채우기(lint): entity·concept 상한(fine 6/6, standard 3/3, coarse 2/2, minimal 1/2) | `core/batch-limits.ts:27-75`, `system-prompts.ts:189-226`, `constants.ts:280-286`, `:881-887` |
| `tagVocabularyMode` + custom 목록 | 프롬프트에 주는 하위 종류 목록, 쓰기 검사·lint·retag가 판정하는 목록 | `core/tag-vocab.ts:4-20`, commit `170205b` |
| `wikiLanguage` | 페이지·색인·로그·Query 답의 언어. 프롬프트 자체는 영어로 두고 언어 지시를 넣는다 | `en.ts:355`, commit `23fd9ab` "convert all LLM prompts to English" |
| `skipMentionOnlyCandidates` / `gateDissentStubs` | 후보를 버리거나 stub으로 만든다 | `types.ts:556-579` (ingest 갈래) |
| `createStubsForUnresolvableLinks` | Fix Dead Links가 빈 페이지를 만들지 | `types.ts:581-591` |
| `minAliasLength` | 쓰는 별칭의 최소 길이 | `types.ts:604-610` |
| `slugCase` | 새 파일 이름 대소문자. 독일어 명사처럼 소문자가 뜻을 바꾸는 언어에 `preserve` 권장 | `en.ts:93-96` |
| `markdownConversionBackend` | PDF만(native) / PDF·이미지·Office(MinerU, 외부 업로드) | `wiki-engine.ts:985-1015`, `docs/PDF-OCR-GUIDE.md:18-22` |
| `autoWatch*`, `periodicLint`, `autoSmartFix` | 사람 없이 도는 범위 | §2.6, §2.10, §2.7 |
| `usePerTaskModels` 등 | 작업마다 다른 모델(예: ingest는 싼 모델, lint는 강한 모델) | `types.ts:622-656`, 이슈 #367·#368의 사용자는 lint에 deepseek-v4-pro, ingest·query에 deepseek-v4-flash를 썼다 |
| `customQueryInstructions` | Query 시스템 프롬프트 뒤에 붙는 지시. 다른 작업에는 영향 없음 | `types.ts:612-620` |

## 5. 큰 vault에서의 성능 설정

사용자가 고칠 수 있는 손잡이는 넷뿐이다.

| 설정 | 범위 | 효과 |
|---|---|---|
| `pageGenerationConcurrency` | 1~5 슬라이더 | 한 문서 안 페이지 생성, related page 갱신, lint fix runner, lint dedup 검증의 병렬 수(`wiki-engine.ts:1358`, `:1458`, `fix-runners.ts:58` 등, `dedup-phase.ts:298`) |
| `batchDelayMs` | 100~10000ms | 병렬 묶음 사이 대기 |
| `extractionGranularity` | | 문서당 LLM 항목 수. UI 문구가 "Use Minimal/Coarse for folders with many files to save time and cost."라고 권한다(`en.ts:375`) |
| lint dedup 임계값 3개 + sources 포함 여부 | | 중복 후보 수 |

나머지 규모 대응은 코드 상수다(바꿀 수 없음).

| 상수 | 값 | 이유 원문 | 근거 |
|---|---|---|---|
| `CANDIDATE_WINDOW_TOP_K` | 30 | "the model did not find a synonym's target in it (0 of 18) while it found the same targets 9 of 9 times in a 30-entry window" | `constants.ts:231-241` |
| `LINT_DEDUP_BUCKET_PREFIX_LEN` | 2 | "eliminates the O(N²) memory peak that OOMs at ~2000 pages" (CJK·키릴 제목은 접두사 버킷에서 빠진다고 스스로 적음) | `constants.ts:570-586` |
| `LINT_DEDUP_BATCH_SIZE` | 50 | 2141쪽 vault에서 100개 batch가 "yielded 0-byte responses on 9/10 batches" | `constants.ts:745-758` |
| `LINT_DEDUP_PROMPT_CHAR_BUDGET` | 7000자 | thinking 모델이 출력 예산을 다 써서 빈 응답 | `constants.ts:760-779` |
| `DEFAULT_QUERY_TOP_N_PAGES` / `MAX_` | 10 / 20 | 2137 노드 vault에서 5쪽은 부족 | `constants.ts:785-809` |
| `MAX_PAGE_CONTENT_CHARS` | 12800 | 병합으로 커진 페이지가 Query 문맥을 키우지 않게 | `constants.ts:484-489` |
| `YIELD_EVERY_ITERATIONS`, `LINT_YIELD_*` | 200, 50, 500 | O(n²) 루프 중 UI 멈춤 방지 | `constants.ts:536-568` |
| PDF 캐시 | 100MB, 1000개, 개당 10MB, 30일 | "Lower bound on Obsidian startup scan time" | `constants.ts:105-119` |

규모의 실측 사례는 이슈에 있다. #367: 11,610쪽 터키어 vault에서 lint가 60분 동안 API 호출 0회로 멈췄다. 사용자는 "Lint is effectively capped around ~1.2–1.5k pages"라고 썼고, 우회책은 "all bulk lint/triage delegated to an external coding agent; plugin used for query + single-file ingest only"였다. v1.25.10이 fix runner를 `pageGenerationConcurrency` 묶음으로 나눠 일부 고쳤다(저자 답글). #473: 마지막 lint 분석이 위키 전체 문맥을 보내 313,754 토큰 요청으로 HTTP 400이 났다(제목). MODEL-GUIDE는 "Context window ≥ 200K tokens for vaults over ~500 pages"를 권한다(docs/MODEL-GUIDE.md:13).

[추정] 파일 단위 ingest가 차례로만 도는 것은 엔진이 취소 신호·완료 콜백·내용 해시 스냅샷을 한 벌만 갖기 때문이다(사례 3개: `wiki-engine.ts:974-978` 컨트롤러 하나, `ingest-commands.ts:224-230` 완료 콜백 바꿔치기, `types.ts:754-759` batch 문맥 하나). 저자가 이유를 적은 곳은 찾지 못했다.

## 6. 설계 결정과 이유

(a)는 작성자가 밝힌 이유, (b)는 추론이다.

**D1. 플러그인 하나가 실행 환경이다(서버·DB·임베딩 없음).**
(a) README.md:69-73 "Obsidian is the runtime. No terminal, no separate app, no Docker, no Python." / "Zero dependencies. No embedding model, no vector database". 임베딩을 뺀 이유: "most providers we support ... don't ship a `/v1/embeddings` endpoint at all"(README.md:255, 이슈 #175). 대안은 CLI·데스크톱 앱(README의 비교표: nashsu Tauri 앱, SamurAIGPT 스킬, atomicstrata CLI). 대가도 README가 적는다: "Want a hosted SaaS with team collaboration — there's no backend, no server, no shared state"(README.md:93). 이력: 헤드리스 실행은 형제 저장소 `green-dalii/obsidian-llm-wiki-cli`(npm `karpathywiki-cli`)로 따로 낸다(README.md:392). 레포 안 `tools/dev-instrument/`는 측정용이다. 이유: 마켓 리뷰 봇이 저장소 전체 `.ts`를 검사해 예전 CLI가 "~70 Bot findings"를 쌓았다(tools/dev-instrument/README.md "Why it exists", 이슈 #507).

**D2. LLM 연결을 통과해야 기능이 열린다(`llmReady` gate).**
(a) commit `9798a5d` "This prevents silent failures from stale default models (especially Ollama's llama3) and guides new users through proper setup." 대안: 기본 모델 하드코딩. 같은 commit에서 버림. 모델 기본값도 비워 둔다(`types.ts:1539`).

**D3. 비밀값은 OS keychain(SecretStorage)에만, 두 단계 이관.**
(a) `main.ts:215-224`, `settings.ts:150-170` "On Windows 10 Credential Manager failure ... Now we surface a recoverable Notice AND return `false`". 이력: v1.25.3 #182 도입, v1.25.4 #339에서 "지운 뒤 쓰기 실패" 사고로 순서를 바꿈. 대안: data.json 평문(이전 방식).

**D4. 감시 기본값은 꺼짐, 켜도 기본은 알림만.**
(a) `en.ts:454` 비용 경고 "Auto-maintenance features consume API tokens. "Auto Ingest" triggers LLM calls on every source file change." README.md:352 "Auto-Maintenance is OFF by default." 섹션에 BETA 표시(`en.ts:417`). (b) [추정] notify 모드에 바로 ingest하는 버튼을 두지 않은 것은 알림이 Obsidian Notice라서 버튼을 둘 자리가 없기 때문이다(사례: `auto-maintain.ts:225-229`가 문자열 Notice만 만든다). 저자 이유는 못 찾음.

**D5. 배경 작업은 막지 않고 알린다(Notice + 기록 패널).**
(a) 이슈 #204 저자 답 "A fix completed in the background should report, not block." commit `0490f71`(v1.22.2), v1.22.6에서 `trigger` 필드로 실제 연결. 대안: 모든 ingest 뒤 보고서 창(이전 방식). `FixReportModal`은 이때 쓰이지 않게 됐지만 파일은 남아 있다(`ui/modals/index.ts:14`, 생성처 0곳).

**D6. 여러 파일 ingest는 제자리 큐로.**
(a) 이슈 #130 "Moving the originals has two harmful side effects: 1. Broken provenance ... 2. Re-ingest on move-back." 대안: 스테이징 폴더로 옮겨 폴더 ingest(이전 우회책). v1.23.0에서 구현.

**D7. 파일 고르기 창은 디스크 상태를 보이고, 바뀐 노트는 잠그지 않지만 재수집 버튼도 두지 않는다.**
(a) 이슈 #598 "The picker is the one place where the user decides what to ingest, and it is the one place that does not consult the result of the last ingest." / "A re-ingest is additive rather than revising (#220 Tier 1/2)". `multi-file-row-state.ts:42-46` "A DRIFTED row is deliberately left live ... the decision stays with the user even though this PR offers no re-ingest button of its own."

**D8. 중복 내용 재수집은 단일 ingest에서만 묻고, 나머지는 조용히 건너뛴다.**
(a) `main.ts:134-135` "#164: when an interactive ingest hits a duplicate, ask the user whether to re-ingest. Folder/watcher ingests leave this unused and auto-skip." 이슈 #164는 빈 노트에서 환각 엔티티("Yinmin Zhong")가 생긴 사고에서 시작했다. 저자: "The pre-ingest requirements gate ... now validates every source file *before* any LLM call."

**D9. Schema 변경은 LLM이 전체 본문을 쓰고, 사람은 diff를 보고 적용, 자동 백업 3개.**
(a) commit `4692a4f`(위 §2.8 인용), 이슈 #97(요청자: "建议 -> 审核 -> 应用 -> 回退" 닫힌 고리 — 제안→검토→적용→되돌리기). Regenerate 버튼은 "to ship a minimal v1.22 release" 숨김. 대안: patch 적용, 수동 편집만.

**D10. Schema 파일에는 사용자 지식만, 런타임 값(태그 목록·폴더·언어)은 호출 때 주입.**
(a) AGENTS.md:416-429 "schema file MUST NOT bake runtime parameters. It MUST remain pure user domain knowledge." 이유: 두 곳에 같은 값이 있으면 어긋난다("reintroduces the dual-source problem"). 그래서 태그 목록은 설정 UI에, 페이지 규칙은 `config.md`에 있다.

**D11. 설정 패널은 둘로: LLM 샘플링(LLM Advanced)과 그 밖의 고급(하단 패널). 숨기면 값도 기본으로.**
(a) AGENTS.md:351-357 "LLM Advanced = LLM sampling + provider overrides ONLY. Everything else → bottom panel." `advanced-settings-section.ts` 머리 주석 "closing the showAdvancedSettings toggle resets every gated field to its default ... so a hidden setting never keeps a no-UI-affordance value." 예외: `minAliasLength`·`createWelcomeNote`·`maxConversationHistory`는 닫아도 유지된다(코드상 초기화 목록에 없음, `:54-70`). (b) [추정] `gateDissentStubs`·`extractionTopP`·`samplingSeed`처럼 UI 없는 설정은 이 원칙의 반대편 위험(보이지 않는 값)을 그대로 남긴다(사례 3개, §1.3).

**D12. 시작 점검은 항상 돈다. 사용자는 알림만 끈다.**
(a) commit `e0b8ca8` "Single owner = single source of truth; no more 'Notice showed but no file written' race condition". 이관은 예전 `startupCheck:false` 사용자를 'silent'로 옮겨 의도를 지킨다.

**D13. 작업별 모델은 모델 이름만 나눈다.**
(a) `types.ts:622-627` "per-provider split would 4× the credentials UI and break Test Connection's contract". UI 토글은 그리기만 바꾸고, 빈 값은 통합 모델로 떨어진다(`:648-656`).

**D14. UI 언어와 위키 언어를 나눈다. 프롬프트는 영어.**
(a) commit `23fd9ab`(v1.6.5) "Wiki content language is now independent of UI language" / "All LLM-facing prompts converted to English". README.md:85 "your wiki can be in Chinese while the interface is in English".

**D15. 자동 lint + autoSmartFix는 승인 없이 전부 고친다.**
(a) `en.ts:440` "When lint runs, automatically apply all fixes (Smart Fix All) without showing the report modal." 기본값 false(`types.ts:1569`). 사용자 요청 출처는 #204의 한 사용자가 daily lint + Auto Smart Fix를 켜고 쓴 사례.

**D16. 주기 lint는 소스가 안 바뀌면 건너뛴다.**
(a) `en.ts:434` "Run LLM lint on schedule, only when source files have changed since last check". hourly를 뺀 이유는 commit `0490f71`이 적지 않는다. 모르는 것.

**D17. PDF 변환 결과는 기본적으로 vault 밖 캐시에만.**
(a) `types.ts:464-469` "Default false (cache-only architecture; the cache in `.obsidian/` is the only artifact)". PDF-OCR-GUIDE.md:168 "your vault is not modified by default". MinerU는 외부 업로드라서 문서가 이를 경고한다: "treat an upload there as leaving your control"(PDF-OCR-GUIDE.md:22). 자체 호스팅 MinerU 주소는 아직 설정할 수 없다(`:86`, 이슈 #404).

**D18. Dead code는 한 릴리스 안에 연결하거나 지운다.**
(a) AGENTS.md:347-349 "Do not ship dead code across two releases." 그런데 HEAD에 규칙 위반으로 보이는 것이 셋 있다: `FixReportModal`(생성처 0), `enableSchema`(읽는 곳 0), schema 창의 Regenerate 주석 코드. [추정] 이 규칙은 export된 심볼만 검사해서 이것들을 못 잡는다(사례: 규칙 문구가 "exported symbols with zero production importers"로 한정, `FixReportModal`은 `index.ts`가 re-export하므로 importer가 있는 것처럼 보임).

**D19. CI·봇.**
(a) `.github/workflows/pr-ci.yml`: lockfile 동기화, `pnpm audit --audit-level high`, lint·typecheck·build·test·css-lint. "CI does NOT enable auto-merge. Explicit "merge it" ... from the maintainer is still required". `main` push에도 도는 이유: "#681 and #684 broke it: each was green against the `main` it branched from, the break existed only in the pair". `dependabot-lockfile.yml`은 Dependabot이 pnpm lockfile만 고쳐서 npm lockfile을 다시 만든다. 봇은 Dependabot뿐이고 이슈 분류 봇은 없다. 위키 기능과는 관계가 적다.

## 7. 앞선 schema-glossary 보고서와 어긋나는 점

| 앞선 보고서의 주장 | 이번에 본 것 | 근거 |
|---|---|---|
| #D "병합은 사용자가 Lint 창에서 고른다." | 고르는 단위는 쌍이 아니라 분류 전체다. "중복 병합(N)" 버튼 하나가 찾은 쌍 전부를 병합한다. 쌍별 선택 UI는 없다 | `LintReportModal-class.ts:123-141`, `controller.ts:387-399`, `:402-404` |
| #A "사용자는 설정에서 이 목록을 CSV로 바꿀 수 있다" | `tagVocabularyMode`를 `custom`으로 바꿔야 쓰인다. 입력은 chip UI이고 저장만 CSV다. `default` 모드에서는 입력값이 있어도 무시하고, 설정 설명이 "toggle to Custom to activate"라고 알린다 | `core/tag-vocab.ts:4-20`, `wiki-config-section.ts:176-178` |
| #A "적용은 사람 몫 ... diff 창에서 Apply" | 맞다. 덧붙일 것: 진입점은 Lint 보고서 창의 버튼 하나이고 명령 팔레트에는 없다. 일부만 적용하는 길은 없다. 설정 탭의 "Regenerate Default Schema" 버튼은 확인·백업 없이 `config.md`를 덮어쓴다 | `controller.ts:261`, `schema-manager.ts:412-440`, `wiki-config-section.ts:246-259` |
| #A·#E "쓰기 직전에 목록 밖 태그를 지운다" | 레포 안에서 문구가 어긋난다. 설정 화면은 아직 "Schema hint only — the LLM may still emit out-of-vocabulary types. Run Lint to find and fix those pages."라고 쓴다. 이 문구는 commit `83dec0e`(2026-07-29, #368)에서 들어왔고, 쓰기 검사를 한 목록으로 묶은 commit `170205b`(2026-09-20, #673)보다 오래됐다. 쓰기 함수는 `domainVocabulary`를 받은 경로에서만 지우고, 안 받은 경로에서는 남기고 로그만 찍는다(`frontmatter.ts:825-851`). 어느 경로가 받는지는 ingest 갈래가 확인할 일이다 | `en.ts:395`, `wiki-config-section.ts:180-187`, `core/frontmatter.ts:841` |
| #F "`skipMentionOnlyCandidates` ... 옵션, 기본 꺼짐" | 맞다. 덧붙일 것: 하단 Advanced 패널을 닫으면 false로 돌아간다. `gateDissentStubs`는 UI가 없어 data.json을 고쳐야만 켤 수 있다 | `advanced-settings-section.ts:68-69`, §1.3 |
| (암묵) 원칙 "LLM suggests, user decides" | ingest 경로에는 확인 지점이 없다. 저장소가 이를 미완 항목(Preview-Confirm gate)으로 인정한다 | 이슈 #330 §1, ROADMAP.md:375 |

레포 안 문서끼리 어긋나는 것도 적어 둔다. MODEL-GUIDE.md:11은 "The plugin feeds the LLM your full Wiki context per query"라고 쓰지만, Query는 PPR로 기본 10쪽·최대 20쪽만 고른다(`constants.ts:800`, `:809`). 이슈 #367 저자 답글은 "`concurrency = 1` (the v1.25.9 default)"라고 쓰지만, 기본값은 commit `3f8e63e`(v1.8.1)부터 3이다("Default concurrency 1→3").

## 8. 코드로 본 결함과 의심 (실행 안 함)

**F1. 여러 파일 창의 취소 버튼이 돌고 있는 batch를 멈추지 않는다.** `IngestQueue.remove()`는 작업의 `abortController.abort()`를 부르고 행을 지운다(`ingest-queue.ts:192-201`). 그런데 그 신호를 읽는 곳이 src 전체에 없다(grep `job.abortController`·`abortController.signal`: `ingest-queue.ts:197`과 엔진 자신의 컨트롤러 `wiki-engine.ts:812`뿐). `runBatchIngest`는 큐에서 지워진 작업을 확인하지 않고 다음 파일을 ingest한다(`ingest-commands.ts:246-272`; `start()`는 없는 id에 대해 아무것도 안 하고 돌아간다, `ingest-queue.ts:156-163`). 그래서 "Cancel all"을 눌러도 파일은 계속 수집될 것이다. 확인하려면 파일 3개를 큐에 넣고 첫 파일 중 Cancel all을 눌러 log.md를 본다.

**F2. 감시를 끄거나 주기 lint를 바꿔도 Obsidian을 다시 열 때까지 이전 동작이 남는다.** `saveSettings()`는 `stop()` 후 다시 시작한다(`main.ts:349-356`). `stopWatching()`은 상태만 지우고 이벤트를 해제하지 않는다. 주석 원문 "registerEvent handles cleanup via plugin lifecycle; we just clear our own state"(`auto-maintain.ts:98-105`). `onFileChanged()`는 `watching`도 `autoWatchSources`도 보지 않는다(`:133-193`). `clearPeriodicLint()`는 플래그만 내리고 `clearInterval`을 부르지 않는다(`:298-302`; `lintIntervalId`는 대입만 되고 읽히지 않음, `:34`, `:281`). [추정] 결과: 감시를 끄더라도 `watchedFolders`가 남아 있고 `autoWatchMode: auto`면 계속 자동 ingest된다. 설정을 저장할 때마다 이벤트 핸들러와 interval이 하나씩 늘어난다(사례 2개: 위 코드, 이슈 #204 사용자 보고 "they show "off" in the GUI, but the actions continue as though the setting is "on"" — 저자는 iCloud 동기화 탓으로 봤다).

**F3. `periodicLint: monthly`는 30일 간격이 32비트 상한을 넘는다.** `30*24*60*60*1000 = 2,592,000,000ms`이고 상한은 2,147,483,647ms다(`auto-maintain.ts:275-279`). MDN은 "Delays of more than this value will cause an integer overflow"라고 쓰고, 넘친 값이 음수가 되면 바로 실행된다고 한다(https://developer.mozilla.org/en-US/docs/Web/API/Window/setTimeout#maximum_delay_value). 2,592,000,000은 32비트로 감으면 음수다. [추정] 그래서 monthly를 고르면 interval이 거의 쉬지 않고 돈다. 감시 폴더가 비어 있으면 `hasSourceFilesChanged()`가 늘 true라서(`:337`) lint가 연달아 시작될 수 있다(사례 1개: 이 계산. 이슈 검색 "monthly"는 결과 0건). 확인하려면 Electron 콘솔에서 `setInterval(f, 2592000000)`을 돌려 본다.

**F4. "Regenerate Default Schema"는 확인 없이, 백업 없이 사용자 schema를 덮어쓴다.** `wiki-config-section.ts:246-259` → `schema-manager.ts:432-436`(`vault.process(existing, () => content)`). LLM 제안 Apply는 백업 3개를 남기는 것과 대조된다(`apply-suggestion.ts:55-67`).

**F5. 여러 파일 창에서 바뀐 노트를 골라도 수집되지 않고, 그 작업은 큐에 pending으로 남는다.** 창은 바뀐 행을 열어 둔다(D7). 그런데 `runBatchIngest`의 `isAlreadyIngested`는 소유권만 보므로 바뀐 노트도 "이미 수집됨"으로 건너뛴다(`ingest-commands.ts:190-199`, `ingest-state.ts:42-48`). 건너뛴 파일의 job id는 `alignedJobIds`에서 빠지므로 `start`/`complete`가 불리지 않는다(`:192-198`, `:240-245`). [추정] 그래서 그 행은 pending으로 남는다(사례 1개: 위 코드 흐름). 바뀐 노트를 다시 넣는 길은 단일 ingest(해시가 다르니 통과)와 감시 auto 모드뿐이다.

**F6. Office 파일은 MinerU를 켜도 고르기 창에 안 나온다.** 엔진은 MinerU일 때 doc/docx/ppt/pptx/xls/xlsx·이미지를 받는다(`wiki-engine.ts:1003-1005`, `constants.ts:45-48`). 파일 고르기·폴더 ingest·여러 파일 창은 `COMPATIBLE_SOURCE_EXTENSIONS`(md, markdown, txt, text, pdf)만 보인다(`suggest-modals.ts:12-13`, `ingest-commands.ts:136`, `MultiFileSuggestModal-class.ts:130-133`). 남는 길은 "지금 연 파일 ingest"인데, Obsidian은 Office 파일을 열지 못한다(PDF-OCR-GUIDE.md:60). 그리고 엔진의 요구 조건 gate도 `COMPATIBLE_SOURCE_EXTENSIONS`로 확장자를 거른다(`wiki-engine.ts:585-589`). 다만 변환 분기가 gate보다 먼저 도는지는 ingest 갈래가 확인할 일이다. [추정] UI에서 Office 파일을 넣을 길이 없다(사례: 세 진입점의 필터). README의 비교표는 "Markdown + PDF + images + Office (DOCX/PPTX/XLSX)"를 내세운다(README.md:64).

**F7. notify 알림 문구가 감시 폴더와 관계없이 "sources/"라고 쓴다.** `en.ts:459` "file(s) changed in sources/". 작은 문구 문제다.

## 9. 엔터프라이즈 다중 작성자 보고서 용도에 비춰

### 쓸 만한 장치

- **출처 소유권과 본문 해시로 "이미 넣음 / 바뀜"을 가르는 장치.** source 페이지에 `source_file:`과 `contentHash`를 남기고, 넣기 전에 대조한다(`ingest-state.ts`). 여러 사람이 같은 보고서를 고쳐 다시 올리는 환경에서 "바뀐 문서만 다시 넣기"의 기반이 된다. 다만 출처가 둘 이상인 페이지에서는 판정을 포기한다(`ingest-state.ts:57-64`).
- **제자리 큐(#130).** 문서를 옮기지 않아 원문 링크가 깨지지 않는다. 보고서 저장소의 폴더 구조를 그대로 두고 수집하는 데 맞다.
- **schema 변경 = diff 미리보기 + 전체 적용 + 자동 백업 + 제안 시각 기록.** 팀 표준 용어 규칙(schema)을 바꿀 때 검토자가 diff를 보고 승인하는 흐름으로 옮길 수 있다. `applied_suggestion:`이 suggestions.md 항목과 정확한 문자열로 이어져 감사 추적이 된다(`schema-commands.ts:68-70` 주석).
- **schema 파일과 런타임 값의 분리(D10).** 용어집·태그 목록 같은 조직 공통 값을 설정 쪽 한 곳에서 관리하고, 문서 작성 규칙만 schema에 두는 구조다. 용어 불일치 문제에서 "목록은 한 곳"이라는 원칙이 그대로 쓸모 있다.
- **배경 작업은 알리고, 상세는 기록 패널(log.md)에서.** 감사 로그를 vault 안 Markdown 한 파일로 두는 방식이다. 사람이 읽을 수 있고 버전 관리된다.
- **작업별 모델 분리.** 대량 ingest는 싼 모델, lint 판정은 강한 모델로. #367·#368 사용자가 실제로 그렇게 썼다.
- **위키 언어 고정.** 한국어·영어가 섞인 보고서를 한 언어의 페이지로 모은다(`wikiLanguage`). 별칭이 교차 언어 표기를 받는다(앞선 보고서 #B).
- **요구 조건 gate(빈 문서·중복 내용 거절).** 형식 없는 문서가 섞여도 빈 문서에서 환각 페이지가 생기는 사고(#164)를 막는다.
- **reviewed: true 잠금.** 담당자가 검수한 페이지를 이후 ingest가 덮지 않게 하는 사람 쪽 장치다(구현은 병합 갈래).

### 걸리는 점

- **다중 사용자·권한 모델이 없다.** 한 vault, 한 사용자, 한 설정이다. README.md:93이 팀 협업을 범위 밖이라고 명시한다. 문서별·폴더별 접근 권한, 작성자 필드, 승인자 개념이 없다. 감사 로그(log.md)에도 "누가"가 없다(HistoryModal 필드에 작성자 없음, `history-modal/types.ts:61-80`). 다중 vault 분리(#142)는 "long-term" 연구 항목이다(ROADMAP.md:395).
- **동시 쓰기 보호가 없다.** 수동 ingest·감시 ingest·lint가 겹쳐 돌 수 있다(§2.11). 여러 기기가 iCloud·Obsidian Sync로 같은 vault를 쓰면 설정·페이지가 어긋난다는 사용자 보고가 있다(#204). 서버에서 여러 사람의 문서를 받는 구조에는 그대로 못 쓴다.
- **ingest 결정에 사람 확인 지점이 없다.** 무엇이 페이지가 되고 어느 기존 페이지와 같은지(용어 불일치의 핵심)를 LLM과 코드가 혼자 정한다(이슈 #330). 사용자 목표 "어느 정도 사람이 하더라도 성능을 보장"에 맞추려면 Preview-Confirm gate에 해당하는 것을 직접 설계해야 한다. 이 레포에는 설계 메모만 있다.
- **승인 단위가 굵다.** lint는 분류 전체, schema는 본문 전체다. 여러 담당자가 각자 쌍·항목을 승인하는 흐름이 없다.
- **규모 한계.** lint는 1.2-1.5k쪽 부근에서 막혔다는 보고(#367)와 2000쪽 OOM 언급(`constants.ts:575`)이 있다. CJK 제목은 중복 버킷에서 빠진다(`constants.ts:578-584`). 한국어 보고서가 수천 건이면 lint 중복 검출이 약해질 수 있다.
- **형식 없는 문서 중 Office 파일은 UI로 넣기 어렵다(F6).** 외부 업로드(MinerU)이기도 해서 사내 문서에는 쓰기 어렵다.
- **자동 모드의 끄기가 믿을 만하지 않다(F2·F3).** 사내 비용 통제를 이 코드에 기대면 안 된다.

## 10. 모르는 것

- 모르는 것: `periodicLint` hourly를 왜 뺐는지. commit `0490f71`과 #204·#219는 사실만 적는다. 이슈 #219 본문과 v1.22.2 릴리스 노트를 보면 알 수 있다.
- 모르는 것: `gateDissentStubs`·`extractionTopP`·`samplingSeed`에 UI를 두지 않은 이유. PR #607·#511의 토론을 보면 알 수 있다.
- 모르는 것: F1·F2·F3·F5가 실제로 그렇게 동작하는지. Obsidian에서 돌려 보거나 `src/__tests__/ui/`·`src/__tests__/schema/`에 같은 경우를 다루는 테스트가 있는지 보면 알 수 있다(이번에는 테스트 파일을 읽지 않았다).
- 모르는 것: notify 모드에 "지금 수집" 버튼을 두지 않은 이유. 관련 이슈를 검색하지 않았다.
- 모르는 것: 파일 단위 ingest를 병렬로 돌리지 않는 것이 의도인지(§5 [추정]). AGENTS.md·MEMORY.md에 언급이 없었다(`serial` grep 0건). 엔진 갈래가 공유 상태 목록을 보면 판단할 수 있다.
- 모르는 것: 쓰기 검사가 `domainVocabulary`를 받는 호출 경로가 어디인지(§7 넷째 줄). ingest 갈래 노트에서 `enforceFrontmatterConstraints` 호출처를 보면 알 수 있다.
- 모르는 것: 헤드리스 CLI(`karpathywiki-cli`)가 이 플러그인과 같은 설정·승인 흐름을 갖는지. 형제 저장소(green-dalii/obsidian-llm-wiki-cli, 마지막 push 2026-08-21)를 읽어야 안다. 서버형 엔터프라이즈 배치에는 이쪽이 더 가까울 수 있다.
- 모르는 것: 11개 UI 언어의 번역 품질. i18n-parity 테스트(`src/__tests__/root/i18n-parity.test.ts`)는 키 완전성만 본다고 barrel 주석이 적는다(`texts.ts` "The i18n-parity test enforces key completeness").

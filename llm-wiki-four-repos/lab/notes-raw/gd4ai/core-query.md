# GD4AI obsidian-llm-wiki — core-query 갈래 노트

- 레포: GD4AI/obsidian-llm-wiki, HEAD `f41a39d` (2026-10-09), Apache-2.0 (Copyright Greener-Dalii)
- 로컬: `lab/repos/GD4AI_obsidian-llm-wiki`. 아래 `path:line`은 모두 레포 루트 기준이다.
- 맡은 범위: query·chat 흐름(`src/wiki/query-engine/**`, `src/wiki/conversation-ingest.ts`), 검색 core(`src/core/ppr-cascade.ts`, `monte-carlo-ppr.ts`, `build-graph.ts`, `index-search.ts`, `section-extractor.ts`, `hub-*.ts`), lint·health(`src/wiki/lint/**`, `src/wiki/contradictions.ts`), LLM 공급자 추상화(`src/llm-sdk/**`, `src/llm-client-wrapper.ts`, `src/core/create-plugin-llm-client.ts`, `llm-dispatch.ts`, `model-resolver.ts`, `task-policy.ts`).
- 코드는 실행하지 않았다. 모든 판단은 파일을 읽은 것이다. 읽기 전용 git·gh 명령만 썼다.

## 읽은 정도

| 파일 | 정도 |
|---|---|
| `src/wiki/query-engine/QueryView-class.ts`, `pipeline/*.ts`, `SuggestSaveModal-class.ts`, `custom-instructions.ts`, `types.ts` | 끝까지 |
| `src/core/ppr-cascade.ts`, `monte-carlo-ppr.ts`, `build-graph.ts`, `index-search.ts`, `section-extractor.ts`, `hub-link-distinctiveness.ts`, `hub-detection.ts` | 끝까지 |
| `src/wiki/engine-internals/graph-cache.ts`, `index-generator.ts` | 끝까지 |
| `src/wiki/conversation-ingest.ts`, `src/wiki/prompts/{conversation,seed-selection,lint,fixes}.ts` | 끝까지 |
| `src/wiki/lint/controller.ts`, `phases/*.ts`, `scanners.ts`, `llm-phases/contradiction-phase.ts`, `merge-duplicates.ts`, `link-orphan.ts`, `src/core/orphan-matcher.ts`, `src/wiki/contradictions.ts` | 끝까지 |
| `src/wiki/lint/llm-phases/dedup-phase.ts`, `duplicate-detection.ts`, `fix-runners.ts`, `fix-dead-link.ts` | 핵심 경로만 읽고 나머지는 훑음 |
| `src/llm-client-wrapper.ts`, `src/llm-sdk/create-llm-client.ts`, `src/core/create-plugin-llm-client.ts`, `llm-dispatch.ts`, `model-resolver.ts` | 끝까지 |
| `src/llm-sdk/output-mode-prober.ts`, `output-args.ts`(머리 주석), `task-policy.ts`(머리 주석), `transient-retry.ts`, `truncation-retry.ts`, `json.ts`(머리 주석) | 훑음 |
| `src/llm-sdk/openai-compat-sdk-client.ts`(1694줄), `anthropic-sdk-client.ts`, `openai-sdk-client.ts`, `bedrock-sso/**`, `openai-codex/**`, `obsidian-fetch-bridge.ts` | 재시도 갈래 위치만 grep으로 훑음 |
| `src/core/slug.ts`, `related-shaping.ts` | 끝까지 (앞선 보고서 확인용) |
| `src/core/frontmatter.ts`, `paragraph-provenance.ts`, `provenance-marker.ts`, `incomplete-page-cleaner.ts`, `page-write-guard.ts`, `related-link-corrector.ts` | 머리 주석만 훑음 |

다른 갈래와의 경계다. ingest(추출·page-factory·candidate-gate·path-resolution), schema(`src/schema/**`, vocabulary), auto-maintain 감시자는 다른 갈래 몫이라 경계만 적는다. `src/schema/auto-maintain.ts`는 주기 lint를 거는 곳(`auto-maintain.ts:273-295`)까지만 봤다.

## 한눈에

- Query는 임베딩 없이 돈다. `wiki/index.md`를 파싱한 페이지 목록에 대한 제목·별칭 문자열 매칭, 필요하면 LLM이 만든 키워드로 같은 매칭을 한 번 더, 그 결과를 seed로 `[[wikilink]]` 그래프 위에서 Monte Carlo PPR을 돌려 상위 10쪽을 고른다.
- 답 되저장은 수동이다. 사용자가 Save를 누르면 대화 전체가 하나의 source로 ingest된다. LLM이 "저장할 가치"를 판정해 묻던 자동 제안은 2026-05-28에 꺼졌고 코드는 죽은 채 남아 있다.
- Lint는 결정적 스캐너 9종 + LLM 중복 검증 1종이다. 수리는 사람이 버튼을 눌러야 돈다(자동 lint에서 `autoSmartFix`를 켠 경우는 예외). 전체를 LLM에게 "건강 진단"시키던 단계는 거짓 분석과 토큰 폭주 때문에 지웠다(#473).
- LLM 공급자 추상화는 Vercel AI SDK 위의 얇은 어댑터 4종 + 설정 주입 wrapper 하나다. 구조화 출력은 `json_schema → json_schema_strict → json_object → text_prompt`로 400을 받을 때마다 한 단계씩 내려가며, 내려간 단계를 (baseURL, model)별로 기억한다.
- 저자들 스스로 잰 약점이 크다. 그래프 edge의 95%가 같은 note에서 태어난 페이지끼리이고, 실제 query 경로는 5문항 중 3문항에서 단순 임베딩에 졌다(#729, `MEMORY.md:673-674`). 이 문제를 고치는 작업이 미병합 브랜치에서 진행 중이다.

## 모듈 지도

### Query 경로

```
main-commands/query-lint-commands.ts  queryWiki() → activateQueryView()
  └ wiki/query-engine/QueryView-class.ts  (Obsidian ItemView, 오른쪽 패널)
      sendMessage()
        ├ buildWikiContext()                           QueryView-class.ts:1096-1210
        │   ├ pipeline/read-index.ts  readWikiIndex()  → core/index-search.ts parseIndexForPages()
        │   ├ wikiEngine.getOrBuildGraph()             → engine-internals/graph-cache.ts → core/build-graph.ts
        │   ├ pipeline/select-seeds.ts selectPprSeeds()
        │   │    ├ core/ppr-cascade.ts lexMatchByTitleAndAliases / tokenizeQuery / lexIsReliable
        │   │    ├ pipeline/query-keywords.ts generateQueryKeywords()   [LLM]
        │   │    ├ pipeline/seed-selector.ts selectSeedsWithLLM()       [LLM, 키워드 실패 시만]
        │   │    └ core/ppr-cascade.ts pprCascade() → core/monte-carlo-ppr.ts personalizedPageRank()
        │   ├ pipeline/load-pages.ts loadRelevantPagesForQuery() → core/section-extractor.ts
        │   └ pipeline/assemble-context.ts assembleWikiContext()
        ├ custom-instructions.ts appendCustomQueryInstructions()
        └ llmClient.createMessageStream() [LLM]  (실패 시 createMessage로 1회 대체)
      saveToWiki() → wikiEngine.ingestConversation() → wiki/conversation-ingest.ts
```

### Lint 경로

```
query-lint-commands.ts lintWiki() → wiki/lint/controller.ts runLintWiki()
  ├ phases/preparation.ts      페이지 읽기 + 이중 링크·sources 정규화(디스크에 씀) + welcome 제외
  ├ core/build-graph.ts        (hub 스캐너용 그래프)
  ├ phases/programmatic.ts     scanners.ts 9종 (LLM 없음)
  ├ llm-phases/dedup-phase.ts  duplicate-detection.ts 후보 → LLM 검증 [LLM]
  ├ llm-phases/contradiction-phase.ts  wiki/contradictions 폴더 기록을 보고만
  ├ report-builder.ts          → log.md에 기록, LintReportModal
  └ fix-runners.ts / merge-duplicates.ts / fix-dead-link.ts / link-orphan.ts / fill-empty-page.ts  (버튼별 수리) [LLM]
```

### LLM 계층

```
core/create-plugin-llm-client.ts createLLMClient()
  ├ llm-sdk/create-llm-client.ts createLLMClientFromSettingsSync()  provider id → 어댑터 선택
  │    ├ AnthropicSdkClient   (anthropic, anthropic-compatible, bedrock-anthropic)
  │    ├ OpenAISdkClient      (openai, custom-responses)
  │    ├ OpenAICompatSdkClient (그 밖 전부 + bedrock-openai)
  │    └ OpenAICodexSdkClient  (openai-codex)
  └ llm-client-wrapper.ts wrapWithAdvancedSettings()  설정 주입·task 정책·계측
호출 지점: core/llm-dispatch.ts callLlm()  (typed 메서드가 있으면 그쪽, 없으면 createMessage)
모델 선택: core/model-resolver.ts resolveModelForTask(settings, 'ingest'|'lint'|'query')
```

## 핵심 자료 구조

| 이름 | 필드 | 출처 |
|---|---|---|
| `PageRef` | `path`(예 `entities/Foo`, wiki 폴더·`.md` 없음), `title`(path 끝 조각), `aliases[]`, `summary?`(본문 첫 줄 100자) | `src/core/ppr-cascade.ts:25-37`, `index-search.ts:11-27` |
| `Graph` | `nodes: string[]`, `edges: Map<string, string[]>`(나가는 방향만) | `src/core/monte-carlo-ppr.ts:24-27` |
| `PPROptions` | `numWalks`(3000), `maxSteps`(50), `damping`(0.05, 실제 뜻은 seed로 돌아갈 확률), `rng?` | `monte-carlo-ppr.ts:29-38` |
| `PageMatch` | `page`, `score`, `arm: 'lex' \| 'lex-seeded-ppr' \| 'graph-first-ppr'` | `ppr-cascade.ts:188-192` |
| `SeedSelectionResult` | `matches`, `armLabel`("Lex+PPR" / "LLM+PPR" / "LLM+KB" / "Lex++PPR"), `llmAugmented`, `pureLLM` | `pipeline/select-seeds.ts:60-78` |
| `RetrievalLabelData` | `arm`, `count`, `topPaths[]` — 답마다 저장해 다시 열어도 칩이 보인다 | `query-engine/types.ts:48-55` |
| `HistoryMessage` | `role`, `content`, `timestamp`, `retrieval?` — `settings.queryHistory`(data.json)에 저장 | `query-engine/types.ts:29-41`, `QueryView-class.ts:656-670` |
| `ProgrammaticFindings` | aliasDeficientPages, emptyPages, orphans, tagViolations, pollutedPages, deadLinks, ungroundedQuotes, hubLinkDensityIssues, sourceDriftIssues, contradictionMarkerIssues, sources 정규화 수, 이중 링크 수정 수 | `src/wiki/lint/types.ts:445-462` |
| `DuplicateCandidate` → `DuplicateResult` | 후보: 두 path, `signal`(crossLang·caseVariant·bigram·sharedLinks·sharedIncoming·sourceFingerprint), `score`, `reason` / 결과: `target`(남김), `source`(합쳐 지움), `reason` | `duplicate-detection.ts:19`, `lint/types.ts:464-468` |
| `HubLinkDensityIssue` | `pagePath`, `inDegree`, `totalRelatedLinks`, `distinctivenessScore`, `recommendation: strip\|review\|keep`, `lowDistinctivenessTargets` | `src/core/hub-link-distinctiveness.ts:37-46` |
| `LLMClient` | `createMessage(params): string`, `createMessageWithOutput?<T>(params): {text, output?, outputMode, finishReason, usage?}`, `createMessageStream?(params+onChunk)`, `listModels?()`. params에 `task`, `response_format{schema?}`, `outputModeOverride`, `enableThinking`, `reasoningEffort`, `temperature`, `top_p`, `seed`, `abortSignal`, `onFinish`, `cacheBreakpoint` | `src/types.ts:860-1019` |
| `OutputMode` | `json_schema` → `json_schema_strict` → `json_object` → `text_prompt` | `src/llm-sdk/output-mode-prober.ts:68` |

`wiki/index.md` 한 줄의 모양이 검색 전체의 입력 형식이다. `- [[entities/Foo|Foo]] \`aliases: a, b\` - 본문 첫 줄` 꼴이다(`engine-internals/index-generator.ts:120-131`). 파서는 이 정규식 하나다(`src/core/index-search.ts:15`). 그래서 별칭에 쉼표가 들어 있으면 둘로 갈린다(`index-search.ts:23`).

## Query 흐름

### 단계표

| # | 입력 | 처리 | 출력 | LLM | 근거 |
|---|---|---|---|---|---|
| 0 | 사용자 질문 | history에 push, `maxConversationHistory`×2 넘으면 앞을 자름 | — | — | `QueryView-class.ts:442-452`, `:961-982` |
| 1 | `wiki/index.md` | 줄 정규식으로 `PageRef[]` 생성. 파일이 없으면 "Wiki is empty" 안내 prompt로 끝 | `pageRefs`, `allPaths` | — | `pipeline/read-index.ts:30-48`, `assemble-context.ts:emptyWikiHint` |
| 2 | `allPaths` | 엔진 캐시에서 그래프를 꺼내거나, 모든 페이지 본문(frontmatter 포함)을 읽어 `[[...]]`를 edge로 만든다 | `Graph` | — | `QueryView-class.ts:1117`, `graph-cache.ts:73-87`, `build-graph.ts:48-103` |
| 3a | 질문 | `tokenizeQuery`로 2글자 이상 토큰. 제목 일치 3점·별칭 일치 2점, 모든 토큰이 맞으면 +2. 라틴 문자는 단어 시작에서만, CJK·한글·태국어는 부분 문자열로 맞춘다 | `lexHits` | — | `ppr-cascade.ts:109-186`, `:235-269` |
| 3b | `lexHits` | 1위 점수 ≥5 이고 hit ≥3 개이고 토큰 ≥2 개면 "strong" — LLM을 부르지 않는다 | `lexStrong` | — | `select-seeds.ts:106-114`, `constants.ts:829`, `:846` |
| 4 | 질문 | strong이 아니면 LLM에게 5-10개 키워드(질문 언어 + 영어)를 JSON으로 받는다 | `keywords[]` | 1회 | `pipeline/query-keywords.ts:72-97`, `:198-212` |
| 5 | `keywords` | 모든 `pageRefs`의 제목·별칭에 3a와 같은 점수식으로 다시 매칭(LLM 없음) | `keywordMatches` | — | `select-seeds.ts:229-232` |
| 6 | lex top 50 또는 pageRefs 앞 50 | 키워드가 0개일 때만, LLM에게 path·제목·별칭 목록을 주고 seed ≤3 개를 고르게 한다. 응답 path는 목록에 있는 것만 남긴다 | `llmSeeds` | 1회(+재시도) | `select-seeds.ts:149-161`, `seed-selector.ts:361-429`, `prompts/seed-selection.ts:23-39` |
| 7 | 위 결과 | seed 결정: strong lex 상위 5 → 키워드 매칭 상위 5 → LLM seed → 약한 lex 상위 5 → 없으면 `pureLLM` | `seeds`, 칩 라벨 | — | `select-seeds.ts:163-194`, `constants.ts:858` |
| 8 | seeds, graph | `pprCascade`: 그래프 성숙도(쪽 ≥30, edge ≥30, edge/쪽 ≥1, 첫 노드에서 BFS가 50% 넘게 닿음)에 따라 lex만 / lex-seeded / graph-first. seed마다 PPR을 돌려 노드별 최댓값으로 합친다. PPR 질량이 순위를 정하고 lex 순위는 동점 깨기용(최대 질량의 10%까지) | 상위 `min(10, 전체쪽수)` | — | `select-seeds.ts:200-206`, `ppr-cascade.ts:355-391`, `:397-413`, `:424-521`, `:530-584` |
| 9 | 상위 path | entity·concept 쪽은 `## Description`(없으면 `## Definition`) 절만 잘라 최대 4266자, 그 밖은 본문 12800자까지 | `## path\n\n본문` 덩어리들 | — | `pipeline/load-pages.ts:193-264`, `section-extractor.ts:145-181`, `constants.ts:489` |
| 10 | 덩어리 + pageRefs 앞 50 줄 | system prompt 조립: 언어 지시, (pureLLM이면 "일반 지식 답" 경고 배너), 쪽 목록 힌트, 본문, 인용 규칙(`[[__WIKI_FOLDER__/...]]`, `## References`) | system 문자열 | — | `pipeline/assemble-context.ts:55-127`, `QueryView-class.ts:1189-1201` |
| 11 | system + 대화 전체 | 사용자 지정 지시(≤5000자)를 system 끝에 붙여 streaming 호출. 실패하면 비-streaming 1회 | 답 텍스트 | 1회 | `QueryView-class.ts:531-743`, `custom-instructions.ts:133-146` |
| 12 | 답 | thinking 블록을 접이식 패널로 떼고, `__WIKI_FOLDER__`를 현재 폴더로 바꿔 렌더. history와 retrieval 라벨을 data.json에 저장 | 화면 | — | `QueryView-class.ts:790-842`, `:656-675` |

결정적(코드) 검사 지점은 다음과 같다.

- LLM이 낸 seed path는 입력 목록에 있는 것만 남긴다(`seed-selector.ts:426-428`). 그래프에 없는 seed는 버린다(`ppr-cascade.ts:419-422`).
- 키워드는 대소문자 무시 중복 제거, 6단어 이상은 문장으로 보고 버림, 최대 10개(`query-keywords.ts:114-132`).
- 답의 인용 링크를 실제 페이지와 대조하는 검사는 없다. 프롬프트가 `## References`를 요구할 뿐이다(`assemble-context.ts:109-116`).

실패·재시도 처리는 다음과 같다.

| 지점 | 처리 | 근거 |
|---|---|---|
| 키워드 생성 | 어떤 예외든 `[]` 반환 → 6단계(LLM seed 선택)로 넘어감 | `query-keywords.ts:206-211` |
| LLM seed 선택 | `withTransientRetry`로 빈 응답·JSON 실패 재시도, 401/403/429는 재시도 안 함. 끝내 실패하면 `[]` | `seed-selector.ts:395-422` |
| 컨텍스트 조립 전체 | 예외면 "Wiki context 실패, 일반 지식으로 답하라" prompt로 계속 | `QueryView-class.ts:1206-1209`, `assemble-context.ts:wikiContextErrorHint` |
| 답 streaming | 실패하면 같은 prompt로 비-streaming 1회, 그것도 실패하면 오류 문구 | `QueryView-class.ts:573-635` |
| 답 길이 잘림 | `finishReason === 'length'`면 콘솔 경고만 | `QueryView-class.ts:552-556` |
| 중지 버튼 | `aborted` 플래그만 세운다. `abortSignal`을 넘기지 않아 HTTP 요청은 끝까지 간다 | `QueryView-class.ts:745-754`, `:539-571` |

### 그래프와 캐시

그래프 노드는 index.md에 있는 모든 path(sources 포함)다. edge는 각 페이지 본문 전체(frontmatter 포함)에서 뽑은 `[[...]]` 중 노드로 풀리는 것이다(`build-graph.ts:48-103`). wiki 폴더 접두어를 떼고, 그래도 안 맞으면 마지막 path 조각으로 맞춘다(`build-graph.ts:64-93`). 자기 자신 링크는 버리고 같은 쪽 안 중복은 한 번만 센다.

frontmatter `sources: ["[[sources/x]]"]`도 edge가 된다. #480은 이것이 저자 vault에서 edge 질량의 약 30%라고 쟀다: "Roughly 30% of the edge mass means 'was extracted from here', not 'is related to'" — 즉 "여기서 추출됨"을 "관련됨"과 같은 edge로 걷는다(gh issue #480).

캐시는 엔진 단위 하나다. 키는 path 집합이고, 엔진을 거친 쓰기·삭제가 있을 때마다 통째로 버린다(`graph-cache.ts:73-97`, `wiki-engine.ts:525-530`, `:2055-2058`, `:2161-2166`). 사용자가 Obsidian에서 직접 링크를 고친 경우는 엔진을 거치지 않는다. 그러면 path 집합이 그대로인 한 다음 ingest 전까지 옛 그래프를 쓴다. [추정] 직접 만든 쪽은 index.md를 재생성하기 전까지 검색 후보에도 들지 않는다(사례: 후보 목록의 유일한 출처가 index.md다 — `read-index.ts:39-48`, index는 엔진의 `generateIndexFromEngine`만 쓴다 — `index-generator.ts:67-104`; 2개).

### Monte Carlo PPR 자체

walk 3000번, walk마다 50걸음이다. 걸음마다 0.05 확률로 seed로 돌아가고, 아니면 나가는 edge 하나를 고르게 고른다. 막다른 노드면 seed로 돌아간다. 방문 횟수를 전체 방문 수로 나눠 확률로 만든다(`monte-carlo-ppr.ts:40-99`). 비용은 쪽수와 무관한 K×L이다. 이것이 power iteration 대신 이 방식을 고른 이유로 적혀 있다: "Monte Carlo's K×L cost is independent of |V|: a 2000-page vault costs the same per query as a 200-page vault" — 2000쪽이나 200쪽이나 query당 비용이 같다(`monte-carlo-ppr.ts:4-6`).

RNG는 `Math.random`이라 같은 질문도 결과가 조금씩 달라질 수 있다. 저자는 이를 받아들였다: "acceptable for non-deterministic ranking — top-k is robust to sampling noise per #198 consensus" — top-k는 표본 잡음에 강하다고 봤다(`monte-carlo-ppr.ts:19-22`).

### 답 되저장

| 길 | 상태 | 근거 |
|---|---|---|
| Save 버튼 → `saveToWiki()` → `ingestConversation()` | 동작 | `QueryView-class.ts:293-300`, `:984-1023` |
| 답마다 LLM이 "저장할 가치"를 판정해 모달로 제안 (`evaluateAndSuggestSave`) | 호출처 없음. 죽은 코드 | `QueryView-class.ts:370-435`, commit `d72dffa` |

`ingestConversation`은 다음 순서다(`src/wiki/conversation-ingest.ts:55-323`).

1. index.md를 읽는다. 비어 있지 않으면 index 앞 3000자와 대화 앞 1500자로 LLM에게 `fully_redundant | partially_new | entirely_new`를 묻는다(`:80-107`, `:325-353`, `prompts/conversation.ts:20-35`). `fully_redundant`면 아무것도 안 쓰고 "Knowledge already exists in Wiki"를 돌려준다. 판정 호출이 실패하면 그냥 저장으로 넘어간다(`:104-106`).
2. **index.md 전체**와 대화 전체를 한 프롬프트에 넣어 source_title·entities·concepts를 JSON으로 뽑는다. "Entity/concept names should match existing Wiki pages if possible"이 지시다(`:109-160`). JSON이 깨지면 LLM에게 문법만 고치게 1회 더 묻는다(`:178-190`).
3. `wiki/sources/<slug(source_title)>.md`에 요약 페이지를 LLM으로 쓴다(`:209-257`).
4. 엔티티·개념마다 ingest와 같은 `pageFactory.createOrUpdate*Page`를 부른다(`:261-295`). 그래서 이후의 별칭 대조·병합 규칙은 ingest 갈래와 같다.
5. index를 다시 만들고 log에 남긴다. 이 경로의 모순(contradiction)은 "nothing collects it for a conversation run yet" — 아직 아무도 모으지 않는다(`:297-301`).

## Lint 흐름

### 단계표

| 단계 | 하는 일 | 디스크 쓰기 | LLM | 근거 |
|---|---|---|---|---|
| 0 | LLM 클라이언트가 없으면 lint 전체를 거부 | — | — | `lint/controller.ts:52-55` |
| 1  준비 | wiki 폴더의 md를 50개씩 병렬로 읽음(index·log·schema·contradictions 제외) | — | — | `phases/preparation.ts:24-60` |
| 1 준비 | `[[a|[[b]]]]` 같은 이중 링크 수정, `sources:` 오염 정규화 | **함** (scan 중에 조용히) | — | `preparation.ts:62-115` |
| 1 준비 | `type: welcome` 쪽 제외 | — | — | `preparation.ts:139-156` |
| 2 그래프 | pageMap으로 그래프 생성 (hub 스캐너용) | — | — | `controller.ts:91-98` |
| 3 스캐너 9종 | 아래 표 | — | — | `phases/programmatic.ts:202-346` |
| 4 중복 | 후보 생성(결정적) → Tier 분류 → 배치로 LLM 검증 | — | 배치당 1회 | `llm-phases/dedup-phase.ts:124-` |
| 5 빈 쪽 | 중복 판정에 걸린 쪽을 빼고 `isPageEmpty` | — | — | `controller.ts:159-172` |
| 6 모순 | `wiki/contradictions/` 기록 중 resolved·suppressed 아닌 것을 나열 | — | — | `llm-phases/contradiction-phase.ts:78-92`, `src/wiki/contradictions.ts:16-57` |
| 7 보고 | 보고서를 `log.md`에 남기고 모달을 띄움. 자동 lint는 Notice만, `autoSmartFix`면 Fix All 실행 | log.md | — | `controller.ts:620-657` |

결정적 스캐너 9종이다.

| 스캐너 | 판정 | 근거 |
|---|---|---|
| alias 부족 | entity·concept 쪽 frontmatter에 비어 있지 않은 `aliases:`가 없음 | `scanners.ts:42-119` |
| 고아 | 어떤 wiki 쪽에서도 제목·path·별칭으로 들어오는 링크가 없음 | `scanners.ts:165-198` |
| 태그 위반 | `tags:`가 활성 어휘 밖이거나 비어 있음 | `scanners.ts:416-479` |
| 오염 쪽 | 제목에 폴더 접두어가 박힌 쪽 | `programmatic.ts:216-226` |
| 죽은 링크 | vault 전체 파일명·상대경로·하위경로 집합에 없고, 공백→`-` 바꿔도 없음 | `scanners.ts:20-39`, `:123-162` |
| 인용 근거 | `## Mentions in Source`의 `"인용" — [[출처]]`가 출처 본문에 그대로(또는 대소문자·구두점·공백 정규화 후) 있는지. 원본 note까지 읽는다 | `scanners.ts:287-388`, `programmatic.ts:241-277` |
| hub 링크 밀도 | in-degree 상위 hub의 `## Related`/`See also`/`Related pages` 절 링크끼리 PPR로 서로 잘 닿으면 strip/review 권고 | `core/hub-link-distinctiveness.ts:130-229` |
| source drift | source 쪽 `contentHash`와 원본 note 본문 해시가 다름 (보고만) | `scanners.ts:514-564`, `programmatic.ts:287-321` |
| 모순 표식 | frontmatter `contradictions:` 목록이 있는 쪽 | `scanners.ts:589-603` |

### 중복 검출

후보 생성은 결정적이다. 쪽을 제목 앞 2글자(`tp:`), 나가는 링크 대상(`lh:`), 들어오는 링크 출처(`ic:`) 버킷에 넣고 버킷 안에서만 쌍을 비교한다(`duplicate-detection.ts:207-253`, `constants.ts:586`, `:597`). 신호는 6종이다(`duplicate-detection.ts:583-635`).

| 신호 | Tier | 근거 |
|---|---|---|
| crossLang(별칭 교차 일치), caseVariant, sourceFingerprint(본문 해시 같음) | 1 — 예산과 무관하게 전부 검증 | `dedup-phase.ts:68-84`, `:97-113` |
| bigram 제목 유사도 ≥0.6 | 1 | 같은 곳, `constants.ts:659` |
| bigram 0.4–0.6, sharedLinks(링크 Jaccard ≥0.4 + 본문 Jaccard ≥0.2), sharedIncoming | 2 — 남은 토큰 예산만큼 | 같은 곳, `constants.ts:614`, `:629`, `:642`, `:676` |

entity↔source, concept↔source 쌍은 버린다. entity↔concept 쌍은 허용한다(`duplicate-detection.ts:47-82`).

LLM 검증 프롬프트에 들어가는 것은 쌍마다 두 path와 신호 설명 한 줄뿐이다. 페이지 본문은 넣지 않는다: `` `- Candidate A: ${c.target}\n  Candidate B: ${c.source}\n  Signal: ${c.reason}` ``(`dedup-phase.ts:562-564`). 프롬프트 주석은 "Verify duplicate candidates with content analysis"라고 적지만(`prompts/lint.ts:27`), 실제 판정은 이름과 신호만 보고 한다. thinking은 강제로 끈다(`dedup-phase.ts:402`). 프롬프트에는 "Do not reason step by step"까지 넣었다(`prompts/lint.ts:55`).

### 수리(fix) 단계

| 버튼 | 하는 일 | LLM | 근거 |
|---|---|---|---|
| 오염 쪽 수정 | 제목에서 폴더 접두어 제거 | — | `controller.ts:264-296` |
| 별칭 채우기 | 제목 + 본문 2000자로 별칭 3-8개 생성, frontmatter에 병합 | 쪽당 1회 | `fix-runners.ts:48-225`, `prompts/lint.ts:98-125` |
| 중복 병합 | 두 본문을 LLM이 융합(JSON `{body, aliases}`), 실패하면 `## From <source>`로 덧붙임. source 제목·H1·별칭을 target 별칭에 넣음. vault 전체에서 source를 가리키는 링크를 target으로 바꾼 뒤 source를 휴지통으로 | 쌍당 1회 | `merge-duplicates.ts:15-206`, `core/link-retarget.ts:1-38` |
| 죽은 링크 | 후보 창(제목·별칭·문맥으로 고른 30쪽)을 주고 `correct` 또는 `create_stub` 판정. stub은 LLM이 채우지 않는 정직한 placeholder | 링크당 1회 | `fix-dead-link.ts:1-120`, `prompts/fixes.ts:4-22` |
| 고아 연결 | 고아 본문 2000자 + **index.md 앞 3000자**를 주고 1-3쪽 고르게 함. 고른 쪽 끝 `## Related Pages`에 한 줄 추가 | 고아당 1회 | `link-orphan.ts:17-108`, `core/orphan-matcher.ts:24-36` |
| 빈 쪽 채우기 | 기존 내용 + **index.md 앞 2000자**로 150-300단어 생성. 인용이 없으면 Mentions 절을 만들지 말라고 지시 | 쪽당 1회 | `fix-runners.ts:290-339`, `core/prompt-builders.ts:28-42`, `prompts/fixes.ts:24-49` |
| 태그 재지정 | 제목 + 첫 문단 + 활성 어휘로 `tags`만 다시 씀. 응답도 어휘로 재검증 | 쪽당 1회 | `fix-runners.ts:448-` |
| 빈 stub 삭제 | 항상 보이는 독립 버튼 | — | `controller.ts:344-370` |

Smart Fix All 순서는 오염 쪽 → 별칭 → 중복 병합 → 죽은 링크 → 고아 → 빈 쪽 → 태그다(`controller.ts:448-542`). 이유는 주석에 있다: "Aliases are required for Tier 1 duplicate signals (crossLang)" / "Eliminates redundant pages, resolves many dead links and orphans automatically via link rewriting" — 별칭이 있어야 중복 신호가 살고, 병합이 링크를 고치며 죽은 링크·고아를 함께 없앤다(`controller.ts:466-490`).

[추정] Fix All은 lint를 다시 돌리지 않고 처음 스캔한 목록을 끝까지 쓴다(사례: `deadLinks`·`orphans`·`emptyPages`는 `controller.ts:118-126`에서 한 번 잡힌 배열이고 각 단계가 그 배열을 그대로 넘긴다 — `:484`, `:498`, `:511`, `:522`; 4곳). 그래서 병합으로 지워진 쪽에 대한 죽은 링크 수리가 그대로 시도된다. 실행해 확인하지는 않았다.

## LLM 공급자 추상화

### 공급자와 어댑터

provider id는 17개다: openai, openai-codex, anthropic, gemini, openrouter, deepseek, minimax, kimi, glm, opencode, bedrock-anthropic, bedrock-openai, ollama, lmstudio, custom, custom-responses, anthropic-compatible(`src/types.ts:1290-`). 어댑터는 4종이고 분기는 `create-llm-client.ts:325-401`이다. 대부분의 공급자는 `@ai-sdk/openai-compatible` 하나로 묶인다.

HTTP는 브라우저 `fetch` 대신 Obsidian `requestUrl`을 기본으로 쓰는 다리를 거친다. 이유는 "Custom protocol schemes / non-HTTP base URLs … can hit CORS preflight edge cases" 그리고 "`requestUrl` is the official, sandbox-aware HTTP client" — 로컬 서버 CORS 문제와 Obsidian 공식 클라이언트라서다(`src/core/obsidian-fetch-bridge.ts:1-22`). Bedrock SSO/IAM은 AWS SDK 없이 SigV4를 직접 구현했다(`create-llm-client.ts:113-161`, README.md:305).

API 키는 Obsidian SecretStorage에서 읽고, 없으면 옛 `settings.apiKey`로 내려간다(`create-llm-client.ts:338-350`).

### wrapper가 하는 일

`createLLMClient`는 늘 `wrapWithAdvancedSettings`로 감싼 클라이언트를 돌려준다(`core/create-plugin-llm-client.ts:61-69`). wrapper는 세 가지를 한다(`src/llm-client-wrapper.ts:83-213`).

1. 호출자가 비워 둔 `temperature`·`top_p`·`repetition_penalty`·`seed`를 설정값으로 채우고 `max_tokens`에 상한을 씌운다. 호출자가 넣은 값이 이긴다(`:140-154`).
2. `task` 라벨로 단계별 정책을 적용한다. 정책은 출력 모드와 thinking을 함께 고정한다(`:173-191`). 이유: "a `response_format` on the request sets `reasoning_tokens` to 0 regardless of `reasoning_effort`" — 구조화 출력을 걸면 추론이 0이 되므로 "생각하게 할지"는 출력 모드와 묶인 단계별 결정이다(`src/core/task-policy.ts:3-10`).
3. `task`별 소요 시간을 기록하고 디버그 로그에 단계 이름을 남긴다(`:193-213`).

`Object.create(client)`로 감싼 이유도 적혀 있다: "spread only captures own enumerable properties, which drops all prototype methods" — spread는 prototype 메서드를 잃는다(`llm-client-wrapper.ts:74-81`).

### 구조화 출력과 재시도 계층

| 계층 | 무엇을 막나 | 근거 |
|---|---|---|
| 출력 모드 강등 | 400 응답 본문이 `json_schema`/strict/`json_object`를 거부하면 한 단계 약한 모드로 즉시 재시도. 성공한 모드를 (baseURL, model) 키로 기억 | `output-mode-prober.ts:1-53`, `:129-191`, `openai-compat-sdk-client.ts:653-760`(훑음) |
| reasoning 필드 제거 | `reasoning_effort` 등을 거부하는 400이면 빼고 1회 재시도, 성공 후에만 캐시 | `openai-compat-sdk-client.ts:564-650`(훑음) |
| token 키 교체 | `max_tokens` ↔ `max_completion_tokens` 400이면 바꿔 재시도 | `src/llm-sdk/token-key-probe.ts`(훑음) |
| URL 대체 | 사용자 baseURL이 404면 후보 URL을 시험 | `openai-compat-sdk-client.ts:533-560`, `core/url-fallback.ts`(훑음) |
| 일시 오류 | 200인데 빈 본문, JSON 파싱 실패, 네트워크 흔들림 → 지수 백오프 재시도. 401/403/429는 안 함 | `core/transient-retry.ts:1-40` |
| 잘림 | finish가 length면 `max_tokens`를 두 배(상한 16000)로 1회 | `core/truncation-retry.ts:1-40` |
| JSON 파서 | 빈 응답을 별도 예외로, `{"": ""}` 같은 placeholder를 실패로 분류, LLM에게 JSON 문법만 고치게 하는 repair 콜백 | `core/json.ts:1-170`(머리 주석) |

호출 지점은 `callLlm`이 typed 메서드 유무로 갈라 준다(`core/llm-dispatch.ts:125-134`). Anthropic·OpenAI·Codex 어댑터는 typed 메서드를 구현하지 않아 늘 텍스트 + 호출자 파싱 경로다(`src/types.ts:953-957`).

모델은 `ingest`·`lint`·`query` 세 갈래로 따로 지정할 수 있고 비우면 기본 모델이다(`core/model-resolver.ts:164-204`).

## 설계 결정과 이유

### 검색

| 결정 | 이유 | 대안 | 이력 |
|---|---|---|---|
| 임베딩을 쓰지 않고 `[[wikilink]]` 그래프 PPR로 검색 | (a) "Only OpenAI natively supports `/v1/embeddings`", "a per-page embedding index for a 2000-page vault is roughly 12 MB of JSON that has to be versioned, migrated, invalidated", "PPR … gives you what an embedding would have given you, but the graph *is already the data*" — 공급자 대부분이 임베딩이 없고, 색인 유지가 짐이며, 그래프가 이미 같은 정보를 가진다고 봤다(gh issue #198). (a) 뒤에는 정체성 이유가 붙었다: "`Zero-embedding graph retrieval` is a load-bearing identity claim: README badge line, SEO intents" — 마케팅 주장이 이 결정을 떠받친다(`MEMORY.md:729-732`, gh issue #729 "Why not embeddings"). | #175의 임베딩 공통층(contentHash 키 캐시, cos 기반 prefilter) | #175 제안(2026-06-21) → #198로 대체, `560ade0`·`84425c7`(2026-06-27) |
| 그래프 신호가 임베딩만큼 좋다는 근거 | (a) 53쪽 합성 fixture에서 cascade R@5 27.1% vs bge-m3 kNN 24.1%. 같은 문서가 "a pure semantic retriever (knn) lands within 1-3pp of the cascade", "the structural component alone is only ~3pp" — 향상 대부분은 그래프가 아니라 의미 매칭 몫이라고 스스로 적었다(`src/__tests__/fixtures/wikis/sample-50page/REAL_VAULT_EVAL.md:77-94`). #480은 "A graph whose edges encode co-occurrence *is* a similarity measure, so 'PPR ≈ kNN' is the expected outcome" — edge가 동시 출현이라 같을 수밖에 없다고 정정했다. | — | #480 OPEN |
| Monte Carlo PPR (power iteration 아님) | (a) 쪽수와 무관한 K×L 비용(`monte-carlo-ppr.ts:4-6`) | power iteration, 쪽별 PageRank 캐시(#198 질문 5의 a/b/c) | `84425c7` |
| damping(되돌아갈 확률) 0.15 → 0.05, walk 1000 → 3000 | (a) 2142쪽 실제 vault leave-one-out에서 "damping reduction is the strongest lever (+2.3pp cumulative)", "numWalks 3000 is saturation point" — R@5 21.5% → 23.8% (commit `0a26951`) | 0.10, 5000 walk, 길이 40 | `0a26951` (2026-06-30). 미병합 브랜치는 다시 0.30 / 10걸음으로 바꿨다(아래 #진행 중인 방향) |
| 질의 의존 seed가 없으면 PPR을 안 돈다 | (a) "PPR from an ARBITRARY seed (e.g. `pages[0]`) is query-irrelevant noise … surfaced 'concepts/自我修正算法' for a 'DeepSeek DSA HCA' query" — 무관한 seed는 잡음만 낸다(`ppr-cascade.ts:486-500`) | 차수 순위 fallback (삭제됨, `ppr-cascade.ts:476-478`) | `98fea01` (#281) |
| 그래프 성숙도로 lex / lex-seeded / graph-first 3갈래 | (a) "picks the right retrieval strategy based on graph maturity", 문턱은 "@GioiaZheng's consensus thresholds"(`ppr-cascade.ts:3-15`, `:351-354`). 작은 vault는 PPR이 대부분 0이라는 #198 질문 3에 대한 답 | lex만, 강제 hub seed ingest | `560ade0` |
| 1단계 lex는 제목·별칭만 보고 summary는 안 봄 | (a) "user vault pages frequently lack summary frontmatter … Aliases carry the curated 'what is this page' signal"(`ppr-cascade.ts:155-160`) | summary 포함 | `98fea01` |
| LLM에게 페이지 목록 대신 키워드를 받아 로컬에서 전수 매칭 | (a) "LLM with 50 random pageRefs returns seeds=[]", 관련 쪽이 index 1410번째 줄이라 앞 50쪽에 없었다. "Root cause was the slice, not the LLM"(`select-seeds.ts:22-31`, PR #281 본문). 전체 목록은 "2137 pageRefs × 50 chars ≈ 30K tokens"(`query-keywords.ts:5-8`) | 전체 목록을 LLM에 보냄 | `98fea01` |
| 키워드 프롬프트에 언어 쌍을 하드코딩하지 않고 "질문 언어 + 영어" | (a) "Hardcoding 'Chinese ↔ English' breaks i18n users"(`query-keywords.ts:19-25`) | 중↔영 고정 | `98fea01` |
| 라틴 needle은 단어 시작에서만 맞춤, CJK는 부분 문자열 | (a) 3000쪽 독일어 vault에서 "'man' hit Kahneman and Karpman, 'bei' hit Salbei … 'creatin' hit Phosphocreatin"(`ppr-cascade.ts:100-108`, commit `30a15fd`) | 전부 부분 문자열(이전) | `30a15fd` (#625) |
| lex·PPR 합칠 때 PPR 질량이 주, lex는 동점 깨기 | (a) "`max(lex, ppr)` let any keyword hit outrank every PPR seed: with 76 lex hits the top ten were all lex"(`ppr-cascade.ts:541-552`) | max 합치기(이전) | `30a15fd` |
| 여러 seed의 PPR을 합이 아니라 노드별 최댓값으로 합침 | 모르는 것: 이유가 적혀 있지 않다(`ppr-cascade.ts:393-413`). #198 원문을 다시 보거나 저자에게 물어야 한다 | 합, 평균 | `560ade0` |
| 찾은 게 없으면 일반 지식으로 답하고 배너로 알림(`LLM+KB`) | (a) "we should NOT pretend to have wiki sources … the chat LLM answers from general knowledge with a UI banner"(`select-seeds.ts:33-38`) | "모름"으로 답 | `98fea01` |
| 질의 때 쪽 요약은 LLM이 아니라 `## Description` 절을 잘라 씀 | (a) "Every wiki page already has a `## Description` … We will extract it on demand … No new frontmatter field, no LLM call"(gh issue #198 "Tier B redesign"). Description을 Definition보다 먼저 보는 이유: 3025쪽 vault에서 "183 had a definition under 400 chars and a description at least three times as long"(`section-extractor.ts:153-160`) | 질의마다 LLM 요약(ROADMAP Tier B, 취소) | #198 |
| 답 prompt에 실제 wiki 폴더 대신 `__WIKI_FOLDER__` | (a) 답이 history로 다시 few-shot이 되므로 폴더를 바꿔도 "the LLM would follow that established folder"(`assemble-context.ts:37-49`) | 실제 폴더 | v1.24.0 |
| index 전문을 답 prompt에서 뺌 | (a) "2137 nodes → ~70K tokens of index text alone"(`assemble-context.ts:69-77`) | index 전문 포함(이전) | `98fea01` |
| 기본 상위 쪽수 5 → 10 | (a) "With only 5 pages the `5 pages · PPR` chip loses meaning on large vaults"(`constants.ts:786-799`) | 5 | `98fea01` |
| 사용자 지정 지시는 query에만 주입 | (a) "Ingest / lint / page generation / Save to Wiki / seed selection / duplicate merge are intentionally NOT affected"(`custom-instructions.ts:7-10`) | 전 단계 주입 | #251 |

### 답 되저장

| 결정 | 이유 | 대안 | 이력 |
|---|---|---|---|
| 자동 저장 제안을 끄고 수동 Save만 남김 | (a) "removes unwanted LLM evaluation and SuggestSaveModal prompt"(commit `d72dffa` 메시지) | 닫을 때마다 LLM 가치 판정 | `20c3df8`에서 도입, `d72dffa`(2026-05-28)에서 해제 |
| 대화를 하나의 source로 보고 ingest와 같은 page-factory로 흘림 | [추정] 별도 저장 형식을 만들지 않고 ingest의 별칭 대조·병합을 재사용하려는 것이다(사례: `conversation-ingest.ts:267`, `:285`가 ingest와 같은 `createOrUpdate*Page`를 부른다; 2곳) | 답을 별도 "synthesis" 페이지로 저장 | — |
| 저장 전에 LLM으로 중복 판정 | (a) dedup 결과를 숨기지 말라는 #398: "a silent-success outcome … does not lie to the user"(`QueryView-class.ts:1004-1012`) | 판정 없이 저장 | #398 |

### Lint

| 결정 | 이유 | 대안 | 이력 |
|---|---|---|---|
| wiki 전체를 LLM에게 진단시키던 단계를 삭제 | (a) "it only sees a 5-field stats block + 8 pages of content (~5K tokens of a 152K-token vault) — the analysis was dishonest and repeated programmatic findings or invented details", "Karpathy's lint design is conversational"(commit `0e7496a`). 촉발은 313,754토큰 요청으로 HTTP 400이 난 #473 | 요약·배치로 축소 | `0e7496a` (2026-08-18) |
| 스캐너는 순수 함수, LLM은 중복 검증과 수리에만 | (a) "These have no Obsidian API dependencies and can be unit tested directly"(`scanners.ts:1-2`) | — | v1.18.3 분리 |
| 중복 후보를 Tier로 나눠 Tier 1은 무조건 검증 | (a) "truncating would silently drop high-precision duplicates"(`dedup-phase.ts:90-96`) | 일괄 상한 | #382 |
| 중복 검증 때 thinking 강제 해제 | (a) "chain-of-thought reasoning adds latency, can exhaust the token budget before the JSON output fits … and does not improve recall or precision on this task class"(`prompts/lint.ts:29-38`) | 사용자 설정 따름 | #382 후속 |
| 죽은 링크 stub을 LLM으로 채우지 않음 | (a) "With no real source note to anchor the generation, the LLM fabricates alias claims, related-link targets, and a summary that looks authoritative but is unsourced … The lint path was a back door around the gate"(`fix-dead-link.ts:71-92`) | stub을 LLM으로 채움(이전) | v1.22.1 (#197) |
| 병합 전에 vault 전체 링크를 target으로 바꿈, 사용자 note도 포함 | (a) 2824쪽 vault에서 "1762 (across 340 notes) were written as a bare title `[[Foo]]`", "Resolve before replacing", "Write surgically. Foreign notes are the user's own files"(`core/link-retarget.ts:9-35`) | wiki 폴더 안만 | #386 |
| source drift는 보고만 | (a) "a re-ingest is additive, so acting on drift automatically would duplicate content rather than revise it"(`scanners.ts:507-509`) | 자동 재ingest | #220 Tier 0 |
| 모순은 기록 파일을 나열만, 자동 해결 삭제 | (a) "Nothing ever produced that status … so the branch filtered an always-empty set and was removed"(`contradiction-phase.ts:9-15`) | `review_ok` 자동 재작성 | #604, #666 |
| hub 링크 밀도를 PPR로 판정 | (a) "two targets with high mutual reachability are providing overlapping information"(`hub-link-distinctiveness.ts:23-28`). #157의 임베딩 cos 공식을 대체(gh issue #198 표 2번) | in-degree만, 임베딩 cos | P1-6 |

### LLM 계층

| 결정 | 이유 | 대안 | 이력 |
|---|---|---|---|
| 손수 짠 클라이언트 1625줄을 Vercel AI SDK 어댑터로 교체 | (a) "Eliminates the entire class of provider-version regressions (#137 / #141 / #143 / #147 / #207)"(ROADMAP 당시 문구, commit `0a26951` diff), "AI-SDK provider behaviors (auto-routing gpt-5.x to Responses API, reasoning effort, max_tokens ↔ max_completion_tokens) are now maintained upstream"(commit `6be9258`) | 손수 유지 | `6be9258` (2026-06-30), v7 승격 `f41a39d` |
| 출력 모드를 가장 강한 것에서 시작해 400마다 강등, 캐시는 (baseURL, model) | (a) 강등은 백엔드 성질이지만 placeholder 응답은 모델 성질: "on ONE LM Studio gateway, Qwen3.5 emits `{"": ""}` under grammar constraint while gemma-4-12b emits full JSON. A per-baseURL cache would demote gemma too"(`output-mode-prober.ts:42-52`) | baseURL 단위 캐시(이전), 공급자별 하드코딩 | #443, #658 |
| 강등 결정은 재시도가 성공한 뒤에만 기록 | (a) "A transient retry failure (5xx, network blip) must not permanently downgrade the baseURL"(`output-mode-prober.ts:18-25`) | 즉시 기록 | v1.26.3 |
| 단계별 task 정책(출력 모드 + thinking) | (a) 위 wrapper 절의 #481 인용. "Which of them benefits from reasoning is unmeasured. This module exists so that it can be measured"(`task-policy.ts:12-14`) | 전역 토글 하나 | #481, #524 |
| 모델을 ingest·lint·query 세 갈래로 | (a) 27곳 호출이 각자 `settings.model`을 읽던 것을 한곳으로: "Single point of truth"(`model-resolver.ts:1-12`) | 단계마다 모델 | #208 |
| Obsidian `requestUrl` 다리 | 위 공급자 절 인용 | 브라우저 fetch만 | `6be9258` |

## 진행 중인 방향 (미병합 브랜치)

HEAD에는 없고 원격 브랜치에만 있다. 보고서 작성자가 "현재 구현"과 섞지 않도록 따로 둔다.

| 브랜치·commit | 내용 | 저자가 밝힌 이유 |
|---|---|---|
| `origin/feat/729-phase1-co-citation` `7b01a61` | `src/core/co-citation.ts` 추가. 같은 대상을 함께 가리키는 쪽을 Related 후보로 써서 출처를 넘는 edge를 만든다 | #729: "in a star forest there is no path between two stars, so **no weight function can create reachability**" — 별 모양 그래프에선 PPR을 아무리 조정해도 다른 note로 못 건너간다 |
| `origin/feat/729-reader-recall-2026-10-07` `d3eb3c4` | lex·PPR 합치기를 RRF 합에서 채널별 정규화 max로 | "bridge recall up 53% on test10 and 11% on test8. Self MRR down 0.054 and 0.007" |
| 같은 브랜치 `d008289` | damping 0.30, maxSteps 10 | "bridge +8% and +11%", self MRR 하락은 "a reordering and not a retrieval failure" |
| 같은 브랜치 `8dc9c0c` | 검색 상수를 `constants.ts`로 모으고 예산 10 → 20 | "budget 20 → bridge recall 0.819", "2x the tokens for +42% recall" |

이 브랜치는 HEAD에 없는 `assembly.ts`, RRF 합치기를 전제로 한다. [추정] HEAD의 `mergeWithPPR`보다 더 나아간 다른 검색 경로가 브랜치에서 자라고 있다(사례: `d3eb3c4`가 "replace the RRF sum"이라 적는데 HEAD에는 RRF가 없다, `8dc9c0c`가 `assembleWithCoverage`를 언급한다; 2개).

## 저자들이 잰 약점

| 측정 | 값 | 출처 |
|---|---|---|
| 같은 note에서 태어난 쪽끼리의 edge 비율 | 95% (단순 동시 출현이 Related edge의 94.5%를 재현) | gh issue #729, `MEMORY.md:673` |
| 다른 출처 쪽에서 들어오는 링크가 없는 쪽 | 10쪽 중 9쪽 | gh issue #729 |
| 5개 다(多) note 질문에서 query 경로 | 3문항 패배. 원인은 "the **lexical seed stage**, wrong seeds and not missing paths" | `MEMORY.md:674`, gh issue #729 |
| 같은 문제에서 wiki 쪽에 임베딩 검색 | raw note 임베딩보다 약간 나음 — "the reader is the bottleneck … of *recall*" | gh issue #729 |
| 원인 | 추출 프롬프트가 Related를 "other items extracted from this same source file"로 지시 | gh issue #729, `src/wiki/prompts/ingestion.ts:27`(ingest 갈래) |
| 그래프가 ingest의 결정을 다시 읽을 뿐 | "the graph is largely a render of the ingest's own co-occurrence decisions — which is why PPR cannot discover anything the ingest had not already decided" | `MEMORY.md:479` |

## 앞선 schema-glossary 보고서와 어긋나는 점

| 앞선 주장 | 이번에 본 것 | 근거 |
|---|---|---|
| "허브 Related 링크 lint는 기본 생성 페이지에서 걸리지 않는다 — 절 제목이 `Related Entities`·`Related Concepts`라서"([추정]) | 절 제목 문제는 맞다. 그보다 앞선 문제가 있다. [추정] lint에서는 그래프 edge가 0개라 hub 자체가 안 잡힌다(사례: lint는 `pageMap` 키, 곧 `wiki/entities/Foo.md` 꼴 전체 경로로 노드를 만든다 — `phases/preparation.ts:47-52`, `controller.ts:93-98`; 링크 해석은 `entities/Foo`·`wiki/entities/Foo`·마지막 조각 `Foo`로만 노드를 찾는데 노드 키는 `.md`가 붙어 어느 것도 맞지 않는다 — `build-graph.ts:64-93`; 그래프 테스트는 index 꼴 경로만 쓴다 — `src/__tests__/core/build-graph.test.ts:13-55`; hub는 in-degree ≥2가 필요하다 — `hub-detection.ts:47`, `:83`; 4개). 실행해 확인하지 않았다. 고아 연결 수리가 쓰는 절 제목 `Related Pages`(`system-prompts.ts:26`)는 영어 vault에서 이 스캐너가 읽는 제목과 맞는다. | 좌동 |
| "#H 근거 수치: 검색 PPR recall@5 27.1% vs kNN 24.1%. 53페이지 합성 fixture" | 숫자는 맞다. 다만 kNN 쪽은 저자가 아니라 공동 메인테이너 DocTpoint가 잰 것이고, 같은 문서와 #480이 "그래프 몫은 약 3pp뿐"이라고 해석을 낮췄다. 출시된 5단계 경로가 아니라 이전 cascade로 잰 값이다 | `REAL_VAULT_EVAL.md:77-94`, gh issue #480 |
| 별칭 중복 검사는 엔진이 별칭을 더할 때만 돈다 | 맞다. lint의 별칭 채우기도 다른 쪽 별칭과의 중복 검사 없이 병합한다. ROADMAP도 "`filterRedundantAliases` cross-page gate still needs the wiring follow-up"이라 적는다 | `fix-runners.ts:128-133`, `ROADMAP.md:318` |
| `core/hub-retirement.ts`는 호출처가 없다 | 맞다. 2026-06-30 병합 당시 "Closes the loop on #117/#157/#175"라고 했지만 지금도 연결되지 않았다 | grep 결과 `__tests__` 밖 호출 없음, commit `0a26951` ROADMAP diff |

## README·주석과 코드가 어긋나는 점

| 문서 주장 | 코드 | 근거 |
|---|---|---|
| 4단계 "LLM KB fallback — … the LLM re-seeds the top-N candidates against the full wiki for one semantic pass" | LLM seed 선택은 키워드 생성이 0개일 때만 돈다. 후보는 lex 상위 50 또는 index 앞 50쪽이다. `LLM+KB`는 wiki 없이 일반 지식으로 답하는 상태다 | README.md:242, `select-seeds.ts:149-161`, `:189-194` |
| "Below 200K the cascade may drop earlier stages to fit", 상수 주석의 "Phase 5.4's graceful overflow fallback (auto-shrink + retry)" | 그런 축소·재시도 코드가 없다. `MAX_QUERY_TOP_N_PAGES = 20`도 어디서도 읽지 않는다 | README.md:287, `constants.ts:792-809`, grep `overflow`·`MAX_QUERY_TOP_N_PAGES` |
| tuning commit "walkLength=20 is optimal" | 기본 걸음 수는 처음부터 지금까지 50이다. README는 "3,000 random walks × 50 steps"로 코드와 맞다 | commit `0a26951` diff(`DEFAULT_MAX_STEPS = 50` 그대로), `monte-carlo-ppr.ts:37`, README.md:249 |
| `lexIsReliable` 주석의 예 "4 multi-char / 21 total (19%) → unreliable" | `tokenizeQuery`는 2글자 미만 토큰을 아예 만들지 않으므로 비율 조건은 늘 참이다. 실제 조건은 "토큰 ≥2개"뿐이다 | `ppr-cascade.ts:235-269`, `:294-311` |
| 키워드 생성도 query 모델을 쓴다는 #208 원칙 | `generateQueryKeywords`는 `settings.model`을 직접 쓴다. seed 선택·답은 `resolveModelForTask(…,'query')`를 쓴다 | `query-keywords.ts:154`, `:175`, `seed-selector.ts:398` |
| 중복 검증 프롬프트 "with content analysis" | 본문 없이 두 path와 신호만 보낸다 | `prompts/lint.ts:27`, `dedup-phase.ts:562-564` |
| README "The plugin never modifies your source files" | 병합 때 사용자 note의 링크를 고친다(의도된 설계, 위 결정표) | README.md:370, `core/link-retarget.ts:28-35` |
| pureLLM prompt | 같은 system prompt 안에 "일반 지식으로 답하라" 배너와 "Answer based on the Wiki pages above (not general knowledge)", "Do NOT make up information outside Wiki"가 함께 들어간다 | `assemble-context.ts:83-85`, `:97`, `:120` |

## 엔터프라이즈 다중 작성자 보고서 용도에 비춰

사용자 조건은 "작성자마다 같은 대상을 다른 용어로 쓴다", "형식 없는 문서가 있다", 목표는 "raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조"다.

### 쓸 만한 장치

| 장치 | 왜 쓸 만한가 | 근거 |
|---|---|---|
| 질의 때 LLM 키워드 → 로컬 전수 매칭 | 용어 불일치를 질의 쪽에서 메운다. LLM은 동의어·번역·약어만 내고, 수천 쪽 매칭은 토큰 없이 코드로 한다. 별칭이 쌓일수록 좋아진다 | `query-keywords.ts:72-97`, `select-seeds.ts:229-232` |
| 질의 경로를 칩으로 노출 (`Lex+PPR`/`LLM+PPR`/`LLM+KB`) + 답마다 저장 | 사람이 "이 답이 wiki에서 왔나"를 바로 본다. 감사 추적에 맞다 | `select-seeds.ts:12-20`, `QueryView-class.ts:656-663` |
| 인용 근거 스캐너 | wiki의 인용이 원본 문서에 실제로 있는지 코드로 확인한다. 원본 note까지 읽는다. 여러 사람이 쓴 보고서에서 LLM 요약이 원문을 벗어났는지 잡는 데 바로 옮길 수 있다 | `scanners.ts:287-388`, `programmatic.ts:248-277` |
| source drift 스캐너 | 원본 보고서가 고쳐졌는데 wiki가 옛 판을 요약하고 있으면 해시로 잡는다. 보고서가 개정되는 조직에 필요하다 | `scanners.ts:514-564` |
| 병합 시 vault 전체 링크 재지정 + 별칭 학습 | 두 작성자의 다른 이름을 한 쪽으로 합쳐도 기존 링크가 끊기지 않는다 | `merge-duplicates.ts:42-75`, `:185-201` |
| stub을 LLM이 채우지 않는 규칙 | 근거 없는 쪽이 그럴듯한 내용으로 채워지는 것을 막는다 | `fix-dead-link.ts:71-92` |
| 출력 모드 강등 + (baseURL, model) 캐시 | 사내 게이트웨이·로컬 모델처럼 구조화 출력 지원이 제각각인 환경에서 한 번의 400으로 맞는 모드를 찾는다 | `output-mode-prober.ts:1-53` |
| task 라벨 + 단계별 정책·계측 | 단계별 비용·시간을 나눠 보고, 단계마다 모델·추론을 바꿀 수 있다 | `llm-client-wrapper.ts:173-213`, `model-resolver.ts:192-204` |
| 진단 LLM 단계를 지운 판단 | "전체 wiki를 LLM이 진단"은 큰 저장소에서 정직하지 않다는 실측. 사내 lint 설계 때 같은 함정을 피할 근거 | commit `0e7496a`, gh issue #473 |

### 걸리는 점

| 걸리는 점 | 왜 문제인가 | 근거 |
|---|---|---|
| 새 데이터와 기존 데이터의 연결고리 발견이 약하다 | 그래프 edge 95%가 같은 note 안이다. PPR은 ingest가 이미 정한 연결만 걷는다. 사용자 목표의 두 번째 절반과 정면으로 부딪힌다 | gh issue #729, `MEMORY.md:479` |
| 질의 1단계가 글자 매칭이다 | 저자 측정에서 query 패배의 원인이 seed 단계다. [추정] 한국어는 조사가 붙은 어절이 통째로 토큰이 되어 제목과 안 맞는다(사례: 한글은 공백 split 토큰과 연속 한글 run 그대로 쓰고 형태소를 자르지 않는다 — `ppr-cascade.ts:252-266`; "크레아틴을"은 제목 "크레아틴"의 부분 문자열이 아니다; 1개). 그러면 매번 LLM 키워드 단계로 넘어간다 | `MEMORY.md:674`, `ppr-cascade.ts:235-269` |
| 단일 사용자·단일 vault 전제 | 권한·작성자·접근 범위 개념이 query·lint 어디에도 없다. README 스스로 "Want a hosted SaaS with team collaboration — there's no backend, no shared state"를 대상 밖으로 둔다. 질의 history는 개인 data.json에 저장된다 | README.md:93, `QueryView-class.ts:669` |
| 답에 들어가는 근거가 요약 절뿐 | entity·concept 쪽은 `## Description`만 잘라 넣고 `## Mentions in Source` 인용은 빠진다. 원문 근거로 답하려면 source 쪽이 함께 뽑혀야 한다 | `load-pages.ts:240-254`, `section-extractor.ts:145-181` |
| 답 인용 검증 없음 | `## References` 링크가 실제 쪽인지 코드가 보지 않는다 | `assemble-context.ts:109-116` |
| 못 찾으면 일반 지식으로 답함 | 사내 용도에서는 "wiki에 없다"가 더 안전할 수 있다. 끌 설정은 없다 | `select-seeds.ts:189-194` |
| 중복 검증이 이름만 본다 | 작성자마다 같은 이름을 다른 대상에 쓰는 경우(동음이의)를 걸러낼 정보가 LLM에게 없다 | `dedup-phase.ts:562-564` |
| 고아 연결·빈 쪽 채우기가 index 앞 2000-3000자만 본다 | 큰 저장소에서는 index 앞쪽(알파벳·파일 순) 몇십 쪽만 후보가 된다 | `orphan-matcher.ts:29-30`, `prompt-builders.ts:33` |
| 대화 저장은 index 전체를 프롬프트에 넣는다 | #473과 같은 토큰 폭주가 이 경로에는 남아 있다 | `conversation-ingest.ts:111-112` |
| frontmatter `sources:` 링크가 관련 edge로 섞인다 | "추출된 곳"과 "관련된 것"을 구별하지 않는다. 사내 그래프에선 둘을 다른 edge 종류로 둬야 한다 | gh issue #480 |
| lint가 스캔 중에 디스크를 고친다 | 이중 링크·sources 정규화가 보고 전에 조용히 쓰인다. 여러 사람이 편집하는 저장소에서는 변경 기록·승인과 부딪힌다 | `phases/preparation.ts:62-115` |
| 수리는 쪽당 LLM 1회, 승인 단위는 버튼 하나 | Fix All은 6단계를 한 번에 돌린다. 쪽별 미리보기·승인은 없다. ROADMAP도 "Preview-Confirm gate"를 미구현 설계로 둔다 | `controller.ts:427-618`, `ROADMAP.md:375` |

## 모르는 것

| 모르는 것 | 무엇을 보면 아나 |
|---|---|
| 여러 seed PPR을 합이 아니라 최댓값으로 합친 이유 | gh issue #198 댓글 전체, commit `560ade0`·`bc187f8` 본문 |
| `damping` 0.05 튜닝 때 쓴 평가 스크립트의 걸음 수가 코드의 50과 같았는지 | 커밋에 없는 `/tmp/ppr-eval/eval-vault.ts`(commit `0a26951` "not committed"). 저자에게 물어야 한다 |
| lint 그래프 edge가 정말 0인지 | 실제 vault에서 lint 실행 후 콘솔 `lintWiki: N hub pages with link density issues`(`programmatic.ts:285`) 값. 이번 규칙상 실행하지 않았다 |
| 대화 저장 때 source 제목 slug가 기존 source와 같으면 덮어쓰는지 | `wiki-engine.ts`의 `createOrUpdateFile`(ingest 갈래 범위)를 읽으면 안다 |
| Smart Fix All이 병합으로 지워진 쪽에 대한 죽은 링크 수리를 어떻게 넘기는지 | `wiki-engine.ts`의 `fixDeadLink`가 없는 source 파일을 받을 때의 분기 |
| 병합 병렬 실행(`pageGenerationConcurrency`>1) 때 A→B, B→C 같은 사슬 쌍이 충돌하는지 | `runDuplicateMerges`(`fix-runners.ts:394-446`)는 쌍 사이 의존을 보지 않는다. 테스트 `src/__tests__/wiki/lint/fix-runners.test.ts`나 실제 실행 |
| `openai-compat-sdk-client.ts` 재시도 계층들이 겹칠 때의 순서 전체 | 이 파일 `:324-900`을 끝까지 읽어야 한다(이번엔 grep으로 위치만 봄) |
| 미병합 `feat/729-reader-recall-2026-10-07` 브랜치가 main에 들어올지, 들어오면 검색 구조가 어떻게 바뀌는지 | 해당 브랜치의 `src/core/assembly.ts`와 #729·#819 스레드 |

# gd4ai-why — GD4AI/obsidian-llm-wiki의 이력과 설계 이유

갈래: gd4ai-why. 대상: `lab/repos/GD4AI_obsidian-llm-wiki`, HEAD `f41a39d` (2026-10-09), 1224 commits, 라이선스 Apache-2.0.
이 노트는 "무엇을 왜 골랐나"와 "언제 바꿨나"를 다룬다. 모듈 내부 동작의 깊은 설명은 다른 갈래 몫이고, 여기서는 이유를 대기 위해 필요한 만큼만 코드를 읽었다.

## 0. 표기와 범위

- 출처 표기: 레포 파일은 레포 루트 기준 `path:line`. 이슈·PR은 `#번호`(GitHub GD4AI/obsidian-llm-wiki). 커밋은 짧은 hash. 토론은 `D번호`(GitHub Discussions).
- "왜"의 두 종류: 작성자가 밝힌 이유는 원문을 큰따옴표로 옮기고 출처를 단다. 내가 추론한 이유는 `[추정]`을 달고 근거 사례와 개수를 문장 끝 괄호에 붙인다. 근거가 없으면 `모르는 것:`으로 적는다.
- 사람 이름(역할): `green-dalii`/`Greener-Dalii`는 원저자·메인테이너다. `DocTpoint`는 2026-05-19부터 이슈를 올리기 시작한 기여자이고, 2026-09부터 공동 메인테이너다(README.md:409). GitHub 조직 `GD4AI`의 설명은 "Greener & DocTpoint for AI"이고 조직 생성일은 2026-09-06이다(`gh api orgs/GD4AI`). 저장소 생성일은 2026-04-26이다(`gh repo view`). 원래 주소는 `green-dalii/obsidian-llm-wiki`였고 이슈 본문 링크가 그 주소를 쓴다(#175, #198 댓글 링크).
- 설계 "이유"의 대부분은 코드가 아니라 이슈 토론에 있다. 특히 DocTpoint가 측정을 붙여 올린 이슈(#117, #157, #175, #330, #479, #480, #482, #514, #519, #568, #588, #729)가 방향을 바꿨다. 메인테이너 문서도 이 점을 적는다. "your issues have been driving the roadmap for two months"(#330 green-dalii 댓글 2026-07-27) — 두 달 동안 로드맵을 끌어온 것은 당신의 이슈였다.

### 끝까지 읽은 것

- README.md 전부, AGENTS.md 전부, ROADMAP.md 전부, CLAUDE.md(포인터 stub), MEMORY.md의 Contents·Current state·Key design decisions·Architectural invariants·Hermes cross-reference·Appendix A 중 #729 설계 기록(MEMORY.md:1-48, 294-345, 569-760).
- docs/contributions/openai-codex-oauth-proposal.md(17줄, 설계 이유와 관계 적음).
- 코드: `src/core/candidate-gate.ts` 전부, `src/wiki/page-factory/path-resolution.ts` 전부, `src/wiki/prompts/ingestion.ts` 전부, `src/wiki/wiki-engine.ts:1100-1260`(gate 구간), `src/types.ts:128-175`(EntityInfo/ConceptInfo/CandidateCoverage), `src/core/monte-carlo-ppr.ts:1-60`, `src/core/ppr-cascade.ts:1-60`, `src/core/candidate-window.ts:1-30`, `src/wiki/query-engine/pipeline/select-seeds.ts:195-215`.
- 이슈(본문+댓글 전부): #30, #40, #116, #117, #142, #157, #175, #198, #213, #216(앞부분), #312(앞부분), #317(끝부분), #328, #330, #358(본문+첫 댓글), #472, #479, #480, #482, #514, #519, #568, #569(PR), #588, #607(PR, 앞부분), #661, #729(본문 앞부분).
- 토론: D49, D224, D237(앞부분), D253, D299, D721.
- git: 첫 80개 커밋 제목, 태그 날짜 전부, 핵심 커밋 본문 f8a311c, f26ffd8, f690ff9, cdd49b3, a7a2236, b63934a, 57da2e4, 6581d5c, 0a26951, 9d6183c, 6a5ba34. 원격 브랜치 `feat/729-reader-recall-2026-10-07`의 커밋 본문 5개.
- 웹: https://llmwiki.greenerai.top/ (첫 화면), /blog/ (목록), /blog/posts/v123-graph-engine-ai-sdk/, /blog/posts/why-llm-wiki-for-obsidian-users/.

### 훑음

- CHANGELOG.md: 머리글 목록과 1.27.0~1.27.1 구간(CHANGELOG.md:90-160)만 읽었다. 1.26.0 첫머리(CHANGELOG.md:349-365)를 훑었다.
- MEMORY.md 나머지(프로세스 규칙, 세션 로그, #603·#741·#701 설계 기록)는 제목만 봤다.
- 이슈 #285, #220, #91, #446, #306, #124, #131, #365, #668, #657은 내려받았지만 본문을 끝까지 읽지 않았다(훑음).
- 토론 D222(PDF 설계), D548(aing 소개)는 훑지 않았다.
- `docs/README_*.md` 10개 번역본, `docs/MODEL-GUIDE.md`(줄 14, 16만), `docs/PDF-OCR-GUIDE.md`(줄 11-23, 188만).
- 원격 브랜치 docs/657-data-residency, docs/memory-*: main 대비 diff 크기만 봤다(문서 1~4개, 37~182줄 추가). 내용은 이미 main의 MEMORY.md·PDF-OCR-GUIDE.md에 합쳐진 것과 같은 주제다.

### 다른 갈래와의 경계

- PPR·cascade·query 파이프라인의 알고리즘 세부, 관련 목록(related-shaping), 별칭 쓰기 경로(aliases.ts, slug.ts), lint·Smart Fix All, frontmatter 직렬화, 쓰기 게이트(#603 rawWrite/pageGuard/notify)는 여기서 깊게 다루지 않는다. 이유와 이력에 필요한 곳만 짚는다.

## 1. 이 갈래가 다루는 부분의 구조

### 1.1 모듈 지도(결정 지점 위주)

```
WikiEngine.ingestSource (src/wiki/wiki-engine.ts)
  ├─ source-analyzer.analyzeSource ── LLM 추출 (prompt: src/wiki/prompts/ingestion.ts analyzeSource)
  │     출력: SourceAnalysis { entities: EntityInfo[], concepts: ConceptInfo[], ... }
  ├─ [opt-in] applyOutcomeTable (core/candidate-gate.ts:629)     ← gateDissentStubs && skipMentionOnlyCandidates
  ├─ [opt-in] gateCandidates   (core/candidate-gate.ts:478)      ← skipMentionOnlyCandidates
  ├─ [항상]  applyCoverageThreshold (core/candidate-gate.ts:551)  ← outcome table을 안 탔을 때
  ├─ selectDomains (core/domain-axis.ts) — 태그 값 검증
  ├─ related 목록 정리 (core/related-shaping.ts)  [다른 갈래]
  └─ 항목마다 page-factory
        resolvePagePath (wiki/page-factory/path-resolution.ts:114)
          ├─ 같은 폴더 같은 slug 파일 → 그 경로
          ├─ ConflictResolver.resolve (core/conflict-resolver.ts) — slug/alias 키 대조
          ├─ 반대 폴더 claim 확인 (#588)
          ├─ 3글자 미만 로마자 이름 → LLM 없이 생성 (#661)
          ├─ selectDedupCandidates → selectCandidateWindow (core/candidate-window.ts) K=30
          └─ LLM resolveEntityDedup (prompts/ingestion.ts:116-140) → appendAliases
              └─ 반대 폴더 일치 시 applyClassificationDecision (path-resolution.ts:387) — 폴더 이동/표시

QueryView → select-seeds.ts:202 pprCascade(query, pageRefs, {graph, topN, seeds})
  └─ ppr-cascade.ts → personalizedPageRank (core/monte-carlo-ppr.ts:40)  [다른 갈래]
```

### 1.2 핵심 자료 구조(이 갈래에서 이유를 다룬 필드)

`EntityInfo`(src/types.ts:128-148), `ConceptInfo`(src/types.ts:150-163):

| 필드 | 뜻 | 이유가 걸린 결정 |
|---|---|---|
| `name` | 원문 언어 그대로의 이름. "NEVER translate"(src/wiki/prompts/ingestion.ts:100) | 위치 gate가 원문에서 이름을 찾는다(#514) |
| `type` | entity 7종 / concept 7종 문자열 | 어휘 닫기(#568, #672) |
| `aliases?` | 추출 단계 별칭 1-2개(선택) | 병합의 slug·alias 대조 키 |
| `summary` | 4-6문장 | dedup LLM 판정 입력(300자), stub 본문(#607) |
| `mentions_in_source`, `mentions_with_provenance?` | 원문 인용 2-4개 | 출처 추적(#244) |
| `related_entities?`, `related_concepts` | "same source file" 안의 이름 | 그래프가 문서 안에 갇힌 원인(#729) |
| `coverage?: CandidateCoverage` | `'defined' \| 'discussed' \| 'named'` (src/types.ts:175) | coverage gate(#568) |
| `domains?` | 이 항목이 속한 태그 부분집합 | 태그 축(#568) |

`GateResult<R>`(src/core/candidate-gate.ts:449-462): `entities`, `concepts`, `dropped: {name, kind, verdict}[]`, `linkedAnyway: string[]`(#620), `applied: boolean`(언어 프로필 없으면 false).
`OutcomeTableResult`(src/core/candidate-gate.ts:605-610): 위에 `stubs: {kind, cell: 'prose+named'|'aside+covered', item}[]`, `existing`을 더한다.
`StubIdentity = 'none' | 'match' | 'ambiguous'`(src/core/candidate-gate.ts:603).
`DropReason`(src/core/candidate-gate.ts:429-435): `'aside' | 'absent' | 'named' | 'aside+named' | 'ambiguous'`.
`PPROptions`(src/core/monte-carlo-ppr.ts:29-34): `numWalks`(기본 3000), `maxSteps`(기본 50), `damping`(기본 0.05, "teleport back to seed" 확률), `rng`(기본 `Math.random`).

## 2. 동작 흐름(이 갈래가 다룬 결정 지점)

### 2.1 Ingest: 추출 → gate → 정체 판정

| 단계 | 입력 | 처리 | 출력 | LLM/결정적 | 실패 처리 |
|---|---|---|---|---|---|
| 1 추출 | 노트 본문 + 지침 + (있으면) 태그 어휘 | `analyzeSource` 프롬프트(src/wiki/prompts/ingestion.ts:11-105). 기존 위키 목록은 넣지 않는다(#482/#484, 2.3절) | EntityInfo/ConceptInfo + `coverage` | LLM | JSON 복구 등은 다른 갈래 |
| 2a 위치 gate(opt-in) | 원문 본문, 후보 이름, 위키 언어 | `classifyCandidate`: 링크 안·제목줄·이름만 든 괄호=prose, 괄호·나열·짧은 목록=aside, 없음=absent (src/core/candidate-gate.ts:384-415) | prose만 통과, 나머지 dropped | 결정적 | 언어 프로필 없으면 `applied:false`로 통과하고 보고(src/wiki/wiki-engine.ts:1190-1192) |
| 2b coverage gate(항상) | 2a 생존자 | `coverage`가 `named`면 버림. 작성자가 링크한 이름은 살림(src/core/candidate-gate.ts:551-575) | 생존자 | 결정적(모델 관찰값 사용) | `coverage` 없거나 모르는 값이면 유지(src/core/candidate-gate.ts:423-424) |
| 2' outcome table(opt-in 둘 다 켰을 때) | 2a+2b 동시 | 결정표: 링크=full, prose+covered=full, prose+named/aside+covered=stub, aside+named·absent=drop(src/core/candidate-gate.ts:612-628) | full/stub/existing/drop | 결정적, stub 생성은 LLM 없음 | 이름을 두 페이지가 별칭으로 가지면 `ambiguous` → drop |
| 3 정체 판정 | 이름, 종류, summary, tags | 2.2절 순서 | 기존 경로 또는 새 경로 | 결정적 → (필요 시) LLM 1회 | 응답 해석 실패는 오류 로그 후 fallbackPath(src/wiki/page-factory/path-resolution.ts:303-322) |

### 2.2 정체 판정 순서(src/wiki/page-factory/path-resolution.ts:114-360)

1. 같은 종류 폴더에 같은 slug 파일 → 그 경로(:145-154).
2. `ConflictResolver`가 같은 종류 제목·별칭 slug 키로 찾는다. 한 페이지만 맞고 반대 폴더 claim이 없으면 병합하고 이름을 별칭에 더한다(:179-187).
3. 반대 폴더에도 같은 이름이 있거나(#588), 같은 종류 두 페이지 이상이 맞으면(#446) LLM 판정으로 넘긴다(:188-209).
4. 아무도 안 갖고 로마자 3글자 미만이면 LLM 없이 새로 만든다(:217-226, constants.ts:922).
5. 양쪽 폴더에서 K=30 window를 만들고, 이름을 가진 페이지를 맨 앞에 두고, LLM `resolveEntityDedup`을 부른다(:233-295).
6. 일치 → 반대 폴더였으면 종류를 한 번 다시 판정해 폴더를 옮기거나 `type_conflict:`를 남긴다(:387-449). 그다음 새 이름을 별칭에 더한다(:336-350).
7. 불일치·해석 실패 → fallbackPath. 같은 종류 여러 페이지 경우만 1위 후보로, 나머지는 새 slug 경로(:355-359).

LLM 호출 지점: 추출(`analyzeSource`), 정체 판정(`resolveEntityDedup`). 둘 다 프롬프트 파일은 `src/wiki/prompts/ingestion.ts`.

### 2.3 Query: cascade

`select-seeds.ts:202`가 `pprCascade(query, pageRefs, {graph, topN, seeds})`를 부른다. `pprOptions`를 넘기지 않으므로 `monte-carlo-ppr.ts`의 기본값(3000 walks, 50 steps, damping 0.05)이 쓰인다(src/wiki/query-engine/pipeline/select-seeds.ts:202-205, src/core/monte-carlo-ppr.ts:36-38). cascade 단계 설명은 README.md:237-245에 있다. 세부는 다른 갈래 몫이다.

## 3. 시기별 방향 전환

| 날짜(태그) | 바뀐 것 | 근거 |
|---|---|---|
| 2026-04-26 (v0.1~1.0) | 첫 커밋부터 Obsidian 플러그인. Anthropic+OpenAI 두 provider. 첫 ROADMAP에는 "语义搜索（嵌入向量）"(의미 검색, 임베딩 벡터)와 "多用户编辑检测/审核工作流"(다중 사용자 편집 감지/검토 흐름)이 계획으로 있었다 | `git show 6581d5c:ROADMAP.md` |
| 2026-04-26 | Karpathy gist를 다시 읽고 "单页生成 vs 多页生成（一个源应生成 10-15 页）"(한 페이지 생성 대 여러 페이지 생성, 한 소스는 10-15쪽을 만들어야 한다)를 근본 결함으로 정리. entity/concept/source 세 종류의 기원 | 57da2e4 (KARPATHY_ANALYSIS.md, 이후 6d58d34에서 삭제) |
| 2026-05-08 (1.7.1) | slug fast path + LLM 의미 dedup 도입 | f8a311c |
| 2026-05-14 (1.7.10) | lint 쪽 3단 중복 탐지(프로그램 신호 → LLM 제목 스캔 → LLM 내용 검증)와 별칭 인프라 | f26ffd8 |
| 2026-05-20 (1.10.1) | 정체 판정에 "title + aliases via case-insensitive slug match"를 LLM 앞에 둠 | cdd49b3 (#32) |
| 2026-05-27 (1.12.0) | 추출 프롬프트에서 위키 전체 페이지 목록을 뺌 | D49 |
| 2026-06-01 | `ConflictResolver` 분리(순수 함수) | a7a2236 |
| 2026-06-16 (1.19.0) | 추출 프롬프트에 compact slug 목록을 다시 넣음 | #116 |
| 2026-06-22 | 임베딩 층 제안(#175) 거절, 그래프 신호로 대체 | #175 |
| 2026-07-02 (1.23.0) | Monte Carlo PPR + 3단 cascade | #198, 0a26951 |
| 2026-07-03 | MIT → Apache-2.0 | D237 |
| 2026-07-22 (1.25.2) | schema 3층 분리 Phase 1 | #328 |
| 2026-07-27 | "complementary memory model"을 설계 기준으로 채택 | #330 댓글, #358 |
| 2026-08-18 (1.26.4 주기) | 추출 프롬프트의 slug 목록을 다시 뺌. "Extraction is reading, not linking" | #482, PR #484 |
| 2026-08-19 | 반대 폴더 claim을 아예 보지 않게 함(same-type only) | PR #499 (#472) |
| 2026-08-22 (1.27.0) | 위치 gate opt-in | PR #521 (#514) |
| 2026-09-02 | 반대 폴더 claim을 다시 보되 LLM 판정으로만 넘김 | PR #589 (#588) |
| 2026-09-04 | coverage 관찰값(항상 켜짐)과 3결과 결정표(opt-in) | PR #569, PR #607 |
| 2026-09-16~10-05 | 그래프가 문서 안에 갇힌다는 진단(#729). 측정 먼저 하고 co-citation을 만들기로 결정(direction A) | #729, ROADMAP.md:109-161 |
| 2026-10-07~11 (main 밖) | 원격 브랜치 `feat/729-reader-recall-2026-10-07`: BM25F, 융합, PPR 기본값 damping 0.30·maxSteps 10, co-citation 설계 기각 | 8dc9c0c, d008289, 0e30655 |

[추정] 방향 전환의 주된 동력은 메인테이너의 계획이 아니라 기여자의 실측이다(사례: #175→#198, #482, #514, #588, #729 — 다섯 번 모두 DocTpoint 측정 이슈가 먼저 있고 메인테이너가 채택했다).

## 4. 설계 결정과 이유

각 결정마다: 결정 / (a) 작성자가 밝힌 이유 / (b) 추론 / 대안 / 이력.

### W1. Obsidian 플러그인으로 만든다

- 결정: 실행 환경을 Obsidian 하나로 둔다. 서버·CLI·별도 앱을 기본으로 두지 않는다.
- (a) README는 의도적 선택 세 가지의 첫째로 적는다. "**Obsidian is the runtime.** No terminal, no separate app, no Docker, no Python. Install from Community Plugins, click Ingest, the wiki lives in your vault from the first second. Obsidian's native Graph View renders your `[[wiki-link]]` graph — built in, zero extra bundle size."(README.md:71) — 터미널·별도 앱·Docker·Python 없이 설치 즉시 vault 안에 위키가 생기고, 그래프 시각화는 Obsidian 기본 Graph View를 쓴다.
- (a) 비교표의 첫 줄도 배포 형태다. "**Other open-source reimplementations of Karpathy's LLM Wiki idea exist — but none ships as a one-click Obsidian plugin.**"(README.md:53) — 다른 구현은 있지만 원클릭 Obsidian 플러그인은 없다.
- (a) Karpathy 원문이 "디렉터리 위의 에이전트"라는 반론(#330 §8)에 메인테이너는 이렇게 답했다. "The plugin provides the directory and the persistence. The agent has no version control, no cross-platform UI, no localisation, no plugin distribution — these are all things the plugin already provides, and turning the plugin into an agent framework would mean throwing away every advantage we built up."(#330 green-dalii 2026-07-27) — 플러그인이 디렉터리·지속성·UI·현지화·배포를 주므로 에이전트 프레임워크로 바꾸면 그 이점을 버린다.
- (a) 블로그: "LLM Wiki doesn't replace Obsidian. It extends it." 그리고 "It coexists with Dataview, Templater, Kanban, and every other plugin you use."(https://llmwiki.greenerai.top/blog/posts/why-llm-wiki-for-obsidian-users/, 2026-04-26) — 대체가 아니라 확장이고 다른 플러그인과 함께 쓴다.
- (a) 대상 밖으로 둔 것: "**Want a hosted SaaS with team collaboration** — there's no backend, no server, no shared state; everything runs locally inside your Obsidian."(README.md:93) — 팀 협업 SaaS는 대상이 아니다.
- (b) [추정] 플러그인 선택은 개인 사용자의 진입 비용과 데이터 주권을 우선한 결과다(사례: README.md:81 "5-minute setup", README.md:84 "data sovereignty", 블로그 첫 화면 "Your vault stays yours." "Nothing leaves your machine." — 세 곳).
- 대안과 그 처리: 헤드리스 CLI. v1.26.0에서 `tools/llm-wiki-cli/`를 노출했다가(CHANGELOG.md:358) 1.27.0에서 저장소 밖 형제 프로젝트 `karpathywiki-cli`로 옮기고, 저장소 안에는 측정 도구 `tools/dev-instrument/`만 남겼다(PR #511, #507). ROADMAP은 이 이동이 "eliminated 49 of ~52 Obsidian Bot errors"라고 적는다(ROADMAP.md:16-18) — Obsidian 심사 봇 오류 52개 중 49개를 없앴다. 다중 vault/다중 위키(#142)는 "Out of scope"로 두고 `wikiFolder` 프리셋 전환을 우회로로 안내했다(#142 댓글 2026-06-18, 06-19, ROADMAP.md:395).
- 결과로 생긴 제약: 코드에서 `document` 전역 금지, Node 모듈은 `Platform.isDesktop` 가드 뒤에만, Obsidian 심사 봇 규칙을 lint보다 위에 둔다(AGENTS.md:371-406). 이름 "Karpathy"를 명령어 접두에서 빼 달라는 요청은 manifest가 마켓 색인에 묶여 있어 거절했다. "Given the poor return on investment (ROI), we will not pursue this modification."(D253 green-dalii 2026-07-10)

### W2. 페이지 종류를 entity / concept / source 셋으로 고정한다

- (a) 출발점은 Karpathy gist 해석이다. 커밋 57da2e4의 분석 문서는 "Wiki 页面结构：摘要页 + 实体页 + 概念页 + 比较页"(위키 페이지 구조: 요약 페이지 + 실체 페이지 + 개념 페이지 + 비교 페이지)를 "正确机制"(올바른 메커니즘)으로 적는다(57da2e4 커밋 메시지). 비교 페이지는 구현되지 않았다(`WIKI_SUBFOLDERS`에 없음 — #213 메인테이너 댓글이 constants.ts:17을 인용).
- (a) 종류를 늘리자는 요청(#213)은 이렇게 거절했다. "this isn't a missing feature; it's an architectural change to the entity/concept duality the Karpathy "Sources → Wiki → Schema" model is built on." 그리고 "LLM-Wiki's philosophy is **self-organization**: the LLM classifies, the user corrects tags as the vault grows. Manual large-scale schema edits ... invite entropy"(#213 green-dalii 2026-06-30) — entity/concept 이분법은 구조의 바탕이고, 사람이 schema를 크게 고치면 엔트로피가 늘어난다.
- 이력(방향 바뀜): 3주 뒤 #328에서 메인테이너가 반대 방향을 제안했다. "Pure constraint locks the plugin at whatever three page types the initial developer guessed at, and every new domain needs a feature request."(#328 본문 §2) — 순수 제약은 처음 개발자가 짐작한 세 종류에 플러그인을 가둔다. Phase 2(설정에서 종류 등록)를 v1.26.0에 "committed"로 적었지만(#358 본문), HEAD까지 만들지 않았다. ROADMAP은 "the schema layer still takes its reported types from code today"라고 정정했다(ROADMAP.md:384-386).
- (b) [추정] 종류 확장이 늦어지는 이유는 정체 판정이 폴더=종류에 묶여 있어서다(사례: #330 §3 "With N registered types, the fraction of the vault the dedup step cannot see grows with N", #588 메인테이너 "turn cross-type dedup from a 1/2 into a 1/N problem" — 두 곳).

### W3. 임베딩을 쓰지 않고 링크 그래프 위 PPR로 검색한다

- 결정: 벡터 DB·임베딩 없이 `[[wiki-link]]` 그래프에서 Personalized PageRank로 seed 주변 페이지를 고른다.
- 발단: DocTpoint가 허브 태그(#117), 링크 변별력(#157, bge-m3 cos − centrality), dedup prefilter, grounding을 "five consumers of one missing capability"로 묶어 공유 임베딩 층을 제안했다(#175 본문).
- (a) 거절 이유 1 — provider 호환: "only OpenAI natively supports /v1/embeddings. DeepSeek, GLM, MiniMax, Ollama, OpenRouter — the providers most of our users actually run — don't."(#175 green-dalii 2026-06-22) — 사용자 다수가 쓰는 provider에 임베딩 엔드포인트가 없다.
- (a) 이유 2 — 상태 부담: "the 2000-page vault JSON cache is a persistent-state burden we'd have to maintain across versions."(#175 같은 댓글), "roughly 12 MB of JSON that has to be versioned, migrated, invalidated on model change, and held in memory."(#198 본문)
- (a) 이유 3 — 신호가 이미 있다: "Every `A → B` link is already an encoded statement of relatedness, computed via LLM at ingest time"(#175 같은 댓글) — 링크는 ingest 때 LLM이 이미 계산한 관련성 진술이다.
- (a) 이유 4 — 수학적 동등성 주장: "Haveliwala's 2002 paper proves that Personalized PageRank over a link graph produces a ranking mathematically equivalent to cosine distance over the graph's adjacency-matrix representation"(#198 본문 §Why not embeddings). 이 주장은 같은 스레드에서 정정됐다. GioiaZheng이 "I would not lean too hard on the embedding-equivalence argument"라고 반박했고(#198 댓글 2026-06-23), 메인테이너는 "embedding-equivalence is the *upper bound* of PPR's behavior"로 물렀다(#198 2026-06-24). 블로그 본문도 "That's wrong"이라고 쓰지만 부록에는 동등성 문장이 남아 있다(https://llmwiki.greenerai.top/blog/posts/v123-graph-engine-ai-sdk/, WebFetch 요약 기준).
- (a) 이유 5 — 철학: "Embedding index maintenance ... contradicts the Karpathy philosophy of knowledge compounding through links, not brittle hidden indexes."(#198 green-dalii 2026-06-28) 같은 댓글이 "The "unlinked page" scenario PPR is blind to doesn't exist in steady-state."라고 적는다.
- (a) 이유 6 — 정체성(나중에 붙음): "`Zero-embedding graph retrieval` is a load-bearing claim of this project — the badge line, the SEO intents ..., the comparison table ... Adopting one would trade the project's positioning for a capability the existing local machinery already reaches."(#729 본문 §Why not embeddings; 같은 취지 MEMORY.md:729-732) — 임베딩 없음이 제품 포지셔닝의 기둥이다. 같은 곳에서 "an embedding endpoint is itself a **model-dependent** dependency that would be paid on every install by every user"라고 floor/ceiling 원칙(W12)에 잇는다.
- 측정 근거와 그 한계:
  - 53페이지 합성 fixture, 질의 10개에서 R@5: lex 13.3%, bge-m3 kNN 24.1%, cascade 27.1%(#198 DocTpoint 2026-06-30, scripts/eval-recall.ts:7-9). README는 이 숫자를 "PPR @5 = 27.1% vs pure-kNN baseline 24.1%"로 쓴다(README.md:251).
  - 측정자 본인의 해석은 다르다. "So the honest case for the graph engine isn't retrieval quality — it's cost."(#198 DocTpoint 2026-06-30) — 그래프 엔진의 정직한 장점은 검색 품질이 아니라 비용이다. 같은 댓글에서 실제 vault의 leave-one-out 링크 예측은 kNN MRR 0.172 ≈ lex 0.171 ≫ PPR 0.088이었다.
  - 메인테이너는 이 해석을 받아들였다. "we're not overclaiming retrieval quality, we're claiming zero-cost retrieval that's good enough."(#198 green-dalii 2026-06-30) 그러나 README는 "zero benefit on retrieval quality"(README.md:255)라고 임베딩 쪽을 깎는 문장을 유지한다.
  - 후속 정정: "a graph whose edges encode co-occurrence *is* a similarity measure, so "PPR ≈ kNN" is the expected outcome. It characterises this edge set — not PPR, and not graph retrieval."(#480 본문) — 엣지가 공출현이라 PPR≈kNN은 예상된 결과다. 메인테이너는 연구 과제로만 기록했다(#480 2026-08-18).
- 결정의 강도가 흔들린 기록: "Decision: No embedding layer. Not for v1.23.0, not for v1.25.0."(#198 2026-06-28) → 이틀 뒤 "No opt-in embedding path in v1.24.0+ roadmap"(#198 2026-06-30) → 종료 댓글 "Embeddings → opt-in in v1.25.0+ (deferred from v1.24.0)"(#198 2026-07-02) → 같은 날 #175 종료 댓글 "Embeddings permanently rejected." → #358 "Out of scope (explicit): ❌ Embedding / vector store / RAG retrieval" → #729 "deferred, not rejected"(M2) → MEMORY.md:306 "@DocTpoint argues the ceiling should come from the notes too, i.e. M2 rejected rather than deferred; the maintainer agrees and the issue still says "deferred"."
- 대안: (1) 임베딩 opt-in 층 + capability probe(GioiaZheng, #198 2026-06-24). (2) 그래프 신호 3종(degree, shared-link ratio, 2차 공통 이웃)(#175 2026-06-22). 채택된 것은 PPR + lex 혼합 cascade다.
- (b) [추정] 실제 결정 요인은 품질이 아니라 provider 호환과 "설치 하나로 끝" 포지셔닝이다(사례: #175·#198·#729가 모두 provider·상태·포지셔닝을 먼저 들고, 품질 비교는 3pp 차이를 "within sampling noise"로 다룬다 — 세 곳).
- 남은 경계(작성자 스스로 표시): "What no name index reaches is the semantically related page whose name never appears in the prose. ... closing it needs a semantic index, which the plugin does not have today."(#482 DocTpoint 2026-08-17) 같은 문장이 #519 본문 끝과 candidate-window.ts:30에도 있다.

### W4. PPR은 Monte Carlo로, 3단 cascade로 돌린다

- (a) Monte Carlo 선택: "Cost scales with walk length × K, **not** with V — a 2000-page vault costs the same per query as a 200-page one"(#198 DocTpoint 2026-06-23). 코드 머리말이 같은 이유를 적는다(src/core/monte-carlo-ppr.ts:3-6).
- (a) 반론과 수용: "Fogaras MC earns its keep on *large* graphs — the sparse cold-start regime is exactly where exact power-iteration PPR is both cheaper *and* variance-free."(#198 DocTpoint 2026-06-28) 메인테이너는 "I went with MC as the default path for simplicity (one knob to tune)"(#198 2026-07-02)로 답했다.
- (a) cascade: "lex-only below thresholds, lex-seeded PPR in the middle, graph-first PPR when mature"(#198 2026-06-27). 임계값 출처는 GioiaZheng 제안 `min_pages=30 / min_edges=30 / edges/pages >= 1.0 / seed_degree >= 1 / LWC > 50%`(#198 2026-06-24)이고 "tuning priors, not defaults to defend upfront"라고 본인이 단서를 달았다(#198 2026-06-28).
- (a) 무작위성 허용 이유: "the default uses Math.random (acceptable for non-deterministic ranking — top-k is robust to sampling noise per #198 consensus)."(src/core/monte-carlo-ppr.ts:19-22)
- 이력(뒤집힘): 같은 무작위성이 2026-10에 결함으로 재분류됐다. "`monte-carlo-ppr.ts:53` defaults `rng` to `Math.random` ... so the graph arm is an estimate rather than a function: a rerun moves the numbers. ... Seeding the rng from the query hash is a prerequisite"(ROADMAP.md:124-126). 동점 처리도 결함으로 지목됐다. "`ppr-cascade.ts:146`, `:348` and `:581` each sort by score alone, so **there is no tie-break**"(ROADMAP.md:119).
- 파라미터 불일치(확인): 튜닝 커밋 0a26951 제목은 "damping=0.05, numWalks=3000, walkLength=20"이고 본문은 "walkLength 20 is optimal (40 slightly regresses)"이다. 그러나 이 커밋의 diff는 `DEFAULT_NUM_WALKS`와 `DEFAULT_DAMPING`만 바꾸고 `DEFAULT_MAX_STEPS = 50`은 그대로 둔다(`git show 0a26951 -- src/core/monte-carlo-ppr.ts`). 운영 경로는 옵션을 넘기지 않으므로 50 step으로 돈다(src/wiki/query-engine/pipeline/select-seeds.ts:202-205). README는 "3,000 random walks × 50 steps each"(README.md:249), 블로그는 "walk length 20"이라 서로 어긋난다.
- 이력(진행 중, main 밖): 원격 브랜치 d008289(2026-10-11)가 기본값을 damping 0.30, maxSteps 10으로 바꾸고 이유를 적는다. "Both vaults agree on direction and magnitude: bridge +8% and +11%." 대가도 적는다. "self MRR drops 0.045 on test10 and 0.102 on test8. ... Adopting it is a judgement".
- 튜닝 근거의 재현성: 실제 vault 튜닝 스크립트는 "Eval scripts live at /tmp/ppr-eval/ (outside repo, not committed)."(0a26951 본문, REAL_VAULT_EVAL.md "Eval Scripts"). `scripts/eval-recall.ts`의 fixture 경로는 메인테이너 로컬 절대경로다(scripts/eval-recall.ts:26).

### W5. 추출 프롬프트에 기존 위키를 넣지 않는다 ("Extraction is reading, not linking")

- 결정(현재): 추출 호출은 지침과 노트만 받는다. 기존 페이지와의 연결은 추출 뒤 결정적 대조와 정체 판정 단계가 한다.
- 이력(두 번 뒤집힘):
  1. v1.12.0(2026-05-27)에 전체 페이지 목록을 뺐다. "For a 2,000-page wiki, that's ~200K characters of page metadata being included in every single extraction call. ... The LLM would occasionally hallucinate unrelated entities from other wiki pages."(D49) — 2000쪽이면 매 추출에 20만 자가 붙고, 다른 페이지의 엔티티를 지어냈다. 결과로 "Ingestion is ~80% faster"(D49).
  2. v1.19.0(2026-06-16)에 slug만 다시 넣었다. 이유는 죽은 링크다. "706 dead links — most caused by the LLM guessing wrong slugs for pages that already exist."(#116 본문)
  3. 1.26.4 주기(PR #484, 2026-08-18)에 다시 뺐다. "**the per-call payload must be a function of the note and the items extracted from it, never of vault size.**"(#482 본문) 측정: 2,843쪽 vault에서 목록이 "about 91 % of the prompt"였고, 생각하는 모델이 목록을 체크리스트처럼 읽어 "116,912 of 120,433 output tokens went into enumerating the list"(#482 본문).
- (a) 링크 문제를 다른 곳에서 푸는 방법: "Resolution happens after generation, against **every** page: title first, then curated aliases."(#482 DocTpoint 2026-08-17) — 생성 뒤 전체 페이지에 이름 해석을 돌린다. `[[E433]]` → `entities/Polysorbate` 예가 "a connection no window can contain"이라고 든다.
- (b) [추정] 이 결정은 비용(prompt cache, 토큰)과 대규모 vault 안정성이 품질보다 앞선 판단이다(사례: #452·#483 "freeze the extraction catalog per run so the prompt cache survives", #482의 91% 수치 — PR 두 개와 이슈 하나).
- 대가: 추출 모델은 기존 이름을 모르므로 같은 대상을 다른 표기로 뽑는다. 그 표기 차이는 모두 W6의 정체 판정이 떠안는다.

### W6. 병합은 결정적 대조(slug·별칭)를 먼저, LLM 판정은 남은 것만

- 결정: 같은 slug 파일 → slug/alias 키 대조 → (조건부) LLM 판정. 판정이 일치하면 새 표기를 별칭에 더해 다음부터는 대조 단계에서 잡히게 한다.
- (a) 대조를 앞에 둔 이유: "Zero LLM cost — pure algorithmic match before semantic resolution"(cdd49b3 본문, #32 수정). 발단은 공백·하이픈 차이로 같은 페이지가 두 번 생긴 버그다(#32 제목). `ConflictResolver`를 따로 뗀 이유는 시험 가능성이다. "Zero side effects — no file IO, no LLM calls. Fully unit-testable without any mock infrastructure."(a7a2236 본문)
- (a) 별칭을 판정 뒤에 더하는 이유: "Append the new name as an alias to the existing page to prevent future duplicates"(src/wiki/page-factory/path-resolution.ts:340-344 주석).
- (a) 같은 표기를 두 페이지가 가질 때 결정하지 않는 이유: "tags rank the candidates, they never decide identity — so the question goes to the semantic dedup"(path-resolution.ts:198-202). 그때 별칭을 더하지 않는 이유: "an unanswered question would spread as a global claim across the candidates"(path-resolution.ts:132-142).
- (a) 반대 폴더 처리 — 두 번 뒤집힘:
  1. 2026-05-28 외부 기여: 반대 폴더 같은 이름이면 별칭으로 잇고 생성을 건너뜀(b63934a).
  2. 2026-08-19 PR #499: 반대 폴더를 아예 보지 않음. "A designator is `(letters, type)`. The same letters in the opposite folder are not weaker candidates for this item, they are candidates for a different item."(#472 green-dalii 종료 댓글) 발단은 `KHK`(효소 Ketohexokinase / 관상동맥질환)가 잘못 병합되는 경우(#472 본문).
  3. 2026-09-02 PR #589: 반대 폴더 claim을 LLM 판정으로만 넘김. "the extraction's `type` is a per-call classification, not a property of the referent: measured on this batch it flips between notes often enough that folder-scoped matching mints a twin roughly every fifth note."(#588 본문) 83노트에서 쌍둥이 18쌍. 현재 코드 주석: "the folder is the extraction's guess, not a property of the referent"(path-resolution.ts:228-230).
- (a) LLM 후보를 30개로 줄인 이유: "the model found a synonym's target in that list 0 of 18 times while it found the same targets 9 of 9 times in a 30-entry window that contained them. The list held the target; it did not deliver it."(path-resolution.ts:52-60, #519 본문) — 전체 목록에 정답이 있어도 모델은 못 찾았다.
- (a) 짧은 이름을 LLM에 묻지 않는 이유: "Two characters carry no information a summary could confirm; the model is guessing."(#661 본문) `Cr`가 `Kreatinin`에 병합된 사례. 한자·가나·한글 두 글자는 완전한 낱말이라 예외로 둔다(path-resolution.ts:109-112).
- (a) 판정 기준: "Never match a page about a related, broader, narrower, or component thing — a relationship is not sameness."(src/wiki/prompts/ingestion.ts:132)
- (b) [추정] 대조 → LLM 순서는 비용과 결정성 둘 다를 위한 것이다(사례: cdd49b3 "Zero LLM cost", #330 §7이 지적한 "pages.find() returns the first page in vault order" 비결정성을 #446·PR #471이 고침 — 두 곳).
- 남은 문제(작성자 표시): 판정은 이름이 같은지만 묻고, "이것은 저것의 한 형태" 같은 관계를 담을 곳이 없어 별칭(정체 주장)으로 뭉개진다. "A detector found 61 alias collisions in my vault; of the twelve borderline pairs I reviewed by hand ... none was a duplicate."(#328 DocTpoint 2026-07-22) 관계 타입(#285)과 모호함 기록(#330 §7)은 v1.26.0 "committed"였지만 HEAD에 없다(`grep -rln 'relation_type\|AmbiguityRecord\|derived_from' src` 결과 0건).

### W7. coverage gate: 모델은 관찰만, 문턱은 코드가

- 결정: 추출이 후보마다 `coverage`(defined/discussed/named)를 보고한다. `named`면 페이지를 만들지 않는다. 이 단계는 설정과 무관하게 항상 돈다. 위치 gate는 opt-in이다.
- 발단(#514): 독일어 노트 10개, 후보 115개에서 9.6% 이름 없음, 19.1% 괄호·나열에만, 71.3% 본문(#514 본문, candidate-gate.ts:11-15). 이런 후보마다 페이지 생성·dedup·생성 호출이 든다. "on this vault 58 % of all entity pages look like that."(#514 본문)
- (a) 페이지가 무엇인지에 대한 원칙: "A wiki page is a claim: *this source treats this thing*. A page made from a passing mention makes no such claim ... A graph whose edges come from mentions cannot beat a nearest-neighbour search because it asserts nothing the search does not"(#514 본문) — 페이지는 "이 출처가 이것을 다룬다"는 주장이고, 언급만으로 만든 그래프는 근접 이웃 검색을 이길 수 없다.
- (a) 문턱을 코드에 둔 이유: "The threshold lives here, in code, not in a prompt: every constant below is a policy line that can move without a model noticing. Three prompt-side formulations of the same question were stable within a formulation (91–100 % self-agreement over three draws) and inconsistent between formulations (0.9 % to 13.9 % filtered)."(src/core/candidate-gate.ts:17-21) 같은 원칙이 coverage 쪽에도 있다. "the model reports what the text does (`defined` / `discussed` / `named`), the code decides what is enough. Moving it ... is a change here, not in a prompt, and no model notices."(candidate-gate.ts:417-425) 프롬프트도 같은 분업을 지시한다. "Report what the text does; do not decide whether that is enough"(src/wiki/prompts/ingestion.ts:34)
- (a) 위치 gate가 기본 꺼짐인 이유: "it changes which pages an ingest writes, so it is the user's choice, not an upgrade's."(candidate-gate.ts:25-26) 측정 언어가 독일어뿐이라 "the setting is off by default, so an estimate is a starting point a user opts into, not a claim shipped to everyone."(candidate-gate.ts:107-110)
- (a) coverage가 항상 켜진 이유: "Runs regardless of the #521 opt-in — the deterministic gate is upstream's setting, this half is the local domain-axis design."(src/wiki/wiki-engine.ts:1208-1210) — coverage는 태그 축 작업(#568) PR #569의 커밋 2로 들어왔다(#607 본문 "the coverage observation this table consumes is commit 2 of #569"). 9d6183c의 squash 메시지에는 coverage 문턱을 넣은 이유 문단이 따로 없다.
- (b) [추정] coverage gate가 기본으로 켜진 것은 숙의된 제품 결정이라기보다 태그 축 PR에 실려 들어온 결과다(사례: wiki-engine.ts:1208-1210이 스스로 "local" 설계라고 부르고, #569 PR 본문 요약 6개 항목에 coverage가 없으며, #514에서 같은 측정자가 "prompt-side formulations ... inconsistent between formulations"라고 프롬프트 판단의 흔들림을 측정했다 — 세 곳). 모르는 것: 메인테이너가 "항상 켜짐"을 따로 승인한 기록. #569 리뷰 이벤트 본문을 보면 알 수 있다.
- (a) 두 gate가 엇갈리면 버리지 않고 stub: "their dissent is mixed content — neither half may hold a veto alone."(candidate-gate.ts:578-584) "Measured over 1,153 items across three ingest runs ... converts about half of today's drops into stubs and demotes nothing."(같은 곳)
- (a) 작성자 링크가 두 gate보다 우선: "the author linking a name is a stronger statement about relevance than the model's reading of how the text treats it."(candidate-gate.ts:545-549) 사례 `[[Reis]]`, `[[Blei]]`(6a5ba34).
- (a) 대가를 알고 받아들임: "a thing that fails here in source A and passes in source B gets its page with B, and A is not among its sources. The page set stays order-independent; the evidence set does not."(candidate-gate.ts:50-52)
- 이력: gate가 이름을 관련 목록에서 지우자 "782 of 2612 entity/concept pages with no outgoing link (vs 95 of 2386 pre-gate)"(CHANGELOG.md:114, #620)가 됐고, 기존 페이지 이름은 지우지 않게 고쳤다(PR #621).
- 대안: 프롬프트에 문턱을 두는 것(측정상 0.9~13.9%로 흔들림), 언어 무관 단순 규칙(첫 규칙 7.8/27.8/64.3으로 과대 판정, candidate-gate.ts:12-15).

### W8. 원칙: 판단은 모델, 정책 선은 코드 (반복되는 패턴)

이 레포에서 여러 결정이 같은 문장 꼴로 이유를 댄다.

- 태그: "A term enters the vocabulary through a note's frontmatter, a page's frontmatter, or the settings list — never through the model."(src/core/vocabulary.ts:14-18, 앞선 보고서 인용) "a model-proposed tag is a candidate, not a fact."(#568 본문)
- 모순 기록: 모델 말만으로 기록하던 것을 두 결정적 gate 뒤로 옮겼다. "measured 7 of 9 records were false"(CHANGELOG.md:119, #609).
- 경로·출처: "Contradiction `source_page` is resolved against the page index, never trusted from the model"(CHANGELOG.md:123, #601), `created:`는 "never read from the LLM-generated content"(CHANGELOG.md:365, #388), "prompts: stop asking the model for what the code writes"(ROADMAP.md:190, #774).
- 관련 목록: "Deterministic, no model call"(src/wiki/wiki-engine.ts:1251-1254 주석, #636).
- [추정] 이 원칙은 "작은 로컬 모델에서도 구조가 유지돼야 한다"는 floor 원칙(W12)의 구체형이다(사례: #328 DocTpoint "A rule that is delivered but never demanded is advisory by construction", #729 "The floor must not depend on the model", 위 5개 결정 — 일곱 곳).

### W9. schema 3층 분리 (사용자 지식 / 실행 파라미터 / 엔진 사실)

- (a) "Each layer owns its half, **never overlap, can never conflict**"(AGENTS.md:418). "schema file MUST NOT bake runtime parameters."(AGENTS.md:426)
- (a) 발단: "`buildDefaultSchemaBody()` writes the active tag list directly into the schema file ... If you later change your tag vocabulary in Settings, the schema file still has the old list. The LLM sees two different tag lists"(#328 본문 §3) — 태그 목록이 schema 파일과 설정 두 곳에 있어 어긋났다. 사용자 질문(D299)에 메인테이너가 "目前操作还较为繁琐，需要在设置和Schema中同步更新"(지금은 설정과 Schema를 둘 다 고쳐야 해서 번거롭다, D299 2026-07-19)라고 답한 바로 그 문제다.
- (a) 원칙 이름: "I call this the *knowledge conservation* principle. Every change to the schema passes one test: does it make the long-term coherence of a typical vault higher, or lower?"(#328 본문 §2)
- 반론(작성자 측 기록): "**a rule that is delivered but never demanded is advisory by construction.**"(#330 §2) schema에 "인용 저자를 엔티티로 뽑지 말라"가 두 번 있어도 17개 인용 페이지가 생겼다(#330 §2). 메인테이너는 "Admission criterion in Task Requirements lands in v1.25.10 PATCH"라고 약속했으나(#330 2026-07-27) 이행되지 않았음을 인정했다(#330 green-dalii 2026-09-02 "it's a commitment I made and didn't deliver"). HEAD의 Task Requirements(src/wiki/prompts/ingestion.ts:24-36)에 입장 기준 항목은 없고, 비슷한 규칙은 Important Rules 끝 "Apply the wiki-link test to every candidate"(ingestion.ts:105, 2026-05-26 da02e63부터)뿐이다.
- 이력: Phase 1만 v1.25.2에 들어갔다(#328 2026-07-22 댓글, PR #331). Phase 2(종류 등록)·Phase 3(다중 위키)는 미구현(ROADMAP.md:377-386).

### W10. 태그 어휘는 사람 쪽에서만 늘어난다

- (a) 발단 측정: 노트 자신의 태그만 허용했더니 "43% of answers empty by construction"이었고 모델이 그룹 접두를 3번에 1번 떨어뜨렸다(#568 본문). vault 전체 태그를 어휘로 바꾸자 "42 items with 14 empty and 8 false rejections became 35 items with 7 empty and 0 rejections"(#568 본문).
- (a) 사람 교정 루프: "One human pass over 19 flagged wiki pages (editing tags in place — the workflow this design assumes), then the next run: **rejections 23 → 2, vocabulary-foreign values on pages 19 → 0**"(#569 DocTpoint 2026-08-29) — 위키 페이지에서 사람이 고친 태그가 다음 어휘로 돌아간다.
- (a) 어휘 두 개 문제: "Two tag vocabularies: the prompt offers one list, the write gate enforces another — 7.6 % of pages are born ta[gless]"(#672 제목) → 하나로 합침(PR #673, #762). README: "Prompt, write gate, lint and retag all read this one list, so what the model is offered is exactly what lands on disk"(README.md:148).
- 사용자 목표와의 관계: 이 장치는 "분류 축(태그)"을 닫는 것이지 "대상 이름(엔티티)"을 닫는 것이 아니다. 엔티티 이름은 W6으로 열린 채 들어온다(앞선 보고서 #E와 같음).

### W11. complementary memory model — 원문 노트와 위키는 서로 다른 질문을 맡는다

- 발단: DocTpoint의 전체 재구축 보고. 417노트, 약 5000분 로컬 추론, 2781쪽. "Running inference over the original notes gives better answers than running it over the wiki. ... it inverts the premise the whole design rests on."(#330 본문 서두) 손실 유형을 셋으로 적었다: swallowed(삼켜짐), buried(잘못된 표제 아래 묻힘), scattered(목록이 낱개로 흩어짐). "**the note carried the connections, the wiki carries the fragments plus edges that assert only co-occurrence.**"(#330 본문)
- (a) 메인테이너 답: 원문=episodic, 위키=semantic. "The wiki does not need to win the first question to be valuable; it needs to be the right answer to the second."(#330 green-dalii 2026-07-27) "If this framing is right, the plugin's design target should be **complementary query surface, not fidelity to source**."(같은 댓글) 이것이 하드 룰이 됐다(AGENTS.md:431-441).
- (a) 반박(작성자 쪽): "The raw note won because it still contained what the wiki had dropped. That is not a different query. That is the same query, answered from a lossy copy."(#330 DocTpoint 2026-07-27) 경계 문장을 제안했다. "It does not apply when the wiki page is **missing** information the source carried. That is loss, and loss is a bug."(같은 댓글) 메인테이너는 "I'll add that one-sentence boundary to AGENTS.md"라고 답했으나(#330 2026-09-02), HEAD의 AGENTS.md:431-441에는 그 경계 문장이 없다.
- (a) 함의: "self-improving over time" means a periodic consolidation pass with LLM judgement on past decisions, not a smarter ingest path."(AGENTS.md:438)
- 이행 상태: v1.26.0 "committed" 목록(Preview-Confirm gate, 모호함 기록, 안정된 변경 인터페이스, 관계 타입, 양방향 frontmatter, 종류 등록, #358 본문)중 HEAD에 있는 것은 source-lemma(#357)뿐이다. 나머지는 ROADMAP.md:366-382가 "unbuilt half"로 적는다. v1.26.0 CHANGELOG도 이 항목들이 "scoped but not implemented in this release"라고 적는다(CHANGELOG.md:351). `ingestMode`는 src에 없다(grep 결과는 `ingestModel`만).
- (b) [추정] 이 프레임은 "위키가 원문보다 못하다"는 보고를 "다른 질문"으로 돌릴 위험이 있고, 측정자가 그 위험을 지적했지만 문서에 반영되지 않았다(사례: AGENTS.md:435 문구, #330 2026-09-02 "rewrite that dropped 11 of 13 source mentions" — 두 곳).

### W12. floor / ceiling, 그리고 "그래프가 문서 안에 갇힌다"

- (a) 원칙: "**The floor must not depend on the model.** A user on a small local model should still get a wiki whose cross-source structure is real."(#729 본문 §Design principle; MEMORY.md:306) "model-dependent mechanisms exist to explore the **ceiling** and are **deferred, never rejected**"(MEMORY.md:306).
- (a) 진단: "**95 % of edges connect pages born from the same note.** ... **Nine of ten pages have no incoming link from a page with another source.**"(#729 본문) 원인은 프롬프트다. "These should be other items extracted from this same source file"(src/wiki/prompts/ingestion.ts:33) → "So the write path can **confirm** a name but can never **discover** one."(#729 본문)
- (a) 순서 논쟁: DocTpoint는 손실이 그래프가 아니라 질의의 lexical seed 단계에서 난다고 반박했다. "**A denser graph cannot repair a wrong seed**"(ROADMAP.md:219). 메인테이너는 2026-10-05에 "measure, then M0"로 정했다(ROADMAP.md:111-122).
- 이력(main 밖, 2026-10-11): co-citation(같은 출처를 가진 페이지끼리 엣지) 설계를 측정해 기각했다. "It HURTS, and it hurts a lot. Each source's pages form a clique"(0e30655), "the co-citation projection LOWERS bridge recall 34% and #781's naive design is rejected."(335873b)
- 사용자 목표와의 관계: 새 문서와 기존 문서의 연결 고리는 현재 (1) 이름이 기존 제목·별칭과 같을 때의 `sources:` 덧붙임(앞선 보고서 #C·#D), (2) 질의 시 PPR 확산뿐이다. "새 문서가 기존 페이지와 어떤 관계인지 발견"하는 쓰기 경로는 아직 없다(#729 본문 "Nobody has ever asked: *which other pages in this vault relate to this one?*").

### W13. 병합 triage: 분류 후 경로 선택, 출처 권한

- (a) 전체 재작성이 약한 모델에서 손실을 낸다: "Regeneration is intrinsically lossy for weaker models: they re-summarize the Description and silently drop detail."(#216 본문) 그래서 `mergeAnalysis`로 분류(new/duplicate/complementary/contradictory) 후 경로를 고르게 했다(#216, 메인테이너 수용 2026-06-30).
- (a) 출처 권한 문제: "Whichever source happens to reach the page first defines it; the topic's own source, if it arrives later, can only append."(#312 본문) — 먼저 도착한 출처가 페이지를 정의한다. `Endotheliale Dysfunktion` 페이지가 트랜스지방 노트에서 먼저 만들어져 정의 노트의 내용이 bullet로만 붙은 사례(#312 본문). 대응으로 "source-slug = page-lemma"면 결정적으로 병합하는 경로를 넣었다(CHANGELOG.md:359, PR #357).
- 남은 것: #220 Tier 2 "recency ≠ correctness"는 일부러 열어 둠. "A "newest wins" rule would silently collapse editorial disagreement into recency"(MEMORY.md:603-606).

### W14. 원문 변경(drift)은 보고만 하고 자동 수정하지 않는다

- (a) "**Drift detection is intrinsic to wiki-mode, not an add-on.**"(MEMORY.md:595) "**Auto-revise on drift is empirically harmful.** Wikipedia's record shows a fact revision on page X does not propagate to pages citing X, and an automatic fix risks unbounded cascade corruption. Report the drift, route it to the user; never auto-re-ingest, never auto-revise."(MEMORY.md:599-602)
- (a) 지문은 사용자 노트가 아니라 파생 `wiki/sources/*.md`에만 둔다. 이유는 "because the plugin never writes user notes"다(MEMORY.md:583-585)
- 대안 비교: Hermes(NousResearch) llm-wiki 스킬은 원문 frontmatter에 `sha256:`을 쓰고 문단 단위 출처 표시를 쓴다. 이 레포는 구조화된 `Mentions:` 블록을 유지한다. "Ours parses more reliably for an LLM ... revisit only on user research — not on symmetry."(MEMORY.md:587-590)

### W15. 라이선스 MIT → Apache-2.0 (2026-07-03)

- (a) "The plugin now pulls in **AI-SDK v6 and four of its sub-packages** ... Those packages ship under Apache 2.0 themselves." "Apache 2.0 gives every contributor a clear, explicit patent grant" "Apache 2.0 includes a trademark clause"(D237) — 의존성 라이선스 정렬, 기여자 특허 보호, 상표 보호.

### W16. 데이터 거주(residency)를 경로마다 문서화

- (a) "The plugin runs no server of its own, but the paths above do not all send your file to the same place — and one of them is not a place you choose."(docs/PDF-OCR-GUIDE.md:13) MinerU는 "operated by OpenDataLab (Shanghai AI Lab) on Aliyun infrastructure"이고 보존 정책을 찾지 못했다(docs/PDF-OCR-GUIDE.md:18-22). MinerU 주소는 상수(`MINERU_API_BASE_URL`)라 자체 호스팅으로 바꿀 설정이 없다(ROADMAP.md:404-408).

### W17. 개발 과정 규율(이유가 설계에 영향)

- 측정 없는 주장 금지 문화: AGENTS.md는 답변에 "Numbers, not adjectives", "No hedge"를 요구한다(AGENTS.md:14-24). 커밋마다 성능 5차원 표를 요구한다(AGENTS.md:78-101).
- 죽은 코드 반감기 한 릴리스(AGENTS.md:347-349). [확인] `src/core/hub-retirement.ts`는 2026-06-30(263c9dc)에 들어왔고 HEAD(v1.28.0 이후)까지 운영 호출처가 없다(앞선 보고서 #F와 같음). 자기 규칙을 여러 릴리스 동안 어기고 있다.
- 설계 기록을 이슈에 둔다: "**The measurement, the root cause, the three mechanisms ... are all in issue #729**, which was written as the design document"(MEMORY.md:699). 약속한 `docs/v1.26.0-design.md`(#358)는 어느 브랜치에도 없다(`git log --all -- docs/v1.26.0-design.md` 결과 없음). 그런데 CHANGELOG는 그 파일에서 추적한다고 적는다(CHANGELOG.md:351).

## 5. 앞선 schema-glossary 보고서와 어긋나거나 빠진 점

앞선 보고서: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/reports/schema-glossary/gd4ai-obsidian-llm-wiki.md`.

| 위치 | 앞선 보고서 | 이번에 본 것 | 근거 |
|---|---|---|---|
| #B 용어집 | "예전에는 기존 페이지 목록을 프롬프트 앞에 넣었다. 지금은 뺐다." | 한 번이 아니라 두 번 뺐다. v1.12.0에서 전체 목록 제거 → v1.19.0에서 slug 목록 재도입 → PR #484에서 다시 제거 | D49, #116, #482 |
| #D 새/기존 연결 6단계 | LLM이 일치라고 하면 병합하고 별칭 추가 | 반대 폴더 일치일 때는 종류를 한 번 다시 판정해 폴더를 옮기거나 `type_conflict:`를 남기고, `type_confirmed: true`로 재질문을 막는다. 보고서에 없다 | path-resolution.ts:363-449 |
| #D 반대 폴더 | 현재 동작만 기술 | 현재 동작에 이르기까지 bridge(b63934a) → 차단(PR #499) → LLM 판정(PR #589)으로 두 번 뒤집혔다 | b63934a, #472, #588 |
| #F 범용어 허브, coverage 기준 "항상" | 사실은 맞음 | 항상 켜진 이유가 "local domain-axis design"이라는 주석뿐이고, 같은 측정자가 프롬프트 판단의 흔들림(0.9~13.9%)을 근거로 위치 gate를 코드로 만들었다는 긴장이 빠졌다 | wiki-engine.ts:1208-1210, candidate-gate.ts:17-21 |
| #H 근거 수치, 검색 | "PPR recall@5 27.1% vs kNN 24.1%"를 그대로 기록 | 측정자 본인은 "the honest case ... isn't retrieval quality — it's cost"라고 해석했고, 실제 vault 링크 예측에서는 kNN MRR 0.172 ≫ PPR 0.088이었다. README의 "zero benefit on retrieval quality"는 이 측정과 맞지 않는다 | #198 DocTpoint 2026-06-30, README.md:255 |
| #H, PPR 파라미터 | 언급 없음 | 튜닝 결론(walkLength 20)과 운영 기본값(maxSteps 50)이 다르다 | 0a26951 diff, monte-carlo-ppr.ts:37 |
| #E 새 용어, 이름 | "새 페이지를 자동으로 만든다. 승인 대기열은 없다" | 맞다. 덧붙임: 승인 단계(Preview-Confirm gate)와 모호함 기록은 v1.26.0 "committed"로 약속됐다가 만들어지지 않았다 | #358 본문, ROADMAP.md:366-382, grep 0건 |
| 가져올 것, "용어 출처를 사람 쪽으로 닫는 규칙" | 확인 | 이 규칙은 태그 축에만 적용된다. 엔티티 이름 자체는 닫혀 있지 않다(같은 보고서 #E와 일관, 표현만 보강) | #568 |

어긋남이 아니라 확인된 것: #A의 "기본 추출 프롬프트 안내가 `location`/`technology`를 쓴다"(src/wiki/prompts/ingestion.ts:79, 91)는 HEAD에도 그대로다.

## 6. 엔터프라이즈 다중 작성자 보고서 용도에서 본 장치와 걸리는 점

### 쓸 만한 장치

1. **"모델은 관찰, 코드는 문턱" 분업**(W7, W8). 작성자마다 형식이 다른 보고서에서 "이 보고서가 이 대상을 정의/논의/언급만 하는가"를 모델이 관찰값으로 내고, 페이지를 만들지는 코드 상수로 정한다. 문턱을 바꿔도 모델 프롬프트를 건드리지 않아 측정 재현이 쉽다(candidate-gate.ts:417-425).
2. **위치 gate의 결정적 판정과 작성자 링크 우선**(W7). 형식이 없는 문서에서도 "괄호·나열·짧은 목록 안에만 나온 이름"을 코드로 거른다. 사내 보고서에 작성자가 직접 건 링크나 표기가 있으면 최상위 신호로 쓴다(candidate-gate.ts:395-397, 545-549). 한국어 프로필은 조사 목록 기반이고 "estimated"다(src/core/candidate-gate.ts:146-150). 사내 데이터로 다시 재야 한다.
3. **정체 판정 순서: slug/별칭 → 모호하면 LLM → 판정 뒤 별칭 학습**(W6). 작성자마다 다른 용어(예: 약어·한영 혼용)가 한 번 LLM 판정을 거치면 별칭으로 남아 다음부터 LLM 없이 붙는다. 같은 표기를 두 페이지가 가지면 결정하지 않는 규칙(path-resolution.ts:198-202), 짧은 약어를 LLM에 묻지 않는 규칙(#661)은 사내 약어 충돌(같은 두세 글자 약어가 부서마다 다른 뜻)에 바로 맞는다.
4. **후보 window를 본문(prose)으로 순위 매기기**(#519). 동의어 대상이 window에 드는 비율 25% → 42%, 손으로 고른 동의어 10건 중 2 → 7(candidate-window.ts:14-18). 임베딩 없이 용어 불일치를 줄이는 가장 싼 장치다.
5. **태그 어휘를 vault 태그에서 수확하고 사람이 페이지에서 고친 태그가 되먹임**(W10). 여러 작성자가 쓴 태그를 합쳐 통제 어휘로 만들고, 사람이 고친 결과가 다음 실행에 반영된다(rejections 23 → 2, #569).
6. **drift는 보고만, 자동 수정 금지**(W14). 여러 사람이 원문을 고치는 환경에서 연쇄 오염을 막는 보수적 기본값이다.
7. **결정의 근거를 이슈에 측정과 함께 남기는 운영 방식**. 이 레포의 결정 대부분은 숫자와 함께 남아 있어서 뒤집을 때도 근거가 따라간다(MEMORY.md Appendix A 머리말 "Read this before reopening one of these decisions.", MEMORY.md:652-653).

### 걸리는 점

1. **협업·권한 모델이 없다.** 대상 사용자가 개인이고 "no backend, no server, no shared state"(README.md:93)다. 작성자별 권한, 페이지 소유권, 승인 흐름이 없다. 첫 ROADMAP의 "多用户编辑检测/审核工作流"(다중 사용자 편집 감지/검토 흐름, 6581d5c:ROADMAP.md)는 사라졌다.
2. **먼저 쓴 출처가 페이지를 정의한다**(#312). 여러 작성자 환경에서는 "누가 이 대상의 권위 있는 출처인가"가 곧 권한 문제다. 이 레포는 source-lemma(파일 이름 = 페이지 이름)일 때만 결정적 우선권을 준다. #787은 그 가정이 회의록 같은 노트에서 틀린다고 지적한다(ROADMAP.md:89).
3. **관계 타입이 없어 "비슷하지만 다른 것"이 별칭(정체)으로 뭉개진다**(W6 끝). 사내 보고서는 "A는 B의 하위 프로젝트", "A는 B의 후속 결정" 같은 관계가 핵심인데 담을 곳이 없다. 61건 별칭 충돌 중 검토한 12건이 모두 중복이 아니었다(#328 DocTpoint).
4. **교차 문서 연결이 쓰기 단계에서 발견되지 않는다**(W12). 관련 목록은 같은 문서 안 이름으로 한정되고(ingestion.ts:33), 엣지 95%가 같은 노트 안이다(#729). 사용자 목표의 "새 데이터와 기존 데이터의 연결고리 발견"은 이 레포에서 열린 문제다. co-citation 단순 설계는 측정으로 기각됐다(0e30655).
5. **임베딩 거절의 이유 일부는 이 레포 고유 사정이다.** provider 호환, 설치 하나로 끝, 포지셔닝(W3 (a) 1·2·6)은 사내 시스템에는 해당하지 않을 수 있다. 측정 자체는 kNN과 PPR이 비슷하거나(53쪽 fixture) kNN이 낫다(실제 vault 링크 예측)는 쪽이다. 측정자는 서로 잘하는 질의 유형이 다르다고 적었다. "embeddings catch conceptual synonyms link-extraction misses; the graph catches structural/proper-noun cohesion embeddings miss."(#198 DocTpoint 2026-06-30)
6. **위치 gate는 기본 꺼짐이고 측정 언어가 독일어뿐**이다. 한국어 사내 문서에 적용하려면 재측정이 필요하다.
7. **모호함을 기록할 곳이 없다.** 판정이 불확실해도 둘 중 하나로 정한다. #330 §7의 "ambiguity record" 제안은 다중 작성자 환경의 사람 검토 지점으로 쓸 만하지만 구현되지 않았다.

## 7. 모르는 것과 무엇을 보면 알 수 있는지

- coverage gate를 항상 켜기로 한 명시적 승인 기록: PR #569의 리뷰 이벤트 본문과 #568 이후 댓글(`gh pr view 569 --comments`의 review 본문, `gh api repos/GD4AI/obsidian-llm-wiki/pulls/569/reviews`)을 보면 알 수 있다.
- coverage 값 분포(실제로 `named`가 몇 %인가): DocTpoint 측정 레포 `llm-wiki-measure`(#519 본문이 언급)나 dev-instrument 실행 로그가 필요하다. 저장소 안에는 없다.
- 실제 vault PPR 튜닝 스크립트와 데이터: "/tmp/ppr-eval/ (outside repo, not committed)"(0a26951). 재현 불가. 원격 브랜치 `feat/729-reader-recall-2026-10-07`의 `tools/dev-instrument/src/recall-diagnostic.ts`가 새 측정 도구라서, 그 브랜치가 main에 들어오면 재현 가능해진다.
- walkLength 20 튜닝 결론이 왜 코드에 반영되지 않았는지: 0a26951 이후 `monte-carlo-ppr.ts` 이력에 설명이 없다. 메인테이너에게 묻거나 #198 이후 v1.23.x PATCH 기록을 더 읽어야 한다.
- Haveliwala 2002의 "코사인 동등성" 주장의 원문 근거: 논문 본문(https://www-cs.stanford.edu/~taherh/papers/topic-sensitive-pagerank.pdf)을 읽지 않았다. 스레드 안에서 이미 정정됐으므로 결론에는 영향이 작다.
- README "first-published: 2025-09 (v0.1.0)"(README.md:14)와 저장소 생성일 2026-04-26의 차이: 저장소 이전(green-dalii → GD4AI)이나 이전 비공개 개발의 흔적인지 알 수 없다. 첫 커밋이 이미 v0.1.0 MVP 기능을 담고 있는지(`git show 6581d5c --stat`의 main.ts 567줄) 보면 일부 짐작은 되지만 날짜 근거는 없다.
- #285(typed edges / OKF), #220(source-revision), #91(중첩 태그), #446(모호 designator) 본문 전체: 내려받았으나 훑지 않았다. 관계 타입 설계의 원문 이유는 #285에 있다.
- 웹: Greener-Dalii 개인 소개(greenerdalii.top)와 블로그 "Why We Sample Instead of Solve"(/blog/posts/monte-carlo-ppr/), "Cutting Ingestion Latency by Removing 200K Characters"(/blog/posts/faster-ingestion/)는 읽지 않았다. W4·W5의 이유를 다른 말로 반복할 가능성이 크다.

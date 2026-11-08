# gd4ai — Obsidian 플러그인 하나 안에서 LLM에게는 읽기·판정·문장만 맡기고 이름 연결·출처·문턱은 코드가 쥐는 llm-wiki이며, 그 경계는 작성자들의 vault 실측이 한 칸씩 옮겨 왔다

GD4AI/obsidian-llm-wiki는 Karpathy llm-wiki 패턴을 Obsidian 커뮤니티 플러그인 "Karpathy LLM Wiki"로 만든 TypeScript 구현이다(manifest.json:2-9).
노트를 넣으면 `wiki/entities/`·`wiki/concepts/`·`wiki/sources/` 페이지가 생기고, 오른쪽 패널에서 질문하고, lint로 손본다.

이 보고서의 경로는 모두 레포 루트(`lab/repos/GD4AI_obsidian-llm-wiki`) 기준이다. 같은 절에서 앞서 전체 경로로 나온 파일은 파일 이름만 적는다.
`#번호`는 GitHub 이슈·PR, `D번호`는 GitHub Discussions, 7자리 hex는 commit이다.
코드는 실행하지 않았다. 근거는 파일 읽기, 읽기 전용 `git`, `gh` 조회다.

## 한눈에

| 항목 | 내용 | 출처 |
|---|---|---|
| 무엇 | Karpathy llm-wiki의 Obsidian 플러그인. 문서 하나에서 entity·concept 페이지 여러 장과 source 요약 페이지 한 장을 만든다 | manifest.json:2-9, README.md:71 |
| 실행 형태 | Obsidian 안에서 도는 플러그인. 서버·DB·임베딩이 없다. LLM provider preset 17개 | README.md:69-73, `src/types.ts:1290-1523` |
| 규모 | src 안 테스트 아닌 `.ts` 66,084줄, 테스트 `.ts` 327개 65,195줄. commit 1,224개, 2026-04-26 ~ 2026-10-09(약 5.5개월). 태그 89개, 원격 브랜치 34개 | `find src -name '*.ts' … \| wc -l`, `git rev-list --count HEAD`, `git tag \| wc -l`, `git branch -r` |
| 사람 | green-dalii/Greener-Dalii(원저자) 1,022 commit, DocTpoint(2026-09부터 공동 메인테이너) 130 commit | `git shortlog -sn`, README.md:409 |
| 라이선스 | Apache-2.0, "Copyright 2025-2026 Greener-Dalii". 2026-07-03에 MIT에서 바꿨다 | LICENSE, NOTICE, D237 |
| 차용 조건 | 코드를 옮기면 LICENSE와 기여자 귀속 목록이 담긴 NOTICE를 함께 두고, 바꾼 파일에 변경 사실을 적는다. 특허 허락이 명시돼 있다. 번들 의존성 고지는 THIRD-PARTY-NOTICES.md에 따로 있다(Apache-2.0 9개, MIT 3개). commit `9bdce00`(2026-07-03) 전 판은 MIT로 배포됐다 | LICENSE, NOTICE:4-30, THIRD-PARTY-NOTICES.md:19-22, `git log -- LICENSE`, D237 |
| 성숙도 | PR과 main push마다 "Five-Gate (lint + typecheck + build + test + css-lint)"와 `pnpm audit`를 돌린다. 태그 push가 release workflow를 띄운다. Dependabot만 봇으로 쓴다. 최신 1.28.0 | `.github/workflows/pr-ci.yml:81-96`, `.github/workflows/release.yml`, manifest.json:4 |
| 분석 commit | `f41a39d` (2026-10-09) | `git log -1` |

이 레포에서 설계 이유는 코드보다 이슈 토론에 더 많다.
메인테이너는 기여자 DocTpoint에게 "your issues have been driving the roadmap for two months"(두 달 동안 로드맵을 끈 것은 당신의 이슈였다)라고 썼다(#330 green-dalii 2026-07-27).

[추정] 방향 전환은 메인테이너의 계획보다 기여자의 실측이 끌었다(사례: #175→#198, #482, #514, #588은 DocTpoint가 측정을 담아 연 이슈이고, #729는 DocTpoint의 413노트 재구축 측정을 메인테이너가 이슈로 옮겼다. 다섯 번 모두 측정이 먼저 있었다).

거의 모든 장치에 측정값이 주석·CHANGELOG·이슈로 붙어 있다.
측정 대부분은 작성자들의 독일어 의료 vault에서 나왔고, 원자료는 저장소에 없다.

## 큰 구조

```
Obsidian
 └ 플러그인 껍데기   main.ts + main-commands/* (mixin 7개) + ui/*         사람이 누르는 곳
     ├ AutoMaintainManager   schema/auto-maintain.ts                      감시·주기 lint·시작 점검
     ├ WikiEngine            wiki/wiki-engine.ts                          ingest 지휘 + 페이지 쓰기 관문
     │   ├ SourceAnalyzer    wiki/source-analyzer.ts                      LLM 추출 루프
     │   ├ 결정적 후보 정리  core/candidate-gate, domain-axis, related-shaping
     │   ├ PageFactory       wiki/page-factory/*                          경로 결정·생성·병합·관련 갱신
     │   │   └ core/conflict-resolver, candidate-window, paragraph-provenance, section-header-canonicalizer
     │   ├ 쓰기 직전 정규화  wiki/page-write-guard.ts + core/frontmatter.ts
     │   └ engine-internals/ index-generator, log-writer, graph-cache
     ├ QueryView             wiki/query-engine/*                          seed 선택 → PPR → 문맥 조립 → 답
     │   └ core/ppr-cascade, monte-carlo-ppr, build-graph, index-search, section-extractor
     ├ Lint                  wiki/lint/*                                  스캐너 9종 + LLM 중복 검증 + 버튼별 수리
     └ SchemaManager         schema/*                                     config.md 절 배달, 제안·diff·적용
LLM 계층  core/create-plugin-llm-client → llm-sdk 어댑터 4종 → llm-client-wrapper (task 정책·계측)
```

| 구성 요소 | 맡는 일 | 대표 파일 |
|---|---|---|
| 플러그인 껍데기 | 명령 12개(수집 4·질의·lint·index 재생성·취소·기록 보기·Welcome 재생성·PDF 캐시 비우기·API 키 되돌리기)와 리본 2개를 등록한다. 메서드는 mixin 7개로 나눠 prototype에 붙인다 | `src/main.ts:451-457`, `src/main-commands/command-registry.ts:49-150` |
| WikiEngine | 문서 하나의 ingest 순서를 지휘한다. 페이지 쓰기 관문 `writeFileWithIntent`를 두지만, 모든 쓰기가 이 관문을 지나지는 않는다(#축별 분석 > 2. 규칙의 위치) | `src/wiki/wiki-engine.ts:944-1662`, `:1993` |
| SourceAnalyzer | 노트 전체를 라운드마다 LLM에 보내 entity·concept JSON을 모은다. 멈춤·재시도·type 보정을 한다 | `src/wiki/source-analyzer.ts:183`, `:343-757` |
| 후보 gate | 이름이 본문에 나오는지(위치)와 모델이 본 다룸 정도(coverage)로 페이지 후보를 거른다 | `src/core/candidate-gate.ts:384-678` |
| PageFactory | 후보마다 기존 페이지를 찾고, 새로 쓰거나 병합한다. 2026-07-12에 1,297줄 god class를 모듈 함수로 쪼갰다 | `src/wiki/page-factory/index.ts:1-26`, commit `6dadf18` |
| 쓰기 guard(guard 켠 intent의 쓰기마다) | 링크 오염 두 패턴 교정, `sources:` 정규화, 제목 줄 간격·각주 괄호 정리 | `src/wiki/page-write-guard.ts:68-130` |
| 재작성 guard(병합·관련 페이지 재작성에서만) | 사라진 섹션, 다른 source가 소유한 문단, H1을 복원한다. frontmatter 재직렬화(`enforceFrontmatterConstraints`)는 호출자가 따로 부른다 | `src/core/paragraph-provenance.ts:241-251`, `src/wiki/page-factory/merge-page.ts:361`, `related-page.ts:183` |
| Query 파이프라인 | 제목·별칭 글자 매칭과 LLM 키워드로 seed를 고르고 링크 그래프에서 Monte Carlo PPR을 돌린다 | `src/wiki/query-engine/pipeline/select-seeds.ts`, `src/core/ppr-cascade.ts` |
| Lint | 결정적 스캐너 9종, LLM 중복 검증, 버튼마다 LLM 수리 | `src/wiki/lint/controller.ts`, `src/wiki/lint/scanners.ts` |
| SchemaManager | `wiki/schema/config.md`를 `## 제목` 단위로 쪼개 task마다 정해진 절만 system prompt에 넣는다 | `src/schema/schema-manager.ts:122-138` |
| LLM 계층 | Vercel AI SDK 위 어댑터 4종과, 설정 주입·task 정책·계측을 하는 wrapper | `src/llm-sdk/create-llm-client.ts:325-401`, `src/llm-client-wrapper.ts:83-212` |

vault에 남는 것은 아래와 같다.
페이지 밖 파일은 PDF 캐시, 설정 파일 `data.json`, opt-in PDF 변환 사본, schema 백업이다. API 키는 vault 밖 OS keychain에 둔다(#엔터프라이즈 llm-wiki에 비추어의 권한 행).

| 경로 | 쓰는 쪽 | 비고 |
|---|---|---|
| `wiki/entities/<slug>.md`, `wiki/concepts/<slug>.md` | 생성·병합·관련 갱신·stub | slug 기본 소문자(`src/core/slug.ts:19-44`) |
| `wiki/sources/<basename>_<6hex>.md` | source 요약 | 경로 FNV-1a 지문(`src/core/source-slug.ts:24`, `:35-44`, `:67-76`). `contentHash`·`source_file`을 코드가 쓴다 |
| `wiki/contradictions/<claim-slug>-<date>.md` | 항목 단위 모순 기록 | `src/wiki/page-factory/merge-page.ts:418-450` |
| `wiki/schema/config.md`, `suggestions.md` | SchemaManager | `src/schema/schema-manager.ts:15-16` |
| `wiki/index.md`, `wiki/log.md` | ingest 끝, lint 수리 뒤, 'regenerate-index' 명령, 대화 저장 때 코드가 index를 재생성한다. log는 추가만 한다 | `src/wiki/wiki-engine.ts:2277-2305`, `src/wiki/lint/controller.ts:285-656`(10곳), `src/main-commands/command-registry.ts:86`, `src/wiki/conversation-ingest.ts:298`. index가 query 후보의 유일한 출처다 |
| `.obsidian/plugins/karpathywiki/pdf-cache/` | PDF·MinerU 변환 캐시 | `src/core/pdf-cache.ts:234` |
| `<원본 폴더>/<이름>.pdf.md` | opt-in(`writePdfMarkdownToVault`) PDF 변환 사본. guard 없는 `RAW_WRITE_INTENT`로 쓴다 | `src/wiki/wiki-engine.ts:899-913` |
| `wiki/schema/config.md.bak.<iso>` | schema Apply 백업(최대 3개) | `src/schema/apply-suggestion.ts:55-67` |
| `data.json` | 설정, query 대화 기록 | `src/types.ts:259-669`, `src/wiki/query-engine/QueryView-class.ts:656-670` |

frontmatter 정식 키는 `type, created, updated, sources, tags, reviewed, aliases` 일곱이고, 그 밖 키는 보존된다(`src/core/frontmatter.ts:290-292`, `:306-335`).

추출 결과 한 항목(`EntityInfo`)은 name·type·aliases·summary·verbatim 인용·같은 문서 안 관련 이름·`coverage`(defined/discussed/named)·`domains`를 가진다(`src/types.ts:128-175`).

## 한 바퀴 흐름

### ingest (원문 → 페이지)

진입점은 `WikiEngine.ingestSource`다(`src/wiki/wiki-engine.ts:944`).

| # | 단계 | 누가 | 근거 |
|---|---|---|---|
| 0 | `.pdf`(또는 MinerU 설정 시 이미지·Office)를 markdown으로 바꿔 같은 함수에 다시 넣는다 | LLM(native `pdf-convert`) 또는 외부 MinerU API | `src/wiki/wiki-engine.ts:739-942`, `:1002-1023` |
| 1 | 빈 본문·허용 확장자·본문 해시 중복을 거른다. 대화형 단일 ingest만 중복 재수집을 묻는다 | 코드 | `src/wiki/wiki-engine.ts:584-599`, `:1032-1043` |
| 1.5 | (opt-in, 기본 꺼짐) 노트에 박힌 로컬 이미지를 앞뒤 문단과 함께 vision 호출로 읽는다. 결과는 `## Embedded Image Visual Evidence` 절로 추출 본문 뒤에 붙고, 설정하면 source 페이지에 감사 절로도 남는다. 이미지 하나 10MiB·묶음 20MiB·8장까지이고 원격 URL은 건너뛴다. provider가 이미지를 거부하면 텍스트만으로 계속한다(commit `2a4a99b`, #687) | LLM `embedded-image-analysis` + 코드 | `src/wiki/source-analyzer.ts:324-329`, `:839-985`, `src/core/embedded-image-resolver.ts:7-10`, `:123`, `src/types.ts:1608-1609` |
| 2 | 노트 전체 + 지침으로 라운드마다 JSON을 뽑는다. 2라운드부터 이미 뽑은 이름을 주고 다시 뽑지 말라고 한다 | LLM `extract` ×N | `src/wiki/source-analyzer.ts:343-757` |
| 3 | 뽑은 모든 이름의 slug를 기존 페이지 제목·별칭 slug와 대조해 `related_pages`를 만든다 | 코드 | `src/wiki/source-analyzer.ts:767-779`, `src/core/index-search.ts:46-66` |
| 4 | 노트 주제(파일 이름)가 후보에 없으면 추가하고 entity/concept 분류만 LLM에 묻는다. 요약이 없거나 분류가 정해지지 않거나 상한에 걸릴 때만 빠지고, 끄는 설정은 없다 | LLM `lemma-classify` | `src/wiki/source-analyzer.ts:1001-1058`, `src/core/source-lemma.ts:64-80` |
| 5 | 어휘 밖 type을 접어 맞추고, 안 맞으면 목록을 주고 다시 고르게 한다 | 코드 → LLM `type-repair` | `src/wiki/source-analyzer.ts:1105-1186` |
| 6 | 위치 gate(opt-in) + coverage `named` 제거(항상), 또는 둘을 합친 결정표 → stub | 코드 | `src/wiki/wiki-engine.ts:1139-1236` |
| 7 | 도메인 태그를 어휘로 검증하고, 관련 목록을 기존 이름으로 교정한다. 고아 페이지에만 형제 3개를 잇는다 | 코드 | `src/wiki/wiki-engine.ts:1240-1282`, `src/core/related-shaping.ts:67-145` |
| 8 | source 요약 페이지를 쓴다. hash·경로·제목·인용 출처는 코드가 덮어쓴다 | LLM `source-page` + 코드 | `src/wiki/wiki-engine.ts:1743-1935` |
| 9 | 후보마다 경로 결정: 같은 slug 파일 → slug·별칭 키 대조 → (모호·반대 폴더·후보 창) LLM 판정 → 판정된 새 표기를 별칭에 추가 | 코드 → LLM `dedup` | `src/wiki/page-factory/path-resolution.ts:114-361` |
| 10 | 새 경로면 생성, `reviewed: true`면 덧붙이기만, 그 밖은 병합(분류 → 섹션별 보완 또는 본문 재작성 → guard) | LLM `page-generate`·`merge-triage`·`source-stance`·`complementary`·`merge-body` + 코드 | `src/wiki/page-factory/create-page.ts:80-173`, `merge-page.ts:91-264` |
| 11 | 3단계에서 맞은 기존 페이지마다 `sources:`에 이번 source를 더한다. 이번 추출에 같은 이름 항목이 있으면 본문도 고쳐 쓴다 | 코드 (+ LLM `related-page`) | `src/wiki/wiki-engine.ts:1461-1496`, `src/wiki/page-factory/related-page.ts:61-203` |
| 12 | 이번 run에서 쓴 페이지끼리 폴더가 틀린 링크를 고친다 | 코드 | `src/wiki/wiki-engine.ts:1701-1741` |
| 13 | index 전체를 다시 만들고 log에 시간·모델·바이트를 남긴다 | 코드 | `src/wiki/wiki-engine.ts:1540-1550`, `:2277-2305` |

ingest·생성·병합 경로의 페이지 쓰기는 `createOrUpdateFile`(= `writeFileWithIntent` + `FULL_WRITE_INTENT`)를 지나 guard를 받고, 쓴 뒤 `generation_complete: true` 도장을 받는다(`src/wiki/wiki-engine.ts:1971-2063`, `src/types.ts:1121-1126`). 도장은 guard를 켠 intent로 쓴 wiki 페이지에만 찍힌다(`wiki-engine.ts:2057-2059`).

이 관문을 거치지 않는 쓰기도 있다. lint 별칭·태그 수리는 guard 없는 `LINT_WRITE_INTENT`로 쓴다(`src/wiki/lint/fix-runners.ts:152`, `:634`, `src/types.ts:1188-1193`). 시작 점검의 `sources:` 정규화와 중복 병합의 링크 재지정은 `vault.process`로 바로 쓴다(`src/core/sources-normalizer.ts:247`, `src/core/link-retarget.ts:285`). 전체 목록은 #축별 분석 > 2. 규칙의 위치에 있다.

한 문서 안에서 페이지 생성(9-10단계)과 관련 페이지 갱신(11단계)이 기본 3개씩 병렬이고, 추출 라운드와 문서끼리는 차례로 돈다(`src/wiki/wiki-engine.ts:1358-1381`, `:1458-1469`, `src/types.ts:1579`, `src/main-commands/ingest-commands.ts:246-272`).

### query (질문 → 답)

진입점은 오른쪽 패널 `QueryView.sendMessage`(`src/wiki/query-engine/QueryView-class.ts:437-743`)이고, 문맥 조립은 `buildWikiContext`(`:1096-1210`)가 한다.

| # | 단계 | 누가 | 근거 |
|---|---|---|---|
| 1 | `wiki/index.md`를 줄 정규식 하나로 파싱해 페이지 목록(path·제목·별칭·첫 줄)을 만든다 | 코드 | `src/wiki/query-engine/pipeline/read-index.ts:30-48`, `src/core/index-search.ts:15` |
| 2 | 엔진 캐시에서 링크 그래프를 꺼내거나, 모든 페이지 본문(frontmatter 포함)의 `[[...]]`로 새로 만든다 | 코드 | `src/wiki/engine-internals/graph-cache.ts:73-87`, `src/core/build-graph.ts:48-103` |
| 3 | 질문 토큰을 제목(3점)·별칭(2점)에 맞춘다. 라틴은 단어 시작만, 한중일은 부분 문자열 | 코드 | `src/core/ppr-cascade.ts:109-186`, `:235-269` |
| 4 | 1위 ≥5점·hit ≥3·토큰 ≥2면 LLM을 건너뛴다. 아니면 질문 언어 + 영어 키워드 5-10개를 받는다 | 코드 → LLM | `src/wiki/query-engine/pipeline/select-seeds.ts:106-114`, `src/wiki/query-engine/pipeline/query-keywords.ts:72-97` |
| 5 | 키워드로 모든 페이지 제목·별칭을 다시 매칭한다. 키워드가 0개일 때만 LLM이 후보 50개에서 seed ≤3개를 고른다 | 코드 (→ LLM) | `src/wiki/query-engine/pipeline/select-seeds.ts:149-161`, `:229-232` |
| 6 | 그래프 성숙도에 따라 lex만 / lex-seeded PPR / graph-first PPR. walk 3000 × 50걸음, seed 복귀 확률 0.05. 상위 10쪽 | 코드 | `src/core/ppr-cascade.ts:355-583`, `src/core/monte-carlo-ppr.ts:36-99` |
| 7 | entity·concept은 `## Description`(없으면 `## Definition`) 절만 4,266자까지, 그 밖은 12,800자까지 잘라 문맥에 넣는다 | 코드 | `src/wiki/query-engine/pipeline/load-pages.ts:83-102`, `src/core/section-extractor.ts:145-181` |
| 8 | 언어 지시·쪽 목록 힌트·본문·인용 규칙 + 사용자 지정 지시로 streaming 답을 받는다. seed가 없으면 "위키에 맞는 페이지가 없어 일반 지식으로 답한다"는 안내 문장을 프롬프트 앞뒤에 넣고, UI는 `LLM+KB` 칩을 붙인다. 같은 프롬프트의 "Answer based on the Wiki pages above (not general knowledge)"와 "Do NOT make up information outside Wiki"가 그대로 남아 지시가 엇갈린다 | LLM | `src/wiki/query-engine/pipeline/assemble-context.ts:83-124`, `src/wiki/query-engine/renderers/retrieval-label.ts:34`, `QueryView-class.ts:531-743` |
| 9 | 답과 검색 경로 칩을 `data.json`에 저장한다. Save 버튼은 `ingestSource`가 아닌 별도 경로(W17)로 저장한다 | 코드 + (Save 시) LLM | `QueryView-class.ts:656-675`, `:984-1023`, `src/wiki/conversation-ingest.ts:55-323` |

답의 `## References` 링크가 실제 페이지인지 보는 코드는 없다(`src/wiki/query-engine/pipeline/assemble-context.ts:109-116`).
답마다 "저장할 가치"를 LLM이 판정하던 `evaluateAndSuggestSave`는 정의만 있고 호출처가 없다(`grep -rn evaluateAndSuggestSave src` 결과 `QueryView-class.ts:370` 정의뿐, commit `d72dffa`).

### 유지보수 (lint·수리·schema)

| # | 단계 | 누가 | 근거 |
|---|---|---|---|
| 1 | wiki 페이지를 읽으면서 이중 링크·`sources:` 오염을 디스크에 바로 고친다 | 코드 | `src/wiki/lint/phases/preparation.ts:62-115` |
| 2 | 스캐너 9종: 별칭 부족, 고아, 태그 위반, 오염 페이지, 죽은 링크, 인용 근거(원본 노트까지 읽어 literal 대조), hub 링크 밀도, source drift(해시), 모순 표식 | 코드 | `src/wiki/lint/phases/programmatic.ts:38-159`, `src/wiki/lint/scanners.ts` |
| 3 | 중복 후보를 제목 앞 2글자·링크 버킷에서 결정적으로 뽑고, Tier 1은 전부, Tier 2는 예산만큼 LLM이 두 path와 신호만 보고 판정한다 | 코드 → LLM | `src/wiki/lint/duplicate-detection.ts:207-253`, `llm-phases/dedup-phase.ts:68-113`, `:562-564` |
| 4 | `wiki/contradictions/` 기록 중 열린 것을 나열한다 | 코드 | `llm-phases/contradiction-phase.ts:78-92` |
| 5 | 보고서를 `log.md`에 쓴다. 수동 lint면 보고서 창을, 자동 lint면 알림만 띄우고, 자동 + `autoSmartFix`면 승인 없이 Fix All을 돈다 | 코드 | `src/wiki/lint/controller.ts:620-657` |
| 6 | 버튼별 수리: 별칭 채우기, 중복 병합(vault 전체 링크 재지정 후 source 휴지통), 죽은 링크(교정 또는 LLM 없는 stub), 고아 연결, 빈 페이지 채우기, 태그 재지정 | LLM + 코드 | `src/wiki/lint/fix-runners.ts`, `merge-duplicates.ts:15-206`, `fix-dead-link.ts:1-120` |
| 7 | "Analyze schema" → LLM이 새 schema 본문 전체를 쓰고, 사람이 diff를 보고 Apply. 백업 3개를 남긴다 | LLM + 사람 | `src/schema/analyze.ts:47-94`, `src/schema/apply-suggestion.ts:55-99` |
| 8 | 시작할 때마다 폴더 구조 확인, `sources:` 정규화, `generation_complete: false`로 멈춘 페이지를 휴지통으로 | 코드 | `src/schema/auto-maintain.ts:355-533` |

재컴파일(원문이 바뀐 페이지를 다시 만드는 단계)은 없다.
원문이 바뀌면 drift 스캐너가 보고만 하고, 다시 넣으면 병합이 "추가·보완"으로만 돈다(`src/wiki/lint/scanners.ts:507-509`).

## 왜 이 구조인가

결정마다 결정 / 대안 / 이유 / 이력 순으로 적는다.
이유는 작성자가 밝힌 것은 원문 인용과 출처로, 추론한 것은 [추정]으로 적는다.

### W1. 실행 환경은 Obsidian 플러그인 하나다

- 결정: 서버·CLI·별도 앱·Docker 없이 Obsidian 안에서만 돈다. 그래프 시각화는 Obsidian 기본 Graph View에 맡긴다.
- 대안: CLI·데스크톱 앱(README 비교표의 nashsu Tauri 앱, atomicstrata CLI), "디렉터리 위의 에이전트"(#330 §8).
- 이유: "Obsidian is the runtime. No terminal, no separate app, no Docker, no Python."(Obsidian이 실행 환경이다, README.md:71). 에이전트로 바꾸자는 반론에 메인테이너는 "The agent has no version control, no cross-platform UI, no localisation, no plugin distribution … turning the plugin into an agent framework would mean throwing away every advantage we built up."(에이전트에는 버전 관리·UI·현지화·배포가 없고, 바꾸면 쌓은 이점을 버린다, #330 green-dalii 2026-07-27)라고 답했다.
- 받아들인 대가: "Want a hosted SaaS with team collaboration — there's no backend, no server, no shared state"(팀 협업 SaaS를 원하면 대상이 아니다, README.md:93).
- [추정] 개인 사용자의 진입 비용과 데이터 주권을 앞에 둔 선택이다(사례: README.md:81 "5-minute setup", README.md:84 "data sovereignty", https://llmwiki.greenerai.top/ 첫 화면 "Nothing leaves your machine." 세 곳).
- 이력: v1.26.0에 레포 안 `tools/llm-wiki-cli/`를 냈다가(CHANGELOG.md:358) 1.27.0에서 형제 저장소 `karpathywiki-cli`로 옮겼다. 이유는 Obsidian 심사 봇이 레포 전체 `.ts`를 검사해 "eliminated 49 of ~52 Obsidian Bot errors"(봇 오류 52개 중 49개를 없앴다, ROADMAP.md:16-18, PR #511·#507). 첫 ROADMAP의 '协作功能'(협업 기능) 절에 있던 "多用户编辑检测"(다중 사용자 편집 감지)와 "审核工作流"(검토 흐름) 항목은 같은 날 문서 재구성 commit `b127638`에서 빠졌다(`git show 6581d5c:ROADMAP.md`:61-66). 빠진 이유는 commit에 적혀 있지 않다.

### W2. 페이지 종류를 entity / concept / source 셋으로 고정한다

- 결정: 폴더 셋과 하위 종류 목록(entity 7개, concept 7개)만 둔다(`src/types.ts:1040-1041`). 관계 종류는 없다.
- 대안: 사용자가 종류를 등록하는 방식(#213 요청, #328 Phase 2).
- 이유: 출발점은 Karpathy gist를 다시 읽은 분석 문서다. "Wiki 页面结构：摘要页 + 实体页 + 概念页 + 比较页"(위키 페이지 구조: 요약 + 실체 + 개념 + 비교 페이지, commit `57da2e4`). 비교 페이지는 만들지 않았다. 종류를 늘리자는 #213에는 "it's an architectural change to the entity/concept duality"(entity/concept 이분법을 바꾸는 구조 변경이다)와 "Manual large-scale schema edits … invite entropy"(사람이 schema를 크게 고치면 엔트로피를 부른다, #213 green-dalii 2026-06-30)로 거절했다.
- 이력: 3주 뒤 메인테이너는 고정 세 종류의 한계를 인정했다. "Neither wins alone. Pure flexibility produces chaos in months. Pure constraint locks the plugin at whatever three page types the initial developer guessed at"(둘 다 혼자서는 이기지 못한다. 유연성만으로는 몇 달 안에 혼란이 오고, 제약만으로는 처음 짐작한 세 종류에 갇힌다, #328 §2). 답으로는 사용자가 정할 층과 엔진이 정할 층을 나누는 방식을 냈다. Phase 2를 v1.26.0 "committed"로 적었지만(#358) HEAD에도 없고, ROADMAP은 "the schema layer still takes its reported types from code today"라고 정정했다(ROADMAP.md:384-386).
- 이유(확장이 늦어지는 까닭): 저장소는 종류 등록이 정체 판정과 묶여 있다고 적는다. "Strongly coupled to cross-type dedup"(교차 종류 dedup과 강하게 묶여 있다, ROADMAP.md:377), "cross-type dedup candidate visibility (#328 Phase 2 pre-condition)"(교차 종류 dedup 후보 노출이 Phase 2의 전제다, #358). #330 §3도 "the fraction of the vault the dedup step cannot see grows with N"(종류가 N개로 늘수록 dedup이 못 보는 몫이 커진다)이라고 적는다.

### W3. 임베딩 없이 링크 그래프 위 PPR로 찾는다

- 결정: 벡터 DB·임베딩 없이 `[[wikilink]]` 그래프에서 Personalized PageRank로 seed 주변 페이지를 고른다.
- 대안: DocTpoint의 공유 임베딩 층 제안(#175, contentHash 키 캐시와 cos prefilter), GioiaZheng의 opt-in 임베딩 + capability probe(#198 2026-06-24).
- 이유(provider): "only OpenAI natively supports /v1/embeddings. DeepSeek, GLM, MiniMax, Ollama, OpenRouter — the providers most of our users actually run — don't."(사용자 대부분이 쓰는 provider에 임베딩 엔드포인트가 없다, #175 green-dalii 2026-06-22)
- 이유(상태 부담): "roughly 12 MB of JSON that has to be versioned, migrated, invalidated on model change"(2,000쪽이면 12MB JSON을 버전·이관·무효화해야 한다, #198 본문).
- 이유(신호가 이미 있다): "Every `A → B` link is already an encoded statement of relatedness, computed via LLM at ingest time"(링크는 ingest 때 LLM이 이미 계산한 관련성 진술이다, #175).
- 이유(정체성, 나중에 붙음): "`Zero-embedding graph retrieval` is a load-bearing claim of this project — the badge line, the SEO intents"(임베딩 없음은 배지·SEO가 기대는 주장이다, #729 "Why not embeddings", MEMORY.md:729-732).
- 측정과 그 한계: 53쪽 합성 fixture에서 R@5는 cascade 27.1%, bge-m3 kNN 24.1%였다(`scripts/eval-recall.ts:7-9`). 측정자 본인은 "So the honest case for the graph engine isn't retrieval quality — it's cost."(그래프 엔진의 정직한 장점은 품질이 아니라 비용이다)라고 적었고, 실제 vault 링크 예측은 kNN MRR 0.172 ≫ PPR 0.088이었다(#198 DocTpoint 2026-06-30). #480은 "a graph whose edges encode co-occurrence *is* a similarity measure, so "PPR ≈ kNN" is the expected outcome"(edge가 동시 출현이면 PPR≈kNN은 당연한 결과다)로 해석을 낮췄다.
- 이력: 강도가 여러 번 흔들렸다. "No embedding layer. Not for v1.23.0"(#198 2026-06-28) → "Embeddings permanently rejected."(#175 2026-07-02 03:49Z) → 같은 날 네 시간 뒤 "Embeddings → opt-in in v1.25.0+ (deferred from v1.24.0)"(#198 2026-07-02 07:51Z) → "deferred, not rejected"(#729 M2). Haveliwala 2002의 "코사인 동등성" 주장은 같은 스레드에서 "embedding-equivalence is the *upper bound*"로 물렀다(#198 2026-06-24).
- 이유(비용 대비 품질): 메인테이너는 "The 3pp gap doesn't justify the 9-provider embedding matrix"(3pp 차로는 provider 9곳의 임베딩 대응을 정당화할 수 없다, #198 green-dalii 2026-07-02)라고 적었고, #175에서는 같은 3pp 차를 "graph signals are sufficient"(그래프 신호로 충분하다)의 근거로 들었다(#175 2026-07-02). 결정 요인이 품질이 아니라 provider 호환 비용이라는 것은 작성자가 밝힌 이유다.

### W4. PPR은 Monte Carlo로, 그래프 성숙도에 따라 3갈래로 돈다

- 결정: walk 3000 × 최대 50걸음, 걸음마다 0.05 확률로 seed 복귀(`src/core/monte-carlo-ppr.ts:36-38`). 그래프가 작으면 글자 매칭만, 중간이면 lex seed PPR, 성숙하면 graph-first.
- 대안: power iteration, 쪽별 PageRank 캐시(#198 질문 5).
- 이유: "Monte Carlo's K×L cost is independent of |V|: a 2000-page vault costs the same per query as a 200-page vault"(비용이 쪽수와 무관하다, `src/core/monte-carlo-ppr.ts:4-6`). 주석은 이 논거를 "per @DocTpoint on #198 Q4/Q5"라고 기여자에게 돌린다. 메인테이너 블로그도 "Cost is O(K × L), independent of |V|."라고 쓰고, 난수를 고정하지 않은 이유로 "the determinism tax on production callers isn't worth the stability tax on rank quality"(결정론을 위해 치르는 비용이 순위 안정성 이득보다 크다)를 든다(https://llmwiki.greenerai.top/blog/posts/monte-carlo-ppr/, 2026-07-04). 반론 "the sparse cold-start regime is exactly where exact power-iteration PPR is both cheaper *and* variance-free"(작은 그래프에선 power iteration이 더 싸고 분산도 없다, #198 DocTpoint 2026-06-28)에 메인테이너는 "I went with MC as the default path for simplicity (one knob to tune)"(손잡이가 하나라 단순해서 MC를 골랐다, #198 2026-07-02)로 답했다. 3갈래 문턱은 GioiaZheng 제안이고 본인이 "tuning priors, not defaults to defend upfront"(지킬 기본값이 아니라 튜닝 출발점)라고 단서를 달았다(#198 2026-06-28).
- 이유(무작위 허용): "acceptable for non-deterministic ranking — top-k is robust to sampling noise per #198 consensus"(top-k는 표본 잡음에 강하다, `src/core/monte-carlo-ppr.ts:19-22`).
- 이력: 같은 무작위성을 2026-10에 결함으로 다시 분류했다. "the graph arm is an estimate rather than a function: a rerun moves the numbers"(다시 돌리면 숫자가 움직인다, ROADMAP.md:124-126). 튜닝 commit `0a26951` 제목은 "walkLength=20"이지만 diff는 `DEFAULT_MAX_STEPS = 50`을 건드리지 않았다(`git show 0a26951 -- src/core/monte-carlo-ppr.ts`). 미병합 브랜치 `d008289`(2026-10-11)는 damping 0.30·maxSteps 10으로 바꾸고 "bridge +8% and +11%"를 근거로 든다.

### W5. 추출 프롬프트에 기존 위키를 넣지 않는다

- 결정: 추출 호출은 "instructions plus the note"(지침과 노트)만 받는다. 기존 페이지와의 연결은 추출 뒤 코드 대조와 정체 판정이 맡는다(`src/wiki/source-analyzer.ts:304-312`). 예외는 vault 태그 어휘 블록(`domain_context`)과 opt-in 이미지 증거 절이다. 태그 블록은 페이지 수가 아니라 태그 수를 따라 자라고 모든 노트에 같아서 prefix cache를 깨지 않는다(`source-analyzer.ts:317-320`, `:324-337`).
- 대안: 기존 페이지 목록(전체 또는 slug)을 프롬프트에 넣어 모델이 연결까지 하게 한다.
- 이유: "Extraction is reading, not linking"(추출은 읽기이지 연결이 아니다, `src/wiki/source-analyzer.ts:310`). 원칙은 "**the per-call payload must be a function of the note and the items extracted from it, never of vault size.**"(호출 크기는 vault 크기가 아니라 노트의 함수여야 한다, #482). 측정: 2,843쪽 vault에서 목록이 "about 91 % of the prompt"였고, 생각하는 모델이 목록을 체크리스트처럼 읽어 "116,912 of 120,433 output tokens went into enumerating the list"(출력 토큰 대부분을 목록 나열에 썼다, #482). commit `57099b7`은 catalog 판이 매번 2라운드를 출력 한도로 잃었고(398–421초) 새 판은 다 돌았다(80–110초)고 적는다.
- 이력: 두 번 뒤집혔다. v1.12.0에서 전체 목록을 뺐고("Ingestion is ~80% faster", D49), v1.19.0에서 "706 dead links — most caused by the LLM guessing wrong slugs"(죽은 링크 706개, #116) 때문에 slug 목록을 다시 넣었고, PR #484(2026-08-18)에서 다시 뺐다.
- 받아들인 대가: 추출 모델은 기존 이름을 모르므로 같은 대상을 다른 표기로 뽑는다. 그 차이는 모두 W6이 떠안는다.

### W6. 정체 판정은 결정론 먼저, LLM은 좁은 후보 창에서만, 판정 뒤 별칭으로 배운다

- 결정: 같은 slug 파일 → 같은 종류 제목·별칭 slug 키 대조(한 페이지면 병합) → 두 페이지 이상이거나 반대 폴더에도 있으면 LLM → 라틴·그리스·키릴 3글자 미만이면 LLM 없이 생성 → 그 밖은 후보 30개 창으로 LLM(`src/wiki/page-factory/path-resolution.ts:109-361`, `src/constants.ts:241`(창 30), `:922`(3글자 문턱)). 판정된 새 표기는 그 페이지 별칭에 더하되, 다른 페이지가 이미 가진 이름이면 넣지 않는다(`src/wiki/page-factory/aliases.ts:103-118`).
- 대안: 임베딩 유사도, 전체 페이지 목록을 LLM에 주기.
- 이유(대조 먼저): "Zero LLM cost — pure algorithmic match before semantic resolution"(LLM 비용 0, commit `cdd49b3`, #32). 대조기를 순수 함수로 뗀 이유는 "Fully unit-testable without any mock infrastructure"(mock 없이 단위 테스트가 된다, commit `a7a2236`).
- 이유(좁은 창): "the model found a synonym's target in that list 0 of 18 times while it found the same targets 9 of 9 times in a 30-entry window that contained them"(긴 목록에서는 18번 중 0번, 30개 창에서는 9번 중 9번 찾았다, `path-resolution.ts:57-62`). 창 순위는 제목 3·별칭 2·본문 키워드 1점이고, 절반 넘는 페이지에 나오는 키워드는 버린다. "the cap replaces a language-specific stop list"(이 상한이 언어별 불용어 목록을 대신한다, `src/core/candidate-window.ts:20-24`).
- 이유(판정 기준): "Never match a page about a related, broader, narrower, or component thing — a relationship is not sameness."(관련·상위·하위·부분은 같은 것이 아니다, `src/wiki/prompts/ingestion.ts:132`)
- 이유(모호하면 배우지 않음): "an unanswered question would spread as a global claim across the candidates"(답 못한 질문이 vault 전체 주장으로 퍼진다, `path-resolution.ts:132-142`). 모호한 경우 LLM이 아니라고 해도 1위 후보로 간다. "a new page is the one answer that is certainly wrong"(새 페이지는 확실히 틀린 답이다, `path-resolution.ts:125-131`).
- 이유(짧은 이름): "Two characters carry no information a summary could confirm; the model is guessing."(두 글자는 요약으로 확인할 정보가 없다, #661). `Cr`가 `Kreatinin`에 병합된 사례에서 나왔다. 한자·가나·한글 두 글자는 "a complete word"(완전한 낱말)라 LLM 판정을 유지한다(`path-resolution.ts:109-112`).
- 이력(반대 폴더, 두 번 뒤집힘): 반대 폴더 같은 이름이면 별칭으로 잇던 외부 기여(`b63934a`, 2026-05-28) → "A designator is `(letters, type)`"(지시어는 글자와 종류의 쌍이다)로 반대 폴더를 아예 안 봄(PR #499, `KHK` 오병합 #472) → "the extraction's `type` is a per-call classification, not a property of the referent"(추출의 type은 호출마다 바뀌는 분류다, #588: 83노트에서 쌍둥이 18쌍)로 LLM 판정에만 넘김(PR #589). 판정되면 폴더를 옮기고 `type_confirmed: true`로 재질문을 막는다(`path-resolution.ts:387-447`). `create-page.ts:8-11` 머리 주석은 아직 두 번째 결정을 적고 있다.
- 이력(별칭): 모호한 fallback에서 별칭을 붙였다가(`b824c80`, 2026-08-16) 이틀 뒤 뺐다(`2806d24`).

### W7. "이 문서가 그 이름을 다루는가"는 모델이 관찰하고 문턱은 코드가 정한다

- 결정: 추출이 후보마다 `coverage`(defined/discussed/named)를 보고하고, `named`면 페이지를 만들지 않는다(항상 켜짐). 이름이 괄호·나열·짧은 목록에만 나오는지 보는 위치 gate는 opt-in이다. 둘이 엇갈리면 결정표가 LLM 없는 stub을 만든다(opt-in, UI 없음)(`src/core/candidate-gate.ts:384-678`).
- 대안: 프롬프트에 문턱을 두는 것, 언어 무관 단순 규칙.
- 이유(코드 문턱): "The threshold lives here, in code, not in a prompt … Three prompt-side formulations of the same question were stable within a formulation (91–100 % self-agreement over three draws) and inconsistent between formulations (0.9 % to 13.9 % filtered)."(같은 질문을 프롬프트 세 가지로 물으면 각자는 안정적이지만 서로 0.9~13.9%로 갈렸다, `src/core/candidate-gate.ts:17-21`). 프롬프트도 "Report what the text does; do not decide whether that is enough"(본문이 하는 일만 보고하고 충분한지는 정하지 말라)라고 지시한다(`src/wiki/prompts/ingestion.ts:34`).
- 이유(페이지가 뜻하는 것): "A wiki page is a claim: *this source treats this thing*. … A graph whose edges come from mentions cannot beat a nearest-neighbour search because it asserts nothing the search does not"(페이지는 "이 출처가 이것을 다룬다"는 주장이고, 언급만으로 만든 그래프는 근접 이웃 검색을 못 이긴다, #514).
- 이유(위치 gate 기본 꺼짐): "it changes which pages an ingest writes, so it is the user's choice, not an upgrade's"(쓰는 페이지가 바뀌므로 사용자가 고를 일이다, `candidate-gate.ts:25-26`). 측정 언어가 독일어 하나뿐이다(`:105-111`). 한국어 프로필은 조사 목록 기반의 "estimated"다(`:146-151`).
- 이유(작성자 링크 우선): "the author linking a name is a stronger statement about relevance than the model's reading"(작성자가 건 링크가 모델의 읽기보다 강한 신호다, `candidate-gate.ts:546-549`, commit `6a5ba34`).
- 받아들인 대가: "a thing that fails here in source A and passes in source B gets its page with B, and A is not among its sources"(A에서 떨어지고 B에서 붙으면 A는 출처에서 빠진다, `candidate-gate.ts:50-52`).
- 이력: gate를 켜자 "782 of 2612 entity/concept pages with no outgoing link (vs 95 of 2386 pre-gate)"(나가는 링크 없는 페이지가 95개에서 782개로, CHANGELOG.md:114) 되어 기존 페이지 이름은 지우지 않게 고쳤다(PR #621). 다만 결정표 경로는 `isKnownPage`를 넘기지 않는다(`src/wiki/wiki-engine.ts:1145-1150`).
- [추정] coverage 문턱은 #568 설계의 3단계로 #569에 함께 들어왔다(사례: commit `9d6183c` 메시지의 "coverage threshold on the candidate gate (#568)", `candidate-gate.ts:21-23`의 "stage 3 of the design", 두 곳). 측정자는 문턱을 "The threshold is a product decision, and it has to live somewhere; I would rather it lived in code"(문턱은 제품 결정이고 코드에 두고 싶다, #514)로 다뤘다. 위치 gate는 opt-in인데 coverage는 항상 켠 이유를 밝힌 원문은 찾지 못했다(#확인하지 못한 것).

### W8. 코드가 아는 값과 분류 어휘는 모델에게 맡기지 않는다

- 결정: `contentHash`, `source_file`, source 페이지 H1, 인용의 `source_path`·`extracted_at`, `created:`, `sources:`는 코드가 쓴다(`src/wiki/wiki-engine.ts:1824-1837`, `src/wiki/source-analyzer.ts:69-95`, `src/wiki/page-factory/create-page.ts:298-307`). 태그·type 어휘는 설정 목록 ∪ 노트 태그 ∪ 위키 페이지 태그에서만 나온다(`src/core/vocabulary.ts:45-59`).
- 대안: 프롬프트가 값을 요구하고 모델 출력을 그대로 쓰기. 구조화 출력에 enum 걸기.
- 이유(값): 모델이 복사한 값은 "a typo, a control character for `α`, and a translation of the file name"(오타, 제어 문자, 파일 이름 번역)이었다(`source-analyzer.ts:61-67`). 생성 경로의 `sources:`는 "5 of 8 "multi-source" pages were born with a second source whose note does not exist … fabricated provenance is worse than none"(8쪽 중 5쪽이 없는 노트를 출처로 달고 태어났다. 지어낸 출처는 없느니만 못하다, `create-page.ts:298-304`).
- 이유(어휘): "A term enters the vocabulary through a note's frontmatter, a page's frontmatter, or the settings list — never through the model."(어휘는 사람 쪽 세 곳으로만 들어온다, `src/core/vocabulary.ts:16-17`). 계기는 프롬프트 목록과 쓰기 검사 목록이 달라 "7.6 % of pages are born ta[gless]"(7.6%가 태그 없이 태어났다, #672, commit `170205b`). enum 대신 사후 보정을 고른 이유는 "about one item in ten arrives with a type the active vocabulary does not admit. Resolve that here, while the source's own words are still at hand"(열에 하나가 목록 밖이니 원문이 손에 있을 때 바로잡는다, `source-analyzer.ts:823-827`). 구조화 출력 필드를 느슨하게 둔 이유는 "a single entity missing one field into a whole-response `NoObjectGeneratedError`"(한 필드 누락이 응답 전체 실패가 된다, `src/llm-sdk/output-schemas.ts:160-163`).
- 이력: `98b82af`·`872508f`(2026-09-12)로 코드가 쓰게 바꾼 뒤 `4ae0f39`(#774)에서 프롬프트 요구까지 지웠다. "a declared property is a request"(선언한 속성은 요청이다, commit `4ae0f39`). 사람이 위키 페이지에서 고친 태그가 다음 어휘로 돌아가 "rejections 23 → 2"(거절 23건 → 2건)가 됐다(#569 DocTpoint 2026-08-29).
- 이유(값, 작성자): "The code knows the path exactly."(코드가 경로를 정확히 안다, commit `98b82af`). 이 commit은 모델이 `Notizen/Zytokine.md`를 `Notizen/Zytokines.md`로 베낀 사례를 함께 든다.
- [추정] 나흘 뒤 #729에 나온 floor 원칙(2026-09-16, proposed, MEMORY.md:306)은 이런 개별 결정들을 일반화한 것으로 보인다(사례: #328 "advisory by construction", #729 "The floor must not depend on the model", 두 곳).

### W9. 병합은 분류 뒤 경로를 고르고, 모델의 재작성은 결정적 층을 지난다

- 결정: triage가 merge/skip/complementary/contradictory를 고른다. skip은 frontmatter만, complementary는 섹션마다 덧붙이기, merge·contradictory만 본문 재작성(`src/wiki/page-factory/merge-page.ts:159-264`). 재작성 결과는 사라지거나 절반 이하로 준 섹션 복원 → 다른 source가 각주로 소유한 문단 복원 → H1 복원을 지난다(`src/core/paragraph-provenance.ts:241-251`). 노트 파일 이름이 페이지 이름과 맞으면 그 노트를 "주 문서"로 보고 skip을 merge로 바꾸고, 노트 전체(12,000자)를 넘긴다(`merge-triage.ts:250-271`, `note-window.ts:38-105`).
- 대안: 매번 본문 전체 재작성.
- 이유(분류): "Regeneration is intrinsically lossy for weaker models: they re-summarize the Description and silently drop detail."(약한 모델은 재생성 때마다 설명을 다시 요약하며 세부를 흘린다, #216). 이미 있던 `mergeAnalysis` 프롬프트가 "never called anywhere in `src/`"였다고 같은 이슈가 적고(#216), 이를 연결한 commit `b7bf5f0`은 "formerly 0-callers"라고 적는다. 불확실하면 "better to rewrite than to silently drop new info"(새 정보를 조용히 버리느니 다시 쓰는 게 낫다, `src/wiki/prompts/merge.ts:73`).
- 이유(주 문서): "Whichever source happens to reach the page first defines it; the topic's own source, if it arrives later, can only append."(먼저 도착한 출처가 페이지를 정의하고, 주제의 진짜 출처는 늦으면 덧붙이기만 한다, #312). "measured on a real ingest, 5 of 7 merges added nothing but links"(병합 7번 중 5번이 링크만 더했다, `merge-page.ts:128-134`).
- 이유(guard): "nine `## Beschreibung` blocks of 800–8400 characters came back from a rewrite at under half their size — 5046 → 335 in the worst case"(재작성 뒤 9개 섹션이 절반 이하로 돌아왔다, `src/core/section-header-canonicalizer.ts:195-201`). "Ownership, not size, is the variable"(크기가 아니라 소유가 기준이다, `paragraph-provenance.ts:18-20`). 토큰 한도에서 잘린 재작성은 채택하지 않는다. 계기는 "one page going 32 KB → 127 KB with 300–760 provenance footnotes"(CHANGELOG.md:67, commit `1428b5d`).
- 이력: 각주 형식은 vault 설정이 정하고 기본 프롬프트·schema는 요구하지 않아, 기본 설정에서 문단 guard는 "no-op without it"(각주 규칙이 없으면 아무 일도 안 한다)이다(`src/core/provenance-marker.ts:4-6`, CHANGELOG.md:105). `reviewed: true` 페이지의 덧붙이기 경로에는 이 guard가 없고 모델이 기존 본문을 다시 써서 낸다(`prompts/merge.ts:191-198`, `merge-page.ts:556-557`). "recency ≠ correctness"(최신이 옳은 것은 아니다)는 일부러 열어 두었다. "A "newest wins" rule would silently collapse editorial disagreement into recency"(MEMORY.md:603-606).

### W10. 모순 기록은 결정적 검사 두 개를 지나야 남는다

- 결정: 항목 단위 모순은 (1) 인용한 페이지 문장이 실제로 페이지에 있고 (2) 별도 LLM 호출이 증거 문장과 함께 "source가 그 주장을 스스로 한다"고 확인해야 `wiki/contradictions/`에 기록된다. 떨어진 항목은 일반 사실로 덧붙인다(`src/wiki/page-factory/contradiction-gates.ts:1-29`, `:199-240`).
- 대안: triage 판단만으로 기록, 프롬프트 규칙 강화.
- 이유: "of nine contradictions the triage recorded in one night, two were real, three were positions the source only REPORTED … and four conflicted with nothing the page says"(하룻밤 9건 중 진짜 2건, 남의 입장을 전한 것 3건, 아무것과도 부딪히지 않은 것 4건, `contradiction-gates.ts:4-8`). 프롬프트 대안은 "removed the false positives and the planted true positive alike"(가짜와 심어 둔 진짜를 함께 지웠다, `:9-11`).
- 이유(별도 파일): "a body block is not a durable carrier, stripUnknownSections removes it on the next rewrite"(본문 블록은 다음 재작성 때 지워진다, `merge-page.ts:192-198`).
- 이력: 범위를 일부러 좁혔다. 페이지 단위 contradictory 전략은 같은 결함이 있지만 "one lane measured, one lane changed"(잰 한 길만 바꿨다, `contradiction-gates.ts:24-27`). lint의 자동 해결 갈래는 "Nothing ever produced that status"(그 상태를 만든 코드가 없다)여서 지웠다(`llm-phases/contradiction-phase.ts:9-15`, #604·#666).

### W11. schema는 사람 지식만 담고, 실행 값은 호출 때 주입하며, 바꿀 때는 diff를 보고 통째로 적용한다

- 결정: `config.md`는 task마다 정해진 이름의 절만 system prompt로 간다(`src/schema/schema-manager.ts:122-138`). 태그 목록·폴더·언어는 설정에서 호출 때 넣는다. 페이지 섹션은 코드 상수 `SECTION_LABELS`만 인정하고 다른 `##` 절은 지운다(`src/wiki/system-prompts.ts:15-150`, `src/core/section-header-canonicalizer.ts:415-430`). schema 변경은 LLM이 새 본문 전체를 쓰고 사람이 diff 창에서 Apply하며, 백업 3개를 남긴다(`src/schema/apply-suggestion.ts:55-99`).
- 대안: schema 파일에 태그 목록을 함께 쓰기(이전 방식), 제안을 patch로 적용, 수동 편집만.
- 이유(3층): "schema file MUST NOT bake runtime parameters. It MUST remain pure user domain knowledge."(schema 파일은 실행 값을 품지 않는다, AGENTS.md:426). 발단은 "If you later change your tag vocabulary in Settings, the schema file still has the old list. The LLM sees two different tag lists"(설정을 바꿔도 schema에 옛 목록이 남아 LLM이 목록 두 개를 본다, #328 §3).
- 이유(diff 승인): "'Suggest Schema Updates' was a silent command-palette invocation … with no preview and no undo."(미리보기도 되돌리기도 없었다) 그리고 "The apply path is a verbatim replace, not a patch — the LLM owns the full new body so the diff is meaningful."(LLM이 본문 전체를 써야 diff가 뜻을 가진다, commit `4692a4f`). 요청자는 "建议 -> 审核 -> 应用 -> 回退"(제안 → 검토 → 적용 → 되돌리기)를 원했다(#97).
- 반론(작성자 쪽): "**a rule that is delivered but never demanded is advisory by construction.**"(전달만 되고 요구되지 않는 규칙은 구조상 권고일 뿐이다, #330 §2). schema에 인용 저자를 뽑지 말라는 규칙이 두 번 있어도 17개 인용 페이지가 생겼다. 메인테이너가 약속한 입장 기준은 "it's a commitment I made and didn't deliver"(약속하고 못 지켰다, #330 2026-09-02)로 남았다.
- 이력: Phase 1만 v1.25.2에 들어갔고(PR #331) Phase 2·3은 미구현이다(ROADMAP.md:377-386). 설정 탭의 "Regenerate Default Schema"는 확인·백업 없이 `config.md`를 덮어쓴다(`src/schema/schema-manager.ts:432-436`).

### W12. 원문 변경(drift)은 보고만 하고 자동으로 고치지 않는다

- 결정: source 페이지 `contentHash`와 원본 노트 해시가 다르면 lint가 보고만 한다(`src/wiki/lint/scanners.ts:514-564`). 여러 파일 창은 바뀐 노트를 표시만 하고 재수집 버튼을 두지 않는다(`src/ui/modals/multi-file-row-state.ts:36-66`).
- 대안: 바뀐 노트 자동 재ingest, 원문 frontmatter에 해시 쓰기(Hermes llm-wiki 스킬 방식).
- 이유: "a re-ingest is additive, so acting on drift automatically would duplicate content rather than revise it"(재ingest는 가산적이라 자동으로 하면 고치지 않고 중복한다, `scanners.ts:507-509`). "**Auto-revise on drift is empirically harmful.** … Report the drift, route it to the user; never auto-re-ingest, never auto-revise."(자동 수정은 해롭다. 보고하고 사람에게 넘긴다, MEMORY.md:599-602). 재수집 버튼을 두지 않은 이유는 "offering a button there would invite exactly the operation that damages the page"(그 버튼이 페이지를 망치는 동작을 부른다, #598 DocTpoint 2026-09-01)이다.
- 이유(지문 위치): "because the plugin never writes user notes"(플러그인은 사용자 노트를 쓰지 않으므로, MEMORY.md:583-585). 다만 lint 중복 병합은 사용자 노트의 링크를 고친다. "Foreign notes are the user's own files"라며 수술적으로 쓴다(`src/core/link-retarget.ts:9-35`).
- 이력: 개정을 반영하는 경로(#220 Tier 1/2)는 아직 없다. [추정] 그래서 이전 판에서 빠진 사실을 거두는 경로가 없다(사례: `mergeFrontmatter`가 sources를 합치기만 함 `src/core/frontmatter.ts:584-596`, triage 4전략에 철회가 없음 `prompts/merge.ts:47-55`, 두 곳).

### W13. lint는 결정적 스캐너가 사실을 내고, LLM은 중복 검증과 수리만 한다

- 결정: 스캐너 9종은 Obsidian API 없는 순수 함수다(`src/wiki/lint/scanners.ts:1-2`). LLM은 중복 검증과 버튼별 수리에만 쓴다. 죽은 링크 stub은 LLM이 채우지 않는다.
- 대안: 위키 전체를 LLM에게 "건강 진단"시키는 단계(삭제됨).
- 이유(진단 삭제): "it only sees a 5-field stats block + 8 pages of content (~5K tokens of a 152K-token vault) — the analysis was dishonest and repeated programmatic findings or invented details"(15만 토큰 vault에서 5천 토큰만 보고 정직하지 않은 분석을 냈다), "Karpathy's lint design is conversational"(commit `0e7496a`). 촉발은 313,754토큰 요청이 HTTP 400을 낸 #473이다.
- 이유(stub 비우기): "the LLM fabricates alias claims, related-link targets, and a summary that looks authoritative but is unsourced … The lint path was a back door around the gate"(근거 없는 그럴듯한 내용을 지어내고, lint가 gate의 뒷문이었다, `src/wiki/lint/fix-dead-link.ts:71-92`).
- 이유(Tier): "truncating would silently drop high-precision duplicates"(자르면 정밀한 중복을 조용히 버린다, `llm-phases/dedup-phase.ts:90-96`). 중복 검증의 thinking을 끈 이유는 "does not improve recall or precision on this task class"(이 작업에선 정확도를 못 올린다, `src/wiki/prompts/lint.ts:29-38`).
- 이유(Fix All 순서): "Aliases are required for Tier 1 duplicate signals (crossLang)"(별칭이 있어야 교차 언어 중복 신호가 산다, `src/wiki/lint/controller.ts:466-468`).
- 이력: 승인 단위는 분류 하나 전체다. "The user gets a single bulk button "Retag N page(s) with LLM" — no per-page approval."(쪽별 승인 없이 버튼 하나, `controller.ts:402-404`). 중복 검증 프롬프트 주석은 "with content analysis"라고 쓰지만 LLM에 들어가는 것은 두 path와 신호 한 줄뿐이다(`prompts/lint.ts:27`, `dedup-phase.ts:562-564`).

### W14. 위키는 원문을 대신하지 않는다는 "complementary memory"와 floor/ceiling 원칙

- 결정: 위키의 목표를 원문 충실도가 아니라 원문과 다른 질문에 답하는 "complementary query surface"로 둔다(AGENTS.md:431-441). 모델과 무관한 장치가 품질의 바닥(floor)을, 모델 의존 장치가 천장(ceiling)을 맡는다(MEMORY.md:306, 상태 proposed).
- 발단: 417노트·2,781쪽 전체 재구축에서 "Running inference over the original notes gives better answers than running it over the wiki. … it inverts the premise the whole design rests on."(원문으로 답하는 편이 위키보다 낫다. 설계 전제를 뒤집는다, #330 서두). "**the note carried the connections, the wiki carries the fragments plus edges that assert only co-occurrence.**"(연결은 노트에 있고, 위키에는 조각과 동시 출현 edge만 남았다).
- 작성자 답: 원문은 episodic, 위키는 semantic이다. "The wiki does not need to win the first question to be valuable; it needs to be the right answer to the second."(위키는 두 번째 질문의 옳은 답이면 된다, #330 green-dalii 2026-07-27).
- 반론과 미반영: DocTpoint는 "The raw note won because it still contained what the wiki had dropped. That is not a different query. That is the same query, answered from a lossy copy."(같은 질문을 손실 사본으로 답한 것이다)라고 반박했다(#330 2026-07-27). 메인테이너는 "the page is missing what the source carried = loss, and loss is a bug"(source가 준 것을 페이지가 잃으면 손실이고 손실은 버그다)라는 경계 한 문장을 AGENTS.md에 넣겠다고 했지만(#330 2026-09-02), AGENTS.md:431-441에 없다.
- 이력(그래프가 문서 안에 갇힘): "**95 % of edges connect pages born from the same note.** … **Nine of ten pages have no incoming link from a page with another source.**"(edge 95%가 같은 노트 출신이고, 10쪽 중 9쪽이 다른 출처에서 들어오는 링크가 없다, #729). 원인은 추출 프롬프트의 "These should be other items extracted from this same source file"(관련 항목은 같은 파일에서 뽑은 것이어야 한다, `src/wiki/prompts/ingestion.ts:33`)이다. "the write path can **confirm** a name but can never **discover** one"(쓰기 경로는 이름을 확인할 뿐 발견하지 못한다). 2026-10-05에 "measure, then M0"(측정 먼저, 그다음 co-citation)로 정했다(ROADMAP.md:109-160).
- 이력(main 밖): `origin/feat/729-phase1-co-citation`의 `7b01a61`(2026-09-22)이 co-citation을 만들었고, `origin/feat/729-reader-recall-2026-10-07`의 `0e30655`가 측정해 "It HURTS, and it hurts a lot. Each source's pages form a clique"(같은 source 페이지끼리 clique가 된다), `335873b`가 "the co-citation projection LOWERS bridge recall 34%"(교차 recall을 34% 낮춘다)로 기각했다. 둘 다 HEAD에 없다(`git merge-base --is-ancestor 0e30655 HEAD` 실패).

### W15. LLM 계층은 AI SDK 위 얇은 어댑터와, 400마다 한 칸씩 내려가는 출력 모드다

- 결정: 손수 짠 클라이언트를 Vercel AI SDK 어댑터 4종으로 바꿨다. 구조화 출력은 `json_schema → json_schema_strict → json_object → text_prompt`로 400을 받을 때마다 내려가고, 내려간 단계를 (baseURL, model) 키로 기억한다(`src/llm-sdk/output-mode-prober.ts:1-68`). `task` 라벨마다 출력 모드와 thinking을 함께 고정하고 시간을 잰다(`src/llm-client-wrapper.ts:173-212`). 모델은 ingest·lint·query 세 갈래로만 나눈다(`src/core/model-resolver.ts:164-204`).
- 대안: provider별 하드코딩, baseURL 단위 캐시(이전), 전역 thinking 토글 하나.
- 이유(SDK): "Eliminates the entire class of provider-version regressions (#137 / #141 / #143 / #147 / #207)"(provider 버전 회귀 부류를 없앤다, commit `0a26951` diff의 ROADMAP 문구), commit `6be9258`.
- 이유(캐시 키): "on ONE LM Studio gateway, Qwen3.5 emits `{"": ""}` under grammar constraint while gemma-4-12b emits full JSON. A per-baseURL cache would demote gemma too"(한 게이트웨이에서도 모델마다 다르다, `output-mode-prober.ts:42-52`). 기록은 재시도 성공 뒤에만 한다. "A transient retry failure (5xx, network blip) must not permanently downgrade the baseURL"(`:18-25`).
- 이유(task 정책): "a `response_format` on the request sets `reasoning_tokens` to 0 regardless of `reasoning_effort`"(구조화 출력을 걸면 추론이 0이 된다)와 "This module exists so that it can be measured"(측정할 수 있게 하려고 만들었다, `src/core/task-policy.ts:3-14`).
- 이유(모델 세 갈래): "per-provider split would 4× the credentials UI and break Test Connection's contract"(provider까지 나누면 자격 UI가 4배가 된다, `src/types.ts:622-627`).

### W16. 사람은 연결 테스트·결과 보고서·lint 버튼에서 개입하고, ingest 결정에는 확인 지점이 없다

- 결정: Test Connection을 통과해야(`llmReady`) ingest·query·lint·schema가 열린다(`src/main-commands/connection-commands.ts:196-200`). 배경 작업은 막지 않고 알림과 log.md 기록 패널로 알린다. 무엇이 페이지가 되고 어느 페이지와 같은지는 사람에게 묻지 않는다.
- 대안: 기본 모델 하드코딩, ingest마다 보고서 창, 쓰기 전 미리보기·확인(Preview-Confirm gate).
- 이유(연결 gate): "This prevents silent failures from stale default models (especially Ollama's llama3)"(오래된 기본 모델의 조용한 실패를 막는다, commit `9798a5d`).
- 이유(알림): "A fix completed in the background should report, not block."(배경 작업은 막지 말고 알린다, #204 저자 답).
- 원칙과 실제의 간극: AGENTS.md:300은 "Human-in-the-loop — LLM suggests, user decides"라고 쓴다. DocTpoint는 "All four hold in the query path. **None of them holds in the ingest path.**"(query에선 지켜지고 ingest에선 하나도 안 지켜진다, #330 §1)라고 짚었다. 저장소는 Preview-Confirm gate를 "UX cost evaluation is still pending discussion"(UX 비용 평가가 논의 중)으로 미뤄 두었다(ROADMAP.md:375).
- 이력: v1.26.0 "committed" 목록(#358) 가운데 HEAD에 들어온 것으로 확인한 것은 source-lemma(#357)와 교차 폴더 dedup 후보 노출(PR #589, `2bd4a6d`, `git merge-base --is-ancestor` 통과) 두 가지다. Preview-Confirm gate·모호함 기록·관계 타입·종류 등록은 없다(ROADMAP.md:366-382, `grep -rln 'relation_type\|AmbiguityRecord\|derived_from' src` 0건).

### W17. 질의 답은 사람이 Save를 눌러야 위키로 돌아간다

- 결정: Save 버튼은 `ingestSource`가 아닌 별도 경로 `ConversationIngestor`로 저장한다. 먼저 LLM이 index 앞 3,000자와 대화 앞 1,500자로 중복 여부를 판정하고, "fully_redundant"면 저장을 건너뛰고 알린다(`src/wiki/conversation-ingest.ts:80-103`, `:325-328`). 아니면 index.md 전체를 "Existing Wiki Index"로 넣은 자체 추출 프롬프트로 source 페이지와 entity·concept 페이지를 만들고, 페이지 쓰기는 ingest와 같은 PageFactory에 흘린다(`:109-112`, `:261-295`).
- 대안: 답마다 LLM이 저장 가치를 판정해 묻기(이전), 답을 별도 synthesis 페이지로 저장.
- 이유: 자동 제안을 끈 commit은 "removes unwanted LLM evaluation and SuggestSaveModal prompt"(원치 않는 LLM 평가와 창을 없앤다, commit `d72dffa`)라고 적는다. 중복 판정 결과를 숨기지 않는 이유는 "a silent-success outcome … does not lie to the user"(조용한 성공이 사용자에게 거짓말하지 않게, `QueryView-class.ts:1004-1012`, #398).
- [추정] ingest와 같은 PageFactory를 쓰는 이유는 별칭 대조·병합 규칙을 그대로 재사용하려는 것이다(사례: `conversation-ingest.ts:267`, `:285`가 `createOrUpdate*Page`를 부른다, 두 곳).
- 이력: 이 경로는 추출에 index 전체를 넣고 `sourceSlug`를 넘기지 않아 모델이 쓴 `sources:`에 기댄다(commit `4ae0f39` 메시지). W5("추출은 기존 위키를 보지 않는다")와 W8의 원칙이 아직 닿지 않은 경로다.

## 축별 분석

축 이름과 뜻은 `llm-wiki-implementations/lab/reports/00-comparison.md`의 #설계 축별 스펙트럼을 따른다.

#### 1. 실행 형태

Obsidian 플러그인이다(manifest.json, `isDesktopOnly: false`).

비교 문서의 "데스크톱 앱·IDE" 칸에 가깝지만, 앱을 따로 띄우지 않고 사용자가 이미 쓰는 앱 안에 들어간다(W1).

헤드리스 ingest는 형제 저장소 `karpathywiki-cli`로 뺐다. 이 CLI는 v0.1.0(2026-08-12)이고 마지막 push가 2026-08-21이며, `lint` 명령은 "Phase 1.6 placeholder"다(`gh api repos/green-dalii/obsidian-llm-wiki-cli`, 그 README:3, :32, README.md:392).

레포 안 `tools/dev-instrument/`는 측정 도구지만, 실제 `WikiEngine.ingestSource`를 Obsidian 없이 Node에서 돌린다. 경계는 `obsidian` 모듈 shim(259줄)과 실제 fs 위의 NodeVault(467줄)다(`tools/dev-instrument/README.md:9-13`, `tools/dev-instrument/src/shim.ts:1-6`). 이 shim 크기가 엔진의 Obsidian 의존 면이라서, 서버형으로 옮길 때의 seam을 보여 준다.

#### 2. 규칙의 위치

"쓰기 직전 gate(한 경로)"에 "LLM에게 쓰기 도구 없음"이 겹친 자리다.

LLM은 도구 없이 문자열만 돌려주고, 엔진은 페이지 쓰기 관문 `writeFileWithIntent`를 둔다(`src/wiki/wiki-engine.ts:1993`). ingest 경로와 lint의 중복 병합·죽은 링크·빈 쪽·고아 수리는 guard를 켠 `createOrUpdateFile`을 부른다(`src/wiki/lint/merge-duplicates.ts:183`, `fix-dead-link.ts:331`, `fill-empty-page.ts:108`, `link-orphan.ts:103`).

쓰기마다 guard·notify·create·cancel 층을 기본값 없이 선언한다. "There is no default. A default is how the ambiguity this type exists to remove would come back."(기본값이 있으면 이 타입이 없애려던 모호함이 돌아온다, `src/types.ts:1078-1079`).

새는 곳은 여덟이다.

| 우회 경로 | 근거 |
|---|---|
| lint 준비 단계가 스캔 중 페이지를 직접 고친다 | `src/wiki/lint/phases/preparation.ts:62-115` |
| reviewed 덧붙이기는 재작성 guard 없이 모델 출력 전체를 쓴다 | `src/wiki/page-factory/merge-page.ts:556-557` |
| LLM이 쓴 별칭은 다른 페이지와의 중복 검사를 받지 않는다 | `src/core/frontmatter.ts:859-861`, `src/wiki/wiki-engine.ts:1872-1877` |
| 기본 프롬프트·schema에 옛 지시("full paths from the list above")가 남아 코드 규칙과 어긋난다 | `src/wiki/prompts/generation.ts:22`, `:56`, `src/schema/schema-manager.ts:197` |
| 시작 점검의 `sources:` 정규화가 wiki 페이지를 `vault.process`로 바로 고친다 | `src/core/sources-normalizer.ts:247`, `src/schema/auto-maintain.ts:415-421` |
| lint 별칭 채우기·태그 재지정은 guard 없는 intent로 쓴다 | `src/wiki/lint/fix-runners.ts:152`, `:634`, `src/types.ts:1188-1193` |
| lint 중복 병합은 LLM이 쓴 본문을 H1만 복원해 채택하고 재작성 guard(섹션·소유 문단 복원)를 거치지 않는다 | `src/wiki/lint/merge-duplicates.ts:87-121` |
| 중복 병합의 링크 재지정은 관문을 일부러 피해 wiki 페이지와 사용자 노트를 오프셋 단위로 고친다. "This is also why the write goes through `vault.process` rather than the wiki's own write gate"(사용자 노트를 정규화하지 않으려고 관문을 피한다) | `src/core/link-retarget.ts:28-36`, `:285` |

#### 3. 저장 구조

type 디렉터리(`entities/`·`concepts/`·`sources/`) + `contradictions/` + `schema/` + `index.md`·`log.md`다.

메타데이터는 YAML frontmatter 일곱 키다(`src/core/frontmatter.ts:290-292`).

페이지 밖 파일은 PDF 캐시, `data.json`, opt-in PDF 사본, schema 백업이다(#큰 구조). 비밀값은 vault 밖 OS keychain에 둔다(`src/llm-sdk/provider-secret-store.ts:1-15`). ingest 큐는 메모리에만 있다(`src/core/ingest-queue.ts`).

변경 이력은 사용자의 Git에 맡긴다(README.md:216). 플러그인이 지우는 페이지(중복 병합의 source, 미완 페이지, 빈 stub, Welcome 재생성)는 Obsidian `fileManager.trashFile`로 휴지통에 보낸다(`trashFile(` 4곳: `src/wiki/wiki-engine.ts:2164`, `src/core/incomplete-page-cleaner.ts:74`, `src/schema/auto-maintain.ts:666`, `src/schema/apply-suggestion.ts:88`). 자체 백업은 schema Apply의 `config.md.bak.<iso>` 3개뿐이다(`src/schema/apply-suggestion.ts:55-67`).

#### 4. Ingest

| 하위 선택 | 이 레포 | 근거 |
|---|---|---|
| 사람 참여 | 자율. 확인 지점은 단일 ingest의 중복 재수집 질문 하나 | `src/main.ts:134-145`, #330 §1 |
| 증분 판정 | 본문 해시(배치 안·위키 안) + source 페이지 소유권(`source_file`) | `src/core/source-requirements.ts:68-86`, `src/core/ingest-state.ts:42-48` |
| 실패 복구 | 쓴 뒤 `generation_complete: true` 도장, 시작 점검이 미완 페이지를 휴지통으로. 취소 시 source 페이지를 지워 다음에 다시 수집 | `src/wiki/wiki-engine.ts:355-381`, `:1600-1637`, `src/schema/auto-maintain.ts:355-533` |
| 추출 루프 방어 | 반복 루프 감지(#524, LM Studio 응답 2,493건으로 기준을 맞춤), 수확률 50% 미만이면 batch를 반으로 줄이고 그래도 같으면 멈춤, 잘림·일시 오류 재시도 | `src/core/repetition-loop.ts:1-23`, `src/core/convergence-detector.ts:25-31`, `src/core/truncation-retry.ts`, `src/core/transient-retry.ts` |
| 자동 감시 | `.md`만, 기본 꺼짐, 켜도 기본은 알림만 | `src/schema/auto-maintain.ts:140`, `src/types.ts:1563` |
| 소스당 페이지 | granularity standard 상한 50, 2만 자 미만 문서는 600자당 1개 | `src/core/batch-limits.ts:27-75` |

청크는 없다. 노트 전체를 매 라운드 보내고 1,000줄이 넘으면 경고만 띄운다(`src/wiki/wiki-engine.ts:1058-1070`).

README의 "No chunking"은 검색 쪽 이유("chunking breaks the LLM's ability to reason across your whole knowledge graph", README.md:233)이고, ingest에서 청크를 안 쓰는 이유를 따로 적은 곳은 찾지 못했다.

#### 5. 근거 추적 단위

"페이지 + literal 글자 일치" 칸이다.

페이지 단위는 `sources:` 배열, 문장 단위는 `## Mentions in Source`의 verbatim 인용 2-4개다(`src/wiki/prompts/ingestion.ts:30`).

Mentions 절은 모델이 쓴 것을 지우고 `(quote, source_path)` 키로 합친 목록을 코드가 다시 쓴다(`src/wiki/page-factory/mentions-integration.ts:87-127`).

인용이 원문에 실제 있는지는 ingest가 아니라 lint 스캐너가 원본 노트까지 읽어 대조한다(`src/wiki/lint/scanners.ts:287-388`).

vault 설정이 각주 규칙(`^[Quelle: [[X]]]`)을 정하면 문단 단위 소유도 생긴다. 기본 설정에서는 없다(`src/core/provenance-marker.ts:4-6`).

#### 6. Link

"LLM이 걸고 코드가 해석·검증" 칸이고, 타입은 없다.

생성 프롬프트는 "write [[Name]] … the system resolves every name to its real page after generation"(이름만 쓰면 시스템이 생성 뒤 실제 페이지로 푼다)이라고 지시한다(`src/wiki/prompts/generation.ts:21`). 해석은 전체 페이지의 제목 → 별칭 순이다(`src/core/related-link-corrector.ts:41-90`). 이 변경으로 related 링크 8,800개의 해결률이 90.48%에서 93.08%로 올랐다(commit `57099b7`).

Related 섹션은 모델이 쓰지 않고 코드가 목록에서 렌더한다. 모델이 이름을 "misspelt"(잘못 적은) 사례 때문이다(`src/core/related-sections.ts:4-10`).

관련 목록은 같은 source 안으로 한정돼 그래프가 문서 안에 갇힌다(W14).

frontmatter `sources:`도 그래프 edge가 되어 edge 질량의 약 30%가 "was extracted from here, not is related to"(여기서 추출됨이지 관련됨이 아님)다(#480).

#### 7. Lint

"결정적 + LLM, 보고만"에 "사람이 고른 분류만 적용"이 붙은 자리다(W13).

결정적 스캐너 9종이 사실을 내고, LLM은 중복 검증(이름과 신호만 봄)과 버튼별 수리에 쓴다.

gate로 쓰이지 않는다. 자동 lint에 `autoSmartFix`를 켜면 승인 없이 Fix All이 돈다(`src/wiki/lint/controller.ts:634-637`).

규모 한계가 보고됐다. 11,610쪽 vault에서 "Lint is effectively capped around ~1.2–1.5k pages"(#367).

#### 8. stale·모순 처리

drift는 해시로 감지해 보고만 한다(W12).

모순은 두 gate를 지난 항목만 별도 파일로 남기고 lint가 나열만 한다(W10).

지우지 않는 표시(`superseded_by`, 유효 기간)나 철회 경로는 없다. 병합은 가산적이다.

ingest 경로에서는 사람이 `reviewed: true`를 단 페이지가 덧붙이기만 받는다(`src/wiki/page-factory/create-page.ts:115-121`, `related-page.ts:121-124`). lint 중복 병합은 reviewed를 보지 않고 대상 본문을 LLM으로 다시 쓰며, `reviewed` 값은 그대로 둔다(`src/wiki/lint/merge-duplicates.ts:87-121`, `:159`). lint에서 reviewed를 거르는 곳은 빈 stub 삭제 하나다(`src/wiki/lint/delete-empty-stubs.ts:90`).

#### 9. 사람 개입

ingest는 자율이고 lint·schema는 묶음 승인이다.

| 지점 | 승인 단위 | 근거 |
|---|---|---|
| 무엇이 페이지가 되고 어느 페이지와 같은지 | 없음 | #330 §1 "There is no confirmation point in `analyzeSource` → `resolvePagePath` → `createNewPage`." |
| lint 수리 | 분류 하나 전체(수동), 없음(`autoSmartFix`) | `src/ui/modals/LintReportModal-class.ts:122-141`, `controller.ts:402-404` |
| schema 변경 | 본문 전체 | `src/ui/schema-diff-modal.ts:242-292` |
| 페이지 잠금 | 페이지(`reviewed: true`). ingest 경로에만 걸리고 lint 중복 병합에는 걸리지 않는다 | README.md:324, `src/wiki/lint/merge-duplicates.ts:87-121` |
| 답 되저장 | 대화 하나(Save 버튼) | `QueryView-class.ts:293-300` |

승인 표시를 agent가 만드는 문제는 없다. agent 경로가 없기 때문이다.

#### 10. 동시성·안전

"장치 없음"에 가깝다.

전역 잠금이 없어 수동 ingest·감시 ingest·lint가 겹칠 수 있다. 저자 주석이 "they overlap, because `lint-wiki` is registered without an `isIngesting()` guard"(겹친다, `src/types.ts:1105-1113`)라고 적는다.

한 문서 안 페이지 생성은 기본 3개 병렬이다(`src/types.ts:1579`).

안전 장치는 `generation_complete` 도장과 시작 점검의 미완 페이지 정리, 잘린 재작성 거부, 재작성 guard다.

쓰기 직전 재대조는 링크 재지정 한 곳에만 있다. 오프셋 자리의 글자가 캐시가 말한 것과 다르면 건너뛰고 센다. "a position that no longer holds what the cache promised is counted, never guessed at"(`src/core/link-retarget.ts:270-295`). 페이지 본문 쓰기에는 이런 재대조가 없다.

[추정] 감시를 끄거나 주기 lint를 바꿔도 Obsidian을 다시 열 때까지 이전 동작이 남는다(사례: `stopWatching()`이 이벤트를 해제하지 않음 `src/schema/auto-maintain.ts:98-105`, `clearPeriodicLint()`가 `clearInterval`을 안 부름 `:298-302`, #204 사용자 보고 "they show "off" in the GUI, but the actions continue", 세 곳).

#### 11. Query·검색

| 하위 선택 | 이 레포 | 근거 |
|---|---|---|
| 검색 | 제목·별칭 글자 매칭 → (약하면) LLM 키워드로 전수 매칭 → 링크 그래프 Monte Carlo PPR. 임베딩 없음 | W3, W4 |
| 원문으로 내려가기 | 내려가지 않음. entity·concept은 `## Description` 절만 넣고 Mentions 인용은 빠진다 | `src/wiki/query-engine/pipeline/load-pages.ts:83-102` |
| 되저장 | 요청 시(Save) 재-ingest | W17 |

검색 경로를 칩(`Lex+PPR`/`LLM+PPR`/`Lex++PPR`/`LLM+KB`)으로 보이고 답마다 저장한다(`src/wiki/query-engine/pipeline/select-seeds.ts:12-20`).

찾은 것이 없으면 일반 지식으로 답한다는 안내 문장을 프롬프트에 넣고 `LLM+KB` 칩을 붙인다(#한 바퀴 흐름 > query 8단계). 이유는 "we should NOT pretend to have wiki sources"(위키 출처가 있는 척하지 않는다, `select-seeds.ts:33-38`)다. 끄는 설정은 없다.

저자 측정에서 질의 경로는 5문항 중 3문항에서 졌고 원인은 "the **lexical seed stage**, wrong seeds and not missing paths"(글자 seed 단계의 잘못된 seed)였다(#729, MEMORY.md:674).

#### 12. index·log 관리

index는 매 ingest 끝에 코드가 frontmatter·본문 첫 줄에서 전체 재생성한다(`src/wiki/engine-internals/index-generator.ts:67-131`).

log는 코드가 시간·모델·바이트를 append하고, 기록 패널이 log.md를 파싱해 보여 준다(`src/ui/history-modal/HistoryModal-class.ts:68-84`). log 쓰기는 page guard를 거치지 않는다(`src/types.ts:1196-1220`).

index.md 한 줄 모양이 검색 전체의 입력이다. 그래서 사용자가 직접 만든 페이지는 index 재생성 전까지 검색 후보에 들지 않는다 [추정](사례: 후보의 유일한 출처가 index.md `src/wiki/query-engine/pipeline/read-index.ts:39-48`, index는 엔진만 씀 `index-generator.ts:67-104`, 두 곳).

#### 13. 포맷 표준

"대응 없음"이다.

ROADMAP에 "OKF Bundle export (#285) — typed-edges output standard; community-pending"(OKF 내보내기, 커뮤니티 대기)이 한 줄 있다(ROADMAP.md:399).

#### 14. 규모·비용

9개 비교 구현과 달리 단계별 측정이 많다. ingest 끝에 task 라벨별 LLM 시간을 개발자 콘솔(`console.debug`)에 찍는다(`src/wiki/wiki-engine.ts:1573-1580`). `log.md`에는 시간·모델·바이트만 남는다(`:1545-1550`).

| 장치 | 측정·이유 | 근거 |
|---|---|---|
| 추출 호출 크기를 vault와 떼어 냄 | 목록이 프롬프트의 91%, 398–421초 → 80–110초 | W5, commit `57099b7` |
| 정적 prefix를 prompt cache에 태움 | 추출 prefix 캐시, dedup 호출은 목록을 앞에 두어 KV 캐시 공유 | `src/wiki/source-analyzer.ts:331-341`, `src/wiki/prompts/ingestion.ts:110-115` |
| query 비용이 쪽수와 무관 | Monte Carlo K×L | W4 |
| LLM에 목록 대신 키워드를 받아 로컬 전수 매칭 | 전체 목록 "2137 pageRefs × 50 chars ≈ 30K tokens" | `src/wiki/query-engine/pipeline/query-keywords.ts:5-8` |
| lint 중복 후보 버킷 | "eliminates the O(N²) memory peak that OOMs at ~2000 pages" | `src/constants.ts:570-586` |

[추정] 한 연산 안에 위키 전체를 읽는 단계가 남은 곳은 대화 저장이다(사례: `conversation-ingest.ts:111-112`가 index.md 전체를 넣음, 고아 연결·빈 쪽 채우기는 index 앞 2,000-3,000자만 봄 `src/core/orphan-matcher.ts:29-30`, 세 곳).

#### 15. frosk1 비판 대응

| 비판 | 강도 | 이 레포의 대응 |
|---|---|---|
| 1 오류 누적 | 부분 | 재작성 guard·잘린 출력 거부·모순 2-gate·인용 근거 lint. 병합은 이전본 위에 가산적으로 쌓인다 |
| 2 부분 문맥 | 부분 | 병합에 노트 발췌(4,000자) 또는 주 문서 전체(12,000자). 추출은 기존 위키를 보지 않고, 관련 목록은 같은 문서 안이다 |
| 3 요약 손실 | 부분 | 원문 노트는 건드리지 않고 verbatim 인용을 코드가 누적한다. query는 원문으로 내려가지 않는다. #330 재구축에서 원문이 위키보다 나은 답을 냈다 |
| 4 가짜 SoT | 재정의 | 위키를 원문의 대체가 아닌 "complementary query surface"로 정의했다(W14) |
| 5 환각 병합 | 부분 | "a relationship is not sameness" 판정 기준, 모호하면 별칭을 배우지 않음, 짧은 이름 floor, 모순 2-gate. 중복 lint의 LLM 판정은 이름만 본다 |
| 6 운영 복잡도 | 부분 | 사용자 쪽은 플러그인 설치 하나. 코드는 66k줄이고 설정 항목이 많다 |
| 7 ingest 비용 | 부분 | 호출 크기를 vault와 떼고 prefix cache·해시 skip·granularity를 둔다. 문서당 LLM 호출은 라운드 수 + 후보 수 × 여러 단계다 |

#### 16. 성숙도·차용 가능성

Apache-2.0이라 LICENSE·NOTICE를 지키면 코드째 가져올 수 있다(조건은 #한눈에의 차용 조건 행).

테스트 파일 327개와 PR CI Five-Gate가 있고, 5.5개월 동안 commit 1,224개·태그 89개로 활발하다.

문서와 코드가 어긋난 곳이 여럿이다.

| 문서 주장 | 코드 | 근거 |
|---|---|---|
| "LLM KB fallback — … re-seeds the top-N candidates against the full wiki" | LLM seed 선택은 키워드 0개일 때만, 후보 50개에서 | README.md:242, `select-seeds.ts:149-161` |
| "Below 200K the cascade may drop earlier stages to fit" | 그런 축소 코드가 없다 | README.md:287 |
| "Lint shows counts before running fixes — nothing is charged without your approval." | `autoSmartFix`면 승인 없이 고친다 | README.md:352, `controller.ts:634-637` |
| "The plugin never modifies your source files" | 중복 병합이 사용자 노트의 링크를 고친다 | README.md:370, `src/core/link-retarget.ts:28-35` |
| "Markdown + PDF + images + Office (DOCX/PPTX/XLSX)" | 파일 고르기 창 세 곳이 md·txt·pdf만 보인다 | README.md:65, `src/ui/modals/suggest-modals.ts:12-13` |
| "Do not ship dead code across two releases." | `hub-retirement.ts`(2026-06-30부터), `FixReportModal`, `enableSchema`, `evaluateAndSuggestSave`가 호출처 없이 남았다 | AGENTS.md:347-349, commit `263c9dc` |

떼어 쓰기 좋은 단위는 `src/core/candidate-gate.ts`, `src/core/conflict-resolver.ts`(순수 함수), `src/core/candidate-window.ts`, `src/core/vocabulary.ts`(Obsidian `App` 타입 의존, `:20`), `src/core/paragraph-provenance.ts`, `src/llm-sdk/output-mode-prober.ts`다.

## 엔터프라이즈 llm-wiki에 비추어

사용자 조건은 "작성자마다 같은 대상을 다른 용어로 쓴다"와 "형식 없는 문서가 있다"이고, 목표는 "raw들을 연결할 수 있는 구조, 새로운 데이터와 기존 데이터의 연결고리를 발견할 수 있는 구조"다.

| 조건 | 이 레포가 주는 답 | 빈 곳 |
|---|---|---|
| 다중 작성자 | 주 문서 개념으로 그 주제를 정의한 보고서가 본문을 주도한다(W9). vault schema가 `^[출처: [[X]]]` 각주 규칙을 정한 경우에만, 다른 source가 각주로 소유한 문단이 재작성에서 복원된다. 모순은 두 gate를 지나 별도 파일로 남는다(W10) | 작성자 필드가 없다. provenance는 노트 경로뿐이다(`src/types.ts:20-36`). 각주 규칙은 기본 설정에 없다(`src/core/provenance-marker.ts:3-5`). 주 문서는 노트의 파일 이름·추출 제목·노트 별칭 중 하나가 페이지 이름·별칭과 slug로 같을 때 성립한다(`src/wiki/page-factory/merge-triage.ts:250-271`). 노트 이름이 주제가 아닌 회의록에서는 이 가정이 틀린다(ROADMAP.md:89, #787) |
| 용어 불일치 | slug·별칭 대조 → 좁은 창 LLM 판정 → 판정 뒤 별칭 학습(W6). 질의 때 LLM 키워드를 받아 로컬 전수 매칭. 분류 어휘는 사람 쪽에서만 늘어난다(W8). 언어가 섞이면 이름은 원문 언어로 두고 요약만 위키 언어로 쓴다("NEVER translate names", `src/wiki/source-analyzer.ts:379`). 생성은 별칭을 1개 이상 반드시 쓰게 하고, lint crossLang 신호가 별칭·제목 겹침으로 언어가 다른 중복을 찾는다(`src/wiki/prompts/generation.ts:25-32`, `src/wiki/lint/duplicate-detection.ts:758-778`) | 관계 타입이 없어 "비슷하지만 다른 것"이 별칭으로 뭉개진다. 별칭 충돌 61건 중 손으로 본 12건이 모두 중복이 아니었다(#328 DocTpoint 2026-07-22). 모호함을 기록할 곳이 없다. 같은 대상이 언어별로 따로 페이지가 되었다가 lint 병합으로만 합쳐진다. 생성 프롬프트는 확립된 기술 용어의 번역어를 지어내지 말라고 하고(`generation.ts:29-31`), crossLang 대조는 한글을 지우는 정규화를 써서(`duplicate-detection.ts:98`) 한국어 별칭끼리는 이 신호로 잡히지 않는다 |
| 형식 없는 문서 | 빈 문서·중복 내용 gate(#164 환각 페이지 사고에서 나옴), 위치 × coverage 결정표로 나열·괄호 속 이름 거르기(W7), PDF·OCR을 markdown으로 바꿔 같은 경로로. 도표·스크린샷은 opt-in 이미지 분석으로 텍스트 증거가 된다(#한 바퀴 흐름 > ingest 1.5단계) | 청크가 없어 긴 문서는 라운드만 늘고 1라운드 실패면 문서 전체가 실패한다(`src/wiki/source-analyzer.ts:612-613`). source 요약 페이지는 원문 본문 앞 500자와 추출 결과 JSON을 받고, 원문 전체는 받지 않는다(`src/wiki/wiki-engine.ts:1796-1797`). Office 파일을 넣는 UI 경로가 사실상 없다. 노트 파일 이름을 페이지 후보로 더하는 단계를 끌 수 없어(`src/core/source-lemma.ts:64-80`, #787) 주간보고처럼 파일 이름이 주제가 아닌 문서에서 그 이름의 페이지가 생긴다. 프롬프트 주입 검사는 거절 사유 이름만 예약돼 있다(`src/core/source-requirements.ts:9-16`, `:54`) |
| 권한 | 문서 권한은 없다("no backend, no server, no shared state", README.md:93). LLM 접근 쪽에는 장치가 있다. API 키는 OS keychain에 두고 이관이 실패하면 평문을 지우지 않는다(`src/llm-sdk/provider-secret-store.ts:1-15`, `src/main.ts:218-248`, #182). Bedrock은 SSO·IAM 키 + SigV4이고 임시 자격은 메모리에만 둔다(`src/llm-sdk/bedrock-sso/credential-manager.ts:1-10`, commit `92ec94e`). 사내 gateway용 사용자 지정 헤더(`src/llm-sdk/compat-headers.ts:1-21`, #723), 키 없는 로컬 provider ollama·lmstudio(`src/core/local-no-key-provider.ts:6`) | 문서·폴더별 접근 권한, 승인자, log의 "누가"가 없다. 여러 위키 분리는 범위 밖이다("Multi-vault isolation (#142) — long-term", ROADMAP.md:395). 문서·이미지가 나가는 곳은 경로가 정한다. native는 설정한 provider로, 내장 MinerU는 `mineru.net`으로 가고, 로컬 OCR이나 로컬 provider면 기기 밖으로 나가지 않는다(docs/PDF-OCR-GUIDE.md:12-21) |
| 규모 | 추출 호출 크기가 vault와 무관(W5), Monte Carlo PPR, 중복 후보 버킷 | lint가 1.2-1.5k쪽 부근에서 막혔다(#367). 한글·가나·키릴 제목은 제목 앞 2글자 버킷(`tp:`)에서 빠져서 중복 후보가 링크·피인용 버킷으로만 잡힌다. 한자는 남는다(`src/wiki/lint/duplicate-detection.ts:98`, `:269-280`, `src/constants.ts:578-584`). 전역 잠금이 없어 여러 writer를 받는 서버 구조에 그대로 못 쓴다 |

사용자 목표의 뒤 절반, "새 데이터와 기존 데이터의 연결고리 발견"은 이 레포에서도 열린 문제다.

새 문서와 기존 페이지의 연결은 (1) 이름이 기존 제목·별칭과 같을 때의 `sources:` 덧붙임과 (2) 질의 때 PPR 확산뿐이다(#729 "Nobody has ever asked: *which other pages in this vault relate to this one?*"(이 페이지와 관련된 다른 페이지가 무엇인지 아무도 묻지 않았다)).
단순 co-citation은 측정으로 기각됐다(W14). 임베딩 거절의 이유 중 provider 호환·설치 하나·포지셔닝(W3)은 사내 시스템에는 해당하지 않을 수 있다.

### 가져올 것

| 아이디어 | 맞는 이유 | 코드 위치 |
|---|---|---|
| 추출은 노트만 보고, 연결은 추출 뒤 코드로 | 문서가 수만 건이어도 추출 호출 크기가 vault와 무관하다 | `src/wiki/source-analyzer.ts:301-312`, `src/core/index-search.ts:46-66` |
| 정체 판정 사다리: slug·별칭 대조 → 본문 키워드로 순위 매긴 30개 창 LLM → 판정 뒤 별칭 학습 | 작성자마다 다른 표기가 판정 한 번 뒤로는 LLM 없이 붙는다. 용어 불일치를 점진적으로 흡수한다 | `src/wiki/page-factory/path-resolution.ts:114-361`, `src/core/candidate-window.ts`, `src/core/conflict-resolver.ts` |
| 모호하면 결정하지 않고 별칭도 배우지 않음 + 짧은 라틴 약어는 LLM에 묻지 않음 | 부서마다 같은 두세 글자 약어가 다른 뜻인 사내 문서에서 잘못된 병합이 퍼지는 것을 막는다 | `path-resolution.ts:109-142`, `src/wiki/page-factory/aliases.ts:103-118` |
| "모델은 관찰값을 내고 문턱은 코드 상수" | 형식 없는 보고서에서 "정의/논의/언급만"을 모델이 보고하고, 페이지 생성 문턱은 프롬프트를 건드리지 않고 옮길 수 있어 재측정이 쉽다 | `src/core/candidate-gate.ts:17-21`, `:417-425`, `:612-628` |
| 작성자 링크를 최상위 관련성 신호로 | 사내 보고서에 사람이 건 링크·표기는 모델 판단보다 강하다 | `candidate-gate.ts:546-549` |
| 분류 어휘는 설정·문서 태그·페이지 태그에서만, 프롬프트 목록과 쓰기 검사 목록은 같은 함수 | 모델이 새 분류를 못 만들고, 사람이 고친 태그가 다음 실행에 반영된다 | `src/core/vocabulary.ts:45-59`, `src/wiki/system-prompts.ts:276-303` |
| 코드가 아는 값(경로·해시·인용 출처·날짜)은 모델에게 묻지 않음 | 감사 추적에서 "지어낸 출처"가 생기지 않는다 | `src/wiki/source-analyzer.ts:61-95`, `src/wiki/page-factory/create-page.ts:298-307` |
| 병합 triage + 재작성 guard(섹션·소유 문단·H1 복원) + 잘린 출력 거부 | 여러 보고서가 한 페이지를 계속 고쳐도 다른 보고서가 쓴 내용이 지워지지 않는다. 다만 소유 문단 복원은 각주 규칙을 정한 vault에서만 돌고, lint 중복 병합은 이 guard를 거치지 않는다(#축별 분석 > 2. 규칙의 위치) | `src/wiki/page-factory/merge-page.ts:159-264`, `src/core/paragraph-provenance.ts:241-251` |
| 주 문서 개념 | 같은 주제를 여러 사람이 쓸 때 그 주제를 정의한 보고서가 본문을 주도한다 | `src/wiki/page-factory/merge-triage.ts:250-271`, `note-window.ts:38-105` |
| 모순 2-gate(인용 실존 + "스스로 주장" 확인) + 별도 기록 파일 | 작성자 간 상충을 "남의 입장 전달"과 갈라 오탐을 줄인다 | `src/wiki/page-factory/contradiction-gates.ts:1-240` |
| 인용 근거 스캐너와 source drift 스캐너 | 요약이 원문을 벗어났는지, source 페이지의 원문이 바뀌었는지를 LLM 없이 잡는다. 다만 drift는 `sources/` 페이지만 보고 해시가 페이지당 하나라서, 출처가 여럿인 페이지는 나열된 노트 중 하나만 맞아도 drift가 아니다(`scanners.ts:507-511`, `:521`, `src/core/ingest-state.ts:55-70`). 개정 추적에 쓰려면 출처마다 해시를 따로 두어야 한다 | `src/wiki/lint/scanners.ts:287-388`, `:514-564` |
| 중복 병합 때 vault 전체 링크를 target으로 재지정 + source 이름을 별칭으로 | 두 작성자의 이름을 하나로 합쳐도 기존 링크가 끊기지 않는다 | `src/wiki/lint/merge-duplicates.ts:42-75`, `src/core/link-retarget.ts:1-38` |
| 쓰기 의도를 기본값 없이 선언하는 `WriteIntent` | 쓰기 경로마다 어떤 검사를 거치는지 코드에서 확인할 수 있다 | `src/types.ts:1072-1235` |
| API 키 OS keychain 이관(실패하면 평문 유지, 두 단계 commit) | 사내 배포에서 비밀값이 vault 백업·동기화로 새지 않고, 이관 실패로 키를 잃지도 않는다 | `src/llm-sdk/provider-secret-store.ts:1-15`, `src/main.ts:218-248` |
| 출력 모드 강등 + (baseURL, model) 캐시, task 라벨별 정책·시간 계측 | 사내 게이트웨이·로컬 모델처럼 구조화 출력 지원이 제각각인 환경에서 맞는 모드를 한 번에 찾고, 단계별 비용을 본다 | `src/llm-sdk/output-mode-prober.ts:1-68`, `src/llm-client-wrapper.ts:173-212` |
| 검색 경로 칩을 답마다 저장 | 사람이 "이 답이 위키에서 왔나"를 바로 본다 | `src/wiki/query-engine/pipeline/select-seeds.ts:12-20`, `QueryView-class.ts:656-663` |
| schema 변경 = diff 미리보기 + 전체 적용 + 자동 백업 + 제안 시각 기록 | 팀 표준 용어 규칙을 바꿀 때 검토자가 diff를 보고 승인하는 흐름으로 옮길 수 있다 | `src/schema/apply-suggestion.ts:55-99`, `src/ui/schema-diff-modal.ts` |
| 결정의 근거 측정을 design record·commit·코드 주석에 남기는 운영 | 결정을 뒤집을 때 근거가 따라간다. "Read this before reopening one of these decisions."(MEMORY.md:652-653) | MEMORY.md:648-655(design record), AGENTS.md:78-101(변경마다 성능 회귀 점검), 측정값을 적은 주석 예: `src/core/candidate-gate.ts:17-21`, `src/wiki/page-factory/contradiction-gates.ts:4-11` |

### 피할 것

- 관련 목록을 "같은 문서 안 이름"으로 한정하는 추출 지시. edge 95%가 같은 노트 안에 갇혀 새/기존 연결을 발견하지 못한다(`src/wiki/prompts/ingestion.ts:33`, #729). 사내 목표와 정면으로 부딪힌다.
- `sources:`(추출된 곳)와 관련 링크를 같은 edge로 걷는 그래프. edge 질량의 약 30%가 "여기서 추출됨"이다(#480). edge 종류를 나눠야 한다.
- 관계 타입 없이 정체(별칭)만 두는 모델. "A는 B의 하위 프로젝트" 같은 관계가 별칭으로 뭉개진다(#328).
- 질의 1단계를 글자 매칭에 두는 것. 저자 측정에서 패배 원인이 seed 단계였다(#729). [추정] 한국어는 조사가 붙은 어절이 통째로 토큰이 되어 제목과 맞지 않는다(사례: 한글은 공백 split과 연속 한글 run만 쓰고 형태소를 자르지 않는다 `src/core/ppr-cascade.ts:252-266` 1곳).
- 못 찾으면 일반 지식으로 답하는 기본값. 사내 용도에서는 "위키에 없다"가 더 안전할 수 있고, 이 레포에는 끌 설정이 없다(`select-seeds.ts:189-194`).
- 중복 판정 LLM에 두 이름과 신호만 주는 것. 동음이의(같은 이름, 다른 대상)를 가를 정보가 없다(`dedup-phase.ts:562-564`).
- 원칙과 경로의 간극. "LLM suggests, user decides"를 적어 두고 ingest에 확인 지점이 없다(AGENTS.md:300, #330 §1). 사내 구현은 정체 판정 결과를 사람이 보는 지점(Preview-Confirm, 모호함 기록)을 처음부터 설계해야 한다.
- 굵은 승인 단위. lint는 분류 전체, schema는 본문 전체라 여러 담당자가 항목별로 승인할 수 없다.
- 가산적 재ingest만 있고 철회가 없는 병합. 보고서 개정본에서 빠진 사실을 거둘 길이 없다(W12).
- 전역 잠금 없이 여러 쓰기 경로를 여는 것, 그리고 끄기가 믿을 만하지 않은 자동 모드(`src/schema/auto-maintain.ts:98-105`, `:298-302`).
- 주소를 바꿀 수 없는 외부 OCR 경로. 내장 MinerU 백엔드(기본값은 native, `src/types.ts:1540`)는 원문을 고정 주소 `mineru.net`으로 올리고, 주소를 바꾸는 설정이 없다(`src/constants.ts:132`, ROADMAP.md:404-408, #404). 기본 native도 원문을 설정한 LLM provider로 보낸다(docs/PDF-OCR-GUIDE.md:12-21).
- 측정 원자료를 저장소 밖에 두는 것. 튜닝 스크립트가 "/tmp/ppr-eval/ (outside repo, not committed)"(commit `0a26951`)라 재현이 안 된다.

## 확인하지 못한 것

| 모르는 것 | 무엇을 보면 알 수 있나 |
|---|---|
| 여러 seed의 PPR을 합이 아닌 노드별 최댓값으로 합친 이유 | #198 댓글 전체, commit `560ade0`·`bc187f8` 본문 |
| walkLength 20 튜닝 결론이 코드(50걸음)에 반영되지 않은 이유 | 0a26951 이후 `monte-carlo-ppr.ts` 이력, v1.23.x PATCH 기록, 메인테이너 |
| coverage gate를 항상 켜기로 한 명시적 승인 | `gh api repos/GD4AI/obsidian-llm-wiki/pulls/569/reviews` |
| 결정표 경로에서 `isKnownPage`를 넘기지 않은 것이 의도인지 | PR #607 토론, `src/__tests__/core/candidate-gate.test.ts` |
| docx·이미지를 MinerU로 변환한 뒤 실제로 페이지가 생기는지. 재진입 때 요건 gate가 원본 확장자로 검사한다(`src/wiki/wiki-engine.ts:1032-1033`, `:584-590`, `src/constants.ts:35`) | docx 하나를 실제 vault에 넣거나 `ingestSource(docxFile)` 뒤 생성 경로를 단언하는 테스트 |
| 동시성 3에서 두 후보가 같은 페이지로 풀릴 때 덮어쓰기가 나는지 | 같은 페이지로 풀리는 두 이름을 가진 노트로 재현 |
| reviewed 덧붙이기가 기존 본문을 그대로 복사하는 비율 | reviewed 페이지 재수집 전후 diff |
| lint 그래프 edge가 0개라 hub 스캐너가 아무것도 못 잡는지(노드 키에 `.md`가 붙어 링크 해석과 안 맞는다는 [추정], `phases/preparation.ts:47-52`, `build-graph.ts:64-93`) | 실제 vault에서 lint 후 콘솔 `lintWiki: N hub pages with link density issues`(`programmatic.ts:116`) |
| 여러 파일 창의 "Cancel all"이 돌고 있는 batch를 멈추는지(신호를 읽는 곳이 없다는 [추정], `src/core/ingest-queue.ts:192-201`) | 파일 3개를 큐에 넣고 첫 파일 중 취소한 뒤 log.md |
| `periodicLint: monthly`의 30일 interval이 32비트 상한(2,147,483,647ms)을 넘어 곧바로 반복되는지(`src/schema/auto-maintain.ts:275-279`) | Electron 콘솔에서 `setInterval(f, 2592000000)` |
| 감시 수집이 `.md`만 보는 이유, hourly 주기 lint를 뺀 이유 | `git log -S"endsWith('.md')" -- src/schema/auto-maintain.ts`, 이슈 #219, v1.22.2 릴리스 노트 |
| ingest에서 청크를 쓰지 않는 ingest 쪽 이유 | #175, #330 본문 전체 |
| 측정치(91%, 0/18 vs 9/9, 7/9 오탐, 95% edge 등)의 재현성 | DocTpoint 측정 레포 `llm-wiki-measure`(#519 언급), 미병합 브랜치의 `tools/dev-instrument/src/recall-diagnostic.ts` |
| 미병합 브랜치 `feat/729-reader-recall-2026-10-07`(BM25F·max fusion·damping 0.30·예산 20)가 main에 들어올지, 들어오면 검색 구조가 어떻게 바뀌는지 | 그 브랜치의 `src/core/assembly.ts`, #729·#819 스레드 |
| 헤드리스 CLI `karpathywiki-cli`(v0.1.0, lint는 placeholder, 2026-08-21 이후 push 없음)가 플러그인의 설정·승인 흐름을 얼마나 따라가는지. 서버형 배치에는 이쪽이 가깝다 | 형제 저장소 green-dalii/obsidian-llm-wiki-cli의 `src/` 와 플러그인 `src/` 동기화 workflow |
| README "first-published: 2025-09 (v0.1.0)"(README.md:14)와 저장소 생성일 2026-04-26의 차이 | 이전 저장소 이력, 메인테이너 |
| 관계 타입 설계(#285)와 개정 처리(#220)의 원문 이유 | 두 이슈 본문 전체(이번엔 훑기만 했다) |

## 검증 기록

검증자 셋이 이 보고서를 레포(`f41a39d`)·이슈·블로그와 다시 대조했다. 지적마다 evidence를 `sed`·`grep`·`git show`·`gh issue view`·WebFetch로 직접 다시 확인한 뒤 반영했다.

| 관점 | 대조한 주장 수 | 지적 수 | 반영 | 기각 |
|---|---|---|---|---|
| 코드 주장(줄 번호·동작) | 84 | 23 | 23 | 0 |
| "왜" 주장(인용·[추정]·이력) | 115 | 16 | 16 | 0 |
| 빠진 하위 체계·근거가 얇은 축 | 38 | 14 | 14 | 0 |

세 관점이 같은 곳을 짚은 지적이 세 쌍 있다(관문을 새는 곳의 개수, 명령 개수, MinerU 기본값). 이 쌍은 한 번에 고쳤다.

### 크게 바뀐 것

| 전 | 후 |
|---|---|
| 모든 페이지 쓰기가 `writeFileWithIntent` 관문과 guard를 지나고 도장을 받는다 | ingest·생성·병합 경로만 그렇다. lint 별칭·태그 수리는 guard 없는 intent로, 시작 점검의 `sources:` 정규화와 링크 재지정은 `vault.process`로 바로 쓴다 |
| 관문을 새는 곳은 넷이다 | 여덟이다. 검증자 하나는 일곱(링크 재지정을 넣으면 여덟), 다른 하나는 여섯을 셌다. 두 목록의 합집합을 표에 넣었다 |
| 쓰기 guard 한 줄에 섹션·문단 복원까지 묶음 | 쓰기마다 도는 guard와, 병합·관련 페이지 재작성에서만 도는 재작성 guard로 나눔 |
| `reviewed: true` 페이지는 덧붙이기만 받는다 | ingest 경로에서만 그렇다. lint 중복 병합은 reviewed를 보지 않고 본문을 다시 쓴다 |
| 주 문서는 파일 이름 = 페이지 이름일 때만 성립 | 파일 이름·추출 제목·노트 별칭 중 하나가 페이지 이름·별칭과 slug로 같을 때 성립 |
| 한중일·키릴 제목은 중복 버킷에서 빠진다 | 한글·가나·키릴만 제목 버킷(`tp:`)에서 빠지고, 링크·피인용 버킷에는 남는다. 한자는 남는다 |
| W3 "영구 거절 → opt-in"의 순서와 [추정] | 같은 날 03:49Z 영구 거절 → 07:51Z opt-in 연기로 순서를 바로잡았다. 비용 대비 품질 판단은 작성자가 밝힌 이유("The 3pp gap doesn't justify …")로 옮겼다 |
| W2·W8의 [추정] | W2는 ROADMAP.md:377 "Strongly coupled to cross-type dedup"으로 작성자 이유가 됐다. W8은 floor 원칙(2026-09-16)이 commit(2026-09-12)보다 늦다는 순서에 맞춰 방향을 뒤집었다 |
| 권한·용어 불일치·형식 없는 문서 행 | LLM 접근 장치(keychain·Bedrock SSO·사용자 헤더·로컬 provider), 언어 혼합 장치, 이미지 분석, source-lemma를 끌 수 없음, 주입 검사 미구현을 더했다 |

### 그 밖에 고친 것

- 줄 범위가 틀린 출처를 실제 줄로 바꿨다. 파일 길이를 넘은 곳은 `load-pages.ts`(두 곳), `programmatic.ts`(두 곳), `source-slug.ts`, `candidate-window.ts`, `ppr-cascade.ts`, `llm-client-wrapper.ts`(두 곳)이고, 다른 함수를 가리킨 곳은 `QueryView-class.ts` 진입점과 PDF 캐시 경로다. `pipeline/…` 짧은 경로는 레포 루트 기준 전체 경로로 바꿨다.
- 명령 수를 11개에서 12개로 고쳤다. 병렬 범위에는 관련 페이지 갱신(11단계)을 더했다. 자동 lint는 창 없이 알림만 띄운다는 점을 적었다. index 재생성 시점 넷도 적고, task별 LLM 시간은 `log.md`가 아니라 개발자 콘솔에 찍힌다고 고쳤다.
- 질의 칩을 넷(`Lex++PPR` 포함)으로 고쳤다. seed가 없을 때의 "배너"는 프롬프트 문구이고, 같은 프롬프트의 "not general knowledge" 지시와 엇갈린다고 고쳤다. Save 경로는 `ingestSource`가 아닌 별도 경로로 적었다.
- W1의 중국어 인용은 원문의 두 항목으로 나누고, 빠진 commit `b127638`을 적었다. W2의 #328은 앞뒤 문장을 함께 인용했다. W4에는 주석이 논거를 DocTpoint에게 돌린다는 점과 메인테이너 블로그를 더했다. W6·W9·W12의 출처 귀속(#588 대 PR #589, #216 대 commit, "뺀" → "두지 않은")을 바로잡았다. W14에서는 반론 문장과 약속 문장을 갈랐고, W16에는 PR #589를 더했다.
- 축 1에는 `tools/dev-instrument/`의 shim과 형제 CLI 상태를 적었다. 축 3에는 Git·휴지통·keychain을, 축 4에는 추출 루프 방어를, 축 10에는 링크 재지정의 쓰기 직전 재대조를 더했다. 가져올 것에서는 drift 스캐너의 다중 출처 한계와 측정 운영의 실제 출처를 고치고, keychain 이관 행을 더했다. 한눈에의 차용 조건에는 NOTICE 귀속, THIRD-PARTY-NOTICES, MIT 시기를 더했다.

### 검증자 근거를 고쳐 반영한 것

기각한 지적은 없다. 다만 다섯 곳은 검증자의 근거나 제안 문장이 코드와 달라서, 확인한 내용으로 고쳐 반영했다.

- `LINT_WRITE_INTENT`의 위치는 `src/types.ts:1172-1177`이 아니라 `:1188-1193`이다(`grep -n LINT_WRITE_INTENT src/types.ts`).
- 대화 저장의 중복 판정은 index 전체가 아니라 앞 3,000자와 대화 앞 1,500자를 본다(`src/wiki/conversation-ingest.ts:325-328`). index 전체가 들어가는 곳은 그 뒤 추출 프롬프트다.
- seed가 없을 때 안내 문장은 모델에게 "답 앞뒤에 넣으라"는 지시가 아니라 프롬프트 앞뒤에 놓인 서술문이다(`assemble-context.ts:83-89`, `:124`).
- 생성 프롬프트는 "번역을 포함한 별칭"을 요구하지 않는다. 별칭을 1개 이상 요구하고, 확립된 기술 용어의 번역어는 지어내지 말라고 한다(`generation.ts:25-32`). crossLang 대조도 한글을 지우는 정규화를 쓴다(`duplicate-detection.ts:98`).
- source-lemma는 "무조건" 더해지지 않는다. 요약이 없거나 분류가 정해지지 않거나 상한에 걸리면 빠진다(`source-analyzer.ts:1022-1041`). 끄는 설정이 없다는 점만 맞다. `trashFile(` 호출은 5곳이 아니라 4곳이다.

W16의 #358 목록 가운데 "admission criterion" 항목이 HEAD에 들어왔는지는 `grep -rni admission src` 결과가 비어 확인하지 못했다. 그래서 "확인한 것은 두 가지"로 적었다.

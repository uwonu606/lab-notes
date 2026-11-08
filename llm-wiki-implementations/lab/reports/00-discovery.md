# llm-wiki 분석 세트 제안 — 주신 4개에 새 구현 5개와 OKF 스펙을 더한다

2026-10-10 후보 탐색 결과다. 검색 갈래 5개가 후보 55개를 모았다. gh api로 별 수·최근 push·라이선스를 확인했다. 아래 설명은 README와 메타데이터 기준이고, 코드 분석은 같은 폴더의 repo별 보고서에 있다.

## 1. Karpathy 원본 스펙 요약

원문은 세 곳에 있다. 원문 조사 갈래가 셋 모두 직접 읽었다.
- gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (llm-wiki.md 파일 하나, 2026-04-04, 댓글 1,137개)
- 첫 트윗 "LLM Knowledge Bases": https://x.com/karpathy/status/2039805659525644595 (2026-04-02)
- 후속 트윗: https://x.com/karpathy/status/2040470801506541998 (2026-04-04). 이 트윗은 'idea file' 개념을 소개한다. 코드 대신 아이디어를 공유하고, 받는 쪽 에이전트가 맞춤 구현한다는 뜻이다.

### 3계층
- Raw sources: 바뀌지 않는 원천 자료다. LLM은 읽기만 한다. 이 층이 source of truth다.
- Wiki: LLM이 소유하는 markdown 디렉터리다. 요약, entity, concept, 비교, overview, synthesis 페이지가 들어간다.
- Schema: CLAUDE.md 또는 AGENTS.md다. 구조와 관습, workflow를 정한다. 사람과 LLM이 함께 고쳐 나간다.

### 3연산
- Ingest: 소스는 한 번에 하나씩 넣는다. 사람도 참여한다. 소스 하나가 10~15페이지를 건드린다. 그때마다 index를 갱신하고 log에 한 줄을 더한다.
- Query: index를 먼저 읽고 관련 페이지로 내려간다. 답에는 인용을 붙인다. 좋은 답은 wiki에 새 페이지로 다시 저장한다.
- Lint: 페이지 간 모순을 찾는다. 새 소스에 밀려 낡은 주장(stale claim)도 찾는다. 들어오는 링크가 없는 orphan 페이지, 페이지가 없는 개념, 빠진 상호 참조, 데이터 공백도 점검한다. 다음에 조사할 질문을 제안한다.

### 특수 파일
- index.md: 내용 카탈로그다. 원문은 "~100 sources, 수백 페이지"까지는 임베딩 RAG 없이 충분하다고 적었다.
- log.md: append-only 시간순 기록이다. 각 항목은 `## [YYYY-MM-DD] ingest | Title` 형식으로 시작한다. 그래서 grep으로 파싱할 수 있다.

### 선택 사항
- 규모가 커지면 검색 도구를 붙인다. 원문은 tobi/qmd(BM25 + vector + LLM rerank)를 권한다.
- Obsidian, Web Clipper, Marp, Dataview, git을 함께 쓰라고 권한다.
- 원문은 스스로를 "intentionally abstract"라고 부른다. 디렉터리 구조, schema, 도구는 모두 고르기 나름이다.

### 트윗에만 있는 내용
- 저자의 연구 wiki는 "~100 articles, ~400K words" 규모다.
- 검색은 직접 만든 단순한 검색엔진으로 한다.
- 향후 방향으로 '합성 데이터 + finetuning'을 언급한다.

### 평가 축으로 쓸 비판
gist 댓글에 frosk1(2026-04-06)이 남긴 비판 7가지가 있다. 오류 누적, 부분 문맥, 요약에 따른 정보 손실, 가짜 source of truth, 환각 병합, 운영 복잡도, ingest 비용이다. 여러 구현이 이 비판을 설계 동기로 인용한다. cablate가 대표적이다.

## 2. 사용자가 준 4개의 프로필

수치는 2026-10-10 gh api 기준이다.

| repo | 별 | 마지막 push | 형태 | 한 줄 방식 |
|---|---|---|---|---|
| inkeep/open-knowledge | 4,507 | 2026-10-10 | 데스크톱·웹 markdown IDE (GPL-3.0, 커밋 약 2,589개) | wiki를 research/(임시)와 articles/(확정)로 나누고 consolidate로 승격한다. schema는 폴더별 frontmatter.yml에 흩어 둔다. 고정 index.md 대신 동적 index를 쓰고, 검색은 grep과 backlink 추적이다. |
| Ar9av/obsidian-wiki | 3,546 | 2026-10-10 | skill 39개 + 선택적 Python CLI (커밋 약 358개, 기여자 32명) | .manifest.json으로 소스별 변경분을 추적한다. claim마다 extracted / inferred / ambiguous 출처 태그를 단다. dedup, equilibrium 점검, 세션 기록 ingest, staging 리뷰 큐가 있다. |
| Astro-Han/karpathy-llm-wiki | 2,457 | 2026-07-23 | 단일 skill (커밋 28개, 372KB) | 'Grounding Invariant'가 핵심 규칙이다. wiki의 숫자, 날짜, 인용은 raw 원문에 글자 그대로 있어야 한다. check_evidence.py가 이를 grep으로 검사한다. |
| frankchu91/mindbase-llm-wiki | 129 | 2026-10-10 | MCP 49 tools + 웹 UI + Claude Code plugin (커밋 약 92개, 기여자 1명) | 모든 쓰기를 사람이 승인한다. LLM은 제약된 JSON으로 계획만 내고, 허용된 executor가 실행한다. context.md 하나에 '진실'을 합성하고 snapshot으로 되돌린다. 기본 모델은 로컬 Ollama다. |

### 분석 가치 판단
- open-knowledge: 높음. [확인] 4개 가운데 유일한 편집기형이다. 임시/확정 분리와 분산 schema는 다른 구현에 없는 아이디어다. [추정] 다만 llm-wiki는 이 제품의 starter pack 하나다. 그래서 전체 코드(193MB)가 아니라 두 파일을 중심으로 보면 된다. docs/content/workflows/karpathy-llm-wiki.mdx와 packages/server/assets/skills/packs/knowledge-base/SKILL.md다. GPL이라 코드는 가져오지 말고 아이디어만 참고한다.
- obsidian-wiki: 높음. [확인] skill 중심 구현 가운데 원문에 덧붙인 장치가 가장 많다. docs/architecture.md에 원문 대비 추가분을 정리한 절이 있다. 참고: 자체 벤치마크는 n=2라서 근거가 약하다.
- Astro-Han: 높음. [확인] 최소 구현의 기준선이다. README의 'Design Boundaries' 절이 운영 로그를 근거로 여러 기능을 반대한다. 대상은 source hash, 줄 번호 인용, confidence, vector/graph 검색, MCP, UI다. 그래서 다른 구현들의 반론 자료로 바로 쓸 수 있다. 7월 이후로는 활동이 없다.
- mindbase: 중상. [확인] '엔진 + 안전장치' 설계의 극단이다. 매 쓰기 승인, 에이전트별 도구 허용 목록, context.md 하나에 진실을 모으는 구조가 그 예다. 채택은 적고 관리자는 1명이다. apps/ 아래에 android, ios까지 있어 범위가 넓다. 그래서 packages/core와 ops engine 위주로 보는 편이 낫다.

## 3. 새 후보

### 강력 추천 (6개)
각 후보가 4개와 어느 설계 축에서 다른지를 적는다.

**1. atomicstrata/llm-wiki-compiler** — 2,177★, 2026-10-10 push, TypeScript CLI + MCP + SDK, MIT
- 다른 축: 규칙을 어디에 두는가(프롬프트 ↔ 코드)와 근거 추적 단위다.
- [확인] .llmwiki/profile.json이 schema, 관계, lifecycle, review gate를 선언한다. trust gate는 프롬프트가 아니라 write path에서 강제된다.
- [확인] 문단마다 출처를 "source files and line ranges"로 단다. llmwiki lint가 이 인용을 검증한다.
- [확인] 원문의 'schema 파일 하나에 다 맡긴다'와 정반대 끝에 있다. 위치가 Astro-Han의 반대편이다. Astro-Han은 줄 번호 인용을 명시적으로 반대한다.

**2. langchain-ai/openwiki** — 17,061★, 2026-10-10 push, npm CLI + MCP, MIT
- 다른 축: stale 처리와 증분 갱신, 평가다.
- [확인] 사실(claim)을 버전이 붙은 소스 증거에 묶는다. 소스가 바뀌면 영향받은 claim만 갱신한다.
- [확인] 페이지 단위로 진행을 저장하고 재개한다.
- [확인] WikiBench로 평가했다. 대형 벤더가 평가 수치까지 낸 유일한 사례다.
- 대상이 코드베이스다. 개인 지식과의 차이 자체가 비교 포인트다.

**3. AgriciDaniel/claude-obsidian** — 15,445★, 2026-09-10 push, Claude Code plugin + Python 패키지, MIT
- 다른 축: 동시 쓰기 안전과 승인 방식이다.
- [확인] 병렬 worker는 draft만 낸다. orchestrator 하나가 그 draft를 transaction 하나로 적용한다.
- [확인] 변경은 JSON plan을 미리 보고, approved_plan_sha256로 승인하는 2단계다.
- [확인] source ledger와 claim ledger를 둔다.
- 사용자가 준 obsidian-wiki와 같은 Obsidian + skill 갈래다. [확인] 그 갈래에서 가장 크다. 안전장치도 가장 두껍다. 그래서 같은 갈래 안에서 직접 비교된다.

**4. kfchou/wiki-skills** — 188★, 2026-07-03 push, Claude Code plugin + stdlib Python, MIT
- 다른 축: 결정적 처리와 LLM 처리의 경계, git 활용이다.
- [확인] index 생성, log 렌더링, 모순 검사, 형식 lint를 결정적 스크립트로 한다.
- [확인] pre-commit hook이 commit을 막는다. 대상은 미해결 모순, frontmatter 누락, 깨진 링크, slug 충돌이다.
- [확인] git repo에서는 log.md 대신 git history로 log를 렌더링한다.
- [추정] 별은 적다. 그래도 개인 repo를 git 위에 세울 때 가장 바로 가져다 쓸 수 있는 크기다. 근거는 tests/에 스크립트 4개의 테스트가 있는 작은 구조라는 점 1개다.

**5. nashsu/llm_wiki** — 20,422★, 2026-09-28 push, Tauri 데스크톱 앱(TS + Rust), GPL-3.0
- 다른 축: 앱형과 원문 충실도, 자동 ingest 운영이다.
- [확인] README에 원문 대비 'What We Kept / What We Changed' 표가 있다.
- [확인] 영구 ingest queue가 있어 crash 뒤에 복구된다. raw/sources/ 폴더를 감시해 자동으로 다시 ingest한다.
- [확인] 4-signal 그래프와 Louvain 클러스터링을 쓴다. 선택적으로 LanceDB를 붙인다.
- llm-wiki 전용 앱으로는 가장 크다. open-knowledge(범용 IDE + pack), mindbase(MCP + 웹)와 앱형끼리 비교된다. GPL이라 아이디어만 참고한다.

**6. Google OKF v0.2 SPEC** — GoogleCloudPlatform/knowledge-catalog의 okf/SPEC.md, 9,437★, Apache-2.0
- 다른 축: 저장 포맷 표준이다. 구현이 아니라 스펙이다.
- [확인] §5가 provenance, trust, lifecycle(status, stale_after)를 frontmatter 필드로 표준화한다. §8은 index, §9는 log, §6은 cross-link를 다룬다.
- [확인] 사용자가 준 obsidian-wiki와 open-knowledge가 OKF 호환을 밝힌다. openwiki와 atomicstrata도 OKF 출력을 지원한다.
- 내 repo의 frontmatter 설계를 정할 때 기준점이 된다. 37KB라 읽는 비용도 작다.

### 고려 (축 하나를 더 보고 싶을 때)
| 후보 | 별 / 상태 | 더하는 축 |
|---|---|---|
| lucasastorian/llmwiki | 1,679★, 2026-10-02 | 사람 개입의 반대 극단(야간 자율 합성). mindbase와 같은 MCP + 웹 구조다. |
| cablate/llm-atomic-wiki | 149★, 2026-04-20 이후 정지, 라이선스 없음 | raw → atom(1 claim) → wiki 3단 구조. slug 선점 방식의 병렬 naming. frosk1 비판에 대한 직접 답이다. 코드가 아니라 방법론 문서로 읽을 것. |
| Emmimal/wiki-compiler | 108★ | LLM 없이 링크, backlink, lint를 하는 순수 Python 반론. 'compiler 소유 섹션 / 사람 소유 섹션' 분리. |
| FSoft-AI4Code/CodeWiki | 1,764★ | 증분 갱신을 가장 엄밀하게 한다. 페이지 경계를 결정적 그래프로 정하고, update_record.json을 남긴다. 비용 수치는 커밋 1개 $0.34 대 전체 $21.48이다. 코드 전용이다. |
| xoai/sage-wiki | 623★, Go | 근거가 붙은 typed graph, tiered compile로 규모를 키운다. Obsidian vault 위에 overlay로 얹는다. |
| SamurAIGPT/llm-wiki-agent | 3,614★ | gist 디렉터리를 가장 충실히 옮겼다. [확인] 다만 "코드 없음"은 틀리다. tools/에 선택적 Python이 있다. 2023년에 생성된 repo를 재사용해서 별 수 비교가 어렵다. Astro-Han과 역할이 겹친다. |
| GD4AI/obsidian-llm-wiki | 697★ | 검색 축. 임베딩 없이 Personalized PageRank를 쓴다. 자체 수치는 미검증이다. |
| kytmanov/obsidian-llm-wiki-local → synto | 833★ (유지보수 모드) / 261★ | 사람이 손으로 고친 문서를 보존한다. 거절 이유를 다음 프롬프트에 넣는다. 자동 작업마다 git commit하고 undo한다. 완전 로컬(Ollama)이다. |
| flsteven87/llm-wiki-mcp | 1★, 이틀 만에 정지 | 책임 분리를 가장 또렷하게 보여 준다. 결정적 I/O는 MCP 도구, 판단은 skill, 규칙은 schema 파일이다. seam 참고용이다. |
| rohitg00 'LLM Wiki v2' gist | — | confidence, supersession, 망각, consolidation tier를 다루는 확장 idea file이다. 비교 축 체크리스트로 쓴다. |
| getzep/graphiti | 31,611★ | 덮어쓰지 않고 supersede한다. fact마다 유효 기간(validity window)을 둔다. graph DB라 markdown과는 거리가 있다. |
| garrytan/gbrain | 30,742★ | 대규모 장기 운영 사례다. README는 15만 페이지 이상, cron 66개라고 밝힌다. DB 중심 대조군이다. 범위가 '에이전트 메모리'로 넓어서 경계 사례다. |

### 제외
- 플랫폼이나 인프라라서 뺐다. [확인] 대상은 Tencent/WeKnora(RAG 플랫폼의 한 모드), TencentDB-Agent-Memory(팀 memory hub), kiwifs(BSL 라이선스, 파일시스템 계층), basic-memory(AGPL, Karpathy 이전의 MCP 메모리)다. 개인 repo 레퍼런스로는 너무 무겁거나 층이 다르다.
- 한 번 생성하고 끝나는 계열이라 뺐다. deepwiki-open, STORM(1년 넘게 정지)이다. 누적 유지(compounding)가 없다.
- 메모리나 연구 계열이라 뺐다. claude-mem, letta-code, A-mem, graphrag다. 교훈 하나씩만 고려 표나 비교 축에 반영했다.
- 4개 또는 추천 후보와 겹쳐서 뺐다.
  - nvk/llm-wiki: 리서치 엔진 쪽 확장이다.
  - sdyckjq-lab/llm-wiki-skill: Astro-Han과 같은 갈래이고 라이선스가 없다.
  - eugeniughelbur/obsidian-second-brain: 명령 47개로 핵심 루프가 흐려진다.
  - OpenKB: 7월 이후 정지했다. 검색 축은 GD4AI 쪽이 더 선명하다.
  - swarmvault: 6월 이후 정지했다.
  - synthadoc: AGPL이다.
  - pi-llm-wiki: OKF 채택 사례로 OKF SPEC과 겹친다.
- 정지했거나 범위 밖이라 뺐다.
  - NicholasSpisak/second-brain, ekadetov/llm-wiki: 하루~이틀 만에 정지했다.
  - lewislulu/llm-wiki-skill: 정지했고 라이선스가 없다.
  - shannhk/llm-wikid, Hermes llm-wiki SKILL: 템플릿이나 단일 문서다.
  - Pratiyush/llm-wiki, toolboxmd/karpathy-wiki, ctxr-dev/llm-wiki-memory: 세션·개발 기록 전용이다.
  - skyllwt/AutoSci: 연구 도메인 특화다.
  - crow-hq/llm-wiki-v2: 생성된 지 2주이고 AGPL이다.
  - nex-crm/wuphf: 지금은 다른 프로젝트로 리다이렉트된다.
  - [추정] 연구 노트 용도라면 AutoSci는 다시 볼 만하다. 근거는 연구 수명주기 전체를 다루는 구조 1개다.

## 4. 최종 제안 분석 세트

### 구현 10개 + 스펙 1개
1. Astro-Han/karpathy-llm-wiki: 최소 skill, grep으로 검증하는 grounding
2. Ar9av/obsidian-wiki: 장치가 많은 skill pack
3. AgriciDaniel/claude-obsidian: transaction과 plan 승인 (2와 같은 갈래)
4. kfchou/wiki-skills: 결정적 스크립트와 git hook
5. atomicstrata/llm-wiki-compiler: 코드로 강제하는 compiler, 줄 범위 인용
6. langchain-ai/openwiki: claim 증거, drift, 평가
7. frankchu91/mindbase-llm-wiki: MCP + 웹, 매 쓰기 승인
8. nashsu/llm_wiki: 전용 데스크톱 앱, 자동 ingest queue
9. inkeep/open-knowledge: IDE, 임시/확정 분리, 분산 schema
10. OKF v0.2 SPEC: 포맷 기준 (구현은 아님)

### 함께 읽을 짧은 자료 (분석 대상은 아님)
- Karpathy gist
- frosk1 비판 댓글
- rohitg00 v2 gist
- cablate/llm-atomic-wiki의 METHODOLOGY.md

### 비교 축
1. 실행 형태: prompt-only skill / skill + 결정적 스크립트 / CLI·SDK 엔진 / MCP 서버 + 웹 / 데스크톱 앱·IDE
2. 규칙의 위치: schema 문서(프롬프트) ↔ 코드 강제(write path gate, profile.json, pre-commit)
3. 저장 구조: 디렉터리 분류(topic / entity·concept / 임시·확정), 단일 진실 파일(context.md) 대 다수 페이지, 파생 인덱스와 상태 파일(manifest, state/, ledger)
4. Ingest 방식: 사람 참여 정도, 증분·변경분 추적, queue와 crash 복구, 자동 감시, 멀티포맷
5. 근거 추적 단위: 페이지 → 원문 글자 일치(grounding) → 줄 범위 → claim ledger
6. Link 방식: LLM이 링크를 거는가, 결정적으로 추출하는가. backlink와 그래프를 관리하는 주체는 누구인가
7. Lint: LLM lint와 결정적 lint의 경계. 자동 수정 범위. commit gate 여부
8. stale·모순 처리: 덮어쓰기 / supersede 체인 / drift 감지 / 사람 리뷰
9. 사람 개입: 매 쓰기 승인 / plan 해시 승인 / 리뷰 큐 / 공동 편집 / 야간 자율
10. 동시성·안전: transaction, 원자적 쓰기, snapshot·undo, 도구 허용 목록
11. Query와 검색: index.md만 / 계층 조회 / grep + backlink / hybrid. 답을 wiki에 다시 저장하는가
12. index·log 관리: LLM이 손으로 갱신 / 결정적 재생성 / git log 대체 / 동적 index
13. 포맷 표준: OKF 준수 정도, frontmatter 필드
14. 규모 한계와 비용: 각 repo가 밝힌 운영 규모, ingest 비용
15. frosk1 비판 7가지에 대한 대응
16. 성숙도와 차용 가능성: 별, 활동, 기여자 수, 라이선스(GPL은 open-knowledge와 nashsu)

### 확인하지 못한 것
- [확인] 모든 approach 설명은 README와 메타데이터 기준이다. 코드는 deepwiki-open 하나만 확인했다.
- README의 수치는 하나도 검증하지 않았다. 대상은 성능·규모 주장, 벤치마크, 비용 수치다.
- Farza gist의 본문 확인 여부가 갈래마다 다르다. 원문 갈래는 읽었다고 했고, 검증 갈래는 읽지 않았다고 했다. 그래서 확인되지 않은 것으로 둔다.
- Astro-Han README가 말하는 'LLM Wiki v2'가 무엇인지 확정하지 못했다. 링크가 없다. crow-hq repo는 Astro-Han 글보다 나중에 생겼다. rohitg00 gist일 가능성이 있으나 확인하지 않았다.

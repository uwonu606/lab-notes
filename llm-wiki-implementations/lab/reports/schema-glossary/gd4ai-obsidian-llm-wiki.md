# obsidian-llm-wiki는 종류 목록을 사람이 정하고 별칭 대조로 새 문서를 기존 페이지에 붙이지만, 범용어 허브를 막는 장치는 문서 단위 언급 필터뿐이다

GD4AI/obsidian-llm-wiki는 Karpathy llm-wiki를 Obsidian 플러그인으로 만든 TypeScript 구현이다. 문서 하나를 넣으면 LLM이 entity·concept 후보를 뽑는다. 후보마다 `wiki/entities/`나 `wiki/concepts/`에 페이지가 하나씩 생긴다.

사용자 목표에 주는 답은 세 가지다.

- [확인] "사람이 정한 schema"는 페이지 종류 셋(entity·concept·source)과 하위 종류 목록(entity 7개·concept 7개)까지만 있다. 관계 종류는 없다. 관계는 타입 없는 `related_entities`/`related_concepts` 목록과 `[[wikilink]]`뿐이다.
- [확인] 용어집은 별도 파일이 아니다. 페이지마다 제목과 `aliases:` frontmatter로 흩어져 있다. 추출 프롬프트에는 넣지 않는다. 추출 뒤 slug·별칭 대조와 LLM 판정으로 기존 페이지에 붙인다.
- [확인] 범용어 허브 대책은 문서 하나 안에서 "이름만 나온 후보"를 버리는 gate다. 저장소 전체의 빈도를 보는 stoplist나 허브 억제는 페이지 생성 경로에 없다. 이 gate를 켰을 때 연결이 크게 줄었다는 측정도 저장소 안에 있다(#H 근거 수치).

## 한 바퀴 흐름

문서 하나가 페이지가 되기까지의 순서다. 진입점은 `src/wiki/wiki-engine.ts:944` `ingestSource`다.

| 단계 | 하는 일 | 근거 |
|---|---|---|
| 1. 추출 | 원문 전체와 지침을 프롬프트로 보낸다. 기존 위키 목록은 넣지 않는다. 여러 라운드로 나눠 뽑는다. 2라운드부터는 이미 뽑은 이름과 별칭을 주고 다시 뽑지 말라고 한다. | `source-analyzer.ts:304-312`, `:350-369` |
| 2. 출력 형식 | 후보마다 name·type·aliases·summary·verbatim 인용 2-4개·related 목록·coverage(defined/discussed/named)를 JSON으로 받는다. | `prompts/ingestion.ts:38-71` |
| 3. 종류 보정 | type이 목록 밖이면 대소문자·발음 기호를 접어 맞춘다. 그래도 안 맞으면 LLM에 목록을 주고 다시 고르게 한다. | `source-analyzer.ts:824-829`, `:1105-1144` |
| 4. 기존 이름 대조 | 뽑은 이름의 slug를 기존 페이지 제목·별칭 slug와 맞춰 `related_pages`를 만든다. | `source-analyzer.ts:759-776`, `core/index-search.ts:46-66` |
| 5. 후보 gate | (옵션) 이름이 괄호·나열·짧은 목록 안에만 나온 후보를 버린다. (항상) 모델이 `named`라고 본 후보를 버린다. | `wiki-engine.ts:1114-1235` |
| 6. 관련 목록 정리 | 같은 문서에서 나온 형제 페이지를 최대 3개 잇는다. 태그 값과 같은 이름은 관련 목록에서 뺀다. | `wiki-engine.ts:1260-1285`, `core/related-shaping.ts` |
| 7. source 페이지 | `wiki/sources/<slug>.md`를 쓴다. | `wiki-engine.ts:1345`, `:1743` |
| 8. 경로 결정 | 후보마다 같은 slug 파일 → 같은 종류 slug·별칭 일치 → LLM 판정 순으로 기존 페이지를 찾는다. 찾으면 병합하고 새 이름을 별칭에 더한다. 못 찾으면 새 페이지를 만든다. | `page-factory/path-resolution.ts:114-360` |
| 9. 관련 페이지 갱신 | 4단계에서 맞은 기존 페이지의 `sources:`에 이번 source를 더하고 본문을 LLM으로 고쳐 쓴다. | `page-factory/related-page.ts:57-203` |
| 10. 쓰기 직전 검사 | 목록 밖 태그를 지운다. 페이지 이름과 같은 별칭, 다른 페이지가 이미 가진 별칭을 지운다. | `core/frontmatter.ts:676-688`, `core/slug.ts:159-196` |

## 축별 분석

### A schema

[확인] schema는 사람이 고치는 Markdown 파일 `wiki/schema/config.md` 하나다. 플러그인이 처음에 기본 본문을 써 준다. 본문에는 "This file governs how the LLM builds and maintains your Wiki. Edit it freely."라고 적혀 있다(`src/schema/schema-manager.ts:15`, `:147-149`).

[확인] 이 파일은 `## 제목` 단위로 쪼개져 작업마다 필요한 절만 system prompt에 들어간다. 추출(analyze)은 Wiki Structure·Classification Rules·Naming Conventions·Content Rules를 받는다(`schema-manager.ts:122-138`).

[확인] 하위 종류 목록은 schema 파일이 아니라 설정에 있다. 기본값은 다음과 같다(`src/types.ts:1040-1041`).

| 페이지 종류 | 하위 종류 |
|---|---|
| entity | person, organization, project, product, event, place, other |
| concept | theory, method, field, phenomenon, standard, term, other |

[확인] 사용자는 설정에서 이 목록을 CSV로 바꿀 수 있다(`core/tag-vocab.ts:4-20`). 노트와 위키 페이지에 이미 달린 중첩 태그(`Group/Value`)도 같은 목록에 합쳐진다. 모델이 목록을 늘리는 길은 없다.

원문은 "A term enters the vocabulary through a note's frontmatter, a page's frontmatter, or the settings list — never through the model."(`core/vocabulary.ts:14-18`)

강제는 세 겹이다.

| 겹 | 방식 | 근거 |
|---|---|---|
| 프롬프트 | "you MUST use one of the following allowed values. Do NOT invent new types." | `wiki/system-prompts.ts:286` |
| 구조화 출력 | zod schema를 json_schema로 보낸다. 하지만 `type`은 enum이 아닌 `z.string().optional()`이다. | `llm-sdk/output-schemas.ts:175-188` |
| 추출 직후·쓰기 직전 | 접기 → LLM 재선택 → 그래도 밖이면 쓰기 직전에 태그를 지운다. | `source-analyzer.ts:1105-1144`, `core/frontmatter.ts:676-688` |

[확인] 저자 스스로 프롬프트만으로는 안 지켜진다고 적었다. "about one item in ten arrives with a type the active vocabulary does not admit"(`source-analyzer.ts:824-826`).

[확인] 기본 추출 프롬프트의 안내가 기본 목록과 어긋난다. 안내는 `location`과 `technology`를 쓰라고 한다(`prompts/ingestion.ts:79`, `:91`). 기본 목록에는 `place`가 있고 `technology`는 없다. [추정] 이 어긋남이 목록 밖 type 비율을 키운다 — 사례: 위 두 줄. 실행해서 확인하지는 않았다.

[확인] schema 자체를 바꾸는 제안은 LLM이 만든다. 결과는 `wiki/schema/suggestions.md`에 쌓인다. 머리말은 "Review and decide whether to apply them"이다(`schema-manager.ts:446-507`, `:559`). 적용은 사람 몫이다. [확인] 다만 LLM은 제안과 함께 새 schema 본문 전체를 쓴다. 사람은 diff 창에서 Apply를 눌러 그 본문으로 `config.md`를 통째로 바꾼다. 바꾸기 전 백업을 남긴다(`main-commands/schema-commands.ts:56-82`). 사람이 직접 고치는 것과 LLM 본문을 승인하는 것, 두 길이 있다.

### B 용어집

[확인] 정식 이름은 페이지 제목(파일 이름)이다. 별칭은 frontmatter `aliases:`다. 별도 용어집 파일은 없다. `wiki/index.md`가 모든 페이지를 별칭과 함께 나열하는 색인 노릇을 한다(`engine-internals/index-generator.ts:90`, `:123-127`).

별칭을 쓰는 주체는 넷이다.

| 주체 | 시점 | 근거 |
|---|---|---|
| 추출 LLM | 후보마다 1-2개, 선택 사항 | `prompts/ingestion.ts:27` |
| 페이지 생성 LLM | 1-3개, "REQUIRED" | `prompts/generation.ts:26-32`, `:47` |
| 엔진 | 기존 페이지로 판정된 새 이름을 그 페이지 별칭에 더한다 | `path-resolution.ts:185`, `:349` |
| 사람 | Obsidian에서 frontmatter를 직접 고친다. 원문 노트의 `aliases:`는 source 페이지로 옮겨진다 | `source-analyzer.ts:202-210` |

[확인] README는 "every page ships with at least one alias"라고 쓴다(README.md:145). 코드에서 이 보장은 프롬프트 요구와 Lint의 "missing aliases" 보충이다. 쓰기 직전 검사는 오히려 페이지 이름과 같은 별칭을 지운다(`core/slug.ts:159-196`).

[추정] 그래서 "별칭 하나 이상"은 쓰기 단계에서 보장되지 않는다 — 사례: 생성 프롬프트가 "use the page title itself as the first alias"라고 시키는데(`generation.ts:32`) 그 별칭이 바로 지워지는 대상이다.

[확인] 별칭 중복 검사는 엔진이 별칭을 더할 때만 돈다. 엔진이 기존 페이지로 판정된 새 이름을 별칭에 더할 때, 다른 페이지 제목이나 별칭과 겹치면 버린다. 원문 주석은 "already used on another page — wikilink ambiguity"다(`core/slug.ts:184`, `page-factory/aliases.ts:103-117`). 이 검사를 켜는 호출은 `path-resolution.ts:185`와 `:349` 두 곳뿐이다.

[확인] LLM이 쓴 별칭에는 중복 검사가 없다. 새 페이지 frontmatter 정리와 source 페이지 별칭 정리는 같은 함수를 부르지만 다른 페이지 목록 인자에 `undefined`를 넘긴다(`core/frontmatter.ts:860`, `wiki/wiki-engine.ts:1872-1877`). 그래서 생성 LLM이 다른 페이지가 이미 가진 이름을 별칭으로 써도 그대로 남는다. 저장소 전체에서 별칭이 유일하다는 보장은 없다.

[확인] 용어집은 추출 전에 프롬프트로 주지 않는다. 예전에는 기존 페이지 목록을 프롬프트 앞에 넣었다. 지금은 뺐다. 이유는 "~91% of it on a mature vault, grew without bound"이다. 대신 "Extraction is reading, not linking"이라는 원칙으로 연결을 추출 뒤로 미뤘다(`source-analyzer.ts:304-312`). 정규화는 추출 뒤 slug·별칭 대조로 한다(#D 새/기존 연결).

### C 원문 연결 범위

[확인] 원문 연결 단위는 둘이다.

| 단위 | 어디에 | 무엇을 가리키나 | 근거 |
|---|---|---|---|
| 문서 | entity·concept 페이지의 `sources:` 배열 | `[[sources/<slug>]]` source 페이지 | `related-page.ts:100-105` |
| 문장 | `## Mentions in Source` 절 | 원문 verbatim 인용 2-4문장 + source 링크 | `prompts/ingestion.ts:30`, `schema-manager.ts:219-226` |

[확인] 문서 단위 링크는 "처음 본 곳만"이 아니다. 같은 엔티티가 다른 문서에서 다시 뽑히면 병합 경로나 관련 페이지 갱신 경로가 `sources:`에 새 source를 덧붙인다. 스키마 규칙은 "Sources array: Append new sources, never overwrite"다(`schema-manager.ts:242`). 인용도 페이지에 있던 것과 이번 것을 합친다(`related-page.ts:186-201`).

[확인] 하지만 문서 안의 "모든 등장"은 아니다. 인용은 LLM이 고른 2-4문장이다. 절의 글자 예산은 새 페이지 500자이고, 갱신 때 기존 길이에 500자를 더한다(`core/mentions-formatter.ts:23`, `page-factory/mentions-integration.ts:126`). 청크라는 단위는 없다. "No chunking"이 설계 원칙이다(README.md FAQ).

[확인] 문서 단위로도 빠지는 경우가 있다. 이름이 나왔어도 추출이 안 뽑은 문서는 `sources:`에 안 들어간다. gate가 버린 경우는 페이지가 이미 있느냐에 따라 갈린다. 페이지가 아직 없으면 그 문서는 빠진다. 저자가 이를 알고 받아들였다. "a thing that fails here in source A and passes in source B gets its page with B, and A is not among its sources."(`core/candidate-gate.ts:50-52`)

[확인] 페이지가 이미 있으면 gate가 버린 문서도 `sources:`에 들어간다. 기존 페이지 대조(`related_pages`)는 gate 전에 추출된 이름 전체로 한다(`source-analyzer.ts:763-776`). gate는 `entities`·`concepts`만 줄이고 `related_pages`는 건드리지 않는다(`wiki-engine.ts:1176-1235`, `:1461`). 관련 페이지 갱신은 이번 문서에 그 이름의 추출 항목이 없으면 본문은 두고 `sources:`만 더한다(`related-page.ts:100-114`).

[추정] 사용자의 직전 실험과 비교하면 이 구현은 "이름이 나온 모든 문서"와 "처음 본 곳만" 사이에 있다. 추출과 gate를 통과한 문서마다 링크를 건다. 이름이 나왔지만 뽑히지 않은 문서에는 안 건다 — 사례: 위 두 인용.

### D 새/기존 연결

[확인] 새 후보를 기존 페이지에 잇는 절차는 `resolvePagePath`다(`page-factory/path-resolution.ts:114-360`).

1. 같은 종류 폴더에 같은 slug 파일이 있으면 그 페이지다(`:145-154`).
2. `ConflictResolver`가 같은 종류 페이지의 제목 slug와 별칭 slug 집합에서 찾는다(`core/conflict-resolver.ts:67-72`). 한 페이지만 맞으면 병합한다. 새 이름을 그 페이지 별칭에 더한다(`path-resolution.ts:179-187`).
3. 두 페이지 이상이 맞으면 결정하지 않고 LLM 판정으로 넘긴다(`:199-209`). 반대 폴더(entity↔concept)에 같은 이름이 있어도 LLM 판정으로 넘긴다(`:164-197`).
4. 아무 페이지도 안 맞고 이름이 3글자 미만 로마자면 LLM을 부르지 않고 새로 만든다(`:223-232`, `constants.ts:922`).
5. LLM 판정. 양쪽 폴더에서 후보 30개를 뽑는다. 순위는 제목 3점·별칭 2점·본문 키워드 1점이다. 페이지 절반 넘게 나오는 키워드는 버린다(`core/candidate-window.ts:20-27`, `constants.ts:241`, `:260`). 후보 목록과 새 이름·summary 300자를 주고 "same referent"인지 묻는다(`prompts/ingestion.ts:116-140`).
6. 맞다고 하면 그 페이지로 병합하고 새 이름을 별칭에 더한다(`path-resolution.ts:335-350`). 아니면 새 페이지를 만든다(`:356-360`). 예외가 하나 있다. 3번의 "같은 종류 두 페이지 이상" 경우에 LLM이 아니라고 하거나 답을 못 읽으면, 새 페이지 대신 순위 1위 후보로 병합한다(`:205-207`, `:355-359` 주석 "it resolves to the top-ranked candidate instead"). 이때는 별칭을 더하지 않는다(`:133-142`).

[확인] 판정 기준은 엄격하다. "Never match a page about a related, broader, narrower, or component thing — a relationship is not sameness."(`prompts/ingestion.ts:132`) 임베딩은 쓰지 않는다. README는 "We deliberately rejected the embedding path"라고 쓴다.

[확인] 정체 판정과 별도로 "관련" 연결도 있다. 뽑은 이름이 기존 페이지 제목·별칭과 slug로 맞으면 그 페이지를 `related_pages`로 잡는다(`source-analyzer.ts:759-776`). 그 페이지는 이번 source를 `sources:`에 받는다(`related-page.ts:100-114`).

[확인] 사람이 나중에 고치는 경로도 있다. Lint가 제목·별칭 bigram 유사도와 교차 언어 별칭 일치로 중복 후보를 낸다(`wiki/lint/duplicate-detection.ts:741-777`). 병합은 사용자가 Lint 창에서 고른다.

### E 새 용어

[확인] 처리는 대상마다 다르다.

| 대상 | 목록 밖일 때 | 근거 |
|---|---|---|
| 엔티티·개념 이름 | 새 페이지를 자동으로 만든다. 승인 대기열은 없다. | `path-resolution.ts:356-360` |
| 하위 종류(type) | 접기 → LLM 재선택 → 그래도 밖이면 쓰기 직전에 태그를 지운다. | `source-analyzer.ts:1105-1144`, `frontmatter.ts:676-688` |
| 도메인 태그(`Group/Value`) | 버리고 로그만 남긴다. "a model-proposed tag is a candidate, not a fact" | `wiki-engine.ts:1237-1248`, `core/domain-axis.ts:16-18` |
| schema 자체 | LLM 제안을 `suggestions.md`에 쌓는다. 사람이 적용한다. | `schema-manager.ts:446-507` |

[확인] 이름에는 옵션이 하나 더 있다. `gateDissentStubs`를 켜면 두 gate가 엇갈린 후보는 LLM 호출 없이 summary로 stub 페이지가 된다(`types.ts:569-579`, `candidate-gate.ts:612-628`). 기본값은 꺼짐이다. 위치 gate(`skipMentionOnlyCandidates`)도 켜져 있어야 동작한다. 원문은 "Takes effect only with `skipMentionOnlyCandidates` on"(`types.ts:573-574`).

### F 범용어 허브

[확인] 장치는 넷이다. 그중 페이지 생성 경로에서 도는 것은 둘이다.

| 장치 | 무엇을 보나 | 생성 경로에서 도나 | 근거 |
|---|---|---|---|
| 위치 gate (`skipMentionOnlyCandidates`) | 이 문서에서 이름이 본문 문장에 나오나, 괄호·나열·짧은 목록에만 나오나 | 옵션, 기본 꺼짐 | `candidate-gate.ts:384-415`, `wiki-engine.ts:1176-1206` |
| coverage 기준 | 모델이 보고한 `named`(예시·나열·지나가는 언급)면 버린다 | 항상 | `candidate-gate.ts:426`, `wiki-engine.ts:1208-1235` |
| 태그 값 제거 | 관련 목록의 이름이 태그 어휘에 있으면 페이지 링크 대신 뺀다 | 항상, 관련 목록에만 | `core/related-shaping.ts:93-97` |
| 허브 Related 링크 lint | in-degree 상위 페이지의 `## Related` 링크끼리 PPR로 겹치면 strip/review를 권한다 | Lint 보고만 | `core/hub-link-distinctiveness.ts`, `wiki/lint/phases/programmatic.ts:113` |

[확인] 위치 gate의 규칙은 코드 상수다. 쉼표 2개 이상 문장에서 이름이 든 조각이 4단어 이하면 나열이다. 6단어 이하 목록 항목도 나열이다(`candidate-gate.ts:58-66`). 저자가 링크한 이름, 제목 줄의 이름, 괄호가 이름 자체를 풀이하는 경우는 본문으로 친다(`:395-404`). 한국어 프로필은 조사 목록으로 있다. 다만 "estimated"다(`:146-151`).

기본값이 꺼진 이유는 세 가지다.

- [확인] 쓰는 페이지 수가 바뀌는 동작 변경이라서다. "it changes which pages an ingest writes, so it is the user's choice, not an upgrade's."(`candidate-gate.ts:25-26`)
- [확인] 측정한 언어가 독일어 하나다. 나머지는 추정, zh/ja는 미측정이다(`candidate-gate.ts:105-111`, CHANGELOG.md:149).
- [확인] 용어집형 노트에는 맞지 않는다. 설정 설명은 "Leave off for glossary-style vaults or bullet-point notes where every named term should become a page."(`texts/en.ts:805`)

[확인] 이 장치들은 사용자 실험의 허브 문제를 직접 다루지 않는다. 위치 gate와 coverage 기준은 "이 문서가 그 이름을 다루는가"만 본다. KG·LLM처럼 여러 문서의 본문에서 실제로 논의되는 범용어는 둘 다 통과한다. 저장소 전체 빈도로 링크를 깎는 장치는 페이지 생성 경로에 없다. 빈도 상한(`CANDIDATE_WINDOW_DF_CAP = 0.5`)은 있지만 중복 판정 후보 순위의 키워드에만 쓴다(`constants.ts:254-260`).

[확인] 허브 해제 판정 모듈 `core/hub-retirement.ts`(군집 계수로 허브 지위를 거둠)는 src 안에 호출처가 없다. 테스트만 있다.

[추정] 허브 Related 링크 lint는 기본 생성 페이지에서 걸리지 않는다 — 사례: 이 lint는 제목이 정확히 `related`·`see also`·`related pages`인 절만 읽는다(`hub-link-distinctiveness.ts:137`). 기본 페이지 절 이름은 `Related Entities`·`Related Concepts`다(`wiki/system-prompts.ts:20`). 실행해서 확인하지는 않았다.

[추정] 사용자 시스템에 옮길 만한 생각은 태그 값 제거다. 범용어를 페이지(링크 노드)가 아닌 태그 축으로 돌리는 방식이다 — 사례: `Thema/Therapie`나 맨 `Therapie`가 관련 목록에서 빠진다(`related-shaping.ts:93-97`). 다만 이 구현은 관련 목록에서만 빼고, 범용어 페이지가 생기는 것 자체는 막지 않는다.

### G 엔티티·이벤트

[확인] 이벤트는 entity의 하위 종류 `event` 하나다. 추출 안내는 "event/conference/milestone/historical occurrence"다(`prompts/ingestion.ts:78`). 일반 엔티티와 같은 필드(name·type·aliases·summary·인용·related)만 가진다(`types.ts:128-148`).

[확인] 시간축은 없다. 날짜·기간·참여자 필드가 없다. `timeline`·`temporal`·`occurred`를 src에서 찾았지만 추출·페이지 경로에는 없었다. `created:`·`updated:`는 페이지 작성 날짜이고 사건 날짜가 아니다(`schema-manager.ts:213-217`).

### H 근거 수치

[확인] schema·별칭 설계 전체의 효과를 잰 실험은 없다. 개별 장치의 측정이 코드 주석과 CHANGELOG에 흩어져 있다. 대부분 저자들의 독일어 vault에서 쟀다.

| 대상 | 수치 | 근거 |
|---|---|---|
| 위치 gate 필요성 | 독일어 노트 10개·후보 115개 중 원문 본문에 이름이 아예 없음 9.6%, 괄호·나열에만 19.1%, 본문 71.3%. 앞의 둘을 합친 28.7%를 CHANGELOG는 "named but never treated by their source"라고 부른다 | `candidate-gate.ts:11-15`, CHANGELOG.md:149 |
| 위치 gate 프롬프트 대안 | 같은 질문을 프롬프트 세 가지로 물으면 걸러지는 비율이 0.9%~13.9%로 갈렸다 | `candidate-gate.ts:17-21` |
| 위치 gate의 연결 손실 | 켰더니 나가는 링크 없는 페이지가 2612개 중 782개(켜기 전 2386개 중 95개). 기존 페이지 이름은 링크를 남기도록 고쳤다 | CHANGELOG.md:114 |
| 관련 목록 정리 | 413노트 vault에서 죽은 관련 항목 24% → 1%, 나가는 링크 없는 페이지 103 → 0 | CHANGELOG.md:97 |
| 중복 판정 후보 창 | 전체 목록을 주면 동의어 대상을 18번 중 0번 찾았다. 대상이 든 30개 창이면 9번 중 9번 찾았다. 본문 키워드 순위로 대상이 창에 드는 비율 25% → 42% | `candidate-window.ts:5-18` |
| 반대 폴더 쌍둥이 | 83노트 한 번에 같은 대상이 entity·concept 양쪽에 생긴 쌍 18개 | `path-resolution.ts:13-17` |
| 어휘 불일치 | 903페이지 재구축에서 69페이지(7.6%)가 빈 `tags:` | `core/vocabulary.ts:3-12` |
| 검색 | PPR recall@5 27.1% vs kNN 24.1%. 53페이지 합성 fixture | README.md:251, `scripts/eval-recall.ts:7-9` |

[추정] 사용자 실험과 같은 모양의 trade-off가 이 저장소에도 기록돼 있다 — 사례: 후보를 걸러 정밀도를 올리자 연결이 줄었다(CHANGELOG.md:114). 사용자 실험은 반대 방향으로 연결을 늘리자 정밀도가 떨어졌다.

## 가져올 것

- [확인] **용어 출처를 사람 쪽으로 닫는 규칙.** 어휘는 설정·노트 태그·페이지 태그로만 들어온다. 모델은 못 넣는다(`core/vocabulary.ts`). 프롬프트에 주는 목록과 쓰기 직전 검사 목록을 같은 함수에서 만든다.
- [확인] **쓰기 직전 검사 + 짧은 재선택 호출.** 목록 밖 type은 접기 → 목록을 준 1회 LLM 호출 → 그래도 밖이면 버림(`source-analyzer.ts:1105-1195`). 구조화 출력에 enum을 걸지 않고도 목록을 지킨다.
- [확인] **별칭 중복 차단 + 중복 시 LLM 판정.** 엔진이 별칭을 더할 때 다른 페이지가 가진 이름은 넣지 않는다(`core/slug.ts:184`, `path-resolution.ts:185`, `:349`). 두 페이지가 같은 이름을 가지면 결정론 병합을 멈추고 LLM 판정으로 넘긴다(`path-resolution.ts:199-209`). 사용자 실험의 "용어집이 한 이름으로 모아 준 범용어" 문제를 반대쪽에서 막는 장치다. 다만 이 구현은 LLM이 쓴 별칭에 같은 검사를 걸지 않는다(#B 용어집). 옮길 때는 모든 별칭 쓰기 경로에 걸어야 전역 유일이 된다.
- [확인] **정체 판정 후 별칭 학습.** 기존 페이지로 판정된 새 표기를 그 페이지 별칭에 더한다(`path-resolution.ts:349`). 다음 문서부터는 LLM 없이 slug 대조로 붙는다.
- [확인] **위치 gate와 coverage를 두 축으로 보는 결정표.** 본문+다룸이면 페이지, 한쪽만이면 stub, 둘 다 아니면 버림(`candidate-gate.ts:612-628`). 사용자 시스템에서는 "이 문서가 그 용어를 다루는가"를 링크 가중치로 바꿔 쓸 수 있다. [추정] 범용어 허브는 이것만으로 안 풀린다 — 사례: #F 범용어 허브에서 본 대로 KG·LLM은 본문에서도 논의된다.
- [추정] **범용어를 태그 축으로 돌리기.** `related-shaping.ts`처럼 범용어를 링크 노드에서 빼서 `Group/Value` 태그로 둔다. 근거는 이 저장소의 관련 목록 처리 하나뿐이다. [확인] 이 구현에서는 맨 이름(`Therapie`)이 기존 페이지나 같은 문서의 생존 후보로 풀리면 링크가 남는다. 태그로 빠지는 것은 아무 페이지로도 안 풀릴 때뿐이다(`related-shaping.ts:99-110`). 범용어 페이지가 이미 있으면 막지 못한다. 사용자 데이터에서 효과는 재 봐야 안다.

라이선스는 Apache-2.0이다. 코드를 옮겨 쓰면 LICENSE·NOTICE를 함께 두고 바꾼 파일에 변경 사실을 적어야 한다.

## 출처

- 저장소: https://github.com/GD4AI/obsidian-llm-wiki
- 읽은 commit: `f41a39d06e89558d94c5e298c4cc9669d64e2854` (2026-10-09)
- 로컬 사본: `/home/ssafy/workspace/alt/lab-notes/llm-wiki-implementations/lab/repos/GD4AI_obsidian-llm-wiki`
- 라이선스: Apache-2.0 (LICENSE, NOTICE, THIRD-PARTY-NOTICES.md)
- 코드는 실행하지 않았다. 위 근거는 모두 파일을 읽은 것이다.

## 검증 기록

반박 검증 에이전트가 같은 commit(`f41a39d`)의 로컬 사본을 다시 읽었다. 코드는 실행하지 않았다.

다시 열어 맞는 것을 확인한 인용이다.

- A: `schema-manager.ts:15`(파일 이름), `:149`("Edit it freely"), `:122-138`(작업별 절), `:242`, `:559`. `types.ts:1040-1041`(기본 목록). `system-prompts.ts:286`("MUST use one of"). `output-schemas.ts:175-188`(`type: z.string().optional()`). `source-analyzer.ts:824-826`, `:1105-1144`. `core/vocabulary.ts:14-18`. `core/tag-vocab.ts:4-20`. `prompts/ingestion.ts:79`, `:91`.
- schema·용어집이 사람 쪽이냐는 의심: 기본 schema 본문과 기본 type 목록은 코드가 써 준다. 사람은 이를 고치거나 설정에서 바꿀 수 있다. 어휘에 새 값이 들어오는 길은 설정·노트 태그·페이지 태그뿐이다. 모델이 낸 type·domain은 접기·재선택 뒤에도 밖이면 버린다. 사람이 정한다는 주장은 부풀리지 않았다.
- B·D: `prompts/ingestion.ts:27`, `:132`. `generation.ts:25-32`, `:47`. `path-resolution.ts:114-360` 단계 순서. `candidate-window.ts:5-27`(0/18, 9/9, 25%→42%, 제목 3·별칭 2·키워드 1). `constants.ts:241`(K=30), `:260`(DF 0.5), `:922`(3글자). README.md:255("deliberately rejected the embedding path").
- C: `prompts/ingestion.ts:30`(2-4 verbatim), `mentions-formatter.ts:23`(500자), `mentions-integration.ts:126`, `candidate-gate.ts:50-52`.
- F·G·H: `candidate-gate.ts:11-26`, `:105-111`, `:384-426`, `:612-628`. `texts/en.ts:805`. `wiki-engine.ts:1176-1248`. `hub-link-distinctiveness.ts:137`. `hub-retirement.ts`는 `__tests__` 밖 호출처가 없다. `prompts/ingestion.ts:78`. `types.ts:128-148`. `schema-manager.ts:213-217`. CHANGELOG.md:97, :114, :149. README.md:251. `scripts/eval-recall.ts:7`(53-page synthetic fixture).

고친 것이다.

| 위치 | 원래 주장 | 고친 내용 | 근거 |
|---|---|---|---|
| #B 용어집, #가져올 것 | 별칭은 저장소 전체에서 한 페이지만 가진다 | 중복 검사는 엔진이 별칭을 더할 때만 돈다. LLM이 쓴 별칭은 검사하지 않는다 | `frontmatter.ts:860`, `wiki-engine.ts:1872-1877`이 다른 페이지 목록에 `undefined`를 넘긴다. 목록을 넘기는 곳은 `path-resolution.ts:185`, `:349`뿐이다 |
| #C 원문 연결 범위 | gate가 버린 문서는 `sources:`에 안 들어간다 | 페이지가 아직 없을 때만 그렇다. 페이지가 있으면 related page 경로로 `sources:`에 들어간다 | `source-analyzer.ts:763-776`가 gate 전에 대조한다. `related-page.ts:100-114`가 추출 항목 없이도 `sources:`를 더한다 |
| #D 새/기존 연결 | LLM이 아니라고 하면 새 페이지를 만든다 | 같은 종류 두 페이지 이상이 맞은 경우는 순위 1위 후보로 병합한다 | `path-resolution.ts:205-207`, `:355-359` |
| #E 새 용어 | `gateDissentStubs`를 켜면 stub이 된다 | 위치 gate도 켜져 있어야 한다 | `types.ts:573-574` |
| #H 근거 수치 | 28.7%가 이름만 나온 후보 | 9.6%는 본문에 이름이 아예 없고 19.1%만 괄호·나열에 나온다 | `candidate-gate.ts:11-12`, CHANGELOG.md:149 |
| #A schema | 적용은 사람 몫 | 사람이 LLM이 쓴 새 본문 전체를 Apply로 승인하는 길도 있다고 덧붙였다 | `schema-commands.ts:56-82` |
| #가져올 것 | 범용어를 태그 축으로 | 맨 이름은 기존 페이지로 풀리면 링크가 남는다고 덧붙였다 | `related-shaping.ts:99-110` |


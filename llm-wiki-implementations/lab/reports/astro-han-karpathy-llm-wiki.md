# Astro-Han/karpathy-llm-wiki — 규칙은 프롬프트에 두고, 숫자·날짜·인용만 원문 grep으로 검사한다

## 한눈에

| 항목 | 값 |
|---|---|
| URL | https://github.com/Astro-Han/karpathy-llm-wiki |
| clone commit | `eafcc77` (2026-07-24 +0800, "fix: align log inventory and examples") |
| 별·fork | 2,457 · 288 (2026-10-10 gh api) |
| 최근 push | 2026-07-23 |
| 라이선스 | MIT (`LICENSE:1`) |
| 커밋 수 | 28개 (gh api 페이지 수로 셈) |
| 형태 | Agent Skills 규격 skill 하나 + 보고 전용 Python 스크립트 하나 |
| 코드 규모 | `SKILL.md` 233줄, `scripts/check_evidence.py` 431줄, `tests/test_check_evidence.py` 765줄(test 함수 52개), 템플릿 4개(합 75줄) |

[확인] 커밋 28개 가운데 14개가 2026-07-23 하루에 몰려 있다. 그날 Grounding Invariant, triage, Status block, Design Boundaries가 모두 들어왔다. 나머지 14개는 2026-04-05~04-13의 초기 skill과 README·SEO 작업이다.

[확인] 이 보고서는 저장소 코드를 실행하지 않았다. 테스트 통과 여부는 미검증이다.

## 한 바퀴 흐름

Ingest:

1. 에이전트가 `SKILL.md:3` description의 trigger 문구("add to wiki" 등)로 skill을 고른다.
2. 첫 ingest라면 `raw/`, `wiki/`, `wiki/index.md`, `wiki/log.md`를 없는 것만 만든다 (`SKILL.md:28-37`).
3. Fetch 단계다. 에이전트가 가진 웹·파일 도구로 원문을 가져온다. 도구가 없으면 사람에게 붙여 넣기를 청한다 (`SKILL.md:51`).
4. 원문을 `raw/<topic>/YYYY-MM-DD-slug.md`로 저장한다. 머리에 Source·Collected·Published를 blockquote로 단다 (`SKILL.md:55-62`, `references/raw-template.md:1-7`).
5. Triage 단계다. wiki 전체를 핵심 entity와 동의어로 검색한다. 그 뒤 New / Update / Disputed / No material 가운데 처분을 선언한다 (`SKILL.md:64-73`).
6. No material이면 raw는 남기고 log에만 적고 멈춘다 (`SKILL.md:71`, `SKILL.md:113-118`).
7. Compile 단계다. 같은 논지면 기존 article에 합치고, 새 개념이면 새 article을 만든다 (`SKILL.md:77-83`).
8. 쓰기 전에 숫자·날짜·인용을 raw에서 grep으로 찾는다. 찾은 표기 그대로 쓴다 (`SKILL.md:85`). 이것이 Grounding Invariant의 "establish" 쪽이다 (`SKILL.md:41`).
9. Cascade 단계다. index에 기대지 말고 wiki 전체를 검색해 영향받는 article을 고친다. 밀려난 주장은 지우지 않고 Status block을 단다 (`SKILL.md:92-98`).
10. `wiki/index.md` 행을 고치고 `wiki/log.md`에 항목을 덧붙인다 (`SKILL.md:100-120`).

Query:

1. `wiki/index.md`를 읽고, 이어서 wiki/를 핵심어와 동의어로 full-text 검색한다 (`SKILL.md:141`).
2. 찾은 article을 읽고 답한다. wiki article 경로로 인용한다 (`SKILL.md:142-143`).
3. 파일은 쓰지 않는다 (`SKILL.md:144`). 사람이 명시적으로 청할 때만 archive 페이지를 새로 만들고 index·log를 고친다 (`SKILL.md:146-160`).

Lint:

1. Safe Fixes 단계다. 에이전트가 index와 실제 파일, 내부 링크, Raw 링크, See Also를 비교해 고친다 (`SKILL.md:168-191`). 이 단계에는 스크립트가 없다.
2. Mechanical Reports 단계다. 에이전트가 `python3 <skill-dir>/scripts/check_evidence.py <project-root>`를 돌린다 (`SKILL.md:195`).
3. 스크립트의 `main()`이 article마다 `check_article()`을 부른다 (`scripts/check_evidence.py:358-385`, `:290-315`).
4. `check_article()`은 header의 Raw 링크를 모은다 (`raw_links_of`, `:260-267`). 링크가 raw/ 밖이면 evidence error다 (`:303-304`).
5. `extract_candidates()`가 article에서 숫자·날짜·인용 후보를 뽑는다 (`:195-257`). `contains()`가 각 후보를 연결된 raw 본문에서 찾는다 (`:270-279`).
6. `unreferenced_raws()`가 어떤 article도 가리키지 않는 raw를 모은다. log의 no-material heading에 적힌 raw는 뺀다 (`:324-355`).
7. 스크립트는 보고서만 출력하고 exit 0으로 끝난다 (`:393-427`).
8. Judgment Reports 단계다. 에이전트가 모순, 낡은 주장, orphan 등을 보고만 한다 (`SKILL.md:203-215`).
9. log에 `lint | N issues found, M auto-fixed`를 덧붙인다 (`SKILL.md:217-223`).

## 축별 분석

#### 1. 실행 형태

skill + 결정적 스크립트 하나다.

[확인] 실행 주체는 사용자의 coding agent다. 저장소는 `SKILL.md`, 템플릿, `check_evidence.py`만 제공한다 (`README.md:98-108`).

[확인] 스크립트는 lint의 한 단계에서만 쓰인다 (`SKILL.md:195`). ingest·query는 순수 프롬프트다.

[확인] README는 MCP 서버·UI·hook을 범위 밖이라고 적었다 (`README.md:134`, `README.md:138`).

#### 2. 규칙의 위치

거의 모든 규칙이 `SKILL.md` 프롬프트에 있다. 코드가 강제하는 것은 없고, 코드가 보고하는 것만 있다.

- [확인] raw 불변 규칙은 문장 하나뿐이다 (`SKILL.md:18`). hook·권한·체크섬은 없다.
- [확인] 스크립트가 보고하는 규칙은 셋이다. Raw field 존재 (`scripts/check_evidence.py:294-297`), Raw 링크가 raw/ 안을 가리킴 (`:303-306`), 숫자·날짜·인용의 원문 존재 (`:309-314`).
- [확인] 스크립트는 "The exit code carries no information"이라고 스스로 밝힌다 (`:28`). 실제로 wiki/가 없을 때만 1을 돌려준다 (`:361-363`, `:427`). 그래서 pre-commit gate로 바로 쓸 수 없다.
- [확인] 테스트도 이 동작을 고정한다. 경고가 나는 경우에도 `returncode == 0`을 단언한다 (`tests/test_check_evidence.py:338`, `:343`).
- [확인] 도구 허용 목록도 없다. `SKILL.md` frontmatter에 `allowed-tools`가 없다 (`SKILL.md:1-4`).

#### 3. 저장 구조

| 요소 | 내용 | 근거 |
|---|---|---|
| 디렉터리 | `wiki/<topic>/` 한 단계만(프롬프트 규칙). raw는 저장 경로 관례로 `raw/<topic>/`. 스크립트는 둘 다 `rglob`으로 깊이를 가리지 않는다 | `SKILL.md:20`, `SKILL.md:55`, `SKILL.md:230`, `scripts/check_evidence.py:319`, `:352` |
| 페이지 종류 | raw, article, archive 셋 | `references/*-template.md` |
| article 메타 | `> Sources:` `> Raw:` `> Updated:` | `references/article-template.md:3-5` |
| archive 메타 | `> Sources:`(wiki 링크) `> Archived:` | `references/archive-template.md:3-5` |
| raw 메타 | `> Source:` `> Collected:` `> Published:` | `references/raw-template.md:3-5` |
| 주장 상태 | `> **Status: Outdated** (날짜)`, `> **Status: Disputed**` | `references/article-template.md:17-21` |
| 파생 파일 | `wiki/index.md`, `wiki/log.md` 둘뿐 | `SKILL.md:21-22` |

[확인] YAML frontmatter를 쓰지 않는다. 메타데이터는 H1 바로 아래 blockquote다. 스크립트도 이 모양을 전제로 header를 가른다 (`scripts/check_evidence.py:96-146`).

[확인] manifest·ledger·hash 같은 상태 파일은 없다. `SKILL.md:41`은 "there is no incremental state to maintain"이라고 적었다.

[확인] log의 no-material heading 형식은 사람용 기록이면서 기계가 읽는 키다 (`SKILL.md:120`, `scripts/check_evidence.py:53-55`).

#### 4. Ingest

| 항목 | 입장 | 근거 |
|---|---|---|
| 사람 참여 | 보통은 사람이 소스 하나를 지목해 시작한다. 사람이 Research를 청하면 에이전트가 소스를 찾아 고른다. 어느 쪽이든 이후 승인 단계는 없다 | `SKILL.md:47`, `SKILL.md:66`, `SKILL.md:124-128` |
| 증분 추적 | 없다. raw가 불변이라 hash가 필요 없다고 본다 | `README.md:128` |
| backlog | 컴파일되지 않은 raw를 lint가 목록으로 보여 준다 | `scripts/check_evidence.py:345-355` |
| queue·crash 복구 | 없다 | (해당 파일 없음) |
| 자동 감시 | 의도적으로 뺐다 | `README.md:134` |
| 멀티포맷 변환 | 에이전트 도구에 맡긴다. 변환 코드는 없다 | `SKILL.md:51`, `README.md:118` |
| 병렬 | 검색은 병렬 가능, 컴파일은 한 소스씩 | `SKILL.md:128` |
| 건드리는 페이지 수 | 상한·목표 없음. 주 article 하나 이상 + cascade | `SKILL.md:83`, `SKILL.md:94` |

[확인] 원문 gist는 소스 하나가 10~15페이지를 건드린다고 적었다 (`lab/sources/karpathy-llm-wiki-gist/llm-wiki.md:37`). 이 skill은 숫자를 정하지 않는다. 대신 No material 처분으로 "Do not force an article out of a thin source"라고 막는다 (`SKILL.md:71`).

[확인] raw 파일만 `*.md`로 셈한다 (`scripts/check_evidence.py:352`). PDF 같은 원본은 markdown으로 옮긴 뒤에만 근거가 된다.

#### 5. 근거 추적 단위

페이지 단위 출처 + 일부 literal의 원문 글자 일치다. 줄 범위와 claim ledger는 없다.

- [확인] article은 `> Raw:` 줄로 raw 파일을 가리킨다 (`references/article-template.md:4`). 이것이 페이지 단위 출처다.
- [확인] 스크립트는 그 article이 가리키는 raw 안에서만 찾는다 (`scripts/check_evidence.py:298-314`). wiki 전체 raw가 아니다.
- [확인] 검사 대상은 닫힌 집합이다 (`:18-26`). 15자 이상 인용, ISO 날짜, 쉼표·소수점·K/M/B/% 접미사가 붙은 숫자, 4자리 이상 숫자다.
- [확인] 3자리 이하 정수, 글로 쓴 날짜는 검사하지 않는다 (`:23-25`, `:173-177`). 통화·부호는 기호만 무시된다. 숫자 부분이 쉼표·4자리 이상·접미사 조건을 채우면 검사한다. `$2,000`은 `2,000`으로 검사되고, `$200`은 200이 3자리라서 빠진다 (`:41-44`, `:173-177`). 예시 article의 "$200/month"와 "3 independent issues"가 이 이유로 범위 밖이다 (`examples/claude-code-statusline-landscape.md:30-31`).
- [확인] article header의 `Sources`·`Updated` 줄은 후보에서 빠진다 (`:48`, `:197-199`). 그래서 Sources에 적힌 날짜는 대조되지 않는다. 예시 article은 Sources에 `2026-03-19; 2026-03-24` 두 날짜를 적었지만 Raw 링크는 하나뿐이다 (`examples/claude-code-statusline-landscape.md:3-4`). Sources 수와 Raw 수가 어긋나도 스크립트는 보지 않는다.
- [확인] raw 쪽은 메타 header를 빼고 본문만 쓴다 (`:282-287`). Collected 날짜가 연도 후보를 잘못 통과시키지 않게 하려는 것이다.
- [확인] 숫자는 경계를 지켜 맞춘다. raw의 "142K"가 article의 "42K"를 통과시키지 않는다 (`:270-279`, 커밋 "fix: make the evidence checker actually check").
- [확인] 줄 번호 인용은 의도적으로 뺐다 (`README.md:129`). 근거는 관찰된 오류가 모두 "value absent from the source"였다는 운영 경험이다.

빈틈은 아래와 같다.

- [확인] Status block 안의 문장은 검사하지 않는다 (`scripts/check_evidence.py:225-233`). 테스트가 이 동작을 고정한다. "Superseded by the 2026-07-18 report, which restated the count as 55K"의 55K는 보고되지 않는다 (`tests/test_check_evidence.py:60-69`, `:377-382`). 템플릿은 "what the current understanding is"를 이 block 안에 적으라고 한다 (`references/article-template.md:17-18`). [추정] 그래서 대체 값이 block 안에만 적히는 경우가 생기기 쉽고, 그 값은 검사에서 빠진다. 사례 1개: 위 테스트 fixture가 바로 대체 값 55K를 block 안에만 적었다. 다만 merge 규칙은 본문의 "affected sections"도 고치라고 한다 (`SKILL.md:79`). 본문에도 적힌 값은 검사된다.
- [확인] archive 페이지는 Raw가 없으면 통째로 건너뛴다 (`:294-296`). archive는 wiki article을 인용하는 합성 답이라 원문 대조 경로가 아예 없다. 테스트가 지어낸 "999K"와 지어낸 인용이 보고되지 않는 것을 고정한다 (`tests/test_check_evidence.py:164-170`, `:312-316`).
- [확인] archive 면제는 페이지가 스스로 선언한다. header에 `> Archived:` 줄이 있고 Raw가 없으면 면제다 (`:295`). 본문이나 fence 안의 Archived 줄은 면제를 주지 않는다 (`tests/test_check_evidence.py:395-398`, `:526`). 하지만 일반 article이라도 header에 Archived 줄을 달면 evidence error와 사실 검사를 모두 피한다.
- [추정] 값이 raw 어딘가에 있으면 통과하므로, 맞는 숫자를 틀린 주장에 붙인 오류는 잡지 못한다. 사례 1개: `contains()`는 문맥을 보지 않고 존재만 본다 (`:270-279`). README는 이 실패를 아직 겪지 않았다고 적었다 (`README.md:129`).

#### 6. Link

LLM이 링크를 건다. 결정적 추출이나 backlink 파일은 없다.

- [확인] 여러 topic에 걸친 article은 See Also로 잇는다 (`SKILL.md:81`). 모순이 다른 article에 있으면 양쪽에 표시하고 서로 링크한다 (`SKILL.md:83`).
- [확인] 깨진 링크 수리는 lint의 Safe Fix다. 같은 파일명을 wiki에서 찾아 하나면 고치고, 없거나 여럿이면 사람에게 보고한다 (`SKILL.md:177-191`). 이 수리도 에이전트가 손으로 한다.
- [확인] See Also의 죽은 링크는 대상이 없으면 지운다 (`SKILL.md:190`). 다른 링크는 지우지 않는다.
- [확인] orphan 탐지와 빠진 cross-reference 제안은 판단 보고다 (`SKILL.md:210`, `SKILL.md:212`). 스크립트는 wiki 내부 링크를 보지 않는다.
- [확인] 타입 있는 관계는 뺐다. 링크 의미는 주변 문장에 둔다 (`README.md:136`).

#### 7. Lint

세 단계로 권한을 나눈다 (`SKILL.md:166`).

| 단계 | 하는 주체 | 검사 내용 | 자동 수정 |
|---|---|---|---|
| Safe Fixes | 에이전트(프롬프트) | index↔파일, 내부 링크, Raw 링크, See Also | 함 |
| Mechanical Reports | `check_evidence.py` | literal 원문 존재, evidence error, 미참조 raw | 안 함 |
| Judgment Reports | 에이전트 판단 | 모순, 낡은 주장, Status block 누락·형식, orphan, 빠진 개념, 낡은 archive | 안 함 |

[확인] 결정적 lint는 `check_evidence.py` 하나뿐이다. 이 스크립트가 사실 대조, evidence error, 미참조 raw 세 가지를 본다 (`scripts/check_evidence.py:4-16`). index 정합성과 wiki 내부 링크 검사는 결정적으로 할 수 있는 일인데도 프롬프트에 남아 있다 (`SKILL.md:172-191`).

[확인] 사실은 절대 자동 수정하지 않는다 ("never auto-fix facts", `SKILL.md:195`).

[확인] 스크립트가 낸 의심 항목은 후보일 뿐이고 에이전트가 raw 문맥으로 다시 판정한다 (`SKILL.md:197`).

[확인] commit gate는 없다. 근거는 #2의 exit code다.

#### 8. stale·모순 처리

supersede 표시 방식이다. 덮어쓰지 않고, drift 감지는 없다.

- [확인] 밀려난 주장은 그대로 두고 아래에 Status block을 단다. Outdated는 날짜를 붙이고, Disputed는 경쟁 주장을 출처와 함께 적는다 (`SKILL.md:96`, `references/article-template.md:15-21`).
- [확인] "Never silently rewrite history"가 규칙이다 (`SKILL.md:96`).
- [확인] archive 페이지는 cascade 대상이 아니다 (`SKILL.md:98`). 인용한 article이 크게 바뀐 archive는 lint가 판단 보고로 짚는다 (`SKILL.md:215`).
- [확인] source hash, 페이지별 review 날짜, 접근 기반 decay는 의도적으로 뺐다 (`README.md:128`, `README.md:131-132`). 새 정보는 새 소스로 들어온다는 전제다.
- [확인] 사람 리뷰 큐는 없다. 사람은 lint 보고(`SKILL.md:205`)나 article 안의 Disputed 표시를 직접 읽어야 안다.

#### 9. 사람 개입

자율 + 선언이다. plan 승인이나 쓰기 승인은 없다.

- [확인] Triage에서 에이전트는 처분을 "state"한다 (`SKILL.md:66`). 승인을 기다리라는 문구는 없다.
- [확인] Safe Fix와 Mechanical 단계에서 사람에게 넘기는 결정은 다섯 갈래다. index의 `[MISSING]` 항목 (`SKILL.md:174`), 같은 이름 파일이 없거나 여럿인 내부 링크 (`SKILL.md:180`), 같은 조건의 Raw 링크 (`SKILL.md:185`), 대상이 여럿인 See Also 링크 (`SKILL.md:191`), evidence error (`SKILL.md:199`). Judgment Reports는 전부 보고만 하고 사람에게 넘긴다 (`SKILL.md:205`).
- [확인] archive 저장과 Research는 사람이 명시적으로 청할 때만 한다 (`SKILL.md:124`, `SKILL.md:148`).
- [확인] 원문 gist는 사람이 ingest마다 요약을 읽고 방향을 잡는 방식을 선호한다고 적었다 (`lab/sources/karpathy-llm-wiki-gist/llm-wiki.md:37`). 이 skill은 그 대화 단계를 workflow에 넣지 않았다.

#### 10. 동시성·안전

코드 수준 장치는 없다. 프롬프트 규칙 둘과 읽기 전용 스크립트가 전부다.

- [확인] 컴파일은 한 소스씩이다. index, log, cascade가 공유 상태라서다 (`SKILL.md:128`).
- [확인] 초기화는 기존 파일을 덮어쓰지 않는다 (`SKILL.md:30`).
- [확인] 스크립트는 파일을 바꾸지 않는다 (`scripts/check_evidence.py:4`).
- [확인] transaction, 원자적 쓰기, snapshot, undo는 없다. `SKILL.md`와 `README.md`에 git·commit 언급도 없다 (grep 결과 hook 한 줄만 나옴, `README.md:134`).
- [확인] retract 장치는 의도적으로 미뤘다. "Handle it manually until it does" (`README.md:133`).

#### 11. Query·검색

index.md + grep이다. vector와 graph는 뺐다.

- [확인] index를 읽은 뒤 동의어까지 넣어 full-text 검색한다 (`SKILL.md:141`).
- [확인] 둘 다 비었을 때만 "없다"고 말하고, 검색했다는 사실도 밝힌다 (`SKILL.md:141`). 커밋 "guard against false absence"가 이 규칙을 넣었다.
- [확인] 훈련 지식보다 wiki 내용을 우선한다 (`SKILL.md:145`). 답은 raw가 아니라 wiki article을 인용한다 (`SKILL.md:143`).
- [확인] 답은 기본적으로 저장하지 않는다 (`SKILL.md:144`). 요청 시 archive 페이지로 저장한다. archive는 기존 article에 합치지 않는다 (`SKILL.md:155`).
- [확인] vector·graph 검색은 "50K–100K tokens of curated wiki"에서 grep이 더 믿을 만하다는 이유로 뺐다 (`README.md:135`).

#### 12. index·log 관리

LLM이 갱신하고 lint가 맞춘다. 결정적 재생성은 없다.

- [확인] index는 topic별 표다. 열은 Article, Summary, Updated다 (`references/index-template.md:7-9`).
- [확인] Updated는 파일 시각이 아니라 지식 내용이 바뀐 날이다 (`SKILL.md:102`, `references/article-template.md:5`).
- [확인] lint가 index와 article의 Updated를 비교해 index 쪽을 고친다 (`SKILL.md:175`).
- [확인] log는 append-only다. 형식은 원문 gist의 `## [YYYY-MM-DD] op | subject`를 따른다 (`SKILL.md:107-118`, `examples/log-sample.md:3`).
- [확인] 스크립트는 log에서 no-material heading만 읽는다. fence 안의 heading과 본문 언급은 무시한다 (`scripts/check_evidence.py:324-333`, `tests/test_check_evidence.py:419-445`).

#### 13. 포맷 표준

OKF를 따르지 않는다.

[확인] README는 OKF가 v0.1 draft이고 도구 생태계가 작아서 추적만 한다고 적었다 (`README.md:137`, `README.md:144`).

[확인] YAML frontmatter가 없으니 frontmatter 기반 표준과는 구조부터 다르다 (#3 참고).

[추정] OKF로 옮기려면 blockquote header를 frontmatter로 바꾸고 `parse_document()`도 고쳐야 한다. 사례 1개: header 판정이 `>`로 시작하는 줄에 묶여 있다 (`scripts/check_evidence.py:131-142`).

#### 14. 규모·비용

| 주장 | 근거 | 확인 가능 여부 |
|---|---|---|
| article 94개, topic 13개, 소스 99개 | `README.md:42-46` | 비공개 wiki라 확인 불가 |
| 최근 7일 log 87건 | `README.md:46`, `examples/README.md:34` | 확인 불가 |
| "three months of production logs" | `README.md:126` | 확인 불가 |
| wiki 크기 50K–100K tokens | `README.md:135` | 확인 불가 |
| 스크립트가 전체 wiki를 "in seconds"에 검사 | `SKILL.md:41` | 측정값 없음 |

[확인] 규모 숫자는 2026-04-12 커밋 "showcase real wiki data (94 articles, 99 sources, 87 log entries)"에서 들어왔다. 7월 Design Boundaries가 "three months"를 말할 때도 숫자는 갱신되지 않았다.

[확인] ingest 비용(토큰·시간·금액)은 어디에도 없다.

[확인] 컨텍스트 사용 방식은 index 한 장 + grep + 필요한 article 읽기다 (`SKILL.md:141-142`). cascade는 wiki 전체 검색을 요구한다 (`SKILL.md:94`).

[추정] wiki가 커지면 cascade 검색 비용이 ingest마다 늘어난다. 사례 1개: cascade 범위에 상한이 없다 (`SKILL.md:94`).

#### 15. frosk1 비판 7가지

| 비판 | 대응 | 강도 | 근거 |
|---|---|---|---|
| 오류 누적 | literal은 쓰기 전 locate + lint grep. 그 밖의 주장은 판단 lint뿐 | 부분 | `SKILL.md:41`, `SKILL.md:85`, `scripts/check_evidence.py:18-26` |
| 부분 문맥 | triage·cascade·query에서 동의어 포함 전체 검색을 요구. Research는 반대 측을 찾게 함 | 프롬프트만 | `SKILL.md:66`, `SKILL.md:94`, `SKILL.md:127`, `SKILL.md:141` |
| 요약 손실 | raw를 불변으로 남기고 article마다 Raw 링크를 단다. query는 raw로 내려가지 않는다 | 부분 | `SKILL.md:18`, `SKILL.md:143-145` |
| 가짜 source of truth | raw를 근거로 정의한다. 다만 query 답은 wiki를 인용한다 | 부분 | `SKILL.md:41`, `SKILL.md:143` |
| 환각 병합 | 모순은 Disputed로 남기고 조용한 재작성을 금지한다. 탐지는 LLM 판단 | 프롬프트만 | `SKILL.md:83`, `SKILL.md:96`, `SKILL.md:207-209` |
| 운영 복잡도 | 의존성 없는 skill 하나와 스크립트 하나. 기능 11개를 명시적으로 거절 | 강함 | `README.md:124-138` |
| ingest 비용 | No material이면 컴파일하지 않고 멈춘다. 비용 측정은 없다 | 약함 | `SKILL.md:71` |

[확인] frosk1의 8번째 항목(staleness)은 #8에서 다뤘다. 페이지별 타이머 대신 전체 lint로 유지한다는 입장이다 (`README.md:131`).

[확인] 롤백·버전 관리(운영 복잡도 비판의 한 갈래)는 다루지 않는다. git 언급이 없다 (#10).

#### 16. 성숙도·차용 가능성

| 항목 | 값 | 근거 |
|---|---|---|
| 테스트 | stdlib `unittest` 52개. 스크립트를 subprocess로 돌려 출력 문자열을 본다 | `tests/test_check_evidence.py:1-7`, `:199-205` |
| 예시 회귀 | 예시 article이 의심 항목 0개인지 검사 | `tests/test_check_evidence.py:719-731` |
| CI | 없다 (`.github/` 없음) | `ls` 결과 |
| 의존성 | 없다. Python 3.10+ (`str \| None` 주석) | `scripts/check_evidence.py:36-39`, `:66` |
| 라이선스 | MIT. 코드 차용 가능 | `LICENSE:1-3` |
| 활동 | 2026-07-23 이후 push 없음 | gh api |

[확인] README FAQ는 "a design spec"이 저장소에 있다고 적었다 (`README.md:122`). 현재 트리에는 없다. 첫 커밋 메시지가 `docs/SPEC.md`를 언급하지만, gh api로 본 첫 커밋 트리에는 `.gitignore`만 있다.

[확인] 스크립트를 고친 커밋 8개는 모두 테스트도 함께 고쳤다. 예를 들어 "make the evidence checker actually check"는 스크립트 +109줄, 테스트 +157줄이다. [추정] 그래서 `check_evidence.py`는 떼어 와도 경계 사례가 잘 덮여 있다. 사례 1개: fence 변형, 날짜 경계, 접미사 공백 같은 경계마다 test class가 따로 있다 (`tests/test_check_evidence.py:385-716`).

[확인] examples/는 "real files from a knowledge base"라고 소개한다 (`examples/README.md:3`). 하지만 7월 23일 커밋들이 예시를 새 규칙에 맞게 고쳤다.

- 커밋 9340c1f("close the candidate set and hold examples to it")가 예시 raw의 header에 있던 "market data as of 2026-03-19"를 본문 문장으로 옮겼다. 스크립트가 raw header를 근거에서 빼면서 article의 날짜가 통과하도록 raw를 고친 것이다. 저장소 스스로 raw 불변 규칙을 지키지 않은 사례다.
- 같은 커밋이 예시 article의 인용 두 개를 raw 표기에 맞게 바꿨다("one command to see amount" → "one command to see costs" 등).
- 커밋 f8e592f와 eafcc77이 `log-sample.md`를 통째로 새 형식 항목으로 바꿨다. 새 항목 다섯 가운데 넷은 날짜가 2026-04-15~04-21이다. 4월 12일 예시 추가 커밋보다 뒤의 날짜이고, 7월 커밋으로 들어왔다.
- [추정] 그래서 예시 smoke test(`tests/test_check_evidence.py:719-731`)의 0개는 운영 wiki가 그대로 통과했다는 증거가 아니다. 사례 1개: 위 인용 두 개는 고치기 전에는 raw에 글자 그대로 없었다.

## 장점

- 규칙의 근거를 함께 남긴다. [확인] Design Boundaries는 거절한 기능마다 이유를 한 줄씩 붙였다 (`README.md:124-138`). 다른 구현의 기능을 평가할 때 반론 자료로 쓸 수 있다.
- 사실 검증의 경계가 명시적이다. [확인] 무엇을 검사하고 무엇을 안 하는지 docstring에 닫힌 목록으로 적었다 (`scripts/check_evidence.py:18-26`). 새 표기를 넣을 때 regex가 아니라 목록부터 고치라고 적었다.
- establish/verify를 나눴다. [확인] 쓰기 전 locate가 establish이고 lint grep이 verify다 (`SKILL.md:41`, `SKILL.md:85`). 쓰는 단계와 검사하는 단계가 같은 규칙을 공유한다.
- 근거 범위가 article별이다. [확인] 그 article이 가리키는 raw 안에서만 찾는다 (`scripts/check_evidence.py:298-314`). 다른 소스의 같은 숫자가 잘못 통과하지 않는다.
- 얇은 소스를 거른다. [확인] No material 처분이 억지 article을 막는다 (`SKILL.md:71`). 버린 raw도 log에 남아 inventory에서 빠진다 (`scripts/check_evidence.py:345-355`).
- false absence를 막는 문구가 있다. [확인] index와 full-text가 모두 비었을 때만 "없다"고 답한다 (`SKILL.md:141`).
- 역사를 지우지 않는다. [확인] Outdated·Disputed block으로 옛 주장을 남긴다 (`SKILL.md:96`).
- 가볍다. [확인] 의존성 없음, 스크립트 431줄, MIT다.

## 단점

- 강제가 없다. [확인] wiki/가 있으면 exit code가 항상 0이라 gate가 될 수 없다 (`scripts/check_evidence.py:28`, `:427`). raw 불변도 문장뿐이다 (`SKILL.md:18`). `SKILL.md:41`의 "a verified article stays verified"는 이 불변 규칙에 기댄다.
- Status block 안의 대체 값이 검사에서 빠진다. [확인] Status block 안은 검사하지 않는다 (`scripts/check_evidence.py:225-233`, `tests/test_check_evidence.py:377-382`). 템플릿이 현재 이해를 block 안에 적게 한다 (`references/article-template.md:17-18`). [추정] 대체 값이 block 안에만 적히면 가장 새로운 사실이 대조되지 않는다. 사례 1개: 테스트 fixture의 55K.
- archive는 근거 검사 경로가 없다. [확인] Raw 없는 archive는 건너뛴다 (`scripts/check_evidence.py:295-296`). archive에 새로 생긴 숫자는 어디에도 대조되지 않는다. 면제 조건도 페이지가 스스로 다는 `> Archived:` 줄 하나다.
- 검사는 존재만 본다. [추정] 맞는 값을 틀린 주장에 붙인 오류는 통과한다. 사례 1개: `contains()`가 문맥 없이 부분 문자열만 찾는다 (`scripts/check_evidence.py:270-279`).
- 결정적으로 할 수 있는 lint를 LLM에 맡겼다. [확인] index 정합성, 링크 수리, See Also 정리는 모두 프롬프트 지시다 (`SKILL.md:172-191`). 스크립트는 wiki 내부 링크를 보지 않는다.
- 3자리 이하 정수는 검사 밖이다. [확인] 예시 article에도 "$200", "3 independent issues"가 있다 (`examples/claude-code-statusline-landscape.md:30-31`). 통화 기호가 붙은 큰 수(`$2,000`)는 숫자 부분이 검사된다.
- Sources 메타는 대조하지 않는다. [확인] Sources 줄의 날짜는 후보에서 빠지고, Sources 수와 Raw 수가 어긋나도 보고하지 않는다 (`scripts/check_evidence.py:48`, `examples/claude-code-statusline-landscape.md:3-4`).
- 예시가 "real files"라는 소개와 다르게 7월에 고쳐졌다. [확인] 예시 raw 본문과 article 인용을 checker에 맞게 바꿨다 (커밋 9340c1f). raw 불변 규칙을 저장소 스스로 어긴 사례다.
- 규모 주장이 검증되지 않고 오래됐다. [확인] 94/99/87 숫자는 4월 커밋 그대로다 (#14).
- 사람 참여가 약하다. [확인] triage 처분은 선언일 뿐 승인 단계가 없다 (`SKILL.md:66`).
- 롤백이 없다. [확인] git·snapshot 언급이 없다 (#10).
- 활동이 멈췄다. [확인] 마지막 push가 2026-07-23이다.

## 내 llm-wiki에 가져올 것 / 피할 것

가져올 것:

- Grounding Invariant 문장 자체. "숫자·날짜·인용은 그 페이지가 가리키는 raw에 글자 그대로 있다"를 schema 첫머리에 둔다 (`SKILL.md:41`).
- locate-before-write 규칙. 찾은 표기 그대로 쓰고, 계산한 값은 구성 요소를 함께 보인다 (`SKILL.md:85`).
- `check_evidence.py`의 후보 추출과 경계 매칭. MIT라 코드째 가져올 수 있다. 테스트 52개도 같이 가져온다.
- 닫힌 후보 집합을 docstring에 적는 습관 (`scripts/check_evidence.py:18-26`).
- raw 메타 header를 근거에서 빼는 처리 (`scripts/check_evidence.py:282-287`).
- Triage 처분 4종과 No material 정지 경로, 그리고 이를 log heading으로 기계가 읽게 하는 방식 (`SKILL.md:64-73`, `SKILL.md:116-120`).
- Status: Outdated / Disputed block (`references/article-template.md:17-21`).
- false absence 금지 문구 (`SKILL.md:141`).
- Design Boundaries처럼 "만들지 않은 것과 이유"를 문서로 남기는 관행 (`README.md:124-138`).
- lint를 safe fix / mechanical report / judgment report 세 권한으로 나누는 틀 (`SKILL.md:166`).

피할 것:

- exit code 없는 검사기. 가져오면 의심 항목·evidence error 수로 exit code를 내게 바꿔 pre-commit에 건다.
- Status block 면제. 대체 값은 그 block이 인용하는 새 raw에 대조하도록 바꾼다.
- archive 면제. archive의 literal은 인용한 article의 Raw로 거슬러 대조한다.
- 프롬프트만의 raw 불변. hook이나 파일 권한, 또는 raw hash 목록으로 강제한다. README가 hash를 거절한 이유는 raw가 불변이라는 전제다 (`README.md:128`). 그 전제를 코드로 지키지 않으면 이유도 같이 흔들린다.
- index·링크 정합성을 LLM에 맡기기. 결정적 스크립트로 옮긴다.
- 검증 안 된 규모 숫자를 README에 두는 것.

## 확인하지 못한 것

- 테스트 52개가 지금 통과하는지. 저장소 코드를 실행하지 않았다. `python3 -m unittest tests/test_check_evidence.py`를 격리 환경에서 돌리면 알 수 있다.
- 예시 article이 실제로 의심 항목 0개인지. 테스트가 이를 주장하지만(`tests/test_check_evidence.py:719-731`) 돌려 보지 않았다. 통과하더라도 예시를 checker에 맞게 고친 뒤의 결과다(#16).
- 운영 wiki의 규모와 "three months of production logs" 내용. wiki가 공개되지 않았다. 작성자에게 log 사본을 받아야 알 수 있다.
- "every observed fidelity error was 'value absent from the source'"라는 관찰의 표본 크기 (`README.md:129`). 근거 로그가 저장소에 없다.
- "in seconds" 속도 주장 (`SKILL.md:41`). 측정값이 없다. 수백 페이지 wiki를 만들어 시간을 재면 알 수 있다.
- README FAQ가 말한 design spec의 내용 (`README.md:122`). 트리에도 첫 커밋에도 없다. 작성자 로컬에만 있는 것으로 보인다.
- 에이전트가 프롬프트 규칙(한 소스씩 컴파일, 동의어 검색, locate-before-write)을 실제로 얼마나 지키는지. 같은 소스로 여러 번 ingest를 돌려 diff를 비교해야 알 수 있다.

## 검증 기록

- #2에 테스트가 exit code 0을 단언한다는 사실을 더했다 (`tests/test_check_evidence.py:338`, `:343`).
- #3 디렉터리 행을 고쳤다. 한 단계 규칙은 wiki에만 있고, 스크립트는 깊이를 가리지 않는다.
- #4 사람 참여 행에 Research 경로(에이전트가 소스를 고름)를 더했다.
- #5 "통화는 검사 밖"을 고쳤다. 통화 기호만 무시되고 숫자 부분은 조건이 맞으면 검사된다.
- #5에 Sources 메타 날짜가 대조되지 않는다는 항목과 예시 article의 Sources·Raw 수 불일치를 더했다.
- #5 Status block 빈틈을 "가장 최근 사실이 빠진다"에서 "block 안에만 적힌 대체 값이 빠진다"로 낮추고 [추정]으로 바꿨다.
- #5에 archive 면제가 header의 `> Archived:` 자기 선언 하나에 달렸다는 것과 이를 고정하는 테스트를 더했다.
- #7 "결정적 lint는 사실 검사 하나뿐"을 "check_evidence.py 하나가 세 가지를 본다"로 고쳤다.
- #8 "Disputed 표시가 사람에게 남기는 신호"라는 근거 없는 해석을 사실 서술로 바꿨다.
- #6 링크 수리의 보고 조건을 "없거나 여럿"으로 고쳤다.
- #9 사람에게 넘기는 결정 목록을 셋에서 다섯 갈래로 고쳤다. 내부 링크 조건도 "여럿"에서 "없거나 여럿"으로 고쳤다.
- #16 "버그 수정 커밋마다"를 "스크립트를 고친 커밋 8개 모두"로 좁혔다.
- #16에 7월 커밋이 예시 raw·article·log를 checker에 맞게 고쳤다는 항목을 더했다 (커밋 9340c1f, f8e592f, eafcc77).
- 단점의 exit code 문장에 "wiki/가 있으면"을 붙였다.
- 단점에 Sources 메타 미대조, 예시 수정 항목을 더했다. Status block·archive·통화 항목을 위와 맞췄다.
- 확인하지 못한 것의 smoke test 항목에 예시 수정 사실을 덧붙였다.
- 나머지 path:line 인용은 모두 열어 보았다. 가리키는 내용이 맞았다.

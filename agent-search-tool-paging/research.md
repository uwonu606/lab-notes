# 에이전트 검색 툴 — 하이브리드·reranker·이어 보기의 결론

- 조사 날짜: 2026-11-07
- 물음: 엑셀·markdown처럼 형식이 섞인 많은 문서를 에이전트 툴이 키워드·임베딩 벡터·메타데이터를 섞어 찾고, reranker를 거친 결과를 상위 몇 건씩 넘길 때 "다음 10건"도 줄 수 있는 설계인가.
- 재료: `~/dig-notes/agent-hybrid-search-paging/`의 `map.md`(지도 64줄, 1인칭 조각 1,162개를 대어 판정), `sources.md`(출처 196), `people/`(카드 다섯). 줄 번호(M1, N5)는 그 `map.md` 첫 표의 번호다. 이 문서는 그 조사의 `conclusion.md` 사본이다.
- 이전 조사와의 관계: `~/dig-notes/search-vocabulary`는 검색 어휘를, `~/dig-notes/llm-findable-structure`는 결함 데이터의 구조를 다뤘다. 이 조사는 검색 구조와 이어 보기를 다룬다.

## 읽는 법

큰따옴표 안은 원문 그대로이고, 옮김은 괄호에 붙였다. 출처 링크는 인용 바로 뒤에 둔다. 조각의 출처가 벤더 소속이면 그렇게 적었다. 수치는 그 사람의 corpus에서 잰 것이라 다른 표의 숫자끼리는 견주지 않는다.

## 결론

| 번호 | 결론 | 가장 센 근거 |
|---|---|---|
| 1 | "다음 10건"을 못 주는 것은 reranker가 아니라 툴이 상위 몇 건만 남기고 버리기 때문이다 | reranker는 후보 전부를 정렬해 돌려준다(M39 확인 4). 벤더는 reranker 뒤 paging을 다루지 않는다 |
| 2 | 에이전트가 페이지를 넘긴다고 전제할 수 없다. 실무자는 페이지 대신 id·얇은 레코드를 주고 본문은 별도 호출로 꺼내게 한다 | 다음 페이지 요청 0회 측정(M38)과 context가 찰 때까지 받아 온 관찰(M29 깸)이 둘 다 있다 |
| 3 | 하이브리드는 기본값이 아니다. 자기 평가셋으로 재 보고 켠다 | 한쪽이 약하면 RRF가 벡터 단독보다 못한 실측(M1 깸 13) |
| 4 | 순위 지표(MRR·nDCG)가 아니라 "돌려준 묶음에 답이 들었나"로 잰다 | 에이전트는 돌려준 것을 전부 읽는다(M20·N9) |

### 1. 이어 보기는 툴이 붙잡아 두면 된다

reranker는 받은 후보 전부에 점수를 매겨 정렬된 목록을 돌려주고 top_n은 돌려줄 개수만 자른다. 그래서 이어 보기를 원하면 1차 후보 풀(50~300건)을 한 번 rerank한 목록을 툴 세션에 붙잡아 두고 불투명한 cursor로 10건씩 잘라 주면 된다.

재질의로 offset을 흉내 내면 깨진다. OpenSearch 포럼의 답이 그 이유를 적는다 — "when you increase the from and size values to see more results then new results captured might end up on earlier pages" [출처](https://forum.opensearch.org/t/hybrid-search-pagination-best-practices/23545) (옮김: from·size를 키워 더 보려 하면 새로 잡힌 결과가 앞 페이지에 올라올 수 있다).

OpenSearch는 그래서 `pagination_depth`로 샤드별 후보 풀을 먼저 고정하고 그 안에서 from·size로 넘기게 했다. 반대로 Pinecone은 paging이 없어 topK를 10,000까지 키워 클라이언트에서 자르라고 답하고, Milvus는 iterator가 rerank 뒤에 깨지며, Elasticsearch는 `rank_window_size` 밖 페이지가 0건이다(M37·M8).

### 2. 에이전트는 페이지를 넘기기도 하고 안 넘기기도 한다

룩셈부르크 대학 팀은 예산을 넘긴 도구 응답에서 에이전트가 스스로 다음 페이지를 요청한 횟수가 0이었다고 쟀다(M38, [출처](https://arxiv.org/html/2608.26130)). Datadog MCP 개발자 Reilly Wood는 반대를 봤다 — "an agent would request a reasonable number of logs and then the context window was gone because a few of the logs were huge" [출처](https://www.datadoghq.com/blog/engineering/mcp-server-agent-tools/) (옮김: 에이전트가 적당한 수의 로그를 요청했는데 몇 개가 거대해서 context window가 날아갔다).

Claude Code skill이 Atlassian MCP의 cursor를 끝까지 따라가다 마지막 페이지에서 멈춘 이슈도 있다(M29 깸).

둘 다 실재하므로 실무자들은 페이지 계약에 기대지 않는다. 검색은 id·제목·짧은 발췌만 돌려주고 본문은 `get(id)`로 꺼내게 한다(N5).

한 페이지 크기는 어차피 하네스가 먼저 자른다 — Claude Code 25k·Codex 10k 토큰이고 릴리스마다 바뀐다(N6). 응답 모양을 바꾸면 tool description도 같이 바꿔야 한다. 안 그러면 "the agent stops at the thin record, never realises" [출처](https://dev.to/alexbudanov/an-mcp-server-post-mortem-context-vs-protocol-375l) (옮김: 에이전트가 얇은 레코드에서 멈추고 더 있다는 걸 모른다).

### 3. 하이브리드는 재 보고 켠다

Javier Cañete가 자기 랩에서 잰 수치가 가장 날카롭다 — "Fusing both lists with Reciprocal Rank Fusion (RRF, with k = 60) gave 0.642, below the 0.811 of BGE-M3 alone. The FTS was weak enough to add noise to the good list." [출처](https://jacar.es/en/local-reranking-llama-cpp-pgvector/) (옮김: RRF로 합치니 0.642로 BGE-M3 단독 0.811보다 낮았다. 전문 검색이 약해서 좋은 목록에 잡음을 보탰다).

gnosis-mcp는 하이브리드가 키워드 단독과 바이트 단위로 같은 top-10을 냈다고 적었다(M1 깸).

품질을 가장 크게 움직인 것은 reranker나 임베딩 모델이 아니라 chunking과 BM25 추가였다(N3). 손대는 순서는 chunking → BM25 → 평가셋으로 벡터 추가 여부 확인 → 마지막에 reranker다. reranker는 표·레퍼런스·이미지 메타데이터 같은 비산문 chunk를 체계적으로 내린다(N4).

메타데이터는 두 갈래다. 권한·종류처럼 포함 여부를 정하는 것은 점수 전에 거르는 필터이고(M36), 최신성처럼 얼마나 위로 올릴지를 정하는 것은 fusion 뒤 점수에 더하는 축이다(N17).

엑셀 표는 chunk 임베딩이 틀렸다는 쪽(M15 깸)과 text-to-SQL도 벡터만큼 안 됐다는 쪽(M13)이 맞서므로, 정량 질문은 SQL 경로, 설명 질문은 표 요약 임베딩 경로로 가른다.

### 4. 순위 지표가 아니라 내용 적중으로 잰다

Candlekeep 제작자의 말이다 — "An agent doesn't click. It reads everything you return. It doesn't care whether the relevant chunk is at position 1 or position 2 — it cares whether the chunk you returned at *any* position actually contains the answer." [출처](https://reddit.sentinel-team.org/posts/1rlt0su/snapshots/2026-03-06T19%3A31%3A02.646669Z) (옮김: 에이전트는 클릭하지 않고 돌려준 것을 전부 읽는다. 1위냐 2위냐가 아니라 어느 위치든 답을 담았는지만 중요하다). 그의 파이프라인은 Hit Rate@1과 Precision을 올리면서 MRR은 6~11% 떨어뜨렸다(N9).

## 바꾼 뒤의 모양

조사한 사람들이 겪고 나서 실제로 어떤 형태로 바꿨는지다. 전부 1인칭 글이고, 벤더 소속은 표시했다.

| 사람 | 전 | 후 | 출처 |
|---|---|---|---|
| Nicolas Bustamante (Fintool 창업자) | 1년 걸린 하이브리드+rerank 스택 | 검색 툴은 날짜·검색어를 받아 메타데이터만 100~200건, 읽기는 ID로. 하이브리드는 "a tool for agents"로 내려감 | [출처](https://www.nicolasbustamante.com/blog/the-rag-obituary-killed-by-agents) |
| Reilly Wood (Datadog MCP, 벤더 소속) | 레코드 수로 자르는 페이지 | 토큰 예산으로 자르고 cursor 반환. 드문 필드는 기본 출력에서 빼고 요청하면 줌. 요약 요청은 받아 오기 대신 SQL | [출처](https://www.datadoghq.com/blog/engineering/mcp-server-agent-tools/) |
| Shinsuke KAGAWA (mcp-local-rag·jev-reranker) | RRF 하이브리드 | 벡터 거리를 주 신호로 두고 키워드는 나눗셈 boost. reranker 점수는 거리와 섞지 않고 단독 정렬. evidence 0.5 미만이면 빈 배열, 채워 넣지 않음 | [출처](https://dev.to/shinpr/what-retrieval-still-hasnt-decided-3haa) |
| BansheeEmperor (Candlekeep MCP) | reranker를 항상 거는 한 경로 | simple·hybrid·precise 세 경로를 열어 두고 에이전트가 질의마다 고름. 인접 chunk 확장이 content match를 가장 크게 올림 | [출처](https://reddit.sentinel-team.org/posts/1rlt0su/snapshots/2026-03-06T19%3A31%3A02.646669Z) |
| Jediah Katz (Cursor, 벤더 소속) | 긴 도구 결과를 context에 넣음 | 결과를 파일로 쓰고 에이전트가 tail·grep으로 읽음 | [출처](https://cursor.com/blog/dynamic-context-discovery) |
| Alexander Budanov (MCP 서버 post-mortem) | 3건에 61KB를 돌려주던 list | list는 id·제목·상태만, 본문은 `get_bug`로. tool description에 그 규약을 적음 | [출처](https://dev.to/alexbudanov/an-mcp-server-post-mortem-context-vs-protocol-375l) |
| cbcoutinho (nextcloud-mcp-server) | 클라이언트가 algorithm·가중치를 고르는 파라미터 | 파라미터를 전부 없애고 Qdrant 안의 BM25 하이브리드(RRF 기본) 하나로 | [출처](https://raw.githubusercontent.com/cbcoutinho/nextcloud-mcp-server/7384b47795fb5984ce34652002a7bed051c026fb/docs/ADR-014-bm25-search.md) |
| 이창근 (한국어 책 저자) | 하위 질의 3회·월별 7회 검색 뒤 RRF 병합 | 단일 검색으로 되돌림. Recall@10 0.837 대 0.737로 "일곱 배로 검색한 쪽이 가장 나쁩니다" | [출처](https://wikidocs.net/390112) |
| Alex Isken (Sourcegraph Cody, 벤더 소속) | 임베딩이 검색의 중추 | 임베딩을 버리고 키워드 검색으로 | [출처](https://sourcegraph.com/blog/how-cody-understands-your-codebase) |

공통점은 셋이다. 검색이 돌려주는 것을 얇게 만들고 읽기를 분리했다. 융합·reranker를 줄이거나 단순화했다. 경로를 하나로 고정하지 않고 에이전트나 질의 모양에 맡겼다.

## 설계로 옮기면

| 단계 | 하는 것 |
|---|---|
| 색인 | markdown은 헤더 단위 chunk. 표는 시트별 SQL 테이블과 LLM 요약 임베딩 둘 다. 종류·권한·날짜를 메타데이터로 |
| 질의 | 권한·종류 필터 → BM25와 벡터를 따로 뽑되 자기 평가셋으로 하이브리드가 이기는지 먼저 확인 → 후보 50~300건 rerank → 점수 간격이나 threshold로 건수를 정하고 없으면 빈 결과 |
| 반환 | id·제목·발췌만. 본문은 `get(id)`. rerank한 목록은 세션에 붙잡아 두고 cursor로 이어 보기를 열어 두되 거기에 기대지 않음 |
| 측정 | 돌려준 묶음에 답이 들었는지(content match)와 end-to-end 정확도를 따로. 답 없는 질의도 평가셋에 넣음 |

첫 실험은 자기 로그에서 에이전트가 `next_cursor`를 부르는 비율을 재는 것이다. 0에 가까우면 반환 단계의 얇은 레코드 설계로 가고, 높으면 세션 붙잡기 설계로 간다.

## 확인하지 못한 것

- 에이전트가 페이지를 넘기는지는 하네스·프롬프트마다 다르다. 자기 로그로만 답이 난다.
- 한국어·중국어 1인칭 글은 탐침에서 거의 안 나와 영어·일본어로 쏠렸다(`sources.md` 언어 탐침).
- Medium 유료 글 2개와 LinkedIn 글 2개는 열지 않았다(`sources.md` 못 찾음).

## 약칭

| 약칭 | 뜻 |
|---|---|
| BM25 | 키워드 일치 점수. 전문 검색 색인 위에서 돈다 |
| RRF | reciprocal rank fusion. 두 검색 결과의 순위만으로 합치는 방식 |
| reranker | 1차 후보를 query와 함께 다시 읽어 순서를 매기는 모델. cross-encoder가 흔하다 |
| MCP | Model Context Protocol. 에이전트가 툴을 부르는 규약 |
| MRR·nDCG·Hit Rate | 순위 기반 검색 품질 지표 |
| content match | 돌려준 묶음 안에 답이 들었는지를 보는 지표 |

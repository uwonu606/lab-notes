# 일부러 넓게 잇고 나중에 지우기 쉬운 구조: 조사 종합

## 표시 규칙

- `[2차 검증: 맞음]`: 수집한 에이전트와 다른 에이전트가 원문을 다시 열었다. 그 에이전트는 인용과 설명을 맞다고 판정했다.
- `[2차 검증: 일부]`: 다른 에이전트가 원문을 다시 열었다. 인용은 맞지만 설명의 일부가 바로잡혔다. 바로잡힌 내용은 "옮겨지지 않는 것"에 반영했다.
- `[critic만]`: 빠진 것을 찾는 critic 에이전트만 열어 본 출처다. 다른 에이전트가 다시 확인하지 않았다.
- kfchou lint-mechanical은 반박됐다. 그래서 쓰지 않았다.

---

## 1. 여섯 가지 패턴

### 1.1 링크를 근거가 붙은 파생 데이터로 본다

**메커니즘.** 파생 결과마다 그것을 만든 근거를 적어 둔다. 근거 수를 세어 두기도 한다. 근거를 철회하면 그 근거에 기댄 결과만 빠진다. 근거가 하나도 남지 않은 결과는 사라진다. 다른 근거가 남은 결과는 그대로 산다.

**대표 출처**
- Counting algorithm (Gupta, Mumick, Subrahmanian, SIGMOD 1993). 논문. http://www.cs.columbia.edu/~gravano/Qual/Papers/13%20-%20Maintaining%20Views%20Incrementally.pdf
  "The counting algorithm works by storing the number of alternative derivations of each tuple t in the materialized view." `[2차 검증: 일부]`
- ATMS (de Kleer, Artificial Intelligence 1986). 논문. https://dekleer.org/Publications/An%20Assumption-Based%20TMS.pdf
  "context switching is free, and most backtracking (and all retraction) is avoided." `[2차 검증: 맞음]`
- Provenance Guided Rollback Suggestions (Zhao 외, arXiv 2501.09225). 논문. https://arxiv.org/abs/2501.09225
  "This paper introduces an incremental debugging technique for Datalog, which determines the failing changes for a rollback in an incremental setup." `[2차 검증: 맞음]`
- Event Sourcing (Martin Fowler). 블로그. https://martinfowler.com/eaaDev/EventSourcing.html
  "We can discard the application state completely and rebuild it by re-running the events from the event log on an empty application." `[2차 검증: 맞음]`
- Provenance semirings (Green, Karvounarakis, Tannen, PODS 2007). 논문. https://web.cs.ucdavis.edu/~green/papers/pods07.pdf
  "It seems that we need to know not just which input tuples contribute but also how they contribute." `[2차 검증: 일부]`
- LightRAG adelete_by_doc_id. GitHub. https://github.com/HKUDS/LightRAG/blob/main/lightrag/lightrag.py
  "If entities or relationships are partially affected, they will be rebuilded using LLM cached from remaining documents." `[2차 검증: 일부]`
- 반면교사 1: Microsoft GraphRAG issue #2590. GitHub issue. https://github.com/microsoft/graphrag/issues/2590
  "the incremental update computes which documents were removed from the input, but never uses that information." `[2차 검증: 맞음]`
- 반면교사 2: A-MEM memory_system.py. GitHub. https://github.com/agiresearch/A-mem/blob/main/agentic_memory/memory_system.py
  `note.links.extend(suggest_connections)` `[2차 검증: 일부]`
- 같은 축의 출처: DRed, Hu-Motik-Horrocks AAAI 2018, JTMS(Doyle 1979), ULDBs/Trio, Soufflé provenance, differential dataflow, ER with Evolving Rules. 모두 `[2차 검증: 일부]` 또는 `[2차 검증: 맞음]`이다.

**우리 설정에 옮기면**
- 링크 (A, B)의 근거는 "둘 다 언급한 entry"다. 정확히는 매칭된 (entry, alias)다.
- [확인] 우리 링크 규칙은 재귀 없는 join 하나다. 원문은 counting을 비재귀 뷰용으로 제시한다. 그래서 Counting이 그대로 맞는다.
- 공유 entry 수가 곧 count다. alias 하나를 빼면 count가 줄어든다. count가 0이 된 링크만 사라진다.
- [추정] ATMS를 옮기면 LLM 행동 하나가 가정 하나가 된다. 그러면 원래 용어집과 LLM이 키운 용어집의 비교가 context 전환이 된다. 근거는 ATMS 원문 1개다. 이 적용은 우리 쪽 해석이다.
- [추정] Rollback 논문의 구조는 우리 문제와 모양이 같다. 원문은 입력 변경, 원치 않는 결과, 원인 변경 rollback의 순서다. 우리는 용어집 행동, 틀린 링크, 행동 철회의 순서다. 근거는 이 논문 1개다.

**옮겨지지 않는 것**
- 이 패턴은 무엇이 틀렸는지 알 때 지우는 법을 준다. 무엇이 틀렸는지 찾아 주지는 않는다.
- Rollback 논문에서도 결함 집합은 사용자가 준다.
- JTMS 본문은 열어 보지 못했다. 그래서 IN/OUT 같은 세부는 근거로 쓸 수 없다.
- differential dataflow나 Soufflé 같은 엔진은 수천 노트 규모에서는 과하다.

### 1.2 후보 층과 확정 층을 나눈다

**메커니즘.** 기계가 만든 링크는 후보 층에 둔다. 확정 층과 섞지 않는다. 확인을 통과한 것만 확정 층으로 올라간다. 후보는 따로 저장되거나, 화면을 그릴 때만 계산된다.

**대표 출처**
- NELL (Carlson 외, AAAI 2010). 논문. https://www.cs.cmu.edu/~acarlson/papers/carlson-aaai10.pdf
  "Category and relation instances added to the KB are partitioned into candidate facts and beliefs." `[2차 검증: 일부]`
- Knowledge Graph Identification with PSL (Pujara 외, ISWC 2013). 논문. https://www.jaypujara.org/pubs/2013/pujara:iswc13/pujara_iswc13.pdf
  "determining which candidate facts should be included into a knowledge graph as knowledge graph identification." `[2차 검증: 맞음]`
- Wikimedia "Add a link" (mwaddlink). product docs와 Phabricator. https://wikitech.wikimedia.org/wiki/Add_Link
  "A MySQL table per wiki is used for caching the actual link recommendations" `[2차 검증: 맞음]`
- Obsidian Virtual Linker. GitHub. https://github.com/vschroeter/obsidian-virtual-linker
  "The auto generated links are post-processed, so they neither change your note text to hard-coded links enclosed in brackets not appear in the graph view or reference counting." `[2차 검증: 맞음]`
- mindbase links 표의 origin과 confidence 열. 로컬에 클론한 GitHub repo. llm-wiki-implementations/lab/repos/frankchu91_mindbase-llm-wiki/packages/core/src/graph/index/wiki-index.ts
  "Origin is set to 'llm' to distinguish from markdown-derived edges." `[2차 검증: 일부]`
- Wikidata Mix'n'match. product docs. https://meta.wikimedia.org/wiki/Mix'n'match/Manual
  "the system has guessed one or more possible match for the entry in Wikidata, but a person needs to verify or reject it." `[critic만]`
- 같은 축의 출처: inkeep links suggest, Obsidian unlinked mentions, Smart Connections. 모두 `[2차 검증: 일부]` 또는 `[2차 검증: 맞음]`이다.
- 반쪽 사례: Ar9av cross-linker. 이 도구도 INFERRED 등급을 매긴다. 그러나 등급은 보고서에만 남는다. 파일에 쓴 링크에는 표시가 없다. 그래서 나중에 골라낼 수 없다. `[2차 검증: 일부]`

**우리 설정에 옮기면**
- 지금의 co-mention 링크 전체를 후보 층으로 본다. PSL 논문의 용어로는 extraction graph다.
- 조회할 때는 확정 층만 쓴다. 확정 층은 점수 문턱이나 LLM 판정을 통과한 부분집합이다.
- 상태는 세 단계로 둘 수 있다. 후보, 확정, 거절이다.
- 링크에 origin을 단다. 예를 들어 "원래 용어집에서 왔다"와 "LLM이 키운 용어집에서 왔다"를 구분한다.

**옮겨지지 않는 것**
- Wikimedia, Virtual Linker, Mix'n'match, Smart Connections는 모두 사람이 승격한다. 우리는 사람 검토가 없다. 그 자리를 점수 문턱(#1.3)이나 LLM 검증기가 맡아야 한다.
- LLM 검증기를 쓴다면 KGValidator의 출력 형식(is_valid와 reason)을 빌릴 수 있다. KGValidator는 `[2차 검증: 일부]`다.
- NELL에는 강등 경로가 없다. 원문은 "once a candidate fact is promoted as a belief, it is never demoted."라고 쓴다.
- [확인] 우리에게 NELL의 KB에 해당하는 것은 링크가 아니다. LLM이 키우는 용어집이다. 용어집에 강등 경로가 없으면 오류가 거기서 쌓인다.

### 1.3 넘치게 만들고, 점수를 붙이고, 자르기는 읽을 때 한다

**메커니즘.** 후보는 recall 위주의 싼 규칙으로 넉넉히 만든다. 후보마다 점수를 붙인다. 문턱은 저장할 때가 아니라 읽을 때 건다. 그래서 문턱을 바꿔도 아무것도 지워지지 않는다.

**대표 출처**
- DeepDive (Shin 외, VLDB 2015). 논문. http://www.vldb.org/pvldb/vol8/p1310-shin.pdf
  "Candidate mappings are simply SQL queries with UDFs that look like low-precision but high-recall ETL scripts." `[2차 검증: 맞음]`
- DBpedia Spotlight (Mendes 외 2011). 논문. https://www.dbpedia-spotlight.org/docs/spotlight.pdf
  "we decided to employ minimal pre-filtering and postpone the selection to a user-configured post-disambiguation configuration stage." `[2차 검증: 맞음]`
- Knowledge Vault (Dong 외, KDD 2014). 논문. https://www.cs.ubc.ca/~murphyk/papers/kv-kdd14.pdf
  "KV has 1.6B triples, of which 324M have a confidence of 0.7 or higher, and 271M have a confidence of 0.9 or higher." `[2차 검증: 맞음]`
- Neo4j GDS Node Similarity. product docs. https://neo4j.com/docs/graph-data-science/current/algorithms/node-similarity/
  "Lower limit for the similarity score to be present in the result." `[2차 검증: 맞음]`
- Cognee cross_connect_entities. GitHub. https://github.com/topoteretes/cognee/blob/main/cognee/tasks/memify/cross_connect_entities.py
  "# Inferred edges start with a low feedback weight so they can be told apart from # extraction-time relationships and pruned first if they turn out to be noise." `[2차 검증: 맞음]`
- Splink predict와 clustering. product docs. https://moj-analytical-services.github.io/splink/demos/tutorials/05_Predicting_results.html
  "which will drop any row where the predicted score is below the threshold." `[2차 검증: 맞음]`
- Alignment API cut과 harden. product docs. https://moex.gitlabpages.inria.fr/alignapi/api.html
  "all correspondences whose strength is strictly greater than the argument is converted to the maximum confidence, the others being set to the minimum" `[critic만]`
- OKF 명세. 로컬에 클론한 GitHub repo. llm-wiki-implementations/lab/repos/GoogleCloudPlatform_knowledge-catalog/okf/SPEC.md
  "It does not store a credibility score: a score is subjective, unportable across consumers, and goes stale." `[2차 검증: 일부]`
- 같은 축의 출처: Retrieve & Re-Rank, spaCy EntityLinker threshold. 둘 다 `[2차 검증: 맞음]`이다.

**우리 설정에 옮기면**
- [확인] 구조가 가장 가까운 것은 DeepDive다. 용어집 co-mention 규칙이 "low-precision but high-recall" candidate mapping 자리에 그대로 들어간다.
- [추정] 링크 점수는 저장하지 않는다. 재계산할 때 신호에서 매번 계산한다. 근거는 OKF 명세 1개와, 우리가 링크를 이미 재계산한다는 점이다.
- 신호의 예는 entry의 document frequency, alias의 출처, 공유 entry 수다.
- 조회 API는 Alignment API의 `cut(t)` 모양으로 둔다. t는 precision과 recall 사이를 조절하는 다이얼이 된다.

**옮겨지지 않는 것**
- DeepDive와 Knowledge Vault의 calibration은 라벨로 학습해서 얻는다. 라벨이 없는 우리는 "p=0.9면 90%가 맞다"는 성질을 기대할 수 없다.
- 점수는 손으로 만들어야 한다.
- Cognee의 낮은 가중치는 기본 설정에서 아무 효과가 없다. 검색에 섞는 비율 default_feedback_influence가 기본으로 0.0이다. inferred 엣지를 지우는 코드도 저장소에 없다.
- Splink는 predict 단계에서 이미 문턱 아래 행을 버린다. 그래서 진짜 "읽을 때 자르기"는 아니다.

### 1.4 흔한 entry를 entry 단위로 누른다

**메커니즘.** 거의 모든 문서에 나오는 key는 쓸모없는 쌍을 대량으로 만든다. 이런 key를 통째로 빼거나 등장 빈도로 가중치를 깎는다. key 단위로 한 번만 정하면 그 key가 만든 링크가 모두 따라 움직인다.

**대표 출처**
- Meta-blocking과 Block Purging (Papadakis 외, TKDE13; Gagliardelli 외, arXiv 2204.08801). 논문. https://arxiv.org/html/2204.08801
  "Block Purging ... discards all the blocks that contain more than half of the entity profiles in the collection in a parameter-free way." `[2차 검증: 맞음]`
- Adamic-Adar index (NetworkX). product docs. https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_prediction.adamic_adar_index.html
  "∑_{w ∈ Γ(u) ∩ Γ(v)} 1/log|Γ(w)|" `[2차 검증: 일부]`
- Mem0 OSS entity boost. GitHub. https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py
  `memory_count_weight = 1.0 / (1.0 + 0.001 * ((num_linked - 1) ** 2))` `[2차 검증: 일부]`
- Ar9av session_index의 DF 상한. 로컬에 클론한 GitHub repo. llm-wiki-implementations/lab/repos/Ar9av_obsidian-wiki/obsidian_wiki/session_index.py
  "Any term appearing in more than MAX_DF_RATIO of all sessions is deleted from the vocabulary outright." `[2차 검증: 일부]`
- Elasticsearch More Like This. product docs. https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-mlt-query.html
  "The maximum document frequency above which the terms will be ignored from the input document." `[2차 검증: 일부]`
- Milne & Witten (CIKM 2008). 논문. https://complexevents.com/wp-content/uploads/2008/12/cikm08-learningtolinkwithwikipedia.pdf
  "is only intended to discard nonsense phrases and stop words." `[2차 검증: 맞음]`
- DBpedia Spotlight support. 논문. https://www.dbpedia-spotlight.org/docs/spotlight.pdf
  "With the support parameter, users can specify the minimum number of inlinks a DBpedia resource has to have in order to be annotated." `[2차 검증: 맞음]`
- mindbase god_node_disambiguation. 로컬에 클론한 GitHub repo. llm-wiki-implementations/lab/repos/frankchu91_mindbase-llm-wiki 안의 suggestions.ts:92
  "${g.title} is referenced ${g.inboundCount} times, but ${ambiguousCount} of those edges are uncertain — clarify what this concept means." `[2차 검증: 일부]`
- Snorkel data programming (Ratner 외, VLDB 2017). 논문. https://arxiv.org/abs/1711.10160
  "sources will overlap and conflict, and to resolve their conflicts we need to estimate their accuracies and correlation structure, without access to ground truth." `[critic만]`
- Raad 외, Detecting Erroneous Identity Links (ISWC 2018). 논문. https://research.vu.nl/ws/files/75391299/Raad2018_Chapter_DetectingErroneousIdentityLink.pdf
  "It is subsequently used to rank identity links, allowing potentially erroneous links to be identified" `[critic만]`
- 같은 축의 출처: HippoRAG node specificity(1/등장 passage 수), Wikify keyphraseness, Gerlach 외 link probability, nashsu Adamic-Adar, Cognee IDF 가중 후보 선택. 모두 `[2차 검증: 일부]` 또는 `[2차 검증: 맞음]`이다.

**우리 설정에 옮기면**
- [확인] 구조가 같다. entry는 block이다. 같은 entry를 언급한 두 chunk는 blocking graph의 edge다.
- 링크 점수는 공유 entry마다 1/log(df)를 더한 값으로 둘 수 있다. df는 그 entry를 언급한 chunk 수다. 이것은 chunk-entry bipartite graph에 Adamic-Adar를 건 것이다.
- [확인] 계산 예를 보면 차이가 크다. 300개 chunk에 나오는 entry는 0.175를 보탠다. 2개 chunk에 나오는 entry는 1.44를 보탠다.
- 더 거친 방식도 있다. 절반이 넘는 chunk에 나오는 entry를 링크 계산에서 뺀다. 원문은 Block Purging이고 기준은 50%다. Ar9av는 45%를 쓴다.
- 이 방식은 entry를 용어집에서 지우지 않는다. 링크 계산에서만 뺀다. Elasticsearch의 max_doc_freq도 같은 모양이다.
- mindbase 규칙도 옮길 수 있다. 불확실한 링크가 한 entry에 몰리면 그 entry를 의심하라고 알린다.
- [추정] Snorkel을 옮기면 entry 하나가 labeling function 하나가 된다. 그러면 entry마다 coverage와 conflict를 계산할 수 있다. 근거는 튜토리얼의 keyword LF 1개다.

**옮겨지지 않는 것**
- link probability와 keyphraseness는 사람이 단 링크 통계가 필요하다. Milne & Witten, Gerlach, Wikify가 모두 그렇다. 우리는 document frequency로 대신해야 한다. 그 대체가 통하는지는 어느 출처도 다루지 않는다.
- 차수 기반 가중치에는 반대 방향의 함정이 있다. 드문 entry에 잘못 붙은 alias는 오히려 높은 점수를 받는다. 그래서 잘못된 alias가 만든 오류는 이 패턴으로 잡히지 않는다.
- Snorkel의 LabelModel은 LF끼리 조건부 독립에 가깝다고 가정한다. 서로 강하게 상관된 alias에서는 이 가정이 깨질 수 있다.
- Raad 방식은 그대로 옮기기 어렵다. 우리 링크는 entry마다 clique를 만든다. generic entry의 clique는 밀집 community가 된다. 그러면 오히려 error degree가 낮게 나올 수 있다.

### 1.5 지우지 말고 무효 표식과 거절 기록을 남긴다

**메커니즘.** 틀린 항목을 물리적으로 지우지 않는다. 상태를 낮추고 이유와 시각을 단다. 기본 조회는 낮춘 항목을 빼고 읽는다. 거절 기록은 같은 것이 다시 들어오는 것을 막는 근거가 된다.

**대표 출처**
- Wikidata statement rank. product docs. https://www.wikidata.org/wiki/Help:Ranking
  "Marking erroneous statements as deprecated instead of simply deleting such statements has three benefits: it allows other users to know not to re-add the value to the item" `[2차 검증: 맞음]` (두 갈래가 따로 수집했다)
- Wikimedia "Add a link"의 거절 처리 (T429417). Phabricator. https://phabricator.wikimedia.org/T429417
  "We the Growth team simply 'swallow' (and keep to ourselves) suggestions that were rejected before." `[2차 검증: 맞음]`
- Graphiti/Zep edges. GitHub. https://github.com/getzep/graphiti/blob/main/graphiti_core/edges.py
  `expired_at ... description='datetime of when the node was invalidated'` `[2차 검증: 일부]`
- Mem0 논문의 Mem0g. 논문. https://arxiv.org/html/2504.19413v1
  "marking them as invalid rather than physically removing them to enable temporal reasoning." `[2차 검증: 일부]`
- Obsidian Smart Connections. GitHub. https://github.com/brianpetro/obsidian-smart-connections
  "Right click a result to hide it from the list" `[2차 검증: 맞음]`
- openwiki wiki-link-validator. 로컬에 클론한 GitHub repo. llm-wiki-implementations/lab/repos/langchain-ai_openwiki/src/agent/wiki-link-validator.ts
  "Existing stamps are cleared first, so a fixed link leaves no residual comment." `[2차 검증: 일부]`
- Nanopublication retraction. product docs. https://nanopub.readthedocs.io/en/latest/publishing/retraction.html
  "A nanopublication is persistent, you can never edit nor delete it. You can however retract a nanopublication." `[critic만]`
- FamilySearch record hints. product docs. https://www.familysearch.org/en/help/helpcenter/article/what-do-i-do-with-record-hints-in-family-tree-that-arent-a-match
  "Dismissing prevents others from attaching the record by mistake." `[critic만]`
- MusicBrainz voting. product docs. https://musicbrainz.org/doc/Introduction_to_Voting
  "Some edits (most removals and merges) are considered \"destructive\" (meaning they're either impossible or very hard to revert)." `[critic만]`
- 같은 축의 출처: TerminusDB branch와 reset `[critic만]`, atomicstrata의 orphaned 제외 `[2차 검증: 일부]`.

**우리 설정에 옮기면**
- 표식을 둘 자리는 두 곳이다.
- 첫째는 용어집이다. entry와 alias에 상태를 단다. 예를 들면 active, deprecated, 이유, 그것을 만든 LLM 결정 id다. 재계산은 deprecated를 건너뛴다. LLM은 다음 성장 단계에서 deprecated 목록을 보고 같은 alias를 다시 넣지 않는다.
- [확인] 둘째 근거는 Wikidata 원문이다. 원문이 "다시 추가하지 않게 알린다"를 첫 번째 이점으로 든다.
- 둘째는 링크 단위의 거절 목록이다. 형태는 (chunk A, chunk B, entry)다. 재계산 결과 위에 이 목록을 필터로 건다. Wikimedia와 FamilySearch가 같은 모양이다.
- [추정] alias 결정은 두 이름을 병합하는 것과 같다. MusicBrainz는 병합을 되돌리기 어려운 작업으로 다룬다. 그래서 alias는 표식으로 끌 수 있게 두는 편이 맞다. 근거는 MusicBrainz 사례 1개다.
- openwiki에서 가져올 원칙도 있다. 의심 표시를 저장된 상태로 두지 않고, run마다 다시 계산하는 값으로 둔다.

**옮겨지지 않는 것**
- 누가 deprecated로 바꿀지가 비어 있다. Wikidata, Wikimedia, FamilySearch, Smart Connections는 모두 사람이 누른다.
- Graphiti와 Mem0g의 무효화는 LLM이 모순을 볼 때만 일어난다. generic entry가 만든 링크는 무엇과도 모순되지 않는다. 그래서 이 방식은 그런 링크에 반응하지 않는다.
- Graphiti에는 기본 검색이 무효화된 엣지를 빼지 않는 문제도 있다. issue #1728은 반환된 fact의 30%가 invalid_at을 달고 있었다고 적는다.
- 같은 issue는 표본 4건 중 3건이 오판이었다고 적는다. 잘못 무효화된 fact를 되살리는 일은 별도 작업으로 남아 있다. 표식 자체도 틀릴 수 있다는 뜻이다.
- Smart Connections의 숨김이 다시 인덱싱한 뒤에도 남는지는 README에 없다.

### 1.6 쓰이면 강화하고 안 쓰이면 감쇠한다

**메커니즘.** 처음에는 링크나 항목을 약한 가중치로 둔다. 검색에서 함께 쓰이면 가중치가 오른다. 쓰이지 않으면 시간에 따라 내려간다. 지우는 것은 아주 약해진 경우뿐이다.

**대표 출처**
- MemoryOS (arXiv 2506.06326). 논문. https://arxiv.org/html/2506.06326v1
  "When the length of segments exceeds the maximum capacity, segments with the lowest heat are evicted." `[2차 검증: 일부]`
  같은 검증에서 Generative Agents(arXiv 2304.03442)의 "Our decay factor is 0.995"도 확인했다.
- rohitg00 LLM Wiki v2 gist. 로컬에 저장한 gist. llm-wiki-implementations/lab/sources/rohitg00-llm-wiki-v2-gist/llm-wiki.md
  "Not deleted, but deprioritized." `[2차 검증: 일부]`
- HeLa-Mem (arXiv 2604.16839). 논문. https://arxiv.org/html/2604.16839
  "this strict compound criterion ensures that the system selectively removes noise while preserving strong, albeit older, associations." `[critic만]`
- Learning Webs (Bollen & Heylighen). 블로그. https://pespmc1.vub.ac.be/LEARNWEB.html
  "The frequency rule that reinforces a link from document A to document B each time a user moves from A to B." `[critic만]`
- 같은 축의 출처: Cognee의 평점 기반 feedback_weight 이동평균 `[2차 검증: 맞음]`.

**우리 설정에 옮기면**
- [추정] 검색이나 평가 질의에서 함께 쓰인 chunk 쌍의 가중치를 올릴 수 있다. 그러면 아무도 쓰지 않는 generic 링크가 상대적으로 가라앉는다. 사례는 2개다(HeLa-Mem, Learning Webs).

**옮겨지지 않는 것**
- 여섯 패턴 중 가장 덜 맞는다.
- 모든 출처가 사용 로그를 신호로 쓴다. 우리에게는 질의 기록이 거의 없다.
- 가중치는 상태다. 그래서 별도 저장소가 생긴다. 링크를 저장하지 않는 지금 구조와 부딪힌다.
- HeLa-Mem 감쇠식의 표기는 원문에서 다시 확인하지 못했다.
- Ar9av의 decay는 링크가 아니라 session 노드에 걸린다. 그래서 링크 감쇠의 근거로 쓸 수 없다.

---

## 2. 우리 설정에 이미 있는 것과 없는 것

### 이미 있는 것
- [확인] 링크는 용어집에서 다시 계산된다. 그래서 entry나 alias를 빼면 그것에 기댄 링크가 다음 재계산에서 빠진다. #1.1의 Counting과 DRed가 주는 효과를 이미 공짜로 얻는다.
- [확인] LLM은 링크를 직접 저장하지 않는다. 그래서 A-MEM과 GraphRAG #2590처럼 링크가 쌓이기만 하는 문제를 피한다.
- [확인] word-boundary 매칭은 recall 1.00이다. #1.3의 high-recall candidate mapping 자리를 이미 채운다. spaCy로 보면 get_candidates 단계에 해당한다. 우리는 거기서 멈춘다.

### 없는 것

| 빠진 것 | 해당 패턴 | 없어서 생기는 일 |
|---|---|---|
| 링크마다 붙는 상태(후보, 확정, 거절) | #1.2, #1.5 | 틀린 링크 하나만 끌 방법이 없다. 끄려면 entry를 지워야 하고, 그러면 맞는 링크도 함께 사라진다. |
| entry마다 붙는 가중치(df 등) | #1.4, #1.3 | PDF, arXiv, "user"가 희귀 entry와 같은 무게로 링크를 만든다. |
| 출처 기록: 링크→(entry, alias), entry와 alias→LLM 결정·문서·시각 | #1.1 | 틀린 링크가 어느 LLM 결정에서 왔는지 거꾸로 찾을 수 없다. |
| 용어집 쪽 표식(deprecated와 이유) | #1.5 | LLM이 버린 alias를 다음 성장 단계에서 다시 넣을 수 있다. 이 일이 실제로 일어나는지는 아래 "모르는 것"에 적었다. |
| 사용 신호 | #1.6 | 강화와 감쇠를 할 수 없다. |

- [확인] NELL에서 얻을 교훈은 링크보다 용어집에 걸린다. NELL에서 오류가 쌓이는 곳은 강등 경로가 없는 KB다. 우리 구조에서 그 자리는 LLM이 혼자 키우는 용어집이다. 측정값도 같은 방향이다. 성장 뒤 precision은 0.44에서 0.27, 0.20으로 내려갔다.
- 모르는 것: 지금 성장 로그에 discard 결정이 이유와 함께 남는지 나는 모른다. 성장 파이프라인의 출력 파일을 보면 알 수 있다.

---

## 3. 다음에 돌릴 가장 싼 실험 두 개

### 실험 1: entry별 df 가중치를 읽을 때 계산한다 (#1.4와 #1.3)
- 점수는 score(A, B) = Σ 1/log(df_e)로 둔다. 합은 A와 B가 공유한 entry e 전부에 대해 구한다.
- 비교군은 둘이다. 하나는 절반이 넘는 chunk에 나오는 entry를 빼는 Block Purging이다. 다른 하나는 45%를 기준으로 하는 Ar9av의 상한이다.
- 문턱을 바꿔 가며 잰다.
- 저장 구조는 바뀌지 않는다. LLM 호출도 없다. 재계산 함수 하나만 바꾼다.
- 지표 1: 세 용어집(원래 용어집, 성장 두 단계)마다 precision-recall 곡선을 그린다. recall을 0.9 이상으로 유지할 때의 precision을 지금 값과 비교한다. 지금 값은 recall 1.00에서 0.44, 0.27, 0.20이다.
- 지표 2: 남은 오류를 원인별로 나눈다. 원인은 generic entry와 잘못된 alias 두 가지다.
- [추정] 남은 오류는 대부분 잘못된 alias일 것이다. 사례 2개에서 끌어냈다. Adamic-Adar 항목이 드문 entry의 잘못된 alias가 높은 점수를 받는다고 지적한다. Meta-blocking 항목도 잘못된 alias의 block은 purging으로 잡히지 않는다고 지적한다. 이 비율이 크면 실험 2가 필요하다.

### 실험 2: 링크에 출처를 달고, LLM 결정 단위로 철회 효과를 잰다 (#1.1과 #1.5)
- 재계산할 때 링크마다 (entry, alias, 그 alias를 만든 LLM 결정 id)를 붙인다.
- 정답 링크로 결정마다 틀린 링크 수를 센다.
- 지표 1: 오류가 얼마나 몰려 있는지 잰다. 예를 들어 틀린 링크 중 몇 %가 가장 나쁜 결정 10%에서 오는지 본다.
- 지표 2: 가장 나쁜 결정 k개를 철회했을 때 precision이 어떻게 오르는지 본다. k는 1, 5, 10으로 둔다.
- 이 실험은 정답 라벨을 쓴다. 그래서 결과는 상한선이다. 자동 탐지기를 만들기 전에 결정 단위 철회가 효과가 있을지를 알려 준다.
- 오류가 몰려 있으면 #1.5를 들일 근거가 선다. 용어집에 deprecated 표식을 두고 성장 단계에 tombstone을 넘기는 구조다.
- 그때 함께 잴 것은 재추가 비율이다. tombstone이 있을 때와 없을 때 LLM이 버린 alias를 다시 넣는 비율을 비교한다.
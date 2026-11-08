---
tech: llm-wiki (jonex·AutoSci·sage-wiki·GD4AI)
slug: llm-wiki-four-repos
status: cycling
task: "이 레포들이 확인한 각 방식을 보고 우리 시스템에는 어떻게 입힐지 구상을 할 수 있었으면 해."
sessions: [2026-10-11]
---

## 줄기
- 추측 — 왜 갈라졌나: "카파시 원형이 구체적이지 않고, 이 구조가 모든 원문들을 저장하고 잘 볼 수 있는 구조가 아님."
- 추측 — 그 문제가 사내 보고서에도 있나: "네"
- 추측 — 그때 대안: "임베딩과 벡터 서치 RAG"
- 출처: Karpathy, LLM Wiki gist (2026-04-04), `../llm-wiki-implementations/lab/sources/karpathy-llm-wiki-gist/llm-wiki.md`
  - 9줄: "Most people's experience with LLMs and documents looks like RAG: you upload a collection of files, the LLM retrieves relevant chunks at query time, and generates an answer. This works, but the LLM is rediscovering knowledge from scratch on every question. There's no accumulation."
  - 29줄: "**Raw sources** — your curated collection of source documents. Articles, papers, images, data files. These are immutable — the LLM reads from them but never modifies them. This is your source of truth."
  - 31줄: "**The wiki** — a directory of LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, an overview, a synthesis. The LLM owns this layer entirely. It creates pages, updates them when new sources arrive, maintains cross-references, and keeps everything consistent. You read it; the LLM writes it."
  - 47줄: "When answering a query, the LLM reads the index first to find relevant pages, then drills into them. This works surprisingly well at moderate scale (~100 sources, ~hundreds of pages) and avoids the need for embedding-based RAG infrastructure."
  - 75줄: "This document is intentionally abstract. It describes the idea, not a specific implementation. The exact directory structure, the schema conventions, the page formats, the tooling — all of that will depend on your domain, your preferences, and your LLM of choice."
- 출처: jonex, `jonex:domain/engine/compile/organization.py:361-364` (`project_page` docstring) — "No LLM rewrites the page: the body is the ordered list of the claims the evidence gate already accepted, one bullet each, deduplicated by text. Order is the order the records arrived in (stable input order), not completion order and not an alphabetical reshuffle of someone's prose."
- 출처: sage-wiki, commit `f4fd525` (`sage-wiki.md` #결정 13 인용) — "Article frontmatter was duplicated ~60% of the time because the prompt asked the LLM to generate it ... Redesign: ground-truth fields ... are always code-generated."
- 대목과 견준 뒤 (2026-10-11): "wiki로 나누기 위해 먼저 여기서는 재탐색은 할 수 있되, 일반적인 RAG처럼 청크를 나누고 그것을 가져오는 것이 아닌 어떤 가공을 하여 바로 찾아오기를 원해. 그래야 vector search를 할 때도 더 유의미할거라 생각해."
- 읽기 전 물음 (2026-10-11): "jonex는 글의 주장들을 뽑고 그 주장에 글머리를 다는 형식인거 같아 맞을까? sage-wiki는 코드로 관리한다는데 그게 어떤 방식인지 모르겠어."
- 읽기 전 물음 (2026-10-12): "jonex의 방식이면 어느정도 주장이 맞다는 걸 볼 수 있다고 보는데, 그럼 이 주장들을 임베딩하는거야?"
- 읽기 전 물음 (2026-10-12): "주장들을 최상단에 두고 주장들 모두를 임베딩하는 것도 아니고 그냥 페이지야? 그럼 주장은 왜 있는거야?"
- 읽기 전 물음 (2026-10-12): "주장 묶음 페이지에 들어간 주장들은 각각 어디서 온것들이고, 이것들은 어떤 단위로 어떤 디렉토리 구조로 묶여 있어."
- 읽기 전 물음 (2026-10-12): "아직 이해할 수가 없어. 이렇게 하면 주장은 언제 쓰이는거야?"
- 읽기 전 물음 (2026-10-12): "text에 주장만을 두는 게 더 좋지 않아? 왜 텍스트 앞만 잘라서 두는걸까? chunk로 결국 다 나누는거야? 1,2,3,4.."
- 읽기 전 물음 (2026-10-12): "passage에 chunk가 있잖아. 그러니까 '생산팀 passage'가 여러개 만들어질 수 있다는거야?"
- 읽기 전 물음 (2026-10-12): "facts가 만들어지는데, facts는 어떻게 만들어지는거고, 왜 만드는거야?"
- 읽기 전 물음 (2026-10-12): "예전 방식과 지금 방식에서 llm이 어떻게 쓰이는지 모르겠어. 그냥 어떻게 저 2개를 활용하는지 모르겠어."
- 읽기 전 물음 (2026-10-13): "이해가 아직 되지 않아. factor들이 잇고 이것도 두번째에서 이전것과 묶이는데. 어떻게 저장하길래 그걸 가져올 수 잇고 묶일 수 잇는지."
- 생각 (2026-10-12): "지금 내 생각은 페이지는 임베딩할 필요없이 factor에 연결만 시켜두면 되지 않나 해."

## 과제
- 하려는 것: 이 레포들이 확인한 각 방식을 보고 우리 시스템에는 어떻게 입힐지 구상을 할 수 있었으면 해.

## 지도
| # | 기제 | 숨은 상태 | 관측할 것 | 상태 |
|---|---|---|---|---|

## 회차

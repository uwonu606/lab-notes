# llm-wiki 구현 조사 — lab

Karpathy의 llm-wiki 아이디어를 구현한 repo 10개와 포맷 스펙 하나를 코드 수준에서 비교한 자료다.
내 llm-wiki repo를 설계하기 전에 구조·방식·장단점을 파악하려고 모았다.

## 읽는 순서

1. `reports/00-comparison.md` — 축 16개로 본 비교, repo별 장단점, 설계 때 정할 결정 지도.
2. `reports/<repo>.md` — repo 하나의 한 바퀴 흐름과 축별 분석. 끝의 `## 검증 기록`은 반박 검증이 고친 내용이다.
3. `reports/00-discovery.md` — 후보 55개에서 이 세트를 고른 근거와 제외한 repo 목록.

보고서의 `path:line`은 아래 clone 기준이다.
보고서는 코드를 읽고 쓴 것이고, 어떤 repo도 실행하지 않았다.

## repos/ — 참고 저장소 (gitignore 됨)

다시 받을 때는 `repos/`에서 실행한다.

```sh
for r in frankchu91/mindbase-llm-wiki inkeep/open-knowledge Astro-Han/karpathy-llm-wiki \
         Ar9av/obsidian-wiki atomicstrata/llm-wiki-compiler langchain-ai/openwiki \
         AgriciDaniel/claude-obsidian kfchou/wiki-skills nashsu/llm_wiki \
         GoogleCloudPlatform/knowledge-catalog cablate/llm-atomic-wiki; do
  git clone --depth 1 "https://github.com/$r.git" "$(echo "$r" | tr / _)"
done
```

| 디렉터리 | 분석 시점 commit | 라이선스 | 먼저 볼 파일 |
|---|---|---|---|
| `Astro-Han_karpathy-llm-wiki` | eafcc77 | MIT | `SKILL.md`, `scripts/check_evidence.py`, README "Design Boundaries" |
| `Ar9av_obsidian-wiki` | df54595 | MIT | `docs/architecture.md`, `obsidian_wiki/cli.py` |
| `frankchu91_mindbase-llm-wiki` | c5273d2 | MIT | `packages/core` |
| `inkeep_open-knowledge` | 7e67576 | GPL-3.0 | `docs/content/workflows/karpathy-llm-wiki.mdx`, `packages/server/assets/skills/packs/knowledge-base/SKILL.md` |
| `atomicstrata_llm-wiki-compiler` | a3eb447 | MIT | `src/compiler/prompts.ts`, `.llmwiki/profile.json` 처리 코드 |
| `langchain-ai_openwiki` | 27b3c76 | MIT | `src/`, `evals/` |
| `AgriciDaniel_claude-obsidian` | 32ac5a0 | MIT | `claude_obsidian/transaction.py` |
| `kfchou_wiki-skills` | d9267ec | MIT | `skills/`, `tests/` |
| `nashsu_llm_wiki` | 48fd970 | GPL-3.0 | README "What We Kept / What We Changed", `src-tauri/` |
| `GoogleCloudPlatform_knowledge-catalog` | 58b3370 | Apache-2.0 | `okf/SPEC.md` |
| `cablate_llm-atomic-wiki` | eaf5e1d | 없음 | `METHODOLOGY.md` |

GPL-3.0 두 곳은 설계만 참고한다.
cablate는 라이선스가 없어서 코드를 가져올 수 없다.

## sources/ — 비교 기준 자료

| 파일 | 내용 |
|---|---|
| `karpathy-llm-wiki-gist/llm-wiki.md` | 원본 idea file (gist 442a6bf5…, 2026-04-04) |
| `frosk1-critique-comments.md` | 원본 gist 댓글 중 frosk1이 든 한계 7가지 |
| `rohitg00-llm-wiki-v2-gist/llm-wiki.md` | confidence·supersession·망각을 더한 확장 idea file |

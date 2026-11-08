# lab

`repos/` 에 참고 저장소 클론을 둔다. 커밋하지 않는다(.gitignore). 없으면 다시 받는다:

```bash
git clone https://github.com/mattpocock/skills repos/mattpocock-skills
git clone https://github.com/cursor/plugins repos/cursor-plugins
```

- poteto 의 커밋·PR 규칙: `repos/cursor-plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md` (7·13·27번 줄)
- Matt 의 저장소 규칙: `repos/mattpocock-skills/CLAUDE.md`, `.changeset/`

`diagrams/` 에 poteto 규칙을 옮긴 그림이 있다. SVG 다섯 장(`01`~`05`)과 그것을 모은 `poteto-commit-flow.html`. 아티팩트: https://claude.ai/artifact/PNmap6m8PqgGaygSqeVNWm
`notes.md` 의 줄기 절이 이 그림들을 원문 대목 옆에 끼워 넣는다.
`diagrams/g1`~`g6` 는 git 의 구조(물건과 이름표)를 그린 것. 모은 페이지 `git-objects-and-labels.html`.
`diagrams/g7`~`g11` 은 squash 와 merge commit 의 차이. 모은 페이지 `squash-vs-merge.html`.

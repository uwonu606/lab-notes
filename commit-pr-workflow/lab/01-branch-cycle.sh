#!/usr/bin/env bash
# 회차 1. 브랜치에서 wip 커밋 7개 → rebase 로 4개 → squash merge 로 main 에 1개.
# 단계마다 브랜치·main 의 커밋 목록과, 원래 7개 커밋 객체가 남아 있는지를 찍는다.
# 뺀 것: 원격 없음, PR 없음(squash merge 는 GitHub 기본 방식을 손으로 흉내), CI 없음.
set -euo pipefail

work=$(mktemp -d)
cd "$work"
git init -q -b main
git config user.name lab; git config user.email lab@example.com
git config core.hooksPath /dev/null

say() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
count() { git rev-list --count "$1"; }

echo "seed" > seed.txt; git add .; git commit -qm "chore: seed"
say "시작. main 의 커밋 수: $(count main)"

git switch -qc feature
echo "feature v1"   > feature.txt; git add .; git commit -qm "wip"
echo "feature v2"   > feature.txt; git add .; git commit -qm "wip"
echo "feature v3"   > feature.txt; git add .; git commit -qm "fix"
echo "feature docs" > README.md;   git add .; git commit -qm "wip"
echo "feature docs, clearer" > README.md; git add .; git commit -qm "docs"
echo "feature v3 (renamed helper)" > feature.txt; git add .; git commit -qm "oops"
echo "feature v3 (renamed helper, empty input ok)" > feature.txt; git add .; git commit -qm "fix"

say "① 브랜치에서 아낌없이 커밋. feature 의 커밋 수: $(count main..feature)"
git log --oneline main..feature
mapfile -t old < <(git rev-list --reverse main..feature)

say "② rebase. 7개를 4개로 다시 짠다 (todo 를 미리 써서 편집기 없이)"
todo=$(cat <<T
pick ${old[0]}
fixup ${old[1]}
fixup ${old[2]}
exec git commit --amend -qm "feat(lab): add feature"
pick ${old[3]}
fixup ${old[4]}
exec git commit --amend -qm "docs(lab): describe feature"
pick ${old[5]}
exec git commit --amend -qm "refactor(lab): rename helper"
pick ${old[6]}
exec git commit --amend -qm "fix(lab): handle empty input"
T
)
GIT_SEQUENCE_EDITOR="printf '%s\n' \"\$todo\" >" todo="$todo" git rebase -qi main 2>/dev/null || {
  # 일부 git 은 위 한 줄 방식이 안 먹는다. 파일로 우회.
  printf '%s\n' "$todo" > "$work/todo"
  GIT_SEQUENCE_EDITOR="cp $work/todo" git rebase -qi main
}
echo "feature 의 커밋 수: $(count main..feature)"
git log --oneline main..feature

say "   숨은 상태: 원래 7개 커밋 객체는 어디 갔나"
for h in "${old[@]}"; do
  printf '   %s  객체 있음? %s   어느 브랜치에 속함? %s\n' "${h:0:7}" "$(git cat-file -t "$h" 2>/dev/null || echo 없음)" "$(git branch --contains "$h" 2>/dev/null | tr -d ' *\n' || true)"
done
echo "   reflog 의 feature 이력 (최근 3줄):"; git reflog show feature | head -3 | sed 's/^/   /'

say "③ PR 열기 → ④ squash merge (GitHub 기본: 제목 = PR 제목, 본문 = 브랜치 커밋 메시지들을 '* ' 로 이음)"
git switch -q main
git merge -q --squash feature
{
  echo "feat(lab): add feature (#1)"
  echo
  git log --reverse --format='* %s%n%n%b' main..feature
} > "$work/msg"
git commit -qF "$work/msg"
echo "main 의 커밋 수: $(count main)"
git log --oneline main
say "   main 맨 위 커밋의 본문"
git show -s --format=%B main | sed 's/^/   /'
say "   squash 뒤 feature 는 그대로인가. main..feature 의 커밋 수: $(count main..feature), feature..main 의 커밋 수: $(count feature..main)"
git log --oneline --graph --all | head -12

echo; echo "(임시 저장소: $work)"

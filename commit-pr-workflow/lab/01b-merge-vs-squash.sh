#!/usr/bin/env bash
# 회차 1 변형. 같은 feature(4개)를 merge commit 과 squash merge 로 각각 얹어 main 의 상태를 나란히 본다.
set -euo pipefail
work=$(mktemp -d); cd "$work"
git init -q -b main; git config user.name lab; git config user.email lab@example.com
echo seed > seed.txt; git add .; git commit -qm "chore: seed"
git switch -qc feature
for m in "feat(lab): add feature" "docs(lab): describe feature" "refactor(lab): rename helper" "fix(lab): handle empty input"; do
  echo "$m" >> f.txt; git add .; git commit -qm "$m"
done
git switch -q main
git branch -q main-merge; git branch -q main-squash

show() {
  printf '\n== %s ==\n' "$1"
  printf 'main 의 커밋 수: %s\n' "$(git rev-list --count "$1")"
  printf '맨 위 커밋의 부모 수: %s   (부모: %s)\n' "$(git rev-list --parents -n1 "$1" | wc -w | awk '{print $1-1}')" "$(git log -1 --format=%p "$1")"
  printf 'main..feature: %s    feature..main: %s\n' "$(git rev-list --count "$1..feature")" "$(git rev-list --count "feature..$1")"
  printf 'git branch --contains <feature 의 fix 커밋>: [%s]\n' "$(git branch --contains feature | tr -d ' *' | tr '\n' ' ')"
  git log --oneline --graph "$1" feature | head -8
}

git switch -q main-merge;  git merge -q --no-ff -m "Merge pull request #1 from feature" feature
git switch -q main-squash; git merge -q --squash feature >/dev/null; git commit -qm "feat(lab): add feature (#1)"
show main-merge
show main-squash
printf '\n== 브랜치를 지운 뒤 (GitHub 이 squash 뒤 자동으로 하는 일) ==\n'
fix=$(git rev-parse feature); git branch -qD feature
printf 'main-merge  에서 fix 커밋에 닿는가: %s\n' "$(git merge-base --is-ancestor $fix main-merge && echo 닿음 || echo 안닿음)"
printf 'main-squash 에서 fix 커밋에 닿는가: %s\n' "$(git merge-base --is-ancestor $fix main-squash && echo 닿음 || echo 안닿음)"
printf 'fix 커밋 객체는 있는가: %s   (reflog: %s)\n' "$(git cat-file -t $fix)" "$(git reflog show --all | grep -c "$(git rev-parse --short $fix)" || true)건"

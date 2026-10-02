#!/usr/bin/env bash
# Commit local changes (if any) and push the current branch to origin.
#
# Usage:
#   ./scripts/push.sh
#   ./scripts/push.sh "your commit message"
#   GIT_REMOTE=origin ./scripts/push.sh "msg"
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/push.sh [commit message]

Stages all changes, commits when needed, then pushes the current branch
to origin (or $GIT_REMOTE). Default message: "chore: update <time>".
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not a git repository: $ROOT" >&2
  exit 1
fi

branch="$(git branch --show-current)"
if [[ -z "$branch" ]]; then
  echo "error: detached HEAD; checkout a branch first" >&2
  exit 1
fi

remote="${GIT_REMOTE:-origin}"
if ! git remote get-url "$remote" >/dev/null 2>&1; then
  echo "error: remote '$remote' not found" >&2
  exit 1
fi

if [[ "$#" -gt 0 ]]; then
  msg="$*"
else
  msg="chore: update $(date '+%Y-%m-%d %H:%M')"
fi

git add -A

if [[ -n "$(git status --porcelain)" ]]; then
  git commit -m "$msg"
  echo "committed: $msg"
else
  echo "nothing to commit"
fi

upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [[ -z "$upstream" ]]; then
  echo "pushing $branch → $remote (setting upstream)"
  git push -u "$remote" "HEAD"
else
  ahead="$(git rev-list --count "$upstream..HEAD")"
  if [[ "$ahead" -gt 0 ]]; then
    echo "pushing $branch → $remote ($ahead commit(s))"
    git push "$remote" "HEAD"
  else
    echo "already up to date with $upstream"
  fi
fi

git status -sb

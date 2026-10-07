#!/usr/bin/env bash
# Commit local changes (if any), push the current branch to origin, then sync
# Notes/Projects into jiangbyte.github.io on branch sync/content.
# Site repo workflow merges that branch into main and deploys.
#
# Usage:
#   ./scripts/push.sh
#   ./scripts/push.sh "your commit message"
#   SITE_DIR=~/path/to/jiangbyte.github.io ./scripts/push.sh
#   SKIP_SITE_SYNC=1 ./scripts/push.sh "msg"
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/push.sh [commit message]

Stages all changes, commits when needed, pushes the current branch to
origin (or $GIT_REMOTE), then syncs Notes/Projects into the local
jiangbyte.github.io checkout on branch sync/content (Hugo-checked) and
pushes that branch so the site workflow can merge → deploy.

Env:
  GIT_REMOTE       push remote (default: origin)
  SITE_DIR         path to jiangbyte.github.io
                   (default: ../jiangbyte.github.io next to this repo)
  SITE_SYNC_BRANCH branch name on the site repo (default: sync/content)
  SKIP_SITE_SYNC   set to 1 to only push this repo
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

# Frontmatter before commit so Notes are publish-ready.
python3 "$ROOT/scripts/add_frontmatter.py"

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

if [[ "${SKIP_SITE_SYNC:-0}" == "1" ]]; then
  echo "SKIP_SITE_SYNC=1 — not syncing site repo"
  exit 0
fi

SITE_DIR="${SITE_DIR:-$ROOT/../jiangbyte.github.io}"
if [[ ! -d "$SITE_DIR/.git" ]]; then
  echo "error: site repo not found: $SITE_DIR" >&2
  echo "set SITE_DIR to your jiangbyte.github.io checkout" >&2
  exit 1
fi
SITE_DIR="$(cd "$SITE_DIR" && pwd)"
SITE_SYNC_BRANCH="${SITE_SYNC_BRANCH:-sync/content}"

if ! command -v hugo >/dev/null 2>&1; then
  echo "error: hugo not found in PATH (needed to verify sync before push)" >&2
  exit 1
fi

echo "syncing Notes/Projects → $SITE_DIR ($SITE_SYNC_BRANCH)"

(
  cd "$SITE_DIR"
  git fetch origin
  git checkout main
  git pull --ff-only origin main
  git checkout -B "$SITE_SYNC_BRANCH"

  python3 scripts/sync_notes.py "$ROOT/Notes"
  python3 scripts/sync_projects.py "$ROOT/Projects"

  echo "verifying Hugo build…"
  hugo --minify

  # Content + pipeline files (so sync/content carries merge/deploy workflows).
  git add -A -- \
    content/posts \
    content/projects \
    .github/workflows/deploy.yml \
    .github/workflows/merge-content.yml \
    .gitignore \
    README.md

  if [[ -n "$(git status --porcelain -- \
      content/posts content/projects \
      .github/workflows/deploy.yml \
      .github/workflows/merge-content.yml \
      .gitignore README.md)" ]]; then
    sync_msg="content: sync from jiangbyte $(date '+%Y-%m-%d %H:%M')"
    git commit -m "$sync_msg"
    echo "site committed: $sync_msg"
  else
    echo "site content already up to date"
  fi

  echo "pushing $SITE_SYNC_BRANCH → origin"
  git push -u origin "HEAD:$SITE_SYNC_BRANCH" --force-with-lease
  git status -sb
)

echo "done — site workflow will merge $SITE_SYNC_BRANCH into main and deploy"

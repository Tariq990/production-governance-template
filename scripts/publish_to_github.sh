#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/publish_to_github.sh <repository-url>" >&2
  exit 2
fi

repository_url="$1"
branch="$(git branch --show-current)"

if [[ "$branch" != "main" ]]; then
  echo "Expected branch 'main', found '$branch'." >&2
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$repository_url"
else
  git remote add origin "$repository_url"
fi

git push -u origin main
echo "Published to $repository_url"

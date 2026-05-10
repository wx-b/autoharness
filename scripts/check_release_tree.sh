#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

tracked_or_new="$(mktemp)"
content_hits="$(mktemp)"
trap 'rm -f "$tracked_or_new" "$content_hits"' EXIT

{
  git ls-files
  git ls-files --others --exclude-standard
} | sort -u >"$tracked_or_new"

if grep -E '^(dist|build|tmp|artifacts|temp)/' "$tracked_or_new" >/dev/null; then
  echo "Release tree contains local output paths:"
  grep -E '^(dist|build|tmp|artifacts|temp)/' "$tracked_or_new"
  exit 1
fi

content_markers='/Users/[[:alnum:]_.-]+|/home/[[:alnum:]_.-]+|[A-Za-z]:\\Users\\'
if rg -n "$content_markers" --glob '!tmp/**' --glob '!dist/**' --glob '!build/**' --glob '!scripts/check_release_tree.sh' . >"$content_hits"; then
  echo "Release tree contains local machine paths:"
  cat "$content_hits"
  exit 1
fi

echo "Release tree OK"

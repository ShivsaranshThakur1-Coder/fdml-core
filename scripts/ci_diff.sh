#!/usr/bin/env bash
set -euo pipefail
RID=$(gh run list --workflow CI -L 1 --json databaseId -q '.[0].databaseId')
SHA=$(gh run view "$RID" --json headSha -q '.headSha')
echo "CI_SHA=$SHA"
git fetch origin
echo "HEAD=$(git rev-parse HEAD)"
git diff --name-status "$SHA"..HEAD || true

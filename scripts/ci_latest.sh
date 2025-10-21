#!/usr/bin/env bash
set -euo pipefail
RUN=$(gh run list --workflow CI -L 1 --json databaseId,headSha,headBranch,conclusion,startedAt,updatedAt -q '.[0]')
echo "$RUN"
RID=$(echo "$RUN" | sed -n 's/.*"databaseId":[ ]*\([0-9]*\).*/\1/p')
echo "RUN_ID=$RID"
gh run view "$RID" --json jobs -q '.jobs[] | "\(.databaseId)\t\(.name)\t\(.conclusion)"'

#!/usr/bin/env bash
set -euo pipefail
RID=$(gh run list --workflow CI -L 1 --json databaseId -q '.[0].databaseId')
IDS=$(gh run view "$RID" --json jobs -q '.jobs[].databaseId')
for JID in $IDS; do
  echo "==== JOB $JID ===="
  gh run view "$RID" --job "$JID" --log | tail -n ${1:-200}
done

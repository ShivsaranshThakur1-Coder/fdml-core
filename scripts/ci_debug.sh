#!/usr/bin/env bash
set -euo pipefail
RUN_JSON=$(gh run list --workflow CI -L 1 --json databaseId,headSha,headBranch,conclusion,startedAt,updatedAt -q '.[0]')
echo "RUN=$RUN_JSON"
RUN_ID=$(echo "$RUN_JSON" | sed -n 's/.*"databaseId":[ ]*\([0-9]*\).*/\1/p')
echo "RUN_ID=$RUN_ID"
echo "JOBS:"
gh run view "$RUN_ID" --json jobs -q '.jobs[] | "\(.databaseId)\t\(.name)\t\(.conclusion)"'
FAIL_ID=$(gh run view "$RUN_ID" --json jobs -q '.jobs[] | select(.conclusion=="failure") | .databaseId' | head -n1)
if [ -z "${FAIL_ID:-}" ]; then
  JOB_ID=$(gh run view "$RUN_ID" --json jobs -q '.jobs[] | select(.name=="build") | .databaseId' | head -n1)
else
  JOB_ID="$FAIL_ID"
fi
echo "JOB_ID=$JOB_ID"
echo "----- LOG TAIL -----"
gh run view "$RUN_ID" --job "$JOB_ID" --log | tail -n 300
echo "----- ERROR GREP -----"
OUTDIR="out/ci-logs-$RUN_ID"
mkdir -p "$OUTDIR"
set +e
gh run download "$RUN_ID" -D "$OUTDIR" >/dev/null 2>&1
set -e
if compgen -G "$OUTDIR/**/*.txt" > /dev/null 2>&1; then
  find "$OUTDIR" -type f -name '*.txt' -maxdepth 3 -print
  grep -RInE "##\\[error\\]|FAIL|SCH FAIL|cvc-|XPST0003|SXXP0003|COMPILATION ERROR" "$OUTDIR" | tail -n 120 || true
else
  echo "No artifacts to download"
fi
echo "----- CI SHA VS LOCAL -----"
SHA=$(gh run view "$RUN_ID" --json headSha -q '.headSha'); echo "CI_SHA=$SHA"
git fetch origin >/dev/null 2>&1 || true
echo "HEAD=$(git rev-parse HEAD)"
git diff --name-status "$SHA"..HEAD || true

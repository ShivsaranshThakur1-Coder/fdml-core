#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="${1:-site}"
DST_DIR="${2:-pages}"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "sync_pages_snapshot.sh: missing source dir: $SRC_DIR" >&2
  echo "Run: make html" >&2
  exit 1
fi

rm -rf "$DST_DIR"
mkdir -p "$DST_DIR"
cp -R "$SRC_DIR"/. "$DST_DIR"/

echo "Synced $SRC_DIR -> $DST_DIR"

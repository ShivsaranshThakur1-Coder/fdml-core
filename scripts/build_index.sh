#!/usr/bin/env bash
set -euo pipefail
repo_path="/fdml-core"
ver="${1:-nocache}"
out="out/html/index.html"
{
  echo '<!doctype html><meta charset="utf-8"><title>FDML Cards</title><h1>FDML Cards</h1><ul>'
  for f in out/html/*.html; do
    b=$(basename "$f")
    printf '<li><a href="%s/%s?v=%s">%s</a></li>\n' "$repo_path" "$b" "$ver" "$b"
  done
  echo '</ul>'
} > "$out"

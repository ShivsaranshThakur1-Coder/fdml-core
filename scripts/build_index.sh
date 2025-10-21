#!/usr/bin/env bash
set -euo pipefail
out="out/html"
{
  echo '<!doctype html><meta charset="utf-8"><title>FDML Cards</title><h1>FDML Cards</h1><ul>'
  for f in "$out"/*.html; do
    b="$(basename "$f")"
    echo "<li><a href=\"$b\">$b</a></li>"
  done
  echo '</ul>'
} > "$out/index.html"

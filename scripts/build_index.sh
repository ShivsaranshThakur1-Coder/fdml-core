#!/usr/bin/env bash
set -euo pipefail
V="${1:-nocache}"
OUT="site"
rm -rf "$OUT"
mkdir -p "$OUT" "$OUT/cards"
cp -f out/html/*.html "$OUT/"
cp -f out/html/*.html "$OUT/cards/"
cp -f docs/style.css "$OUT/style.css"
cp -f docs/style.css "$OUT/cards/style.css"
{
  printf '%s\n' '<!doctype html><meta charset="utf-8"><title>FDML Cards</title>'
  printf '%s\n' '<link rel="stylesheet" href="style.css?'"$V"'">'
  printf '%s\n' '<h1>FDML Cards</h1>'
  printf '%s\n' '<h2>Examples (root)</h2><ul>'
  for f in out/html/*.html; do b="${f##*/}"; printf '<li><a href="./%s?%s">%s</a></li>\n' "$b" "$V" "$b"; done
  printf '%s\n' '</ul>'
  printf '%s\n' '<h2>Examples under /cards/</h2><ul>'
  for f in out/html/*.html; do b="${f##*/}"; printf '<li><a href="./cards/%s?%s">%s</a></li>\n' "$b" "$V" "$b"; done
  printf '%s\n' '</ul>'
} > "$OUT/index.html"
echo "Site generated at $(pwd)/$OUT"

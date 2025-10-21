#!/usr/bin/env bash
set -euo pipefail

OUT="site"
rm -rf "$OUT"
mkdir -p "$OUT" "$OUT/cards" "$OUT/assets"

cp -a docs/. "$OUT/"
cp -a out/html/. "$OUT/"
cp -a xslt/style.css "$OUT/style.css"
cp -a xslt/style.css "$OUT/cards/style.css"
cp -a out/html/*.html "$OUT/cards/"

{
  printf '<!doctype html><meta charset="utf-8"><title>FDML Cards</title>\n'
  printf '<link rel="stylesheet" href="style.css">\n'
  printf '<h1>FDML Cards</h1>\n'
  printf '<h2>Examples (root)</h2><ul>\n'
  for f in out/html/*.html; do b="${f##*/}"; printf '<li><a href="./%s?nocache">%s</a></li>\n' "$b" "$b"; done
  printf '</ul>\n'
  printf '<h2>Examples under /cards/</h2><ul>\n'
  for f in out/html/*.html; do b="${f##*/}"; printf '<li><a href="./cards/%s?nocache">%s</a></li>\n' "$b" "$b"; done
  printf '</ul>\n'
} > "$OUT/index.html"

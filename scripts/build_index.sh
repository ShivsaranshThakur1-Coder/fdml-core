#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/site"
rm -rf "$OUT"
mkdir -p "$OUT/cards"
cp -a "$ROOT"/out/html/*.html "$OUT/" || true
cp -a "$ROOT"/out/html/*.html "$OUT/cards/" || true
install -m 0644 "$ROOT/docs/style.css" "$OUT/style.css"
install -m 0644 "$ROOT/docs/style.css" "$OUT/cards/style.css"
root_files=( "$OUT"/*.html )
cards_files=( "$OUT"/cards/*.html )
{
  printf '<!doctype html><meta charset="utf-8"><title>FDML Cards</title>\n'
  printf '<link rel="stylesheet" href="style.css">\n'
  printf '<h1>FDML Cards</h1>\n'
  printf '<h2>Examples (root)</h2><ul>\n'
  for f in "${root_files[@]}"; do b="${f##*/}"; printf '<li><a href="./%s?nocache">%s</a></li>\n' "$b" "$b"; done
  printf '</ul>\n'
  printf '<h2>Examples under /cards/</h2><ul>\n'
  for f in "${cards_files[@]}"; do b="${f##*/}"; printf '<li><a href="./cards/%s?nocache">%s</a></li>\n' "$b" "$b"; done
  printf '</ul>\n'
} > "$OUT/index.html"
echo "Site generated at $OUT"

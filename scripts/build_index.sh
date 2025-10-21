#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/site"
rm -rf "$OUT"
mkdir -p "$OUT/cards"
cp -a "$ROOT"/out/html/*.html "$OUT/"
cp -a "$ROOT"/out/html/*.html "$OUT/cards/" || true
install -m 0644 "$ROOT/docs/style.css" "$OUT/style.css"
install -m 0644 "$ROOT/docs/style.css" "$OUT/cards/style.css"
{
  printf '<!doctype html><meta charset="utf-8"><title>FDML Cards</title>\n'
  printf '<link rel="stylesheet" href="style.css">\n'
  printf '<h1>FDML Cards</h1>\n'
  printf '<h2>Examples (root)</h2><ul>\n'
  for f in "$OUT"/*.html; do b="${f##*/}"; printf '<li><a href="./%s?nocache">%s</a></li>\n' "$b" "$b"; done
  printf '</ul>\n'
  printf '<h2>Examples under /cards/</h2><ul>\n'
  for f in "$OUT"/cards/*.html 2>/dev/null; do b="${f##*/}"; printf '<li><a href="./cards/%s?nocache">%s</a></li>\n' "$b" "$b"; done
  printf '</ul>\n'
} > "$OUT/index.html"
echo "Site generated at $OUT"

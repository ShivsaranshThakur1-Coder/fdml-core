#!/usr/bin/env bash
set -euo pipefail
OUT=site
rm -rf "$OUT"
mkdir -p "$OUT/cards"
cp -a out/html/. "$OUT/"
cp -a out/html/. "$OUT/cards/"
cp -a docs/style.css "$OUT/style.css"
cp -a docs/style.css "$OUT/cards/style.css"
cat > "$OUT/index.html" <<HTML
<!doctype html><meta charset="utf-8"><title>FDML Cards</title>
<link rel="stylesheet" href="./style.css">
<div class="container">
  <div class="hero"><h1>FDML Cards</h1></div>
  <h2>Examples (root)</h2>
  <ul>
    $(for f in $(ls -1 out/html/*.html | xargs -n1 basename); do printf '<li><a href="./%s">%s</a></li>\n' "$f" "$f"; done)
  </ul>
  <h2>Examples under /cards/</h2>
  <ul>
    $(for f in $(ls -1 out/html/*.html | xargs -n1 basename); do printf '<li><a href="./cards/%s">%s</a></li>\n' "$f" "$f"; done)
  </ul>
</div>
HTML
echo "Site generated at $(pwd)/$OUT"

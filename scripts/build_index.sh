#!/usr/bin/env bash
set -euo pipefail
V="${1:-${V:-$EPOCHSECONDS}}"

# Rebuild cards only; keep site/ stable
rm -rf site/cards
mkdir -p site site/cards

# Ship CSS
cp -f docs/style.css site/style.css
cp -f docs/style.css site/cards/style.css
cp -f docs/timeline.js site/cards/timeline.js
cp -f docs/diagram.js site/cards/diagram.js

# Copy generated cards
cp -f out/html/*.html site/cards/

# Emit per-card export-json payloads for timeline renderer
tmp_cards="$(mktemp)"
find corpus/valid -type f -name '*.xml' | sort > "$tmp_cards"
while IFS= read -r f; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  bin/fdml export-json "$f" --out "site/cards/${stem}.json" >/dev/null
done < "$tmp_cards"
rm -f "$tmp_cards"

# Emit index.json for Search
bin/fdml index corpus/valid --out site/index.json

# Emit export-json sample for demo page
bin/fdml export-json corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml --out site/export-json-sample.json >/dev/null

# Inject per-card navigation continuity links
python3 scripts/patch_card_nav.py

# Copy Search and thread cache-buster
cp -f docs/search.html site/search.html
perl -pi -e "s/@@CSSV@@/${V}/g" site/search.html

# Copy Demo page and thread cache-buster
cp -f docs/DEMO.html site/demo.html
perl -pi -e "s/@@CSSV@@/${V}/g" site/demo.html

# Build homepage
cat > site/index.html <<HTML
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>FDML – Examples</title>
<link rel="stylesheet" href="style.css?v=${V}">
</head>
<body>
<header class="site-head">
  <div class="container">
    <a class="brand" href="./">FDML</a>
    <nav class="nav">
      <a href="./index.html">Home</a>
      <a href="./demo.html">Demo</a>
      <a href="./search.html">Search</a>
      <a class="muted" href="https://github.com/ShivsaranshThakur1-Coder/fdml-core">GitHub</a>
    </nav>
  </div>
</header>
<main class="container">
  <div class="hero">
    <h1>Folk Dance Markup Library</h1>
    <p class="sub">Curated, validated examples rendered as clean, printable cards.</p>
    <p><a class="cta" href="./demo.html">Demo</a></p>
  </div>
  <ul class="grid">
HTML
for p in site/cards/*.html; do
  b="$(basename "$p")"
  title="$(grep -m1 -oE "<h1[^>]*>[^<]+" "$p" | sed -E "s#<[^>]+>##g")"
  printf '    <li><a class="card" href="cards/%s"><strong>%s</strong><div class="sub">%s</div></a></li>
' "$b" "$title" "$b" >> site/index.html
done
cat >> site/index.html <<'HTML'
  </ul>
  <footer><div class="container">
    <span class="muted">©</span> <a class="muted" href="https://github.com/ShivsaranshThakur1-Coder">Shivsaransh Thakur</a> ·
    <a class="muted" href="https://github.com/ShivsaranshThakur1-Coder/fdml-core">Source</a>
  </div></footer>
</main>
</body></html>
HTML

echo "Site built → site/ (cards/, index.html, demo.html, search.html, index.json)"

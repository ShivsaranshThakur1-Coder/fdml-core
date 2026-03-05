#!/usr/bin/env bash
set -euo pipefail
V="${1:-${V:-0}}"
V12_DEMO_FILES=(
  "corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml"
  "corpus/valid_v12/mayim-mayim.v12.fdml.xml"
  "corpus/valid_v12/example-05-contra.progress.v12.fdml.xml"
)
UNIFIED_CORPUS_DIR="out/m9_full_description_uplift/run1"
M5_SHOWCASE_FILES=(
  "out/m9_full_description_uplift/run1/acquired_sources__adumu.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__attan.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__giddha.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__branle.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__cueca.fdml.xml"
)
M6_SHOWCASE_FILES=(
  "out/m9_full_description_uplift/run1/acquired_sources__kpanlogo.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__khorumi.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__joget.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__farandole.fdml.xml"
  "out/m9_full_description_uplift/run1/acquired_sources__cumbia.fdml.xml"
)

# Rebuild cards only; keep site/ stable
rm -rf site/cards
mkdir -p site site/cards

if [[ ! -d "$UNIFIED_CORPUS_DIR" ]]; then
  echo "Missing unified corpus dir: $UNIFIED_CORPUS_DIR" >&2
  echo "Run: make m11-validator-unified-check" >&2
  exit 1
fi

# Ship CSS
cp -f docs/style.css site/style.css
cp -f docs/style.css site/cards/style.css
cp -f docs/timeline.js site/cards/timeline.js
cp -f docs/diagram.js site/cards/diagram.js

# Copy generated cards
cp -f out/html/*.html site/cards/

# Render unified full-corpus cards directly (default production workflow)
tmp_promoted_cards="$(mktemp)"
find "$UNIFIED_CORPUS_DIR" -type f -name '*.fdml.xml' | sort > "$tmp_promoted_cards"
while IFS= read -r f; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  xsltproc --stringparam cssVersion "$V" xslt/card.xsl "$f" > "site/cards/${stem}.html"
done < "$tmp_promoted_cards"
rm -f "$tmp_promoted_cards"

# Render curated v1.2 demo cards directly (deterministic explicit list)
for f in "${V12_DEMO_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required v1.2 demo file: $f" >&2
    exit 1
  fi
  base="$(basename "$f")"
  stem="${base%.xml}"
  xsltproc --stringparam cssVersion "$V" xslt/card.xsl "$f" > "site/cards/${stem}.html"
done
for f in "${M5_SHOWCASE_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required M5 showcase file: $f" >&2
    exit 1
  fi
  base="$(basename "$f")"
  stem="${base%.xml}"
  xsltproc --stringparam cssVersion "$V" xslt/card.xsl "$f" > "site/cards/${stem}.html"
done
for f in "${M6_SHOWCASE_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required M6 showcase file: $f" >&2
    exit 1
  fi
  base="$(basename "$f")"
  stem="${base%.xml}"
  xsltproc --stringparam cssVersion "$V" xslt/card.xsl "$f" > "site/cards/${stem}.html"
done

# Emit per-card export-json payloads for timeline renderer
tmp_cards="$(mktemp)"
find corpus/valid -type f -name '*.xml' | sort > "$tmp_cards"
while IFS= read -r f; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  bin/fdml export-json "$f" --out "site/cards/${stem}.json" >/dev/null
done < "$tmp_cards"
rm -f "$tmp_cards"
tmp_promoted_json="$(mktemp)"
find "$UNIFIED_CORPUS_DIR" -type f -name '*.fdml.xml' | sort > "$tmp_promoted_json"
while IFS= read -r f; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  bin/fdml export-json "$f" --out "site/cards/${stem}.json" >/dev/null
done < "$tmp_promoted_json"
rm -f "$tmp_promoted_json"
for f in "${V12_DEMO_FILES[@]}"; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  bin/fdml export-json "$f" --out "site/cards/${stem}.json" >/dev/null
done
for f in "${M5_SHOWCASE_FILES[@]}"; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  bin/fdml export-json "$f" --out "site/cards/${stem}.json" >/dev/null
done
for f in "${M6_SHOWCASE_FILES[@]}"; do
  base="$(basename "$f")"
  stem="${base%.xml}"
  bin/fdml export-json "$f" --out "site/cards/${stem}.json" >/dev/null
done

# Emit index.json for Search
bin/fdml index corpus/valid "${V12_DEMO_FILES[@]}" "$UNIFIED_CORPUS_DIR" --out site/index.json

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

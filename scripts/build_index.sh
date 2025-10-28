#!/usr/bin/env bash
set -euo pipefail
V="${1:-$EPOCHSECONDS}"
rm -rf site
mkdir -p site/cards
cp -f docs/style.css site/style.css
cp -f out/html/*.html site/cards/

# Build a single “cards” grid homepage
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
      <a class="muted" href="https://github.com/ShivsaranshThakur1-Coder/fdml-core">GitHub</a>
    </nav>
  </div>
</header>
<main class="container">
  <div class="hero">
    <h1>Folk Dance Markup Library</h1>
    <p class="sub">Curated, validated examples rendered as clean, printable cards.</p>
  </div>
  <ul class="grid">
HTML
for p in site/cards/*.html; do
  b="$(basename "$p")"
  title="$(grep -m1 -oE '<h1[^>]*>[^<]+' "$p" | sed -E 's#<[^>]+>##g')"
  printf '    <li><a class="card" href="cards/%s"><strong>%s</strong><div class="sub">%s</div></a></li>\n' "$b" "$title" "$b" >> site/index.html
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
echo "Site built → site/ (with cards/ and polished index)"

cp -f docs/style.css site/cards/style.css

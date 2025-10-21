#!/usr/bin/env bash
set -euo pipefail
V="${1:-nocache}"
mkdir -p site site/cards
cp -f docs/style.css "site/style.css"
cp -f docs/style.css "site/cards/style.css"
cp -f out/html/*.html site/
cp -f out/html/*.html site/cards/

ROOT_LIST=$(for f in out/html/*.html; do b=$(basename "$f"); printf '<li><a class="card link" href="%s">%s</a></li>\n' "$b" "$b"; done)
CARDS_LIST=$(for f in out/html/*.html; do b=$(basename "$f"); printf '<li><a class="card link" href="cards/%s">%s</li>\n' "$b" "$b"; done)

cat > site/index.html <<HTML
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="color-scheme" content="dark light"/>
  <title>FDML – Examples</title>
  <link rel="stylesheet" href="style.css?$V"/>
</head>
<body>
  <header class="site-name site-head">
    <div class="container">
      <a class="brand" href="./">FDML</a>
      <nav class="nav">
        <a href="./index.html">Examples</a>
        <a href="https://github.com/ShivsaranshThakur1-Coder/fdml-core" target="_blank" rel="noopener">GitHub</a>
      </nav>
    </div>
  </header>
  <main class="container">
    <section class="hero">
      <h1>Folk Dance Markup Library</h1>
      <p class="sub">Browse working examples of structured dance notation. Each card links to a fully rendered page.</p>
    </section>

    <h2>Examples (root)</h2>
    <ul class="grid">
$ROOT_LIST
    </ul>

    <h2>Examples under <span class="muted">/cards/</span></h2>
    <ul class="grid">
$CARDS_LIST
    </ul>
  </main>
  <footer><div class="container">© $(date +%Y) FDML</div></footer>
</body>
</html>
HTML
# ensure root pages have correct back-link path
sed -i '' -e 's#href="../index\.html"#href="index.html"#g' site/*.html || true
# provide an index in /cards for convenience
cp -f site/index.html site/cards/index.html

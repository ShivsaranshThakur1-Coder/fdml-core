#!/usr/bin/env bash
set -euo pipefail
TS="${1:-$(date +%s)}"
out="site"
mkdir -p "$out"
cp -f docs/style.css "$out/style.css"
{
  echo '<!doctype html>'
  echo '<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
  echo '<title>FDML • Examples</title>'
  echo "<link rel=\"stylesheet\" href=\"style.css?${TS}\">"
  echo '</head><body>'
  echo '<header class="site-head"><div class="container"><a class="brand" href="index.html">FDML</a><nav class="nav"><a href="index.html">Examples</a><a href=\"https://github.com/ShivsaranshThakur1-Coder/fdml-core\" target=\"_blank\" rel=\"noopener\">GitHub</a></nav></div></header>"
  echo '<main class="container" style="padding-top:96px">'
  echo '<section class="hero"><h1>Folk Dance Markup Language</h1><p class="sub">Curated, printable examples rendered from FDML.</p></section>'
  echo '<div class="card"><h2>Examples</h2><ul class="doc-list">'
  LC_ALL=C find corpus/valid -type f -name '*.xml' -exec basename {} \; | sort | while read -r f; do
    stem="${f%.xml}"; printf '<li><a href="%s.html">%s</a></li>\n' "$stem" "$stem"
  done
  echo '</ul></div></main></body></html>'
} > "$out/index.html"

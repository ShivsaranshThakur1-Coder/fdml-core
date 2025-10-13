#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/docs/examples"
PDF="$ROOT/docs/pdfs"

rm -rf "$OUT"
mkdir -p "$OUT" "$ROOT/docs/css" "$PDF"

cp -f "$ROOT/css/print.css" "$ROOT/docs/css/print.css"

for f in "$ROOT"/corpus/valid/*.xml; do
  b="$(basename "$f")"
  name="${b%.*}"
  "$ROOT/bin/fdml" render "$f" --out "$OUT/$name.html"
  "$ROOT/bin/fdml" export-pdf "$f" --out "$PDF/$name.pdf" || true
done

cat > "$OUT/index.html" <<HTML
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>FDML Examples</title>
    <link rel="stylesheet" href="../site.css"/>
  </head>
  <body>
    <div class="wrap">
      <div class="nav"><a class="cta" href="../index.html">← Home</a></div>
      <h1>FDML Examples</h1>
      <ul>
HTML

for html in "$OUT"/*.html; do
  base="$(basename "$html")"
  title="$(sed -n 's@.*<title>\\(.*\\)</title>.*@\\1@p' "$html" | head -n1)"
  pdfbase="$(echo "$base" | sed 's/\.html$/.pdf/')"
  pdfrel="../pdfs/$pdfbase"
  if [ -f "$PDF/$pdfbase" ]; then
    echo "        <li><a href=\"$base\">${title:-$base}</a> — <a href=\"$pdfrel\">PDF</a></li>" >> "$OUT/index.html"
  else
    echo "        <li><a href=\"$base\">${title:-$base}</a></li>" >> "$OUT/index.html"
  fi
done

cat >> "$OUT/index.html" <<HTML
      </ul>
    </div>
  </body>
</html>
HTML

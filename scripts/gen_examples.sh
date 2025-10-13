#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/docs/examples"

rm -rf "$OUT"
mkdir -p "$OUT" "$ROOT/docs/css"

cp -f "$ROOT/css/print.css" "$ROOT/docs/css/print.css"

for f in "$ROOT"/corpus/valid/*.xml; do
  b="$(basename "$f")"
  name="${b%.*}"
  "$ROOT/bin/fdml" render "$f" --out "$OUT/$name.html"
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
  echo "        <li><a href=\"$base\">$base</a></li>" >> "$OUT/index.html"
done

cat >> "$OUT/index.html" <<HTML
      </ul>
    </div>
  </body>
</html>
HTML

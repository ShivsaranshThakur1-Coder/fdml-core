#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/docs/examples"

rm -rf "$OUT"
mkdir -p "$OUT"

# Render each valid corpus file into docs/examples
for f in "$ROOT"/corpus/valid/*.xml; do
  b="$(basename "$f")"
  name="${b%.*}"
  "$ROOT/bin/fdml" render "$f" --out "$OUT/$name.html"
done

# Build an index page
cat > "$OUT/index.html" <<HTML
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>FDML Examples</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial, sans-serif; margin: 2rem; }
      h1 { margin-bottom: 0.5rem; }
      ul { padding-left: 1rem; }
      li { margin: 0.25rem 0; }
      code { background: #f6f8fa; padding: 0.2rem 0.4rem; border-radius: 4px; }
    </style>
  </head>
  <body>
    <h1>FDML Examples</h1>
    <p>These HTML pages are rendered from files in <code>corpus/valid/</code>.</p>
    <ul>
HTML

for html in "$OUT"/*.html; do
  base="$(basename "$html")"
  echo "      <li><a href=\"$base\">$base</a></li>" >> "$OUT/index.html"
done

cat >> "$OUT/index.html" <<HTML
    </ul>
    <p>Regenerate with: <code>make docs</code></p>
  </body>
</html>
HTML

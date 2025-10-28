#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 || ! "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Usage: $0 vX.Y.Z" >&2; exit 2
fi
REL="$1"; VER="${REL#v}"
echo "== Tagging $REL =="
git tag -a "$REL" -m "FDML Core $REL"
git push origin "$REL"

URL="https://github.com/ShivsaranshThakur1-Coder/fdml-core/releases/download/$REL/fdml-core.jar"
TMP="$(mktemp)"; tries=0
echo "== Waiting for release asset =="
until curl -fsSL -o "$TMP" "$URL"; do
  tries=$((tries+1)); [[ $tries -gt 72 ]] && { echo "Timed out waiting for $URL"; exit 1; }
  sleep 5
done
SHA="$(shasum -a 256 "$TMP" | awk "{print \$1}")"; rm -f "$TMP"
echo "SHA256=$SHA"

echo "== Updating tap formula =="
pushd homebrew-fdml >/dev/null
git fetch origin
git checkout main
git reset --hard origin/main
cat > Formula/fdml.rb <<RUBY
class Fdml < Formula
  desc "Folk Dance Markup Language CLI"
  homepage "https://shivsaranshthakur1-coder.github.io/fdml-core/"
  url "$URL", using: :nounzip
  version "$VER"
  sha256 "$SHA"

  depends_on "openjdk@17"

  def install
    libexec.install "fdml-core.jar"
    (bin/"fdml").write <<~EOS
      #!/usr/bin/env bash
      exec "#{Formula["openjdk@17"].opt_bin}/java" -jar "#{libexec}/fdml-core.jar" "$@"
    EOS
    chmod 0555, bin/"fdml"
  end

  test do
    (testpath/"t.fdml.xml").write <<~XML
      <?xml version="1.0" encoding="UTF-8"?>
      <fdml version="1.0">
        <meta><title>t</title></meta>
        <body><section id="s-1">ok</section></body>
      </fdml>
    XML
    system "#{bin}/fdml", "validate", testpath/"t.fdml.xml"
  end
end
RUBY
git add Formula/fdml.rb
git commit -m "fdml $REL: update url=$URL sha256=$SHA"
git push origin main
popd >/dev/null
echo "== Done: $REL published and tap updated =="

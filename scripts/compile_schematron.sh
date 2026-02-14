#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMATRON_INPUT="${1:-$ROOT_DIR/schematron/fdml.sch}"
COMPILED_OUTPUT="${2:-$ROOT_DIR/schematron/fdml-compiled.xsl}"
COMPILER_JAR="$ROOT_DIR/tools/schxslt-cli-1.10.1.jar"
COMPILER_JAR_SHA256="cefb6c45441252675270bacc67a1ec4421ed1133f7fb8fee8f314ecfa6a0171a"

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
    return
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
    return
  fi
  echo "ERROR: no SHA-256 tool found (need shasum or sha256sum)" >&2
  exit 2
}

if [[ ! -f "$SCHEMATRON_INPUT" ]]; then
  echo "ERROR: missing Schematron source: $SCHEMATRON_INPUT" >&2
  exit 2
fi

if [[ ! -f "$COMPILER_JAR" ]]; then
  echo "ERROR: missing pinned compiler jar: $COMPILER_JAR" >&2
  exit 2
fi

if ! command -v javac >/dev/null 2>&1 || ! command -v java >/dev/null 2>&1; then
  echo "ERROR: Java 17 (java + javac) is required" >&2
  exit 2
fi

actual_sha256="$(sha256_file "$COMPILER_JAR")"
if [[ "$actual_sha256" != "$COMPILER_JAR_SHA256" ]]; then
  echo "ERROR: checksum mismatch for $COMPILER_JAR" >&2
  echo "Expected: $COMPILER_JAR_SHA256" >&2
  echo "Actual:   $actual_sha256" >&2
  exit 2
fi

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/fdml-sch-XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT

cat >"$tmpdir/CompileSchematron.java" <<'JAVA'
import java.io.File;
import java.util.Map;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Source;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import javax.xml.transform.stream.StreamSource;
import name.dmaus.schxslt.Compiler;
import org.w3c.dom.Document;

public final class CompileSchematron {
  public static void main(String[] args) throws Exception {
    if (args.length != 2) {
      System.err.println("Usage: CompileSchematron <input.sch> <output.xsl>");
      System.exit(2);
    }

    System.setProperty(
        "javax.xml.transform.TransformerFactory",
        "net.sf.saxon.TransformerFactoryImpl");

    Source schema = new StreamSource(new File(args[0]));
    Compiler compiler = new Compiler();
    Document compiled = compiler.compile(schema, Map.of());

    TransformerFactory tf = TransformerFactory.newInstance();
    Transformer serializer = tf.newTransformer();
    serializer.setOutputProperty(OutputKeys.METHOD, "xml");
    serializer.setOutputProperty(OutputKeys.ENCODING, "UTF-8");
    serializer.setOutputProperty(OutputKeys.INDENT, "yes");
    serializer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "no");
    serializer.setOutputProperty("{http://saxon.sf.net/}indent-spaces", "2");
    serializer.transform(new DOMSource(compiled), new StreamResult(new File(args[1])));
  }
}
JAVA

mkdir -p "$(dirname "$COMPILED_OUTPUT")"
javac -cp "$COMPILER_JAR" "$tmpdir/CompileSchematron.java"
java -cp "$COMPILER_JAR:$tmpdir" CompileSchematron "$SCHEMATRON_INPUT" "$COMPILED_OUTPUT"

echo "Compiled Schematron:"
echo "  Source : $SCHEMATRON_INPUT"
echo "  Output : $COMPILED_OUTPUT"

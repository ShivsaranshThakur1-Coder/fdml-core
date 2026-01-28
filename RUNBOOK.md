# FDML Core — RUNBOOK

This runbook is based **only** on evidence in this repo.

## 0) Prerequisites
- Java 17 (required): see `README.md` and `pom.xml` (`maven.compiler.release=17`).
- Maven (`mvn`) to build: `bin/fdml` will run `mvn -q -DskipTests package` if `target/fdml-core.jar` is missing.
- For `make html` you need:
  - `xsltproc` (libxslt) — see `Makefile` (uses `xsltproc`) and `.github/workflows/render-test.yml` (installs `libxslt`).

## 1) Build the CLI jar
Option A — direct Maven:
```bash
mvn -q -DskipTests package
```
Produces:
- `target/fdml-core.jar` (shaded jar) — configured in `pom.xml`.

Option B — via wrapper (auto-builds jar if missing):
```bash
./bin/fdml --help
```
Wrapper: `bin/fdml`.

## 2) Validate FDML (XSD)
Validate a file:
```bash
./bin/fdml validate corpus/valid/example-01.fdml.xml
```

Validate a directory (recursively; filters for `.xml`, `.fdml`, `.fdml.xml`):
```bash
./bin/fdml validate corpus/valid
```

JSON output:
```bash
./bin/fdml validate corpus/valid --json --json-out out/validate.json
```

Implementation details:
- Uses XSD at `schema/fdml.xsd` (see `src/main/java/org/fdml/cli/FdmlValidator.java`).

## 3) Validate FDML (Schematron)
Validate directory:
```bash
./bin/fdml validate-sch corpus/valid
```

JSON output:
```bash
./bin/fdml validate-sch corpus/valid --json --json-out out/validate-sch.json
```

Implementation details:
- Uses compiled Schematron XSL: `schematron/fdml-compiled.xsl` (see `src/main/java/org/fdml/cli/SchematronValidator.java`).

Unknown:
- How to regenerate `schematron/fdml-compiled.xsl` from `schematron/fdml.sch`.
- To resolve: add documentation or script (candidate path: `docs/ARCHITECTURE.md`).

## 4) Validate all (XSD + Schematron)
```bash
./bin/fdml validate-all corpus/valid
```

## 5) Lint (meter/beat warnings)
```bash
./bin/fdml lint corpus/valid
```

Strict mode (warnings become exit code 2):
```bash
./bin/fdml lint corpus/valid --strict
```

What lint checks (per `src/main/java/org/fdml/cli/Linter.java`):
- warns if total `step/@beats` within each top-level `figure` is not divisible by meter numerator
- warns if meter missing

Caveat:
- It currently sums only `figure/step/@beats`, not `figure/measureRange/step/@beats`.
  - If you use `measureRange`, lint may undercount.

## 6) Doctor (XSD + Schematron + Lint)
```bash
./bin/fdml doctor corpus/valid
```

Strict gate (fails if any lint warnings):
```bash
./bin/fdml doctor corpus/valid --strict
```

CI uses strict doctor on valid corpus:
- `.github/workflows/ci.yml`

## 7) Render a single FDML file to HTML (via Java/Saxon)
```bash
./bin/fdml render corpus/valid/example-01.fdml.xml --out out/example-01.html
```

Implementation:
- Uses XSL `xslt/fdml-to-card.xsl` (see `src/main/java/org/fdml/cli/Main.java`).

## 8) Export a single FDML file to PDF
```bash
./bin/fdml export-pdf corpus/valid/example-01.fdml.xml --out out/example-01.pdf
```

Implementation:
- Uses XSL `xslt/fdml-to-xhtml.xsl` and `openhtmltopdf` (see `src/main/java/org/fdml/cli/PdfExporter.java`).

## 9) Build the static site (HTML cards + index/search)
### One command
```bash
make html
```

What it does (per `Makefile` and `scripts/build_index.sh`):
- renders each `corpus/valid/*.xml` to `out/html/*.html` using `xsltproc` and `xslt/card.xsl`
- copies CSS and pages into `site/`
- generates:
  - `site/index.html`
  - `site/search.html` (with cache-busted CSS parameter)
  - `site/index.json` (via `bin/fdml index corpus/valid --out site/index.json`)

Serve locally:
```bash
make serve
# then open http://localhost:8000
```

## 10) Run the full local CI pipeline
```bash
make ci
```
Per `Makefile`, this runs:
- `validate-valid` (calls `fdml validate`)
- `validate-invalid` (ensures `fdml validate` fails on invalid corpus)
- `html`

Note: `make validate-*` uses `fdml` in PATH (not `./bin/fdml`).
- Unknown whether you expect Homebrew-installed `fdml` or want to use the local wrapper.
- To resolve: clarify in docs (candidate path: `docs/USAGE.md`).

## 11) Release (tag-driven)
Automated release:
- Trigger: Git tag `v*`
- Workflow: `.github/workflows/release.yml`
- Artifacts: `target/fdml-core.jar`, `fdml-pdfs.zip`

Helper script:
```bash
./scripts/release.sh vX.Y.Z
```
What it does (per `scripts/release.sh`):
- tags and pushes
- waits for GitHub Release jar asset
- calculates SHA256
- updates Homebrew formula in `homebrew-fdml/Formula/fdml.rb` and pushes

Unknown:
- Whether you want `homebrew-fdml/` as a submodule or kept in-sync as a directory.
- To resolve: document in `docs/CONTRIBUTING.md` or `README.md`.

## 12) Troubleshooting

### “Building fdml-core.jar…” happens every time
Cause: `target/fdml-core.jar` missing.
- Build once: `mvn -q -DskipTests package`
- Or ensure `target/` isn’t being cleaned.

### Schematron fails unexpectedly
Likely causes:
- `schematron/fdml-compiled.xsl` out of sync with `schematron/fdml.sch`.
- FDML file is `version="1.1"` and triggers v1.1-only assertions.

Where to inspect:
- rules: `schematron/fdml.sch`
- compiled XSL: `schematron/fdml-compiled.xsl`

### Doctor fails in strict mode due to lint warnings
Run non-strict to see warnings:
```bash
./bin/fdml doctor corpus/valid
./bin/fdml lint corpus/valid
```
Then fix meter/beat consistency or add missing meter.

### make html fails: xsltproc not found
Install libxslt:
- See `.github/workflows/render-test.yml` which installs `libxslt` via brew on macOS runners.

## 13) Repo hygiene (current state)
Per `.clawdbot_context/01_git_status.txt`, the following are currently untracked locally:
- `.clawdbot_context/`
- `TerminalLineCommands/`
- `tutor_brief*.{aux,log,out,pdf}` and `tutor_brief_explained*.{aux,log,out,pdf}`

Unknown:
- Whether these should be committed.
- To resolve: consult `.gitignore` and contributing guidance (`docs/CONTRIBUTING.md`).

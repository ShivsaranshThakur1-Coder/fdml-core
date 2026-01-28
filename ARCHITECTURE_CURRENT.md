# FDML Core — Current Architecture

This document is derived **only** from evidence in this repository (including `.clawdbot_context/**`).

## 1) What this repo is
**FDML Core** is a Java/Maven project that provides:
- an XML format for folk dance material (**FDML**) defined by **XSD**
- semantic/business-rule validation via **Schematron**
- rendering FDML to HTML (and PDF export) via **XSLT**
- a CLI wrapper (`fdml`) and CI workflows
- an example corpus (`corpus/`) plus generated site outputs (`site/`, `out/`, `docs/examples/`)

Primary entrypoints:
- CLI wrapper script: `bin/fdml`
- Java main: `src/main/java/org/fdml/cli/Main.java`

Repository description:
- `README.md`

## 2) Major components

### 2.1 FDML format definition (XSD)
- **Schema:** `schema/fdml.xsd`
- Root structure: `<fdml version="…">` containing `<meta>` and `<body>`.
- Key model elements (per XSD):
  - `meta`: title + optional dance/origin/type/meter/tempo/formation/styling/music/source/difficulty/tags/author
  - `body`: sequences of `section`, `part`, `figure`, `sequence`
  - `figure`: has `@id`, optional `@name` and `@formation`, and contains `step` and/or `measureRange/step`
  - `sequence/use`: can reference `@figure` or `@part` and optional `@repeat`

Notes:
- The schema does **not** restrict `fdml/@version` to a fixed value (it’s `xs:string`).
- This repo’s docs include FDML 1.0 and there is evidence of FDML 1.1 rules in Schematron and examples.

### 2.2 Semantic validation (Schematron)
- Schematron source: `schematron/fdml.sch`
- Compiled Schematron (SVRL-producing XSL): `schematron/fdml-compiled.xsl`
- Implemented in Java via Saxon: `src/main/java/org/fdml/cli/SchematronValidator.java`

Rules evidenced in `schematron/fdml.sch` include:
- `fdml` must contain `meta` and `body`.
- Every `figure` must contain at least one `step` or `measureRange/step`.
- `sequence/use[@figure]` must reference an existing `figure/@id`.
- **FDML v1.1-specific** constraints for richer metadata:
  - require `meta/origin/@country`
  - require `meta/type/@genre`
  - require `meta/meter/@value`
  - require `body/section[@type='notes']` and `body/section[@type='setup']`
  - type/formation consistency checks (genre circle/line/couple must appear in formation text)

### 2.3 Linting (soft validation)
- Linter: `src/main/java/org/fdml/cli/Linter.java`

What it does (per code):
- Reads `meta/meter/@value` (expects `N/D`), parses numerator `N`.
- For each top-level `/fdml/body/figure` only:
  - sums `./step/@beats` (note: does **not** sum `measureRange/step/@beats`)
  - emits warning `off_meter` if total beats is not divisible by meter numerator
- Emits warning `missing_meter` when meter is missing.

Implications:
- FDML documents that put steps inside `measureRange` will currently appear as 0 beats to lint for that figure.
  - Unknown whether that’s intentional.
  - To resolve intent: add or reference an issue/decision record (none found). Candidate file to add: `docs/ARCHITECTURE.md` or `docs/FDML-SPEC.md`.

### 2.4 CLI (Java shaded jar)
- Main CLI: `src/main/java/org/fdml/cli/Main.java`
- Build config: `pom.xml` (shade plugin produces `target/fdml-core.jar` with `Main` as entrypoint)
- Wrapper script: `bin/fdml` builds jar if missing and runs `java -jar target/fdml-core.jar`.

Commands evidenced in `Main.java`:
- `validate` (XSD)
- `validate-sch` (Schematron)
- `validate-all` (both)
- `render` (FDML → HTML) using `xslt/fdml-to-card.xsl`
- `export-pdf` (FDML → XHTML → PDF) using `xslt/fdml-to-xhtml.xsl` + `openhtmltopdf`
- `index` (build search index JSON) via `Indexer`
- `lint` (meter/beat lint)
- `init` (create starter FDML file)
- `doctor` (XSD + Schematron + lint; strict mode fails on lint warnings)

Exit codes (per `Main.java`):
- `0` OK
- `2` validation errors (and also strict lint failures in `lint`/`doctor`)
- `3` transform/render error (used conceptually; actual throws in renderer become I/O error unless caught elsewhere)
- `4` I/O / usage error

### 2.5 Rendering & site generation
There are **two** rendering pipelines in evidence:

1) **Java render/export-pdf**
- Render: `Renderer.render(...)` uses Saxon to apply an XSLT.
- Render XSL used by CLI: `xslt/fdml-to-card.xsl` (see `Main.java`).
- PDF export: `PdfExporter` uses `xslt/fdml-to-xhtml.xsl` and then renders HTML to PDF.

2) **Makefile HTML pipeline (xsltproc)**
- `make html` in `Makefile`:
  - applies `xslt/card.xsl` with `xsltproc`
  - outputs per-file HTML into `out/html/`
  - copies CSS into `site/` and copies HTML into `site/`
  - runs `scripts/build_index.sh` and `bin/fdml index` to emit `site/index.json`

Site assets:
- CSS: `docs/style.css` copied into `site/style.css` and `site/cards/style.css` (see `scripts/build_index.sh`).
- Built site directory in repo: `site/` (also used by GitHub Pages workflow).

### 2.6 Corpus & tests
- Example FDML files:
  - valid: `corpus/valid/*.fdml.xml`
  - invalid: `corpus/invalid/*.fdml.xml`
  - invalid v1.1: `corpus/invalid_v11/*.fdml.xml`

Test scaffolding directories exist:
- `test/unit`, `test/snapshot`, `test/e2e`, `test/perf`
- Java tests/resources in `src/test/**`.

Unknowns:
- Specific snapshot test strategy and what “render snapshot” expects.
- To resolve: inspect test sources under `src/test/java/org/fdml/**` and `src/test/resources/snapshots/**`.

### 2.7 CI / release automation
GitHub Actions workflows:
- `/.github/workflows/ci.yml`
  - builds shaded jar
  - validates valid corpus (XSD + Schematron)
  - asserts invalid corpus fails (XSD + Schematron)
  - runs `doctor corpus/valid --strict`
  - runs `mvn test`

- `/.github/workflows/render-test.yml`
  - installs `fdml` via Homebrew tap
  - runs `make html`
  - archives generated HTML as artifact

- `/.github/workflows/fdml-validate.yml`
  - installs `fdml` via Homebrew tap
  - validates corpus/valid passes and corpus/invalid fails

- `/.github/workflows/release.yml`
  - triggered on tag `v*`
  - builds shaded jar and PDFs (`./scripts/gen_examples.sh`)
  - uploads `target/fdml-core.jar` and `fdml-pdfs.zip` to GitHub Release

Release helper script:
- `scripts/release.sh` tags, waits for GitHub Release asset, computes SHA256, updates `homebrew-fdml/Formula/fdml.rb`.

## 3) Dependency graph (runtime)
From `pom.xml`:
- Java 17
- Saxon-HE (`net.sf.saxon:Saxon-HE`) for XSLT/Schematron execution
- openhtmltopdf (`com.openhtmltopdf:openhtmltopdf-pdfbox`) for PDF export
- JUnit Jupiter for tests

## 4) Operational architecture (how a typical workflow runs)

### Validate a directory of FDML files
- CLI `fdml validate corpus/valid`
  - expands directory to XML-ish files
  - validates each file against `schema/fdml.xsd`

### Schematron validation
- CLI `fdml validate-sch corpus/valid`
  - applies compiled Schematron XSL (`schematron/fdml-compiled.xsl`) to each input
  - inspects SVRL failed-assert nodes

### Doctor (strict)
- CLI `fdml doctor corpus/valid --strict`
  - runs XSD + Schematron + Linter
  - fails (exit 2) if any XSD/Schematron failure or any lint warning

### Render cards site
- `make html`
  - renders each valid corpus file via `xslt/card.xsl` and `xsltproc`
  - builds `site/index.html`, `site/search.html`, `site/index.json`

## 5) Unknowns (explicit)
The following are **not determined** from repo evidence:

- **Canonical FDML versioning policy** (how 1.0 vs 1.1 is intended to be handled across schema + tools).
  - Evidence exists of v1.1 constraints in `schematron/fdml.sch` and example files, and 1.0 spec in `docs/FDML-SPEC.md`.
  - To resolve: add or update `docs/FDML-SPEC.md` and/or add a `docs/FDML-1.1-SPEC.md`.

- **Why there are two card render XSLs** (`xslt/card.xsl` vs `xslt/fdml-to-card.xsl`) and which is preferred.
  - To resolve: document in `docs/ARCHITECTURE.md` or `docs/USAGE.md`.

- **How `schematron/fdml-compiled.xsl` is generated/updated**.
  - To resolve: add build instructions or a generator script (candidate doc: `docs/ARCHITECTURE.md`).

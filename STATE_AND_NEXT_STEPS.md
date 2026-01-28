# FDML Core — State and Next Steps

This snapshot uses **only evidence from this repo** (including `.clawdbot_context/**`).

## 1) Current state (what’s working / present)

### Code & build
- Maven/Java project configured for **Java 17**: `pom.xml`.
- Shaded runnable jar produced at `target/fdml-core.jar` with main class `org.fdml.cli.Main`: `pom.xml`.
- CLI wrapper script exists and auto-builds the jar if missing: `bin/fdml`.

### CLI capabilities (implemented)
From `src/main/java/org/fdml/cli/Main.java`:
- Validation:
  - `validate` (XSD) using `schema/fdml.xsd`
  - `validate-sch` (Schematron) using `schematron/fdml-compiled.xsl`
  - `validate-all`
- Rendering:
  - `render` using `xslt/fdml-to-card.xsl` (Saxon)
  - `export-pdf` using `xslt/fdml-to-xhtml.xsl` + `openhtmltopdf`
- Indexing:
  - `index` (produces JSON index used by Search page/site)
- Linting:
  - `lint` (meter/beat warnings)
- Authoring:
  - `init` (bootstrap a new FDML file)
- Aggregation:
  - `doctor` (XSD + Schematron + lint; strict mode fails on lint warnings)

### FDML definitions & rules
- XSD structure: `schema/fdml.xsd`.
- Schematron rules (including v1.1-specific assertions): `schematron/fdml.sch`.
- Compiled Schematron XSL: `schematron/fdml-compiled.xsl`.

### Example corpus
- Valid examples: `corpus/valid/*.fdml.xml`.
- Invalid examples for tests: `corpus/invalid/*.fdml.xml`.
- Invalid v1.1 examples: `corpus/invalid_v11/*.fdml.xml`.

### Static site generation
- `make html` pipeline exists: `Makefile`.
- Site builder script exists: `scripts/build_index.sh`.
- Generated outputs present in repo:
  - `out/html/*`
  - `site/*` including `site/index.html`, `site/search.html`, `site/index.json`.

### CI automation
Workflows exist and (by intent) enforce quality gates:
- Build + validate + doctor strict + tests: `.github/workflows/ci.yml`.
- Render artifacts: `.github/workflows/render-test.yml`.
- Validate with Homebrew-installed `fdml`: `.github/workflows/fdml-validate.yml`.
- Tag-based release: `.github/workflows/release.yml`.

### Release + Homebrew tap automation
- Release helper: `scripts/release.sh`.
- Homebrew tap is included in-repo: `homebrew-fdml/`.

### Context pack contents (what it tells us)
- Basic timestamp + CWD: `.clawdbot_context/00_basic.txt`.
- Git status shows untracked files (including the context pack itself): `.clawdbot_context/01_git_status.txt`.
- Git remote: `.clawdbot_context/02_git_remote.txt`.
- Recent git history shows FDML v1.1 examples and Schematron rule enrichment are already merged to `main`: `.clawdbot_context/03_git_log_30.txt`.

## 2) Key unknowns (explicit, with exact resolving file path)

1) **How to regenerate `schematron/fdml-compiled.xsl`**
- There is no script or Makefile target evidenced that compiles Schematron.
- The compiled file is committed, but the compilation procedure is not.
- To resolve: add documentation or script at one of:
  - `scripts/compile_schematron.sh` (does not exist)
  - or document in `docs/ARCHITECTURE.md` / `docs/USAGE.md`

2) **Which renderer is canonical: Java `render` vs `make html` XSLT pipeline**
- CLI uses `xslt/fdml-to-card.xsl` (Saxon).
- Site build uses `xslt/card.xsl` (xsltproc).
- To resolve: document intent in `docs/ARCHITECTURE.md` or `docs/USAGE.md`.

3) **FDML versioning contract (1.0 vs 1.1)**
- Schematron enforces extra rules when `fdml/@version='1.1'`: `schematron/fdml.sch`.
- XSD does not constrain `fdml/@version` and appears to model richer meta fields already: `schema/fdml.xsd`.
- Spec doc is titled “FDML 1.0”: `docs/FDML-SPEC.md`.
- To resolve: update/add spec documentation (candidate paths):
  - `docs/FDML-SPEC.md` (update)
  - or add `docs/FDML-1.1-SPEC.md` (does not exist)

4) **Lint coverage for `measureRange` steps**
- XSD allows `figure/measureRange/step`, but linter sums only `figure/step/@beats`: `src/main/java/org/fdml/cli/Linter.java`.
- To resolve: update `Linter.java` or document that lint ignores measureRange steps.

5) **Whether generated artifacts should be committed**
- Repo includes `site/` and `out/` directories.
- `.github/workflows/render-test.yml` builds HTML and uploads artifacts; `.gitignore` exists but intent is unclear without reviewing it.
- To resolve: check `.gitignore` and project policy in `README.md` / `docs/CONTRIBUTING.md`.

## 3) Suggested next steps (evidence-aligned)

### A) Document/automate Schematron compilation
Goal: reduce drift between `schematron/fdml.sch` and `schematron/fdml-compiled.xsl`.

Minimal viable outcome:
- Add a script: `scripts/compile_schematron.sh` (currently missing).
- Add a Makefile target `schematron` that regenerates the compiled file.

### B) Unify or clearly separate rendering paths
Decide and document one of:
- “`fdml render` is the canonical renderer; `make html` is a convenience wrapper”
- or “`make html` (xsltproc + xslt/card.xsl) is canonical for site; Java renderer is for PDFs and local preview”

Where to document:
- `docs/ARCHITECTURE.md`
- `docs/USAGE.md`

### C) Clarify FDML 1.1 vs 1.0 in docs
Given v1.1 enforcement exists in Schematron and examples:
- Update `docs/FDML-SPEC.md` to explicitly cover v1.1 (or split into two docs).

### D) Fix/extend lint to cover `measureRange`
If `measureRange` is intended for real usage:
- Update `Linter.java` to sum both direct `step` and `measureRange/step`.

### E) Clean up repo state / ignore policy
Per `.clawdbot_context/01_git_status.txt`, local untracked files include PDFs and LaTeX artifacts.
- Decide whether they should be ignored or committed.
- Paths involved:
  - `tutor_brief*.pdf` and `tutor_brief_explained*.pdf` (currently at repo root)
  - `TerminalLineCommands/`

## 4) Quick verification checklist
(All based on existing commands/docs)

- Build jar:
  - `mvn -q -DskipTests package`
- Validate corpus:
  - `./bin/fdml validate corpus/valid`
  - `./bin/fdml validate-sch corpus/valid`
  - `./bin/fdml doctor corpus/valid --strict`
- Render site:
  - `make html`
  - `make serve` → open `http://localhost:8000`

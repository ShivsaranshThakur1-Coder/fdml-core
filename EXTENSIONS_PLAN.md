# FDML Extensions Plan (Evidence-Based)

This plan is derived from repository evidence in `src/main/java/org/fdml/cli`, `schema/`, `schematron/`, `corpus/`, `scripts/`, `docs/`, `Makefile`, and `.github/workflows/`.

## 1) Product Surface Inventory

### CLI commands and what they do

| Command | What it does | Evidence |
| --- | --- | --- |
| `validate` | XSD validation for files/dirs; supports `--json` and `--json-out` | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/FdmlValidator.java` |
| `validate-sch` | Schematron validation using compiled XSL; supports JSON output | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/SchematronValidator.java`, `schematron/fdml-compiled.xsl` |
| `validate-all` | Runs XSD + Schematron and returns combined status/JSON | `src/main/java/org/fdml/cli/Main.java` |
| `validate-geo` | Geometry/topology semantic validation for v1.2 | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/GeometryValidator.java` |
| `lint` | Advisory beat/meter lint checks; `--strict` can fail | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/Linter.java` |
| `doctor` | Consolidated gate: XSD + Schematron + GEO + Lint + Timing | `src/main/java/org/fdml/cli/Doctor.java` |
| `render` | Renders FDML to HTML card via XSLT | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/Renderer.java`, `xslt/fdml-to-card.xsl` |
| `export-pdf` | Renders FDML to PDF via XHTML transform + OpenHTMLToPDF | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/PdfExporter.java`, `xslt/fdml-to-xhtml.xsl` |
| `index` | Builds `index.json` for discovery/search | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/Indexer.java` |
| `init` | Generates a starter FDML file template | `src/main/java/org/fdml/cli/Main.java`, `src/main/java/org/fdml/cli/Init.java` |

### Validation layers (XSD / Schematron / GEO / Timing / Lint)

| Layer | Current scope | Primary artifacts |
| --- | --- | --- |
| XSD | Structural constraints, enums, required attributes/elements | `schema/fdml.xsd`, `src/main/java/org/fdml/cli/FdmlValidator.java` |
| Schematron | Cross-field and business-rule assertions (including v1.2 geometry assertions) | `schematron/fdml.sch`, `schematron/fdml-compiled.xsl`, `src/main/java/org/fdml/cli/SchematronValidator.java` |
| GEO | Stateful geometry/topology invariants and issue codes | `src/main/java/org/fdml/cli/GeometryValidator.java`, `src/test/java/org/fdml/cli/GeometryValidatorTest.java` |
| Timing | Meter parsing and figure-level meter alignment checks | `src/main/java/org/fdml/cli/TimingValidator.java`, `src/test/java/org/fdml/cli/TimingValidatorTest.java`, `docs/TIMING-SPEC.md` |
| Lint | Non-fatal advisory checks around beat/meter consistency | `src/main/java/org/fdml/cli/Linter.java` |

### Site pipeline

- `make html` renders cards from `corpus/valid/*.xml` into `out/html/*.html`, then builds site artifacts.
- `scripts/build_index.sh` builds:
  - `site/cards/*.html`
  - `site/index.html`
  - `site/search.html`
  - `site/index.json` (via `bin/fdml index corpus/valid --out site/index.json`)
- Search UI is client-side over `site/index.json` (`docs/search.html`).
- Key evidence: `Makefile`, `scripts/build_index.sh`, `docs/search.html`, `src/main/java/org/fdml/cli/Indexer.java`.

### Missing for a “full product demo”

Based on current repo behavior, the following are missing or minimal:

1. Guided end-to-end user flow (author -> validate -> preview -> publish) with a single “demo” entrypoint.
2. Rich browse/search UX (metadata filters, sort, facets, deep-linkable queries).
3. High-fidelity visual choreography views (timeline, formation diagrams, animation).
4. Authoring ergonomics beyond `fdml init` (no editor assist, no schema-aware snippets/quick-fixes).
5. Hardened ingestion path from source documents (current ingestion scripts live under `analysis/` and are not productized).
6. Stronger release ergonomics (version policy docs/changelog automation, compatibility matrix, binary distribution story beyond current scripts/workflows).
7. Non-functional quality program beyond unit/snapshot tests (performance baselines, fuzz/property tests, regression dashboards).

## 2) Backlog (MoSCoW by category)

Legend: `M = Must`, `S = Should`, `C = Could`, `W = Won't (now)`.

### A) Site UX (search, filtering, navigation, example pages)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| M | Make discovery useful for demo audience | Add metadata facets (meter, formation, genre) + sort in search | `docs/search.html`, `src/main/java/org/fdml/cli/Indexer.java`, `scripts/build_index.sh` | `src/test/java/org/fdml/cli/IndexJsonTest.java`, add fixture docs in `corpus/valid` | Med |
| M | Improve navigation continuity | Add prev/next and breadcrumbs across cards/search/home | `xslt/card.xsl`, `docs/style.css`, `scripts/build_index.sh` | Extend `src/test/java/org/fdml/cli/RenderSnapshotTest.java` snapshot(s) | Low |
| S | Make example pages easier to scan | Add section anchors + sticky TOC on card pages | `xslt/card.xsl`, `docs/style.css` | Snapshot update in `src/test/resources/snapshots` | Low |
| C | Shareable query state | URL query params for filters + persisted search state | `docs/search.html` | Manual fixture check over `site/index.json` | Low |
| W | Full multi-language i18n | Defer to post-submission | N/A (rationale: large content/translation scope) | N/A | High |

### B) Rendering quality (card layout, print/PDF, accessibility)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| M | Demo-ready visual consistency | Refine card typography/spacing across generated HTML | `xslt/card.xsl`, `docs/style.css`, `xslt/style.css` | Snapshot updates in `src/test/resources/snapshots/example-01.html` | Low |
| M | Reliable print/PDF output | Align HTML and PDF templates; eliminate layout drift on key samples | `xslt/fdml-to-xhtml.xsl`, `src/main/java/org/fdml/cli/PdfExporter.java`, `scripts/gen_examples.sh` | Add regression fixture for one stable PDF source in `corpus/valid` | Med |
| S | Accessibility baseline | Add semantic landmarks, heading order, color contrast fixes | `xslt/card.xsl`, `docs/style.css`, `docs/search.html` | Add static checks in CI (e.g. link/heading lint script) | Med |
| C | Print stylesheet quality | Add dedicated print behavior for cards/search | `css/print.css`, `docs/style.css` | Manual visual fixture notes in `docs/` | Low |
| W | Full WCAG AA audit automation | Defer until post-submission | N/A (rationale: external tooling setup + remediation cycle) | N/A | Med |

### C) Visualizations/animation (step timeline, formation diagrams)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| S | Explain timing at a glance | Static step timeline component per figure (beats/counts) | `docs/search.html` (or new `docs/viewer.js`), `src/main/java/org/fdml/cli/Indexer.java` | Add timing-heavy fixtures: `corpus/valid/abdala.fdml.xml`, `corpus/invalid_timing/example-off-meter.fdml.xml` | Med |
| C | Visualize formations | SVG diagram renderer for circle/line/twoLines from geometry metadata | new `docs/geometry-viewer.js`, `src/main/java/org/fdml/cli/Indexer.java` | Geometry fixtures from `corpus/valid_v12` and `corpus/invalid_v12` | High |
| C | Demonstrate movement flow | Optional step-by-step animation scrubber | new frontend assets under `docs/` | Add lightweight UI smoke test script in `scripts/` | High |
| W | Real-time physics simulation | Defer; beyond submission scope | N/A (rationale: significant algorithm + UX complexity) | N/A | High |

### D) Authoring (init templates, editor helpers)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| M | Lower authoring friction | Extend `fdml init` profiles (`--profile v1.0|v1.2`, geometry stubs) | `src/main/java/org/fdml/cli/Init.java`, `src/main/java/org/fdml/cli/Main.java` | Add `src/test/java/org/fdml/cli/MainHelpTest.java` and new init-focused test | Low |
| S | Faster correction loop | Add `fdml doctor --explain` mapping issue codes -> remediation text | `src/main/java/org/fdml/cli/Doctor.java`, `src/main/java/org/fdml/cli/MainJson.java` | Extend doctor tests; fixtures from `corpus/invalid*` | Med |
| S | Editor usability | Provide VS Code snippets + schema association docs | new `.vscode/` snippets, `docs/USAGE.md` | No runtime tests; doc validation in CI optional | Low |
| C | Auto-fix simple issues | `fdml fix` for whitespace/id normalization/simple missing attrs | new CLI class under `src/main/java/org/fdml/cli` | Add before/after fixtures in `corpus/invalid` | Med |
| W | Full WYSIWYG editor | Defer; high UI surface not needed for submission | N/A (rationale: separate product track) | N/A | High |

### E) Ingestion (PDF/text -> FDML toolchain)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| S | Make ingestion reproducible | Promote one deterministic ingestion pipeline from `analysis/` into `scripts/` | `analysis/*.py`, new `scripts/ingest_*.sh`, `docs/` | Add gold fixtures under `analysis/gold` and schema-validate generated XML | High |
| S | Traceability of extracted data | Structured provenance sidecar (`.json`) linking source spans to FDML fields | `analysis/llm_extract_*.py`, `analysis/validate_llm_all.py` | Add provenance fixture in `analysis/gold/llm` | High |
| C | Human-in-the-loop review | CLI subcommand to open extraction diffs against corpus files | new CLI class + script glue | Add fixture pairs in `corpus/valid_v12_auto*` | Med |
| W | Fully automatic production ingestion | Defer until extraction accuracy/QA bar is established | N/A (rationale: high correctness risk) | N/A | High |

### F) Packaging (Homebrew, releases, versioning)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| M | Predictable release protocol | Versioning + release checklist doc (tag, assets, tap update, smoke checks) | `RUNBOOK.md`, `docs/CONTRIBUTING.md`, `CHANGELOG.md` | Add release dry-run script check in CI | Low |
| M | Artifact consistency | Ensure release builds run full test/CI gates before publish | `.github/workflows/release.yml`, `.github/workflows/ci.yml` | Workflow validation via PR checks | Med |
| S | Packaging confidence | Add post-install smoke matrix for macOS/Linux Java 17 | `.github/workflows/fdml-validate.yml`, new workflow file | Corpus spot-checks using `corpus/valid/example-01.fdml.xml` | Med |
| C | Additional distribution channel | Optional npm wrapper or standalone launcher | new packaging files | Basic invocation fixture | Med |
| W | Multi-runtime native binaries | Defer; build complexity vs current Java distribution | N/A (rationale: large toolchain lift) | N/A | High |

### G) Quality (coverage expansion, perf, fuzz tests)

| Pri | Goal | Concrete deliverable | Files likely touched | Tests/fixtures needed | Risk |
| --- | --- | --- | --- | --- | --- |
| M | Prevent coverage drift | Wire `make coverage` into CI gate and track matrix changes in PRs | `Makefile`, `.github/workflows/ci.yml`, `docs/COVERAGE.md`, `scripts/coverage_report.py` | Existing coverage script output as CI artifact | Low |
| M | Broaden semantic regression suite | Add targeted tests for CLI JSON contracts + error codes | `src/test/java/org/fdml/cli/*Test.java` | New fixtures across `corpus/invalid*` and `corpus/valid_v12` | Low |
| S | Track performance baseline | Add benchmark script for validate/doctor over full corpus | new `scripts/perf_validate.sh`, `docs/` | Stable corpus timing fixture snapshot | Med |
| S | Robustness hardening | Add lightweight fuzz/property tests for XML inputs and arg parsing | new test classes under `src/test/java/org/fdml/cli` | Generated malformed fixtures in `corpus/invalid` | Med |
| C | Mutation testing | Pilot mutation checks on validator core classes | `pom.xml` + test configuration | No fixture changes required initially | High |
| W | Distributed load testing | Defer; not aligned to single-node CLI usage profile | N/A (rationale: little product value now) | N/A | High |

## 3) Two-Phase Execution Plan

### Phase 1: Submission demo ready (low-risk, keep CI green)

Scope principles:
- Avoid high-risk architecture shifts.
- Prefer additive changes with fixture-backed tests.
- Keep `make ci` and `mvn test` green at each merge.

Planned delivery:
1. Site UX Must items:
   - Search facets/sort on existing `index.json` fields.
   - Navigation improvements on generated cards.
2. Rendering quality Must items:
   - Card polish and PDF consistency for representative examples.
3. Authoring Must item:
   - `fdml init` profile extension for v1.2-ready templates.
4. Packaging Must items:
   - Release protocol documentation and CI-reinforced release preconditions.
5. Quality Must items:
   - CI-enforced coverage report and expanded CLI/validator regression tests.

Exit criteria:
- Demo script can show: `init -> validate/doctor -> render/html -> search/index`.
- No red CI on main (`make ci`, `mvn test`, workflow checks).
- Updated docs for all touched surfaces.

### Phase 2: Post-submission (larger and/or riskier features)

Scope principles:
- Prioritize differentiation features (visualization/ingestion).
- Tolerate larger refactors behind test coverage expansion.

Planned delivery:
1. Visualization track:
   - Timeline and formation diagrams.
   - Optional animation scrubber.
2. Ingestion track:
   - Deterministic extraction pipeline with provenance sidecars.
   - Human-in-the-loop review tooling.
3. Quality and packaging expansion:
   - Perf baselines, fuzz/property tests, optional mutation testing.
   - Additional distribution hardening.

Exit criteria:
- Visual and ingestion features validated against existing corpus fixtures.
- Performance and robustness baselines documented and repeatable.
- Backward compatibility maintained for core CLI validation commands.

# FDML Core

Implementation of the FDML project: schema + validation (XSD + Schematron), transforms (XSLT), sample corpus, and test/CI scaffolding.

## Layout
- `schema/` — FDML XSD schema
- `schematron/` — business-rule validation
- `xslt/` — transformations (HTML card renderer, etc.)
- `css/` — stylesheets for rendered output
- `corpus/valid` and `corpus/invalid` — example FDML documents
- `docs/` — architecture/spec notes
- `test/` — unit, snapshot, e2e, perf scaffolding
- `.github/workflows/` — CI

## Getting Started
- Java 17 required (installed in Step 1).
- CI currently runs a placeholder `make ci`. Validation/build steps will be added in Step 3+.

## Licenses
- Code: MIT (`LICENSE`)
- Docs & corpus: CC BY 4.0 (`LICENSE-DATA`)

## Quick CLI

Build once:
```bash
mvn -q -DskipTests package

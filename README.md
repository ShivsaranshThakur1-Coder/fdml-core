[![render-test](https://github.com/ShivsaranshThakur1-Coder/fdml-core/actions/workflows/render-test.yml/badge.svg?branch=main)](https://github.com/ShivsaranshThakur1-Coder/fdml-core/actions/workflows/render-test.yml)

[![fdml-validate](https://github.com/ShivsaranshThakur1-Coder/fdml-core/actions/workflows/fdml-validate.yml/badge.svg?branch=main)](https://github.com/ShivsaranshThakur1-Coder/fdml-core/actions/workflows/fdml-validate.yml)

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
## Install (Homebrew)

~~~bash
brew tap ShivsaranshThakur1-Coder/fdml
brew install fdml
~~~

## Quick Start

```bash
fdml init song.fdml.xml --title "My Dance" --meter 3/4 --tempo 96 --figure-id f-1 --figure-name Intro
fdml validate song.fdml.xml
fdml validate corpus/valid/*.xml
fdml validate song.fdml.xml --json --json-out result.json
```

## Local CI

```bash
make ci
```

## Render

```bash
make html
open out/html/example-01.fdml.html
```

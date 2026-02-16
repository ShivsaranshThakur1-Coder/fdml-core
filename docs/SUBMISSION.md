# FDML — Submission Notes (Offline + Optional Pages)

This project ships as:
- a CLI (`./bin/fdml`)
- validators (XSD + Schematron + Geometry + Timing + Lint)
- a generated static demo site (`site/`)

## A) Offline / no-hosting demo (submission-safe)

### 1) Verify everything passes
Run:
- make ci
- mvn test

### 2) Build the demo site
Run:
- make html

This generates:
- site/index.html
- site/demo.html
- site/search.html
- site/cards/*.html (+ matching *.json)

### 3) View locally (recommended)
Because the site uses fetch() for JSON, it must be served over HTTP.

Run:
- make serve

Then open:
- http://localhost:8000/index.html
- http://localhost:8000/demo.html
- http://localhost:8000/search.html

## B) Optional GitHub Pages demo (if allowed)

GitHub Pages can publish either:
- from a branch folder (/ or /docs), or
- via a GitHub Actions workflow.

If you enable Pages for this repo, set:
Settings → Pages → Source = GitHub Actions (recommended).

Note: Pages is public by default, so do not use it for sensitive content.


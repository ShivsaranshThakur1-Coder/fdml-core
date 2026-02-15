# PHASE2_PLAN: Comprehensive Improvements

This plan uses the repo engineering method:

`Spec -> Impl -> Test -> Fixture -> CI -> Demo`

## 1) Progress

- 2026-02-15: DONE: A1 export-json
- 2026-02-15: DONE: A2 export-json schema + CI gate
- 2026-02-15: DONE: B1 timeline
- 2026-02-15: DONE: B2 diagrams
- 2026-02-15: DONE: C1 animation scrubber
- 2026-02-15: DONE: C2 init profiles
- 2026-02-15: DONE: D1 doctor --explain

## 2) Phase-2 Scope Map

- Visualization/Animation
- Export JSON
- Authoring
- Ingestion
- Publishing

## 3) Work Items (A1-E2)

| ID | Status | Scope | Deliverable | Repo files likely touched | Tests / fixtures required | CI gate to add / extend | Demo surface |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | DONE | Export JSON | `fdml export-json <input> --out <file>` command with deterministic ordering and stable keys | `src/main/java/org/fdml/cli/Main.java`, new `src/main/java/org/fdml/cli/ExportJson.java`, `src/main/java/org/fdml/cli/MainJson.java` | `src/test/java/org/fdml/cli/ExportJsonTest.java` for single file + directory mode; fixtures from `corpus/valid/example-03.fdml.xml` and `corpus/valid/abdala.fdml.xml` | Add `make ci` check that regenerates sample JSON and diffs against committed expected file | `site/demo.html` command block + downloadable sample JSON link |
| A2 | DONE | Export JSON | JSON contract spec + schema validation for exported payload (`v1`) | new `schema/export-json.schema.json`, `docs/FDML-SPEC.md`, `docs/USAGE.md` | Schema conformance test in `ExportJsonTest`; one invalid JSON fixture under `src/test/resources/export-json/invalid/` | Add CI step that validates generated JSON against schema | `site/demo.html` “Data Contract” section |
| B1 | DONE | Visualization/Animation | Timeline data model and timeline renderer for figures/steps (counts + meter labels) | `docs/search.html`, new `docs/timeline.js`, `docs/style.css`, `scripts/build_index.sh` (copy asset) | JS smoke test script for timeline placeholders; fixture targets `corpus/valid/abdala.fdml.xml` and `corpus/invalid_timing/example-off-meter.fdml.xml` | Extend `scripts/site_smoke.py` to require timeline container + script include | `site/cards/abdala.fdml.html` timeline section |
| B2 | DONE | Visualization/Animation | Formation diagrams (static) for line/circle/twoLines from exported geometry data | new `docs/diagram.js`, `docs/style.css`, `docs/search.html`, optional `src/main/java/org/fdml/cli/Indexer.java` for extra fields | Add card-level diagram fixture checks using `corpus/valid_v12/mayim-mayim.v12.fdml.xml` and `corpus/valid_v12/haire-mamougeh.v12.fdml.xml` | Extend site smoke to assert diagram mount node exists on v1.2 card pages | `site/cards/mayim-mayim.v12.fdml.html` geometry panel |
| C1 | DONE | Visualization/Animation | Animation scrubber layered on diagram state transitions (play/pause/scrub by count) | `docs/diagram.js`, new `docs/animate.js`, `docs/style.css` | Deterministic state-step test vectors under `src/test/resources/animation/`; invalid transition fixture from `corpus/invalid_v12` | Add CI check that generated transition trace hash is stable | `site/cards/haire-mamougeh.v12.fdml.html` animation controls |
| C2 | DONE | Authoring | Enhanced `init` templates (`--profile`) for common formations + timing-ready skeletons | `src/main/java/org/fdml/cli/Init.java`, `src/main/java/org/fdml/cli/Main.java`, template snippets in `src/main/resources/` if added | New `src/test/java/org/fdml/cli/InitProfileTest.java`; generated outputs validated by `doctor --strict` | Add matrix test in CI for all profiles | `site/demo.html` “Start authoring” section |
| D1 | DONE | Authoring | `doctor --explain` with issue remediation guidance and optional `--json --explain` payload | `src/main/java/org/fdml/cli/Doctor.java`, `src/main/java/org/fdml/cli/MainJson.java`, docs in `docs/USAGE.md` | Extend `src/test/java/org/fdml/cli/DoctorTimingTest.java` and add doctor explain tests on `corpus/invalid*` + `corpus/invalid_v12/*` | Add CI snapshot check for explain output (stable issue codes + advice IDs) | `site/demo.html` troubleshooting examples |
| D2 | TODO | Ingestion | Deterministic ingest CLI scaffold (`fdml ingest --source ... --out ...`) with minimal provenance | new `src/main/java/org/fdml/cli/Ingest.java`, `src/main/java/org/fdml/cli/Main.java`, `analysis/` helper wrappers as needed | One gold fixture in `analysis/gold/` to verify normalized output; one failure fixture for malformed source | Add CI smoke target for ingest on a tiny fixture | `site/demo.html` ingestion quickstart block |
| E1 | TODO | Ingestion | Provenance sidecar schema (`*.provenance.json`) and validator hook | new `schema/provenance.schema.json`, `analysis/` scripts, `docs/USAGE.md` | Schema validation test + fixture pair under `analysis/gold/` | Add CI check for provenance schema compliance | `site/demo.html` provenance section |
| E2 | TODO | Publishing | Release-quality publishing hardening: reproducible site manifest + pre-release gate | `scripts/build_index.sh`, new `scripts/site_manifest.py`, `Makefile`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `RUNBOOK.md` | Snapshot fixture for site manifest + reproducibility test (two builds, same checksums) | Extend `make ci`/GH Actions with manifest diff gate before release | `site/index.html` release badge/status note + demo checklist link |

## 4) Strict Definition-of-Done Checklist

An item is done only if every checkbox below is true.

- [ ] Spec
- [ ] Spec updated in docs with concrete input/output examples and issue codes (if applicable).
- [ ] Scope and non-goals explicitly written in the corresponding plan subsection.

- [ ] Impl
- [ ] Implementation merged with deterministic behavior (stable ordering, no time-dependent output).
- [ ] Backward compatibility verified for existing commands and current corpus.

- [ ] Test
- [ ] Happy-path test added/updated.
- [ ] Failure-path test added/updated.
- [ ] Exit code and key fields/assertions are explicit.

- [ ] Fixture
- [ ] At least one valid fixture and one invalid/edge fixture added or updated.
- [ ] Fixture names encode intent and map to a specific issue code or behavior.

- [ ] CI
- [ ] New or extended gate wired to `make ci` and/or GitHub Actions.
- [ ] Gate fails on regression with actionable error text.

- [ ] Demo
- [ ] Feature is visible in site demo surfaces.
- [ ] Copy-paste command shown in `site/demo.html` and result can be reproduced locally.

## 5) Linear Execution Order (Minimize Backtracking)

1. A1: Export JSON command foundation.
2. A2: Export JSON schema + contract tests.
3. B1: Timeline renderer using exported JSON.
4. B2: Static formation diagrams using the same JSON substrate.
5. C1: Animation scrubber on top of diagram state transitions.
6. C2: Authoring profile templates aligned to export/visualization needs.
7. D1: `doctor --explain` to improve correction loops during authoring.
8. D2: Ingest scaffold to feed the same JSON and validation pipeline.
9. E1: Provenance schema + validation wiring.
10. E2: Publishing reproducibility and release hardening.

Why this order:

- Export JSON first to create one canonical data contract.
- Timeline before diagrams/animation to validate timing semantics early with lower UI complexity.
- Diagrams before animation to avoid debugging visual state and motion simultaneously.
- Authoring and explainability after data/visual foundations to avoid rework.
- Ingestion and publishing hardening last so CI/release gates stabilize after feature shape is known.

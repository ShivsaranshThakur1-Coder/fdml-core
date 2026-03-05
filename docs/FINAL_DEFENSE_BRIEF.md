# Final Defense Brief (M7-K3)

Date: 2026-02-23

## 1) Project Objective

Build a deterministic, evidence-first FDML pipeline that can:
- acquire licensed folk-dance sources,
- convert text into structured FDML,
- validate output quality with strict gates,
- expose results in reproducible demo/search artifacts,
- and provide submission-ready evidence for academic defense.

## 2) Why This Matters

Most dance-description projects stop at static prose or unvalidated templates.  
This project demonstrates an end-to-end engineering system where data quality, modeling quality, and reproducibility are measured continuously and tied to milestone KPIs.

## 3) Method Summary

Pipeline layers:
- acquisition and licensing controls (`review-passrate`, `license-policy`)
- deterministic conversion batch with reproducibility checks
- strict validator quality gates (`doctor --strict`, provenance schema)
- semantic enrichment and issue/spec alignment gates
- full-description depth expansion and quality retention gates
- site/demo discoverability checks
- program/approval gates for milestone-level governance

Execution model:
- KPI-mapped work items (`analysis/program/work_items.csv`)
- automatic approval checks for all completed items
- deterministic artifact generation under `out/` and `site/`

## 4) Quantitative Results (Current)

Acquisition and conversion:
- review quality: 90/90 passed (85 wiki + 5 nonwiki)
- strict doctor: 90/90 (passRate 1.0000)
- provenance coverage: 90/90 schema-valid sidecars (coverage 1.0000)

Semantic quality:
- enriched semantic inventory: 15/15
- issue trend: issueTotal 0, strictFailFiles 0
- spec alignment: 35 discovered codes, 35 mapped, 0 missing

Full dance description depth (M6):
- strict coverage: baseline 1/90 (0.0111) -> current 67/90 (0.7444)
- relaxed coverage: baseline 3/90 (0.0333) -> current 82/90 (0.9111)
- strict-quality gate: 67/67 strict rows pass doctor (1.0000), placeholder-only 0

Demo/search readiness:
- search index items: 30
- full-description tiers: 3
- strict showcase items: 5
- source categories covered: 5

Submission rehearsal (M7-K2):
- final rehearsal report: PASS
- tests: 55 (failures 0, errors 0)
- packaged artifacts in rehearsal report: 14

## 5) Reproducibility Proof Points

Primary commands:
- `make ci`
- `mvn test`
- `make final-rehearsal-check`

Primary handoff artifacts:
- `out/final_rehearsal/report.json`
- `analysis/program/approval_report.json`
- `analysis/program/goal_state.json`
- `docs/SUBMISSION.md`
- `docs/COVERAGE.md`

## 6) Limitations (Defense-Ready)

- Internal-validity bias: gates prioritize consistency of this repository over external benchmark parity.
- Domain coverage is broad but incomplete for global folk-dance variation.
- Geometry/state modeling uses deterministic rule checks, not full physical simulation.
- Rendering verification is smoke-level, not full visual regression across browsers/devices.
- Source quality is bounded by upstream text quality and licensing constraints.

## 7) Future Work Roadmap

Phase R1 (near-term, 2-4 weeks):
- add external benchmark set for cross-repo validity checks
- add richer strict-description coverage targets beyond 67/90
- add deterministic rehearsal diff mode (before/after artifact hash comparison)

Phase R2 (mid-term, 1-3 months):
- expand semantic taxonomy for partner/formation transitions
- add stronger provenance lineage checks from source fragments to FDML sections
- improve site analytics facets for comparative dance retrieval

Phase R3 (long-term, 3-6 months):
- model higher-order temporal and topology transitions
- add visual-regression testing for render outputs
- evaluate translation to other choreography or movement-description domains

## 8) Defense Talking Points

- Engineering novelty: milestone-governed quality system, not a one-off converter.
- Measured improvement: strict full-description coverage raised from 1/90 to 67/90 without strict quality regression.
- Reproducibility: one command (`make final-rehearsal-check`) generates a deterministic final handoff report.
- Risk awareness: limitations are explicit and already mapped to future roadmap phases.

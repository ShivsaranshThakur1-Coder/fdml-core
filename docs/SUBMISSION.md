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

## C) Final Evaluation Package (M4 + M6 evidence, M25 hardening + M26 polish)

Use this sequence to produce a deterministic final evidence bundle:

1) Core quality and reproducibility gates:
- `make ci`
- `mvn test`

2) Explicit coverage/demo/baseline checks:
- `make full-description-coverage-check`
- `make full-description-quality-check`
- `make demo-flow-check`
- `make site-check`
- `make final-rehearsal-check`
- `make m25-hardening-check`
- `make m26-activation-check`
- `make m26-polish-baseline-check`
- `make m26-polish-execution-check`
- `make m26-governance-handoff-check`

3) Collect evidence artifacts:
- `analysis/program/approval_report.json`
- `analysis/program/goal_state.json`
- `out/demo_flow/demo_flow_report.json`
- `out/m2_conversion/run1/doctor_passrate.json`
- `out/m2_conversion/run1/provenance_coverage.json`
- `out/m3_semantic_inventory.json`
- `out/m3_issue_current.json`
- `out/m3_semantic_spec_alignment.json`
- `out/m6_full_description_baseline.json`
- `out/m6_full_description_current.json`
- `out/m6_full_description_quality.json`
- `out/final_rehearsal/report.json`
- `out/m25_hardening_report.json`
- `out/m26_activation_report.json`
- `out/m26_polish_baseline_report.json`
- `out/m26_polish_execution_report.json`
- `out/m26_handoff_governance_report.json`
- `site/index.json`

4) Review findings and constraints:
- findings matrix: `docs/COVERAGE.md` (Evaluation Findings section)
- limitations: `docs/COVERAGE.md` (Limitations and Known Gaps section)

Current local snapshot (2026-03-05):
- review quality: `109/109` pass (`out/acquired_sources/review.json`, `out/acquired_sources_nonwiki/review.json`)
- generated FDML strict validity: `109/109` pass (`out/m2_conversion/run1/doctor_passrate.json`)
- provenance coverage: `109/109` valid sidecars (`out/m2_conversion/run1/provenance_coverage.json`)
- semantic enrichment: `15/15` enriched (`out/m3_semantic_inventory.json`)
- semantic issue total: `0` (`out/m3_issue_current.json`)
- spec-alignment mapping: `35/35` codes (`out/m3_semantic_spec_alignment.json`)
- full-description strict coverage: baseline `1/90` -> current `78/109` (`out/m6_full_description_baseline.json`, `out/m6_full_description_current.json`)
- full-description quality: strict doctor `78/78` pass, placeholder-only `0` (`out/m6_full_description_quality.json`)
- demo/search discoverability: `129` indexed items, `3` description tiers, `109` strict items, `7` source categories (`out/demo_flow/demo_flow_report.json`)
- M25 final baseline package: PASS (`label=m25-final-product-baseline`, `active=M26`, `queuedGapCount=0`, `releaseReady=true`, `artifacts=11`) (`out/final_rehearsal/report.json`)
- M25 hardening gate: PASS (`out/m25_hardening_report.json`)
- M26 activation gate: PASS (`activeMilestone=M26`, `m26OpenRows=0`) (`out/m26_activation_report.json`)
- M26 polish baseline gate: PASS (`docGapCount=0`, `cleanupBacklogCount=1`) (`out/m26_polish_baseline_report.json`)
- M26 polish execution gate: PASS (`docGapAfter=0`, `docsMissingM26After=0`, `pycacheDirCountAfter=0`) (`out/m26_polish_execution_report.json`)
- M26 governance handoff gate: PASS (`finalReleaseReady=true`, `finalQueuedGapCount=0`, `out/m26_handoff_governance_report.json`; includes residual-risk ledger + hashed handoff artifact manifest)

## D) M19 Release-Readiness Addendum (2026-03-02)

Use this sequence for current M19 closeout-grade evidence:

1) M19 pipeline commands:
- `make m19-corpus-expansion-baseline-check`
- `make m19-descriptor-validator-expansion-check`
- `make m19-pipeline-governance-check`

2) M19 evidence artifacts:
- `out/m19_corpus_expansion_report.json`
- `out/m19_descriptor_uplift_report.json`
- `out/m19_fdml_coverage_report.json`
- `out/m19_validator_expansion_baseline_report.json`
- `out/m19_validator_expansion_report.json`
- `out/m19_validator_burndown_report.json`
- `out/m19_pipeline_governance.json`

3) Current M19 snapshot:
- corpus baseline: `90/90` files with country and region coverage at `1.0`; five-bucket target-per-bucket=`18` with backlog gaps (`africa +10`, `middle-east-caucasus +6`, `americas-oceania +3`)
- descriptor depth uplift: targeted files `89`, updated files `89`, strict doctor `90/90`, validate-geo `90/90`
- target descriptor support ratios raised to `1.0` for:
  - `descriptor.style.call_response_mode`
  - `descriptor.style.energy_profile`
  - `descriptor.style.improvisation_mode`
  - `descriptor.performance.impact_profile`
- validator layering: rule count `47`, candidate mapping `13/13`, no no-applicability rule violations
- burn-down: baseline failures `282` -> current `0`, reduction ratio `1.0`, failure-file ratio `0.0`
- governance: PASS with machine-readable decision/assumption/risk ledgers (`out/m19_pipeline_governance.json`)

Acceptance expectation:
- all commands above pass without manual intervention
- evidence artifacts are generated and internally consistent
- tracker/approval state shows no gate blockers for completed items

## I) M24 Release-Readiness Addendum (2026-03-04)

Use this sequence for current M24 closeout-grade evidence:

1) M24 pipeline commands:
- `make m24-residual-failure-closure-check`
- `make m24-descriptor-completion-check`
- `make m24-pipeline-governance-check`

2) M24 evidence artifacts:
- `out/m24_residual_failure_closure_report.json`
- `out/m24_validator_expansion_baseline_report.json`
- `out/m24_validator_expansion_report.json`
- `out/m24_validator_burndown_report.json`
- `out/m24_descriptor_completion_report.json`
- `out/m24_descriptor_registry.json`
- `out/m24_fdml_coverage_report.json`
- `out/m24_pipeline_governance.json`

## G) M22 Release-Readiness Addendum (2026-03-04)

Use this sequence for current M22 closeout-grade evidence:

1) M22 pipeline commands:
- `make m22-descriptor-uplift-check`
- `make m22-validator-expansion-check`
- `make m22-pipeline-governance-check`

2) M22 evidence artifacts:
- `out/m22_descriptor_uplift_report.json`
- `out/m22_descriptor_registry.json`
- `out/m22_fdml_coverage_report.json`
- `out/m22_validator_expansion_baseline_report.json`
- `out/m22_validator_expansion_report.json`
- `out/m22_validator_burndown_report.json`
- `out/m22_pipeline_governance.json`

3) Current M22 snapshot:
- descriptor uplift: files `109`, updated files `56`, source-grounded additions `89`, low-support keys `8`, low-support keys with growth `8`, low-support average support ratio `0.355505 -> 0.457569`, strict doctor `109/109`, validate-geo `109/109`
- validator layering: dedicated M22 rule count `20` (`alignment=16`, `coherence=4`), source-grounded applicable evaluations `1207`, coherence-applicable evaluations `224`, candidate mapping `13/13`
- burn-down: baseline failures `146` -> current `86`, reduction ratio `0.410959`, failure-file ratio `0.46789`
- governance: PASS with machine-readable decision/assumption/risk ledgers (`out/m22_pipeline_governance.json`)

Acceptance expectation:
- all commands above pass without manual intervention
- evidence artifacts are generated and internally consistent
- tracker/approval state shows no gate blockers for completed items

## H) M23 Release-Readiness Addendum (2026-03-04)

Use this sequence for current M23 closeout-grade evidence:

1) M23 pipeline commands:
- `make m23-descriptor-consolidation-check`
- `make m23-validator-expansion-check`
- `make m23-pipeline-governance-check`

2) M23 evidence artifacts:
- `out/m23_descriptor_consolidation_report.json`
- `out/m23_descriptor_registry.json`
- `out/m23_fdml_coverage_report.json`
- `out/m23_validator_expansion_baseline_report.json`
- `out/m23_validator_expansion_report.json`
- `out/m23_validator_burndown_report.json`
- `out/m23_pipeline_governance.json`

3) Current M23 snapshot:
- descriptor consolidation: files `109`, updated files `51`, source-grounded additions `82`, low-support keys `8`, low-support growth keys `8`, low-support average support ratio `0.631881 -> 0.725917`, residual potential-growth gap `91 -> 9`, strict doctor `109/109`, validate-geo `109/109`
- validator layering: dedicated M23 rule count `20` (`alignment=16`, `coherence=4`), source-grounded applicable evaluations `1187`, coherence-applicable evaluations `204`, candidate mapping `13/13`
- burn-down: baseline failures `86` -> current `6`, reduction ratio `0.930233`, failure-file ratio `0.045872`
- governance: PASS with machine-readable decision/assumption/risk ledgers (`out/m23_pipeline_governance.json`)

Acceptance expectation:
- all commands above pass without manual intervention
- evidence artifacts are generated and internally consistent
- tracker/approval state shows no gate blockers for completed items

## E) M20 Release-Readiness Addendum (2026-03-04)

Use this sequence for current M20 closeout-grade evidence:

1) M20 pipeline commands:
- `make m20-corpus-expansion-check`
- `make m20-descriptor-validator-expansion-check`
- `make m20-pipeline-governance-check`

2) M20 evidence artifacts:
- `out/m20_corpus_expansion_report.json`
- `out/m20_descriptor_evidence_report.json`
- `out/m20_fdml_coverage_report.json`
- `out/m20_validator_expansion_baseline_report.json`
- `out/m20_validator_expansion_report.json`
- `out/m20_validator_burndown_report.json`
- `out/m20_pipeline_governance.json`

3) Current M20 snapshot:
- corpus expansion: files `109`, M19 baseline gap total `19`, current residual gap `0`, reduction ratio `1.0`, improved buckets `3/3`, and no baseline-gap regressions
- descriptor evidence: updated files `60`, source-grounded additions `133`, keys with growth `8/8`, strict doctor `109/109`, validate-geo `109/109`
- validator layering: dedicated M20 rule count `8`, source-grounded applicable evaluations `351`, candidate mapping `13/13`
- burn-down: baseline failures `133` -> current `0`, reduction ratio `1.0`, failure-file ratio `0.0`
- governance: PASS with machine-readable decision/assumption/risk ledgers (`out/m20_pipeline_governance.json`)

Acceptance expectation:
- all commands above pass without manual intervention
- evidence artifacts are generated and internally consistent
- tracker/approval state shows no gate blockers for completed items

## F) M21 Release-Readiness Addendum (2026-03-04)

Use this sequence for current M21 closeout-grade evidence:

1) M21 pipeline commands:
- `make m21-descriptor-completion-check`
- `make m21-validator-expansion-check`
- `make m21-pipeline-governance-check`

2) M21 evidence artifacts:
- `out/m21_descriptor_completion_report.json`
- `out/m21_descriptor_registry.json`
- `out/m21_fdml_coverage_report.json`
- `out/m21_validator_expansion_baseline_m17_report.json`
- `out/m21_validator_expansion_m17_report.json`
- `out/m21_validator_expansion_baseline_report.json`
- `out/m21_validator_expansion_report.json`
- `out/m21_validator_burndown_report.json`
- `out/m21_pipeline_governance.json`

3) Current M21 snapshot:
- descriptor completion: files `109`, updated files `13`, source-grounded additions `18`, keys with growth `9`, strict doctor `109/109`, validate-geo `109/109`, style depth `88 -> 93`, cultural depth `102 -> 109`, combined depth `100 -> 105`
- validator layering: dedicated M21 rule count `16`, source-grounded applicable evaluations `983`, candidate mapping `13/13`
- burn-down: baseline failures `163` -> current `146`, reduction ratio `0.104294`, failure-file ratio `0.642202`
- governance: PASS with machine-readable decision/assumption/risk ledgers (`out/m21_pipeline_governance.json`)

Acceptance expectation:
- all commands above pass without manual intervention
- evidence artifacts are generated and internally consistent
- tracker/approval state shows no gate blockers for completed items

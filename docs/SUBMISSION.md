# FDML — Submission Notes (Offline + Optional Pages)

This project ships as:
- a CLI (`./bin/fdml`)
- validators (XSD + Schematron + Geometry + Timing + Lint)
- a generated static demo site (`site/`)
- a Git-tracked Pages deployment snapshot (`pages/`)

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

Deployment model used here:
- generate locally with `make html`
- sync tracked deploy snapshot with `make pages-sync`
- push `main`; `.github/workflows/pages.yml` publishes `pages/`

Note: Pages is public by default, so do not use it for sensitive content.

## B1) Deterministic Cloud Version-Control + Release Workflow (M27-K2)

Run documentation + wiring gate:
- `make m27-cloud-workflow-check`

Gate report artifact:
- `out/m27_cloud_workflow_report.json`

Use this deterministic GitHub CLI protocol:

1) Authenticate and sync:
- `gh auth status`
- `git fetch origin`
- `git checkout main`
- `git pull --ff-only origin main`

2) Create branch with required prefix:
- `git checkout -b codex/<scope>`

3) Run checks and commit scoped changes:
- `make m27-cloud-workflow-check`
- `git add <scoped-files>`
- `git commit -m "<message>"`

4) Push and open PR:
- `git push -u origin codex/<scope>`
- `gh pr create --base main --head codex/<scope> --fill`
- `gh pr view --web`

5) Merge and sync local main:
- `gh pr merge --squash --delete-branch`
- `git checkout main`
- `git pull --ff-only origin main`

6) Tag and publish release:
- `REL_TAG="vX.Y.Z"`
- `git tag -a "$REL_TAG" -m "FDML release $REL_TAG"`
- `git push origin "$REL_TAG"`
- `gh release create "$REL_TAG" --title "$REL_TAG" --notes-file docs/SUBMISSION.md`

## B2) Assessor Narrative and Walkthrough Package (M27-K3)

Run documentation + narrative package gate:
- `make m27-assessor-package-check`

Gate report artifact:
- `out/m27_assessor_package_report.json`

Assessor-facing walkthrough source:
- `docs/ASSESSOR_WALKTHROUGH.md`

This package provides:
- project explanation in normal language (non-code)
- deterministic live demo command path for evaluation
- claim-to-artifact evidence mapping for rubric-aligned defense
- explicit scope limits and portfolio framing for assessor review

## B3) M28 Activation and Queue Governance Baseline

Run activation gate:
- `make m28-activation-check`

Gate report artifact:
- `out/m28_activation_report.json`

This confirms:
- `M27` is completed and `M28` is the sole active milestone
- M28 queue seeding is present (`PRG-271` onward)
- goal-state + program-plan + CI wiring are synchronized for the next execution cycle

## B4) M28 Website Narrative Baseline (PRG-271)

Run narrative baseline gate:
- `make m28-narrative-baseline-check`

Gate report artifact:
- `out/m28_narrative_baseline_report.json`

This report publishes:
- prioritized website narrative correction backlog (severity + effort + evidence + recommendation)
- deterministic mismatch signals across `DEMO`, `SEARCH`, `SUBMISSION`, and tracker state
- execution handoff payload for `PRG-272` correction implementation

## B5) M28 Website Narrative Execution (PRG-272)

Run narrative execution gate:
- `make m28-narrative-execution-check`

Gate report artifact:
- `out/m28_narrative_execution_report.json`

This confirms:
- corrected M28 narrative wiring is reflected in generated demo surfaces
- high-priority baseline mismatch set from `PRG-271` is resolved
- CI/tracker/doc synchronization is ready for final M28 governance handoff

## B6) M28 Governance + Final Showcase Handoff (PRG-273)

Run governance handoff gate:
- `make m28-governance-handoff-check`

Gate report artifact:
- `out/m28_governance_handoff_report.json`

This confirms:
- activation/baseline/execution report chain remains PASS with backlog closure
- demo/build-index/site-smoke synchronize on `reports/m28_governance_handoff.report.json`
- tracker (`PRG-273`) and CI wiring are deterministic and replayable for final showcase delivery

## B7) M26 Archive-Safe CI Stabilization (PRG-274)

Run archive gate:
- `make m26-archive-check`

Gate report artifact:
- `out/m26_archive_gate_report.json`

This confirms:
- M26 remains completed with zero open M26 rows while active milestone is M29
- required M26 closeout work (`PRG-260` to `PRG-264`) remains done
- default CI uses archive-safe M26 validation instead of rerunning milestone-active M26 gates

## B8) M28 Archive and M29 Activation (PRG-275)

Run archive and activation gates:
- `make m28-archive-check`
- `make m29-activation-check`

Gate report artifacts:
- `out/m28_archive_gate_report.json`
- `out/m29_activation_report.json`

This confirms:
- M28 remains completed with zero open M28 rows while active milestone is M29
- required M28 closeout work (`PRG-270` to `PRG-274`) remains done
- M29 activation invariants are synchronized across plan, goal state, queue seeding, and CI wiring

## B9) M29 Release-Workflow Baseline (PRG-276)

Run baseline gate:
- `make m29-release-baseline-check`

Gate report artifact:
- `out/m29_release_baseline_report.json`

This confirms:
- M29 activation state remains valid and synchronized across plan/goal-state/work tracker
- M29 release baseline backlog is generated with deterministic priority ordering and linked next-work ids
- release-facing docs and CI wiring stay aligned on one command path for `PRG-276` handoff to `PRG-277`

## B10) M29 Delivery Stabilization Execution (PRG-277)

Run execution gate:
- `make m29-delivery-stabilization-check`

Gate report artifact:
- `out/m29_delivery_stabilization_report.json`

This confirms:
- `PRG-277` is completed and synchronized across work tracker, step map, docs, and CI
- M29 backlog closure state is recorded with deterministic resolution statuses
- final rehearsal queued-gap and open-queue targets are reduced to the expected post-PRG-277 state

## B11) M29 Governance Freeze (PRG-278)

Run governance freeze gate:
- `make m29-governance-freeze-check`

Gate report artifact:
- `out/m29_governance_freeze_report.json`

This confirms:
- `PRG-278` is done and M29 queue is frozen (`open M29 rows = 0`)
- M29 activation/baseline/delivery/final-rehearsal reports stay synchronized and PASS
- release docs and demo snapshot wiring are synchronized to one freeze command and artifact path
- a hashed freeze artifact manifest is published for deterministic handoff replay

## B12) M29 Archive and M30 Activation (PRG-279)

Run archive and activation gates:
- `make m29-archive-check`
- `make m30-activation-check`

Gate report artifacts:
- `out/m29_archive_gate_report.json`
- `out/m30_activation_report.json`

This confirms:
- M29 remains completed with zero open M29 rows while active milestone is M30
- required M29 closeout work (`PRG-275` to `PRG-278`) remains done
- M30 activation invariants are synchronized across plan, goal state, queue seeding, and CI wiring

## B13) M30 Repository Hygiene Baseline (PRG-280)

Run baseline gate:
- `make m30-repo-baseline-check`

Gate report artifact:
- `out/m30_repo_baseline_report.json`

This confirms:
- M30 activation state remains valid and synchronized across plan/goal-state/work tracker
- M30 repository cleanup baseline backlog is generated with deterministic priority ordering and linked next-work ids
- release-facing docs and CI wiring stay aligned on one command path for `PRG-280` handoff to `PRG-281`

## B14) M30 Repository Cleanup Execution (PRG-281)

Run execution gate:
- `make m30-repo-execution-check`

Gate report artifact:
- `out/m30_repo_execution_report.json`

This confirms:
- `PRG-281` is completed and synchronized across work tracker, step map, docs, and CI
- M30 baseline backlog closure state is recorded with deterministic resolution statuses
- final rehearsal queued-gap and open-queue targets are reduced to expected post-PRG-281 values for handoff to `PRG-282`

## B15) M30 Governance and Package Handoff (PRG-282)

Run governance gate:
- `make m30-governance-check`

Gate report artifact:
- `out/m30_governance_report.json`

This confirms:
- `PRG-282` is completed and M30 queue is frozen closed (`open M30 rows = 0`)
- final rehearsal is release-ready (`queuedGapCount = 0`, `releaseReady = true`)
- release docs and demo snapshot wiring are synchronized to one governance command and artifact path
- a hashed final-package replay manifest is published for deterministic handoff

## B16) M30 Archive and M31 Post-Completion Control (PRG-283)

Run archive and activation gates:
- `make m30-archive-check`
- `make m31-activation-check`

Gate report artifacts:
- `out/m30_archive_gate_report.json`
- `out/m31_activation_report.json`

This confirms:
- M30 remains completed with zero open M30 rows under later active milestones
- required M30 closeout work (`PRG-279` to `PRG-282`) remains done
- M31 is the sole active milestone and holds a zero-queue post-completion control state
- default CI now validates archive-safe M30 invariants instead of rerunning milestone-active M30 gates

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
- `make m26-archive-check`
- `make m28-archive-check`
- `make m29-archive-check`
- `make m30-archive-check`
- `make m31-activation-check`

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
- `out/m30_archive_gate_report.json`
- `out/m31_activation_report.json`
- `out/m26_archive_gate_report.json`
- `out/m26_activation_report.json`
- `out/m26_polish_baseline_report.json`
- `out/m26_polish_execution_report.json`
- `out/m26_handoff_governance_report.json`
- `out/m28_archive_gate_report.json`
- `out/m29_archive_gate_report.json`
- `out/m29_activation_report.json`
- `out/m29_release_baseline_report.json`
- `out/m29_delivery_stabilization_report.json`
- `out/m29_governance_freeze_report.json`
- `out/m30_activation_report.json`
- `out/m30_repo_baseline_report.json`
- `out/m30_repo_execution_report.json`
- `out/m30_governance_report.json`
- `out/m28_governance_handoff_report.json`
- `site/index.json`

4) Review findings and constraints:
- findings matrix: `docs/COVERAGE.md` (Evaluation Findings section)
- limitations: `docs/COVERAGE.md` (Limitations and Known Gaps section)

Current local snapshot (2026-03-07):
- review quality: `109/109` pass (`out/acquired_sources/review.json`, `out/acquired_sources_nonwiki/review.json`)
- generated FDML strict validity: `109/109` pass (`out/m2_conversion/run1/doctor_passrate.json`)
- provenance coverage: `109/109` valid sidecars (`out/m2_conversion/run1/provenance_coverage.json`)
- semantic enrichment: `15/15` enriched (`out/m3_semantic_inventory.json`)
- semantic issue total: `0` (`out/m3_issue_current.json`)
- spec-alignment mapping: `35/35` codes (`out/m3_semantic_spec_alignment.json`)
- full-description strict coverage: baseline `1/90` -> current `78/109` (`out/m6_full_description_baseline.json`, `out/m6_full_description_current.json`)
- full-description quality: strict doctor `78/78` pass, placeholder-only `0` (`out/m6_full_description_quality.json`)
- demo/search discoverability: `129` indexed items, `3` description tiers, `109` strict items, `7` source categories (`out/demo_flow/demo_flow_report.json`)
- M25 final baseline package: PASS (`label=m25-final-product-baseline`, `queuedGapCount=0`, `releaseReady=true`, `artifacts=11`) (`out/final_rehearsal/report.json`)
- M25 hardening gate: PASS (`out/m25_hardening_report.json`)
- M26 archive gate: PASS (`checks=25/25`) (`out/m26_archive_gate_report.json`)
- M26 activation gate: legacy milestone-specific gate (`requiredActiveMilestone=M26`); rerunning under active `M31` yields expected mismatch (`out/m26_activation_report.json`)
- M26 polish baseline gate: historical M26 closeout artifact (`out/m26_polish_baseline_report.json`)
- M26 polish execution gate: historical M26 closeout artifact (`out/m26_polish_execution_report.json`)
- M26 governance handoff gate: historical M26 closeout artifact (`out/m26_handoff_governance_report.json`; includes residual-risk ledger + hashed handoff artifact manifest)
- M28 activation gate: PASS (`activeMilestone=M28`, `m28OpenRows=0`) (`out/m28_activation_report.json`)
- M28 website narrative baseline gate: PASS (`checks=12/12`, `backlogCount=0`) (`out/m28_narrative_baseline_report.json`)
- M28 website narrative execution gate: PASS (`checks=16/16`) (`out/m28_narrative_execution_report.json`)
- M28 governance handoff gate: PASS (`checks=20/20`, `PRG-273=done`) (`out/m28_governance_handoff_report.json`)
- M28 archive gate: PASS (`out/m28_archive_gate_report.json`)
- M29 activation gate: PASS (`activeMilestone=M29`) (`out/m29_activation_report.json`)
- M29 governance freeze gate: PASS (`PRG-278=done`, `m29OpenRows=0`) (`out/m29_governance_freeze_report.json`)
- M29 archive gate: PASS (`checks=24/24`, `M29.status=completed`) (`out/m29_archive_gate_report.json`)
- M30 activation/baseline/execution/governance gates: historical active-milestone artifacts preserved from the M30 execution window (`out/m30_activation_report.json`, `out/m30_repo_baseline_report.json`, `out/m30_repo_execution_report.json`, `out/m30_governance_report.json`)
- M30 archive gate: PASS (`M30.status=completed`, `open_m30_rows=0`) (`out/m30_archive_gate_report.json`)
- M31 activation gate: PASS (`activeMilestone=M31`, `m31OpenRows=0`) (`out/m31_activation_report.json`)

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

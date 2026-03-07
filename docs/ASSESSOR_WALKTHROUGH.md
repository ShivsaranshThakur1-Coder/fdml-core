# FDML Assessor Walkthrough Package (M27-K3)

Date: 2026-03-05

## 1) Project In Plain Language

This project builds a reliable system for describing folk dances in a structured way instead of only using free-form text.

In plain terms, the system:
- reads dance-source material,
- converts it into one FDML structure,
- checks the result with deterministic validators,
- publishes searchable demo cards,
- and produces machine-readable evidence reports to prove quality.

## 2) What Is Stored In FDML (Non-Code)

Each dance file stores:
- identity: title, source id, source category, origin metadata
- musical context: meter and tempo
- group structure: formation kind (line, circle, couple, two-lines-facing)
- movement description: ordered full-description steps (not placeholders)
- geometry readiness: whether the dance is compatible with v1.2 geometry checks
- provenance context: source linkage and conversion traceability

This creates one general structure for all corpus examples, instead of separate ad-hoc templates per subset.

## 3) How Validation Works (Non-Code)

Validation is a layered quality system:
- structure validators: enforce FDML shape and required fields
- strict quality validators: reject weak/placeholder dance descriptions
- geometry validators: enforce spatial consistency for geometry-ready files
- governance validators: ensure docs, tracker state, and release evidence stay synchronized

The key point for assessment:
- quality is not claimed by narrative only
- quality is demonstrated by repeatable command outputs and reports

## 4) Live Demonstration Script (10-12 Minutes)

### Step A: Verify pipeline health

Run:
- `make final-rehearsal-check`
- `make site-check`
- `make m27-cloud-workflow-check`
- `make m27-assessor-package-check`

Explain:
- these commands regenerate quality/governance evidence,
- and fail if core claims are not true.

### Step B: Show public demo surfaces

Open:
- `site/demo.html`
- `site/search.html`

Explain:
- demo dashboard uses report snapshots, not hardcoded numbers,
- search can filter by strict description tier, source category, and geometry readiness.

### Step C: Show evidence artifacts

Open:
- `out/final_rehearsal/report.json`
- `out/m27_cloud_workflow_report.json`
- `out/m27_assessor_package_report.json`
- `analysis/program/goal_state.json`

Explain:
- release readiness, queue state, and narrative package checks are machine-verifiable.

### Step D: Show one concrete dance example path

Open one strict card from search (for example a strict + geometry-ready item), then explain:
- where the description is stored,
- what validators enforced,
- how that file appears in index/search metadata.

## 5) Evidence Map (Claim -> Artifact)

| Claim | Artifact | What Assessor Checks |
|---|---|---|
| Pipeline is reproducible | `out/final_rehearsal/report.json` | `ok=true`, deterministic artifact list, release-ready summary |
| Site/demo reflects current pipeline state | `site/demo.html` + `site/reports/*.json` | dashboard values come from report snapshots |
| Search supports depth and coverage inspection | `site/search.html` + `site/index.json` | strict tier, geometry, source-category filtering works |
| Cloud workflow is formalized and reproducible | `out/m27_cloud_workflow_report.json` | branch/PR/release protocol checks pass |
| Assessor narrative package is complete | `out/m27_assessor_package_report.json` | walkthrough + submission + governance links validated |
| Program execution is auditable | `analysis/program/work_items.csv`, `analysis/program/goal_state.json` | M27 queue state, done/planned counts, next item traceability |

## 6) Limitations And Scope

Current system does not claim full world-level cultural exhaustiveness.

It does provide:
- a strong single-pipeline engineering foundation,
- deterministic quality gates,
- measurable evidence for what is covered now,
- and explicit visibility into remaining scope.

## 7) Portfolio Framing (For CV + Recording)

Position this as:
- a production-style data/validation pipeline project,
- with deterministic QA gates, governance automation, and evidence-first delivery,
- not just a static markup or dataset exercise.

Suggested one-line framing:
- "Built an end-to-end FDML folk-dance modeling pipeline with deterministic validation, governance gates, and portfolio-grade demo/search evidence surfaces."

## 8) Assessor Q&A Anchors

If asked "How do you prove this is not manual narration?":
- show `make final-rehearsal-check` and generated reports.

If asked "How do you know docs and claims stay consistent?":
- show `make m27-assessor-package-check` and report checks.

If asked "How does this scale beyond one dance?":
- show corpus-wide `site/index.json` and strict/geometry filters in search.

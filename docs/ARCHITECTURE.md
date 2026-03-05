# FDML Architecture

This document defines the production architecture for `fdml-core` at the M25 stage.
The project operates as one deterministic, corpus-wide pipeline with governance gates.

## System Scope

The repository provides:
- a CLI (`./bin/fdml`) for validation, rendering, ingestion, and indexing
- schema/rule validation (`XSD`, `Schematron`, geometry/timing/semantic validators)
- deterministic pipeline scripts under `scripts/`
- static demo/search output under `site/`
- program governance state under `analysis/program/`

Primary objective at this stage:
- preserve one canonical folk-dance FDML pipeline across all active files
- enforce anti-drift checks in CI
- keep results reproducible with machine-readable artifacts

## Canonical Data Pipeline

The canonical artifact chain is:
1. Source acquisition (`out/acquired_sources`, `out/acquired_sources_nonwiki`)
2. Deterministic conversion (`out/m2_conversion/run1`)
3. Promotion and descriptor/validator expansion stages (M9-M24 outputs)
4. Residual closure and saturation:
   - `out/m24_residual_failure_closure/run1`
   - `out/m24_descriptor_completion/run1`
5. Governance and closeout:
   - `out/m24_pipeline_governance.json`
   - `out/final_rehearsal/report.json`

Within M24/M25, the validator baseline/current invariants are fixed:
- baseline corpus: `out/m23_descriptor_consolidation/run1`
- current corpus: `out/m24_residual_failure_closure/run1`
- descriptor completion corpus: `out/m24_descriptor_completion/run1`

## Validation And Quality Gates

Validation stack:
- XSD structure validation
- Schematron business-rule validation
- Java validator layers (`GeometryValidator`, `TimingValidator`, `Linter`, `Doctor`)
- corpus quality gates (`doctor-passrate`, provenance coverage, descriptor/validator governance)

Program and milestone control gates:
- `make program-check`
- `make task-approval-check`
- `make goal-state-check`

M24/M25 closeout gates:
- `make m24-pipeline-governance-check`
- `make final-rehearsal-check`
- `make m25-hardening-check`

## Component Boundaries

Core component classes:
- CLI entry/commands:
  - `src/main/java/org/fdml/cli/Main.java`
  - `src/main/java/org/fdml/cli/Doctor.java`
  - `src/main/java/org/fdml/cli/Indexer.java`
  - `src/main/java/org/fdml/cli/Ingest.java`
- validators:
  - `src/main/java/org/fdml/cli/GeometryValidator.java`
  - `src/main/java/org/fdml/cli/TimingValidator.java`
  - `src/main/java/org/fdml/cli/Linter.java`
- render/index outputs:
  - `src/main/java/org/fdml/cli/Renderer.java`
  - `src/main/java/org/fdml/cli/JsonExporter.java`

Pipeline automation:
- stage-specific Python scripts in `scripts/`
- target orchestration via `Makefile`

Governance and state:
- `analysis/program/plan.json`
- `analysis/program/work_items.csv`
- `analysis/program/goal_state.json`
- `analysis/program/approval_report.json`

## Testing Strategy

Testing is multi-layered:
- Java unit/integration tests via `mvn test`
- validator and schema checks via `make ci`
- fixture-backed gate scripts for milestone invariants
- state/model integrity checks for program execution

M25 testing hardening focus:
- ensure final baseline report is M25-aware (not legacy M7-only)
- verify docs and make targets stay synchronized with active milestone
- enforce CI inclusion for new hardening checks

## Program Governance

Execution is milestone/KPI-driven:
- exactly one active milestone at a time
- done items require evidence and approval-gate pass
- active queue and next step are derived from machine state

Release readiness is measured by:
- governance gate pass status
- quality metrics from current canonical corpus
- explicit open-gap ledger in `out/final_rehearsal/report.json`

At M25, `releaseReady` remains `false` until all queue items complete and the
milestone is formally closed.

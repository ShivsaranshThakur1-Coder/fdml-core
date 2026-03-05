## FDML v1.2 Geometry Extension

FDML v1.2 adds an optional geometry layer that makes formations and movement constraints explicit and machine-checkable. This supports invariants that are difficult to express in XSD/Schematron alone (e.g., order preservation in circles; formation–primitive compatibility).

### Files and commands

Validate geometry for all v1.2 valid examples:

```bash
./bin/fdml validate-geo corpus/valid_v12
```

Validate geometry for invalid examples (expected to FAIL with exit code 2):

```bash
./bin/fdml validate-geo corpus/invalid_v12
```

Run the full “doctor” pipeline (XSD + Schematron + GEO + Lint) on the v1.2 examples:

```bash
./bin/fdml doctor --strict corpus/valid_v12/mayim-mayim.v12.fdml.xml
./bin/fdml doctor --strict corpus/valid_v12/haire-mamougeh.v12.fdml.xml
```

Show remediation guidance per issue code:

```bash
./bin/fdml doctor corpus/invalid_timing/example-off-meter.fdml.xml --explain
./bin/fdml doctor corpus/invalid_timing/example-off-meter.fdml.xml --json --explain
```

Example v1.2 files in this repo:

Valid:
- corpus/valid_v12/mayim-mayim.v12.fdml.xml
- corpus/valid_v12/haire-mamougeh.v12.fdml.xml

Invalid (intentionally fails GEO validation):
- corpus/invalid_v12/haire-mamougeh.bad-formation.v12.fdml.xml
- corpus/invalid_v12/mayim-mayim.order-broken.v12.fdml.xml

### Regenerate compiled Schematron

`schematron/fdml-compiled.xsl` is generated from `schematron/fdml.sch` using a pinned, vendored compiler jar in `tools/`.

Regenerate it after any Schematron rule changes:

```bash
make schematron
```

Validate that the committed compiled output is up to date:

```bash
make check-schematron
```

### v1.2 structure (minimum required)

For fdml version="1.2" the geometry validator requires:
- meta/geometry/formation/@kind (e.g., circle, twoLinesFacing, couple)
- If roles are declared in meta/geometry/roles, then any @who references in steps/primitives must refer to declared role IDs.
- Per-step geometry primitives are expressed under step/geo/primitive and each primitive must have @kind.

See: docs/GEOMETRY-SPEC.md for the full schema and intended semantics.

### Current validator rules (GeometryValidator)

- v1.2 requires meta/geometry/formation/@kind.
- Each step/geo/primitive must have @kind.
- If roles exist, step/@who and primitive/@who must reference a declared role.
- approach / retreat primitives only allowed for formation/@kind="twoLinesFacing".
- Circle order preservation proxy: if any primitive has preserveOrder="true", then crossing primitives (pass, weave, swapPlaces) trigger circle_order_violation.

### Interpreting GEO failures

validate-geo prints either GEO OK or GEO FAIL plus issue codes like:
- missing_formation_kind
- missing_primitive_kind
- unknown_role
- bad_formation_for_approach_retreat
- circle_order_violation

## Export JSON Contract (v1)

Generate export JSON for a file or directory:

```bash
./bin/fdml export-json corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml --out out/export.json
./bin/fdml export-json corpus/valid --out out/export-batch.json
```

Contract schema:
- `schema/export-json.schema.json`

Validate any export artifact against the contract:

```bash
python3 scripts/validate_json_schema.py schema/export-json.schema.json out/export.json
```

CI/local gate:
- `make export-json-check` regenerates `site/export-json-sample.json` and validates it against the v1 contract schema.

## M11 Unified Contract Promotion

Generate the M11 unified FDML contract promotion artifact from M10 ontology candidates:

```bash
make m11-contract-promotion-check
```

This command writes:
- `out/m11_contract_promotion.json`

Inputs used by the promotion step:
- `out/m10_ontology_candidates.json`
- `schema/fdml.xsd`
- `docs/FDML-SPEC.md`

Run the unified validator stack report (same rules over full promoted corpus):

```bash
make m11-validator-unified-check
```

This command writes:
- `out/m11_validator_unified_report.json`

Inputs used by the unified validator step:
- `out/m9_full_description_uplift/run1`
- `out/m10_validator_candidates.json`
- `out/m11_contract_promotion.json`

Run unified pipeline governance gate (M11-K3):

```bash
make m11-pipeline-governance-check
```

This enforces:
- fixture pass/fail behavior for `scripts/m11_pipeline_governance_gate.py`
- `make ci` wiring includes unified validator + M11 governance gate
- `make html` wiring includes unified validator prerequisite
- live contract + validator + demo/search/site alignment on unified corpus path

Live report output:
- `out/m11_pipeline_governance.json`

Run semantic-depth and rule-depth governance gate (M12-K1):

```bash
make m12-semantic-depth-check
```

This enforces:
- rubric-driven per-dimension coverage thresholds for folk-dance description depth
- minimum average semantic coverage and per-file dimension richness
- minimum ontology/validator/contract/rule-depth counts
- fixture pass/fail behavior for `scripts/m12_semantic_depth_gate.py`

Live report output:
- `out/m12_semantic_depth_report.json`

Note:
- this gate is not in `make ci` yet, because it is intended to expose remaining semantic-depth gaps before promoting M12 quality thresholds into default CI.

## M13 Parameter Registry (Full-Corpus)

Build deterministic, evidence-linked parameter coverage from the full promoted corpus:

```bash
make m13-parameter-registry-check
```

This command writes:
- `out/m13_parameter_registry.json`
- `out/m13_fdml_fit_report.json`

Inputs used by the registry step:
- `out/m9_full_description_uplift/run1`

Registry output includes:
- canonical FDML parameter keys with group/path/type metadata
- support counts and support ratios across the full corpus
- distinct/top observed values
- evidence sample per key (file + text span)

Fit output includes:
- per-file missing-core-key analysis for the unified FDML structure
- fit classes (`fully_fit`, `near_fit`, `partial_fit`, `requires_contract_expansion`)
- missing-core frequency summary for contract expansion prioritization
- expressive-fit analysis using formation-aware advanced-key requirements
- context-specificity diagnostics (placeholder vs non-placeholder context values)
- deterministic contract-expansion priority tiers (`P0`, `P1`, `P2`) with recommended actions

Run expanded validator stack derived from M13 registry priorities:

```bash
make m13-validator-expansion-check
```

This command writes:
- `out/m13_validator_expansion_report.json`

Expanded validator report includes:
- one deterministic full-corpus rule stack mapped from `P0/P1` contract-expansion keys
- per-rule applicability, pass/fail counts, and explicit failure-code taxonomy
- priority-key coverage audit (mapped vs missing)
- file-level failed-rule inventory for remediation planning

Run M13 anti-drift pipeline governance gate:

```bash
make m13-pipeline-governance-check
```

This command writes:
- `out/m13_pipeline_governance.json`

Governance output includes:
- chain checks across M10 discovery governance, M11 contract promotion, M13 registry/fit, and M13 validator expansion
- single-corpus-path invariants for M13 targets (`out/m9_full_description_uplift/run1`)
- decision registry (chosen options, alternatives, tradeoffs, reversal conditions)
- assumption registry (confidence, verification plans, invalidation signals)
- risk ledger (severity/likelihood signals with mitigations)

## M14 Contract Uplift (P0/P1)

Run deterministic full-corpus contract uplift for highest-impact M13 P0/P1 gaps:

```bash
make m14-contract-uplift-check
```

This command writes:
- `out/m14_contract_uplift/run1` (uplifted full corpus)
- `out/m14_parameter_registry.json` (post-uplift registry snapshot)
- `out/m14_fdml_fit_report.json` (post-uplift fit snapshot)
- `out/m14_contract_uplift_report.json` (before/after uplift summary)

The uplift step deterministically fills high-impact contract fields on the unified corpus path:
- `meta.geometry.dancers.count`
- `meta.geometry.hold.kind` (couple formations)
- `step.geo.primitive.axis`
- `step.geo.primitive.dir`
- `step.geo.primitive.frame`
- `step.geo.primitive.preserveOrder` (circle formations)

The report enforces:
- strict doctor and geometry validation pass-rate thresholds on uplifted outputs
- minimum reduction in expressive contract-expansion backlog vs M13 baseline
- minimum count of improved targeted key support metrics

Run deterministic context-specificity normalization and gate:

```bash
make m14-context-specificity-check
```

This command writes:
- `out/m14_context_specificity/run1` (context-normalized full corpus)
- `out/m14_context_specificity_report.json`
- `out/m14_context_parameter_registry.json`
- `out/m14_context_fdml_fit_report.json`

The context gate performs:
- evidence-linked extraction of `meta.origin.country` from acquired source text/title
- deterministic mapping from inferred country to `meta.origin.region`
- strict doctor + geometry re-validation on normalized outputs
- threshold checks for non-placeholder country/region coverage (>=90% each)
- context-gap reduction checks against the baseline fit report

Run deterministic validator failure burn-down gate:

```bash
make m14-validator-burndown-check
```

This command writes:
- `out/m14_validator_expansion_report.json`
- `out/m14_validator_burndown_report.json`

Burn-down gate enforces:
- one expanded validator stack over `out/m14_context_specificity/run1`
- baseline-to-current failure reduction ratio of at least `70%` (against `out/m13_validator_expansion_report.json`)
- maximum files-with-any-failure ratio of `30%`
- full-corpus processing minimum (`>=90` files), expanded-rule minimum (`>=10`), and applicability/mapping integrity checks

Run M15 full-corpus exhaustive descriptor discovery:

```bash
make m15-discovery-run
```

This command writes:
- `out/m15_discovery/run1/discovery_report.json`
- `out/m15_ontology_candidates.json`
- `out/m15_validator_candidates.json`
- `out/m15_coverage_gaps.json`

The M15 discovery run:
- uses `out/m14_context_specificity/run1` as the full-corpus input path
- performs deterministic multi-pass discovery (`passes=5`) with growth/saturation tracking
- emits evidence-linked ontology and validator candidate ledgers for downstream M15 contract and rule expansion

Run M15 validator expansion and burn-down:

```bash
make m15-validator-expansion-check
```

This command writes:
- `out/m15_validator_expansion_baseline_report.json`
- `out/m15_validator_expansion_report.json`
- `out/m15_validator_burndown_report.json`

The M15 validator step:
- derives one expanded validator stack from `out/m15_validator_candidates.json`
- evaluates baseline on `out/m9_full_description_uplift/run1` and current on `out/m14_context_specificity/run1`
- publishes explicit applicability and failure taxonomy, then enforces burn-down thresholds on the same expanded rules

Run M15 pipeline governance gate:

```bash
make m15-pipeline-governance-check
```

This command writes:
- `out/m15_pipeline_governance.json`

The M15 governance gate enforces:
- discovery-to-validator-to-burndown coherence over one live corpus path (`out/m14_context_specificity/run1`)
- CI wiring includes `m15-pipeline-governance-check` and excludes legacy subset paths
- decision, assumption, and risk ledgers are emitted with minimum row counts
- `docs/PROGRAM_PLAN.md` includes the M15 PRG-153 execution outcome

Run M16 contract promotion from M15 ontology evidence:

```bash
make m16-contract-promotion-check
```

This command writes:
- `out/m16_contract_promotion.json`

The M16 contract step:
- promotes accepted M15 ontology candidates into unified FDML contract fields
- validates schema/spec support against `schema/fdml.xsd` and `docs/FDML-SPEC.md`
- emits promoted field inventory and decision registry for the next validator-deepening step

Run M16 unified validator expansion and burn-down:

```bash
make m16-validator-expansion-check
```

This command writes:
- `out/m16_validator_expansion_baseline_report.json`
- `out/m16_validator_expansion_report.json`
- `out/m16_validator_burndown_report.json`

The M16 validator step:
- runs one expanded validator stack (movement, geometry, relational, timing, and structural families) over all `90/90` files
- evaluates baseline on `out/m9_full_description_uplift/run1` and current on `out/m14_context_specificity/run1`
- enforces candidate-key mapping completeness, zero no-applicability rules, and measurable failure burn-down thresholds

Run M16 pipeline governance gate:

```bash
make m16-pipeline-governance-check
```

This command writes:
- `out/m16_pipeline_governance.json`

The M16 governance gate enforces:
- contract-to-validator-to-burndown coherence across one canonical live corpus path (`out/m14_context_specificity/run1`)
- fixed baseline path usage (`out/m9_full_description_uplift/run1`) for measurable burn-down
- CI wiring includes `m16-pipeline-governance-check` while retaining prior governance gates
- decision, assumption, and risk ledgers are emitted with minimum row counts

Run M17 descriptor registry and depth-coverage extraction:

```bash
make m17-descriptor-registry-check
```

This command writes:
- `out/m17_descriptor_registry.json`
- `out/m17_fdml_coverage_report.json`

The M17 descriptor step:
- runs deterministic full-corpus extraction over `out/m14_context_specificity/run1`
- expands style/performance/cultural descriptor families in one unified registry
- publishes per-key support/evidence metrics and per-file depth classes with explicit backlog priorities

Run M17 one-stack validator expansion and burn-down:

```bash
make m17-validator-expansion-check
```

This command writes:
- `out/m17_validator_expansion_baseline_report.json`
- `out/m17_validator_expansion_report.json`
- `out/m17_validator_burndown_report.json`

The M17 validator step:
- runs one expanded validator stack with biomechanical and transition-realism families over `90/90` files
- evaluates baseline on `out/m9_full_description_uplift/run1` and current on `out/m14_context_specificity/run1`
- enforces candidate-key mapping completeness, applicability coverage, and measurable burn-down thresholds
- surfaces remaining realism backlog explicitly (currently concentrated in turn-axis per-step coverage)

Run M17 pipeline governance gate:

```bash
make m17-pipeline-governance-check
```

This command writes:
- `out/m17_pipeline_governance.json`

The M17 governance gate enforces:
- descriptor-to-validator-to-burndown coherence across one canonical live corpus path (`out/m14_context_specificity/run1`)
- fixed baseline path usage (`out/m9_full_description_uplift/run1`) for measurable burn-down
- CI wiring includes `m17-pipeline-governance-check` while retaining prior governance gates
- decision, assumption, and risk ledgers are emitted with minimum row counts

Run M18 residual-realism uplift and burn-down:

```bash
make m18-realism-uplift-check
```

This command writes:
- `out/m18_realism_uplift_report.json`
- `out/m18_validator_realism_uplift_report.json`
- `out/m18_validator_burndown_report.json`

The M18 realism step:
- deterministically uplifts turn-axis and missing transition-foot markers on `out/m14_context_specificity/run1`
- re-runs strict doctor + validate-geo over uplifted outputs (`out/m18_realism_uplift/run1`)
- evaluates one-stack M17 validators on uplifted outputs and compares against M17 baseline (`out/m17_validator_expansion_report.json`) to enforce measurable residual-failure burn-down

Run M18 cultural-depth descriptor uplift:

```bash
make m18-descriptor-uplift-check
```

This command writes:
- `out/m18_descriptor_uplift_report.json`
- `out/m18_descriptor_registry.json`
- `out/m18_fdml_coverage_report.json`

The M18 descriptor step:
- deterministically enriches low-cultural-depth files with schema-safe cultural-context notes on top of `out/m18_realism_uplift/run1`
- re-validates strict doctor + validate-geo on all uplifted outputs (`out/m18_descriptor_uplift/run1`)
- recomputes descriptor registry/coverage with stricter cultural-depth thresholds (`min-files-with-cultural-depth=85`) for measurable closure progress

Run M18 pipeline governance gate:

```bash
make m18-pipeline-governance-check
```

This command writes:
- `out/m18_pipeline_governance.json`

The M18 governance gate enforces:
- realism-to-descriptor stage coherence across canonical paths (`out/m14_context_specificity/run1` -> `out/m18_realism_uplift/run1` -> `out/m18_descriptor_uplift/run1`)
- fixed M17 baseline usage (`out/m17_validator_expansion_report.json`) for residual-failure burn-down
- CI wiring includes `m18-pipeline-governance-check` while retaining prior governance gates
- decision, assumption, and risk ledgers are emitted with minimum row counts and plan-sync checks

Run M19 corpus-expansion and regional-balance baseline:

```bash
make m19-corpus-expansion-baseline-check
```

This command writes:
- `out/m19_descriptor_registry.json`
- `out/m19_fdml_coverage_report.json`
- `out/m19_corpus_expansion_report.json`

The M19 baseline step:
- recomputes full-corpus descriptor coverage on the current canonical corpus path (`out/m18_descriptor_uplift/run1`)
- publishes machine-readable regional-balance distribution and imbalance gaps using the M5 five-bucket model
- emits backlog-ready expansion candidates with required additional file counts per underrepresented bucket
- preserves one-structure FDML depth evidence (`style=10/10`, `culture=6/6`, `files with combined depth=90/90`) while establishing corpus-breadth targets

Run M19 descriptor-depth uplift and validator expansion:

```bash
make m19-descriptor-validator-expansion-check
```

This command writes:
- `out/m19_descriptor_uplift_report.json`
- `out/m19_descriptor_registry.json`
- `out/m19_fdml_coverage_report.json`
- `out/m19_validator_expansion_baseline_report.json`
- `out/m19_validator_expansion_report.json`
- `out/m19_validator_burndown_report.json`

The M19 depth-expansion step:
- applies deterministic descriptor uplift on `out/m18_descriptor_uplift/run1` into `out/m19_descriptor_uplift/run1` for low-support descriptor families (`call_response_mode`, `energy_profile`, `improvisation_mode`, `impact_profile`)
- re-runs descriptor registry/coverage to keep one canonical post-uplift coverage snapshot
- layers four M19 descriptor-depth validator rules on top of the existing M17 one-stack rule set (rule count rises from `43` to `47`)
- publishes baseline/current burn-down where descriptor-depth failures are explicit and measurable (`282 -> 0` in current corpus)

Run M19 pipeline governance and release-readiness gate:

```bash
make m19-pipeline-governance-check
```

This command writes:
- `out/m19_pipeline_governance.json`

The M19 governance gate enforces:
- corpus-expansion to descriptor-uplift to validator-layering coherence across canonical paths (`out/m18_descriptor_uplift/run1` -> `out/m19_descriptor_uplift/run1`)
- fixed baseline/current report invariants for M19 burn-down (`out/m19_validator_expansion_baseline_report.json` -> `out/m19_validator_expansion_report.json`)
- candidate-mapping and applicability integrity through retained M17 one-stack intermediate reports
- CI wiring includes `m19-pipeline-governance-check` while retaining prior governance gates
- submission readiness documentation includes explicit M19 command and artifact references

Run M20 corpus expansion and M19-gap burn-down:

```bash
make m20-corpus-expansion-check
```

This command writes:
- `out/m20_descriptor_registry.json`
- `out/m20_fdml_coverage_report.json`
- `out/m20_corpus_expansion_report.json`

The M20 expansion step:
- merges `analysis/sources/m20_expansion_seed_manifest.json` into the deterministic acquisition flow
- re-runs acquisition + conversion on one canonical path (`out/m2_conversion/run1`) to expand the active corpus beyond 90 files
- recomputes descriptor coverage on the expanded corpus and publishes M20 regional-balance deltas against `out/m19_corpus_expansion_report.json`
- reports explicit bucket-level burn-down (`baseline required additional` vs `current required additional`) so backlog reduction is machine-verifiable

Run M20 source-grounded descriptor uplift and validator burn-down:

```bash
make m20-descriptor-validator-expansion-check
```

This command writes:
- `out/m20_descriptor_evidence/run1/*`
- `out/m20_descriptor_evidence_report.json`
- `out/m20_descriptor_registry.json`
- `out/m20_fdml_coverage_report.json`
- `out/m20_validator_expansion_baseline_m17_report.json`
- `out/m20_validator_expansion_m17_report.json`
- `out/m20_validator_expansion_baseline_report.json`
- `out/m20_validator_expansion_report.json`
- `out/m20_validator_burndown_report.json`

The M20 descriptor-plus-validator step:
- applies deterministic source-grounded descriptor enrichment on `out/m2_conversion/run1` using lexeme evidence from `out/acquired_sources` plus `out/acquired_sources_nonwiki`
- adds only evidence-linked descriptor notes (no synthetic fallback marker text) and re-validates strict doctor plus validate-geo over the uplifted corpus
- expands a dedicated M20 realism validator layer with source-grounded applicability rules for energy, call-response, improvisation, impact, rotation, elevation, partner interaction, and spatial pattern
- publishes baseline/current burn-down on the M20 layer (`133 -> 0` failures in live run) while preserving candidate-mapping completeness from the base one-stack validator reports

Run M20 pipeline governance and release-readiness gate:

```bash
make m20-pipeline-governance-check
```

This command writes:
- `out/m20_pipeline_governance.json`

The M20 governance gate enforces:
- expansion to descriptor-evidence to validator-layer coherence across canonical paths (`out/m2_conversion/run1` -> `out/m20_descriptor_evidence/run1`)
- fixed baseline/current report invariants for M20 burn-down (`out/m20_validator_expansion_baseline_report.json` -> `out/m20_validator_expansion_report.json`)
- source-grounded descriptor and validator invariants (required source-text dirs, descriptor growth, applicability, and mapping integrity)
- CI wiring includes `m20-pipeline-governance-check` while retaining prior milestone governance gates
- submission readiness documentation includes explicit M20 command and artifact references

Run M21 descriptor completion uplift:

```bash
make m21-descriptor-completion-check
```

This command writes:
- `out/m21_descriptor_completion/run1/*`
- `out/m21_descriptor_completion_report.json`
- `out/m21_descriptor_registry.json`
- `out/m21_fdml_coverage_report.json`

The M21 descriptor-completion step:
- starts from the M20 source-grounded descriptor corpus (`out/m20_descriptor_evidence/run1`) and targets low-depth files using `out/m20_fdml_coverage_report.json`
- applies deterministic source-grounded descriptor additions only when matching lexemes are present in acquired source text (`out/acquired_sources`, `out/acquired_sources_nonwiki`)
- prioritizes depth-gap closure for style (`>=2`), cultural (`>=1`), and combined descriptor depth (`>=4`) while preserving strict doctor and geometry validity
- publishes explicit baseline/current depth-gain metrics and per-file evidence-linked additions for M21 handoff into validator expansion

Run M21 context/structure validator expansion and burn-down:

```bash
make m21-validator-expansion-check
```

This command writes:
- `out/m21_validator_expansion_baseline_m17_report.json`
- `out/m21_validator_expansion_m17_report.json`
- `out/m21_validator_expansion_baseline_report.json`
- `out/m21_validator_expansion_report.json`
- `out/m21_validator_burndown_report.json`

The M21 validator-expansion step:
- keeps one baseline/current comparison path (`out/m20_descriptor_evidence/run1` -> `out/m21_descriptor_completion/run1`)
- composes a dedicated M21 source-grounded rule layer that extends M20 realism checks with context and structure families (`motion_quality`, `grouping_mode`, and six cultural-context descriptor constraints)
- validates candidate-mapping and rule applicability on both baseline and current reports
- publishes explicit baseline/current burn-down metrics via `out/m21_validator_burndown_report.json` for M21-K2 progress tracking

Run M21 pipeline governance and release-readiness gate:

```bash
make m21-pipeline-governance-check
```

This command writes:
- `out/m21_pipeline_governance.json`

The M21 governance gate enforces:
- descriptor completion to context/structure validator-layer coherence across canonical paths (`out/m20_descriptor_evidence/run1` -> `out/m21_descriptor_completion/run1`)
- fixed baseline/current report invariants for M21 burn-down (`out/m21_validator_expansion_baseline_report.json` -> `out/m21_validator_expansion_report.json`)
- source-grounded descriptor and validator invariants (depth gains, required source-text dirs, mapping integrity, and applicability)
- CI wiring includes `m21-pipeline-governance-check` while retaining prior milestone governance gates
- submission readiness documentation includes explicit M21 command and artifact references

Run M22 low-support descriptor uplift:

```bash
make m22-descriptor-uplift-check
```

This command writes:
- `out/m22_descriptor_uplift/run1/*`
- `out/m22_descriptor_uplift_report.json`
- `out/m22_descriptor_registry.json`
- `out/m22_fdml_coverage_report.json`

The M22 descriptor-uplift step:
- starts from the M21 descriptor-completion corpus (`out/m21_descriptor_completion/run1`) and baseline coverage (`out/m21_fdml_coverage_report.json`)
- identifies low-support descriptor families using support-ratio and source-signal potential criteria, then applies deterministic source-grounded additions only for missing signaled keys
- preserves strict quality (`doctor --strict` and `validate-geo`) while raising low-support descriptor support and publishing per-key growth metrics
- emits refreshed descriptor registry plus depth coverage artifacts for M22 validator hardening handoff

Run M22 context/structure validator coherence expansion and burn-down:

```bash
make m22-validator-expansion-check
```

This command writes:
- `out/m22_validator_expansion_baseline_report.json`
- `out/m22_validator_expansion_report.json`
- `out/m22_validator_burndown_report.json`

The M22 validator-expansion step:
- evaluates one baseline/current path (`out/m21_descriptor_completion/run1` -> `out/m22_descriptor_uplift/run1`) against source-grounded context/structure rule families
- adds M22 coherence rules that validate uplift-note integrity (`source_id` matching, key-pair presence, low-support key restriction, and source-lexeme grounding)
- preserves candidate-mapping integrity through base-report priority coverage checks while requiring rule applicability and explicit failure taxonomy output
- publishes baseline/current failure-taxonomy burn-down metrics via `out/m22_validator_burndown_report.json` for M22-K2 progress tracking

Run M22 pipeline governance and release-readiness gate:

```bash
make m22-pipeline-governance-check
```

This command writes:
- `out/m22_pipeline_governance.json`

The M22 governance gate enforces:
- descriptor uplift to validator coherence-layer coherence across canonical paths (`out/m21_descriptor_completion/run1` -> `out/m22_descriptor_uplift/run1`)
- fixed baseline/current report invariants for M22 burn-down (`out/m22_validator_expansion_baseline_report.json` -> `out/m22_validator_expansion_report.json`)
- low-support descriptor and coherence-validator invariants (source-grounded additions, low-support growth, rule-family minima, mapping integrity, and applicability)
- CI wiring includes `m22-pipeline-governance-check` while retaining prior milestone governance gates
- submission and program plan docs include explicit M22 command and artifact references

Run M23 descriptor-support consolidation:

```bash
make m23-descriptor-consolidation-check
```

This command writes:
- `out/m23_descriptor_consolidation/run1/*`
- `out/m23_descriptor_consolidation_report.json`
- `out/m23_descriptor_registry.json`
- `out/m23_fdml_coverage_report.json`

The M23 descriptor-consolidation step:
- starts from the M22 descriptor-uplift corpus (`out/m22_descriptor_uplift/run1`) and baseline coverage (`out/m22_fdml_coverage_report.json`)
- targets descriptor families with residual support gaps via deterministic source-grounded extraction (including high-gap keys even when support ratio is no longer low)
- preserves strict quality (`doctor --strict` and `validate-geo`) while reducing residual source-signal minus support gaps
- publishes refreshed registry and coverage artifacts for M23 validator-taxonomy burn-down handoff

Run M23 validator expansion and burn-down:

```bash
make m23-validator-expansion-check
```

This command writes:
- `out/m23_validator_expansion_baseline_report.json`
- `out/m23_validator_expansion_report.json`
- `out/m23_validator_burndown_report.json`

The M23 validator-expansion step:
- evaluates one baseline/current path (`out/m22_descriptor_uplift/run1` -> `out/m23_descriptor_consolidation/run1`) against source-grounded context/structure rule families
- preserves M23 uplift-note coherence constraints (`source_id` matching, descriptor pair presence, low-support key restriction, and source-lexeme grounding)
- requires candidate-mapping integrity and rule applicability on baseline/current reports
- publishes baseline/current failure-taxonomy burn-down metrics via `out/m23_validator_burndown_report.json` for M23-K2 progress tracking

Run M23 pipeline governance and release-readiness gate:

```bash
make m23-pipeline-governance-check
```

This command writes:
- `out/m23_pipeline_governance.json`

The M23 governance gate enforces:
- descriptor consolidation to validator coherence across canonical paths (`out/m22_descriptor_uplift/run1` -> `out/m23_descriptor_consolidation/run1`)
- fixed baseline/current report invariants for M23 burn-down (`out/m23_validator_expansion_baseline_report.json` -> `out/m23_validator_expansion_report.json`)
- low-support descriptor and coherence-validator invariants (source-grounded additions, low-support growth, rule-family minima, mapping integrity, and applicability)
- CI wiring includes `m23-pipeline-governance-check` while retaining prior milestone governance gates
- submission and program-plan docs include explicit M23 command and artifact references

Run M24 residual validator-failure closure and burn-down:

```bash
make m24-residual-failure-closure-check
```

This command writes:
- `out/m24_residual_failure_closure/run1/*`
- `out/m24_residual_failure_closure_report.json`
- `out/m24_validator_expansion_baseline_report.json`
- `out/m24_validator_expansion_report.json`
- `out/m24_validator_burndown_report.json`

The M24 residual-closure step:
- reads residual file/rule failures from `out/m23_validator_expansion_report.json` and applies deterministic source-grounded note additions only on targeted files
- closes residual cultural-context alignment gaps for occasion, social-function, and transmission descriptors under the same one-pipeline corpus path
- re-runs the M23 validator-expansion stack on baseline/current paths (`out/m23_descriptor_consolidation/run1` -> `out/m24_residual_failure_closure/run1`)
- enforces strict residual elimination via burn-down thresholds (`min_reduction_ratio=1.0`, `max_failure_file_ratio=0.0`) in `out/m24_validator_burndown_report.json`

Run M24 cultural-context descriptor completion:

```bash
make m24-descriptor-completion-check
```

This command writes:
- `out/m24_descriptor_completion/run1/*`
- `out/m24_descriptor_completion_report.json`
- `out/m24_descriptor_registry.json`
- `out/m24_fdml_coverage_report.json`

The M24 descriptor-completion step:
- starts from `out/m24_residual_failure_closure/run1` and uses acquired source text evidence to identify low-support cultural descriptor families with residual growth potential
- applies deterministic source-grounded cultural descriptor additions (`occasion_context`, `social_function`, `music_context`, `costume_prop_context`, `participant_identity`, `transmission_context`) with per-file addition caps
- preserves strict quality (`doctor --strict` and `validate-geo`) while reducing low-support cultural residual growth gap
- publishes updated descriptor registry and depth coverage artifacts for M24 governance handoff

Run M24 pipeline governance and final-queue activation gate:

```bash
make m24-pipeline-governance-check
```

This command writes:
- `out/m24_pipeline_governance.json`

The M24 governance gate enforces:
- residual-closure to descriptor-completion to validator-burndown coherence across canonical paths (`out/m23_descriptor_consolidation/run1` -> `out/m24_residual_failure_closure/run1` -> `out/m24_descriptor_completion/run1`)
- strict residual-zeroing invariants for M24 validator reports (`out/m24_validator_expansion_baseline_report.json` -> `out/m24_validator_expansion_report.json`) and burndown thresholds (`reduction_ratio=1.0`, `failure_file_ratio=0.0`)
- low-support cultural descriptor growth and residual-gap reduction invariants from `out/m24_descriptor_completion_report.json`
- CI wiring includes `m24-pipeline-governance-check` while retaining prior milestone governance gates
- submission and program-plan docs include explicit M24 command/artifact references for milestone closeout and final productization queue activation

## Init Profiles

`fdml init` supports profile templates:

- `v1-basic`
- `v12-circle`
- `v12-line`
- `v12-twoLinesFacing`
- `v12-couple`

Examples:

```bash
./bin/fdml init out/basic.fdml.xml --profile v1-basic --title "Basic"
./bin/fdml init out/circle.v12.fdml.xml --profile v12-circle --title "Circle v1.2"
./bin/fdml init out/twolines.v12.fdml.xml --profile v12-twoLinesFacing --title "Two Lines v1.2"
```

Validate generated output with strict doctor:

```bash
./bin/fdml doctor out/twolines.v12.fdml.xml --strict
```

## Ingest Scaffold

Generate a deterministic FDML scaffold from local text notes:

```bash
./bin/fdml ingest \
  --source analysis/gold/ingest/source_minimal.txt \
  --out out/ingest-minimal.fdml.xml \
  --title "Ingest Minimal" \
  --meter 4/4 \
  --tempo 112 \
  --profile v1-basic
```

Enable optional API enrichment (Groq/DeepL/OCR-space/YouTube) from local `.env`:

```bash
./bin/fdml ingest \
  --source analysis/gold/ingest/source_minimal.txt \
  --out out/ingest-enriched.fdml.xml \
  --profile v1-basic \
  --enable-enrichment \
  --env-file .env \
  --enrichment-report out/enrichment-report.json
```

When `FDML_OFFLINE=1`, enrichment is skipped automatically and ingest remains deterministic.

Validate deterministic offline enrichment report fixture:

```bash
make enrichment-report-check
```

This gate is optional and not part of `make ci` so core CI remains offline-safe.

Batch ingest a directory of source `.txt` files:

```bash
./bin/fdml ingest-batch \
  --source-dir src/test/resources/ingest_batch/sources \
  --out-dir out/ingest-batch \
  --title-prefix "Batch Fixture" \
  --meter 4/4 \
  --tempo 112 \
  --profile v1-basic \
  --enable-enrichment \
  --env-file .env \
  --index-out out/ingest-batch/index.json
```

The batch index summarizes each source file with output paths, strict doctor result, schema checks, and errors.

Optional acceptance gate:

```bash
make ingest-batch-check
```

Promote passing batch items into a curated destination:

```bash
./bin/fdml ingest-promote \
  --index out/ingest-batch/index.json \
  --dest corpus/valid_ingest_auto \
  --quarantine-dir out/ingest-quarantine \
  --quarantine-out out/ingest-quarantine/quarantine.json
```

Promotion criteria (all required):
- `ingestExitCode == 0`
- `doctor.strictOk == true`
- `schema.provenance == true`
- `schema.enrichmentReport == true`

Items that do not meet criteria are copied to quarantine and listed in `quarantine.json`.

Optional acceptance gate:

```bash
make ingest-promote-check
```

Emit provenance sidecar JSON:

```bash
./bin/fdml ingest \
  --source analysis/gold/ingest/source_minimal.txt \
  --out out/ingest-minimal.fdml.xml \
  --provenance-out out/provenance_minimal.json
python3 scripts/validate_json_schema.py schema/provenance.schema.json out/provenance_minimal.json
```

Validate the generated file:

```bash
./bin/fdml doctor out/ingest-minimal.fdml.xml --strict
```

## Reproducible Site Manifest

Generate the current site manifest:

```bash
make html
python3 scripts/site_manifest.py site --out out/site_manifest.json
```

Check against the committed expected manifest:

```bash
make site-manifest-check
```

If site output changed intentionally, regenerate the expected manifest:

```bash
make html
python3 scripts/site_manifest.py site --out docs/manifest.expected.json
```

## Web source acquisition (licensed)

Curated web-source manifest:
- `analysis/sources/web_seed_manifest.json`
- `analysis/sources/non_wikipedia_public_domain_manifest.json` (non-Wikipedia public-domain set)

Acquire sources deterministically:

```bash
python3 scripts/acquire_sources.py \
  --manifest analysis/sources/web_seed_manifest.json \
  --out-dir out/acquired_sources
```

Acquire non-Wikipedia public-domain set:

```bash
python3 scripts/acquire_sources.py \
  --manifest analysis/sources/non_wikipedia_public_domain_manifest.json \
  --out-dir out/acquired_sources_nonwiki
```

Run quality review gate (fails on low-quality extracts):

```bash
python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources
python3 scripts/review_acquired_sources.py --input-dir out/acquired_sources_nonwiki
```

Then ingest acquired text into FDML:

```bash
mkdir -p out/acquired_fdml
for txt in out/acquired_sources/*.txt; do
  stem="$(basename "$txt" .txt)"
  ./bin/fdml ingest --source "$txt" --out "out/acquired_fdml/${stem}.fdml.xml" --title "$stem" --meter 4/4 --tempo 112 --profile v1-basic
done
./bin/fdml doctor out/acquired_fdml --strict
```

Run deterministic M2 conversion batch (double-run reproducibility check):

```bash
make conversion-batch-check
```

This produces `out/m2_conversion/run1/index.json` and `out/m2_conversion/run2/index.json` and fails if they differ.

Run full-description coverage KPI check (M6-K1):

```bash
make full-description-coverage-check
```

This enforces:
- strict full-description count in `out/m2_conversion/run1` is `>= 30`
- strict/relaxed coverage report is generated deterministically

Current report output:
- `out/m6_full_description_current.json`

Run full-description quality gate (M6-K2):

```bash
make full-description-quality-check
```

This enforces:
- fixture pass/fail behavior for `scripts/full_description_quality_gate.py`
- strict-doctor pass-rate `>= 95%` for files classified as strict full-description
- placeholder-only files in that upgraded set are `0`

Live report output (when `out/m2_conversion/run1` is present):
- `out/m6_full_description_quality.json`

M6 search/discovery facet:
- `site/index.json` now includes `fullDescriptionTier` (`strict|relaxed|basic`) and related quality counters.
- Demo prefilled link: `site/search.html?fullDescriptionTier=strict`

Run M8 geometry baseline map (KPI M8-K1):

```bash
make m8-geometry-baseline-check
```

This produces deterministic readiness/blocker inventory for the full converted corpus:
- `out/m8_geometry_baseline.json`

Run M8 strict-file geometry uplift (KPI M8-K2):

```bash
make m8-geometry-uplift-check
```

This upgrades strict full-description files into v1.2 geometry-ready outputs and validates each with strict doctor + geometry validator.

Outputs:
- `out/m8_geometry_uplift/run1/*.fdml.xml`
- `out/m8_geometry_uplift_progress.json`

Run M8 geometry governance gate (KPI M8-K3):

```bash
make m8-geometry-governance-check
```

This enforces:
- fixture pass/fail behavior for `scripts/m8_geometry_governance_gate.py`
- alignment across baseline, strict coverage, and uplift reports
- required blocker burn-down (`version_not_1_2`, `missing_meta_geometry`, `missing_formation_kind`, `missing_step_geo_primitive`)
- live quality thresholds (`doctor >= 95%`, `validate-geo = 100%`, geometry-ready = `100%`) when conversion artifacts exist

Live report output (when `out/m2_conversion/run1` is present):
- `out/m8_geometry_governance.json`

Run M9 full-corpus v1.2 promotion pipeline (KPI M9-K1):

```bash
make m9-geometry-full-corpus-check
```

This enforces:
- deterministic promotion of all converted files (`out/m2_conversion/run1`) into geometry-ready v1.2 outputs
- strict doctor + geometry validator pass-rate thresholds on promoted files
- zero unresolved required baseline blockers in promoted outputs:
  - `version_not_1_2`
  - `missing_meta_geometry`
  - `missing_formation_kind`
  - `missing_step_geo_primitive`

Live outputs:
- `out/m9_full_corpus_v12/run1/*.fdml.xml`
- `out/m9_geometry_full_corpus.json`

Run M9 strict-description uplift pipeline (KPI M9-K2):

```bash
make m9-full-description-uplift-check
```

This enforces:
- deterministic uplift of baseline non-strict files from the promoted v1.2 corpus
- strict full-description target lift to at least `85/90`
- preserved quality thresholds (`strict doctor >= 95%`, `placeholder-only strict files = 0`)
- no geometry regressions after uplift (`validate-geo = 100%`)

Live outputs:
- `out/m9_full_description_uplift/run1/*.fdml.xml`
- `out/m9_full_description_current.json`
- `out/m9_full_description_quality.json`
- `out/m9_full_description_progress.json`

Default site/demo/search workflow adoption (KPI M11-K3):
- `make html` uses unified corpus source `out/m9_full_description_uplift/run1` and requires `m11-validator-unified-check` before card/index generation.
- `make ci` includes `m11-pipeline-governance-check` (which verifies demo/search outputs and writes `out/m11_pipeline_governance.json`).

Run strict doctor pass-rate KPI gate (M2-K2):

```bash
make doctor-passrate-check
```

This enforces:
- fixture pass/fail behavior for `scripts/doctor_passrate_gate.py`
- live generated batch strict-doctor pass-rate `>= 90%` when acquired-source dirs are present

Live report output:
- `out/m2_conversion/run1/doctor_passrate.json`

Run provenance coverage KPI gate (M2-K3):

```bash
make provenance-coverage-check
```

This enforces:
- every generated FDML entry has a provenance sidecar reference
- referenced provenance files exist and pass `schema/provenance.schema.json`
- live generated batch provenance coverage `>= 100%` when acquired-source dirs are present

Live report output:
- `out/m2_conversion/run1/provenance_coverage.json`

Run semantic enrichment baseline inventory (M3-K1 baseline):

```bash
make semantic-enrichment-check
```

This reports semantic enrichment coverage for `corpus/valid_v12` and currently enforces:
- enriched count `>= 15`
- KPI target tracking toward `15` enriched files

Output report:
- `out/m3_semantic_inventory.json`

Run semantic issue trend gate (M3-K2, fail on regression vs baseline):

```bash
make semantic-issue-trend-check
```

This compares current `doctor --json` + `validate-geo --json` totals for `corpus/valid_v12`
against:
- `analysis/program/m3_issue_baseline.json`

It fails if any tracked metric increases:
- `xsdFailed`, `schematronFailures`, `lintWarnings`, `timingIssues`, `geoIssues`, `strictFailFiles`, `issueTotal`

Current report output:
- `out/m3_issue_current.json`

Run semantic spec-alignment gate (M3-K3):

```bash
make semantic-spec-alignment-check
```

This enforces a maintained mapping between emitted semantic issue codes and spec references:
- mapping manifest: `analysis/program/semantic_issue_code_map.json`
- emitted-code sources: `GeometryValidator`, `TimingValidator`, `Linter`, `DoctorExplain`

The gate fails if:
- any emitted issue code is unmapped
- mapping contains stale code entries
- mapped reference files are missing or outside docs/schema/schematron roots

Current report output:
- `out/m3_semantic_spec_alignment.json`

Run demo flow gate (M4-K2):

```bash
make demo-flow-check
```

This enforces the reproducible walkthrough:
- `fdml init` (v1.2 demo fixture)
- `fdml doctor --strict`
- `fdml render`
- `make html` + Search/index artifact checks
- Search metadata coverage for M5 diversity categories via `sourceCategory`:
  - `africa`
  - `middle-east-caucasus`
  - `south-se-asia`
  - `europe-regional`
  - `americas-oceania`

Current report output:
- `out/demo_flow/demo_flow_report.json`

Run final product-readiness baseline (M25-K1):

```bash
make final-rehearsal-check
```

This executes the final handoff sequence:
- full gate stack (`make ci`)
- test run (`mvn test`)
- deterministic regeneration of both conversion gate reports:
  - `out/m2_conversion/run1/doctor_passrate.json`
  - `out/m2_conversion/run1/provenance_coverage.json`
- M25 baseline validation + gap-ledger packaging (`scripts/final_rehearsal_check.py`)

Current report output:
- `out/final_rehearsal/report.json`

Run M25 documentation + architecture hardening gate (PRG-252):

```bash
make m25-hardening-check
```

This enforces:
- architecture documentation is non-placeholder and section-complete
- submission/coverage/usage docs are synchronized with M25 baseline evidence
- final baseline report schema/label/gap-ledger integrity
- CI wiring includes `m25-hardening-check`

Current report output:
- `out/m25_hardening_report.json`

Run M25 final release-governance closeout gate (PRG-253):

```bash
make m25-release-governance-check
```

This enforces:
- active M25 queue is closed (`planned=0`, `in_progress=0`, `blocked=0`)
- final baseline report is release-ready (`releaseReady=true`, `queuedGapCount=0`)
- hardening gate, tracker state, execution map, docs, and CI wiring are synchronized
- machine-readable decision/assumption/risk ledgers are present for closeout auditability

Current report output:
- `out/m25_release_governance.json`

Run M26 polish baseline gate (PRG-261):

```bash
make m26-polish-baseline-check
```

This enforces:
- active milestone remains `M26` with activation invariants intact
- deterministic backlog metrics for repository hygiene + documentation coherence
- explicit cleanup queue evidence linked to `PRG-262` / `PRG-263`

Current report output:
- `out/m26_polish_baseline_report.json`

Run M26 polish execution gate (PRG-262):

```bash
make m26-polish-execution-check
```

This enforces:
- reviewer-facing docs (`PROGRAM_PLAN`, `SUBMISSION`, `COVERAGE`, `USAGE`) include current M26 command/artifact references
- generated Python cache artifacts are removed and blocked via `.gitignore` rules
- M26 execution mapping and CI wiring are synchronized for deterministic replay

Current report output:
- `out/m26_polish_execution_report.json`

Run M26 governance handoff gate (PRG-263):

```bash
make m26-governance-handoff-check
```

This enforces:
- final M26 anti-drift governance invariants over queue shape, baseline/execution report lineage, and CI wiring
- synchronized handoff references across `PROGRAM_PLAN`, `SUBMISSION`, `COVERAGE`, and `USAGE`
- machine-readable handoff package with command set, hashed artifact manifest, and residual-risk ledger

Current report output:
- `out/m26_handoff_governance_report.json`

Make shortcuts:

```bash
make acquire-sources
make acquire-sources-nonwiki
```

Both targets now enforce the M1-K2 review KPI automatically:
- pass-rate must be `>= 95%` or the command fails.

Run pass-rate gate directly:

```bash
make review-passrate-check
```

Run license-policy gate directly:

```bash
make license-policy-check
```

Policy and governance details:
- `docs/ACQUISITION-SPEC.md`

## Program Gate (M0 guardrail)

Run milestone/KPI consistency checks:

```bash
make program-check
make task-approval-check
```

Source files:

- `docs/PROGRAM_PLAN.md`
- `analysis/program/plan.json`
- `analysis/program/work_items.csv`
- `analysis/program/approval_report.json` (generated)
- `analysis/program/goal_state.json` (generated handoff context)

Goal state commands:

```bash
make goal-state-update
make goal-state-check
```

`make ci` now runs `program-check`, `task-approval-check`, and `goal-state-check` first.

Autopilot execution (until milestone boundary):

```bash
make program-autopilot
```

Dry-run preview:

```bash
make program-autopilot-dry-run
```

Autopilot behavior:
- reads active queue from `analysis/program/work_items.csv` and command mapping from `analysis/program/step_execution_map.json`
- runs mapped command(s) for the next `in_progress`/`planned` item in the active milestone
- marks completed items as `done`, then reruns `program-check`, `task-approval-check`, and `goal-state-update`
- stops on first failure, missing mapping, empty active queue, `--max-items` limit, or milestone boundary

## Optional API health check

For enrichment providers configured in local `.env`, run:

```bash
make api-check
```

Notes:
- Sends a stable `User-Agent` header for all providers (including Groq) to avoid bot-style client blocks.
- Skips network calls when `FDML_OFFLINE=1`.

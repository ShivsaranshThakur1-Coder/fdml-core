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

Validate the generated file:

```bash
./bin/fdml doctor out/ingest-minimal.fdml.xml --strict
```

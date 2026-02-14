# Topology and Progression Specification (Implemented)

This document describes the topology/progression behavior currently implemented in:
- `src/main/java/org/fdml/cli/GeometryValidator.java`

Scope note:
- This is an implementation-facing spec (what the validator does now), not a full language design document.
- Examples reference existing v1.2 corpus fixtures under `corpus/valid_v12` and `corpus/invalid_v12`.

## 1) twoLinesFacing Rules

### Required topology
- If `meta/geometry/formation/@kind = "twoLinesFacing"`, then `body/geometry/twoLines/facing` is required.
- Issue code on violation: `missing_two_lines_facing`.

### Approach/retreat formation compatibility
- `geo/primitive kind="approach"|"retreat"` is only allowed when formation kind is `twoLinesFacing`.
- Issue code on violation: `bad_formation_for_approach_retreat`.

### Approach/retreat pairing and separation dip checks
When formation kind is `twoLinesFacing` and approach/retreat primitives are present:
- Both approach and retreat must appear.
- Issue code: `missing_approach_retreat_pair`.
- A simple numeric separation model must show enough variation (`maxSep - minSep >= 0.3`).
- Issue code: `two_lines_no_sep_dip`.

### Minimal corpus examples
- Passing: `corpus/valid_v12/haire-mamougeh.v12.fdml.xml`
- Failing: `corpus/invalid_v12/haire-mamougeh.bad-formation.v12.fdml.xml` (`bad_formation_for_approach_retreat`)

## 2) line Formation Progression Rules

### Progress requires explicit slot order
If formation kind is `line` and any `geo/primitive kind="progress"` appears:
- `body/geometry/line/order/slot/@who` entries must exist.
- Issue code: `missing_line_order_slots`.

### Progress primitive requires delta
If any `geo/primitive kind="progress"` is missing `@delta`:
- Issue code: `progress_missing_delta`.

### Minimal corpus examples
- Passing: `corpus/valid_v12/example-05-contra.progress.v12.fdml.xml`
- Failing: `corpus/invalid_v12/example-05-contra.progress-missing-order.v12.fdml.xml` (`missing_line_order_slots`)

## 3) couple Formation womanSide/relpos Rules

These rules apply when:
- `meta/geometry/formation/@kind = "couple"`
- `meta/geometry/formation/@womanSide` is present (`left` or `right`)

### Required partner model
- Roles `man` and `woman` must exist in `meta/geometry/roles/role/@id`.
- A partner pair must exist at `body/geometry/couples/pair` linking man and woman.
- Issue code on violation: `missing_partner_pairing`.

### Required relpos evidence
- At least one `geo/primitive kind="relpos"` between man and woman must exist so side-state can be checked.
- Issue code on violation: `missing_relpos_evidence`.

### swapPlaces and side-state
- The validator tracks expected side-state from `womanSide`.
- A `geo/primitive kind="swapPlaces"` between man and woman flips side-state.
- Subsequent `relpos` assertions are checked against current side-state.
- Mismatch emits: `relpos_contradiction`.

### Minimal corpus examples
- Passing: `corpus/valid_v12/aalistullaa.relpos.v12.fdml.xml`
- Failing: `corpus/invalid_v12/aalistullaa.relpos-contradiction.v12.fdml.xml` (`relpos_contradiction`)
- Also failing (missing swapPlaces before side flip): `corpus/invalid_v12/aalistullaa.relpos-flip-missing-swap.v12.fdml.xml` (`relpos_contradiction`)

## 4) circle preserveOrder / explicit order Rules

These rules apply when formation kind is `circle` and preserve-order semantics are used.

### Crossing primitives forbidden with preserveOrder
If any primitive has `preserveOrder=true`, then crossing primitives are forbidden:
- crossing set: `pass`, `weave`, `swapPlaces`
- issue code: `circle_order_violation`

### Explicit order slots required for preserveOrder state check
If `preserveOrder=true` is used:
- `body/geometry/circle/order/slot/@who` list must be present.
- issue code when missing: `missing_circle_order_slots`

### swapPlaces effect on explicit order
- The validator copies initial slot order.
- It applies every `swapPlaces(a,b)` in document order to a working list.
- If working order differs from initial order, issue code: `circle_order_changed`.

### Minimal corpus examples
- Passing: `corpus/valid_v12/mayim-mayim.v12.fdml.xml`
- Failing: `corpus/invalid_v12/mayim-mayim.order-broken.v12.fdml.xml`
  - emits `circle_order_violation`
  - emits `circle_order_changed`

## 5) Related Topology/Formation Issue Codes

The following additional formation-topology-adjacent codes are implemented in `GeometryValidator` and may appear with the above checks:
- `missing_formation_kind`
- `missing_primitive_kind`
- `unknown_role`
- `circle_travel_ambiguous`
- `line_travel_too_small`


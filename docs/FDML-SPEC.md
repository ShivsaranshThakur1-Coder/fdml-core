# FDML 1.0 Specification (Implementation Draft)

## 1. Overview

FDML (Folk Dance Markup Language) is an XML-based format for representing folk dance material in a way that is:

- Human-readable,
- Machine-validated (via XML Schema and Schematron),
- Amenable to automated rendering into caller cards and teaching aids.

This document describes the **FDML 1.0** format as implemented in this repository
(`schema/fdml.xsd` plus supporting Schematron rules).

## 2. Root Structure

### 2.1 Root element

Each FDML document has a single root element:

\`\`\`xml
<fdml version="1.0">
  <meta>…</meta>
  <body>…</body>
</fdml>
\`\`\`

- `version` is a required attribute, fixed to `"1.0"` in the current schema.
- `meta` contains document-level metadata (title, dance name, meter, tempo, author).
- `body` contains the actual dance material (sections, figures, sequences).

### 2.2 Meta block

The `<meta>` element has the following structure:

\`\`\`xml
<meta>
  <title>Circle Waltz — Basic</title>
  <dance name="Circle Waltz"/>
  <meter value="3/4"/>
  <tempo bpm="112"/>
  <author email="alice@example.com">Alice Example</author>
</meta>
\`\`\`

Semantics:

- `<title>` (required)
  - Human-facing title for this FDML document (usually the dance or card title).
- `<dance @name>` (optional)
  - Canonical name of the dance, if different from the title.
- `<meter @value>` (optional but recommended)
  - Time signature, stored as a string like `"2/4"`, `"3/4"`, `"4/4"`, etc.
- `<tempo @bpm>` (optional)
  - Approximate tempo in beats per minute.
- `<author @email>` (optional)
  - Free-text author name; email is validated by Schematron if present.

Validation notes:

- Schematron enforces that `<title>` is non-empty and within a reasonable length.
- If `author/@email` is present, it must match a basic email pattern.

### 2.3 Body block

The <body> element contains the actual dance material. It may contain one or more <section>, <figure> and <sequence> elements in any order.
The body must contain at least one of these elements.

## 3. Figures and steps

A figure describes a unit of choreography as a sequence of steps. Each figure has an id, an optional name, an optional formation, and one or more step elements.
Figures are the main reusable blocks that sequences refer to.

Steps are the atomic actions within a figure. Each step specifies who performs it, a free-text action description, a beat count, and optional information about feet, direction and facing.
The schema constrains many of these attributes to enumerated values (for example who, startFoot, endFoot, direction, facing).

## 4. Sections and sequences

Sections are free-form textual blocks used for notes, teaching remarks or structural headings. They may carry an id so that tools and humans can refer to them.

Sequences assemble figures into larger structures by reference. A sequence contains one or more use elements, each of which references a figure id and may specify an optional repeat count.
Schematron rules ensure that every use/figure attribute refers to an existing figure in the same document.

## 5. Meter and beat consistency

The implementation includes a linter that checks meter consistency per figure. The linter reads the meter value from meta/meter, extracts the numerator, and sums the beats of all steps inside each figure.
If the total beat count for a figure is not divisible by the meter numerator, the linter emits an off_meter warning with figure id, meter, total beats and approximate bars.
If meta/meter is missing, the linter emits a missing_meter warning.

## 6. Validation pipeline

FDML documents are checked in three layers:

1. XML Schema (schema/fdml.xsd) ensures structural correctness: required elements, attribute types, id patterns and enumerations.
2. Schematron (schematron/fdml-compiled.xsl) enforces semantic rules such as non-empty titles, valid author emails, positive beats and valid figure references.
3. Lint (org.fdml.cli.Linter) provides soft warnings around meter and beat consistency.

The doctor CLI command runs all three layers and can be configured to treat warnings as failures via a strict mode.

## 7. CLI usage (summary)

The specification is complemented by CLI tooling in this project:

- fdml validate: validate against the XML Schema.
- fdml validate-sch: validate against the Schematron rules.
- fdml validate-all: run both schema and Schematron.
- fdml lint: run the meter and beat linter.
- fdml doctor: run schema, Schematron and lint with a consolidated report.

## 8. Versioning and future extensions

This document describes FDML 1.0 as implemented in this repository. Future versions may add richer metadata, more detailed bar-level structure, additional enumerations for formations and roles, and extended Schematron rules.
Any such changes will be reflected by an updated version attribute, schema and specification document.

## 9. Unified Contract Promotion (M11)

M11 promotes accepted ontology candidates from `out/m10_ontology_candidates.json`
into one contract structure used across the full promoted corpus.

### 9.1 Canonical promoted fields (v-next draft)

| Contract field | XPath | Type | Cardinality | Promotion status |
| --- | --- | --- | --- | --- |
| `meta.meter.value` | `/fdml/meta/meter/@value` | string | `0..1` (quality workflow treats as required) | promoted |
| `meta.geometry.formation.kind` | `/fdml/meta/geometry/formation/@kind` | enum | `1` for v1.2 profiles | promoted |
| `meta.geometry.roles.role.id` | `/fdml/meta/geometry/roles/role/@id` | string[] | `0..n` (required when role references are used) | promoted |
| `step.geo.primitive.kind` | `/fdml/body//figure//step/geo/primitive/@kind` | enum | `1` per primitive | promoted |

Current promoted observed values from M10 evidence:
- formation kinds: `circle`, `line`, `couple`, `twoLinesFacing`
- primitive kinds (observed in candidate set): `move`

Contract enum anchors:
- `GeoFormationKind`: `circle|line|couple|twoLinesFacing`
- `GeoPrimitiveKind`: `move|face|turn|twirl|approach|retreat|swapPlaces|pass|weave|releaseHold|progress|relpos`

### 9.2 Single-structure extension policy

- One FDML contract is used for all examples; no subset-specific schema branches.
- New formation or primitive concepts are added through versioned enum expansion in `schema/fdml.xsd`.
- Candidate promotion requires evidence-backed rows with confidence and support counts.
- Validators consume the same canonical paths for the full corpus.

### 9.3 Decision registry and reversal conditions

- Formation kind as required v1.2 contract field:
  - Trade-off: deterministic geometry semantics vs enum governance overhead.
  - Reversal condition: if repeated unsupported formation families appear, add versioned enum values.
- Primitive kind as canonical step semantic field:
  - Trade-off: precise validator behavior vs need for controlled vocabulary growth.
  - Reversal condition: if unresolved primitives exceed governance threshold, extend enum in next contract revision.
- Role inventory promotion:
  - Trade-off: consistent references vs normalization effort on noisy source text.
  - Reversal condition: if role normalization repeatedly fails, allow provisional namespaces before hard enforcement.
- Meter value promotion:
  - Trade-off: deterministic timing checks vs normalization overhead for malformed source timing strings.
  - Reversal condition: if meter normalization repeatedly fails at scale, downgrade to advisory until correction pass exists.

### 9.4 Machine-readable promotion artifact

`out/m11_contract_promotion.json` is the decision registry source of truth for this promotion step.

## 10. Contract Deepening (M16)

M16 re-runs contract promotion against `out/m15_ontology_candidates.json`
to deepen the same unified FDML contract without introducing subset branches.

### 10.1 M16 promotion snapshot

- source artifact: `out/m16_contract_promotion.json`
- accepted ontology rows: `21/21`
- promoted contract fields: `17`
- unknown key count: `0`

Newly promoted field relative to earlier M11 snapshot:
- `meta.geometry.hold.kind` (`/fdml/meta/geometry/hold/@kind`)

### 10.2 M16 contract continuity rules

- M16 uses the same canonical contract field mapping model and decision-registry structure as M11.
- Promotion remains evidence-linked and requires confidence/support thresholds.
- Schema/spec alignment is checked against `schema/fdml.xsd` and this document on every M16 promotion run.

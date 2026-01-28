# FDML v1.2 — Geometry Extension (Specification Draft)

This document specifies a **language extension** for FDML documents with `fdml/@version = "1.2"`.

It is derived **only** from evidence in this repository:
- Current core schema: `schema/fdml.xsd`
- Current semantic rules: `schematron/fdml.sch`
- Existing CLI architecture/validation approach: `src/main/java/org/fdml/cli/*.java`
- LLM-derived relation/primitive inventories captured as JSON:
  - `analysis/out/llm/abdala.json`
  - `analysis/out/llm/cobankat.json`
  - `analysis/out/llm/aalistullaa.json`
  - `analysis/out/llm/haire-mamougeh.json`
  - `analysis/out/llm/mayim-mayim.json`

If something is unknown, it is marked as **UNKNOWN** and the exact file path that would resolve it is cited.

---

## 0) Background: what FDML already provides (v1.0–v1.1)

### Existing structural model (XSD)
From `schema/fdml.xsd`:
- Root: `<fdml version="…"><meta>…</meta><body>…</body></fdml>`
- `meta` contains (optionally) `<formation text="…"/>`, `<type genre="…" style="…"/>`, `<meter value="…"/>`, etc.
- `body` contains `section`, `part`, `figure`, `sequence`.
- `figure` contains `step` elements (and/or `measureRange/step`).
- `step` has attributes `who`, `action`, `beats`, optional `direction`, `facing`, `startFoot`, `endFoot`, `count`.

### Existing semantic checks (Schematron)
From `schematron/fdml.sch`:
- Presence checks: `meta`, `body`.
- Figure structure: `figure` must contain at least one step.
- Sequence references: `sequence/use/@figure` must reference an existing `figure/@id`.
- v1.1 checks:
  - require origin/type/meter
  - require sections `type="notes"` and `type="setup"`
  - type/formation text consistency (circle/line/couple string containment)

### Evidence of geometric semantics needed
The JSON analysis files explicitly contain:
- **formation types**: `circle`, `line`, `couple`, and “two lines facing each other” (`analysis/out/llm/*.json`).
- **relations** that are geometric/social constraints, e.g.
  - `hold` (belt hold, V-position, Armenian hold) (`analysis/out/llm/abdala.json`, `analysis/out/llm/cobankat.json`, `analysis/out/llm/haire-mamougeh.json`)
  - `facing_lines` and `approach_and_retreat` (`analysis/out/llm/haire-mamougeh.json`)
  - `partners_side_by_side` (`analysis/out/llm/aalistullaa.json`)
  - travel along a shared path (LOD / clockwise / counterclockwise) (`analysis/out/llm/abdala.json`, `analysis/out/llm/cobankat.json`, `analysis/out/llm/mayim-mayim.json`)

FDML v1.2 geometry aims to make these constraints **machine-checkable**, not just human text.

---

## 1) Goals and non-goals

### Goals
1. Allow FDML documents to declare **formation geometry** and **roles/dancers** explicitly.
2. Allow each step to include a structured list of **geometry primitives** (movement/orientation/hold).
3. Enable validation of higher-level invariants:
   - circle order preservation
   - two-line approach/retreat consistency
   - partner side-by-side constraints
   - hold constraints
4. Clearly separate which constraints belong to:
   - XSD (structure/type)
   - Schematron (cross-reference, local semantic rules)
   - Java geometry validator (stateful / computed / global invariants)

### Non-goals (for this draft)
- Full metric coordinates, collision avoidance, continuous kinematics.
- Authoring a canonical numeric coordinate system for every dance.

UNKNOWN: whether the project wants absolute coordinates vs relative/topological constraints.
- To resolve: add a design note under `docs/ARCHITECTURE.md`.

---

## 2) New v1.2 elements and attributes

This section defines **additive** elements/attrs for FDML v1.2.

### 2.1 `meta/geometry` (new)
Add a structured geometry block in metadata.

```xml
<fdml version="1.2">
  <meta>
    <title>…</title>

    <!-- Existing v1.1+ meta -->
    <origin country="…"/>
    <type genre="line"/>
    <meter value="2/4"/>
    <tempo bpm="120"/>

    <!-- New in v1.2 -->
    <geometry>
      <formation kind="circle"/>
      <dancers count="16"/>
      <roles>
        <role id="all"/>
      </roles>
    </geometry>
  </meta>
  …
</fdml>
```

#### 2.1.1 `geometry/formation`
- `@kind` (required): enumerated formation kinds.

Proposed values (evidence-driven):
- `circle` (seen in `analysis/out/llm/mayim-mayim.json`)
- `line` (seen in `analysis/out/llm/cobankat.json`)
- `couple` (seen in `analysis/out/llm/aalistullaa.json`)
- `twoLinesFacing` (seen in `analysis/out/llm/haire-mamougeh.json` initial formation)

Optional attributes:
- `@notes` (optional): free text for human nuance.

#### 2.1.2 `geometry/dancers`
- `@count` (optional): integer.

Rationale:
- The current XSD has no dancer count concept; the JSON analysis is dance-level and implies collective roles like `all`, `all_couples`, etc.

#### 2.1.3 `geometry/roles` and `geometry/roles/role`
Declare reusable role identifiers for `step/@who` and geometry primitives.

- `<role id="…"/>`

Evidence-driven role patterns found in JSON:
- `all` (`analysis/out/llm/*.json`)
- couples & couple components: `all_couples`, `couple_1`, `couple_2`, `inner_circle_couples` (`analysis/out/llm/aalistullaa.json`)
- group/line roles: `bride_line`, `groom_line`, `neighbors_in_same_line` (`analysis/out/llm/haire-mamougeh.json`)

NOTE: This spec does **not** rename existing `step/@who`; it formalizes it by allowing explicit declarations.

### 2.2 `body/geometry` (new, optional)
Allow declaring formation-specific topology (e.g., circle order, couple pairing) close to choreography.

```xml
<body>
  <geometry>
    <circle>
      <order role="all"/>
    </circle>
  </geometry>

  …
</body>
```

Proposed subelements (additive; optional):
- `<circle>`
  - `<order role="…"/>` (declares that dancers in this role have an order around the circle)
- `<twoLines>`
  - `<line id="bride" role="bride_line"/>
     <line id="groom" role="groom_line"/>
     <facing a="bride_line" b="groom_line"/>`
- `<couples>`
  - `<pair a="…" b="…" relationship="partners"/>`

UNKNOWN: exact dancer identity model (named dancers vs anonymous positions).
- To resolve: a concrete proposal + examples in a new directory like `docs/spec-examples/` (does not exist) or expand `docs/FDML-SPEC.md`.

### 2.3 Per-step geometry primitives (new)
FDML already has a `step` element with textual attributes; v1.2 adds a nested, machine-checkable geometry representation.

New: allow a child element under `step`:

```xml
<step who="all" action="travel" beats="4" direction="forward">
  <geo>
    <primitive kind="move" frame="formation" axis="tangent" amount="1" unit="measure"/>
  </geo>
</step>
```

#### 2.3.1 `<geo>`
- Container for one or more primitives.

#### 2.3.2 `<geo/primitive>`
Primitives are atomic geometry changes.

Required attributes:
- `@kind`: primitive type

Optional but commonly used:
- `@who`: role override (defaults to `step/@who`)
- `@frame`: coordinate frame (`formation`, `dancer`, `partner`, `opposite`, `line`) — see below.

##### Primitive kinds (evidence-driven inventory)
From the JSON step `action_type` and `inferred_relations` we can justify these primitive kinds:

Movement/orientation primitives:
- `move` (travel/run/step): supported by action types `travel`, `run`, `step` across JSON.
- `face` (explicit facing changes): action type `face` in `analysis/out/llm/mayim-mayim.json`.
- `turn` (rotation around a reference): action type `turn` in `analysis/out/llm/aalistullaa.json`.
- `approach` and `retreat` (two-line/couple approach): relation `approach_and_retreat` and step descriptions “toward … then back” in `analysis/out/llm/aalistullaa.json` and `analysis/out/llm/haire-mamougeh.json`.
- `pass` (passing an opposite): action type `pass` in `analysis/out/llm/aalistullaa.json`.
- `weave` (arch/pass under): action type `weave` in `analysis/out/llm/aalistullaa.json`.

Hold/contact primitives:
- `hold` (establish/maintain a handhold/belt hold): relation `hold` in `analysis/out/llm/abdala.json` and `analysis/out/llm/cobankat.json`, and within-line Armenian hold in `analysis/out/llm/haire-mamougeh.json`.
- `release` (drop a hold)

Other step-local primitives that affect geometry validation:
- `swapPlaces` (change places with opposite): implied by “change places with opposite” (`analysis/out/llm/aalistullaa.json`).
- `progress` (advance to next couple/opposite): action type `progress` in `analysis/out/llm/aalistullaa.json`.

##### Coordinate frames and references
The JSON files describe direction relative to:
- formation path (LOD / clockwise / counterclockwise)
- center (“face center”)
- line axes (two lines facing, forward/back)
- partner/opposite relationships

So v1.2 defines `@frame`:
- `formation`: directions like `around`, `tangent`, `radial`, `clockwise`, `counterclockwise`
- `line`: for two-line dances: `towardOppositeLine`, `awayFromOppositeLine`, `left`, `right`
- `partner`: relative to partner
- `opposite`: relative to opposite
- `dancer`: dancer-relative left/right/forward/back

And defines `@ref` (optional) for some primitives:
- `center`
- `neighbor`
- `partner`
- `opposite`

##### Primitive attributes (proposed)
- `@amount` (optional): numeric quantity
- `@unit` (optional): `beats`, `counts`, `measures`, `steps` (evidence: JSON has count ranges and “meas …”)
- `@dir` / `@axis` (optional): enumerated direction/axis depending on frame
- `@handhold` (optional): `vPos`, `armenian`, `belt`, `palmToPalm`, `handsJoinedLowV` (evidence across JSON)
- `@slot` (optional): for partner side-by-side, `leftOfPartner` / `rightOfPartner` (evidence: W left of partner)

---

## 3) Geometry invariants (what v1.2 must validate)

These are **semantic constraints** motivated by the JSON relation types and common formations in this repo.

### 3.1 Circle order preservation
Applies when formation is `circle` and the choreography uses around-the-circle travel.

Invariant:
- If a step (or figure/sequence) is declared as “travel around the circle” without explicit crossing/weaving, then the **cyclic order** of dancers in the circle must be preserved.

Evidence:
- Circle formation described in `analysis/out/llm/mayim-mayim.json` and travel “around the circle” / LOD.

Validation approach:
- XSD: can only enforce that a `<circle><order …/></circle>` declaration exists.
- Schematron: can enforce that steps which declare `primitive kind="move" frame="formation" axis="tangent"` also declare whether they are `preserveOrder="true"|"false"`.
- Java geometry validator: computes whether any primitive implies a swap/cross that violates order when `preserveOrder=true`.

UNKNOWN: what constitutes a “crossing” primitive that intentionally breaks order.
- To resolve: define explicit crossing primitives and semantics (candidate path: `docs/GEOMETRY-SPEC.md` itself plus example FDML in `corpus/valid/` for v1.2).

### 3.2 Two-line approach/retreat
Applies when formation is `twoLinesFacing`.

Invariant:
- Steps marked as `approach` must move both lines **toward** each other along the same axis, and `retreat` must move **away**, without changing left/right line membership unless explicitly modeled.

Evidence:
- “Two lines facing each other … approach and retreat” from `analysis/out/llm/haire-mamougeh.json`.

Validation approach:
- XSD: ensure `twoLines` structure exists and roles referenced exist.
- Schematron:
  - ensure both line roles exist (`bride_line`, `groom_line`) if referenced
  - ensure that an `approach` primitive in a two-line dance uses `frame="line"` and `axis="towardOppositeLine"` (or equivalent)
- Java geometry validator:
  - simulates line separation distance changes and asserts approach reduces distance, retreat increases distance.

### 3.3 Partner side-by-side constraint
Applies in `couple`-based formations and any time a role indicates partnership.

Invariant:
- If a role relationship declares `partners_side_by_side`, the partners must remain adjacent and in the declared left/right slot unless a primitive explicitly changes it (e.g., a `turn` around a shared center or `swapPlaces`).

Evidence:
- `analysis/out/llm/aalistullaa.json` includes `partners_side_by_side` with “W is left of partner”.

Validation approach:
- XSD: ensures a `<couples><pair … relationship="partners" …/></couples>` structure is well-formed.
- Schematron:
  - checks referenced role ids exist
  - ensures any primitive claiming to preserve slot uses a slot attribute.
- Java geometry validator:
  - checks that primitives do not violate adjacency/slot invariants unless overridden.

### 3.4 Hold constraints
Applies when a hold is declared as maintained across a region (figure/part/sequence) and certain primitives would be incompatible.

Invariant examples:
- If the hold is `armenian` (within-line pinky hold), dancers should not be modeled as “passing under” or “arching” without an explicit `release` and re-`hold`.
- If the hold is a belt hold / joined hands, primitives implying partner separation beyond reasonable adjacency must explicitly release.

Evidence:
- Armenian hold: `analysis/out/llm/haire-mamougeh.json`
- Belt hold: `analysis/out/llm/abdala.json`
- Hands joined V-position: `analysis/out/llm/cobankat.json`
- Palm-to-palm both hands for couple twirl: `analysis/out/llm/aalistullaa.json`

Validation approach:
- XSD: restrict hold types via enumeration (if implemented).
- Schematron:
  - local consistency: if a step has `primitive kind="weave"` or `primitive kind="pass"`, assert that hold state is not declared as “locked” in the same scope.
- Java geometry validator:
  - stateful hold tracking across steps, ensuring required releases occur.

UNKNOWN: the exact taxonomy of holds and which primitives require release.
- To resolve: add a hold compatibility table under `docs/GEOMETRY-SPEC.md` once there are v1.2 examples in `corpus/valid/`.

---

## 4) Validation responsibility split: XSD vs Schematron vs Java

FDML already uses a 3-layer approach:
- structure via XSD (`schema/fdml.xsd`)
- semantic assertions via Schematron (`schematron/fdml.sch` and `schematron/fdml-compiled.xsl`)
- computed checks via Java (see `Doctor` and `Linter` in `src/main/java/org/fdml/cli/*.java`)

v1.2 geometry follows the same pattern.

### 4.1 XSD (structure & simple typing)
XSD should validate:
- the existence and shape of `meta/geometry`
- formation kind enumerations
- role ids and basic structure
- allowed primitive kinds and required attributes per primitive type (where possible)

Why XSD:
- The current schema already models step attributes and nested structures; geometry elements fit this layer.

Implementation impact:
- Requires extending `schema/fdml.xsd`.

### 4.2 Schematron (cross-references and local semantic rules)
Schematron should validate:
- all referenced role ids exist (e.g., `primitive/@who` and `body/geometry/*/@role`)
- references like `@partner`, `@opposite`, `@neighbor` only appear when a corresponding relationship is declared
- constraints that are expressible as document-local assertions, e.g.
  - if `fdml/@version='1.2'` and formation kind is `circle`, require either a circle order declaration or an explicit statement that order is unspecified
  - if a step has `primitive kind='approach'`, ensure formation is `twoLinesFacing` or that a suitable reference frame is declared

Implementation impact:
- Requires extending `schematron/fdml.sch` (and updating `schematron/fdml-compiled.xsl`).

UNKNOWN: how this repo currently regenerates `schematron/fdml-compiled.xsl`.
- To resolve: document or add script (candidate path: `docs/ARCHITECTURE.md`).

### 4.3 Java geometry validator (stateful / computed invariants)
A Java validator is required for invariants that need simulation / global reasoning, like “circle order preserved”.

Planned responsibilities:
- parse v1.2 geometry declarations
- maintain an abstract formation state:
  - circle: cyclic order
  - two lines: line membership and separation
  - couples: partner adjacency/slots
  - hold state across roles
- apply per-step primitives in sequence order (including within `measureRange`)
- emit failures/warnings consistent with the CLI’s current patterns

Integration point:
- Add a new validator invoked by `doctor`.

UNKNOWN: where and how to integrate geometry checks into CLI.
- The existing aggregation is in `src/main/java/org/fdml/cli/Doctor.java`.
- To resolve: implement a new class (proposed path) `src/main/java/org/fdml/cli/GeometryValidator.java` and call it from `Doctor.run(...)`.

---

## 5) Proposed minimal schema additions (illustrative, not authoritative XSD)

This section is intentionally **illustrative**; it describes what should be added conceptually.
The authoritative implementation would live in `schema/fdml.xsd`.

### 5.1 Example: circle with order preservation
```xml
<fdml version="1.2">
  <meta>
    <title>Mayim Mayim (geometry-annotated)</title>
    <origin country="…"/>
    <type genre="circle"/>
    <meter value="4/4"/>
    <tempo bpm="…"/>
    <geometry>
      <formation kind="circle"/>
      <roles>
        <role id="all"/>
      </roles>
    </geometry>
  </meta>
  <body>
    <geometry>
      <circle>
        <order role="all"/>
      </circle>
    </geometry>

    <figure id="f-1" name="Part 3">
      <step who="all" action="run" beats="3" direction="around">
        <geo>
          <primitive kind="move" frame="formation" axis="tangent" dir="counterclockwise" amount="3" unit="steps" preserveOrder="true"/>
        </geo>
      </step>
    </figure>
  </body>
</fdml>
```

### 5.2 Example: two lines approach/retreat
```xml
<fdml version="1.2">
  <meta>
    <title>Haire Mamougeh (geometry-annotated)</title>
    <type genre="line"/>
    <meter value="2/4"/>
    <geometry>
      <formation kind="twoLinesFacing"/>
      <roles>
        <role id="bride_line"/>
        <role id="groom_line"/>
      </roles>
    </geometry>
  </meta>
  <body>
    <geometry>
      <twoLines>
        <line id="bride" role="bride_line"/>
        <line id="groom" role="groom_line"/>
        <facing a="bride_line" b="groom_line"/>
      </twoLines>
    </geometry>

    <figure id="f-approach" name="Approach">
      <step who="bride_line" action="step" beats="2" direction="forward">
        <geo><primitive kind="approach" frame="line" axis="towardOppositeLine" amount="1" unit="measure"/></geo>
      </step>
      <step who="groom_line" action="step" beats="2" direction="forward">
        <geo><primitive kind="approach" frame="line" axis="towardOppositeLine" amount="1" unit="measure"/></geo>
      </step>
    </figure>
  </body>
</fdml>
```

---

## 6) Compatibility and migration

- v1.2 geometry is optional and additive; existing v1.0/v1.1 documents remain valid under their existing rules.
- v1.2 documents should continue to use the existing textual `meta/formation@text` and `step/@direction`/`@facing` fields for human readability.
  - The structured geometry is the machine-checkable counterpart.

UNKNOWN: whether v1.2 should **require** geometry blocks.
- To resolve: add an explicit v1.2 Schematron pattern in `schematron/fdml.sch` once policy is decided.

---

## 7) Implementation checklist (repo-local)

To implement this spec in the current repo architecture:
1. Extend schema:
   - `schema/fdml.xsd`
2. Extend schematron:
   - `schematron/fdml.sch`
   - regenerate `schematron/fdml-compiled.xsl` (procedure currently UNKNOWN)
3. Add Java validator + wire into doctor:
   - proposed: `src/main/java/org/fdml/cli/GeometryValidator.java` (does not exist)
   - integrate via `src/main/java/org/fdml/cli/Doctor.java`
4. Add corpus examples:
   - `corpus/valid_v12/…` (does not exist)

UNKNOWN: repository convention for new corpus directories.
- To resolve: follow existing pattern in `corpus/invalid_v11/` and document in `docs/CONTRIBUTING.md`.

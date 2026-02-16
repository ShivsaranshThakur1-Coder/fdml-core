# PHASE3_PLAN: Complex Animation (Kinematics-Lite)

This phase introduces a deterministic 2D kinematic engine for card-page playback.

Engineering method:

`Spec -> Impl -> Test -> Fixture -> CI -> Demo`

## 1) Scope

- Build a 2D kinematic engine on card pages.
- Implement `line` + `twoLinesFacing` first.
- Defer `circle` + `couple` kinematics to follow-up items.
- Keep deterministic outputs and CI stability as a hard requirement.

## 2) Definition of Done (Per Item)

- [ ] Spec: behavior and non-goals documented.
- [ ] Impl: code merged with deterministic behavior.
- [ ] Test: happy-path and failure-path checks added/updated.
- [ ] Fixture: valid deterministic fixture(s) committed.
- [ ] CI: gate wired or extended in `make ci`/`mvn test`.
- [ ] Demo: visible in site card/demo surfaces.

## 3) Item List

| ID | Status | Deliverable |
| --- | --- | --- |
| P3-1 | NOW | 2D positions + smooth interpolation for `line` and `twoLinesFacing` |
| P3-2 | TODO | Circle positions + order-preserving swaps |
| P3-3 | TODO | Couple twirl/hold kinematics |
| P3-4 | TODO | Motion mapping for `move`/`turn`/`pass`/`weave` |
| P3-5 | TODO | Collision-lite soft constraints |

## 4) Execution Order

1. P3-1: line + twoLinesFacing interpolation core.
2. P3-2: circle layout/state transitions.
3. P3-3: couple hold/twirl kinematics.
4. P3-4: richer primitive-to-motion mapping.
5. P3-5: soft collision-lite constraints.

## 5) Rationale

- Start with line-like formations because slot-based positions already exist in export topology.
- Add circle/couple after interpolation + state-transition plumbing is stable.
- Defer richer primitive mapping until baseline trajectory and replay semantics are verified.
- Add collision-lite last to avoid masking earlier motion/state defects.

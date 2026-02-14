# Timing Validator Specification

This document describes the semantics implemented by `TimingValidator` (`src/main/java/org/fdml/cli/TimingValidator.java`).

## 1) Beat Unit

- `step/@beats` is interpreted as **counts**.
- Figure timing is validated using the sum of counts from both:
  - `figure/step/@beats`
  - `figure/measureRange/step/@beats`

## 2) Supported Meter Formats

`meta/meter/@value` supports:

1. Simple meter: `N/D`
   - Example: `3/4`, `4/4`, `9/16`
2. Additive meter: `A+B+.../D`
   - Example: `2+2+2+3/16`

All numeric components must be positive integers.

## 3) Bar Length Semantics (Counts)

### 3.1 Simple meter (`N/D`)

- Default rule: `barLengthCounts = N`.
- Figure total counts must align to `barLengthCounts`.

### 3.2 Special-case `9/16` compatibility

- For simple `9/16`, timing uses:
  - `barLengthCounts = 4` (count feel: `1-2-3-A`).
- Compatibility rule: phrases encoded in legacy corpus at half-bar granularity are accepted.
  - Practically, totals divisible by `4` pass.
  - For `9/16`, even totals are also accepted for backward compatibility.

Rationale:
- Existing corpus content (notably `corpus/valid/abdala.fdml.xml`) represents `9/16` phrases using a count model that does not map cleanly to strict numerator-as-count validation.
- The compatibility rule preserves current valid corpus behavior under `doctor --strict`.

### 3.3 Additive meter (`A+B+.../D`)

- `barLengthCounts = number of additive groups`.
  - Example: `2+2+2+3/16` has 4 groups, so `barLengthCounts = 4`.
- Figure totals must align to bar length in counts.
- Additive boundary checks are applied on **group boundaries** across step boundaries.

## 4) Issue Codes

`TimingValidator` emits the following issue codes:

- `missing_meter`
  - `meta/meter/@value` is absent or empty.
- `bad_meter_format`
  - Meter is not parseable as `N/D` or `A+B+.../D`.
- `bad_step_beats`
  - A step has missing/non-positive/non-integer `@beats`.
- `off_meter_figure`
  - Figure totals or additive boundary alignment fail timing rules.

## 5) Examples

### 5.1 Passing example (existing valid corpus)

From `corpus/valid/abdala.fdml.xml`:

```xml
<meter value="9/16" rhythmPattern="2+2+2+3"/>
...
<figure id="f-II">
  <measureRange from="1" to="2">
    <step who="all" beats="3" .../>
  </measureRange>
  <measureRange from="3" to="4">
    <step who="all" beats="3" .../>
  </measureRange>
</figure>
```

Total counts for `f-II` are 6, which passes due to `9/16` legacy compatibility.

### 5.2 Failing example (timing fixture)

`corpus/invalid_timing/example-off-meter.fdml.xml`:

```xml
<meter value="2+2+2+3/16"/>
...
<figure id="f-off">
  <step who="all" action="step one" beats="3" startFoot="R"/>
  <step who="all" action="step two" beats="6" startFoot="L"/>
</figure>
```

This fails timing with `off_meter_figure` because step boundaries do not align with additive group boundaries.

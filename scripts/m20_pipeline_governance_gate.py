#!/usr/bin/env python3
"""Governance gate for M20 corpus expansion and source-grounded descriptor/validator adoption."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Validate M20 expansion plus source-grounded descriptor/validator pipeline "
            "and emit decision/assumption/risk ledgers."
        )
    )
    ap.add_argument("--expansion-report", required=True, help="path to M20 corpus-expansion report")
    ap.add_argument("--descriptor-report", required=True, help="path to M20 descriptor evidence report")
    ap.add_argument("--descriptor-registry-report", required=True, help="path to M20 descriptor registry report")
    ap.add_argument("--descriptor-coverage-report", required=True, help="path to M20 descriptor coverage report")
    ap.add_argument("--validator-m17-baseline-report", required=True, help="path to M20 baseline M17 validator report")
    ap.add_argument("--validator-m17-current-report", required=True, help="path to M20 current M17 validator report")
    ap.add_argument("--validator-baseline-report", required=True, help="path to M20 baseline validator report")
    ap.add_argument("--validator-current-report", required=True, help="path to M20 current validator report")
    ap.add_argument("--burndown-report", required=True, help="path to M20 validator burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md", help="path to submission doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m20-pipeline-governance", help="report label")

    ap.add_argument(
        "--required-source-dir",
        default="out/m2_conversion/run1",
        help="required canonical source corpus dir for M20 expansion",
    )
    ap.add_argument(
        "--required-descriptor-out-dir",
        default="out/m20_descriptor_evidence/run1",
        help="required descriptor evidence output dir",
    )
    ap.add_argument(
        "--required-source-text-dir",
        action="append",
        default=[],
        help="required source text dirs used by descriptor/validator steps (repeatable)",
    )
    ap.add_argument(
        "--required-manifest",
        default="out/acquired_sources/merged_manifest.json",
        help="required merged manifest path used by M20 expansion",
    )
    ap.add_argument(
        "--required-candidate-report",
        default="out/m15_validator_candidates.json",
        help="required candidate report used by M17 layer",
    )
    ap.add_argument(
        "--required-m17-baseline-report",
        default="out/m20_validator_expansion_baseline_m17_report.json",
        help="required M17 baseline report path used by M20 baseline validator layer",
    )
    ap.add_argument(
        "--required-m17-current-report",
        default="out/m20_validator_expansion_m17_report.json",
        help="required M17 current report path used by M20 current validator layer",
    )
    ap.add_argument(
        "--required-baseline-report",
        default="out/m20_validator_expansion_baseline_report.json",
        help="required M20 baseline validator report for burndown",
    )
    ap.add_argument(
        "--required-current-report",
        default="out/m20_validator_expansion_report.json",
        help="required M20 current validator report for burndown",
    )
    ap.add_argument(
        "--required-coverage-report",
        default="out/m20_fdml_coverage_report.json",
        help="required coverage report path referenced by expansion step",
    )
    ap.add_argument(
        "--required-baseline-gap-report",
        default="out/m19_corpus_expansion_report.json",
        help="required baseline gap report used by M20 expansion",
    )

    ap.add_argument("--min-total-files", type=int, default=100, help="minimum source files")
    ap.add_argument("--min-country-coverage-ratio", type=float, default=0.0)
    ap.add_argument("--min-region-coverage-ratio", type=float, default=0.0)
    ap.add_argument("--min-region-buckets", type=int, default=5)
    ap.add_argument("--min-gap-reduction-ratio", type=float, default=0.60)
    ap.add_argument("--min-gap-buckets-improved", type=int, default=3)
    ap.add_argument("--min-descriptor-files-updated", type=int, default=40)
    ap.add_argument("--min-source-grounded-additions", type=int, default=80)
    ap.add_argument("--min-descriptor-keys-with-growth", type=int, default=6)
    ap.add_argument("--min-descriptor-keys-with-support", type=int, default=18)
    ap.add_argument("--min-style-keys-with-support", type=int, default=8)
    ap.add_argument("--min-culture-keys-with-support", type=int, default=6)
    ap.add_argument("--min-files-with-cultural-depth", type=int, default=85)
    ap.add_argument("--min-files-with-combined-depth", type=int, default=85)
    ap.add_argument("--min-expanded-rules", type=int, default=8)
    ap.add_argument("--min-source-grounded-applicable", type=int, default=80)
    ap.add_argument("--min-reduction-ratio", type=float, default=0.60)
    ap.add_argument("--max-failure-file-ratio", type=float, default=0.35)
    ap.add_argument("--min-decision-count", type=int, default=5)
    ap.add_argument("--min-assumption-count", type=int, default=5)
    ap.add_argument("--min-risk-count", type=int, default=5)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m20_pipeline_governance_gate.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"1", "true", "yes", "y"}:
            return True
        if token in {"0", "false", "no", "n"}:
            return False
    return default


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").rstrip("/")


def normalize_paths(values: list[Any]) -> list[str]:
    out = [normalize_path(str(v)) for v in values if str(v).strip()]
    return sorted(set(out))


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_make_target_line(make_text: str, target: str) -> str:
    needle = target + ":"
    for line in make_text.splitlines():
        if line.startswith(needle):
            return line
    return ""


def extract_make_target_block(make_text: str, target: str) -> str:
    match = re.search(rf"(?ms)^{re.escape(target)}:\n(.*?)(?:^\S|\Z)", make_text)
    if not match:
        return ""
    return match.group(1)


def check_ok(payload: dict[str, Any], check_id: str) -> bool:
    for row in as_list(payload.get("checks")):
        d = as_dict(row)
        if str(d.get("id") or "") == check_id:
            return as_bool(d.get("ok"), False)
    return False


def build_decision_registry(required_source_dir: str, required_descriptor_out_dir: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "M20-DEC-001",
            "decision": "Keep one canonical source corpus for expansion and source-grounded uplift",
            "chosenOption": f"Use {required_source_dir} as canonical M20 source path",
            "alternativesConsidered": [
                "run per-region corpora",
                "use mixed source snapshots across steps",
            ],
            "tradeoffs": [
                "pro: deterministic stage comparability and auditable metrics",
                "con: every breadth/depth change must fit one shared FDML structure",
            ],
            "reversalCondition": "if corpus root changes, update all M20 stage inputs atomically",
        },
        {
            "id": "M20-DEC-002",
            "decision": "Keep descriptor evidence as an explicit stage artifact",
            "chosenOption": f"descriptor evidence output fixed at {required_descriptor_out_dir}",
            "alternativesConsidered": [
                "in-place mutation of converted corpus",
                "validator-only source grounding without descriptor stage",
            ],
            "tradeoffs": [
                "pro: explicit before/after evidence for descriptor grounding",
                "con: additional artifact set to maintain",
            ],
            "reversalCondition": "if stage is removed, preserve equivalent baseline/current reproducibility",
        },
        {
            "id": "M20-DEC-003",
            "decision": "Evaluate M20 validator realism as a dedicated layer",
            "chosenOption": "compose M20 validator checks from base M17 mapping plus 8 source-grounded rules",
            "alternativesConsidered": [
                "fold M20 rules into legacy validator totals",
                "skip baseline/current M20 layer burndown",
            ],
            "tradeoffs": [
                "pro: isolates source-grounded realism progress",
                "con: governance must enforce cross-report input invariants",
            ],
            "reversalCondition": "if layered composition becomes unstable, migrate to single-pass unified validator output",
        },
        {
            "id": "M20-DEC-004",
            "decision": "Promote M20 governance to CI",
            "chosenOption": "wire m20-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "manual governance execution",
                "document-only governance assertions",
            ],
            "tradeoffs": [
                "pro: anti-drift enforcement on every CI run",
                "con: small CI runtime increase",
            ],
            "reversalCondition": "if CI budget tightens, split stages but keep governance fail-fast",
        },
        {
            "id": "M20-DEC-005",
            "decision": "Synchronize release evidence docs with M20 machine artifacts",
            "chosenOption": "update submission/program docs with M20 commands and artifact paths",
            "alternativesConsidered": [
                "keep release docs at M19 snapshot",
                "store M20 evidence only in tracker files",
            ],
            "tradeoffs": [
                "pro: evaluator-facing release story is current and reproducible",
                "con: docs require ongoing synchronization with pipeline changes",
            ],
            "reversalCondition": "if release handoff format changes, migrate references to the new canonical release doc",
        },
    ]


def build_assumption_registry(
    required_source_dir: str,
    required_descriptor_out_dir: str,
    min_gap_reduction_ratio: float,
    min_reduction_ratio: float,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M20-ASM-001",
            "assumption": "Converted corpus remains canonical source for M20 expansion and grounding",
            "confidence": 0.9,
            "verificationPlan": f"enforce stage inputs reference {required_source_dir}",
            "invalidationSignal": "any M20 stage reads from a different corpus path",
        },
        {
            "id": "M20-ASM-002",
            "assumption": "Descriptor evidence output remains canonical input for current M20 coverage and validation",
            "confidence": 0.9,
            "verificationPlan": f"enforce current coverage/validator inputs reference {required_descriptor_out_dir}",
            "invalidationSignal": "current coverage/validator inputs diverge from descriptor evidence output",
        },
        {
            "id": "M20-ASM-003",
            "assumption": "Gap reduction versus M19 baseline is a meaningful breadth signal",
            "confidence": 0.85,
            "verificationPlan": f"require gap reduction ratio >= {min_gap_reduction_ratio:.2f} and no gap regression",
            "invalidationSignal": "ratio passes while bucket-level regional quality regresses",
        },
        {
            "id": "M20-ASM-004",
            "assumption": "M20 baseline/current burndown reflects real source-grounded validator gains",
            "confidence": 0.85,
            "verificationPlan": f"require reduction ratio >= {min_reduction_ratio:.2f} with applicability and mapping integrity",
            "invalidationSignal": "burndown improves only due to applicability collapse or mapping drift",
        },
        {
            "id": "M20-ASM-005",
            "assumption": "Program and submission docs stay synchronized with M20 outputs",
            "confidence": 0.75,
            "verificationPlan": "require PRG-202/PRG-203 outcomes in PROGRAM_PLAN and M20 release references in SUBMISSION",
            "invalidationSignal": "governance passes while release docs omit current M20 artifacts",
        },
    ]


def build_risk_ledger(
    baseline_gap_total: int,
    current_gap_total: int,
    descriptor_files_updated: int,
    source_grounded_additions: int,
    validator_rule_count: int,
    validator_total_applicable: int,
    baseline_failures: int,
    current_failures: int,
    missing_candidate_keys: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M20-RSK-001",
            "risk": "Regional breadth gains can hide residual long-tail imbalance",
            "severity": "high",
            "likelihood": "medium",
            "signal": f"baselineGapTotal={baseline_gap_total} currentGapTotal={current_gap_total}",
            "mitigation": "carry explicit bucket backlog candidates forward with machine-readable deltas",
            "owner": "corpus",
        },
        {
            "id": "M20-RSK-002",
            "risk": "Source-grounded descriptor additions may still under-cover nuanced style semantics",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"descriptorFilesUpdated={descriptor_files_updated} additions={source_grounded_additions}",
            "mitigation": "continue expanding evidence lexeme families and coverage thresholds",
            "owner": "descriptor",
        },
        {
            "id": "M20-RSK-003",
            "risk": "Dedicated M20 rule layer may lose applicability on future corpus shifts",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"validatorRuleCount={validator_rule_count} sourceGroundedApplicable={validator_total_applicable}",
            "mitigation": "fail governance on applicability/mapping regression and maintain baseline/current checks",
            "owner": "validator",
        },
        {
            "id": "M20-RSK-004",
            "risk": "Burndown metrics can mask coverage issues if mapping degrades",
            "severity": "high",
            "likelihood": "low",
            "signal": f"missingCandidateKeys={missing_candidate_keys} baselineFailures={baseline_failures} currentFailures={current_failures}",
            "mitigation": "enforce candidate mapping completeness and source-grounded applicability in governance",
            "owner": "pipeline",
        },
        {
            "id": "M20-RSK-005",
            "risk": "Release evidence can become stale as M20 checks evolve",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "submission doc lacks M20 command/evidence references",
            "mitigation": "gate on SUBMISSION.md references and CI wiring for M20 governance",
            "owner": "release",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if not (0.0 <= args.min_country_coverage_ratio <= 1.0):
        return fail("--min-country-coverage-ratio must be in [0,1]")
    if not (0.0 <= args.min_region_coverage_ratio <= 1.0):
        return fail("--min-region-coverage-ratio must be in [0,1]")
    if args.min_region_buckets <= 0:
        return fail("--min-region-buckets must be > 0")
    if not (0.0 <= args.min_gap_reduction_ratio <= 1.0):
        return fail("--min-gap-reduction-ratio must be in [0,1]")
    if args.min_gap_buckets_improved < 0:
        return fail("--min-gap-buckets-improved must be >= 0")
    if args.min_descriptor_files_updated < 0:
        return fail("--min-descriptor-files-updated must be >= 0")
    if args.min_source_grounded_additions < 0:
        return fail("--min-source-grounded-additions must be >= 0")
    if args.min_descriptor_keys_with_growth < 0:
        return fail("--min-descriptor-keys-with-growth must be >= 0")
    if args.min_descriptor_keys_with_support <= 0:
        return fail("--min-descriptor-keys-with-support must be > 0")
    if args.min_style_keys_with_support <= 0:
        return fail("--min-style-keys-with-support must be > 0")
    if args.min_culture_keys_with_support <= 0:
        return fail("--min-culture-keys-with-support must be > 0")
    if args.min_files_with_cultural_depth <= 0 or args.min_files_with_combined_depth <= 0:
        return fail("min files with cultural/combined depth must be > 0")
    if args.min_expanded_rules <= 0:
        return fail("--min-expanded-rules must be > 0")
    if args.min_source_grounded_applicable < 0:
        return fail("--min-source-grounded-applicable must be >= 0")
    if not (0.0 <= args.min_reduction_ratio <= 1.0):
        return fail("--min-reduction-ratio must be in [0,1]")
    if not (0.0 <= args.max_failure_file_ratio <= 1.0):
        return fail("--max-failure-file-ratio must be in [0,1]")
    if args.min_decision_count <= 0 or args.min_assumption_count <= 0 or args.min_risk_count <= 0:
        return fail("min decision/assumption/risk counts must be > 0")

    expansion_path = Path(args.expansion_report)
    descriptor_path = Path(args.descriptor_report)
    descriptor_registry_path = Path(args.descriptor_registry_report)
    descriptor_coverage_path = Path(args.descriptor_coverage_report)
    validator_m17_baseline_path = Path(args.validator_m17_baseline_report)
    validator_m17_current_path = Path(args.validator_m17_current_report)
    validator_baseline_path = Path(args.validator_baseline_report)
    validator_current_path = Path(args.validator_current_report)
    burndown_path = Path(args.burndown_report)
    makefile_path = Path(args.makefile)
    program_plan_path = Path(args.program_plan_doc)
    submission_path = Path(args.submission_doc)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (expansion_path, "--expansion-report"),
        (descriptor_path, "--descriptor-report"),
        (descriptor_registry_path, "--descriptor-registry-report"),
        (descriptor_coverage_path, "--descriptor-coverage-report"),
        (validator_m17_baseline_path, "--validator-m17-baseline-report"),
        (validator_m17_current_path, "--validator-m17-current-report"),
        (validator_baseline_path, "--validator-baseline-report"),
        (validator_current_path, "--validator-current-report"),
        (burndown_path, "--burndown-report"),
        (makefile_path, "--makefile"),
        (program_plan_path, "--program-plan-doc"),
        (submission_path, "--submission-doc"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    try:
        expansion = load_json(expansion_path)
        descriptor = load_json(descriptor_path)
        descriptor_registry = load_json(descriptor_registry_path)
        descriptor_coverage = load_json(descriptor_coverage_path)
        validator_m17_baseline = load_json(validator_m17_baseline_path)
        validator_m17_current = load_json(validator_m17_current_path)
        validator_baseline = load_json(validator_baseline_path)
        validator_current = load_json(validator_current_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_source_dir = normalize_path(str(args.required_source_dir))
    required_descriptor_out_dir = normalize_path(str(args.required_descriptor_out_dir))
    required_source_text_dirs = normalize_paths(args.required_source_text_dir or ["out/acquired_sources", "out/acquired_sources_nonwiki"])
    required_manifest = normalize_path(str(args.required_manifest))
    required_candidate_report = normalize_path(str(args.required_candidate_report))
    required_m17_baseline_report = normalize_path(str(args.required_m17_baseline_report))
    required_m17_current_report = normalize_path(str(args.required_m17_current_report))
    required_baseline_report = normalize_path(str(args.required_baseline_report))
    required_current_report = normalize_path(str(args.required_current_report))
    required_coverage_report = normalize_path(str(args.required_coverage_report))
    required_baseline_gap_report = normalize_path(str(args.required_baseline_gap_report))

    expansion_inputs = as_dict(expansion.get("inputs"))
    expansion_source_dir = normalize_path(str(expansion_inputs.get("inputDir") or ""))
    expansion_coverage_report = normalize_path(str(expansion_inputs.get("coverageReport") or ""))
    expansion_manifest = normalize_path(str(expansion_inputs.get("manifest") or ""))
    expansion_baseline_report = normalize_path(str(expansion_inputs.get("baselineReport") or ""))
    expansion_totals = as_dict(expansion.get("totals"))
    expansion_source = as_int(expansion_totals.get("sourceFiles"), 0)
    expansion_processed = as_int(expansion_totals.get("processedFiles"), 0)
    expansion_country_ratio = clamp01(as_float(expansion_totals.get("countryCoverageRatio"), 0.0))
    expansion_region_ratio = clamp01(as_float(expansion_totals.get("regionCoverageRatio"), 0.0))
    expansion_region_buckets = as_int(expansion_totals.get("regionBucketsWithSignal"), 0)
    expansion_target_bucket_count = as_int(expansion_totals.get("targetBucketCount"), 0)
    baseline_gap_total = as_int(expansion_totals.get("baselineGapTotal"), 0)
    current_gap_total = as_int(expansion_totals.get("currentGapTotalVsM19Baseline"), 0)
    gap_reduction_ratio = clamp01(as_float(expansion_totals.get("gapReductionRatio"), 0.0))
    improved_gap_buckets = as_int(expansion_totals.get("improvedGapBuckets"), 0)
    regressed_gap_buckets = as_int(expansion_totals.get("regressedGapBuckets"), 0)

    descriptor_inputs = as_dict(descriptor.get("inputs"))
    descriptor_source_dir = normalize_path(str(descriptor_inputs.get("sourceDir") or ""))
    descriptor_source_text_dirs = normalize_paths(as_list(descriptor_inputs.get("sourceTextDirs")))
    descriptor_out_dir = normalize_path(str(descriptor_inputs.get("outDir") or ""))
    descriptor_totals = as_dict(descriptor.get("totals"))
    descriptor_source = as_int(descriptor_totals.get("sourceFiles"), 0)
    descriptor_processed = as_int(descriptor_totals.get("processedFiles"), 0)
    descriptor_files_updated = as_int(descriptor_totals.get("filesUpdated"), 0)
    source_grounded_additions = as_int(descriptor_totals.get("sourceGroundedAdditions"), 0)
    descriptor_doctor_ratio = clamp01(as_float(descriptor_totals.get("doctorPassRate"), 0.0))
    descriptor_geo_ratio = clamp01(as_float(descriptor_totals.get("geoPassRate"), 0.0))
    descriptor_keys_with_growth = as_int(descriptor_totals.get("keysWithGrowth"), 0)
    marker_style_before = as_int(descriptor_totals.get("markerStyleFilesBefore"), 0)
    marker_style_after = as_int(descriptor_totals.get("markerStyleFilesAfter"), 0)

    descriptor_registry_input_dir = normalize_path(str(descriptor_registry.get("inputDir") or ""))
    descriptor_registry_totals = as_dict(descriptor_registry.get("totals"))
    descriptor_keys_support = as_int(descriptor_registry_totals.get("descriptorKeysWithSupport"), 0)
    descriptor_keys_evidence = as_int(descriptor_registry_totals.get("descriptorKeysWithEvidence"), 0)

    descriptor_coverage_input_dir = normalize_path(str(descriptor_coverage.get("inputDir") or ""))
    descriptor_coverage_totals = as_dict(descriptor_coverage.get("totals"))
    style_keys_support = as_int(descriptor_coverage_totals.get("styleKeysWithSupport"), 0)
    culture_keys_support = as_int(descriptor_coverage_totals.get("cultureKeysWithSupport"), 0)
    files_with_cultural_depth = as_int(descriptor_coverage_totals.get("filesWithCulturalDepth"), 0)
    files_with_combined_depth = as_int(descriptor_coverage_totals.get("filesWithCombinedDepth"), 0)

    m17_baseline_inputs = as_dict(validator_m17_baseline.get("inputs"))
    m17_baseline_corpus = normalize_path(str(m17_baseline_inputs.get("corpusDir") or ""))
    m17_baseline_candidate_report = normalize_path(str(m17_baseline_inputs.get("candidateReport") or ""))
    m17_current_inputs = as_dict(validator_m17_current.get("inputs"))
    m17_current_corpus = normalize_path(str(m17_current_inputs.get("corpusDir") or ""))
    m17_current_candidate_report = normalize_path(str(m17_current_inputs.get("candidateReport") or ""))

    validator_baseline_inputs = as_dict(validator_baseline.get("inputs"))
    validator_baseline_corpus = normalize_path(str(validator_baseline_inputs.get("corpusDir") or ""))
    validator_baseline_base_report = normalize_path(str(validator_baseline_inputs.get("baseReport") or ""))
    validator_baseline_source_text_dirs = normalize_paths(as_list(validator_baseline_inputs.get("sourceTextDirs")))

    validator_current_inputs = as_dict(validator_current.get("inputs"))
    validator_current_corpus = normalize_path(str(validator_current_inputs.get("corpusDir") or ""))
    validator_current_base_report = normalize_path(str(validator_current_inputs.get("baseReport") or ""))
    validator_current_source_text_dirs = normalize_paths(as_list(validator_current_inputs.get("sourceTextDirs")))

    validator_current_totals = as_dict(validator_current.get("totals"))
    validator_source = as_int(validator_current_totals.get("sourceFiles"), 0)
    validator_processed = as_int(validator_current_totals.get("processedFiles"), 0)
    validator_rule_count = as_int(validator_current_totals.get("ruleCount"), 0)
    validator_candidate_keys = as_int(validator_current_totals.get("candidateKeys"), 0)
    validator_mapped_candidate_keys = as_int(validator_current_totals.get("mappedCandidateKeys"), 0)
    validator_total_applicable = as_int(validator_current_totals.get("m20SourceGroundedApplicable"), 0)

    validator_priority = as_dict(validator_current.get("priorityCoverage"))
    missing_candidate_keys = len(as_list(validator_priority.get("missingKeys")))
    validator_mapping_ratio = clamp01(as_float(validator_priority.get("coverageRatio"), 0.0))

    burndown_inputs = as_dict(burndown.get("inputs"))
    burndown_baseline_report = normalize_path(str(burndown_inputs.get("baselineReport") or ""))
    burndown_current_report = normalize_path(str(burndown_inputs.get("currentReport") or ""))
    burndown_totals = as_dict(burndown.get("totals"))
    baseline_failures = as_int(burndown_totals.get("baselineRuleFailures"), 0)
    current_failures = as_int(burndown_totals.get("currentRuleFailures"), 0)
    reduction_ratio = clamp01(as_float(burndown_totals.get("failureReductionRatio"), 0.0))
    failure_file_ratio = clamp01(as_float(burndown_totals.get("currentFailureFileRatio"), 1.0))

    make_text = makefile_path.read_text(encoding="utf-8")
    ci_line = extract_make_target_line(make_text, "ci")
    m20_expansion_block = extract_make_target_block(make_text, "m20-corpus-expansion-check")
    m20_depth_block = extract_make_target_block(make_text, "m20-descriptor-validator-expansion-check")
    m20_governance_block = extract_make_target_block(make_text, "m20-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")
    submission_text = submission_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(required_source_dir, required_descriptor_out_dir)
    assumptions = build_assumption_registry(
        required_source_dir,
        required_descriptor_out_dir,
        args.min_gap_reduction_ratio,
        args.min_reduction_ratio,
    )
    risks = build_risk_ledger(
        baseline_gap_total,
        current_gap_total,
        descriptor_files_updated,
        source_grounded_additions,
        validator_rule_count,
        validator_total_applicable,
        baseline_failures,
        current_failures,
        missing_candidate_keys,
    )

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check("m20_expansion_report_ok", as_bool(expansion.get("ok"), False), f"expansion_ok={as_bool(expansion.get('ok'), False)}")
    add_check(
        "m20_expansion_counts_min",
        expansion_source >= args.min_total_files and expansion_processed >= args.min_total_files,
        f"source={expansion_source} processed={expansion_processed} min={args.min_total_files}",
    )
    add_check(
        "m20_expansion_coverage_ratios_min",
        expansion_country_ratio >= args.min_country_coverage_ratio and expansion_region_ratio >= args.min_region_coverage_ratio,
        (
            f"country_ratio={expansion_country_ratio:.4f} min_country={args.min_country_coverage_ratio:.4f} "
            f"region_ratio={expansion_region_ratio:.4f} min_region={args.min_region_coverage_ratio:.4f}"
        ),
    )
    add_check(
        "m20_expansion_bucket_signal_min",
        expansion_region_buckets >= args.min_region_buckets and expansion_target_bucket_count >= args.min_region_buckets,
        (
            f"region_buckets_with_signal={expansion_region_buckets} "
            f"target_bucket_count={expansion_target_bucket_count} min={args.min_region_buckets}"
        ),
    )
    add_check(
        "m20_expansion_gap_reduction_min",
        gap_reduction_ratio >= args.min_gap_reduction_ratio,
        f"gap_reduction_ratio={gap_reduction_ratio:.4f} min={args.min_gap_reduction_ratio:.4f}",
    )
    add_check(
        "m20_expansion_gap_buckets_improved_min",
        improved_gap_buckets >= args.min_gap_buckets_improved,
        f"improved_gap_buckets={improved_gap_buckets} min={args.min_gap_buckets_improved}",
    )
    add_check(
        "m20_expansion_no_baseline_gap_regression",
        regressed_gap_buckets == 0,
        f"regressed_gap_buckets={regressed_gap_buckets} expected=0",
    )
    add_check(
        "m20_expansion_input_invariants",
        expansion_source_dir == required_source_dir
        and expansion_coverage_report == required_coverage_report
        and expansion_manifest == required_manifest
        and expansion_baseline_report == required_baseline_gap_report,
        (
            f"input_dir={expansion_source_dir} coverage_report={expansion_coverage_report} "
            f"manifest={expansion_manifest} baseline_report={expansion_baseline_report}"
        ),
    )
    add_check(
        "m20_expansion_checks_present",
        check_ok(expansion, "baseline_gap_reduction_ratio_min")
        and check_ok(expansion, "gap_buckets_improved_min")
        and check_ok(expansion, "no_baseline_gap_regression"),
        "expansion checks include gap reduction, improved buckets, and no-regression assertions",
    )

    add_check("m20_descriptor_report_ok", as_bool(descriptor.get("ok"), False), f"descriptor_ok={as_bool(descriptor.get('ok'), False)}")
    add_check(
        "m20_descriptor_counts_min",
        descriptor_source >= args.min_total_files
        and descriptor_processed >= args.min_total_files
        and descriptor_files_updated >= args.min_descriptor_files_updated,
        (
            f"source={descriptor_source} processed={descriptor_processed} "
            f"files_updated={descriptor_files_updated} min_updated={args.min_descriptor_files_updated}"
        ),
    )
    add_check(
        "m20_descriptor_source_grounded_additions_min",
        source_grounded_additions >= args.min_source_grounded_additions,
        f"source_grounded_additions={source_grounded_additions} min={args.min_source_grounded_additions}",
    )
    add_check(
        "m20_descriptor_quality",
        descriptor_doctor_ratio >= 0.999 and descriptor_geo_ratio >= 0.999,
        f"doctor_ratio={descriptor_doctor_ratio:.4f} geo_ratio={descriptor_geo_ratio:.4f}",
    )
    add_check(
        "m20_descriptor_stage_dir_invariants",
        descriptor_source_dir == required_source_dir
        and descriptor_out_dir == required_descriptor_out_dir
        and descriptor_registry_input_dir == required_descriptor_out_dir
        and descriptor_coverage_input_dir == required_descriptor_out_dir
        and descriptor_source_text_dirs == required_source_text_dirs,
        (
            f"descriptor_source={descriptor_source_dir} descriptor_out={descriptor_out_dir} "
            f"registry_input={descriptor_registry_input_dir} coverage_input={descriptor_coverage_input_dir} "
            f"source_text_dirs={descriptor_source_text_dirs}"
        ),
    )
    add_check(
        "m20_descriptor_growth_min",
        descriptor_keys_with_growth >= args.min_descriptor_keys_with_growth,
        f"keys_with_growth={descriptor_keys_with_growth} min={args.min_descriptor_keys_with_growth}",
    )
    add_check(
        "m20_descriptor_marker_style_not_regressed",
        marker_style_after <= marker_style_before,
        f"marker_style_before={marker_style_before} marker_style_after={marker_style_after}",
    )

    add_check(
        "m20_descriptor_registry_counts_min",
        descriptor_keys_support >= args.min_descriptor_keys_with_support
        and descriptor_keys_evidence >= args.min_descriptor_keys_with_support,
        (
            f"keys_with_support={descriptor_keys_support} keys_with_evidence={descriptor_keys_evidence} "
            f"min={args.min_descriptor_keys_with_support}"
        ),
    )
    add_check("m20_descriptor_coverage_report_ok", as_bool(descriptor_coverage.get("ok"), False), f"coverage_ok={as_bool(descriptor_coverage.get('ok'), False)}")
    add_check(
        "m20_descriptor_depth_thresholds",
        style_keys_support >= args.min_style_keys_with_support
        and culture_keys_support >= args.min_culture_keys_with_support
        and files_with_cultural_depth >= args.min_files_with_cultural_depth
        and files_with_combined_depth >= args.min_files_with_combined_depth,
        (
            f"style_keys={style_keys_support} min_style={args.min_style_keys_with_support} "
            f"culture_keys={culture_keys_support} min_culture={args.min_culture_keys_with_support} "
            f"cultural_depth={files_with_cultural_depth} min_cultural={args.min_files_with_cultural_depth} "
            f"combined_depth={files_with_combined_depth} min_combined={args.min_files_with_combined_depth}"
        ),
    )
    add_check(
        "m20_descriptor_coverage_checks_present",
        check_ok(descriptor_coverage, "style_keys_supported_min")
        and check_ok(descriptor_coverage, "culture_keys_supported_min")
        and check_ok(descriptor_coverage, "files_with_cultural_depth_min")
        and check_ok(descriptor_coverage, "files_with_combined_depth_min"),
        "coverage checks include style/culture/cultural-depth/combined-depth thresholds",
    )

    add_check("m20_validator_m17_baseline_ok", as_bool(validator_m17_baseline.get("ok"), False), f"validator_m17_baseline_ok={as_bool(validator_m17_baseline.get('ok'), False)}")
    add_check("m20_validator_m17_current_ok", as_bool(validator_m17_current.get("ok"), False), f"validator_m17_current_ok={as_bool(validator_m17_current.get('ok'), False)}")
    add_check(
        "m20_validator_m17_input_invariants",
        m17_baseline_corpus == required_source_dir
        and m17_current_corpus == required_descriptor_out_dir
        and m17_baseline_candidate_report == required_candidate_report
        and m17_current_candidate_report == required_candidate_report,
        (
            f"m17_baseline_corpus={m17_baseline_corpus} m17_current_corpus={m17_current_corpus} "
            f"candidate_report_baseline={m17_baseline_candidate_report} candidate_report_current={m17_current_candidate_report}"
        ),
    )
    add_check(
        "m20_validator_m17_mapping_complete",
        check_ok(validator_m17_baseline, "priority_key_mapping_complete")
        and check_ok(validator_m17_current, "priority_key_mapping_complete"),
        "m17 baseline/current mapping completeness checks pass",
    )

    add_check("m20_validator_baseline_ok", as_bool(validator_baseline.get("ok"), False), f"validator_baseline_ok={as_bool(validator_baseline.get('ok'), False)}")
    add_check("m20_validator_current_ok", as_bool(validator_current.get("ok"), False), f"validator_current_ok={as_bool(validator_current.get('ok'), False)}")
    add_check(
        "m20_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m20_validator_candidate_mapping_complete",
        check_ok(validator_current, "priority_key_mapping_complete")
        and missing_candidate_keys == 0
        and validator_mapping_ratio >= 0.999
        and validator_candidate_keys == validator_mapped_candidate_keys,
        (
            f"mapping_check={check_ok(validator_current, 'priority_key_mapping_complete')} "
            f"missing={missing_candidate_keys} coverage_ratio={validator_mapping_ratio:.4f} "
            f"mapped={validator_mapped_candidate_keys}/{validator_candidate_keys}"
        ),
    )
    add_check(
        "m20_validator_applicability_ok",
        check_ok(validator_current, "all_rules_have_applicability")
        and check_ok(validator_current, "source_grounded_applicability_min")
        and validator_total_applicable >= args.min_source_grounded_applicable,
        (
            f"all_rules_have_applicability={check_ok(validator_current, 'all_rules_have_applicability')} "
            f"source_grounded_applicability={validator_total_applicable} "
            f"min={args.min_source_grounded_applicable}"
        ),
    )
    add_check(
        "m20_validator_source_grounded_rules_added",
        check_ok(validator_baseline, "m20_descriptor_rules_added") and check_ok(validator_current, "m20_descriptor_rules_added"),
        "m20 source-grounded rule addition check passes for baseline/current",
    )
    add_check(
        "m20_validator_input_invariants",
        validator_baseline_corpus == required_source_dir
        and validator_current_corpus == required_descriptor_out_dir
        and validator_baseline_base_report == required_m17_baseline_report
        and validator_current_base_report == required_m17_current_report
        and validator_baseline_source_text_dirs == required_source_text_dirs
        and validator_current_source_text_dirs == required_source_text_dirs,
        (
            f"baseline_corpus={validator_baseline_corpus} current_corpus={validator_current_corpus} "
            f"baseline_base_report={validator_baseline_base_report} current_base_report={validator_current_base_report} "
            f"baseline_source_text_dirs={validator_baseline_source_text_dirs} "
            f"current_source_text_dirs={validator_current_source_text_dirs}"
        ),
    )

    add_check("m20_burndown_ok", as_bool(burndown.get("ok"), False), f"burndown_ok={as_bool(burndown.get('ok'), False)}")
    add_check(
        "m20_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m20_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m20_burndown_input_invariants",
        burndown_baseline_report == required_baseline_report and burndown_current_report == required_current_report,
        (
            f"burndown_baseline_report={burndown_baseline_report} required_baseline={required_baseline_report} "
            f"burndown_current_report={burndown_current_report} required_current={required_current_report}"
        ),
    )

    add_check(
        "m20_make_target_invariants",
        required_source_dir in m20_expansion_block
        and required_manifest in m20_expansion_block
        and required_coverage_report in m20_expansion_block
        and required_source_dir in m20_depth_block
        and required_descriptor_out_dir in m20_depth_block
        and required_candidate_report in m20_depth_block
        and required_m17_baseline_report in m20_depth_block
        and required_m17_current_report in m20_depth_block
        and required_baseline_report in m20_depth_block
        and required_current_report in m20_depth_block,
        "M20 make targets reference required dirs, reports, and source-grounded stage paths",
    )
    add_check(
        "make_ci_wires_m20_governance",
        "m20-pipeline-governance-check" in ci_line,
        "ci target includes m20-pipeline-governance-check",
    )
    add_check(
        "make_ci_keeps_m19_governance",
        "m19-pipeline-governance-check" in ci_line,
        "ci target retains m19-pipeline-governance-check",
    )
    add_check(
        "make_m20_targets_exist",
        bool(m20_expansion_block.strip()) and bool(m20_depth_block.strip()) and bool(m20_governance_block.strip()),
        "m20 expansion/depth/governance target blocks exist",
    )
    add_check(
        "program_plan_mentions_prg202_outcome",
        "M20 execution outcome (PRG-202)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-202 execution outcome",
    )
    add_check(
        "program_plan_mentions_prg203_outcome",
        "M20 execution outcome (PRG-203)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-203 execution outcome",
    )
    add_check(
        "submission_doc_mentions_m20_release",
        "m20-pipeline-governance-check" in submission_text
        and "out/m20_pipeline_governance.json" in submission_text,
        "SUBMISSION.md includes M20 release command and governance artifact",
    )
    add_check(
        "governance_decision_registry_min",
        len(decisions) >= args.min_decision_count,
        f"decision_rows={len(decisions)} min={args.min_decision_count}",
    )
    add_check(
        "governance_assumption_registry_min",
        len(assumptions) >= args.min_assumption_count,
        f"assumption_rows={len(assumptions)} min={args.min_assumption_count}",
    )
    add_check(
        "governance_risk_ledger_min",
        len(risks) >= args.min_risk_count,
        f"risk_rows={len(risks)} min={args.min_risk_count}",
    )

    ok = all(as_bool(row.get("ok"), False) for row in checks)

    payload: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "expansionReport": str(expansion_path),
            "descriptorReport": str(descriptor_path),
            "descriptorRegistryReport": str(descriptor_registry_path),
            "descriptorCoverageReport": str(descriptor_coverage_path),
            "validatorM17BaselineReport": str(validator_m17_baseline_path),
            "validatorM17CurrentReport": str(validator_m17_current_path),
            "validatorBaselineReport": str(validator_baseline_path),
            "validatorCurrentReport": str(validator_current_path),
            "burndownReport": str(burndown_path),
            "makefile": str(makefile_path),
            "programPlanDoc": str(program_plan_path),
            "submissionDoc": str(submission_path),
        },
        "thresholds": {
            "requiredSourceDir": required_source_dir,
            "requiredDescriptorOutDir": required_descriptor_out_dir,
            "requiredSourceTextDirs": required_source_text_dirs,
            "requiredManifest": required_manifest,
            "requiredCandidateReport": required_candidate_report,
            "requiredM17BaselineReport": required_m17_baseline_report,
            "requiredM17CurrentReport": required_m17_current_report,
            "requiredBaselineReport": required_baseline_report,
            "requiredCurrentReport": required_current_report,
            "requiredCoverageReport": required_coverage_report,
            "requiredBaselineGapReport": required_baseline_gap_report,
            "minTotalFiles": args.min_total_files,
            "minCountryCoverageRatio": args.min_country_coverage_ratio,
            "minRegionCoverageRatio": args.min_region_coverage_ratio,
            "minRegionBuckets": args.min_region_buckets,
            "minGapReductionRatio": args.min_gap_reduction_ratio,
            "minGapBucketsImproved": args.min_gap_buckets_improved,
            "minDescriptorFilesUpdated": args.min_descriptor_files_updated,
            "minSourceGroundedAdditions": args.min_source_grounded_additions,
            "minDescriptorKeysWithGrowth": args.min_descriptor_keys_with_growth,
            "minDescriptorKeysWithSupport": args.min_descriptor_keys_with_support,
            "minStyleKeysWithSupport": args.min_style_keys_with_support,
            "minCultureKeysWithSupport": args.min_culture_keys_with_support,
            "minFilesWithCulturalDepth": args.min_files_with_cultural_depth,
            "minFilesWithCombinedDepth": args.min_files_with_combined_depth,
            "minExpandedRules": args.min_expanded_rules,
            "minSourceGroundedApplicable": args.min_source_grounded_applicable,
            "minReductionRatio": args.min_reduction_ratio,
            "maxFailureFileRatio": args.max_failure_file_ratio,
            "minDecisionCount": args.min_decision_count,
            "minAssumptionCount": args.min_assumption_count,
            "minRiskCount": args.min_risk_count,
        },
        "metrics": {
            "expansionSourceFiles": expansion_source,
            "expansionProcessedFiles": expansion_processed,
            "expansionCountryCoverageRatio": round(expansion_country_ratio, 6),
            "expansionRegionCoverageRatio": round(expansion_region_ratio, 6),
            "expansionRegionBucketsWithSignal": expansion_region_buckets,
            "expansionTargetBucketCount": expansion_target_bucket_count,
            "baselineGapTotal": baseline_gap_total,
            "currentGapTotalVsM19Baseline": current_gap_total,
            "expansionGapReductionRatio": round(gap_reduction_ratio, 6),
            "expansionImprovedGapBuckets": improved_gap_buckets,
            "expansionRegressedGapBuckets": regressed_gap_buckets,
            "descriptorSourceFiles": descriptor_source,
            "descriptorProcessedFiles": descriptor_processed,
            "descriptorFilesUpdated": descriptor_files_updated,
            "sourceGroundedAdditions": source_grounded_additions,
            "descriptorKeysWithGrowth": descriptor_keys_with_growth,
            "descriptorDoctorPassRate": round(descriptor_doctor_ratio, 6),
            "descriptorGeoPassRate": round(descriptor_geo_ratio, 6),
            "markerStyleFilesBefore": marker_style_before,
            "markerStyleFilesAfter": marker_style_after,
            "descriptorKeysWithSupport": descriptor_keys_support,
            "descriptorKeysWithEvidence": descriptor_keys_evidence,
            "styleKeysWithSupport": style_keys_support,
            "cultureKeysWithSupport": culture_keys_support,
            "filesWithCulturalDepth": files_with_cultural_depth,
            "filesWithCombinedDepth": files_with_combined_depth,
            "validatorSourceFiles": validator_source,
            "validatorProcessedFiles": validator_processed,
            "validatorRuleCount": validator_rule_count,
            "validatorCandidateKeys": validator_candidate_keys,
            "validatorMappedCandidateKeys": validator_mapped_candidate_keys,
            "validatorMissingCandidateKeys": missing_candidate_keys,
            "validatorCoverageRatio": round(validator_mapping_ratio, 6),
            "validatorSourceGroundedApplicable": validator_total_applicable,
            "burndownBaselineFailures": baseline_failures,
            "burndownCurrentFailures": current_failures,
            "burndownReductionRatio": round(reduction_ratio, 6),
            "burndownFailureFileRatio": round(failure_file_ratio, 6),
        },
        "decisionRegistry": decisions,
        "assumptionRegistry": assumptions,
        "riskLedger": risks,
        "checks": checks,
        "ok": ok,
    }

    if report_out is not None:
        write_json(report_out, payload)
        print(f"Created: {report_out}")

    if ok:
        print("Summary: PASS")
        return 0
    print("Summary: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

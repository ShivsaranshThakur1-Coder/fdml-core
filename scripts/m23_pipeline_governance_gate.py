#!/usr/bin/env python3
"""Governance gate for M23 descriptor consolidation and validator coherence adoption."""

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
            "Validate M23 descriptor consolidation plus validator coherence pipeline and emit "
            "decision/assumption/risk ledgers."
        )
    )
    ap.add_argument("--descriptor-report", required=True, help="path to M23 descriptor consolidation report")
    ap.add_argument("--descriptor-registry-report", required=True, help="path to M23 descriptor registry report")
    ap.add_argument("--descriptor-coverage-report", required=True, help="path to M23 descriptor coverage report")
    ap.add_argument("--validator-baseline-report", required=True, help="path to M23 baseline validator report")
    ap.add_argument("--validator-current-report", required=True, help="path to M23 current validator report")
    ap.add_argument("--burndown-report", required=True, help="path to M23 validator burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md", help="path to submission doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m23-pipeline-governance", help="report label")

    ap.add_argument(
        "--required-source-dir",
        default="out/m22_descriptor_uplift/run1",
        help="required canonical source corpus dir for M23 descriptor consolidation and validator baseline",
    )
    ap.add_argument(
        "--required-descriptor-out-dir",
        default="out/m23_descriptor_consolidation/run1",
        help="required descriptor-consolidation output dir",
    )
    ap.add_argument(
        "--required-baseline-coverage-report",
        default="out/m22_fdml_coverage_report.json",
        help="required baseline coverage report path used by M23 descriptor consolidation",
    )
    ap.add_argument(
        "--required-base-validator-report",
        default="out/m22_validator_expansion_report.json",
        help="required M22 validator report used as mapping baseline in M23 validator runs",
    )
    ap.add_argument(
        "--required-descriptor-report-path",
        default="out/m23_descriptor_consolidation_report.json",
        help="required descriptor report path used by M23 validator runs",
    )
    ap.add_argument(
        "--required-source-text-dir",
        action="append",
        default=[],
        help="required source text dirs used by descriptor and validator steps (repeatable)",
    )
    ap.add_argument(
        "--required-baseline-report",
        default="out/m23_validator_expansion_baseline_report.json",
        help="required M23 baseline validator report path used by burndown",
    )
    ap.add_argument(
        "--required-current-report",
        default="out/m23_validator_expansion_report.json",
        help="required M23 current validator report path used by burndown",
    )

    ap.add_argument("--min-total-files", type=int, default=100, help="minimum source files")
    ap.add_argument("--min-descriptor-files-updated", type=int, default=20)
    ap.add_argument("--min-source-grounded-additions", type=int, default=40)
    ap.add_argument("--min-low-support-keys", type=int, default=6)
    ap.add_argument("--min-low-support-keys-with-growth", type=int, default=5)
    ap.add_argument("--min-descriptor-keys-with-support", type=int, default=18)
    ap.add_argument("--min-style-keys-with-support", type=int, default=8)
    ap.add_argument("--min-culture-keys-with-support", type=int, default=6)
    ap.add_argument("--min-files-with-cultural-depth", type=int, default=109)
    ap.add_argument("--min-files-with-combined-depth", type=int, default=105)
    ap.add_argument("--min-expanded-rules", type=int, default=20)
    ap.add_argument("--min-alignment-rules", type=int, default=16)
    ap.add_argument("--min-coherence-rules", type=int, default=4)
    ap.add_argument("--min-source-grounded-applicable", type=int, default=200)
    ap.add_argument("--min-coherence-applicable", type=int, default=100)
    ap.add_argument("--min-reduction-ratio", type=float, default=0.30)
    ap.add_argument("--max-failure-file-ratio", type=float, default=0.70)
    ap.add_argument("--min-decision-count", type=int, default=5)
    ap.add_argument("--min-assumption-count", type=int, default=5)
    ap.add_argument("--min-risk-count", type=int, default=5)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m23_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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
            "id": "M23-DEC-001",
            "decision": "Keep one canonical baseline/current corpus path for M23 descriptor consolidation and validator coherence",
            "chosenOption": f"Use {required_source_dir} as baseline and {required_descriptor_out_dir} as current corpus path",
            "alternativesConsidered": [
                "split descriptor and validator corpus roots",
                "regionalized M23 sub-pipelines",
            ],
            "tradeoffs": [
                "pro: deterministic baseline/current comparability across all 109 files",
                "con: all M23 improvements must fit one shared FDML structure",
            ],
            "reversalCondition": "if canonical paths change, update all M23 stage inputs atomically",
        },
        {
            "id": "M23-DEC-002",
            "decision": "Preserve low-support consolidation as an explicit stage artifact",
            "chosenOption": f"descriptor consolidation output fixed at {required_descriptor_out_dir}",
            "alternativesConsidered": [
                "in-place edits on M22 corpus without a stage artifact",
                "validator-only changes without descriptor consolidation",
            ],
            "tradeoffs": [
                "pro: auditable low-support before/after evidence prior to validator evaluation",
                "con: additional artifact set to maintain",
            ],
            "reversalCondition": "if stage is removed, preserve equivalent reproducible before/after evidence",
        },
        {
            "id": "M23-DEC-003",
            "decision": "Treat uplift-note integrity as first-class validator coherence constraints",
            "chosenOption": "compose M23 validator layer from 16 alignment rules plus 4 note-coherence rules",
            "alternativesConsidered": [
                "keep only alignment rules",
                "track note integrity only in descriptor stage",
            ],
            "tradeoffs": [
                "pro: measurable coupling between descriptor uplift intent and validator behavior",
                "con: governance must enforce descriptor-report and source-text invariants",
            ],
            "reversalCondition": "if coherence rules become unstable, migrate note checks into equivalent deterministic stage gate",
        },
        {
            "id": "M23-DEC-004",
            "decision": "Promote M23 governance to CI",
            "chosenOption": "wire m23-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "manual governance execution",
                "document-only governance assertions",
            ],
            "tradeoffs": [
                "pro: anti-drift enforcement on every CI run",
                "con: small CI runtime increase",
            ],
            "reversalCondition": "if CI budget tightens, split phases but keep governance fail-fast",
        },
        {
            "id": "M23-DEC-005",
            "decision": "Synchronize release evidence docs with M23 machine artifacts",
            "chosenOption": "update submission/program docs with explicit M23 commands and artifact paths",
            "alternativesConsidered": [
                "keep release docs at M22 snapshot",
                "store M23 evidence only in tracker files",
            ],
            "tradeoffs": [
                "pro: evaluator-facing release story stays current and reproducible",
                "con: docs require ongoing synchronization",
            ],
            "reversalCondition": "if release handoff format changes, migrate references to canonical release docs",
        },
    ]


def build_assumption_registry(
    required_source_dir: str,
    required_descriptor_out_dir: str,
    min_reduction_ratio: float,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M23-ASM-001",
            "assumption": "M22 descriptor-uplift corpus remains canonical baseline for M23",
            "confidence": 0.9,
            "verificationPlan": f"enforce descriptor and baseline validator inputs reference {required_source_dir}",
            "invalidationSignal": "any M23 stage reads from a different baseline corpus path",
        },
        {
            "id": "M23-ASM-002",
            "assumption": "M23 descriptor-consolidation output remains canonical current corpus",
            "confidence": 0.9,
            "verificationPlan": f"enforce current coverage/validator inputs reference {required_descriptor_out_dir}",
            "invalidationSignal": "coverage or validator current inputs diverge from descriptor consolidation output",
        },
        {
            "id": "M23-ASM-003",
            "assumption": "Low-support consolidation thresholds reflect real descriptor support improvements",
            "confidence": 0.85,
            "verificationPlan": "require files-updated, source-grounded additions, low-support key growth, and average-ratio increase",
            "invalidationSignal": "thresholds pass while low-support descriptor support regresses",
        },
        {
            "id": "M23-ASM-004",
            "assumption": "M23 burndown reflects genuine coherence-linked validator gains",
            "confidence": 0.85,
            "verificationPlan": f"require reduction ratio >= {min_reduction_ratio:.2f} with mapping and applicability checks",
            "invalidationSignal": "burndown improves only due to mapping or applicability drift",
        },
        {
            "id": "M23-ASM-005",
            "assumption": "Program and submission docs stay synchronized with M23 outputs",
            "confidence": 0.75,
            "verificationPlan": "require PRG-231/PRG-232/PRG-233 outcomes in PROGRAM_PLAN and M23 references in SUBMISSION",
            "invalidationSignal": "governance passes while release docs omit M23 artifacts",
        },
    ]


def build_risk_ledger(
    descriptor_files_updated: int,
    source_grounded_additions: int,
    low_support_key_count: int,
    low_support_keys_with_growth: int,
    low_support_before_ratio: float,
    low_support_after_ratio: float,
    validator_rule_count: int,
    alignment_rule_count: int,
    coherence_rule_count: int,
    validator_total_applicable: int,
    coherence_applicable: int,
    baseline_failures: int,
    current_failures: int,
    missing_candidate_keys: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M23-RSK-001",
            "risk": "Low-support descriptor families can remain uneven despite consolidation gains",
            "severity": "high",
            "likelihood": "medium",
            "signal": (
                f"filesUpdated={descriptor_files_updated} additions={source_grounded_additions} "
                f"lowSupportKeys={low_support_key_count} growthKeys={low_support_keys_with_growth} "
                f"ratio={low_support_before_ratio:.6f}->{low_support_after_ratio:.6f}"
            ),
            "mitigation": "continue evidence-driven consolidation for residual low-support families and monitor per-key backlog",
            "owner": "descriptor",
        },
        {
            "id": "M23-RSK-002",
            "risk": "Coherence rule applicability may regress on future corpus shifts",
            "severity": "medium",
            "likelihood": "medium",
            "signal": (
                f"validatorRuleCount={validator_rule_count} alignmentRules={alignment_rule_count} "
                f"coherenceRules={coherence_rule_count} sourceGroundedApplicable={validator_total_applicable} "
                f"coherenceApplicable={coherence_applicable}"
            ),
            "mitigation": "fail governance on rule-family minimums and applicability regression",
            "owner": "validator",
        },
        {
            "id": "M23-RSK-003",
            "risk": "Burndown metrics can hide regressions if mapping integrity drifts",
            "severity": "high",
            "likelihood": "low",
            "signal": (
                f"missingCandidateKeys={missing_candidate_keys} "
                f"baselineFailures={baseline_failures} currentFailures={current_failures}"
            ),
            "mitigation": "enforce candidate mapping completeness and source-grounded applicability in governance",
            "owner": "pipeline",
        },
        {
            "id": "M23-RSK-004",
            "risk": "CI can drift from intended M23 governance without explicit wiring checks",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "ci target missing m23-pipeline-governance-check",
            "mitigation": "gate on Makefile target existence and CI inclusion",
            "owner": "ci",
        },
        {
            "id": "M23-RSK-005",
            "risk": "Release evidence can become stale as M23 checks evolve",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "submission doc lacks M23 command/evidence references",
            "mitigation": "gate on SUBMISSION.md references and maintain PROGRAM_PLAN synchronization",
            "owner": "release",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_descriptor_files_updated < 0:
        return fail("--min-descriptor-files-updated must be >= 0")
    if args.min_source_grounded_additions < 0:
        return fail("--min-source-grounded-additions must be >= 0")
    if args.min_low_support_keys <= 0:
        return fail("--min-low-support-keys must be > 0")
    if args.min_low_support_keys_with_growth < 0:
        return fail("--min-low-support-keys-with-growth must be >= 0")
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
    if args.min_alignment_rules <= 0:
        return fail("--min-alignment-rules must be > 0")
    if args.min_coherence_rules <= 0:
        return fail("--min-coherence-rules must be > 0")
    if args.min_source_grounded_applicable < 0:
        return fail("--min-source-grounded-applicable must be >= 0")
    if args.min_coherence_applicable < 0:
        return fail("--min-coherence-applicable must be >= 0")
    if not (0.0 <= args.min_reduction_ratio <= 1.0):
        return fail("--min-reduction-ratio must be in [0,1]")
    if not (0.0 <= args.max_failure_file_ratio <= 1.0):
        return fail("--max-failure-file-ratio must be in [0,1]")
    if args.min_decision_count <= 0 or args.min_assumption_count <= 0 or args.min_risk_count <= 0:
        return fail("min decision/assumption/risk counts must be > 0")

    descriptor_path = Path(args.descriptor_report)
    descriptor_registry_path = Path(args.descriptor_registry_report)
    descriptor_coverage_path = Path(args.descriptor_coverage_report)
    validator_baseline_path = Path(args.validator_baseline_report)
    validator_current_path = Path(args.validator_current_report)
    burndown_path = Path(args.burndown_report)
    makefile_path = Path(args.makefile)
    program_plan_path = Path(args.program_plan_doc)
    submission_path = Path(args.submission_doc)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (descriptor_path, "--descriptor-report"),
        (descriptor_registry_path, "--descriptor-registry-report"),
        (descriptor_coverage_path, "--descriptor-coverage-report"),
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
        descriptor = load_json(descriptor_path)
        descriptor_registry = load_json(descriptor_registry_path)
        descriptor_coverage = load_json(descriptor_coverage_path)
        validator_baseline = load_json(validator_baseline_path)
        validator_current = load_json(validator_current_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_source_dir = normalize_path(str(args.required_source_dir))
    required_descriptor_out_dir = normalize_path(str(args.required_descriptor_out_dir))
    required_baseline_coverage_report = normalize_path(str(args.required_baseline_coverage_report))
    required_base_validator_report = normalize_path(str(args.required_base_validator_report))
    required_descriptor_report_path = normalize_path(str(args.required_descriptor_report_path))
    required_source_text_dirs = normalize_paths(args.required_source_text_dir or ["out/acquired_sources", "out/acquired_sources_nonwiki"])
    required_baseline_report = normalize_path(str(args.required_baseline_report))
    required_current_report = normalize_path(str(args.required_current_report))

    descriptor_inputs = as_dict(descriptor.get("inputs"))
    descriptor_source_dir = normalize_path(str(descriptor_inputs.get("sourceDir") or ""))
    descriptor_baseline_coverage = normalize_path(str(descriptor_inputs.get("baselineCoverageReport") or ""))
    descriptor_source_text_dirs = normalize_paths(as_list(descriptor_inputs.get("sourceTextDirs")))
    descriptor_out_dir = normalize_path(str(descriptor_inputs.get("outDir") or ""))
    descriptor_totals = as_dict(descriptor.get("totals"))
    descriptor_source = as_int(descriptor_totals.get("sourceFiles"), 0)
    descriptor_processed = as_int(descriptor_totals.get("processedFiles"), 0)
    descriptor_files_updated = as_int(descriptor_totals.get("filesUpdated"), 0)
    source_grounded_additions = as_int(descriptor_totals.get("sourceGroundedAdditions"), 0)
    descriptor_doctor_ratio = clamp01(as_float(descriptor_totals.get("doctorPassRate"), 0.0))
    descriptor_geo_ratio = clamp01(as_float(descriptor_totals.get("geoPassRate"), 0.0))
    low_support_key_count = as_int(descriptor_totals.get("lowSupportKeyCount"), 0)
    low_support_keys_with_growth = as_int(descriptor_totals.get("lowSupportKeysWithGrowth"), 0)
    low_support_before_ratio = clamp01(as_float(descriptor_totals.get("lowSupportAverageRatioBefore"), 0.0))
    low_support_after_ratio = clamp01(as_float(descriptor_totals.get("lowSupportAverageRatioAfter"), 0.0))
    low_support_additions = as_int(descriptor_totals.get("lowSupportAdditions"), 0)

    descriptor_support = as_dict(descriptor.get("descriptorSupport"))
    low_support_keys = [str(v).strip() for v in as_list(descriptor_support.get("lowSupportKeys")) if str(v).strip()]

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

    validator_baseline_inputs = as_dict(validator_baseline.get("inputs"))
    validator_baseline_corpus = normalize_path(str(validator_baseline_inputs.get("corpusDir") or ""))
    validator_baseline_base_report = normalize_path(str(validator_baseline_inputs.get("baseReport") or ""))
    validator_baseline_descriptor_report = normalize_path(str(validator_baseline_inputs.get("descriptorReport") or ""))
    validator_baseline_source_text_dirs = normalize_paths(as_list(validator_baseline_inputs.get("sourceTextDirs")))

    validator_current_inputs = as_dict(validator_current.get("inputs"))
    validator_current_corpus = normalize_path(str(validator_current_inputs.get("corpusDir") or ""))
    validator_current_base_report = normalize_path(str(validator_current_inputs.get("baseReport") or ""))
    validator_current_descriptor_report = normalize_path(str(validator_current_inputs.get("descriptorReport") or ""))
    validator_current_source_text_dirs = normalize_paths(as_list(validator_current_inputs.get("sourceTextDirs")))

    validator_current_totals = as_dict(validator_current.get("totals"))
    validator_source = as_int(validator_current_totals.get("sourceFiles"), 0)
    validator_processed = as_int(validator_current_totals.get("processedFiles"), 0)
    validator_rule_count = as_int(validator_current_totals.get("ruleCount"), 0)
    validator_candidate_keys = as_int(validator_current_totals.get("candidateKeys"), 0)
    validator_mapped_candidate_keys = as_int(validator_current_totals.get("mappedCandidateKeys"), 0)
    validator_total_applicable = as_int(validator_current_totals.get("m23SourceGroundedApplicable"), 0)
    validator_alignment_rule_count = as_int(validator_current_totals.get("m23AlignmentRuleCount"), 0)
    validator_coherence_rule_count = as_int(validator_current_totals.get("m23CoherenceRuleCount"), 0)
    validator_coherence_applicable = as_int(validator_current_totals.get("m23CoherenceApplicable"), 0)

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
    m23_descriptor_block = extract_make_target_block(make_text, "m23-descriptor-consolidation-check")
    m23_validator_block = extract_make_target_block(make_text, "m23-validator-expansion-check")
    m23_governance_block = extract_make_target_block(make_text, "m23-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")
    submission_text = submission_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(required_source_dir, required_descriptor_out_dir)
    assumptions = build_assumption_registry(required_source_dir, required_descriptor_out_dir, args.min_reduction_ratio)
    risks = build_risk_ledger(
        descriptor_files_updated,
        source_grounded_additions,
        low_support_key_count,
        low_support_keys_with_growth,
        low_support_before_ratio,
        low_support_after_ratio,
        validator_rule_count,
        validator_alignment_rule_count,
        validator_coherence_rule_count,
        validator_total_applicable,
        validator_coherence_applicable,
        baseline_failures,
        current_failures,
        missing_candidate_keys,
    )

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check("m23_descriptor_report_ok", as_bool(descriptor.get("ok"), False), f"descriptor_ok={as_bool(descriptor.get('ok'), False)}")
    add_check(
        "m23_descriptor_counts_min",
        descriptor_source >= args.min_total_files
        and descriptor_processed >= args.min_total_files
        and descriptor_files_updated >= args.min_descriptor_files_updated,
        (
            f"source={descriptor_source} processed={descriptor_processed} "
            f"files_updated={descriptor_files_updated} min_updated={args.min_descriptor_files_updated}"
        ),
    )
    add_check(
        "m23_descriptor_source_grounded_additions_min",
        source_grounded_additions >= args.min_source_grounded_additions,
        f"source_grounded_additions={source_grounded_additions} min={args.min_source_grounded_additions}",
    )
    add_check(
        "m23_descriptor_low_support_thresholds",
        low_support_key_count >= args.min_low_support_keys
        and low_support_keys_with_growth >= args.min_low_support_keys_with_growth
        and low_support_additions > 0
        and len(low_support_keys) >= args.min_low_support_keys,
        (
            f"low_support_key_count={low_support_key_count} min_keys={args.min_low_support_keys} "
            f"low_support_keys_with_growth={low_support_keys_with_growth} "
            f"min_growth={args.min_low_support_keys_with_growth} low_support_additions={low_support_additions} "
            f"low_support_keys_list={len(low_support_keys)}"
        ),
    )
    add_check(
        "m23_descriptor_low_support_ratio_increase",
        low_support_after_ratio >= low_support_before_ratio,
        f"low_support_avg_ratio={low_support_before_ratio:.6f}->{low_support_after_ratio:.6f}",
    )
    add_check(
        "m23_descriptor_quality",
        descriptor_doctor_ratio >= 0.999 and descriptor_geo_ratio >= 0.999,
        f"doctor_ratio={descriptor_doctor_ratio:.4f} geo_ratio={descriptor_geo_ratio:.4f}",
    )
    add_check(
        "m23_descriptor_stage_dir_invariants",
        descriptor_source_dir == required_source_dir
        and descriptor_out_dir == required_descriptor_out_dir
        and descriptor_baseline_coverage == required_baseline_coverage_report
        and descriptor_registry_input_dir == required_descriptor_out_dir
        and descriptor_coverage_input_dir == required_descriptor_out_dir
        and descriptor_source_text_dirs == required_source_text_dirs,
        (
            f"descriptor_source={descriptor_source_dir} descriptor_out={descriptor_out_dir} "
            f"baseline_coverage={descriptor_baseline_coverage} registry_input={descriptor_registry_input_dir} "
            f"coverage_input={descriptor_coverage_input_dir} source_text_dirs={descriptor_source_text_dirs}"
        ),
    )
    add_check(
        "m23_descriptor_checks_present",
        check_ok(descriptor, "source_files_min")
        and check_ok(descriptor, "low_support_keys_min")
        and check_ok(descriptor, "files_updated_min")
        and check_ok(descriptor, "source_grounded_additions_min")
        and check_ok(descriptor, "low_support_additions_positive")
        and check_ok(descriptor, "low_support_keys_with_growth_min")
        and check_ok(descriptor, "low_support_average_ratio_increase")
        and check_ok(descriptor, "doctor_pass_rate_min")
        and check_ok(descriptor, "geo_pass_rate_min")
        and check_ok(descriptor, "missing_source_text_files_max"),
        "descriptor checks include low-support consolidation, quality, and source-text coverage assertions",
    )
    add_check(
        "m23_descriptor_registry_counts_min",
        descriptor_keys_support >= args.min_descriptor_keys_with_support
        and descriptor_keys_evidence >= args.min_descriptor_keys_with_support,
        (
            f"keys_with_support={descriptor_keys_support} keys_with_evidence={descriptor_keys_evidence} "
            f"min={args.min_descriptor_keys_with_support}"
        ),
    )
    add_check("m23_descriptor_coverage_report_ok", as_bool(descriptor_coverage.get("ok"), False), f"coverage_ok={as_bool(descriptor_coverage.get('ok'), False)}")
    add_check(
        "m23_descriptor_coverage_depth_thresholds",
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
        "m23_descriptor_coverage_checks_present",
        check_ok(descriptor_coverage, "style_keys_supported_min")
        and check_ok(descriptor_coverage, "culture_keys_supported_min")
        and check_ok(descriptor_coverage, "files_with_cultural_depth_min")
        and check_ok(descriptor_coverage, "files_with_combined_depth_min")
        and check_ok(descriptor_coverage, "keys_with_evidence_min"),
        "coverage checks include style/culture/cultural-depth/combined-depth/evidence thresholds",
    )

    add_check("m23_validator_baseline_ok", as_bool(validator_baseline.get("ok"), False), f"validator_baseline_ok={as_bool(validator_baseline.get('ok'), False)}")
    add_check("m23_validator_current_ok", as_bool(validator_current.get("ok"), False), f"validator_current_ok={as_bool(validator_current.get('ok'), False)}")
    add_check(
        "m23_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m23_validator_candidate_mapping_complete",
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
        "m23_validator_rule_family_min",
        validator_alignment_rule_count >= args.min_alignment_rules
        and validator_coherence_rule_count >= args.min_coherence_rules,
        (
            f"alignment_rules={validator_alignment_rule_count} min_alignment={args.min_alignment_rules} "
            f"coherence_rules={validator_coherence_rule_count} min_coherence={args.min_coherence_rules}"
        ),
    )
    add_check(
        "m23_validator_applicability_ok",
        check_ok(validator_current, "all_rules_have_applicability")
        and check_ok(validator_current, "source_grounded_applicability_min")
        and validator_total_applicable >= args.min_source_grounded_applicable
        and validator_coherence_applicable >= args.min_coherence_applicable,
        (
            f"all_rules_have_applicability={check_ok(validator_current, 'all_rules_have_applicability')} "
            f"source_grounded_applicability={validator_total_applicable} min={args.min_source_grounded_applicable} "
            f"coherence_applicability={validator_coherence_applicable} min={args.min_coherence_applicable}"
        ),
    )
    add_check(
        "m23_validator_coherence_rules_added",
        check_ok(validator_baseline, "m23_coherence_rules_added")
        and check_ok(validator_current, "m23_coherence_rules_added"),
        "m23 coherence rule-addition check passes for baseline/current",
    )
    add_check(
        "m23_validator_input_invariants",
        validator_baseline_corpus == required_source_dir
        and validator_current_corpus == required_descriptor_out_dir
        and validator_baseline_base_report == required_base_validator_report
        and validator_current_base_report == required_base_validator_report
        and validator_baseline_descriptor_report == required_descriptor_report_path
        and validator_current_descriptor_report == required_descriptor_report_path
        and validator_baseline_source_text_dirs == required_source_text_dirs
        and validator_current_source_text_dirs == required_source_text_dirs,
        (
            f"baseline_corpus={validator_baseline_corpus} current_corpus={validator_current_corpus} "
            f"baseline_base_report={validator_baseline_base_report} current_base_report={validator_current_base_report} "
            f"baseline_descriptor_report={validator_baseline_descriptor_report} "
            f"current_descriptor_report={validator_current_descriptor_report} "
            f"baseline_source_text_dirs={validator_baseline_source_text_dirs} "
            f"current_source_text_dirs={validator_current_source_text_dirs}"
        ),
    )

    add_check("m23_burndown_ok", as_bool(burndown.get("ok"), False), f"burndown_ok={as_bool(burndown.get('ok'), False)}")
    add_check(
        "m23_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m23_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m23_burndown_input_invariants",
        burndown_baseline_report == required_baseline_report and burndown_current_report == required_current_report,
        (
            f"burndown_baseline_report={burndown_baseline_report} required_baseline={required_baseline_report} "
            f"burndown_current_report={burndown_current_report} required_current={required_current_report}"
        ),
    )

    add_check(
        "m23_make_target_invariants",
        required_source_dir in m23_descriptor_block
        and required_descriptor_out_dir in m23_descriptor_block
        and required_baseline_coverage_report in m23_descriptor_block
        and required_source_dir in m23_validator_block
        and required_descriptor_out_dir in m23_validator_block
        and required_base_validator_report in m23_validator_block
        and required_descriptor_report_path in m23_validator_block
        and required_baseline_report in m23_validator_block
        and required_current_report in m23_validator_block,
        "M23 make targets reference required dirs, reports, and baseline/current stage paths",
    )
    add_check(
        "make_ci_wires_m23_governance",
        "m23-pipeline-governance-check" in ci_line,
        "ci target includes m23-pipeline-governance-check",
    )
    add_check(
        "make_ci_keeps_m22_governance",
        "m22-pipeline-governance-check" in ci_line,
        "ci target retains m22-pipeline-governance-check",
    )
    add_check(
        "make_m23_targets_exist",
        bool(m23_descriptor_block.strip()) and bool(m23_validator_block.strip()) and bool(m23_governance_block.strip()),
        "m23 descriptor/validator/governance target blocks exist",
    )
    add_check(
        "program_plan_mentions_prg231_outcome",
        "M23 execution outcome (PRG-231)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-231 execution outcome",
    )
    add_check(
        "program_plan_mentions_prg232_outcome",
        "M23 execution outcome (PRG-232)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-232 execution outcome",
    )
    add_check(
        "program_plan_mentions_prg233_outcome",
        "M23 execution outcome (PRG-233)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-233 execution outcome",
    )
    add_check(
        "submission_doc_mentions_m23_release",
        "m23-pipeline-governance-check" in submission_text
        and "out/m23_pipeline_governance.json" in submission_text,
        "SUBMISSION.md includes M23 release command and governance artifact",
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
            "descriptorReport": str(descriptor_path),
            "descriptorRegistryReport": str(descriptor_registry_path),
            "descriptorCoverageReport": str(descriptor_coverage_path),
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
            "requiredBaselineCoverageReport": required_baseline_coverage_report,
            "requiredBaseValidatorReport": required_base_validator_report,
            "requiredDescriptorReportPath": required_descriptor_report_path,
            "requiredSourceTextDirs": required_source_text_dirs,
            "requiredBaselineReport": required_baseline_report,
            "requiredCurrentReport": required_current_report,
            "minTotalFiles": args.min_total_files,
            "minDescriptorFilesUpdated": args.min_descriptor_files_updated,
            "minSourceGroundedAdditions": args.min_source_grounded_additions,
            "minLowSupportKeys": args.min_low_support_keys,
            "minLowSupportKeysWithGrowth": args.min_low_support_keys_with_growth,
            "minDescriptorKeysWithSupport": args.min_descriptor_keys_with_support,
            "minStyleKeysWithSupport": args.min_style_keys_with_support,
            "minCultureKeysWithSupport": args.min_culture_keys_with_support,
            "minFilesWithCulturalDepth": args.min_files_with_cultural_depth,
            "minFilesWithCombinedDepth": args.min_files_with_combined_depth,
            "minExpandedRules": args.min_expanded_rules,
            "minAlignmentRules": args.min_alignment_rules,
            "minCoherenceRules": args.min_coherence_rules,
            "minSourceGroundedApplicable": args.min_source_grounded_applicable,
            "minCoherenceApplicable": args.min_coherence_applicable,
            "minReductionRatio": args.min_reduction_ratio,
            "maxFailureFileRatio": args.max_failure_file_ratio,
            "minDecisionCount": args.min_decision_count,
            "minAssumptionCount": args.min_assumption_count,
            "minRiskCount": args.min_risk_count,
        },
        "metrics": {
            "descriptorSourceFiles": descriptor_source,
            "descriptorProcessedFiles": descriptor_processed,
            "descriptorFilesUpdated": descriptor_files_updated,
            "sourceGroundedAdditions": source_grounded_additions,
            "descriptorDoctorPassRate": round(descriptor_doctor_ratio, 6),
            "descriptorGeoPassRate": round(descriptor_geo_ratio, 6),
            "lowSupportKeyCount": low_support_key_count,
            "lowSupportKeysWithGrowth": low_support_keys_with_growth,
            "lowSupportAverageRatioBefore": round(low_support_before_ratio, 6),
            "lowSupportAverageRatioAfter": round(low_support_after_ratio, 6),
            "lowSupportAdditions": low_support_additions,
            "descriptorKeysWithSupport": descriptor_keys_support,
            "descriptorKeysWithEvidence": descriptor_keys_evidence,
            "styleKeysWithSupport": style_keys_support,
            "cultureKeysWithSupport": culture_keys_support,
            "filesWithCulturalDepth": files_with_cultural_depth,
            "filesWithCombinedDepth": files_with_combined_depth,
            "validatorSourceFiles": validator_source,
            "validatorProcessedFiles": validator_processed,
            "validatorRuleCount": validator_rule_count,
            "validatorAlignmentRuleCount": validator_alignment_rule_count,
            "validatorCoherenceRuleCount": validator_coherence_rule_count,
            "validatorCandidateKeys": validator_candidate_keys,
            "validatorMappedCandidateKeys": validator_mapped_candidate_keys,
            "validatorMissingCandidateKeys": missing_candidate_keys,
            "validatorCoverageRatio": round(validator_mapping_ratio, 6),
            "validatorSourceGroundedApplicable": validator_total_applicable,
            "validatorCoherenceApplicable": validator_coherence_applicable,
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

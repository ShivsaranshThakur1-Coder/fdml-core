#!/usr/bin/env python3
"""Governance gate for M24 residual-closure and descriptor-completion adoption."""

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
            "Validate M24 residual-closure plus descriptor-completion pipeline and emit "
            "decision/assumption/risk ledgers."
        )
    )
    ap.add_argument("--residual-closure-report", required=True, help="path to M24 residual closure report")
    ap.add_argument("--descriptor-report", required=True, help="path to M24 descriptor completion report")
    ap.add_argument("--descriptor-registry-report", required=True, help="path to M24 descriptor registry report")
    ap.add_argument("--descriptor-coverage-report", required=True, help="path to M24 descriptor coverage report")
    ap.add_argument("--validator-baseline-report", required=True, help="path to M24 baseline validator report")
    ap.add_argument("--validator-current-report", required=True, help="path to M24 current validator report")
    ap.add_argument("--burndown-report", required=True, help="path to M24 validator burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md", help="path to submission doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m24-pipeline-governance", help="report label")

    ap.add_argument(
        "--required-source-dir",
        default="out/m23_descriptor_consolidation/run1",
        help="required canonical baseline corpus dir for M24 residual closure and validator baseline",
    )
    ap.add_argument(
        "--required-residual-out-dir",
        default="out/m24_residual_failure_closure/run1",
        help="required residual-closure output dir",
    )
    ap.add_argument(
        "--required-descriptor-out-dir",
        default="out/m24_descriptor_completion/run1",
        help="required descriptor-completion output dir",
    )
    ap.add_argument(
        "--required-residual-reference-report",
        default="out/m23_validator_expansion_report.json",
        help="required M23 validator report referenced by M24 residual closure",
    )
    ap.add_argument(
        "--required-residual-report-path",
        default="out/m24_residual_failure_closure_report.json",
        help="required residual closure report path used by descriptor completion",
    )
    ap.add_argument(
        "--required-base-validator-report",
        default="out/m22_validator_expansion_report.json",
        help="required M22 validator report used as mapping baseline in M24 validator runs",
    )
    ap.add_argument(
        "--required-validator-descriptor-report-path",
        default="out/m23_descriptor_consolidation_report.json",
        help="required descriptor report path used by M24 validator runs",
    )
    ap.add_argument(
        "--required-source-text-dir",
        action="append",
        default=[],
        help="required source text dirs used by residual/descriptor/validator steps (repeatable)",
    )
    ap.add_argument(
        "--required-baseline-report",
        default="out/m24_validator_expansion_baseline_report.json",
        help="required M24 baseline validator report path used by burndown",
    )
    ap.add_argument(
        "--required-current-report",
        default="out/m24_validator_expansion_report.json",
        help="required M24 current validator report path used by burndown",
    )

    ap.add_argument("--min-total-files", type=int, default=100, help="minimum source files")
    ap.add_argument("--min-residual-targeted-files", type=int, default=5)
    ap.add_argument("--min-residual-files-updated", type=int, default=5)
    ap.add_argument("--min-residual-source-grounded-additions", type=int, default=6)
    ap.add_argument("--min-descriptor-targeted-files", type=int, default=5)
    ap.add_argument("--min-descriptor-files-updated", type=int, default=5)
    ap.add_argument("--min-descriptor-source-grounded-additions", type=int, default=5)
    ap.add_argument("--min-low-support-cultural-keys", type=int, default=2)
    ap.add_argument("--min-low-support-keys-with-growth", type=int, default=2)
    ap.add_argument("--min-residual-focus-files", type=int, default=5)
    ap.add_argument("--min-descriptor-keys-with-support", type=int, default=18)
    ap.add_argument("--min-style-keys-with-support", type=int, default=8)
    ap.add_argument("--min-culture-keys-with-support", type=int, default=6)
    ap.add_argument("--min-files-with-cultural-depth", type=int, default=109)
    ap.add_argument("--min-files-with-combined-depth", type=int, default=105)
    ap.add_argument("--min-expanded-rules", type=int, default=20)
    ap.add_argument("--min-alignment-rules", type=int, default=16)
    ap.add_argument("--min-coherence-rules", type=int, default=4)
    ap.add_argument("--min-source-grounded-applicable", type=int, default=300)
    ap.add_argument("--min-coherence-applicable", type=int, default=100)
    ap.add_argument("--min-reduction-ratio", type=float, default=1.0)
    ap.add_argument("--max-failure-file-ratio", type=float, default=0.0)
    ap.add_argument("--min-decision-count", type=int, default=5)
    ap.add_argument("--min-assumption-count", type=int, default=5)
    ap.add_argument("--min-risk-count", type=int, default=5)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m24_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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


def build_decision_registry(
    required_source_dir: str,
    required_residual_out_dir: str,
    required_descriptor_out_dir: str,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M24-DEC-001",
            "decision": "Keep one canonical M24 baseline/current validator path",
            "chosenOption": f"use {required_source_dir} baseline and {required_residual_out_dir} current for M24 validator pass",
            "alternativesConsidered": [
                "split validator baseline/current across separate corpora",
                "re-run validator on descriptor-completion output for K1 evidence",
            ],
            "tradeoffs": [
                "pro: deterministic and comparable residual-zeroing metric",
                "con: validator KPI remains anchored to residual-closure stage rather than descriptor-completion stage",
            ],
            "reversalCondition": "if validator stage changes, update baseline/current invariants and burndown references atomically",
        },
        {
            "id": "M24-DEC-002",
            "decision": "Preserve M24 descriptor completion as explicit second-stage artifact",
            "chosenOption": f"descriptor completion output fixed at {required_descriptor_out_dir}",
            "alternativesConsidered": [
                "in-place modifications on residual-closure corpus",
                "combine closure and completion into one pass artifact",
            ],
            "tradeoffs": [
                "pro: clear auditable handoff between zero-failure closure and descriptor saturation uplift",
                "con: adds one additional stage artifact to govern",
            ],
            "reversalCondition": "if stage is collapsed, retain equivalent before/after evidence in one deterministic report",
        },
        {
            "id": "M24-DEC-003",
            "decision": "Enforce full strict-quality retention throughout M24",
            "chosenOption": "require doctor --strict and validate-geo pass rates at 1.0 on both M24 stages",
            "alternativesConsidered": [
                "allow partial pass-rate thresholds",
                "check strict quality only at milestone closeout",
            ],
            "tradeoffs": [
                "pro: no hidden quality regressions during residual zeroing and descriptor completion",
                "con: tighter gate can fail on minor unrelated fixture drift",
            ],
            "reversalCondition": "if corpus scale changes, update strict thresholds only with explicit rationale",
        },
        {
            "id": "M24-DEC-004",
            "decision": "Promote M24 governance gate to CI before milestone closeout",
            "chosenOption": "wire m24-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "manual governance execution",
                "doc-only governance assertions",
            ],
            "tradeoffs": [
                "pro: anti-drift enforcement on every CI run",
                "con: additional CI runtime",
            ],
            "reversalCondition": "if CI budget tightens, split runtime but keep governance fail-fast",
        },
        {
            "id": "M24-DEC-005",
            "decision": "Activate final productization queue at M24 governance closeout",
            "chosenOption": "close M24 and move active milestone to final productization queue from clean state",
            "alternativesConsidered": [
                "defer queue activation to a separate closeout item",
                "keep M24 active and append more K3 tasks",
            ],
            "tradeoffs": [
                "pro: unblocks final finish-work immediately after governance pass",
                "con: requires synchronized plan/work/docs state update in same step",
            ],
            "reversalCondition": "if closeout blockers appear, keep M24 active and restore planned status for activation item",
        },
    ]


def build_assumption_registry(
    required_source_dir: str,
    required_residual_out_dir: str,
    required_descriptor_out_dir: str,
    min_reduction_ratio: float,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M24-ASM-001",
            "assumption": "M23 descriptor-consolidation corpus remains canonical M24 baseline",
            "confidence": 0.9,
            "verificationPlan": f"enforce residual stage and baseline validator corpus reference {required_source_dir}",
            "invalidationSignal": "M24 residual stage reads from a different baseline corpus path",
        },
        {
            "id": "M24-ASM-002",
            "assumption": "M24 residual-closure output remains canonical validator current path",
            "confidence": 0.9,
            "verificationPlan": f"enforce validator current corpus reference {required_residual_out_dir}",
            "invalidationSignal": "M24 validator current report points outside residual closure output",
        },
        {
            "id": "M24-ASM-003",
            "assumption": "M24 descriptor completion keeps low-support cultural uplift source-grounded",
            "confidence": 0.85,
            "verificationPlan": (
                "require low-support key discovery, growth-key thresholds, non-decreasing support ratios, "
                "and residual growth gap reduction"
            ),
            "invalidationSignal": "descriptor completion passes with no low-support growth or residual-gap reduction",
        },
        {
            "id": "M24-ASM-004",
            "assumption": "M24 burndown remains strict zero-failure proof",
            "confidence": 0.9,
            "verificationPlan": f"require failure reduction ratio >= {min_reduction_ratio:.2f} and failure-file ratio <= threshold",
            "invalidationSignal": "current failures or failure-file ratio exceed strict M24 threshold",
        },
        {
            "id": "M24-ASM-005",
            "assumption": "Program and submission docs remain synchronized with M24 outputs",
            "confidence": 0.75,
            "verificationPlan": "require PRG-241/PRG-242/PRG-243 outcomes in PROGRAM_PLAN and M24 command/artifact references in SUBMISSION",
            "invalidationSignal": "governance passes while release docs omit M24 references",
        },
        {
            "id": "M24-ASM-006",
            "assumption": "Final productization queue activation occurs only after clean governance pass",
            "confidence": 0.85,
            "verificationPlan": "activate next milestone only when all governance checks pass and approval gate is green",
            "invalidationSignal": "active milestone changes while governance gate is failing",
        },
    ]


def build_risk_ledger(
    residual_files_updated: int,
    residual_additions: int,
    descriptor_files_updated: int,
    descriptor_additions: int,
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
            "id": "M24-RSK-001",
            "risk": "Residual closure can overfit a narrow failure set",
            "severity": "medium",
            "likelihood": "medium",
            "signal": (
                f"residual_files_updated={residual_files_updated} residual_additions={residual_additions} "
                f"baseline_failures={baseline_failures} current_failures={current_failures}"
            ),
            "mitigation": "retain canonical baseline/current validator reports and strict zero-failure burndown checks",
            "owner": "validator",
        },
        {
            "id": "M24-RSK-002",
            "risk": "Low-support cultural families may remain shallow after initial saturation pass",
            "severity": "high",
            "likelihood": "medium",
            "signal": (
                f"descriptor_files_updated={descriptor_files_updated} descriptor_additions={descriptor_additions} "
                f"low_support_keys={low_support_key_count} growth_keys={low_support_keys_with_growth} "
                f"ratio={low_support_before_ratio:.6f}->{low_support_after_ratio:.6f}"
            ),
            "mitigation": "carry low-support families into final productization queue with deterministic source-grounded uplift passes",
            "owner": "descriptor",
        },
        {
            "id": "M24-RSK-003",
            "risk": "Mapping/applicability drift could hide validator regressions",
            "severity": "high",
            "likelihood": "low",
            "signal": (
                f"validator_rules={validator_rule_count} alignment_rules={alignment_rule_count} "
                f"coherence_rules={coherence_rule_count} source_grounded_applicable={validator_total_applicable} "
                f"coherence_applicable={coherence_applicable} missing_candidate_keys={missing_candidate_keys}"
            ),
            "mitigation": "fail governance on mapping completeness and applicability thresholds",
            "owner": "pipeline",
        },
        {
            "id": "M24-RSK-004",
            "risk": "CI may drift from current governance expectations",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "ci target missing m24-pipeline-governance-check",
            "mitigation": "gate on CI wiring and target-block invariants",
            "owner": "ci",
        },
        {
            "id": "M24-RSK-005",
            "risk": "Release evidence can become stale after milestone transition",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "submission/program docs omit M24 governance command/artifact references",
            "mitigation": "enforce release-doc synchronization checks at governance time",
            "owner": "release",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_residual_targeted_files < 0:
        return fail("--min-residual-targeted-files must be >= 0")
    if args.min_residual_files_updated < 0:
        return fail("--min-residual-files-updated must be >= 0")
    if args.min_residual_source_grounded_additions < 0:
        return fail("--min-residual-source-grounded-additions must be >= 0")
    if args.min_descriptor_targeted_files < 0:
        return fail("--min-descriptor-targeted-files must be >= 0")
    if args.min_descriptor_files_updated < 0:
        return fail("--min-descriptor-files-updated must be >= 0")
    if args.min_descriptor_source_grounded_additions < 0:
        return fail("--min-descriptor-source-grounded-additions must be >= 0")
    if args.min_low_support_cultural_keys <= 0:
        return fail("--min-low-support-cultural-keys must be > 0")
    if args.min_low_support_keys_with_growth < 0:
        return fail("--min-low-support-keys-with-growth must be >= 0")
    if args.min_residual_focus_files < 0:
        return fail("--min-residual-focus-files must be >= 0")
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

    residual_path = Path(args.residual_closure_report)
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
        (residual_path, "--residual-closure-report"),
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
        residual = load_json(residual_path)
        descriptor = load_json(descriptor_path)
        descriptor_registry = load_json(descriptor_registry_path)
        descriptor_coverage = load_json(descriptor_coverage_path)
        validator_baseline = load_json(validator_baseline_path)
        validator_current = load_json(validator_current_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_source_dir = normalize_path(str(args.required_source_dir))
    required_residual_out_dir = normalize_path(str(args.required_residual_out_dir))
    required_descriptor_out_dir = normalize_path(str(args.required_descriptor_out_dir))
    required_residual_reference_report = normalize_path(str(args.required_residual_reference_report))
    required_residual_report_path = normalize_path(str(args.required_residual_report_path))
    required_base_validator_report = normalize_path(str(args.required_base_validator_report))
    required_validator_descriptor_report_path = normalize_path(str(args.required_validator_descriptor_report_path))
    required_source_text_dirs = normalize_paths(
        args.required_source_text_dir or ["out/acquired_sources", "out/acquired_sources_nonwiki"]
    )
    required_baseline_report = normalize_path(str(args.required_baseline_report))
    required_current_report = normalize_path(str(args.required_current_report))

    residual_inputs = as_dict(residual.get("inputs"))
    residual_source_dir = normalize_path(str(residual_inputs.get("sourceDir") or ""))
    residual_reference_report = normalize_path(str(residual_inputs.get("residualReport") or ""))
    residual_source_text_dirs = normalize_paths(as_list(residual_inputs.get("sourceTextDirs")))
    residual_out_dir = normalize_path(str(residual_inputs.get("outDir") or ""))
    residual_totals = as_dict(residual.get("totals"))
    residual_source = as_int(residual_totals.get("sourceFiles"), 0)
    residual_processed = as_int(residual_totals.get("processedFiles"), 0)
    residual_targeted_files = as_int(residual_totals.get("targetedFiles"), 0)
    residual_files_updated = as_int(residual_totals.get("filesUpdated"), 0)
    residual_additions = as_int(residual_totals.get("sourceGroundedAdditions"), 0)
    residual_unresolved = as_int(residual_totals.get("unresolvedTargetRules"), 0)
    residual_unsupported = as_int(residual_totals.get("unsupportedRuleCount"), 0)
    residual_doctor_ratio = clamp01(as_float(residual_totals.get("doctorPassRate"), 0.0))
    residual_geo_ratio = clamp01(as_float(residual_totals.get("geoPassRate"), 0.0))

    descriptor_inputs = as_dict(descriptor.get("inputs"))
    descriptor_source_dir = normalize_path(str(descriptor_inputs.get("sourceDir") or ""))
    descriptor_residual_report = normalize_path(str(descriptor_inputs.get("residualClosureReport") or ""))
    descriptor_source_text_dirs = normalize_paths(as_list(descriptor_inputs.get("sourceTextDirs")))
    descriptor_out_dir = normalize_path(str(descriptor_inputs.get("outDir") or ""))
    descriptor_totals = as_dict(descriptor.get("totals"))
    descriptor_source = as_int(descriptor_totals.get("sourceFiles"), 0)
    descriptor_processed = as_int(descriptor_totals.get("processedFiles"), 0)
    descriptor_residual_focus_file_count = as_int(descriptor_totals.get("residualFocusFileCount"), 0)
    descriptor_targeted_files = as_int(descriptor_totals.get("targetedFiles"), 0)
    descriptor_files_updated = as_int(descriptor_totals.get("filesUpdated"), 0)
    descriptor_additions = as_int(descriptor_totals.get("sourceGroundedAdditions"), 0)
    descriptor_low_support_keys = as_int(descriptor_totals.get("lowSupportCulturalKeyCount"), 0)
    descriptor_low_support_growth = as_int(descriptor_totals.get("lowSupportKeysWithGrowth"), 0)
    low_support_before_ratio = clamp01(as_float(descriptor_totals.get("lowSupportAverageRatioBefore"), 0.0))
    low_support_after_ratio = clamp01(as_float(descriptor_totals.get("lowSupportAverageRatioAfter"), 0.0))
    residual_growth_before = as_int(descriptor_totals.get("residualPotentialGrowthBefore"), 0)
    residual_growth_after = as_int(descriptor_totals.get("residualPotentialGrowthAfter"), 0)
    residual_focus_covered_before = as_int(descriptor_totals.get("residualFocusCoveredBeforeFiles"), 0)
    residual_focus_covered_after = as_int(descriptor_totals.get("residualFocusCoveredAfterFiles"), 0)
    descriptor_doctor_ratio = clamp01(as_float(descriptor_totals.get("doctorPassRate"), 0.0))
    descriptor_geo_ratio = clamp01(as_float(descriptor_totals.get("geoPassRate"), 0.0))
    descriptor_support = as_dict(descriptor.get("descriptorSupport"))
    low_support_keys_list = [str(v).strip() for v in as_list(descriptor_support.get("lowSupportKeys")) if str(v).strip()]

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
    m24_residual_block = extract_make_target_block(make_text, "m24-residual-failure-closure-check")
    m24_descriptor_block = extract_make_target_block(make_text, "m24-descriptor-completion-check")
    m24_governance_block = extract_make_target_block(make_text, "m24-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")
    submission_text = submission_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(required_source_dir, required_residual_out_dir, required_descriptor_out_dir)
    assumptions = build_assumption_registry(
        required_source_dir,
        required_residual_out_dir,
        required_descriptor_out_dir,
        args.min_reduction_ratio,
    )
    risks = build_risk_ledger(
        residual_files_updated,
        residual_additions,
        descriptor_files_updated,
        descriptor_additions,
        descriptor_low_support_keys,
        descriptor_low_support_growth,
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

    add_check("m24_residual_report_ok", as_bool(residual.get("ok"), False), f"residual_ok={as_bool(residual.get('ok'), False)}")
    add_check(
        "m24_residual_counts_min",
        residual_source >= args.min_total_files
        and residual_processed >= args.min_total_files
        and residual_targeted_files >= args.min_residual_targeted_files
        and residual_files_updated >= args.min_residual_files_updated,
        (
            f"source={residual_source} processed={residual_processed} targeted={residual_targeted_files} "
            f"updated={residual_files_updated} min_targeted={args.min_residual_targeted_files} "
            f"min_updated={args.min_residual_files_updated}"
        ),
    )
    add_check(
        "m24_residual_source_grounded_additions_min",
        residual_additions >= args.min_residual_source_grounded_additions,
        f"residual_additions={residual_additions} min={args.min_residual_source_grounded_additions}",
    )
    add_check(
        "m24_residual_integrity",
        residual_unresolved == 0 and residual_unsupported == 0,
        f"unresolved={residual_unresolved} unsupported={residual_unsupported}",
    )
    add_check(
        "m24_residual_quality",
        residual_doctor_ratio >= 0.999 and residual_geo_ratio >= 0.999,
        f"doctor_ratio={residual_doctor_ratio:.4f} geo_ratio={residual_geo_ratio:.4f}",
    )
    add_check(
        "m24_residual_input_invariants",
        residual_source_dir == required_source_dir
        and residual_out_dir == required_residual_out_dir
        and residual_reference_report == required_residual_reference_report
        and residual_source_text_dirs == required_source_text_dirs,
        (
            f"source_dir={residual_source_dir} out_dir={residual_out_dir} residual_report={residual_reference_report} "
            f"source_text_dirs={residual_source_text_dirs}"
        ),
    )
    add_check(
        "m24_residual_checks_present",
        check_ok(residual, "source_files_min")
        and check_ok(residual, "residual_targets_detected")
        and check_ok(residual, "targeted_files_min")
        and check_ok(residual, "files_updated_min")
        and check_ok(residual, "source_grounded_additions_min")
        and check_ok(residual, "unresolved_target_rules_zero")
        and check_ok(residual, "unsupported_rule_count_zero")
        and check_ok(residual, "doctor_pass_rate_min")
        and check_ok(residual, "geo_pass_rate_min")
        and check_ok(residual, "missing_source_text_files_max"),
        "residual checks include target detection, integrity, quality, and source-text coverage assertions",
    )

    add_check("m24_descriptor_report_ok", as_bool(descriptor.get("ok"), False), f"descriptor_ok={as_bool(descriptor.get('ok'), False)}")
    add_check(
        "m24_descriptor_counts_min",
        descriptor_source >= args.min_total_files
        and descriptor_processed >= args.min_total_files
        and descriptor_residual_focus_file_count >= args.min_residual_focus_files
        and descriptor_targeted_files >= args.min_descriptor_targeted_files
        and descriptor_files_updated >= args.min_descriptor_files_updated,
        (
            f"source={descriptor_source} processed={descriptor_processed} residual_focus={descriptor_residual_focus_file_count} "
            f"targeted={descriptor_targeted_files} updated={descriptor_files_updated} "
            f"min_focus={args.min_residual_focus_files} min_targeted={args.min_descriptor_targeted_files} "
            f"min_updated={args.min_descriptor_files_updated}"
        ),
    )
    add_check(
        "m24_descriptor_source_grounded_additions_min",
        descriptor_additions >= args.min_descriptor_source_grounded_additions,
        f"descriptor_additions={descriptor_additions} min={args.min_descriptor_source_grounded_additions}",
    )
    add_check(
        "m24_descriptor_low_support_thresholds",
        descriptor_low_support_keys >= args.min_low_support_cultural_keys
        and descriptor_low_support_growth >= args.min_low_support_keys_with_growth
        and descriptor_additions > 0
        and len(low_support_keys_list) >= args.min_low_support_cultural_keys,
        (
            f"low_support_keys={descriptor_low_support_keys} min_keys={args.min_low_support_cultural_keys} "
            f"growth_keys={descriptor_low_support_growth} min_growth={args.min_low_support_keys_with_growth} "
            f"low_support_keys_list={len(low_support_keys_list)} additions={descriptor_additions}"
        ),
    )
    add_check(
        "m24_descriptor_low_support_ratio_increase",
        low_support_after_ratio >= low_support_before_ratio,
        f"low_support_avg_ratio={low_support_before_ratio:.6f}->{low_support_after_ratio:.6f}",
    )
    add_check(
        "m24_descriptor_residual_growth_gap_reduced",
        residual_growth_after <= residual_growth_before,
        f"residual_growth_gap={residual_growth_before}->{residual_growth_after}",
    )
    add_check(
        "m24_descriptor_focus_non_regression",
        residual_focus_covered_after >= residual_focus_covered_before,
        f"residual_focus_covered={residual_focus_covered_before}->{residual_focus_covered_after}",
    )
    add_check(
        "m24_descriptor_quality",
        descriptor_doctor_ratio >= 0.999 and descriptor_geo_ratio >= 0.999,
        f"doctor_ratio={descriptor_doctor_ratio:.4f} geo_ratio={descriptor_geo_ratio:.4f}",
    )
    add_check(
        "m24_descriptor_input_invariants",
        descriptor_source_dir == required_residual_out_dir
        and descriptor_residual_report == required_residual_report_path
        and descriptor_out_dir == required_descriptor_out_dir
        and descriptor_source_text_dirs == required_source_text_dirs
        and descriptor_registry_input_dir == required_descriptor_out_dir
        and descriptor_coverage_input_dir == required_descriptor_out_dir,
        (
            f"source_dir={descriptor_source_dir} residual_report={descriptor_residual_report} "
            f"out_dir={descriptor_out_dir} registry_input={descriptor_registry_input_dir} "
            f"coverage_input={descriptor_coverage_input_dir} source_text_dirs={descriptor_source_text_dirs}"
        ),
    )
    add_check(
        "m24_descriptor_checks_present",
        check_ok(descriptor, "source_files_min")
        and check_ok(descriptor, "residual_focus_files_min")
        and check_ok(descriptor, "low_support_cultural_keys_min")
        and check_ok(descriptor, "targeted_files_min")
        and check_ok(descriptor, "files_updated_min")
        and check_ok(descriptor, "source_grounded_additions_min")
        and check_ok(descriptor, "low_support_keys_with_growth_min")
        and check_ok(descriptor, "low_support_average_ratio_increase")
        and check_ok(descriptor, "residual_growth_gap_reduced")
        and check_ok(descriptor, "residual_focus_non_regression")
        and check_ok(descriptor, "doctor_pass_rate_min")
        and check_ok(descriptor, "geo_pass_rate_min")
        and check_ok(descriptor, "missing_source_text_files_max"),
        "descriptor checks include low-support growth, residual-gap reduction, and quality assertions",
    )
    add_check(
        "m24_descriptor_registry_counts_min",
        descriptor_keys_support >= args.min_descriptor_keys_with_support
        and descriptor_keys_evidence >= args.min_descriptor_keys_with_support,
        (
            f"keys_with_support={descriptor_keys_support} keys_with_evidence={descriptor_keys_evidence} "
            f"min={args.min_descriptor_keys_with_support}"
        ),
    )
    add_check("m24_descriptor_coverage_report_ok", as_bool(descriptor_coverage.get("ok"), False), f"coverage_ok={as_bool(descriptor_coverage.get('ok'), False)}")
    add_check(
        "m24_descriptor_coverage_depth_thresholds",
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
        "m24_descriptor_coverage_checks_present",
        check_ok(descriptor_coverage, "style_keys_supported_min")
        and check_ok(descriptor_coverage, "culture_keys_supported_min")
        and check_ok(descriptor_coverage, "files_with_cultural_depth_min")
        and check_ok(descriptor_coverage, "files_with_combined_depth_min")
        and check_ok(descriptor_coverage, "keys_with_evidence_min"),
        "coverage checks include style/culture/cultural-depth/combined-depth/evidence thresholds",
    )

    add_check("m24_validator_baseline_ok", as_bool(validator_baseline.get("ok"), False), f"validator_baseline_ok={as_bool(validator_baseline.get('ok'), False)}")
    add_check("m24_validator_current_ok", as_bool(validator_current.get("ok"), False), f"validator_current_ok={as_bool(validator_current.get('ok'), False)}")
    add_check(
        "m24_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m24_validator_candidate_mapping_complete",
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
        "m24_validator_rule_family_min",
        validator_alignment_rule_count >= args.min_alignment_rules
        and validator_coherence_rule_count >= args.min_coherence_rules,
        (
            f"alignment_rules={validator_alignment_rule_count} min_alignment={args.min_alignment_rules} "
            f"coherence_rules={validator_coherence_rule_count} min_coherence={args.min_coherence_rules}"
        ),
    )
    add_check(
        "m24_validator_applicability_ok",
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
        "m24_validator_coherence_rules_added",
        check_ok(validator_baseline, "m23_coherence_rules_added")
        and check_ok(validator_current, "m23_coherence_rules_added"),
        "m24 validator baseline/current retain M23 coherence rule set and checks",
    )
    add_check(
        "m24_validator_input_invariants",
        validator_baseline_corpus == required_source_dir
        and validator_current_corpus == required_residual_out_dir
        and validator_baseline_base_report == required_base_validator_report
        and validator_current_base_report == required_base_validator_report
        and validator_baseline_descriptor_report == required_validator_descriptor_report_path
        and validator_current_descriptor_report == required_validator_descriptor_report_path
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

    add_check("m24_burndown_ok", as_bool(burndown.get("ok"), False), f"burndown_ok={as_bool(burndown.get('ok'), False)}")
    add_check(
        "m24_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m24_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m24_burndown_input_invariants",
        burndown_baseline_report == required_baseline_report and burndown_current_report == required_current_report,
        (
            f"burndown_baseline_report={burndown_baseline_report} required_baseline={required_baseline_report} "
            f"burndown_current_report={burndown_current_report} required_current={required_current_report}"
        ),
    )

    add_check(
        "m24_make_target_invariants",
        required_source_dir in m24_residual_block
        and required_residual_out_dir in m24_residual_block
        and required_residual_reference_report in m24_residual_block
        and required_residual_out_dir in m24_descriptor_block
        and required_descriptor_out_dir in m24_descriptor_block
        and required_residual_report_path in m24_descriptor_block
        and required_source_dir in m24_governance_block
        and required_residual_out_dir in m24_governance_block
        and required_descriptor_out_dir in m24_governance_block
        and required_baseline_report in m24_governance_block
        and required_current_report in m24_governance_block,
        "M24 make targets reference required dirs, reports, and baseline/current stage paths",
    )
    add_check(
        "make_ci_wires_m24_governance",
        "m24-pipeline-governance-check" in ci_line,
        "ci target includes m24-pipeline-governance-check",
    )
    add_check(
        "make_ci_keeps_m23_governance",
        "m23-pipeline-governance-check" in ci_line,
        "ci target retains m23-pipeline-governance-check",
    )
    add_check(
        "make_m24_targets_exist",
        bool(m24_residual_block.strip()) and bool(m24_descriptor_block.strip()) and bool(m24_governance_block.strip()),
        "m24 residual/descriptor/governance target blocks exist",
    )

    add_check(
        "program_plan_mentions_prg241_outcome",
        "M24 execution outcome (PRG-241)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-241 execution outcome",
    )
    add_check(
        "program_plan_mentions_prg242_outcome",
        "M24 execution outcome (PRG-242)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-242 execution outcome",
    )
    add_check(
        "program_plan_mentions_prg243_outcome",
        "M24 execution outcome (PRG-243)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-243 execution outcome",
    )
    add_check(
        "submission_doc_mentions_m24_release",
        "m24-pipeline-governance-check" in submission_text and "out/m24_pipeline_governance.json" in submission_text,
        "SUBMISSION.md includes M24 release command and governance artifact",
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
            "residualClosureReport": str(residual_path),
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
            "requiredResidualOutDir": required_residual_out_dir,
            "requiredDescriptorOutDir": required_descriptor_out_dir,
            "requiredResidualReferenceReport": required_residual_reference_report,
            "requiredResidualReportPath": required_residual_report_path,
            "requiredBaseValidatorReport": required_base_validator_report,
            "requiredValidatorDescriptorReportPath": required_validator_descriptor_report_path,
            "requiredSourceTextDirs": required_source_text_dirs,
            "requiredBaselineReport": required_baseline_report,
            "requiredCurrentReport": required_current_report,
            "minTotalFiles": args.min_total_files,
            "minResidualTargetedFiles": args.min_residual_targeted_files,
            "minResidualFilesUpdated": args.min_residual_files_updated,
            "minResidualSourceGroundedAdditions": args.min_residual_source_grounded_additions,
            "minDescriptorTargetedFiles": args.min_descriptor_targeted_files,
            "minDescriptorFilesUpdated": args.min_descriptor_files_updated,
            "minDescriptorSourceGroundedAdditions": args.min_descriptor_source_grounded_additions,
            "minLowSupportCulturalKeys": args.min_low_support_cultural_keys,
            "minLowSupportKeysWithGrowth": args.min_low_support_keys_with_growth,
            "minResidualFocusFiles": args.min_residual_focus_files,
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
            "residualSourceFiles": residual_source,
            "residualProcessedFiles": residual_processed,
            "residualTargetedFiles": residual_targeted_files,
            "residualFilesUpdated": residual_files_updated,
            "residualSourceGroundedAdditions": residual_additions,
            "residualUnresolvedTargetRules": residual_unresolved,
            "residualUnsupportedRuleCount": residual_unsupported,
            "residualDoctorPassRate": round(residual_doctor_ratio, 6),
            "residualGeoPassRate": round(residual_geo_ratio, 6),
            "descriptorSourceFiles": descriptor_source,
            "descriptorProcessedFiles": descriptor_processed,
            "descriptorResidualFocusFiles": descriptor_residual_focus_file_count,
            "descriptorTargetedFiles": descriptor_targeted_files,
            "descriptorFilesUpdated": descriptor_files_updated,
            "descriptorSourceGroundedAdditions": descriptor_additions,
            "descriptorLowSupportCulturalKeyCount": descriptor_low_support_keys,
            "descriptorLowSupportKeysWithGrowth": descriptor_low_support_growth,
            "descriptorLowSupportAverageRatioBefore": round(low_support_before_ratio, 6),
            "descriptorLowSupportAverageRatioAfter": round(low_support_after_ratio, 6),
            "descriptorResidualGrowthBefore": residual_growth_before,
            "descriptorResidualGrowthAfter": residual_growth_after,
            "descriptorResidualFocusCoveredBefore": residual_focus_covered_before,
            "descriptorResidualFocusCoveredAfter": residual_focus_covered_after,
            "descriptorDoctorPassRate": round(descriptor_doctor_ratio, 6),
            "descriptorGeoPassRate": round(descriptor_geo_ratio, 6),
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

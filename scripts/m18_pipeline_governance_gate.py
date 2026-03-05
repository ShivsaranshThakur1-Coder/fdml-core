#!/usr/bin/env python3
"""Governance gate for M18 realism/descriptor closure adoption."""

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
            "Validate M18 realism+descriptor uplift governance and emit "
            "decision/assumption/risk ledgers."
        )
    )
    ap.add_argument("--realism-report", required=True, help="path to M18 realism uplift report")
    ap.add_argument(
        "--descriptor-uplift-report",
        required=True,
        help="path to M18 descriptor uplift report",
    )
    ap.add_argument(
        "--descriptor-registry-report",
        required=True,
        help="path to M18 descriptor registry report",
    )
    ap.add_argument(
        "--descriptor-coverage-report",
        required=True,
        help="path to M18 descriptor coverage report",
    )
    ap.add_argument("--validator-report", required=True, help="path to M18 validator report")
    ap.add_argument("--burndown-report", required=True, help="path to M18 burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m18-pipeline-governance", help="report label")
    ap.add_argument(
        "--required-realism-source-dir",
        default="out/m14_context_specificity/run1",
        help="required source corpus dir for realism uplift",
    )
    ap.add_argument(
        "--required-realism-out-dir",
        default="out/m18_realism_uplift/run1",
        help="required output corpus dir for realism uplift",
    )
    ap.add_argument(
        "--required-descriptor-out-dir",
        default="out/m18_descriptor_uplift/run1",
        help="required output corpus dir for descriptor uplift",
    )
    ap.add_argument(
        "--required-candidate-report",
        default="out/m15_validator_candidates.json",
        help="required validator candidate ledger path",
    )
    ap.add_argument(
        "--required-baseline-report",
        default="out/m17_validator_expansion_report.json",
        help="required baseline validator report for M18 burndown",
    )
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum source files")
    ap.add_argument("--min-realism-files-updated", type=int, default=20)
    ap.add_argument("--min-descriptor-files-updated", type=int, default=16)
    ap.add_argument("--min-descriptor-keys-with-support", type=int, default=20)
    ap.add_argument("--min-style-keys-with-support", type=int, default=8)
    ap.add_argument("--min-culture-keys-with-support", type=int, default=6)
    ap.add_argument("--min-files-with-cultural-depth", type=int, default=85)
    ap.add_argument("--min-files-with-combined-depth", type=int, default=60)
    ap.add_argument("--min-expanded-rules", type=int, default=35)
    ap.add_argument("--min-reduction-ratio", type=float, default=0.50)
    ap.add_argument("--max-failure-file-ratio", type=float, default=0.30)
    ap.add_argument("--min-decision-count", type=int, default=5)
    ap.add_argument("--min-assumption-count", type=int, default=5)
    ap.add_argument("--min-risk-count", type=int, default=5)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m18_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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
    realism_source_dir: str,
    realism_out_dir: str,
    descriptor_out_dir: str,
    baseline_report: str,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M18-DEC-001",
            "decision": "Keep realism uplift on one canonical source corpus",
            "chosenOption": f"Use {realism_source_dir} as the sole realism-uplift source corpus",
            "alternativesConsidered": [
                "Run realism uplift on mixed subset paths",
                "Use per-region source paths",
            ],
            "tradeoffs": [
                "pro: single-path comparability across all files",
                "con: all realism fixes must land on canonical corpus",
            ],
            "reversalCondition": "If source corpus changes, update all M18 targets atomically",
        },
        {
            "id": "M18-DEC-002",
            "decision": "Separate staged outputs for realism and descriptor uplift",
            "chosenOption": f"Use staged dirs {realism_out_dir} then {descriptor_out_dir}",
            "alternativesConsidered": [
                "One in-place mutation directory",
                "Descriptor uplift directly on source corpus",
            ],
            "tradeoffs": [
                "pro: explicit stage boundaries and auditability",
                "con: extra artifact storage",
            ],
            "reversalCondition": "If stage boundary is removed, preserve equivalent traceability in governance report",
        },
        {
            "id": "M18-DEC-003",
            "decision": "Use fixed M17 baseline for residual-failure burndown",
            "chosenOption": f"Use {baseline_report} as the M18 burndown baseline",
            "alternativesConsidered": [
                "Dynamic baseline per run",
                "No baseline and current-only reporting",
            ],
            "tradeoffs": [
                "pro: stable residual-reduction metric",
                "con: baseline artifact must be preserved",
            ],
            "reversalCondition": "If baseline contract changes, update burndown gates and thresholds together",
        },
        {
            "id": "M18-DEC-004",
            "decision": "Promote M18 governance to CI-level gate",
            "chosenOption": "Wire m18-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "Manual governance execution",
                "Separate report checks without CI enforcement",
            ],
            "tradeoffs": [
                "pro: anti-drift enforcement on every CI run",
                "con: slight CI runtime increase",
            ],
            "reversalCondition": "If CI budget tightens, split steps but keep governance as fail-fast mandatory gate",
        },
        {
            "id": "M18-DEC-005",
            "decision": "Publish deterministic M18 governance artifact",
            "chosenOption": "Emit out/m18_pipeline_governance.json with checks and ledgers",
            "alternativesConsidered": [
                "Track governance only in narrative docs",
                "Scatter metrics across multiple outputs",
            ],
            "tradeoffs": [
                "pro: machine-readable closeout evidence",
                "con: requires schema stability",
            ],
            "reversalCondition": "If schema changes often, version fields while preserving backward compatibility",
        },
    ]


def build_assumption_registry(realism_out_dir: str, descriptor_out_dir: str, min_reduction_ratio: float) -> list[dict[str, Any]]:
    return [
        {
            "id": "M18-ASM-001",
            "assumption": "Realism uplift output remains canonical validator input",
            "confidence": 0.9,
            "verificationPlan": f"Enforce validator corpus dir equals {realism_out_dir}",
            "invalidationSignal": "validator corpus input diverges from realism output dir",
        },
        {
            "id": "M18-ASM-002",
            "assumption": "Descriptor uplift output remains canonical descriptor coverage input",
            "confidence": 0.9,
            "verificationPlan": f"Enforce descriptor registry/coverage input dir equals {descriptor_out_dir}",
            "invalidationSignal": "descriptor registry or coverage input diverges from descriptor output dir",
        },
        {
            "id": "M18-ASM-003",
            "assumption": "Candidate-mapped validator stack remains complete over full corpus",
            "confidence": 0.8,
            "verificationPlan": "Require priority mapping complete and no missing candidate keys",
            "invalidationSignal": "priority mapping check fails or missing candidate keys appear",
        },
        {
            "id": "M18-ASM-004",
            "assumption": "Residual burndown ratio remains a meaningful quality signal",
            "confidence": 0.85,
            "verificationPlan": f"Enforce reduction ratio >= {min_reduction_ratio:.2f} with failure-file cap",
            "invalidationSignal": "burndown ratio degrades under stable corpus/rule counts",
        },
        {
            "id": "M18-ASM-005",
            "assumption": "Plan narrative remains synchronized with M18 machine outputs",
            "confidence": 0.75,
            "verificationPlan": "Require PROGRAM_PLAN.md to include PRG-183 execution outcome",
            "invalidationSignal": "governance passes while PRG-183 outcome is absent in plan doc",
        },
    ]


def build_risk_ledger(
    realism_files_updated: int,
    descriptor_files_updated: int,
    files_with_cultural_depth: int,
    baseline_failures: int,
    current_failures: int,
    missing_candidate_keys: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M18-RSK-001",
            "risk": "Realism uplift may underfit unseen movement variants",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"realismFilesUpdated={realism_files_updated}",
            "mitigation": "track remaining failure taxonomy and extend deterministic uplift heuristics",
            "owner": "realism",
        },
        {
            "id": "M18-RSK-002",
            "risk": "Cultural-depth enrichment may over-generalize context notes",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"descriptorFilesUpdated={descriptor_files_updated}",
            "mitigation": "retain explicit marker and monitor coverage/backlog outputs for refinement",
            "owner": "descriptor",
        },
        {
            "id": "M18-RSK-003",
            "risk": "Residual-failure metrics can hide semantic blind spots",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"baselineFailures={baseline_failures} currentFailures={current_failures}",
            "mitigation": "pair burndown metrics with periodic manual evidence audits",
            "owner": "governance",
        },
        {
            "id": "M18-RSK-004",
            "risk": "Candidate mapping drift breaks validator traceability",
            "severity": "high",
            "likelihood": "low",
            "signal": f"missingCandidateKeys={missing_candidate_keys}",
            "mitigation": "fail governance on mapping incompleteness",
            "owner": "pipeline",
        },
        {
            "id": "M18-RSK-005",
            "risk": "CI drift can bypass M18 governance checks",
            "severity": "high",
            "likelihood": "low",
            "signal": "ci target no longer includes m18-pipeline-governance-check",
            "mitigation": "hard-check CI wiring in governance gate",
            "owner": "build",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_realism_files_updated < 0:
        return fail("--min-realism-files-updated must be >= 0")
    if args.min_descriptor_files_updated < 0:
        return fail("--min-descriptor-files-updated must be >= 0")
    if args.min_descriptor_keys_with_support <= 0:
        return fail("--min-descriptor-keys-with-support must be > 0")
    if args.min_style_keys_with_support <= 0:
        return fail("--min-style-keys-with-support must be > 0")
    if args.min_culture_keys_with_support <= 0:
        return fail("--min-culture-keys-with-support must be > 0")
    if args.min_files_with_cultural_depth <= 0:
        return fail("--min-files-with-cultural-depth must be > 0")
    if args.min_files_with_combined_depth <= 0:
        return fail("--min-files-with-combined-depth must be > 0")
    if args.min_expanded_rules <= 0:
        return fail("--min-expanded-rules must be > 0")
    if not (0.0 <= args.min_reduction_ratio <= 1.0):
        return fail("--min-reduction-ratio must be in [0,1]")
    if not (0.0 <= args.max_failure_file_ratio <= 1.0):
        return fail("--max-failure-file-ratio must be in [0,1]")
    if args.min_decision_count <= 0 or args.min_assumption_count <= 0 or args.min_risk_count <= 0:
        return fail("min decision/assumption/risk counts must be > 0")

    realism_path = Path(args.realism_report)
    descriptor_uplift_path = Path(args.descriptor_uplift_report)
    descriptor_registry_path = Path(args.descriptor_registry_report)
    descriptor_coverage_path = Path(args.descriptor_coverage_report)
    validator_path = Path(args.validator_report)
    burndown_path = Path(args.burndown_report)
    makefile_path = Path(args.makefile)
    program_plan_path = Path(args.program_plan_doc)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (realism_path, "--realism-report"),
        (descriptor_uplift_path, "--descriptor-uplift-report"),
        (descriptor_registry_path, "--descriptor-registry-report"),
        (descriptor_coverage_path, "--descriptor-coverage-report"),
        (validator_path, "--validator-report"),
        (burndown_path, "--burndown-report"),
        (makefile_path, "--makefile"),
        (program_plan_path, "--program-plan-doc"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    try:
        realism = load_json(realism_path)
        descriptor_uplift = load_json(descriptor_uplift_path)
        descriptor_registry = load_json(descriptor_registry_path)
        descriptor_coverage = load_json(descriptor_coverage_path)
        validator = load_json(validator_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_realism_source_dir = normalize_path(str(args.required_realism_source_dir))
    required_realism_out_dir = normalize_path(str(args.required_realism_out_dir))
    required_descriptor_out_dir = normalize_path(str(args.required_descriptor_out_dir))
    required_candidate_report = normalize_path(str(args.required_candidate_report))
    required_baseline_report = normalize_path(str(args.required_baseline_report))

    realism_inputs = as_dict(realism.get("inputs"))
    realism_source_dir = normalize_path(str(realism_inputs.get("sourceDir") or ""))
    realism_out_dir = normalize_path(str(realism_inputs.get("outDir") or ""))
    realism_totals = as_dict(realism.get("totals"))
    realism_source_files = as_int(realism_totals.get("sourceFiles"), 0)
    realism_processed_files = as_int(realism_totals.get("processedFiles"), 0)
    realism_files_updated = as_int(realism_totals.get("filesUpdated"), 0)

    descriptor_uplift_inputs = as_dict(descriptor_uplift.get("inputs"))
    descriptor_source_dir = normalize_path(str(descriptor_uplift_inputs.get("sourceDir") or ""))
    descriptor_out_dir = normalize_path(str(descriptor_uplift_inputs.get("outDir") or ""))
    descriptor_uplift_totals = as_dict(descriptor_uplift.get("totals"))
    descriptor_source_files = as_int(descriptor_uplift_totals.get("sourceFiles"), 0)
    descriptor_processed_files = as_int(descriptor_uplift_totals.get("processedFiles"), 0)
    descriptor_files_updated = as_int(descriptor_uplift_totals.get("filesUpdated"), 0)

    descriptor_registry_input_dir = normalize_path(str(descriptor_registry.get("inputDir") or ""))
    descriptor_registry_totals = as_dict(descriptor_registry.get("totals"))
    descriptor_keys_with_support = as_int(descriptor_registry_totals.get("descriptorKeysWithSupport"), 0)
    descriptor_keys_with_evidence = as_int(descriptor_registry_totals.get("descriptorKeysWithEvidence"), 0)

    coverage_ok = as_bool(descriptor_coverage.get("ok"), False)
    descriptor_coverage_input_dir = normalize_path(str(descriptor_coverage.get("inputDir") or ""))
    descriptor_coverage_totals = as_dict(descriptor_coverage.get("totals"))
    style_keys_with_support = as_int(descriptor_coverage_totals.get("styleKeysWithSupport"), 0)
    culture_keys_with_support = as_int(descriptor_coverage_totals.get("cultureKeysWithSupport"), 0)
    files_with_cultural_depth = as_int(descriptor_coverage_totals.get("filesWithCulturalDepth"), 0)
    files_with_combined_depth = as_int(descriptor_coverage_totals.get("filesWithCombinedDepth"), 0)

    validator_ok = as_bool(validator.get("ok"), False)
    validator_inputs = as_dict(validator.get("inputs"))
    validator_corpus_dir = normalize_path(str(validator_inputs.get("corpusDir") or ""))
    validator_candidate_report = normalize_path(str(validator_inputs.get("candidateReport") or ""))
    validator_totals = as_dict(validator.get("totals"))
    validator_source = as_int(validator_totals.get("sourceFiles"), 0)
    validator_processed = as_int(validator_totals.get("processedFiles"), 0)
    validator_rule_count = as_int(validator_totals.get("ruleCount"), 0)
    validator_candidate_keys = as_int(validator_totals.get("candidateKeys"), 0)
    priority_coverage = as_dict(validator.get("priorityCoverage"))
    missing_candidate_keys = len(as_list(priority_coverage.get("missingKeys")))
    mapping_ratio = clamp01(as_float(priority_coverage.get("coverageRatio"), 0.0))

    failure_taxonomy = as_list(validator.get("failureTaxonomy"))
    turn_axis_failures = 0
    for row in failure_taxonomy:
        row_d = as_dict(row)
        if str(row_d.get("code") or "") == "low_turn_axis_step_coverage":
            turn_axis_failures = as_int(row_d.get("count"), 0)
            break

    burndown_ok = as_bool(burndown.get("ok"), False)
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
    m18_realism_block = extract_make_target_block(make_text, "m18-realism-uplift-check")
    m18_descriptor_block = extract_make_target_block(make_text, "m18-descriptor-uplift-check")
    m18_governance_block = extract_make_target_block(make_text, "m18-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(
        required_realism_source_dir,
        required_realism_out_dir,
        required_descriptor_out_dir,
        required_baseline_report,
    )
    assumptions = build_assumption_registry(
        required_realism_out_dir,
        required_descriptor_out_dir,
        args.min_reduction_ratio,
    )
    risks = build_risk_ledger(
        realism_files_updated,
        descriptor_files_updated,
        files_with_cultural_depth,
        baseline_failures,
        current_failures,
        missing_candidate_keys,
    )

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check(
        "m18_realism_report_ok",
        as_bool(realism.get("ok"), False),
        f"realism_ok={as_bool(realism.get('ok'), False)}",
    )
    add_check(
        "m18_realism_counts_min",
        realism_source_files >= args.min_total_files
        and realism_processed_files >= args.min_total_files
        and realism_files_updated >= args.min_realism_files_updated,
        (
            f"source={realism_source_files} processed={realism_processed_files} "
            f"files_updated={realism_files_updated} min_updated={args.min_realism_files_updated}"
        ),
    )
    add_check(
        "m18_descriptor_uplift_report_ok",
        as_bool(descriptor_uplift.get("ok"), False),
        f"descriptor_uplift_ok={as_bool(descriptor_uplift.get('ok'), False)}",
    )
    add_check(
        "m18_descriptor_uplift_counts_min",
        descriptor_source_files >= args.min_total_files
        and descriptor_processed_files >= args.min_total_files
        and descriptor_files_updated >= args.min_descriptor_files_updated,
        (
            f"source={descriptor_source_files} processed={descriptor_processed_files} "
            f"files_updated={descriptor_files_updated} min_updated={args.min_descriptor_files_updated}"
        ),
    )
    add_check(
        "m18_descriptor_registry_counts_min",
        descriptor_keys_with_support >= args.min_descriptor_keys_with_support
        and descriptor_keys_with_evidence >= args.min_descriptor_keys_with_support,
        (
            f"keys_with_support={descriptor_keys_with_support} "
            f"keys_with_evidence={descriptor_keys_with_evidence} "
            f"min={args.min_descriptor_keys_with_support}"
        ),
    )
    add_check(
        "m18_descriptor_coverage_report_ok",
        coverage_ok,
        f"coverage_ok={coverage_ok}",
    )
    add_check(
        "m18_descriptor_depth_thresholds",
        style_keys_with_support >= args.min_style_keys_with_support
        and culture_keys_with_support >= args.min_culture_keys_with_support
        and files_with_cultural_depth >= args.min_files_with_cultural_depth
        and files_with_combined_depth >= args.min_files_with_combined_depth,
        (
            f"style_keys={style_keys_with_support} min_style={args.min_style_keys_with_support} "
            f"culture_keys={culture_keys_with_support} min_culture={args.min_culture_keys_with_support} "
            f"cultural_depth={files_with_cultural_depth} min_cultural_depth={args.min_files_with_cultural_depth} "
            f"combined_depth={files_with_combined_depth} min_combined_depth={args.min_files_with_combined_depth}"
        ),
    )
    add_check(
        "m18_descriptor_coverage_checks_present",
        check_ok(descriptor_coverage, "style_keys_supported_min")
        and check_ok(descriptor_coverage, "culture_keys_supported_min")
        and check_ok(descriptor_coverage, "files_with_cultural_depth_min")
        and check_ok(descriptor_coverage, "files_with_combined_depth_min"),
        "coverage checks include style/culture/cultural-depth/combined-depth thresholds",
    )
    add_check(
        "m18_stage_dir_invariants",
        realism_source_dir == required_realism_source_dir
        and realism_out_dir == required_realism_out_dir
        and descriptor_source_dir == required_realism_out_dir
        and descriptor_out_dir == required_descriptor_out_dir
        and descriptor_registry_input_dir == required_descriptor_out_dir
        and descriptor_coverage_input_dir == required_descriptor_out_dir,
        (
            f"realism_source={realism_source_dir} realism_out={realism_out_dir} "
            f"descriptor_source={descriptor_source_dir} descriptor_out={descriptor_out_dir} "
            f"registry_input={descriptor_registry_input_dir} coverage_input={descriptor_coverage_input_dir}"
        ),
    )
    add_check("m18_validator_report_ok", validator_ok, f"validator_ok={validator_ok}")
    add_check(
        "m18_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m18_validator_candidate_mapping_complete",
        check_ok(validator, "priority_key_mapping_complete")
        and missing_candidate_keys == 0
        and mapping_ratio >= 0.999,
        (
            f"mapping_check={check_ok(validator, 'priority_key_mapping_complete')} "
            f"missing_keys={missing_candidate_keys} coverage_ratio={mapping_ratio:.4f}"
        ),
    )
    add_check(
        "m18_validator_applicability_ok",
        check_ok(validator, "all_rules_have_applicability"),
        f"all_rules_have_applicability={check_ok(validator, 'all_rules_have_applicability')}",
    )
    add_check(
        "m18_validator_input_invariants",
        validator_corpus_dir == required_realism_out_dir
        and validator_candidate_report == required_candidate_report,
        (
            f"validator_corpus={validator_corpus_dir} required_corpus={required_realism_out_dir} "
            f"candidate_report={validator_candidate_report} required_candidate_report={required_candidate_report}"
        ),
    )
    add_check("m18_burndown_ok", burndown_ok, f"burndown_ok={burndown_ok}")
    add_check(
        "m18_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m18_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m18_burndown_input_invariants",
        burndown_baseline_report == required_baseline_report
        and burndown_current_report.endswith("out/m18_validator_realism_uplift_report.json"),
        (
            f"baseline_report={burndown_baseline_report} required_baseline={required_baseline_report} "
            f"current_report={burndown_current_report}"
        ),
    )
    add_check(
        "m18_make_target_invariants",
        required_realism_source_dir in m18_realism_block
        and required_realism_out_dir in m18_realism_block
        and required_realism_out_dir in m18_descriptor_block
        and required_descriptor_out_dir in m18_descriptor_block
        and required_baseline_report in m18_realism_block,
        "M18 make targets reference required staged dirs and baseline report",
    )
    add_check(
        "make_ci_wires_m18_governance",
        "m18-pipeline-governance-check" in ci_line,
        "ci target includes m18-pipeline-governance-check",
    )
    add_check(
        "make_ci_keeps_m17_governance",
        "m17-pipeline-governance-check" in ci_line,
        "ci target retains m17-pipeline-governance-check",
    )
    add_check(
        "make_ci_excludes_legacy_subset_path",
        "corpus/valid_ingest_auto" not in ci_line,
        "ci target excludes legacy subset corpus path",
    )
    add_check(
        "make_m18_targets_exist",
        bool(m18_realism_block.strip())
        and bool(m18_descriptor_block.strip())
        and bool(m18_governance_block.strip()),
        "m18 realism/descriptor/governance target blocks exist",
    )
    add_check(
        "program_plan_mentions_prg183_outcome",
        "M18 execution outcome (PRG-183)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-183 execution outcome",
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
            "realismReport": str(realism_path),
            "descriptorUpliftReport": str(descriptor_uplift_path),
            "descriptorRegistryReport": str(descriptor_registry_path),
            "descriptorCoverageReport": str(descriptor_coverage_path),
            "validatorReport": str(validator_path),
            "burndownReport": str(burndown_path),
            "makefile": str(makefile_path),
            "programPlanDoc": str(program_plan_path),
        },
        "thresholds": {
            "requiredRealismSourceDir": required_realism_source_dir,
            "requiredRealismOutDir": required_realism_out_dir,
            "requiredDescriptorOutDir": required_descriptor_out_dir,
            "requiredCandidateReport": required_candidate_report,
            "requiredBaselineReport": required_baseline_report,
            "minTotalFiles": args.min_total_files,
            "minRealismFilesUpdated": args.min_realism_files_updated,
            "minDescriptorFilesUpdated": args.min_descriptor_files_updated,
            "minDescriptorKeysWithSupport": args.min_descriptor_keys_with_support,
            "minStyleKeysWithSupport": args.min_style_keys_with_support,
            "minCultureKeysWithSupport": args.min_culture_keys_with_support,
            "minFilesWithCulturalDepth": args.min_files_with_cultural_depth,
            "minFilesWithCombinedDepth": args.min_files_with_combined_depth,
            "minExpandedRules": args.min_expanded_rules,
            "minReductionRatio": args.min_reduction_ratio,
            "maxFailureFileRatio": args.max_failure_file_ratio,
            "minDecisionCount": args.min_decision_count,
            "minAssumptionCount": args.min_assumption_count,
            "minRiskCount": args.min_risk_count,
        },
        "metrics": {
            "realismSourceFiles": realism_source_files,
            "realismProcessedFiles": realism_processed_files,
            "realismFilesUpdated": realism_files_updated,
            "descriptorSourceFiles": descriptor_source_files,
            "descriptorProcessedFiles": descriptor_processed_files,
            "descriptorFilesUpdated": descriptor_files_updated,
            "descriptorKeysWithSupport": descriptor_keys_with_support,
            "descriptorKeysWithEvidence": descriptor_keys_with_evidence,
            "styleKeysWithSupport": style_keys_with_support,
            "cultureKeysWithSupport": culture_keys_with_support,
            "filesWithCulturalDepth": files_with_cultural_depth,
            "filesWithCombinedDepth": files_with_combined_depth,
            "validatorSourceFiles": validator_source,
            "validatorProcessedFiles": validator_processed,
            "validatorRuleCount": validator_rule_count,
            "validatorCandidateKeys": validator_candidate_keys,
            "validatorMissingCandidateKeys": missing_candidate_keys,
            "validatorCoverageRatio": round(mapping_ratio, 6),
            "turnAxisCoverageFailures": turn_axis_failures,
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

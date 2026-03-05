#!/usr/bin/env python3
"""Governance gate for M17 single-pipeline descriptor-to-validator adoption."""

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
            "Validate M17 descriptor-to-validator governance and emit "
            "decision/assumption/risk ledgers."
        )
    )
    ap.add_argument(
        "--descriptor-registry-report",
        required=True,
        help="path to M17 descriptor registry report",
    )
    ap.add_argument(
        "--descriptor-coverage-report",
        required=True,
        help="path to M17 descriptor depth coverage report",
    )
    ap.add_argument("--validator-report", required=True, help="path to M17 validator expansion report")
    ap.add_argument("--burndown-report", required=True, help="path to M17 validator burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m17-pipeline-governance", help="report label")
    ap.add_argument(
        "--required-live-corpus-dir",
        default="out/m14_context_specificity/run1",
        help="required live corpus directory used by M17 descriptor and validator runs",
    )
    ap.add_argument(
        "--required-baseline-corpus-dir",
        default="out/m9_full_description_uplift/run1",
        help="required baseline corpus directory used by M17 burn-down",
    )
    ap.add_argument(
        "--required-candidate-report",
        default="out/m15_validator_candidates.json",
        help="required validator candidate ledger path",
    )
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum source files")
    ap.add_argument(
        "--min-descriptor-keys-with-support",
        type=int,
        default=20,
        help="minimum descriptor keys with support in registry report",
    )
    ap.add_argument(
        "--min-style-keys-with-support",
        type=int,
        default=8,
        help="minimum style/performance descriptor keys with support",
    )
    ap.add_argument(
        "--min-culture-keys-with-support",
        type=int,
        default=6,
        help="minimum cultural descriptor keys with support",
    )
    ap.add_argument(
        "--min-files-with-cultural-depth",
        type=int,
        default=55,
        help="minimum files with at least one cultural descriptor",
    )
    ap.add_argument(
        "--min-files-with-combined-depth",
        type=int,
        default=45,
        help="minimum files with combined style+cultural descriptor depth",
    )
    ap.add_argument(
        "--min-expanded-rules",
        type=int,
        default=35,
        help="minimum expanded validator rules expected",
    )
    ap.add_argument(
        "--min-reduction-ratio",
        type=float,
        default=0.70,
        help="minimum required failure reduction ratio",
    )
    ap.add_argument(
        "--max-failure-file-ratio",
        type=float,
        default=0.30,
        help="maximum files-with-failure ratio",
    )
    ap.add_argument("--min-decision-count", type=int, default=5)
    ap.add_argument("--min-assumption-count", type=int, default=5)
    ap.add_argument("--min-risk-count", type=int, default=5)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m17_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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
    required_live_corpus_dir: str, required_baseline_corpus_dir: str, required_candidate_report: str
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M17-DEC-001",
            "decision": "Keep one canonical live corpus path for M17 descriptor and validator runs",
            "chosenOption": (
                f"Use {required_live_corpus_dir} for descriptor registry, coverage, and live validator expansion"
            ),
            "alternativesConsidered": [
                "Use separate corpus roots for descriptor and validator stages",
                "Mix legacy subset paths into M17 stage inputs",
            ],
            "tradeoffs": [
                "pro: preserves one-stack comparability across all files",
                "con: all descriptor and validator fixes must land on one canonical path",
            ],
            "reversalCondition": (
                "If canonical corpus path changes, update descriptor/validator/governance targets atomically"
            ),
        },
        {
            "id": "M17-DEC-002",
            "decision": "Use fixed baseline corpus for M17 burn-down evidence",
            "chosenOption": (
                f"Use {required_baseline_corpus_dir} as baseline for M17 validator burn-down"
            ),
            "alternativesConsidered": [
                "Dynamic baseline selected per run",
                "No baseline and report only current failures",
            ],
            "tradeoffs": [
                "pro: stable reduction metric over time",
                "con: requires maintaining baseline report contract",
            ],
            "reversalCondition": (
                "If baseline definition changes, regenerate baseline artifacts and thresholds together"
            ),
        },
        {
            "id": "M17-DEC-003",
            "decision": "Retain candidate-mapping traceability for M17 validator expansion",
            "chosenOption": (
                f"Require M17 validator report to map all candidate keys from {required_candidate_report}"
            ),
            "alternativesConsidered": [
                "Manual untracked validator additions",
                "Advisory-only candidate mapping checks",
            ],
            "tradeoffs": [
                "pro: preserves evidence-linked traceability from candidate ledger to rule inventory",
                "con: candidate-ledger quality affects downstream rule roadmap",
            ],
            "reversalCondition": "If mapping completeness fails, block governance and CI adoption",
        },
        {
            "id": "M17-DEC-004",
            "decision": "Promote M17 governance to CI-level gate",
            "chosenOption": "Wire m17-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "Run governance manually",
                "Run only validator gate without descriptor-governance coherence",
            ],
            "tradeoffs": [
                "pro: anti-drift checks are enforced continuously",
                "con: CI runtime increases modestly",
            ],
            "reversalCondition": "If CI budget is exceeded, split execution but keep fail-fast governance enforcement",
        },
        {
            "id": "M17-DEC-005",
            "decision": "Publish deterministic governance artifact for M17",
            "chosenOption": "Emit out/m17_pipeline_governance.json with checks and ledgers",
            "alternativesConsidered": [
                "Record governance state only in narrative docs",
                "Scatter governance checks across multiple artifacts",
            ],
            "tradeoffs": [
                "pro: machine-readable audit trail for closeout",
                "con: governance schema must remain stable",
            ],
            "reversalCondition": (
                "If schema changes frequently, version schema while preserving compatibility"
            ),
        },
    ]


def build_assumption_registry(required_live_corpus_dir: str, min_reduction_ratio: float) -> list[dict[str, Any]]:
    return [
        {
            "id": "M17-ASM-001",
            "assumption": "M17 live corpus path remains canonical for descriptor and validator workflows",
            "confidence": 0.9,
            "verificationPlan": f"Enforce {required_live_corpus_dir} across M17 make targets and governance checks",
            "invalidationSignal": "Descriptor or validator inputs diverge from required live path",
        },
        {
            "id": "M17-ASM-002",
            "assumption": "M17 descriptor coverage metrics are sufficient to support style/cultural depth claims",
            "confidence": 0.85,
            "verificationPlan": "Enforce minimum style/culture support and file-depth thresholds",
            "invalidationSignal": "Coverage report fails style/culture/depth threshold checks",
        },
        {
            "id": "M17-ASM-003",
            "assumption": "M17 validator mapping and applicability remain complete over full corpus",
            "confidence": 0.8,
            "verificationPlan": "Require priority mapping complete and all rules with applicability",
            "invalidationSignal": "Missing candidate keys or non-applicable rules appear",
        },
        {
            "id": "M17-ASM-004",
            "assumption": "M17 burn-down ratio remains a meaningful quality signal",
            "confidence": 0.85,
            "verificationPlan": f"Enforce reduction ratio >= {min_reduction_ratio:.2f} with failure-file cap",
            "invalidationSignal": "Reduction ratio remains high while qualitative audits show regressions",
        },
        {
            "id": "M17-ASM-005",
            "assumption": "Program plan narrative remains synchronized with M17 machine outputs",
            "confidence": 0.75,
            "verificationPlan": "Require PROGRAM_PLAN.md to include PRG-173 execution outcome",
            "invalidationSignal": "Governance passes while PRG-173 outcome is absent from plan narrative",
        },
    ]


def build_risk_ledger(
    files_with_cultural_depth: int,
    baseline_failures: int,
    current_failures: int,
    rule_count: int,
    missing_candidate_keys: int,
    turn_axis_failures: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M17-RSK-001",
            "risk": "Descriptor depth may remain uneven across style and cultural subfamilies",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"filesWithCulturalDepth={files_with_cultural_depth}",
            "mitigation": "Track expansion backlog keys and prioritize lowest-support descriptor families",
            "owner": "descriptor",
        },
        {
            "id": "M17-RSK-002",
            "risk": "Remaining biomechanical realism failures may concentrate in turn-axis coverage",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"turnAxisCoverageFailures={turn_axis_failures}",
            "mitigation": "Prioritize axis extraction and normalization for turn-cue steps",
            "owner": "validator",
        },
        {
            "id": "M17-RSK-003",
            "risk": "Burn-down metrics can hide unresolved semantic blind spots",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"baselineFailures={baseline_failures} currentFailures={current_failures}",
            "mitigation": "Pair burn-down metrics with periodic evidence-linked manual audits",
            "owner": "governance",
        },
        {
            "id": "M17-RSK-004",
            "risk": "Candidate mapping drift breaks validator traceability",
            "severity": "high",
            "likelihood": "low",
            "signal": f"missingCandidateKeys={missing_candidate_keys}",
            "mitigation": "Fail governance on mapping incompleteness",
            "owner": "pipeline",
        },
        {
            "id": "M17-RSK-005",
            "risk": "CI drift can bypass M17 governance checks",
            "severity": "high",
            "likelihood": "low",
            "signal": "ci target no longer includes m17-pipeline-governance-check",
            "mitigation": "Hard-check CI wiring in governance gate",
            "owner": "build",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
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

    descriptor_registry_path = Path(args.descriptor_registry_report)
    descriptor_coverage_path = Path(args.descriptor_coverage_report)
    validator_path = Path(args.validator_report)
    burndown_path = Path(args.burndown_report)
    makefile_path = Path(args.makefile)
    program_plan_path = Path(args.program_plan_doc)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
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
        descriptor_registry = load_json(descriptor_registry_path)
        descriptor_coverage = load_json(descriptor_coverage_path)
        validator = load_json(validator_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_live_corpus_dir = normalize_path(str(args.required_live_corpus_dir))
    required_baseline_corpus_dir = normalize_path(str(args.required_baseline_corpus_dir))
    required_candidate_report = normalize_path(str(args.required_candidate_report))

    descriptor_registry_input_dir = normalize_path(str(descriptor_registry.get("inputDir") or ""))
    descriptor_coverage_input_dir = normalize_path(str(descriptor_coverage.get("inputDir") or ""))

    descriptor_registry_totals = as_dict(descriptor_registry.get("totals"))
    descriptor_source = as_int(descriptor_registry_totals.get("sourceFiles"), 0)
    descriptor_processed = as_int(descriptor_registry_totals.get("processedFiles"), 0)
    descriptor_keys_with_support = as_int(
        descriptor_registry_totals.get("descriptorKeysWithSupport"),
        0,
    )
    descriptor_keys_with_evidence = as_int(
        descriptor_registry_totals.get("descriptorKeysWithEvidence"),
        0,
    )

    coverage_ok = as_bool(descriptor_coverage.get("ok"), False)
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
    m17_descriptor_block = extract_make_target_block(make_text, "m17-descriptor-registry-check")
    m17_validator_block = extract_make_target_block(make_text, "m17-validator-expansion-check")
    m17_governance_block = extract_make_target_block(make_text, "m17-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(
        required_live_corpus_dir,
        required_baseline_corpus_dir,
        required_candidate_report,
    )
    assumptions = build_assumption_registry(required_live_corpus_dir, args.min_reduction_ratio)
    risks = build_risk_ledger(
        files_with_cultural_depth,
        baseline_failures,
        current_failures,
        validator_rule_count,
        missing_candidate_keys,
        turn_axis_failures,
    )

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check(
        "m17_descriptor_registry_counts_min",
        descriptor_source >= args.min_total_files
        and descriptor_processed >= args.min_total_files
        and descriptor_keys_with_support >= args.min_descriptor_keys_with_support
        and descriptor_keys_with_evidence >= args.min_descriptor_keys_with_support,
        (
            f"source={descriptor_source} processed={descriptor_processed} "
            f"keys_with_support={descriptor_keys_with_support} "
            f"keys_with_evidence={descriptor_keys_with_evidence} "
            f"min={args.min_descriptor_keys_with_support}"
        ),
    )
    add_check(
        "m17_descriptor_coverage_report_ok",
        coverage_ok,
        f"coverage_ok={coverage_ok}",
    )
    add_check(
        "m17_descriptor_depth_thresholds",
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
        "m17_descriptor_coverage_checks_present",
        check_ok(descriptor_coverage, "style_keys_supported_min")
        and check_ok(descriptor_coverage, "culture_keys_supported_min")
        and check_ok(descriptor_coverage, "files_with_cultural_depth_min")
        and check_ok(descriptor_coverage, "files_with_combined_depth_min"),
        "coverage checks include style/culture/cultural-depth/combined-depth thresholds",
    )
    add_check(
        "m17_descriptor_input_dir_invariant",
        descriptor_registry_input_dir == required_live_corpus_dir
        and descriptor_coverage_input_dir == required_live_corpus_dir,
        (
            f"registry_input={descriptor_registry_input_dir} coverage_input={descriptor_coverage_input_dir} "
            f"required={required_live_corpus_dir}"
        ),
    )
    add_check("m17_validator_report_ok", validator_ok, f"validator_ok={validator_ok}")
    add_check(
        "m17_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m17_validator_candidate_mapping_complete",
        check_ok(validator, "priority_key_mapping_complete")
        and missing_candidate_keys == 0
        and mapping_ratio >= 0.999,
        (
            f"mapping_check={check_ok(validator, 'priority_key_mapping_complete')} "
            f"missing_keys={missing_candidate_keys} coverage_ratio={mapping_ratio:.4f}"
        ),
    )
    add_check(
        "m17_validator_applicability_ok",
        check_ok(validator, "all_rules_have_applicability"),
        f"all_rules_have_applicability={check_ok(validator, 'all_rules_have_applicability')}",
    )
    add_check("m17_burndown_ok", burndown_ok, f"burndown_ok={burndown_ok}")
    add_check(
        "m17_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m17_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m17_corpus_dir_invariant",
        validator_corpus_dir == required_live_corpus_dir,
        f"validator_input={validator_corpus_dir} required={required_live_corpus_dir}",
    )
    add_check(
        "m17_candidate_report_invariant",
        validator_candidate_report == required_candidate_report,
        f"validator_candidate_report={validator_candidate_report} required={required_candidate_report}",
    )
    add_check(
        "m17_make_target_dir_invariants",
        required_live_corpus_dir in m17_descriptor_block
        and required_baseline_corpus_dir in m17_validator_block
        and required_live_corpus_dir in m17_validator_block,
        "m17 descriptor/validator make targets reference required corpus dirs",
    )
    add_check(
        "m17_burndown_inputs_invariant",
        burndown_baseline_report.endswith("out/m17_validator_expansion_baseline_report.json")
        and burndown_current_report.endswith("out/m17_validator_expansion_report.json"),
        f"burndown_baseline={burndown_baseline_report} burndown_current={burndown_current_report}",
    )
    add_check(
        "make_ci_wires_m17_governance",
        "m17-pipeline-governance-check" in ci_line,
        "ci target includes m17-pipeline-governance-check",
    )
    add_check(
        "make_ci_keeps_m16_governance",
        "m16-pipeline-governance-check" in ci_line,
        "ci target retains m16-pipeline-governance-check",
    )
    add_check(
        "make_ci_excludes_legacy_subset_path",
        "corpus/valid_ingest_auto" not in ci_line,
        "ci target excludes legacy subset corpus path",
    )
    add_check(
        "make_m17_targets_exist",
        bool(m17_descriptor_block.strip())
        and bool(m17_validator_block.strip())
        and bool(m17_governance_block.strip()),
        "m17 descriptor/validator/governance target blocks exist",
    )
    add_check(
        "program_plan_mentions_prg173_outcome",
        "M17 execution outcome (PRG-173)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-173 execution outcome",
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
            "descriptorRegistryReport": str(descriptor_registry_path),
            "descriptorCoverageReport": str(descriptor_coverage_path),
            "validatorReport": str(validator_path),
            "burndownReport": str(burndown_path),
            "makefile": str(makefile_path),
            "programPlanDoc": str(program_plan_path),
        },
        "thresholds": {
            "requiredLiveCorpusDir": required_live_corpus_dir,
            "requiredBaselineCorpusDir": required_baseline_corpus_dir,
            "requiredCandidateReport": required_candidate_report,
            "minTotalFiles": args.min_total_files,
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
            "descriptorSourceFiles": descriptor_source,
            "descriptorProcessedFiles": descriptor_processed,
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

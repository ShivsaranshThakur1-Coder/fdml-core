#!/usr/bin/env python3
"""Governance gate for M15 single-pipeline adoption."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate M15 discovery-to-validator governance and emit decision/assumption/risk ledgers."
    )
    ap.add_argument("--discovery-report", required=True, help="path to M15 discovery report")
    ap.add_argument("--validator-report", required=True, help="path to M15 validator expansion report")
    ap.add_argument("--burndown-report", required=True, help="path to M15 validator burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m15-pipeline-governance", help="report label")
    ap.add_argument(
        "--required-corpus-dir",
        default="out/m14_context_specificity/run1",
        help="required single corpus directory used by M15 workflow",
    )
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum source files")
    ap.add_argument(
        "--min-validator-candidates",
        type=int,
        default=13,
        help="minimum validator candidate keys expected",
    )
    ap.add_argument(
        "--min-expanded-rules",
        type=int,
        default=15,
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
    print(f"m15_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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
    m = re.search(rf"(?ms)^{re.escape(target)}:\n(.*?)(?:^\S|\Z)", make_text)
    if not m:
        return ""
    return m.group(1)


def check_ok(payload: dict[str, Any], check_id: str) -> bool:
    for row in as_list(payload.get("checks")):
        d = as_dict(row)
        if str(d.get("id") or "") == check_id:
            return as_bool(d.get("ok"), False)
    return False


def build_decision_registry(required_corpus_dir: str, reduction_ratio: float, rule_count: int) -> list[dict[str, Any]]:
    return [
        {
            "id": "M15-DEC-001",
            "decision": "Keep one canonical corpus input path for M15",
            "chosenOption": f"Use {required_corpus_dir} for M15 discovery and live validator runs",
            "alternativesConsidered": [
                "Run discovery/validators on mixed legacy subsets",
                "Use different corpus roots for discovery and validation",
            ],
            "tradeoffs": [
                "pro: prevents branch drift in semantics/rules",
                "con: requires all remediations to land on one path first",
            ],
            "reversalCondition": "If canonical corpus path changes in plan, update all M15 gates atomically",
        },
        {
            "id": "M15-DEC-002",
            "decision": "Use candidate-driven validator expansion",
            "chosenOption": "Map M15 validator candidates into explicit expanded validator rules",
            "alternativesConsidered": [
                "Manual ad-hoc rule additions",
                "Reuse M13 rules unchanged",
            ],
            "tradeoffs": [
                "pro: evidence-linked traceability from discovery to validation",
                "con: candidate extraction quality directly affects rule roadmap",
            ],
            "reversalCondition": "If candidate mapping becomes incomplete, block governance until restored",
        },
        {
            "id": "M15-DEC-003",
            "decision": "Baseline/current burn-down against same expanded stack",
            "chosenOption": "Compare baseline and live with identical rule inventory",
            "alternativesConsidered": [
                "Compare against legacy rule stack",
                "Skip baseline and report only current failures",
            ],
            "tradeoffs": [
                "pro: reduction metric is interpretable and stable",
                "con: requires maintaining baseline run path",
            ],
            "reversalCondition": "If baseline corpus definition changes, regenerate baseline in same run",
        },
        {
            "id": "M15-DEC-004",
            "decision": "Promote M15 governance to CI-level gate",
            "chosenOption": "Wire m15-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "Run governance manually",
                "Only check validator output without governance",
            ],
            "tradeoffs": [
                "pro: anti-drift checks run continuously",
                "con: CI runtime increases",
            ],
            "reversalCondition": "If CI time budget is exceeded, split gate but keep fail-fast governance enforcement",
        },
        {
            "id": "M15-DEC-005",
            "decision": "Record program-level governance state in machine-readable artifact",
            "chosenOption": "Emit out/m15_pipeline_governance.json with checks + ledgers",
            "alternativesConsidered": [
                "Keep governance only in prose docs",
                "Scatter checks across unrelated reports",
            ],
            "tradeoffs": [
                "pro: deterministic audit trail",
                "con: requires schema consistency",
            ],
            "reversalCondition": "If schema grows unstable, split ledgers into referenced sub-artifacts",
        },
    ]


def build_assumption_registry(required_corpus_dir: str, min_reduction_ratio: float) -> list[dict[str, Any]]:
    return [
        {
            "id": "M15-ASM-001",
            "assumption": "M15 context-normalized corpus remains canonical",
            "confidence": 0.9,
            "verificationPlan": f"Enforce {required_corpus_dir} in make targets and governance checks",
            "invalidationSignal": "Discovery or validator report points to a different live corpus path",
        },
        {
            "id": "M15-ASM-002",
            "assumption": "Candidate-derived rules reflect discovery evidence sufficiently",
            "confidence": 0.8,
            "verificationPlan": "Require complete candidate-key mapping in validator report",
            "invalidationSignal": "priority_key_mapping_complete becomes false",
        },
        {
            "id": "M15-ASM-003",
            "assumption": "Burn-down ratio is a meaningful quality signal",
            "confidence": 0.85,
            "verificationPlan": f"Enforce reduction ratio >= {min_reduction_ratio:.2f} with failure-file cap",
            "invalidationSignal": "High reduction ratio but worsening qualitative spot checks",
        },
        {
            "id": "M15-ASM-004",
            "assumption": "Rule applicability remains broad over full corpus",
            "confidence": 0.8,
            "verificationPlan": "Enforce all_rules_have_applicability in validator report",
            "invalidationSignal": "Multiple rules become non-applicable across runs",
        },
        {
            "id": "M15-ASM-005",
            "assumption": "Program plan narrative stays synchronized with machine outputs",
            "confidence": 0.75,
            "verificationPlan": "Check PROGRAM_PLAN includes PRG-153 outcome and next-step shift",
            "invalidationSignal": "Governance report passes while docs omit M15 governance outcome",
        },
    ]


def build_risk_ledger(
    baseline_failures: int,
    current_failures: int,
    rule_count: int,
    missing_candidate_keys: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M15-RSK-001",
            "risk": "Expanded validator inventory may overfit current corpus",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"ruleCount={rule_count}",
            "mitigation": "Track applicability and failures by formation/context buckets",
            "owner": "validator",
        },
        {
            "id": "M15-RSK-002",
            "risk": "Burn-down metrics can hide semantic blind spots",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"baselineFailures={baseline_failures} currentFailures={current_failures}",
            "mitigation": "Pair burn-down with periodic manual evidence audits",
            "owner": "governance",
        },
        {
            "id": "M15-RSK-003",
            "risk": "Candidate mapping drift breaks traceability",
            "severity": "high",
            "likelihood": "low",
            "signal": f"missingCandidateKeys={missing_candidate_keys}",
            "mitigation": "Fail gate on mapping incompleteness",
            "owner": "pipeline",
        },
        {
            "id": "M15-RSK-004",
            "risk": "CI drift can bypass M15 gate",
            "severity": "high",
            "likelihood": "low",
            "signal": "ci target no longer includes m15-pipeline-governance-check",
            "mitigation": "Hard-check ci wiring in governance gate",
            "owner": "build",
        },
        {
            "id": "M15-RSK-005",
            "risk": "Legacy subset paths reintroduced into control path",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "legacy subset strings appear in ci or m15 make blocks",
            "mitigation": "Enforce legacy path exclusion checks",
            "owner": "program",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_validator_candidates <= 0:
        return fail("--min-validator-candidates must be > 0")
    if args.min_expanded_rules <= 0:
        return fail("--min-expanded-rules must be > 0")
    if not (0.0 <= args.min_reduction_ratio <= 1.0):
        return fail("--min-reduction-ratio must be in [0,1]")
    if not (0.0 <= args.max_failure_file_ratio <= 1.0):
        return fail("--max-failure-file-ratio must be in [0,1]")
    if args.min_decision_count <= 0 or args.min_assumption_count <= 0 or args.min_risk_count <= 0:
        return fail("min decision/assumption/risk counts must be > 0")

    discovery_path = Path(args.discovery_report)
    validator_path = Path(args.validator_report)
    burndown_path = Path(args.burndown_report)
    makefile_path = Path(args.makefile)
    program_plan_path = Path(args.program_plan_doc)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (discovery_path, "--discovery-report"),
        (validator_path, "--validator-report"),
        (burndown_path, "--burndown-report"),
        (makefile_path, "--makefile"),
        (program_plan_path, "--program-plan-doc"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    try:
        discovery = load_json(discovery_path)
        validator = load_json(validator_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_corpus_dir = normalize_path(str(args.required_corpus_dir))

    discovery_totals = as_dict(discovery.get("totals"))
    discovery_source = as_int(discovery_totals.get("sourceFiles"), 0)
    discovery_processed = as_int(discovery_totals.get("processedFiles"), 0)
    discovery_missing = as_int(discovery_totals.get("checklistMissing"), 0)
    discovery_uncertain = as_int(discovery_totals.get("checklistUncertain"), 0)
    discovery_candidate_validators = as_int(discovery_totals.get("validatorCandidateUniqueTotal"), 0)
    discovery_saturation = as_dict(discovery.get("saturation"))
    tail_ratios = [as_float(x, 1.0) for x in as_list(discovery_saturation.get("latestGrowthRatios"))]
    saturation_tail_ok = len(tail_ratios) >= 2 and all(x <= 0.01 for x in tail_ratios[-2:])
    saturation_consecutive = as_int(discovery_saturation.get("consecutivePassesUnderThreshold"), 0)

    validator_ok = as_bool(validator.get("ok"), False)
    validator_inputs = as_dict(validator.get("inputs"))
    validator_corpus_dir = normalize_path(str(validator_inputs.get("corpusDir") or ""))
    validator_totals = as_dict(validator.get("totals"))
    validator_source = as_int(validator_totals.get("sourceFiles"), 0)
    validator_processed = as_int(validator_totals.get("processedFiles"), 0)
    validator_rule_count = as_int(validator_totals.get("ruleCount"), 0)
    validator_candidate_keys = as_int(validator_totals.get("candidateKeys"), 0)
    priority_coverage = as_dict(validator.get("priorityCoverage"))
    missing_candidate_keys = len(as_list(priority_coverage.get("missingKeys")))
    mapping_ratio = clamp01(as_float(priority_coverage.get("coverageRatio"), 0.0))

    burndown_ok = as_bool(burndown.get("ok"), False)
    burndown_totals = as_dict(burndown.get("totals"))
    baseline_failures = as_int(burndown_totals.get("baselineRuleFailures"), 0)
    current_failures = as_int(burndown_totals.get("currentRuleFailures"), 0)
    reduction_ratio = clamp01(as_float(burndown_totals.get("failureReductionRatio"), 0.0))
    failure_file_ratio = clamp01(as_float(burndown_totals.get("currentFailureFileRatio"), 1.0))

    make_text = makefile_path.read_text(encoding="utf-8")
    ci_line = extract_make_target_line(make_text, "ci")
    m15_discovery_block = extract_make_target_block(make_text, "m15-discovery-run")
    m15_validator_block = extract_make_target_block(make_text, "m15-validator-expansion-check")
    m15_governance_block = extract_make_target_block(make_text, "m15-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(required_corpus_dir, reduction_ratio, validator_rule_count)
    assumptions = build_assumption_registry(required_corpus_dir, args.min_reduction_ratio)
    risks = build_risk_ledger(baseline_failures, current_failures, validator_rule_count, missing_candidate_keys)

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check(
        "m15_discovery_counts_min",
        discovery_source >= args.min_total_files and discovery_processed >= args.min_total_files,
        f"source={discovery_source} processed={discovery_processed} min={args.min_total_files}",
    )
    add_check(
        "m15_discovery_checklist_complete",
        discovery_missing == 0 and discovery_uncertain == 0,
        f"missing={discovery_missing} uncertain={discovery_uncertain}",
    )
    add_check(
        "m15_discovery_candidate_validators_min",
        discovery_candidate_validators >= args.min_validator_candidates,
        f"validator_candidates={discovery_candidate_validators} min={args.min_validator_candidates}",
    )
    add_check(
        "m15_discovery_saturation_tail",
        saturation_tail_ok and saturation_consecutive >= 2,
        f"tail={tail_ratios[-2:] if len(tail_ratios)>=2 else tail_ratios} consecutive={saturation_consecutive}",
    )
    add_check("m15_validator_report_ok", validator_ok, f"validator_ok={validator_ok}")
    add_check(
        "m15_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m15_validator_candidate_mapping_complete",
        check_ok(validator, "priority_key_mapping_complete") and missing_candidate_keys == 0,
        (
            f"mapping_check={check_ok(validator, 'priority_key_mapping_complete')} "
            f"missing_keys={missing_candidate_keys} coverage_ratio={mapping_ratio:.4f}"
        ),
    )
    add_check(
        "m15_validator_applicability_ok",
        check_ok(validator, "all_rules_have_applicability"),
        f"all_rules_have_applicability={check_ok(validator, 'all_rules_have_applicability')}",
    )
    add_check("m15_burndown_ok", burndown_ok, f"burndown_ok={burndown_ok}")
    add_check(
        "m15_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m15_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m15_corpus_dir_invariants",
        normalize_path(str(discovery.get("inputDir") or "")) == required_corpus_dir
        and validator_corpus_dir == required_corpus_dir,
        (
            f"discovery_input={normalize_path(str(discovery.get('inputDir') or ''))} "
            f"validator_input={validator_corpus_dir} required={required_corpus_dir}"
        ),
    )
    add_check(
        "make_targets_use_required_corpus_dir",
        required_corpus_dir in m15_discovery_block and required_corpus_dir in m15_validator_block,
        "m15 make targets reference required single corpus dir",
    )
    add_check(
        "make_ci_wires_m15_governance",
        "m15-pipeline-governance-check" in ci_line,
        "ci target includes m15-pipeline-governance-check",
    )
    add_check(
        "make_ci_excludes_legacy_subset_path",
        "corpus/valid_ingest_auto" not in ci_line,
        "ci target excludes legacy subset corpus path",
    )
    add_check(
        "make_target_block_exists",
        bool(m15_governance_block.strip()),
        "m15-pipeline-governance-check target block exists",
    )
    add_check(
        "program_plan_mentions_prg153_outcome",
        "M15 execution outcome (PRG-153)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-153 execution outcome",
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
            "discoveryReport": str(discovery_path),
            "validatorReport": str(validator_path),
            "burndownReport": str(burndown_path),
            "makefile": str(makefile_path),
            "programPlanDoc": str(program_plan_path),
        },
        "thresholds": {
            "requiredCorpusDir": required_corpus_dir,
            "minTotalFiles": args.min_total_files,
            "minValidatorCandidates": args.min_validator_candidates,
            "minExpandedRules": args.min_expanded_rules,
            "minReductionRatio": args.min_reduction_ratio,
            "maxFailureFileRatio": args.max_failure_file_ratio,
            "minDecisionCount": args.min_decision_count,
            "minAssumptionCount": args.min_assumption_count,
            "minRiskCount": args.min_risk_count,
        },
        "metrics": {
            "discoverySourceFiles": discovery_source,
            "discoveryProcessedFiles": discovery_processed,
            "discoveryChecklistMissing": discovery_missing,
            "discoveryChecklistUncertain": discovery_uncertain,
            "discoveryValidatorCandidateUniqueTotal": discovery_candidate_validators,
            "discoverySaturationConsecutive": saturation_consecutive,
            "validatorSourceFiles": validator_source,
            "validatorProcessedFiles": validator_processed,
            "validatorRuleCount": validator_rule_count,
            "validatorCandidateKeys": validator_candidate_keys,
            "validatorMissingCandidateKeys": missing_candidate_keys,
            "validatorCoverageRatio": round(mapping_ratio, 6),
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

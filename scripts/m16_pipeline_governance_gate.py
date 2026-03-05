#!/usr/bin/env python3
"""Governance gate for M16 single-pipeline adoption."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate M16 contract-to-validator governance and emit decision/assumption/risk ledgers."
    )
    ap.add_argument("--contract-report", required=True, help="path to M16 contract promotion report")
    ap.add_argument("--validator-report", required=True, help="path to M16 validator expansion report")
    ap.add_argument("--burndown-report", required=True, help="path to M16 validator burndown report")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md", help="path to program plan doc")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m16-pipeline-governance", help="report label")
    ap.add_argument(
        "--required-live-corpus-dir",
        default="out/m14_context_specificity/run1",
        help="required live corpus directory used by M16 validator runs",
    )
    ap.add_argument(
        "--required-baseline-corpus-dir",
        default="out/m9_full_description_uplift/run1",
        help="required baseline corpus directory used by M16 burn-down",
    )
    ap.add_argument(
        "--required-candidate-report",
        default="out/m15_validator_candidates.json",
        help="required validator candidate ledger path",
    )
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum source files")
    ap.add_argument("--min-accepted-rows", type=int, default=15, help="minimum accepted ontology rows")
    ap.add_argument("--min-promoted-fields", type=int, default=15, help="minimum promoted contract fields")
    ap.add_argument("--max-unknown-key-count", type=int, default=0, help="maximum unknown contract keys")
    ap.add_argument(
        "--min-expanded-rules",
        type=int,
        default=25,
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
    print(f"m16_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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
            "id": "M16-DEC-001",
            "decision": "Keep one canonical live corpus path for M16 validation",
            "chosenOption": f"Use {required_live_corpus_dir} as the only live M16 validator corpus",
            "alternativesConsidered": [
                "Mix legacy subsets with promoted corpus outputs",
                "Use different corpus roots for validator and governance checks",
            ],
            "tradeoffs": [
                "pro: preserves one-stack comparability across all files",
                "con: all remediations must land on canonical corpus before release",
            ],
            "reversalCondition": "If canonical corpus path changes in plan, update validator and governance targets atomically",
        },
        {
            "id": "M16-DEC-002",
            "decision": "Use fixed baseline corpus for burn-down evidence",
            "chosenOption": f"Use {required_baseline_corpus_dir} as baseline for M16 burn-down comparisons",
            "alternativesConsidered": [
                "Dynamic baseline per run",
                "No baseline and report current failures only",
            ],
            "tradeoffs": [
                "pro: stable reduction metric over time",
                "con: requires explicit baseline artifact maintenance",
            ],
            "reversalCondition": "If baseline definition changes, regenerate baseline and update governance thresholds together",
        },
        {
            "id": "M16-DEC-003",
            "decision": "Retain evidence-linked candidate mapping for M16 validator stack",
            "chosenOption": f"Require M16 validator report to map all candidate keys from {required_candidate_report}",
            "alternativesConsidered": [
                "Manual untracked rule additions",
                "Candidate mapping checks as advisory warnings",
            ],
            "tradeoffs": [
                "pro: preserves traceability from discovery evidence to rule inventory",
                "con: candidate ledger quality directly affects downstream rule planning",
            ],
            "reversalCondition": "If candidate mapping cannot be completed, fail governance and block CI adoption",
        },
        {
            "id": "M16-DEC-004",
            "decision": "Promote M16 governance to CI-level gate",
            "chosenOption": "Wire m16-pipeline-governance-check into ci target",
            "alternativesConsidered": [
                "Run M16 governance manually",
                "Gate only validator reports without governance coherence checks",
            ],
            "tradeoffs": [
                "pro: anti-drift constraints enforced continuously",
                "con: CI runtime increases slightly",
            ],
            "reversalCondition": "If CI budget is exceeded, split execution but keep governance as required fail-fast step",
        },
        {
            "id": "M16-DEC-005",
            "decision": "Publish deterministic governance artifact for M16",
            "chosenOption": "Emit out/m16_pipeline_governance.json with checks and registries",
            "alternativesConsidered": [
                "Record governance status only in docs",
                "Scatter governance signals across multiple unrelated files",
            ],
            "tradeoffs": [
                "pro: machine-readable audit trail for closeout",
                "con: requires schema stability for governance artifact",
            ],
            "reversalCondition": "If report schema changes frequently, version schema and keep backward-compatible keys",
        },
    ]


def build_assumption_registry(required_live_corpus_dir: str, min_reduction_ratio: float) -> list[dict[str, Any]]:
    return [
        {
            "id": "M16-ASM-001",
            "assumption": "M16 live corpus path remains canonical for validator and governance checks",
            "confidence": 0.9,
            "verificationPlan": f"Enforce {required_live_corpus_dir} in make targets and governance checks",
            "invalidationSignal": "Validator report input corpus diverges from required live path",
        },
        {
            "id": "M16-ASM-002",
            "assumption": "Contract promotion outputs are sufficiently rich for M16 validator deepening",
            "confidence": 0.85,
            "verificationPlan": "Require minimum accepted rows and promoted fields with zero unknown keys",
            "invalidationSignal": "Contract report accepted/promoted totals drop below thresholds",
        },
        {
            "id": "M16-ASM-003",
            "assumption": "M16 burn-down ratio remains a meaningful quality signal",
            "confidence": 0.85,
            "verificationPlan": f"Enforce reduction ratio >= {min_reduction_ratio:.2f} with failure-file cap",
            "invalidationSignal": "Reduction ratio remains high while manual audit quality degrades",
        },
        {
            "id": "M16-ASM-004",
            "assumption": "Expanded M16 rules stay broadly applicable over full corpus",
            "confidence": 0.8,
            "verificationPlan": "Require all_rules_have_applicability and minimum expanded rule count",
            "invalidationSignal": "Rules with zero applicability appear in live report",
        },
        {
            "id": "M16-ASM-005",
            "assumption": "Program plan narrative remains synchronized with M16 machine outputs",
            "confidence": 0.75,
            "verificationPlan": "Require PROGRAM_PLAN.md to include PRG-163 execution outcome",
            "invalidationSignal": "Governance passes while PRG-163 outcome is missing from plan doc",
        },
    ]


def build_risk_ledger(
    unknown_key_count: int,
    baseline_failures: int,
    current_failures: int,
    rule_count: int,
    missing_candidate_keys: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M16-RSK-001",
            "risk": "Contract expansion may still underfit rare regional semantics",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"unknownKeyCount={unknown_key_count}",
            "mitigation": "Track unknown keys and field backlog in next milestone",
            "owner": "contract",
        },
        {
            "id": "M16-RSK-002",
            "risk": "Expanded validator inventory can overfit current corpus",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"ruleCount={rule_count}",
            "mitigation": "Monitor applicability and formation-bucket coverage every run",
            "owner": "validator",
        },
        {
            "id": "M16-RSK-003",
            "risk": "Burn-down metrics can hide unmodeled semantic blind spots",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"baselineFailures={baseline_failures} currentFailures={current_failures}",
            "mitigation": "Pair burn-down with periodic evidence-linked manual audits",
            "owner": "governance",
        },
        {
            "id": "M16-RSK-004",
            "risk": "Candidate mapping drift breaks discovery-to-rule traceability",
            "severity": "high",
            "likelihood": "low",
            "signal": f"missingCandidateKeys={missing_candidate_keys}",
            "mitigation": "Fail governance on mapping incompleteness",
            "owner": "pipeline",
        },
        {
            "id": "M16-RSK-005",
            "risk": "CI drift can bypass M16 governance checks",
            "severity": "high",
            "likelihood": "low",
            "signal": "ci target no longer includes m16-pipeline-governance-check",
            "mitigation": "Hard-check CI wiring in governance gate",
            "owner": "build",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_accepted_rows <= 0:
        return fail("--min-accepted-rows must be > 0")
    if args.min_promoted_fields <= 0:
        return fail("--min-promoted-fields must be > 0")
    if args.max_unknown_key_count < 0:
        return fail("--max-unknown-key-count must be >= 0")
    if args.min_expanded_rules <= 0:
        return fail("--min-expanded-rules must be > 0")
    if not (0.0 <= args.min_reduction_ratio <= 1.0):
        return fail("--min-reduction-ratio must be in [0,1]")
    if not (0.0 <= args.max_failure_file_ratio <= 1.0):
        return fail("--max-failure-file-ratio must be in [0,1]")
    if args.min_decision_count <= 0 or args.min_assumption_count <= 0 or args.min_risk_count <= 0:
        return fail("min decision/assumption/risk counts must be > 0")

    contract_path = Path(args.contract_report)
    validator_path = Path(args.validator_report)
    burndown_path = Path(args.burndown_report)
    makefile_path = Path(args.makefile)
    program_plan_path = Path(args.program_plan_doc)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (contract_path, "--contract-report"),
        (validator_path, "--validator-report"),
        (burndown_path, "--burndown-report"),
        (makefile_path, "--makefile"),
        (program_plan_path, "--program-plan-doc"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    try:
        contract = load_json(contract_path)
        validator = load_json(validator_path)
        burndown = load_json(burndown_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_live_corpus_dir = normalize_path(str(args.required_live_corpus_dir))
    required_baseline_corpus_dir = normalize_path(str(args.required_baseline_corpus_dir))
    required_candidate_report = normalize_path(str(args.required_candidate_report))

    contract_inputs = as_dict(contract.get("inputs"))
    contract_totals = as_dict(contract.get("totals"))
    contract_input_rows = as_int(contract_totals.get("inputRows"), 0)
    contract_accepted_rows = as_int(contract_totals.get("acceptedRows"), 0)
    contract_promoted_fields = as_int(contract_totals.get("promotedFields"), 0)
    contract_unknown_key_count = as_int(contract_totals.get("unknownKeyCount"), 0)

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
    m16_contract_block = extract_make_target_block(make_text, "m16-contract-promotion-check")
    m16_validator_block = extract_make_target_block(make_text, "m16-validator-expansion-check")
    m16_governance_block = extract_make_target_block(make_text, "m16-pipeline-governance-check")

    plan_text = program_plan_path.read_text(encoding="utf-8")

    decisions = build_decision_registry(
        required_live_corpus_dir, required_baseline_corpus_dir, required_candidate_report
    )
    assumptions = build_assumption_registry(required_live_corpus_dir, args.min_reduction_ratio)
    risks = build_risk_ledger(
        contract_unknown_key_count,
        baseline_failures,
        current_failures,
        validator_rule_count,
        missing_candidate_keys,
    )

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check(
        "m16_contract_rows_min",
        contract_input_rows >= args.min_accepted_rows and contract_accepted_rows >= args.min_accepted_rows,
        f"input_rows={contract_input_rows} accepted_rows={contract_accepted_rows} min={args.min_accepted_rows}",
    )
    add_check(
        "m16_contract_promoted_fields_min",
        contract_promoted_fields >= args.min_promoted_fields,
        f"promoted_fields={contract_promoted_fields} min={args.min_promoted_fields}",
    )
    add_check(
        "m16_contract_unknown_keys_max",
        contract_unknown_key_count <= args.max_unknown_key_count,
        f"unknown_key_count={contract_unknown_key_count} max={args.max_unknown_key_count}",
    )
    add_check(
        "m16_contract_inputs_present",
        bool(contract_inputs.get("ontologyCandidates"))
        and bool(contract_inputs.get("schema"))
        and bool(contract_inputs.get("spec")),
        "contract inputs include ontologyCandidates, schema, and spec",
    )
    add_check("m16_validator_report_ok", validator_ok, f"validator_ok={validator_ok}")
    add_check(
        "m16_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"source={validator_source} processed={validator_processed} "
            f"rules={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m16_validator_candidate_mapping_complete",
        check_ok(validator, "priority_key_mapping_complete")
        and missing_candidate_keys == 0
        and mapping_ratio >= 0.999,
        (
            f"mapping_check={check_ok(validator, 'priority_key_mapping_complete')} "
            f"missing_keys={missing_candidate_keys} coverage_ratio={mapping_ratio:.4f}"
        ),
    )
    add_check(
        "m16_validator_applicability_ok",
        check_ok(validator, "all_rules_have_applicability"),
        f"all_rules_have_applicability={check_ok(validator, 'all_rules_have_applicability')}",
    )
    add_check("m16_burndown_ok", burndown_ok, f"burndown_ok={burndown_ok}")
    add_check(
        "m16_burndown_reduction_ratio_min",
        reduction_ratio >= args.min_reduction_ratio,
        f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
    )
    add_check(
        "m16_burndown_failure_file_ratio_max",
        failure_file_ratio <= args.max_failure_file_ratio,
        f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
    )
    add_check(
        "m16_corpus_dir_invariant",
        validator_corpus_dir == required_live_corpus_dir,
        f"validator_input={validator_corpus_dir} required={required_live_corpus_dir}",
    )
    add_check(
        "m16_candidate_report_invariant",
        validator_candidate_report == required_candidate_report,
        f"validator_candidate_report={validator_candidate_report} required={required_candidate_report}",
    )
    add_check(
        "m16_make_target_dir_invariants",
        required_baseline_corpus_dir in m16_validator_block and required_live_corpus_dir in m16_validator_block,
        "m16 validator make target references required baseline and live corpus dirs",
    )
    add_check(
        "m16_burndown_inputs_invariant",
        burndown_baseline_report.endswith("out/m16_validator_expansion_baseline_report.json")
        and burndown_current_report.endswith("out/m16_validator_expansion_report.json"),
        f"burndown_baseline={burndown_baseline_report} burndown_current={burndown_current_report}",
    )
    add_check(
        "make_ci_wires_m16_governance",
        "m16-pipeline-governance-check" in ci_line,
        "ci target includes m16-pipeline-governance-check",
    )
    add_check(
        "make_ci_keeps_m15_governance",
        "m15-pipeline-governance-check" in ci_line,
        "ci target retains m15-pipeline-governance-check",
    )
    add_check(
        "make_ci_excludes_legacy_subset_path",
        "corpus/valid_ingest_auto" not in ci_line,
        "ci target excludes legacy subset corpus path",
    )
    add_check(
        "make_m16_targets_exist",
        bool(m16_contract_block.strip()) and bool(m16_validator_block.strip()) and bool(m16_governance_block.strip()),
        "m16 contract/validator/governance target blocks exist",
    )
    add_check(
        "program_plan_mentions_prg163_outcome",
        "M16 execution outcome (PRG-163)" in plan_text,
        "PROGRAM_PLAN.md includes PRG-163 execution outcome",
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
            "contractReport": str(contract_path),
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
            "minAcceptedRows": args.min_accepted_rows,
            "minPromotedFields": args.min_promoted_fields,
            "maxUnknownKeyCount": args.max_unknown_key_count,
            "minExpandedRules": args.min_expanded_rules,
            "minReductionRatio": args.min_reduction_ratio,
            "maxFailureFileRatio": args.max_failure_file_ratio,
            "minDecisionCount": args.min_decision_count,
            "minAssumptionCount": args.min_assumption_count,
            "minRiskCount": args.min_risk_count,
        },
        "metrics": {
            "contractInputRows": contract_input_rows,
            "contractAcceptedRows": contract_accepted_rows,
            "contractPromotedFields": contract_promoted_fields,
            "contractUnknownKeyCount": contract_unknown_key_count,
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

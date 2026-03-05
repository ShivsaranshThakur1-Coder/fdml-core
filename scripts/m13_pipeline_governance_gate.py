#!/usr/bin/env python3
"""Governance gate for M13 anti-drift full-product workflow."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate M13 single-path workflow and emit decision/assumption/risk ledgers."
    )
    ap.add_argument(
        "--discovery-governance",
        required=True,
        help="path to M10 discovery governance report",
    )
    ap.add_argument(
        "--contract-report",
        required=True,
        help="path to M11 contract promotion report",
    )
    ap.add_argument(
        "--registry-report",
        required=True,
        help="path to M13 parameter registry report",
    )
    ap.add_argument(
        "--fit-report",
        required=True,
        help="path to M13 fit analysis report",
    )
    ap.add_argument(
        "--validator-expansion-report",
        required=True,
        help="path to M13 validator expansion report",
    )
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m13-pipeline-governance", help="report label")
    ap.add_argument(
        "--required-corpus-dir",
        default="out/m9_full_description_uplift/run1",
        help="required single corpus directory used by M13 workflow",
    )
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum total source files")
    ap.add_argument(
        "--min-priority-keys",
        type=int,
        default=10,
        help="minimum targeted priority keys expected in M13 fit/validator reports",
    )
    ap.add_argument(
        "--min-expanded-rules",
        type=int,
        default=10,
        help="minimum expanded validator rules expected",
    )
    ap.add_argument(
        "--min-priority-coverage-ratio",
        type=float,
        default=1.0,
        help="minimum mapping ratio from targeted priority keys to expanded rules",
    )
    ap.add_argument(
        "--min-decision-count",
        type=int,
        default=5,
        help="minimum decision registry entries required",
    )
    ap.add_argument(
        "--min-assumption-count",
        type=int,
        default=5,
        help="minimum assumption registry entries required",
    )
    ap.add_argument(
        "--min-risk-count",
        type=int,
        default=5,
        help="minimum risk ledger entries required",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m13_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y"}:
            return True
        if v in {"0", "false", "no", "n"}:
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


def build_decision_registry(
    required_corpus_dir: str,
    targeted_priority_keys: list[str],
    mapped_priority_keys: list[str],
    expressive_expansion_files: int,
    rule_failures: int,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M13-DEC-001",
            "decision": "Single promoted corpus path for M13 execution",
            "chosenOption": f"use {required_corpus_dir} as sole corpus input for registry and validator expansion",
            "alternativesConsidered": [
                "mix legacy subset directories with promoted corpus",
                "use per-formation branch-specific corpus paths",
            ],
            "tradeoffs": [
                "pro: prevents hidden subset drift",
                "con: requires full-corpus consistency before promotions",
            ],
            "reversalCondition": "if promoted corpus path changes in plan.json, update governance target and gate thresholds together",
        },
        {
            "id": "M13-DEC-002",
            "decision": "Dual fit-model strategy retained",
            "chosenOption": "keep contract-presence and expressive-coverage models in one fit report",
            "alternativesConsidered": [
                "track only core presence fit",
                "track only expressive fit and remove core model",
            ],
            "tradeoffs": [
                "pro: preserves backward compatibility while exposing real depth gaps",
                "con: requires stakeholders to interpret two fit views",
            ],
            "reversalCondition": "if expressive model and presence model converge for three milestones, simplify to one model",
        },
        {
            "id": "M13-DEC-003",
            "decision": "Priority-driven validator expansion",
            "chosenOption": f"derive expanded rules from P0/P1 backlog and require full key mapping ({len(mapped_priority_keys)}/{len(targeted_priority_keys)})",
            "alternativesConsidered": [
                "add ad-hoc rules not tied to fit backlog",
                "enforce all possible rules immediately regardless of mapping",
            ],
            "tradeoffs": [
                "pro: direct traceability from gap detection to validator behavior",
                "con: priority extraction quality directly affects rule roadmap",
            ],
            "reversalCondition": "if priority mapping ratio drops below threshold, halt promotion until backlog mapping is restored",
        },
        {
            "id": "M13-DEC-004",
            "decision": "Expose failures instead of auto-pass masking",
            "chosenOption": f"allow report PASS with surfaced failures ({rule_failures}) while keeping taxonomy mandatory",
            "alternativesConsidered": [
                "force zero rule failures before any governance PASS",
                "suppress failing rules until data quality improves",
            ],
            "tradeoffs": [
                "pro: preserves reality contact and transparent backlog",
                "con: requires disciplined remediation planning to avoid normalization of failures",
            ],
            "reversalCondition": "if remediation KPI is defined, tighten gate to cap allowed failures by milestone target",
        },
        {
            "id": "M13-DEC-005",
            "decision": "Embed governance logs in machine-readable artifact",
            "chosenOption": "emit decision registry, assumption registry, and risk ledger inside m13 pipeline governance report",
            "alternativesConsidered": [
                "store logs only in prose docs",
                "store each ledger in separate unlinked files",
            ],
            "tradeoffs": [
                "pro: one deterministic source of governance truth for pipeline checks",
                "con: report schema grows and needs version discipline",
            ],
            "reversalCondition": "if report size or coupling becomes problematic, split ledgers with explicit references and hash linkage",
        },
        {
            "id": "M13-DEC-006",
            "decision": "Treat expressive expansion count as strategic signal",
            "chosenOption": f"carry filesExpressiveRequiringContractExpansion={expressive_expansion_files} as a first-class planning metric",
            "alternativesConsidered": [
                "ignore expressive expansion count and rely on rule failures only",
                "convert expressive expansion count into hard-fail immediately",
            ],
            "tradeoffs": [
                "pro: anchors roadmap to measurable depth gaps",
                "con: can fluctuate with model changes and requires interpretation",
            ],
            "reversalCondition": "if expressive expansion metric becomes unstable, redefine with fixed denominator categories",
        },
    ]


def build_assumption_registry(
    required_corpus_dir: str,
    priority_coverage_ratio: float,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "M13-ASM-001",
            "assumption": "Promoted corpus directory remains the canonical single execution path",
            "confidence": 0.9,
            "verificationPlan": f"validate all M13 targets reference {required_corpus_dir} and no subset alternatives",
            "invalidationSignal": "make targets or reports reference additional corpus branches",
        },
        {
            "id": "M13-ASM-002",
            "assumption": "P0/P1 priority keys are sufficient to seed the next validator expansion wave",
            "confidence": 0.8,
            "verificationPlan": "check mapping coverage ratio from targeted keys to expanded rules every run",
            "invalidationSignal": f"priority coverage ratio falls below baseline ({priority_coverage_ratio:.4f})",
        },
        {
            "id": "M13-ASM-003",
            "assumption": "Placeholder context detection captures low-specificity metadata reliably",
            "confidence": 0.7,
            "verificationPlan": "sample false-positive and false-negative context labels against source evidence",
            "invalidationSignal": "high disagreement rate in manual audit samples",
        },
        {
            "id": "M13-ASM-004",
            "assumption": "Failure taxonomy emitted by expanded rules is stable enough for remediation planning",
            "confidence": 0.75,
            "verificationPlan": "track top failure code churn over successive runs",
            "invalidationSignal": "taxonomy code volatility exceeds governance threshold",
        },
        {
            "id": "M13-ASM-005",
            "assumption": "Rule applicability remains broad across full corpus and no rule becomes dead/unused",
            "confidence": 0.85,
            "verificationPlan": "enforce all_rules_have_applicability check each run",
            "invalidationSignal": "one or more expanded rules have zero applicable files",
        },
        {
            "id": "M13-ASM-006",
            "assumption": "Decision, assumption, and risk logs in governance artifact are sufficient to prevent silent drift",
            "confidence": 0.8,
            "verificationPlan": "require non-empty ledgers and check updates when queue changes",
            "invalidationSignal": "queue advances without corresponding governance ledger updates",
        },
    ]


def build_risk_ledger(
    expressive_expansion_files: int,
    rule_failures: int,
    context_gap_files: int,
    targeted_priority_keys: int,
    mapped_priority_keys: int,
) -> list[dict[str, Any]]:
    coverage_ratio = (
        1.0
        if targeted_priority_keys <= 0
        else float(mapped_priority_keys) / float(targeted_priority_keys)
    )
    return [
        {
            "id": "M13-RSK-001",
            "risk": "High expressive-gap footprint across corpus",
            "severity": "high",
            "likelihood": "high",
            "signal": f"filesExpressiveRequiringContractExpansion={expressive_expansion_files}",
            "mitigation": "prioritize P0 movement/context keys before adding lower-impact rule families",
            "owner": "pipeline",
        },
        {
            "id": "M13-RSK-002",
            "risk": "Large active failure backlog in expanded validator stack",
            "severity": "high",
            "likelihood": "high",
            "signal": f"ruleFailures={rule_failures}",
            "mitigation": "use taxonomy counts to sequence remediation work and track burn-down trend",
            "owner": "validator",
        },
        {
            "id": "M13-RSK-003",
            "risk": "Context specificity remains placeholder-dominated",
            "severity": "high",
            "likelihood": "high",
            "signal": f"filesWithContextSpecificityGap={context_gap_files}",
            "mitigation": "upgrade origin extraction/normalization with evidence checks before strict context gating",
            "owner": "ingest",
        },
        {
            "id": "M13-RSK-004",
            "risk": "Priority-to-rule mapping drift",
            "severity": "medium",
            "likelihood": "medium",
            "signal": f"priorityCoverageRatio={coverage_ratio:.4f} ({mapped_priority_keys}/{targeted_priority_keys})",
            "mitigation": "block governance pass when targeted keys are unmapped",
            "owner": "governance",
        },
        {
            "id": "M13-RSK-005",
            "risk": "Workflow split risk from subset-specific execution branches",
            "severity": "medium",
            "likelihood": "medium",
            "signal": "Makefile targets may diverge from single-corpus path over time",
            "mitigation": "enforce corpus-path invariants in governance gate and CI wiring",
            "owner": "build",
        },
        {
            "id": "M13-RSK-006",
            "risk": "Governance artifact becomes stale relative to active queue",
            "severity": "medium",
            "likelihood": "low",
            "signal": "queue change without governance rerun",
            "mitigation": "keep m13-pipeline-governance-check runnable as standard step and include in CI",
            "owner": "program",
        },
    ]


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_priority_keys <= 0:
        return fail("--min-priority-keys must be > 0")
    if args.min_expanded_rules <= 0:
        return fail("--min-expanded-rules must be > 0")
    if not (0.0 <= args.min_priority_coverage_ratio <= 1.0):
        return fail("--min-priority-coverage-ratio must be in [0,1]")
    if args.min_decision_count <= 0:
        return fail("--min-decision-count must be > 0")
    if args.min_assumption_count <= 0:
        return fail("--min-assumption-count must be > 0")
    if args.min_risk_count <= 0:
        return fail("--min-risk-count must be > 0")

    discovery_path = Path(args.discovery_governance)
    contract_path = Path(args.contract_report)
    registry_path = Path(args.registry_report)
    fit_path = Path(args.fit_report)
    validator_path = Path(args.validator_expansion_report)
    makefile_path = Path(args.makefile)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (discovery_path, "--discovery-governance"),
        (contract_path, "--contract-report"),
        (registry_path, "--registry-report"),
        (fit_path, "--fit-report"),
        (validator_path, "--validator-expansion-report"),
        (makefile_path, "--makefile"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    try:
        discovery = load_json(discovery_path)
        contract = load_json(contract_path)
        registry = load_json(registry_path)
        fit = load_json(fit_path)
        validator = load_json(validator_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_corpus_dir = normalize_path(str(args.required_corpus_dir))
    required_prefix = required_corpus_dir + "/"

    discovery_ok = as_bool(discovery.get("ok"), False)
    discovery_totals = as_dict(discovery.get("totals"))
    discovery_source = as_int(discovery_totals.get("sourceFiles"), 0)
    discovery_processed = as_int(discovery_totals.get("processedFiles"), 0)
    discovery_unresolved = as_int(discovery_totals.get("coverageUnresolvedFiles"), 0)

    contract_totals = as_dict(contract.get("totals"))
    accepted_rows = as_int(contract_totals.get("acceptedRows"), 0)
    promoted_fields = as_int(contract_totals.get("promotedFields"), 0)
    unknown_key_count = as_int(contract_totals.get("unknownKeyCount"), 0)
    decision_registry = as_list(contract.get("decisionRegistry"))

    registry_totals = as_dict(registry.get("totals"))
    registry_input_dir = normalize_path(str(registry.get("inputDir") or ""))
    registry_source = as_int(registry_totals.get("sourceFiles"), 0)
    registry_processed = as_int(registry_totals.get("processedFiles"), 0)
    unique_keys_with_support = as_int(registry_totals.get("uniqueKeysWithSupport"), 0)
    core_key_count = as_int(registry_totals.get("coreKeyCount"), 0)
    core_keys_with_support = as_int(registry_totals.get("coreKeysWithSupport"), 0)

    fit_input_dir = normalize_path(str(fit.get("inputDir") or ""))
    fit_totals = as_dict(fit.get("totals"))
    fit_source = as_int(fit_totals.get("sourceFiles"), 0)
    fit_processed = as_int(fit_totals.get("processedFiles"), 0)
    expressive_expansion_files = as_int(
        fit_totals.get("filesExpressiveRequiringContractExpansion"), 0
    )
    context_specificity = as_dict(fit.get("contextSpecificity"))
    context_gap_files = as_int(context_specificity.get("filesWithContextSpecificityGap"), 0)
    priority_rows = as_list(fit.get("contractExpansionPriorities"))
    targeted_priority_keys = sorted(
        {
            str(as_dict(row).get("key") or "")
            for row in priority_rows
            if str(as_dict(row).get("tier") or "") in {"P0", "P1"}
            and str(as_dict(row).get("key") or "")
        }
    )

    validator_ok = as_bool(validator.get("ok"), False)
    validator_inputs = as_dict(validator.get("inputs"))
    validator_corpus_dir = normalize_path(str(validator_inputs.get("corpusDir") or ""))
    validator_totals = as_dict(validator.get("totals"))
    validator_source = as_int(validator_totals.get("sourceFiles"), 0)
    validator_processed = as_int(validator_totals.get("processedFiles"), 0)
    validator_rule_count = as_int(validator_totals.get("ruleCount"), 0)
    validator_rule_failures = as_int(validator_totals.get("ruleFailures"), 0)
    priority_coverage = as_dict(validator.get("priorityCoverage"))
    mapped_priority_keys = sorted(
        [
            str(x)
            for x in as_list(priority_coverage.get("mappedKeys"))
            if str(x).strip()
        ]
    )
    missing_priority_keys = sorted(
        [
            str(x)
            for x in as_list(priority_coverage.get("missingKeys"))
            if str(x).strip()
        ]
    )
    coverage_ratio = clamp01(as_float(priority_coverage.get("coverageRatio"), 0.0))

    make_text = makefile_path.read_text(encoding="utf-8")
    ci_line = extract_make_target_line(make_text, "ci")
    m13_registry_block = extract_make_target_block(make_text, "m13-parameter-registry-check")
    m13_validator_block = extract_make_target_block(make_text, "m13-validator-expansion-check")
    m13_governance_block = extract_make_target_block(make_text, "m13-pipeline-governance-check")

    decisions = build_decision_registry(
        required_corpus_dir=required_corpus_dir,
        targeted_priority_keys=targeted_priority_keys,
        mapped_priority_keys=mapped_priority_keys,
        expressive_expansion_files=expressive_expansion_files,
        rule_failures=validator_rule_failures,
    )
    assumptions = build_assumption_registry(
        required_corpus_dir=required_corpus_dir,
        priority_coverage_ratio=coverage_ratio,
    )
    risks = build_risk_ledger(
        expressive_expansion_files=expressive_expansion_files,
        rule_failures=validator_rule_failures,
        context_gap_files=context_gap_files,
        targeted_priority_keys=len(targeted_priority_keys),
        mapped_priority_keys=len(mapped_priority_keys),
    )

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        print(("PASS" if ok else "FAIL") + f" {check_id}: {detail}")

    add_check(
        "m10_discovery_governance_ok",
        discovery_ok,
        f"discovery_ok={discovery_ok}",
    )
    add_check(
        "m10_discovery_counts_min",
        discovery_source >= args.min_total_files and discovery_processed >= args.min_total_files,
        f"source={discovery_source} processed={discovery_processed} min={args.min_total_files}",
    )
    add_check(
        "m10_unresolved_files_zero",
        discovery_unresolved == 0,
        f"unresolved={discovery_unresolved}",
    )
    add_check(
        "m11_contract_unknown_keys_zero",
        unknown_key_count == 0,
        f"unknown_key_count={unknown_key_count}",
    )
    add_check(
        "m11_contract_nontrivial",
        accepted_rows >= 4 and promoted_fields >= 4 and len(decision_registry) > 0,
        f"accepted_rows={accepted_rows} promoted_fields={promoted_fields} decision_rows={len(decision_registry)}",
    )
    add_check(
        "m13_registry_counts_min",
        registry_source >= args.min_total_files
        and registry_processed >= args.min_total_files
        and unique_keys_with_support >= 15,
        (
            f"registry_source={registry_source} registry_processed={registry_processed} "
            f"keys_with_support={unique_keys_with_support}"
        ),
    )
    add_check(
        "m13_core_support_complete",
        core_key_count > 0 and core_keys_with_support == core_key_count,
        f"core_support={core_keys_with_support}/{core_key_count}",
    )
    add_check(
        "m13_fit_priority_rows_min",
        len(targeted_priority_keys) >= args.min_priority_keys,
        f"targeted_priority_keys={len(targeted_priority_keys)} min={args.min_priority_keys}",
    )
    add_check(
        "m13_validator_expansion_ok",
        validator_ok,
        f"validator_ok={validator_ok}",
    )
    add_check(
        "m13_validator_counts_min",
        validator_source >= args.min_total_files
        and validator_processed >= args.min_total_files
        and validator_rule_count >= args.min_expanded_rules,
        (
            f"validator_source={validator_source} validator_processed={validator_processed} "
            f"rule_count={validator_rule_count} min_rules={args.min_expanded_rules}"
        ),
    )
    add_check(
        "m13_priority_mapping_ratio_min",
        coverage_ratio >= args.min_priority_coverage_ratio,
        (
            f"coverage_ratio={coverage_ratio:.4f} min={args.min_priority_coverage_ratio:.4f} "
            f"missing_keys={len(missing_priority_keys)}"
        ),
    )
    add_check(
        "m13_priority_mapping_no_missing_keys",
        len(missing_priority_keys) == 0,
        f"missing_priority_keys={len(missing_priority_keys)}",
    )
    add_check(
        "corpus_dir_invariants",
        registry_input_dir == required_corpus_dir
        and fit_input_dir == required_corpus_dir
        and validator_corpus_dir == required_corpus_dir,
        (
            f"registry='{registry_input_dir}' fit='{fit_input_dir}' "
            f"validator='{validator_corpus_dir}' required='{required_corpus_dir}'"
        ),
    )
    add_check(
        "make_targets_use_required_corpus_dir",
        (
            required_corpus_dir in m13_registry_block
            and required_corpus_dir in m13_validator_block
            and required_corpus_dir in m13_governance_block
        ),
        "m13 make targets reference required single corpus dir",
    )
    add_check(
        "make_ci_wires_m13_governance",
        "m13-pipeline-governance-check" in ci_line,
        "ci target includes m13-pipeline-governance-check",
    )
    add_check(
        "make_ci_excludes_legacy_subset_path",
        "corpus/valid_ingest_auto" not in ci_line,
        "ci target excludes legacy subset corpus path",
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

    ok = all(bool(row.get("ok")) for row in checks)

    payload: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "discoveryGovernance": str(discovery_path),
            "contractReport": str(contract_path),
            "registryReport": str(registry_path),
            "fitReport": str(fit_path),
            "validatorExpansionReport": str(validator_path),
            "makefile": str(makefile_path),
        },
        "thresholds": {
            "requiredCorpusDir": required_corpus_dir,
            "requiredCorpusPrefix": required_prefix,
            "minTotalFiles": args.min_total_files,
            "minPriorityKeys": args.min_priority_keys,
            "minExpandedRules": args.min_expanded_rules,
            "minPriorityCoverageRatio": args.min_priority_coverage_ratio,
            "minDecisionCount": args.min_decision_count,
            "minAssumptionCount": args.min_assumption_count,
            "minRiskCount": args.min_risk_count,
        },
        "metrics": {
            "m10SourceFiles": discovery_source,
            "m10ProcessedFiles": discovery_processed,
            "m10UnresolvedFiles": discovery_unresolved,
            "m11AcceptedRows": accepted_rows,
            "m11PromotedFields": promoted_fields,
            "m11UnknownKeyCount": unknown_key_count,
            "m13RegistrySourceFiles": registry_source,
            "m13RegistryProcessedFiles": registry_processed,
            "m13UniqueKeysWithSupport": unique_keys_with_support,
            "m13CoreSupport": {
                "coreKeyCount": core_key_count,
                "coreKeysWithSupport": core_keys_with_support,
            },
            "m13FitSourceFiles": fit_source,
            "m13FitProcessedFiles": fit_processed,
            "m13ExpressiveExpansionFiles": expressive_expansion_files,
            "m13ContextGapFiles": context_gap_files,
            "m13TargetedPriorityKeys": len(targeted_priority_keys),
            "m13MappedPriorityKeys": len(mapped_priority_keys),
            "m13PriorityCoverageRatio": round(coverage_ratio, 6),
            "m13ValidatorRuleCount": validator_rule_count,
            "m13ValidatorRuleFailures": validator_rule_failures,
        },
        "priorityMapping": {
            "targetedKeys": targeted_priority_keys,
            "mappedKeys": mapped_priority_keys,
            "missingKeys": missing_priority_keys,
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

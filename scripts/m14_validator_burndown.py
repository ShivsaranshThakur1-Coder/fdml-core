#!/usr/bin/env python3
"""Deterministic M14 validator failure burn-down gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Compare baseline and post-remediation validator reports and enforce burn-down targets."
    )
    ap.add_argument(
        "--baseline-report",
        default="out/m13_validator_expansion_report.json",
        help="baseline validator expansion report",
    )
    ap.add_argument(
        "--current-report",
        default="out/m14_validator_expansion_report.json",
        help="current validator expansion report",
    )
    ap.add_argument(
        "--report-out",
        default="out/m14_validator_burndown_report.json",
        help="burn-down report output path",
    )
    ap.add_argument(
        "--label",
        default="m14-validator-burndown-live",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum files expected in current validator run",
    )
    ap.add_argument(
        "--min-rule-count",
        type=int,
        default=10,
        help="minimum expanded rule count expected in current validator run",
    )
    ap.add_argument(
        "--min-reduction-ratio",
        type=float,
        default=0.70,
        help="minimum required reduction ratio in [0,1]",
    )
    ap.add_argument(
        "--max-files-with-fail-ratio",
        type=float,
        default=0.30,
        help="maximum allowed ratio of files with any validator failure in [0,1]",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m14_validator_burndown.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def taxonomy_map(payload: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in as_list(payload.get("failureTaxonomy")):
        row_dict = as_dict(row)
        code = str(row_dict.get("code") or "").strip()
        if not code:
            continue
        try:
            out[code] = int(row_dict.get("count") or 0)
        except Exception:
            out[code] = 0
    return out


def check_ok(payload: dict[str, Any], check_id: str) -> bool:
    for row in as_list(payload.get("checks")):
        row_dict = as_dict(row)
        if str(row_dict.get("id") or "").strip() != check_id:
            continue
        return bool(row_dict.get("ok"))
    return False


def main() -> int:
    args = parse_args()
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_rule_count <= 0:
        return fail("--min-rule-count must be > 0")
    if not (0.0 <= args.min_reduction_ratio <= 1.0):
        return fail("--min-reduction-ratio must be between 0 and 1")
    if not (0.0 <= args.max_files_with_fail_ratio <= 1.0):
        return fail("--max-files-with-fail-ratio must be between 0 and 1")

    baseline_path = Path(args.baseline_report)
    current_path = Path(args.current_report)
    report_out = Path(args.report_out)
    if not baseline_path.exists():
        return fail(f"baseline report not found: {baseline_path}")
    if not current_path.exists():
        return fail(f"current report not found: {current_path}")

    baseline = load_json(baseline_path)
    current = load_json(current_path)

    base_totals = as_dict(baseline.get("totals"))
    curr_totals = as_dict(current.get("totals"))

    baseline_failures = int(base_totals.get("ruleFailures") or 0)
    current_failures = int(curr_totals.get("ruleFailures") or 0)
    failure_reduction = baseline_failures - current_failures
    failure_reduction_ratio = (
        float(failure_reduction) / float(baseline_failures) if baseline_failures > 0 else 0.0
    )

    current_source_files = int(curr_totals.get("sourceFiles") or 0)
    current_processed_files = int(curr_totals.get("processedFiles") or 0)
    current_rule_count = int(curr_totals.get("ruleCount") or 0)
    current_failure_files = int(curr_totals.get("filesWithAnyRuleFailure") or 0)
    failure_file_ratio = (
        float(current_failure_files) / float(current_processed_files)
        if current_processed_files > 0
        else 0.0
    )

    baseline_tax = taxonomy_map(baseline)
    current_tax = taxonomy_map(current)
    tax_rows: list[dict[str, Any]] = []
    for code in sorted(set(baseline_tax.keys()) | set(current_tax.keys())):
        b = int(baseline_tax.get(code, 0))
        c = int(current_tax.get(code, 0))
        delta = b - c
        ratio = (float(delta) / float(b)) if b > 0 else 0.0
        tax_rows.append(
            {
                "code": code,
                "baselineCount": b,
                "currentCount": c,
                "reductionCount": delta,
                "reductionRatio": round(clamp_ratio(ratio), 6) if b > 0 else 0.0,
            }
        )

    checks = [
        {
            "id": "baseline_report_ok",
            "ok": bool(baseline.get("ok")),
            "detail": f"baseline_ok={bool(baseline.get('ok'))}",
        },
        {
            "id": "current_report_ok",
            "ok": bool(current.get("ok")),
            "detail": f"current_ok={bool(current.get('ok'))}",
        },
        {
            "id": "current_files_min",
            "ok": current_source_files >= args.min_total_files,
            "detail": f"source_files={current_source_files} min={args.min_total_files}",
        },
        {
            "id": "current_processed_full",
            "ok": current_processed_files >= args.min_total_files,
            "detail": f"processed_files={current_processed_files} min={args.min_total_files}",
        },
        {
            "id": "current_rules_min",
            "ok": current_rule_count >= args.min_rule_count,
            "detail": f"rule_count={current_rule_count} min={args.min_rule_count}",
        },
        {
            "id": "rules_have_applicability",
            "ok": check_ok(current, "all_rules_have_applicability"),
            "detail": "all_rules_have_applicability must be true",
        },
        {
            "id": "priority_mapping_complete",
            "ok": check_ok(current, "priority_key_mapping_complete"),
            "detail": "priority_key_mapping_complete must be true",
        },
        {
            "id": "failure_reduction_ratio_min",
            "ok": failure_reduction_ratio >= args.min_reduction_ratio,
            "detail": (
                f"baseline_failures={baseline_failures} current_failures={current_failures} "
                f"reduction_ratio={round(clamp_ratio(failure_reduction_ratio), 6)} "
                f"min={args.min_reduction_ratio}"
            ),
        },
        {
            "id": "failure_file_ratio_max",
            "ok": failure_file_ratio <= args.max_files_with_fail_ratio,
            "detail": (
                f"files_with_any_failure={current_failure_files} processed={current_processed_files} "
                f"ratio={round(clamp_ratio(failure_file_ratio), 6)} max={args.max_files_with_fail_ratio}"
            ),
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "baselineReport": str(baseline_path),
            "currentReport": str(current_path),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minRuleCount": args.min_rule_count,
            "minReductionRatio": args.min_reduction_ratio,
            "maxFilesWithFailRatio": args.max_files_with_fail_ratio,
        },
        "totals": {
            "baselineRuleFailures": baseline_failures,
            "currentRuleFailures": current_failures,
            "failureReduction": failure_reduction,
            "failureReductionRatio": round(clamp_ratio(failure_reduction_ratio), 6),
            "currentSourceFiles": current_source_files,
            "currentProcessedFiles": current_processed_files,
            "currentRuleCount": current_rule_count,
            "currentFilesWithAnyRuleFailure": current_failure_files,
            "currentFailureFileRatio": round(clamp_ratio(failure_file_ratio), 6),
            "baselineTaxonomyCodeCount": len(baseline_tax),
            "currentTaxonomyCodeCount": len(current_tax),
        },
        "taxonomyBurndown": tax_rows,
        "checks": checks,
        "ok": ok,
    }
    write_json(report_out, report)
    status = "PASS" if ok else "FAIL"
    print(
        f"M14 VALIDATOR BURNDOWN {status} "
        f"baseline_failures={baseline_failures} current_failures={current_failures} "
        f"reduction_ratio={round(clamp_ratio(failure_reduction_ratio), 4)} "
        f"failure_file_ratio={round(clamp_ratio(failure_file_ratio), 4)}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

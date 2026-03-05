#!/usr/bin/env python3
"""Governance gate for M12 semantic depth and validator-rule depth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate folk-dance semantic depth and rule-depth readiness from discovery and validator artifacts."
    )
    ap.add_argument(
        "--discovery-report",
        required=True,
        help="path to m10 discovery report (with perFileChecklistResolution)",
    )
    ap.add_argument(
        "--ontology-candidates",
        required=True,
        help="path to ontology candidate report",
    )
    ap.add_argument(
        "--validator-candidates",
        required=True,
        help="path to validator candidate report",
    )
    ap.add_argument(
        "--contract-promotion",
        required=True,
        help="path to m11 contract promotion report",
    )
    ap.add_argument(
        "--validator-unified",
        required=True,
        help="path to m11 unified validator report",
    )
    ap.add_argument(
        "--rubric",
        required=True,
        help="path to M12 semantic rubric JSON",
    )
    ap.add_argument(
        "--report-out",
        default="out/m12_semantic_depth_report.json",
        help="output path for gate report",
    )
    ap.add_argument(
        "--label",
        default="m12-semantic-depth",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum source and processed file count expected from discovery",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m12_semantic_depth_gate.py: {msg}", file=sys.stderr)
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
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    return default


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_checklist_status_map(row: dict[str, Any]) -> dict[str, str]:
    checklist = row.get("checklist")
    out: dict[str, str] = {}
    if isinstance(checklist, list):
        for item in checklist:
            if not isinstance(item, dict):
                continue
            dim = str(item.get("dimension") or "").strip()
            status = str(item.get("status") or "").strip().lower()
            if dim:
                out[dim] = status
        return out
    if isinstance(checklist, dict):
        for key, value in checklist.items():
            dim = str(key).strip()
            status = str(value or "").strip().lower()
            if dim:
                out[dim] = status
        return out
    return out


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")

    discovery_path = Path(args.discovery_report)
    ontology_path = Path(args.ontology_candidates)
    validator_candidates_path = Path(args.validator_candidates)
    contract_path = Path(args.contract_promotion)
    validator_unified_path = Path(args.validator_unified)
    rubric_path = Path(args.rubric)
    report_out = Path(args.report_out)

    for p, flag in (
        (discovery_path, "--discovery-report"),
        (ontology_path, "--ontology-candidates"),
        (validator_candidates_path, "--validator-candidates"),
        (contract_path, "--contract-promotion"),
        (validator_unified_path, "--validator-unified"),
        (rubric_path, "--rubric"),
    ):
        if not p.exists():
            return fail(f"missing {flag}: {p}")

    try:
        discovery = load_json(discovery_path)
        ontology = load_json(ontology_path)
        validator_candidates = load_json(validator_candidates_path)
        contract = load_json(contract_path)
        validator_unified = load_json(validator_unified_path)
        rubric = load_json(rubric_path)
    except Exception as exc:
        return fail(f"failed to parse input JSON: {exc}")

    rubric_dims: list[dict[str, Any]] = []
    for item in as_list(rubric.get("dimensions")):
        row = as_dict(item)
        dim_id = str(row.get("id") or "").strip()
        if not dim_id:
            continue
        min_cov = clamp01(as_float(row.get("minCoverage"), 0.0))
        rubric_dims.append({"id": dim_id, "minCoverage": min_cov})

    if not rubric_dims:
        return fail("rubric has no valid dimensions")

    dim_ids = [str(d["id"]) for d in rubric_dims]
    dim_min_cov = {str(d["id"]): clamp01(as_float(d.get("minCoverage"), 0.0)) for d in rubric_dims}

    global_thresholds = as_dict(rubric.get("globalThresholds"))
    rule_thresholds = as_dict(rubric.get("ruleDepthThresholds"))

    min_avg_dim_coverage = clamp01(as_float(global_thresholds.get("minAverageDimensionCoverage"), 0.0))
    min_present_dims_per_file = as_int(global_thresholds.get("minPresentDimensionsPerFile"), 0)
    min_file_ratio_with_min_dims = clamp01(
        as_float(global_thresholds.get("minFilesMeetingPerFileThresholdRatio"), 0.0)
    )
    max_zero_coverage_dimensions = as_int(
        global_thresholds.get("maxZeroCoverageDimensions"),
        len(dim_ids),
    )

    min_ontology_candidates = as_int(rule_thresholds.get("minOntologyCandidates"), 0)
    min_validator_candidates = as_int(rule_thresholds.get("minValidatorCandidates"), 0)
    min_promoted_contract_fields = as_int(rule_thresholds.get("minPromotedContractFields"), 0)
    min_recognized_rules = as_int(rule_thresholds.get("minRecognizedRules"), 0)

    if min_present_dims_per_file < 0:
        return fail("rubric globalThresholds.minPresentDimensionsPerFile must be >= 0")
    if max_zero_coverage_dimensions < 0:
        return fail("rubric globalThresholds.maxZeroCoverageDimensions must be >= 0")

    discovery_totals = as_dict(discovery.get("totals"))
    source_files = as_int(discovery_totals.get("sourceFiles"), 0)
    processed_files = as_int(discovery_totals.get("processedFiles"), 0)
    file_rows = as_list(discovery.get("perFileChecklistResolution"))
    if source_files <= 0:
        source_files = len(file_rows)
    if processed_files <= 0:
        processed_files = len(file_rows)

    dimension_present_counts = {dim: 0 for dim in dim_ids}
    present_dims_per_file: list[int] = []

    for item in file_rows:
        row = as_dict(item)
        status_map = parse_checklist_status_map(row)
        present_count = 0
        for dim in dim_ids:
            if status_map.get(dim) == "present":
                dimension_present_counts[dim] += 1
                present_count += 1
        present_dims_per_file.append(present_count)

    coverage_denominator = len(file_rows) if file_rows else max(source_files, processed_files, 1)
    dimension_coverage = {
        dim: float(dimension_present_counts[dim]) / float(coverage_denominator) for dim in dim_ids
    }

    avg_dimension_coverage = (
        sum(dimension_coverage.values()) / float(len(dim_ids)) if dim_ids else 0.0
    )

    files_meeting_min_dims = sum(1 for count in present_dims_per_file if count >= min_present_dims_per_file)
    files_meeting_min_dims_ratio = (
        float(files_meeting_min_dims) / float(len(present_dims_per_file))
        if present_dims_per_file
        else 0.0
    )

    zero_coverage_dimensions = sorted([dim for dim in dim_ids if dimension_coverage[dim] <= 0.0])

    ontology_totals = as_dict(ontology.get("totals"))
    ontology_rows = as_int(ontology_totals.get("rows"), len(as_list(ontology.get("rows"))))
    validator_candidate_totals = as_dict(validator_candidates.get("totals"))
    validator_candidate_rows = as_int(
        validator_candidate_totals.get("rows"), len(as_list(validator_candidates.get("rows")))
    )
    contract_totals = as_dict(contract.get("totals"))
    promoted_fields = as_int(contract_totals.get("promotedFields"), 0)
    accepted_contract_rows = as_int(contract_totals.get("acceptedRows"), 0)
    validator_unified_totals = as_dict(validator_unified.get("totals"))
    recognized_rules = as_int(validator_unified_totals.get("recognizedRules"), 0)
    rule_failures = as_int(validator_unified_totals.get("ruleFailures"), 0)
    validator_unified_ok = as_bool(validator_unified.get("ok"), False)

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        status = "PASS" if ok else "FAIL"
        print(f"{status} {check_id}: {detail}")

    add_check(
        "source_files_min",
        source_files >= args.min_total_files,
        f"source_files={source_files} min={args.min_total_files}",
    )
    add_check(
        "processed_files_min",
        processed_files >= args.min_total_files,
        f"processed_files={processed_files} min={args.min_total_files}",
    )
    add_check(
        "rubric_dimensions_min",
        len(dim_ids) >= 1,
        f"rubric_dimensions={len(dim_ids)}",
    )

    for dim in dim_ids:
        cov = dimension_coverage[dim]
        min_cov = dim_min_cov[dim]
        add_check(
            f"dimension_coverage:{dim}",
            cov >= min_cov,
            f"coverage={cov:.4f} min={min_cov:.4f} ({dimension_present_counts[dim]}/{coverage_denominator})",
        )

    add_check(
        "average_dimension_coverage_min",
        avg_dimension_coverage >= min_avg_dim_coverage,
        f"average_coverage={avg_dimension_coverage:.4f} min={min_avg_dim_coverage:.4f}",
    )
    add_check(
        "files_meeting_min_dimensions_ratio_min",
        files_meeting_min_dims_ratio >= min_file_ratio_with_min_dims,
        (
            f"ratio={files_meeting_min_dims_ratio:.4f} min={min_file_ratio_with_min_dims:.4f} "
            f"({files_meeting_min_dims}/{len(present_dims_per_file)})"
        ),
    )
    add_check(
        "zero_coverage_dimensions_max",
        len(zero_coverage_dimensions) <= max_zero_coverage_dimensions,
        (
            f"zero_coverage_dimensions={len(zero_coverage_dimensions)} "
            f"max={max_zero_coverage_dimensions}"
        ),
    )
    add_check(
        "ontology_candidates_min",
        ontology_rows >= min_ontology_candidates,
        f"ontology_candidates={ontology_rows} min={min_ontology_candidates}",
    )
    add_check(
        "validator_candidates_min",
        validator_candidate_rows >= min_validator_candidates,
        f"validator_candidates={validator_candidate_rows} min={min_validator_candidates}",
    )
    add_check(
        "promoted_contract_fields_min",
        promoted_fields >= min_promoted_contract_fields,
        f"promoted_contract_fields={promoted_fields} min={min_promoted_contract_fields}",
    )
    add_check(
        "recognized_rules_min",
        recognized_rules >= min_recognized_rules,
        f"recognized_rules={recognized_rules} min={min_recognized_rules}",
    )
    add_check(
        "validator_unified_ok",
        validator_unified_ok,
        f"validator_unified_ok={validator_unified_ok}",
    )
    add_check(
        "validator_rule_failures_zero",
        rule_failures == 0,
        f"rule_failures={rule_failures}",
    )

    ok = all(bool(c["ok"]) for c in checks)

    dimension_rows = [
        {
            "id": dim,
            "presentFiles": dimension_present_counts[dim],
            "coverage": round(dimension_coverage[dim], 6),
            "minCoverage": round(dim_min_cov[dim], 6),
        }
        for dim in dim_ids
    ]

    payload: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "discoveryReport": str(discovery_path),
            "ontologyCandidates": str(ontology_path),
            "validatorCandidates": str(validator_candidates_path),
            "contractPromotion": str(contract_path),
            "validatorUnified": str(validator_unified_path),
            "rubric": str(rubric_path),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minAverageDimensionCoverage": min_avg_dim_coverage,
            "minPresentDimensionsPerFile": min_present_dims_per_file,
            "minFilesMeetingPerFileThresholdRatio": min_file_ratio_with_min_dims,
            "maxZeroCoverageDimensions": max_zero_coverage_dimensions,
            "minOntologyCandidates": min_ontology_candidates,
            "minValidatorCandidates": min_validator_candidates,
            "minPromotedContractFields": min_promoted_contract_fields,
            "minRecognizedRules": min_recognized_rules,
        },
        "metrics": {
            "sourceFiles": source_files,
            "processedFiles": processed_files,
            "coverageDenominator": coverage_denominator,
            "rubricDimensions": len(dim_ids),
            "averageDimensionCoverage": round(avg_dimension_coverage, 6),
            "filesMeetingMinDimensions": files_meeting_min_dims,
            "filesMeetingMinDimensionsRatio": round(files_meeting_min_dims_ratio, 6),
            "zeroCoverageDimensions": len(zero_coverage_dimensions),
            "zeroCoverageDimensionIds": zero_coverage_dimensions,
            "ontologyCandidates": ontology_rows,
            "validatorCandidates": validator_candidate_rows,
            "acceptedContractRows": accepted_contract_rows,
            "promotedContractFields": promoted_fields,
            "recognizedRules": recognized_rules,
            "validatorUnifiedOk": validator_unified_ok,
            "validatorRuleFailures": rule_failures,
        },
        "dimensions": dimension_rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, payload)
    print(f"Created: {report_out}")

    if ok:
        print("Summary: PASS")
        return 0
    print("Summary: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

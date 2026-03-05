#!/usr/bin/env python3
"""Governance gate for M10 corpus-wide discovery saturation and evidence quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate M10 discovery reports for coverage, saturation, and candidate evidence quality."
    )
    ap.add_argument(
        "--discovery-report",
        required=True,
        help="path to corpus-wide discovery report (for example out/m10_discovery/run1/discovery_report.json)",
    )
    ap.add_argument(
        "--ontology-candidates",
        required=True,
        help="path to ontology/FDML parameter candidate report",
    )
    ap.add_argument(
        "--validator-candidates",
        required=True,
        help="path to validator rule candidate report",
    )
    ap.add_argument(
        "--coverage-gaps",
        required=True,
        help="path to coverage gap report",
    )
    ap.add_argument(
        "--report-out",
        default="",
        help="optional governance report output path",
    )
    ap.add_argument(
        "--label",
        default="m10-discovery-governance",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum corpus file count expected in discovery and coverage reports",
    )
    ap.add_argument(
        "--min-pass-count",
        type=int,
        default=3,
        help="minimum discovery passes required",
    )
    ap.add_argument(
        "--max-growth-ratio",
        type=float,
        default=0.01,
        help="maximum growth ratio considered saturated",
    )
    ap.add_argument(
        "--required-consecutive-saturation",
        type=int,
        default=2,
        help="required number of consecutive full passes under max-growth-ratio",
    )
    ap.add_argument(
        "--max-checklist-missing-ratio",
        type=float,
        default=0.05,
        help="maximum checklist missing ratio allowed",
    )
    ap.add_argument(
        "--max-checklist-uncertain-ratio",
        type=float,
        default=0.1,
        help="maximum checklist uncertain ratio allowed",
    )
    ap.add_argument(
        "--max-unresolved-files",
        type=int,
        default=0,
        help="maximum unresolved files allowed in coverage-gaps report",
    )
    ap.add_argument(
        "--min-parameter-candidates",
        type=int,
        default=1,
        help="minimum ontology/FDML parameter candidates required",
    )
    ap.add_argument(
        "--min-validator-candidates",
        type=int,
        default=1,
        help="minimum validator rule candidates required",
    )
    ap.add_argument(
        "--min-candidate-confidence",
        type=float,
        default=0.6,
        help="minimum confidence required for every accepted candidate in [0,1]",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m10_discovery_governance_gate.py: {msg}", file=sys.stderr)
    return 2


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


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


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def pick_int(node: dict[str, Any], keys: list[str], default: int = 0) -> int:
    for key in keys:
        if key in node:
            return as_int(node.get(key), default)
    return default


def compute_tail_consecutive(values: list[float], threshold: float) -> int:
    count = 0
    for value in reversed(values):
        if value <= threshold:
            count += 1
        else:
            break
    return count


def has_evidence(row: dict[str, Any]) -> bool:
    evidence = as_dict(row.get("evidence"))
    text = str(
        evidence.get("text")
        or evidence.get("quote")
        or row.get("evidenceText")
        or ""
    ).strip()

    span = evidence.get("span")
    if not isinstance(span, dict):
        span = row.get("evidenceSpan")
    span_dict = span if isinstance(span, dict) else {}

    start = span_dict.get("start")
    end = span_dict.get("end")
    if isinstance(start, int) and isinstance(end, int) and start >= 0 and end >= start:
        return bool(text)
    return False


def validate_candidate_rows(
    rows: list[Any], min_confidence: float
) -> tuple[int, int, int, list[dict[str, Any]]]:
    valid = 0
    invalid = 0
    below_conf = 0
    samples: list[dict[str, Any]] = []

    for idx, raw in enumerate(rows):
        row = raw if isinstance(raw, dict) else {}
        file_value = str(row.get("file", "")).strip()
        confidence = as_float(row.get("confidence"), -1.0)

        reasons: list[str] = []
        if not file_value:
            reasons.append("missing_file")
        if confidence < 0.0 or confidence > 1.0:
            reasons.append("invalid_confidence_range")
        if confidence < min_confidence:
            below_conf += 1
            reasons.append("confidence_below_threshold")
        if not has_evidence(row):
            reasons.append("missing_evidence_text_or_span")

        if reasons:
            invalid += 1
            if len(samples) < 15:
                samples.append(
                    {
                        "index": idx,
                        "file": file_value,
                        "confidence": confidence,
                        "reasons": reasons,
                    }
                )
        else:
            valid += 1

    return valid, invalid, below_conf, samples


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_pass_count <= 0:
        return fail("--min-pass-count must be > 0")
    if args.required_consecutive_saturation <= 0:
        return fail("--required-consecutive-saturation must be > 0")
    if args.max_unresolved_files < 0:
        return fail("--max-unresolved-files must be >= 0")
    if args.min_parameter_candidates < 0:
        return fail("--min-parameter-candidates must be >= 0")
    if args.min_validator_candidates < 0:
        return fail("--min-validator-candidates must be >= 0")
    if not (0.0 <= args.max_growth_ratio <= 1.0):
        return fail("--max-growth-ratio must be between 0 and 1")
    if not (0.0 <= args.max_checklist_missing_ratio <= 1.0):
        return fail("--max-checklist-missing-ratio must be between 0 and 1")
    if not (0.0 <= args.max_checklist_uncertain_ratio <= 1.0):
        return fail("--max-checklist-uncertain-ratio must be between 0 and 1")
    if not (0.0 <= args.min_candidate_confidence <= 1.0):
        return fail("--min-candidate-confidence must be between 0 and 1")

    discovery_path = Path(args.discovery_report)
    ontology_path = Path(args.ontology_candidates)
    validator_path = Path(args.validator_candidates)
    gaps_path = Path(args.coverage_gaps)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (discovery_path, "--discovery-report"),
        (ontology_path, "--ontology-candidates"),
        (validator_path, "--validator-candidates"),
        (gaps_path, "--coverage-gaps"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    try:
        discovery = load_json(discovery_path)
        ontology = load_json(ontology_path)
        validator = load_json(validator_path)
        gaps = load_json(gaps_path)
    except Exception as exc:
        return fail(f"failed to parse JSON report(s): {exc}")

    totals = as_dict(discovery.get("totals"))
    source_files = pick_int(totals, ["sourceFiles", "totalFiles", "files"], 0)
    processed_files = pick_int(totals, ["processedFiles", "processed", "processedTotal"], 0)
    checklist_total = pick_int(totals, ["checklistItemsTotal", "checklistTotal"], 0)
    checklist_missing = pick_int(totals, ["checklistMissing", "missingChecklist"], 0)
    checklist_uncertain = pick_int(totals, ["checklistUncertain", "uncertainChecklist"], 0)

    checklist_missing_ratio = (
        float(checklist_missing) / float(checklist_total) if checklist_total > 0 else 1.0
    )
    checklist_uncertain_ratio = (
        float(checklist_uncertain) / float(checklist_total) if checklist_total > 0 else 1.0
    )

    passes = [p for p in as_list(discovery.get("passes")) if isinstance(p, dict)]
    pass_count = len(passes)
    full_pass_count = sum(
        1 for p in passes if as_int(p.get("processedFiles"), 0) >= args.min_total_files
    )

    saturation = as_dict(discovery.get("saturation"))
    growth_values = [
        as_float(v, -1.0)
        for v in as_list(saturation.get("latestGrowthRatios"))
        if isinstance(v, (int, float))
    ]
    if not growth_values:
        growth_values = [
            as_float(p.get("growthRatio"), -1.0)
            for p in passes
            if "growthRatio" in p
        ]
    growth_values = [v for v in growth_values if v >= 0.0]

    consecutive_under = as_int(
        saturation.get("consecutivePassesUnderThreshold"), -1
    )
    if consecutive_under < 0:
        consecutive_under = compute_tail_consecutive(growth_values, args.max_growth_ratio)

    gaps_totals = as_dict(gaps.get("totals"))
    gap_rows = [r for r in as_list(gaps.get("rows")) if isinstance(r, dict)]
    gaps_files = pick_int(gaps_totals, ["files", "sourceFiles", "totalFiles"], len(gap_rows))
    unresolved_files = pick_int(gaps_totals, ["unresolvedFiles", "unresolved"], -1)
    if unresolved_files < 0:
        unresolved_files = sum(as_int(r.get("unresolvedCount"), 0) > 0 for r in gap_rows)

    ontology_rows = [r for r in as_list(ontology.get("rows")) if isinstance(r, dict)]
    validator_rows = [r for r in as_list(validator.get("rows")) if isinstance(r, dict)]

    (
        ontology_valid,
        ontology_invalid,
        ontology_below_conf,
        ontology_invalid_samples,
    ) = validate_candidate_rows(ontology_rows, args.min_candidate_confidence)
    (
        validator_valid,
        validator_invalid,
        validator_below_conf,
        validator_invalid_samples,
    ) = validate_candidate_rows(validator_rows, args.min_candidate_confidence)

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        status = "PASS" if ok else "FAIL"
        print(f"{status} {check_id}: {detail}")

    add_check(
        "discovery_source_total",
        source_files >= args.min_total_files,
        f"source_files={source_files} min={args.min_total_files}",
    )
    add_check(
        "discovery_processed_total",
        processed_files >= args.min_total_files,
        f"processed_files={processed_files} min={args.min_total_files}",
    )
    add_check(
        "discovery_processed_matches_source",
        processed_files == source_files and source_files > 0,
        f"processed={processed_files} source={source_files}",
    )
    add_check(
        "discovery_pass_count",
        pass_count >= args.min_pass_count,
        f"pass_count={pass_count} min={args.min_pass_count}",
    )
    add_check(
        "discovery_full_pass_count",
        full_pass_count >= args.min_pass_count,
        f"full_pass_count={full_pass_count} min={args.min_pass_count}",
    )
    add_check(
        "saturation_consecutive",
        consecutive_under >= args.required_consecutive_saturation,
        (
            f"consecutive_under={consecutive_under} "
            f"required={args.required_consecutive_saturation} max_growth={args.max_growth_ratio:.4f}"
        ),
    )
    add_check(
        "checklist_missing_ratio",
        checklist_missing_ratio <= clamp_ratio(args.max_checklist_missing_ratio),
        (
            f"missing_ratio={checklist_missing_ratio:.4f} "
            f"max={args.max_checklist_missing_ratio:.4f} "
            f"(missing={checklist_missing}/{checklist_total})"
        ),
    )
    add_check(
        "checklist_uncertain_ratio",
        checklist_uncertain_ratio <= clamp_ratio(args.max_checklist_uncertain_ratio),
        (
            f"uncertain_ratio={checklist_uncertain_ratio:.4f} "
            f"max={args.max_checklist_uncertain_ratio:.4f} "
            f"(uncertain={checklist_uncertain}/{checklist_total})"
        ),
    )
    add_check(
        "coverage_gap_total",
        gaps_files >= args.min_total_files,
        f"coverage_files={gaps_files} min={args.min_total_files}",
    )
    add_check(
        "coverage_gap_unresolved",
        unresolved_files <= args.max_unresolved_files,
        f"unresolved_files={unresolved_files} max={args.max_unresolved_files}",
    )
    add_check(
        "ontology_candidate_count",
        ontology_valid >= args.min_parameter_candidates,
        f"valid={ontology_valid} min={args.min_parameter_candidates} invalid={ontology_invalid}",
    )
    add_check(
        "validator_candidate_count",
        validator_valid >= args.min_validator_candidates,
        f"valid={validator_valid} min={args.min_validator_candidates} invalid={validator_invalid}",
    )
    add_check(
        "ontology_candidate_quality",
        ontology_invalid == 0 and ontology_below_conf == 0,
        f"invalid={ontology_invalid} below_confidence={ontology_below_conf}",
    )
    add_check(
        "validator_candidate_quality",
        validator_invalid == 0 and validator_below_conf == 0,
        f"invalid={validator_invalid} below_confidence={validator_below_conf}",
    )

    ok = all(bool(c["ok"]) for c in checks)

    payload: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "discoveryReport": str(discovery_path),
            "ontologyCandidates": str(ontology_path),
            "validatorCandidates": str(validator_path),
            "coverageGaps": str(gaps_path),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minPassCount": args.min_pass_count,
            "maxGrowthRatio": args.max_growth_ratio,
            "requiredConsecutiveSaturation": args.required_consecutive_saturation,
            "maxChecklistMissingRatio": args.max_checklist_missing_ratio,
            "maxChecklistUncertainRatio": args.max_checklist_uncertain_ratio,
            "maxUnresolvedFiles": args.max_unresolved_files,
            "minParameterCandidates": args.min_parameter_candidates,
            "minValidatorCandidates": args.min_validator_candidates,
            "minCandidateConfidence": args.min_candidate_confidence,
        },
        "totals": {
            "sourceFiles": source_files,
            "processedFiles": processed_files,
            "passCount": pass_count,
            "fullPassCount": full_pass_count,
            "growthRatios": growth_values,
            "consecutiveSaturationPasses": consecutive_under,
            "checklistItemsTotal": checklist_total,
            "checklistMissing": checklist_missing,
            "checklistMissingRatio": round(checklist_missing_ratio, 6),
            "checklistUncertain": checklist_uncertain,
            "checklistUncertainRatio": round(checklist_uncertain_ratio, 6),
            "coverageFiles": gaps_files,
            "coverageUnresolvedFiles": unresolved_files,
            "ontologyCandidatesValid": ontology_valid,
            "ontologyCandidatesInvalid": ontology_invalid,
            "validatorCandidatesValid": validator_valid,
            "validatorCandidatesInvalid": validator_invalid,
        },
        "samples": {
            "ontologyInvalid": ontology_invalid_samples,
            "validatorInvalid": validator_invalid_samples,
        },
        "checks": checks,
        "ok": ok,
    }

    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Created: {report_out}")

    print(
        f"Summary ({args.label}): "
        f"ok={ok} source={source_files} processed={processed_files} "
        f"passes={pass_count} full_passes={full_pass_count} "
        f"saturation_tail={consecutive_under} unresolved_files={unresolved_files} "
        f"ontology_valid={ontology_valid} validator_valid={validator_valid}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

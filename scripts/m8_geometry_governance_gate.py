#!/usr/bin/env python3
"""Governance gate for M8 geometry baseline + uplift consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_REQUIRED_BLOCKERS = [
    "version_not_1_2",
    "missing_meta_geometry",
    "missing_formation_kind",
    "missing_step_geo_primitive",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate geometry governance consistency across baseline, coverage, and uplift reports."
    )
    ap.add_argument(
        "--baseline-report",
        required=True,
        help="path to out/m8_geometry_baseline.json-like report",
    )
    ap.add_argument(
        "--coverage-report",
        required=True,
        help="path to out/m6_full_description_current.json-like report",
    )
    ap.add_argument(
        "--uplift-report",
        required=True,
        help="path to out/m8_geometry_uplift_progress.json-like report",
    )
    ap.add_argument(
        "--report-out",
        default="",
        help="optional output report path",
    )
    ap.add_argument(
        "--label",
        default="m8-geometry-governance",
        help="report label",
    )
    ap.add_argument(
        "--min-baseline-total",
        type=int,
        default=0,
        help="minimum total files expected in baseline report",
    )
    ap.add_argument(
        "--min-strict-candidates",
        type=int,
        default=0,
        help="minimum strict candidates expected in uplift report",
    )
    ap.add_argument(
        "--min-doctor-pass-rate",
        type=float,
        default=0.95,
        help="minimum strict-doctor pass rate in [0,1]",
    )
    ap.add_argument(
        "--min-geo-pass-rate",
        type=float,
        default=1.0,
        help="minimum geometry validator pass rate in [0,1]",
    )
    ap.add_argument(
        "--min-ready-rate",
        type=float,
        default=1.0,
        help="minimum geometry-ready rate in [0,1]",
    )
    ap.add_argument(
        "--required-blocker",
        action="append",
        default=[],
        help="required blocker id for burn-down checks (repeatable)",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m8_geometry_governance_gate.py: {msg}", file=sys.stderr)
    return 2


def load_json(path: Path) -> dict[str, object]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return obj


def as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return default


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def main() -> int:
    args = parse_args()

    baseline_path = Path(args.baseline_report)
    coverage_path = Path(args.coverage_report)
    uplift_path = Path(args.uplift_report)
    report_out = Path(args.report_out) if args.report_out else None

    for p, name in (
        (baseline_path, "--baseline-report"),
        (coverage_path, "--coverage-report"),
        (uplift_path, "--uplift-report"),
    ):
        if not p.exists():
            return fail(f"missing {name}: {p}")

    if args.min_baseline_total < 0:
        return fail("--min-baseline-total must be >= 0")
    if args.min_strict_candidates < 0:
        return fail("--min-strict-candidates must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_ready_rate <= 1.0):
        return fail("--min-ready-rate must be between 0 and 1")

    try:
        baseline = load_json(baseline_path)
        coverage = load_json(coverage_path)
        uplift = load_json(uplift_path)
    except Exception as exc:
        return fail(f"failed to parse JSON report(s): {exc}")

    baseline_total = as_int(baseline.get("total"), 0)
    baseline_blockers = baseline.get("blockerCounts", {})
    if not isinstance(baseline_blockers, dict):
        baseline_blockers = {}

    strict_node = coverage.get("strict", {})
    if not isinstance(strict_node, dict):
        strict_node = {}
    strict_count = as_int(strict_node.get("fullDescriptionCount"), 0)

    totals = uplift.get("totals", {})
    if not isinstance(totals, dict):
        totals = {}
    strict_candidates = as_int(totals.get("strictCandidates"), 0)
    uplifted = as_int(totals.get("uplifted"), 0)
    errors = as_int(totals.get("errors"), 0)
    doctor_rate = as_float(totals.get("doctorStrictPassRate"), 0.0)
    geo_rate = as_float(totals.get("validateGeoPassRate"), 0.0)
    ready_rate = as_float(totals.get("geometryReadyRate"), 0.0)

    burn = uplift.get("blockerBurnDown", {})
    if not isinstance(burn, dict):
        burn = {}
    burn_before = burn.get("before", {})
    burn_after = burn.get("after", {})
    burn_resolved = burn.get("resolved", {})
    if not isinstance(burn_before, dict):
        burn_before = {}
    if not isinstance(burn_after, dict):
        burn_after = {}
    if not isinstance(burn_resolved, dict):
        burn_resolved = {}

    required_blockers = args.required_blocker[:] if args.required_blocker else DEFAULT_REQUIRED_BLOCKERS[:]

    checks: list[dict[str, object]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        status = "PASS" if ok else "FAIL"
        print(f"{status} {check_id}: {detail}")

    add_check(
        "baseline_total",
        baseline_total >= args.min_baseline_total,
        f"baseline_total={baseline_total} min={args.min_baseline_total}",
    )
    add_check(
        "strict_candidates_min",
        strict_candidates >= args.min_strict_candidates,
        f"strict_candidates={strict_candidates} min={args.min_strict_candidates}",
    )
    add_check(
        "coverage_alignment",
        strict_candidates == strict_count,
        f"strict_candidates={strict_candidates} coverage_strict={strict_count}",
    )
    add_check(
        "uplifted_all_candidates",
        uplifted == strict_candidates,
        f"uplifted={uplifted} strict_candidates={strict_candidates}",
    )
    add_check(
        "doctor_pass_rate",
        doctor_rate >= clamp_ratio(args.min_doctor_pass_rate),
        f"doctor_pass_rate={doctor_rate:.4f} min={args.min_doctor_pass_rate:.4f}",
    )
    add_check(
        "geo_pass_rate",
        geo_rate >= clamp_ratio(args.min_geo_pass_rate),
        f"geo_pass_rate={geo_rate:.4f} min={args.min_geo_pass_rate:.4f}",
    )
    add_check(
        "ready_rate",
        ready_rate >= clamp_ratio(args.min_ready_rate),
        f"ready_rate={ready_rate:.4f} min={args.min_ready_rate:.4f}",
    )
    add_check(
        "uplift_errors_zero",
        errors == 0,
        f"errors={errors}",
    )

    for blocker in required_blockers:
        baseline_count = as_int(baseline_blockers.get(blocker), 0)
        before_count = as_int(burn_before.get(blocker), 0)
        after_count = as_int(burn_after.get(blocker), 0)
        resolved_count = as_int(burn_resolved.get(blocker), 0)
        add_check(
            f"baseline_blocker_present:{blocker}",
            baseline_count > 0,
            f"baseline={baseline_count}",
        )
        add_check(
            f"burn_down_before:{blocker}",
            before_count > 0,
            f"before={before_count}",
        )
        add_check(
            f"burn_down_after_zero:{blocker}",
            after_count == 0,
            f"after={after_count}",
        )
        add_check(
            f"burn_down_resolved:{blocker}",
            resolved_count == before_count and before_count > 0,
            f"resolved={resolved_count} before={before_count}",
        )

    ok = all(bool(c["ok"]) for c in checks)

    payload = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "baselineReport": str(baseline_path),
            "coverageReport": str(coverage_path),
            "upliftReport": str(uplift_path),
        },
        "thresholds": {
            "minBaselineTotal": args.min_baseline_total,
            "minStrictCandidates": args.min_strict_candidates,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
            "minReadyRate": args.min_ready_rate,
            "requiredBlockers": required_blockers,
        },
        "metrics": {
            "baselineTotal": baseline_total,
            "coverageStrictCount": strict_count,
            "strictCandidates": strict_candidates,
            "uplifted": uplifted,
            "errors": errors,
            "doctorPassRate": round(doctor_rate, 4),
            "geoPassRate": round(geo_rate, 4),
            "readyRate": round(ready_rate, 4),
        },
        "checks": checks,
        "ok": ok,
    }

    if report_out is not None:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Created: {report_out}")

    if ok:
        print("Summary: PASS")
        return 0
    print("Summary: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

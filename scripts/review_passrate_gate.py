#!/usr/bin/env python3
"""Enforce minimum pass-rate KPIs on acquisition review reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_report(path: Path) -> tuple[int, int, int]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{path}: failed to parse JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: root must be JSON object")

    total = payload.get("total")
    passed = payload.get("passed")
    failed = payload.get("failed")
    if not isinstance(total, int) or not isinstance(passed, int) or not isinstance(failed, int):
        raise RuntimeError(f"{path}: expected integer total/passed/failed")
    if total < 0 or passed < 0 or failed < 0:
        raise RuntimeError(f"{path}: total/passed/failed must be >= 0")
    if passed + failed != total:
        raise RuntimeError(f"{path}: inconsistent counts (passed + failed != total)")
    return total, passed, failed


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fail if review pass rate is below KPI threshold.")
    ap.add_argument(
        "--report",
        action="append",
        default=[],
        help="review report JSON path (repeatable)",
    )
    ap.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.95,
        help="minimum pass-rate threshold in [0,1] (default: 0.95)",
    )
    ap.add_argument(
        "--label",
        default="review-passrate",
        help="label printed in summary output",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    if not args.report:
        print("review_passrate_gate.py: provide at least one --report", file=sys.stderr)
        return 2
    if not (0.0 <= args.min_pass_rate <= 1.0):
        print("review_passrate_gate.py: --min-pass-rate must be between 0 and 1", file=sys.stderr)
        return 2

    failures: list[str] = []
    totals = {"total": 0, "passed": 0, "failed": 0}

    for raw in args.report:
        path = Path(raw)
        if not path.exists():
            failures.append(f"{path}: missing report")
            continue
        try:
            total, passed, failed = load_report(path)
        except RuntimeError as exc:
            failures.append(str(exc))
            continue

        rate = (passed / total) if total > 0 else 0.0
        totals["total"] += total
        totals["passed"] += passed
        totals["failed"] += failed
        print(f"REPORT {path} total={total} passed={passed} failed={failed} passRate={rate:.4f}")
        if rate < args.min_pass_rate:
            failures.append(
                f"{path}: pass-rate {rate:.4f} below threshold {args.min_pass_rate:.4f}"
            )

    combined_rate = (
        (totals["passed"] / totals["total"]) if totals["total"] > 0 else 0.0
    )
    print(
        f"Summary ({args.label}): total={totals['total']} passed={totals['passed']} "
        f"failed={totals['failed']} passRate={combined_rate:.4f} threshold={args.min_pass_rate:.4f}"
    )

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

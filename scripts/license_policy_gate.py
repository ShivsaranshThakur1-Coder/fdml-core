#!/usr/bin/env python3
"""Enforce acquisition license-policy compliance on index.json outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_ALLOWED = {
    "Public Domain",
    "CC0 1.0",
    "CC BY 4.0",
    "CC BY-SA 4.0",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fail if acquisition index contains disallowed licenses.")
    ap.add_argument(
        "--index",
        action="append",
        default=[],
        help="acquisition index JSON path (repeatable)",
    )
    ap.add_argument(
        "--allow-license",
        action="append",
        default=[],
        help="additional allowed license value (repeatable)",
    )
    ap.add_argument(
        "--label",
        default="license-policy",
        help="label printed in summary output",
    )
    return ap.parse_args()


def load_index(path: Path) -> tuple[list[dict], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{path}: failed to parse JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: root must be JSON object")

    raw_records = payload.get("records")
    raw_errors = payload.get("errors", [])
    if not isinstance(raw_records, list):
        raise RuntimeError(f"{path}: missing records[]")
    if not isinstance(raw_errors, list):
        raise RuntimeError(f"{path}: errors must be an array")

    records: list[dict] = []
    for i, row in enumerate(raw_records):
        if not isinstance(row, dict):
            raise RuntimeError(f"{path}: records[{i}] must be object")
        records.append(row)
    errors: list[str] = [str(e) for e in raw_errors]
    return records, errors


def main() -> int:
    args = parse_args()
    if not args.index:
        print("license_policy_gate.py: provide at least one --index", file=sys.stderr)
        return 2

    allowed = set(DEFAULT_ALLOWED)
    for lic in args.allow_license:
        if lic.strip():
            allowed.add(lic.strip())

    failures: list[str] = []
    total_records = 0

    for raw in args.index:
        path = Path(raw)
        if not path.exists():
            failures.append(f"{path}: missing index")
            continue
        try:
            records, errors = load_index(path)
        except RuntimeError as exc:
            failures.append(str(exc))
            continue

        total_records += len(records)
        for row in records:
            source_id = str(row.get("id", "")).strip() or "<unknown>"
            license_name = str(row.get("license", "")).strip()
            if not license_name:
                failures.append(f"{path}: record '{source_id}' missing license")
                continue
            if license_name not in allowed:
                failures.append(
                    f"{path}: record '{source_id}' has disallowed license '{license_name}'"
                )

        for err in errors:
            if "disallowed license" in err.lower():
                failures.append(f"{path}: {err}")

        print(
            f"INDEX {path} records={len(records)} errors={len(errors)} "
            f"allowedLicenses={len(allowed)}"
        )

    print(
        f"Summary ({args.label}): indexes={len(args.index)} records={total_records} "
        f"allowedLicenses={sorted(allowed)}"
    )

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Enforce quality thresholds on strict full-description FDML files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Fail if strict full-description files regress in quality."
    )
    ap.add_argument(
        "--coverage-report",
        required=True,
        help="full-description coverage JSON report path",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.95,
        help="minimum strict doctor pass-rate in [0,1] for strict full-description files",
    )
    ap.add_argument(
        "--max-placeholder-only",
        type=int,
        default=0,
        help="maximum allowed placeholder-only files in strict full-description set",
    )
    ap.add_argument("--report-out", default="", help="optional JSON report output path")
    ap.add_argument(
        "--label",
        default="full-description-quality",
        help="summary label",
    )
    return ap.parse_args()


def load_coverage_rows(path: Path) -> tuple[dict, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: root must be object")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise RuntimeError(f"{path}: missing rows[]; regenerate with full_description_coverage.py")
    clean_rows: list[dict] = []
    for row in rows:
        if isinstance(row, dict):
            clean_rows.append(row)
    return payload, clean_rows


def resolve_fdml_path(file_field: str, report_path: Path) -> Path:
    p = Path(file_field)
    if p.is_absolute():
        return p
    # Prefer workspace-relative resolution; fallback to report-relative.
    candidate = Path.cwd() / p
    if candidate.exists():
        return candidate
    return report_path.parent / p


def run_doctor(fdml_bin: Path, fdml_file: Path) -> tuple[int, str]:
    p = subprocess.run(
        [str(fdml_bin), "doctor", str(fdml_file), "--strict"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return p.returncode, (p.stdout or "").strip()


def main() -> int:
    args = parse_args()
    if not (0.0 <= args.min_pass_rate <= 1.0):
        print("full_description_quality_gate.py: --min-pass-rate must be between 0 and 1", file=sys.stderr)
        return 2
    if args.max_placeholder_only < 0:
        print("full_description_quality_gate.py: --max-placeholder-only must be >= 0", file=sys.stderr)
        return 2

    coverage_path = Path(args.coverage_report)
    if not coverage_path.exists():
        print(f"full_description_quality_gate.py: missing coverage report: {coverage_path}", file=sys.stderr)
        return 2

    fdml_bin = Path(args.fdml_bin)
    if not fdml_bin.exists():
        print(f"full_description_quality_gate.py: missing fdml executable: {fdml_bin}", file=sys.stderr)
        return 2

    payload, rows = load_coverage_rows(coverage_path)
    strict_rows = [row for row in rows if bool(row.get("strictFullDescription"))]
    if not strict_rows:
        print(
            f"full_description_quality_gate.py: no strict full-description rows found in {coverage_path}",
            file=sys.stderr,
        )
        return 2

    placeholder_only_rows: list[dict] = []
    for row in strict_rows:
        try:
            non_placeholder_steps = int(row.get("nonPlaceholderSteps", 0))
        except Exception:
            non_placeholder_steps = 0
        if non_placeholder_steps <= 0:
            placeholder_only_rows.append(row)

    doctor_results: list[dict[str, object]] = []
    passed = 0
    for row in strict_rows:
        file_field = str(row.get("file", "")).strip()
        if not file_field:
            doctor_results.append(
                {
                    "file": file_field,
                    "doctorExitCode": 127,
                    "strictOk": False,
                    "error": "missing_file_field",
                }
            )
            continue
        fdml_file = resolve_fdml_path(file_field, coverage_path)
        if not fdml_file.exists():
            doctor_results.append(
                {
                    "file": str(fdml_file),
                    "doctorExitCode": 127,
                    "strictOk": False,
                    "error": "missing_fdml_file",
                }
            )
            print(f"FAIL {file_field} missing_fdml_file")
            continue

        exit_code, output = run_doctor(fdml_bin, fdml_file)
        strict_ok = exit_code == 0
        if strict_ok:
            passed += 1
        doctor_results.append(
            {
                "file": str(fdml_file),
                "doctorExitCode": exit_code,
                "strictOk": strict_ok,
                "outputSnippet": output[:240],
            }
        )
        status = "PASS" if strict_ok else "FAIL"
        print(f"{status} {file_field} ({fdml_file})")

    total = len(strict_rows)
    failed = total - passed
    pass_rate = (passed / total) if total else 0.0
    placeholder_only_count = len(placeholder_only_rows)
    coverage_parse_errors = payload.get("parseErrors")
    parse_error_count = len(coverage_parse_errors) if isinstance(coverage_parse_errors, list) else 0
    strict_count_reported = (
        int(payload.get("strict", {}).get("fullDescriptionCount", total))
        if isinstance(payload.get("strict"), dict)
        else total
    )

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "coverageReport": str(coverage_path),
        "minPassRate": args.min_pass_rate,
        "maxPlaceholderOnly": args.max_placeholder_only,
        "coverageRows": len(rows),
        "strictRows": total,
        "strictRowsReported": strict_count_reported,
        "parseErrorCount": parse_error_count,
        "doctor": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "passRate": pass_rate,
        },
        "placeholderAudit": {
            "placeholderOnlyCount": placeholder_only_count,
            "placeholderOnlyFiles": [str(r.get("file", "")) for r in placeholder_only_rows],
        },
        "results": doctor_results,
    }

    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Created: {out_path}")

    print(
        f"Summary ({args.label}): strict={total} passed={passed} failed={failed} "
        f"passRate={pass_rate:.4f} threshold={args.min_pass_rate:.4f} "
        f"placeholderOnly={placeholder_only_count} allowed={args.max_placeholder_only} "
        f"parseErrors={parse_error_count}"
    )

    ok = (
        pass_rate >= args.min_pass_rate
        and placeholder_only_count <= args.max_placeholder_only
        and parse_error_count == 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

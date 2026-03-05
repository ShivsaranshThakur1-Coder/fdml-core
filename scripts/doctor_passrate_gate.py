#!/usr/bin/env python3
"""Enforce strict doctor pass-rate for generated FDML batches."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Fail if strict doctor pass-rate is below threshold."
    )
    ap.add_argument("--index", required=True, help="conversion index JSON path")
    ap.add_argument(
        "--root-dir",
        default="",
        help="root directory for relative fdmlFile paths (default: index parent)",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.90,
        help="minimum strict doctor pass-rate in [0,1] (default: 0.90)",
    )
    ap.add_argument("--report-out", default="", help="optional JSON report output path")
    ap.add_argument("--label", default="doctor-passrate", help="summary label")
    return ap.parse_args()


def load_generated_entries(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: root must be object")

    out: list[dict] = []
    if isinstance(payload.get("generated"), list):
        for row in payload["generated"]:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "")).strip()
            fdml_file = str(row.get("fdmlFile", "")).strip()
            if key and fdml_file:
                out.append({"key": key, "fdmlFile": fdml_file})
    elif isinstance(payload.get("items"), list):
        # Fallback shape for ingest-batch style indexes.
        for row in payload["items"]:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source", "")).strip()
            outputs = row.get("outputs", {})
            if not isinstance(outputs, dict):
                continue
            fdml_file = str(outputs.get("fdml", "")).strip()
            if source and fdml_file:
                out.append({"key": source, "fdmlFile": fdml_file})
    else:
        raise RuntimeError(f"{path}: expected generated[] or items[]")

    out.sort(key=lambda r: r["key"])
    return out


def resolve_fdml_path(fdml_field: str, root_dir: Path) -> Path:
    p = Path(fdml_field)
    if p.is_absolute():
        return p
    return root_dir / p


def run_doctor(fdml_bin: Path, fdml_file: Path) -> tuple[int, str]:
    cmd = [str(fdml_bin), "doctor", str(fdml_file), "--strict"]
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return p.returncode, (p.stdout or "").strip()


def main() -> int:
    args = parse_args()
    if not (0.0 <= args.min_pass_rate <= 1.0):
        print("doctor_passrate_gate.py: --min-pass-rate must be between 0 and 1", file=sys.stderr)
        return 2

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"doctor_passrate_gate.py: missing index file: {index_path}", file=sys.stderr)
        return 2

    fdml_bin = Path(args.fdml_bin)
    if not fdml_bin.exists():
        print(f"doctor_passrate_gate.py: missing fdml executable: {fdml_bin}", file=sys.stderr)
        return 2

    root_dir = Path(args.root_dir) if args.root_dir else index_path.parent
    entries = load_generated_entries(index_path)
    if not entries:
        print(f"doctor_passrate_gate.py: no generated entries in index: {index_path}", file=sys.stderr)
        return 2

    results: list[dict] = []
    passed = 0
    for row in entries:
        key = row["key"]
        fdml_file = resolve_fdml_path(row["fdmlFile"], root_dir)
        if not fdml_file.exists():
            results.append(
                {
                    "key": key,
                    "fdmlFile": str(fdml_file),
                    "doctorExitCode": 127,
                    "strictOk": False,
                    "error": "missing_fdml_file",
                }
            )
            continue
        exit_code, output = run_doctor(fdml_bin, fdml_file)
        strict_ok = exit_code == 0
        if strict_ok:
            passed += 1
        results.append(
            {
                "key": key,
                "fdmlFile": str(fdml_file),
                "doctorExitCode": exit_code,
                "strictOk": strict_ok,
                "outputSnippet": output[:240],
            }
        )
        status = "PASS" if strict_ok else "FAIL"
        print(f"{status} {key} ({fdml_file})")

    total = len(results)
    failed = total - passed
    pass_rate = (passed / total) if total else 0.0
    print(
        f"Summary ({args.label}): total={total} passed={passed} failed={failed} "
        f"passRate={pass_rate:.4f} threshold={args.min_pass_rate:.4f}"
    )

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "index": str(index_path),
        "rootDir": str(root_dir),
        "minPassRate": args.min_pass_rate,
        "total": total,
        "passed": passed,
        "failed": failed,
        "passRate": pass_rate,
        "results": results,
    }
    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Created: {out_path}")

    return 0 if pass_rate >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())

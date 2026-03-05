#!/usr/bin/env python3
"""Track semantic issue trend and fail on regression vs baseline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


METRIC_KEYS = [
    "xsdFailed",
    "schematronFailures",
    "lintWarnings",
    "timingIssues",
    "geoIssues",
    "strictFailFiles",
    "issueTotal",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Fail when semantic issue totals regress versus baseline."
    )
    ap.add_argument(
        "--target",
        action="append",
        default=[],
        help="file or directory target for fdml checks (repeatable)",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--baseline",
        required=True,
        help="baseline trend JSON path",
    )
    ap.add_argument(
        "--report-out",
        default="",
        help="optional current trend JSON output path",
    )
    ap.add_argument(
        "--label",
        default="semantic-issue-trend",
        help="summary label",
    )
    ap.add_argument(
        "--write-baseline",
        action="store_true",
        help="write/refresh baseline from current values and exit 0",
    )
    return ap.parse_args()


def run_json(cmd: list[str]) -> dict:
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = (p.stdout or "").strip()
    try:
        payload = json.loads(output)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            f"failed to parse JSON from command: {' '.join(cmd)}\nexit={p.returncode}\noutput={output[:400]}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON shape from command: {' '.join(cmd)}")
    return payload


def normalize_file(raw: str, repo_root: Path) -> str:
    p = Path(raw)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(repo_root).as_posix()
        except Exception:
            return p.resolve().as_posix()
    return p.as_posix()


def collect_current(fdml_bin: Path, targets: list[str], repo_root: Path) -> dict:
    doctor = run_json([str(fdml_bin), "doctor", *targets, "--json"])
    geo = run_json([str(fdml_bin), "validate-geo", *targets, "--json"])

    per_file: dict[str, dict[str, int | bool]] = {}

    def ensure(file_key: str) -> dict[str, int | bool]:
        if file_key not in per_file:
            per_file[file_key] = {
                "xsdFailed": 0,
                "schematronFailures": 0,
                "lintWarnings": 0,
                "timingIssues": 0,
                "geoIssues": 0,
                "strictFail": False,
            }
        return per_file[file_key]

    for row in doctor.get("xsd", []):
        if not isinstance(row, dict):
            continue
        file_key = normalize_file(str(row.get("file", "")), repo_root)
        if not file_key:
            continue
        stats = ensure(file_key)
        if not bool(row.get("ok", False)):
            stats["xsdFailed"] = int(stats["xsdFailed"]) + 1

    for row in doctor.get("schematron", []):
        if not isinstance(row, dict):
            continue
        file_key = normalize_file(str(row.get("file", "")), repo_root)
        if not file_key:
            continue
        stats = ensure(file_key)
        msgs = row.get("messages", [])
        fail_count = len(msgs) if isinstance(msgs, list) else 0
        stats["schematronFailures"] = int(stats["schematronFailures"]) + fail_count

    for row in doctor.get("lint", []):
        if not isinstance(row, dict):
            continue
        file_key = normalize_file(str(row.get("file", "")), repo_root)
        if not file_key:
            continue
        stats = ensure(file_key)
        warns = row.get("warnings", [])
        warn_count = len(warns) if isinstance(warns, list) else 0
        stats["lintWarnings"] = int(stats["lintWarnings"]) + warn_count

    for row in doctor.get("timing", []):
        if not isinstance(row, dict):
            continue
        file_key = normalize_file(str(row.get("file", "")), repo_root)
        if not file_key:
            continue
        stats = ensure(file_key)
        issues = row.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        stats["timingIssues"] = int(stats["timingIssues"]) + issue_count

    for row in geo.get("results", []):
        if not isinstance(row, dict):
            continue
        file_key = normalize_file(str(row.get("file", "")), repo_root)
        if not file_key:
            continue
        stats = ensure(file_key)
        issues = row.get("issues", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        stats["geoIssues"] = int(stats["geoIssues"]) + issue_count

    totals = {
        "files": 0,
        "xsdFailed": 0,
        "schematronFailures": 0,
        "lintWarnings": 0,
        "timingIssues": 0,
        "geoIssues": 0,
        "strictFailFiles": 0,
        "issueTotal": 0,
    }

    rows: list[dict[str, int | bool | str]] = []
    for file_key in sorted(per_file.keys()):
        stats = per_file[file_key]
        strict_fail = (
            int(stats["xsdFailed"]) > 0
            or int(stats["schematronFailures"]) > 0
            or int(stats["lintWarnings"]) > 0
            or int(stats["timingIssues"]) > 0
            or int(stats["geoIssues"]) > 0
        )
        stats["strictFail"] = strict_fail
        issue_total = (
            int(stats["xsdFailed"])
            + int(stats["schematronFailures"])
            + int(stats["lintWarnings"])
            + int(stats["timingIssues"])
            + int(stats["geoIssues"])
        )

        totals["files"] += 1
        totals["xsdFailed"] += int(stats["xsdFailed"])
        totals["schematronFailures"] += int(stats["schematronFailures"])
        totals["lintWarnings"] += int(stats["lintWarnings"])
        totals["timingIssues"] += int(stats["timingIssues"])
        totals["geoIssues"] += int(stats["geoIssues"])
        totals["strictFailFiles"] += 1 if strict_fail else 0
        totals["issueTotal"] += issue_total

        rows.append(
            {
                "file": file_key,
                "xsdFailed": int(stats["xsdFailed"]),
                "schematronFailures": int(stats["schematronFailures"]),
                "lintWarnings": int(stats["lintWarnings"]),
                "timingIssues": int(stats["timingIssues"]),
                "geoIssues": int(stats["geoIssues"]),
                "strictFail": strict_fail,
                "issueTotal": issue_total,
            }
        )

    return {
        "schemaVersion": "1",
        "source": "doctor-json+validate-geo",
        "scope": targets,
        "totals": totals,
        "files": rows,
    }


def load_baseline(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: baseline root must be object")
    if not isinstance(payload.get("totals"), dict):
        raise RuntimeError(f"{path}: baseline missing totals")
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    if not args.target:
        print("semantic_issue_trend_gate.py: provide at least one --target", file=sys.stderr)
        return 2

    fdml_bin = Path(args.fdml_bin)
    if not fdml_bin.exists():
        print(f"semantic_issue_trend_gate.py: missing fdml executable: {fdml_bin}", file=sys.stderr)
        return 2

    repo_root = Path(".").resolve()
    current = collect_current(fdml_bin, args.target, repo_root)
    current["label"] = args.label

    baseline_path = Path(args.baseline)
    if args.write_baseline:
        write_json(baseline_path, current)
        print(f"Created baseline: {baseline_path}")
        return 0

    if not baseline_path.exists():
        print(f"semantic_issue_trend_gate.py: missing baseline: {baseline_path}", file=sys.stderr)
        return 2

    baseline = load_baseline(baseline_path)
    baseline_totals = baseline.get("totals", {})
    current_totals = current.get("totals", {})

    regressions: list[str] = []
    for key in METRIC_KEYS:
        prev = int(baseline_totals.get(key, 0))
        now = int(current_totals.get(key, 0))
        if now > prev:
            regressions.append(f"{key}: baseline={prev} current={now}")

    print(f"Baseline ({args.label}): {json.dumps({k: int(baseline_totals.get(k, 0)) for k in METRIC_KEYS}, sort_keys=True)}")
    print(f"Current  ({args.label}): {json.dumps({k: int(current_totals.get(k, 0)) for k in METRIC_KEYS}, sort_keys=True)}")

    if args.report_out:
        out_path = Path(args.report_out)
        write_json(out_path, current)
        print(f"Created: {out_path}")

    if regressions:
        for msg in regressions:
            print(f"FAIL: regression {msg}")
        return 1

    print(f"Summary ({args.label}): PASS (no metric regressions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

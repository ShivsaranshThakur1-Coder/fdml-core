#!/usr/bin/env python3
"""Quality gate for acquired source text files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import string
import sys
from pathlib import Path


HEADER_REQUIRED = {
    "source_id",
    "title",
    "source_url",
    "license",
    "attribution",
    "parser",
    "source_sha256",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_source_file(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    header: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("# "):
            break
        body = line[2:]
        if ":" in body:
            key, val = body.split(":", 1)
            header[key.strip()] = val.strip()
        i += 1
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    text = "\n".join(lines[i:])
    if text and not text.endswith("\n"):
        text += "\n"
    return header, text


def compute_metrics(text: str) -> dict[str, float | int]:
    chars = len(text)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    word_count = len(words)
    alpha_chars = sum(1 for c in text if c.isalpha())

    printable = set(string.printable)
    control_chars = sum(1 for c in text if c not in printable and not c.isalpha())

    non_space_chars = sum(1 for c in text if not c.isspace())
    alpha_ratio = (alpha_chars / non_space_chars) if non_space_chars else 0.0
    control_ratio = (control_chars / chars) if chars else 0.0

    repeated_symbol_runs = len(re.findall(r"([^\w\s])\1{6,}", text))

    lines = [ln for ln in text.splitlines() if ln.strip()]
    noisy_lines = 0
    for ln in lines:
        total = len(ln)
        if total == 0:
            continue
        noisy = sum(1 for ch in ln if not (ch.isalnum() or ch.isspace() or ch in ".,;:!?()[]{}'\"-_/&"))
        if noisy / total > 0.35:
            noisy_lines += 1
    noisy_line_ratio = (noisy_lines / len(lines)) if lines else 1.0

    return {
        "chars": chars,
        "words": word_count,
        "alphaRatio": alpha_ratio,
        "controlRatio": control_ratio,
        "repeatedSymbolRuns": repeated_symbol_runs,
        "noisyLineRatio": noisy_line_ratio,
    }


def evaluate(path: Path, args: argparse.Namespace) -> dict:
    header, text = parse_source_file(path)
    metrics = compute_metrics(text)
    checks: list[dict[str, str | bool | int | float]] = []

    missing = sorted(k for k in HEADER_REQUIRED if not header.get(k))
    checks.append(
        {
            "name": "header_required_keys",
            "ok": not missing,
            "detail": "missing=" + ",".join(missing) if missing else "ok",
        }
    )

    expected_sha = header.get("source_sha256", "")
    actual_sha = sha256_text(text)
    checks.append(
        {
            "name": "body_sha256_match",
            "ok": bool(expected_sha) and expected_sha == actual_sha,
            "detail": f"expected={expected_sha} actual={actual_sha}",
        }
    )

    checks.append(
        {
            "name": "min_chars",
            "ok": metrics["chars"] >= args.min_chars,
            "detail": f"chars={metrics['chars']} threshold={args.min_chars}",
        }
    )
    checks.append(
        {
            "name": "min_words",
            "ok": metrics["words"] >= args.min_words,
            "detail": f"words={metrics['words']} threshold={args.min_words}",
        }
    )
    checks.append(
        {
            "name": "alpha_ratio",
            "ok": metrics["alphaRatio"] >= args.min_alpha_ratio,
            "detail": f"alphaRatio={metrics['alphaRatio']:.4f} threshold={args.min_alpha_ratio}",
        }
    )
    checks.append(
        {
            "name": "control_ratio",
            "ok": metrics["controlRatio"] <= args.max_control_ratio,
            "detail": f"controlRatio={metrics['controlRatio']:.6f} threshold={args.max_control_ratio}",
        }
    )
    checks.append(
        {
            "name": "noisy_line_ratio",
            "ok": metrics["noisyLineRatio"] <= args.max_noisy_line_ratio,
            "detail": f"noisyLineRatio={metrics['noisyLineRatio']:.4f} threshold={args.max_noisy_line_ratio}",
        }
    )
    checks.append(
        {
            "name": "repeated_symbol_runs",
            "ok": metrics["repeatedSymbolRuns"] <= args.max_repeated_symbol_runs,
            "detail": f"repeatedSymbolRuns={metrics['repeatedSymbolRuns']} threshold={args.max_repeated_symbol_runs}",
        }
    )

    ok = all(bool(c["ok"]) for c in checks)
    return {
        "file": str(path),
        "ok": ok,
        "metrics": metrics,
        "checks": checks,
        "header": header,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Review acquired source text quality before ingest.")
    ap.add_argument("--input-dir", default="out/acquired_sources", help="directory with acquired .txt files")
    ap.add_argument("--report", default="", help="path to write JSON report")
    ap.add_argument("--min-chars", type=int, default=800, help="minimum body chars")
    ap.add_argument("--min-words", type=int, default=120, help="minimum body words")
    ap.add_argument("--min-alpha-ratio", type=float, default=0.45, help="minimum alpha/non-space ratio")
    ap.add_argument("--max-control-ratio", type=float, default=0.01, help="maximum control-char ratio")
    ap.add_argument("--max-noisy-line-ratio", type=float, default=0.35, help="maximum noisy-line ratio")
    ap.add_argument("--max-repeated-symbol-runs", type=int, default=8, help="maximum repeated symbol runs")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"review_acquired_sources.py: input dir not found: {input_dir}", file=sys.stderr)
        return 2

    files = sorted(
        p for p in input_dir.glob("*.txt")
        if p.is_file()
    )
    if not files:
        print(f"review_acquired_sources.py: no .txt files found in {input_dir}", file=sys.stderr)
        return 2

    results = [evaluate(p, args) for p in files]
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed

    report = {
        "inputDir": str(input_dir),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    report_path = Path(args.report) if args.report else input_dir / "review.json"
    if report_path.parent:
        report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    for r in results:
        status = "PASS" if r["ok"] else "FAIL"
        print(f"{status} {r['file']}")
        if not r["ok"]:
            for c in r["checks"]:
                if not c["ok"]:
                    print(f"  - {c['name']}: {c['detail']}")

    print(f"Summary: passed={passed} failed={failed} report={report_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

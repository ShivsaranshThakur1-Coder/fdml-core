#!/usr/bin/env python3
"""Inventory semantic enrichment coverage (timing + topology) for FDML files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Compute semantic enrichment coverage for FDML files."
    )
    ap.add_argument(
        "--input-dir",
        action="append",
        default=[],
        help="directory containing FDML .xml files (repeatable)",
    )
    ap.add_argument(
        "--fdml-bin",
        default="bin/fdml",
        help="fdml executable path (default: bin/fdml)",
    )
    ap.add_argument(
        "--target",
        type=int,
        default=15,
        help="target enriched file count for KPI tracking (default: 15)",
    )
    ap.add_argument(
        "--min-enriched",
        type=int,
        default=0,
        help="minimum enriched count required to pass (default: 0)",
    )
    ap.add_argument("--report-out", default="", help="optional JSON report output path")
    ap.add_argument("--label", default="semantic-enrichment", help="summary label")
    return ap.parse_args()


def parse_beats(beats: str) -> bool:
    value = beats.strip()
    if not value:
        return False
    try:
        return float(value) > 0.0
    except ValueError:
        if "/" in value:
            parts = value.split("/", 1)
            if len(parts) != 2:
                return False
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
            except ValueError:
                return False
            return den != 0.0 and (num / den) > 0.0
        return False


def run_doctor(fdml_bin: Path, path: Path) -> tuple[bool, str]:
    p = subprocess.run(
        [str(fdml_bin), "doctor", str(path), "--strict"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = (p.stdout or "").strip()
    return p.returncode == 0, output[:240]


def inspect_file(path: Path, fdml_bin: Path) -> dict[str, object]:
    row: dict[str, object] = {"file": str(path)}

    try:
        root = ET.parse(path).getroot()
    except Exception as exc:
        row["enriched"] = False
        row["errors"] = [f"xml_parse_error:{exc}"]
        return row

    meter_value = ""
    meter = root.find("./meta/meter")
    if meter is not None:
        meter_value = (meter.get("value") or "").strip()

    formation_kind = ""
    formation = root.find("./meta/geometry/formation")
    if formation is not None:
        formation_kind = (formation.get("kind") or "").strip()

    body_geometry = root.findall("./body/geometry/*")
    steps = root.findall(".//step")
    primitives = root.findall(".//geo/primitive")

    beats_values = [(s.get("beats") or "").strip() for s in steps]
    bad_beats = [b for b in beats_values if not parse_beats(b)]

    strict_ok, doctor_snippet = run_doctor(fdml_bin, path)

    errors: list[str] = []
    if not meter_value:
        errors.append("missing_meter")
    if not formation_kind:
        errors.append("missing_formation_kind")
    if not body_geometry:
        errors.append("missing_body_geometry")
    if not steps:
        errors.append("missing_steps")
    if bad_beats:
        errors.append("bad_step_beats")
    if not primitives:
        errors.append("missing_geo_primitives")
    if not strict_ok:
        errors.append("doctor_strict_failed")

    row.update(
        {
            "meter": meter_value,
            "formationKind": formation_kind,
            "stepCount": len(steps),
            "primitiveCount": len(primitives),
            "doctorStrictOk": strict_ok,
            "doctorSnippet": doctor_snippet,
            "errors": errors,
            "enriched": len(errors) == 0,
        }
    )
    return row


def gather_files(input_dirs: list[Path]) -> list[Path]:
    out: list[Path] = []
    for d in sorted(input_dirs, key=lambda p: str(p)):
        files = sorted([p for p in d.glob("*.xml") if p.is_file()], key=lambda p: p.name)
        out.extend(files)
    return out


def main() -> int:
    args = parse_args()
    if not args.input_dir:
        print("semantic_enrichment_inventory.py: provide at least one --input-dir", file=sys.stderr)
        return 2
    if args.min_enriched < 0:
        print("semantic_enrichment_inventory.py: --min-enriched must be >= 0", file=sys.stderr)
        return 2
    if args.target < 0:
        print("semantic_enrichment_inventory.py: --target must be >= 0", file=sys.stderr)
        return 2

    input_dirs = [Path(p) for p in args.input_dir]
    for d in input_dirs:
        if not d.is_dir():
            print(f"semantic_enrichment_inventory.py: input dir not found: {d}", file=sys.stderr)
            return 2

    fdml_bin = Path(args.fdml_bin)
    if not fdml_bin.exists():
        print(f"semantic_enrichment_inventory.py: fdml executable not found: {fdml_bin}", file=sys.stderr)
        return 2

    files = gather_files(input_dirs)
    if not files:
        print("semantic_enrichment_inventory.py: no .xml files found", file=sys.stderr)
        return 2

    rows: list[dict[str, object]] = []
    enriched = 0
    for path in files:
        row = inspect_file(path, fdml_bin)
        rows.append(row)
        if bool(row.get("enriched", False)):
            enriched += 1
            print(f"ENRICHED {path}")
        else:
            reasons = ",".join(row.get("errors", [])) if isinstance(row.get("errors"), list) else "unknown"
            print(f"MISSING  {path} [{reasons}]")

    total = len(rows)
    missing = total - enriched
    coverage = (enriched / total) if total else 0.0
    target_gap = max(0, args.target - enriched)

    print(
        f"Summary ({args.label}): total={total} enriched={enriched} missing={missing} "
        f"coverage={coverage:.4f} target={args.target} gap={target_gap} baseline={args.min_enriched}"
    )

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputDirs": [str(p) for p in sorted(input_dirs, key=lambda p: str(p))],
        "target": args.target,
        "baseline": args.min_enriched,
        "total": total,
        "enriched": enriched,
        "missing": missing,
        "coverage": coverage,
        "targetGap": target_gap,
        "files": rows,
    }
    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Created: {out_path}")

    return 0 if enriched >= args.min_enriched else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compute geometry-readiness baseline for generated FDML outputs."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Measure v1.2 geometry-readiness coverage for generated FDML files."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m2_conversion/run1",
        help="directory containing generated .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m8_geometry_baseline.json",
        help="output JSON report path",
    )
    ap.add_argument(
        "--label",
        default="m8-geometry-baseline",
        help="report label",
    )
    ap.add_argument(
        "--required-version",
        default="1.2",
        help="required FDML version for geometry-ready status",
    )
    ap.add_argument(
        "--min-total",
        type=int,
        default=0,
        help="fail if total files scanned is below this value",
    )
    ap.add_argument(
        "--min-ready",
        type=int,
        default=0,
        help="fail if geometry-ready file count is below this value",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m8_geometry_baseline.py: {msg}", file=sys.stderr)
    return 2


def inspect_file(fdml_file: Path, required_version: str) -> dict[str, object]:
    root = ET.parse(fdml_file).getroot()
    version = (root.get("version") or "").strip()
    steps = root.findall(".//figure/step")
    if not steps:
        steps = root.findall(".//step")

    meta_geometry = root.find("./meta/geometry")
    has_meta_geometry = meta_geometry is not None
    formation_kind = ""
    if meta_geometry is not None:
        formation = meta_geometry.find("./formation")
        if formation is not None:
            formation_kind = (formation.get("kind") or "").strip()

    step_geo_nodes = root.findall(".//step/geo")
    primitives = root.findall(".//step/geo/primitive")
    missing_primitive_kind_count = sum(1 for primitive in primitives if not (primitive.get("kind") or "").strip())
    has_all_primitive_kind = len(primitives) > 0 and missing_primitive_kind_count == 0

    blockers: list[str] = []
    if version != required_version:
        blockers.append(f"version_not_{required_version.replace('.', '_')}")
    if not has_meta_geometry:
        blockers.append("missing_meta_geometry")
    if not formation_kind:
        blockers.append("missing_formation_kind")
    if not primitives:
        blockers.append("missing_step_geo_primitive")
    elif missing_primitive_kind_count:
        blockers.append("missing_primitive_kind")

    return {
        "file": str(fdml_file).replace("\\", "/"),
        "version": version,
        "stepCount": len(steps),
        "hasMetaGeometry": has_meta_geometry,
        "formationKind": formation_kind,
        "hasStepGeo": bool(step_geo_nodes),
        "primitiveCount": len(primitives),
        "missingPrimitiveKindCount": missing_primitive_kind_count,
        "allPrimitiveKindPresent": has_all_primitive_kind,
        "geometryReady": len(blockers) == 0,
        "blockers": blockers,
    }


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    report_out = Path(args.report_out)

    if not input_dir.is_dir():
        return fail(f"input dir not found: {input_dir}")
    if args.min_total < 0:
        return fail("--min-total must be >= 0")
    if args.min_ready < 0:
        return fail("--min-ready must be >= 0")

    fdml_files = sorted(input_dir.glob("*.fdml.xml"))
    if not fdml_files:
        return fail(f"no .fdml.xml files found under: {input_dir}")

    rows: list[dict[str, object]] = []
    parse_errors: list[dict[str, str]] = []
    version_counts: Counter[str] = Counter()
    blocker_counts: Counter[str] = Counter()
    signal_counts = {
        "hasMetaGeometry": 0,
        "hasFormationKind": 0,
        "hasStepGeo": 0,
        "hasGeoPrimitives": 0,
        "allPrimitiveKindPresent": 0,
    }

    for fdml_file in fdml_files:
        try:
            row = inspect_file(fdml_file, args.required_version)
            rows.append(row)
            version_key = str(row.get("version") or "(missing)")
            version_counts[version_key] += 1
            if bool(row.get("hasMetaGeometry")):
                signal_counts["hasMetaGeometry"] += 1
            if bool(row.get("formationKind")):
                signal_counts["hasFormationKind"] += 1
            if bool(row.get("hasStepGeo")):
                signal_counts["hasStepGeo"] += 1
            if int(row.get("primitiveCount", 0)) > 0:
                signal_counts["hasGeoPrimitives"] += 1
            if bool(row.get("allPrimitiveKindPresent")):
                signal_counts["allPrimitiveKindPresent"] += 1
            for blocker in row.get("blockers", []):
                blocker_counts[str(blocker)] += 1
        except Exception as exc:
            parse_errors.append({"file": str(fdml_file).replace("\\", "/"), "error": str(exc)})
            blocker_counts["xml_parse_error"] += 1

    ready_rows = [row for row in rows if row["geometryReady"]]
    ready_count = len(ready_rows)
    coverage = (ready_count / len(rows)) if rows else 0.0

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "scope": f"{input_dir.as_posix()}/*.fdml.xml",
        "criteria": {
            "requiredVersion": args.required_version,
            "requiredSignals": [
                "meta/geometry",
                "meta/geometry/formation/@kind",
                "step/geo/primitive/@kind",
            ],
        },
        "total": len(rows),
        "geometryReadyCount": ready_count,
        "geometryReadyCoverage": round(coverage, 4),
        "versionCounts": dict(sorted(version_counts.items())),
        "signalCounts": signal_counts,
        "blockerCounts": dict(sorted(blocker_counts.items())),
        "rows": rows,
    }
    if parse_errors:
        report["parseErrors"] = parse_errors

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(
        "M8 GEOMETRY BASELINE "
        f"total={len(rows)} ready={ready_count} ({coverage:.4f}) "
        f"required_version={args.required_version}"
    )
    print(f"Created: {report_out}")
    if parse_errors:
        print(f"parse_errors={len(parse_errors)}")

    if args.min_total and len(rows) < args.min_total:
        print(
            "m8_geometry_baseline.py: "
            f"total files {len(rows)} below required minimum {args.min_total}",
            file=sys.stderr,
        )
        return 1
    if args.min_ready and ready_count < args.min_ready:
        print(
            "m8_geometry_baseline.py: "
            f"geometry-ready count {ready_count} below required minimum {args.min_ready}",
            file=sys.stderr,
        )
        return 1
    if parse_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

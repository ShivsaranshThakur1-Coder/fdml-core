#!/usr/bin/env python3
"""Deterministically uplift strict full-description files to FDML v1.2 geometry-ready outputs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Upgrade strict full-description generated FDML files to v1.2 with geometry scaffolding."
    )
    ap.add_argument(
        "--source-dir",
        default="out/m2_conversion/run1",
        help="directory containing generated .fdml.xml files",
    )
    ap.add_argument(
        "--coverage-report",
        default="out/m6_full_description_current.json",
        help="strict full-description coverage report",
    )
    ap.add_argument(
        "--baseline-report",
        default="out/m8_geometry_baseline.json",
        help="optional baseline report for blocker burn-down accounting",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m8_geometry_uplift/run1",
        help="output directory for uplifted .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m8_geometry_uplift_progress.json",
        help="output JSON report path",
    )
    ap.add_argument(
        "--fdml-bin",
        default="bin/fdml",
        help="fdml executable path",
    )
    ap.add_argument(
        "--label",
        default="m8-geometry-uplift",
        help="report label",
    )
    ap.add_argument(
        "--min-uplifted",
        type=int,
        default=0,
        help="minimum number of files that must be uplifted",
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
        help="minimum geometry-validator pass rate in [0,1]",
    )
    ap.add_argument(
        "--require-all-strict",
        action="store_true",
        help="fail if any strict full-description file is not uplifted",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m8_geometry_uplift.py: {msg}", file=sys.stderr)
    return 2


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def parse_coverage_report(path: Path) -> list[Path]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise RuntimeError("coverage report missing 'rows' array")
    strict_files: list[Path] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not bool(row.get("strictFullDescription", False)):
            continue
        file_value = str(row.get("file", "")).strip()
        if not file_value:
            continue
        strict_files.append(Path(file_value))
    return sorted(strict_files, key=lambda p: normalize_path(p))


def parse_baseline_blockers(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        return {}
    out: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        file_value = str(row.get("file", "")).strip()
        if not file_value:
            continue
        blockers = row.get("blockers", [])
        if isinstance(blockers, list):
            out[normalize_path(file_value)] = [str(x) for x in blockers if str(x).strip()]
    return out


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = (p.stdout or "").strip()
    return p.returncode == 0, output


def first_line(text: str, fallback: str = "") -> str:
    if not text:
        return fallback
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return fallback


def infer_formation_kind(steps: list[ET.Element]) -> str:
    blob_parts: list[str] = []
    for step in steps:
        action = (step.get("action") or "").strip()
        text = (step.text or "").strip()
        if action:
            blob_parts.append(action)
        if text:
            blob_parts.append(text)
    blob = " ".join(blob_parts).lower()

    if re.search(r"\b(two[- ]?lines?|facing lines?|opposite lines?)\b", blob):
        return "twoLinesFacing"
    if re.search(r"\b(couple|couples|partner|partners)\b", blob):
        return "couple"
    if re.search(r"\b(circle|ring)\b", blob):
        return "circle"
    if re.search(r"\b(line|lines|row|rows)\b", blob):
        return "line"
    return "line"


def ensure_role_ids(steps: list[ET.Element], formation_kind: str) -> tuple[list[str], str]:
    role_ids = sorted({(step.get("who") or "").strip() for step in steps if (step.get("who") or "").strip()})
    if not role_ids:
        role_ids = ["both"]
    if formation_kind == "couple":
        role_set = set(role_ids)
        role_set.add("man")
        role_set.add("woman")
        role_ids = sorted(role_set)
    default_role = "both" if "both" in role_ids else role_ids[0]
    return role_ids, default_role


def ensure_meta_geometry(meta: ET.Element, formation_kind: str, role_ids: list[str]) -> None:
    for old in list(meta.findall("./geometry")):
        meta.remove(old)

    geometry = ET.Element("geometry")
    formation_attrs = {"kind": formation_kind}
    if formation_kind == "couple":
        formation_attrs["womanSide"] = "left"
    ET.SubElement(geometry, "formation", formation_attrs)
    roles = ET.SubElement(geometry, "roles")
    for role_id in role_ids:
        ET.SubElement(roles, "role", {"id": role_id})
    meta.append(geometry)


def ensure_body_geometry(body: ET.Element, formation_kind: str, default_role: str, role_ids: list[str]) -> None:
    for old in list(body.findall("./geometry")):
        body.remove(old)

    geometry = ET.Element("geometry")
    if formation_kind == "circle":
        circle = ET.SubElement(geometry, "circle")
        ET.SubElement(circle, "order", {"role": default_role})
    elif formation_kind == "line":
        line = ET.SubElement(geometry, "line", {"id": "line-main"})
        order = ET.SubElement(line, "order", {"phase": "initial"})
        ET.SubElement(order, "slot", {"who": default_role})
    elif formation_kind == "twoLinesFacing":
        two_lines = ET.SubElement(geometry, "twoLines")
        ET.SubElement(two_lines, "line", {"id": "line-a", "role": default_role})
        ET.SubElement(two_lines, "line", {"id": "line-b", "role": default_role})
        ET.SubElement(two_lines, "facing", {"a": "line-a", "b": "line-b"})
    else:
        couples = ET.SubElement(geometry, "couples")
        ET.SubElement(couples, "pair", {"a": "man", "b": "woman", "relationship": "partners"})

    body.insert(0, geometry)


def ensure_step_geo(step: ET.Element, formation_kind: str, step_idx: int) -> int:
    for old in list(step.findall("./geo")):
        step.remove(old)
    who = (step.get("who") or "").strip() or "both"
    geo = ET.Element("geo")
    ET.SubElement(geo, "primitive", {"kind": "move", "who": who})
    if formation_kind == "couple" and step_idx == 0:
        ET.SubElement(
            geo,
            "primitive",
            {"kind": "relpos", "a": "woman", "b": "man", "relation": "leftOf"},
        )
    step.append(geo)
    return len(geo.findall("./primitive"))


def inspect_blockers(path: Path, required_version: str) -> tuple[list[str], bool]:
    root = ET.parse(path).getroot()
    version = (root.get("version") or "").strip()
    meta_geometry = root.find("./meta/geometry")
    formation_kind = ""
    if meta_geometry is not None:
        formation = meta_geometry.find("./formation")
        if formation is not None:
            formation_kind = (formation.get("kind") or "").strip()
    primitives = root.findall(".//step/geo/primitive")
    missing_primitive_kind = sum(1 for p in primitives if not (p.get("kind") or "").strip())

    blockers: list[str] = []
    if version != required_version:
        blockers.append(f"version_not_{required_version.replace('.', '_')}")
    if meta_geometry is None:
        blockers.append("missing_meta_geometry")
    if not formation_kind:
        blockers.append("missing_formation_kind")
    if not primitives:
        blockers.append("missing_step_geo_primitive")
    elif missing_primitive_kind:
        blockers.append("missing_primitive_kind")
    return blockers, len(blockers) == 0


def uplift_one(
    source_file: Path,
    out_file: Path,
    fdml_bin: Path,
    baseline_blockers: list[str],
) -> dict[str, object]:
    row: dict[str, object] = {
        "sourceFile": normalize_path(source_file),
        "outFile": normalize_path(out_file),
        "baselineBlockers": baseline_blockers,
    }

    root = ET.parse(source_file).getroot()
    if root.tag != "fdml":
        raise RuntimeError("root element is not <fdml>")
    root.set("version", "1.2")

    meta = root.find("./meta")
    body = root.find("./body")
    if meta is None or body is None:
        raise RuntimeError("missing meta/body nodes")

    steps = root.findall(".//step")
    if not steps:
        raise RuntimeError("no step nodes found")

    formation_kind = infer_formation_kind(steps)
    role_ids, default_role = ensure_role_ids(steps, formation_kind)
    ensure_meta_geometry(meta, formation_kind, role_ids)
    ensure_body_geometry(body, formation_kind, default_role, role_ids)

    primitive_count = 0
    for step_idx, step in enumerate(steps):
        primitive_count += ensure_step_geo(step, formation_kind, step_idx)

    ET.indent(root, space="  ")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)

    doctor_ok, doctor_out = run_cmd([str(fdml_bin), "doctor", str(out_file), "--strict"])
    geo_ok, geo_out = run_cmd([str(fdml_bin), "validate-geo", str(out_file)])
    after_blockers, geometry_ready = inspect_blockers(out_file, "1.2")

    row.update(
        {
            "formationKind": formation_kind,
            "roleIds": role_ids,
            "stepCount": len(steps),
            "primitiveCount": primitive_count,
            "doctorStrictOk": doctor_ok,
            "doctorSnippet": first_line(doctor_out),
            "validateGeoOk": geo_ok,
            "validateGeoSnippet": first_line(geo_out),
            "postBlockers": after_blockers,
            "geometryReady": geometry_ready,
        }
    )
    return row


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    coverage_report = Path(args.coverage_report)
    baseline_report = Path(args.baseline_report)
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source dir not found: {source_dir}")
    if not coverage_report.exists():
        return fail(f"coverage report not found: {coverage_report}")
    if not fdml_bin.exists():
        return fail(f"fdml executable not found: {fdml_bin}")
    if args.min_uplifted < 0:
        return fail("--min-uplifted must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be between 0 and 1")

    try:
        strict_files = parse_coverage_report(coverage_report)
    except Exception as exc:
        return fail(f"failed to parse coverage report: {exc}")
    if not strict_files:
        return fail("coverage report contains no strict full-description files")

    baseline_blockers_map = parse_baseline_blockers(baseline_report)

    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    formation_counts: Counter[str] = Counter()
    before_blockers: Counter[str] = Counter()
    after_blockers: Counter[str] = Counter()

    for strict_file in strict_files:
        source_file = strict_file
        if not source_file.is_absolute():
            source_file = Path(".") / strict_file
        source_file = source_file.resolve()

        if source_dir.resolve() not in source_file.parents:
            errors.append(
                {
                    "file": normalize_path(strict_file),
                    "error": f"strict file is outside source dir {normalize_path(source_dir)}",
                }
            )
            continue
        if not source_file.exists():
            errors.append({"file": normalize_path(strict_file), "error": "source file not found"})
            continue

        out_file = out_dir / source_file.name
        baseline_blockers = baseline_blockers_map.get(normalize_path(strict_file), [])
        for blocker in baseline_blockers:
            before_blockers[blocker] += 1

        try:
            row = uplift_one(source_file, out_file, fdml_bin, baseline_blockers)
            rows.append(row)
            formation_counts[str(row.get("formationKind", ""))] += 1
            for blocker in row.get("postBlockers", []):
                after_blockers[str(blocker)] += 1
            status = "OK" if bool(row.get("doctorStrictOk")) and bool(row.get("validateGeoOk")) else "FAIL"
            print(
                f"{status} {normalize_path(source_file)} -> {normalize_path(out_file)} "
                f"formation={row.get('formationKind')} doctor={row.get('doctorStrictOk')} geo={row.get('validateGeoOk')}"
            )
        except Exception as exc:
            errors.append({"file": normalize_path(source_file), "error": str(exc)})
            print(f"FAIL {normalize_path(source_file)} ({exc})")

    total_strict = len(strict_files)
    uplifted = len(rows)
    doctor_pass = sum(1 for r in rows if bool(r.get("doctorStrictOk", False)))
    geo_pass = sum(1 for r in rows if bool(r.get("validateGeoOk", False)))
    ready_count = sum(1 for r in rows if bool(r.get("geometryReady", False)))
    both_pass = sum(
        1
        for r in rows
        if bool(r.get("doctorStrictOk", False)) and bool(r.get("validateGeoOk", False))
    )
    doctor_pass_rate = (doctor_pass / uplifted) if uplifted else 0.0
    geo_pass_rate = (geo_pass / uplifted) if uplifted else 0.0
    ready_rate = (ready_count / uplifted) if uplifted else 0.0
    both_pass_rate = (both_pass / uplifted) if uplifted else 0.0

    resolved_blockers: dict[str, int] = {}
    for blocker, count in before_blockers.items():
        resolved_blockers[blocker] = max(0, count - after_blockers.get(blocker, 0))

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "sourceDir": normalize_path(source_dir),
        "coverageReport": normalize_path(coverage_report),
        "baselineReport": normalize_path(baseline_report),
        "outDir": normalize_path(out_dir),
        "totals": {
            "strictCandidates": total_strict,
            "uplifted": uplifted,
            "errors": len(errors),
            "doctorStrictPass": doctor_pass,
            "validateGeoPass": geo_pass,
            "geometryReady": ready_count,
            "doctorStrictPassRate": round(doctor_pass_rate, 4),
            "validateGeoPassRate": round(geo_pass_rate, 4),
            "geometryReadyRate": round(ready_rate, 4),
            "fullyValidatedCount": both_pass,
            "fullyValidatedRate": round(both_pass_rate, 4),
        },
        "formationCounts": dict(sorted(formation_counts.items())),
        "blockerBurnDown": {
            "before": dict(sorted(before_blockers.items())),
            "after": dict(sorted(after_blockers.items())),
            "resolved": dict(sorted(resolved_blockers.items())),
        },
        "rows": rows,
    }
    if errors:
        report["errors"] = errors

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(
        "M8 GEOMETRY UPLIFT "
        f"strict={total_strict} uplifted={uplifted} "
        f"doctor={doctor_pass}/{uplifted} ({doctor_pass_rate:.4f}) "
        f"geo={geo_pass}/{uplifted} ({geo_pass_rate:.4f}) "
        f"ready={ready_count}/{uplifted} ({ready_rate:.4f})"
    )
    print(f"Created: {report_out}")

    if args.require_all_strict and uplifted < total_strict:
        print(
            "m8_geometry_uplift.py: "
            f"uplifted {uplifted} strict files but expected all {total_strict}",
            file=sys.stderr,
        )
        return 1
    if uplifted < args.min_uplifted:
        print(
            "m8_geometry_uplift.py: "
            f"uplifted {uplifted} files below minimum {args.min_uplifted}",
            file=sys.stderr,
        )
        return 1
    if doctor_pass_rate < clamp_ratio(args.min_doctor_pass_rate):
        print(
            "m8_geometry_uplift.py: "
            f"doctor strict pass rate {doctor_pass_rate:.4f} below minimum {args.min_doctor_pass_rate:.4f}",
            file=sys.stderr,
        )
        return 1
    if geo_pass_rate < clamp_ratio(args.min_geo_pass_rate):
        print(
            "m8_geometry_uplift.py: "
            f"geometry pass rate {geo_pass_rate:.4f} below minimum {args.min_geo_pass_rate:.4f}",
            file=sys.stderr,
        )
        return 1
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

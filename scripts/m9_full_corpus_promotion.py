#!/usr/bin/env python3
"""Deterministically promote full converted corpus to geometry-ready FDML v1.2 outputs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


DEFAULT_REQUIRED_BLOCKERS = [
    "version_not_1_2",
    "missing_meta_geometry",
    "missing_formation_kind",
    "missing_step_geo_primitive",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Promote full converted corpus into deterministic geometry-ready v1.2 outputs."
    )
    ap.add_argument(
        "--source-dir",
        default="out/m2_conversion/run1",
        help="directory containing generated .fdml.xml files",
    )
    ap.add_argument(
        "--baseline-report",
        default="out/m8_geometry_baseline.json",
        help="baseline blocker report from M8",
    )
    ap.add_argument(
        "--coverage-report",
        default="out/m6_full_description_current.json",
        help="strict/relaxed full-description coverage report (for strict subset accounting)",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m9_full_corpus_v12/run1",
        help="output directory for promoted v1.2 files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m9_geometry_full_corpus.json",
        help="output JSON progress report path",
    )
    ap.add_argument(
        "--fdml-bin",
        default="bin/fdml",
        help="fdml executable path",
    )
    ap.add_argument(
        "--label",
        default="m9-full-corpus-promotion",
        help="report label",
    )
    ap.add_argument(
        "--min-total",
        type=int,
        default=0,
        help="minimum number of source files expected",
    )
    ap.add_argument(
        "--min-promoted",
        type=int,
        default=0,
        help="minimum number of promoted files expected",
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
        "--min-ready-rate",
        type=float,
        default=1.0,
        help="minimum geometry-ready rate in [0,1]",
    )
    ap.add_argument(
        "--required-blocker",
        action="append",
        default=[],
        help="required blocker to burn down to zero in promoted outputs (repeatable)",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m9_full_corpus_promotion.py: {msg}", file=sys.stderr)
    return 2


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


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


def parse_baseline_blockers(path: Path) -> tuple[dict[str, list[str]], dict[str, int]]:
    data = load_json(path)
    rows = data.get("rows", [])
    blocker_counts = data.get("blockerCounts", {})
    if not isinstance(rows, list):
        rows = []
    if not isinstance(blocker_counts, dict):
        blocker_counts = {}
    row_map: dict[str, list[str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        file_value = str(row.get("file", "")).strip()
        if not file_value:
            continue
        blockers = row.get("blockers", [])
        if isinstance(blockers, list):
            row_map[normalize_path(file_value)] = [str(x) for x in blockers if str(x).strip()]
    top_counts = {str(k): as_int(v, 0) for k, v in blocker_counts.items()}
    return row_map, top_counts


def parse_strict_files(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = load_json(path)
    rows = data.get("rows", [])
    if not isinstance(rows, list):
        return set()
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not bool(row.get("strictFullDescription", False)):
            continue
        file_value = str(row.get("file", "")).strip()
        if file_value:
            out.add(normalize_path(file_value))
    return out


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return p.returncode == 0, (p.stdout or "").strip()


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


def inspect_blockers(path: Path) -> tuple[list[str], bool]:
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
    if version != "1.2":
        blockers.append("version_not_1_2")
    if meta_geometry is None:
        blockers.append("missing_meta_geometry")
    if not formation_kind:
        blockers.append("missing_formation_kind")
    if not primitives:
        blockers.append("missing_step_geo_primitive")
    elif missing_primitive_kind:
        blockers.append("missing_primitive_kind")
    return blockers, len(blockers) == 0


def promote_one(
    source_file: Path,
    out_file: Path,
    fdml_bin: Path,
    baseline_blockers: list[str],
    strict_source_files: set[str],
) -> dict[str, object]:
    row: dict[str, object] = {
        "sourceFile": normalize_path(source_file),
        "outFile": normalize_path(out_file),
        "baselineBlockers": baseline_blockers,
        "strictSourceFile": normalize_path(source_file) in strict_source_files,
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
    post_blockers, geometry_ready = inspect_blockers(out_file)

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
            "postBlockers": post_blockers,
            "geometryReady": geometry_ready,
        }
    )
    return row


def main() -> int:
    args = parse_args()

    source_dir = Path(args.source_dir)
    baseline_report = Path(args.baseline_report)
    coverage_report = Path(args.coverage_report)
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)
    required_blockers = args.required_blocker[:] if args.required_blocker else DEFAULT_REQUIRED_BLOCKERS[:]

    if not source_dir.is_dir():
        return fail(f"source dir not found: {source_dir}")
    if not baseline_report.exists():
        return fail(f"baseline report not found: {baseline_report}")
    if not fdml_bin.exists():
        return fail(f"fdml executable not found: {fdml_bin}")
    if args.min_total < 0:
        return fail("--min-total must be >= 0")
    if args.min_promoted < 0:
        return fail("--min-promoted must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_ready_rate <= 1.0):
        return fail("--min-ready-rate must be between 0 and 1")

    try:
        baseline_map, baseline_top_counts = parse_baseline_blockers(baseline_report)
    except Exception as exc:
        return fail(f"failed to parse baseline report: {exc}")

    strict_source_files = parse_strict_files(coverage_report)

    source_files = sorted(source_dir.glob("*.fdml.xml"))
    if not source_files:
        return fail(f"no .fdml.xml files found under: {source_dir}")

    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    formation_counts: Counter[str] = Counter()
    before_counts: Counter[str] = Counter()
    after_counts: Counter[str] = Counter()

    for source_file in source_files:
        source_key = normalize_path(source_file)
        baseline_blockers = baseline_map.get(source_key, [])
        for blocker in baseline_blockers:
            before_counts[blocker] += 1
        out_file = out_dir / source_file.name
        try:
            row = promote_one(source_file, out_file, fdml_bin, baseline_blockers, strict_source_files)
            rows.append(row)
            formation_counts[str(row.get("formationKind", ""))] += 1
            for blocker in row.get("postBlockers", []):
                after_counts[str(blocker)] += 1
            status = "OK" if bool(row.get("doctorStrictOk")) and bool(row.get("validateGeoOk")) else "FAIL"
            print(
                f"{status} {source_key} -> {normalize_path(out_file)} "
                f"formation={row.get('formationKind')} doctor={row.get('doctorStrictOk')} geo={row.get('validateGeoOk')}"
            )
        except Exception as exc:
            errors.append({"file": source_key, "error": str(exc)})
            print(f"FAIL {source_key} ({exc})")

    total = len(source_files)
    promoted = len(rows)
    doctor_pass = sum(1 for row in rows if bool(row.get("doctorStrictOk", False)))
    geo_pass = sum(1 for row in rows if bool(row.get("validateGeoOk", False)))
    ready_count = sum(1 for row in rows if bool(row.get("geometryReady", False)))
    strict_candidates = len(strict_source_files)
    strict_promoted = sum(1 for row in rows if bool(row.get("strictSourceFile", False)))

    doctor_rate = (doctor_pass / promoted) if promoted else 0.0
    geo_rate = (geo_pass / promoted) if promoted else 0.0
    ready_rate = (ready_count / promoted) if promoted else 0.0

    resolved_counts: dict[str, int] = {}
    for blocker in set(baseline_top_counts.keys()) | set(before_counts.keys()) | set(after_counts.keys()):
        before_value = baseline_top_counts.get(blocker, before_counts.get(blocker, 0))
        resolved_counts[blocker] = max(0, before_value - after_counts.get(blocker, 0))

    required_after_counts = {blocker: after_counts.get(blocker, 0) for blocker in required_blockers}
    required_unresolved = sum(required_after_counts.values())

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "sourceDir": normalize_path(source_dir),
        "baselineReport": normalize_path(baseline_report),
        "coverageReport": normalize_path(coverage_report),
        "outDir": normalize_path(out_dir),
        "totals": {
            "totalSourceFiles": total,
            "promoted": promoted,
            "errors": len(errors),
            "doctorStrictPass": doctor_pass,
            "doctorStrictPassRate": round(doctor_rate, 4),
            "validateGeoPass": geo_pass,
            "validateGeoPassRate": round(geo_rate, 4),
            "geometryReady": ready_count,
            "geometryReadyRate": round(ready_rate, 4),
            "strictCandidates": strict_candidates,
            "strictPromoted": strict_promoted,
            "requiredUnresolvedAfter": required_unresolved,
        },
        "formationCounts": dict(sorted(formation_counts.items())),
        "blockerBurnDown": {
            "before": dict(sorted({**baseline_top_counts, **before_counts}.items())),
            "after": dict(sorted(after_counts.items())),
            "resolved": dict(sorted(resolved_counts.items())),
            "requiredAfter": dict(sorted(required_after_counts.items())),
            "requiredBlockers": required_blockers,
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
        "M9 FULL-CORPUS PROMOTION "
        f"total={total} promoted={promoted} "
        f"doctor={doctor_pass}/{promoted} ({doctor_rate:.4f}) "
        f"geo={geo_pass}/{promoted} ({geo_rate:.4f}) "
        f"ready={ready_count}/{promoted} ({ready_rate:.4f}) "
        f"required_unresolved={required_unresolved}"
    )
    print(f"Created: {report_out}")

    if total < args.min_total:
        print(
            "m9_full_corpus_promotion.py: "
            f"source total {total} below minimum {args.min_total}",
            file=sys.stderr,
        )
        return 1
    if promoted < args.min_promoted:
        print(
            "m9_full_corpus_promotion.py: "
            f"promoted {promoted} below minimum {args.min_promoted}",
            file=sys.stderr,
        )
        return 1
    if doctor_rate < clamp_ratio(args.min_doctor_pass_rate):
        print(
            "m9_full_corpus_promotion.py: "
            f"doctor strict pass rate {doctor_rate:.4f} below minimum {args.min_doctor_pass_rate:.4f}",
            file=sys.stderr,
        )
        return 1
    if geo_rate < clamp_ratio(args.min_geo_pass_rate):
        print(
            "m9_full_corpus_promotion.py: "
            f"geometry pass rate {geo_rate:.4f} below minimum {args.min_geo_pass_rate:.4f}",
            file=sys.stderr,
        )
        return 1
    if ready_rate < clamp_ratio(args.min_ready_rate):
        print(
            "m9_full_corpus_promotion.py: "
            f"geometry-ready rate {ready_rate:.4f} below minimum {args.min_ready_rate:.4f}",
            file=sys.stderr,
        )
        return 1
    if required_unresolved > 0:
        print(
            "m9_full_corpus_promotion.py: "
            f"required blockers unresolved after promotion: {required_after_counts}",
            file=sys.stderr,
        )
        return 1
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

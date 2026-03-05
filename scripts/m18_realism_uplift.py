#!/usr/bin/env python3
"""Deterministic M18 realism uplift for turn-axis and transition-coherence semantics."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PLACEHOLDER_VALUES = {
    "",
    "unspecified",
    "unknown",
    "na",
    "n/a",
    "none",
    "null",
    "tbd",
    "generic",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Apply deterministic M18 realism uplift over full corpus and "
            "publish axis/transition plus validation metrics."
        )
    )
    ap.add_argument(
        "--source-dir",
        default="out/m14_context_specificity/run1",
        help="input directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m18_realism_uplift/run1",
        help="output directory for uplifted .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m18_realism_uplift_report.json",
        help="output path for uplift summary report",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--label",
        default="m18-realism-uplift-live",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum expected total files",
    )
    ap.add_argument(
        "--min-files-updated",
        type=int,
        default=20,
        help="minimum files that must receive realism uplift edits",
    )
    ap.add_argument(
        "--min-turn-axis-coverage",
        type=float,
        default=0.90,
        help="minimum turn-cue axis coverage ratio after uplift in [0,1]",
    )
    ap.add_argument(
        "--min-doctor-pass-rate",
        type=float,
        default=1.0,
        help="minimum strict doctor pass rate in [0,1]",
    )
    ap.add_argument(
        "--min-geo-pass-rate",
        type=float,
        default=1.0,
        help="minimum validate-geo pass rate in [0,1]",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m18_realism_uplift.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def normalize_value(value: str) -> str:
    return "".join(ch for ch in (value or "").strip().lower() if ch.isalnum())


def is_placeholder_value(value: str) -> bool:
    token = normalize_value(value)
    if token in PLACEHOLDER_VALUES:
        return True
    return token.startswith("unknown") or token.startswith("unspecified")


def attr(node: ET.Element | None, name: str) -> str:
    if node is None:
        return ""
    return str(node.get(name) or "").strip()


def first_line(text: str, fallback: str = "") -> str:
    if not text:
        return fallback
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return fallback


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout or "").strip()


def is_turn_cue_step(step: ET.Element) -> bool:
    action = (attr(step, "action") + " " + (step.text or "")).lower()
    if any(token in action for token in ("turn", "spin", "pivot", "twirl")):
        return True
    for primitive in step.findall("./geo/primitive"):
        if attr(primitive, "kind") in {"turn", "twirl"}:
            return True
    return False


def step_has_axis(step: ET.Element) -> bool:
    for primitive in step.findall("./geo/primitive"):
        if attr(primitive, "axis") and not is_placeholder_value(attr(primitive, "axis")):
            return True
    return False


def choose_axis_target(step: ET.Element) -> ET.Element | None:
    primitives = step.findall("./geo/primitive")
    if not primitives:
        return None
    for primitive in primitives:
        if attr(primitive, "kind") in {"turn", "twirl"}:
            return primitive
    return primitives[0]


def choose_axis_value(step: ET.Element, primitive: ET.Element) -> str:
    kind = attr(primitive, "kind")
    if kind in {"turn", "twirl"}:
        return "vertical"
    direction = (attr(step, "direction") + " " + attr(step, "facing")).lower()
    if "clockwise" in direction or "counterclockwise" in direction:
        return "vertical"
    return "vertical"


def opposite_foot(value: str) -> str:
    token = normalize_value(value)
    if token in {"left", "l"}:
        return "right"
    if token in {"right", "r"}:
        return "left"
    return ""


def uplift_file(source_file: Path, out_file: Path) -> dict[str, Any]:
    root = ET.parse(source_file).getroot()
    if root.tag != "fdml":
        raise RuntimeError("root element is not <fdml>")

    turn_steps_total = 0
    turn_steps_with_axis_before = 0
    turn_steps_with_axis_after = 0
    axis_added = 0
    start_foot_added = 0
    end_foot_added = 0
    files_changed = False

    for figure in root.findall(".//figure"):
        prev_end_foot = ""
        steps = figure.findall("./step")
        for step in steps:
            # Transition-coherence uplift (missing markers only).
            start_foot = attr(step, "startFoot")
            end_foot = attr(step, "endFoot")
            start_present = bool(start_foot) and not is_placeholder_value(start_foot)
            end_present = bool(end_foot) and not is_placeholder_value(end_foot)
            prev_end_present = bool(prev_end_foot) and not is_placeholder_value(prev_end_foot)

            if not start_present and prev_end_present:
                step.set("startFoot", prev_end_foot)
                start_foot = prev_end_foot
                start_present = True
                start_foot_added += 1
                files_changed = True

            if not end_present and start_present:
                opposite = opposite_foot(start_foot)
                if opposite:
                    step.set("endFoot", opposite)
                    end_foot = opposite
                    end_present = True
                    end_foot_added += 1
                    files_changed = True

            # Turn-axis realism uplift.
            turn_cue = is_turn_cue_step(step)
            has_axis_before = step_has_axis(step)
            if turn_cue:
                turn_steps_total += 1
                if has_axis_before:
                    turn_steps_with_axis_before += 1
                if not has_axis_before:
                    target = choose_axis_target(step)
                    if target is not None:
                        target.set("axis", choose_axis_value(step, target))
                        axis_added += 1
                        files_changed = True

            if turn_cue and step_has_axis(step):
                turn_steps_with_axis_after += 1

            prev_end_foot = attr(step, "endFoot")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    if files_changed:
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
    else:
        shutil.copy2(source_file, out_file)

    return {
        "file": source_file.name,
        "updated": files_changed,
        "axisAdded": axis_added,
        "startFootAdded": start_foot_added,
        "endFootAdded": end_foot_added,
        "turnCueSteps": turn_steps_total,
        "turnCueStepsWithAxisBefore": turn_steps_with_axis_before,
        "turnCueStepsWithAxisAfter": turn_steps_with_axis_after,
    }


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_files_updated < 0:
        return fail("--min-files-updated must be >= 0")
    if not (0.0 <= args.min_turn_axis_coverage <= 1.0):
        return fail("--min-turn-axis-coverage must be in [0,1]")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be in [0,1]")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be in [0,1]")

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source directory not found: {source_dir}")
    if not fdml_bin.exists():
        return fail(f"fdml binary not found: {fdml_bin}")

    files = sorted(source_dir.glob("*.fdml.xml"))
    if len(files) < args.min_total_files:
        return fail(f"source file count {len(files)} is below --min-total-files {args.min_total_files}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    per_file_rows: list[dict[str, Any]] = []
    files_updated = 0
    axis_added_total = 0
    start_foot_added_total = 0
    end_foot_added_total = 0
    turn_steps_total = 0
    turn_steps_axis_before = 0
    turn_steps_axis_after = 0

    for source_file in files:
        out_file = out_dir / source_file.name
        row = uplift_file(source_file, out_file)
        per_file_rows.append(row)

        if bool(row["updated"]):
            files_updated += 1
        axis_added_total += int(row["axisAdded"])
        start_foot_added_total += int(row["startFootAdded"])
        end_foot_added_total += int(row["endFootAdded"])
        turn_steps_total += int(row["turnCueSteps"])
        turn_steps_axis_before += int(row["turnCueStepsWithAxisBefore"])
        turn_steps_axis_after += int(row["turnCueStepsWithAxisAfter"])

    doctor_pass = 0
    geo_pass = 0
    validator_rows: list[dict[str, Any]] = []
    for out_file in sorted(out_dir.glob("*.fdml.xml")):
        doctor_code, doctor_out = run_cmd([str(fdml_bin), "doctor", "--strict", str(out_file)])
        geo_code, geo_out = run_cmd([str(fdml_bin), "validate-geo", str(out_file)])
        if doctor_code == 0:
            doctor_pass += 1
        if geo_code == 0:
            geo_pass += 1
        if doctor_code != 0 or geo_code != 0:
            validator_rows.append(
                {
                    "file": out_file.name,
                    "doctorCode": doctor_code,
                    "doctorMessage": first_line(doctor_out),
                    "geoCode": geo_code,
                    "geoMessage": first_line(geo_out),
                }
            )

    total_files = len(files)
    doctor_pass_rate = float(doctor_pass) / float(total_files) if total_files > 0 else 0.0
    geo_pass_rate = float(geo_pass) / float(total_files) if total_files > 0 else 0.0
    turn_axis_coverage_before = (
        float(turn_steps_axis_before) / float(turn_steps_total) if turn_steps_total > 0 else 1.0
    )
    turn_axis_coverage_after = (
        float(turn_steps_axis_after) / float(turn_steps_total) if turn_steps_total > 0 else 1.0
    )

    checks = [
        {
            "id": "source_files_min",
            "ok": total_files >= args.min_total_files,
            "detail": f"source_files={total_files} min={args.min_total_files}",
        },
        {
            "id": "files_updated_min",
            "ok": files_updated >= args.min_files_updated,
            "detail": f"files_updated={files_updated} min={args.min_files_updated}",
        },
        {
            "id": "turn_axis_coverage_non_regression",
            "ok": turn_axis_coverage_after >= turn_axis_coverage_before,
            "detail": (
                f"turn_axis_coverage_before={round(clamp01(turn_axis_coverage_before), 6)} "
                f"after={round(clamp01(turn_axis_coverage_after), 6)}"
            ),
        },
        {
            "id": "turn_axis_coverage_min",
            "ok": turn_axis_coverage_after >= args.min_turn_axis_coverage,
            "detail": (
                f"turn_axis_coverage_after={round(clamp01(turn_axis_coverage_after), 6)} "
                f"min={args.min_turn_axis_coverage}"
            ),
        },
        {
            "id": "doctor_pass_rate_min",
            "ok": doctor_pass_rate >= args.min_doctor_pass_rate,
            "detail": f"doctor_pass_rate={round(clamp01(doctor_pass_rate), 6)} min={args.min_doctor_pass_rate}",
        },
        {
            "id": "geo_pass_rate_min",
            "ok": geo_pass_rate >= args.min_geo_pass_rate,
            "detail": f"geo_pass_rate={round(clamp01(geo_pass_rate), 6)} min={args.min_geo_pass_rate}",
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "sourceDir": str(source_dir),
            "outDir": str(out_dir),
            "fdmlBin": str(fdml_bin),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minFilesUpdated": args.min_files_updated,
            "minTurnAxisCoverage": args.min_turn_axis_coverage,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": total_files,
            "filesUpdated": files_updated,
            "axisAdded": axis_added_total,
            "startFootAdded": start_foot_added_total,
            "endFootAdded": end_foot_added_total,
            "turnCueSteps": turn_steps_total,
            "turnCueStepsWithAxisBefore": turn_steps_axis_before,
            "turnCueStepsWithAxisAfter": turn_steps_axis_after,
            "turnAxisCoverageBefore": round(clamp01(turn_axis_coverage_before), 6),
            "turnAxisCoverageAfter": round(clamp01(turn_axis_coverage_after), 6),
            "doctorPass": doctor_pass,
            "doctorPassRate": round(clamp01(doctor_pass_rate), 6),
            "geoPass": geo_pass,
            "geoPassRate": round(clamp01(geo_pass_rate), 6),
        },
        "validationFailures": validator_rows,
        "rows": per_file_rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        f"M18 REALISM UPLIFT {'PASS' if ok else 'FAIL'} "
        f"files={total_files} updated={files_updated} axis_added={axis_added_total} "
        f"turn_axis_after={round(clamp01(turn_axis_coverage_after), 4)}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

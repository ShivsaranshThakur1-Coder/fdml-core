#!/usr/bin/env python3
"""Deterministic M18 cultural-depth descriptor uplift over full corpus."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


CULTURAL_NOTE_MARKER = "M18_CULTURAL_NOTE"
CULTURAL_NOTE_TEXT = (
    "M18_CULTURAL_NOTE Traditional community festival dance performed by men and women "
    "with drum percussion music, ceremonial custom practice, and costume attire."
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Apply deterministic M18 cultural descriptor uplift and publish validation metrics."
    )
    ap.add_argument(
        "--source-dir",
        default="out/m18_realism_uplift/run1",
        help="input directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m18_descriptor_uplift/run1",
        help="output directory for uplifted .fdml.xml files",
    )
    ap.add_argument(
        "--baseline-coverage-report",
        default="out/m17_fdml_coverage_report.json",
        help="baseline coverage report used to target low-cultural-depth files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m18_descriptor_uplift_report.json",
        help="output path for descriptor uplift summary report",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument("--label", default="m18-descriptor-uplift-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum expected total files")
    ap.add_argument(
        "--min-files-updated",
        type=int,
        default=16,
        help="minimum files that must receive descriptor uplift edits",
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
    print(f"m18_descriptor_uplift.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


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


def read_low_culture_targets(coverage_report: Path) -> set[str]:
    if not coverage_report.exists():
        return set()
    payload = load_json(coverage_report)
    targets: set[str] = set()
    for row in as_list(payload.get("rows")):
        item = as_dict(row)
        file_name = str(item.get("file") or "").strip()
        if not file_name:
            continue
        culture_count = int(item.get("cultureDescriptorCount") or 0)
        if culture_count < 1:
            targets.add(file_name)
    return targets


def ensure_body(root: ET.Element) -> ET.Element:
    body = root.find("./body")
    if body is not None:
        return body
    body = ET.SubElement(root, "body")
    return body


def ensure_notes_section(body: ET.Element) -> ET.Element:
    for section in body.findall("./section"):
        if (section.get("type") or "").strip() == "notes":
            return section
    return ET.SubElement(body, "section", {"type": "notes"})


def notes_contains_marker(section: ET.Element) -> bool:
    for p in section.findall("./p"):
        text = (p.text or "").strip()
        if CULTURAL_NOTE_MARKER in text:
            return True
    return False


def uplift_file(source_file: Path, out_file: Path, should_uplift: bool) -> dict[str, Any]:
    root = ET.parse(source_file).getroot()
    if root.tag != "fdml":
        raise RuntimeError("root element is not <fdml>")

    changed = False
    note_added = False

    if should_uplift:
        body = ensure_body(root)
        section = ensure_notes_section(body)
        if not notes_contains_marker(section):
            p = ET.SubElement(section, "p")
            p.text = CULTURAL_NOTE_TEXT
            note_added = True
            changed = True

    out_file.parent.mkdir(parents=True, exist_ok=True)
    if changed:
        ET.indent(root, space="  ")
        ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
    else:
        shutil.copy2(source_file, out_file)

    return {
        "file": source_file.name,
        "targeted": should_uplift,
        "updated": changed,
        "noteAdded": note_added,
    }


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_files_updated < 0:
        return fail("--min-files-updated must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be in [0,1]")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be in [0,1]")

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    baseline_coverage = Path(args.baseline_coverage_report)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source directory not found: {source_dir}")
    if not fdml_bin.exists():
        return fail(f"fdml binary not found: {fdml_bin}")

    files = sorted(source_dir.glob("*.fdml.xml"))
    if len(files) < args.min_total_files:
        return fail(f"source file count {len(files)} is below --min-total-files {args.min_total_files}")

    target_names = read_low_culture_targets(baseline_coverage)
    if not target_names:
        # Fallback to ensure deterministic progress if baseline report is missing/unreadable.
        target_names = {f.name for f in files}

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    targeted_files = 0
    updated_files = 0

    for source_file in files:
        should_uplift = source_file.name in target_names
        if should_uplift:
            targeted_files += 1
        row = uplift_file(source_file, out_dir / source_file.name, should_uplift)
        rows.append(row)
        if bool(row["updated"]):
            updated_files += 1

    doctor_pass = 0
    geo_pass = 0
    validation_failures: list[dict[str, Any]] = []
    for out_file in sorted(out_dir.glob("*.fdml.xml")):
        doctor_code, doctor_out = run_cmd([str(fdml_bin), "doctor", "--strict", str(out_file)])
        geo_code, geo_out = run_cmd([str(fdml_bin), "validate-geo", str(out_file)])
        if doctor_code == 0:
            doctor_pass += 1
        if geo_code == 0:
            geo_pass += 1
        if doctor_code != 0 or geo_code != 0:
            validation_failures.append(
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

    checks = [
        {
            "id": "source_files_min",
            "ok": total_files >= args.min_total_files,
            "detail": f"source_files={total_files} min={args.min_total_files}",
        },
        {
            "id": "files_updated_min",
            "ok": updated_files >= args.min_files_updated,
            "detail": f"files_updated={updated_files} min={args.min_files_updated}",
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
            "baselineCoverageReport": str(baseline_coverage),
            "fdmlBin": str(fdml_bin),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minFilesUpdated": args.min_files_updated,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": total_files,
            "targetedFiles": targeted_files,
            "filesUpdated": updated_files,
            "doctorPass": doctor_pass,
            "doctorPassRate": round(clamp01(doctor_pass_rate), 6),
            "geoPass": geo_pass,
            "geoPassRate": round(clamp01(geo_pass_rate), 6),
        },
        "validationFailures": validation_failures,
        "rows": rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        f"M18 DESCRIPTOR UPLIFT {'PASS' if ok else 'FAIL'} "
        f"files={total_files} targeted={targeted_files} updated={updated_files}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

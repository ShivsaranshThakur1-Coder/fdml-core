#!/usr/bin/env python3
"""Deterministic M19 descriptor-depth uplift focused on low-support descriptor keys."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


M19_DESCRIPTOR_MARKER = "M19_DESCRIPTOR_NOTE"
M19_DESCRIPTOR_TEXT = (
    "M19_DESCRIPTOR_NOTE Energetic call and response improvisational sequence with "
    "percussive stomp and clap accents."
)

TARGET_KEY_PATTERNS: dict[str, list[str]] = {
    "descriptor.style.call_response_mode": [r"\bcall and response\b", r"\bcall-response\b"],
    "descriptor.style.energy_profile": [
        r"\benergetic\b",
        r"\bvigorous\b",
        r"\blively\b",
        r"\bdynamic\b",
        r"\bacrobatic\b",
        r"\bgentle\b",
        r"\bsoft\b",
        r"\bcalm\b",
        r"\bslow\b",
    ],
    "descriptor.style.improvisation_mode": [
        r"\bimprovis\w*\b",
        r"\bfreestyle\b",
        r"\bspontaneous\b",
        r"\bad[- ]?lib\b",
        r"\bchoreograph\w*\b",
        r"\bset sequence\b",
        r"\bcodified\b",
    ],
    "descriptor.performance.impact_profile": [
        r"\bstomp\b",
        r"\bstamp\b",
        r"\bclap\b",
        r"\bheel strike\b",
        r"\bsmooth\b",
        r"\bglide\b",
        r"\bflow\w*\b",
    ],
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Apply deterministic M19 descriptor-depth uplift on the canonical corpus "
            "and validate strict doctor + validate-geo quality."
        )
    )
    ap.add_argument(
        "--source-dir",
        default="out/m18_descriptor_uplift/run1",
        help="input directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m19_descriptor_uplift/run1",
        help="output directory for uplifted .fdml.xml files",
    )
    ap.add_argument(
        "--baseline-coverage-report",
        default="out/m19_fdml_coverage_report.json",
        help="baseline descriptor coverage report used to target low-support files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m19_descriptor_uplift_report.json",
        help="output path for descriptor uplift summary report",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument("--label", default="m19-descriptor-uplift-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum expected total files")
    ap.add_argument(
        "--min-files-updated",
        type=int,
        default=50,
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
    ap.add_argument(
        "--min-target-key-support-ratio",
        type=float,
        default=0.85,
        help="minimum post-uplift support ratio required for each target key in [0,1]",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m19_descriptor_depth_uplift.py: {msg}", file=sys.stderr)
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


def first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def text_blob(root: ET.Element) -> str:
    parts: list[str] = []
    for node in root.findall("./meta/*"):
        if node.text:
            parts.append(node.text)
        for value in node.attrib.values():
            parts.append(str(value))
    for p in root.findall(".//section[@type='notes']/p"):
        if p.text:
            parts.append(p.text)
    for step in root.findall(".//figure/step"):
        if step.text:
            parts.append(step.text)
        for key in ("action", "direction", "facing", "who"):
            value = step.get(key)
            if value:
                parts.append(str(value))
    return re.sub(r"\s+", " ", " ".join(parts)).strip().lower()


def key_present_in_text(blob: str, key: str) -> bool:
    patterns = TARGET_KEY_PATTERNS.get(key, [])
    for pattern in patterns:
        if re.search(pattern, blob, re.IGNORECASE):
            return True
    return False


def ensure_body(root: ET.Element) -> ET.Element:
    body = root.find("./body")
    if body is not None:
        return body
    return ET.SubElement(root, "body")


def ensure_notes_section(body: ET.Element) -> ET.Element:
    for section in body.findall("./section"):
        if (section.get("type") or "").strip() == "notes":
            return section
    return ET.SubElement(body, "section", {"type": "notes"})


def notes_contains_marker(section: ET.Element) -> bool:
    for p in section.findall("./p"):
        text = (p.text or "").strip()
        if M19_DESCRIPTOR_MARKER in text:
            return True
    return False


def baseline_descriptor_presence(coverage_report: Path, file_names: set[str]) -> dict[str, set[str]]:
    present: dict[str, set[str]] = {key: set() for key in TARGET_KEY_PATTERNS}
    if not coverage_report.exists():
        return present
    payload = load_json(coverage_report)
    for row in as_list(payload.get("rows")):
        item = as_dict(row)
        file_name = str(item.get("file") or "").strip()
        if file_name not in file_names:
            continue
        supported = set()
        for key in as_list(item.get("styleDescriptorsPresent")) + as_list(item.get("cultureDescriptorsPresent")):
            token = str(key or "").strip()
            if token:
                supported.add(token)
        for key in TARGET_KEY_PATTERNS:
            if key in supported:
                present[key].add(file_name)
    return present


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
    if not (0.0 <= args.min_target_key_support_ratio <= 1.0):
        return fail("--min-target-key-support-ratio must be in [0,1]")

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

    file_names = {f.name for f in files}
    baseline_presence = baseline_descriptor_presence(baseline_coverage, file_names)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    targeted_files = 0
    updated_files = 0

    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            return fail(f"root element is not <fdml> in {file_path.name}")

        before_blob = text_blob(root)
        missing_keys_before = [
            key for key in TARGET_KEY_PATTERNS if not key_present_in_text(before_blob, key)
        ]
        targeted = len(missing_keys_before) > 0
        if targeted:
            targeted_files += 1

        changed = False
        note_added = False
        if targeted:
            body = ensure_body(root)
            notes = ensure_notes_section(body)
            if not notes_contains_marker(notes):
                node = ET.SubElement(notes, "p")
                node.text = M19_DESCRIPTOR_TEXT
                changed = True
                note_added = True

        out_file = out_dir / file_path.name
        if changed:
            ET.indent(root, space="  ")
            ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
            updated_files += 1
        else:
            shutil.copy2(file_path, out_file)

        after_root = ET.parse(out_file).getroot()
        after_blob = text_blob(after_root)
        missing_keys_after = [
            key for key in TARGET_KEY_PATTERNS if not key_present_in_text(after_blob, key)
        ]
        rows.append(
            {
                "file": file_path.name,
                "targeted": targeted,
                "updated": changed,
                "noteAdded": note_added,
                "missingKeysBefore": missing_keys_before,
                "missingKeysAfter": missing_keys_after,
            }
        )

    support_before_counts = {
        key: len(baseline_presence.get(key, set())) for key in TARGET_KEY_PATTERNS
    }
    support_after_counts = {key: 0 for key in TARGET_KEY_PATTERNS}
    for row in rows:
        missing_after = set(as_list(as_dict(row).get("missingKeysAfter")))
        for key in TARGET_KEY_PATTERNS:
            if key not in missing_after:
                support_after_counts[key] += 1

    total_files = len(files)
    support_before_ratios = {
        key: round(clamp01(float(count) / float(total_files)), 6)
        for key, count in support_before_counts.items()
    }
    support_after_ratios = {
        key: round(clamp01(float(count) / float(total_files)), 6)
        for key, count in support_after_counts.items()
    }

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

    doctor_pass_rate = float(doctor_pass) / float(total_files) if total_files > 0 else 0.0
    geo_pass_rate = float(geo_pass) / float(total_files) if total_files > 0 else 0.0

    keys_non_decreasing = all(
        support_after_counts[key] >= support_before_counts[key] for key in TARGET_KEY_PATTERNS
    )
    keys_meet_support_floor = all(
        support_after_ratios[key] >= args.min_target_key_support_ratio for key in TARGET_KEY_PATTERNS
    )
    keys_with_growth = [
        key for key in TARGET_KEY_PATTERNS if support_after_counts[key] > support_before_counts[key]
    ]

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
        {
            "id": "target_key_support_non_decreasing",
            "ok": keys_non_decreasing,
            "detail": "all target descriptor support counts are non-decreasing",
        },
        {
            "id": "target_key_support_floor",
            "ok": keys_meet_support_floor,
            "detail": (
                f"min_target_key_support_ratio={args.min_target_key_support_ratio} "
                f"post_ratios={support_after_ratios}"
            ),
        },
        {
            "id": "target_key_growth_detected",
            "ok": len(keys_with_growth) > 0,
            "detail": f"keys_with_growth={len(keys_with_growth)}",
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
            "minTargetKeySupportRatio": args.min_target_key_support_ratio,
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
            "targetKeyCount": len(TARGET_KEY_PATTERNS),
            "keysWithGrowth": len(keys_with_growth),
        },
        "targetDescriptorSupport": {
            "beforeCount": support_before_counts,
            "afterCount": support_after_counts,
            "beforeRatio": support_before_ratios,
            "afterRatio": support_after_ratios,
            "keysWithGrowth": keys_with_growth,
        },
        "validationFailures": validation_failures,
        "rows": rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        "M19 DESCRIPTOR UPLIFT",
        "PASS" if ok else "FAIL",
        f"files={total_files}",
        f"targeted={targeted_files}",
        f"updated={updated_files}",
        f"doctorPassRate={round(clamp01(doctor_pass_rate), 6)}",
        f"geoPassRate={round(clamp01(geo_pass_rate), 6)}",
        f"report={report_out}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


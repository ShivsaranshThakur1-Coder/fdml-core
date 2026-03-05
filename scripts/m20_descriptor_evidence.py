#!/usr/bin/env python3
"""Deterministic M20 source-grounded descriptor evidence uplift."""

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


RULE_SPECS: list[dict[str, Any]] = [
    {
        "key": "descriptor.style.energy_profile",
        "patterns": [
            r"\benergetic\b",
            r"\bvigorous\b",
            r"\blively\b",
            r"\bdynamic\b",
            r"\bpowerful\b",
            r"\bgentle\b",
            r"\bsoft\b",
            r"\bcalm\b",
            r"\bslow\b",
            r"\bfast\b",
        ],
    },
    {
        "key": "descriptor.style.call_response_mode",
        "patterns": [
            r"\bcall and response\b",
            r"\bcall-response\b",
            r"\bresponse chant\b",
        ],
    },
    {
        "key": "descriptor.style.improvisation_mode",
        "patterns": [
            r"\bimprovis\w*\b",
            r"\bfreestyle\b",
            r"\bspontaneous\b",
            r"\bad[ -]?lib\b",
            r"\bset sequence\b",
            r"\bcodified\b",
        ],
    },
    {
        "key": "descriptor.performance.impact_profile",
        "patterns": [
            r"\bstomp\w*\b",
            r"\bstamp\w*\b",
            r"\bclap\w*\b",
            r"\bheel\b",
            r"\bpercussive\b",
            r"\bglide\w*\b",
            r"\bflow\w*\b",
        ],
    },
    {
        "key": "descriptor.performance.rotation_profile",
        "patterns": [
            r"\bturn\w*\b",
            r"\bspin\w*\b",
            r"\btwirl\w*\b",
            r"\bpivot\w*\b",
            r"\brotation\b",
        ],
    },
    {
        "key": "descriptor.performance.elevation_profile",
        "patterns": [
            r"\bjump\w*\b",
            r"\bleap\w*\b",
            r"\bhop\w*\b",
            r"\bbounce\w*\b",
            r"\belevat\w*\b",
        ],
    },
    {
        "key": "descriptor.performance.partner_interaction",
        "patterns": [
            r"\bpartner\w*\b",
            r"\bcouple\w*\b",
            r"\bpair\w*\b",
            r"\bhold hands\b",
            r"\bfacing each other\b",
        ],
    },
    {
        "key": "descriptor.style.spatial_pattern",
        "patterns": [
            r"\bcircle\w*\b",
            r"\bring\b",
            r"\bline\w*\b",
            r"\bprocession\w*\b",
            r"\bprogress\w*\b",
        ],
    },
]

MARKER_STYLE_PATTERNS = [
    re.compile(r"M19_DESCRIPTOR_NOTE", re.IGNORECASE),
    re.compile(r"Ingest filler step", re.IGNORECASE),
    re.compile(r"M2 Conversion", re.IGNORECASE),
    re.compile(r"#\s*source_id", re.IGNORECASE),
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Apply deterministic source-grounded descriptor evidence uplift on top of the "
            "expanded M20 corpus and verify strict doctor plus validate-geo quality."
        )
    )
    ap.add_argument(
        "--source-dir",
        default="out/m2_conversion/run1",
        help="input directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--source-text-dir",
        action="append",
        default=[],
        help="directory containing acquired source .txt files (repeatable)",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m20_descriptor_evidence/run1",
        help="output directory for uplifted .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m20_descriptor_evidence_report.json",
        help="output path for descriptor-evidence uplift report",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument("--label", default="m20-descriptor-evidence-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=100, help="minimum expected total files")
    ap.add_argument(
        "--min-files-updated",
        type=int,
        default=40,
        help="minimum files that must receive source-grounded descriptor updates",
    )
    ap.add_argument(
        "--min-source-grounded-additions",
        type=int,
        default=80,
        help="minimum descriptor additions linked to source evidence",
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
        "--min-keys-with-growth",
        type=int,
        default=6,
        help="minimum descriptor keys whose support must increase",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m20_descriptor_evidence.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout or "").strip()


def first_line(text: str) -> str:
    for line in text.splitlines():
        token = line.strip()
        if token:
            return token
    return ""


def infer_source_id(file_name: str) -> str:
    stem = file_name
    if stem.endswith(".fdml.xml"):
        stem = stem[: -len(".fdml.xml")]
    if "__" not in stem:
        return stem
    return stem.split("__", 1)[1].strip()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def sanitize_lexeme(value: str, max_len: int = 64) -> str:
    token = normalize_text(value)
    if len(token) > max_len:
        token = token[: max_len - 3].rstrip() + "..."
    return token


def text_blob(root: ET.Element) -> str:
    parts: list[str] = []
    for node in root.findall("./meta/*"):
        if node.text:
            parts.append(node.text)
        for raw in node.attrib.values():
            parts.append(str(raw))
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
    return normalize_text(" ".join(parts)).lower()


def find_first_match(patterns: list[re.Pattern[str]], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return sanitize_lexeme(match.group(0))
    return ""


def has_any_match(patterns: list[re.Pattern[str]], text: str) -> bool:
    for pattern in patterns:
        if pattern.search(text):
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


def load_source_texts(source_dirs: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for source_dir in source_dirs:
        if not source_dir.is_dir():
            continue
        for txt in sorted(source_dir.glob("*.txt")):
            source_id = txt.stem.strip()
            if not source_id:
                continue
            out[source_id] = txt.read_text(encoding="utf-8", errors="ignore")
    return out


def marker_style_present(raw_xml: str) -> bool:
    for pattern in MARKER_STYLE_PATTERNS:
        if pattern.search(raw_xml):
            return True
    return False


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_files_updated < 0:
        return fail("--min-files-updated must be >= 0")
    if args.min_source_grounded_additions < 0:
        return fail("--min-source-grounded-additions must be >= 0")
    if args.min_keys_with_growth < 0:
        return fail("--min-keys-with-growth must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be in [0,1]")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be in [0,1]")

    source_dir = Path(args.source_dir)
    source_text_dirs = [Path(p) for p in args.source_text_dir] if args.source_text_dir else []
    if not source_text_dirs:
        source_text_dirs = [Path("out/acquired_sources"), Path("out/acquired_sources_nonwiki")]
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source directory not found: {source_dir}")
    for path in source_text_dirs:
        if not path.is_dir():
            return fail(f"source-text directory not found: {path}")
    if not fdml_bin.exists():
        return fail(f"fdml binary not found: {fdml_bin}")

    files = sorted(source_dir.glob("*.fdml.xml"))
    total_files = len(files)
    if total_files < args.min_total_files:
        return fail(f"source file count {total_files} is below --min-total-files {args.min_total_files}")

    source_text_map = load_source_texts(source_text_dirs)

    compiled_specs: list[dict[str, Any]] = []
    for spec in RULE_SPECS:
        compiled_specs.append(
            {
                "key": str(spec["key"]),
                "patterns": [re.compile(p, re.IGNORECASE) for p in list(spec["patterns"])],
            }
        )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    support_before = {str(spec["key"]): 0 for spec in compiled_specs}
    support_after = {str(spec["key"]): 0 for spec in compiled_specs}
    source_signal_counts = {str(spec["key"]): 0 for spec in compiled_specs}
    additions_by_key = {str(spec["key"]): 0 for spec in compiled_specs}

    rows: list[dict[str, Any]] = []
    targeted_files = 0
    updated_files = 0
    files_with_source_signals = 0
    files_with_additions = 0
    source_grounded_additions = 0
    missing_source_text_files = 0
    marker_style_files_before = 0
    marker_style_files_after = 0

    for file_path in files:
        raw_before = file_path.read_text(encoding="utf-8", errors="ignore")
        if marker_style_present(raw_before):
            marker_style_files_before += 1

        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            return fail(f"root element is not <fdml> in {file_path.name}")

        source_id = infer_source_id(file_path.name)
        source_text = source_text_map.get(source_id, "")
        if not source_text:
            missing_source_text_files += 1

        before_blob = text_blob(root)
        signals_for_file: list[dict[str, str]] = []
        additions_for_file: list[dict[str, str]] = []

        for spec in compiled_specs:
            key = str(spec["key"])
            patterns = list(spec["patterns"])
            fdml_has_before = has_any_match(patterns, before_blob)
            if fdml_has_before:
                support_before[key] += 1

            source_lexeme = find_first_match(patterns, source_text)
            source_has_signal = bool(source_lexeme)
            if source_has_signal:
                source_signal_counts[key] += 1
                signals_for_file.append({"key": key, "lexeme": source_lexeme})

            if source_has_signal and not fdml_has_before:
                additions_for_file.append({"key": key, "lexeme": source_lexeme})

        if signals_for_file:
            files_with_source_signals += 1
        if additions_for_file:
            targeted_files += 1

        changed = False
        if additions_for_file:
            body = ensure_body(root)
            notes = ensure_notes_section(body)
            descriptor_parts = [
                f"{item['key']}='{item['lexeme']}'" for item in additions_for_file
            ]
            node = ET.SubElement(notes, "p")
            node.text = (
                f"M20_EVIDENCE source_id={source_id} source_grounded_descriptors: "
                + "; ".join(descriptor_parts)
                + "."
            )
            changed = True

            files_with_additions += 1
            source_grounded_additions += len(additions_for_file)
            for item in additions_for_file:
                additions_by_key[item["key"]] += 1

        out_file = out_dir / file_path.name
        if changed:
            ET.indent(root, space="  ")
            ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
            updated_files += 1
        else:
            shutil.copy2(file_path, out_file)

        after_root = ET.parse(out_file).getroot()
        after_blob = text_blob(after_root)
        missing_keys_after: list[str] = []
        for spec in compiled_specs:
            key = str(spec["key"])
            patterns = list(spec["patterns"])
            if has_any_match(patterns, after_blob):
                support_after[key] += 1
            else:
                missing_keys_after.append(key)

        raw_after = out_file.read_text(encoding="utf-8", errors="ignore")
        if marker_style_present(raw_after):
            marker_style_files_after += 1

        rows.append(
            {
                "file": file_path.name,
                "sourceId": source_id,
                "hasSourceText": bool(source_text),
                "sourceSignals": signals_for_file,
                "sourceGroundedAdditions": additions_for_file,
                "targeted": bool(additions_for_file),
                "updated": changed,
                "missingKeysAfter": missing_keys_after,
            }
        )

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

    keys_with_growth = [
        key for key in support_before if support_after[key] > support_before[key]
    ]
    support_non_decreasing = all(support_after[key] >= support_before[key] for key in support_before)

    support_before_ratio = {
        key: round(clamp01(float(value) / float(total_files)), 6)
        for key, value in support_before.items()
    }
    support_after_ratio = {
        key: round(clamp01(float(value) / float(total_files)), 6)
        for key, value in support_after.items()
    }
    source_signal_ratio = {
        key: round(clamp01(float(value) / float(total_files)), 6)
        for key, value in source_signal_counts.items()
    }

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
            "id": "source_grounded_additions_min",
            "ok": source_grounded_additions >= args.min_source_grounded_additions,
            "detail": (
                f"source_grounded_additions={source_grounded_additions} "
                f"min={args.min_source_grounded_additions}"
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
        {
            "id": "descriptor_support_non_decreasing",
            "ok": support_non_decreasing,
            "detail": "all tracked descriptor supports are non-decreasing",
        },
        {
            "id": "descriptor_keys_with_growth_min",
            "ok": len(keys_with_growth) >= args.min_keys_with_growth,
            "detail": f"keys_with_growth={len(keys_with_growth)} min={args.min_keys_with_growth}",
        },
        {
            "id": "marker_style_files_not_increased",
            "ok": marker_style_files_after <= marker_style_files_before,
            "detail": (
                f"marker_style_files_before={marker_style_files_before} "
                f"after={marker_style_files_after}"
            ),
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "sourceDir": str(source_dir),
            "sourceTextDirs": [str(p) for p in source_text_dirs],
            "outDir": str(out_dir),
            "fdmlBin": str(fdml_bin),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minFilesUpdated": args.min_files_updated,
            "minSourceGroundedAdditions": args.min_source_grounded_additions,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
            "minKeysWithGrowth": args.min_keys_with_growth,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": total_files,
            "filesWithSourceSignals": files_with_source_signals,
            "filesTargeted": targeted_files,
            "filesUpdated": updated_files,
            "filesWithAdditions": files_with_additions,
            "sourceGroundedAdditions": source_grounded_additions,
            "missingSourceTextFiles": missing_source_text_files,
            "doctorPass": doctor_pass,
            "doctorPassRate": round(clamp01(doctor_pass_rate), 6),
            "geoPass": geo_pass,
            "geoPassRate": round(clamp01(geo_pass_rate), 6),
            "trackedDescriptorKeyCount": len(compiled_specs),
            "keysWithGrowth": len(keys_with_growth),
            "markerStyleFilesBefore": marker_style_files_before,
            "markerStyleFilesAfter": marker_style_files_after,
        },
        "descriptorSupport": {
            "beforeCount": support_before,
            "afterCount": support_after,
            "beforeRatio": support_before_ratio,
            "afterRatio": support_after_ratio,
            "sourceSignalCount": source_signal_counts,
            "sourceSignalRatio": source_signal_ratio,
            "additionsByKey": additions_by_key,
            "keysWithGrowth": keys_with_growth,
        },
        "validationFailures": validation_failures,
        "rows": rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        "M20 DESCRIPTOR EVIDENCE",
        "PASS" if ok else "FAIL",
        f"files={total_files}",
        f"updated={updated_files}",
        f"additions={source_grounded_additions}",
        f"doctorPassRate={round(clamp01(doctor_pass_rate), 6)}",
        f"geoPassRate={round(clamp01(geo_pass_rate), 6)}",
        f"report={report_out}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

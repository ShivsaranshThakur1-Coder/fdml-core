#!/usr/bin/env python3
"""Deterministic M24 cultural-context descriptor saturation pass."""

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


CULTURE_RULE_SPECS: list[dict[str, Any]] = [
    {
        "key": "descriptor.culture.occasion_context",
        "patterns": [
            r"\bfestival\b",
            r"\bcelebration\b",
            r"\bfeast\b",
            r"\bholiday\b",
            r"\bwedding\b",
            r"\bmarriage\b",
            r"\bbridal\b",
            r"\britual\b",
            r"\bceremon\w*\b",
            r"\breligious\b",
            r"\bsacred\b",
            r"\bharvest\b",
            r"\bagricultural\b",
            r"\bcrop\b",
            r"\bfair\b",
            r"\bprocession\b",
            r"\bparade\b",
            r"\bseasonal\b",
        ],
    },
    {
        "key": "descriptor.culture.social_function",
        "patterns": [
            r"\bcommunity\b",
            r"\bcollective\b",
            r"\bidentity\b",
            r"\bpeople\b",
            r"\bcourtship\b",
            r"\bromance\b",
            r"\bflirt\w*\b",
            r"\bwarrior\b",
            r"\bcombat\b",
            r"\bmartial\b",
            r"\bbattle\b",
            r"\bstory\w*\b",
            r"\bnarrative\b",
            r"\blegend\b",
            r"\bnational\b",
            r"\bsolidarity\b",
            r"\bsocial\b",
            r"\bceremonial\b",
        ],
    },
    {
        "key": "descriptor.culture.music_context",
        "patterns": [
            r"\bdrum\w*\b",
            r"\bpercussion\b",
            r"\bdhol\b",
            r"\btabla\b",
            r"\bchant\w*\b",
            r"\bsong\w*\b",
            r"\bsing\w*\b",
            r"\bvocal\w*\b",
            r"\bflute\b",
            r"\bfiddle\b",
            r"\blute\b",
            r"\bhorn\b",
            r"\bbagpipe\b",
            r"\bviolin\b",
            r"\bguitar\b",
            r"\borchestra\b",
            r"\brhythm\w*\b",
            r"\bmelod\w*\b",
        ],
    },
    {
        "key": "descriptor.culture.costume_prop_context",
        "patterns": [
            r"\bcostume\b",
            r"\battire\b",
            r"\bdress\b",
            r"\bskirt\b",
            r"\bgarment\b",
            r"\bbead\w*\b",
            r"\bjewelry\b",
            r"\bsword\b",
            r"\bstick\b",
            r"\bfan\b",
            r"\bhandkerchief\b",
            r"\bcane\b",
            r"\bshield\b",
            r"\bspear\b",
            r"\bhat\b",
            r"\bturban\b",
            r"\bfez\b",
            r"\bvest\b",
            r"\bsash\b",
            r"\btrouser\w*\b",
            r"\bboot\w*\b",
            r"\bmask\w*\b",
            r"\bbell\w*\b",
            r"\bribbon\w*\b",
            r"\bheadpiece\b",
        ],
    },
    {
        "key": "descriptor.culture.participant_identity",
        "patterns": [
            r"\bmen\b",
            r"\bwomen\b",
            r"\bmale\b",
            r"\bfemale\b",
            r"\byouth\b",
            r"\byoung\b",
            r"\bwarrior\b",
            r"\bvillager\w*\b",
            r"\bcommunity members\b",
            r"\belder\w*\b",
            r"\bdancer\w*\b",
            r"\bperformer\w*\b",
            r"\bboy\w*\b",
            r"\bgirl\w*\b",
            r"\bsoldier\w*\b",
            r"\bbride\w*\b",
            r"\bgroom\w*\b",
        ],
    },
    {
        "key": "descriptor.culture.transmission_context",
        "patterns": [
            r"\btraditional\b",
            r"\bfolk\b",
            r"\bheritage\b",
            r"\bancestral\b",
            r"\bcustom\w*\b",
            r"\bceremon\w*\b",
            r"\britual practice\b",
            r"\bpreserv\w*\b",
            r"\brevive\w*\b",
            r"\bpassed down\b",
            r"\bgeneration\w*\b",
            r"\bteach\w*\b",
            r"\blearn\w*\b",
            r"\bschool\w*\b",
        ],
    },
]


CULTURE_KEYS = [str(spec["key"]) for spec in CULTURE_RULE_SPECS]
NOTE_MARKER = "M24_COMPLETION"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Apply deterministic source-grounded M24 cultural-context completion for residual "
            "weak-support descriptor families while preserving strict quality."
        )
    )
    ap.add_argument("--source-dir", default="out/m24_residual_failure_closure/run1", help="input FDML directory")
    ap.add_argument(
        "--residual-closure-report",
        default="out/m24_residual_failure_closure_report.json",
        help="M24 residual-closure report used to load residual-failure file focus set",
    )
    ap.add_argument(
        "--source-text-dir",
        action="append",
        default=[],
        help="directory containing acquired source .txt files (repeatable)",
    )
    ap.add_argument("--out-dir", default="out/m24_descriptor_completion/run1", help="output FDML directory")
    ap.add_argument(
        "--report-out",
        default="out/m24_descriptor_completion_report.json",
        help="output completion report path",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument("--label", default="m24-descriptor-completion-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=100)
    ap.add_argument("--max-low-support-ratio", type=float, default=0.8)
    ap.add_argument("--min-low-support-cultural-keys", type=int, default=2)
    ap.add_argument("--min-targeted-files", type=int, default=5)
    ap.add_argument("--min-files-updated", type=int, default=5)
    ap.add_argument("--min-source-grounded-additions", type=int, default=5)
    ap.add_argument("--min-low-support-keys-with-growth", type=int, default=2)
    ap.add_argument("--max-additions-per-file", type=int, default=3)
    ap.add_argument("--min-residual-focus-files", type=int, default=5)
    ap.add_argument("--max-missing-source-text-files", type=int, default=0)
    ap.add_argument("--min-doctor-pass-rate", type=float, default=1.0)
    ap.add_argument("--min-geo-pass-rate", type=float, default=1.0)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m24_descriptor_completion.py: {msg}", file=sys.stderr)
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


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def sanitize_lexeme(value: str, max_len: int = 64) -> str:
    token = normalize_text(value)
    if len(token) > max_len:
        token = token[: max_len - 3].rstrip() + "..."
    return token


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
            if source_id:
                out[source_id] = txt.read_text(encoding="utf-8", errors="ignore")
    return out


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def find_first_match(patterns: list[re.Pattern[str]], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return sanitize_lexeme(match.group(0))
    return ""


def load_residual_focus_files(report_path: Path) -> list[str]:
    payload = load_json(report_path)
    files: list[str] = []
    for row in as_list(payload.get("rows")):
        row_dict = as_dict(row)
        if not bool(row_dict.get("targeted")):
            continue
        file_name = str(row_dict.get("file") or "").strip()
        if file_name:
            files.append(file_name)
    return sorted(set(files))


def main() -> int:
    args = parse_args()
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if not (0.0 <= args.max_low_support_ratio <= 1.0):
        return fail("--max-low-support-ratio must be in [0,1]")
    if args.min_low_support_cultural_keys <= 0:
        return fail("--min-low-support-cultural-keys must be > 0")
    if args.min_targeted_files < 0:
        return fail("--min-targeted-files must be >= 0")
    if args.min_files_updated < 0:
        return fail("--min-files-updated must be >= 0")
    if args.min_source_grounded_additions < 0:
        return fail("--min-source-grounded-additions must be >= 0")
    if args.min_low_support_keys_with_growth < 0:
        return fail("--min-low-support-keys-with-growth must be >= 0")
    if args.max_additions_per_file <= 0:
        return fail("--max-additions-per-file must be > 0")
    if args.min_residual_focus_files < 0:
        return fail("--min-residual-focus-files must be >= 0")
    if args.max_missing_source_text_files < 0:
        return fail("--max-missing-source-text-files must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be in [0,1]")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be in [0,1]")

    source_dir = Path(args.source_dir)
    residual_closure_report = Path(args.residual_closure_report)
    source_text_dirs = [Path(p) for p in args.source_text_dir] if args.source_text_dir else []
    if not source_text_dirs:
        source_text_dirs = [Path("out/acquired_sources"), Path("out/acquired_sources_nonwiki")]
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source directory not found: {source_dir}")
    if not residual_closure_report.exists():
        return fail(f"residual closure report not found: {residual_closure_report}")
    if not fdml_bin.exists():
        return fail(f"fdml binary not found: {fdml_bin}")
    for path in source_text_dirs:
        if not path.is_dir():
            return fail(f"source-text directory not found: {path}")

    files = sorted(source_dir.glob("*.fdml.xml"))
    total_files = len(files)
    if total_files < args.min_total_files:
        return fail(f"source file count {total_files} is below --min-total-files {args.min_total_files}")

    residual_focus_files = load_residual_focus_files(residual_closure_report)
    source_text_map = load_source_texts(source_text_dirs)

    compiled_specs = [
        {
            "key": str(spec["key"]),
            "patterns": [re.compile(p, re.IGNORECASE) for p in list(spec["patterns"])],
        }
        for spec in CULTURE_RULE_SPECS
    ]
    patterns_by_key = {str(spec["key"]): list(spec["patterns"]) for spec in compiled_specs}

    support_before = {key: 0 for key in CULTURE_KEYS}
    source_signal_counts = {key: 0 for key in CULTURE_KEYS}
    per_file_baseline_present: dict[str, set[str]] = {}
    per_file_source_signals: dict[str, dict[str, str]] = {}
    missing_source_text_files = 0

    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            return fail(f"root element is not <fdml> in {file_path.name}")

        blob = text_blob(root)
        source_id = infer_source_id(file_path.name)
        source_text = source_text_map.get(source_id, "")
        if not source_text:
            missing_source_text_files += 1

        baseline_present: set[str] = set()
        for key in CULTURE_KEYS:
            if any(p.search(blob) for p in patterns_by_key[key]):
                baseline_present.add(key)
                support_before[key] += 1
        per_file_baseline_present[file_path.name] = baseline_present

        signals: dict[str, str] = {}
        for spec in compiled_specs:
            key = str(spec["key"])
            lexeme = find_first_match(list(spec["patterns"]), source_text)
            if lexeme:
                signals[key] = lexeme
                source_signal_counts[key] += 1
        per_file_source_signals[file_path.name] = signals

    low_support_candidates: list[dict[str, Any]] = []
    for key in CULTURE_KEYS:
        before_count = int(support_before[key])
        ratio = float(before_count) / float(total_files) if total_files > 0 else 0.0
        signal_count = int(source_signal_counts[key])
        potential_growth = max(0, signal_count - before_count)
        if ratio <= args.max_low_support_ratio and potential_growth > 0:
            low_support_candidates.append(
                {
                    "key": key,
                    "beforeCount": before_count,
                    "beforeRatio": round(clamp01(ratio), 6),
                    "sourceSignalCount": signal_count,
                    "potentialGrowth": potential_growth,
                }
            )

    low_support_candidates.sort(
        key=lambda row: (float(row["beforeRatio"]), -int(row["potentialGrowth"]), str(row["key"]))
    )
    low_support_keys = [str(row["key"]) for row in low_support_candidates]
    if len(low_support_keys) < args.min_low_support_cultural_keys:
        return fail(
            "identified low-support cultural keys "
            f"{len(low_support_keys)} below --min-low-support-cultural-keys "
            f"{args.min_low_support_cultural_keys}"
        )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    support_after = {key: 0 for key in CULTURE_KEYS}
    additions_by_key = {key: 0 for key in CULTURE_KEYS}
    rows: list[dict[str, Any]] = []
    files_targeted = 0
    files_updated = 0
    source_grounded_additions = 0

    residual_signaled_files = 0
    residual_covered_before_files = 0
    residual_covered_after_files = 0

    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            return fail(f"root element is not <fdml> in {file_path.name}")

        file_name = file_path.name
        source_id = infer_source_id(file_name)
        baseline_present = set(per_file_baseline_present[file_name])
        source_signals = dict(per_file_source_signals[file_name])
        is_residual_focus = file_name in residual_focus_files

        missing_candidate_keys = [
            key for key in low_support_keys if key in source_signals and key not in baseline_present
        ]
        selected = missing_candidate_keys[: args.max_additions_per_file]
        selected_additions = [{"key": key, "lexeme": source_signals[key]} for key in selected]

        if selected_additions:
            files_targeted += 1

        changed = False
        if selected_additions:
            body = ensure_body(root)
            notes = ensure_notes_section(body)
            descriptor_parts = [f"{item['key']}='{item['lexeme']}'" for item in selected_additions]
            node = ET.SubElement(notes, "p")
            node.text = (
                f"{NOTE_MARKER} source_id={source_id} low_support_cultural_descriptors: "
                + "; ".join(descriptor_parts)
                + "."
            )
            changed = True
            files_updated += 1
            source_grounded_additions += len(selected_additions)
            for item in selected_additions:
                additions_by_key[item["key"]] += 1

        out_file = out_dir / file_name
        if changed:
            ET.indent(root, space="  ")
            ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
        else:
            shutil.copy2(file_path, out_file)

        after_root = ET.parse(out_file).getroot()
        after_blob = text_blob(after_root)
        present_after = {key for key in CULTURE_KEYS if any(p.search(after_blob) for p in patterns_by_key[key])}
        for key in present_after:
            support_after[key] += 1

        residual_signaled_keys = [key for key in low_support_keys if key in source_signals]
        residual_covered_before = all(key in baseline_present for key in residual_signaled_keys)
        residual_covered_after = all(key in present_after for key in residual_signaled_keys)
        if is_residual_focus and residual_signaled_keys:
            residual_signaled_files += 1
            if residual_covered_before:
                residual_covered_before_files += 1
            if residual_covered_after:
                residual_covered_after_files += 1

        rows.append(
            {
                "file": file_name,
                "sourceId": source_id,
                "residualFocus": is_residual_focus,
                "hasSourceText": bool(source_text_map.get(source_id, "")),
                "baselinePresent": sorted(baseline_present),
                "sourceSignals": [{"key": key, "lexeme": source_signals[key]} for key in sorted(source_signals)],
                "sourceGroundedAdditions": selected_additions,
                "targeted": bool(selected_additions),
                "updated": changed,
                "residualFocusLowSupportSignals": residual_signaled_keys,
                "residualFocusCoveredBefore": bool(residual_covered_before),
                "residualFocusCoveredAfter": bool(residual_covered_after),
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

    low_support_keys_with_growth = [key for key in low_support_keys if support_after[key] > support_before[key]]
    low_support_additions = sum(int(additions_by_key[key]) for key in low_support_keys)
    low_support_before_avg = (
        sum(float(support_before[key]) / float(total_files) for key in low_support_keys) / float(len(low_support_keys))
        if low_support_keys and total_files > 0
        else 0.0
    )
    low_support_after_avg = (
        sum(float(support_after[key]) / float(total_files) for key in low_support_keys) / float(len(low_support_keys))
        if low_support_keys and total_files > 0
        else 0.0
    )
    residual_growth_before = (
        sum(max(0, int(source_signal_counts[key]) - int(support_before[key])) for key in low_support_keys)
        if low_support_keys
        else 0
    )
    residual_growth_after = (
        sum(max(0, int(source_signal_counts[key]) - int(support_after[key])) for key in low_support_keys)
        if low_support_keys
        else 0
    )

    checks = [
        {
            "id": "source_files_min",
            "ok": total_files >= args.min_total_files,
            "detail": f"source_files={total_files} min={args.min_total_files}",
        },
        {
            "id": "residual_focus_files_min",
            "ok": len(residual_focus_files) >= args.min_residual_focus_files,
            "detail": f"residual_focus_files={len(residual_focus_files)} min={args.min_residual_focus_files}",
        },
        {
            "id": "low_support_cultural_keys_min",
            "ok": len(low_support_keys) >= args.min_low_support_cultural_keys,
            "detail": (
                f"low_support_cultural_keys={len(low_support_keys)} "
                f"min={args.min_low_support_cultural_keys}"
            ),
        },
        {
            "id": "targeted_files_min",
            "ok": files_targeted >= args.min_targeted_files,
            "detail": f"targeted_files={files_targeted} min={args.min_targeted_files}",
        },
        {
            "id": "files_updated_min",
            "ok": files_updated >= args.min_files_updated,
            "detail": f"files_updated={files_updated} min={args.min_files_updated}",
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
            "id": "low_support_keys_with_growth_min",
            "ok": len(low_support_keys_with_growth) >= args.min_low_support_keys_with_growth,
            "detail": (
                f"low_support_keys_with_growth={len(low_support_keys_with_growth)} "
                f"min={args.min_low_support_keys_with_growth}"
            ),
        },
        {
            "id": "low_support_average_ratio_increase",
            "ok": low_support_after_avg >= low_support_before_avg,
            "detail": (
                f"low_support_avg_ratio={round(clamp01(low_support_before_avg), 6)}"
                f"->{round(clamp01(low_support_after_avg), 6)}"
            ),
        },
        {
            "id": "residual_growth_gap_reduced",
            "ok": residual_growth_after <= residual_growth_before,
            "detail": f"residual_growth_gap={residual_growth_before}->{residual_growth_after}",
        },
        {
            "id": "residual_focus_non_regression",
            "ok": residual_covered_after_files >= residual_covered_before_files,
            "detail": (
                f"residual_focus_covered={residual_covered_before_files}"
                f"->{residual_covered_after_files} signaled={residual_signaled_files}"
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
            "id": "missing_source_text_files_max",
            "ok": missing_source_text_files <= args.max_missing_source_text_files,
            "detail": (
                f"missing_source_text_files={missing_source_text_files} "
                f"max={args.max_missing_source_text_files}"
            ),
        },
    ]
    ok = all(bool(item.get("ok")) for item in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "sourceDir": str(source_dir),
            "residualClosureReport": str(residual_closure_report),
            "sourceTextDirs": [str(p) for p in source_text_dirs],
            "outDir": str(out_dir),
            "fdmlBin": str(fdml_bin),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "maxLowSupportRatio": args.max_low_support_ratio,
            "minLowSupportCulturalKeys": args.min_low_support_cultural_keys,
            "minTargetedFiles": args.min_targeted_files,
            "minFilesUpdated": args.min_files_updated,
            "minSourceGroundedAdditions": args.min_source_grounded_additions,
            "minLowSupportKeysWithGrowth": args.min_low_support_keys_with_growth,
            "maxAdditionsPerFile": args.max_additions_per_file,
            "minResidualFocusFiles": args.min_residual_focus_files,
            "maxMissingSourceTextFiles": args.max_missing_source_text_files,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": total_files,
            "residualFocusFileCount": len(residual_focus_files),
            "targetedFiles": files_targeted,
            "filesUpdated": files_updated,
            "sourceGroundedAdditions": source_grounded_additions,
            "missingSourceTextFiles": missing_source_text_files,
            "doctorPass": doctor_pass,
            "doctorPassRate": round(clamp01(doctor_pass_rate), 6),
            "geoPass": geo_pass,
            "geoPassRate": round(clamp01(geo_pass_rate), 6),
            "trackedCulturalKeyCount": len(CULTURE_KEYS),
            "lowSupportCulturalKeyCount": len(low_support_keys),
            "lowSupportKeysWithGrowth": len(low_support_keys_with_growth),
            "lowSupportAverageRatioBefore": round(clamp01(low_support_before_avg), 6),
            "lowSupportAverageRatioAfter": round(clamp01(low_support_after_avg), 6),
            "lowSupportAdditions": low_support_additions,
            "residualPotentialGrowthBefore": residual_growth_before,
            "residualPotentialGrowthAfter": residual_growth_after,
            "residualFocusSignaledFiles": residual_signaled_files,
            "residualFocusCoveredBeforeFiles": residual_covered_before_files,
            "residualFocusCoveredAfterFiles": residual_covered_after_files,
        },
        "descriptorSupport": {
            "beforeCount": support_before,
            "afterCount": support_after,
            "sourceSignalCount": source_signal_counts,
            "additionsByKey": additions_by_key,
            "lowSupportKeys": low_support_keys,
            "lowSupportKeysWithGrowth": low_support_keys_with_growth,
            "lowSupportCandidates": low_support_candidates,
        },
        "residualFocus": {
            "files": residual_focus_files,
            "signaledFiles": residual_signaled_files,
            "coveredBeforeFiles": residual_covered_before_files,
            "coveredAfterFiles": residual_covered_after_files,
        },
        "validationFailures": validation_failures,
        "rows": rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        "M24 DESCRIPTOR COMPLETION",
        "PASS" if ok else "FAIL",
        f"files={total_files}",
        f"targeted={files_targeted}",
        f"updated={files_updated}",
        f"sourceGroundedAdditions={source_grounded_additions}",
        f"lowSupportKeys={len(low_support_keys)}",
        f"lowSupportGrowth={len(low_support_keys_with_growth)}",
        f"residualGap={residual_growth_before}->{residual_growth_after}",
        f"report={report_out}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

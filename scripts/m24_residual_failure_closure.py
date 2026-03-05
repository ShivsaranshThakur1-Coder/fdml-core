#!/usr/bin/env python3
"""Deterministic M24 residual validator failure closure over M23 outputs."""

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


RULE_SPECS: dict[str, dict[str, Any]] = {
    "rule:source_grounded_occasion_context_alignment": {
        "descriptorKey": "descriptor.culture.occasion_context",
        "failureCode": "missing_source_grounded_occasion_context",
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
        ],
    },
    "rule:source_grounded_social_function_alignment": {
        "descriptorKey": "descriptor.culture.social_function",
        "failureCode": "missing_source_grounded_social_function",
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
        ],
    },
    "rule:source_grounded_transmission_context_alignment": {
        "descriptorKey": "descriptor.culture.transmission_context",
        "failureCode": "missing_source_grounded_transmission_context",
        "patterns": [
            r"\btraditional\b",
            r"\bfolk\b",
            r"\bheritage\b",
            r"\bancestral\b",
            r"\bcustom\w*\b",
            r"\bceremon\w*\b",
            r"\britual practice\b",
        ],
    },
}


NOTE_MARKER = "M24_UPLIFT"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Apply deterministic source-grounded residual failure closure by reading "
            "M23 file/rule failures and appending targeted M24 notes."
        )
    )
    ap.add_argument(
        "--source-dir",
        default="out/m23_descriptor_consolidation/run1",
        help="input FDML directory",
    )
    ap.add_argument(
        "--residual-report",
        default="out/m23_validator_expansion_report.json",
        help="M23 validator expansion report containing residual file/rule failures",
    )
    ap.add_argument(
        "--source-text-dir",
        action="append",
        default=[],
        help="directory containing acquired source .txt files (repeatable)",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m24_residual_failure_closure/run1",
        help="output FDML directory",
    )
    ap.add_argument(
        "--report-out",
        default="out/m24_residual_failure_closure_report.json",
        help="output closure report path",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument("--label", default="m24-residual-failure-closure-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=100)
    ap.add_argument("--min-targeted-files", type=int, default=5)
    ap.add_argument("--min-files-updated", type=int, default=5)
    ap.add_argument("--min-source-grounded-additions", type=int, default=6)
    ap.add_argument("--max-additions-per-file", type=int, default=3)
    ap.add_argument("--max-missing-source-text-files", type=int, default=0)
    ap.add_argument("--min-doctor-pass-rate", type=float, default=1.0)
    ap.add_argument("--min-geo-pass-rate", type=float, default=1.0)
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m24_residual_failure_closure.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def infer_source_id(file_name: str) -> str:
    stem = file_name
    if stem.endswith(".fdml.xml"):
        stem = stem[: -len(".fdml.xml")]
    if "__" not in stem:
        return stem
    return stem.split("__", 1)[1].strip()


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


def load_residual_targets(
    residual_report: Path,
) -> tuple[dict[str, list[str]], dict[tuple[str, str], str], dict[str, int], int]:
    payload = load_json(residual_report)
    by_file: dict[str, list[str]] = {}
    evidence_by_file_rule: dict[tuple[str, str], str] = {}
    taxonomy: dict[str, int] = {}
    total_residual_rules = 0

    for row in as_list(payload.get("fileFailures")):
        row_dict = as_dict(row)
        file_name = Path(str(row_dict.get("file") or "")).name
        if not file_name:
            continue
        failed_rules = [str(r).strip() for r in as_list(row_dict.get("failedRules")) if str(r).strip()]
        if not failed_rules:
            continue
        by_file[file_name] = sorted(set(failed_rules))
        total_residual_rules += len(by_file[file_name])

    for row in as_list(payload.get("failureTaxonomy")):
        row_dict = as_dict(row)
        code = str(row_dict.get("code") or "").strip()
        if not code:
            continue
        try:
            taxonomy[code] = int(row_dict.get("count") or 0)
        except Exception:
            taxonomy[code] = 0

    for rule in as_list(payload.get("rules")):
        rule_dict = as_dict(rule)
        rule_key = str(rule_dict.get("key") or "").strip()
        if not rule_key:
            continue
        for sample in as_list(rule_dict.get("failedSamples")):
            sample_dict = as_dict(sample)
            file_name = Path(str(sample_dict.get("file") or "")).name
            if not file_name:
                continue
            source_evidence = sanitize_lexeme(str(sample_dict.get("sourceEvidence") or ""))
            if source_evidence:
                evidence_by_file_rule[(file_name, rule_key)] = source_evidence

    return by_file, evidence_by_file_rule, taxonomy, total_residual_rules


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_targeted_files < 0:
        return fail("--min-targeted-files must be >= 0")
    if args.min_files_updated < 0:
        return fail("--min-files-updated must be >= 0")
    if args.min_source_grounded_additions < 0:
        return fail("--min-source-grounded-additions must be >= 0")
    if args.max_additions_per_file <= 0:
        return fail("--max-additions-per-file must be > 0")
    if args.max_missing_source_text_files < 0:
        return fail("--max-missing-source-text-files must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be in [0,1]")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be in [0,1]")

    source_dir = Path(args.source_dir)
    residual_report = Path(args.residual_report)
    source_text_dirs = [Path(p) for p in args.source_text_dir] if args.source_text_dir else []
    if not source_text_dirs:
        source_text_dirs = [Path("out/acquired_sources"), Path("out/acquired_sources_nonwiki")]
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source directory not found: {source_dir}")
    if not residual_report.exists():
        return fail(f"residual report not found: {residual_report}")
    if not fdml_bin.exists():
        return fail(f"fdml binary not found: {fdml_bin}")
    for path in source_text_dirs:
        if not path.is_dir():
            return fail(f"source-text directory not found: {path}")

    files = sorted(source_dir.glob("*.fdml.xml"))
    total_files = len(files)
    if total_files < args.min_total_files:
        return fail(f"source file count {total_files} is below --min-total-files {args.min_total_files}")

    source_text_map = load_source_texts(source_text_dirs)
    residual_by_file, evidence_by_file_rule, residual_taxonomy, residual_rule_count = load_residual_targets(
        residual_report
    )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    compiled_patterns = {
        key: [re.compile(pat, re.IGNORECASE) for pat in list(as_list(spec.get("patterns")))]
        for key, spec in RULE_SPECS.items()
    }

    rows: list[dict[str, Any]] = []
    targeted_files = 0
    files_updated = 0
    source_grounded_additions = 0
    missing_source_text_files = 0
    unresolved_target_rules = 0
    unsupported_rule_count = 0
    additions_by_descriptor: dict[str, int] = {}

    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            return fail(f"root element is not <fdml> in {file_path.name}")

        file_name = file_path.name
        source_id = infer_source_id(file_name)
        source_text = source_text_map.get(source_id, "")
        source_text_lower = source_text.lower()
        failed_rules = list(residual_by_file.get(file_name, []))

        if failed_rules:
            targeted_files += 1
            if not source_text:
                missing_source_text_files += 1

        selected_additions: list[dict[str, str]] = []
        unresolved: list[dict[str, str]] = []

        for rule_key in failed_rules:
            spec = RULE_SPECS.get(rule_key)
            if not spec:
                unsupported_rule_count += 1
                unresolved_target_rules += 1
                unresolved.append({"ruleKey": rule_key, "reason": "unsupported_rule"})
                continue

            descriptor_key = str(spec["descriptorKey"])
            evidence = sanitize_lexeme(evidence_by_file_rule.get((file_name, rule_key), ""))
            if evidence and source_text and evidence.lower() not in source_text_lower:
                evidence = ""
            if not evidence and source_text:
                evidence = find_first_match(compiled_patterns[rule_key], source_text)
            if not evidence:
                unresolved_target_rules += 1
                unresolved.append({"ruleKey": rule_key, "reason": "source_evidence_not_found"})
                continue

            selected_additions.append(
                {
                    "ruleKey": rule_key,
                    "descriptorKey": descriptor_key,
                    "lexeme": evidence,
                    "failureCode": str(spec["failureCode"]),
                }
            )

        deduped: list[dict[str, str]] = []
        seen_pairs: set[tuple[str, str]] = set()
        for item in selected_additions:
            pair = (str(item["descriptorKey"]), str(item["lexeme"]).lower())
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            deduped.append(item)
        selected_additions = deduped[: args.max_additions_per_file]

        changed = False
        if selected_additions:
            body = ensure_body(root)
            notes = ensure_notes_section(body)
            descriptor_parts = [
                f"{item['descriptorKey']}='{item['lexeme']}'"
                for item in selected_additions
            ]
            node = ET.SubElement(notes, "p")
            node.text = (
                f"{NOTE_MARKER} source_id={source_id} residual_failure_closure: "
                + "; ".join(descriptor_parts)
                + "."
            )
            changed = True
            files_updated += 1
            source_grounded_additions += len(selected_additions)
            for item in selected_additions:
                descriptor_key = str(item["descriptorKey"])
                additions_by_descriptor[descriptor_key] = int(additions_by_descriptor.get(descriptor_key, 0)) + 1

        out_file = out_dir / file_name
        if changed:
            ET.indent(root, space="  ")
            ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
        else:
            shutil.copy2(file_path, out_file)

        rows.append(
            {
                "file": file_name,
                "sourceId": source_id,
                "targeted": bool(failed_rules),
                "updated": changed,
                "failedRulesFromResidualReport": failed_rules,
                "sourceGroundedAdditions": selected_additions,
                "unresolvedRules": unresolved,
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

    checks = [
        {
            "id": "source_files_min",
            "ok": total_files >= args.min_total_files,
            "detail": f"source_files={total_files} min={args.min_total_files}",
        },
        {
            "id": "residual_targets_detected",
            "ok": len(residual_by_file) > 0,
            "detail": f"residual_files={len(residual_by_file)} residual_rules={residual_rule_count}",
        },
        {
            "id": "targeted_files_min",
            "ok": targeted_files >= args.min_targeted_files,
            "detail": f"targeted_files={targeted_files} min={args.min_targeted_files}",
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
            "id": "unresolved_target_rules_zero",
            "ok": unresolved_target_rules == 0,
            "detail": f"unresolved_target_rules={unresolved_target_rules}",
        },
        {
            "id": "unsupported_rule_count_zero",
            "ok": unsupported_rule_count == 0,
            "detail": f"unsupported_rule_count={unsupported_rule_count}",
        },
        {
            "id": "missing_source_text_files_max",
            "ok": missing_source_text_files <= args.max_missing_source_text_files,
            "detail": (
                f"missing_source_text_files={missing_source_text_files} "
                f"max={args.max_missing_source_text_files}"
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
    ok = all(bool(item.get("ok")) for item in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "sourceDir": str(source_dir),
            "residualReport": str(residual_report),
            "sourceTextDirs": [str(p) for p in source_text_dirs],
            "outDir": str(out_dir),
            "fdmlBin": str(fdml_bin),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minTargetedFiles": args.min_targeted_files,
            "minFilesUpdated": args.min_files_updated,
            "minSourceGroundedAdditions": args.min_source_grounded_additions,
            "maxAdditionsPerFile": args.max_additions_per_file,
            "maxMissingSourceTextFiles": args.max_missing_source_text_files,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": total_files,
            "residualFailureFiles": len(residual_by_file),
            "residualFailureRules": residual_rule_count,
            "targetedFiles": targeted_files,
            "filesUpdated": files_updated,
            "sourceGroundedAdditions": source_grounded_additions,
            "unresolvedTargetRules": unresolved_target_rules,
            "unsupportedRuleCount": unsupported_rule_count,
            "missingSourceTextFiles": missing_source_text_files,
            "doctorPass": doctor_pass,
            "doctorPassRate": round(clamp01(doctor_pass_rate), 6),
            "geoPass": geo_pass,
            "geoPassRate": round(clamp01(geo_pass_rate), 6),
        },
        "residualTaxonomy": [
            {"code": code, "count": int(count)}
            for code, count in sorted(residual_taxonomy.items(), key=lambda item: (-int(item[1]), str(item[0])))
        ],
        "supportedRuleKeys": sorted(RULE_SPECS.keys()),
        "descriptorAdditionsByKey": additions_by_descriptor,
        "validationFailures": validation_failures,
        "rows": rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        "M24 RESIDUAL FAILURE CLOSURE",
        "PASS" if ok else "FAIL",
        f"files={total_files}",
        f"targeted={targeted_files}",
        f"updated={files_updated}",
        f"additions={source_grounded_additions}",
        f"residualRules={residual_rule_count}",
        f"unresolved={unresolved_target_rules}",
        f"report={report_out}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

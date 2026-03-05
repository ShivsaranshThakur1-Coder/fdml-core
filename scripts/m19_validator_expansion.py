#!/usr/bin/env python3
"""M19 validator expansion by layering descriptor-depth rules onto M17 one-stack reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


NEW_RULE_SPECS = [
    {
        "key": "rule:descriptor_energy_profile_present",
        "name": "descriptor_energy_profile_present",
        "description": "Descriptor depth must include energy-profile cues.",
        "derivedFromCandidateKeys": ["descriptor.style.energy_profile"],
        "patterns": [
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
        "failureCode": "missing_descriptor_energy_profile",
    },
    {
        "key": "rule:descriptor_call_response_mode_present",
        "name": "descriptor_call_response_mode_present",
        "description": "Descriptor depth must include call-response interaction cues.",
        "derivedFromCandidateKeys": ["descriptor.style.call_response_mode"],
        "patterns": [r"\bcall and response\b", r"\bcall-response\b"],
        "failureCode": "missing_descriptor_call_response_mode",
    },
    {
        "key": "rule:descriptor_improvisation_mode_present",
        "name": "descriptor_improvisation_mode_present",
        "description": "Descriptor depth must include improvisational or fixed-sequence cues.",
        "derivedFromCandidateKeys": ["descriptor.style.improvisation_mode"],
        "patterns": [
            r"\bimprovis\w*\b",
            r"\bfreestyle\b",
            r"\bspontaneous\b",
            r"\bad[- ]?lib\b",
            r"\bchoreograph\w*\b",
            r"\bset sequence\b",
            r"\bcodified\b",
        ],
        "failureCode": "missing_descriptor_improvisation_mode",
    },
    {
        "key": "rule:descriptor_impact_profile_present",
        "name": "descriptor_impact_profile_present",
        "description": "Descriptor depth must include impact-profile cues (percussive or smooth).",
        "derivedFromCandidateKeys": ["descriptor.performance.impact_profile"],
        "patterns": [
            r"\bstomp\b",
            r"\bstamp\b",
            r"\bclap\b",
            r"\bheel strike\b",
            r"\bsmooth\b",
            r"\bglide\b",
            r"\bflow\w*\b",
        ],
        "failureCode": "missing_descriptor_impact_profile",
    },
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Compose an M19 validator expansion report by augmenting M17 validator "
            "outputs with descriptor-depth rules."
        )
    )
    ap.add_argument(
        "--input-dir",
        default="out/m19_descriptor_uplift/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--base-report",
        required=True,
        help="base M17 validator report for the same corpus path",
    )
    ap.add_argument(
        "--report-out",
        default="out/m19_validator_expansion_report.json",
        help="output path for M19 validator expansion report",
    )
    ap.add_argument("--label", default="m19-validator-expansion-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum expected total files")
    ap.add_argument("--min-rules", type=int, default=45, help="minimum expanded rule count required")
    ap.add_argument(
        "--max-rules-with-no-applicability",
        type=int,
        default=1,
        help="maximum allowed count of rules with zero applicable files",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m19_validator_expansion.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def display_path(path_value: Path, repo_root: Path) -> str:
    try:
        return path_value.resolve().relative_to(repo_root).as_posix()
    except Exception:
        return path_value.resolve().as_posix()


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


def evaluate_new_rules(files: list[Path], repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, int], int, int]:
    file_blobs: dict[str, str] = {}
    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            raise RuntimeError(f"root element is not <fdml> in {file_path}")
        key = file_path.resolve().as_posix()
        file_blobs[key] = text_blob(root)

    new_rule_rows: list[dict[str, Any]] = []
    new_file_failures: dict[str, list[str]] = {}
    failure_code_counts: dict[str, int] = {}
    evaluations = 0
    failures = 0

    for spec in NEW_RULE_SPECS:
        key = str(spec["key"])
        patterns = [re.compile(pat, re.IGNORECASE) for pat in spec["patterns"]]
        fail_code = str(spec["failureCode"])

        applicable = 0
        passed = 0
        failed = 0
        skipped = 0
        local_fail_counts: dict[str, int] = {}
        failed_samples: list[dict[str, Any]] = []

        for file_path in files:
            file_key = file_path.resolve().as_posix()
            blob = file_blobs[file_key]
            applicable += 1
            evaluations += 1
            matched = any(bool(pattern.search(blob)) for pattern in patterns)
            if matched:
                passed += 1
                continue

            failed += 1
            failures += 1
            local_fail_counts[fail_code] = int(local_fail_counts.get(fail_code, 0)) + 1
            failure_code_counts[fail_code] = int(failure_code_counts.get(fail_code, 0)) + 1

            display = display_path(file_path, repo_root)
            new_file_failures.setdefault(display, []).append(key)
            if len(failed_samples) < 20:
                failed_samples.append({"file": display, "codes": [fail_code]})

        pass_rate = float(passed) / float(applicable) if applicable > 0 else 1.0
        new_rule_rows.append(
            {
                "key": key,
                "name": str(spec["name"]),
                "description": str(spec["description"]),
                "derivedFromCandidateKeys": [str(x) for x in as_list(spec.get("derivedFromCandidateKeys"))],
                "metrics": {
                    "applicableFiles": applicable,
                    "passedFiles": passed,
                    "failedFiles": failed,
                    "skippedFiles": skipped,
                    "passRate": round(pass_rate, 6),
                    "failureCodeCounts": local_fail_counts,
                },
                "failedSamples": failed_samples,
            }
        )

    return new_rule_rows, new_file_failures, failure_code_counts, evaluations, failures


def main() -> int:
    args = parse_args()
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_rules <= 0:
        return fail("--min-rules must be > 0")
    if args.max_rules_with_no_applicability < 0:
        return fail("--max-rules-with-no-applicability must be >= 0")

    repo_root = Path(".").resolve()
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = (repo_root / input_dir).resolve()
    base_report_path = Path(args.base_report)
    if not base_report_path.is_absolute():
        base_report_path = (repo_root / base_report_path).resolve()
    report_out = Path(args.report_out)
    if not report_out.is_absolute():
        report_out = (repo_root / report_out).resolve()

    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")
    if not base_report_path.exists():
        return fail(f"base report not found: {base_report_path}")

    files = sorted(input_dir.glob("*.fdml.xml"))
    if len(files) < args.min_total_files:
        return fail(f"source file count {len(files)} is below --min-total-files {args.min_total_files}")

    base = load_json(base_report_path)
    base_rules = [as_dict(x) for x in as_list(base.get("rules"))]
    base_file_failures = {str(as_dict(row).get("file") or ""): list(as_list(as_dict(row).get("failedRules"))) for row in as_list(base.get("fileFailures"))}
    base_failure_tax = {str(as_dict(row).get("code") or ""): as_int(as_dict(row).get("count"), 0) for row in as_list(base.get("failureTaxonomy"))}
    base_totals = as_dict(base.get("totals"))
    base_priority = as_dict(base.get("priorityCoverage"))
    base_missing = [str(x) for x in as_list(base_priority.get("missingKeys")) if str(x)]

    new_rules, new_file_failures, new_failure_tax, new_evaluations, new_failures = evaluate_new_rules(files, repo_root)

    merged_rules = base_rules + new_rules
    merged_file_failures: dict[str, list[str]] = {}
    for file_name, rule_keys in base_file_failures.items():
        if not file_name:
            continue
        merged_file_failures.setdefault(file_name, []).extend([str(x) for x in rule_keys if str(x)])
    for file_name, rule_keys in new_file_failures.items():
        merged_file_failures.setdefault(file_name, []).extend([str(x) for x in rule_keys if str(x)])
    merged_file_failures = {
        file_name: sorted(set(rule_keys))
        for file_name, rule_keys in merged_file_failures.items()
        if file_name
    }

    merged_failure_tax = dict(base_failure_tax)
    for code, count in new_failure_tax.items():
        if not code:
            continue
        merged_failure_tax[code] = int(merged_failure_tax.get(code, 0)) + int(count)

    rules_with_no_applicability = [
        str(as_dict(rule).get("key") or "")
        for rule in merged_rules
        if as_int(as_dict(as_dict(rule).get("metrics")).get("applicableFiles"), 0) <= 0
    ]

    merged_rule_count = len(merged_rules)
    merged_evaluations = as_int(base_totals.get("ruleEvaluations"), 0) + new_evaluations
    merged_failures = as_int(base_totals.get("ruleFailures"), 0) + new_failures

    checks = [
        {
            "id": "source_files_min",
            "ok": len(files) >= args.min_total_files,
            "detail": f"source_files={len(files)} min={args.min_total_files}",
        },
        {
            "id": "expanded_rules_min",
            "ok": merged_rule_count >= args.min_rules,
            "detail": f"rules={merged_rule_count} min={args.min_rules}",
        },
        {
            "id": "all_rules_have_applicability",
            "ok": len(rules_with_no_applicability) <= args.max_rules_with_no_applicability,
            "detail": (
                f"rules_with_no_applicability={len(rules_with_no_applicability)} "
                f"max={args.max_rules_with_no_applicability}"
            ),
        },
        {
            "id": "priority_key_mapping_complete",
            "ok": len(base_missing) == 0,
            "detail": (
                f"candidate_keys={as_int(base_totals.get('candidateKeys'), 0)} "
                f"mapped={as_int(base_totals.get('mappedCandidateKeys'), 0)} missing={len(base_missing)}"
            ),
        },
        {
            "id": "m19_descriptor_rules_added",
            "ok": len(new_rules) >= len(NEW_RULE_SPECS),
            "detail": f"m19_rules={len(new_rules)} expected={len(NEW_RULE_SPECS)}",
        },
        {
            "id": "failure_taxonomy_recorded",
            "ok": (merged_failures == 0) or (len(merged_failure_tax) > 0),
            "detail": f"rule_failures={merged_failures} taxonomy_codes={len(merged_failure_tax)}",
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    m19_ratio_by_rule = {
        str(as_dict(rule).get("key") or ""): as_dict(as_dict(rule).get("metrics")).get("passRate")
        for rule in new_rules
    }

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "corpusDir": display_path(input_dir, repo_root),
            "baseReport": display_path(base_report_path, repo_root),
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "candidateKeys": as_int(base_totals.get("candidateKeys"), 0),
            "mappedCandidateKeys": as_int(base_totals.get("mappedCandidateKeys"), 0),
            "ruleCount": merged_rule_count,
            "ruleEvaluations": merged_evaluations,
            "ruleFailures": merged_failures,
            "filesWithAnyRuleFailure": len(merged_file_failures),
            "failureTaxonomyCodeCount": len(merged_failure_tax),
        },
        "priorityCoverage": {
            "targetedKeys": [str(x) for x in as_list(base_priority.get("targetedKeys")) if str(x)],
            "mappedKeys": [str(x) for x in as_list(base_priority.get("mappedKeys")) if str(x)],
            "missingKeys": base_missing,
            "coverageRatio": round(clamp01(float(as_int(base_totals.get("mappedCandidateKeys"), 0)) / float(max(1, as_int(base_totals.get("candidateKeys"), 0)))), 6),
            "m19DescriptorTargetKeys": [str(spec["derivedFromCandidateKeys"][0]) for spec in NEW_RULE_SPECS],
            "m19DescriptorRulePassRates": m19_ratio_by_rule,
        },
        "failureTaxonomy": [
            {"code": code, "count": int(count)}
            for code, count in sorted(merged_failure_tax.items(), key=lambda item: (-int(item[1]), str(item[0])))
        ],
        "rules": merged_rules,
        "rulesWithNoApplicability": rules_with_no_applicability,
        "fileFailures": [
            {"file": file_name, "failedRules": rule_keys}
            for file_name, rule_keys in sorted(merged_file_failures.items(), key=lambda item: item[0])
        ],
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        f"M19 VALIDATOR EXPANSION {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} rules={merged_rule_count} "
        f"failures={merged_failures} report={display_path(report_out, repo_root)}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


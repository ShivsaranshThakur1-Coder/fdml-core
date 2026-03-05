#!/usr/bin/env python3
"""M20 validator expansion using source-grounded descriptor applicability."""

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
        "key": "rule:source_grounded_energy_profile_alignment",
        "name": "source_grounded_energy_profile_alignment",
        "description": "If source text signals energy-profile cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.style.energy_profile"],
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
        "failureCode": "missing_source_grounded_energy_profile",
    },
    {
        "key": "rule:source_grounded_call_response_alignment",
        "name": "source_grounded_call_response_alignment",
        "description": "If source text signals call-response cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.style.call_response_mode"],
        "patterns": [
            r"\bcall and response\b",
            r"\bcall-response\b",
            r"\bresponse chant\b",
        ],
        "failureCode": "missing_source_grounded_call_response",
    },
    {
        "key": "rule:source_grounded_improvisation_alignment",
        "name": "source_grounded_improvisation_alignment",
        "description": "If source text signals improvisation cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.style.improvisation_mode"],
        "patterns": [
            r"\bimprovis\w*\b",
            r"\bfreestyle\b",
            r"\bspontaneous\b",
            r"\bad[ -]?lib\b",
            r"\bset sequence\b",
            r"\bcodified\b",
        ],
        "failureCode": "missing_source_grounded_improvisation",
    },
    {
        "key": "rule:source_grounded_impact_alignment",
        "name": "source_grounded_impact_alignment",
        "description": "If source text signals impact cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.performance.impact_profile"],
        "patterns": [
            r"\bstomp\w*\b",
            r"\bstamp\w*\b",
            r"\bclap\w*\b",
            r"\bheel\b",
            r"\bpercussive\b",
            r"\bglide\w*\b",
            r"\bflow\w*\b",
        ],
        "failureCode": "missing_source_grounded_impact_profile",
    },
    {
        "key": "rule:source_grounded_rotation_alignment",
        "name": "source_grounded_rotation_alignment",
        "description": "If source text signals rotation cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.performance.rotation_profile"],
        "patterns": [
            r"\bturn\w*\b",
            r"\bspin\w*\b",
            r"\btwirl\w*\b",
            r"\bpivot\w*\b",
            r"\brotation\b",
        ],
        "failureCode": "missing_source_grounded_rotation_profile",
    },
    {
        "key": "rule:source_grounded_elevation_alignment",
        "name": "source_grounded_elevation_alignment",
        "description": "If source text signals elevation cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.performance.elevation_profile"],
        "patterns": [
            r"\bjump\w*\b",
            r"\bleap\w*\b",
            r"\bhop\w*\b",
            r"\bbounce\w*\b",
            r"\belevat\w*\b",
        ],
        "failureCode": "missing_source_grounded_elevation_profile",
    },
    {
        "key": "rule:source_grounded_partner_alignment",
        "name": "source_grounded_partner_alignment",
        "description": "If source text signals partner interaction cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.performance.partner_interaction"],
        "patterns": [
            r"\bpartner\w*\b",
            r"\bcouple\w*\b",
            r"\bpair\w*\b",
            r"\bhold hands\b",
            r"\bfacing each other\b",
        ],
        "failureCode": "missing_source_grounded_partner_interaction",
    },
    {
        "key": "rule:source_grounded_spatial_alignment",
        "name": "source_grounded_spatial_alignment",
        "description": "If source text signals spatial-pattern cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.style.spatial_pattern"],
        "patterns": [
            r"\bcircle\w*\b",
            r"\bring\b",
            r"\bline\w*\b",
            r"\bprocession\w*\b",
            r"\bprogress\w*\b",
        ],
        "failureCode": "missing_source_grounded_spatial_pattern",
    },
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Compose an M20 validator expansion report by augmenting M17 validator "
            "outputs with source-grounded descriptor realism rules."
        )
    )
    ap.add_argument(
        "--input-dir",
        default="out/m20_descriptor_evidence/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--base-report",
        required=True,
        help="base M17 validator report for the same corpus path",
    )
    ap.add_argument(
        "--source-text-dir",
        action="append",
        default=[],
        help="directory containing acquired source .txt files (repeatable)",
    )
    ap.add_argument(
        "--report-out",
        default="out/m20_validator_expansion_report.json",
        help="output path for M20 validator expansion report",
    )
    ap.add_argument("--label", default="m20-validator-expansion-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=100, help="minimum expected total files")
    ap.add_argument("--min-rules", type=int, default=50, help="minimum expanded rule count required")
    ap.add_argument(
        "--max-rules-with-no-applicability",
        type=int,
        default=1,
        help="maximum allowed count of rules with zero applicable files",
    )
    ap.add_argument(
        "--min-total-applicable",
        type=int,
        default=80,
        help="minimum combined applicable-file count across all M20 rules",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m20_validator_expansion.py: {msg}", file=sys.stderr)
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


def infer_source_id(file_name: str) -> str:
    stem = file_name
    if stem.endswith(".fdml.xml"):
        stem = stem[: -len(".fdml.xml")]
    if "__" not in stem:
        return stem
    return stem.split("__", 1)[1].strip()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


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
    return normalize_text(" ".join(parts)).lower()


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


def find_first_match(patterns: list[re.Pattern[str]], text: str) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return normalize_text(match.group(0))
    return ""


def evaluate_new_rules(
    files: list[Path],
    source_text_map: dict[str, str],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, int], int, int, int]:
    file_blobs: dict[str, str] = {}
    source_by_file: dict[str, str] = {}
    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            raise RuntimeError(f"root element is not <fdml> in {file_path}")
        file_key = file_path.resolve().as_posix()
        file_blobs[file_key] = text_blob(root)

        source_id = infer_source_id(file_path.name)
        source_by_file[file_key] = source_text_map.get(source_id, "")

    new_rule_rows: list[dict[str, Any]] = []
    new_file_failures: dict[str, list[str]] = {}
    failure_code_counts: dict[str, int] = {}
    evaluations = 0
    failures = 0
    total_applicable = 0

    for spec in NEW_RULE_SPECS:
        key = str(spec["key"])
        patterns = [re.compile(pat, re.IGNORECASE) for pat in list(spec["patterns"])]
        fail_code = str(spec["failureCode"])

        applicable = 0
        passed = 0
        failed = 0
        skipped = 0
        local_fail_counts: dict[str, int] = {}
        failed_samples: list[dict[str, Any]] = []

        for file_path in files:
            file_key = file_path.resolve().as_posix()
            fdml_blob = file_blobs[file_key]
            source_blob = source_by_file[file_key]

            source_lexeme = find_first_match(patterns, source_blob)
            if not source_lexeme:
                skipped += 1
                continue

            applicable += 1
            total_applicable += 1
            evaluations += 1

            matched = any(bool(pattern.search(fdml_blob)) for pattern in patterns)
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
                failed_samples.append(
                    {
                        "file": display,
                        "codes": [fail_code],
                        "sourceEvidence": source_lexeme,
                    }
                )

        pass_rate = float(passed) / float(applicable) if applicable > 0 else 1.0
        new_rule_rows.append(
            {
                "key": key,
                "name": str(spec["name"]),
                "description": str(spec["description"]),
                "derivedFromCandidateKeys": [
                    str(x) for x in as_list(spec.get("derivedFromCandidateKeys"))
                ],
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

    return (
        new_rule_rows,
        new_file_failures,
        failure_code_counts,
        evaluations,
        failures,
        total_applicable,
    )


def main() -> int:
    args = parse_args()
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_rules <= 0:
        return fail("--min-rules must be > 0")
    if args.max_rules_with_no_applicability < 0:
        return fail("--max-rules-with-no-applicability must be >= 0")
    if args.min_total_applicable < 0:
        return fail("--min-total-applicable must be >= 0")

    repo_root = Path(".").resolve()
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = (repo_root / input_dir).resolve()
    base_report_path = Path(args.base_report)
    if not base_report_path.is_absolute():
        base_report_path = (repo_root / base_report_path).resolve()
    source_text_dirs = [Path(p) for p in args.source_text_dir] if args.source_text_dir else []
    if not source_text_dirs:
        source_text_dirs = [Path("out/acquired_sources"), Path("out/acquired_sources_nonwiki")]
    source_text_dirs = [p if p.is_absolute() else (repo_root / p).resolve() for p in source_text_dirs]

    report_out = Path(args.report_out)
    if not report_out.is_absolute():
        report_out = (repo_root / report_out).resolve()

    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")
    if not base_report_path.exists():
        return fail(f"base report not found: {base_report_path}")
    for source_dir in source_text_dirs:
        if not source_dir.is_dir():
            return fail(f"source-text directory not found: {source_dir}")

    files = sorted(input_dir.glob("*.fdml.xml"))
    if len(files) < args.min_total_files:
        return fail(f"source file count {len(files)} is below --min-total-files {args.min_total_files}")

    source_text_map = load_source_texts(source_text_dirs)

    base = load_json(base_report_path)
    base_rules = [as_dict(x) for x in as_list(base.get("rules"))]
    base_file_failures = {
        str(as_dict(row).get("file") or ""): list(as_list(as_dict(row).get("failedRules")))
        for row in as_list(base.get("fileFailures"))
    }
    base_failure_tax = {
        str(as_dict(row).get("code") or ""): as_int(as_dict(row).get("count"), 0)
        for row in as_list(base.get("failureTaxonomy"))
    }
    base_totals = as_dict(base.get("totals"))
    base_priority = as_dict(base.get("priorityCoverage"))
    base_missing = [str(x) for x in as_list(base_priority.get("missingKeys")) if str(x)]

    (
        new_rules,
        new_file_failures,
        new_failure_tax,
        new_evaluations,
        new_failures,
        total_applicable,
    ) = evaluate_new_rules(files, source_text_map, repo_root)

    # M20 focuses on source-grounded descriptor realism layer only.
    # Base report is used for candidate mapping integrity and context, not to carry
    # forward unrelated historical failures into M20 burndown math.
    layer_rules = new_rules
    layer_file_failures = {
        file_name: sorted(set([str(x) for x in rule_keys if str(x)]))
        for file_name, rule_keys in new_file_failures.items()
        if file_name
    }
    layer_failure_tax = {str(code): int(count) for code, count in new_failure_tax.items() if str(code)}

    rules_with_no_applicability = [
        str(as_dict(rule).get("key") or "")
        for rule in layer_rules
        if as_int(as_dict(as_dict(rule).get("metrics")).get("applicableFiles"), 0) <= 0
    ]

    layer_rule_count = len(layer_rules)
    layer_evaluations = new_evaluations
    layer_failures = new_failures

    checks = [
        {
            "id": "source_files_min",
            "ok": len(files) >= args.min_total_files,
            "detail": f"source_files={len(files)} min={args.min_total_files}",
        },
        {
            "id": "expanded_rules_min",
            "ok": layer_rule_count >= args.min_rules,
            "detail": f"rules={layer_rule_count} min={args.min_rules}",
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
            "id": "m20_descriptor_rules_added",
            "ok": len(new_rules) >= len(NEW_RULE_SPECS),
            "detail": f"m20_rules={len(new_rules)} expected={len(NEW_RULE_SPECS)}",
        },
        {
            "id": "source_grounded_applicability_min",
            "ok": total_applicable >= args.min_total_applicable,
            "detail": f"total_applicable={total_applicable} min={args.min_total_applicable}",
        },
        {
            "id": "failure_taxonomy_recorded",
            "ok": (layer_failures == 0) or (len(layer_failure_tax) > 0),
            "detail": f"rule_failures={layer_failures} taxonomy_codes={len(layer_failure_tax)}",
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    m20_ratio_by_rule = {
        str(as_dict(rule).get("key") or ""): as_dict(as_dict(rule).get("metrics")).get("passRate")
        for rule in new_rules
    }
    m20_applicable_by_rule = {
        str(as_dict(rule).get("key") or ""): as_int(as_dict(as_dict(rule).get("metrics")).get("applicableFiles"), 0)
        for rule in new_rules
    }

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "corpusDir": display_path(input_dir, repo_root),
            "baseReport": display_path(base_report_path, repo_root),
            "sourceTextDirs": [display_path(p, repo_root) for p in source_text_dirs],
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "candidateKeys": as_int(base_totals.get("candidateKeys"), 0),
            "mappedCandidateKeys": as_int(base_totals.get("mappedCandidateKeys"), 0),
            "ruleCount": layer_rule_count,
            "ruleEvaluations": layer_evaluations,
            "ruleFailures": layer_failures,
            "filesWithAnyRuleFailure": len(layer_file_failures),
            "failureTaxonomyCodeCount": len(layer_failure_tax),
            "m20SourceGroundedApplicable": total_applicable,
        },
        "priorityCoverage": {
            "targetedKeys": [str(x) for x in as_list(base_priority.get("targetedKeys")) if str(x)],
            "mappedKeys": [str(x) for x in as_list(base_priority.get("mappedKeys")) if str(x)],
            "missingKeys": base_missing,
            "coverageRatio": round(
                clamp01(
                    float(as_int(base_totals.get("mappedCandidateKeys"), 0))
                    / float(max(1, as_int(base_totals.get("candidateKeys"), 0)))
                ),
                6,
            ),
            "m20DescriptorTargetKeys": [
                str(as_list(spec.get("derivedFromCandidateKeys"))[0]) for spec in NEW_RULE_SPECS
            ],
            "m20DescriptorRulePassRates": m20_ratio_by_rule,
            "m20DescriptorApplicableByRule": m20_applicable_by_rule,
        },
        "failureTaxonomy": [
            {"code": code, "count": int(count)}
            for code, count in sorted(layer_failure_tax.items(), key=lambda item: (-int(item[1]), str(item[0])))
        ],
        "rules": layer_rules,
        "rulesWithNoApplicability": rules_with_no_applicability,
        "fileFailures": [
            {"file": file_name, "failedRules": rule_keys}
            for file_name, rule_keys in sorted(layer_file_failures.items(), key=lambda item: item[0])
        ],
        "baseReportSummary": {
            "baseReportPath": display_path(base_report_path, repo_root),
            "baseRuleCount": len(base_rules),
            "baseRuleFailures": as_int(base_totals.get("ruleFailures"), 0),
            "baseFilesWithAnyRuleFailure": as_int(base_totals.get("filesWithAnyRuleFailure"), 0),
            "baseFailureTaxonomyCodeCount": len(base_failure_tax),
        },
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        f"M20 VALIDATOR EXPANSION {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} rules={layer_rule_count} failures={layer_failures} "
        f"applicable={total_applicable} report={display_path(report_out, repo_root)}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

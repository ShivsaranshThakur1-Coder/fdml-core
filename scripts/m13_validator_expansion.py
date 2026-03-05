#!/usr/bin/env python3
"""Expanded full-corpus validator stack derived from M13 registry/fit priorities."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable


RuleFn = Callable[[dict[str, Any]], tuple[bool, bool, list[str]]]

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
        description="Run expanded M13 validator stack and publish explicit failure taxonomy."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m9_full_description_uplift/run1",
        help="directory containing promoted .fdml.xml files",
    )
    ap.add_argument(
        "--registry-report",
        default="out/m13_parameter_registry.json",
        help="path to M13 parameter registry report",
    )
    ap.add_argument(
        "--fit-report",
        default="out/m13_fdml_fit_report.json",
        help="path to M13 fit analysis report",
    )
    ap.add_argument(
        "--report-out",
        default="out/m13_validator_expansion_report.json",
        help="output path for validator expansion report",
    )
    ap.add_argument(
        "--label",
        default="m13-validator-expansion",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum source file count required",
    )
    ap.add_argument(
        "--min-rules",
        type=int,
        default=10,
        help="minimum expanded rules required",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m13_validator_expansion.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def is_placeholder_value(value: str) -> bool:
    token = normalize_value(value)
    if token in PLACEHOLDER_VALUES:
        return True
    if token.startswith("unknown") or token.startswith("unspecified"):
        return True
    return False


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def canonical_path(path_value: str | Path, repo_root: Path) -> str:
    path = Path(path_value)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (repo_root / path).resolve()
    return resolved.as_posix()


def display_path(abs_path: str | Path, repo_root: Path) -> str:
    path = Path(abs_path)
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except Exception:
        return path.resolve().as_posix()


def attr(node: ET.Element | None, name: str) -> str:
    if node is None:
        return ""
    return str(node.get(name) or "").strip()


def collect_file_meta(files: list[Path]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for file_path in files:
        root = ET.parse(file_path).getroot()
        version = str(root.get("version") or "").strip()
        formation_node = root.find("./meta/geometry/formation")
        formation_kind = attr(formation_node, "kind")
        woman_side = attr(formation_node, "womanSide")
        origin_country = attr(root.find("./meta/origin"), "country")
        origin_region = attr(root.find("./meta/origin"), "region")
        hold_kind = attr(root.find("./meta/geometry/hold"), "kind")
        dancers_count_text = attr(root.find("./meta/geometry/dancers"), "count")
        has_dancers_count = False
        if dancers_count_text:
            try:
                has_dancers_count = int(dancers_count_text) > 0
            except Exception:
                has_dancers_count = False

        has_pair_relationship = False
        for pair in root.findall("./body/geometry/couples/pair"):
            if attr(pair, "relationship"):
                has_pair_relationship = True
                break

        has_primitive_dir = False
        has_primitive_frame = False
        has_primitive_axis = False
        has_primitive_preserve_order = False
        has_relpos_primitive = False
        has_relpos_relation = False
        has_turn_primitive = False
        for prim in root.findall(".//figure/step/geo/primitive"):
            kind = attr(prim, "kind")
            if attr(prim, "dir"):
                has_primitive_dir = True
            if attr(prim, "frame"):
                has_primitive_frame = True
            if attr(prim, "axis"):
                has_primitive_axis = True
            if attr(prim, "preserveOrder"):
                has_primitive_preserve_order = True
            if kind == "relpos":
                has_relpos_primitive = True
                if attr(prim, "relation"):
                    has_relpos_relation = True
            if kind in {"turn", "twirl"}:
                has_turn_primitive = True

        has_turn_action = False
        for step in root.findall(".//figure/step"):
            action = attr(step, "action").lower()
            if ("turn" in action) or ("spin" in action) or ("pivot" in action):
                has_turn_action = True
                break

        out[file_path.resolve().as_posix()] = {
            "version": version,
            "formationKind": formation_kind,
            "womanSide": woman_side,
            "originCountry": origin_country,
            "originRegion": origin_region,
            "holdKind": hold_kind,
            "hasDancersCount": has_dancers_count,
            "hasPairRelationship": has_pair_relationship,
            "hasPrimitiveDir": has_primitive_dir,
            "hasPrimitiveFrame": has_primitive_frame,
            "hasPrimitiveAxis": has_primitive_axis,
            "hasPrimitivePreserveOrder": has_primitive_preserve_order,
            "hasRelposPrimitive": has_relpos_primitive,
            "hasRelposRelation": has_relpos_relation,
            "hasTurnCue": has_turn_action or has_turn_primitive,
        }
    return out


def evaluate_rule_origin_country_specific(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    country = str(meta.get("originCountry") or "")
    if not country:
        return True, False, ["missing_origin_country"]
    if is_placeholder_value(country):
        return True, False, ["placeholder_origin_country"]
    return True, True, []


def evaluate_rule_origin_region_specific(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    region = str(meta.get("originRegion") or "")
    if not region:
        return True, False, ["missing_origin_region"]
    if is_placeholder_value(region):
        return True, False, ["placeholder_origin_region"]
    return True, True, []


def evaluate_rule_line_like_requires_dir(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    formation = str(meta.get("formationKind") or "")
    applicable = formation in {"line", "twoLinesFacing"}
    if not applicable:
        return False, True, []
    return True, bool(meta.get("hasPrimitiveDir")), ["missing_primitive_dir_contract"]


def evaluate_rule_line_like_requires_frame(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    formation = str(meta.get("formationKind") or "")
    applicable = formation in {"line", "twoLinesFacing"}
    if not applicable:
        return False, True, []
    return True, bool(meta.get("hasPrimitiveFrame")), ["missing_primitive_frame_contract"]


def evaluate_rule_circle_requires_dir(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "circle"
    if not applicable:
        return False, True, []
    return True, bool(meta.get("hasPrimitiveDir")), ["missing_circle_primitive_dir_contract"]


def evaluate_rule_circle_requires_preserve_order(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "circle"
    if not applicable:
        return False, True, []
    return (
        True,
        bool(meta.get("hasPrimitivePreserveOrder")),
        ["missing_circle_preserve_order_contract"],
    )


def evaluate_rule_rotation_requires_axis(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = bool(meta.get("hasTurnCue"))
    if not applicable:
        return False, True, []
    return True, bool(meta.get("hasPrimitiveAxis")), ["missing_rotation_axis_contract"]


def evaluate_rule_couple_requires_woman_side(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "couple"
    if not applicable:
        return False, True, []
    woman_side = str(meta.get("womanSide") or "")
    if not woman_side:
        return True, False, ["missing_woman_side_contract"]
    if woman_side not in {"left", "right"}:
        return True, False, ["invalid_woman_side_contract"]
    return True, True, []


def evaluate_rule_couple_requires_pair_relationship(
    meta: dict[str, Any],
) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "couple"
    if not applicable:
        return False, True, []
    return (
        True,
        bool(meta.get("hasPairRelationship")),
        ["missing_pair_relationship_contract"],
    )


def evaluate_rule_couple_relpos_requires_relation(
    meta: dict[str, Any],
) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "couple" and bool(
        meta.get("hasRelposPrimitive")
    )
    if not applicable:
        return False, True, []
    return (
        True,
        bool(meta.get("hasRelposRelation")),
        ["missing_relpos_relation_contract"],
    )


def evaluate_rule_formation_requires_dancers_count(
    meta: dict[str, Any],
) -> tuple[bool, bool, list[str]]:
    formation = str(meta.get("formationKind") or "")
    applicable = formation in {"line", "twoLinesFacing", "circle"}
    if not applicable:
        return False, True, []
    return True, bool(meta.get("hasDancersCount")), ["missing_dancers_count_contract"]


def evaluate_rule_couple_requires_hold_kind(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "couple"
    if not applicable:
        return False, True, []
    return True, bool(str(meta.get("holdKind") or "")), ["missing_hold_kind_contract"]


RULE_SPECS: list[dict[str, Any]] = [
    {
        "key": "rule:origin_country_specific_non_placeholder",
        "name": "origin_country_specific_non_placeholder",
        "description": "Origin country must be present and non-placeholder.",
        "priorityKeys": ["meta.origin.country"],
        "evaluate": evaluate_rule_origin_country_specific,
    },
    {
        "key": "rule:origin_region_specific_non_placeholder",
        "name": "origin_region_specific_non_placeholder",
        "description": "Origin region must be present and non-placeholder.",
        "priorityKeys": ["meta.origin.region"],
        "evaluate": evaluate_rule_origin_region_specific,
    },
    {
        "key": "rule:line_like_requires_primitive_dir",
        "name": "line_like_requires_primitive_dir",
        "description": "Line and two-lines-facing formations require primitive direction semantics.",
        "priorityKeys": ["step.geo.primitive.dir"],
        "evaluate": evaluate_rule_line_like_requires_dir,
    },
    {
        "key": "rule:line_like_requires_primitive_frame",
        "name": "line_like_requires_primitive_frame",
        "description": "Line and two-lines-facing formations require primitive frame semantics.",
        "priorityKeys": ["step.geo.primitive.frame"],
        "evaluate": evaluate_rule_line_like_requires_frame,
    },
    {
        "key": "rule:circle_requires_primitive_dir",
        "name": "circle_requires_primitive_dir",
        "description": "Circle formations require primitive direction semantics.",
        "priorityKeys": ["step.geo.primitive.dir"],
        "evaluate": evaluate_rule_circle_requires_dir,
    },
    {
        "key": "rule:circle_requires_preserve_order_marker",
        "name": "circle_requires_preserve_order_marker",
        "description": "Circle formations require preserve-order markers for topology constraints.",
        "priorityKeys": ["step.geo.primitive.preserveOrder"],
        "evaluate": evaluate_rule_circle_requires_preserve_order,
    },
    {
        "key": "rule:rotation_cues_require_axis",
        "name": "rotation_cues_require_axis",
        "description": "Rotation cues require explicit primitive axis semantics.",
        "priorityKeys": ["step.geo.primitive.axis"],
        "evaluate": evaluate_rule_rotation_requires_axis,
    },
    {
        "key": "rule:couple_requires_woman_side",
        "name": "couple_requires_woman_side",
        "description": "Couple formations require woman-side orientation semantics.",
        "priorityKeys": ["meta.geometry.formation.womanSide"],
        "evaluate": evaluate_rule_couple_requires_woman_side,
    },
    {
        "key": "rule:couple_requires_pair_relationship",
        "name": "couple_requires_pair_relationship",
        "description": "Couple formations require pair relationship metadata.",
        "priorityKeys": ["body.geometry.couples.pair.relationship"],
        "evaluate": evaluate_rule_couple_requires_pair_relationship,
    },
    {
        "key": "rule:couple_relpos_requires_relation",
        "name": "couple_relpos_requires_relation",
        "description": "Couple relpos primitives require relation direction values.",
        "priorityKeys": [
            "body.geometry.couples.pair.relationship",
            "step.geo.primitive.relation",
        ],
        "evaluate": evaluate_rule_couple_relpos_requires_relation,
    },
    {
        "key": "rule:formation_requires_dancers_count",
        "name": "formation_requires_dancers_count",
        "description": "Non-couple formations require dancer count metadata.",
        "priorityKeys": ["meta.geometry.dancers.count"],
        "evaluate": evaluate_rule_formation_requires_dancers_count,
    },
    {
        "key": "rule:couple_requires_hold_kind",
        "name": "couple_requires_hold_kind",
        "description": "Couple formations require hold/contact kind metadata.",
        "priorityKeys": ["meta.geometry.hold.kind"],
        "evaluate": evaluate_rule_couple_requires_hold_kind,
    },
]


def main() -> int:
    args = parse_args()
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_rules <= 0:
        return fail("--min-rules must be > 0")

    repo_root = Path(".").resolve()

    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = repo_root / input_dir
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")

    registry_path = Path(args.registry_report)
    if not registry_path.is_absolute():
        registry_path = repo_root / registry_path
    registry_path = registry_path.resolve()
    if not registry_path.is_file():
        return fail(f"registry report not found: {registry_path}")

    fit_path = Path(args.fit_report)
    if not fit_path.is_absolute():
        fit_path = repo_root / fit_path
    fit_path = fit_path.resolve()
    if not fit_path.is_file():
        return fail(f"fit report not found: {fit_path}")

    report_out = Path(args.report_out)
    if not report_out.is_absolute():
        report_out = repo_root / report_out
    report_out = report_out.resolve()

    files = sorted(input_dir.glob("*.fdml.xml"))
    if not files:
        return fail(f"no .fdml.xml files found in {input_dir}")
    if len(files) < args.min_total_files:
        return fail(
            f"source file count {len(files)} is below --min-total-files {args.min_total_files}"
        )

    registry_payload = load_json(registry_path)
    fit_payload = load_json(fit_path)
    registry_rows = [as_dict(x) for x in as_list(registry_payload.get("rows"))]
    registry_by_key = {str(row.get("key") or ""): row for row in registry_rows}
    priority_rows = [
        as_dict(x)
        for x in as_list(fit_payload.get("contractExpansionPriorities"))
        if str(as_dict(x).get("tier") or "") in {"P0", "P1"}
    ]
    targeted_priority_keys = sorted({str(row.get("key") or "") for row in priority_rows if row.get("key")})

    meta_map = collect_file_meta(files)
    file_abs_list = [canonical_path(f, repo_root) for f in files]
    file_display = {canonical_path(f, repo_root): display_path(f, repo_root) for f in files}

    if len(RULE_SPECS) < args.min_rules:
        return fail(f"expanded rule count {len(RULE_SPECS)} is below --min-rules {args.min_rules}")

    rule_rows: list[dict[str, Any]] = []
    file_failures: dict[str, list[str]] = {}
    failure_code_counts_global: dict[str, int] = {}
    total_evaluations = 0
    total_failures = 0
    mapped_priority_keys: set[str] = set()

    for spec in RULE_SPECS:
        key = str(spec["key"])
        name = str(spec["name"])
        description = str(spec["description"])
        priority_keys = [str(x) for x in spec["priorityKeys"]]
        evaluator: RuleFn = spec["evaluate"]
        for pkey in priority_keys:
            if pkey in targeted_priority_keys:
                mapped_priority_keys.add(pkey)

        applicable = 0
        passed = 0
        failed = 0
        skipped = 0
        failure_code_counts: dict[str, int] = {}
        failed_samples: list[dict[str, Any]] = []

        for file_abs in file_abs_list:
            meta = as_dict(meta_map.get(file_abs))
            is_applicable, is_pass, fail_codes = evaluator(meta)
            if not is_applicable:
                skipped += 1
                continue
            applicable += 1
            total_evaluations += 1
            if is_pass:
                passed += 1
                continue
            failed += 1
            total_failures += 1
            display = file_display[file_abs]
            file_failures.setdefault(display, []).append(key)
            for code in fail_codes:
                failure_code_counts[code] = int(failure_code_counts.get(code, 0)) + 1
                failure_code_counts_global[code] = int(failure_code_counts_global.get(code, 0)) + 1
            if len(failed_samples) < 20:
                failed_samples.append({"file": display, "codes": fail_codes})

        pass_rate = 1.0 if applicable == 0 else float(passed) / float(applicable)
        priority_evidence = []
        for pkey in priority_keys:
            prow = as_dict(registry_by_key.get(pkey))
            priority_evidence.append(
                {
                    "key": pkey,
                    "supportRatio": clamp01(float(prow.get("supportRatio", 0.0))),
                    "nonPlaceholderRatio": clamp01(float(prow.get("nonPlaceholderRatio", 0.0))),
                }
            )
        rule_rows.append(
            {
                "key": key,
                "name": name,
                "description": description,
                "derivedFromPriorityKeys": priority_keys,
                "priorityEvidence": priority_evidence,
                "metrics": {
                    "applicableFiles": applicable,
                    "passedFiles": passed,
                    "failedFiles": failed,
                    "skippedFiles": skipped,
                    "passRate": round(pass_rate, 6),
                    "failureCodeCounts": failure_code_counts,
                },
                "failedSamples": failed_samples,
            }
        )

    rules_with_no_applicability = [
        str(row.get("key") or "")
        for row in rule_rows
        if int(as_dict(row.get("metrics")).get("applicableFiles", 0)) <= 0
    ]
    missing_priority_keys = sorted([key for key in targeted_priority_keys if key not in mapped_priority_keys])
    priority_coverage_ratio = (
        1.0
        if not targeted_priority_keys
        else float(len(mapped_priority_keys)) / float(len(targeted_priority_keys))
    )

    checks = [
        {
            "id": "source_files_min",
            "ok": len(files) >= args.min_total_files,
            "detail": f"source_files={len(files)} min={args.min_total_files}",
        },
        {
            "id": "expanded_rules_min",
            "ok": len(rule_rows) >= args.min_rules,
            "detail": f"rules={len(rule_rows)} min={args.min_rules}",
        },
        {
            "id": "all_rules_have_applicability",
            "ok": len(rules_with_no_applicability) == 0,
            "detail": f"rules_with_no_applicability={len(rules_with_no_applicability)}",
        },
        {
            "id": "priority_key_mapping_complete",
            "ok": len(missing_priority_keys) == 0,
            "detail": (
                f"targeted_priority_keys={len(targeted_priority_keys)} "
                f"mapped={len(mapped_priority_keys)} missing={len(missing_priority_keys)}"
            ),
        },
        {
            "id": "failure_taxonomy_recorded",
            "ok": (total_failures == 0) or (len(failure_code_counts_global) > 0),
            "detail": f"rule_failures={total_failures} taxonomy_codes={len(failure_code_counts_global)}",
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "corpusDir": display_path(input_dir, repo_root),
            "registryReport": display_path(registry_path, repo_root),
            "fitReport": display_path(fit_path, repo_root),
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "priorityRowsP0P1": len(priority_rows),
            "targetedPriorityKeys": len(targeted_priority_keys),
            "mappedPriorityKeys": len(mapped_priority_keys),
            "ruleCount": len(rule_rows),
            "ruleEvaluations": total_evaluations,
            "ruleFailures": total_failures,
            "filesWithAnyRuleFailure": len(file_failures),
            "failureTaxonomyCodeCount": len(failure_code_counts_global),
        },
        "priorityCoverage": {
            "targetedKeys": targeted_priority_keys,
            "mappedKeys": sorted(mapped_priority_keys),
            "missingKeys": missing_priority_keys,
            "coverageRatio": round(priority_coverage_ratio, 6),
        },
        "failureTaxonomy": [
            {"code": code, "count": int(count)}
            for code, count in sorted(
                failure_code_counts_global.items(), key=lambda item: (-int(item[1]), str(item[0]))
            )
        ],
        "rules": rule_rows,
        "rulesWithNoApplicability": rules_with_no_applicability,
        "fileFailures": [
            {"file": file_name, "failedRules": sorted(set(rule_keys))}
            for file_name, rule_keys in sorted(file_failures.items(), key=lambda item: item[0])
        ],
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        f"M13 VALIDATOR EXPANSION {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} rules={len(rule_rows)} "
        f"failures={total_failures} report={display_path(report_out, repo_root)}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic full-corpus parameter registry for M13."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable


Extractor = Callable[[ET.Element], list[str]]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build evidence-linked parameter registry and FDML fit snapshot from promoted corpus."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m9_full_description_uplift/run1",
        help="directory containing promoted .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m13_parameter_registry.json",
        help="output path for parameter registry report",
    )
    ap.add_argument(
        "--fit-report-out",
        default="out/m13_fdml_fit_report.json",
        help="output path for FDML fit snapshot report",
    )
    ap.add_argument(
        "--label",
        default="m13-parameter-registry",
        help="registry report label",
    )
    ap.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="optional maximum files to process (0 = all)",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum corpus file count required",
    )
    ap.add_argument(
        "--min-unique-keys",
        type=int,
        default=15,
        help="minimum unique parameter keys that must be discovered",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m13_parameter_registry.py: {msg}", file=sys.stderr)
    return 2


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_files(input_dir: Path, max_files: int) -> list[Path]:
    files = sorted(input_dir.glob("*.fdml.xml"))
    if max_files > 0:
        files = files[:max_files]
    return files


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def attr(node: ET.Element | None, name: str) -> str:
    if node is None:
        return ""
    return str(node.get(name) or "").strip()


def uniq_sorted(values: list[str]) -> list[str]:
    out = sorted({v.strip() for v in values if v and v.strip()})
    return out


def evidence_from_patterns(file_path: Path, file_name: str, patterns: list[str]) -> dict[str, Any]:
    text = file_path.read_text(encoding="utf-8")
    flags = re.IGNORECASE | re.MULTILINE
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if not match:
            continue
        start = match.start()
        line_no = text.count("\n", 0, start) + 1
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        if line_end < 0:
            line_end = len(text)
        line_text = norm_text(text[line_start:line_end])
        return {
            "file": file_name,
            "text": line_text,
            "span": {"start": line_start, "end": line_end},
            "lineIds": [f"L{line_no:04d}"],
        }
    return {
        "file": file_name,
        "text": "",
        "span": {"start": -1, "end": -1},
        "lineIds": [],
    }


def ex_meta_origin_country(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/origin"), "country")])


def ex_meta_origin_region(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/origin"), "region")])


def ex_meta_type_genre(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/type"), "genre")])


def ex_meta_type_style(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/type"), "style")])


def ex_meta_meter_value(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/meter"), "value")])


def ex_meta_meter_rhythm(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/meter"), "rhythmPattern")])


def ex_meta_tempo_bpm(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/tempo"), "bpm")])


def ex_meta_formation_kind(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/geometry/formation"), "kind")])


def ex_meta_formation_woman_side(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/geometry/formation"), "womanSide")])


def ex_meta_hold_kind(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/geometry/hold"), "kind")])


def ex_meta_dancers_count(root: ET.Element) -> list[str]:
    return uniq_sorted([attr(root.find("./meta/geometry/dancers"), "count")])


def ex_meta_role_ids(root: ET.Element) -> list[str]:
    values = [attr(node, "id") for node in root.findall("./meta/geometry/roles/role")]
    return uniq_sorted(values)


def ex_pair_relationship(root: ET.Element) -> list[str]:
    values = [attr(node, "relationship") for node in root.findall("./body/geometry/couples/pair")]
    return uniq_sorted(values)


def ex_step_direction(root: ET.Element) -> list[str]:
    values = [attr(node, "direction") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_step_facing(root: ET.Element) -> list[str]:
    values = [attr(node, "facing") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_step_beats(root: ET.Element) -> list[str]:
    values = [attr(node, "beats") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_step_count(root: ET.Element) -> list[str]:
    values = [attr(node, "count") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_step_start_foot(root: ET.Element) -> list[str]:
    values = [attr(node, "startFoot") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_step_end_foot(root: ET.Element) -> list[str]:
    values = [attr(node, "endFoot") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_step_action(root: ET.Element) -> list[str]:
    values = [attr(node, "action") for node in root.findall(".//figure/step")]
    return uniq_sorted(values)


def ex_primitive_kind(root: ET.Element) -> list[str]:
    values = [attr(node, "kind") for node in root.findall(".//figure/step/geo/primitive")]
    return uniq_sorted(values)


def ex_primitive_dir(root: ET.Element) -> list[str]:
    values = [attr(node, "dir") for node in root.findall(".//figure/step/geo/primitive")]
    return uniq_sorted(values)


def ex_primitive_frame(root: ET.Element) -> list[str]:
    values = [attr(node, "frame") for node in root.findall(".//figure/step/geo/primitive")]
    return uniq_sorted(values)


def ex_primitive_axis(root: ET.Element) -> list[str]:
    values = [attr(node, "axis") for node in root.findall(".//figure/step/geo/primitive")]
    return uniq_sorted(values)


def ex_primitive_relation(root: ET.Element) -> list[str]:
    values = [attr(node, "relation") for node in root.findall(".//figure/step/geo/primitive")]
    return uniq_sorted(values)


def ex_primitive_preserve_order(root: ET.Element) -> list[str]:
    values = [attr(node, "preserveOrder") for node in root.findall(".//figure/step/geo/primitive")]
    return uniq_sorted(values)


PARAMETER_SPECS: list[dict[str, Any]] = [
    {
        "key": "meta.origin.country",
        "group": "context",
        "path": "/fdml/meta/origin/@country",
        "valueType": "string",
        "core": True,
        "description": "Origin country context in metadata.",
        "extract": ex_meta_origin_country,
        "evidencePatterns": [r"<origin\b[^>]*\bcountry="],
    },
    {
        "key": "meta.origin.region",
        "group": "context",
        "path": "/fdml/meta/origin/@region",
        "valueType": "string",
        "core": True,
        "description": "Origin region context in metadata.",
        "extract": ex_meta_origin_region,
        "evidencePatterns": [r"<origin\b[^>]*\bregion="],
    },
    {
        "key": "meta.type.genre",
        "group": "context",
        "path": "/fdml/meta/type/@genre",
        "valueType": "string",
        "core": True,
        "description": "Dance genre classification.",
        "extract": ex_meta_type_genre,
        "evidencePatterns": [r"<type\b[^>]*\bgenre="],
    },
    {
        "key": "meta.type.style",
        "group": "context",
        "path": "/fdml/meta/type/@style",
        "valueType": "string",
        "core": True,
        "description": "Dance style classification.",
        "extract": ex_meta_type_style,
        "evidencePatterns": [r"<type\b[^>]*\bstyle="],
    },
    {
        "key": "meta.meter.value",
        "group": "timing",
        "path": "/fdml/meta/meter/@value",
        "valueType": "string",
        "core": True,
        "description": "Declared meter signature.",
        "extract": ex_meta_meter_value,
        "evidencePatterns": [r"<meter\b[^>]*\bvalue="],
    },
    {
        "key": "meta.meter.rhythmPattern",
        "group": "timing",
        "path": "/fdml/meta/meter/@rhythmPattern",
        "valueType": "string",
        "core": True,
        "description": "Additive rhythm pattern declaration.",
        "extract": ex_meta_meter_rhythm,
        "evidencePatterns": [r"<meter\b[^>]*\brhythmPattern="],
    },
    {
        "key": "meta.tempo.bpm",
        "group": "timing",
        "path": "/fdml/meta/tempo/@bpm",
        "valueType": "integer",
        "core": True,
        "description": "Tempo declaration in BPM.",
        "extract": ex_meta_tempo_bpm,
        "evidencePatterns": [r"<tempo\b[^>]*\bbpm="],
    },
    {
        "key": "meta.geometry.formation.kind",
        "group": "formation",
        "path": "/fdml/meta/geometry/formation/@kind",
        "valueType": "string",
        "core": True,
        "description": "Top-level formation kind.",
        "extract": ex_meta_formation_kind,
        "evidencePatterns": [r"<formation\b[^>]*\bkind="],
    },
    {
        "key": "meta.geometry.formation.womanSide",
        "group": "formation",
        "path": "/fdml/meta/geometry/formation/@womanSide",
        "valueType": "string",
        "core": False,
        "description": "Couple-side orientation when formation is couple.",
        "extract": ex_meta_formation_woman_side,
        "evidencePatterns": [r"<formation\b[^>]*\bwomanSide="],
    },
    {
        "key": "meta.geometry.hold.kind",
        "group": "formation",
        "path": "/fdml/meta/geometry/hold/@kind",
        "valueType": "string",
        "core": False,
        "description": "Declared hold/contact configuration.",
        "extract": ex_meta_hold_kind,
        "evidencePatterns": [r"<hold\b[^>]*\bkind="],
    },
    {
        "key": "meta.geometry.dancers.count",
        "group": "formation",
        "path": "/fdml/meta/geometry/dancers/@count",
        "valueType": "integer",
        "core": False,
        "description": "Declared dancer count.",
        "extract": ex_meta_dancers_count,
        "evidencePatterns": [r"<dancers\b[^>]*\bcount="],
    },
    {
        "key": "meta.geometry.roles.role.id",
        "group": "roles",
        "path": "/fdml/meta/geometry/roles/role/@id",
        "valueType": "string[]",
        "core": False,
        "description": "Declared role identifiers.",
        "extract": ex_meta_role_ids,
        "evidencePatterns": [r"<role\b[^>]*\bid="],
    },
    {
        "key": "body.geometry.couples.pair.relationship",
        "group": "roles",
        "path": "/fdml/body/geometry/couples/pair/@relationship",
        "valueType": "string",
        "core": False,
        "description": "Couple relationship semantics.",
        "extract": ex_pair_relationship,
        "evidencePatterns": [r"<pair\b[^>]*\brelationship="],
    },
    {
        "key": "step.direction",
        "group": "movement",
        "path": "/fdml/body//figure//step/@direction",
        "valueType": "string",
        "core": True,
        "description": "Per-step direction semantics.",
        "extract": ex_step_direction,
        "evidencePatterns": [r"<step\b[^>]*\bdirection="],
    },
    {
        "key": "step.facing",
        "group": "movement",
        "path": "/fdml/body//figure//step/@facing",
        "valueType": "string",
        "core": True,
        "description": "Per-step facing semantics.",
        "extract": ex_step_facing,
        "evidencePatterns": [r"<step\b[^>]*\bfacing="],
    },
    {
        "key": "step.beats",
        "group": "timing",
        "path": "/fdml/body//figure//step/@beats",
        "valueType": "integer",
        "core": True,
        "description": "Per-step beat duration.",
        "extract": ex_step_beats,
        "evidencePatterns": [r"<step\b[^>]*\bbeats="],
    },
    {
        "key": "step.count",
        "group": "timing",
        "path": "/fdml/body//figure//step/@count",
        "valueType": "string",
        "core": True,
        "description": "Per-step count marker.",
        "extract": ex_step_count,
        "evidencePatterns": [r"<step\b[^>]*\bcount="],
    },
    {
        "key": "step.startFoot",
        "group": "movement",
        "path": "/fdml/body//figure//step/@startFoot",
        "valueType": "string",
        "core": True,
        "description": "Per-step starting support foot.",
        "extract": ex_step_start_foot,
        "evidencePatterns": [r"<step\b[^>]*\bstartFoot="],
    },
    {
        "key": "step.endFoot",
        "group": "movement",
        "path": "/fdml/body//figure//step/@endFoot",
        "valueType": "string",
        "core": True,
        "description": "Per-step ending support foot.",
        "extract": ex_step_end_foot,
        "evidencePatterns": [r"<step\b[^>]*\bendFoot="],
    },
    {
        "key": "step.action",
        "group": "movement",
        "path": "/fdml/body//figure//step/@action",
        "valueType": "string",
        "core": False,
        "description": "Per-step action phrase.",
        "extract": ex_step_action,
        "evidencePatterns": [r"<step\b[^>]*\baction="],
    },
    {
        "key": "step.geo.primitive.kind",
        "group": "movement",
        "path": "/fdml/body//figure//step/geo/primitive/@kind",
        "valueType": "string",
        "core": True,
        "description": "Primitive action kind.",
        "extract": ex_primitive_kind,
        "evidencePatterns": [r"<primitive\b[^>]*\bkind="],
    },
    {
        "key": "step.geo.primitive.dir",
        "group": "movement",
        "path": "/fdml/body//figure//step/geo/primitive/@dir",
        "valueType": "string",
        "core": False,
        "description": "Primitive direction axis.",
        "extract": ex_primitive_dir,
        "evidencePatterns": [r"<primitive\b[^>]*\bdir="],
    },
    {
        "key": "step.geo.primitive.frame",
        "group": "movement",
        "path": "/fdml/body//figure//step/geo/primitive/@frame",
        "valueType": "string",
        "core": False,
        "description": "Primitive reference frame.",
        "extract": ex_primitive_frame,
        "evidencePatterns": [r"<primitive\b[^>]*\bframe="],
    },
    {
        "key": "step.geo.primitive.axis",
        "group": "movement",
        "path": "/fdml/body//figure//step/geo/primitive/@axis",
        "valueType": "string",
        "core": False,
        "description": "Primitive rotation axis.",
        "extract": ex_primitive_axis,
        "evidencePatterns": [r"<primitive\b[^>]*\baxis="],
    },
    {
        "key": "step.geo.primitive.relation",
        "group": "movement",
        "path": "/fdml/body//figure//step/geo/primitive/@relation",
        "valueType": "string",
        "core": False,
        "description": "Primitive relational semantic.",
        "extract": ex_primitive_relation,
        "evidencePatterns": [r"<primitive\b[^>]*\brelation="],
    },
    {
        "key": "step.geo.primitive.preserveOrder",
        "group": "movement",
        "path": "/fdml/body//figure//step/geo/primitive/@preserveOrder",
        "valueType": "boolean",
        "core": False,
        "description": "Primitive preserve-order invariant marker.",
        "extract": ex_primitive_preserve_order,
        "evidencePatterns": [r"<primitive\b[^>]*\bpreserveOrder="],
    },
]


def coverage_tier(ratio: float) -> str:
    if ratio >= 0.95:
        return "universal"
    if ratio >= 0.75:
        return "high"
    if ratio >= 0.4:
        return "medium"
    if ratio > 0.0:
        return "low"
    return "none"


def classify_presence_fit(missing_core_count: int) -> str:
    if missing_core_count == 0:
        return "fully_fit"
    if missing_core_count <= 2:
        return "near_fit"
    if missing_core_count <= 5:
        return "partial_fit"
    return "requires_contract_expansion"


def classify_expressive_fit(expressive_gap_count: int) -> str:
    if expressive_gap_count == 0:
        return "fully_fit"
    if expressive_gap_count <= 1:
        return "near_fit"
    if expressive_gap_count <= 2:
        return "partial_fit"
    return "requires_contract_expansion"


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

CONTEXT_SPECIFIC_KEYS = ["meta.origin.country", "meta.origin.region"]

FORMATION_ADVANCED_REQUIRED: dict[str, list[str]] = {
    "line": ["step.geo.primitive.dir", "step.geo.primitive.frame"],
    "twoLinesFacing": ["step.geo.primitive.dir", "step.geo.primitive.frame"],
    "circle": ["step.geo.primitive.preserveOrder", "step.geo.primitive.dir"],
    "couple": [
        "meta.geometry.formation.womanSide",
        "body.geometry.couples.pair.relationship",
        "step.geo.primitive.relation",
    ],
}

EXPRESSIVENESS_CRITICAL_KEYS = {
    "meta.origin.country",
    "meta.origin.region",
    "step.geo.primitive.dir",
    "step.geo.primitive.frame",
    "step.geo.primitive.axis",
    "step.geo.primitive.preserveOrder",
}

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def is_placeholder_value(value: str) -> bool:
    token = normalize_value(value)
    if token in PLACEHOLDER_VALUES:
        return True
    if token.startswith("unknown") or token.startswith("unspecified"):
        return True
    return False


def compute_non_placeholder_ratio(value_counts: dict[str, int]) -> tuple[int, int, float]:
    total_instances = 0
    non_placeholder_instances = 0
    for value, count in value_counts.items():
        icount = int(count)
        total_instances += icount
        if not is_placeholder_value(value):
            non_placeholder_instances += icount
    ratio = float(non_placeholder_instances) / float(total_instances) if total_instances > 0 else 0.0
    return non_placeholder_instances, total_instances, round(ratio, 4)


def priority_for_row(row: dict[str, Any]) -> tuple[str, str, str]:
    key = str(row.get("key") or "")
    support_ratio = float(row.get("supportRatio") or 0.0)
    non_placeholder_ratio = float(row.get("nonPlaceholderRatio") or 0.0)
    group = str(row.get("group") or "")

    if key in CONTEXT_SPECIFIC_KEYS and non_placeholder_ratio < 0.5:
        return (
            "P0",
            "core context field is mostly placeholder and weak for real-world coverage",
            "prioritize context extraction and normalization from source evidence before further rule expansion",
        )
    if support_ratio == 0.0 and key in EXPRESSIVENESS_CRITICAL_KEYS:
        return (
            "P0",
            "critical expressiveness field has zero support across corpus",
            "extend extraction and mapping to capture this field deterministically in the unified FDML structure",
        )
    if support_ratio == 0.0:
        return (
            "P1",
            "field has zero support and blocks subset of advanced modeling",
            "add extraction heuristics for this field and validate against promoted corpus",
        )
    if support_ratio < 0.25:
        return (
            "P1",
            "field is present but coverage is too low for reliable full-corpus rule promotion",
            "increase field coverage in source-to-FDML conversion before enforcing strict validators",
        )
    if support_ratio < 0.5:
        return (
            "P2",
            "field has partial support and needs broader normalization",
            "expand normalization and add targeted validation checks for inconsistent files",
        )

    # Keep backlog focused on high-leverage gaps.
    if group == "movement" and support_ratio < 0.75:
        return (
            "P2",
            "movement field support remains moderate and can limit geometry-depth modeling",
            "continue iterative extraction upgrades and monitor support growth in registry runs",
        )
    return ("", "", "")


def main() -> int:
    args = parse_args()
    if args.max_files < 0:
        return fail("--max-files must be >= 0")
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_unique_keys <= 0:
        return fail("--min-unique-keys must be > 0")

    input_dir = Path(args.input_dir)
    report_out = Path(args.report_out)
    fit_report_out = Path(args.fit_report_out)
    if not input_dir.is_dir():
        return fail(f"input dir not found: {input_dir}")

    files = pick_files(input_dir, args.max_files)
    if not files:
        return fail(f"no .fdml.xml files found under: {input_dir}")
    if len(files) < args.min_total_files:
        return fail(
            f"total files {len(files)} is below minimum required {args.min_total_files}"
        )

    print(
        f"M13 PARAMETER REGISTRY START files={len(files)} input={input_dir.as_posix()}",
        file=sys.stderr,
    )

    registry: dict[str, dict[str, Any]] = {}
    for spec in PARAMETER_SPECS:
        registry[spec["key"]] = {
            "key": spec["key"],
            "group": spec["group"],
            "path": spec["path"],
            "valueType": spec["valueType"],
            "core": bool(spec["core"]),
            "description": spec["description"],
            "supportFiles": set(),
            "valueCounts": {},
            "evidence": {"file": "", "text": "", "span": {"start": -1, "end": -1}, "lineIds": []},
        }

    file_fit_rows: list[dict[str, Any]] = []
    core_keys = [spec["key"] for spec in PARAMETER_SPECS if bool(spec["core"])]

    for idx, file_path in enumerate(files, start=1):
        print(f"file={idx}/{len(files)} name={file_path.name}", file=sys.stderr)
        try:
            root = ET.parse(file_path).getroot()
        except Exception as exc:
            return fail(f"failed to parse XML '{file_path}': {exc}")

        file_name = file_path.name
        file_presence: dict[str, bool] = {}
        file_values: dict[str, list[str]] = {}

        for spec in PARAMETER_SPECS:
            key = spec["key"]
            extractor: Extractor = spec["extract"]
            values = uniq_sorted(extractor(root))
            file_values[key] = values
            present = len(values) > 0
            file_presence[key] = present
            if not present:
                continue

            row = registry[key]
            row["supportFiles"].add(file_name)
            for value in values:
                counts = row["valueCounts"]
                counts[value] = int(counts.get(value, 0)) + 1
            if not row["evidence"]["text"]:
                row["evidence"] = evidence_from_patterns(
                    file_path, file_name, list(spec["evidencePatterns"])
                )
                if not row["evidence"]["text"]:
                    row["evidence"] = {
                        "file": file_name,
                        "text": f"observed {key} via XML extraction",
                        "span": {"start": -1, "end": -1},
                        "lineIds": [],
                    }

        missing_core = sorted([key for key in core_keys if not file_presence.get(key, False)])
        formation_values = file_values.get("meta.geometry.formation.kind", [])
        formation_kind = formation_values[0] if formation_values else "unknown"
        required_advanced_keys = sorted(FORMATION_ADVANCED_REQUIRED.get(formation_kind, []))
        missing_advanced_keys = sorted(
            [key for key in required_advanced_keys if not file_presence.get(key, False)]
        )
        context_specific_keys_present = sorted(
            [
                key
                for key in CONTEXT_SPECIFIC_KEYS
                if any(not is_placeholder_value(value) for value in file_values.get(key, []))
            ]
        )
        context_specificity_gap = len(context_specific_keys_present) < len(CONTEXT_SPECIFIC_KEYS)
        expressive_gap_count = len(missing_core) + len(missing_advanced_keys) + (
            1 if context_specificity_gap else 0
        )
        file_fit_rows.append(
            {
                "file": file_name,
                "formationKind": formation_kind,
                "presentCoreCount": len(core_keys) - len(missing_core),
                "missingCoreCount": len(missing_core),
                "missingCoreKeys": missing_core,
                "requiredAdvancedKeys": required_advanced_keys,
                "missingAdvancedKeys": missing_advanced_keys,
                "contextSpecificKeysPresent": context_specific_keys_present,
                "contextSpecificityGap": context_specificity_gap,
                "contractPresenceFitClass": classify_presence_fit(len(missing_core)),
                "expressiveGapCount": expressive_gap_count,
                "expressiveFitClass": classify_expressive_fit(expressive_gap_count),
            }
        )

    rows_out: list[dict[str, Any]] = []
    keys_with_support = 0
    keys_with_evidence = 0
    for spec in sorted(PARAMETER_SPECS, key=lambda item: str(item["key"])):
        key = str(spec["key"])
        row = registry[key]
        support_files = sorted(list(row["supportFiles"]))
        support_count = len(support_files)
        support_ratio = round(float(support_count) / float(len(files)), 4)
        value_counts = row["valueCounts"]
        non_placeholder_count, value_instance_total, non_placeholder_ratio = compute_non_placeholder_ratio(
            value_counts
        )
        top_values = sorted(
            [
                {"value": value, "count": int(count)}
                for value, count in value_counts.items()
            ],
            key=lambda item: (-int(item["count"]), str(item["value"])),
        )[:10]
        if support_count > 0:
            keys_with_support += 1
        evidence = row["evidence"]
        if evidence.get("text"):
            keys_with_evidence += 1
        rows_out.append(
            {
                "key": key,
                "group": row["group"],
                "path": row["path"],
                "valueType": row["valueType"],
                "core": bool(row["core"]),
                "description": row["description"],
                "supportCount": support_count,
                "supportRatio": support_ratio,
                "coverageTier": coverage_tier(support_ratio),
                "nonPlaceholderCount": non_placeholder_count,
                "valueInstanceTotal": value_instance_total,
                "nonPlaceholderRatio": non_placeholder_ratio,
                "distinctValueCount": len(value_counts),
                "topValues": top_values,
                "sampleFiles": support_files[:5],
                "evidence": evidence,
            }
        )

    if keys_with_support < args.min_unique_keys:
        return fail(
            f"discovered keys with support {keys_with_support} below required minimum {args.min_unique_keys}"
        )

    missing_core_globally = [
        key
        for key in core_keys
        if not any(row["key"] == key and int(row["supportCount"]) > 0 for row in rows_out)
    ]
    if missing_core_globally:
        return fail(
            "core keys missing from registry support: " + ", ".join(sorted(missing_core_globally))
        )

    fit_rows_sorted = sorted(file_fit_rows, key=lambda item: str(item["file"]))
    missing_freq_map: dict[str, int] = {key: 0 for key in core_keys}
    presence_fit_counts = {
        "fully_fit": 0,
        "near_fit": 0,
        "partial_fit": 0,
        "requires_contract_expansion": 0,
    }
    expressive_fit_counts = {
        "fully_fit": 0,
        "near_fit": 0,
        "partial_fit": 0,
        "requires_contract_expansion": 0,
    }
    advanced_missing_freq_map: dict[str, int] = {}
    formation_summary_map: dict[str, dict[str, Any]] = {}
    context_specificity_gap_files = 0
    missing_total = 0
    expressive_gap_total = 0
    for row in fit_rows_sorted:
        missing_total += int(row["missingCoreCount"])
        expressive_gap_total += int(row["expressiveGapCount"])
        if bool(row.get("contextSpecificityGap")):
            context_specificity_gap_files += 1
        presence_fit_class = str(row.get("contractPresenceFitClass", ""))
        expressive_fit_class = str(row.get("expressiveFitClass", ""))
        if presence_fit_class in presence_fit_counts:
            presence_fit_counts[presence_fit_class] += 1
        if expressive_fit_class in expressive_fit_counts:
            expressive_fit_counts[expressive_fit_class] += 1
        for key in row["missingCoreKeys"]:
            missing_freq_map[key] = int(missing_freq_map.get(key, 0)) + 1
        for key in row.get("missingAdvancedKeys", []):
            advanced_missing_freq_map[key] = int(advanced_missing_freq_map.get(key, 0)) + 1

        formation_kind = str(row.get("formationKind") or "unknown")
        fsum = formation_summary_map.get(formation_kind)
        if fsum is None:
            fsum = {
                "formationKind": formation_kind,
                "fileCount": 0,
                "contextSpecificityGapFiles": 0,
                "sumExpressiveGapCount": 0,
                "filesRequiringContractExpansion": 0,
                "requiredAdvancedKeysUnion": set(),
                "missingAdvancedByKey": {},
            }
            formation_summary_map[formation_kind] = fsum
        fsum["fileCount"] = int(fsum["fileCount"]) + 1
        if bool(row.get("contextSpecificityGap")):
            fsum["contextSpecificityGapFiles"] = int(fsum["contextSpecificityGapFiles"]) + 1
        fsum["sumExpressiveGapCount"] = int(fsum["sumExpressiveGapCount"]) + int(
            row.get("expressiveGapCount", 0)
        )
        if expressive_fit_class == "requires_contract_expansion":
            fsum["filesRequiringContractExpansion"] = int(fsum["filesRequiringContractExpansion"]) + 1
        for key in row.get("requiredAdvancedKeys", []):
            fsum["requiredAdvancedKeysUnion"].add(str(key))
        for key in row.get("missingAdvancedKeys", []):
            mcounts = fsum["missingAdvancedByKey"]
            mcounts[str(key)] = int(mcounts.get(str(key), 0)) + 1

    missing_core_frequency = sorted(
        [{"key": key, "missingFileCount": int(count)} for key, count in missing_freq_map.items()],
        key=lambda item: (-int(item["missingFileCount"]), str(item["key"])),
    )
    advanced_missing_frequency = sorted(
        [{"key": key, "missingFileCount": int(count)} for key, count in advanced_missing_freq_map.items()],
        key=lambda item: (-int(item["missingFileCount"]), str(item["key"])),
    )

    formation_summary: list[dict[str, Any]] = []
    for kind in sorted(formation_summary_map.keys()):
        row = formation_summary_map[kind]
        file_count = int(row["fileCount"])
        missing_advanced_by_key = sorted(
            [
                {"key": key, "missingFileCount": int(count)}
                for key, count in row["missingAdvancedByKey"].items()
            ],
            key=lambda item: (-int(item["missingFileCount"]), str(item["key"])),
        )
        formation_summary.append(
            {
                "formationKind": kind,
                "fileCount": file_count,
                "contextSpecificityGapFiles": int(row["contextSpecificityGapFiles"]),
                "filesRequiringContractExpansion": int(row["filesRequiringContractExpansion"]),
                "averageExpressiveGapCount": round(
                    float(int(row["sumExpressiveGapCount"])) / float(file_count), 4
                )
                if file_count > 0
                else 0.0,
                "requiredAdvancedKeys": sorted(list(row["requiredAdvancedKeysUnion"])),
                "missingAdvancedByKey": missing_advanced_by_key,
            }
        )

    key_rows_by_key = {str(row["key"]): row for row in rows_out}
    context_key_rows = [key_rows_by_key.get(key, {}) for key in CONTEXT_SPECIFIC_KEYS]
    context_specificity_summary = {
        "contextKeys": CONTEXT_SPECIFIC_KEYS,
        "filesWithContextSpecificityGap": context_specificity_gap_files,
        "filesWithContextSpecificity": len(files) - context_specificity_gap_files,
        "keySpecificity": [
            {
                "key": str(row.get("key") or key),
                "supportRatio": float(row.get("supportRatio") or 0.0),
                "nonPlaceholderRatio": float(row.get("nonPlaceholderRatio") or 0.0),
            }
            for key, row in zip(CONTEXT_SPECIFIC_KEYS, context_key_rows)
        ],
    }

    contract_expansion_priorities: list[dict[str, Any]] = []
    for row in rows_out:
        tier, rationale, action = priority_for_row(row)
        if not tier:
            continue
        support_ratio = float(row["supportRatio"])
        contract_expansion_priorities.append(
            {
                "tier": tier,
                "key": row["key"],
                "group": row["group"],
                "supportRatio": support_ratio,
                "gapRatio": round(1.0 - support_ratio, 4),
                "nonPlaceholderRatio": float(row.get("nonPlaceholderRatio") or 0.0),
                "rationale": rationale,
                "recommendedAction": action,
            }
        )
    contract_expansion_priorities.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(str(item.get("tier", "")), 99),
            -float(item.get("gapRatio", 0.0)),
            str(item.get("key", "")),
        )
    )

    registry_report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputDir": input_dir.as_posix(),
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "uniqueKeysConfigured": len(PARAMETER_SPECS),
            "uniqueKeysWithSupport": keys_with_support,
            "coreKeyCount": len(core_keys),
            "coreKeysWithSupport": len(core_keys) - len(missing_core_globally),
            "keysWithEvidence": keys_with_evidence,
        },
        "coreKeys": core_keys,
        "rows": rows_out,
    }

    fit_report = {
        "schemaVersion": "1",
        "label": "m13-fdml-fit-analysis",
        "inputDir": input_dir.as_posix(),
        "fitModels": {
            "contractPresence": {
                "fully_fit": "missingCoreCount == 0",
                "near_fit": "missingCoreCount <= 2",
                "partial_fit": "missingCoreCount <= 5",
                "requires_contract_expansion": "missingCoreCount > 5",
            },
            "expressiveCoverage": {
                "gapFormula": "missingCoreCount + missingAdvancedKeysCount + contextSpecificityGapFlag",
                "fully_fit": "expressiveGapCount == 0",
                "near_fit": "expressiveGapCount <= 1",
                "partial_fit": "expressiveGapCount <= 2",
                "requires_contract_expansion": "expressiveGapCount > 2",
            },
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "coreKeyCount": len(core_keys),
            "filesAllCorePresent": int(presence_fit_counts["fully_fit"]),
            "filesNearFit": int(presence_fit_counts["near_fit"]),
            "filesPartialFit": int(presence_fit_counts["partial_fit"]),
            "filesRequiringContractExpansion": int(
                presence_fit_counts["requires_contract_expansion"]
            ),
            "averageMissingCorePerFile": round(float(missing_total) / float(len(files)), 4),
            "filesExpressiveFullyFit": int(expressive_fit_counts["fully_fit"]),
            "filesExpressiveNearFit": int(expressive_fit_counts["near_fit"]),
            "filesExpressivePartialFit": int(expressive_fit_counts["partial_fit"]),
            "filesExpressiveRequiringContractExpansion": int(
                expressive_fit_counts["requires_contract_expansion"]
            ),
            "averageExpressiveGapPerFile": round(float(expressive_gap_total) / float(len(files)), 4),
        },
        "contextSpecificity": context_specificity_summary,
        "missingCoreFrequency": missing_core_frequency,
        "advancedMissingFrequency": advanced_missing_frequency,
        "formationSummary": formation_summary,
        "contractExpansionPriorities": contract_expansion_priorities,
        "rows": fit_rows_sorted,
    }

    write_json(report_out, registry_report)
    write_json(fit_report_out, fit_report)

    print(
        "M13 PARAMETER REGISTRY DONE "
        f"files={len(files)} keys_with_support={keys_with_support}/{len(PARAMETER_SPECS)} "
        f"presence_fully_fit={presence_fit_counts['fully_fit']} "
        f"expressive_requires_expansion={expressive_fit_counts['requires_contract_expansion']}",
        file=sys.stderr,
    )
    print(f"Created: {report_out}")
    print(f"Created: {fit_report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

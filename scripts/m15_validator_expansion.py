#!/usr/bin/env python3
"""Expanded full-corpus validator stack derived from M15 discovery candidates."""

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
        description="Run expanded M15 validator stack from discovery candidates and publish failure taxonomy."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m14_context_specificity/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--candidate-report",
        default="out/m15_validator_candidates.json",
        help="path to M15 validator candidate report",
    )
    ap.add_argument(
        "--report-out",
        default="out/m15_validator_expansion_report.json",
        help="output path for validator expansion report",
    )
    ap.add_argument(
        "--label",
        default="m15-validator-expansion",
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
        default=15,
        help="minimum expanded rule count required",
    )
    ap.add_argument(
        "--max-rules-with-no-applicability",
        type=int,
        default=1,
        help="maximum allowed count of rules with zero applicable files",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m15_validator_expansion.py: {msg}", file=sys.stderr)
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


def parse_positive_float(text: str) -> float | None:
    token = str(text or "").strip()
    if not token:
        return None
    try:
        value = float(token)
    except Exception:
        return None
    if value <= 0.0:
        return None
    return value


def parse_meter_numerator(text: str) -> int | None:
    token = str(text or "").strip()
    if not token:
        return None
    if "/" not in token:
        return None
    left, _, _ = token.partition("/")
    left = left.strip()
    if not left:
        return None
    try:
        num = int(left)
    except Exception:
        return None
    return num if num > 0 else None


def is_meter_aligned(beat_total: float, meter_num: int) -> bool:
    if meter_num <= 0:
        return False
    ratio = beat_total / float(meter_num)
    # Allow quarter-phrase granularity for folk patterns (e.g., 1 beat in 4/4 => 0.25).
    scaled = ratio * 4.0
    nearest = round(scaled)
    return abs(scaled - float(nearest)) <= 1e-6


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
        type_genre = attr(root.find("./meta/type"), "genre")
        type_style = attr(root.find("./meta/type"), "style")
        meter_value = attr(root.find("./meta/meter"), "value")
        meter_num = parse_meter_numerator(meter_value)
        tempo_bpm = attr(root.find("./meta/tempo"), "bpm")
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
        step_total = 0
        steps_missing_count = 0
        steps_missing_direction = 0
        steps_missing_facing = 0
        steps_non_positive_beats = 0
        step_beats_seen = 0
        figure_beat_totals: list[float] = []

        for figure in root.findall(".//figure"):
            figure_sum = 0.0
            figure_has_steps = False
            for step in figure.findall("./step"):
                step_total += 1
                figure_has_steps = True
                action = attr(step, "action").lower()
                if ("turn" in action) or ("spin" in action) or ("pivot" in action):
                    has_turn_action = True

                if not attr(step, "count"):
                    steps_missing_count += 1
                direction = attr(step, "direction")
                if (not direction) or is_placeholder_value(direction):
                    steps_missing_direction += 1
                facing = attr(step, "facing")
                if (not facing) or is_placeholder_value(facing):
                    steps_missing_facing += 1

                beats = parse_positive_float(attr(step, "beats"))
                if beats is None:
                    steps_non_positive_beats += 1
                else:
                    step_beats_seen += 1
                    figure_sum += beats
            if figure_has_steps:
                figure_beat_totals.append(figure_sum)

        out[file_path.resolve().as_posix()] = {
            "version": version,
            "formationKind": formation_kind,
            "womanSide": woman_side,
            "originCountry": origin_country,
            "originRegion": origin_region,
            "typeGenre": type_genre,
            "typeStyle": type_style,
            "meterValue": meter_value,
            "meterNumerator": meter_num,
            "tempoBpm": tempo_bpm,
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
            "stepTotal": step_total,
            "stepsMissingCount": steps_missing_count,
            "stepsMissingDirection": steps_missing_direction,
            "stepsMissingFacing": steps_missing_facing,
            "stepsNonPositiveBeats": steps_non_positive_beats,
            "stepBeatsSeen": step_beats_seen,
            "figureBeatTotals": figure_beat_totals,
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


def evaluate_rule_type_genre_required(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    genre = str(meta.get("typeGenre") or "")
    if not genre:
        return True, False, ["missing_type_genre"]
    if is_placeholder_value(genre):
        return True, False, ["placeholder_type_genre"]
    return True, True, []


def evaluate_rule_type_style_required(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    style = str(meta.get("typeStyle") or "")
    if not style:
        return True, False, ["missing_type_style"]
    if is_placeholder_value(style):
        return True, False, ["placeholder_type_style"]
    return True, True, []


def evaluate_rule_require_formation_kind_for_v12(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    version = str(meta.get("version") or "")
    applicable = version.startswith("1.2")
    if not applicable:
        return False, True, []
    kind = str(meta.get("formationKind") or "")
    if not kind:
        return True, False, ["missing_formation_kind_v12"]
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


def evaluate_rule_direction_requires_frame_compatibility(
    meta: dict[str, Any],
) -> tuple[bool, bool, list[str]]:
    applicable = bool(meta.get("hasPrimitiveDir"))
    if not applicable:
        return False, True, []
    return True, bool(meta.get("hasPrimitiveFrame")), ["direction_without_frame"]


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


def evaluate_rule_couple_relpos_consistency(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = str(meta.get("formationKind") or "") == "couple" and bool(
        meta.get("hasRelposPrimitive")
    )
    if not applicable:
        return False, True, []
    ok = bool(meta.get("hasRelposRelation")) and bool(meta.get("hasPairRelationship")) and (
        str(meta.get("womanSide") or "") in {"left", "right"}
    )
    return True, ok, ["couple_relpos_inconsistent"]


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


def evaluate_rule_step_beats_positive(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = int(meta.get("stepTotal", 0)) > 0
    if not applicable:
        return False, True, []
    return True, int(meta.get("stepsNonPositiveBeats", 0)) == 0, ["non_positive_step_beats"]


def evaluate_rule_step_count_required(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = int(meta.get("stepTotal", 0)) > 0
    if not applicable:
        return False, True, []
    return True, int(meta.get("stepsMissingCount", 0)) == 0, ["missing_step_count"]


def evaluate_rule_step_direction_required(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = int(meta.get("stepTotal", 0)) > 0
    if not applicable:
        return False, True, []
    return True, int(meta.get("stepsMissingDirection", 0)) == 0, ["missing_step_direction"]


def evaluate_rule_step_facing_required(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = int(meta.get("stepTotal", 0)) > 0
    if not applicable:
        return False, True, []
    return True, int(meta.get("stepsMissingFacing", 0)) == 0, ["missing_step_facing"]


def evaluate_rule_step_beats_align_to_meter(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    applicable = int(meta.get("stepTotal", 0)) > 0
    if not applicable:
        return False, True, []
    meter_num = meta.get("meterNumerator")
    if not isinstance(meter_num, int) or meter_num <= 0:
        return True, False, ["missing_or_invalid_meter_value"]
    totals = [float(x) for x in as_list(meta.get("figureBeatTotals")) if float(x) > 0.0]
    if not totals:
        return True, False, ["missing_figure_beat_totals"]
    for value in totals:
        if not is_meter_aligned(value, meter_num):
            return True, False, ["misaligned_figure_beat_total"]
    return True, True, []


def evaluate_rule_tempo_bpm_required(meta: dict[str, Any]) -> tuple[bool, bool, list[str]]:
    bpm = str(meta.get("tempoBpm") or "")
    if not bpm:
        return True, False, ["missing_tempo_bpm"]
    try:
        ok = int(bpm) > 0
    except Exception:
        ok = False
    return True, ok, ["invalid_tempo_bpm"]


RULE_SPECS: list[dict[str, Any]] = [
    {
        "key": "rule:origin_country_specific_non_placeholder",
        "name": "origin_country_specific_non_placeholder",
        "description": "Origin country must be present and non-placeholder.",
        "candidateKeys": ["rule:origin_country_required"],
        "evaluate": evaluate_rule_origin_country_specific,
    },
    {
        "key": "rule:origin_region_specific_non_placeholder",
        "name": "origin_region_specific_non_placeholder",
        "description": "Origin region must be present and non-placeholder.",
        "candidateKeys": ["rule:origin_region_required"],
        "evaluate": evaluate_rule_origin_region_specific,
    },
    {
        "key": "rule:type_genre_required",
        "name": "type_genre_required",
        "description": "Type genre metadata must be present and non-placeholder.",
        "candidateKeys": ["rule:type_genre_required"],
        "evaluate": evaluate_rule_type_genre_required,
    },
    {
        "key": "rule:type_style_required",
        "name": "type_style_required",
        "description": "Type style metadata must be present and non-placeholder.",
        "candidateKeys": ["rule:type_style_required"],
        "evaluate": evaluate_rule_type_style_required,
    },
    {
        "key": "rule:require_formation_kind_for_v12",
        "name": "require_formation_kind_for_v12",
        "description": "FDML v1.2 files require explicit formation kind.",
        "candidateKeys": ["rule:require_formation_kind_for_v12"],
        "evaluate": evaluate_rule_require_formation_kind_for_v12,
    },
    {
        "key": "rule:line_like_requires_primitive_dir",
        "name": "line_like_requires_primitive_dir",
        "description": "Line and two-lines-facing formations require primitive direction semantics.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_line_like_requires_dir,
    },
    {
        "key": "rule:line_like_requires_primitive_frame",
        "name": "line_like_requires_primitive_frame",
        "description": "Line and two-lines-facing formations require primitive frame semantics.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_line_like_requires_frame,
    },
    {
        "key": "rule:direction_requires_frame_compatibility",
        "name": "direction_requires_frame_compatibility",
        "description": "Directional primitives require compatible frame declarations.",
        "candidateKeys": ["rule:direction_requires_frame_compatibility"],
        "evaluate": evaluate_rule_direction_requires_frame_compatibility,
    },
    {
        "key": "rule:circle_requires_primitive_dir",
        "name": "circle_requires_primitive_dir",
        "description": "Circle formations require primitive direction semantics.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_circle_requires_dir,
    },
    {
        "key": "rule:circle_requires_preserve_order_marker",
        "name": "circle_requires_preserve_order_marker",
        "description": "Circle formations require preserve-order markers for topology constraints.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_circle_requires_preserve_order,
    },
    {
        "key": "rule:rotation_cues_require_axis",
        "name": "rotation_cues_require_axis",
        "description": "Rotation cues require explicit primitive axis semantics.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_rotation_requires_axis,
    },
    {
        "key": "rule:couple_requires_woman_side",
        "name": "couple_requires_woman_side",
        "description": "Couple formations require woman-side orientation semantics.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_couple_requires_woman_side,
    },
    {
        "key": "rule:couple_requires_pair_relationship",
        "name": "couple_requires_pair_relationship",
        "description": "Couple formations require pair relationship metadata.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_couple_requires_pair_relationship,
    },
    {
        "key": "rule:couple_relpos_requires_relation",
        "name": "couple_relpos_requires_relation",
        "description": "Couple relpos primitives require relation values.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_couple_relpos_requires_relation,
    },
    {
        "key": "rule:couple_relpos_consistency",
        "name": "couple_relpos_consistency",
        "description": "Couple relpos declarations require consistent relation and pair context.",
        "candidateKeys": ["rule:couple_relpos_consistency"],
        "evaluate": evaluate_rule_couple_relpos_consistency,
    },
    {
        "key": "rule:formation_requires_dancers_count",
        "name": "formation_requires_dancers_count",
        "description": "Non-couple formations require dancer count metadata.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_formation_requires_dancers_count,
    },
    {
        "key": "rule:couple_requires_hold_kind",
        "name": "couple_requires_hold_kind",
        "description": "Couple formations require hold/contact kind metadata.",
        "candidateKeys": [],
        "evaluate": evaluate_rule_couple_requires_hold_kind,
    },
    {
        "key": "rule:step_beats_positive",
        "name": "step_beats_positive",
        "description": "Each step must declare a positive beats value.",
        "candidateKeys": ["rule:step_beats_positive"],
        "evaluate": evaluate_rule_step_beats_positive,
    },
    {
        "key": "rule:step_count_required",
        "name": "step_count_required",
        "description": "Each step must declare count metadata.",
        "candidateKeys": ["rule:step_count_required"],
        "evaluate": evaluate_rule_step_count_required,
    },
    {
        "key": "rule:step_direction_required",
        "name": "step_direction_required",
        "description": "Each step must include non-placeholder direction semantics.",
        "candidateKeys": ["rule:step_direction_required"],
        "evaluate": evaluate_rule_step_direction_required,
    },
    {
        "key": "rule:step_facing_required",
        "name": "step_facing_required",
        "description": "Each step must include non-placeholder facing semantics.",
        "candidateKeys": ["rule:step_facing_required"],
        "evaluate": evaluate_rule_step_facing_required,
    },
    {
        "key": "rule:step_beats_align_to_meter",
        "name": "step_beats_align_to_meter",
        "description": "Figure beat totals must align with declared meter granularity.",
        "candidateKeys": ["rule:step_beats_align_to_meter"],
        "evaluate": evaluate_rule_step_beats_align_to_meter,
    },
    {
        "key": "rule:tempo_bpm_required",
        "name": "tempo_bpm_required",
        "description": "Tempo BPM must be present and positive.",
        "candidateKeys": ["rule:tempo_bpm_required"],
        "evaluate": evaluate_rule_tempo_bpm_required,
    },
]


# Discovery-derived mapping from candidate keys to implemented rule keys.
CANDIDATE_TO_RULE_KEYS: dict[str, list[str]] = {
    "rule:couple_relpos_consistency": [
        "rule:couple_relpos_consistency",
        "rule:couple_relpos_requires_relation",
        "rule:couple_requires_pair_relationship",
        "rule:couple_requires_woman_side",
    ],
    "rule:direction_requires_frame_compatibility": [
        "rule:direction_requires_frame_compatibility",
        "rule:line_like_requires_primitive_frame",
        "rule:line_like_requires_primitive_dir",
    ],
    "rule:origin_country_required": ["rule:origin_country_specific_non_placeholder"],
    "rule:origin_region_required": ["rule:origin_region_specific_non_placeholder"],
    "rule:require_formation_kind_for_v12": ["rule:require_formation_kind_for_v12"],
    "rule:step_beats_align_to_meter": ["rule:step_beats_align_to_meter"],
    "rule:step_beats_positive": ["rule:step_beats_positive"],
    "rule:step_count_required": ["rule:step_count_required"],
    "rule:step_direction_required": ["rule:step_direction_required"],
    "rule:step_facing_required": ["rule:step_facing_required"],
    "rule:tempo_bpm_required": ["rule:tempo_bpm_required"],
    "rule:type_genre_required": ["rule:type_genre_required"],
    "rule:type_style_required": ["rule:type_style_required"],
}


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
        input_dir = repo_root / input_dir
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")

    candidate_path = Path(args.candidate_report)
    if not candidate_path.is_absolute():
        candidate_path = repo_root / candidate_path
    candidate_path = candidate_path.resolve()
    if not candidate_path.is_file():
        return fail(f"candidate report not found: {candidate_path}")

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

    candidate_payload = load_json(candidate_path)
    candidate_rows = [as_dict(x) for x in as_list(candidate_payload.get("rows"))]
    candidate_keys = sorted({str(row.get("key") or "") for row in candidate_rows if row.get("key")})

    meta_map = collect_file_meta(files)
    file_abs_list = [canonical_path(f, repo_root) for f in files]
    file_display = {canonical_path(f, repo_root): display_path(f, repo_root) for f in files}

    if len(RULE_SPECS) < args.min_rules:
        return fail(f"expanded rule count {len(RULE_SPECS)} is below --min-rules {args.min_rules}")

    rule_key_set = {str(spec["key"]) for spec in RULE_SPECS}
    mapped_candidate_keys: set[str] = set()
    missing_candidate_keys: list[str] = []
    for ckey in candidate_keys:
        mapped_rules = CANDIDATE_TO_RULE_KEYS.get(ckey, [])
        if mapped_rules and all(rule_key in rule_key_set for rule_key in mapped_rules):
            mapped_candidate_keys.add(ckey)
        else:
            missing_candidate_keys.append(ckey)

    rule_rows: list[dict[str, Any]] = []
    file_failures: dict[str, list[str]] = {}
    failure_code_counts_global: dict[str, int] = {}
    total_evaluations = 0
    total_failures = 0

    for spec in RULE_SPECS:
        key = str(spec["key"])
        name = str(spec["name"])
        description = str(spec["description"])
        derived_candidates = [str(x) for x in spec.get("candidateKeys", [])]
        evaluator: RuleFn = spec["evaluate"]

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
        rule_rows.append(
            {
                "key": key,
                "name": name,
                "description": description,
                "derivedFromCandidateKeys": derived_candidates,
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

    candidate_coverage_ratio = (
        1.0
        if not candidate_keys
        else float(len(mapped_candidate_keys)) / float(len(candidate_keys))
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
            "ok": len(rules_with_no_applicability) <= args.max_rules_with_no_applicability,
            "detail": (
                f"rules_with_no_applicability={len(rules_with_no_applicability)} "
                f"max={args.max_rules_with_no_applicability}"
            ),
        },
        {
            "id": "priority_key_mapping_complete",
            "ok": len(missing_candidate_keys) == 0,
            "detail": (
                f"candidate_keys={len(candidate_keys)} "
                f"mapped={len(mapped_candidate_keys)} missing={len(missing_candidate_keys)}"
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
            "candidateReport": display_path(candidate_path, repo_root),
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "candidateKeys": len(candidate_keys),
            "mappedCandidateKeys": len(mapped_candidate_keys),
            "ruleCount": len(rule_rows),
            "ruleEvaluations": total_evaluations,
            "ruleFailures": total_failures,
            "filesWithAnyRuleFailure": len(file_failures),
            "failureTaxonomyCodeCount": len(failure_code_counts_global),
        },
        "priorityCoverage": {
            "targetedKeys": candidate_keys,
            "mappedKeys": sorted(mapped_candidate_keys),
            "missingKeys": sorted(missing_candidate_keys),
            "coverageRatio": round(clamp01(candidate_coverage_ratio), 6),
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
        f"M15 VALIDATOR EXPANSION {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} rules={len(rule_rows)} "
        f"failures={total_failures} report={display_path(report_out, repo_root)}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

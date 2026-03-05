#!/usr/bin/env python3
"""Offline, deterministic M10 multi-pass discovery runner (no API usage)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


CHECKLIST_DIMENSIONS = [
    "movement_path_pattern",
    "footwork_support_transfer",
    "turn_spin_rotation",
    "hold_contact_pattern",
    "partner_relative_position",
    "formation_topology",
    "role_assignment",
    "direction_orientation",
    "progression_order_change",
    "timing_phrase_alignment",
    "rhythm_accent_grouping",
    "gesture_styling_posture",
    "performance_dynamics",
    "cultural_context_notes",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run deterministic multi-pass corpus discovery without external API calls."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m9_full_description_uplift/run1",
        help="directory containing promoted .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m10_discovery/run1",
        help="output directory for pass artifacts",
    )
    ap.add_argument(
        "--report-out",
        default="out/m10_discovery/run1/discovery_report.json",
        help="output path for discovery report",
    )
    ap.add_argument(
        "--ontology-out",
        default="out/m10_ontology_candidates.json",
        help="output path for ontology candidate report",
    )
    ap.add_argument(
        "--validator-out",
        default="out/m10_validator_candidates.json",
        help="output path for validator candidate report",
    )
    ap.add_argument(
        "--coverage-gaps-out",
        default="out/m10_coverage_gaps.json",
        help="output path for coverage-gaps report",
    )
    ap.add_argument(
        "--passes",
        type=int,
        default=3,
        help="number of deterministic passes to run (>=3 recommended)",
    )
    ap.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="optional max files to process (0 = all files)",
    )
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="minimum confidence retained in promoted candidate rows",
    )
    ap.add_argument(
        "--label",
        default="m10-multi-pass-discovery-offline",
        help="report label",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m10_multi_pass_discovery_offline.py: {msg}", file=sys.stderr)
    return 2


def clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def norm_key(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower())
    return s.strip("_")


def text_of(el: ET.Element | None) -> str:
    if el is None:
        return ""
    if el.text and el.text.strip():
        return el.text.strip()
    return ""


def pick_files(input_dir: Path, max_files: int) -> list[Path]:
    files = sorted(input_dir.glob("*.fdml.xml"))
    if max_files > 0:
        files = files[:max_files]
    return files


def build_evidence_lines(fdml_file: Path) -> tuple[str, dict[str, tuple[int, int, str]]]:
    root = ET.parse(fdml_file).getroot()
    lines: list[str] = []

    def add(line: str) -> None:
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)

    add(f"file={fdml_file.name}")
    add(f"version={root.get('version', '').strip() or 'unknown'}")

    title = text_of(root.find("./meta/title"))
    if title:
        add(f"meta.title={title}")
    dance = root.find("./meta/dance")
    if dance is not None and dance.get("name"):
        add(f"meta.dance.name={dance.get('name','').strip()}")

    origin = root.find("./meta/origin")
    if origin is not None:
        country = (origin.get("country") or "").strip()
        region = (origin.get("region") or "").strip()
        if country:
            add(f"meta.origin.country={country}")
        if region:
            add(f"meta.origin.region={region}")

    typ = root.find("./meta/type")
    if typ is not None:
        genre = (typ.get("genre") or "").strip()
        style = (typ.get("style") or "").strip()
        if genre:
            add(f"meta.type.genre={genre}")
        if style:
            add(f"meta.type.style={style}")

    meter = root.find("./meta/meter")
    if meter is not None:
        value = (meter.get("value") or "").strip()
        rhythm = (meter.get("rhythmPattern") or "").strip()
        if value:
            add(f"meta.meter.value={value}")
        if rhythm:
            add(f"meta.meter.rhythmPattern={rhythm}")

    tempo = root.find("./meta/tempo")
    if tempo is not None and tempo.get("bpm"):
        add(f"meta.tempo.bpm={tempo.get('bpm','').strip()}")

    mgeo_form = root.find("./meta/geometry/formation")
    if mgeo_form is not None:
        kind = (mgeo_form.get("kind") or "").strip()
        woman_side = (mgeo_form.get("womanSide") or "").strip()
        if kind:
            add(f"meta.geometry.formation.kind={kind}")
        if woman_side:
            add(f"meta.geometry.formation.womanSide={woman_side}")

    hold = root.find("./meta/geometry/hold")
    if hold is not None and hold.get("kind"):
        add(f"meta.geometry.hold.kind={hold.get('kind','').strip()}")

    dancers = root.find("./meta/geometry/dancers")
    if dancers is not None and dancers.get("count"):
        add(f"meta.geometry.dancers.count={dancers.get('count','').strip()}")

    roles = [
        (r.get("id") or "").strip()
        for r in root.findall("./meta/geometry/roles/role")
        if (r.get("id") or "").strip()
    ]
    if roles:
        add(f"meta.geometry.roles={','.join(roles)}")

    circle_order = root.find("./body/geometry/circle/order")
    if circle_order is not None:
        role = (circle_order.get("role") or "").strip()
        if role:
            add(f"body.geometry.circle.order.role={role}")
        slots = [
            (slot.get("who") or "").strip()
            for slot in circle_order.findall("./slot")
            if (slot.get("who") or "").strip()
        ]
        if slots:
            add(f"body.geometry.circle.order.slots={','.join(slots)}")

    for line in root.findall("./body/geometry/twoLines/line"):
        lid = (line.get("id") or "").strip()
        role = (line.get("role") or "").strip()
        add(f"body.geometry.twoLines.line id={lid} role={role}")
        slots = [
            (slot.get("who") or "").strip()
            for slot in line.findall("./order/slot")
            if (slot.get("who") or "").strip()
        ]
        if slots:
            add(f"body.geometry.twoLines.line.order {lid}={','.join(slots)}")

    for facing in root.findall("./body/geometry/twoLines/facing"):
        a = (facing.get("a") or "").strip()
        b = (facing.get("b") or "").strip()
        if a and b:
            add(f"body.geometry.twoLines.facing a={a} b={b}")

    for line in root.findall("./body/geometry/line"):
        lid = (line.get("id") or "").strip()
        if lid:
            add(f"body.geometry.line.id={lid}")
        for order in line.findall("./order"):
            phase = (order.get("phase") or "").strip()
            slots = [
                (slot.get("who") or "").strip()
                for slot in order.findall("./slot")
                if (slot.get("who") or "").strip()
            ]
            if slots:
                add(f"body.geometry.line.order phase={phase} slots={','.join(slots)}")

    for pair in root.findall("./body/geometry/couples/pair"):
        a = (pair.get("a") or "").strip()
        b = (pair.get("b") or "").strip()
        rel = (pair.get("relationship") or "").strip()
        if a and b:
            add(f"body.geometry.couples.pair a={a} b={b} relationship={rel}")

    for section in root.findall("./body/section"):
        stype = (section.get("type") or "").strip()
        sid = (section.get("id") or "").strip()
        section_texts: list[str] = []
        if section.text and section.text.strip():
            section_texts.append(section.text.strip())
        for p in section.findall("./p"):
            if p.text and p.text.strip():
                section_texts.append(p.text.strip())
        if section_texts:
            add(f"body.section type={stype} id={sid} text={' '.join(section_texts)}")

    for fig in root.findall(".//figure"):
        fig_id = (fig.get("id") or "").strip()
        fig_name = (fig.get("name") or "").strip()
        fig_form = (fig.get("formation") or "").strip()
        add(f"figure id={fig_id} name={fig_name} formation={fig_form}")
        for step in fig.findall("./step"):
            who = (step.get("who") or "").strip()
            action = (step.get("action") or "").strip()
            beats = (step.get("beats") or "").strip()
            direction = (step.get("direction") or "").strip()
            facing = (step.get("facing") or "").strip()
            count = (step.get("count") or "").strip()
            start_foot = (step.get("startFoot") or "").strip()
            end_foot = (step.get("endFoot") or "").strip()
            add(
                "step "
                f"figure={fig_id} who={who} beats={beats} count={count} "
                f"startFoot={start_foot} endFoot={end_foot} direction={direction} "
                f"facing={facing} action={action}"
            )
            for prim in step.findall("./geo/primitive"):
                kind = (prim.get("kind") or "").strip()
                p_who = (prim.get("who") or "").strip()
                p_a = (prim.get("a") or "").strip()
                p_b = (prim.get("b") or "").strip()
                p_frame = (prim.get("frame") or "").strip()
                p_dir = (prim.get("dir") or "").strip()
                p_axis = (prim.get("axis") or "").strip()
                p_rel = (prim.get("relation") or "").strip()
                p_delta = (prim.get("delta") or "").strip()
                p_pres = (prim.get("preserveOrder") or "").strip()
                add(
                    "primitive "
                    f"figure={fig_id} kind={kind} who={p_who} a={p_a} b={p_b} frame={p_frame} "
                    f"dir={p_dir} axis={p_axis} relation={p_rel} delta={p_delta} preserveOrder={p_pres}"
                )

    prefixed = [f"L{i:04d}: {line}" for i, line in enumerate(lines, start=1)]
    source_text = "\n".join(prefixed)
    line_map: dict[str, tuple[int, int, str]] = {}
    cursor = 0
    for full in prefixed:
        lid, _, text = full.partition(": ")
        start = source_text.find(full, cursor)
        if start < 0:
            start = source_text.find(full)
        end = start + len(full)
        line_map[lid] = (start, end, text)
        cursor = end
    return source_text, line_map


def line_ids_for_patterns(
    line_map: dict[str, tuple[int, int, str]], patterns: list[str], limit: int = 2
) -> list[str]:
    out: list[str] = []
    comp = [re.compile(p, re.IGNORECASE) for p in patterns]
    for lid in sorted(line_map.keys()):
        text = line_map[lid][2]
        for rx in comp:
            if rx.search(text):
                out.append(lid)
                break
        if len(out) >= limit:
            break
    return out


def evidence_from_line_ids(
    line_ids: list[str], line_map: dict[str, tuple[int, int, str]]
) -> dict[str, Any]:
    valid = [lid for lid in line_ids if lid in line_map]
    if not valid:
        return {"text": "", "span": {"start": -1, "end": -1}, "lineIds": []}
    lid = valid[0]
    start, end, text = line_map[lid]
    return {"text": text, "span": {"start": start, "end": end}, "lineIds": valid}


def build_checklist(line_map: dict[str, tuple[int, int, str]]) -> list[dict[str, Any]]:
    rules: dict[str, list[str]] = {
        "movement_path_pattern": [r"\bprimitive\b.*\bkind=(move|progress|pass|weave|swapPlaces|approach|retreat)\b", r"\bstep\b.*\baction=.*(travel|step|advance|retreat)\b"],
        "footwork_support_transfer": [r"\bstep\b.*\b(startFoot|endFoot)=\w+", r"\baction=.*\b(foot|heel|toe|weight)\b"],
        "turn_spin_rotation": [r"\bprimitive\b.*\bkind=(turn|twirl)\b", r"\baction=.*\b(turn|spin|pivot)\b"],
        "hold_contact_pattern": [r"\bmeta\.geometry\.hold\.kind=\w+", r"\baction=.*\b(hold|link|hands|clasp)\b"],
        "partner_relative_position": [r"\bprimitive\b.*\bkind=relpos\b", r"\b(relationship=partners|partner|opposite)\b"],
        "formation_topology": [r"\bmeta\.geometry\.formation\.kind=\w+", r"\bbody\.geometry\.(circle|twoLines|line|couples)\b"],
        "role_assignment": [r"\bmeta\.geometry\.roles=", r"\bstep\b.*\bwho=\w+"],
        "direction_orientation": [r"\bstep\b.*\b(direction|facing)=\w+", r"\bprimitive\b.*\b(dir|frame)=\w+"],
        "progression_order_change": [
            r"\bprimitive\b.*\bkind=(progress|swapPlaces|pass|weave)\b",
            r"\bbody\.geometry\.(line|circle)\.order\b",
            r"\bstep\b.*\bcount=\w+",
        ],
        "timing_phrase_alignment": [r"\bmeta\.meter\.value=", r"\bstep\b.*\bbeats=\d+"],
        "rhythm_accent_grouping": [r"\bmeta\.meter\.rhythmPattern=", r"\baction=.*\b(clap|stomp|accent|beat)\b"],
        "gesture_styling_posture": [r"\bbody\.section\b.*\b(notes|setup)\b", r"\baction=.*\b(arms|posture|sway|gesture)\b"],
        "performance_dynamics": [r"\baction=.*\b(quick|slow|grounded|energetic|gentle|sharp)\b", r"\bbody\.section\b.*\b(style|dynamic)\b"],
        "cultural_context_notes": [r"\bmeta\.origin\.(country|region)=", r"\bmeta\.type\.(genre|style)="],
    }

    checklist: list[dict[str, Any]] = []
    for dim in CHECKLIST_DIMENSIONS:
        line_ids = line_ids_for_patterns(line_map, rules.get(dim, []), limit=2)
        present = bool(line_ids)
        status = "present" if present else "absent"
        confidence = 0.86 if present else 0.72
        rationale = (
            f"detected evidence for {dim}" if present else f"no explicit evidence found for {dim}"
        )
        checklist.append(
            {
                "dimension": dim,
                "status": status,
                "confidence": confidence,
                "rationale": rationale,
                "evidence": evidence_from_line_ids(line_ids, line_map),
            }
        )
    return checklist


def candidate_param(
    key: str,
    name: str,
    group: str,
    description: str,
    file_path: str,
    line_ids: list[str],
    line_map: dict[str, tuple[int, int, str]],
    confidence: float,
) -> dict[str, Any] | None:
    if not line_ids:
        return None
    return {
        "key": key,
        "name": name,
        "group": group,
        "description": description,
        "confidence": clamp01(confidence),
        "file": file_path,
        "evidence": evidence_from_line_ids(line_ids, line_map),
    }


def candidate_rule(
    key: str,
    name: str,
    rule_type: str,
    layer: str,
    description: str,
    file_path: str,
    line_ids: list[str],
    line_map: dict[str, tuple[int, int, str]],
    confidence: float,
) -> dict[str, Any] | None:
    if not line_ids:
        return None
    return {
        "key": key,
        "name": name,
        "ruleType": rule_type,
        "enforceLayer": layer,
        "description": description,
        "confidence": clamp01(confidence),
        "file": file_path,
        "evidence": evidence_from_line_ids(line_ids, line_map),
    }


def extract_candidates(
    fdml_file: Path, line_map: dict[str, tuple[int, int, str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    file_path = fdml_file.as_posix()
    params: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []

    # Parameter candidates.
    form_lines = line_ids_for_patterns(line_map, [r"\bmeta\.geometry\.formation\.kind=(\w+)"])
    if form_lines:
        form_text = line_map[form_lines[0]][2]
        m = re.search(r"formation\.kind=(\w+)", form_text, re.IGNORECASE)
        if m:
            kind = m.group(1).strip().lower()
            item = candidate_param(
                key=f"formation_kind:{kind}",
                name=f"formation_kind_{kind}",
                group="formation",
                description="Formation kind used in choreography metadata.",
                file_path=file_path,
                line_ids=form_lines,
                line_map=line_map,
                confidence=0.9,
            )
            if item:
                params.append(item)

    meter_lines = line_ids_for_patterns(line_map, [r"\bmeta\.meter\.value=([0-9+]+/[0-9]+)"])
    if meter_lines:
        item = candidate_param(
            key="timing:meter_value",
            name="meter_value",
            group="timing",
            description="Meter signature used for step grouping and phrase validation.",
            file_path=file_path,
            line_ids=meter_lines,
            line_map=line_map,
            confidence=0.88,
        )
        if item:
            params.append(item)

    tempo_lines = line_ids_for_patterns(line_map, [r"\bmeta\.tempo\.bpm=\d+"])
    if tempo_lines:
        item = candidate_param(
            key="timing:tempo_bpm",
            name="tempo_bpm",
            group="timing",
            description="Tempo declaration used by timing and dynamics checks.",
            file_path=file_path,
            line_ids=tempo_lines,
            line_map=line_map,
            confidence=0.86,
        )
        if item:
            params.append(item)

    rhythm_lines = line_ids_for_patterns(line_map, [r"\bmeta\.meter\.rhythmPattern="])
    if rhythm_lines:
        item = candidate_param(
            key="timing:rhythm_pattern",
            name="rhythm_pattern",
            group="timing",
            description="Explicit rhythm grouping pattern for additive timing constraints.",
            file_path=file_path,
            line_ids=rhythm_lines,
            line_map=line_map,
            confidence=0.86,
        )
        if item:
            params.append(item)

    origin_country_lines = line_ids_for_patterns(line_map, [r"\bmeta\.origin\.country=\S+"])
    if origin_country_lines:
        item = candidate_param(
            key="context:origin_country",
            name="origin_country",
            group="context",
            description="Country context captured in FDML origin metadata.",
            file_path=file_path,
            line_ids=origin_country_lines,
            line_map=line_map,
            confidence=0.89,
        )
        if item:
            params.append(item)

    origin_region_lines = line_ids_for_patterns(line_map, [r"\bmeta\.origin\.region=\S+"])
    if origin_region_lines:
        item = candidate_param(
            key="context:origin_region",
            name="origin_region",
            group="context",
            description="Regional context captured in FDML origin metadata.",
            file_path=file_path,
            line_ids=origin_region_lines,
            line_map=line_map,
            confidence=0.87,
        )
        if item:
            params.append(item)

    type_genre_lines = line_ids_for_patterns(line_map, [r"\bmeta\.type\.genre=\S+"])
    if type_genre_lines:
        item = candidate_param(
            key="context:type_genre",
            name="type_genre",
            group="context",
            description="Dance genre classification in metadata.",
            file_path=file_path,
            line_ids=type_genre_lines,
            line_map=line_map,
            confidence=0.88,
        )
        if item:
            params.append(item)

    type_style_lines = line_ids_for_patterns(line_map, [r"\bmeta\.type\.style=\S+"])
    if type_style_lines:
        item = candidate_param(
            key="context:type_style",
            name="type_style",
            group="context",
            description="Dance style classification in metadata.",
            file_path=file_path,
            line_ids=type_style_lines,
            line_map=line_map,
            confidence=0.88,
        )
        if item:
            params.append(item)

    role_lines = line_ids_for_patterns(line_map, [r"\bmeta\.geometry\.roles="])
    if role_lines:
        item = candidate_param(
            key="roles:role_ids",
            name="role_ids",
            group="roles",
            description="Declared dance role inventory used by steps and primitives.",
            file_path=file_path,
            line_ids=role_lines,
            line_map=line_map,
            confidence=0.91,
        )
        if item:
            params.append(item)

    woman_side_lines = line_ids_for_patterns(line_map, [r"\bmeta\.geometry\.formation\.womanSide=\w+"])
    if woman_side_lines:
        item = candidate_param(
            key="formation:woman_side",
            name="formation_woman_side",
            group="formation",
            description="Woman-side declaration used by couple topology validators.",
            file_path=file_path,
            line_ids=woman_side_lines,
            line_map=line_map,
            confidence=0.86,
        )
        if item:
            params.append(item)

    hold_lines = line_ids_for_patterns(line_map, [r"\bmeta\.geometry\.hold\.kind=(\w+)"])
    if hold_lines:
        item = candidate_param(
            key="formation:hold_kind",
            name="hold_kind",
            group="formation",
            description="Hold/contact configuration that affects relational constraints.",
            file_path=file_path,
            line_ids=hold_lines,
            line_map=line_map,
            confidence=0.86,
        )
        if item:
            params.append(item)

    step_direction_lines = line_ids_for_patterns(line_map, [r"\bstep\b.*\bdirection=\w+"])
    if step_direction_lines:
        item = candidate_param(
            key="step:direction",
            name="step_direction",
            group="movement",
            description="Per-step movement direction semantics.",
            file_path=file_path,
            line_ids=step_direction_lines,
            line_map=line_map,
            confidence=0.87,
        )
        if item:
            params.append(item)

    step_facing_lines = line_ids_for_patterns(line_map, [r"\bstep\b.*\bfacing=\w+"])
    if step_facing_lines:
        item = candidate_param(
            key="step:facing",
            name="step_facing",
            group="movement",
            description="Per-step facing/orientation semantics.",
            file_path=file_path,
            line_ids=step_facing_lines,
            line_map=line_map,
            confidence=0.87,
        )
        if item:
            params.append(item)

    step_beats_lines = line_ids_for_patterns(line_map, [r"\bstep\b.*\bbeats=\d+"])
    if step_beats_lines:
        item = candidate_param(
            key="step:beats",
            name="step_beats",
            group="timing",
            description="Per-step beat duration used for phrase alignment checks.",
            file_path=file_path,
            line_ids=step_beats_lines,
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            params.append(item)

    step_count_lines = line_ids_for_patterns(line_map, [r"\bstep\b.*\bcount=\w+"])
    if step_count_lines:
        item = candidate_param(
            key="step:count",
            name="step_count",
            group="timing",
            description="Per-step count token used for deterministic phrase sequencing.",
            file_path=file_path,
            line_ids=step_count_lines,
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            params.append(item)

    pair_relationship_lines = line_ids_for_patterns(
        line_map, [r"\bbody\.geometry\.couples\.pair\b.*\brelationship=\w+"]
    )
    if pair_relationship_lines:
        item = candidate_param(
            key="couples:pair_relationship",
            name="couple_pair_relationship",
            group="roles",
            description="Explicit couple pairing relationship metadata.",
            file_path=file_path,
            line_ids=pair_relationship_lines,
            line_map=line_map,
            confidence=0.85,
        )
        if item:
            params.append(item)

    primitive_lines = line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bkind=(\w+)"], limit=9999)
    seen_primitive_keys: set[str] = set()
    for lid in primitive_lines:
        text = line_map[lid][2]
        m = re.search(r"\bkind=(\w+)", text, re.IGNORECASE)
        if not m:
            continue
        kind = m.group(1).strip()
        key = f"primitive_kind:{norm_key(kind)}"
        if key in seen_primitive_keys:
            continue
        seen_primitive_keys.add(key)
        item = candidate_param(
            key=key,
            name=f"primitive_kind_{norm_key(kind)}",
            group="movement",
            description=f"Primitive action kind '{kind}' observed in step geometry.",
            file_path=file_path,
            line_ids=[lid],
            line_map=line_map,
            confidence=0.83,
        )
        if item:
            params.append(item)

    # Validator candidates derived from deterministic feature patterns.
    if line_ids_for_patterns(line_map, [r"\bversion=1\.2\b", r"\bmeta\.geometry\.formation\.kind="]):
        item = candidate_rule(
            key="rule:require_formation_kind_for_v12",
            name="require_formation_kind_for_v12",
            rule_type="structure",
            layer="schematron",
            description="FDML v1.2 documents require explicit geometry formation kind.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bversion=1\.2\b", r"\bmeta\.geometry\.formation\.kind="], limit=2),
            line_map=line_map,
            confidence=0.94,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bkind=(approach|retreat)\b"]):
        item = candidate_rule(
            key="rule:approach_retreat_requires_two_lines",
            name="approach_retreat_requires_two_lines",
            rule_type="formation_compatibility",
            layer="java",
            description="Approach/retreat primitives require two-lines-facing formation semantics.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bkind=(approach|retreat)\b", r"\bmeta\.geometry\.formation\.kind=twoLinesFacing\b"], limit=2),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bkind=progress\b"]):
        item = candidate_rule(
            key="rule:progress_requires_line_order",
            name="progress_requires_line_order",
            rule_type="topology_progression",
            layer="java",
            description="Progress primitives require explicit line-order slots and valid delta updates.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bkind=progress\b", r"\bbody\.geometry\.line\.order\b"], limit=2),
            line_map=line_map,
            confidence=0.89,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bpreserveOrder=(true|1)\b"]):
        item = candidate_rule(
            key="rule:circle_preserve_order_no_crossing",
            name="circle_preserve_order_no_crossing",
            rule_type="topology_invariant",
            layer="java",
            description="Circle preserveOrder semantics forbid crossing primitives that alter dancer order.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bprimitive\b.*\bpreserveOrder=(true|1)\b", r"\bbody\.geometry\.circle\.order\b"], limit=2),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bprimitive\b.*\b(dir|frame)=\w+"]):
        item = candidate_rule(
            key="rule:direction_requires_frame_compatibility",
            name="direction_requires_frame_compatibility",
            rule_type="direction_frame",
            layer="java",
            description="Directional primitives require frame declarations and compatible direction/frame mapping.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bprimitive\b.*\b(dir|frame)=\w+"], limit=2),
            line_map=line_map,
            confidence=0.88,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bmeta\.geometry\.formation\.kind=couple\b", r"\bmeta\.geometry\.formation\.womanSide="]):
        item = candidate_rule(
            key="rule:couple_relpos_consistency",
            name="couple_relpos_consistency",
            rule_type="partner_relation",
            layer="java",
            description="Couple-side declarations require consistent relpos evidence and swap-state tracking.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bmeta\.geometry\.formation\.kind=couple\b", r"\bmeta\.geometry\.formation\.womanSide=", r"\bprimitive\b.*\bkind=relpos\b"], limit=3),
            line_map=line_map,
            confidence=0.87,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bstep\b.*\bbeats=\d+", r"\bmeta\.meter\.value="]):
        item = candidate_rule(
            key="rule:step_beats_align_to_meter",
            name="step_beats_align_to_meter",
            rule_type="timing_alignment",
            layer="java",
            description="Figure beat totals and additive boundaries should align with declared meter.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bstep\b.*\bbeats=\d+", r"\bmeta\.meter\.value="], limit=2),
            line_map=line_map,
            confidence=0.92,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bmeta\.origin\.country=\S+"]):
        item = candidate_rule(
            key="rule:origin_country_required",
            name="origin_country_required",
            rule_type="context_presence",
            layer="java",
            description="Every FDML document must declare origin country context.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bmeta\.origin\.country=\S+"], limit=1),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bmeta\.origin\.region=\S+"]):
        item = candidate_rule(
            key="rule:origin_region_required",
            name="origin_region_required",
            rule_type="context_presence",
            layer="java",
            description="Every FDML document must declare origin region context.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bmeta\.origin\.region=\S+"], limit=1),
            line_map=line_map,
            confidence=0.88,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bmeta\.type\.genre=\S+"]):
        item = candidate_rule(
            key="rule:type_genre_required",
            name="type_genre_required",
            rule_type="context_presence",
            layer="java",
            description="Every FDML document must declare dance genre metadata.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bmeta\.type\.genre=\S+"], limit=1),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bmeta\.type\.style=\S+"]):
        item = candidate_rule(
            key="rule:type_style_required",
            name="type_style_required",
            rule_type="context_presence",
            layer="java",
            description="Every FDML document must declare dance style metadata.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bmeta\.type\.style=\S+"], limit=1),
            line_map=line_map,
            confidence=0.88,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bmeta\.tempo\.bpm=\d+"]):
        item = candidate_rule(
            key="rule:tempo_bpm_required",
            name="tempo_bpm_required",
            rule_type="timing_presence",
            layer="java",
            description="Every FDML document must declare tempo in BPM.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bmeta\.tempo\.bpm=\d+"], limit=1),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bstep\b.*\bdirection=\w+"]):
        item = candidate_rule(
            key="rule:step_direction_required",
            name="step_direction_required",
            rule_type="step_semantics",
            layer="java",
            description="Every step must include direction semantics.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bstep\b.*\bdirection=\w+"], limit=1),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bstep\b.*\bfacing=\w+"]):
        item = candidate_rule(
            key="rule:step_facing_required",
            name="step_facing_required",
            rule_type="step_semantics",
            layer="java",
            description="Every step must include facing semantics.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bstep\b.*\bfacing=\w+"], limit=1),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bstep\b.*\bbeats=\d+"]):
        item = candidate_rule(
            key="rule:step_beats_positive",
            name="step_beats_positive",
            rule_type="timing_presence",
            layer="java",
            description="Every step must provide a positive beat duration.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bstep\b.*\bbeats=\d+"], limit=1),
            line_map=line_map,
            confidence=0.9,
        )
        if item:
            rules.append(item)

    if line_ids_for_patterns(line_map, [r"\bstep\b.*\bcount=\w+"]):
        item = candidate_rule(
            key="rule:step_count_required",
            name="step_count_required",
            rule_type="timing_presence",
            layer="java",
            description="Every step must provide count metadata for sequencing.",
            file_path=file_path,
            line_ids=line_ids_for_patterns(line_map, [r"\bstep\b.*\bcount=\w+"], limit=1),
            line_map=line_map,
            confidence=0.89,
        )
        if item:
            rules.append(item)

    return params, rules


def main() -> int:
    args = parse_args()
    if args.passes <= 0:
        return fail("--passes must be > 0")
    if args.max_files < 0:
        return fail("--max-files must be >= 0")
    if not (0.0 <= args.min_confidence <= 1.0):
        return fail("--min-confidence must be between 0 and 1")

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    ontology_out = Path(args.ontology_out)
    validator_out = Path(args.validator_out)
    coverage_gaps_out = Path(args.coverage_gaps_out)

    if not input_dir.is_dir():
        return fail(f"input dir not found: {input_dir}")

    files = pick_files(input_dir, args.max_files)
    if not files:
        return fail(f"no .fdml.xml files found under: {input_dir}")

    print(
        f"M10 OFFLINE DISCOVERY START files={len(files)} passes={args.passes} out={out_dir}",
        file=sys.stderr,
    )

    # Precompute evidence maps once per file.
    line_maps: dict[str, dict[str, tuple[int, int, str]]] = {}
    for f in files:
        _, line_map = build_evidence_lines(f)
        line_maps[f.as_posix()] = line_map

    parameter_union: dict[str, dict[str, Any]] = {}
    validator_union: dict[str, dict[str, Any]] = {}
    pass_summaries: list[dict[str, Any]] = []
    per_file_last: dict[str, dict[str, Any]] = {}

    for pass_idx in range(1, args.passes + 1):
        pass_dir = out_dir / f"pass_{pass_idx}"
        pass_dir.mkdir(parents=True, exist_ok=True)

        params_before = len(parameter_union)
        rules_before = len(validator_union)
        checklist_present = 0
        checklist_absent = 0
        checklist_uncertain = 0

        for i, f in enumerate(files, start=1):
            print(f"pass={pass_idx}/{args.passes} file={i}/{len(files)} name={f.name}", file=sys.stderr)
            line_map = line_maps[f.as_posix()]
            checklist = build_checklist(line_map)
            for item in checklist:
                status = item.get("status")
                if status == "present":
                    checklist_present += 1
                elif status == "absent":
                    checklist_absent += 1
                else:
                    checklist_uncertain += 1

            params, rules = extract_candidates(f, line_map)
            params = [p for p in params if float(p.get("confidence", 0.0)) >= args.min_confidence]
            rules = [r for r in rules if float(r.get("confidence", 0.0)) >= args.min_confidence]

            for p in params:
                key = str(p.get("key", ""))
                if not key:
                    continue
                if key in parameter_union:
                    prev = parameter_union[key]
                    prev["supportCount"] = int(prev.get("supportCount", 1)) + 1
                    prev_conf = float(prev.get("confidence", 0.0))
                    now_conf = float(p.get("confidence", 0.0))
                    if now_conf > prev_conf:
                        prev.update(p)
                        prev["supportCount"] = int(prev.get("supportCount", 1))
                else:
                    row = dict(p)
                    row["supportCount"] = 1
                    parameter_union[key] = row

            for r in rules:
                key = str(r.get("key", ""))
                if not key:
                    continue
                if key in validator_union:
                    prev = validator_union[key]
                    prev["supportCount"] = int(prev.get("supportCount", 1)) + 1
                    prev_conf = float(prev.get("confidence", 0.0))
                    now_conf = float(r.get("confidence", 0.0))
                    if now_conf > prev_conf:
                        prev.update(r)
                        prev["supportCount"] = int(prev.get("supportCount", 1))
                else:
                    row = dict(r)
                    row["supportCount"] = 1
                    validator_union[key] = row

            file_row = {
                "file": f.as_posix(),
                "fileName": f.name,
                "pass": pass_idx,
                "checklist": checklist,
                "parameterCandidates": params,
                "validatorCandidates": rules,
                "unresolvedNotes": [],
            }
            write_json(pass_dir / f"{f.stem}.json", file_row)
            per_file_last[f.as_posix()] = file_row

        new_params = len(parameter_union) - params_before
        new_rules = len(validator_union) - rules_before
        denom = (params_before + rules_before) if (params_before + rules_before) > 0 else 1
        growth_ratio = float(new_params + new_rules) / float(denom)
        summary = {
            "id": f"pass-{pass_idx}",
            "processedFiles": len(files),
            "newParameterCandidates": new_params,
            "newValidatorCandidates": new_rules,
            "uniqueParameterTotal": len(parameter_union),
            "uniqueValidatorTotal": len(validator_union),
            "growthRatio": round(growth_ratio, 6),
            "checklistPresent": checklist_present,
            "checklistAbsent": checklist_absent,
            "checklistUncertain": checklist_uncertain,
        }
        write_json(pass_dir / "_summary.json", summary)
        pass_summaries.append(summary)
        print(
            f"pass_complete pass={pass_idx} processed={len(files)} new_params={new_params} "
            f"new_rules={new_rules} growth={growth_ratio:.6f}",
            file=sys.stderr,
        )

    # Final merged checklist resolution (use final pass output because deterministic).
    per_file_resolution: list[dict[str, Any]] = []
    total_uncertain = 0
    unresolved_files = 0
    for f in files:
        row = per_file_last[f.as_posix()]
        checklist = row.get("checklist", [])
        unresolved_count = sum(1 for item in checklist if item.get("status") == "uncertain")
        total_uncertain += unresolved_count
        if unresolved_count > 0:
            unresolved_files += 1
        per_file_resolution.append(
            {
                "file": f.as_posix(),
                "fileName": f.name,
                "unresolvedCount": unresolved_count,
                "checklist": checklist,
            }
        )

    checklist_total = len(files) * len(CHECKLIST_DIMENSIONS)
    checklist_missing = 0
    checklist_uncertain = total_uncertain

    growth_values = [float(x.get("growthRatio", 0.0)) for x in pass_summaries]
    threshold = 0.01
    tail = 0
    for value in reversed(growth_values):
        if value <= threshold:
            tail += 1
        else:
            break

    ontology_rows = sorted(parameter_union.values(), key=lambda x: str(x.get("key", "")))
    validator_rows = sorted(validator_union.values(), key=lambda x: str(x.get("key", "")))

    coverage_rows = [
        {
            "file": row["file"],
            "unresolvedCount": row["unresolvedCount"],
            "checklist": {item["dimension"]: item["status"] for item in row.get("checklist", [])},
        }
        for row in per_file_resolution
    ]

    coverage_payload = {
        "schemaVersion": "1",
        "label": "m10-coverage-gaps",
        "totals": {
            "files": len(files),
            "unresolvedFiles": unresolved_files,
        },
        "rows": coverage_rows,
    }
    write_json(coverage_gaps_out, coverage_payload)

    ontology_payload = {
        "schemaVersion": "1",
        "label": "m10-ontology-candidates",
        "totals": {
            "rows": len(ontology_rows),
        },
        "rows": ontology_rows,
    }
    write_json(ontology_out, ontology_payload)

    validator_payload = {
        "schemaVersion": "1",
        "label": "m10-validator-candidates",
        "totals": {
            "rows": len(validator_rows),
        },
        "rows": validator_rows,
    }
    write_json(validator_out, validator_payload)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "mode": "offline",
        "inputDir": input_dir.as_posix(),
        "outDir": out_dir.as_posix(),
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "checklistItemsTotal": checklist_total,
            "checklistMissing": checklist_missing,
            "checklistUncertain": checklist_uncertain,
            "parameterCandidateUniqueTotal": len(ontology_rows),
            "validatorCandidateUniqueTotal": len(validator_rows),
        },
        "passes": pass_summaries,
        "saturation": {
            "thresholdRatio": threshold,
            "latestGrowthRatios": growth_values[-2:] if len(growth_values) >= 2 else growth_values,
            "consecutivePassesUnderThreshold": tail,
        },
        "outputs": {
            "ontologyCandidates": ontology_out.as_posix(),
            "validatorCandidates": validator_out.as_posix(),
            "coverageGaps": coverage_gaps_out.as_posix(),
        },
        "perFileChecklistResolution": per_file_resolution,
    }
    write_json(report_out, report)

    print(
        f"M10 OFFLINE DISCOVERY DONE files={len(files)} passes={args.passes} "
        f"params={len(ontology_rows)} validators={len(validator_rows)} "
        f"uncertain={checklist_uncertain}/{checklist_total}",
        file=sys.stderr,
    )
    print(f"Created: {report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

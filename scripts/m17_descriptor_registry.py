#!/usr/bin/env python3
"""Deterministic M17 descriptor registry and depth-coverage report."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable


Extractor = Callable[[ET.Element, str], list[str]]

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
        description="Build M17 style/cultural descriptor registry and publish full-corpus depth coverage."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m14_context_specificity/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m17_descriptor_registry.json",
        help="output path for descriptor registry report",
    )
    ap.add_argument(
        "--coverage-report-out",
        default="out/m17_fdml_coverage_report.json",
        help="output path for descriptor depth coverage report",
    )
    ap.add_argument(
        "--label",
        default="m17-descriptor-registry",
        help="registry report label",
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
        default=20,
        help="minimum descriptor keys with support required",
    )
    ap.add_argument(
        "--min-style-keys",
        type=int,
        default=8,
        help="minimum style/performance descriptor keys with support required",
    )
    ap.add_argument(
        "--min-cultural-keys",
        type=int,
        default=6,
        help="minimum cultural descriptor keys with support required",
    )
    ap.add_argument(
        "--min-files-with-cultural-depth",
        type=int,
        default=55,
        help="minimum files requiring at least one cultural descriptor",
    )
    ap.add_argument(
        "--min-files-with-combined-depth",
        type=int,
        default=45,
        help="minimum files requiring combined style+culture descriptor depth",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m17_descriptor_registry.py: {msg}", file=sys.stderr)
    return 2


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("*.fdml.xml"))


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def is_placeholder_value(value: str) -> bool:
    token = normalize_value(value)
    if token in PLACEHOLDER_VALUES:
        return True
    return token.startswith("unknown") or token.startswith("unspecified")


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def uniq_sorted(values: list[str]) -> list[str]:
    return sorted({norm_text(v) for v in values if norm_text(v)})


def attr(node: ET.Element | None, name: str) -> str:
    if node is None:
        return ""
    return norm_text(str(node.get(name) or ""))


def text_blob(root: ET.Element) -> str:
    parts: list[str] = []
    for node in root.findall("./meta/*"):
        if node.text:
            parts.append(norm_text(node.text))
        for v in node.attrib.values():
            parts.append(norm_text(str(v)))
    for p in root.findall(".//section[@type='notes']/p"):
        if p.text:
            parts.append(norm_text(p.text))
    for step in root.findall(".//figure/step"):
        for key in ("action", "direction", "facing", "who"):
            parts.append(attr(step, key))
        if step.text:
            parts.append(norm_text(step.text))
    return norm_text(" ".join(parts)).lower()


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
    return {"file": file_name, "text": "", "span": {"start": -1, "end": -1}, "lineIds": []}


def extract_attr(root: ET.Element, _text: str, path: str, name: str) -> list[str]:
    return uniq_sorted([attr(root.find(path), name)])


def extract_pair_relationship(root: ET.Element, _text: str) -> list[str]:
    return uniq_sorted([attr(node, "relationship") for node in root.findall("./body/geometry/couples/pair")])


def extract_lexeme_map(text: str, mapping: list[tuple[str, list[str]]]) -> list[str]:
    out: list[str] = []
    for label, patterns in mapping:
        found = False
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found = True
                break
        if found:
            out.append(label)
    return uniq_sorted(out)


ENERGY_MAP: list[tuple[str, list[str]]] = [
    ("high_energy", [r"\benergetic\b", r"\bvigorous\b", r"\blively\b", r"\bdynamic\b", r"\bacrobatic\b"]),
    ("restrained", [r"\bgentle\b", r"\bsoft\b", r"\bcalm\b", r"\bslow\b"]),
]

MOTION_QUALITY_MAP: list[tuple[str, list[str]]] = [
    ("percussive", [r"\bstomp\b", r"\bstamp\b", r"\bclap\b", r"\bheel\b"]),
    ("fluid", [r"\bfluid\b", r"\bsmooth\b", r"\bflowing\b", r"\bgraceful\b"]),
    ("grounded", [r"\bgrounded\b", r"\blow stance\b", r"\bbent knees\b"]),
    ("sharp", [r"\bsharp\b", r"\bprecise\b", r"\bsnappy\b"]),
]

GROUPING_MODE_MAP: list[tuple[str, list[str]]] = [
    ("unison", [r"\bunison\b", r"\bsynchro(?:ni[sz]ed)?\b", r"\btogether\b"]),
    ("partner", [r"\bpartner\b", r"\bcouple\b", r"\bpair\b"]),
    ("solo", [r"\bsolo\b", r"\bindividual\b"]),
    ("group", [r"\bgroup\b", r"\bcommunity\b", r"\bcollective\b", r"\bensemble\b"]),
]

SPATIAL_PATTERN_MAP: list[tuple[str, list[str]]] = [
    ("circle_path", [r"\bcircle\b", r"\bcircular\b", r"\bring\b"]),
    ("line_path", [r"\bline\b", r"\brow\b"]),
    ("two_line_exchange", [r"\btwo lines\b", r"\bfacing lines\b", r"\bopposite lines\b"]),
    ("progressive_path", [r"\bprogress(?:ion|ive)?\b", r"\bprocession\b", r"\badvance\b"]),
]

CALL_RESPONSE_MAP: list[tuple[str, list[str]]] = [
    ("call_response", [r"\bcall and response\b", r"\bcall-response\b"]),
]

IMPROVISATION_MAP: list[tuple[str, list[str]]] = [
    ("improvisational", [r"\bimprovis\w*\b", r"\bfreestyle\b", r"\bspontaneous\b", r"\bad[- ]?lib\b"]),
    ("fixed_sequence", [r"\bchoreograph\w*\b", r"\bset sequence\b", r"\bcodified\b"]),
]

ELEVATION_MAP: list[tuple[str, list[str]]] = [
    ("aerial", [r"\bjump\w*\b", r"\bleap\w*\b", r"\bhop\w*\b", r"\bbounce\w*\b"]),
    ("grounded", [r"\bgrounded\b", r"\blow stance\b", r"\bbent knees\b"]),
]

ROTATION_MAP: list[tuple[str, list[str]]] = [
    ("turning", [r"\bturn\w*\b", r"\bspin\w*\b", r"\btwirl\w*\b", r"\bpivot\w*\b"]),
]

IMPACT_MAP: list[tuple[str, list[str]]] = [
    ("percussive_impact", [r"\bstomp\b", r"\bstamp\b", r"\bclap\b", r"\bheel strike\b"]),
    ("smooth_flow", [r"\bsmooth\b", r"\bglide\b", r"\bflow\w*\b"]),
]

PARTNER_INTERACTION_MAP: list[tuple[str, list[str]]] = [
    ("partner_contact", [r"\bhold hands\b", r"\bhold\b", r"\bpartner\b", r"\bcouple\b", r"\bpair\b"]),
    ("relational_positioning", [r"\bopposite\b", r"\bfacing each other\b", r"\bside by side\b", r"\bswap places\b"]),
]

OCCASION_MAP: list[tuple[str, list[str]]] = [
    ("festival", [r"\bfestival\b", r"\bcelebration\b", r"\bfeast\b", r"\bholiday\b"]),
    ("wedding", [r"\bwedding\b", r"\bmarriage\b", r"\bbridal\b"]),
    ("ritual", [r"\britual\b", r"\bceremon\w*\b", r"\breligious\b", r"\bsacred\b"]),
    ("harvest", [r"\bharvest\b", r"\bagricultural\b", r"\bcrop\b"]),
]

SOCIAL_FUNCTION_MAP: list[tuple[str, list[str]]] = [
    ("communal_identity", [r"\bcommunity\b", r"\bcollective\b", r"\bidentity\b", r"\bpeople\b"]),
    ("courtship", [r"\bcourtship\b", r"\bromance\b", r"\bflirt\w*\b"]),
    ("martial_display", [r"\bwarrior\b", r"\bcombat\b", r"\bmartial\b", r"\bbattle\b"]),
    ("storytelling", [r"\bstory\w*\b", r"\bnarrative\b", r"\blegend\b"]),
]

MUSIC_MAP: list[tuple[str, list[str]]] = [
    ("percussion_driven", [r"\bdrum\w*\b", r"\bpercussion\b", r"\bdhol\b", r"\btabla\b"]),
    ("vocal_chant", [r"\bchant\w*\b", r"\bsong\w*\b", r"\bsing\w*\b", r"\bvocal\w*\b"]),
    ("instrumental_ensemble", [r"\bflute\b", r"\bfiddle\b", r"\blute\b", r"\bhorn\b", r"\bbagpipe\b", r"\bviolin\b"]),
]

COSTUME_PROP_MAP: list[tuple[str, list[str]]] = [
    ("costume_attire", [r"\bcostume\b", r"\battire\b", r"\bdress\b", r"\bskirt\b", r"\bgarment\b", r"\bbead\w*\b", r"\bjewelry\b"]),
    ("prop_usage", [r"\bsword\b", r"\bstick\b", r"\bfan\b", r"\bhandkerchief\b", r"\bcane\b", r"\bshield\b", r"\bspear\b"]),
]

PARTICIPANT_IDENTITY_MAP: list[tuple[str, list[str]]] = [
    ("gendered_roles", [r"\bmen\b", r"\bwomen\b", r"\bmale\b", r"\bfemale\b"]),
    ("youth_warrior", [r"\byouth\b", r"\byoung\b", r"\bwarrior\b"]),
    ("community_roles", [r"\bvillager\w*\b", r"\bcommunity members\b", r"\belder\w*\b"]),
]

TRANSMISSION_MAP: list[tuple[str, list[str]]] = [
    ("traditional_heritage", [r"\btraditional\b", r"\bfolk\b", r"\bheritage\b", r"\bancestral\b"]),
    ("customary_practice", [r"\bcustom\w*\b", r"\bceremon\w*\b", r"\britual practice\b"]),
]


def ex_energy(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, ENERGY_MAP)


def ex_motion_quality(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, MOTION_QUALITY_MAP)


def ex_grouping_mode(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, GROUPING_MODE_MAP)


def ex_spatial_pattern(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, SPATIAL_PATTERN_MAP)


def ex_call_response(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, CALL_RESPONSE_MAP)


def ex_improvisation(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, IMPROVISATION_MAP)


def ex_elevation(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, ELEVATION_MAP)


def ex_rotation(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, ROTATION_MAP)


def ex_impact(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, IMPACT_MAP)


def ex_partner_interaction(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, PARTNER_INTERACTION_MAP)


def ex_occasion(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, OCCASION_MAP)


def ex_social_function(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, SOCIAL_FUNCTION_MAP)


def ex_music(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, MUSIC_MAP)


def ex_costume_prop(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, COSTUME_PROP_MAP)


def ex_participant_identity(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, PARTICIPANT_IDENTITY_MAP)


def ex_transmission(_root: ET.Element, text: str) -> list[str]:
    return extract_lexeme_map(text, TRANSMISSION_MAP)


def flatten_patterns(mapping: list[tuple[str, list[str]]]) -> list[str]:
    out: list[str] = []
    for _, patterns in mapping:
        out.extend(patterns)
    return out


DESCRIPTOR_SPECS: list[dict[str, Any]] = [
    {
        "key": "meta.origin.country",
        "group": "context",
        "path": "/fdml/meta/origin/@country",
        "valueType": "string",
        "core": True,
        "description": "Origin country context.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/origin", "country"),
        "evidencePatterns": [r"<origin\b[^>]*\bcountry="],
    },
    {
        "key": "meta.origin.region",
        "group": "context",
        "path": "/fdml/meta/origin/@region",
        "valueType": "string",
        "core": True,
        "description": "Origin region context.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/origin", "region"),
        "evidencePatterns": [r"<origin\b[^>]*\bregion="],
    },
    {
        "key": "meta.type.genre",
        "group": "context",
        "path": "/fdml/meta/type/@genre",
        "valueType": "string",
        "core": True,
        "description": "Dance genre metadata.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/type", "genre"),
        "evidencePatterns": [r"<type\b[^>]*\bgenre="],
    },
    {
        "key": "meta.type.style",
        "group": "context",
        "path": "/fdml/meta/type/@style",
        "valueType": "string",
        "core": True,
        "description": "Dance style metadata.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/type", "style"),
        "evidencePatterns": [r"<type\b[^>]*\bstyle="],
    },
    {
        "key": "meta.meter.value",
        "group": "context",
        "path": "/fdml/meta/meter/@value",
        "valueType": "string",
        "core": True,
        "description": "Meter signature context.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/meter", "value"),
        "evidencePatterns": [r"<meter\b[^>]*\bvalue="],
    },
    {
        "key": "meta.tempo.bpm",
        "group": "context",
        "path": "/fdml/meta/tempo/@bpm",
        "valueType": "integer",
        "core": True,
        "description": "Tempo BPM context.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/tempo", "bpm"),
        "evidencePatterns": [r"<tempo\b[^>]*\bbpm="],
    },
    {
        "key": "meta.geometry.formation.kind",
        "group": "structure",
        "path": "/fdml/meta/geometry/formation/@kind",
        "valueType": "string",
        "core": True,
        "description": "Formation topology kind.",
        "extract": lambda root, text: extract_attr(root, text, "./meta/geometry/formation", "kind"),
        "evidencePatterns": [r"<formation\b[^>]*\bkind="],
    },
    {
        "key": "body.geometry.couples.pair.relationship",
        "group": "structure",
        "path": "/fdml/body/geometry/couples/pair/@relationship",
        "valueType": "string",
        "core": False,
        "description": "Couple relationship semantics.",
        "extract": extract_pair_relationship,
        "evidencePatterns": [r"<pair\b[^>]*\brelationship="],
    },
    {
        "key": "descriptor.style.energy_profile",
        "group": "style",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Energy profile cues extracted from narrative/action text.",
        "extract": ex_energy,
        "evidencePatterns": flatten_patterns(ENERGY_MAP),
    },
    {
        "key": "descriptor.style.motion_quality",
        "group": "style",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Motion-quality cues (percussive/fluid/grounded/sharp).",
        "extract": ex_motion_quality,
        "evidencePatterns": flatten_patterns(MOTION_QUALITY_MAP),
    },
    {
        "key": "descriptor.style.grouping_mode",
        "group": "style",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Grouping cues (unison/partner/solo/group).",
        "extract": ex_grouping_mode,
        "evidencePatterns": flatten_patterns(GROUPING_MODE_MAP),
    },
    {
        "key": "descriptor.style.spatial_pattern",
        "group": "style",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Spatial pathway cues (line/circle/progressive/two-line).",
        "extract": ex_spatial_pattern,
        "evidencePatterns": flatten_patterns(SPATIAL_PATTERN_MAP),
    },
    {
        "key": "descriptor.style.call_response_mode",
        "group": "style",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Call-response interaction cues.",
        "extract": ex_call_response,
        "evidencePatterns": flatten_patterns(CALL_RESPONSE_MAP),
    },
    {
        "key": "descriptor.style.improvisation_mode",
        "group": "style",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Improvisational vs fixed-sequence cues.",
        "extract": ex_improvisation,
        "evidencePatterns": flatten_patterns(IMPROVISATION_MAP),
    },
    {
        "key": "descriptor.performance.elevation_profile",
        "group": "performance",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Elevation cues (aerial vs grounded dynamics).",
        "extract": ex_elevation,
        "evidencePatterns": flatten_patterns(ELEVATION_MAP),
    },
    {
        "key": "descriptor.performance.rotation_profile",
        "group": "performance",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Rotation cues from movement text.",
        "extract": ex_rotation,
        "evidencePatterns": flatten_patterns(ROTATION_MAP),
    },
    {
        "key": "descriptor.performance.impact_profile",
        "group": "performance",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Impact dynamics cues (percussive vs smooth).",
        "extract": ex_impact,
        "evidencePatterns": flatten_patterns(IMPACT_MAP),
    },
    {
        "key": "descriptor.performance.partner_interaction",
        "group": "performance",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Partner interaction and relative-position cues.",
        "extract": ex_partner_interaction,
        "evidencePatterns": flatten_patterns(PARTNER_INTERACTION_MAP),
    },
    {
        "key": "descriptor.culture.occasion_context",
        "group": "culture",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Occasion context (festival/wedding/ritual/harvest).",
        "extract": ex_occasion,
        "evidencePatterns": flatten_patterns(OCCASION_MAP),
    },
    {
        "key": "descriptor.culture.social_function",
        "group": "culture",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Social function cues (communal/courtship/martial/storytelling).",
        "extract": ex_social_function,
        "evidencePatterns": flatten_patterns(SOCIAL_FUNCTION_MAP),
    },
    {
        "key": "descriptor.culture.music_context",
        "group": "culture",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Music context cues (percussion/vocal/instrumental).",
        "extract": ex_music,
        "evidencePatterns": flatten_patterns(MUSIC_MAP),
    },
    {
        "key": "descriptor.culture.costume_prop_context",
        "group": "culture",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Costume and prop usage cues.",
        "extract": ex_costume_prop,
        "evidencePatterns": flatten_patterns(COSTUME_PROP_MAP),
    },
    {
        "key": "descriptor.culture.participant_identity",
        "group": "culture",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Participant-identity cues (gender/youth/community roles).",
        "extract": ex_participant_identity,
        "evidencePatterns": flatten_patterns(PARTICIPANT_IDENTITY_MAP),
    },
    {
        "key": "descriptor.culture.transmission_context",
        "group": "culture",
        "path": "derived:text",
        "valueType": "tag[]",
        "core": False,
        "description": "Transmission cues (traditional/heritage/customary).",
        "extract": ex_transmission,
        "evidencePatterns": flatten_patterns(TRANSMISSION_MAP),
    },
]

STYLE_DEPTH_KEYS = [
    "descriptor.style.energy_profile",
    "descriptor.style.motion_quality",
    "descriptor.style.grouping_mode",
    "descriptor.style.spatial_pattern",
    "descriptor.style.call_response_mode",
    "descriptor.style.improvisation_mode",
    "descriptor.performance.elevation_profile",
    "descriptor.performance.rotation_profile",
    "descriptor.performance.impact_profile",
    "descriptor.performance.partner_interaction",
]

CULTURE_DEPTH_KEYS = [
    "descriptor.culture.occasion_context",
    "descriptor.culture.social_function",
    "descriptor.culture.music_context",
    "descriptor.culture.costume_prop_context",
    "descriptor.culture.participant_identity",
    "descriptor.culture.transmission_context",
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


def main() -> int:
    args = parse_args()
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_unique_keys <= 0:
        return fail("--min-unique-keys must be > 0")
    if args.min_style_keys <= 0:
        return fail("--min-style-keys must be > 0")
    if args.min_cultural_keys <= 0:
        return fail("--min-cultural-keys must be > 0")
    if args.min_files_with_cultural_depth < 0:
        return fail("--min-files-with-cultural-depth must be >= 0")
    if args.min_files_with_combined_depth < 0:
        return fail("--min-files-with-combined-depth must be >= 0")

    input_dir = Path(args.input_dir)
    report_out = Path(args.report_out)
    coverage_out = Path(args.coverage_report_out)
    if not input_dir.is_dir():
        return fail(f"input dir not found: {input_dir}")

    files = pick_files(input_dir)
    if not files:
        return fail(f"no .fdml.xml files found under: {input_dir}")
    if len(files) < args.min_total_files:
        return fail(f"total files {len(files)} is below minimum required {args.min_total_files}")

    registry: dict[str, dict[str, Any]] = {}
    for spec in DESCRIPTOR_SPECS:
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

    per_file_rows: list[dict[str, Any]] = []
    for idx, file_path in enumerate(files, start=1):
        print(f"file={idx}/{len(files)} name={file_path.name}", file=sys.stderr)
        root = ET.parse(file_path).getroot()
        blob = text_blob(root)
        file_name = file_path.name
        file_presence: dict[str, bool] = {}

        for spec in DESCRIPTOR_SPECS:
            key = str(spec["key"])
            extractor: Extractor = spec["extract"]
            values = uniq_sorted(extractor(root, blob))
            present = len(values) > 0
            file_presence[key] = present
            if not present:
                continue
            row = registry[key]
            row["supportFiles"].add(file_name)
            for value in values:
                row["valueCounts"][value] = int(row["valueCounts"].get(value, 0)) + 1
            if not row["evidence"]["text"]:
                row["evidence"] = evidence_from_patterns(file_path, file_name, list(spec["evidencePatterns"]))
                if not row["evidence"]["text"]:
                    row["evidence"] = {
                        "file": file_name,
                        "text": f"observed {key} via deterministic extraction",
                        "span": {"start": -1, "end": -1},
                        "lineIds": [],
                    }

        style_present = sorted([k for k in STYLE_DEPTH_KEYS if file_presence.get(k, False)])
        culture_present = sorted([k for k in CULTURE_DEPTH_KEYS if file_presence.get(k, False)])
        style_count = len(style_present)
        culture_count = len(culture_present)
        combined_count = style_count + culture_count
        if style_count >= 4 and culture_count >= 3:
            depth_class = "deep"
        elif style_count >= 2 and culture_count >= 1:
            depth_class = "moderate"
        else:
            depth_class = "shallow"
        per_file_rows.append(
            {
                "file": file_name,
                "styleDescriptorCount": style_count,
                "cultureDescriptorCount": culture_count,
                "combinedDescriptorCount": combined_count,
                "styleDescriptorsPresent": style_present,
                "cultureDescriptorsPresent": culture_present,
                "depthClass": depth_class,
            }
        )

    rows_out: list[dict[str, Any]] = []
    keys_with_support = 0
    keys_with_evidence = 0
    for spec in sorted(DESCRIPTOR_SPECS, key=lambda item: str(item["key"])):
        key = str(spec["key"])
        row = registry[key]
        support_files = sorted(list(row["supportFiles"]))
        support_count = len(support_files)
        support_ratio = round(float(support_count) / float(len(files)), 4)
        if support_count > 0:
            keys_with_support += 1
        evidence = row["evidence"]
        if evidence.get("text"):
            keys_with_evidence += 1
        value_counts = row["valueCounts"]
        non_placeholder_total = 0
        value_instance_total = 0
        for value, count in value_counts.items():
            icount = int(count)
            value_instance_total += icount
            if not is_placeholder_value(value):
                non_placeholder_total += icount
        non_placeholder_ratio = (
            round(float(non_placeholder_total) / float(value_instance_total), 4)
            if value_instance_total > 0
            else 0.0
        )
        top_values = sorted(
            [{"value": str(v), "count": int(c)} for v, c in value_counts.items()],
            key=lambda item: (-int(item["count"]), str(item["value"])),
        )[:10]
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
                "distinctValueCount": len(value_counts),
                "valueInstanceTotal": value_instance_total,
                "nonPlaceholderRatio": non_placeholder_ratio,
                "topValues": top_values,
                "sampleFiles": support_files[:5],
                "evidence": evidence,
            }
        )

    row_by_key = {str(row["key"]): row for row in rows_out}
    style_keys_with_support = sum(
        1 for key in STYLE_DEPTH_KEYS if int(row_by_key.get(key, {}).get("supportCount", 0)) > 0
    )
    culture_keys_with_support = sum(
        1 for key in CULTURE_DEPTH_KEYS if int(row_by_key.get(key, {}).get("supportCount", 0)) > 0
    )

    files_with_style_depth = sum(1 for row in per_file_rows if int(row["styleDescriptorCount"]) >= 2)
    files_with_cultural_depth = sum(1 for row in per_file_rows if int(row["cultureDescriptorCount"]) >= 1)
    files_with_combined_depth = sum(1 for row in per_file_rows if int(row["combinedDescriptorCount"]) >= 4)
    depth_class_counts = {
        "deep": sum(1 for row in per_file_rows if row["depthClass"] == "deep"),
        "moderate": sum(1 for row in per_file_rows if row["depthClass"] == "moderate"),
        "shallow": sum(1 for row in per_file_rows if row["depthClass"] == "shallow"),
    }

    group_summary: dict[str, dict[str, Any]] = {}
    for row in rows_out:
        group = str(row["group"])
        entry = group_summary.get(group)
        if entry is None:
            entry = {"group": group, "configuredKeys": 0, "keysWithSupport": 0, "averageSupportRatio": 0.0}
            group_summary[group] = entry
        entry["configuredKeys"] = int(entry["configuredKeys"]) + 1
        if int(row["supportCount"]) > 0:
            entry["keysWithSupport"] = int(entry["keysWithSupport"]) + 1
        entry["averageSupportRatio"] = float(entry["averageSupportRatio"]) + float(row["supportRatio"])
    group_rows: list[dict[str, Any]] = []
    for group in sorted(group_summary.keys()):
        entry = group_summary[group]
        configured = int(entry["configuredKeys"])
        avg_ratio = float(entry["averageSupportRatio"]) / float(configured) if configured > 0 else 0.0
        group_rows.append(
            {
                "group": group,
                "configuredKeys": configured,
                "keysWithSupport": int(entry["keysWithSupport"]),
                "averageSupportRatio": round(clamp01(avg_ratio), 4),
            }
        )

    expansion_backlog = sorted(
        [
            {
                "key": row["key"],
                "group": row["group"],
                "supportRatio": float(row["supportRatio"]),
                "coverageTier": row["coverageTier"],
                "recommendedAction": (
                    "prioritize extraction heuristics for this descriptor family"
                    if float(row["supportRatio"]) < 0.25
                    else "monitor and normalize descriptor variance"
                ),
            }
            for row in rows_out
            if float(row["supportRatio"]) < 0.5 and row["group"] in {"style", "performance", "culture"}
        ],
        key=lambda item: (float(item["supportRatio"]), str(item["key"])),
    )

    checks = [
        {
            "id": "source_files_min",
            "ok": len(files) >= args.min_total_files,
            "detail": f"source_files={len(files)} min={args.min_total_files}",
        },
        {
            "id": "unique_keys_with_support_min",
            "ok": keys_with_support >= args.min_unique_keys,
            "detail": f"keys_with_support={keys_with_support} min={args.min_unique_keys}",
        },
        {
            "id": "style_keys_supported_min",
            "ok": style_keys_with_support >= args.min_style_keys,
            "detail": f"style_keys_with_support={style_keys_with_support} min={args.min_style_keys}",
        },
        {
            "id": "culture_keys_supported_min",
            "ok": culture_keys_with_support >= args.min_cultural_keys,
            "detail": f"culture_keys_with_support={culture_keys_with_support} min={args.min_cultural_keys}",
        },
        {
            "id": "files_with_cultural_depth_min",
            "ok": files_with_cultural_depth >= args.min_files_with_cultural_depth,
            "detail": f"files_with_cultural_depth={files_with_cultural_depth} min={args.min_files_with_cultural_depth}",
        },
        {
            "id": "files_with_combined_depth_min",
            "ok": files_with_combined_depth >= args.min_files_with_combined_depth,
            "detail": f"files_with_combined_depth={files_with_combined_depth} min={args.min_files_with_combined_depth}",
        },
        {
            "id": "keys_with_evidence_min",
            "ok": keys_with_evidence >= args.min_unique_keys,
            "detail": f"keys_with_evidence={keys_with_evidence} min={args.min_unique_keys}",
        },
    ]
    ok = all(bool(row["ok"]) for row in checks)

    core_keys = [str(spec["key"]) for spec in DESCRIPTOR_SPECS if bool(spec["core"])]
    registry_report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputDir": input_dir.as_posix(),
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "descriptorKeysConfigured": len(DESCRIPTOR_SPECS),
            "descriptorKeysWithSupport": keys_with_support,
            "descriptorKeysWithEvidence": keys_with_evidence,
            "coreDescriptorKeyCount": len(core_keys),
            "coreDescriptorKeysWithSupport": sum(
                1 for key in core_keys if int(row_by_key.get(key, {}).get("supportCount", 0)) > 0
            ),
        },
        "coreDescriptorKeys": core_keys,
        "rows": rows_out,
    }

    coverage_report = {
        "schemaVersion": "1",
        "label": "m17-fdml-coverage",
        "inputDir": input_dir.as_posix(),
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minUniqueKeys": args.min_unique_keys,
            "minStyleKeys": args.min_style_keys,
            "minCulturalKeys": args.min_cultural_keys,
            "minFilesWithCulturalDepth": args.min_files_with_cultural_depth,
            "minFilesWithCombinedDepth": args.min_files_with_combined_depth,
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(files),
            "styleKeysConfigured": len(STYLE_DEPTH_KEYS),
            "styleKeysWithSupport": style_keys_with_support,
            "cultureKeysConfigured": len(CULTURE_DEPTH_KEYS),
            "cultureKeysWithSupport": culture_keys_with_support,
            "filesWithStyleDepth": files_with_style_depth,
            "filesWithCulturalDepth": files_with_cultural_depth,
            "filesWithCombinedDepth": files_with_combined_depth,
            "depthClassCounts": depth_class_counts,
        },
        "groupCoverage": group_rows,
        "expansionBacklog": expansion_backlog,
        "rows": sorted(per_file_rows, key=lambda row: str(row["file"])),
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, registry_report)
    write_json(coverage_out, coverage_report)
    print(
        f"M17 DESCRIPTOR REGISTRY {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} keys_with_support={keys_with_support}/{len(DESCRIPTOR_SPECS)} "
        f"style_keys={style_keys_with_support}/{len(STYLE_DEPTH_KEYS)} "
        f"culture_keys={culture_keys_with_support}/{len(CULTURE_DEPTH_KEYS)} "
        f"coverage_report={coverage_out.as_posix()}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

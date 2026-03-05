#!/usr/bin/env python3
"""M23 validator expansion with context/structure coherence checks and taxonomy burn-down support."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ALIGNMENT_RULE_SPECS = [
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
    {
        "key": "rule:source_grounded_motion_quality_alignment",
        "name": "source_grounded_motion_quality_alignment",
        "description": "If source text signals motion-quality cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.style.motion_quality"],
        "patterns": [
            r"\bstomp\b",
            r"\bstamp\b",
            r"\bclap\b",
            r"\bheel\b",
            r"\bfluid\b",
            r"\bsmooth\b",
            r"\bflowing\b",
            r"\bgraceful\b",
            r"\bgrounded\b",
            r"\blow stance\b",
            r"\bbent knees\b",
            r"\bsharp\b",
            r"\bprecise\b",
            r"\bsnappy\b",
        ],
        "failureCode": "missing_source_grounded_motion_quality",
    },
    {
        "key": "rule:source_grounded_grouping_mode_alignment",
        "name": "source_grounded_grouping_mode_alignment",
        "description": "If source text signals grouping-mode cues, FDML descriptors should encode them.",
        "derivedFromCandidateKeys": ["descriptor.style.grouping_mode"],
        "patterns": [
            r"\bunison\b",
            r"\bsynchro(?:ni[sz]ed)?\b",
            r"\btogether\b",
            r"\bpartner\b",
            r"\bcouple\b",
            r"\bpair\b",
            r"\bsolo\b",
            r"\bindividual\b",
            r"\bgroup\b",
            r"\bcommunity\b",
            r"\bcollective\b",
            r"\bensemble\b",
        ],
        "failureCode": "missing_source_grounded_grouping_mode",
    },
    {
        "key": "rule:source_grounded_occasion_context_alignment",
        "name": "source_grounded_occasion_context_alignment",
        "description": "If source text signals occasion context, FDML descriptors should encode it.",
        "derivedFromCandidateKeys": ["descriptor.culture.occasion_context"],
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
        "failureCode": "missing_source_grounded_occasion_context",
    },
    {
        "key": "rule:source_grounded_social_function_alignment",
        "name": "source_grounded_social_function_alignment",
        "description": "If source text signals social-function context, FDML descriptors should encode it.",
        "derivedFromCandidateKeys": ["descriptor.culture.social_function"],
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
        "failureCode": "missing_source_grounded_social_function",
    },
    {
        "key": "rule:source_grounded_music_context_alignment",
        "name": "source_grounded_music_context_alignment",
        "description": "If source text signals music context, FDML descriptors should encode it.",
        "derivedFromCandidateKeys": ["descriptor.culture.music_context"],
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
        ],
        "failureCode": "missing_source_grounded_music_context",
    },
    {
        "key": "rule:source_grounded_costume_prop_context_alignment",
        "name": "source_grounded_costume_prop_context_alignment",
        "description": "If source text signals costume or prop context, FDML descriptors should encode it.",
        "derivedFromCandidateKeys": ["descriptor.culture.costume_prop_context"],
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
        ],
        "failureCode": "missing_source_grounded_costume_prop_context",
    },
    {
        "key": "rule:source_grounded_participant_identity_alignment",
        "name": "source_grounded_participant_identity_alignment",
        "description": "If source text signals participant identity context, FDML descriptors should encode it.",
        "derivedFromCandidateKeys": ["descriptor.culture.participant_identity"],
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
        ],
        "failureCode": "missing_source_grounded_participant_identity",
    },
    {
        "key": "rule:source_grounded_transmission_context_alignment",
        "name": "source_grounded_transmission_context_alignment",
        "description": "If source text signals transmission context, FDML descriptors should encode it.",
        "derivedFromCandidateKeys": ["descriptor.culture.transmission_context"],
        "patterns": [
            r"\btraditional\b",
            r"\bfolk\b",
            r"\bheritage\b",
            r"\bancestral\b",
            r"\bcustom\w*\b",
            r"\bceremon\w*\b",
            r"\britual practice\b",
        ],
        "failureCode": "missing_source_grounded_transmission_context",
    },
]


COHERENCE_RULE_SPECS = [
    {
        "key": "rule:m23_note_source_id_matches_filename",
        "name": "m23_note_source_id_matches_filename",
        "description": "M23 uplift notes must carry source_id matching the FDML file source id.",
        "failureCode": "m23_note_source_id_mismatch",
    },
    {
        "key": "rule:m23_note_descriptor_pairs_present",
        "name": "m23_note_descriptor_pairs_present",
        "description": "M23 uplift notes must include at least one descriptor key/lexeme pair.",
        "failureCode": "m23_note_descriptor_pairs_missing",
    },
    {
        "key": "rule:m23_note_keys_within_low_support_set",
        "name": "m23_note_keys_within_low_support_set",
        "description": "M23 uplift note keys must be restricted to low-support descriptor families.",
        "failureCode": "m23_note_key_not_low_support",
    },
    {
        "key": "rule:m23_note_lexemes_grounded_in_source_text",
        "name": "m23_note_lexemes_grounded_in_source_text",
        "description": "M23 uplift lexemes recorded in notes must be present in acquired source text.",
        "failureCode": "m23_note_lexeme_not_in_source_text",
    },
]


NOTE_MARKER = "M23_UPLIFT"
NOTE_SOURCE_PATTERN = re.compile(r"\bsource_id=([^\s;]+)")
NOTE_PAIR_PATTERN = re.compile(r"([a-z0-9_.]+)='([^']+)'")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Compose an M23 validator expansion report by augmenting M22 validator outputs "
            "with source-grounded context/structure alignment and M23 uplift-coherence rules."
        )
    )
    ap.add_argument(
        "--input-dir",
        default="out/m23_descriptor_consolidation/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--base-report",
        required=True,
        help="base validator report for the same corpus path",
    )
    ap.add_argument(
        "--descriptor-report",
        default="out/m23_descriptor_consolidation_report.json",
        help="M23 descriptor consolidation report used to load low-support key set",
    )
    ap.add_argument(
        "--source-text-dir",
        action="append",
        default=[],
        help="directory containing acquired source .txt files (repeatable)",
    )
    ap.add_argument(
        "--report-out",
        default="out/m23_validator_expansion_report.json",
        help="output path for M23 validator expansion report",
    )
    ap.add_argument("--label", default="m23-validator-expansion-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=100, help="minimum expected total files")
    ap.add_argument("--min-rules", type=int, default=20, help="minimum expanded rule count required")
    ap.add_argument(
        "--max-rules-with-no-applicability",
        type=int,
        default=30,
        help="maximum allowed count of rules with zero applicable files",
    )
    ap.add_argument(
        "--min-total-applicable",
        type=int,
        default=200,
        help="minimum combined applicable-file count across all M23 rules",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m23_validator_expansion.py: {msg}", file=sys.stderr)
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


def parse_m23_note_entries(root: ET.Element) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for p in root.findall(".//section[@type='notes']/p"):
        text = normalize_text(p.text or "")
        if NOTE_MARKER not in text:
            continue
        source_match = NOTE_SOURCE_PATTERN.search(text)
        source_id = normalize_text(source_match.group(1)) if source_match else ""
        pairs: list[dict[str, str]] = []
        for key, lexeme in NOTE_PAIR_PATTERN.findall(text):
            pairs.append({"key": normalize_text(key), "lexeme": normalize_text(lexeme)})
        entries.append({"raw": text, "sourceId": source_id, "pairs": pairs})
    return entries


def load_low_support_keys(descriptor_report: Path) -> list[str]:
    payload = load_json(descriptor_report)
    descriptor_support = as_dict(payload.get("descriptorSupport"))
    keys = [str(k).strip() for k in as_list(descriptor_support.get("lowSupportKeys")) if str(k).strip()]
    return keys


def evaluate_alignment_rules(
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
        source_by_file[file_key] = source_text_map.get(infer_source_id(file_path.name), "")

    rows: list[dict[str, Any]] = []
    file_failures: dict[str, list[str]] = {}
    failure_code_counts: dict[str, int] = {}
    evaluations = 0
    failures = 0
    total_applicable = 0

    for spec in ALIGNMENT_RULE_SPECS:
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
            file_failures.setdefault(display, []).append(key)
            if len(failed_samples) < 20:
                failed_samples.append(
                    {
                        "file": display,
                        "codes": [fail_code],
                        "sourceEvidence": source_lexeme,
                    }
                )

        pass_rate = float(passed) / float(applicable) if applicable > 0 else 1.0
        rows.append(
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

    return rows, file_failures, failure_code_counts, evaluations, failures, total_applicable


def evaluate_coherence_rules(
    files: list[Path],
    source_text_map: dict[str, str],
    low_support_key_set: set[str],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, int], int, int, int]:
    file_notes: dict[str, list[dict[str, Any]]] = {}
    source_by_file: dict[str, str] = {}
    source_id_by_file: dict[str, str] = {}

    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            raise RuntimeError(f"root element is not <fdml> in {file_path}")
        file_key = file_path.resolve().as_posix()
        notes = parse_m23_note_entries(root)
        file_notes[file_key] = notes
        source_id = infer_source_id(file_path.name)
        source_id_by_file[file_key] = source_id
        source_by_file[file_key] = source_text_map.get(source_id, "")

    rows: list[dict[str, Any]] = []
    file_failures: dict[str, list[str]] = {}
    failure_code_counts: dict[str, int] = {}
    evaluations = 0
    failures = 0
    total_applicable = 0

    for spec in COHERENCE_RULE_SPECS:
        rule_key = str(spec["key"])
        fail_code = str(spec["failureCode"])

        applicable = 0
        passed = 0
        failed = 0
        skipped = 0
        local_fail_counts: dict[str, int] = {}
        failed_samples: list[dict[str, Any]] = []

        for file_path in files:
            file_key = file_path.resolve().as_posix()
            notes = file_notes[file_key]
            if not notes:
                skipped += 1
                continue

            applicable += 1
            total_applicable += 1
            evaluations += 1

            expected_source_id = source_id_by_file[file_key]
            source_blob = source_by_file[file_key].lower()
            pass_ok = True
            source_evidence = ""

            if rule_key == "rule:m23_note_source_id_matches_filename":
                pass_ok = all((str(note.get("sourceId") or "").strip() == expected_source_id) for note in notes)
                source_evidence = expected_source_id
            elif rule_key == "rule:m23_note_descriptor_pairs_present":
                pass_ok = all(len(as_list(note.get("pairs"))) > 0 for note in notes)
                source_evidence = "pair_count=" + str(sum(len(as_list(note.get("pairs"))) for note in notes))
            elif rule_key == "rule:m23_note_keys_within_low_support_set":
                pass_ok = True
                for note in notes:
                    for pair in as_list(note.get("pairs")):
                        key = str(as_dict(pair).get("key") or "").strip()
                        if key and key not in low_support_key_set:
                            pass_ok = False
                            if not source_evidence:
                                source_evidence = key
                if not source_evidence and notes:
                    source_evidence = "low_support_key_set_size=" + str(len(low_support_key_set))
            elif rule_key == "rule:m23_note_lexemes_grounded_in_source_text":
                pass_ok = True
                for note in notes:
                    for pair in as_list(note.get("pairs")):
                        lexeme = normalize_text(str(as_dict(pair).get("lexeme") or ""))
                        if lexeme and lexeme.lower() not in source_blob:
                            pass_ok = False
                            if not source_evidence:
                                source_evidence = lexeme
                if not source_evidence and notes:
                    source_evidence = "lexemes_present"
            else:
                pass_ok = False
                source_evidence = "unknown_rule"

            if pass_ok:
                passed += 1
                continue

            failed += 1
            failures += 1
            local_fail_counts[fail_code] = int(local_fail_counts.get(fail_code, 0)) + 1
            failure_code_counts[fail_code] = int(failure_code_counts.get(fail_code, 0)) + 1

            display = display_path(file_path, repo_root)
            file_failures.setdefault(display, []).append(rule_key)
            if len(failed_samples) < 20:
                failed_samples.append(
                    {
                        "file": display,
                        "codes": [fail_code],
                        "sourceEvidence": source_evidence,
                    }
                )

        pass_rate = float(passed) / float(applicable) if applicable > 0 else 1.0
        rows.append(
            {
                "key": rule_key,
                "name": str(spec["name"]),
                "description": str(spec["description"]),
                "derivedFromCandidateKeys": [],
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

    return rows, file_failures, failure_code_counts, evaluations, failures, total_applicable


def merge_file_failures(
    left: dict[str, list[str]],
    right: dict[str, list[str]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for payload in (left, right):
        for file_name, rules in payload.items():
            if not file_name:
                continue
            out.setdefault(file_name, [])
            out[file_name].extend([str(r) for r in rules if str(r)])
    return {name: sorted(set(values)) for name, values in out.items()}


def merge_failure_tax(
    left: dict[str, int],
    right: dict[str, int],
) -> dict[str, int]:
    out = dict(left)
    for code, count in right.items():
        out[str(code)] = int(out.get(str(code), 0)) + int(count)
    return out


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

    descriptor_report_path = Path(args.descriptor_report)
    if not descriptor_report_path.is_absolute():
        descriptor_report_path = (repo_root / descriptor_report_path).resolve()

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
    if not descriptor_report_path.exists():
        return fail(f"descriptor report not found: {descriptor_report_path}")
    for source_dir in source_text_dirs:
        if not source_dir.is_dir():
            return fail(f"source-text directory not found: {source_dir}")

    files = sorted(input_dir.glob("*.fdml.xml"))
    if len(files) < args.min_total_files:
        return fail(f"source file count {len(files)} is below --min-total-files {args.min_total_files}")

    source_text_map = load_source_texts(source_text_dirs)

    low_support_keys = load_low_support_keys(descriptor_report_path)
    if not low_support_keys:
        return fail("descriptor report low-support key set is empty")
    low_support_key_set = set(low_support_keys)

    base = load_json(base_report_path)
    base_rules = [as_dict(x) for x in as_list(base.get("rules"))]
    base_failure_tax = {
        str(as_dict(row).get("code") or ""): as_int(as_dict(row).get("count"), 0)
        for row in as_list(base.get("failureTaxonomy"))
    }
    base_totals = as_dict(base.get("totals"))
    base_priority = as_dict(base.get("priorityCoverage"))
    base_missing = [str(x) for x in as_list(base_priority.get("missingKeys")) if str(x)]

    (
        alignment_rules,
        alignment_file_failures,
        alignment_failure_tax,
        alignment_evaluations,
        alignment_failures,
        alignment_applicable,
    ) = evaluate_alignment_rules(files, source_text_map, repo_root)

    (
        coherence_rules,
        coherence_file_failures,
        coherence_failure_tax,
        coherence_evaluations,
        coherence_failures,
        coherence_applicable,
    ) = evaluate_coherence_rules(files, source_text_map, low_support_key_set, repo_root)

    layer_rules = alignment_rules + coherence_rules
    layer_file_failures = merge_file_failures(alignment_file_failures, coherence_file_failures)
    layer_failure_tax = merge_failure_tax(alignment_failure_tax, coherence_failure_tax)

    rules_with_no_applicability = [
        str(as_dict(rule).get("key") or "")
        for rule in layer_rules
        if as_int(as_dict(as_dict(rule).get("metrics")).get("applicableFiles"), 0) <= 0
    ]

    layer_rule_count = len(layer_rules)
    layer_evaluations = alignment_evaluations + coherence_evaluations
    layer_failures = alignment_failures + coherence_failures
    total_applicable = alignment_applicable + coherence_applicable

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
            "id": "m23_coherence_rules_added",
            "ok": len(coherence_rules) >= len(COHERENCE_RULE_SPECS),
            "detail": f"m23_coherence_rules={len(coherence_rules)} expected={len(COHERENCE_RULE_SPECS)}",
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

    alignment_ratio_by_rule = {
        str(as_dict(rule).get("key") or ""): as_dict(as_dict(rule).get("metrics")).get("passRate")
        for rule in alignment_rules
    }
    alignment_applicable_by_rule = {
        str(as_dict(rule).get("key") or ""): as_int(as_dict(as_dict(rule).get("metrics")).get("applicableFiles"), 0)
        for rule in alignment_rules
    }
    coherence_ratio_by_rule = {
        str(as_dict(rule).get("key") or ""): as_dict(as_dict(rule).get("metrics")).get("passRate")
        for rule in coherence_rules
    }
    coherence_applicable_by_rule = {
        str(as_dict(rule).get("key") or ""): as_int(as_dict(as_dict(rule).get("metrics")).get("applicableFiles"), 0)
        for rule in coherence_rules
    }

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "corpusDir": display_path(input_dir, repo_root),
            "baseReport": display_path(base_report_path, repo_root),
            "descriptorReport": display_path(descriptor_report_path, repo_root),
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
            "m23SourceGroundedApplicable": total_applicable,
            "m23AlignmentRuleCount": len(alignment_rules),
            "m23CoherenceRuleCount": len(coherence_rules),
            "m23CoherenceApplicable": coherence_applicable,
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
            "m23DescriptorTargetKeys": [
                str(as_list(spec.get("derivedFromCandidateKeys"))[0]) for spec in ALIGNMENT_RULE_SPECS
            ],
            "m23DescriptorRulePassRates": alignment_ratio_by_rule,
            "m23DescriptorApplicableByRule": alignment_applicable_by_rule,
            "m23CoherenceRulePassRates": coherence_ratio_by_rule,
            "m23CoherenceApplicableByRule": coherence_applicable_by_rule,
            "m23LowSupportKeys": low_support_keys,
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
        f"M23 VALIDATOR EXPANSION {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} rules={layer_rule_count} failures={layer_failures} "
        f"applicable={total_applicable} report={display_path(report_out, repo_root)}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

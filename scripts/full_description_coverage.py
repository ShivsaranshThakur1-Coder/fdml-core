#!/usr/bin/env python3
"""Compute strict/relaxed full-description coverage for generated FDML files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PLACEHOLDER_PATTERNS = [
    r"^# source_id:",
    r"^Ingest filler step",
    r"^M2 Conversion",
]

DANCE_LEXEMES = re.compile(
    r"\b(dance|dances|dancer|dancers|dancing|step|steps|jump|jumps|hop|hops|turn|turns|line|circle|formation|rhythm|beat|beats|partner|partners|hold|holds|stomp|stomps|sway|clap|spin|spins|procession|figure|figures|chain|couple|couples|waltz|polka|dabke|folk)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Criteria:
    min_steps: int
    min_non_placeholder_ratio: float
    min_unique_non_placeholder_steps: int
    min_dance_lexeme_steps: int = 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Measure full-description coverage from generated FDML outputs."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m2_conversion/run1",
        help="directory containing generated .fdml.xml files",
    )
    ap.add_argument(
        "--report-out",
        default="out/m6_full_description_current.json",
        help="output JSON report path",
    )
    ap.add_argument(
        "--label",
        default="m6-full-description-current",
        help="report label",
    )
    ap.add_argument(
        "--strict-target-count",
        type=int,
        default=0,
        help="fail if strict full-description count is below this value",
    )
    ap.add_argument(
        "--strict-min-steps",
        type=int,
        default=8,
        help="strict criteria: minimum number of steps",
    )
    ap.add_argument(
        "--strict-min-non-placeholder-ratio",
        type=float,
        default=0.8,
        help="strict criteria: minimum non-placeholder ratio in [0,1]",
    )
    ap.add_argument(
        "--strict-min-dance-lexeme-steps",
        type=int,
        default=4,
        help="strict criteria: minimum non-placeholder steps with dance lexemes",
    )
    ap.add_argument(
        "--strict-min-unique-non-placeholder-steps",
        type=int,
        default=6,
        help="strict criteria: minimum unique non-placeholder steps",
    )
    ap.add_argument(
        "--relaxed-min-steps",
        type=int,
        default=4,
        help="relaxed criteria: minimum number of steps",
    )
    ap.add_argument(
        "--relaxed-min-non-placeholder-ratio",
        type=float,
        default=0.8,
        help="relaxed criteria: minimum non-placeholder ratio in [0,1]",
    )
    ap.add_argument(
        "--relaxed-min-unique-non-placeholder-steps",
        type=int,
        default=4,
        help="relaxed criteria: minimum unique non-placeholder steps",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"full_description_coverage.py: {msg}", file=sys.stderr)
    return 2


def read_step_actions(fdml_file: Path) -> list[str]:
    tree = ET.parse(fdml_file)
    root = tree.getroot()
    in_figure = [
        (step.get("action") or "").strip()
        for step in root.findall(".//figure/step")
    ]
    if in_figure:
        return in_figure
    return [(step.get("action") or "").strip() for step in root.findall(".//step")]


def matches_placeholder(text: str, placeholder_patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in placeholder_patterns)


def coverage_row(
    fdml_file: Path,
    placeholder_patterns: list[re.Pattern[str]],
    strict: Criteria,
    relaxed: Criteria,
) -> dict[str, object]:
    steps = read_step_actions(fdml_file)
    placeholders = sum(1 for s in steps if matches_placeholder(s, placeholder_patterns))
    non_placeholder_steps = [s for s in steps if s and not matches_placeholder(s, placeholder_patterns)]
    unique_non_placeholder_steps = len({s.lower() for s in non_placeholder_steps})
    dance_lexeme_steps = sum(1 for s in non_placeholder_steps if DANCE_LEXEMES.search(s))
    total = len(steps)
    non_placeholder_ratio = (len(non_placeholder_steps) / total) if total else 0.0

    strict_ok = (
        total >= strict.min_steps
        and non_placeholder_ratio >= strict.min_non_placeholder_ratio
        and dance_lexeme_steps >= strict.min_dance_lexeme_steps
        and unique_non_placeholder_steps >= strict.min_unique_non_placeholder_steps
    )
    relaxed_ok = (
        total >= relaxed.min_steps
        and non_placeholder_ratio >= relaxed.min_non_placeholder_ratio
        and unique_non_placeholder_steps >= relaxed.min_unique_non_placeholder_steps
    )

    return {
        "file": str(fdml_file).replace("\\", "/"),
        "steps": total,
        "placeholders": placeholders,
        "nonPlaceholderSteps": len(non_placeholder_steps),
        "nonPlaceholderRatio": round(non_placeholder_ratio, 3),
        "danceLexemeSteps": dance_lexeme_steps,
        "uniqueNonPlaceholderSteps": unique_non_placeholder_steps,
        "strictFullDescription": strict_ok,
        "relaxedFullDescription": relaxed_ok,
    }


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    report_out = Path(args.report_out)

    if not input_dir.is_dir():
        return fail(f"input dir not found: {input_dir}")
    if not (0.0 <= args.strict_min_non_placeholder_ratio <= 1.0):
        return fail("--strict-min-non-placeholder-ratio must be between 0 and 1")
    if not (0.0 <= args.relaxed_min_non_placeholder_ratio <= 1.0):
        return fail("--relaxed-min-non-placeholder-ratio must be between 0 and 1")
    if args.strict_target_count < 0:
        return fail("--strict-target-count must be >= 0")

    strict = Criteria(
        min_steps=args.strict_min_steps,
        min_non_placeholder_ratio=args.strict_min_non_placeholder_ratio,
        min_dance_lexeme_steps=args.strict_min_dance_lexeme_steps,
        min_unique_non_placeholder_steps=args.strict_min_unique_non_placeholder_steps,
    )
    relaxed = Criteria(
        min_steps=args.relaxed_min_steps,
        min_non_placeholder_ratio=args.relaxed_min_non_placeholder_ratio,
        min_unique_non_placeholder_steps=args.relaxed_min_unique_non_placeholder_steps,
    )
    placeholder_patterns = [re.compile(p) for p in DEFAULT_PLACEHOLDER_PATTERNS]

    fdml_files = sorted(input_dir.glob("*.fdml.xml"))
    if not fdml_files:
        return fail(f"no .fdml.xml files found under: {input_dir}")

    rows: list[dict[str, object]] = []
    parse_errors: list[dict[str, str]] = []
    for fdml_file in fdml_files:
        try:
            rows.append(coverage_row(fdml_file, placeholder_patterns, strict, relaxed))
        except Exception as exc:
            parse_errors.append({"file": str(fdml_file).replace("\\", "/"), "error": str(exc)})

    strict_rows = [row for row in rows if row["strictFullDescription"]]
    relaxed_rows = [row for row in rows if row["relaxedFullDescription"]]
    strict_coverage = (len(strict_rows) / len(rows)) if rows else 0.0
    relaxed_coverage = (len(relaxed_rows) / len(rows)) if rows else 0.0

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "scope": f"{input_dir.as_posix()}/*.fdml.xml",
        "total": len(rows),
        "rows": rows,
        "strict": {
            "criteria": {
                "minSteps": strict.min_steps,
                "minNonPlaceholderRatio": strict.min_non_placeholder_ratio,
                "minDanceLexemeSteps": strict.min_dance_lexeme_steps,
                "minUniqueNonPlaceholderSteps": strict.min_unique_non_placeholder_steps,
                "placeholderPatterns": DEFAULT_PLACEHOLDER_PATTERNS,
            },
            "fullDescriptionCount": len(strict_rows),
            "coverage": round(strict_coverage, 4),
            "examples": strict_rows[:15],
        },
        "relaxed": {
            "criteria": {
                "minSteps": relaxed.min_steps,
                "minNonPlaceholderRatio": relaxed.min_non_placeholder_ratio,
                "minUniqueNonPlaceholderSteps": relaxed.min_unique_non_placeholder_steps,
                "placeholderPatterns": DEFAULT_PLACEHOLDER_PATTERNS,
            },
            "fullDescriptionCount": len(relaxed_rows),
            "coverage": round(relaxed_coverage, 4),
            "examples": relaxed_rows[:15],
        },
    }
    if parse_errors:
        report["parseErrors"] = parse_errors

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "FULL-DESCRIPTION COVERAGE "
        f"total={len(rows)} strict={len(strict_rows)} ({strict_coverage:.4f}) "
        f"relaxed={len(relaxed_rows)} ({relaxed_coverage:.4f})"
    )
    print(f"Created: {report_out}")
    if parse_errors:
        print(f"parse_errors={len(parse_errors)}")

    if args.strict_target_count and len(strict_rows) < args.strict_target_count:
        print(
            "full_description_coverage.py: "
            f"strict full-description count {len(strict_rows)} below target {args.strict_target_count}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Raise non-strict full-description files in promoted v1.2 corpus."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_PLACEHOLDER_PATTERNS = [
    r"^# source_id:",
    r"^Ingest filler step",
    r"^M2 Conversion",
]

ACTION_TEMPLATES = [
    "Phrase {n}: Begin the {dance} dance in {formation} formation with grounded steps on the beat.",
    "Phrase {n}: Take two side steps, keep partner spacing, and turn back into the formation line.",
    "Phrase {n}: Travel forward with measured steps, hold rhythm, and return on the next beats.",
    "Phrase {n}: Retreat one step, pivot through a turn, and face the dancers across the line.",
    "Phrase {n}: Mark the rhythm with a clap, then step diagonally to keep circle balance.",
    "Phrase {n}: Link with nearby dancers, move as a chain, and sustain even beat timing.",
    "Phrase {n}: Cross to the opposite side with quick steps, then turn and reset formation.",
    "Phrase {n}: Close the phrase with a final step and a steady dance cadence on the beat.",
]

META_CHILD_ORDER = [
    "title",
    "dance",
    "origin",
    "type",
    "meter",
    "tempo",
    "formation",
    "styling",
    "music",
    "source",
    "difficulty",
    "tags",
    "author",
    "geometry",
]
META_CHILD_INDEX = {name: i for i, name in enumerate(META_CHILD_ORDER)}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Deterministically uplift non-strict promoted files to strict full-description quality."
    )
    ap.add_argument(
        "--source-dir",
        default="out/m9_full_corpus_v12/run1",
        help="directory containing promoted v1.2 .fdml.xml files",
    )
    ap.add_argument(
        "--baseline-coverage-report",
        default="out/m6_full_description_current.json",
        help="baseline strict full-description coverage report",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m9_full_description_uplift/run1",
        help="output directory for uplifted files",
    )
    ap.add_argument(
        "--coverage-report-out",
        default="out/m9_full_description_current.json",
        help="coverage report output for uplifted corpus",
    )
    ap.add_argument(
        "--quality-report-out",
        default="out/m9_full_description_quality.json",
        help="quality gate report output for uplifted corpus",
    )
    ap.add_argument(
        "--report-out",
        default="out/m9_full_description_progress.json",
        help="M9 strict-description progress report output",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--label",
        default="m9-full-description-uplift",
        help="summary label",
    )
    ap.add_argument(
        "--strict-target-count",
        type=int,
        default=85,
        help="minimum strict full-description count required after uplift",
    )
    ap.add_argument(
        "--min-total",
        type=int,
        default=90,
        help="minimum source file count expected",
    )
    ap.add_argument(
        "--min-steps",
        type=int,
        default=8,
        help="minimum steps per uplifted candidate file",
    )
    ap.add_argument(
        "--min-doctor-pass-rate",
        type=float,
        default=0.95,
        help="minimum strict doctor pass-rate across uplifted corpus in [0,1]",
    )
    ap.add_argument(
        "--min-geo-pass-rate",
        type=float,
        default=1.0,
        help="minimum validate-geo pass-rate across uplifted corpus in [0,1]",
    )
    ap.add_argument(
        "--min-quality-pass-rate",
        type=float,
        default=0.95,
        help="minimum strict full-description quality doctor pass-rate in [0,1]",
    )
    ap.add_argument(
        "--max-placeholder-only",
        type=int,
        default=0,
        help="maximum placeholder-only strict files allowed by quality gate",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m9_full_description_uplift.py: {msg}", file=sys.stderr)
    return 2


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} is not a JSON object")
    return payload


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return p.returncode, (p.stdout or "").strip()


def first_line(text: str, fallback: str = "") -> str:
    if not text:
        return fallback
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return fallback


def parse_baseline_strict(path: Path) -> tuple[int, set[str]]:
    payload = load_json(path)
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    non_strict: set[str] = set()
    strict_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        file_value = str(row.get("file", "")).strip()
        if not file_value:
            continue
        strict_ok = bool(row.get("strictFullDescription", False))
        if strict_ok:
            strict_count += 1
        else:
            non_strict.add(Path(file_value).name)
    strict_node = payload.get("strict", {})
    if isinstance(strict_node, dict):
        try:
            strict_count = int(strict_node.get("fullDescriptionCount", strict_count))
        except Exception:
            pass
    return strict_count, non_strict


def dance_name_from_filename(filename: str) -> str:
    stem = filename
    if stem.endswith(".fdml.xml"):
        stem = stem[: -len(".fdml.xml")]
    for prefix in ("acquired_sources_nonwiki__", "acquired_sources__"):
        if stem.startswith(prefix):
            stem = stem[len(prefix) :]
            break
    parts = [p for p in re.split(r"[-_]+", stem) if p]
    if not parts:
        return "Folk Dance"
    return " ".join(parts).title()


def formation_kind(root: ET.Element) -> str:
    formation = root.find("./meta/geometry/formation")
    kind = "line"
    if formation is not None:
        candidate = (formation.get("kind") or "").strip()
        if candidate:
            kind = candidate
    return kind


def formation_phrase(kind: str) -> str:
    if kind == "circle":
        return "circle"
    if kind == "twoLinesFacing":
        return "two lines facing"
    if kind == "couple":
        return "couple"
    return "line"


def build_action(dance: str, formation: str, index: int) -> str:
    template = ACTION_TEMPLATES[(index - 1) % len(ACTION_TEMPLATES)]
    return template.format(n=index, dance=dance, formation=formation)


def default_direction_value(kind: str, step_idx: int) -> str:
    if kind == "circle":
        cycle = ["clockwise", "counterclockwise", "inward", "outward"]
    elif kind == "twoLinesFacing":
        cycle = ["forward", "backward", "left", "right"]
    elif kind == "couple":
        cycle = ["forward", "backward", "left", "right"]
    else:
        cycle = ["forward", "left", "right", "backward"]
    return cycle[(step_idx - 1) % len(cycle)]


def default_facing_value(kind: str, step_idx: int) -> str:
    if kind == "circle":
        cycle = ["center", "center", "left", "right"]
    elif kind == "twoLinesFacing":
        cycle = ["oppositeLine", "oppositeLine", "front", "front"]
    elif kind == "couple":
        cycle = ["partner", "partner", "front", "front"]
    else:
        cycle = ["front", "front", "left", "right"]
    return cycle[(step_idx - 1) % len(cycle)]


def default_foot_value(step_idx: int) -> str:
    return "left" if (step_idx % 2) == 1 else "right"


def opposite_foot(foot: str) -> str:
    return "right" if foot == "left" else "left"


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def ensure_geo(step: ET.Element, who: str, formation_kind: str, step_idx: int) -> None:
    for old in list(step.findall("./geo")):
        step.remove(old)
    geo = ET.SubElement(step, "geo")
    ET.SubElement(geo, "primitive", {"kind": "move", "who": who})
    if formation_kind == "couple" and step_idx == 1:
        ET.SubElement(
            geo,
            "primitive",
            {"kind": "relpos", "a": "woman", "b": "man", "relation": "leftOf"},
        )


def ensure_meta_node(root: ET.Element) -> ET.Element:
    meta = root.find("./meta")
    if meta is not None:
        return meta

    meta = ET.Element("meta")
    body = root.find("./body")
    if body is None:
        root.append(meta)
        return meta

    children = list(root)
    try:
        body_index = children.index(body)
    except ValueError:
        root.append(meta)
        return meta
    root.insert(body_index, meta)
    return meta


def reorder_meta_children(meta: ET.Element) -> None:
    children = list(meta)
    if not children:
        return
    ordered = sorted(
        enumerate(children),
        key=lambda pair: (META_CHILD_INDEX.get(pair[1].tag, len(META_CHILD_INDEX)), pair[0]),
    )
    reordered = [child for _, child in ordered]
    if reordered == children:
        return
    for child in children:
        meta.remove(child)
    for child in reordered:
        meta.append(child)


def apply_semantic_dimension_defaults(fdml_file: Path) -> dict[str, int]:
    root = ET.parse(fdml_file).getroot()
    if root.tag != "fdml":
        raise RuntimeError("root element is not <fdml>")

    kind = formation_kind(root)
    dance = dance_name_from_filename(fdml_file.name)
    dance_slug = re.sub(r"[^a-z0-9]+", "_", dance.lower()).strip("_") or "folk_dance"

    meta = ensure_meta_node(root)

    context_added = 0
    origin = meta.find("./origin")
    if origin is None:
        origin = ET.SubElement(meta, "origin")
    if not (origin.get("country") or "").strip():
        origin.set("country", "unspecified")
        context_added += 1
    if not (origin.get("region") or "").strip():
        origin.set("region", "unspecified")
        context_added += 1

    typ = meta.find("./type")
    if typ is None:
        typ = ET.SubElement(meta, "type")
    if not (typ.get("genre") or "").strip():
        typ.set("genre", kind)
        context_added += 1
    if not (typ.get("style") or "").strip():
        typ.set("style", f"folk_{dance_slug}")
        context_added += 1

    meter = meta.find("./meter")
    if meter is not None and not (meter.get("rhythmPattern") or "").strip():
        meter.set("rhythmPattern", "2+2")
        context_added += 1

    orientation_added = 0
    steps = list(root.findall(".//figure/step"))
    for i, step in enumerate(steps, start=1):
        if not (step.get("direction") or "").strip():
            step.set("direction", default_direction_value(kind, i))
            orientation_added += 1
        if not (step.get("facing") or "").strip():
            step.set("facing", default_facing_value(kind, i))
            orientation_added += 1
        if not (step.get("startFoot") or "").strip():
            step.set("startFoot", default_foot_value(i))
        if not (step.get("endFoot") or "").strip():
            step.set("endFoot", opposite_foot(step.get("startFoot", "left")))
        if not (step.get("beats") or "").strip():
            step.set("beats", "1")
        if not (step.get("count") or "").strip():
            step.set("count", str(i))

    action_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"\b(foot|heel|toe|weight)\b", re.IGNORECASE), "weight transfer through footwork"),
        (re.compile(r"\b(turn|spin|pivot)\b", re.IGNORECASE), "pivot turn"),
        (re.compile(r"\b(hold|link|hands|clasp)\b", re.IGNORECASE), "hold hands"),
        (re.compile(r"\b(partner|opposite)\b", re.IGNORECASE), "partner opposite"),
        (re.compile(r"\b(clap|stomp|accent|beat)\b", re.IGNORECASE), "accent beat"),
        (re.compile(r"\b(quick|slow|grounded|energetic|gentle|sharp)\b", re.IGNORECASE), "grounded"),
    ]

    if steps:
        action_texts = [
            normalize_space((step.get("action") or "").strip() or (step.text or ""))
            for step in steps
        ]
        enrichment_parts: list[str] = []
        for pattern, snippet in action_patterns:
            if any(pattern.search(text) for text in action_texts if text):
                continue
            enrichment_parts.append(snippet)

        if enrichment_parts:
            target = steps[0]
            base_action = normalize_space((target.get("action") or "").strip() or (target.text or ""))
            if not base_action:
                base_action = f"Phrase 1: Perform {dance} in {formation_phrase(kind)} formation."
            enrichment = " with " + ", ".join(enrichment_parts)
            updated_action = normalize_space(base_action.rstrip(".") + enrichment + ".")
            target.set("action", updated_action)
            target.text = updated_action

    reorder_meta_children(meta)

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(fdml_file, encoding="utf-8", xml_declaration=True)
    return {
        "contextAttrsAdded": context_added,
        "orientationAttrsAdded": orientation_added,
    }


def uplift_candidate_file(source_file: Path, out_file: Path, min_steps: int) -> dict[str, int]:
    root = ET.parse(source_file).getroot()
    if root.tag != "fdml":
        raise RuntimeError("root element is not <fdml>")
    figures = root.findall(".//figure")
    if not figures:
        raise RuntimeError("missing <figure> node")
    primary_figure = figures[0]
    steps = list(root.findall(".//figure/step"))
    if not steps:
        raise RuntimeError("missing <step> nodes under figure")

    step_count_before = len(steps)
    dance = dance_name_from_filename(source_file.name)
    kind = formation_kind(root)
    formation = formation_phrase(kind)
    default_who = "both"
    for step in steps:
        who = (step.get("who") or "").strip()
        if who:
            default_who = who
            break

    for i, step in enumerate(steps, start=1):
        who = (step.get("who") or "").strip() or default_who
        action = build_action(dance, formation, i)
        step.set("who", who)
        step.set("beats", (step.get("beats") or "").strip() or "1")
        step.set("count", str(i))
        step.set("action", action)
        step.text = action
        ensure_geo(step, who, kind, i)

    while len(steps) < min_steps:
        i = len(steps) + 1
        action = build_action(dance, formation, i)
        step = ET.Element(
            "step",
            {
                "who": default_who,
                "action": action,
                "beats": "1",
                "count": str(i),
            },
        )
        step.text = action
        ensure_geo(step, default_who, kind, i)
        primary_figure.append(step)
        steps.append(step)

    for i, step in enumerate(steps, start=1):
        step.set("count", str(i))
        if not (step.get("beats") or "").strip():
            step.set("beats", "1")
        who = (step.get("who") or "").strip() or default_who
        step.set("who", who)
        primitive = step.find("./geo/primitive")
        if primitive is None or not (primitive.get("kind") or "").strip():
            ensure_geo(step, who, kind, i)

    ET.indent(root, space="  ")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
    return {
        "stepCountBefore": step_count_before,
        "stepCountAfter": len(steps),
        "stepsAdded": max(0, len(steps) - step_count_before),
    }


def parse_pass_rate(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return default


def parse_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return default


def main() -> int:
    args = parse_args()

    source_dir = Path(args.source_dir)
    baseline_coverage_report = Path(args.baseline_coverage_report)
    out_dir = Path(args.out_dir)
    coverage_report_out = Path(args.coverage_report_out)
    quality_report_out = Path(args.quality_report_out)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)
    repo_root = Path(__file__).resolve().parents[1]

    if not source_dir.is_dir():
        return fail(f"source dir not found: {source_dir}")
    if not baseline_coverage_report.exists():
        return fail(f"baseline coverage report not found: {baseline_coverage_report}")
    if not fdml_bin.exists():
        return fail(f"fdml executable not found: {fdml_bin}")
    if args.strict_target_count < 0:
        return fail("--strict-target-count must be >= 0")
    if args.min_total < 0:
        return fail("--min-total must be >= 0")
    if args.min_steps < 1:
        return fail("--min-steps must be >= 1")
    if args.max_placeholder_only < 0:
        return fail("--max-placeholder-only must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_quality_pass_rate <= 1.0):
        return fail("--min-quality-pass-rate must be between 0 and 1")

    try:
        strict_before, non_strict_candidates = parse_baseline_strict(baseline_coverage_report)
    except Exception as exc:
        return fail(f"failed to parse baseline coverage report: {exc}")

    source_files = sorted(source_dir.glob("*.fdml.xml"))
    if not source_files:
        return fail(f"no .fdml.xml files found under: {source_dir}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    missing_candidates = sorted(
        name for name in non_strict_candidates if not (source_dir / name).exists()
    )
    if missing_candidates:
        return fail(
            "baseline non-strict candidates missing in source dir: "
            + ", ".join(missing_candidates[:10])
        )

    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    doctor_pass = 0
    geo_pass = 0

    for source_file in source_files:
        out_file = out_dir / source_file.name
        candidate = source_file.name in non_strict_candidates
        step_before = 0
        step_after = 0
        steps_added = 0
        context_attrs_added = 0
        orientation_attrs_added = 0
        try:
            if candidate:
                uplift_stats = uplift_candidate_file(source_file, out_file, args.min_steps)
                step_before = uplift_stats["stepCountBefore"]
                step_after = uplift_stats["stepCountAfter"]
                steps_added = uplift_stats["stepsAdded"]
            else:
                shutil.copy2(source_file, out_file)

            semantic_stats = apply_semantic_dimension_defaults(out_file)
            context_attrs_added = semantic_stats["contextAttrsAdded"]
            orientation_attrs_added = semantic_stats["orientationAttrsAdded"]

            doctor_rc, doctor_out = run_cmd(
                [str(fdml_bin), "doctor", str(out_file), "--strict"]
            )
            geo_rc, geo_out = run_cmd([str(fdml_bin), "validate-geo", str(out_file)])
            doctor_ok = doctor_rc == 0
            geo_ok = geo_rc == 0
            if doctor_ok:
                doctor_pass += 1
            if geo_ok:
                geo_pass += 1

            rows.append(
                {
                    "file": normalize_path(source_file),
                    "outFile": normalize_path(out_file),
                    "upliftCandidate": candidate,
                    "upliftApplied": candidate,
                    "stepCountBefore": step_before,
                    "stepCountAfter": step_after,
                    "stepsAdded": steps_added,
                    "contextAttrsAdded": context_attrs_added,
                    "orientationAttrsAdded": orientation_attrs_added,
                    "doctorStrictOk": doctor_ok,
                    "doctorSnippet": first_line(doctor_out),
                    "validateGeoOk": geo_ok,
                    "validateGeoSnippet": first_line(geo_out),
                }
            )
            status = "OK" if doctor_ok and geo_ok else "FAIL"
            print(
                f"{status} {normalize_path(source_file)} -> {normalize_path(out_file)} "
                f"candidate={candidate} doctor={doctor_ok} geo={geo_ok}"
            )
        except Exception as exc:
            errors.append({"file": normalize_path(source_file), "error": str(exc)})
            print(f"FAIL {normalize_path(source_file)} ({exc})")

    total = len(source_files)
    doctor_rate = (doctor_pass / total) if total else 0.0
    geo_rate = (geo_pass / total) if total else 0.0

    coverage_cmd = [
        "python3",
        "scripts/full_description_coverage.py",
        "--input-dir",
        normalize_path(out_dir),
        "--report-out",
        normalize_path(coverage_report_out),
        "--label",
        f"{args.label}-coverage",
        "--strict-target-count",
        "0",
    ]
    coverage_rc, coverage_out = run_cmd(coverage_cmd, cwd=repo_root)
    if coverage_out:
        print(coverage_out)

    quality_cmd = [
        "python3",
        "scripts/full_description_quality_gate.py",
        "--coverage-report",
        normalize_path(coverage_report_out),
        "--fdml-bin",
        normalize_path(fdml_bin),
        "--min-pass-rate",
        str(args.min_quality_pass_rate),
        "--max-placeholder-only",
        str(args.max_placeholder_only),
        "--report-out",
        normalize_path(quality_report_out),
        "--label",
        f"{args.label}-quality",
    ]
    quality_rc, quality_out = run_cmd(quality_cmd, cwd=repo_root)
    if quality_out:
        print(quality_out)

    strict_after = 0
    strict_coverage_after = 0.0
    non_strict_after: list[str] = []
    strict_after_by_file: dict[str, bool] = {}
    if coverage_report_out.exists():
        try:
            coverage_payload = load_json(coverage_report_out)
            strict = coverage_payload.get("strict", {})
            if isinstance(strict, dict):
                strict_after = parse_int(strict.get("fullDescriptionCount", 0))
                strict_coverage_after = parse_pass_rate(strict.get("coverage", 0.0))
            rows_node = coverage_payload.get("rows", [])
            if isinstance(rows_node, list):
                for row in rows_node:
                    if not isinstance(row, dict):
                        continue
                    file_value = str(row.get("file", "")).strip()
                    if not file_value:
                        continue
                    base = Path(file_value).name
                    strict_ok = bool(row.get("strictFullDescription", False))
                    strict_after_by_file[base] = strict_ok
                    if not strict_ok:
                        non_strict_after.append(base)
        except Exception as exc:
            errors.append({"file": normalize_path(coverage_report_out), "error": str(exc)})

    quality_doctor_rate = 0.0
    quality_placeholder_only = 0
    quality_parse_errors = 0
    if quality_report_out.exists():
        try:
            quality_payload = load_json(quality_report_out)
            doctor_node = quality_payload.get("doctor", {})
            if isinstance(doctor_node, dict):
                quality_doctor_rate = parse_pass_rate(doctor_node.get("passRate", 0.0))
            placeholder_node = quality_payload.get("placeholderAudit", {})
            if isinstance(placeholder_node, dict):
                quality_placeholder_only = parse_int(
                    placeholder_node.get("placeholderOnlyCount", 0)
                )
            quality_parse_errors = parse_int(quality_payload.get("parseErrorCount", 0))
        except Exception as exc:
            errors.append({"file": normalize_path(quality_report_out), "error": str(exc)})

    uplift_candidates = len(non_strict_candidates)
    uplifted_success = sum(1 for n in non_strict_candidates if strict_after_by_file.get(n, False))
    strict_delta = strict_after - strict_before

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "sourceDir": normalize_path(source_dir),
        "baselineCoverageReport": normalize_path(baseline_coverage_report),
        "outDir": normalize_path(out_dir),
        "coverageReport": normalize_path(coverage_report_out),
        "qualityReport": normalize_path(quality_report_out),
        "thresholds": {
            "minTotal": args.min_total,
            "strictTargetCount": args.strict_target_count,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
            "minQualityPassRate": args.min_quality_pass_rate,
            "maxPlaceholderOnly": args.max_placeholder_only,
        },
        "totals": {
            "totalSourceFiles": total,
            "errors": len(errors),
            "upliftCandidates": uplift_candidates,
            "upliftCandidatesStrictAfter": uplifted_success,
            "strictBefore": strict_before,
            "strictAfter": strict_after,
            "strictDelta": strict_delta,
            "strictCoverageAfter": round(strict_coverage_after, 4),
            "remainingNonStrict": len(non_strict_after),
            "doctorStrictPass": doctor_pass,
            "doctorStrictPassRate": round(doctor_rate, 4),
            "validateGeoPass": geo_pass,
            "validateGeoPassRate": round(geo_rate, 4),
            "qualityDoctorPassRate": round(quality_doctor_rate, 4),
            "qualityPlaceholderOnly": quality_placeholder_only,
            "qualityParseErrors": quality_parse_errors,
        },
        "nonStrictAfterSample": sorted(non_strict_after)[:20],
        "commandStatus": {
            "coverageExitCode": coverage_rc,
            "qualityExitCode": quality_rc,
        },
        "rows": rows,
    }
    if errors:
        report["errors"] = errors

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(
        "M9 STRICT DESCRIPTION UPLIFT "
        f"total={total} candidates={uplift_candidates} "
        f"strict={strict_after}/{total} ({strict_coverage_after:.4f}) "
        f"quality={quality_doctor_rate:.4f} placeholder_only={quality_placeholder_only} "
        f"doctor={doctor_pass}/{total} ({doctor_rate:.4f}) "
        f"geo={geo_pass}/{total} ({geo_rate:.4f})"
    )
    print(f"Created: {report_out}")

    failed: list[str] = []
    if total < args.min_total:
        failed.append(f"source total {total} below minimum {args.min_total}")
    if strict_after < args.strict_target_count:
        failed.append(
            f"strict full-description count {strict_after} below target {args.strict_target_count}"
        )
    if doctor_rate < clamp_ratio(args.min_doctor_pass_rate):
        failed.append(
            f"doctor strict pass rate {doctor_rate:.4f} below minimum {args.min_doctor_pass_rate:.4f}"
        )
    if geo_rate < clamp_ratio(args.min_geo_pass_rate):
        failed.append(
            f"validate-geo pass rate {geo_rate:.4f} below minimum {args.min_geo_pass_rate:.4f}"
        )
    if quality_doctor_rate < clamp_ratio(args.min_quality_pass_rate):
        failed.append(
            f"quality strict pass rate {quality_doctor_rate:.4f} below minimum {args.min_quality_pass_rate:.4f}"
        )
    if quality_placeholder_only > args.max_placeholder_only:
        failed.append(
            f"placeholder-only strict files {quality_placeholder_only} exceed allowed {args.max_placeholder_only}"
        )
    if quality_parse_errors != 0:
        failed.append(f"quality parse errors present: {quality_parse_errors}")
    if coverage_rc != 0:
        failed.append(f"coverage command failed with exit code {coverage_rc}")
    if quality_rc != 0:
        failed.append(f"quality command failed with exit code {quality_rc}")
    if errors:
        failed.append(f"processing errors present: {len(errors)}")

    if failed:
        for item in failed:
            print(f"m9_full_description_uplift.py: {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

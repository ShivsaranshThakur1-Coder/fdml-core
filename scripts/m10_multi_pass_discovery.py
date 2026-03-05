#!/usr/bin/env python3
"""Run corpus-wide multi-pass OpenAI-assisted discovery and emit PRG-101 ledger report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field


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

PASS_PROMPTS = {
    1: "Pass 1: broad extraction. Capture core reusable dimensions and constraints with evidence.",
    2: "Pass 2: gap-focused extraction. Resolve checklist gaps and uncertain dimensions from prior passes.",
    3: "Pass 3: adversarial extraction. Search for missed dimensions and edge-case constraints that are still evidence-backed.",
}


class ChecklistItem(BaseModel):
    dimension: str = Field(description="One of the required checklist dimension ids.")
    status: str = Field(description="present|absent|uncertain")
    rationale: str
    confidence: float
    evidence_line_ids: list[str] = Field(default_factory=list)


class ParameterCandidate(BaseModel):
    name: str
    group: str
    description: str
    confidence: float
    evidence_line_ids: list[str] = Field(default_factory=list)


class ValidatorCandidate(BaseModel):
    name: str
    rule_type: str
    enforce_layer: str
    description: str
    confidence: float
    evidence_line_ids: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    checklist: list[ChecklistItem]
    parameter_candidates: list[ParameterCandidate]
    validator_candidates: list[ValidatorCandidate]
    unresolved_notes: list[str] = Field(default_factory=list)


@dataclass
class SourceContext:
    path: Path
    source_text: str
    line_map: dict[str, tuple[int, int, str]]
    hash: str


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Run M10 multi-pass OpenAI discovery ledger over promoted corpus."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m9_full_description_uplift/run1",
        help="directory containing promoted .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m10_discovery/run1",
        help="output directory for multi-pass artifacts",
    )
    ap.add_argument(
        "--report-out",
        default="out/m10_discovery/run1/discovery_report.json",
        help="discovery report output path",
    )
    ap.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="OpenAI model for extraction",
    )
    ap.add_argument(
        "--passes",
        type=int,
        default=3,
        help="number of discovery passes (>=3 recommended for saturation checks)",
    )
    ap.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="optional limit for files processed (0 means all)",
    )
    ap.add_argument(
        "--max-step-lines",
        type=int,
        default=140,
        help="maximum step lines embedded per file prompt",
    )
    ap.add_argument(
        "--max-section-lines",
        type=int,
        default=30,
        help="maximum section lines embedded per file prompt",
    )
    ap.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=120.0,
        help="timeout for a single model request",
    )
    ap.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="retries for transient API failures",
    )
    ap.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=3.0,
        help="base retry backoff in seconds",
    )
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="minimum confidence retained in candidate union",
    )
    ap.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="environment variable containing API key",
    )
    ap.add_argument(
        "--label",
        default="m10-multi-pass-discovery",
        help="report label",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m10_multi_pass_discovery.py: {msg}", file=sys.stderr)
    return 2


def to_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # pydantic v2
    if hasattr(obj, "dict"):
        return obj.dict()  # pydantic v1
    if isinstance(obj, dict):
        return obj
    raise RuntimeError(f"unsupported parsed object type: {type(obj)!r}")


def clamp_confidence(value: Any, default: float = 0.6) -> float:
    try:
        v = float(value)
    except Exception:
        return default
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def norm_key(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower())
    return s.strip("_")


def safe_status(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"present", "absent", "uncertain"}:
        return v
    return "uncertain"


def pick_fdml_files(input_dir: Path, max_files: int) -> list[Path]:
    files = sorted(input_dir.glob("*.fdml.xml"))
    if max_files > 0:
        files = files[:max_files]
    return files


def primary_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    if el.text and el.text.strip():
        return el.text.strip()
    return ""


def build_source_context(
    fdml_file: Path, max_step_lines: int, max_section_lines: int
) -> SourceContext:
    root = ET.parse(fdml_file).getroot()
    lines: list[str] = []

    def add(line: str) -> None:
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)

    add(f"file={fdml_file.name}")
    add(f"version={root.get('version', '').strip() or 'unknown'}")

    title = primary_text(root.find("./meta/title"))
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
        notes = (mgeo_form.get("notes") or "").strip()
        if kind:
            add(f"meta.geometry.formation.kind={kind}")
        if woman_side:
            add(f"meta.geometry.formation.womanSide={woman_side}")
        if notes:
            add(f"meta.geometry.formation.notes={notes}")

    hold = root.find("./meta/geometry/hold")
    if hold is not None and hold.get("kind"):
        add(f"meta.geometry.hold.kind={hold.get('kind','').strip()}")

    dancers = root.find("./meta/geometry/dancers")
    if dancers is not None and dancers.get("count"):
        add(f"meta.geometry.dancers.count={dancers.get('count','').strip()}")

    role_ids = [
        (role.get("id") or "").strip()
        for role in root.findall("./meta/geometry/roles/role")
        if (role.get("id") or "").strip()
    ]
    if role_ids:
        add(f"meta.geometry.roles={','.join(role_ids)}")

    # Body geometry topology declarations.
    circle_role = root.find("./body/geometry/circle/order")
    if circle_role is not None:
        role = (circle_role.get("role") or "").strip()
        if role:
            add(f"body.geometry.circle.order.role={role}")
        slots = [
            (slot.get("who") or "").strip()
            for slot in circle_role.findall("./slot")
            if (slot.get("who") or "").strip()
        ]
        if slots:
            add(f"body.geometry.circle.order.slots={','.join(slots)}")

    for line in root.findall("./body/geometry/twoLines/line"):
        lid = (line.get("id") or "").strip()
        role = (line.get("role") or "").strip()
        if lid or role:
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
                if phase:
                    add(f"body.geometry.line.order phase={phase} slots={','.join(slots)}")
                else:
                    add(f"body.geometry.line.order slots={','.join(slots)}")

    for pair in root.findall("./body/geometry/couples/pair"):
        a = (pair.get("a") or "").strip()
        b = (pair.get("b") or "").strip()
        rel = (pair.get("relationship") or "").strip()
        if a and b:
            if rel:
                add(f"body.geometry.couples.pair a={a} b={b} relationship={rel}")
            else:
                add(f"body.geometry.couples.pair a={a} b={b}")

    # Sections/notes/setup text.
    section_count = 0
    for section in root.findall("./body/section"):
        if section_count >= max_section_lines:
            break
        stype = (section.get("type") or "").strip()
        sid = (section.get("id") or "").strip()
        text_bits = []
        if section.text and section.text.strip():
            text_bits.append(section.text.strip())
        for p in section.findall("./p"):
            if p.text and p.text.strip():
                text_bits.append(p.text.strip())
        text = re.sub(r"\s+", " ", " ".join(text_bits)).strip()
        if text:
            add(f"body.section type={stype} id={sid} text={text}")
            section_count += 1

    # Figures and steps.
    step_count = 0
    for fig in root.findall(".//figure"):
        fig_id = (fig.get("id") or "").strip()
        fig_name = (fig.get("name") or "").strip()
        fig_form = (fig.get("formation") or "").strip()
        add(f"figure id={fig_id} name={fig_name} formation={fig_form}")
        for step in fig.findall("./step"):
            if step_count >= max_step_lines:
                break
            who = (step.get("who") or "").strip()
            action = (step.get("action") or "").strip()
            beats = (step.get("beats") or "").strip()
            direction = (step.get("direction") or "").strip()
            facing = (step.get("facing") or "").strip()
            count = (step.get("count") or "").strip()
            add(
                "step "
                f"figure={fig_id} who={who} beats={beats} count={count} "
                f"direction={direction} facing={facing} action={action}"
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
                    f"figure={fig_id} kind={kind} who={p_who} a={p_a} b={p_b} "
                    f"frame={p_frame} dir={p_dir} axis={p_axis} relation={p_rel} "
                    f"delta={p_delta} preserveOrder={p_pres}"
                )
            step_count += 1
        if step_count >= max_step_lines:
            break

    # Sequence usage.
    for seq in root.findall("./body/sequence"):
        sid = (seq.get("id") or "").strip()
        sname = (seq.get("name") or "").strip()
        add(f"sequence id={sid} name={sname}")
        for use in seq.findall("./use"):
            fig_ref = (use.get("figure") or "").strip()
            part_ref = (use.get("part") or "").strip()
            rep = (use.get("repeat") or "").strip()
            add(f"sequence.use sequence={sid} figure={fig_ref} part={part_ref} repeat={rep}")

    prefixed_lines: list[str] = []
    line_map: dict[str, tuple[int, int, str]] = {}
    cursor = 0
    for i, line in enumerate(lines, start=1):
        lid = f"L{i:04d}"
        full = f"{lid}: {line}"
        prefixed_lines.append(full)
    source_text = "\n".join(prefixed_lines)

    for full in prefixed_lines:
        lid, _, text = full.partition(": ")
        start = source_text.find(full, cursor)
        if start < 0:
            start = source_text.find(full)
        end = start + len(full)
        line_map[lid] = (start, end, text)
        cursor = end

    return SourceContext(
        path=fdml_file,
        source_text=source_text,
        line_map=line_map,
        hash=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    )


def validate_line_ids(ids: list[str], line_map: dict[str, tuple[int, int, str]]) -> list[str]:
    out = []
    for lid in ids:
        lid = (lid or "").strip()
        if lid in line_map and lid not in out:
            out.append(lid)
    return out


def evidence_from_line_ids(
    ids: list[str], line_map: dict[str, tuple[int, int, str]]
) -> tuple[dict[str, Any], list[str]]:
    valid = validate_line_ids(ids, line_map)
    if not valid:
        return {"text": "", "span": {"start": -1, "end": -1}, "lineIds": []}, []
    lid = valid[0]
    start, end, text = line_map[lid]
    return {"text": text, "span": {"start": start, "end": end}, "lineIds": valid}, valid


def call_model(
    client: OpenAI,
    model: str,
    source: SourceContext,
    pass_index: int,
    previous_summary: dict[str, Any],
    max_retries: int,
    retry_backoff_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    sys_prompt = (
        "You are extracting exhaustive folk dance description and validation dimensions from FDML evidence lines. "
        "Use only provided line ids. Do not invent evidence."
    )

    prior_dims = previous_summary.get("unresolvedDimensions", [])
    prior_param_keys = previous_summary.get("knownParameterKeys", [])
    prior_rule_keys = previous_summary.get("knownValidatorKeys", [])

    required_dims = ", ".join(CHECKLIST_DIMENSIONS)
    pass_goal = PASS_PROMPTS.get(pass_index, PASS_PROMPTS[3])

    user_prompt = (
        f"{pass_goal}\n\n"
        "Required checklist dimensions (must all be included exactly once in checklist[]):\n"
        f"{required_dims}\n\n"
        "Output rules:\n"
        "- checklist[].status must be one of: present, absent, uncertain.\n"
        "- For present/uncertain checklist items, include at least one evidence_line_ids entry.\n"
        "- For absent checklist items, evidence_line_ids may be empty.\n"
        "- parameter_candidates and validator_candidates must be reusable/generalized, not dance-title specific.\n"
        "- Every candidate must include evidence_line_ids with at least one valid line id.\n"
        "- confidence values must be in [0,1].\n\n"
        f"Prior unresolved dimensions for this file: {prior_dims}\n"
        f"Known parameter keys already discovered corpus-wide (avoid trivial duplicates): {prior_param_keys}\n"
        f"Known validator keys already discovered corpus-wide (avoid trivial duplicates): {prior_rule_keys}\n\n"
        "FDML evidence lines:\n"
        f"{source.source_text}"
    )

    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=ExtractionResult,
                timeout=timeout_seconds,
            )
            parsed = getattr(resp, "output_parsed", None)
            if parsed is None:
                raise RuntimeError("empty parsed response")
            return to_dict(parsed)
        except Exception as exc:
            last_err = exc
            if attempt >= max_retries:
                break
            sleep_s = retry_backoff_seconds * attempt
            print(
                f"retry pass={pass_index} file={source.path.name} attempt={attempt}/{max_retries} sleep={sleep_s:.1f}s err={exc}",
                file=sys.stderr,
            )
            time.sleep(sleep_s)
    raise RuntimeError(
        f"OpenAI extraction failed for {source.path.name} pass={pass_index}: {last_err}"
    )


def merge_dimension_status(existing: str, new: str) -> str:
    if existing == "present" or new == "present":
        return "present"
    if existing == "absent" and new == "absent":
        return "absent"
    if existing == "absent" and new == "uncertain":
        return "uncertain"
    if existing == "uncertain" and new == "absent":
        return "uncertain"
    if existing == "uncertain" and new == "uncertain":
        return "uncertain"
    if existing == "unknown":
        return new
    if new == "unknown":
        return existing
    return "uncertain"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    if args.passes <= 0:
        return fail("--passes must be > 0")
    if args.max_files < 0:
        return fail("--max-files must be >= 0")
    if args.max_step_lines <= 0:
        return fail("--max-step-lines must be > 0")
    if args.max_section_lines <= 0:
        return fail("--max-section-lines must be > 0")
    if args.max_retries <= 0:
        return fail("--max-retries must be > 0")
    if args.request_timeout_seconds <= 0:
        return fail("--request-timeout-seconds must be > 0")
    if not (0.0 <= args.min_confidence <= 1.0):
        return fail("--min-confidence must be between 0 and 1")

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    report_out = Path(args.report_out)
    if not input_dir.is_dir():
        return fail(f"input dir not found: {input_dir}")

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        return fail(f"missing API key env var: {args.api_key_env}")

    files = pick_fdml_files(input_dir, args.max_files)
    if not files:
        return fail(f"no .fdml.xml files found under: {input_dir}")

    print(
        f"M10 DISCOVERY START files={len(files)} passes={args.passes} model={args.model} out={out_dir}",
        file=sys.stderr,
    )

    contexts: list[SourceContext] = []
    for f in files:
        contexts.append(
            build_source_context(
                f,
                max_step_lines=args.max_step_lines,
                max_section_lines=args.max_section_lines,
            )
        )

    client = OpenAI(api_key=api_key)

    pass_summaries: list[dict[str, Any]] = []
    all_pass_rows: list[dict[str, Any]] = []
    per_file_history: dict[str, list[dict[str, Any]]] = {}

    parameter_union: dict[str, dict[str, Any]] = {}
    validator_union: dict[str, dict[str, Any]] = {}
    prior_param_key_order: list[str] = []
    prior_validator_key_order: list[str] = []

    for pass_index in range(1, args.passes + 1):
        pass_dir = out_dir / f"pass_{pass_index}"
        pass_dir.mkdir(parents=True, exist_ok=True)
        rows_this_pass: list[dict[str, Any]] = []

        param_before = len(parameter_union)
        val_before = len(validator_union)

        checklist_present = 0
        checklist_absent = 0
        checklist_uncertain = 0

        for idx, source in enumerate(contexts, start=1):
            previous_file_rows = per_file_history.get(source.path.name, [])
            unresolved_dims = []
            if previous_file_rows:
                latest = previous_file_rows[-1]
                for item in latest.get("checklist", []):
                    if item.get("status") == "uncertain":
                        unresolved_dims.append(item.get("dimension"))

            prev_summary = {
                "unresolvedDimensions": unresolved_dims[:12],
                "knownParameterKeys": prior_param_key_order[-40:],
                "knownValidatorKeys": prior_validator_key_order[-40:],
            }

            print(
                f"pass={pass_index}/{args.passes} file={idx}/{len(contexts)} name={source.path.name}",
                file=sys.stderr,
            )

            started = time.time()
            parsed = call_model(
                client=client,
                model=args.model,
                source=source,
                pass_index=pass_index,
                previous_summary=prev_summary,
                max_retries=args.max_retries,
                retry_backoff_seconds=args.retry_backoff_seconds,
                timeout_seconds=args.request_timeout_seconds,
            )
            elapsed_ms = int((time.time() - started) * 1000.0)

            checklist_raw = parsed.get("checklist", [])
            if not isinstance(checklist_raw, list):
                checklist_raw = []
            check_by_dim: dict[str, dict[str, Any]] = {}
            for item in checklist_raw:
                if not isinstance(item, dict):
                    continue
                dim = str(item.get("dimension", "")).strip()
                if not dim:
                    continue
                status = safe_status(str(item.get("status", "")))
                confidence = clamp_confidence(item.get("confidence"), 0.6)
                line_ids = validate_line_ids(item.get("evidence_line_ids") or [], source.line_map)
                evidence, _ = evidence_from_line_ids(line_ids, source.line_map)
                check_by_dim[dim] = {
                    "dimension": dim,
                    "status": status,
                    "confidence": confidence,
                    "rationale": str(item.get("rationale", "")).strip(),
                    "evidence": evidence,
                }

            checklist_out: list[dict[str, Any]] = []
            for dim in CHECKLIST_DIMENSIONS:
                item = check_by_dim.get(dim)
                if item is None:
                    item = {
                        "dimension": dim,
                        "status": "uncertain",
                        "confidence": 0.5,
                        "rationale": "missing_from_model_output",
                        "evidence": {"text": "", "span": {"start": -1, "end": -1}, "lineIds": []},
                    }
                status = item["status"]
                if status == "present":
                    checklist_present += 1
                elif status == "absent":
                    checklist_absent += 1
                else:
                    checklist_uncertain += 1
                checklist_out.append(item)

            params_raw = parsed.get("parameter_candidates", [])
            if not isinstance(params_raw, list):
                params_raw = []
            params_out: list[dict[str, Any]] = []
            for p in params_raw:
                if not isinstance(p, dict):
                    continue
                name = str(p.get("name", "")).strip()
                group = str(p.get("group", "")).strip().lower() or "other"
                if not name:
                    continue
                confidence = clamp_confidence(p.get("confidence"), 0.6)
                if confidence < args.min_confidence:
                    continue
                evidence, valid_ids = evidence_from_line_ids(p.get("evidence_line_ids") or [], source.line_map)
                if not valid_ids:
                    continue
                key = f"{group}:{norm_key(name)}"
                row = {
                    "key": key,
                    "name": name,
                    "group": group,
                    "description": str(p.get("description", "")).strip(),
                    "confidence": confidence,
                    "file": source.path.as_posix(),
                    "evidence": evidence,
                }
                params_out.append(row)
                if key not in parameter_union:
                    parameter_union[key] = row
                    prior_param_key_order.append(key)

            vals_raw = parsed.get("validator_candidates", [])
            if not isinstance(vals_raw, list):
                vals_raw = []
            vals_out: list[dict[str, Any]] = []
            for v in vals_raw:
                if not isinstance(v, dict):
                    continue
                name = str(v.get("name", "")).strip()
                rule_type = str(v.get("rule_type", "")).strip().lower() or "consistency"
                layer = str(v.get("enforce_layer", "")).strip().lower() or "java"
                if not name:
                    continue
                confidence = clamp_confidence(v.get("confidence"), 0.6)
                if confidence < args.min_confidence:
                    continue
                evidence, valid_ids = evidence_from_line_ids(v.get("evidence_line_ids") or [], source.line_map)
                if not valid_ids:
                    continue
                key = f"{rule_type}:{norm_key(name)}"
                row = {
                    "key": key,
                    "name": name,
                    "ruleType": rule_type,
                    "enforceLayer": layer,
                    "description": str(v.get("description", "")).strip(),
                    "confidence": confidence,
                    "file": source.path.as_posix(),
                    "evidence": evidence,
                }
                vals_out.append(row)
                if key not in validator_union:
                    validator_union[key] = row
                    prior_validator_key_order.append(key)

            unresolved_notes = parsed.get("unresolved_notes", [])
            if not isinstance(unresolved_notes, list):
                unresolved_notes = []
            unresolved_notes = [str(x).strip() for x in unresolved_notes if str(x).strip()]

            file_row = {
                "file": source.path.as_posix(),
                "fileName": source.path.name,
                "sourceHash": source.hash,
                "pass": pass_index,
                "durationMs": elapsed_ms,
                "checklist": checklist_out,
                "parameterCandidates": params_out,
                "validatorCandidates": vals_out,
                "unresolvedNotes": unresolved_notes,
            }
            rows_this_pass.append(file_row)
            all_pass_rows.append(file_row)

            per_file_history.setdefault(source.path.name, []).append(file_row)
            write_json(pass_dir / f"{source.path.stem}.json", file_row)

        new_params = max(0, len(parameter_union) - param_before)
        new_vals = max(0, len(validator_union) - val_before)
        existing_total = param_before + val_before
        growth_ratio = float(new_params + new_vals) / float(existing_total if existing_total > 0 else 1)

        pass_summary = {
            "id": f"pass-{pass_index}",
            "processedFiles": len(rows_this_pass),
            "newParameterCandidates": new_params,
            "newValidatorCandidates": new_vals,
            "uniqueParameterTotal": len(parameter_union),
            "uniqueValidatorTotal": len(validator_union),
            "growthRatio": round(growth_ratio, 6),
            "checklistPresent": checklist_present,
            "checklistAbsent": checklist_absent,
            "checklistUncertain": checklist_uncertain,
        }
        pass_summaries.append(pass_summary)
        write_json(pass_dir / "_summary.json", pass_summary)

        print(
            "pass_complete "
            f"pass={pass_index} processed={len(rows_this_pass)} "
            f"new_params={new_params} new_rules={new_vals} growth={growth_ratio:.6f}",
            file=sys.stderr,
        )

    # Build final per-file resolution by merging across passes.
    per_file_resolution: list[dict[str, Any]] = []
    unresolved_files = 0
    total_uncertain = 0
    for source in contexts:
        hist = per_file_history.get(source.path.name, [])
        dim_state: dict[str, dict[str, Any]] = {
            d: {
                "dimension": d,
                "status": "unknown",
                "confidence": 0.0,
                "rationale": "",
                "evidence": {"text": "", "span": {"start": -1, "end": -1}, "lineIds": []},
            }
            for d in CHECKLIST_DIMENSIONS
        }

        for row in hist:
            for item in row.get("checklist", []):
                if not isinstance(item, dict):
                    continue
                dim = str(item.get("dimension", "")).strip()
                if dim not in dim_state:
                    continue
                old = dim_state[dim]
                merged = merge_dimension_status(old.get("status", "unknown"), item.get("status", "unknown"))
                if merged != old.get("status"):
                    dim_state[dim] = item
                    dim_state[dim]["status"] = merged
                elif clamp_confidence(item.get("confidence"), 0.0) > clamp_confidence(old.get("confidence"), 0.0):
                    dim_state[dim] = item
                    dim_state[dim]["status"] = merged

        resolved = []
        unresolved_count = 0
        for dim in CHECKLIST_DIMENSIONS:
            item = dim_state[dim]
            status = item.get("status", "unknown")
            if status == "unknown":
                status = "uncertain"
            item["status"] = status
            if status == "uncertain":
                unresolved_count += 1
            resolved.append(item)

        if unresolved_count > 0:
            unresolved_files += 1
        total_uncertain += unresolved_count
        per_file_resolution.append(
            {
                "file": source.path.as_posix(),
                "fileName": source.path.name,
                "unresolvedCount": unresolved_count,
                "checklist": resolved,
            }
        )

    checklist_total = len(contexts) * len(CHECKLIST_DIMENSIONS)
    checklist_missing = 0  # Missing means dimension not attempted; model output is normalized to full checklist.
    checklist_uncertain = total_uncertain

    growth_values = [float(p.get("growthRatio", 0.0)) for p in pass_summaries]
    threshold = 0.01
    tail_consecutive = 0
    for value in reversed(growth_values):
        if value <= threshold:
            tail_consecutive += 1
        else:
            break

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "model": args.model,
        "inputDir": input_dir.as_posix(),
        "outDir": out_dir.as_posix(),
        "totals": {
            "sourceFiles": len(contexts),
            "processedFiles": len(contexts),
            "checklistItemsTotal": checklist_total,
            "checklistMissing": checklist_missing,
            "checklistUncertain": checklist_uncertain,
            "parameterCandidateUniqueTotal": len(parameter_union),
            "validatorCandidateUniqueTotal": len(validator_union),
        },
        "passes": pass_summaries,
        "saturation": {
            "thresholdRatio": threshold,
            "latestGrowthRatios": growth_values[-2:] if len(growth_values) >= 2 else growth_values,
            "consecutivePassesUnderThreshold": tail_consecutive,
        },
        "perFileChecklistResolution": per_file_resolution,
        "candidateInventory": {
            "parameter": sorted(parameter_union.values(), key=lambda x: x.get("key", "")),
            "validator": sorted(validator_union.values(), key=lambda x: x.get("key", "")),
        },
        "coverageGapsPreview": {
            "unresolvedFiles": unresolved_files,
            "rows": [
                {
                    "file": row["file"],
                    "unresolvedCount": row["unresolvedCount"],
                }
                for row in per_file_resolution
            ],
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "candidate_inventory.json", report["candidateInventory"])
    write_json(out_dir / "coverage_gaps_preview.json", report["coverageGapsPreview"])
    write_json(report_out, report)

    print(
        "M10 DISCOVERY DONE "
        f"files={len(contexts)} passes={args.passes} "
        f"params={len(parameter_union)} validators={len(validator_union)} "
        f"uncertain={checklist_uncertain}/{checklist_total}",
        file=sys.stderr,
    )
    print(f"Created: {report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run unified M11 validator stack across full promoted corpus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


FORMATION_REQUIRED_CODES = {"missing_formation_kind"}
TIMING_ALIGN_CODES = {"missing_meter", "bad_meter_format", "off_meter_figure"}
COUPLE_RELPOS_CODES = {
    "missing_partner_pairing",
    "missing_relpos_evidence",
    "relpos_contradiction",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate promoted corpus using one M11 rule stack derived from M10 validator candidates."
    )
    ap.add_argument(
        "--input-dir",
        default="out/m9_full_description_uplift/run1",
        help="directory containing promoted .fdml.xml files",
    )
    ap.add_argument(
        "--validator-candidates",
        default="out/m10_validator_candidates.json",
        help="path to M10 validator candidate report",
    )
    ap.add_argument(
        "--contract-promotion",
        default="out/m11_contract_promotion.json",
        help="optional path to M11 contract promotion report",
    )
    ap.add_argument(
        "--fdml-bin",
        default="bin/fdml",
        help="fdml executable path",
    )
    ap.add_argument(
        "--report-out",
        default="out/m11_validator_unified_report.json",
        help="output path for unified validator report",
    )
    ap.add_argument(
        "--label",
        default="m11-validator-unified",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum corpus file count required",
    )
    ap.add_argument(
        "--min-rules",
        type=int,
        default=3,
        help="minimum recognized validator rules required",
    )
    ap.add_argument(
        "--min-couple-woman-side-coverage",
        type=float,
        default=1.0,
        help="minimum coverage ratio for womanSide in v1.2 couple files [0,1]",
    )
    ap.add_argument(
        "--min-couple-relpos-coverage",
        type=float,
        default=1.0,
        help="minimum coverage ratio for man/woman relpos evidence in v1.2 couple files [0,1]",
    )
    ap.add_argument(
        "--min-meter-coverage",
        type=float,
        default=1.0,
        help="minimum coverage ratio for meter declaration in source files [0,1]",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m11_validator_unified.py: {msg}", file=sys.stderr)
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


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
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


def run_json(cmd: list[str]) -> tuple[int, dict[str, Any], str]:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = (proc.stdout or "").strip()
    payload: dict[str, Any] = {}
    if output:
        try:
            parsed = json.loads(output)
        except Exception:
            parsed = {}
        if isinstance(parsed, dict):
            payload = parsed
    return proc.returncode, payload, output


def has_evidence(row: dict[str, Any]) -> bool:
    file_value = str(row.get("file") or "").strip()
    evidence = as_dict(row.get("evidence"))
    text = str(evidence.get("text") or "").strip()
    span = as_dict(evidence.get("span"))
    start = span.get("start")
    end = span.get("end")
    return bool(
        file_value
        and text
        and isinstance(start, int)
        and isinstance(end, int)
        and start >= 0
        and end >= start
    )


def collect_file_meta(files: list[Path]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for file_path in files:
        root = ET.parse(file_path).getroot()
        version = str(root.get("version") or "").strip()
        meter_value = str(
            (root.find("./meta/meter").get("value") if root.find("./meta/meter") is not None else "")
            or ""
        ).strip()
        tempo_bpm = str(
            (root.find("./meta/tempo").get("bpm") if root.find("./meta/tempo") is not None else "")
            or ""
        ).strip()
        origin_country = str(
            (root.find("./meta/origin").get("country") if root.find("./meta/origin") is not None else "")
            or ""
        ).strip()
        origin_region = str(
            (root.find("./meta/origin").get("region") if root.find("./meta/origin") is not None else "")
            or ""
        ).strip()
        type_genre = str(
            (root.find("./meta/type").get("genre") if root.find("./meta/type") is not None else "")
            or ""
        ).strip()
        type_style = str(
            (root.find("./meta/type").get("style") if root.find("./meta/type") is not None else "")
            or ""
        ).strip()
        formation = root.find("./meta/geometry/formation")
        formation_kind = ""
        woman_side = ""
        if formation is not None:
            formation_kind = str(formation.get("kind") or "").strip()
            woman_side = str(formation.get("womanSide") or "").strip()

        steps = root.findall(".//figure/step")
        has_step_direction = bool(steps) and all(str(step.get("direction") or "").strip() for step in steps)
        has_step_facing = bool(steps) and all(str(step.get("facing") or "").strip() for step in steps)
        has_step_count = bool(steps) and all(str(step.get("count") or "").strip() for step in steps)
        has_step_beats_positive = False
        if steps:
            beats_ok = True
            for step in steps:
                beats_text = str(step.get("beats") or "").strip()
                if not beats_text:
                    beats_ok = False
                    break
                try:
                    beats_value = int(beats_text)
                except Exception:
                    beats_ok = False
                    break
                if beats_value <= 0:
                    beats_ok = False
                    break
            has_step_beats_positive = beats_ok

        couple_pair_relationship = False
        role_ids = {
            str(r.get("id") or "").strip()
            for r in root.findall("./meta/geometry/roles/role")
            if str(r.get("id") or "").strip()
        }
        has_man_role = "man" in role_ids
        has_woman_role = "woman" in role_ids
        has_partner_pair = False
        for pair in root.findall("./body/geometry/couples/pair"):
            a = str(pair.get("a") or "").strip()
            b = str(pair.get("b") or "").strip()
            relationship = str(pair.get("relationship") or "").strip()
            if relationship:
                couple_pair_relationship = True
            if (a == "man" and b == "woman") or (a == "woman" and b == "man"):
                has_partner_pair = True
                break
        has_relpos_man_woman = False
        for prim in root.findall(".//step/geo/primitive"):
            kind = str(prim.get("kind") or "").strip()
            a = str(prim.get("a") or "").strip()
            b = str(prim.get("b") or "").strip()
            relation = str(prim.get("relation") or "").strip()
            if kind != "relpos":
                continue
            if relation not in {"leftOf", "rightOf"}:
                continue
            if (a == "man" and b == "woman") or (a == "woman" and b == "man"):
                has_relpos_man_woman = True
                break
        out[file_path.resolve().as_posix()] = {
            "version": version,
            "formationKind": formation_kind,
            "womanSide": woman_side,
            "hasWomanSide": woman_side in {"left", "right"},
            "hasMeter": bool(meter_value),
            "hasTempoBpm": bool(tempo_bpm),
            "hasOriginCountry": bool(origin_country),
            "hasOriginRegion": bool(origin_region),
            "hasTypeGenre": bool(type_genre),
            "hasTypeStyle": bool(type_style),
            "hasStepDirection": has_step_direction,
            "hasStepFacing": has_step_facing,
            "hasStepCount": has_step_count,
            "hasStepBeatsPositive": has_step_beats_positive,
            "hasPairRelationship": couple_pair_relationship,
            "hasManRole": has_man_role,
            "hasWomanRole": has_woman_role,
            "hasPartnerPair": has_partner_pair,
            "hasRelposManWoman": has_relpos_man_woman,
        }
    return out


def issue_code_set(value: Any) -> set[str]:
    codes: set[str] = set()
    for item in as_list(value):
        row = as_dict(item)
        code = str(row.get("code") or "").strip()
        if code:
            codes.add(code)
    return codes


def normalize_result_rows(
    rows: list[Any], key_name: str, repo_root: Path
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = as_dict(raw)
        file_value = str(row.get("file") or "").strip()
        if not file_value:
            continue
        key = canonical_path(file_value, repo_root)
        out[key] = row
    return out


def evaluate_rule(
    rule_key: str,
    file_abs: str,
    meta: dict[str, Any],
    geo_row: dict[str, Any],
    timing_row: dict[str, Any],
) -> tuple[bool, bool, list[str]]:
    version = str(meta.get("version") or "")
    formation_kind = str(meta.get("formationKind") or "")
    woman_side = str(meta.get("womanSide") or "")
    has_woman_side = bool(meta.get("hasWomanSide", False))
    has_origin_country = bool(meta.get("hasOriginCountry", False))
    has_origin_region = bool(meta.get("hasOriginRegion", False))
    has_type_genre = bool(meta.get("hasTypeGenre", False))
    has_type_style = bool(meta.get("hasTypeStyle", False))
    has_tempo_bpm = bool(meta.get("hasTempoBpm", False))
    has_step_direction = bool(meta.get("hasStepDirection", False))
    has_step_facing = bool(meta.get("hasStepFacing", False))
    has_step_count = bool(meta.get("hasStepCount", False))
    has_step_beats_positive = bool(meta.get("hasStepBeatsPositive", False))
    has_pair_relationship = bool(meta.get("hasPairRelationship", False))
    has_man_role = bool(meta.get("hasManRole", False))
    has_woman_role = bool(meta.get("hasWomanRole", False))
    has_partner_pair = bool(meta.get("hasPartnerPair", False))
    has_relpos_man_woman = bool(meta.get("hasRelposManWoman", False))
    geo_codes = issue_code_set(geo_row.get("issues"))
    timing_codes = issue_code_set(timing_row.get("issues"))

    if rule_key == "rule:require_formation_kind_for_v12":
        applicable = version == "1.2"
        if not applicable:
            return False, True, []
        fail_codes: set[str] = set()
        if not formation_kind:
            fail_codes.add("missing_formation_kind")
        fail_codes.update(geo_codes.intersection(FORMATION_REQUIRED_CODES))
        return True, len(fail_codes) == 0, sorted(fail_codes)

    if rule_key == "rule:step_beats_align_to_meter":
        applicable = True
        fail_codes = timing_codes.intersection(TIMING_ALIGN_CODES)
        return applicable, len(fail_codes) == 0, sorted(fail_codes)

    if rule_key == "rule:couple_relpos_consistency":
        applicable = version == "1.2" and formation_kind == "couple"
        if not applicable:
            return False, True, []
        fail_codes: set[str] = set()
        if not woman_side:
            fail_codes.add("missing_woman_side_contract")
        elif not has_woman_side:
            fail_codes.add("invalid_woman_side_contract")
        if not (has_man_role and has_woman_role and has_partner_pair):
            fail_codes.add("missing_partner_pairing_contract")
        if not has_relpos_man_woman:
            fail_codes.add("missing_relpos_evidence_contract")
        fail_codes.update(geo_codes.intersection(COUPLE_RELPOS_CODES))
        return True, len(fail_codes) == 0, sorted(fail_codes)

    if rule_key == "rule:origin_country_required":
        applicable = True
        fail_codes = [] if has_origin_country else ["missing_origin_country_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:origin_region_required":
        applicable = True
        fail_codes = [] if has_origin_region else ["missing_origin_region_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:type_genre_required":
        applicable = True
        fail_codes = [] if has_type_genre else ["missing_type_genre_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:type_style_required":
        applicable = True
        fail_codes = [] if has_type_style else ["missing_type_style_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:tempo_bpm_required":
        applicable = True
        fail_codes = [] if has_tempo_bpm else ["missing_tempo_bpm_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:step_direction_required":
        applicable = True
        fail_codes = [] if has_step_direction else ["missing_step_direction_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:step_facing_required":
        applicable = True
        fail_codes = [] if has_step_facing else ["missing_step_facing_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:step_beats_positive":
        applicable = True
        fail_codes = [] if has_step_beats_positive else ["invalid_step_beats_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:step_count_required":
        applicable = True
        fail_codes = [] if has_step_count else ["missing_step_count_contract"]
        return applicable, not fail_codes, fail_codes

    if rule_key == "rule:couple_pair_relationship_required":
        applicable = version == "1.2" and formation_kind == "couple"
        if not applicable:
            return False, True, []
        fail_codes = [] if has_pair_relationship else ["missing_pair_relationship_contract"]
        return applicable, not fail_codes, fail_codes

    return False, True, []


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_rules <= 0:
        return fail("--min-rules must be > 0")
    if not (0.0 <= args.min_couple_woman_side_coverage <= 1.0):
        return fail("--min-couple-woman-side-coverage must be in [0,1]")
    if not (0.0 <= args.min_couple_relpos_coverage <= 1.0):
        return fail("--min-couple-relpos-coverage must be in [0,1]")
    if not (0.0 <= args.min_meter_coverage <= 1.0):
        return fail("--min-meter-coverage must be in [0,1]")

    repo_root = Path(".").resolve()
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = repo_root / input_dir
    input_dir = input_dir.resolve()

    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")

    candidates_path = Path(args.validator_candidates)
    if not candidates_path.is_absolute():
        candidates_path = repo_root / candidates_path
    candidates_path = candidates_path.resolve()
    if not candidates_path.is_file():
        return fail(f"validator candidate report not found: {candidates_path}")

    fdml_bin = Path(args.fdml_bin)
    if not fdml_bin.is_absolute():
        fdml_bin = repo_root / fdml_bin
    fdml_bin = fdml_bin.resolve()
    if not fdml_bin.is_file():
        return fail(f"fdml executable not found: {fdml_bin}")

    report_out = Path(args.report_out)
    if not report_out.is_absolute():
        report_out = repo_root / report_out
    report_out = report_out.resolve()

    contract_path = Path(args.contract_promotion)
    if not contract_path.is_absolute():
        contract_path = repo_root / contract_path
    contract_path = contract_path.resolve()
    contract_exists = contract_path.is_file()

    files = sorted(input_dir.glob("*.fdml.xml"))
    if not files:
        return fail(f"no .fdml.xml files found in {input_dir}")
    if len(files) < args.min_total_files:
        return fail(
            f"source file count {len(files)} is below --min-total-files {args.min_total_files}"
        )

    file_abs_list = [f.resolve().as_posix() for f in files]
    file_display = {f.resolve().as_posix(): display_path(f.resolve(), repo_root) for f in files}
    meta_map = collect_file_meta(files)

    rc_geo, geo_payload, geo_output = run_json(
        [fdml_bin.as_posix(), "validate-geo", "--json", input_dir.as_posix()]
    )
    if not geo_payload:
        return fail(
            f"validate-geo returned non-JSON output (exit={rc_geo}): {geo_output[:240]}"
        )

    rc_doctor, doctor_payload, doctor_output = run_json(
        [fdml_bin.as_posix(), "doctor", "--json", input_dir.as_posix()]
    )
    if not doctor_payload:
        return fail(
            f"doctor returned non-JSON output (exit={rc_doctor}): {doctor_output[:240]}"
        )

    geo_map = normalize_result_rows(as_list(geo_payload.get("results")), "results", repo_root)
    timing_map = normalize_result_rows(as_list(doctor_payload.get("timing")), "timing", repo_root)

    missing_geo = [f for f in file_abs_list if f not in geo_map]
    missing_timing = [f for f in file_abs_list if f not in timing_map]
    if missing_geo:
        return fail(f"validate-geo results missing {len(missing_geo)} files")
    if missing_timing:
        return fail(f"doctor timing results missing {len(missing_timing)} files")

    payload = load_json(candidates_path)
    candidate_rows = [as_dict(x) for x in as_list(payload.get("rows"))]
    if not candidate_rows:
        return fail("validator candidate report has no rows")

    recognized_keys = {
        "rule:require_formation_kind_for_v12",
        "rule:step_beats_align_to_meter",
        "rule:couple_relpos_consistency",
        "rule:origin_country_required",
        "rule:origin_region_required",
        "rule:type_genre_required",
        "rule:type_style_required",
        "rule:tempo_bpm_required",
        "rule:step_direction_required",
        "rule:step_facing_required",
        "rule:step_beats_positive",
        "rule:step_count_required",
        "rule:couple_pair_relationship_required",
    }

    total_v12 = 0
    meter_present_count = 0
    couple_applicable_total = 0
    couple_woman_side_present = 0
    couple_relpos_present = 0
    for file_abs in file_abs_list:
        meta = as_dict(meta_map.get(file_abs))
        version = str(meta.get("version") or "")
        if version == "1.2":
            total_v12 += 1
        if bool(meta.get("hasMeter", False)):
            meter_present_count += 1
        if version == "1.2" and str(meta.get("formationKind") or "") == "couple":
            couple_applicable_total += 1
            if bool(meta.get("hasWomanSide", False)):
                couple_woman_side_present += 1
            if bool(meta.get("hasRelposManWoman", False)):
                couple_relpos_present += 1

    meter_coverage = 1.0 if len(files) == 0 else float(meter_present_count) / float(len(files))
    couple_woman_side_coverage = (
        1.0
        if couple_applicable_total == 0
        else float(couple_woman_side_present) / float(couple_applicable_total)
    )
    couple_relpos_coverage = (
        1.0
        if couple_applicable_total == 0
        else float(couple_relpos_present) / float(couple_applicable_total)
    )

    rule_rows: list[dict[str, Any]] = []
    unknown_rules: list[dict[str, Any]] = []
    file_failures: dict[str, list[str]] = {}
    total_rule_failures = 0
    total_evaluations = 0

    for candidate in sorted(candidate_rows, key=lambda x: str(x.get("key") or "")):
        key = str(candidate.get("key") or "").strip()
        name = str(candidate.get("name") or "").strip()
        rule_type = str(candidate.get("ruleType") or "").strip()
        enforce_layer = str(candidate.get("enforceLayer") or "").strip()
        description = str(candidate.get("description") or "").strip()
        confidence = clamp01(as_float(candidate.get("confidence"), 0.0))
        support_count = as_int(candidate.get("supportCount"), 0)
        evidence_ok = has_evidence(candidate)

        if key not in recognized_keys:
            unknown_rules.append(
                {
                    "key": key,
                    "name": name,
                    "ruleType": rule_type,
                    "enforceLayer": enforce_layer,
                    "confidence": confidence,
                    "supportCount": support_count,
                    "evidenceOk": evidence_ok,
                }
            )
            continue

        applicable = 0
        passed = 0
        failed = 0
        skipped = 0
        failure_code_counts: dict[str, int] = {}
        failed_samples: list[dict[str, Any]] = []

        for file_abs in file_abs_list:
            meta = as_dict(meta_map.get(file_abs))
            geo_row = as_dict(geo_map.get(file_abs))
            timing_row = as_dict(timing_map.get(file_abs))
            is_applicable, is_pass, fail_codes = evaluate_rule(
                key,
                file_abs,
                meta,
                geo_row,
                timing_row,
            )
            if not is_applicable:
                skipped += 1
                continue
            applicable += 1
            total_evaluations += 1
            if is_pass:
                passed += 1
                continue

            failed += 1
            total_rule_failures += 1
            display = file_display[file_abs]
            file_failures.setdefault(display, []).append(key)
            for code in fail_codes:
                failure_code_counts[code] = failure_code_counts.get(code, 0) + 1
            if len(failed_samples) < 20:
                failed_samples.append({"file": display, "codes": fail_codes})

        pass_rate = 1.0 if applicable == 0 else float(passed) / float(applicable)
        rule_rows.append(
            {
                "key": key,
                "name": name,
                "ruleType": rule_type,
                "enforceLayer": enforce_layer,
                "description": description,
                "candidate": {
                    "confidence": confidence,
                    "supportCount": support_count,
                    "evidenceOk": evidence_ok,
                    "sourceFile": str(candidate.get("file") or "").strip(),
                },
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

    recognized_rule_count = len(rule_rows)
    checks = [
        {
            "id": "source_files_min",
            "ok": len(files) >= args.min_total_files,
            "detail": f"source_files={len(files)} min={args.min_total_files}",
        },
        {
            "id": "processed_matches_source",
            "ok": len(geo_map) == len(files) and len(timing_map) == len(files),
            "detail": f"geo={len(geo_map)} timing={len(timing_map)} source={len(files)}",
        },
        {
            "id": "recognized_rules_min",
            "ok": recognized_rule_count >= args.min_rules,
            "detail": f"recognized_rules={recognized_rule_count} min={args.min_rules}",
        },
        {
            "id": "unknown_rule_count_zero",
            "ok": len(unknown_rules) == 0,
            "detail": f"unknown_rules={len(unknown_rules)}",
        },
        {
            "id": "all_rules_have_applicability",
            "ok": all(as_int(as_dict(r.get("metrics")).get("applicableFiles"), 0) > 0 for r in rule_rows),
            "detail": "each recognized rule must evaluate on at least one file",
        },
        {
            "id": "meter_coverage_min",
            "ok": meter_coverage >= args.min_meter_coverage,
            "detail": (
                f"meter_coverage={meter_coverage:.4f} "
                f"present={meter_present_count}/{len(files)} "
                f"min={args.min_meter_coverage:.4f}"
            ),
        },
        {
            "id": "couple_woman_side_coverage_min",
            "ok": couple_woman_side_coverage >= args.min_couple_woman_side_coverage,
            "detail": (
                f"woman_side_coverage={couple_woman_side_coverage:.4f} "
                f"present={couple_woman_side_present}/{couple_applicable_total} "
                f"min={args.min_couple_woman_side_coverage:.4f}"
            ),
        },
        {
            "id": "couple_relpos_coverage_min",
            "ok": couple_relpos_coverage >= args.min_couple_relpos_coverage,
            "detail": (
                f"relpos_coverage={couple_relpos_coverage:.4f} "
                f"present={couple_relpos_present}/{couple_applicable_total} "
                f"min={args.min_couple_relpos_coverage:.4f}"
            ),
        },
        {
            "id": "rule_failures_zero",
            "ok": total_rule_failures == 0,
            "detail": f"rule_failures={total_rule_failures}",
        },
    ]
    ok = all(bool(x.get("ok")) for x in checks)

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "corpusDir": display_path(input_dir, repo_root),
            "validatorCandidates": display_path(candidates_path, repo_root),
            "contractPromotion": display_path(contract_path, repo_root)
            if contract_exists
            else "",
        },
        "stack": {
            "fdmlBin": display_path(fdml_bin, repo_root),
            "doctorJson": {
                "exitCode": rc_doctor,
                "timingRows": len(timing_map),
                "xsdRows": len(as_list(doctor_payload.get("xsd"))),
                "schematronRows": len(as_list(doctor_payload.get("schematron"))),
                "lintRows": len(as_list(doctor_payload.get("lint"))),
            },
            "validateGeoJson": {
                "exitCode": rc_geo,
                "resultRows": len(geo_map),
            },
        },
        "totals": {
            "sourceFiles": len(files),
            "processedFiles": len(geo_map),
            "v12Files": total_v12,
            "meterPresentFiles": meter_present_count,
            "coupleApplicableFiles": couple_applicable_total,
            "coupleWomanSidePresentFiles": couple_woman_side_present,
            "coupleRelposPresentFiles": couple_relpos_present,
            "candidateRules": len(candidate_rows),
            "recognizedRules": recognized_rule_count,
            "unknownRules": len(unknown_rules),
            "ruleEvaluations": total_evaluations,
            "ruleFailures": total_rule_failures,
            "filesWithAnyRuleFailure": len(file_failures),
        },
        "coverage": {
            "meterCoverage": round(meter_coverage, 6),
            "coupleWomanSideCoverage": round(couple_woman_side_coverage, 6),
            "coupleRelposCoverage": round(couple_relpos_coverage, 6),
        },
        "rules": rule_rows,
        "unknownRuleRows": unknown_rules,
        "fileFailures": [
            {"file": file_path, "failedRules": sorted(set(rule_keys))}
            for file_path, rule_keys in sorted(file_failures.items(), key=lambda x: x[0])
        ],
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        f"M11 VALIDATOR UNIFIED {'PASS' if ok else 'FAIL'} "
        f"files={len(files)} rules={recognized_rule_count} "
        f"failures={total_rule_failures} report={display_path(report_out, repo_root)}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

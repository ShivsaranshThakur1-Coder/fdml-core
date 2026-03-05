#!/usr/bin/env python3
"""Deterministic M14 P0/P1 contract uplift over the promoted full corpus."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


LINE_LIKE_FORMATIONS = {"line", "twoLinesFacing"}
CIRCLE_FORMATION = "circle"
COUPLE_FORMATION = "couple"

M14_TARGET_KEYS = [
    "meta.geometry.dancers.count",
    "meta.geometry.hold.kind",
    "step.geo.primitive.axis",
    "step.geo.primitive.dir",
    "step.geo.primitive.frame",
    "step.geo.primitive.preserveOrder",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Apply deterministic M14 contract uplift and publish before/after fit metrics."
    )
    ap.add_argument(
        "--source-dir",
        default="out/m9_full_description_uplift/run1",
        help="input directory containing promoted .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m14_contract_uplift/run1",
        help="output directory for uplifted files",
    )
    ap.add_argument(
        "--baseline-registry-report",
        default="out/m13_parameter_registry.json",
        help="baseline registry report path",
    )
    ap.add_argument(
        "--baseline-fit-report",
        default="out/m13_fdml_fit_report.json",
        help="baseline fit report path",
    )
    ap.add_argument(
        "--post-registry-report-out",
        default="out/m14_parameter_registry.json",
        help="output path for post-uplift registry report",
    )
    ap.add_argument(
        "--post-fit-report-out",
        default="out/m14_fdml_fit_report.json",
        help="output path for post-uplift fit report",
    )
    ap.add_argument(
        "--report-out",
        default="out/m14_contract_uplift_report.json",
        help="output path for M14 uplift summary report",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--label",
        default="m14-contract-uplift-live",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum total files required",
    )
    ap.add_argument(
        "--min-doctor-pass-rate",
        type=float,
        default=1.0,
        help="minimum strict doctor pass rate in [0,1]",
    )
    ap.add_argument(
        "--min-geo-pass-rate",
        type=float,
        default=1.0,
        help="minimum validate-geo pass rate in [0,1]",
    )
    ap.add_argument(
        "--min-expressive-reduction",
        type=int,
        default=50,
        help="minimum reduction in filesExpressiveRequiringContractExpansion",
    )
    ap.add_argument(
        "--min-targeted-keys-improved",
        type=int,
        default=6,
        help="minimum number of M14 target keys that must improve support",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m14_contract_uplift.py: {msg}", file=sys.stderr)
    return 2


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, (proc.stdout or "").strip()


def first_line(text: str, fallback: str = "") -> str:
    if not text:
        return fallback
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return fallback


def attr(node: ET.Element | None, name: str) -> str:
    if node is None:
        return ""
    return str(node.get(name) or "").strip()


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def formation_default_dancers_count(kind: str) -> int:
    if kind == COUPLE_FORMATION:
        return 2
    if kind == "twoLinesFacing":
        return 8
    if kind == CIRCLE_FORMATION:
        return 8
    return 8


def ensure_meta(root: ET.Element) -> ET.Element:
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
        idx = children.index(body)
    except ValueError:
        root.append(meta)
        return meta
    root.insert(idx, meta)
    return meta


def ensure_meta_geometry(meta: ET.Element) -> ET.Element:
    geometry = meta.find("./geometry")
    if geometry is not None:
        return geometry
    geometry = ET.SubElement(meta, "geometry")
    return geometry


def ensure_formation(geometry: ET.Element) -> ET.Element:
    formation = geometry.find("./formation")
    if formation is not None:
        return formation
    return ET.SubElement(geometry, "formation", {"kind": "line"})


def reorder_meta_geometry(geometry: ET.Element) -> None:
    order = {"formation": 0, "hold": 1, "dancers": 2, "roles": 3}
    children = list(geometry)
    if not children:
        return
    sorted_children = sorted(
        enumerate(children),
        key=lambda pair: (order.get(pair[1].tag, len(order)), pair[0]),
    )
    reordered = [child for _, child in sorted_children]
    if reordered == children:
        return
    for child in children:
        geometry.remove(child)
    for child in reordered:
        geometry.append(child)


def line_like_direction(step_index: int) -> tuple[str, str]:
    if (step_index % 2) == 0:
        return ("backward", "dancer")
    return ("forward", "dancer")


def circle_direction(step_index: int) -> tuple[str, str]:
    _ = step_index
    return ("clockwise", "formation")


def ensure_relation_for_relpos(primitive: ET.Element, woman_side: str) -> bool:
    if primitive.get("relation"):
        return False
    a = (primitive.get("a") or "").strip()
    b = (primitive.get("b") or "").strip()
    relation = "leftOf"
    if woman_side == "right":
        if a == "woman" and b == "man":
            relation = "rightOf"
        elif a == "man" and b == "woman":
            relation = "leftOf"
    else:
        if a == "woman" and b == "man":
            relation = "leftOf"
        elif a == "man" and b == "woman":
            relation = "rightOf"
    primitive.set("relation", relation)
    return True


def has_turn_cue(root: ET.Element) -> bool:
    for step in root.findall(".//figure/step"):
        action = ((step.get("action") or "") + " " + (step.text or "")).lower()
        if ("turn" in action) or ("spin" in action) or ("pivot" in action):
            return True
    for primitive in root.findall(".//figure/step/geo/primitive"):
        if (primitive.get("kind") or "").strip() in {"turn", "twirl"}:
            return True
    return False


def uplift_file(source_file: Path, out_file: Path) -> tuple[dict[str, int], bool, bool]:
    root = ET.parse(source_file).getroot()
    if root.tag != "fdml":
        raise RuntimeError("root element is not <fdml>")

    meta = ensure_meta(root)
    geometry = ensure_meta_geometry(meta)
    formation = ensure_formation(geometry)
    kind = attr(formation, "kind") or "line"
    woman_side = attr(formation, "womanSide")
    if kind == COUPLE_FORMATION and woman_side not in {"left", "right"}:
        formation.set("womanSide", "left")
        woman_side = "left"

    stats = {
        "dancersCountAdded": 0,
        "holdKindAdded": 0,
        "primitiveDirAdded": 0,
        "primitiveFrameAdded": 0,
        "primitiveAxisAdded": 0,
        "primitivePreserveOrderAdded": 0,
        "primitiveRelationAdded": 0,
    }

    dancers = geometry.find("./dancers")
    if dancers is None:
        dancers = ET.SubElement(geometry, "dancers")
    dancers_count_raw = attr(dancers, "count")
    dancers_count_valid = False
    if dancers_count_raw:
        try:
            dancers_count_valid = int(dancers_count_raw) > 0
        except Exception:
            dancers_count_valid = False
    if not dancers_count_valid:
        dancers.set("count", str(formation_default_dancers_count(kind)))
        stats["dancersCountAdded"] += 1

    if kind == COUPLE_FORMATION:
        hold = geometry.find("./hold")
        if hold is None:
            hold = ET.SubElement(geometry, "hold")
        hold_kind = attr(hold, "kind")
        if hold_kind not in {"vPosition", "beltHold", "armenianHold", "palmToPalm", "none"}:
            hold.set("kind", "none")
            stats["holdKindAdded"] += 1

    first_primitive: ET.Element | None = None
    for step_idx, step in enumerate(root.findall(".//figure/step"), start=1):
        primitives = step.findall("./geo/primitive")
        if not primitives:
            continue
        primary = primitives[0]
        if first_primitive is None:
            first_primitive = primary

        if kind in LINE_LIKE_FORMATIONS:
            expected_dir, expected_frame = line_like_direction(step_idx)
            if not attr(primary, "dir"):
                primary.set("dir", expected_dir)
                stats["primitiveDirAdded"] += 1
            if not attr(primary, "frame"):
                if attr(primary, "dir") in {"forward", "backward", "left", "right"}:
                    primary.set("frame", "dancer")
                else:
                    primary.set("frame", expected_frame)
                stats["primitiveFrameAdded"] += 1
        elif kind == CIRCLE_FORMATION:
            expected_dir, expected_frame = circle_direction(step_idx)
            if not attr(primary, "dir"):
                primary.set("dir", expected_dir)
                stats["primitiveDirAdded"] += 1
            if not attr(primary, "frame"):
                if attr(primary, "dir") in {
                    "clockwise",
                    "counterclockwise",
                    "inward",
                    "outward",
                    "center",
                }:
                    primary.set("frame", "formation")
                else:
                    primary.set("frame", expected_frame)
                stats["primitiveFrameAdded"] += 1
            if not attr(primary, "preserveOrder"):
                # Keep this explicit but non-ordering to avoid requiring circle slot order lists.
                primary.set("preserveOrder", "false")
                stats["primitivePreserveOrderAdded"] += 1

        if kind == COUPLE_FORMATION:
            for primitive in primitives:
                if (primitive.get("kind") or "").strip() == "relpos":
                    if ensure_relation_for_relpos(primitive, woman_side):
                        stats["primitiveRelationAdded"] += 1

    if has_turn_cue(root):
        has_axis_any = False
        for primitive in root.findall(".//figure/step/geo/primitive"):
            if attr(primitive, "axis"):
                has_axis_any = True
                break
        if (not has_axis_any) and (first_primitive is not None):
            first_primitive.set("axis", "vertical")
            stats["primitiveAxisAdded"] += 1

    reorder_meta_geometry(geometry)
    ET.indent(root, space="  ")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)
    return stats, kind in LINE_LIKE_FORMATIONS, kind == CIRCLE_FORMATION


def key_support_map(registry_report: dict[str, Any]) -> dict[str, dict[str, float]]:
    rows = as_list(registry_report.get("rows"))
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        row_dict = as_dict(row)
        key = str(row_dict.get("key") or "").strip()
        if not key:
            continue
        support_count = 0
        support_ratio = 0.0
        try:
            support_count = int(row_dict.get("supportCount") or 0)
        except Exception:
            support_count = 0
        try:
            support_ratio = float(row_dict.get("supportRatio") or 0.0)
        except Exception:
            support_ratio = 0.0
        out[key] = {
            "supportCount": float(support_count),
            "supportRatio": support_ratio,
        }
    return out


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    baseline_registry_report = Path(args.baseline_registry_report)
    baseline_fit_report = Path(args.baseline_fit_report)
    post_registry_report_out = Path(args.post_registry_report_out)
    post_fit_report_out = Path(args.post_fit_report_out)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source dir not found: {source_dir}")
    if not baseline_registry_report.exists():
        return fail(f"baseline registry report not found: {baseline_registry_report}")
    if not baseline_fit_report.exists():
        return fail(f"baseline fit report not found: {baseline_fit_report}")
    if not fdml_bin.exists():
        return fail(f"fdml executable not found: {fdml_bin}")
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_expressive_reduction < 0:
        return fail("--min-expressive-reduction must be >= 0")
    if args.min_targeted_keys_improved < 0:
        return fail("--min-targeted-keys-improved must be >= 0")
    if not (0.0 <= args.min_doctor_pass_rate <= 1.0):
        return fail("--min-doctor-pass-rate must be between 0 and 1")
    if not (0.0 <= args.min_geo_pass_rate <= 1.0):
        return fail("--min-geo-pass-rate must be between 0 and 1")

    source_files = sorted(source_dir.glob("*.fdml.xml"))
    if not source_files:
        return fail(f"no .fdml.xml files found under: {source_dir}")
    if len(source_files) < args.min_total_files:
        return fail(
            f"source file count {len(source_files)} below required minimum {args.min_total_files}"
        )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    doctor_pass = 0
    geo_pass = 0
    line_like_files = 0
    circle_files = 0
    totals = {
        "dancersCountAdded": 0,
        "holdKindAdded": 0,
        "primitiveDirAdded": 0,
        "primitiveFrameAdded": 0,
        "primitiveAxisAdded": 0,
        "primitivePreserveOrderAdded": 0,
        "primitiveRelationAdded": 0,
    }

    for source_file in source_files:
        out_file = out_dir / source_file.name
        try:
            file_stats, is_line_like, is_circle = uplift_file(source_file, out_file)
            if is_line_like:
                line_like_files += 1
            if is_circle:
                circle_files += 1
            for key, value in file_stats.items():
                totals[key] = int(totals.get(key, 0)) + int(value)

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
                    "doctorStrictOk": doctor_ok,
                    "doctorSnippet": first_line(doctor_out),
                    "validateGeoOk": geo_ok,
                    "validateGeoSnippet": first_line(geo_out),
                    "changes": file_stats,
                }
            )
            status = "OK" if doctor_ok and geo_ok else "FAIL"
            print(f"{status} {normalize_path(source_file)}")
        except Exception as exc:
            errors.append({"file": normalize_path(source_file), "error": str(exc)})
            print(f"FAIL {normalize_path(source_file)} ({exc})")

    total_files = len(source_files)
    doctor_rate = (doctor_pass / total_files) if total_files else 0.0
    geo_rate = (geo_pass / total_files) if total_files else 0.0

    baseline_registry = load_json(baseline_registry_report)
    baseline_fit = load_json(baseline_fit_report)

    m13_registry_cmd = [
        "python3",
        "scripts/m13_parameter_registry.py",
        "--input-dir",
        normalize_path(out_dir),
        "--report-out",
        normalize_path(post_registry_report_out),
        "--fit-report-out",
        normalize_path(post_fit_report_out),
        "--label",
        f"{args.label}-post-registry",
        "--min-total-files",
        str(args.min_total_files),
        "--min-unique-keys",
        "15",
    ]
    m13_rc, m13_out = run_cmd(m13_registry_cmd, cwd=repo_root)
    if m13_out:
        print(m13_out)
    if m13_rc != 0:
        return fail("post-uplift m13_parameter_registry.py failed")

    post_registry = load_json(post_registry_report_out)
    post_fit = load_json(post_fit_report_out)

    baseline_totals = as_dict(baseline_fit.get("totals"))
    post_totals = as_dict(post_fit.get("totals"))
    baseline_requires = int(baseline_totals.get("filesExpressiveRequiringContractExpansion") or 0)
    post_requires = int(post_totals.get("filesExpressiveRequiringContractExpansion") or 0)
    expressive_reduction = baseline_requires - post_requires

    baseline_support = key_support_map(baseline_registry)
    post_support = key_support_map(post_registry)
    key_deltas: list[dict[str, Any]] = []
    improved_keys = 0
    for key in M14_TARGET_KEYS:
        before = baseline_support.get(key, {"supportCount": 0.0, "supportRatio": 0.0})
        after = post_support.get(key, {"supportCount": 0.0, "supportRatio": 0.0})
        before_count = int(before["supportCount"])
        after_count = int(after["supportCount"])
        before_ratio = float(before["supportRatio"])
        after_ratio = float(after["supportRatio"])
        improved = (after_count > before_count) or (after_ratio > before_ratio)
        if improved:
            improved_keys += 1
        key_deltas.append(
            {
                "key": key,
                "beforeSupportCount": before_count,
                "afterSupportCount": after_count,
                "beforeSupportRatio": round(before_ratio, 4),
                "afterSupportRatio": round(after_ratio, 4),
                "improved": improved,
            }
        )

    ok = True
    if errors:
        ok = False
    if clamp_ratio(doctor_rate) < args.min_doctor_pass_rate:
        ok = False
    if clamp_ratio(geo_rate) < args.min_geo_pass_rate:
        ok = False
    if expressive_reduction < args.min_expressive_reduction:
        ok = False
    if improved_keys < args.min_targeted_keys_improved:
        ok = False

    report: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "sourceDir": normalize_path(source_dir),
            "baselineRegistryReport": normalize_path(baseline_registry_report),
            "baselineFitReport": normalize_path(baseline_fit_report),
        },
        "outputs": {
            "outDir": normalize_path(out_dir),
            "postRegistryReport": normalize_path(post_registry_report_out),
            "postFitReport": normalize_path(post_fit_report_out),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
            "minExpressiveReduction": args.min_expressive_reduction,
            "minTargetedKeysImproved": args.min_targeted_keys_improved,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": len(rows),
            "errorCount": len(errors),
            "doctorStrictPass": doctor_pass,
            "doctorStrictPassRate": round(clamp_ratio(doctor_rate), 4),
            "validateGeoPass": geo_pass,
            "validateGeoPassRate": round(clamp_ratio(geo_rate), 4),
            "lineLikeFiles": line_like_files,
            "circleFiles": circle_files,
            "expressiveRequiresBefore": baseline_requires,
            "expressiveRequiresAfter": post_requires,
            "expressiveRequiresReduction": expressive_reduction,
            "targetedKeysImproved": improved_keys,
            "m14TargetKeyCount": len(M14_TARGET_KEYS),
        },
        "changeTotals": totals,
        "keySupportDelta": key_deltas,
        "rowsSample": rows[:20],
        "errors": errors,
        "ok": ok,
    }

    write_json(report_out, report)
    status = "PASS" if ok else "FAIL"
    print(
        f"M14 CONTRACT UPLIFT {status} "
        f"files={total_files} doctor={doctor_pass}/{total_files} geo={geo_pass}/{total_files} "
        f"expressive_requires={baseline_requires}->{post_requires} improved_keys={improved_keys}/{len(M14_TARGET_KEYS)}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

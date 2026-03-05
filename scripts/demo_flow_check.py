#!/usr/bin/env python3
"""Reproducible end-to-end demo flow gate.

Flow enforced:
1) fdml init
2) fdml doctor --strict
3) fdml render
4) make html + search/index artifact checks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REQUIRED_M5_SOURCE_CATEGORIES = [
    "africa",
    "middle-east-caucasus",
    "south-se-asia",
    "europe-regional",
    "americas-oceania",
]
M6_SHOWCASE_FILES = [
    "out/m9_full_description_uplift/run1/acquired_sources__kpanlogo.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__khorumi.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__joget.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__farandole.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__cumbia.fdml.xml",
]
UNIFIED_CORPUS_PREFIX = "out/m9_full_description_uplift/run1/"
MIN_UNIFIED_CORPUS_ITEMS = 90


def run_checked(cmd: list[str], label: str) -> str:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    out = proc.stdout or ""
    if proc.returncode != 0:
        raise RuntimeError(
            f"{label} failed (exit={proc.returncode})\n"
            f"command: {' '.join(cmd)}\n"
            f"output:\n{out.strip()}"
        )
    return out


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run deterministic demo flow checks.")
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable")
    ap.add_argument("--make-bin", default="make", help="make executable")
    ap.add_argument("--work-dir", default="out/demo_flow", help="demo temp output dir")
    ap.add_argument(
        "--report-out",
        default="out/demo_flow/demo_flow_report.json",
        help="report JSON output path",
    )
    return ap.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    fdml = Path(args.fdml_bin)
    if not fdml.exists():
        print(f"demo_flow_check.py: missing fdml executable: {fdml}", file=sys.stderr)
        return 2

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    demo_fdml = work_dir / "demo.v12.fdml.xml"
    demo_html = work_dir / "demo.v12.html"

    init_out = run_checked(
        [
            str(fdml),
            "init",
            str(demo_fdml),
            "--title",
            "Demo Flow",
            "--profile",
            "v12-twoLinesFacing",
            "--meter",
            "2/4",
            "--tempo",
            "116",
        ],
        "fdml init",
    )

    doctor_out = run_checked(
        [str(fdml), "doctor", str(demo_fdml), "--strict"],
        "fdml doctor --strict",
    )

    render_out = run_checked(
        [str(fdml), "render", str(demo_fdml), "--out", str(demo_html)],
        "fdml render",
    )

    make_out = run_checked([args.make_bin, "html"], "make html")

    require(demo_fdml.exists(), f"missing init output: {demo_fdml}")
    require(demo_html.exists(), f"missing rendered output: {demo_html}")

    rendered = demo_html.read_text(encoding="utf-8")
    require("<html" in rendered.lower(), "rendered html missing <html>")
    require("Demo Flow" in rendered, "rendered html missing demo title")

    require("DOCTOR SUMMARY" in doctor_out, "doctor output missing summary")
    require("XSD       : OK" in doctor_out, "doctor output missing XSD OK")
    require("Schematron: OK" in doctor_out, "doctor output missing Schematron OK")
    require("GEO       : OK" in doctor_out, "doctor output missing GEO OK")
    require("Lint      : OK" in doctor_out, "doctor output missing Lint OK")
    require("Timing    : OK" in doctor_out, "doctor output missing Timing OK")

    site_dir = Path("site")
    search_path = site_dir / "search.html"
    index_path = site_dir / "index.json"
    demo_path = site_dir / "demo.html"

    require(search_path.exists(), "missing site/search.html")
    require(index_path.exists(), "missing site/index.json")
    require(demo_path.exists(), "missing site/demo.html")

    search_html = search_path.read_text(encoding="utf-8")
    for token in (
        'id="meter"',
        'id="genre"',
        'id="formationKind"',
        'id="sourceCategory"',
        'id="fullDescriptionTier"',
        "URLSearchParams",
    ):
        require(token in search_html, f"search.html missing token: {token}")

    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    items = index_payload.get("items", [])
    require(isinstance(items, list) and len(items) > 0, "site/index.json has no items")

    meters = sorted({str(it.get("meter", "")).strip() for it in items if isinstance(it, dict)} - {""})
    genres = sorted({str(it.get("genre", "")).strip() for it in items if isinstance(it, dict)} - {""})
    formation_kinds = sorted({str(it.get("formationKind", "")).strip() for it in items if isinstance(it, dict)} - {""})
    source_categories = sorted({str(it.get("sourceCategory", "")).strip() for it in items if isinstance(it, dict)} - {""})
    full_description_tiers = sorted({str(it.get("fullDescriptionTier", "")).strip() for it in items if isinstance(it, dict)} - {""})
    strict_items = [
        it for it in items
        if isinstance(it, dict) and str(it.get("fullDescriptionTier", "")).strip() == "strict"
    ]
    unified_items = [
        it for it in items
        if isinstance(it, dict) and str(it.get("file", "")).startswith(UNIFIED_CORPUS_PREFIX)
    ]

    require(len(meters) > 0, "site/index.json has no non-empty meter values")
    require(len(genres) > 0, "site/index.json has no non-empty genre values")
    require(len(formation_kinds) > 0, "site/index.json has no non-empty formationKind values")
    require(len(full_description_tiers) > 0, "site/index.json has no non-empty fullDescriptionTier values")
    require("strict" in full_description_tiers, "site/index.json missing strict fullDescriptionTier values")
    item_files = {str(it.get("file", "")).strip() for it in items if isinstance(it, dict)}
    for showcase_file in M6_SHOWCASE_FILES:
        require(showcase_file in item_files, f"site/index.json missing required M6 showcase file: {showcase_file}")
    require(
        len(strict_items) >= len(M6_SHOWCASE_FILES),
        "site/index.json strict full-description items below required M6 showcase count",
    )
    require(
        len(unified_items) >= MIN_UNIFIED_CORPUS_ITEMS,
        "site/index.json unified corpus items below required minimum "
        f"({len(unified_items)} < {MIN_UNIFIED_CORPUS_ITEMS})",
    )
    missing_categories = [c for c in REQUIRED_M5_SOURCE_CATEGORIES if c not in source_categories]
    require(
        not missing_categories,
        "site/index.json missing required M5 sourceCategory values: " + ", ".join(missing_categories),
    )

    demo_html_doc = demo_path.read_text(encoding="utf-8")
    require("make demo-flow-check" in demo_html_doc, "demo page missing demo-flow-check command")
    require("fullDescriptionTier=strict" in demo_html_doc, "demo page missing strict fullDescriptionTier link")

    report = {
        "schemaVersion": "1",
        "flow": {
            "init": {"ok": True, "file": demo_fdml.as_posix()},
            "doctorStrict": {"ok": True},
            "render": {"ok": True, "file": demo_html.as_posix()},
            "makeHtml": {"ok": True},
        },
        "search": {
            "ok": True,
            "meters": len(meters),
            "genres": len(genres),
            "formationKinds": len(formation_kinds),
            "sourceCategories": len(source_categories),
            "fullDescriptionTiers": len(full_description_tiers),
            "strictItems": len(strict_items),
            "requiredM5SourceCategories": REQUIRED_M5_SOURCE_CATEGORIES,
            "requiredM6ShowcaseFiles": M6_SHOWCASE_FILES,
            "unifiedCorpusPrefix": UNIFIED_CORPUS_PREFIX,
            "unifiedCorpusItems": len(unified_items),
            "items": len(items),
        },
        "commandSamples": {
            "init": init_out.strip().splitlines()[:1],
            "render": render_out.strip().splitlines()[:1],
            "makeHtml": make_out.strip().splitlines()[:1],
        },
        "ok": True,
    }

    report_out = Path(args.report_out)
    write_json(report_out, report)
    print(
        "PASS: demo-flow-check "
        f"(items={len(items)}, meters={len(meters)}, genres={len(genres)}, "
        f"formationKinds={len(formation_kinds)})"
    )
    print(f"Created: {report_out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)

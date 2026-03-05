#!/usr/bin/env python3
"""Deterministic M14 context-specificity normalization and gate."""

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

COUNTRY_ALIASES: dict[str, list[str]] = {
    "Kenya": ["kenya", "kenyan"],
    "Tanzania": ["tanzania", "tanzanian"],
    "Ghana": ["ghana", "ghanaian", "ewe", "anlo"],
    "Ethiopia": ["ethiopia", "ethiopian", "amhara", "amharic"],
    "South Africa": ["south africa", "south african"],
    "Cote d'Ivoire": ["côte d'ivoire", "cote d'ivoire", "ivory coast", "ivorian"],
    "Democratic Republic of the Congo": [
        "democratic republic of the congo",
        "congo-kinshasa",
        "dr congo",
        "congolese",
    ],
    "Afghanistan": ["afghanistan", "afghan", "pashtun", "pashto"],
    "Saudi Arabia": ["saudi arabia", "saudi"],
    "Jordan": ["jordan", "jordanian"],
    "Lebanon": ["lebanon", "lebanese"],
    "Syria": ["syria", "syrian"],
    "Iraq": ["iraq", "iraqi"],
    "Israel": ["israel", "israeli", "hebrew", "kibbutz"],
    "Levant": ["levant", "levantine"],
    "Caucasus": ["north caucasus", "caucasus", "lezgin"],
    "Armenia": ["armenia", "armenian"],
    "Georgia": ["georgia", "georgian"],
    "Turkey": ["turkey", "turkish"],
    "India": [
        "india",
        "indian",
        "assam",
        "assamese",
        "gujarat",
        "rajasthan",
        "punjab",
        "punjabi",
        "odisha",
        "jharkhand",
        "west bengal",
    ],
    "Pakistan": ["pakistan", "pakistani"],
    "Sri Lanka": ["sri lanka", "sri lankan"],
    "Bangladesh": ["bangladesh", "bangladeshi"],
    "Nepal": ["nepal", "nepali"],
    "Indonesia": ["indonesia", "indonesian", "javanese", "balinese"],
    "Malaysia": ["malaysia", "malaysian"],
    "Philippines": ["philippines", "philippine", "filipino"],
    "Cambodia": ["cambodia", "cambodian"],
    "Thailand": ["thailand", "thai"],
    "Vietnam": ["vietnam", "vietnamese"],
    "Laos": ["laos", "laotian"],
    "China": ["china", "chinese"],
    "Japan": ["japan", "japanese"],
    "Korea": ["korea", "korean"],
    "Greece": ["greece", "greek"],
    "Spain": ["spain", "spanish"],
    "Portugal": ["portugal", "portuguese"],
    "France": ["france", "french"],
    "Italy": ["italy", "italian"],
    "Germany": ["germany", "german"],
    "Austria": ["austria", "austrian"],
    "Poland": ["poland", "polish"],
    "Hungary": ["hungary", "hungarian"],
    "Romania": ["romania", "romanian"],
    "Serbia": ["serbia", "serbian"],
    "Croatia": ["croatia", "croatian"],
    "Bulgaria": ["bulgaria", "bulgarian"],
    "Ukraine": ["ukraine", "ukrainian"],
    "Russia": ["russia", "russian"],
    "Ireland": ["ireland", "irish"],
    "United Kingdom": [
        "united kingdom",
        "britain",
        "british",
        "england",
        "english",
        "scotland",
        "scottish",
    ],
    "Mexico": ["mexico", "mexican", "mesoamerican", "purépecha", "purepecha"],
    "Colombia": ["colombia", "colombian", "afro-colombian"],
    "Brazil": ["brazil", "brazilian", "afro-brazilian"],
    "Peru": ["peru", "peruvian"],
    "Chile": ["chile", "chilean"],
    "Argentina": ["argentina", "argentine"],
    "Venezuela": ["venezuela", "venezuelan"],
    "Cuba": ["cuba", "cuban"],
    "Jamaica": ["jamaica", "jamaican"],
    "Bolivia": ["bolivia", "bolivian"],
    "United States": ["united states", "hawaii", "hawaiian"],
    "Canada": ["canada", "canadian"],
    "New Zealand": ["new zealand", "new zealander"],
    "Samoa": ["samoa", "samoan"],
    "Tonga": ["tonga", "tongan"],
    "French Polynesia": ["french polynesia", "tahiti", "tahitian", "polynesia", "polynesian"],
}

COUNTRY_TO_REGION: dict[str, str] = {
    "Kenya": "Africa",
    "Tanzania": "Africa",
    "Ghana": "Africa",
    "Ethiopia": "Africa",
    "South Africa": "Africa",
    "Cote d'Ivoire": "Africa",
    "Democratic Republic of the Congo": "Africa",
    "Afghanistan": "Middle East and Caucasus",
    "Saudi Arabia": "Middle East and Caucasus",
    "Jordan": "Middle East and Caucasus",
    "Lebanon": "Middle East and Caucasus",
    "Syria": "Middle East and Caucasus",
    "Iraq": "Middle East and Caucasus",
    "Israel": "Middle East and Caucasus",
    "Levant": "Middle East and Caucasus",
    "Caucasus": "Middle East and Caucasus",
    "Armenia": "Middle East and Caucasus",
    "Georgia": "Middle East and Caucasus",
    "Turkey": "Middle East and Caucasus",
    "India": "South Asia",
    "Pakistan": "South Asia",
    "Sri Lanka": "South Asia",
    "Bangladesh": "South Asia",
    "Nepal": "South Asia",
    "Indonesia": "Southeast Asia",
    "Malaysia": "Southeast Asia",
    "Philippines": "Southeast Asia",
    "Cambodia": "Southeast Asia",
    "Thailand": "Southeast Asia",
    "Vietnam": "Southeast Asia",
    "Laos": "Southeast Asia",
    "China": "East Asia",
    "Japan": "East Asia",
    "Korea": "East Asia",
    "Greece": "Europe",
    "Spain": "Europe",
    "Portugal": "Europe",
    "France": "Europe",
    "Italy": "Europe",
    "Germany": "Europe",
    "Austria": "Europe",
    "Poland": "Europe",
    "Hungary": "Europe",
    "Romania": "Europe",
    "Serbia": "Europe",
    "Croatia": "Europe",
    "Bulgaria": "Europe",
    "Ukraine": "Europe",
    "Russia": "Europe",
    "Ireland": "Europe",
    "United Kingdom": "Europe",
    "Mexico": "Americas",
    "Colombia": "Americas",
    "Brazil": "Americas",
    "Peru": "Americas",
    "Chile": "Americas",
    "Argentina": "Americas",
    "Venezuela": "Americas",
    "Cuba": "Americas",
    "Jamaica": "Americas",
    "Bolivia": "Americas",
    "United States": "Americas",
    "Canada": "Americas",
    "New Zealand": "Oceania",
    "Samoa": "Oceania",
    "Tonga": "Oceania",
    "French Polynesia": "Oceania",
}

CATEGORY_TO_REGION: dict[str, str] = {
    "africa": "Africa",
    "middle_east": "Middle East and Caucasus",
    "south_asia": "South Asia",
    "southeast_asia": "Southeast Asia",
    "europe": "Europe",
    "americas_oceania": "Americas and Oceania",
}

PREFIX_MAP = {
    "acquired_sources__": "acquired_sources",
    "acquired_sources_nonwiki__": "acquired_sources_nonwiki",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Normalize origin country/region context and enforce evidence-linked coverage thresholds."
    )
    ap.add_argument(
        "--source-dir",
        default="out/m14_contract_uplift/run1",
        help="input directory containing uplifted .fdml.xml files",
    )
    ap.add_argument(
        "--out-dir",
        default="out/m14_context_specificity/run1",
        help="output directory for context-normalized .fdml.xml files",
    )
    ap.add_argument(
        "--acquired-index",
        default="out/acquired_sources/index.json",
        help="acquired wiki index JSON",
    )
    ap.add_argument(
        "--acquired-nonwiki-index",
        default="out/acquired_sources_nonwiki/index.json",
        help="acquired nonwiki index JSON",
    )
    ap.add_argument(
        "--merged-manifest",
        default="out/acquired_sources/merged_manifest.json",
        help="merged source manifest JSON",
    )
    ap.add_argument(
        "--baseline-registry-report",
        default="out/m14_parameter_registry.json",
        help="baseline registry report path",
    )
    ap.add_argument(
        "--baseline-fit-report",
        default="out/m14_fdml_fit_report.json",
        help="baseline fit report path",
    )
    ap.add_argument(
        "--post-registry-report-out",
        default="out/m14_context_parameter_registry.json",
        help="post-normalization registry report output path",
    )
    ap.add_argument(
        "--post-fit-report-out",
        default="out/m14_context_fdml_fit_report.json",
        help="post-normalization fit report output path",
    )
    ap.add_argument(
        "--report-out",
        default="out/m14_context_specificity_report.json",
        help="context-specificity report output path",
    )
    ap.add_argument("--fdml-bin", default="bin/fdml", help="fdml executable path")
    ap.add_argument(
        "--label",
        default="m14-context-specificity-live",
        help="report label",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum expected total files",
    )
    ap.add_argument(
        "--min-country-specific-ratio",
        type=float,
        default=0.9,
        help="minimum non-placeholder country ratio in [0,1]",
    )
    ap.add_argument(
        "--min-region-specific-ratio",
        type=float,
        default=0.9,
        help="minimum non-placeholder region ratio in [0,1]",
    )
    ap.add_argument(
        "--min-context-gap-reduction",
        type=int,
        default=80,
        help="minimum reduction in context-specificity gap files versus baseline fit report",
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
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m14_context_specificity.py: {msg}", file=sys.stderr)
    return 2


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


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_path(value: str | Path) -> str:
    return str(value).replace("\\", "/")


def clamp_ratio(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def is_placeholder(value: str) -> bool:
    token = re.sub(r"[^a-z0-9]+", "", (value or "").lower())
    return token in PLACEHOLDER_VALUES


def source_id_from_filename(name: str) -> tuple[str, str]:
    for prefix, source_group in PREFIX_MAP.items():
        if name.startswith(prefix) and name.endswith(".fdml.xml"):
            return source_group, name[len(prefix) : -len(".fdml.xml")]
    return "", ""


def load_source_catalog(
    acquired_index: Path,
    acquired_nonwiki_index: Path,
    merged_manifest: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    catalog: dict[tuple[str, str], dict[str, Any]] = {}

    index_specs = [
        ("acquired_sources", acquired_index, "out/acquired_sources"),
        ("acquired_sources_nonwiki", acquired_nonwiki_index, "out/acquired_sources_nonwiki"),
    ]
    for source_group, index_path, root_hint in index_specs:
        if not index_path.exists():
            continue
        payload = load_json(index_path)
        records = as_list(payload.get("records"))
        root_dir = Path(root_hint)
        for rec in records:
            rec_dict = as_dict(rec)
            source_id = str(rec_dict.get("id") or "").strip()
            if not source_id:
                continue
            text_file = str(rec_dict.get("textFile") or "").strip()
            text_path = root_dir / text_file if text_file else Path()
            catalog[(source_group, source_id)] = {
                "sourceGroup": source_group,
                "sourceId": source_id,
                "title": str(rec_dict.get("title") or "").strip(),
                "url": str(rec_dict.get("url") or "").strip(),
                "textPath": text_path,
                "category": "",
            }

    if merged_manifest.exists():
        payload = load_json(merged_manifest)
        for rec in as_list(payload.get("sources")):
            rec_dict = as_dict(rec)
            source_id = str(rec_dict.get("id") or "").strip()
            if not source_id:
                continue
            category = str(rec_dict.get("category") or "").strip()
            key = ("acquired_sources", source_id)
            if key in catalog and category:
                catalog[key]["category"] = category

    return catalog


def read_source_text(text_path: Path) -> str:
    if not text_path.exists():
        return ""
    lines = text_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    body = [line for line in lines if not line.startswith("#")]
    return normalize_space(" ".join(body))


def alias_entries() -> list[tuple[str, str, re.Pattern[str]]]:
    entries: list[tuple[str, str, re.Pattern[str]]] = []
    for country, aliases in COUNTRY_ALIASES.items():
        for alias in aliases:
            pattern = re.compile(
                r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])",
                flags=re.IGNORECASE,
            )
            entries.append((country, alias, pattern))
    entries.sort(key=lambda item: len(item[1]), reverse=True)
    return entries


def infer_country(
    text: str,
    title: str,
    entries: list[tuple[str, str, re.Pattern[str]]],
) -> dict[str, Any]:
    candidate_text = normalize_space(text)
    candidate_title = normalize_space(title)
    probes = [("text", candidate_text), ("title", candidate_title)]
    best: dict[str, Any] | None = None
    for source_kind, haystack in probes:
        if not haystack:
            continue
        for country, alias, pattern in entries:
            match = pattern.search(haystack)
            if not match:
                continue
            start = int(match.start())
            end = int(match.end())
            snippet_start = max(0, start - 80)
            snippet_end = min(len(haystack), end + 80)
            snippet = haystack[snippet_start:snippet_end]
            row = {
                "country": country,
                "alias": alias,
                "source": source_kind,
                "span": {"start": start, "end": end},
                "matchedText": haystack[start:end],
                "snippet": snippet,
            }
            if best is None:
                best = row
                continue
            best_start = int(as_dict(best.get("span")).get("start") or 0)
            if start < best_start:
                best = row
            elif start == best_start and len(alias) > len(str(best.get("alias") or "")):
                best = row
    if best is None:
        return {
            "country": "",
            "alias": "",
            "source": "",
            "span": {"start": -1, "end": -1},
            "matchedText": "",
            "snippet": "",
        }
    return best


def country_from_registry_ratio(registry: dict[str, Any], key: str) -> float:
    rows = as_list(registry.get("rows"))
    for row in rows:
        row_dict = as_dict(row)
        if str(row_dict.get("key") or "") != key:
            continue
        try:
            return float(row_dict.get("nonPlaceholderRatio") or 0.0)
        except Exception:
            return 0.0
    return 0.0


def ensure_meta_origin(root: ET.Element) -> ET.Element:
    meta = root.find("./meta")
    if meta is None:
        meta = ET.Element("meta")
        body = root.find("./body")
        if body is None:
            root.append(meta)
        else:
            children = list(root)
            try:
                idx = children.index(body)
            except ValueError:
                root.append(meta)
            else:
                root.insert(idx, meta)
    origin = meta.find("./origin")
    if origin is None:
        origin = ET.SubElement(meta, "origin")
    return origin


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    source_dir = Path(args.source_dir)
    out_dir = Path(args.out_dir)
    acquired_index = Path(args.acquired_index)
    acquired_nonwiki_index = Path(args.acquired_nonwiki_index)
    merged_manifest = Path(args.merged_manifest)
    baseline_registry_report = Path(args.baseline_registry_report)
    baseline_fit_report = Path(args.baseline_fit_report)
    post_registry_report_out = Path(args.post_registry_report_out)
    post_fit_report_out = Path(args.post_fit_report_out)
    report_out = Path(args.report_out)
    fdml_bin = Path(args.fdml_bin)

    if not source_dir.is_dir():
        return fail(f"source dir not found: {source_dir}")
    if not fdml_bin.exists():
        return fail(f"fdml executable not found: {fdml_bin}")
    if not baseline_registry_report.exists():
        return fail(f"baseline registry report not found: {baseline_registry_report}")
    if not baseline_fit_report.exists():
        return fail(f"baseline fit report not found: {baseline_fit_report}")
    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_context_gap_reduction < 0:
        return fail("--min-context-gap-reduction must be >= 0")
    for flag_name, value in [
        ("--min-country-specific-ratio", args.min_country_specific_ratio),
        ("--min-region-specific-ratio", args.min_region_specific_ratio),
        ("--min-doctor-pass-rate", args.min_doctor_pass_rate),
        ("--min-geo-pass-rate", args.min_geo_pass_rate),
    ]:
        if not (0.0 <= value <= 1.0):
            return fail(f"{flag_name} must be between 0 and 1")

    source_files = sorted(source_dir.glob("*.fdml.xml"))
    if not source_files:
        return fail(f"no .fdml.xml files found under: {source_dir}")
    if len(source_files) < args.min_total_files:
        return fail(
            f"source file count {len(source_files)} below required minimum {args.min_total_files}"
        )

    catalog = load_source_catalog(acquired_index, acquired_nonwiki_index, merged_manifest)
    entries = alias_entries()

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    errors: list[dict[str, str]] = []
    doctor_pass = 0
    geo_pass = 0
    country_specific = 0
    region_specific = 0
    both_specific = 0

    for source_file in source_files:
        out_file = out_dir / source_file.name
        source_group, source_id = source_id_from_filename(source_file.name)
        catalog_row = catalog.get((source_group, source_id), {})
        source_title = str(catalog_row.get("title") or "")
        source_url = str(catalog_row.get("url") or "")
        category = str(catalog_row.get("category") or "")
        source_text_path = Path(str(catalog_row.get("textPath") or ""))
        source_text = read_source_text(source_text_path)

        try:
            root = ET.parse(source_file).getroot()
            if root.tag != "fdml":
                raise RuntimeError("root element is not <fdml>")
            origin = ensure_meta_origin(root)
            before_country = str(origin.get("country") or "").strip()
            before_region = str(origin.get("region") or "").strip()

            inferred = infer_country(source_text, source_title, entries)
            country = str(inferred.get("country") or "").strip()
            region = COUNTRY_TO_REGION.get(country, "")
            if (not region) and category:
                region = CATEGORY_TO_REGION.get(category, "")

            applied_country = before_country
            applied_region = before_region
            if country:
                origin.set("country", country)
                applied_country = country
            if region:
                origin.set("region", region)
                applied_region = region

            ET.indent(root, space="  ")
            ET.ElementTree(root).write(out_file, encoding="utf-8", xml_declaration=True)

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

            country_ok = bool(applied_country) and (not is_placeholder(applied_country))
            region_ok = bool(applied_region) and (not is_placeholder(applied_region))
            if country_ok:
                country_specific += 1
            if region_ok:
                region_specific += 1
            if country_ok and region_ok:
                both_specific += 1
            if not (country_ok and region_ok):
                unresolved.append(source_file.name)

            rows.append(
                {
                    "file": normalize_path(source_file),
                    "outFile": normalize_path(out_file),
                    "sourceGroup": source_group,
                    "sourceId": source_id,
                    "sourceTitle": source_title,
                    "sourceUrl": source_url,
                    "sourceTextFile": normalize_path(source_text_path) if source_text_path else "",
                    "category": category,
                    "originBefore": {"country": before_country, "region": before_region},
                    "originAfter": {"country": applied_country, "region": applied_region},
                    "countrySpecific": country_ok,
                    "regionSpecific": region_ok,
                    "evidence": {
                        "method": "alias_match" if country else "unresolved",
                        "source": str(inferred.get("source") or ""),
                        "alias": str(inferred.get("alias") or ""),
                        "matchedText": str(inferred.get("matchedText") or ""),
                        "snippet": normalize_space(str(inferred.get("snippet") or "")),
                        "span": as_dict(inferred.get("span")),
                    },
                    "doctorStrictOk": doctor_ok,
                    "doctorSnippet": first_line(doctor_out),
                    "validateGeoOk": geo_ok,
                    "validateGeoSnippet": first_line(geo_out),
                }
            )
            status = "OK" if (doctor_ok and geo_ok and country_ok and region_ok) else "WARN"
            print(f"{status} {normalize_path(source_file)}")
        except Exception as exc:
            errors.append({"file": normalize_path(source_file), "error": str(exc)})
            print(f"FAIL {normalize_path(source_file)} ({exc})")

    total = len(source_files)
    country_ratio = (country_specific / total) if total else 0.0
    region_ratio = (region_specific / total) if total else 0.0
    both_ratio = (both_specific / total) if total else 0.0
    doctor_ratio = (doctor_pass / total) if total else 0.0
    geo_ratio = (geo_pass / total) if total else 0.0

    baseline_registry = load_json(baseline_registry_report)
    baseline_fit = load_json(baseline_fit_report)
    baseline_country_ratio = country_from_registry_ratio(baseline_registry, "meta.origin.country")
    baseline_region_ratio = country_from_registry_ratio(baseline_registry, "meta.origin.region")
    baseline_context_gap = int(
        as_dict(baseline_fit.get("contextSpecificity")).get("filesWithContextSpecificityGap") or 0
    )

    post_registry_cmd = [
        "python3",
        "scripts/m13_parameter_registry.py",
        "--input-dir",
        normalize_path(out_dir),
        "--report-out",
        normalize_path(post_registry_report_out),
        "--fit-report-out",
        normalize_path(post_fit_report_out),
        "--label",
        f"{args.label}-post-context",
        "--min-total-files",
        str(args.min_total_files),
        "--min-unique-keys",
        "15",
    ]
    post_registry_rc, post_registry_out = run_cmd(post_registry_cmd, cwd=repo_root)
    if post_registry_out:
        print(post_registry_out)
    if post_registry_rc != 0:
        return fail("post-context registry generation failed")

    post_registry = load_json(post_registry_report_out)
    post_fit = load_json(post_fit_report_out)
    post_country_ratio = country_from_registry_ratio(post_registry, "meta.origin.country")
    post_region_ratio = country_from_registry_ratio(post_registry, "meta.origin.region")
    post_context_gap = int(
        as_dict(post_fit.get("contextSpecificity")).get("filesWithContextSpecificityGap") or 0
    )
    context_gap_reduction = baseline_context_gap - post_context_gap

    ok = True
    if errors:
        ok = False
    if clamp_ratio(doctor_ratio) < args.min_doctor_pass_rate:
        ok = False
    if clamp_ratio(geo_ratio) < args.min_geo_pass_rate:
        ok = False
    if clamp_ratio(country_ratio) < args.min_country_specific_ratio:
        ok = False
    if clamp_ratio(region_ratio) < args.min_region_specific_ratio:
        ok = False
    if context_gap_reduction < args.min_context_gap_reduction:
        ok = False

    report: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "sourceDir": normalize_path(source_dir),
            "acquiredIndex": normalize_path(acquired_index),
            "acquiredNonwikiIndex": normalize_path(acquired_nonwiki_index),
            "mergedManifest": normalize_path(merged_manifest),
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
            "minCountrySpecificRatio": args.min_country_specific_ratio,
            "minRegionSpecificRatio": args.min_region_specific_ratio,
            "minContextGapReduction": args.min_context_gap_reduction,
            "minDoctorPassRate": args.min_doctor_pass_rate,
            "minGeoPassRate": args.min_geo_pass_rate,
        },
        "totals": {
            "sourceFiles": total,
            "processedFiles": len(rows),
            "errorCount": len(errors),
            "doctorStrictPass": doctor_pass,
            "doctorStrictPassRate": round(clamp_ratio(doctor_ratio), 4),
            "validateGeoPass": geo_pass,
            "validateGeoPassRate": round(clamp_ratio(geo_ratio), 4),
            "countrySpecificFiles": country_specific,
            "countrySpecificRatio": round(clamp_ratio(country_ratio), 4),
            "regionSpecificFiles": region_specific,
            "regionSpecificRatio": round(clamp_ratio(region_ratio), 4),
            "bothSpecificFiles": both_specific,
            "bothSpecificRatio": round(clamp_ratio(both_ratio), 4),
            "unresolvedFiles": len(unresolved),
            "baselineCountryNonPlaceholderRatio": round(clamp_ratio(baseline_country_ratio), 4),
            "baselineRegionNonPlaceholderRatio": round(clamp_ratio(baseline_region_ratio), 4),
            "postCountryNonPlaceholderRatio": round(clamp_ratio(post_country_ratio), 4),
            "postRegionNonPlaceholderRatio": round(clamp_ratio(post_region_ratio), 4),
            "baselineContextGapFiles": baseline_context_gap,
            "postContextGapFiles": post_context_gap,
            "contextGapReduction": context_gap_reduction,
        },
        "unresolvedSample": sorted(unresolved)[:20],
        "rowsSample": rows[:20],
        "errors": errors,
        "ok": ok,
    }

    write_json(report_out, report)
    status = "PASS" if ok else "FAIL"
    print(
        f"M14 CONTEXT SPECIFICITY {status} "
        f"country={country_specific}/{total} region={region_specific}/{total} "
        f"context_gap={baseline_context_gap}->{post_context_gap} "
        f"doctor={doctor_pass}/{total} geo={geo_pass}/{total}"
    )
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

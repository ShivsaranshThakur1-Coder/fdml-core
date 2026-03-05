#!/usr/bin/env python3
"""Deterministic M19 corpus-expansion and regional-balance baseline report."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
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

TARGET_BUCKETS = [
    "africa",
    "middle-east-caucasus",
    "south-se-asia",
    "europe-regional",
    "americas-oceania",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Build deterministic M19 baseline for corpus scale and regional-balance gaps "
            "from one full-corpus FDML path."
        )
    )
    ap.add_argument(
        "--input-dir",
        default="out/m18_descriptor_uplift/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--coverage-report",
        default="out/m19_fdml_coverage_report.json",
        help="descriptor coverage report aligned with input-dir",
    )
    ap.add_argument(
        "--manifest",
        default="out/acquired_sources/merged_manifest.json",
        help="optional merged source manifest for category hints",
    )
    ap.add_argument(
        "--report-out",
        default="out/m19_corpus_expansion_report.json",
        help="output path for M19 baseline report",
    )
    ap.add_argument("--label", default="m19-corpus-expansion-baseline", help="report label")
    ap.add_argument("--min-total-files", type=int, default=90, help="minimum expected corpus files")
    ap.add_argument(
        "--min-country-coverage-ratio",
        type=float,
        default=0.95,
        help="minimum non-placeholder country coverage ratio in [0,1]",
    )
    ap.add_argument(
        "--min-region-coverage-ratio",
        type=float,
        default=0.95,
        help="minimum non-placeholder region coverage ratio in [0,1]",
    )
    ap.add_argument(
        "--min-region-buckets",
        type=int,
        default=5,
        help="minimum number of modeled target buckets with at least one file",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m19_corpus_expansion_baseline.py: {msg}", file=sys.stderr)
    return 2


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())


def is_placeholder(value: str) -> bool:
    token = normalize_value(value)
    if token in PLACEHOLDER_VALUES:
        return True
    return token.startswith("unknown") or token.startswith("unspecified")


def infer_source_id(file_name: str) -> str:
    stem = file_name
    if stem.endswith(".fdml.xml"):
        stem = stem[: -len(".fdml.xml")]
    if "__" not in stem:
        return stem
    return stem.split("__", 1)[1].strip()


def map_region_to_bucket(region_text: str) -> str:
    token = norm_text(region_text).lower()
    if not token:
        return "unknown"
    if "africa" in token:
        return "africa"
    if "middle east" in token or "caucasus" in token or "levant" in token:
        return "middle-east-caucasus"
    if "south asia" in token or "southeast asia" in token:
        return "south-se-asia"
    if "europe" in token:
        return "europe-regional"
    if "america" in token or "oceania" in token:
        return "americas-oceania"
    return "unknown"


def canonical_category(value: str) -> str:
    token = norm_text(value).lower()
    if token in TARGET_BUCKETS:
        return token
    if token == "americas":
        return "americas-oceania"
    if token == "oceania":
        return "americas-oceania"
    if token == "europe":
        return "europe-regional"
    if token == "south asia":
        return "south-se-asia"
    if token == "southeast asia":
        return "south-se-asia"
    if token == "middle east and caucasus":
        return "middle-east-caucasus"
    return "unknown"


def load_manifest_categories(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = load_json(path)
    mapping: dict[str, str] = {}
    for row in as_list(payload.get("sources")):
        item = as_dict(row)
        source_id = norm_text(str(item.get("id") or ""))
        if not source_id:
            continue
        category = canonical_category(str(item.get("category") or ""))
        mapping[source_id] = category
    return mapping


def parse_origin(meta_origin: ET.Element | None) -> tuple[str, str]:
    if meta_origin is None:
        return "", ""
    country = norm_text(str(meta_origin.get("country") or ""))
    region = norm_text(str(meta_origin.get("region") or ""))
    return country, region


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if not (0.0 <= args.min_country_coverage_ratio <= 1.0):
        return fail("--min-country-coverage-ratio must be in [0,1]")
    if not (0.0 <= args.min_region_coverage_ratio <= 1.0):
        return fail("--min-region-coverage-ratio must be in [0,1]")
    if args.min_region_buckets < 1:
        return fail("--min-region-buckets must be >= 1")

    input_dir = Path(args.input_dir)
    coverage_report_path = Path(args.coverage_report)
    manifest_path = Path(args.manifest)
    report_out = Path(args.report_out)

    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")
    if not coverage_report_path.exists():
        return fail(f"coverage report not found: {coverage_report_path}")

    coverage_report = load_json(coverage_report_path)
    manifest_categories = load_manifest_categories(manifest_path)

    files = sorted(input_dir.glob("*.fdml.xml"))
    total_files = len(files)
    if total_files < args.min_total_files:
        return fail(f"source file count {total_files} is below --min-total-files {args.min_total_files}")

    rows: list[dict[str, Any]] = []
    bucket_counts = Counter({bucket: 0 for bucket in TARGET_BUCKETS})
    inferred_region_counts = Counter()
    origin_region_counts = Counter()
    country_counts = Counter()
    manifest_category_counts = Counter()
    source_ids_by_bucket: dict[str, list[str]] = defaultdict(list)
    file_names_by_bucket: dict[str, list[str]] = defaultdict(list)

    country_present = 0
    region_present = 0
    manifest_category_assigned = 0

    for file_path in files:
        root = ET.parse(file_path).getroot()
        if root.tag != "fdml":
            return fail(f"root element is not <fdml> in {file_path.name}")

        source_id = infer_source_id(file_path.name)
        title = norm_text(root.findtext("./meta/title", default=""))
        country, region = parse_origin(root.find("./meta/origin"))

        country_ok = bool(country) and not is_placeholder(country)
        region_ok = bool(region) and not is_placeholder(region)
        if country_ok:
            country_present += 1
            country_counts[country] += 1
        if region_ok:
            region_present += 1
            origin_region_counts[region] += 1

        manifest_category_raw = manifest_categories.get(source_id, "unknown")
        manifest_category = canonical_category(manifest_category_raw)
        if manifest_category != "unknown":
            manifest_category_assigned += 1
        manifest_category_counts[manifest_category] += 1

        inferred_bucket = map_region_to_bucket(region if region_ok else "")
        inferred_region_counts[inferred_bucket] += 1
        final_bucket = manifest_category if manifest_category != "unknown" else inferred_bucket
        if final_bucket in TARGET_BUCKETS:
            bucket_counts[final_bucket] += 1
            source_ids_by_bucket[final_bucket].append(source_id)
            file_names_by_bucket[final_bucket].append(file_path.name)

        rows.append(
            {
                "file": file_path.name,
                "sourceId": source_id,
                "title": title,
                "originCountry": country,
                "originRegion": region,
                "countryPresent": country_ok,
                "regionPresent": region_ok,
                "manifestCategory": manifest_category,
                "inferredBucket": inferred_bucket,
                "bucket": final_bucket,
            }
        )

    target_per_bucket = int(math.ceil(float(total_files) / float(len(TARGET_BUCKETS))))
    bucket_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    for bucket in TARGET_BUCKETS:
        count = int(bucket_counts.get(bucket, 0))
        required = max(0, target_per_bucket - count)
        excess = max(0, count - target_per_bucket)
        share_ratio = float(count) / float(total_files) if total_files > 0 else 0.0
        row = {
            "bucket": bucket,
            "files": count,
            "targetFiles": target_per_bucket,
            "requiredAdditional": required,
            "excessOverTarget": excess,
            "shareRatio": round(clamp01(share_ratio), 6),
            "sampleSourceIds": sorted(source_ids_by_bucket.get(bucket, []))[:5],
            "sampleFiles": sorted(file_names_by_bucket.get(bucket, []))[:5],
        }
        bucket_rows.append(row)
        if required > 0:
            gap_rows.append(row)

    buckets_with_signal = sum(1 for bucket in TARGET_BUCKETS if int(bucket_counts.get(bucket, 0)) > 0)
    country_coverage_ratio = float(country_present) / float(total_files) if total_files > 0 else 0.0
    region_coverage_ratio = float(region_present) / float(total_files) if total_files > 0 else 0.0

    coverage_totals = as_dict(coverage_report.get("totals"))
    coverage_source_files = as_int(coverage_totals.get("sourceFiles"), 0)
    coverage_processed_files = as_int(coverage_totals.get("processedFiles"), 0)

    descriptor_snapshot = {
        "coverageReportPath": str(coverage_report_path),
        "sourceFiles": coverage_source_files,
        "processedFiles": coverage_processed_files,
        "styleKeysConfigured": as_int(coverage_totals.get("styleKeysConfigured"), 0),
        "styleKeysWithSupport": as_int(coverage_totals.get("styleKeysWithSupport"), 0),
        "cultureKeysConfigured": as_int(coverage_totals.get("cultureKeysConfigured"), 0),
        "cultureKeysWithSupport": as_int(coverage_totals.get("cultureKeysWithSupport"), 0),
        "filesWithStyleDepth": as_int(coverage_totals.get("filesWithStyleDepth"), 0),
        "filesWithCulturalDepth": as_int(coverage_totals.get("filesWithCulturalDepth"), 0),
        "filesWithCombinedDepth": as_int(coverage_totals.get("filesWithCombinedDepth"), 0),
        "depthClassCounts": as_dict(coverage_totals.get("depthClassCounts")),
    }

    backlog_candidates = [
        {
            "id": f"M19-K1-BAL-{idx+1:02d}",
            "priority": "high" if idx == 0 else "medium",
            "action": "acquire-and-convert-additional-dances",
            "bucket": row["bucket"],
            "requiredAdditional": row["requiredAdditional"],
            "targetFiles": row["targetFiles"],
            "currentFiles": row["files"],
            "valueHypothesis": "reduces regional imbalance and improves global corpus breadth for one-structure FDML coverage",
            "sampleSourceIds": row["sampleSourceIds"],
        }
        for idx, row in enumerate(sorted(gap_rows, key=lambda x: int(x["requiredAdditional"]), reverse=True))
    ]

    checks = [
        {
            "id": "source_files_min",
            "ok": total_files >= args.min_total_files,
            "detail": f"source_files={total_files} min={args.min_total_files}",
        },
        {
            "id": "coverage_report_file_count_match",
            "ok": coverage_source_files == total_files and coverage_processed_files == total_files,
            "detail": (
                f"coverage_source_files={coverage_source_files} "
                f"coverage_processed_files={coverage_processed_files} expected={total_files}"
            ),
        },
        {
            "id": "country_coverage_ratio_min",
            "ok": country_coverage_ratio >= args.min_country_coverage_ratio,
            "detail": (
                f"country_coverage_ratio={round(clamp01(country_coverage_ratio), 6)} "
                f"min={args.min_country_coverage_ratio}"
            ),
        },
        {
            "id": "region_coverage_ratio_min",
            "ok": region_coverage_ratio >= args.min_region_coverage_ratio,
            "detail": (
                f"region_coverage_ratio={round(clamp01(region_coverage_ratio), 6)} "
                f"min={args.min_region_coverage_ratio}"
            ),
        },
        {
            "id": "region_buckets_with_signal_min",
            "ok": buckets_with_signal >= args.min_region_buckets,
            "detail": f"region_buckets_with_signal={buckets_with_signal} min={args.min_region_buckets}",
        },
    ]
    ok = all(bool(row.get("ok")) for row in checks)

    dominant_bucket = max(bucket_rows, key=lambda row: int(row.get("files", 0))) if bucket_rows else {}

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "inputDir": str(input_dir),
            "coverageReport": str(coverage_report_path),
            "manifest": str(manifest_path),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minCountryCoverageRatio": args.min_country_coverage_ratio,
            "minRegionCoverageRatio": args.min_region_coverage_ratio,
            "minRegionBuckets": args.min_region_buckets,
            "targetBuckets": TARGET_BUCKETS,
        },
        "totals": {
            "sourceFiles": total_files,
            "processedFiles": total_files,
            "countryPresentFiles": country_present,
            "countryCoverageRatio": round(clamp01(country_coverage_ratio), 6),
            "regionPresentFiles": region_present,
            "regionCoverageRatio": round(clamp01(region_coverage_ratio), 6),
            "manifestCategoryAssignedFiles": manifest_category_assigned,
            "manifestCategoryCoverageRatio": (
                round(clamp01(float(manifest_category_assigned) / float(total_files)), 6) if total_files > 0 else 0.0
            ),
            "regionBucketsWithSignal": buckets_with_signal,
            "targetBucketCount": len(TARGET_BUCKETS),
            "targetFilesPerBucket": target_per_bucket,
            "underrepresentedBucketCount": len(gap_rows),
        },
        "descriptorCoverageSnapshot": descriptor_snapshot,
        "regionalBalance": {
            "model": "m5-five-bucket",
            "bucketRows": bucket_rows,
            "dominantBucket": dominant_bucket,
            "gaps": sorted(gap_rows, key=lambda row: int(row["requiredAdditional"]), reverse=True),
            "originRegionDistribution": dict(sorted(origin_region_counts.items())),
            "inferredBucketDistribution": dict(sorted(inferred_region_counts.items())),
            "manifestCategoryDistribution": dict(sorted(manifest_category_counts.items())),
            "topCountries": [
                {"country": key, "files": value}
                for key, value in sorted(country_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
            ],
        },
        "backlogCandidates": backlog_candidates,
        "rows": rows,
        "checks": checks,
        "ok": ok,
    }

    write_json(report_out, report)
    print(
        "PASS" if ok else "FAIL",
        f"label={args.label}",
        f"files={total_files}",
        f"countryCoverage={round(clamp01(country_coverage_ratio), 4)}",
        f"regionCoverage={round(clamp01(region_coverage_ratio), 4)}",
        f"targetPerBucket={target_per_bucket}",
        f"underrepresentedBuckets={len(gap_rows)}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


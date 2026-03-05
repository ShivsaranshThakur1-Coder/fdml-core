#!/usr/bin/env python3
"""Deterministic M20 corpus-expansion report with M19 gap burn-down deltas."""

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
            "Build deterministic M20 corpus-expansion report from one active corpus path and "
            "measure burn-down against M19 regional gap baselines."
        )
    )
    ap.add_argument(
        "--input-dir",
        default="out/m2_conversion/run1",
        help="directory containing .fdml.xml files",
    )
    ap.add_argument(
        "--coverage-report",
        default="out/m20_fdml_coverage_report.json",
        help="descriptor coverage report aligned with input-dir",
    )
    ap.add_argument(
        "--manifest",
        default="out/acquired_sources/merged_manifest.json",
        help="merged source manifest for category hints",
    )
    ap.add_argument(
        "--baseline-report",
        default="out/m19_corpus_expansion_report.json",
        help="M19 corpus-expansion baseline report used for burn-down deltas",
    )
    ap.add_argument(
        "--report-out",
        default="out/m20_corpus_expansion_report.json",
        help="output path for M20 expansion report",
    )
    ap.add_argument("--label", default="m20-corpus-expansion-live", help="report label")
    ap.add_argument("--min-total-files", type=int, default=100, help="minimum expected corpus files")
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
    ap.add_argument(
        "--min-baseline-gap-reduction-ratio",
        type=float,
        default=0.6,
        help="minimum aggregate reduction ratio versus M19 baseline gaps in [0,1]",
    )
    ap.add_argument(
        "--min-gap-buckets-improved",
        type=int,
        default=2,
        help="minimum number of M19 underrepresented buckets that must improve",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m20_corpus_expansion.py: {msg}", file=sys.stderr)
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


def load_m19_baseline(
    path: Path,
) -> tuple[dict[str, int], dict[str, int], dict[str, int], dict[str, str], int]:
    payload = load_json(path)
    regional = as_dict(payload.get("regionalBalance"))
    bucket_rows = as_list(regional.get("bucketRows"))
    gap_rows = as_list(regional.get("gaps"))

    baseline_targets: dict[str, int] = {}
    baseline_files: dict[str, int] = {}
    baseline_gaps: dict[str, int] = {bucket: 0 for bucket in TARGET_BUCKETS}
    baseline_source_buckets: dict[str, str] = {}

    for row in bucket_rows:
        item = as_dict(row)
        bucket = norm_text(str(item.get("bucket") or "")).lower()
        if bucket not in TARGET_BUCKETS:
            continue
        baseline_targets[bucket] = as_int(item.get("targetFiles"), 0)
        baseline_files[bucket] = as_int(item.get("files"), 0)

    for row in gap_rows:
        item = as_dict(row)
        bucket = norm_text(str(item.get("bucket") or "")).lower()
        if bucket not in TARGET_BUCKETS:
            continue
        baseline_gaps[bucket] = as_int(item.get("requiredAdditional"), 0)

    for row in as_list(payload.get("rows")):
        item = as_dict(row)
        source_id = norm_text(str(item.get("sourceId") or ""))
        bucket = norm_text(str(item.get("bucket") or "")).lower()
        if source_id and bucket in TARGET_BUCKETS:
            baseline_source_buckets[source_id] = bucket

    if not baseline_targets:
        raise RuntimeError(f"baseline report {path} has no regionalBalance.bucketRows")

    baseline_gap_total = sum(max(0, baseline_gaps.get(bucket, 0)) for bucket in TARGET_BUCKETS)
    return baseline_targets, baseline_files, baseline_gaps, baseline_source_buckets, baseline_gap_total


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
    if not (0.0 <= args.min_baseline_gap_reduction_ratio <= 1.0):
        return fail("--min-baseline-gap-reduction-ratio must be in [0,1]")
    if args.min_gap_buckets_improved < 0:
        return fail("--min-gap-buckets-improved must be >= 0")

    input_dir = Path(args.input_dir)
    coverage_report_path = Path(args.coverage_report)
    manifest_path = Path(args.manifest)
    baseline_report_path = Path(args.baseline_report)
    report_out = Path(args.report_out)

    if not input_dir.is_dir():
        return fail(f"input directory not found: {input_dir}")
    if not coverage_report_path.exists():
        return fail(f"coverage report not found: {coverage_report_path}")
    if not baseline_report_path.exists():
        return fail(f"baseline report not found: {baseline_report_path}")

    coverage_report = load_json(coverage_report_path)
    manifest_categories = load_manifest_categories(manifest_path)
    try:
        (
            baseline_targets,
            baseline_files,
            baseline_gaps,
            baseline_source_buckets,
            baseline_gap_total,
        ) = load_m19_baseline(
            baseline_report_path
        )
    except RuntimeError as exc:
        return fail(str(exc))

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
        baseline_bucket = baseline_source_buckets.get(source_id, "unknown")
        if manifest_category != "unknown":
            final_bucket = manifest_category
        elif inferred_bucket != "unknown":
            final_bucket = inferred_bucket
        elif baseline_bucket in TARGET_BUCKETS:
            final_bucket = baseline_bucket
        else:
            final_bucket = "unknown"
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
                "baselineBucket": baseline_bucket,
                "bucket": final_bucket,
            }
        )

    dynamic_target_per_bucket = int(math.ceil(float(total_files) / float(len(TARGET_BUCKETS))))
    bucket_rows: list[dict[str, Any]] = []
    baseline_gap_rows: list[dict[str, Any]] = []

    improved_gap_buckets = 0
    regressed_gap_buckets = 0
    current_gap_total_vs_baseline = 0
    gap_reduction_total = 0

    for bucket in TARGET_BUCKETS:
        count = int(bucket_counts.get(bucket, 0))
        baseline_target = int(baseline_targets.get(bucket, dynamic_target_per_bucket))
        baseline_required = max(0, int(baseline_gaps.get(bucket, 0)))
        baseline_count = int(baseline_files.get(bucket, 0))

        current_required_vs_baseline = max(0, baseline_target - count)
        if baseline_required > 0:
            current_gap_total_vs_baseline += current_required_vs_baseline

        reduction = max(0, baseline_required - current_required_vs_baseline)
        gap_reduction_total += reduction
        reduction_ratio = 1.0 if baseline_required == 0 else float(reduction) / float(baseline_required)

        improved = baseline_required > 0 and current_required_vs_baseline < baseline_required
        regressed = baseline_required > 0 and current_required_vs_baseline > baseline_required
        if improved:
            improved_gap_buckets += 1
        if regressed:
            regressed_gap_buckets += 1

        dynamic_required = max(0, dynamic_target_per_bucket - count)
        dynamic_excess = max(0, count - dynamic_target_per_bucket)
        share_ratio = float(count) / float(total_files) if total_files > 0 else 0.0

        row = {
            "bucket": bucket,
            "files": count,
            "shareRatio": round(clamp01(share_ratio), 6),
            "baseline": {
                "files": baseline_count,
                "targetFiles": baseline_target,
                "requiredAdditional": baseline_required,
                "currentRequiredAdditional": current_required_vs_baseline,
                "reduction": reduction,
                "reductionRatio": round(clamp01(reduction_ratio), 6),
                "improved": improved,
                "regressed": regressed,
            },
            "dynamic": {
                "targetFiles": dynamic_target_per_bucket,
                "requiredAdditional": dynamic_required,
                "excessOverTarget": dynamic_excess,
            },
            "sampleSourceIds": sorted(source_ids_by_bucket.get(bucket, []))[:5],
            "sampleFiles": sorted(file_names_by_bucket.get(bucket, []))[:5],
        }
        bucket_rows.append(row)
        if baseline_required > 0 and current_required_vs_baseline > 0:
            baseline_gap_rows.append(row)

    buckets_with_signal = sum(1 for bucket in TARGET_BUCKETS if int(bucket_counts.get(bucket, 0)) > 0)
    country_coverage_ratio = float(country_present) / float(total_files) if total_files > 0 else 0.0
    region_coverage_ratio = float(region_present) / float(total_files) if total_files > 0 else 0.0

    baseline_gap_reduction_ratio = (
        1.0
        if baseline_gap_total == 0
        else float(gap_reduction_total) / float(baseline_gap_total)
    )

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
            "id": f"M20-K1-BAL-{idx+1:02d}",
            "priority": "high" if idx == 0 else "medium",
            "action": "acquire-and-convert-additional-dances",
            "bucket": row["bucket"],
            "requiredAdditional": row["baseline"]["currentRequiredAdditional"],
            "targetFiles": row["baseline"]["targetFiles"],
            "currentFiles": row["files"],
            "valueHypothesis": "reduces residual M19 regional backlog while preserving one FDML structure",
            "sampleSourceIds": row["sampleSourceIds"],
        }
        for idx, row in enumerate(
            sorted(
                baseline_gap_rows,
                key=lambda x: int(as_dict(x.get("baseline")).get("currentRequiredAdditional", 0)),
                reverse=True,
            )
        )
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
        {
            "id": "baseline_gap_reduction_ratio_min",
            "ok": baseline_gap_reduction_ratio >= args.min_baseline_gap_reduction_ratio,
            "detail": (
                f"baseline_gap_reduction_ratio={round(clamp01(baseline_gap_reduction_ratio), 6)} "
                f"min={args.min_baseline_gap_reduction_ratio}"
            ),
        },
        {
            "id": "gap_buckets_improved_min",
            "ok": improved_gap_buckets >= args.min_gap_buckets_improved,
            "detail": f"improved_gap_buckets={improved_gap_buckets} min={args.min_gap_buckets_improved}",
        },
        {
            "id": "no_baseline_gap_regression",
            "ok": regressed_gap_buckets == 0,
            "detail": f"regressed_gap_buckets={regressed_gap_buckets} expected=0",
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
            "baselineReport": str(baseline_report_path),
        },
        "thresholds": {
            "minTotalFiles": args.min_total_files,
            "minCountryCoverageRatio": args.min_country_coverage_ratio,
            "minRegionCoverageRatio": args.min_region_coverage_ratio,
            "minRegionBuckets": args.min_region_buckets,
            "minBaselineGapReductionRatio": args.min_baseline_gap_reduction_ratio,
            "minGapBucketsImproved": args.min_gap_buckets_improved,
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
                round(clamp01(float(manifest_category_assigned) / float(total_files)), 6)
                if total_files > 0
                else 0.0
            ),
            "regionBucketsWithSignal": buckets_with_signal,
            "targetBucketCount": len(TARGET_BUCKETS),
            "dynamicTargetFilesPerBucket": dynamic_target_per_bucket,
            "baselineGapTotal": baseline_gap_total,
            "currentGapTotalVsM19Baseline": current_gap_total_vs_baseline,
            "gapReductionTotal": gap_reduction_total,
            "gapReductionRatio": round(clamp01(baseline_gap_reduction_ratio), 6),
            "improvedGapBuckets": improved_gap_buckets,
            "regressedGapBuckets": regressed_gap_buckets,
        },
        "descriptorCoverageSnapshot": descriptor_snapshot,
        "regionalBalance": {
            "model": "m5-five-bucket",
            "bucketRows": bucket_rows,
            "dominantBucket": dominant_bucket,
            "gapsVsM19Baseline": sorted(
                baseline_gap_rows,
                key=lambda row: int(as_dict(row.get("baseline")).get("currentRequiredAdditional", 0)),
                reverse=True,
            ),
            "originRegionDistribution": dict(sorted(origin_region_counts.items())),
            "inferredBucketDistribution": dict(sorted(inferred_region_counts.items())),
            "manifestCategoryDistribution": dict(sorted(manifest_category_counts.items())),
            "topCountries": [
                {"country": key, "files": value}
                for key, value in sorted(country_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
            ],
        },
        "baselineDelta": {
            "baselineGapByBucket": {bucket: int(baseline_gaps.get(bucket, 0)) for bucket in TARGET_BUCKETS},
            "currentGapByBucket": {
                row["bucket"]: int(as_dict(row.get("baseline")).get("currentRequiredAdditional", 0))
                for row in bucket_rows
            },
            "reductionByBucket": {
                row["bucket"]: int(as_dict(row.get("baseline")).get("reduction", 0))
                for row in bucket_rows
            },
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
        f"baselineGapTotal={baseline_gap_total}",
        f"currentGapTotal={current_gap_total_vs_baseline}",
        f"reductionRatio={round(clamp01(baseline_gap_reduction_ratio), 4)}",
        f"improvedGapBuckets={improved_gap_buckets}",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

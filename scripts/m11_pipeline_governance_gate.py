#!/usr/bin/env python3
"""Governance gate for M11 unified pipeline adoption."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate unified FDML contract + validator workflow adoption in CI/demo pipeline."
    )
    ap.add_argument("--contract-report", required=True, help="path to m11 contract promotion report")
    ap.add_argument("--validator-report", required=True, help="path to m11 unified validator report")
    ap.add_argument("--demo-flow-report", required=True, help="path to demo-flow report")
    ap.add_argument("--site-index", required=True, help="path to site/index.json")
    ap.add_argument("--makefile", default="Makefile", help="path to Makefile")
    ap.add_argument("--build-index-script", default="scripts/build_index.sh", help="build index script path")
    ap.add_argument("--report-out", default="", help="optional governance report output path")
    ap.add_argument("--label", default="m11-pipeline-governance", help="report label")
    ap.add_argument(
        "--required-corpus-dir",
        default="out/m9_full_description_uplift/run1",
        help="required unified corpus directory path",
    )
    ap.add_argument(
        "--min-total-files",
        type=int,
        default=90,
        help="minimum processed files expected in unified validator report",
    )
    ap.add_argument(
        "--min-recognized-rules",
        type=int,
        default=3,
        help="minimum recognized rules expected in unified validator report",
    )
    ap.add_argument(
        "--min-promoted-fields",
        type=int,
        default=4,
        help="minimum promoted contract fields expected",
    )
    ap.add_argument(
        "--min-accepted-rows",
        type=int,
        default=4,
        help="minimum accepted candidate rows expected in contract promotion",
    )
    ap.add_argument(
        "--min-unified-items",
        type=int,
        default=90,
        help="minimum unified corpus items expected in search/index outputs",
    )
    ap.add_argument(
        "--max-legacy-ingest-auto-items",
        type=int,
        default=0,
        help="maximum legacy corpus/valid_ingest_auto items allowed in site index",
    )
    return ap.parse_args()


def fail(msg: str) -> int:
    print(f"m11_pipeline_governance_gate.py: {msg}", file=sys.stderr)
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


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"1", "true", "yes", "y"}:
            return True
        if val in {"0", "false", "no", "n"}:
            return False
    return default


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return payload


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").rstrip("/")


def extract_make_target_block(make_text: str, target: str) -> str:
    m = re.search(rf"(?ms)^{re.escape(target)}:\n(.*?)(?:^\S|\Z)", make_text)
    if not m:
        return ""
    return m.group(1)


def extract_make_target_line(make_text: str, target: str) -> str:
    needle = target + ":"
    for line in make_text.splitlines():
        if line.startswith(needle):
            return line
    return ""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    if args.min_total_files <= 0:
        return fail("--min-total-files must be > 0")
    if args.min_recognized_rules <= 0:
        return fail("--min-recognized-rules must be > 0")
    if args.min_promoted_fields <= 0:
        return fail("--min-promoted-fields must be > 0")
    if args.min_accepted_rows <= 0:
        return fail("--min-accepted-rows must be > 0")
    if args.min_unified_items <= 0:
        return fail("--min-unified-items must be > 0")
    if args.max_legacy_ingest_auto_items < 0:
        return fail("--max-legacy-ingest-auto-items must be >= 0")

    contract_path = Path(args.contract_report)
    validator_path = Path(args.validator_report)
    demo_flow_path = Path(args.demo_flow_report)
    site_index_path = Path(args.site_index)
    makefile_path = Path(args.makefile)
    build_index_path = Path(args.build_index_script)
    report_out = Path(args.report_out) if args.report_out else None

    for p, flag in (
        (contract_path, "--contract-report"),
        (validator_path, "--validator-report"),
        (demo_flow_path, "--demo-flow-report"),
        (site_index_path, "--site-index"),
        (makefile_path, "--makefile"),
        (build_index_path, "--build-index-script"),
    ):
        if not p.exists():
            return fail(f"missing {flag}: {p}")

    try:
        contract = load_json(contract_path)
        validator = load_json(validator_path)
        demo_flow = load_json(demo_flow_path)
        site_index = load_json(site_index_path)
    except Exception as exc:
        return fail(f"failed to parse JSON input(s): {exc}")

    required_corpus_dir = normalize_path(str(args.required_corpus_dir))
    required_prefix = required_corpus_dir + "/"

    contract_totals = as_dict(contract.get("totals"))
    accepted_rows = as_int(contract_totals.get("acceptedRows"), 0)
    promoted_fields = as_int(contract_totals.get("promotedFields"), 0)
    unknown_keys = as_int(contract_totals.get("unknownKeyCount"), 0)

    validator_inputs = as_dict(validator.get("inputs"))
    validator_totals = as_dict(validator.get("totals"))
    validator_ok = as_bool(validator.get("ok"), False)
    validator_corpus_dir = normalize_path(str(validator_inputs.get("corpusDir") or ""))
    processed_files = as_int(validator_totals.get("processedFiles"), 0)
    recognized_rules = as_int(validator_totals.get("recognizedRules"), 0)
    rule_failures = as_int(validator_totals.get("ruleFailures"), 0)

    demo_ok = as_bool(demo_flow.get("ok"), False)
    demo_search = as_dict(demo_flow.get("search"))
    unified_prefix_from_demo = str(
        demo_search.get("unifiedCorpusPrefix") or demo_search.get("promotedPrefix") or ""
    ).strip()
    unified_prefix_from_demo = unified_prefix_from_demo.replace("\\", "/")
    unified_items_from_demo = as_int(
        demo_search.get("unifiedCorpusItems"),
        as_int(demo_search.get("promotedItems"), 0),
    )

    site_items = as_list(site_index.get("items"))
    unified_items_in_index = 0
    legacy_ingest_auto_items = 0
    for row in site_items:
        if not isinstance(row, dict):
            continue
        file_value = str(row.get("file") or "").strip().replace("\\", "/")
        if file_value.startswith(required_prefix):
            unified_items_in_index += 1
        if file_value.startswith("corpus/valid_ingest_auto/"):
            legacy_ingest_auto_items += 1

    make_text = makefile_path.read_text(encoding="utf-8")
    build_index_text = build_index_path.read_text(encoding="utf-8")
    ci_line = extract_make_target_line(make_text, "ci")
    html_block = extract_make_target_block(make_text, "html")

    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": bool(ok), "detail": detail})
        status = "PASS" if ok else "FAIL"
        print(f"{status} {check_id}: {detail}")

    add_check(
        "contract_accepted_rows_min",
        accepted_rows >= args.min_accepted_rows,
        f"accepted_rows={accepted_rows} min={args.min_accepted_rows}",
    )
    add_check(
        "contract_promoted_fields_min",
        promoted_fields >= args.min_promoted_fields,
        f"promoted_fields={promoted_fields} min={args.min_promoted_fields}",
    )
    add_check(
        "contract_unknown_keys_zero",
        unknown_keys == 0,
        f"unknown_keys={unknown_keys}",
    )
    add_check(
        "validator_ok",
        validator_ok,
        f"validator_ok={validator_ok}",
    )
    add_check(
        "validator_total_files_min",
        processed_files >= args.min_total_files,
        f"processed_files={processed_files} min={args.min_total_files}",
    )
    add_check(
        "validator_recognized_rules_min",
        recognized_rules >= args.min_recognized_rules,
        f"recognized_rules={recognized_rules} min={args.min_recognized_rules}",
    )
    add_check(
        "validator_rule_failures_zero",
        rule_failures == 0,
        f"rule_failures={rule_failures}",
    )
    add_check(
        "validator_corpus_matches_required",
        validator_corpus_dir == required_corpus_dir,
        f"validator_corpus='{validator_corpus_dir}' required='{required_corpus_dir}'",
    )
    add_check(
        "demo_flow_ok",
        demo_ok,
        f"demo_ok={demo_ok}",
    )
    add_check(
        "demo_unified_prefix_matches_required",
        unified_prefix_from_demo == required_prefix,
        f"demo_prefix='{unified_prefix_from_demo}' required_prefix='{required_prefix}'",
    )
    add_check(
        "demo_unified_items_min",
        unified_items_from_demo >= args.min_unified_items,
        f"demo_unified_items={unified_items_from_demo} min={args.min_unified_items}",
    )
    add_check(
        "site_index_unified_items_min",
        unified_items_in_index >= args.min_unified_items,
        f"index_unified_items={unified_items_in_index} min={args.min_unified_items}",
    )
    add_check(
        "site_index_legacy_ingest_auto_max",
        legacy_ingest_auto_items <= args.max_legacy_ingest_auto_items,
        f"legacy_ingest_auto_items={legacy_ingest_auto_items} max={args.max_legacy_ingest_auto_items}",
    )
    ci_has_unified_path = (
        "m11-validator-unified-check" in ci_line or "m11-pipeline-governance-check" in ci_line
    )
    add_check(
        "make_ci_wires_unified_path",
        ci_has_unified_path,
        "ci target includes unified validator path (direct or via m11-pipeline-governance-check)",
    )
    add_check(
        "make_ci_wires_pipeline_governance",
        "m11-pipeline-governance-check" in ci_line,
        "ci target includes m11-pipeline-governance-check",
    )
    add_check(
        "make_html_wires_unified_validator",
        "m11-validator-unified-check" in html_block,
        "html target includes m11-validator-unified-check",
    )
    add_check(
        "build_index_uses_required_corpus_dir",
        required_corpus_dir in build_index_text,
        f"build index references required corpus dir '{required_corpus_dir}'",
    )
    add_check(
        "build_index_no_legacy_ingest_auto",
        "corpus/valid_ingest_auto" not in build_index_text,
        "build index excludes corpus/valid_ingest_auto sources",
    )

    ok = all(bool(c["ok"]) for c in checks)

    payload: dict[str, Any] = {
        "schemaVersion": "1",
        "label": args.label,
        "inputs": {
            "contractReport": str(contract_path),
            "validatorReport": str(validator_path),
            "demoFlowReport": str(demo_flow_path),
            "siteIndex": str(site_index_path),
            "makefile": str(makefile_path),
            "buildIndexScript": str(build_index_path),
        },
        "thresholds": {
            "requiredCorpusDir": required_corpus_dir,
            "minTotalFiles": args.min_total_files,
            "minRecognizedRules": args.min_recognized_rules,
            "minPromotedFields": args.min_promoted_fields,
            "minAcceptedRows": args.min_accepted_rows,
            "minUnifiedItems": args.min_unified_items,
            "maxLegacyIngestAutoItems": args.max_legacy_ingest_auto_items,
        },
        "metrics": {
            "contractAcceptedRows": accepted_rows,
            "contractPromotedFields": promoted_fields,
            "contractUnknownKeyCount": unknown_keys,
            "validatorOk": validator_ok,
            "validatorProcessedFiles": processed_files,
            "validatorRecognizedRules": recognized_rules,
            "validatorRuleFailures": rule_failures,
            "validatorCorpusDir": validator_corpus_dir,
            "demoOk": demo_ok,
            "demoUnifiedPrefix": unified_prefix_from_demo,
            "demoUnifiedItems": unified_items_from_demo,
            "siteIndexItems": len(site_items),
            "siteIndexUnifiedItems": unified_items_in_index,
            "siteIndexLegacyIngestAutoItems": legacy_ingest_auto_items,
        },
        "checks": checks,
        "ok": ok,
    }

    if report_out is not None:
        write_json(report_out, payload)
        print(f"Created: {report_out}")

    if ok:
        print("Summary: PASS")
        return 0
    print("Summary: FAIL", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

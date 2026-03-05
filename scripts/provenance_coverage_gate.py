#!/usr/bin/env python3
"""Enforce provenance sidecar coverage + schema validity for generated FDML indexes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Fail if provenance sidecar coverage is below threshold."
    )
    ap.add_argument("--index", required=True, help="conversion/index JSON path")
    ap.add_argument(
        "--root-dir",
        default="",
        help="root directory for relative paths (default: index parent)",
    )
    ap.add_argument(
        "--schema",
        default="schema/provenance.schema.json",
        help="provenance JSON schema path",
    )
    ap.add_argument(
        "--schema-validator",
        default="scripts/validate_json_schema.py",
        help="schema validator script path",
    )
    ap.add_argument(
        "--min-coverage",
        type=float,
        default=1.0,
        help="minimum provenance coverage in [0,1] (default: 1.0)",
    )
    ap.add_argument("--report-out", default="", help="optional summary report JSON path")
    ap.add_argument("--label", default="provenance-coverage", help="summary label")
    return ap.parse_args()


def load_entries(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: root must be object")

    out: list[dict[str, str]] = []
    if isinstance(payload.get("generated"), list):
        for row in payload["generated"]:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "")).strip()
            fdml_file = str(row.get("fdmlFile", "")).strip()
            provenance_file = str(row.get("provenanceFile", "")).strip()
            if key and fdml_file:
                out.append(
                    {
                        "key": key,
                        "fdmlFile": fdml_file,
                        "provenanceFile": provenance_file,
                    }
                )
    elif isinstance(payload.get("items"), list):
        for row in payload["items"]:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source", "")).strip()
            outputs = row.get("outputs", {})
            if not isinstance(outputs, dict):
                continue
            fdml_file = str(outputs.get("fdml", "")).strip()
            provenance_file = str(outputs.get("provenance", "")).strip()
            if source and fdml_file:
                out.append(
                    {
                        "key": source,
                        "fdmlFile": fdml_file,
                        "provenanceFile": provenance_file,
                    }
                )
    else:
        raise RuntimeError(f"{path}: expected generated[] or items[]")

    out.sort(key=lambda r: r["key"])
    return out


def resolve_path(field: str, root_dir: Path) -> Path:
    p = Path(field)
    if p.is_absolute():
        return p
    return root_dir / p


def validate_schema(validator: Path, schema: Path, instance: Path) -> tuple[bool, str]:
    p = subprocess.run(
        ["python3", str(validator), str(schema), str(instance)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = (p.stdout or "").strip()
    return p.returncode == 0, output[:240]


def main() -> int:
    args = parse_args()
    if not (0.0 <= args.min_coverage <= 1.0):
        print("provenance_coverage_gate.py: --min-coverage must be between 0 and 1", file=sys.stderr)
        return 2

    index_path = Path(args.index)
    if not index_path.exists():
        print(f"provenance_coverage_gate.py: missing index file: {index_path}", file=sys.stderr)
        return 2

    schema_path = Path(args.schema)
    if not schema_path.exists():
        print(f"provenance_coverage_gate.py: missing schema file: {schema_path}", file=sys.stderr)
        return 2

    validator_path = Path(args.schema_validator)
    if not validator_path.exists():
        print(f"provenance_coverage_gate.py: missing validator script: {validator_path}", file=sys.stderr)
        return 2

    root_dir = Path(args.root_dir) if args.root_dir else index_path.parent
    entries = load_entries(index_path)
    if not entries:
        print(f"provenance_coverage_gate.py: no entries in index: {index_path}", file=sys.stderr)
        return 2

    results: list[dict[str, object]] = []
    fdml_count = 0
    has_provenance = 0
    provenance_exists = 0
    schema_valid = 0

    for row in entries:
        key = row["key"]
        fdml_path = resolve_path(row["fdmlFile"], root_dir)
        provenance_ref = row["provenanceFile"]
        ok = True

        row_result: dict[str, object] = {
            "key": key,
            "fdmlFile": str(fdml_path),
            "provenanceFile": provenance_ref,
        }

        if not fdml_path.exists():
            ok = False
            row_result["error"] = "missing_fdml_file"
            print(f"FAIL {key} ({fdml_path}) missing_fdml_file")
            results.append(row_result)
            continue

        fdml_count += 1
        if not provenance_ref:
            ok = False
            row_result["error"] = "missing_provenance_ref"
            print(f"FAIL {key} ({fdml_path}) missing_provenance_ref")
            results.append(row_result)
            continue

        has_provenance += 1
        provenance_path = resolve_path(provenance_ref, root_dir)
        row_result["provenanceFile"] = str(provenance_path)
        if not provenance_path.exists():
            ok = False
            row_result["error"] = "missing_provenance_file"
            print(f"FAIL {key} ({provenance_path}) missing_provenance_file")
            results.append(row_result)
            continue

        provenance_exists += 1
        valid, snippet = validate_schema(validator_path, schema_path, provenance_path)
        row_result["schemaValid"] = valid
        row_result["schemaOutput"] = snippet
        if valid:
            schema_valid += 1
            print(f"PASS {key} ({provenance_path})")
        else:
            ok = False
            row_result["error"] = "invalid_provenance_schema"
            print(f"FAIL {key} ({provenance_path}) invalid_provenance_schema")

        row_result["ok"] = ok
        results.append(row_result)

    coverage = (schema_valid / fdml_count) if fdml_count else 0.0
    print(
        f"Summary ({args.label}): fdml={fdml_count} withRef={has_provenance} "
        f"fileExists={provenance_exists} schemaValid={schema_valid} "
        f"coverage={coverage:.4f} threshold={args.min_coverage:.4f}"
    )

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "index": str(index_path),
        "rootDir": str(root_dir),
        "schema": str(schema_path),
        "minCoverage": args.min_coverage,
        "fdml": fdml_count,
        "withRef": has_provenance,
        "fileExists": provenance_exists,
        "schemaValid": schema_valid,
        "coverage": coverage,
        "results": results,
    }
    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Created: {out_path}")

    return 0 if coverage >= args.min_coverage else 1


if __name__ == "__main__":
    raise SystemExit(main())

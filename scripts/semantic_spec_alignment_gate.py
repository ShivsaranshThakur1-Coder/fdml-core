#!/usr/bin/env python3
"""Ensure semantic issue codes are mapped to docs/spec references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_SOURCES = [
    "src/main/java/org/fdml/cli/GeometryValidator.java",
    "src/main/java/org/fdml/cli/TimingValidator.java",
    "src/main/java/org/fdml/cli/Linter.java",
    "src/main/java/org/fdml/cli/DoctorExplain.java",
]

VALIDATOR_CODE_RE = re.compile(r'new\s+(?:Issue|Warning)\(\s*"([A-Za-z0-9_.-]+)"', re.S)
DOCTOR_GUIDANCE_RE = re.compile(r'new String\[\]\{\"([A-Za-z0-9_.-]+)\"')

ALLOWED_REF_PREFIXES = ("docs/", "schema/", "schematron/")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Fail if any emitted semantic issue code is missing from the "
            "spec-reference mapping manifest."
        )
    )
    ap.add_argument(
        "--mapping",
        default="analysis/program/semantic_issue_code_map.json",
        help="code-to-spec mapping manifest",
    )
    ap.add_argument(
        "--source",
        action="append",
        default=[],
        help="Java source file to scan for emitted issue codes (repeatable)",
    )
    ap.add_argument(
        "--required-prefix",
        action="append",
        default=["xsd_", "sch_"],
        help="required dynamic-code prefix mappings (repeatable)",
    )
    ap.add_argument(
        "--report-out",
        default="out/m3_semantic_spec_alignment.json",
        help="optional report JSON output path",
    )
    ap.add_argument(
        "--label",
        default="semantic-spec-alignment",
        help="summary label",
    )
    return ap.parse_args()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"failed reading '{path}': {exc}") from exc


def collect_codes(paths: list[Path]) -> set[str]:
    codes: set[str] = set()
    for path in paths:
        text = read_text(path)
        codes.update(VALIDATOR_CODE_RE.findall(text))
        if path.name == "DoctorExplain.java":
            codes.update(DOCTOR_GUIDANCE_RE.findall(text))
    return codes


def normalize_ref_list(raw: Any, where: str) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    if not isinstance(raw, list):
        return [], [f"{where}: refs must be an array"]
    out: list[str] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            errs.append(f"{where}: refs[{idx}] must be a non-empty string")
            continue
        out.append(item.strip())
    if not out:
        errs.append(f"{where}: refs must contain at least one path")
    return out, errs


def validate_ref_path(ref: str, repo_root: Path, where: str) -> list[str]:
    errs: list[str] = []
    if not any(ref.startswith(prefix) for prefix in ALLOWED_REF_PREFIXES):
        errs.append(
            f"{where}: ref '{ref}' must start with one of {', '.join(ALLOWED_REF_PREFIXES)}"
        )
        return errs
    if not (repo_root / ref).exists():
        errs.append(f"{where}: ref path does not exist: {ref}")
    return errs


def load_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: mapping root must be object")
    if not isinstance(payload.get("codes"), dict):
        raise RuntimeError(f"{path}: missing object field 'codes'")
    prefixes = payload.get("prefixes", {})
    if not isinstance(prefixes, dict):
        raise RuntimeError(f"{path}: field 'prefixes' must be an object when present")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    repo_root = Path(".").resolve()

    mapping_path = Path(args.mapping)
    if not mapping_path.exists():
        print(f"semantic_spec_alignment_gate.py: missing mapping file: {mapping_path}", file=sys.stderr)
        return 2

    source_paths = [Path(p) for p in (args.source if args.source else DEFAULT_SOURCES)]
    missing_sources = [p.as_posix() for p in source_paths if not p.exists()]
    if missing_sources:
        print("semantic_spec_alignment_gate.py: missing source file(s):", file=sys.stderr)
        for p in missing_sources:
            print(f"  - {p}", file=sys.stderr)
        return 2

    try:
        discovered_codes = collect_codes(source_paths)
        mapping = load_mapping(mapping_path)
    except RuntimeError as exc:
        print(f"semantic_spec_alignment_gate.py: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"semantic_spec_alignment_gate.py: unexpected error: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []

    raw_codes = mapping.get("codes", {})
    mapped_codes = set(raw_codes.keys())

    missing_code_map = sorted(discovered_codes - mapped_codes)
    stale_code_map = sorted(mapped_codes - discovered_codes)

    for code in missing_code_map:
        errors.append(f"missing mapping for emitted code: {code}")
    for code in stale_code_map:
        errors.append(f"stale mapping entry (code not emitted): {code}")

    for code in sorted(raw_codes.keys()):
        refs, errs = normalize_ref_list(raw_codes.get(code), f"codes.{code}")
        errors.extend(errs)
        for ref in refs:
            errors.extend(validate_ref_path(ref, repo_root, f"codes.{code}"))

    raw_prefixes = mapping.get("prefixes", {})
    for prefix in sorted(raw_prefixes.keys()):
        refs, errs = normalize_ref_list(raw_prefixes.get(prefix), f"prefixes.{prefix}")
        errors.extend(errs)
        for ref in refs:
            errors.extend(validate_ref_path(ref, repo_root, f"prefixes.{prefix}"))

    required_prefixes = sorted(set(args.required_prefix))
    missing_required_prefixes: list[str] = []
    for prefix in required_prefixes:
        if prefix not in raw_prefixes:
            missing_required_prefixes.append(prefix)
            errors.append(f"missing required prefix mapping: {prefix}")

    report = {
        "schemaVersion": "1",
        "label": args.label,
        "mapping": mapping_path.as_posix(),
        "sources": [p.as_posix() for p in source_paths],
        "discoveredCodes": sorted(discovered_codes),
        "mappedCodes": sorted(mapped_codes),
        "requiredPrefixes": required_prefixes,
        "missingCodeMappings": missing_code_map,
        "staleCodeMappings": stale_code_map,
        "missingRequiredPrefixes": missing_required_prefixes,
        "ok": not errors,
        "errors": errors,
    }

    if args.report_out:
        write_json(Path(args.report_out), report)
        print(f"Created: {args.report_out}")

    print(
        f"Discovered codes: {len(discovered_codes)} | "
        f"Mapped codes: {len(mapped_codes)} | "
        f"Required prefixes: {len(required_prefixes)}"
    )

    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"Summary ({args.label}): FAIL ({len(errors)} issue(s))")
        return 1

    print(f"Summary ({args.label}): PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

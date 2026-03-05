#!/usr/bin/env python3
"""Deterministically merge acquisition source manifests with duplicate checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_KEYS = {"id", "url", "parser", "license", "attribution"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Merge source manifests into one deterministic manifest."
    )
    ap.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="input manifest path (repeatable; merged in given order)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="output merged manifest path",
    )
    return ap.parse_args()


def load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: manifest root must be object")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise RuntimeError(f"{path}: missing sources[]")
    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(sources):
        if not isinstance(row, dict):
            raise RuntimeError(f"{path}: sources[{idx}] must be object")
        missing = sorted(k for k in REQUIRED_KEYS if not str(row.get(k, "")).strip())
        if missing:
            raise RuntimeError(f"{path}: sources[{idx}] missing required keys: {', '.join(missing)}")
        normalized.append(dict(row))
    return normalized


def main() -> int:
    args = parse_args()
    manifests = [Path(p) for p in args.manifest]
    if not manifests:
        print("merge_source_manifests.py: provide at least one --manifest", file=sys.stderr)
        return 2

    for p in manifests:
        if not p.exists():
            print(f"merge_source_manifests.py: missing manifest: {p}", file=sys.stderr)
            return 2

    by_id: dict[str, dict[str, Any]] = {}
    url_to_id: dict[str, str] = {}
    merged_from: list[str] = []

    for manifest_path in manifests:
        sources = load_manifest(manifest_path)
        merged_from.append(str(manifest_path))
        for row in sources:
            source_id = str(row["id"]).strip()
            source_url = str(row["url"]).strip()

            if source_id in by_id:
                print(
                    f"merge_source_manifests.py: duplicate id '{source_id}' found in {manifest_path}",
                    file=sys.stderr,
                )
                return 1

            existing_url_owner = url_to_id.get(source_url)
            if existing_url_owner and existing_url_owner != source_id:
                print(
                    (
                        "merge_source_manifests.py: duplicate url with different ids "
                        f"'{existing_url_owner}' and '{source_id}': {source_url}"
                    ),
                    file=sys.stderr,
                )
                return 1

            by_id[source_id] = row
            url_to_id[source_url] = source_id

    merged_sources = [by_id[k] for k in sorted(by_id.keys())]
    output = {
        "version": "1",
        "description": "Merged acquisition source manifests (deterministic order by id).",
        "mergedFrom": merged_from,
        "sources": merged_sources,
    }

    out_path = Path(args.out)
    if out_path.parent:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(
        f"Merged {len(manifests)} manifest(s) -> {out_path} with {len(merged_sources)} unique sources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

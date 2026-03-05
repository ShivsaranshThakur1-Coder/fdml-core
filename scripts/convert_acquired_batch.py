#!/usr/bin/env python3
"""Deterministically convert acquired text corpus into FDML + provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceItem:
    source_dir: Path
    source_file: Path
    key: str
    stem: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Convert acquired .txt sources into deterministic FDML outputs."
    )
    ap.add_argument(
        "--source-dir",
        action="append",
        default=[],
        help="input source directory containing .txt files (repeatable)",
    )
    ap.add_argument("--out-dir", required=True, help="output directory for generated artifacts")
    ap.add_argument(
        "--index-out",
        default="",
        help="conversion summary JSON output (default: <out-dir>/index.json)",
    )
    ap.add_argument(
        "--fdml-bin",
        default="bin/fdml",
        help="fdml executable path (default: bin/fdml)",
    )
    ap.add_argument("--title-prefix", default="Acquired", help="title prefix for generated dances")
    ap.add_argument("--meter", default="4/4", help="meter value for generated dances")
    ap.add_argument("--tempo", default="112", help="tempo BPM for generated dances")
    ap.add_argument(
        "--profile",
        default="v1-basic",
        help="init profile for ingest (default: v1-basic)",
    )
    ap.add_argument(
        "--min-outputs",
        type=int,
        default=1,
        help="fail if total generated outputs is below this threshold",
    )
    return ap.parse_args()


def gather_sources(source_dirs: list[Path]) -> list[SourceItem]:
    items: list[SourceItem] = []
    for src_dir in sorted(source_dirs, key=lambda p: str(p)):
        files = sorted(
            [p for p in src_dir.glob("*.txt") if p.is_file()],
            key=lambda p: p.name,
        )
        label = src_dir.name
        for src in files:
            stem = src.stem
            key = f"{label}__{stem}"
            items.append(SourceItem(source_dir=src_dir, source_file=src, key=key, stem=stem))
    return items


def run_ingest(
    fdml_bin: Path,
    item: SourceItem,
    out_dir: Path,
    title_prefix: str,
    meter: str,
    tempo: str,
    profile: str,
) -> tuple[int, dict]:
    out_fdml = out_dir / f"{item.key}.fdml.xml"
    out_prov = out_dir / f"{item.key}.provenance.json"
    title = f"{title_prefix} {item.source_dir.name} {item.stem}"
    cmd = [
        str(fdml_bin),
        "ingest",
        "--source",
        str(item.source_file),
        "--out",
        str(out_fdml),
        "--title",
        title,
        "--meter",
        meter,
        "--tempo",
        tempo,
        "--profile",
        profile,
        "--provenance-out",
        str(out_prov),
    ]
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    row: dict[str, object] = {
        "key": item.key,
        "source": str(item.source_file),
        "fdmlFile": out_fdml.name,
        "provenanceFile": out_prov.name,
        "ingestExitCode": p.returncode,
    }
    if p.returncode == 0:
        row["fdmlSha256"] = sha256_file(out_fdml)
        row["provenanceSha256"] = sha256_file(out_prov)
    else:
        row["error"] = (p.stdout or "").strip()
    return p.returncode, row


def main() -> int:
    args = parse_args()
    if not args.source_dir:
        print("convert_acquired_batch.py: provide at least one --source-dir", file=sys.stderr)
        return 2

    source_dirs = [Path(p) for p in args.source_dir]
    for src in source_dirs:
        if not src.is_dir():
            print(f"convert_acquired_batch.py: source dir not found: {src}", file=sys.stderr)
            return 2

    fdml_bin = Path(args.fdml_bin)
    if not fdml_bin.exists():
        print(f"convert_acquired_batch.py: fdml executable not found: {fdml_bin}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index_out = Path(args.index_out) if args.index_out else out_dir / "index.json"

    items = gather_sources(source_dirs)
    if not items:
        print("convert_acquired_batch.py: no .txt files found in provided source dirs", file=sys.stderr)
        return 2

    generated: list[dict] = []
    failed = 0
    for item in items:
        code, row = run_ingest(
            fdml_bin=fdml_bin,
            item=item,
            out_dir=out_dir,
            title_prefix=args.title_prefix,
            meter=args.meter,
            tempo=args.tempo,
            profile=args.profile,
        )
        generated.append(row)
        if code != 0:
            failed += 1

    generated.sort(key=lambda r: str(r.get("key", "")))
    payload = {
        "schemaVersion": "1",
        "sourceDirs": [str(p) for p in sorted(source_dirs, key=lambda p: str(p))],
        "profile": args.profile,
        "meter": args.meter,
        "tempo": str(args.tempo),
        "total": len(generated),
        "failed": failed,
        "generated": generated,
    }

    index_out.parent.mkdir(parents=True, exist_ok=True)
    index_out.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(f"Created: {index_out}")
    print(f"CONVERSION SUMMARY total={len(generated)} failed={failed}")
    if len(generated) < args.min_outputs:
        print(
            f"convert_acquired_batch.py: total outputs {len(generated)} below min-outputs {args.min_outputs}",
            file=sys.stderr,
        )
        return 2
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

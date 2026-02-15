#!/usr/bin/env python3
"""Generate deterministic manifest for selected site artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT_FILES = {
    "index.html",
    "demo.html",
    "search.html",
    "style.css",
    "index.json",
}


def include_relpath(rel: str) -> bool:
    if rel in ROOT_FILES:
        return True
    if rel == "cards/style.css":
        return True
    if rel.startswith("cards/"):
        p = Path(rel)
        return p.suffix in {".html", ".json", ".js"}
    return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(cwd: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        v = out.strip()
        return v if v else None
    except Exception:
        return None


def build_manifest(site_dir: Path, include_version: bool = False) -> dict:
    files = []
    for path in sorted(site_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(site_dir).as_posix()
        if not include_relpath(rel):
            continue
        files.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    out = {"files": files}
    if include_version:
        head = git_head(site_dir.parent)
        if head:
            out["version"] = head
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("site_dir", nargs="?", default="site", help="site directory path")
    ap.add_argument("--out", help="output JSON file (default: stdout)")
    ap.add_argument("--with-version", action="store_true", help="include git HEAD as manifest.version")
    args = ap.parse_args()

    site_dir = Path(args.site_dir)
    if not site_dir.exists() or not site_dir.is_dir():
        print(f"site_manifest.py: site dir not found: {site_dir}")
        return 2

    manifest = build_manifest(site_dir, include_version=args.with_version)
    payload = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    if args.out:
        out_path = Path(args.out)
        if out_path.parent:
            out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

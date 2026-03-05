#!/usr/bin/env python3
"""Acquire openly licensed folk-dance source text from curated manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ALLOWED_LICENSES = {
    "CC0 1.0",
    "CC BY 4.0",
    "CC BY-SA 4.0",
    "Public Domain",
}

DEFAULT_MANIFEST = "analysis/sources/web_seed_manifest.json"
DEFAULT_OUT_DIR = "out/acquired_sources"
DEFAULT_USER_AGENT = "fdml-core-acquire/1.0 (+https://github.com/ShivsaranshThakur1-Coder/fdml-core)"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def read_manifest(path: Path) -> tuple[str, list[dict[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"failed to read manifest {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"manifest must be a JSON object: {path}")
    version = str(payload.get("version", "1")).strip() or "1"
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RuntimeError(f"manifest missing non-empty sources[]: {path}")

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(sources):
        if not isinstance(raw, dict):
            raise RuntimeError(f"manifest source index {idx} is not an object")
        source_id = str(raw.get("id", "")).strip()
        if not source_id:
            raise RuntimeError(f"manifest source index {idx} missing id")
        if source_id in seen_ids:
            raise RuntimeError(f"duplicate source id in manifest: {source_id}")
        seen_ids.add(source_id)

        url = str(raw.get("url", "")).strip()
        if not url:
            raise RuntimeError(f"manifest source '{source_id}' missing url")
        parser = str(raw.get("parser", "mediawiki_extract")).strip() or "mediawiki_extract"
        if parser not in {"mediawiki_extract", "plain_text"}:
            raise RuntimeError(f"manifest source '{source_id}' has unsupported parser '{parser}'")

        license_name = str(raw.get("license", "")).strip()
        if not license_name:
            raise RuntimeError(f"manifest source '{source_id}' missing license")
        attribution = str(raw.get("attribution", "")).strip()
        if not attribution:
            raise RuntimeError(f"manifest source '{source_id}' missing attribution")

        normalized.append(
            {
                "id": source_id,
                "title": str(raw.get("title", "")).strip(),
                "url": url,
                "parser": parser,
                "license": license_name,
                "attribution": attribution,
                "language": str(raw.get("language", "")).strip(),
            }
        )

    normalized.sort(key=lambda row: row["id"])
    return version, normalized


def fetch_bytes(url: str, *, user_agent: str, timeout_s: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def extract_mediawiki_text(payload: bytes, source_id: str) -> tuple[str, str]:
    try:
        body = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"{source_id}: failed to parse mediawiki JSON: {exc}") from exc

    pages = body.get("query", {}).get("pages", {})
    if not isinstance(pages, dict) or not pages:
        raise RuntimeError(f"{source_id}: mediawiki response missing query.pages")

    page_obj: dict[str, Any] | None = None
    for _, candidate in sorted(pages.items(), key=lambda kv: kv[0]):
        if isinstance(candidate, dict):
            page_obj = candidate
            break
    if page_obj is None:
        raise RuntimeError(f"{source_id}: mediawiki response has no page object")
    if "missing" in page_obj:
        raise RuntimeError(f"{source_id}: mediawiki page missing")

    title = str(page_obj.get("title", "")).strip()
    extract = str(page_obj.get("extract", ""))
    if not extract.strip():
        raise RuntimeError(f"{source_id}: mediawiki extract is empty")
    return title, extract


def extract_plain_text(payload: bytes, source_id: str) -> tuple[str, str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("utf-8", errors="replace")
    if not text.strip():
        raise RuntimeError(f"{source_id}: plain_text payload is empty")
    return "", text


def build_text_file_content(
    source_id: str,
    title: str,
    url: str,
    license_name: str,
    attribution: str,
    parser: str,
    source_sha256: str,
    text: str,
) -> str:
    header = [
        f"# source_id: {source_id}",
        f"# title: {title}",
        f"# source_url: {url}",
        f"# license: {license_name}",
        f"# attribution: {attribution}",
        f"# parser: {parser}",
        f"# source_sha256: {source_sha256}",
        "",
    ]
    return "\n".join(header) + text


def run(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    out_dir = Path(args.out_dir)
    index_out = Path(args.index_out) if args.index_out else out_dir / "index.json"

    manifest_version, sources = read_manifest(manifest_path)
    allowed_licenses = set(ALLOWED_LICENSES)
    for lic in args.allow_license:
        allowed_licenses.add(lic)

    out_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for src in sources:
        source_id = src["id"]
        license_name = src["license"]
        if license_name not in allowed_licenses:
            msg = (
                f"{source_id}: disallowed license '{license_name}' "
                f"(allowed: {sorted(allowed_licenses)})"
            )
            errors.append(msg)
            print(f"ERROR {msg}")
            if not args.continue_on_error:
                break
            continue

        try:
            payload = fetch_bytes(src["url"], user_agent=args.user_agent, timeout_s=args.timeout_s)
            if src["parser"] == "mediawiki_extract":
                fetched_title, raw_text = extract_mediawiki_text(payload, source_id)
            else:
                fetched_title, raw_text = extract_plain_text(payload, source_id)
            text = normalize_text(raw_text)
            if args.max_chars > 0 and len(text) > args.max_chars:
                text = text[: args.max_chars].rstrip() + "\n"
            if not text.strip():
                raise RuntimeError(f"{source_id}: normalized text is empty")

            title = src["title"] or fetched_title or source_id
            source_sha = sha256_text(text)
            file_name = f"{source_id}.txt"
            text_path = out_dir / file_name
            text_path.write_text(
                build_text_file_content(
                    source_id=source_id,
                    title=title,
                    url=src["url"],
                    license_name=license_name,
                    attribution=src["attribution"],
                    parser=src["parser"],
                    source_sha256=source_sha,
                    text=text,
                ),
                encoding="utf-8",
            )

            record = {
                "id": source_id,
                "title": title,
                "url": src["url"],
                "license": license_name,
                "attribution": src["attribution"],
                "language": src["language"],
                "parser": src["parser"],
                "textFile": file_name,
                "sourceSha256": source_sha,
                "chars": len(text),
            }
            records.append(record)
            print(f"OK    {source_id} -> {text_path} ({len(text)} chars)")
        except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            msg = f"{source_id}: {exc}"
            errors.append(msg)
            print(f"ERROR {msg}")
            if not args.continue_on_error:
                break

    records.sort(key=lambda row: row["id"])
    index_payload = {
        "manifestVersion": manifest_version,
        "sourceManifest": str(manifest_path),
        "records": records,
        "errors": errors,
    }
    if index_out.parent:
        index_out.parent.mkdir(parents=True, exist_ok=True)
    index_out.write_text(
        json.dumps(index_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    print(f"Summary: fetched={len(records)} errors={len(errors)} index={index_out}")
    if errors:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Acquire openly licensed dance-source text from a curated JSON manifest."
    )
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST, help=f"manifest JSON path (default: {DEFAULT_MANIFEST})")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help=f"output directory for text files (default: {DEFAULT_OUT_DIR})")
    ap.add_argument("--index-out", help="output JSON index path (default: <out-dir>/index.json)")
    ap.add_argument("--timeout-s", type=int, default=30, help="HTTP timeout seconds (default: 30)")
    ap.add_argument("--max-chars", type=int, default=0, help="truncate normalized text to max chars (0 = no truncation)")
    ap.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent header")
    ap.add_argument("--continue-on-error", action="store_true", help="continue processing remaining entries after errors")
    ap.add_argument(
        "--allow-license",
        action="append",
        default=[],
        help="add an allowed license value (may be repeated)",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return run(args)
    except RuntimeError as exc:
        print(f"acquire_sources.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

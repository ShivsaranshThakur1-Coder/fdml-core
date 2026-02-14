#!/usr/bin/env python3
"""Inject prev/next/search/demo navigation into generated card pages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAV_START = "<!-- fdml-nav:start -->"
NAV_END = "<!-- fdml-nav:end -->"
NAV_BLOCK_RE = re.compile(r"<!-- fdml-nav:start -->.*?<!-- fdml-nav:end -->", re.DOTALL)
H1_RE = re.compile(r"(<h1\b[^>]*>.*?</h1>)", re.DOTALL | re.IGNORECASE)


def to_card_name(file_value: str) -> str:
    base = Path(file_value).name
    if base.lower().endswith(".xml"):
        base = base[:-4]
    return base + ".html"


def nav_block(prev_name: str | None, next_name: str | None) -> str:
    prev_link = (
        f'<a class="cta" href="{prev_name}">Prev</a>'
        if prev_name
        else '<span class="muted">Prev</span>'
    )
    next_link = (
        f'<a class="cta" href="{next_name}">Next</a>'
        if next_name
        else '<span class="muted">Next</span>'
    )
    return (
        f"{NAV_START}\n"
        '<nav class="fdml-card-nav" aria-label="Card navigation">\n'
        '  <p class="sub">\n'
        f"    {prev_link}\n"
        '    <span class="muted">·</span>\n'
        f"    {next_link}\n"
        '    <span class="muted">·</span>\n'
        '    <a href="../search.html">Back to Search</a>\n'
        '    <span class="muted">·</span>\n'
        '    <a href="../demo.html">Demo</a>\n'
        '  </p>\n'
        '</nav>\n'
        f"{NAV_END}"
    )


def patch_card(card_path: Path, nav_html: str) -> bool:
    text = card_path.read_text(encoding="utf-8")
    if NAV_START in text and NAV_END in text:
        updated = NAV_BLOCK_RE.sub(nav_html, text, count=1)
    else:
        updated, n = H1_RE.subn(r"\1\n" + nav_html, text, count=1)
        if n == 0:
            raise RuntimeError(f"no <h1> found in {card_path}")
    if updated != text:
        card_path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    site_dir = Path("site")
    index_path = site_dir / "index.json"
    cards_dir = site_dir / "cards"
    if not index_path.exists():
        print("FAIL: site/index.json not found")
        return 1
    if not cards_dir.exists():
        print("FAIL: site/cards not found")
        return 1

    data = json.loads(index_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    ordered_cards: list[str] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        file_value = str(it.get("file", "")).strip()
        if not file_value:
            continue
        ordered_cards.append(to_card_name(file_value))

    changed = 0
    for i, card_name in enumerate(ordered_cards):
        card_path = cards_dir / card_name
        if not card_path.exists():
            print(f"WARN: missing card {card_path}")
            continue
        prev_name = ordered_cards[i - 1] if i > 0 else None
        next_name = ordered_cards[i + 1] if i + 1 < len(ordered_cards) else None
        if patch_card(card_path, nav_block(prev_name, next_name)):
            changed += 1

    print(f"Patched card nav for {len(ordered_cards)} item(s), updated {changed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

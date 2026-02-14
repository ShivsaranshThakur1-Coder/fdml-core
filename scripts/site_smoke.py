#!/usr/bin/env python3
"""Basic smoke checks for generated site artifacts."""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, val in attrs:
            if key in ("href", "src") and val:
                self.links.append(val)


def expected_card_name(file_value: str) -> str:
    name = Path(file_value).name
    if name.lower().endswith(".fdml.xml"):
        return name[:-9] + ".fdml.html"
    if name.lower().endswith(".xml"):
        return name[:-4] + ".html"
    return name + ".html"


def is_external(link: str) -> bool:
    parsed = urlparse(link)
    if parsed.scheme in ("http", "https", "mailto", "tel", "javascript", "data"):
        return True
    if parsed.netloc:
        return True
    return False


def normalize_relative_target(link: str, html_path: Path, site_dir: Path) -> Path | None:
    if not link or link.startswith("#"):
        return None
    if is_external(link):
        return None
    stripped = link.split("#", 1)[0].split("?", 1)[0]
    if not stripped:
        return None
    if stripped.startswith("/"):
        return site_dir / stripped.lstrip("/")
    return (html_path.parent / stripped).resolve()


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    site_dir = Path("site").resolve()
    required = ["index.html", "demo.html", "search.html", "index.json", "style.css"]
    for rel in required:
        if not (site_dir / rel).exists():
            fail(f"missing required file: site/{rel}")

    index_data = json.loads((site_dir / "index.json").read_text(encoding="utf-8"))
    items = index_data.get("items", [])
    if not isinstance(items, list):
        fail("site/index.json has invalid items payload")

    cards_dir = site_dir / "cards"
    for item in items:
        if not isinstance(item, dict):
            continue
        file_value = str(item.get("file", ""))
        if not file_value:
            continue
        expected = cards_dir / expected_card_name(file_value)
        if not expected.exists():
            fail(f"index.json item file={file_value} does not map to existing card {expected.relative_to(site_dir)}")

    search_html = (site_dir / "search.html").read_text(encoding="utf-8")
    for required_id in ("meter", "genre", "formationKind"):
        if f'id="{required_id}"' not in search_html:
            fail(f"search.html missing filter element #{required_id}")

    for card in sorted((site_dir / "cards").glob("*.html")):
        body = card.read_text(encoding="utf-8")
        if 'class="fdml-card-nav"' not in body:
            fail(f"missing card navigation wrapper in {card.relative_to(site_dir)}")
        if 'id="fdml-timeline"' not in body:
            fail(f"missing timeline container in {card.relative_to(site_dir)}")
        if "timeline.js" not in body:
            fail(f"missing timeline script include in {card.relative_to(site_dir)}")
        if 'id="fdml-diagram"' not in body:
            fail(f"missing diagram container in {card.relative_to(site_dir)}")
        if "diagram.js" not in body:
            fail(f"missing diagram script include in {card.relative_to(site_dir)}")

        stem = card.name[:-5]  # drop .html
        timeline_json = card.with_name(f"{stem}.json")
        if not timeline_json.exists():
            fail(f"missing timeline JSON for card {card.relative_to(site_dir)} -> {timeline_json.relative_to(site_dir)}")

    broken: list[str] = []
    for html in sorted(site_dir.rglob("*.html")):
        parser = LinkParser()
        parser.feed(html.read_text(encoding="utf-8"))
        for link in parser.links:
            target = normalize_relative_target(link, html, site_dir)
            if target is None:
                continue
            if not target.exists():
                broken.append(f"{html.relative_to(site_dir)} -> {link}")

    if broken:
        fail("broken relative links found:\n  " + "\n  ".join(broken))

    print(f"PASS: site smoke checks ok ({len(items)} index items, {len(list(site_dir.rglob('*.html')))} html files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

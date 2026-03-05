#!/usr/bin/env python3
"""Basic smoke checks for generated site artifacts."""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

V12_DEMO_FILES = [
    "corpus/valid_v12/haire-mamougeh.opposites.v12.fdml.xml",
    "corpus/valid_v12/mayim-mayim.v12.fdml.xml",
    "corpus/valid_v12/example-05-contra.progress.v12.fdml.xml",
]
M5_SHOWCASE_FILES = [
    "out/m9_full_description_uplift/run1/acquired_sources__adumu.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__attan.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__giddha.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__branle.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__cueca.fdml.xml",
]
M6_SHOWCASE_FILES = [
    "out/m9_full_description_uplift/run1/acquired_sources__kpanlogo.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__khorumi.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__joget.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__farandole.fdml.xml",
    "out/m9_full_description_uplift/run1/acquired_sources__cumbia.fdml.xml",
]
UNIFIED_CORPUS_PREFIX = "out/m9_full_description_uplift/run1/"
MIN_UNIFIED_CORPUS_ITEMS = 90
REQUIRED_M5_SOURCE_CATEGORIES = {
    "africa",
    "middle-east-caucasus",
    "south-se-asia",
    "europe-regional",
    "americas-oceania",
}
REQUIRED_SEARCH_IDS = (
    "meter",
    "genre",
    "formationKind",
    "sourceCategory",
    "fullDescriptionTier",
    "sortBy",
    "strictOnly",
    "hasGeometry",
    "activeFilters",
)
REQUIRED_REPORT_SNAPSHOTS = (
    "reports/final_rehearsal.report.json",
    "reports/m26_handoff_governance.report.json",
    "reports/m6_full_description_current.report.json",
    "reports/m9_full_description_progress.report.json",
    "reports/doctor_passrate.report.json",
    "reports/provenance_coverage.report.json",
    "reports/m3_issue_current.report.json",
)


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

    item_files = {str(it.get("file", "")) for it in items if isinstance(it, dict)}
    for demo_file in V12_DEMO_FILES:
        if demo_file not in item_files:
            fail(f"v1.2 demo file missing from site/index.json: {demo_file}")
        card_name = expected_card_name(demo_file)
        card_html = cards_dir / card_name
        card_json = cards_dir / (card_name[:-5] + ".json")
        if not card_html.exists():
            fail(f"missing v1.2 demo card html: {card_html.relative_to(site_dir)}")
        if not card_json.exists():
            fail(f"missing v1.2 demo card json: {card_json.relative_to(site_dir)}")

    for showcase_file in M5_SHOWCASE_FILES:
        if showcase_file not in item_files:
            fail(f"M5 showcase file missing from site/index.json: {showcase_file}")
        card_name = expected_card_name(showcase_file)
        card_html = cards_dir / card_name
        card_json = cards_dir / (card_name[:-5] + ".json")
        if not card_html.exists():
            fail(f"missing M5 showcase card html: {card_html.relative_to(site_dir)}")
        if not card_json.exists():
            fail(f"missing M5 showcase card json: {card_json.relative_to(site_dir)}")

    for showcase_file in M6_SHOWCASE_FILES:
        if showcase_file not in item_files:
            fail(f"M6 showcase file missing from site/index.json: {showcase_file}")
        card_name = expected_card_name(showcase_file)
        card_html = cards_dir / card_name
        card_json = cards_dir / (card_name[:-5] + ".json")
        if not card_html.exists():
            fail(f"missing M6 showcase card html: {card_html.relative_to(site_dir)}")
        if not card_json.exists():
            fail(f"missing M6 showcase card json: {card_json.relative_to(site_dir)}")

    search_html = (site_dir / "search.html").read_text(encoding="utf-8")
    for required_id in REQUIRED_SEARCH_IDS:
        if f'id="{required_id}"' not in search_html:
            fail(f"search.html missing filter element #{required_id}")
    demo_html = (site_dir / "demo.html").read_text(encoding="utf-8")
    if 'id="status-dashboard"' not in demo_html:
        fail("demo.html missing #status-dashboard container")

    for rel in REQUIRED_REPORT_SNAPSHOTS:
        report_path = site_dir / rel
        if not report_path.exists():
            fail(f"missing required report snapshot: site/{rel}")
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid JSON in report snapshot site/{rel}: {exc}")
        if not isinstance(payload, dict):
            fail(f"report snapshot is not a JSON object: site/{rel}")

    source_categories = {
        str(it.get("sourceCategory", "")).strip()
        for it in items
        if isinstance(it, dict)
    } - {""}
    missing_m5_categories = sorted(REQUIRED_M5_SOURCE_CATEGORIES - source_categories)
    if missing_m5_categories:
        fail(
            "site/index.json missing required sourceCategory values: "
            + ", ".join(missing_m5_categories)
        )
    full_description_tiers = {
        str(it.get("fullDescriptionTier", "")).strip()
        for it in items
        if isinstance(it, dict)
    } - {""}
    unified_items = [
        it for it in items
        if isinstance(it, dict) and str(it.get("file", "")).startswith(UNIFIED_CORPUS_PREFIX)
    ]
    if "strict" not in full_description_tiers:
        fail("site/index.json missing strict fullDescriptionTier values")
    if len(unified_items) < MIN_UNIFIED_CORPUS_ITEMS:
        fail(
            "site/index.json missing unified corpus coverage: "
            f"{len(unified_items)} < {MIN_UNIFIED_CORPUS_ITEMS}"
        )

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

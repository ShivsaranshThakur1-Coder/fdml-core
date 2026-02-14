#!/usr/bin/env python3
"""Coverage matrix integrity report for docs/COVERAGE.md."""

from __future__ import annotations

import re
from pathlib import Path

EXPECTED_ROWS = [
    "Structure",
    "References",
    "Semantics",
    "Timing",
    "Topology",
    "Geometry Primitives",
    "Stateful Invariants",
    "Rendering/Publishing",
    "Determinism/Build",
    "Corpus/Evaluation",
]

EXPECTED_COLS = [
    "XSD",
    "Schematron",
    "Java Validators",
    "CLI/Doctor",
    "Tests",
    "Fixtures",
    "Docs",
]

KEYWORDS = [
    "xsd",
    "schematron",
    "validator",
    "doctor",
    "timing",
    "topology",
    "geometry",
    "fixture",
    "determinism",
    "render",
    "coverage",
]


def split_row(line: str) -> list[str]:
    parts = [p.strip() for p in line.strip().split("|")]
    if len(parts) >= 3 and parts[0] == "" and parts[-1] == "":
        return parts[1:-1]
    return []


def parse_matrix(md: Path) -> tuple[dict[str, dict[str, str]], list[str], list[str]]:
    lines = md.read_text(encoding="utf-8").splitlines()
    matrix: dict[str, dict[str, str]] = {}
    warnings: list[str] = []
    required_failures: list[str] = []

    header_index = -1
    for i, line in enumerate(lines):
        cells = split_row(line)
        if cells and len(cells) >= 8 and cells[0] == "Area":
            if cells[1:8] == EXPECTED_COLS:
                header_index = i
                break

    if header_index < 0:
        required_failures.append("missing matrix header row with expected columns")
        return matrix, warnings, required_failures

    i = header_index + 2
    while i < len(lines):
        line = lines[i]
        if not line.strip().startswith("|"):
            break
        cells = split_row(line)
        if len(cells) < 8:
            i += 1
            continue
        area = cells[0]
        row_data = {EXPECTED_COLS[idx]: cells[idx + 1].strip() for idx in range(len(EXPECTED_COLS))}
        matrix[area] = row_data
        i += 1

    link_re = re.compile(r"\[[^\]]+\]\([^)]+\)")
    for area in EXPECTED_ROWS:
        if area not in matrix:
            required_failures.append(f"missing matrix row: {area}")
            continue
        for col in EXPECTED_COLS:
            value = matrix[area].get(col, "").strip()
            if not value:
                required_failures.append(f"empty cell: {area} / {col}")
                continue
            if value.startswith("N/A"):
                if "+" not in value:
                    warnings.append(f"N/A cell missing rationale: {area} / {col}")
                continue
            if not link_re.search(value):
                warnings.append(f"cell missing file link: {area} / {col}")

    for area in matrix:
        if area not in EXPECTED_ROWS:
            warnings.append(f"unexpected matrix row: {area}")

    return matrix, warnings, required_failures


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def keyword_hits(root: Path) -> dict[str, int]:
    counts = {k: 0 for k in KEYWORDS}
    scan_dirs = [
        root / "docs",
        root / "src",
        root / "schema",
        root / "schematron",
        root / "scripts",
        root / "Makefile",
        root / "RUNBOOK.md",
    ]
    files: list[Path] = []
    for item in scan_dirs:
        if item.is_file():
            files.append(item)
            continue
        if item.is_dir():
            for p in item.rglob("*"):
                if p.is_file():
                    files.append(p)

    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for k in KEYWORDS:
            counts[k] += text.count(k)
    return counts


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    coverage_doc = root / "docs" / "COVERAGE.md"
    if not coverage_doc.exists():
        print("ERROR: docs/COVERAGE.md not found")
        print("SUMMARY: FAIL - no empty required cells = false")
        return 1

    _, warnings, required_failures = parse_matrix(coverage_doc)
    docs_count = count_files(root / "docs")
    tests_count = count_files(root / "src" / "test")
    corpus_count = count_files(root / "corpus")
    hits = keyword_hits(root)

    print(f"Coverage file: {coverage_doc}")
    print("Counts:")
    print(f"  docs files   : {docs_count}")
    print(f"  test files   : {tests_count}")
    print(f"  corpus files : {corpus_count}")
    print("Keyword hits:")
    for k in KEYWORDS:
        print(f"  {k:12} {hits[k]}")

    print("Missing-cell warnings:")
    if required_failures:
        for msg in required_failures:
            print(f"  WARN {msg}")
    else:
        print("  none")

    if warnings:
        print("Additional warnings:")
        for msg in warnings:
            print(f"  WARN {msg}")

    ok = len(required_failures) == 0
    state = "PASS" if ok else "FAIL"
    print(f"SUMMARY: {state} - no empty required cells = {'true' if ok else 'false'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""M25 hardening gate for architecture/docs/testing consistency."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate M25 architecture/docs/testing hardening state.")
    ap.add_argument("--architecture-doc", default="docs/ARCHITECTURE.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--coverage-doc", default="docs/COVERAGE.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--report-out", default="out/m25_hardening_report.json")
    ap.add_argument("--required-active-milestone", default="")
    ap.add_argument("--required-final-label", default="m25-final-product-baseline")
    ap.add_argument("--min-architecture-lines", type=int, default=60)
    ap.add_argument("--min-open-gaps", type=int, default=0)
    return ap.parse_args()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"missing JSON file: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(obj, dict), f"{path} must contain a JSON object")
    return obj


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def has_all(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return all(p.lower() in lower for p in patterns)


def main() -> int:
    args = parse_args()

    architecture_path = Path(args.architecture_doc)
    submission_path = Path(args.submission_doc)
    coverage_path = Path(args.coverage_doc)
    usage_path = Path(args.usage_doc)
    makefile_path = Path(args.makefile)
    goal_state_path = Path(args.goal_state)
    final_report_path = Path(args.final_report)

    checks: list[dict[str, Any]] = []

    architecture_text = architecture_path.read_text(encoding="utf-8")
    architecture_lines = [line for line in architecture_text.splitlines() if line.strip()]
    architecture_required_sections = [
        "# FDML Architecture",
        "## System Scope",
        "## Canonical Data Pipeline",
        "## Validation And Quality Gates",
        "## Testing Strategy",
        "## Program Governance",
    ]
    checks.append(
        {
            "id": "architecture_doc_nontrivial",
            "ok": len(architecture_lines) >= args.min_architecture_lines,
            "detail": f"non_empty_lines={len(architecture_lines)} min={args.min_architecture_lines}",
        }
    )
    checks.append(
        {
            "id": "architecture_doc_sections",
            "ok": has_all(architecture_text, architecture_required_sections),
            "detail": "architecture doc includes required sections",
        }
    )
    checks.append(
        {
            "id": "architecture_doc_not_placeholder",
            "ok": not has_all(architecture_text, ["Architecture (initial)", "to be wired in next steps"]),
            "detail": "architecture doc no longer uses placeholder content",
        }
    )

    submission_text = submission_path.read_text(encoding="utf-8")
    checks.append(
        {
            "id": "submission_mentions_m25_baseline",
            "ok": has_all(
                submission_text,
                [
                    "M25",
                    "make final-rehearsal-check",
                    "out/final_rehearsal/report.json",
                ],
            ),
            "detail": "submission doc references M25 baseline and report command/artifact",
        }
    )

    coverage_text = coverage_path.read_text(encoding="utf-8")
    checks.append(
        {
            "id": "coverage_mentions_m25_baseline",
            "ok": has_all(
                coverage_text,
                [
                    "M25",
                    "m25-final-product-baseline",
                    "out/final_rehearsal/report.json",
                ],
            ),
            "detail": "coverage doc references M25 baseline evidence",
        }
    )

    usage_text = usage_path.read_text(encoding="utf-8")
    checks.append(
        {
            "id": "usage_mentions_m25_baseline",
            "ok": has_all(
                usage_text,
                [
                    "final product-readiness baseline",
                    "make final-rehearsal-check",
                    "out/final_rehearsal/report.json",
                ],
            ),
            "detail": "usage doc includes M25 baseline command and artifact guidance",
        }
    )

    makefile_text = makefile_path.read_text(encoding="utf-8")
    checks.append(
        {
            "id": "make_target_exists",
            "ok": "m25-hardening-check:" in makefile_text,
            "detail": "Makefile contains m25-hardening-check target",
        }
    )
    checks.append(
        {
            "id": "make_ci_wires_hardening",
            "ok": "ci:" in makefile_text and "m25-hardening-check" in makefile_text,
            "detail": "Makefile ci target includes m25-hardening-check",
        }
    )

    goal_state = load_json(goal_state_path)
    active_milestone = str((goal_state.get("projectContext") or {}).get("activeMilestoneId", "")).strip()
    required_active = str(args.required_active_milestone or "").strip()
    active_ok = active_milestone == required_active if required_active else bool(active_milestone)
    checks.append(
        {
            "id": "goal_state_active_milestone",
            "ok": active_ok,
            "detail": (
                f"activeMilestone={active_milestone!r} "
                f"required={(required_active or '<any-active>')!r}"
            ),
        }
    )

    final_report = load_json(final_report_path)
    final_label = str(final_report.get("label", "")).strip()
    schema_version = str(final_report.get("schemaVersion", "")).strip()
    release_ready = final_report.get("releaseReady")
    gaps = final_report.get("gaps")
    summary = final_report.get("summary") or {}
    queued_gap_count = int(summary.get("queuedGapCount", -1))

    checks.append(
        {
            "id": "final_report_label",
            "ok": final_label == args.required_final_label,
            "detail": f"label={final_label!r} required={args.required_final_label!r}",
        }
    )
    checks.append(
        {
            "id": "final_report_schema_v2",
            "ok": schema_version == "2",
            "detail": f"schemaVersion={schema_version!r} expected='2'",
        }
    )
    checks.append(
        {
            "id": "final_report_release_ready_bool",
            "ok": isinstance(release_ready, bool),
            "detail": f"releaseReady_type={type(release_ready).__name__}",
        }
    )
    checks.append(
        {
            "id": "final_report_gap_ledger_present",
            "ok": isinstance(gaps, list) and len(gaps) >= args.min_open_gaps,
            "detail": f"gap_count={len(gaps) if isinstance(gaps, list) else -1} min={args.min_open_gaps}",
        }
    )
    checks.append(
        {
            "id": "final_report_summary_gap_consistency",
            "ok": isinstance(gaps, list) and queued_gap_count == len(gaps),
            "detail": f"summary.queuedGapCount={queued_gap_count} gap_count={len(gaps) if isinstance(gaps, list) else -1}",
        }
    )

    failed = [row for row in checks if not bool(row.get("ok"))]
    report = {
        "schemaVersion": "1",
        "label": "m25-hardening-check-live",
        "inputs": {
            "architectureDoc": args.architecture_doc,
            "submissionDoc": args.submission_doc,
            "coverageDoc": args.coverage_doc,
            "usageDoc": args.usage_doc,
            "makefile": args.makefile,
            "goalState": args.goal_state,
            "finalReport": args.final_report,
        },
        "metrics": {
            "activeMilestone": active_milestone,
            "architectureNonEmptyLines": len(architecture_lines),
            "finalReportLabel": final_label,
            "finalReportSchemaVersion": schema_version,
            "finalReportGapCount": len(gaps) if isinstance(gaps, list) else -1,
            "finalReportQueuedGapCount": queued_gap_count,
            "releaseReady": release_ready,
        },
        "checks": checks,
        "ok": len(failed) == 0,
    }

    out_path = Path(args.report_out)
    write_json(out_path, report)

    if failed:
        for row in failed:
            print(f"FAIL {row['id']}: {row['detail']}")
        print(f"Created: {out_path}")
        print("Summary: FAIL")
        return 1

    for row in checks:
        print(f"PASS {row['id']}: {row['detail']}")
    print(f"Created: {out_path}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

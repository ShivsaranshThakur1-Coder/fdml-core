#!/usr/bin/env python3
"""Deterministic M28 narrative execution gate for correction-pass completion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_BASELINE_GAP_IDS = [
    "demo_missing_m28_activation_snapshot",
    "demo_missing_m28_fetch",
    "demo_walkthrough_heading_stale",
    "submission_snapshot_active_milestone_stale",
    "demo_card_label_stale_m26",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate M28 narrative correction execution against baseline backlog."
    )
    ap.add_argument("--demo-doc", default="docs/DEMO.html")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--baseline-report", default="out/m28_narrative_baseline_report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m28_narrative_execution_report.json")
    ap.add_argument("--required-work-id", default="PRG-272")
    ap.add_argument("--required-next-work-id", default="PRG-273")
    ap.add_argument("--required-ci-target", default="m28-narrative-execution-check")
    return ap.parse_args()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def has_all(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return all(p.lower() in lower for p in patterns)


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


def main() -> int:
    args = parse_args()

    demo_text = Path(args.demo_doc).read_text(encoding="utf-8")
    submission_text = Path(args.submission_doc).read_text(encoding="utf-8")
    usage_text = Path(args.usage_doc).read_text(encoding="utf-8")
    program_plan_text = Path(args.program_plan_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")

    baseline_report = load_json(Path(args.baseline_report))
    step_map = load_json(Path(args.step_map))

    baseline_backlog = baseline_report.get("backlog") if isinstance(baseline_report.get("backlog"), list) else []
    baseline_gap_ids = {
        str(row.get("id", "")).strip()
        for row in baseline_backlog
        if isinstance(row, dict)
    }
    baseline_metrics = baseline_report.get("metrics") if isinstance(baseline_report.get("metrics"), dict) else {}
    baseline_backlog_count = int(baseline_metrics.get("backlogCount", len(baseline_backlog)))

    items = step_map.get("items") if isinstance(step_map.get("items"), dict) else {}
    step_entry = items.get(args.required_work_id) if isinstance(items, dict) else None
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    commands_list = [str(c).strip() for c in commands] if isinstance(commands, list) else []
    step_note = step_entry.get("note") if isinstance(step_entry, dict) else ""

    checks: list[dict[str, Any]] = []
    baseline_has_required_ids = all(gid in baseline_gap_ids for gid in REQUIRED_BASELINE_GAP_IDS)
    baseline_zero_backlog = baseline_backlog_count == 0
    checks.append(
        {
            "id": "baseline_contains_required_gap_ids",
            "ok": baseline_has_required_ids or baseline_zero_backlog,
            "detail": (
                f"baseline_backlog_count={baseline_backlog_count} "
                f"required_ids_present={baseline_has_required_ids} "
                f"baseline_gap_ids={sorted(baseline_gap_ids)}"
            ),
        }
    )
    checks.append(
        {
            "id": "demo_story_anchor_updated",
            "ok": 'id="m28-story"' in demo_text and 'id="m27-story"' not in demo_text,
            "detail": "DEMO has m28 story id and no stale m27 id",
        }
    )
    checks.append(
        {
            "id": "demo_walkthrough_heading_updated",
            "ok": "M28 Story Walkthrough" in demo_text and "M27 Story Walkthrough" not in demo_text,
            "detail": "DEMO walkthrough heading updated to M28",
        }
    )
    checks.append(
        {
            "id": "demo_snapshot_link_added",
            "ok": "reports/m28_activation.report.json" in demo_text,
            "detail": "DEMO evidence list includes m28 activation snapshot",
        }
    )
    checks.append(
        {
            "id": "demo_snapshot_fetch_added",
            "ok": 'loadJson("reports/m28_activation.report.json")' in demo_text,
            "detail": "DEMO script fetches m28 activation snapshot",
        }
    )
    checks.append(
        {
            "id": "demo_stale_m26_label_removed",
            "ok": "M26 Handoff Governance" not in demo_text and "Governance Snapshot" in demo_text,
            "detail": "DEMO stale M26 governance card label replaced",
        }
    )
    checks.append(
        {
            "id": "submission_active_m26_removed",
            "ok": "active=M26" not in submission_text,
            "detail": "SUBMISSION no longer contains stale active=M26 snapshot claim",
        }
    )
    checks.append(
        {
            "id": "submission_mentions_m28_activation",
            "ok": has_all(
                submission_text,
                [
                    "M28 activation gate: PASS",
                    "out/m28_activation_report.json",
                ],
            ),
            "detail": "SUBMISSION includes M28 activation snapshot line",
        }
    )
    checks.append(
        {
            "id": "submission_mentions_m28_baseline",
            "ok": has_all(
                submission_text,
                [
                    "M28 website narrative baseline gate: PASS",
                    "out/m28_narrative_baseline_report.json",
                ],
            ),
            "detail": "SUBMISSION includes M28 narrative baseline snapshot line",
        }
    )
    checks.append(
        {
            "id": "step_map_has_prg272_entry",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map has entry for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_execution_target",
            "ok": any(args.required_ci_target in cmd for cmd in commands_list),
            "detail": f"{args.required_work_id}.commands={commands_list}",
        }
    )
    checks.append(
        {
            "id": "step_map_mentions_next_work",
            "ok": str(args.required_next_work_id) in str(step_note),
            "detail": f"{args.required_work_id}.note references {args.required_next_work_id}",
        }
    )
    checks.append(
        {
            "id": "make_target_exists",
            "ok": f"{args.required_ci_target}:" in makefile_text,
            "detail": f"Makefile contains {args.required_ci_target} target",
        }
    )
    checks.append(
        {
            "id": "make_ci_wires_execution_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci target includes {args.required_ci_target}",
        }
    )
    checks.append(
        {
            "id": "program_plan_mentions_prg272",
            "ok": has_all(
                program_plan_text,
                [
                    "PRG-272",
                    "M28-K2",
                    "m28-narrative-execution-check",
                    "out/m28_narrative_execution_report.json",
                ],
            ),
            "detail": "PROGRAM_PLAN includes PRG-272 command and artifact references",
        }
    )
    checks.append(
        {
            "id": "usage_mentions_prg272",
            "ok": has_all(
                usage_text,
                [
                    "PRG-272",
                    "make m28-narrative-execution-check",
                    "out/m28_narrative_execution_report.json",
                ],
            ),
            "detail": "USAGE includes PRG-272 execution command and artifact references",
        }
    )

    ok = all(bool(row.get("ok")) for row in checks)
    payload = {
        "label": "m28-narrative-execution-live",
        "ok": ok,
        "checks": checks,
        "summary": {
            "checkCount": len(checks),
            "passCount": sum(1 for row in checks if row.get("ok")),
            "failedIds": [str(row.get("id")) for row in checks if not row.get("ok")],
            "requiredWorkId": args.required_work_id,
            "requiredNextWorkId": args.required_next_work_id,
            "requiredCiTarget": args.required_ci_target,
            "baselineGapCount": len(baseline_gap_ids),
        },
    }
    write_json(Path(args.report_out), payload)

    if ok:
        print(
            "PASS: m28 narrative execution check ("
            f"checks={payload['summary']['passCount']}/{payload['summary']['checkCount']}, "
            f"report={args.report_out})"
        )
        return 0

    print(
        "FAIL: m28 narrative execution check ("
        f"failed={','.join(payload['summary']['failedIds'])}, "
        f"report={args.report_out})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

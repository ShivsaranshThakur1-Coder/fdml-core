#!/usr/bin/env python3
"""Build and validate persistent program goal state snapshot.

This file gives new agents a deterministic, machine-readable handoff view of:
- current active milestone
- work queue and status counts
- approval summary
- immediate next execution items
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_WORK_HEADERS = {
    "id",
    "title",
    "status",
    "milestone_id",
    "kpi_id",
    "evidence",
    "owner",
    "last_updated",
    "notes",
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Update or validate analysis/program/goal_state.json")
    ap.add_argument("--plan", default="analysis/program/plan.json", help="program plan JSON")
    ap.add_argument("--work", default="analysis/program/work_items.csv", help="work item CSV")
    ap.add_argument(
        "--approval",
        default="analysis/program/approval_report.json",
        help="approval report JSON (optional)",
    )
    ap.add_argument("--out", default="analysis/program/goal_state.json", help="output goal state JSON")
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify output is up to date (do not write)",
    )
    return ap.parse_args()


def load_plan(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path}: plan must be JSON object")
    return payload


def load_work_items(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_WORK_HEADERS - headers)
        if missing:
            raise RuntimeError(f"{path}: missing headers: {', '.join(missing)}")
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if all(not v for v in row.values()):
                continue
            rows.append(row)
    return rows


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def status_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {"planned": 0, "in_progress": 0, "done": 0, "blocked": 0, "deferred": 0}
    for row in rows:
        status = row.get("status", "")
        if status in counts:
            counts[status] += 1
    return counts


def compact_item(row: dict[str, str]) -> dict[str, str]:
    return {
        "id": row.get("id", ""),
        "title": row.get("title", ""),
        "status": row.get("status", ""),
        "milestoneId": row.get("milestone_id", ""),
        "kpiId": row.get("kpi_id", ""),
        "owner": row.get("owner", ""),
        "lastUpdated": row.get("last_updated", ""),
        "notes": row.get("notes", ""),
    }


def compact_item_with_evidence(row: dict[str, str]) -> dict[str, Any]:
    evidence_raw = row.get("evidence", "")
    evidence = [p.strip() for p in evidence_raw.split("|") if p.strip()]
    out = compact_item(row)
    out["evidenceCount"] = len(evidence)
    out["hasEvidence"] = bool(evidence)
    return out


def build_goal_state(
    plan: dict[str, Any],
    rows: list[dict[str, str]],
    approval: dict[str, Any] | None,
    *,
    plan_path: Path,
    work_path: Path,
    approval_path: Path,
) -> dict[str, Any]:
    active_id = str(plan.get("activeMilestone", "")).strip()
    milestones = plan.get("milestones", [])
    if not isinstance(milestones, list):
        milestones = []

    milestone_by_id: dict[str, dict[str, Any]] = {}
    for m in milestones:
        if isinstance(m, dict):
            mid = str(m.get("id", "")).strip()
            if mid:
                milestone_by_id[mid] = m

    active_milestone = milestone_by_id.get(active_id, {})
    active_kpis = active_milestone.get("kpis", []) if isinstance(active_milestone, dict) else []
    if not isinstance(active_kpis, list):
        active_kpis = []
    active_kpi_ids = [str(k.get("id", "")).strip() for k in active_kpis if isinstance(k, dict)]

    all_rows_sorted = sorted(rows, key=lambda r: r.get("id", ""))
    active_rows = [r for r in all_rows_sorted if r.get("milestone_id") == active_id]

    active_queue_rows = [
        r for r in active_rows if r.get("status") in {"in_progress", "planned", "blocked"}
    ]
    active_queue_rows.sort(key=lambda r: (0 if r.get("status") == "in_progress" else 1, r.get("id", "")))

    blocked_rows = [r for r in all_rows_sorted if r.get("status") == "blocked"]
    in_progress_rows = [r for r in all_rows_sorted if r.get("status") == "in_progress"]
    planned_rows = [r for r in all_rows_sorted if r.get("status") == "planned"]
    done_rows = [r for r in all_rows_sorted if r.get("status") == "done"]

    done_rows_recent = sorted(
        done_rows,
        key=lambda r: (r.get("last_updated", ""), r.get("id", "")),
        reverse=True,
    )[:10]

    done_missing_evidence = [
        compact_item_with_evidence(r)
        for r in done_rows
        if not [p for p in r.get("evidence", "").split("|") if p.strip()]
    ]

    milestone_summaries: list[dict[str, Any]] = []
    for m in milestones:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id", "")).strip()
        mkpis = m.get("kpis", [])
        if not isinstance(mkpis, list):
            mkpis = []
        mrows = [r for r in all_rows_sorted if r.get("milestone_id") == mid]
        milestone_summaries.append(
            {
                "id": mid,
                "title": str(m.get("title", "")).strip(),
                "status": str(m.get("status", "")).strip(),
                "kpiIds": [str(k.get("id", "")).strip() for k in mkpis if isinstance(k, dict)],
                "workCounts": status_counts(mrows),
            }
        )

    active_kpi_progress: list[dict[str, Any]] = []
    for k in active_kpis:
        if not isinstance(k, dict):
            continue
        kid = str(k.get("id", "")).strip()
        krows = [r for r in active_rows if r.get("kpi_id") == kid]
        kcounts = status_counts(krows)
        total = len(krows)
        done = kcounts["done"]
        ratio = float(done) / float(total) if total > 0 else 0.0
        active_kpi_progress.append(
            {
                "id": kid,
                "name": str(k.get("name", "")).strip(),
                "target": str(k.get("target", "")).strip(),
                "measure": str(k.get("measure", "")).strip(),
                "workCounts": kcounts,
                "completionRatio": round(ratio, 4),
            }
        )

    constraints = plan.get("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    max_wip = int(constraints.get("maxInProgressItems", 3))
    wip_count = len(in_progress_rows)

    approval_summary: dict[str, Any]
    if approval is None:
        approval_summary = {
            "available": False,
            "reportPath": str(approval_path),
        }
    else:
        approval_summary = {
            "available": True,
            "reportPath": str(approval_path),
            "programGateOk": bool(approval.get("programGate", {}).get("ok")),
            "approved": int(approval.get("approved", 0)),
            "denied": int(approval.get("denied", 0)),
            "totalDone": int(approval.get("totalDone", 0)),
            "failingDoneIds": sorted(
                [
                    str(a.get("id", "")).strip()
                    for a in approval.get("approvals", [])
                    if isinstance(a, dict) and not bool(a.get("approved"))
                ]
            ),
        }

    state = {
        "schemaVersion": "1",
        "sourceFiles": {
            "plan": str(plan_path),
            "workItems": str(work_path),
            "approvalReport": str(approval_path),
        },
        "projectContext": {
            "activeMilestoneId": active_id,
            "activeMilestoneTitle": str(active_milestone.get("title", "")).strip(),
            "activeMilestoneStatus": str(active_milestone.get("status", "")).strip(),
            "activeKpiIds": active_kpi_ids,
            "planUpdated": str(plan.get("updated", "")).strip(),
            "workItemTotal": len(all_rows_sorted),
            "statusCounts": status_counts(all_rows_sorted),
            "milestoneSummaries": milestone_summaries,
        },
        "executionState": {
            "activeQueue": [compact_item(r) for r in active_queue_rows],
            "inProgress": [compact_item(r) for r in in_progress_rows],
            "planned": [compact_item(r) for r in planned_rows],
            "blocked": [compact_item(r) for r in blocked_rows],
            "recentDone": [compact_item_with_evidence(r) for r in done_rows_recent],
        },
        "activeKpiProgress": active_kpi_progress,
        "qualitySignals": {
            "approval": approval_summary,
            "doneMissingEvidence": done_missing_evidence,
            "wipCount": wip_count,
            "maxInProgressItems": max_wip,
            "wipLimitExceeded": bool(wip_count > max_wip),
        },
        "nextExecutionHint": (
            "Continue with active queue item(s) for active milestone in order: in_progress first, then planned."
        ),
    }
    return state


def encode_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def check_up_to_date(out_path: Path, expected: str) -> int:
    if not out_path.exists():
        print(f"FAIL: missing goal state file: {out_path}")
        print("Run: make goal-state-update")
        return 1
    actual = out_path.read_text(encoding="utf-8")
    if actual == expected:
        print(f"PASS: goal state is up to date: {out_path}")
        return 0
    print(f"FAIL: goal state is stale: {out_path}")
    print("Run: make goal-state-update")
    diff = difflib.unified_diff(
        actual.splitlines(),
        expected.splitlines(),
        fromfile=str(out_path),
        tofile="expected",
        n=3,
        lineterm="",
    )
    for idx, line in enumerate(diff):
        print(line)
        if idx >= 60:
            print("... (diff truncated)")
            break
    return 1


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan)
    work_path = Path(args.work)
    approval_path = Path(args.approval)
    out_path = Path(args.out)

    try:
        plan = load_plan(plan_path)
        rows = load_work_items(work_path)
        approval = load_optional_json(approval_path)
        state = build_goal_state(
            plan,
            rows,
            approval,
            plan_path=plan_path,
            work_path=work_path,
            approval_path=approval_path,
        )
        encoded = encode_json(state)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 2

    if args.check:
        return check_up_to_date(out_path, encoded)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(encoded, encoding="utf-8")
    print(
        "Updated goal state:"
        f" {out_path} (active={state['projectContext']['activeMilestoneId']},"
        f" total={state['projectContext']['workItemTotal']},"
        f" in_progress={state['projectContext']['statusCounts']['in_progress']},"
        f" planned={state['projectContext']['statusCounts']['planned']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

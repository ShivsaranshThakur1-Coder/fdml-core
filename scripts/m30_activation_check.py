#!/usr/bin/env python3
"""M30 activation gate for post-M29 transition and queue bootstrap."""

from __future__ import annotations

import argparse
import csv
import json
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
    ap = argparse.ArgumentParser(description="Validate M30 activation and seeded work queue state.")
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m30_activation_report.json")
    ap.add_argument("--required-active-milestone", default="M30")
    ap.add_argument("--required-previous-milestone", default="M29")
    ap.add_argument("--required-activation-work-id", default="PRG-279")
    ap.add_argument("--required-next-work-id", default="PRG-280")
    ap.add_argument("--min-active-queue", type=int, default=1)
    return ap.parse_args()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"missing JSON file: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(obj, dict), f"{path} must contain a JSON object")
    return obj


def load_rows(path: Path) -> list[dict[str, str]]:
    require(path.exists(), f"missing CSV file: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_WORK_HEADERS - headers)
        require(not missing, f"{path} missing required headers: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if all(not v for v in row.values()):
                continue
            rows.append(row)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def has_all(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return all(p.lower() in lower for p in patterns)


def find_milestone(plan: dict[str, Any], milestone_id: str) -> dict[str, Any] | None:
    milestones = plan.get("milestones")
    if not isinstance(milestones, list):
        return None
    for row in milestones:
        if isinstance(row, dict) and str(row.get("id", "")).strip() == milestone_id:
            return row
    return None


def find_row(rows: list[dict[str, str]], item_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("id", "") == item_id:
            return row
    return None


def main() -> int:
    args = parse_args()

    plan = load_json(Path(args.plan))
    rows = load_rows(Path(args.work))
    goal_state = load_json(Path(args.goal_state))
    program_plan_text = Path(args.program_plan_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")

    checks: list[dict[str, Any]] = []

    active_plan = str(plan.get("activeMilestone", "")).strip()
    checks.append(
        {
            "id": "plan_active_m30",
            "ok": active_plan == args.required_active_milestone,
            "detail": f"plan.activeMilestone={active_plan!r}",
        }
    )

    prev = find_milestone(plan, args.required_previous_milestone)
    prev_status = str((prev or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "previous_milestone_completed",
            "ok": prev is not None and prev_status == "completed",
            "detail": f"{args.required_previous_milestone}.status={prev_status!r}",
        }
    )

    active = find_milestone(plan, args.required_active_milestone)
    active_status = str((active or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "active_milestone_status_active",
            "ok": active is not None and active_status == "active",
            "detail": f"{args.required_active_milestone}.status={active_status!r}",
        }
    )

    activation_row = find_row(rows, args.required_activation_work_id)
    activation_status = str((activation_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "activation_work_done",
            "ok": activation_row is not None and activation_status == "done",
            "detail": f"{args.required_activation_work_id}.status={activation_status!r}",
        }
    )

    next_row = find_row(rows, args.required_next_work_id)
    next_status = str((next_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "next_work_seeded",
            "ok": next_row is not None and next_status in {"planned", "in_progress", "done"},
            "detail": f"{args.required_next_work_id}.status={next_status!r}",
        }
    )

    m30_rows = [r for r in rows if r.get("milestone_id", "") == args.required_active_milestone]
    m30_open = [r for r in m30_rows if r.get("status", "") in {"planned", "in_progress", "blocked"}]
    checks.append(
        {
            "id": "m30_active_queue_seeded",
            "ok": len(m30_open) >= args.min_active_queue,
            "detail": f"open_m30_rows={len(m30_open)} min={args.min_active_queue}",
        }
    )

    goal_project = goal_state.get("projectContext") if isinstance(goal_state.get("projectContext"), dict) else {}
    goal_exec = goal_state.get("executionState") if isinstance(goal_state.get("executionState"), dict) else {}
    goal_active = str(goal_project.get("activeMilestoneId", "")).strip()
    goal_active_queue = goal_exec.get("activeQueue") if isinstance(goal_exec.get("activeQueue"), list) else []
    checks.append(
        {
            "id": "goal_state_active_m30",
            "ok": goal_active == args.required_active_milestone,
            "detail": f"goal_state.activeMilestoneId={goal_active!r}",
        }
    )
    checks.append(
        {
            "id": "goal_state_active_queue_seeded",
            "ok": len(goal_active_queue) >= args.min_active_queue,
            "detail": f"goal_state.activeQueueCount={len(goal_active_queue)} min={args.min_active_queue}",
        }
    )

    checks.append(
        {
            "id": "make_target_exists",
            "ok": "m30-activation-check:" in makefile_text,
            "detail": "Makefile contains m30-activation-check target",
        }
    )
    checks.append(
        {
            "id": "make_ci_wires_m30_activation",
            "ok": "ci:" in makefile_text and "m30-activation-check" in makefile_text,
            "detail": "Makefile ci target includes m30-activation-check",
        }
    )

    checks.append(
        {
            "id": "program_plan_mentions_m30",
            "ok": has_all(
                program_plan_text,
                [
                    "M30",
                    args.required_activation_work_id,
                    args.required_next_work_id,
                    "m30-activation-check",
                    "out/m30_activation_report.json",
                ],
            ),
            "detail": "PROGRAM_PLAN.md includes M30 activation state and next step",
        }
    )

    failed = [row for row in checks if not bool(row.get("ok"))]
    report = {
        "schemaVersion": "1",
        "label": "m30-activation-live",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "programPlanDoc": args.program_plan_doc,
            "makefile": args.makefile,
        },
        "metrics": {
            "activeMilestone": active_plan,
            "m30TotalRows": len(m30_rows),
            "m30OpenRows": len(m30_open),
            "goalStateActiveQueueCount": len(goal_active_queue),
        },
        "checks": checks,
        "ok": len(failed) == 0,
    }
    write_json(Path(args.report_out), report)

    if failed:
        for row in failed:
            print(f"FAIL {row['id']}: {row['detail']}")
        print(f"Created: {args.report_out}")
        print("Summary: FAIL")
        return 1

    for row in checks:
        print(f"PASS {row['id']}: {row['detail']}")
    print(f"Created: {args.report_out}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

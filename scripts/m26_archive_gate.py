#!/usr/bin/env python3
"""Archive-safe M26 gate for CI runs after milestone M26 is closed."""

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

OPEN_STATUSES = {"planned", "in_progress", "blocked"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate archived M26 closeout invariants under later active milestones."
    )
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--report-out", default="out/m26_archive_gate_report.json")
    ap.add_argument("--required-milestone-id", default="M26")
    ap.add_argument(
        "--required-work-id",
        action="append",
        default=[
            "PRG-260",
            "PRG-261",
            "PRG-262",
            "PRG-263",
            "PRG-264",
        ],
    )
    ap.add_argument(
        "--required-artifact",
        action="append",
        default=[
            "out/m26_activation_report.json",
            "out/m26_polish_baseline_report.json",
            "out/m26_polish_execution_report.json",
            "out/m26_handoff_governance_report.json",
        ],
    )
    ap.add_argument("--required-ci-target", default="m26-archive-check")
    ap.add_argument("--makefile", default="Makefile")
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


def find_row(rows: list[dict[str, str]], item_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("id", "") == item_id:
            return row
    return None


def find_milestone(plan: dict[str, Any], milestone_id: str) -> dict[str, Any] | None:
    milestones = plan.get("milestones")
    if not isinstance(milestones, list):
        return None
    for row in milestones:
        if isinstance(row, dict) and str(row.get("id", "")).strip() == milestone_id:
            return row
    return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    plan = load_json(Path(args.plan))
    rows = load_rows(Path(args.work))
    goal_state = load_json(Path(args.goal_state))
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")

    checks: list[dict[str, Any]] = []
    active_milestone = str(plan.get("activeMilestone", "")).strip()
    checks.append(
        {
            "id": "plan_has_active_milestone",
            "ok": bool(active_milestone),
            "detail": f"plan.activeMilestone={active_milestone!r}",
        }
    )

    m26 = find_milestone(plan, args.required_milestone_id)
    m26_status = str((m26 or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "m26_marked_completed",
            "ok": m26 is not None and m26_status == "completed",
            "detail": f"M26.status={m26_status!r}",
        }
    )

    m26_rows = [r for r in rows if r.get("milestone_id", "") == args.required_milestone_id]
    m26_open = [r for r in m26_rows if r.get("status", "").strip().lower() in OPEN_STATUSES]
    checks.append(
        {
            "id": "m26_open_queue_zero",
            "ok": len(m26_open) == 0,
            "detail": f"open_m26_rows={len(m26_open)}",
        }
    )

    for wid in args.required_work_id:
        row = find_row(rows, wid)
        status = str((row or {}).get("status", "")).strip().lower()
        checks.append(
            {
                "id": f"required_work_done_{wid}",
                "ok": row is not None and status == "done",
                "detail": f"{wid}.status={status!r}",
            }
        )

    for rel in args.required_artifact:
        path = Path(rel)
        exists = path.exists()
        json_ok = False
        if exists:
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                json_ok = isinstance(obj, dict)
            except Exception:
                json_ok = False
        checks.append(
            {
                "id": f"artifact_present_{path.name}",
                "ok": exists and json_ok,
                "detail": f"path={rel} exists={exists} jsonObject={json_ok}",
            }
        )

    goal_project = (
        goal_state.get("projectContext")
        if isinstance(goal_state.get("projectContext"), dict)
        else {}
    )
    goal_exec = (
        goal_state.get("executionState")
        if isinstance(goal_state.get("executionState"), dict)
        else {}
    )
    goal_active = str(goal_project.get("activeMilestoneId", "")).strip()
    active_queue = goal_exec.get("activeQueue") if isinstance(goal_exec.get("activeQueue"), list) else []
    checks.append(
        {
            "id": "goal_state_active_milestone_present",
            "ok": bool(goal_active),
            "detail": f"goal_state.activeMilestoneId={goal_active!r}",
        }
    )
    checks.append(
        {
            "id": "goal_state_active_queue_is_list",
            "ok": isinstance(active_queue, list),
            "detail": f"goal_state.activeQueueCount={len(active_queue)}",
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
            "id": "make_ci_wires_archive_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci target includes {args.required_ci_target}",
        }
    )

    ok = all(bool(row.get("ok")) for row in checks)
    payload = {
        "label": "m26-archive-gate-live",
        "ok": ok,
        "checks": checks,
        "metrics": {
            "activeMilestone": active_milestone,
            "goalStateActiveMilestone": goal_active,
            "m26TotalRows": len(m26_rows),
            "m26OpenRows": len(m26_open),
            "requiredWorkCount": len(args.required_work_id),
            "requiredArtifactCount": len(args.required_artifact),
        },
        "summary": {
            "checkCount": len(checks),
            "passCount": sum(1 for row in checks if row.get("ok")),
            "failedIds": [str(row.get("id")) for row in checks if not row.get("ok")],
            "requiredCiTarget": args.required_ci_target,
        },
    }
    write_json(Path(args.report_out), payload)

    if ok:
        print(
            "PASS: m26 archive gate ("
            f"checks={payload['summary']['passCount']}/{payload['summary']['checkCount']}, "
            f"report={args.report_out})"
        )
        return 0

    print(
        "FAIL: m26 archive gate ("
        f"failed={','.join(payload['summary']['failedIds'])}, "
        f"report={args.report_out})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

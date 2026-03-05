#!/usr/bin/env python3
"""Execute active queue work items automatically until a milestone boundary or failure."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_PREFLIGHT_COMMANDS = [
    "make program-check",
    "make task-approval-check",
    "make goal-state-update",
]

DEFAULT_POST_STEP_COMMANDS = [
    "make program-check",
    "make task-approval-check",
    "make goal-state-update",
]

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

STATUS_ORDER = {"in_progress": 0, "planned": 1}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Autopilot for analysis/program active queue")
    ap.add_argument("--plan", default="analysis/program/plan.json", help="program plan JSON")
    ap.add_argument("--work", default="analysis/program/work_items.csv", help="work item CSV")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json", help="goal state JSON output path")
    ap.add_argument("--map", default="analysis/program/step_execution_map.json", help="PRG to command map JSON")
    ap.add_argument("--max-items", type=int, default=10, help="max queue items to execute in this run")
    ap.add_argument("--owner", default="codex", help="owner string written on completed rows")
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="last_updated date (YYYY-MM-DD)")
    ap.add_argument("--allow-cross-milestone", action="store_true", help="continue if active milestone changes")
    ap.add_argument("--allow-missing-map", action="store_true", help="skip unmapped PRG ids instead of failing")
    ap.add_argument("--skip-preflight", action="store_true", help="skip preflight checks")
    ap.add_argument("--dry-run", action="store_true", help="print selected actions without changing files")
    return ap.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def load_work_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        missing = sorted(REQUIRED_WORK_HEADERS - set(headers))
        if missing:
            raise RuntimeError(f"{path} missing required headers: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if all(not v for v in row.values()):
                continue
            rows.append(row)
    return headers, rows


def write_work_rows(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def split_paths(value: str) -> list[str]:
    return [p.strip() for p in value.split("|") if p.strip()]


def join_paths(values: list[str]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        v = value.strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return "|".join(out)


def active_queue(rows: list[dict[str, str]], active_milestone: str) -> list[dict[str, str]]:
    queue = [
        row
        for row in rows
        if row.get("milestone_id") == active_milestone and row.get("status") in STATUS_ORDER
    ]
    queue.sort(key=lambda r: (STATUS_ORDER.get(r.get("status", "planned"), 9), r.get("id", "")))
    return queue


def run_command(repo_root: Path, command: str, *, dry_run: bool = False) -> int:
    print(f"[autopilot] run: {command}")
    if dry_run:
        return 0
    proc = subprocess.run(command, cwd=str(repo_root), shell=True, check=False)
    return int(proc.returncode)


def map_for_id(exec_map: dict[str, Any], item_id: str) -> dict[str, Any]:
    return (
        exec_map.get("items", {}).get(item_id)
        if isinstance(exec_map.get("items"), dict)
        else {}
    ) if isinstance(exec_map, dict) else {}


def main() -> int:
    args = parse_args()
    if args.max_items <= 0:
        print("FAIL: --max-items must be > 0")
        return 2

    repo_root = Path(".").resolve()
    plan_path = (repo_root / args.plan).resolve()
    work_path = (repo_root / args.work).resolve()
    map_path = (repo_root / args.map).resolve()

    for p in (plan_path, work_path, map_path):
        if not p.exists():
            print(f"FAIL: missing required file: {p}")
            return 2

    try:
        exec_map = load_json(map_path)
    except Exception as exc:
        print(f"FAIL: unable to read execution map: {exc}")
        return 2

    if not args.skip_preflight:
        for cmd in DEFAULT_PREFLIGHT_COMMANDS:
            rc = run_command(repo_root, cmd, dry_run=args.dry_run)
            if rc != 0:
                print(f"FAIL: preflight command failed ({rc}): {cmd}")
                return rc

    start_plan = load_json(plan_path)
    start_milestone = str(start_plan.get("activeMilestone") or "").strip()
    if not start_milestone:
        print("FAIL: active milestone missing in plan")
        return 2

    executed: list[str] = []
    simulated_done: set[str] = set()

    for _ in range(args.max_items):
        plan = load_json(plan_path)
        active_milestone = str(plan.get("activeMilestone") or "").strip()
        if not active_milestone:
            print("FAIL: active milestone missing in plan")
            return 2

        if executed and not args.allow_cross_milestone and active_milestone != start_milestone:
            print(
                "[autopilot] stop: milestone boundary reached "
                f"({start_milestone} -> {active_milestone})"
            )
            break

        headers, rows = load_work_rows(work_path)
        queue = active_queue(rows, active_milestone)
        if args.dry_run and simulated_done:
            queue = [row for row in queue if str(row.get("id") or "").strip() not in simulated_done]
        if not queue:
            print(f"[autopilot] stop: no in_progress/planned rows for active milestone {active_milestone}")
            break

        item = queue[0]
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            print("FAIL: next queue item has no id")
            return 2

        entry = map_for_id(exec_map, item_id)
        commands = entry.get("commands") if isinstance(entry, dict) else []
        if (
            not isinstance(commands, list)
            or len(commands) == 0
            or not all(isinstance(c, str) and c.strip() for c in commands)
        ):
            msg = f"no execution commands mapped for {item_id} in {args.map}"
            if args.allow_missing_map:
                print(f"[autopilot] skip: {msg}")
                break
            print(f"[autopilot] stop: {msg}")
            break

        print(f"[autopilot] execute item {item_id} ({item.get('title', '')})")
        for cmd in commands:
            rc = run_command(repo_root, cmd, dry_run=args.dry_run)
            if rc != 0:
                print(f"FAIL: item {item_id} command failed ({rc}): {cmd}")
                return rc

        if args.dry_run:
            executed.append(item_id)
            simulated_done.add(item_id)
            continue

        note = str(entry.get("note") or "").strip()
        extra_evidence = entry.get("appendEvidence")
        extra_paths = [str(v).strip() for v in extra_evidence] if isinstance(extra_evidence, list) else []

        updated = False
        for row in rows:
            if row.get("id") != item_id:
                continue
            row["status"] = "done"
            row["owner"] = args.owner
            row["last_updated"] = args.date
            if note:
                row["notes"] = note
            if extra_paths:
                merged = split_paths(row.get("evidence", "")) + extra_paths
                row["evidence"] = join_paths(merged)
            updated = True
            break

        if not updated:
            print(f"FAIL: could not update row for {item_id}")
            return 2

        write_work_rows(work_path, headers, rows)
        print(f"[autopilot] marked done: {item_id}")

        for cmd in DEFAULT_POST_STEP_COMMANDS:
            rc = run_command(repo_root, cmd, dry_run=False)
            if rc != 0:
                print(f"FAIL: post-step command failed ({rc}) after {item_id}: {cmd}")
                return rc

        executed.append(item_id)

    if not args.dry_run:
        # ensure goal-state file is refreshed at end, even when loop exits early.
        rc = run_command(repo_root, f"python3 scripts/update_goal_state.py --plan {args.plan} --work {args.work} --approval analysis/program/approval_report.json --out {args.goal_state}")
        if rc != 0:
            print(f"FAIL: final goal-state refresh failed ({rc})")
            return rc

    print(
        f"[autopilot] summary: executed={len(executed)} "
        + ("none" if not executed else ",".join(executed))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

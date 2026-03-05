#!/usr/bin/env python3
"""Program-level guardrail gate for milestone/KPI-driven execution."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_WORK_STATUSES = {"planned", "in_progress", "done", "blocked", "deferred"}
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


def load_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"failed to read plan '{path}': {exc}") from exc
    if not isinstance(plan, dict):
        raise RuntimeError("plan must be a JSON object")
    return plan


def validate_plan(plan: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]], str, int, bool, bool]:
    errors: list[str] = []

    active = str(plan.get("activeMilestone", "")).strip()
    if not active:
        errors.append("plan.activeMilestone is required")

    constraints = plan.get("constraints", {})
    if not isinstance(constraints, dict):
        errors.append("plan.constraints must be an object")
        constraints = {}

    max_in_progress = constraints.get("maxInProgressItems", 3)
    try:
        max_in_progress = int(max_in_progress)
    except Exception:
        errors.append("constraints.maxInProgressItems must be an integer")
        max_in_progress = 3
    if max_in_progress < 1:
        errors.append("constraints.maxInProgressItems must be >= 1")

    require_mapping = bool(constraints.get("requireMilestoneMapping", True))
    require_evidence_done = bool(constraints.get("requireEvidenceForDone", True))

    milestones = plan.get("milestones", [])
    if not isinstance(milestones, list) or not milestones:
        errors.append("plan.milestones must be a non-empty array")
        milestones = []

    milestone_map: dict[str, dict[str, Any]] = {}
    kpi_map: dict[str, dict[str, Any]] = {}
    active_count = 0

    for idx, m in enumerate(milestones):
        if not isinstance(m, dict):
            errors.append(f"milestones[{idx}] must be an object")
            continue
        mid = str(m.get("id", "")).strip()
        if not mid:
            errors.append(f"milestones[{idx}].id is required")
            continue
        if mid in milestone_map:
            errors.append(f"duplicate milestone id '{mid}'")
            continue

        status = str(m.get("status", "")).strip().lower()
        if status not in {"active", "planned", "completed"}:
            errors.append(f"milestone '{mid}' has invalid status '{status}'")
        if status == "active":
            active_count += 1
        milestone_map[mid] = m

        kpis = m.get("kpis", [])
        if not isinstance(kpis, list) or not kpis:
            errors.append(f"milestone '{mid}' must define non-empty kpis")
            continue
        for kidx, k in enumerate(kpis):
            if not isinstance(k, dict):
                errors.append(f"milestone '{mid}' kpis[{kidx}] must be an object")
                continue
            kid = str(k.get("id", "")).strip()
            if not kid:
                errors.append(f"milestone '{mid}' kpis[{kidx}].id is required")
                continue
            if kid in kpi_map:
                errors.append(f"duplicate KPI id '{kid}'")
                continue
            target = str(k.get("target", "")).strip()
            measure = str(k.get("measure", "")).strip()
            if not target:
                errors.append(f"KPI '{kid}' missing target")
            if not measure:
                errors.append(f"KPI '{kid}' missing measure")
            kpi_map[kid] = {"milestone_id": mid, "kpi": k}

    if active_count != 1:
        errors.append(f"exactly one active milestone required; found {active_count}")
    if active and active not in milestone_map:
        errors.append(f"activeMilestone '{active}' not found in milestones")
    elif active and str(milestone_map[active].get("status", "")).strip().lower() != "active":
        errors.append(f"activeMilestone '{active}' must have status='active'")

    return errors, milestone_map, kpi_map, active, max_in_progress, require_mapping, require_evidence_done


def load_work_items(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    errors: list[str] = []
    rows: list[dict[str, str]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])
            missing_headers = sorted(REQUIRED_WORK_HEADERS - headers)
            if missing_headers:
                errors.append(f"work item file missing headers: {', '.join(missing_headers)}")
            for raw in reader:
                row = {k: (v or "").strip() for k, v in raw.items()}
                # skip completely empty rows
                if all(not v for v in row.values()):
                    continue
                rows.append(row)
    except Exception as exc:
        errors.append(f"failed to read work items '{path}': {exc}")
    return errors, rows


def validate_work_items(
    rows: list[dict[str, str]],
    milestone_map: dict[str, dict[str, Any]],
    kpi_map: dict[str, dict[str, Any]],
    active_milestone: str,
    max_in_progress: int,
    require_mapping: bool,
    require_evidence_done: bool,
) -> tuple[list[str], dict[str, int], int]:
    errors: list[str] = []
    per_status: dict[str, int] = {s: 0 for s in sorted(ALLOWED_WORK_STATUSES)}
    in_progress_count = 0
    seen_ids: set[str] = set()

    for idx, row in enumerate(rows, start=2):
        item_id = row.get("id", "")
        status = row.get("status", "")
        milestone_id = row.get("milestone_id", "")
        kpi_id = row.get("kpi_id", "")
        evidence = row.get("evidence", "")

        if not item_id:
            errors.append(f"work_items.csv:{idx} missing id")
            continue
        if item_id in seen_ids:
            errors.append(f"work_items.csv:{idx} duplicate id '{item_id}'")
        seen_ids.add(item_id)

        if status not in ALLOWED_WORK_STATUSES:
            errors.append(f"work_items.csv:{idx} item '{item_id}' has invalid status '{status}'")
            continue
        per_status[status] += 1

        if require_mapping and status != "deferred":
            if not milestone_id:
                errors.append(f"work_items.csv:{idx} item '{item_id}' missing milestone_id")
            elif milestone_id not in milestone_map:
                errors.append(f"work_items.csv:{idx} item '{item_id}' references unknown milestone '{milestone_id}'")

            if not kpi_id:
                errors.append(f"work_items.csv:{idx} item '{item_id}' missing kpi_id")
            elif kpi_id not in kpi_map:
                errors.append(f"work_items.csv:{idx} item '{item_id}' references unknown KPI '{kpi_id}'")
            elif milestone_id and milestone_id in milestone_map and kpi_id in kpi_map:
                expected_mid = kpi_map[kpi_id]["milestone_id"]
                if milestone_id != expected_mid:
                    errors.append(
                        f"work_items.csv:{idx} item '{item_id}' maps milestone '{milestone_id}' "
                        f"but KPI '{kpi_id}' belongs to '{expected_mid}'"
                    )

        if status == "in_progress":
            in_progress_count += 1
            if milestone_id != active_milestone:
                errors.append(
                    f"work_items.csv:{idx} item '{item_id}' is in_progress but not in active milestone '{active_milestone}'"
                )

        if status == "done" and require_evidence_done and not evidence:
            errors.append(f"work_items.csv:{idx} item '{item_id}' is done but missing evidence")

    if in_progress_count > max_in_progress:
        errors.append(
            f"in_progress item count {in_progress_count} exceeds maxInProgressItems {max_in_progress}"
        )

    return errors, per_status, in_progress_count


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate milestone/KPI guardrail files.")
    ap.add_argument("--plan", default="analysis/program/plan.json", help="program plan JSON")
    ap.add_argument("--work", default="analysis/program/work_items.csv", help="work item CSV")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = Path(args.plan)
    work_path = Path(args.work)

    errors: list[str] = []

    if not plan_path.exists():
        print(f"FAIL: missing plan file: {plan_path}")
        return 2
    if not work_path.exists():
        print(f"FAIL: missing work item file: {work_path}")
        return 2

    plan = load_plan(plan_path)
    p_errs, milestone_map, kpi_map, active, max_in_progress, require_mapping, require_evidence_done = validate_plan(plan)
    errors.extend(p_errs)

    w_load_errs, rows = load_work_items(work_path)
    errors.extend(w_load_errs)

    if not errors:
        w_errs, per_status, in_progress_count = validate_work_items(
            rows,
            milestone_map,
            kpi_map,
            active,
            max_in_progress,
            require_mapping,
            require_evidence_done,
        )
        errors.extend(w_errs)
    else:
        per_status = {}
        in_progress_count = 0

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        print(f"Summary: FAIL ({len(errors)} issue(s))")
        return 1

    total = len(rows)
    print(
        "Summary: PASS "
        f"(active={active}, total_items={total}, wip={in_progress_count}, "
        + ", ".join(f"{k}={v}" for k, v in per_status.items())
        + ")"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

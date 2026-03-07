#!/usr/bin/env python3
"""Deterministic M28 governance and final showcase handoff gate."""

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
        description="Validate M28 anti-drift governance and final showcase handoff synchronization."
    )
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--activation-report", default="out/m28_activation_report.json")
    ap.add_argument("--baseline-report", default="out/m28_narrative_baseline_report.json")
    ap.add_argument("--execution-report", default="out/m28_narrative_execution_report.json")
    ap.add_argument("--demo-doc", default="docs/DEMO.html")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--build-index-script", default="scripts/build_index.sh")
    ap.add_argument("--site-smoke-script", default="scripts/site_smoke.py")
    ap.add_argument("--report-out", default="out/m28_governance_handoff_report.json")
    ap.add_argument("--required-active-milestone", default="M28")
    ap.add_argument("--required-previous-work-id", default="PRG-272")
    ap.add_argument("--required-work-id", default="PRG-273")
    ap.add_argument("--required-ci-target", default="m28-governance-handoff-check")
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
    activation_report = load_json(Path(args.activation_report))
    baseline_report = load_json(Path(args.baseline_report))
    execution_report = load_json(Path(args.execution_report))

    demo_text = Path(args.demo_doc).read_text(encoding="utf-8")
    submission_text = Path(args.submission_doc).read_text(encoding="utf-8")
    usage_text = Path(args.usage_doc).read_text(encoding="utf-8")
    program_plan_text = Path(args.program_plan_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    build_index_text = Path(args.build_index_script).read_text(encoding="utf-8")
    site_smoke_text = Path(args.site_smoke_script).read_text(encoding="utf-8")

    step_map = load_json(Path(args.step_map))
    items = step_map.get("items") if isinstance(step_map.get("items"), dict) else {}
    step_entry = items.get(args.required_work_id) if isinstance(items, dict) else None
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    commands_list = [str(c).strip() for c in commands] if isinstance(commands, list) else []

    active_milestone = str(plan.get("activeMilestone", "")).strip()
    active_row = find_milestone(plan, args.required_active_milestone)
    active_status = str((active_row or {}).get("status", "")).strip().lower()
    goal_active = str(
        ((goal_state.get("projectContext") or {}).get("activeMilestoneId", ""))
    ).strip()

    prev_row = find_row(rows, args.required_previous_work_id)
    prev_status = str((prev_row or {}).get("status", "")).strip().lower()
    current_row = find_row(rows, args.required_work_id)
    current_status = str((current_row or {}).get("status", "")).strip().lower()

    m28_rows = [r for r in rows if r.get("milestone_id", "") == args.required_active_milestone]
    m28_open_rows = [r for r in m28_rows if r.get("status", "").strip().lower() in OPEN_STATUSES]
    m28_open_ids = sorted(r.get("id", "") for r in m28_open_rows)

    baseline_metrics = baseline_report.get("metrics") if isinstance(baseline_report.get("metrics"), dict) else {}
    baseline_backlog = baseline_report.get("backlog") if isinstance(baseline_report.get("backlog"), list) else []
    baseline_backlog_count = int(baseline_metrics.get("backlogCount", len(baseline_backlog)))

    activation_metrics = (
        activation_report.get("metrics") if isinstance(activation_report.get("metrics"), dict) else {}
    )
    activation_open_rows = int(activation_metrics.get("m28OpenRows", -1))

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "id": "plan_active_m28",
            "ok": active_milestone == args.required_active_milestone,
            "detail": f"plan.activeMilestone={active_milestone!r}",
        }
    )
    checks.append(
        {
            "id": "plan_m28_status_active",
            "ok": active_row is not None and active_status == "active",
            "detail": f"{args.required_active_milestone}.status={active_status!r}",
        }
    )
    checks.append(
        {
            "id": "goal_state_active_m28",
            "ok": goal_active == args.required_active_milestone,
            "detail": f"goal_state.activeMilestoneId={goal_active!r}",
        }
    )
    checks.append(
        {
            "id": "previous_work_done",
            "ok": prev_row is not None and prev_status == "done",
            "detail": f"{args.required_previous_work_id}.status={prev_status!r}",
        }
    )
    checks.append(
        {
            "id": "required_work_present",
            "ok": current_row is not None and current_status in OPEN_STATUSES.union({"done"}),
            "detail": f"{args.required_work_id}.status={current_status!r}",
        }
    )
    checks.append(
        {
            "id": "m28_open_queue_shape_valid",
            "ok": (len(m28_open_rows) == 0) or (len(m28_open_rows) == 1 and args.required_work_id in m28_open_ids),
            "detail": f"open_m28_rows={len(m28_open_rows)} open_ids={m28_open_ids}",
        }
    )
    checks.append(
        {
            "id": "activation_report_ok",
            "ok": bool(activation_report.get("ok", False)) and activation_open_rows >= 0,
            "detail": f"activation.ok={activation_report.get('ok', False)} m28OpenRows={activation_open_rows}",
        }
    )
    checks.append(
        {
            "id": "baseline_report_ok_and_backlog_zero",
            "ok": bool(baseline_report.get("ok", False)) and baseline_backlog_count == 0,
            "detail": (
                f"baseline.ok={baseline_report.get('ok', False)} "
                f"backlogCount={baseline_backlog_count}"
            ),
        }
    )
    checks.append(
        {
            "id": "execution_report_ok",
            "ok": bool(execution_report.get("ok", False)),
            "detail": f"execution.ok={execution_report.get('ok', False)}",
        }
    )
    checks.append(
        {
            "id": "step_map_has_prg273_entry",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map has entry for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_governance_target",
            "ok": any(args.required_ci_target in cmd for cmd in commands_list),
            "detail": f"{args.required_work_id}.commands={commands_list}",
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
            "id": "make_ci_wires_governance_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci target includes {args.required_ci_target}",
        }
    )
    checks.append(
        {
            "id": "program_plan_mentions_prg273",
            "ok": has_all(
                program_plan_text,
                [
                    "PRG-273",
                    "M28-K3",
                    "make m28-governance-handoff-check",
                    "out/m28_governance_handoff_report.json",
                ],
            ),
            "detail": "PROGRAM_PLAN includes PRG-273 governance command/artifact references",
        }
    )
    checks.append(
        {
            "id": "usage_mentions_prg273",
            "ok": has_all(
                usage_text,
                [
                    "PRG-273",
                    "make m28-governance-handoff-check",
                    "out/m28_governance_handoff_report.json",
                ],
            ),
            "detail": "USAGE includes PRG-273 governance command and artifact references",
        }
    )
    checks.append(
        {
            "id": "submission_mentions_prg273",
            "ok": has_all(
                submission_text,
                [
                    "PRG-273",
                    "make m28-governance-handoff-check",
                    "out/m28_governance_handoff_report.json",
                ],
            ),
            "detail": "SUBMISSION includes PRG-273 handoff command and artifact references",
        }
    )
    checks.append(
        {
            "id": "demo_links_m28_governance_snapshot",
            "ok": "reports/m28_governance_handoff.report.json" in demo_text,
            "detail": "DEMO includes m28 governance report snapshot link",
        }
    )
    checks.append(
        {
            "id": "demo_fetches_m28_governance_snapshot",
            "ok": 'loadJson("reports/m28_governance_handoff.report.json")' in demo_text,
            "detail": "DEMO fetches m28 governance report snapshot",
        }
    )
    checks.append(
        {
            "id": "build_index_snapshots_m28_governance",
            "ok": "out/m28_governance_handoff_report.json:m28_governance_handoff.report.json"
            in build_index_text,
            "detail": "build_index script snapshots m28 governance handoff report",
        }
    )
    checks.append(
        {
            "id": "site_smoke_requires_m28_governance_snapshot",
            "ok": "reports/m28_governance_handoff.report.json" in site_smoke_text,
            "detail": "site smoke requires m28 governance report snapshot",
        }
    )

    ok = all(bool(row.get("ok")) for row in checks)
    payload = {
        "label": "m28-governance-handoff-live",
        "ok": ok,
        "checks": checks,
        "metrics": {
            "activeMilestone": active_milestone,
            "goalStateActiveMilestone": goal_active,
            "prg273Status": current_status,
            "m28TotalRows": len(m28_rows),
            "m28OpenRows": len(m28_open_rows),
            "activationOpenRows": activation_open_rows,
            "baselineBacklogCount": baseline_backlog_count,
            "reportChainOk": bool(activation_report.get("ok", False))
            and bool(baseline_report.get("ok", False))
            and bool(execution_report.get("ok", False)),
        },
        "summary": {
            "checkCount": len(checks),
            "passCount": sum(1 for row in checks if row.get("ok")),
            "failedIds": [str(row.get("id")) for row in checks if not row.get("ok")],
            "requiredWorkId": args.required_work_id,
            "requiredPreviousWorkId": args.required_previous_work_id,
            "requiredCiTarget": args.required_ci_target,
        },
    }
    write_json(Path(args.report_out), payload)

    if ok:
        print(
            "PASS: m28 governance handoff check ("
            f"checks={payload['summary']['passCount']}/{payload['summary']['checkCount']}, "
            f"report={args.report_out})"
        )
        return 0

    print(
        "FAIL: m28 governance handoff check ("
        f"failed={','.join(payload['summary']['failedIds'])}, "
        f"report={args.report_out})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

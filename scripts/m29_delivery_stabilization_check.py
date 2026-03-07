#!/usr/bin/env python3
"""Deterministic M29 delivery-stabilization execution gate."""

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
REQUIRED_BASELINE_GAP_IDS = {"M29-BLG-001", "M29-BLG-003", "M29-BLG-005"}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate M29 delivery stabilization execution state.")
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--baseline-report", default="out/m29_release_baseline_report.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--gitignore", default=".gitignore")
    ap.add_argument("--report-out", default="out/m29_delivery_stabilization_report.json")
    ap.add_argument("--required-active-milestone", default="M29")
    ap.add_argument("--required-work-id", default="PRG-277")
    ap.add_argument("--required-next-work-id", default="PRG-278")
    ap.add_argument("--required-baseline-label", default="m29-release-workflow-baseline-live")
    ap.add_argument("--required-final-label", default="m25-final-product-baseline")
    ap.add_argument("--required-ci-target", default="m29-delivery-stabilization-check")
    ap.add_argument("--max-queued-gap-after", type=int, default=2)
    ap.add_argument("--max-open-queue-after", type=int, default=1)
    return ap.parse_args()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"missing JSON file: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(obj, dict), f"{path} must contain a JSON object")
    return obj


def load_work_rows(path: Path) -> list[dict[str, str]]:
    require(path.exists(), f"missing work items file: {path}")
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


def has_token(text: str, token: str) -> bool:
    return token.lower() in text.lower()


def doc_token_check(path: Path, required_tokens: list[str]) -> dict[str, Any]:
    require(path.exists(), f"missing document: {path}")
    text = path.read_text(encoding="utf-8")
    missing = [token for token in required_tokens if not has_token(text, token)]
    return {
        "path": str(path).replace("\\", "/"),
        "requiredTokens": required_tokens,
        "missingTokens": missing,
        "ok": len(missing) == 0,
    }


def find_milestone(plan: dict[str, Any], milestone_id: str) -> dict[str, Any] | None:
    milestones = plan.get("milestones")
    if not isinstance(milestones, list):
        return None
    for row in milestones:
        if isinstance(row, dict) and str(row.get("id", "")).strip() == milestone_id:
            return row
    return None


def find_work_row(rows: list[dict[str, str]], item_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("id") == item_id:
            return row
    return None


def count_pycache_dirs(repo_root: Path) -> int:
    count = 0
    for path in repo_root.rglob("__pycache__"):
        if path.is_dir():
            count += 1
    return count


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()

    plan = load_json(Path(args.plan))
    rows = load_work_rows(Path(args.work))
    goal_state = load_json(Path(args.goal_state))
    baseline = load_json(Path(args.baseline_report))
    final_report = load_json(Path(args.final_report))
    step_map = load_json(Path(args.step_map))
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    gitignore_text = Path(args.gitignore).read_text(encoding="utf-8")

    checks: list[dict[str, Any]] = []

    active_milestone = str(plan.get("activeMilestone", "")).strip()
    checks.append(
        {
            "id": "plan_active_m29",
            "ok": active_milestone == args.required_active_milestone,
            "detail": f"plan.activeMilestone={active_milestone!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    active = find_milestone(plan, args.required_active_milestone)
    active_status = str((active or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "active_milestone_status",
            "ok": active is not None and active_status == "active",
            "detail": f"{args.required_active_milestone}.status={active_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    goal_active = str((goal_state.get("projectContext") or {}).get("activeMilestoneId", "")).strip()
    checks.append(
        {
            "id": "goal_state_active_m29",
            "ok": goal_active == args.required_active_milestone,
            "detail": f"goalState.activeMilestoneId={goal_active!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    baseline_label = str(baseline.get("label", "")).strip()
    baseline_ok = bool(baseline.get("ok", False))
    checks.append(
        {
            "id": "baseline_report_ok",
            "ok": baseline_ok and baseline_label == args.required_baseline_label,
            "detail": f"baseline.ok={baseline_ok} baseline.label={baseline_label!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    final_label = str(final_report.get("label", "")).strip()
    final_ok = bool(final_report.get("ok", False))
    checks.append(
        {
            "id": "final_report_ok",
            "ok": final_ok and final_label == args.required_final_label,
            "detail": f"final.ok={final_ok} final.label={final_label!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    row_277 = find_work_row(rows, args.required_work_id)
    require(row_277 is not None, f"missing work item: {args.required_work_id}")
    status_277 = str((row_277 or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "work_item_277_done",
            "ok": status_277 == "done",
            "detail": f"{args.required_work_id}.status={status_277!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    row_278 = find_work_row(rows, args.required_next_work_id)
    require(row_278 is not None, f"missing work item: {args.required_next_work_id}")
    status_278 = str((row_278 or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "work_item_278_present",
            "ok": status_278 in {"planned", "in_progress", "done"},
            "detail": f"{args.required_next_work_id}.status={status_278!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    baseline_metrics = baseline.get("metrics") if isinstance(baseline.get("metrics"), dict) else {}
    baseline_queued_gaps = int(baseline_metrics.get("finalQueuedGapCount", -1))
    baseline_open_queue = int(baseline_metrics.get("openM29QueueCount", -1))
    baseline_pycache = int(baseline_metrics.get("pycacheDirCount", -1))
    baseline_tracked_changes = int(baseline_metrics.get("gitTrackedChanges", 0))
    baseline_untracked_changes = int(baseline_metrics.get("gitUntrackedChanges", 0))

    baseline_backlog = baseline.get("releaseBacklog") if isinstance(baseline.get("releaseBacklog"), list) else []
    baseline_gap_ids = {
        str(row.get("id", "")).strip()
        for row in baseline_backlog
        if isinstance(row, dict)
    }
    expected_gap_ids: set[str] = set()
    if baseline_pycache > 0 or (baseline_tracked_changes + baseline_untracked_changes) > 0:
        expected_gap_ids.add("M29-BLG-001")
    if baseline_queued_gaps > 0:
        expected_gap_ids.add("M29-BLG-003")
    if baseline_open_queue > 0:
        expected_gap_ids.add("M29-BLG-005")
    post_freeze_baseline_shape = (
        status_278 == "done" and baseline_open_queue == 0 and baseline_queued_gaps <= 0
    )
    checks.append(
        {
            "id": "baseline_has_required_prg277_backlog",
            "ok": expected_gap_ids.issubset(baseline_gap_ids)
            or REQUIRED_BASELINE_GAP_IDS.issubset(baseline_gap_ids)
            or post_freeze_baseline_shape,
            "detail": (
                f"baselineGapIds={sorted(baseline_gap_ids)} expectedGapIds={sorted(expected_gap_ids)} "
                f"postFreezeShape={post_freeze_baseline_shape}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    step_entry = ((step_map.get("items") or {}).get(args.required_work_id) or {})
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    note = step_entry.get("note") if isinstance(step_entry, dict) else ""
    checks.append(
        {
            "id": "step_map_contains_prg277_command",
            "ok": isinstance(commands, list)
            and any(args.required_ci_target in str(command) for command in commands),
            "detail": f"commands={commands!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "step_map_mentions_next_work",
            "ok": str(args.required_next_work_id) in str(note),
            "detail": f"{args.required_work_id}.note references {args.required_next_work_id}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "make_target_exists",
            "ok": f"{args.required_ci_target}:" in makefile_text,
            "detail": f"make target '{args.required_ci_target}' present",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "make_ci_wires_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"ci includes '{args.required_ci_target}'",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "gitignore_pycache_rules_present",
            "ok": "__pycache__/" in gitignore_text and "*.py[cod]" in gitignore_text,
            "detail": "gitignore includes __pycache__/ and *.py[cod]",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    program_plan_check = doc_token_check(
        Path(args.program_plan_doc),
        ["M29", "PRG-277", args.required_ci_target, "out/m29_delivery_stabilization_report.json"],
    )
    usage_check = doc_token_check(
        Path(args.usage_doc),
        ["PRG-277", f"make {args.required_ci_target}", "out/m29_delivery_stabilization_report.json"],
    )
    submission_check = doc_token_check(
        Path(args.submission_doc),
        ["PRG-277", f"make {args.required_ci_target}", "out/m29_delivery_stabilization_report.json"],
    )
    doc_checks = [program_plan_check, usage_check, submission_check]
    docs_with_gaps = [check for check in doc_checks if not check.get("ok")]
    checks.append(
        {
            "id": "docs_have_required_tokens",
            "ok": len(docs_with_gaps) == 0,
            "detail": f"docsWithGaps={len(docs_with_gaps)}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    final_summary = final_report.get("summary") if isinstance(final_report.get("summary"), dict) else {}
    current_queued_gaps = int(final_summary.get("queuedGapCount", -1))
    current_open_queue = sum(
        1
        for row in rows
        if row.get("milestone_id", "") == args.required_active_milestone
        and row.get("status", "").strip().lower() in OPEN_STATUSES
    )
    current_pycache = count_pycache_dirs(repo_root)

    queued_gap_reduction = baseline_queued_gaps - current_queued_gaps
    open_queue_reduction = baseline_open_queue - current_open_queue

    checks.append(
        {
            "id": "queued_gap_target",
            "ok": current_queued_gaps <= args.max_queued_gap_after,
            "detail": (
                f"baselineQueuedGaps={baseline_queued_gaps} currentQueuedGaps={current_queued_gaps} "
                f"targetMax={args.max_queued_gap_after}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "open_queue_target",
            "ok": current_open_queue <= args.max_open_queue_after,
            "detail": (
                f"baselineOpenQueue={baseline_open_queue} currentOpenQueue={current_open_queue} "
                f"targetMax={args.max_open_queue_after}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "queued_gap_non_regression_vs_baseline",
            "ok": baseline_queued_gaps < 0 or current_queued_gaps <= baseline_queued_gaps,
            "detail": (
                f"baselineQueuedGaps={baseline_queued_gaps} currentQueuedGaps={current_queued_gaps}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "open_queue_non_regression_vs_baseline",
            "ok": baseline_open_queue < 0 or current_open_queue <= baseline_open_queue,
            "detail": (
                f"baselineOpenQueue={baseline_open_queue} currentOpenQueue={current_open_queue}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "pycache_non_regression",
            "ok": baseline_pycache < 0 or current_pycache <= baseline_pycache,
            "detail": f"baselinePycache={baseline_pycache} currentPycache={current_pycache}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    resolution: list[dict[str, Any]] = []
    for row in baseline_backlog:
        if not isinstance(row, dict):
            continue
        backlog_id = str(row.get("id", "")).strip()
        linked = str(row.get("linkedWorkItemId", "")).strip()
        status = "deferred"
        reason = "linked to later work"
        if linked == args.required_work_id and backlog_id == "M29-BLG-001":
            status = "mitigated" if current_pycache <= baseline_pycache else "open"
            reason = f"pycache baseline={baseline_pycache} current={current_pycache}"
        elif linked == args.required_work_id and backlog_id == "M29-BLG-003":
            status = "resolved" if current_queued_gaps <= args.max_queued_gap_after else "open"
            reason = (
                f"queuedGap baseline={baseline_queued_gaps} current={current_queued_gaps} "
                f"reduction={queued_gap_reduction}"
            )
        elif linked == args.required_work_id and backlog_id == "M29-BLG-005":
            status = "resolved" if current_open_queue <= args.max_open_queue_after else "open"
            reason = (
                f"openQueue baseline={baseline_open_queue} current={current_open_queue} "
                f"reduction={open_queue_reduction}"
            )
        elif linked == args.required_next_work_id:
            status = "deferred_to_prg278"
            reason = f"handoff to {args.required_next_work_id}"
        resolution.append(
            {
                "id": backlog_id,
                "linkedWorkItemId": linked,
                "status": status,
                "reason": reason,
            }
        )

    report = {
        "schemaVersion": "1",
        "label": "m29-delivery-stabilization-live",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "baselineReport": args.baseline_report,
            "finalReport": args.final_report,
            "stepExecutionMap": args.step_map,
            "programPlanDoc": args.program_plan_doc,
            "submissionDoc": args.submission_doc,
            "usageDoc": args.usage_doc,
            "makefile": args.makefile,
        },
        "metrics": {
            "activeMilestone": active_milestone,
            "baselineQueuedGapCount": baseline_queued_gaps,
            "currentQueuedGapCount": current_queued_gaps,
            "queuedGapReduction": queued_gap_reduction,
            "baselineOpenQueueCount": baseline_open_queue,
            "currentOpenQueueCount": current_open_queue,
            "openQueueReduction": open_queue_reduction,
            "baselinePycacheDirCount": baseline_pycache,
            "currentPycacheDirCount": current_pycache,
            "releaseReady": bool(final_report.get("releaseReady", False)),
            "docGapCount": len(docs_with_gaps),
        },
        "checks": checks,
        "docChecks": doc_checks,
        "backlogResolution": resolution,
        "ok": True,
    }

    out_path = Path(args.report_out)
    write_json(out_path, report)

    for row in checks:
        print(f"PASS {row['id']}: {row['detail']}")
    print(
        "Backlog resolution: "
        + ", ".join(
            f"{entry['id']}={entry['status']}" for entry in resolution if entry.get("id")
        )
    )
    print(f"Created: {out_path}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

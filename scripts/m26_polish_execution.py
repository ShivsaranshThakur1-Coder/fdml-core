#!/usr/bin/env python3
"""Deterministic M26 polish execution gate for repo/docs cleanup pass."""

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
    ap = argparse.ArgumentParser(description="Validate M26 repo/docs polish execution state.")
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--baseline-report", default="out/m26_polish_baseline_report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--coverage-doc", default="docs/COVERAGE.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--gitignore", default=".gitignore")
    ap.add_argument("--report-out", default="out/m26_polish_execution_report.json")
    ap.add_argument("--required-active-milestone", default="M26")
    ap.add_argument("--required-work-id", default="PRG-262")
    ap.add_argument("--required-next-work-id", default="PRG-263")
    ap.add_argument("--required-baseline-label", default="m26-production-polish-baseline")
    ap.add_argument("--required-ci-target", default="m26-polish-execution-check")
    ap.add_argument("--max-doc-gap-after", type=int, default=0)
    ap.add_argument("--max-docs-missing-m26-after", type=int, default=0)
    ap.add_argument("--max-pycache-after", type=int, default=0)
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
    goal_state = load_json(Path(args.goal_state))
    baseline = load_json(Path(args.baseline_report))
    step_map = load_json(Path(args.step_map))
    rows = load_work_rows(Path(args.work))
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    gitignore_text = Path(args.gitignore).read_text(encoding="utf-8")

    checks: list[dict[str, Any]] = []

    active_milestone = str(plan.get("activeMilestone", "")).strip()
    checks.append(
        {
            "id": "plan_active_m26",
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
            "id": "goal_state_active_m26",
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

    row_262 = find_work_row(rows, args.required_work_id)
    require(row_262 is not None, f"missing work item: {args.required_work_id}")
    row_262_status = str((row_262 or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "work_item_262_present",
            "ok": row_262_status in {"planned", "in_progress", "done"},
            "detail": f"{args.required_work_id}.status={row_262_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    row_263 = find_work_row(rows, args.required_next_work_id)
    require(row_263 is not None, f"missing work item: {args.required_next_work_id}")
    row_263_status = str((row_263 or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "work_item_263_present",
            "ok": row_263_status in {"planned", "in_progress", "done"},
            "detail": f"{args.required_next_work_id}.status={row_263_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    step_entry = ((step_map.get("items") or {}).get(args.required_work_id) or {})
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    step_map_ok = isinstance(commands, list) and any(
        args.required_ci_target in str(command) for command in commands
    )
    checks.append(
        {
            "id": "step_map_contains_prg262_command",
            "ok": step_map_ok,
            "detail": f"commands={commands!r}",
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
        ["M26", "PRG-262", "m26-polish-execution-check", "out/m26_polish_execution_report.json"],
    )
    submission_check = doc_token_check(
        Path(args.submission_doc),
        ["M26", "m26-polish-baseline-check", "m26-polish-execution-check", "out/m26_polish_execution_report.json"],
    )
    coverage_check = doc_token_check(
        Path(args.coverage_doc),
        ["M26", "out/m26_polish_baseline_report.json", "out/m26_polish_execution_report.json"],
    )
    usage_check = doc_token_check(
        Path(args.usage_doc),
        ["M26", "make m26-polish-baseline-check", "make m26-polish-execution-check", "out/m26_polish_execution_report.json"],
    )

    doc_checks = [program_plan_check, submission_check, coverage_check, usage_check]
    doc_gap_after = sum(1 for check in doc_checks if not bool(check.get("ok", False)))
    docs_missing_m26_after = sum(
        1
        for check in doc_checks
        if any(str(token).strip().lower() == "m26" for token in check.get("missingTokens", []))
    )
    pycache_after = count_pycache_dirs(repo_root)

    baseline_metrics = baseline.get("metrics") if isinstance(baseline.get("metrics"), dict) else {}
    doc_gap_before = int(baseline_metrics.get("docGapCount", -1))
    docs_missing_before = int(baseline_metrics.get("docsMissingM26Count", -1))
    pycache_before = int(baseline_metrics.get("pycacheDirCount", -1))

    checks.append(
        {
            "id": "doc_gap_closed",
            "ok": doc_gap_after <= args.max_doc_gap_after,
            "detail": f"docGapAfter={doc_gap_after} max={args.max_doc_gap_after}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "docs_missing_m26_closed",
            "ok": docs_missing_m26_after <= args.max_docs_missing_m26_after,
            "detail": f"docsMissingM26After={docs_missing_m26_after} max={args.max_docs_missing_m26_after}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "pycache_closed",
            "ok": pycache_after <= args.max_pycache_after,
            "detail": f"pycacheAfter={pycache_after} max={args.max_pycache_after}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "doc_gap_non_regression",
            "ok": doc_gap_before < 0 or doc_gap_after <= doc_gap_before,
            "detail": f"docGapBefore={doc_gap_before} docGapAfter={doc_gap_after}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "docs_missing_non_regression",
            "ok": docs_missing_before < 0 or docs_missing_m26_after <= docs_missing_before,
            "detail": (
                f"docsMissingM26Before={docs_missing_before} "
                f"docsMissingM26After={docs_missing_m26_after}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "pycache_non_regression",
            "ok": pycache_before < 0 or pycache_after <= pycache_before,
            "detail": f"pycacheBefore={pycache_before} pycacheAfter={pycache_after}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    backlog = baseline.get("cleanupBacklog") if isinstance(baseline.get("cleanupBacklog"), list) else []
    linked_262 = [row for row in backlog if isinstance(row, dict) and str(row.get("linkedWorkItemId", "")) == args.required_work_id]
    linked_263 = [row for row in backlog if isinstance(row, dict) and str(row.get("linkedWorkItemId", "")) == args.required_next_work_id]
    checks.append(
        {
            "id": "baseline_backlog_linked_to_prg262",
            "ok": len(linked_262) >= 1,
            "detail": f"baselineLinkedTo{args.required_work_id}={len(linked_262)}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "baseline_backlog_linked_to_prg263",
            "ok": len(linked_263) >= (0 if row_263_status == "done" else 1),
            "detail": (
                f"baselineLinkedTo{args.required_next_work_id}={len(linked_263)} "
                f"requiredMin={(0 if row_263_status == 'done' else 1)} "
                f"prg263Status={row_263_status!r}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    open_m26_rows = [
        row
        for row in rows
        if row.get("milestone_id") == args.required_active_milestone
        and row.get("status") in {"planned", "in_progress", "blocked"}
    ]

    report = {
        "schemaVersion": "1",
        "label": "m26-polish-execution-live",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "baselineReport": args.baseline_report,
            "stepMap": args.step_map,
            "programPlanDoc": args.program_plan_doc,
            "submissionDoc": args.submission_doc,
            "coverageDoc": args.coverage_doc,
            "usageDoc": args.usage_doc,
            "makefile": args.makefile,
            "gitignore": args.gitignore,
        },
        "metrics": {
            "activeMilestone": active_milestone,
            "docGapBefore": doc_gap_before,
            "docGapAfter": doc_gap_after,
            "docsMissingM26Before": docs_missing_before,
            "docsMissingM26After": docs_missing_m26_after,
            "pycacheDirCountBefore": pycache_before,
            "pycacheDirCountAfter": pycache_after,
            "baselineBacklogCount": len(backlog),
            "baselineBacklogLinkedToPRG262": len(linked_262),
            "baselineBacklogLinkedToPRG263": len(linked_263),
            "openM26QueueCount": len(open_m26_rows),
        },
        "docChecks": doc_checks,
        "checks": checks,
        "ok": True,
    }

    out_path = Path(args.report_out)
    write_json(out_path, report)

    for row in checks:
        print(f"PASS {row['id']}: {row['detail']}")
    print(f"Created: {out_path}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

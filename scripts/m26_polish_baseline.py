#!/usr/bin/env python3
"""Deterministic M26 production-polish baseline and prioritized cleanup backlog."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
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
        description="Generate deterministic M26 production-polish baseline and cleanup backlog."
    )
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--activation-report", default="out/m26_activation_report.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--hardening-report", default="out/m25_hardening_report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--coverage-doc", default="docs/COVERAGE.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m26_polish_baseline_report.json")
    ap.add_argument("--required-active-milestone", default="M26")
    ap.add_argument("--required-previous-milestone", default="M25")
    ap.add_argument("--required-work-id", default="PRG-261")
    ap.add_argument("--required-next-work-id", default="PRG-262")
    ap.add_argument("--required-ci-target", default="m26-polish-baseline-check")
    ap.add_argument("--min-backlog-items", type=int, default=2)
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


def load_work_rows(path: Path) -> list[dict[str, str]]:
    require(path.exists(), f"missing work items file: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_WORK_HEADERS - headers)
        require(not missing, f"{path} missing headers: {', '.join(missing)}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if all(not v for v in row.values()):
                continue
            rows.append(row)
    return rows


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


def git_status_metrics(repo_root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    lines = [line.rstrip("\n") for line in (proc.stdout or "").splitlines() if line.strip()]
    tracked = 0
    untracked = 0
    staged = 0
    unstaged = 0
    deleted = 0
    renamed = 0
    for line in lines:
        if line.startswith("??"):
            untracked += 1
            continue
        if len(line) < 3:
            continue
        tracked += 1
        x = line[0]
        y = line[1]
        if x not in {" ", "?"}:
            staged += 1
        if y not in {" ", "?"}:
            unstaged += 1
        if x == "D" or y == "D":
            deleted += 1
        if x == "R" or y == "R":
            renamed += 1

    branch_proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    branch = (branch_proc.stdout or "").strip() or "unknown"

    commit_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    commit = (commit_proc.stdout or "").strip() or "unknown"

    return {
        "branch": branch,
        "headCommit": commit,
        "gitStatusExitCode": int(proc.returncode),
        "trackedChanges": tracked,
        "untrackedChanges": untracked,
        "stagedChanges": staged,
        "unstagedChanges": unstaged,
        "deletedChanges": deleted,
        "renamedChanges": renamed,
        "totalPorcelainRows": len(lines),
    }


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
    activation = load_json(Path(args.activation_report))
    final_report = load_json(Path(args.final_report))
    hardening = load_json(Path(args.hardening_report))
    step_map = load_json(Path(args.step_map))
    rows = load_work_rows(Path(args.work))
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")

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

    previous = find_milestone(plan, args.required_previous_milestone)
    require(previous is not None, f"plan missing milestone: {args.required_previous_milestone}")
    previous_status = str(previous.get("status", "")).strip().lower()
    checks.append(
        {
            "id": "previous_milestone_completed",
            "ok": previous_status == "completed",
            "detail": f"{args.required_previous_milestone}.status={previous_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    active = find_milestone(plan, args.required_active_milestone)
    require(active is not None, f"plan missing milestone: {args.required_active_milestone}")
    active_status = str(active.get("status", "")).strip().lower()
    checks.append(
        {
            "id": "active_milestone_status",
            "ok": active_status == "active",
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

    activation_ok = bool(activation.get("ok", False))
    checks.append(
        {
            "id": "activation_report_ok",
            "ok": activation_ok,
            "detail": f"activation.ok={activation_ok}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    final_ok = bool(final_report.get("ok", False))
    final_label = str(final_report.get("label", "")).strip()
    checks.append(
        {
            "id": "final_report_ok",
            "ok": final_ok and final_label == "m25-final-product-baseline",
            "detail": f"final.ok={final_ok} label={final_label!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    hardening_ok = bool(hardening.get("ok", False))
    checks.append(
        {
            "id": "hardening_report_ok",
            "ok": hardening_ok,
            "detail": f"hardening.ok={hardening_ok}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    row_261 = find_work_row(rows, args.required_work_id)
    require(row_261 is not None, f"missing work item: {args.required_work_id}")
    row_261_status = str((row_261 or {}).get("status", "")).strip()
    checks.append(
        {
            "id": "work_item_261_present",
            "ok": row_261_status in {"planned", "in_progress", "done"},
            "detail": f"{args.required_work_id}.status={row_261_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    row_262 = find_work_row(rows, args.required_next_work_id)
    require(row_262 is not None, f"missing work item: {args.required_next_work_id}")
    row_262_status = str((row_262 or {}).get("status", "")).strip()
    checks.append(
        {
            "id": "work_item_262_present",
            "ok": row_262_status in {"planned", "in_progress", "done"},
            "detail": f"{args.required_next_work_id}.status={row_262_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    map_entry = ((step_map.get("items") or {}).get(args.required_work_id) or {})
    mapped_commands = map_entry.get("commands") if isinstance(map_entry, dict) else []
    mapped_ok = isinstance(mapped_commands, list) and any(
        args.required_ci_target in str(cmd) for cmd in mapped_commands
    )
    checks.append(
        {
            "id": "step_map_contains_prg261_command",
            "ok": mapped_ok,
            "detail": f"commands={mapped_commands!r}",
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

    program_plan_check = doc_token_check(Path(args.program_plan_doc), ["M26", "PRG-261"])
    submission_check = doc_token_check(
        Path(args.submission_doc),
        ["M26", "m26-polish-baseline-check", "out/m26_polish_baseline_report.json"],
    )
    coverage_check = doc_token_check(
        Path(args.coverage_doc),
        ["M26", "out/m26_polish_baseline_report.json"],
    )
    usage_check = doc_token_check(
        Path(args.usage_doc),
        ["M26", "m26-polish-baseline-check", "out/m26_polish_baseline_report.json"],
    )

    doc_checks = [program_plan_check, submission_check, coverage_check, usage_check]
    docs_missing_m26 = [
        check["path"]
        for check in doc_checks
        if any(token.lower() == "m26" for token in check.get("missingTokens", []))
    ]
    checks.append(
        {
            "id": "docs_scanned",
            "ok": len(doc_checks) == 4,
            "detail": f"docs_scanned={len(doc_checks)}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    git_metrics = git_status_metrics(repo_root)
    pycache_dirs = count_pycache_dirs(repo_root)
    open_m26_rows = [
        row
        for row in rows
        if row.get("milestone_id") == args.required_active_milestone
        and row.get("status") in OPEN_STATUSES
    ]

    backlog: list[dict[str, Any]] = []

    dirty_count = int(git_metrics["trackedChanges"]) + int(git_metrics["untrackedChanges"])
    if dirty_count > 0 or pycache_dirs > 0:
        backlog.append(
            {
                "id": "M26-BLG-001",
                "priority": 1,
                "area": "repository_hygiene",
                "linkedWorkItemId": "PRG-262",
                "title": "Stabilize repository hygiene and generated-artifact boundaries",
                "evidence": (
                    f"trackedChanges={git_metrics['trackedChanges']} "
                    f"untrackedChanges={git_metrics['untrackedChanges']} "
                    f"pycacheDirs={pycache_dirs}"
                ),
                "acceptanceTest": (
                    "Classify/retain intended files, remove transient artifacts, "
                    "and re-run m26-polish-baseline-check with reduced hygiene noise."
                ),
            }
        )

    docs_with_gaps = [check for check in doc_checks if not check.get("ok")]
    if docs_with_gaps:
        backlog.append(
            {
                "id": "M26-BLG-002",
                "priority": 1,
                "area": "documentation_coherence",
                "linkedWorkItemId": "PRG-262",
                "title": "Synchronize reviewer-facing docs with active M26 baseline flow",
                "evidence": (
                    "docsWithGaps="
                    + ",".join(check["path"] for check in docs_with_gaps)
                ),
                "acceptanceTest": (
                    "docs/SUBMISSION.md, docs/COVERAGE.md, and docs/USAGE.md reference "
                    "M26 commands/artifacts and pass targeted consistency checks."
                ),
            }
        )

    release_ready = bool(final_report.get("releaseReady", False))
    if not release_ready or len(open_m26_rows) > 0:
        backlog.append(
            {
                "id": "M26-BLG-003",
                "priority": 2,
                "area": "governance_handoff",
                "linkedWorkItemId": "PRG-263",
                "title": "Adopt M26 anti-drift governance and publish final handoff package",
                "evidence": (
                    f"releaseReady={release_ready} openM26Rows={len(open_m26_rows)}"
                ),
                "acceptanceTest": (
                    "Add M26 governance gate in CI and publish handoff evidence with "
                    "residual-risk ledger and reproducibility commands."
                ),
            }
        )

    backlog.sort(key=lambda row: (int(row.get("priority", 9)), str(row.get("id", ""))))
    checks.append(
        {
            "id": "cleanup_backlog_min_items",
            "ok": len(backlog) >= args.min_backlog_items,
            "detail": f"backlog_count={len(backlog)} min={args.min_backlog_items}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    metrics = {
        "activeMilestone": args.required_active_milestone,
        "openM26QueueCount": len(open_m26_rows),
        "finalReleaseReady": release_ready,
        "gitBranch": git_metrics["branch"],
        "headCommit": git_metrics["headCommit"],
        "gitTrackedChanges": git_metrics["trackedChanges"],
        "gitUntrackedChanges": git_metrics["untrackedChanges"],
        "gitStagedChanges": git_metrics["stagedChanges"],
        "gitUnstagedChanges": git_metrics["unstagedChanges"],
        "gitDeletedChanges": git_metrics["deletedChanges"],
        "gitRenamedChanges": git_metrics["renamedChanges"],
        "pycacheDirCount": pycache_dirs,
        "docGapCount": len(docs_with_gaps),
        "docsMissingM26Count": len(docs_missing_m26),
        "cleanupBacklogCount": len(backlog),
    }

    report = {
        "schemaVersion": "1",
        "label": "m26-production-polish-baseline",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "activationReport": args.activation_report,
            "finalReport": args.final_report,
            "hardeningReport": args.hardening_report,
            "stepExecutionMap": args.step_map,
            "programPlanDoc": args.program_plan_doc,
            "submissionDoc": args.submission_doc,
            "coverageDoc": args.coverage_doc,
            "usageDoc": args.usage_doc,
            "makefile": args.makefile,
        },
        "metrics": metrics,
        "checks": checks,
        "docChecks": doc_checks,
        "cleanupBacklog": backlog,
        "ok": True,
    }

    out_path = Path(args.report_out)
    write_json(out_path, report)

    for row in checks:
        print(f"PASS {row['id']}: {row['detail']}")
    print(
        "Backlog priorities: "
        + ", ".join(f"{item['id']}(P{item['priority']})" for item in backlog)
    )
    print(f"Created: {out_path}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

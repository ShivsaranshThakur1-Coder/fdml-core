#!/usr/bin/env python3
"""Deterministic M26 governance gate and polished handoff package generator."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
    ap = argparse.ArgumentParser(description="Validate M26 governance state and publish handoff package.")
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--baseline-report", default="out/m26_polish_baseline_report.json")
    ap.add_argument("--execution-report", default="out/m26_polish_execution_report.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--coverage-doc", default="docs/COVERAGE.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m26_handoff_governance_report.json")
    ap.add_argument("--required-active-milestone", default="M26")
    ap.add_argument("--required-previous-work-id", default="PRG-262")
    ap.add_argument("--required-work-id", default="PRG-263")
    ap.add_argument("--required-baseline-label", default="m26-production-polish-baseline")
    ap.add_argument("--required-execution-label", default="m26-polish-execution-live")
    ap.add_argument("--required-final-label", default="m25-final-product-baseline")
    ap.add_argument("--required-ci-target", default="m26-governance-handoff-check")
    ap.add_argument("--min-decision-count", type=int, default=5)
    ap.add_argument("--min-assumption-count", type=int, default=5)
    ap.add_argument("--min-risk-count", type=int, default=5)
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
    require(path.exists(), f"missing work item file: {path}")
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def artifact_manifest(repo_root: Path, rel_paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rel in sorted(set(rel_paths)):
        p = repo_root / rel
        require(p.exists(), f"missing handoff artifact: {rel}")
        records.append(
            {
                "path": rel,
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
        )
    return records


def build_decision_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "M26-DEC-001",
            "decision": "Make M26 governance target a mandatory CI gate",
            "chosenOption": "Wire m26-governance-handoff-check into ci to prevent post-polish drift",
            "alternativesConsidered": ["manual reviewer checklist", "local-only command outside ci"],
            "tradeoffs": ["pro: continuous anti-drift enforcement", "con: tighter coupling to handoff docs/artifacts"],
            "reversalCondition": "if handoff checks move to a dedicated release workflow",
        },
        {
            "id": "M26-DEC-002",
            "decision": "Publish machine-readable handoff package with artifact hashes",
            "chosenOption": "Generate deterministic report with command set and SHA256 artifact manifest",
            "alternativesConsidered": ["narrative-only handoff section in docs", "artifact list without hashes"],
            "tradeoffs": ["pro: auditable reproducibility bundle", "con: requires artifact path stability"],
            "reversalCondition": "if artifact attestation is delegated to an external release system",
        },
        {
            "id": "M26-DEC-003",
            "decision": "Track residual risks explicitly even after gate success",
            "chosenOption": "Embed residual-risk ledger in M26 governance report",
            "alternativesConsidered": ["close all risks when gates pass", "keep risks only in prose docs"],
            "tradeoffs": ["pro: clearer boundary between solved and remaining risks", "con: adds maintenance overhead"],
            "reversalCondition": "if risk tracking is fully centralized elsewhere",
        },
        {
            "id": "M26-DEC-004",
            "decision": "Keep one-active-milestone guardrail through handoff completion",
            "chosenOption": "Validate active M26 milestone while requiring queue closure consistency",
            "alternativesConsidered": ["allow zero active milestones", "force immediate milestone completion toggle"],
            "tradeoffs": ["pro: no structural tracker changes", "con: completion semantics rely on queue state"],
            "reversalCondition": "if plan constraints are changed to allow no active milestone",
        },
        {
            "id": "M26-DEC-005",
            "decision": "Use execution map as canonical replay path for PRG-263",
            "chosenOption": "Require PRG-263 command mapping in step_execution_map.json",
            "alternativesConsidered": ["manual execution from docs", "implicit command inference"],
            "tradeoffs": ["pro: deterministic autopilot behavior", "con: mapping must stay synchronized"],
            "reversalCondition": "if autopilot mechanism is replaced by another orchestrator",
        },
    ]


def build_assumption_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "M26-ASM-001",
            "assumption": "M26 is the active handoff milestone while governance checks run",
            "confidence": 0.92,
            "verificationPlan": "assert plan.activeMilestone and goal_state activeMilestoneId both equal M26",
            "invalidationSignal": "active milestone changes before handoff queue closes",
        },
        {
            "id": "M26-ASM-002",
            "assumption": "M26 baseline and execution reports remain the required preconditions for handoff",
            "confidence": 0.9,
            "verificationPlan": "require baseline/execution report labels and ok=true in gate",
            "invalidationSignal": "upstream M26 report labels or schema contracts change",
        },
        {
            "id": "M26-ASM-003",
            "assumption": "Reviewer-facing handoff references live in PROGRAM_PLAN/SUBMISSION/COVERAGE/USAGE",
            "confidence": 0.88,
            "verificationPlan": "enforce token checks for command/artifact synchronization across four docs",
            "invalidationSignal": "official handoff docs move to a different file set",
        },
        {
            "id": "M26-ASM-004",
            "assumption": "Queue closure for M26 can be inferred from PRG-263 status plus open-row shape",
            "confidence": 0.86,
            "verificationPlan": "allow only two valid shapes: PRG-263 open alone (pre-close) or no open rows (post-close)",
            "invalidationSignal": "additional M26 planned/in_progress/blocked rows are introduced",
        },
        {
            "id": "M26-ASM-005",
            "assumption": "Final rehearsal report remains the canonical release-readiness signal",
            "confidence": 0.85,
            "verificationPlan": "require out/final_rehearsal/report.json label and consistency with PRG-263 state",
            "invalidationSignal": "release-readiness source of truth moves away from final_rehearsal report",
        },
    ]


def build_residual_risk_ledger(
    *,
    final_release_ready: bool,
    final_queued_gap_count: int,
    prg263_status: str,
    open_m26_count: int,
) -> list[dict[str, Any]]:
    queue_open = open_m26_count > 0 or prg263_status in {"planned", "in_progress"}
    return [
        {
            "id": "M26-RSK-001",
            "risk": "Documentation may drift from executable handoff command path over time",
            "severity": "medium",
            "likelihood": "medium",
            "status": "active",
            "mitigation": "Keep M26 governance check in CI with doc token assertions",
        },
        {
            "id": "M26-RSK-002",
            "risk": "Artifact bundle can become stale after additional tracker or doc edits",
            "severity": "medium",
            "likelihood": "medium",
            "status": "active",
            "mitigation": "Regenerate m26-governance-handoff-check before external handoff",
        },
        {
            "id": "M26-RSK-003",
            "risk": "Queue state and release-readiness can diverge if final rehearsal is not refreshed",
            "severity": "high",
            "likelihood": "low",
            "status": "active",
            "mitigation": "Target reruns final_rehearsal_check.py before governance assertions",
        },
        {
            "id": "M26-RSK-004",
            "risk": "Project remains scoped to internal corpus and validators, not full-world dance exhaustiveness",
            "severity": "medium",
            "likelihood": "high",
            "status": "active",
            "mitigation": "Treat this as explicit product limitation in docs/COVERAGE.md",
        },
        {
            "id": "M26-RSK-005",
            "risk": "Release readiness may remain false while PRG-263 or other queue work is open",
            "severity": "high",
            "likelihood": "medium" if queue_open else "low",
            "status": "active" if (queue_open or not final_release_ready or final_queued_gap_count > 0) else "monitoring",
            "mitigation": "Close active queue, rerun final rehearsal, and confirm queuedGapCount=0",
        },
    ]


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()

    plan = load_json(Path(args.plan))
    goal_state = load_json(Path(args.goal_state))
    baseline = load_json(Path(args.baseline_report))
    execution = load_json(Path(args.execution_report))
    final_report = load_json(Path(args.final_report))
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

    baseline_ok = bool(baseline.get("ok", False))
    baseline_label = str(baseline.get("label", "")).strip()
    checks.append(
        {
            "id": "baseline_report_ok",
            "ok": baseline_ok and baseline_label == args.required_baseline_label,
            "detail": f"baseline.ok={baseline_ok} baseline.label={baseline_label!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    execution_ok = bool(execution.get("ok", False))
    execution_label = str(execution.get("label", "")).strip()
    checks.append(
        {
            "id": "execution_report_ok",
            "ok": execution_ok and execution_label == args.required_execution_label,
            "detail": f"execution.ok={execution_ok} execution.label={execution_label!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    final_ok = bool(final_report.get("ok", False))
    final_label = str(final_report.get("label", "")).strip()
    final_release_ready = bool(final_report.get("releaseReady", False))
    final_queued_gap_count = int((final_report.get("summary") or {}).get("queuedGapCount", -1))
    checks.append(
        {
            "id": "final_report_ok",
            "ok": final_ok and final_label == args.required_final_label,
            "detail": f"final.ok={final_ok} final.label={final_label!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    previous_row = find_work_row(rows, args.required_previous_work_id)
    require(previous_row is not None, f"missing work item: {args.required_previous_work_id}")
    previous_status = str((previous_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "prg262_done",
            "ok": previous_status == "done",
            "detail": f"{args.required_previous_work_id}.status={previous_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    current_row = find_work_row(rows, args.required_work_id)
    require(current_row is not None, f"missing work item: {args.required_work_id}")
    current_status = str((current_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "prg263_status_allowed",
            "ok": current_status in {"planned", "in_progress", "done"},
            "detail": f"{args.required_work_id}.status={current_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    m26_rows = [row for row in rows if row.get("milestone_id", "") == args.required_active_milestone]
    open_m26_rows = [row for row in m26_rows if row.get("status", "").strip().lower() in OPEN_STATUSES]
    open_non263_rows = [row for row in open_m26_rows if row.get("id") != args.required_work_id]

    queue_shape_ok = False
    if current_status in {"planned", "in_progress"}:
        queue_shape_ok = (
            len(open_m26_rows) == 1
            and str(open_m26_rows[0].get("id", "")).strip() == args.required_work_id
        )
    elif current_status == "done":
        queue_shape_ok = len(open_m26_rows) == 0

    checks.append(
        {
            "id": "m26_open_queue_shape",
            "ok": queue_shape_ok and len(open_non263_rows) == 0,
            "detail": (
                f"openM26={len(open_m26_rows)} "
                f"openNonPRG263={len(open_non263_rows)} "
                f"prg263Status={current_status!r}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    goal_execution_state = goal_state.get("executionState") or {}
    goal_active_queue = (
        goal_execution_state.get("activeQueue")
        if isinstance(goal_execution_state.get("activeQueue"), list)
        else []
    )
    goal_active_queue_count = len(goal_active_queue)
    goal_queue_shape_ok = False
    if current_status in {"planned", "in_progress"}:
        ids = {str(row.get("id", "")).strip() for row in goal_active_queue if isinstance(row, dict)}
        goal_queue_shape_ok = goal_active_queue_count >= 1 and args.required_work_id in ids
    elif current_status == "done":
        goal_queue_shape_ok = goal_active_queue_count == 0

    checks.append(
        {
            "id": "goal_state_queue_shape",
            "ok": goal_queue_shape_ok,
            "detail": f"goalState.activeQueueCount={goal_active_queue_count} prg263Status={current_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    final_consistency_ok = False
    if current_status in {"planned", "in_progress"}:
        final_consistency_ok = (not final_release_ready) and final_queued_gap_count >= 1
    elif current_status == "done":
        final_consistency_ok = final_release_ready and final_queued_gap_count == 0

    checks.append(
        {
            "id": "final_report_consistent_with_prg263_state",
            "ok": final_consistency_ok,
            "detail": (
                f"releaseReady={final_release_ready} "
                f"queuedGapCount={final_queued_gap_count} "
                f"prg263Status={current_status!r}"
            ),
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
            "id": "step_map_contains_prg263_command",
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

    program_plan_check = doc_token_check(
        Path(args.program_plan_doc),
        [
            "M26",
            "PRG-263",
            "m26-governance-handoff-check",
            "out/m26_handoff_governance_report.json",
            "residual-risk",
        ],
    )
    submission_check = doc_token_check(
        Path(args.submission_doc),
        [
            "m26-governance-handoff-check",
            "out/m26_handoff_governance_report.json",
            "residual-risk ledger",
        ],
    )
    coverage_check = doc_token_check(
        Path(args.coverage_doc),
        [
            "M26 governance handoff",
            "out/m26_handoff_governance_report.json",
        ],
    )
    usage_check = doc_token_check(
        Path(args.usage_doc),
        [
            "make m26-governance-handoff-check",
            "out/m26_handoff_governance_report.json",
        ],
    )
    doc_checks = [program_plan_check, submission_check, coverage_check, usage_check]
    doc_gap_count = sum(1 for check in doc_checks if not bool(check.get("ok", False)))
    checks.append(
        {
            "id": "docs_synchronized_for_m26_handoff",
            "ok": doc_gap_count == 0,
            "detail": f"docGapCount={doc_gap_count}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    decision_registry = build_decision_registry()
    assumption_registry = build_assumption_registry()
    residual_risk_ledger = build_residual_risk_ledger(
        final_release_ready=final_release_ready,
        final_queued_gap_count=final_queued_gap_count,
        prg263_status=current_status,
        open_m26_count=len(open_m26_rows),
    )
    checks.append(
        {
            "id": "decision_registry_floor",
            "ok": len(decision_registry) >= args.min_decision_count,
            "detail": f"decision_count={len(decision_registry)} min={args.min_decision_count}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])
    checks.append(
        {
            "id": "assumption_registry_floor",
            "ok": len(assumption_registry) >= args.min_assumption_count,
            "detail": f"assumption_count={len(assumption_registry)} min={args.min_assumption_count}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])
    checks.append(
        {
            "id": "residual_risk_floor",
            "ok": len(residual_risk_ledger) >= args.min_risk_count,
            "detail": f"risk_count={len(residual_risk_ledger)} min={args.min_risk_count}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    handoff_commands = [
        "make program-check",
        "make task-approval-check",
        "make goal-state-check",
        "make m26-activation-check",
        "make m26-polish-baseline-check",
        "make m26-polish-execution-check",
        "make m26-governance-handoff-check",
    ]
    handoff_artifact_paths = [
        args.plan,
        args.work,
        args.goal_state,
        args.program_plan_doc,
        args.submission_doc,
        args.coverage_doc,
        args.usage_doc,
        args.baseline_report,
        args.execution_report,
        args.final_report,
        "out/m26_activation_report.json",
        "out/m25_hardening_report.json",
    ]
    handoff_artifacts = artifact_manifest(repo_root, handoff_artifact_paths)

    failed = [row for row in checks if not bool(row.get("ok", False))]
    report = {
        "schemaVersion": "1",
        "label": "m26-handoff-governance-live",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "baselineReport": args.baseline_report,
            "executionReport": args.execution_report,
            "finalReport": args.final_report,
            "stepMap": args.step_map,
            "programPlanDoc": args.program_plan_doc,
            "submissionDoc": args.submission_doc,
            "coverageDoc": args.coverage_doc,
            "usageDoc": args.usage_doc,
            "makefile": args.makefile,
        },
        "metrics": {
            "activeMilestone": active_milestone,
            "prg262Status": previous_status,
            "prg263Status": current_status,
            "openM26QueueCount": len(open_m26_rows),
            "openM26NonPRG263Count": len(open_non263_rows),
            "goalStateActiveQueueCount": goal_active_queue_count,
            "finalReleaseReady": final_release_ready,
            "finalQueuedGapCount": final_queued_gap_count,
            "docGapCount": doc_gap_count,
            "handoffArtifactCount": len(handoff_artifacts),
        },
        "handoffPackage": {
            "commands": handoff_commands,
            "artifacts": handoff_artifacts,
            "residualRiskLedger": residual_risk_ledger,
        },
        "decisionRegistry": decision_registry,
        "assumptionRegistry": assumption_registry,
        "docChecks": doc_checks,
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

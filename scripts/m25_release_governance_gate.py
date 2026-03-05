#!/usr/bin/env python3
"""Final M25 release-governance gate for queue closeout and anti-drift enforcement."""

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
    ap = argparse.ArgumentParser(description="Validate M25 release governance and closeout invariants.")
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--hardening-report", default="out/m25_hardening_report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m25_release_governance.json")
    ap.add_argument("--required-active-milestone", default="M25")
    ap.add_argument("--required-final-label", default="m25-final-product-baseline")
    ap.add_argument("--required-prg-id", default="PRG-253")
    ap.add_argument("--required-ci-target", default="m25-release-governance-check")
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


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


def has_all(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return all(p.lower() in lower for p in patterns)


def build_decision_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "M25-DEC-001",
            "decision": "Define release readiness by queue closure and gate integrity",
            "chosenOption": "releaseReady requires zero queued gaps and all release gates passing",
            "alternativesConsidered": [
                "mark release readiness by date only",
                "require milestone status=completed despite one-active-milestone guardrail",
            ],
            "tradeoffs": [
                "pro: deterministic and auditable readiness semantics",
                "con: requires explicit queue hygiene before every release check",
            ],
            "reversalCondition": "if guardrail model changes to allow zero active milestones",
        },
        {
            "id": "M25-DEC-002",
            "decision": "Keep M25 as active while queue is empty",
            "chosenOption": "retain one-active-milestone invariant and close queue to declare release readiness",
            "alternativesConsidered": [
                "add a synthetic post-closeout milestone",
                "relax program gate to allow zero active milestones",
            ],
            "tradeoffs": [
                "pro: avoids structural tracker rewrite at closeout",
                "con: milestone status text remains active even when release is ready",
            ],
            "reversalCondition": "if next-cycle milestones are introduced",
        },
        {
            "id": "M25-DEC-003",
            "decision": "Enforce closeout governance directly in CI",
            "chosenOption": "wire m25-release-governance-check into ci target",
            "alternativesConsidered": [
                "manual closeout checklist",
                "release governance check outside ci",
            ],
            "tradeoffs": [
                "pro: anti-drift guarantees stay continuously enforced",
                "con: future queue changes require deliberate governance updates",
            ],
            "reversalCondition": "if ci runtime budget requires separation of release gates",
        },
        {
            "id": "M25-DEC-004",
            "decision": "Keep final baseline as canonical release source of truth",
            "chosenOption": "require final report label/schema and releaseReady=true in governance gate",
            "alternativesConsidered": [
                "derive release state directly from work_items only",
                "accept hardening report alone as release signal",
            ],
            "tradeoffs": [
                "pro: one auditable artifact consolidates architecture quality and queue state",
                "con: release gate depends on baseline regeneration sequence",
            ],
            "reversalCondition": "if a dedicated release manifest supersedes final rehearsal report",
        },
        {
            "id": "M25-DEC-005",
            "decision": "Record deterministic execution path for PRG-253",
            "chosenOption": "store command mapping in step_execution_map and assert it in governance checks",
            "alternativesConsidered": [
                "leave PRG-253 as manual operation",
                "store mapping only in docs",
            ],
            "tradeoffs": [
                "pro: autopilot and future agents can reproduce closeout command path",
                "con: mapping must stay synchronized with Makefile target evolution",
            ],
            "reversalCondition": "if execution-map mechanism is replaced with another orchestrator",
        },
    ]


def build_assumption_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "M25-ASM-001",
            "assumption": "No further active milestone work items are required for initial release handoff",
            "confidence": 0.85,
            "verificationPlan": "enforce activeQueueCount=0 and openM25WorkItems=0",
            "invalidationSignal": "new planned/in_progress/blocked M25 row appears",
        },
        {
            "id": "M25-ASM-002",
            "assumption": "Current corpus scale and validator floor are sufficient for this closeout release",
            "confidence": 0.8,
            "verificationPlan": "read final baseline processed-file and rule-count metrics",
            "invalidationSignal": "final baseline drops below required thresholds",
        },
        {
            "id": "M25-ASM-003",
            "assumption": "Program and submission docs are the primary reviewer-facing references",
            "confidence": 0.9,
            "verificationPlan": "require release-governance command and artifact references in both docs",
            "invalidationSignal": "official handoff process moves to different document set",
        },
        {
            "id": "M25-ASM-004",
            "assumption": "Hardening gate remains mandatory precondition for final governance",
            "confidence": 0.88,
            "verificationPlan": "require hardening report ok=true and zero failed checks",
            "invalidationSignal": "hardening gate is replaced or removed from CI",
        },
        {
            "id": "M25-ASM-005",
            "assumption": "Execution map remains an approved source for deterministic step commands",
            "confidence": 0.82,
            "verificationPlan": "assert PRG-253 command entry exists and points to release-governance target",
            "invalidationSignal": "step_execution_map schema or ownership changes",
        },
    ]


def build_risk_ledger() -> list[dict[str, Any]]:
    return [
        {
            "id": "M25-RSK-001",
            "risk": "Queue drift after closeout reintroduces hidden scope",
            "severity": "high",
            "likelihood": "medium",
            "mitigation": "CI blocks when release governance sees non-empty active queue or gaps",
        },
        {
            "id": "M25-RSK-002",
            "risk": "Release docs diverge from executable gate path",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "governance check asserts command/artifact references in docs",
        },
        {
            "id": "M25-RSK-003",
            "risk": "Final baseline report becomes stale after tracker edits",
            "severity": "high",
            "likelihood": "medium",
            "mitigation": "governance target regenerates baseline and hardening reports before checks",
        },
        {
            "id": "M25-RSK-004",
            "risk": "Manual status changes bypass deterministic execution map",
            "severity": "medium",
            "likelihood": "low",
            "mitigation": "step map command entry is required and validated",
        },
        {
            "id": "M25-RSK-005",
            "risk": "Future milestone expansion could invalidate closeout assumptions",
            "severity": "medium",
            "likelihood": "medium",
            "mitigation": "decision registry includes explicit reversal conditions",
        },
    ]


def main() -> int:
    args = parse_args()

    plan = load_json(Path(args.plan))
    goal_state = load_json(Path(args.goal_state))
    final_report = load_json(Path(args.final_report))
    hardening = load_json(Path(args.hardening_report))
    step_map = load_json(Path(args.step_map))
    rows = load_work_rows(Path(args.work))

    program_plan_text = Path(args.program_plan_doc).read_text(encoding="utf-8")
    submission_text = Path(args.submission_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")

    checks: list[dict[str, Any]] = []

    active_milestone = str(plan.get("activeMilestone", "")).strip()
    checks.append(
        {
            "id": "plan_active_m25",
            "ok": active_milestone == args.required_active_milestone,
            "detail": f"activeMilestone={active_milestone!r}",
        }
    )

    milestone_rows = plan.get("milestones") if isinstance(plan.get("milestones"), list) else []
    m25 = None
    for row in milestone_rows:
        if isinstance(row, dict) and str(row.get("id", "")).strip() == args.required_active_milestone:
            m25 = row
            break
    m25_status = str((m25 or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "plan_m25_status_active",
            "ok": m25_status == "active",
            "detail": f"m25.status={m25_status!r}",
        }
    )

    m25_rows = [r for r in rows if r.get("milestone_id", "") == args.required_active_milestone]
    open_m25_rows = [r for r in m25_rows if r.get("status", "") in {"planned", "in_progress", "blocked"}]
    done_m25_rows = [r for r in m25_rows if r.get("status", "") == "done"]
    checks.append(
        {
            "id": "work_items_m25_queue_closed",
            "ok": len(open_m25_rows) == 0,
            "detail": f"open_m25_work_items={len(open_m25_rows)}",
        }
    )
    checks.append(
        {
            "id": "work_items_m25_done_floor",
            "ok": len(done_m25_rows) >= 3,
            "detail": f"done_m25_work_items={len(done_m25_rows)}",
        }
    )

    prg253_rows = [r for r in rows if r.get("id", "") == args.required_prg_id]
    prg253_status = prg253_rows[0].get("status", "") if prg253_rows else ""
    checks.append(
        {
            "id": "prg253_done",
            "ok": len(prg253_rows) == 1 and prg253_status == "done",
            "detail": f"found={len(prg253_rows)} status={prg253_status!r}",
        }
    )

    project_context = goal_state.get("projectContext") or {}
    execution_state = goal_state.get("executionState") or {}
    goal_active = str(project_context.get("activeMilestoneId", "")).strip()
    active_queue = execution_state.get("activeQueue") if isinstance(execution_state.get("activeQueue"), list) else []
    checks.append(
        {
            "id": "goal_state_active_m25",
            "ok": goal_active == args.required_active_milestone,
            "detail": f"goal_state.activeMilestoneId={goal_active!r}",
        }
    )
    checks.append(
        {
            "id": "goal_state_active_queue_closed",
            "ok": len(active_queue) == 0,
            "detail": f"goal_state.activeQueueCount={len(active_queue)}",
        }
    )

    final_label = str(final_report.get("label", "")).strip()
    final_schema = str(final_report.get("schemaVersion", "")).strip()
    release_ready = bool(final_report.get("releaseReady", False))
    gaps = final_report.get("gaps")
    gap_count = len(gaps) if isinstance(gaps, list) else -1
    queued_gap_count = int((final_report.get("summary") or {}).get("queuedGapCount", -1))
    checks.append(
        {
            "id": "final_report_label",
            "ok": final_label == args.required_final_label,
            "detail": f"label={final_label!r}",
        }
    )
    checks.append(
        {
            "id": "final_report_schema_v2",
            "ok": final_schema == "2",
            "detail": f"schemaVersion={final_schema!r}",
        }
    )
    checks.append(
        {
            "id": "final_report_release_ready",
            "ok": release_ready,
            "detail": f"releaseReady={release_ready}",
        }
    )
    checks.append(
        {
            "id": "final_report_gap_free",
            "ok": isinstance(gaps, list) and gap_count == 0 and queued_gap_count == 0,
            "detail": f"gapCount={gap_count} queuedGapCount={queued_gap_count}",
        }
    )

    hardening_ok = bool(hardening.get("ok", False))
    hardening_checks = hardening.get("checks")
    failed_hardening = [
        row for row in (hardening_checks if isinstance(hardening_checks, list) else [])
        if isinstance(row, dict) and not bool(row.get("ok", False))
    ]
    checks.append(
        {
            "id": "hardening_passes",
            "ok": hardening_ok and len(failed_hardening) == 0,
            "detail": f"hardening_ok={hardening_ok} failed_checks={len(failed_hardening)}",
        }
    )

    map_item = (step_map.get("items") or {}).get(args.required_prg_id, {})
    map_commands = map_item.get("commands") if isinstance(map_item, dict) else []
    map_ok = (
        isinstance(map_commands, list)
        and len(map_commands) == 1
        and str(map_commands[0]).strip() == f"make {args.required_ci_target}"
    )
    checks.append(
        {
            "id": "step_map_prg253",
            "ok": map_ok,
            "detail": f"commands={map_commands!r}",
        }
    )

    checks.append(
        {
            "id": "make_target_exists",
            "ok": f"{args.required_ci_target}:" in makefile_text,
            "detail": f"target={args.required_ci_target}",
        }
    )
    checks.append(
        {
            "id": "make_ci_wires_release_governance",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"ci_contains={args.required_ci_target}",
        }
    )

    checks.append(
        {
            "id": "program_plan_mentions_release_governance",
            "ok": has_all(
                program_plan_text,
                [
                    args.required_prg_id,
                    "completed",
                    args.required_ci_target,
                    "out/m25_release_governance.json",
                ],
            ),
            "detail": "program plan synchronized with PRG-253 closeout",
        }
    )
    checks.append(
        {
            "id": "submission_mentions_release_governance",
            "ok": has_all(
                submission_text,
                [
                    args.required_ci_target,
                    "out/m25_release_governance.json",
                    "releaseReady=true",
                ],
            ),
            "detail": "submission doc synchronized with release closeout command/artifact",
        }
    )

    decision_registry = build_decision_registry()
    assumption_registry = build_assumption_registry()
    risk_ledger = build_risk_ledger()
    checks.append(
        {
            "id": "decision_registry_floor",
            "ok": len(decision_registry) >= args.min_decision_count,
            "detail": f"decision_count={len(decision_registry)} min={args.min_decision_count}",
        }
    )
    checks.append(
        {
            "id": "assumption_registry_floor",
            "ok": len(assumption_registry) >= args.min_assumption_count,
            "detail": f"assumption_count={len(assumption_registry)} min={args.min_assumption_count}",
        }
    )
    checks.append(
        {
            "id": "risk_ledger_floor",
            "ok": len(risk_ledger) >= args.min_risk_count,
            "detail": f"risk_count={len(risk_ledger)} min={args.min_risk_count}",
        }
    )

    failed = [row for row in checks if not bool(row.get("ok"))]
    report = {
        "schemaVersion": "1",
        "label": "m25-release-governance-live",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "finalReport": args.final_report,
            "hardeningReport": args.hardening_report,
            "stepMap": args.step_map,
            "programPlanDoc": args.program_plan_doc,
            "submissionDoc": args.submission_doc,
            "makefile": args.makefile,
        },
        "metrics": {
            "activeMilestone": active_milestone,
            "m25Status": m25_status,
            "m25WorkItemTotal": len(m25_rows),
            "m25DoneWorkItems": len(done_m25_rows),
            "m25OpenWorkItems": len(open_m25_rows),
            "goalStateActiveQueueCount": len(active_queue),
            "releaseReady": release_ready,
            "gapCount": gap_count,
            "queuedGapCount": queued_gap_count,
        },
        "decisionRegistry": decision_registry,
        "assumptionRegistry": assumption_registry,
        "riskLedger": risk_ledger,
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

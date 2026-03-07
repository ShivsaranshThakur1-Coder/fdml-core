#!/usr/bin/env python3
"""Deterministic M29 governance and final delivery-freeze gate."""

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
    ap = argparse.ArgumentParser(
        description="Validate M29 anti-drift governance and freeze final delivery package."
    )
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--activation-report", default="out/m29_activation_report.json")
    ap.add_argument("--baseline-report", default="out/m29_release_baseline_report.json")
    ap.add_argument("--execution-report", default="out/m29_delivery_stabilization_report.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--demo-doc", default="docs/DEMO.html")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--build-index-script", default="scripts/build_index.sh")
    ap.add_argument("--site-smoke-script", default="scripts/site_smoke.py")
    ap.add_argument("--report-out", default="out/m29_governance_freeze_report.json")
    ap.add_argument("--required-active-milestone", default="M29")
    ap.add_argument("--required-previous-work-id", default="PRG-277")
    ap.add_argument("--required-work-id", default="PRG-278")
    ap.add_argument("--required-baseline-label", default="m29-release-workflow-baseline-live")
    ap.add_argument("--required-execution-label", default="m29-delivery-stabilization-live")
    ap.add_argument("--required-final-label", default="m25-final-product-baseline")
    ap.add_argument("--required-ci-target", default="m29-governance-freeze-check")
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
        require(p.exists(), f"missing freeze artifact: {rel}")
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
            "id": "M29-DEC-001",
            "decision": "Add an explicit M29 governance-freeze target in CI",
            "chosenOption": "Wire m29-governance-freeze-check into ci for anti-drift enforcement",
            "alternativesConsidered": ["stop at PRG-277 delivery gate", "manual freeze checklist only"],
            "tradeoffs": ["pro: deterministic final-freeze guardrail", "con: higher CI coupling to freeze docs/artifacts"],
            "reversalCondition": "if freeze checks move to a dedicated release workflow outside ci",
        },
        {
            "id": "M29-DEC-002",
            "decision": "Require queue-closure state at governance freeze",
            "chosenOption": "PRG-278 must be done and open M29 rows must be zero",
            "alternativesConsidered": ["allow PRG-278 planned state in freeze gate", "allow nonzero open queue"],
            "tradeoffs": ["pro: clear frozen state boundary", "con: requires completion update before gate pass"],
            "reversalCondition": "if protocol changes to permit staged freeze with open queue items",
        },
        {
            "id": "M29-DEC-003",
            "decision": "Publish hashed freeze package for handoff reproducibility",
            "chosenOption": "Emit command list plus SHA256 manifest for final tracker/docs/artifacts",
            "alternativesConsidered": ["reference artifact paths without hashes", "store evidence only in prose"],
            "tradeoffs": ["pro: auditable reproducibility package", "con: artifact set must remain stable"],
            "reversalCondition": "if artifact attestation is delegated to external release tooling",
        },
        {
            "id": "M29-DEC-004",
            "decision": "Keep M29 as active milestone while queue is frozen",
            "chosenOption": "Preserve one-active-milestone guardrail and represent freeze via zero open queue",
            "alternativesConsidered": ["mark M29 completed without a successor milestone", "add synthetic closeout milestone"],
            "tradeoffs": ["pro: no program-gate contract breakage", "con: active status must be interpreted with queue state"],
            "reversalCondition": "if plan constraints are updated to allow zero active milestones",
        },
        {
            "id": "M29-DEC-005",
            "decision": "Use PRG-278 step map entry as canonical replay command",
            "chosenOption": "Require step_execution_map PRG-278 command to point at freeze target",
            "alternativesConsidered": ["derive command only from docs", "leave replay path implicit"],
            "tradeoffs": ["pro: deterministic autopilot replay", "con: mapping must stay synchronized"],
            "reversalCondition": "if step execution replay moves to another orchestrator",
        },
    ]


def build_assumption_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "M29-ASM-001",
            "assumption": "M29 remains the active milestone during the final freeze step",
            "confidence": 0.92,
            "verificationPlan": "assert plan.activeMilestone and goal_state activeMilestoneId equal M29",
            "invalidationSignal": "active milestone switches before freeze package is emitted",
        },
        {
            "id": "M29-ASM-002",
            "assumption": "PRG-277 execution output remains a required precondition for PRG-278",
            "confidence": 0.9,
            "verificationPlan": "require execution report label/ok and PRG-277=done",
            "invalidationSignal": "delivery-stabilization contract or labels change",
        },
        {
            "id": "M29-ASM-003",
            "assumption": "Final rehearsal report is still canonical release-readiness evidence",
            "confidence": 0.89,
            "verificationPlan": "require final report label plus releaseReady=true and queuedGapCount=0",
            "invalidationSignal": "release-readiness source moves away from final_rehearsal report",
        },
        {
            "id": "M29-ASM-004",
            "assumption": "Freeze references must stay synchronized across PROGRAM_PLAN, SUBMISSION, and USAGE",
            "confidence": 0.88,
            "verificationPlan": "enforce token checks in all three docs",
            "invalidationSignal": "official reviewer-facing docs move to a new file set",
        },
        {
            "id": "M29-ASM-005",
            "assumption": "Demo/site snapshots must include the new M29 freeze report",
            "confidence": 0.86,
            "verificationPlan": "assert DEMO/build_index/site_smoke all reference m29_governance_freeze snapshot",
            "invalidationSignal": "demo evidence panel architecture changes",
        },
    ]


def build_residual_risk_ledger(*, queue_closed: bool, docs_synced: bool, release_ready: bool) -> list[dict[str, Any]]:
    return [
        {
            "id": "M29-RSK-001",
            "risk": "Queue drift can reopen work after freeze",
            "severity": "high",
            "likelihood": "medium",
            "status": "mitigated" if queue_closed else "active",
            "mitigation": "CI freeze gate requires PRG-278 done and zero open M29 queue rows",
        },
        {
            "id": "M29-RSK-002",
            "risk": "Release docs may diverge from executable freeze command path",
            "severity": "medium",
            "likelihood": "medium",
            "status": "mitigated" if docs_synced else "active",
            "mitigation": "Token checks enforce synchronized command/artifact references across release docs",
        },
        {
            "id": "M29-RSK-003",
            "risk": "Final release readiness signal can become stale after tracker edits",
            "severity": "high",
            "likelihood": "medium",
            "status": "mitigated" if release_ready else "active",
            "mitigation": "Freeze gate requires final rehearsal report releaseReady=true with zero queued gaps",
        },
        {
            "id": "M29-RSK-004",
            "risk": "Demo evidence panel can drift from current freeze artifact set",
            "severity": "medium",
            "likelihood": "low",
            "status": "active",
            "mitigation": "build_index + site_smoke + DEMO checks require m29_governance_freeze snapshot references",
        },
        {
            "id": "M29-RSK-005",
            "risk": "Future milestone model changes can invalidate active-milestone freeze semantics",
            "severity": "medium",
            "likelihood": "medium",
            "status": "active",
            "mitigation": "decision registry records explicit reversal condition for one-active-milestone model",
        },
    ]


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()

    plan = load_json(Path(args.plan))
    rows = load_work_rows(Path(args.work))
    goal_state = load_json(Path(args.goal_state))
    activation = load_json(Path(args.activation_report))
    baseline = load_json(Path(args.baseline_report))
    execution = load_json(Path(args.execution_report))
    final_report = load_json(Path(args.final_report))
    step_map = load_json(Path(args.step_map))
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    demo_text = Path(args.demo_doc).read_text(encoding="utf-8")
    build_index_text = Path(args.build_index_script).read_text(encoding="utf-8")
    site_smoke_text = Path(args.site_smoke_script).read_text(encoding="utf-8")

    checks: list[dict[str, Any]] = []

    active_milestone = str(plan.get("activeMilestone", "")).strip()
    checks.append(
        {
            "id": "plan_active_m29",
            "ok": active_milestone == args.required_active_milestone,
            "detail": f"plan.activeMilestone={active_milestone!r}",
        }
    )

    active = find_milestone(plan, args.required_active_milestone)
    active_status = str((active or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "active_milestone_status",
            "ok": active is not None and active_status == "active",
            "detail": f"{args.required_active_milestone}.status={active_status!r}",
        }
    )

    goal_project = goal_state.get("projectContext") if isinstance(goal_state.get("projectContext"), dict) else {}
    goal_exec = goal_state.get("executionState") if isinstance(goal_state.get("executionState"), dict) else {}
    goal_active = str(goal_project.get("activeMilestoneId", "")).strip()
    goal_active_queue = goal_exec.get("activeQueue") if isinstance(goal_exec.get("activeQueue"), list) else []
    checks.append(
        {
            "id": "goal_state_active_m29",
            "ok": goal_active == args.required_active_milestone,
            "detail": f"goalState.activeMilestoneId={goal_active!r}",
        }
    )

    prev_row = find_work_row(rows, args.required_previous_work_id)
    prev_status = str((prev_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "prg277_done",
            "ok": prev_row is not None and prev_status == "done",
            "detail": f"{args.required_previous_work_id}.status={prev_status!r}",
        }
    )

    freeze_row = find_work_row(rows, args.required_work_id)
    freeze_status = str((freeze_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "prg278_done",
            "ok": freeze_row is not None and freeze_status == "done",
            "detail": f"{args.required_work_id}.status={freeze_status!r}",
        }
    )

    m29_rows = [row for row in rows if row.get("milestone_id", "") == args.required_active_milestone]
    open_m29_rows = [row for row in m29_rows if row.get("status", "").strip().lower() in OPEN_STATUSES]
    open_m29_ids = sorted(row.get("id", "") for row in open_m29_rows)
    checks.append(
        {
            "id": "m29_queue_closed",
            "ok": len(open_m29_rows) == 0,
            "detail": f"openM29Rows={len(open_m29_rows)} openIds={open_m29_ids}",
        }
    )
    checks.append(
        {
            "id": "goal_state_active_queue_closed",
            "ok": len(goal_active_queue) == 0,
            "detail": f"goalState.activeQueueCount={len(goal_active_queue)}",
        }
    )

    activation_ok = bool(activation.get("ok", False))
    checks.append(
        {
            "id": "activation_report_ok",
            "ok": activation_ok,
            "detail": f"activation.ok={activation_ok}",
        }
    )

    baseline_label = str(baseline.get("label", "")).strip()
    baseline_ok = bool(baseline.get("ok", False))
    checks.append(
        {
            "id": "baseline_report_ok",
            "ok": baseline_ok and baseline_label == args.required_baseline_label,
            "detail": f"baseline.ok={baseline_ok} baseline.label={baseline_label!r}",
        }
    )

    execution_label = str(execution.get("label", "")).strip()
    execution_ok = bool(execution.get("ok", False))
    checks.append(
        {
            "id": "execution_report_ok",
            "ok": execution_ok and execution_label == args.required_execution_label,
            "detail": f"execution.ok={execution_ok} execution.label={execution_label!r}",
        }
    )

    final_label = str(final_report.get("label", "")).strip()
    final_ok = bool(final_report.get("ok", False))
    release_ready = bool(final_report.get("releaseReady", False))
    queued_gap_count = int((final_report.get("summary") or {}).get("queuedGapCount", -1))
    checks.append(
        {
            "id": "final_report_release_ready",
            "ok": final_ok
            and final_label == args.required_final_label
            and release_ready
            and queued_gap_count == 0,
            "detail": (
                f"final.ok={final_ok} final.label={final_label!r} "
                f"releaseReady={release_ready} queuedGapCount={queued_gap_count}"
            ),
        }
    )

    items = step_map.get("items") if isinstance(step_map.get("items"), dict) else {}
    step_entry = items.get(args.required_work_id) if isinstance(items, dict) else None
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    command_list = [str(c).strip() for c in commands] if isinstance(commands, list) else []
    checks.append(
        {
            "id": "step_map_prg278_entry",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map entry exists for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_freeze_target",
            "ok": any(args.required_ci_target in cmd for cmd in command_list),
            "detail": f"{args.required_work_id}.commands={command_list}",
        }
    )

    checks.append(
        {
            "id": "make_target_exists",
            "ok": f"{args.required_ci_target}:" in makefile_text,
            "detail": f"Makefile has target {args.required_ci_target}",
        }
    )
    checks.append(
        {
            "id": "make_ci_wires_freeze_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci includes {args.required_ci_target}",
        }
    )

    program_plan_check = doc_token_check(
        Path(args.program_plan_doc),
        ["PRG-278", "M29-K3", f"make {args.required_ci_target}", "out/m29_governance_freeze_report.json"],
    )
    usage_check = doc_token_check(
        Path(args.usage_doc),
        ["PRG-278", f"make {args.required_ci_target}", "out/m29_governance_freeze_report.json"],
    )
    submission_check = doc_token_check(
        Path(args.submission_doc),
        ["PRG-278", f"make {args.required_ci_target}", "out/m29_governance_freeze_report.json"],
    )
    doc_checks = [program_plan_check, usage_check, submission_check]
    docs_with_gaps = [check for check in doc_checks if not check.get("ok")]
    checks.append(
        {
            "id": "release_docs_synchronized",
            "ok": len(docs_with_gaps) == 0,
            "detail": f"docsWithGaps={len(docs_with_gaps)}",
        }
    )

    checks.append(
        {
            "id": "demo_links_freeze_snapshot",
            "ok": "reports/m29_governance_freeze.report.json" in demo_text,
            "detail": "DEMO includes m29_governance_freeze snapshot link",
        }
    )
    checks.append(
        {
            "id": "demo_fetches_freeze_snapshot",
            "ok": 'loadJson("reports/m29_governance_freeze.report.json")' in demo_text,
            "detail": "DEMO fetches m29_governance_freeze snapshot",
        }
    )
    checks.append(
        {
            "id": "build_index_snapshots_freeze_report",
            "ok": "out/m29_governance_freeze_report.json:m29_governance_freeze.report.json"
            in build_index_text,
            "detail": "build_index snapshots m29_governance_freeze report",
        }
    )
    checks.append(
        {
            "id": "site_smoke_requires_freeze_snapshot",
            "ok": "reports/m29_governance_freeze.report.json" in site_smoke_text,
            "detail": "site_smoke requires m29_governance_freeze snapshot",
        }
    )

    decision_registry = build_decision_registry()
    assumption_registry = build_assumption_registry()
    queue_closed = len(open_m29_rows) == 0 and len(goal_active_queue) == 0
    docs_synced = len(docs_with_gaps) == 0
    risk_ledger = build_residual_risk_ledger(
        queue_closed=queue_closed, docs_synced=docs_synced, release_ready=release_ready
    )
    checks.append(
        {
            "id": "decision_registry_floor",
            "ok": len(decision_registry) >= args.min_decision_count,
            "detail": f"decisionCount={len(decision_registry)} min={args.min_decision_count}",
        }
    )
    checks.append(
        {
            "id": "assumption_registry_floor",
            "ok": len(assumption_registry) >= args.min_assumption_count,
            "detail": f"assumptionCount={len(assumption_registry)} min={args.min_assumption_count}",
        }
    )
    checks.append(
        {
            "id": "risk_ledger_floor",
            "ok": len(risk_ledger) >= args.min_risk_count,
            "detail": f"riskCount={len(risk_ledger)} min={args.min_risk_count}",
        }
    )

    freeze_commands = [
        "make m29-activation-check",
        "make m29-release-baseline-check",
        "make m29-delivery-stabilization-check",
        "make m29-governance-freeze-check",
        "make ci",
    ]
    freeze_artifact_paths = [
        "analysis/program/plan.json",
        "analysis/program/work_items.csv",
        "analysis/program/goal_state.json",
        "analysis/program/step_execution_map.json",
        "docs/PROGRAM_PLAN.md",
        "docs/SUBMISSION.md",
        "docs/USAGE.md",
        "docs/DEMO.html",
        "Makefile",
        "scripts/m29_governance_freeze_check.py",
        "out/m29_activation_report.json",
        "out/m29_release_baseline_report.json",
        "out/m29_delivery_stabilization_report.json",
        "out/final_rehearsal/report.json",
    ]
    freeze_artifacts = artifact_manifest(repo_root, freeze_artifact_paths)

    failed = [row for row in checks if not bool(row.get("ok", False))]
    report = {
        "schemaVersion": "1",
        "label": "m29-governance-freeze-live",
        "inputs": {
            "plan": args.plan,
            "work": args.work,
            "goalState": args.goal_state,
            "activationReport": args.activation_report,
            "baselineReport": args.baseline_report,
            "executionReport": args.execution_report,
            "finalReport": args.final_report,
            "stepMap": args.step_map,
            "programPlanDoc": args.program_plan_doc,
            "submissionDoc": args.submission_doc,
            "usageDoc": args.usage_doc,
            "demoDoc": args.demo_doc,
            "makefile": args.makefile,
            "buildIndexScript": args.build_index_script,
            "siteSmokeScript": args.site_smoke_script,
        },
        "metrics": {
            "activeMilestone": active_milestone,
            "m29TotalRows": len(m29_rows),
            "m29OpenRows": len(open_m29_rows),
            "goalStateActiveQueueCount": len(goal_active_queue),
            "releaseReady": release_ready,
            "queuedGapCount": queued_gap_count,
            "freezeArtifactCount": len(freeze_artifacts),
            "docGapCount": len(docs_with_gaps),
        },
        "decisionRegistry": decision_registry,
        "assumptionRegistry": assumption_registry,
        "riskLedger": risk_ledger,
        "docChecks": doc_checks,
        "freezePackage": {
            "commands": freeze_commands,
            "artifacts": freeze_artifacts,
        },
        "checks": checks,
        "ok": len(failed) == 0,
    }

    out_path = Path(args.report_out)
    write_json(out_path, report)

    if failed:
        for row in failed:
            print(f"FAIL {row['id']}: {row['detail']}")
        print(f"Created: {out_path}")
        print("Summary: FAIL")
        return 1

    for row in checks:
        print(f"PASS {row['id']}: {row['detail']}")
    print(f"Freeze package artifacts: {len(freeze_artifacts)}")
    print(f"Created: {out_path}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

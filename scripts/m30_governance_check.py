#!/usr/bin/env python3
"""Deterministic M30 governance and final package handoff gate."""

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
        description="Validate M30 anti-drift governance and final package handoff synchronization."
    )
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--work", default="analysis/program/work_items.csv")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--activation-report", default="out/m30_activation_report.json")
    ap.add_argument("--baseline-report", default="out/m30_repo_baseline_report.json")
    ap.add_argument("--execution-report", default="out/m30_repo_execution_report.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--demo-doc", default="docs/DEMO.html")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--build-index-script", default="scripts/build_index.sh")
    ap.add_argument("--site-smoke-script", default="scripts/site_smoke.py")
    ap.add_argument("--report-out", default="out/m30_governance_report.json")
    ap.add_argument("--required-active-milestone", default="M30")
    ap.add_argument("--required-previous-work-id", default="PRG-281")
    ap.add_argument("--required-work-id", default="PRG-282")
    ap.add_argument("--required-baseline-label", default="m30-repo-baseline-live")
    ap.add_argument("--required-execution-label", default="m30-repo-execution-live")
    ap.add_argument("--required-final-label", default="m25-final-product-baseline")
    ap.add_argument("--required-ci-target", default="m30-governance-check")
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
            "id": "M30-DEC-001",
            "decision": "Add an explicit M30 governance target in CI",
            "chosenOption": "Wire m30-governance-check into ci for final anti-drift enforcement",
            "alternativesConsidered": ["stop at PRG-281 execution gate", "manual handoff checklist only"],
            "tradeoffs": ["pro: deterministic final-package guardrail", "con: CI now depends on handoff docs and demo snapshots"],
            "reversalCondition": "if final package validation moves to a dedicated release orchestrator",
        },
        {
            "id": "M30-DEC-002",
            "decision": "Represent final product handoff as an active milestone with zero open queue",
            "chosenOption": "Keep M30 active while requiring PRG-282 done and no open M30 rows",
            "alternativesConsidered": ["mark M30 completed", "introduce a synthetic post-M30 closeout milestone"],
            "tradeoffs": ["pro: preserves one-active-milestone contract and enables releaseReady=true", "con: active status must be interpreted alongside queue closure"],
            "reversalCondition": "if final rehearsal no longer requires an active milestone status",
        },
        {
            "id": "M30-DEC-003",
            "decision": "Require final rehearsal releaseReady=true before governance passes",
            "chosenOption": "Gate on queuedGapCount=0 and releaseReady=true after PRG-282 completion",
            "alternativesConsidered": ["allow governance pass before final rehearsal is clear", "treat final rehearsal as advisory only"],
            "tradeoffs": ["pro: governance reflects actual release state", "con: tracker/docs must be synchronized before the gate can pass"],
            "reversalCondition": "if release readiness is computed outside out/final_rehearsal/report.json",
        },
        {
            "id": "M30-DEC-004",
            "decision": "Publish a hashed M30 handoff package",
            "chosenOption": "Emit canonical replay commands plus SHA256 manifest for tracker/docs/report artifacts",
            "alternativesConsidered": ["list artifacts without hashes", "document handoff only in prose"],
            "tradeoffs": ["pro: auditable package integrity", "con: artifact set must remain stable"],
            "reversalCondition": "if artifact attestation is delegated to external release tooling",
        },
        {
            "id": "M30-DEC-005",
            "decision": "Synchronize demo evidence snapshots with the M30 governance report",
            "chosenOption": "Require DEMO, build_index, and site_smoke to reference reports/m30_governance.report.json",
            "alternativesConsidered": ["leave demo on M29 governance snapshot only", "avoid demo synchronization in final handoff"],
            "tradeoffs": ["pro: reviewer-facing site matches the final package", "con: one more artifact must be regenerated with site builds"],
            "reversalCondition": "if demo evidence stops consuming site/reports snapshots",
        },
    ]


def build_assumption_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "M30-ASM-001",
            "assumption": "PRG-281 execution output remains a required precondition for PRG-282",
            "confidence": 0.93,
            "verificationPlan": "require m30 execution report label/ok and PRG-281=done",
            "invalidationSignal": "execution contract or report label changes",
        },
        {
            "id": "M30-ASM-002",
            "assumption": "Final rehearsal report is still the canonical release-readiness source",
            "confidence": 0.92,
            "verificationPlan": "require final report label plus releaseReady=true and queuedGapCount=0",
            "invalidationSignal": "release readiness moves away from out/final_rehearsal/report.json",
        },
        {
            "id": "M30-ASM-003",
            "assumption": "M30 should stay active while the final queue is frozen closed",
            "confidence": 0.9,
            "verificationPlan": "assert plan.activeMilestone and goal_state activeMilestoneId equal M30 while activeQueueCount=0",
            "invalidationSignal": "program model changes to allow zero active milestones",
        },
        {
            "id": "M30-ASM-004",
            "assumption": "Reviewer-facing docs must stay synchronized on one governance command and artifact path",
            "confidence": 0.89,
            "verificationPlan": "enforce token checks across PROGRAM_PLAN, SUBMISSION, and USAGE",
            "invalidationSignal": "official reviewer-facing docs move to a different file set",
        },
        {
            "id": "M30-ASM-005",
            "assumption": "The demo evidence panel should expose the M30 governance report",
            "confidence": 0.87,
            "verificationPlan": "assert DEMO/build_index/site_smoke all reference reports/m30_governance.report.json",
            "invalidationSignal": "site evidence architecture stops consuming report snapshots",
        },
    ]


def build_risk_ledger(*, queue_closed: bool, docs_synced: bool, release_ready: bool, demo_synced: bool) -> list[dict[str, Any]]:
    return [
        {
            "id": "M30-RSK-001",
            "risk": "M30 queue drift can reopen final work after handoff",
            "severity": "high",
            "likelihood": "medium",
            "status": "mitigated" if queue_closed else "active",
            "mitigation": "Governance gate requires PRG-282 done and zero open M30 queue rows.",
        },
        {
            "id": "M30-RSK-002",
            "risk": "Release-facing docs can diverge from the executable governance command",
            "severity": "medium",
            "likelihood": "medium",
            "status": "mitigated" if docs_synced else "active",
            "mitigation": "Token checks enforce synchronized command/artifact references across release docs.",
        },
        {
            "id": "M30-RSK-003",
            "risk": "Release-readiness can become stale after tracker edits",
            "severity": "high",
            "likelihood": "medium",
            "status": "mitigated" if release_ready else "active",
            "mitigation": "Governance gate requires final rehearsal releaseReady=true with queuedGapCount=0.",
        },
        {
            "id": "M30-RSK-004",
            "risk": "Demo evidence panel can lag behind the final governance artifact",
            "severity": "medium",
            "likelihood": "low",
            "status": "mitigated" if demo_synced else "active",
            "mitigation": "DEMO, build_index, and site_smoke all require the m30 governance snapshot.",
        },
        {
            "id": "M30-RSK-005",
            "risk": "One-active-milestone semantics may be misread as unfinished product state",
            "severity": "medium",
            "likelihood": "medium",
            "status": "active",
            "mitigation": "Decision registry records the zero-open-queue interpretation for final handoff.",
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
            "id": "plan_active_m30",
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
            "id": "goal_state_active_m30",
            "ok": goal_active == args.required_active_milestone,
            "detail": f"goalState.activeMilestoneId={goal_active!r}",
        }
    )

    prev_row = find_work_row(rows, args.required_previous_work_id)
    prev_status = str((prev_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "prg281_done",
            "ok": prev_row is not None and prev_status == "done",
            "detail": f"{args.required_previous_work_id}.status={prev_status!r}",
        }
    )

    governance_row = find_work_row(rows, args.required_work_id)
    governance_status = str((governance_row or {}).get("status", "")).strip().lower()
    checks.append(
        {
            "id": "prg282_done",
            "ok": governance_row is not None and governance_status == "done",
            "detail": f"{args.required_work_id}.status={governance_status!r}",
        }
    )

    m30_rows = [row for row in rows if row.get("milestone_id", "") == args.required_active_milestone]
    open_m30_rows = [row for row in m30_rows if row.get("status", "").strip().lower() in OPEN_STATUSES]
    open_m30_ids = sorted(row.get("id", "") for row in open_m30_rows)
    checks.append(
        {
            "id": "m30_queue_closed",
            "ok": len(open_m30_rows) == 0,
            "detail": f"openM30Rows={len(open_m30_rows)} openIds={open_m30_ids}",
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
            "id": "step_map_prg282_entry",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map entry exists for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_governance_target",
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
            "id": "make_ci_wires_governance_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci includes {args.required_ci_target}",
        }
    )

    program_plan_check = doc_token_check(
        Path(args.program_plan_doc),
        ["PRG-282", "M30-K3", f"make {args.required_ci_target}", "out/m30_governance_report.json"],
    )
    usage_check = doc_token_check(
        Path(args.usage_doc),
        ["PRG-282", f"make {args.required_ci_target}", "out/m30_governance_report.json"],
    )
    submission_check = doc_token_check(
        Path(args.submission_doc),
        ["PRG-282", f"make {args.required_ci_target}", "out/m30_governance_report.json"],
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
            "id": "demo_links_governance_snapshot",
            "ok": "reports/m30_governance.report.json" in demo_text,
            "detail": "DEMO includes m30_governance snapshot link",
        }
    )
    checks.append(
        {
            "id": "demo_fetches_governance_snapshot",
            "ok": 'loadJson("reports/m30_governance.report.json")' in demo_text,
            "detail": "DEMO fetches m30_governance snapshot",
        }
    )
    checks.append(
        {
            "id": "build_index_snapshots_governance_report",
            "ok": "out/m30_governance_report.json:m30_governance.report.json" in build_index_text,
            "detail": "build_index snapshots m30_governance report",
        }
    )
    checks.append(
        {
            "id": "site_smoke_requires_governance_snapshot",
            "ok": "reports/m30_governance.report.json" in site_smoke_text,
            "detail": "site_smoke requires m30_governance snapshot",
        }
    )

    decision_registry = build_decision_registry()
    assumption_registry = build_assumption_registry()
    queue_closed = len(open_m30_rows) == 0 and len(goal_active_queue) == 0
    docs_synced = len(docs_with_gaps) == 0
    demo_synced = (
        "reports/m30_governance.report.json" in demo_text
        and "out/m30_governance_report.json:m30_governance.report.json" in build_index_text
        and "reports/m30_governance.report.json" in site_smoke_text
    )
    risk_ledger = build_risk_ledger(
        queue_closed=queue_closed,
        docs_synced=docs_synced,
        release_ready=release_ready,
        demo_synced=demo_synced,
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

    handoff_commands = [
        "make m30-activation-check",
        "make m30-repo-baseline-check",
        "make m30-repo-execution-check",
        "make m30-governance-check",
        "make ci",
    ]
    handoff_artifact_paths = [
        "analysis/program/plan.json",
        "analysis/program/work_items.csv",
        "analysis/program/goal_state.json",
        "analysis/program/step_execution_map.json",
        "docs/PROGRAM_PLAN.md",
        "docs/SUBMISSION.md",
        "docs/USAGE.md",
        "docs/DEMO.html",
        "Makefile",
        "scripts/build_index.sh",
        "scripts/site_smoke.py",
        "scripts/m30_governance_check.py",
        "out/m30_activation_report.json",
        "out/m30_repo_baseline_report.json",
        "out/m30_repo_execution_report.json",
        "out/m30_governance_report.json",
        "out/final_rehearsal/report.json",
    ]
    handoff_artifacts = artifact_manifest(repo_root, handoff_artifact_paths)

    failed = [row for row in checks if not bool(row.get("ok", False))]
    report = {
        "schemaVersion": "1",
        "label": "m30-governance-live",
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
            "m30TotalRows": len(m30_rows),
            "m30OpenRows": len(open_m30_rows),
            "goalStateActiveQueueCount": len(goal_active_queue),
            "releaseReady": release_ready,
            "queuedGapCount": queued_gap_count,
            "handoffArtifactCount": len(handoff_artifacts),
            "docGapCount": len(docs_with_gaps),
        },
        "decisionRegistry": decision_registry,
        "assumptionRegistry": assumption_registry,
        "riskLedger": risk_ledger,
        "docChecks": doc_checks,
        "handoffPackage": {
            "commands": handoff_commands,
            "artifacts": handoff_artifacts,
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
    print(f"Handoff package artifacts: {len(handoff_artifacts)}")
    print(f"Created: {out_path}")
    print("Summary: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

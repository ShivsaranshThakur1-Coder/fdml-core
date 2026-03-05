#!/usr/bin/env python3
"""Deterministic final product-readiness baseline and gap ledger for M25-K1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_ARTIFACTS = [
    "analysis/program/approval_report.json",
    "analysis/program/goal_state.json",
    "analysis/program/plan.json",
    "out/m24_pipeline_governance.json",
    "out/m24_residual_failure_closure_report.json",
    "out/m24_descriptor_completion_report.json",
    "out/m24_validator_burndown_report.json",
    "docs/PROGRAM_PLAN.md",
    "docs/SUBMISSION.md",
    "docs/USAGE.md",
    "Makefile",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Generate deterministic M25 final product-readiness baseline report."
    )
    ap.add_argument("--approval-report", default="analysis/program/approval_report.json")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--plan", default="analysis/program/plan.json")
    ap.add_argument("--m24-governance-report", default="out/m24_pipeline_governance.json")
    ap.add_argument("--m24-residual-report", default="out/m24_residual_failure_closure_report.json")
    ap.add_argument("--m24-descriptor-report", default="out/m24_descriptor_completion_report.json")
    ap.add_argument("--m24-burndown-report", default="out/m24_validator_burndown_report.json")
    ap.add_argument("--report-out", default="out/final_rehearsal/report.json")
    ap.add_argument("--label", default="m25-final-product-baseline")
    ap.add_argument("--required-active-milestone", default="")
    ap.add_argument("--required-previous-milestone", default="M24")
    ap.add_argument("--min-total-files", type=int, default=100)
    ap.add_argument("--min-validator-rules", type=int, default=20)
    ap.add_argument("--min-reduction-ratio", type=float, default=1.0)
    ap.add_argument("--max-failure-file-ratio", type=float, default=0.0)
    return ap.parse_args()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"missing required artifact: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(obj, dict), f"{path} must contain a JSON object")
    return obj


def as_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise RuntimeError(f"invalid integer for {field}: {value!r}") from exc


def as_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise RuntimeError(f"invalid float for {field}: {value!r}") from exc


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
        require(p.exists(), f"missing required artifact: {rel}")
        records.append(
            {
                "path": rel,
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
        )
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def find_milestone(plan: dict[str, Any], milestone_id: str) -> dict[str, Any] | None:
    milestones = plan.get("milestones")
    if not isinstance(milestones, list):
        return None
    for row in milestones:
        if isinstance(row, dict) and str(row.get("id", "")).strip() == milestone_id:
            return row
    return None


def collect_gap_ledger(goal_state: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    project_context = goal_state.get("projectContext") or {}
    execution_state = goal_state.get("executionState") or {}

    active_status = str(project_context.get("activeMilestoneStatus", "")).strip().lower()
    active_id = str(project_context.get("activeMilestoneId", "")).strip()
    active_queue = execution_state.get("activeQueue") or []
    blocked = execution_state.get("blocked") or []

    active_queue_rows = [row for row in active_queue if isinstance(row, dict)] if isinstance(active_queue, list) else []
    blocked_rows = [row for row in blocked if isinstance(row, dict)] if isinstance(blocked, list) else []

    # Program guardrails enforce exactly one active milestone. For closeout readiness,
    # treat non-completed status as a gap only when work is still queued or blocked.
    if active_status != "completed" and (active_queue_rows or blocked_rows):
        gaps.append(
            {
                "id": f"{active_id}-status-open",
                "type": "milestone_status",
                "severity": "high",
                "status": active_status or "unknown",
                "title": f"{active_id} is not completed",
                "closureTarget": (
                    "Finish remaining queued/blocked work. "
                    "Milestone closure can stay open while one-active-milestone guardrail is preserved."
                ),
            }
        )

    for row in active_queue_rows:
        status = str(row.get("status", "")).strip()
        gaps.append(
            {
                "id": str(row.get("id", "")).strip() or "unknown-work-item",
                "type": "queued_work",
                "severity": "high" if status in {"blocked", "in_progress"} else "medium",
                "status": status or "unknown",
                "kpiId": str(row.get("kpiId", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "closureTarget": "Complete this queued item and re-run baseline check.",
            }
        )

    for row in blocked_rows:
        gaps.append(
            {
                "id": str(row.get("id", "")).strip() or "unknown-blocked-item",
                "type": "blocked_work",
                "severity": "high",
                "status": "blocked",
                "kpiId": str(row.get("kpiId", "")).strip(),
                "title": str(row.get("title", "")).strip(),
                "closureTarget": "Resolve blocker and complete item.",
            }
        )

    return gaps


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()

    approval = load_json(repo_root / args.approval_report)
    goal_state = load_json(repo_root / args.goal_state)
    plan = load_json(repo_root / args.plan)
    m24_governance = load_json(repo_root / args.m24_governance_report)
    m24_residual = load_json(repo_root / args.m24_residual_report)
    m24_descriptor = load_json(repo_root / args.m24_descriptor_report)
    m24_burndown = load_json(repo_root / args.m24_burndown_report)

    checks: list[dict[str, Any]] = []

    total_done = as_int(approval.get("totalDone", 0), "approval.totalDone")
    approved = as_int(approval.get("approved", 0), "approval.approved")
    denied = as_int(approval.get("denied", 0), "approval.denied")
    program_gate_ok = bool((approval.get("programGate") or {}).get("ok", False))
    checks.append(
        {
            "id": "approval_gate_ok",
            "ok": program_gate_ok and denied == 0 and approved == total_done and total_done > 0,
            "detail": (
                f"programGateOk={program_gate_ok} totalDone={total_done} "
                f"approved={approved} denied={denied}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    goal_context = goal_state.get("projectContext") or {}
    goal_active = str(goal_context.get("activeMilestoneId", "")).strip()
    goal_active_status = str(goal_context.get("activeMilestoneStatus", "")).strip()
    required_active = str(args.required_active_milestone or "").strip()
    goal_active_ok = goal_active == required_active if required_active else bool(goal_active)
    checks.append(
        {
            "id": "goal_state_active_milestone",
            "ok": goal_active_ok,
            "detail": (
                f"activeMilestone={goal_active!r} "
                f"required={(required_active or '<any-active>')!r}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    plan_active = str(plan.get("activeMilestone", "")).strip()
    plan_active_ok = plan_active == required_active if required_active else bool(plan_active)
    checks.append(
        {
            "id": "plan_active_milestone",
            "ok": plan_active_ok,
            "detail": (
                f"plan.activeMilestone={plan_active!r} "
                f"required={(required_active or '<any-active>')!r}"
            ),
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

    active_target = required_active or plan_active
    active = find_milestone(plan, active_target)
    require(active is not None, f"plan missing milestone: {active_target}")
    active_status = str(active.get("status", "")).strip().lower()
    checks.append(
        {
            "id": "active_milestone_status_valid",
            "ok": active_status == "active",
            "detail": f"{active_target}.status={active_status!r}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    governance_ok = bool(m24_governance.get("ok", False))
    governance_checks = m24_governance.get("checks") or []
    failed_governance_checks = [
        row
        for row in governance_checks
        if isinstance(row, dict) and not bool(row.get("ok", False))
    ]
    checks.append(
        {
            "id": "m24_governance_ok",
            "ok": governance_ok and len(failed_governance_checks) == 0,
            "detail": (
                f"governance_ok={governance_ok} "
                f"failed_checks={len(failed_governance_checks)}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    governance_metrics = m24_governance.get("metrics") or {}
    validator_processed = as_int(
        governance_metrics.get("validatorProcessedFiles", 0),
        "m24 governance metrics.validatorProcessedFiles",
    )
    validator_rules = as_int(
        governance_metrics.get("validatorRuleCount", 0),
        "m24 governance metrics.validatorRuleCount",
    )
    reduction_ratio = as_float(
        governance_metrics.get("burndownReductionRatio", 0.0),
        "m24 governance metrics.burndownReductionRatio",
    )
    failure_file_ratio = as_float(
        governance_metrics.get("burndownFailureFileRatio", 1.0),
        "m24 governance metrics.burndownFailureFileRatio",
    )

    checks.append(
        {
            "id": "m24_validator_scale",
            "ok": validator_processed >= args.min_total_files,
            "detail": f"validator_processed={validator_processed} min={args.min_total_files}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "m24_validator_rule_floor",
            "ok": validator_rules >= args.min_validator_rules,
            "detail": f"validator_rules={validator_rules} min={args.min_validator_rules}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "m24_burndown_floor",
            "ok": reduction_ratio >= args.min_reduction_ratio,
            "detail": f"reduction_ratio={reduction_ratio:.4f} min={args.min_reduction_ratio:.4f}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    checks.append(
        {
            "id": "m24_failure_file_ratio_cap",
            "ok": failure_file_ratio <= args.max_failure_file_ratio,
            "detail": f"failure_file_ratio={failure_file_ratio:.4f} max={args.max_failure_file_ratio:.4f}",
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    residual_totals = m24_residual.get("totals") or {}
    residual_processed = as_int(residual_totals.get("processedFiles", 0), "m24 residual processedFiles")
    residual_unresolved = as_int(
        residual_totals.get("unresolvedTargetRules", 0),
        "m24 residual unresolvedTargetRules",
    )
    residual_doctor_rate = as_float(
        residual_totals.get("doctorPassRate", 0.0),
        "m24 residual doctorPassRate",
    )
    residual_geo_rate = as_float(
        residual_totals.get("geoPassRate", 0.0),
        "m24 residual geoPassRate",
    )
    checks.append(
        {
            "id": "m24_residual_quality",
            "ok": (
                residual_processed >= args.min_total_files
                and residual_unresolved == 0
                and residual_doctor_rate >= 1.0
                and residual_geo_rate >= 1.0
            ),
            "detail": (
                f"processed={residual_processed} unresolved={residual_unresolved} "
                f"doctor={residual_doctor_rate:.4f} geo={residual_geo_rate:.4f}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    descriptor_totals = m24_descriptor.get("totals") or {}
    descriptor_processed = as_int(
        descriptor_totals.get("processedFiles", 0),
        "m24 descriptor processedFiles",
    )
    low_support_growth = as_int(
        descriptor_totals.get("lowSupportKeysWithGrowth", 0),
        "m24 descriptor lowSupportKeysWithGrowth",
    )
    residual_growth_after = as_int(
        descriptor_totals.get("residualPotentialGrowthAfter", 0),
        "m24 descriptor residualPotentialGrowthAfter",
    )
    checks.append(
        {
            "id": "m24_descriptor_completion",
            "ok": (
                descriptor_processed >= args.min_total_files
                and low_support_growth >= 2
                and residual_growth_after == 0
            ),
            "detail": (
                f"processed={descriptor_processed} low_support_growth={low_support_growth} "
                f"residual_growth_after={residual_growth_after}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    burndown_ok = bool(m24_burndown.get("ok", False))
    burndown_totals = m24_burndown.get("totals") or {}
    burndown_baseline_failures = as_int(
        burndown_totals.get("baselineRuleFailures", 0),
        "m24 burndown baselineRuleFailures",
    )
    burndown_current_failures = as_int(
        burndown_totals.get("currentRuleFailures", 0),
        "m24 burndown currentRuleFailures",
    )
    checks.append(
        {
            "id": "m24_burndown_ok",
            "ok": burndown_ok and burndown_current_failures <= burndown_baseline_failures,
            "detail": (
                f"burndown_ok={burndown_ok} baseline_failures={burndown_baseline_failures} "
                f"current_failures={burndown_current_failures}"
            ),
        }
    )
    require(checks[-1]["ok"], checks[-1]["detail"])

    gaps = collect_gap_ledger(goal_state)
    release_ready = len(gaps) == 0

    architecture = {
        "singlePipeline": True,
        "activeMilestone": goal_active,
        "activeMilestoneStatus": goal_active_status,
        "baselineCorpusDir": str((m24_governance.get("thresholds") or {}).get("requiredSourceDir", "")),
        "residualCorpusDir": str((m24_governance.get("thresholds") or {}).get("requiredResidualOutDir", "")),
        "descriptorCorpusDir": str((m24_governance.get("thresholds") or {}).get("requiredDescriptorOutDir", "")),
        "validatorRuleCount": validator_rules,
        "validatorProcessedFiles": validator_processed,
    }

    quality = {
        "doctorPassRate": residual_doctor_rate,
        "geometryPassRate": residual_geo_rate,
        "validatorFailureReductionRatio": reduction_ratio,
        "validatorFailureFileRatio": failure_file_ratio,
        "descriptorLowSupportGrowthKeys": low_support_growth,
        "descriptorResidualGrowthAfter": residual_growth_after,
    }

    reproducibility = {
        "programGateOk": program_gate_ok,
        "approvedDoneItems": approved,
        "doneItems": total_done,
        "deniedDoneItems": denied,
        "governanceDecisionCount": len(m24_governance.get("decisionRegistry") or []),
        "governanceAssumptionCount": len(m24_governance.get("assumptionRegistry") or []),
        "governanceRiskCount": len(m24_governance.get("riskLedger") or []),
        "checkedArtifacts": len(REQUIRED_ARTIFACTS),
    }

    artifacts = artifact_manifest(repo_root, REQUIRED_ARTIFACTS)
    report = {
        "schemaVersion": "2",
        "label": args.label,
        "ok": True,
        "releaseReady": release_ready,
        "checks": checks,
        "summary": {
            "activeMilestone": goal_active,
            "activeMilestoneStatus": goal_active_status,
            "queuedGapCount": len(gaps),
            "releaseReady": release_ready,
            "nextExecutionHint": str(goal_state.get("nextExecutionHint", "")).strip(),
        },
        "baseline": {
            "architecture": architecture,
            "quality": quality,
            "reproducibility": reproducibility,
        },
        "gaps": gaps,
        "artifacts": artifacts,
    }

    out_path = Path(args.report_out)
    write_json(out_path, report)
    print(
        "PASS: final-rehearsal-baseline "
        f"(active={goal_active}, rules={validator_rules}, gaps={len(gaps)}, "
        f"releaseReady={release_ready})"
    )
    print(f"Created: {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)

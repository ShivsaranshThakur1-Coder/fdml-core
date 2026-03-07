#!/usr/bin/env python3
"""Deterministic M28 website narrative baseline and prioritized correction backlog."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}
EFFORT_WEIGHT = {"small": 1, "medium": 2, "large": 3}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Generate M28 baseline for website narrative correctness and correction backlog."
    )
    ap.add_argument("--demo-doc", default="docs/DEMO.html")
    ap.add_argument("--search-doc", default="docs/search.html")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--goal-state", default="analysis/program/goal_state.json")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m28_narrative_baseline_report.json")
    ap.add_argument("--required-work-id", default="PRG-271")
    ap.add_argument("--required-next-work-id", default="PRG-272")
    ap.add_argument("--required-ci-target", default="m28-narrative-baseline-check")
    ap.add_argument("--min-backlog-items", type=int, default=0)
    ap.add_argument("--min-active-queue-count", type=int, default=0)
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def count_occurrences(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def add_gap(
    gaps: list[dict[str, Any]],
    *,
    gap_id: str,
    title: str,
    severity: str,
    effort: str,
    evidence: str,
    recommendation: str,
) -> None:
    severity = severity.lower().strip()
    effort = effort.lower().strip()
    score = (SEVERITY_WEIGHT.get(severity, 1) * 10) - EFFORT_WEIGHT.get(effort, 3)
    gaps.append(
        {
            "id": gap_id,
            "title": title,
            "severity": severity,
            "effort": effort,
            "score": score,
            "evidence": evidence,
            "recommendation": recommendation,
        }
    )


def main() -> int:
    args = parse_args()

    demo_text = Path(args.demo_doc).read_text(encoding="utf-8")
    search_text = Path(args.search_doc).read_text(encoding="utf-8")
    submission_text = Path(args.submission_doc).read_text(encoding="utf-8")
    usage_text = Path(args.usage_doc).read_text(encoding="utf-8")
    program_plan_text = Path(args.program_plan_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    goal_state = load_json(Path(args.goal_state))
    final_report = load_json(Path(args.final_report))
    step_map = load_json(Path(args.step_map))

    items = step_map.get("items") if isinstance(step_map.get("items"), dict) else {}
    step_entry = items.get(args.required_work_id) if isinstance(items, dict) else None
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    commands_list = [str(c).strip() for c in commands] if isinstance(commands, list) else []
    step_note = step_entry.get("note") if isinstance(step_entry, dict) else ""

    project_context = goal_state.get("projectContext") if isinstance(goal_state.get("projectContext"), dict) else {}
    execution_state = goal_state.get("executionState") if isinstance(goal_state.get("executionState"), dict) else {}
    active_goal_milestone = str(project_context.get("activeMilestoneId", "")).strip()
    active_queue = execution_state.get("activeQueue") if isinstance(execution_state.get("activeQueue"), list) else []

    final_summary = final_report.get("summary") if isinstance(final_report.get("summary"), dict) else {}
    final_release_ready = bool(final_report.get("releaseReady", False))
    final_queued_gap_count = int(final_summary.get("queuedGapCount", -1))
    final_active_milestone = str(final_summary.get("activeMilestone", "")).strip()

    gaps: list[dict[str, Any]] = []

    if 'id="m27-story"' in demo_text:
        add_gap(
            gaps,
            gap_id="demo_m27_id_stale",
            title="Demo narrative anchor still uses M27-specific id",
            severity="medium",
            effort="small",
            evidence='`docs/DEMO.html` contains `id="m27-story"`',
            recommendation="Rename to an M28-neutral or M28-specific id and keep site-smoke selectors synchronized.",
        )
    if "M27 Story Walkthrough" in demo_text:
        add_gap(
            gaps,
            gap_id="demo_walkthrough_heading_stale",
            title="Demo walkthrough heading still references M27",
            severity="high",
            effort="small",
            evidence='`docs/DEMO.html` still labels the walkthrough as `M27 Story Walkthrough`.',
            recommendation="Update heading and walkthrough bullets to reflect current M28 objective and queue context.",
        )
    if "reports/m28_activation.report.json" not in demo_text:
        add_gap(
            gaps,
            gap_id="demo_missing_m28_activation_snapshot",
            title="Demo dashboard does not list M28 activation snapshot",
            severity="high",
            effort="small",
            evidence='`docs/DEMO.html` evidence list omits `reports/m28_activation.report.json`.',
            recommendation="Add M28 activation report to dashboard evidence links and metric rendering.",
        )
    if 'loadJson("reports/m28_activation.report.json")' not in demo_text:
        add_gap(
            gaps,
            gap_id="demo_missing_m28_fetch",
            title="Demo script does not fetch M28 activation report",
            severity="high",
            effort="small",
            evidence='`docs/DEMO.html` fetch block has no `loadJson("reports/m28_activation.report.json")` call.',
            recommendation="Fetch the M28 report and expose M28 queue/baseline values in the status cards.",
        )
    if "M26 Handoff Governance" in demo_text:
        add_gap(
            gaps,
            gap_id="demo_card_label_stale_m26",
            title="Demo dashboard still highlights M26 handoff card label",
            severity="medium",
            effort="small",
            evidence="`docs/DEMO.html` card title still uses `M26 Handoff Governance`.",
            recommendation="Retitle card to current execution context or add distinct M28 baseline/governance cards.",
        )
    if "active=M26" in submission_text:
        add_gap(
            gaps,
            gap_id="submission_snapshot_active_milestone_stale",
            title="Submission snapshot still reports active=M26",
            severity="high",
            effort="small",
            evidence="`docs/SUBMISSION.md` current local snapshot contains `active=M26`.",
            recommendation="Refresh snapshot block to current milestone state and include M28 baseline references.",
        )
    if "M26 activation gate: PASS" in submission_text and "M28 activation" not in submission_text:
        add_gap(
            gaps,
            gap_id="submission_snapshot_missing_m28_line",
            title="Submission snapshot missing M28 activation status line",
            severity="medium",
            effort="small",
            evidence="`docs/SUBMISSION.md` includes M26 activation line but no M28 activation snapshot line.",
            recommendation="Add explicit M28 activation status line with key metrics from `out/m28_activation_report.json`.",
        )

    gaps.sort(key=lambda row: (-int(row.get("score", 0)), str(row.get("id", ""))))
    top_gaps = gaps[:5]

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "id": "goal_state_active_m28",
            "ok": active_goal_milestone == "M28",
            "detail": f"goal_state.activeMilestoneId={active_goal_milestone!r}",
        }
    )
    checks.append(
        {
            "id": "goal_state_active_queue_threshold",
            "ok": len(active_queue) >= args.min_active_queue_count,
            "detail": (
                f"goal_state.activeQueueCount={len(active_queue)} "
                f"minRequired={args.min_active_queue_count}"
            ),
        }
    )
    checks.append(
        {
            "id": "final_report_release_ready",
            "ok": final_release_ready and final_queued_gap_count == 0,
            "detail": f"releaseReady={final_release_ready} queuedGapCount={final_queued_gap_count}",
        }
    )
    checks.append(
        {
            "id": "step_map_has_prg271_entry",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map has entry for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_baseline_target",
            "ok": any(args.required_ci_target in cmd for cmd in commands_list),
            "detail": f"{args.required_work_id}.commands={commands_list}",
        }
    )
    checks.append(
        {
            "id": "step_map_mentions_next_work",
            "ok": str(args.required_next_work_id) in str(step_note),
            "detail": f"{args.required_work_id}.note references {args.required_next_work_id}",
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
            "id": "make_ci_wires_baseline_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci target includes {args.required_ci_target}",
        }
    )
    checks.append(
        {
            "id": "program_plan_mentions_prg271",
            "ok": has_all(
                program_plan_text,
                [
                    "M28",
                    "PRG-271",
                    args.required_ci_target,
                    "out/m28_narrative_baseline_report.json",
                ],
            ),
            "detail": "PROGRAM_PLAN.md includes M28 baseline command/artifact references",
        }
    )
    checks.append(
        {
            "id": "usage_mentions_baseline_target",
            "ok": has_all(
                usage_text,
                [
                    "PRG-271",
                    f"make {args.required_ci_target}",
                    "out/m28_narrative_baseline_report.json",
                ],
            ),
            "detail": "USAGE.md includes M28 baseline command section",
        }
    )
    checks.append(
        {
            "id": "backlog_minimum_count",
            "ok": len(gaps) >= args.min_backlog_items,
            "detail": f"backlogCount={len(gaps)} minRequired={args.min_backlog_items}",
        }
    )
    checks.append(
        {
            "id": "search_filters_present",
            "ok": has_all(
                search_text,
                [
                    'id="sourceCategory"',
                    'id="fullDescriptionTier"',
                    'id="strictOnly"',
                    'id="hasGeometry"',
                    'id="copyLink"',
                ],
            ),
            "detail": "search.html retains required narrative filter controls",
        }
    )

    ok = all(bool(row.get("ok")) for row in checks)
    payload = {
        "label": "m28-website-narrative-baseline-live",
        "ok": ok,
        "checks": checks,
        "metrics": {
            "activeMilestoneGoalState": active_goal_milestone,
            "activeQueueCount": len(active_queue),
            "finalReportActiveMilestone": final_active_milestone,
            "finalReportReleaseReady": final_release_ready,
            "finalReportQueuedGapCount": final_queued_gap_count,
            "m27TokenCountDemo": count_occurrences(demo_text, r"\bm27\b"),
            "m26TokenCountSubmission": count_occurrences(submission_text, r"\bm26\b"),
            "backlogCount": len(gaps),
            "topBacklogIds": [str(row.get("id")) for row in top_gaps],
        },
        "backlog": gaps,
        "summary": {
            "checkCount": len(checks),
            "passCount": sum(1 for row in checks if row.get("ok")),
            "failedIds": [str(row.get("id")) for row in checks if not row.get("ok")],
            "requiredWorkId": args.required_work_id,
            "requiredNextWorkId": args.required_next_work_id,
            "requiredCiTarget": args.required_ci_target,
            "topPriorityBacklog": top_gaps,
        },
    }
    write_json(Path(args.report_out), payload)

    if ok:
        print(
            "PASS: m28 website narrative baseline check ("
            f"checks={payload['summary']['passCount']}/{payload['summary']['checkCount']}, "
            f"backlog={len(gaps)}, "
            f"report={args.report_out})"
        )
        return 0

    print(
        "FAIL: m28 website narrative baseline check ("
        f"failed={','.join(payload['summary']['failedIds'])}, "
        f"report={args.report_out})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

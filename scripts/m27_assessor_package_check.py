#!/usr/bin/env python3
"""M27 portfolio narrative + assessor walkthrough package gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate M27 assessor narrative package and evidence synchronization."
    )
    ap.add_argument("--walkthrough-doc", default="docs/ASSESSOR_WALKTHROUGH.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--program-plan-doc", default="docs/PROGRAM_PLAN.md")
    ap.add_argument("--final-report", default="out/final_rehearsal/report.json")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m27_assessor_package_report.json")
    ap.add_argument("--required-work-id", default="PRG-267")
    ap.add_argument("--required-ci-target", default="m27-assessor-package-check")
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


def main() -> int:
    args = parse_args()

    walkthrough_text = Path(args.walkthrough_doc).read_text(encoding="utf-8")
    submission_text = Path(args.submission_doc).read_text(encoding="utf-8")
    program_plan_text = Path(args.program_plan_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    step_map = load_json(Path(args.step_map))
    final_report = load_json(Path(args.final_report))

    items = step_map.get("items") if isinstance(step_map.get("items"), dict) else {}
    step_entry = items.get(args.required_work_id) if isinstance(items, dict) else None
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    commands_list = [str(c).strip() for c in commands] if isinstance(commands, list) else []

    final_summary = final_report.get("summary") if isinstance(final_report.get("summary"), dict) else {}
    final_release_ready = bool(final_report.get("releaseReady", False))
    queued_gap_count = int(final_summary.get("queuedGapCount", -1))

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "id": "walkthrough_sections_present",
            "ok": has_all(
                walkthrough_text,
                [
                    "# fdml assessor walkthrough package",
                    "## 1) project in plain language",
                    "## 2) what is stored in fdml (non-code)",
                    "## 3) how validation works (non-code)",
                    "## 4) live demonstration script",
                    "## 5) evidence map (claim -> artifact)",
                    "## 6) limitations and scope",
                    "## 7) portfolio framing",
                ],
            ),
            "detail": "walkthrough includes required narrative sections",
        }
    )
    checks.append(
        {
            "id": "walkthrough_commands_present",
            "ok": has_all(
                walkthrough_text,
                [
                    "make final-rehearsal-check",
                    "make site-check",
                    "make m27-cloud-workflow-check",
                    "make m27-assessor-package-check",
                ],
            ),
            "detail": "walkthrough includes deterministic assessor command path",
        }
    )
    checks.append(
        {
            "id": "submission_mentions_walkthrough_package",
            "ok": has_all(
                submission_text,
                [
                    "M27-K3",
                    "docs/ASSESSOR_WALKTHROUGH.md",
                    "make m27-assessor-package-check",
                    "out/m27_assessor_package_report.json",
                ],
            ),
            "detail": "submission doc includes M27-K3 package references",
        }
    )
    checks.append(
        {
            "id": "program_plan_mentions_prg267",
            "ok": has_all(
                program_plan_text,
                [
                    "PRG-267",
                    "M27-K3",
                    "assessor walkthrough",
                ],
            ),
            "detail": "program plan includes PRG-267 narrative line(s)",
        }
    )
    checks.append(
        {
            "id": "final_report_release_ready",
            "ok": final_release_ready and queued_gap_count == 0,
            "detail": f"releaseReady={final_release_ready} queuedGapCount={queued_gap_count}",
        }
    )
    checks.append(
        {
            "id": "step_map_has_prg267_entry",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map has entry for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_assessor_target",
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
            "id": "make_ci_wires_assessor_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci target includes {args.required_ci_target}",
        }
    )

    ok = all(bool(c.get("ok")) for c in checks)
    payload = {
        "label": "m27-assessor-package-live",
        "ok": ok,
        "checks": checks,
        "summary": {
            "checkCount": len(checks),
            "passCount": sum(1 for c in checks if c.get("ok")),
            "failedIds": [str(c.get("id")) for c in checks if not c.get("ok")],
            "requiredWorkId": args.required_work_id,
            "requiredCiTarget": args.required_ci_target,
        },
    }
    write_json(Path(args.report_out), payload)

    if ok:
        print(
            "PASS: m27 assessor package check ("
            f"checks={payload['summary']['passCount']}/{payload['summary']['checkCount']}, "
            f"report={args.report_out})"
        )
        return 0
    print(
        "FAIL: m27 assessor package check ("
        f"failed={','.join(payload['summary']['failedIds'])}, "
        f"report={args.report_out})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

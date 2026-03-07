#!/usr/bin/env python3
"""M27 cloud version-control and release workflow documentation gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Validate deterministic cloud version-control and release workflow documentation."
    )
    ap.add_argument("--usage-doc", default="docs/USAGE.md")
    ap.add_argument("--submission-doc", default="docs/SUBMISSION.md")
    ap.add_argument("--step-map", default="analysis/program/step_execution_map.json")
    ap.add_argument("--makefile", default="Makefile")
    ap.add_argument("--report-out", default="out/m27_cloud_workflow_report.json")
    ap.add_argument("--required-work-id", default="PRG-266")
    ap.add_argument("--required-next-work-id", default="PRG-267")
    ap.add_argument("--required-ci-target", default="m27-cloud-workflow-check")
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

    usage_text = Path(args.usage_doc).read_text(encoding="utf-8")
    submission_text = Path(args.submission_doc).read_text(encoding="utf-8")
    makefile_text = Path(args.makefile).read_text(encoding="utf-8")
    step_map = load_json(Path(args.step_map))

    items = step_map.get("items") if isinstance(step_map.get("items"), dict) else {}
    step_entry = items.get(args.required_work_id) if isinstance(items, dict) else None
    commands = step_entry.get("commands") if isinstance(step_entry, dict) else []
    note = step_entry.get("note") if isinstance(step_entry, dict) else ""
    commands_list = [str(c).strip() for c in commands] if isinstance(commands, list) else []

    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "id": "usage_has_m27_gate_section",
            "ok": has_all(
                usage_text,
                [
                    "Run M27 cloud version-control and release workflow gate (PRG-266):",
                    "make m27-cloud-workflow-check",
                ],
            ),
            "detail": "USAGE.md includes M27 gate command section",
        }
    )
    checks.append(
        {
            "id": "usage_has_branch_pr_protocol",
            "ok": has_all(
                usage_text,
                [
                    "git checkout -b codex/",
                    "gh pr create",
                    "gh pr merge --squash --delete-branch",
                ],
            ),
            "detail": "USAGE.md includes deterministic branch + PR workflow commands",
        }
    )
    checks.append(
        {
            "id": "usage_has_release_protocol",
            "ok": has_all(
                usage_text,
                [
                    "REL_TAG=",
                    "git tag -a",
                    "gh release create",
                    "out/m27_cloud_workflow_report.json",
                ],
            ),
            "detail": "USAGE.md includes deterministic tag + release protocol and report artifact",
        }
    )
    checks.append(
        {
            "id": "submission_has_m27_cloud_workflow",
            "ok": has_all(
                submission_text,
                [
                    "M27-K2",
                    "make m27-cloud-workflow-check",
                    "gh pr create",
                    "gh release create",
                    "out/m27_cloud_workflow_report.json",
                ],
            ),
            "detail": "SUBMISSION.md includes evaluator-facing M27 cloud workflow protocol",
        }
    )
    checks.append(
        {
            "id": "step_map_has_required_work_id",
            "ok": isinstance(step_entry, dict),
            "detail": f"step_execution_map has entry for {args.required_work_id}",
        }
    )
    checks.append(
        {
            "id": "step_map_wires_required_target",
            "ok": any(args.required_ci_target in cmd for cmd in commands_list),
            "detail": f"{args.required_work_id}.commands={commands_list}",
        }
    )
    checks.append(
        {
            "id": "step_map_mentions_next_work",
            "ok": str(args.required_next_work_id).strip() in str(note),
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
            "id": "make_ci_wires_target",
            "ok": "ci:" in makefile_text and args.required_ci_target in makefile_text,
            "detail": f"Makefile ci target includes {args.required_ci_target}",
        }
    )

    ok = all(bool(c.get("ok")) for c in checks)
    payload = {
        "label": "m27-cloud-workflow-live",
        "ok": ok,
        "checks": checks,
        "summary": {
            "checkCount": len(checks),
            "passCount": sum(1 for c in checks if c.get("ok")),
            "failedIds": [str(c.get("id")) for c in checks if not c.get("ok")],
            "requiredWorkId": args.required_work_id,
            "requiredNextWorkId": args.required_next_work_id,
            "requiredCiTarget": args.required_ci_target,
        },
    }
    write_json(Path(args.report_out), payload)
    if ok:
        print(
            "PASS: m27 cloud workflow check ("
            f"checks={payload['summary']['passCount']}/{payload['summary']['checkCount']}, "
            f"report={args.report_out})"
        )
        return 0
    print(
        "FAIL: m27 cloud workflow check ("
        f"failed={','.join(payload['summary']['failedIds'])}, "
        f"report={args.report_out})"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

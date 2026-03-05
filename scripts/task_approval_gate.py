#!/usr/bin/env python3
"""Automatic task approval gate.

Approves done work items when objective checks pass:
- milestone + KPI mapping resolves
- evidence path(s) exist
- active program gate passes
- for guardrail tasks, critical pipeline wiring exists
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_HEADERS = {
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


def load_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"failed to read JSON '{path}': {exc}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return obj


def load_work_items(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = set(reader.fieldnames or [])
        missing = REQUIRED_HEADERS - headers
        if missing:
            raise RuntimeError(f"missing work_items headers: {', '.join(sorted(missing))}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {k: (v or "").strip() for k, v in raw.items()}
            if all(not v for v in row.values()):
                continue
            rows.append(row)
    return rows


def split_evidence(value: str) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.split("|") if p.strip()]


def path_exists(repo_root: Path, rel: str) -> bool:
    return (repo_root / rel).exists()


def verify_critical_wiring(repo_root: Path) -> tuple[bool, str]:
    makefile = repo_root / "Makefile"
    if not makefile.exists():
        return False, "Makefile missing"
    text = makefile.read_text(encoding="utf-8")
    if "ci: program-check" not in text:
        return False, "Makefile ci target missing program-check wiring"
    if "program-check:" not in text:
        return False, "Makefile missing program-check target"
    return True, "ok"


def run_program_gate(repo_root: Path, plan: Path, work: Path) -> tuple[bool, str]:
    cmd = [
        "python3",
        "scripts/program_gate.py",
        "--plan",
        str(plan),
        "--work",
        str(work),
    ]
    p = subprocess.run(
        cmd,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    out = (p.stdout or "").strip()
    if p.returncode != 0:
        return False, out
    return True, out


def build_kpi_map(plan: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in plan.get("milestones", []):
        if not isinstance(m, dict):
            continue
        mid = str(m.get("id", "")).strip()
        for k in m.get("kpis", []):
            if not isinstance(k, dict):
                continue
            kid = str(k.get("id", "")).strip()
            if kid:
                out[kid] = mid
    return out


def evaluate_done_item(
    row: dict[str, str],
    repo_root: Path,
    kpi_map: dict[str, str],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    item_id = row.get("id", "")
    mid = row.get("milestone_id", "")
    kid = row.get("kpi_id", "")

    if not item_id:
        reasons.append("missing id")
    if not mid:
        reasons.append("missing milestone_id")
    if not kid:
        reasons.append("missing kpi_id")
    if kid and kid not in kpi_map:
        reasons.append(f"unknown KPI '{kid}'")
    elif kid and mid and kpi_map.get(kid) != mid:
        reasons.append(f"KPI '{kid}' belongs to milestone '{kpi_map.get(kid)}', not '{mid}'")

    evidence = split_evidence(row.get("evidence", ""))
    if not evidence:
        reasons.append("missing evidence")
    else:
        for ev in evidence:
            if not path_exists(repo_root, ev):
                reasons.append(f"evidence missing: {ev}")

    # Guardrail-specific mandatory wiring check for PRG-003.
    if item_id == "PRG-003":
        ok, msg = verify_critical_wiring(repo_root)
        if not ok:
            reasons.append(msg)

    return len(reasons) == 0, reasons


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Automatic task approval gate.")
    ap.add_argument("--plan", default="analysis/program/plan.json", help="program plan JSON")
    ap.add_argument("--work", default="analysis/program/work_items.csv", help="work item CSV")
    ap.add_argument(
        "--report",
        default="analysis/program/approval_report.json",
        help="output approval report JSON",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(".").resolve()
    plan_path = (repo_root / args.plan).resolve()
    work_path = (repo_root / args.work).resolve()
    report_path = (repo_root / args.report).resolve()

    if not plan_path.exists():
        print(f"FAIL: plan file missing: {plan_path}")
        return 2
    if not work_path.exists():
        print(f"FAIL: work item file missing: {work_path}")
        return 2

    try:
        plan = load_json(plan_path)
        rows = load_work_items(work_path)
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 2

    kpi_map = build_kpi_map(plan)

    gate_ok, gate_msg = run_program_gate(repo_root, Path(args.plan), Path(args.work))
    approvals: list[dict[str, Any]] = []
    failures: list[str] = []

    for row in rows:
        if row.get("status") != "done":
            continue
        ok, reasons = evaluate_done_item(row, repo_root, kpi_map)
        approvals.append(
            {
                "id": row.get("id", ""),
                "title": row.get("title", ""),
                "approved": bool(ok and gate_ok),
                "reasons": reasons if reasons else [],
            }
        )
        if not ok:
            failures.append(f"{row.get('id','(no-id)')}: " + "; ".join(reasons))

    if not gate_ok:
        failures.append("program_gate failed: " + gate_msg)

    approved_count = sum(1 for a in approvals if a["approved"])
    total_done = len(approvals)
    denied = total_done - approved_count

    payload = {
        "plan": str(Path(args.plan)),
        "workItems": str(Path(args.work)),
        "programGate": {"ok": gate_ok, "message": gate_msg},
        "totalDone": total_done,
        "approved": approved_count,
        "denied": denied,
        "approvals": approvals,
        "failures": failures,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    for a in approvals:
        label = "APPROVED" if a["approved"] else "DENIED"
        print(f"{label} {a['id']} - {a['title']}")
        if not a["approved"]:
            for r in a["reasons"]:
                print(f"  - {r}")
    if not gate_ok:
        print("DENIED program-gate")
        print("  - " + gate_msg)

    if failures:
        print(f"Summary: FAIL approved={approved_count}/{total_done} report={report_path}")
        return 1
    print(f"Summary: PASS approved={approved_count}/{total_done} report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json, math, re
from pathlib import Path

LLM_DIR = Path("analysis/out/llm")
OUT = Path("analysis/out/geometry/invariants_report.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def has_rel(d, rel):
    rel = norm(rel)
    return any(norm(r.get("relation","")) == rel for r in d.get("inferred_relations", []))

def get_rels(d, rel):
    rel = norm(rel)
    return [r for r in d.get("inferred_relations", []) if norm(r.get("relation","")) == rel]

def classify(d):
    f = norm(d.get("initial_formation",""))
    if "two lines" in f or "two line" in f:
        return "two_lines"
    if "circle" in f and "couple" in f:
        return "couples_circle"
    if "circle" in f:
        return "circle"
    if "couple" in f:
        return "couple"
    if "line" in f:
        return "line"
    return "unknown"

def count_ranges(steps):
    out = []
    for s in steps:
        out.append((s.get("part",""), s.get("count_range",""), s.get("action_type",""), norm(s.get("direction",""))))
    return out

def check_circle(d):
    issues = []
    steps = d["steps"]
    dirs = " ".join(norm(s.get("direction","")) for s in steps)
    if "ccw" in dirs or "counterclockwise" in dirs or "left" in dirs:
        pass
    else:
        issues.append("circle: no explicit ccw/left travel detected in step directions (may be fine, but check extraction).")

    if has_rel(d, "travel") or has_rel(d, "travel_direction"):
        pass
    if has_rel(d, "unison"):
        pass
    if has_rel(d, "facing_change") and not any("face" in norm(s.get("action_type","")) or "face" in norm(s.get("notes","")) for s in steps):
        issues.append("circle: inferred facing_change but no step explicitly mentions face/turn in action_type/notes; verify.")

    return issues

def check_two_lines(d):
    issues = []
    if not has_rel(d, "facing_lines"):
        issues.append("two_lines: missing facing_lines relation.")
    if not has_rel(d, "approach_and_retreat"):
        issues.append("two_lines: missing approach_and_retreat relation.")
    if not has_rel(d, "handhold_within_line"):
        issues.append("two_lines: missing handhold_within_line relation.")
    return issues

def check_line(d):
    issues = []
    if not has_rel(d, "hold"):
        issues.append("line: missing hold relation (may be ok if no hold mentioned).")
    if has_rel(d, "travel_direction") or has_rel(d, "travel_path"):
        pass
    else:
        issues.append("line: missing travel_direction/travel_path; might reduce geometric interpretability.")
    return issues

def check_couple(d):
    issues = []
    if not has_rel(d, "partners_side_by_side"):
        issues.append("couple: missing partners_side_by_side relation.")
    return issues

def run():
    lines = []
    for p in sorted(LLM_DIR.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        kind = classify(d)
        issues = []
        if kind == "circle":
            issues = check_circle(d)
        elif kind == "two_lines":
            issues = check_two_lines(d)
        elif kind == "line":
            issues = check_line(d)
        elif kind in ["couple", "couples_circle"]:
            issues = check_couple(d)

        lines.append(f"== {d['dance_id']} ({kind}) ==")
        lines.append(f"formation: {d.get('initial_formation','')}")
        lines.append(f"coord: {d.get('coordinate_convention','')[:140]}")
        lines.append("relations: " + ", ".join(sorted({norm(r.get('relation','')) for r in d.get('inferred_relations', [])})))
        lines.append("steps_head:")
        for a,b,c,dirn in count_ranges(d["steps"][:6]):
            lines.append(f"  - {a} {b} {c} | {dirn}")
        if issues:
            lines.append("issues:")
            for x in issues:
                lines.append(f"  - {x}")
        else:
            lines.append("issues: none (v0 checks passed)")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", OUT)

run()

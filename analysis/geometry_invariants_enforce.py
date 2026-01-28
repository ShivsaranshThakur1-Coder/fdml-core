import csv, json, re
from pathlib import Path

METRICS = Path("analysis/out/geometry/metrics.csv")
LLM_DIR = Path("analysis/out/llm")

def norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())

def relset(d):
    return {norm(r.get("relation","")) for r in d.get("inferred_relations", [])}

rows = list(csv.DictReader(METRICS.open(encoding="utf-8")))
by_id = {r["dance_id"]: r for r in rows}

def fnum(x):
    try:
        return float(x)
    except:
        return None

def check(dance_id):
    path = LLM_DIR / f"{dance_id}.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    rels = relset(d)
    m = by_id.get(dance_id, {})
    kind = m.get("kind","")

    fails = []

    if kind == "circle":
        mad = fnum(m.get("mean_angle_delta"))
        rmin = fnum(m.get("min_radius_min"))
        if ("travel" in rels or "travel_direction" in rels) and mad is not None:
            if mad <= 0.05:
                fails.append(f"Expected CCW travel to produce positive mean_angle_delta, got {mad}")
        if any(x in rels for x in ["facing_change","formation"]):
            pass
        if rmin is not None:
            if rmin < 0.6:
                fails.append(f"Radius collapsed too far (min_radius_min={rmin}); likely bad mapping.")

    if kind == "two_lines":
        smin = fnum(m.get("line_sep_min"))
        smax = fnum(m.get("line_sep_max"))
        if "approach_and_retreat" in rels and smin is not None and smax is not None:
            if not (smin < smax - 0.3):
                fails.append(f"Expected separation dip for approach/retreat, got min={smin}, max={smax}")

    if kind == "line":
        mx = fnum(m.get("mean_x_delta"))
        if "travel_direction" in rels and mx is not None:
            if abs(mx) < 0.05:
                fails.append(f"Expected lateral travel (mean_x_delta), got {mx}")

    status = "PASS" if not fails else "FAIL"
    return status, fails, rels, kind

for did in ["aalistullaa","abdala","cobankat","haire-mamougeh","mayim-mayim"]:
    status, fails, rels, kind = check(did)
    print(f"{did}: {status} ({kind})")
    if fails:
        for f in fails:
            print("  -", f)

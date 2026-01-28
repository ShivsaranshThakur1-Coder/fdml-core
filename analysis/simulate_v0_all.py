import json, math, csv, re
from pathlib import Path

LLM_DIR = Path("analysis/out/llm")
OUT_DIR = Path("analysis/out/geometry")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def parse_counts(s):
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", s)
    if not m:
        return 4
    a, b = int(m.group(1)), int(m.group(2))
    return max(1, b - a + 1)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def circular_order(angles):
    idx = sorted(range(len(angles)), key=lambda i: angles[i] % (2*math.pi))
    return idx

def line_order(xs):
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    return idx

def inversions(order0, order1):
    pos0 = {v:i for i,v in enumerate(order0)}
    seq = [pos0[v] for v in order1]
    inv = 0
    for i in range(len(seq)):
        for j in range(i+1, len(seq)):
            if seq[i] > seq[j]:
                inv += 1
    return inv

def mean_std(vals):
    if not vals:
        return (0.0, 0.0)
    m = sum(vals)/len(vals)
    v = sum((x-m)**2 for x in vals)/len(vals)
    return (m, math.sqrt(v))

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def make_state_circle(n):
    R = 1.0
    angles = [2*math.pi*i/n for i in range(n)]
    radii = [R]*n
    heading = [math.pi/2]*n
    return {"kind":"circle","n":n,"angles":angles,"radii":radii,"heading":heading}

def make_state_line(n):
    xs = [i-(n-1)/2 for i in range(n)]
    ys = [0.0]*n
    heading = [0.0]*n
    return {"kind":"line","n":n,"xs":xs,"ys":ys,"heading":heading}

def make_state_two_lines(n_per):
    n = 2*n_per
    xs = [i-(n_per-1)/2 for i in range(n_per)] + [i-(n_per-1)/2 for i in range(n_per)]
    ys = [-1.0]*n_per + [1.0]*n_per
    heading = [math.pi/2]*n_per + [-math.pi/2]*n_per
    return {"kind":"two_lines","n":n,"n_per":n_per,"xs":xs,"ys":ys,"heading":heading}

def make_state_couples(n_couples):
    n = 2*n_couples
    angles = [2*math.pi*i/n_couples for i in range(n_couples)]
    radii = [1.0]*n
    theta = []
    for a in angles:
        theta.append(a)
        theta.append(a)
    offset = 0.08
    off = []
    for i in range(n):
        off.append(-offset if i%2==0 else offset)
    return {"kind":"couples_circle","n":n,"n_couples":n_couples,"theta":theta,"radii":radii,"off":off,"heading":[math.pi/2]*n}

def pos(state, i):
    k = state["kind"]
    if k == "circle":
        a = state["angles"][i]
        r = state["radii"][i]
        return (r*math.cos(a), r*math.sin(a))
    if k in ["line","two_lines"]:
        return (state["xs"][i], state["ys"][i])
    if k == "couples_circle":
        a = state["theta"][i]
        r = state["radii"][i]
        x = r*math.cos(a)
        y = r*math.sin(a)
        nx = -math.sin(a)
        ny = math.cos(a)
        return (x + state["off"][i]*nx, y + state["off"][i]*ny)
    raise RuntimeError("unknown kind")

def apply_to_indices(actors, state):
    n = state["n"]
    a = " ".join([str(x).lower() for x in actors]) if actors else "all"
    if "all" in a:
        return list(range(n))
    if state["kind"] == "two_lines":
        n_per = state["n_per"]
        if "bride" in a or "line1" in a or "family1" in a:
            return list(range(0, n_per))
        if "groom" in a or "line2" in a or "family2" in a:
            return list(range(n_per, 2*n_per))
    return list(range(n))

def step_magnitude(action_type, counts):
    t = (action_type or "").lower()
    base = 1.0
    if "run" in t:
        base = 1.3
    elif "walk" in t:
        base = 0.9
    elif "hop" in t:
        base = 0.6
    elif "grapevine" in t:
        base = 1.0
    elif "repeat" in t:
        base = 0.8
    return base * (counts/4.0)

def apply_step(state, step):
    counts = parse_counts(step.get("count_range",""))
    mag = step_magnitude(step.get("action_type",""), counts)
    dirn = (step.get("direction") or "").lower()
    idxs = apply_to_indices(step.get("actors",["all"]), state)
    k = state["kind"]

    rot = 0.0
    if "clockwise" in dirn or " cw" in f" {dirn} ":
        rot -= 0.10*mag
    if "counterclockwise" in dirn or "anticlockwise" in dirn or " ccw" in f" {dirn} " or "left" in dirn:
        rot += 0.10*mag
    if "turn" in (step.get("action_type") or "").lower():
        rot += 0.20*mag

    fwd = 0.0
    if "forward" in dirn or "fwd" in dirn or "twd" in dirn:
        fwd += 0.12*mag
    if "backward" in dirn or "bkwd" in dirn or "away" in dirn:
        fwd -= 0.12*mag

    side = 0.0
    if " right" in f" {dirn} " or "to r" in dirn:
        side += 0.10*mag
    if " left" in f" {dirn} " or "to l" in dirn:
        side -= 0.10*mag

    if k == "circle":
        for i in idxs:
            state["angles"][i] += rot
            state["radii"][i] = clamp(state["radii"][i] - fwd, 0.3, 2.0)
    elif k == "line":
        for i in idxs:
            state["xs"][i] += side
            state["ys"][i] += fwd
            state["heading"][i] += rot
    elif k == "two_lines":
        for i in idxs:
            state["xs"][i] += side
            state["ys"][i] += fwd
            state["heading"][i] += rot
    elif k == "couples_circle":
        for i in idxs:
            state["theta"][i] += rot
            state["radii"][i] = clamp(state["radii"][i] - fwd, 0.3, 2.0)
    return state

def partner_pairs(n):
    pairs = []
    for i in range(0, n-1, 2):
        pairs.append((i, i+1))
    return pairs

def opposite_pairs_circle(n):
    if n % 2 != 0:
        return []
    pairs = []
    for i in range(n//2):
        pairs.append((i, i+n//2))
    return pairs

def summarize(dance_id, data):
    form = (data.get("initial_formation") or "").lower()
    if "two line" in form or "two lines" in form:
        state = make_state_two_lines(5)
    elif "circle" in form:
        if "couple" in form or "cpl" in form:
            state = make_state_couples(5)
        else:
            state = make_state_circle(8)
    elif "couple" in form:
        state = make_state_couples(5)
    else:
        state = make_state_line(8)

    n = state["n"]
    if state["kind"] in ["circle","couples_circle"]:
        order0 = circular_order(state.get("angles", state.get("theta")))
    else:
        order0 = line_order(state["xs"])

    per_step = []
    for s in data["steps"]:
        state = apply_step(state, s)
        pts = [pos(state, i) for i in range(n)]
        mind = min(dist(pts[i], pts[j]) for i in range(n) for j in range(i+1,n))
        per_step.append({"part":s["part"],"count_range":s["count_range"],"action_type":s["action_type"],"min_distance":mind})

    pts_final = [pos(state, i) for i in range(n)]
    if state["kind"] in ["circle","couples_circle"]:
        order1 = circular_order(state.get("angles", state.get("theta")))
    else:
        order1 = line_order(state["xs"])

    inv = inversions(order0, order1)

    pdists = [dist(pts_final[a], pts_final[b]) for a,b in partner_pairs(n)]
    pmean, pstd = mean_std(pdists)

    odists = []
    if state["kind"] in ["circle","couples_circle"]:
        odists = [dist(pts_final[a], pts_final[b]) for a,b in opposite_pairs_circle(n)]
    omean, ostd = mean_std(odists)

    mind_final = min(dist(pts_final[i], pts_final[j]) for i in range(n) for j in range(i+1,n))

    return {
        "dance_id": dance_id,
        "formation": data.get("initial_formation",""),
        "coord": data.get("coordinate_convention",""),
        "sim_kind": state["kind"],
        "n_dancers_assumed": n,
        "order_inversions": inv,
        "partner_dist_mean": pmean,
        "partner_dist_std": pstd,
        "opposite_dist_mean": omean,
        "opposite_dist_std": ostd,
        "min_distance_final": mind_final,
        "per_step": per_step,
    }

summaries = []
for p in sorted(LLM_DIR.glob("*.json")):
    data = json.loads(p.read_text(encoding="utf-8"))
    s = summarize(p.stem, data)
    (OUT_DIR / f"{p.stem}_sim.json").write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summaries.append(s)

out_csv = OUT_DIR / "summary.csv"
cols = ["dance_id","sim_kind","n_dancers_assumed","order_inversions","partner_dist_mean","partner_dist_std","opposite_dist_mean","opposite_dist_std","min_distance_final"]
with out_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for s in summaries:
        w.writerow({k:s.get(k,"") for k in cols})

print("Wrote", out_csv)
for s in summaries:
    print(s["dance_id"], s["sim_kind"], "inv=", s["order_inversions"], "partner_mean=", round(s["partner_dist_mean"],3), "minD=", round(s["min_distance_final"],3))

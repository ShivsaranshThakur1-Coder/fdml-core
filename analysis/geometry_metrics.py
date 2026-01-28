import json, math, re, csv
from pathlib import Path

LLM_DIR = Path("analysis/out/llm")
OUT = Path("analysis/out/geometry/metrics.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())
def parse_counts(s):
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", s)
    if not m: return 4
    a,b=int(m.group(1)),int(m.group(2))
    return max(1,b-a+1)

def simulate_kind(form):
    f = norm(form)
    if "two lines" in f or "two line" in f: return "two_lines"
    if "circle" in f and "couple" in f: return "couples_circle"
    if "circle" in f: return "circle"
    if "couple" in f: return "couple"
    if "line" in f: return "line"
    return "unknown"

def run_circle(d):
    n=8
    ang=[2*math.pi*i/n for i in range(n)]
    r=[1.0]*n
    def rot(delta):
        for i in range(n): ang[i]+=delta
    def radial(delta):
        for i in range(n): r[i]=max(0.3,min(2.0,r[i]+delta))
    a0=sum(ang)/n
    min_r=[]
    for s in d["steps"]:
        counts=parse_counts(s.get("count_range",""))
        mag=counts/4.0
        dirn=norm(s.get("direction",""))
        if "left" in dirn or "ccw" in dirn or "counterclockwise" in dirn: rot(+0.10*mag)
        if "right" in dirn or "cw" in dirn or "clockwise" in dirn: rot(-0.10*mag)
        if "forward" in dirn: radial(-0.05*mag)
        if "backward" in dirn: radial(+0.05*mag)
        min_r.append(min(r))
    a1=sum(ang)/n
    return {"mean_angle_delta": a1-a0, "min_radius_min": min(min_r) if min_r else 0.0, "min_radius_max": max(min_r) if min_r else 0.0}

def run_two_lines(d):
    n_per=5
    xs=[i-(n_per-1)/2 for i in range(n_per)] + [i-(n_per-1)/2 for i in range(n_per)]
    ys=[-1.0]*n_per + [1.0]*n_per
    def step_line(idxs, dy, dx):
        for i in idxs:
            ys[i]+=dy
            xs[i]+=dx
    sep=[]
    for s in d["steps"]:
        counts=parse_counts(s.get("count_range",""))
        mag=counts/4.0
        dirn=norm(s.get("direction",""))
        dy=0.0; dx=0.0
        if "forward" in dirn or "twd" in dirn: dy+=0.12*mag
        if "backward" in dirn or "bkwd" in dirn or "away" in dirn: dy-=0.12*mag
        if " right" in f" {dirn} " or "to r" in dirn: dx+=0.08*mag
        if " left" in f" {dirn} " or "to l" in dirn: dx-=0.08*mag
        step_line(range(0,n_per), dy, dx)
        step_line(range(n_per,2*n_per), -dy, dx)
        y1=sum(ys[:n_per])/n_per
        y2=sum(ys[n_per:])/n_per
        sep.append(abs(y2-y1))
    return {"line_sep_min": min(sep) if sep else 0.0, "line_sep_max": max(sep) if sep else 0.0}

def run_line(d):
    n=8
    xs=[i-(n-1)/2 for i in range(n)]
    ys=[0.0]*n
    x0=sum(xs)/n
    for s in d["steps"]:
        counts=parse_counts(s.get("count_range",""))
        mag=counts/4.0
        dirn=norm(s.get("direction",""))
        dx=0.0; dy=0.0
        if "to the right" in dirn or "clockwise" in dirn or "to r" in dirn: dx+=0.10*mag
        if "to the left" in dirn or "counterclockwise" in dirn or "to l" in dirn: dx-=0.10*mag
        if "forward" in dirn: dy+=0.08*mag
        if "backward" in dirn: dy-=0.08*mag
        for i in range(n):
            xs[i]+=dx
            ys[i]+=dy
    x1=sum(xs)/n
    return {"mean_x_delta": x1-x0}

def run():
    rows=[]
    for p in sorted(LLM_DIR.glob("*.json")):
        d=json.loads(p.read_text(encoding="utf-8"))
        kind=simulate_kind(d.get("initial_formation",""))
        m={"dance_id": d["dance_id"], "kind": kind}
        if kind=="circle":
            m.update(run_circle(d))
        elif kind=="two_lines":
            m.update(run_two_lines(d))
        elif kind=="line":
            m.update(run_line(d))
        else:
            m.update({})
        rows.append(m)

    cols=sorted({k for r in rows for k in r.keys()})
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("Wrote", OUT)

run()

import json, math
from pathlib import Path

d = json.loads(Path("analysis/out/llm_mayim.json").read_text(encoding="utf-8"))

N = 8
names = [f"D{i+1}" for i in range(N)]
R = 1.0
angles = [2*math.pi*i/N for i in range(N)]
radii = [R]*N

def pos(i):
    return (radii[i]*math.cos(angles[i]), radii[i]*math.sin(angles[i]))

def rotate_all(delta):
    for i in range(N):
        angles[i] += delta

def radial_all(delta):
    for i in range(N):
        radii[i] = max(0.2, radii[i] + delta)

def step_apply(step):
    t = (step.get("action_type") or "").lower()
    dirn = (step.get("direction") or "").lower()
    if t in ["grapevine","run","walk/run","walk","repeat"]:
        if "left" in dirn or "counterclockwise" in dirn:
            rotate_all(+math.pi/12)
        if "right" in dirn or "clockwise" in dirn:
            rotate_all(-math.pi/12)
        if "forward" in dirn:
            radial_all(-0.05)
        if "backward" in dirn:
            radial_all(+0.05)

print("Initial positions:")
for i,n in enumerate(names):
    x,y = pos(i)
    print(n, f"{x:.3f}", f"{y:.3f}")

for idx, step in enumerate(d["steps"], 1):
    step_apply(step)
    if idx in [1,3,4,5,10]:
        print("\nAfter step", idx, step["part"], step["count_range"], step["action_type"])
        for i,n in enumerate(names[:4]):
            x,y = pos(i)
            print(n, f"{x:.3f}", f"{y:.3f}")

print("\nDone (v0).")

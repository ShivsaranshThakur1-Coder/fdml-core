import json
from pathlib import Path

OUTDIR = Path("analysis/out/llm")

def check(d, path):
    req_top = ["dance_id","initial_formation","coordinate_convention","steps","inferred_relations"]
    for k in req_top:
        if k not in d:
            raise AssertionError(f"{path}: missing top key {k}")
    if not isinstance(d["steps"], list) or not d["steps"]:
        raise AssertionError(f"{path}: steps empty")
    for i,s in enumerate(d["steps"]):
        for k in ["part","count_range","action_type","actors"]:
            if k not in s:
                raise AssertionError(f"{path}: step {i} missing {k}")
        if not isinstance(s["actors"], list) or not s["actors"]:
            raise AssertionError(f"{path}: step {i} actors empty")
    if not isinstance(d["inferred_relations"], list):
        raise AssertionError(f"{path}: inferred_relations not list")
    for i,r in enumerate(d["inferred_relations"]):
        for k in ["relation","between"]:
            if k not in r:
                raise AssertionError(f"{path}: relation {i} missing {k}")
        if not isinstance(r["between"], list) or not r["between"]:
            raise AssertionError(f"{path}: relation {i} between empty")

files = sorted(OUTDIR.glob("*.json"))
print("files:", len(files))
for p in files:
    d = json.loads(p.read_text(encoding="utf-8"))
    check(d, p)
print("OK: all passed")

import json
from pathlib import Path

p = Path("analysis/out/llm_mayim.json")
d = json.loads(p.read_text(encoding="utf-8"))

req_top = ["dance_id","initial_formation","coordinate_convention","steps","inferred_relations"]
for k in req_top:
    assert k in d, f"missing top key: {k}"

assert isinstance(d["steps"], list) and d["steps"], "steps must be non-empty list"
for i,s in enumerate(d["steps"]):
    for k in ["part","count_range","action_type","actors"]:
        assert k in s, f"step {i} missing {k}"
    assert isinstance(s["actors"], list) and s["actors"], f"step {i} actors must be non-empty list"

assert isinstance(d["inferred_relations"], list), "inferred_relations must be list"
for i,r in enumerate(d["inferred_relations"]):
    for k in ["relation","between"]:
        assert k in r, f"relation {i} missing {k}"
    assert isinstance(r["between"], list) and r["between"], f"relation {i} between must be non-empty list"

print("OK: schema shape looks good")
print("dance_id:", d["dance_id"])
print("steps:", len(d["steps"]))
print("relations:", len(d["inferred_relations"]))

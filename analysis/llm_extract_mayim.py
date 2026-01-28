import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

ROOT = Path("/Users/shivsaranshthakur/Projects/fdml-core")
INP = ROOT / "analysis" / "out" / "training_set.jsonl"
OUT = ROOT / "analysis" / "out" / "llm_mayim.json"

class Step(BaseModel):
    part: str
    count_range: str
    action_type: str
    actors: List[str]
    direction: Optional[str] = ""
    amount: Optional[str] = ""
    notes: Optional[str] = ""

class Relation(BaseModel):
    relation: str
    between: List[str]
    notes: Optional[str] = ""

class DancePrimitives(BaseModel):
    dance_id: str
    initial_formation: str
    coordinate_convention: str
    steps: List[Step]
    inferred_relations: List[Relation]

def to_plain(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj

client = OpenAI()

rec = None
for line in INP.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r.get("dance_id") == "mayim-mayim":
        rec = r
        break
assert rec is not None

prompt = f"""
Convert the dance description into structured movement primitives.

Dance ID: {rec["dance_id"]}
FDML formations: {rec["fdml_formations"]}
FDML meter: {rec["fdml_meter"]}
FDML tempo bpm: {rec["fdml_tempo_bpm"]}

Return a JSON object matching the schema exactly.

Source text:
{rec["source_text"]}
""".strip()

resp = client.responses.parse(
    model="gpt-5.2",
    input=[{"role":"user","content":prompt}],
    text_format=DancePrimitives,
)

parsed = resp.output_parsed
data = to_plain(parsed)

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Wrote", OUT)
print(data["dance_id"], len(data["steps"]), len(data["inferred_relations"]))
print(data["steps"][:5])

import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

ROOT = Path("/Users/shivsaranshthakur/Projects/fdml-core")
INP = ROOT / "analysis" / "out" / "training_set.jsonl"
OUTDIR = ROOT / "analysis" / "out" / "llm"

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

target = "mayim-mayim"
rec = None
for line in INP.read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    if r.get("dance_id") == target:
        rec = r
        break
assert rec is not None

prompt = f"""
Convert the dance description into structured movement primitives.

Hard requirement:
If the dance includes any facing/orientation change (e.g., "face center", "turn to face ..."),
you MUST include at least one explicit step with action_type = "face" or "turn" and notes containing the exact phrase (e.g., "face center").
Do not encode facing changes only as inferred_relations.

Dance ID: {rec["dance_id"]}
FDML formations: {rec["fdml_formations"]}
FDML meter: {rec["fdml_meter"]}
FDML tempo bpm: {rec["fdml_tempo_bpm"]}

Return JSON matching the schema exactly.

Source text:
{rec["source_text"]}
""".strip()

resp = client.responses.parse(
    model="gpt-5.2",
    input=[{"role":"user","content":prompt}],
    text_format=DancePrimitives,
)

data = to_plain(resp.output_parsed)
OUTDIR.mkdir(parents=True, exist_ok=True)
out_path = OUTDIR / f"{target}.json"
out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Wrote", out_path)

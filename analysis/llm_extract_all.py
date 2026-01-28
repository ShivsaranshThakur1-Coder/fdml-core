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

recs = [json.loads(line) for line in INP.read_text(encoding="utf-8").splitlines()]
OUTDIR.mkdir(parents=True, exist_ok=True)

for rec in recs:
    dance_id = rec["dance_id"]
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

    data = to_plain(resp.output_parsed)
    out_path = OUTDIR / f"{dance_id}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote", out_path, "steps=", len(data["steps"]), "rels=", len(data["inferred_relations"]))

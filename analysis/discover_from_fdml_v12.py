import json
from pathlib import Path
from collections import Counter
from typing import List, Literal
from pydantic import BaseModel
from openai import OpenAI

SRC_DIR = Path("analysis/out/fdml_v12_text")
OUT_DIR = Path("analysis/out/discovery_fdml_v12/per_file")
OUT_SUM = Path("analysis/out/discovery_fdml_v12")
OUT_SUM.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

BestBy = Literal["xsd","schematron","java","manual"]
InvCat = Literal["geometry","timing","formation","structure","safety"]
VarType = Literal["discrete","continuous","graph","set","string","boolean","enum"]

class Primitive(BaseModel):
    name: str
    parameters: List[str]
    confidence: float
    evidence: str

class Invariant(BaseModel):
    name: str
    category: InvCat
    description: str
    requires_state: List[str]
    best_enforced_by: BestBy
    confidence: float
    evidence: str

class StateVar(BaseModel):
    name: str
    var_type: VarType
    description: str
    confidence: float
    evidence: str

class Discovery(BaseModel):
    source_file: str
    primitives: List[Primitive]
    invariants: List[Invariant]
    state_vars: List[StateVar]

def clean_text(s: str, max_chars: int = 14000) -> str:
    s = s.replace("\r\n","\n").replace("\r","\n").strip()
    return s[:max_chars]

client = OpenAI()
files = sorted(SRC_DIR.glob("*.txt"))
print("files_to_process:", len(files))

prim = Counter()
inv = Counter()
sv  = Counter()

for f in files:
    text = clean_text(f.read_text(encoding="utf-8", errors="ignore"))
    prompt = f"""
You are inducing a reusable ontology from an FDML v1.2 document summary with geo primitives.

Return JSON matching the schema exactly.

Rules:
- Primitives: output only reusable movement/formation primitives that appear in the geo primitives or step actions (e.g., move, face, turn, approach, retreat, swapPlaces, twirl, hold types).
- Invariants: output only checkable invariants that can be enforced by XSD, Schematron, or Java.
- Prefer invariants that generalize across many dances (not per-dance idiosyncrasies).
- Evidence must quote exact lines from the input.
- confidence 0..1.

source_file: {f.name}

FDML SUMMARY:
{text}
""".strip()

    resp = client.responses.parse(
        model="gpt-5.2",
        input=[{"role":"user","content":prompt}],
        text_format=Discovery,
    )

    obj = resp.output_parsed
    data = obj.dict() if hasattr(obj, "dict") else obj
    (OUT_DIR / f"{f.stem}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for p0 in data.get("primitives", []):
        name = (p0.get("name","") or "").strip().lower()
        if name: prim[name] += 1

    for i0 in data.get("invariants", []):
        name = (i0.get("name","") or "").strip().lower()
        cat  = (i0.get("category","") or "").strip().lower()
        if name: inv[(cat,name)] += 1

    for s0 in data.get("state_vars", []):
        name = (s0.get("name","") or "").strip().lower()
        if name: sv[name] += 1

OUT_SUM.joinpath("primitives_top.json").write_text(json.dumps(prim.most_common(80), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("state_vars_top.json").write_text(json.dumps(sv.most_common(80), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("invariants_top.json").write_text(json.dumps(
    [{"category":c,"name":n,"count":k} for (c,n),k in inv.most_common(80)], indent=2
) + "\n", encoding="utf-8")

print("\nTOP PRIMITIVES:")
for n,k in prim.most_common(20):
    print("-", n, k)

print("\nTOP INVARIANTS:")
for (c,n),k in inv.most_common(25):
    print("-", c, n, k)

print("\nTOP STATE VARS:")
for n,k in sv.most_common(20):
    print("-", n, k)

print("\nWROTE:")
print("analysis/out/discovery_fdml_v12/primitives_top.json")
print("analysis/out/discovery_fdml_v12/invariants_top.json")
print("analysis/out/discovery_fdml_v12/state_vars_top.json")

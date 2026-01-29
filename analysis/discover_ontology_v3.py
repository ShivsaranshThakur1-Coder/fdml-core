import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Literal
from pydantic import BaseModel
from openai import OpenAI

SRC_DIR = Path("analysis/out/sources_text")
OUT_DIR = Path("analysis/out/discovery_v3/per_file")
OUT_SUM = Path("analysis/out/discovery_v3")
OUT_SUM.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

SKIP = {
    "EvansVilleFolkDance.txt",
    "SocalFolkDance.txt",
    "MayimMayim_textutil.txt",
}

class Primitive(BaseModel):
    name: str
    parameters: List[str]
    synonyms: List[str]
    confidence: float
    evidence: str

BestBy = Literal["xsd","schematron","java","manual"]
InvCat = Literal["geometry","timing","styling","formation","structure","music","safety"]

class Invariant(BaseModel):
    name: str
    category: InvCat
    description: str
    requires_state: List[str]
    best_enforced_by: BestBy
    confidence: float
    evidence: str

VarType = Literal["discrete","continuous","graph","set","string","boolean","enum"]

class StateVar(BaseModel):
    name: str
    var_type: VarType
    description: str
    confidence: float
    evidence: str

class Discovery(BaseModel):
    source_file: str
    movement_primitives: List[Primitive]
    formation_primitives: List[Primitive]
    timing_primitives: List[Primitive]
    styling_primitives: List[Primitive]
    invariants: List[Invariant]
    state_vars: List[StateVar]

def clean_text(s: str, max_chars: int = 12000) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.splitlines())
    s = s.strip()
    return s[:max_chars]

def pick_files():
    files = []
    for f in sorted(SRC_DIR.glob("*.txt")):
        if f.name in SKIP:
            continue
        if f.stat().st_size < 200:
            continue
        files.append(f)
    return files

client = OpenAI()

files = pick_files()
print("files_to_process:", [f.name for f in files])

for f in files:
    text = clean_text(f.read_text(encoding="utf-8", errors="ignore"))
    prompt = f"""
Induce a reusable ontology from this single dance description.

Return JSON matching the schema exactly.

Rules:
- Do NOT output metadata (title, meter, tempo, recording) as movement primitives.
- movement_primitives: actions that change position/heading/order/adjacency (e.g., step, travel, turn, swap, pass, circle).
- formation_primitives: formation/roles/holds/facing arrangements (e.g., circle, line, two lines, partner left/right, handhold type).
- timing_primitives: count structure, meter subdivision, phrase constraints (e.g., 9/16 grouped 1-2-3-A).
- styling_primitives: posture/bounce/arm-frame rules.
- Invariants must be generic + checkable.
- confidence is 0..1.
- evidence must quote a short excerpt from the text.

source_file: {f.name}

SOURCE TEXT:
{text}
""".strip()

    resp = client.responses.parse(
        model="gpt-5.2",
        input=[{"role":"user","content":prompt}],
        text_format=Discovery,
    )

    obj = resp.output_parsed
    data = obj.dict() if hasattr(obj, "dict") else obj
    out_path = OUT_DIR / f"{f.stem}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote:", out_path)

mov = Counter()
frm = Counter()
tim = Counter()
sty = Counter()
inv = Counter()
var = Counter()
enf = Counter()

for p in sorted(OUT_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))

    for x in d.get("movement_primitives", []):
        mov[x["name"].strip().lower()] += 1
    for x in d.get("formation_primitives", []):
        frm[x["name"].strip().lower()] += 1
    for x in d.get("timing_primitives", []):
        tim[x["name"].strip().lower()] += 1
    for x in d.get("styling_primitives", []):
        sty[x["name"].strip().lower()] += 1

    for x in d.get("invariants", []):
        inv[(x["category"], x["name"].strip().lower())] += 1
        enf[x["best_enforced_by"]] += 1

    for x in d.get("state_vars", []):
        var[x["name"].strip().lower()] += 1

OUT_SUM.joinpath("movement_top.json").write_text(json.dumps(mov.most_common(60), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("formation_top.json").write_text(json.dumps(frm.most_common(60), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("timing_top.json").write_text(json.dumps(tim.most_common(60), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("styling_top.json").write_text(json.dumps(sty.most_common(60), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("invariants_top.json").write_text(json.dumps(
    [{"category":c,"name":n,"count":k} for (c,n),k in inv.most_common(60)], indent=2
) + "\n", encoding="utf-8")
OUT_SUM.joinpath("state_vars_top.json").write_text(json.dumps(var.most_common(60), indent=2) + "\n", encoding="utf-8")
OUT_SUM.joinpath("enforcement_top.json").write_text(json.dumps(enf.most_common(20), indent=2) + "\n", encoding="utf-8")

print("\nTOP MOVEMENT PRIMITIVES:")
for n,k in mov.most_common(20):
    print("-", n, k)

print("\nTOP FORMATION PRIMITIVES:")
for n,k in frm.most_common(20):
    print("-", n, k)

print("\nTOP TIMING PRIMITIVES:")
for n,k in tim.most_common(20):
    print("-", n, k)

print("\nTOP STYLING PRIMITIVES:")
for n,k in sty.most_common(20):
    print("-", n, k)

print("\nTOP INVARIANTS:")
for (c,n),k in inv.most_common(20):
    print("-", c, n, k)

print("\nWROTE:")
print("analysis/out/discovery_v3/movement_top.json")
print("analysis/out/discovery_v3/formation_top.json")
print("analysis/out/discovery_v3/timing_top.json")
print("analysis/out/discovery_v3/styling_top.json")
print("analysis/out/discovery_v3/invariants_top.json")
print("analysis/out/discovery_v3/state_vars_top.json")
print("analysis/out/discovery_v3/enforcement_top.json")

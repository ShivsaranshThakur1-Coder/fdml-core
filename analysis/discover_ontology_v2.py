import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

SRC_DIR = Path("analysis/out/sources_text")
OUT_DIR = Path("analysis/out/discovery_v2/per_file")
OUT_SUM = Path("analysis/out/discovery_v2")
OUT_SUM.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

SKIP = {
    "EvansVilleFolkDance.txt",
    "SocalFolkDance.txt",
    "MayimMayim_textutil.txt",
}

class Primitive(BaseModel):
    name: str
    category: str
    parameters: List[str]
    synonyms: List[str]
    confidence: float
    evidence: str

class Invariant(BaseModel):
    name: str
    category: str
    description: str
    requires_state: List[str]
    best_enforced_by: str
    confidence: float
    evidence: str

class StateVar(BaseModel):
    name: str
    var_type: str
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
- Do NOT output metadata items (title, meter, tempo, formation) as movement primitives.
- Use categories:
  - movement_primitives: actions that change positions/headings/adjacency (e.g., step, turn, travel, swap).
  - formation_primitives: holds, lines/circle/couples, roles/inside-outside, facing arrangements.
  - timing_primitives: count structures, measure phrasing, meter subdivisions (e.g., 9/16 grouped).
  - styling_primitives: posture/arm position/bounce instructions.
- Invariants must be generic and checkable (avoid “measure 12 missing” unless it’s clearly a general rule pattern).
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

prim_counts = Counter()
inv_counts = Counter()
state_counts = Counter()
cat_counts = Counter()

def add_prims(lst):
    for pr in lst:
        name = (pr.get("name","") or "").strip().lower()
        cat = (pr.get("category","") or "").strip().lower()
        if name:
            prim_counts[(cat, name)] += 1
            cat_counts[cat] += 1

for p in sorted(OUT_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    add_prims(d.get("movement_primitives", []))
    add_prims(d.get("formation_primitives", []))
    add_prims(d.get("timing_primitives", []))
    add_prims(d.get("styling_primitives", []))
    for inv in d.get("invariants", []):
        name = (inv.get("name","") or "").strip().lower()
        if name:
            inv_counts[(inv.get("category","") or "").strip().lower(), name] += 1
    for sv in d.get("state_vars", []):
        name = (sv.get("name","") or "").strip().lower()
        if name:
            state_counts[name] += 1

(OUT_SUM / "primitives_top.json").write_text(json.dumps(
    [{"category":c,"name":n,"count":k} for (c,n),k in prim_counts.most_common(60)], indent=2
) + "\n", encoding="utf-8")

(OUT_SUM / "invariants_top.json").write_text(json.dumps(
    [{"category":c,"name":n,"count":k} for (c,n),k in inv_counts.most_common(60)], indent=2
) + "\n", encoding="utf-8")

(OUT_SUM / "state_vars_top.json").write_text(json.dumps(
    state_counts.most_common(60), indent=2
) + "\n", encoding="utf-8")

print("\nTOP MOVEMENT PRIMITIVES:")
for (cat,name),k in prim_counts.most_common(30):
    if cat=="movement":
        print("-", name, k)

print("\nTOP FORMATION PRIMITIVES:")
for (cat,name),k in prim_counts.most_common(30):
    if cat=="formation":
        print("-", name, k)

print("\nTOP INVARIANTS:")
for (cat,name),k in inv_counts.most_common(20):
    print("-", cat, name, k)

print("\nWROTE:")
print("analysis/out/discovery_v2/primitives_top.json")
print("analysis/out/discovery_v2/invariants_top.json")
print("analysis/out/discovery_v2/state_vars_top.json")

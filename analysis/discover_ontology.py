import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI

SRC_DIR = Path("analysis/out/sources_text")
OUT_DIR = Path("analysis/out/discovery/per_file")
OUT_SUM = Path("analysis/out/discovery")
OUT_SUM.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

class Primitive(BaseModel):
    name: str
    synonyms: List[str]
    parameters: List[str]
    evidence: str

class Invariant(BaseModel):
    name: str
    description: str
    requires_state: List[str]
    best_enforced_by: str
    evidence: str

class StateVar(BaseModel):
    name: str
    var_type: str
    description: str
    evidence: str

class Ambiguity(BaseModel):
    text_span: str
    reason: str
    missing_info: str

class Discovery(BaseModel):
    source_file: str
    primitives: List[Primitive]
    invariants: List[Invariant]
    state_vars: List[StateVar]
    ambiguities: List[Ambiguity]

def clean_text(s: str, max_chars: int = 14000) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.splitlines())
    s = s.strip()
    if len(s) > max_chars:
        s = s[:max_chars]
    return s

def pick_files():
    files = sorted(SRC_DIR.glob("*.txt"))
    out = []
    for f in files:
        try:
            if f.stat().st_size < 100:
                continue
            out.append(f)
        except:
            pass
    return out

client = OpenAI()

files = pick_files()
print("files_to_process:", len(files))
for f in files:
    text = clean_text(f.read_text(encoding="utf-8", errors="ignore"))
    prompt = f"""
You are inducing an ontology for folk dance description from source text.

Only propose primitives/invariants/state variables that are directly supported by the text.
For each item, include a short evidence excerpt copied from the source text.
Prefer a small, reusable vocabulary; include synonyms when the text uses variants.

Return JSON matching the schema exactly.

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
enforce_counts = Counter()

prim_syn = defaultdict(set)
inv_enforce = defaultdict(set)

for p in sorted(OUT_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    for pr in d.get("primitives", []):
        name = (pr.get("name","") or "").strip().lower()
        if name:
            prim_counts[name] += 1
            for s in pr.get("synonyms", []) or []:
                prim_syn[name].add(str(s).strip().lower())
    for inv in d.get("invariants", []):
        name = (inv.get("name","") or "").strip().lower()
        if name:
            inv_counts[name] += 1
            be = (inv.get("best_enforced_by","") or "").strip().lower()
            if be:
                inv_enforce[name].add(be)
                enforce_counts[be] += 1
    for sv in d.get("state_vars", []):
        name = (sv.get("name","") or "").strip().lower()
        if name:
            state_counts[name] += 1

(OUT_SUM / "primitives_top.json").write_text(json.dumps(prim_counts.most_common(50), indent=2) + "\n", encoding="utf-8")
(OUT_SUM / "invariants_top.json").write_text(json.dumps(inv_counts.most_common(50), indent=2) + "\n", encoding="utf-8")
(OUT_SUM / "state_vars_top.json").write_text(json.dumps(state_counts.most_common(50), indent=2) + "\n", encoding="utf-8")
(OUT_SUM / "enforcement_top.json").write_text(json.dumps(enforce_counts.most_common(50), indent=2) + "\n", encoding="utf-8")

print("\nTOP PRIMITIVES:")
for k,n in prim_counts.most_common(20):
    syn = sorted(list(prim_syn[k]))[:8]
    print(f"- {k} ({n})" + (f" syn={syn}" if syn else ""))

print("\nTOP INVARIANTS:")
for k,n in inv_counts.most_common(20):
    be = sorted(list(inv_enforce[k]))[:5]
    print(f"- {k} ({n})" + (f" enforce={be}" if be else ""))

print("\nTOP STATE VARS:")
for k,n in state_counts.most_common(20):
    print(f"- {k} ({n})")

print("\nWROTE SUMMARY FILES:")
print("analysis/out/discovery/primitives_top.json")
print("analysis/out/discovery/invariants_top.json")
print("analysis/out/discovery/state_vars_top.json")
print("analysis/out/discovery/enforcement_top.json")

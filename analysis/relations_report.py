import json, re
from pathlib import Path
from collections import Counter, defaultdict

LLM_DIR = Path("analysis/out/llm")

def norm(s):
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

rel_counter = Counter()
by_dance = defaultdict(list)

for p in sorted(LLM_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    did = d["dance_id"]
    for r in d.get("inferred_relations", []):
        rel = norm(r.get("relation",""))
        between = [norm(x) for x in (r.get("between") or [])]
        rel_counter[rel] += 1
        by_dance[did].append((rel, tuple(between), norm(r.get("notes",""))))

print("Top relation types:")
for rel, n in rel_counter.most_common(30):
    print(f"- {rel}: {n}")

print("\nPer dance:")
for did in sorted(by_dance.keys()):
    print("\n==", did, "==")
    for rel, between, notes in by_dance[did]:
        print("-", rel, "|", list(between), "|", notes[:120])

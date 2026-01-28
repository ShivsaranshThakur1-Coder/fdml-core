import os, re, csv, json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
OUT_CSV = ROOT / "analysis" / "out" / "corpus_audit.csv"
OUT_JSONL = ROOT / "analysis" / "out" / "corpus_audit.jsonl"

def txt(el):
    if el is None: return ""
    return (el.text or "").strip()

def count_xpath(root, tag):
    return len(root.findall(".//" + tag))

def attr_count(root, attr):
    return sum(1 for e in root.iter() if attr in (e.attrib or {}))

def attr_values(root, tag, attr):
    vals = []
    for e in root.findall(".//" + tag):
        if attr in e.attrib:
            v = (e.attrib.get(attr) or "").strip()
            if v: vals.append(v)
    return vals

def path_group(p: Path) -> str:
    s = str(p).replace("\\", "/")
    if "/corpus/valid/" in s: return "valid"
    if "/corpus/invalid_v11/" in s: return "invalid_v11"
    if "/corpus/invalid/" in s: return "invalid"
    return "unknown"

def step_text_signals(root):
    texts = []
    for tag in ["step", "section", "figure"]:
        for e in root.findall(".//" + tag):
            t = (e.text or "").strip()
            if t:
                texts.append(t)
    blob = " ".join(texts)
    blob_l = blob.lower()
    signals = {
        "mentions_partner": ("partner" in blob_l) or ("partners" in blob_l),
        "mentions_couple": ("couple" in blob_l) or ("couples" in blob_l),
        "mentions_line": ("line" in blob_l) or ("lines" in blob_l),
        "mentions_circle": ("circle" in blob_l) or ("round" in blob_l),
        "mentions_square": ("square" in blob_l),
        "mentions_left_right": (" left " in f" {blob_l} ") or (" right " in f" {blob_l} "),
        "mentions_facing": ("face" in blob_l) or ("facing" in blob_l),
        "mentions_clock": ("clockwise" in blob_l) or ("anticlockwise" in blob_l) or ("counterclockwise" in blob_l),
    }
    return signals, blob[:4000]

rows = []
OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

files = sorted(CORPUS.rglob("*.fdml.xml"))
for p in files:
    rec = {
        "path": str(p.relative_to(ROOT)),
        "group": path_group(p),
        "parse_ok": False,
    }
    try:
        tree = ET.parse(p)
        r = tree.getroot()
        rec["parse_ok"] = True
        rec["fdml_version"] = (r.attrib.get("version") or "").strip()

        meta = r.find("./meta")
        rec["title"] = txt(meta.find("./title")) if meta is not None else ""
        meter = meta.find("./meter") if meta is not None else None
        tempo = meta.find("./tempo") if meta is not None else None
        rec["meter_value"] = (meter.attrib.get("value") or "").strip() if meter is not None else ""
        rec["tempo_bpm"] = (tempo.attrib.get("bpm") or "").strip() if tempo is not None else ""

        rec["n_section"] = count_xpath(r, "section")
        rec["n_part"] = count_xpath(r, "part")
        rec["n_figure"] = count_xpath(r, "figure")
        rec["n_sequence"] = count_xpath(r, "sequence")
        rec["n_use"] = count_xpath(r, "use")

        rec["n_step_direct"] = count_xpath(r, "step")
        rec["n_measureRange"] = count_xpath(r, "measureRange")
        rec["n_step_in_measureRange"] = len(r.findall(".//measureRange//step"))

        rec["has_figure_id"] = any("id" in e.attrib for e in r.findall(".//figure"))
        rec["formation_attr_count"] = attr_count(r, "formation")
        rec["figure_formation_values"] = list(dict.fromkeys(attr_values(r, "figure", "formation")))[:20]

        signals, sample_text = step_text_signals(r)
        rec.update(signals)
        rec["sample_text_head"] = sample_text

    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"

    rows.append(rec)

# write csv
cols = [
    "path","group","parse_ok","fdml_version","title","meter_value","tempo_bpm",
    "n_section","n_part","n_figure","n_sequence","n_use",
    "n_step_direct","n_measureRange","n_step_in_measureRange",
    "has_figure_id","formation_attr_count","figure_formation_values",
    "mentions_partner","mentions_couple","mentions_line","mentions_circle",
    "mentions_square","mentions_left_right","mentions_facing","mentions_clock"
]
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        rr = dict(r)
        rr["figure_formation_values"] = "|".join(rr.get("figure_formation_values") or [])
        w.writerow({k: rr.get(k, "") for k in cols})

# write jsonl
with open(OUT_JSONL, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# print summary
valid = [r for r in rows if r["group"] == "valid" and r.get("parse_ok")]
valid_sorted = sorted(valid, key=lambda x: (x.get("n_step_direct",0) + x.get("n_step_in_measureRange",0)), reverse=True)

print("Wrote:", OUT_CSV)
print("Wrote:", OUT_JSONL)
print()
print("Top 10 valid by step count:")
for r in valid_sorted[:10]:
    steps = (r.get("n_step_direct",0) or 0) + (r.get("n_step_in_measureRange",0) or 0)
    print(f"- {r['path']}: steps={steps}, figures={r.get('n_figure',0)}, formationAttrs={r.get('formation_attr_count',0)}")

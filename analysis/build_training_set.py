import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path("/Users/shivsaranshthakur/Projects/fdml-core")
OUT = ROOT / "analysis" / "out" / "training_set.jsonl"

def norm_id(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\.(fdml\.xml|xml|txt|pdf|docx)$", "", s)
    s = re.sub(r"_ocr$", "", s)
    s = re.sub(r"_full$", "", s)
    s = re.sub(r"\d+$", "", s)
    s = s.replace("_", "-").replace(" ", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    return s

source_files = {
    "abdala": ROOT / "analysis" / "out" / "sources_text" / "Abdala1992.txt",
    "aalistullaa": ROOT / "analysis" / "out" / "sources_text" / "Aalistullaa2000_ocr.txt",
    "cobankat": ROOT / "analysis" / "out" / "sources_text" / "Cobankat2004_ocr.txt",
    "haire-mamougeh": ROOT / "analysis" / "out" / "sources_text" / "HaireMamougeh1985_ocr.txt",
    "mayim-mayim": ROOT / "analysis" / "out" / "sources_text" / "MayimMayim_full.txt",
}

fdml_files = {norm_id(p.name.replace(".fdml.xml","")): p for p in sorted((ROOT/"corpus"/"valid").glob("*.fdml.xml"))}

def fdml_meta(fdml_path: Path):
    r = ET.parse(fdml_path).getroot()
    meta = r.find("./meta")
    title = (meta.findtext("./title") or "").strip() if meta is not None else ""
    meter = (meta.find("./meter").attrib.get("value","").strip() if meta is not None and meta.find("./meter") is not None else "")
    tempo = (meta.find("./tempo").attrib.get("bpm","").strip() if meta is not None and meta.find("./tempo") is not None else "")
    formations = []
    for e in r.iter():
        if "formation" in e.attrib:
            v = (e.attrib.get("formation") or "").strip()
            if v:
                formations.append(v)
    formations = list(dict.fromkeys(formations))
    return title, meter, tempo, formations

OUT.unlink(missing_ok=True)
written = 0

for dance_id, src_path in source_files.items():
    if not src_path.exists():
        continue
    src_text = src_path.read_text(encoding="utf-8", errors="ignore")
    fdml_path = fdml_files.get(dance_id)
    rec = {
        "dance_id": dance_id,
        "source_text_path": str(src_path.relative_to(ROOT)),
        "source_text": src_text,
        "fdml_path": str(fdml_path.relative_to(ROOT)) if fdml_path else None,
        "fdml_title": None,
        "fdml_meter": None,
        "fdml_tempo_bpm": None,
        "fdml_formations": [],
    }
    if fdml_path:
        title, meter, tempo, formations = fdml_meta(fdml_path)
        rec["fdml_title"] = title
        rec["fdml_meter"] = meter
        rec["fdml_tempo_bpm"] = tempo
        rec["fdml_formations"] = formations
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    written += 1

print("Wrote", OUT, "records=", written)

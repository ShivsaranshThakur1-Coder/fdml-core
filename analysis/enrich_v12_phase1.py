import xml.etree.ElementTree as ET
from pathlib import Path
import shutil
import re

SRC = Path("corpus/valid_v12_auto")
OUT = Path("corpus/valid_v12_auto_phase1")

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True, exist_ok=True)

def norm(s): return (s or "").strip().lower()

def ensure_roles(root):
    meta = root.find("meta")
    if meta is None: return
    mg = meta.find("geometry")
    if mg is None: return
    roles = mg.find("roles")
    if roles is None:
        roles = ET.SubElement(mg, "roles")
    declared = {e.attrib.get("id","") for e in roles.findall("role")}
    needed = set()
    for s in root.findall(".//step"):
        w = (s.attrib.get("who","") or "").strip()
        if w:
            needed.add(w)
    for rid in sorted(needed):
        if rid not in declared:
            ET.SubElement(roles, "role", {"id": rid})
            declared.add(rid)

def add_geo_minimal(root):
    for step in root.findall(".//step"):
        geo = step.find("geo")
        if geo is None:
            geo = ET.SubElement(step, "geo")
        if geo.find("primitive") is not None:
            continue
        who = (step.attrib.get("who","all") or "all").strip() or "all"
        action = norm(step.attrib.get("action",""))
        facing = norm(step.attrib.get("facing",""))
        if "center" in facing:
            ET.SubElement(geo, "primitive", {"kind":"face","who":who,"dir":"center"})
        if "turn" in action or "twirl" in action:
            ET.SubElement(geo, "primitive", {"kind":"turn","who":who})
        ET.SubElement(geo, "primitive", {"kind":"move","who":who})

def fix_known_kinds(root, stem):
    meta = root.find("meta")
    if meta is None: return
    mg = meta.find("geometry")
    if mg is None: return
    form = mg.find("formation")
    if form is None: return
    if stem == "abdala":
        form.set("kind","line")
    if stem == "mayim-mayim":
        form.set("kind","circle")

for f in sorted(SRC.glob("*.v12.fdml.xml")):
    t = ET.parse(f)
    r = t.getroot()
    stem = f.name.replace(".v12.fdml.xml","")
    ensure_roles(r)
    add_geo_minimal(r)
    fix_known_kinds(r, stem)
    out = OUT / f.name
    t.write(out, encoding="utf-8", xml_declaration=True)

print("Wrote:", OUT)

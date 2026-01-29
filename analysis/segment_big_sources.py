import re
from pathlib import Path

SRC = Path("analysis/out/sources_text")
OUT = Path("analysis/out/segmented")
OUT.mkdir(parents=True, exist_ok=True)

def segment(name):
    text = (SRC / name).read_text(encoding="utf-8", errors="ignore")
    lines = [l.rstrip() for l in text.splitlines()]
    idx = []
    for i,l in enumerate(lines):
        s=l.strip()
        if 2 <= len(s) <= 45 and re.match(r"^[A-Za-z][A-Za-z '\-]+$", s):
            if s.isupper() or s.istitle():
                if i>2 and lines[i-1].strip()=="":
                    idx.append((i,s))
    segs=[]
    for k,(i,title) in enumerate(idx):
        j = idx[k+1][0] if k+1 < len(idx) else len(lines)
        block = "\n".join(lines[i:j]).strip()
        if len(block) < 400:
            continue
        segs.append((title, block))
    return segs

for fname in ["EvansVilleFolkDance.txt","SocalFolkDance.txt"]:
    segs = segment(fname)
    outdir = OUT / Path(fname).stem
    outdir.mkdir(parents=True, exist_ok=True)
    for n,(title,block) in enumerate(segs,1):
        safe = re.sub(r"[^a-z0-9]+","-", title.lower()).strip("-")
        (outdir / f"{n:03d}-{safe}.txt").write_text(block+"\n", encoding="utf-8")
    print(fname, "segments=", len(segs), "->", outdir)

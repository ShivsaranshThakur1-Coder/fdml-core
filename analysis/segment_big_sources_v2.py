import re
from pathlib import Path

SRC = Path("analysis/out/sources_text")
OUT = Path("analysis/out/segmented_v2")
OUT.mkdir(parents=True, exist_ok=True)

def is_title_like(s):
    s=s.strip()
    if not (2 <= len(s) <= 60):
        return False
    if re.search(r"\d", s):
        return False
    if re.search(r"^(FORMATION|MUSIC|RECORD|RHYTHM|STEPS|STYLE|STYLING|MEAS|MEASURE|PATTERN)\b", s, re.I):
        return False
    if re.match(r"^[A-Za-z][A-Za-z '\-]+$", s):
        return True
    return False

def segment(name):
    text = (SRC / name).read_text(encoding="utf-8", errors="ignore")
    lines = [l.rstrip("\n") for l in text.splitlines()]

    idx = []
    for i in range(len(lines)):
        s = lines[i].strip()

        # Pattern A: Title line then (Country) next line
        if is_title_like(s) and i+1 < len(lines):
            nxt = lines[i+1].strip()
            if re.match(r"^\([A-Za-z][A-Za-z '\-]+\)$", nxt):
                idx.append((i, s))
                continue

        # Pattern B: Title line then (Country) within 3 lines
        if is_title_like(s):
            for k in (1,2,3):
                if i+k < len(lines):
                    nxt = lines[i+k].strip()
                    if re.match(r"^\([A-Za-z][A-Za-z '\-]+\)$", nxt):
                        idx.append((i, s))
                        break

        # Pattern C: "FORMATION:" line — treat previous non-empty title-ish line as start
        if re.match(r"^FORMATION\s*:", s, re.I):
            j=i-1
            while j>=0 and lines[j].strip()=="":
                j-=1
            if j>=0 and is_title_like(lines[j]):
                idx.append((j, lines[j].strip()))

    # dedupe + sort
    seen=set()
    uniq=[]
    for i,t in sorted(idx, key=lambda x:x[0]):
        if i not in seen:
            seen.add(i)
            uniq.append((i,t))

    segs=[]
    for k,(i,title) in enumerate(uniq):
        j = uniq[k+1][0] if k+1 < len(uniq) else len(lines)
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

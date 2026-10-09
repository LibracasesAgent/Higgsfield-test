#!/usr/bin/env python3
"""Prepare a new winner for remix.py: find its RAW, transcribe it, make a contact sheet and propose a draft
winner_raws entry (pipeline/data/clip_bank.json) for Claude to review like an editor.

  python3 pipeline/winner_prep.py "ACH-YEVH-172-H4" [--id <drive id>] [--key raw172_H4] [--product "Hobo 2.0"] [--write]

  1. Library match (pipeline/cache/library.json, built by index_library.py): the RAW first (a /RAW/ folder or
     "RAW" in the name, no captions); only an edited export found -> burned_captions true. --id skips the search.
  2. Download (recut.source: 1 MB ranges, cached in pipeline/cache/media/) and transcribe (faster-whisper
     small.en, word timestamps) -> pipeline/data/transcripts/<key>_words.json
  3. Contact sheet with timestamps -> <outdir>/<key>_sheet.jpg (Read it: speaker, product, burned captions).
  4. Draft entry (printed with the timed transcript): concept/hook, product, dur, cold_opens (top 3 hook-like
     sentences of 2-7 s after 5 s, each with a proposed hook "type", one of projects.TYPES), insert_at (sentence
     holding the offer), offer_word, labels (REASON/STEP n), review_intro, min_reviews, "draft": true. Ranges sit on word boundaries (first word -0.08 s, last word
     +0.15 s); where whisper's timing lands in audible speech the point moves to the real pause nearby.
     --write puts it into winner_raws (other entries untouched; a reviewed entry is never overwritten).
     Then review it: fix ranges/labels/types/insert point/cuts, set end_title, delete "draft" (edit the JSON).
     Burned-caption files: put every boundary on a caption change (look at the frames), not just the words.

  python3 pipeline/winner_prep.py --check [raw94_H4 ...]
          Verify entries against their transcripts: words inside every cold open, words around insert_at and
          cuts, the word each label and the offer card land on, RAW body length vs min_reviews, and (when the
          file is cached) the audio level at every boundary: a cut inside speech is a WARNING (exit 1), and so are a
          cold open without a valid "type" and a cold open whose first/last frames show the neighbouring shot (cut
          as the render cuts it; the first frame is the version's thumbnail).
  python3 pipeline/winner_prep.py --format
          Rewrite the winner_raws section in the standard layout (nothing else in the file changes).
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from find_assets import is_raw, match_ad, strip_name  # noqa: E402
from index_library import CACHE, load_config  # noqa: E402

BANK = os.path.join(HERE, "data", "clip_bank.json")
TRANS = os.path.join(HERE, "data", "transcripts")
FONT = os.path.join(HERE, "assets", "fonts", "Montserrat.ttf")
END = {"Hobo Bag": "The Luxury Hobo Bag", "Hobo 2.0": "Hobo 2.0", "Hobo Bag 3-Piece Set": "The Hobo 3-Piece Set",
       "Vintage Bag": "The Vintage Bag", "Slouchy Soft 3-Piece Set": "The Slouchy Soft Set"}
PRODUCT_WORDS = [("Hobo 2.0", r"hobo 2\.?0|hobo two|2\.0"), ("Hobo Bag 3-Piece Set", r"3[- ]piece|three[- ]piece"),
                 ("Slouchy Soft 3-Piece Set", r"slouchy"), ("Vintage Bag", r"vintage"), ("Hobo Bag", r"hobo")]
NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, **{str(k): k for k in range(1, 8)}}
ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7}
PROBLEM = re.compile(r"\b(los[et]|losing|robbed|rob|stolen|steal|thie|pickpocket|fakes?|cheap|mess|messy|digging|pain|"
                     r"terrible|worse|worst|tired|anxious|worr|hate|regret|broke|fall apart|fell apart|fray|black hole|"
                     r"embarrass|ruin|plastic|warn|problem|struggl|heavy|bottomless)", re.I)
HOOKY = re.compile(r"\b(most|never|stop|secret|truth|honest|nobody|everyone|wish|mistake|why|wait|crazy|last)\b", re.I)
CTA = re.compile(r"\b(link|click|tap|below|shop now|order|cart|website|grab)\b", re.I)
WEAK = {"and", "so", "but", "because", "or", "then", "also", "which", "first", "second", "third", "fourth", "fifth",
        "reason", "step", "number", "plus", "as"}
PRONOUN = {"it", "it's", "this", "they", "these", "that", "that's", "there", "there's", "she", "he"}
OFFER = {"50", "fifty", "percent", "half", "off"}


def clean(w):
    return w.lower().strip(".,!?;:\"'%")


def sentences(ws):
    """[(i0, i1)] word-index spans: split at . ? ! and pauses >= 0.6 s; run-ons > 7 s also at pauses >= 0.35 s and
    capitalised words (whisper sometimes drops the full stops but keeps the capitals)."""
    out, cur = [], []
    for i, w in enumerate(ws):
        cur.append(i)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        if nxt is None or w["w"].rstrip("\"'").endswith((".", "?", "!")) or nxt["s"] - w["e"] >= 0.6:
            out.append((cur[0], cur[-1]))
            cur = []
    res = []
    for a, b in out:
        if ws[b]["e"] - ws[a]["s"] <= 7:
            res.append((a, b))
            continue
        s0 = a
        for i in range(a, b):
            nw = ws[i + 1]["w"]
            cap = nw[:1].isupper() and not re.match(r"I\b|I'|Susan|Mom|Grandma", nw)
            if ws[i + 1]["s"] - ws[i]["e"] >= 0.35 or (cap and i + 1 - s0 >= 3):
                res.append((s0, i))
                s0 = i + 1
        res.append((s0, b))
    return res


def text(ws, a, b):
    return " ".join(w["w"] for w in ws[a:b + 1]).replace(" %", "%").replace(" .", ".").replace(" -", "-")


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    import numpy as np
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def edge_flash(path, r, n=6):
    """Frames of a neighbouring shot at the edges of a cold open, as the render cuts it (recut: -ss/-t, fps 30): a jump
    in the first/last n frames that stands out (> 25 and 4x the cold open's median frame change, 2x its neighbours'). The
    first frame is also the version's thumbnail. Returns [("start"|"end", frames of the other shot, s of the cut)]."""
    import numpy as np
    W, H = 64, 114
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(r[0]), "-t", f"{r[1] - r[0]:.3f}", "-i", path,
                          "-vf", f"fps=30,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    k = len(raw) // (W * H)
    if k < 3:
        return []
    d = np.abs(np.diff(np.frombuffer(raw[:k * W * H], np.uint8).reshape(k, H, W).astype(np.float32), axis=0)).mean(axis=(1, 2))
    thr = max(25.0, 4 * float(np.median(d)))
    jump = [i for i in range(len(d)) if d[i] > thr and d[i] > 2 * max([d[j] for j in (i - 1, i + 1) if 0 <= j < len(d)])]
    return ([("start", i + 1, round(r[0] + (i + 1) / 30, 2)) for i in jump if i < n] +
            [("end", len(d) - i, round(r[0] + (i + 1) / 30, 2)) for i in jump if i >= len(d) - n])


def db(x, t, w=0.02):
    seg = x[max(int((t - w / 2) * 16000), 0):][:int(w * 16000)]
    return float(20 * math.log10(math.sqrt(float((seg ** 2).mean())) + 1e-9)) if len(seg) else -120.0


def quiet(x, t, lo, hi):
    """t, or the quietest 20 ms point in [lo, hi] when t sits in speech (louder than -45 dB and >= 10 dB above it)."""
    if x is None or hi <= lo or db(x, t) <= -45:
        return t
    ts = [lo + k * 0.02 for k in range(int((hi - lo) / 0.02) + 1)]
    q = min(ts, key=lambda u: db(x, u))
    return q if db(x, t) - db(x, q) >= 10 else t


def word_range(ws, a, b, dur=None, x=None):
    """RAW seconds for words a..b: 0.08 s lead-in, 0.15 s tail, never into the neighbouring words (whisper's
    timings); with the audio x, a point that still sits in speech moves to the real pause nearby."""
    s = ws[a]["s"] - 0.08
    if a > 0:
        s = max(s, ws[a - 1]["e"])
        s = quiet(x, s, max(ws[a - 1]["s"] + ws[a - 1]["e"], 2 * s - 0.3) / 2, ws[a]["s"] + 0.1)
    e = ws[b]["e"] + 0.15
    if b + 1 < len(ws):
        e = min(e, ws[b + 1]["s"])
        e = quiet(x, e, ws[b]["e"] - 0.06, min(e + 0.25, (ws[b + 1]["s"] + ws[b + 1]["e"]) / 2))
    elif dur:
        e = min(e, dur)
    return [round(max(s, 0), 2), round(e, 2)]


def hook_score(t, d):
    low = t.lower()
    first = clean(t.split()[0])
    sc = 2.0 * ("?" in t) + 1.5 * bool(re.search(r"\d|\b(two|three|four|five|six|seven|ten|hundred)\b", low))
    sc += 1.5 * min(len(HOOKY.findall(low)), 2) + 1.5 * min(len(PROBLEM.findall(low)), 2)
    sc += 1.0 * bool(re.search(r"\b(my|mine)\b", low)) - 3.0 * bool(CTA.search(low))
    sc -= 1.5 * (first in WEAK) + 0.5 * (first in PRONOUN)
    return round(sc + 0.5 * (2.5 <= d <= 5), 2)


def draft_label(t):
    ws = [x for x in re.sub(r"[^\w\s'?%.-]", "", t).split()]
    while ws and clean(ws[0]) in WEAK:
        ws = ws[1:]
    ws = ws[:4]
    while len(ws) > 2 and clean(ws[-1]) in {"to", "of", "the", "a", "an", "after", "is", "was", "and", "for", "be", "your", "my"}:
        ws = ws[:-1]
    lab = " ".join(ws).upper().rstrip(".,")
    return lab + "?" if "?" in t and not lab.endswith("?") else lab


def cold_open_candidates(ws, dur, n=3, after=5.0, x=None):
    sents = sentences(ws)
    cands = []
    for k in range(len(sents)):
        for m in range(k, min(k + 3, len(sents))):
            a, b = sents[k][0], sents[m][1]
            d = ws[b]["e"] - ws[a]["s"]
            if m > k and (clean(ws[sents[m][0]]["w"]) in WEAK - {"and", "but", "so"} or clean(ws[sents[m][0]]["w"]).isdigit()):
                break
            if ws[a]["s"] < after or not 2 <= d <= 7:
                continue
            t = text(ws, a, b)
            cands.append((hook_score(t, d) - 0.3 * (m - k), a, b, t, draft_label(text(ws, a, sents[k][1]))))
    picked = []
    for c in sorted(cands, key=lambda c: (-c[0], c[1])):
        if all(c[2] < p[1] or c[1] > p[2] for p in picked):
            picked.append(c)
        if len(picked) == n:
            break
    return [dict(range=word_range(ws, a, b, dur, x), label=lab, line=t, score=sc) for sc, a, b, t, lab in picked]


def sentence_of(ws, i):
    return next((a, b) for a, b in sentences(ws) if a <= i <= b)


def cut_point(ws, i, x=None):
    """A RAW time just before word i (middle of the pause before it, or the real pause in the audio x)."""
    if i == 0:
        return 0.0
    t = max(ws[i - 1]["e"], (ws[i - 1]["e"] + ws[i]["s"]) / 2)
    return round(quiet(x, t, (ws[i - 1]["s"] + ws[i - 1]["e"]) / 2, ws[i]["s"] + 0.1), 2)


def offer_and_insert(ws, dur, x=None):
    hit = next((i for i, w in enumerate(ws)
                if w["s"] >= 0.4 * dur and (clean(w["w"]) in OFFER or clean(w["w"]).startswith("50"))), None)
    if hit is not None:
        ins = cut_point(ws, sentence_of(ws, hit)[0], x)
    else:
        target = 0.8 * dur
        ins = cut_point(ws, min((a for a, _ in sentences(ws)), key=lambda a: abs(ws[a]["s"] - target)), x)
    tok = lambda w: "50" if "50" in w["w"] else re.sub(r"[^\w]", "", w["w"])  # noqa: E731
    after = [w for w in ws if w["s"] >= ins - 1 and (clean(w["w"]) in OFFER - {"off"} or "50" in w["w"])]
    if after:
        return ins, tok(after[0]), None
    before = [w for w in ws if clean(w["w"]) in OFFER - {"off"} or "50" in w["w"]]
    if before:
        return ins, tok(before[0]), round(math.floor(before[0]["s"] * 10) / 10 - 0.2, 1)
    return ins, None, None


def number_labels(ws):
    """Longest 1-2-3... run of number words (cardinals after 'reason'/'step' or at a sentence start, ordinals, digits)."""
    starts = {a for a, _ in sentences(ws)}
    low = " ".join(clean(w["w"]) for w in ws)
    best = []
    for fam in (NUM, ORD):
        pos = {}
        for i, w in enumerate(ws):
            c = clean(w["w"])
            if c not in fam:
                continue
            ok = (fam is ORD or i in starts or w["w"].endswith((",", "."))
                  or (i > 0 and clean(ws[i - 1]["w"]) in ("reason", "step", "number", "tip")))
            if ok:
                pos.setdefault(fam[c], []).append(i)
        for i0 in pos.get(1, []):
            run, last = [i0], i0
            for k in range(2, 8):
                nxt = next((j for j in pos.get(k, []) if j > last and ws[j]["s"] - ws[last]["s"] <= 25), None)
                if nxt is None:
                    break
                run.append(nxt)
                last = nxt
            if len(run) > len(best):
                best = run
    if len(best) < 2:
        return []
    steps = clean(ws[best[0]]["w"]) in ORD or re.search(r"\bsteps?\b|\bhow to\b", low)
    kind = "STEP" if steps and not re.search(r"\breasons?\b|\bwhy\b", low) else "REASON"
    out, prev = [], None
    for k, j in enumerate(best):
        after = math.floor((ws[prev]["s"] if prev is not None else ws[j]["s"]) * 10) / 10
        out.append(dict(text=f"{kind} {k + 1}", word=clean(ws[j]["w"]), after=after))
        prev = j
    return out


def min_reviews(body):
    return 2 if body >= 50 else 3 if body >= 30 else 4 if body >= 20 else 5


def body_len(e, dur):
    return (e.get("end") or dur) - e.get("start", 0.0) - sum(b - a for a, b in e.get("cut", []))


def parse_code(name):
    n = strip_name(name)
    m = re.search(r"(\d+)\s*[-_ ]*\s*(H\d+|\(\d+\))", n, re.I)
    if m:
        return m.group(1), m.group(2).upper() if m.group(2)[0] in "hH" else m.group(2)
    m = re.search(r"\b(C\d+)[\s_-]+(V\d+)", n, re.I)
    if m:
        return m.group(1).upper(), m.group(2).upper()
    m = re.findall(r"\d+", n)
    return (m[-1] if m else re.sub(r"\W", "", n)[:12]), ""


def default_key(concept, hook):
    h = hook.strip("()")
    if concept.isdigit():
        return f"raw{concept}_{h}" if h else f"raw{concept}"
    return f"{concept.lower()}_{h}" if h else concept.lower()


def guess_product(path, words_text):
    for name, folders in load_config()["products"].items():
        if any(path.startswith(f + "/") for f in folders):
            if name == "Slouchy Vintage Bag":
                return "Slouchy Soft 3-Piece Set" if re.search("slouchy", words_text + path, re.I) else "Vintage Bag"
            if name in END:
                return name
    for name, rx in PRODUCT_WORDS:
        if re.search(rx, (path + " " + words_text).lower()):
            return name
    return "Hobo Bag"


def fetch(fid):
    import recut
    recut.LOCAL_MAX = max(recut.LOCAL_MAX, 600 * 2**20)
    p = recut.source(fid)
    if os.path.exists(p):
        return p
    import drive_upload
    if all(os.environ.get(v) for v in drive_upload.VARS):
        return drive_upload.download(drive_upload.access_token(), fid, os.path.join(recut.MEDIA_CACHE, fid))
    sys.exit(f"Could not download {fid} (range reads failed and no Drive OAuth variables are set).")


def probe_dur(f):
    return round(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                      capture_output=True, text=True).stdout), 2)


def transcribe(path, out):
    if os.path.exists(out):
        return json.load(open(out))
    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(path, word_timestamps=True, condition_on_previous_text=False)
    ws = [dict(w=w.word.strip(), s=round(float(w.start), 2), e=round(float(w.end), 2)) for s in segs for w in s.words]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(ws, open(out, "w"))
    return ws


def contact_sheet(path, dur, out, cols=6, n=36):
    step = max(1.5, dur / n)
    rows = math.ceil(dur / step / cols)
    vf = (f"fps=1/{step:.3f},scale=240:-2,drawtext=fontfile={FONT}:text='%{{pts\\:flt}}':x=8:y=8:fontsize=22:"
          f"fontcolor=white:box=1:boxcolor=black@0.6,tile={cols}x{rows}")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf", vf, "-frames:v", "1", "-y", out],
                   check=True)
    return out


def hook_type(line, label):
    """Proposed hook type of a cold open (projects.TYPES; the editor corrects it: plan/report show it per version)."""
    import projects
    return projects.classify(f"{line} {label}".strip())


def draft(name, fid, path, ws, dur, raw, product=None, x=None):
    concept, hook = parse_code(name)
    product = product or guess_product(path, " ".join(w["w"] for w in ws))
    ins, offer_word, offer_after = offer_and_insert(ws, dur, x)
    edit = dict(start=0.0, end=None, cut=[], insert_at=ins, offer_word=offer_word, offer_after=offer_after,
                burned_captions=not raw, labels=number_labels(ws), end_title=END.get(product, f"The {product}"),
                cold_opens=[dict({k: c[k] for k in ("range", "label", "line")}, type=hook_type(c["line"], c["label"]))
                            for c in cold_open_candidates(ws, dur, x=x)])
    first_person = len(re.findall(r"\b(i|i'm|my|me|mine)\b", " ".join(clean(w["w"]) for w in ws))) >= 4
    edit["review_intro"] = (["Don't just take her word for it."] if first_person else []) + [
        "And customers agree.", "Here's what customers are saying."]
    edit["min_reviews"] = min_reviews(body_len(edit, dur))
    notes = f"Draft by winner_prep from {'RAW' if raw else 'edited export (burned-in captions)'}: {path}."
    return dict(id=fid, dur=dur, ad=strip_name(name), product=product, concept=concept, hook=hook, draft=True,
                notes=notes, edit=edit)


# ---- clip_bank.json: rewrite only the winner_raws section, in a readable fixed layout ----

def j(v):
    return json.dumps(v, ensure_ascii=False)


def fmt_entry(k, e):
    head = ", ".join(f"{j(x)}: {j(v)}" for x, v in e.items() if x not in ("notes", "edit"))
    if "edit" not in e:
        return f"  {j(k)}: {{{head}" + (f", \"notes\": {j(e['notes'])}" if "notes" in e else "") + "}"
    lines = [f"  {j(k)}: {{{head},"]
    if "notes" in e:
        lines.append(f"   \"notes\": {j(e['notes'])},")
    ed = e["edit"]
    first = ("start", "end", "cut", "insert_at", "offer_word", "offer_after", "burned_captions")
    rest = [x for x in ed if x not in first + ("labels", "end_title", "cold_opens")]
    lines.append("   \"edit\": {" + ", ".join(f"{j(x)}: {j(ed[x])}" for x in first if x in ed) + ",")
    lines.append(f"    \"labels\": {j(ed.get('labels', []))},")
    lines.append(f"    \"end_title\": {j(ed.get('end_title'))},")
    cos = ed.get("cold_opens", [])
    lines.append("    \"cold_opens\": [" + ("" if cos else "]" + ("," if rest else "")))
    for i, c in enumerate(cos):
        lines.append(f"     {j(c)}" + ("," if i + 1 < len(cos) else "]" + ("," if rest else "")))
    if rest:
        lines.append("    " + ", ".join(f"{j(x)}: {j(ed[x])}" for x in rest))
    lines[-1] += "}}"
    return "\n".join(lines)


def section_span(txt, name="winner_raws"):
    i = txt.index(f'"{name}": {{') + len(f'"{name}": ')
    depth, k, ins = 0, i, False
    while True:
        c = txt[k]
        if ins:
            if c == "\\":
                k += 1
            elif c == '"':
                ins = False
        elif c == '"':
            ins = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i, k + 1
        k += 1


def write_raws(raws):
    txt = open(BANK).read()
    before = json.loads(txt)
    a, b = section_span(txt)
    body = "{\n" + ",\n".join(fmt_entry(k, e) for k, e in raws.items()) + "\n }"
    new = txt[:a] + body + txt[b:]
    after = json.loads(new)
    assert after["winner_raws"] == raws and all(after[s] == before[s] for s in before if s != "winner_raws")
    open(BANK, "w").write(new)


# ---- verification ----

def check(key, e):
    ed, ws = e.get("edit", {}), json.load(open(os.path.join(TRANS, f"{key}_words.json")))
    dur = e["dur"]
    import recut
    f = os.path.join(recut.MEDIA_CACHE, e["id"])
    x = load_audio(f) if os.path.exists(f) else None
    print(f"== {key}  {e.get('ad')}  {e.get('product')}  dur {dur}  concept {e.get('concept')!r} hook {e.get('hook')!r}"
          + ("  DRAFT" if e.get("draft") else ""))
    warn = []

    def inside(t):
        return next((w for w in ws if w["s"] + 0.02 < t < w["e"] - 0.02), None)

    def level(t):
        """Audio level at a boundary vs the quietest point within 0.12 s (a cut inside speech is loud)."""
        if x is None:
            return ""
        q = min((t + k * 0.02 for k in range(-6, 7)), key=lambda u: db(x, u))
        if db(x, t) - db(x, q) >= 12 and db(x, t) > -35:
            warn.append(f"boundary {t} is in speech ({db(x, t):.0f} dB; pause at {q:.2f}, {db(x, q):.0f} dB)")
        return f" [{db(x, t):.0f}/{db(x, q):.0f} dB]"

    import projects
    for c in ed.get("cold_opens", []):
        r = c["range"]
        if c.get("type") not in projects.TYPES:
            warn.append(f"cold open {c['label']!r}: type {c.get('type')!r} is not one of {', '.join(projects.TYPES)} "
                        f"(the hook type plan and the run report show for its version)")
        if r is None:
            print(f"   cold open: none, label {c['label']!r} at 0.1 s [{c.get('type')}]")
            continue
        got = " ".join(w["w"] for w in ws if w["s"] >= r[0] - 0.05 and w["e"] <= r[1] + 0.05)
        lv = level(r[0]) + level(r[1])
        print(f"   cold open {r[0]:6.2f}-{r[1]:6.2f} ({r[1] - r[0]:.1f}s){lv} {c['label']!r} [{c.get('type')}]: {got}")
        for edge, nf, t in edge_flash(f, r) if x is not None else []:
            warn.append(f"cold open {r} {c['label']!r}: its {'first' if edge == 'start' else 'last'} {nf} frame(s) show "
                        f"the {'previous' if edge == 'start' else 'next'} shot (cut at ~{t} s): "
                        f"{'start just after' if edge == 'start' else 'end ~0.05 s before'} the cut, outside the words")
        for t in r:
            if inside(t) and x is None:
                warn.append(f"cold open {r} boundary {t} cuts the word {inside(t)['w']!r}")
        if not 1.8 <= r[1] - r[0] <= 7.5:
            warn.append(f"cold open {r} is {r[1] - r[0]:.1f} s")
    for a, b in ed.get("cut", []):
        pre = " ".join(w["w"] for w in ws if a - 2 <= w["s"] < a)
        post = " ".join(w["w"] for w in ws if b <= w["s"] < b + 2)
        print(f"   cut {a}-{b}{level(a)}{level(b)}: ...{pre} | {post}...")
        warn += [f"cut boundary {t} cuts {inside(t)['w']!r}" for t in (a, b) if inside(t) and x is None]
    ins = ed.get("insert_at")
    if ins is not None:
        pre = " ".join(w["w"] for w in ws if ins - 3 <= w["s"] < ins)
        post = " ".join(w["w"] for w in ws if ins <= w["s"] < ins + 3)
        print(f"   reviews at {ins}{level(ins)}: ...{pre} || {post}...")
        if inside(ins) and x is None:
            warn.append(f"insert_at {ins} cuts the word {inside(ins)['w']!r}")
    for lb in ed.get("labels", []):
        w0 = next((x for x in ws if x["s"] >= lb.get("after", 0) and x["w"].lower().strip(".,") == lb["word"]), None)
        print(f"   label {lb['text']!r} on {lb['word']!r}: {w0['s'] if w0 else 'NOT FOUND'}")
        if not w0:
            warn.append(f"label {lb['text']} word {lb['word']!r} not found after {lb.get('after')}")
    if ed.get("offer_word"):
        oa = ed.get("offer_after")
        oa = (ins or 0) - 1 if oa is None else oa
        w0 = next((x for x in ws if ed["offer_word"] in x["w"] and x["s"] >= oa), None)
        print(f"   offer card on {ed['offer_word']!r} after {oa}: {w0['s'] if w0 else 'NOT FOUND'}")
        if not w0:
            warn.append("offer word not found")
    body = body_len(ed, dur)
    print(f"   body {body:.1f} s, min_reviews {ed.get('min_reviews')} (rule {min_reviews(body)}), end {ed.get('end_title')!r}, "
          f"intro {ed.get('review_intro')}")
    if ed.get("burned_captions"):  # boundaries there follow the burned captions (checked on frames), not the audio
        notes, warn = [w for w in warn if " in speech " in w], [w for w in warn if " in speech " not in w]
        for w in notes:
            print("   note (burned captions, boundary set by the captions):", w)
    for w in warn:
        print("   WARNING:", w)
    return not warn


def show_transcript(ws):
    for a, b in sentences(ws):
        print(f"   {ws[a]['s']:6.2f}-{ws[b]['e']:6.2f}  {text(ws, a, b)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="*", help="ad name or code (or winner_raws keys with --check)")
    ap.add_argument("--id", help="Drive file id of the RAW (skips the library search)")
    ap.add_argument("--key", help="winner_raws key (default from the code, e.g. raw172_H4)")
    ap.add_argument("--product", help="product name (default: from the library folder / transcript)")
    ap.add_argument("--raw", choices=["yes", "no"], help="with --id: is the file a RAW without captions (default yes)")
    ap.add_argument("--outdir", default="/tmp/winner_prep", help="contact sheet folder")
    ap.add_argument("--write", action="store_true", help="insert the draft into winner_raws")
    ap.add_argument("--check", action="store_true", help="verify winner_raws entries against their transcripts")
    ap.add_argument("--format", action="store_true", help="rewrite winner_raws in the standard layout")
    a = ap.parse_args()
    raws = json.load(open(BANK))["winner_raws"]
    if a.format:
        write_raws(raws)
        return print(f"winner_raws rewritten ({len(raws)} entries)")
    if a.check:
        ok = [check(k, raws[k]) for k in (a.name or raws)]
        return sys.exit(0 if all(ok) else 1)
    if len(a.name) != 1:
        ap.error("give one ad name, e.g. ACH-YEVH-172-H4")
    name = a.name[0]
    if not os.path.exists(CACHE):
        subprocess.run([sys.executable, os.path.join(HERE, "index_library.py")], check=True)
    files = [i for i in json.load(open(CACHE))["items"] if i["kind"] == "file"]
    if a.id:
        known = next((i for i in files if i["id"] == a.id), None)
        fid, path = a.id, known["path"] if known else name
        raw = a.raw != "no" if a.raw or not known else is_raw(known)
    else:
        hits = match_ad(name, files)
        if not hits:
            sys.exit(f"'{name}' is not in the library index. Rebuild it (index_library.py) or pass --id.")
        fid, path, raw = hits[0]["id"], hits[0]["path"], is_raw(hits[0])
        print(f"library: {path} ({'RAW' if raw else 'edited export: burned-in captions'})  id {fid}", file=sys.stderr)
    key = a.key or default_key(*parse_code(name))
    if a.write and key in raws and not raws[key].get("draft"):
        sys.exit(f"{key} already exists and is reviewed (no 'draft'): not overwriting. Use another --key or edit it by hand.")
    local = fetch(fid)
    dur = probe_dur(local)
    ws = transcribe(local, os.path.join(TRANS, f"{key}_words.json"))
    os.makedirs(a.outdir, exist_ok=True)
    sheet = contact_sheet(local, dur, os.path.join(a.outdir, f"{key}_sheet.jpg"))
    x = load_audio(local)
    e = draft(name, fid, path, ws, dur, raw, a.product, x)
    print(f"# {key}: {path}  ({dur} s)  file {local}\n# contact sheet: {sheet}\n# transcript:")
    show_transcript(ws)
    print("# cold open candidates (hook score):")
    for c in cold_open_candidates(ws, dur, n=6, x=x):
        print(f"   {c['score']:5.1f}  {c['range']}  {c['line']}")
    print(f"# draft entry:\n{fmt_entry(key, e)}")
    if a.write:
        raws[key] = e
        write_raws(raws)
        print(f"# written to winner_raws[{key!r}] in {BANK}")


if __name__ == "__main__":
    main()

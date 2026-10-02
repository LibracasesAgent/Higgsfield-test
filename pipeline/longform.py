#!/usr/bin/env python3
"""Long-form (45-90 s) direct-response ad, built like the client's winning ads.

Pipeline: base cut (recut.py segments + voice/sfx mix, no text)  ->  word-level transcript of the
final audio (faster-whisper)  ->  phrase captions every 2-4 words with red keywords  ->  timed
overlays (number labels, review cards, offer card, end card)  ->  one high-quality encode.

  python3 pipeline/longform.py ad.json --out ad.mp4

ad.json (paths relative to the JSON):
{
  "segments": [ ...recut.py segments (src/start/dur/speed/focus/zoom/mute/fx)... ],
  "audio": "natural", "vo": "...", "vo_start": 0, "bed_gain": 1.0, "sfx": [...],      # as recut.py
  "keywords": ["number", "one", "50%", "off", "free"],      # words drawn in red (case-insensitive)
  "caption_y": 1000,  "no_captions": [[t0, t1], ...],        # caption band centre; windows to skip
  "overlays": [
    {"type": "label",  "text": "NUMBER ONE", "at": 2.3, "dur": 1.2},
    {"type": "tag",    "text": "KEYS → GOLD SIDE ZIP", "at": 20, "dur": 2.5},
    {"type": "review", "n": 7, "at": 40.0, "dur": 3.0},      # from pipeline/data/reviews.json (verbatim)
    {"type": "offer",  "title": "50% OFF", "sub": "+ FREE WALLET WITH EVERY ORDER", "at": 50, "dur": 4},
    {"type": "end",    "title": "The Hobo Bag", "sub": "Tap the link below", "at": 56, "dur": 3}
  ]
}
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recut  # noqa: E402

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
RED, INK, GOLD = (226, 30, 36), (17, 17, 17), (245, 180, 0)


def font(name, size, weight=None):
    return recut.font(name, size, weight)


# ---------- captions ----------
def words_of(path):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small.en"), device="cpu", compute_type="int8")  # small.en: fewer caption typos than base.en
    segs, _ = m.transcribe(path, word_timestamps=True)
    return [dict(w=w.word.strip(), s=w.start, e=w.end) for s in segs for w in s.words if w.word.strip()]


CAPTION_FIX = [["xa,", "X A.,"], ["have mercy,", "Mercy,"], ["ask customers", "asked customers"]]  # known whisper slips on our VO


def fix_words(words, fixes):
    """caption_fix: [["have mercy,", "Mercy:"], ["xa,", "X A.:"]]: replace whisper word runs (case-insensitive)."""
    out, i = [], 0
    while i < len(words):
        for src, dst in fixes:
            n = len(src.split())
            if [w["w"].lower() for w in words[i:i + n]] == src.lower().split():
                out += [dict(w=t, s=words[i]["s"], e=words[i + n - 1]["e"]) for t in dst.split()]
                i += n
                break
        else:
            out.append(words[i])
            i += 1
    return out


def phrases(words, max_words=4):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.?!,:]$", w["w"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for i, p in enumerate(out):
        end = out[i + 1][0]["s"] if i + 1 < len(out) else p[-1]["e"] + 0.3
        res.append(dict(words=[w["w"] for w in p], s=p[0]["s"], e=min(end, p[-1]["e"] + 0.6)))
    return res


def caption_png(path, words, keywords, y):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Montserrat.ttf", 64, "ExtraBold")
    toks = [re.sub(r"[^\w%'’-]", "", w) or w for w in words]
    merged = []                                  # whisper writes "50 %": glue the sign back on
    for t in toks:
        if t == "%" and merged:
            merged[-1] += "%"
        else:
            merged.append(t)
    toks = merged
    text = " ".join(toks).strip()
    # wrap to <= 860 px
    lines, cur = [], []
    for t in toks:
        trial = " ".join(cur + [t])
        if cur and d.textlength(trial, font=f) > 860:
            lines.append(cur)
            cur = [t]
        else:
            cur.append(t)
    lines.append(cur)
    lh = 84
    top = y - lh * len(lines) / 2
    for li, ln in enumerate(lines):
        s = " ".join(ln)
        tw = d.textlength(s, font=f)
        x0, yy = (W - tw) / 2, top + li * (lh + 10)
        d.rounded_rectangle([x0 - 26, yy - 10, x0 + tw + 26, yy + 74], radius=18, fill=(255, 255, 255, 250))
        x = x0
        for t in ln:
            col = RED if t.lower().strip("'’") in keywords else INK
            d.text((x, yy), t, font=f, fill=col + (255,))
            x += d.textlength(t + " ", font=f)
    im.save(path)
    return text


# ---------- overlays ----------
def label_png(path, o):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Montserrat.ttf", 92, "Black")
    tw = d.textlength(o["text"], font=f)
    y = o.get("y", 520)
    d.rounded_rectangle([(W - tw) / 2 - 34, y - 14, (W + tw) / 2 + 34, y + 112], radius=22, fill=RED + (255,))
    d.text(((W - tw) / 2, y), o["text"], font=f, fill=(255, 255, 255, 255))
    im.save(path)


def tag_png(path, o):
    """Item -> pocket tag: dark pill with white text, e.g. 'PASSPORT → BACK POCKET'."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Montserrat.ttf", o.get("size", 60), "ExtraBold")
    tw = d.textlength(o["text"], font=f)
    y = o.get("y", 330)
    d.rounded_rectangle([(W - tw) / 2 - 36, y - 16, (W + tw) / 2 + 36, y + f.size + 22], radius=40, fill=(20, 16, 14, 235))
    d.text(((W - tw) / 2, y), o["text"], font=f, fill=(255, 255, 255, 255))
    im.save(path)


def stars(d, x, y, size=44):
    import math
    for k in range(5):
        cx, cy, r = x + k * (size + 8) + size / 2, y + size / 2, size / 2
        pts = []
        for j in range(10):
            a = math.pi / 2 + j * math.pi / 5
            rr = r if j % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
        d.polygon(pts, fill=GOLD + (255,))


def review_png(path, o, reviews):
    r = next(x for x in reviews if x["n"] == o["n"])
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fn, ft, fs = font("Inter.ttf", 48, "Bold"), font("Inter.ttf", 44, "Regular"), font("Inter.ttf", 30, "Medium")
    words, lines, cur = r["text"].split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=ft) > 800 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    ch = 230 + 60 * len(lines)
    y0 = o.get("y", (H - ch) // 2 - 80)
    x0 = 70
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 8, y0 + 14, W - x0 + 8, y0 + ch + 14], radius=36, fill=(0, 0, 0, 90))
    from PIL import ImageFilter
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x0, y0, W - x0, y0 + ch], radius=36, fill=(255, 255, 255, 252))
    d.text((x0 + 50, y0 + 44), r["name"], font=fn, fill=INK + (255,))
    nx = x0 + 50 + d.textlength(r["name"], font=fn) + 18
    if r.get("verified"):
        d.ellipse([nx, y0 + 52, nx + 40, y0 + 92], fill=INK + (255,))
        d.line([(nx + 10, y0 + 72), (nx + 18, y0 + 81), (nx + 31, y0 + 62)], fill=(255, 255, 255, 255), width=5)
        d.text((nx + 52, y0 + 58), "Verified buyer", font=fs, fill=(90, 90, 90, 255))
    stars(d, x0 + 50, y0 + 112)
    for i, ln in enumerate(lines):
        d.text((x0 + 50, y0 + 185 + i * 60), ln, font=ft, fill=(40, 40, 40, 255))
    im.save(path)


def offer_png(path, o):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ft, fs = font("Montserrat.ttf", 170, "Black"), font("Montserrat.ttf", 50, "ExtraBold")
    y = o.get("y", 560)
    t, s = o.get("title", "50% OFF"), o.get("sub", "+ FREE WALLET WITH EVERY ORDER")
    tw, sw = d.textlength(t, font=ft), d.textlength(s, font=fs)
    bw = max(tw, sw) + 120
    d.rounded_rectangle([(W - bw) / 2, y, (W + bw) / 2, y + 330], radius=40, fill=RED + (250,))
    d.text(((W - tw) / 2, y + 30), t, font=ft, fill=(255, 255, 255, 255))
    d.rounded_rectangle([(W - sw) / 2 - 24, y + 236, (W + sw) / 2 + 24, y + 306], radius=16, fill=(255, 255, 255, 255))
    d.text(((W - sw) / 2, y + 242), s, font=fs, fill=RED + (255,))
    im.save(path)


def end_png(path, o):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ft, fs = font("CormorantGaramond.ttf", 120, "SemiBold"), font("Montserrat.ttf", 54, "ExtraBold")
    y = o.get("y", 1180)
    t, s = o.get("title", "The Hobo Bag"), o.get("sub", "Tap the link below")
    d.rectangle([0, y - 60, W, y + 330], fill=(18, 14, 12, 200))
    size = 120
    while d.textlength(t, font=ft) > W - 100 and size > 60:   # shrink long titles to fit
        size -= 6
        ft = font("CormorantGaramond.ttf", size, "SemiBold")
    tw = d.textlength(t, font=ft)
    d.text(((W - tw) / 2, y - 20), t, font=ft, fill=(250, 244, 236, 255))
    sw = d.textlength(s, font=fs)
    d.rounded_rectangle([(W - sw) / 2 - 44, y + 170, (W + sw) / 2 + 44, y + 270], radius=50, fill=RED + (255,))
    d.text(((W - sw) / 2, y + 186), s, font=fs, fill=(255, 255, 255, 255))
    im.save(path)


def build_overlay_track(events, tmp, total):
    """events: [(t0, t1, png, layer)] -> list of (png, at, dur) after resolving priority (overlays > captions)."""
    blank = os.path.join(tmp, "blank.png")
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    # sample every frame, pick the top layer active at t, merge layers by compositing when both active
    frames, n = [], int(total * FPS) + 1
    for k in range(n):
        t = k / FPS
        act = sorted([e for e in events if e[0] <= t < e[1]], key=lambda e: e[3])
        frames.append(tuple(e[2] for e in act))
    runs, cache = [], {}
    for k, key in enumerate(frames):
        if runs and runs[-1][0] == key:
            runs[-1][2] += 1
        else:
            runs.append([key, k, 1])
    lst = os.path.join(tmp, "ov.txt")
    with open(lst, "w") as fh:
        for key, k0, cnt in runs:
            if not key:
                p = blank
            elif len(key) == 1:
                p = key[0]
            else:
                p = cache.get(key)
                if not p:
                    im = Image.open(key[0]).convert("RGBA")
                    for q in key[1:]:
                        im = Image.alpha_composite(im, Image.open(q).convert("RGBA"))
                    p = os.path.join(tmp, f"mix{len(cache)}.png")
                    im.save(p)
                    cache[key] = p
            fh.write(f"file '{p}'\nduration {cnt / FPS:.5f}\n")
        fh.write(f"file '{blank}'\n")
    return lst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    e = json.load(open(a.edl))
    edl_dir = os.path.dirname(os.path.abspath(a.edl))
    tmp = tempfile.mkdtemp(prefix="longform_")

    # 1) base cut without any text
    base_edl = {k: v for k, v in e.items() if k in ("segments", "audio", "vo", "vo_start", "bed_gain", "sfx")}
    base_edl["segments"] = [{k: v for k, v in s.items() if k != "caption"} for s in e["segments"]]
    bj = os.path.join(edl_dir, "_base_edl.json")
    json.dump(base_edl, open(bj, "w"))
    base = os.path.join(tmp, "base.mp4")
    subprocess.run([sys.executable, os.path.join(HERE, "recut.py"), bj, "--out", base], check=True)
    os.remove(bj)
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base],
                                 capture_output=True, text=True).stdout)

    # 2) captions from the final audio
    events = []
    kw = {k.lower() for k in e.get("keywords", [])}
    skip = e.get("no_captions", [])
    for i, p in enumerate(phrases(fix_words(words_of(base), CAPTION_FIX + e.get("caption_fix", [])), e.get("max_words", 4))):
        if any(s0 <= p["s"] < s1 for s0, s1 in skip):
            continue
        png = os.path.join(tmp, f"cap{i:03d}.png")
        caption_png(png, p["words"], kw, e.get("caption_y", 1000))
        events.append((p["s"], p["e"], png, 1))

    # 3) overlays
    reviews = json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]
    for j, o in enumerate(e.get("overlays", [])):
        png = os.path.join(tmp, f"ov{j:02d}.png")
        {"label": label_png, "offer": offer_png, "end": end_png, "tag": tag_png}.get(o["type"], lambda p, o: review_png(p, o, reviews))(png, o)
        events.append((o["at"], o["at"] + o["dur"], png, 2))

    lst = build_overlay_track(events, tmp, total)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", base, "-f", "concat", "-safe", "0", "-i", lst,
                    "-filter_complex", "[1:v]fps=30,format=rgba[o];[0:v][o]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-maxrate", "14M",
                    "-bufsize", "28M", "-r", "30", "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", "-y", a.out],
                   check=True, timeout=3600)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2), captions=sum(1 for x in events if x[3] == 1),
                          overlays=len(e.get("overlays", [])))))


if __name__ == "__main__":
    main()

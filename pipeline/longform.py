#!/usr/bin/env python3
"""Long-form (45-90 s) direct-response ad, built like the client's winning ads.

Pipeline: base cut (recut.py segments + voice/sfx mix, no text)  ->  word-level transcript of the
final audio (faster-whisper)  ->  timed overlays (number labels, tags, review cards, offer card, end card)  ->
captions placed clear of them  ->  one high-quality encode. The words come from the EDL's "transcript" when the engine
knows them (storyboard: the script on its voiceover's timings; remix: the RAW's committed transcript), else whisper.

Captions (like the top Reels ads): up to 8 words (9 for a whole sentence) on at most 2 balanced lines, broken at
sentence ends, commas and pauses (never "hand making these / bags", never "the Black / Friday deal", one word alone only
as a whole sentence), at least 0.8 s on screen, no dashes or stray symbols. They look like part of the video (white
text, dark outline, soft shadow, keywords on a red pill; "caption_style": "box" = the older white boxes) and sit in the
bottom band (centre y 1380, text ~1295-1465: above Stories' UI, inside Feed's 4:5 crop; "caption_zone": "reels" keeps
them above Meta's strict Reels zone, ~1065-1235). A shot whose bottom band shows something important (a face, or the
product / the action: spectral-residual saliency) gets its captions in the emptiest of the top band or just above the
product instead (never over a face), for that shot only
("caption_pos": "top" / "bottom" on a segment forces it; "caption_auto": false turns the check off). They move up or
down while an overlay would be under them; no caption over the end card (it carries the CTA): one mostly under it is
left out, one that runs into it ends where the card starts. The opening line stays one caption (<= 10 words, at 52 px
when 60 px is too wide for two lines).

  python3 pipeline/longform.py ad.json --out ad.mp4

ad.json (paths relative to the JSON):
{
  "segments": [ ...recut.py segments (src/start/dur/speed/focus/zoom/mute/fx)...,
                {..., "caption_pos": "top"} ],                # captions in the upper area while this segment plays
  "audio": "natural", "vo": "...", "vo_start": 0, "bed_gain": 1.0, "sfx": [...],      # as recut.py
  "keywords": ["number", "one", "50%", "off", "free"],      # words drawn in red (case-insensitive)
  "caption_top": [[t0, t1], ...],                            # windows with captions in the upper area (briefly)
  "no_captions": [[t0, t1], ...],                            # windows without captions
  "breaks": [t, ...],                                        # block / speaker changes: no caption runs across one
  "transcript": [{"w": "Take", "s": 0.1, "e": 0.3, "k": "script"}, ...],   # the words said (ad seconds); else whisper
                                                             # a word may carry "pre": "1." (storyboard ugc chapter number):
                                                             # shown before it in the same caption ("1. you stop worrying")
  "caption_words": 7,                                        # max words per caption
  "caption_fix": [["have mercy,", "Mercy,"]],                # whisper slips (+ CAPTION_FIX)
  "caption_y": 1000, "caption_y_force": true,                # old fixed caption centre: used only with caption_y_force
                                                             # (older EDLs always wrote caption_y and max_words: ignored)
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
import time

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recut  # noqa: E402

W, H, FPS = 1080, 1920, 30
try:
    from PIL import features as _pf
    FEAT = {"features": ["lnum"]} if _pf.check("raqm") else {}   # lining figures in Cormorant titles ('Hobo 2.0')
except ImportError:
    FEAT = {}
HERE = os.path.dirname(os.path.abspath(__file__))
RED, INK, GOLD = (226, 30, 36), (17, 17, 17), (245, 180, 0)


def font(name, size, weight=None):
    return recut.font(name, size, weight)


# ---------- captions ----------
def words_of(path):
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small.en"), device="cpu", compute_type="int8")  # small.en: fewer caption typos than base.en
    segs, _ = m.transcribe(path, word_timestamps=True, condition_on_previous_text=False)  # True can silently drop a closing sentence
    return [dict(w=w.word.strip(), s=w.start, e=w.end) for s in segs for w in s.words if w.word.strip()]


CAPTION_FIX = [["2 .0", "2.0"], ["2 .0?", "2.0?"], ["2 .0.", "2.0."], ["xa,", "X A.,"], ["have mercy,", "Mercy,"], ["ask customers", "asked customers"],
               ["Libra -Hobo", "Libra Hobo"], ["phobo", "Hobo"]]  # known whisper slips (our VO, the clips' transcripts)


def fix_known(words, fixes):
    """fix_words on the words a transcript gave (whisper's slips), never on a script's own words (k == 'script')."""
    out, run = [], []
    for w in words + [None]:
        if w is None or w.get("k") == "script":
            out += fix_words(run, fixes) if run else []
            run = []
            if w is not None:
                out.append(w)
        else:
            run.append(w)
    return out


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


# Caption layout, like the top Reels ads: low in the 9:16 safe zone (Meta Reels keeps the top ~14 % and the bottom ~35 %
# clear of text, Stories the bottom ~20 %), fuller phrases on at most two balanced lines, each on screen long enough to read.
CAP_SIZE, CAP_MAXW, CAP_ONE_LINE = 60, 840, 700   # Montserrat ExtraBold px; max line width; wider phrases take two lines
CAP_LINE_H, CAP_GAP = 80, 10                      # one boxed line; gap between the two lines
CAP_Y, CAP_Y_TOP = 1380, 430                      # default caption centre: the bottom band (2 lines ~1295-1465); "top": upper band
SAFE_TOP, SAFE_BOTTOM = 270, 1500                 # caption text stays between these rows (Stories UI: bottom ~20 % = below 1536;
#                                                   Feed's 4:5 crop keeps rows 285-1635)
ZONES = {"bottom": (CAP_Y, SAFE_BOTTOM), "reels": (1150, 1250)}   # EDL "caption_zone": "reels" = Meta's strict Reels zone
#                                                   (its UI covers the bottom ~35 %): captions sit higher, at ~1065-1235
CAP_MARGIN = 24                                   # clear rows between a caption and an overlay (label, tag, card)
CAP_WORDS, CAP_MIN_S, CAP_HOLD = 8, 0.8, 0.6      # words per caption; min seconds on screen; hold after the last word
HOOK_WORDS, HOOK_SIZE = 10, 52                    # the opening line stays one caption up to this many words (at HOOK_SIZE
#                                                   px when it is too wide for two lines at CAP_SIZE)
NO_END = set(("a an the of to for with and or but nor so as than if then plus your my her his its their our these those "
              "in on at by from into onto about over under after before until without through during since across around "
              "can will would could should "
              "not no i we she he they it's that's there's here's what's who's let's i'm you're we're they're "
              "every each some any very just more most you've we've they've i've i'd you'd we'd they'd she'd he'd "
              "depending according").split())   # never the last word of a caption or a line
SOFT_END = set("this that all is are was were be been am has have had do does did".split())   # "buy this", "it has": rather not
NO_START = set("it them him me us too up off out of".split())       # never the first word ("wear / it", "50% / off")
AUX = set("can can't will won't would could should is are was were have has had do don't does did 'll".split())
SUBJ = set("i you we they she he it".split())
CLAUSE = set("i you we they she he i've you've we've they've i'm you're we're they're she's he's".split())   # a clause
#                                                       starts here: "the Black Friday deal / you've been waiting for"
NUMS = set("one two three four five six seven eight nine ten twenty thirty forty fifty sixty hundred".split())
MODS = set(("great new old last other first next best little big small whole same own wonderful beautiful perfect real "
            "true favourite favorite luxury leather soft hidden secret only entire extra free matching single double "
            "brand").split())                     # rather not end a line on a modifier: "this great / new purse"
LINK = set("look looks looked feel feels felt seem seems get gets got become becomes stay stays".split())   # "look / terrible"
LEADS = set(("for with without to in on at from into through during since across around about and but or so because "
             "that which who when while if as than like after before until plus").split())   # a new phrase starts here: a fine break
DETS = set("the a an your my her his our their every each".split())   # a noun phrase starts here: an ok break
DASH = re.compile(r"[‒-―]|-{2,}")                     # figure/en/em dashes, '--': a pause, never shown
QUOTES = "\"'‘’“”"


def clean_word(t):
    """Caption text of one word: letters, digits, %, $, &, #1, apostrophes, in-word hyphens and slashes, number points
    ('2.0', '1,400'); no dashes, quotes, brackets or other stray symbols, no punctuation (cap_words keeps that apart)."""
    t = re.sub(r"(?<=\d)([.,])(?=\d)", lambda m: "\x01" if m.group(1) == "." else "\x02", DASH.sub("", t))
    t = re.sub(r"(?<=\w)/(?=\w)", "\x03", re.sub(r"#(?=\d)", "\x04", t))
    t = re.sub(r"[^\w%$&'’\x01-\x04-]|_", "", t).strip("-").lstrip("'’")
    if t[-1:] in "'’" and not t[-2:-1] in ("s", "S"):     # a closing quote, not "customers'"
        t = t.rstrip("'’")
    return t.replace("\x01", ".").replace("\x02", ",").replace("\x03", "/").replace("\x04", "#")


def stop(raw):
    """(strength, mark) of the punctuation ending a whisper word: strength 2 sentence end, 1 clause (comma, colon, dash,
    '...'), 0 none; mark is what a caption may show after the word (',', ':', '.', '?', '!' or '')."""
    raw = raw.rstrip(QUOTES + ")]")
    if re.search(r"(\.\.\.|…)$", raw):
        return 1, ""
    if re.search(r"([‒-―]|-)$", raw):
        return 1, ","
    m = re.search(r"[,;:.?!]$", raw)
    if not m:
        return 0, ""
    c = {";": ","}.get(m.group(0), m.group(0))
    return (2 if c in ".?!" else 1), c


def cap_words(words):
    """Whisper words -> caption words dict(t=text, m=punctuation mark, p=stop strength, s, e): '%' glued to its number,
    'go' + '-to' glued, a word with a dash inside split in two (the dash is a pause), dash-only and symbol-only tokens
    dropped (the word before gets the pause)."""
    out = []
    for w in words:
        prev = out[-1] if out else None
        if prev and (w["w"].startswith("%") or re.match(r"-\w", w["w"]) and not prev["p"] and w["s"] - prev["e"] < 0.05):
            p, m = stop(w["w"])                               # whisper writes "50 %" and "go -to"
            tail = "%" if w["w"].startswith("%") else "-" + clean_word(w["w"])
            out[-1] = dict(prev, t=prev["t"] + tail, p=max(prev["p"], p), m=m or prev["m"], e=w["e"])
            continue
        parts = DASH.split(re.sub(r"(?<=\d)[‒-―](?=\d)", "-", w["w"]))   # "2–3" stays "2-3"
        span, n = w["e"] - w["s"], sum(len(x) for x in parts) or 1
        t0 = w["s"]
        for k, raw in enumerate(parts):
            t1 = w["e"] if k == len(parts) - 1 else t0 + span * len(raw) / n
            p, m = stop(raw) if k == len(parts) - 1 else (1, ",")
            txt = clean_word(raw)
            if txt:
                if k == 0 and w.get("pre"):                       # chapter number ("1."): its own token, no stop, no time
                    out.append(dict(t=w["pre"], m="", p=0, s=round(t0, 3), e=round(t0, 3)))
                out.append(dict(t=txt, m=m, p=p, s=round(t0, 3), e=round(t1, 3)))
            elif out and p and not out[-1]["p"]:
                out[-1].update(p=p, m=m)
            t0 = t1
    return out


_MEASURE = {}


def cap_font(size=CAP_SIZE):
    return font("Montserrat.ttf", size, "ExtraBold")


def text_w(s, size=CAP_SIZE):
    if size not in _MEASURE:
        _MEASURE[size] = (ImageDraw.Draw(Image.new("RGBA", (8, 8))), cap_font(size))
    d, f = _MEASURE[size]
    return d.textlength(s, font=f)


def nude(t):
    return t.lower().replace("’", "'").rstrip(",:.?!").strip("'")


def end_cost(a, b):
    """Cost of a caption or line ending between words a and b (no punctuation between): never after 'the' / 'your' /
    'can', rather not after 'is' / 'this' (fine when a new phrase starts: "buy this / because"), never before 'it' /
    'off' / 'of', never between 'you' and 'can' or '3' and 'reasons'."""
    x, y = nude(a["t"]), nude(b["t"])
    return ((4 if x in NO_END else 1.5 if x in SOFT_END and y not in LEADS else 0) + (2.5 if y in NO_START else 0) +
            (3 if x in SUBJ and y in AUX else 0) +                                   # "and you / can wear it"
            (3 if (x in NUMS or x.rstrip("%").isdigit()) and y not in LEADS else 0) +   # "here are 3 / reasons"
            (2 if (x in MODS or x in LINK) and y not in LEADS and y not in NO_END else 0))   # "my other / purse"


def name_pair(a, b):
    """'Vintage Bag', 'Hobo 2.0': two words of one name (never split over two lines or two captions)."""
    return not a["p"] and a["t"][:1].isupper() and nude(a["t"]) != "i" and (b["t"][:1].isupper() or b["t"][:1].isdigit())


def shown(line):
    """Text of one caption line: punctuation kept inside the line, at its end only '?' and '!' (the break is the pause)."""
    return [w["t"] + (w["m"] if k < len(line) - 1 or w["m"] in "?!" else "") for k, w in enumerate(line)]


def cap_lines(p, size=CAP_SIZE):
    """Caption words -> (lines of shown words, score): one line when it is short, else two balanced lines broken at
    punctuation or a pause, never after 'the' / 'these', never before 'it' / 'off' and never one word alone on a line
    ("hand making / these bags"). None: too wide for two lines (at `size` px)."""
    one = shown(p)
    full = text_w(" ".join(one), size)
    if full <= CAP_ONE_LINE or (len(p) <= 4 and full <= CAP_MAXW) or len(p) == 1:
        return [one], 0.0
    best = None
    for k in range(1, len(p)):
        l1, l2 = shown(p[:k]), shown(p[k:])
        w1, w2 = text_w(" ".join(l1), size), text_w(" ".join(l2), size)
        if max(w1, w2) > CAP_MAXW:
            continue
        sc = abs(w1 - w2) / 200
        if not p[k - 1]["p"]:
            sc += end_cost(p[k - 1], p[k]) * 2
        sc += 5 if name_pair(p[k - 1], p[k]) else 0                # never "the Black / Friday deal"
        sc += (1.5 if k == 1 and p[0]["p"] else 4.5) if k == 1 or len(p) - k == 1 else 0   # one word alone on a line
        #                                                         ("Inside, / divided compartments" is fine)
        sc -= (3 if p[k - 1]["p"] == 2 else 2 if p[k - 1]["p"] else 0.8 if p[k]["s"] - p[k - 1]["e"] >= 0.3 or
               nude(p[k]["t"]) in LEADS | DETS else 0)
        if best is None or sc < best[1]:
            best = ([l1, l2], sc)
    if full <= CAP_MAXW and (best is None or best[1] >= 3):       # no good break: one (wide) line
        return [one], 1.0
    return (best[0], max(best[1], 0.0)) if best else None


SIZE_COST = {1: 6.0, 2: 1.2, 3: 0.5, 4: 0.1, 5: 0.0, 6: 0.0, 7: 0.2, 8: 0.4, 9: 0.7}     # one word alone flashes by: only a whole sentence


def cap_cost(u, i, j):
    """Cost of showing u[i:j] as one caption (None: does not fit two lines). Prefers 4-6 words, an end at a sentence
    end, comma or pause (or before 'for' / 'because' ...), never ends on 'the' / 'your' ..., never starts with 'it' /
    'off', never splits 'Vintage Bag', never runs across a sentence end or a long pause, and keeps the caption on screen
    at least CAP_MIN_S (too-fast fragments merge)."""
    p, last, n = u[i:j], u[j - 1], len(u)
    lay = cap_lines(p)
    if lay is None:
        return None
    whole = last["p"] and (i == 0 or u[i - 1]["p"])                 # a whole clause: "Not worse." "Shop now."
    sent = last["p"] == 2 and (i == 0 or u[i - 1]["p"] == 2)         # a whole sentence ("Ooh." "Brown.")
    c = 0.5 + (0.6 if j - i == 1 and sent else SIZE_COST.get(j - i, 0.4) * (0.5 if whole else 1)) + lay[1]
    if j < n:
        gap, lead = u[j]["s"] - last["e"], nude(u[j]["t"])
        c += (0 if last["p"] == 2 else 1.2 if last["p"] and lead in ("and", "or") else 0.4 if last["p"] or gap >= 0.45
              else 1.2 if gap >= 0.25 else 1.5 if lead in LEADS else 2.0 if lead in CLAUSE
              else 2.5 if lead in DETS or lead.endswith("ing") else 5.0)   # ", and keys": the list goes on
        if not last["p"]:
            c += end_cost(last, u[j]) + (3 if name_pair(last, u[j]) else 0)
    for k in range(len(p) - 1):
        c += (3.5 if p[k]["p"] == 2 else 0) + (5 if p[k + 1]["s"] - p[k]["e"] > 0.7 else 0)
    on = (u[j]["s"] if j < n else last["e"] + CAP_HOLD) - p[0]["s"]
    return c + max(0.0, CAP_MIN_S - on) * 6 + max(0.0, 0.5 - on) * 20 + max(0.0, last["e"] - p[0]["s"] - 3.6) * 3


def split_unit(u, max_words):
    """Cheapest split of one stretch of speech (no break inside) into captions (dynamic programming over cap_cost)."""
    n, inf = len(u), float("inf")
    best, back = [0.0] + [inf] * n, [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - max_words - 1), j):
            if j - i > max_words and not (u[j - 1]["p"] == 2 and (i == 0 or u[i - 1]["p"] == 2)):
                continue                  # one more word only for a whole sentence
            c = cap_cost(u, i, j) if best[i] < inf else None
            if c is not None and best[i] + c < best[j]:
                best[j], back[j] = best[i] + c, i
    cuts, j = [], n
    while j > 0:
        cuts.append((back[j], j))
        j = back[j]
    return [u[i:j] for i, j in reversed(cuts)]


def phrases(words, max_words=CAP_WORDS, breaks=()):
    """Caption phrases: up to max_words words on at most two lines, never across a break (a block / speaker change).
    -> [dict(words, lines, s, e)]: on screen from the first word until the next caption (at least CAP_MIN_S, held
    CAP_HOLD after the last word, not past the next break unless that is needed for CAP_MIN_S)."""
    units, cur = [], []
    for w in cap_words(words):
        if cur and any(cur[-1]["s"] < b - 0.15 <= w["s"] for b in breaks):
            units.append(cur)
            cur = []
        cur.append(w)
    if cur:
        units.append(cur)
    groups, size = [], {}
    for k, u in enumerate(units):     # the hook (the first stretch) stays one caption when it fits (a little smaller
        hook = k == 0 and len(u) <= HOOK_WORDS and u[-1]["e"] - u[0]["s"] <= 4.5 and \
            not any(w["p"] == 2 for w in u[:-1])     # when it must): never "the Black / Friday deal you've been waiting for"
        sz = next((z for z in (CAP_SIZE, HOOK_SIZE) if cap_lines(u, z) is not None), None) if hook else None
        if sz:
            size[len(groups)] = sz
            groups.append(u)
        else:
            groups += split_unit(u, max_words)
    res = []
    for i, p in enumerate(groups):
        s, last = p[0]["s"], p[-1]
        e = last["e"] + CAP_HOLD
        nb = min([b for b in breaks if b - 0.15 > last["s"]], default=None)
        if nb is not None:
            e = min(e, max(nb, last["e"] + 0.1))
        e = max(e, s + CAP_MIN_S)
        if i + 1 < len(groups):
            nxt = groups[i + 1][0]["s"]
            e = nxt if nxt - e < 0.25 else min(e, nxt)            # no blink between two captions
        sz = size.get(i, CAP_SIZE)
        res.append(dict(words=[w["t"] for w in p], lines=cap_lines(p, sz)[0], s=s, e=e, **({"size": sz} if sz != CAP_SIZE else {})))
    return res


def caption_png(path, lines, keywords, cy, size=CAP_SIZE, style="native"):
    """Caption lines centred on row cy. style "native" (default, like Reels/TikTok captions: part of the video, no box):
    white text with a dark outline and a soft shadow, keywords white on a red pill. style "box": white boxes, ink text,
    red keywords (the older look). -> the text shown."""
    from PIL import ImageFilter
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = cap_font(size)
    lh, gap = line_h(size)
    top = cy - cap_height(len(lines), size) / 2
    _, ga, _, gd = f.getbbox("Hg", anchor="ls")
    base = (lh - (gd - ga)) / 2 - ga + 1                          # baseline: caps and descenders centred in the line
    sw = max(3, round(size / 11))                                 # outline width
    if style == "native":                                         # soft shadow under the whole caption first
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for li, ln in enumerate(lines):
            s_ = " ".join(ln)
            x0, yy = (W - d.textlength(s_, font=f)) / 2, top + li * (lh + gap)
            sd.text((x0 + 3, yy + base + 5), s_, font=f, fill=(0, 0, 0, 150), anchor="ls", stroke_width=sw + 2,
                    stroke_fill=(0, 0, 0, 150))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
        d = ImageDraw.Draw(im)
    for li, ln in enumerate(lines):
        s_ = " ".join(ln)
        tw = d.textlength(s_, font=f)
        x0, yy = (W - tw) / 2, top + li * (lh + gap)
        if style != "native":
            d.rounded_rectangle([x0 - 26, yy, x0 + tw + 26, yy + lh], radius=18, fill=(255, 255, 255, 250))
        x = x0
        for t in ln:
            key = nude(t) in keywords
            if style == "native":
                if key:
                    d.rounded_rectangle([x - 12, yy + 4, x + d.textlength(t, font=f) + 12, yy + lh - 4], radius=14,
                                        fill=RED + (255,))
                    d.text((x, yy + base), t, font=f, fill=(255, 255, 255, 255), anchor="ls")
                else:
                    d.text((x, yy + base), t, font=f, fill=(255, 255, 255, 255), anchor="ls", stroke_width=sw,
                           stroke_fill=(20, 20, 20, 255))
            else:
                d.text((x, yy + base), t, font=f, fill=(RED if key else INK) + (255,), anchor="ls")
            x += d.textlength(t + " ", font=f)
    im.save(path)
    return " / ".join(" ".join(ln) for ln in lines)


def line_h(size=CAP_SIZE):
    """(boxed line height, gap between lines) at caption size `size`."""
    return round(CAP_LINE_H * size / CAP_SIZE), round(CAP_GAP * size / CAP_SIZE)


def cap_height(nlines, size=CAP_SIZE):
    lh, gap = line_h(size)
    return nlines * lh + (nlines - 1) * gap


def cap_centre(h, pref, blocked, lo=SAFE_TOP, hi=SAFE_BOTTOM):
    """Centre row for a caption box of height h: the one nearest pref that keeps the box between rows lo and hi and
    CAP_MARGIN clear of every blocked (top, bottom) row range. None: no room."""
    def free(c):
        return lo - 0.5 <= c - h / 2 and c + h / 2 <= hi + 0.5 and all(
            c + h / 2 + CAP_MARGIN <= a + 0.5 or c - h / 2 - CAP_MARGIN >= b - 0.5 for a, b in blocked)
    cands = [pref, min(max(pref, lo + h / 2), hi - h / 2)] + [a - CAP_MARGIN - h / 2 for a, _ in blocked] + \
        [b + CAP_MARGIN + h / 2 for _, b in blocked]
    ok = [c for c in cands if free(c)]
    return min(ok, key=lambda c: abs(c - pref)) if ok else None


def alpha_rows(png):
    """(top, bottom) rows an overlay PNG covers (alpha > 40), or None when it is empty."""
    a = Image.open(png).getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    return (a[1], a[3]) if a else None


def top_windows(e):
    """Windows where captions go to the upper area: EDL "caption_top": [[t0, t1], ...] plus segments with
    "caption_pos": "top" (something important low in the frame)."""
    win, t = [list(map(float, w)) for w in e.get("caption_top", [])], 0.0
    for s in e["segments"]:
        if s.get("caption_pos") == "top":
            win.append([t, t + float(s["dur"])])
        t += float(s["dur"])
    return win


def spot_windows(e, spots):
    """[(t0, t1, centre)] for the shots caption_spots() moved (a segment with "caption_pos" set keeps its own)."""
    win, t = [], 0.0
    for k, s in enumerate(e["segments"]):
        if k in spots and not s.get("caption_pos"):
            win.append((t, t + float(s["dur"]), spots[k]))
        t += float(s["dur"])
    return win


def saliency(gray):
    """Spectral-residual saliency (Hou & Zhang 2007) of a small grayscale frame, normalised to mean 1."""
    import cv2
    import numpy as np
    sm = cv2.resize(gray, (64, 114)).astype(np.float32)
    F = np.fft.fft2(sm)
    la = np.log(np.abs(F) + 1e-6)
    r = la - cv2.blur(la, (3, 3))
    m = np.abs(np.fft.ifft2(np.exp(r + 1j * np.angle(F)))) ** 2
    m = cv2.GaussianBlur(m.astype(np.float32), (9, 9), 2.5)
    m = cv2.resize(m, (gray.shape[1], gray.shape[0]))
    return m / (m.mean() + 1e-9)


SPOTS = [(1380, 0.75), (430, 0.9), (1150, 1.0)]   # caption centres a shot may use: bottom (preferred), top, low-middle


def caption_spots(base, e, default_y=CAP_Y):
    """{segment index: caption centre} for shots where the default bottom band would cover something important. Per
    shot (3 frames a second, majority vote) each spot's band is scored by its saliency (spectral residual: the product,
    hands, the action) times a preference (bottom 0.75, top 0.9, low-middle 1.0); a band over a face's eyes, nose or
    mouth (YuNet box below its top quarter) is never used. A shot moves only when another spot is clearly emptier than the bottom (score < 0.8x and the bottom is busy).
    Needs opencv; without it nothing moves (captions stay at the bottom)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {}
    w_, h_ = 360, 640
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", base, "-vf", f"fps=3,scale={w_}:{h_}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    n = len(raw) // (w_ * h_ * 3)
    if not n:
        return {}
    frames = np.frombuffer(raw[:n * w_ * h_ * 3], np.uint8).reshape(n, h_, w_, 3)
    det = None
    model = os.path.join(HERE, "assets", "models", "face_detection_yunet_2023mar.onnx")
    if os.path.exists(model) and hasattr(cv2, "FaceDetectorYN"):
        det = cv2.FaceDetectorYN.create(model, "", (w_, h_), 0.75, 0.3, 50)
    sy = h_ / H
    spots = [(c, b) for c, b in SPOTS if c != default_y] + [(default_y, 0.75)]
    rows = {c: (int((c - 95) * sy), int((c + 95) * sy)) for c, _ in spots}
    shots, t = [], 0.0
    for k, sg in enumerate(e["segments"]):
        shots.append((k, t, float(sg["dur"]), sg.get("src")))
        t += float(sg["dur"])
    pick_of = {}
    for k, t, d_, _ in shots:
        idx = [i for i in range(n) if t + 0.15 <= i / 3.0 < t + d_ - 0.1] or [min(int((t + d_ / 2) * 3), n - 1)]
        votes = {}
        for i in idx:
            fr = frames[i]
            faces = []
            if det is not None:
                _, fs = det.detect(fr)                       # eyes, nose, mouth: below the top quarter of the box
                faces = [(f[1] + 0.25 * f[3], f[1] + f[3]) for f in (fs if fs is not None else [])]
            sal = saliency(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY))
            score = {}
            for c, bias in spots:
                a, b = rows[c]
                if any(y1 > a and y0 < b for y0, y1 in faces):
                    continue
                score[c] = float(sal[a:b].mean()) * bias
            if default_y not in score:                           # a face where the caption would be: move it
                pick = min(score, key=score.get) if score else default_y
            else:
                best = min(score, key=score.get)
                pick = best if best != default_y and score[default_y] >= 0.8 and score[best] < 0.8 * score[default_y] \
                    else default_y
            votes[pick] = votes.get(pick, 0) + 1
        c = max(votes, key=votes.get)
        pick_of[k] = c if votes[c] * 2 > len(idx) else default_y
    # no jumping back and forth: a short shot (< 3 s) between two moved shots of the same source moves with them
    for j in range(1, len(shots) - 1):
        k, _, d_, src = shots[j]
        a, b = shots[j - 1], shots[j + 1]
        if pick_of[k] == default_y and d_ < 3.0 and a[3] == src == b[3] and pick_of[a[0]] == pick_of[b[0]] != default_y:
            pick_of[k] = pick_of[a[0]]
    return {k: c for k, c in pick_of.items() if c != default_y}


def bare(s):
    return re.sub(r"[^a-z0-9% ]", "", s.lower()).split()


def caption_events(e, words, ovs, tmp, spots=None):
    """Caption PNG events [(t0, t1, png, 1)] + stats. ovs: [(t0, t1, overlay dict, rows)]. Each caption sits in the
    bottom band (or the top band in "caption_top" windows and busy shots, or caption_y with "caption_y_force"), moved
    up or down to keep clear of every overlay on screen with it; no caption over the end card."""
    kw = {k.lower() for k in e.get("keywords", [])}
    skip, tops, moved = e.get("no_captions", []), top_windows(e), spot_windows(e, spots or {})
    forced = e.get("caption_y_force") and e.get("caption_y") is not None
    zy, zhi = ZONES.get(e.get("caption_zone", "bottom"), ZONES["bottom"])
    base_y = float(e["caption_y"]) if forced else zy
    lo, hi = (0, H) if forced else (SAFE_TOP, zhi)
    style = e.get("caption_style", "native")
    events, st = [], dict(captions=0, caption_moved=0, caption_top=0, caption_hidden=0, caption_dropped=0)
    for i, p in enumerate(phrases(words, int(e.get("caption_words", CAP_WORDS)), e.get("breaks", []))):
        if any(s0 <= p["s"] < s1 for s0, s1 in skip):
            continue
        span = p["e"] - p["s"]
        # the end card (it carries the CTA and sits where the captions are): no caption over it. One mostly under it is
        # left out; one that only runs into it ends where the card starts (never pushed up to mid-screen)
        ends = [t0 for t0, t1, o, rows in ovs if o["type"] == "end" and min(t1, p["e"]) - max(t0, p["s"]) > 0.05]
        if ends and (min(ends) - p["s"] < max(span / 2, 0.5)):
            st["caption_dropped"] += 1
            continue
        if ends:
            p = dict(p, e=min(ends))
            span = p["e"] - p["s"]
        top = any(t0 <= p["s"] < t1 or min(t1, p["e"]) - max(t0, p["s"]) >= span / 2 for t0, t1 in tops)
        live = [(o, rows) for t0, t1, o, rows in ovs if rows and min(t1, p["e"]) - max(t0, p["s"]) > 0.05]
        mv = [(min(t1, p["e"]) - max(t0, p["s"]), c) for t0, t1, c in moved if min(t1, p["e"]) - max(t0, p["s"]) > 0]
        mv = max(mv) if mv else None                 # the shot under most of this caption moved its captions
        pref = CAP_Y_TOP if top else (mv[1] if mv and mv[0] >= span / 2 and not forced else base_y)
        top = top or pref < H / 2
        cy = cap_centre(cap_height(len(p["lines"]), p.get("size", CAP_SIZE)), pref, [r for _, r in live], lo, hi)
        if cy is None:
            st["caption_hidden"] += 1
            print(f"caption hidden (no room next to the overlays) at {p['s']:.2f}s: {' '.join(p['words'])}", file=sys.stderr)
            continue
        png = os.path.join(tmp, f"cap{i:03d}.png")
        caption_png(png, p["lines"], kw, cy, p.get("size", CAP_SIZE), style)
        events.append((p["s"], p["e"], png, 1))
        st["captions"] += 1
        st["caption_top"] += top
        st["caption_moved"] += abs(cy - pref) > 1
    return events, st


# ---------- overlays ----------
def label_png(path, o):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 92
    f = font("Montserrat.ttf", size, "Black")
    tw = d.textlength(o["text"], font=f)
    while tw > W - 140 and size > 48:          # long labels shrink to fit the frame
        size -= 4
        f = font("Montserrat.ttf", size, "Black")
        tw = d.textlength(o["text"], font=f)
    y = o.get("y", 520) + (92 - size) // 2
    d.rounded_rectangle([(W - tw) / 2 - 34, y - 14, (W + tw) / 2 + 34, y + int(size * 1.22)], radius=22, fill=RED + (255,))
    d.text(((W - tw) / 2, y), o["text"], font=f, fill=(255, 255, 255, 255))
    im.save(path)


def tag_png(path, o):
    """Item -> pocket tag: dark pill with white text, e.g. 'PASSPORT → BACK POCKET'."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = o.get("size", 60)
    f = font("Montserrat.ttf", size, "ExtraBold")
    tw = d.textlength(o["text"], font=f)
    while tw > W - 150 and size > 36:          # long tags shrink to fit the frame
        size -= 3
        f = font("Montserrat.ttf", size, "ExtraBold")
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
    """Red offer card. Long titles like "BLACK FRIDAY 50% OFF" become a small kicker line + "50% OFF"."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fs = font("Montserrat.ttf", 50, "ExtraBold")
    y = o.get("y", 560)
    t, s = o.get("title", "50% OFF"), o.get("sub", "+ FREE WALLET WITH EVERY ORDER")
    kicker = ""
    ft = font("Montserrat.ttf", 170, "Black")
    m = re.search(r"\d+%", t)
    if d.textlength(t, font=ft) > W - 200 and m and m.start():           # "BLACK FRIDAY 60% OFF": kicker + "60% OFF"
        kicker, t = t[:m.start()].strip(" :-·"), t[m.start():]
    size = 170
    while d.textlength(t, font=ft) > W - 200 and size > 90:
        size -= 10
        ft = font("Montserrat.ttf", size, "Black")
    fk = font("Montserrat.ttf", 64, "Black")
    kh = 84 if kicker else 0
    tw, sw = d.textlength(t, font=ft), d.textlength(s, font=fs)
    kw = d.textlength(kicker, font=fk) if kicker else 0
    bw = min(max(tw, sw, kw) + 120, W - 40)
    d.rounded_rectangle([(W - bw) / 2, y, (W + bw) / 2, y + (330 if s else 236) + kh], radius=40, fill=RED + (250,))
    if kicker:
        d.text(((W - kw) / 2, y + 26), kicker, font=fk, fill=(255, 255, 255, 255))
    d.text(((W - tw) / 2, y + 30 + kh + (170 - size) // 2), t, font=ft, fill=(255, 255, 255, 255))
    if s:                                             # no sub (no gift): title only, no empty white pill
        d.rounded_rectangle([(W - sw) / 2 - 24, y + 236 + kh, (W + sw) / 2 + 24, y + 306 + kh], radius=16,
                            fill=(255, 255, 255, 255))
        d.text(((W - sw) / 2, y + 242 + kh), s, font=fs, fill=RED + (255,))
    im.save(path)


def end_png(path, o):
    """The closing card, a full opaque frame (Julian 2026-10-21: the grey band over a product-page collage "looks off"): with a
    studio packshot (`photo`, an absolute path) it is the studio static in 9:16: the real bag large on a calm tinted backdrop, the
    wordmark, the product's name, the offer pill (`offer`, when there is one) and a button; without one a plain espresso card with the
    name and the button. Everything sits between Meta's top header (260 px) and the Reels caption / button zone (the lowest 380 px)."""
    t, s = o.get("title", "The Hobo Bag"), o.get("sub", "Tap the link below")
    ph = o.get("photo")
    if ph and os.path.exists(ph):
        try:
            import brand_statics as bs
            c = bs.l_studio(dict(size=[W, H], photo=os.path.basename(ph), caption=t, badge=o.get("offer") or "", cta=s, top=260, bottom=400,
                                 hsize=76), os.path.dirname(ph))
            c.convert("RGBA").save(path)
            return
        except Exception as e:  # noqa: BLE001  (a card must always be made: the plain one below)
            print(f"end card: studio card skipped ({type(e).__name__}: {e})", file=sys.stderr)
    im = Image.new("RGBA", (W, H), (28, 22, 19, 255))
    d = ImageDraw.Draw(im)
    ft, fs = font("CormorantGaramond.ttf", 120, "SemiBold"), font("Montserrat.ttf", 54, "ExtraBold")
    size = 120
    while d.textlength(t, font=ft, **FEAT) > W - 140 and size > 60:
        size -= 6
        ft = font("CormorantGaramond.ttf", size, "SemiBold")
    tw = d.textlength(t, font=ft, **FEAT)
    d.text(((W - tw) / 2, 640), t, font=ft, fill=(250, 244, 236, 255), **FEAT)
    sw = d.textlength(s, font=fs)
    d.rounded_rectangle([(W - sw) / 2 - 44, 880, (W + sw) / 2 + 44, 980], radius=50, fill=RED + (255,))
    d.text(((W - sw) / 2, 896), s, font=fs, fill=(255, 255, 255, 255))
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


def text_events(e, words, tmp, spots=None):
    """Overlay and caption PNG events [(t0, t1, png, layer)] (overlays layer 2, drawn over captions) + caption stats.
    spots: {segment index: caption centre} from caption_spots (shots whose bottom band shows something important)."""
    events, ovs = [], []
    reviews = json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]
    for j, o in enumerate(e.get("overlays", [])):
        png = os.path.join(tmp, f"ov{j:02d}.png")
        {"label": label_png, "offer": offer_png, "end": end_png, "tag": tag_png}.get(o["type"], lambda p, o: review_png(p, o, reviews))(png, o)
        events.append((o["at"], o["at"] + o["dur"], png, 2))
        ovs.append((o["at"], o["at"] + o["dur"], o, alpha_rows(png)))
    caps, st = caption_events(e, words, ovs, tmp, spots)
    st["caption_moved_shots"] = len(spots or {})
    return caps + events, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    e = json.load(open(a.edl))
    edl_dir = os.path.dirname(os.path.abspath(a.edl))
    tmp = tempfile.mkdtemp(prefix="longform_")
    t0 = time.time()

    # 1) base cut without any text
    base_edl = {k: v for k, v in e.items() if k in ("segments", "audio", "vo", "vo_start", "bed_gain", "sfx")}
    base_edl["segments"] = [{k: v for k, v in s.items() if k not in ("caption", "caption_pos")} for s in e["segments"]]
    bj = os.path.join(edl_dir, f"_base_edl_{os.getpid()}.json")  # unique: several renders may share a folder
    json.dump(base_edl, open(bj, "w"))
    base = os.path.join(tmp, "base.mp4")
    subprocess.run([sys.executable, os.path.join(HERE, "recut.py"), bj, "--out", base], check=True)
    os.remove(bj)
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base],
                                 capture_output=True, text=True).stdout)

    t1 = time.time()
    # 2) overlays, then captions from the final audio, placed clear of them
    if e.get("transcript"):          # what is said, known: the script on its voiceover timings, committed transcripts
        ws = fix_words(fix_known(e["transcript"], CAPTION_FIX), e.get("caption_fix", []))
    else:                            # (older EDLs) transcribe the final mix
        ws = fix_words(words_of(base), CAPTION_FIX + e.get("caption_fix", []))
    zy = ZONES.get(e.get("caption_zone", "bottom"), ZONES["bottom"])[0]
    spots = {} if e.get("caption_y_force") or e.get("caption_auto") is False else caption_spots(base, e, zy)
    events, st = text_events(e, ws, tmp, spots)

    t2 = time.time()
    lst = build_overlay_track(events, tmp, total)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", base, "-f", "concat", "-safe", "0", "-i", lst,
                    "-filter_complex", "[1:v]fps=30,format=rgba[o];[0:v][o]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "faster", "-crf", "17", "-maxrate", "14M",
                    "-bufsize", "28M", "-r", "30", "-c:a", "copy", "-movflags", "+faststart", "-t", f"{total:.3f}", "-y", a.out],
                   check=True, timeout=3600)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2), overlays=len(e.get("overlays", [])), **st)))
    print(f"longform: base cut {t1 - t0:.0f} s, captions + overlays {t2 - t1:.0f} s, final encode {time.time() - t2:.0f} s", file=sys.stderr)


if __name__ == "__main__":
    main()

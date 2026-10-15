#!/usr/bin/env python3
"""Brand-styled Facebook statics (1080x1350 / 1080x1080) built from real product photos.

White-background packshots are composited with a multiply blend, so the studio white turns into the
card colour and the natural contact shadow is kept (no background removal needed).

  python3 pipeline/brand_statics.py spec.json --outdir out/ [--only NAME] [--strict]

spec.json: {"ads": [{"name": "...", "layout": "<layout>", "size": [1080, 1350], ...layout fields...}]}

Layouts
  hero      photo, headline, sub, cta, badge?, hsize?, bg?          clean product hero
  promo     photo, headline, sub, features[3], badge, cta            espresso frame + cream panel (Ads Library style)
  callouts  photo, headline, points[{text, x, y, tx, ty}], cta       feature callouts with leader lines
  review    photo, review_n (pipeline/data/reviews.json) or quote/author, headline?   big quote card
  compare   photo, headline, left_title, left[], right_title, right[]           other bags vs ours
  colours   photos[{src, name}], headline, sub, cta                  colour picker grid
  bold      photo, lines[], sub, cta, accent, dots?                  big condensed type
  lifestyle photo (full bleed, crop/focus), headline, sub, cta       photo + text box
  split     left, right, headline, sub?, left_label, right_label     two photos side by side
  carousel  photo, headline, label, sub                              1080x1080 card for a carousel
  offer     photo, pct (or big), headline?, kicker?, gift?, price?, was?, sub?, cta    bottom of funnel: huge "50% OFF"
  stars     photo, reviews[n | {n, text}] (2-3, reviews.json), headline?, cta       star row + verbatim review snippets
  checklist photo, ticks[3-5], headline, sub?, offer?, cta          packshot + feature ticks + offer pill

Ad Library layouts (what the top-impression ads look like; new_layouts() lists them for make_batch's static cycle)
  native    photo, headline|caption, pct|badge?, focus?, crop?     a real face-free photo full bleed (cover-fit), no graphic: a small red
                                                                   offer pill in the calmer top corner + one caption in the video
                                                                   caption look (white Montserrat, dark outline, soft shadow) in the
                                                                   lower third; no sub, no CTA. The caption shrinks (1 line only while
                                                                   big, then 2, then 3 lines down to 34 px) before the static fails
  quotes    photo, quotes[{text, author, verified?, stars?}] | reviews[n | {n, text}], pct|badge|offer|price?, gift?, headline?, cta
                                                                   the packshot between two speech-bubble review cards (one when one
                                                                   quote is given; the longer of two is dropped when the packshot would
                                                                   get too little room), the offer line, the CTA pill. No quote given =
                                                                   no static; quotes are never cut or reworded
  value     price?, was?, pct|badge?, photo, headline?, gift?, sub?, cta   price-led on the brand cream: the big price with the was price
                                                                   struck through beside a "50% OFF" tag; with no price a red "50% OFF"
                                                                   plate; then the packshot, the gift label and the CTA. The packshot
                                                                   gets its room first; sub, then headline, go before the static fails
New optional spec keys (all of them are drawn verbatim, nothing is added):
  quotes   [{"text": verbatim quote, "author": "Jenny H.", "verified": false, "stars": true}]   (quotes layout; 'reviews' still works)
  price    "$59.95"      was   "$119.95" (must be above price; with pct, price must be pct % below was, +-2 points, else the static is refused)
  caption  native: the caption line (else headline)      offer   quotes: a ready offer line (else from pct / badge / price)
  focus [fx, fy] / crop [x0, y0, x1, y1]   native: where the cover-fit looks / a crop of the photo first
No "limited stock", "selling out", "ends tonight" or any other claim is ever drawn: only the words the spec carries. native refuses a
studio packshot (white border) and any photo the strict face check (new_product.count_faces(strict=True), the one lifestyle photos
pass) flags; it cannot tell a cropped head from a body, so feed it make_batch's lifestyle() photos (those drop "statics": false).
A review that mentions a gift or shipping (reviews.json "note") is the caller's to vet before it is passed in.

Typography (client feedback 2026-10-09: more air, smaller headlines, bigger small text, nothing touching): every text
block is placed by its measured ink (ascenders and descenders, not the em box); the block under a headline starts at
least AIR x its own font size below the headline's descender line; lines are balanced (no lone last word, no break after
'+', 'a', '50%' ...). render() checks every static for overlaps between text, pills, badges, panels and the product's own
pixels, and for anything off the canvas: it retries with 5% smaller type, and a static that still collides is not written
(stderr 'FAILED <name>': make_batch's QA then reports it as a failed render, so it never reaches Drive).
"""
import argparse
import functools
import itertools
import json
import math
import os
import re
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat, features

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "assets", "fonts")
CREAM, SAND, ESPRESSO, INK = (246, 241, 234), (236, 226, 212), (58, 40, 28), (24, 20, 18)
RED, GOLD, WHITE = (200, 22, 40), (184, 137, 59), (255, 255, 255)
MUTED = (90, 70, 56)
FEAT = {"features": ["lnum"]} if features.check("raqm") else {}   # lining figures: Cormorant's old-style '2in1' reads '2ını'
SCALE = [1.0]    # type scale of the current attempt: render() retries a static with smaller type while anything collides
TRACK = [False]  # True while render() draws a static: drawn elements are recorded in DRAWN for the overlap check
AIR = 0.6        # gap above a text block that follows another one, x its font size (client: more air under headlines)
EDGE = 24        # no text, pill or badge closer than this to the canvas edge
CANVAS = [1350]  # height of the static being rendered (room() scales its minimum photo height with it)


def font(name, size, weight=None):
    size = max(10, int(round(size * SCALE[0])))
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    f.key = (name, size, weight)
    return f


SERIF = lambda s: font("CormorantGaramond.ttf", s, "SemiBold")  # noqa: E731
SANS = lambda s, w="Medium": font("Inter.ttf", s, w)  # noqa: E731
BLACK = lambda s: font("Montserrat.ttf", s, "Black")  # noqa: E731
XB = lambda s: font("Montserrat.ttf", s, "ExtraBold")  # noqa: E731


MASKS = {}   # src -> list of [x0, y0, x1, y1] fractions painted white (baked-in "NEW"/"SALE" badges)


def load(spec_dir, src):
    im = ImageOps.exif_transpose(Image.open(os.path.join(spec_dir, src))).convert("RGB")
    if src in MASKS:
        for x0, y0, x1, y1 in MASKS[src]:     # white-fill baked-in badges on studio-white shots
            # cover the badge with the clean backdrop directly below it (keeps texture on paper backdrops)
            bx0, by0, bx1, by1 = int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)
            im.paste(im.crop((bx0, by1, bx1, by1 + (by1 - by0))), (bx0, by0))
    if src in CROPS:
        x0, y0, x1, y1 = CROPS[src]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    if src in CARD:
        im._card = True
    return im


def whiten(im, sample=12, knee=236):
    """Lift light-grey studio backgrounds (incl. soft vignettes) to pure white so the multiply blend
    leaves no box: values above `knee` ramp to 255, everything darker (the product) is untouched."""
    w, h = im.size
    px = [im.getpixel((x, y)) for x, y in ((sample, sample), (w - sample, sample), (sample, h - sample), (w - sample, h - sample))]
    if min(min(c) for c in px) < 225:          # not a studio packshot
        return im
    lut = [v if v < knee else int(knee + (v - knee) * (255 - knee) / max(250 - knee, 1)) if v < 250 else 255 for v in range(256)]
    return im.point(lut * 3)


def textured(path, band=0.06):
    """A light but not white backdrop (grey paper or plaster): even after whiten() a multiply blend would leave a visible
    grey box, so it goes in a framed photo card. True when over 30% of the border band stays below 246."""
    im = whiten(ImageOps.exif_transpose(Image.open(path)).convert("RGB")).convert("L")
    im.thumbnail((300, 300))
    w, h = im.size
    b = max(1, int(min(w, h) * band))
    px = [im.getpixel((x, y)) for y in range(h) for x in range(w) if x < b or y < b or x >= w - b or y >= h - b]
    return sum(v < 246 for v in px) / max(len(px), 1) > 0.3


def trim_white(im, thresh=245, pad=12):
    """Crop a white-background packshot to its content box."""
    g = im.convert("L").point(lambda v: 255 if v < thresh else 0)
    box = g.getbbox()
    if not box:
        return im
    x0, y0, x1, y1 = box
    return im.crop((max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, im.width), min(y1 + pad, im.height)))


CROPS = {}  # src -> [x0, y0, x1, y1] fractions kept (cuts baked-in badges off textured shots)
CARD = set()   # srcs shown as a framed photo card instead of a multiply blend (textured backdrops)


# ---------------------------------------------------------------- overlap check
DRAWN = []      # what the static being rendered has drawn (see note()); checked by collisions() after every layout
PROBLEMS = []   # layout-level problems of the current attempt (e.g. no room left for the photo)
_grp = itertools.count(1)


def note(kind, box, host=None, size=0, mask=None, grp=None, circle=None, label=""):
    """Record a drawn element for the overlap check and return its group id. kind: text | mark (stars, ticks, dots) |
    pill | label (a callout or tag box) | badge (circle) | box (a panel or card that holds other elements: pass its id as
    their host) | photo (its box + the product's own pixels as mask). Elements of one group, or hosted (directly or
    further up) by the other, never collide."""
    g = grp or next(_grp)
    if TRACK[0]:
        DRAWN.append(dict(kind=kind, box=tuple(int(round(v)) for v in box), grp=g, host=host, size=size, mask=mask,
                        circle=circle, label=label))
    return g


def _dist(r, s):
    """Gap between two boxes in px (0 when they touch or overlap)."""
    return math.hypot(max(s[0] - r[2], r[0] - s[2], 0), max(s[1] - r[3], r[1] - s[3], 0))


def _mask_hit(p, box, clear):
    """True when box (grown by clear) covers any pixel of photo p's product (the whole photo when it has no mask)."""
    x0, y0, x1, y1 = (max(box[0] - clear, p["box"][0]), max(box[1] - clear, p["box"][1]),
                      min(box[2] + clear, p["box"][2]), min(box[3] + clear, p["box"][3]))
    if x0 >= x1 or y0 >= y1:
        return False
    if p["mask"] is None:
        return True
    ox, oy = p["box"][:2]
    return p["mask"].crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy)).getbbox() is not None


def _cover(p, cx, cy, r):
    """Share of a circle covered by photo p's product pixels."""
    x0, y0, x1, y1 = int(cx - r), int(cy - r), int(cx + r), int(cy + r)
    ox, oy = p["box"][:2]
    m = (p["mask"] or Image.new("L", (p["box"][2] - ox, p["box"][3] - oy), 255)).crop((x0 - ox, y0 - oy, x1 - ox, y1 - oy))
    circ = Image.new("L", m.size, 0)
    ImageDraw.Draw(circ).ellipse([0, 0, m.width - 1, m.height - 1], fill=255)
    hit = ImageChops.multiply(m, circ).histogram()[255]
    return hit / max(circ.histogram()[255], 1)


FREE = ({"badge", "photo"},)   # a sale sticker may sit on the product photo


def _hit(a, b):
    """Why a and b collide, or None."""
    ka, kb = a["kind"], b["kind"]
    if {ka, kb} in FREE or (ka == kb == "photo" and _dist(a["box"], b["box"]) > 0):
        return None
    if "photo" in (ka, kb):
        p, o = (a, b) if ka == "photo" else (b, a)
        if o["kind"] == "photo":
            return "overlap"
        if o["circle"]:
            return "covers the product" if _cover(p, *o["circle"]) > 0.02 else None
        return "touches the product" if _mask_hit(p, o["box"], 4 if o["kind"] == "box" else 10) else None
    text = {"text", "mark"}
    clear = (max(8, 0.4 * min(a["size"] or 20, b["size"] or 20)) if ka in text and kb in text else
             4 if "box" in (ka, kb) else 10)
    if a["circle"] or b["circle"]:
        c, o = (a, b) if a["circle"] else (b, a)
        cx, cy, r = c["circle"]
        if o["circle"]:
            gap = math.hypot(cx - o["circle"][0], cy - o["circle"][1]) - r - o["circle"][2]
        else:
            gap = _dist(o["box"], (cx, cy, cx, cy)) - r
        return f"{gap:.0f}px apart" if gap < clear else None
    gap = _dist(a["box"], b["box"])
    return (f"{gap:.0f}px apart (want {clear:.0f})" if gap > 0 else "overlap") if gap < clear else None


def collisions(W, H):
    """Every pair of recorded elements that overlap or sit too close, plus anything off the canvas: a list of messages."""
    hosts = {e["grp"]: e["host"] for e in DRAWN}

    def up(g):
        seen = set()
        while g is not None and g not in seen:
            seen.add(g)
            g = hosts.get(g)
        return seen
    name = lambda e: f"{e['kind']} '{e['label'][:28]}'" if e["label"] else f"{e['kind']} {list(e['box'])}"  # noqa: E731
    out = []
    for i, a in enumerate(DRAWN):
        x0, y0, x1, y1 = a["box"]
        m = 0 if a["kind"] in ("photo", "box") else EDGE
        if x0 < m or y0 < m or x1 > W - m or y1 > H - m:
            out.append(f"{name(a)} runs off the canvas")
        ua = up(a["grp"])
        for b in DRAWN[i + 1:]:
            if b["grp"] in ua or a["grp"] in up(b["grp"]):
                continue
            why = _hit(a, b)
            if why:
                out.append(f"{name(a)} / {name(b)}: {why}")
    return out


def room(box, min_h=300, what="photo", scale=True):
    """box as ints, with a problem recorded when less than min_h px (on a 1350 px high canvas, scaled for 1080x1080
    unless scale=False) is left for the photo."""
    x0, y0, x1, y1 = (int(v) for v in box)
    min_h = int(min_h * (min(1.0, CANVAS[0] / 1350) if scale else 1))
    if y1 - y0 < min_h:
        PROBLEMS.append(f"only {y1 - y0}px left for the {what} (want {min_h})")
    return (x0, y0, x1, max(y1, y0 + 40))


class LayoutError(Exception):
    pass


# ---------------------------------------------------------------- drawing
def place_packshot(canvas, im, box, trim=True, host=None):
    """Multiply-blend a white-bg photo into box (x0, y0, x1, y1) on an RGB canvas, centred, aspect kept."""
    if getattr(im, "_card", False):
        x0, y0, x1, y1 = box
        s = min((x1 - x0) / im.width, (y1 - y0) / im.height)
        im2 = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        px, py = x0 + ((x1 - x0) - im2.width) // 2, y0 + ((y1 - y0) - im2.height) // 2
        mask = Image.new("L", im2.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, im2.width - 1, im2.height - 1], radius=28, fill=255)
        sh = Image.new("L", (im2.width + 60, im2.height + 60), 0)
        ImageDraw.Draw(sh).rounded_rectangle([30, 30, im2.width + 30, im2.height + 30], radius=28, fill=70)
        sh = sh.filter(ImageFilter.GaussianBlur(16))
        canvas.paste((0, 0, 0), (px - 24, py - 18), ImageChops.multiply(sh, Image.new("L", sh.size, 255)))
        canvas.paste(im2, (px, py), mask)
        note("photo", (px, py, px + im2.width, py + im2.height), host=host)
        return (px, py, px + im2.width, py + im2.height)
    im = whiten(im)
    if trim:
        im = trim_white(im)
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    px, py = x0 + ((x1 - x0) - im.width) // 2, y0 + ((y1 - y0) - im.height) // 2
    region = canvas.crop((px, py, px + im.width, py + im.height))
    canvas.paste(ImageChops.multiply(region, im), (px, py))
    if TRACK[0]:   # the product's own pixels (contact shadow included): nothing printed may touch them
        m = im.convert("L").point(lambda v: 255 if v < 226 else 0).filter(ImageFilter.MinFilter(5))
        note("photo", (px, py, px + im.width, py + im.height), host=host, mask=m)
    return (px, py, px + im.width, py + im.height)


def packshot_aspect(im):
    """Width / height of a packshot's content (after the same whiten + trim place_packshot does)."""
    if getattr(im, "_card", False):
        return im.width / im.height
    t = trim_white(whiten(im))
    return t.width / t.height


_MET = {}


def metrics(f):
    """(ascent, descent) of a font's ink in px: the tallest ascender ('b', 'd', 'H') above the baseline and the deepest
    descender ('g', 'y') below it. Text is placed by these, not by the em box, so a 'y' never reaches the line below."""
    k = getattr(f, "key", None) or (getattr(f, "path", ""), f.size)
    if k not in _MET:
        _MET[k] = (-f.getbbox("Hbdfhklt", anchor="ls", **FEAT)[1], f.getbbox("gjpqy", anchor="ls", **FEAT)[3])
    return _MET[k]


BAD_END = {"+", "&", "a", "an", "the", "and", "or", "of", "for", "with", "to", "your", "my", "in", "on", "at", "by",
           "free", "-", "–", "—", "·"}


def _balance(ws, n, tl, max_w):
    """ws split into n lines that all fit max_w: the widest line as narrow as possible, a break after '+', 'a', 'the',
    '50%' or a number counting as a quarter of the width; None when no split fits."""
    bad = lambda w: w.lower() in BAD_END or w.endswith("%") or w.isdigit()  # noqa: E731
    cost = lambda r: r[0] + 0.25 * max_w * r[1]  # noqa: E731

    @functools.lru_cache(None)
    def go(i, k):           # (widest, bad breaks, break indexes) for ws[i:] in k lines
        if k == 1:
            w = tl(" ".join(ws[i:]))
            return (w, 0, ()) if w <= max_w else None
        best = None
        for j in range(i + 1, len(ws) - k + 2):
            w = tl(" ".join(ws[i:j]))
            if w > max_w:
                break
            r = go(j, k - 1)
            if r:
                cand = (max(w, r[0]), r[1] + bad(ws[j - 1]), (j,) + r[2])
                if best is None or cost(cand) < cost(best):
                    best = cand
        return best
    r = go(0, n)
    if not r:
        return None
    cuts = (0,) + r[2] + (len(ws),)
    return [" ".join(ws[a:b]) for a, b in zip(cuts, cuts[1:])]


def wrap(d, text, f, max_w, balance=False):
    """Lines of text that fit max_w ('\\n' forces a break). balance: as many lines as a greedy wrap, but even in length and
    never broken after '+', 'a', 'the', '50%' (no lone last word: 'hand making / these bags')."""
    tl = lambda s: d.textlength(s, font=f, **FEAT)  # noqa: E731
    out = []
    for para in text.split("\n"):
        ws, cur, lines = para.split(), "", []
        for w in ws:
            t = (cur + " " + w).strip()
            if cur and tl(t) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        if balance and len(lines) > 1:
            lines = _balance(tuple(ws), len(lines), tl, max_w) or lines
        elif len(lines) > 1 and " " not in lines[-1] and lines[-2].count(" ") > 1:     # no lone last word
            a, b = lines[-2].rsplit(" ", 1)
            if tl(b + " " + lines[-1]) <= max_w:
                lines[-2:] = [a, b + " " + lines[-1]]
        out += lines
    return out


def put(d, text, f, fill, top, max_w, cx=None, x=None, lh=1.12, host=None, balance=None, dry=False, kind="text", stroke=0,
        stroke_fill=(20, 20, 20)):
    """Draw text wrapped to max_w (or a list of ready lines; fill may be a colour per line) with the first line's ink top
    at `top`, centred on cx or left-aligned at x. Returns the block's bottom: the descender line under the last
    baseline (the real ink bottom for all-caps text), so whatever the caller puts below never meets a 'g' or a 'y'.
    balance (default: centred text and short phrases, not a left-aligned paragraph): see wrap(). dry: measure only.
    stroke: outline width in px (native captions); the measured bottom and the overlap box include it."""
    if not text:
        return top
    if balance is None:
        balance = x is None or len(text) < 70
    lines = list(text) if isinstance(text, (list, tuple)) else wrap(d, text, f, max_w, balance)
    asc, desc = metrics(f)
    caps = not any(ch.islower() for ch in "".join(lines))
    step = max(int(f.size * lh), asc + (0 if caps else desc) + int(f.size * 0.14))
    g, base, low = next(_grp), top + asc, top
    sk, bk = (dict(stroke_width=stroke, stroke_fill=stroke_fill), dict(stroke_width=stroke)) if stroke else ({}, {})  # (none: as before)
    if x is None and cx is None:
        cx = d.im.size[0] / 2
    for k, ln in enumerate(lines):
        tx = x if cx is None else cx - d.textlength(ln, font=f, **FEAT) / 2
        if ln.strip():
            bb = d.textbbox((tx, base), ln, font=f, anchor="ls", **bk, **FEAT)
            low = max(low, bb[3])
            if not dry:
                d.text((tx, base), ln, font=f, fill=fill[k] if isinstance(fill, list) else fill, anchor="ls", **sk, **FEAT)
                note(kind, bb, host=host, size=f.size, grp=g, label=ln)
        base += step
    return max(low, base - step + (0 if caps else desc))


def air(f_next, f_prev=None, k=AIR):
    """Gap between a text block and the next one: k x the next font size, and at least 0.3 x a big headline above it."""
    return int(max(k * f_next.size, 0.3 * f_prev.size if f_prev else 0, 16))


def width(d, text, f):
    return d.textlength(text, font=f, **FEAT)


def text_c(d, W, y, text, f, fill, max_w=None, lh=1.12):
    """Centred text block from y (its ink top); returns its bottom (kept for older callers: see put())."""
    return put(d, text, f, fill, y, max_w or W - 120, cx=W / 2, lh=lh) + 10


def fit_font(d, text, maker, size, max_w, min_size=40):
    f = maker(size)
    longest = lambda f: max(d.textlength(t, font=f, **FEAT) for t in text.split("\n"))  # noqa: E731
    while longest(f) > max_w and size > min_size:
        size -= 4
        f = maker(size)
    return f


def fit(d, text, maker, size, max_w, lines=2, min_size=40):
    """The biggest font (from size down) at which text wraps to at most `lines` lines within max_w, no word cut; one line
    when that only costs up to 14% of the size ('Your everyday bag vs Hobo Bag' on one line, not broken after 'everyday')."""
    if lines > 1 and "\n" not in text:
        one = fit(d, text, maker, size, max_w, 1, max(min_size, int(size * 0.86)))
        if width(d, text, one) <= max_w:
            return one
    while True:
        f = maker(size)
        ls = wrap(d, text, f, max_w)
        if size <= min_size or (len(ls) <= lines and max(width(d, x, f) for x in ls) <= max_w):
            return f
        size -= 4


def pill(d, W, y, text, bg=ESPRESSO, fg=WHITE, size=36, host=None, cx=None, bold=False, dry=False):
    """A rounded button centred on cx (default the canvas centre) from y; returns its bottom."""
    f = XB(size) if bold else font("Inter.ttf", size, "SemiBold")
    h, w = int(f.size * 2.4), width(d, text, f) + 3 * f.size
    if dry:
        return y + h
    x = (W / 2 if cx is None else cx) - w / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    d.text((x + w / 2, y + h / 2), text, font=f, fill=fg, anchor="mm", **FEAT)
    note("pill", (x, y, x + w, y + h), host=host, label=text)
    return y + h


def badge(canvas, cx, cy, r, top, big, bottom, colour=RED, angle=-12, host=None):
    lay = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([10, 10, 10 + 2 * r, 10 + 2 * r], fill=colour + (255,))
    d.ellipse([22, 22, 2 * r - 2, 2 * r - 2], outline=(255, 255, 255, 170), width=3)
    fb, fs = BLACK(int(r * 0.62 / SCALE[0])), XB(int(r * 0.2 / SCALE[0]))     # the sticker keeps its size
    for txt, f, dy in ((top, fs, -0.42), (big, fb, -0.12), (bottom, fs, 0.36)):
        if txt:
            tw = d.textlength(txt, font=f)
            d.text((10 + r - tw / 2, 10 + r + dy * r - f.size * 0.35 + (0 if f is fs else -r * 0.05)), txt, font=f, fill=WHITE)
    lay = lay.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 80), mask=lay.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    canvas.alpha_composite(sh, (int(cx - lay.width / 2 + 6), int(cy - lay.height / 2 + 10)))
    canvas.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))
    note("badge", (cx - r, cy - r, cx + r, cy + r), circle=(cx, cy, r), host=host, label=big)


def auto_badge(canvas, b, r, photo, host=None):
    """The sale badge at the photo's top-right corner (or half above it, then the other corners) where it hits no text,
    pill or panel and does not touch the product (else covers at most 12% of it, else wherever it covers least)."""
    W, H = canvas.size
    x0, y0, x1, y1 = photo
    spots = [(x1 - 0.15 * r, y0 + 1.05 * r), (x1 - 0.5 * r, y0 - 0.25 * r), (x1 - 0.6 * r, y0 - 0.7 * r),
             (x0 + 0.15 * r, y0 + 1.05 * r), (x0 + 0.5 * r, y0 - 0.25 * r), (x1 - 0.15 * r, y1 - 1.05 * r),
             (x0 + 0.15 * r, y1 - 1.05 * r)]
    spots = [(min(max(cx, EDGE + r + 6), W - EDGE - r - 6), min(max(cy, EDGE + r + 6), H - EDGE - r - 6)) for cx, cy in spots]
    photos = [e for e in DRAWN if e["kind"] == "photo"]
    best = None
    for k, (cx, cy) in enumerate(spots):
        probe = dict(kind="badge", box=(cx - r, cy - r, cx + r, cy + r), circle=(cx, cy, r), size=0, mask=None)
        hit = any(_hit(probe, e) for e in DRAWN if e["kind"] != "photo" and e["grp"] != host)
        cover = max([_cover(p, cx, cy, r) for p in photos] or [0])
        score = (hit, 0 if cover < 0.003 else 1 if cover <= 0.12 else 2, cover if cover > 0.12 else k)
        if best is None or score < best[0]:
            best = (score, cx, cy)
    badge(canvas, best[1], best[2], r, b.get("top", ""), b["big"], b.get("bottom", ""), host=host)


def brand_mark(d, W, y, colour=ESPRESSO):
    """LIBRA CASES letter-spaced, ink top at y; returns its bottom."""
    return put(d, ["L I B R A   C A S E S"], font("Inter.ttf", 26, "SemiBold"), colour, y, W, cx=W / 2)


def spaced(t):
    """Letter-spaced caps for small labels: 'FINAL SALE' -> 'F I N A L   S A L E'."""
    return "   ".join(" ".join(w) for w in t.upper().split())


def stars(d, x, y, s=40, colour=GOLD, host=None):
    for k in range(5):
        cx, cy, r = x + k * (s + 8) + s / 2, y + s / 2, s / 2
        pts = [(cx + (r if j % 2 == 0 else r * 0.45) * math.cos(math.pi / 2 + j * math.pi / 5),
                cy - (r if j % 2 == 0 else r * 0.45) * math.sin(math.pi / 2 + j * math.pi / 5)) for j in range(10)]
        d.polygon(pts, fill=colour)
    note("mark", (x, y, x + 5 * s + 32, y + s), host=host, label="stars")
    return y + s


def tick(d, cx, cy, r, bg=GOLD, fg=WHITE, host=None):
    """A check mark in a filled circle."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.34), (cx + r * 0.46, cy - r * 0.32)], fill=fg,
           width=max(3, int(r * 0.24)), joint="curve")
    note("mark", (cx - r, cy - r, cx + r, cy + r), host=host)


def cross(d, cx, cy, r, bg=(190, 120, 112), fg=WHITE, host=None):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    k, w = r * 0.36, max(3, int(r * 0.22))
    d.line([(cx - k, cy - k), (cx + k, cy + k)], fill=fg, width=w)
    d.line([(cx - k, cy + k), (cx + k, cy - k)], fill=fg, width=w)
    note("mark", (cx - r, cy - r, cx + r, cy + r), host=host)


def tick_list(d, items, f, x, top, max_w, mark=tick, colour=ESPRESSO, gap=None, host=None, dry=False, r=None):
    """Items as rows of mark + text (left-aligned at x, mark centred on the first line's x-height); returns the bottom."""
    asc = metrics(f)[0]
    r = r or int(f.size * 0.6)
    y = top
    for k, it in enumerate(items):
        if k:
            y += gap if gap is not None else int(f.size * 0.75)
        t0 = y + max(0, r - asc * 0.62)       # the mark's top never above the row's top
        if not dry:
            mark(d, x + r, t0 + asc * 0.62, r, host=host)
        y = max(put(d, it, f, colour, t0, max_w - 2 * r - int(f.size * 0.55), x=x + 2 * r + int(f.size * 0.55), lh=1.18,
                    host=host, dry=dry), t0 + asc * 0.62 + r)
    return y


# ---------------------------------------------------------------- layouts
def l_hero(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    y = brand_mark(d, W, 58)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 98), W - 140, 2)
    y = put(d, a["headline"], fh, ESPRESSO, y + 46, W - 140, lh=1.0)
    if a.get("sub"):
        fs = SANS(42)
        y = put(d, a["sub"], fs, MUTED, y + air(fs, fh), W - 190, lh=1.3)
    py = H - 175
    box = place_packshot(c, load(sd, a["photo"]), room((90, y + 52, W - 90, py - 44)))
    c = c.convert("RGBA")
    if a.get("badge"):
        auto_badge(c, a["badge"], 116, box)
    pill(ImageDraw.Draw(c), W, py, a.get("cta", "Shop now"))
    return c


def l_promo(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), ESPRESSO)
    d = ImageDraw.Draw(c)
    m, py = 46, H - 175
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 84), W - 140, 2)
    y = put(d, a["headline"], fh, (250, 236, 214), 62, W - 140, lh=1.0)
    top, bot = max(y + 46, 170), py - 50
    panel = note("box", (m, top, W - m, bot))
    d.rounded_rectangle([m, top, W - m, bot], radius=28, fill=CREAM)
    y = top + 44
    if a.get("sub"):
        y = put(d, a["sub"], SANS(40, "SemiBold"), ESPRESSO, y, W - 2 * m - 120, host=panel)
    feats, fy = a.get("features", []), bot - 32
    if feats:
        f = SANS(32, "SemiBold")
        fw = (W - 2 * m - 60) / len(feats)
        hs = [put(d, t, f, ESPRESSO, 0, fw - 52, dry=True, lh=1.2) for t in feats]
        bh = max(hs) + 56
        fy -= bh
        for i, t in enumerate(feats):
            x0 = m + 30 + i * fw
            fb = note("box", (x0 + 8, fy, x0 + fw - 8, fy + bh), host=panel)
            d.rounded_rectangle([x0 + 8, fy, x0 + fw - 8, fy + bh], radius=18, fill=SAND)
            put(d, t, f, ESPRESSO, fy + (bh - hs[i]) / 2, fw - 52, cx=x0 + fw / 2, lh=1.2, host=fb)
    box = place_packshot(c, load(sd, a["photo"]), room((m + 70, y + 36, W - m - 70, fy - 30), 280), host=panel)
    c = c.convert("RGBA")
    if a.get("badge"):
        auto_badge(c, a["badge"], 112, box, host=panel)
    pill(ImageDraw.Draw(c), W, py, a.get("cta", "Shop now"), bg=RED)
    return c


def l_callouts(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 86), W - 120, 2)
    y = put(d, a["headline"], fh, ESPRESSO, 70, W - 120, lh=1.0)
    py = H - 165
    bx = place_packshot(c, load(sd, a["photo"]), tuple(a.get("photo_box") or room((250, y + 48, W - 250, py - 50))))
    f = SANS(a.get("psize", 34), "SemiBold")
    for p in a["points"]:
        # p.x, p.y are fractions of the placed photo box; tx, ty canvas pixels for the label (kept under the headline)
        px = bx[0] + p["x"] * (bx[2] - bx[0])
        py_ = bx[1] + p["y"] * (bx[3] - bx[1])
        lx = p["tx"]
        for mw in (260, 210, 170):      # a narrower label (more lines) when no spot beside the product is free
            lines = wrap(d, p["text"], f, mw, True)
            tw = max(width(d, x, f) for x in lines)
            bw, bh = tw + 44, put(d, lines, f, ESPRESSO, 0, 400, x=0, lh=1.2, dry=True) + 40
            x0 = lx if lx < W / 2 else lx - bw
            ly = free_y(x0, max(p["ty"], y + 36), bw, bh, y + 36, py - 30)
            if ly is not None:
                break
        ly = max(p["ty"], y + 36) if ly is None else ly
        d.line([(px, py_), (x0 + (bw if lx < W / 2 else 0), ly + bh / 2)], fill=GOLD, width=3)
        d.ellipse([px - 9, py_ - 9, px + 9, py_ + 9], fill=GOLD, outline=WHITE, width=3)
        lb = note("label", (x0, ly, x0 + bw, ly + bh), label=p["text"])
        d.rounded_rectangle([x0, ly, x0 + bw, ly + bh], radius=16, fill=WHITE, outline=(226, 214, 198), width=2)
        put(d, lines, f, ESPRESSO, ly + 20, 400, x=x0 + 22, lh=1.2, host=lb)
    pill(d, W, py, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def free_y(x0, y0, w, h, lo, hi, step=24, reach=10):
    """The y nearest y0 (within lo..hi) where a w x h label at x0 touches nothing drawn so far (the product, text, other
    labels); None when none is."""
    for k in range(2 * reach + 1):
        y = y0 + (k + 1) // 2 * step * (1 if k % 2 else -1)
        if lo <= y and y + h <= hi:
            probe = dict(kind="label", box=(x0, y, x0 + w, y + h), size=0, mask=None, circle=None)
            if not any(_hit(probe, e) for e in DRAWN):
                return y
    return None


def review_text(n):
    r = next(x for x in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"] if x["n"] == n)
    return r["text"], r["name"], r.get("verified")


def name_line(d, x, top, name, verified, fn, host=None):
    """'— Name  ✓ Verified customer' from top (ink top of the name); returns the bottom."""
    fv = SANS(28)
    bot = put(d, "— " + name, fn, ESPRESSO, top, 900, x=x, host=host)
    if verified:
        put(d, "✓ Verified customer", fv, (70, 120, 70), top + metrics(fn)[0] - metrics(fv)[0], 600,
            x=x + width(d, "— " + name, fn) + 20, host=host)
    return bot


def l_review(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", SAND)))
    d = ImageDraw.Draw(c)
    if a.get("review_n"):
        quote, name, verified = review_text(a["review_n"])
    else:
        quote, name, verified = a["quote"], a.get("author", a.get("name")), a.get("verified", True)
    y = 110
    if a.get("headline"):
        fh = fit(d, a["headline"], SERIF, a.get("hsize", 76), W - 140, 2)
        y = put(d, a["headline"], fh, ESPRESSO, 70, W - 140, lh=1.0) + 48
    fq, fn = SERIF(a.get("qsize", 50)), SANS(34, "SemiBold")
    q = "“" + quote + "”"
    qtop = y + 56 + 40 + 36
    qbot = put(d, q, fq, INK, qtop, W - 260, x=130, balance=False, dry=True)
    ntop = qbot + air(fn)
    cb = ntop + sum(metrics(fn)) + 56
    card = note("box", (70, y, W - 70, cb))
    d.rounded_rectangle([70, y, W - 70, cb], radius=34, fill=WHITE)
    stars(d, 130, y + 56, host=card)
    put(d, q, fq, INK, qtop, W - 260, x=130, balance=False, host=card)
    name_line(d, 130, ntop, name, verified, fn, host=card)
    py = H - 165
    place_packshot(c, load(sd, a["photo"]), room((160, cb + 44, W - 160, py - 40), 280))
    pill(d, W, py, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def l_compare(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 82), W - 120, 2)
    y = put(d, a["headline"], fh, ESPRESSO, 64, W - 120, lh=1.0)
    py = H - 165
    cw = (W - 150) / 2
    fi = SANS(34, "Medium")
    cols = ((a["left_title"], a["left"], False), (a["right_title"], a["right"], True))

    def body(x0, top, title, items, good, dry, host=None):
        yy = put(d, title, fit_font(d, title, XB, 40, cw - 60, 26), WHITE if good else (110, 100, 92), top, cw - 60,
                 cx=x0 + cw / 2, host=host, dry=dry)
        return tick_list(d, items, fi, x0 + 34, yy + 34, cw - 64, mark=tick if good else cross,
                         colour=WHITE if good else (110, 100, 92), gap=26, host=host, dry=dry, r=19)
    ch = max(body(0, 0, t, it, g, True) for t, it, g in cols) + 40 + 44
    ctop = py - 46 - ch
    place_packshot(c, load(sd, a["photo"]), room((280, y + 40, W - 280, ctop - 36), 260))
    for k, (title, items, good) in enumerate(cols):
        x0 = 60 + k * (cw + 30)
        col = note("box", (x0, ctop, x0 + cw, ctop + ch))
        d.rounded_rectangle([x0, ctop, x0 + cw, ctop + ch], radius=26, fill=(ESPRESSO if good else (226, 220, 212)))
        body(x0, ctop + 40, title, items, good, False, col)
    pill(d, W, py, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")


def l_colours(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 88), W - 120, 2)
    y = put(d, a["headline"], fh, ESPRESSO, 64, W - 120, lh=1.0)
    if a.get("sub"):
        fs = SANS(40)
        y = put(d, a["sub"], fs, MUTED, y + air(fs, fh), W - 180, lh=1.3)
    ph = a["photos"]
    py = H - 165
    gx, gy0, gy1 = 50, y + 40, py - 40
    f = SANS(32, "SemiBold")
    nh = sum(metrics(f))
    asp = packshot_aspect(load(sd, ph[0]["src"]))

    def shown(cols):        # total photo area of a grid with this many columns
        rows = math.ceil(len(ph) / cols)
        cw, chh = (W - 2 * gx) / cols - 60, (gy1 - gy0) / rows - 76 - nh
        s = min(cw / asp, chh) if cw > 0 and chh > 0 else 0
        return s * s * asp * len(ph) * (0.9 if rows * cols - len(ph) > 1 else 1)
    cols = max((1, 2, 3), key=shown) if len(ph) > 1 else 1
    rows = math.ceil(len(ph) / cols)
    cw, chh = (W - 2 * gx) / cols, (gy1 - gy0) / rows
    for i, p in enumerate(ph):
        left = len(ph) - (i // cols) * cols         # a short last row is centred
        x0, y0 = gx + (i % cols) * cw + (cols - left) * cw / 2 * (left < cols), gy0 + (i // cols) * chh
        cell = note("box", (x0 + 10, y0 + 10, x0 + cw - 10, y0 + chh - 10))
        d.rounded_rectangle([x0 + 10, y0 + 10, x0 + cw - 10, y0 + chh - 10], radius=22, fill=WHITE)
        ntop = y0 + chh - 10 - 22 - nh
        place_packshot(c, load(sd, p["src"]), room((x0 + 30, y0 + 28, x0 + cw - 30, ntop - 16), 120), host=cell)
        if p.get("name"):
            put(d, p["name"], f, ESPRESSO, ntop, cw - 40, cx=x0 + cw / 2, host=cell)
    pill(d, W, py, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def l_bold(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", WHITE)))
    d = ImageDraw.Draw(c)
    acc = tuple(a.get("accent", RED))
    lines = a["lines"]
    fb = min((fit_font(d, ln, BLACK, a.get("size_px", 122), W - 110) for ln in lines), key=lambda f: f.size)  # one size
    y = put(d, lines, fb, [acc if i in a.get("accent_lines", [0]) else INK for i in range(len(lines))], 74, W, lh=1.0)
    if a.get("sub"):
        fs = SANS(42, "SemiBold")
        y = put(d, a["sub"], fs, (70, 60, 52), y + max(air(fs, fb), int(0.4 * fb.size)), W - 170, lh=1.3)
    py = H - 160
    bottom = py - 40
    if a.get("dots"):
        n, ds = len(a["dots"]), 44
        x = W / 2 - (n * 60 - 16) / 2
        dy = py - 34 - ds
        for col in a["dots"]:
            d.ellipse([x, dy, x + ds, dy + ds], fill=tuple(col), outline=(200, 200, 200), width=2)
            x += 60
        note("mark", (W / 2 - (n * 60 - 16) / 2, dy, W / 2 + (n * 60 - 16) / 2, dy + ds), label="colour dots")
        bottom = dy - 30
    place_packshot(c, load(sd, a["photo"]), room((110, y + 48, W - 110, bottom)))
    pill(d, W, py, a.get("cta", "Shop now"), bg=INK)
    return c.convert("RGBA")


def l_lifestyle(a, sd):
    W, H = a.get("size", [1080, 1350])
    im = load(sd, a["photo"])
    if a.get("crop"):
        x0, y0, x1, y1 = a["crop"]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    c = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=tuple(a.get("focus", [0.5, 0.5]))).convert("RGBA")
    d = ImageDraw.Draw(c)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 86), W - 180, 2)
    fs = SANS(38)
    hh = put(d, a["headline"], fh, ESPRESSO, 0, W - 180, lh=1.02, dry=True)
    sh = air(fs, fh) + put(d, a["sub"], fs, MUTED, 0, W - 220, lh=1.3, dry=True) if a.get("sub") else 0
    bh = 48 + hh + sh + 36 + (pill(d, W, 0, a.get("cta", "Shop now"), size=32, dry=True)) + 44
    by = 60 if a.get("text_pos", "bottom") == "top" else H - bh - 50
    c.alpha_composite(Image.new("RGBA", (W - 100, bh), CREAM + (238,)), (50, by))
    d = ImageDraw.Draw(c)
    panel = note("box", (50, by, W - 50, by + bh))
    y = put(d, a["headline"], fh, ESPRESSO, by + 48, W - 180, lh=1.02, host=panel)
    if a.get("sub"):
        y = put(d, a["sub"], fs, MUTED, y + air(fs, fh), W - 220, lh=1.3, host=panel)
    pill(d, W, y + 36, a.get("cta", "Shop now"), size=32, host=panel)
    return c


def tag(d, cx, top, text, bg, f=None, host=None, kind="label"):
    """A small rounded tag (XB caps) centred on cx; returns its box."""
    f = f or XB(34)
    tw, (asc, _) = width(d, text, f), metrics(f)
    w, h = tw + 1.4 * f.size, asc + f.size
    box = (cx - w / 2, top, cx + w / 2, top + h)
    g = note(kind, box, host=host, label=text)
    d.rounded_rectangle(box, radius=h / 2, fill=bg)
    d.text((cx, top + h / 2 + asc / 2), text, font=f, fill=WHITE, anchor="ms", **FEAT)
    return box, g


def l_split(a, sd):
    """Before / after: two photos side by side under a headline."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 82), W - 120, 2)
    y = put(d, a["headline"], fh, ESPRESSO, 56, W - 120, lh=1.0)
    if a.get("sub"):
        fs = SANS(38)
        y = put(d, a["sub"], fs, MUTED, y + air(fs, fh), W - 180, lh=1.3)
    py = H - 165
    top, bot, g = y + 40, py - 40, 24
    room((0, top, 0, bot), 360, "photos")
    bot = max(bot, top + 40)
    cw = (W - 100 - g) // 2
    for k, (src, lab) in enumerate(((a["left"], a.get("left_label", "BEFORE")), (a["right"], a.get("right_label", "AFTER")))):
        x0 = 50 + k * (cw + g)
        ph = ImageOps.fit(load(sd, src).convert("RGB"), (cw, bot - top), Image.LANCZOS, centering=tuple(a.get("focus", [0.5, 0.5])))
        m = Image.new("L", ph.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], radius=26, fill=255)
        c.paste(ph, (x0, top), m)
        cell = note("box", (x0, top, x0 + cw, bot))
        tag(d, x0 + cw / 2, top + 24, lab, RED if k else INK, host=cell)
    pill(d, W, py, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")


def l_carousel(a, sd):
    W, H = a.get("size", [1080, 1080])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 70), W - 120, 2)
    y = put(d, a["headline"], fh, ESPRESSO, 52, W - 120, lh=1.0)
    bot = H - 60
    if a.get("sub"):
        fs = SANS(40, "SemiBold")
        bot = H - 56 - put(d, a["sub"], fs, ESPRESSO, 0, W - 120, dry=True)
        put(d, a["sub"], fs, ESPRESSO, bot, W - 120)
    box = place_packshot(c, load(sd, a["photo"]), room((120, y + 40, W - 120, bot - 36), 260))
    if a.get("label"):
        f = BLACK(64)
        asc = metrics(f)[0]
        tw, h = width(d, a["label"], f), asc + 52
        x0, y0 = 60, max(y + 30, box[1])
        note("label", (x0, y0, x0 + tw + 60, y0 + h), label=a["label"])
        d.rounded_rectangle([x0, y0, x0 + tw + 60, y0 + h], radius=h / 2, fill=ESPRESSO)
        d.text((x0 + 30, y0 + h / 2 + asc / 2), a["label"], font=f, fill=WHITE, anchor="ls", **FEAT)
    return c.convert("RGBA")


# ---------------------------------------------------------------- bottom of funnel (the Hobo Bag static that converts)
def l_offer(a, sd):
    """The deal first: huge '50% OFF', the product name, an optional price line, the packshot, the gift ribbon and the
    CTA. Every number and gift comes from the spec (make_batch reads them from the site): nothing is made up here."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    big = a.get("big") or f"{int(a['pct'])}% OFF"
    if not a.get("big") and not 5 <= int(a["pct"]) <= 90:
        raise ValueError(f"offer: pct {a['pct']} is not a real discount")
    y = brand_mark(d, W, 54)
    if a.get("kicker"):
        y = put(d, [spaced(a["kicker"])], fit_font(d, spaced(a["kicker"]), XB, 30, W - 120, 18), ESPRESSO, y + 40, W - 100)
    fb = fit_font(d, big, BLACK, a.get("bsize", 200), W - 110, 80)
    y = put(d, big, fb, RED, y + (30 if a.get("kicker") else 42), W, lh=1.0)
    prev = fb
    if a.get("headline"):
        fh = fit(d, a["headline"], SERIF, a.get("hsize", 72), W - 160, 1)
        y = put(d, a["headline"], fh, ESPRESSO, y + air(fh, k=0.5), W - 160, lh=1.0)
        prev = fh
    if a.get("price"):
        fp, fw = XB(58), SANS(42)
        top = y + air(fp, prev, 0.5)
        pw, ww = width(d, a["price"], fp), (width(d, a["was"], fw) + 24 if a.get("was") else 0)
        x = W / 2 - (pw + ww) / 2
        base = top + metrics(fp)[0]
        g = next(_grp)
        d.text((x, base), a["price"], font=fp, fill=INK, anchor="ls", **FEAT)
        note("text", d.textbbox((x, base), a["price"], font=fp, anchor="ls", **FEAT), size=fp.size, grp=g, label=a["price"])
        y = base + metrics(fp)[1]
        if a.get("was"):
            wx = x + pw + 24
            bb = d.textbbox((wx, base), a["was"], font=fw, anchor="ls", **FEAT)
            d.text((wx, base), a["was"], font=fw, fill=(150, 136, 124), anchor="ls", **FEAT)
            mid = (bb[1] + bb[3]) / 2
            d.line([(bb[0] - 4, mid), (bb[2] + 4, mid)], fill=(150, 136, 124), width=max(2, fw.size // 14))
            note("text", bb, size=fw.size, grp=g, label=a["was"])
        prev = fp
    if a.get("sub"):
        fs = SANS(36)
        y = put(d, a["sub"], fs, MUTED, y + air(fs, prev, 0.5), W - 180, lh=1.3)
    py = H - 170
    bot = py - 40
    if a.get("gift"):
        g = "+ " + re.sub(r"^\+\s*", "", a["gift"]).upper()
        fg = fit_font(d, g, XB, 34, W - 220, 22)
        asc = metrics(fg)[0]
        h = asc + int(fg.size * 1.15)
        w = width(d, g, fg) + 2 * fg.size
        gy = py - 34 - h
        rb = note("label", (W / 2 - w / 2, gy, W / 2 + w / 2, gy + h), label=g)
        d.rounded_rectangle([W / 2 - w / 2, gy, W / 2 + w / 2, gy + h], radius=14, fill=SAND)
        d.text((W / 2, gy + h / 2 + asc / 2), g, font=fg, fill=ESPRESSO, anchor="ms", **FEAT)
        note("text", (W / 2 - w / 2 + fg.size, gy + h / 2 - asc / 2, W / 2 + w / 2 - fg.size, gy + h / 2 + asc / 2),
            host=rb, size=fg.size, label=g)
        bot = gy - 28
    place_packshot(c, load(sd, a["photo"]), room((110, y + 44, W - 110, bot), 340))
    pill(d, W, py, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")


POSITIVE = re.compile(r"\b(love|loved|best|quality|amazing|perfect|stylish|compartments?|pockets?|compliments|adores?|spacious|"
                      r"comfortable|versatile|holds|fits|pleased|chic|recommend)\b", re.I)
NOT_SNIPPET = re.compile(r"\b(free|gift|wallet|shipping|arrived|price|discount|order|cheap|(?:\d+|one|two|three|four|five|six|"
                         r"seven|few|couple of) days?)\b", re.I)          # offers and delivery times change


def snippet(text, max_chars=110):
    """The best short verbatim piece of a review: 1-2 consecutive whole sentences as written, nothing about gifts,
    prices or delivery (offers change), the most positive words first, about 55 characters."""
    t = re.sub(r"\s+", " ", text).strip()
    spans = [m.span() for m in re.finditer(r"[^.!?]+[.!?]+", t)]
    best = None
    for i in range(len(spans)):
        for j in (i, i + 1):
            if j >= len(spans):
                break
            run = t[spans[i][0]:spans[j][1]].strip()
            if len(run) > max_chars or NOT_SNIPPET.search(run) or len(run.split()) < 3 or re.search(r"[.!?][A-Za-z]", run):
                continue
            score = (len(POSITIVE.findall(run)), -abs(len(run) - 55))
            if best is None or score > best[0]:
                best = (score, run)
    return best[1] if best else None


def review_snippets(items):
    """[(snippet, name, verified)] for stars: items are review numbers (reviews.json, best sentence picked) or
    {n, text} (text must be a verbatim part of that review) or {quote, author}."""
    revs = {r["n"]: r for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}
    norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    out = []
    for it in items:
        if isinstance(it, dict) and "quote" in it:
            out.append((it["quote"], it["author"], it.get("verified", False)))
            continue
        n = it["n"] if isinstance(it, dict) else int(it)
        r = revs[n]
        s = it.get("text") if isinstance(it, dict) else snippet(r["text"])
        if s and norm(s) not in norm(r["text"]):
            raise ValueError(f"stars: '{s}' is not a verbatim part of review {n}")
        if s:
            out.append((s, r["name"], r.get("verified")))
    return out


def l_stars(a, sd):
    """Social proof: a gold five-star row, 2-3 short verbatim snippets of real reviews with the customer's name, and the
    packshot. No rating numbers or review counts (the review data has none)."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", SAND)))
    d = ImageDraw.Draw(c)
    revs = review_snippets(a.get("reviews") or [])[:3]
    if len(revs) < 1:
        raise ValueError("stars: no usable review snippet")
    s = 54
    y = stars(d, W / 2 - (5 * s + 32) / 2, 66, s)
    fh = fit(d, a.get("headline") or "What our customers say", SERIF, a.get("hsize", 74), W - 140, 2)
    y = put(d, a.get("headline") or "What our customers say", fh, ESPRESSO, y + 36, W - 140, lh=1.0)
    py = H - 165
    fq, fn = SERIF(a.get("qsize", 44)), SANS(30, "SemiBold")

    def card_h(q):
        return 34 + put(d, "“" + q + "”", fq, INK, 0, W - 220, x=0, balance=False, dry=True) + air(fn) + sum(metrics(fn)) + 34
    while len(revs) > 1 and py - 40 - (y + 40 + sum(card_h(q) + 22 for q, _, _ in revs)) < a.get("min_photo", 300):
        revs = revs[:-1]          # a second / third card only when the packshot keeps its room
    yy = y + 40
    for q, name, verified in revs:
        h = card_h(q)
        card = note("box", (60, yy, W - 60, yy + h))
        d.rounded_rectangle([60, yy, W - 60, yy + h], radius=26, fill=WHITE)
        qb = put(d, "“" + q + "”", fq, INK, yy + 34, W - 220, x=110, balance=False, host=card)
        name_line(d, 110, qb + air(fn), name, verified, fn, host=card)
        yy += h + 22
    place_packshot(c, load(sd, a["photo"]), room((180, yy + 18, W - 180, py - 36), a.get("min_photo", 300)))
    pill(d, W, py, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def l_checklist(a, sd):
    """Packshot + 3-5 ticked features (the product's own feature tags) + the offer pill above the CTA. A tall bag stands
    right of the list; a wide bag (Vintage) goes on top with the list centred under it."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    ticks = list(a["ticks"])[:5]
    if len(ticks) < 2:
        raise ValueError("checklist: needs 2-5 ticks")
    fh = fit(d, a["headline"], SERIF, a.get("hsize", 84), W - 140, 2)
    y = put(d, a["headline"], fh, ESPRESSO, 66, W - 140, lh=1.0)
    if a.get("sub"):
        fs = SANS(40)
        y = put(d, a["sub"], fs, MUTED, y + air(fs, fh), W - 180, lh=1.3)
    py = H - 165
    bot = py - 44
    if a.get("offer"):
        oh = pill(d, W, 0, a["offer"], size=38, bold=True, dry=True)
        pill(d, W, py - 24 - oh, a["offer"], bg=RED, size=38, bold=True)
        bot = py - 24 - oh - 44
    im = load(sd, a["photo"])
    ft = SANS(a.get("tsize", 46), "SemiBold")       # (Julian: the small text a bit bigger)
    top = y + 56
    wide = packshot_aspect(im) > 1.2
    while True:          # 5 ticks only while they fit next to (tall bag) or under (wide bag) a full-size packshot
        if wide:
            lw = min(W - 160, max(width(d, t, ft) for t in ticks) + 2 * int(ft.size * 0.6) + int(ft.size * 0.55) + 4)
            th = tick_list(d, ticks, ft, 0, 0, lw, dry=True)
            short = bot - th - 48 - top < 300 * min(1.0, H / 1350)
        else:
            lw = int(W * 0.45) - 64
            th = tick_list(d, ticks, ft, 0, 0, lw, gap=int(ft.size * 1.0), dry=True)
            short = bot - top < th + 20
        if not short or len(ticks) <= 3:
            break
        ticks = ticks[:-1]
    if wide:
        place_packshot(c, im, room((90, top, W - 90, bot - th - 48), 300))
        tick_list(d, ticks, ft, (W - lw) / 2, bot - th, lw)
    else:                # the bag as big as its column allows, the ticks centred on it, the pair centred in the free
        room((0, top, 0, bot), th + 20, "ticks", scale=False)      # height (no empty band under the headline)
        x0, x1 = 64 + lw + 12, W - 20
        asp = packshot_aspect(im)
        ph = min(bot - top, (x1 - x0) / max(asp, 0.1))
        gap = int(ft.size * 1.0)
        if len(ticks) > 1 and th < 0.8 * ph:      # a short list next to a tall bag: the ticks spread over most of its
            gap = int(min(ft.size * 2.2, gap + (0.8 * ph - th) / (len(ticks) - 1)))   # height (no sparse band)
            th = tick_list(d, ticks, ft, 0, 0, lw, gap=gap, dry=True)
        bh = max(ph, th)
        y0 = top + max(0, (bot - top - bh) / 2)
        tick_list(d, ticks, ft, 64, y0 + (bh - th) / 2, lw, gap=gap)
        place_packshot(c, im, room((x0, y0 + (bh - ph) / 2, x1, y0 + (bh + ph) / 2), 300))
    pill(d, W, py, a.get("cta", "Shop now"), bg=ESPRESSO)
    return c.convert("RGBA")


# ---------------------------------------------------------------- Ad Library layouts (native, quotes, value)
def new_layouts():
    """The layouts modelled on the top-impression Ad Library statics, for make_batch's static cycle."""
    return ["native", "quotes", "value"]


def offer_text(a):
    """The offer as short text from the spec: pct -> '50% OFF', else the badge ({big, bottom} or a string); '' when none."""
    if a.get("pct"):
        if not 5 <= int(a["pct"]) <= 90:
            raise ValueError(f"pct {a['pct']} is not a real discount")
        return f"{int(a['pct'])}% OFF"
    b = a.get("badge")
    return " ".join(x for x in (b.get("big"), b.get("bottom")) if x) if isinstance(b, dict) else (b or "")


def money(s):
    """A price string as a number ('$119.95' -> 119.95); None when it has no number."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s or "")
    return float(m.group().replace(",", "")) if m else None


def studio_white(im, band=0.06, lim=244):
    """True for a studio packshot: the border band of the photo is white all around (not a real photo)."""
    g = whiten(im).convert("L")
    g.thumbnail((200, 200))
    w, h = g.size
    b = max(1, int(min(w, h) * band))
    px = [g.getpixel((x, y)) for y in range(h) for x in range(w) if x < b or y < b or x >= w - b or y >= h - b]
    return sum(v >= lim for v in px) / max(len(px), 1) > 0.9


_FACES = {}


def no_face(path, who):
    """Raises when the strict face check (new_product.count_faces: the one lifestyle photos pass) finds a face. Silent when
    no detector is installed (make_batch's QA checks every PNG again and keeps a face out of Drive)."""
    if path not in _FACES:
        try:
            if HERE not in sys.path:
                sys.path.insert(0, HERE)
            import new_product
            _FACES[path] = new_product.count_faces(path, strict=True)
        except Exception:  # noqa: BLE001
            _FACES[path] = None
    if _FACES[path]:
        raise ValueError(f"{who}: a face was found in the photo: never used")


def l_native(a, sd):
    """A phone-photo post: the real photo full bleed (cover-fit), nothing else but a small offer pill in the calmer top corner
    and one caption in the look of the video captions (white Montserrat, dark outline, soft shadow) in the lower third,
    where the photo is plainest. The spec's own words only; no sub, no CTA (the ad's button is the CTA)."""
    W, H = a.get("size", [1080, 1350])
    im = load(sd, a["photo"])
    if studio_white(im):
        raise ValueError("native: a studio packshot is not a real photo (needs a worn / lifestyle photo)")
    no_face(os.path.join(sd, a["photo"]), "native")
    if a.get("crop"):
        x0, y0, x1, y1 = a["crop"]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    text, offer = a.get("caption") or a.get("headline"), offer_text(a)
    if not (text or offer):
        raise ValueError("native: needs a caption (headline) or an offer")
    ph = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=tuple(a.get("focus", [0.5, 0.5])))
    if max(W / im.width, H / im.height) > 1.25:          # an upscaled phone photo: a little crispness back
        ph = ph.filter(ImageFilter.UnsharpMask(radius=1.8, percent=55, threshold=3))
    edge = ph.convert("L").resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.FIND_EDGES)
    calm = lambda box: ImageStat.Stat(edge.crop(tuple(int(v / 8) for v in box))).mean[0]  # noqa: E731  (low = plain)
    c = ph.convert("RGBA")
    d = ImageDraw.Draw(c)
    if offer:
        for psz in range(34, 21, -2):                     # a small pill: a long badge text shrinks to 62% of the width
            f = XB(psz)
            if width(d, offer, f) + 3 * f.size <= 0.62 * W:
                break
        w, h, m = width(d, offer, f) + 3 * f.size, int(f.size * 2.4), 40
        x = min((m, W - m - w), key=lambda x: calm((x, m, x + w, m + h)))
        sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x, m + 6, x + w, m + h + 6], radius=h / 2, fill=(0, 0, 0, 120))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
        pill(d, W, m, offer, bg=RED, size=psz, cx=x + w / 2, bold=True)
    if text:
        pad = 70
        for n, sizes in ((1, range(66, 57, -2)), (2, range(64, 39, -2)), (3, range(46, 33, -2))):   # one line only while big
            for sz in sizes:
                f = XB(sz)
                ls = wrap(d, text, f, W - 2 * pad, True)
                if len(ls) <= n and max(width(d, x, f) for x in ls) <= W - 2 * pad:
                    break
            else:
                continue
            break
        else:
            PROBLEMS.append("the caption does not fit three lines at 34 px")
        sw = max(3, round(f.size / 11))
        hb = put(d, ls, f, WHITE, 0, W, dry=True, stroke=sw)
        cy = min((k * H for k in (0.66, 0.70, 0.74, 0.78, 0.82)),
                 key=lambda y: calm((pad, y - hb / 2, W - pad, y + hb / 2)) + 60 * abs(y / H - 0.72))
        top = int(cy - hb / 2)
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        keep, TRACK[0] = TRACK[0], False                 # the shadow layer is not an element of the static
        put(ImageDraw.Draw(lay), ls, f, (0, 0, 0, 150), top + 5, W, cx=W / 2 + 3, stroke=sw + 2, stroke_fill=(0, 0, 0, 150))
        TRACK[0] = keep
        c.alpha_composite(lay.filter(ImageFilter.GaussianBlur(7)))
        put(d, ls, f, WHITE, top, W, stroke=sw)
    return c


def quote_items(a):
    """[(text, author, verified, stars)] for the quotes layout: the spec's 'quotes' [{text, author, verified?, stars?}] as passed
    (nothing is cut or rewritten), else 'reviews' (reviews.json numbers / {n, text}, verbatim-checked) like the stars layout."""
    out = [(q["text"], q.get("author"), q.get("verified", False), q.get("stars", True)) for q in a.get("quotes") or []
           if q.get("text")]
    if not out and a.get("reviews"):
        out = [(t, n, v, True) for t, n, v in review_snippets(a["reviews"])]
    return out[:2]


TAIL, TAIL_W = 36, 58        # a speech bubble's tail: its height and the width of its base


def bubble_size(d, q, fq, fn, max_w, pad=36):
    """(width, height, quote lines) of a speech-bubble card (without its tail): stars, the quote, '— Author'."""
    text, author, verified, stars_on = q
    ls = wrap(d, "“" + text.strip() + "”", fq, max_w - 2 * pad, True)
    nw = (width(d, "— " + author, fn) + (20 + width(d, "✓ Verified customer", SANS(28)) if verified else 0)) if author else 0
    w = max(max(width(d, x, fq) for x in ls), nw, 5 * 30 + 32 if stars_on else 0) + 2 * pad
    h = 30 + (30 + 16 if stars_on else 0) + put(d, ls, fq, INK, 0, max_w, x=0, lh=1.28, dry=True)
    h += (air(fn) + sum(metrics(fn))) if author else 0
    return int(w), int(h + 30), ls


def bubble(c, d, q, ls, fq, fn, x0, y0, w, h, tail_up, tail_x, lean, pad=36):
    """A white speech-bubble card at (x0, y0) of size w x h with a tail on its top (tail_up) or bottom edge from x = tail_x, its tip
    leaning `lean` px sideways (toward the product): soft shadow, gold stars, the quote, '— Author  ✓ Verified customer'."""
    text, author, verified, stars_on = q
    ty, ey = (y0 - TAIL, y0 + 2) if tail_up else (y0 + h + TAIL, y0 + h - 2)
    m = 90                                                  # (the blur needs room: a tight canvas leaves a visible edge)
    sh = Image.new("L", (w + 2 * m, h + 2 * m), 0)
    ImageDraw.Draw(sh).rounded_rectangle([m, m + 10, w + m, h + m + 10], radius=38, fill=70)
    c.paste((0, 0, 0), (x0 - m, y0 - m), sh.filter(ImageFilter.GaussianBlur(16)))
    host = note("box", (x0, min(y0, ty), x0 + w, max(y0 + h, ty)))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=38, fill=WHITE)
    d.polygon([(tail_x, ey), (tail_x + TAIL_W, ey), (tail_x + TAIL_W // 2 + lean, ty)], fill=WHITE)
    y = y0 + 30
    if stars_on:
        y = stars(d, x0 + pad, y, 30, host=host) + 16
    y = put(d, ls, fq, INK, y, w, x=x0 + pad, lh=1.28, host=host)
    if author:
        name_line(d, x0 + pad, y + air(fn), author, verified, fn, host=host)
    return host


def gift_tag(d, W, bottom, gift, dry=False):
    """'+ FREE ...' on a sand label whose bottom edge is at `bottom` (as in the offer layout); returns its top (dry: measure only)."""
    g = "+ " + re.sub(r"^\+\s*", "", gift).upper()
    fg = fit_font(d, g, XB, 34, W - 220, 22)
    asc = metrics(fg)[0]
    h, w = asc + int(fg.size * 1.15), width(d, g, fg) + 2 * fg.size
    gy = bottom - h
    if dry:
        return gy
    rb = note("label", (W / 2 - w / 2, gy, W / 2 + w / 2, gy + h), label=g)
    d.rounded_rectangle([W / 2 - w / 2, gy, W / 2 + w / 2, gy + h], radius=14, fill=SAND)
    d.text((W / 2, gy + h / 2 + asc / 2), g, font=fg, fill=ESPRESSO, anchor="ms", **FEAT)
    note("text", (W / 2 - w / 2 + fg.size, gy + h / 2 - asc / 2, W / 2 + w / 2 - fg.size, gy + h / 2 + asc / 2), host=rb,
         size=fg.size, label=g)
    return gy


def l_quotes(a, sd):
    """Social proof the way the top ads' copy reads: the packshot between two speech-bubble review cards (verbatim quote,
    author as in the review, e.g. 'Jenny H.'), the offer line and the CTA pill. Only quotes that were passed in are drawn: none =
    an error; one = one card. The quote text shrinks (to 30 px) before anything is cut: when two cards leave the packshot no room
    the second one is dropped (the shorter of the two stays)."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    qs = quote_items(a)
    if not qs:
        raise ValueError("quotes: no quote was passed in (none is ever made up)")
    offer = a.get("offer") or offer_text(a) or a.get("price") or ""
    gift, py = a.get("gift"), H - 165
    fo = fit_font(d, offer, XB, 60, W - 140, 34) if offer else None
    oh = (put(d, offer, fo, RED, 0, W - 140, dry=True) if offer else 0) + (1000 - gift_tag(d, W, 1000, gift, dry=True) + 18 if gift else 0)
    bot = py - 34 - oh - (58 if oh else 0)
    fn = SANS(30, "SemiBold")
    min_h = int(430 * min(1.0, H / 1350))
    head = a.get("headline")
    fh = fit(d, head, SERIF, 64, W - 140, 2) if head else None
    hh = (put(d, head, fh, ESPRESSO, 0, W - 140, lh=1.0, dry=True) + 30) if head else 0
    variants = [qs] + ([sorted(qs, key=lambda q: len(q[0]))[:1]] if len(qs) > 1 else [])

    def choose():
        """(cards, quote font, sizes, headline?, top, a_end, b_top) of the first fit that leaves the packshot min_h: the biggest
        quote text first, the headline dropped before the text shrinks, one card before text under 30 px."""
        for items in variants:
            for qsz in range(44, 29, -2):
                fq = SANS(qsz, "Medium")
                dims = [bubble_size(d, q, fq, fn, 880) for q in items]
                for wh in ((True, False) if head else (False,)):
                    top = 56 + (hh if wh else 0)
                    a_end = top + dims[0][1] + TAIL
                    b_top = bot - dims[1][1] - TAIL if len(items) > 1 else bot
                    if b_top - 18 - (a_end + 18) >= min_h:
                        return items, fq, dims, wh, top, a_end, b_top
        return None
    got = choose()
    if not got:                             # nothing leaves the photo its room: the smallest, the problem is recorded (room)
        fq = SANS(30, "Medium")
        items = variants[-1]
        dims = [bubble_size(d, q, fq, fn, 880) for q in items]
        got = items, fq, dims, False, 56, 56 + dims[0][1] + TAIL, bot
    items, fq, dims, with_head, top, a_end, b_top = got
    if with_head:
        put(d, head, fh, ESPRESSO, 56, W - 140, lh=1.0)
    ls = [dm[2] for dm in dims]
    def aim(x0, w):               # a tail's base x and lean: inside its card, its tip toward the packshot's middle
        tx = int(min(max(W / 2 - TAIL_W / 2 - 70, x0 + 60), x0 + w - 60 - TAIL_W))
        return tx, int(min(max((W / 2 - (tx + TAIL_W / 2)) * 0.4, -70), 70))
    tx, ln = aim(56, dims[0][0])
    bubble(c, d, items[0], ls[0], fq, fn, 56, top, dims[0][0], dims[0][1], False, tx, ln)
    photo = (90, a_end + 18, W - 90, b_top - 18)
    place_packshot(c, load(sd, a["photo"]), room(photo, 300))
    if len(items) > 1:
        bx = W - 56 - dims[1][0]
        tx, ln = aim(bx, dims[1][0])
        bubble(c, d, items[1], ls[1], fq, fn, bx, b_top + TAIL, dims[1][0], dims[1][1], True, tx, ln)
    y = py - 34 - oh
    if offer:
        y = put(d, offer, fo, RED, y, W - 140)
    if gift:
        gift_tag(d, W, py - 34, gift)
    pill(d, W, py, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")


def struck(d, x, base, text, f, fill=(150, 136, 124)):
    """A price with a strike line through its middle, left end at x on baseline `base`; returns its box."""
    bb = d.textbbox((x, base), text, font=f, anchor="ls", **FEAT)
    d.text((x, base), text, font=f, fill=fill, anchor="ls", **FEAT)
    mid = (bb[1] + bb[3]) / 2
    d.line([(bb[0] - 4, mid), (bb[2] + 4, mid)], fill=fill, width=max(3, f.size // 13))
    note("text", bb, size=f.size, label=text)
    return bb


def l_value(a, sd):
    """Price-led, on the brand cream: the big real price with the was price struck through beside a red '50% OFF' tag; with no
    price a red plate with '50% OFF'. Then the packshot, an optional gift label and the CTA. Numbers come from the spec only."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    price, was, off = a.get("price"), a.get("was"), offer_text(a)
    if not (price or off):
        raise ValueError("value: needs a price or a pct")
    if was and not price:
        raise ValueError("value: a was price without a price")
    if was and money(was) is not None and money(price) is not None:
        if money(was) <= money(price):
            raise ValueError(f"value: was {was} is not above {price}")
        if a.get("pct") and abs(100 * (1 - money(price) / money(was)) - int(a["pct"])) > 2:     # the tag must be true
            raise ValueError(f"value: {price} from {was} is not {a['pct']}% off")
    py, gift = H - 170, a.get("gift")
    bot = gift_tag(d, W, py - 40, gift, dry=True) - 28 if gift else py - 40     # (the label itself is drawn last)
    fb = font("Inter.ttf", 26, "SemiBold")
    fs, sub, head, fh = SANS(36), a.get("sub"), a.get("headline"), None

    def stack(psz, dry):
        """Draws (or just measures) everything above the photo for a price size; returns the bottom."""
        y = put(d, ["L I B R A   C A S E S"], fb, ESPRESSO, 54, W, cx=W / 2, dry=dry)
        prev = fb
        if fh:
            y = put(d, head, fh, ESPRESSO, y + 34, W - 140, lh=1.0, dry=dry)
            prev = fh
        if price:
            ft, fw, fp = XB(40), SANS(64), fit_font(d, price, BLACK, psz, W - 110, 80)
            if off or was:                                           # tag and struck was price on one row
                tw, th = width(d, off, ft) + 1.4 * ft.size if off else 0, metrics(ft)[0] + ft.size
                ww, wh = width(d, was, fw) if was else 0, sum(metrics(fw))
                rh, top = max(th if off else 0, wh if was else 0), y + air(fp, prev, 0.3)
                if not dry:
                    x = W / 2 - (tw + ww + (30 if off and was else 0)) / 2
                    if off:
                        tag(d, x + tw / 2, top + (rh - th) / 2, off, RED, ft, kind="pill")
                        x += tw + 30
                    if was:
                        struck(d, x, top + (rh - wh) / 2 + metrics(fw)[0], was, fw)
                y = top + rh
            top = y + air(fp, prev, 0.12 if (off or was) else 0.28) + int(0.1 * fp.size)        # ('$' rises above the caps)
            if was:
                top += int(0.25 * min(fw.size, fp.size))
            y = put(d, price, fp, INK, top, W, lh=1.0, dry=dry)
            prev = fp
        else:                                                        # no price: the % as a red plate
            fp = fit_font(d, off, BLACK, int(psz * 0.95), W - 260, 70)
            ph_ = sum(metrics(fp)) + int(fp.size * 0.5)
            top = y + air(fp, prev, 0.3)
            pw = width(d, off, fp) + fp.size
            if not dry:
                pl = note("box", (W / 2 - pw / 2, top, W / 2 + pw / 2, top + ph_))
                d.rounded_rectangle([W / 2 - pw / 2, top, W / 2 + pw / 2, top + ph_], radius=int(fp.size * 0.3), fill=RED)
                put(d, off, fp, WHITE, top + int(fp.size * 0.25), W, host=pl)
            y, prev = top + ph_, fp
        if sub:
            y = put(d, sub, fs, MUTED, y + air(fs, prev, 0.5), W - 180, lh=1.3, dry=dry)
        return y
    opts = [(n, p) for n in (520, 440, 360) for p in range(240, 149, -10)] + [(340, p) for p in range(140, 109, -10)]
    for sub, head in ((a.get("sub"), a.get("headline")),) + (((None, a.get("headline")), (None, None)) if SCALE[0] < 0.8 else ()):
        fh = fit(d, head, SERIF, 70, W - 140, 2) if head else None       # (smaller type first; only then the optional lines go)
        psz = next((p for n, p in opts if bot - (stack(p, True) + 36) >= int(n * min(1.0, H / 1350))), None)   # the bag's room first
        if psz:
            break
    psz = psz or 110
    y = stack(psz, False)
    place_packshot(c, load(sd, a["photo"]), room((110, y + 36, W - 110, bot), 340))
    if gift:
        gift_tag(d, W, py - 40, gift)
    pill(d, W, py, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")


LAYOUTS = {k[2:]: v for k, v in globals().items() if k.startswith("l_")}


def render(ad, sd, tries=6):
    """The static as an RGB image, checked for overlaps and off-canvas elements; retried with 5% smaller type while
    anything collides. Raises LayoutError when the last attempt still does."""
    TRACK[0] = True
    try:
        for k in range(tries):
            SCALE[0], CANVAS[0] = 0.95 ** k, (ad.get("size") or [1080, 1080 if ad["layout"] == "carousel" else 1350])[1]
            DRAWN.clear()
            PROBLEMS.clear()
            im = LAYOUTS[ad["layout"]](ad, sd)
            bad = PROBLEMS + collisions(*im.size)
            if not bad:
                if k:
                    print(f"{ad.get('name')}: type at {SCALE[0]:.0%} so nothing overlaps", file=sys.stderr)
                return im.convert("RGB")
        raise LayoutError("; ".join(list(dict.fromkeys(bad))[:4]))
    finally:
        SCALE[0], TRACK[0], CANVAS[0] = 1.0, False, 1350
        DRAWN.clear()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--only")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any static failed (default: report and go on)")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    MASKS.update(spec.get("masks", {}))
    CARD.update(spec.get("card_photos", []))
    CROPS.update(spec.get("crops", {}))
    sd = os.path.dirname(os.path.abspath(a.spec))
    os.makedirs(a.outdir, exist_ok=True)
    failed = []
    for ad in spec["ads"]:
        if a.only and not ad["name"].startswith(a.only):
            continue
        out = os.path.join(a.outdir, ad["name"] + ".png")
        try:
            im = render(ad, sd)
        except Exception as e:  # noqa: BLE001  one broken static never stops the batch; its PNG is missing -> QA flags it
            if os.path.exists(out):
                os.remove(out)           # no stale PNG from an earlier run in its place
            failed.append(ad["name"])
            print(f"FAILED {ad['name']}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            continue
        im.save(out, "PNG", optimize=True)
        print(out, im.size)
    if failed and a.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()

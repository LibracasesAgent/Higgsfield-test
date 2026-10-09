#!/usr/bin/env python3
"""Brand-styled Facebook statics (1080x1350 / 1080x1080) built from real product photos.

White-background packshots are composited with a multiply blend, so the studio white turns into the
card colour and the natural contact shadow is kept (no background removal needed).

  python3 pipeline/brand_statics.py spec.json --outdir out/

spec.json: {"ads": [{"name": "...", "layout": "<layout>", "size": [1080, 1350], ...layout fields...}]}

Layouts
  hero      photo, headline, sub, cta, badge?                      clean product hero
  promo     photo, headline, sub, features[3], badge, cta          espresso frame + cream panel (Ads Library style)
  callouts  photo, headline, points[{text, x, y, tx, ty}], cta     feature callouts with leader lines
  review    photo, review_n (pipeline/data/reviews.json) or quote/name, headline?   big quote card
  compare   photo, headline, left_title, left[], right_title, right[]           other bags vs ours
  colours   photos[{src, name}], headline, sub, cta                colour picker grid
  bold      photo, lines[], sub, cta, accent                       big condensed type
  lifestyle photo (full bleed, crop/focus), headline, sub, cta     photo + text box
  carousel  photo, headline, label, sub                            1080x1080 card for a carousel
"""
import argparse
import json
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps, features

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "assets", "fonts")
CREAM, SAND, ESPRESSO, INK = (246, 241, 234), (236, 226, 212), (58, 40, 28), (24, 20, 18)
RED, GOLD, WHITE = (200, 22, 40), (184, 137, 59), (255, 255, 255)
FEAT = {"features": ["lnum"]} if features.check("raqm") else {}   # lining figures: Cormorant's old-style '2in1' reads '2ını'


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


SERIF = lambda s: font("CormorantGaramond.ttf", s, "SemiBold")  # noqa: E731
SANS = lambda s, w="Medium": font("Inter.ttf", s, w)  # noqa: E731
BLACK = lambda s: font("Montserrat.ttf", s, "Black")  # noqa: E731
XB = lambda s: font("Montserrat.ttf", s, "ExtraBold")  # noqa: E731


MASKS = {}   # src -> list of [x0, y0, x1, y1] fractions painted white (baked-in "NEW"/"SALE" badges)


def load(spec_dir, src):
    im = ImageOps.exif_transpose(Image.open(os.path.join(spec_dir, src))).convert("RGB")
    if src in MASKS:
        d = ImageDraw.Draw(im)  # white-fill baked-in badges on studio-white shots
        for x0, y0, x1, y1 in MASKS[src]:
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


def place_packshot(canvas, im, box, trim=True):
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
    return (px, py, px + im.width, py + im.height)


def wrap(d, text, f, max_w):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if cur and d.textlength(t, font=f, **FEAT) > max_w:
                out.append(cur)
                cur = w
            else:
                cur = t
        out.append(cur)
    return out


def text_c(d, W, y, text, f, fill, max_w=None, lh=1.12):
    lines = wrap(d, text, f, max_w or W - 120)
    bottom = y
    for ln in lines:
        tw = d.textlength(ln, font=f, **FEAT)
        d.text(((W - tw) / 2, y), ln, font=f, fill=fill, **FEAT)
        bottom = d.textbbox(((W - tw) / 2, y), ln, font=f, **FEAT)[3] if ln.strip() else y
        y += int(f.size * lh)
    return max(y, bottom + 10)      # a descender ('p', 'y') of the last line never touches what comes next


def fit_font(d, text, maker, size, max_w, min_size=40):
    f = maker(size)
    longest = lambda f: max(d.textlength(t, font=f, **FEAT) for t in text.split("\n"))  # noqa: E731
    while longest(f) > max_w and size > min_size:
        size -= 4
        f = maker(size)
    return f


def pill(d, W, y, text, bg=ESPRESSO, fg=WHITE, size=36):
    f = font("Inter.ttf", size, "SemiBold")
    tw = d.textlength(text, font=f)
    w, h = tw + 110, int(size * 2.4)
    x = (W - w) / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    a, de = f.getmetrics()
    d.text((x + 55, y + (h - a - de) / 2), text, font=f, fill=fg)
    return y + h


def badge(canvas, cx, cy, r, top, big, bottom, colour=RED, angle=-12):
    lay = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([10, 10, 10 + 2 * r, 10 + 2 * r], fill=colour + (255,))
    d.ellipse([22, 22, 2 * r - 2, 2 * r - 2], outline=(255, 255, 255, 170), width=3)
    fb, fs = BLACK(int(r * 0.62)), XB(int(r * 0.2))
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


def brand_mark(d, W, y, colour=ESPRESSO):
    f = font("Inter.ttf", 26, "SemiBold")
    t = "L I B R A   C A S E S"
    tw = d.textlength(t, font=f)
    d.text(((W - tw) / 2, y), t, font=f, fill=colour)


# ---------------------------------------------------------------- layouts
def l_hero(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    brand_mark(d, W, 58)
    y = text_c(d, W, 120, a["headline"], SERIF(a.get("hsize", 112)), ESPRESSO, W - 140, 1.0)
    if a.get("sub"):
        y = text_c(d, W, y + 14, a["sub"], SANS(38), (90, 70, 56), W - 200, 1.3)
    place_packshot(c, load(sd, a["photo"]), (90, y + 40, W - 90, H - 230))
    c = c.convert("RGBA")
    if a.get("badge"):
        b = a["badge"]
        badge(c, W - 175, y + 150, 120, b.get("top", ""), b["big"], b.get("bottom", ""))
    d = ImageDraw.Draw(c)
    pill(d, W, H - 175, a.get("cta", "Shop now"))
    return c


def l_promo(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), ESPRESSO)
    d = ImageDraw.Draw(c)
    m = 46
    d.rounded_rectangle([m, 190, W - m, H - 230], radius=28, fill=CREAM)
    f = fit_font(d, a["headline"], SERIF, 92, W - 120)
    text_c(d, W, 62, a["headline"], f, (250, 236, 214), W - 100, 1.0)
    if a.get("sub"):
        text_c(d, W, 222, a["sub"], SANS(36, "SemiBold"), ESPRESSO, W - 200)
    place_packshot(c, load(sd, a["photo"]), (m + 60, 300, W - m - 60, H - 420))
    # features row
    feats = a.get("features", [])
    if feats:
        fw = (W - 2 * m - 60) / len(feats)
        fy = H - 400
        for i, t in enumerate(feats):
            x0 = m + 30 + i * fw
            d.rounded_rectangle([x0 + 8, fy, x0 + fw - 8, fy + 140], radius=18, fill=SAND)
            ls = wrap(d, t, SANS(30, "SemiBold"), fw - 40)
            yy = fy + 70 - len(ls) * 19
            for ln in ls:
                tw = d.textlength(ln, font=SANS(30, "SemiBold"))
                d.text((x0 + fw / 2 - tw / 2, yy), ln, font=SANS(30, "SemiBold"), fill=ESPRESSO)
                yy += 38
    c = c.convert("RGBA")
    if a.get("badge"):
        b = a["badge"]
        badge(c, W - 170, 380, 118, b.get("top", ""), b["big"], b.get("bottom", ""))
    d = ImageDraw.Draw(c)
    pill(d, W, H - 175, a.get("cta", "Shop now"), bg=RED)
    return c


def l_callouts(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", CREAM)))
    d = ImageDraw.Draw(c)
    y = text_c(d, W, 70, a["headline"], fit_font(d, a["headline"], SERIF, 96, W - 120), ESPRESSO, W - 120, 1.0)
    bx = place_packshot(c, load(sd, a["photo"]), tuple(a.get("photo_box", (250, y + 40, W - 250, H - 220))))
    f = SANS(a.get("psize", 36), "SemiBold")
    for p in a["points"]:
        # p.x, p.y are fractions of the placed photo box; tx, ty canvas pixels for the label
        px = bx[0] + p["x"] * (bx[2] - bx[0])
        py = bx[1] + p["y"] * (bx[3] - bx[1])
        lines = wrap(d, p["text"], f, 260)
        tw = max(d.textlength(l, font=f) for l in lines)
        lx, ly = p["tx"], p["ty"]
        lh = int(f.size * 1.25)
        bw, bh = tw + 40, lh * len(lines) + 26
        x0 = lx if lx < W / 2 else lx - bw
        d.line([(px, py), (x0 + (bw if lx < W / 2 else 0), ly + bh / 2)], fill=GOLD, width=3)
        d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=GOLD, outline=WHITE, width=3)
        d.rounded_rectangle([x0, ly, x0 + bw, ly + bh], radius=16, fill=WHITE, outline=(226, 214, 198), width=2)
        for i, ln in enumerate(lines):
            d.text((x0 + 20, ly + 12 + i * lh), ln, font=f, fill=ESPRESSO)
    pill(d, W, H - 165, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def stars(d, x, y, s=40, colour=GOLD):
    for k in range(5):
        cx, cy, r = x + k * (s + 8) + s / 2, y + s / 2, s / 2
        pts = [(cx + (r if j % 2 == 0 else r * 0.45) * math.cos(math.pi / 2 + j * math.pi / 5),
                cy - (r if j % 2 == 0 else r * 0.45) * math.sin(math.pi / 2 + j * math.pi / 5)) for j in range(10)]
        d.polygon(pts, fill=colour)


def l_review(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), tuple(a.get("bg", SAND)))
    d = ImageDraw.Draw(c)
    if a.get("review_n"):
        r = next(x for x in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"] if x["n"] == a["review_n"])
        quote, name, verified = r["text"], r["name"], r.get("verified")
    else:
        quote, name, verified = a["quote"], a.get("author", a["name"]), a.get("verified", True)
    if a.get("headline"):
        text_c(d, W, 70, a["headline"], SERIF(84), ESPRESSO, W - 140, 1.0)
    # card
    cy0 = 210 if a.get("headline") else 120
    fq = SERIF(a.get("qsize", 54))
    lines = wrap(d, "“" + quote + "”", fq, W - 260)
    ch = 150 + len(lines) * int(fq.size * 1.12) + 90
    d.rounded_rectangle([70, cy0, W - 70, cy0 + ch], radius=34, fill=WHITE)
    stars(d, 130, cy0 + 60)
    yy = cy0 + 130
    for ln in lines:
        d.text((130, yy), ln, font=fq, fill=INK, **FEAT)
        yy += int(fq.size * 1.12)
    fn = SANS(34, "SemiBold")
    d.text((130, yy + 24), "— " + name, font=fn, fill=ESPRESSO)
    if verified:
        vx = 130 + d.textlength("— " + name, font=fn) + 18
        d.text((vx, yy + 30), "✓ Verified customer", font=SANS(28), fill=(70, 120, 70))
    place_packshot(c, load(sd, a["photo"]), (160, cy0 + ch + 30, W - 160, H - 200))
    pill(d, W, H - 165, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def l_compare(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(c)
    text_c(d, W, 64, a["headline"], fit_font(d, a["headline"], SERIF, 92, W - 120), ESPRESSO, W - 120, 1.0)
    place_packshot(c, load(sd, a["photo"]), (300, 200, W - 300, 600))
    cw = (W - 150) / 2
    for k, (title, items, good) in enumerate(((a["left_title"], a["left"], False), (a["right_title"], a["right"], True))):
        x0 = 60 + k * (cw + 30)
        d.rounded_rectangle([x0, 640, x0 + cw, H - 210], radius=26, fill=(ESPRESSO if good else (226, 220, 212)))
        fg = WHITE if good else (110, 100, 92)
        ft = XB(40)
        tw = d.textlength(title, font=ft)
        d.text((x0 + cw / 2 - tw / 2, 676), title, font=ft, fill=fg)
        yy = 760
        for it in items:
            mark = "✓" if good else "✗"
            d.text((x0 + 34, yy), mark, font=SANS(40, "Bold"), fill=(GOLD if good else (170, 70, 70)))
            ls = wrap(d, it, SANS(32, "Medium"), cw - 110)
            for ln in ls:
                d.text((x0 + 86, yy + 4), ln, font=SANS(32, "Medium"), fill=fg)
                yy += 42
            yy += 26
    pill(d, W, H - 165, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")


def l_colours(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(c)
    y = text_c(d, W, 64, a["headline"], fit_font(d, a["headline"], SERIF, 100, W - 120), ESPRESSO, W - 120, 1.0)
    if a.get("sub"):
        y = text_c(d, W, y + 6, a["sub"], SANS(36), (90, 70, 56), W - 200)
    ph = a["photos"]
    cols = 3 if len(ph) > 4 else 2
    rows = math.ceil(len(ph) / cols)
    gx, gy0, gy1 = 50, y + 30, H - 210
    cw, chh = (W - 2 * gx) / cols, (gy1 - gy0) / rows
    for i, p in enumerate(ph):
        x0, y0 = gx + (i % cols) * cw, gy0 + (i // cols) * chh
        d.rounded_rectangle([x0 + 10, y0 + 10, x0 + cw - 10, y0 + chh - 10], radius=22, fill=WHITE)
        place_packshot(c, load(sd, p["src"]), (int(x0 + 30), int(y0 + 26), int(x0 + cw - 30), int(y0 + chh - 76)))
        f = SANS(30, "SemiBold")
        tw = d.textlength(p["name"], font=f)
        d.text((x0 + cw / 2 - tw / 2, y0 + chh - 64), p["name"], font=f, fill=ESPRESSO)
    pill(d, W, H - 165, a.get("cta", "Shop now"))
    return c.convert("RGBA")


def l_bold(a, sd):
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(c)
    y = 70
    acc = tuple(a.get("accent", RED))
    for i, ln in enumerate(a["lines"]):
        f = fit_font(d, ln, BLACK, a.get("size_px", 138), W - 100)
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill=(acc if i in a.get("accent_lines", [0]) else INK))
        y += int(f.size * 1.02)
    if a.get("sub"):
        y = text_c(d, W, y + 10, a["sub"], SANS(38, "SemiBold"), (70, 60, 52), W - 160)
    place_packshot(c, load(sd, a["photo"]), (110, y + 20, W - 110, H - 230))
    if a.get("dots"):
        n = len(a["dots"])
        x = W / 2 - (n * 60 - 16) / 2
        for col in a["dots"]:
            d.ellipse([x, H - 225, x + 44, H - 181], fill=tuple(col), outline=(200, 200, 200), width=2)
            x += 60
    pill(d, W, H - 160, a.get("cta", "Shop now"), bg=INK)
    return c.convert("RGBA")


def l_lifestyle(a, sd):
    W, H = a.get("size", [1080, 1350])
    im = load(sd, a["photo"])
    if a.get("crop"):
        x0, y0, x1, y1 = a["crop"]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    c = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=tuple(a.get("focus", [0.5, 0.5]))).convert("RGBA")
    d = ImageDraw.Draw(c)
    pos = a.get("text_pos", "bottom")
    fh = fit_font(d, a["headline"], SERIF, a.get("hsize", 96), W - 160)
    lines = wrap(d, a["headline"], fh, W - 160)
    bh = 60 + len(lines) * int(fh.size * 1.02) + (70 if a.get("sub") else 0) + 130
    by = 60 if pos == "top" else H - bh - 50
    panel = Image.new("RGBA", (W - 100, bh), CREAM + (238,))
    c.alpha_composite(panel, (50, by))
    d = ImageDraw.Draw(c)
    y = text_c(d, W, by + 40, a["headline"], fh, ESPRESSO, W - 160, 1.02)
    if a.get("sub"):
        y = text_c(d, W, y + 4, a["sub"], SANS(34), (80, 64, 52), W - 220)
    pill(d, W, y + 18, a.get("cta", "Shop now"), size=32)
    return c



def l_split(a, sd):
    """Before / after: two photos side by side under a headline."""
    W, H = a.get("size", [1080, 1350])
    c = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(c)
    y = text_c(d, W, 56, a["headline"], fit_font(d, a["headline"], SERIF, 92, W - 120), ESPRESSO, W - 120, 1.0)
    if a.get("sub"):
        y = text_c(d, W, y + 4, a["sub"], SANS(34), (90, 70, 56), W - 180)
    top, bot, g = y + 30, H - 200, 24
    cw = (W - 100 - g) // 2
    for k, (src, lab) in enumerate(((a["left"], a.get("left_label", "BEFORE")), (a["right"], a.get("right_label", "AFTER")))):
        x0 = 50 + k * (cw + g)
        ph = ImageOps.fit(load(sd, src).convert("RGB"), (cw, bot - top), Image.LANCZOS, centering=tuple(a.get("focus", [0.5, 0.5])))
        m = Image.new("L", ph.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], radius=26, fill=255)
        c.paste(ph, (x0, top), m)
        f = XB(34)
        tw = d.textlength(lab, font=f)
        bx = x0 + cw / 2 - tw / 2
        d.rounded_rectangle([bx - 24, top + 22, bx + tw + 24, top + 82], radius=30, fill=(RED if k else INK))
        d.text((bx, top + 30), lab, font=f, fill=WHITE)
    pill(d, W, H - 165, a.get("cta", "Shop now"), bg=RED)
    return c.convert("RGBA")

def l_carousel(a, sd):
    W, H = a.get("size", [1080, 1080])
    c = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(c)
    text_c(d, W, 50, a["headline"], fit_font(d, a["headline"], SERIF, 78, W - 120), ESPRESSO, W - 120, 1.0)
    place_packshot(c, load(sd, a["photo"]), (120, 190, W - 120, H - 170))
    if a.get("label"):
        f = BLACK(64)
        tw = d.textlength(a["label"], font=f)
        d.rounded_rectangle([60, 180, 60 + tw + 60, 180 + 96], radius=48, fill=ESPRESSO)
        d.text((90, 188), a["label"], font=f, fill=WHITE)
    if a.get("sub"):
        text_c(d, W, H - 130, a["sub"], SANS(38, "SemiBold"), ESPRESSO)
    return c.convert("RGBA")


LAYOUTS = {k[2:]: v for k, v in globals().items() if k.startswith("l_")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--only")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    MASKS.update(spec.get("masks", {}))
    CARD.update(spec.get("card_photos", []))
    CROPS.update(spec.get("crops", {}))
    sd = os.path.dirname(os.path.abspath(a.spec))
    os.makedirs(a.outdir, exist_ok=True)
    for ad in spec["ads"]:
        if a.only and not ad["name"].startswith(a.only):
            continue
        im = LAYOUTS[ad["layout"]](ad, sd).convert("RGB")
        out = os.path.join(a.outdir, ad["name"] + ".png")
        im.save(out, "PNG", optimize=True)
        print(out, im.size)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""UGC-style static ads: a real photo + typeset overlays (never AI-generated text).

  python3 pipeline/ugc_statics.py spec.json --outdir out/

spec.json: {"ads": [{"name": "...", "base": "photo.jpg" | null, "focus": [0.5, 0.5],
                      "crop": [x0, y0, x1, y1] (fractions, optional), "elements": [ ... ]}]}
Element types (coordinates are pixels on the 1080x1350 canvas):
  caption   {"text", "y", "size"}                         white rounded box, black Montserrat (native caption)
  postit    {"text", "x", "y", "w", "angle"}              yellow sticky note with Caveat handwriting
  marker    {"text", "x", "y", "size", "angle"}           red Permanent Marker text
  circle    {"box": [x0, y0, x1, y1]}                     hand-drawn red ellipse
  arrow     {"from": [x, y], "to": [x, y]}                hand-drawn red arrow
  notes     {"x", "y", "w", "title", "lines", "struck"}   Notes-style card; struck = indexes crossed out
  receipt   {"x", "y", "w", "lines", "angle"}             thermal receipt (Courier Prime)
  letters   {"items": [{"t": "A", "x", "y"}], "size"}     big handwritten letters on the photo
  handwrite {"lines", "x", "y", "size", "angle", "ticks"}  pen handwriting (Caveat) straight onto paper in the photo;
                                                          ticks = indexes that get a red hand-drawn check mark
  strip     {"frames": [paths], "labels": [..]}           2x2 frame-by-frame grid (base may be null)
"""
import argparse
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1350
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
RED = (226, 30, 36)


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


def wrap(d, text, f, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) > max_w and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
    return lines


def base_image(ad, spec_dir):
    if not ad.get("base"):
        return Image.new("RGB", (W, H), (244, 239, 232))
    im = ImageOps.exif_transpose(Image.open(os.path.join(spec_dir, ad["base"]))).convert("RGB")
    if ad.get("crop"):
        x0, y0, x1, y1 = ad["crop"]
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    return ImageOps.fit(im, (W, H), Image.LANCZOS, centering=tuple(ad.get("focus", [0.5, 0.5])))


def paste_rotated(canvas, layer, x, y, angle, shadow=True):
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    if shadow:
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 90), mask=layer.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        canvas.alpha_composite(sh, (int(x + 8), int(y + 12)))
    canvas.alpha_composite(layer, (int(x), int(y)))


def el_caption(c, e):
    d = ImageDraw.Draw(c)
    f = font("Montserrat.ttf", e.get("size", 58), "ExtraBold")
    lines = wrap(d, e["text"], f, 920)
    lh = int(f.size * 1.22)
    y = e["y"]
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.rounded_rectangle([(W - tw) / 2 - 26, y - 12, (W + tw) / 2 + 26, y + f.size + 16], radius=18,
                            fill=(255, 255, 255, 248))
        d.text(((W - tw) / 2, y), ln, font=f, fill=(0, 0, 0, 255))
        y += lh + 14


def el_postit(c, e):
    w = e.get("w", 340)
    note = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    d = ImageDraw.Draw(note)
    d.rectangle([0, 0, w, w], fill=(255, 236, 110, 255))
    d.rectangle([0, 0, w, int(w * 0.08)], fill=(247, 222, 86, 255))       # sticky strip
    f = font("Caveat.ttf", e.get("size", 56), "Bold")
    lines = wrap(d, e["text"], f, w - 50)
    y = int(w * 0.14)
    for ln in lines:
        d.text((26, y), ln, font=f, fill=(24, 40, 96, 255))
        y += int(f.size * 1.05)
    paste_rotated(c, note, e["x"], e["y"], e.get("angle", -4))


def el_marker(c, e):
    f = font("PermanentMarker.ttf", e.get("size", 46))
    d0 = ImageDraw.Draw(c)
    lines = wrap(d0, e["text"], f, e.get("max_w", 520))
    lw = int(max(d0.textlength(l, font=f) for l in lines)) + 40
    lay = Image.new("RGBA", (lw, int(f.size * 1.3 * len(lines)) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, ln in enumerate(lines):
        d.text((6 + 4, 4 + i * int(f.size * 1.3)), ln, font=f, fill=tuple(e.get("color", RED)) + (255,),
               stroke_width=e.get("stroke", 5), stroke_fill=(255, 255, 255, 255))
    paste_rotated(c, lay, e["x"], e["y"], e.get("angle", 0), shadow=False)


def wobble_line(d, pts, width):
    random.seed(len(pts))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.line([(x0, y0), (x1, y1)], fill=RED + (255,), width=width, joint="curve")


def el_circle(c, e):
    d = ImageDraw.Draw(c)
    x0, y0, x1, y1 = e["box"]
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    pts = []
    for k in range(0, 380, 6):  # slightly more than a full turn, like a quick marker loop
        a = math.radians(k - 20)
        r = 1 + 0.04 * math.sin(k / 23)
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    wobble_line(d, pts, 9)


def el_arrow(c, e):
    d = ImageDraw.Draw(c)
    (x0, y0), (x1, y1) = e["from"], e["to"]
    mx, my = (x0 + x1) / 2 + (y1 - y0) * 0.12, (y0 + y1) / 2 - (x1 - x0) * 0.12   # gentle curve
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1)
           for t in [i / 20 for i in range(21)]]
    wobble_line(d, pts, 8)
    ang = math.atan2(y1 - pts[-3][1], x1 - pts[-3][0])
    for s in (-1, 1):
        d.line([(x1, y1), (x1 - 42 * math.cos(ang + s * 0.5), y1 - 42 * math.sin(ang + s * 0.5))],
               fill=RED + (255,), width=8)


def el_notes(c, e):
    w = e.get("w", 640)
    ft, fl = font("Inter.ttf", 58, "Bold"), font("Inter.ttf", 54, "Regular")
    lh = 80
    h = 140 + lh * len(e["lines"]) + 30
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, w, h], radius=28, fill=(255, 253, 246, 245))
    d.text((36, 34), e["title"], font=ft, fill=(20, 20, 20, 255))
    for i, ln in enumerate(e["lines"]):
        y = 138 + i * lh
        d.text((36, y), ln, font=fl, fill=(40, 40, 40, 255))
        if i in e.get("struck", []):
            tw = d.textlength(ln, font=fl)
            d.line([(32, y + 34), (40 + tw, y + 30)], fill=(40, 40, 40, 255), width=5)
    paste_rotated(c, card, e["x"], e["y"], e.get("angle", 0))


def el_receipt(c, e):
    w = e.get("w", 520)
    f = font("CourierPrime.ttf", 34)
    lh = 48
    h = 80 + lh * len(e["lines"]) + 50
    rc = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(rc)
    d.rectangle([0, 0, w, h - 14], fill=(250, 250, 246, 255))
    for x in range(0, w, 20):  # torn zig-zag bottom edge
        d.polygon([(x, h - 14), (x + 10, h), (x + 20, h - 14)], fill=(250, 250, 246, 255))
    for i, ln in enumerate(e["lines"]):
        y = 44 + i * lh
        if ln == "---":
            d.line([(30, y + 22), (w - 30, y + 22)], fill=(60, 60, 60, 255), width=2)
            continue
        left, _, right = ln.partition("|")
        d.text((30, y), left, font=f, fill=(30, 30, 30, 255))
        if right:
            rw = d.textlength(right, font=f)
            d.text((w - 30 - rw, y), right, font=f, fill=(30, 30, 30, 255))
    paste_rotated(c, rc, e["x"], e["y"], e.get("angle", 3))


def el_handwrite(c, e):
    f = font("Caveat.ttf", e.get("size", 44), "Bold")
    lh = int(f.size * 1.25)
    d0 = ImageDraw.Draw(c)
    lw = int(max(d0.textlength(l, font=f) for l in e["lines"])) + 90
    lay = Image.new("RGBA", (lw, lh * len(e["lines"]) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i, ln in enumerate(e["lines"]):
        y = i * lh
        d.text((0, y), ln, font=f, fill=tuple(e.get("color", (24, 40, 96))) + (255,))
        if i in e.get("ticks", []):
            x = d.textlength(ln, font=f) + 18
            d.line([(x, y + lh * 0.55), (x + 12, y + lh * 0.8), (x + 40, y + lh * 0.2)], fill=RED + (255,), width=6,
                   joint="curve")
    paste_rotated(c, lay, e["x"], e["y"], e.get("angle", 0), shadow=False)


def el_letters(c, e):
    d = ImageDraw.Draw(c)
    f = font("PermanentMarker.ttf", e.get("size", 120))
    for it in e["items"]:
        d.text((it["x"] + 4, it["y"] + 4), it["t"], font=f, fill=(0, 0, 0, 120))
        d.text((it["x"], it["y"]), it["t"], font=f, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))


def el_strip(c, e, spec_dir):
    cw, ch = 510, 600
    f = font("Caveat.ttf", 80, "Bold")
    d = ImageDraw.Draw(c)
    for i, fp in enumerate(e["frames"][:4]):
        im = ImageOps.fit(Image.open(os.path.join(spec_dir, fp)).convert("RGB"), (cw, ch), Image.LANCZOS)
        x, y = 20 + (i % 2) * (cw + 20), 130 + (i // 2) * (ch + 20)
        c.paste(im, (x, y))
        lab = e.get("labels", ["1", "2", "3", "4"])[i]
        d.text((x + 18, y + 6), lab, font=f, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255))


def render(ad, spec_dir):
    c = base_image(ad, spec_dir).convert("RGBA")
    for e in ad["elements"]:
        t = e["type"]
        if t == "strip":
            el_strip(c, e, spec_dir)
        else:
            globals()[f"el_{t}"](c, e)
    return c.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    spec_dir = os.path.dirname(os.path.abspath(a.spec))
    os.makedirs(a.outdir, exist_ok=True)
    for ad in spec["ads"]:
        img = render(ad, spec_dir)
        out = os.path.join(a.outdir, f"{ad['name']}.png")
        img.save(out, "PNG")
        img.resize((360, 450), Image.LANCZOS).save(os.path.join(a.outdir, f"{ad['name']}_phone.jpg"), quality=85)
        print(out)


if __name__ == "__main__":
    main()

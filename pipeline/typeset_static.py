#!/usr/bin/env python3
"""Typeset a Facebook static ad over a generated product image.

Text is set with real fonts (never generated), so it is always spelled right.
Outputs: a sRGB PNG at the requested size, a 2x master PNG, and an editable SVG
(background image + separate text layers) for Figma/Illustrator.

  python3 pipeline/typeset_static.py --image hero.png --out ad_4x5 \
      --headline "Meet the Hobo Bag." --sub "Soft, structured leather. Two gold side zips." \
      --cta "Shop Now" --serif fonts/CormorantGaramond.ttf --sans fonts/Inter.ttf
"""
import argparse
import base64
import html
import io
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def fit(img, w, h):
    """Scale to cover w x h and center-crop."""
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.5))


def render(args, scale):
    W, H = args.width * scale, args.height * scale
    base = fit(Image.open(args.image), W, H)
    d = ImageDraw.Draw(base)
    ink = tuple(int(args.ink[i:i + 2], 16) for i in (1, 3, 5))
    layers = []

    y = int(args.top * H)
    hf = font(args.serif, int(args.headline_size * scale), "SemiBold")
    for line in args.headline.split("|"):
        tw = d.textlength(line, font=hf)
        d.text(((W - tw) / 2, y), line, font=hf, fill=ink)
        layers.append(("headline", line, W / 2, y, hf.size, "Cormorant Garamond", 600, args.ink))
        y += int(hf.size * 1.05)

    if args.sub:
        sf = font(args.sans, int(args.sub_size * scale), "Regular")
        y += int(18 * scale)
        tw = d.textlength(args.sub, font=sf)
        d.text(((W - tw) / 2, y), args.sub, font=sf, fill=ink + (230,))
        layers.append(("sub", args.sub, W / 2, y, sf.size, "Inter", 400, args.ink))

    if args.cta:
        cf = font(args.sans, int(args.cta_size * scale), "SemiBold")
        tw = d.textlength(args.cta, font=cf)
        pw, ph = tw + 2 * int(34 * scale), int(cf.size * 2.3)
        px, py = (W - pw) / 2, H - int(args.bottom * H) - ph
        d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph / 2, fill=ink)
        asc, desc = cf.getmetrics()
        d.text((px + (pw - tw) / 2, py + (ph - asc - desc) / 2), args.cta, font=cf, fill=(250, 244, 236))
        layers.append(("cta", args.cta, W / 2, py, cf.size, "Inter", 600, "#faf4ec", (px, py, pw, ph)))
    return base, layers


def svg(args, layers):
    W, H = args.width, args.height
    buf = io.BytesIO()
    fit(Image.open(args.image), W * 2, H * 2).save(buf, "JPEG", quality=92)
    img64 = base64.b64encode(buf.getvalue()).decode()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<g id="background"><image width="{W}" height="{H}" xlink:href="data:image/jpeg;base64,{img64}"/></g>']
    ink = args.ink
    for layer in layers:
        name, text, cx, y, size, family, weight, color = layer[:8]
        if name == "cta":
            px, py, pw, ph = layer[8]
            parts.append(f'<g id="cta"><rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="{ph / 2:.1f}" fill="{ink}"/>'
                         f'<text x="{cx:.1f}" y="{py + ph / 2:.1f}" dominant-baseline="central" text-anchor="middle" font-family="{family}" font-weight="{weight}" font-size="{size}" fill="{color}">{html.escape(text)}</text></g>')
        else:
            parts.append(f'<text id="{name}" x="{cx:.1f}" y="{y + size * 0.8:.1f}" text-anchor="middle" font-family="{family}" font-weight="{weight}" font-size="{size}" fill="{color}">{html.escape(text)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True, help="output path without extension")
    ap.add_argument("--headline", required=True, help="use | for a line break")
    ap.add_argument("--sub", default="")
    ap.add_argument("--cta", default="Shop Now")
    ap.add_argument("--serif", required=True)
    ap.add_argument("--sans", required=True)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1350)
    ap.add_argument("--ink", default="#3a2a1f")
    ap.add_argument("--top", type=float, default=0.075, help="headline top as fraction of height")
    ap.add_argument("--bottom", type=float, default=0.055, help="CTA bottom margin as fraction of height")
    ap.add_argument("--headline-size", type=int, default=92)
    ap.add_argument("--sub-size", type=int, default=30)
    ap.add_argument("--cta-size", type=int, default=28)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    img, layers = render(args, 1)
    img.save(args.out + ".png", "PNG", icc_profile=None)
    render(args, 2)[0].save(args.out + "@2x.png", "PNG")
    img.resize((args.width // 3, args.height // 3), Image.LANCZOS).save(args.out + "_phone_preview.png")
    with open(args.out + ".svg", "w") as f:
        f.write(svg(args, layers))
    print(f"{args.out}.png  {args.out}@2x.png  {args.out}.svg  {args.out}_phone_preview.png")


if __name__ == "__main__":
    main()

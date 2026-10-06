#!/usr/bin/env python3
"""Product photos + facts from libracases.com (Shopify), for statics and new-product ads.

  python3 pipeline/site_assets.py "Hobo Bag" --out /tmp/run/site
  python3 pipeline/site_assets.py luxury-anti-theft-hobo-bag-2-0 --out /tmp/run/site

Writes <out>/<key>_00.jpg, _01.jpg ... (full-size product images, in site order) and
<out>/<key>_facts.json (title, price, compare-at price, colours/options, description text).
Image 00 often has baked-in "BEST SELLER" / "CLEARANCE SALE" badges in the corners: prefer a
later image, or mask the badge in the brand_statics spec ("masks").
"""
import argparse
import html
import json
import os
import re
import urllib.request

SITE = "https://libracases.com"
HANDLES = {  # names used in briefs and requests -> Shopify handle
    "hobo bag": "luxury-hobo-handbag-special-gift-1",
    "hobo": "luxury-hobo-handbag-special-gift-1",
    "hobo bag print": "luxury-hobo-anti-theft-handbag-print-free-pouch-wallet",
    "hobo 2.0": "luxury-anti-theft-hobo-bag-2-0",
    "hobo2": "luxury-anti-theft-hobo-bag-2-0",
    "3-piece set": "luxury-leather-hobo-3-piece-bag-set",
    "hobo bag 3-piece set": "luxury-leather-hobo-3-piece-bag-set",
    "slouchy": "the-slouchy-soft-leather-3-piece-set",
    "slouchy soft 3-piece set": "the-slouchy-soft-leather-3-piece-set",
    "vintage bag": "libra-vintage-bag",
    "vintage": "libra-vintage-bag",
    "backpack": "2-in-1-convertible-backpack-tote-free-pouch",
    "silhouette bag": "the-silhouette-bag",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def find_handle(name):
    key = name.lower().strip()
    if key in HANDLES:
        return HANDLES[key]
    prods = json.loads(get(f"{SITE}/products.json?limit=250"))["products"]
    for p in prods:
        if key == p["handle"]:
            return p["handle"]
    words = key.split()
    best = max(prods, key=lambda p: sum(w in p["title"].lower() for w in words))
    return best["handle"]


def clean_score(path):
    """1.0 = plain packshot on white with empty corners (no baked-in SALE/BEST SELLER badge, no scene)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((200, 200))
    w, h = im.size
    px = im.load()

    def white(x0, y0, x1, y1):
        n = k = 0
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                r, g, b = px[x, y]
                n += 1
                k += r > 232 and g > 232 and b > 232
        return k / max(n, 1)
    b = 0.08
    border = (white(0, 0, w, h * b) + white(0, h * (1 - b), w, h) + white(0, 0, w * b, h) + white(w * (1 - b), 0, w, h)) / 4
    corners = min(white(0, 0, w * .25, h * .16), white(w * .75, 0, w, h * .16))
    return round(border * corners, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product", help="product name or Shopify handle")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=20)
    a = ap.parse_args()
    handle = find_handle(a.product)
    p = json.loads(get(f"{SITE}/products/{handle}.json"))["product"]
    os.makedirs(a.out, exist_ok=True)
    key = re.sub(r"[^a-z0-9]+", "_", a.product.lower()).strip("_")[:24]
    files = []
    for i, im in enumerate(p["images"][:a.max]):
        f = os.path.join(a.out, f"{key}_{i:02d}.jpg")
        if not os.path.exists(f):
            open(f, "wb").write(get(im["src"]))
        files.append(f)
    colours = {}
    by_id = {im["id"]: im["src"] for im in p["images"]}
    for var in p["variants"]:
        img = (var.get("featured_image") or {}).get("src") or by_id.get(var.get("image_id"))
        name = var.get("option1") or var["title"]
        if img and name not in colours:
            f = os.path.join(a.out, f"{key}_colour_{re.sub(r'[^a-z0-9]+', '_', name.lower())}.jpg")
            if not os.path.exists(f):
                open(f, "wb").write(get(img))
            colours[name] = f
    scores = {f: clean_score(f) for f in files + list(colours.values())}
    clean = [f for f in sorted(scores, key=lambda f: -scores[f]) if scores[f] >= 0.8]
    v = p["variants"][0]
    text = html.unescape(re.sub(r"<[^>]+>", " ", p.get("body_html") or ""))
    facts = dict(handle=handle, url=f"{SITE}/products/{handle}", title=p["title"], price=v.get("price"),
                 compare_at=v.get("compare_at_price"),
                 options={o["name"]: o["values"] for o in p.get("options", [])},
                 description=re.sub(r"\s+", " ", text).strip()[:4000], images=files,
                 colours=colours, clean_images=clean, scores=scores)
    json.dump(facts, open(os.path.join(a.out, f"{key}_facts.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(handle=handle, title=p["title"], price=v.get("price"), images=len(files),
                          colours=list(colours), clean=len(clean), facts=os.path.join(a.out, f"{key}_facts.json")),
                     ensure_ascii=False))
    return facts


if __name__ == "__main__":
    main()

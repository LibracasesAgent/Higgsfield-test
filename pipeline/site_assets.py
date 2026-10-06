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
    "hobo bag": "luxury-hobo-anti-theft-handbag-print-free-pouch-wallet",
    "hobo": "luxury-hobo-anti-theft-handbag-print-free-pouch-wallet",
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
    v = p["variants"][0]
    text = html.unescape(re.sub(r"<[^>]+>", " ", p.get("body_html") or ""))
    facts = dict(handle=handle, url=f"{SITE}/products/{handle}", title=p["title"], price=v.get("price"),
                 compare_at=v.get("compare_at_price"),
                 options={o["name"]: o["values"] for o in p.get("options", [])},
                 description=re.sub(r"\s+", " ", text).strip()[:4000], images=files)
    json.dump(facts, open(os.path.join(a.out, f"{key}_facts.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(handle=handle, title=p["title"], price=v.get("price"), images=len(files),
                          options=facts["options"]), ensure_ascii=False))


if __name__ == "__main__":
    main()

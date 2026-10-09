#!/usr/bin/env python3
"""Product photos + facts from libracases.com (Shopify), for statics and new-product ads.

  python3 pipeline/site_assets.py "Hobo Bag" --out /tmp/run/site
  python3 pipeline/site_assets.py luxury-anti-theft-hobo-bag-2-0 --out /tmp/run/site
  python3 pipeline/site_assets.py https://libracases.com/products/the-silhouette-bag?variant=1 --out /tmp/run/site
  python3 pipeline/site_assets.py "silhouete" --find          (only print the matched handle)

The product is a full product URL, a Shopify handle, a known name (HANDLES below, or the key/aliases of
pipeline/data/products/*.json), or else a title match over /products.json. A weak or ambiguous title
match exits 2 with the close matches listed: rerun with the exact handle, never guess.

Writes <out>/<key>_00.jpg, _01.jpg ... (full-size product images, in site order) and
<out>/<key>_facts.json (title, price, compare-at price, colours/options, description text, bullets).
Colour names drop sales suffixes ("Black + Free Small Purse" -> "Black").
Image 00 often has baked-in "BEST SELLER" / "CLEARANCE SALE" badges in the corners: prefer a
later image, or mask the badge in the brand_statics spec ("masks").
"""
import argparse
import difflib
import glob
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

SITE = "https://libracases.com"
HERE = os.path.dirname(os.path.abspath(__file__))
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
    "2in1 backpack": "2-in-1-convertible-backpack-tote-free-pouch",
    "silhouette bag": "the-silhouette-bag",
}
GENERIC = {"the", "a", "and", "with", "bag", "bags", "handbag", "leather", "luxury", "free", "pouch", "wallet", "new", "libra"}
MIN_SCORE, MARGIN = 0.6, 0.15


class NoMatch(LookupError):
    pass


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def handle_from_url(text):
    m = re.search(r"/products/([a-z0-9][a-z0-9\-]*)", text.lower())
    return m.group(1) if m else None


def clean_colour(name):
    """'Black + Free Small Purse' -> 'Black'; 'Brown (Free Pouch Wallet)' -> 'Brown'."""
    s = re.sub(r"\s*(?:\+|&|-|–|with|\()\s*free\b.*$", "", name or "", flags=re.I)
    return re.sub(r"\s+", " ", s).strip() or (name or "").strip()


def known_handles():
    """HANDLES plus key / aliases / name of every pipeline/data/products/*.json that has a site handle."""
    out = dict(HANDLES)
    for f in sorted(glob.glob(os.path.join(HERE, "data", "products", "*.json"))):
        try:
            d = json.load(open(f))
        except (ValueError, OSError):
            continue
        if d.get("site"):
            for n in [d.get("key"), d.get("name"), d.get("short")] + list(d.get("aliases") or []):
                if n:
                    out.setdefault(n.lower().strip(), d["site"])
    return out


def all_products():
    prods, page = [], 1
    while page < 10:
        got = json.loads(get(f"{SITE}/products.json?limit=250&page={page}"))["products"]
        prods += got
        if len(got) < 250:
            return prods
        page += 1
    return prods


def words(s):
    return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", s.lower())


def match_score(query, p):
    """Weighted share of the query's words found in the product title/handle (typos ok, generic words count 1/4)."""
    tw = set(words(p["title"])) | set(words(p["handle"].replace("-", " ")))
    compact = re.sub(r"[^a-z0-9]", "", (p["title"] + p["handle"]).lower())
    tot = got = 0.0
    for w in words(query):
        wt = 0.25 if w in GENERIC else 1.0
        tot += wt
        if w in tw or (len(w) >= 3 and w in compact) or difflib.get_close_matches(w, tw, 1, 0.85):
            got += wt
    return round(got / tot, 3) if tot else 0.0


def find_handle(name, prods=None):
    """URL / handle / known alias, else a clear title match. Raises NoMatch (with close matches) otherwise."""
    text = name.strip()
    h = handle_from_url(text) if ("/" in text or "libracases" in text.lower()) else None
    if h:
        return h
    key = re.sub(r"\s+", " ", text.lower())
    known = known_handles()
    if key in known:
        return known[key]
    prods = prods if prods is not None else all_products()
    handles = {p["handle"] for p in prods}
    if key in handles:
        return key
    if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", key):  # looks like a handle: try it directly (unlisted products)
        try:
            get(f"{SITE}/products/{key}.json")
            return key
        except urllib.error.HTTPError:
            pass
    ranked = sorted(((match_score(key, p), p) for p in prods), key=lambda x: -x[0])
    close = [f"{s:.2f}  {p['handle']}  ({p['title']})" for s, p in ranked[:5] if s > 0]
    best = ranked[0][0] if ranked else 0
    second = ranked[1][0] if len(ranked) > 1 else 0
    if best >= MIN_SCORE and best - second >= MARGIN:
        return ranked[0][1]["handle"]
    why = "is ambiguous" if best >= MIN_SCORE else "matches no product well enough"
    raise NoMatch(f"'{name}' {why} on libracases.com. Rerun with the exact handle or product URL."
                  + ("\nClose matches (score, handle, title):\n  " + "\n  ".join(close) if close else ""))


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


def corner_badges(path, size=240):
    """Baked-in sale tags in the top corners of a packshot, as (side, [x0, y0, x1, y1] fractions): dark/coloured blobs
    that touch the left or right edge and stay in the top third ('NEW', 'BEST SELLER', the round 'CLEARANCE SALE')."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((size, size))
    w, h = im.size
    px = im.load()
    dark = bytearray(min(px[x, y]) < 215 for y in range(h) for x in range(w))
    seen, out = bytearray(w * h), []
    for y in range(int(h * .16)):
        for x in list(range(int(w * .25))) + list(range(int(w * .75), w)):
            i = y * w + x
            if not dark[i] or seen[i]:
                continue
            st, comp, seen[i] = [i], [], 1
            while st and len(comp) < w * h * .2:     # flood fill (8-connected)
                j = st.pop()
                comp.append(j)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = j % w + dx, j // w + dy
                        k = ny * w + nx
                        if 0 <= nx < w and 0 <= ny < h and dark[k] and not seen[k]:
                            seen[k] = 1
                            st.append(k)
            xs, ys = [j % w for j in comp], [j // w for j in comp]
            box = [min(xs) / w, min(ys) / h, (max(xs) + 1) / w, (max(ys) + 1) / h]
            if st or box[3] > .35 or len(comp) < w * h * .001 or (box[0] > .05 and box[2] < .95):
                continue                             # the product itself (runs down), a speck, or away from the edge
            pad = .015
            out.append(("left" if box[0] <= .05 else "right",
                        [round(max(box[0] - pad, 0), 3), round(max(box[1] - pad, 0), 3), round(min(box[2] + pad, 1), 3),
                         round(min(box[3] + pad, 1), 3)]))
    return out


def unbadged(path, out_dir):
    """A copy of a site photo without its baked-in tag, or None when it cannot be cleaned. Rectangular tags on the
    left edge ('NEW', 'BEST SELLER') are covered with the backdrop just below them; a photo with a round sale badge
    on the right ('CLEARANCE SALE 50% OFF') is refused (masking leaves a ghost of it). Clean photos come back as is."""
    from PIL import Image
    tags = corner_badges(path)
    if not tags:
        return path
    if any(side == "right" for side, _ in tags):
        return None
    im = Image.open(path).convert("RGB")
    for _, (x0, y0, x1, y1) in tags:
        b = [int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)]
        im.paste(im.crop((b[0], b[3], b[2], b[3] + b[3] - b[1])), (b[0], b[1]))
    os.makedirs(out_dir, exist_ok=True)
    f = os.path.join(out_dir, os.path.basename(path))
    im.save(f, quality=95)
    return None if corner_badges(f) else f


def bullets(body):
    """Feature-ish snippets from the product HTML: <li> items, else sentences; plus the bold phrases."""
    body = body or ""
    txt = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()  # noqa: E731
    items = [txt(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", body, re.S | re.I)]
    if not items:
        for para in re.split(r"</p>|<br\s*/?>|\n", body, flags=re.I):
            items += re.split(r"(?<=[.!?])\s+(?=[A-Z])", txt(para))
    strong = [txt(x).strip(" .,:;") for x in re.findall(r"<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>", body, re.S | re.I)]
    return [i for i in items if len(i.split()) >= 3], [s for s in strong if s]


def fetch(product, out, max_images=20, key=None):
    """Download images + write <key>_facts.json into out; returns the facts dict."""
    handle = find_handle(product)
    try:
        p = json.loads(get(f"{SITE}/products/{handle}.json"))["product"]
    except urllib.error.HTTPError as e:
        raise NoMatch(f"libracases.com has no product with handle '{handle}' (HTTP {e.code})")
    os.makedirs(out, exist_ok=True)
    key = key or re.sub(r"[^a-z0-9]+", "_", (handle if handle_from_url(product) else product).lower()).strip("_")[:24]
    files = []
    for i, im in enumerate(p["images"][:max_images]):
        f = os.path.join(out, f"{key}_{i:02d}.jpg")
        if not os.path.exists(f):
            open(f, "wb").write(get(im["src"]))
        files.append(f)
    colours = {}
    by_id = {im["id"]: im["src"] for im in p["images"]}
    for var in p["variants"]:
        img = (var.get("featured_image") or {}).get("src") or by_id.get(var.get("image_id"))
        name = clean_colour(var.get("option1") or var["title"])
        if img and name not in colours:
            f = os.path.join(out, f"{key}_colour_{re.sub(r'[^a-z0-9]+', '_', name.lower())}.jpg")
            if not os.path.exists(f):
                open(f, "wb").write(get(img))
            colours[name] = f
    scores = {f: clean_score(f) for f in files + list(colours.values())}
    clean = [f for f in sorted(scores, key=lambda f: -scores[f]) if scores[f] >= 0.8]
    v = p["variants"][0]
    text = html.unescape(re.sub(r"<[^>]+>", " ", p.get("body_html") or ""))
    bl, strong = bullets(p.get("body_html"))
    facts = dict(handle=handle, url=f"{SITE}/products/{handle}", title=p["title"], price=v.get("price"),
                 compare_at=v.get("compare_at_price"),
                 options={o["name"]: [clean_colour(x) for x in o["values"]] for o in p.get("options", [])},
                 description=re.sub(r"\s+", " ", text).strip()[:4000], images=files,
                 colours=colours, clean_images=clean, scores=scores,
                 variant_titles=[var["title"] for var in p["variants"]], bullets=bl, highlights=strong)
    json.dump(facts, open(os.path.join(out, f"{key}_facts.json"), "w"), indent=1, ensure_ascii=False)
    facts["facts_file"] = os.path.join(out, f"{key}_facts.json")
    return facts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product", help="product URL, Shopify handle or product name")
    ap.add_argument("--out")
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--find", action="store_true", help="only resolve and print the handle")
    a = ap.parse_args()
    try:
        if a.find or not a.out:
            print(find_handle(a.product))
            return
        facts = fetch(a.product, a.out, a.max)
    except NoMatch as e:
        print(f"site_assets: {e}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(dict(handle=facts["handle"], title=facts["title"], price=facts["price"], images=len(facts["images"]),
                          colours=list(facts["colours"]), clean=len(facts["clean_images"]), facts=facts["facts_file"]),
                     ensure_ascii=False))
    return facts


if __name__ == "__main__":
    main()

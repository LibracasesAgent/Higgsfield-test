#!/usr/bin/env python3
"""New-product intake: a product folder in Drive "New Products" (or a site link) -> a draft product file
pipeline/data/products/<slug>.json that make_batch.py can build ads from. Schema: pipeline/data/products/README.md.

  list    python3 pipeline/new_product.py list
          Subfolders of New Products, newest first: photo / clip / note counts and the product file status.
  intake  python3 pipeline/new_product.py intake "Silhouette Bag"        (a New Products subfolder, by name)
          python3 pipeline/new_product.py intake --latest                 (the newest subfolder)
          python3 pipeline/new_product.py intake --site https://libracases.com/products/the-silhouette-bag \
              [--name "The Silhouette Bag"]
          python3 pipeline/new_product.py intake --local ~/bag_folder --name "Silhouette Bag"
          Downloads photos (-> jpg), clips and notes into pipeline/cache/new_products/<slug>/, reads the site
          (price, compare-at, colours, description), scores photos (clean, faces), proposes 3 start times per
          clip, makes contact sheets + overview.jpg, drafts the offer and 3-5 features, writes the file with
          status "draft". Claude then looks at overview.jpg, rewrites what is wrong, sets status "ready".
  check   python3 pipeline/new_product.py check silhouette-bag            (slug or path; exit 1 on problems)

Never invents an offer: the % comes only from the site's compare-at price, the gift only from a quoted
"free pouch / wallet / purse / gift" phrase on the site or in the client's notes.
"""
import argparse
import datetime
import glob
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import site_assets  # noqa: E402

PRODUCTS_DIR = os.path.join(HERE, "data", "products")
CACHE_DIR = os.path.join(HERE, "cache", "new_products")
FOLDER = "application/vnd.google-apps.folder"
GDOC = "application/vnd.google-apps.document"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
CLIP_EXT = {".mp4", ".mov", ".m4v"}
NOTE_EXT = {".txt", ".md", ".url"}
GENERIC = site_assets.GENERIC | {"tote", "set", "crossbody", "shoulder", "piece", "3-piece", "mini", "small", "large"}
GIFT = re.compile(r"\bfree\s+(?:(?:matching|small|mini|bonus|little|leather)\s+){0,2}"
                  r"(?:pouch(?:\s+wallet)?|wallet|purse|clutch|gift|keychain|charm|card\s*holder)\b", re.I)
SITE_URL = re.compile(r"(?:https?://)?(?:www\.)?libracases\.com/\S*?products/[A-Za-z0-9\-]+", re.I)
SALESY = re.compile(r"%|\bsale\b|ends tonight|\bfree (?:delivery|shipping)\b|\bdiscount|\bshipping\b|\bprice\b|"
                    r"\border\b|http|libracases\.com|limited time|today only", re.I)
TAGS = [  # (pattern in the sentence, on-screen tag): first hit wins, so specific before generic
    (r"anti-?theft", "ANTI-THEFT POCKET"), (r"\brfid\b", "RFID LINING"), (r"lockable|\block", "LOCKABLE ZIPPERS"),
    (r"cut-?resistant", "CUT-RESISTANT STRAP"), (r"convertible|backpack, tote|switch\b", "CONVERTIBLE STRAPS"),
    (r"laptop", "FITS A LAPTOP"), (r"water-?(?:resistant|proof)", "WATER-RESISTANT LEATHER"),
    (r"scratch", "SCRATCH-PROOF LEATHER"), (r"compartment", "SMART COMPARTMENTS"), (r"hidden pocket", "HIDDEN POCKETS"),
    (r"pocket", "HANDY POCKETS"), (r"zip", "ZIP CLOSURE"), (r"adjustable|removable", "ADJUSTABLE STRAP"),
    (r"strap", "EASY STRAPS"), (r"crossbody|ways to wear|in hand", "WEAR IT YOUR WAY"),
    (r"spacious|room for|fits? (?:your|all|everything)|holds", "ROOM FOR EVERYTHING"),
    (r"lightweight", "LIGHTWEIGHT"), (r"silhouette|structured|shape", "SLEEK SHAPE"), (r"leather", "SOFT LEATHER"),
    (r"stitch|finish", "CLEAN FINISH"), (r"free .*pouch|pouch", "FREE MATCHING POUCH"),
]
CLIP_TOPICS = [  # words that link a feature line to a clip file name
    {"strap", "straps", "convertible", "wear", "wearing", "crossbody", "backpack", "tote", "shoulder", "handle"},
    {"inside", "fits", "room", "spacious", "laptop", "essentials", "putting", "stuff", "pack", "packing", "holds", "open"},
    {"water", "resistant", "snow", "rain", "weather", "proof", "cold", "snowing"},
    {"walk", "walking", "carry", "carrying", "anywhere", "day", "outdoor", "grocery", "car"},
    {"leather", "details", "detail", "close", "macro", "scratch", "stitching", "finish"},
    {"pocket", "pockets", "zip", "zipper", "keys", "wallet", "phone", "back"},
    {"outfit", "style", "styling", "sleek", "look", "looks", "blazer", "dress"},
]
HAAR_URL = "https://raw.githubusercontent.com/opencv/opencv/4.10.0/data/haarcascades/haarcascade_frontalface_default.xml"
HOOKY = re.compile(r"wear|walk|styl|outfit|carry|street|outside", re.I)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def rel(p):
    """Repo-relative path (absolute when outside the repo, e.g. a test cache)."""
    r = os.path.relpath(p, ROOT) if p else p
    return p if r and r.startswith("..") else r


def names_for(display):
    name = re.sub(r"\s+", " ", display).strip()
    short = re.sub(r"^the\s+", "", name, flags=re.I)
    key = short.lower()
    return key, name, short, (name if name.lower().startswith("the ") else "The " + short)


def clean_title(title):
    """'Luxury Leather 2-in-1 Convertible Backpack + Free Pouch' -> '2-in-1 Convertible Backpack'."""
    t = re.sub(r"\([^)]*\)", "", site_assets.clean_colour(title))
    return re.sub(r"^luxury\s+(?:pu\s+)?leather\s+", "", re.sub(r"\s+", " ", t).strip(), flags=re.I)


def aliases_for(key, extra):
    """Distinctive words of the key + folder name + site handle; never a built-in product's name ("hobo", "vintage")."""
    try:
        from make_batch import PRODUCT_KEYS, PRODUCTS
        reserved = set(PRODUCTS) | set(PRODUCT_KEYS)
    except Exception:  # noqa: BLE001
        reserved = set()
    distinct = " ".join(w for w in key.split() if w not in GENERIC)
    last = distinct.split()[-1] if distinct else ""
    out = []
    for a in [distinct, last if len(last) >= 4 else ""] + [x.lower().strip() for x in extra if x]:
        if a and a != key and a not in out and a not in reserved:
            out.append(a)
    return out


def say(n):
    ones = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
            "seventeen eighteen nineteen").split()
    tens = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
    return ones[n] if n < 20 else tens[n // 10] + ("-" + ones[n % 10] if n % 10 else "")


def dumps(o, ind=0):
    """JSON with short lists/dicts on one line, so a product file stays easy to read and edit."""
    s = json.dumps(o, ensure_ascii=False)
    if len(s) + ind <= 118 or not isinstance(o, (dict, list)) or not o:
        return s
    p = " " * (ind + 1)
    if isinstance(o, dict):
        body = ",\n".join(f"{p}{json.dumps(k, ensure_ascii=False)}: {dumps(v, ind + 1)}" for k, v in o.items())
        return "{\n" + body + "\n" + " " * ind + "}"
    return "[\n" + ",\n".join(p + dumps(v, ind + 1) for v in o) + "\n" + " " * ind + "]"


def load_product(ref, products_dir=PRODUCTS_DIR):
    path = ref if os.path.exists(ref) else os.path.join(products_dir, slugify(ref) + ".json")
    return path, json.load(open(path))


def load_all(products_dir=PRODUCTS_DIR):
    """{key: product} for every product file (any status)."""
    out = {}
    for f in sorted(glob.glob(os.path.join(products_dir, "*.json"))):
        try:
            d = json.load(open(f))
            out[d["key"]] = d
        except (ValueError, KeyError, OSError):
            continue
    return out


def lookup(text, products_dir=PRODUCTS_DIR):
    """The product file whose key / alias / name / slug occurs in text (longest name wins), or None."""
    t = (text or "").lower()
    best = None
    for k, d in load_all(products_dir).items():
        for n in [k, d.get("name", ""), d.get("short", ""), slugify(k)] + list(d.get("aliases") or []):
            n = (n or "").lower()
            if n and n in t and (best is None or len(n) > best[0]):
                best = (len(n), d)
    return best[1] if best else None


# ---------------------------------------------------------------- sources
def kind(name, mime=""):
    ext = os.path.splitext(name)[1].lower()
    if mime == GDOC or ext in NOTE_EXT or mime in ("text/plain", "text/markdown"):
        return "note"
    if mime.startswith("image/") or ext in PHOTO_EXT:
        return "photo"
    if mime.startswith("video/") or ext in CLIP_EXT:
        return "clip"
    return None


def drive_files(token, folder_id):
    """Files of a product folder plus one level of subfolders (photos/, clips/ ...)."""
    from drive_upload import list_children
    out = []
    for f in list_children(token, folder_id):
        if f["mimeType"] == FOLDER:
            out += [dict(x, sub=f["name"]) for x in list_children(token, f["id"]) if x["mimeType"] != FOLDER]
        else:
            out.append(f)
    return out


def local_files(d):
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*")) + glob.glob(os.path.join(d, "*", "*"))):
        if os.path.isfile(p) and not os.path.basename(p).startswith("."):
            out.append(dict(id=None, name=os.path.basename(p), mimeType="", size=os.path.getsize(p), local=p))
    return out


def product_folders(token):
    from drive_upload import list_children
    from index_library import load_config
    return [f for f in list_children(token, load_config()["drive"]["new_products_folder"]) if f["mimeType"] == FOLDER]


def unique(path, taken):
    """path, or path_2, path_3 ... when another file of this intake already took the name (reruns overwrite)."""
    base, ext = os.path.splitext(path)
    k, out = 2, path
    while out in taken:
        out, k = f"{base}_{k}{ext}", k + 1
    taken.add(out)
    return out


def fetch_file(f, dest, token):
    """Drive download (skipped when the cached copy has the same size) or local copy."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if f.get("local"):
        if not (os.path.exists(dest) and os.path.getsize(dest) == f["size"]):
            shutil.copy2(f["local"], dest)
        return dest
    if os.path.exists(dest) and str(os.path.getsize(dest)) == str(f.get("size")):
        return dest
    from drive_upload import download
    return download(token, f["id"], dest)


def note_text(f, cache, token):
    if f.get("mimeType") == GDOC:
        from drive_upload import export_text
        txt = export_text(token, f["id"])
        open(os.path.join(cache, "notes", slugify(f["name"]) + ".txt"), "w").write(txt)
        return txt
    p = fetch_file(f, os.path.join(cache, "notes", f["name"]), token)
    return open(p, errors="replace").read()


# ---------------------------------------------------------------- photos
def to_jpg(src, dst, warn):
    from PIL import Image, ImageOps
    ext = os.path.splitext(src)[1].lower()
    if ext in (".heic", ".heif"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:  # other converters, if installed (ffmpeg reads HEIC from 7.0 on)
            for cmd in (["heif-convert", src, dst], ["magick", src, dst],
                        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-frames:v", "1", "-q:v", "2", "-y", dst]):
                if shutil.which(cmd[0]) and subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(dst):
                    return dst
            warn(f"skipped {os.path.basename(src)}: HEIC needs pillow-heif (pip install pillow-heif)")
            return None
    try:
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    except Exception as e:  # noqa: BLE001
        warn(f"skipped {os.path.basename(src)}: cannot read image ({e})")
        return None
    im.thumbnail((2400, 2400))
    im.save(dst, quality=92)
    return dst


_DET = []


def face_detector():
    """Haar frontal-face cascade: from cv2.data, else pipeline/cache/models (downloaded once: opencv 5 wheels ship none)."""
    if _DET:
        return _DET[0]
    import cv2
    name = "haarcascade_frontalface_default.xml"
    local = os.path.join(HERE, "cache", "models", name)
    path = next((p for p in (os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), name), local)
                 if os.path.exists(p)), None)
    if not path:
        os.makedirs(os.path.dirname(local), exist_ok=True)
        open(local, "wb").write(site_assets.get(HAAR_URL))
        path = local
    det = cv2.CascadeClassifier(path)
    _DET.append(None if det.empty() else det)
    return _DET[0]


def count_faces(path):
    try:
        import cv2
        det = face_detector()
    except Exception:  # noqa: BLE001  (no opencv, or the cascade could not be fetched)
        return None
    img = cv2.imread(path)
    if img is None or det is None:
        return None
    s = 900 / max(img.shape[:2])
    if s < 1:
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = max(24, int(min(gray.shape) * 0.06))
    boxes = det.detectMultiScale(cv2.equalizeHist(gray), scaleFactor=1.1, minNeighbors=6, minSize=(m, m))
    if not len(boxes) or cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 1].mean() < 20:  # none, or a b/w photo: trust Haar
        return len(boxes)
    ycc = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    n = 0
    for x, y, w, h in boxes:  # a real face box is mostly skin; bag charms / buckles / stitching are not
        r = ycc[y + h // 5:y + 4 * h // 5, x + w // 5:x + 4 * w // 5]
        n += ((r[..., 1] >= 135) & (r[..., 1] <= 180) & (r[..., 2] >= 85) & (r[..., 2] <= 135)).mean() >= 0.25
    return int(n)


# ---------------------------------------------------------------- clips
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height:"
                        "stream_side_data=rotation:stream_tags=rotate", "-of", "json", path], capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    rot = (v.get("tags") or {}).get("rotate") or next((sd.get("rotation") for sd in v.get("side_data_list", []) or []
                                                       if "rotation" in sd), 0)
    w, h = v.get("width", 0), v.get("height", 0)
    if abs(int(float(rot or 0))) % 180 == 90:
        w, h = h, w
    return dict(dur=round(float(j.get("format", {}).get("duration", 0) or 0), 2), w=w, h=h,
                audio=any(s.get("codec_type") == "audio" for s in j.get("streams", [])))


def good_starts(path, dur, n=3, tail=2.5):
    """n start times: just after scene cuts (downscaled ffmpeg pass), filled with 10/40/70 % of the clip.
    Each leaves >= tail seconds (half the clip for short ones); short clips get evenly spaced starts."""
    tail = min(tail, dur / 2)
    span = dur - tail
    if span < 0.3:
        return [0.0]
    if span < 3.0:
        return sorted({round(0.3 + (span - 0.3) * k / (n - 1), 1) for k in range(n)})
    cuts = []
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-t", "120", "-i", path, "-an", "-vf",  # first 2 min: ~45 s for 4K
           "fps=4,scale=160:-2,select='gt(scene,0.25)',showinfo", "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        cuts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr)]
    except subprocess.TimeoutExpired:
        pass
    gap = max(1.5, dur / (n * 2))
    picks = []
    for t in [c + 0.3 for c in cuts] + [dur * f for f in (0.1, 0.4, 0.7)]:
        t = round(min(max(t, 0.3), span), 1)
        if len(picks) < n and all(abs(t - p) >= gap for p in picks):
            picks.append(t)
    for k in range(2 * n + 1):  # still short of n: evenly spaced, with a smaller gap
        t = round(0.3 + (span - 0.3) * k / (2 * n), 1)
        if len(picks) < n and all(abs(t - p) >= min(gap, span / (n + 1)) for p in picks):
            picks.append(t)
    return sorted(picks)


def frame(path, t, w=200, h=356):
    """One frame at t, letterboxed into a w x h cell (PIL image) or None."""
    from PIL import Image
    tmp = os.path.join(os.path.dirname(path), f".f_{os.getpid()}.jpg")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease", "-y", tmp], capture_output=True)
    if r.returncode or not os.path.exists(tmp):
        return None
    im = Image.open(tmp).convert("RGB")
    os.remove(tmp)
    c = Image.new("RGB", (w, h), (30, 30, 30))
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def font(size):
    from PIL import ImageFont
    try:
        f = ImageFont.truetype(os.path.join(HERE, "assets", "fonts", "Montserrat.ttf"), size)
        f.set_variation_by_name("SemiBold")
        return f
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def contact_sheet(path, c, out_jpg):
    """12 frames (evenly spaced + the proposed starts in red) with times; returns {start: frame} for the overview."""
    from PIL import Image, ImageDraw
    dur = c["dur"]
    times = sorted({round(dur * (0.03 + 0.94 * k / 8), 1) for k in range(9)} | set(c["good"]))
    keep = []
    for t in times:
        if t in c["good"] or all(abs(t - k) > 0.4 for k in keep):
            keep.append(t)
    keep = sorted(keep)[:12]
    W, H, top = 200, 356, 44
    sheet = Image.new("RGB", (W * 6, top + (H + 26) * ((len(keep) + 5) // 6)), "white")
    d = ImageDraw.Draw(sheet)
    d.text((8, 10), f"{c['name']}  {dur:.1f}s  {c['w']}x{c['h']}  starts {c['good']}", font=font(20), fill="black")
    good = {}
    for i, t in enumerate(keep):
        im = frame(path, t)
        x, y = (i % 6) * W, top + (i // 6) * (H + 26)
        if im:
            sheet.paste(im, (x, y))
        g = t in c["good"]
        if g:
            good[t] = im
            d.rectangle([x, y, x + W - 1, y + H - 1], outline=(200, 20, 30), width=5)
        d.text((x + 6, y + H + 3), f"{'START ' if g else ''}{t:.1f}s", font=font(17), fill=(200, 20, 30) if g else "black")
    sheet.save(out_jpg, quality=85)
    return good


def overview(photos, clips, site_imgs, good_frames, out_jpg, title):
    """One image to look at: client photos (P#, clean, faces), clip starts (C#), site packshots (S#)."""
    from PIL import Image, ImageDraw
    rows, cell = [], (220, 300)

    def tile(label, im, red=False):
        c = Image.new("RGB", (cell[0], cell[1] + 28), "white")
        if im is not None:
            im = im.copy()
            im.thumbnail(cell)
            c.paste(im, ((cell[0] - im.width) // 2, (cell[1] - im.height) // 2))
        ImageDraw.Draw(c).text((4, cell[1] + 4), label, font=font(15), fill=(200, 20, 30) if red else "black")
        return c
    pt = [tile(f"P{i} clean {p['clean']:.2f} faces {p['faces']}", Image.open(os.path.join(ROOT, p["path"])),
               bool(p["faces"])) for i, p in enumerate(photos)]
    ct = [tile(f"C{i} @{t:.1f}s {c['name'][:14]}", good_frames.get((i, t))) for i, c in enumerate(clips) for t in c["good"]]
    st = [tile(f"S{i} clean {sc:.2f} faces {fc}", Image.open(f), bool(fc)) for i, (f, sc, fc) in enumerate(site_imgs)]
    for name, ts in (("CLIENT PHOTOS (red = faces: never in statics)", pt), ("CLIP START TIMES", ct),
                     ("SITE IMAGES (red = faces)", st)):
        for k in range(0, len(ts), 8):
            rows.append((name if k == 0 else "", ts[k:k + 8]))
    if not rows:
        return None
    W = cell[0] * 8
    hh = [(30 if n else 0) + cell[1] + 28 for n, _ in rows]
    img = Image.new("RGB", (W, 50 + sum(hh)), (246, 241, 234))
    d = ImageDraw.Draw(img)
    d.text((10, 12), title, font=font(24), fill="black")
    y = 50
    for (n, ts), h in zip(rows, hh):
        if n:
            d.text((10, y + 4), n, font=font(19), fill=(90, 50, 30))
        for k, t in enumerate(ts):
            img.paste(t, (k * cell[0], y + (30 if n else 0)))
        y += h
    img.save(out_jpg, quality=85)
    return out_jpg


# ---------------------------------------------------------------- drafts
def money(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def sentence_around(text, m):
    a = max(text.rfind(".", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
    e = [i for i in (text.find(".", m.end()), text.find("\n", m.end())) if i >= 0]
    return re.sub(r"\s+", " ", text[a:(min(e) + 1 if e else len(text))]).strip()[:160]


def draft_offer(facts, notes, short):
    price, was = money(facts.get("price")), money(facts.get("compare_at"))
    pct = int(math.floor(round(100 * (1 - price / was), 1))) if price and was and was >= price * 1.1 else 0
    sources = [("site title", facts.get("title", "")), ("site variants", " | ".join(facts.get("variant_titles", []))),
               ("site description", facts.get("description", "")), ("notes", notes)]
    hits = [(m.group(0), src, sentence_around(txt, m)) for src, txt in sources for m in GIFT.finditer(txt or "")]
    gift = max(hits, key=lambda h: len(h[0]))[0].lower() if hits else None
    gift = re.sub(r"\s+", " ", gift) if gift else None
    a_gift = f"a {gift}" if gift else ""
    if pct and gift:
        close = f"It's {say(pct)} percent off right now, with {a_gift}. Tap the link below."
        sub = f"{pct}% off + {a_gift}."
    elif pct:
        close, sub = f"It's {say(pct)} percent off right now. Tap the link below.", f"Now {pct}% off."
    elif gift:
        close, sub = f"It comes with {a_gift}. Tap the link below.", f"Comes with {a_gift}."
    else:
        close, sub = "Tap the link below to see it.", f"Meet the {short}."
    evidence = [f"{src}: \"{q}\"" for g, src, q in hits[:4]]
    if pct:
        evidence.insert(0, f"site price {facts.get('price')} vs compare-at {facts.get('compare_at')} = {pct}% off")
    why = ("not used: the % comes from the site prices" if was else
           "no site prices: badge left empty, set it from this only if it is the client's current offer")
    evidence += [f"notes say ({why}): \"{sentence_around(notes, m)}\""
                 for m in re.finditer(r"\d{1,2}\s*%\s*off", notes or "", re.I)][:2]
    return dict(badge={"top": "NOW", "big": f"{pct}%", "bottom": "OFF"} if pct else None, gift=gift,
                offer_title=f"{pct}% OFF" if pct else "", offer_sub=f"+ {gift.upper()}" if gift else "",
                statics_sub=sub, close=close, evidence=evidence)


def notes_colours(notes):
    m = re.search(r"^\W*colou?rs?\s*[:\-]\s*(.+)$", notes or "", re.I | re.M)
    return [c.strip(" .").title() for c in re.split(r",|/|\band\b|\bor\b", m.group(1)) if c.strip(" .")] if m else []


def spoken(s):
    s = re.sub(r"\s+", " ", s.replace(" & ", " and ")).strip(" -*•·:;")
    s = s[:1].upper() + s[1:]
    return s if s[-1:] in ".!?" else s + "."


def tag_for(s, highlights):
    for pat, tag in TAGS:
        if re.search(pat, s, re.I):
            return tag
    for h in highlights:
        if h.lower() in s.lower() and 2 <= len(h.split()) <= 3:
            return h.upper()
    w = [x for x in re.findall(r"[A-Za-z][A-Za-z\-']+", s) if x.lower() not in GENERIC | {"it", "its", "your", "you", "is"}]
    return " ".join(w[:2]).upper()


def candidates(facts, notes):
    out = []
    lines = [ln.strip() for ln in (notes or "").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    marked = [ln for ln in lines if re.match(r"(?:[-*\u2022\u00b7]|\d+[.)])\s", ln)]
    for ln in marked or lines:  # bullet lines when the notes have any (skips titles / headers)
        ln = re.sub(r"^(?:[-*\u2022\u00b7]|\d+[.)])\s+", "", ln)
        if 3 <= len(ln.split()) <= 25 and not ln.endswith(":"):
            out.append((ln, "notes"))
    out += [(x, "site") for x in facts.get("bullets", [])]  # client notes first: written for this product
    seen, res = set(), []
    for s, src in out:
        if SALESY.search(s) or len(s.split()) > 30:
            continue
        line = spoken(s)
        tag = tag_for(line, facts.get("highlights", []))
        if tag in seen:
            continue
        seen.add(tag)
        hits = sum(bool(re.search(p, line, re.I)) for p, _ in TAGS[:-1])
        res.append(dict(line=line, tag=tag, source=src, score=hits - (2 if GIFT.search(line) else 0)))
    res.sort(key=lambda c: -c["score"])
    return res


def topics(text):
    w = set(re.findall(r"[a-z]+", text.lower()))
    return {i for i, g in enumerate(CLIP_TOPICS) if w & g}


def draft_picks(feats, clips):
    """features / hook_clips / broll picks: the product's own clips first, else photos of the plan's pool."""
    usable = [i for i, c in enumerate(clips) if c["good"]]
    if not usable:
        for j, f in enumerate(feats):
            f["picks"] = [["photo", 2 * j], ["photo", 2 * j + 1]]
        return [["photo", 0], ["photo", 1]], [["photo", k] for k in range(2, 7)]
    use = {i: 0 for i in usable}

    def take(i):
        c = clips[i]
        t = c["good"][use[i] % len(c["good"])]
        use[i] += 1
        return ["clip", i, t]
    for f in feats:
        ft = topics(f["line"] + " " + f["tag"])
        ranked = sorted(usable, key=lambda i: (-len(ft & topics(clips[i]["name"])), use[i], i))
        f["picks"] = [take(ranked[0])] + ([take(ranked[1])] if len(ranked) > 1 else [])
    hooky = sorted(usable, key=lambda i: (not HOOKY.search(clips[i]["name"]), i))
    hook = [["clip", i, clips[i]["good"][0]] for i in hooky[:3]]
    broll = [["clip", i, clips[i]["good"][-1]] for i in usable][:5]
    if len(broll) < 3:
        broll += [["photo", k] for k in range(3 - len(broll))]
    return hook, broll


# ---------------------------------------------------------------- commands
def cmd_list(a):
    from drive_upload import access_token
    token = access_token()
    have = {}
    for f in glob.glob(os.path.join(a.products_dir, "*.json")):
        try:
            d = json.load(open(f))
        except ValueError:
            continue
        have[(d.get("source") or {}).get("drive_folder") or f] = (f, d.get("status"))
        have.setdefault(os.path.basename(f)[:-5], (f, d.get("status")))
    rows = []
    for fo in product_folders(token):
        files = drive_files(token, fo["id"])
        ks = [kind(f["name"], f["mimeType"]) for f in files]
        slug = slugify(names_for(fo["name"])[0])
        f, st = have.get(fo["id"]) or have.get(slug) or (None, None)
        rows.append(dict(name=fo["name"], id=fo["id"], created=fo["createdTime"][:10], photos=ks.count("photo"),
                         clips=ks.count("clip"), notes=ks.count("note"), other=ks.count(None), slug=slug,
                         product_file=rel(f), status=st or "new"))
    print(json.dumps(rows, indent=1, ensure_ascii=False))
    if not rows:
        print("New Products has no product subfolders yet. The client adds one folder per product "
              "(photos, clips, a notes doc with the libracases.com link).", file=sys.stderr)


def cmd_intake(a):
    warnings = []
    warn = lambda m: (warnings.append(m), print("warning:", m, file=sys.stderr))  # noqa: E731
    token, files, folder, folder_name = None, [], None, ""
    if a.local:
        files, folder_name = local_files(a.local), os.path.basename(os.path.abspath(a.local).rstrip("/"))
        if not files:
            sys.exit(f"no files in {a.local}")
    elif a.folder or a.latest:
        from drive_upload import access_token
        token = access_token()
        fs = product_folders(token)
        if a.latest:
            folder = fs[0] if fs else None
        else:
            q = a.folder.lower().strip()
            folder = next((f for f in fs if f["name"].lower().strip() == q), None)
            sub = [f for f in fs if q in f["name"].lower()]
            folder = folder or (sub[0] if len(sub) == 1 else None)
        if not folder:
            sys.exit("no matching product folder in Drive New Products. Folders: " + (", ".join(f["name"] for f in fs) or "none"))
        folder_name = folder["name"]
        files = drive_files(token, folder["id"])
    elif not a.site:
        sys.exit("give a New Products folder name, --latest, --site <url|handle> or --local <dir>")

    # site handle: --site, else a libracases.com link in the notes, else the folder name (only on a clear match)
    notes_files = [f for f in files if kind(f["name"], f.get("mimeType", "")) == "note"]
    handle = site_title = None
    how = ""
    if a.site:
        try:
            handle, how = site_assets.find_handle(a.site), "--site"
        except site_assets.NoMatch as e:
            sys.exit(str(e))
    display = a.name or folder_name
    if not display and handle:
        site_title = json.loads(site_assets.get(f"{site_assets.SITE}/products/{handle}.json"))["product"]["title"]
        display = clean_title(site_title)
    key, name, short, end = names_for(display)
    slug = slugify(key)
    out_file = os.path.join(a.products_dir, slug + ".json")
    if os.path.exists(out_file):
        if json.load(open(out_file)).get("status") == "ready" and not a.force:
            sys.exit(f"{rel(out_file)} is already 'ready'. Use --force to redo the intake (it overwrites Claude's edits).")
        warn(f"replacing the earlier {rel(out_file)}")
    cache = os.path.join(a.cache, slug)
    for sub in ("photos", "clips", "notes", "raw", "sheets"):
        os.makedirs(os.path.join(cache, sub), exist_ok=True)

    notes = "\n\n".join(f"## {f['name']}\n{note_text(f, cache, token)}" for f in notes_files)
    if not handle:
        m = SITE_URL.search(notes)
        if m:
            handle, how = site_assets.handle_from_url(m.group(0)), "link in notes"
        else:
            try:
                handle, how = site_assets.find_handle(display), "matched by name: CHECK it is the same product"
            except site_assets.NoMatch as e:
                warn(f"no libracases.com page found (no link in notes, name not on the site): {str(e).splitlines()[0]}")
    facts = {}
    if handle:
        try:
            facts = site_assets.fetch(handle, os.path.join(cache, "site"), key=slug.replace("-", "_")[:24])
        except (site_assets.NoMatch, OSError) as e:
            warn(f"site fetch failed for {handle}: {e}")
            handle = None

    # photos
    photos, taken = [], set()
    for f in [f for f in files if kind(f["name"], f.get("mimeType", "")) == "photo"][:a.max_photos]:
        raw = fetch_file(f, unique(os.path.join(cache, "raw", f["name"]), taken), token)
        dst = to_jpg(raw, unique(os.path.join(cache, "photos", os.path.splitext(f["name"])[0] + ".jpg"), taken), warn)
        if dst:
            from PIL import Image
            w, h = Image.open(dst).size
            photos.append(dict(id=f["id"], name=os.path.basename(dst), clean=site_assets.clean_score(dst),
                               faces=count_faces(dst), w=w, h=h, path=rel(dst)))
    photos.sort(key=lambda p: (bool(p["faces"]), -p["clean"]))
    if any(p["faces"] is None for p in photos):
        warn("face check unavailable (opencv or its face model missing): look at every photo before using it in statics")

    # clips
    clips, good_frames = [], {}  # (same-named files in two subfolders get _2 names via unique)
    vids = [f for f in files if kind(f["name"], f.get("mimeType", "")) == "clip"]
    if len(vids) > a.max_clips:
        warn(f"{len(vids)} clips, only the first {a.max_clips} taken (--max-clips)")
    for f in vids[:a.max_clips]:
        p = fetch_file(f, unique(os.path.join(cache, "clips", f["name"]), taken), token)
        pr = probe(p)
        if not pr["dur"]:
            warn(f"skipped {f['name']}: ffprobe found no video")
            continue
        c = dict(id=f["id"], name=f["name"], dur=pr["dur"], w=pr["w"], h=pr["h"], good=good_starts(p, pr["dur"]),
                 mute=True, audio=pr["audio"], path=rel(p))
        sheet = os.path.join(cache, "sheets", slugify(os.path.splitext(f["name"])[0]) + ".jpg")
        for t, im in contact_sheet(p, c, sheet).items():
            good_frames[(len(clips), t)] = im
        c["sheet"] = rel(sheet)
        clips.append(c)
    if any(c["id"] is None for c in clips + photos):
        warn("local files have no Drive id: they work only on this machine. For later sessions put them in the "
             "product's Drive folder and rerun the intake from there")

    # drafts
    offer = draft_offer(facts, notes, short)
    feats = candidates(facts, notes)[:5]
    hook, broll = draft_picks(feats, clips)
    if len(feats) < 3:
        warn(f"only {len(feats)} feature lines found: write 3-5 from the facts / notes before setting status ready")
    sc = facts.get("scores", {})
    site_imgs = [(f, sc.get(f, 0), count_faces(f)) for f in facts.get("images", [])[:16]]
    title = f"{name}  |  {facts.get('url', 'no site page')}  |  {len(photos)} photos, {len(clips)} clips"
    ov = overview(photos, clips, site_imgs, good_frames, os.path.join(cache, "overview.jpg"), title)
    if not photos and not clips and not handle:
        warn("no photos, no clips and no site page: nothing to build ads from yet")

    extra = [folder_name if folder and slugify(folder_name) != slug else "", handle or ""]
    product = dict(
        key=key, aliases=aliases_for(key, extra), name=name, short=short, end=end, site=handle,
        photos=photos, clips=clips, offer=offer,
        hook_clips=hook, features=[[f["line"], f["tag"], f["picks"]] for f in feats], customer=[], broll=broll,
        reviews=[],
        facts=dict(price=facts.get("price"), compare_at=facts.get("compare_at"),
                   colours=(list(facts.get("colours", {})) or (facts.get("options") or {}).get("Color", [])
                            or notes_colours(notes)),
                   description=facts.get("description", ""), notes=notes.strip()[:4000],
                   title=facts.get("title") or site_title, url=facts.get("url")),
        source=dict(drive_folder=folder["id"] if folder else None, folder_name=folder_name or None,
                    site_url=facts.get("url"), site_match=how or None, local_dir=os.path.abspath(a.local) if a.local else None,
                    cache=rel(cache), overview=rel(ov), added=datetime.date.today().isoformat()),
        status="draft")
    os.makedirs(a.products_dir, exist_ok=True)
    open(out_file, "w").write(dumps(product) + "\n")

    pr_line = (f"${facts.get('price')}" + (f" (was ${facts['compare_at']})" if facts.get("compare_at") else "")) if facts else "-"
    print(f"product   {name}  (key \"{key}\", aliases {', '.join(product['aliases']) or '-'})")
    print(f"file      {rel(out_file)}  (status draft)")
    print(f"site      {facts.get('url', '-')}  [{how or 'none'}]  {pr_line}  "
          f"colours: {', '.join(product['facts']['colours']) or '-'}")
    print(f"offer     {offer['offer_title'] or 'no discount'}  {offer['offer_sub']}  |  close: \"{offer['close']}\"")
    for e in offer["evidence"]:
        print(f"          evidence: {e}")
    print(f"photos    {len(photos)} ({sum(p['clean'] >= 0.8 for p in photos)} clean packshots, "
          f"{sum(bool(p['faces']) for p in photos)} with faces = never in statics)")
    for i, c in enumerate(clips):
        print(f"clip C{i}   {c['name']}  {c['dur']:.1f}s  {c['w']}x{c['h']}  starts {c['good']}  sheet {c['sheet']}")
    print("features  (draft, from " + ("site + notes" if facts and notes else "site" if facts else "notes") + ")")
    for i, f in enumerate(feats):
        print(f"  {i + 1}. [{f['tag']}] \"{f['line']}\"  picks {f['picks']}")
    print(f"hook      {hook}\nbroll     {broll}")
    print(f"look at   {rel(ov) if ov else '-'}  (+ {rel(os.path.join(cache, 'sheets'))}/*.jpg)")
    for w in warnings:
        print(f"WARNING   {w}")
    print(f"NEXT: Claude checks/rewrites features (3-5, only true claims from facts/notes), checks the offer, "
          f"sets status ready, then runs make_batch.py plan --product \"{key}\"")


def validate(d):
    """(problems, warnings) for a product dict against the schema in pipeline/data/products/README.md."""
    P, W = [], []
    bank = json.load(open(os.path.join(HERE, "data", "clip_bank.json")))
    review_ns = {r["n"] for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}
    for k in ("key", "name", "short", "end"):
        if not isinstance(d.get(k), str) or not d.get(k).strip():
            P.append(f"'{k}' must be a non-empty string")
    if d.get("key") and d["key"] != d["key"].lower():
        P.append("'key' must be lowercase")
    if not isinstance(d.get("aliases", []), list):
        P.append("'aliases' must be a list")
    if d.get("site") is not None and not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", str(d.get("site"))):
        P.append(f"'site' must be a Shopify handle or null, not {d.get('site')!r}")
    photos, clips = d.get("photos", []), d.get("clips", [])
    for i, p in enumerate(photos):
        if not isinstance(p.get("clean"), (int, float)) or not isinstance(p.get("faces"), int):
            P.append(f"photo {i}: needs numeric 'clean' and integer 'faces'")
        if not p.get("id") and not (p.get("path") and os.path.exists(os.path.join(ROOT, p["path"]))):
            P.append(f"photo {i} ({p.get('name')}): no Drive id and no local file")
        elif not p.get("id"):
            W.append(f"photo {i} ({p.get('name')}): local only (no Drive id)")
    for i, c in enumerate(clips):
        if not isinstance(c.get("dur"), (int, float)) or c["dur"] <= 0:
            P.append(f"clip {i}: 'dur' must be > 0")
            continue
        if not c.get("good") or any(not 0 <= t < c["dur"] for t in c["good"]):
            P.append(f"clip {i} ({c.get('name')}): 'good' starts must be within 0..{c['dur']}")
        if not isinstance(c.get("mute", True), bool):
            P.append(f"clip {i}: 'mute' must be true/false")
        if not c.get("id") and not (c.get("path") and os.path.exists(os.path.join(ROOT, c["path"]))):
            P.append(f"clip {i} ({c.get('name')}): no Drive id and no local file")
        elif not c.get("id"):
            W.append(f"clip {i} ({c.get('name')}): local only (no Drive id)")
    pool = len(photos) + (1 if d.get("site") else 0)

    def pick_ok(p, where):
        if not isinstance(p, list) or not p:
            P.append(f"{where}: pick {p!r} must be a list")
        elif p[0] == "clip":
            if len(p) != 3 or not isinstance(p[1], int) or not 0 <= p[1] < len(clips):
                P.append(f"{where}: {p!r} points at no clip (have {len(clips)})")
            elif not isinstance(p[2], (int, float)) or not 0 <= p[2] < clips[p[1]]["dur"] - 0.5:
                P.append(f"{where}: {p!r} start is outside clip {p[1]} ({clips[p[1]]['dur']}s)")
        elif p[0] == "photo":
            if len(p) != 2 or not isinstance(p[1], int) or p[1] < 0:
                P.append(f"{where}: {p!r} must be [\"photo\", N]")
            elif not pool:
                P.append(f"{where}: {p!r} but there are no photos and no site page")
        elif len(p) == 3 and isinstance(bank.get(p[0]), dict) and p[1] in bank[p[0]] and p[0] not in ("_help", "voices",
                                                                                                         "winner_raws"):
            if not isinstance(p[2], (int, float)):
                P.append(f"{where}: {p!r} start must be a number")
        else:
            P.append(f"{where}: {p!r} is not a clip_bank section/key, a clip or a photo pick")
    feats = d.get("features", [])
    if not 3 <= len(feats) <= 5:
        P.append(f"needs 3-5 features (has {len(feats)})")
    for i, f in enumerate(feats):
        if not (isinstance(f, list) and len(f) == 3 and isinstance(f[0], str) and isinstance(f[1], str)
                and isinstance(f[2], list) and f[2]):
            P.append(f"feature {i + 1}: must be [\"spoken line\", \"TAG\", [pick, ...]]")
            continue
        if f[1] != f[1].upper() or not 1 <= len(f[1].split()) <= 4:
            P.append(f"feature {i + 1}: tag {f[1]!r} must be 2-3 UPPERCASE words")
        elif not 2 <= len(f[1].split()) <= 3:
            W.append(f"feature {i + 1}: tag {f[1]!r} is not 2-3 words")
        if len(f[0].split()) > 30 or f[0].strip()[-1:] not in ".!?":
            P.append(f"feature {i + 1}: line must be one short spoken sentence ending in . ! or ?")
        for p in f[2]:
            pick_ok(p, f"feature {i + 1}")
    for fld in ("hook_clips", "broll"):
        if not d.get(fld):
            P.append(f"'{fld}' needs at least one pick")
        for p in d.get(fld) or []:
            pick_ok(p, fld)
    for i, c in enumerate(d.get("customer", [])):
        if not (len(c) == 4 and isinstance(bank.get(c[0]), dict) and c[1] in bank[c[0]] and c[2] < c[3]):
            P.append(f"customer {i}: {c!r} must be [section, key, start, end] from clip_bank.json")
    bad = [n for n in d.get("reviews", []) if n not in review_ns]
    if bad:
        P.append(f"reviews {bad} do not exist in reviews.json")
    if d.get("reviews"):
        W.append(f"reviews {d['reviews']} set: only keep reviews that are about this product")
    o = d.get("offer")
    if not isinstance(o, dict):
        P.append("'offer' missing")
    else:
        for k in ("offer_title", "offer_sub", "statics_sub", "close"):
            if not isinstance(o.get(k), str):
                P.append(f"offer.{k} must be a string")
        if "link below" not in (o.get("close") or "").lower():
            P.append("offer.close must end with 'Tap the link below.'")
        b, f = o.get("badge"), d.get("facts") or {}
        if b is not None:
            if not (isinstance(b, dict) and all(isinstance(b.get(k), str) for k in ("top", "big", "bottom"))):
                P.append("offer.badge must be null or {top, big, bottom}")
            else:
                m = re.match(r"(\d+)%", b["big"])
                price, was = money(f.get("price")), money(f.get("compare_at"))
                real = 100 * (1 - price / was) if price and was else None
                said = re.findall(r"(\d{1,2})\s*%\s*off", f.get("notes") or "", re.I)  # client-stated offer
                if m and (real is None or abs(int(m.group(1)) - real) > 2) and m.group(1) not in said:
                    P.append(f"offer.badge {b['big']} is backed neither by the site prices ({f.get('price')} vs "
                             f"{f.get('compare_at')}) nor by the client's notes")
                if m and m.group(1) not in o.get("offer_title", ""):
                    W.append("offer_title does not repeat the badge %")
        elif re.search(r"percent off|% off", (o.get("close", "") + o.get("offer_title", "")), re.I):
            P.append("offer mentions a discount but badge is null")
        g = o.get("gift")
        src = " ".join(str(f.get(k) or "") for k in ("title", "description", "notes")).lower()
        if g and g.lower() not in src and not all(w in src for w in re.findall(r"[a-z]+", g.lower()) if len(w) > 3):
            P.append(f"offer.gift {g!r} is not found in the site text or notes: never invent gifts")
        if not g and re.search(r"\bfree\b", o.get("close", "") + o.get("offer_sub", ""), re.I):
            P.append("offer mentions something free but gift is null")
    if d.get("status") not in ("draft", "ready"):
        P.append("'status' must be draft or ready")
    elif d["status"] == "draft":
        W.append("status is draft: review features + offer, then set \"ready\"")
    if any(p.get("faces") for p in photos):
        W.append(f"{sum(bool(p.get('faces')) for p in photos)} photo(s) show faces: never use them in statics")
    return P, W


def cmd_check(a):
    try:
        path, d = load_product(a.ref, a.products_dir)
    except (OSError, ValueError) as e:
        sys.exit(f"cannot read product file for {a.ref!r}: {e}")
    P, W = validate(d)
    if slugify(d.get("key", "")) + ".json" != os.path.basename(path):
        W.append(f"file name should be {slugify(d.get('key', ''))}.json")
    print(json.dumps(dict(file=path, key=d.get("key"), status=d.get("status"), ok=not P, problems=P, warnings=W),
                     indent=1, ensure_ascii=False))
    sys.exit(1 if P else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    i = sub.add_parser("intake")
    i.add_argument("folder", nargs="?", help="New Products subfolder name")
    i.add_argument("--latest", action="store_true", help="the newest New Products subfolder")
    i.add_argument("--site", help="libracases.com product URL or handle (overrides a link in the notes)")
    i.add_argument("--local", help="a local folder instead of Drive (photos, clips, notes.txt)")
    i.add_argument("--name", help="display name, e.g. 'The Silhouette Bag' (default: folder name or site title)")
    i.add_argument("--max-photos", type=int, default=20)
    i.add_argument("--max-clips", type=int, default=12)
    i.add_argument("--cache", default=CACHE_DIR)
    i.add_argument("--force", action="store_true", help="redo a product file that is already 'ready'")
    c = sub.add_parser("check")
    c.add_argument("ref", help="slug, key or path of a product file")
    for p in (ls, i, c):
        p.add_argument("--products-dir", default=PRODUCTS_DIR)
    a = ap.parse_args()
    {"list": cmd_list, "intake": cmd_intake, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()

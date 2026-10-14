#!/usr/bin/env python3
"""New-product intake: a product folder in Drive "Ad Creative Pipeline / New Products" -> a product file
pipeline/data/products/<slug>.json that make_batch.py builds ads from. Schema: pipeline/data/products/README.md.

The folder is the source: its photos, clips and every note-like file (.txt .md .url .csv, Google Docs / Sheets, .docx,
.pdf, .rtf) plus the folder's own Drive description. libracases.com is read only with --site <url|handle> or --use-site,
and then only for what the folder lacks (prices, colours, a gift the notes don't mention, more feature lines).

  list    python3 pipeline/new_product.py list
          New Products subfolders, newest first: photo / clip / note counts, the product file, status
          (new | draft | ready | tested <date>), changed (files added or edited since the intake), tests.
  intake  python3 pipeline/new_product.py intake "Silhouette Bag"        (a subfolder: exact name or a unique part of it)
          python3 pipeline/new_product.py intake --latest                 (the newest subfolder)
          python3 pipeline/new_product.py intake "Silhouette Bag" --use-site   (libracases.com fills what the folder lacks)
          python3 pipeline/new_product.py intake --site https://libracases.com/products/the-silhouette-bag [--name ...]
          python3 pipeline/new_product.py intake --local ~/bag_folder --name "Silhouette Bag"
          Downloads photos (-> jpg), clips and notes into pipeline/cache/new_products/<slug>/, scores the photos (clean,
          faces) and sorts them into packshot / worn / detail / other ("statics": false on a worn photo that may show
          part of a head: videos only), proposes clip start times (about one per 4.5 s, after scene changes), reads
          price, was-price, an "NN% off", a gift, colours (also inside the price line) and the feature bullets (or, with
          no bullet marks, the one-sentence lines) from the notes, drafts 0-7 spoken
          feature lines + tags and picks the footage that shows each (zip -> the zipper close-up, straps -> a worn
          photo, room -> the open bag, shape -> a packshot), writes overview.jpg + contact sheets. No check problems ->
          "status": "ready", "auto": true (made automatically, not hand-reviewed); else "draft" with the problems
          ("auto": false). Either way source.auto_sig marks it untouched: ensure() re-makes it when the folder changes.
          --draft always keeps it draft; --force redoes a file that is already ready.
  check   python3 pipeline/new_product.py check silhouette-bag            (slug or path; exit 1 on problems)

Python (make_batch.py): intake(...), ensure(ref) (a folder name, "next" or "latest": reuses the product file while the
folder is unchanged, else runs the intake), record_test(ref, info) (ads made from it), pending() (folders with no ads
yet or changed since). They raise ValueError with a clear message, never exit.

Never invents an offer: a % comes from prices (the notes', else the site's: compare-at at least 10% above the price,
rounded down to a multiple of 5) or from an "NN% off" the notes state (both and they disagree: the lower); a gift only
from a quoted "free pouch / wallet / purse / gift" phrase that is not negated ("No free gift" is no gift).
"""
import argparse
import csv
import datetime
import glob
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import site_assets  # noqa: E402

PRODUCTS_DIR = os.path.join(HERE, "data", "products")
CACHE_DIR = os.environ.get("LC_NP_CACHE") or os.path.join(HERE, "cache", "new_products")   # (env: tests' scratch cache)
FOLDER = "application/vnd.google-apps.folder"
GDOC = "application/vnd.google-apps.document"
GSHEET = "application/vnd.google-apps.spreadsheet"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
CLIP_EXT = {".mp4", ".mov", ".m4v"}
NOTE_EXT = {".txt", ".md", ".url", ".csv", ".docx", ".pdf", ".rtf"}
NOTE_MIME = {GDOC, GSHEET, DOCX, "application/pdf", "application/rtf", "text/rtf", "text/plain", "text/markdown", "text/csv"}
KINDS = ("packshot", "worn", "detail", "other")
GENERIC = site_assets.GENERIC | {"tote", "set", "crossbody", "shoulder", "piece", "3-piece", "mini", "small", "large"}
GIFT = re.compile(r"\bfree\s+(?:(?:matching|small|mini|bonus|little|leather)\s+){0,2}"
                  r"(?:pouch(?:\s+wallet)?|wallet|purse|clutch|gift|keychain|charm|card\s*holder)\b", re.I)
SITE_URL = re.compile(r"(?:https?://)?(?:www\.)?libracases\.com/\S*?products/[A-Za-z0-9\-]+", re.I)
SALESY = re.compile(r"%|\bsale\b|ends tonight|\bfree (?:delivery|shipping)\b|\bdiscount|\bshipping\b|\bprice\b|"
                    r"\border\b|http|libracases\.com|limited time|today only", re.I)
TAGS = [  # (pattern in the sentence, on-screen tag or tag(line)): a line's first hit is its tag, a later one its
    # fallback when another line took the first (so specific before generic); a tag never says more than its line
    (r"anti-?theft", "ANTI-THEFT POCKET"), (r"\brfid\b", "RFID LINING"), (r"lockable|\block", "LOCKABLE ZIPPERS"),
    (r"cut-?resistant", "CUT-RESISTANT STRAP"), (r"convertible|backpack, tote|switch\b", "CONVERTIBLE STRAPS"),
    (r"laptop", "FITS A LAPTOP"), (r"water-?(?:resistant|proof)", "WATER-RESISTANT LEATHER"),
    (r"scratch", "SCRATCH-PROOF LEATHER"), (r"compartment", "SMART COMPARTMENTS"), (r"hidden pocket", "HIDDEN POCKETS"),
    (r"pocket", "HANDY POCKETS"), (r"zip", "ZIP CLOSURE"), (r"adjustable|removable", "ADJUSTABLE STRAP"),
    (r"strap", "EASY STRAPS"), (r"crossbody|ways to wear|in hand", "WEAR IT YOUR WAY"),
    (r"spacious|room for|fits? (?:your|all|everything)|holds", "ROOM FOR EVERYTHING"),
    (r"fits? (?:a |an |the |your )?(?:phone|cards?|keys?|wallet|lipstick|essentials)", "ROOM FOR ESSENTIALS"),
    (r"lightweight", "LIGHTWEIGHT"),
    (r"\b(?:soft|smooth)\w*,?\s+(?:\w+\s+)?leather", lambda s: ("SMOOTH" if re.search(r"\bsmooth", s, re.I) else "SOFT")
     + " LEATHER"),
    (r"\bsmooth|\bsoft|\bfeel\w*\b.*\blux|\blux\w*\b.*\bfeel",            # how it feels, before the shape rule
     lambda s: ("LUXE" if re.search(r"\blux", s, re.I) else "SMOOTH" if re.search(r"\bsmooth", s, re.I) else "SOFT")
     + " FEEL"),
    (r"silhouette|elongated|\bshape", "SLEEK SHAPE"), (r"structured", "SLEEK SHAPE"),
    (r"nights? out|day to night|office days?", "DAY TO NIGHT"),
    (r"leather", lambda s: next((w.upper() + " LEATHER" for w in re.findall(r"(\w+)\s+leather", s, re.I)
                                 if w.lower() in ("soft", "smooth", "vegan", "genuine", "faux", "pu", "glossy")),
                                "LEATHER FINISH")),
    (r"stitch|finish", "CLEAN FINISH"), (r"free .*pouch|pouch", "FREE MATCHING POUCH"),
]
SOFT_TAGS = {"DAY TO NIGHT", "FREE MATCHING POUCH"}   # a mood or the gift, not a feature: no ranking bonus
# feature words -> the photo kind that shows them (a clip moment fits any); most hits wins, ties in this order
ROUTES = [
    ("detail", r"stitch\w*|finish\w*|leather|gloss\w*|materials?|textur\w*|zip\w*|hardware|closures?|clasps?|buckles?|"
               r"smooth\w*|grain|feel\w*|soft\w*"),
    ("inside", r"room|roomy|fits?|inside|interior|pockets?|compartments?|essentials|phones?|wallets?|keys|holds?|"
               r"spacious|organi[sz]\w*"),
    ("worn", r"straps?|shoulders?|carry\w*|arms?|under-?arm|wear|wearing|worn|outfits?|styl\w*|handles?|crossbody|hands?|"
             r"nights? out"),
    ("packshot", r"colou?rs?|shapes?|silhouette|structur\w*|designs?|sleek|elongated|looks?"),
]
ROUTES = [(k, re.compile(r"(?<![\w-])(?:" + p + r")(?![\w-])", re.I)) for k, p in ROUTES]
PREFER = {"detail": ("detail", "other", "packshot"), "inside": ("other", "detail"), "worn": ("worn", "other"),
          "packshot": ("packshot",), None: ("worn", "other", "detail", "packshot")}
HARDWARE = re.compile(r"zip|hardware|closure|clasp|buckle|metal|lock", re.I)     # busiest close-up (teeth, metal)
SURFACE = re.compile(r"stitch|finish|leather|gloss|textur|smooth|grain|feel|soft", re.I)   # calmest close-up (a surface)
ODD = re.compile(r"\bcoven\w*|\bwitch\w*|\boccult\w*|\bcursed?\b|\bdevil\w*|\bsexy\b|\bsins?\b", re.I)
META = re.compile(r"^\W*(?:available\s+|free\s+)?(?:colou?rs?|prices?|was|now|compare|site|link|url|website|files?|"
                  r"photos?|clips?|videos?|offer|gift|discount|sale|name|product|title|sku|handle|notes?|sizes?|"
                  r"dimensions?|weight|shipping)\b[^:\n]{0,24}:", re.I)       # 'Colours: ...', 'Price: ...' lines
PNOUN = r"bags?|totes?|backpacks?|purses?|handbags?|clutch(?:es)?|wallets?|satchels?|crossbodys?|sets?|shoppers?"
OTHER_NAMES = ("hobo", "slouchy", "vintage bag", "3-piece set", "three-piece set")   # built-in bags (make_batch.PRODUCTS)
CLIP_TOPICS = [  # words that link a feature line to a clip file name
    {"strap", "straps", "convertible", "wear", "wearing", "crossbody", "backpack", "tote", "shoulder", "handle"},
    {"inside", "fits", "room", "spacious", "laptop", "essentials", "putting", "stuff", "pack", "packing", "holds", "open"},
    {"water", "resistant", "snow", "rain", "weather", "proof", "cold", "snowing"},
    {"walk", "walking", "carry", "carrying", "anywhere", "day", "outdoor", "grocery", "car"},
    {"leather", "details", "detail", "close", "macro", "scratch", "stitching", "finish"},
    {"pocket", "pockets", "zip", "zipper", "keys", "wallet", "phone", "back"},
    {"outfit", "style", "styling", "sleek", "look", "looks", "blazer", "dress"},
]
HAAR_URL = "https://raw.githubusercontent.com/opencv/opencv/4.10.0/data/haarcascades/"
YUNET = "face_detection_yunet_2023mar.onnx"   # committed in pipeline/assets/models (MIT, opencv_zoo)
YUNET_URL = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/" + YUNET
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


COLOUR_WORDS = {"black", "white", "brown", "beige", "red", "wine", "burgundy", "blue", "navy", "green", "olive", "grey",
                "gray", "pink", "rose", "purple", "apricot", "coffee", "cream", "ivory", "tan", "camel", "caramel", "cognac",
                "khaki", "taupe", "nude", "silver", "gold", "orange", "yellow", "chocolate", "espresso", "mocha", "ginger",
                "light", "dark"}
ALIAS_SKIP = {"notes", "note", "pdf", "doc", "docs", "test", "product", "products", "folder", "photos", "clips", "files",
              "draft", "copy", "final", "only", "colour", "color", "colours", "colors", "edition", "version", "one",
              "backpack", "backpacks", "purse", "purses", "handbags", "clutch", "satchel", "shopper", "totes", "sets"}


def builtin_names():
    """Keys, names and keywords of make_batch's built-in bags (lowercase), or the bare OTHER_NAMES without it."""
    try:
        from make_batch import PRODUCT_KEYS, PRODUCTS
        return (set(PRODUCTS) | set(PRODUCT_KEYS) | {str(p.get(k) or "").lower() for p in PRODUCTS.values()
                                                     for k in ("name", "short", "site")}) - {""}
    except Exception:  # noqa: BLE001
        return set(OTHER_NAMES) | {"hobo bag", "hobo 2.0", "vintage", "slouchy", "3-piece set"}


def aliases_for(key, extra, products_dir=PRODUCTS_DIR):
    """Distinctive words of the key + folder name + site handle: never a colour ("black"), a generic or notes word
    ("bag", "notes"), a punctuation token, a built-in product's name ("hobo", "vintage") or an alias / name another
    product file already has (two "Silhouette ..." folders: the first keeps "silhouette")."""
    reserved = builtin_names()
    for k, d in load_all(products_dir).items():
        if k != key:
            reserved |= {str(x).lower().strip() for x in [k, d.get("name"), d.get("short")] + list(d.get("aliases") or [])
                         if x}
    skip = GENERIC | COLOUR_WORDS | ALIAS_SKIP

    def words(s):
        return [w for w in re.findall(r"[a-z0-9][a-z0-9.'\-]*[a-z0-9]|[a-z0-9]", s.lower()) if w not in skip]
    distinct = " ".join(words(key))
    last = distinct.split()[-1] if distinct else ""
    out = []
    for a in [distinct, last if len(last) >= 4 and not last[0].isdigit() else ""] + \
            [" ".join(words(x.replace("-", " "))) for x in extra if x]:
        if a and a != key and a not in out and a not in reserved and re.search(r"[a-z]{3}", a):
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
    if mime in NOTE_MIME or ext in NOTE_EXT:
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
            mt = datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).isoformat()[:23] + "Z"
            out.append(dict(id=None, name=os.path.basename(p), mimeType="", size=os.path.getsize(p), local=p,
                            modifiedTime=mt))
    return out


def product_folders(token):
    from drive_upload import list_children
    from index_library import load_config
    return [f for f in list_children(token, load_config()["drive"]["new_products_folder"]) if f["mimeType"] == FOLDER]


def _token():
    """Drive access token; ValueError (never an exit) without the Drive login."""
    from drive_upload import access_token
    try:
        return access_token()
    except SystemExit as e:
        raise ValueError("no Drive login (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN missing or "
                         "refused): python3 pipeline/drive_upload.py check") from e


def _folders(token):
    try:
        fs = product_folders(token)
    except (urllib.error.URLError, OSError) as e:
        raise ValueError(f"cannot list Drive New Products: {e}") from e
    if not fs:
        raise ValueError("Drive New Products has no product folders yet: the client adds one folder per product "
                         "(photos, clips, a notes doc)")
    return fs


def norm_name(s):
    """A folder / product name for matching: no leading 'the', case, punctuation or plural s ('The Silhouette Bags',
    'silhouette-bag' -> 'silhouette-bag')."""
    s = re.sub(r"^\s*the\s+", "", s or "", flags=re.I)
    return "-".join(re.sub(r"(?<=[a-z]{3})s$", "", w) for w in slugify(s).split("-") if w)


def find_folder(fs, ref):
    """The New Products folder named ref: the exact name (any case), else the normalised name (norm_name: 'The
    Silhouette Bag', 'silhouette bags', 'Silhouette-Bag'), else the one folder whose name contains it."""
    q, qn = (ref or "").lower().strip(), norm_name(ref)
    for hits in ([f for f in fs if f["name"].lower().strip() == q], [f for f in fs if qn and norm_name(f["name"]) == qn]):
        if len(hits) == 1:
            return hits[0]
    sub = [f for f in fs if q and q in f["name"].lower()] or [f for f in fs if qn and qn in norm_name(f["name"])]
    if len(sub) == 1:
        return sub[0]
    raise ValueError(f"{'more than one' if sub else 'no'} New Products folder matches {ref!r}. Folders: "
                     + (", ".join(f["name"] for f in fs) or "none"))


def folder_description(token, folder_id):
    """The Drive folder's own description ('' when it has none)."""
    from drive_upload import API, api
    try:
        with api("GET", f"{API}/drive/v3/files/{folder_id}?fields=description&supportsAllDrives=true", token) as r:
            return (json.load(r).get("description") or "").strip()
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def file_rows(files):
    """[{id, name, modifiedTime}] of a folder's files: what ensure() compares to see whether the folder changed."""
    return sorted((dict(id=f.get("id"), name=f["name"], modifiedTime=f.get("modifiedTime")) for f in files),
                  key=lambda r: (r["name"], r["id"] or ""))


def folder_changes(d, files):
    """Names of the folder's files added or edited since the product file's intake, plus removed ones ('- name');
    None when the file has no source.files (made before they were stored)."""
    old = (d.get("source") or {}).get("files")
    if old is None:
        return None
    was = {(r.get("id") or r.get("name")): r.get("modifiedTime") for r in old}
    now = {(f.get("id") or f["name"]): f for f in files}
    out = [f["name"] for k, f in now.items() if k not in was or was[k] != f.get("modifiedTime")]
    return out + ["- " + r["name"] for r in old if (r.get("id") or r.get("name")) not in now]


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


def docx_text(path):
    """Text of a .docx (word/document.xml, no extra dependency): one line per paragraph, list items start with '- '."""
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S):
        t = re.sub(r"<w:tab/>", "\t", re.sub(r"<w:br/>|<w:cr/>", "\n", p))
        out.append(("- " if "<w:numPr>" in p else "") + html.unescape(re.sub(r"<[^>]+>", "", t)))
    return "\n".join(out)


RTF_SKIP = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "header", "footer", "listtable", "listoverridetable",
            "generator", "themedata", "datastore", "latentstyles", "rsidtbl", "xmlnstbl"}


def rtf_text(s):
    """Plain text of an RTF document: control words dropped, \\par -> new line, \\'hh and \\uN decoded."""
    out, stack, skip, drop = [], [], False, 0
    for m in re.finditer(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([^\\{}]+)", s, re.S):
        w, num, hx, sym, br, txt = m.groups()
        if br == "{":
            stack.append(skip)
        elif br == "}":
            skip = stack.pop() if stack else False
        elif skip:
            continue
        elif w:                                   # a destination group ({\fonttbl ...}) is skipped to its end
            skip = w in RTF_SKIP
            out.append("\n" if w in ("par", "line") else "\t" if w == "tab" else chr(int(num) % 65536) if w == "u" and num
                       else "")
            drop = 1 if w == "u" else 0           # \uN is followed by one fallback character
        elif sym:
            skip = sym == "*"
            out.append(sym if sym in "\\{}" else {"\n": "\n", "\r": "\n", "~": " ", "_": "-"}.get(sym, ""))
        elif hx:
            out.append("" if drop else bytes.fromhex(hx).decode("cp1252", "replace"))
            drop = 0
        elif txt:
            out.append(txt.replace("\r", "").replace("\n", "")[drop:])
            drop = 0
    return "".join(out)


def csv_text(s):
    """A sheet as note lines: one cell -> '- cell' (a list item) when it is a phrase, two -> 'a: b', more -> 'a; b; c'."""
    out = []
    for row in csv.reader(io.StringIO(s)):
        cells = [c.strip() for c in row if c.strip()]
        if cells:
            out.append(("- " + cells[0] if len(cells[0].split()) >= 3 else cells[0]) if len(cells) == 1 else
                       f"{cells[0]}: {cells[1]}" if len(cells) == 2 else "; ".join(cells))
    return "\n".join(out)


def pdf_text(p, name, warn):
    """Text of a PDF: pdftotext (poppler-utils), else pypdf; '' plus a warning naming the file and the fix."""
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
    try:
        import pypdf
    except ImportError:
        warn(f"{name}: PDF notes not read (neither pdftotext nor pypdf is installed: apt-get install -y poppler-utils "
             f"or pip install pypdf, then plan again with --refresh-product)")
        return ""
    try:
        txt = "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(p).pages)
    except Exception as e:  # noqa: BLE001  (pypdf raises its own error types on broken files)
        warn(f"{name}: PDF notes not read ({e})")
        return ""
    if not txt.strip():
        warn(f"{name}: the PDF has no text layer (a scan?): put the notes in a Google Doc or a .txt in the folder")
    return txt


def note_text(f, cache, token, warn=None, taken=None):
    """Plain text of a note-like file: .txt .md .url .csv, a Google Doc (text export) or Sheet (csv export), .docx,
    .pdf (pdftotext, else pypdf), .rtf. '' plus a warning naming the file when it can't be read."""
    warn = warn or (lambda m: None)
    mime, ext = f.get("mimeType", ""), os.path.splitext(f["name"])[1].lower()
    d = os.path.join(cache, "notes")
    os.makedirs(d, exist_ok=True)
    try:
        if mime in (GDOC, GSHEET):
            from drive_upload import API, api
            with api("GET", f"{API}/drive/v3/files/{f['id']}/export?mimeType="
                            f"{'text/csv' if mime == GSHEET else 'text/plain'}", token) as r:
                txt = r.read().decode("utf-8-sig", "replace")
            open(os.path.join(d, slugify(f["name"]) + (".csv" if mime == GSHEET else ".txt")), "w").write(txt)
            return csv_text(txt) if mime == GSHEET else txt
        p = fetch_file(f, unique(os.path.join(d, f["name"]), taken if taken is not None else set()), token)
        if ext == ".docx" or mime == DOCX:
            return docx_text(p)
        if ext == ".pdf" or mime == "application/pdf":
            return pdf_text(p, f["name"], warn)
        txt = open(p, encoding="utf-8-sig", errors="replace").read()
        return rtf_text(txt) if ext == ".rtf" or "rtf" in mime else csv_text(txt) if ext == ".csv" else txt
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, urllib.error.URLError) as e:
        warn(f"{f['name']}: note not read ({e})")
        return ""


# ---------------------------------------------------------------- photos
def is_heif(path):
    """The file is HEIC / HEIF / AVIF by its content (an 'ftyp' box with a HEIF brand), whatever its name."""
    try:
        head = open(path, "rb").read(32)
    except OSError:
        return False
    return head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim",
                                                    b"heis", b"avif")


def to_jpg(src, dst, warn):
    """A photo (any PIL format or HEIC; src may have no extension, e.g. a download's temp file) -> dst as an RGB JPEG at
    most 2400 px, EXIF rotation applied: the pixels the intake's face check sees and plan reuses. None + a warning when
    it can't be read."""
    from PIL import Image, ImageOps
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()           # by content, so an extension-less temp file opens too
    except ImportError:
        pillow_heif = None
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    try:
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    except Exception as e:  # noqa: BLE001
        if is_heif(src) and pillow_heif is None:     # other converters, if installed (ffmpeg reads HEIC from 7.0 on)
            for cmd in (["heif-convert", src, dst], ["magick", src, dst],
                        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-frames:v", "1", "-q:v", "2", "-y", dst]):
                if shutil.which(cmd[0]) and subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(dst):
                    return dst
            warn(f"skipped {os.path.basename(src)}: HEIC needs pillow-heif (pip install pillow-heif)")
            return None
        warn(f"skipped {os.path.basename(src)}: cannot read image ({e})")
        return None
    im.thumbnail((2400, 2400))
    im.save(dst, "JPEG", quality=92)
    return dst


_DET = {}


def model_file(name, url):
    """Model file: pipeline/assets/models, cv2.data, else pipeline/cache/models (downloaded once)."""
    import cv2
    local = os.path.join(HERE, "cache", "models", name)
    for p in (os.path.join(HERE, "assets", "models", name), os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), name),
              local):
        if os.path.exists(p) and os.path.getsize(p) > 10000:
            return p
    os.makedirs(os.path.dirname(local), exist_ok=True)
    open(local, "wb").write(site_assets.get(url))
    return local


def detectors():
    """(YuNet DNN face detector or None, [Haar frontal, Haar profile cascades])."""
    if not _DET:
        import cv2
        try:
            cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
        except Exception:  # noqa: BLE001
            pass
        try:
            _DET["dnn"] = cv2.FaceDetectorYN.create(model_file(YUNET, YUNET_URL), "", (320, 320), 0.7, 0.3, 5000)
        except Exception:  # noqa: BLE001  (old opencv, or the model could not be fetched)
            _DET["dnn"] = None
        _DET["haar"] = []
        for n in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
            try:
                c = cv2.CascadeClassifier(model_file(n, HAAR_URL + n))
                _DET["haar"] += [] if c.empty() else [c]
            except Exception:  # noqa: BLE001
                pass
    return _DET["dnn"], _DET["haar"]


def count_faces(path, strict=False):
    """Faces in a photo or a rendered static (None: no detector, or the file can't be read).
    The DNN (YuNet, on the photo and its mirror image, at a few sizes) finds frontal, turned, small and sunglasses faces and does not
    fire on bags, so it is the check for packshots and the render QA of every static. strict=True is the 'safe' check
    for lifestyle photos (a false hit only costs one photo): it also counts every Haar frontal/profile hit, mirrored
    too, minNeighbors 3, no skin-tone filter. Without the DNN (old opencv) every check is the strict one."""
    try:
        import cv2
        dnn, haar = detectors()
    except Exception:  # noqa: BLE001  (no opencv)
        return None
    img0 = cv2.imread(path)
    if img0 is None or (dnn is None and not haar):
        return None
    n = 0
    for size in ((640, 900, 1350, 1800) if strict else (900, 1350)) if dnn is not None else ():
        s = size / max(img0.shape[:2])          # the DNN sees a face at some scales only: try a few
        if s > 1.01 and size > 900:
            continue
        img = cv2.resize(img0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        h, w = img.shape[:2]
        dnn.setInputSize((w, h))
        for im in (img, cv2.flip(img, 1)):
            f = dnn.detect(im)[1]
            n = max(n, sum(min(x[2], x[3]) >= 0.02 * min(w, h) for x in (f if f is not None else [])))
    s = 900 / max(img0.shape[:2])
    img = cv2.resize(img0, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else img0
    h, w = img.shape[:2]
    if strict or dnn is None:
        g = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        m = max(24, int(min(h, w) * 0.06))
        hits = [b for c in haar for gg in (g, cv2.flip(g, 1)) for b in c.detectMultiScale(gg, scaleFactor=1.1, minNeighbors=3,
                                                                                            minSize=(m, m))]
        n = max(n, len(hits))
    return int(n)


def photo_kind(path, clean):
    """(kind, busy) of a client photo, cheap pixel statistics at 200 px:
    packshot  clean >= 0.8 (plain packshot on white);
    detail    a close-up: under 20% plain background, one tone (the product's colour, or black) fills >= 60% of it and
              almost no skin-like pixels outside that tone;
    worn      someone wears / holds it (faces are counted separately): on a plain background the largest non-plain
              shape is cut by a frame edge (a body, a coat); in a scene, skin-like pixels outside the product's tone;
    other     the product on a plain background (an open bag, labels) or a scene without a person.
    busy = edge density (Canny): a zipper / hardware close-up is busy, a smooth leather surface is calm."""
    try:
        import cv2
        import numpy as np
        im = cv2.imread(path)
    except Exception:  # noqa: BLE001
        im = None
    if im is None:
        return ("packshot" if clean >= 0.8 else "other"), 0.0
    im = cv2.resize(im, None, fx=200 / max(im.shape[:2]), fy=200 / max(im.shape[:2]), interpolation=cv2.INTER_AREA)
    busy = round(float((cv2.Canny(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), 80, 160) > 0).mean()), 3)
    if clean >= 0.8:
        return "packshot", busy
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(int)
    ycc = cv2.cvtColor(im, cv2.COLOR_BGR2YCrCb).astype(int)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    plain = (s < 35) & (v > 185)
    tone = np.where(v < 60, 12, np.where(s <= 40, 13, h // 15))         # 12 hue bins, 12 = dark, 13 = grey
    cnt = np.bincount(tone[~plain], minlength=14) / max(int((~plain).sum()), 1)
    pair = [cnt[k] + cnt[(k + 1) % 12] for k in range(12)]               # a brown spans two hue bins
    dom = max(cnt[12], cnt[13], max(pair))
    grey = dom == cnt[13] and dom > max(pair) and dom > cnt[12]
    skin = ((ycc[..., 1] > 138) & (ycc[..., 1] < 175) & (ycc[..., 2] > 77) & (ycc[..., 2] < 127) & (v > 90) & ~plain
            & (cnt[tone] < 0.35)).mean()                                 # skin-like, not the product's own tone
    pf = plain.mean()
    if pf < 0.2 and dom >= 0.6 and skin < 0.08 and (not grey or skin < 0.03):
        return "detail", busy
    if pf >= 0.2:
        m = cv2.morphologyEx((~plain).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        if n > 1:
            big = lab == 1 + int(np.argmax(st[1:, 4]))
            if max(big[0].mean(), big[-1].mean(), big[:, 0].mean(), big[:, -1].mean()) >= 0.12:
                return "worn", busy
        return "other", busy
    return ("worn" if skin >= 0.04 else "other"), busy


def head_part(path):
    """Why a worn photo may show part of a head (a jaw, an ear, a chin, hair) although no face was found, or None:
    such a photo gets "statics": false (videos only; statics never show a face). Pixel cues at 300 px, tuned on the
    Silhouette photos (P10: hair bun + jaw + ear; P7: the edge of a chin; P6: a hand at the top, fine).
    Studio photo (a plain border): a skin- or hair-like blob that touches the top edge, stays in the upper 45% (above
    the shoulders, unlike a hand in front of the body or a strap running down to the bag) and is bordered by the
    background (it sticks out of the figure), or a figure that doesn't reach the top edge (the whole head is in frame).
    Scene (no plain border to tell the figure from): always (a person seen from behind passes every pixel cue). A false
    hit costs one static."""
    try:
        import cv2
        import numpy as np
        im = cv2.imread(path)
    except Exception:  # noqa: BLE001
        im = None
    if im is None:
        return "not checked (cannot read the photo)"
    im = cv2.resize(im, None, fx=300 / max(im.shape[:2]), fy=300 / max(im.shape[:2]), interpolation=cv2.INTER_AREA)
    H, W = im.shape[:2]
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(int)
    ycc = cv2.cvtColor(im, cv2.COLOR_BGR2YCrCb).astype(int)
    v = hsv[..., 2]
    plain = (hsv[..., 1] < 35) & (v > 185)
    edge = np.ones((H, W), bool)
    edge[8:-8, 8:-8] = False
    if plain[edge].mean() < 0.6:
        return "a person in a scene (no plain background): the head can't be ruled out"
    skin = (ycc[..., 1] > 140) & (ycc[..., 1] < 175) & (ycc[..., 2] > 77) & (ycc[..., 2] < 127) & (v > 90) & ~plain \
        & (hsv[..., 0] >= 8) & (hsv[..., 0] <= 25)                      # (a reddish-brown strap, hue under 8, is no skin)
    fig = cv2.morphologyEx((~plain).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fig, 8)
    if n > 1 and st[1 + int(np.argmax(st[1:, 4])), 1] > 0.03 * H:
        return "the figure ends below the top edge (the whole head is in frame)"
    ring_k = np.ones((5, 5), np.uint8)
    for what, mask, need in (("skin", skin, 0.3), ("hair", v < 80, 0.15)):
        m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        for i in range(1, n):
            x, y, w, h, a = (int(t) for t in st[i])
            if y > 0.02 * H or y + h > 0.45 * H or a < 0.0012 * H * W:
                continue
            c = lab == i
            ring = (cv2.dilate(c.astype(np.uint8), ring_k) > 0) & ~c
            if plain[ring].mean() >= need:
                return (f"{what}-like area at the top edge, above the shoulders (x {x / W:.0%}-{(x + w) / W:.0%}, "
                        f"to {(y + h) / H:.0%} of the height)")
    return None


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


def scene_scores(path):
    """[(t, frame-difference score 0..1)] at 4 fps over the first 2 minutes (ffmpeg scene score, 160 px: ~45 s for 4K)."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-t", "120", "-i", path, "-an", "-vf",
           "fps=4,scale=160:-2,select='gte(scene,0)',metadata=print", "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return []
    return [(float(t), float(s)) for t, s in re.findall(r"pts_time:([\d.]+)[^\n]*\n[^\n]*lavfi\.scene_score=([\d.]+)",
                                                         r.stderr)]


def good_starts(path, dur, n=None, tail=2.5, scores=None):
    """Start times: n (default about one per 4.5 s, 1-8), just after the biggest frame-difference peaks (scene changes,
    score >= 0.08), the rest filled evenly. Each leaves >= tail seconds (half the clip for short ones)."""
    n = n or max(1, min(8, int(round(dur / 4.5))))
    tail = min(tail, dur / 2)
    span = dur - tail
    if span < 0.3:
        return [0.0]
    if span < 3.0:
        return sorted({round(0.3 + (span - 0.3) * k / max(n - 1, 1), 1) for k in range(min(n, 3))})
    sc = scores if scores is not None else scene_scores(path)
    peaks = [(s, t) for k, (t, s) in enumerate(sc) if s >= 0.08 and s >= max(x[1] for x in sc[max(0, k - 2):k + 3])]
    gap = max(1.5, 0.6 * span / n)
    picks = []
    for _, t in sorted(peaks, reverse=True):
        t = round(min(max(t + 0.3, 0.3), span), 1)
        if len(picks) < n and all(abs(t - p) >= gap for p in picks):
            picks.append(t)
    for g in (gap, gap / 2):                     # still short of n: evenly spaced, farthest from the picks first
        even = [round(0.3 + (span - 0.3) * (k + 0.5) / n, 1) for k in range(n)]
        for t in sorted(even, key=lambda t: -min([abs(t - p) for p in picks] or [span])):
            if len(picks) < n and all(abs(t - p) >= g for p in picks):
                picks.append(t)
    return sorted(picks)


def moment_rank(scores, t):
    """How fresh a start is: the frame-difference peak just before it (a start right after a cut opens a new shot)."""
    return max([s for x, s in scores or [] if t - 0.8 <= x <= t] or [0.0])


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
    even = [t for t in {round(dur * (0.03 + 0.94 * k / 8), 1) for k in range(9)} if all(abs(t - g) > 0.4 for g in c["good"])]
    even = sorted(even, key=lambda t: -min([abs(t - g) for g in c["good"]] or [dur]))[:max(0, 12 - len(c["good"]))]
    keep = sorted(set(c["good"]) | set(even))       # every proposed start, filled up to 12 frames
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
    pt = [tile(f"P{i} {p.get('kind', '')} {p['clean']:.2f} " + ("no statics" if p.get("statics") is False and
                                                              p["faces"] == 0 else f"faces {p['faces']}"),
               Image.open(os.path.join(ROOT, p["path"])), bool(p["faces"]) or p.get("statics") is False)
          for i, p in enumerate(photos)]
    ct = [tile(f"C{i} @{t:.1f}s {c['name'][:14]}", good_frames.get((i, t))) for i, c in enumerate(clips) for t in c["good"]]
    st = [tile(f"S{i} clean {sc:.2f} faces {fc}", Image.open(f), bool(fc)) for i, (f, sc, fc) in enumerate(site_imgs)]
    for name, ts in (("CLIENT PHOTOS (red = a face: never used; no statics = part of a head: videos only)", pt), ("CLIP START TIMES", ct),
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


NEG = re.compile(r"\b(?:no|not|never|without|nor|isn't|aren't|doesn't|don't|won't|n't)\b", re.I)
NEG_AFTER = re.compile(r"^[^.;\n]{0,40}?\b(?:ended|expired|is over|no longer|not (?:included|available|any ?more)|"
                       r"discontinued|cancell?ed)\b|^[\s:=\-–—]*(?:none|n/?a|no)\b", re.I)


def clause_start(text, i):
    """Start of the clause that holds position i (after '. ', a new line, ';', '!', '?' or ' but '; a decimal point
    such as $59.95 is no boundary)."""
    return max([0] + [j + len(s) for s in (". ", ".\n", "\n", "; ", "! ", "? ", " but ") for j in [text.rfind(s, 0, i)]
                      if j >= 0])


def negated(text, m):
    """The match is denied in its clause: 'No free gift', 'not 50% off' before it, 'Free gift: none' or '... ended' after."""
    return bool(NEG.search(text[clause_start(text, m.start()):m.start()]) or NEG_AFTER.search(text[m.end():]))


def gift_hits(text):
    """GIFT matches that are not negated in their clause ('No free gift is mentioned' is no gift)."""
    return [m for m in GIFT.finditer(text or "") if not negated(text, m)]


def sentence_around(text, m):
    a = max(text.rfind(". ", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
    e = [i for i in (text.find(". ", m.end()), text.find("\n", m.end())) if i >= 0]
    return re.sub(r"\s+", " ", text[a:(min(e) + 1 if e else len(text))]).strip()[:160]


PCT = re.compile(r"(\d{1,2})\s*(?:%|percent)\s*(?:off|discount)\b|\b(?:save|sale|discount(?:ed)?(?:\s+by)?|take)\s*:?\s*"
                 r"(\d{1,2})\s*(?:%|percent)|\bhalf[- ](?:price|off)\b", re.I)
NO_DEAL = re.compile(r"\bno (?:discount|sale|offer|deal|promotion)s?\b|\bnot (?:on sale|discounted)\b", re.I)
MONEY = re.compile(r"(?<![\w.,])(US\$|\$|USD ?|€|£)?(\d{1,5}(?:,\d{3})*(?:\.\d{1,2})?)(?![\w%×]|\.\d|\s*(?:%|percent))",
                   re.I)
WAS_W = re.compile(r"\b(?:was|were|regular(?:ly)?|reg|compare[ds]?(?:[ -]at)?|original(?:ly)?|rrp|msrp|retail|before|"
                   r"instead of|usually|normally|full price)\b", re.I)
PRICE_W = re.compile(r"\b(?:was|regular(?:ly)?|reg|compare[ds]?(?:[ -]at)?|original(?:ly)?|rrp|msrp|retail|instead of|now|"
                     r"prices?|sale price|costs?)\b[\s:=\-–(]*$", re.I)
PRICE_NEXT = re.compile(r"usd|dollars?|eur|now|was|compare[ds]?|regular|reg|rrp|retail|original(?:ly)?|instead|today|only|"
                        r"each|sale|price", re.I)


def stated_pcts(text):
    """[(pct, sentence)] the notes state as an offer ('50% off', 'SALE 40% OFF', 'save 30%', 'half price'); negated
    ones ('not 50% off', '50% off ended') are left out."""
    text = text or ""
    return [(int(next((g for g in m.groups() if g), "50")), sentence_around(text, m)) for m in PCT.finditer(text)
            if not negated(text, m)]


def notes_prices(text):
    """(price, compare_at, line) from the client's notes: '$59.95 (was $119.95)', 'was $119.95, now $59.95',
    'Price: 59.95 / compare at 119.95', 'Now $49, was $99'. A price without a was-price: (price, None, line).
    A bare number counts only with a currency sign or a price word right before it ('Price: 59.95')."""
    single = (None, None, None)
    for ln in (text or "").splitlines():
        now, was, end = [], [], 0
        for m in MONEY.finditer(ln):
            pre, end = ln[end:m.start()], m.end()
            v = money(m.group(2).replace(",", ""))
            nxt = re.match(r"\s*([a-z]+)", ln[m.end():], re.I)        # a bare '3 colours' / 'now 12 pockets' is no price
            bare = (v or 0) < 5 or nxt and not PRICE_NEXT.fullmatch(nxt.group(1))
            if v and (m.group(1) or PRICE_W.search(pre) and not bare):
                (was if WAS_W.search(pre) else now).append(v)
        if now and was and max(was) >= now[0] * 1.05:
            return now[0], max(was), ln.strip()
        if now and not single[0]:
            single = (now[0], None, ln.strip())
    return single


def site_pct(price, was):
    """Discount from the site prices, rounded down to a multiple of 5 (52.50 vs 105.00 -> 50; 69.95 vs 174.88 -> 60);
    0 when there is no real compare-at price."""
    price, was = money(price), money(was)
    return int(math.floor(round(100 * (1 - price / was), 1) / 5) * 5) if price and was and was >= price * 1.1 else 0


HOOK_TYPES = ("problem", "curiosity", "question", "feature", "offer", "gift", "travel", "POV", "story")   # = projects.TYPES
GIFT_ONLY = re.compile(r"pouch|wallet|purse", re.I)
SALEY = re.compile(r"\bdeals?\b|\bsales?\b|came early|last call|selling (?:fast|out)|sold out|clearance|ends tonight|"
                   r"today only|limited time|half (?:price|off)", re.I)


def unbacked(s, pct=None, gift=None):
    """What s claims that the offer does not back (None when it is honest): a % off without a discount (or another %),
    something free without a gift, sale/urgency words ('deal', 'last call', 'selling fast') without any deal."""
    s = s or ""
    if re.search(r"half (?:price|off)", s, re.I) and str(pct) != "50":
        return "half price"
    for m in re.finditer(r"(\d+)\s*%\s*(?:off|discount)|\bsave (\d+)\s*%|(\d+)\s*% (?:sale|deal)", s, re.I):
        n = next(g for g in m.groups() if g)
        if str(n) != str(pct):
            return f"{n}% off"
    if re.search(r"percent off", s, re.I) and not pct:
        return "a discount"
    if pct and re.search(r"percent", s, re.I) and say(int(pct)) + " percent" not in s.lower():
        return "another percent"
    if not gift and re.search(r"(?<![-\w])free\b(?!\s+(?:US\s+|U\.S\.\s+)?(?:shipping|delivery))|\b(?:comes|arrives) with an? (?:\w+ ){0,2}"
                              r"(?:pouch|wallet|purse)|\bincludes? an? (?:\w+ ){0,2}(?:pouch|wallet|purse)", s, re.I):
        return "a free gift"
    if not (pct or gift) and SALEY.search(s):
        return "a sale"
    return None


def draft_offer(facts, notes, short, warn=None):
    """Offer block. %: from the prices in facts (the intake puts the notes' prices there, else the site's; without any,
    the notes' own prices) and an "NN% off" the notes state; both and they disagree (or the notes say 'no discount'):
    the lower, with a warning. Gift: a non-negated 'free pouch / wallet ...' phrase in the notes, else (only when the
    notes don't mention a gift at all) in the site title / variants / description. Nothing without a line behind it."""
    warn = warn or (lambda m: None)
    notes = notes or ""
    price, was, src = money(facts.get("price")), money(facts.get("compare_at")), facts.get("price_source") or "site"
    line = facts.get("price_line")
    if not price:
        price, was, line = notes_prices(notes)
        src = "notes"
    pct_p = site_pct(price, was)
    said = stated_pcts(notes)
    pct_s = said[0][0] if said else 0
    pct = min(x for x in (pct_p, pct_s) if x) if pct_p or pct_s else 0
    evidence = []
    if pct_p:
        evidence.append(f"{src} price {price:g} vs compare-at {was:g} = {pct_p}% off" + (f": \"{line}\"" if line else ""))
    if pct_s:
        evidence.append(f"notes say: \"{said[0][1]}\"")
    if pct_p and pct_s and pct_p != pct_s:
        warn(f"the {src} prices give {pct_p}% off but the notes say {pct_s}% off: the ads use the lower, {pct}%")
    if pct and not pct_s and NO_DEAL.search(notes):
        warn(f"the {src} prices give {pct}% off but the notes say \"{NO_DEAL.search(notes).group(0)}\": no % in the ads")
        evidence.append(f"not used ({src} {pct}% off): the notes say \"{sentence_around(notes, NO_DEAL.search(notes))}\"")
        pct = 0
    site = [("site title", facts.get("title") or ""), ("site variants", " | ".join(facts.get("variant_titles") or [])),
            ("site description", facts.get("description") or "")]
    hits = [(m.group(0), "notes", sentence_around(notes, m)) for m in gift_hits(notes)]
    if not hits and not GIFT.search(notes):
        hits = [(m.group(0), w, sentence_around(t, m)) for w, t in site for m in gift_hits(t)]
    gift = re.sub(r"\s+", " ", max(hits, key=lambda h: len(h[0]))[0].lower()) if hits else None
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
    evidence += [f"{w}: \"{q}\"" for g, w, q in hits[:4]]
    return dict(badge={"top": "NOW", "big": f"{pct}%", "bottom": "OFF"} if pct else None, gift=gift,
                offer_title=f"{pct}% OFF" if pct else "", offer_sub=f"+ {gift.upper()}" if gift else "",
                statics_sub=sub, close=close, evidence=evidence)


def notes_colours(notes):
    m = re.search(r"^\W*(?:available\s+)?colou?rs?(?:\s+available)?\s*[:\-]\s*(.+)$", notes or "", re.I | re.M)
    if not m:       # inside a line, the way clients write it: "Price: Now $69, was $99. ... Colours: Cream, Sage, Midnight"
        m = re.search(r"(?:^|[.;|]\s+)(?:available\s+)?colou?rs?(?:\s+available)?\s*:\s*(.+)$", notes or "", re.I | re.M)
    if not m:
        return []
    txt = re.split(r"\.\s+(?=[A-Z])", m.group(1))[0]            # up to the end of that sentence
    return [c.strip(" .").title() for c in re.split(r",|/|\band\b|\bor\b", re.sub(r"\([^)]*\)", "", txt))
            if c.strip(" .")]


def spoken(s):
    s = re.sub(r"\s+", " ", s.replace(" & ", " and ").replace("’", "'")).strip(" -*•·:;,")
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = s[:1].upper() + s[1:]
    return s if s[-1:] in ".!?" else s + "."


def short_line(s, most=14):
    """s as one spoken sentence of at most `most` words; a longer one is cut at its last clause boundary that fits
    (':', ';', ' - ', ', while / so / and / but / which / without ...'); None when no clause of 4+ words fits."""
    s = spoken(s)
    if len(s.split()) <= most:
        return s
    best = None
    for m in re.finditer(r"\s*(?:[:;]|\s[-–—]\s|,\s+(?=(?:while|so|and|but|which|without|giving|making|with|that|"
                         r"because|plus)\b))", s):
        if 4 <= len(s[:m.start()].split()) <= most:
            best = s[:m.start()]
    return spoken(best) if best else None


def tags_for(s, highlights=()):
    """[(tag, named)] for a line, best first: every TAGS hit in TAGS order, then a highlight it quotes (named: a known
    feature), else its first two distinctive words (not named)."""
    out = []
    for pat, tag in TAGS:
        t = (tag(s) if callable(tag) else tag) if re.search(pat, s, re.I) else None
        if t and t not in [x for x, _ in out]:
            out.append((t, True))
    out += [(h.upper(), True) for h in highlights or [] if h.lower() in s.lower() and 2 <= len(h.split()) <= 3
            and h.upper() not in [x for x, _ in out]]
    if not out:
        w = [x for x in re.findall(r"[A-Za-z][A-Za-z\-']+", s) if x.lower() not in GENERIC | {"it", "its", "your", "you", "is"}]
        out.append((" ".join(w[:2]).upper(), False))
    return out


def tag_for(s, highlights=()):
    return tags_for(s, highlights)[0][0]


def known_tag(t):
    """The on-screen tag is one TAGS gives for a known feature ('SMOOTH LEATHER'), not the two odd words of a line that
    matched none ('SIMPLE CLEAN'): the recap block reads only known tags aloud."""
    return any(isinstance(g, str) and g == t for _, g in TAGS) or \
        bool(re.fullmatch(r"(?:SMOOTH|SOFT|LUXE) (?:LEATHER|FEEL)|[A-Z]+ LEATHER|LEATHER FINISH", t))


def other_names(key, products_dir=PRODUCTS_DIR):
    """Names of the other products (built-in bags + product files) that a line about this one must not mention."""
    own = set(re.findall(r"[a-z0-9.\-]+", (key or "").lower()))
    out = [n for n in OTHER_NAMES if not set(n.split()) & own]
    for k, d in load_all(products_dir).items():
        if k != key:
            out += [n.lower() for n in [k, d.get("short")] + list(d.get("aliases") or [])
                    if n and len(n) >= 5 and not set(n.lower().split()) & own]
    return out


def names_other(s, own, others=()):
    """The sentence names another product: 'The Libra Covenette Bag ...' (a capitalised name with Libra or a bag word
    whose words are not this product's), or a known other product ('Hobo Bag')."""
    for m in re.finditer(r"(?:\b(?:The|the|Libra|libra)\s+)?((?:[A-Z][\w'.\-]*\s+){0,3}[A-Z][\w'.\-]*)(\s+(?:"
                         + PNOUN + r"))?\b", s):
        ws = m.group(1).split()
        named = m.group(2) or re.fullmatch(PNOUN, ws[-1].lower()) or "libra" in m.group(0).lower()
        if m.start(1) == 0 and len(ws) == 1:
            continue                                 # just the sentence's first word ('Slim shoulder straps', 'Adjustable crossbody strap')
        distinct = {w.lower().strip(".'") for w in ws} - GENERIC - {"the", "libra", "cases"} - \
            {w for w in (x.lower() for x in ws) if re.fullmatch(PNOUN, w)}
        if named and distinct and not distinct <= own:
            return m.group(0).strip()
    low = s.lower()
    return next((n for n in others if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", low)), None)


def route(text):
    """The photo kind a feature line is about (ROUTES: most word hits, ties in ROUTES order), None for no hit."""
    hits = [(len(rx.findall(text)), -i, k) for i, (k, rx) in enumerate(ROUTES)]
    best = max(hits)
    return best[2] if best[0] else None


def feature_texts(notes, facts):
    """[(text, source, group)]: the client's bullet list (group 0), the other note sentences (1), the site's (2)."""
    out = []
    lines = [ln.strip() for ln in (notes or "").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    bullets = any(re.match(r"(?:[-*•·–]|\d+[.)])\s+", ln) for ln in lines)
    for ln in lines:
        b = re.match(r"(?:[-*•·–]|\d+[.)])\s+(.*)", ln)
        if b:
            out.append((b.group(1), "notes", 0))
        elif not ln.endswith(":") and not META.match(ln):
            parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", ln)
            # notes with no bullet marks at all ("one fact per line", as the client guide asks): a line that is one short
            # sentence is the client's own list entry, like a bullet (a sentence of a paragraph stays an "other" sentence)
            own = not bullets and len(parts) == 1 and 3 <= len(ln.split()) <= 14
            out += [(x, "notes", 0 if own else 1) for x in parts]
    return out + [(x, "site", 2) for x in facts.get("bullets") or []]


def compliance_ctx(facts, notes):
    """compliance.check context for our own feature lines: claims and numbers only from the notes (+ the site text
    when it was read); the offer is checked separately (unbacked)."""
    import compliance
    src = "\n".join(x for x in (notes, facts.get("description"), " ".join(facts.get("bullets") or [])) if x)
    return dict(offer=None, pct=None, gift=None, corpus=compliance.corpus_text(src),
                numbers={round(v, 2) for v, *_ in compliance.numbers(src)})


def candidates(facts, notes, key="", name="", offer=None, products_dir=PRODUCTS_DIR, why=None):
    """Feature candidates [{line, tag, source, score, route}], best first: the client's bullets, then the other note
    sentences, then the site's. A line is one spoken sentence of at most 14 words. Dropped (reason into `why`): a line
    naming another product, one compliance.py flags, sales / offer talk (SALESY), odd words (ODD), more than the
    offer backs (unbacked), a client bullet whose every tag choice another line took."""
    import compliance
    why = why if why is not None else []
    own = {w for w in re.findall(r"[a-z0-9.\-']+", f"{key} {name}".lower())} - GENERIC - {"the"}
    others, ctx = other_names(key, products_dir), compliance_ctx(facts, notes)
    pct, gift = offer or (None, None)
    ok, res = [], []
    for n, (s, src, group) in enumerate(feature_texts(notes, facts)):
        if len(s.split()) < 3 or len(s.split()) > 40 or SALESY.search(s):
            continue
        line = short_line(s)
        bad = ("longer than 14 words" if not line else ("names " + o) if (o := names_other(s, own, others)) else
               "odd word " + ODD.search(s).group(0) if ODD.search(s) else None)
        if not bad:
            pr = compliance.check([line], ctx=ctx)
            bad = f"compliance: {pr[0]['term']} ({pr[0]['category']})" if pr else unbacked(line, pct, gift)
        if bad:
            why.append(f"{src}: \"{s[:70]}\" not used: {bad}")
            continue
        tags = tags_for(line, facts.get("highlights") or [])
        if not group and (not tags[0][0].strip() or (not tags[0][1] and set(tags[0][0].lower().split()) <= own)):
            continue                                 # a list entry that only restates the product's name (a title line)
        if group and (not tags[0][1] or len(line.split()) < 5):
            continue                                 # outside the client's list: only lines about a known feature
        ok.append((group, n, s, src, line, [t for t, named in tags if named or not group]))
    seen = {}
    for group, n, s, src, line, tags in sorted(ok, key=lambda c: (c[0], len(c[5]), c[1])):
        tag = next((t for t in tags if t not in seen), None)   # bullets first; a line with fewer tag choices first
        if tag is None:
            if not group:
                why.append(f"{src}: \"{s[:70]}\" not used: its on-screen tag {tags[0]} is taken by "
                           f"\"{seen[tags[0]][:50]}\"")
            continue
        seen[tag] = line
        hits = sum(bool(re.search(p, line, re.I)) for p, t in TAGS if t not in SOFT_TAGS)
        res.append(dict(line=line, tag=tag, source=src, group=group, order=n, route=route(f"{line} {tag}"),
                        score=hits - (2 if GIFT.search(line) else 0)))
    res.sort(key=lambda c: (c["group"], -c["score"], c["order"]))
    return res


MAX_FEATURES = 7     # a Drive product's features video: ~40-50 s with 7 lines (validate: 3-7)


def pick_features(cands, most=MAX_FEATURES):
    """Up to `most` candidates in the client's order (best ones chosen, as ranked by candidates)."""
    return sorted(cands[:most], key=lambda c: (c["group"], c["order"]))


def topics(text):
    w = set(re.findall(r"[a-z]+", text.lower()))
    return {i for i, g in enumerate(CLIP_TOPICS) if w & g}


def draft_picks(feats, clips, photos=(), busy=None, scores=None):
    """Fills f["picks"] of each feature and returns (hook_clips, broll).
    A feature gets the photo whose kind shows its words (route: zip / stitching -> a detail close-up, the busiest for
    hardware, the calmest for a leather surface; straps -> worn; room -> the open-bag shot (other); shape / colour ->
    a packshot) first, then a clip moment; features don't share a photo or a moment while unused ones are left, and
    the moments of one clip are spread over its length (moments used up: a second photo rather than a repeated
    moment). hook_clips: the freshest moments (right after a cut) that no feature uses (2 kept back when moments are
    few and photos many), else worn photos. broll: 5-8 distinct shots (moments, worn photos, packshots). Never a photo
    with a face (faces != 0). Photo picks are ["photo", "P<n>"] = photos[n]; clip picks ["clip", i, start]."""
    busy, scores = busy or {}, scores or {}
    ok = [i for i, p in enumerate(photos) if p.get("faces") == 0]
    moments = [(i, t) for i, c in enumerate(clips) for t in c.get("good") or []]
    if not ok and not moments:                       # a site-only product: photos of the plan's pool (site packshots)
        for j, f in enumerate(feats):
            f["picks"] = [["photo", 2 * j], ["photo", 2 * j + 1]]
        return [["photo", 0], ["photo", 1]], [["photo", k] for k in range(2, 7)]
    used_p, used_m = {i: 0 for i in ok}, {m: 0 for m in moments}
    P = lambda i: ["photo", f"P{i}"]  # noqa: E731
    M = lambda m: ["clip", m[0], m[1]]  # noqa: E731
    rank = sorted(moments, key=lambda m: (not HOOKY.search(clips[m[0]]["name"]), -moment_rank(scores.get(m[0]), m[1]),
                                          m))
    spare = len(moments) - len(feats)               # few moments but photos to spare: still keep 2 fresh hook moments
    n_hook = min(3, spare) if spare > 0 else min(2, len(moments) // 3) if len(ok) >= len(feats) + 2 else 0
    hook = [M(m) for m in rank[:n_hook]]
    for m in rank[:n_hook]:
        used_m[m] += 1

    def photo_for(f, kinds, other_than=()):
        """An unused photo of the feature's kinds; else (first pick) a used one of those kinds rather than an unrelated
        shot, (second pick, other_than set) any unused photo before sharing."""
        words = f["line"] + " " + f["tag"]
        sub = (lambda i: -busy.get(i, 0)) if HARDWARE.search(words) else \
            (lambda i: busy.get(i, 0)) if SURFACE.search(words) else (lambda i: 0)
        pool = [i for i in ok if i not in other_than]
        for c in ([i for i in pool if photos[i].get("kind") == k and not used_p[i]] for k in kinds):
            if c:
                return min(c, key=lambda i: (sub(i), i))
        rel_ = [i for i in pool if photos[i].get("kind") in kinds]
        free = [i for i in pool if not used_p[i]]
        c = (free or rel_ or pool) if other_than else (rel_ or free or pool)
        return min(c, key=lambda i: (used_p[i], sub(i), i)) if c else None

    def moment_for(f, fresh=False):
        """The feature's moment: clip-name topics, then far from the clip's used moments; fresh: an unused one only."""
        cand = [m for m in moments if not (fresh and used_m[m])]
        if not cand:
            return None
        ft = topics(f["line"] + " " + f["tag"])

        def gap(m):
            ts = [t for (i, t), u in used_m.items() if u and i == m[0]]
            return min([abs(m[1] - t) for t in ts] or [1e9])
        return min(cand, key=lambda m: (used_m[m], -len(ft & topics(clips[m[0]]["name"])), -gap(m), m))
    order = sorted(feats, key=lambda f: f.get("route") is None)       # routed features choose their photo first
    for f in order:
        kinds = PREFER[f.get("route")]
        i = photo_for(f, kinds)
        m = moment_for(f, fresh=bool(ok))            # (moments used up: a second photo below rather than a repeat)
        f["picks"] = [P(i)] if i is not None else []
        if i is not None:
            used_p[i] += 1
        if m:
            used_m[m] += 1                           # the photo that shows the line first, else the moving shot first
            f["picks"].insert(len(f["picks"]) if f["picks"] and f.get("route") and photos[i].get("kind") in kinds else 0,
                              M(m))
    for f in order:                                  # no clips: a second photo; no photos: a second moment
        if len(f["picks"]) < 2:
            first = {int(p[1][1:]) for p in f["picks"] if p[0] == "photo"} or {-1}
            j = photo_for(f, PREFER[f.get("route")], other_than=first) if ok else None
            m2 = None if j is not None or not moments else moment_for(f)
            if j is not None and P(j) not in f["picks"]:
                used_p[j] += 1
                f["picks"].append(P(j))
            elif m2 and M(m2) not in f["picks"]:
                used_m[m2] += 1
                f["picks"].append(M(m2))
    of = {k: sorted((i for i in ok if photos[i].get("kind") == k), key=lambda i: (used_p[i], i)) for k in KINDS}
    if not hook:
        hook = [M(m) for m in rank[:1]] or [P(i) for i in of["worn"][:3]] or [P(i) for i in ok[:2]]
    hooks = {(h[1], h[2]) for h in hook if h[0] == "clip"}
    again = sorted(moments, key=lambda m: (used_m[m], m in hooks, rank.index(m)))
    broll = [M(m) for m in moments if not used_m[m]] + [P(i) for i in of["worn"][:2] + of["packshot"][:2]] + \
        [M(m) for m in again] + [P(i) for i in of["worn"][2:] + of["packshot"][2:] + of["other"] + of["detail"]]
    return hook, [x for n, x in enumerate(broll) if x not in broll[:n]][:8]


# ---------------------------------------------------------------- intake (Python API: make_batch.py calls these)
SIG_KEYS = ("key", "aliases", "name", "short", "end", "site", "photos", "clips", "offer", "hook_clips", "features",
            "customer", "broll", "reviews", "hooks", "site_lifestyle", "status")


def content_sig(d):
    """Hash of what a person may edit by hand (not facts / source / tests): an "auto" file whose hash changed was
    edited after the intake, so ensure() keeps it."""
    return hashlib.sha1(json.dumps({k: d.get(k) for k in SIG_KEYS}, sort_keys=True).encode()).hexdigest()[:16]


def product_files_by_folder(products_dir=PRODUCTS_DIR):
    out = []
    for f in sorted(glob.glob(os.path.join(products_dir, "*.json"))):
        try:
            out.append((f, json.load(open(f))))
        except (ValueError, OSError):
            continue
    return out


def file_for_folder(folder, products_dir=PRODUCTS_DIR):
    """(path, product dict) of a New Products folder's product file (source.drive_folder, else the slug), or (None, None)."""
    rows = product_files_by_folder(products_dir)
    hit = next(((f, d) for f, d in rows if (d.get("source") or {}).get("drive_folder") == folder["id"]), None)
    slug = slugify(names_for(folder["name"])[0])
    return hit or next(((f, d) for f, d in rows if os.path.basename(f) == slug + ".json"), (None, None))


def _resolve_source(folder, latest, local, site):
    """(token, files, folder dict or None, folder name, source kind)."""
    if local:
        files = local_files(local)
        if not files:
            raise ValueError(f"no files in {local}")
        return None, files, None, os.path.basename(os.path.abspath(local).rstrip("/")), "local"
    if folder or latest:
        token = _token()
        if isinstance(folder, dict):                 # a Drive folder row (ensure() passes the one it found)
            fo = folder
        else:
            fs = _folders(token)
            fo = fs[0] if latest and not folder else find_folder(fs, folder)
        try:
            files = drive_files(token, fo["id"])
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(f"cannot list Drive folder {fo['name']!r}: {e}") from e
        return token, files, fo, fo["name"], "drive"
    if site:
        return None, [], None, "", "site"
    raise ValueError("give a New Products folder name, latest, a libracases.com page (site) or a local folder")


def intake(folder=None, latest=False, local=None, site=None, name=None, products_dir=PRODUCTS_DIR, cache=CACHE_DIR,
           use_site=False, force=False, draft=False, max_photos=20, max_clips=12):
    """A New Products folder (name: exact or a unique part, or a Drive folder row; latest=True: the newest), a local
    dir or a site page -> pipeline/data/products/<slug>.json. Drive-only unless site (a libracases.com url or handle)
    or use_site (the notes' link, else a name match): the site then fills only what the folder lacks. Ready + "auto":
    true when validate() finds no problems (fewer than 3 features only warns: plan pads thin products; draft=True: always draft); a ready file is
    redone only with force. "tests" of an earlier file are kept.
    Returns dict(file, key, status, problems, warnings, summary); raises ValueError (never exits)."""
    warnings = []
    warn = warnings.append
    token, files, fo, folder_name, src_kind = _resolve_source(folder, latest, local, site)

    # site: --site, or (use_site) a libracases.com link in the notes, else the name (only on a clear match)
    handle = site_title = None
    how = ""
    if site:
        try:
            handle, how = site_assets.find_handle(site), "--site"
        except site_assets.NoMatch as e:
            raise ValueError(str(e)) from e
    display = name or folder_name
    if not display and handle:
        try:
            site_title = json.loads(site_assets.get(f"{site_assets.SITE}/products/{handle}.json"))["product"]["title"]
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            raise ValueError(f"libracases.com page {handle!r} unreadable ({e}): pass name=") from e
        display = clean_title(site_title)
    key, pname, short, end = names_for(display)
    slug = slugify(key)
    out_file = os.path.join(products_dir, slug + ".json")
    old = {}
    if os.path.exists(out_file):
        try:
            old = json.load(open(out_file))
        except ValueError:
            old = {}
        if old.get("status") == "ready" and not force:
            raise ValueError(f"{rel(out_file)} is already 'ready'. Use force (--force) to redo the intake (it "
                             f"overwrites any hand edits).")
        warn(f"replacing the earlier {rel(out_file)}")
    cache = os.path.join(cache, slug)
    for sub in ("photos", "clips", "notes", "raw", "sheets"):
        os.makedirs(os.path.join(cache, sub), exist_ok=True)

    # notes: every note-like file + the folder's own description
    taken = set()
    notes_files = [f for f in files if kind(f["name"], f.get("mimeType", "")) == "note"]
    parts = [f"## {f['name']}\n{note_text(f, cache, token, warn, taken)}" for f in notes_files]
    desc = folder_description(token, fo["id"]) if fo else ""
    notes = "\n\n".join(([f"## folder description\n{desc}"] if desc else []) + parts).strip()
    link = SITE_URL.search(notes)
    if src_kind != "site" and not notes_files and not desc:
        warn("the folder has no notes file (price, colours, what makes it special): no offer and features only "
             "from what the site says" if (site or use_site) else
             "the folder has no notes file (price, colours, what makes it special): no offer, no feature lines")
    if use_site and not handle:
        if link:
            handle, how = site_assets.handle_from_url(link.group(0)), "link in notes"
        else:
            try:
                handle, how = site_assets.find_handle(display), "matched by name: CHECK it is the same product"
            except site_assets.NoMatch as e:
                warn(f"no libracases.com page found (no link in notes, name not on the site): {str(e).splitlines()[0]}")
    sfacts = {}
    if handle:
        try:
            sfacts = site_assets.fetch(handle, os.path.join(cache, "site"), key=slug.replace("-", "_")[:24])
        except (site_assets.NoMatch, OSError, ValueError) as e:
            warn(f"site fetch failed for {handle}: {e}")
            handle = None

    # photos: jpg, clean score, faces, kind (packshot / worn / detail / other), statics (false: may show part of a head,
    # videos only); src_name = the Drive original's name (make_batch converts a re-download the same way: to_jpg)
    photos, busy_of, heads = [], {}, {}
    for f in [f for f in files if kind(f["name"], f.get("mimeType", "")) == "photo"][:max_photos]:
        try:
            raw = fetch_file(f, unique(os.path.join(cache, "raw", f["name"]), taken), token)
        except (urllib.error.URLError, OSError, ValueError) as e:
            warn(f"skipped {f['name']}: download failed ({e})")
            continue
        dst = to_jpg(raw, unique(os.path.join(cache, "photos", os.path.splitext(f["name"])[0] + ".jpg"), taken), warn)
        if dst:
            from PIL import Image
            w, h = Image.open(dst).size
            sc = site_assets.clean_score(dst)
            k, busy = photo_kind(dst, sc)
            faces = count_faces(dst, strict=sc < 0.8)
            head = head_part(dst) if k == "worn" and faces == 0 else None
            photos.append(dict(id=f["id"], name=os.path.basename(dst), src_name=f["name"], clean=sc, faces=faces,
                               statics=faces == 0 and not head, kind=k, w=w, h=h, path=rel(dst)))
            busy_of[dst], heads[dst] = busy, head
    photos.sort(key=lambda p: (bool(p["faces"]), -p["clean"]))
    busy = {i: busy_of.get(os.path.join(ROOT, p["path"]), busy_of.get(p["path"], 0)) for i, p in enumerate(photos)}
    for i, p in enumerate(photos):
        hd = heads.get(os.path.join(ROOT, p["path"]), heads.get(p["path"]))
        if hd:
            warn(f"P{i} {p['src_name']}: no face found, but it may show part of a head ({hd}): \"statics\": false "
                 f"(videos only, never in a static)")
    if any(p["faces"] is None for p in photos):
        warn("face check unavailable (opencv or its face model missing): look at every photo before using it in statics")

    # clips: start times after scene changes (about one per 4.5 s), contact sheets
    clips, good_frames, scores = [], {}, {}
    vids = [f for f in files if kind(f["name"], f.get("mimeType", "")) == "clip"]
    if len(vids) > max_clips:
        warn(f"{len(vids)} clips, only the first {max_clips} taken (--max-clips)")
    for f in vids[:max_clips]:
        try:
            p = fetch_file(f, unique(os.path.join(cache, "clips", f["name"]), taken), token)
        except (urllib.error.URLError, OSError, ValueError) as e:
            warn(f"skipped {f['name']}: download failed ({e})")
            continue
        pr = probe(p)
        if not pr["dur"]:
            warn(f"skipped {f['name']}: ffprobe found no video")
            continue
        sc = scene_scores(p)
        c = dict(id=f["id"], name=f["name"], dur=pr["dur"], w=pr["w"], h=pr["h"], good=good_starts(p, pr["dur"], scores=sc),
                 mute=True, audio=pr["audio"], path=rel(p))
        sheet = os.path.join(cache, "sheets", slugify(os.path.splitext(f["name"])[0]) + ".jpg")
        for t, im in contact_sheet(p, c, sheet).items():
            good_frames[(len(clips), t)] = im
        c["sheet"] = rel(sheet)
        scores[len(clips)] = sc
        clips.append(c)
    if any(c["id"] is None for c in clips + photos):
        warn("local files have no Drive id: they work only on this machine. For later sessions put them in the "
             "product's Drive folder and rerun the intake from there")

    # facts: the folder first; the site only for what the folder lacks
    np_, nw_, nline = notes_prices(notes)
    use_notes_price = bool(np_)
    facts = dict(price=f"{np_:.2f}" if use_notes_price else sfacts.get("price"),
                 compare_at=(f"{nw_:.2f}" if nw_ else None) if use_notes_price else sfacts.get("compare_at"),
                 price_source="notes" if use_notes_price else "site" if sfacts.get("price") else None,
                 price_line=nline if use_notes_price else None,
                 colours=notes_colours(notes) or list(sfacts.get("colours", {}))
                 or (sfacts.get("options") or {}).get("Color", []),
                 description=sfacts.get("description", ""), notes=notes[:4000], title=sfacts.get("title") or site_title,
                 url=sfacts.get("url"))
    offer = draft_offer(dict(sfacts, **{k: facts[k] for k in ("price", "compare_at", "price_source", "price_line")}),
                        notes, short, warn)
    if not offer["badge"] and not offer["gift"]:
        warn("no offer found in the notes" + (" or on the site" if sfacts else "") + ": the ads say no % and no gift "
             "(a sale theme such as Black Friday will be refused)")
    dropped = []
    deal = (int(offer["badge"]["big"].rstrip("%")) if offer["badge"] else None, offer["gift"])
    cands = candidates(dict(sfacts, bullets=sfacts.get("bullets") or [], highlights=sfacts.get("highlights") or []),
                       notes, key, pname, deal, products_dir, dropped)
    feats = pick_features(cands)
    dropped += [f"{c['source']}: \"{c['line'][:70]}\" not used: more than {MAX_FEATURES} feature lines (the best "
                f"{MAX_FEATURES} are kept)" for c in cands[MAX_FEATURES:]]
    hook, broll = draft_picks(feats, clips, photos, busy, scores)
    if len(feats) < 3:         # (not a draft: plan pads the videos from the offer / colours / a recap, see make_batch.board)
        warn(f"only {len(feats)} feature line(s) found in the notes: the videos are padded with true notes-derived blocks "
             f"(price / gift, colours, a recap) and run shorter; 3-{MAX_FEATURES} lines (one short line each) make them "
             f"longer. Ads still run: the client need not add anything")
    sc = sfacts.get("scores", {})
    site_imgs = [(f, sc.get(f, 0), count_faces(f, strict=True)) for f in sfacts.get("images", [])[:16]]
    where = sfacts.get("url") or (f"Drive New Products / {folder_name}" if fo else local or "no folder")
    ov = overview(photos, clips, site_imgs, good_frames, os.path.join(cache, "overview.jpg"),
                  f"{pname}  |  {where}  |  {len(photos)} photos, {len(clips)} clips")
    if not photos and not clips and not handle:
        warn("no photos, no clips and no site page: nothing to build ads from yet")

    extra = [folder_name if fo and slugify(folder_name) != slug else "", handle or ""]
    if key in builtin_names() or slug in {slugify(n) for n in builtin_names()}:
        warn(f"the name {pname!r} is also a built-in bag's: this file keeps key {key!r} with source.kind "
             f"{src_kind!r} (plan --pipeline new-product uses this file, never the built-in bag or libracases.com)")
    product = dict(
        key=key, aliases=aliases_for(key, extra, products_dir), name=pname, short=short, end=end, site=handle,
        photos=photos, clips=clips, offer=offer,
        hook_clips=hook, features=[[f["line"], f["tag"], f["picks"]] for f in feats], customer=[], broll=broll,
        reviews=[], facts=facts,
        source=dict(kind=src_kind, drive_folder=fo["id"] if fo else None, folder_name=folder_name or None,
                    files=file_rows(files) if src_kind != "site" else [], site_url=sfacts.get("url"),
                    site_match=how or None, notes_link=link.group(0) if link and not handle else None,
                    local_dir=os.path.abspath(local) if local else None, cache=rel(cache), overview=rel(ov),
                    added=datetime.date.today().isoformat()),
        status="ready")
    problems, vw = validate(product)
    auto = not problems and not draft
    product["status"] = "ready" if auto else "draft"
    product["auto"] = auto                           # ready without a human; a draft is "auto": false
    if draft:
        product["source"]["draft_asked"] = True      # --draft: a re-made file stays draft for its review
    product["source"]["auto_sig"] = content_sig(product)    # untouched since the intake (drafts too: ensure re-makes)
    if not auto:
        problems, vw = validate(product)
    if old.get("tests"):
        product["tests"] = old["tests"]               # ads made from the earlier intake stay on record
    os.makedirs(products_dir, exist_ok=True)
    open(out_file, "w").write(dumps(product) + "\n")
    warnings += [w for w in vw if not w.startswith("status is draft")]

    pr_line = (f"${facts['price']}" + (f" (was ${facts['compare_at']})" if facts.get("compare_at") else "") +
               f" [{facts['price_source']}]") if facts.get("price") else "-"
    kinds = {k: [f"P{i}" for i, p in enumerate(photos) if p.get("kind") == k] for k in KINDS}
    lines = [f"product   {pname}  (key \"{key}\", aliases {', '.join(product['aliases']) or '-'})",
             f"file      {rel(out_file)}  (status {product['status']}{', auto' if auto else ''})",
             f"source    {where}  [{src_kind}{', site: ' + how if how else ''}]  {pr_line}  "
             f"colours: {', '.join(facts['colours']) or '-'}",
             f"offer     {offer['offer_title'] or 'no discount'}  {offer['offer_sub']}  |  close: \"{offer['close']}\""]
    lines += [f"          evidence: {e}" for e in offer["evidence"]]
    nost = [f"P{i}" for i, p in enumerate(photos) if p.get("statics") is False and p["faces"] == 0]
    lines.append(f"photos    {len(photos)}: " + ", ".join(f"{k} {' '.join(v)}" for k, v in kinds.items() if v) +
                 f"  ({sum(bool(p['faces']) for p in photos)} with faces = never used" +
                 (f"; {' '.join(nost)} may show part of a head = videos only, never in statics" if nost else "") + ")")
    lines += [f"clip C{i}   {c['name']}  {c['dur']:.1f}s  {c['w']}x{c['h']}  starts {c['good']}  sheet {c['sheet']}"
              for i, c in enumerate(clips)]
    lines.append("features  (from " + ("notes + site" if sfacts and notes else "site" if sfacts else "the folder's notes")
                 + ")")
    lines += [f"  {i + 1}. [{f['tag']}] \"{f['line']}\"  picks {f['picks']}" for i, f in enumerate(feats)]
    lines += [f"  not used: {x}" for x in dropped[:12]] + ([f"  not used: ... {len(dropped) - 12} more"] if len(dropped) > 12
                                                          else [])
    lines += [f"hook      {hook}", f"broll     {broll}",
              f"look at   {rel(ov) if ov else '-'}  (+ {rel(os.path.join(cache, 'sheets'))}/*.jpg)"]
    lines += [f"PROBLEM   {p}" for p in problems]
    lines.append(f"NEXT: make_batch.py plan --product \"{key}\" (ready, made automatically: look at overview.jpg "
                 f"when you can)" if auto else
                 f"NEXT: fix the problems / features in {rel(out_file)} (only true claims from the notes), set status "
                 f"ready, python3 pipeline/new_product.py check {slug}")
    return dict(file=out_file, key=key, status=product["status"], problems=problems, warnings=warnings,
                summary="\n".join(lines))


def untouched(d):
    """The product file is as its intake wrote it (source.auto_sig = content_sig): a ready "auto" file or an intake
    draft nobody edited, so ensure() re-makes it when the folder changes. A ready file set to "auto": false was reviewed
    by hand. Files from before auto_sig: auto ones, and drafts of a Drive intake, count as untouched."""
    src = (d or {}).get("source") or {}
    if not d or src.get("auto_sig") not in (None, content_sig(d)):
        return False
    if d.get("status") == "draft":
        return bool(src.get("auto_sig") or src.get("kind") == "drive")
    return bool(d.get("auto"))


def ensure(ref, products_dir=PRODUCTS_DIR, cache=CACHE_DIR, refresh=False):
    """The product file for a New Products folder, made or refreshed when needed. ref: a folder name (exact, else a
    unique part), "next" (the newest folder with no ads made yet: no product file, or one without "tests") or "latest"
    (the newest folder). No product file -> intake. Folder unchanged since the intake (file ids + modifiedTime) ->
    reuse. Changed: a file nobody edited since its intake (untouched: auto-ready or an intake draft) -> intake again;
    a hand-edited one -> reuse + a warning naming the new files. refresh=True: always intake again. Cached media may
    be missing (fresh container): make_batch downloads by Drive id. Returns dict(key, file, status, created, changed, problems, warnings, summary); raises ValueError."""
    token = _token()
    fs = _folders(token)
    r = (ref or "").strip()
    if r.lower() == "next":
        fo = next((f for f in fs if not (file_for_folder(f, products_dir)[1] or {}).get("tests")), None)
        if not fo:
            raise ValueError("every folder in New Products already has ads: name one to make more ("
                             + ", ".join(f["name"] for f in fs) + ")")
    elif r.lower() == "latest":
        fo = fs[0]
    else:
        fo = find_folder(fs, r)
    path, d = file_for_folder(fo, products_dir)
    try:
        files = drive_files(token, fo["id"])
    except (urllib.error.URLError, OSError) as e:
        raise ValueError(f"cannot list Drive folder {fo['name']!r}: {e}") from e
    redo, warnings = refresh or d is None, []
    diff = folder_changes(d, files) if d else None
    auto = untouched(d)
    if d and not refresh and diff:
        if auto:
            redo = True
            warnings.append(f"{fo['name']}: the Drive folder changed since the intake ({', '.join(diff[:6])}"
                            f"{' ...' if len(diff) > 6 else ''}): intake redone")
        else:
            warnings.append(f"{fo['name']}: the Drive folder changed since the intake ({', '.join(diff[:6])}"
                            f"{' ...' if len(diff) > 6 else ''}) but {rel(path)} was edited by hand: it is used as it is "
                            f"(re-run python3 pipeline/new_product.py intake \"{fo['name']}\" --force to include them)")
    if d and diff is None and not refresh:
        warnings.append(f"{rel(path)} has no record of the folder's files (made before ensure): used as it is")
    if redo:
        res = intake(folder=fo, name=(d or {}).get("name"), products_dir=products_dir, cache=cache, force=True,
                     draft=bool(((d or {}).get("source") or {}).get("draft_asked")))
        return dict(key=res["key"], file=res["file"], status=res["status"], created=True, changed=bool(diff),
                    problems=res["problems"], warnings=warnings + res["warnings"], summary=res["summary"])
    problems, vw = validate(d)
    tests = d.get("tests") or []
    summary = (f"{d.get('name')}: {rel(path)} reused ({d.get('status')}{', auto' if d.get('auto') else ''}; folder "
               f"{'unchanged' if not diff else 'changed'} since {(d.get('source') or {}).get('added')}"
               f"{'; ads made ' + str(len(tests)) + 'x, last ' + str(tests[-1].get('date')) if tests else ''})")
    return dict(key=d.get("key"), file=path, status=d.get("status"), created=False, changed=bool(diff),
                problems=problems, warnings=warnings + [w for w in vw if not w.startswith("status is draft")],
                summary=summary)


def _product_path(ref, products_dir=PRODUCTS_DIR):
    """Path of a product file: a path, a slug / key, an alias / name (lookup) or a New Products folder name."""
    if ref and os.path.exists(ref):
        return ref
    p = os.path.join(products_dir, slugify(ref or "") + ".json")
    if os.path.exists(p):
        return p
    q = (ref or "").lower().strip()
    names = lambda d: [(d.get("source") or {}).get("folder_name"), d.get("name"), d.get("short"), d.get("key")] + \
        list(d.get("aliases") or [])  # noqa: E731
    rows = product_files_by_folder(products_dir)
    hit = next((f for f, d in rows if q in {str(x).lower().strip() for x in names(d) if x}), None) or \
        next((f for f, d in rows if norm_name(q) and norm_name(q) in {norm_name(str(x)) for x in names(d) if x}), None)
    if not hit:
        raise ValueError(f"no product file for {ref!r} in {rel(products_dir)}")
    return hit


def record_test(ref_or_path, info, products_dir=PRODUCTS_DIR):
    """Append info (dict: date, name, drive_link, statics, videos, projects) to the product file's "tests" (ads made
    from it) and write it back. Returns the file path."""
    path = _product_path(ref_or_path, products_dir)
    d = json.load(open(path))
    d.setdefault("tests", []).append(dict(info, date=info.get("date") or datetime.date.today().isoformat()))
    open(path, "w").write(dumps(d) + "\n")
    return path


def folder_rows(products_dir=PRODUCTS_DIR, token=None):
    """One row per New Products folder, newest first: counts, product file, status (new | draft | ready | tested
    <date>), changed (files added or edited since the intake; None = unknown), tests (number of batches made)."""
    token = token or _token()
    rows = []
    for fo in _folders(token):
        try:
            files = drive_files(token, fo["id"])
        except (urllib.error.URLError, OSError) as e:
            raise ValueError(f"cannot list Drive folder {fo['name']!r}: {e}") from e
        ks = [kind(f["name"], f["mimeType"]) for f in files]
        f, d = file_for_folder(fo, products_dir)
        tests = (d or {}).get("tests") or []
        st = "new" if d is None else f"tested {tests[-1].get('date')}" if tests else d.get("status") or "draft"
        diff = folder_changes(d, files) if d else None
        rows.append(dict(name=fo["name"], id=fo["id"], created=fo["createdTime"][:10], photos=ks.count("photo"),
                         clips=ks.count("clip"), notes=ks.count("note"), other=ks.count(None),
                         slug=slugify(names_for(fo["name"])[0]), product_file=rel(f), status=st,
                         auto=bool((d or {}).get("auto")), changed=bool(diff) if diff is not None else None,
                         changed_files=diff or [], tests=len(tests)))
    return rows


def pending(products_dir=PRODUCTS_DIR):
    """Folder rows (folder_rows) with no ads made yet, or changed since their intake."""
    return [r for r in folder_rows(products_dir) if not r["tests"] or r["changed"]]


# ---------------------------------------------------------------- commands
def cmd_list(a):
    try:
        rows = folder_rows(a.products_dir)
    except ValueError as e:
        if "no product folders" not in str(e):
            sys.exit(str(e))
        rows = []
        print(e, file=sys.stderr)
    print(json.dumps(rows, indent=1, ensure_ascii=False))


def cmd_intake(a):
    try:
        res = intake(folder=a.folder, latest=a.latest, local=a.local, site=a.site, name=a.name,
                     products_dir=a.products_dir, cache=a.cache, use_site=a.use_site, force=a.force, draft=a.draft,
                     max_photos=a.max_photos, max_clips=a.max_clips)
    except ValueError as e:
        sys.exit(str(e))
    print(res["summary"])
    for w in res["warnings"]:
        print(f"WARNING   {w}")


def review_about(n, d, revs=None):
    """reviews.json review n is about this product (its 'product' names the product's name, short name or key)."""
    revs = revs or {r["n"]: r.get("product") or "" for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}
    rp = re.sub(r"\s*\(.*$|\s+-.*$", "", revs.get(n, "")).lower().strip()
    if not rp or rp == "any":
        return False
    names = {(x or "").lower().strip() for x in (d.get("name"), d.get("short"), d.get("key"))} - {""}
    return any(rp in x or x in rp for x in names)


def site_index(x):
    """'S3' / 3 -> 3 (a site image number in overview.jpg); None for S0 (the sale-badge photo) or junk."""
    m = re.fullmatch(r"[sS]?(\d+)", str(x).strip())
    return int(m.group(1)) if m and int(m.group(1)) > 0 else None


def validate(d):
    """(problems, warnings) for a product dict against the schema in pipeline/data/products/README.md."""
    P, W = [], []
    bank = json.load(open(os.path.join(HERE, "data", "clip_bank.json")))
    review_ns = {r["n"]: r.get("product") or "" for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}
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
        if p.get("kind") is not None and p["kind"] not in KINDS:
            P.append(f"photo {i}: kind {p['kind']!r} is not one of {', '.join(KINDS)}")
        if not isinstance(p.get("statics", True), bool):
            P.append(f"photo {i}: 'statics' must be true or false (false: may show part of a head, videos only)")
        elif p.get("statics") and p.get("faces"):
            P.append(f"photo {i} ({p.get('name')}): shows a face, so 'statics' can't be true")
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
        elif p[0] == "photo" and len(p) == 2 and isinstance(p[1], str) and re.fullmatch(r"P\d+", p[1]):
            n = int(p[1][1:])                        # ["photo", "P3"] = photos[3] (the P numbers of overview.jpg)
            if n >= len(photos):
                P.append(f"{where}: {p!r} points at no photo (have {len(photos)})")
            elif photos[n].get("faces") != 0:
                P.append(f"{where}: {p!r} ({photos[n].get('name')}) shows a face or was not face-checked: never picked")
        elif p[0] == "photo":
            if len(p) != 2 or not isinstance(p[1], int) or p[1] < 0:
                P.append(f"{where}: {p!r} must be [\"photo\", N] or [\"photo\", \"P<n>\"]")
            elif not pool:
                P.append(f"{where}: {p!r} but there are no photos and no site page")
        elif len(p) == 3 and isinstance(bank.get(p[0]), dict) and p[1] in bank[p[0]] and p[0] not in ("_help", "voices",
                                                                                                         "winner_raws"):
            if not isinstance(p[2], (int, float)):
                P.append(f"{where}: {p!r} start must be a number")
            if str(p[1]).startswith("ai_") or str(bank[p[0]][p[1]].get("id", "")).startswith("http"):
                P.append(f"{where}: {p!r} is an AI clip: real footage only")
        else:
            P.append(f"{where}: {p!r} is not a clip_bank section/key, a clip or a photo pick")
    feats = d.get("features", [])
    if len(feats) > MAX_FEATURES:
        P.append(f"at most {MAX_FEATURES} features (has {len(feats)})")
    elif len(feats) < 3:                  # thin products are normal: make_batch pads the videos (or leaves them out)
        W.append(f"{len(feats)} feature line(s): videos are padded from the offer / colours / a recap, and run shorter")
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
    hooks = d.get("hooks", [])
    if not isinstance(hooks, list):
        P.append("'hooks' must be a list")
        hooks = []
    for i, h in enumerate(hooks):            # optional opening lines for project mode (pipeline/projects.py)
        h = {"text": h} if isinstance(h, str) else h
        if not (isinstance(h, dict) and isinstance(h.get("text"), str) and h["text"].strip()):
            P.append(f"hook {i + 1}: must be \"line\" or {{\"text\": ..., \"type\": ..., \"labels\": [...]}}")
            continue
        if len(h["text"].split()) > 15 or h["text"].strip()[-1:] not in ".!?":
            P.append(f"hook {i + 1}: must be one short spoken line (15 words at most) ending in . ! or ?")
        if h.get("type") is not None and h["type"] not in HOOK_TYPES:
            P.append(f"hook {i + 1}: type {h['type']!r} is not one of {', '.join(HOOK_TYPES)}")
        labs = h.get("labels") or []
        if not isinstance(labs, list) or any(not isinstance(x, str) or x != x.upper() or not 1 <= len(x.split()) <= 4
                                             for x in labs):
            P.append(f"hook {i + 1}: labels must be a list of 1-4 word UPPERCASE texts")
        if h.get("feature") and h["feature"] not in {f[1] for f in feats if isinstance(f, list) and len(f) == 3}:
            W.append(f"hook {i + 1}: feature {h['feature']!r} is not a feature TAG (its opening shot is picked without it)")
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
    for n in d.get("reviews", []):
        if n in review_ns and not review_about(n, d):
            P.append(f"review {n} is about '{review_ns[n]}', not this product: product files only list reviews of the product "
                     f"itself (store reviews 6-10 are for the built-in bags)")
    sl = d.get("site_lifestyle") or []
    if not isinstance(sl, list) or any(site_index(x) is None for x in sl):
        P.append("'site_lifestyle' must be a list of site image numbers from overview.jpg (S1, S2 ... or 1, 2 ...; never S0)")
    elif sl and not d.get("site"):
        P.append("'site_lifestyle' needs a 'site' page")
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
                said = {str(n) for n, _ in stated_pcts(f.get("notes") or "")}   # client-stated offer
                ok = real is not None and (abs(int(m.group(1)) - real) <= 2 or 0 <= real - int(m.group(1)) < 5.5)
                if m and not ok and m.group(1) not in said:
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
        elif g and GIFT.search(src) and not gift_hits(src):
            P.append(f"offer.gift {g!r}: the site text or notes only say there is no free gift")
        if not g and re.search(r"\bfree\b", o.get("close", "") + o.get("offer_sub", ""), re.I):
            P.append("offer mentions something free but gift is null")
        pm = re.match(r"(\d+)%", (b or {}).get("big", "") if isinstance(b, dict) else "")
        texts = [("name", d.get("name")), ("short", d.get("short")), ("end", d.get("end"))] + \
                [(f"offer.{k}", o.get(k)) for k in ("statics_sub", "close", "offer_title", "offer_sub")] + \
                [(f"feature {i + 1} {'line' if k == 0 else 'tag'}", f[k]) for i, f in enumerate(feats)
                 if isinstance(f, list) and len(f) == 3 for k in (0, 1)] + \
                [(f"hook {i + 1}", x) for i, h in enumerate(hooks) for x in
                 ([h] if isinstance(h, str) else [h.get("text")] + list(h.get("labels") or []) if isinstance(h, dict) else [])]
        for where, t in texts:
            why = unbacked(t if isinstance(t, str) else "", pm.group(1) if pm else None, g)
            if why:
                P.append(f"{where} claims {why} that the offer does not back: {t!r}")
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
    i.add_argument("--site", help="libracases.com product URL or handle: the site fills what the folder lacks (alone: "
                                  "a product from the site only)")
    i.add_argument("--use-site", action="store_true", help="also read libracases.com (the notes' link, else the name) "
                                                           "for what the folder lacks; default: the Drive folder only")
    i.add_argument("--draft", action="store_true", help="keep the file draft even when check finds no problems")
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

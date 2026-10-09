#!/usr/bin/env python3
"""One-line request -> finished statics + videos in the proven house style (the 2026-10-02 test run).

The look is fixed by templates: site packshots + brand_statics layouts for statics; real clips from
pipeline/data/clip_bank.json + voiceover + captions/tags/review cards/offer/end card for videos; winner
videos re-edit the winning RAW (pipeline/remix.py) with a new cold open and a narrated review section.
No AI images or AI video are made here. The only paid step is the voiceover lines (~0.3 credits each),
which Claude generates with Higgsfield between `plan` and `render`.

  1) python3 pipeline/make_batch.py plan --statics 3 --videos 4 --product "Hobo Bag" \
         --theme "black friday" --out /tmp/run
         [--winner-videos 6 [--winners latest | "94-H4,148-H5" | "94,148" | brief.json | all]]
     -> /tmp/run/plan.json, statics.json, <name>.json per video, tts_needed.json (lines to voice, with voice ids)
     Winner videos come first (V01..), one per winner in brief order (cycling, each reuse gets another cold
     open + other reviews); storyboard videos follow. --product omitted: the top winner's product, else Hobo Bag.
     Products: the built-in bags below or pipeline/data/products/<slug>.json (new_product.py); an unknown or
     draft product exits 2. Refuses (exit 2) when the voiceover would cost more than 40 credits (--budget X).
  2) Claude: for each item in tts_needed.json -> Higgsfield generate_audio_batch (model text2speech_v2,
     variant elevenlabs, use_unlim false, voice from the item) -> download the mp3 to /tmp/run/<file>
     (identical lines are listed once; render copies them to the other file names)
  3) python3 pipeline/make_batch.py render --out /tmp/run [--jobs 2] [--only V03]
     (statics, then videos in parallel, + QA sheets and qa/report.json)
  4) Claude looks at /tmp/run/qa/*.jpg; re-render (--only) or drop anything broken
  5) python3 pipeline/make_batch.py upload --out /tmp/run --name "Black Friday test" [--include-flagged]
     -> Drive Outputs/<date> – <name>/{Statics,Videos} + "run report.txt"; prints the folder link and the ad list
     (videos QA flagged ok=false are skipped unless --include-flagged)

Optional --lines lines.json overrides any spoken line or headline (keys as in plan.json "text").
"""
import argparse
import concurrent.futures as cf
import datetime
import glob
import itertools
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

BRAND_VOICE = {"voice_type": "element", "voice_id": "241459b6-b4e8-4a2a-9868-da8bcdcd0558"}
NARRATOR = {"voice_type": "preset", "voice_id": "64cf4f1a-61c8-5938-9aea-83d12b2e1d13"}
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
MAX_CREDITS = 40

# ---------------------------------------------------------------- themes
# Strings for the built-in bags (50% off + free matching pouch wallet). Product files get offer-neutral
# versions from offer_texts(); "lead" opens their spoken close.
THEMES = {
    "default": dict(
        label="", hooks=["Here's what makes the {short} different.", "Stop carrying a bag that swallows your keys.",
                         "This might be the most practical bag you'll see today."],
        hero="Meet the {short}.", bold=["SELLING", "FAST."], offer_title="50% OFF", offer_sub="+ FREE MATCHING WALLET",
        close="It's fifty percent off right now, with a free matching pouch wallet. Tap the link below.",
        sub="Final clearance: 50% off + free shipping while stock lasts.", cta="Shop now · 50% off", lead=""),
    "black friday": dict(
        label="BLACK FRIDAY", hooks=["Black Friday came early.", "This is the Black Friday deal you've been waiting for.",
                                     "Black Friday: the bag everyone asks about is half price."],
        hero="Black Friday deal.", bold=["BLACK", "FRIDAY."], offer_title="BLACK FRIDAY 50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="For Black Friday it's fifty percent off, plus a free matching pouch wallet. Tap the link below before it's gone.",
        sub="Our biggest sale of the year: 50% off + free wallet.", cta="Get the Black Friday deal",
        lead="This is our Black Friday deal."),
    "cyber monday": dict(
        label="CYBER MONDAY", hooks=["Cyber Monday: last call on our biggest sale."],
        hero="Cyber Monday deal.", bold=["CYBER", "MONDAY."], offer_title="CYBER MONDAY 50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="For Cyber Monday it's still fifty percent off, plus a free matching pouch wallet. Tap the link below.",
        sub="Last call: 50% off + free wallet.", cta="Shop the deal", lead="Cyber Monday is your last call."),
    "christmas": dict(
        label="GIFT IDEA", hooks=["Still looking for the perfect Christmas gift?", "Most gifts end up in a drawer. Not this one."],
        hero="The gift she'll use every day.", bold=["GIFT", "SORTED."], offer_title="50% OFF",
        offer_sub="+ FREE WALLET FOR HER",
        close="It arrives with a free matching pouch wallet, and it's fifty percent off right now. Order today so it arrives in time.",
        sub="50% off + a free matching wallet in the box.", cta="Shop the gift", lead="It makes the perfect Christmas gift."),
    "mothers day": dict(
        label="FOR MUM", hooks=["Still trying to figure out what to get your mum?"],
        hero="For the mum who carries everything.", bold=["FOR", "MUM."], offer_title="50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="It arrives with a free matching pouch wallet, and it's fifty percent off right now. Tap the link below.",
        sub="50% off + a free matching wallet.", cta="Shop for mum", lead="It makes the perfect gift for mum."),
    "travel": dict(
        label="TRAVEL DAY", hooks=["Travel day is where a bottomless bag really hurts."],
        hero="Made for travel day.", bold=["PACK", "SMARTER."], offer_title="50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="It's fifty percent off right now, with a free matching pouch wallet. Tap the link below.",
        sub="Hidden pocket, gold side zips, room for everything.", cta="Shop now · 50% off", lead=""),
}
THEME_KEYS = {"black friday": "black friday", "bfcm": "black friday", "cyber": "cyber monday", "christmas": "christmas",
              "xmas": "christmas", "gift": "christmas", "holiday": "christmas", "mother": "mothers day", "mum": "mothers day",
              "mom": "mothers day", "travel": "travel", "travelling": "travel", "traveling": "travel", "vacation": "travel"}
THEME_WORDS = {"black friday": ["black", "friday"], "cyber monday": ["cyber", "monday"], "christmas": ["gift", "christmas"],
               "mothers day": ["mum", "gift"], "travel": ["travel"], "default": []}


def pick_theme(text):
    """Whole-word match ("mum" never matches "premium"); plural / possessive allowed ("mother's day")."""
    t = (text or "").lower()
    for k, v in THEME_KEYS.items():
        if re.search(r"\b" + re.escape(k).replace(r"\ ", r"[\s-]*") + r"(?:s|'s)?\b", t):
            return v
    return "default"


# ---------------------------------------------------------------- products
# Spoken feature lines + on-screen tag + picks: [clip_bank section, key, start] | ["clip", i, start] | ["photo", n].
PRODUCTS = {
    "hobo bag": dict(
        name="Hobo Bag", short="Hobo Bag", site="Hobo Bag", end="The Luxury Hobo Bag",
        hook_clips=[["hobo_bag", "back_pocket_4k", 1.0], ["hobo_3piece_set", "brown_room_outside", 0.5],
                    ["hobo_bag", "cafe_chair_4k", 1.0]],
        features=[
            ("First, a hidden pocket on the back. It sits flat against you, so your passport and cards stay right there.",
             "HIDDEN BACK POCKET", [["hobo_bag", "back_pocket_4k", 1.0], ["hobo_bag", "back_pocket_4k", 6.0]]),
            ("Two gold side zips, one on each side, for your keys and phone.", "GOLD SIDE ZIPS",
             [["hobo_bag", "side_zip_keys_4k", 2.0], ["hobo_bag", "side_zip_keys_4k", 8.0]]),
            ("Inside, divided compartments, so nothing sinks to the bottom.", "SMART COMPARTMENTS",
             [["hobo_bag", "testi_black", 63.3], ["hobo_bag", "black_detail", 9.5]]),
            ("Two straps, so you can wear it on the shoulder, as a handbag, or crossbody.", "3 WAYS TO WEAR",
             [["hobo_bag", "testi_black", 54.0], ["hobo_3piece_set", "brown_room_outside", 21.0]]),
            ("Soft, water-resistant leather that looks expensive and only gets better with time.", "SOFT LEATHER",
             [["hobo_bag", "details_macro_4k", 0.5], ["hobo_bag", "metal_details_4k", 4.0]]),
        ],
        customer=[["hobo_bag", "testi_black", 15.0, 31.5], ["hobo_bag", "testi_black", 33.1, 41.7],
                  ["hobo_bag", "testi_black", 41.6, 52.5]],
        broll=[["hobo_bag", "walking_113H3", 3.0], ["hobo_bag", "cafe_chair_4k", 1.0], ["hobo_bag", "metal_details_4k", 12.0],
               ["hobo_3piece_set", "brown_room_outside", 42.0], ["hobo_bag", "details_macro_4k", 4.0]],
        reviews=[7, 8, 9, 10, 6, 2, 12]),
    "hobo 2.0": dict(
        name="Hobo 2.0", short="Hobo 2.0", site="Hobo 2.0", end="Hobo 2.0",
        hook_clips=[["hobo_2_0", "ai_brown_pushin_1080p", 0.0], ["hobo_2_0", "ai_black_dollyin_1080p", 0.6]],
        features=[
            ("Lockable zippers, so nobody can open it in a crowd.", "LOCKABLE ZIPPERS",
             [["hobo_2_0", "lockable_zippers", 28.1], ["hobo_2_0", "lockable_zippers", 31.6]]),
            ("An RFID lining that blocks card scanners.", "RFID LINING", [["hobo_2_0", "ai_black_dollyin_1080p", 0.6]]),
            ("A cut-resistant strap.", "CUT-RESISTANT STRAP", [["hobo_2_0", "beige_360", 12.0]]),
            ("And a table strap that loops around your chair, so your bag stays right where you left it.",
             "TABLE SECURITY STRAP", [["hobo_2_0", "table_strap", 18.9], ["hobo_2_0", "table_strap", 0.0]]),
            ("Hidden pockets and smart compartments for everything else.", "HIDDEN POCKETS",
             [["hobo_2_0", "table_strap", 12.6], ["hobo_2_0", "beige_360", 6.85]]),
        ],
        customer=[], broll=[["hobo_2_0", "beige_360", 0.0], ["hobo_2_0", "table_strap", 28.4],
                            ["hobo_2_0", "lockable_zippers", 35.1]],
        reviews=[11, 7, 8, 6]),
    "3-piece set": dict(
        name="Hobo Bag 3-Piece Set", short="3-Piece Set", site="3-piece set", end="The Hobo 3-Piece Set",
        hook_clips=[["hobo_3piece_set", "brown_room_outside", 0.5], ["hobo_3piece_set", "black_door", 0.0]],
        features=[
            ("Every set comes with three pieces: the hobo bag, a crossbody, and a matching pouch.", "3 BAGS, 1 PRICE",
             [["hobo_3piece_set", "brown_room_outside", 0.5], ["hobo_3piece_set", "black_hanging", 1.0]]),
            ("The hobo for every day. The crossbody for when you want to go light.", "HOBO + CROSSBODY",
             [["hobo_3piece_set", "brown_room_outside", 21.0], ["hobo_3piece_set", "brown_room_outside", 63.0]]),
            ("And the pouch keeps your cards and cash in one place.", "MATCHING POUCH",
             [["hobo_bag", "black_gift", 28.6]]),
        ],
        customer=[], broll=[["hobo_3piece_set", "brown_room_outside", 31.0], ["hobo_3piece_set", "brown_room_outside", 73.0],
                            ["hobo_3piece_set", "brown_room_outside", 105.0], ["hobo_3piece_set", "black_door", 0.0]],
        reviews=[7, 8, 9, 6]),
    "vintage": dict(
        name="Vintage Bag", short="Vintage Bag", site="vintage", end="The Vintage Bag",
        hook_clips=[["vintage_bag", "clasp_brown", 0.0], ["vintage_bag", "tryon_brown", 12.4]],
        features=[
            ("A clasp that snaps shut with one hand.", "ONE-HAND CLASP", [["vintage_bag", "clasp_brown", 0.0]]),
            ("Open it up and there's room for your phone, wallet and keys, all in their own spot.", "ROOM FOR EVERYTHING",
             [["vintage_bag", "open_inside_brown", 6.6], ["vintage_bag", "open_inside_brown", 9.3]]),
            ("An adjustable strap, so you can wear it as a handbag or crossbody.", "ADJUSTABLE STRAP",
             [["vintage_bag", "strap_brown", 0.5], ["vintage_bag", "details_brown", 3.5]]),
        ],
        customer=[["vintage_bag", "becky_testimony", 5.8, 14.45], ["vintage_bag", "becky_testimony", 15.4, 30.4],
                  ["vintage_bag", "becky_testimony", 39.6, 48.6]],
        broll=[["vintage_bag", "compare_black_brown", 0.0], ["vintage_bag", "flatlay", 1.0], ["vintage_bag", "tryon_brown", 9.6]],
        reviews=[6, 7, 9]),
    "slouchy": dict(
        name="Slouchy Soft 3-Piece Set", short="Slouchy Set", site="slouchy", end="The Slouchy Soft Set",
        hook_clips=[["slouchy_set", "brown_lifestyle", 8.0], ["slouchy_set", "coffee_run", 6.5]],
        features=[
            ("Soft, slouchy leather that moulds to you.", "SOFT SLOUCHY LEATHER", [["slouchy_set", "brown_lifestyle", 11.3]]),
            ("Three pieces in every set: the bag, a crossbody, and a pouch.", "3-PIECE SET",
             [["slouchy_set", "flatlay", 1.0], ["slouchy_set", "all3_crossbody", 4.0]]),
            ("Big enough for everything, light enough for all day.", "ROOMY + LIGHT", [["slouchy_set", "coffee_run", 11.8]]),
        ],
        customer=[], broll=[["slouchy_set", "all3_crossbody", 9.0], ["slouchy_set", "brown_lifestyle", 14.5],
                            ["slouchy_set", "coffee_run", 1.0]],
        reviews=[7, 8, 6]),
}
# keyword -> built-in product, most specific first (whole words: "set" never matches "sunset");
# "Slouchy Vintage Bag" is the weekly brief's name for the Vintage Bag group (33-H5, C9_V2)
PRODUCT_KEYS = {"slouchy vintage": "vintage", "slouchy": "slouchy", "2.0": "hobo 2.0", "hobo2": "hobo 2.0", "hobo 2": "hobo 2.0", "6-layer": "hobo 2.0",
                "3-piece": "3-piece set", "3 piece": "3-piece set", "three piece": "3-piece set", "set": "3-piece set",
                "vintage": "vintage", "hobo": "hobo bag"}
DOTS = {"brown": [120, 66, 36], "black": [25, 25, 25], "blue": [40, 52, 90], "grey": [110, 110, 112], "gray": [110, 110, 112],
        "burgundy": [96, 28, 44], "red": [170, 26, 36], "purple": [96, 28, 60], "chocolate": [70, 40, 30],
        "ginger": [176, 96, 40], "beige": [210, 190, 160], "apricot": [230, 170, 130], "white": [240, 236, 228],
        "pink": [222, 160, 160], "green": [70, 100, 70], "wine": [110, 30, 45]}


def products_dir(a=None):
    import new_product
    return getattr(a, "products_dir", None) or os.environ.get("LC_PRODUCTS_DIR") or new_product.PRODUCTS_DIR


def product_files(pdir):
    """{key: product file dict} from pipeline/data/products/*.json (schema: pipeline/data/products/README.md)."""
    import new_product
    out = new_product.load_all(pdir)
    for f in glob.glob(os.path.join(pdir, "*.json")):
        try:
            k = json.load(open(f)).get("key")
        except (ValueError, OSError):
            continue
        if k in out:
            out[k]["_path"] = f
    return out


def nn(s):
    return re.sub(r"\s+", " ", re.sub(r"^the\s+", "", (s or "").lower().strip()))


def has_word(text, w):
    return bool(w) and re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?:s|'s)?(?![a-z0-9])", text) is not None


def pick_product(text, files=None):
    """Product key for a request text, or None. Exact name first (built-in or product file), then the longest
    product-file key/alias inside the text, then the built-in keyword map (most specific first)."""
    t, files = nn(text), files or {}
    if not t:
        return None
    for k, p in PRODUCTS.items():
        if t in {nn(x) for x in (k, p["name"], p["short"], p["site"], p["end"])}:
            return k
    names = {k: [k, d.get("name"), d.get("short"), d.get("end"), d.get("site"), re.sub(r"[^a-z0-9]+", "-", k)]
             + list(d.get("aliases") or []) for k, d in files.items()}
    for k, ns in names.items():
        if t in {nn(x) for x in ns if x}:
            return k
    best = max(((len(nn(x)), k) for k, ns in names.items() for x in ns if x and has_word(t, nn(x))), default=None)
    if best:
        return best[1]
    return next((v for kw, v in PRODUCT_KEYS.items() if has_word(t, kw)), None)


def product(pk, files):
    """Built-in product or a product file, in one shape (offer None = built-in 50% + free matching pouch wallet)."""
    if pk in PRODUCTS:
        return dict(PRODUCTS[pk], key=pk, offer=None, photos=[], clips=[], source="built-in", status="ready")
    d = files[pk]
    return dict(key=pk, name=d.get("short") or d["name"], short=d.get("short") or d["name"], site=d.get("site"),
                end=d.get("end") or d["name"], hook_clips=d.get("hook_clips") or [],
                features=[tuple(f) for f in d.get("features") or []], customer=d.get("customer") or [],
                broll=d.get("broll") or [], reviews=d.get("reviews") or [], offer=d.get("offer") or {},
                photos=d.get("photos") or [], clips=d.get("clips") or [], source=d.get("_path") or "product file",
                status=d.get("status"))


def known_products(files):
    return [p["name"] for p in PRODUCTS.values()] + [d.get("name") or k for k, d in files.items()]


def offer_texts(pr, th):
    """Every offer/claim string a batch uses. Built-in bags: THEMES wording (50% + free matching pouch wallet).
    Product files: only what their offer block has; never a % or a free gift it does not list."""
    if pr.get("offer") is None:
        return dict(badge={"top": "NOW", "big": "50%", "bottom": "OFF"}, promo_badge={"top": "SALE", "big": "50%", "bottom": "OFF"},
                    gift_tail=" and a free matching pouch wallet.", promo_sub="+ FREE matching pouch wallet",
                    colours_sub="Every colour comes with a free matching pouch wallet.",
                    colours_line="Every colour comes with a free matching pouch wallet.", bold_sub=th["sub"], cta=th["cta"],
                    offer_title=th["offer_title"], offer_sub=th["offer_sub"], offer_word="50", close=th["close"],
                    hooks=th["hooks"], hero=th["hero"],
                    keywords=["50%", "free", "wallet", "hidden", "pocket", "leather", "black", "friday", "gift"],
                    compare_left=["Keys lost at the bottom", "One big empty space", "Wallet sold separately"])
    o = pr["offer"]
    badge = o.get("badge") or None
    m = re.match(r"\s*(\d+)\s*%", (badge or {}).get("big", ""))
    pct = m.group(1) if m else None
    gift = re.sub(r"^(?:a|an)\s+", "", (o.get("gift") or "").strip(), flags=re.I) or None
    deal = bool(pct or gift)

    def honest(s):   # a theme line may only claim what the product file offers
        if re.search(r"half price|half off", s, re.I) and pct != "50":
            return False
        if re.search(r"\d+\s*%|percent", s, re.I) and not pct:
            return False
        if re.search(r"\bfree\b|wallet", s, re.I) and not gift:
            return False
        return deal or not re.search(r"\bdeal\b|\bsale\b", s, re.I)

    d = THEMES["default"]
    hooks = [h for h in th["hooks"] if honest(h)]
    hooks += d["hooks"] if len(hooks) < 2 and hooks != d["hooks"] else []
    cta = th["cta"]
    if "%" in cta:
        cta = f"Shop now · {pct}% off" if pct else "Shop now"
    elif not honest(cta):
        cta = "Shop now"
    title = o.get("offer_title") or ""
    if pct and th["label"] and "50%" in th["offer_title"] and th["offer_title"] != "50% OFF":
        title = th["offer_title"].replace("50%", f"{pct}%")          # "BLACK FRIDAY 40% OFF"
    lead = th.get("lead", "") if honest(th.get("lead", "")) else ""
    close = o.get("close") or "Tap the link below."
    statics_sub = o.get("statics_sub") or ""
    gift_words = [w for w in re.findall(r"[a-z]+", (gift or "").lower()) if w in ("free", "pouch", "wallet", "purse", "gift")]
    return dict(badge=badge, promo_badge=dict(badge, top="SALE") if badge else None,
                gift_tail=f" and a {gift}." if gift else ".",
                promo_sub=("+ " + re.sub(r"^free\b", "FREE", gift, flags=re.I)) if gift else statics_sub,
                colours_sub=f"Every colour comes with a {gift}." if gift else statics_sub,
                colours_line=f"Every colour comes with a {gift}." if gift else "Which one is yours?",
                bold_sub=statics_sub, cta=cta, offer_title=title, offer_sub=o.get("offer_sub") or "",
                offer_word=pct or ("free" if gift else None), close=(lead + " " if lead else "") + close, hooks=hooks,
                hero=th["hero"] if honest(th["hero"]) else d["hero"],
                keywords=([f"{pct}%"] if pct else []) + gift_words + ["leather"],
                compare_left=["Keys lost at the bottom", "One big empty space",
                              "Wallet sold separately" if gift and re.search("wallet|pouch|purse", gift, re.I) else "Nothing has its own place"])


def bank():
    return json.load(open(os.path.join(HERE, "data", "clip_bank.json")))


def clip(b, sec, key):
    return b[sec][key]["id"]


def reviews_by_n():
    return {r["n"]: r for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}


SPOKEN = {  # short verbatim pieces of each review, as read by the narrator
    2: ("One customer", "the quality is amazing, it fits all my essentials"),
    6: ("Mercy", "the best bag for travel and every day use"),
    7: ("Carol", "best bag I have ever bought"),
    8: ("Beverly", "looks expensive, but price was so nice"),
    9: ("Felicia", "got this bag for my daughter for Christmas and she adores it"),
    10: ("Margie", "it holds many things"),
    11: ("Sarah", "the lockable zippers and RFID lining are genuinely incredible"),
    12: ("Jenny", "it's spacious, lightweight, and super functional with lots of pockets"),
}


def short_quote(text, n_words=14):
    first = re.split(r"(?<=[.!])\s", text.strip())[0]
    w = first.split()
    return " ".join(w[:n_words]).rstrip(",;") if len(w) > n_words else first


def spoken(n, revs):
    r = revs[n]
    return SPOKEN.get(n, (r["name"].split()[0].rstrip("."), short_quote(r["text"]).rstrip(".!")))


def tok(w):
    return re.sub(r"[^\w%']", "", w.lower())


def cards_ok(text, cards, starts):
    """remix.py finds each card's word in order, each after the previous one: check it lands on the right name."""
    toks, k = [tok(w) for w in text.split()], 0
    for c, want in zip(cards, starts):
        i = next((i for i in range(k, len(toks)) if toks[i].startswith(c["word"])), None)
        if i != want:
            return False
        k = i + 1
    return True


def review_script(ns, intros, j, revs):
    """Narrated review section: '<intro> Carol: best bag I have ever bought. Beverly: ...' + card words.
    The intro rotates with j; one that would steal a card's word (e.g. '...the only one.' before 'One customer') is skipped."""
    parts = [spoken(n, revs) for n in ns]
    intros = intros or ["Here's what customers are saying."]
    cards = [dict(n=n, word=tok(who.split()[0])) for n, (who, _) in zip(ns, parts)]
    first = None
    for t in range(len(intros)):
        intro = intros[(j + t) % len(intros)]
        text, starts = intro, []
        for who, q in parts:
            starts.append(len(text.split()))
            text += f" {who}: {q}."
        first = first or (text, intro)
        if cards_ok(text, cards, starts):
            return text, cards, intro
    return first[0], cards, first[1]


# ---------------------------------------------------------------- naming
def slug(text):
    """CamelCase, letters/digits only: 'Hobo 2.0' -> 'Hobo20', 'black friday' -> 'BlackFriday'."""
    return "".join(w.capitalize() if w.islower() else w for w in re.findall(r"[A-Za-z0-9]+", text))


def ad_prefix(product, theme_key, rev=1):
    """LC_<YYMMDD>_<Product>_<Theme>[_v2]: see docs/NAMING.md. The ad id (S01_hero / V01_features) follows it."""
    d = datetime.date.today().strftime("%y%m%d")
    return f"LC_{d}_{slug(product)}_{slug(theme_key) if theme_key != 'default' else 'Evergreen'}" + (f"_v{rev}" if rev > 1 else "")


WPS = 2.7   # spoken words per second (brand voice and narrator)


def est_seconds(spec, texts, rw=None):
    """Rough ad length before any voiceover exists: words / WPS for voiced parts, real ranges for RAW and clips."""
    if "raw" in spec:
        e = next((x for x in (rw or {}).values() if x.get("id") == spec["raw"]), {})
        body = (spec.get("end") or e.get("dur") or 0) - (spec.get("start") or 0) - sum(b - a for a, b in spec.get("cut") or [])
        co = spec.get("cold_open")
        rv = spec.get("reviews")
        return round(body + (co[1] - co[0] if co else 0) + (len(rv["text"].split()) / WPS + 0.4 if rv else 0), 1)
    t = 0.0
    for blk in spec["blocks"]:
        t += len(texts.get(blk["vo"], "").split()) / WPS + 0.25 if "vo" in blk else blk["range"][1] - blk["range"][0]
    return round(t, 1)


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_") or "file"


# ---------------------------------------------------------------- plan
def plan(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    theme_key = pick_theme(a.theme)
    th = dict(THEMES[theme_key])
    pdir = products_dir(a)
    files = product_files(pdir)
    warnings = []
    W = max(a.winner_videos, 0)
    sel = None
    if W:
        import winners
        sel = winners.select(a.winners)
        if sel["note"]:
            warnings.append(f"winners: {sel['note']}; using all {len(sel['winners'])} bank winners in clip_bank order")
        if sel["brief"] and sel["brief"].get("stale"):
            warnings.append(f"the newest brief is {sel['brief'].get('age_days')} days old (stale): winners may be out of date")
    if a.product:
        pk = pick_product(a.product, files)
        if pk is None:
            print(f"unknown product '{a.product}'. Known: {', '.join(known_products(files))}. For a new product: "
                  f"python3 pipeline/new_product.py intake \"{a.product}\" (its Drive New Products folder) or "
                  f"--site <libracases.com link>, then new_product.py check <slug>", file=sys.stderr)
            sys.exit(2)
    else:
        pk = pick_product(sel["winners"][0]["product"], files) if sel and sel["winners"] else None
        pk = pk or "hobo bag"
    pr = product(pk, files)
    if pr["status"] != "ready" and not a.allow_draft:
        print(f"product file {pr['source']} has status '{pr['status']}': review its features and offer, set "
              f"\"status\": \"ready\", run python3 pipeline/new_product.py check {pr['source']} (or plan with --allow-draft)",
              file=sys.stderr)
        sys.exit(2)
    over = json.load(open(a.lines)) if a.lines else {}
    fill = lambda s: s.format(short=pr["short"], name=pr["name"])  # noqa: E731
    prefix = ad_prefix(pr["name"], theme_key, a.rev)
    tx = offer_texts(pr, th)
    rel = lambda f: os.path.relpath(f, out) if os.path.abspath(f).startswith(out + os.sep) else os.path.abspath(f)  # noqa: E731
    revs = reviews_by_n()
    b = bank()

    # ---------- site photos + facts, product-file photos and clips
    colour_imgs, packs, clean_site, other_site, facts = [], [], [], [], {}
    need = a.statics > 0 or a.videos > 0
    if need and pr["site"]:
        site = os.path.join(out, "site")
        r = subprocess.run([sys.executable, os.path.join(HERE, "site_assets.py"), pr["site"], "--out", site],
                           capture_output=True, text=True)
        print(r.stdout.strip(), r.stderr.strip(), file=sys.stderr)
        ff = glob.glob(os.path.join(site, "*_facts.json"))
        if r.returncode or not ff:
            if pr["source"] == "built-in":
                sys.exit(f"site_assets.py failed for {pr['site']!r}")
            warnings.append(f"site photos for {pr['site']!r} could not be read: using the product file's photos only")
        else:
            facts = json.load(open(ff[0]))
            sc = facts["scores"]
            colour_imgs = [(n, f) for n, f in facts["colours"].items() if sc.get(f, 0) >= 0.6]
            clean_site = [f for f in facts["clean_images"] if f not in dict(colour_imgs).values()]
            packs = [f for _, f in colour_imgs] or clean_site
            other_site = [f for f in facts["images"] if sc.get(f, 0) < 0.6]
    token = []

    def fetch(item, dest):
        """Product-file photo/clip: the cached copy ('path') if it is there, else a Drive download by 'id'."""
        src = os.path.join(ROOT, item["path"]) if item.get("path") else None
        if src and os.path.exists(src):
            return src
        if not item.get("id"):
            warnings.append(f"{item.get('name')}: no cached copy and no Drive id (intake ran in another session?)")
            return None
        try:
            from drive_upload import access_token, download
            token[:] = token or [access_token()]
            return download(token[0], item["id"], src or dest)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            warnings.append(f"{item.get('name')}: Drive download failed ({e})")
            return None

    file_photos, file_packs, file_life = [], [], []
    for i, p in enumerate(pr["photos"] if need else []):
        if p.get("faces") != 0:          # faces (or not checked): never in ads
            continue
        dest = os.path.join(out, "photos", f"{i:02d}_{safe_name(p.get('name') or 'photo.jpg')}")
        f = fetch(p, dest)
        if f:
            if not os.path.exists(dest):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy(f, dest)
            file_photos.append(dest)
            (file_packs if (p.get("clean") or 0) >= 0.8 else file_life).append(dest)
    clips = []
    for i, c in enumerate(pr["clips"] if a.videos > 0 else []):
        clips.append(fetch(c, os.path.join(out, "clips", f"{i:02d}_{safe_name(c.get('name', 'clip.mp4'))}")))
    packs = packs + file_packs
    pool = list(dict.fromkeys(packs + clean_site + file_photos))
    life_cache = []

    def lifestyle():
        """Photos for lifestyle statics: faceless product-file photos + site photos with no face found."""
        if not life_cache:
            import new_product
            site_ok = [f for f in other_site if new_product.count_faces(f) == 0]
            life_cache.append(file_life + site_ok)
        return life_cache[0]

    def pick(p, w=1.0):
        """[src, start, weight(, extra)] for a pick, or None when it points at nothing."""
        if not p:
            return None
        if p[0] == "photo":
            return [rel(pool[p[1] % len(pool)]), 0, w, {"zoom": [1.0, 1.06]}] if pool else None
        if p[0] == "clip":
            c = clips[p[1]] if isinstance(p[1], int) and 0 <= p[1] < len(clips) else None
            return [c, p[2], w] if c else None
        try:
            return [clip(b, p[0], p[1]), p[2], w]
        except (KeyError, IndexError, TypeError):
            warnings.append(f"pick {p!r} is not in clip_bank.json")
            return None

    def picks(ps, fallback=True, w=1.0):
        got = [x for x in (pick(p, w) for p in ps) if x]
        if got or not fallback:
            return got
        for alt in pr["broll"] + pr["hook_clips"] + [["photo", 0]]:
            x = pick(alt)
            if x:
                return [x]
        return []

    # ---------- statics
    feats = [f[1].title() for f in pr["features"]] or [pr["short"]]
    feats = (feats * 3)[:3]
    clean_mode = len(packs) >= 2
    seq = (["hero", "promo", "bold", "review", "colours", "compare", "review", "promo", "hero", "bold"] if clean_mode else
           ["lifestyle", "bold", "hero", "lifestyle", "compare", "review", "lifestyle", "bold", "hero", "lifestyle"])
    if not clean_mode and a.statics:
        warnings.append(f"only {len(packs)} clean packshot(s): statics use lifestyle photos and framed photo cards")
    statics, cards, n_life = [], set(), 0
    for i in range(a.statics):
        lay = seq[i % len(seq)]
        if lay == "review" and not pr["reviews"]:
            lay = "lifestyle" if lifestyle() else "compare"
        if lay == "colours" and len(colour_imgs) < 2 and len(packs) < 2:
            lay = "lifestyle" if lifestyle() else "bold"
        if lay == "lifestyle" and not lifestyle():
            lay = "hero"
        if lay == "lifestyle":
            photo = lifestyle()[n_life % len(lifestyle())]
            n_life += 1
        elif packs:
            photo = packs[i % len(packs)]
        elif lifestyle():
            photo = lifestyle()[i % len(lifestyle())]
            cards.add(rel(photo))
        else:
            warnings.append(f"static {i + 1}: no usable photo (no clean packshot, no faceless photo): skipped")
            continue
        photo = rel(photo)
        name = f"{prefix}_S{len(statics) + 1:02d}_{lay}"
        if lay == "hero":
            s = dict(layout="hero", photo=photo, headline=over.get("hero", fill(tx["hero"])),
                     sub=f"{feats[0].capitalize()}, {feats[1].lower()}{tx['gift_tail']}", badge=tx["badge"], cta=tx["cta"])
        elif lay == "promo":
            s = dict(layout="promo", photo=photo, headline=(th["label"].title() + ": " if th["label"] else "") + f"The {pr['short']}",
                     sub=tx["promo_sub"], features=feats, badge=tx["promo_badge"], cta=tx["cta"])
        elif lay == "bold":
            dots = [DOTS.get(n.lower().split()[0], [150, 150, 150]) for n, _ in colour_imgs][:7]
            s = dict(layout="bold", photo=photo, lines=over.get("bold", th["bold"]), accent_lines=[1], sub=tx["bold_sub"],
                     cta=tx["cta"], dots=dots)
        elif lay == "review":
            n = pr["reviews"][(i // 6) % len(pr["reviews"])]
            s = dict(layout="review", review_n=n, photo=photo, cta=tx["cta"])
        elif lay == "colours":
            ph = [dict(src=rel(f), name=n) for n, f in colour_imgs][:6] or [dict(src=rel(f), name="") for f in packs[:4]]
            s = dict(layout="colours", photos=ph, headline=over.get("colours", "Pick your colour."), sub=tx["colours_sub"], cta=tx["cta"])
        elif lay == "lifestyle":
            heads = [over.get("hero", fill(tx["hero"])), f"The {pr['short']}.", f"{feats[0]}. {feats[1]}."]
            s = dict(layout="lifestyle", photo=photo, headline=heads[(n_life - 1) % len(heads)], sub=tx["bold_sub"] or None,
                     cta=tx["cta"])
        else:
            s = dict(layout="compare", photo=photo, headline=f"Your everyday bag vs {pr['short']}",
                     left_title="Most bags", left=tx["compare_left"],
                     right_title=pr["short"], right=[f.capitalize() for f in [x[1].lower() for x in pr["features"]][:3]],
                     cta=tx["cta"])
        s["name"] = name
        statics.append(s)

    # ---------- videos
    tts, videos, specs = [], [], {}

    def line(vid, key, text, voice):
        f = f"{vid}_{key}.mp3"
        tts.append(dict(file=f, text=text, **voice))
        return f

    # winner remixes first: V01..VW
    rw, used_sets, uses = {}, set(), {}
    if W:
        import winners
        rw = winners.raws()
    for i in range(W):
        w = sel["winners"][i % len(sel["winners"])]
        e = rw[w["key"]]
        ed = e["edit"]
        j = uses.get(w["key"], 0) + a.seed - 1
        uses[w["key"]] = uses.get(w["key"], 0) + 1
        vid = f"V{i + 1:02d}"
        wpk = pick_product(e.get("product") or "", files) or pk
        wp = product(wpk, files) if wpk != pk else pr
        wtx = offer_texts(wp, th)
        cos = ed.get("cold_opens") or [{"range": None, "label": "", "line": ""}]
        co = cos[j % len(cos)]
        spec = dict(raw=e["id"], start=ed.get("start") or 0.0, end=ed.get("end"), cut=ed.get("cut") or [],
                    insert_at=ed.get("insert_at"), offer_word=ed.get("offer_word"), offer_after=ed.get("offer_after"),
                    burned_captions=bool(ed.get("burned_captions")), labels=ed.get("labels") or [],
                    end_title=ed.get("end_title") or wp["end"],
                    offer_title=ed.get("offer_title", wtx["offer_title"]), offer_sub=ed.get("offer_sub", wtx["offer_sub"]),
                    keywords=list(dict.fromkeys(wtx["keywords"] + THEME_WORDS[theme_key])))
        if co.get("range"):
            spec["cold_open"] = co["range"]
        if co.get("label"):
            spec["hook_label"] = co["label"]
        rl = [n for n in wp["reviews"] if n in revs]
        ns, intro = (), None
        if rl and ed.get("insert_at") is not None:
            base = est_seconds(spec, {}, rw)           # RAW body + cold open, before the review section
            cnt = min(max(ed.get("min_reviews") or 2, 2), len(rl))
            while True:                                 # short RAWs (113-H2) get more reviews until ~40 s
                s0 = (j * cnt) % len(rl)
                order = rl[s0:] + rl[:s0]         # rotate by j; never the same set twice in one plan when avoidable
                cands = [tuple(order[(t + q) % len(rl)] for q in range(cnt)) for t in range(len(rl))]
                cands += list(itertools.combinations(order, cnt))
                ns = next((c for c in cands if frozenset(c) not in used_sets), cands[0])
                text, rcards, intro = review_script(ns, ed.get("review_intro"), j, revs)
                if cnt >= len(rl) or base + len(text.split()) / WPS + 0.4 >= 40:
                    break
                cnt += 1
            used_sets.add(frozenset(ns))
            cand, seen = [], set()
            for p in wp["broll"] + [x for f in wp["features"] for x in f[2]] + wp["hook_clips"]:
                x = pick(p) if wp is pr else ([clip(b, p[0], p[1]), p[2]] if p and p[0] in b else None)
                if x and not str(x[0]).startswith("http") and not str(x[0]).lower().endswith((".jpg", ".png")):  # real footage only
                    cand.append([x[0], x[1]])
            firsts, rest = [], []
            for c in cand:                    # one shot per clip first, then second moments of the same clips
                (rest if c[0] in seen else firsts).append(c)
                seen.add(c[0])
            cand = firsts + rest
            n_br = max(3, min(len(cand), math.ceil((len(text.split()) / WPS + 0.4) / 3.5)))
            rot = (j * 2) % max(len(cand), 1)
            broll = [cand[(rot + q) % len(cand)] for q in range(n_br)] if cand else []
            if broll:
                spec["reviews"] = dict(vo=line(vid, "rev", text, NARRATOR), text=text, cards=rcards, broll=broll)
            else:
                ns = ()
        if not ns:
            spec["insert_at"] = None
            warnings.append(f"{vid}: {wp['name']} has no reviews/B-roll to narrate: remix without a review section")
        name = f"{ad_prefix(wp['name'], theme_key, a.rev)}_{vid}_remix{slug(e.get('concept') or w['key']).lower()}"
        specs[name] = spec
        videos.append(dict(name=name, id=vid, format="remix", engine="remix", hook=co.get("line") or "",
                           hook_label=co.get("label") or "",
                           winner=dict(key=w["key"], ad=e.get("ad"), brief_name=w.get("name"), roas=w.get("roas"),
                                       action=w.get("action"), product=wp["name"], cold_open=co.get("range"),
                                       reviews=list(ns), intro=intro)))

    # storyboard videos: V(W+1)..
    formats = ["features", "reviews", "colours", "features", "reviews", "colours"]
    fs = pr["features"]
    rich = bool(pr["reviews"] or pr["customer"])
    for v in range(a.videos):
        vid = f"V{W + v + 1:02d}"
        fmt = formats[v % len(formats)]
        if fmt == "colours" and len(colour_imgs) < 3:
            fmt = "features"
        if fmt == "reviews" and not pr["reviews"]:
            fmt = "features"
        hooks = tx["hooks"]
        hook = over.get(f"{vid}_hook") or fill(hooks[v % len(hooks)])
        if fmt == "colours":
            hook = over.get(f"{vid}_hook") or ("Be honest. Which colour are you?" if theme_key == "default"
                                                else fill(hooks[0]) + " Which colour are you?")
        hc = pr["hook_clips"][v % len(pr["hook_clips"])] if pr["hook_clips"] else None
        blocks = [dict(vo=line(vid, "hook", hook, BRAND_VOICE), broll=picks([hc] if hc else []))]
        ov = [dict(type="label", text=th["label"] or {"features": "LOOK CLOSER", "reviews": "REAL REVIEWS",
                                                        "colours": "WHICH ONE?"}[fmt], block=0, at=0.1, dur=1.8)]
        k0 = (v * 2) % len(fs) if fs else 0
        nfeat = (3 if fmt == "features" else 2) if rich else min(len(fs), 5)
        chosen = [fs[(k0 + j) % len(fs)] for j in range(nfeat)] if fs else []

        def add_features():
            for j, (txt, tag, ps) in enumerate(chosen):
                blocks.append(dict(vo=line(vid, f"feat{j}", txt, BRAND_VOICE), broll=picks(ps)))
                ov.append(dict(type="tag", text=tag, block=len(blocks) - 1, at=0.15, dur=2.6))

        def add_reviews(count):
            if not pr["reviews"]:
                return
            ns = [pr["reviews"][(v + j) % len(pr["reviews"])] for j in range(count)]
            for j, n in enumerate(ns):
                who, q = spoken(n, revs)
                text = ("Here's what customers say. " if j == 0 else "") + f"{who}: {q}."
                br = pr["broll"][(v + j) % len(pr["broll"])] if pr["broll"] else None
                blocks.append(dict(vo=line(vid, f"rev{j}", text, NARRATOR), broll=picks([br] if br else [])))
                ov.append(dict(type="review", n=n, block=len(blocks) - 1, at=0.1, until_block_end=True))

        def add_customer():
            if pr["customer"]:
                s_, k_, a_, e_ = pr["customer"][v % len(pr["customer"])]
                blocks.append(dict(clip=clip(b, s_, k_), range=[a_, e_]))
                ov.append(dict(type="label", text="REAL CUSTOMER", block=len(blocks) - 1, at=0.3, dur=2.0))

        def add_colours():
            sw = []
            for n, f in colour_imgs[:6]:
                fr = os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")
                sw.append((n, fr))
            names = [n for n, _ in sw]
            ctext = ", ".join(names[:-1]) + ", or " + names[-1] + ". " + tx["colours_line"]
            blocks.append(dict(vo=line(vid, "colours", ctext, BRAND_VOICE),
                               broll=[[os.path.relpath(f, out), 0, 1.0, {"zoom": [1.0, 1.06]}] for _, f in sw]))
            ov.append(dict(type="tag", text=" · ".join(n.upper() for n in names[:4]), block=len(blocks) - 1, at=0.1, dur=3.0))

        if fmt == "features":
            add_features(); add_customer(); add_reviews(2)  # noqa: E702
            if not rich and len(colour_imgs) >= 3:
                add_colours()
        elif fmt == "reviews":
            add_reviews(3); add_customer(); add_features()  # noqa: E702
        else:
            add_colours(); add_customer(); add_reviews(2); add_features()  # noqa: E702
        close = over.get(f"{vid}_close", tx["close"])
        cb = pr["broll"][v % len(pr["broll"])] if pr["broll"] else None
        cl = ([[rel(packs[v % len(packs)]), 0, 1.0, {"zoom": [1.0, 1.06]}]] if packs else []) + picks([cb] if cb else [], fallback=False, w=1.2)
        blocks.append(dict(vo=line(vid, "close", close, BRAND_VOICE), broll=cl or picks([])))
        if any(not blk.get("broll") for blk in blocks if "vo" in blk):
            sys.exit(f"{pr['name']}: no footage or photo to show under the voiceover (product has no clips, no clean "
                     f"photos and no site page). Add clips/photos to its Drive folder and re-run the intake.")
        offer = (dict(block=len(blocks) - 1, word=tx["offer_word"], title=tx["offer_title"], sub=tx["offer_sub"])
                 if tx["offer_title"] and tx["offer_word"] else None)
        spec = dict(blocks=blocks, overlays=ov, end_title=pr["end"], offer=offer,
                    keywords=list(dict.fromkeys(tx["keywords"] + THEME_WORDS[theme_key])))
        name = f"{prefix}_{vid}_{fmt}"
        specs[name] = spec
        videos.append(dict(name=name, id=vid, format=fmt, engine="storyboard", hook=hook))

    # ---------- voiceover: one line per (text, voice); budget
    uniq, dupes = {}, {}
    for t in tts:
        k = (t["text"], t["voice_type"], t["voice_id"])
        if k in uniq:
            dupes[t["file"]] = uniq[k]["file"]
        else:
            uniq[k] = t
    tts_u = list(uniq.values())
    texts = {t["file"]: t["text"] for t in tts}
    for v in videos:
        v["est_seconds"] = est_seconds(specs[v["name"]], texts, rw)
        lo, hi = (35, 110) if v["engine"] == "remix" else (35, 95)
        if not lo <= v["est_seconds"] <= hi:
            warnings.append(f"{v['id']} will run about {v['est_seconds']:.0f} s (QA wants {lo}-{hi} s)" +
                            (": the product file needs more features/clips, or add lines with --lines" if v["engine"] != "remix" else ""))
    est = round(0.35 * len(tts_u), 1)
    limit = a.budget if a.budget is not None else MAX_CREDITS
    summary = dict(statics=len(statics), videos=len(videos), tts_lines=len(tts_u), est_credits=est, budget=limit,
                   theme=theme_key, product=pr["name"], product_source=pr["source"])
    if est > limit:
        print(json.dumps(summary, indent=1), file=sys.stderr)
        print(f"voiceover would cost ~{est} credits, over the {limit}-credit budget: make fewer videos, or pass "
              f"--budget {math.ceil(est)} if the request names a bigger budget", file=sys.stderr)
        sys.exit(2)

    json.dump(dict(ads=statics, card_photos=sorted(cards)), open(os.path.join(out, "statics.json"), "w"), indent=1)
    for name, spec in specs.items():
        json.dump(spec, open(os.path.join(out, name + ".json"), "w"), indent=1)
    json.dump(tts_u, open(os.path.join(out, "tts_needed.json"), "w"), indent=1)
    brief = sel["brief"] if sel else None
    p = dict(prefix=prefix, created=datetime.date.today().isoformat(), request=a.request or "", product=pr["name"],
             product_key=pk, product_source=pr["source"], theme=theme_key, statics=[s["name"] for s in statics],
             videos=videos, tts_lines=len(tts_u), tts_dupes=dupes, est_credits=est, budget=limit,
             colour_images=dict(colour_imgs), packshots=packs, brief=brief,
             winners_source=sel["source"] if sel else None, winners_note=sel["note"] if sel else None,
             winners_used=[dict(key=w["key"], name=w.get("name"), roas=w.get("roas"), action=w.get("action"))
                           for w in (sel["winners"][:W] if sel else [])],
             unmatched_winners=sel["unmatched"] if sel else [], warnings=warnings)
    json.dump(p, open(os.path.join(out, "plan.json"), "w"), indent=1)
    print(json.dumps(dict(plan=os.path.join(out, "plan.json"), **summary, tts_needed=os.path.join(out, "tts_needed.json"),
                          tts_duplicates=len(dupes), brief=brief, winners_source=p["winners_source"],
                          winner_videos=[f"{v['name']} ({v['winner']['brief_name']}, " + (f"cold open: {v['hook_label']}" if
                                         v["winner"]["cold_open"] else f"no cold open, label {v['hook_label']}") + ")"
                                         for v in videos if v["engine"] == "remix"],
                          unmatched_winners=[f"{u['name']} (ROAS {u.get('roas')}): {u.get('why')}" for u in p["unmatched_winners"]],
                          warnings=warnings), indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- render
def swatches(out, colour_imgs):
    from PIL import Image
    import brand_statics as bs
    os.makedirs(os.path.join(out, "sw"), exist_ok=True)
    for n, f in colour_imgs.items():
        fr = os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")
        if not os.path.exists(fr):
            c = Image.new("RGB", (1080, 1920), (246, 241, 234))
            bs.place_packshot(c, Image.open(f).convert("RGB"), (60, 380, 1020, 1500))
            c.save(fr, quality=95)


def contact_sheet(f, out_jpg):
    L = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                             capture_output=True, text=True).stdout or 0)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", f, "-vf",
                    f"fps=24/{max(L, 1):.2f},scale=150:-1,tile=12x2", "-frames:v", "1", "-y", out_jpg])
    return L


def prefetch(out, videos):
    """Download every Drive source once, before parallel renders (two renders must not fetch the same file at once),
    and transcribe clips that keep their own sound."""
    import recut
    from remix import loc, words
    std, seen = recut.LOCAL_MAX, set()
    for v in videos:
        s = json.load(open(os.path.join(out, v["name"] + ".json")))
        if v.get("engine") == "remix":
            srcs = [(s["raw"], True)] + [(x[0], False) for x in (s.get("reviews") or {}).get("broll", [])]
        else:
            srcs = [(x[0], False) for blk in s["blocks"] for x in blk.get("broll", [])] + \
                   [(blk["clip"], False) for blk in s["blocks"] if "clip" in blk]
        for src, big in srcs:
            if src in seen or not DRIVE_ID.match(str(src)) or os.path.exists(os.path.join(out, src)):
                continue
            seen.add(src)
            print(f"prefetch {src}", file=sys.stderr, flush=True)
            recut.LOCAL_MAX = max(std, 600 * 2**20) if big else std
            loc(out, src) if big else recut.source(src)
        for blk in s.get("blocks", []):
            if "clip" in blk and not blk.get("mute"):
                words(loc(out, blk["clip"]))
    recut.LOCAL_MAX = std


def render_one(out, v):
    eng = v.get("engine", "storyboard")
    f = os.path.join(out, "videos", v["name"] + ".mp4")
    script = os.path.join(HERE, "remix.py" if eng == "remix" else "storyboard.py")
    tmp = os.path.join(out, "_tmp", v["id"])           # longform/recut leave their temp folders: one per video, removed after
    os.makedirs(tmp, exist_ok=True)
    r = subprocess.run([sys.executable, script, os.path.join(out, v["name"] + ".json"), "--out", f], capture_output=True, text=True,
                       env=dict(os.environ, TMPDIR=tmp))
    shutil.rmtree(tmp, ignore_errors=True)
    open(os.path.join(out, "qa", v["id"] + ".log"), "w").write(r.stdout + r.stderr)
    ok = r.returncode == 0 and os.path.exists(f)
    L = contact_sheet(f, os.path.join(out, "qa", v["id"] + ".jpg")) if ok else 0
    problems = [] if ok else ["render failed (see qa/%s.log)" % v["id"]]
    lo, hi = (35, 110) if eng == "remix" else (35, 95)
    if ok and not lo <= L <= hi:
        problems.append(f"length {L:.0f}s (want {lo}-{hi}s)")
    miss = r.stderr.count("anchor not found")
    if miss:
        problems.append(f"{miss} overlay anchor(s) not found (see qa/{v['id']}.log)")
    return dict(name=v["name"], id=v["id"], engine=eng, format=v.get("format"), seconds=round(L, 1), ok=ok and not problems,
                problems=problems)


def render(a):
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    only = (a.only or "").upper()
    vids = [] if only.startswith("S") else [v for v in p["videos"] if not only or v["id"].startswith(only)]
    for dup, src in (p.get("tts_dupes") or {}).items():       # identical lines were voiced once
        if not os.path.exists(os.path.join(out, dup)) and os.path.exists(os.path.join(out, src)):
            shutil.copy(os.path.join(out, src), os.path.join(out, dup))
    want = [t["file"] for t in json.load(open(os.path.join(out, "tts_needed.json")))] + list(p.get("tts_dupes") or {})
    if only:
        want = [f for f in want if any(f.startswith(v["id"] + "_") for v in vids)]
    missing = [f for f in want if not os.path.exists(os.path.join(out, f))]
    if missing:
        sys.exit(f"voiceover files missing (generate them first): {missing}")
    for d in ("statics", "videos", "qa"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    swatches(out, p["colour_images"])
    if not only or only.startswith("S"):
        subprocess.run([sys.executable, os.path.join(HERE, "brand_statics.py"), os.path.join(out, "statics.json"),
                        "--outdir", os.path.join(out, "statics")], check=True)
    if vids:
        prefetch(out, vids)
    rp = os.path.join(out, "qa", "report.json")
    old = {r["name"]: r for r in json.load(open(rp))} if only and os.path.exists(rp) else {}
    report = {}
    with cf.ThreadPoolExecutor(max(1, a.jobs)) as ex:
        for r in ex.map(lambda v: render_one(out, v), vids):
            report[r["name"]] = r
            print(json.dumps(r), flush=True)
    order = [v["name"] for v in p["videos"]]
    merged = {**old, **report}
    json.dump(sorted(merged.values(), key=lambda r: order.index(r["name"]) if r["name"] in order else 999),
              open(rp, "w"), indent=1)
    # statics grid for a quick look
    from PIL import Image
    ims = [Image.open(x) for x in sorted(glob.glob(os.path.join(out, "statics", "*.png")))]
    if ims:
        for im in ims:
            im.thumbnail((270, 338))
        cols = min(6, len(ims))
        g = Image.new("RGB", (270 * cols, 338 * ((len(ims) + cols - 1) // cols)), "white")
        for k, im in enumerate(ims):
            g.paste(im, ((k % cols) * 270, (k // cols) * 338))
        g.save(os.path.join(out, "qa", "statics.jpg"), quality=88)
    print("QA: look at", os.path.join(out, "qa"), "(statics.jpg + one contact sheet per video) before uploading")


# ---------------------------------------------------------------- upload
def run_report(p, report, uploaded, skipped, name):
    L = [f"Libra Cases ads: {name}", f"Request: {p.get('request') or '-'}",
         f"Product: {p['product']} · Theme: {p['theme']} · voiceover lines: {p.get('tts_lines')} (~{p.get('est_credits')} credits)"]
    br = p.get("brief")
    if p.get("winners_source"):
        src = {"brief": f"weekly brief '{(br or {}).get('name')}' ({(br or {}).get('age_days')} days old"
                        + (", STALE: no newer brief in Research Briefs)" if (br or {}).get("stale") else ")"),
               "codes": "the ads named in the request", "all": "all bank winners",
               "fallback": f"all bank winners ({p.get('winners_note')})"}.get(p["winners_source"], p["winners_source"])
        L.append(f"Winners from: {src}")
    if p.get("unmatched_winners"):
        L.append("Winners not remixed yet (no RAW edit in the clip bank; run pipeline/winner_prep.py):")
        L += [f"  - {u['name']} (ROAS {u.get('roas')}, {u.get('action')}): {u.get('why')}" for u in p["unmatched_winners"]]
    st = [n for n, k in uploaded if k == "static"]
    L.append(f"\nStatics ({len(st)}):")
    L += [f"  {n}.png  static 1080x1350, layout {n.rsplit('_', 1)[-1]}" for n in st]
    vs = {v["name"]: v for v in p["videos"]}
    vu = [n for n, k in uploaded if k == "video"]
    L.append(f"\nVideos ({len(vu)}):")
    for n in vu:
        v, r = vs.get(n, {}), report.get(n, {})
        secs = f"{r.get('seconds', 0):.0f} s" if r else "length ?"
        if v.get("engine") == "remix":
            w = v["winner"]
            hook = f'cold open "{v.get("hook_label")}": "{v.get("hook")}"' if w.get("cold_open") else f'label "{v.get("hook_label")}" (no cold open)'
            L.append(f"  {n}.mp4  video {secs}, remix of {w.get('brief_name') or w.get('ad')} (ROAS {w.get('roas')}), {hook}, "
                     f"{len(w.get('reviews') or [])} reviews")
        else:
            L.append(f"  {n}.mp4  video {secs}, {v.get('format', '?')}, hook: \"{v.get('hook', '')}\"")
    if skipped:
        L.append("\nNot uploaded (QA flagged; a human should look):")
        L += [f"  {s['name']}: {'; '.join(s['problems'])}" for s in skipped]
    if p.get("warnings"):
        L.append("\nNotes:")
        L += [f"  - {w}" for w in p["warnings"]]
    return "\n".join(L) + "\n"


def upload(a):
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    rp = os.path.join(out, "qa", "report.json")
    report = {r["name"]: r for r in json.load(open(rp))} if os.path.exists(rp) else {}
    up = [sys.executable, os.path.join(HERE, "drive_upload.py")]
    cfg = json.load(open(os.path.join(HERE, "config.json")))
    name = f"{datetime.date.today().isoformat()} – {a.name or p.get('request') or p['product']}"
    run = lambda *x: subprocess.run(up + list(x), capture_output=True, text=True, check=True).stdout.strip()  # noqa: E731
    folder = run("mkdir", name, "--parent", cfg["drive"]["outputs_folder"]).splitlines()[-1]
    st = run("mkdir", "Statics", "--parent", folder).splitlines()[-1]
    vd = run("mkdir", "Videos", "--parent", folder).splitlines()[-1]
    uploaded, skipped, existed = [], [], []

    def send(f, dest, kind):
        r = json.loads(run("upload", f, "--folder", dest, "--skip-existing").splitlines()[-1])
        n = os.path.splitext(os.path.basename(f))[0]
        uploaded.append((n, kind))
        if r.get("skipped"):
            existed.append(n)

    for f in sorted(glob.glob(os.path.join(out, "statics", "*.png"))):
        send(f, st, "static")
    for f in sorted(glob.glob(os.path.join(out, "videos", "*.mp4"))):
        n = os.path.splitext(os.path.basename(f))[0]
        r = report.get(n)
        if r and not r["ok"] and not a.include_flagged:
            skipped.append(dict(name=n, problems=r["problems"]))
            print(f"skipped (QA flagged): {n}: {'; '.join(r['problems'])}", file=sys.stderr)
            continue
        send(f, vd, "video")
    txt = os.path.join(out, "run report.txt")
    open(txt, "w").write(run_report(p, report, uploaded, skipped, name))
    run("upload", txt, "--folder", folder, "--skip-existing")
    print(json.dumps(dict(folder=f"https://drive.google.com/drive/folders/{folder}", name=name, files=len(uploaded),
                          uploaded=[n for n, _ in uploaded], already_there=existed, skipped=skipped, report=txt),
                     indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--statics", type=int, default=0)
    pl.add_argument("--videos", type=int, default=0, help="storyboard (new-angle) videos")
    pl.add_argument("--winner-videos", type=int, default=0, help="winner remixes (remix.py), numbered first")
    pl.add_argument("--winners", default="latest", help="latest (newest brief) | all | brief.json | '94-H4,148-H5' | '94,148'")
    pl.add_argument("--product", help="built-in bag or a pipeline/data/products file (default: top winner's, else Hobo Bag)")
    pl.add_argument("--products-dir", help="product files folder (default pipeline/data/products, or $LC_PRODUCTS_DIR)")
    pl.add_argument("--allow-draft", action="store_true", help="build from a product file still marked draft")
    pl.add_argument("--theme", default="")
    pl.add_argument("--request", default="", help="the user's message, for the folder name and report")
    pl.add_argument("--lines", help="json with overrides: hero, bold, colours, V01_hook, V01_close ...")
    pl.add_argument("--seed", type=int, default=1, help="variation: shifts winner cold opens/reviews and nothing else")
    pl.add_argument("--rev", type=int, default=1, help="revision of an earlier batch with the same product+theme+date: adds _v2, _v3")
    pl.add_argument("--budget", type=float, help=f"credits the request allows for voiceover (default {MAX_CREDITS})")
    pl.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    r.add_argument("--only", help="V03 (one video), V (all videos) or S (statics only)")
    r.add_argument("--jobs", type=int, default=2, help="videos rendered in parallel")
    u = sub.add_parser("upload")
    u.add_argument("--out", required=True)
    u.add_argument("--name", default="")
    u.add_argument("--include-flagged", action="store_true", help="also upload videos QA marked ok=false")
    a = ap.parse_args()
    {"plan": plan, "render": render, "upload": upload}[a.cmd](a)


if __name__ == "__main__":
    main()

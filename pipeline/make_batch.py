#!/usr/bin/env python3
"""One-line request -> finished statics + videos in the proven house style (the 2026-10-02 test run).

The look is fixed by templates: site packshots + brand_statics layouts for statics; real clips from
pipeline/data/clip_bank.json + voiceover + captions/tags/review cards/offer/end card for videos; winner
videos re-edit the winning RAW (pipeline/remix.py) with a new cold open and a narrated review section.
No AI images or AI video are made here. The only paid step is the voiceover lines (~0.3 credits each),
which Claude generates with Higgsfield between `plan` and `render`.

Videos are delivered as PROJECTS, the client's agency format ('ACH - MAX - 94 - H4' = project 94, hook 4): every
planned video is one body (story, features, reviews, offer, end card) made in --hooks versions H1-H4 (default 4) that
differ only in the first 2-5 s: the spoken opening line, the opening shot and the hook label; a winner remix gets
another cold open per version. pipeline/projects.py makes the versions (hook lines: pipeline/data/hooks.json). Ids
P01H1 .. P01H4, names LC_<date>_<Product>_<Theme>_P01_H1_<angle>. --hooks 1 = single videos V01, V02 ... as before.

  1) python3 pipeline/make_batch.py plan --statics 3 --videos 4 --product "Hobo Bag" \
         --theme "black friday" --out /tmp/run [--hooks 4]
         [--winner-videos 6 [--winners latest | "94-H4,148-H5" | "94,148" | brief.json | all]]
     -> /tmp/run/plan.json (videos: one entry per version; projects: P01.. with their hooks), statics.json, one spec
        <name>.json per version, tts_needed.json (lines to voice, with voice ids; the H2-H4 hook lines included)
     Winner videos come first (P01..), one project per winner in brief order: a project holds up to --hooks of its
     winner's cold opens, so a winner gets a 2nd project only when its RAW has --hooks more (else the extra projects
     are left out with a warning: they would repeat its openings; --hooks 1: cycling, each reuse gets another cold open
     + other reviews); storyboard videos follow. --product omitted: the top winner's product, else Hobo Bag.
     Winner openings that already went out in a committed batch (pipeline/recipes/daily) are named in a warning.
     Products: the built-in bags below or pipeline/data/products/<slug>.json (new_product.py); an unknown or
     draft product exits 2. Refuses (exit 2) when the voiceover, hook lines included, would cost more than 40
     credits (--budget X).
  2) Claude: for each item in tts_needed.json -> Higgsfield generate_audio_batch (model text2speech_v2,
     variant elevenlabs, use_unlim false, voice from the item) -> download the mp3 to /tmp/run/<file>
     (identical lines are listed once; render copies them to the other file names; the versions of a project share
     their body lines, so only the hook lines are new)
  3) python3 pipeline/make_batch.py render --out /tmp/run [--jobs 2] [--only P03 | P03H2 | V | S]
     (statics, then videos in parallel, + QA: qa/statics.jpg, one contact sheet per version qa/P01H1.jpg ..., one
     sheet per project qa/P01.jpg (its versions side by side, the body once, body match < 10 = same body), and
     qa/report.json)
  4) Claude looks at /tmp/run/qa/*.jpg; re-render (--only) or drop anything broken
  5) python3 pipeline/make_batch.py upload --out /tmp/run --name "Black Friday test" [--only S|V|P03|P03H2] [--include-flagged]
     -> Drive Outputs/<date> – <name>/{Statics, Videos/<P01 – angle>/ (one folder per project)} + "run report <HHMM>.txt"
     (one block per project: each version's hook type, label, line and length); prints the folder link and the ad list
     (only the files plan.json lists; hard QA failures stay out: render failed, file missing, a face in a static, a
     video under 25 s;
     length / anchor flags are uploaded and listed in the report; ads not rendered yet are listed as still being made)
  6) python3 pipeline/make_batch.py specs --out /tmp/run --dest pipeline/recipes/daily/<date>/<name>   (JSON to commit)
A redo of a whole project: the same plan command with --seed <N+1> --rev 2 --only P02 (voices, renders and uploads only
P02's versions; with --hooks 1: --only V02). A redo of one version on the same body: the same plan command (same
--seed) with --hook-seed <N+1> --rev 2 --only P02H3. --only V02 in project mode means P02.

Optional --lines lines.json overrides headlines and spoken lines: hero, bold, colours, V03_hook / V03_close (video id;
P03_hook / P03_close the same: the H1 line and the close every version shares) or B01_hook / B01_close (storyboard 1,
whatever its number after the winner videos); unused keys are warned about.
Offers come from libracases.com at plan time (each product's own %, a gift only when the site says so); names move to
the first _vN that is not in Drive yet.
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
MIN_SECONDS = 25   # a storyboard shorter than this is never made (35-95 s is the QA range; 25-35 s is uploaded, flagged)

# ---------------------------------------------------------------- themes
# Theme lines are templates, filled per product by offer_vars(): {P} "60%", {off_sp} "sixty percent off", {price_sp}
# "half price" (50%) or "sixty percent off", {gift} "free matching pouch wallet", {gift_sp} "a free matching pouch
# wallet", {gift_w} "free wallet", {GIFT_W} "WALLET", {card} the offer-card sub, {feats} the product's first 3 tags.
# A [...] part drops out when a value in it is empty; a line with an empty value outside [...] is skipped (a list:
# the first one that fills). So a bag without a gift never mentions one, and the % is always the product's own.
THEMES = {
    "default": dict(
        label="", hooks=["Here's what makes the {short} different.", "Stop carrying a bag that swallows your keys.",
                         "This might be the most practical bag you'll see today."],
        hero="Meet the {short}.", bold=["SELLING", "FAST."], offer_title="{P} OFF", offer_sub="[{card}]",
        close=["It's {off_sp} right now[, with {gift_sp}]. Tap the link below.", "[It comes with {gift_sp}. ]Tap the link below."],
        sub="Final clearance: {P} off + free shipping while stock lasts.", cta=["Shop now · {P} off", "Shop now"], lead=""),
    "black friday": dict(
        label="BLACK FRIDAY", hooks=["Black Friday came early.", "This is the Black Friday deal you've been waiting for.",
                                     "Black Friday: the bag everyone asks about is {price_sp}."],
        hero="Black Friday deal.", bold=["BLACK", "FRIDAY."], offer_title="BLACK FRIDAY {P} OFF", offer_sub="[{card}]",
        close="For Black Friday it's {off_sp}[, plus {gift_sp}]. Tap the link below before it's gone.",
        sub="Our biggest sale of the year: {P} off[ + {gift_w}].", cta="Get the Black Friday deal",
        lead="This is our Black Friday deal."),
    "cyber monday": dict(
        label="CYBER MONDAY", hooks=["Cyber Monday: last call on our biggest sale."],
        hero="Cyber Monday deal.", bold=["CYBER", "MONDAY."], offer_title="CYBER MONDAY {P} OFF", offer_sub="[{card}]",
        close="For Cyber Monday it's still {off_sp}[, plus {gift_sp}]. Tap the link below.",
        sub="Last call: {P} off[ + {gift_w}].", cta="Shop the deal", lead="Cyber Monday is your last call."),
    "cyber week": dict(
        label="CYBER WEEK", hooks=["Cyber Week: our biggest sale is still on."],
        hero="Cyber Week deal.", bold=["CYBER", "WEEK."], offer_title="CYBER WEEK {P} OFF", offer_sub="[{card}]",
        close="For Cyber Week it's {off_sp}[, plus {gift_sp}]. Tap the link below.",
        sub="Cyber Week: {P} off[ + {gift_w}].", cta="Shop the deal", lead="This is our Cyber Week deal."),
    "christmas": dict(
        label="GIFT IDEA", hooks=["Still looking for the perfect Christmas gift?", "Most gifts end up in a drawer. Not this one."],
        hero="The gift she'll use every day.", bold=["GIFT", "SORTED."], offer_title="{P} OFF",
        offer_sub="[+ FREE {GIFT_W} FOR HER]",
        close=["[It arrives with {gift_sp}, and ]it's {off_sp} right now. Tap the link below.",
               "[It arrives with {gift_sp}. ]Tap the link below."],
        sub="{P} off[ + {gift_sp} in the box].", cta="Shop the gift", lead="It makes the perfect Christmas gift."),
    "gift": dict(   # a gift with no Christmas word (birthday, Valentine's, Father's Day ...): no Christmas lines, no "her"
        label="GIFT IDEA", hooks=["Looking for a gift that actually gets used?", "Most gifts end up in a drawer. Not this one."],
        hero="The gift that gets used every day.", bold=["GIFT", "SORTED."], offer_title="{P} OFF",
        offer_sub="[+ FREE {GIFT_W}]",
        close=["[It arrives with {gift_sp}, and ]it's {off_sp} right now. Tap the link below.",
               "[It arrives with {gift_sp}. ]Tap the link below."],
        sub="{P} off[ + {gift_sp} in the box].", cta="Shop the gift", lead="It makes a gift that gets used every day."),
    "mothers day": dict(
        label="FOR MUM", hooks=["Still trying to figure out what to get your mum?", "Most gifts end up in a drawer. Not this one.",
                                 "Here's a gift your mum will actually use every day."],
        hero="For the mum who carries everything.", bold=["FOR", "MUM."], offer_title="{P} OFF", offer_sub="[{card}]",
        close=["[It arrives with {gift_sp}, and ]it's {off_sp} right now. Tap the link below.",
               "[It arrives with {gift_sp}. ]Tap the link below."],
        sub="{P} off[ + {gift_sp}].", cta="Shop for mum", lead="It makes the perfect gift for mum."),
    "travel": dict(
        label="TRAVEL DAY", hooks=["Travel day is where a bottomless bag really hurts.",
                                   "Heading away soon? Here's the bag to take.", "Packing for a trip? Start with the bag."],
        hero="Made for travel day.", bold=["PACK", "SMARTER."], offer_title="{P} OFF", offer_sub="[{card}]",
        close=["It's {off_sp} right now[, with {gift_sp}]. Tap the link below.", "[It comes with {gift_sp}. ]Tap the link below."],
        sub="{feats}.", cta=["Shop now · {P} off", "Shop now"], lead=""),
}
SALE_THEMES = ("black friday", "cyber monday", "cyber week")
# request word -> theme, the specific occasion first: "mother's day gift" is Mother's Day, "holiday travel" is travel;
# a plain "gift" (birthday, Valentine's, Father's Day) is the neutral gift theme, "gift" + a Christmas word is Christmas.
# Spaces also match a hyphen or nothing ("CyberMonday", "X-mas").
THEME_KEYS = [("black friday", "black friday"), ("bfcm", "black friday"), ("cyber week", "cyber week"),
              ("cyber monday", "cyber monday"), ("cyber", "cyber monday"), ("mother", "mothers day"),
              ("mum", "mothers day"), ("mom", "mothers day"), ("father", "gift"), ("dad", "gift"), ("valentine", "gift"),
              ("travel", "travel"), ("travelling", "travel"), ("traveling", "travel"), ("vacation", "travel"),
              ("christmas", "christmas"), ("xmas", "christmas"), ("x mas", "christmas"), ("holiday", "christmas"), ("gift", "gift")]
THEME_WORDS = {"black friday": ["black", "friday"], "cyber monday": ["cyber", "monday"], "cyber week": ["cyber", "week"],
               "christmas": ["gift", "christmas"], "gift": ["gift"], "mothers day": ["mum", "gift"], "travel": ["travel"],
               "default": []}
NAMED = ("black friday", "cyber monday", "cyber week", "christmas", "mothers day", "travel")   # own name part: BlackFriday
FILLER = {"sale", "sales", "deal", "deals", "style", "styled", "theme", "themed", "ad", "ads", "the", "a", "an", "for", "her",
          "him", "our", "with", "and", "of", "idea", "ideas", "angle", "s", "batch", "video", "videos", "static", "statics"}


def pick_theme(text):
    """Whole-word match ("mum" never matches "premium"); plural / possessive allowed ("mother's day")."""
    t = re.sub(r"[\u2018\u2019`\u00b4]", "'", (text or "").lower())
    for k, v in THEME_KEYS:
        if re.search(r"\b" + re.escape(k).replace(r"\ ", r"[\s-]*") + r"(?:s|'s)?\b", t):
            return v
    return "default"


def theme_name(text, key):
    """Theme part of ad names: BlackFriday / Christmas / ...; a theme that is not built in keeps its own words
    ("valentines day" -> ValentinesDay, "birthday gift" -> BirthdayGift); no theme -> Evergreen."""
    if key in NAMED:
        return slug(key)
    t = re.sub(r"'s\b", "s", re.sub(r"[\u2018\u2019`\u00b4]", "'", (text or "").lower()))     # "Valentine's" -> valentines
    t = re.sub(r"\bvalentines?(?:[\s-]*day)?\b", "valentines day", t)                    # one name: ValentinesDay
    words = [w for w in re.findall(r"[a-z0-9]+", t) if w not in FILLER]
    return slug(" ".join(words[:3])) if words else ("Evergreen" if key == "default" else slug(key))


def tpl(s, v):
    """Fill a theme template (see THEMES); a list is tried in order. None when nothing fills."""
    for t in (s if isinstance(s, list) else [s]):
        t = re.sub(r"\[([^\]]*)\]", lambda m: m.group(1) if all(v.get(k) for k in re.findall(r"{(\w+)}", m.group(1))) else "", t)
        if all(v.get(k) for k in re.findall(r"{(\w+)}", t)):
            t = t.format(**v)
            return t[:1].upper() + t[1:]
    return None


# ---------------------------------------------------------------- products
# Spoken feature lines + on-screen tag + picks: [clip_bank section, key, start] | ["clip", i, start] | ["photo", n].
# Real footage only (pick() refuses AI clips). deal = the stored offer, used when libracases.com can't be read: plan
# takes the % (price vs compare-at) and the gift (title/description says free pouch/wallet) from the site.
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
        reviews=[7, 8, 9, 10, 6, 2, 12], deal=dict(pct=50, gift="free matching pouch wallet", card="+ FREE MATCHING WALLET")),
    "hobo 2.0": dict(
        name="Hobo 2.0", short="Hobo 2.0", site="Hobo 2.0", end="Hobo 2.0",
        hook_clips=[["hobo_2_0", "beige_360", 0.0], ["hobo_2_0", "table_strap", 28.6]],
        features=[
            ("Lockable zippers, so nobody can open it in a crowd.", "LOCKABLE ZIPPERS",
             [["hobo_2_0", "lockable_zippers", 28.1], ["hobo_2_0", "lockable_zippers", 31.6]]),
            ("An RFID lining that blocks card scanners.", "RFID LINING",
             [["hobo_2_0", "lockable_zippers", 12.2], ["hobo_2_0", "beige_360", 5.0]]),
            ("A cut-resistant strap.", "CUT-RESISTANT STRAP", [["hobo_2_0", "beige_360", 12.0]]),
            ("And a table strap that loops around your chair, so your bag stays right where you left it.",
             "TABLE SECURITY STRAP", [["hobo_2_0", "table_strap", 18.9], ["hobo_2_0", "table_strap", 0.0]]),
            ("Hidden pockets and smart compartments for everything else.", "HIDDEN POCKETS",
             [["hobo_2_0", "table_strap", 12.6], ["hobo_2_0", "beige_360", 6.85]]),
        ],
        customer=[], broll=[["hobo_2_0", "beige_360", 0.0], ["hobo_2_0", "table_strap", 28.4],
                            ["hobo_2_0", "lockable_zippers", 35.1]],
        reviews=[11, 7, 8, 6], deal=dict(pct=50, gift="free pouch wallet", card="+ FREE POUCH WALLET")),
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
            ("Smart compartments and an anti-theft design keep everything secure.", "ANTI-THEFT DESIGN",
             [["hobo_3piece_set", "brown_room_outside", 111.0], ["hobo_bag", "back_pocket_4k", 3.6]]),
            ("Soft, water-resistant, scratch-proof leather that looks beautiful season after season.", "SCRATCH-PROOF LEATHER",
             [["hobo_3piece_set", "brown_room_outside", 101.5], ["hobo_bag", "details_macro_4k", 2.0]]),
        ],
        customer=[], broll=[["hobo_3piece_set", "brown_room_outside", 31.0], ["hobo_3piece_set", "brown_room_outside", 73.0],
                            ["hobo_3piece_set", "brown_room_outside", 105.0], ["hobo_3piece_set", "black_door", 0.0]],
        reviews=[7, 8, 9, 6], deal=dict(pct=60, gift=None, statics_sub="Bag, crossbody and pouch in one set.")),
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
        reviews=[6, 7, 9], deal=dict(pct=50, gift=None)),
    "slouchy": dict(
        name="Slouchy Soft 3-Piece Set", short="Slouchy Set", site="slouchy", end="The Slouchy Soft Set",
        hook_clips=[["slouchy_set", "brown_lifestyle", 8.0], ["slouchy_set", "coffee_run", 6.5]],
        features=[
            ("Effortlessly stylish, with a soft, slouchy silhouette.", "SOFT + SLOUCHY", [["slouchy_set", "brown_lifestyle", 11.3]]),
            ("Three pieces in every set: the bag, a crossbody, and a pouch.", "3-PIECE SET",
             [["slouchy_set", "flatlay", 1.0], ["slouchy_set", "all3_crossbody", 4.0]]),
            ("Thoughtful pockets keep everything beautifully organised.", "STAYS ORGANISED", [["slouchy_set", "coffee_run", 11.8]]),
            ("Secure anti-theft zips and thoughtful pockets keep your valuables safe.", "ANTI-THEFT ZIPS",
             [["slouchy_set", "all3_crossbody", 0.5], ["slouchy_set", "flatlay", 3.5]]),
            ("A relaxed, timeless shape that goes with any outfit.", "TIMELESS LOOK",
             [["slouchy_set", "brown_lifestyle", 3.0], ["slouchy_set", "coffee_run", 0.5]]),
        ],
        customer=[], broll=[["slouchy_set", "all3_crossbody", 9.0], ["slouchy_set", "brown_lifestyle", 14.5],
                            ["slouchy_set", "coffee_run", 1.0]],
        reviews=[7, 8, 6], deal=dict(pct=60, gift=None, statics_sub="Bag, crossbody and pouch in one set.")),
}
# keyword -> built-in product, most specific first (whole words: "set" never matches "sunset");
# "Slouchy Vintage Bag" is the weekly brief's name for the Vintage Bag group (33-H5, C9_V2)
PRODUCT_KEYS = {"slouchy vintage": "vintage", "slouchy": "slouchy", "2.0": "hobo 2.0", "hobo2": "hobo 2.0", "hobo 2": "hobo 2.0", "6-layer": "hobo 2.0",
                "3-piece": "3-piece set", "three piece": "3-piece set", "set": "3-piece set",
                "vintage": "vintage", "hobo bag": "hobo bag", "hobo": "hobo bag"}
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
    """Whole-word match; a space or hyphen in w also matches a space, a hyphen or nothing ('three piece' ~ 'three-piece',
    'hobo bag' ~ 'HoboBag')."""
    pat = re.sub(r"(?:\\ |\\-|-)+", r"[\\s-]*", re.escape(w)) if w else ""
    return bool(w) and re.search(r"(?<![a-z0-9])" + pat + r"(?:s|'s)?(?![a-z0-9])", text) is not None


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


def product(pk, files, warnings=None):
    """Built-in product or a product file, in one shape. offer: the product-file offer block; built-ins get theirs
    from resolve_offer() at plan time. Product files never carry reviews of other products or unbacked claims."""
    import new_product
    w = warnings if warnings is not None else []
    if pk in PRODUCTS:
        d = PRODUCTS[pk]["deal"]
        return dict(PRODUCTS[pk], key=pk, offer=builtin_offer(d["pct"], d.get("gift"), d), photos=[], clips=[],
                    source="built-in", status="ready", site_lifestyle=[])
    d = files[pk]
    revs = [n for n in d.get("reviews") or [] if new_product.review_about(n, d)]
    if revs != list(d.get("reviews") or []):
        w.append(f"{d['name']}: reviews {[n for n in d.get('reviews') or [] if n not in revs]} dropped: not about this product")
    return dict(key=pk, name=d.get("short") or d["name"], short=d.get("short") or d["name"], site=d.get("site"),
                end=d.get("end") or d["name"], hook_clips=d.get("hook_clips") or [], features=[tuple(f) for f in d.get("features") or []],
                customer=d.get("customer") or [], broll=d.get("broll") or [], reviews=revs, offer=d.get("offer") or {},
                photos=d.get("photos") or [], clips=d.get("clips") or [], source=d.get("_path") or "product file",
                status=d.get("status"), notes=(d.get("facts") or {}).get("notes") or "", facts=d.get("facts") or {},
                site_lifestyle=d.get("site_lifestyle") or [], hooks=d.get("hooks") or [])   # hooks: project-mode lines


def honest(pr, warnings):
    """Product file, after its offer is resolved: drop feature lines/tags and a statics_sub that claim more than the
    offer backs (a hand-edited 'ready' file must not leak a % or a free gift into the ads)."""
    import new_product
    if pr["source"] == "built-in":
        return pr
    pct, gift = deal_of(pr["offer"])
    feats = []
    for f in pr["features"]:
        why = new_product.unbacked(f[0], pct, gift) or new_product.unbacked(f[1], pct, gift)
        if why:
            warnings.append(f"{pr['name']}: feature {f[1]!r} dropped: it claims {why} that the offer does not back")
        else:
            feats.append(f)
    sub = pr["offer"].get("statics_sub") or ""
    if new_product.unbacked(sub, pct, gift):
        warnings.append(f"{pr['name']}: offer.statics_sub {sub!r} dropped: it claims more than the offer")
        pr["offer"] = dict(pr["offer"], statics_sub="")
    pr["features"] = feats
    return pr


def known_products(files):
    return [p["name"] for p in PRODUCTS.values()] + [d.get("name") or k for k, d in files.items()]


def builtin_offer(pct, gift, d):
    """Offer block (product-file shape) for a built-in bag."""
    card = d.get("card") if gift and gift == d.get("gift") else ("+ " + gift.upper() if gift else "")
    return dict(badge={"top": "NOW", "big": f"{pct}%", "bottom": "OFF"} if pct else None, gift=gift,
                offer_title=f"{pct}% OFF" if pct else "", offer_sub=card, statics_sub=d.get("statics_sub") or "", close="")


_SITE = {}


def site_facts(site):
    """Price, compare-at, title and description of a libracases.com product (no photos), cached; {} when unreadable."""
    if site not in _SITE:
        try:
            import html
            import site_assets
            h = site_assets.find_handle(site)
            p = json.loads(site_assets.get(f"{site_assets.SITE}/products/{h}.json"))["product"]
            v = p["variants"][0]
            _SITE[site] = dict(title=p["title"], price=v.get("price"), compare_at=v.get("compare_at_price"),
                               description=html.unescape(re.sub(r"<[^>]+>", " ", p.get("body_html") or "")))
        except Exception:  # noqa: BLE001 - offline / site down: the stored offer is used
            _SITE[site] = {}
    return _SITE[site]


def resolve_offer(pr, facts, warnings):
    """Honest offer from libracases.com at plan time: % = price vs compare-at, rounded down to a multiple of 5; a gift
    only when the title/description says free pouch/wallet. Built-ins fall back to their stored deal, product files
    to their own offer block, when the site can't be read."""
    import new_product
    if not pr.get("site"):
        return pr["offer"]
    facts = facts or site_facts(pr["site"])
    if not facts.get("price"):
        warnings.append(f"{pr['name']}: libracases.com could not be read: using the stored offer")
        return pr["offer"]
    pct = new_product.site_pct(facts.get("price"), facts.get("compare_at")) or None
    hits = [m.group(0) for m in new_product.GIFT.finditer(f"{facts.get('title', '')} {facts.get('description', '')}")
            if new_product.GIFT_ONLY.search(m.group(0))]
    o = pr["offer"]
    if pr["source"] == "built-in":
        d = pr["deal"]
        gift = (d.get("gift") or max(hits, key=len).lower()) if hits else None
        if (pct, gift) != (d["pct"], d.get("gift")):
            warnings.append(f"{pr['name']}: the site now shows {f'{pct}% off' if pct else 'no discount'}"
                            f"{' + ' + gift if gift else ', no gift'} (stored: {d['pct']}%{' + ' + d['gift'] if d.get('gift') else ''})"
                            f": the ads use the site's offer")
        return builtin_offer(pct, gift, d)
    m = re.match(r"\s*(\d+)\s*%", (o.get("badge") or {}).get("big", ""))
    have = int(m.group(1)) if m else None
    said = re.findall(r"(\d{1,2})\s*%\s*off", pr.get("notes") or "", re.I)
    g = (o.get("gift") or "").lower()
    src = f"{facts.get('title', '')} {facts.get('description', '')} {pr.get('notes') or ''}".lower()
    gift_ok = not g or g in src or all(w in src for w in re.findall(r"[a-z]+", g) if len(w) > 3)   # as new_product.validate
    if ((pct or None) == have or (not pct and have and str(have) in said)) and gift_ok:
        return o
    new = new_product.draft_offer(dict(pr.get("facts") or {}, **facts), pr.get("notes") or "", pr["short"])
    was = " + ".join(x for x in (o.get("offer_title") or "no discount", g) if x)
    now = " + ".join(x for x in (new["offer_title"] or "no discount", new.get("gift")) if x)
    warnings.append(f"{pr['name']}: the product file says {was}, the site now gives {now}"
                    f"{'' if gift_ok else f' (it no longer mentions a {g})'}: the ads use the site's offer (update the product file)")
    return dict(o, **{k: new[k] for k in ("badge", "gift", "offer_title", "offer_sub", "statics_sub", "close")})


def deal_of(o):
    m = re.match(r"\s*(\d+)\s*%", (o.get("badge") or {}).get("big", ""))
    gift = re.sub(r"^(?:a|an)\s+", "", (o.get("gift") or "").strip(), flags=re.I) or None
    return (int(m.group(1)) if m else None), gift


ACRONYMS = {"RFID", "US", "UK", "USB", "ID", "PU", "XL", "XS"}


def tcase(tag, mode="title"):
    """On-screen case for a feature TAG, acronyms kept: 'RFID LINING' -> 'RFID Lining' (title), 'RFID lining'
    (sentence), 'RFID lining' (lower); 'CUT-RESISTANT STRAP' -> 'Cut-Resistant Strap' / 'Cut-resistant strap'."""
    out = []
    for i, w in enumerate(tag.split()):
        if re.sub(r"[^A-Za-z]", "", w).upper() in ACRONYMS and w.isupper():
            out.append(w)
        elif mode == "title":
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
        else:
            out.append((w[:1].upper() if mode == "sentence" and i == 0 else w[:1].lower()) + w[1:].lower())
    return " ".join(out)


def offer_vars(pr):
    """Values for the THEMES templates from the product's own offer."""
    import new_product
    o = pr["offer"]
    pct, gift = deal_of(o)
    noun = (re.findall(r"pouch|wallet|purse", gift or "", re.I) or [""])[-1].lower()
    off = f"{new_product.say(pct)} percent off" if pct else ""
    tags = list(dict.fromkeys(f[1] for f in pr["features"]))[:3]
    return dict(short=pr["short"], name=pr["name"], pct=pct, gift=gift or "", P=f"{pct}%" if pct else "", off_sp=off,
                price_sp="half price" if pct == 50 else off, gift_sp=f"a {gift}" if gift else "",
                gift_w=f"free {noun}" if noun else "", GIFT_W=noun.upper(),
                card=(o.get("offer_sub") or ("+ " + gift.upper() if gift else "")) if gift else "",
                feats=", ".join([tcase(t, "sentence") for t in tags[:1]] + [tcase(t, "lower") for t in tags[1:]]))


def offer_texts(pr, th):
    """Every offer/claim string a batch uses, from the product's own offer (built-ins: THEMES templates; product
    files: their offer block, with the theme's lead). Nothing claims a %, a gift or a sale the offer does not back."""
    import new_product
    v = offer_vars(pr)
    o, pct, gift, bi = pr["offer"], v["pct"], v["gift"] or None, pr["source"] == "built-in"
    d = THEMES["default"]

    def T(key, theme=th):    # filled theme line, or None when it can't be said honestly
        s = tpl(theme.get(key) or "", v)
        return s if s and not new_product.unbacked(s, pct, gift) else None
    hooks = [h for h in (tpl(x, v) for x in th["hooks"]) if h and not new_product.unbacked(h, pct, gift)]
    if len(hooks) < (1 if bi else 2) and th is not d:
        hooks += [tpl(x, v) for x in d["hooks"]]
    statics_sub = o.get("statics_sub") or ""
    lead = T("lead") or ""
    bold = th["bold"]
    if not bi and (bold == d["bold"] or new_product.unbacked(" ".join(bold), pct, gift)):
        ws = (list(dict.fromkeys(f[1] for f in pr["features"])) or [f"MEET THE {pr['short'].upper()}"])[0].split()
        bold = [" ".join(ws[:-1]), ws[-1] + "."] if len(ws) > 1 else [ws[0] + "."]
    gift_words = [w for w in re.findall(r"[a-z]+", (gift or "").lower()) if w in ("free", "pouch", "wallet", "purse", "gift")]
    return dict(badge=o.get("badge") or None, promo_badge=dict(o["badge"], top="SALE") if o.get("badge") else None,
                gift_tail=f" and a {gift}." if gift else ".",
                promo_sub=("+ " + re.sub(r"^free\b", "FREE", gift, flags=re.I)) if gift else statics_sub or (f"Now {pct}% off." if pct else ""),
                colours_sub=f"Every colour comes with a {gift}." if gift else statics_sub or (f"Now {pct}% off." if pct else ""),
                colours_line=f"Every colour comes with a {gift}." if gift else "Which one is yours?",
                bold_sub=(T("sub") or statics_sub or (f"Now {pct}% off." if pct else "")) if bi else statics_sub,
                cta=T("cta") or "Shop now", offer_title=T("offer_title") or ("" if bi else o.get("offer_title") or ""),
                offer_sub=(T("offer_sub") or "") if bi else o.get("offer_sub") or "",
                offer_word=str(pct) if pct else ("free" if gift else None),
                close=(T("close") or "Tap the link below.") if bi else (lead + " " if lead else "") + (o.get("close") or "Tap the link below."),
                hooks=hooks, hero=T("hero") or tpl(d["hero"], v), bold=bold,
                keywords=([f"{pct}%"] if pct else []) + gift_words + (["hidden", "pocket"] if bi else []) + ["leather"],
                compare_left=["Keys lost at the bottom", "One big empty space",
                              "Wallet sold separately" if gift and re.search("wallet|pouch|purse", gift, re.I) else "Nothing has its own place"])


def rot(xs, k):
    """xs rotated left by k."""
    xs = list(xs)
    return xs[k % len(xs):] + xs[:k % len(xs)] if xs else xs


def bank():
    return json.load(open(os.path.join(HERE, "data", "clip_bank.json")))


def clip(b, sec, key):
    return b[sec][key]["id"]


def reviews_by_n():
    return {r["n"]: r for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}


SPOKEN = {  # short verbatim pieces of each review, as read by the narrator (spoken() checks they are verbatim)
    1: ("One customer", "it holds everything I need for my daily outings"),
    2: ("One customer", "the quality of the Hobo Shoulder Bag is amazing! It fits all my essentials"),
    3: ("One customer", "it holds all my daily essentials and looks chic"),
    4: ("One customer", "the quality is fantastic, and it fits all my essentials perfectly"),
    5: ("One customer", "quick shipping and good quality make it a standout purchase"),
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


def flat(s):
    return " ".join(re.findall(r"[a-z0-9']+", s.lower()))


def spoken(n, revs):
    """(who, quote) the narrator reads: SPOKEN if its quote is verbatim in reviews.json, else the review's first
    sentence. A reviewer known only by an initial ('M A.') is 'One customer'."""
    r = revs[n]
    if n in SPOKEN and flat(SPOKEN[n][1]) in flat(r["text"]):
        return SPOKEN[n]
    if n in SPOKEN:
        print(f"SPOKEN[{n}] is not verbatim in reviews.json: reading the review's first sentence", file=sys.stderr)
    who = r["name"].split()[0].rstrip(".")
    return ("One customer" if len(who) < 2 else who), short_quote(r["text"]).rstrip(".!")


def tok(w):
    return re.sub(r"[^\w%']", "", w.lower())


def cards_ok(text, cards, starts):
    """remix.py finds each card's word in order, each after the previous one (same match rule, remix.hit): check it
    lands on the right name."""
    from remix import hit
    toks, k = [tok(w) for w in text.split()], 0
    for c, want in zip(cards, starts):
        i = next((i for i in range(k, len(toks)) if hit(toks[i], c["word"])), None)
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


def ad_prefix(product, theme, rev=1):
    """LC_<YYMMDD>_<Product>_<Theme>[_v2]: see docs/NAMING.md (theme = theme_name()). The ad id (S01_hero) follows."""
    d = datetime.date.today().strftime("%y%m%d")
    return f"LC_{d}_{slug(product)}_{theme}" + (f"_v{rev}" if rev > 1 else "")


def drive_names(day):
    """Names of the files in Drive that start with LC_<day> (read-only query), or None when Drive can't be read."""
    try:
        import contextlib
        import io
        from drive_upload import access_token, query
        with contextlib.redirect_stdout(io.StringIO()):
            tok_ = access_token()
        return [f["name"] for f in query(tok_, f"name contains 'LC_{day}' and trashed = false")]
    except (Exception, SystemExit):  # noqa: BLE001
        return None


def free_rev(prefixes, rev, taken):
    """First revision >= rev whose names are not in Drive yet (NAMING.md rule 4: a name is never reused)."""
    while any(n.startswith(ad_prefix(p, t, rev) + "_") and (rev > 1 or not re.match(r"_v\d+_", n[len(ad_prefix(p, t, 1)):]))
              for p, t in prefixes for n in taken):
        rev += 1
    return rev


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


def only_ids(only, projects):
    """--only 'S01,V02,P03H2' -> upper-case id prefixes in the plan's own terms (an ad is picked when its id starts with
    one). Project mode (video ids P01H1 ..): V02 = project P02 (all its versions), V / P = every video. Single videos
    (--hooks 1, ids V01 ..): P02 / P02H1 = V02 (a P02H3 matches nothing: there are no hook versions)."""
    ids = []
    for x in re.sub(r"\s+", "", (only or "").upper()).split(","):
        if x[:1] == "V" and projects:
            x = "P" + x[1:]
        elif x[:1] == "P" and not projects:
            m = re.match(r"P(\d*)(?:H1)?$", x)
            x = "V" + m.group(1) if m else x
        ids += [x] if x else []
    return ids


def picked(i, ids):
    return any(i.startswith(x) for x in ids)


def static_id(name):
    return re.findall(r"_(S\d+)_", name)[-1]


# ---------------------------------------------------------------- plan
def plan(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    theme_key = pick_theme(a.theme)
    th = dict(THEMES[theme_key])
    tname = theme_name(a.theme, theme_key)
    pdir = products_dir(a)
    files = product_files(pdir)
    warnings = []
    if (a.theme or "").strip() and theme_key not in NAMED and tname not in ("Evergreen", "Gift"):
        warnings.append(f"theme {a.theme!r} is not built in: the ads use the {'gift' if theme_key == 'gift' else 'evergreen'} "
                        f"lines and are named ..._{tname}_...; write its hooks and closes with --lines")
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
    pr = product(pk, files, warnings)
    if pr["status"] != "ready" and not a.allow_draft:
        print(f"product file {pr['source']} has status '{pr['status']}': review its features and offer, set "
              f"\"status\": \"ready\", run python3 pipeline/new_product.py check {pr['source']} (or plan with --allow-draft)",
              file=sys.stderr)
        sys.exit(2)
    if pr["source"] != "built-in":    # a 'ready' file must still pass check (media reachable, 3-5 features, honest offer)
        import new_product
        P, _ = new_product.validate({k: v for k, v in files[pk].items() if k != "_path"})
        if P and not a.allow_draft:
            print(f"product file {pr['source']} fails python3 pipeline/new_product.py check:\n  - " + "\n  - ".join(P) +
                  "\nFix the file and re-run check. Photos/clips with no Drive id and no local file: put them in the product's "
                  "Drive New Products folder and re-run new_product.py intake from there (a file made with intake --local "
                  "only works in the session that made it).", file=sys.stderr)
            sys.exit(2)
        warnings += [f"{pr['name']} (--allow-draft): {x}" for x in P]
    over, used = (json.load(open(a.lines)) if a.lines else {}), set()

    def ov(default, *keys):           # --lines override: the first key it has (V03_hook, or storyboard-relative B01_hook)
        k = next((k for k in keys if k in over), None)
        used.update([k] if k else [])
        return over[k] if k else default
    rel = lambda f: os.path.relpath(f, out) if os.path.abspath(f).startswith(out + os.sep) else os.path.abspath(f)  # noqa: E731
    revs = reviews_by_n()
    b = bank()
    rw = {}
    if W:
        import winners
        rw = winners.raws()
    wps = {}                          # winner product key -> product (offer resolved once)

    def wprod(key):
        wpk = pick_product(rw[key].get("product") or "", files) or pk
        if wpk not in wps:
            wps[wpk] = pr if wpk == pk else product(wpk, files, warnings)
        return wps[wpk]

    def need_deal(p):                 # a sale-event ad must have a real deal behind it
        if theme_key in SALE_THEMES and not any(deal_of(p["offer"])):
            print(f"{p['name']} has no offer right now (libracases.com shows no discount and no free gift"
                  f"{'' if p['source'] == 'built-in' else ', and its product file has none'}): a {theme_key} ad would promise "
                  f"a deal that isn't there. Drop the theme, or add the offer to the product file (offer.badge / gift, "
                  f"backed by the site or the client's notes) and re-run.", file=sys.stderr)
            sys.exit(2)

    # ---------- site photos + facts, product-file photos and clips
    colour_imgs, packs, clean_site, site_imgs, facts = [], [], [], [], {}
    need = a.statics > 0 or a.videos > 0
    if need and pr["site"]:
        import site_assets
        site = os.path.join(out, "site")
        r = subprocess.run([sys.executable, os.path.join(HERE, "site_assets.py"), pr["site"], "--out", site],
                           capture_output=True, text=True)
        print(r.stdout.strip(), r.stderr.strip(), file=sys.stderr)
        try:      # this product's facts file (an --out reused for another product holds other facts files too)
            ff = [json.loads(r.stdout.strip().splitlines()[-1])["facts"]]
        except (ValueError, KeyError, IndexError):
            ff = []
        if r.returncode or not ff or not os.path.exists(ff[0]):
            if pr["source"] == "built-in":
                sys.exit(f"site_assets.py failed for {pr['site']!r}")
            warnings.append(f"site photos for {pr['site']!r} could not be read: using the product file's photos only")
        else:
            facts = json.load(open(ff[0]))
            sc, site_imgs = facts["scores"], facts["images"]

            def usable(f, lo):        # a site packshot without its baked-in tag ('NEW' masked off), clean enough
                if f in site_imgs[:1]:
                    return None       # image 00: sale badges
                u = site_assets.unbadged(f, os.path.join(site, "clean"))
                return u if u and (sc.get(f, 0) if u == f else site_assets.clean_score(u)) >= lo else None
            colour_imgs = [(n, u) for n, f in facts["colours"].items() for u in [usable(f, 0.6)] if u]
            clean_site = [u for f in facts["clean_images"] if f not in facts["colours"].values() for u in [usable(f, 0.8)] if u]
            packs = [f for _, f in colour_imgs] or clean_site
    pr["offer"] = resolve_offer(pr, facts, warnings)
    honest(pr, warnings)
    for w in (sel["winners"] if W else []):
        p_ = wprod(w["key"])
        if p_ is not pr and not p_.get("_resolved"):
            p_.update(offer=resolve_offer(p_, None, warnings), _resolved=True)
            honest(p_, warnings)
    if W:     # the speaker's % must never be more than the site gives: such a RAW needs a human recut of its offer
        keep = []
        for w in sel["winners"]:
            ow, wp_ = str(rw[w["key"]]["edit"].get("offer_word") or ""), wprod(w["key"])
            wpct = deal_of(wp_["offer"])[0]
            if ow.isdigit() and (not wpct or wpct < int(ow)):
                now = f"{wpct}% off" if wpct else "no discount"
                sel["unmatched"].append(dict(name=w.get("name") or w["key"], roas=w.get("roas"), action=w.get("action"),
                                             product=wp_["name"], why=f"the RAW says {ow}% off but {wp_['name']} is {now} on "
                                             f"libracases.com now: a human must recut its offer (not remixed)",
                                             client=f"its video says {ow}% off, the site now gives {now}: it needs a new offer edit"))
            else:
                keep.append(w)
        if not keep:
            msg = "every winner's RAW promises more than the site's offer now (see unmatched): no winner remixes"
            if sel["source"] == "codes":
                print(json.dumps(sel["unmatched"], indent=1, ensure_ascii=False) + "\n" + msg, file=sys.stderr)
                sys.exit(2)
            warnings.append(msg)
            W = 0
        sel["winners"] = keep
    wrows = [sel["winners"][i % len(sel["winners"])] for i in range(W)] if W else []   # cycling through the winners
    if W and a.hooks > 1:   # project mode: a project holds up to --hooks of its winner's cold opens (projects.py); another
        # project of the same winner only when its RAW has --hooks more, else it would repeat them under new names
        def n_cos(k):
            return len({(json.dumps(c.get("range")), (c.get("label") or "").upper())
                        for c in rw[k]["edit"].get("cold_opens") or []}) or 1
        cap = {w["key"]: max(1, n_cos(w["key"]) // a.hooks) for w in sel["winners"]}
        wrows = [w for r_ in range(max(cap.values())) for w in sel["winners"] if cap[w["key"]] > r_][:W]
        if len(wrows) < W:
            held = ", ".join(f"{w.get('name') or w['key']}: {n_cos(w['key'])}" for w in {x["key"]: x for x in wrows}.values())
            warnings.append(f"--winner-videos {W}: {len(wrows)} winner project{'s' if len(wrows) > 1 else ''} "
                            f"({'one per winner' if max(cap.values()) == 1 else 'per winner as its cold opens allow'}; cold "
                            f"opens {held}): a project holds up to {a.hooks} of its winner's cold opens, so another project "
                            f"of the same winner would repeat its openings under new names (only the narrated reviews "
                            f"differ); {W - len(wrows)} left out. More projects of a winner need new cold opens first "
                            f"(python3 pipeline/winner_prep.py)")
        W = len(wrows)
    wkeys = [w["key"] for w in wrows]
    if need:
        need_deal(pr)
    for k in wkeys:
        need_deal(wprod(k))
    tx = offer_texts(pr, th)

    # ---------- names: the first _vN not in Drive yet (NAMING.md rule 4)
    rev = a.rev
    if not a.no_name_check:
        taken = drive_names(datetime.date.today().strftime("%y%m%d"))
        if taken is None:
            warnings.append("could not read Drive to check today's names: if this product + theme was uploaded today "
                            "already, re-plan with --rev 2")
        else:
            rev = free_rev({(pr["name"], tname)} | {(wprod(k)["name"], tname) for k in wkeys}, a.rev, taken)
            if rev != a.rev:
                print(f"names: _v{rev} (today's {ad_prefix(pr['name'], tname, a.rev)} names are already in Drive)", file=sys.stderr)
                warnings.append(f"names bumped to _v{rev}: earlier ads with these names are already in Drive today")
    prefix = ad_prefix(pr["name"], tname, rev)
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
            import contextlib
            import io
            from drive_upload import access_token, download
            with contextlib.redirect_stdout(io.StringIO()):       # its error JSON must not break plan's stdout JSON
                token[:] = token or [access_token()]
                return download(token[0], item["id"], src or dest)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            warnings.append(f"{item.get('name')}: Drive download failed "
                            f"({'no Drive login: python3 pipeline/drive_upload.py check' if isinstance(e, SystemExit) else e})")
            return None

    import new_product
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
            pack = (p.get("clean") or 0) >= 0.8
            if new_product.count_faces(dest, strict=not pack):          # re-checked with today's detector
                warnings.append(f"photo {p.get('name')}: a face was found: never used in statics")
                continue
            file_photos.append(dest)
            (file_packs if pack else file_life).append(dest)
    clips = []
    for i, c in enumerate(pr["clips"] if a.videos > 0 else []):
        clips.append(fetch(c, os.path.join(out, "clips", f"{i:02d}_{safe_name(c.get('name', 'clip.mp4'))}")))
    packs = packs + file_packs
    pool = list(dict.fromkeys(packs + clean_site + file_photos))
    life_cache = []

    def lifestyle():
        """Photos for lifestyle statics: the client's photos with no face (strict check) and the site photos the product
        file lists in site_lifestyle (never image 0). Other site photos are never put in statics automatically."""
        if not life_cache:
            listed = [site_imgs[i] for i in (new_product.site_index(x) for x in pr["site_lifestyle"]) if i and i < len(site_imgs)]
            ok = []
            for f in listed:
                if new_product.count_faces(f, strict=True):
                    warnings.append(f"site_lifestyle {os.path.basename(f)}: a face was found: not used")
                else:
                    ok.append(f)
            life_cache.append(file_life + ok)
        return life_cache[0]

    def pick(p, w=1.0):
        """[src, start, weight(, extra)] for a pick, or None when it points at nothing (or at an AI clip)."""
        if not p:
            return None
        if p[0] == "photo":
            return [rel(pool[p[1] % len(pool)]), 0, w, {"zoom": [1.0, 1.06]}] if pool else None
        if p[0] == "clip":
            c = clips[p[1]] if isinstance(p[1], int) and 0 <= p[1] < len(clips) else None
            return [c, p[2], w] if c else None
        try:
            src = clip(b, p[0], p[1])
        except (KeyError, IndexError, TypeError):
            warnings.append(f"pick {p!r} is not in clip_bank.json")
            return None
        if str(src).startswith("http") or str(p[1]).startswith("ai_"):
            warnings.append(f"pick {p!r} is an AI clip: real footage only, skipped")
            return None
        return [src, p[2], w]

    def picks(ps, fallback=True, w=1.0):
        got = [x for x in (pick(p, w) for p in ps) if x]
        if got or not fallback:
            return got
        for alt in pr["broll"] + pr["hook_clips"] + [["photo", 0]]:
            x = pick(alt)
            if x:
                return [x]
        return []

    # ---------- statics: a later pass over the layout cycle (or another --seed) shows another photo and headline; a
    # static that would still repeat an earlier one exactly is left out
    tags = list(dict.fromkeys(f[1] for f in pr["features"]))
    clean_mode = len(packs) >= 2
    seq = (["hero", "promo", "bold", "review", "colours", "compare", "review", "promo", "hero", "bold"] if clean_mode else
           ["lifestyle", "bold", "hero", "lifestyle", "compare", "review", "lifestyle", "bold", "hero", "lifestyle"])
    if not clean_mode and a.statics:
        warnings.append(f"only {len(packs)} clean packshot(s): statics use the client's lifestyle photos and framed photo cards")
    statics, n_life, seen_s, nlay = [], 0, set(), {}
    import brand_statics as bs
    cards = {rel(f) for f in packs if bs.textured(f)}     # light textured backdrop: a framed card, never a grey box
    hero = ov(tx["hero"], "hero") if a.statics else tx["hero"]

    def two_lines(tag):
        ws = tag.split()
        return [" ".join(ws[:-1]), ws[-1] + "."] if len(ws) > 1 else [ws[0] + "."]

    def static(lay, photo, hv):       # hv: headline/sub variant (0 = the standard one)
        V = lambda *xs: list(dict.fromkeys(x for x in xs if x))[hv % len(list(dict.fromkeys(x for x in xs if x)))]  # noqa: E731
        tg = rot(tags, hv)
        if lay == "hero":
            sub = ", ".join([tcase(t, "sentence") for t in tg[:1]] + [tcase(t, "lower") for t in tg[1:2]])
            return dict(layout="hero", photo=photo, headline=V(hero, f"Meet the {pr['short']}.", f"The {pr['short']}."),
                        sub=sub + tx["gift_tail"] if sub else tx["bold_sub"], badge=tx["badge"], cta=tx["cta"])
        if lay == "promo":
            return dict(layout="promo", photo=photo, headline=V((th["label"].title() + ": " if th["label"] else "") +
                                                               f"The {pr['short']}", f"The {pr['short']}", f"Meet the {pr['short']}"),
                        sub=tx["promo_sub"], features=[tcase(t) for t in tg[:3]], badge=tx["promo_badge"], cta=tx["cta"])
        if lay == "bold":
            dots = [DOTS.get(n.lower().split()[0], [150, 150, 150]) for n, _ in colour_imgs][:7]
            lines_ = [ov(tx["bold"], "bold")] + [two_lines(t) for t in tags]
            return dict(layout="bold", photo=photo, lines=lines_[hv % len(lines_)], accent_lines=[1], sub=tx["bold_sub"],
                        cta=tx["cta"], dots=dots)
        if lay == "review":
            return dict(layout="review", review_n=pr["reviews"][(i // 6 + hv) % len(pr["reviews"])], photo=photo, cta=tx["cta"])
        if lay == "colours":
            ph = [dict(src=rel(f), name=n) for n, f in colour_imgs][:6] or [dict(src=rel(f), name="") for f in packs[:4]]
            return dict(layout="colours", photos=rot(ph, hv), headline=V(ov("Pick your colour.", "colours"), "Which one is yours?",
                                                                         "Which colour are you?"), sub=tx["colours_sub"], cta=tx["cta"])
        if lay == "lifestyle":
            heads = [hero, f"The {pr['short']}."] + ([". ".join(tcase(t) for t in tags[:2]) + "."] if tags else [])
            return dict(layout="lifestyle", photo=photo, headline=heads[(n_life - 1 + hv) % len(heads)], sub=tx["bold_sub"] or None,
                        cta=tx["cta"])
        return dict(layout="compare", photo=photo, headline=V(f"Your everyday bag vs {pr['short']}", f"Most bags vs the {pr['short']}"),
                    left_title="Most bags", left=tx["compare_left"], right_title=pr["short"],
                    right=[tcase(t, "sentence") for t in tg[:3]], cta=tx["cta"])

    for i in range(a.statics):
        lay = seq[i % len(seq)]
        if lay == "review" and not pr["reviews"]:
            lay = "lifestyle"
        if lay == "colours" and len(colour_imgs) < 2 and len(packs) < 2:
            lay = "lifestyle"
        if lay == "lifestyle" and n_life >= len(lifestyle()):     # each lifestyle photo once per batch
            lay = {"review": "compare", "colours": "bold"}.get(seq[i % len(seq)], "compare" if i % 2 else "bold")
        card = False
        if lay == "lifestyle":
            photos = [lifestyle()[n_life]]
            n_life += 1
        elif packs:
            photos = packs
        elif lifestyle():
            photos, card = lifestyle(), True
        else:
            warnings.append(f"static {i + 1}: no usable photo (no clean packshot, no faceless client photo): skipped")
            continue
        rnd, hv0 = i // len(seq) + a.seed - 1, nlay.get(lay, 0) + a.seed - 1   # hv0: the 2nd hero/promo/... gets another headline
        for t in range(len(photos) * 4):
            photo = photos[(i + rnd + t) % len(photos)]
            s = static(lay, rel(photo), hv0 + t // len(photos))
            sig = json.dumps(s, sort_keys=True)
            if sig not in seen_s:
                break
        else:
            warnings.append(f"static {i + 1} ({lay}) would repeat an earlier static exactly: left out (too few photos/lines "
                            f"for {a.statics} different statics of {pr['name']})")
            continue
        seen_s.add(sig)
        nlay[lay] = nlay.get(lay, 0) + 1
        if card:
            cards.add(rel(photo))
        s["name"] = f"{prefix}_S{len(statics) + 1:02d}_{lay}"
        statics.append(s)

    # ---------- videos
    tts, videos, specs, said = [], [], {}, {}

    def line(vid, key, text, voice):
        f = f"{vid}_{key}.mp3"
        tts.append(dict(file=f, text=text, **voice))
        said[f] = text
        return f

    # winner remixes first: V01..VW
    used_sets, uses = set(), {}
    for i in range(W):
        w = wrows[i]
        e = rw[w["key"]]
        ed = e["edit"]
        j = uses.get(w["key"], 0) + a.seed - 1
        uses[w["key"]] = uses.get(w["key"], 0) + 1
        vid = f"V{i + 1:02d}"
        wp = wprod(w["key"])
        wpct, wo = deal_of(wp["offer"])[0], wp
        if str(ed.get("offer_word") or "").isdigit() and wpct and int(ed["offer_word"]) < wpct:   # (more: left out above)
            if uses[w["key"]] == 1:
                warnings.append(f"{w['key']}: the RAW says {ed['offer_word']}% but {wp['name']} is {wpct}% off on the site: "
                                f"the offer card shows the speaker's {ed['offer_word']}% (never contradict the voice)")
            b_ = wp["offer"].get("badge") or {"top": "NOW", "bottom": "OFF"}
            wo = dict(wp, offer=dict(wp["offer"], badge=dict(b_, big=f"{ed['offer_word']}%"), offer_title=f"{ed['offer_word']}% OFF"))
        wtx = offer_texts(wo, th)
        cos = ed.get("cold_opens") or [{"range": None, "label": "", "line": ""}]
        co = cos[j % len(cos)]
        spec = dict(raw=e["id"], start=ed.get("start") or 0.0, end=ed.get("end"), cut=ed.get("cut") or [],
                    insert_at=ed.get("insert_at"), offer_word=ed.get("offer_word"), offer_after=ed.get("offer_after"),
                    burned_captions=bool(ed.get("burned_captions")), labels=ed.get("labels") or [],
                    end_title=ed.get("end_title") or wp["end"],
                    offer_title=ed.get("offer_title", wtx["offer_title"]), offer_sub=ed.get("offer_sub", wtx["offer_sub"]),
                    keywords=list(dict.fromkeys(wtx["keywords"] + THEME_WORDS[theme_key])))
        if not ed.get("offer_word") and spec["offer_title"] and uses[w["key"]] == 1:
            warnings.append(f"{w['key']}: the RAW never says the offer: its '{spec['offer_title']}' card shows after the review "
                            f"section, just before the end card")
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
                if x and not str(x[0]).startswith("http") and not str(p[1]).startswith("ai_") and \
                        not str(x[0]).lower().endswith((".jpg", ".png")):           # real footage only
                    cand.append([x[0], x[1]])
            firsts, rest = [], []
            for c in cand:                    # one shot per clip first, then second moments of the same clips
                (rest if c[0] in seen else firsts).append(c)
                seen.add(c[0])
            cand = firsts + rest
            n_br = max(3, min(len(cand), math.ceil((len(text.split()) / WPS + 0.4) / 3.5)))
            r0 = (j * 2) % max(len(cand), 1)
            broll = [cand[(r0 + q) % len(cand)] for q in range(n_br)] if cand else []
            if broll:
                spec["reviews"] = dict(vo=line(vid, "rev", text, NARRATOR), text=text, cards=rcards, broll=broll)
            else:
                ns = ()
        if not ns:
            spec["insert_at"] = None
            warnings.append(f"{vid}: {wp['name']} has no reviews/B-roll to narrate: remix without a review section")
        name = f"{ad_prefix(wp['name'], tname, rev)}_{vid}_remix{slug(e.get('concept') or w['key']).lower()}"
        specs[name] = spec
        videos.append(dict(name=name, id=vid, format="remix", engine="remix", hook=co.get("line") or "",
                           hook_label=co.get("label") or "",
                           winner=dict(key=w["key"], ad=e.get("ad"), brief_name=w.get("name"), roas=w.get("roas"),
                                       action=w.get("action"), product=wp["name"], cold_open=co.get("range"),
                                       reviews=list(ns), intro=intro)))

    # storyboard videos: V(W+1).. ; each grows (more features, reviews, colours, customer clips) to ~38 s. Each later pass
    # over the 6-format cycle (and each --seed) starts the hook, features, reviews and B-roll elsewhere; a video that would
    # still repeat an earlier one exactly is left out. No shot shows twice in one ad when another is left.
    formats = ["features", "reviews", "colours", "features", "reviews", "colours"]
    fs = pr["features"]
    rich = bool(pr["reviews"] or pr["customer"])
    feat_picks = {tuple(p) for f in fs for p in f[2]}
    photo_picks = [["photo", k] for k in range(len(pool))]
    colour_names = list((facts or {}).get("colours") or {}) or [n for n, _ in colour_imgs]   # every site colour is said
    gnoun = (re.findall(r"pouch|wallet|purse", deal_of(pr["offer"])[1] or "", re.I) or [""])[-1]
    feat_gift = bool(gnoun) and any(re.search(r"\bfree\b.*\b" + gnoun, f[0], re.I) for f in fs)
    colours_tail = "Which one is yours?" if feat_gift else tx["colours_line"]       # the gift is said twice at most

    def fmt_of(v):
        fmt = formats[v % len(formats)]
        if fmt == "colours" and len(colour_imgs) < 3:
            fmt = "features"
        return "features" if fmt == "reviews" and not pr["reviews"] else fmt

    def board(v, vid, bid, fmt, o):
        # o: this format's earlier videos + (--seed - 1) + retries. Every step moves the hook line and clip, the close
        # B-roll, where the features start and where the reviews start, so a later pass or another seed differs everywhere
        hooks = tx["hooks"]
        if fmt == "colours":
            hooks = (["Be honest. Which colour are you?", "Which colour would you pick?"] if theme_key == "default" else
                     [h + " Which colour are you?" for h in hooks])
        o2 = o + o // len(hooks)
        o3 = o + o // max(len(fs), 1)
        pid = "P" + vid[1:]               # project mode: P03_hook = V03_hook (H1's line; H2.. come from projects.py)
        hook = ov(hooks[(v + o) % len(hooks)], f"{vid}_hook", f"{pid}_hook", f"{bid}_hook")
        hcs = rot(pr["hook_clips"], v + o)
        hc = next((h for h in hcs if tuple(h) not in feat_picks), hcs[0] if hcs else None)   # not a shot a feature shows
        shown = {tuple(hc)} if hc else set()
        cb = next((p for p in rot(pr["broll"], v + o) if tuple(p) not in shown), None)       # kept for the close
        reserved = {tuple(cb)} if cb else set()
        blocks = [dict(vo=line(vid, "hook", hook, BRAND_VOICE), broll=picks([hc] if hc else []))]
        ovl = [dict(type="label", text=th["label"] or {"features": "LOOK CLOSER", "reviews": "REAL REVIEWS",
                                                         "colours": "WHICH ONE?"}[fmt], block=0, at=0.1, dur=1.8)]
        k0 = (v * 2 + o2) % len(fs) if fs else 0
        feat_q = [(k0 + j) % len(fs) for j in range(len(fs))]      # each feature, review, clip at most once per video
        rev_q = rot(pr["reviews"], v + o3)
        cust_q = rot(pr["customer"], v + o3)
        cnt = dict(feat=0, rev=0, colours=0)

        def unseen(ps, k=None):   # shots not on screen yet in this ad (else an unseen photo, else the given ones)
            got = ([p for p in ps if tuple(p) not in shown | reserved] or
                   [p for p in photo_picks if tuple(p) not in shown | reserved][:1] or list(ps))[:k]
            shown.update(tuple(p) for p in got)
            return got

        def add_features(n):
            for _ in range(n):
                if not feat_q:
                    return
                txt, tag, ps = fs[feat_q.pop(0)]
                blocks.append(dict(vo=line(vid, f"feat{cnt['feat']}", txt, BRAND_VOICE), broll=picks(unseen(ps))))
                ovl.append(dict(type="tag", text=tag, block=len(blocks) - 1, at=0.15, dur=2.6))
                cnt["feat"] += 1

        def add_reviews(n):
            for _ in range(n):
                if not rev_q:
                    return
                rn = rev_q.pop(0)
                who, q = spoken(rn, revs)
                text = ("Here's what customers say. " if cnt["rev"] == 0 else "") + f"{who}: {q}."
                br = unseen(rot(pr["broll"], v + o + cnt["rev"] + 1), 1) if pr["broll"] else []
                blocks.append(dict(vo=line(vid, f"rev{cnt['rev']}", text, NARRATOR), broll=picks(br)))
                ovl.append(dict(type="review", n=rn, block=len(blocks) - 1, at=0.1, until_block_end=True))
                cnt["rev"] += 1

        def add_customer():
            if cust_q:
                s_, k_, a_, e_ = cust_q.pop(0)
                blocks.append(dict(clip=clip(b, s_, k_), range=[a_, e_]))
                ovl.append(dict(type="label", text="REAL CUSTOMER", block=len(blocks) - 1, at=0.3, dur=2.0))

        def add_colours():
            if cnt["colours"] or len(colour_imgs) < 3:
                return
            cnt["colours"] = 1
            sw = [(n, os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")) for n, _ in colour_imgs[:6]]
            ns = colour_names
            ctext = (", ".join(ns[:-1]) + ", or " + ns[-1] if len(ns) > 1 else ns[0]) + ". " + colours_tail
            blocks.append(dict(vo=line(vid, "colours", ctext, BRAND_VOICE),
                               broll=[[os.path.relpath(f, out), 0, 1.0, {"zoom": [1.0, 1.06]}] for _, f in sw]))
            ovl.append(dict(type="tag", text=" · ".join(n.upper() for n in ns) if len(ns) <= 4 else f"{len(ns)} COLOURS",
                            block=len(blocks) - 1, at=0.1, dur=3.0))

        nfeat = (3 if fmt == "features" else 2) if rich else 5
        if fmt == "features":
            add_features(nfeat); add_customer(); add_reviews(2)  # noqa: E702
            if not rich:
                add_colours()
        elif fmt == "reviews":
            add_reviews(3); add_customer(); add_features(nfeat)  # noqa: E702
        else:
            add_colours(); add_customer(); add_reviews(2); add_features(nfeat)  # noqa: E702
        close = ov(tx["close"], f"{vid}_close", f"{pid}_close", f"{bid}_close")

        def est_now():
            return sum(len(said.get(x.get("vo"), "").split()) / WPS + 0.25 if "vo" in x else x["range"][1] - x["range"][0]
                       for x in blocks) + len(close.split()) / WPS + 0.25
        while est_now() < 38:            # too short: add what this ad hasn't shown yet (never the same thing twice)
            nb = len(blocks)
            if feat_q:
                add_features(1)
            elif rev_q:
                add_reviews(1)
            elif cnt["colours"] == 0 and len(colour_imgs) >= 3:
                add_colours()
            elif cust_q:
                add_customer()
            if len(blocks) == nb:
                break
        if {f"{vid}_close", f"{pid}_close", f"{bid}_close"} & used and tx["offer_title"] and tx["offer_word"]:
            ow = tx["offer_word"]
            if ow not in close.lower() and (not ow.isdigit() or new_product.say(int(ow)).split("-")[0] not in close.lower()):
                warnings.append(f"{vid}: the --lines close has no '{ow}' (or its spoken word): the offer card will not show")
        on = {rel(pool[p[1] % len(pool)]) for p in shown if p and p[0] == "photo"} if pool else set()
        ph = next((f for f in rot([rel(f) for f in packs], v + o) if f not in on), rel(packs[(v + o) % len(packs)]) if packs else None)
        cl = ([[ph, 0, 1.0, {"zoom": [1.0, 1.06]}]] if ph else []) + \
            [x for x in picks([cb] if cb else [], fallback=False, w=1.2) if x[0] != ph]
        blocks.append(dict(vo=line(vid, "close", close, BRAND_VOICE), broll=cl or picks([])))
        if any(not blk.get("broll") for blk in blocks if "vo" in blk):
            sys.exit(f"{pr['name']}: no footage or photo to show under the voiceover (product has no clips, no clean "
                     f"photos and no site page). Add clips/photos to its Drive folder and re-run the intake.")
        offer = (dict(block=len(blocks) - 1, word=tx["offer_word"], title=tx["offer_title"], sub=tx["offer_sub"])
                 if tx["offer_title"] and tx["offer_word"] else None)
        spec = dict(blocks=blocks, overlays=ovl, end_title=pr["end"], offer=offer,
                    keywords=list(dict.fromkeys(tx["keywords"] + THEME_WORDS[theme_key])))
        return f"{prefix}_{vid}_{fmt}", spec, dict(name=f"{prefix}_{vid}_{fmt}", id=vid, format=fmt, engine="storyboard", hook=hook)

    seen_v, seen_sc, nsb, per_fmt = {}, set(), 0, {}

    def sigs(spec):                       # (script: the words, customer clips and on-screen texts; everything incl. B-roll)
        sc = [said.get(x["vo"]) if "vo" in x else [x["clip"], x["range"]] for x in spec["blocks"]] + \
            [[x.get("type"), x.get("text"), x.get("n")] for x in spec["overlays"]]
        return json.dumps(sc), json.dumps([sc, [x.get("broll") for x in spec["blocks"]]])
    for v in range(a.videos):
        vid, bid, fmt = f"V{W + nsb + 1:02d}", f"B{nsb + 1:02d}", fmt_of(v)
        c, per_fmt[fmt] = per_fmt.get(fmt, 0), per_fmt.get(fmt, 0) + 1
        alt = None                        # another script first; same words over other footage only when nothing else is left
        for t in range(min(60, max(12, len(tx["hooks"]) * max(len(fs), 1) * max(len(pr["reviews"]), 1)))):
            n0, s0 = len(tts), dict(said)
            name, spec, ventry = board(v, vid, bid, fmt, c + a.seed - 1 + t)
            ssig, sig = sigs(spec)
            if ssig not in seen_sc:
                break
            alt = t if alt is None and sig not in seen_v else alt
            del tts[n0:]                  # a repeat of an earlier video's script: take its lines back, start elsewhere
            said.clear()
            said.update(s0)
        else:
            if alt is None:
                warnings.append(f"storyboard video {v + 1} would repeat {seen_v.get(sig, 'an earlier video')} exactly: left out "
                                f"({pr['name']} has only enough features, reviews and clips for {nsb} different storyboard videos)")
                continue
            name, spec, ventry = board(v, vid, bid, fmt, c + a.seed - 1 + alt)
            ssig, sig = sigs(spec)
            warnings.append(f"{vid} says the same words as an earlier video over other footage ({pr['name']} has few "
                            f"features/reviews/hooks): add hooks/closes with --lines for more variety")
        seen_sc.add(ssig)
        seen_v[sig] = vid
        nsb += 1
        specs[name] = spec
        videos.append(ventry)
    unused = sorted(set(over) - used)
    if unused:
        ids = ", ".join(f"{v['id']} (= B{k + 1:02d}{', P' + v['id'][1:] if a.hooks > 1 else ''})"
                        for k, v in enumerate(x for x in videos if x["engine"] == "storyboard"))
        warnings.append(f"--lines keys not used: {', '.join(unused)}. Keys: hero, bold, colours, <id>_hook / <id>_close for "
                        f"the storyboard videos {ids or '(none in this plan)'}")
    pm = a.hooks > 1 and bool(videos)   # project mode: every video becomes project Pnn in a.hooks versions (projects.py)
    keep, ponly = videos, None          # keep: the videos this plan makes; ponly: --only for projects.expand (P02, P02H3)
    if a.only:      # a redo of some ads: only these are voiced, rendered and uploaded (their names keep their numbers)
        ids, statics_all, videos_all = only_ids(a.only, pm), statics, videos
        statics = [s for s in statics if picked(static_id(s["name"]), ids)]
        if pm:      # every video is still planned and expanded, so the kept versions get the hooks the full plan gives them
            pids = [re.match(r"P\d*", x).group(0) for x in ids if x[:1] == "P"]
            keep = [v for v in videos if picked("P" + v["id"][1:], pids)]
            ponly = None if "P" in ids else ",".join(x for x in ids if x[:1] == "P")
            if not keep:
                videos, specs, tts, pm = [], {}, [], False
        else:
            keep = videos = [v for v in videos if picked(v["id"], ids)]
            specs = {v["name"]: specs[v["name"]] for v in videos}
            tts = [t for t in tts if any(t["file"].startswith(v["id"] + "_") for v in videos)]
        if not statics and not keep:
            have = [static_id(s["name"]) for s in statics_all] + [("P" + v["id"][1:]) if a.hooks > 1 else v["id"] for v in videos_all]
            print(f"--only {a.only}: no static or video with that id in this plan (ids: {', '.join(have) or 'none'}"
                  f"{'; --hooks 1 makes single videos, no hook versions' if a.hooks <= 1 and 'H' in a.only.upper() else ''})",
                  file=sys.stderr)
            sys.exit(2)

    # ---------- voiceover: one line per (text, voice); budget
    uniq, dupes = {}, {}
    for t in tts:
        k = (t["text"], t["voice_type"], t["voice_id"])
        if k in uniq:
            dupes[t["file"]] = uniq[k]["file"]
        else:
            uniq[k] = t
    tts_u = list(uniq.values())
    vname = lambda v: ("P" + v["id"][1:]) if pm else v["id"]  # noqa: E731 - how the reply and Drive call this video
    for v in videos:
        v["est_seconds"] = est_seconds(specs[v["name"]], said, rw)
        lo, hi = (35, 110) if v["engine"] == "remix" else (35, 95)
        if v in keep and not lo <= v["est_seconds"] <= hi and not (pm and v["est_seconds"] < lo):  # (expand: per version)
            fix = ("" if v["engine"] == "remix" else ": add lines with --lines" if pr["source"] == "built-in" else
                   ": the product file needs more features/clips, or add lines with --lines")
            warnings.append(f"{vname(v)} will run about {v['est_seconds']:.0f} s (QA wants {lo}-{hi} s){fix}")
    short = [v for v in keep if v["engine"] == "storyboard" and v["est_seconds"] < MIN_SECONDS]
    if short:
        print(f"{', '.join(vname(v) + ' ~' + str(round(v['est_seconds'])) + ' s' for v in short)}: under the {MIN_SECONDS} s "
              f"floor, too short to run as an ad. " + ("Add hook/close lines with --lines, or make fewer videos." if pr["source"] ==
                                                      "built-in" else f"{pr['source']} needs more features, clips or photos "
                                                      "(new_product.py check), or longer lines with --lines."), file=sys.stderr)
        sys.exit(2)
    est = round(0.35 * len(tts_u), 1)
    limit = a.budget if a.budget is not None else MAX_CREDITS
    pct, gift = deal_of(pr["offer"])
    warnings[:] = list(dict.fromkeys(warnings))
    summary = dict(statics=len(statics), **({"projects": len(keep), "hooks": a.hooks} if pm else {}), videos=len(videos),
                   tts_lines=len(tts_u), est_credits=est, budget=limit,
                   theme=theme_key, theme_name=tname, product=pr["name"], product_source=pr["source"],
                   offer=" + ".join(x for x in (f"{pct}% off" if pct else "no discount", gift) if x), names=prefix)
    if est > limit and not (pm and a.only):   # project mode: projects.expand checks again with the hook lines (and --only)
        print(json.dumps(summary, indent=1), file=sys.stderr)
        print(f"voiceover would cost ~{est} credits{f' before the H2-H{a.hooks} hook lines' if pm else ''}, over the "
              f"{limit}-credit budget: make fewer videos{' or fewer --hooks' if pm else ''}, or pass --budget "
              f"{math.ceil(est)}{' or more' if pm else ''} if the request names a bigger budget", file=sys.stderr)
        sys.exit(2)

    rp, now = os.path.join(out, "tts_said.json"), {t["file"]: f"{t['voice_id']}|{t['text']}" for t in tts}
    said_before = json.load(open(rp)) if os.path.exists(rp) else {}
    for f, txt in now.items():        # a re-plan into the same --out: a voiceover made for other words is stale
        if f in said_before and said_before[f] != txt:
            for x in (f, os.path.splitext(f)[0] + "_words.json"):
                if os.path.exists(os.path.join(out, x)):
                    os.remove(os.path.join(out, x))
    json.dump({**said_before, **now}, open(rp, "w"), indent=1, ensure_ascii=False)
    json.dump(dict(ads=statics, card_photos=sorted(cards)), open(os.path.join(out, "statics.json"), "w"), indent=1)
    for name, spec in specs.items():
        json.dump(spec, open(os.path.join(out, name + ".json"), "w"), indent=1)
    json.dump(tts_u, open(os.path.join(out, "tts_needed.json"), "w"), indent=1)
    brief = sel["brief"] if sel else None
    p = dict(prefix=prefix, rev=rev, created=datetime.date.today().isoformat(), request=a.request or "", product=pr["name"],
             product_key=pk, product_source=pr["source"], theme=theme_key, theme_name=tname, offer=summary["offer"],
             statics=[s["name"] for s in statics], videos=videos, tts_lines=len(tts_u), tts_dupes=dupes, est_credits=est,
             budget=limit, colour_images=dict(colour_imgs), packshots=packs, brief=brief,
             winners_source=sel["source"] if sel else None, winners_note=sel["note"] if sel else None,
             winners_used=[dict(key=w["key"], name=w.get("name"), roas=w.get("roas"), action=w.get("action"))
                           for w in {x["key"]: x for x in wrows}.values()],
             unmatched_winners=sel["unmatched"] if sel else [], warnings=warnings,
             hooks=a.hooks if pm else 1)     # hooks > 1 and no "projects": the expansion below failed, render refuses it
    json.dump(p, open(os.path.join(out, "plan.json"), "w"), indent=1)
    if pm:          # Vnn -> project Pnn: H1 = this plan's video, H2.. = other hook lines/shots/cold opens, same body
        import projects
        p0 = p        # the plan without hook versions (render refuses it): written back when no version can be made

        def expand(seed, only, budget):
            try:          # (re-running restores the plan from $OUT/_before_hooks first: each call starts from this plan)
                projects.expand(out, hooks=a.hooks, seed=seed, only=only, budget=budget, quiet=True)
            except SystemExit as e:
                if e.code in (None, 0):
                    raise
                if not isinstance(e.code, int):
                    print(e.code, file=sys.stderr)
                print(f"no hook versions were made, so {os.path.join(out, 'plan.json')} can't be rendered: fix the request "
                      f"(see above) and re-run plan", file=sys.stderr)
                sys.exit(2)
            return json.load(open(os.path.join(out, "plan.json")))   # versions, projects, tts lines + credits with the hooks

        def sig(x, h):    # what makes a version another hook: its spoken line (storyboard), its cold open + label (remix)
            return (json.dumps(h.get("cold_open")), h["label"].upper()) if x["engine"] == "remix" else projects.norm(h["hook_text"])
        hseed = a.seed if a.hook_seed is None else a.hook_seed
        if ponly and hseed != a.seed:
            # a redo of some hook versions on the same bodies (same --seed): they must not repeat a version the project has
            # already (its hooks with hook seed = --seed), so the next hook seeds are tried until none does
            had = {x["id"]: {sig(x, h): h["hook"] for h in x["hooks"]} for x in expand(a.seed, None, 1e9)["projects"]}

            def repeats(p):   # the redone versions that open exactly like a version their project already has
                return [(h, x) for x in p["projects"] for h in x["hooks"] if h["hook"] != "H1" and sig(x, h) in had.get(x["id"], {})]
            tries = []
            for t in range(12):
                p = expand(hseed + t, ponly, a.budget)
                rep = repeats(p)
                tries.append((len(rep), t))
                if not rep:
                    break
            if rep:           # every hook seed repeats something: the one with the fewest repeats, named from that plan
                t = min(tries)[1]
                p = expand(hseed + t, ponly, a.budget)
                rep = repeats(p)
                desc = "; ".join(f"{h['id']} \"{h['label']}\" = " + (
                    "the one it has" if x["id"] + had[x["id"]][sig(x, h)] == h["id"] else x["id"] + had[x["id"]][sig(x, h)])
                    for h, x in rep)
                redone = [h for x in p["projects"] for h in x["hooks"] if h["hook"] != "H1"]
                if len(rep) == len(redone):
                    with open(os.path.join(out, "plan.json"), "w") as f_:
                        json.dump(p0, f_, indent=1)     # not renderable (hooks > 1, no projects): nothing to voice or render
                    print(f"--hook-seed: no new hook left for {', '.join(h['id'] for h, _ in rep)}: every option repeats a "
                          f"version its project already has ({desc}). Add hook lines (hooks.json, a product file's 'hooks', "
                          f"--lines P01_hook) or, for a winner, cold opens (python3 pipeline/winner_prep.py); nothing was "
                          f"made", file=sys.stderr)
                    sys.exit(2)
                p["warnings"].append(f"--hook-seed: no new hook left for {', '.join(h['id'] for h, _ in rep)} (repeats "
                                     f"{desc}), hook seed {hseed + t} used: leave {'it' if len(rep) == 1 else 'them'} out or "
                                     f"add hook lines (hooks.json / cold opens)")
            elif t:
                p["warnings"].append(f"--hook-seed {hseed} gave a hook these projects already have: hook seed {hseed + t} "
                                     f"used (re-plan with --hook-seed {hseed + t + 1} for another)")
            if any(h["hook"] == "H1" for x in p["projects"] for h in x["hooks"]):
                p["warnings"].append("H1 is the planned video itself: --hook-seed never changes it (its hook: --lines "
                                     "V<nn>_hook; a new body: another --seed)")
            json.dump(p, open(os.path.join(out, "plan.json"), "w"), indent=1, ensure_ascii=False)
        else:
            p = expand(hseed, ponly, a.budget)
        dupes, warnings = p.get("tts_dupes") or {}, p.get("warnings") or []
        summary.update(projects=len(p["projects"]), videos=len(p["videos"]), tts_lines=p["tts_lines"],
                       est_credits=p["est_credits"])
        vs = {v["name"]: v for v in p["videos"]}

        listing = dict(project_hooks=[])
        for x in p["projects"]:       # P01 – features: H1 [question] GIFT IDEA: "Still looking ...?" (~38 s) ...
            w, e = x.get("winner") or {}, dict(project=f"{x['id']} – {x['angle']}")
            if x["engine"] == "remix":
                e["winner"] = f"{w.get('brief_name') or w.get('key')}" + (f" (ROAS {w['roas']})" if w.get("roas") is not None else "")
            e["versions"] = []
            for h in x["hooks"]:
                r = h.get("cold_open")
                co = (f", cold open {r[0]:.1f}-{r[1]:.1f} s" if r else ", no cold open") if x["engine"] == "remix" else ""
                e["versions"].append(f"{h['hook']} [{h['type']}] {h['label']}: \"{h['hook_text']}\" "
                                     f"(~{(vs.get(h['name']) or {}).get('est_seconds') or 0:.0f} s{co})")
            listing["project_hooks"].append(e)
    else:
        listing = dict(winner_videos=[f"{v['name']} ({v['winner']['brief_name']}, " + (
            f"cold open: {v['hook_label']}" if v["winner"]["cold_open"] else f"no cold open, label {v['hook_label']}") + ")"
            for v in videos if v["engine"] == "remix"])
    print(json.dumps(dict(plan=os.path.join(out, "plan.json"), **summary, tts_needed=os.path.join(out, "tts_needed.json"),
                          tts_duplicates=len(dupes), brief=brief, winners_source=p["winners_source"], **listing,
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
            im = Image.open(f).convert("RGB")
            im._card = bs.textured(f)              # light textured backdrop: framed card, not a grey box
            bs.place_packshot(c, im, (60, 380, 1020, 1500))
            c.save(fr, quality=95)


def contact_sheet(f, out_jpg):
    L = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                             capture_output=True, text=True).stdout or 0)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", f, "-vf",
                    f"fps=24/{max(L, 1):.2f},scale=150:-1,tile=12x2", "-frames:v", "1", "-y", out_jpg])
    return L


def prefetch(out, videos):
    """Download every Drive / https source once, before parallel renders (two renders must not fetch the same file at
    once), with the same 600 MB rule the renders use (remix.loc), and transcribe clips that keep their own sound."""
    from remix import loc, words
    seen = set()
    for v in videos:
        s = json.load(open(os.path.join(out, v["name"] + ".json")))
        if v.get("engine") == "remix":
            srcs = [s["raw"]] + [x[0] for x in (s.get("reviews") or {}).get("broll", [])]
        else:
            srcs = [x[0] for blk in s["blocks"] for x in blk.get("broll", [])] + [blk["clip"] for blk in s["blocks"] if "clip" in blk]
        for src in srcs:
            src = str(src)
            if src in seen or not (DRIVE_ID.match(src) or src.startswith("http")) or os.path.exists(os.path.join(out, src)):
                continue
            seen.add(src)
            print(f"prefetch {src}", file=sys.stderr, flush=True)
            loc(out, src)
        for blk in s.get("blocks", []):
            if "clip" in blk and not blk.get("mute"):
                words(loc(out, blk["clip"]))


HARD = ("render failed", "file missing", "face", "too short")       # QA problems that keep a file out of Drive


def render_one(out, v):
    eng = v.get("engine", "storyboard")
    f = os.path.join(out, "videos", v["name"] + ".mp4")
    script = os.path.join(HERE, "remix.py" if eng == "remix" else "storyboard.py")
    tmp = os.path.join(out, "_tmp", v["id"])           # longform/recut leave their temp folders: one per video, removed after
    os.makedirs(tmp, exist_ok=True)
    r = subprocess.run([sys.executable, script, os.path.join(out, v["name"] + ".json"), "--out", f], capture_output=True, text=True,
                       env=dict(os.environ, TMPDIR=tmp))
    shutil.rmtree(tmp, ignore_errors=True)
    wav = os.path.join(out, f"_{v['name']}_audio.wav")      # the mixed sound track: inside the mp4 now
    if os.path.exists(wav):
        os.remove(wav)
    open(os.path.join(out, "qa", v["id"] + ".log"), "w").write(r.stdout + r.stderr)
    ok = r.returncode == 0 and os.path.exists(f)
    L = contact_sheet(f, os.path.join(out, "qa", v["id"] + ".jpg")) if ok else 0
    problems = [] if ok else ["render failed (see qa/%s.log)" % v["id"]]
    lo, hi = (35, 110) if eng == "remix" else (35, 95)
    if ok and L < MIN_SECONDS:
        problems.append(f"too short: {L:.1f}s (never under {MIN_SECONDS}s; want {lo}-{hi}s)")
    elif ok and not lo <= L <= hi:
        problems.append(f"length {L:.1f}s (want {lo}-{hi}s)")
    miss = r.stderr.count("anchor not found")
    if miss:
        problems.append(f"{miss} overlay anchor(s) not found (see qa/{v['id']}.log)")
    return dict(name=v["name"], id=v["id"], engine=eng, format=v.get("format"), seconds=round(L, 1), ok=ok and not problems,
                problems=problems, hard=[x for x in problems if x.startswith(HARD)])


def static_qa(out, names):
    """Every static PNG exists and shows no face (new_product.count_faces, the DNN check): a hit is a hard failure."""
    import new_product
    rep = []
    for k, n in enumerate(names):
        f = os.path.join(out, "statics", n + ".png")
        faces = new_product.count_faces(f) if os.path.exists(f) else None
        problems = (["file missing (render failed)"] if not os.path.exists(f) else
                    [f"face detected ({faces}): never a face in statics"] if faces else
                    ["render failed: the PNG can't be read (no face check possible): re-render it"] if faces is None else [])
        rep.append(dict(name=n, id=f"S{k + 1:02d}", engine="static", format=n.rsplit("_", 1)[-1], ok=not problems,
                        problems=problems, hard=[x for x in problems if x.startswith(HARD)]))
        print(json.dumps(rep[-1]), flush=True)
    return rep


def load_plan(out):
    """plan.json, refused when it asked for hook versions but has none (a plan whose projects.expand step was refused or
    undone lists the bare V01 .. videos: they must never be rendered or uploaded as if they were the batch)."""
    p = json.load(open(os.path.join(out, "plan.json")))
    if (p.get("hooks") or 1) > 1 and p["videos"] and not p.get("projects"):
        sys.exit(f"{out}/plan.json was planned with --hooks {p['hooks']} but has no hook versions (the plan was refused, or "
                 f"a projects.py expand was undone): re-run make_batch.py plan")
    return p


def render(a):
    out = os.path.abspath(a.out)
    p = load_plan(out)
    ids = only_ids(a.only, bool(p.get("projects")))
    vids = [v for v in p["videos"] if not ids or picked(v["id"], ids)]
    if ids and not vids and not any(x[:1] == "S" for x in ids):
        sys.exit(f"--only {a.only}: no video with that id in plan.json (videos: {', '.join(v['id'] for v in p['videos']) or 'none'})")
    import filecmp
    dupes = p.get("tts_dupes") or {}
    for dup, src in dupes.items():                            # identical lines were voiced once; a copy left from an
        s_, d_ = os.path.join(out, src), os.path.join(out, dup)  # earlier plan into this --out may say other words
        if os.path.exists(s_) and not (os.path.exists(d_) and filecmp.cmp(s_, d_, shallow=False)):
            shutil.copy(s_, d_)
    if ids:             # what these videos' specs use: the versions of a project share their body lines (V01_feat0.mp3 ..)
        import projects
        want = projects.voice_files(out, vids)
    else:
        want = [t["file"] for t in json.load(open(os.path.join(out, "tts_needed.json")))] + list(dupes)
    missing = sorted({dupes.get(f, f) for f in want if not os.path.exists(os.path.join(out, f))})
    if missing:
        sys.exit(f"voiceover files missing (generate them first, tts_needed.json): {missing}")
    for d in ("statics", "videos", "qa"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    swatches(out, p["colour_images"])
    rp = os.path.join(out, "qa", "report.json")
    old = {r["name"]: r for r in json.load(open(rp))} if ids and os.path.exists(rp) else {}
    report = {}
    if (not ids or any(x[:1] == "S" for x in ids)) and p["statics"]:
        import new_product
        try:
            dnn = new_product.detectors()[0]
        except Exception:  # noqa: BLE001
            dnn = None
        if dnn is None:      # every static must pass the face check before it can go to Drive
            sys.exit("the face check can't run (opencv with FaceDetectorYN is missing): pip install -q opencv-python-headless, "
                     "then re-run render")
        subprocess.run([sys.executable, os.path.join(HERE, "brand_statics.py"), os.path.join(out, "statics.json"),
                        "--outdir", os.path.join(out, "statics")], check=True)
        report.update({r["name"]: r for r in static_qa(out, p["statics"])})
    if vids:
        prefetch(out, vids)
    with cf.ThreadPoolExecutor(max(1, a.jobs)) as ex:
        for r in ex.map(lambda v: render_one(out, v), vids):
            report[r["name"]] = r
            print(json.dumps(r), flush=True)
    if os.path.isdir(os.path.join(out, "_tmp")) and not os.listdir(os.path.join(out, "_tmp")):
        os.rmdir(os.path.join(out, "_tmp"))
    order = p["statics"] + [v["name"] for v in p["videos"]]
    merged = {**old, **report}
    json.dump(sorted(merged.values(), key=lambda r: order.index(r["name"]) if r["name"] in order else 999),
              open(rp, "w"), indent=1)
    # statics grid for a quick look
    from PIL import Image
    ims = [Image.open(x) for x in (os.path.join(out, "statics", n + ".png") for n in p["statics"]) if os.path.exists(x)]
    if ims:
        for im in ims:
            im.thumbnail((270, 338))
        cols = min(6, len(ims))
        g = Image.new("RGB", (270 * cols, 338 * ((len(ims) + cols - 1) // cols)), "white")
        for k, im in enumerate(ims):
            g.paste(im, ((k % cols) * 270, (k // cols) * 338))
        g.save(os.path.join(out, "qa", "statics.jpg"), quality=88)
    sheets = []
    if p.get("projects") and vids:      # one image per project: its versions side by side, the body once, body match
        import projects
        try:
            sheets = projects.sheet(out, ",".join(sorted({v["project"] for v in vids})) if ids else None)
        except Exception as e:  # noqa: BLE001 - the renders and qa/report.json are done; say so and carry on
            print(f"project QA sheets failed ({type(e).__name__}: {e}): look at the per-version contact sheets", file=sys.stderr)
    print("QA: look at", os.path.join(out, "qa"), "(statics.jpg + one contact sheet per video" +
          (f" + one sheet per project, {', '.join(os.path.basename(s['sheet']) for s in sheets)}: its hook versions side by "
           f"side, the body once, body match under 10 = the same body" if sheets else "") + ") before uploading")


# ---------------------------------------------------------------- upload
def run_report(p, report, uploaded, skipped, name, flagged=(), notes=(), pending=()):
    L = [f"Libra Cases ads: {name}", f"Request: {p.get('request') or '-'}",
         f"Product: {p['product']} · Theme: {p.get('theme_name') or p['theme']} · Offer: {p.get('offer') or '-'} · "
         f"voiceover lines: {p.get('tts_lines')} (~{p.get('est_credits')} credits)"]
    br = p.get("brief")
    if p.get("winners_source"):
        src = {"brief": f"weekly brief '{(br or {}).get('name')}' ({(br or {}).get('age_days')} days old"
                        + (", STALE: no newer brief in Research Briefs)" if (br or {}).get("stale") else ")"),
               "codes": "the ads named in the request", "all": "all bank winners",
               "fallback": f"all bank winners ({p.get('winners_note')})"}.get(p["winners_source"], p["winners_source"])
        L.append(f"Winners from: {src}")
    if p.get("unmatched_winners"):
        L.append("Winners not remixed (a human should look):")
        L += [f"  - {u['name']} (ROAS {u.get('roas')}, {u.get('action')}): {u.get('client') or u.get('why')}"
              for u in p["unmatched_winners"]]
    st = [(n, d) for n, k, d in uploaded if k == "static"]
    L.append(f"\nStatics ({len(st)}):")
    L += [f"  {d}  static 1080x1350, layout {n.rsplit('_', 1)[-1]}" for n, d in st]
    vs = {v["name"]: v for v in p["videos"]}
    vu = [(n, d) for n, k, d in uploaded if k == "video"]
    length = lambda n: f"{report[n].get('seconds', 0):.0f} s" if report.get(n) else "length ?"  # noqa: E731
    rest = vu
    if p.get("projects"):      # one block per project (its folder), one line per version: name, length, hook
        got = dict(vu)
        ps = [x for x in p["projects"] if any(h["name"] in got for h in x["hooks"])]
        L.append(f"\nVideos ({len(vu)}): {len(ps)} project(s), each one body in up to {p.get('hooks')} hook versions (only the "
                 f"first seconds differ: the opening line, shot and label), one folder per project in Videos")
        for x in ps:
            w, n_up = x.get("winner") or {}, sum(h["name"] in got for h in x["hooks"])
            nrev = len(((vs.get(x["hooks"][0]["name"]) or {}).get("winner") or {}).get("reviews") or [])
            L.append(f"  {project_folder(x)}: " + (
                f"remix of {w.get('brief_name') or w.get('ad') or w.get('key')}" +
                (f" (ROAS {w['roas']}, {w.get('action') or '-'})" if w.get("roas") is not None else "") +
                f", {nrev} narrated reviews" if x["engine"] == "remix" else f"new storyboard video, {x.get('format') or x['angle']} angle") +
                f" · {n_up} of its {len(x['hooks'])} versions in this upload")
            for h in x["hooks"]:
                if h["name"] not in got:
                    continue
                r = h.get("cold_open")
                co = (f", cold open {r[0]:.1f}-{r[1]:.1f} s" if r else ", no cold open (the RAW from its start)") \
                    if x["engine"] == "remix" else ""
                L.append(f"    {got[h['name']]}  {length(h['name'])}, {h['hook']} [{h['type']}] {h['label']}: "
                         f"\"{h['hook_text']}\"{co}")
        inp = {h["name"] for x in p["projects"] for h in x["hooks"]}
        rest = [(n, d) for n, d in vu if n not in inp]
    else:
        L.append(f"\nVideos ({len(vu)}):")
    for n, dn in rest:
        v, r = vs.get(n, {}), report.get(n, {})
        secs = length(n)
        if v.get("engine") == "remix":
            w = v["winner"]
            hook = f'cold open "{v.get("hook_label")}": "{v.get("hook")}"' if w.get("cold_open") else f'label "{v.get("hook_label")}" (no cold open)'
            L.append(f"  {dn}  video {secs}, remix of {w.get('brief_name') or w.get('ad')}" +
                     (f" (ROAS {w['roas']})" if w.get("roas") is not None else "") +
                     f", {hook}, {len(w.get('reviews') or [])} reviews")
        else:
            L.append(f"  {dn}  video {secs}, {v.get('format', '?')}, hook: \"{v.get('hook', '')}\"")
    if flagged:
        L.append("\nUploaded, but QA flagged them (a human should look):")
        L += [f"  {s['name']}: {'; '.join(s['problems'])}" for s in flagged]
    if skipped:
        L.append("\nNot uploaded (a human must look):")
        L += [f"  {s['name']}: {'; '.join(s['problems'])}" for s in skipped]
    if pending:
        L.append(f"\nStill being made (they follow in this folder): {len(pending)}")
        L += [f"  {n}" for n in pending]
    if p.get("warnings") or notes:
        L.append("\nNotes:")
        L += [f"  - {w}" for w in list(notes) + list(p.get("warnings") or [])]
    return "\n".join(L) + "\n"


def md5(f):
    import hashlib
    h = hashlib.md5()
    with open(f, "rb") as fh:
        for chunk in iter(lambda: fh.read(2**20), b""):
            h.update(chunk)
    return h.hexdigest()


def project_folder(x):
    """Drive folder of a project's versions, inside the batch's Videos folder: 'P01 – features'."""
    return f"{x['id']} – {x['angle']}"


def upload(a):
    """Uploads the files plan.json lists (never leftovers in the folder). Hard QA failures (render failed, file
    missing, a face in a static) stay out; length / anchor flags are uploaded and listed. A same-named file already
    in Drive is skipped when identical; a newer local render with other content is uploaded under a suffix, loudly.
    Project mode: each project's versions go in their own folder Videos/<P01 – angle>."""
    out = os.path.abspath(a.out)
    p = load_plan(out)
    rp = os.path.join(out, "qa", "report.json")
    report = {r["name"]: r for r in json.load(open(rp))} if os.path.exists(rp) else {}
    up = [sys.executable, os.path.join(HERE, "drive_upload.py")]
    cfg = json.load(open(os.path.join(HERE, "config.json")))
    now = datetime.datetime.now()
    name = f"{now.date().isoformat()} – {a.name or p.get('request') or p['product']}"
    run = lambda *x: subprocess.run(up + list(x), capture_output=True, text=True, check=True).stdout.strip()  # noqa: E731
    projs = {x["id"]: x for x in p.get("projects") or []}
    vproj = {v["name"]: projs.get(v.get("project")) for v in p["videos"]}
    want = [(os.path.join(out, "statics", n + ".png"), "static", static_id(n)) for n in p["statics"]] + \
           [(os.path.join(out, "videos", v["name"] + ".mp4"), "video", v["id"]) for v in p["videos"]]
    listed = {f for f, _, _ in want}
    if a.only:        # same ids as render --only: S, V/P, P03, P03H2, 'S01,P02' (--hooks 1 plans: V03)
        ids = only_ids(a.only, bool(projs))
        want = [w for w in want if picked(w[2], ids)]
    stray = sorted(f for d, ext in (("statics", "png"), ("videos", "mp4")) for f in glob.glob(os.path.join(out, d, "*." + ext))
                   if f not in listed)
    for f in stray:
        print(f"not uploaded (not in this plan.json, left from an earlier run?): {os.path.relpath(f, out)}", file=sys.stderr)
    folder = run("mkdir", name, "--parent", cfg["drive"]["outputs_folder"]).splitlines()[-1]
    dest = {"static": run("mkdir", "Statics", "--parent", folder).splitlines()[-1],
            "video": run("mkdir", "Videos", "--parent", folder).splitlines()[-1]}
    sub, there = {}, {}

    def dest_of(n, kind):             # a project's versions: Videos/<P01 – angle>, found or made once per upload
        x = vproj.get(n) if kind == "video" else None
        if not x:
            return dest[kind]
        if x["id"] not in sub:
            sub[x["id"]] = run("mkdir", project_folder(x), "--parent", dest["video"]).splitlines()[-1]
        return sub[x["id"]]

    def in_drive(d):                  # the files already in a Drive folder, read once
        if d not in there:
            there[d] = {f["name"]: f for f in json.loads(run("ls", d) or "[]")}
        return there[d]
    uploaded, skipped, flagged, existed, renamed, notes, pending = [], [], [], [], [], [], []
    for f, kind, _ in want:
        n = os.path.splitext(os.path.basename(f))[0]
        r = report.get(n) or {}
        hard = r.get("hard", [x for x in r.get("problems", []) if x.startswith(HARD)])
        if not os.path.exists(f) and not r:       # never rendered yet (statics first, videos later): not a failure
            pending.append(n)
            continue
        if not os.path.exists(f):
            hard = hard or ["file missing (not rendered)"]
        if hard and not (a.include_flagged and kind == "video" and os.path.exists(f)):
            skipped.append(dict(name=n, problems=r.get("problems") or hard))
            print(f"skipped (QA hard failure): {n}: {'; '.join(r.get('problems') or hard)}", file=sys.stderr)
            continue
        if r.get("problems"):
            flagged.append(dict(name=n, problems=r["problems"]))
        base, h, d = os.path.basename(f), md5(f), dest_of(n, kind)
        same = next((x["name"] for x in in_drive(d).values() if x["name"].startswith(n) and x.get("md5Checksum") == h), None)
        if same:                                        # this exact file is in Drive already (maybe as _updHHMM)
            existed.append(n)
            uploaded.append((n, kind, same))
            continue
        old = in_drive(d).get(base)
        if old:
            t_drive = datetime.datetime.fromisoformat(old["modifiedTime"].replace("Z", "+00:00")).timestamp()
            if os.path.getmtime(f) <= t_drive:
                msg = f"{base}: Drive already has a different, newer file with this name: NOT uploaded"
                skipped.append(dict(name=n, problems=[msg]))
                print("WARNING " + msg, file=sys.stderr)
                continue
            base = f"{n}_upd{now:%H%M}{os.path.splitext(f)[1]}"
            msg = (f"{n}: Drive already had a different (older) file with this name; the new render went up as {base}. "
                   f"A human should delete or rename the old one (we never delete Drive files)")
            renamed.append(base)
            notes.append(msg)
            print("WARNING " + msg, file=sys.stderr)
        res = json.loads(run("upload", f, "--folder", d, "--name", base, "--skip-existing").splitlines()[-1])
        if res.get("skipped"):
            existed.append(n)
        uploaded.append((n, kind, base))
    txt = os.path.join(out, f"run report {now:%H%M}.txt")
    if a.only:
        notes.insert(0, f"this upload covers only {a.only.upper()} of the batch (other ads: earlier/later run reports here)")
    if pending:
        print(f"not rendered yet, so not uploaded now: {', '.join(pending)}", file=sys.stderr)
    open(txt, "w").write(run_report(p, report, uploaded, skipped, name, flagged, notes, pending))
    run("upload", txt, "--folder", folder)          # a fresh report every upload, never skipped
    print(json.dumps(dict(folder=f"https://drive.google.com/drive/folders/{folder}", name=name, files=len(uploaded),
                          **({"project_folders": {f"Videos/{project_folder(projs[k])}": f"https://drive.google.com/drive/folders/{d}"
                                                  for k, d in sub.items()}} if projs else {}),
                          uploaded=[d for _, _, d in uploaded], already_there=existed, renamed=renamed,
                          flagged=flagged, skipped=skipped, not_rendered_yet=pending,
                          not_in_plan=[os.path.relpath(f, out) for f in stray], report=txt),
                     indent=1, ensure_ascii=False))


def specs_copy(a):
    """plan.json, statics.json, tts_needed.json and one spec per video: what a batch is made of. Never the render files
    (_*_longform.json, *_words.json transcripts, audio, media)."""
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    os.makedirs(a.to, exist_ok=True)
    fs = ["plan.json", "statics.json", "tts_needed.json"] + [v["name"] + ".json" for v in p["videos"]]
    for f in fs:
        shutil.copy(os.path.join(out, f), os.path.join(a.to, f))
    print(json.dumps(dict(to=os.path.abspath(a.to), files=fs), indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--statics", type=int, default=0)
    pl.add_argument("--videos", type=int, default=0, help="storyboard (new-angle) videos: each one is a project of --hooks versions")
    pl.add_argument("--winner-videos", type=int, default=0, help="winner remixes (remix.py), numbered first: each one is a "
                    "project of --hooks versions (another cold open each); one project per winner unless its RAW has "
                    "--hooks more cold opens")
    pl.add_argument("--hooks", type=int, default=4, help="hook versions per video (default 4, the client's H1-H4: one body, "
                    "another opening line + shot + label per version; ids P01H1 ..); 1 = single videos V01 .. as before")
    pl.add_argument("--hook-seed", type=int, help="variation of the hook versions only (default: --seed); the same --seed "
                    "with another --hook-seed keeps every body and changes the H2-H4 hooks")
    pl.add_argument("--winners", default="latest", help="latest (newest brief) | all | brief.json | '94-H4,148-H5' | '94,148'")
    pl.add_argument("--product", help="built-in bag or a pipeline/data/products file (default: top winner's, else Hobo Bag)")
    pl.add_argument("--products-dir", help="product files folder (default pipeline/data/products, or $LC_PRODUCTS_DIR)")
    pl.add_argument("--allow-draft", action="store_true", help="build from a product file still marked draft")
    pl.add_argument("--theme", default="")
    pl.add_argument("--request", default="", help="the user's message, for the folder name and report")
    pl.add_argument("--lines", help="json with overrides: hero, bold, colours, V01_hook, V01_close ... (P01_hook = V01_hook: "
                    "project P01's H1 line)")
    pl.add_argument("--seed", type=int, default=1, help="variation: another seed gives other winner reviews (a winner project holds every "
                    "cold open its RAW has: only H1 changes; --hooks 1: other cold opens), other "
                    "storyboard hooks, feature order, reviews and B-roll, other static photos/headlines, and other hook "
                    "versions (unless --hook-seed)")
    pl.add_argument("--only", help="keep only these ads (P02 = project 2's versions, P02H3 = one version, S03, 'P02H3,S01', "
                    "V/P = all videos, S = all statics; V02 = P02; --hooks 1: V02): a redo voices, renders and uploads just them")
    pl.add_argument("--rev", type=int, default=1, help="revision of an earlier batch with the same product+theme+date: adds _v2, _v3"
                    " (plan also moves to the first _vN not in Drive yet)")
    pl.add_argument("--no-name-check", action="store_true", help="don't look in Drive for today's names (offline tests)")
    pl.add_argument("--budget", type=float, help=f"credits the request allows for voiceover, hook lines included "
                    f"(default {MAX_CREDITS})")
    pl.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    r.add_argument("--only", help="P03 (one project's versions), P03H2 (one version), V or P (all videos), S (statics only), "
                   "'S,P02H1'; --hooks 1 plans: V03")
    r.add_argument("--jobs", type=int, default=2, help="videos rendered in parallel")
    u = sub.add_parser("upload")
    u.add_argument("--out", required=True)
    u.add_argument("--name", default="")
    u.add_argument("--include-flagged", action="store_true", help="also upload videos with a hard QA failure (the file must exist)")
    u.add_argument("--only", help="as render --only: S (statics), V or P (videos), P03, P03H2, 'S01,P02'; --hooks 1 plans: V03")
    sp = sub.add_parser("specs", help="copy the batch's spec JSONs (no media, no render files) for committing")
    sp.add_argument("--out", required=True)
    sp.add_argument("--to", "--dest", dest="to", required=True, help="e.g. pipeline/recipes/daily/<YYYY-MM-DD>/<short-name>")
    a = ap.parse_args()
    {"plan": plan, "render": render, "upload": upload, "specs": specs_copy}[a.cmd](a)


if __name__ == "__main__":
    main()

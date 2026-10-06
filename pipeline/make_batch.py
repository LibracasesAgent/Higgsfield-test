#!/usr/bin/env python3
"""One-line request -> finished statics + videos in the proven house style (the 2026-10-02 test run).

The look is fixed by templates: site packshots + brand_statics layouts for statics; real clips from
pipeline/data/clip_bank.json + voiceover + captions/tags/review cards/offer/end card for videos.
No AI images or AI video are made here. The only paid step is the voiceover lines (~0.3 credits each),
which Claude generates with Higgsfield between `plan` and `render`.

  1) python3 pipeline/make_batch.py plan --statics 3 --videos 4 --product "Hobo Bag" \
         --theme "black friday" --out /tmp/run
     -> /tmp/run/plan.json, statics.json, V*.json, tts_needed.json (lines to voice, with voice ids)
  2) Claude: for each item in tts_needed.json -> Higgsfield generate_audio_batch (model text2speech_v2,
     variant elevenlabs, use_unlim false, voice from the item) -> download the mp3 to /tmp/run/<file>
  3) python3 pipeline/make_batch.py render --out /tmp/run      (statics, then videos one by one, + QA sheets)
  4) Claude looks at /tmp/run/qa/*.jpg; re-render or drop anything broken
  5) python3 pipeline/make_batch.py upload --out /tmp/run --name "Black Friday test"
     -> Drive Outputs/<date> – <name>/{Statics,Videos}; prints the folder link and the ad list

Optional --lines lines.json overrides any spoken line or headline (keys as in plan.json "text").
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BRAND_VOICE = {"voice_type": "element", "voice_id": "241459b6-b4e8-4a2a-9868-da8bcdcd0558"}
NARRATOR = {"voice_type": "preset", "voice_id": "64cf4f1a-61c8-5938-9aea-83d12b2e1d13"}

# ---------------------------------------------------------------- themes
THEMES = {
    "default": dict(
        label="", hooks=["Here's what makes the {short} different.", "Stop carrying a bag that swallows your keys.",
                         "This might be the most practical bag you'll see today."],
        hero="Meet the {short}.", bold=["SELLING", "FAST."], offer_title="50% OFF", offer_sub="+ FREE MATCHING WALLET",
        close="It's fifty percent off right now, with a free matching pouch wallet. Tap the link below.",
        sub="Final clearance: 50% off + free shipping while stock lasts.", cta="Shop now · 50% off"),
    "black friday": dict(
        label="BLACK FRIDAY", hooks=["Black Friday came early.", "This is the Black Friday deal you've been waiting for.",
                                     "Black Friday: the bag everyone asks about is half price."],
        hero="Black Friday deal.", bold=["BLACK", "FRIDAY."], offer_title="BLACK FRIDAY 50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="For Black Friday it's fifty percent off, plus a free matching pouch wallet. Tap the link below before it's gone.",
        sub="Our biggest sale of the year: 50% off + free wallet.", cta="Get the Black Friday deal"),
    "cyber monday": dict(
        label="CYBER MONDAY", hooks=["Cyber Monday: last call on our biggest sale."],
        hero="Cyber Monday deal.", bold=["CYBER", "MONDAY."], offer_title="CYBER MONDAY 50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="For Cyber Monday it's still fifty percent off, plus a free matching pouch wallet. Tap the link below.",
        sub="Last call: 50% off + free wallet.", cta="Shop the deal"),
    "christmas": dict(
        label="GIFT IDEA", hooks=["Still looking for the perfect Christmas gift?", "Most gifts end up in a drawer. Not this one."],
        hero="The gift she'll use every day.", bold=["GIFT", "SORTED."], offer_title="50% OFF",
        offer_sub="+ FREE WALLET FOR HER",
        close="It arrives with a free matching pouch wallet, and it's fifty percent off right now. Order today so it arrives in time.",
        sub="50% off + a free matching wallet in the box.", cta="Shop the gift"),
    "mothers day": dict(
        label="FOR MUM", hooks=["Still trying to figure out what to get your mum?"],
        hero="For the mum who carries everything.", bold=["FOR", "MUM."], offer_title="50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="It arrives with a free matching pouch wallet, and it's fifty percent off right now. Tap the link below.",
        sub="50% off + a free matching wallet.", cta="Shop for mum"),
    "travel": dict(
        label="TRAVEL DAY", hooks=["Travel day is where a bottomless bag really hurts."],
        hero="Made for travel day.", bold=["PACK", "SMARTER."], offer_title="50% OFF",
        offer_sub="+ FREE MATCHING WALLET",
        close="It's fifty percent off right now, with a free matching pouch wallet. Tap the link below.",
        sub="Hidden pocket, gold side zips, room for everything.", cta="Shop now · 50% off"),
}
THEME_KEYS = {"black friday": "black friday", "bfcm": "black friday", "cyber": "cyber monday", "christmas": "christmas",
              "xmas": "christmas", "gift": "christmas", "holiday": "christmas", "mother": "mothers day", "mum": "mothers day",
              "mom": "mothers day", "travel": "travel", "vacation": "travel"}


def pick_theme(text):
    t = (text or "").lower()
    for k, v in THEME_KEYS.items():
        if k in t:
            return v
    return "default"


# ---------------------------------------------------------------- products
# Spoken feature lines + on-screen tag + clip-bank picks [section, key, start].
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
PRODUCT_KEYS = {"2.0": "hobo 2.0", "hobo2": "hobo 2.0", "6-layer": "hobo 2.0", "3-piece": "3-piece set", "3 piece": "3-piece set",
                "set": "3-piece set", "vintage": "vintage", "slouchy": "slouchy", "hobo": "hobo bag"}
DOTS = {"brown": [120, 66, 36], "black": [25, 25, 25], "blue": [40, 52, 90], "grey": [110, 110, 112], "gray": [110, 110, 112],
        "burgundy": [96, 28, 44], "red": [170, 26, 36], "purple": [96, 28, 60], "chocolate": [70, 40, 30],
        "ginger": [176, 96, 40], "beige": [210, 190, 160], "apricot": [230, 170, 130], "white": [240, 236, 228],
        "pink": [222, 160, 160], "green": [70, 100, 70]}


def pick_product(text):
    t = (text or "hobo bag").lower()
    for k, v in PRODUCT_KEYS.items():
        if k in t:
            return v
    return "hobo bag"


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


# ---------------------------------------------------------------- plan
def plan(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    theme_key = pick_theme(a.theme)
    th = dict(THEMES[theme_key])
    pk = pick_product(a.product)
    pr = PRODUCTS[pk]
    over = json.load(open(a.lines)) if a.lines else {}
    rng = random.Random(a.seed)
    fill = lambda s: s.format(short=pr["short"], name=pr["name"])

    # site photos + facts
    site = os.path.join(out, "site")
    subprocess.run([sys.executable, os.path.join(HERE, "site_assets.py"), pr["site"], "--out", site], check=True)
    facts = json.load(open(glob.glob(os.path.join(site, "*_facts.json"))[0]))
    sc = facts["scores"]
    colour_imgs = [(n, f) for n, f in facts["colours"].items() if sc.get(f, 0) >= 0.6]
    fallback = [f for f in facts["clean_images"] if f not in dict(colour_imgs).values()]
    packs = [f for _, f in colour_imgs] or fallback
    rel = lambda f: os.path.relpath(f, out)
    revs = reviews_by_n()

    # ---------- statics
    feats = [f[1].title() for f in pr["features"]][:3]
    layouts = ["hero", "promo", "bold", "review", "colours", "compare", "review", "promo", "hero", "bold"]
    statics = []
    for i in range(a.statics):
        lay = layouts[i % len(layouts)]
        photo = rel(packs[i % len(packs)])
        name = f"S{i + 1:02d}_{lay}"
        if lay == "hero":
            s = dict(layout="hero", photo=photo, headline=over.get("hero", fill(th["hero"])),
                     sub=f"{feats[0].capitalize()}, {feats[1].lower()} and a free matching pouch wallet.",
                     badge={"top": "NOW", "big": "50%", "bottom": "OFF"}, cta=th["cta"])
        elif lay == "promo":
            s = dict(layout="promo", photo=photo, headline=(th["label"].title() + ": " if th["label"] else "") + f"The {pr['short']}",
                     sub="+ FREE matching pouch wallet", features=feats,
                     badge={"top": "SALE", "big": "50%", "bottom": "OFF"}, cta=th["cta"])
        elif lay == "bold":
            dots = [DOTS.get(n.lower().split()[0], [150, 150, 150]) for n, _ in colour_imgs][:7]
            s = dict(layout="bold", photo=photo, lines=over.get("bold", th["bold"]), accent_lines=[1], sub=th["sub"],
                     cta=th["cta"], dots=dots)
        elif lay == "review":
            n = pr["reviews"][(i // 6) % len(pr["reviews"])]
            s = dict(layout="review", review_n=n, photo=photo, cta=th["cta"])
        elif lay == "colours":
            ph = [dict(src=rel(f), name=n) for n, f in colour_imgs][:6] or [dict(src=rel(f), name="") for f in packs[:4]]
            s = dict(layout="colours", photos=ph, headline=over.get("colours", "Pick your colour."),
                     sub="Every colour comes with a free matching pouch wallet.", cta=th["cta"])
        else:
            s = dict(layout="compare", photo=photo, headline=f"Your everyday bag vs {pr['short']}",
                     left_title="Most bags", left=["Keys lost at the bottom", "One big empty space", "Wallet sold separately"],
                     right_title=pr["short"], right=[f.capitalize() for f in [x[1].lower() for x in pr["features"]][:3]],
                     cta=th["cta"])
        s["name"] = name
        statics.append(s)
    json.dump(dict(ads=statics), open(os.path.join(out, "statics.json"), "w"), indent=1)

    # ---------- videos
    b = bank()
    tts, videos = [], []
    formats = ["features", "reviews", "colours", "features", "reviews", "colours"]

    def line(vid, key, text, voice):
        f = f"{vid}_{key}.mp3"
        tts.append(dict(file=f, text=text, **voice))
        return f

    for v in range(a.videos):
        vid = f"V{v + 1:02d}"
        fmt = formats[v % len(formats)]
        if fmt == "colours" and len(colour_imgs) < 3:
            fmt = "features"
        hook = over.get(f"{vid}_hook") or fill(th["hooks"][v % len(th["hooks"])])
        if fmt == "colours":
            hook = over.get(f"{vid}_hook") or ("Be honest. Which colour are you?" if theme_key == "default"
                                                else fill(th["hooks"][0]) + " Which colour are you?")
        hc = pr["hook_clips"][v % len(pr["hook_clips"])]
        blocks = [dict(vo=line(vid, "hook", hook, BRAND_VOICE), broll=[[clip(b, hc[0], hc[1]), hc[2], 1.0]])]
        ov = [dict(type="label", text=th["label"] or {"features": "LOOK CLOSER", "reviews": "REAL REVIEWS",
                                                        "colours": "WHICH ONE?"}[fmt], block=0, at=0.1, dur=1.8)]
        fs = pr["features"]
        k0 = (v * 2) % len(fs)
        chosen = [fs[(k0 + j) % len(fs)] for j in range(3 if fmt == "features" else 2)]

        def add_features():
            for j, (txt, tag, picks) in enumerate(chosen):
                blocks.append(dict(vo=line(vid, f"feat{j}", txt, BRAND_VOICE),
                                   broll=[[clip(b, s_, k_), t_, 1.0] for s_, k_, t_ in picks]))
                ov.append(dict(type="tag", text=tag, block=len(blocks) - 1, at=0.15, dur=2.6))

        def add_reviews(count):
            ns = [pr["reviews"][(v + j) % len(pr["reviews"])] for j in range(count)]
            for j, n in enumerate(ns):
                r = revs[n]
                who, q = SPOKEN.get(n, (r["name"].split()[0].rstrip("."), short_quote(r["text"]).rstrip(".!")))
                spoken = ("Here's what customers say. " if j == 0 else "") + f"{who}: {q}."
                br = pr["broll"][(v + j) % len(pr["broll"])]
                blocks.append(dict(vo=line(vid, f"rev{j}", spoken, NARRATOR), broll=[[clip(b, br[0], br[1]), br[2], 1.0]]))
                ov.append(dict(type="review", n=n, block=len(blocks) - 1, at=0.1, until_block_end=True))

        def add_customer():
            if pr["customer"]:
                s_, k_, a_, e_ = pr["customer"][v % len(pr["customer"])]
                blocks.append(dict(clip=clip(b, s_, k_), range=[a_, e_]))
                ov.append(dict(type="label", text="REAL CUSTOMER", block=len(blocks) - 1, at=0.3, dur=2.0))

        if fmt == "features":
            add_features(); add_customer(); add_reviews(2)
        elif fmt == "reviews":
            add_reviews(3); add_customer(); add_features()
        else:
            sw = []
            for n, f in colour_imgs[:6]:
                fr = os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")
                sw.append((n, fr))
            names = [n for n, _ in sw]
            ctext = ", ".join(names[:-1]) + ", or " + names[-1] + ". Every colour comes with a free matching pouch wallet."
            blocks.append(dict(vo=line(vid, "colours", ctext, BRAND_VOICE),
                               broll=[[os.path.relpath(f, out), 0, 1.0, {"zoom": [1.0, 1.06]}] for _, f in sw]))
            ov.append(dict(type="tag", text=" · ".join(n.upper() for n in names[:4]), block=len(blocks) - 1, at=0.1, dur=3.0))
            add_customer(); add_reviews(2); add_features()
        close = over.get(f"{vid}_close", th["close"])
        cb = pr["broll"][v % len(pr["broll"])]
        blocks.append(dict(vo=line(vid, "close", close, BRAND_VOICE),
                           broll=[[rel(packs[v % len(packs)]), 0, 1.0, {"zoom": [1.0, 1.06]}], [clip(b, cb[0], cb[1]), cb[2], 1.2]]))
        spec = dict(blocks=blocks, overlays=ov, end_title=pr["end"],
                    offer=dict(block=len(blocks) - 1, word="50", title=th["offer_title"], sub=th["offer_sub"]),
                    keywords=["50%", "free", "wallet", "hidden", "pocket", "leather", "black", "friday", "gift"])
        name = f"{vid}_{fmt}"
        json.dump(spec, open(os.path.join(out, name + ".json"), "w"), indent=1)
        videos.append(dict(name=name, format=fmt, hook=hook))

    json.dump(tts, open(os.path.join(out, "tts_needed.json"), "w"), indent=1)
    p = dict(created=datetime.date.today().isoformat(), request=a.request or "", product=pr["name"], theme=theme_key,
             statics=[s["name"] for s in statics], videos=videos, tts_lines=len(tts),
             est_credits=round(0.35 * len(tts), 1), colour_images=dict(colour_imgs), packshots=packs)
    json.dump(p, open(os.path.join(out, "plan.json"), "w"), indent=1)
    print(json.dumps(dict(plan=os.path.join(out, "plan.json"), statics=len(statics), videos=len(videos),
                          tts_needed=os.path.join(out, "tts_needed.json"), tts_lines=len(tts), est_credits=p["est_credits"],
                          theme=theme_key, product=pr["name"]), indent=1))


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


def render(a):
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    missing = [t["file"] for t in json.load(open(os.path.join(out, "tts_needed.json")))
               if not os.path.exists(os.path.join(out, t["file"]))]
    if missing:
        sys.exit(f"voiceover files missing (generate them first): {missing}")
    os.makedirs(os.path.join(out, "statics"), exist_ok=True)
    os.makedirs(os.path.join(out, "videos"), exist_ok=True)
    os.makedirs(os.path.join(out, "qa"), exist_ok=True)
    swatches(out, p["colour_images"])
    subprocess.run([sys.executable, os.path.join(HERE, "brand_statics.py"), os.path.join(out, "statics.json"),
                    "--outdir", os.path.join(out, "statics")], check=True)
    report = []
    for v in p["videos"]:
        if a.only and not v["name"].startswith(a.only):
            continue
        f = os.path.join(out, "videos", v["name"] + ".mp4")
        r = subprocess.run([sys.executable, os.path.join(HERE, "storyboard.py"), os.path.join(out, v["name"] + ".json"),
                            "--out", f], capture_output=True, text=True)
        open(os.path.join(out, "qa", v["name"] + ".log"), "w").write(r.stdout + r.stderr)
        ok = r.returncode == 0 and os.path.exists(f)
        L = contact_sheet(f, os.path.join(out, "qa", v["name"] + ".jpg")) if ok else 0
        problems = [] if ok else ["render failed (see qa/*.log)"]
        if ok and not 25 <= L <= 95:
            problems.append(f"length {L:.0f}s")
        if "anchor not found" in r.stderr:
            problems.append("an overlay anchor was not found")
        report.append(dict(name=v["name"], seconds=round(L, 1), ok=ok and not problems, problems=problems))
        print(json.dumps(report[-1]), flush=True)
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
    json.dump(report, open(os.path.join(out, "qa", "report.json"), "w"), indent=1)
    print("QA: look at", os.path.join(out, "qa"), "(statics.jpg + one contact sheet per video) before uploading")


# ---------------------------------------------------------------- upload
def upload(a):
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    up = [sys.executable, os.path.join(HERE, "drive_upload.py")]
    cfg = json.load(open(os.path.join(HERE, "config.json")))
    name = f"{datetime.date.today().isoformat()} – {a.name or p.get('request') or p['product']}"
    run = lambda *x: subprocess.run(up + list(x), capture_output=True, text=True, check=True).stdout.strip()
    folder = run("mkdir", name, "--parent", cfg["drive"]["outputs_folder"]).splitlines()[-1]
    st = run("mkdir", "Statics", "--parent", folder).splitlines()[-1]
    vd = run("mkdir", "Videos", "--parent", folder).splitlines()[-1]
    n = 0
    for f in sorted(glob.glob(os.path.join(out, "statics", "*.png"))):
        run("upload", f, "--folder", st); n += 1
    for f in sorted(glob.glob(os.path.join(out, "videos", "*.mp4"))):
        run("upload", f, "--folder", vd); n += 1
    print(json.dumps(dict(folder=f"https://drive.google.com/drive/folders/{folder}", name=name, files=n)))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--statics", type=int, default=0)
    pl.add_argument("--videos", type=int, default=0)
    pl.add_argument("--product", default="Hobo Bag")
    pl.add_argument("--theme", default="")
    pl.add_argument("--request", default="", help="the user's message, for the folder name and report")
    pl.add_argument("--lines", help="json with overrides: hero, bold, colours, V01_hook, V01_close ...")
    pl.add_argument("--seed", type=int, default=1)
    pl.add_argument("--out", required=True)
    r = sub.add_parser("render")
    r.add_argument("--out", required=True)
    r.add_argument("--only")
    u = sub.add_parser("upload")
    u.add_argument("--out", required=True)
    u.add_argument("--name", default="")
    a = ap.parse_args()
    {"plan": plan, "render": render, "upload": upload}[a.cmd](a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""One-line request -> finished statics + videos in the proven house style (the 2026-10-02 test run).

The look is fixed by templates: site packshots + brand_statics layouts for statics; real clips from
pipeline/data/clip_bank.json + voiceover + captions/tags/review cards/offer/end card for videos; winner
videos re-edit the winning RAW (pipeline/remix.py) with a new cold open, the proven body intact (plan --winner-reviews
adds the old narrated review section). One voice per storyboard video (the brand voice; reviews said about the customer
with her card on screen; a real customer speaks only in her own clip, introduced by the narrator), no B-roll shot over ~4 s,
every cut on a sentence end (pipeline/projects.py cadence audits the clip bank).
No free-form AI images or video are made here. The paid steps are the voiceover lines (~0.3 credits each) and the AI scene
stills / clips of the real bag that plan lists in ai_needed.json (ai_gen.py, owner 2026-10-20; 100 credits per batch in total),
which Claude generates with Higgsfield between `plan` and `render`.

New storyboard videos (catalog, new-product and winners-fill projects) are in the ugc format since 2026-10-14 (the owner's
measurement of the top-impression ads): ugc_script.py writes one script per project in the 'you' voice (a hook, 5-9 chapters,
the offer last), the board is the hook block + one block per chapter ("mode": "ugc": storyboard.py voice-prepares every take,
cuts the picture where each phrase starts and masters the mix to -14 LUFS) with footage matched to the words of each phrase
(the product's feature picks, clip_bank moments, clip_index.json library clips of the built-in bags, photos), 55-80 s,
one voice take per chapter (the project's 4 hook versions share them; H2-H4 are the script's alt_hooks, one short voice line
each), numbered chapters, reviews on screen at most 3 s; render adds scorecard.py's line to every video's QA. --classic keeps the
earlier formats (showcase / features / reviews / colours / lifestyle / offer, 40-60 s) and the old static cycle, --story the
classic story format; pipeline/data/voice.json {"voice_type", "voice_id", "speed"} overrides the brand voice and the take speed.

Videos are delivered as PROJECTS, the client's agency format ('ACH - MAX - 94 - H4' = project 94, hook 4): every
planned video is one body (story, features, reviews, offer, end card) made in --hooks versions H1-H4 (default 4) that
differ only in the first 2-5 s: the spoken opening line, the opening shot and the hook label; a winner remix gets
another cold open per version. pipeline/projects.py makes the versions (hook lines: pipeline/data/hooks.json). Ids
P01H1 .. P01H4, names LC_<date>_<Product>_<Theme>_P01_H1_<angle>. --hooks 1 = single videos V01, V02 ... as before.

  1) python3 pipeline/make_batch.py plan --statics 3 --videos 4 --product "Hobo Bag" \
         --theme "black friday" --out /tmp/run [--hooks 4] [--classic]
         [--winner-videos 6 [--winners latest | "94-H4,148-H5" | "94,148" | brief.json | all]]
     -> /tmp/run/plan.json (videos: one entry per version; projects: P01.. with their hooks), statics.json, one spec
        <name>.json per version, tts_needed.json (lines to voice, with voice ids; the H2-H4 hook lines included)
     Winner videos come first (P01..), one project per winner in brief order: a project holds up to --hooks of its
     winner's cold opens, so a winner gets a 2nd project only when its RAW has --hooks more (else the extra projects
     are left out with a warning: they would repeat its openings; --hooks 1: cycling, each reuse gets another cold open);
     a winner keeps its RAW body (0 voiceover lines; 15-110 s); storyboard videos follow (formats: showcase when the
     product has real customer clips, then features, reviews, colours). --product omitted: the top winner's product, else Hobo Bag.
     Winner openings that already went out in a committed batch (pipeline/recipes/daily) are named in a warning.
     Products: the built-in bags below or pipeline/data/products/<slug>.json (new_product.py); an unknown or
     draft product exits 2. Refuses (exit 2) when the voiceover, hook lines included, would cost more than 40
     credits (--budget X).
     Then the Meta ad copy of every ad (pipeline/ad_copy.py -> ad_copy.csv / ad_copy.json: primary texts, headlines,
     description, CTA; a project's versions share theirs) and the compliance check of every text of the batch, the copy
     included (pipeline/compliance.py -> compliance.json: no health/medical, drugs, politics, religion, blood or
     violence, only true claims): a problem exits 2 with the lines listed (render refuses the $OUT until it passes).
     Statics: brand_statics layouts in a cycle; the Hobo Bag leans on the bottom-of-funnel ones (offer, stars, checklist).
  2) Claude: for each item in tts_needed.json -> Higgsfield generate_audio_batch (model text2speech_v2,
     variant elevenlabs, use_unlim false, voice from the item) -> download the mp3 to /tmp/run/<file>
     (identical lines are listed once; render copies them to the other file names; the versions of a project share
     their body lines, so only the hook lines are new)
  3) python3 pipeline/make_batch.py render --out /tmp/run [--jobs 2] [--only P03 | P03H2 | V | S]
     (statics, then videos in parallel, + QA: qa/statics.jpg, one contact sheet per version qa/P01H1.jpg ..., one
     sheet per project qa/P01.jpg (its versions side by side, the body once, body match < 10 = same body), and
     qa/report.json; a version whose body differs from H1's, body match 10+, is flagged there: still uploaded, listed)
  4) Claude looks at /tmp/run/qa/*.jpg; re-render (--only) or drop anything broken
  5) python3 pipeline/make_batch.py upload --out /tmp/run --name "Black Friday test" [--only S|V|P03|P03H2] [--include-flagged]
     -> Drive Outputs/<plan date> – <name>/{Statics, Videos/<P01 – angle>/ (one folder per project)} + "run report <HHMM>.txt"
     (one block per project: each version's hook type, label, line and length) + <prefix>_ad_copy.csv (the copy rows of
     the ads in the folder); prints the folder link, the ad copy link and the ad list
     (only the files plan.json lists; hard QA failures stay out: render failed, file missing, a face in a static, a
     video under its floor: 25 s storyboard, 15 s winner;
     length / anchor / cadence flags are uploaded and listed in the report; ads not rendered yet are listed as still
     being made)
  6) python3 pipeline/make_batch.py specs --out /tmp/run --dest pipeline/recipes/daily/<date>/<name>   (JSON to commit,
     ad_copy.json and compliance.json included)
A redo of a whole project: the same plan command with --seed <N+1> --rev 2 --only P02 (voices, renders and uploads only
P02's versions; with --hooks 1: --only V02). A redo of one version on the same body: the same plan command (same
--seed) with --hook-seed <N+1> --rev 2 --only P02H3. --only V02 in project mode means P02.

Pipelines (plan --pipeline, default catalog = the flags above as they are):
  winners      the weekly brief's winners: winner projects (brief order, as --winner-videos; --projects N = N of them) +
               statics of the winners' product. Fewer winner projects possible than asked (unmatched winners, a winner
               gets one project per --hooks cold opens) -> the rest are new-angle storyboard projects of that product
               ("fill", named in a warning; --no-fill: only the winner projects).
  new-product  --new-product "<Drive New Products folder>" | next | latest: new_product.ensure() makes or reuses its
               product file from the folder only (photos, clips, notes; never libracases.com), then plans it as
               --product <key> (its own file even when the key is a built-in bag's); plan.json "intake" says what was
               read. --refresh-product redoes the intake. A draft (problems) exits 2. --new-product alone implies this
               pipeline. --seed defaults to 1 + the batches its product file records (not with --only), so another
               batch of the product gets other statics and hooks; up to 7 feature lines make its videos ~40-60 s.
               Its video projects take one angle each: features, colours, showcase (detail photos first), lifestyle
               (worn photos first), offer; its packshots get the notes' colour names by shade (match_colours, only a
               sure match) for the colours static and swatches.
  No count given (none of --statics/--videos/--winner-videos/--projects) in winners / new-product, or --batch in any
  pipeline: a BATCH = 20 statics + 5 projects x --hooks 4 = 20 videos (--batch fills only the counts not given).
  winners: --videos N = --projects N (winner projects).
  upload puts winners in Outputs/Winners/<date> – <name>, new products in Outputs/New Products/<date> – <name> (and
  records the batch in the product file's "tests"), catalog in Outputs/<date> – <name>.
Product-file photos are picked as ["photo", "P<n>"] (= its photos[n]; a face: skipped; "statics": false = part of a head:
videos only); product-file photos and clips that are not 9:16 are framed whole ("fit": recut.py; under the close higher,
fit_y CLOSE_FIT_Y) in the videos and their hook versions; built-in footage is cropped as before. A later session downloads a
photo by its Drive id and converts it as the intake did (new_product.to_jpg).

Optional --lines lines.json overrides headlines and spoken lines: hero, bold, colours, V03_hook / V03_close (video id;
P03_hook / P03_close the same: the H1 line and the close every version shares) or B01_hook / B01_close (storyboard 1,
whatever its number after the winner videos); unused keys are warned about.
Offers come from libracases.com at plan time (each product's own %, a gift only when the site says so; a product file
with no site page: its own offer, from the client's notes); names move to the first _vN that is not in Drive yet.
"""
import argparse
import collections
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
import ai_gen  # noqa: E402  (AI scene stills / clips, owner 2026-10-20)
import novelty  # noqa: E402

BRAND_VOICE = {"voice_type": "element", "voice_id": "241459b6-b4e8-4a2a-9868-da8bcdcd0558"}
NARRATOR = {"voice_type": "preset", "voice_id": "64cf4f1a-61c8-5938-9aea-83d12b2e1d13"}
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
MAX_CREDITS = 40
MIN_SECONDS = 25   # a storyboard shorter than this is never made (35-95 s is the QA range; 25-35 s is uploaded, flagged)
PLAN_SECONDS = MIN_SECONDS + 2   # plan leaves a storyboard out when it estimates under this: the real voice runs a second or
#                                  two off the words / 2.7 estimate, and a render under MIN_SECONDS is never uploaded
QA_SECONDS = {"storyboard": (35, 95), "remix": (15, 110),    # a winner body is as long as it is: RAW + cold open, no
              "story": (60, 130),                             # padding (113-H2 runs ~18 s); never under the floor. story:
              "ugc": (55, 85)}                                # the classic 1.5-2 min storytelling format (Julian, 2026-10-09);
FLOOR = {"storyboard": MIN_SECONDS, "remix": 15}                # ugc: the default storyboard format (owner 2026-10-14: 55-80 s)
UGC_ANGLE = dict(n_things="things", demo="demo", stop_x="stop", travel="travel", value="value")   # ugc_script angle -> the name part
AI_SHOTS_MAX = 5      # AI clips in one ugc video (of ~30 shots): the real footage stays the base
UGC_WPS = 2.75      # words per second of a voice take before the speed-up (ugc_script.VPS / storyboard.VOICE_SPEED)
UGC_SPEED = 1.12    # storyboard.VOICE_SPEED: the voice takes are sped up this much
UGC_TAKE = 0.075    # silence storyboard.voice_prep keeps at the two ends of a take (KEEP_HEAD + KEEP_TAIL)
UGC_JOIN = 0.08     # storyboard.UGC_PAD: the pad after a take
UGC_HOOK_PAD = 0.2  # storyboard.UGC_HOOK_PAD
UGC_END_PAD = 0.6   # storyboard.END_PAD (remix.TAIL + 0.2)
VOICE_FILE = os.path.join(HERE, "data", "voice.json")   # optional {"voice_type", "voice_id", "speed"}: the lead's choice of voice
PIPELINES = ("catalog", "winners", "new-product")
BATCH = dict(statics=20, projects=5)   # the owner (2026-10-13): no numbers = 20 statics + 5 projects x 4 hooks = 20 videos
FIT_CLIP = "auto"   # product-file clips not shot 9:16: recut picks a flat backdrop (light studio border) or a blur
CLOSE_FIT_Y = 0.30  # a framed square under the close: y 36-1116, above the end card band (1120-1510)
STORY_WORDS = re.compile(r"\bstor(?:y|ies|ytelling)\b|\blong(?:er)?[- ](?:video|ad|form|version)s?\b|"
                         r"\b(?:1[.,]5|2|two)[- ]?min(?:ute)?s?\b", re.I)   # a request for the story format

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
        sub="{P} off the {short}[ + {gift_w}].", cta="Get the Black Friday deal",   # (never "our biggest sale": the % runs
        #                                           all year; the bold headline already says BLACK FRIDAY: not twice)
        lead="This is our Black Friday deal."),
    "cyber monday": dict(
        label="CYBER MONDAY", hooks=["Cyber Monday: last call for {P} off."],
        hero="Cyber Monday deal.", bold=["CYBER", "MONDAY."], offer_title="CYBER MONDAY {P} OFF", offer_sub="[{card}]",
        close="For Cyber Monday it's still {off_sp}[, plus {gift_sp}]. Tap the link below.",
        sub="Last call: {P} off[ + {gift_w}].", cta="Shop the deal", lead="Cyber Monday is your last call."),
    "cyber week": dict(
        label="CYBER WEEK", hooks=["Cyber Week: {P} off is still on."],
        hero="Cyber Week deal.", bold=["CYBER", "WEEK."], offer_title="CYBER WEEK {P} OFF", offer_sub="[{card}]",
        close="For Cyber Week it's {off_sp}[, plus {gift_sp}]. Tap the link below.",
        sub="{P} off the {short}[ + {gift_w}].", cta="Shop the deal", lead="This is our Cyber Week deal."),
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
            ("Inside, divided compartments, so nothing sinks to the bottom.", "SMART COMPARTMENTS",     # (never the real
             [["hobo_bag", "black_detail", 9.5], ["hobo_bag", "black_detail", 16.0]]),               # customer's clip:
            ("Two straps, so you can wear it on the shoulder, as a handbag, or crossbody.", "3 WAYS TO WEAR",   # she talks
             [["hobo_3piece_set", "brown_room_outside", 21.0], ["hobo_3piece_set", "brown_room_outside", 84.0]]),
            ("Soft, water-resistant leather that looks expensive and only gets better with time.", "SOFT LEATHER",
             [["hobo_bag", "details_macro_4k", 0.5], ["hobo_bag", "metal_details_4k", 4.0]]),
        ],
        customer=[["hobo_bag", "testi_black", 14.16, 25.43], ["hobo_bag", "testi_black", 26.0, 40.57],   # whole sentences
                  ["hobo_bag", "testi_black", 41.1, 52.73]],                                          # (projects.py cadence)
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
        customer=[["vintage_bag", "becky_testimony", 4.76, 13.3], ["vintage_bag", "becky_testimony", 15.32, 21.5],
                  ["vintage_bag", "becky_testimony", 31.98, 38.85], ["vintage_bag", "becky_testimony", 39.1, 47.8]],
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
COLOUR_REF = dict(DOTS, coffee=[78, 46, 34], espresso=[60, 40, 30], mocha=[110, 80, 60], cream=[236, 226, 206],
                  ivory=[240, 234, 218], tan=[196, 150, 108], camel=[190, 140, 90], caramel=[180, 120, 70],
                  cognac=[150, 75, 35], khaki=[180, 170, 130], navy=[30, 40, 70], taupe=[140, 125, 110],
                  nude=[220, 185, 160], silver=[190, 190, 195], gold=[200, 165, 90], orange=[220, 110, 40],
                  yellow=[230, 200, 70], olive=[110, 110, 60], rose=[210, 140, 150])   # (match_colours only)


def lab(rgb):
    """sRGB 0-255 -> CIELAB (D65): distances in it are what the eye sees."""
    import numpy as np
    c = np.asarray(rgb, float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    x, y, z = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ c / [0.9505, 1.0, 1.089]
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return np.array([116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))])


def bag_rgb(f):
    """Median colour of the product in a studio packshot (pixels away from the backdrop of its top/bottom rows)."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(f).convert("RGB").resize((200, 200))).reshape(-1, 3).astype(float)
    bg = np.median(np.concatenate([a[:200], a[-200:]]), axis=0)
    m = a[np.abs(a - bg).max(axis=1) > 40]
    return [int(x) for x in np.median(m, axis=0)] if len(m) > 800 else None


def match_colours(files, names):
    """Which packshot shows which colour the client's notes list: the one-to-one assignment with the smallest colour
    distance (CIELAB). Only a sure one is used (every pair within 25, the next best assignment 10 worse), as [(name,
    file, rgb)] in the notes' order; else ([], why). A colour name with no reference colour is not matched."""
    def ref(n):
        n = n.lower().strip()
        return COLOUR_REF.get(n) or next((COLOUR_REF[w] for w in re.findall(r"[a-z]+", n) if w in COLOUR_REF), None)
    names = [n for n in names if ref(n)][:8]
    got = [(f, bag_rgb(f)) for f in files[:8]]
    got = [(f, c) for f, c in got if c]
    if len(names) < 2 or len(got) < 2:
        return [], f"{len(got)} packshot(s), {len(names)} colour name(s) with a known shade"
    D = [[float(sum((lab(c) - lab(ref(n))) ** 2) ** 0.5) for n in names] for _, c in got]
    if len(got) <= len(names):        # every photo gets a name / every name a photo, whichever runs out first
        cands = (tuple(zip(range(len(got)), ns)) for ns in itertools.permutations(range(len(names)), len(got)))
    else:
        cands = (tuple(zip(ps, range(len(names)))) for ps in itertools.permutations(range(len(got)), len(names)))
    opts = sorted((sum(D[i][j] for i, j in pairs), pairs) for pairs in cands)
    best = opts[0]
    worst = max(D[i][j] for i, j in best[1])
    margin = next((c - best[0] for c, _ in opts[1:] if c - best[0] > 1e-6), 99)
    if worst > 25 or margin < 10:
        return [], f"no sure match (worst pair {worst:.0f}, next assignment {margin:.0f} worse)"
    by = {j: i for i, j in best[1]}
    return [(names[j], got[by[j]][0], got[by[j]][1]) for j in range(len(names)) if j in by], ""


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
    from resolve_offer() at plan time. Product files never carry reviews of other products or unbacked claims.
    A new-product plan's own file wins over a built-in bag of the same key ($LC_PRODUCT_FILE: a folder 'Hobo Bag')."""
    import new_product
    w = warnings if warnings is not None else []
    if pk in PRODUCTS and not (pk in files and os.environ.get("LC_PRODUCT_FILE") == pk):
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


THIRD = {   # storyboards: the brand voice says what each customer wrote (one voice per video: the narrator never speaks as
    # the customer); the verbatim review card is on screen. third() checks every word is backed by the review.
    1: "One customer says it holds everything they need for their daily outings.",
    2: "One customer says the quality is amazing, and it fits all their essentials.",
    3: "One customer says it holds all their daily essentials and looks chic.",
    4: "One customer says the quality is fantastic, and it fits all their essentials perfectly.",
    5: "One customer calls it a standout purchase, with quick shipping and good quality.",
    6: "Mercy calls it the best bag for travel and every day use.",
    7: "Carol calls it the best bag she has ever bought.",
    8: "Beverly says it looks expensive, but the price was so nice.",
    9: "Felicia got this bag for her daughter for Christmas, and says she adores it.",
    10: "Margie says it holds many things.",
    11: "Sarah says the lockable zippers and RFID lining are genuinely incredible.",
    12: "Jenny says it's spacious, lightweight, and super functional, with lots of pockets.",
}
FRAMING = set("one customer customers says say calls call it it's its she her they their them has have and a an the with "
              "is was but".split())     # words a third-person line may add around the review's own words


def third(n, revs):
    """Brand-voice line about review n: THIRD[n] when every other word of it is in the review text, else a plain
    pointer to the card ("Here's what Carol says.")."""
    r = revs[n]
    who = r["name"].split()[0].rstrip(".")
    who = "one customer" if len(who) < 2 else who
    s = THIRD.get(n)
    if s and set(flat(s).split()) - FRAMING - {who.lower()} <= set(flat(r["text"]).split()) | {"it's"}:
        return s
    if s:
        print(f"THIRD[{n}] says more than review {n}: using a pointer to its card", file=sys.stderr)
    return f"Here's what {who} says."


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


def voice_cfg():
    """(voice, speed) of the ugc videos: the brand voice and UGC_SPEED, unless pipeline/data/voice.json says otherwise
    ({"voice_type", "voice_id", "speed": 0.8-1.25}; every key optional: the lead's choice after a listening test)."""
    try:
        d = json.load(open(VOICE_FILE))
    except (OSError, ValueError):
        d = {}
    d = d if isinstance(d, dict) else {}
    voice = dict(BRAND_VOICE)
    if isinstance(d.get("voice_type"), str) and isinstance(d.get("voice_id"), str) and d["voice_type"] and d["voice_id"]:
        voice = dict(voice_type=d["voice_type"], voice_id=d["voice_id"])
    try:
        speed = min(max(float(d.get("speed") or UGC_SPEED), 0.8), 1.25)
    except (TypeError, ValueError):
        speed = UGC_SPEED
    return voice, speed


def est_ugc(spec, texts):
    """Length of a ugc board before any voiceover exists: each take's words / (UGC_WPS x voice_speed) + the silence kept at
    its ends + the pad after it (the hook's UGC_HOOK_PAD, the last take's UGC_END_PAD, else the board's pad)."""
    sp, last, t = spec.get("voice_speed") or UGC_SPEED, len(spec["blocks"]) - 1, 0.0
    for k, blk in enumerate(spec["blocks"]):
        if "vo" not in blk:
            t += blk["range"][1] - blk["range"][0]
            continue
        pad = blk.get("pad", spec.get("hook_pad", UGC_HOOK_PAD) if k == 0 and last else spec.get("pad", UGC_JOIN))
        t += len(texts.get(blk["vo"], "").split()) / (UGC_WPS * sp) + UGC_TAKE + (max(pad, UGC_END_PAD) if k == last else pad) + \
            (blk.get("hold", 0.0) if 0 < k < last else 0.0)
    return round(t, 1)


def est_seconds(spec, texts, rw=None):
    """Rough ad length before any voiceover exists: words / WPS for voiced parts, real ranges for RAW and clips (ugc boards:
    est_ugc)."""
    if spec.get("mode") == "ugc":
        return est_ugc(spec, texts)
    if "raw" in spec:
        e = next((x for x in (rw or {}).values() if x.get("id") == spec["raw"]), {})
        import remix
        body = (spec.get("end") or e.get("dur") or 0) - (spec.get("start") or 0) - sum(
            b - a for a, b in list(spec.get("cut") or []) + remix.claim_ranges(spec))
        co = spec.get("cold_open")
        rv = spec.get("reviews")
        return round(body + (co[1] - co[0] if co else 0) + (len(rv["text"].split()) / WPS + 0.4 if rv else 0), 1)
    t = 0.45                          # storyboard: the hook's and the last line's longer pauses (HOOK_PAD, END_PAD)
    for blk in spec["blocks"]:
        t += len(texts.get(blk["vo"], "").split()) / WPS + 0.25 + blk.get("hold", 0.0) if "vo" in blk else \
            blk["range"][1] - blk["range"][0]
    return round(t, 1)


KW_SYN = {"zipper": "zip", "zippers": "zip", "zips": "zip", "zipped": "zip", "hanging": "hang", "hangs": "hang", "hook": "hang",
          "chair": "hang", "macro": "detail", "details": "detail", "closeup": "detail", "close": "detail", "interior": "inside",
          "open": "inside", "opened": "inside", "opens": "inside", "opening": "inside", "packing": "pack", "packed": "pack",
          "unpack": "pack", "unpacking": "pack", "worn": "wear", "wearing": "wear", "wears": "wear", "walking": "walk",
          "street": "walk", "outside": "walk", "outdoors": "walk", "colours": "colour", "color": "colour", "colors": "colour",
          "lineup": "colour", "carousel": "colour", "stitching": "stitch", "stitches": "stitch", "desk": "table",
          "hands": "hand", "arms": "hand", "bags": "bag", "keys": "key", "lipstick": "item", "things": "item", "stuff": "item",
          "items": "item", "essentials": "item", "adjust": "strap", "adjustable": "strap",
          "crowd": "walk", "crowds": "walk", "crowded": "walk", "busy": "walk", "train": "walk", "subway": "walk", "station": "walk",
          "commute": "walk", "airport": "walk", "trip": "walk", "checkout": "shop", "store": "shop", "cafe": "coffee",
          "restaurant": "coffee", "lunch": "coffee"}   # footage keyword folding (kw_terms); the situations a problem line names -> the footage
#                                                       that has the bag out in the world (the library has little: see PLAYBOOK)
KW_STOP = set("the a an and or of to in on for with your you it its this that is are be at by as from up out into so just no "
              "not more most all any can will one two get got has have had was were than then too very only".split())


def kw_terms(text):
    """The footage keywords of a text: lower-case words with plurals and near-synonyms folded (zippers -> zip, hanging -> hang),
    small words dropped. Footage notes and a script's phrases are matched on these."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        w = KW_SYN.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = KW_SYN.get(w[:-1], w[:-1])
        if len(w) > 2 and w not in KW_STOP:
            out.add(w)
    return out


HOOK_MOVE = {"hand", "zip", "pocket", "inside"}   # an opening shot that moves (hands in the bag, a zip); a bag hanging or a person standing does not


def hook_type_of(text):
    """ugc hook type of a line nobody typed (a theme hook): question / price / promise."""
    if (text or "").strip().endswith("?"):
        return "question"
    return "price" if re.search(r"%|\bpercent\b|half price|\bdeals?\b|\bsales?\b|\boff\b|\bprice\b", text or "", re.I) else "promise"


def ugc_slots(text, speed=UGC_SPEED, pad=UGC_JOIN):
    """[(the words, shot pieces)] one entry per shot of a ugc take as storyboard will cut it: the take's words timed at the
    estimated pace, phrase_cuts / shot_groups / ugc_pieces of storyboard (a long group is split into pieces: the 2nd, 3rd ...
    take a spare shot). plan matches the footage to these words and orders a block's picks by them."""
    import storyboard as sb
    ws, t = [], 0.0
    for w in text.split():
        ws.append(dict(w=w, s=round(t, 3), e=round(t + 1 / (UGC_WPS * speed), 3)))
        t += 1 / (UGC_WPS * speed) + (0.07 if w.rstrip("\"')")[-1:] in ".?!" else 0.03 if w[-1:] in ",;:" else 0.0)
    L = t + UGC_TAKE + pad
    out = []
    for a, b in sb.shot_groups(sb.phrase_cuts(ws, 0.0), L):
        pts = sb.ugc_pieces(a, b, ws, 0.0)
        lo, hi = (a + sb.CUT_LEAD - 0.001 if a > 0 else -1.0), b + sb.CUT_LEAD - 0.001     # (a cut is CUT_LEAD s before its word)
        out.append((" ".join(w["w"] for w in ws if lo <= w["s"] < hi), len(pts) - 1))
    return out or [(text, 1)]


def check_out(out):
    """compliance.check_out (it allows the count a ugc hook says: plan.json 'ugc_numbers')."""
    import compliance
    return compliance.check_out(out)


INDEX_PRODUCT = {"hobo bag": "Hobo Bag", "hobo 2.0": "Hobo 2.0", "slouchy": "Slouchy", "vintage": "Vintage Bag"}   # built-in -> its
#                                                                    product in pipeline/data/clip_index.json (the client's library)


def index_clips(pk, taken=()):
    """The client's library footage of a built-in bag that clip_bank.json does not hold, for the ugc videos' shot pool: clips of
    pipeline/data/clip_index.json marked usable, no face, no on-screen text, at least 720p and 2.5 s, not a winner's RAW. ->
    [(Drive id, duration s, note + folder words)]. `taken`: Drive ids to leave out (the ones the bank has)."""
    name = INDEX_PRODUCT.get(pk)
    try:
        rows = json.load(open(os.path.join(HERE, "data", "clip_index.json")))
    except (OSError, ValueError):
        return []
    return [(r["id"], float(r["duration"]), f"{r.get('note') or ''} {r.get('path') or ''}") for r in rows
            if name and r.get("product") == name and r.get("usable") == "yes" and r.get("faces") == "none"
            and r.get("text") in (None, "", "none") and r["id"] not in taken and DRIVE_ID.match(str(r["id"]))
            and min(int(r.get("width") or 0), int(r.get("height") or 0)) >= 720 and float(r.get("duration") or 0) >= 2.5
            and not re.search(r"\bRAW\b|Concept \d|Creative Delivery", r.get("path") or "")]


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


# ---------------------------------------------------------------- pipelines
def counts(a):
    """The plan's numbers: a.statics, a.videos (storyboard projects), a.winner_videos (winner projects) and a.fill_to
    (winners: the projects the batch keeps, storyboards filling what the winners can't). winners / new-product with no
    count given, or --batch: a BATCH (--batch fills only the counts not given); else the counts given, missing ones 0
    (catalog without --batch: exactly as before). --projects N = N projects of the pipeline's kind (winner projects in
    winners, storyboards otherwise). Returns the size record for plan.json / the reply."""
    pipe, keys = getattr(a, "pipeline", None) or "catalog", ("statics", "videos", "winner_videos", "projects")
    given = {k for k in keys if getattr(a, k, None) is not None}
    batch = bool(getattr(a, "batch", False)) or (pipe != "catalog" and not given)
    n, notes = {k: max(getattr(a, k, None) or 0, 0) for k in keys}, []
    if pipe == "winners" and "videos" in given and not given & {"winner_videos", "projects"}:   # "winners, 2 videos"
        n["projects"], n["videos"], given = n["videos"], 0, (given - {"videos"}) | {"projects"}
        notes.append(f"--videos {n['projects']} in winners = {n['projects']} winner project(s) (--projects)")
    if batch and "statics" not in given:
        n["statics"] = BATCH["statics"]
    if batch and not given & {"videos", "winner_videos", "projects"}:
        n["projects"], given = BATCH["projects"], given | {"projects"}
    kind = "winner_videos" if pipe == "winners" else "videos"
    if "projects" in given:
        if kind in given and n[kind] != n["projects"]:
            notes.append(f"--projects {n['projects']} and --{kind.replace('_', '-')} {n[kind]}: --projects counts")
        n[kind] = n["projects"]
    a.statics, a.videos, a.winner_videos = n["statics"], n["videos"], n["winner_videos"]
    a.fill_to = a.winner_videos if pipe == "winners" and not getattr(a, "no_fill", False) else 0
    return dict(batch=batch, statics=a.statics, projects=a.videos + a.winner_videos, notes=notes)


def np_intake(a, pdir):
    """--pipeline new-product: the product file of a Drive New Products folder via new_product.ensure() (made from the
    folder only, reused while the folder is unchanged), then planned as --product <key>. Exits 2 when the folder can't
    be read or the file still has problems (draft). Returns plan.json's "intake" record."""
    import new_product
    ref = getattr(a, "new_product", None) or a.product or "next"
    try:
        res = new_product.ensure(ref, products_dir=pdir, cache=os.environ.get("LC_NP_CACHE") or new_product.CACHE_DIR,
                                 refresh=bool(getattr(a, "refresh_product", False)))
    except (ValueError, OSError) as e:
        print(f"new product {ref!r}: {e}", file=sys.stderr)
        sys.exit(2)
    d = json.load(open(res["file"]))
    info = intake_info(res, d)
    if (res["status"] != "ready" or res["problems"]) and not a.allow_draft:
        print(res.get("summary") or "", file=sys.stderr)
        for w in res.get("warnings") or []:      # (e.g. a PDF notes file not read: pdftotext missing)
            print(f"WARNING {w}", file=sys.stderr)
        slug_ = os.path.splitext(os.path.basename(res["file"]))[0]
        print(f"new product {d.get('name')!r}: {res['file']} is '{res['status']}', not ready for ads:\n  - " +
              "\n  - ".join(res["problems"] or ["fewer than 3 feature lines found in the folder's notes"]) +
              f"\nFix: put what is missing into Drive 'New Products / {info['folder'] or ref}' (a notes doc with 3-7 "
              f"features, the price / offer; faceless photos; clips) and plan again with --refresh-product, or edit "
              f"{res['file']} by hand (only true claims from the notes), set \"status\": \"ready\", run python3 "
              f"pipeline/new_product.py check {slug_}, then plan again", file=sys.stderr)
        sys.exit(2)
    a.product = res["key"]     # planned as this product file even when its key is a built-in bag's ('Hobo Bag')
    os.environ["LC_PRODUCT_FILE"] = res["key"]
    return info


def intake_info(res, d):
    """plan.json "intake": where a new product came from and what its intake read (new_product.ensure + its file)."""
    import new_product
    src, fa, o = d.get("source") or {}, d.get("facts") or {}, d.get("offer") or {}
    fid, ph = src.get("drive_folder"), d.get("photos") or []
    edited = not d.get("auto") or src.get("auto_sig") not in (None, new_product.content_sig(d))
    kinds = {}
    for i, p in enumerate(ph):
        kinds.setdefault(p.get("kind") or "?", []).append(f"P{i}")
    pct, gift = deal_of(o)
    f = os.path.abspath(res["file"])
    if res.get("created"):
        how = "made now from the folder" + (" (the folder changed since the last intake)" if res.get("changed") else "")
    else:
        how = "reused (the folder " + ("changed, but the file was edited by hand: kept as it is" if res.get("changed")
                                       else "is unchanged") + ")"
    clips = [f"{c.get('name')} {c.get('dur') or 0:.0f} s {c.get('w')}x{c.get('h')}" for c in d.get("clips") or []]
    return dict(folder=src.get("folder_name"), drive_link=f"https://drive.google.com/drive/folders/{fid}" if fid else None,
                product_file=os.path.relpath(f, ROOT) if f.startswith(ROOT + os.sep) else f, key=d.get("key"),
                status=d.get("status"), created=bool(res.get("created")), changed=bool(res.get("changed")), intake=how,
                made_by="hand-edited" if edited else "the intake, automatically (auto)",
                site=f"libracases.com/{d['site']} (only what the folder lacks)" if d.get("site") else
                "not read (Drive folder only)",
                read=dict(photos=len(ph), photo_kinds=kinds, faces=[f"P{i}" for i, p in enumerate(ph) if p.get("faces")],
                          clips=clips, notes=re.findall(r"^## (.+)$", fa.get("notes") or "", re.M)),
                offer=dict(text=" + ".join(x for x in (f"{pct}% off" if pct else "no discount", gift) if x),
                           price=fa.get("price"), compare_at=fa.get("compare_at"), price_source=fa.get("price_source"),
                           evidence=o.get("evidence") or []),
                colours=fa.get("colours") or [], features=[f"{x[1]}: {x[0]}" for x in d.get("features") or []],
                problems=res.get("problems") or [], warnings=res.get("warnings") or [],
                tests=len(d.get("tests") or []), summary=(res.get("summary") or "").splitlines())


# ---------------------------------------------------------------- plan
def plan(a):
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    theme_key = pick_theme(a.theme)
    th = dict(THEMES[theme_key])
    tname = theme_name(a.theme, theme_key)
    pdir = products_dir(a)
    early = []
    if getattr(a, "new_product", None) and (getattr(a, "pipeline", None) or "catalog") != "new-product":
        if (getattr(a, "pipeline", None) or "catalog") == "catalog":   # a Drive folder never reads the site / built-in ads
            early.append(f"--new-product {a.new_product!r} without --pipeline new-product: planned as --pipeline new-product")
            a.pipeline = "new-product"
        else:
            early.append(f"--new-product {a.new_product!r} is for --pipeline new-product: ignored in {a.pipeline}")
    pipe = getattr(a, "pipeline", None) or "catalog"
    size = counts(a)
    warnings = early + list(size.pop("notes"))
    intake = np_intake(a, pdir) if pipe == "new-product" else None
    seed_given = getattr(a, "seed", None) is not None
    if not seed_given:                # another batch of a new product: other statics, hooks and bodies by itself
        a.seed = 1 + ((intake or {}).get("tests") or 0 if not a.only else 0)
        if a.seed > 1:
            warnings.append(f"this product already has {a.seed - 1} batch(es): --seed {a.seed} so the statics and hooks "
                            f"differ (redos of this batch: the same flags with --seed {a.seed + 1} --only P02, or --seed "
                            f"{a.seed} --hook-seed {a.seed + 1} --only P02H3)")
    files = product_files(pdir)
    if (a.theme or "").strip() and theme_key not in NAMED and tname not in ("Evergreen", "Gift"):
        warnings.append(f"theme {a.theme!r} is not built in: the ads use the {'gift' if theme_key == 'gift' else 'evergreen'} "
                        f"lines and are named ..._{tname}_...; write its hooks and closes with --lines")
    W = max(a.winner_videos, 0)
    sel = None
    if W or (pipe == "winners" and not a.product):    # (winners: the statics are of the top winner's product)
        import winners
        sel = winners.select(a.winners)
        if sel["note"]:
            warnings.append(f"winners: {sel['note']}; using all {len(sel['winners'])} bank winners in clip_bank order")
        if sel["brief"] and sel["brief"].get("stale"):
            warnings.append(f"the newest brief is {sel['brief'].get('age_days')} days old (stale): winners may be out of date")
    if a.product:
        pk = a.product if pipe == "new-product" and a.product in files else pick_product(a.product, files)
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
    if pr["source"] != "built-in":    # a 'ready' file must still pass check (media reachable, 3-7 features, honest offer)
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
            why = ("its notes give no price, % or gift" if not p.get("site") else "libracases.com shows no discount and no "
                   "free gift" + ("" if p["source"] == "built-in" else ", and its product file has none"))
            fix = ("add the price and was price (or 'NN% off') to its Drive folder's notes and re-plan with "
                   "--refresh-product" if not p.get("site") else "add the offer to the product file (offer.badge / gift, "
                   "backed by the site or the client's notes) and re-run")
            print(f"{p['name']} has no offer right now ({why}): a {theme_key} ad would promise "
                  f"a deal that isn't there. Drop the theme, or {fix}.", file=sys.stderr)
            sys.exit(2)

    # ---------- site photos + facts, product-file photos and clips
    colour_imgs, packs, clean_site, site_imgs, facts = [], [], [], [], {}
    need = a.statics > 0 or a.videos > 0 or a.fill_to > 0     # (fill: storyboards may follow the winner projects)
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
            colour_imgs, painted = [], set()
            for n_, f_ in facts["colours"].items():   # every site colour gets its swatch: a packshot with a sale badge
                u = usable(f_, 0.6)                    # gets it painted out (badge_free: the brown Hobo Bag photo is the
                if not u:                              # 'CLEARANCE SALE' image), used for swatches / colours only
                    u = site_assets.badge_free(f_, os.path.join(site, "clean"))
                    painted.update([u] if u else [])
                if u:
                    colour_imgs.append((n_, u))
            clean_site = [u for f in facts["clean_images"] if f not in facts["colours"].values() for u in [usable(f, 0.8)] if u]
            packs = [f for _, f in colour_imgs if f not in painted] or clean_site
    pr["offer"] = resolve_offer(pr, facts, warnings)
    honest(pr, warnings)
    for w in (sel["winners"] if W else []):
        p_ = wprod(w["key"])
        if p_ is not pr and not p_.get("_resolved"):
            p_.update(offer=resolve_offer(p_, None, warnings), _resolved=True)
            honest(p_, warnings)
    if W:     # the speaker's % must never be more than the site gives: such a RAW needs a human recut of its offer
        import compliance
        keep = []
        for w in sel["winners"]:
            ow, wp_ = str(rw[w["key"]]["edit"].get("offer_word") or ""), wprod(w["key"])
            wpct = deal_of(wp_["offer"])[0]
            claims = compliance.raw_audit(compliance.raw_words(w["key"]), compliance.remix_ranges(
                rw[w["key"]]["edit"], rw[w["key"]].get("dur"), body_only=True))[0]
            if claims:        # Julian 2026-10-09: no health claim even in the client's RAW (a cut must remove it first)
                c0 = claims[0]
                sel["unmatched"].append(dict(name=w.get("name") or w["key"], roas=w.get("roas"), action=w.get("action"),
                                             product=wp_["name"], why=f"its RAW body says \"{c0['text']}\" ({c0['start']:.1f}-"
                                             f"{c0['end']:.1f} s): a {c0['category']} claim (Julian's rule: never, not even in "
                                             f"RAW audio); cut it on word boundaries (clip_bank winner_raws[{w['key']}].edit."
                                             f"claim_cuts, then projects.py cadence) before it can run (not remixed)",
                                             client=f"its video says \"{c0['text']}\": a health claim Julian's rules don't "
                                                    f"allow; it needs that line cut first"))
            elif ow.isdigit() and (not wpct or wpct < int(ow)):
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
                        for c in compliance.cold_opens(k, rw[k]["edit"].get("cold_opens"))}) or 1
        cap = {w["key"]: max(1, n_cos(w["key"]) // a.hooks) for w in sel["winners"]}
        wrows = [w for r_ in range(max(cap.values())) for w in sel["winners"] if cap[w["key"]] > r_][:W]
        if len(wrows) < W:
            held = ", ".join(f"{w.get('name') or w['key']}: {n_cos(w['key'])}" for w in {x["key"]: x for x in wrows}.values())
            warnings.append(f"{W} winner projects asked: {len(wrows)} winner project{'s' if len(wrows) > 1 else ''} "
                            f"({'one per winner' if max(cap.values()) == 1 else 'per winner as its cold opens allow'}; cold "
                            f"opens {held}): a project holds up to {a.hooks} of its winner's cold opens, so another project "
                            f"of the same winner would repeat its openings and its body under new names); {W - len(wrows)} "
                            + ("filled with new-angle projects (below)" if a.fill_to else "left out") +
                            ". More projects of a winner need new cold opens first (python3 pipeline/winner_prep.py)")
        W = len(wrows)
    wkeys = [w["key"] for w in wrows]
    fill = max(a.fill_to - W, 0)      # winners: the batch keeps its projects, storyboards of the winners' product fill in
    if fill:
        why = ([f"{len(sel['unmatched'])} of the brief's winners can't be remixed (unmatched: no prepared RAW, or its RAW "
                f"needs a human first)"] if sel and sel["unmatched"] else []) + \
            ([f"{len({w['key'] for w in wrows})} winner(s) to remix, one project each (another project of the same winner "
              f"would repeat its cold opens)"] if wrows and a.hooks > 1 else []) + ([] if wrows else ["no winner can be remixed now"])
        warnings.append(f"winners batch: {W} winner project{'s' if W != 1 else ''}"
                        f"{' (' + ', '.join(dict.fromkeys(w.get('name') or w['key'] for w in wrows)) + ')' if wrows else ''}"
                        f" + {fill} new-angle storyboard project{'s' if fill > 1 else ''} of {pr['name']} to keep "
                        f"{a.fill_to} projects ({'; '.join(why) or 'fewer winner projects than asked'}); --no-fill: only "
                        f"the winner projects")
        a.videos += fill
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

    def fetch(item, dest, photo=False):
        """Product-file photo/clip: the cached copy ('path') if it is there, else a Drive download by 'id'. A photo is
        downloaded to a temp file named like the Drive original (src_name) and converted by new_product.to_jpg, as the
        intake did (EXIF rotation, HEIC): a later session sees the pixels the intake's face check saw."""
        src = os.path.join(ROOT, item["path"]) if item.get("path") else None
        if src and os.path.exists(src):
            return src
        if not item.get("id"):
            warnings.append(f"{item.get('name')}: no cached copy and no Drive id (intake ran in another session?)")
            return None
        tmp = None
        try:
            import contextlib
            import io
            from drive_upload import access_token, download
            with contextlib.redirect_stdout(io.StringIO()):       # its error JSON must not break plan's stdout JSON
                token[:] = token or [access_token()]
                if not photo:
                    return download(token[0], item["id"], src or dest)
                tmp = f"{src or dest}.drive{os.path.splitext(item.get('src_name') or '')[1].lower()}"
                download(token[0], item["id"], tmp)
            return new_product.to_jpg(tmp, src or dest, warnings.append)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            warnings.append(f"{item.get('name')}: Drive download failed "
                            f"({'no Drive login: python3 pipeline/drive_upload.py check' if isinstance(e, SystemExit) else e})")
            return None
        finally:
            for x in ([tmp, tmp + ".lock"] if tmp else []):
                if os.path.exists(x):
                    os.remove(x)

    ai_clips = {}                     # planned AI clips by id (ai_gen.plan_ai, below): ["ai", "AC03", 0] picks
    import new_product
    file_photos, file_packs, file_life, pfile = [], [], [], {}     # pfile: photos[n] -> its file (["photo", "P<n>"])
    refused, no_static = {}, set()    # refused: photos[n] plan's face re-check refused; no_static: videos only (statics false)
    for i, p in enumerate(pr["photos"] if need else []):
        if p.get("faces") != 0:          # faces (or not checked): never in ads
            continue
        nm = safe_name(p.get("name") or "photo.jpg")
        dest = os.path.join(out, "photos", f"{i:02d}_" + (nm if nm.lower().endswith((".jpg", ".jpeg")) else
                                                          os.path.splitext(nm)[0] + ".jpg"))
        f = fetch(p, dest, photo=True)
        if f:
            if not os.path.exists(dest):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy(f, dest)
            pack = (p.get("clean") or 0) >= 0.8
            if new_product.count_faces(dest, strict=not pack):          # re-checked with today's detector
                refused[i] = p.get("name")
                warnings.append(f"photo P{i} {p.get('name')}: a face was found by plan's re-check: never used (its picks "
                                f"are skipped)")
                continue
            file_photos.append(dest)
            pfile[i] = dest
            (file_packs if pack else file_life).append(dest)
            if p.get("statics") is False:      # may show part of a face or head (intake): videos only, never a static
                no_static.add(dest)
    clips = []
    for i, c in enumerate(pr["clips"] if a.videos > 0 or a.fill_to > 0 else []):
        clips.append(fetch(c, os.path.join(out, "clips", f"{i:02d}_{safe_name(c.get('name', 'clip.mp4'))}")))
    packs = packs + file_packs
    pool = list(dict.fromkeys(packs + clean_site + file_photos))
    fits = set(file_photos) | {c for c in clips if c}    # the product file's own media: framed whole when not 9:16
    pnum, dot_rgb = {f: n for n, f in pfile.items()}, {}
    pkind = {n: pr["photos"][n].get("kind") for n in pfile}     # packshot / worn / detail / other (new_product intake)
    if need and pr["source"] != "built-in" and not colour_imgs:    # no site swatches: the client's packshots, by shade
        names_ = list((pr.get("facts") or {}).get("colours") or [])
        shots_ = [pfile[n] for n, ph in enumerate(pr["photos"]) if n in pfile and ph.get("kind") == "packshot"] or file_packs
        if len(names_) >= 2 and len(shots_) >= 2:
            got_, why_ = match_colours(shots_, names_)
            colour_imgs, dot_rgb = [(n, f) for n, f, _ in got_], {n: c for n, _, c in got_}
            warnings.append("colour swatches: packshots matched to the notes' colours by shade: " +
                            ", ".join(f"{n} = P{pnum[f]}" for n, f in colour_imgs) + " (check the colours static / swatches)"
                            if got_ else f"colours: {why_}: no named colour swatches (the colours static shows the packshots)")
    life_cache = []

    def lifestyle():
        """Photos for lifestyle statics: the client's photos with no face (strict check; never one the intake marked
        "statics": false: part of a head) and the site photos the product file lists in site_lifestyle (never image 0).
        Other site photos are never put in statics automatically."""
        if not life_cache:
            listed = [site_imgs[i] for i in (new_product.site_index(x) for x in pr["site_lifestyle"]) if i and i < len(site_imgs)]
            ok = []
            for f in listed:
                if new_product.count_faces(f, strict=True):
                    warnings.append(f"site_lifestyle {os.path.basename(f)}: a face was found: not used")
                else:
                    ok.append(f)
            life = [f for f in file_life if f not in no_static]
            kept = [f for f in life if pkind.get(pnum.get(f)) in ("worn", "detail")]   # (full bleed: an unsorted photo
            life_cache.append((kept if len(kept) >= 3 else life) + ok)               # may have text baked in)
        return life_cache[0]

    def photo_file(p):
        """The file of a photo pick: ["photo", "P<n>"] = the product file's photos[n] (None: a face, or not downloaded),
        ["photo", k] = the plan's photo pool (packshots first)."""
        if isinstance(p[1], str):
            m_ = re.fullmatch(r"P(\d+)", p[1].strip())
            n_ = int(m_.group(1)) if m_ else None
            if n_ not in pfile:
                ph_ = pr["photos"][n_] if n_ is not None and n_ < len(pr["photos"]) else None
                if n_ not in refused:      # (a re-check refusal is said once, above)
                    warnings.append(f"pick {p!r}: " + ("no such photo in the product file" if not ph_ else
                                                       f"{ph_.get('name')} shows a face: never used" if ph_.get("faces") else
                                                       f"{ph_.get('name')} could not be downloaded") + ": skipped")
                return None
            return pfile[n_]
        return pool[p[1] % len(pool)] if pool and isinstance(p[1], int) else None

    def fit_of(src):                  # recut 'fit': a product-file photo / clip not shot 9:16 is shown whole (recut.py)
        return {"fit": FIT_CLIP if src in clips else "auto"} if src in fits else {}

    def pick(p, w=1.0):
        """[src, start, weight(, extra)] for a pick, or None when it points at nothing (or at an AI clip)."""
        if not p:
            return None
        if p[0] == "photo":
            f_ = photo_file(p)
            return [rel(f_), 0, w, dict({"zoom": [1.0, 1.06]}, **fit_of(f_))] if f_ else None
        if p[0] == "clip":
            c = clips[p[1]] if isinstance(p[1], int) and 0 <= p[1] < len(clips) else None
            return ([c, p[2], w] + ([fit_of(c)] if fit_of(c) else [])) if c else None
        if p[0] == "drive":           # ["drive", <Drive file id>, start]: a client library clip (clip_index.json), ugc only
            return [p[1], p[2], w] if DRIVE_ID.match(str(p[1])) else None
        if p[0] == "ai":              # ["ai", "AC03", 0]: a planned AI clip (ai_gen.py: made after plan; render swaps one that
            c_ = ai_clips.get(p[1])   # failed its gate for the block's real spare shot)
            return [ai_gen.clip_file(out, p[1]), p[2], w] if c_ else None
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
    # static that would still repeat an earlier one exactly is left out. Bottom of funnel (Julian, 2026-10-09: the statics
    # that get spend are BOF, a Hobo Bag static performs): offer (huge real %), stars (verbatim review snippets) and
    # checklist (the product's own feature tags + offer pill); the Hobo Bag's cycle leans on them.
    import brand_statics as bs
    tags = list(dict.fromkeys(f[1] for f in pr["features"]))
    s_packs = [f for f in packs if f not in no_static]                 # statics: never a photo marked "statics": false
    s_colours = [(n, f) for n, f in colour_imgs if f not in no_static]
    clean_mode = len(s_packs) >= 2
    if clean_mode and pk == "hobo bag" and pr["source"] == "built-in":
        seq = ["hero", "offer", "stars", "promo", "checklist", "bold", "review", "colours", "offer", "compare", "stars",
               "checklist"]
    elif clean_mode and pr["source"] != "built-in" and len(lifestyle()) >= 3:   # the client's own worn / detail photos:
        seq = ["hero", "offer", "lifestyle", "promo", "colours", "checklist", "lifestyle", "bold", "stars",  # each once
               "compare", "lifestyle", "review"]
    elif clean_mode:
        seq = ["hero", "promo", "offer", "bold", "stars", "colours", "checklist", "compare", "review", "promo", "hero", "bold"]
    else:
        seq = ["lifestyle", "bold", "hero", "lifestyle", "compare", "review", "lifestyle", "bold", "hero", "lifestyle"]
    if not getattr(a, "classic", False):   # the clean cycle (owner 2026-10-20: the competitors' statics look clean, "take it to essence"):
        # one big photo and next to no text. Of 20: studio 4 (the packshot large on a tinted seamless, one line, one pill), native 4-5
        # (a real face-free photo, one caption), the proven bottom-of-funnel ones calmer and fewer (quotes 3 verbatim reviews around the
        # packshot, value 2 the real price struck through, offer 2, stars 1) and each text-heavy layout (colours, checklist, bold,
        # compare) once; hero / promo / review are not in the cycle any more (studio is the cleaner hero). A layout the product can't
        # back (no photo / review / price) is replaced by `instead` (below).
        if clean_mode and pk == "hobo bag" and pr["source"] == "built-in":
            seq = ["studio", "native", "offer", "quotes", "studio", "native", "value", "stars", "studio", "native", "quotes",
                   "checklist", "studio", "native", "offer", "colours", "value", "quotes", "bold", "compare"]
        elif clean_mode and pr["source"] != "built-in" and len(lifestyle()) >= 3:
            seq = ["studio", "native", "offer", "quotes", "studio", "native", "value", "native", "stars", "colours", "studio",
                   "native", "checklist", "quotes", "native", "value", "studio", "lifestyle", "bold", "compare"]
            #       (the photos go to the natives first, then to the lifestyle layout: each photo once per batch)
        elif clean_mode:
            seq = ["studio", "offer", "native", "quotes", "studio", "value", "stars", "native", "studio", "colours", "checklist",
                   "quotes", "native", "studio", "value", "bold", "native", "compare", "quotes", "offer"]
        else:
            seq = ["native", "lifestyle", "native", "hero", "native", "lifestyle", "native", "review", "native", "compare",
                   "lifestyle", "native", "lifestyle", "native", "bold", "native", "lifestyle", "review", "native", "hero"]
    if not clean_mode and a.statics and lifestyle():
        warnings.append(f"only {len(s_packs)} clean packshot(s): statics use the client's lifestyle photos and framed photo "
                        f"cards")
    s_pct, s_gift = deal_of(pr["offer"])
    s_v = offer_vars(pr)
    star_revs = [n for n in pr["reviews"] if n in revs and bs.snippet(revs[n]["text"])]   # a verbatim snippet to show
    quote_revs = [n for n in star_revs if len(revs[n]["name"].split()[0].rstrip(".")) > 1] or star_revs   # (quotes: not 'X A.')
    pf_ = facts if facts.get("price") else (pr.get("facts") or {})    # no site read: the client's notes' prices
    try:
        s_price, s_was = float(pf_.get("price") or 0), float(pf_.get("compare_at") or 0)
    except ValueError:
        s_price = s_was = 0
    price_ok = s_pct and s_was > s_price > 0 and new_product.site_pct(pf_.get("price"), pf_.get("compare_at")) == s_pct
    value_ok = bool(price_ok and abs(100 * (1 - s_price / s_was) - s_pct) <= 2)    # (brand_statics' value layout refuses worse)
    statics, n_life, seen_s, nlay, no_photo = [], 0, set(), {}, 0
    # another batch of the same product shows other photos and headlines by itself (the client: "the statics repeat across batches"):
    # the static cycle starts one step further for every batch the novelty log has (a new product's --seed already counts its tests)
    sseed = a.seed + (0 if seed_given or pr["source"] != "built-in" or a.only else len(novelty.batches(pr["name"])))
    if sseed != a.seed:
        warnings.append(f"{pr['name']} has {sseed - a.seed} earlier batch(es) in the novelty log: the statics start {sseed - a.seed} "
                        f"step(s) further in their photo / headline cycle (other photos and captions than before)")
    life_used, studio = set(), {}      # lifestyle() photos taken so far (a lifestyle or native static each take one, once per batch)

    def next_life(native=False):       # the next unused lifestyle photo (native: a real photo, not a studio packshot)
        for k_, f_ in sorted(enumerate(lifestyle()), key=lambda x: (native and pkind.get(pnum.get(x[1])) != "worn", x[0])):
            if k_ in life_used:          # (native: a worn photo first: a macro of leather or a zip reads as a texture ad)
                continue
            if native:
                if f_ not in studio:
                    studio[f_] = bs.studio_white(bs.load(os.path.dirname(f_), os.path.basename(f_)))
                if studio[f_]:
                    continue
            return k_
        return None
    def studio_pack(f_):               # a packshot on a white studio backdrop (the studio layout needs one)
        if f_ not in studio:
            studio[f_] = bs.studio_white(bs.load(os.path.dirname(f_), os.path.basename(f_)))
        return studio[f_]
    cards = {rel(f) for f in s_packs if bs.textured(f)}     # light textured backdrop: a framed card, never a grey box
    ptag = {rel(f): x[1] for x in reversed(pr["features"]) for p in x[2] if p and p[0] == "photo" and isinstance(p[1], str)
            for f in [pfile.get(int(p[1][1:])) if re.fullmatch(r"P\d+", p[1]) else None] if f}   # client photo -> its tag
    hero = ov(tx["hero"], "hero") if a.statics else tx["hero"]

    def revs_shown():                 # how often the statics so far show each review (review cards; a stars static's first 2
        c_ = {}                       # snippets: a 3rd card shows only when the packshot keeps its room)
        for x in statics:
            for n in ([x["review_n"]] if x.get("review_n") else []) + [r for r in (x.get("reviews") or [])[:2] if isinstance(r, int)]:
                c_[n] = c_.get(n, 0) + 1
        return c_

    def two_lines(tag):
        ws = tag.split()
        return [" ".join(ws[:-1]), ws[-1] + "."] if len(ws) > 1 else [ws[0] + "."]

    def static(lay, photo, hv, t=0):  # hv: headline/sub variant (0 = the standard one); t: the retry
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
            dots = [dot_rgb.get(n) or DOTS.get(n.lower().split()[0], [150, 150, 150]) for n, _ in s_colours][:7]
            lines_ = list({json.dumps(x): x for x in [ov(tx["bold"], "bold")] + [two_lines(t) for t in tags]}.values())
            return dict(layout="bold", photo=photo, lines=lines_[hv % len(lines_)], accent_lines=[1], sub=tx["bold_sub"],
                        cta=tx["cta"], dots=dots)
        if lay == "review":           # a review a stars static of this batch shows already comes last
            rq, c_ = rot(pr["reviews"], (i // 6 + hv) % len(pr["reviews"])), revs_shown()
            return dict(layout="review", review_n=min(rq, key=lambda n: (c_.get(n, 0), rq.index(n))), photo=photo,
                        cta=tx["cta"])
        if lay == "colours":
            ph = [dict(src=rel(f), name=n) for n, f in s_colours][:6] or [dict(src=rel(f), name="") for f in s_packs[:4]]
            return dict(layout="colours", photos=rot(ph, hv), headline=V(ov("Pick your colour.", "colours"), "Which one is yours?",
                                                                         "Which colour are you?"), sub=tx["colours_sub"], cta=tx["cta"])
        if lay in ("lifestyle", "native"):
            heads = [hero, f"The {pr['short']}."] + ([". ".join(tcase(t) for t in tags[:2]) + "."] if tags else [])
            if ptag.get(photo) and not t:         # a client photo a feature line picks: that feature's tag
                heads = [f"{tcase(ptag[photo])}."] * len(heads)
            elif pr["source"] != "built-in":      # (else a headline the batch's lifestyle statics have not used yet)
                had = {x.get("headline") or x.get("caption") for x in statics if x.get("layout") in ("lifestyle", "native")}
                heads = rot(heads, n_life - 1 + hv)
                heads = [next((h for h in heads if h not in had), heads[0])] * len(heads)
            if lay == "native":                   # a phone-photo post: the photo, one caption, a small offer pill (no sub, no CTA)
                return dict(layout="native", photo=photo, caption=heads[(n_life - 1 + hv) % len(heads)],
                            **({"pct": s_pct} if s_pct and 5 <= s_pct <= 90 else {}))
            return dict(layout="lifestyle", photo=photo, headline=heads[(n_life - 1 + hv) % len(heads)], sub=tx["bold_sub"] or None,
                        cta=tx["cta"])
        if lay == "quotes":           # verbatim review snippets (brand_statics picks the best sentence) around the packshot
            sq, c_ = rot(quote_revs, hv * 2), revs_shown()
            d_ = dict(layout="quotes", photo=photo, reviews=sorted(sq, key=lambda n: (c_.get(n, 0), sq.index(n)))[:2],
                      pct=s_pct if s_pct and 5 <= s_pct <= 90 else None, gift=s_gift, cta=tx["cta"])
            return {k: x for k, x in d_.items() if x not in (None, "")}
        if lay == "value":            # the real price struck through (value_ok: it matches the % within 2 points)
            d_ = dict(layout="value", photo=photo, price=f"${s_price:.2f}", was=f"${s_was:.2f}", pct=s_pct, gift=s_gift,
                      headline=V(f"The {pr['short']}", f"Meet the {pr['short']}"), cta=tx["cta"])
            return {k: x for k, x in d_.items() if x not in (None, "")}
        if lay == "studio":           # the packshot large on a tinted seamless: ONE short line and / or the small offer pill
            pool = [x for x in dict.fromkeys([f"The {pr['short']}.", f"Meet the {pr['short']}."] +
                                             [tcase(t, "sentence") + "." for t in tg[:3]]) if len(x) <= 38]
            k4, pct_ = hv % 4, (s_pct if s_pct and 5 <= s_pct <= 90 else None)
            d_ = dict(layout="studio", photo=photo, headline=None if (k4 == 3 and pct_) else pool[hv % len(pool)],
                      pct=pct_ if k4 != 1 else None)       # (line + pill, line, line + pill, pill alone)
            return {k: x for k, x in d_.items() if x not in (None, "")}
        if lay == "offer":            # every number from the site / the resolved offer (brand_statics invents nothing)
            d_ = dict(layout="offer", photo=photo, pct=s_pct, kicker=th["label"],
                      headline=V(f"The {pr['short']}", f"Meet the {pr['short']}", "Your new everyday bag"),
                      gift=s_gift, cta=tx["cta"])
            if price_ok and hv % 2 == 0:
                d_.update(price=f"${s_price:.2f}", was=f"${s_was:.2f}")
            elif pr["source"] == "built-in":
                d_["sub"] = "Free US shipping"           # store-wide (PLAYBOOK section 1)
            return {k: x for k, x in d_.items() if x not in (None, "")}
        if lay == "stars":            # 2 cards usually fit: the next one starts after them; reviews not shown yet first
            sq, c_ = rot(star_revs, hv * 2), revs_shown()
            return dict(layout="stars", photo=photo, reviews=sorted(sq, key=lambda n: (c_.get(n, 0), sq.index(n)))[:3],
                        headline=V("What our customers say", "Loved by our customers", "Real customers. Real words."),
                        cta=tx["cta"])
        if lay == "checklist":
            pill_ = " + ".join(x for x in ((tx["offer_title"] or (f"{s_v['P']} OFF" if s_pct else "")),
                                           f"FREE {s_v['GIFT_W']}" if s_gift and s_v["GIFT_W"] else "") if x)
            d_ = dict(layout="checklist", photo=photo, headline=V(f"Why the {pr['short']}?", f"What makes the {pr['short']} different"),
                      ticks=[tcase(t, "sentence") for t in tg[:4]], offer=pill_, cta=tx["cta"])
            return {k: x for k, x in d_.items() if x not in (None, "")}
        return dict(layout="compare", photo=photo, headline=V(f"Your everyday bag vs {pr['short']}", f"Most bags vs the {pr['short']}"),
                    left_title="Most bags", left=tx["compare_left"], right_title=pr["short"],
                    right=[tcase(t, "sentence") for t in tg[:3]], cta=tx["cta"])

    def can(lay):                     # this product has what the layout shows
        return {"offer": lambda: bool(s_pct and 5 <= s_pct <= 90),         # a real % right now (no '..% OFF' static without one)
                "checklist": lambda: len(tags) >= 3, "stars": lambda: len(star_revs) >= 2, "review": lambda: bool(pr["reviews"]),
                "colours": lambda: len(s_colours) >= 2 or len(s_packs) >= 2,
                "lifestyle": lambda: next_life() is not None,                # each lifestyle photo once per batch
                "native": lambda: next_life(True) is not None,               # a face-free real photo is left
                "studio": lambda: any(rel(f_) not in cards and studio_pack(f_) for f_ in s_packs),   # a white-backdrop packshot
                "quotes": lambda: clean_mode and bool(quote_revs),            # a real review with a verbatim snippet
                "value": lambda: clean_mode and value_ok}.get(lay, lambda: True)()   # the real price, % within 2 points
    instead = {"offer": "studio", "checklist": "studio", "stars": "quotes", "review": "studio", "colours": "studio", "native": "lifestyle",
               "lifestyle": "studio", "value": "offer", "quotes": "native", "studio": "hero"}   # (the clean ones first: hero always works)
    last = ["compare", "bold", "promo", "hero"] if clean_mode else ["compare", "bold"]
    if getattr(a, "classic", False):      # the old cycle's fallbacks, unchanged
        instead = {"offer": "hero", "checklist": "promo", "stars": "review", "review": "lifestyle", "colours": "lifestyle",
                   "native": "lifestyle", "value": "offer"}
    for i in range(a.statics):
        lay = seq[i % len(seq)]
        while not can(lay):           # the next best layout; at the end the least used of `last` (variety, no repeats)
            lay = instead.get(lay) or min(last, key=lambda x: (nlay.get(x, 0), last.index(x)))
        card = False
        if lay in ("lifestyle", "native"):
            k_ = next_life(lay == "native")
            photos = [lifestyle()[k_]]
            life_used.add(k_)
            n_life += 1
        elif lay == "studio":         # a clean white-backdrop packshot (never a photo card)
            photos = [f for f in s_packs if rel(f) not in cards and studio_pack(f)]
        elif s_packs:
            photos = s_packs
        elif lifestyle():
            photos, card = lifestyle(), True
        else:
            no_photo += 1
            continue
        rnd, hv0 = i // len(seq) + sseed - 1, nlay.get(lay, 0) + sseed - 1   # hv0: the 2nd hero/promo/... gets another headline
        for t in range(len(photos) * 4):
            photo = photos[(i + rnd + t) % len(photos)]
            s = static(lay, rel(photo), hv0 + t // len(photos), t)
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
    if no_photo:                      # one warning, not one per static (a clips-only folder)
        bi_ = pr["source"] == "built-in"
        warnings.append(f"{no_photo} of {a.statics} statics left out: {pr['name']} has no photo a static may use (no clean "
                        f"packshot, no faceless client photo{'' if bi_ else '; clips are for videos only'})" +
                        ("" if bi_ else ": the client must add photos without a face (packshots on a plain background, the "
                         "bag worn without a head in frame) to its Drive folder"))

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
        cos = compliance.cold_opens(w["key"], ed.get("cold_opens")) or [{"range": None, "label": "", "line": ""}]
        if a.hooks > 1:                  # H1 is a real spoken opening: a text-hook variant (another's opening under a new
            cos = [c for c in cos if not c.get("variant")] or cos   # label) only ever joins as H2-H4 (projects.expand)
        co = cos[j % len(cos)]           # (no cold open with a health claim; a medical story one comes last)
        spec = dict(raw=e["id"], start=ed.get("start") or 0.0, end=ed.get("end"), cut=ed.get("cut") or [],
                    **({"claim_cuts": ed["claim_cuts"]} if ed.get("claim_cuts") else {}), insert_at=ed.get("insert_at"), offer_word=ed.get("offer_word"), offer_after=ed.get("offer_after"),
                    burned_captions=bool(ed.get("burned_captions")), labels=ed.get("labels") or [],
                    end_title=ed.get("end_title") or wp["end"],
                    offer_title=ed.get("offer_title", wtx["offer_title"]), offer_sub=ed.get("offer_sub", wtx["offer_sub"]),
                    keywords=list(dict.fromkeys(wtx["keywords"] + THEME_WORDS[theme_key])),
                    music=False if getattr(a, "no_music", False) else dict(auto=True, seed=(a.seed - 1) * 11 + i + 1))
        #             (the RAW's own sound: most RAWs have a bed; remix.py adds one only to a RAW recorded dry)
        if uses[w["key"]] == 1:       # what a human should know about this RAW (Julian's health rule): reply + run report
            warnings += compliance.raw_human_notes(w["key"], ed, e.get("dur"), w.get("name"))
        if not ed.get("offer_word") and spec["offer_title"] and uses[w["key"]] == 1:
            warnings.append(f"{w['key']}: the RAW never says the offer: its '{spec['offer_title']}' card shows just before the "
                            f"end card")
        if co.get("range"):
            spec["cold_open"] = co["range"]
        if co.get("label"):
            spec["hook_label"] = co["label"]
        rl = [n for n in wp["reviews"] if n in revs]
        ns, intro = (), None
        if a.winner_reviews and rl and ed.get("insert_at") is not None:   # opt-in: the proven body plays intact by default
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
            ps = wp["broll"] + [x for f in wp["features"] for x in f[2]] + wp["hook_clips"]
            ps += [[p[0], p[1], g] for p in ps if p and p[0] in b for g in (b[p[0]].get(p[1]) or {}).get("good") or []
                   if abs(float(g) - float(p[2])) >= 2.5]          # + the other vetted moments of the same clips
            for p in ps:
                x = pick(p) if wp is pr else ([clip(b, p[0], p[1]), p[2]] if p and p[0] in b else None)
                if x and not str(x[0]).startswith("http") and not str(p[1]).startswith("ai_") and \
                        not str(x[0]).lower().endswith((".jpg", ".png")) and \
                        not any(c[0] == x[0] and abs(float(c[1]) - float(x[1])) < 2.5 for c in cand):   # real footage, once
                    cand.append([x[0], x[1]])
            firsts, rest = [], []
            for c in cand:                    # one shot per clip first, then second moments of the same clips
                (rest if c[0] in seen else firsts).append(c)
                seen.add(c[0])
            cand = firsts + rest
            n_br = max(3, min(len(cand), math.ceil((len(text.split()) / WPS + 0.4) / 3.5)))   # no shot over ~3.5 s
            r0 = (j * 2) % max(len(cand), 1)
            broll = [cand[(r0 + q) % len(cand)] for q in range(n_br)] if cand else []
            if broll:
                spec["reviews"] = dict(vo=line(vid, "rev", text, NARRATOR), text=text, cards=rcards, broll=broll,
                                       spare=[c for c in cand if c not in broll][:4])
            else:
                ns = ()
            if not ns:
                warnings.append(f"{vid}: {wp['name']} has no reviews/B-roll to narrate: remix without a review section")
        try:                          # the client's cadence rule, checked on the committed transcript (no download)
            import remix
            ws_ = remix._norm(json.load(open(os.path.join(HERE, "data", "transcripts", f"{w['key']}_words.json"))))
            for x in remix.remix_cadence(spec, ws_, e.get("dur") or 9999):
                warnings.append(f"{vid} ({w['key']}): cadence: {x}")
        except (OSError, ValueError):
            pass
        name = f"{ad_prefix(wp['name'], tname, rev)}_{vid}_remix{slug(e.get('concept') or w['key']).lower()}"
        specs[name] = spec
        videos.append(dict(name=name, id=vid, format="remix", engine="remix", hook=co.get("line") or "",
                           hook_label=co.get("label") or "",
                           winner=dict(key=w["key"], ad=e.get("ad"), brief_name=w.get("name"), roas=w.get("roas"),
                                       action=w.get("action"), product=wp["name"], cold_open=co.get("range"),
                                       reviews=list(ns), intro=intro)))

    # storyboard videos: V(W+1).. ; each grows (more features, reviews, colours, customer clips) to ~38 s. Each later pass
    # over the format cycle (and each --seed) starts the hook, features, reviews and B-roll elsewhere; a video that would
    # still repeat an earlier one exactly is left out. No shot shows twice in one ad when another is left.
    # One voice per video (the client: never switch the point of view): every line is the brand voice; reviews are said
    # about the customer ("Carol calls it ...") with her verbatim card on screen; a real customer speaks only in her own
    # clip, after the narrator introduces her (clip_bank 'intros'). Pacing: no B-roll shot over ~3.6 s (WPS estimate; the
    # board's spare_broll covers a longer real voiceover, storyboard.MAX_SHOT).
    # showcase = V09 Vintage showcase (2026-10-02, the first batch's only video with spend): "Take a closer look at the
    # <bag>", every feature with its tag, a real customer in her own words, the colours, the offer. First in the cycle when
    # the product has real customer clips (it fits only then).
    formats = (["showcase"] if pr["customer"] else []) + ["features", "reviews", "colours", "features", "reviews", "colours"]
    if pr["source"] != "built-in" and not pr["reviews"] and not pr["customer"]:
        # a new product (no reviews, no customer clips yet): one angle per project on the same true material, each with
        # its own opening shot, feature order and label: features, colours (named swatches), showcase (take a closer
        # look: the detail photos first), lifestyle (the worn photos first), offer (the deal first, the packshots)
        formats = [f for f in ("features", "colours", "showcase", "lifestyle", "offer") if
                   {"colours": len(colour_imgs) >= 3, "lifestyle": "worn" in pkind.values(),
                    "offer": any(deal_of(pr["offer"]))}.get(f, True)]
    LEAD = {"showcase": "detail", "lifestyle": "worn", "offer": "packshot"} if pkind else {}   # photo kind each angle leads with
    story = bool(getattr(a, "story", False) or (a.videos and STORY_WORDS.search(a.request or "")))
    if story and not getattr(a, "story", False):
        warnings.append("the request asks for a story / long video: storyboard videos use the story format (1.5-2 min: "
                        "every feature, the real customer in full, reviews, colours, the offer)")
    if story:                         # 1.5-2 min storytelling: every feature, the real customer in full, reviews, colours
        formats = ["story"]
    fs = pr["features"]
    rich = bool(pr["reviews"] or pr["customer"])
    feat_picks = {tuple(p) for f in fs for p in f[2]}
    photo_picks = [["photo", f"P{pnum[f]}"] if f in pnum else ["photo", k] for k, f in enumerate(pool)]
    colour_names = list((facts or {}).get("colours") or {}) or [n for n, _ in colour_imgs]   # every site colour is said
    gnoun = (re.findall(r"pouch|wallet|purse", deal_of(pr["offer"])[1] or "", re.I) or [""])[-1]
    feat_gift = bool(gnoun) and any(re.search(r"\bfree\b.*\b" + gnoun, f[0], re.I) for f in fs)
    colours_tail = "Which one is yours?" if feat_gift else tx["colours_line"]       # the gift is said twice at most
    SHOT, SHOWCASE_MAX = 3.6, 66      # longest planned shot (s); a showcase adds customer clips up to ~66 s (+ colours)
    NEW_MAX = 58                      # a new product's ad: its feature lines up to ~1 min (the 40-60 s it should run)
    TARGET = 38                       # an ad shorter than this (est.) is padded with what the product's own material backs
    HOLD_MAX = 2.4                    # the longest silent picture hold after a line (padding: a second look at the product)
    new_prod = pr["source"] != "built-in" and not pr["reviews"] and not pr["customer"]   # product file, Drive material only
    STORY_MAX = 112                   # a story adds customer clips and reviews up to ~112 s (QA 60-130 s)

    def near(p, q):                   # the same shot: same photo (P3 = its pool number too), or the same clip within 2.5 s
        if not p or not q or p[0] != q[0]:
            return False
        if p[0] == "photo":
            return p[1] == q[1] or (photo_file(p) or 0) == photo_file(q)
        return p[1] == q[1] and abs(float(p[2]) - float(q[2])) < 2.5

    def moments(p):                   # the other vetted moments of a pick's clip (clip_bank / product-file 'good')
        if not p or p[0] == "photo":
            return []
        if p[0] == "clip":
            c = pr["clips"][p[1]] if isinstance(p[1], int) and 0 <= p[1] < len(pr["clips"]) else {}
            gs = (c or {}).get("good") or []
        else:
            gs = ((b.get(p[0]) or {}).get(p[1]) or {}).get("good") or []
        return [[p[0], p[1], g] for g in gs if abs(float(g) - float(p[2])) >= 2.5]
    all_shots = []                    # every real shot of this product: picks, B-roll, hook clips, their moments, photos
    for p in pr["hook_clips"] + pr["broll"] + [x for f in fs for x in f[2]]:
        for q in [p] + moments(p):
            if q and not any(near(q, x) for x in all_shots) and pick(q):
                all_shots.append(q)
    all_shots += [p for p in photo_picks if not any(near(p, x) for x in all_shots)]   # (a B-roll photo is there already)
    scenes ={(c[0], c[1]) for c in pr["customer"]}      # customer clips: her testimony, not B-roll under the narrator
    talk_ws = {}

    def talks(p):
        """A pick where someone speaks on camera (its clip's committed / cached transcript has a word within the shot,
        0.3 s margins): never muted B-roll under the narrator (lips moving under another voice: the point of view would
        switch without a reason)."""
        x = pick(p) if p and p[0] != "photo" else None
        if not x or str(x[0]).lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return False
        src = str(x[0])
        if src not in talk_ws:
            import remix
            ws_ = remix.committed(src)
            j_ = os.path.splitext(src)[0] + "_words.json"
            talk_ws[src] = ws_ if ws_ is not None else remix._norm(json.load(open(j_))) if os.path.exists(j_) else []
        a_ = float(x[1])
        return any(w["e"] > a_ - 0.3 and w["s"] < a_ + SHOT + 0.3 for w in talk_ws[src])

    def unfit(p):                     # never B-roll: a real customer's own clip (her scene comes later, introduced) or a
        return bool(p) and p[0] not in ("photo", "ai") and ((p[0], p[1]) in scenes or talks(p))   # moment someone talks

    def fmt_of(v):
        fmt = formats[v % len(formats)]
        if fmt == "colours" and len(colour_imgs) < 3:
            fmt = "features"
        return "features" if fmt == "reviews" and not pr["reviews"] else fmt

    def need_for(text, pad=0.25):     # shots a voiced line needs so that none runs over SHOT s
        return max(1, math.ceil((len(text.split()) / WPS + pad) / SHOT))

    def has_person(p):                # a clip-bank shot whose notes say a person / face is in it (try-on, presenter ...)
        if not p or p[0] in ("photo", "clip") or p[0] not in b or not isinstance(b[p[0]], dict):
            return False
        e = b[p[0]].get(p[1]) or {}
        return bool(e.get("person")) or bool(re.search(r"face|person|woman|model|try-?on|presenter|wearing|customer",
                                                       str(e.get("notes", "")), re.I))

    def intro_of(c, k):               # the narrator's line before a real customer's clip: the script reason for her voice
        ins = (((b.get(c[0]) or {}).get(c[1]) or {}).get("intros") if c and c[0] in b else None) or \
            ["Here's a real customer with hers."]
        return ins[k % len(ins)]

    def board(v, vid, bid, fmt, o):
        # o: this format's earlier videos + (--seed - 1) + retries. Every step moves the hook line and clip, the close
        # B-roll, where the features start and where the reviews start, so a later pass or another seed differs everywhere
        hooks = tx["hooks"]
        if fmt == "colours":
            hooks = (["Be honest. Which colour are you?", "Which colour would you pick?"] if theme_key == "default" else
                     [h + " Which colour are you?" for h in hooks])
        elif fmt in ("showcase", "story"):   # V09's hook first; the theme's hooks on a later pass
            hooks = [f"Take a closer look at the {pr['short']}."] + hooks
        elif fmt == "offer":                 # the deal first (the product's own offer: never more than it backs)
            hooks = [x for x in (tpl("The {short} is {price_sp}[, with {gift_sp}].", s_v),
                                 tpl("The {short} comes with {gift_sp}.", s_v)) if x][:1] + hooks
        o2 = o + o // len(hooks)
        o3 = o + o // max(len(fs), 1)
        pid = "P" + vid[1:]               # project mode: P03_hook = V03_hook (H1's line; H2.. come from projects.py)
        hook = ov(hooks[((0 if fmt in ("showcase", "story", "offer") else v) + o) % len(hooks)], f"{vid}_hook", f"{pid}_hook",
                  f"{bid}_hook")
        shown, reserved = [], []

        def is_shown(p):
            return any(near(p, q) for q in shown + reserved)

        def crowded(p, got):          # a 3rd shot of one clip in a block, or a 2nd within 4 s of the 1st: one long take
            same = [g for g in got if p[0] != "photo" and g[0] == p[0] and g[1] == p[1]]
            return len(same) >= 2 or any(abs(float(g[2]) - float(p[2])) < 4.0 for g in same)

        def take(ps, need, extra=True, people=True, least=False):
            """need shots for one voiced block: ps first (not on screen yet in this ad), then the other moments of their
            clips, then (extra) any unseen shot of the product; nothing unseen left: an unseen photo, else ps. Never a
            customer's own clip or a moment someone talks (unfit); at most 2 shots of one clip, 4 s apart (crowded).
            people=False: no shot with a person in it (under 'Here's <customer> ...' another woman would pose as her)."""
            got, pool_ = [], list(ps) + [m for p in ps for m in moments(p)]
            if extra:
                pool_ += [x for x in rot(all_shots, v + o + len(shown)) if (x[0], x[1]) not in scenes]
            ok_ = (lambda p: True) if people else (lambda p: not has_person(p))
            for p in pool_:
                if len(got) >= need:
                    break
                if p and not is_shown(p) and not any(near(p, g) for g in got) and not unfit(p) and not crowded(p, got) \
                        and ok_(p) and pick(p):
                    got.append(p)
            if not got and least and photo_picks:   # (padding) every shot is on screen already: repeat the one shown least
                got = [min(photo_picks, key=lambda p: sum(near(p, q) for q in shown))]   # (the same photo again is punched in)
            got = got or [p for p in photo_picks if not is_shown(p)][:1] or \
                [p for p in ps if p and not unfit(p) and ok_(p)][:1] or photo_picks[:1]
            shown.extend(got)
            return got

        hcs = rot(pr["hook_clips"], v + o)
        hc = next((h for h in hcs if tuple(h) not in feat_picks), hcs[0] if hcs else None)   # not a shot a feature shows
        lead = rot([["photo", f"P{n}"] for n in sorted(pkind) if pkind[n] == LEAD.get(fmt)], v + o)
        if lead:                          # the angle's own opening: a worn / detail photo, or a packshot for the deal
            hc = next((h for h in lead if tuple(h) not in feat_picks), lead[0])
            hcs = [hc] + hcs
        if hc:
            shown.append(hc)
        cb = next((p for p in rot(pr["broll"], v + o) if not is_shown(p)), None)       # kept for the close
        if cb:
            reserved.append(cb)
        hook_ps, hook_more = ([hc] if hc else []), []
        for h in ([hc] + [x for x in hcs if x is not hc]) if hc else []:     # a long hook line: more hook-clip moments
            hook_more += ([] if h is hc else [h]) + moments(h)
        for m in hook_more:
            if len(hook_ps) >= need_for(hook, 0.35):
                break
            if not is_shown(m):
                hook_ps.append(m)
                shown.append(m)
        hook_spare = [m for m in hook_more if not is_shown(m)][:1]           # a real voiceover longer than planned
        shown.extend(hook_spare)
        blocks = [dict(vo=line(vid, "hook", hook, BRAND_VOICE), broll=picks(hook_ps), pad=0.35,
                       **({"spare": picks(hook_spare, fallback=False)} if hook_spare else {}))]
        ovl = [dict(type="label", text=th["label"] or {"features": "LOOK CLOSER", "reviews": "REAL REVIEWS", "colours": "WHICH ONE?",
                                                         "showcase": "TAKE A CLOSER LOOK", "story": "TAKE A CLOSER LOOK",
                                                         "lifestyle": "STYLE IT", "offer": tx["offer_title"] or "THE DEAL"}[fmt],
                    block=0, at=0.1, dur=1.8)]
        k0 = (v * 2 + o2) % len(fs) if fs else 0
        feat_q = [(k0 + j) % len(fs) for j in range(len(fs))]      # each feature, review, clip at most once per video
        if fmt in ("showcase", "story"):
            feat_q = list(range(len(fs)))                           # V09 order: the product's features as listed
        if LEAD.get(fmt):                 # the features the angle's photos show come first
            feat_q.sort(key=lambda i: not any(p and p[0] == "photo" and pkind.get(int(p[1][1:]) if re.fullmatch(
                r"P\d+", str(p[1])) else -1) == LEAD[fmt] for p in fs[i][2]))
        rev_q = rot(pr["reviews"], v + o3)
        cust_q = rot(pr["customer"], v + o3)
        cnt = dict(feat=0, rev=0, colours=0, cust=0)
        tags_said = []                    # the on-screen tags of the features this ad says (the recap uses only these)
        close = ov(tx["close"], f"{vid}_close", f"{pid}_close", f"{bid}_close")

        def est_now():
            return sum(len(said.get(x.get("vo"), "").split()) / WPS + 0.25 + x.get("hold", 0.0) if "vo" in x else
                       x["range"][1] - x["range"][0] for x in blocks) + len(close.split()) / WPS + 0.6

        def add_features(n, cap=None):
            """n features; cap: stop (after 3) where the next one would take the ad, the colours still to come
            included, past cap s."""
            for _ in range(n):
                if not feat_q:
                    return
                col = 0 if cnt["colours"] or len(colour_imgs) < 3 else (len(" ".join(colour_names).split()) + 4) / WPS + 0.6
                if cap and cnt["feat"] >= 3 and est_now() + len(fs[feat_q[0]][0].split()) / WPS + 0.25 + col > cap:
                    return
                txt, tag, ps = fs[feat_q.pop(0)]
                tags_said.append(tag)
                got_ = take(ps, need_for(txt))
                own_ = [m for m in list(ps) + [m for p in ps for m in moments(p)] if m and not is_shown(m) and not unfit(m)
                        and not crowded(m, got_) and pick(m)][:1]   # a longer voice than planned: more of this feature
                shown.extend(own_)
                blocks.append(dict(vo=line(vid, f"feat{cnt['feat']}", txt, BRAND_VOICE), broll=picks(got_),
                                   **({"spare": picks(own_, fallback=False)} if own_ else {})))
                ovl.append(dict(type="tag", text=tag, block=len(blocks) - 1, at=0.15, dur=2.6))
                cnt["feat"] += 1

        def add_reviews(n):
            for _ in range(n):
                if not rev_q:
                    return
                rn = rev_q.pop(0)
                text = ("Here's what customers are saying. " if cnt["rev"] == 0 else "") + third(rn, revs)
                br = take(rot(pr["broll"], v + o + cnt["rev"] + 1), need_for(text))
                blocks.append(dict(vo=line(vid, f"rev{cnt['rev']}", text, BRAND_VOICE), broll=picks(br)))
                ovl.append(dict(type="review", n=rn, block=len(blocks) - 1, at=0.1, until_block_end=True))
                cnt["rev"] += 1

        def add_customer(n=1):
            """The narrator introduces a real customer, then she speaks: n ranges of one clip in time order (showcase: as
            many as fit under SHOWCASE_MAX), each a run of whole sentences (cadence-checked ranges)."""
            if not cust_q:
                return
            c0 = cust_q[0]
            run = sorted([c for c in cust_q if c[:2] == c0[:2]], key=lambda c: c[2])[:n] if n > 1 else [c0]
            text = intro_of(c0, v + o + cnt["cust"])
            blocks.append(dict(vo=line(vid, f"intro{cnt['cust']}", text, BRAND_VOICE),
                               broll=picks(take(rot(pr["broll"], v + o + 2), need_for(text), people=False))))
            for k_, (s_, key_, a_, e_) in enumerate(run):
                if k_ and est_now() + e_ - a_ > (STORY_MAX if fmt == "story" else SHOWCASE_MAX):
                    break
                cust_q.remove([s_, key_, a_, e_])
                blocks.append(dict(clip=clip(b, s_, key_), range=[a_, e_]))
                if not k_:
                    ovl.append(dict(type="label", text="REAL CUSTOMER", block=len(blocks) - 1, at=0.3, dur=2.0))
            cnt["cust"] += 1

        def add_colours():
            if cnt["colours"] or len(colour_imgs) < 3:
                return
            cnt["colours"] = 1
            sw = [(n, os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")) for n, _ in colour_imgs[:6]]
            shown_ = {n.lower() for n, _ in sw}         # say the colours in the swatch order, so each name lands on
            ns = [n for n, _ in sw] + [n for n in colour_names if n.lower() not in shown_]   # its bag (the rest after)
            ctext = (", ".join(ns[:-1]) + ", or " + ns[-1] if len(ns) > 1 else ns[0]) + ". " + colours_tail
            wts = [len(n.split()) + 0.35 for n, _ in sw]                    # a swatch per spoken name (word timing)
            wts[-1] += sum(len(n.split()) + 0.35 for n in ns[len(sw):]) + 0.8 + len(colours_tail.split())   # + the rest
            blocks.append(dict(vo=line(vid, "colours", ctext, BRAND_VOICE),
                               broll=[[os.path.relpath(f, out), 0, round(w_, 2), {"zoom": [1.0, 1.06]}]
                                      for (_, f), w_ in zip(sw, wts)]))
            names_ = " · ".join(n.upper() for n in ns)       # a long tag is shrunk to fit and hard to read: the count
            ovl.append(dict(type="tag", text=names_ if len(ns) <= 4 and len(names_) <= 28 else f"{len(ns)} COLOURS",
                            block=len(blocks) - 1, at=0.1, dur=3.0))

        # ---- padding for a thin product (a Drive folder with 0-4 feature lines is normal): blocks that only restate what
        # the client's folder says, each only when the notes back it (colours named in the notes, the price, the gift, the
        # features' own tags): nothing new is claimed, compliance checks every line like any other
        def note_block(key, text, tag=None, label=None):
            blocks.append(dict(vo=line(vid, key, text, BRAND_VOICE),
                               broll=picks(take([], need_for(text), least=True), fallback=False)))
            if tag:
                ovl.append(dict(type="tag", text=tag, block=len(blocks) - 1, at=0.1, dur=3.0))
            if label:
                ovl.append(dict(type="label", text=label, block=len(blocks) - 1, at=0.2, dur=2.4))

        def gift_said():                  # how often the ad says the gift so far (the close does: at most twice in all)
            g_ = (deal_of(pr["offer"])[1] or "").lower()
            return bool(g_) * (sum(g_ in said.get(x.get("vo"), "").lower() for x in blocks) + (g_ in close.lower()))

        def add_colour_names():           # the colours the notes name, said over the product (no swatch photos matched)
            ns = list(dict.fromkeys(n.strip() for n in ((pr.get("facts") or {}).get("colours") or []) if n.strip()))[:6]
            if cnt["colours"] or len(ns) < 2:
                return
            cnt["colours"] = 1
            note_block("colours", "Choose your colour: " + ", ".join(ns[:-1]) + ", or " + ns[-1] + ". " + colours_tail,
                       tag=f"{len(ns)} COLOURS")

        def add_recap():                  # the features' own tags in one sentence, then the product's name
            tg = [t for t in dict.fromkeys(tags_said) if new_product.known_tag(t)]   # (a tag of two odd words is not read out)
            if len(tg) < 2 or cnt.get("recap"):
                return
            cnt["recap"] = 1
            lst = [tcase(t, "sentence" if i == 0 else "lower") for i, t in enumerate(tg[:4])]
            note_block("recap", ", ".join(lst[:-1]) + " and " + lst[-1] + f". That's the {pr['short']}.")

        def add_price():                  # the price the client's notes give (and the was price): never more than they say
            fct = pr.get("facts") or {}
            price, was = new_product.money(fct.get("price")), new_product.money(fct.get("compare_at"))
            if not price or cnt.get("price") or not fct.get("price_source"):
                return
            cnt["price"] = 1
            say = lambda x: f"${x:.0f}" if abs(x - round(x)) < 0.005 else f"${x:.2f}"   # noqa: E731
            if was and was > price:
                note_block("price", f"Now {say(price)}, down from {say(was)}.", label=f"NOW {say(price)}")
            else:
                note_block("price", f"The {pr['short']} is {say(price)}.", label=say(price))

        def add_gift():                   # the notes' free gift, when the ad has not said it twice already
            if cnt.get("gift") or gift_said() >= 2:
                return
            t_ = tpl("And it comes with {gift_sp}.", s_v)
            if t_:
                cnt["gift"] = 1
                note_block("gift", t_)

        pad_steps = [add_colour_names, add_recap, add_price, add_gift] if new_prod else []
        # a new product (no reviews, no customer clips): every feature line its notes give (3-7) while the ad stays
        # under NEW_MAX s, so 6-7 good lines make a 40-60 s ad; 3-5 lines run shorter (plan warns)
        nfeat, cap = ((3 if fmt == "features" else 2), None) if rich else (len(fs), NEW_MAX)
        if fmt == "showcase":         # V09: look closer -> features with tags -> real customer -> colours -> offer
            add_features(min(len(fs), 4) if cust_q else len(fs), cap); add_customer(len(cust_q))  # noqa: E702
            if not cnt["cust"]:
                add_reviews(2)
            add_colours()
        elif fmt == "story":          # the long version: every feature, the customer in full, what customers say, colours
            add_features(len(fs)); add_customer(len(cust_q)); add_colours()  # noqa: E702
            while rev_q and est_now() < STORY_MAX - 8:     # what customers say: as many reviews as fit (3+)
                add_reviews(1)
        elif fmt == "features":
            add_features(nfeat, cap); add_customer(); add_reviews(2)  # noqa: E702
            if not rich:
                add_colours()
        elif fmt == "reviews":
            add_reviews(3); add_customer(); add_features(nfeat, cap)  # noqa: E702
        elif fmt in ("lifestyle", "offer"):   # (a new product's angles: the opening and the order make them)
            add_features(nfeat, cap); add_colours()  # noqa: E702
        else:
            add_colours(); add_customer(); add_reviews(2); add_features(nfeat, cap)  # noqa: E702
        while est_now() < (90 if fmt == "story" else TARGET):   # too short: add what this ad hasn't shown yet (never twice)
            nb = len(blocks)
            if feat_q:
                add_features(1)
            elif rev_q:
                add_reviews(1)
            elif cnt["colours"] == 0 and len(colour_imgs) >= 3:
                add_colours()
            elif cust_q:
                add_customer()
            elif pad_steps:               # a thin product: its colours, a recap, the price, the gift (the notes back each)
                pad_steps.pop(0)()
            if len(blocks) == nb and not pad_steps:
                break
        if new_prod and fmt != "story" and TARGET - est_now() > 0.4:
            # still short: every middle line holds the picture a moment after it (a second, closer look at the product: more
            # shots of it, the same photo punched in when no other is left), never the hook and never the close
            el = [x for x in blocks[1:] if "vo" in x]
            h_ = round(min(HOLD_MAX, (TARGET - est_now()) / len(el)), 2) if el else 0
            for x in el if h_ >= 0.2 else []:
                x["hold"] = h_
                more = math.ceil((len(said.get(x["vo"], "").split()) / WPS + 0.25 + h_) / 3.9) - len(x["broll"])   # (<= 4 s a shot)
                if more > 0:                  # first the feature's own other moments (kept as spares: on screen only when the
                    sp_ = x.pop("spare", [])  # voice runs long), then any unseen shot of the product
                    x["broll"] = x["broll"] + sp_[:more]
                    if more > len(sp_):
                        x["broll"] = x["broll"] + picks(take([], more - len(sp_), least=True), fallback=False)
        if {f"{vid}_close", f"{pid}_close", f"{bid}_close"} & used and tx["offer_title"] and tx["offer_word"]:
            ow = tx["offer_word"]
            if ow not in close.lower() and (not ow.isdigit() or new_product.say(int(ow)).split("-")[0] not in close.lower()):
                warnings.append(f"{vid}: the --lines close has no '{ow}' (or its spoken word): the offer card will not show")
        on = {rel(f) for f in (photo_file(p) for p in shown if p and p[0] == "photo") if f}
        ph = next((f for f in rot([rel(f) for f in packs], v + o) if f not in on), rel(packs[(v + o) % len(packs)]) if packs else None)
        cl = ([[ph, 0, 1.0, dict({"zoom": [1.0, 1.06]}, **next((fit_of(f) for f in packs if rel(f) == ph), {}))]]
              if ph else []) + \
            [x for x in picks([cb] if cb else [], fallback=False, w=1.2) if x[0] != ph]
        if cl and len(cl) < need_for(close, 0.6):          # a long close (theme lead + offer): more shots
            cl += [x for x in picks(take([], need_for(close, 0.6) - len(cl)), fallback=False) if x[0] != ph]
        # a framed (fit) shot under the close sits higher: the offer label and the end card band (y 1120-1510) never
        # cover the bag
        cl = [x[:3] + [dict(x[3], fit_y=CLOSE_FIT_Y)] if len(x) > 3 and x[3].get("fit") else x for x in cl or picks([])]
        blocks.append(dict(vo=line(vid, "close", close, BRAND_VOICE), broll=cl))
        if pr["source"] != "built-in":    # a photo shown again in this ad (few photos): punched in closer, so it reads as a new shot
            seen_st = {}
            for blk in blocks[:-1]:       # (not the close: its framing is set above the end card band, fit_y)
                for x in blk.get("broll") or []:
                    if str(x[0]).lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        k_ = seen_st[x[0]] = seen_st.get(x[0], -1) + 1
                        if k_:                # (zoom 1.2-1.4 keeps the bag in frame; the framing also moves a little each time)
                            z_ = (1.2, 1.32)[(k_ - 1) % 2]
                            ex_ = dict(x[3]) if len(x) > 3 else {}
                            mv_ = (0.0, -0.05, 0.07)[k_ % 3]
                            x[:] = x[:3] + [dict(ex_, zoom=[z_, round(z_ + 0.1, 2)], **(
                                {"fit_y": round(0.42 + mv_, 2)} if ex_.get("fit") else {"focus": [0.5, round(0.5 + mv_, 2)]}))]
        if any(not blk.get("broll") for blk in blocks if "vo" in blk):
            sys.exit(f"{pr['name']}: no footage or photo to show under the voiceover (product has no clips, no clean "
                     f"photos and no site page). Add clips/photos to its Drive folder and re-run the intake.")
        offer = (dict(block=len(blocks) - 1, word=tx["offer_word"], title=tx["offer_title"], sub=tx["offer_sub"])
                 if tx["offer_title"] and tx["offer_word"] else None)
        spare = [x for x in rot(all_shots, v + o) if not is_shown(x) and not unfit(x)][:6]
        spec = dict(blocks=blocks, overlays=ovl, end_title=pr["end"], offer=offer,
                    keywords=list(dict.fromkeys(tx["keywords"] + THEME_WORDS[theme_key])),
                    spare_broll=picks(spare, fallback=False),
                    music=False if getattr(a, "no_music", False) else dict(seed=(a.seed - 1) * 11 + v + 1))   # a bed under the voice (music.py;
        #                                                   the project's versions share it: projects.py copies the spec)
        return f"{prefix}_{vid}_{fmt}", spec, dict(name=f"{prefix}_{vid}_{fmt}", id=vid, format=fmt, engine="storyboard", hook=hook)

    # ---------- AI scenes (ai_gen.py, owner 2026-10-20: the statics repeated across batches): the REAL bag placed in new scenes.
    # About 40% of the statics become scene statics (scene / scene_quote / scene_price: each replaces a real-photo slot and keeps
    # that static as its "fallback") and a few 9:16 clips join the ugc shot pool. Nothing is made here: $OUT/ai_needed.json lists
    # what to generate (the agent does, with Higgsfield), `ai_gen.py gate / clips` check it, render swaps whatever failed back to
    # the real photo / real footage (ai_gen.apply). The plan is inside the batch cap (voiceover + AI = 100 credits).
    ai_plan = dict(stills=[], clips=[], est_credits=0.0, budget={}, notes=[])
    if need and not getattr(a, "no_ai", False) and not getattr(a, "classic", False) and (a.statics or (a.videos and not story)):
        ai_refs = [dict(file=f_, colour=n_) for n_, f_ in colour_imgs if f_ in packs and f_ not in no_static]
        ai_refs += [dict(file=f_, colour=None) for f_ in packs if f_ not in {r_["file"] for r_ in ai_refs} and f_ not in no_static]
        try:
            ai_plan = ai_gen.plan_ai(
                name=pr["name"], slug=novelty.slug_of(pr["name"]), refs=ai_refs, n_statics=len(statics),
                boost=min(4, sum(max(c_ - 1, 0) for l_, c_ in collections.Counter(
                    x["layout"] for x in statics).items() if l_ in ("compare", "bold", "promo", "hero", "checklist"))),
                n_clips=min(ai_gen.MAX_CLIPS, max(3, 2 * a.videos)) if a.videos and not story else 0,
                tts_est=4.5 * a.videos if not story else 0, seed=a.seed, out=out, cap=getattr(a, "ai_cap", None),
                grade_refs=[c_ for c_ in clips if c_][:4],
                static_layouts=["scene", "scene_quote" if clean_mode and quote_revs else "scene", "scene",
                                "scene_price" if value_ok else "scene", "scene", "scene_quote" if clean_mode and quote_revs else "scene",
                                "scene", "scene"])
        except Exception as e:  # noqa: BLE001 - the AI part must never stop a batch: real photos and footage still work
            warnings.append(f"AI scenes skipped ({type(e).__name__}: {e}): real photos and footage only")
        warnings += [f"AI scenes: {x}" for x in ai_plan.get("notes") or []]

    def ai_slot(lay_):                # the static a scene static replaces: the text-heavy ones first (a scene photo is the cleaner
        # twin), then the real-photo ones (the scenes exist because those repeat); a BOF layout only when it has a twin; three
        # studio statics and the first of checklist / stars / quotes / value stay
        for ln, keep in {"scene": (("bold", 0), ("compare", 0), ("promo", 0), ("hero", 0), ("native", 0), ("lifestyle", 0),
                                   ("review", 0), ("checklist", 1), ("studio", 3)),
                         "scene_quote": (("quotes", 1), ("stars", 1), ("review", 1)),
                         "scene_price": (("value", 1), ("offer", 1))}[lay_]:
            idx = [i_ for i_, x in enumerate(statics) if x["layout"] == ln and "ai" not in x]
            if len(idx) > keep:
                return idx[-1]
        return None
    ai_dropped, n_sc = [], 0
    for k_, s_ in enumerate(x for x in ai_plan["stills"] if x["use"] == "static"):
        i_ = ai_slot(s_["layout"])
        if i_ is None:
            ai_dropped.append(s_["id"])
            continue
        orig_, lay_, hv_ = statics[i_], s_["layout"], k_ + sseed - 1
        d_ = static({"scene": "native", "scene_quote": "quotes", "scene_price": "value"}[lay_], s_["file"], hv_)
        d_["layout"] = lay_
        if lay_ == "scene_quote":
            d_["reviews"] = d_["reviews"][:1]
        elif lay_ == "scene":         # the clean look: the scene statics alternate pill only / caption only / photo alone / caption + pill
            n_sc += 1                 # (n_sc % 4 = 1: pill only, 2: caption only, 3: photo alone, 0: caption + pill: half carry no caption)
            d_.pop("headline", None)
            if n_sc % 2 == 0:         # a caption from the product's own feature tags, the ones that fit the scene first, never twice
                taken_ = {x.get("caption") or x.get("headline") for x in statics}
                want_ = {"worn": ("strap", "shoulder", "wear", "carry", "hand"), "hand": ("strap", "carry", "hand", "room"),
                         "object": ("room", "zip", "finish", "shape", "pocket", "secure", "storage")}.get(s_["kind"], ())
                cand_ = sorted(tags, key=lambda t: (not any(w_ in t.lower() for w_ in want_), tags.index(t)))
                pool_ = [tcase(t, "sentence") + "." for t in cand_] + \
                    [". ".join(tcase(t, "sentence") for t in cand_[j_:j_ + 2]) + "." for j_ in range(len(cand_) - 1)] + \
                    [f"The {pr['short']}.", hero]
                d_["caption"] = next((c_ for c_ in pool_ if c_ not in taken_), pool_[0])
            else:
                d_.pop("caption", None)
            if n_sc % 4 in (2, 3):    # (a caption alone / the photo alone: no pill)
                d_.pop("pct", None)
        d_.update(name=re.sub(r"(_S\d+_).*$", lambda m_: m_.group(1) + lay_, orig_["name"]),
                  ai=dict(id=s_["id"], scene=s_["scene"], colour=s_.get("colour")), fallback=orig_)
        statics[i_] = d_
    if ai_dropped:                    # no slot left for them: not generated (the credits are not spent)
        ai_plan["stills"] = [x for x in ai_plan["stills"] if x["id"] not in ai_dropped]
    ai_clips.update({c_["id"]: c_ for c_ in ai_plan["clips"]})

    # ---------- ugc storyboards: the default storyboard format since 2026-10-14 (--classic keeps the formats above). The script
    # engine (ugc_script.py) writes one script per project in the 'you' voice: a hook, 5-9 chapters (one voice take each, shared by
    # the project's hook versions), the offer last. The board is the hook block + one block per chapter, every block's footage
    # matched to the words of its phrases (storyboard cuts the picture where a phrase starts); the owner's reference ads
    # (187-220 wpm, a new shot every ~2 s, numbered chapters, one steady loudness) are the target (scorecard.py measures it).
    STILLS = (".jpg", ".jpeg", ".png", ".webp")
    ugc_voice, ugc_speed = voice_cfg()
    ugc_sc, ulib, dnote, dlong = [], [], {}, {}
    if a.videos and not story and not getattr(a, "classic", False):
        import ugc_script
        try:
            nl_ = novelty.load()               # what the product's last batches said (novelty.py): other hooks, other words
            ugc_sc = ugc_script.scripts(pr, n=a.videos, seed=a.seed, hooks=a.hooks, avoid=dict(
                hooks=novelty.recent(pr["name"], "hook", log=nl_),
                sentences=[t_ for b_ in novelty.batches(pr["name"], log=nl_)[-novelty.LAST:] for v_ in b_.get("videos") or []
                           for t_ in v_.get("chapters") or []]))
        except Exception as e:  # noqa: BLE001 - the script engine must not stop a batch: the classic format still works
            warnings.append(f"ugc script engine failed for {pr['name']} ({type(e).__name__}: {e}): the classic format is used")
        if not ugc_sc and not any("ugc script engine failed" in w for w in warnings):
            warnings.append(f"{pr['name']} has no feature lines for a ugc script: the classic format is used (3-7 one-line "
                            f"features in the product's notes make the ugc videos)")

    def gen_moments(dur, cap=6):      # a clip with no vetted moments: starts about 4 s apart, the last one 3 s before its end
        if not dur or dur < 3.0:
            return [0.0]
        n = min(cap, int((dur - 3.0) // 4.0) + 1)
        return [round(0.5 + k * ((dur - 3.5) / max(n - 1, 1) if n > 1 else 0), 1) for k in range(n)]

    def ugc_lib():
        """The product's footage as matchable shots [{p, kw, tag, kind, src, pen, only, hook, long}]: its feature picks and their other vetted
        moments (tag = the feature), B-roll and hook clips, every other clip of its clip_bank sections (the vetted moments, else
        one about every 4 s), the client's library footage of a built-in bag (clip_index.json), then the photos. kw = footage
        keywords (kw_terms of the notes, the feature line); pen = how much to avoid it; only = keywords one of which the text
        must have (gift reveals / unboxing). One entry per moment (near): the same shot is never listed twice."""
        if ulib:
            return ulib

        def note_kw(p):
            if p[0] == "photo":
                return set()
            if p[0] == "clip":
                c = pr["clips"][p[1]] if isinstance(p[1], int) and 0 <= p[1] < len(pr["clips"]) else {}
                return kw_terms(f"{c.get('name', '')} {c.get('notes', '')}")
            if p[0] == "drive":
                return kw_terms(dnote.get(p[1], ""))
            return kw_terms(f"{((b.get(p[0]) or {}).get(p[1]) or {}).get('notes', '')} {str(p[1]).replace('_', ' ')}")

        def long_clip(p):             # a compilation (30 s +): its moments are different scenes, so cutting it again is no repeat
            if p[0] == "drive":
                return dlong.get(p[1], False)
            if p[0] == "clip":
                c = pr["clips"][p[1]] if isinstance(p[1], int) and 0 <= p[1] < len(pr["clips"]) else {}
                return float(c.get("dur") or 0) >= 60
            return float(((b.get(p[0]) or {}).get(p[1]) or {}).get("dur") or 0) >= 60

        def add(p, extra=(), tag=None, kind="clip", pen=0.0, only=(), hook=False):
            if not p or unfit(p) or any(near(p, e["p"]) for e in ulib):
                return
            x = pick(p)
            if x:                   # once: a photo of kind 'other' (a product page's diagram with its words) is shown whole, one time
                f_ = photo_file(p) if p[0] == "photo" else None
                ulib.append(dict(p=list(p), kw=note_kw(p) | set(extra), tag=tag, kind=kind, src=str(x[0]), pen=pen, only=set(only),
                                 hook=hook, long=kind == "photo" or long_clip(p), once=pkind.get(pnum.get(f_)) == "other"))
        for line_, tag_, ps_ in fs:
            fk = kw_terms(f"{line_} {tag_}")
            for p in ps_:
                add(p, fk, tag_, "photo" if p and p[0] == "photo" else "clip")
                for m in moments(p):
                    add(m, fk, tag_)
        for p in pr["hook_clips"] + pr["broll"]:               # (the hook clips are the editor's picks for an opening)
            add(p, (), None, "photo" if p and p[0] == "photo" else "clip", hook=p in pr["hook_clips"])
            for m in moments(p):
                add(m)
        for i_, c_ in enumerate(pr["clips"]):                  # a product file's own clips: every moment it lists, else spread
            if i_ < len(clips) and clips[i_]:
                for g in c_.get("good") or gen_moments(c_.get("dur"), 5):
                    add(["clip", i_, g])
        secs = list(dict.fromkeys(p[0] for p in pr["broll"] + pr["hook_clips"] + [x for f in fs for x in f[2]] if p and p[0] in b))
        for sec in secs:
            for key, e in b[sec].items():
                notes = e.get("notes", "") if isinstance(e, dict) else ""
                if not isinstance(e, dict) or key.startswith("ai_") or (sec, key) in scenes or "REAL CUSTOMER" in notes or e.get("text"):
                    continue                  # (a clip with "text": printed words fill its frame: the captions sit on them)
                gift = bool(re.search(r"gift|unbox|reveal|reaction", f"{notes} {key}", re.I))
                for g in e.get("good") or gen_moments(e.get("dur"), 6):
                    add([sec, key, g], (), None, "clip", 1.5 if "lips" in notes else 0.0,
                        {"gift", "pouch", "wallet", "unbox", "free"} if gift else ())
        if pr["source"] == "built-in":
            taken = {e["id"] for d_ in b.values() if isinstance(d_, dict) for e in d_.values() if isinstance(e, dict) and e.get("id")}
            for id_, dur_, note_ in index_clips(pk, taken):
                dnote[id_], dlong[id_] = note_, dur_ >= 60
                for g in gen_moments(dur_, 5):
                    add(["drive", id_, g], (), None, "clip", 0.5)
        for c_ in ai_plan["clips"]:    # planned AI clips (ai_gen.py): scenes the client never filmed (a cafe, the street), matched on
            ulib.append(dict(p=["ai", c_["id"], 0.0], kw=kw_terms(" ".join(c_["tags"])), tag=None, kind="clip",   # their scene words
                             src=ai_gen.clip_file(out, c_["id"]), pen=0.0, only=set(), hook=False, long=False, once=False))
        for p in photo_picks:
            f_ = photo_file(p)
            kind_ = pkind.get(pnum.get(f_)) or "packshot"
            add(p, {"packshot": {"hero", "packshot", "product"}, "worn": {"wear", "shoulder", "walk", "hand"},
                    "detail": {"detail", "leather", "zip", "stitch", "hardware"}}.get(kind_, ()), None, "photo",
                0.5 if pr["source"] != "built-in" else 2.0)
        return ulib

    def ugc_board(v, vid, bid, sc):
        """(name, spec, plan entry) of project v from its script sc: see the block above."""
        lib, pid = ugc_lib(), "P" + vid[1:]
        uses, jit = {}, v * 5 + a.seed * 3
        hk, alts = dict(sc["hook"]), [dict(h) for h in sc["alt_hooks"]]
        if theme_key != "default" and tx["hooks"]:        # a themed request: its own opening first, the script's hook is H2's pool
            tl = tx["hooks"][v % len(tx["hooks"])]
            alts = [hk] + [h for h in alts if h["text"] != tl]
            hk = dict(text=tl, type=hook_type_of(tl), label=th["label"] or hk["label"], feature=None)
        hook = ov(hk["text"], f"{vid}_hook", f"{pid}_hook", f"{bid}_hook")
        if hook != hk["text"]:         # a --lines hook: its own type, a label that fits it, no feature footage
            ty_ = hook_type_of(hook)
            hk = dict(text=hook, type=ty_, feature=None, label=th["label"] or dict(
                question="QUICK QUESTION", price="THE DEAL").get(ty_, "LOOK CLOSER"))
        chs = [dict(c) for c in sc["chapters"]]
        close = ov(None, f"{vid}_close", f"{pid}_close", f"{bid}_close")
        if close is None and theme_key != "default" and chs[-1]["kind"] == "offer" and tx["offer_word"]:
            ow_ = tx["offer_word"]       # a themed request: the theme's close, when it says the offer word the card waits for
            if ow_.lower() in tx["close"].lower() or (ow_.isdigit() and new_product.say(int(ow_)).split("-")[0] in tx["close"].lower()):
                close = tx["close"]
        if close is not None and chs[-1]["kind"] == "offer":
            chs[-1]["text"] = close
            if sc["offer"] and tx["offer_word"]:
                ow = tx["offer_word"]
                if ow not in close.lower() and (not ow.isdigit() or new_product.say(int(ow)).split("-")[0] not in close.lower()):
                    warnings.append(f"{vid}: the --lines close has no '{ow}' (or its spoken word): the offer card will not show")
        sw = [(n, os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")) for n, _ in colour_imgs[:6]]

        recent = []                   # the sources already chosen for this block (a short clip is not cut into it again and again)
        ai_n = [0]                    # AI clips chosen so far in this video (capped: AI_SHOTS_MAX)
        ai_mine = {c_["id"] for c_ in ai_plan["clips"][::1]}      # a project draws on 4 of the batch's AI clips (others: other projects),
        if len(ai_mine) > 4:                                       # so the AI scenes do not repeat in every video
            ids_ = sorted(ai_mine)
            ai_mine = {ids_[(v * 3 + j_) % len(ids_)] for j_ in range(4)}

        def choose(terms, cterms, feat, prev, use, kinds=None, hook=False):
            best = None
            for i, e in enumerate(lib):
                if e["p"][0] == "ai" and (ai_n[0] >= AI_SHOTS_MAX or e["p"][1] not in ai_mine):   # (mostly the real footage)
                    continue
                if (e["only"] and not e["only"] & (terms | cterms)) or (kinds and e["kind"] not in kinds) or (e["once"] and use.get(i)):
                    continue
                s = 3.0 * len(e["kw"] & terms) + 1.5 * len(e["kw"] & cterms) + (6.0 if feat and e["tag"] == feat else 0.0) \
                    + (4.0 if hook and e["hook"] else 0.0) + (2.5 * bool(e["kw"] & HOOK_MOVE) - 2.5 * ("hang" in e["kw"]) if hook else 0.0) - e["pen"] - 6.0 * (prev is not None and e["src"] == prev and not e["long"]) \
                    - 5.0 * recent.count(e["src"]) * (not e["long"]) - 0.01 * ((i * 7 + jit) % 13)
                if best is None or (use.get(i, 0), -s) < best[0]:     # the fewest showings first: never the same moment
                    best = ((use.get(i, 0), -s), i)                  # twice while another is left, then the best match
            if best is None:
                return None
            use[best[1]] = use.get(best[1], 0) + 1
            ai_n[0] += lib[best[1]]["p"][0] == "ai"
            recent.append(lib[best[1]]["src"])
            return best[1], use[best[1]] - 1

        def framed(i, k):             # the k-th showing of one moment: a closer framing, so it reads as another shot
            x = pick(lib[i]["p"])
            if not k or not x:
                return x
            ex, z = dict(x[3]) if len(x) > 3 else {}, (1.2, 1.32)[(k - 1) % 2]
            if str(x[0]).lower().endswith(STILLS):
                mv = (0.0, -0.05, 0.07)[k % 3]
                ex.update(zoom=[z, round(z + 0.1, 2)], **({"fit_y": round(0.42 + mv, 2)} if ex.get("fit") else {"focus": [0.5, round(0.5 + mv, 2)]}))
            else:
                ex.update(zoom=[1.3, 1.36] if k == 1 else [1.6, 1.66], focus=[0.5, 0.55 if k == 1 else 0.42])
            return x[:3] + [ex]

        def swatches_of(text):       # the colours block: every swatch (the colours the chapter names first, in its order), each
            pos = {x[0]: (m_.start() if (m_ := re.search(r"\b" + re.escape(x[0].lower()) + r"\b", text.lower())) else 1e9) for x in sw}
            return [[os.path.relpath(x[1], out), 0, 1.0, {"zoom": [1.0, 1.06], "say": x[0].lower()}]       # 'say': storyboard shows
                    for x in sorted(sw, key=lambda x: pos[x[0]])]                                          # it where that name is said
        cterms = {"hook": kw_terms("hero hand")}      # (an opening on hands moves; a bag hanging on a chair does not)
        texts = [("hook", hook)] + [(c["id"], c["text"]) for c in chs]
        slots = {k_: ugc_slots(t_, ugc_speed, UGC_HOOK_PAD if k_ == "hook" else UGC_JOIN) for k_, t_ in texts}
        main, prev, nsl = {}, None, 0
        for k_, t_ in texts:          # the hook first (its shots are its own), then each chapter's phrases in order
            ch = next((c for c in chs if c["id"] == k_), None)
            ct = cterms["hook"] if ch is None else kw_terms(" ".join(ch["shot_kw"] + [ch["tag"] or ""]))
            feat = hk.get("feature") if ch is None else ch["feature"]
            colour = ch is not None and len(sw) >= 3 and "colour" in kw_terms(" ".join(ch["shot_kw"])) and ch["kind"] != "offer"
            ps = swatches_of(t_) if colour else []       # (however many phrases the voice makes: a shot per colour named)
            recent.clear()
            for j, (st_, _) in enumerate(() if colour else slots[k_]):
                last_slot = ch is not None and ch is chs[-1] and j == len(slots[k_]) - 1
                c_ = choose({"packshot", "hero"}, {"hero"}, None, prev, uses, {"photo"}) if last_slot and packs else None
                c_ = c_ or choose(kw_terms(st_), ct, feat, prev, uses, hook=ch is None)
                x_ = framed(*c_) if c_ else None
                if x_:
                    if last_slot and len(x_) > 3 and x_[3].get("fit"):
                        x_ = x_[:3] + [dict(x_[3], fit_y=CLOSE_FIT_Y)]    # (above the end card band, as the classic close)
                    ps.append(x_)
                    prev = str(x_[0])
            main[k_] = ps
            nsl += len(ps)
        spuse, spares = dict(uses), {}
        recent.clear()
        for k_, t_ in texts:          # the spares: shots no block shows (a long phrase is split onto them), the block's own kind
            ch = next((c for c in chs if c["id"] == k_), None)
            ct = cterms["hook"] if ch is None else kw_terms(" ".join(ch["shot_kw"] + [ch["tag"] or ""]))
            more = sum(n_ - 1 for _, n_ in slots[k_]) + (1 if k_ == "hook" else 2)
            colour = ch is not None and len(sw) >= 3 and "colour" in kw_terms(" ".join(ch["shot_kw"])) and ch["kind"] != "offer"
            sp = []
            recent.clear()
            for _ in range(0 if colour else more):
                c_ = choose(ct, ct, hk.get("feature") if ch is None else ch["feature"], None, spuse)
                x_ = framed(*c_) if c_ else None
                if x_ and not any(x_[0] == y[0] and x_[1] == y[1] for y in sp):
                    sp.append(x_)
            spares[k_] = sp
        gen = [framed(*c_) for c_ in (choose(cterms["hook"], cterms["hook"], None, None, spuse) for _ in range(6)) if c_]
        if any(not main[k_] for k_, _ in texts):
            sys.exit(f"{pr['name']}: no footage or photo to show under the voiceover (product has no clips, no clean "
                     f"photos and no site page). Add clips/photos to its Drive folder and re-run the intake.")
        blocks, ovl = [], [dict(type="label", text=hk["label"], block=0, at=0.1, dur=1.8)]
        for k_, t_ in texts:
            blk = dict(vo=line(vid, k_, t_, ugc_voice), broll=main[k_], **({"spare": spares[k_]} if spares.get(k_) else {}))
            ch = next((c for c in chs if c["id"] == k_), None)
            if ch is not None and ch["number"]:
                blk["number"] = ch["number"]
            blocks.append(blk)
            bi = len(blocks) - 1
            if ch is not None and ch["tag"]:
                ovl.append(dict(type="tag", text=ch["tag"], block=bi, at=0.15, dur=2.6))
            for n_ in (ch or {}).get("reviews") or []:
                nm = revs[n_]["name"].split()[0].rstrip(".") if n_ in revs else ""
                ovl.append(dict(type="review", n=n_, block=bi, word=(nm if len(nm) > 1 else "customer").lower(), dur=2.8))
        offer = (dict(block=len(blocks) - 1, word=sc["offer"]["word"], title=tx["offer_title"], sub=tx["offer_sub"])
                 if sc["offer"] and tx["offer_title"] and tx["offer_word"] else None)
        kws = list(dict.fromkeys(tx["keywords"] + THEME_WORDS[theme_key] + [k for c in chs for k in c["keywords"]]))
        spec = dict(mode="ugc", voice_speed=ugc_speed, blocks=blocks, overlays=ovl, end_title=pr["end"], offer=offer,
                    keywords=kws, spare_broll=[x for x in gen if x],
                    music=False if getattr(a, "no_music", False) else dict(seed=(a.seed - 1) * 11 + v + 1))
        name = f"{prefix}_{vid}_{UGC_ANGLE[sc['angle']]}"
        return name, spec, dict(name=name, id=vid, format="ugc", engine="storyboard", hook=hook,
                                ugc=dict(script=sc["id"], angle=sc["angle"], words=sc["words"], hook=dict(type=hk["type"], label=hk["label"],
                                         feature=hk.get("feature")), alt_hooks=alts, numbers=sc["numbers"]))

    seen_v, seen_sc, nsb, per_fmt = {}, set(), 0, {}

    def sigs(spec):                       # (script: the words, customer clips and on-screen texts; everything incl. B-roll)
        sc = [said.get(x["vo"]) if "vo" in x else [x["clip"], x["range"]] for x in spec["blocks"]] + \
            [[x.get("type"), x.get("text"), x.get("n")] for x in spec["overlays"]]
        return json.dumps(sc), json.dumps([sc, [x.get("broll") for x in spec["blocks"]]])
    for v in range(a.videos):
        if v < len(ugc_sc):               # ugc (the default): this project's script; a script too thin to reach the floor
            vid, bid = f"V{W + nsb + 1:02d}", f"B{nsb + 1:02d}"      # (a product with 1-2 feature lines) falls back to classic
            n0, s0 = len(tts), dict(said)
            name, spec, ventry = ugc_board(v, vid, bid, ugc_sc[v])
            est_u = est_ugc(spec, said)
            if est_u >= (MIN_SECONDS if pr["source"] == "built-in" else PLAN_SECONDS):
                nsb += 1
                specs[name] = spec
                videos.append(ventry)
                continue
            del tts[n0:]
            said.clear()
            said.update(s0)
            warnings.append(f"{vid}: the ugc script of {pr['name']} would run ~{est_u:.0f} s (too thin for the ugc format): this "
                            f"project uses the classic format, padded from the notes ({len(fs)} feature line(s))")
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

    # ---------- a storyboard video that cannot reach the floor even after the padding is left out: the statics proceed, the
    # reply names what the client could add (never an exit for the whole plan unless nothing at all is left to make)
    floor_ = MIN_SECONDS if pr["source"] == "built-in" else PLAN_SECONDS      # (a product file's estimate gets the margin)
    short = [v for v in videos if v["engine"] == "storyboard" and est_seconds(specs[v["name"]], said, rw) < floor_]
    if short:
        nm_ = lambda v: ("P" + v["id"][1:]) if pm else v["id"]  # noqa: E731
        gone = {v["name"] for v in short}
        left_out = ", ".join(f"{nm_(v)} ~{round(est_seconds(specs[v['name']], said, rw))} s" for v in short)
        for lst in (videos, keep):
            lst[:] = [v for v in lst if v["name"] not in gone]
        for n_ in gone:
            specs.pop(n_, None)
        tts[:] = [t for t in tts if not any(t["file"].startswith(v["id"] + "_") for v in short)]
        pm = pm and bool(keep)
        fct, add = pr.get("facts") or {}, []
        if pr["source"] != "built-in":
            if len(fs) < 3:
                add.append("3-5 one-line features in the notes (one fact per line)")
            if not fct.get("price") and not any(deal_of(pr["offer"])):
                add.append("the price and the was price (or 'NN% off') in the notes")
            if len(fct.get("colours") or []) < 2:
                add.append("'Colours: ...' in the notes")
            if len(pool) < 4 and not any(clips):
                add.append("more photos or a clip")
        warnings.append(
            f"videos left out: {left_out} "
            f"would run too close to the {MIN_SECONDS} s floor (under {floor_} s planned) even after padding with what "
            f"{pr['name']}'s material backs ({len(fs)} feature line(s), {len(pool)} photo(s), {len([c for c in clips if c])} "
            f"clip(s)): too short to run as an ad. " + (f"To get videos the client could add: {'; '.join(add)}." if add else
                      "Add hook/close lines with --lines, or make fewer videos."))
        if not statics and not keep:
            print(f"{pr['name']}: nothing to make: the videos would run under {floor_} s (floor {MIN_SECONDS} s) and there "
                  f"are no statics to make (none asked for, or no photo without a face). " +
                  (f"The client could add: {'; '.join(add)}." if add else "Add lines with --lines."), file=sys.stderr)
            sys.exit(2)

    # ---------- AI assets: only what the kept ads use is generated (a --only redo, a video left out); ai_needed.json says what
    if ai_plan["stills"] or ai_plan["clips"]:
        spec_txt = json.dumps(specs)
        ai_plan["clips"] = [c_ for c_ in ai_plan["clips"] if f"{c_['id']}_c.mp4" in spec_txt]
        keep_s = {c_["start"] for c_ in ai_plan["clips"]} | {x["ai"]["id"] for x in statics if x.get("ai")}
        ai_plan["stills"] = [s_ for s_ in ai_plan["stills"] if s_["id"] in keep_s]
        ai_plan["est_credits"] = round(sum(x["est_credits"] for x in ai_plan["stills"] + ai_plan["clips"]), 2)
    ai_file = os.path.join(out, "ai_needed.json")
    if ai_plan["stills"]:
        json.dump(dict(ai_plan, steps=ai_gen.STEPS), open(ai_file, "w"), indent=1, ensure_ascii=False)
    elif os.path.exists(ai_file):
        os.remove(ai_file)
    ai_sum = dict(stills=len([x for x in ai_plan["stills"] if x["use"] == "static"]), clips=len(ai_plan["clips"]),
                  est_credits=ai_plan["est_credits"], budget=ai_plan.get("budget"),
                  scenes=sorted({x["scene"] for x in ai_plan["stills"]}),
                  next=f"python3 pipeline/ai_gen.py show --out {out}") if ai_plan["stills"] else None

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
        lo, hi = QA_SECONDS.get(v.get("format"), QA_SECONDS.get(v["engine"], QA_SECONDS["storyboard"]))
        if v in keep and not lo <= v["est_seconds"] <= hi and not (pm and v["est_seconds"] < lo):  # (expand: per version)
            fix = ("" if v["engine"] == "remix" or v.get("format") == "ugc" else ": add lines with --lines"
                   if pr["source"] == "built-in" else ": the product file needs more features/clips, or add lines with --lines")
            warnings.append(f"{vname(v)} thin script: ~{v['est_seconds']:.0f} s (the ugc format runs {lo}-80 s; {pr['name']} has "
                            f"few feature lines, reviews or colours to talk about: it runs as it is)"
                            if v.get("format") == "ugc" and v["est_seconds"] < lo else
                            f"{vname(v)} will run about {v['est_seconds']:.0f} s (QA wants {lo}-{hi} s){fix}")
    story_short = [v for v in keep if v.get("format") == "story" and v["est_seconds"] < 90]
    if story_short:                  # asked for 1.5-2 min, but the product's real material runs out sooner: say so
        warnings.append(f"story format asked for 1.5-2 min, but {', '.join(vname(v) + ' ~' + str(round(v['est_seconds'])) + ' s' for v in story_short)}: "
                        f"all of {pr['name']}'s real material (features, customer clips, reviews, colours) is used. Tell the "
                        "client; for longer, add narrated story lines with --lines or pick a product with more footage")
    est = round(0.35 * len(tts_u), 1)
    limit = a.budget if a.budget is not None else MAX_CREDITS
    pct, gift = deal_of(pr["offer"])
    warnings[:] = list(dict.fromkeys(warnings))
    summary = dict(pipeline=pipe, **({"batch": f"{BATCH['statics']} statics + {BATCH['projects']} projects x {a.hooks} "
                                                 f"hooks (no counts in the request)"} if size["batch"] else {}),
                   statics=len(statics), **({"projects": len(keep), "hooks": a.hooks} if pm else {}), videos=len(videos),
                   tts_lines=len(tts_u), est_credits=est, budget=limit, seed=a.seed, **({"ai": ai_sum} if ai_sum else {}),
                   **({"hook_seed": a.hook_seed} if a.hook_seed is not None else {}),
                   theme=theme_key, theme_name=tname, product=pr["name"], product_source=pr["source"],
                   offer=" + ".join(x for x in (f"{pct}% off" if pct else "no discount", gift) if x), names=prefix,
                   **({"winner_body": ("the RAW body plus a narrated review section (--winner-reviews)" if a.winner_reviews else
                                       "the proven RAW body plays intact (only its editorial cuts; no narrated review section, "
                                       "--winner-reviews adds one), so winner versions need no voiceover; a winner runs as "
                                       "long as its body: ~%d-%d s" % QA_SECONDS["remix"])} if W else {}))
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
             budget=limit, colour_images=dict(colour_imgs), packshots=packs, brief=brief, **({"ai": ai_sum} if ai_sum else {}),
             winners_source=sel["source"] if sel else None, winners_note=sel["note"] if sel else None,
             winners_used=[dict(key=w["key"], name=w.get("name"), roas=w.get("roas"), action=w.get("action"))
                           for w in {x["key"]: x for x in wrows}.values()],
             unmatched_winners=sel["unmatched"] if sel else [], warnings=warnings, winner_reviews=bool(a.winner_reviews),
             seed=a.seed, hooks=a.hooks if pm else 1,     # hooks > 1 and no "projects": the expansion below failed, render refuses it
             pipeline=pipe, **({"batch": True} if size["batch"] else {}),
             video_format="ugc" if any(v.get("format") == "ugc" for v in videos) else "classic",
             **({"ugc_numbers": sorted({n for v in videos for n in (v.get("ugc") or {}).get("numbers") or []}),
                 "voice": dict(ugc_voice, speed=ugc_speed)} if any(v.get("format") == "ugc" for v in videos) else {}),
             **({"fill": dict(winner_projects=W, new_angle_projects=fill)} if fill else {}),
             **({"intake": intake} if intake else {}),
             **({"photo_files": {f"P{n}": rel(f) for n, f in sorted(pfile.items())}} if pfile else {}))   # (projects.py)
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
        if pipe == "winners" and not seed_given and any("open like ads already delivered" in w for w in warnings):
            warnings = list(warnings) + [f"no --seed: each winner project's H1 is its first cold open; a new batch for "
                                         f"the same winners: --seed {datetime.date.today().timetuple().tm_yday} (the day "
                                         f"of the year) makes another opening H1"]
        summary.update(projects=len(p["projects"]), videos=len(p["videos"]), tts_lines=p["tts_lines"],
                       est_credits=p["est_credits"])
        if ai_sum and p["est_credits"] + ai_sum["est_credits"] > ((ai_sum.get("budget") or {}).get("cap") or 100):
            warnings = list(warnings) + [f"voiceover {p['est_credits']} + AI {ai_sum['est_credits']} credits is over the "
                                         f"{(ai_sum.get('budget') or {}).get('cap') or 100}-credit batch cap: generate only the first AI "
                                         f"assets (the AS/AC ids in ai_needed.json, lowest numbers first) or plan with --no-ai"]
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
        by_line = {}                  # a storyboard hook line that opens more than 2 versions of this batch: say so
        for x in p["projects"]:
            for h in x["hooks"] if x["engine"] != "remix" else []:
                by_line.setdefault(projects.norm(h["hook_text"]), [h["hook_text"]]).append(x["id"] + h["hook"])
        warnings = list(warnings) + [f"the hook line \"{v[0]}\" opens {len(v) - 1} versions ({', '.join(v[1:])}): the batch "
                                     f"has few different openings (more: --lines P01_hook ..., a product file's 'hooks')"
                                     for v in by_line.values() if len(v) > 3]
    else:
        listing = dict(winner_videos=[f"{v['name']} ({v['winner']['brief_name']}, " + (
            f"cold open: {v['hook_label']}" if v["winner"]["cold_open"] else f"no cold open, label {v['hook_label']}") + ")"
            for v in videos if v["engine"] == "remix"])
    # ---------- Meta ad copy for every ad (ad_copy.csv: uploaded with the batch) + the compliance check of every text
    if a.products_dir:
        os.environ["LC_PRODUCTS_DIR"] = os.path.abspath(a.products_dir)      # ad_copy / compliance find the product file
    ac, cr = copy_and_check(out, seed=a.seed)
    warnings = list(warnings) + [f"ad copy: {x}" for x in ac["problems"]] + ([f"compliance: {cr['error']}"] if cr.get("error") else [])
    print(json.dumps(dict(plan=os.path.join(out, "plan.json"), **summary, **({"intake": intake} if intake else {}),
                          tts_needed=os.path.join(out, "tts_needed.json"),
                          tts_duplicates=len(dupes), brief=brief, winners_source=p["winners_source"], **listing,
                          unmatched_winners=[f"{u['name']} (ROAS {u.get('roas')}): {u.get('why')}" for u in p["unmatched_winners"]],
                          **copy_summary(ac, cr), warnings=warnings), indent=1, ensure_ascii=False))
    if not cr["ok"]:
        print(f"compliance: {len(cr['problems'])} problem(s) in this batch's text (Julian's rules 2026-10-09 / CLAUDE.md rule "
              f"3, details in {cr['report']}):\n  - " + "\n  - ".join(compliance_lines(cr)) + f"\n{COMPLIANCE_FIX}. Don't "
              f"voice tts_needed.json before it passes.", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------- ad copy + compliance
def copy_and_check(out, seed=1):
    """Meta ad copy for every ad of the plan (ad_copy.py: $OUT/ad_copy.csv + ad_copy.json), then the compliance check of
    every text of the batch, the copy included (compliance.py: $OUT/compliance.json). Returns (ad copy summary,
    compliance report). Run at the end of plan and after projects.py expand; render re-runs the check (compliance_gate)."""
    try:
        import ad_copy
        rep = ad_copy.write(out, seed=seed)
        ac = dict(csv=rep["csv"], rows=rep["rows"], cta=rep["cta"], notes=rep["notes"], problems=rep["problems"])
    except Exception as e:  # noqa: BLE001 - the copy is extra: the creatives can still go (the reply says it is missing)
        for f in ("ad_copy.csv", "ad_copy.json"):        # never a stale copy of another plan in this --out
            if os.path.exists(os.path.join(out, f)):
                os.remove(os.path.join(out, f))
        ac = dict(csv=None, rows=0, notes=[], problems=[f"ad_copy.py failed ({type(e).__name__}: {e}): no ad copy for "
                                                        f"this batch (python3 pipeline/ad_copy.py --out {out})"])
    try:
        cr = check_out(out)
    except Exception as e:  # noqa: BLE001 - a checker bug must not stop a batch: said loudly, the texts are vetted data
        cr = dict(ok=True, error=f"compliance.py failed ({type(e).__name__}: {e}): the texts were NOT checked "
                                 f"(python3 pipeline/compliance.py --out {out})", problems=[], allowed=[], checked=0)
    cr["report"] = os.path.join(out, "compliance.json")
    json.dump(cr, open(cr["report"], "w"), indent=1, ensure_ascii=False)
    return ac, cr


def compliance_lines(cr):
    """One line per compliance problem: where, the text, the rule."""
    return [f"{x['where']}: \"{x['text'] if len(x['text']) <= 140 else x['text'][:137] + '...'}\" ({x['category']}: "
            f"'{x['term']}': {x['why']})" for x in cr.get("problems") or []]


COMPLIANCE_FIX = ("Reword it (only true claims; never health/medical, drugs, politics, religion, blood or violence): a "
                  "hook/close/headline you wrote -> --lines and re-run plan; a product file's line -> edit the product "
                  "file and re-run plan; an overlay of one version -> its <name>.json, a line of the ad copy -> "
                  "ad_copy.csv (or ad_copy.py --seed N), then python3 pipeline/make_batch.py check --out $OUT. render refuses "
                  "this $OUT until the check passes")


def copy_summary(ac, cr):
    """The ad copy / compliance part of plan's (and projects.py expand's) printed summary."""
    return dict(ad_copy=dict(csv=ac.get("csv"), rows=ac.get("rows"), cta=ac.get("cta"), notes=ac.get("notes") or [],
                             problems=ac.get("problems") or []),
                compliance=dict(ok=cr.get("ok"), checked=cr.get("checked"), problems=compliance_lines(cr),
                                allowed=len(cr.get("allowed") or []), report=cr.get("report"),
                                **({"raw_claim_cuts": len(cr["raw_cuts"])} if cr.get("raw_cuts") else {}),
                                **({"raw_story_for_a_human": len([x for x in cr["raw_story"] if x.get("category") == "health"])}
                                   if cr.get("raw_story") else {}),
                                **({"error": cr["error"]} if cr.get("error") else {})))


def use_products_dir(p):
    """A plan's product file outside the default folder (--products-dir): ad_copy / compliance must find it there too."""
    src = p.get("product_source") or ""
    if os.path.isfile(src) and not os.environ.get("LC_PRODUCTS_DIR"):
        os.environ["LC_PRODUCTS_DIR"] = os.path.dirname(os.path.abspath(src))
    if p.get("pipeline") == "new-product" and p.get("product_key"):    # (its file, even when a built-in has its key)
        os.environ["LC_PRODUCT_FILE"] = p["product_key"]


def compliance_gate(out, p):
    """render refuses a batch whose texts break a rule: compliance.py on the files as they are now (a line fixed by hand
    after plan is checked again), so nothing that breaks Julian's rules is voiced into a video or reaches Drive."""
    use_products_dir(p)
    try:
        cr = check_out(out)
    except Exception as e:  # noqa: BLE001
        print(f"WARNING compliance check could not run ({type(e).__name__}: {e}): rendering anyway; run python3 "
              f"pipeline/compliance.py --out {out} and mention it in the reply", file=sys.stderr)
        return
    cr["report"] = os.path.join(out, "compliance.json")
    json.dump(cr, open(cr["report"], "w"), indent=1, ensure_ascii=False)
    if not cr["ok"]:
        sys.exit(f"compliance: {len(cr['problems'])} problem(s) in this batch's text, nothing rendered:\n  - " +
                 "\n  - ".join(compliance_lines(cr)) + f"\n{COMPLIANCE_FIX}.")


def check_cmd(a):
    """python3 pipeline/make_batch.py check --out $OUT: the compliance check plan and render run (compliance.check_out, the count
    a ugc hook says allowed), on the files as they are now: run it after fixing a line by hand. Exit 2 on a problem."""
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    use_products_dir(p)
    cr = check_out(out)
    cr["report"] = os.path.join(out, "compliance.json")
    json.dump(cr, open(cr["report"], "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(ok=cr["ok"], checked=cr["checked"], allowed=len(cr.get("allowed") or []), report=cr["report"],
                          problems=compliance_lines(cr)), indent=1, ensure_ascii=False))
    if not cr["ok"]:
        sys.exit(f"compliance: {len(cr['problems'])} problem(s): {COMPLIANCE_FIX}.")


# ---------------------------------------------------------------- render
SW_BOX = (60, 400, 1020, 1120)   # a colour swatch's packshot: under the tag (y ~300), above the caption band (~1200-1340)


def swatches(out, colour_imgs):
    """One 1080x1920 still per colour (out/sw/<colour>.jpg, the colours block's B-roll). A swatch is made again when its
    photo or SW_BOX changed (its .key), so an --out re-rendered after a change never keeps an old one."""
    from PIL import Image
    import brand_statics as bs
    os.makedirs(os.path.join(out, "sw"), exist_ok=True)
    for n, f in colour_imgs.items():
        fr = os.path.join(out, "sw", f"{re.sub(r'[^a-z0-9]+', '_', n.lower())}.jpg")
        key = json.dumps([os.path.abspath(f), os.path.getsize(f) if os.path.exists(f) else 0, SW_BOX])
        try:
            same = open(fr + ".key").read() == key and os.path.exists(fr)
        except OSError:
            same = False
        if not same:
            c = Image.new("RGB", (1080, 1920), (246, 241, 234))
            im = Image.open(f).convert("RGB")
            im._card = bs.textured(f)              # light textured backdrop: framed card, not a grey box
            bs.place_packshot(c, im, SW_BOX)
            c.save(fr, quality=95)
            open(fr + ".key", "w").write(key)


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
            if s.get("mode") == "ugc":        # (a long phrase is split onto its block's spare shots, then the board's)
                srcs += [x[0] for blk in s["blocks"] for x in blk.get("spare", [])] + [x[0] for x in s.get("spare_broll") or []]
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


SHORTENED = 0.8       # a storyboard that renders under 80% of the plan's estimate was edited shorter after plan (voice noise is ~5%)
SHORTENED_UGC = 0.7   # ugc: the estimate rests on a words-per-second guess for the voice (the take is sped up, its pauses cut): 70%


def shortened(eng, seconds, est, fmt=None):
    return eng == "storyboard" and bool(est) and seconds < (SHORTENED_UGC if fmt == "ugc" else SHORTENED) * est


def split_word(w):
    """A transcript word {w, s, e} as the transcriber counts it: 'anti-theft' is two words (the span split in half)."""
    parts = [x for x in re.split(r"(?<=\w)-(?=\w)", w["w"]) if x]
    if len(parts) < 2:
        return [w]
    step = (w["e"] - w["s"]) / len(parts)
    return [dict(w, w=x, s=round(w["s"] + i * step, 3), e=round(w["s"] + (i + 1) * step, 3)) for i, x in enumerate(parts)]


def scorecard_line(out, v, f):
    """(summary line, [soft problem]) of a rendered ugc video from scorecard.qa_line: the owner's measured targets (words per
    minute, speech share, longest pause, first word, shot length, loudness and its range, repeated shots, held cards). The
    words are the ones storyboard put under the captions (_<name>_longform.json 'transcript': the script on the voice's timings),
    so nothing is transcribed again. A miss is a flag in the QA problems (never a hard failure: the video is uploaded and
    listed); the length is judged by the QA band already, so its target is left out."""
    ws = cuts = None
    try:
        lf = json.load(open(os.path.join(out, f"_{v['name']}_longform.json")))
        ws = [x for w in lf.get("transcript") or [] for x in split_word(w)] or None     # (whisper counts 'anti-theft' as 2 words)
        t, cuts = 0.0, []
        for s_ in lf.get("segments") or []:               # the render's own cuts: no frame detection to miss or invent one
            t += float(s_["dur"])
            cuts.append(t)
        cuts = cuts[:-1] or None
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        import scorecard
        bad, line = scorecard.qa_line(f, words=ws, cuts=cuts)
    except Exception as e:  # noqa: BLE001 - a soft check: a missing module or an odd file must not fail a render
        return f"scorecard unavailable: {str(e)[:100]}", []
    bad = [x for x in bad if not x.startswith("length ")]
    return line, ([f"scorecard: {'; '.join(bad)}"] if bad else [])


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
    lo, hi = QA_SECONDS.get(v.get("format"), QA_SECONDS.get(eng, QA_SECONDS["storyboard"]))
    floor = FLOOR.get(eng, MIN_SECONDS)
    if ok and L < floor:
        problems.append(f"too short: {L:.1f}s (never under {floor}s; want {lo}-{hi}s)")
    elif ok and not lo <= L <= hi and not (v.get("thin_script") and L < lo):     # (a thin script: plan warned, it runs as it is)
        problems.append(f"length {L:.1f}s (want {lo}-{hi}s)")
    if ok and shortened(eng, L, v.get("est_seconds"), v.get("format")) and not any(x.startswith("too short") for x in problems):
        problems.append(f"too short: {L:.1f}s, plan said ~{v['est_seconds']:.0f}s (the spec was cut down after plan: never shorten or "
                        f"rebuild a video to fit a request, 'hook-first' means other hooks; plan again)")
    miss = r.stderr.count("anchor not found")
    if miss:
        problems.append(f"{miss} overlay anchor(s) not found (see qa/{v['id']}.log)")
    hid = r.stderr.count("caption hidden")
    if hid:                      # longform found no room for a caption next to the overlays: that phrase has no caption
        problems.append(f"{hid} caption(s) hidden behind overlays (see qa/{v['id']}.log)")
    cad = [x.split("cadence:", 1)[1].strip() for x in r.stderr.splitlines() if x.startswith("cadence:")]
    if cad:                      # a piece of someone's speech that starts or ends mid-sentence (remix / storyboard clips)
        problems.append(f"cadence: {'; '.join(cad[:3])}{f' (+{len(cad) - 3} more)' if len(cad) > 3 else ''}")
    mus = next((x.split("music:", 1)[1].strip() for x in r.stderr.splitlines() if x.startswith("music:")), None)
    card = None
    if ok and v.get("format") == "ugc":    # the owner's targets (scorecard.py): soft flags, one summary line; the words come
        card, bad = scorecard_line(out, v, f)  # from the render itself (no transcribing again)
        problems += bad
    return dict(name=v["name"], id=v["id"], engine=eng, format=v.get("format"), seconds=round(L, 1), ok=ok and not problems,
                problems=problems, hard=[x for x in problems if x.startswith(HARD)], **({"music": mus} if mus else {}),
                **({"scorecard": card} if card else {}))


def static_qa(out, names, failed=None):
    """Every static PNG exists and shows no face (new_product.count_faces, the DNN check): a hit is a hard failure.
    failed: {name: reason} from brand_statics' 'FAILED <name>: <reason>' lines (text that would overlap: not drawn)."""
    import new_product
    rep, failed = [], failed or {}
    for k, n in enumerate(names):
        f = os.path.join(out, "statics", n + ".png")
        faces = new_product.count_faces(f) if os.path.exists(f) else None
        problems = ([f"render failed: {failed[n]} (no PNG)"] if n in failed and not os.path.exists(f) else
                    ["file missing (render failed)"] if not os.path.exists(f) else
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


BODY_DIFF = "body differs from"   # a version whose body is not its project's (H1's): flagged, still uploaded


def body_flags(out, p, sheets, rows):
    """projects.sheet's body match into the QA rows: a version at 10 or more (a different body) gets the non-hard
    problem 'body differs from H1 (body match M)', so report.json, upload's flagged list and the run report say it;
    a version that matches again loses it."""
    projs = {x["id"]: x for x in p.get("projects") or []}
    for sh in sheets:
        hs = (projs.get(sh.get("project")) or {}).get("hooks") or []
        made = [h["hook"] for h in hs if os.path.exists(os.path.join(out, "videos", h["name"] + ".mp4"))]
        ref = "H1" if "H1" in made else (made or ["H1"])[0]          # (as projects.sheet: H1, else the first rendered)
        for h in hs:
            r = rows.get(h["name"])
            if not r:
                continue
            r["problems"] = [x for x in r.get("problems") or [] if not x.startswith(BODY_DIFF)]
            m = (sh.get("body_match") or {}).get(h["hook"])
            if m is not None and m >= 10:
                r["problems"].append(f"{BODY_DIFF} {ref} (body match {m}; under 10 = the same body): look at "
                                     f"qa/{sh['project']}.jpg")
            r["ok"] = not r["problems"]


def render(a):
    out = os.path.abspath(a.out)
    p = load_plan(out)
    if os.path.exists(os.path.join(out, "ai_needed.json")):     # AI scenes: what failed its gate (or was never made) goes back to
        rep_ = ai_gen.apply(out)                                 # the real photo / footage it replaced (ai_gen.py)
        print("AI scenes: " + json.dumps({k: v for k, v in (rep_ or {}).items() if v not in ([], 0, False)}), file=sys.stderr, flush=True)
        if rep_ and rep_["changed"]:
            p = load_plan(out)
            if rep_["statics_back"]:        # a static's name / words changed: its ad copy and the compliance check again
                copy_and_check(out, seed=p.get("seed") or 1)
    compliance_gate(out, p)
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
        r_ = subprocess.run([sys.executable, os.path.join(HERE, "brand_statics.py"), os.path.join(out, "statics.json"),
                             "--outdir", os.path.join(out, "statics")], capture_output=True, text=True)
        print(r_.stdout + r_.stderr, end="", file=sys.stderr, flush=True)
        if r_.returncode:            # a crash of the whole run (a broken static only prints FAILED and the batch goes on)
            sys.exit(f"brand_statics.py failed (exit {r_.returncode}): see above")
        failed = dict(m.groups() for m in re.finditer(r"^FAILED (\S+): (.+)$", r_.stderr, re.M))
        report.update({r["name"]: r for r in static_qa(out, p["statics"], failed)})
    if vids:
        prefetch(out, vids)
    with cf.ThreadPoolExecutor(max(1, a.jobs)) as ex:
        for r in ex.map(lambda v: render_one(out, v), vids):
            report[r["name"]] = r
            print(json.dumps(r), flush=True)
            if r.get("scorecard"):
                print(f"scorecard {r['id']}: {r['scorecard']}", flush=True)
    if os.path.isdir(os.path.join(out, "_tmp")) and not os.listdir(os.path.join(out, "_tmp")):
        os.rmdir(os.path.join(out, "_tmp"))
    order = p["statics"] + [v["name"] for v in p["videos"]]
    merged = {**old, **report}
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
        except Exception as e:  # noqa: BLE001 - the renders are done; say so and carry on
            print(f"project QA sheets failed ({type(e).__name__}: {e}): look at the per-version contact sheets", file=sys.stderr)
    body_flags(out, p, sheets, merged)
    json.dump(sorted(merged.values(), key=lambda r: order.index(r["name"]) if r["name"] in order else 999),
              open(rp, "w"), indent=1)
    print("QA: look at", os.path.join(out, "qa"), "(statics.jpg + one contact sheet per video" +
          (f" + one sheet per project, {', '.join(os.path.basename(s['sheet']) for s in sheets)}: its hook versions side by "
           f"side, the body once, body match under 10 = the same body" if sheets else "") + ") before uploading")


# ---------------------------------------------------------------- upload
def run_report(p, report, uploaded, skipped, name, flagged=(), notes=(), pending=(), copy=None):
    pipe, ik, fl = p.get("pipeline") or "catalog", p.get("intake") or {}, p.get("fill") or {}
    rd = ik.get("read") or {}
    what = {"winners": "winners (new versions of the weekly brief's winning videos" + (
        f"; {fl['winner_projects']} winner projects + {fl['new_angle_projects']} new-angle projects to fill the batch"
        if fl else "") + ")",
        "new-product": f"new product (everything from Drive New Products / {ik.get('folder') or p['product']}: "
                       f"{rd.get('photos', '?')} photos, {len(rd.get('clips') or [])} clip(s), the notes; "
                       f"{ik['site'] if str(ik.get('site')).startswith('libracases') else 'libracases.com not read'})"}
    L = [f"Libra Cases ads: {name}", f"Request: {p.get('request') or '-'}",
         f"Pipeline: {what.get(pipe, 'catalog (the products and counts asked)')}" +
         (" · a full batch (no counts in the request)" if p.get("batch") else ""),
         f"Product: {p['product']} · Theme: {p.get('theme_name') or p['theme']} · Offer: {p.get('offer') or '-'} · "
         f"voiceover lines: {p.get('tts_lines')} (~{p.get('est_credits')} credits)"]
    if ik:
        o = ik.get("offer") or {}
        L.append(f"Product file: {ik.get('product_file')} ({ik.get('intake')}; {ik.get('made_by')}) · offer from "
                 f"{o.get('price_source') or 'the notes'}: {o.get('text')}" + (f" (${o['price']} instead of ${o['compare_at']})"
                                                                                 if o.get("price") and o.get("compare_at") else ""))
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
                (f", {nrev} narrated reviews" if nrev else ", its proven body intact") if x["engine"] == "remix" else
                f"new ugc video, {x['angle']} angle (one voice, numbered chapters, the offer last)" if x.get("format") == "ugc" else
                f"new storyboard video, {x.get('format') or x['angle']} angle") +
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
                     f", {hook}, " + (f"{len(w['reviews'])} narrated reviews" if w.get("reviews") else "its proven body intact"))
        else:
            L.append(f"  {dn}  video {secs}, {v.get('format', '?')}, hook: \"{v.get('hook', '')}\"")
    cards = [(vs[n]["id"] if n in vs else n, report[n]["scorecard"]) for n, _ in vu if (report.get(n) or {}).get("scorecard")]
    if cards:     # the owner's measured targets of the ugc format (scorecard.py): a miss is a soft flag, listed with the QA flags
        L.append("Scorecard (ugc videos; targets from the owner's reference ads: 185-215 wpm, speech 85%+, no pause over 0.8 s, a "
                 "shot every 1.4-2.6 s, -14 LUFS with a range under 4 LU, no repeated shot, no card held over 3.2 s):")
        L += [f"  {i}  {c}" for i, c in cards]
    beds = list(dict.fromkeys(report[n]["music"].split(" (")[0] for n, _ in vu if (report.get(n) or {}).get("music")))
    if vu:        # Julian: a video without a music bed feels off (storyboard videos get one; winners keep the RAW's sound)
        gen = any(b.startswith("generated") for b in beds)
        L.append("Music: " + ("; ".join(beds) + (" (made by music.py: no licensed track in pipeline/assets/music; put the "
                                                 "client's tracks there for a real one)" if gen else "") if beds else
                              "none (winner remixes keep the RAW's own sound: its own music bed)") + (
                     "; winner remixes keep the RAW's own sound (a RAW recorded dry gets a bed)" if beds and any(
                         vs.get(n, {}).get("engine") == "remix" for n, _ in vu) else ""))
    if copy:      # the Meta ad copy (ad_copy.py) of the ads in this folder
        L.append("\nAd copy (Meta: 2 primary texts, 2 headlines, description, CTA per ad; a project's versions share it): "
                 + (f"{copy['file']} ({copy['rows']} ads, CTA {copy.get('cta') or '-'})" + (f" {copy['link']}" if copy.get("link") else "")
                    if copy.get("file") else "not uploaded"))
        L += [f"  - {x}" for x in copy.get("notes") or []]
        cr = copy.get("compliance") or {}
        if cr:
            L.append("  Compliance (Julian's rules: no health/medical claims, drugs, politics, religion, blood or violence; "
                     "only true claims; the RAW audio each winner version plays included): " + ("ok" if cr.get("ok") else f"{len(cr.get('problems') or [])} problem(s)") +
                     f", {cr.get('checked', 0)} texts checked" + (f"; {len(cr['allowed'])} customer-review / RAW-story words "
                                                                 f"allowed as approved material" if cr.get("allowed") else ""))
            L += [f"    ! {x}" for x in compliance_lines(cr)]
            al = {}
            for x in cr.get("allowed") or []:      # approved material a human may want to glance at
                al.setdefault((x["term"].lower(), x["why"]), []).append(x["where"])
            L += [f"    allowed: '{t}' ({why}): {len(ws)}x, e.g. {ws[0][:90]}" for (t, why), ws in list(al.items())[:8]]
            for x in cr.get("raw_cuts") or []:     # Julian's health rule inside the client's RAW audio
                L.append(f"    cut from the proven body (health claim): {x['key']} RAW {x['range'][0]:.1f}-{x['range'][1]:.1f} s "
                         f"\"{x.get('said') or ''}\" ({x['where'][:60]}): a human should listen to that line once")
            med = [x for x in cr.get("raw_story") or [] if x.get("category") == "health"]
            L += [f"    needs a human (Julian's health rule, the client's approved RAW story): {x['where'][:70]}: "
                  f"\"{x['text'][:120]}\"" for x in med[:6]]
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


OUT_FOLDERS = {"winners": ("outputs_winners_folder", "Winners"),            # pipeline -> (optional config.json drive key,
               "new-product": ("outputs_new_products_folder", "New Products")}  # else this folder in Outputs)


def record_batch(p, name, link, uploaded, vproj):
    """A new product's batch in its product file's "tests" (new_product.record_test): date, name, Drive link, counts.
    Another upload into the same folder (statics first, videos later) updates that entry. Returns the file or None."""
    import new_product
    f = (p.get("intake") or {}).get("product_file") or p.get("product_source") or ""
    f = f if os.path.isabs(f) else os.path.join(ROOT, f)
    if not f.endswith(".json") or not os.path.exists(f):
        print(f"WARNING the product file {f!r} is gone: this batch is not recorded in its \"tests\"", file=sys.stderr)
        return None
    info = dict(date=p.get("created") or datetime.date.today().isoformat(), name=name, drive_link=link,
                statics=sum(k == "static" for _, k, _ in uploaded), videos=sum(k == "video" for _, k, _ in uploaded),
                projects=len({vproj[n]["id"] for n, k, _ in uploaded if k == "video" and vproj.get(n)}),
                plan=p.get("prefix"), request=p.get("request") or "")
    d = json.load(open(f))
    old = next((t for t in d.get("tests") or [] if t.get("drive_link") == link), None)
    if not old:
        return new_product.record_test(f, info)
    old.update({k: max(old.get(k) or 0, info[k]) if k in ("statics", "videos", "projects") else info[k] for k in info})
    open(f, "w").write(new_product.dumps(d) + "\n")
    return f


def log_novelty(out, p, name, uploaded):
    """What this upload shows, into the product's novelty log (novelty.py: the next batch avoids it): each static's layout /
    photo / scene / colour / caption, the AI clips' scenes, each ugc video's script / angle / hook. Returns the log file."""
    try:
        ads = {x["name"]: x for x in (json.load(open(os.path.join(out, "statics.json"))).get("ads") or [])}
    except (OSError, ValueError):
        ads = {}
    got = {n for n, _, _ in uploaded}
    st = []
    for n in p.get("statics") or []:
        x = ads.get(n)
        if x and n in got:
            e = dict(layout=x.get("layout"), photo=None if x.get("ai") else os.path.basename(str(x.get("photo") or "")) or None,
                     caption=x.get("caption") or x.get("headline"), **{k: (x.get("ai") or {}).get(k) for k in ("scene", "colour")})
            st.append({k: v for k, v in e.items() if v})
    spec_txt = "".join(open(os.path.join(out, f"{v['name']}.json")).read() for v in p.get("videos") or []
                       if v["name"] in got and os.path.exists(os.path.join(out, f"{v['name']}.json")))
    need = ai_gen.load_needed(out) or {}
    cl = [dict(scene=c["scene"]) for c in need.get("clips") or [] if f"{c['id']}_c.mp4" in spec_txt and ai_gen.available(out, "clips", c["id"])]
    vids, seen = [], set()
    try:
        said_ = {f: t.split("|", 1)[-1] for f, t in json.load(open(os.path.join(out, "tts_said.json"))).items()}
    except (OSError, ValueError):
        said_ = {}
    for v in p.get("videos") or []:
        u = v.get("ugc") or {}
        hk_ = v.get("hook_text") or v.get("hook")
        if v["name"] in got and u.get("script") and (u["script"], hk_) not in seen:
            seen.add((u["script"], hk_))
            try:          # the project's chapter takes (every version shares them): what its body said
                sp_ = json.load(open(os.path.join(out, f"{v['name']}.json")))
                ch_ = [said_[b_["vo"]] for b_ in (sp_.get("blocks") or [])[1:] if b_.get("vo") in said_]
            except (OSError, ValueError, KeyError):
                ch_ = []
            first_ = u["script"] not in {z.get("script") for z in vids}      # (a project's versions share their chapters: once)
            vids.append({k: x for k, x in dict(script=u.get("script"), angle=u.get("angle"), hook=hk_,
                                               hook_type=(u.get("hook") or {}).get("type"),
                                               chapters=ch_ if first_ else None).items() if x})
    novelty.record(p.get("product") or "product", dict(date=p.get("created") or datetime.date.today().isoformat(), name=name,
                                                       statics=st, clips=cl, videos=vids))
    return novelty.PATH


def upload(a):
    """Uploads the files plan.json lists (never leftovers in the folder). Hard QA failures (render failed, file
    missing, a face in a static, a video under its floor: 25 s storyboard, 15 s winner) stay out; length / anchor /
    cadence flags are uploaded and listed. A same-named file already in Drive is skipped when identical; a newer local
    render with other content is uploaded under a suffix, loudly. Project mode: each project's versions go in their own
    folder Videos/<P01 – angle>. The ad copy (ad_copy.csv, rows of the ads in Drive) goes in the dated folder as
    <prefix>_ad_copy.csv, next to the run report."""
    out = os.path.abspath(a.out)
    p = load_plan(out)
    use_products_dir(p)               # (the ad copy's compliance check below reads the product file)
    rp = os.path.join(out, "qa", "report.json")
    report = {r["name"]: r for r in json.load(open(rp))} if os.path.exists(rp) else {}
    up = [sys.executable, os.path.join(HERE, "drive_upload.py")]
    cfg = json.load(open(os.path.join(HERE, "config.json")))
    now = datetime.datetime.now()     # (the batch's date is the plan's: statics and videos uploaded after midnight share it)
    name = f"{p.get('created') or now.date().isoformat()} – {a.name or p.get('request') or p['product']}"
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
    pipe = p.get("pipeline") or "catalog"
    parent, where = cfg["drive"]["outputs_folder"], "Outputs"
    if pipe in OUT_FOLDERS:           # winners / new products: their own folder in Outputs (found or made once)
        key_, sub_ = OUT_FOLDERS[pipe]
        parent = cfg["drive"].get(key_) or run("mkdir", sub_, "--parent", parent).splitlines()[-1]
        where = f"Outputs/{sub_}"
    folder = run("mkdir", name, "--parent", parent).splitlines()[-1]
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
    # ---------- the Meta ad copy of every ad in Drive now: this upload's + (--only) the plan's other ads that an earlier
    # upload sent (rendered, no hard QA failure); never a row for an ad that is not there
    copy, cp = None, os.path.join(out, "ad_copy.csv")
    if os.path.exists(cp):
        import csv
        in_run = {os.path.splitext(os.path.basename(f))[0] for f, _, _ in want}

        def sent_before(n, kind):     # an ad of an earlier upload (--only): its file is in its Drive folder (read only)
            x = vproj.get(n) if kind == "video" else None
            d = sub.get(x["id"]) or (in_drive(dest["video"]).get(project_folder(x)) or {}).get("id") if x else dest[kind]
            return bool(d) and any(f.startswith(n) for f in in_drive(d))
        sent = {n for n, _, _ in uploaded} | {n for n, kind in [(n, "static") for n in p["statics"]] +
                                              [(v["name"], "video") for v in p["videos"]]
                                              if a.only and n not in in_run and sent_before(n, kind)}
        with open(cp, encoding="utf-8-sig") as fh:
            rd = csv.DictReader(fh)
            cols, rows = rd.fieldnames, [r for r in rd if r.get("ad_name") in sent]
        try:
            acj = json.load(open(os.path.join(out, "ad_copy.json")))
        except (OSError, ValueError):
            acj = {}
        try:
            cr = check_out(out)                     # the copy as it is now (it may have been refined by hand)
        except Exception as e:  # noqa: BLE001
            cr = dict(ok=True, problems=[], allowed=[], checked=0, error=str(e))
        bad = [x for x in cr["problems"] if x["where"].startswith("ad copy ")]
        copy = dict(file=None, rows=len(rows), cta=acj.get("cta"), notes=list(acj.get("notes") or []), compliance=cr)
        if bad:
            notes.append(f"ad copy NOT uploaded: {len(bad)} line(s) break a rule (fix ad_copy.csv or re-run "
                         f"python3 pipeline/ad_copy.py --out $OUT --seed 2, then upload again)")
        elif rows:
            os.makedirs(os.path.join(out, "_upload"), exist_ok=True)
            base = f"{p['prefix']}_ad_copy.csv"
            local = os.path.join(out, "_upload", base)
            with open(local, "w", newline="", encoding="utf-8-sig") as fh:       # BOM: Excel reads the emoji right
                wr = csv.DictWriter(fh, fieldnames=cols)
                wr.writeheader()
                wr.writerows(rows)
            h = md5(local)
            same = next((x for x in in_drive(folder).values() if x["name"].startswith(f"{p['prefix']}_ad_copy")
                         and x.get("md5Checksum") == h), None)
            if same:
                copy.update(file=same["name"], link=same.get("webViewLink"))
            else:
                if base in in_drive(folder):     # an earlier upload's copy (e.g. statics first): this one covers more ads
                    base = next(b for b in (f"{p['prefix']}_ad_copy_upd{now:%H%M}.csv", f"{p['prefix']}_ad_copy_upd{now:%H%M%S}.csv")
                                + tuple(f"{p['prefix']}_ad_copy_upd{now:%H%M%S}_{k}.csv" for k in range(2, 99))
                                if b not in in_drive(folder))
                    notes.append(f"ad copy: {base} covers all {len(rows)} ads in this folder now (the earlier "
                                 f"{p['prefix']}_ad_copy.csv only the ads of an earlier upload)")
                res = json.loads(run("upload", local, "--folder", folder, "--name", base).splitlines()[-1])
                copy.update(file=base, link=res.get("link") or (f"https://drive.google.com/file/d/{res['id']}/view"
                                                                if res.get("id") else None))
    elif uploaded:
        notes.append("no ad copy for this batch (ad_copy.csv is missing: python3 pipeline/ad_copy.py --out $OUT, then "
                     "upload again)")
    txt = os.path.join(out, f"run report {now:%H%M}.txt")
    if a.only:
        notes.insert(0, f"this upload covers only {a.only.upper()} of the batch (other ads: earlier/later run reports here)")
    if pending:
        print(f"not rendered yet, so not uploaded now: {', '.join(pending)}", file=sys.stderr)
    link = f"https://drive.google.com/drive/folders/{folder}"
    try:          # the ads are in Drive already: a product file that can't be updated must not lose the run report
        tested = record_batch(p, name, link, uploaded, vproj) if pipe == "new-product" and uploaded else None
    except (OSError, ValueError, KeyError, TypeError) as e:
        tested = None
        notes.append(f"product file NOT updated with this batch ({type(e).__name__}: {e}): add it to its \"tests\" by hand "
                     f"(python3 pipeline/new_product.py list shows it as untested until then)")
        print(f"WARNING product file not updated: {e}", file=sys.stderr)
    if tested:
        notes.append(f"the product file records this batch (\"tests\"): {tested}")
    try:          # the novelty log (novelty.py) and the AI scenes this batch shipped
        nlog = log_novelty(out, p, name, uploaded) if uploaded else None
        ai_s = ai_gen.summary(out) if os.path.exists(os.path.join(out, "ai_needed.json")) else None
        if ai_s:
            fell = len([x for x in (ai_gen.load_gate(out).get("stills") or {}).values() if not x.get("ok")]) + \
                len([x for x in (ai_gen.load_gate(out).get("clips") or {}).values() if not x.get("ok")])
            notes.append(f"AI scenes (the real bag in new scenes, ai_gen.py): {len(ai_s['stills_ok'])} stills and {len(ai_s['clips_ok'])} "
                         f"clips passed the quality gate and are in this batch; {fell} failed it or were never made and were replaced by "
                         f"real photos / footage; planned cost ~{ai_s['est_credits']} credits")
        if nlog:
            notes.append(f"the novelty log records this batch (the next one avoids its scenes, photos, captions and hooks): {nlog}")
    except Exception as e:  # noqa: BLE001 - the ads are in Drive: a log that can't be written must not stop the run report
        print(f"WARNING novelty log not updated: {type(e).__name__}: {e}", file=sys.stderr)
    open(txt, "w").write(run_report(p, report, uploaded, skipped, name, flagged, notes, pending, copy))
    run("upload", txt, "--folder", folder)          # a fresh report every upload, never skipped
    if tested:
        print(f"product file changed: {tested} (\"tests\" += this batch): commit it with the specs", file=sys.stderr)
    print(json.dumps(dict(folder=link, name=name, pipeline=pipe, drive_path=f"{where}/{name}", files=len(uploaded),
                          **({"product_file_updated": tested} if tested else {}),
                          **({"project_folders": {f"Videos/{project_folder(projs[k])}": f"https://drive.google.com/drive/folders/{d}"
                                                  for k, d in sub.items()}} if projs else {}),
                          uploaded=[d for _, _, d in uploaded], already_there=existed, renamed=renamed,
                          ad_copy=dict(file=copy.get("file"), link=copy.get("link"), rows=copy.get("rows"),
                                       compliance_ok=(copy.get("compliance") or {}).get("ok")) if copy else None,
                          flagged=flagged, skipped=skipped, not_rendered_yet=pending,
                          not_in_plan=[os.path.relpath(f, out) for f in stray], report=txt),
                     indent=1, ensure_ascii=False))


def specs_copy(a):
    """plan.json, statics.json, tts_needed.json, one spec per video, ad_copy.json and compliance.json: what a batch is
    made of. Never the render files
    (_*_longform.json, *_words.json transcripts, audio, media)."""
    out = os.path.abspath(a.out)
    p = json.load(open(os.path.join(out, "plan.json")))
    os.makedirs(a.to, exist_ok=True)
    fs = ["plan.json", "statics.json", "tts_needed.json"] + [v["name"] + ".json" for v in p["videos"]] + \
        [f for f in ("ad_copy.json", "compliance.json", "ai_needed.json") if os.path.exists(os.path.join(out, f))]   # the copy + its check + the AI plan
    for f in fs:
        shutil.copy(os.path.join(out, f), os.path.join(a.to, f))
    print(json.dumps(dict(to=os.path.abspath(a.to), files=fs), indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--pipeline", choices=PIPELINES, help="catalog (default: the counts and product given, as always; "
                    "--new-product alone means new-product) | winners (the brief's winner projects + statics of their "
                    "product; fill) | new-product (a Drive New Products folder, --new-product)")
    pl.add_argument("--statics", type=int)
    pl.add_argument("--videos", type=int, help="storyboard (new-angle) videos: each one is a project of --hooks versions")
    pl.add_argument("--winner-videos", type=int, help="winner remixes (remix.py), numbered first: each one is a "
                    "project of --hooks versions (another cold open each); one project per winner unless its RAW has "
                    "--hooks more cold opens")
    pl.add_argument("--projects", type=int, help="video projects of the pipeline's kind: winner projects in winners, "
                    "storyboard projects otherwise (= --winner-videos / --videos)")
    pl.add_argument("--batch", action="store_true", help=f"a batch: {BATCH['statics']} statics + {BATCH['projects']} "
                    "projects (the counts not given; winners / new-product with no count do this by themselves)")
    pl.add_argument("--no-fill", action="store_true", help="winners: only winner projects, even when fewer are possible "
                    "than asked (default: new-angle storyboard projects of the winners' product fill the rest)")
    pl.add_argument("--new-product", help="new-product: the Drive New Products folder (name or a unique part of it) | "
                    "next (the newest folder with no ads yet; default) | latest")
    pl.add_argument("--refresh-product", action="store_true", help="new-product: redo the intake from the folder even "
                    "when it is unchanged (a hand-edited product file is overwritten)")
    pl.add_argument("--winner-reviews", action="store_true", help="winner remixes get a narrated review section (another "
                    "voice over B-roll before the offer, as in the first batch). Default: off, the proven RAW body plays intact "
                    "(only its editorial cuts) and winner projects need no voiceover")
    pl.add_argument("--hooks", type=int, default=4, help="hook versions per video (default 4, the client's H1-H4: one body, "
                    "another opening line + shot + label per version; ids P01H1 ..); 1 = single videos V01 .. as before")
    pl.add_argument("--hook-seed", type=int, help="variation of the hook versions only (default: --seed); the same --seed "
                    "with another --hook-seed keeps every body and changes the H2-H4 hooks")
    pl.add_argument("--winners", default="latest", help="latest (newest brief) | all | brief.json | '94-H4,148-H5' | '94,148'")
    pl.add_argument("--product", help="built-in bag or a pipeline/data/products file (default: top winner's, else Hobo Bag; "
                    "new-product: the folder when --new-product is not given)")
    pl.add_argument("--products-dir", help="product files folder (default pipeline/data/products, or $LC_PRODUCTS_DIR)")
    pl.add_argument("--allow-draft", action="store_true", help="build from a product file still marked draft")
    pl.add_argument("--theme", default="")
    pl.add_argument("--request", default="", help="the user's message, for the folder name and report")
    pl.add_argument("--lines", help="json with overrides: hero, bold, colours, V01_hook, V01_close ... (P01_hook = V01_hook: "
                    "project P01's H1 line)")
    pl.add_argument("--seed", type=int, help="variation (default 1; new-product without --only: 1 + the batches its "
                    "product file records, so a new batch differs): another seed gives other winner reviews (with "
                    "--winner-reviews; a winner project holds every cold open its RAW has: only H1 changes; --hooks 1: other "
                    "cold opens), other storyboard hooks, feature order, reviews and B-roll, other static photos/headlines, "
                    "and other hook versions (unless --hook-seed)")
    pl.add_argument("--only", help="keep only these ads (P02 = project 2's versions, P02H3 = one version, S03, 'P02H3,S01', "
                    "V/P = all videos, S = all statics; V02 = P02; --hooks 1: V02): a redo voices, renders and uploads just them")
    pl.add_argument("--classic", action="store_true", help="the pre-2026-10-14 output: storyboard videos in the classic formats "
                    "(showcase / features / reviews / colours / lifestyle / offer, 40-60 s: one script per format, a voice take "
                    "per line) and the old static cycle, instead of the ugc format (default: ugc_script.py's scripts in the 'you' "
                    "voice, 55-80 s, numbered chapters, a new shot about every 2 s, one steady loudness) and the statics with the "
                    "native / quotes / value layouts")
    pl.add_argument("--story", action="store_true", help="storyboard videos in the story format: 1.5-2 min (every feature, the "
                    "real customer in full, reviews, colours, the offer); also chosen when --request asks for a story / "
                    "long video")
    pl.add_argument("--no-music", action="store_true", help="no music bed under the storyboard videos (default: a client "
                    "track from pipeline/assets/music, else a generated bed; winner remixes keep the RAW's own sound, a RAW recorded "
                    "dry gets a bed)")
    pl.add_argument("--rev", type=int, default=1, help="revision of an earlier batch with the same product+theme+date: adds _v2, _v3"
                    " (plan also moves to the first _vN not in Drive yet)")
    pl.add_argument("--no-name-check", action="store_true", help="don't look in Drive for today's names (offline tests)")
    pl.add_argument("--budget", type=float, help=f"credits the request allows for voiceover, hook lines included "
                    f"(default {MAX_CREDITS})")
    pl.add_argument("--no-ai", action="store_true", help="no AI scene stills / clips (ai_gen.py): real photos and footage only. "
                    "Default: about 40% of the statics and a few video shots are the real bag placed in new scenes "
                    "(owner 2026-10-20), generated after plan (ai_needed.json) and kept only when they pass the quality gate")
    pl.add_argument("--ai-cap", type=float, help="credits for voiceover + AI together (default 100, config.json budget."
                    "max_credits_per_batch); only when the request names another budget")
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
    ck = sub.add_parser("check", help="the compliance check of a planned batch (plan and render run it too; ugc count words allowed)")
    ck.add_argument("--out", required=True)
    sp = sub.add_parser("specs", help="copy the batch's spec JSONs (no media, no render files) for committing")
    sp.add_argument("--out", required=True)
    sp.add_argument("--to", "--dest", dest="to", required=True, help="e.g. pipeline/recipes/daily/<YYYY-MM-DD>/<short-name>")
    a = ap.parse_args()
    {"plan": plan, "render": render, "upload": upload, "specs": specs_copy, "check": check_cmd}[a.cmd](a)


if __name__ == "__main__":
    main()

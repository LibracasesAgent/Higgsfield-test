#!/usr/bin/env python3
"""Compliance check of every text a customer hears or sees in our ads (and the Meta ad copy): the rules the client's
media buyer set on 2026-10-09 plus CLAUDE.md rule 3 (only true claims).

Never in a creative or in ad copy: health / medical claims (cure, heals, pain relief, arthritis, therapeutic,
doctor-recommended, posture ...), prescription drugs, politics, religion, blood or violence (even a drop of blood),
violent crime (robbed, mugged), profanity. Only true claims: every number must come from the product's facts (site,
product data, docs/PLAYBOOK.md section 1), claims such as 'waterproof', 'handmade', 'lifetime warranty',
'best-selling', '10,000 customers' or a feature of another bag ('RFID' on the Hobo Bag) only when the facts say so, no
fake testimonial in the brand voice ('I bought mine', 'my sister'), and no %, gift or sale the product's real offer does
not back (new_product.unbacked).

What is ours and what is approved material:
- ours (checked in full): every voiceover line we write (tts_needed.json), every text on statics and video overlays,
  the offer / end cards, the ad copy.
- the client's RAW ads (winner remixes): the Susan / workshop / arthritis / 'her sister was robbed' story is approved as
  RAW audio (PLAYBOOK section 1); an on-screen label that repeats the RAW's words (hook_label, REASON 1) may use the
  story's crime words (robbed) and numbers when the RAW transcript says them, never a health word (no label names a
  medical condition: 'HER LAST COLLECTION', not 'THE ARTHRITIS HAS WON'). Ad copy quoting a RAW line still gets no
  health or crime words (new text we write never makes a health claim). The RAW words each version actually plays
  (cold open + body minus its cuts) are scanned too (raw_audit): a health CLAIM ('a strap that prevents shoulder pain')
  or a drugs / politics / religion / blood word is a problem even there (cut it: clip_bank edit.claim_cuts); the story's
  own health / crime words are listed under raw_story for a human, the claim cuts under raw_cuts.
- customer reviews (reviews.json, approved "yes on all"): their numbers and first-person words are allowed verbatim,
  and so is a brand-voice line that names the customer and adds nothing ('Carol calls it the best bag she has ever
  bought.', make_batch.third); a health claim or a gift the product no longer has is still a problem.
- evidence for claims and numbers: the site facts ($OUT/site/<key>_facts.json), the PLAYBOOK section 1 row and offer
  bullet, the product's data (features, product-file facts). Our own hook lines (hooks.json) are checked, never evidence.
  A Drive-only new product (a product file with no libracases.com page) has only its own file (the client's notes and
  the features from them): no store-wide 'free US shipping' unless its notes say it.
Drugs, politics, religion, blood/violence and profanity are problems whatever the source.

  python3 pipeline/compliance.py --out $OUT          after make_batch.py plan (and ad_copy.py): scans every spoken line
      in tts_needed.json, every visible text in statics.json and the video specs, and ad_copy.csv when it is there;
      writes $OUT/compliance.json, prints it, exit 1 on problems
  python3 pipeline/compliance.py --text "..." [--text ...] [--product "Hobo Bag"] [--offer "50% off + free pouch"]
      ad-hoc check of lines (e.g. --lines you are about to pass to plan); exit 1 on problems

Python: check(texts, product=None, offer=None, facts=None, ctx=None) -> list of problems
  (dicts: where, text, category, term, why); texts = a string, a list of strings, or dicts {where, text, source, raw}.
"""
import argparse
import csv
import datetime
import glob
import itertools
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PLAYBOOK = os.path.join(ROOT, "docs", "PLAYBOOK.md")
REVIEWS = os.path.join(HERE, "data", "reviews.json")
TRANS = os.path.join(HERE, "data", "transcripts")


def _words(*alts):
    """One case-insensitive regex for whole words/phrases (a hyphen counts as part of a word: 'anti-theft' is one)."""
    return re.compile(r"(?<![\w-])(?:" + "|".join(alts) + r")(?![\w-])", re.I)


# ---------------------------------------------------------------- word lists
# never in a creative or copy (Julian, 2026-10-09); health also covers the conditions themselves, so a line we write never
# implies the bag helps one (Meta's personal-health rule as well)
HEALTH = _words(
    r"cur(?:e|es|ed|ing)", r"heal(?:s|ed|ing)?", r"pain(?:s|ful|less|-free)?", r"relie(?:f|ve|ves|ved|ving)",
    r"arthriti(?:s|c)", r"rheumat\w*", r"therap(?:y|ies|ist|eutic)", r"doctors?(?:-| )(?:recommend\w*|approved)",
    r"recommended by doctors?", r"physicians?", r"chiropract\w*", r"orthopa?edic", r"clinical(?:ly)?",
    r"medical(?:ly)?", r"medicin(?:e|al)", r"fda", r"posture", r"joints?", r"inflammation", r"injur(?:y|ies|ed)",
    r"carpal tunnel", r"chronic", r"ailments?", r"diseases?", r"illness(?:es)?", r"symptoms?", r"diagnos\w*",
    r"anxiety", r"anxious", r"depress(?:ion|ed)", r"panic attacks?", r"mental health", r"insomnia", r"adhd", r"ptsd",
    r"stress relief", r"detox\w*", r"immun(?:e|ity)", r"weight loss", r"lose weight", r"diabet(?:es|ic)", r"cancer",
    r"covid(?:-19)?", r"virus(?:es)?", r"anti-?bacterial", r"antimicrobial", r"hypoallergenic", r"strain",
    r"health(?:y|ier)?", r"wellness", r"well-?being", r"supplements?", r"vitamins?", r"hospitals?", r"surger(?:y|ies)",
    r"disabilit(?:y|ies)", r"disabled", r"pregnan(?:t|cy)")
DRUGS = _words(
    r"prescriptions?", r"prescribed", r"rx", r"pharmac(?:y|ies|ist|eutical)", r"pills?", r"medications?", r"meds",
    r"drugs?", r"opioids?", r"insulin", r"ozempic", r"wegovy", r"viagra", r"xanax", r"adderall", r"valium",
    r"oxycodone", r"painkillers?", r"antidepressants?", r"cannabis", r"marijuana", r"cbd", r"thc", r"weed", r"vap(?:e|es|ing)",
    r"narcotics?")
POLITICS = _words(
    r"politics", r"political", r"politicians?", r"elections?", r"vot(?:e|es|ed|ing|ers?)", r"ballots?", r"democrats?",
    r"democratic party", r"republicans?", r"gop", r"maga", r"trump", r"biden", r"obama", r"congress",
    r"senat(?:e|or|ors)", r"parliament", r"government", r"president(?!s?'?s? day)", r"liberals?", r"conservatives?", r"left-wing",
    r"right-wing", r"immigra(?:tion|nts?)", r"abortion", r"pro-life", r"pro-choice", r"gun control",
    r"second amendment", r"protests?")
RELIGION = _words(
    r"god", r"gods", r"goddess(?:es)?", r"oh my god", r"omg", r"god bless", r"godsend", r"jesus", r"christ", r"bible",
    r"biblical", r"church(?:es)?", r"pray(?:s|ed|ing|er|ers)?", r"bless(?:ed|ing|ings)?", r"religio(?:n|us)", r"faith",
    r"allah", r"muslims?", r"islam(?:ic)?", r"christians?", r"christianity", r"catholic", r"jewish", r"judaism",
    r"hindu", r"buddh(?:a|ist)", r"mosques?", r"temples?", r"synagogues?", r"holy", r"heaven(?:ly)?", r"amen",
    r"sins?", r"sinful", r"worship", r"scriptures?", r"spiritual")
VIOLENCE = _words(
    r"blood(?:y|ied)?", r"bleed(?:s|ing)?", r"gor(?:e|y)", r"kill(?:s|ed|er|ers|ing)?", r"murder(?:s|ed)?", r"dead",
    r"deadly", r"death", r"di(?:e|es|ed)", r"dying", r"stab(?:s|bed|bing)?", r"shoot(?:s|ing)?", r"guns?", r"gunpoint",
    r"knife", r"knives", r"knifepoint", r"weapons?", r"violen(?:ce|t)", r"assault(?:s|ed)?", r"attack(?:s|ed)?",
    r"wound(?:s|ed)?", r"corpses?", r"massacre", r"war", r"bombs?", r"terror(?:ist|ism)?", r"suicide",
    r"slash(?:es|ed|er)?", r"slash-proof", r"kidnap\w*", r"hostages?")
# violent crime: the client's approved RAW story says it ('designed after her sister was robbed'), so an on-screen label
# that repeats its RAW may too; never in a new line or the ad copy (pickpocket / theft words are fine: anti-theft)
CRIME = _words(r"rob(?:s|bed|bing|bery|beries|ber|bers)", r"mugg(?:ed|ing|er|ers)", r"burglar(?:y|ies|s)?",
               r"break-?ins?", r"carjack\w*")
PROFANITY = _words(
    r"fuck\w*", r"f[*#@]+k\w*", r"shit\w*", r"sh[*#@]+t", r"damn(?:ed|it)?", r"dammit", r"goddamn\w*", r"hell",
    r"bitch\w*", r"bastards?", r"crap(?:py)?", r"ass", r"asses", r"asshole\w*", r"badass", r"arse", r"piss(?:ed)?",
    r"wtf", r"stfu", r"dick", r"cock", r"pussy", r"slut", r"whore", r"bollocks")
CATEGORIES = [("health", HEALTH, "a health / medical word: never in creatives or copy (no health claims)"),
              ("drugs", DRUGS, "drugs / prescription medicine: never in creatives or copy"),
              ("politics", POLITICS, "politics: never in creatives or copy"),
              ("religion", RELIGION, "religion: never in creatives or copy"),
              ("violence", VIOLENCE, "blood / violence: never in creatives or copy (not even a drop of blood)"),
              ("crime", CRIME, "violent crime: not in new lines or copy (only a label repeating the client's RAW story)"),
              ("profanity", PROFANITY, "profanity: never in creatives or copy")]
HARD = {"drugs", "politics", "religion", "violence", "profanity"}     # problems whatever the source
STORY = {"health", "crime"}       # the RAW's approved story (heard as is in its audio, listed for a human)
LABEL_STORY = {"crime"}           # allowed in an on-screen label that repeats the RAW ('HER SISTER WAS ROBBED'); a label
#                                   never names a health condition, not even the RAW's ('THE ARTHRITIS HAS WON': no)

# a returns promise while a final-sale campaign runs (campaign.json final_sale: the Black Friday terms say sale items can't be returned)
FINAL_SALE = re.compile(r"\b(?:(?:free|easy|simple|hassle[- ]free) returns?|\d+[- ]day returns?|returns? (?:are|is) (?:free|easy)|"
                        r"send it back|return it|returnable|no questions asked|risk[- ]free|money[- ]back)\b", re.I)
# claims that are only true when the product's facts (site, product data, PLAYBOOK section 1) say them
CLAIMS = [
    (r"water ?proof", "waterproof (the site says water-resistant)"),
    (r"(?:genuine|real|full-grain|full grain|top-grain|top grain|italian|100% ?) leather|cowhide|vegan leather",
     "a leather grade"),
    (r"hand-?(?:made|crafted|stitched|sewn)|hand (?:made|crafted|stitched|sewn)|made by hand", "handmade"),
    (r"lifetime(?: warranty| guarantee)?", "a lifetime warranty"),
    (r"money-back|money back|guarantee[ds]?", "a guarantee"),
    (r"\w+[- ]years? warranty", "a warranty length"),
    (r"free returns?|easy returns?|\d+[- ]day returns?", "returns"),
    (r"free (?:us |u\.s\. )?(?:shipping|delivery)", "free shipping"),
    (r"(?:worldwide|international|global) (?:shipping|delivery)", "worldwide shipping"),
    (r"best[- ]?sell(?:er|ers|ing)|#\s?1|number one|no\. ?1|top[- ]rated|most popular|award[- ]winning|as seen on|"
     r"world'?s best|best bag", "a ranking / superlative"),
    (r"\d(?:\.\d)?[- ]?stars?|five[- ]stars?|★+", "a star rating"),
    (r"thousands of|millions of|hundreds of|\d[\d,]*\+? (?:happy |satisfied )?(?:customers|women|people|buyers|orders|"
     r"reviews|sold)", "a customer count"),
    (r"scientifically|proven|certified|patent(?:ed)?", "a proof / certification"),
    (r"lowest prices?|cheapest|best price|never (?:be )?(?:this )?(?:cheap|low)(?:er)?", "a lowest-price claim"),
    (r"biggest (?:sale|discount|deal|offer)s?(?: of the year| ever)?", "a biggest-sale claim (the same % runs all year)"),
    (r"eco-?friendly|sustainabl[ey]|recycled|organic|biodegradable|cruelty-?free|vegan", "an eco claim"),
    (r"celebrit(?:y|ies)|influencers?", "celebrity use"),
    (r"sold out|selling out|restock(?:ed)?|back in stock|only \w+ left|limited stock|low stock|almost gone",
     "scarcity"),
    (r"theft-?proof|pickpocket-?proof|thief-?proof|100% secure|unbreakable|indestructible|bullet-?proof|cut-?proof|"
     r"knife-?proof", "an absolute security claim"),
    # features of one bag only: never said of another (the Vintage Bag has no anti-theft pocket, only Hobo 2.0 has RFID)
    (r"rfid", "an RFID lining"), (r"lockable", "lockable zippers"), (r"cut-?resistant", "a cut-resistant strap"),
    (r"table (?:security )?strap", "a table strap"), (r"anti-?theft", "anti-theft"),
    (r"water-?resistant", "water-resistant"), (r"scratch-?(?:proof|resistant)", "scratch-proof"),
    (r"hidden (?:back )?pockets?", "a hidden pocket"), (r"laptops?", "fits a laptop"),
    (r"(?:6|six)-?layer", "6-layer security"),
]
CLAIMS = [(re.compile(r"(?<![\w-])(?:" + p + r")(?![\w-])", re.I), why) for p, why in CLAIMS]
# the brand voice never speaks as a customer (PLAYBOOK section 1, the client: never switch the point of view)
TESTIMONIAL = re.compile(
    r"\bI(?:'ve| have)? (?:just )?(?:bought|ordered|purchased|got (?:mine|one|this|it|my))\b|\bI(?:'m| am) (?:obsessed|"
    r"in love)\b|\bI (?:love|adore|use|carry) (?:mine|it|this|my)\b|\bmine\b|\bmy (?:sister|mum|mom|mother|daughter|son|"
    r"wife|husband|friend|grandma|grandmother|bag|hobo|vintage)\b|\bI've (?:had|been using|been carrying|carried|owned)\b",
    re.I)
WHY = dict(numbers="a number the product's facts don't have (invented numbers / stats are not allowed)",
           claims="a claim the product's facts don't back (only true claims: site, product data, PLAYBOOK section 1)",
           testimonial="the brand voice speaking as a customer (no fake testimonials, never switch the point of view)",
           offer="more than the product's real offer (new_product.unbacked)")

# ---------------------------------------------------------------- numbers
ONES = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                   "fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1}
ORDS = {w: i + 4 for i, w in enumerate("fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
                                       "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth".split())}
SPECIAL = {"dozen": 12, "decade": 10}
MULT = {"hundred": 100, "thousand": 1000, "million": 1000000}
TOKEN = re.compile(r"(?<![A-Za-z0-9.])\$?\d[\d,]*(?:\.\d+)?|[A-Za-z]+(?:-[A-Za-z]+)*")


def numbers(text):
    """[(value, token, start, end)]: digits ('$52.50', '3.5', '1,000', '7th' -> 7) and number words ('six-layer' -> 6,
    'twenty-five', 'ten thousand', 'a decade'); 'first' / 'second' / 'third' are sequence words, never stats."""
    text = text or ""
    out = []
    toks = list(TOKEN.finditer(text))
    i = 0
    while i < len(toks):
        m = toks[i]
        t, v, a, b = m.group(0), None, m.start(), m.end()
        if t[0] in "$0123456789":
            try:
                v = float(t.lstrip("$").replace(",", ""))
            except ValueError:
                v = None
        else:
            parts = t.lower().split("-")
            p0 = parts[0]
            if p0 in TENS and len(parts) > 1 and parts[1] in ONES and ONES[parts[1]] < 10:
                v = TENS[p0] + ONES[parts[1]]
            elif p0 in ONES or p0 in TENS:
                v = ONES.get(p0, TENS.get(p0))
                nxt = toks[i + 1].group(0).lower() if i + 1 < len(toks) else ""
                if p0 in TENS and len(parts) == 1 and nxt in ONES and ONES[nxt] < 10:      # 'twenty five'
                    v, i, b = v + ONES[nxt], i + 1, toks[i + 1].end()
            elif p0 in ORDS:
                v = ORDS[p0]
            elif p0 in SPECIAL:
                v = SPECIAL[p0]
            elif p0 in MULT and len(parts) == 1:
                if out and out[-1][3] >= a - 1:                             # 'ten thousand': fold into the number before
                    pv, _, a, _ = out.pop()
                    v = pv * MULT[p0]
                else:
                    v = MULT[p0]
        if v is not None:
            out.append((v, text[a:b], a, b))
        i += 1
    return out


def years():
    y = datetime.date.today().year
    return {float(y), float(y + 1)}


# ---------------------------------------------------------------- facts (what claims may rest on)
def flat(s):
    """Lower case, hyphens as spaces, number words as digits: 'One-hand clasp' ~ '1 hand clasp', 'Water-resistant' ~
    'water resistant'; plurals folded ('pockets' ~ 'pocket')."""
    s = re.sub(r"[‐-―-]", " ", (s or "").lower())
    s = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", s)
    ws = []
    for w in re.findall(r"[a-z0-9%$.']+", s):
        w = w.strip(".'")
        w = str(ONES[w]) if w in ONES else str(TENS[w]) if w in TENS else w
        ws.append(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return " " + " ".join(ws) + " "


HANDMADE = re.compile(r"hand[\s-]?mak\w*|made by (?:\w+ ){0,2}hands?|hand[\s-]?stitch\w*|hand[\s-]?craft\w*", re.I)


def corpus_text(*parts):
    t = " \n ".join(p for p in parts if p)
    return flat(t + (" handmade" if HANDMADE.search(t) else ""))


def playbook():
    """(product rows of the PLAYBOOK section 1 table, the store-wide offer bullet) as text."""
    try:
        txt = open(PLAYBOOK, encoding="utf-8").read()
    except OSError:
        return [], ""
    sec = re.split(r"\n## ", txt.split("\n## 1.", 1)[1] if "\n## 1." in txt else "")[0]
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in sec.splitlines()
            if ln.strip().startswith("|") and not set(ln.strip()) <= set("|- ")]
    offer = re.search(r"- \*\*Offer.*?(?=\n- \*\*|\Z)", sec, re.S)
    return rows[1:], offer.group(0) if offer else ""


def playbook_row(name, rows):
    """The product's row of the PLAYBOOK section 1 table (cells: product, price, colours, key claims), [] if none."""
    n = (name or "").lower().strip()
    if not n:
        return []
    exact = [r for r in rows if r and (r[0].lower() == n or f'("{n}")' in r[0].lower() or f'"{n}"' in r[0].lower())]
    near = sorted((r for r in rows if r and n in r[0].lower()), key=lambda r: len(r[0]))
    return (exact or near or [[]])[0]


def find_facts(out, site=None):
    """The product's site facts file in $OUT/site (make_batch plan writes <key>_facts.json), or {}."""
    fs = sorted(glob.glob(os.path.join(out, "site", "*_facts.json")))
    if not fs:
        return {}
    key = re.sub(r"[^a-z0-9]+", "_", (site or "").lower()).strip("_")[:24]
    pick = [f for f in fs if os.path.basename(f) == f"{key}_facts.json"] if key else []
    if not pick and site:
        pick = [f for f in fs if key and key in os.path.basename(f)]
    if not pick and len(fs) == 1 and not site:
        pick = fs
    try:
        return json.load(open(pick[0])) if pick else {}
    except (OSError, ValueError):
        return {}


def parse_offer(o):
    """(pct, gift) from '50% off + free matching pouch wallet' / (50, 'gift') / an offer block; None = no offer known."""
    if o is None:
        return None
    if isinstance(o, (tuple, list)):
        return (int(o[0]) if o[0] else None), (o[1] or None)
    if isinstance(o, dict):
        import make_batch
        return make_batch.deal_of(o)
    s = str(o)
    m = re.match(r"\s*(\d+)\s*%", s)
    gift = s.split(" + ", 1)[1].strip() if " + " in s else (s.strip() if re.match(r"\s*(?:a\s+)?free\b", s, re.I) else None)
    return (int(m.group(1)) if m else None), (re.sub(r"^(?:a|an)\s+", "", gift, flags=re.I) if gift else None)


_CAMPAIGN = [None]       # the store-wide sale campaign of the batch being checked (campaign.py; plan / check_out set it)


def use_campaign(c):
    """Every context() from now on carries this campaign (None: none): its facts back claims and numbers, its approved
    phrases ('up to 60% off', 'free gifts', 'a free jewellery box') back offer words."""
    _CAMPAIGN[0] = c or None


def context(product=None, offer=None, facts=None, out=None, extra=(), campaign=False):
    """What the texts of one product may say: its real offer, its facts (corpus for claims) and the numbers in them.
    campaign: a campaign dict (campaign.py), None for none; default: the one use_campaign() set.
    product: a key / name ('Hobo Bag', 'vintage', a product file) or a make_batch product dict; offer: see
    parse_offer (default: the product's stored offer); facts: a site facts dict or file (default: $OUT/site). A
    Drive-only product (drive_only()): only its product file (notes, features), never PLAYBOOK section 1 or $OUT/site."""
    import make_batch
    pr, files = None, {}
    if isinstance(product, dict):
        pr = product
    elif product:
        files = make_batch.product_files(make_batch.products_dir())
        pk = make_batch.pick_product(product, files)
        pr = make_batch.product(pk, files) if pk else None
    if isinstance(facts, str):
        facts = json.load(open(facts)) if os.path.exists(facts) else {}
    only = drive_only(pr)
    if facts is None and out and pr and not only:
        facts = find_facts(out, pr.get("site"))
    facts = facts or {}
    deal = parse_offer(offer) if offer is not None else (make_batch.deal_of(pr["offer"]) if pr else None)
    rows, store = playbook()
    if only:                  # the client's folder is the only source: no store-wide bullet (free US shipping), no row
        rows, store = [], ""
    # evidence = the site, the PLAYBOOK row and the product's data (features, product-file facts); never our own hook
    # lines (hooks.json, a product file's 'hooks'): they are checked like any other line, they don't back themselves
    pf = (pr or {}).get("facts") or {}
    row = list(playbook_row((pr or {}).get("name"), rows))
    if len(row) > 2:          # the colours cell without its notes ('(Beige was sold out ... by 10-09 ...)' is no evidence)
        row[2] = re.sub(r"\s*\([^)]*\)", "", row[2])
    colours = [c for v in (facts.get("options") or {}).values() for c in v] or list(facts.get("colours") or {}) or \
        list(pf.get("colours") or []) or [c.strip() for c in (row[2] if len(row) > 2 else "").split(",") if c.strip()]
    prod = "\n".join(x for x in [
        " | ".join(row), (pr or {}).get("name"), (pr or {}).get("short"), (pr or {}).get("end"),
        facts.get("title"), facts.get("description"), " ".join(facts.get("bullets") or []),
        " ".join(facts.get("highlights") or []), pf.get("title"), pf.get("description"), pf.get("notes"),
        " ".join(f"{f[0]} {f[1]}" for f in (pr or {}).get("features") or [])] + list(extra) if x)
    camp = _CAMPAIGN[0] if campaign is False else campaign
    if camp:
        import campaign as campaign_mod
        prod += "\n" + campaign_mod.corpus(camp)
    nums = {round(v, 2) for v, *_ in numbers(prod)}
    if camp:
        nums |= {round(x, 2) for x in campaign_mod.numbers(camp)}
    pct, gift = deal or (None, None)
    nums |= {float(x) for x in (pct,) if x}
    for k in ("price", "compare_at"):
        try:
            nums.add(round(float(facts.get(k) or (pf.get(k) if pf else None) or "x"), 2))
        except ValueError:
            pass
    if colours:
        nums.add(float(len(colours)))
    return dict(product=(pr or {}).get("name"), key=(pr or {}).get("key"), offer=deal, pct=pct, gift=gift,
                corpus=corpus_text(prod, store), numbers=nums, colours=colours, drive_only=only, campaign=camp or None)


def drive_only(pr):
    """A product known only from the client's Drive folder (a product file with no libracases.com page: "site" null,
    source.kind drive / local): its ads say only what its notes say, so PLAYBOOK's store-wide lines (free US shipping)
    and the site are no evidence for it."""
    return bool(pr) and pr.get("source") != "built-in" and not pr.get("site")


_REV = []


def reviews():
    """reviews.json entries (cached), [] when unreadable."""
    if not _REV:
        try:
            _REV.extend(json.load(open(REVIEWS))["reviews"])
        except (OSError, ValueError, KeyError):
            _REV.append({})
    return [r for r in _REV if r.get("text")]


def reviews_flat():
    return [flat(r["text"]) for r in reviews()]


def attributed(seg):
    """True when seg tells what a named customer wrote in the brand voice ('Carol calls it the best bag she has ever
    bought.', 'One customer says it holds everything they need ...'): it starts with the reviewer's first name (or 'One
    customer' for one known by initials) and every other word is in that review or a framing word (make_batch.third)."""
    import make_batch
    ws = make_batch.flat(seg).split()
    for r in reviews():
        who = r.get("name", "").split()[0].rstrip(".").lower() if r.get("name") else ""
        who = "one customer" if len(who) < 2 else who
        if ws[:len(who.split())] != who.split():
            continue
        if set(ws) - make_batch.FRAMING - set(who.split()) <= set(make_batch.flat(r["text"]).split()) | {"it's"}:
            return True
    return False


def raw_text(key):
    """A winner RAW's transcript as one text ('3 .5' -> '3.5', '15 -20' -> '15-20'), '' when there is none."""
    f = os.path.join(TRANS, f"{key}_words.json")
    try:
        ws = json.load(open(f))
    except (OSError, ValueError):
        return ""
    t = " ".join(w["w"] if isinstance(w, dict) else w[0] for w in ws)
    return re.sub(r"(\d) ([.\-]\d)", r"\1\2", t)


def raw_numbers(t):
    """The numbers a RAW says, plus the differences of any two (its '20' and '36' back a '16 YEARS' label)."""
    ns = {round(v, 2) for v, *_ in numbers(t)}
    return ns | {round(abs(a - b), 2) for a, b in itertools.combinations(ns, 2)}


# ---------------------------------------------------------------- the client's RAW audio (winner remixes)
# Julian (2026-10-09): never a health / medical CLAIM, not even in the client's own RAW. A RAW line that says the bag
# helps the body ('an adjustable strap that prevents shoulder pain', 'machines don't care if the strap hurts your
# shoulder') is cut out of the RAW (clip_bank winner_raws[key].edit.claim_cuts) or the winner is left out. The RAW's
# story (Susan's arthritis, her doctor, her sister robbed) is approved material (PLAYBOOK section 1): heard as it is,
# and listed for a human (raw_story in compliance.json, plan warnings, the run report).
BENEFIT = _words(r"prevent\w*", r"reliev\w*", r"relief", r"reduc\w*", r"eas(?:e|es|ed|ing)", r"cur(?:e|es|ed)",
                 r"heal\w*", r"help(?:s|ed)?", r"protect\w*", r"support\w*", r"sooth\w*", r"no more", r"pain-?free",
                 r"good for", r"better for", r"gentle on", r"kind to")
BODY_HURT = re.compile(r"\b(?:straps?|bags?|handles?|it|this)\b(?:\W+\w+){0,3}?\W+(?:hurt|hurts|hurting|aches?|strains?|"
                       r"digs? into)\b(?:\W+\w+){0,2}?\W+(?:shoulders?|back|neck|hands?|wrists?|arms?|skin)\b", re.I)


STORY_MED = _words(r"doctors?", r"nurses?", r"lose function")    # medical story words (never a claim by themselves)


def raw_sentences(ws, ranges):
    """The sentences heard in the RAW pieces `ranges` ([a, b] RAW seconds): [(text, start, end)], only the words inside
    the pieces; a cut ends a sentence (what plays is what is checked)."""
    out, cur, last = [], [], None
    for i, w in enumerate(ws):
        if not any(w["e"] > a + 0.02 and w["s"] < b - 0.02 for a, b in ranges):
            continue
        if cur and last is not None and i != last + 1:
            out.append(cur)
            cur = []
        cur.append(w)
        last = i
        if w["w"].rstrip("\"')").endswith((".", "?", "!")):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [(re.sub(r"(\d) ([.\-%]\d?)", r"\1\2", " ".join(x["w"] for x in s)), s[0]["s"], s[-1]["e"]) for s in out]


def raw_audit(ws, ranges):
    """(claims, story) in the RAW words a remix plays (ranges). claims = problems: a health word in a line that says the
    bag helps (BENEFIT: prevents, relieves, no more ...) or a line about the bag hurting the body (BODY_HURT), and any
    drugs / politics / religion / blood / violence / profanity word. story = the approved story's own health / crime
    words (arthritis, her doctor, robbed): heard as is, listed for a human. Each: dict(text, start, end, category, term)."""
    claims, story = [], []
    for text, s, e in raw_sentences(ws, ranges):
        hurt, ben = BODY_HURT.search(text), BENEFIT.search(text)
        found = []
        for cat, rx, _ in CATEGORIES:
            for m in rx.finditer(text):
                found.append((cat, m.group(0)))
        if hurt and not any(c == "health" for c, _ in found):
            found.append(("health", hurt.group(0)))
        if not any(c == "health" for c, _ in found) and STORY_MED.search(text):    # 'her doctor told her to stop'
            found.append(("health", STORY_MED.search(text).group(0)))
        for cat, term in found:
            d = dict(text=text, start=round(s, 2), end=round(e, 2), category=cat, term=term)
            (claims if cat in HARD or (cat == "health" and (ben or hurt)) else story).append(d)
    return claims, story


def raw_words(key):
    """A winner RAW's committed transcript (pipeline/data/transcripts/<key>_words.json) as word dicts, [] if none."""
    try:
        ws = json.load(open(os.path.join(TRANS, f"{key}_words.json")))
    except (OSError, ValueError):
        return []
    return [w if isinstance(w, dict) else dict(w=w[0], s=w[1], e=w[2]) for w in ws]


def remix_ranges(spec, dur=None, body_only=False):
    """RAW seconds a remix spec plays: its cold open, then its body pieces (remix.body_pieces: the cuts and the claim
    cuts left out)."""
    import remix
    co = [] if body_only or not spec.get("cold_open") else [list(spec["cold_open"])]
    return co + [p for p in remix.body_pieces(spec, dur or spec.get("end") or 9999) if p != "REVIEWS"]


def winner_raw_dur(key):
    try:
        return (json.load(open(os.path.join(HERE, "data", "clip_bank.json")))["winner_raws"].get(key) or {}).get("dur")
    except (OSError, ValueError, KeyError):
        return None


def cold_opens(key, cos):
    """A winner's cold opens fit to use: none whose words make a health claim (raw_audit) and none whose on-screen label
    names a health condition (Julian: no label does; winner_prep --check asks for a story label), each marked "medical"
    when its words name one (the approved story: 'The arthritis has won.'); those come last, so H1 (and the first
    versions) open on something else."""
    ws, res = raw_words(key), []
    for c in cos or []:
        r = c.get("range")
        claims, story = raw_audit(ws, [r]) if r and ws else ([], [])
        if claims or HEALTH.search(c.get("label") or ""):
            continue
        med = bool(HEALTH.search(c.get("line") or "") or any(x["category"] == "health" for x in story))
        res.append(dict(c, medical=med) if med else dict(c))
    return sorted(res, key=lambda c: bool(c.get("medical")))


def raw_human_notes(key, edit, dur=None, name=None):
    """Plan warnings for one winner RAW (Julian's health rule): the claims cut out of its body, and the approved story's
    health words it still plays (body and cold opens), for the reply and the run report."""
    ws, who, out = raw_words(key), f"{key}" + (f" ({name})" if name and name != key else ""), []
    if not ws:
        return out
    for cc in edit.get("claim_cuts") or []:
        r = cc.get("range") if isinstance(cc, dict) else cc
        said = (cc.get("said") if isinstance(cc, dict) else "") or " ".join(
            w["w"] for w in ws if w["s"] >= r[0] - 0.02 and w["e"] <= r[1] + 0.05)
        before = [w for w in ws if w["e"] <= r[0] + 0.02][-8:]
        while len(before) > 1 and any(w["w"].rstrip("\"')").endswith((".", "?", "!")) for w in before[:-1]):
            before = before[1:]                       # the shortened sentence only
        out.append(f"{who}: Julian's health rule: \"{said}\" is cut out of its proven body (RAW {r[0]:.1f}-{r[1]:.1f} s), so it "
                   f"says \"...{' '.join(w['w'] for w in before)}.\": needs a human to listen to that line once")
    _, story = raw_audit(ws, remix_ranges(edit, dur, body_only=True))
    med = list(dict.fromkeys(x["text"] for x in story if x["category"] == "health"))
    opens = [c.get("label") for c in cold_opens(key, edit.get("cold_opens")) if c.get("medical")]
    if med or opens:
        out.append(f"{who}: needs a human (Julian's health rule): its approved RAW story (PLAYBOOK section 1) plays as is: "
                   + "; ".join(f"\"{t}\"" for t in med[:3]) + (f"; cold open {', '.join(opens)} says it too (used last, "
                                                                f"its label names no condition)" if opens else ""))
    return out


def raw_checks(out, p):
    """The RAW audio of every winner version of the plan: (problems, story notes, claim cuts applied). A health claim
    the version still plays is a problem (render refuses it); the story words and the cuts are for a human to glance at."""
    probs, story, cuts = {}, {}, {}
    for v in p.get("videos") or []:
        key = (v.get("winner") or {}).get("key")
        f = os.path.join(out, v["name"] + ".json")
        if not key or not os.path.exists(f):
            continue
        spec, vid = json.load(open(f)), v.get("id") or v["name"]
        if "raw" not in spec:
            continue
        ws = raw_words(key)
        if not ws:
            continue
        claims, st = raw_audit(ws, remix_ranges(spec, winner_raw_dur(key)))
        for c in claims:
            k = (key, c["text"], c["term"].lower())
            if k in probs:
                probs[k]["where"] += f", {vid}"
                continue
            probs[k] = dict(where=f"{vid} RAW audio of {key} {c['start']:.1f}-{c['end']:.1f} s", text=c["text"],
                            category=c["category"], term=c["term"],
                            why=f"{'a health claim' if c['category'] == 'health' else 'a ' + c['category'] + ' word'} in "
                                f"the client's RAW (Julian 2026-10-09: never, not even in approved RAW audio): cut the "
                                f"sentence (clip_bank winner_raws[{key}].edit.claim_cuts, on word boundaries) or leave "
                                f"the winner out")
        for c in st:
            k = (key, c["text"])
            if k in story:
                if vid not in story[k]["where"]:
                    story[k]["where"] += f", {vid}"
                continue
            story[k] = dict(where=f"{vid} RAW {key} {c['start']:.1f}-{c['end']:.1f} s", text=c["text"],
                            category=c["category"], term=c["term"],
                            why="the client's approved RAW story (PLAYBOOK section 1), heard as is: a human may want to "
                                "check it against Julian's health rule")
        for cc in spec.get("claim_cuts") or []:
            r = cc.get("range") if isinstance(cc, dict) else cc
            k = (key, tuple(r))
            if k not in cuts:
                cuts[k] = dict(where=vid, key=key, range=list(r), said=(cc.get("said") if isinstance(cc, dict) else "") or "",
                               why="cut out of the proven body (Julian's health rule): listen once to the line around it")
            elif vid not in cuts[k]["where"]:
                cuts[k]["where"] += f", {vid}"
        hl = spec.get("hook_label") or ""
        if hl and HEALTH.search(hl):
            k = (key, hl)
            story.setdefault(k, dict(where=f"{vid} hook label", text=hl, category="health", term=HEALTH.search(hl).group(0),
                                     why="an on-screen label repeating the RAW's approved story: a human may want to check "
                                         "it against Julian's health rule"))
    return list(probs.values()), list(story.values()), list(cuts.values())


# ---------------------------------------------------------------- check
def review_segment(text, a, b):
    """True when the sentence around text[a:b] is a customer's own words: verbatim in reviews.json (3+ words), or told in
    the brand voice with the customer named and nothing added (attributed())."""
    cuts = [0] + [m.end() for m in re.finditer(r"[.!?:\"“”]\s*", text)] + [len(text)]
    for s, e in zip(cuts, cuts[1:]):
        if s <= a < max(e, s + 1):
            seg = flat(text[s:e])
            return (len(seg.split()) >= 3 and any(seg in r for r in reviews_flat())) or attributed(text[s:e])
    return False


def _items(texts, source):
    if isinstance(texts, str):
        texts = [texts]
    out = []
    for i, t in enumerate(texts or []):
        if isinstance(t, dict):
            out.append(dict(where=t.get("where") or f"text {i + 1}", text=t.get("text") or "",
                            source=t.get("source") or source, raw=t.get("raw") or ""))
        else:
            out.append(dict(where=f"text {i + 1}", text=str(t or ""), source=source, raw=""))
    return out


def check(texts, product=None, offer=None, facts=None, ctx=None, source="ours", allowed=None, allowed_numbers=None):
    """Problems in texts (see the module doc). ctx: context() (built from product/offer/facts when not given; without
    any, numbers and claims are checked against nothing but 0, 1 and this/next year, and the offer is not checked).
    source per text: 'ours' (default), 'raw' (an on-screen label repeating a RAW: its transcript in 'raw' backs the
    story's words and numbers), 'raw_quote' (ad copy quoting a RAW: numbers / claims backed, health / crime never),
    'review' (a verbatim customer review). Allowed story / review hits go into the list `allowed` when given."""
    import new_product
    if ctx is None:
        ctx = context(product, offer, facts) if (product or offer is not None or facts) else \
            dict(offer=None, pct=None, gift=None, corpus=" ", numbers=set())
    okn = set(ctx["numbers"]) | {0.0, 1.0} | years() | {round(float(x), 2) for x in allowed_numbers or ()}
    probs = []
    for it in _items(texts, source):
        t, src = it["text"], it["source"]
        if not t.strip():
            continue
        rawc = corpus_text(it["raw"]) if it["raw"] else " "
        rawn = raw_numbers(it["raw"]) if it["raw"] else set()
        found = []

        def hit(cat, term, why, a, b, rx=None):
            """A word of a category: a problem, or (story / review material) an allowed hit."""
            in_review = src == "review" or (src == "ours" and review_segment(t, a, b))
            said = src in ("raw", "raw_quote") and cat != "numbers" and (           # the RAW says it (a story word in
                f" {flat(term).strip()} " in rawc or                                 # any form: ROBBERY ~ 'robbed')
                (HANDMADE.search(term) is not None and " handmade " in rawc) or
                (cat in STORY and rx is not None and any(m.group(0).lower()[:4] == term.lower()[:4]
                                                         for m in rx.finditer(it["raw"]))))
            ok = None
            if cat in LABEL_STORY and src == "raw" and said:
                ok = "the RAW's approved story (PLAYBOOK section 1)"
            elif cat in ("numbers", "claims", "testimonial") and in_review:
                ok = "a customer review (verbatim, or attributed to the customer by name)"
            elif cat in ("claims", "testimonial") and (said or (cat == "testimonial" and src != "ours")):
                ok = "the RAW's own words"
            if ok:
                if allowed is not None:
                    allowed.append(dict(where=it["where"], text=t, category=cat, term=term, why=ok))
                return
            found.append(dict(where=it["where"], text=t, category=cat, term=term, why=why))
        for cat, rx, why in CATEGORIES:
            for m in rx.finditer(t):
                hit(cat, m.group(0), why, m.start(), m.end(), rx)
        final = bool((ctx.get("campaign") or {}).get("final_sale"))
        if final:
            for m in FINAL_SALE.finditer(t):
                hit("claims", m.group(0), "a returns promise: Black Friday Sale items are final sale (the site's sale terms); the 1-year "
                    "warranty and faulty-item cover still hold, say those instead", m.start(), m.end())
        for rx, what in CLAIMS:
            if final and what in ("returns", "a guarantee"):
                continue                  # (FINAL_SALE above)
            for m in rx.finditer(t):
                ph = flat(m.group(0))
                if ph in ctx["corpus"] or (what == "free shipping" and " free shipping " in ctx["corpus"].replace(
                        " free us shipping ", " free shipping ").replace(" free delivery ", " free shipping ")):
                    continue
                hit("claims", m.group(0), f"{what}: {WHY['claims']}", m.start(), m.end())
        if src in ("ours", "raw_quote"):
            for m in TESTIMONIAL.finditer(t):
                hit("testimonial", m.group(0), WHY["testimonial"], m.start(), m.end())
        # (new_product.unbacked takes 'free US shipping' for a free gift: it only knows 'free shipping / delivery')
        t_offer = t
        if ctx.get("campaign"):           # 'up to 60% off', 'free gifts', 'a free jewellery box': the sale's own words
            import campaign as campaign_mod
            t_offer = campaign_mod.strip(t, ctx["campaign"])
        why_offer = new_product.unbacked(re.sub(r"\bfree (?:US|U\.S\.) (shipping|delivery)\b", r"free \1", t_offer, flags=re.I),
                                         ctx["pct"], ctx["gift"]) if ctx.get("offer") is not None else None
        if why_offer:
            hit("offer", why_offer, f"it claims {why_offer}: {WHY['offer']} ({_offer_str(ctx)})", 0, 0)
        for v, tok, a, b in numbers(t):
            v = round(v, 2)
            if v in okn:
                continue
            if src in ("raw", "raw_quote") and v in rawn:
                if allowed is not None:
                    allowed.append(dict(where=it["where"], text=t, category="numbers", term=tok, why="the RAW's own words"))
                continue
            if why_offer and re.match(r"\s*(?:%|percent)", t[b:]):
                continue                                       # the % is already the offer problem
            hit("numbers", tok, f"{WHY['numbers']}; allowed: {_nums(okn)}", a, b)
        seen = set()
        for f in found:
            k = (f["category"], f["term"].lower())
            if k not in seen:
                seen.add(k)
                probs.append(f)
    return probs


def _nums(ns):
    show = sorted(n for n in ns if n not in years())
    return ", ".join(f"{n:g}" for n in show[:14]) + (" ..." if len(show) > 14 else "")


def _offer_str(ctx):
    pct, gift = ctx.get("pct"), ctx.get("gift")
    return "the offer: " + (" + ".join(x for x in (f"{pct}% off" if pct else "no discount", gift) if x))


# ---------------------------------------------------------------- a whole batch ($OUT)
SKIP_KEYS = {"name", "layout", "photo", "photo_box", "src", "path", "bg", "size", "hsize", "psize", "qsize", "dots",
             "accent_lines", "masks", "crops", "card_photos", "box", "mask", "x", "y", "tx", "ty", "id", "verified",
             "review_n", "colour", "color", "file", "zoom", "reviews", "ai", "tint", "frame"}   # stars' reviews: as review items (batch_items)


def visible(d, where):
    """Every visible string of a static (generic walk, layout keys skipped): [(where, text)]."""
    out = []
    if isinstance(d, str):
        out.append((where, d))
    elif isinstance(d, list):
        for i, x in enumerate(d):
            out += visible(x, f"{where}[{i}]")
    elif isinstance(d, dict):
        for k, v in d.items():
            if k not in SKIP_KEYS and not (isinstance(v, str) and re.search(r"\.(?:jpe?g|png|webp|mp4|mp3)$", v, re.I)):
                out += visible(v, f"{where}.{k}")
    return out


def review_item(n, where):
    try:
        r = {x["n"]: x for x in json.load(open(REVIEWS))["reviews"]}[n]
    except (OSError, ValueError, KeyError):
        return []
    return [dict(where=where, text=r["text"], source="review"), dict(where=where + ".name", text=r["name"], source="review")]


def batch_items(out):
    """Every text of a planned batch with its source: (items for the main product, {product name: items})."""
    p = json.load(open(os.path.join(out, "plan.json")))
    items = []
    for t in json.load(open(os.path.join(out, "tts_needed.json"))) if os.path.exists(os.path.join(out, "tts_needed.json")) else []:
        items.append(dict(where=f"voiceover {t['file']}", text=t["text"], source="ours"))
    st = os.path.join(out, "statics.json")
    for s in (json.load(open(st)).get("ads") or []) if os.path.exists(st) else []:
        sid = s.get("name", "static").rsplit("_", 2)[-2:]
        w = "_".join(sid)
        items += [dict(where=a, text=x, source="ours") for a, x in visible(s, w)]
        if s.get("review_n"):
            items += review_item(s["review_n"], f"{w}.review")
        for r in s.get("reviews") or []:          # stars: review numbers, a pinned snippet {n, text}, a site {quote, author}
            if isinstance(r, int) or (isinstance(r, dict) and r.get("n") and not r.get("text")):
                items += review_item(r if isinstance(r, int) else r["n"], f"{w}.stars")
            elif isinstance(r, dict):
                items += [dict(where=f"{w}.stars", text=x, source="review") for x in (r.get("text") or r.get("quote"),
                                                                                       r.get("author")) if x]
    other = {}
    for v in p.get("videos") or []:
        f = os.path.join(out, v["name"] + ".json")
        if not os.path.exists(f):
            continue
        spec, vid = json.load(open(f)), v.get("id") or v["name"]
        win = v.get("winner") or {}
        sink = items if not win or win.get("product") in (None, p.get("product")) else other.setdefault(win["product"], [])
        if "raw" in spec:
            raw = raw_text(win.get("key") or "")
            for x in [spec.get("hook_label")] + [lb.get("text") for lb in spec.get("labels") or []]:
                if x:
                    sink.append(dict(where=f"{vid} label", text=x, source="raw" if raw else "ours", raw=raw))
            for k in ("offer_title", "offer_sub", "end_title", "end_sub"):
                if spec.get(k):
                    sink.append(dict(where=f"{vid} {k}", text=spec[k], source="ours"))
            for c in (spec.get("reviews") or {}).get("cards") or []:
                sink += review_item(c.get("n"), f"{vid} review card")
            continue
        for o in spec.get("overlays") or []:
            if o.get("type") == "review":
                sink += review_item(o.get("n"), f"{vid} review card")
                continue
            for k in ("text", "title", "sub", "lines"):
                for x in (o.get(k) if isinstance(o.get(k), list) else [o.get(k)]):
                    if isinstance(x, str) and x.strip():
                        sink.append(dict(where=f"{vid} {o.get('type', 'overlay')}", text=x, source="ours"))
        for b_ in spec.get("blocks") or []:            # a presenter's lines (presenter.py): her take says the script's words
            if b_.get("talk") and b_.get("text"):
                sink.append(dict(where=f"{vid} presenter {os.path.basename(b_['talk'])}", text=b_["text"], source="ours"))
        off = spec.get("offer") or {}
        for k in ("title", "sub"):
            if off.get(k):
                sink.append(dict(where=f"{vid} offer {k}", text=off[k], source="ours"))
        for k in ("end_title", "end_sub"):
            if spec.get(k):
                sink.append(dict(where=f"{vid} {k}", text=spec[k], source="ours"))
    cp = os.path.join(out, "ad_copy.csv")
    if os.path.exists(cp):           # placement groups as ad_copy.groups(): the projects, or (--hooks 1) each video
        gs = p.get("projects") or [dict(id=v["id"], engine=v.get("engine", "storyboard"), winner=v.get("winner"))
                                    for v in p.get("videos") or [] if v.get("id")]
        raws = {x["id"]: raw_text((x.get("winner") or {}).get("key") or "") for x in gs if x.get("engine") == "remix"}
        prods = {x["id"]: (x.get("winner") or {}).get("product") for x in gs}
        for r in csv.DictReader(open(cp, encoding="utf-8-sig")):
            g = r.get("placement_group") or ""
            prod = prods.get(g)
            sink = items if prod in (None, p.get("product")) else other.setdefault(prod, [])
            for k in ("primary_text_1", "primary_text_2", "headline_1", "headline_2", "description", "cta"):
                if r.get(k):
                    sink.append(dict(where=f"ad copy {r['ad_name']} {k}", text=r[k], source="ours"))
            if r.get("hook_first_line"):
                sink.append(dict(where=f"ad copy {r['ad_name']} hook_first_line", text=r["hook_first_line"],
                                 source="raw_quote" if raws.get(g) else "ours", raw=raws.get(g) or ""))
    return p, items, other


def dedupe(items):
    """One entry per (text, source): versions of a project share most texts; 'where' keeps every place."""
    by = {}
    for it in items:
        k = (it["text"], it["source"], it.get("raw", "")[:40])
        if k in by:
            by[k]["where"] += ", " + it["where"] if it["where"] not in by[k]["where"] else ""
        else:
            by[k] = dict(it)
    return list(by.values())


COUNT_WORD = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|\d{1,2})\s+(?:things|reasons|details)\b", re.I)


def count_words(probs, allowed, nums):
    """A ugc hook that counts ('Four things you'll notice ...', its label '4 THINGS') says the number of chapters the video then
    shows, not a stat: plan.json 'ugc_numbers' (ugc_script's script['numbers']). Those 'numbers' hits move to `allowed`; every
    other hit stays. -> the problems left."""
    nums, keep = {float(x) for x in nums or ()}, []
    for x in probs:
        w = {m.group(1).lower(): (int(m.group(1)) if m.group(1).isdigit() else ONES[m.group(1).lower()]) for m in COUNT_WORD.finditer(x["text"])}
        if nums and x["category"] == "numbers" and w.get(x["term"].lower()) in nums:
            allowed.append(dict(x, why="the count of the chapters the video shows ('Four things ...'), not a stat"))
        else:
            keep.append(x)
    return keep


def check_out(out):
    p, items, other = batch_items(out)
    probs, allowed = [], []
    use_campaign(p.get("campaign"))
    ctx = context(p.get("product_key") or p.get("product"), offer=p.get("offer"), out=out)
    probs += count_words(check(dedupe(items), ctx=ctx, allowed=allowed), allowed, p.get("ugc_numbers"))
    for name, its in other.items():       # a winner of another product (its own offer and facts)
        probs += check(dedupe(its), ctx=context(name, out=out), allowed=allowed)
    rp, story, cuts = raw_checks(out, p)  # the client's RAW audio each winner version plays (health claims: never)
    probs += rp
    for x in probs + allowed + story:
        if len(x["where"]) > 300:
            x["where"] = x["where"][:300] + " ..."
    return dict(ok=not probs, product=p.get("product"), offer=p.get("offer"),
                checked=len(items) + sum(map(len, other.values())), problems=probs, allowed=allowed,
                raw_story=story, raw_cuts=cuts)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="a planned batch: scan its voiceover lines, statics, video specs and ad_copy.csv")
    ap.add_argument("--text", action="append", help="a line to check (repeatable)")
    ap.add_argument("--product", help="product for --text (its facts and offer)")
    ap.add_argument("--offer", help="offer for --text, e.g. '50%% off + free matching pouch wallet' (default: the product's)")
    ap.add_argument("--theme", help="for --text: the batch's theme ('black friday'): the sale campaign running today backs its words")
    a = ap.parse_args()
    if a.theme and not a.out:
        import campaign as campaign_mod
        import make_batch
        use_campaign(campaign_mod.active(make_batch.pick_theme(a.theme)))
    if a.out:
        rep = check_out(os.path.abspath(a.out))
        rep["report"] = os.path.join(os.path.abspath(a.out), "compliance.json")
        json.dump(rep, open(rep["report"], "w"), indent=1, ensure_ascii=False)
    elif a.text:
        ctx = context(a.product, offer=a.offer) if (a.product or a.offer) else None
        probs = check(a.text, ctx=ctx)
        rep = dict(ok=not probs, product=(ctx or {}).get("product"), checked=len(a.text), problems=probs)
    else:
        ap.error("--out or --text")
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(0 if rep["ok"] else 1)


if __name__ == "__main__":
    main()

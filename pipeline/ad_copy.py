#!/usr/bin/env python3
"""Meta ad copy (primary texts, headlines, description, CTA button) for every ad of a planned batch, written from the
product's own data: its features, its real offer (the % and gift make_batch.py plan read from libracases.com), the site
facts in $OUT/site, the theme and each ad's angle / hook. A Drive-only new product (no libracases.com page) has only its
folder's notes: no 'free US shipping' or 'on libracases.com' line unless the notes say it. Template-based and
deterministic (no LLM calls); --seed gives other picks. Every line passes compliance.check (no health / drug / political / religious / violent words, no profanity,
no number or claim the facts don't have, nothing beyond the real offer); a line that fails is replaced by the next
template, and a field nothing compliant fits is left empty and reported (exit 1).

Per static (S01 ..) one set. Per project (P01 ..) one set shared by its versions H1-H4 (the agencies split-test the hook
on a proven body, so the copy stays the same) plus each version's opening line as an optional first line
(hook_first_line: our spoken hook, or a winner RAW's cold open in quotes; a RAW line with a health or crime word, e.g.
"The arthritis has won", is left out: new text never makes a health claim).

  python3 pipeline/ad_copy.py --out $OUT [--seed N]
      after make_batch.py plan: writes $OUT/ad_copy.csv (one row per ad: ad_name, placement_group, primary_text_1,
      primary_text_2, headline_1, headline_2, description, cta, hook_first_line) and $OUT/ad_copy.json (per static /
      project, with each version's hook variant of primary_text_2 and notes); prints a summary with samples

Meta limits used: primary_text_1 1-2 lines (<= 125 characters, no emoji), primary_text_2 3-5 lines with line breaks and
at most 2 emojis, headlines <= 40 characters, description <= 30, cta one of Meta's buttons (Get Offer for a sale theme
with a deal, else Shop Now). No em dashes. The Slack session may refine wording afterwards within the same rules, then
re-runs python3 pipeline/compliance.py --out $OUT (it scans ad_copy.csv too).
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compliance  # noqa: E402
import make_batch as mb  # noqa: E402

COLUMNS = ["ad_name", "placement_group", "primary_text_1", "primary_text_2", "headline_1", "headline_2", "description",
           "cta", "hook_first_line"]
LIMITS = dict(primary_text_1=125, headline=40, description=30, hook_first_line=125)
CTA_TYPE = {"Shop Now": "SHOP_NOW", "Get Offer": "GET_OFFER"}
SALE_NAME = {"black friday": "Black Friday", "cyber monday": "Cyber Monday", "cyber week": "Cyber Week"}
EMOJI = {"black friday": "🖤", "cyber monday": "⏰", "cyber week": "🛍️", "christmas": "🎁", "gift": "🎁",
         "mothers day": "💐", "travel": "✈️", "default": "👜"}
SHIP = re.compile(r"free (?:us |u\.s\. )?(?:shipping|delivery)", re.I)
SITE_LINE = "Tap the link to see the {short}."    # a Drive-only product's 'Shop the X on libracases.com.'
EMOJI_RX = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u23F0-\u23FF]")
DASHES = re.compile("[\u2013\u2014\u2015]")       # en / em dashes: never in our copy (the client)

# ---------------------------------------------------------------- templates
# Placeholders: make_batch.offer_vars() ({short} {P} {gift_sp} {gift_w} ...) plus {TH} (sale name), {Gift_t} / {GIFT_Wt}
# (title case gift), {N} / {colour_list} (site colours), {t1} {t2} (feature tags, title case), {hq} (short review quote).
# A [...] part drops out when a value in it is empty; a template with an empty value outside [...] is skipped.
OFFER_LINE = {
    "black friday": ["Black Friday: {P} off[ + {gift_sp}].", "This Black Friday: {P} off[ + {gift_sp}]."],   # (no "biggest sale": unprovable)
    "cyber monday": ["Cyber Monday: still {P} off[ + {gift_sp}].", "Last call: {P} off[ + {gift_sp}]."],
    "cyber week": ["Cyber Week: {P} off[ + {gift_sp}].", "Our Cyber Week deal: {P} off[ + {gift_sp}]."],
    "gifting": ["[It arrives with {gift_sp}, and ]it's {P} off right now.", "Now {P} off[, with {gift_sp} in the box]."],
    "default": ["Now {P} off[, with {gift_sp}].", "It's {P} off right now[, with {gift_sp}]."],
    "gift_only": ["It comes with {gift_sp}.", "Every order comes with {gift_sp}."],
    "none": ["Free US shipping.", "Available in {N} colours."],
}
SHORT_OFFER = {
    "sale": ["{TH}: {P} off the {short}[ + {gift_w}].", "{TH} deal: the {short} is {P} off[ + {gift_w}]."],
    "default": ["The {short}: {P} off[ + {gift_w}].", "The {short}, now {P} off[ with {gift_sp}].",
                "{P} off the {short}[ + {gift_w}]."],
    "gift_only": ["The {short} comes with {gift_sp}."],
    "none": ["Meet the {short}.", "Shop the {short} on libracases.com."],
}
CTA_LINE = {
    "Get Offer": ["Tap Get Offer to claim the deal.", "Tap Get Offer before it's gone."],
    "Shop Now": ["Tap Shop Now to get yours.", "Tap Shop Now to find yours."],
    "her": ["Tap Shop Now to get one for her."], "mum": ["Tap Shop Now to get one for mum."],
    "colours": ["Tap Shop Now to pick your colour."],
}
HEADLINES = {
    "offer": ["{short}: {P} Off[ + Free {GIFT_Wt}]", "{P} Off the {short}[ + Free {GIFT_Wt}]", "Now {P} Off: The {short}"],
    "sale": ["{TH}: {P} Off the {short}", "{TH} Deal: {P} Off[ + Free {GIFT_Wt}]", "{TH}: {P} Off"],
    "christmas": ["The Gift She'll Use Every Day", "Christmas Gift Sorted: The {short}", "Christmas Gift Sorted"],
    "gift": ["The Gift That Gets Used Every Day", "Gift Sorted: The {short}", "Gift Sorted"],
    "mothers day": ["For the Mum Who Carries Everything", "The Gift for Mum: The {short}", "A Gift for Mum"],
    "travel": ["Made for Travel Day", "Pack Smarter With the {short}", "Pack Smarter"],
    "feature": ["{t1} + {t2}", "Meet the {short}: {t1}", "The {short}: {t1}"],
    "colours": ["{N} Colours. Which One Is Yours?", "Pick Your Colour: {N} to Choose From", "Which Colour Are You?"],
    "review": ["\"{hq}\""],
    "gift_item": ["{Gift_t} Included"],
    "generic": ["Meet the {short}", "Shop the {short}"],
}
DESCRIPTIONS = {
    "sale": ["{TH}: {P} off", "{TH} deal: {P} off"],
    "offer": ["{P} off + free US shipping", "Now {P} off"],
    "gift_item": ["{Gift_s}", "{Gift_s} included"],
    "colours": ["{N} colours + free US shipping", "{N} colours to choose from"],
    "trust": ["1-year warranty + easy returns", "Free US shipping"],
    "generic": ["Free US shipping", "Shop the {short}", "Meet the {short}", "Tap the link to see it"],
}
# angle -> preferred hook types for the first line (hooks.json types; 'theme' = THEMES hooks, 'hero' = THEMES hero line)
HOOK_PREFS = {
    "offer": ["theme", "hero", "offer", "curiosity", "problem", "feature", "question", "gift", "travel", "POV"],
    "colours": ["colour", "theme", "question", "curiosity", "feature", "problem"],
    "compare": ["problem", "theme", "curiosity", "feature", "question"],
    "lifestyle": ["theme", "curiosity", "feature", "problem", "question", "hero"],
    "showcase": ["curiosity", "theme", "feature", "question", "problem"],
    "features": ["problem", "feature", "theme", "curiosity", "question"],
    "review": ["theme", "curiosity", "problem", "feature"],
    "winner": ["theme", "problem", "curiosity", "feature", "question", "hero"],
}
HEADLINE_PREFS = {   # (first headline families, second headline families); 'generic' is every list's last fallback
    "offer": (["themed", "offer"], ["feature", "gift_item", "offer"]),
    "review": (["review", "themed"], ["offer", "feature"]),
    "colours": (["colours", "themed"], ["offer", "gift_item"]),
    "default": (["themed", "feature"], ["offer", "gift_item", "feature"]),
}
ANGLES = {"hero": "offer", "promo": "offer", "bold": "offer", "review": "review", "reviews": "review",
          "colours": "colours", "compare": "compare", "split": "compare", "lifestyle": "lifestyle",
          "carousel": "lifestyle", "callouts": "features", "showcase": "showcase", "features": "features",
          "offer": "offer", "stars": "review", "checklist": "features"}


def rot(xs, k):
    return xs[k % len(xs):] + xs[:k % len(xs)] if xs else []


def num(seed, key):
    """A stable number for (seed, key): the same plan and seed always give the same copy."""
    return int(hashlib.md5(f"{seed}|{key}".encode()).hexdigest()[:8], 16)


def emojis(s):
    return len(EMOJI_RX.findall(s or ""))


def fill(t, v):
    s = mb.tpl(t, v)
    return re.sub(r"\s+([.,:!?])", r"\1", re.sub(r"[ \t]+", " ", s)).strip() if s else None


def title(s):
    """Headline case: every word capitalised but the small ones ('3 Ways to Wear', 'Free Matching Pouch Wallet')."""
    small = {"a", "an", "and", "or", "the", "of", "to", "in", "on", "for", "with", "+"}
    return " ".join(w.lower() if (i and w.lower() in small) else w[:1].upper() + w[1:]
                    for i, w in enumerate((s or "").split()))


# ---------------------------------------------------------------- product + facts
class Product:
    """One product's copy material: its data (make_batch), real offer, site facts, compliance context, hook pool."""

    def __init__(self, out, name, offer=None, theme="default"):
        files = mb.product_files(mb.products_dir())
        pk = mb.pick_product(name or "hobo bag", files) or "hobo bag"
        pr = mb.product(pk, files)
        self.pct, self.gift = compliance.parse_offer(offer) if offer is not None else mb.deal_of(pr["offer"])
        pr["offer"] = mb.builtin_offer(self.pct, self.gift, pr.get("deal") or {})
        import new_product
        pr["features"] = [f for f in pr["features"] if not (new_product.unbacked(f[0], self.pct, self.gift) or
                                                            new_product.unbacked(f[1], self.pct, self.gift))]
        self.pk, self.pr, self.theme = pk, pr, theme
        # a Drive-only new product: its folder's notes are the only source (no site page, no store-wide lines)
        self.drive = compliance.drive_only(pr)
        said = " ".join(str(x) for x in (pr.get("notes"), (pr.get("facts") or {}).get("description")) if x)
        self.ship, self.store = (not self.drive or bool(SHIP.search(said)),
                                 not self.drive or "libracases.com" in said.lower())
        self.facts = {} if self.drive else compliance.find_facts(out, pr.get("site"))
        self.ctx = compliance.context(pr, offer=(self.pct, self.gift), facts=self.facts)
        self.v = self.vars()
        self.hooks = self.hook_pool()

    def tpls(self, ts):
        """The templates this product may use: a Drive-only product says free US shipping / libracases.com only when its
        notes do ('Shop the X on libracases.com.' -> SITE_LINE); built-ins and site products: all of them."""
        out = []
        for t in ts:
            if not self.ship and SHIP.search(t):
                continue
            out.append(SITE_LINE if not self.store and "libracases.com" in t.lower() else t)
        return out

    def vars(self):
        v = dict(mb.offer_vars(self.pr))
        gift = self.gift or ""
        cols = self.ctx.get("colours") or []
        v.update(TH=SALE_NAME.get(self.theme, ""), Gift_t=title(gift), GIFT_Wt=title(v.get("GIFT_W", "").lower()),
                 Gift_s=gift[:1].upper() + gift[1:], N=str(len(cols)) if len(cols) > 1 else "",
                 colour_list=(", ".join(cols[:-1]) + " or " + cols[-1]) if len(cols) > 1 else "")
        return v

    def hook_pool(self):
        """[(type, line)]: the theme's hooks and hero line (THEMES, filled with this product's offer), the product's
        hooks.json / product-file lines, the generic ones, and the colour questions. All brand voice, all ours."""
        try:
            lib = json.load(open(os.path.join(HERE, "data", "hooks.json")))
        except (OSError, ValueError):
            lib = {}
        th = mb.THEMES.get(self.theme) or mb.THEMES["default"]
        tx = mb.offer_texts(self.pr, th)
        pool = [("theme", h) for h in tx["hooks"]] + [("hero", tx["hero"])]
        for h in ((lib.get("products") or {}).get(self.pk) or []) + list(self.pr.get("hooks") or []) + \
                [g for g in lib.get("generic") or [] if not g.get("per_feature")]:
            h = h if isinstance(h, dict) else dict(text=h, type="curiosity")
            t = fill(h["text"], self.v)
            if t:
                pool.append((h.get("type") or "curiosity", t))
        if self.v["N"]:
            pool += [("colour", t) for t, d in (lib.get("theme_hooks") or {}).items()
                     if isinstance(d, dict) and re.search(r"\bcolou?r\b", t, re.I)]
        seen, out = set(), []
        for typ, t in pool:
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append((typ, t))
        return out

    def feature_lines(self, order=None):
        """The product's spoken feature lines as copy sentences ('First, a hidden pocket ...' -> 'A hidden pocket ...'),
        in `order` (feature TAGs) first, then the rest."""
        feats = list(self.pr["features"])
        if order:
            rank = {t.upper(): i for i, t in enumerate(order)}
            feats.sort(key=lambda f: rank.get(f[1].upper(), 99))
        out = []
        for line, tag, *_ in feats:
            s = re.sub(r"^(?:first|and|inside|plus|also|then|finally|next)\b,?\s+", "", line.strip(), flags=re.I)
            sents = re.split(r"(?<=[.!?])\s+", s[:1].upper() + s[1:])
            s = sents[0] if len(sents) == 1 or len(sents[0]) >= 45 or len(sents[0]) + len(sents[1]) > 110 else \
                f"{sents[0]} {sents[1]}"
            out.append((tag, s if s.endswith((".", "!", "?")) else s + "."))
        return out


# ---------------------------------------------------------------- checks + picking
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is", "it", "it's", "this", "that", "your",
        "you", "+", "now"}
OFFERY = re.compile(r"%|half price|\bpercent\b", re.I)


def words(s):
    return [x for x in re.findall(r"[a-z0-9%']+", (s or "").lower()) if x not in STOP]


def overlap(a, b):
    """True when two lines of one text repeat each other: a shared word pair ('Black Friday', 'free wallet') or both
    stating the discount."""
    pairs = lambda s: set(zip(words(s), words(s)[1:]))  # noqa: E731
    return bool(pairs(a) & pairs(b)) or bool(OFFERY.search(a) and OFFERY.search(b))


def similar(a, b):
    """Near-duplicates ('Meet the Hobo Bag: Smart Compartments' ~ 'The Hobo Bag: Smart Compartments')."""
    x, y = set(words(a)), set(words(b))
    return bool(x and y) and (len(x & y) / len(x | y) >= 0.5 or x <= y or y <= x)


def opening(text):
    return EMOJI_RX.sub("", (text or "").split("\n", 1)[0]).replace("\ufe0f", "").strip().lower()


class Writer:
    """Picks, per field, the least-used candidate that passes the checks (compliance + Meta limits), the preferred list
    before the fallback one, so the ads of a batch differ; records notes and problems."""

    def __init__(self, seed):
        self.seed, self.uses, self.notes, self.problems = seed, {}, [], []

    def use(self, family, text):
        u = self.uses.setdefault(family, {})
        u[text] = u.get(text, 0) + 1

    def fresh(self, family, lines):
        """lines, the ones the batch has used least first (stable order otherwise)."""
        u = self.uses.get(family, {})
        return sorted(dict.fromkeys(x for x in lines if x), key=lambda x: u.get(x.lower(), 0))

    def why_not(self, text, field, prod, source="ours", raw=""):
        why = [f"{p['category']}: {p['term']}" for p in compliance.check(
            [dict(where=field, text=text, source=source, raw=raw)], ctx=prod.ctx)]
        lim = LIMITS.get("headline" if field.startswith("headline") else field)
        if lim and len(text) > lim:
            why.append(f"{len(text)} characters (max {lim})")
        if DASHES.search(text):
            why.append("em dash")
        if field in ("primary_text_1", "headline_1", "headline_2", "description", "hook_first_line") and emojis(text):
            why.append("emoji")
        if field == "primary_text_1" and text.count("\n") > 1:
            why.append("more than 2 lines")
        if field == "primary_text_2" and (emojis(text) > 2 or not 3 <= text.count("\n") + 1 <= 5):
            why.append("needs 3-5 lines and at most 2 emojis")
        return why

    def pick(self, field, preferred, prod, where, fallback=(), avoid=(), family=None):
        """The least-used passing candidate of `preferred` (in its order among equals), else of `fallback`; '' and a
        problem when none passes. avoid: texts it must not equal or nearly repeat (the ad's other fields)."""
        family = family or field
        tried = []
        for cands in (preferred, fallback):
            for c in self.fresh(family, [c for c in cands if not any(a and (c.lower() == a.lower() or similar(c, a))
                                                                     for a in avoid)]):
                why = self.why_not(c, field, prod)
                if not why:
                    self.use(family, c.lower())
                    return c
                tried.append(f"{c!r} ({'; '.join(why)})")
        self.problems.append(dict(where=where, field=field, why="no compliant line" + (": " + " | ".join(tried[:4])
                                                                                      if tried else "")))
        return ""


# ---------------------------------------------------------------- one copy set
def hook_lines(prod, w, angle, k, avoid=()):
    """Hook candidates for an angle (4+ words), type preference first, each type's lines rotated by the seed."""
    prefs = HOOK_PREFS.get(angle) or HOOK_PREFS["lifestyle"]
    by = {}
    for typ, t in prod.hooks:
        if len(t.split()) >= 4:
            by.setdefault(typ, []).append(t)
    out = []
    for typ in prefs + [t for t in by if t not in prefs]:
        if typ == "colour" and angle != "colours":
            continue
        out += rot(by.get(typ, []), num(w.seed, f"{typ}{k}") if typ not in ("theme", "hero") else w.seed - 1)
    return [h for h in out if h.lower() not in {a.lower() for a in avoid if a}]


def offer_lines(prod):
    v, th = prod.v, prod.theme
    if prod.pct:
        key = th if th in mb.SALE_THEMES else "gifting" if th in ("christmas", "gift", "mothers day") else "default"
        return [x for x in (fill(t, v) for t in prod.tpls(OFFER_LINE[key] + OFFER_LINE["default"])) if x]
    if prod.gift:
        return [x for x in (fill(t, v) for t in prod.tpls(OFFER_LINE["gift_only"])) if x]
    return [x for x in (fill(t, v) for t in prod.tpls(OFFER_LINE["none"])) if x] or \
        [fill("Meet the {short}.", v)]          # (a Drive-only product with one colour and no offer)


def cta_of(prod):
    return "Get Offer" if prod.theme in mb.SALE_THEMES and (prod.pct or prod.gift) else "Shop Now"


def quote_of(n):
    """The review's own sentence around its SPOKEN piece (make_batch), a <= 38 character version for a headline, and
    who wrote it ('Carol R.'; 'a customer' for one known by initials)."""
    revs = mb.reviews_by_n()
    if n not in revs:
        return None
    r = revs[n]
    who, piece = mb.spoken(n, revs)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s*", r["text"]) if s.strip()]
    sent = next((s for s in sents if mb.flat(piece) in mb.flat(s) or mb.flat(s) in mb.flat(piece)), sents[0] if sents else "")
    name = r["name"] if len(r["name"].split()[0].rstrip(".")) > 1 else "a customer"
    hq = sent.rstrip(".!")
    return dict(n=n, sentence=sent, short=hq if len(hq) <= 38 else "", who=name)


def raw_tags(prod, key, spec):
    """The product's feature TAGs a winner's RAW actually talks about (content words of the feature line / tag heard in the
    RAW words the version plays), most-mentioned first: a winner's copy never leads with a feature its video never shows
    or says ('Gold Side Zips' on RAW 94)."""
    ws = compliance.raw_words(key or "")
    if not ws:
        return []
    heard = " ".join(t for t, _, _ in compliance.raw_sentences(ws, compliance.remix_ranges(spec, compliance.winner_raw_dur(key))))
    stem = lambda x: re.sub(r"(?:ing|ed|es|s)$", "", x)  # noqa: E731
    said = {stem(x) for x in re.findall(r"[a-z]+", heard.lower()) if len(x) >= 4}
    said |= {"3"} if re.search(r"\b(?:three|3)\b", heard, re.I) else set()
    score = []

    def content(t):
        return {stem(x) for x in re.findall(r"[a-z0-9]+", t.lower()) if (len(x) >= 4 or x == "3") and
                x not in ("that", "with", "your", "keep", "everything", "first", "inside", "only", "looks", "right", "there")}
    for line, tag, *_ in prod.pr["features"]:
        th = len(content(tag) & said)             # the feature itself ('pocket', 'leather', '3 ways') must be said
        if th:
            score.append((-(2 * th + len(content(line) & said)), tag.upper()))
    return [t for _, t in sorted(score)]


def copy_set(prod, w, gid, angle, k, tag_order=None, review_n=None, avoid_hooks=(), only_tags=None):
    """One set of copy fields for a static or a project. only_tags: use only these features (a winner: what its RAW says)."""
    v, cta = prod.v, cta_of(prod)
    fam = ANGLES.get(angle, angle)
    q = quote_of(review_n) if review_n else None
    if fam == "review" and not q:
        q = next((x for x in (quote_of(n) for n in prod.pr.get("reviews") or []) if x and x["who"] != "a customer"), None)
    if q and compliance.check(q["sentence"], ctx=prod.ctx):
        q = None                                    # e.g. a review that mentions a gift this product doesn't have
    quote = f"\"{q['sentence']}\" - {q['who']}" if q and fam == "review" else ""
    feats = prod.feature_lines(tag_order)           # the video's / static's own features first, else seed-rotated
    feats = feats if tag_order else rot(feats, num(w.seed, f"feat{k}"))
    if only_tags:
        feats = [f for f in feats if f[0].upper() in only_tags] or feats
    name_w = set(re.findall(r"[a-z0-9]+", prod.v["short"].lower()))        # no 'The Slouchy Set: 3-Piece Set'
    tags = [title(mb.tcase(t, "title")) for t, _ in feats
            if not re.search(r"[+,]", t) and not set(re.findall(r"[a-z0-9]+", t.lower())) & name_w]
    v = dict(v, hq=(q or {}).get("short", ""), t1=tags[0] if tags else "", t2=tags[1] if len(tags) > 1 else "")
    hooks = hook_lines(prod, w, fam, k, avoid_hooks)

    # long primary text: hook (or the review), 1-2 feature lines, the offer line + emoji, the CTA line
    emoji = "🎁" if prod.gift else EMOJI.get(prod.theme, EMOJI["default"])
    th_emoji = EMOJI.get(prod.theme) if prod.theme != "default" and EMOJI.get(prod.theme) != emoji else ""
    lines = ([f"Choose from {v['colour_list']}."] if fam == "colours" and v["colour_list"] else []) + [s for _, s in feats]
    offers = rot(offer_lines(prod), num(w.seed, f"offer{k}"))
    ctas = (CTA_LINE["colours"] if fam == "colours" and v["N"] and cta == "Shop Now" else []) + \
        (CTA_LINE["her"] if prod.theme == "christmas" else CTA_LINE["mum"] if prod.theme == "mothers day" else []) + \
        rot(CTA_LINE[cta], num(w.seed, f"cta{k}"))
    firsts = ([quote] if quote else []) + w.fresh("opening", hooks)
    good, repeats = [], []                          # repeats: the opening says the offer line again (fallback only)
    for first in firsts[:8]:
        lead = first + (f" {th_emoji}" if th_emoji and first != quote else "")
        body = [x for x in lines if not overlap(first, x)][:2]          # feature lines that don't repeat the opening
        body = body[:1] if len(" ".join(body)) > 200 else body
        for o in offers:
            c = next((x for x in ctas if not overlap(o, x)), ctas[0])
            (repeats if overlap(first, o) else good).extend(
                ["\n".join([lead] + body + [f"{o} {emoji}", c]), "\n".join([lead] + body[:1] + [f"{o} {emoji}", c])])
    p2 = w.pick("primary_text_2", good, prod, gid, fallback=repeats)
    w.use("opening", opening(p2))

    # short primary text: another opening + the product with its offer (2 lines, no emoji)
    if prod.pct:
        shorts = [fill(t, v) for t in prod.tpls((SHORT_OFFER["sale"] if prod.theme in mb.SALE_THEMES else []) +
                                                SHORT_OFFER["default"])]
    else:
        shorts = [fill(t, v) for t in prod.tpls(SHORT_OFFER["gift_only" if prod.gift else "none"])]
    shorts = rot([s for s in shorts if s], num(w.seed, f"short{k}"))
    firsts1 = ([quote] if quote and opening(p2) != quote.lower() else []) + \
        w.fresh("opening", [h for h in hooks if h.lower() != opening(p2)])
    cands = [f"{a}\n{b}" for a in firsts1[:8] if len(a) <= 80 for b in shorts if not overlap(a, b)] + \
        [f"{a}\n{b}" for a in firsts1[:8] if len(a) <= 80 for b in shorts]
    p1 = w.pick("primary_text_1", cands, prod, gid)
    w.use("opening", opening(p1))

    # headlines: the angle's / theme's family first, then offer / feature / gift; never two near-duplicates
    hk = "review" if fam == "review" else "colours" if fam == "colours" else "offer" if fam == "offer" else "default"
    first_f, second_f = HEADLINE_PREFS[hk]

    def heads(fams):
        out = []
        for f in fams:
            if f == "themed":
                f = "sale" if prod.theme in mb.SALE_THEMES and prod.pct else prod.theme if prod.theme in HEADLINES else ""
            if f == "offer" and not prod.pct:
                continue
            out += rot([x for x in (fill(t, v) for t in HEADLINES.get(f, [])) if x], num(w.seed, f"h{f}{k}"))
        return out
    h1 = w.pick("headline_1", heads(first_f), prod, gid, fallback=heads(second_f + ["generic"]), family="headline")
    h2 = w.pick("headline_2", heads(second_f), prod, gid, fallback=heads(first_f + ["generic"]), avoid=[h1],
                family="headline")

    # description (never a repeat of a headline)
    dfam = (["sale"] if prod.theme in mb.SALE_THEMES and prod.pct else []) + \
        (["gift_item"] if prod.gift and prod.theme in ("christmas", "gift", "mothers day") else []) + \
        (["colours"] if fam == "colours" else []) + (["offer"] if prod.pct else []) + \
        rot(["gift_item", "colours", "trust"], num(w.seed, f"d{k}"))
    descs = [x for f in dfam for x in (fill(t, v) for t in prod.tpls(DESCRIPTIONS[f])) if x]
    d = w.pick("description", descs, prod, gid, fallback=[x for x in (fill(t, v) for t in prod.tpls(DESCRIPTIONS["generic"]))
                                                          if x], avoid=[h1, h2])
    return dict(primary_text_1=p1, primary_text_2=p2, headline_1=h1, headline_2=h2, description=d, cta=cta,
                cta_type=CTA_TYPE[cta])


def hook_variant(prod, w, gid, hook, p2, raw=""):
    """(hook_first_line, primary_text_2 opening with it) for one version, or ('', '') + a note."""
    text = (hook.get("hook_text") or "").strip()
    if not text:
        return "", ""
    line = f"\"{text}\"" if raw else text
    why = w.why_not(line, "hook_first_line", prod, source="raw_quote" if raw else "ours", raw=raw)
    if why:
        w.notes.append(f"{gid}: no hook_first_line ({'; '.join(why)}): use the shared primary texts")
        return "", ""
    rest = p2.split("\n")[1:] if p2 else []
    var = "\n".join([line] + rest)           # its lines are checked already (the hook above, the rest in p2): only the shape
    return line, (var if rest and emojis(var) <= 2 and 3 <= len(rest) + 1 <= 5 and not DASHES.search(var) else "")


# ---------------------------------------------------------------- a batch
def groups(p):
    """Video placement groups: the plan's projects, or (--hooks 1) one group per single video."""
    if p.get("projects"):
        return p["projects"]
    out = []
    for v in p.get("videos") or []:
        out.append(dict(id=v["id"], angle=v["name"].rpartition(f"_{v['id']}_")[2] or v.get("format") or "",
                        engine=v.get("engine", "storyboard"), format=v.get("format"), winner=v.get("winner"),
                        hooks=[dict(hook="", id=v["id"], name=v["name"], hook_text=v.get("hook_text") or v.get("hook") or "")]))
    return out


def spec_of(out, name):
    try:
        return json.load(open(os.path.join(out, name + ".json")))
    except (OSError, ValueError):
        return {}


def winner_product(out, x, spec, main, cache):
    """The product of a winner project: the plan's own (its offer), or the winner's bag with the % its video shows."""
    name = (x.get("winner") or {}).get("product")
    if not name or mb.pick_product(name, mb.product_files(mb.products_dir())) == main.pk:
        return main
    if name not in cache:
        m = re.match(r"\s*(\d+)\s*%", spec.get("offer_title") or "")
        base = Product(out, name, theme=main.theme)
        gift = base.gift if base.gift and re.search(r"pouch|wallet|purse|gift", spec.get("offer_sub") or "", re.I) else None
        cache[name] = Product(out, name, offer=(int(m.group(1)) if m else base.pct, gift), theme=main.theme)
    return cache[name]


def write(out, seed=1):
    out = os.path.abspath(out)
    p = json.load(open(os.path.join(out, "plan.json")))
    stp = os.path.join(out, "statics.json")
    statics = {s["name"]: s for s in (json.load(open(stp)).get("ads") or [])} if os.path.exists(stp) else {}
    main = Product(out, p.get("product_key") or p.get("product"), offer=p.get("offer"), theme=p.get("theme") or "default")
    w = Writer(seed)
    if p.get("theme") == "default" and p.get("theme_name") not in (None, "", "Evergreen"):
        w.notes.append(f"theme {p['theme_name']!r} is not built in: the copy uses the evergreen lines; refine it with the "
                       f"theme's words (true claims only) and re-run compliance.py")
    rows, js_statics, js_projects = [], [], []
    for k, name in enumerate(p.get("statics") or []):
        s = statics.get(name, {})
        sid = mb.static_id(name)
        angle = s.get("layout") or name.rsplit("_", 1)[-1]
        order = [f.upper() for f in s.get("features") or s.get("ticks") or []] or None     # the static's own tags first
        rn = s.get("review_n") or next((r if isinstance(r, int) else r.get("n") for r in s.get("reviews") or []
                                        if isinstance(r, int) or (isinstance(r, dict) and r.get("n"))), None)   # stars
        c = copy_set(main, w, sid, angle, k, tag_order=order, review_n=rn)
        rows.append(dict(ad_name=name, placement_group=sid, hook_first_line="", **c))
        js_statics.append(dict(id=sid, ad_name=name, angle=angle, **c))
    wcache = {}
    for k, x in enumerate(groups(p)):
        hs = x.get("hooks") or []
        spec = spec_of(out, hs[0]["name"]) if hs else {}
        eng = x.get("engine") or "storyboard"
        prod = winner_product(out, x, spec, main, wcache) if eng == "remix" else main
        angle = "winner" if eng == "remix" else x.get("angle") or x.get("format") or "features"
        tag_order = [o["text"] for o in spec.get("overlays") or [] if o.get("type") == "tag"] or None
        only = None
        if eng == "remix":            # the features the winner's RAW talks about, in that order
            only = raw_tags(prod, (x.get("winner") or {}).get("key"), spec) or None
            tag_order = only
            if not only:
                w.notes.append(f"{x['id']}: its RAW names none of {prod.pr['name']}'s feature lines: the copy uses them all")
        rev = next((o.get("n") for o in spec.get("overlays") or [] if o.get("type") == "review"), None)
        c = copy_set(prod, w, x["id"], angle, 100 + k, tag_order=tag_order,
                     review_n=rev if ANGLES.get(angle) == "review" else None,
                     avoid_hooks=[h.get("hook_text") for h in hs], only_tags=only)
        raw = compliance.raw_text((x.get("winner") or {}).get("key") or "") if eng == "remix" else ""
        versions = []
        for h in hs:
            first, var = hook_variant(prod, w, h.get("id") or x["id"], h, c["primary_text_2"], raw=raw)
            versions.append(dict(hook=h.get("hook"), id=h.get("id"), ad_name=h["name"], hook_text=h.get("hook_text"),
                                 hook_first_line=first, primary_text_2_hook=var))
            rows.append(dict(ad_name=h["name"], placement_group=x["id"], hook_first_line=first,
                             **{f: c[f] for f in COLUMNS if f in c}))
        js_projects.append(dict(id=x["id"], angle=x.get("angle"), engine=eng, product=prod.pr["name"],
                                winner=x.get("winner"), **c, versions=versions))
    csv_path, js_path = os.path.join(out, "ad_copy.csv"), os.path.join(out, "ad_copy.json")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    rep = dict(ok=not w.problems, created=datetime.date.today().isoformat(), product=main.pr["name"], theme=p.get("theme"),
               theme_name=p.get("theme_name"), offer=p.get("offer"), seed=seed, cta=cta_of(main), rows=len(rows),
               csv=csv_path, statics=js_statics, projects=js_projects, notes=w.notes, problems=w.problems)
    json.dump(rep, open(js_path, "w"), indent=1, ensure_ascii=False)
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="a planned batch (make_batch.py plan --out)")
    ap.add_argument("--seed", type=int, default=1, help="variation: another seed picks other hooks, features and lines")
    a = ap.parse_args()
    rep = write(a.out, a.seed)
    sample = [dict(id=x["id"], ad_name=x["ad_name"], **{k: x[k] for k in COLUMNS[2:8]}) for x in rep["statics"][:1]] + \
        [dict(id=x["id"], **{k: x[k] for k in COLUMNS[2:8]},
              hook_first_lines={v["hook"] or v["id"]: v["hook_first_line"] for v in x["versions"]}) for x in rep["projects"][:1]]
    print(json.dumps(dict(ok=rep["ok"], csv=rep["csv"], json=os.path.join(os.path.dirname(rep["csv"]), "ad_copy.json"),
                          rows=rep["rows"], statics=len(rep["statics"]), projects=len(rep["projects"]), cta=rep["cta"],
                          notes=rep["notes"], problems=rep["problems"], samples=sample), indent=1, ensure_ascii=False))
    sys.exit(0 if rep["ok"] else 1)


if __name__ == "__main__":
    main()

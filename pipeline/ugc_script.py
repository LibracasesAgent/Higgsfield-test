#!/usr/bin/env python3
"""Script engine of the ugc storyboard format: a 55-80 s voiceover in the 'you' voice that sounds like a person talking
fast to the viewer (owner's reference ads: 187-220 wpm, a specific hook in the first 3 s, numbered chapters, problem ->
fix pairs, proof, the offer last), made from a product's own features and offer. No first person (I / my / me) except
inside a verbatim review quote; only claims the product's facts back (compliance.check passes on every text).

  python3 pipeline/ugc_script.py "Hobo Bag" [--n 5] [--seed 1] [--hooks 4] [--lint] [--json] [--products-dir DIR]

Python: scripts(pr, n=5, seed=1, hooks=4, voice="you") -> [script, ...]   pr = make_batch.product() (plus honest() and
  the resolved offer, as plan has them). One script per project i: angle cycle n_things, demo, stop_x, travel, value
  (rotated by seed; an angle the product's facts can't carry is skipped); [] when the product has no feature lines.
  script = {"id": "U01", "index": 0, "angle", "voice": "you", "product": key,
    "hook": {"text", "type" (promise|superlative|question|problem|price), "label" (<= 3 words, UPPERCASE), "feature" (TAG|None)},
    "alt_hooks": [hook, ...]  (max(3, hooks) + 1: other types than the main hook first, all different: H2-H4 ...; each text
        <= 14 words, at most one content word shared with the main hook; no hook text repeats in the other scripts),
    "chapters": [{"id": "c1", "text" (1-3 sentences, <= 45 words, ONE voice take), "number" (1.. in n_things, else None:
        printed before the first caption as '1.', never written in the text), "tag" (on-screen TAG of the feature | None),
        "feature" (same), "shot_kw" [2-4 words for the shot planner: clip_index.json notes vocabulary], "keywords"
        [1-3 caption highlights], "kind" point|proof|reviews|objection|offer, ("reviews": [review numbers] on a reviews
        chapter: the cards to show, each <= 3 s)}, ...],
    "offer": {"chapter": "c6", "word": "50"} | None   (the closing chapter says '<fifty> percent off'; word = the % or 'free'),
    "words": int (hook + chapters), "est_seconds": words / (2.75 * 1.12)  (2.75 w/s = espeak / TTS tempo, x1.12 the
        renderer's speed-up; ~1 s of pads on top; a 200 wpm voice does words / 3.3),
    "claims": [str],
    "numbers": [count words the text says that no fact backs ('Four things'): pass as allowed_numbers to compliance.check]}
  tts_items(script, hook=None) -> [(id, text)] hook + chapters; ctx_texts(script) -> [(where, text)] every text a viewer
  hears or reads; lint(script, pr) -> [problem str] (first person, lengths, hook rules, compliance); PROJECT_TYPE maps the
  hook types to projects.TYPES. Data: pipeline/data/ugc_arcs.json (lexicon, frames, offer / review pieces) and
  pipeline/data/ugc_hobo.json (five hand-written Hobo Bag scripts, used before the engine).
"""
import argparse
import collections
import itertools
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
VPS = 2.75 * 1.12
ANGLES = ("day", "n_things", "demo", "stop_x", "travel", "value")      # (day first: a batch of 5 always has the story)
HOOK_TYPES = ("promise", "superlative", "question", "problem", "price")
PROJECT_TYPE = dict(promise="curiosity", superlative="curiosity", question="question", problem="problem", price="offer")
MAX_HOOK_WORDS, MAX_CHAPTER_WORDS, MAX_SENTENCES = 14, 45, 3
NUMW = "zero one two three four five six seven eight nine ten".split()
FIRST = re.compile(r"\b(?:I|I'm|I've|I'll|I'd|[Mm]e|[Mm]y|[Mm]ine|[Mm]yself|[Ww]e|[Ww]e're|[Ww]e've|[Ll]et's|[Uu]s|[Oo]urs?)\b")   # (brand voice:
#                                                                                      no 'we' either; 'US' the country is fine)
SHIPPING = re.compile(r"free\s+(?:(us|u\.s\.)\s+)?(?:shipping|delivery)", re.I)
OPTIONAL = {"ship", "ship_s"}
STOP = set("the a an and or of to in on for with your you you'll you're it's its this that these those is are was be been "
           "have has had do does did not no yes can could will would should might may must just only more most very much "
           "too than then so if as at by from up out over into about what what's when where which who how why here here's there bag "
           "bags don't it's that's".split())
VERB_S = re.compile(r"^(?:fits|holds|keeps|has|gives|comes|sits|stays|looks|goes|features|lets|makes|blocks|loops|snaps|"
                    r"closes|opens|adds|offers|turns|folds|stands|carries|works|feels|softens|packs)\b", re.I)
CONNECT = re.compile(r"^(?:(?:and|plus|also|then|finally|lastly|first(?:ly)?|second(?:ly)?|third(?:ly)?|next)\b,?\s+)+", re.I)
STOPW = set("that which with for of without in on to so and but from against around at by as".split())    # end of a noun phrase
VERBS = set("keeps holds fits gives lets blocks makes sits stays snaps loops opens closes looks goes comes has is are softens "
            "protects secures features offers adds turns folds stands carries works feels packs".split())
PRODUCT_NOUNS = set("bag tote crossbody purse satchel clutch backpack handbag shoulder-bag hobo set".split())
MASS = set("room leather stitching storage space comfort style protection security hardware material fabric canvas suede "
           "padding capacity".split())
ITEMS = re.compile(r"\b(passport|keys|phone|wallet|cards|table|chair|shoulder|crossbody|lipstick|laptop|coffee|zip|lining)\b", re.I)
REVIEWS = False       # ugc videos carry no "<name> says: ..." review chapter and no review cards (media buyer 2026-10-21: "I don't think it is
#                       good as objection handling before the CTA"): the proof chapter is the recap, the objection a fact. Statics keep quotes.
PRICE_PIECE = "looks expensive but price was so nice"     # review 8 (Beverly): the answer to a price doubt


class Used(collections.Counter):
    """Counts of the lines said so far in one scripts() call (a line is said once while any other fits), and the review quotes of
    each finished script (no two scripts share two quotes)."""
    sets = ()

    def fork(self):
        u = Used(self)
        u.sets = list(self.sets)
        return u


_D = {}


def data(name):
    if name not in _D:
        _D[name] = json.load(open(os.path.join(HERE, "data", name), encoding="utf-8"))
    return _D[name]


def mb():
    import make_batch               # offer_vars, deal_of, reviews ... (lazy: make_batch imports this module)
    return make_batch


def comp():
    import compliance
    return compliance


def nwords(t):
    return len(t.split())


def sents(t):
    """Sentences; 'Carol says: best bag ...' is one."""
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def flat(t):
    return " ".join(re.findall(r"[a-z0-9']+", t.lower()))


def cap(t):
    return t[:1].upper() + t[1:]


def lowerfirst(t, keep=()):
    w = re.match(r"[\w'+-]+", t)
    return t if not w or (w.group(0).isupper() and len(w.group(0)) > 1) or w.group(0).lower() in keep else t[:1].lower() + t[1:]


def val(k, v):
    """{key} of a template: v[key]; {Price_sp} = v['price_sp'] capitalised."""
    return v.get(k) if k in v else (cap(v.get(k.lower()) or "") if k.lower() in v else None)


def fill(t, v):
    """Fill a template: a [..] part drops out when a value in it is empty, a line with an empty value outside [..] is None
    (ship / ship_s may be empty)."""
    def has(k):
        return k in OPTIONAL or bool(val(k, v))
    t = re.sub(r"\[([^\]]*)\]", lambda m: m.group(1) if all(has(k) for k in re.findall(r"{(\w+)}", m.group(1))) else "", t)
    ks = re.findall(r"{(\w+)}", t)
    if not all(has(k) for k in ks):
        return None
    return cap(re.sub(r"\s+", " ", t.format(**{k: val(k, v) or "" for k in ks})).strip())


def money(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def price_str(x):
    return f"${x:.2f}" if x != int(x) else f"${int(x)}"


# ---------------------------------------------------------------- context: what a product's facts back
def noun_of(short):
    return {"set": "set", "tote": "tote", "crossbody": "crossbody", "purse": "purse", "backpack": "backpack",
            "clutch": "clutch", "satchel": "satchel"}.get(short.lower().split()[-1], "bag")


def clean_line(line):
    """A feature line as one standalone spoken sentence: no leading 'And' / 'First,' ..., a capital, a full stop."""
    s = CONNECT.sub("", re.sub(r"\s+", " ", line.strip()))
    return cap(s) + ("" if s[-1:] in ".!?" else ".")


def context(pr):
    """What the script may say about a product: features (a concept each; a line's 'needs' are tested on the client's line alone,
    never on our tag), offer values, backed facts, reviews."""
    import new_product
    M, C, arcs = mb(), comp(), data("ugc_arcs.json")
    builtin = pr.get("source") == "built-in"
    pct, gift = M.deal_of(pr.get("offer") or {})
    ov = M.offer_vars(pr)
    f = pr.get("facts") or {}
    notes = f.get("notes") or pr.get("notes") or ""
    price, was = money(f.get("price")), money(f.get("compare_at"))
    priced = bool(price and was and was >= price * 1.1 and not builtin and not pr.get("site") and f.get("price_source") in (None, "notes"))
    store = not C.drive_only(pr)        # built-ins (and site products): PLAYBOOK's store-wide 'free US shipping', warranty, returns
    m = SHIPPING.search(notes)
    neg = bool(m and re.search(r"\b(?:no|not|without)\b[^.\n]{0,20}$", notes[max(0, m.start() - 30):m.start()], re.I))
    ship = "US" if store else ("US" if m.group(1) else "-") if m and not neg else ""     # "-": shipping, no region
    src = (" | ".join(C.playbook_row(pr["name"], C.playbook()[0])) if store else "") + " " + notes
    mw = re.search(r"(\d+|\w+)[- ]years? warranty", src, re.I)
    mr = None if (C._CAMPAIGN[0] or {}).get("final_sale") else re.search(r"\b(easy|free) returns?\b", src, re.I)   # (final sale: none)
    short = pr["short"]
    V = dict(short=short, noun=noun_of(short), pct=pct, gift=gift or "", P=ov["P"], off_sp=ov["off_sp"], price_sp=ov["price_sp"],
             gift_sp=ov["gift_sp"], price=price_str(price) if priced else "", was=price_str(was) if priced else "",
             warranty=(f"{new_product.say(int(mw.group(1))) if mw.group(1).isdigit() else mw.group(1).lower()}-year warranty") if mw else "",
             returns=f"{mr.group(1).lower()} returns" if mr else "", price_label="HALF PRICE" if pct == 50 else f"{ov['P']} OFF" if pct else "")
    ctx = dict(pr=pr, V=V, M=M, C=C, arcs=arcs, builtin=builtin, pct=pct, gift=gift, priced=priced, ship=ship,
               colours=[c for c in (f.get("colours") or []) if c] if not builtin else [], revs=M.reviews_by_n(),
               bi=(arcs["builtin"].get(pr.get("key")) or {}) if builtin else {}, np=new_product)
    ctx["concepts"] = {c["id"]: c for c in arcs["concepts"]}
    ctx["feats"] = feats(ctx)
    ctx["deal"] = bool(pct or gift or priced)
    ctx["rich"] = len(ctx["feats"]) >= 5            # (fewer feature lines: a thin product, a shorter script)
    return ctx


def feats(ctx):
    out = []
    for f in ctx["pr"].get("features") or []:
        line, tag = clean_line(f[0]), f[1]
        text = f"{tag} {line}".lower()
        b = ctx["bi"].get(tag)
        c = ctx["concepts"][b["concept"]] if b else next(c for c in ctx["arcs"]["concepts"] if re.search(c["match"], text))
        out.append(dict(line=line, line_l=line.lower(), tag=tag, text=text, c=c, fix=(b or {}).get("fix"), ov={k: v for k, v in (b or {}).items() if k in LEAD_KEYS}))
    return out


# ---------------------------------------------------------------- choosing lines
def fits(o, text):
    if isinstance(o, str):
        return True
    return (not o.get("needs") or bool(re.search(o["needs"], text))) and not (o.get("not") and re.search(o["not"], text))


def choose(opts, text, rng, used, avoid="", strict=True, first=0.0, fresh=False):
    """A line that fits `text` (the client's feature line) and shares at most one content word with `avoid`: the least used
    so far (across the scripts of one call), at random among those. None when nothing fits (strict False: the overlap
    rule is dropped before giving up; fresh: only a line no script has said yet)."""
    c = [o if isinstance(o, str) else o["t"] for o in opts if fits(o, text)]
    base, bg = cw(avoid), bigrams(avoid)
    pick = [x for x in c if len(cw(x) & base) < 2 and not bigrams(x) & bg] or ([] if strict else c)
    pick = [x for x in pick if not used[x]] if fresh else pick
    if not pick:
        return None
    m = min(used[x] for x in pick)
    low = [x for x in pick if used[x] == m]
    x = low[0] if rng.random() < first and pick[0] in low else rng.choice(low)       # first: favour the plain wording
    used[x] += 1
    return x


def forms(L, keep=(), short=""):
    """Wordings of one feature line (a spoken fragment or sentence from the client's notes) as 'you' copy, plain first: the
    line itself (split at a colon), 'It fits ...' for a verb-first line, 'You get / It has / There's <a> ...' for a noun phrase
    (the article from its head noun: plural or mass nouns get none), 'A / This <subject> keeps ...' for a sentence."""
    body = L.rstrip(".!?")
    lc = lowerfirst(body, keep)
    out = []
    mm = re.match(r"([^:;]{12,}?)[:;]\s+(.{12,})$", body)
    if mm:
        out.append(f"{cap(mm.group(1))}. {cap(mm.group(2))}.")
    out.append(L)
    if VERB_S.match(L):
        return out + [f"It {lc}.", f"Yes, it {lc}.", f"And it {lc}."] + ([f"This {noun_of(short)} {lc}."] if short else [])
    toks = body.split()
    head, verb = [], False
    for k, t in enumerate(toks):
        w = t.strip(",:;.").lower()
        if k and w in STOPW:
            break
        if k and w in VERBS:
            verb = True
            break
        head.append(w)
        if t.endswith((",", ":", ";")) and len(head) >= 2:
            break
    h = head[-1] if head else ""
    plural = h.endswith("s") and not h.endswith(("ss", "us", "is", "ous")) and h not in MASS
    mass = h in MASS or (h.endswith("ing") and h not in ("lining", "ring", "string"))
    if toks[0].lower() in ("a", "an", "the", "your", "this", "these", "our", "every", "each") or len(head) < 1:
        return out
    a_ = "" if plural or mass else ("an " if toks[0][:1].lower() in "aeiou" or (toks[0].isupper() and toks[0][:1] in "AEFHILMNORSX") else "a ")
    if verb:
        return out + ([] if plural else [f"{cap(a_)}{lc}.", f"This {lc}.", f"The {lc}."])
    lc = re.sub(r"\s*[:;]\s*", ", ", lc)
    if h in PRODUCT_NOUNS:          # the line describes the bag itself ('Sleek, under-arm bag for ...'): never 'It has a ... bag'
        return out + [f"This is {a_}{lc}.", f"It's {a_}{lc}.", f"You get {a_}{lc}.", f"Picture {a_}{lc}.", f"Say hello to {a_}{lc}."]
    return out + [f"You get {a_}{lc}.", f"It has {a_}{lc}.", ("There are " if plural else "There's ") + f"{a_}{lc}.",
                  f"Picture {a_}{lc}.", f"Say hello to {a_}{lc}.", f"Count on {a_}{lc}."]


def fix_line(ctx, f, rng, used, avoid="", lead=""):
    """The feature as a standalone sentence: a built-in bag's own wordings, else forms() of its line: another wording each time
    the feature comes up in a batch (the plain one first)."""
    if f["fix"]:
        return choose(f["fix"], "", rng, used, avoid, strict=False)
    return choose(forms(f["line"], {w.lower() for w in ctx["pr"]["short"].split()}, ctx["pr"]["short"]), "", rng, used, avoid, strict=False,
                  first=0.95 if lead and not lead.endswith("?") and not lead.startswith(("Stop", "You ")) else 0.7)


def shot_kw(c, f):
    kw = list(c["shot_kw"])
    for w in ITEMS.findall(f["line"]):
        if w.lower() not in " ".join(kw) and len(kw) < 4:
            kw.append(w.lower())
    return kw[:4]


def key_words(c, f, text):
    low = text.lower()
    kws = [k for k in c["keywords"] if k.lower() in low]
    return (kws or [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]+", f["tag"]) if w.lower() in low and len(w) > 3][:2])[:3]


def chapter(text, kind, f=None, number=None, c=None, kw=None, keywords=None):
    return dict(id="c?", text=text, number=number, tag=f["tag"] if f else None, feature=f["tag"] if f else None,
                shot_kw=kw or (shot_kw(c, f) if f else []),
                keywords=keywords if keywords is not None else (key_words(c, f, text) if f else []), kind=kind)


LEAD_KEYS = ("headline", "problem", "stop", "demo", "moment", "after")      # a built-in tag may replace the concept's lines
MODES = {"headline": ("headline", "problem", "stop"), "problem": ("problem", "headline", "stop"), "stop": ("stop", "problem", "headline"),
         "demo": ("demo", "problem", "headline"), "moment": ("moment", "problem", "headline"), "fix": ()}


def pain_lines(ctx, c, kind):
    """The concept's pains in one frame family (problem / stop / headline) as options {t, needs, not}."""
    F, out = ctx["arcs"]["frames"], []
    for pn in c.get("pains") or []:
        if pn.get("ns") and kind != "problem":
            continue
        frames = [F["problem"][k] for k in pn.get("f") or F["default"] + (F["have_to"] if pn.get("ht") else [])
                  if ctx["builtin"] or k != "never"] if kind == "problem" else F[kind]     # ('what if you never had to ...' promises the fix)
        for fr in frames:
            if ("{g}" in fr or "{G}" in fr) and not pn.get("g"):
                continue
            out.append({"t": fr.format(q=pn["q"], g=pn.get("g", ""), G=cap(pn.get("g", ""))), "needs": pn.get("needs"), "not": pn.get("not")})
    return out


def options(ctx, c, mode):
    """Candidate lines of a concept for a lead mode: its own written lines, then its pains in that frame family."""
    return list(c.get(mode) or []) + (pain_lines(ctx, c, mode) if mode in ("problem", "stop", "headline") else [])


def point(ctx, f, rng, used, mode, number=None, kick=1.0):
    """One chapter on a feature: [a lead: a problem question / 'You stop ...' / 'Stop ...' / 'Watch this.' / a scene] + the
    feature as a fix + [a moment or payoff]: 1-3 sentences, <= 45 words. A lead or payoff no script of the call has said yet
    (the concept's own first, then the general ones); a line never repeats another's words."""
    c = dict(ctx["concepts"][f["c"]["id"]], **f["ov"])
    G = ctx["arcs"]["generic"]

    modes = [m for m in MODES[mode] if ctx["builtin"] or m not in ("headline", "stop")]    # a product file's notes carry no 'you stop X':
    #                                         its lead is a question about the situation or a scene, the fix after it is the notes' own line

    def lead_for(avoid=""):
        for m in modes:
            for opts in (options(ctx, c, m), G.get(m) or []):
                x = choose(opts, f["line_l"], rng, used, avoid, fresh=True)
                if x:
                    return x
        return None
    lead = lead_for()
    fx = fix_line(ctx, f, rng, used, lead or "", lead or "")
    if lead and (len(cw(lead) & cw(fx)) >= 2 or bigrams(lead) & bigrams(fx)):     # every wording of the fix repeats the lead
        lead = lead_for(fx)
    aft = None
    if rng.random() < kick:
        for opts in (c.get("after") or [], G["after"]):
            aft = choose(opts, f["line_l"], rng, used, f"{lead or ''} {fx}", fresh=True)
            if aft:
                break
    parts = [p for p in (lead, fx, aft) if p]
    if not lead and aft and sum(len(sents(p)) for p in parts) < MAX_SENTENCES:      # no fresh lead left: a second payoff
        aft2 = next((x for x in (choose(o, f["line_l"], rng, used, f"{fx} {aft}", fresh=True) for o in (c.get("after") or [], G["after"])) if x), None)
        parts += [aft2] if aft2 else []
    while len(parts) > 1 and (nwords(" ".join(parts)) > MAX_CHAPTER_WORDS or sum(len(sents(p)) for p in parts) > MAX_SENTENCES):
        parts.pop(0 if len(parts) == 2 and lead else -1)       # the payoff goes first, then the lead
    return chapter(" ".join(parts), "point", f, number, c)


# ---------------------------------------------------------------- tail chapters
def first_name(r):
    w = r["name"].split()[0].rstrip(".")
    return "One customer" if len(w) < 2 else w


def review_ok(ctx, n, piece):
    r = ctx["revs"].get(n)
    return bool(r and piece and flat(piece) in flat(r["text"]))


def reviews_chapter(ctx, rng, used, prefer=(), picks=None, intro=None, count=2):
    """'<intro> Carol says: <verbatim piece>. Jenny says: <piece>.' from the product's own reviews (None without any);
    picks [(review n, piece)] fixes them (hand-written scripts). Else the `count` quotes (one per review) that share the fewest
    quotes with an earlier script, then the least used, the strongest first."""
    A = ctx["arcs"]["reviews"]
    if picks is None:
        ok = [(n, p) for n in ctx["pr"].get("reviews") or [] for p in A["pieces"].get(str(n)) or [] if review_ok(ctx, n, p)]
        by = {}
        for n, p in ok:
            by.setdefault(n, []).append(p)
        best = None
        for ns in itertools.combinations(by, min(count, len(by))):
            for ps in itertools.product(*(by[n] for n in ns)):
                key = (max([len(set(ps) & st) for st in used.sets] + [0]), sum(n not in prefer for n in ns), sum(used[f"piece {p}"] for p in ps),
                       sum(by[n].index(p) for n, p in zip(ns, ps)), rng.random())
                if best is None or key < best[0]:
                    best = (key, list(zip(ns, ps)))
        picks = best[1] if best else []
        for n, p in picks:
            used[f"piece {p}"] += 1
        if picks:
            used.sets = list(used.sets) + [set(p for _, p in picks)]
    if not picks:
        return None
    intro = intro or (choose(A["intro"], "", rng, used) if len(picks) < 3 else "")          # (a third voice: no intro, 3 sentences)
    c = chapter(" ".join(([intro] if intro else []) + [f"{first_name(ctx['revs'][n])} says: {p}." for n, p in picks]), "reviews",
                kw=["hands", "table", "hanging"], keywords=[])
    c["reviews"] = [n for n, _ in picks]
    return c


def recap_chapter(ctx, sel, rng, used):
    """'Quick recap: <tag>, <tag> and <tag>. That's the <short>.' from the features' own tags (a built-in tag that is no noun phrase
    has a 'recap' wording in ugc_arcs.json; a product file's odd two-word tag is left out)."""
    M = ctx["M"]
    tags = [(ctx["bi"].get(f["tag"]) or {}).get("recap") or f["tag"] for f in sel
            if ctx["builtin"] or ctx["np"].known_tag(f["tag"])]
    if len(tags) < 2:
        return None
    T = ", ".join([M.tcase(t, "sentence") for t in tags[:1]] + [M.tcase(t, "lower") for t in tags[1:3]])
    t = fill(choose(ctx["arcs"]["recap"], "", rng, used), dict(ctx["V"], tags=T[:1].lower() + T[1:], Tags=T))
    return chapter(t, "proof", kw=["hero", "hands", "hanging"], keywords=[]) if t else None


def colours_chapter(ctx, rng, used):
    cs = ctx["colours"]
    if len(cs) < 2:
        return None
    t = fill(choose(ctx["arcs"]["colours"], "", rng, used), dict(ctx["V"], list=", ".join(cs[:-1]) + " and " + cs[-1]))
    return chapter(t, "point", f=None, kw=["colour", "lineup", "hero"], keywords=[c.lower() for c in cs[:2]]) if t else None


def objection_chapter(ctx, rng, used, reviews_used=()):
    """The doubt a buyer has, answered with a fact the product backs: warranty / returns (built-in bags), the price against a
    review ('looks expensive but price was so nice'), or the notes' price and was price. (None: nothing true to say.)"""
    O, V = ctx["arcs"]["objection"], ctx["V"]
    c = [fill(t, V) for t in (O["warranty"] if V["warranty"] else O["returns"] if V["returns"] else [])]
    if not c and REVIEWS and ctx["pct"] and 8 in (ctx["pr"].get("reviews") or []) and 8 not in reviews_used and review_ok(ctx, 8, PRICE_PIECE) \
            and not used[f"piece {PRICE_PIECE}"]:
        c = list(O["price"])
    if not c and ctx["priced"]:
        c = [fill(t, V) for t in O["price_fact"]]
    if not c and ctx["ship"]:
        x = "" if ctx["ship"] == "-" else ctx["ship"]
        c = [cap(re.sub(r"\s+", " ", t.format(x=x)).strip()) for t in O["shipping"]]
    t = choose([x for x in c if x], "", rng, used, fresh=True)
    if t and PRICE_PIECE in t:
        used[f"piece {PRICE_PIECE}"] += 1
        used.sets = list(used.sets[:-1]) + [set(used.sets[-1]) | {PRICE_PIECE}] if used.sets else [{PRICE_PIECE}]
    return chapter(t, "objection", kw=["hands", "hanging", "details"],
                   keywords=[w for w in ("warranty", "returns") if w in t]) if t else None


def ship_phrase(ctx, rng, used):
    """'Free US shipping too.' (a variant per script; '' when the product's facts don't say it)."""
    if not ctx["ship"]:
        return ""
    x = "" if ctx["ship"] == "-" else ctx["ship"]
    return choose([cap(re.sub(r"\s+", " ", t.format(x=x)).strip()) for t in ctx["arcs"]["offer"]["ship"] if x or "the {x}" not in t], "", rng, used)


def offer_chapter(ctx, rng, used, ship=None, price=True):
    V, O = ctx["V"], ctx["arcs"]["offer"]
    kind = "priced" if ctx["priced"] and ctx["pct"] and price else "full" if ctx["pct"] and ctx["gift"] else "pct" if ctx["pct"] else \
        "gift" if ctx["gift"] else "none"
    ship = ship_phrase(ctx, rng, used) if ship is None else ship
    v = dict(V, ship=(" " + ship) if ship else "", ship_s=(ship + " ") if ship else "")
    tpl = choose([f for f in O[kind] if fill(f, v)], "", rng, used, fresh=True) or choose([f for f in O[kind] if fill(f, v)], "", rng, used)
    t = fill(tpl, v)
    return chapter(t, "offer", kw=["hero", "hanging", "shoulder"], keywords=([V["P"]] if ctx["pct"] else []) + (["free"] if ctx["gift"] or ship else []))


# ---------------------------------------------------------------- hooks
def bigrams(text):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return set(zip(w, w[1:]))


def cw(text, extra=()):
    return {w for w in re.findall(r"[a-z][a-z'-]{3,}", text.lower()) if w not in STOP and w not in extra}


def H(text, typ, label, feature=None):
    return dict(text=text, type=typ, label=label, feature=feature)


def hook_ok(h):
    return bool(h["text"]) and nwords(h["text"]) <= MAX_HOOK_WORDS and len(h["label"].split()) <= 3 and h["label"] == h["label"].upper()


def hook_cands(ctx, angle, f1, sel, K):
    """{type: [hook]}: every hook that fits this script. A hook about the first chapter's feature is the problem that chapter
    fixes (the chapter never repeats it); the others are about the whole bag, so every version flows into chapter 1."""
    A, V = ctx["arcs"]["hooks"], ctx["V"]
    out = {t: [] for t in HOOK_TYPES}
    nv = dict(V, Nw=cap(NUMW[min(K, 10)]), nw=NUMW[min(K, 10)])
    for t in A["promise"].get(angle, []) + A["promise"]["any"]:
        s = fill(t, nv)
        if s:                      # ang: the angle's own promise ('Five things ...', 'Watch ...'): the main hook is one of these
            out["promise"].append(dict(H(s, "promise", f"{K} THINGS" if "{Nw}" in t or "{nw}" in t else "WATCH THIS" if angle == "demo" else "ONE DAY" if angle == "day" else "THE DETAILS"),
                                       ang=t in A["promise"].get(angle, [])))
    for adj in dict.fromkeys([f["c"]["adj"] for f in sel] + ["practical", "useful"]):
        out["superlative"] += [H(fill(t, dict(V, adj=adj)), "superlative", f"MOST {adj.upper()}") for t in A["superlative"]]
    qs = [(t, None, None) for t in A["question"]]
    qs = ([(t, None, "TRAVEL DAY") for t in A["travel_question"]] + qs) if angle == "travel" else qs
    qs += [(t if isinstance(t, str) else t["t"], f1["tag"], None) for t in f1["c"].get("hook_q") or [] if fits(t, f1["line_l"])]
    for t, ft, lab in qs:
        out["question"].append(dict(H(t, "question", lab or ["QUICK QUESTION", "BE HONEST", "YOUR ANSWER?"][len(t) % 3], ft), spec=bool(ft or lab)))
    for t in A["problem"]:
        out["problem"].append(H(t, "problem", ["SOUND FAMILIAR?", "BEEN THERE?", "STOP SCROLLING"][len(t) % 3]))
    for t in f1["c"].get("hook_p") or []:
        if fits(t, f1["line_l"]):
            out["problem"].append(dict(H(t if isinstance(t, str) else t["t"], "problem", f1["c"]["label_p"], f1["tag"]), spec=True))
    for h in ctx["bi"].get("_hooks") or []:
        out[h["type"]].append(dict(h, spec=True))
    for h in ctx["pr"].get("hooks") or []:           # a product file's own hook lines (pipeline/data/products/README.md)
        h = h if isinstance(h, dict) else {"text": h}
        t = fill(h.get("text") or "", V)
        lab = next((fill(x, V) for x in h.get("labels") or [] if fill(x, V)), "")
        typ = {"problem": "problem", "question": "question", "offer": "price"}.get(h.get("type"), "promise")
        if t and (typ != "price" or ctx["deal"]):
            out[typ].append(dict(H(t, typ, (lab or "THE DETAILS").upper(), h.get("feature")), spec=True))
    for t in A["price"] if ctx["deal"] else []:
        s = fill(t, V)
        if s:
            out["price"].append(H(s, "price", "REAL PRICE" if "{price}" in t else "HALF PRICE" if ctx["pct"] == 50 else f"{V['P']} OFF" if ctx["pct"] else "WHAT YOU GET"))
    return {t: [h for h in hs if hook_ok(h)] for t, hs in out.items()}


def pick_hooks(ctx, cands, order, n_alt, rng, taken, main_type, main=None):
    """The main hook (of main_type unless given) + n_alt alts: other types first, all different (a second round repeats
    types); none repeats a word of the main hook beyond one; texts not in `taken` (the other scripts' hooks) while any is left."""
    extra = set(re.findall(r"[a-z0-9]+", ctx["pr"]["short"].lower()))
    chosen = []

    def take(t, base):
        have = {c["text"] for c in chosen}
        pool = [h for h in cands.get(t, []) if h["text"] not in have and len(cw(h["text"], extra) & base) <= 1]
        pool = [h for h in pool if h["text"] not in taken] or pool
        spec = [h for h in pool if h.get("spec")]
        return rng.choice(spec if spec and rng.random() < 0.8 else pool) if pool else None
    main = main or take(main_type, set()) or next(h for t in HOOK_TYPES for h in cands[t])
    chosen.append(main)
    base = cw(main["text"], extra)
    types = [t for t in order if t != main["type"]]
    for t in types + types + [main["type"]]:
        h = take(t, base) if len(chosen) <= n_alt else None
        if h:
            chosen.append(h)
    taken.update(h["text"] for h in chosen)
    chosen = [{k: v for k, v in h.items() if k not in ("spec", "ang")} for h in chosen]
    return chosen[0], chosen[1:]


# ---------------------------------------------------------------- the day angle: a story, not a feature list
def day_features(ctx, feats, K, rng):
    """K features in the order of a day (ugc_arcs.json 'day': morning, street, café, crowd, desk, evening): K of the moments (kept in day
    order), each given the feature whose words fit it best (its 'prefer'), else the next one; stored on the feature as f['beat']."""
    B = ctx["arcs"]["day"]
    idx = sorted(rng.sample(range(len(B)), min(K, len(B))))
    fits_ = {k: [x for x in feats if re.search(B[k]["prefer"], x["text"], re.I)] for k in idx}
    got, taken_ = {}, set()
    for k in sorted(idx, key=lambda k: (len(fits_[k]), k)):          # the moment with the fewest fitting features chooses first
        f = next((x for x in fits_[k] if x["tag"] not in taken_), None) or next((x for x in feats if x["tag"] not in taken_), None)
        if f:
            got[k] = f
            taken_.add(f["tag"])
    return [dict(got[k], beat=B[k]) for k in sorted(got)]


def day_chapter(ctx, f, rng, used):
    """One moment of the day: the scene setter ('At the café.') + the feature as a standalone 'you' line (+ sometimes a payoff): 2-3
    short sentences, the footage words of that place in shot_kw so the picture is a clip of it."""
    bt, c = f["beat"], f["c"]
    lead = choose(bt["when"], "", rng, used, fresh=True) or choose(bt["when"], "", rng, used)
    fx = fix_line(ctx, f, rng, used, lead or "", lead or "")
    aft = choose(c.get("after") or [], f["line_l"], rng, used, f"{lead or ''} {fx}", fresh=True) if (rng.random() < 0.85 or not REVIEWS) else None
    parts = [p for p in (lead, fx, aft) if p]
    while len(parts) > 1 and (nwords(" ".join(parts)) > MAX_CHAPTER_WORDS or sum(len(sents(p)) for p in parts) > MAX_SENTENCES):
        parts.pop()
    kw = list(dict.fromkeys(bt["kw"][:2] + shot_kw(c, f)))[:4]      # (2-4 words: the place first, then the feature's footage words)
    return chapter(" ".join(parts), "point", f, None, c, kw=kw)


# ---------------------------------------------------------------- the engine: one script per angle
def build_engine(ctx, angle, i, seed, rng, used, taken, n_alt, bump=0):
    used0, taken0 = used.fork(), set(taken)
    F, hi = ctx["feats"], ctx["arcs"]["words"]["max"]
    aim = ctx["arcs"]["words"]["aim" if ctx["rich"] else "thin_aim"]
    n = len(F)
    K = dict(n_things=min((5 if ctx["rich"] else 4) + bump, n), demo=min(6, n), stop_x=min(5, n), travel=min(4, n), value=min(4, n),
             day=min(5, n))[angle]
    base = sorted(F, key=lambda f: (f["c"]["rank"], rng.random()))             # strongest, most concrete first; leather and looks last
    shift = (i + seed - 1) % n if n > K else 0                                 # which one a script leaves out
    pool = base[shift:] + base[:shift]
    if angle == "travel":
        pool.sort(key=lambda f: not f["c"].get("travel"))
    sel, rest = pool[:K], pool[K:]
    sel.sort(key=lambda f: (not f["c"].get("travel") if angle == "travel" else 0, f["c"]["rank"], rng.random()))
    first, main = sel[0], None
    if angle == "stop_x":      # the main hook IS the first chapter's 'Stop ...' (chapter 1 gives the fix); no such line: a general hook
        c = first["c"]
        hp = choose([o for o in options(ctx, c, "hook_p") + (options(ctx, c, "stop") if ctx["builtin"] else [])
                     if (o if isinstance(o, str) else o["t"]) not in taken and nwords(o if isinstance(o, str) else o["t"]) <= MAX_HOOK_WORDS],
                    first["line_l"], rng, used)
        m_ = re.match(r"(?:Stop|No more|You're done with) (\w+)", hp or "")
        main = H(hp, "problem", f"STOP {m_.group(1).upper()}" if m_ else c["label_p"], first["tag"]) if hp else None
    start, chs = rng.randrange(2), []
    if angle == "day":                 # a story: the bag through a day, each moment tied to the feature that fits it (and to footage of
        sel = day_features(ctx, sel + rest, K, rng)       # that place: a door, the street, a café table), every feature a true line
        first, rest = sel[0], [f for f in pool if f["tag"] not in {x["tag"] for x in sel}]
    for j, f in enumerate(sel):
        if angle == "day":
            chs.append(day_chapter(ctx, f, rng, used))
            continue
        mode = {"n_things": "headline" if (j + start) % 2 == 0 and f["c"].get("headline") else "problem", "demo": "demo",
                "stop_x": "fix" if (j == 0 and main) else "stop",
                "travel": "moment" if f["c"].get("travel") and f["c"].get("moment") else "problem", "value": "problem"}[angle]
        chs.append(point(ctx, f, rng, used, mode, number=j + 1 if angle == "n_things" else None))
    ship = ship_phrase(ctx, rng, used)
    rv = reviews_chapter(ctx, rng, used, prefer=(8,) if angle == "value" else (6,) if angle == "travel" else ()) if REVIEWS else None
    ex = dict(proof=rv or recap_chapter(ctx, sel, rng, used))
    if angle == "value" or (angle in ("n_things", "stop_x") and rng.random() < 0.6):
        ex["objection"] = objection_chapter(ctx, rng, used, rv["reviews"] if rv else ())
    if angle in ("demo", "value") and ctx["colours"]:
        ex["colours"] = colours_chapter(ctx, rng, used)
    off = dict(text="x " * 20)         # (the offer chapter is made last: what the objection already said is not said twice)

    def assemble():
        cs = chs + [ex[k] for k in ("colours", "recap", "proof", "objection") if ex.get(k)] + [off]
        for k, c in enumerate(cs):
            c["id"] = f"c{k + 1}"
        return cs
    for _ in range(8):         # a rich product's script must reach its aim: the optional chapters, then spare features
        if sum(nwords(c["text"]) for c in assemble()) + 12 >= aim:
            break
        if not ex.get("objection") and (c := objection_chapter(ctx, rng, used, rv["reviews"] if rv else ())):
            ex["objection"] = c
        elif not ex.get("recap") and rv and (c := recap_chapter(ctx, sel, rng, used)):
            ex["recap"] = c
        elif not ex.get("colours") and ctx["colours"] and (c := colours_chapter(ctx, rng, used)):
            ex["colours"] = c
        elif rv and len(rv["reviews"]) < 3 and (c := reviews_chapter(ctx, rng, used, prefer=rv["reviews"], count=3)):
            ex["proof"] = rv = c                  # a third voice
        elif rest and angle != "n_things":       # (n_things says how many things there are: no extra chapter)
            chs.append(point(ctx, rest.pop(0), rng, used, "demo" if angle == "demo" else "problem"))
        else:
            break
    ot = (ex.get("objection") or {}).get("text", "")
    off = offer_chapter(ctx, rng, used, "" if "shipping" in ot else ship, price=not (ctx["V"]["price"] and ctx["V"]["price"] in ot))      # (said once: not twice)
    cs = assemble()
    while sum(nwords(c["text"]) for c in cs) + 12 > hi and (ex.get("colours") or ex.get("objection") or ex.get("recap")):
        ex.pop("colours" if ex.get("colours") else "recap" if ex.get("recap") else "objection")
        cs = assemble()
    if angle == "n_things" and ctx["rich"] and rest and sum(nwords(c["text"]) for c in cs) + 12 < ctx["arcs"]["words"]["min"] and bump < 2:
        used.clear(), taken.clear()
        used.update(used0), taken.update(taken0)
        used.sets = list(used0.sets)
        return build_engine(ctx, angle, i, seed, rng, used, taken, n_alt, bump + 1)       # one more numbered thing
    order = list(HOOK_TYPES)
    rng.shuffle(order)
    cands = hook_cands(ctx, angle, first, sel, K)
    if angle == "travel":      # the travel angle opens on a travel question
        main = rng.choice([h for h in cands["question"] if h["label"] == "TRAVEL DAY" and h["text"] not in taken] or cands["question"])
    mt = dict(n_things="promise", demo="promise", stop_x="problem", travel="question", value="price", day="promise")[angle]
    pool = [h for h in cands["promise"] if h.get("ang")]
    if main is None and pool and (angle in ("n_things", "demo", "day") or not cands[mt]):      # the first 3 s are specific: the angle's own
        main = rng.choice([h for h in pool if h["text"] not in taken] or pool)           # promise, never 'A quick look at the bag.'
    h1, alts = pick_hooks(ctx, cands, order, n_alt, rng, taken, mt, main)
    return h1, alts, cs


def hand_script(ctx, hs, seed, used, taken, n_alt, rng):
    """A hand-written Hobo Bag script (ugc_hobo.json) filled with the product's real offer; a part its facts can't carry
    (no % to say, no review of the product) falls back to the engine's chapter or drops out."""
    V, arcs = ctx["V"], ctx["arcs"]
    pool = [h for h in (dict(h, text=fill(h["text"], V), label=fill(h["label"], V) or "") for h in hs["hooks"]) if hook_ok(h)]
    s = (seed - 1) % len(pool)
    pool = pool[s:] + pool[:s]
    main, rest, alts, seen = pool[0], pool[1:], [], {pool[0]["type"]}
    extra = set(re.findall(r"[a-z0-9]+", ctx["pr"]["short"].lower()))
    base = cw(main["text"], extra)
    for rnd in (0, 1):
        for h in rest:
            if h not in alts and len(alts) < n_alt and len(cw(h["text"], extra) & base) <= 1 and (rnd == 1 or h["type"] not in seen):
                alts.append(h)
                seen.add(h["type"])
    taken.update(h["text"] for h in [main] + alts)
    F, chs = {f["tag"]: f for f in ctx["feats"]}, []
    for j, ch in enumerate(hs["chapters"]):
        kind = ch["kind"]
        text = ch["alt"] if seed > 1 and (seed + j) % 2 == 0 and ch.get("alt") else ch.get("text")     # seeds: other wording
        if kind == "reviews" and not REVIEWS:
            continue
        if kind == "reviews":
            keep = [(n, arcs["reviews"]["pieces"][str(n)][k]) for n, k in ch["reviews"] if n in (ctx["pr"].get("reviews") or [])
                    and review_ok(ctx, n, arcs["reviews"]["pieces"][str(n)][k])]
            c = reviews_chapter(ctx, rng, used, picks=keep, intro=ch["intro"]) if keep else reviews_chapter(ctx, rng, used)
        elif kind == "offer":
            ship = ship_phrase(ctx, rng, used)
            t = fill(text, dict(V, ship=(" " + ship) if ship else "", ship_s=(ship + " ") if ship else "")) if ctx["pct"] else None
            c = chapter(t, "offer", kw=ch["shot_kw"], keywords=[x for x in (fill(k, V) for k in ch["keywords"]) if x]) if t else offer_chapter(ctx, rng, used, ship)
        elif kind == "objection":
            c = chapter(text, "objection", kw=ch["shot_kw"], keywords=ch["keywords"]) if V["warranty"] and V["returns"] else None
        elif kind == "proof":
            c = chapter(text, "proof", kw=ch["shot_kw"], keywords=ch["keywords"])
        else:
            c = chapter(text, kind, F[ch["tag"]], ch.get("number"), kw=ch["shot_kw"], keywords=ch["keywords"]) if ch["tag"] in F else None
        if c:
            chs.append(c)
    for k, c in enumerate(chs):
        c["id"] = f"c{k + 1}"
    return main, alts, chs


# ---------------------------------------------------------------- scripts()
def support(ctx):
    n = len(ctx["feats"])
    return [a for a in ANGLES if (a == "demo" and n >= 1) or (a in ("n_things", "stop_x") and n >= 2) or (a == "day" and n >= 4) or
            (a == "travel" and n >= 2 and any(f["c"].get("travel") for f in ctx["feats"])) or (a == "value" and n >= 2 and ctx["deal"])]


def finish(ctx, sc):
    """words, est_seconds, offer, claims and numbers of a built script."""
    V, pct = ctx["V"], ctx["pct"]
    texts = [sc["hook"]["text"]] + [c["text"] for c in sc["chapters"]]
    sc["words"] = sum(nwords(t) for t in texts)
    sc["est_seconds"] = round(sc["words"] / VPS, 1)
    last = sc["chapters"][-1]
    sc["offer"] = dict(chapter=last["id"], word=str(pct) if pct else "free") if last["kind"] == "offer" and (pct or ctx["gift"]) else None
    body = " ".join(texts + [h["text"] for h in sc["alt_hooks"]]).lower()
    cl = list(dict.fromkeys(c["tag"] for c in sc["chapters"] if c["tag"]))
    cl += ([f"{pct}% off"] if pct and sc["offer"] else []) + ([ctx["gift"]] if ctx["gift"] and sc["offer"] else [])
    cl += [x for x, k in (("free shipping", "shipping"), (V["warranty"], "warranty"), (V["returns"], "returns")) if x and k in body]
    cl += [f"review {n}" for c in sc["chapters"] for n in c.get("reviews") or []]
    sc["claims"] = cl
    sc["numbers"] = sorted({NUMW.index(w) for w in re.findall(r"\b(two|three|four|five|six|seven|eight|nine|ten) (?:things|reasons|details)\b", body)})
    return sc


def overlap(sc, others):
    """(most identical sentences shared with one earlier script, a hook shared?)."""
    mine = {flat(s) for c in sc["chapters"] for s in sents(c["text"])}
    hk = {h["text"] for h in [sc["hook"]] + sc["alt_hooks"]}
    return max([len(mine & {flat(s) for c in o["chapters"] for s in sents(c["text"])}) for o in others] + [0]), \
        any(hk & {h["text"] for h in [o["hook"]] + o["alt_hooks"]} for o in others)


def scripts(pr, n=5, seed=1, hooks=4, voice="you", avoid=None):
    """The ugc scripts of a product (module doc). Deterministic for (product, n, seed, hooks, avoid). avoid = {"hooks": [...],
    "sentences": [...]}: what the product's earlier batches already said (novelty.py): the engine takes other words, and a
    hand-written script whose hook went out lately waits (the engine writes that angle instead)."""
    if voice != "you":
        raise ValueError("voice: only 'you' (a first-person voice is not built: never an invented customer experience)")
    ctx = context(pr)
    cycle = support(ctx)
    if not ctx["feats"] or not cycle:
        return []
    last_ = (avoid or {}).get("angles") or []          # the angles of the product's last batch go to the end: a batch of 5 of the 6 angles
    cycle = [x for x in cycle if x not in last_] + [x for x in cycle if x in last_]       # leaves out one of them: another next time
    hand = data("ugc_hobo.json")["scripts"] if ctx["builtin"] and pr.get("key") == "hobo bag" else []
    used, taken, out = Used(), set(), []
    avoid = avoid or {}
    old_hooks = {flat(x) for x in avoid.get("hooks") or []}
    hand = [hs for hs in hand if flat(fill(hs["hooks"][0]["text"], ctx["V"]) or "") not in old_hooks]   # a hand script rests 3 batches
    taken.update(avoid.get("hooks") or [])
    for t in avoid.get("sentences") or []:                                                   # what earlier batches said: not again
        used.update(sents(t))
    taken.update(fill(h["text"], ctx["V"]) or "" for hs in hand for h in hs["hooks"])        # the engine never repeats a hand hook
    for hs in hand:                                                                          # ... or a hand-written sentence
        for ch in hs["chapters"]:
            for t in (ch.get("text"), ch.get("alt")):
                used.update(sents(t or ""))
            if ch["kind"] == "reviews":
                ps = [ctx["arcs"]["reviews"]["pieces"][str(n)][k] for n, k in ch["reviews"]]
                used.sets = list(used.sets) + [set(ps)]
                used.update(f"piece {p}" for p in ps)
                used[ch["intro"]] += 1
    n_alt = max(3, hooks) + 1
    for i in range(n):
        angle = cycle[(i + seed - 1) % len(cycle)]
        best = None
        for attempt in range(8):
            rng = random.Random(f"{pr.get('key')}|{seed}|{i}|{attempt}")
            u2, t2 = used.fork(), set(taken)
            hs = next((h for h in hand if h["angle"] == angle), None) if i < len(hand) and attempt == 0 else None
            main, alts, chs = hand_script(ctx, hs, seed, u2, t2, n_alt, rng) if hs else build_engine(ctx, angle, i, seed, rng, u2, t2, n_alt)
            sc = finish(ctx, dict(id=f"U{i + 1:02d}", index=i, angle=angle, voice=voice, product=pr.get("key"), hook=main,
                                  alt_hooks=alts, chapters=chs))
            score = overlap(sc, out)
            if best is None or score < best[0]:
                best = (score, sc, u2, t2)
            if score[0] <= 2 and not score[1]:
                break
        _, sc, used, taken = best
        out.append(sc)
    return out


# ---------------------------------------------------------------- checks and helpers
def tts_items(sc, hook=None):
    """[(id, text)]: one voice take each, the hook (main unless a hook dict is given) and the chapters."""
    return [("hook", (hook or sc["hook"])["text"])] + [(c["id"], c["text"]) for c in sc["chapters"]]


def ctx_texts(sc):
    """Every text a viewer hears or reads: [(where, text)] (all hooks and labels, chapters, tags)."""
    out = []
    for k, h in enumerate([sc["hook"]] + sc["alt_hooks"]):
        out += [(f"{sc['id']} hook{k}", h["text"]), (f"{sc['id']} hook{k} label", h["label"])]
    for c in sc["chapters"]:
        out += [(f"{sc['id']} {c['id']}", c["text"])] + ([(f"{sc['id']} {c['id']} tag", c["tag"])] if c["tag"] else [])
    return out


def lint(sc, pr, ctx=None):
    """Problems of one script (empty = fine): first person, lengths, hook rules, compliance.check on every text."""
    ctx = ctx or context(pr)
    P = []
    for h in [sc["hook"]] + sc["alt_hooks"]:
        if nwords(h["text"]) > MAX_HOOK_WORDS or not hook_ok(h) or h["type"] not in HOOK_TYPES:
            P.append(f"hook: {h['text']!r} / {h['label']!r} / {h['type']}")
        if FIRST.search(h["text"]):
            P.append(f"first person in hook: {h['text']}")
    if len(sc["alt_hooks"]) < 3 or len({h["type"] for h in sc["alt_hooks"][:3]}) < 3:
        P.append("fewer than 3 alt hooks of different types")
    extra = set(re.findall(r"[a-z0-9]+", pr["short"].lower()))
    P += [f"alt hook repeats the main hook's words: {h['text']}" for h in sc["alt_hooks"]
          if len(cw(h["text"], extra) & cw(sc["hook"]["text"], extra)) > 1]
    for c in sc["chapters"]:
        t = c["text"]
        ns = len(sents(t))
        if not 1 <= ns <= MAX_SENTENCES or nwords(t) > MAX_CHAPTER_WORDS:
            P.append(f"{c['id']}: {ns} sentences, {nwords(t)} words")
        if FIRST.search(re.sub(r"(says:)[^.!?]*[.!?]", r"\1 .", t)):
            P.append(f"{c['id']}: first person outside a review quote: {t}")
        if c["number"] and sc["angle"] != "n_things":
            P.append(f"{c['id']}: a number outside n_things")
        if re.search(r"(?:^|\s)\d\.\s|\bnumber (?:one|two|three|four)\b", t, re.I):
            P.append(f"{c['id']}: the number is written in the text")
        if c["kind"] != "reviews" and not 2 <= len(c["shot_kw"]) <= 4:
            P.append(f"{c['id']}: shot_kw {c['shot_kw']}")
    last = sc["chapters"][-1]
    if last["kind"] != "offer" or "Tap the link below." not in last["text"]:
        P.append("the last chapter is not the offer with 'Tap the link below.'")
    if [c["id"] for c in sc["chapters"]] != [f"c{k + 1}" for k in range(len(sc["chapters"]))]:
        P.append("chapter ids are not c1, c2 ...")
    lo, hi = ctx["arcs"]["words"]["floor"], ctx["arcs"]["words"]["max"]
    if ctx["rich"] and not lo <= sc["words"] <= hi:
        P.append(f"{sc['words']} words (a product with 5+ feature lines: {lo}-{hi}, aim {ctx['arcs']['words']['min']}+)")
    C = comp()
    items = [dict(where=w, text=t, source="ours") for w, t in ctx_texts(sc)]
    P += [f"compliance {p['category']} {p['term']!r} in {p['where']}: {p['text']}" for p in
          C.check(items, ctx=C.context(pr), allowed_numbers=sc.get("numbers") or ())]
    return P


# ---------------------------------------------------------------- CLI
def show(sc):
    print(f"\n=== {sc['id']} {sc['angle']}  {sc['words']} words, ~{sc['est_seconds']} s   offer {sc['offer']}  numbers {sc['numbers']}")
    h = sc["hook"]
    print(f"  HOOK [{h['type']} | {h['label']} | {h['feature']}] {h['text']}")
    for c in sc["chapters"]:
        print(f"  {c['id']}{' #' + str(c['number']) if c['number'] else ''} [{c['kind']} | {c['tag']} | {','.join(c['shot_kw'])} | "
              f"{','.join(c['keywords'])}]\n     {c['text']}")
    for h in sc["alt_hooks"]:
        print(f"  alt [{h['type']} | {h['label']} | {h['feature']}] {h['text']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hooks", type=int, default=4)
    ap.add_argument("--products-dir")
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.products_dir:
        os.environ["LC_PRODUCTS_DIR"] = a.products_dir
    M = mb()
    files = M.product_files(M.products_dir())
    pk = M.pick_product(a.product, files)
    if not pk:
        sys.exit(f"unknown product {a.product!r}")
    w = []
    pr = M.honest(M.product(pk, files, w), w)
    ss = scripts(pr, a.n, a.seed, a.hooks)
    if a.json:
        print(json.dumps(ss, indent=1, ensure_ascii=False))
    else:
        for sc in ss:
            show(sc)
    if a.lint:
        ctx = context(pr)
        bad = [(sc["id"], p) for sc in ss for p in lint(sc, pr, ctx)]
        print("\nlint:", "ok" if not bad else f"{len(bad)} problem(s)")
        for b in bad:
            print("  ", *b)
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""The strategist step: every batch starts with NEW ideas, complete scripts and static concepts written for that batch, never
with the script engine's templates (owner 2026-10-21: "each batch should contain something new or unique ... go through research,
check our past videos, fully new ideas, better ideas ... write stories as story-strat, full strategist-level scripts").

The agent that gets the request is the creative strategist:

  1. python3 pipeline/ideas.py packet --product "Hobo Bag" --theme "black friday" --projects 4 --statics 20 --out $OUT
        -> $OUT/strategy_packet.md: the product's true facts, what the footage library can SHOW (per tag), everything the earlier
           batches did (angles, hooks, statics, scenes), the research notes, the static / scene rules and the sheet's format.
  2. The agent reads it and the research (docs/research/), looks at the past batches' contact sheets if it wants, and WRITES
        $OUT/ideas.json: per project a big idea, why it is new, 4 hooks, a complete script (every line with the picture it needs),
        and per static its concept (an AI studio scene of the real bag, a studio packshot, a real footage frame ...).
  3. python3 pipeline/ideas.py check $OUT/ideas.json --product "Hobo Bag"       -> problems (fix them and check again)
  4. python3 pipeline/make_batch.py plan ... --ideas $OUT/ideas.json            -> voiceovers / AI stills / render / upload as usual
        (the sheet goes to Drive with the batch: strategy_sheet.md + strategy_sheet.csv, made by `ideas.py sheet`).

ideas.json (every text is the spoken / printed text itself; claims only from the packet's facts; no first person, no invented customer
experience, no health / medical claims):
{
 "product": "Hobo Bag", "theme": "black friday", "date": "2026-10-21",
 "research": ["what I looked at and what it changed, one line each"],
 "projects": [{
    "id": "P01", "slug": "whatfits", "title": "Pack it for the whole day", "big_idea": "one sentence",
    "why_new": "what no earlier batch did (angle / hook / picture / structure)",
    "structure": "one_moment" (data/story_structures.json) | "<an id of your own>" with "structure_name": "...", "shape": ">= 60 chars",
    "hooks": [{"text": "<= 14 words", "type": "promise|superlative|question|problem|price", "label": "ON-SCREEN LABEL (<= 3 words)",
               "show": ["packing", "inside"]}, ... 4 in all (H1 is the main one, they differ in type and words)],
    "chapters": [{"kind": "point|proof|objection|offer", "text": "1-5 short sentences, one voice take", "tag": "SMART COMPARTMENTS" | null,
                  "number": null | 1, "show": ["inside", "packing"]  (what the picture must SHOW while this is said: footage_index.TAGS),
                  "highlight": ["compartments"]  (caption words on a red pill, optional),
                  "beat": "move"  (the structure's beat this chapter is), "proof_shot": true  (one or two chapters: the picture proves the
                  line, held 2-3 s with the clip's own sound; show tags a movement)}, ... the last one kind offer, ends 'Tap the link below.']
 }],
 "statics": [{
    "id": "S01", "project": "P01", "layout": "concept | studio | native | quotes | value | offer | stars | colours | checklist",
    "idea": "the creative idea in one sentence",
    "headline": "<= 8 words, optional", "kicker": "BLACK FRIDAY (optional)", "sub": "optional", "pill": true (the offer's % pill) | "badge": "text",
    "where": "top|bottom (concept: where the words go; the scene leaves that end empty)", "tone": "dark|light (optional)",
    "scene": {"kind": "object|worn|hand", "colour": "Black", "prompt": "the scene: surface, props, light, composition (no people / faces)"}
 }, {
    "id": "S02", "project": "P02", "layout": "ad", "idea": "...",
    "format": "magazine_cover"  (data/static_formats.json) | "<a new id>" with "format_name": "...", "art": "the art direction (>= 60 chars)",
              "people": "none|behind|cropped"  (a format of your own: invent one every batch),
    "words": ["LIBRA", "THE BAG THAT ZIPS SHUT", "EARLY BLACK FRIDAY: 50% OFF"]  (the exact words the AI sets in the picture, 1-4 lines),
    "headline": "the line the ad copy and the tracker name (default: the first line that is not LIBRA)",
    "scene": {"colour": "Burgundy", "ref": "optional site photo (a back view)", "prompt": "what the picture shows: setting, props, light"}
 }]
}
The words of the scene prompt are only the scene: the keep-the-real-bag text, the style and the no-face rule are added by ai_gen.
STORIES (owner 2026-10-27; sheets from that day on): every project a story structure (one a batch, not the last batch's), at most 3 features
and a different lead feature per project, the price only in the last chapter and in at most one hook, hooks that open on four different
pictures of the bag doing something (first `show` tag a movement or a person), one or two proof shots, the bag on a person (worn /
walking) in two chapters of a project without the presenter, and one presenter project per batch of 2+ ("no_presenter": "<the request's
words>" when the request says none).
An `ad` static is designed whole by the AI (owner 2026-10-26: the magazine cover, the feature diagram, the HALF PRICE poster, the POV
street photo, the flat lay, the gift tag): ai_gen adds the format's art direction, the keep-the-real-bag text, the exact words and the
people rule; the gate reads the words back. Every batch new formats: each format once a batch, none the product's last batch used, and
at least one format of your own (two when the batch has 6+ ad statics).

PRESENTER PROJECTS (owner 2026-10-21: "avatars accepted if there is an actual story that requires actors"; Julian wants a woman sitting
there and talking, the footage cut in between): a project may carry a presenter: a generated adult host who says the whole script to camera
(presenter.py; ~2 credits per second of her talking). She is a host, never a customer: 'you' form, no first person, no purchase / use /
result she lived. Her words are the script's words, at her own pace (about 2.5 a second: 135-205 words for 55-80 s), and the library's
real footage cuts in over her voice wherever a line describes something. Add to the project:
    "presenter": {"id": "maya", "scenes": [{"id": "cafe", "where": "She sits at a small round table in a sunny cafe, a latte in a white cup in front of her,
                  warm daylight from the window beside her, a softly blurred cafe behind.", "outfit": "She wears a denim shirt.",
                  "bag": "resting on her lap", "colour": "brown", "ambience": "Quiet cafe ambience"}, ...  1-3 scenes]}
    hooks[].scene (default: the first scene), chapters[].scene (default: the first) and chapters[].cam: who is on camera while the chapter
    is said: "open" (she says the first phrase, the footage shows the rest; the default), "both" (she opens and closes it), "close", "full"
    (all of it on her: the story beats that need a face) or "none". A hook is always on her. One chapter = one take (at most 15 s: <= 36 words).
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

LAYOUTS = ("ad", "concept", "studio", "native", "quotes", "value", "offer", "stars", "colours", "checklist", "gifts", "bundle")
SALE_LAYOUTS = ("gifts", "bundle")                   # only while a sale campaign runs (campaign.py): its free gifts / 2-3 bags together


def sale_campaign(theme, day=None):
    """The store-wide sale campaign a batch of this theme gets (campaign.py), and compliance told about it; None when none runs."""
    import campaign
    import compliance
    c = campaign.active(mb().pick_theme(theme or ""), day)
    compliance.use_campaign(c)
    return c
HOOK_TYPES = ("promise", "superlative", "question", "problem", "price")
MAX_HOOK_WORDS = 14
MAX_CHAPTER_WORDS, MAX_SENTENCES = 70, 5            # (the script engine's own limits are 45 / 3: a strategist's story needs more room)
WORDS = (170, 285)                                   # the whole script: 55-80 s at 185-215 wpm
PRES_WORDS, PRES_CHAPTER_WORDS = (135, 205), 36      # a presenter's script: 55-80 s at her 2.5 words a second; one take of at most 15 s
CAMS = ("open", "both", "close", "full", "none")
FACE_WORDS = re.compile(r"\b(face|faces|smil\w+|looking at (?:the )?camera|portrait|selfie|eyes|mouth|lips|mannequin|sunglasses)\b", re.I)
NO_PEOPLE = "Nobody is in the picture, not even blurred in the background."
FAKE_UI = re.compile(r"play button|notification|chat bubble|speech bubble|text message|slider|cursor|check ?box|tick ?box|"
                     r"(?:phone|app|iphone) screen|\b(?:shop|buy|tap|order)[- ]now button|\bswipe\b", re.I)      # Meta: no fake interface
MAGAZINES = re.compile(r"\b(vogue|elle|harper'?s|bazaar|cosmopolitan|marie claire|instyle|vanity fair|time magazine|forbes|"
                       r"people magazine|tatler|grazia|glamour magazine)\b", re.I)
INSIDE = re.compile(r"\b(inside (?:of )?the bag|open bag|unzipped|bag (?:is )?open|interior of the bag|bag'?s interior|lining|spilling out|"
                    r"peeking out)\b", re.I)
AD_PEOPLE = ("none", "behind", "cropped")
NEW_FORMATS = ((3, 1), (6, 2))                       # (ad statics in the batch, formats of your own it needs at least)
STORY_FROM = "2026-10-27"                            # the story rules (owner 2026-10-27) check sheets from this day on
STORY_MAX_FEATURES = 3                               # features one video may talk about
PROOF_TAGS = {"zip", "zip_hand", "side_zip", "snap", "lock", "pocket", "packing", "strap", "tie", "inside"}   # a movement the shot proves
PEOPLE_TAGS = {"worn", "walking"}                    # the bag on a person
STILL_TAGS = {"hero", "placed", "colours"}           # the bag just sitting there: never a hook's opening picture
PRICE_WORDS = re.compile(r"\d+\s?%|\bpercent\b|\bhalf[- ]price\b|\bsale\b|\bblack friday\b|\bcyber monday\b|\bdiscount\w*|\$\s?\d|"
                         r"\bbundles?\b|\bprices?\b|\bfree (?:gifts?|shipping|pouch|wallet|jewell?e?ry)", re.I)


def formats():
    """data/static_formats.json: {"meta": [rules], "formats": {id: format}} (the AI-designed ad formats, ideas.py / ai_gen.py)."""
    try:
        d = json.load(open(os.path.join(HERE, "data", "static_formats.json")))
    except (OSError, ValueError):
        d = {}
    return dict(meta=d.get("meta") or [], formats={f["id"]: f for f in d.get("formats") or []})


def structures():
    """data/story_structures.json: {"rules": [...], "structures": {id: structure}} (the videos' story shapes, owner 2026-10-27)."""
    try:
        d = json.load(open(os.path.join(HERE, "data", "story_structures.json")))
    except (OSError, ValueError):
        d = {}
    return dict(rules=d.get("rules") or [], structures={x["id"]: x for x in d.get("structures") or []})


def _stem(w):
    return re.sub(r"(?:es|s)$", "", w) if len(w) > 3 and not w.endswith("ss") else w


def feature_keys(pr):
    """[(TAG, head stem, [stems])] of the product's features (their on-screen tags: 'GOLD SIDE ZIPS' -> zip, [gold, side, zip])."""
    out = []
    for f in pr.get("features") or []:
        tag = f[1] if len(f) > 1 and f[1] else ""
        ws = [_stem(w) for w in re.findall(r"[a-z]+", tag.lower()) if w not in STOPWORDS and w not in ("one", "two", "three")]
        if ws:
            out.append((tag, ws[-1], ws))
    return out


def features_in(text, keys):
    """The features a line talks about, in the order it says them: its words hold the tag's head word and half of its words."""
    toks = [_stem(w) for w in re.findall(r"[a-z]+", (text or "").lower())]
    got = []
    for tag, head, ws in keys:
        if head in toks and sum(w in toks for w in set(ws)) >= -(-len(set(ws)) // 2):
            got.append((toks.index(head), tag))
    return [t for _, t in sorted(got)]


def story_problems(p, pid, pr, cov, keys, slib, P, W):
    """The story rules of one project (owner 2026-10-27): its structure and beats, at most 3 features, the price only at the end,
    hooks that open on four different pictures of the bag doing something, one or two proof shots, people in the footage.
    Returns the project's lead feature (the first one it talks about) or None."""
    chs, hooks, pres = p.get("chapters") or [], p.get("hooks") or [], p.get("presenter")
    body = [c for c in chs if c.get("kind") != "offer"]
    st = slib.get(p.get("structure") or "")
    if not st:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,23}", str(p.get("structure") or "")) or len(str(p.get("structure_name") or "")) < 4 \
                or len(str(p.get("shape") or "")) < 60:
            P.append(f"{pid}: structure: one of {', '.join(slib)} or one of your own (an id, structure_name and shape of at least 60 characters)")
        elif any(not c.get("beat") for c in body):
            W.append(f"{pid}: name each chapter's beat (the part of your structure it is)")
    else:
        ids = [b["id"] for b in st["beats"]]
        bad = [c.get("beat") for c in body if c.get("beat") not in ids]
        if bad:
            P.append(f"{pid}: beat {bad[0]!r} is not one of {st['name']}'s beats ({', '.join(ids)})")
        else:
            order = [ids.index(c["beat"]) for c in body]
            if order != sorted(order):
                P.append(f"{pid}: the beats are out of {st['name']}'s order ({' -> '.join(ids)})")
            miss = [b["id"] for b in st["beats"] if b.get("required") and b["id"] != "offer" and b["id"] not in {c["beat"] for c in body}]
            if miss:
                P.append(f"{pid}: {st['name']} needs the beat(s) {', '.join(miss)}")
    feats = []
    for c in body:
        for t in features_in(c.get("text"), keys) + ([c["tag"]] if c.get("tag") in {k[0] for k in keys} else []):
            if t not in feats:
                feats.append(t)
    if len(feats) > STORY_MAX_FEATURES:
        P.append(f"{pid}: {len(feats)} features ({', '.join(feats)}): a story talks about at most {STORY_MAX_FEATURES}; one promise, "
                 f"not a feature list")
    for j, c in enumerate(chs, 1):
        m = PRICE_WORDS.search(c.get("text") or "") or PRICE_WORDS.search(c.get("tag") or "")
        if m and c.get("kind") != "offer":
            P.append(f"{pid} c{j}: {m.group(0)!r}: the price, the sale and the bundle are said only in the last chapter")
    priced = [k for k, h in enumerate(hooks[:4], 1) if PRICE_WORDS.search(h.get("text") or "") or h.get("type") == "price"]
    if len(priced) > 1:
        P.append(f"{pid}: hooks {', '.join(f'H{k}' for k in priced)} open on the price: one price hook at most, the others a moment or a question")
    if not pres:
        firsts = []
        for k, h in enumerate(hooks[:4], 1):
            sh = h.get("show") or []
            if not sh or sh[0] in STILL_TAGS:
                P.append(f"{pid} H{k}: the hook opens on {sh[0] if sh else 'nothing'!r}: show the bag doing something (a movement or a person: "
                         f"{', '.join(sorted(PROOF_TAGS | PEOPLE_TAGS))})")
            elif cov and cov.get(sh[0], [0])[0] < MIN_MOMENTS:
                W.append(f"{pid} H{k}: only {cov.get(sh[0], [0])[0]} good footage moments show '{sh[0]}': the opening may not match")
            firsts.append(sh[0] if sh else None)
        if len([f for f in firsts if f]) != len({f for f in firsts if f}):
            P.append(f"{pid}: the hooks open on the same picture ({', '.join(str(f) for f in firsts)}): four hooks, four different first `show` tags")
        if sum(1 for c in body if set(c.get("show") or []) & PEOPLE_TAGS) < 2 and cov and \
                max(cov.get(t, [0])[0] for t in PEOPLE_TAGS) >= MIN_MOMENTS:
            P.append(f"{pid}: show the bag on a person (worn / walking) in at least two chapters: the footage has them, people sell")
    proofs = [c for c in body if c.get("proof_shot")]
    if not 1 <= len(proofs) <= 2:
        P.append(f"{pid}: {len(proofs)} proof shots: one chapter (two at most) with \"proof_shot\": true, where the picture proves the line "
                 f"(held 2-3 s with the clip's own sound)")
    for c in proofs:
        if not set(c.get("show") or []) & PROOF_TAGS:
            P.append(f"{pid}: the proof shot ({(c.get('text') or '')[:30]!r}...) shows {c.get('show')}: it needs a movement "
                     f"({', '.join(sorted(PROOF_TAGS))})")
        if pres and c.get("cam") == "full":
            P.append(f"{pid}: a proof shot is footage: its chapter's cam cannot be 'full'")
    return feats[0] if feats else None


def ad_format(s, lib=None):
    """The format dict of an `ad` static: the library's, or the sheet's own (format_name / art / people)."""
    f = (lib or formats()["formats"]).get(s.get("format") or "")
    if f:
        return f
    return dict(id=s.get("format"), tag=re.sub(r"[^a-z0-9]", "", str(s.get("format") or "").lower())[:12] or "ad",
                name=s.get("format_name") or s.get("format"), art=s.get("art") or "", people=s.get("people") or "none", words=14, new=True)


def ad_headline(s):
    """The line of an `ad` static that names it (ad copy, tracker, novelty): `headline`, else the first line that is not the masthead."""
    if s.get("headline"):
        return s["headline"]
    return next((w for w in s.get("words") or [] if w.strip().upper() != "LIBRA"), (s.get("words") or [""])[0])
MIN_MOMENTS = 4                                      # good footage moments a tag should have for the product before a chapter leans on it
STOPWORDS = set("the a an and or of to in on for with your you it its this that is are be at by as from up out so no not more all".split())


def mb():
    import make_batch
    return make_batch


def nwords(t):
    return len(re.findall(r"[A-Za-z0-9'’%$.-]+", t or ""))


def sents(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", (t or "").strip()) if s]


def words_of(t):
    return {w for w in re.findall(r"[a-z]{4,}", (t or "").lower()) if w not in STOPWORDS}


def load(path):
    return json.load(open(path))


def product_of(name, products_dir=None):
    M = mb()
    files = M.product_files(products_dir or M.products_dir())
    w = []
    return M.honest(M.product(M.pick_product(name, files), files, w), w)


# ------------------------------------------------------------------ what the footage can show
def coverage(pr):
    """{tag: [good moments, [three sample descriptions]]} of the product's labelled library footage (footage_index label-merge)."""
    M = mb()
    name = M.INDEX_PRODUCT.get(pr.get("key") or "")
    out = {}
    try:
        rows = json.load(open(os.path.join(HERE, "data", "clip_index.json")))
    except (OSError, ValueError):
        return out
    for r in rows:
        if r.get("product") != name or r.get("usable") != "yes" or r.get("faces") != "none":
            continue
        for m in r.get("moments") or []:
            if m.get("q") != "good":
                continue
            for t in m.get("tags") or []:
                e = out.setdefault(t, [0, []])
                e[0] += 1
                if len(e[1]) < 3 and m.get("desc") and len(e[1]) < (e[0] // 40 + 1):
                    e[1].append(m["desc"])
    return out


# ------------------------------------------------------------------ the check
def ad_problems(s, sid, lib, P, W, items):
    """The checks of one `ad` static (the AI designs the whole ad): its format, the exact words, the picture, Meta's rules."""
    import ugc_script as U
    f = lib.get(s.get("format") or "")
    if not f:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,23}", str(s.get("format") or "")):
            P.append(f"{sid}: format: one of {', '.join(lib)} or an id of your own (lower case, 3-24 letters) with format_name, art, people")
        if len(str(s.get("format_name") or "")) < 4 or len(str(s.get("art") or "")) < 60:
            P.append(f"{sid}: a format of your own needs format_name and art (the art direction, at least 60 characters)")
        if (s.get("people") or "none") not in AD_PEOPLE:
            P.append(f"{sid}: people {s.get('people')!r} (one of {', '.join(AD_PEOPLE)})")
    fmt = ad_format(s, lib)
    words = s.get("words")
    if not isinstance(words, list) or not 1 <= len(words) <= 4 or not all(isinstance(w, str) and w.strip() for w in words):
        P.append(f"{sid}: words: the exact lines the picture carries, 1-4 strings")
        words = []
    n = sum(nwords(w) for w in words)
    if n > fmt.get("words", 14):
        P.append(f"{sid}: {n} words on the picture, the {fmt.get('name') or fmt.get('id')} format takes at most {fmt.get('words', 14)}")
    for w in words:
        if re.search(r"[$€£]\s?\d|\d+(?:\.\d\d)\b", w):
            P.append(f"{sid}: {w!r}: no prices in an AI ad (the price test; the model may draw a wrong number): say the %")
        if re.search(r'["“”]', w):
            P.append(f"{sid}: {w!r}: no quotation marks in the words (the prompt quotes them)")
        if U.FIRST.search(w):
            P.append(f"{sid}: {w!r}: first person")
        items.append(dict(where=f"{sid} words", text=w, source="ours"))
    sc = s.get("scene") or {}
    pt = str(sc.get("prompt") or "")
    if len(pt) < 40:
        P.append(f"{sid}: scene.prompt: what the picture shows (setting, props, light), at least 40 characters")
    every = " ".join([pt, s.get("art") or "", *words])
    if FACE_WORDS.search(re.sub(r"\b(?:no|nobody|not|without|never|neither)\b[^.;]{0,50}?\b(?:face|faces|eyes|mouth|portrait)\b", "", pt, flags=re.I)):
        P.append(f"{sid}: the scene asks for a face / eyes / sunglasses / a mannequin: an ad never shows a face (from behind, or cut at the shoulders)")
    if FAKE_UI.search(every):
        P.append(f"{sid}: {FAKE_UI.search(every).group(0)!r}: no fake interface in an ad (buttons, notifications, sliders: Meta rejects them)")
    if MAGAZINES.search(every):
        P.append(f"{sid}: {MAGAZINES.search(every).group(0)!r}: no real publication or brand name (the masthead is LIBRA)")
    if INSIDE.search(pt):
        P.append(f"{sid}: {INSIDE.search(pt).group(0)!r}: keep the bag closed: there is no photo of its inside, the AI would invent one")
    if fmt.get("people") == "none" and re.search(r"\b(woman|man|girl|person|people|she|her|hands?)\b", pt, re.I) \
            and not re.search(r"\b(no|nobody|without)\b[^.]{0,30}\b(person|people|one)\b", pt, re.I):
        W.append(f"{sid}: the {fmt.get('id')} format has nobody in the picture, but the scene names a person: ai_gen tells the model nobody is there")


def check(sheet, pr, n_projects=None, n_statics=None, exclude=None, day=None):
    """(problems, warnings) of a sheet. A problem stops `plan`; a warning is said in its output. exclude: a batch id (B045) whose own
    entries in the novelty log do not count (a redo of that batch re-checks its own sheet). day: the rules of that day (default today;
    a committed sheet is checked by the rules of its own date)."""
    import datetime
    import compliance
    import footage_index
    import novelty
    import ugc_script as U
    P, W = [], []
    camp = sale_campaign(sheet.get("theme"))
    ctx = U.context(pr)
    cov = coverage(pr)
    projs, stats = sheet.get("projects") or [], sheet.get("statics") or []
    if (sheet.get("product") or "").lower() != (pr.get("name") or "").lower():
        P.append(f"product {sheet.get('product')!r} is not {pr.get('name')!r}")
    if n_projects is not None and len(projs) < n_projects:
        P.append(f"{len(projs)} projects in the sheet, {n_projects} asked for")
    if n_statics is not None and len(stats) < n_statics:
        P.append(f"{len(stats)} statics in the sheet, {n_statics} asked for")
    if not sheet.get("research"):
        P.append("research: say what you looked at (past batches, the research notes) and what it changed")
    nl = novelty.load()
    if exclude:
        nl = dict(nl, products={k: dict(v, batches=[b for b in v.get("batches") or []
                                                     if not re.match(rf"{re.escape(str(exclude))}(?:r\d+)?\b", str(b.get("name") or ""))])
                                for k, v in nl["products"].items()})
    old_hooks = {re.sub(r"\W+", " ", h.lower()).strip() for h in novelty.recent(pr["name"], "hook", last=12, log=nl)}
    old_sents = {re.sub(r"\W+", " ", t.lower()).strip() for b in novelty.batches(pr["name"], log=nl)[-6:] for v in b.get("videos") or []
                 for c in v.get("chapters") or [] for t in sents(c)}
    seen_ids, seen_slugs, seen_ideas = set(), set(), []
    lib = formats()["formats"]
    story = (day or datetime.date.today().isoformat()) >= STORY_FROM
    slib, keys, leads = structures()["structures"], feature_keys(pr), {}
    items = []                                           # every text for the compliance check
    for p in projs:
        pid = p.get("id") or "?"
        where = f"{pid}"
        if story:
            lead = story_problems(p, pid, pr, cov, keys, slib, P, W)
            if lead:
                leads.setdefault(lead, []).append(pid)
        pres = p.get("presenter")
        scene_ids = []
        if pres:
            import presenter as PR
            if pres.get("id") not in PR.hosts():
                P.append(f"{where}: presenter {pres.get('id')!r} is not in data/presenters.json ({', '.join(k for k in PR.hosts() if k[0] != '_')})")
            sc_l = pres.get("scenes") or []
            if not 1 <= len(sc_l) <= 3:
                P.append(f"{where}: presenter.scenes: 1-3 scenes (id, where, outfit, bag, colour), {len(sc_l)} given")
            for sc_ in sc_l:
                scene_ids.append(sc_.get("id"))
                if not sc_.get("id") or len(str(sc_.get("where") or "")) < 40:
                    P.append(f"{where}: a presenter scene needs an id and a `where` of at least 40 characters (the room, the light, what she sits at)")
                if re.search(r"sunglasses|mannequin", str(sc_.get("where") or ""), re.I):
                    P.append(f"{where}: scene {sc_.get('id')}: no sunglasses or mannequins (they break the face and lip-sync)")
        if pid in seen_ids or not re.fullmatch(r"P\d\d", pid):
            P.append(f"{where}: id must be P01, P02 ... and unique")
        seen_ids.add(pid)
        slug = re.sub(r"[^a-z0-9]", "", str(p.get("slug") or "").lower())
        if not slug or slug in seen_slugs or len(slug) > 14:
            P.append(f"{where}: slug (one lower-case word, <= 14 letters, unique: it is part of the file name)")
        seen_slugs.add(slug)
        for k in ("title", "big_idea", "why_new"):
            if len(str(p.get(k) or "")) < 12:
                P.append(f"{where}: {k} is missing")
        idea_words = words_of(f"{p.get('title')} {p.get('big_idea')}")
        for other in seen_ideas:
            if len(idea_words & other) >= 0.6 * max(min(len(idea_words), len(other)), 1):
                P.append(f"{where}: the idea is the same as an earlier project's of this sheet (different stories, please)")
        seen_ideas.append(idea_words)
        hooks = p.get("hooks") or []
        if len(hooks) < 4:
            P.append(f"{where}: 4 hooks (H1-H4), {len(hooks)} given")
        if len({h.get("type") for h in hooks[:4]}) < 3:
            P.append(f"{where}: the hooks must be of at least 3 different types")
        for k, h in enumerate(hooks[:4], 1):
            t, label = h.get("text") or "", h.get("label") or ""
            if nwords(t) > MAX_HOOK_WORDS or not t:
                P.append(f"{where} H{k}: {nwords(t)} words (at most {MAX_HOOK_WORDS})")
            if h.get("type") not in HOOK_TYPES:
                P.append(f"{where} H{k}: type {h.get('type')!r} (one of {', '.join(HOOK_TYPES)})")
            if not label or len(label.split()) > 3 or label != label.upper():
                P.append(f"{where} H{k}: label {label!r} (UPPER CASE, at most 3 words)")
            if U.FIRST.search(t):
                P.append(f"{where} H{k}: first person in the hook")
            if pres and h.get("scene") and h["scene"] not in scene_ids:
                P.append(f"{where} H{k}: scene {h['scene']!r} is not one of the project's presenter scenes {scene_ids}")
            if re.sub(r"\W+", " ", t.lower()).strip() in old_hooks:
                P.append(f"{where} H{k}: this hook line was used in an earlier batch: {t!r}")
            for tg in h.get("show") or []:
                if tg not in footage_index.TAGS:
                    P.append(f"{where} H{k}: show tag {tg!r} is not in the vocabulary")
            items += [dict(where=f"{where} H{k}", text=t, source="ours"), dict(where=f"{where} H{k} label", text=label, source="ours")]
        chs = p.get("chapters") or []
        if not 5 <= len(chs) <= 11:
            P.append(f"{where}: {len(chs)} chapters (5-11)")
        words = 0
        for j, c in enumerate(chs, 1):
            t, cw = c.get("text") or "", f"{where} c{j}"
            words += nwords(t)
            if pres and nwords(t) > PRES_CHAPTER_WORDS:
                P.append(f"{cw}: {nwords(t)} words: one take of the presenter is at most 15 s, so at most {PRES_CHAPTER_WORDS} words (split the chapter)")
            if pres and c.get("cam") not in (None,) + CAMS:
                P.append(f"{cw}: cam {c.get('cam')!r} (one of {', '.join(CAMS)})")
            if pres and c.get("scene") and c["scene"] not in scene_ids:
                P.append(f"{cw}: scene {c['scene']!r} is not one of the project's presenter scenes {scene_ids}")
            if not 1 <= len(sents(t)) <= MAX_SENTENCES or nwords(t) > MAX_CHAPTER_WORDS or not t:
                P.append(f"{cw}: {len(sents(t))} sentences / {nwords(t)} words (1-{MAX_SENTENCES} / at most {MAX_CHAPTER_WORDS}): one voice take")
            if c.get("kind") not in ("point", "proof", "objection", "offer"):
                P.append(f"{cw}: kind {c.get('kind')!r}")
            if U.FIRST.search(t):
                P.append(f"{cw}: first person: the voice talks to the viewer in 'you' form, it never tells a customer's own experience")
            if re.search(r"(?:^|\s)\d\.\s|\bnumber (?:one|two|three|four)\b", t, re.I) and c.get("number"):
                P.append(f"{cw}: the chapter number is added by the video: do not write it in the text")
            for s in sents(t):
                if re.sub(r"\W+", " ", s.lower()).strip() in old_sents and nwords(s) > 4:
                    W.append(f"{cw}: an earlier batch already said: {s!r}")
            show = c.get("show") or []
            if not show:
                P.append(f"{cw}: show: the tags of the picture this line needs (footage_index.TAGS)")
            for tg in show:
                if tg not in footage_index.TAGS:
                    P.append(f"{cw}: show tag {tg!r} is not in the vocabulary")
                elif cov and cov.get(tg, [0])[0] < MIN_MOMENTS and c.get("kind") != "offer":
                    W.append(f"{cw}: only {cov.get(tg, [0])[0]} good footage moments show '{tg}' for {pr['name']}: the picture may not match")
            items += [dict(where=cw, text=t, source="ours")] + ([dict(where=f"{cw} tag", text=c["tag"], source="ours")] if c.get("tag") else [])
        if chs and (chs[-1].get("kind") != "offer" or "Tap the link below." not in (chs[-1].get("text") or "")):
            P.append(f"{where}: the last chapter must be kind offer and end with 'Tap the link below.'")
        if chs and sum(c.get("kind") == "offer" for c in chs) != 1:
            P.append(f"{where}: exactly one offer chapter, the last")
        wr = PRES_WORDS if pres else WORDS
        if chs and not wr[0] <= words + nwords(hooks[0]["text"] if hooks else "") <= wr[1]:
            P.append(f"{where}: {words} words in all: a 55-80 s video needs {wr[0]}-{wr[1]} (about {'2.5' if pres else '3.1'} words a second)")
    if story and projs:          # the batch (owner 2026-10-27): other stories, other lead features, one presenter
        for f, ps in leads.items():
            if len(ps) > 1:
                P.append(f"videos: {', '.join(ps)} all lead with {f}: each video leads with a different feature")
        stl = [p.get("structure") for p in projs]
        for x in sorted({x for x in stl if x and stl.count(x) > 1}):
            P.append(f"videos: the structure {x!r} is used {stl.count(x)} times: each video a different story shape")
        last = set(novelty.recent(pr["name"], "structure", last=1, log=nl))
        for p in projs:
            if p.get("structure") in last:
                P.append(f"{p.get('id')}: the structure {p['structure']!r} was in {pr['name']}'s last batch: pick another or invent one")
        n_pres = sum(1 for p in projs if p.get("presenter"))
        if len(projs) >= 2 and not n_pres and not sheet.get("no_presenter"):
            P.append("videos: one project of a batch of 2+ carries the presenter (owner 2026-10-27, about 225 credits); when the request says "
                     "no presenter, set \"no_presenter\": \"<its words>\"")
        elif n_pres > 1:
            W.append(f"videos: {n_pres} presenter projects (about 225 credits each): only when the request names that many")
    allowed = sorted({(int(m.group(1)) if m.group(1).isdigit() else compliance.ONES[m.group(1).lower()])
                      for i_ in items for m in compliance.COUNT_WORD.finditer(i_["text"])})      # ('Five things ...': a count the video shows, not a stat)
    for k, s in enumerate(stats, 1):
        sid = f"{s.get('id') or '?'}"
        if s.get("layout") not in LAYOUTS:
            P.append(f"{sid}: layout {s.get('layout')!r} (one of {', '.join(LAYOUTS)})")
        elif s.get("layout") in SALE_LAYOUTS and not (camp and camp.get({"gifts": "gifts", "bundle": "bundle_any"}[s["layout"]])):
            P.append(f"{sid}: layout {s['layout']!r} needs a sale campaign with {'free gifts' if s['layout'] == 'gifts' else 'a 2-3 bag bundle'} "
                     f"running for the theme (campaign.py: none for {sheet.get('theme')!r} today)")
        if s.get("project") not in seen_ids:
            P.append(f"{sid}: project {s.get('project')!r} is not in the sheet")
        if len(str(s.get("idea") or "")) < 10:
            P.append(f"{sid}: idea: the creative idea in one sentence")
        for key in ("headline", "kicker", "sub", "badge"):
            if s.get(key):
                items.append(dict(where=f"{sid} {key}", text=s[key], source="ours"))
        if nwords(s.get("headline") or "") > 8:
            P.append(f"{sid}: headline over 8 words")
        if s.get("layout") == "concept":
            sc = s.get("scene") or {}
            pt = sc.get("prompt") or ""
            if len(pt) < 60 or sc.get("kind") not in ("object", "worn", "hand"):
                P.append(f"{sid}: scene: kind (object|worn|hand) and a prompt of at least 60 characters")
            if FACE_WORDS.search(re.sub(r"\b(?:no|nobody|not|without|never|neither)\b[^.;]{0,50}?\b(?:face|faces|eyes|mouth|portrait)\b", "", pt, flags=re.I)):
                P.append(f"{sid}: the scene prompt asks for a face / eyes / sunglasses / a mannequin: the picture has no face at all "
                         f"(a person is cropped at the shoulders; sunglasses fool the face check)")
            if not re.search(r"empty|clear|calm|space|negative", pt, re.I):
                W.append(f"{sid}: the prompt does not leave the {s.get('where') or 'bottom'} of the frame empty: the words would land on the bag")
            for key in ("headline", "kicker", "sub", "pill", "badge"):
                pass
        if s.get("layout") == "ad":
            ad_problems(s, sid, lib, P, W, items)
        if s.get("pill") not in (None, True, False):
            P.append(f"{sid}: pill is true or false (the offer's % pill); a custom text goes in badge")
    ads = [s for s in stats if s.get("layout") == "ad"]
    if ads:                 # every batch new formats (owner 2026-10-26): once a batch, not the last batch's, some of the strategist's own
        fm = [s.get("format") for s in ads]
        for f in sorted({x for x in fm if x and fm.count(x) > 1}):
            P.append(f"statics: the format {f!r} is used {fm.count(f)} times: each ad static a different format")
        last = set(novelty.recent(pr["name"], "format", last=1, log=nl))
        for s in ads:
            if s.get("format") in last:
                P.append(f"{s.get('id')}: the format {s['format']!r} was in {pr['name']}'s last batch: pick another or invent one")
        ever = set(novelty.recent(pr["name"], "format", last=novelty.KEEP, log=nl))
        own = [s for s in ads if s.get("format") not in lib and s.get("format") not in ever]
        need_ = max([k for n_, k in NEW_FORMATS if len(ads) >= n_] or [0])
        if len(own) < need_:
            P.append(f"statics: {len(own)} format(s) of your own among {len(ads)} ad statics, at least {need_} needed: invent a new format "
                     f"(an id not in data/static_formats.json, format_name, art, people) that no earlier batch used")
        old_caps = {re.sub(r"\W+", " ", c.lower()).strip() for c in novelty.recent(pr["name"], "caption", last=novelty.KEEP, log=nl)}
        for s in ads:
            h = re.sub(r"\W+", " ", ad_headline(s).lower()).strip()
            if h and h in old_caps and h.removeprefix("the ") != re.sub(r"\W+", " ", pr["name"].lower()).strip():   # (the name alone may repeat)
                P.append(f"{s.get('id')}: the line {ad_headline(s)!r} was on a static of an earlier batch: new words")
    if stats:
        n_ai = sum(s.get("layout") in ("concept", "ad") for s in stats)
        W.append(f"{n_ai} AI statics of {len(stats)} ({len(ads)} designed ads, {n_ai - len(ads)} studio scenes; about {n_ai} credits plus retries)")
        heads = [re.sub(r"\W+", " ", ((ad_headline(s) if s.get("layout") == "ad" else s.get("headline")) or "").lower()).strip()
                 for s in stats if s.get("headline") or s.get("layout") == "ad"]
        for h in {x for x in heads if heads.count(x) > 1}:
            P.append(f"statics: the headline {h!r} is used twice")
    C = compliance
    try:
        P += [f"compliance {p['category']} {p['term']!r} in {p['where']}: {p['text']}" for p in
              C.check(items, ctx=C.context(pr), allowed_numbers=allowed)]
    except Exception as e:  # noqa: BLE001
        W.append(f"compliance could not run ({type(e).__name__}: {e}): plan runs it again")
    return P, W


# ------------------------------------------------------------------ the sheet -> scripts for make_batch
def scripts(sheet, pr, hooks=4):
    """ugc_script-compatible scripts [{id, index, angle, hook, alt_hooks, chapters, words, est_seconds, offer, claims, numbers, ...}] of the
    sheet's projects, in order (what ugc_script.scripts returns, so make_batch's board builder takes them unchanged)."""
    import shotmatch
    import ugc_script as U
    ctx = U.context(pr)
    slib = structures()["structures"]
    out = []
    for i, p in enumerate(sheet["projects"]):
        beats = {b["id"]: b for b in (slib.get(p.get("structure") or "") or {}).get("beats") or []}

        def hook(h):
            return dict(U.H(h["text"].strip(), h["type"], h["label"].strip().upper(), None), show=list(h.get("show") or []),
                        **({"scene": h.get("scene")} if p.get("presenter") and h.get("scene") else {}))
        hs = [hook(h) for h in p["hooks"][:max(hooks, 1) + 0]] if hooks else [hook(p["hooks"][0])]
        chs = []
        for j, c in enumerate(p["chapters"], 1):
            show = list(c.get("show") or [])
            kw = list(dict.fromkeys(sorted(shotmatch.fold(show))))[:4]
            kw = kw if len(kw) >= 2 else (kw + [w for w in sorted(words_of(c["text"])) if w not in kw])[:2]
            ch = U.chapter(c["text"].strip(), c["kind"], None, c.get("number"), None, kw=kw,
                           keywords=[w.lower() for w in c.get("highlight") or [] if w.lower() in c["text"].lower()][:3])
            ch.update(id=f"c{j}", tag=(c.get("tag") or None), feature=(c.get("tag") or None), show=show)
            if c.get("proof_shot"):           # the shot that proves the line: held 2-3 s, the clip's own sound (storyboard)
                ch["proof"] = True
            if c.get("beat"):
                ch["beat"] = c["beat"]
            pace = c.get("pace") or (beats.get(c.get("beat") or "") or {}).get("pace")
            if pace in ("slow", "fast"):      # the beat's shot length (storyboard: slow ~2.4 s, fast ~1.6 s)
                ch["pace"] = pace
            if p.get("presenter"):
                ch.update(cam=c.get("cam") or "open", **({"scene": c["scene"]} if c.get("scene") else {}))
            chs.append(ch)
        sc = U.finish(ctx, dict(id=f"U{i + 1:02d}", index=i, angle=p["slug"], voice="you", product=pr.get("key"), hook=hs[0],
                                alt_hooks=hs[1:], chapters=chs))
        sc.update(title=p["title"], idea=p["big_idea"], from_sheet=True, **({"structure": p["structure"]} if p.get("structure") else {}))
        if p.get("presenter"):
            sc["presenter"] = p["presenter"]
        out.append(sc)
    return out


def concept_scenes(sheet):
    """The sheet's AI statics in order (the studio scenes and the designed ads): [(index in statics, static dict)]."""
    return [(i, s) for i, s in enumerate(sheet.get("statics") or []) if s.get("layout") in ("concept", "ad")]


# ------------------------------------------------------------------ the packet the strategist reads
def past(pr):
    """Lines about every earlier batch of the product: ledger (id, folder, ads) and the novelty log (angles, hooks, statics, scenes)."""
    import ledger
    import novelty
    out = []
    for b in ledger.load()["batches"]:
        if b["product"].lower() == pr["name"].lower():
            out.append(f"- {ledger.bid(b['n'], b.get('rev'))} {b['date']} {b.get('theme') or ''} {b.get('statics')} statics + "
                       f"{b.get('projects')} projects ({b['status']})")
    nl = novelty.load()
    for b in novelty.batches(pr["name"], log=nl)[-6:]:
        out.append(f"\n  Batch '{b.get('name')}' ({b.get('date')}):")
        for v in b.get("videos") or []:
            if v.get("chapters"):
                out.append(f"    video angle {v.get('angle')}{' (structure ' + v['structure'] + ')' if v.get('structure') else ''}: "
                           f"hook {v.get('hook')!r}; lines: " +
                           " / ".join(c[:70] for c in v["chapters"][:3]) + " ...")
            elif v.get("hook"):
                out.append(f"    hook version: {v['hook']!r} ({v.get('hook_type')})")
        st = [f"{s.get('layout')}: {s.get('caption') or s.get('headline') or ''}".strip(": ") for s in b.get("statics") or []]
        if st:
            out.append("    statics: " + "; ".join(dict.fromkeys(st))[:400])
        sc = sorted({s.get("scene") for s in b.get("statics") or [] if s.get("scene")})
        if sc:
            out.append("    AI scenes used: " + ", ".join(sc))
        fm = sorted({s.get("format") for s in b.get("statics") or [] if s.get("format")})
        if fm:
            out.append("    AI ad formats used: " + ", ".join(fm))
    return "\n".join(out) or "(nothing yet)"


def packet(pr, theme, n_projects, n_statics, request=""):
    import ugc_script as U
    camp = sale_campaign(theme)
    ctx = U.context(pr)
    V = ctx["V"]
    cov = coverage(pr)
    L = [f"# Strategy packet: {pr['name']} · {theme or 'evergreen'} · {n_projects} projects + {n_statics} statics",
         f"\nRequest: {request or '-'}\n",
         "You are the creative strategist for this batch. Write NEW ideas (not the engine's templates, not an earlier batch's), complete "
         "scripts and static concepts, check them with `ideas.py check`, then plan with `--ideas`. Format: see `ideas.py --help`.\n",
         "## 1. True facts (the only claims you may make)\n"]
    L += [f"- Offer: {V['P'] or '-'} off ({V['off_sp'] or '-'}), gift: {V['gift'] or 'none'}, price {V['price'] or '-'} (was {V['was'] or '-'}); "
          f"shipping: {'free US shipping' if ctx['ship'] else 'not stated: do not mention'}; warranty: {V['warranty'] or '-'}; returns: {V['returns'] or '-'}"]
    L += [f"- Feature: **{f[1]}**: {f[0]}" for f in pr.get("features") or []]
    L += [f"- Colours: {', '.join(pr.get('colours') or []) or ((pr.get('facts') or {}).get('colours') and ', '.join(pr['facts']['colours'])) or '-'}",
          "- Bag colours in packshots: see the plan's colour list (scene.colour picks the packshot used as the reference).",
          "- Never: invented customer experiences ('I bought', 'my bag'), health / medical claims, prescription drugs, politics, religion, "
          "blood / violence, a % or gift the offer does not say, fake urgency (a countdown, 'only 3 left', a sale end date nobody confirmed), "
          "'theft-proof' or other absolutes (anti-theft design is fine).",
          "- Voice: one voice talking to the viewer ('you'), 185-215 words a minute; a hook of at most 14 words in the first 3 s; "
          "the offer last, ending 'Tap the link below.'; no review chapters or review cards in the videos (owner 2026-10-21)."]
    if camp:
        L += [f"\n### The sale running now: {camp['name']} ({camp['from']} to {camp['until']}; client-approved: {camp['approved'][:160]} ...)\n",
              "These are true and may be said (they are the client's own words); the bag's own % above stays its offer: 'up to 60% off' "
              "is fine, '60% off' only as the facts below allow, never '60% off the " + pr["name"] + "' unless it is that bundle. The end "
              f"cards already say '{camp['end_title']}' + '{camp['end_pill']}'; the offer chapter may add the sale (e.g. '{camp['close']}'); "
              "the end date (30 November) is confirmed, so 'the sale ends on the thirtieth of November' is true.\n"]
        L += [f"- {x}" for x in camp["facts"]]
        L += [f"- Gift: {g['name']} (worth ${g['worth']:.2f}) with {g['with']}{'+' if g['with'] > 2 else ''} bags" for g in camp["gifts"]]
        L += [f"- What the client wants now: {camp.get('client_ideas') or '-'}"]
    L += ["\n### What converts for Libra (owner + data, 2026-10-26: read before you write)\n",
          "- The account's money comes from people telling a true story to camera (the ACH creator winners: 123-H4 205 orders, 147-H1 183, "
          "CTR 5-10%); faceless voice-over-b-roll videos mostly lose. Prefer the presenter (a host, never a customer) or a person in the "
          "footage doing something, and a story-like structure (a situation, the problem, what the bag does about it, the sale).",
          "- Every project a DIFFERENT concept (person, setting, opening, format, emotion): Meta groups look-alike ads and they share "
          "delivery, so four similar videos count as one. Never the same structure twice in a batch.",
          "- Open with a reason to buy this bag in the first 2 seconds, shown not told (a hand that can't reach the back pocket, the zip "
          "closing, what fits, two ways to carry); the sale is the close. Every brand opens with '50% off' in November: we don't.",
          "- Sell the 3-Piece Set where it fits (the Hobo Bag page offers it as the 'Best Value' upgrade; its ads ran at ROAS ~3 with a "
          "bigger basket): three pieces for one price.",
          "- No exact prices in new lines or statics while the owner tests a price change: say the % ('50% off', 'up to 60% off').",
          "- Statics: one idea each, few words, the bag big; most should be AI ads (the AI ads 'seem to be starting to work': owner): "
          "the `ad` formats of section 5, each batch new ones, realistic, never the same look twice."]
    sl = structures()
    import novelty as NV
    last_s = NV.recent(pr["name"], "structure", last=1)
    L += ["\n### The videos are stories (owner 2026-10-27: 'go ahead'; B025 / B027 were feature lists in costumes: every project walked "
          "through the same five features)\n"] + [f"- {x}" for x in sl["rules"]] + [
          f"- One project of a batch of 2+ carries the presenter (owner 2026-10-27: one a batch, about 225 credits); the request saying "
          f"no presenter: \"no_presenter\": \"<its words>\" in the sheet.",
          f"- Structures the product's last batch used (not this batch): {', '.join(last_s) or 'none'}. Invent one when none fits "
          f"(structure id of your own, structure_name, shape).",
          "\nThe story structures (data/story_structures.json; each chapter names its `beat`, the beats in this order):\n"]
    for x in sl["structures"].values():
        L.append(f"- `{x['id']}` {x['name']}: {x['shape']} Beats: " + " -> ".join(
            b["id"] + ("*" if b.get("required") else "") + (" (proof)" if b.get("proof") else "") for b in x["beats"]) +
            f". E.g. {x.get('example', '')}")
    L += ["(* = required; (proof) = the beat that usually carries the proof shot)"]
    L += ["\n## 2. What the footage library can SHOW (good, face-free moments per tag; the picture of each line is chosen from these)\n"]
    for tag, (n, ex) in sorted(cov.items(), key=lambda kv: -kv[1][0]):
        L.append(f"- `{tag}`: {n}" + (f"  (e.g. {'; '.join(ex)})" if ex else ""))
    if not cov:
        L.append("(no labelled footage for this product: its videos use its photos and its few clips)")
    L += ["\nA tag with fewer than 4 moments is thin: build the line on something the footage shows more of, or the picture will not match.",
          "\n## 3. What earlier batches did (do not repeat their ideas, hooks, lines, scenes)\n", past(pr),
          "\n## 4. Research notes (read them: docs/research/*.md; the facts above beat them)\n"]
    rd = os.path.join(os.path.dirname(HERE), "docs", "research")
    for f in sorted(os.listdir(rd)) if os.path.isdir(rd) else []:
        L.append(f"- docs/research/{f}")
    fl = formats()
    import novelty
    last_f = novelty.recent(pr["name"], "format", last=1)
    ever_f = novelty.recent(pr["name"], "format", last=novelty.KEEP)
    L += ["\n## 5. The statics (4:5, 1080x1350)\n",
          "**AI-designed ads first** (owner 2026-10-26, after the test sheet: 'i like 2, 3, 4, 6 (make it realistic), 7, 8 (make it more "
          "realistic) ... make them unique each time we run a batch ... new ideas and new formats that follow Meta guidelines'): layout `ad` = "
          "Higgsfield designs the WHOLE ad from the real packshot, picture and words (gpt_image_2_5 sets short text correctly; the gate reads "
          "it back). About two thirds of the statics are `ad`, each a DIFFERENT format and idea; the rest real (studio / native / quotes / "
          "value / stars) or `concept`. Each batch at least one format of your own (two with 6+ ad statics): a new id with format_name, "
          "art (the art direction: what kind of picture, the layout, the type) and people. Realistic beats glossy: a format that is a "
          "photo must look like a real photo (real light, real textures, a candid angle), never CGI.",
          f"Formats the product's last batch used (not this batch): {', '.join(last_f) or 'none'}; used before: {', '.join(ever_f) or 'none'}.",
          "\nThe format library (data/static_formats.json; ★ = the owner liked it on the test sheet):\n"]
    for f in fl["formats"].values():
        L.append(f"- `{f['id']}`{' ★' if f.get('liked') else ''} {f['name']} (people: {f['people']}, at most {f['words']} words): "
                 f"{f.get('words_hint') or ''}" + (f"; e.g. {' / '.join(f['example'])}" if f.get("example") else "") +
                 (f"; {f['bag']}" if f.get("bag") else ""))
    L += ["\nMeta's rules for the ads (the check refuses what breaks them):\n"] + [f"- {x}" for x in fl["meta"]]
    L += ["- Keep the bag closed (no photo of its inside: the AI would invent one); a feature label only for what the reference shows "
          "(the back pocket needs the back view: scene.ref).\n",
          "Other layouts: `concept` = an AI studio scene of the REAL bag (made in Higgsfield from the real packshot, gated against it) with at most a "
          "kicker, a serif headline, a sub-line and the % pill; `studio` = the real packshot large on a tinted backdrop; `native` = a real "
          "face-free footage frame; `quotes` / `stars` = verbatim reviews; `value` = the real price struck through; `offer`; `colours`; `checklist`" +
          (("; while the sale runs: `gifts` = the bag with the free gifts (their real photos) and one line per tier" if camp.get("gifts") else "")
           + ("; `bundle` = 2-3 colours side by side with the bundle % pill" if camp.get("bundle_any") else "") + "." if camp else "."),
          "Concept scenes: premium, realistic, shot like a campaign: the bag is the hero, large, with props that belong to the idea "
          "(a latte, keys, a notebook, gift boxes, a chair), the bag fully visible; leave the end where the words go EMPTY (calm surface, nothing "
          "on it); never a face, eyes, sunglasses, a mannequin or a person even blurred in the background (a person is cropped at the shoulders "
          "or seen from behind); no text or logos in the picture (the words are set on it). One idea per static, a different scene each time.",
          "Mix: about two thirds `ad` (each a different format), the rest real photos (studio / native / value / quotes) or `concept`."]
    L += ["\n## 6. Output\n", "Write `ideas.json` (format in `ideas.py --help`): per project a big idea, why it is new, 4 hooks of different types, "
          "5-11 chapters each with `show` tags, the offer last; per static its concept. Then run `ideas.py check`."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ the sheet for people (Drive: strategy_sheet.md / .csv)
def sheet_md(sheet, scripts_=None):
    L = [f"# Strategy sheet: {sheet.get('product')} · {sheet.get('theme') or 'evergreen'} · {sheet.get('date') or ''}\n"]
    L += ["## Research and what it changed\n"] + [f"- {x}" for x in sheet.get("research") or []] + [""]
    for p in sheet.get("projects") or []:
        L += [f"## {p['id']} · {p['title']}", f"**Big idea:** {p['big_idea']}", f"**Why it is new:** {p['why_new']}\n", "**Hooks (4 versions, same body):**"]
        for k, h in enumerate(p["hooks"][:4], 1):
            L.append(f"- H{k} [{h['type']}] `{h['label']}`: {h['text']}  _(picture: {', '.join(h.get('show') or []) or '-'})_")
        pres = p.get("presenter")
        if pres:
            L += ["", f"**Presenter ({pres['id']}, a generated host, never a customer):** " +
                  "; ".join(f"{x['id']}: {x['where'].strip()}" for x in pres.get("scenes") or [])]
        L += ["", "**Script:**\n", "| # | " + ("Said by the presenter | On camera | " if pres else "Voice | ") + "Picture it needs | On screen |",
              "|---|---|---|---|" + ("---|" if pres else "")]
        for j, c in enumerate(p["chapters"], 1):
            L.append(f"| {j} | {c['text']} | " + (f"{c.get('cam') or 'open'} | " if pres else "") +
                     f"{', '.join(c.get('show') or [])} | {(str(c['number']) + '. ' if c.get('number') else '') + (c.get('tag') or '')} |")
        w = sum(nwords(c["text"]) for c in p["chapters"]) + nwords(p["hooks"][0]["text"])
        L += [f"\n_{w} words, about {round(w / (2.55 if pres else 3.08))} s._\n"]
        sts = [s for s in sheet.get("statics") or [] if s.get("project") == p["id"]]
        if sts:
            L += ["**Statics:**\n", "| # | Look | Idea | Words |", "|---|---|---|---|"]
            for s in sts:
                words = " · ".join(x for x in (s.get("kicker"), s.get("headline"), s.get("sub"), "50% pill" if s.get("pill") else "", s.get("badge")) if x)
                look = s["layout"] + (" (AI scene: " + s["scene"]["kind"] + ")" if s["layout"] == "concept" else "")
                if s["layout"] == "ad":
                    fmt = ad_format(s)
                    look, words = f"AI ad: {fmt.get('name')}{' (new format)' if fmt.get('new') else ''}", " / ".join(s.get("words") or [])
                L.append(f"| {s['id']} | {look} | {s['idea']} | {words or '-'} |")
            L.append("")
    return "\n".join(L) + "\n"


def sheet_csv(sheet, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["project", "title", "kind", "id", "text / idea", "picture it needs", "on screen", "scene prompt"])
        for p in sheet.get("projects") or []:
            for k, h in enumerate(p["hooks"][:4], 1):
                w.writerow([p["id"], p["title"], f"hook H{k} ({h['type']})", f"{p['id']}H{k}", h["text"], ",".join(h.get("show") or []), h["label"], ""])
            for j, c in enumerate(p["chapters"], 1):
                w.writerow([p["id"], p["title"], f"script {c['kind']}", f"{p['id']}c{j}", c["text"], ",".join(c.get("show") or []),
                            ((str(c["number"]) + ". ") if c.get("number") else "") + (c.get("tag") or ""), ""])
        for s in sheet.get("statics") or []:
            w.writerow([s.get("project"), "", f"static {s['layout']}" + (f" {s.get('format')}" if s["layout"] == "ad" else ""), s["id"], s["idea"], "",
                        " / ".join(s.get("words") or []) if s["layout"] == "ad" else
                        " · ".join(x for x in (s.get("kicker"), s.get("headline"), s.get("sub")) if x), (s.get("scene") or {}).get("prompt", "")])


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pk = sub.add_parser("packet")
    pk.add_argument("--product", required=True)
    pk.add_argument("--theme", default="")
    pk.add_argument("--projects", type=int, default=5)
    pk.add_argument("--statics", type=int, default=20)
    pk.add_argument("--request", default="")
    pk.add_argument("--out", required=True)
    pk.add_argument("--products-dir")
    ck = sub.add_parser("check")
    ck.add_argument("sheet")
    ck.add_argument("--product")
    ck.add_argument("--projects", type=int)
    ck.add_argument("--statics", type=int)
    ck.add_argument("--products-dir")
    sh = sub.add_parser("sheet")
    sh.add_argument("sheet")
    sh.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "packet":
        pr = product_of(a.product, a.products_dir)
        os.makedirs(a.out, exist_ok=True)
        txt = packet(pr, a.theme, a.projects, a.statics, a.request)
        open(os.path.join(a.out, "strategy_packet.md"), "w").write(txt)
        print(txt)
        return 0
    sheet = load(a.sheet)
    if a.cmd == "check":
        pr = product_of(a.product or sheet["product"], a.products_dir)
        P, W = check(sheet, pr, a.projects, a.statics)
        for w in W:
            print("warning:", w)
        for p in P:
            print("PROBLEM:", p)
        print(f"{len(P)} problem(s), {len(W)} warning(s)")
        return 1 if P else 0
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "strategy_sheet.md"), "w").write(sheet_md(sheet))
    sheet_csv(sheet, os.path.join(a.out, "strategy_sheet.csv"))
    print(f"strategy_sheet.md / .csv in {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

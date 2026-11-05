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
    "story": "problem_fix|moment|proof|gift|value|ways"  (what it tells next to the offer: data/static_formats.json 'stories'; sheets from
             2026-11-04, the layouts ad / concept / studio / native), "feature": "GOLD SIDE ZIPS"  (the product's feature tag the story is
             about: problem_fix / moment / proof / ways),
    "scene": {"kind": "object|worn|hand", "colour": "Black", "prompt": "the scene: surface, props, light, composition (no people / faces)"},
    "motion": "steam rises from the latte, sunlight flickers through the window"  (optional, concept object scenes only, at most 6 a batch:
              a MOTION STILL: the scene also becomes a 5 s silent loop, Kling 3.0 pro from the still, ~9 credits, our words over it;
              only what is around the bag moves: never the bag, a person or a hand)
 }, {
    "id": "S02", "project": "P02", "layout": "ad", "idea": "...",
    "format": "magazine_cover"  (data/static_formats.json) | "<a new id>" with "format_name": "...", "art": "the art direction (>= 60 chars)",
              "people": "none|behind|cropped"  (a format of your own: invent one every batch),
    "words": ["LIBRA", "THE BAG THAT ZIPS SHUT", "EARLY BLACK FRIDAY: 50% OFF"]  (the exact words the AI sets in the picture, 1-4 lines),
    "headline": "the line the ad copy and the tracker name (default: the first line that is not LIBRA)",
    "scene": {"colour": "Burgundy", "ref": "optional site photo (a back view)", "prompt": "what the picture shows: setting, props, light"}
 }]
}
STORY statics (layout "story", 2026-11-04 "very basic, not top tier"): the layered anatomy of the DTC statics that keep running,
set by our renderer in exact type over the photo of the moment (brand_statics.l_story):
    {"id": "S03", "layout": "story", "look": "hook|quote|list|versus|stack", "story": "problem_fix", "feature": "GOLD SIDE ZIPS",
     "idea": "...", "kicker": "EARLY BLACK FRIDAY" (optional), "hook": "Keys at the bottom of your bag again?" (3-10 words),
     "highlight": ["keys"] (hook words on a marker), "sub": "Two gold side zips keep them in reach." (hook look: the answer),
     "points": ["...", "...", "..."] (list: 3 reasons; stack: 3-4 things you get), "them": "Open tote", "us": "Hobo Bag",
     "rows": [["Open top", "Zips shut"], ...] (versus: 3-4), "review": 12 (one of the product's reviews.json numbers: the proof),
     "review_text": "a verbatim part of it" (optional), "scene": {"kind": "worn", "colour": "Grey", "prompt": "the moment of the hook"}
     (optional: without it a real footage frame is the photo)}
  hook: the photo full bleed, the hook big at the top, the answer, a review card, the % sticker (+ the gift tag) in the calmer corner;
  quote: the customer's own words as the headline (a big gold quote mark, stars, her name), the sticker top right; list: the photo
  above, a deep panel with the hook and 3 numbered reasons, a proof line; versus: the photo with the hook, a cream panel them vs us
  (crosses / ticks); stack: the photo with the hook, a cream panel with the % huge and what you get as ticks. The words are the
  sheet's, the review is verbatim, the % and the gift are the product's.
The words of the scene prompt are only the scene: the keep-the-real-bag text, the style and the no-face rule are added by ai_gen.
OFFER + STORY (Wouter and the team 2026-11-04; sheets from that day on): every static shows the product's offer (an ad's words carry the
% as a hero element, a concept `pill: true`, real statics the % badge) AND tells a story: one line of 3+ words that says why to buy (the
ad's first line that is not the offer, the masthead or the bag's name; a concept / studio / native headline), its `story` type and, for a
feature story, its `feature`; at least 3 story types a batch (2 under 6 statics), none on more than 40%, no feature on more than a third,
at most one `offer` / `colours` static (they tell none).
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

LAYOUTS = ("ad", "story", "concept", "studio", "native", "quotes", "value", "offer", "stars", "colours", "checklist", "gifts", "bundle")
SALE_LAYOUTS = ("gifts", "bundle")                   # only while a sale campaign runs (campaign.py): its free gifts / 2-3 bags together


def sale_campaign(theme, day=None):
    """The store-wide sale campaign a batch of this theme gets (campaign.py), and compliance told about it; None when none runs."""
    import campaign
    import compliance
    c = campaign.active(mb().pick_theme(theme or ""), day)
    compliance.use_campaign(c)
    return c
HOOK_TYPES = ("promise", "superlative", "question", "problem", "price")
MAX_MOTION = 6                                         # motion stills a batch at most (ai_gen.MAX_MOTION; ~9 credits each)
MOTION_PEOPLE = re.compile(r"\b(?:woman|women|man|men|person|people|girl|she|he|her|his|hands?|fingers?|face|someone|somebody)\b", re.I)
MOTION_BAG = re.compile(r"\b(?:bags?|handbags?|hobo|purses?|zips?|zippers?|straps?|pouch)\b", re.I)   # (the motion line never names the bag)
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
NEW_FORMATS = ((3, 1),)                               # (ad statics in the batch, formats of your own it needs at least: one; owner
#                                                       2026-11-04: the offer and a design that sells beat novelty for its own sake)
OFFER_FROM = "2026-11-04"                              # Wouter 2026-11-04 'don't have the offer on it': every static shows the offer
STATIC_STORY_FROM = "2026-11-04"                       # the team 2026-11-04 on the 9 offer-led samples ('story is not enough'):
#                                                       every static tells a story next to the offer (ideas.check, sheets from this day)
STORY_LAYOUTS = ("ad", "story", "concept", "studio", "native")   # the layouts whose words the strategist writes: each names its story
STORY_LOOKS = ("hook", "quote", "list", "versus", "stack")   # layout `story` (brand_statics.l_story): the long-running DTC static anatomy
STORY_SELF = {"quotes": "proof", "stars": "proof", "checklist": "proof", "value": "value", "bundle": "value", "gifts": "gift"}  # (their own reason)
NO_STORY = ("offer", "colours")                        # the offer / the colours alone: at most one a batch
NAME_ONLY = re.compile(r"^\W*(?:the|your|a|an)?\s*(?:[\w'’-]+\s+){0,2}(?:hobo|bag|handbag|set|tote|purse|crossbody|satchel)\W*$", re.I)


def product_pct(pr):
    """The product's own % (its offer badge: 50 for the Hobo Bag, 60 for the 3-Piece Set); None when it has no % offer."""
    d = re.sub(r"\D", "", str((((pr.get("offer") or {}).get("badge") or {}).get("big")) or ""))
    return int(d) if d and 5 <= int(d) <= 90 else None


def offer_shown(text, pct):
    """Does a printed line carry the offer ('50% OFF', '50%', 'fifty percent', 'half price' for 50)?"""
    t = (text or "").lower()
    return bool(re.search(rf"\b{pct}\s?%|\b{pct} ?percent\b", t) or (pct == 50 and re.search(r"\bhalf[- ]price\b", t)))
STORY_FROM = "2026-10-27"                            # the story rules (owner 2026-10-27) check sheets from this day on
STORY_MAX_FEATURES = 3                               # features one video may talk about
PROOF_TAGS = {"zip", "zip_hand", "side_zip", "snap", "lock", "pocket", "packing", "strap", "tie", "inside"}   # a movement the shot proves
PEOPLE_TAGS = {"worn", "walking"}                    # the bag on a person
STILL_TAGS = {"hero", "placed", "colours"}           # the bag just sitting there: never a hook's opening picture
PRICE_WORDS = re.compile(r"\d+\s?%|\bpercent\b|\bhalf[- ]price\b|\bsale\b|\bblack friday\b|\bcyber monday\b|\bdiscount\w*|\$\s?\d|"
                         r"\bbundles?\b|\bprices?\b|\bfree (?:gifts?|shipping|pouch|wallet|jewell?e?ry)", re.I)


def formats():
    """data/static_formats.json: {"meta": [rules], "formats": {id: format}, "stories": {id: story type}} (the AI-designed ad formats and
    the static stories, ideas.py / ai_gen.py)."""
    try:
        d = json.load(open(os.path.join(HERE, "data", "static_formats.json")))
    except (OSError, ValueError):
        d = {}
    return dict(meta=d.get("meta") or [], formats={f["id"]: f for f in d.get("formats") or []},
                stories={x["id"]: x for x in d.get("stories") or []})


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


def offer_word_ok(text, pr):
    """Does the offer chapter say the product's % the way the offer card waits for it ('50%', '50 percent', 'fifty')? None: no %."""
    import new_product
    pct = re.sub(r"\D", "", str((((pr.get("offer") or {}).get("badge") or {}).get("big")) or ""))
    if not pct:
        return None
    sp = new_product.say(int(pct)).split("-")[0]
    return bool(re.search(rf"\b{pct}\s?%|\b{pct} percent|\b{sp}\b", (text or "").lower()))


SOFT_OPEN_FROM = "2026-11-05"    # (Julian 2026-11-04 on B028 P02: "I would not introduce with Black Friday immediately ... a UGC video has to look
#                                  less aggressive") sheets from this day: the lead hook (H1, the version a single video keeps) and every hook
#                                  of a presenter project open on the story, never the sale or the price


def story_problems(p, pid, pr, cov, keys, slib, P, W, date=""):
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
    if pres and priced and not (_rules("presenter") or {}).get("offer_hook", False):
        P.append(f"{pid}: hooks {', '.join(f'H{k}' for k in priced)} open the presenter's video on the sale: a UGC host does not open "
                 f"with Black Friday or the % (Julian 2026-11-05: 'less aggressive'; B028 P02 H4 'Black Friday prices are live now' had the "
                 f"project's lowest hook rate, 33%); open on the moment, the sale is the close")
    if len(priced) > 1:
        P.append(f"{pid}: hooks {', '.join(f'H{k}' for k in priced)} open on the price: one price hook at most, the others a moment or a question")
    if (date or "") >= SOFT_OPEN_FROM:
        soft = priced if pres else [k for k in priced if k == 1]
        if soft:
            P.append(f"{pid}: {'hooks ' + ', '.join(f'H{k}' for k in soft) if pres else 'H1'} open on the sale or the price: "
                     f"{'a presenter video' if pres else 'the lead hook'} opens on the story (Julian 2026-11-04: not Black Friday first, "
                     f"a UGC video is less aggressive); the offer comes in the last chapter")
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
    off = [c for c in chs if c.get("kind") == "offer"]
    if off and offer_word_ok(off[-1].get("text"), pr) is False:
        pct = re.sub(r"\D", "", str(pr["offer"]["badge"]["big"]))
        P.append(f"{pid}: the offer chapter must say the {pct}% ('{pct} percent' or the number in words): the offer card shows when "
                 f"that word is said ('half price' alone leaves it out)")
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


OFFER_WORDS = re.compile(r"\b(?:up to|early|black friday|cyber monday|cyber week|sale|clearance|\d+\s?%|percent|off|half|price|now|"
                         r"the|\+)\b|[\d%+.:!·,\-–—/]", re.I)


def offer_only(line):
    """A line that is only the offer / the sale ('50% OFF', 'BLACK FRIDAY', 'Early Black Friday', 'HALF PRICE'): every static carries
    one (Wouter 2026-11-04), so it never names an ad and never counts as a repeat."""
    return not OFFER_WORDS.sub(" ", line or "").strip()


def ad_headline(s):
    """The line of an `ad` static that names it (ad copy, tracker, novelty): `headline`, else the first line that is not the masthead
    nor only the offer (then the first line)."""
    if s.get("headline"):
        return s["headline"]
    ws = [w for w in s.get("words") or [] if w.strip().upper() != "LIBRA"]
    return next((w for w in ws if not offer_only(w)), (ws or s.get("words") or [""])[0])


def story_line(s):
    """The line of a static that tells its story next to the offer (the team 2026-11-04: 'story is not enough'): an `ad`'s first line
    that is not the masthead, the offer alone or the bag's name alone; a concept / studio / native static's headline (or sub). None
    when it has none ('The everyday hobo.' names the bag, it tells nothing)."""
    if s.get("layout") == "story":                 # (its hook; a quote look's story is the customer's own words)
        if s.get("look") == "quote" and s.get("review"):
            return s.get("review_text") or f"review {s['review']}"
        lines = [s.get("hook")]
    else:
        lines = (s.get("words") or []) if s.get("layout") == "ad" else [s.get("headline"), s.get("sub")]
    ok = [w.strip() for w in lines if w and w.strip().upper() != "LIBRA" and not offer_only(w) and not NAME_ONLY.match(w.strip())
          and nwords(w) >= 3]
    return max(ok, key=nwords) if ok else None      # (the longest: 'One bag, all day.' over the labels 'Morning · Desk · Dinner')


def story_caption(s):
    """The caption a real-photo stand-in of this static carries when its AI picture fails the gate (the story stays, the picture is a real
    one): its story line, with the answer after a question ('Keys at the bottom again? Two gold side zips.'); None without a story."""
    line = story_line(s)
    if not line or s.get("layout") != "ad":
        return line
    rest = [w.strip() for w in s.get("words") or [] if w.strip() and w.strip().upper() != "LIBRA" and not offer_only(w)]
    q = next((k for k, w in enumerate(rest[:-1]) if w.endswith("?")), None)
    return f"{rest[q]} {rest[q + 1]}" if q is not None else line


def feature_tags(pr):
    """The product's feature tags (HIDDEN BACK POCKET, GOLD SIDE ZIPS ...): what a static's story may be about."""
    return [f[1] for f in pr.get("features") or [] if isinstance(f, (list, tuple)) and len(f) > 1 and f[1]]
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


def _rules(section):
    try:
        return json.load(open(os.path.join(HERE, "data", "rulebook.json"))).get(section) or {}
    except (OSError, ValueError):
        return {}


FOOTAGE_RULES = _rules("footage")


PLAYBOOK_FROM = "2026-11-05"          # the rulebook's hard rules (playbook_check.py) check sheets from this day on (older: warnings)


def presenters_wanted(n_projects, day=None):
    """How many projects of a batch carry the presenter: rulebook.json presenter.per_batch (the highest key not above n), one per
    batch of 2+ for sheets before the rulebook."""
    import datetime
    if (day or datetime.date.today().isoformat()) < PLAYBOOK_FROM:
        return 1 if n_projects >= 2 else 0
    tab = {int(k): int(v) for k, v in ((_rules("presenter") or {}).get("per_batch") or {}).items() if str(k).isdigit()}
    if not tab:
        return 1 if n_projects >= 2 else 0
    ks = [k for k in tab if k <= n_projects]
    return min(tab[max(ks)], n_projects) if ks else 0


def footage_problem(text, tag, cov, pr):
    """Why the library cannot show what this line names (None: it can): every feature the words name (shotmatch.specific_wants, with
    what else shows it: shotmatch.ALSO) has fewer good labelled moments for the product than the rulebook's minimum. Then the video
    would put a stand-in under the line (owner 2026-11-05: footage that does not match the captions must never happen)."""
    import shotmatch
    sp = shotmatch.specific_wants(text, tag)
    if not sp:
        return None
    need = int(FOOTAGE_RULES.get("min_moments_for_show_tag", MIN_MOMENTS))
    best = {t: max([cov.get(t, [0])[0]] + [cov.get(x, [0])[0] for x in shotmatch.ALSO.get(t, ())]) for t in sp}
    if any(n >= need for n in best.values()):
        return None
    return (f"the words name {', '.join(sorted(sp))} but {pr['name']}'s labelled footage has only "
            f"{', '.join(f'{n} {t}' for t, n in sorted(best.items()))} good moment(s) (need {need}): the picture would not match the "
            f"caption. Say what the footage shows (the packet's footage tags) or drop the line")


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


def static_story_problems(stats, pr, P, W):
    """Every static tells a story next to the offer (the team 2026-11-04 on the 9 offer-led samples: 'story is not enough'): a static
    whose words the strategist writes names its `story` (a type of data/static_formats.json 'stories') and, for a feature story, the
    `feature`, and carries the story line; the engine's review / value / checklist layouts carry their own; across the batch at least 3
    story types (2 under 6 statics), none on more than 40%, no feature on more than a third, the offer or the colours alone once at most."""
    kinds_lib = formats()["stories"]
    tags = {t.upper() for t in feature_tags(pr)}
    kinds = []
    for s in stats:
        sid, lay = s.get("id") or "?", s.get("layout")
        if lay in STORY_LAYOUTS:
            st = s.get("story")
            if st not in kinds_lib:
                P.append(f"{sid}: story: what it tells next to the offer, one of {', '.join(kinds_lib)} (the team 2026-11-04: "
                         f"'story is not enough')")
            else:
                kinds.append(st)
                if kinds_lib[st].get("feature") and not s.get("feature"):
                    P.append(f"{sid}: feature: the one feature its {st} story is about ({', '.join(sorted(tags)) or 'a fact of the packet'})")
            if not story_line(s):
                P.append(f"{sid}: no story line: next to the offer one line of 3+ words says why to buy (a moment, a problem and its fix, "
                         f"proof, the gift, the value); the offer alone or the bag's name ('The everyday hobo.') tells nothing")
        elif lay in STORY_SELF:
            kinds.append(s.get("story") if s.get("story") in kinds_lib else STORY_SELF[lay])
        if s.get("feature") and tags and str(s["feature"]).upper() not in tags:
            W.append(f"{sid}: feature {s['feature']!r} is not one of {pr['name']}'s feature tags ({', '.join(sorted(tags))}): only a fact "
                     f"of the packet")
    bare = [s.get("id") or "?" for s in stats if s.get("layout") in NO_STORY]
    if len(bare) > 1:
        P.append(f"statics: {', '.join(bare)} show the offer / the colours alone, no story: at most one a batch")
    need = 3 if len(stats) >= 6 else 2 if len(stats) >= 3 else 1
    if kinds and len(set(kinds)) < need:
        P.append(f"statics: {len(set(kinds))} story type(s) ({', '.join(sorted(set(kinds)))}): at least {need} in a batch of {len(stats)} "
                 f"(a moment, a problem and its fix, proof, the gift, the value, the ways to wear)")
    if len(kinds) >= 5:
        for t in sorted(set(kinds)):
            if kinds.count(t) > 0.4 * len(kinds):
                P.append(f"statics: the {t} story on {kinds.count(t)} of {len(kinds)} statics, at most {int(0.4 * len(kinds))}: vary the "
                         f"reason to buy")
    feats = [str(s.get("feature")).upper() for s in stats if s.get("feature")]
    cap = max(2, -(-len(stats) // 3))
    for f in sorted(set(feats)):
        if feats.count(f) > cap:
            P.append(f"statics: {feats.count(f)} statics tell the {f} story, at most {cap}: spread the stories over the features")


def story_static_problems(s, sid, pr, P, W, items):
    """The checks of one `story` static (brand_statics.l_story): its look, the hook (3-10 words; highlight words in it), the answer line,
    the points / rows, the review (one of the product's own reviews.json numbers, any review_text a verbatim part of it), the scene
    (optional: an AI story scene like a concept's; without one a real footage frame is the photo)."""
    import ugc_script as U
    look = s.get("look")
    if look not in STORY_LOOKS:
        P.append(f"{sid}: look {look!r} (one of {', '.join(STORY_LOOKS)})")
    hook = s.get("hook") or ""
    if look == "quote":
        if hook and nwords(hook) > 6:
            P.append(f"{sid}: a quote look's hook is a small kicker over the customer's words: at most 6 words")
    elif not 3 <= nwords(hook) <= 10:
        P.append(f"{sid}: hook: the headline that names the moment or the friction, 3-10 words ({nwords(hook)} given)")
    for w in s.get("highlight") or []:
        if re.sub(r"\W", "", str(w)).lower() not in {re.sub(r"\W", "", x).lower() for x in hook.split()}:
            P.append(f"{sid}: highlight {w!r} is not a word of the hook")
    if s.get("sub") and (look != "hook" or nwords(s["sub"]) > 12):
        P.append(f"{sid}: sub: the answer line of a hook look, at most 12 words")
    pts = s.get("points") or []
    if look in ("list", "stack") and not (3 if look == "list" else 3) <= len(pts) <= (3 if look == "list" else 4):
        P.append(f"{sid}: points: {'3 numbered reasons' if look == 'list' else '3-4 things you get'} ({len(pts)} given)")
    for x in pts:
        if nwords(x) > 8:
            P.append(f"{sid}: point {x!r}: at most 8 words")
    rows = s.get("rows") or []
    if look == "versus":
        if not 3 <= len(rows) <= 4 or not all(isinstance(r, (list, tuple)) and len(r) == 2 for r in rows):
            P.append(f"{sid}: rows: 3-4 pairs [the other bag, ours], each at most 5 words")
        for r in rows:
            for x in r if isinstance(r, (list, tuple)) else []:
                if nwords(x) > 5:
                    P.append(f"{sid}: row {x!r}: at most 5 words")
        for k in ("them", "us"):
            if s.get(k) and nwords(s[k]) > 3:
                P.append(f"{sid}: {k}: at most 3 words")
        if re.search(r"\b(?:coach|kate spade|michael kors|longchamp|pacsafe|travelon|tumi|calpak|bellroy|fossil)\b", " ".join(
                [str(s.get("them") or ""), hook] + [r[0] for r in rows if isinstance(r, (list, tuple)) and r]), re.I):
            P.append(f"{sid}: versus names a real brand: the other side is a generic bag ('Your old tote', 'Open tote')")
    revs = {r["n"]: r for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}
    n = s.get("review")
    want_rev = (_rules("statics") or {}).get("story_review", False)     # (Julian 2026-11-05, three statics: "I would not put a review here")
    if not n and (s.get("look") == "quote" or want_rev):
        P.append(f"{sid}: review: a reviews.json number of {pr['name']} ({pr.get('reviews')}): the quote look is the customer's words")
    elif n and s.get("look") != "quote" and not want_rev:
        W.append(f"{sid}: a review card on a {s.get('look')} story static: Julian 2026-11-05 would leave it out (use the space for the bag); "
                 f"only the quote look needs one")
    if not n:
        pass
    elif n not in (pr.get("reviews") or []):
        P.append(f"{sid}: review {n} is not one of {pr['name']}'s reviews ({pr.get('reviews')})")
    elif s.get("review_text") and re.sub(r"\s+", " ", s["review_text"]).strip() not in re.sub(r"\s+", " ", revs[n]["text"]):
        P.append(f"{sid}: review_text is not a verbatim part of review {n} ({revs[n]['name']}): never reword a customer")
    sc = s.get("scene")
    if sc:
        pt = sc.get("prompt") or ""
        if len(pt) < 60 or sc.get("kind") not in ("object", "worn", "hand"):
            P.append(f"{sid}: scene: kind (object|worn|hand) and a prompt of at least 60 characters (the moment of the hook)")
        if FACE_WORDS.search(re.sub(r"\b(?:no|nobody|not|without|never|neither)\b[^.;]{0,50}?\b(?:face|faces|eyes|mouth|portrait)\b", "", pt, flags=re.I)):
            P.append(f"{sid}: the scene prompt asks for a face / eyes / sunglasses / a mannequin: the picture has no face at all")
        if INSIDE.search(pt):
            P.append(f"{sid}: {INSIDE.search(pt).group(0)!r}: keep the bag closed")
    for t in [hook, s.get("sub"), s.get("kicker"), s.get("them"), s.get("us")] + list(pts) + [x for r in rows if isinstance(r, (list, tuple)) for x in r]:
        if t:
            if U.FIRST.search(str(t)):
                P.append(f"{sid}: {t!r}: first person (only a customer's verbatim review speaks as 'I')")
            items.append(dict(where=f"{sid} story", text=str(t), source="ours"))


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
            lead = story_problems(p, pid, pr, cov, keys, slib, P, W, sheet.get("date") or "")
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
            if cov and c.get("kind") != "offer" and c.get("cam") != "full":   # the footage / caption blocker at plan (rulebook.json footage)
                fp = footage_problem(t, c.get("tag"), cov, pr)
                if fp:
                    (P if FOOTAGE_RULES.get("low_coverage_level", "hard") == "hard" else W).append(f"{cw}: {fp}")
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
        want_pres = presenters_wanted(len(projs), sheet.get("date") or day)
        if n_pres < want_pres and not sheet.get("no_presenter") and not sheet.get("presenter_count"):
            P.append(f"videos: {want_pres} project(s) of a batch of {len(projs)} carry the presenter (rulebook.json presenter.per_batch; owner "
                     f"2026-11-05: 'the presenter UGC videos are good, we need to make more of that'; about 225 credits each); a request "
                     f"that names another number: \"presenter_count\": <n> in the sheet; one that says no presenter: \"no_presenter\": \"<its words>\"")
        elif sheet.get("presenter_count") is not None and n_pres != int(sheet["presenter_count"]) and not sheet.get("no_presenter"):
            P.append(f"videos: the sheet's presenter_count is {sheet['presenter_count']}, {n_pres} projects carry the presenter")
        elif n_pres > max(want_pres, int(sheet.get("presenter_count") or 0)):
            W.append(f"videos: {n_pres} presenter projects (about 225 credits each, more than the rulebook's {want_pres})")
    try:                         # the craft rules (docs/RULEBOOK.md, data/rulebook.json): hooks, banned phrases, claim words, counts
        import playbook_check
        p_, w_ = playbook_check.sheet_problems(sheet, pr, ctx=compliance.context(pr), exclude=exclude, log=nl)
        if (sheet.get("date") or day or datetime.date.today().isoformat()) >= PLAYBOOK_FROM:
            P += p_
        else:
            W += p_
        W += w_
    except Exception as e:  # noqa: BLE001 - a broken rulebook must say so, not hide
        P.append(f"playbook check could not run ({type(e).__name__}: {e}): fix pipeline/data/rulebook.json")
    allowed = sorted({(int(m.group(1)) if m.group(1).isdigit() else compliance.ONES[m.group(1).lower()])
                      for i_ in items for m in compliance.COUNT_WORD.finditer(i_["text"])})      # ('Five things ...': a count the video shows, not a stat)
    pct = product_pct(pr)
    offer_rule = bool(pct) and (sheet.get("date") or day or datetime.date.today().isoformat()) >= OFFER_FROM
    for k, s in enumerate(stats, 1):
        sid = f"{s.get('id') or '?'}"
        if offer_rule and s.get("layout") == "ad" and not any(offer_shown(w, pct) for w in s.get("words") or []):
            P.append(f"{sid}: no offer on the picture (Wouter 2026-11-04: every static shows the offer): one of its words is the offer, "
                     f"set big as part of the design ('{pct}% OFF'{', HALF PRICE' if pct == 50 else ''})")
        if offer_rule and s.get("layout") == "concept" and not s.get("pill") and \
                not any(offer_shown(s.get(x_), pct) for x_ in ("kicker", "headline", "sub", "badge")):
            P.append(f"{sid}: no offer on the concept static (Wouter 2026-11-04): \"pill\": true (the {pct}% OFF badge) or the % in its words")
        if s.get("layout") not in LAYOUTS:
            P.append(f"{sid}: layout {s.get('layout')!r} (one of {', '.join(LAYOUTS)})")
        elif s.get("layout") in SALE_LAYOUTS and not (camp and camp.get({"gifts": "gifts", "bundle": "bundle_any"}[s["layout"]])):
            P.append(f"{sid}: layout {s['layout']!r} needs a sale campaign with {'free gifts' if s['layout'] == 'gifts' else 'a 2-3 bag bundle'} "
                     f"running for the theme (campaign.py: none for {sheet.get('theme')!r} today)")
        if s.get("project") not in seen_ids and (seen_ids or s.get("project")):   # a statics-only sheet: no project needed
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
        if s.get("layout") == "story":
            story_static_problems(s, sid, pr, P, W, items)
        if s.get("pill") not in (None, True, False):
            P.append(f"{sid}: pill is true or false (the offer's % pill); a custom text goes in badge")
    if stats and (sheet.get("date") or day or datetime.date.today().isoformat()) >= STATIC_STORY_FROM:
        static_story_problems(stats, pr, P, W)
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
            if h and not offer_only(ad_headline(s)) and h in old_caps and h.removeprefix("the ") != re.sub(r"\W+", " ", pr["name"].lower()).strip():   # (the name alone may repeat)
                P.append(f"{s.get('id')}: the line {ad_headline(s)!r} was on a static of an earlier batch: new words")
    moving = [s for s in stats if s.get("motion") is not None]
    for s in moving:                  # motion stills (owner 2026-11-03): a concept scene as a short loop, our typography over it
        sid, mo = s.get("id") or "?", s.get("motion")
        if s.get("layout") != "concept":
            P.append(f"{sid}: motion: only a concept static moves (an AI ad's own words would warp in a clip)")
        elif not isinstance(mo, str) or len(mo.strip()) < 20:
            P.append(f"{sid}: motion: what moves around the bag, in a sentence (steam from the cup, light through the window ...)")
        elif MOTION_PEOPLE.search(mo):
            P.append(f"{sid}: motion: nobody and no hand moves in a motion still: only the scene around the bag")
        elif MOTION_BAG.search(mo):
            P.append(f"{sid}: motion: say only what moves around the bag, without naming the bag (it never moves: it would morph)")
        if s.get("style") == "overlay":
            P.append(f"{sid}: motion: a motion still keeps its words in the footer (no style overlay)")
        if s.get("layout") == "concept" and (s.get("scene") or {}).get("kind", "object") != "object":
            P.append(f"{sid}: motion: only an object scene (scene.kind object: nobody in the picture) becomes a motion still")
    if len(moving) > MAX_MOTION:
        P.append(f"statics: {len(moving)} motion stills, at most {MAX_MOTION} a batch (~9 credits each)")
    if stats:
        n_ai = sum(s.get("layout") in ("concept", "ad") or (s.get("layout") == "story" and bool(s.get("scene"))) for s in stats)
        W.append(f"{n_ai} AI statics of {len(stats)} ({len(ads)} designed ads, {n_ai - len(ads)} studio scenes; about {n_ai} credits plus retries)"
                 + (f"; {len(moving)} motion stills, about {round(8.75 * len(moving))} credits more" if moving else ""))
        heads = [re.sub(r"\W+", " ", ((ad_headline(s) if s.get("layout") == "ad" else s.get("headline")) or "").lower()).strip()
                 for s in stats if (s.get("headline") or s.get("layout") == "ad")
                 and not offer_only(ad_headline(s) if s.get("layout") == "ad" else s.get("headline"))]
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
    return [(i, s) for i, s in enumerate(sheet.get("statics") or []) if s.get("layout") in ("concept", "ad")
            or (s.get("layout") == "story" and s.get("scene"))]


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
          f"shipping: {'free shipping (every order: US, UK and Australia; say free shipping, never free US shipping)' if ctx['ship'] else 'not stated: do not mention'}; warranty: {V['warranty'] or '-'}; returns: {V['returns'] or '-'}"]
    L += [f"- Feature: **{f[1]}**: {f[0]}" for f in pr.get("features") or []]
    L += [f"- Also true: {x}" for x in pr.get("also") or []]          # (owner facts that are not a feature line of the engine)
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
    try:
        import playbook_check
        L += ["\n" + playbook_check.packet_section(pr)]
    except Exception as e:  # noqa: BLE001
        L += [f"\n(the rulebook could not be read: {e})"]
    L += ["\n### What converts for Libra (owner + data, 2026-10-26: read before you write)\n",
          "- The account's money comes from people telling a true story to camera (the ACH creator winners: 123-H4 205 orders, 147-H1 183, "
          "CTR 5-10%); faceless voice-over-b-roll videos mostly lose. Prefer the presenter (a host, never a customer) or a person in the "
          "footage doing something, and a story-like structure (a situation, the problem, what the bag does about it, the sale).",
          "- Every project a DIFFERENT concept (person, setting, opening, format, emotion): Meta groups look-alike ads and they share "
          "delivery, so four similar videos count as one. Never the same structure twice in a batch.",
          "- Open with a reason to buy this bag in the first 2 seconds, shown not told (a hand that can't reach the back pocket, the zip "
          "closing, what fits, two ways to carry); the sale is the close. Every brand opens with '50% off' in November: our videos don't (the statics do show it, below).",
          "- Sell the 3-Piece Set where it fits (the Hobo Bag page offers it as the 'Best Value' upgrade; its ads ran at ROAS ~3 with a "
          "bigger basket): three pieces for one price.",
          "- No exact prices in new lines or statics while the owner tests a price change: say the % ('50% off', 'up to 60% off').",
          "- Statics: one idea each, few words, the bag big; most should be AI ads (the AI ads 'seem to be starting to work': owner): "
          "the `ad` formats of section 5, each batch new ones, realistic, never the same look twice.",
          "- **Every static shows the offer** (Wouter 2026-11-04 on B036's 50 statics: 'Don't have the offer on it. Not sure if those will "
          "work.'): every `ad` carries the offer in its words as a HERO element of the design (giant numerals behind the bag, a swing tag on "
          "the strap, a sticker burst, a window decal, neon, a stamp, a ribbon, a sale shopping bag: the offer-led formats of section 5), "
          "every `concept` has `pill: true`, every real static gets the % badge. Lead with the product's own offer stack from the site: "
          "the Hobo Bag '50% OFF + FREE pouch wallet + free shipping', the 3-Piece Set '60% OFF, 3 bags, 1 set' (the site's 'Best Value' "
          "upgrade), the Hobo 2.0 '50% OFF'. The check refuses an ad without it.",
          "- **Scroll-stoppers, studio level, a different design every time** (the owner 2026-11-04: 'offers are nice but the design is the "
          "same every time ... studio level design with offers that increase scroll stopping'): the account's long-running image ads (Meta "
          "Ad Library, Libra's own, some live since Sep 2025) all make the offer the loudest words and the set or the bag big, on a "
          "saturated or warm backdrop. Stop the thumb with ONE strong device per ad: an unexpected scale (numerals bigger than the bag), a "
          "saturated colour the feed doesn't have (deep red, burgundy, forest green, cobalt, black), a real-world object that carries the "
          "offer (tag, sticker, neon, stamp, ribbon, shop window, paper shopping bag), a diagonal split, a candid real-life moment from "
          "behind. Vary across the batch: backdrop colour, composition (centred, off-centre, top-down, close-up, wide), type style "
          "(condensed sans, serif, neon, stamp, handwriting) and the offer device; never two ads alike. One focal point, the offer read in "
          "under a second, then ONE story line (below).",
          "- **Every static tells a story too** (the team 2026-11-04 on the 9 offer-led samples, which Wouter liked: 'Yeah could work' "
          "... 'story is not enough': '50% OFF' + 'Early Black Friday' gives no reason to buy): the offer is the loudest words, ONE "
          "story line of 3-8 words says WHY, and the picture shows that very moment. Name it in the sheet: `story` (problem_fix, moment, "
          "proof, gift, value, ways: section 5) and, for a feature story, `feature` (one of the product's feature tags). 'Packed train. "
          "Cards on your side.' over a photo from behind on a platform, the bag worn; 'Keys at the bottom again?' / 'Two gold side zips.' "
          "over a hand at the zip; 'For Mum. Bag + matching wallet.' on a gift tag by the ribbon; '3 bags. 1 set.' over the set lineup. "
          "Never a line that only names the bag ('The everyday hobo.', 'The hidden-pocket hobo') and never a bare sale word as the only "
          "line. Across the batch at least 3 story types, none on more than 40% of the statics, no feature on more than a third, the "
          "offer or colours layout alone at most once. Only facts of section 1; no invented reaction, no quote that is not a verbatim review.",
          "- **Top tier = the full anatomy, not one line** (the team 2026-11-04 on the story samples: 'good but very basic and not top "
          "tier'; docs/research/2026-11-story-statics.md: the statics that keep running carry 5-6 layers, ours carried 2-3): a hook that "
          "names the friction in 'you' words ('Keys at the bottom of your bag again?'), the picture of that moment, ONE promise, visible "
          "proof (stars + a verbatim review), the offer stack (the % + the free wallet), a small brand mark. Layout `story` sets exactly "
          "that in our own type over the AI story scene or a real footage frame, in five looks of the formats that keep running "
          "(problem hook, testimonial quote, listicle, us vs them, offer stack): about a third of the statics are `story` (each look at "
          "most twice, a different review each time), about half `ad`, the rest real. The `ad` formats stay the bold design pieces; give "
          "them the story line, not the proof (the AI cannot be trusted with a customer's exact words)."]
    sl = structures()
    import novelty as NV
    last_s = NV.recent(pr["name"], "structure", last=1)
    L += ["\n### The videos are stories (owner 2026-10-27: 'go ahead'; B025 / B027 were feature lists in costumes: every project walked "
          "through the same five features)\n"] + [f"- {x}" for x in sl["rules"]] + [
          f"- {presenters_wanted(n_projects)} of this batch's {n_projects} project(s) carry the presenter (rulebook.json presenter.per_batch; owner "
          f"2026-11-05: 'the presenter UGC videos are good, we need to make more of that'; about 225 credits each); a request naming "
          f"another number: \"presenter_count\": <n>; one saying no presenter: \"no_presenter\": \"<its words>\" in the sheet.",
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
    L += ["\nA tag with fewer than 4 moments is thin: build the line on something the footage shows more of. The check REFUSES a line that names a feature (a zip, the clasp, the pocket, the strap ...) the footage has under 4 good moments of: the picture would not match the caption (rulebook footage).",
          "\n## 3. What earlier batches did (do not repeat their ideas, hooks, lines, scenes)\n", past(pr),
          "\n## 4. Research notes (read them: docs/research/*.md; the facts above beat them)\n"]
    rd = os.path.join(os.path.dirname(HERE), "docs", "research")
    for f in sorted(os.listdir(rd)) if os.path.isdir(rd) else []:
        if f.endswith(".md"):                        # the notes; sub-folders (sources, blueprint sheets) are linked from them
            L.append(f"- docs/research/{f}")
    fl = formats()
    import novelty
    last_f = novelty.recent(pr["name"], "format", last=1)
    ever_f = novelty.recent(pr["name"], "format", last=novelty.KEEP)
    L += ["\n## 5. The statics (4:5, 1080x1350)\n",
          "**AI-designed ads first** (owner 2026-10-26, after the test sheet: 'i like 2, 3, 4, 6 (make it realistic), 7, 8 (make it more "
          "realistic) ... make them unique each time we run a batch ... new ideas and new formats that follow Meta guidelines'): layout `ad` = "
          "Higgsfield designs the WHOLE ad from the real packshot, picture and words (gpt_image_2_5 sets short text correctly; the gate reads "
          "it back). About half of the statics are `ad`, each a DIFFERENT format and idea, about a third `story`; the rest real (studio / native / quotes / "
          "value / stars) or `concept`. Each batch at least one format of your own (two with 6+ ad statics): a new id with format_name, "
          "art (the art direction: what kind of picture, the layout, the type) and people. Realistic beats glossy: a format that is a "
          "photo must look like a real photo (real light, real textures, a candid angle), never CGI.",
          f"Formats the product's last batch used (not this batch): {', '.join(last_f) or 'none'}; used before: {', '.join(ever_f) or 'none'}.",
          "\nThe format library (data/static_formats.json; ★ = the owner liked it on the test sheet):\n"]
    for f in fl["formats"].values():
        L.append(f"- `{f['id']}`{' ★' if f.get('liked') else ''} {f['name']} (" + ("offer-led, " if f.get("offer") else "") +
                 ("story, " if f.get("story") else "") + f"people: {f['people']}, at most {f['words']} words): "
                 f"{f.get('words_hint') or ''}" + (f"; e.g. {' / '.join(f['example'])}" if f.get("example") else "") +
                 (f"; {f['bag']}" if f.get("bag") else ""))
    tags_ = feature_tags(pr)
    L += ["\nThe stories a static tells next to its offer (`story`; data/static_formats.json 'stories'; feature = the story needs a "
          f"`feature`: one of {', '.join(tags_) or 'the product facts'}):\n"]
    for x in fl["stories"].values():
        L.append(f"- `{x['id']}` {x['name']}{' (feature)' if x.get('feature') else ''}: {x['what']}; e.g. {' / '.join(x['example'])}")
    L += ["(quotes / stars / checklist count as proof, value / bundle as value, gifts as gift; offer and colours tell none: at most one a "
          "batch. The formats marked `story` in the library are built around one: the taped question, the real moment with a sticker, "
          "the handwritten note, where it all goes, three moments in a day.)"]
    revs_ = {r["n"]: r for r in json.load(open(os.path.join(HERE, "data", "reviews.json")))["reviews"]}
    L += [f"\nThe reviews a `story` static may show (`review`: the number; verbatim, never reworded; `review_text` only a verbatim "
          f"part of it). {pr['name']}'s:\n"]
    for n_ in pr.get("reviews") or []:
        r_ = revs_.get(n_)
        if r_:
            L.append(f"- {n_}: {r_['name']}{' (verified)' if r_.get('verified') else ''}: {r_['text'].strip()}")
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
          "Motion stills (owner 2026-11-03): up to 6 `concept` object scenes may carry `motion` (what moves AROUND the bag, in one sentence, "
          "without naming the bag: 'steam curls up from the latte, sunlight flickers through the blinds'): the static also ships as a 5 s "
          "silent loop (Kling 3.0 pro from its still, ~9 credits each, the same footer words). Pick scenes with something that moves "
          "naturally (steam, candle light, rain on a window, curtains, leaves, city bokeh); the bag, people and hands never move.",
          "`story` (the top-tier anatomy, our own type: hook / quote / list / versus / stack, ideas.py --help): the photo of the moment "
          "(an AI story scene whose composition the look asks for, or a real footage frame), the hook, a verbatim review of the product "
          "(reviews.json numbers listed in section 1), the % sticker with the gift tag. The scene prompt shows the hook's moment; the "
          "look keeps its words off the bag (hook: the top third and a bottom corner calm; quote: the bottom 40% calm and darker; list / "
          "versus / stack: the bag in the middle band, the frame's top and bottom are cropped).",
          "Mix: about half `ad` (each a different format), about a third `story` (each look at most twice), the rest real photos "
          "(studio / native / value / quotes) or `concept`."]
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
        L += _statics_table([s for s in sheet.get("statics") or [] if s.get("project") == p["id"]], "**Statics:**\n")
    pids = {p["id"] for p in sheet.get("projects") or []}
    L += _statics_table([s for s in sheet.get("statics") or [] if s.get("project") not in pids], "## Statics\n")   # a statics-only sheet
    return "\n".join(L) + "\n"


def _statics_table(sts, head):
    if not sts:
        return []
    L = [head, "| # | Look | Story | Idea | Words |", "|---|---|---|---|---|"]
    for s in sts:
        words = " · ".join(x for x in (s.get("kicker"), s.get("headline"), s.get("sub"), "50% pill" if s.get("pill") else "", s.get("badge")) if x)
        look = s["layout"] + (" (AI scene: " + s["scene"]["kind"] + ")" if s["layout"] == "concept" else "")
        if s["layout"] == "ad":
            fmt = ad_format(s)
            look, words = f"AI ad: {fmt.get('name')}{' (new format)' if fmt.get('new') else ''}", " / ".join(s.get("words") or [])
        elif s["layout"] == "story":
            look = f"story: {s.get('look')}" + (f" (AI scene: {s['scene'].get('kind')})" if s.get("scene") else " (a real footage frame)")
            words = " · ".join(x for x in (s.get("kicker"), s.get("hook"), s.get("sub"), " / ".join(s.get("points") or []),
                                           " / ".join(f"{a_} vs {b_}" for a_, b_ in s.get("rows") or []),
                                           f"review {s.get('review')}" if s.get("review") else "", "% sticker") if x)
        story = (s.get("story") or STORY_SELF.get(s["layout"]) or "-") + (f": {s['feature']}" if s.get("feature") else "")
        L.append(f"| {s['id']} | {look} | {story} | {s['idea']} | {words or '-'} |")
    return L + [""]


def sheet_csv(sheet, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["project", "title", "kind", "id", "text / idea", "picture it needs", "on screen", "scene prompt", "story"])
        for p in sheet.get("projects") or []:
            for k, h in enumerate(p["hooks"][:4], 1):
                w.writerow([p["id"], p["title"], f"hook H{k} ({h['type']})", f"{p['id']}H{k}", h["text"], ",".join(h.get("show") or []), h["label"], ""])
            for j, c in enumerate(p["chapters"], 1):
                w.writerow([p["id"], p["title"], f"script {c['kind']}", f"{p['id']}c{j}", c["text"], ",".join(c.get("show") or []),
                            ((str(c["number"]) + ". ") if c.get("number") else "") + (c.get("tag") or ""), ""])
        for s in sheet.get("statics") or []:
            w.writerow([s.get("project"), "", f"static {s['layout']}" + (f" {s.get('format')}" if s["layout"] == "ad" else ""), s["id"], s["idea"], "",
                        " / ".join(s.get("words") or []) if s["layout"] == "ad" else
                        " · ".join(x for x in (s.get("kicker"), s.get("headline"), s.get("sub")) if x), (s.get("scene") or {}).get("prompt", ""),
                        (s.get("story") or STORY_SELF.get(s["layout"]) or "") + (f": {s['feature']}" if s.get("feature") else "")])


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

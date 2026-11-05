#!/usr/bin/env python3
"""Match what a script SAYS to what a footage moment SHOWS (Julian 2026-10-21: "the b-roll must match what is said": a line about the
snap close showed the strap).

footage_index.py label-sheets / label-merge give every usable library clip `moments` [{t, tags, q, desc}]: tags from a fixed vocabulary
(footage_index.TAGS) for the frame at time t. This module turns a spoken phrase into the tags it asks the picture for (`wants`) and scores
a moment's tags against them (`score`). make_batch.ugc_board picks each phrase's shot with it.

  python3 pipeline/shotmatch.py "Keys go in one gold side zip, phone in the other."     # -> the wants of a phrase
"""
import re
import sys

# what a phrase asks for: tag -> (words that ask for it, weight). Specific features weigh most (a line about the clasp needs the clasp).
WANT = {
    "snap": (r"snaps?|clasps?|clicks?|magnet\w*|buckles?|fasten\w*|one[- ]hand|closures?|clos(?:e|es|ing)", 5),
    "side_zip": (r"side zips?|gold (?:side )?zips?|zips? on (?:each|both|either) side|each side", 5),
    "zip": (r"zips?|zippers?|zipped|unzip\w*", 3),
    "zip_hand": (r"opens?|pull\w*|slides?|unzip\w*|open and close", 2),
    "lock": (r"locks?|lockable|locked|padlock\w*|secur\w*|anti[- ]theft|theft|thie[fv]\w*|pickpocket\w*|rfid|cut[- ]resistant", 4),
    "pocket": (r"pockets?|hidden|passports?|cards?|flat against", 4),
    "inside": (r"inside|compartments?|organi[sz]\w*|divided|lining|interior|room for|spacious|space", 4),
    "packing": (r"phones?|wallets?|keys?|lipstick|bottles?|tablets?|laptops?|books?|sunglasses|chargers?|essentials|everything|fits?|"
                r"pack\w*|stuff|items?|things", 3),
    "strap": (r"straps?|adjust\w*|crossbody|cross-body|ways to wear|(?:three|3) ways|hands[- ]free|shoulder", 4),
    "tie": (r"ties?|tied|loop\w*|wraps?|chair|table leg|hook", 4),
    "worn": (r"wear\w*|worn|carry\w*|crossbody|shoulder|walk\w*|out the door|hands[- ]free", 2),
    "walking": (r"walk\w*|commut\w*|on the move|streets?|markets?|stations?", 2),
    "placed": (r"tables?|desks?|chairs?|sits?|stands?|upright|hang\w*|hooks?|floor|seat", 2),
    "hero": (r"looks?|styles?|stylish|silhouette|elegant|expensive|beautiful|gorgeous|shape", 1),
    "leather": (r"leather|soft|scratch\w*|water[- ]resistant|stitch\w*|hardware|texture|grain|material|finish", 3),
    "pouch": (r"pouch\w*|matching", 4),
    "colours": (r"colou?rs?|shades?|red|brown|black|blue|gr[ae]y|burgundy|beige|ginger|chocolate", 3),
    "cafe": (r"caf[eé]|coffee|latte|your table", 3),
    "street": (r"streets?|walk\w*|market|city|town", 2),
    "stairs": (r"stairs?", 3),
    "home": (r"home|morning|bedroom|kitchen|living room", 2),
    "office": (r"desk|office|work|lunch", 2),
    "car": (r"car|driv\w*|travel\w*|trip|airport|flight|train|journey", 3),
    "shop": (r"shop\w*|store|checkout", 3),
    "crowd": (r"crowd\w*|busy|rush hour|packed (?:train|platform|station|street|market)", 3),
    "door": (r"door|leaving|out the door|hurry", 2),
    "handheld": (r"in (?:your|one) hand|hold\w*|grab\w*|by the handle", 2),
    "outdoor": (r"outside|outdoors?|park|garden|sunshine|weekend", 2),
}
# what a chapter's feature tag asks for ('ONE-HAND CLASP' -> the clasp), always on top of the words of the phrase
FEATURE = [
    (r"clasp|snap|closure|click", ("snap",)),
    (r"side zip", ("side_zip", "zip")),
    (r"lockable|lock|anti-?theft|security zip|cut-resistant", ("lock", "zip")),
    (r"table security|table strap|tie", ("tie", "placed", "strap")),
    (r"rfid", ("pocket", "inside")),
    (r"pocket", ("pocket",)),
    (r"compartment|room for|organi|storage|fits", ("inside", "packing")),
    (r"ways to wear|strap|crossbody|adjust", ("strap", "worn")),
    (r"leather|soft|finish|look|timeless", ("leather", "hero")),
    (r"set|pouch", ("pouch",)),
    (r"colou?r", ("colours",)),
    (r"zip", ("zip", "zip_hand")),
]
CHAPTER_SHARE = 0.6          # a chapter's own wants weigh this much of a phrase's (the phrase says more than the chapter)
MISS = -4.0                  # a phrase that names a specific feature (weight >= 4) and a moment that shows none of its wants
WEAK = -2.5                  # a soft / partly hidden frame
SPECIFIC = 4

_RE = {t: re.compile(r"(?<![a-z])(?:%s)(?![a-z])" % rx, re.I) for t, (rx, _) in WANT.items()}
FOLD = {"snap": {"snap", "clasp", "close"}, "zip": {"zip"}, "zip_hand": {"zip", "hand"}, "side_zip": {"zip", "side"}, "lock": {"lock", "secure"},
        "pocket": {"pocket"}, "inside": {"inside"}, "packing": {"pack", "item", "hand"}, "strap": {"strap"}, "tie": {"strap", "hang"},
        "worn": {"wear", "shoulder"}, "walking": {"walk"}, "handheld": {"hand"}, "placed": {"table", "hang"}, "hero": {"hero"},
        "leather": {"leather", "detail"}, "pouch": {"pouch"}, "colours": {"colour"}, "cafe": {"cafe", "coffee"}, "street": {"walk"},
        "stairs": {"stairs"}, "home": {"room"}, "office": {"table"}, "car": {"car"}, "shop": {"shop"}, "crowd": {"walk"}, "door": {"door"}}


def wants(text, feature=None, show=()):
    """{tag: weight} the picture of this phrase should show: the tags its words ask for, the chapter's feature tag and its `show` tags
    (a strategist's own cue: ['snap', 'hand']) at CHAPTER_SHARE of their weight. A phrase with 'open' or 'close' only counts them with a
    zip / snap word nearby (a bag 'opens' everywhere)."""
    w = {t: WANT[t][1] for t, rx in _RE.items() if rx.search(text or "")}
    if not ({"zip", "side_zip", "snap", "pocket"} & set(w)):
        w.pop("zip_hand", None)
    if "snap" in w and not re.search(r"snap|clasp|click|magnet|buckle|fasten|one[- ]hand\W+(?:\w+\W+){0,4}(?:shut|close|closes|closed)|"
                                     r"(?:shut|close|closes|closed)\W+(?:\w+\W+){0,4}one[- ]hand", text or "", re.I):
        w.pop("snap")                                   # ('close' alone is the zip or the offer, 'a coffee in one hand' no clasp)
    for t in list(show) + [x for rx, ts in FEATURE if feature and re.search(rx, feature, re.I) for x in ts]:
        if t in WANT:
            w[t] = max(w.get(t, 0.0), WANT[t][1] * CHAPTER_SHARE)
    return w


def score(tags, want, q="good"):
    """How well a moment (its tag set, quality) answers wants: the weights of the wanted tags it shows; a specific want (a feature)
    that nothing of the moment answers costs MISS; a weak frame costs WEAK."""
    if not want:
        return 0.0 if q == "good" else WEAK
    tags = set(tags or ())
    hit = sum(w for t, w in want.items() if t in tags)
    s = hit + (MISS if hit == 0 and max(want.values()) >= SPECIFIC else 0.0)
    return s + (WEAK if q == "weak" else 0.0)


def tags_of_text(text):
    """The vocabulary tags a free text (a hand-written clip note, a file name: 'back pocket 4k', 'side zip keys') speaks of."""
    return {t for t, rx in _RE.items() if rx.search(text or "")}


def fold(tags):
    """The old footage keywords (make_batch.kw_terms) of a tag set, so the keyword matcher still sees a labelled moment."""
    return set().union(*(FOLD.get(t, set()) for t in tags)) if tags else set()


# ---- the footage / caption blocker (owner 2026-11-05: "the footage sometimes doesn't match the captions ... it should not happen") ----
# A shot passes when the picture at the seconds it plays shows something the words said over it ask for. Only a line that names a
# specific feature (a want of weight >= SPECIFIC: the clasp, a zip, the pocket, the inside, the strap, the lock, the pouch, a tie)
# is judged; a line about a mood or a place is free. Data: clip_index.json `moments` (tags per labelled frame).
NEAR = 2.0                   # a labelled frame this close to the shot's seconds counts as what it shows
FAR = 5.0                    # no frame that close: the nearest frame within FAR s; none: the shot is unverified
_IDX = {}
OFFER_RX = re.compile(r"\d+\s?%|\bpercent\b|\bhalf[- ]price\b|\btap the link\b|\bblack friday\b|\bcyber monday\b|\bfree (?:matching )?pouch", re.I)


def moment_index(path=None):
    """{clip id: [(t, tags, q)]} of every labelled clip (clip_index.json), cached."""
    import json
    import os
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "clip_index.json")
    if path not in _IDX:
        try:
            rows = json.load(open(path))
        except (OSError, ValueError):
            rows = []
        _IDX[path] = {str(r.get("id")): [(float(m.get("t", 0)), set(m.get("tags") or ()), m.get("q", "good")) for m in r.get("moments") or []]
                      for r in rows if r.get("id") and r.get("moments")}
    return _IDX[path]


def src_key(src):
    """The clip id of a segment's src: a Drive id, or a cached file named after it (pipeline/cache/media/<id>.mp4)."""
    import os
    b = os.path.basename(str(src or ""))
    return b.rsplit(".", 1)[0] if "." in b else b


def shows(src, start, dur, speed=1.0, idx=None):
    """The tags the picture of a shot shows (the clip from `start` for dur*speed s), or None when the source has no labels (a photo,
    an AI clip, a new product's clip, a presenter take): then the shot is unverified."""
    ms = (idx if idx is not None else moment_index()).get(src_key(src))
    if not ms:
        return None
    a, b = float(start), float(start) + float(dur) * float(speed or 1.0)
    near = [m for m in ms if a - NEAR <= m[0] <= b + NEAR and m[2] != "bad"]
    if not near:
        d, m = min(((min(abs(m[0] - a), abs(m[0] - b)), m) for m in ms if m[2] != "bad"), default=(None, None), key=lambda x: x[0] if x[0] is not None else 1e9)
        if m is None or d > FAR:
            return None
        near = [m]
    return set().union(*(m[1] for m in near))


# what else shows a want well enough (a line about the compartments over a hand at the inner zip pocket is the right picture)
ALSO = {"inside": {"pocket", "packing", "zip_hand"}, "pocket": {"inside"}, "packing": {"inside", "pocket"}, "lock": {"zip", "side_zip", "zip_hand"},
        "strap": {"worn"}, "side_zip": {"zip"}, "zip": {"side_zip", "zip_hand"}, "zip_hand": {"zip", "side_zip"}, "tie": {"placed"},
        "pouch": set(), "snap": set(), "leather": {"hero"}}


def answers(tags, want):
    """True when a picture showing `tags` answers wants (one of them, or what ALSO says shows it)."""
    tags = set(tags or ())
    return any(t in tags or ALSO.get(t, set()) & tags for t in want)


def specific_wants(text, feature=None, show=()):
    """The wants of a text that the picture MUST answer (weight >= SPECIFIC), {} for a line about a mood or a place."""
    w = wants(text, feature, show)
    return {t: x for t, x in w.items() if x >= SPECIFIC}


def verify(tags, text, feature=None, show=()):
    """(verdict, specific wants) of a shot whose picture shows `tags` (None: unlabelled) under these words: 'ok' (no specific want, or
    the picture shows one of the line's wants), 'mismatch' (it shows none of them), 'unverified' (specific wants, no labels)."""
    sp = specific_wants(text, feature, show)
    if not sp:
        return "ok", sp
    if tags is None:
        return "unverified", sp
    return ("ok" if answers(tags, wants(text, feature, show)) else "mismatch"), sp


def said_in(words, a, b, edge=0.08):
    """The words of a transcript ([{w, s, e}], ad seconds) heard in the window a-b (a word overlapping it by more than `edge`)."""
    return " ".join(str(w.get("w", "")) for w in words or () if float(w["s"]) < b - edge and float(w["e"]) > a + edge)


def audit(lf, idx=None, skip=()):
    """The blocker's check of a rendered video (storyboard's _<name>_longform.json: `segments` in order, `transcript` in ad seconds):
    [{at, dur, src, start, words, wants, shows, verdict}] for every shot under a specific line. skip: sources never judged (the
    presenter's takes, the end card)."""
    out, t = [], 0.0
    words = lf.get("transcript") or []
    for s in lf.get("segments") or []:
        L = float(s.get("dur") or 0)
        a, b = t, t + L
        t = b
        src = str(s.get("src") or "")
        if not L or src in skip or src.startswith("talk/") or "/talk/" in src:
            continue
        said = said_in(words, a, b)
        if not said or OFFER_RX.search(said):      # (the offer: the end card and the packshot are the picture)
            continue
        tg = shows(src, s.get("start", 0), L, s.get("speed", 1.0), idx)
        v, sp = verify(tg, said)
        if sp:
            out.append(dict(at=round(a, 2), dur=round(L, 2), src=src, start=s.get("start"), words=said, wants=sorted(sp),
                            shows=sorted(tg) if tg is not None else None, verdict=v))
    return out


def audit_lines(rows):
    """('shot mismatch: ...' lines, 'shot unverified: ...' lines) of audit() rows, for the render log and the QA report."""
    bad = [f"shot mismatch: {r['at']:.1f}s '{r['words'][:60]}' wants {'/'.join(r['wants'])}, the picture shows "
           f"{'/'.join(r['shows']) or 'nothing labelled'} ({src_key(r['src'])[:12]} @{r['start']})" for r in rows if r["verdict"] == "mismatch"]
    unv = [f"shot unverified: {r['at']:.1f}s '{r['words'][:50]}' wants {'/'.join(r['wants'])} ({src_key(r['src'])[:24]}: no labels)"
           for r in rows if r["verdict"] == "unverified"]
    return bad, unv


if __name__ == "__main__":
    import json as _json
    if sys.argv[1:2] == ["--audit"]:          # python3 pipeline/shotmatch.py --audit $OUT/_<name>_longform.json
        for f in sys.argv[2:]:
            b_, u_ = audit_lines(audit(_json.load(open(f))))
            print(f, f"{len(b_)} mismatch, {len(u_)} unverified")
            for x in b_ + u_:
                print("  ", x)
        sys.exit(0)
    for t in sys.argv[1:]:
        print(t, "->", wants(t))

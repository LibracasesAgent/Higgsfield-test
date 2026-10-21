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
    "crowd": (r"crowd\w*|busy|packed|rush", 3),
    "door": (r"door|leaving|out the door|hurry", 2),
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
    if "snap" in w and not re.search(r"snap|clasp|click|magnet|buckle|fasten|one[- ]hand", text or "", re.I):
        w.pop("snap")                                   # ('close' alone is the zip or the offer, not the clasp)
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


if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(t, "->", wants(t))

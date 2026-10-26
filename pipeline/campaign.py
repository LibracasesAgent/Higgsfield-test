#!/usr/bin/env python3
"""Store-wide sale campaigns the client confirmed (data/campaign.json): Black Friday Sale 2026 = up to 60% off + free gifts.

While a campaign runs (its from .. until, inclusive) a batch whose theme is one of its themes gets it in plan.json
("campaign"): the end card says the campaign ('Black Friday Sale' over the packshot, the pill 'UP TO 60% OFF + FREE GIFTS'),
the offer card's sub line, the gifts / bundle statics, one sentence in the close, the engine's hooks, the ad copy and the
strategy packet's facts. Compliance takes its facts as evidence and its approved phrases as backed offer words ('up to 60%
off', '60% off when you buy 2 or 3 bags', 'free gifts', 'a free jewellery box'): a bag's own % stays its offer, so '60% off
the Hobo Bag' is still a problem.

  python3 pipeline/campaign.py show [--theme "black friday"] [--day 2026-10-23]     the campaign a batch of that theme gets
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "campaign.json")


def load():
    try:
        return json.load(open(DATA, encoding="utf-8")).get("campaigns") or []
    except (OSError, ValueError):
        return []


def _day(day=None):
    if isinstance(day, datetime.date):
        return day
    return datetime.date.fromisoformat(day) if day else datetime.date.today()


def active(theme_key, day=None, campaigns=None):
    """The campaign a batch of this theme gets on this day (default: today), as plan.json stores it; None when none runs."""
    d = _day(day)
    for c in campaigns if campaigns is not None else load():
        if theme_key in (c.get("themes") or []) and _day(c["from"]) <= d <= _day(c["until"]):
            return for_plan(c, theme_key)
    return None


def for_plan(c, theme_key):
    """What a batch needs of campaign c for theme theme_key (gift photos as absolute paths)."""
    pick = lambda v: v.get(theme_key) if isinstance(v, dict) else v      # noqa: E731
    gifts = [dict(g, photo=os.path.join(HERE, g["photo"]) if g.get("photo") else None) for g in c.get("gifts") or []]
    return dict(id=c["id"], name=c["name"], theme=theme_key, banner=c.get("banner"), until=c["until"], **{"from": c["from"]},
                end_title=pick(c.get("end_title")) or c["name"], end_pill=c.get("end_pill") or "", card_sub=c.get("card_sub") or "",
                close=pick(c.get("close")) or "", hooks=pick(c.get("hooks")) or [], facts=list(c.get("facts") or []),
                bundle_pct=c.get("bundle_pct"), upto_pct=c.get("upto_pct") or c.get("bundle_pct"), bundle_any=bool(c.get("bundle_any")),
                client_ideas=c.get("client_ideas") or "", gifts=gifts, gifts_worth=c.get("gifts_worth"), dates=dict(c.get("dates") or {}),
                copy=dict(c.get("copy") or {}), approved_phrases=list(c.get("approved_phrases") or []),
                approved=c.get("approved") or "", final_sale=bool(c.get("final_sale")), terms=c.get("terms") or "",
                banned=list(c.get("banned") or []))


def corpus(c):
    """The campaign's facts as evidence text (compliance: claims and numbers)."""
    if not c:
        return ""
    gifts = " ".join(f"{g['name']} worth ${g['worth']:.2f}" for g in c.get("gifts") or [])
    return " ".join(c.get("facts") or []) + " " + gifts + " " + " ".join(f"{k} {v}" for k, v in (c.get("dates") or {}).items())


def numbers(c):
    """Every number the campaign backs: its %s, gift values, bag counts, dates (27, 30 November; 23 October)."""
    if not c:
        return set()
    nums = {float(x) for x in re.findall(r"\d+(?:\.\d+)?", corpus(c))}
    nums |= {float(c[k]) for k in ("bundle_pct", "upto_pct") if c.get(k)}
    nums |= {round(float(g["worth"]), 2) for g in c.get("gifts") or []}
    nums |= {round(float(c["gifts_worth"]), 2)} if c.get("gifts_worth") else set()
    nums |= {float(g["with"]) for g in c.get("gifts") or [] if g.get("with")}
    return nums


def strip(text, c):
    """text without the campaign's approved offer phrases (what is left is checked against the bag's own offer)."""
    if not c or not text:
        return text
    for p in c.get("approved_phrases") or []:
        text = re.sub(p, " ", text, flags=re.I)
    return re.sub(r"\s{2,}", " ", text)


def gift_line(c, n_bags):
    """'a free mirrored jewellery box (worth $19.95)' for 2 bags, both gifts for 3+ ('' without gifts)."""
    gs = [g for g in (c or {}).get("gifts") or [] if (g.get("with") or 0) <= n_bags]
    if not gs:
        return ""
    if len(gs) == 1:
        return f"a free {gs[0]['name']} (worth ${gs[0]['worth']:.2f})"
    tot = c.get("gifts_worth") or sum(g["worth"] for g in gs)
    return f"a free {gs[0]['name']} + a free {gs[1]['name']} (together worth ${tot:.2f})"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("--theme", default="black friday")
    s.add_argument("--day", default=None)
    a = ap.parse_args()
    c = active(a.theme, a.day)
    print(json.dumps(c, indent=1, ensure_ascii=False) if c else f"no campaign runs for theme {a.theme!r} on {_day(a.day)}")


if __name__ == "__main__":
    sys.exit(main())

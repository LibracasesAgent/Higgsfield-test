#!/usr/bin/env python3
"""Which winners to remix: the weekly brief's winners (or explicit codes) matched to clip_bank winner_raws.

  python3 pipeline/winners.py latest                 newest brief in Drive Research Briefs (brief.py latest)
  python3 pipeline/winners.py "94-H4,148-H5"         explicit ads: concept-hook, concept only ("94,148"), or a key
  python3 pipeline/winners.py brief.json             a saved `brief.py latest --out brief.json`
  python3 pipeline/winners.py all                    every bank winner, in clip_bank.json order

Prints JSON: source (brief | codes | all | fallback), winners [{key, name, roas, action, product, concept, hook}]
(brief order: increase first, then keep, by ROAS), brief {id, name, age_days, stale}, unmatched [{name, roas,
action, product, why}], note (why it fell back to all bank winners). make_batch.py plan --winner-videos N
--winners <same argument> uses this and builds one remix.py spec per winner video.
"""
import argparse
import contextlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
BANK = os.path.join(HERE, "data", "clip_bank.json")


def raws(bank=None):
    """winner_raws entries that have edit data, in file order."""
    b = bank or json.load(open(BANK))
    return {k: e for k, e in b.get("winner_raws", {}).items() if isinstance(e, dict) and e.get("edit") and not e.get("draft")}


def row(key, e, **ex):
    return dict(dict(key=key, name=e.get("ad", key), roas=None, action=None, product=e.get("product"),
                     concept=e.get("concept"), hook=e.get("hook")), **ex)


def by_code(tok, rw):
    """'94-H4' / '94' / '86(2)' / 'C9_V2' / 'raw94_H4' -> winner_raws key or None."""
    import brief
    t = tok.strip()
    if t in rw:
        return t
    c, h = brief.codes(t)
    if not c:
        parts = [x for x in re.split(r"[\s_-]+", t.upper()) if x]
        c, h = (brief.concept_of(parts[0]), "".join(parts[1:])) if parts else (None, "")
    hits = [k for k, e in rw.items() if brief.concept_of(e.get("concept") or "") == c]
    if h:
        hits = [k for k in hits if brief.hook_of(rw[k].get("hook")).strip("()") == brief.hook_of(h).strip("()")]
    return hits[0] if hits else None


def select(arg="latest", bank=None):
    rw = raws(bank)
    out = dict(source=None, winners=[], brief=None, unmatched=[], note=None)
    arg = (arg or "latest").strip()
    if arg.lower() == "all":
        out.update(source="all", winners=[row(k, e) for k, e in rw.items()])
        return out
    if arg.lower() == "latest" or arg.lower().endswith(".json"):
        try:
            import brief
            with contextlib.redirect_stdout(sys.stderr):   # keep stdout clean for the caller's JSON
                b = json.load(open(arg)) if arg.lower().endswith(".json") else brief.latest()
            out["brief"] = {k: b.get(k) for k in ("id", "name", "age_days", "stale")}
            out["unmatched"] = [{k: u.get(k) for k in ("name", "roas", "action", "product", "why")} for u in b.get("unmatched", [])]
            seen = set()
            for m in b.get("matched", []):
                if m["key"] in rw and m["key"] not in seen:
                    seen.add(m["key"])
                    out["winners"].append(row(m["key"], rw[m["key"]], name=m["name"], roas=m.get("roas"), action=m.get("action"),
                                              product=rw[m["key"]].get("product") or m.get("product")))
            out["source"] = "brief"
            if not out["winners"]:
                out["note"] = "the brief matched no winner in clip_bank winner_raws"
        except (Exception, SystemExit) as e:  # noqa: BLE001 - Drive login/read/parse problem: fall back, never stop the run
            out["note"] = f"brief could not be read ({type(e).__name__}: {str(e)[:160]})"
        if not out["winners"]:
            out.update(source="fallback", winners=[row(k, e) for k, e in rw.items()])
        return out
    toks = [t for t in re.split(r"[,;]+", arg) if t.strip()]
    seen = set()
    for t in toks:
        k = by_code(t, rw)
        if k and k not in seen:
            seen.add(k)
            out["winners"].append(row(k, rw[k]))
        elif not k:
            out["unmatched"].append(dict(name=t.strip(), roas=None, action=None, product=None,
                                         why="no winner_raws entry with this code: run pipeline/winner_prep.py"))
    out["source"] = "codes"
    if not out["winners"]:
        known = ", ".join(f"{e.get('concept')}{'' if (e.get('hook') or '(').startswith('(') else '-'}{e.get('hook') or ''}"
                          for e in rw.values())
        print(f"--winners {arg!r} matches no winner in clip_bank winner_raws. Known: {known}", file=sys.stderr)
        sys.exit(2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("winners", nargs="?", default="latest", help="latest | all | brief.json | '94-H4,148-H5'")
    a = ap.parse_args()
    print(json.dumps(select(a.winners), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

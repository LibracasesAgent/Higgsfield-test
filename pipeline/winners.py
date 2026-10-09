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


def not_ready(key, bank=None):
    """Why a winner_raws entry exists but cannot be remixed yet (draft / no edit data), or None."""
    e = (bank or json.load(open(BANK))).get("winner_raws", {}).get(key)
    if not isinstance(e, dict) or (e.get("edit") and not e.get("draft")):
        return None
    return ("winner_raws entry is still a draft: check its edit (pipeline/winner_prep.py --check " + key + ") and remove "
            "\"draft\"" if e.get("edit") else "winner_raws entry has no edit data yet: run pipeline/winner_prep.py")


def in_library(names):
    """{ad name: path of its video in the Drive library index, or None} (find_assets.match_ad). A missing or day-old index
    is rebuilt once (index_library.py, ~30 s) when a name is not in it. {} when the library can't be read."""
    import subprocess
    import time
    from find_assets import match_ad
    from index_library import CACHE

    def look():
        files = [i for i in json.load(open(CACHE))["items"] if i["kind"] == "file"]
        return {n: (match_ad(n, files) or [{}])[0].get("path") for n in names}
    try:
        res = look() if os.path.exists(CACHE) else None
        if res is None or (not all(res.values()) and time.time() - os.path.getmtime(CACHE) > 86400):
            subprocess.run([sys.executable, os.path.join(HERE, "index_library.py")], stdout=sys.stderr, stderr=sys.stderr,
                           check=True, timeout=900)
            res = look()
        return res
    except (Exception, SystemExit):  # noqa: BLE001
        return {}


def explain(unmatched):
    """Winners that can't be remixed: 'why' says what the session can do, 'client' is the run-report wording. A RAW that
    is not in the clip bank is looked up in the Drive library: prepare it (winner_prep.py) or ask the client for it."""
    todo = [u for u in unmatched if re.match(r"RAW not in clip bank|no winner_raws entry", u.get("why") or "")]
    lib = in_library([u["name"] for u in todo]) if todo else {}
    for u in todo:
        if not lib:
            u["why"] += " (the Drive library could not be checked for its RAW)"
            u["client"] = "not set up for remixing yet"
        elif lib.get(u["name"]):
            u["why"] = (f"RAW found in the Drive library ({lib[u['name']]}) but not prepared yet: python3 pipeline/winner_prep.py "
                        f"\"{u['name']}\" --write (about 10 min), review it, then plan again")
            u["client"] = "its video is in the library but not set up for remixing yet (we can prepare it)"
        else:
            u["why"] = ("RAW not found in the Drive library: the client must add the RAW video (without captions) and say its "
                        "concept/hook code (e.g. 94-H4); winner_prep.py can't help until then")
            u["client"] = ("we could not find its RAW video in the Drive library: please add the version without captions "
                           "and tell us its concept/hook code (e.g. 94-H4)")
    for u in unmatched:
        w = u.get("why") or ""
        u.setdefault("client", "its edit is still being checked (a human must finish it)" if "draft" in w else
                     "this hook's video is not set up for remixing yet" if "different hook" in w or "no hook code" in w else
                     "not set up for remixing yet")
    return unmatched


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
    bank = bank or json.load(open(BANK))
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
                why = not_ready(m["key"], bank)
                if why and m["key"] not in seen:          # in the bank, but its edit is not ready: a human must look
                    seen.add(m["key"])
                    out["unmatched"].append(dict(name=m["name"], roas=m.get("roas"), action=m.get("action"),
                                                 product=m.get("product"), why=why))
                elif m["key"] in rw and m["key"] not in seen:
                    seen.add(m["key"])
                    out["winners"].append(row(m["key"], rw[m["key"]], name=m["name"], roas=m.get("roas"), action=m.get("action"),
                                              product=rw[m["key"]].get("product") or m.get("product")))
            out["source"] = "brief"
            explain(out["unmatched"])
            if not out["winners"]:
                out["note"] = "the brief matched no winner in clip_bank winner_raws"
        except (Exception, SystemExit) as e:  # noqa: BLE001 - Drive login/read/parse problem: fall back, never stop the run
            out["note"] = f"brief could not be read ({type(e).__name__}: {str(e)[:160]})"
        if not out["winners"]:
            out.update(source="fallback", winners=[row(k, e) for k, e in rw.items()])
        return out
    toks = [t for t in re.split(r"[,;]+", arg) if t.strip()]
    seen = set()
    allw = {k: e for k, e in bank.get("winner_raws", {}).items() if isinstance(e, dict)}
    for t in toks:
        k = by_code(t, rw)
        if k and k not in seen:
            seen.add(k)
            out["winners"].append(row(k, rw[k]))
        elif not k:
            d = by_code(t, allw)
            out["unmatched"].append(dict(name=t.strip(), roas=None, action=None, product=(allw.get(d) or {}).get("product"),
                                         why=not_ready(d, bank) if d else "no winner_raws entry with this code: run "
                                                                          "pipeline/winner_prep.py"))
    out["source"] = "codes"
    explain(out["unmatched"])
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

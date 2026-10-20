#!/usr/bin/env python3
"""The novelty log: what each product's earlier batches already showed, so the next batch is made of other things.

pipeline/data/novelty_log.json (committed, so every Slack session sees it):
  {"products": {"<product slug>": {"batches": [{"date", "name", "statics": [{"layout", "photo", "scene", "colour", "caption"}],
     "clips": [{"scene"}], "videos": [{"script", "angle", "hook", "hook_type"}]}]}}}

recent(slug, field) = the values of that field in the product's last N batches (N = 3): a scene, photo, colour, caption,
hook, script ... that the next batch avoids while another is left (ai_gen.py, make_batch.py, ugc_script.py ask for it).
record() adds the batch that just went to Drive (make_batch.py upload does it; commit the file with the specs).

  python3 pipeline/novelty.py show [slug]          what is logged (counts per product, or one product's recent values)
  python3 pipeline/novelty.py backfill             first fill from the committed batch specs (pipeline/recipes/**)
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "novelty_log.json")
LAST = 3            # batches that count as "recent"
KEEP = 12           # batches kept per product


def slug_of(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "product"


def load(path=None):
    try:
        d = json.load(open(path or PATH))
    except (OSError, ValueError):
        d = {}
    d.setdefault("products", {})
    return d


def save(d, path=None):
    p = path or PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def batches(slug, log=None, path=None):
    return ((log or load(path))["products"].get(slug_of(slug)) or {}).get("batches") or []


def recent(slug, field, last=LAST, log=None, path=None):
    """Values of `field` (statics' / clips' / videos' entries carry it) of the product's last `last` batches, newest first,
    each once."""
    out, seen = [], set()
    for b in reversed(batches(slug, log, path)[-last:]):
        for sec in ("statics", "clips", "videos"):
            for e in b.get(sec) or []:
                v = e.get(field)
                if v not in (None, "") and v not in seen:
                    seen.add(v)
                    out.append(v)
    return out


def record(slug, batch, path=None):
    """Appends one batch ({"date", "name", "statics": [...], "clips": [...], "videos": [...]}) to the product's log; the same
    (date, name) replaces its earlier entry (a re-upload of a run)."""
    d = load(path)
    p = d["products"].setdefault(slug_of(slug), {"batches": []})
    same = next((b for b in p["batches"] if (b.get("date"), b.get("name")) == (batch.get("date"), batch.get("name"))), None)
    if same:       # statics first, videos later (two uploads into one folder): the entries join, none repeats
        for sec in ("statics", "clips", "videos"):
            seen = {json.dumps(e, sort_keys=True) for e in same.get(sec) or []}
            same[sec] = (same.get(sec) or []) + [e for e in batch.get(sec) or [] if json.dumps(e, sort_keys=True) not in seen]
    else:
        p["batches"].append(batch)
    p["batches"] = p["batches"][-KEEP:]
    save(d, path)
    return d


def backfill(path=None):
    """Fills an empty log from the committed batch specs: pipeline/recipes/<kind>/<date>/<name>/plan.json (statics' layout,
    photo, caption; the ugc videos' script id, angle, hook). Nothing is overwritten."""
    import glob
    d = load(path)
    n = 0
    for pj in sorted(glob.glob(os.path.join(HERE, "recipes", "*", "*", "*", "plan.json"))):
        try:
            plan = json.load(open(pj))
        except (OSError, ValueError):
            continue
        slug = slug_of(plan.get("product"))
        date = os.path.basename(os.path.dirname(os.path.dirname(pj)))
        name = os.path.basename(os.path.dirname(pj))
        if any((b.get("date"), b.get("name")) == (date, name) for b in d["products"].get(slug, {}).get("batches", [])):
            continue
        st = []
        sj = os.path.join(os.path.dirname(pj), "statics.json")
        try:
            for ad in json.load(open(sj)).get("ads") or []:
                st.append({k: ad.get(k) for k in ("layout",) if ad.get(k)} | {
                    "photo": os.path.basename(str(ad.get("photo") or "")) or None,
                    "caption": ad.get("caption") or ad.get("headline")})
        except (OSError, ValueError):
            pass
        vids = [{"script": (v.get("ugc") or {}).get("script"), "angle": (v.get("ugc") or {}).get("angle"),
                 "hook": v.get("hook"), "hook_type": ((v.get("ugc") or {}).get("hook") or {}).get("type")}
                for v in plan.get("videos") or [] if v.get("format") == "ugc"]
        d["products"].setdefault(slug, {"batches": []})["batches"].append(
            {"date": date, "name": name, "statics": [{k: v for k, v in s.items() if v} for s in st],
             "clips": [], "videos": [{k: v for k, v in x.items() if v} for x in vids]})
        n += 1
    for p in d["products"].values():
        p["batches"] = sorted(p["batches"], key=lambda b: (b.get("date") or "", b.get("name") or ""))[-KEEP:]
    save(d, path)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("slug", nargs="?")
    sub.add_parser("backfill")
    a = ap.parse_args()
    if a.cmd == "backfill":
        print(f"{backfill()} batch(es) added to {PATH}")
        return
    d = load()
    if a.slug:
        for f in ("scene", "colour", "photo", "layout", "caption", "script", "angle", "hook"):
            print(f"{f}: {recent(a.slug, f)}")
        return
    for k, v in sorted(d["products"].items()):
        print(f"{k}: {len(v['batches'])} batch(es), last {v['batches'][-1].get('date') if v['batches'] else '-'}")


if __name__ == "__main__":
    sys.exit(main())

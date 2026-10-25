#!/usr/bin/env python3
"""The batch ledger: one running number per batch (B045), so no two batches look alike and an ad is never launched twice by mistake.

Why (owner 2026-10-20: "the batches are confusing: a proper naming convention, so we avoid relaunching the same ads"): Drive had folders
named by whatever the request said ("Hobo Bag 5 projects 10 statics", "hook test 3 videos + 4 statics"), and every batch of a bag
reused S01 / P01_H1 under a date. Now every batch has an id: `plan` reserves the next number, every file and the Drive folder carry it
(docs/NAMING.md), `upload` records the folder and the ads, and a plan that repeats an earlier ad says so.

  pipeline/data/batch_ledger.json (committed, like the novelty log; $LC_LEDGER overrides the path for tests):
  {"next": 12, "batches": [{"id": "B011", "n": 11, "rev": 1, "date", "product", "theme", "pipeline", "request", "statics", "projects",
     "hooks", "seed", "status": "planned" | "uploaded", "folder": "<Drive folder name>", "link", "ads": [{"name", "kind", "fp", "label"}]}]}

  python3 pipeline/ledger.py show [--product P]     every batch, newest last (what exists, what was uploaded, where)
  python3 pipeline/ledger.py table                  the same as a Markdown table (docs/BATCHES.md is made from it)
  python3 pipeline/ledger.py seed-legacy            the Drive Outputs folders that predate the ledger become B001..: once
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "data", "batch_ledger.json")


def path():
    return os.environ.get("LC_LEDGER") or PATH


def bid(n, rev=1):
    """B045, or B045r2 for the second run of that batch (a redo of one of its ads)."""
    return f"B{int(n):03d}" + (f"r{rev}" if rev and rev > 1 else "")


def parse(x):
    """'B045', 'b45', '45', 'B045r2' -> (45, 2); (None, 1) for nothing."""
    m = re.fullmatch(r"\s*[Bb]?0*(\d+)(?:[rR](\d+))?\s*", str(x or ""))
    return (int(m.group(1)), int(m.group(2) or 1)) if m else (None, 1)


def load(p=None):
    try:
        d = json.load(open(p or path()))
    except (OSError, ValueError):
        d = {}
    d.setdefault("batches", [])
    d.setdefault("next", max([b["n"] for b in d["batches"]] + [0]) + 1)
    return d


def save(d, p=None):
    p = p or path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")


def find(d, n):
    return next((b for b in d["batches"] if b["n"] == n), None)


def reserve(product, theme, pipeline, request, statics, projects, hooks, seed, created, number=None, p=None, claim=None, reuse=False):
    """The next batch number (saved at once: three plans of one request get B045, B046, B047 even before anything is uploaded), or, with
    `number`, another run of that batch (rev + 1: a redo of one of its ads keeps the batch id and adds r2; with `reuse`, a re-plan of a
    batch still only planned keeps its number as it is). `claim(next) -> n`: the
    number this run owns across runs (batch_lock.claim: Drive), never lower than the ledger's next. -> the batch entry."""
    d = load(p)
    if number and reuse:           # a re-plan of a batch nobody uploaded yet (same --out): the same number, no r2
        b = find(d, number)
        if b and b.get("status") == "planned" and b.get("product") == product:
            b.update(theme=theme, pipeline=pipeline or "catalog", request=request or "", statics=statics, projects=projects,
                     hooks=hooks, seed=seed)
            save(d, p)
            return b
        number = None
    if number:
        b = find(d, number)
        if b:
            b["rev"] = int(b.get("rev") or 1) + 1
            b["status"] = "planned"
            save(d, p)
            return b
        d["next"] = max(d["next"], number + 1)
    else:
        number = max(d["next"], claim(d["next"])) if claim else d["next"]
        d["next"] = number + 1
    b = dict(id=bid(number), n=number, rev=1, date=created, product=product, theme=theme, pipeline=pipeline or "catalog",
             request=request or "", statics=statics, projects=projects, hooks=hooks, seed=seed, status="planned")
    d["batches"].append(b)
    save(d, p)
    return b


def uploaded(n, folder, link, ads, p=None):
    """The batch went to Drive (all of it, or --only part of it: the ads join): folder name, link, the ads' fingerprints."""
    d = load(p)
    b = find(d, n)
    if not b:
        return None
    b.update(status="uploaded", folder=folder, link=link)
    have = {a["name"] for a in b.get("ads") or []}
    b["ads"] = (b.get("ads") or []) + [a for a in ads if a["name"] not in have]
    save(d, p)
    return b


def static_fp(ad):
    """A static is the same ad when layout, photo and words are the same."""
    return "s|{}|{}|{}".format(ad.get("layout") or "", os.path.basename(str(ad.get("photo") or "")),
                               (ad.get("caption") or ad.get("headline") or "").strip().lower())


def video_fp(hook, chapters=None):
    """A video is the same ad when hook line and body are the same."""
    import hashlib
    body = hashlib.md5(" ".join(chapters or []).lower().encode()).hexdigest()[:8] if chapters else ""
    return f"v|{(hook or '').strip().lower()}|{body}"


def repeats(product, fps, novelty_batches=(), exclude=None, p=None):
    """[(fingerprint, where)] of the planned ads (a dict name -> fingerprint) that an earlier batch of the product already had: from the
    ledger (its uploaded ads) and the novelty log (batches that predate the ledger). Hook lines are matched alone for videos."""
    d = load(p)
    seen = {}
    for b in d["batches"]:
        if b["product"].lower() != product.lower() or b["n"] == exclude:
            continue
        for a in b.get("ads") or []:
            seen.setdefault(a["fp"], f"{bid(b['n'], b.get('rev'))} ({b['date']})")
            if a["fp"].startswith("v|"):
                seen.setdefault("h|" + a["fp"].split("|")[1], f"{bid(b['n'], b.get('rev'))} ({b['date']})")
    for nb in novelty_batches:
        tag = f"the {nb.get('date')} batch"
        for s in nb.get("statics") or []:
            seen.setdefault(static_fp(s), tag)
        for v in nb.get("videos") or []:
            if v.get("hook"):
                seen.setdefault("h|" + v["hook"].strip().lower(), tag)
    out = []
    for name, fp in fps.items():
        w = seen.get(fp) or (seen.get("h|" + fp.split("|")[1]) if fp.startswith("v|") else None)
        if w:
            out.append((name, w))
    return out


def rows(d=None):
    d = d or load()
    out = []
    for b in d["batches"]:
        n_ads = len(b.get("ads") or [])
        out.append((bid(b["n"], b.get("rev")), b["date"], b["product"], b.get("theme") or "", b["status"],
                    f"{b.get('statics')} statics + {b.get('projects')} projects" if b.get("statics") is not None else "",
                    f"{n_ads} ads" if n_ads else "", b.get("folder") or b.get("request") or "", b.get("link") or ""))
    return out


def table(d=None):
    head = ("| Batch | Date | Product | Theme | Status | Size | Ads | Drive folder | Link |", "|---|---|---|---|---|---|---|---|---|")
    return "\n".join(head + tuple("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |" for r in rows(d))) + "\n"


PRODUCTS = ("Hobo 2.0", "Hobo Bag", "Vintage Bag", "Silhouette Bag", "3-Piece Set", "Slouchy")


def product_of(name):
    """The bag a legacy folder name speaks of ('2026-10-16 – Vintage Bag 5 projects 10 statics' -> 'Vintage Bag'), else 'Mixed'."""
    return next((x for x in PRODUCTS if x.lower() in name.lower()), "Mixed")


def seed_legacy():
    """The Outputs folders that predate the ledger (named by their request, no batch number) become B001, B002 ... in date order.
    Their Drive names stay as they are (we never rename or move Drive files); the ledger maps each to its number. Once."""
    sys.path.insert(0, HERE)
    import drive_upload as du
    cfg = json.load(open(os.path.join(HERE, "config.json")))
    tok = du.access_token()
    folder = cfg["drive"]["outputs_folder"]
    top = du.list_children(tok, folder)
    kids = [(x["name"], x) for x in top]
    for x in top:                    # the Winners / New Products subfolders of Outputs hold their own batches
        if x.get("mimeType") == "application/vnd.google-apps.folder" and x["name"] in ("Winners", "New Products"):
            kids += [(y["name"], dict(y, pipeline="winners" if x["name"] == "Winners" else "new-product"))
                     for y in du.list_children(tok, x["id"])]
    d = load()
    have = {b.get("folder") for b in d["batches"]}
    found = []
    for name, x in kids:
        m = re.match(r"(\d{4}-\d{2}-\d{2}) – (.+)", name)
        if x.get("mimeType") == "application/vnd.google-apps.folder" and m and name not in have and not re.match(r"B\d{3}", name):
            found.append((m.group(1), x.get("createdTime") or "", name, x))
    n = 0
    for date, created, name, x in sorted(found):
        num = d["next"]
        d["next"] += 1
        d["batches"].append(dict(id=bid(num), n=num, rev=1, date=date, product=product_of(name), theme="",
                                 pipeline=x.get("pipeline") or "catalog", request=name, statics=None, projects=None, hooks=None, seed=None,
                                 status="uploaded", folder=name, link=x.get("webViewLink") or "", legacy=True, ads=[]))
        n += 1
    save(d)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("--product")
    sub.add_parser("table")
    sub.add_parser("seed-legacy")
    a = ap.parse_args()
    if a.cmd == "seed-legacy":
        print(f"{seed_legacy()} legacy folder(s) numbered")
        return
    d = load()
    if a.cmd == "table":
        print(table(d))
        return
    for r in rows(d):
        if not a.product or a.product.lower() in r[2].lower():
            print(" | ".join(str(x) for x in r[:8]))
    print(f"next batch number: B{d['next']:03d}")


if __name__ == "__main__":
    sys.exit(main())

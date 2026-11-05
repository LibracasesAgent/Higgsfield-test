#!/usr/bin/env python3
"""The weekly performance review: Meta's numbers in, the rulebook updated (owner 2026-11-05: "easy to make updates based on the
weekly performance review meetings").

Three steps, each one command:

  1. ingest   Julian exports the week from Ads Manager (Ads level, CSV; columns used when present: Ad name, Amount spent, Impressions,
              3-second video plays, ThruPlays, Link clicks, Purchases, Purchases conversion value). Our ads are found by their LC_ name
              (docs/NAMING.md) and joined to what they were: batch, project, hook version, the hook line (batch_ledger.json), the story
              structure (novelty_log.json), the hook's formula (rulebook.json). Stored in pipeline/data/performance.json.
                python3 pipeline/weekly_review.py ingest ~/Downloads/meta_week.csv --week 2026-11-09
  2. report   Every ad against the rulebook's targets (hook rate 40-45 %, hold, CTR, ROAS, CPA), the best and worst hooks, which hook
              formulas / structures / batches win, and the rulebook changes the numbers suggest. Written to docs/reviews/<week>.md
              for the meeting.
                python3 pipeline/weekly_review.py report --week 2026-11-09
  3. decide   What the meeting decides goes into pipeline/data/rulebook.json with a dated changelog line; the next strategy packet
              prints it and playbook_check.py enforces it:
                python3 pipeline/weekly_review.py add win  "Opening on the zip closing, sound on" --evidence "B040 P02: hook rate 46%"
                python3 pipeline/weekly_review.py add lose "Gift hooks that name no gift" --evidence "B041: 18% hook rate"
                python3 pipeline/weekly_review.py add ban  "treat yourself" --why "Julian 11-12: reads generic, 14% hook rate" [--level soft]
                python3 pipeline/weekly_review.py set kpi.hook_rate.good 0.42 --why "meeting 11-12"
                python3 pipeline/weekly_review.py set presenter.per_batch.5 4 --why "presenter projects lead on hook rate"
              Commit pipeline/data/rulebook.json + performance.json + docs/reviews/ afterwards.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PERF = os.path.join(HERE, "data", "performance.json")
RULEBOOK = os.path.join(HERE, "data", "rulebook.json")
LEDGER = os.path.join(HERE, "data", "batch_ledger.json")
REVIEWS = os.path.join(ROOT, "docs", "reviews")
NAME = re.compile(r"LC_(\d{6})_([A-Za-z0-9]+)_([A-Za-z0-9]+)_(B\d{3}(?:r\d+)?)_(?:(S\d\d)|(P\d\d)_(H\d)|(V\d\d))(?:_([A-Za-z0-9]+))?")
COLS = {             # our field: header words Meta uses (lower case, any one of them)
    "ad": ("ad name",),
    "spend": ("amount spent",),
    "impressions": ("impressions",),
    "plays3": ("3-second video plays", "3 second video plays", "video plays at 3 seconds"),
    "thruplays": ("thruplays", "thruplay"),
    "clicks": ("link clicks",),
    "purchases": ("purchases", "website purchases", "results"),
    "revenue": ("purchases conversion value", "website purchases conversion value", "conversion value"),
}


def _num(x):
    try:
        return float(re.sub(r"[^\d.\-]", "", str(x))) if str(x).strip() not in ("", "-", "--") else 0.0
    except ValueError:
        return 0.0


def _col(header, keys):
    h = [x.strip().lower() for x in header]
    for k in keys:
        for i, x in enumerate(h):
            if x == k or x.startswith(k + " ("):
                return i
    for k in keys:
        for i, x in enumerate(h):
            if k in x and "cost" not in x and "per" not in x and "rate" not in x:
                return i
    return None


def ledger_ads():
    """{ad name: {batch, kind, hook line, product, date}} of every ad we made (batch_ledger.json)."""
    try:
        L = json.load(open(LEDGER))
    except (OSError, ValueError):
        return {}
    out = {}
    for b in L.get("batches") or []:
        for a in b.get("ads") or []:
            out[a["name"]] = dict(batch=b["id"], kind=a.get("kind"), line=a.get("label"), product=b.get("product"), made=b.get("date"),
                                  theme=b.get("theme"))
    return out


def structures():
    """{(batch id, angle slug): structure} from the novelty log."""
    try:
        n = json.load(open(os.path.join(HERE, "data", "novelty_log.json")))
    except (OSError, ValueError):
        return {}
    out = {}
    for p in (n.get("products") or {}).values():
        for b in p.get("batches") or []:
            bid = (re.match(r"(B\d{3}(?:r\d+)?)", str(b.get("name") or "")) or [None])[0]
            for v in b.get("videos") or []:
                if bid and v.get("angle"):
                    out[(bid, re.sub(r"[^a-z0-9]", "", v["angle"].lower()))] = v.get("structure")
    return out


def row_of(name, nums, led, sts):
    import playbook_check
    m = NAME.search(name or "")
    r = dict(ad=name, **nums)
    if m:
        _, prod, theme, bid, sid, pid, hv, vid, angle = m.groups()
        r.update(batch=bid, product_slug=prod, theme=theme, static=sid, project=pid, hook=hv, video=vid, angle=angle)
    full = next((k for k in led if name and (k == name or name.startswith(k) or k.startswith(name))), None)
    if full:
        r.update({k: v for k, v in led[full].items() if v is not None})
    if r.get("angle") and r.get("batch"):
        r["structure"] = sts.get((re.sub(r"r\d+$", "", r["batch"]), r["angle"].lower())) or sts.get((r["batch"], r["angle"].lower()))
    if r.get("line"):
        r["formulas"] = playbook_check.formula_of(r["line"])
    imp = r.get("impressions") or 0
    r["hook_rate"] = round(r["plays3"] / imp, 4) if imp and r.get("plays3") else None
    r["hold_rate"] = round(r["thruplays"] / r["plays3"], 4) if r.get("plays3") and r.get("thruplays") else None
    r["ctr"] = round(r["clicks"] / imp, 4) if imp and r.get("clicks") else None
    r["roas"] = round(r["revenue"] / r["spend"], 2) if r.get("spend") and r.get("revenue") else (0.0 if r.get("spend") else None)
    r["cpa"] = round(r["spend"] / r["purchases"], 2) if r.get("purchases") else None
    return r


def ingest(path, week, ours_only=True):
    rows = list(csv.reader(open(path, newline="", encoding="utf-8-sig")))
    if not rows:
        sys.exit(f"{path}: empty")
    head, data = rows[0], rows[1:]
    idx = {k: _col(head, v) for k, v in COLS.items()}
    if idx["ad"] is None:
        sys.exit(f"{path}: no 'Ad name' column (export at the Ads level): {head[:8]}")
    led, sts = ledger_ads(), structures()
    out = []
    for x in data:
        name = x[idx["ad"]].strip() if idx["ad"] < len(x) else ""
        if not name or (ours_only and not NAME.search(name)):
            continue
        nums = {k: _num(x[i]) for k, i in idx.items() if k != "ad" and i is not None and i < len(x)}
        out.append(row_of(name, nums, led, sts))
    perf = load()
    perf["weeks"][week] = dict(source=os.path.basename(path), ingested=datetime.date.today().isoformat(), ads=out)
    json.dump(perf, open(PERF, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(dict(week=week, ads=len(out), file=PERF, missing_columns=[k for k, i in idx.items() if i is None]), indent=1))
    return out


def load():
    try:
        p = json.load(open(PERF))
    except (OSError, ValueError):
        p = {}
    p.setdefault("_help", "Meta's weekly numbers of our ads (weekly_review.py ingest); hook_rate = 3-s plays / impressions.")
    p.setdefault("weeks", {})
    return p


def rulebook():
    return json.load(open(RULEBOOK))


def _agg(rows):
    imp = sum(r.get("impressions") or 0 for r in rows)
    p3 = sum(r.get("plays3") or 0 for r in rows)
    sp = sum(r.get("spend") or 0 for r in rows)
    rev = sum(r.get("revenue") or 0 for r in rows)
    pu = sum(r.get("purchases") or 0 for r in rows)
    return dict(n=len(rows), impressions=int(imp), hook_rate=(p3 / imp if imp and p3 else None), spend=round(sp, 2),
                roas=(rev / sp if sp else None), purchases=int(pu), cpa=(sp / pu if pu else None))


def _pct(x):
    return "-" if x is None else f"{x:.0%}"


def _f(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def verdict(r, K):
    hr = r.get("hook_rate")
    if r.get("impressions", 0) < K.get("min_impressions", 1000):
        return "too little data"
    if hr is None:
        return "static" if r.get("static") else "no 3-s plays column"
    hk = K.get("hook_rate") or {}
    if hr >= (hk.get("target") or [0.4])[0]:
        return "hook WINS"
    if hr < hk.get("floor", 0.25):
        return "hook loses"
    return "hook ok"


def groups(rows, key):
    out = {}
    for r in rows:
        ks = r.get(key)
        for k in (ks if isinstance(ks, list) else [ks]):
            if k:
                out.setdefault(k, []).append(r)
    return out


def report(week=None, write=True):
    perf, R = load(), rulebook()
    K = R.get("kpi") or {}
    if not perf["weeks"]:
        sys.exit("no weeks in performance.json yet: weekly_review.py ingest <csv> --week YYYY-MM-DD")
    week = week or sorted(perf["weeks"])[-1]
    rows = perf["weeks"][week]["ads"]
    vids = [r for r in rows if r.get("hook") or r.get("video")]
    enough = [r for r in vids if (r.get("impressions") or 0) >= K.get("min_impressions", 1000) and r.get("hook_rate") is not None]
    tot = _agg(rows)
    hk = K.get("hook_rate") or {}
    L = [f"# Weekly review {week}", "",
         f"Source: {perf['weeks'][week].get('source')} · {len(rows)} of our ads · spend ${tot['spend']:,.0f} · ROAS {_f(tot['roas'])} · "
         f"{tot['purchases']} purchases · CPA ${_f(tot['cpa'])} · hook rate {_pct(tot['hook_rate'])} (target "
         f"{_pct((hk.get('target') or [0.4])[0])}-{_pct((hk.get('target') or [0.4, 0.45])[-1])}, floor {_pct(hk.get('floor'))})", ""]
    if enough:
        srt = sorted(enough, key=lambda r: -r["hook_rate"])
        L += ["## Best hooks (hook rate)", "", "| Ad | Hook line | Formula | Hook rate | Hold | CTR | ROAS | Spend |", "|---|---|---|---|---|---|---|---|"]
        L += [f"| {r['ad']} | {r.get('line') or '-'} | {', '.join(r.get('formulas') or []) or '-'} | {_pct(r['hook_rate'])} | "
              f"{_pct(r.get('hold_rate'))} | {_pct(r.get('ctr'))} | {_f(r.get('roas'))} | ${_f(r.get('spend'), 0)} |" for r in srt[:8]]
        L += ["", "## Worst hooks", "", "| Ad | Hook line | Formula | Hook rate | ROAS | Spend |", "|---|---|---|---|---|---|"]
        L += [f"| {r['ad']} | {r.get('line') or '-'} | {', '.join(r.get('formulas') or []) or '-'} | {_pct(r['hook_rate'])} | "
              f"{_f(r.get('roas'))} | ${_f(r.get('spend'), 0)} |" for r in srt[-6:][::-1]]
    sugg = []
    for key, title in (("formulas", "Hook formula"), ("structure", "Story structure"), ("batch", "Batch"), ("hook", "Hook version")):
        g = groups(enough if key != "batch" else rows, key)
        if not g:
            continue
        L += ["", f"## By {title.lower()}", "", f"| {title} | Ads | Hook rate | ROAS | Spend | Purchases |", "|---|---|---|---|---|---|"]
        for k, rs in sorted(g.items(), key=lambda kv: -(_agg(kv[1])["hook_rate"] or 0)):
            a = _agg(rs)
            L.append(f"| {k} | {a['n']} | {_pct(a['hook_rate'])} | {_f(a['roas'])} | ${a['spend']:,.0f} | {a['purchases']} |")
            if key in ("formulas", "structure") and a["n"] >= 3 and a["hook_rate"] is not None:
                if a["hook_rate"] >= (hk.get("target") or [0.4])[0]:
                    sugg.append(f"weekly_review.py add win \"{title} '{k}' opens well\" --evidence \"{week}: {a['n']} ads, hook rate "
                                f"{_pct(a['hook_rate'])}, ROAS {_f(a['roas'])}\"")
                elif a["hook_rate"] < hk.get("floor", 0.25):
                    sugg.append(f"weekly_review.py add lose \"{title} '{k}' does not stop the scroll\" --evidence \"{week}: {a['n']} ads, "
                                f"hook rate {_pct(a['hook_rate'])}\"")
    L += ["", "## Every ad", "", "| Ad | Verdict | Hook rate | Hold | CTR | ROAS | CPA | Spend |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['ad']} | {verdict(r, K)} | {_pct(r.get('hook_rate'))} | {_pct(r.get('hold_rate'))} | {_pct(r.get('ctr'))} | "
          f"{_f(r.get('roas'))} | {_f(r.get('cpa'))} | ${_f(r.get('spend'), 0)} |" for r in sorted(rows, key=lambda r: -(r.get("spend") or 0))]
    L += ["", "## Suggested rulebook changes (decide in the meeting, then run them)", ""]
    L += [f"- `python3 pipeline/{x}`" for x in sugg] or ["- none: not enough ads per formula / structure (3+ with 1,000+ impressions)"]
    md = "\n".join(L) + "\n"
    if write:
        os.makedirs(REVIEWS, exist_ok=True)
        f = os.path.join(REVIEWS, f"{week}.md")
        open(f, "w").write(md)
        print(f"wrote {f}")
    return md


def packet_lines(perf, product=None, weeks=2):
    """What the strategist reads in the packet: the newest weeks' best and worst hooks (by hook rate), the product's first."""
    R = rulebook()
    K = R.get("kpi") or {}
    rows = [r for w in sorted(perf.get("weeks") or {})[-weeks:] for r in perf["weeks"][w]["ads"]
            if r.get("hook_rate") is not None and (r.get("impressions") or 0) >= K.get("min_impressions", 1000) and r.get("line")]
    if not rows:
        return ""
    mine = [r for r in rows if product and (r.get("product") or "").lower() == product.lower()] or rows
    srt = sorted(mine, key=lambda r: -r["hook_rate"])
    L = [f"### Last weeks in Meta (weekly_review.py; hook rate = 3-s plays / impressions; {len(mine)} hooks)\n"]
    L += [f"- WON {_pct(r['hook_rate'])} (ROAS {_f(r.get('roas'))}): \"{r['line']}\" ({r['ad']})" for r in srt[:4]]
    L += [f"- LOST {_pct(r['hook_rate'])}: \"{r['line']}\" ({r['ad']})" for r in srt[-3:][::-1] if r not in srt[:4]]
    return "\n".join(L)


def _log(R, who, change):
    R.setdefault("changelog", []).append(dict(date=datetime.date.today().isoformat(), who=who, change=change))
    R["version"] = datetime.date.today().isoformat()


def add(kind, text, evidence="", why="", level="hard", who="weekly review", rx=None, where="all"):
    R = rulebook()
    if kind in ("win", "lose"):
        sec = R.setdefault("winning_patterns" if kind == "win" else "losing_patterns", {}).setdefault("items", [])
        rid = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:32]
        sec.append(dict(id=rid, rule=text, evidence=evidence, added=datetime.date.today().isoformat()))
        _log(R, who, f"{kind}: {text} ({evidence})")
    elif kind == "ban":
        pat = rx or r"\b" + re.escape(text.lower()).replace(r"\ ", r"\s+") + r"\b"
        re.compile(pat)
        rid = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:32]
        R.setdefault("banned", {}).setdefault("rules", []).append(dict(id=rid, rx=pat, level=level, where=where,
                                                                        why=f"{why or evidence} (weekly review {datetime.date.today().isoformat()})"))
        _log(R, who, f"ban ({level}, {where}): {text}: {why or evidence}")
    elif kind == "note":
        _log(R, who, text + (f" ({evidence})" if evidence else ""))
    else:
        sys.exit(f"unknown kind {kind!r}: win | lose | ban | note")
    json.dump(R, open(RULEBOOK, "w"), indent=2, ensure_ascii=False)
    print(f"rulebook updated ({kind}): {text}")


def set_value(path, value, why="", who="weekly review"):
    R = rulebook()
    cur, keys = R, path.split(".")
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    try:
        v = json.loads(value)
    except ValueError:
        v = value
    old = cur.get(keys[-1])
    cur[keys[-1]] = v
    _log(R, who, f"{path}: {old!r} -> {v!r}" + (f" ({why})" if why else ""))
    json.dump(R, open(RULEBOOK, "w"), indent=2, ensure_ascii=False)
    print(f"rulebook {path}: {old!r} -> {v!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest")
    i.add_argument("csv")
    i.add_argument("--week", default=datetime.date.today().isoformat(), help="the week's Monday (YYYY-MM-DD)")
    i.add_argument("--all", action="store_true", help="keep ads that are not ours (no LC_ name) too")
    r = sub.add_parser("report")
    r.add_argument("--week")
    a_ = sub.add_parser("add")
    a_.add_argument("kind", choices=("win", "lose", "ban", "note"))
    a_.add_argument("text")
    a_.add_argument("--evidence", default="")
    a_.add_argument("--why", default="")
    a_.add_argument("--level", default="hard", choices=("hard", "soft"))
    a_.add_argument("--where", default="all", choices=("all", "hook", "statics", "copy"))
    a_.add_argument("--rx", help="ban: a regex instead of the literal words")
    a_.add_argument("--who", default="weekly review")
    s_ = sub.add_parser("set")
    s_.add_argument("path", help="dotted path in rulebook.json, e.g. kpi.hook_rate.good")
    s_.add_argument("value", help="JSON value (0.42, \"hard\", [0.4, 0.45])")
    s_.add_argument("--why", default="")
    s_.add_argument("--who", default="weekly review")
    a = ap.parse_args()
    if a.cmd == "ingest":
        ingest(a.csv, a.week, ours_only=not a.all)
    elif a.cmd == "report":
        print(report(a.week))
    elif a.cmd == "add":
        add(a.kind, a.text, a.evidence, a.why, a.level, a.who, a.rx, a.where)
    else:
        set_value(a.path, a.value, a.why, a.who)


if __name__ == "__main__":
    main()

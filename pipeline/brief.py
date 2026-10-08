#!/usr/bin/env python3
"""Read the weekly Facebook ads brief and match its winners to RAW edits in the clip bank.

  latest  python3 pipeline/brief.py latest [--out brief.json] [--text brief.txt] [--doc <google_doc_id>]
          Newest Google Doc in Drive Research Briefs (config.json drive.research_briefs_folder),
          exported as text, parsed and matched. --doc reads that Doc instead of the newest one.
  parse   python3 pipeline/brief.py parse <brief.txt> [--out brief.json]      (offline; "-" = stdin)

Prints JSON: id, name, created, age_days, stale (older than 8 days), period,
  ads       every ad in the brief: name, ad_id, action (increase|keep|pause|attention), roas, cpa,
            conversions, product (+ prior_roas, spend, revenue, ctr when the brief has them)
  tests     "creative tests for next week": product, angle, format, hook, benchmark
  winners   increase first, then keep, each by ROAS (pause/attention left out)
  matched   winners with a RAW edit in pipeline/data/clip_bank.json winner_raws (key = the bank key)
  unmatched winners without one, with the reason (usually: run pipeline/winner_prep.py first)
A one-line summary goes to stderr. Accepts the Drive export and the Drive-connector (Markdown) text.
Importable: latest(token=None), parse(text, bank=None), match(ads, bank).
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
BANK = os.path.join(HERE, "data", "clip_bank.json")
STALE_DAYS = 8
DOC = "application/vnd.google-apps.document"
BULLET = re.compile(r"^\s*(?:[•●○◦▪·\-–*]|\d{1,2}[.)])\s+")
RULE = re.compile(r"^\s*[━─═_\-=~*]{3,}\s*$")
NUM = r"(-?[\d,]*\.?\d+)"
KNOWN = re.compile(r"^(recommended actions|increase budgets?|scale|pause|keep running|keep|winning ads|winners|"
                   r"ads requiring attention|needs attention|creative tests.*|key patterns|executive summary|"
                   r"weekly scorecard)$", re.I)
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


# ---------------------------------------------------------------- text helpers
def clean(text):
    """Drive export or connector Markdown -> plain lines (no BOM, CRLF, bold markers or backslash escapes)."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ").replace("\v", " ")
    text = re.sub(r"(?<!\\)(\*\*|__)", "", text)
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>~<])", r"\1", text)


def num(pat, s, cast=float):
    m = re.search(pat, s, re.I)
    return cast(float(m.group(1).replace(",", ""))) if m else None


def heading(line):
    """Upper-case heading text of a line ("## WINNING ADS", "▲ INCREASE BUDGET"), or None."""
    h = re.sub(r"^[#\s▲▼■□●◆►▶★✓✔*_]+|[\s:*_]+$", "", line)
    if KNOWN.match(h):
        return h.upper()
    if not h or len(h) > 50 or re.search(r"\d", h) or h != h.upper() or not re.search(r"[A-Z]{3}", h):
        return None
    return h


def action_of(h):
    if re.search(r"INCREASE|SCALE|BOOST", h):
        return "increase"
    if re.search(r"PAUSE|TURN OFF|KILL|STOP", h):
        return "pause"
    if re.search(r"KEEP|MAINTAIN", h):
        return "keep"
    return None


def product_name(s):
    s = (s or "").strip(" .:;-–—")
    return None if not s or re.match(r"(not|un)\s*mapped|n/?a$|none$|unknown", s, re.I) else s


def to_date(s):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime.date(*map(int, m.groups()))
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\.?,?\s+(\d{4})", s)
    if m and m.group(2)[:3].lower() in MONTHS:
        return datetime.date(int(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
    return None


# ---------------------------------------------------------------- parsing
def parse_ad(item):
    """'<name> (ad ID 123, product X): ROAS 3.1 ...' -> dict, or None when the bullet is not an ad."""
    m = re.match(r"^(?P<name>.+?)\s*\(\s*ad\s*id\s*[:#]?\s*(?P<id>\d+)(?P<extra>[^)]*)\)\s*:?\s*(?P<rest>.*)$", item, re.I)
    if m:
        name, ad_id, extra, rest = m.group("name"), m.group("id"), m.group("extra"), m.group("rest")
    else:
        m = re.match(r"^(?P<name>[^:]{3,80}?)\s*:\s*(?P<rest>.*\b(?:ROAS|spend|CPA)\b.*)$", item, re.I)
        if not m:
            return None
        name, ad_id, extra, rest = m.group("name"), None, "", m.group("rest")
    p = re.search(r"product\s*:?\s*([^,;)]+)", extra, re.I)
    return dict(name=name.strip(), ad_id=ad_id,
                roas=num(r"\bROAS\s*:?\s*" + NUM, rest),
                prior_roas=num(r"\bprior\s*(?:ROAS)?\s*:?\s*" + NUM, rest),
                cpa=num(r"\bCPA\s*:?\s*\$?\s*" + NUM, rest),
                conversions=num(r"([\d,]+)\s+conversions?\b", rest, int),
                spend=num(r"\bspend\s*:?\s*\$?\s*" + NUM, rest),
                revenue=num(r"\brevenue\s*:?\s*\$?\s*" + NUM, rest),
                ctr=num(r"\bCTR\s*:?\s*" + NUM + r"\s*%", rest),
                product=product_name(p.group(1)) if p else None)


def parse_test(item):
    """'1. Hobo Bag — Angle: ... Format: ... Hook: “...” Benchmark against <ad> (ad ID ..)' -> dict."""
    item = BULLET.sub("", item, count=1).strip()
    field = lambda pat: (lambda m: m.group(1).strip(" .") if m else None)(re.search(pat, item, re.I))  # noqa: E731
    stop = r"(?=\s*(?:Angle\s*:|Format\s*:|Hook\s*:|Benchmark\b|$))"
    hook = re.search(r"Hook\s*:\s*[“\"']([^”\"]+)[”\"']", item, re.I)
    bench = re.search(r"Benchmark(?:\s+against)?\s*:?\s*(.+?)(?:\s*\(\s*ad\s*id\s*[:#]?\s*(\d+)|:|$)", item, re.I)
    product = re.split(r"\s+[—–-]\s+|\s*Angle\s*:", item, maxsplit=1)[0].strip(" .:—–-")
    return dict(product=product or None, angle=field(r"Angle\s*:\s*(.*?)" + stop),
                format=field(r"Format\s*:\s*(.*?)" + stop),
                hook=hook.group(1).strip() if hook else field(r"Hook\s*:\s*(.*?)" + stop),
                benchmark=bench.group(1).strip() if bench else None,
                benchmark_ad_id=bench.group(2) if bench else None)


def items(lines):
    """Group lines into (kind, text): headings, rules and bullets; wrapped lines join their bullet."""
    out, blank = [], True
    for raw in lines:
        line, prev_blank, blank = raw.strip(), blank, not raw.strip()
        if not line:
            continue
        if RULE.match(line):
            out.append(("rule", ""))
        elif re.match(r"^[#*\s]*PRODUCT\s*[:\-–—]\s*\S", line, re.I) and "(ad" not in line.lower():
            out.append(("product", re.sub(r"^[#*\s]*PRODUCT\s*[:\-–—]\s*", "", line, flags=re.I)))
        elif heading(line):
            out.append(("heading", heading(line)))
        elif BULLET.match(line):
            out.append(("bullet", BULLET.sub("", line, count=1).strip(), line))
        elif out and out[-1][0] == "bullet" and not prev_blank:
            out[-1] = ("bullet", out[-1][1] + " " + line, out[-1][2] + " " + line)
        else:
            out.append(("text", line, line))
    return out


def parse(text, bank=None):
    """Brief text -> dict (schema 3). bank = clip_bank dict (default: pipeline/data/clip_bank.json)."""
    text = clean(text)
    lines = text.split("\n")
    ads, order, tests = {}, [], []
    section, action, product = None, None, None
    for it in items(lines):
        kind = it[0]
        if kind == "heading":
            h, act = it[1], action_of(it[1])
            if act and (section == "actions" or len(h) <= 20):
                section, action, product = "actions", act, None
            elif "RECOMMENDED" in h or h == "ACTIONS":
                section, action, product = "actions", None, None
            elif "WINNING" in h or "WINNERS" in h or "TOP ADS" in h:
                section, product = "winning", None
            elif "ATTENTION" in h:
                section, product = "attention", None
            elif "TEST" in h:
                section, product = "tests", None
            else:
                section, product = None, None
        elif kind == "product":
            product = product_name(it[1])
        elif kind in ("bullet", "text") and section == "tests":
            if re.search(r"Angle\s*:|Format\s*:|Hook\s*:", it[1], re.I):
                tests.append(parse_test(it[2]))
        elif kind == "bullet" and section in ("actions", "winning", "attention"):
            ad = parse_ad(it[1])
            if not ad or (section == "actions" and not action):
                continue
            ad["product"] = ad["product"] or (product if section in ("winning", "attention") else None)
            ad["_act"] = {"actions": action, "winning": "keep", "attention": "attention"}[section]
            k = ad["ad_id"] if ad["ad_id"] in ads else next(
                (x for x in order if norm(ads[x]["name"]) == norm(ad["name"])
                 and (ad["ad_id"] is None or ads[x]["ad_id"] in (None, ad["ad_id"]))), ad["ad_id"] or norm(ad["name"]))
            if k not in ads:
                ads[k] = dict(ad, _acts=[])
                order.append(k)
            have = ads[k]
            have["_acts"].append((section, ad["_act"]))
            for f, v in ad.items():
                if have.get(f) is None and v is not None:
                    have[f] = v
    out_ads = []
    for k in order:
        a = ads[k]
        acts = [x for s, x in a["_acts"] if s == "actions"] or [x for s, x in a["_acts"] if s == "winning"] \
            or [x for s, x in a["_acts"]]
        out_ads.append(dict(name=a["name"], ad_id=a["ad_id"], action=acts[0], roas=a["roas"], cpa=a["cpa"],
                            conversions=a["conversions"], product=a["product"], prior_roas=a["prior_roas"],
                            spend=a["spend"], revenue=a["revenue"], ctr=a["ctr"]))
    winners = sorted([a for a in out_ads if a["action"] in ("increase", "keep")],
                     key=lambda a: (a["action"] != "increase", -(a["roas"] if a["roas"] is not None else -1)))
    raws = load_bank(bank)
    matched, unmatched = match(winners, raws)
    for a, m in zip(out_ads, [match([a], raws)[0] for a in out_ads]):
        a["product"] = a["product"] or (m[0]["product"] if m else None)
    title = next((re.sub(r"^[#*\s]+|[*\s]+$", "", l) for l in lines if re.search(r"\bBRIEF\b", l, re.I)), None)
    span = next((l.strip() for l in [l for l in lines if l.strip()][:8] if to_date(l)), None)
    end = to_date(re.split(r"\s+(?:–|—|-|to)\s+", span)[-1]) if span else None
    age = (datetime.date.today() - end).days if end else None
    return dict(id=None, name=title, created=None, age_days=age, stale=age is not None and age > STALE_DAYS,
                period=span, ads=out_ads, tests=tests, winners=winners, matched=matched, unmatched=unmatched)


# ---------------------------------------------------------------- matching
def norm(s):
    """Upper-case, drop ACH / COPY / LIBRA and everything that is not a letter or digit."""
    s = re.sub(r"\b(ACH|COPY|LIBRA)\b", " ", clean(s or "").upper())
    return re.sub(r"[^A-Z0-9]", "", s)


def tokens(s):
    return [t for t in re.split(r"[^A-Z0-9]+", clean(s or "").upper()) if t and t not in ("ACH", "COPY", "LIBRA")]


def hook_of(h):
    return re.sub(r"\s+", "", (h or "").upper())


def concept_of(c):
    c = str(c).strip().upper()
    return str(int(c)) if c.isdigit() else c


def codes(name):
    """(concept, hook) from an ad name: 'ACH - MAX - 94 - H4 - Copy' -> ('94','H4'), 'ACH-YRK-86(2)' -> ('86','(2)'),
    'ACH - MAX - 94' -> ('94',''), 'LC_V03_remix94_H4' -> ('94','H4'). (None, None) when the name has no code."""
    s = re.sub(r"\s*-\s*COPY(\s*\d+)?\s*$", "", clean(name or "").upper().strip())
    if re.match(r"^LC[_\s-]", s) and re.search(r"REMIX\s*(\d+)", s):
        m = re.search(r"REMIX\s*(\d+)(?:\s*[-_ ]*\s*(H\d{1,2}|\(\d{1,2}\)))?", s)
        return concept_of(m.group(1)), hook_of(m.group(2))
    m = re.search(r"(?<![A-Z0-9])(\d{1,4})\s*[-_ ]*\s*(H\d{1,2}|\(\d{1,2}\))(?![A-Z0-9])", s)
    if m:
        return concept_of(m.group(1)), hook_of(m.group(2))
    m = re.match(r"^ACH\s*[-_ ]\s*[A-Z]+\s*[-_ ]\s*(\d{1,4})\s*$", s)
    return (concept_of(m.group(1)), "") if m else (None, None)


def load_bank(bank=None):
    if bank is None:
        with open(BANK) as f:
            bank = json.load(f)
    return bank.get("winner_raws", bank)


def bank_codes(key, e):
    if e.get("concept") not in (None, ""):
        return concept_of(e["concept"]), hook_of(e.get("hook"))
    c, h = codes(e.get("ad", ""))
    return (c, h) if c else codes(re.sub(r"^RAW", "", key.upper()))


def match(ads, bank=None):
    """Winners -> (matched, unmatched) against clip_bank winner_raws (whole clip_bank dict or winner_raws)."""
    raws = load_bank(bank)
    entries = [dict(key=k, product=e.get("product"), ad=e.get("ad", ""), codes=bank_codes(k, e),
                    toks=tokens(e.get("ad", "")), alt=tokens(f"{e.get('concept', '')} {e.get('hook', '')}"))
               for k, e in sorted(raws.items()) if isinstance(e, dict)]
    matched, unmatched = [], []
    for a in ads:
        name, (c, h) = a["name"], codes(a["name"])
        own = bool(re.match(r"^\s*LC[_\s-]", clean(name).upper()))
        hit, why = None, None
        if c:
            same = [e for e in entries if e["codes"][0] == c]
            hit = next((e for e in same if e["codes"][1].strip("()") == h.strip("()")), None)
            if not hit and own and same:  # our own LC_..remix<N> ads: any edit of concept N
                hit = next((e for e in same if not e["codes"][1]), same[0])
            if not hit:
                if same:
                    has = ", ".join(sorted({e["codes"][1] or "no hook" for e in same}))
                    why = (f"same concept {c}, different hook (bank has {has})" if h
                           else f"same concept {c}, but the ad name has no hook code (bank has {has})")
                else:
                    why = "RAW not in clip bank yet: run pipeline/winner_prep.py"
        else:
            key, toks = norm(name), tokens(name)
            pre = lambda a_, b_: len(b_) >= 2 and a_[:len(b_)] == b_  # noqa: E731
            hit = next((e for e in entries if key and (norm(e["ad"]) == key or pre(toks, e["toks"]) or pre(e["toks"], toks)
                                                      or pre(toks, e["alt"]))), None)
            why = None if hit else "RAW not in clip bank yet (name has no concept/hook code): run pipeline/winner_prep.py"
        row = dict(name=name, ad_id=a.get("ad_id"), roas=a.get("roas"), action=a.get("action"))
        if hit:
            matched.append(dict(row, key=hit["key"], product=a.get("product") or hit["product"],
                                concept=hit["codes"][0], hook=hit["codes"][1]))
        else:
            unmatched.append(dict(row, product=a.get("product"), why=why, concept=c, hook=h))
    return matched, unmatched


# ---------------------------------------------------------------- Drive
def fetch_latest(token=None, doc_id=None):
    """(metadata, text) of the newest brief Doc in Research Briefs (or of doc_id)."""
    from drive_upload import API, access_token, api, export_text, list_children
    from index_library import load_config
    token = token or access_token()
    if doc_id:
        with api("GET", f"{API}/drive/v3/files/{doc_id}?fields=id,name,mimeType,createdTime,modifiedTime,webViewLink"
                        "&supportsAllDrives=true", token) as r:
            meta = json.load(r)
    else:
        folder = load_config()["drive"]["research_briefs_folder"]
        docs = [f for f in list_children(token, folder) if f["mimeType"] == DOC]
        if not docs:
            raise RuntimeError(f"no Google Doc in Research Briefs ({folder})")
        meta = max(docs, key=lambda f: f["createdTime"])
    return meta, export_text(token, meta["id"])


def latest(token=None, doc_id=None, text_out=None):
    meta, text = fetch_latest(token, doc_id)
    if text_out:
        with open(text_out, "w") as f:
            f.write(text)
    out = parse(text)
    created = datetime.datetime.fromisoformat(meta["createdTime"].replace("Z", "+00:00"))
    age = round((datetime.datetime.now(datetime.timezone.utc) - created).total_seconds() / 86400, 1)
    out.update(id=meta["id"], name=meta["name"], created=meta["createdTime"], age_days=age, stale=age > STALE_DAYS,
               link=meta.get("webViewLink"))
    if not out["period"]:
        out["period"] = " to ".join(re.findall(r"\d{4}-\d{2}-\d{2}", meta["name"])) or None
    return out


# ---------------------------------------------------------------- CLI
def report(b, out):
    if out:
        with open(out, "w") as f:
            json.dump(b, f, indent=1, ensure_ascii=False)
    print(json.dumps(b, indent=1, ensure_ascii=False))
    age = "age unknown" if b["age_days"] is None else f"{b['age_days']} days old" + (" - STALE" if b["stale"] else "")
    print(f"brief: {b['name']} ({age}) | ads {len(b['ads'])}, winners {len(b['winners'])}: "
          f"matched {len(b['matched'])}, unmatched {len(b['unmatched'])} | tests {len(b['tests'])}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    la = sub.add_parser("latest")
    la.add_argument("--out", help="also write the JSON here")
    la.add_argument("--text", help="save the exported brief text here")
    la.add_argument("--doc", help="Google Doc id to read instead of the newest brief")
    pa = sub.add_parser("parse")
    pa.add_argument("file", help="brief text file, or - for stdin")
    pa.add_argument("--out", help="also write the JSON here")
    a = ap.parse_args()
    if a.cmd == "latest":
        try:
            b = latest(doc_id=a.doc, text_out=a.text)
        except RuntimeError as e:
            sys.exit(str(e))
    else:
        b = parse(sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read())
    report(b, a.out)


if __name__ == "__main__":
    main()

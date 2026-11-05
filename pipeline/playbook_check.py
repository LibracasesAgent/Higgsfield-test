#!/usr/bin/env python3
"""The playbook checker: every hook, spoken line, static's words and ad copy line against the rulebook (owner 2026-11-05: "there should
be a checker that checks if the ad copy or hook adheres by the playbook").

The rules live in data, so a weekly performance review changes them without code: `pipeline/data/rulebook.json` (banned phrases, hook
formulas from Halbert's 349 headlines and our winners, the claim words that need a fact, copy limits, KPI targets), described for people
in `docs/RULEBOOK.md`. compliance.py keeps the legal side (health, politics, numbers the facts don't have, the real offer); this module
keeps the craft side: a hook that flags a reader with something concrete, no template opener a past batch used, no invented social
proof or scarcity, counts the video delivers, claims the product's facts back.

Where it runs: `ideas.py check` (and so `make_batch.py plan --ideas`): the strategist's sheet; `ad_copy.py` (a template line that fails
is skipped for the next one); `make_batch.py check --out $OUT` (ad_copy.csv after a hand edit). By hand:

  python3 pipeline/playbook_check.py --text "Meet the bag everyone is talking about" --role hook
  python3 pipeline/playbook_check.py --sheet $OUT/ideas.json --product "Hobo Bag"
  python3 pipeline/playbook_check.py --out $OUT                     # ad_copy.csv + the planned hooks
  python3 pipeline/playbook_check.py --rules                         # what is enforced, one line each
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RULEBOOK = os.path.join(HERE, "data", "rulebook.json")
ROLES = ("hook", "label", "chapter", "offer", "static", "primary_text_1", "primary_text_2", "headline", "description", "hook_first_line")
COPY_ROLES = ("primary_text_1", "primary_text_2", "headline", "description", "hook_first_line")
HOOKISH = ("hook", "hook_first_line")
NUM_WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
COUNT = re.compile(r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten)\s+(?:\w+\s+)?(things|reasons|mistakes|signs|"
                   r"secrets|questions|details|features|tricks|rules)\b", re.I)      # a list the video promises ('three ways to wear' is a fact)
THIRD = re.compile(r"\b(?:she|her|hers|he|him|his)\b", re.I)
NAMED_STORY = re.compile(r"\b(?!(?:Hobo|Libra|Bag|Set|Vintage|Slouchy|Black|Cyber|Christmas|Monday|Friday|Tap|Now|Then|One|Two|Three|Everyone|Nobody|Someone)\b)[A-Z][a-z]{2,}\s+"
                         r"(?:carried|bought|loved|wore|tried|said|says|told|swears|raves)\b")
PERSONAL = re.compile(r"\b(?:people like you|women (?:your|of your) age|at your age|over (?:40|50|60|forty|fifty|sixty)|in your (?:40s|50s|60s|forties|fifties|sixties)|"
                      r"if you(?:'ve| have) (?:ever )?been (?:robbed|pickpocketed|mugged|scammed)|as a (?:senior|widow|single mom)|"
                      r"your (?:anxiety|disability|weight|religion))\b", re.I)
PRICE_FIG = re.compile(r"\$\s?\d|\b\d+\.\d\d\b|\b\d+ dollars\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
STOP = set("the a an and or of to in on for with your you it its this that is are be at by as from up out so no not more all one".split())
_R = [None]


def rules(path=None):
    """The rulebook (data/rulebook.json), compiled once."""
    if _R[0] is None or path:
        R = json.load(open(path or RULEBOOK))
        R["_banned"] = [dict(r, _rx=re.compile(r["rx"], re.I)) for r in (R.get("banned") or {}).get("rules") or []]
        R["_formulas"] = [dict(f, _rx=re.compile(f["rx"], re.I)) for f in (R.get("hooks") or {}).get("formulas") or []]
        R["_claims"] = [dict(c, _rx=re.compile(r"(?<![\w-])(?:" + c["rx"] + r")(?![\w-])", re.I)) for c in (R.get("claims") or {}).get("rules") or []]
        _R[0] = R
    return _R[0]


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9% ]+", " ", str(t or "").lower())).strip()


def opener(t, n):
    """The first n words of a line, normalised: the part Meta and the viewer meet first."""
    return " ".join(norm(t).split()[:n])


def content_words(t):
    return {w for w in norm(t).split() if w not in STOP and len(w) > 2}


def formula_of(t):
    """The ids of the rulebook formulas a hook follows."""
    return [f["id"] for f in rules()["_formulas"] if f["_rx"].search(t or "")]


def concrete(t):
    """Does a line name something a picture can show (a footage word: keys, a zip, a train, a crowd: shotmatch's vocabulary) or a
    number?"""
    import shotmatch
    w = shotmatch.wants(t)
    return bool({k for k, v in w.items() if k != "hero"}) or bool(re.search(r"\d|\b(?:two|three|four|five|six|seven|half)\b", t or "", re.I))


def _where_ok(rule_where, role):
    if rule_where in (None, "all"):
        return True
    if rule_where == "hook":
        return role in HOOKISH
    if rule_where == "statics":
        return role == "static"
    if rule_where == "copy":
        return role in COPY_ROLES
    return rule_where == role


def lint(items, ctx=None, old_hooks=(), structure=None, numbered=None, campaign=None):
    """(problems, warnings) of items [{where, text, role}] (role: see ROLES; 'review' items are skipped: verbatim customer words).
    ctx: compliance.context() of the product (its `corpus` backs the claim words; None: claim words are not judged). old_hooks: the
    product's hooks of its last batches (the opener-reuse rule). structure: the project's story structure id (a gift / friend
    structure may talk about 'her'). numbered: how many numbered chapters the video has (a count a hook or line says must match it).
    campaign: the sale campaign dict while one runs (its confirmed end date may lift the scarcity rule)."""
    R = rules()
    H = R.get("hooks") or {}
    C = R.get("copy") or {}
    P, W = [], []

    def add(level, rid, where, msg):
        (P if level == "hard" else W).append(f"playbook {rid}: {where}: {msg}")

    corpus = (ctx or {}).get("corpus") if ctx else None
    if corpus is not None:
        import compliance
    reuse = H.get("opener_reuse") or {}
    n_open = int(reuse.get("words", 4))
    seen_open = {}
    for h in old_hooks or ():
        o = opener(h, n_open)
        if len(o.split()) >= n_open:
            seen_open.setdefault(o, h)
    sheet_open, sheet_hooks = {}, []
    lifted = {x for x in ((campaign or {}).get("lift_rules") or [])}
    for it in items:
        t, role, where = str(it.get("text") or ""), it.get("role") or "chapter", it.get("where") or "?"
        if not t.strip() or role == "review":
            continue
        for r in R["_banned"]:
            if r["id"] in lifted or not _where_ok(r.get("where"), role):
                continue
            m = r["_rx"].search(t)
            if m:
                add(r.get("level", "hard"), r["id"], where, f"{m.group(0)!r}: {r['why']}")
        if corpus is not None:
            for c in R["_claims"]:
                m = c["_rx"].search(t)
                if m and compliance.flat(m.group(0)).strip() and compliance.flat(c.get("fact") or m.group(0)) not in corpus:
                    add(c.get("level", "hard"), f"claim_{c['id']}", where, f"{m.group(0)!r}: {c['why']} (not in the product's facts)")
        m = PERSONAL.search(t)
        if m:
            add("hard", "personal_attribute", where, f"{m.group(0)!r}: Meta's personal-attributes rule: never assert or imply who the "
                "viewer is (age, a crime that happened to them, a condition)")
        m = NAMED_STORY.search(t)
        if m:
            add("hard", "invented_customer", where, f"{m.group(0)!r}: a named person's experience the brand voice tells is an invented "
                "testimonial (only a verbatim review may name a customer)")
        m = PRICE_FIG.search(t)
        if m:
            add("hard" if role in HOOKISH + ("static", "headline", "description", "primary_text_1") else "soft", "price_figure", where,
                f"{m.group(0)!r}: no price figures (prices change: B014-B027 statics went out of date); say the %")
        for m in COUNT.finditer(t):
            n = int(m.group(1)) if m.group(1).isdigit() else NUM_WORDS[m.group(1).lower()]
            if numbered is not None and role in ("hook", "chapter") and n != numbered:
                add("hard" if role == "hook" else "soft", "count_delivered", where, f"{m.group(0)!r}: the video has {numbered} numbered chapter(s): a count the line "
                    f"says must be the count the video shows")
        if role in COPY_ROLES:
            lim = {"primary_text_1": C.get("primary_text_1_max"), "headline": C.get("headline_max"),
                   "description": C.get("description_max")}.get(role)
            if lim and len(t) > lim:
                add("hard", "copy_length", where, f"{len(t)} characters (Meta shows {lim})")
            if len(EMOJI.findall(t)) > int(C.get("max_emoji", 2)):
                add("soft", "emoji", where, f"{len(EMOJI.findall(t))} emojis (at most {C.get('max_emoji', 2)})")
        if "—" in t:
            add((C.get("em_dash") or {}).get("level", "soft"), "em_dash", where, "an em dash (reads as AI copy)")
        if role not in HOOKISH:
            continue
        # ---- the hook rules
        nw = len(t.split())
        if nw < int(H.get("min_words", 4)) or nw > int(H.get("max_words", 14)):
            add("hard", "hook_length", where, f"{nw} words ({H.get('min_words', 4)}-{H.get('max_words', 14)})")
        elif nw > int(H.get("spoken_3s_words", 12)) and role == "hook":
            add("soft", "hook_3s", where, f"{nw} words: about {nw / 3.3:.1f} s spoken; the hook should land inside the first 3 s (about {H.get('spoken_3s_words', 12)} words)")
        mc = H.get("must_be_concrete") or {}
        is_c, fm = concrete(t), formula_of(t)
        if not is_c and not fm:          # neither a thing to see nor a proven shape: a statement nobody stops for
            add(mc.get("level", "hard"), "hook_generic", where, f"{t!r} names nothing a picture can show (keys, a zip, a pocket, a train, a "
                "crowd ...), no number, and follows none of the rulebook's hook formulas: rewrite it on one (docs/RULEBOOK.md section 3)")
        elif not is_c:
            add("soft", "hook_concrete", where, f"{t!r} names nothing a picture can show and no number: the opening shot cannot prove it")
        elif not fm:
            add((H.get("formula_needed") or {}).get("level", "soft"), "hook_formula", where,
                f"{t!r} follows none of the rulebook's hook formulas (how to, a question, a number, a warning, a contrast, watch, a "
                "moment, at last, the truth about, imagine, if you, who else, hidden, the offer)")
        tp = H.get("third_person") or {}
        if THIRD.search(t) and (structure or "") not in (tp.get("allowed_structures") or ()):
            add(tp.get("level", "soft"), "hook_third_person", where, f"{t!r} talks about 'her' / 'him': the viewer is 'you'")
        ty = it.get("type")
        if ty == "question" and not t.rstrip().endswith("?"):
            add("hard", "hook_type", where, "type question, but the hook is no question (end it with '?' or change the type)")
        if ty == "price" and not re.search(r"\d+\s?%|percent|half[- ]price|price|off\b|sale|black friday|cyber", t, re.I):
            add("hard", "hook_type", where, "type price, but the hook says no offer")
        o = opener(t, n_open)
        if len(o.split()) >= n_open:
            if o in seen_open:
                add(reuse.get("level", "hard"), "opener_reuse", where, f"opens like an earlier batch's hook {seen_open[o]!r} ('{o} ...'): "
                    f"Meta groups ads with the same look and story; open another way")
            elif o in sheet_open:
                add(reuse.get("level", "hard"), "opener_reuse", where, f"opens like {sheet_open[o]} ('{o} ...') of this sheet")
            sheet_open.setdefault(o, where)
        cw = content_words(t)
        for w2, t2, cw2 in sheet_hooks:
            if cw and cw2 and len(cw & cw2) / len(cw | cw2) >= 0.6:
                add("soft", "hook_near_duplicate", where, f"nearly the same words as {w2} ({t2!r})")
                break
        sheet_hooks.append((where, t, cw))
    return P, W


def numbered_chapters(p):
    return sum(1 for c in p.get("chapters") or [] if c.get("number"))


def old_hooks_of(product_name, n=None, log=None, exclude=None):
    """The hooks (H1-H4) of the product's last n batches (novelty log)."""
    import novelty
    n = n or int(((rules().get("hooks") or {}).get("opener_reuse") or {}).get("last_batches", 8))
    out = []
    for b in novelty.batches(product_name, log=log)[-n:]:
        if exclude and re.match(rf"{re.escape(str(exclude))}(?:r\d+)?\b", str(b.get("name") or "")):
            continue
        for v in b.get("videos") or []:
            out += [h for h in [v.get("hook")] + list(v.get("hooks") or []) if isinstance(h, str)]
        for s in b.get("statics") or []:
            if s.get("caption"):
                out.append(s["caption"])
    return out


def sheet_items(sheet):
    """[(items, project)] of a strategist's sheet: per project its hooks and chapters, then the statics' own words (one group)."""
    groups = []
    for p in sheet.get("projects") or []:
        pid = p.get("id") or "?"
        its = [dict(where=f"{pid} H{k}", text=h.get("text"), role="hook", type=h.get("type")) for k, h in enumerate(p.get("hooks") or [], 1)]
        its += [dict(where=f"{pid} c{j}", text=c.get("text"), role="offer" if c.get("kind") == "offer" else "chapter")
                for j, c in enumerate(p.get("chapters") or [], 1)]
        groups.append((its, p))
    st = []
    for s in sheet.get("statics") or []:
        sid = s.get("id") or "?"
        for k in ("headline", "hook", "sub", "kicker"):
            if s.get(k):
                st.append(dict(where=f"{sid} {k}", text=s[k], role="static"))
        for k, w in enumerate(s.get("words") or [], 1):
            if norm(w) != "libra":
                st.append(dict(where=f"{sid} words[{k}]", text=w, role="static"))
        for k, w in enumerate(s.get("points") or [], 1):
            st.append(dict(where=f"{sid} points[{k}]", text=w, role="static"))
    groups.append((st, None))
    return groups


def sheet_problems(sheet, pr, ctx=None, exclude=None, log=None):
    """(problems, warnings) of a whole sheet: ideas.check calls it."""
    old = old_hooks_of(pr.get("name"), log=log, exclude=exclude)
    P, W, seen = [], [], []
    for its, p in sheet_items(sheet):
        hooks_here = [i for i in its if i["role"] == "hook"]
        p_, w_ = lint(its, ctx=ctx, old_hooks=old + seen, structure=(p or {}).get("structure"),
                      numbered=numbered_chapters(p) if p else None)
        seen += [i["text"] for i in hooks_here if i.get("text")]
        P += p_
        W += w_
    return P, W


def copy_records(out, ctx=None):
    """[{where, text, category: 'playbook', term: rule id, why, level}] of $OUT/ad_copy.csv: the shape compliance.json's problems have."""
    recs = []
    f = os.path.join(out, "ad_copy.csv")
    if not os.path.exists(f):
        return recs
    for row in csv.DictReader(open(f, newline="", encoding="utf-8")):
        ad = row.get("ad_name") or "?"
        for k, v in row.items():
            role = "headline" if (k or "").startswith("headline") else k
            if role not in COPY_ROLES or not v:
                continue
            for lvl, msgs in zip(("hard", "soft"), lint([dict(where=f"{ad} {k}", text=v, role=role)], ctx=ctx)):
                for m in msgs:
                    rid, _, rest = m[len("playbook "):].partition(": ")
                    recs.append(dict(where=f"{ad} {k}", text=v, category="playbook", term=rid, why=rest.split(": ", 1)[-1], level=lvl))
    return recs


def check_out(out, pr=None, ctx=None):
    """(problems, warnings) of a planned batch's ad copy ($OUT/ad_copy.csv: every field) and its planned spoken hooks (tts_needed.json:
    the *_hook lines). Written to $OUT/playbook.json."""
    items = []
    f = os.path.join(out, "ad_copy.csv")
    if os.path.exists(f):
        for row in csv.DictReader(open(f, newline="", encoding="utf-8")):
            ad = row.get("ad_name") or "?"
            for k, v in row.items():
                role = "headline" if (k or "").startswith("headline") else k
                if role in COPY_ROLES and v:
                    items.append(dict(where=f"{ad} {k}", text=v.split("\n")[0] if role == "primary_text_1" else v, role=role))
    P, W = lint(items, ctx=ctx)
    json.dump(dict(problems=P, warnings=W), open(os.path.join(out, "playbook.json"), "w"), indent=1)
    return P, W


def packet_section(pr=None):
    """The rulebook as the strategist reads it in the strategy packet (ideas.py packet): the targets, the hook formulas with an
    example each, what is banned, the claim words that need a fact, what won and lost, and the newest weekly-review learnings."""
    R = rules()
    H, K = R.get("hooks") or {}, R.get("kpi") or {}
    hr = K.get("hook_rate") or {}
    L = [f"### The rulebook ({R.get('version')}; docs/RULEBOOK.md; `playbook_check.py` enforces it at `ideas.py check`)\n",
         f"- Targets every ad is judged on in the weekly review: hook rate (3-s plays / impressions) {hr.get('target', [0.4, 0.45])[0]:.0%}-"
         f"{hr.get('target', [0.4, 0.45])[-1]:.0%} (floor {hr.get('floor', 0.25):.0%}), hold rate {(K.get('hold_rate') or {}).get('good', 0.3):.0%}, "
         f"CTR {(K.get('ctr') or {}).get('good', 0.05):.0%}, ROAS {(K.get('roas') or {}).get('good', 2.4)}, CPA under ${(K.get('cpa') or {}).get('good', 30):.0f}. "
         f"The hook rate is won in the first 3 s: the hook line, the first picture, the label.",
         f"- Every hook: {H.get('min_words', 4)}-{H.get('max_words', 14)} words (spoken in 3 s: about {H.get('spoken_3s_words', 12)}), names "
         f"something the picture shows (keys, a zip, a pocket, a train, a crowd) or a number, follows one formula below, never opens "
         f"with the same {(H.get('opener_reuse') or {}).get('words', 4)} words as a hook of the last "
         f"{(H.get('opener_reuse') or {}).get('last_batches', 8)} batches or of this sheet. The `type` must fit the words (a question ends '?').",
         "\nHook formulas (Halbert's 349 headlines + our winners; write each hook on one, 3+ formulas a project):\n"]
    L += [f"- `{f['id']}` {f['name']}: \"{f['example']}\" ({f['source']})" for f in R["_formulas"]]
    aw = H.get("attention_words") or {}
    if aw:
        L += [f"\nAttention words that fit the brand: {', '.join(aw.get('use') or [])}. Never: {', '.join(aw.get('avoid') or [])}."]
    L += ["\nBanned in every line we write (hard = the check refuses the sheet):\n"]
    L += [f"- [{r.get('level', 'hard')}] {r['id']}: /{r['rx']}/ ({r['why']})" for r in R["_banned"]]
    L += ["\nClaim words that need the product's facts (section 1) behind them:\n"]
    L += [f"- {c['id']}: /{c['rx']}/ ({c['why']})" for c in R["_claims"]]
    for k, head in (("winning_patterns", "What won (build on it)"), ("losing_patterns", "What lost (never again)")):
        it = (R.get(k) or {}).get("items") or []
        if it:
            L += [f"\n{head}:\n"] + [f"- {x['rule']} ({x.get('evidence', '')})" for x in it]
    perf = os.path.join(HERE, "data", "performance.json")
    if os.path.exists(perf):
        try:
            import weekly_review
            L += ["\n" + weekly_review.packet_lines(json.load(open(perf)), (pr or {}).get("name"))]
        except Exception:  # noqa: BLE001
            pass
    log = R.get("changelog") or []
    if log:
        L += ["\nNewest rulebook changes (weekly reviews):\n"] + [f"- {x['date']} ({x.get('who', '?')}): {x['change']}" for x in log[-6:]]
    return "\n".join(L)


def describe():
    R = rules()
    print(f"rulebook {R.get('version')}: {RULEBOOK}")
    for r in R["_banned"]:
        print(f"  [{r.get('level', 'hard')}] {r['id']} ({r.get('where', 'all')}): {r['why'][:110]}")
    for c in R["_claims"]:
        print(f"  [{c.get('level', 'hard')}] claim_{c['id']}: {c['why'][:110]}")
    H = R.get("hooks") or {}
    print(f"  hooks: {H.get('min_words')}-{H.get('max_words')} words, concrete ({(H.get('must_be_concrete') or {}).get('level')}), "
          f"opener reuse over {(H.get('opener_reuse') or {}).get('last_batches')} batches, {len(R['_formulas'])} formulas")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", action="append")
    ap.add_argument("--role", default="hook", choices=ROLES)
    ap.add_argument("--sheet")
    ap.add_argument("--product")
    ap.add_argument("--out")
    ap.add_argument("--rules", action="store_true")
    a = ap.parse_args()
    if a.rules:
        describe()
        return 0
    ctx = pr = None
    if a.product:
        import compliance
        import ideas
        pr = ideas.product_of(a.product)
        ctx = compliance.context(pr)
    if a.sheet:
        sheet = json.load(open(a.sheet))
        pr = pr or __import__("ideas").product_of(sheet.get("product"))
        P, W = sheet_problems(sheet, pr, ctx=ctx)
    elif a.out:
        P, W = check_out(a.out, pr, ctx)
    else:
        P, W = lint([dict(where=f"text {i + 1}", text=t, role=a.role) for i, t in enumerate(a.text or [])], ctx=ctx)
    for x in P:
        print("PROBLEM", x)
    for x in W:
        print("warning", x)
    print(f"{len(P)} problem(s), {len(W)} warning(s)")
    return 2 if P else 0


if __name__ == "__main__":
    sys.exit(main())

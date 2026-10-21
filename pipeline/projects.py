#!/usr/bin/env python3
"""Project mode: every planned video becomes a PROJECT delivered in N hook versions (H1-H4), the way the client's
agencies deliver ("ACH - MAX - 94 - H4" = project 94, hook 4). One project = one body (story, features, reviews,
offer, end card); its versions differ ONLY in the first 2-5 s: the spoken opening line, the opening shot and the
hook label on screen. Statics are not touched.

  python3 pipeline/projects.py expand --out $OUT [--hooks 4] [--seed N] [--only P02H3] [--budget X]
      After `make_batch.py plan`: Vnn -> project Pnn with hooks H1..H4. The command (not the library call) then writes
      the ad copy again (ad_copy.csv) and re-runs the compliance check (exit 2 on a problem), as plan does.
      H1 = the planned spec, unchanged (renamed <prefix>_P01_H1_<angle>). H2..H4 = copies where only the hook differs:
        storyboard specs: blocks[0] (a new spoken hook from pipeline/data/hooks.json, voiced in the same voice as the
          planned hook, over another opening shot from the product's hook clips / B-roll / feature picks / photos, never
          the planned hook's shot or block 1's first clip, never a shot the body plays as a spare (that block would take
          another: the body would change) and a shot the body shows at all only when nothing else is left; a long line
          also gets a 'spare' 2nd shot the body never shows (none free: the same photo closer, CLOSER), used only if its
          voice runs past 4 s; the hook pad stays, so the line finishes before the body) and the block-0 label; every
          other block, overlay, the offer and the end card stay byte-identical, so the body voiceovers are shared (only
          P01H2_hook.mp3 ... are new);
        remix specs (winner videos): another entry of clip_bank winner_raws[key].edit.cold_opens per hook
          (its range + label + type; range null = no cold open, the RAW's own first line under that label; "variant":
          "label" = a text-hook variant, another entry's opening under another label, for a RAW without 4 clean spoken
          openings: taken after the real ones and named in the warnings, "H4 differs from H1 by its on-screen hook
          only"); two cold opens sharing words never go in one project (a variant and its twin excepted); another
          project of the same winner (make_batch plans one only when the RAW has --hooks more cold opens) takes
          openings the earlier one does not have; repeated hook types and openings that already went out in a
          committed batch (pipeline/recipes/daily and recipes/winners) are named in the warnings.
      4 hooks of different types per storyboard project (problem, curiosity, question, feature, offer, gift, travel,
      POV, story), theme hooks first (make_batch THEMES), then the product's lines (hooks.json, or a product file's own
      "hooks" list, POV / question lines made of its feature lines' own words (feature_hooks) and its feature lines),
      then generic ones; across the batch the least-used line comes first, and a line said in another project gets
      another opening shot and label; never a line the body says in its first 3 blocks, never two lines of one feature
      in a project; a spoken hook in more than 2 versions of the batch is named in the warnings. A version with no
      honest line or no opening shot left (thin products) is left out with a warning, never written for `check` to
      reject.
      ugc storyboards (make_batch's default format, "mode": "ugc" specs; plan.json videos[].ugc): H1 is the script's hook, H2-H4
      are its alt_hooks (ugc_script: other hook types than H1's first, rotated by --hook-seed minus the plan's --seed), each with
      its own label, voiced as `P01H2_hook.mp3` and shown over the footage of its feature (or the product's hook clips); the
      body's chapter takes are shared by the 4 versions. storyboard plans the hook after the body and repeats no moment within
      10 s, so a hook may open on a shot the body shows later and the "body plays it as a spare" rule does not apply.
      Writes the new spec files, plan.json (videos: one entry per hook with project/hook/hook_text/...; "projects"),
      tts_needed.json (+ the new hook lines, de-duplicated), est_credits. The plan as make_batch wrote it is kept in
      $OUT/_before_hooks/; a re-run builds from there (another --seed without re-planning). Everything is checked
      before anything is written: a refused run (bad --only, over the budget) leaves $OUT exactly as it was.
      Fixing after QA: a BODY problem (any block after the hook, overlays, offer, end card) goes into
      $OUT/_before_hooks/<the Vnn spec>.json, then re-run expand (same --seed): every version gets it. A HOOK problem
      goes into that version's P..H.. spec, after the last expand (a re-expand rebuilds every version from
      _before_hooks/; edited specs are copied to _before_hooks/edited/ and named in the warnings).
  python3 pipeline/projects.py show --out $OUT [--json]
      The projects with their hook lines, labels, types and opening shots.
  python3 pipeline/projects.py sheet --out $OUT [--only P01]
      After render: qa/P01.jpg ... one QA image per project: H1-H4 side by side (frames at 0.3/1.2/2.4/3.6 s), the body
      once (from H1, else the first rendered version: a redo --out has no H1), and how closely each body matches it.
  python3 pipeline/projects.py check --out $OUT [--build]
      Before render: H1..Hn differ only in the hook, bodies identical, hook texts/labels/shots distinct, hook types
      distinct (storyboard), no new opening on block 1's shot, no hook shot the body plays as a spare (the rendered body
      would differ), cold opens not overlapping (remix), overlay blocks valid, every source resolves, every voiceover is
      in tts_needed (or a duplicate). --build also runs storyboard.build / remix.build on every spec (needs the voiceover mp3s) and checks the
      client's cadence and pacing rules: no piece of someone's speech starting/ending mid-sentence, no B-roll shot over
      MAX_SHOT s, no picture at all over MAX_VISUAL s without a cut (a customer's clip included), >= remix.PAUSE s after
      the hook line before the body, >= storyboard.CLIP_PAD s after a customer's last word before the narrator speaks
      again, >= remix.TAIL s after the last line.
  python3 pipeline/projects.py cadence [raw94_H4 ...]
      Audits the clip bank: every winner_raws cold open, body piece (cuts; the insert point used by --winner-reviews) and
      every real-customer range (built-in products, product files) starts at a sentence start and ends at a sentence end
      (final punctuation and remix.PAUSE s before the next word, or the recording's end), on the committed transcripts.
      Also: no product's B-roll / hook / feature pick is a real customer's own clip or a moment someone talks (a word of
      its committed transcript within the shot): muted under the narrator, her lips would move under another voice.
      Exit 1 on any problem. (winner_prep.py --check then measures the audio and the edge frames at each boundary.)

Library use (make_batch.py): `projects.expand(out, hooks=4, seed=a.seed, budget=a.budget)` returns the summary dict;
`projects.voice_files(out, videos)` lists the mp3s a set of plan.json video entries needs.
Names: a project version is <prefix>_P01_H1_<angle> (docs/NAMING.md: the ID part is Pnn_Hn instead of Vnn).
"""
import argparse
import contextlib
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
LIB = os.path.join(HERE, "data", "hooks.json")
BANK = os.path.join(HERE, "data", "clip_bank.json")
TRANS = os.path.join(HERE, "data", "transcripts")
FONT = os.path.join(HERE, "assets", "fonts", "Montserrat.ttf")
BK = "_before_hooks"
TYPES = ("problem", "curiosity", "question", "feature", "offer", "gift", "travel", "POV", "story")
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
STILL = (".png", ".jpg", ".jpeg", ".webp")
CREDITS_PER_LINE = 0.35            # as make_batch.plan's estimate
SAME_SHOT = 2.5                     # two picks of one clip closer than this (s) are the same shot
MAX_SHOT = 4.0                      # longest B-roll shot (remix.MAX_SHOT / storyboard)
MAX_VISUAL = 5.0                    # longest picture without a cut, a customer's clip included (storyboard reframes it)
COLOUR_Q = "Which colour are you?"
MAX_WORDS = 15                      # longest hook line (~5.5 s at make_batch.WPS)
B1_SCENE = 8.0                      # an opener this close (s) to block 1's first shot in the same clip is the same scene
OVERLAP = 0.3                       # two cold opens sharing more than this (s) of the RAW say the same words twice
WRITTEN = "expanded.json"           # _before_hooks/expanded.json: md5 of every spec expand wrote (hand edits show up)
RECIPES = [os.path.join(HERE, "recipes", d) for d in ("daily", "winners")]   # committed batches (make_batch.py specs):
#                                                     winner openings already out (catalog and winners pipelines)
NEAR = 4.0                          # another vetted moment of a feature's clip this close (s) to its pick: that feature
CLOSER = [1.2, 1.26]                # a long hook line on a photo with no free 2nd shot: the photo again, closer


def mb():
    import make_batch               # THEMES, PRODUCTS, product files, offer templates; copy_and_check after expand
    return make_batch


def rot(xs, k):
    xs = list(xs)
    return xs[k % len(xs):] + xs[:k % len(xs)] if xs else xs


def norm(s):
    return " ".join(re.findall(r"[a-z0-9%']+", (s or "").lower()))


def wps():
    return getattr(mb(), "WPS", 2.7)


def say_secs(text):
    return len((text or "").split()) / wps() + 0.25


PROBLEM = re.compile(r"\b(digg|lost|los[et]|swallow|bottomless|black hole|pickpocket|thie|stolen|robb|mess|tired|heavy|"
                     r"hurts?|worr|anxious|loose|target|sagg|cheap|fray|fake|regret|struggl)", re.I)
OFFERY = re.compile(r"%|\bpercent\b|half price|\bdeals?\b|\bsales?\b|\boff\b(?! the)|\bfree\b|\bprice\b|tonight|"
                    r"last (?:few|call|chance)|almost gone|sell out|selling", re.I)


def classify(text):
    """Hook type of a line nobody typed (a theme hook missing from hooks.json, a cold open, a --lines hook)."""
    t = (text or "").strip()
    low = t.lower()
    if low.startswith("pov"):
        return "POV"
    if re.search(r"\bgift|\bpresent\b|christmas|\bmum\b|\bmom\b|mother", low):
        return "gift"
    if OFFERY.search(t):
        return "offer"
    if re.search(r"\btravel|\btrip\b|passport|packing|vacation|heading away|holiday", low):
        return "travel"
    if t.endswith("?") or re.match(r"(want to know|guess|what if|have you|would you|do you|did you)\b", low):
        return "question"
    if PROBLEM.search(t):
        return "problem"
    if re.search(r"\b(pocket|zip|strap|leather|stitch|lining|rfid|compartment|clasp|hardware|seams?)\b", low):
        return "feature"
    return "curiosity"


def rel_to(out, f):
    f = os.path.abspath(f)
    return os.path.relpath(f, out) if f.startswith(out + os.sep) else f


def load_json(p, default=None):
    return json.load(open(p)) if os.path.exists(p) else default


def dump(o, p):
    json.dump(o, open(p, "w"), indent=1, ensure_ascii=False)


# ---------------------------------------------------------------- plan context
class Ctx:
    """Everything expand needs about one planned batch: product (offer as plan resolved it), hook library, shots."""

    def __init__(self, out, p, tts, warnings):
        self.out, self.p, self.warn = out, p, warnings
        self.lib = json.load(open(LIB))
        self.tts = {t["file"]: t for t in tts}
        self.dupes = dict(p.get("tts_dupes") or {})
        self.theme = p.get("theme") or "default"
        self._pr = None
        self._bank = None

    # voiceover lines
    def item(self, f):
        return self.tts.get(f) or self.tts.get(self.dupes.get(f, ""))

    def text_of(self, f):
        return (self.item(f) or {}).get("text", "")

    # product, with the offer exactly as plan resolved it (plan.json 'offer': "50% off + free matching pouch wallet")
    @property
    def pr(self):
        if self._pr is None:
            m = mb()
            src = self.p.get("product_source") or ""
            pdir = os.path.dirname(src) if src.endswith(".json") and os.path.exists(src) else m.products_dir(None)
            files = m.product_files(pdir)
            pk = self.p.get("product_key")
            if pk not in m.PRODUCTS and pk not in files:
                pk = m.pick_product(self.p.get("product") or "", files) or "hobo bag"
            pr = m.product(pk, files, [])
            pct, gift = parse_offer(self.p.get("offer"))
            if pr["source"] == "built-in":
                pr["offer"] = m.builtin_offer(pct, gift, pr["deal"])
            else:
                o = dict(pr["offer"] or {})
                o["badge"] = dict(o.get("badge") or {"top": "NOW", "bottom": "OFF"}, big=f"{pct}%") if pct else None
                o["gift"] = gift
                pr["offer"] = o
            pr["_vars"] = m.offer_vars(pr)
            pr["_deal"] = (pct, gift)
            pr["_hooks"] = ((files.get(pk) or {}).get("hooks") or []) if pr["source"] != "built-in" else []
            self._pr = pr
        return self._pr

    @property
    def bank(self):
        if self._bank is None:
            self._bank = json.load(open(BANK))
        return self._bank

    def honest(self, s):
        import new_product
        pct, gift = self.pr["_deal"]
        return s and not new_product.unbacked(s, pct, gift)

    def fill(self, t):
        s = mb().tpl(t, self.pr["_vars"]) if t else None
        return s if s and self.honest(s) else None

    # ---------- hook candidates (one list per batch)
    def candidates(self):
        m, lib, pr = mb(), self.lib, self.pr
        out, seen = [], set()
        tl = lib["types"]

        def add(source, text_t, e, labels=None):
            text = self.fill(text_t)
            loose = " ".join(re.sub(r"^the |\bright now\b", "", norm(text)).split())   # 'The X is ... (right now).' once
            if not text or loose in seen:
                return
            typ = e.get("type") if e.get("type") in TYPES else classify(text)
            labs = [x.upper() for x in (self.fill(lab) for lab in (labels or e.get("labels") or [])) if x]
            labs += [x.upper() for x in (self.fill(lab) for lab in tl.get(typ, [])) if x and x.upper() not in labs]
            seen.add(loose)
            out.append(dict(text=text, type=typ, labels=labs, feature=e.get("feature"), formats=e.get("formats"),
                            source=source, template=text_t, per_feature=bool(e.get("per_feature")), base=e.get("base")))
        th = m.THEMES.get(self.theme) or m.THEMES["default"]
        for t in th.get("hooks") or []:
            add("theme", t, lib["theme_hooks"].get(t) or {})
        if pr["source"] == "built-in":
            for e in lib["products"].get(pr["key"], []):
                add("product", e["text"], e)
        else:                                    # a product file's own "hooks" (checked by new_product.py check)
            for e in pr.get("_hooks") or []:
                e = {"text": e} if isinstance(e, str) else e
                if isinstance(e, dict) and isinstance(e.get("text"), str):
                    add("product", e["text"], e)
            for typ, text, labels, tag, line in self.derived():   # POV / question lines of its own feature words
                add("product", text, dict(type=typ, feature=tag, base=line), labels=labels)
        if self.theme != "default":
            for t in m.THEMES["default"].get("hooks") or []:
                add("evergreen", t, lib["theme_hooks"].get(t) or {})
        for e in lib["generic"]:
            if not e.get("per_feature"):
                add("generic", e["text"], e)
            elif pr["source"] != "built-in":     # built-ins have their own feature hooks
                for line, tag, _ in pr["features"]:
                    add("generic", e["text"].replace("{line}", line), dict(e, feature=tag, base=line),
                        labels=[x.replace("{TAG}", tag) for x in e.get("labels") or []])
        return out

    def derived(self):
        """feature_hooks() of a product file's features that pass the compliance check (only true claims: the lines
        reuse the feature's own words, checked against the product's facts like every voiced line)."""
        import compliance
        pr = self.pr
        got = feature_hooks(pr["features"])
        if not got:
            return []
        cx = compliance.context(pr, offer=pr["_deal"])
        return [g for g in got if not compliance.check([g[1]], ctx=cx) and self.honest(g[1])]

    def type_of(self, text, cands):
        """Type of a planned hook line: the library's (theme hooks as filled, or with the colours question added),
        else classify()."""
        base = re.sub(r"\s*" + re.escape(COLOUR_Q) + r"$", "", text or "").strip() or text
        for c in cands:
            if norm(c["text"]) in (norm(text), norm(base)):
                return c["type"]
        for t, e in self.lib["theme_hooks"].items():
            if t.startswith("_"):
                continue
            f = self.fill(t)
            if f and norm(f) in (norm(text), norm(base)):
                return e["type"]
        return classify(base)

    # ---------- opening shots (one list per batch)
    def shots(self):
        m, pr, b, out = mb(), self.pr, self.bank, self.out
        packs = [rel_to(out, f) for f in self.p.get("packshots") or [] if os.path.exists(f)]
        pfile = {k: f for k, f in (self.p.get("photo_files") or {}).items() if os.path.exists(os.path.join(out, f))}
        file_clips = []
        if pr["source"] != "built-in":
            for i, c in enumerate(pr.get("clips") or []):
                src = os.path.join(ROOT, c["path"]) if c.get("path") else None
                if not (src and os.path.exists(src)):
                    src = os.path.join(out, "clips", f"{i:02d}_{m.safe_name(c.get('name', 'clip.mp4'))}")
                file_clips.append(src if os.path.exists(src) else None)
        fits = set(pfile.values()) | {c for c in file_clips if c}     # the product file's own media: "fit" as in the body

        def fx(src):
            return {"fit": m.FIT_CLIP if src in file_clips else "auto"} if src in fits else {}

        def resolve(pk):
            if not pk:
                return None
            if pk[0] == "photo":          # ["photo", "P3"]: the product file's photos[3] (plan.json photo_files; a face: none)
                f = pfile.get(pk[1].strip()) if isinstance(pk[1], str) else packs[pk[1] % len(packs)] if packs else None
                return dict(src=f, start=0, still=True, **fx(f)) if f else None
            if pk[0] == "clip":
                c = file_clips[pk[1]] if isinstance(pk[1], int) and 0 <= pk[1] < len(file_clips) else None
                return dict(src=c, start=pk[2], still=False, **fx(c)) if c else None
            try:
                src = b[pk[0]][pk[1]]["id"]
            except (KeyError, IndexError, TypeError):
                return None
            if str(src).startswith("http") or str(pk[1]).startswith("ai_"):     # real footage only
                return None
            return dict(src=src, start=pk[2], still=False, name=f"{pk[0]}/{pk[1]}")
        def good_of(pk, s):             # other vetted moments of a clip: clip_bank 'good', a product file's clip 'good'
            if s.get("name"):
                return (b.get(pk[0]) or {}).get(pk[1], {}).get("good") or []
            if pk[0] == "clip" and isinstance(pk[1], int) and 0 <= pk[1] < len(pr.get("clips") or []):
                return pr["clips"][pk[1]].get("good") or []
            return []
        cust = {(c[0], c[1]) for c in pr.get("customer") or []}
        talk = {}

        def talks(s):                 # someone speaks on camera there (committed transcript): never a muted opening shot
            if s["still"]:
                return False
            if s["src"] not in talk:
                import remix
                talk[s["src"]] = remix.committed(str(s["src"])) or []
            a = float(s["start"])
            return any(w["e"] > a - 0.3 and w["s"] < a + MAX_SHOT + 0.3 for w in talk[s["src"]])
        res, more = [], []
        for kind, ps in (("hook", [(None, x) for x in pr["hook_clips"]]), ("broll", [(None, x) for x in pr["broll"]]),
                         ("feature", [(f[1], x) for f in pr["features"] for x in f[2]])):
            for tag, pk in ps:
                s = resolve(pk) if pk and (pk[0], pk[1]) not in cust else None   # a customer's clip is her scene only
                if s and talks(s):
                    s = None
                if s:
                    res.append(dict(s, kind=kind, tag=tag))
                    if not s["still"]:            # (of: the pick's moment, for a feature hook's NEAR footage)
                        more += [dict(s, start=g, kind="more", tag=tag, of=float(pk[2])) for g in good_of(pk, s)
                                 if abs(g - float(pk[2])) >= SAME_SHOT and not talks(dict(s, start=g))]
        for i, c in enumerate(file_clips):    # every product-file clip's proposed starts, also of clips no pick uses
            if c:
                more += [dict(src=c, start=g, still=False, kind="more", tag=None, **fx(c))
                         for g in pr["clips"][i].get("good") or []]
        # the other vetted moments of the same clips, then the packshots
        return res + more + [dict(src=f, start=0, still=True, kind="photo", tag=None, **fx(f)) for f in packs]


OCCASION = re.compile(r"\b(?:bag|tote|purse|handbag|crossbody|clutch|enough|made|perfect|ideal|great|designed|built|"
                      r"meant|ready) for ((?:[\w'-]+,? (?:and |or )?){0,4}?(?:nights?|days?|work|office|travel|trips?|weekends?|"
                      r"evenings?|dinners?|errands|commutes?|brunch|events?|everyday|holidays?|vacations?|school)\b.*)$", re.I)
ROOM = re.compile(r"^(?:plenty of |enough |lots of )?(?:room|space) for ((?:your|a|an|all) .+)$", re.I)
FITS = re.compile(r"\b(fits|holds|carries) ((?:your|a|an|all) .+)$", re.I)


def feature_hooks(features):
    """More openings for a product file (its notes' feature lines), so a batch repeats fewer hooks: [(type, text,
    labels, tag, line)], POV and question lines made only of the line's own words plus a framing that claims nothing
    more: a contents line ('Room for your phone, wallet, keys ...', '... fits your laptop ...') -> 'Need room for your
    phone, wallet, keys ...?' / 'POV: one bag with room for ...'; an occasion line ('... bag for nights out, office days
    ...') -> 'POV: one bag for nights out, office days ...' / 'Need a bag for ...?'. Other lines give none."""
    out = []
    for f in features or []:
        line, tag = f[0], f[1]
        s = re.sub(r"^(?:first|and|plus|also|then|finally|next|inside)\b,?\s+", "", (line or "").strip(), flags=re.I)
        s = s.rstrip(" .!")
        if not s or re.search(r"[\[\]{}?:;!\"]|\.\s", s):    # one plain statement only
            continue
        m, fm, om = ROOM.match(s), FITS.search(s), OCCASION.search(s)
        if m:
            x = m.group(1)
            got = [("question", f"Need room for {x}?", [f"{tag}?"]), ("POV", f"POV: one bag with room for {x}.", ["POV", tag])]
        elif fm:
            v, x = fm.group(1).lower(), fm.group(2)
            got = [("question", f"Need a bag that {v} {x}?", [f"{tag}?"]),
                   ("POV", f"POV: one bag that {v} {x}.", ["POV", tag])]
        elif om:
            x = om.group(1)
            got = [("POV", f"POV: one bag for {x}.", ["POV", tag]), ("question", f"Need a bag for {x}?", [f"{tag}?"])]
        else:
            got = []
        out += [(typ, t, labs, tag, line) for typ, t, labs in got]
    return out


def parse_offer(s):
    s = s or ""
    mm = re.match(r"\s*(\d+)\s*% off", s)
    gift = s.split(" + ", 1)[1].strip() if " + " in s else None
    return (int(mm.group(1)) if mm else None), (gift or None)


def same_shot(a, src, start):
    return a["src"] == src and (a.get("still") or abs(float(a["start"]) - float(start or 0)) < SAME_SHOT)


def shot_name(src, bank=None):
    src = str(src)
    if DRIVE_ID.match(src):
        bank = bank or json.load(open(BANK))
        for sec, v in bank.items():
            if isinstance(v, dict) and sec not in ("_help", "voices", "winner_raws"):
                for k, e in v.items():
                    if isinstance(e, dict) and e.get("id") == src:
                        return f"{sec}/{k}"
        return src[:12] + "…"
    return os.path.basename(src)


def first_shot(blk):
    if blk.get("broll"):
        return blk["broll"][0][:2]
    return [blk["clip"], blk["range"][0]] if blk.get("clip") else None


def body_shots(blocks):
    """Every shot the body may show: each block's B-roll, its spare shots (storyboard plays them when the voice runs
    long) and its clip."""
    s = []
    for blk in blocks:
        s += [(x[0], x[1]) for x in (blk.get("broll") or []) + (blk.get("spare") or [])]
        if blk.get("clip"):
            s.append((blk["clip"], blk["range"][0]))
    return s


def body_spares(blocks, spec=None):
    """The shots the body plays only as spares (block spares, the board's spare_broll): a hook opening on one changes
    the body (storyboard never repeats a shot, so that block takes another spare)."""
    return [(x[0], x[1]) for blk in blocks for x in blk.get("spare") or []] + \
        [(x[0], x[1]) for x in (spec or {}).get("spare_broll") or []]


# ---------------------------------------------------------------- hook choice
def pick_hooks(ctx, cands, h1, n, fmt, k, uses, line_labels, said_b1, body_said):
    """n-1 new hooks for one project: types other than H1's and each other's, the least-used lines of the batch first
    (uses: line -> versions saying it so far; a generic line on a built-in bag counts one more, a line of a feature half
    the versions that opened on that feature in any words: "@<line>"), and a label this line has not had elsewhere in
    the batch when it has another (line_labels). Never a line the body says in its first
    blocks (said_b1: about 12 s, nor a POV / question line made of one: its 'base'); other body lines only when they
    are a product file's feature lines (repeating a feature 15 s later is normal); never two lines of one feature in
    one project."""
    lib = ctx.lib
    pref = lib["theme_prefs"].get(ctx.theme) or lib["theme_prefs"]["default"]
    prefer = list(pref["prefer"]) + [t for t in TYPES if t not in pref["prefer"]]
    prefer = rot(prefer, 2 * k)                       # other types first in later projects / other seeds
    avoid = set(pref.get("avoid") or [])
    pool = [c for c in cands if (not c.get("formats") or fmt in c["formats"]) and c["type"] not in avoid
            and norm(c["text"]) not in said_b1 and not (c.get("base") and norm(c["base"]) in said_b1)
            and (c.get("per_feature") or norm(c["text"]) not in body_said)
            and len(spoken(c["text"], fmt).split()) <= MAX_WORDS]           # a hook is 2-5 s
    order = rot([c for c in pool if c["source"] == "theme"], k)
    for t in prefer:
        for src in ("product", "evergreen", "generic"):
            order += rot([c for c in pool if c["source"] == src and c["type"] == t], k)
    builtin = ctx.pr["source"] == "built-in"

    def tier(c):                                      # (+ half the openings its feature had in other words)
        return uses.get(norm(c["text"]), 0) + (1 if builtin and c["source"] == "generic" else 0) + \
            (uses.get("@" + norm(c["base"]), 0) // 2 if c.get("base") else 0)
    types, texts, labels, res = {h1["type"]}, {norm(h1["text"])}, {h1["label"].upper()}, []
    for t_max in range(max(map(tier, pool), default=0) + 1):
        for c in order:
            if len(res) >= n - 1:
                break
            if c["type"] in types or norm(c["text"]) in texts or tier(c) > t_max or \
                    (c.get("base") and norm(c["base"]) in texts):
                continue
            had = line_labels.get(norm(c["text"])) or set()
            lab = (next((x for x in c["labels"] if x not in labels and x not in had), None) or
                   next((x for x in c["labels"] if x not in labels), None))
            if not lab:
                continue
            res.append(dict(c, label=lab))
            types.add(c["type"])
            texts |= {norm(c["text"]), norm(c.get("base"))} - {""}
            labels.add(lab)
    return res


def spoken(text, fmt):
    """The hook line as voiced: colours videos ask the colour question after it (as make_batch's colours hooks do)."""
    return text if fmt != "colours" or "colour" in text.lower() else f"{text} {COLOUR_Q}"


def ugc_hooks(ug, h1, n, k, said=()):
    """n-1 hooks for a ugc project (the new default storyboard format): its script's alt_hooks (ugc_script: other hook types
    than the main one first, different words, a label and, for a feature hook, the feature whose footage opens it), rotated by k
    (a redo with --hook-seed starts further down the list). Other types than H1's and each other's while the list has them,
    never H1's words or label, so H1-H4 differ in the opening line, label and shot only. said: the body's takes, normalised: a
    hook that the body says word for word (the offer chapter's own sentence) is left out."""
    alts = rot([h for h in ug.get("alt_hooks") or [] if norm(h["text"]) != norm(h1["text"])
                and h["label"].upper() != h1["label"].upper() and not any(norm(h["text"]) in t_ for t_ in said)], k)
    res, types, texts, labels = [], {h1["type"]}, {norm(h1["text"])}, {h1["label"].upper()}
    for strict in (True, False):
        for h in alts:
            if len(res) >= n - 1:
                break
            if h in res or norm(h["text"]) in texts or h["label"].upper() in labels or (strict and h["type"] in types):
                continue
            res.append(dict(h, label=h["label"].upper(), source="script", labels=[h["label"].upper()]))
            types.add(h["type"])
            texts.add(norm(h["text"]))
            labels.add(h["label"].upper())
    return res


def ugc_secs(text, spec):
    """Seconds a ugc hook line takes with the take's silence and the hook pad (make_batch.est_ugc's rule)."""
    m = mb()
    return len((text or "").split()) / (m.UGC_WPS * (spec.get("voice_speed") or m.UGC_SPEED)) + m.UGC_TAKE + \
        (spec.get("hook_pad") or m.UGC_HOOK_PAD)


def pick_shot(shots, hook, orig, b1, taken, body, k, avoid=(), scenes=(), spares=(), strict=False):
    """Opening shot for a new hook: the hook's feature footage when it can, else the product's hook clips, B-roll,
    feature picks, the other vetted moments of those clips, packshots (rotated by k). Never the planned hook's shot,
    never block 1's first shot (same clip within B1_SCENE s), never a shot another version of this project opens on:
    None when only those are left (the version is left out, as `check` would refuse it). Never a shot the body shows
    (body: its B-roll, spares, clips; make_batch's rule: no shot twice in one ad) while another is left, and then only
    one its B-roll shows anyway, never one it plays as a spare (spares: the body would change); strict (a hook's 2nd
    shot): never a body shot at all. No moment of a clip the body plays as a scene of its own (scenes: its clip blocks,
    e.g. a customer's testimony; opening on it gives her away before her label) while another is left, and not a shot
    this line already opens on in another project of the batch (avoid) while another is left. Then ranked: the hook's
    feature footage (its own picks, then another vetted moment of the same clip within NEAR s) > a clip no other version
    opens on > another moment of a used clip > a still; then a clip the body does not use at all."""
    feat = hook.get("feature")
    own = [s for s in shots if feat and s["tag"] == feat and s["kind"] != "more"]
    near = [s for s in shots if feat and s["tag"] == feat and s["kind"] == "more" and s.get("of") is not None
            and abs(float(s["start"]) - s["of"]) <= NEAR]
    order = own + near + [x for kind in ("hook", "broll", "feature", "more", "photo")
                          for x in rot([s for s in shots if s["kind"] == kind], k)]
    seen, cands = set(), []
    for s in order:
        key = (s["src"], round(float(s["start"]), 1))
        if key not in seen:
            seen.add(key)
            cands.append(s)
    base = [s for s in cands if not (orig and same_shot(s, orig[0], orig[1])) and not any(same_shot(s, t[0], t[1]) for t in taken)]
    near_b1 = (lambda s: b1 and s["src"] == b1[0] and (s.get("still") or abs(float(s["start"]) - float(b1[1] or 0)) < B1_SCENE))
    ok = [s for s in base if not near_b1(s)]
    shown = (lambda s, xs: any(same_shot(s, a, st) for a, st in xs))
    free = [s for s in ok if not shown(s, body)]
    ok = free if strict else free or [s for s in ok if not shown(s, spares)]
    if not ok:
        return None
    ok = [s for s in ok if s["src"] not in scenes] or ok
    ok = [s for s in ok if not shown(s, avoid)] or ok
    keys = {(s["src"], round(float(s["start"]), 1)) for s in own}, {(s["src"], round(float(s["start"]), 1)) for s in near}

    def score(i, s):
        key = (s["src"], round(float(s["start"]), 1))
        hint = 2 if key in keys[0] else 1 if key in keys[1] else 0
        tier = 0 if s.get("still") else 1 if (orig and s["src"] == orig[0]) or any(s["src"] == t[0] for t in taken) else 2
        fine = -0.3 if any(s["src"] == a for a, _ in body) else 0
        return (hint, tier, fine - 0.5 * (s["kind"] == "more"), -i)
    best = max(enumerate(ok), key=lambda x: score(*x))[1]
    fit = {"fit": best["fit"]} if best.get("fit") else {}     # a product-file photo / clip: framed whole, as in the body
    return [best["src"], 0, 1.0, dict({"zoom": [1.0, 1.06]}, **fit)] if best.get("still") else \
        [best["src"], best["start"], 1.0] + ([fit] if fit else [])


# ---------------------------------------------------------------- remix (winner) hooks
def raw_first_line(key, spec):
    """The RAW's own first sentence (what a version without a cold open opens on)."""
    try:
        import winner_prep
        ws = json.load(open(os.path.join(TRANS, f"{key}_words.json")))
    except (OSError, ValueError, ImportError):
        return ""
    st, cuts = spec.get("start") or 0.0, spec.get("cut") or []
    for a, b in winner_prep.sentences(ws):
        if ws[a]["s"] >= st - 0.05 and not any(x <= ws[a]["s"] < y for x, y in cuts):
            return winner_prep.text(ws, a, b)
    return ""


def cold_open_options(key, spec):
    """The winner's cold opens as hook options: never one whose words make a health claim or whose label names a health
    condition, a medical story one (its words name a condition: 'The arthritis has won.') last (compliance.cold_opens,
    Julian's health rule)."""
    import compliance
    raws = json.load(open(BANK)).get("winner_raws", {})
    cos = compliance.cold_opens(key, ((raws.get(key) or {}).get("edit") or {}).get("cold_opens") or [])
    opts, seen = [], set()
    for c in cos:
        r = c.get("range")
        sig = (tuple(r) if r else None, (c.get("label") or "").upper())
        if sig in seen:
            continue
        seen.add(sig)
        line = c.get("line") or ""
        if not r:
            line = raw_first_line(key, spec) or line
        typ = c.get("type") if c.get("type") in TYPES else classify(f"{line} {c.get('label') or ''}".strip())
        opts.append(dict(range=r, label=c.get("label") or "", text=line, type=typ,   # type: the editor's (winner_prep)
                         **({"medical": True} if c.get("medical") else {}),
                         **({"variant": c["variant"]} if c.get("variant") else {})))   # "label": a text-hook variant
    return opts


def same_opening(a, b):
    """Two cold-open ranges open the same way: both the RAW from the top (null), or sharing more than OVERLAP s."""
    return (a is None and b is None) or overlap(a, b) > OVERLAP


def sent_openings(root=None):
    """Winner openings already delivered: every remix spec in the committed batches under pipeline/recipes/daily and
    pipeline/recipes/winners (make_batch.py specs; root: one folder or a list) -> {winner key: [(range, LABEL, date)]}.
    A spec names its RAW by Drive id (winner_raws[key].id) or, in older batches, by file name (raw94_H4.mp4); the date
    is the batch folder's (the first folder under its root)."""
    roots = [root] if isinstance(root, str) else list(root or RECIPES)
    raws = (load_json(BANK, {}) or {}).get("winner_raws", {})
    by = {}
    for k, e in raws.items():
        if isinstance(e, dict):
            by[str(e.get("id"))], by[k] = k, k
    res = {}
    for r in roots:
        for dp, _, fs in os.walk(r):
            for f in sorted(fs):
                if not f.endswith(".json"):
                    continue
                try:
                    s = json.load(open(os.path.join(dp, f)))
                except (OSError, ValueError):
                    continue
                if not isinstance(s, dict) or "raw" not in s:
                    continue
                key = by.get(str(s["raw"])) or by.get(os.path.splitext(os.path.basename(str(s["raw"])))[0])
                if key:
                    date = os.path.relpath(dp, r).split(os.sep)[0]
                    res.setdefault(key, []).append((s.get("cold_open"), (s.get("hook_label") or "").upper(), date))
    return res


def remix_spec(spec, co):
    s = {k: v for k, v in spec.items() if k not in ("cold_open", "hook_label")}
    if co.get("range"):
        s["cold_open"] = list(co["range"])
    if co.get("label"):
        s["hook_label"] = co["label"]
    return s


def co_len(r):
    return (r[1] - r[0]) if r else 0.0


def overlap(a, b):
    """Seconds two cold-open ranges share (0 when either is null: the RAW from the top)."""
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0])) if a and b else 0.0


def co_sig(o):
    return (tuple(o["range"]) if o.get("range") else None, (o.get("label") or "").upper())


# ---------------------------------------------------------------- expand
def source(out):
    """(dir, plan as make_batch wrote it, plan.json as it is now). An expanded --out is read from _before_hooks/;
    nothing is changed here, so a refused expand leaves $OUT as it was."""
    cur = load_json(os.path.join(out, "plan.json"))
    if cur is None:
        sys.exit(f"{out}/plan.json not found: run make_batch.py plan first")
    if not cur.get("projects"):
        return out, cur, cur
    bk = os.path.join(out, BK)
    if not os.path.exists(os.path.join(bk, "plan.json")):
        sys.exit(f"{out}/plan.json is already expanded and {BK}/ is missing: re-run make_batch.py plan")
    return bk, load_json(os.path.join(bk, "plan.json")), cur


def backup(out, p):
    bk = os.path.join(out, BK)
    shutil.rmtree(bk, ignore_errors=True)
    os.makedirs(bk)
    for f in ["plan.json", "tts_needed.json"] + [v["name"] + ".json" for v in p["videos"]]:
        if os.path.exists(os.path.join(out, f)):
            shutil.copy(os.path.join(out, f), os.path.join(bk, f))


def md5(f):
    import hashlib
    return hashlib.md5(open(f, "rb").read()).hexdigest()


def hand_edits(out, cur):
    """Version specs of the current expansion that changed after expand wrote them: copied to _before_hooks/edited/."""
    written = load_json(os.path.join(out, BK, WRITTEN), {})
    edited = []
    for v in cur.get("videos") or []:
        f = os.path.join(out, v["name"] + ".json")
        if os.path.exists(f) and v["name"] in written and md5(f) != written[v["name"]]:
            os.makedirs(os.path.join(out, BK, "edited"), exist_ok=True)
            shutil.copy(f, os.path.join(out, BK, "edited", v["name"] + ".json"))
            edited.append(v.get("id") or v["name"])
    return edited


def hook_name(name, vid, pid, hid):
    a, sep, b = name.rpartition(f"_{vid}_")
    return f"{a}_{pid}_{hid}_{b}" if sep else f"{name}_{pid}_{hid}"


def angle_of(v):
    return v["name"].rpartition(f"_{v['id']}_")[2] or v.get("format") or ""


def shot_key(s):
    return [s[0], s[1]] if s else None


def expand(out, hooks=4, seed=1, only=None, budget=None, quiet=False):
    """Turn every planned video of $OUT into a project with `hooks` versions. Returns the summary dict (also printed by
    the CLI). Exits 2 when --only names no version or the voiceover lines with the hook versions would go over the
    budget: then nothing is written and an earlier expansion of this --out stays as it was."""
    out = os.path.abspath(out)
    src, p, cur = source(out)
    if hasattr(mb(), "use_products_dir"):      # a product file outside pipeline/data/products (--products-dir)
        mb().use_products_dir(p)
    tts = load_json(os.path.join(src, "tts_needed.json"), [])
    warnings = []
    ctx = Ctx(out, p, tts, warnings)
    n = max(1, int(hooks))
    vids = [v for v in p["videos"]]
    specs = {v["name"]: json.load(open(os.path.join(src, v["name"] + ".json"))) for v in vids}
    sb = [v for v in vids if v.get("engine", "storyboard") == "storyboard"]
    sbc = [v for v in sb if not v.get("ugc")]    # classic storyboards take their hooks from the library; ugc ones from their script
    cands = ctx.candidates() if sbc and n > 1 else []
    shots = ctx.shots() if sb and n > 1 else []
    # batch-wide: how often each line opens a version, the labels and opening shots it had (the planned H1s count)
    uses, line_labels, line_shots = {}, {}, {}

    def note_use(text, label, shot, base=None):
        t = norm(text)
        uses[t] = uses.get(t, 0) + 1
        if base:                                # "@<feature line>": openings made of one feature, in any words
            uses["@" + norm(base)] = uses.get("@" + norm(base), 0) + 1
        line_labels.setdefault(t, set()).add((label or "").upper())
        if shot:
            line_shots.setdefault(t, []).append(shot_key(shot))
    flines = {norm(f[0]): f[0] for f in ctx.pr["features"]} if sbc else {}
    for v in sbc:
        bl = specs[v["name"]].get("blocks") or []
        if bl and bl[0].get("vo"):
            lab = next((o.get("text") for o in specs[v["name"]].get("overlays") or []
                        if o.get("block") == 0 and o.get("type") == "label"), "")
            t0 = ctx.text_of(bl[0]["vo"])
            note_use(t0, lab, first_shot(bl[0]) if bl[0].get("broll") else None, flines.get(norm(t0)))
    uniq = {(t["text"], t["voice_type"], t["voice_id"]): t["file"] for t in tts}
    new_tts, new_dupes, new_specs, entries, projects, said_new = [], {}, {}, [], [], {}
    renames = []
    remix_uses, same_types, remix_had, went_out, all_used, sent = {}, [], {}, [], [], None
    for k, v in enumerate(vids):
        vid, spec = v["id"], specs[v["name"]]
        mm = re.match(r"[A-Z]+0*(\d+)$", vid)
        pid = f"P{int(mm.group(1)):02d}" if mm else f"P{k + 1:02d}"
        eng = v.get("engine", "storyboard")
        kk = seed - 1 + k
        hooks_out = []                       # (hid, spec, entry fields)
        if eng == "remix":
            w = v.get("winner") or {}
            key = w.get("key")
            opts = cold_open_options(key, spec) if key else []
            cur_co = (spec.get("cold_open"), spec.get("hook_label", ""))
            i0 = next((i for i, o in enumerate(opts) if o["range"] == cur_co[0] and o["label"] == cur_co[1]), None)
            if i0 is None:
                i0 = next((i for i, o in enumerate(opts) if o["range"] == cur_co[0]), None)
            h1 = opts[i0] if i0 is not None else dict(range=cur_co[0], label=cur_co[1], text=v.get("hook") or "",
                                                      type=classify(f"{v.get('hook') or ''} {cur_co[1]}".strip()))
            had = remix_had.setdefault(key, {})       # openings an earlier project of this winner holds -> its id
            if i0 is not None and co_sig(h1) in had:  # (make_batch plans another project of a winner only when it has
                free = [o for o in opts[i0 + 1:] + opts[:i0] if co_sig(o) not in had]   # enough cold opens for both)
                if free:
                    h1, i0 = free[0], opts.index(free[0])
            rest = [o for i, o in enumerate(opts) if i != i0]
            if i0 is not None:
                rest = rest[i0:] + rest[:i0]          # the entries after H1's in clip_bank order
            rest = rot(rest, seed - 1 + remix_uses.get(key, 0))
            remix_uses[key] = remix_uses.get(key, 0) + 1
            rest = [o for o in rest if co_sig(o) not in had] or rest
            if sent is None:
                sent = sent_openings()
            out_before = (lambda o: [d for r, _, d in sent.get(key, []) if same_opening(o["range"], r)])
            rest.sort(key=lambda o: (bool(o.get("medical")), bool(out_before(o))))   # a medical story opening last
            # (Julian's health rule), then the openings not delivered in an earlier batch first
            chosen, types = [], {h1["type"]}
            for strict in (2, 1, 0):                  # different hook types first, then the other real openings, then
                for o in rest:                        # a text-hook variant (the same opening under another label)
                    if len(chosen) >= n - 1:
                        break
                    if o in chosen or (strict and o.get("variant")) or (strict == 2 and o["type"] in types):
                        continue
                    if any(overlap(o["range"], x["range"]) > OVERLAP and not (
                            (o.get("variant") or x.get("variant")) and o["range"] == x["range"]) for x in [h1] + chosen):
                        continue                      # the same words twice in one project (a text-hook variant's twin: ok)
                    chosen.append(o)
                    types.add(o["type"])
            who = w.get("brief_name") or key
            try:                                      # the client's cadence rule on every opening (projects.py cadence)
                import remix
                wsk = remix._norm(json.load(open(os.path.join(TRANS, f"{key}_words.json"))))
                for o in [h1] + chosen:
                    for x in remix.cadence(wsk, *o["range"], f"cold open {o['label']!r}") if o.get("range") else []:
                        warnings.append(f"{pid} ({who}): cadence: {x}")
            except (OSError, ValueError, TypeError):
                pass
            if len(chosen) < n - 1:
                warnings.append(f"{pid} ({who}): only {len(chosen) + 1} different cold opens in clip_bank winner_raws: "
                                f"{len(chosen) + 1} hook versions (add cold opens to make {n})")
            vs = [h1] + chosen
            for j, o in enumerate(vs):                # a text-hook variant: same opening as another version, new label
                twin = next((f"H{i + 1}" for i, x in enumerate(vs[:j]) if x["range"] == o["range"]), None)
                if twin:
                    warnings.append(f"{pid} ({who}): H{j + 1} differs from {twin} by its on-screen hook only (label "
                                    f"{o['label']!r} over the same opening: " + (f"cold open {o['range'][0]}-{o['range'][1]}"
                                    if o["range"] else "the RAW from the top") + f"): {key} has no other clean spoken opening")
            ts = [o["type"] for o in [h1] + chosen]
            if len(set(ts)) < len(ts):
                same_types.append(f"{pid} {who} " + "+".join(f"{t_}x{ts.count(t_)}" if ts.count(t_) > 1 else t_
                                                             for t_ in dict.fromkeys(ts)))
            again = sorted({had[co_sig(o)] for o in [h1] + chosen if co_sig(o) in had})
            if again:
                warnings.append(f"{pid} ({who}): its openings repeat {', '.join(again)}'s (every cold open of {key} is used): "
                                f"plan one project per winner, or add cold opens (python3 pipeline/winner_prep.py)")
            for o in [h1] + chosen:
                had.setdefault(co_sig(o), pid)
            went_out.append((pid, who, [(f"H{j + 1}", d) for j, o in enumerate([h1] + chosen) for d in out_before(o)[:1]]))
            if len(opts) <= len(chosen) + 1:
                all_used.append((pid, who, key, len(opts)))
            for j, o in enumerate([h1] + chosen):
                hid = f"H{j + 1}"
                s = spec if o["range"] == cur_co[0] and o["label"] == cur_co[1] else remix_spec(spec, o)
                est = round((v.get("est_seconds") or 0) - co_len(cur_co[0]) + co_len(o["range"]), 1)
                wn = dict(w, cold_open=o["range"])
                hooks_out.append((hid, s, dict(hook_text=o["text"], hook_label=o["label"], hook_type=o["type"],
                                               cold_open=o["range"], est_seconds=est, winner=wn)))
        else:
            blocks = spec.get("blocks") or []
            vo0 = (blocks[0].get("vo") or blocks[0].get("talk")) if blocks else None      # (a presenter's hook is her take)
            lab_i = next((i for i, o in enumerate(spec.get("overlays") or []) if o.get("block") == 0 and o.get("type") == "label"), None)
            h1_label = spec["overlays"][lab_i]["text"] if lab_i is not None else ""
            h1_text = (blocks[0].get("text") if blocks and blocks[0].get("talk") else ctx.text_of(vo0)) if vo0 else ""
            ug = v.get("ugc")                # the ugc format: H1 is the script's hook (its own types: promise, superlative ...)
            h1 = dict(text=h1_text, label=h1_label, type=(ug["hook"]["type"] if ug else ctx.type_of(h1_text, cands)))
            orig = blocks[0]["broll"][0][:2] if blocks and blocks[0].get("broll") else None
            hooks_out.append(("H1", spec, dict(hook_text=h1_text, hook_label=h1_label, hook_type=h1["type"],
                                                opening_shot=orig, est_seconds=v.get("est_seconds"))))
            if n > 1 and not vo0:
                warnings.append(f"{pid}: block 0 is not a voiced hook: only H1")
            elif n > 1:
                item = ctx.item(vo0) or {}
                voice = dict(voice_type=item.get("voice_type") or "element",
                             voice_id=item.get("voice_id") or mb().BRAND_VOICE["voice_id"])
                fmt = v.get("format") or ""
                said = [norm(ctx.text_of(b_.get("vo"))) for b_ in blocks[1:] if b_.get("vo")]
                # never a line the body says in its first 3 blocks (~12 s): the same words twice in a few seconds
                said_b1 = {norm(ctx.text_of(b_["vo"])) for b_ in blocks[1:4] if b_.get("vo")} - {""}
                pres, pres_picked = bool(ug and ug.get("presenter")), []
                if ug:                   # (the script's alternate hooks; a hook that is a sentence of the body is left out)
                    picked = ugc_hooks(ug, h1, n, seed - (p.get("seed") or 1), said)
                    if pres:             # a presenter's hooks are her own short takes (presenter.py): no voiceover line, no B-roll shot
                        pres_picked, picked = picked, []
                else:
                    picked = pick_hooks(ctx, cands, h1, n, fmt, kk, uses, line_labels, said_b1, set(said))
                b1 = first_shot(blocks[1]) if len(blocks) > 1 else None
                taken, got = [], {}
                # (classic: a hook opening on a shot the body plays as a spare would change the body: storyboard never repeats a
                # shot. ugc plans the hook after the body, so its versions never change it)
                spares = () if ug else body_spares(blocks[1:], spec)
                body = body_shots(blocks[1:2]) if ug else body_shots(blocks[1:]) + [(x[0], x[1]) for x in spec.get("spare_broll") or []]
                #       (ugc: storyboard repeats no moment within 10 s only, so the hook may open on a shot the body shows later: a
                #        feature hook on its own feature's footage; the body's first block is what the hook's seconds touch)
                scenes = {b_["clip"] for b_ in blocks[1:] if b_.get("clip")}    # clips the body plays as scenes
                hinted = {j for j, c in enumerate(picked) if c.get("feature") and any(x["tag"] == c["feature"] for x in shots)}
                alt_sh = (ug or {}).get("alt_shots") or {}

                def sheet_shots(c):      # the strategist's hook: the shots make_batch chose for what its line says (its `show` tags), those
                    res_ = []            # that clash with nothing (H1's shot, another version's, block 1's scene, the body's first block)
                    for x in alt_sh.get(c["text"]) or []:
                        d = dict(src=x[0], start=x[1], still=str(x[0]).lower().endswith(STILL))
                        if (orig and same_shot(d, orig[0], orig[1])) or any(same_shot(d, t[0], t[1]) for t in taken) \
                                or (b1 and d["src"] == b1[0] and (d["still"] or abs(float(d["start"]) - float(b1[1] or 0)) < B1_SCENE)) \
                                or any(same_shot(d, a, st) for a, st in body):
                            continue
                        res_.append(x)
                    return res_
                for j in sorted(range(len(picked)), key=lambda j: (j not in hinted, j)):   # feature hooks choose first
                    got[j] = (sheet_shots(picked[j]) or [None])[0] or \
                        pick_shot(shots, picked[j], orig, b1, taken, body, kk + j, line_shots.get(norm(picked[j]["text"]), ()), scenes, spares)
                    if got[j]:
                        taken.append(got[j][:2])
                lost = [c["text"] for j, c in enumerate(picked) if not got[j]]
                why = ([f"only {len(picked)} other honest hook line(s) of new types fit"] if len(picked) < n - 1 else []) + \
                    ([f"no opening shot left for {', '.join(repr(t) for t in lost)} (every other shot is H1's, block 1's or "
                      f"another version's)"] if lost else [])
                picked = [(c, got[j]) for j, c in enumerate(picked) if got[j]]
                if len(picked) < n - 1 and not pres:
                    nv = len(picked) + 1
                    warnings.append(f"{pid}: {nv} hook version{'s' if nv > 1 else ''}, not {n} ({ctx.pr['name']}, {fmt}): "
                                    f"{'; '.join(why)}")
                for j, (c, shot) in enumerate(picked):
                    hid = f"H{j + 2}"
                    text = spoken(c["text"], fmt)
                    f = f"{pid}{hid}_hook.mp3"
                    kt = (text, voice["voice_type"], voice["voice_id"])
                    said_new[f] = f"{voice['voice_id']}|{text}"
                    if kt in uniq:
                        new_dupes[f] = uniq[kt]
                    else:
                        uniq[kt] = f
                        new_tts.append(dict(file=f, text=text, **voice))
                    if not ug:
                        note_use(c["text"], c["label"], shot, c.get("base"))
                    s = copy.deepcopy(spec)
                    s["blocks"][0] = dict(vo=f, broll=[shot], **({"pad": blocks[0].get("pad", 0.35)} if not ug or "pad" in blocks[0] else {}))
                    if ug:                    # ugc: a shot per phrase of the line as storyboard cuts it: the first shot opens, the
                        more = sum(m_ for _, m_ in mb().ugc_slots(text, spec.get("voice_speed") or mb().UGC_SPEED)) - 1  # rest are
                        pool = [x_ for x_ in sheet_shots(c) if x_[:2] != shot[:2]]
                        for q in range(more):  # its own spare shots, a shot the body shows only when no other is left
                            sp = pool.pop(0) if pool else pick_shot(
                                shots, c, orig, b1, taken + [shot[:2]] + [x_[:2] for x_ in s["blocks"][0].get("spare", [])],
                                body, kk + j + 5 + q, line_shots.get(norm(c["text"]), ()), scenes, spares)
                            if sp:            # (the hook's own spares are the only ones it may use: storyboard plans it last)
                                s["blocks"][0].setdefault("spare", []).append(sp)
                    elif say_secs(text) + 0.35 > MAX_SHOT - 0.7:   # a 2nd opening shot, used only if the voice runs > 4 s
                        sp = pick_shot(shots, c, orig, b1, taken + [shot[:2]], body, kk + j + 5,     # (no body shot:
                                       line_shots.get(norm(c["text"]), ()), scenes, spares, strict=True)   # none rather)
                        if sp and not same_shot(dict(src=sp[0], start=sp[1], still=str(sp[0]).lower().endswith(STILL)),
                                                shot[0], shot[1]):
                            s["blocks"][0]["spare"] = [sp]
                        elif str(shot[0]).lower().endswith(STILL):   # no free 2nd shot: the same photo closer (a
                            ex = dict(shot[3]) if len(shot) > 3 else {}   # punch-in reads as a cut; a clip has its own)
                            s["blocks"][0]["spare"] = [[shot[0], shot[1], 1.0, dict(ex, zoom=CLOSER)]]
                        else:                 # a clip with no free 2nd shot (a thin product shows most of its footage in the
                            #                   body): the same clip a moment on its footage that nothing else in the project
                            #                   shows (storyboard frames a clip twice in a row closer), so no shot stays long
                            used_ = list(body) + list(spares) + [tuple(t[:2]) for t in taken] + [tuple(shot[:2])]
                            t2 = next((round(max(float(shot[1]) + dt, 0.0), 1) for dt in (2.4, -2.4, 4.8, -4.8) if not any(
                                a == shot[0] and abs(float(x) - max(float(shot[1]) + dt, 0.0)) < SAME_SHOT for a, x in used_)), None)
                            if t2 is not None:
                                s["blocks"][0]["spare"] = [[shot[0], t2, 1.0] + list(shot[3:4])]
                    if lab_i is not None:
                        s["overlays"][lab_i] = dict(s["overlays"][lab_i], text=c["label"])
                    else:
                        s["overlays"].insert(0, dict(type="label", text=c["label"], block=0, at=0.1, dur=1.8))
                    est = round((v.get("est_seconds") or 0) - ugc_secs(h1_text, spec) + ugc_secs(text, spec), 1) if ug else \
                        round((v.get("est_seconds") or 0) - say_secs(h1_text) + say_secs(text), 1)
                    hooks_out.append((hid, s, dict(hook_text=text, hook_label=c["label"], hook_type=c["type"],
                                                   opening_shot=shot[:2], est_seconds=est, hook_source=c["source"])))
                for j, c in enumerate(pres_picked):
                    hid = f"H{j + 2}"
                    f = f"talk/{pid}{hid}_hook.mp4"
                    said_new[f] = c["text"]
                    s = copy.deepcopy(spec)
                    s["blocks"][0] = dict(talk=f, text=c["text"], scene=c.get("scene") or blocks[0].get("scene"), broll=[["TALK", 0, 1.0]],
                                          **({"pad": blocks[0]["pad"]} if "pad" in blocks[0] else {}))
                    if lab_i is not None:
                        s["overlays"][lab_i] = dict(s["overlays"][lab_i], text=c["label"])
                    else:
                        s["overlays"].insert(0, dict(type="label", text=c["label"], block=0, at=0.1, dur=1.8))
                    est = round((v.get("est_seconds") or 0) - mb().pres_secs(h1_text) + mb().pres_secs(c["text"]), 1)
                    hooks_out.append((hid, s, dict(hook_text=c["text"], hook_label=c["label"], hook_type=c["type"],
                                                   opening_shot=None, est_seconds=est, hook_source=c["source"])))
        proj = dict(id=pid, from_id=vid, angle=angle_of(v), engine=eng, format=v.get("format"), hooks=[])
        if eng == "remix":
            proj["winner"] = {x: (v.get("winner") or {}).get(x) for x in ("key", "ad", "brief_name", "roas", "action", "product")}
        for hid, s, fields in hooks_out:
            name = hook_name(v["name"], vid, pid, hid)
            e = dict(v, name=name, id=f"{pid}{hid}", project=pid, hook=hid, **fields)
            entries.append(e)
            if hid == "H1" and s is spec:
                renames.append((v["name"], name))
            else:                             # (a winner H1 that took another opening is written like H2..)
                new_specs[name] = s
                if hid == "H1":
                    renames.append((v["name"], None))
            proj["hooks"].append(dict(hook=hid, id=e["id"], name=name, hook_text=fields["hook_text"], label=fields["hook_label"],
                                      type=fields["hook_type"], **({"cold_open": fields["cold_open"]} if eng == "remix" else
                                                                    {"shot": fields["opening_shot"]}),
                                      est_seconds=fields["est_seconds"]))
        floor = 15 if eng == "remix" else 60 if v.get("format") == "story" else mb().QA_SECONDS["ugc"][0] if v.get("ugc") else 35
        #                                       (make_batch QA_SECONDS: a winner body is as long as it is; the story format runs
        #                                        1.5-2 min; the ugc format 55-80 s: a thin product's script runs shorter)
        short = [(h["hook"], h["est_seconds"]) for h in proj["hooks"] if (h["est_seconds"] or 99) < floor]
        if short and v.get("ugc"):            # (a script under the floor of plan was replaced by a classic one already)
            for e_ in entries:                # render's length check takes the warning below as the answer (no flag again)
                if e_.get("project") == pid and e_.get("hook") in {h for h, _ in short}:
                    e_["thin_script"] = True
            lo, hi = round(min(x for _, x in short)), round(max(x for _, x in short))
            warnings.append(f"{pid} ({', '.join(h for h, _ in short)}) thin script: about {lo}{'' if lo == hi else f'-{hi}'} s (the ugc "
                            f"format runs {floor}-80 s; {ctx.pr['name']} has few feature lines, reviews or colours to talk about: "
                            f"it runs as it is; more feature lines or reviews in its notes make it longer)")
        elif short:                           # one line per project (make_batch leaves short videos to this check)
            lo, hi = round(min(x for _, x in short)), round(max(x for _, x in short))
            fix = "" if eng == "remix" else (": the story format runs as long as the product's real material (features, "
                                             "customer clips, reviews) allows; add lines with --lines or use the showcase "
                                             "format") if v.get("format") == "story" else ": add lines with --lines" \
                if ctx.pr["source"] == "built-in" else (": plan already padded it with the notes' own price / colours / recap; "
                                                        "more feature lines, a price, colours or clips in the product's "
                                                        "folder make it longer (a suggestion: it runs as it is), or --lines")
            warnings.append(f"{pid} ({', '.join(h for h, _ in short)}) will run about {lo}{'' if lo == hi else f'-{hi}'} s "
                            f"(QA wants {floor}+ s){fix}")
        types = [h["type"] for h in proj["hooks"]]
        if eng != "remix" and len(set(types)) < len(types):
            warnings.append(f"{pid}: hook types repeat ({', '.join(types)})")
        projects.append(proj)


    def refuse(msg):
        print(msg + (f". Nothing was changed: {out} keeps its earlier expansion ({len(cur['videos'])} versions)"
                     if cur.get("projects") else ". Nothing was changed: plan.json still lists the planned videos without "
                     "hook versions"), file=sys.stderr)
        sys.exit(2)
    if only:                                  # a redo of some versions: P02, P02H3, 'P01H2,P03'
        ids = [x.strip().upper() for x in only.split(",") if x.strip()]
        keep = [e for e in entries if any(e["id"].startswith(x) for x in ids)]
        if not keep:
            refuse(f"--only {only}: no project/hook with that id ({', '.join(e['id'] for e in entries)})")
        kept = {e["name"] for e in keep}
        entries = keep
        new_specs = {k_: v_ for k_, v_ in new_specs.items() if k_ in kept}
        projects = [dict(pr_, hooks=[h for h in pr_["hooks"] if h["name"] in kept]) for pr_ in projects]
        projects = [pr_ for pr_ in projects if pr_["hooks"]]
    kept_h = {pr_["id"]: [h["hook"] for h in pr_["hooks"]] for pr_ in projects}
    if only:                                  # the warnings about projects this redo leaves out go too
        warnings[:] = [w_ for w_ in warnings if not re.match(r"P\d+\b", w_) or re.match(r"P\d+", w_).group(0) in kept_h]
    same_types = [x for x in same_types if x.split()[0] in kept_h]
    by_line = {}                              # one spoken hook in more than 2 versions of the batch: say so
    for pr_ in projects:
        for h in pr_["hooks"] if pr_["engine"] != "remix" else []:
            t_ = re.sub(r"\s*" + re.escape(COLOUR_Q) + r"$", "", h["hook_text"] or "").strip()
            by_line.setdefault(norm(t_), [t_]).append(pr_["id"] + h["hook"])
    for v_ in by_line.values():
        if len(v_) > 3:
            warnings.append(f"the spoken hook \"{v_[0]}\" opens {len(v_) - 1} versions of this batch ({', '.join(v_[1:])}): "
                            f"few different hook lines for {ctx.pr['name']} (more: the product file's 'hooks' list, or "
                            f"--lines P01_hook ...)")
    if same_types:
        warnings.append(f"winner projects whose versions repeat a hook type (the versions differ in the opening line and "
                        f"label): {'; '.join(same_types)}")
    gone = [(pid_, who_, [(h, d) for h, d in hs if h in kept_h.get(pid_, ())]) for pid_, who_, hs in went_out]
    gone = [f"{pid_} {who_} {', '.join(h for h, _ in hs)} ({', '.join(sorted({d for _, d in hs}))})" for pid_, who_, hs in gone if hs]
    if gone:
        warnings.append(f"winner versions that open like ads already delivered (pipeline/recipes): {'; '.join(gone)}: "
                        f"they differ from those ads only in the offer card and end card (and the review section those had); "
                        f"new openings need new cold opens (python3 pipeline/winner_prep.py)")
    for pid_, who_, key_, n_ in all_used if only else []:
        if pid_ in kept_h:
            warnings.append(f"{pid_} ({who_}) is a winner project: it holds every cold open {key_} has ({n_}), so a redo "
                            f"with another --seed changes only which opening is H1 (and the narrated reviews with "
                            f"--winner-reviews); new openings "
                            f"need new cold opens (python3 pipeline/winner_prep.py)")

    # voiceover: the plan's lines + the new hooks; only the lines the kept versions use
    all_specs = {**{new: specs[old] for old, new in renames if new}, **new_specs}
    need = set()
    for e in entries:
        need |= spec_voices(all_specs[e["name"]])
    tts_all = [t for t in tts + new_tts]
    dupes_all = {**(p.get("tts_dupes") or {}), **new_dupes}
    if only:
        need_src = need | {dupes_all[f] for f in need if f in dupes_all}
        tts_all = [t for t in tts_all if t["file"] in need_src]
        dupes_all = {d: s_ for d, s_ in dupes_all.items() if d in need}
    est = round(CREDITS_PER_LINE * len(tts_all), 1)
    limit = budget if budget is not None else p.get("budget") or float(
        (json.load(open(os.path.join(HERE, "config.json"))).get("budget") or {}).get("max_credits_per_batch") or 100)
    if est > limit:
        refuse(f"{len(tts_all)} voiceover lines with the hook versions (~{est} credits) are over the {limit}-credit budget: "
               f"fewer videos or hooks, or --budget {int(est) + 1} if the request names a bigger budget")
    missing = [f for f in need if f not in {t["file"] for t in tts_all} and f not in dupes_all]
    if missing:
        warnings.append(f"voiceover files used by the specs but not in tts_needed.json: {sorted(missing)}")

    # ---------- write (every check above passed)
    if src == out:
        backup(out, p)
    else:                                     # an earlier expansion: its version specs go, _before_hooks/ stays
        edited = hand_edits(out, cur)
        if edited:
            warnings.append(f"{', '.join(edited)}: edited by hand after the last expand; the new versions are built from "
                            f"{BK}/ without those edits (copies in {BK}/edited/). Body fixes go into {BK}/<Vnn spec>.json "
                            f"(then expand again), hook fixes into the P..H.. spec after the last expand")
        for v in cur["videos"]:
            f = os.path.join(out, v["name"] + ".json")
            if os.path.exists(f):
                os.remove(f)
    for old, new in renames:
        if any(e["name"] == new for e in entries):
            if src == out:
                os.replace(os.path.join(out, old + ".json"), os.path.join(out, new + ".json"))
            else:
                shutil.copy(os.path.join(src, old + ".json"), os.path.join(out, new + ".json"))
        elif src == out:
            os.remove(os.path.join(out, old + ".json"))
    for name, s in new_specs.items():
        dump(s, os.path.join(out, name + ".json"))
    dump({e["name"]: md5(os.path.join(out, e["name"] + ".json")) for e in entries}, os.path.join(out, BK, WRITTEN))
    sp = os.path.join(out, "tts_said.json")
    said_before = load_json(sp, {})
    now = said_new
    for f, txt in now.items():             # an earlier expand into this --out voiced other words under this name
        if f in said_before and said_before[f] != txt:
            for x in (f, os.path.splitext(f)[0] + "_words.json"):
                if os.path.exists(os.path.join(out, x)):
                    os.remove(os.path.join(out, x))
    dump({**said_before, **now}, sp)
    dump(tts_all, os.path.join(out, "tts_needed.json"))
    p.update(videos=entries, projects=projects, hooks=n, hooks_seed=seed, tts_lines=len(tts_all), tts_dupes=dupes_all,
             est_credits=est, warnings=list(dict.fromkeys((p.get("warnings") or []) + warnings)))
    dump(p, os.path.join(out, "plan.json"))
    summary = dict(projects=len(projects), versions=len(entries), hooks=n, new_hook_lines=len([t for t in new_tts if t in tts_all]),
                   tts_lines=len(tts_all), est_credits=est, budget=limit,
                   project_list=[dict(id=x["id"], angle=x["angle"], winner=(x.get("winner") or {}).get("key"),
                                      hooks=[f"{h['hook']} [{h['type']}] {h['label']}: {h['hook_text']}" for h in x["hooks"]])
                                 for x in projects],
                   warnings=warnings)
    if not quiet:
        print(json.dumps(summary, indent=1, ensure_ascii=False))
    return summary


def spec_voices(s):
    """Voiceover mp3 names a spec uses."""
    if "raw" in s:
        return {s["reviews"]["vo"]} if s.get("reviews") else set()
    return {b["vo"] for b in s.get("blocks") or [] if b.get("vo")}


def voice_files(out, videos):
    """Every voiceover mp3 the given plan.json video entries need (for render's 'missing voiceover' check)."""
    fs = set()
    for v in videos:
        f = os.path.join(out, v["name"] + ".json")
        if os.path.exists(f):
            fs |= spec_voices(json.load(open(f)))
    return sorted(fs)


# ---------------------------------------------------------------- show
def describe(out, as_json=False):
    out = os.path.abspath(out)
    p = load_json(os.path.join(out, "plan.json"))
    if not p or not p.get("projects"):
        sys.exit("no projects in plan.json: run projects.py expand first")
    if as_json:
        return print(json.dumps(p["projects"], indent=1, ensure_ascii=False))
    bank = json.load(open(BANK))
    vs = {v["name"]: v for v in p["videos"]}
    print(f"{p['prefix']}: {len(p['projects'])} projects x {p.get('hooks')} hooks = {len(p['videos'])} videos · "
          f"{p.get('tts_lines')} voiceover lines (~{p.get('est_credits')} credits)")
    for pr in p["projects"]:
        w = pr.get("winner") or {}
        print(f"\n{pr['id']}  {pr['angle']}" + (f"  (winner {w.get('brief_name') or w.get('key')})" if w else ""))
        for h in pr["hooks"]:
            v = vs.get(h["name"], {})
            if pr["engine"] == "remix":
                r = h.get("cold_open")
                shot = f"cold open {r[0]:.2f}-{r[1]:.2f}" if r else "no cold open (RAW from the top)"
            else:
                shot = f"shot {shot_name(h['shot'][0], bank)} @{h['shot'][1]}" if h.get("shot") else "shot ?"
            print(f"  {h['hook']}  [{h['type']:<9}] {h['label']:<24} ~{v.get('est_seconds') or 0:.0f}s  {shot}")
            print(f"      \"{h['hook_text']}\"")
            print(f"      {h['name']}")


# ---------------------------------------------------------------- check
def body_of(s):
    """A spec without its hook: what must be identical across a project's versions."""
    s = copy.deepcopy(s)
    if "raw" in s:
        s.pop("cold_open", None)
        s.pop("hook_label", None)
        return s
    s["blocks"] = s["blocks"][1:]
    s["overlays"] = [o for o in s.get("overlays") or [] if not (o.get("block") == 0 and o.get("type") == "label")]
    return s


def srcs_of(s):
    if "raw" in s:
        return [s["raw"]] + [x[0] for x in (s.get("reviews") or {}).get("broll", [])]
    return [x[0] for x in [y for b in s["blocks"] for y in b.get("broll", [])] if x != "TALK"] + \
        [b["clip"] for b in s["blocks"] if "clip" in b] + \
        ([x[0] for b in s["blocks"] for x in b.get("spare", [])] + [x[0] for x in s.get("spare_broll") or []]
         if s.get("mode") == "ugc" else [])        # (ugc: the spare shots too: a split shot may play any of them)


def check(out, build=False):
    out = os.path.abspath(out)
    p = load_json(os.path.join(out, "plan.json"))
    if not p or not p.get("projects"):
        sys.exit("no projects in plan.json: run projects.py expand first")
    bank = json.load(open(BANK))
    ids = {e.get("id") for sec, v in bank.items() if isinstance(v, dict) and sec not in ("_help", "voices", "winner_raws")
           for e in v.values() if isinstance(e, dict)} | {e.get("id") for e in bank.get("winner_raws", {}).values()}
    ids |= {r.get("id") for r in load_json(os.path.join(HERE, "data", "clip_index.json"), []) if isinstance(r, dict)}   # (ugc shots)
    import recut
    tts = {t["file"] for t in load_json(os.path.join(out, "tts_needed.json"), [])}
    dupes = p.get("tts_dupes") or {}
    rep, bad = [], 0
    for pr in p["projects"]:
        probs, info = [], []
        sp = {h["hook"]: json.load(open(os.path.join(out, h["name"] + ".json"))) for h in pr["hooks"]}
        h1 = sp.get("H1")
        for hid, s in sp.items():
            if h1 is not None and hid != "H1" and json.dumps(body_of(s), sort_keys=True) != json.dumps(body_of(h1), sort_keys=True):
                probs.append(f"{hid}: body differs from H1 (a body fix goes into {BK}/<the Vnn spec>.json, then expand "
                             f"again: every version gets it)")
            if "blocks" in s:
                nb = len(s["blocks"])
                for o in s.get("overlays") or []:
                    if not 0 <= o.get("block", -1) < nb:
                        probs.append(f"{hid}: overlay {o.get('type')} {o.get('text') or o.get('n')} on block {o.get('block')} "
                                     f"(only {nb} blocks)")
                if s.get("offer") and not 0 <= s["offer"].get("block", -1) < nb:
                    probs.append(f"{hid}: offer on block {s['offer'].get('block')}")
            for src in srcs_of(s):
                src = str(src)
                if DRIVE_ID.match(src):
                    if src not in ids and not os.path.exists(os.path.join(recut.MEDIA_CACHE, src)):
                        probs.append(f"{hid}: Drive id {src} is not in clip_bank and not cached")
                elif src.startswith("sw/") and p.get("colour_images"):
                    continue                    # colour swatch frames: make_batch render makes them (swatches())
                elif not src.startswith("http") and not os.path.exists(src if os.path.isabs(src) else os.path.join(out, src)):
                    probs.append(f"{hid}: {src} does not exist")
                elif src.startswith("http"):
                    probs.append(f"{hid}: {src} is a URL (AI clip?): real footage only")
            for f in spec_voices(s):
                if f not in tts and f not in dupes:
                    probs.append(f"{hid}: voiceover {f} is not in tts_needed.json / tts_dupes")
        hs = pr["hooks"]
        for fld, what in (("hook_text", "hook lines"), ("label", "labels")):
            vals = [norm(h[fld]) for h in hs]
            if len(set(vals)) < len(vals):
                (probs if pr["engine"] != "remix" else info).append(f"{what} repeat: {[h[fld] for h in hs]}")
        if pr["engine"] == "remix":
            cos = [json.dumps(h.get("cold_open")) + h["label"] for h in hs]
            if len(set(cos)) < len(cos):
                probs.append("two versions use the same cold open")
            for i, h in enumerate(hs):
                for g in hs[:i]:
                    same = h.get("cold_open") == g.get("cold_open")   # a text-hook variant (expand pairs only those)
                    if not same and overlap(h.get("cold_open"), g.get("cold_open")) > OVERLAP:
                        probs.append(f"{h['hook']} cold open {h['cold_open']} overlaps {g['hook']} {g['cold_open']} by "
                                     f"{overlap(h['cold_open'], g['cold_open']):.2f} s: the same words in two versions")
            if len({h["type"] for h in hs}) < len(hs):
                info.append(f"cold-open types repeat: {[h['type'] for h in hs]} (the versions differ in the opening line "
                            f"and label)")
        else:
            if len({h["type"] for h in hs}) < len(hs):
                probs.append(f"hook types repeat: {[h['type'] for h in hs]}")
            shots = [h.get("shot") for h in hs]
            for i, a in enumerate(shots):
                for b_ in shots[:i]:
                    if a and b_ and a[0] == b_[0] and abs(float(a[1]) - float(b_[1])) < SAME_SHOT:
                        probs.append(f"two versions open on the same shot {shot_name(a[0], bank)} @{a[1]}")
            b1 = first_shot(h1["blocks"][1]) if h1 and len(h1["blocks"]) > 1 else None
            for h in hs[1:]:
                if h.get("shot") and b1 and h["shot"][0] == b1[0] and abs(float(h["shot"][1]) - float(b1[1] or 0)) < B1_SCENE:
                    probs.append(f"{h['hook']} opens on block 1's shot {shot_name(b1[0], bank)} @{b1[1]}")
            for h in hs:
                s = sp.get(h["hook"]) or {}
                bl = s.get("blocks") or []
                spr = [] if s.get("mode") == "ugc" else body_spares(bl[1:], s)     # (ugc plans the hook last: it can't change the body)
                for x in [x[:2] for x in (bl[0].get("broll") or []) + (bl[0].get("spare") or [])] if bl else []:
                    if any(same_shot(dict(src=x[0], start=x[1], still=False), a, st) for a, st in spr):
                        probs.append(f"{h['hook']}'s hook shows {shot_name(x[0], bank)} @{x[1]}, a shot its body plays as a "
                                     f"spare: that block would take another shot, so the body would differ from the other "
                                     f"versions' (pick another hook shot)")
                if h["hook"] != "H1" and h.get("shot") and any(
                        same_shot(dict(src=h["shot"][0], start=h["shot"][1], still=False), a, st)
                        for blk in (bl[1:2] if s.get("mode") == "ugc" else bl[1:]) for a, st in [(y[0], y[1]) for y in blk.get("broll") or []]):
                    info.append(f"{h['hook']} opens on a shot its body shows again ({shot_name(h['shot'][0], bank)} "
                                f"@{h['shot'][1]}): no other shot was left")
        res = dict(project=pr["id"], angle=pr["angle"], versions=len(hs), problems=probs, notes=info)
        if build:
            import remix
            res["build"] = {}
            for hid, s in sp.items():
                bd = res["build"][hid] = build_dry(out, s)
                if bd.get("error"):
                    probs.append(f"{hid}: build failed: {bd['error']}")
                    continue
                if bd.get("anchors_missing"):
                    probs.append(f"{hid}: {bd['anchors_missing']} overlay anchor(s) not found")
                probs += [f"{hid}: cadence: {x}" for x in bd.get("cadence") or []]
                if bd.get("repeats") and s.get("mode") == "ugc":     # (storyboard's Shots.place: no other footage / framing was left)
                    info.append(f"{hid}: {bd['repeats']} shot(s) show a moment of a clip again within 10 s (nothing else to show: "
                                f"more clips or photos for that feature would fix it)")
                if bd.get("longest_shot", 0) > MAX_SHOT + 0.1:
                    probs.append(f"{hid}: a B-roll shot runs {bd['longest_shot']} s (max {MAX_SHOT}: no spare shot left)")
                if bd.get("longest_visual", 0) > MAX_VISUAL:
                    probs.append(f"{hid}: one picture runs {bd['longest_visual']} s without a cut (max {MAX_VISUAL}: Julian's "
                                 f"3-5 s pacing)")
                if bd.get("hook_gap") is not None and bd["hook_gap"] < remix.PAUSE:
                    probs.append(f"{hid}: only {bd['hook_gap']} s after the hook line before the body starts")
                if bd.get("handoff_gap") is not None and bd["handoff_gap"] < 0.45:
                    probs.append(f"{hid}: only {bd['handoff_gap']} s between a customer's last word and the narrator's next "
                                 f"line (want storyboard.CLIP_PAD: her sentence lands, a breath, then the next voice)")
                if bd.get("tail") is not None and bd["tail"] < remix.TAIL:
                    probs.append(f"{hid}: the last line ends {bd['tail']} s before the video ends (want {remix.TAIL})")
        bad += bool(probs)
        rep.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    print(json.dumps(dict(ok=not bad, projects=len(rep), with_problems=bad)))
    return not bad


def speech_end(f, floor=-40.0):
    """Seconds into a voiceover mp3 where its last sound above `floor` dB ends (TTS files are clean: no bed)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if not len(x):
        return 0.0
    hop = 160                                           # 10 ms frames
    n = len(x) // hop
    lv = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1)) + 1e-9)
    loud = np.nonzero(lv > max(floor, float(lv.max()) - 45))[0]
    return float((loud[-1] + 1) * hop / 16000) if len(loud) else 0.0


def build_dry(out, s):
    """storyboard.build / remix.build without rendering: total length, overlays, missing anchors, and the client's
    cadence and pacing rules: 'cadence:' lines (a piece of speech starting/ending mid-sentence), the longest B-roll shot
    (MAX_SHOT), the silence after the hook line (storyboard; remix: build adds the beat) and after the last line (TAIL)."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            if "raw" in s:
                import remix
                segs, audio, ov, total, _ = remix.build(s, out)
                broll = [x for x in segs if x["src"] != s["raw"] and not str(x["src"]).startswith("_hold_")]
            else:
                import storyboard
                binfo = {}
                segs, audio, ov, total, _, _ = storyboard.build(s, out, binfo)
                clips = [(b["clip"], float(b["range"][0]), float(b["range"][1])) for b in s["blocks"] if b.get("clip")]
                broll = [x for x in segs if not any(x["src"] == c and a - 0.01 <= float(x["start"]) < e for c, a, e in clips)]
    except Exception as e:  # noqa: BLE001
        return dict(error=f"{type(e).__name__}: {e}")
    hook = next((o for o in ov if o.get("type") == "label" and o.get("at", 9) <= 0.2), None)
    res = dict(seconds=round(total, 1), segments=len(segs), overlays=len(ov), hook_label=(hook or {}).get("text"),
               anchors_missing=err.getvalue().count("anchor not found"),
               cadence=[x.split("cadence:", 1)[1].strip() for x in err.getvalue().splitlines() if x.startswith("cadence:")],
               longest_shot=round(max([x["dur"] for x in broll] or [0]), 2), repeats=err.getvalue().count("repeat:"))
    if "blocks" in s:                 # every picture change, a customer's clip included (Julian: a new shot every 3-5 s)
        res["longest_visual"] = round(max([x["dur"] for x in segs] or [0]), 2)
        import remix
        hand = []                     # a real customer hands back to the narrator: silence after her last word
        for k in range(1, len(s["blocks"])):
            pb, b_ = s["blocks"][k - 1], s["blocks"][k]
            if "vo" in b_ and pb.get("clip") and not pb.get("mute"):
                ws = [w for w in remix.words(remix.loc(out, pb["clip"])) if pb["range"][0] < w["e"] and w["s"] < pb["range"][1]]
                if ws:
                    hand.append(round(max(pb["range"][1] - ws[-1]["e"], 0) + (binfo.get("leads") or [0] * 99)[k], 2))
        if hand:
            res["handoff_gap"] = min(hand)
    if "blocks" in s and s["blocks"]:
        import storyboard
        bl = s["blocks"]
        pad = s.get("pad", 0.25)
        for k, key in ((0, "hook_gap"), (len(bl) - 1, "tail")):
            if key == "hook_gap" and s.get("mode") == "ugc":
                continue                  # (ugc: one speaker talking on: the body starts UGC_HOOK_PAD s after the hook line)
            blk = bl[k]
            f = os.path.join(out, blk.get("vo") or "")
            if blk.get("vo") and "vo_range" not in blk and os.path.exists(f):
                bp = blk.get("pad", pad)
                bp = max(bp, storyboard.HOOK_PAD) if k == 0 and len(bl) > 1 else max(bp, storyboard.END_PAD) if k == len(bl) - 1 else bp
                res[key] = round(ffdur(f) + bp - speech_end(f), 2)
    return res


# ---------------------------------------------------------------- sheet
def ffdur(f):
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                    capture_output=True, text=True).stdout)
    except ValueError:
        return 0.0


def grab(f, t, w, h):
    from PIL import Image
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.2f}", "-i", f, "-frames:v", "1", "-vf", f"scale={w}:{h}",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    try:
        return Image.open(io.BytesIO(r.stdout)).convert("RGB") if r.stdout else None
    except OSError:
        return None


def hook_end(out, s):
    """Where the body starts in a version: after the cold open and the beat remix.build holds after it when its last word
    ends less than remix.PAUSE s before the body's first (remix), or after the hook block (storyboard)."""
    if "raw" in s:
        r = s.get("cold_open")
        if not r:
            return 0.0
        import remix
        ws, body = remix.committed(str(s["raw"])) or [], remix.body_pieces(s, s.get("end") or 1e9)
        got = remix.spoken_in(ws, *r)
        if not got or not body:
            return co_len(r)
        tail, p0 = max(r[1] - ws[got[-1]]["e"], 0.0), body[0]
        if p0 == "REVIEWS":                   # (the narration's own mp3 lead-in gives ~0.1 s)
            short = remix.PAUSE - 0.1 - tail
        else:
            g = remix.spoken_in(ws, *p0)
            edit = any(abs(p0[0] - e) < 0.02 for _, e in remix.claim_ranges(s))
            short = ((remix.PAUSE_EDIT if edit else remix.PAUSE) - tail - max(ws[g[0]]["s"] - p0[0], 0.0)) if g else 0
        return co_len(r) + (round(max(short, 0.12), 2) if short > 0 else 0.0)
    if s["blocks"][0].get("talk"):        # a presenter's hook: her take from her first word to her last, the edges kept + the hook pad
        import storyboard
        from remix import words
        tp = os.path.join(out, s["blocks"][0]["talk"])
        if not os.path.exists(tp):
            return 0.0
        ws = words(tp)
        return (ws[-1]["e"] + storyboard.TALK_TAIL - max(ws[0]["s"] - storyboard.TALK_HEAD, 0.0) if ws else ffdur(tp)) + \
            s["blocks"][0].get("pad", s.get("hook_pad", storyboard.UGC_HOOK_PAD))
    f = os.path.join(out, s["blocks"][0]["vo"])
    if s.get("mode") == "ugc":            # the voice-prepared take (trimmed, sped up) + the hook pad
        import storyboard
        if not os.path.exists(f):
            return 0.0
        return ffdur(os.path.join(out, storyboard.voice_prep(out, s["blocks"][0]["vo"], s.get("voice_speed", storyboard.VOICE_SPEED)))) \
            + s["blocks"][0].get("pad", s.get("hook_pad", storyboard.UGC_HOOK_PAD))
    return (ffdur(f) if os.path.exists(f) else 0.0) + s["blocks"][0].get("pad", s.get("pad", 0.25))


def sheet(out, only=None):
    from PIL import Image, ImageDraw, ImageFont
    out = os.path.abspath(out)
    p = load_json(os.path.join(out, "plan.json"))
    if not p or not p.get("projects"):
        sys.exit("no projects in plan.json: run projects.py expand first")
    os.makedirs(os.path.join(out, "qa"), exist_ok=True)

    def fnt(sz, weight="SemiBold"):
        try:
            f = ImageFont.truetype(FONT, sz)
            with contextlib.suppress(Exception):
                f.set_variation_by_name(weight)          # Montserrat is a variable font: thin by default
            return f
        except OSError:
            return ImageFont.load_default()
    bank = json.load(open(BANK))
    FW, FH, TW = 180, 320, 420
    BW, BH = 190, 338
    times = (0.3, 1.2, 2.4, 3.6)
    made = []
    for pr in p["projects"]:
        if only and not any(pr["id"].startswith(x.strip().upper()) for x in only.split(",")):
            continue
        hs = pr["hooks"]
        W_ = TW + FW * len(times)
        H_ = 70 + FH * len(hs) + 50 + 2 * BH + 60
        im = Image.new("RGB", (W_, H_), (250, 247, 242))
        d = ImageDraw.Draw(im)
        d.text((16, 14), f"{pr['id']} · {pr['angle']} · {len(hs)} hook versions", fill=(20, 20, 20), font=fnt(30, "ExtraBold"))
        d.text((16, 48), re.sub(r"_H\d+_[^_]+$", "", hs[0]["name"]), fill=(110, 110, 110), font=fnt(16))
        vids, ends, lens = {}, {}, {}
        for i, h in enumerate(hs):
            f = os.path.join(out, "videos", h["name"] + ".mp4")
            s = json.load(open(os.path.join(out, h["name"] + ".json")))
            y = 70 + i * FH
            vids[h["hook"]] = f if os.path.exists(f) else None
            ends[h["hook"]] = hook_end(out, s)
            lens[h["hook"]] = ffdur(f) if vids[h["hook"]] else 0
            d.rectangle([0, y, W_, y + FH - 1], outline=(220, 214, 205))
            d.text((14, y + 12), f"{h['hook']}  [{h['type']}]", fill=(180, 30, 36), font=fnt(26, "ExtraBold"))
            d.text((14, y + 48), h["label"], fill=(20, 20, 20), font=fnt(22, "Bold"))
            wrap, line = [], ""
            for wd in f"\"{h['hook_text']}\"".split():
                if len(line) + len(wd) > 30:
                    wrap.append(line)
                    line = wd
                else:
                    line = (line + " " + wd).strip()
            wrap.append(line)
            for j, ln in enumerate(wrap[:6]):
                d.text((14, y + 84 + j * 24), ln, fill=(60, 60, 60), font=fnt(18))
            where = (f"cold open {h['cold_open'][0]:.1f}-{h['cold_open'][1]:.1f}" if h.get("cold_open") else
                     "no cold open" if pr["engine"] == "remix" else f"shot {shot_name(h['shot'][0], bank)}" if h.get("shot") else "")
            d.text((14, y + FH - 58), where[:40], fill=(110, 110, 110), font=fnt(16))
            d.text((14, y + FH - 32), f"{lens[h['hook']]:.1f} s · body from {ends[h['hook']]:.1f} s" if vids[h["hook"]] else
                   "not rendered yet", fill=(110, 110, 110), font=fnt(16))
            for j, t in enumerate(times):
                fr = grab(f, t, FW, FH) if vids[h["hook"]] else None
                x = TW + j * FW
                if fr:
                    im.paste(fr, (x, y))
                else:
                    d.rectangle([x, y, x + FW - 1, y + FH - 1], fill=(200, 200, 200))
                d.text((x + 6, y + 6), f"{t}s", fill=(255, 255, 255), font=fnt(16, "Bold"), stroke_width=2, stroke_fill=(0, 0, 0))
        y0 = 70 + FH * len(hs) + 10
        # the body is shown from H1, or from the first rendered version (a redo --out of one version has no H1)
        ref = "H1" if vids.get("H1") else next((h["hook"] for h in hs if vids.get(h["hook"])), "H1")
        f1, e1, L1 = vids.get(ref), ends.get(ref, 0), lens.get(ref, 0)
        d.text((14, y0), f"Body ({ref} from {e1:.1f} s to the end): the same in every version", fill=(20, 20, 20), font=fnt(22))
        if f1 and L1 > e1:
            for j in range(12):
                t = e1 + 0.4 + (L1 - e1 - 0.8) * j / 11
                fr = grab(f1, t, BW, BH)
                x, y = (j % 6) * BW, y0 + 40 + (j // 6) * BH
                if fr:
                    im.paste(fr, (x, y))
                d.text((x + 6, y + 6), f"{t:.1f}s", fill=(255, 255, 255), font=fnt(16, "Bold"), stroke_width=2, stroke_fill=(0, 0, 0))
        match = body_match(vids, ends, lens, ref)
        d.text((14, H_ - 40), f"body vs {ref} (mean pixel difference, <10 = same): " +
               ("  ".join(f"{k}: {v}" for k, v in match.items()) or "not rendered yet"), fill=(60, 60, 60), font=fnt(18))
        fn = os.path.join(out, "qa", f"{pr['id']}.jpg")
        im.save(fn, quality=88)
        made.append(dict(project=pr["id"], sheet=fn, seconds={k: round(v, 1) for k, v in lens.items()}, body_match=match))
        print(json.dumps(made[-1]), flush=True)
    return made


def body_match(vids, ends, lens, ref="H1"):
    """Mean grey-level difference between the reference version's body (H1's) and each other version's body at 3
    points (captions are re-made per version, so a few points of difference are normal; a different body is far
    above 10)."""
    import numpy as np
    res = {}
    f1 = vids.get(ref)
    if not f1:
        return res
    for hid, f in vids.items():
        if hid == ref or not f:
            continue
        body = min(lens[ref] - ends[ref], lens[hid] - ends[hid])
        if body <= 2:
            continue
        ds = []
        for q in (0.25, 0.5, 0.75):
            a, b = grab(f1, ends[ref] + body * q, 90, 160), grab(f, ends[hid] + body * q, 90, 160)
            if a and b:
                ds.append(float(np.abs(np.asarray(a.convert("L"), float) - np.asarray(b.convert("L"), float)).mean()))
        if ds:
            res[hid] = round(max(ds), 1)
    return res


# ---------------------------------------------------------------- cadence (clip bank audit)
def cadence_audit(keys=None):
    """The client's cadence rule over everything real people say in our videos: every winner_raws cold open, body piece
    (around its cuts, and around the insert point with --winner-reviews) and every real-customer range (built-in products
    and product files) must start at a sentence start and end at a sentence end (remix.cadence: final punctuation and
    remix.PAUSE s before the next word, or the recording's last word), on the committed transcripts. Prints one line per
    problem; returns the number of problems."""
    import remix
    bank = json.load(open(BANK))

    def ws_of(names):
        for n in names:
            f = os.path.join(TRANS, f"{n}_words.json")
            if os.path.exists(f):
                return remix._norm(json.load(open(f)))
        return None
    bad = 0
    for key, e in (bank.get("winner_raws") or {}).items():
        if keys and key not in keys:
            continue
        ws, ed = ws_of([key]), e.get("edit") or {}
        if ws is None:
            print(f"{key}: no transcript in {TRANS}")
            bad += 1
            continue
        probs = []
        for c in ed.get("cold_opens") or []:
            if c.get("range"):
                probs += remix.cadence(ws, *c["range"], f"cold open {c.get('label')!r}")
        spec = dict(ed, cold_open=None, reviews=None)
        probs += remix.remix_cadence(spec, ws, e.get("dur") or 9999, with_reviews=False)
        if ed.get("insert_at") is not None:
            probs += [p for p in remix.remix_cadence(spec, ws, e.get("dur") or 9999, with_reviews=True) if "review" in p]
        for p in dict.fromkeys(probs):
            print(f"{key}: {p}")
        bad += len(set(probs))
        print(f"{key}: {'ok' if not probs else f'{len(set(probs))} problem(s)'} ({len(ed.get('cold_opens') or [])} openings, "
              f"{len(ed.get('cut') or [])} cuts)")
    if keys:
        return bad
    m = mb()
    files = m.product_files(m.products_dir(None))
    ranges = [(f"{p['name']}", c) for p in m.PRODUCTS.values() for c in p.get("customer") or []]
    ranges += [(d.get("name") or k, c) for k, d in files.items() for c in d.get("customer") or []]
    for who, c in ranges:
        e = ((bank.get(c[0]) or {}).get(c[1]) or {}) if isinstance(c[0], str) else {}
        ws = ws_of([x for x in (e.get("transcript"), c[1]) if x])
        if ws is None:
            print(f"{who} customer {c[0]}/{c[1]}: no committed transcript (render transcribes it)")
            continue
        probs = remix.cadence(ws, c[2], c[3], f"customer {c[1]}")
        for p in probs:
            print(f"{who}: {p}")
        bad += len(probs)
        if not probs:
            print(f"{who}: customer {c[1]} {c[2]}-{c[3]} ok")
    # B-roll picks (muted under the narrator) must never show someone talking or a customer's own clip (her scene)
    prods = [(p["name"], p) for p in m.PRODUCTS.values()] + [(d.get("name") or k, d) for k, d in files.items()]
    for who, p in prods:
        cust = {(c[0], c[1]) for c in p.get("customer") or []}
        picks = [("hook clip", x) for x in p.get("hook_clips") or []] + [("B-roll", x) for x in p.get("broll") or []]
        for f in p.get("features") or []:
            f = f if isinstance(f, (list, tuple)) else (f.get("line"), f.get("tag"), f.get("picks"))
            picks += [(f"feature {f[1]!r}", x) for x in f[2] or []]
        for what, x in picks:
            if not x or not isinstance(x[0], str) or x[0] in ("photo", "clip"):
                continue
            e = (bank.get(x[0]) or {}).get(x[1]) or {}
            if (x[0], x[1]) in cust:
                print(f"{who}: {what} pick {x[0]}/{x[1]} @{x[2]} is a real customer's own clip (her scene, never muted B-roll)")
                bad += 1
                continue
            ws = ws_of([y for y in (e.get("transcript"), x[1]) if y])
            said = [w["w"] for w in ws or [] if w["e"] > float(x[2]) - 0.3 and w["s"] < float(x[2]) + MAX_SHOT + 0.3]
            if said:
                print(f"{who}: {what} pick {x[0]}/{x[1]} @{x[2]}: someone talks there ({' '.join(said[:8])}): lips moving "
                      f"under the narrator; use a silent moment")
                bad += 1
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("expand", help="planned videos -> projects with hook versions H1..Hn")
    e.add_argument("--out", required=True)
    e.add_argument("--hooks", type=int, default=4)
    e.add_argument("--seed", type=int, default=1, help="other hook lines / shots / cold-open order (use plan's --seed)")
    e.add_argument("--only", help="keep only these versions: P02, P02H3, 'P01H2,P03'")
    e.add_argument("--budget", type=float, help="voiceover credit budget (default: plan.json's)")
    s = sub.add_parser("show", help="print the projects and their hooks")
    s.add_argument("--out", required=True)
    s.add_argument("--json", action="store_true")
    sh = sub.add_parser("sheet", help="after render: one QA image per project (qa/P01.jpg ...)")
    sh.add_argument("--out", required=True)
    sh.add_argument("--only", help="P01 or 'P01,P03'")
    cd = sub.add_parser("cadence", help="audit the clip bank: every cold open, cut, insert point and customer range on a "
                        "sentence boundary")
    cd.add_argument("keys", nargs="*", help="winner_raws keys (default: all, plus every customer range)")
    c = sub.add_parser("check", help="before render: versions differ only in the hook, sources resolve")
    c.add_argument("--out", required=True)
    c.add_argument("--build", action="store_true", help="also run storyboard/remix build on every spec (needs the mp3s)")
    a = ap.parse_args()
    if a.cmd == "expand":
        expand(a.out, a.hooks, a.seed, a.only, a.budget)
        mb_ = mb()            # the versions' names and hook lines changed: new ad copy, and every text checked again
        out = os.path.abspath(a.out)
        ac, cr = mb_.copy_and_check(out, seed=(load_json(os.path.join(out, "plan.json"), {}) or {}).get("seed") or 1)
        print(json.dumps(mb_.copy_summary(ac, cr), indent=1, ensure_ascii=False))
        if not cr["ok"]:
            print(f"compliance: {len(cr['problems'])} problem(s):\n  - " + "\n  - ".join(mb_.compliance_lines(cr)) +
                  f"\n{mb_.COMPLIANCE_FIX}.", file=sys.stderr)
            sys.exit(2)
    elif a.cmd == "show":
        describe(a.out, a.json)
    elif a.cmd == "sheet":
        sheet(a.out, a.only)
    elif a.cmd == "cadence":
        sys.exit(1 if cadence_audit(a.keys) else 0)
    else:
        sys.exit(0 if check(a.out, a.build) else 1)


if __name__ == "__main__":
    main()

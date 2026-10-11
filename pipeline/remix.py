#!/usr/bin/env python3
"""Winner variation: re-edit a textless RAW winner into a new ad (for longform.py). The proven body stays intact.

  cold open (a strong line from later in the RAW)  ->  RAW from the top (only its editorial cuts)  ->  RAW offer + CTA
  ->  end card.  Optional (make_batch plan --winner-reviews): a real-review section (narrated, verbatim review cards over
  real B-roll) inserted before the offer; by default there is none: one speaker, the body the client proved.

  python3 pipeline/remix.py remix.json --out ad.mp4

remix.json (paths relative to the JSON; any src may also be a Drive file id or an https URL):
{
  "raw": "1LEOgUgU_hBiRceIx-SW4za6XJZlCQNrH",   # RAW file (Drive id from clip_bank winner_raws, or a local file)
  "cold_open": [12.4, 16.1],          # seconds in the RAW used as the hook (also kept in place later); optional
  "hook_label": "10 YEARS LATER",     # label at 0.1 s (over the cold open, or over the RAW start without one)
  "start": 0.0, "end": null,          # RAW range used for the body
  "cut": [[a, b], ...],               # optional RAW ranges to drop (repeats, dead air)
  "insert_at": 44.3,                  # RAW time of the review section (when "reviews" is set); else only where the offer
                                      # card looks for its word (offer_after)
  "reviews": {"vo": "V01_rev.mp3", "text": "<the VO script>", "cards": [{"n": 7, "word": "carol"}, ...],
              "broll": [[src, start], ...], "spare": [[src, start], ...]},   # optional; cards anchor to their word in
                                      # the VO, in order (text = fallback timing); spare: more shots, so none runs > 4 s
  "burned_captions": false,           # RAW already has captions: skip ours
  "labels": [{"text": "REASON 1", "word": "one", "after": 8.0}],   # optional number labels (RAW times)
  "offer_word": "50", "offer_after": null,     # offer card at the first offer_word after insert_at - 1 (or offer_after)
  "offer_title": "50% OFF", "offer_sub": "+ FREE MATCHING WALLET",   # "" sub: title only
  "end_title": "The Luxury Hobo Bag", "end_sub": "Tap the link below", "keywords": [...],
  "claim_cuts": [{"range": [31.88, 33.3], "said": "that prevents shoulder pain."}],   # health claims cut from the body
  "music": false                      # default: the proven RAW keeps its own sound ({"seed": N}: a bed, music.py;
                                      # {"auto": true, "seed": N}: a bed only when the RAW has no sound under the voice)
}
Captions use the RAW's committed transcript through the edit (punctuated sentences; no transcription of the final mix).
Cadence (the client's rule: every cut lands where a sentence naturally ends): every RAW piece (cold open, body pieces
around cuts and the insert point) should start at a sentence start and end at a sentence end, i.e. final punctuation and
>= PAUSE s before the next word in the transcript, or the RAW's last word; build() prints a 'cadence:' line for each one
that doesn't (make_batch render counts them as QA flags; projects.py cadence audits the whole clip bank). Between two
lines (cold open -> body, across a cut, around the review section) build() leaves at least PAUSE s of silence, and after
the last word at least TAIL s before the video ends (a beat: the RAW's frame held), so a line
always finishes before the next one starts and the end card never cuts speech.
Transcripts: a committed pipeline/data/transcripts/<winner key>_words.json is used for clip-bank files (found by
Drive id), <name>_words.json for local files; anything else is transcribed once (faster-whisper) and cached.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TRANS = os.path.join(HERE, "data", "transcripts")
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
STILL = (".png", ".jpg", ".jpeg", ".webp")
FIN = (".", "?", "!")
PAUSE = 0.3      # a sentence ends where the speaker stops: final punctuation and this long (s) before the next word
TAIL = 0.4       # silence after the last spoken word before the video ends (the end card never cuts speech)
EDGE = 0.2       # whisper starts words early (most in run-on speech): a piece may start this far after its first
                 # word's start (winner_prep.py --check measures the audio at every boundary)
MAX_SHOT = 4.0   # longest B-roll shot (s): longer ones are split over spare shots
PAUSE_EDIT = 0.6    # silence after a sentence shortened by a claim cut (claim_ranges): it lands like a full stop (the
                    # transcript's word ends run late: 0.45 measured ~0.3 s; the speaker's own sentence pauses are ~0.5 s)


def loc(d, s):
    """Local file for s: a path relative to the spec, a Drive file id (downloaded in safe chunks and cached),
    or an https URL (downloaded once and cached). Needed wherever audio is mixed or speech is transcribed."""
    p = os.path.join(d, s)
    if os.path.exists(p):
        return p
    sys.path.insert(0, HERE)
    import recut
    if s.startswith("http"):
        import hashlib
        import urllib.request
        os.makedirs(recut.MEDIA_CACHE, exist_ok=True)
        f = os.path.join(recut.MEDIA_CACHE, hashlib.md5(s.encode()).hexdigest() + os.path.splitext(s.split("?")[0])[1])
        if not os.path.exists(f):
            part = f"{f}.part.{os.getpid()}"            # per process: parallel renders may fetch the same URL
            urllib.request.urlretrieve(s, part)
            os.replace(part, f)
        return f
    recut.LOCAL_MAX = max(recut.LOCAL_MAX, 600 * 2**20)
    f = recut.source(s)
    if f.startswith("http") and DRIVE_ID.match(s):   # not link-shared (or too big): download with the agent's login
        try:
            from drive_upload import access_token, download
            return download(access_token(), s, os.path.join(recut.MEDIA_CACHE, s))
        except (Exception, SystemExit) as e:  # noqa: BLE001
            print(f"loc: authenticated download of {s} failed ({e}); reading it over HTTP", file=sys.stderr)
    return f


def dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                capture_output=True, text=True).stdout)


_DUR = {}


def fit(d, src, st, L):
    """(start, speed) so L output seconds fit inside src: move the start back, or slow a too-short clip down
    (a segment that runs out of footage would end early and push the picture out of sync with the sound)."""
    if str(src).lower().endswith(STILL):
        return st, 1.0
    if src not in _DUR:
        try:
            _DUR[src] = dur(loc(d, src))
        except (ValueError, OSError):
            _DUR[src] = None
    D = _DUR[src]
    if not D or st + L <= D - 0.05:
        return st, 1.0
    if L <= D - 0.1:
        return round(D - L - 0.1, 3), 1.0
    return 0.0, round(max((D - 0.1) / L, 0.25), 3)


def _norm(ws):
    return [w if isinstance(w, dict) else dict(w=w[0], s=w[1], e=w[2]) for w in ws]


def committed(path):
    """Committed transcript for a cached clip-bank file (by Drive id) or a local file (by base name)."""
    base = os.path.splitext(os.path.basename(path))[0]
    names = []
    try:
        bank = json.load(open(os.path.join(HERE, "data", "clip_bank.json")))
        for sec, v in bank.items():
            if isinstance(v, dict) and sec not in ("_help", "voices"):
                names += [x for k, e in v.items() if isinstance(e, dict) and e.get("id") == base
                          for x in ([e["transcript"]] if e.get("transcript") else []) + [k]]   # 'transcript': its file name
    except (OSError, ValueError):
        pass
    for n in names + [base]:
        f = os.path.join(TRANS, n + "_words.json")
        if os.path.exists(f):
            return _norm(json.load(open(f)))
    return None


_MODEL = []


def words(path):
    ws = committed(path)
    if ws is not None:
        return ws
    j = os.path.splitext(path)[0] + "_words.json"
    if os.path.exists(j) and os.path.getmtime(j) >= os.path.getmtime(path):   # a re-made VO gets a new transcript
        return _norm(json.load(open(j)))
    if not _MODEL:                                 # loaded once per process (a storyboard transcribes each voiceover)
        from faster_whisper import WhisperModel
        _MODEL.append(WhisperModel("small.en", device="cpu", compute_type="int8"))
    segs, _ = _MODEL[0].transcribe(path, word_timestamps=True, condition_on_previous_text=False)
    ws = [dict(w=w.word.strip(), s=round(w.start, 2), e=round(w.end, 2)) for s in segs for w in s.words if w.word.strip()]
    json.dump(ws, open(j + f".{os.getpid()}", "w"))
    os.replace(j + f".{os.getpid()}", j)          # atomic: parallel renders may share a clip
    return ws


_SAID = {}


def vo_text(d, f):
    """The script of voiceover f: d/tts_said.json ({file: 'voice_id|text'}, written by make_batch plan and projects.py
    expand for every voiceover file, duplicates included); '' when unknown."""
    p = os.path.join(d, "tts_said.json")
    if p not in _SAID:
        try:
            _SAID[p] = json.load(open(p))
        except (OSError, ValueError):
            _SAID[p] = {}
    v = _SAID[p].get(f) or ""
    return v.split("|", 1)[1] if "|" in v else v


NUMBER = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                          "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
NUMBER.update({w: str(10 * i) for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1})


def _canon(t):
    t = t.lower().replace("’", "'").strip(".,!?;:\"'()[]…‒–—-")
    return "%" if t in ("percent", "%") else NUMBER.get(t, t)


def script_words(text, ws):
    """The script's own words (spelling, punctuation: 'Hobo Bag.', not whisper's 'phobo bag') on the word timings of its
    voiceover transcript ws: matched words take their times, words whisper heard differently share the time of what it
    heard (by length), words it missed sit between their neighbours. 'fifty percent' becomes '50%' (the caption the
    client's ads show). Each word gets k='script' (longform applies no whisper fixes to it)."""
    toks = (text or "").split()
    if not toks or not ws:
        return list(ws)
    a, bw = [_canon(x) for x in toks], [_canon(w["w"]) for w in ws]
    tim = [None] * len(toks)

    def spread(i1, i2, s0, e0):
        n = [max(len(a[i]), 1) for i in range(i1, i2)]
        tot, acc = sum(n), s0
        for i, c in zip(range(i1, i2), n):
            d_ = (e0 - s0) * c / tot
            tim[i] = (acc, acc + d_)
            acc += d_
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, bw, autojunk=False).get_opcodes():
        if tag == "equal":
            for q in range(i2 - i1):
                tim[i1 + q] = (ws[j1 + q]["s"], ws[j1 + q]["e"])
        elif tag == "replace":
            spread(i1, i2, ws[j1]["s"], ws[j2 - 1]["e"])
    i = 0
    while i < len(toks):                          # words whisper missed: between the neighbours' times
        if tim[i] is not None:
            i += 1
            continue
        j = i
        while j < len(toks) and tim[j] is None:
            j += 1
        s0 = tim[i - 1][1] if i else ws[0]["s"]
        e0 = tim[j][0] if j < len(toks) else ws[-1]["e"]
        spread(i, j, s0, max(e0, s0 + 0.12 * (j - i)))
        i = j
    out = []
    for t, (s0, e0) in zip(toks, tim):
        if out and _canon(t) == "%" and _canon(out[-1]["w"]).isdigit():
            prev = out[-1]                        # 'fifty percent,' -> '50%,'
            tail = re.sub(r"^[^.,!?;:]*", "", t)
            out[-1] = dict(prev, w=_canon(prev["w"]) + "%" + tail, e=round(e0, 3))
            continue
        out.append(dict(w=t, s=round(s0, 3), e=round(e0, 3), k="script"))
    return out


def sentence_end(ws, i):
    """Word i ends a sentence: final punctuation and PAUSE s before the next word (or it is the last word)."""
    return ws[i]["w"].rstrip("\"')").endswith(FIN) and (i + 1 == len(ws) or ws[i + 1]["s"] - ws[i]["e"] >= PAUSE)


def sentence_start(ws, i):
    return i == 0 or ws[i - 1]["w"].rstrip("\"')").endswith(FIN)


def spoken_in(ws, a, b):
    """Indices of the words heard in [a, b] (a word that only grazes an edge by 20 ms is not)."""
    return [i for i, w in enumerate(ws) if w["e"] > a + 0.02 and w["s"] < b - 0.02]


def cadence(ws, a, b, what="piece", start=True, end=True):
    """Problems of the piece [a, b] of a recording with transcript ws (the client's rule: a cut lands where a sentence
    naturally ends): it starts at a sentence start, ends at a sentence end (sentence_end) and never inside a word.
    [] = fine. start/end False: that edge joins the recording's own neighbour (not checked)."""
    got, probs = spoken_in(ws, a, b), []
    if not got:
        return probs
    i0, i1 = got[0], got[-1]
    if start:
        if ws[i0]["s"] < a - EDGE:
            probs.append(f"{what} {a:.2f}-{b:.2f} starts inside the word {ws[i0]['w']!r} ({ws[i0]['s']:.2f}-{ws[i0]['e']:.2f} s)")
        elif not sentence_start(ws, i0):
            probs.append(f"{what} {a:.2f}-{b:.2f} starts mid-sentence at {ws[i0]['w']!r} (after {ws[i0 - 1]['w']!r})")
    if end:
        if ws[i1]["e"] > b + 0.05:
            probs.append(f"{what} {a:.2f}-{b:.2f} ends inside the word {ws[i1]['w']!r} ({ws[i1]['s']:.2f}-{ws[i1]['e']:.2f} s)")
        elif not sentence_end(ws, i1):
            nxt = ws[i1 + 1]
            probs.append(f"{what} {a:.2f}-{b:.2f} ends at {ws[i1]['w']!r} but the speaker goes on: {nxt['w']!r} "
                         f"{max(nxt['s'] - ws[i1]['e'], 0):.2f} s later (a sentence end needs final punctuation and {PAUSE} s)")
    return probs


def claim_ranges(r):
    """RAW ranges cut for compliance (spec 'claim_cuts': [{"range": [a, b], "said": "..."}] or [a, b]): a health claim
    inside the client's proven body (Julian 2026-10-09), cut on word boundaries, usually the end of a sentence ('Reason
    four, an adjustable strap[ that prevents shoulder pain.]'): the piece before it may end without a full stop."""
    return [list(c["range"] if isinstance(c, dict) else c) for c in r.get("claim_cuts") or []]


def body_pieces(r, R, with_reviews=None):
    """RAW-time pieces of a remix body in play order: [a, b] ranges between the cuts, split at insert_at where the
    review section goes ("REVIEWS" marks it). with_reviews None: as the spec says (insert_at and reviews both set)."""
    start, end = r.get("start") or 0.0, r.get("end") or R
    ins = r.get("insert_at")
    has_rev = bool(ins is not None and r.get("reviews")) if with_reviews is None else bool(with_reviews and ins is not None)
    pieces, t = [], start
    for a, b in sorted(list(r.get("cut") or []) + claim_ranges(r)) + [[end, end]]:
        if a > t:
            pieces.append([t, min(a, end)])
        t = max(t, b)
    body, placed = [], not has_rev
    for a, b in pieces:
        if not placed and ins <= a:          # insert point on a cut boundary: reviews go before the next piece
            body.append("REVIEWS")
            placed = True
        if not placed and a < ins < b:
            body += [[a, ins], "REVIEWS", [ins, b]]
            placed = True
        else:
            body.append([a, b])
    if not placed:
        body.append("REVIEWS")
    return body


def remix_cadence(r, ws, R, with_reviews=None):
    """Cadence problems of a remix spec (cold open, every body piece, the insert point) against the RAW transcript."""
    probs = []
    co = r.get("cold_open")
    if co:
        probs += cadence(ws, co[0], co[1], "cold open")
    body = body_pieces(r, R, with_reviews)
    edits = [a for a, _ in claim_ranges(r)]
    for k, p in enumerate(body):          # (the RAW's first and last words pass by themselves)
        if p != "REVIEWS":
            near = "REVIEWS" in body[max(k - 1, 0):k] + body[k + 1:k + 2]
            cut_claim = any(abs(p[1] - a) < 0.02 for a in edits)   # its sentence ends at the claim cut on purpose
            probs += [x for x in cadence(ws, p[0], p[1], "RAW piece next to the review section" if near else "RAW piece")
                      if not (cut_claim and " but the speaker goes on: " in x)]
    return probs


def still_frame(d, src, t):
    """A JPG of src's frame at t, cached next to the spec (relative name): a beat held under silence."""
    import hashlib
    name = f"_hold_{hashlib.md5(f'{src}|{t:.2f}'.encode()).hexdigest()[:10]}.jpg"
    f = os.path.join(d, name)
    if not os.path.exists(f):
        part = f"{f}.{os.getpid()}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", loc(d, src), "-frames:v", "1", "-q:v", "2",
                        "-y", part], check=True)
        os.replace(part, f)
    return name


def clean(w):
    return re.sub(r"[^\w%']", "", w.lower())


def hit(w, word):
    """Whisper token w is the card word: same start, or a close spelling ('jenny'/'jennie') with the same first letter
    and length (so 'every' never stands in for 'beverly')."""
    w = clean(w)
    return w.startswith(word) or (len(word) >= 5 and w[:1] == word[:1] and abs(len(w) - len(word)) <= 2
                                  and difflib.SequenceMatcher(None, w, word).ratio() >= 0.75)


def card_starts(vw, cards, text, L):
    """Start time of each card in the review VO: its word, searched in order after the previous card's word.
    A word whisper missed is placed by its position in the script text (or 0.2 s for the first card)."""
    starts, k, tp = [], 0, 0
    toks = [clean(t) for t in (text or "").split()]
    for c in cards:
        pos = next((i for i in range(tp, len(toks)) if hit(toks[i], c["word"])), None)
        tp = tp if pos is None else pos + 1
        j = next((i for i in range(k, len(vw)) if hit(vw[i]["w"], c["word"])), None)
        if j is not None:
            starts.append(vw[j]["s"])
            k = j + 1
            continue
        print(f"review card {c['n']} placed by its script position (whisper did not hear {c['word']!r})", file=sys.stderr)
        est = L * pos / len(toks) if pos is not None else (starts[-1] + 1.5 if starts else 0.2)
        est = max(est, starts[-1] + 0.8 if starts else 0.2)
        starts.append(round(min(est, max(L - 1.0, 0.2)), 2))
    return starts


def build(r, d, info=None):
    """-> segs, audio, overlays, total, breaks. info (a dict) also gets 'words': what is said, in ad seconds (the RAW's
    committed transcript through the edit, the review VO's script on its word timings), for longform's captions."""
    raw = r["raw"]
    R = dur(loc(d, raw))
    ws = words(loc(d, raw))
    ins = r.get("insert_at")
    body = body_pieces(r, R)                # RAW pieces between the cuts (+ "REVIEWS" where the review section goes)
    for p in remix_cadence(r, ws, R):
        print("cadence:", p, file=sys.stderr)

    segs, audio, ov, t = [], [], [], 0.0
    raw_to_out = []                         # (raw_a, raw_b, out_a) for mapping RAW times to output times
    gap = [None, None]                      # silence after the last word so far (s); RAW time the picture stopped at

    def heard(a, b):
        """(lead, tail): silence before the first and after the last word of RAW piece [a, b] (None: no words)."""
        got = spoken_in(ws, a, b)
        return (max(ws[got[0]]["s"] - a, 0.0), max(b - ws[got[-1]]["e"], 0.0)) if got else (None, None)

    def room(need, at):
        """The RAW's own sound with nobody speaking (its music bed / room tone) for a held beat: the nearest gap between
        words at least need + 0.12 s long, so the bed never drops out to digital silence. None found: silence."""
        gaps = [(ws[i]["e"] + 0.06, ws[i + 1]["s"] - 0.06) for i in range(len(ws) - 1) if ws[i + 1]["s"] - ws[i]["e"] >= need + 0.12]
        if ws and R - ws[-1]["e"] >= need + 0.3:
            gaps.append((ws[-1]["e"] + 0.15, R - 0.05))
        if not gaps:
            return ("silence", need)
        g0, _ = min(gaps, key=lambda g: abs(g[0] - at))
        return ("slice", raw, round(g0, 3), round(g0 + need, 3))

    def beat(need, at):
        """need s of silence, so a line finishes before the next starts (PAUSE) or before the end (TAIL). Picture: the
        RAW's frame at `at` held (its own footage past `at` could flash the next shot or, burned in, the next caption)."""
        nonlocal t
        need = round(max(need, 0.12), 2)
        segs.append(dict(src=still_frame(d, raw, max(min(at, R) - 0.05, 0)), start=0, dur=need))
        audio.append(room(need, at))
        t += need
        gap[0] = (gap[0] or 0) + need

    edit_ends = [e_ for _, e_ in claim_ranges(r)]

    def raw_seg(a, b, **ex):
        nonlocal t
        lead, tail = heard(a, b)
        need = PAUSE_EDIT if any(abs(a - e_) < 0.02 for e_ in edit_ends) else PAUSE   # a shortened sentence: a full stop
        if gap[0] is not None and lead is not None and gap[0] + lead < need:
            beat(need - gap[0] - lead, gap[1] if gap[1] is not None else a)
        segs.append(dict(src=raw, start=round(a, 3), dur=round(b - a, 3), **ex))
        audio.append(("slice", raw, a, b))
        raw_to_out.append((a, b, t))
        t += b - a
        gap[:] = [tail if tail is not None else (gap[0] or 0) + b - a, b]

    co = r.get("cold_open")
    hook = None
    if co:
        raw_seg(co[0], co[1])
        hook = dict(type="label", text=r.get("hook_label", "WAIT FOR IT"), at=0.1, dur=min(1.6, co[1] - co[0]), y=300)
    elif r.get("hook_label"):
        hook = dict(type="label", text=r["hook_label"], at=0.1, dur=1.6, y=300)
    review_at = None
    for p in body:
        if p == "REVIEWS":
            rv = r["reviews"]
            if gap[0] is not None and gap[0] < PAUSE - 0.1:      # (the narration's own mp3 lead-in gives ~0.1 s)
                beat(PAUSE - 0.1 - gap[0], gap[1] if gap[1] is not None else 0.0)
            L = dur(loc(d, rv["vo"])) + 0.4
            review_at = t
            br = list(rv["broll"])
            spare = [x for x in rv.get("spare") or [] if x not in br]
            while spare and L / len(br) > MAX_SHOT:             # no review shot longer than MAX_SHOT
                br.append(spare.pop(0))
            for src, st, *_ in br:
                st, sp = fit(d, src, st, L / len(br))
                segs.append(dict(src=src, start=st, dur=round(L / len(br), 3), mute=True, **({"speed": sp} if sp != 1.0 else {})))
            audio.append(("file", rv["vo"], L))
            t += L
            gap[:] = [0.4, None]
        else:
            raw_seg(p[0], p[1])
    if gap[0] is not None and gap[0] < TAIL + 0.15:   # the last word finishes before the video (and the end card) ends
        beat(TAIL + 0.15 - gap[0], gap[1] if gap[1] is not None else R)   # (+0.15: a word decays past whisper's end)

    def out_time(rt):
        for a, b, oa in raw_to_out[1 if co else 0:]:
            if a <= rt <= b:
                return oa + (rt - a)
        return None

    # review cards synced to the narration words
    if review_at is not None:
        rv = r["reviews"]
        L = dur(loc(d, rv["vo"]))
        starts = card_starts(words(loc(d, rv["vo"])), rv["cards"], rv.get("text"), L)
        for k, c in enumerate(rv["cards"]):
            a = review_at + 0.1 + starts[k]
            b = review_at + 0.1 + (starts[k + 1] if k + 1 < len(starts) else L + 0.2)
            ov.append(dict(type="review", n=c["n"], at=round(a, 2), dur=round(b - a, 2), y=330))
    # number labels and offer card from the RAW transcript
    for lb in r.get("labels") or []:
        w0 = next((x for x in ws if x["s"] >= lb.get("after", 0) and x["w"].lower().strip(".,") == lb["word"]), None)
        if w0 and out_time(w0["s"]) is not None:
            ov.append(dict(type="label", text=lb["text"], at=round(out_time(w0["s"]), 2), dur=1.4, y=300))
        else:
            print(f"overlay anchor not found: label {lb['text']!r} (word {lb['word']!r})", file=sys.stderr)
    title, sub = r.get("offer_title", "50% OFF"), r.get("offer_sub", "+ FREE MATCHING WALLET")
    review_end = review_at + dur(loc(d, r["reviews"]["vo"])) + 0.4 if review_at is not None else 0
    if title and not r.get("offer_word"):    # the RAW never says the offer: the card goes with its call to action,
        a = max(review_end, t - 2.6 - 3.4)   # just before the end card, so the theme and the offer still show
        ov.append(dict(type="offer", title=title, sub=sub, at=round(a, 2), dur=3.2, y=420) if sub else
                  dict(type="label", text=title, at=round(a, 2), dur=3.2, y=470))
        print(f"offer card placed before the end card at {a:.1f}s (the RAW has no offer word)", file=sys.stderr)
    elif r.get("offer_word") and title:
        after = r.get("offer_after")
        after = (ins or 0) - 1 if after is None else after
        cands = [x for x in ws if r["offer_word"] in x["w"] and out_time(x["s"]) is not None and x["s"] >= after]
        if cands:
            a = out_time(cands[0]["s"])
            ov.append(dict(type="offer", title=title, sub=sub, at=round(a - 0.2, 2), dur=3.2, y=420) if sub else
                      dict(type="label", text=title, at=round(a - 0.2, 2), dur=3.2, y=470))   # no sub: no empty pill
        else:
            print(f"overlay anchor not found: offer word {r['offer_word']!r}", file=sys.stderr)
    if hook:                       # label box ends at y~412, the offer card starts at 420: both can show at once
        ov.insert(0, hook)
    ov.append(dict(type="end", title=r.get("end_title", "The Luxury Hobo Bag"), sub=r.get("end_sub", "Tap the link below"),
                   at=round(t - 2.6, 2), dur=2.6, opaque=bool(r.get("burned_captions"))))   # covers the RAW's own captions
    breaks = sorted({round(x[2], 2) for x in raw_to_out} | ({round(review_at, 2), round(review_end, 2)} if review_at is not None
                                                              else set()))
    if info is not None:
        kn = []
        for a, b, oa in raw_to_out:          # the RAW's words through the edit (cold open, body pieces)
            for i in spoken_in(ws, a, b):
                w = ws[i]
                kn.append(dict(w=w["w"], s=round(oa + max(w["s"], a) - a, 3), e=round(oa + min(w["e"], b) - a, 3)))
        if review_at is not None:
            rv = r["reviews"]
            vw = words(loc(d, rv["vo"]))
            kn += [dict(w, s=round(review_at + w["s"], 3), e=round(review_at + w["e"], 3))
                   for w in (script_words(rv["text"], vw) if rv.get("text") else vw)]
        info["words"] = sorted(kn, key=lambda w: w["s"])
    return segs, audio, ov, t, breaks


CAPTION_KEYS = ("caption_y", "caption_y_force", "caption_words", "caption_top", "caption_fix")


def caption_opts(spec):
    """Caption settings a spec sets on purpose; everything else is longform.py's own default (low in the safe zone, up
    to 8 words on 2 lines, clear of the overlays). caption_y applies only with caption_y_force; an old spec's max_words
    (always 4) is ignored: a spec that wants another phrase size sets caption_words. caption_top: windows in ad seconds."""
    return {k: spec[k] for k in CAPTION_KEYS if k in spec}


def mix_audio(audio, d, out, music=None):
    """The pieces (slices of recordings, voiceover files, silences) in order, loudness-normalised (-16 LUFS); music
    (music.resolve(): path, gain_db) adds a bed under it: looped to length, 1 s fade in, 1.8 s fade out, ducked a further
    ~6-8 dB whenever someone speaks (sidechain on the voice track)."""
    inputs, fc, k = [], [], 0
    for p in audio:
        if p[0] == "slice":
            inputs += ["-i", loc(d, p[1])]
            L = p[3] - p[2]
            fc.append(f"[{k}:a]atrim={p[2]}:{p[3]},asetpts=N/SR/TB,aresample=48000,aformat=channel_layouts=stereo,"
                      f"afade=t=in:d=0.02,afade=t=out:st={max(L - 0.03, 0):.3f}:d=0.03,apad=whole_dur={L:.3f},atrim=0:{L:.3f}[p{k}]")
        elif p[0] == "silence":
            inputs += ["-f", "lavfi", "-t", f"{p[1]:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            fc.append(f"[{k}:a]atrim=0:{p[1]:.3f}[p{k}]")
        else:
            inputs += ["-i", loc(d, p[1])]
            fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={p[2]:.3f},atrim=0:{p[2]:.3f}[p{k}]")
        k += 1
    if not music:
        fc.append("".join(f"[p{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1,loudnorm=I=-16[o]")
    else:
        T = sum(p[3] - p[2] if p[0] == "slice" else p[1] if p[0] == "silence" else p[2] for p in audio)
        inputs += ["-stream_loop", "-1", "-i", music["path"]]
        g = music.get("gain_db", -15.0)
        fc.append("".join(f"[p{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1,loudnorm=I=-16,aresample=48000,asplit=2[v1][v2]")
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{T:.3f},asetpts=N/SR/TB,"
                  f"loudnorm=I=-16,aresample=48000,volume={g}dB,afade=t=in:d=1.0,afade=t=out:st={max(T - 1.8, 0):.3f}:d=1.8[m]")
        fc.append("[m][v2]sidechaincompress=threshold=0.02:ratio=4:attack=20:release=400:makeup=1[md]")
        fc.append("[v1][md]amix=inputs=2:duration=first:normalize=0[o]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[o]",
                    "-y", out], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("remix")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = json.load(open(a.remix))
    d = os.path.dirname(os.path.abspath(a.remix))
    info = {}
    segs, audio, ov, total, breaks = build(r, d, info)
    name = os.path.splitext(os.path.basename(a.remix))[0]
    wav = f"_{name}_audio.wav"
    import music
    m = r.get("music")
    if isinstance(m, dict) and m.get("auto"):  # make_batch's winners: the RAW's own sound (most have a bed), a bed only
        m = None if music.has_bed(loc(d, r["raw"]), words(loc(d, r["raw"]))) else dict(m, auto=False)   # if it is dry
    bed = music.resolve(m, d)                 # none by default: the proven RAW keeps its own sound
    mix_audio(audio, d, os.path.join(d, wav), bed)
    for s in segs:
        s["mute"] = True
    edl = dict(audio="mute", vo=wav, vo_start=0.0, bed_gain=0.0, segments=segs, overlays=ov, keywords=r.get("keywords", []),
               breaks=breaks, transcript=info.get("words") or [], **caption_opts(r))
    if r.get("burned_captions"):
        edl["no_captions"] = [[0, 9999]]
    lj = os.path.join(d, f"_{name}_longform.json")
    json.dump(edl, open(lj, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "longform.py"), lj, "--out", a.out], check=True)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2))))


if __name__ == "__main__":
    main()

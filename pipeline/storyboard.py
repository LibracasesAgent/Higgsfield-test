#!/usr/bin/env python3
"""Block-based 30-90 s ad (for longform.py): narration blocks over B-roll plus real clips with their own sound.

  python3 pipeline/storyboard.py board.json --out ad.mp4

board.json (paths relative to the JSON):
{
  "blocks": [
    {"vo": "n_vin1.mp3", "broll": [["vin_clasp_brown.mp4", 0.0], ["vin_details_brown.mp4", 3.5, 1.5]]},
                                   # [src, start, weight?]: the VO length is split over the clips by weight
    {"vo": "n_feat1.mp3", "broll": [...], "hold": 1.6},   # "hold": s of silent picture after the line (a middle block only;
                                   # make_batch pads a thin product's ad with it, with enough shots for the longer block)
    {"clip": "vin_becky_testimony.mp4", "range": [5.8, 14.4]},       # real clip with its own audio
    {"clip": "k_h2_brown.mp4", "range": [0, 5], "mute": true},        # silent visual (adds time, no sound)
  ],
  "pad": 0.25,                                       # silence after each VO block
  "overlays": [{"type": "tag", "text": "LOCKABLE ZIPPERS", "block": 0, "word": "lockable", "dur": 2.2},
               {"type": "review", "n": 11, "block": 2, "word": "sarah", "until_block_end": true},
               {"type": "label", "text": "REAL CUSTOMER", "block": 1, "at": 0.2, "dur": 2.0}],
  "offer": {"block": 4, "word": "50", "title": "50% OFF", "sub": "+ FREE MATCHING WALLET"},
                                                     # offer card at that word ("fifty" also matches); "" sub: title only
  "end_title": "The Vintage Bag", "end_sub": "Tap the link below", "keywords": [...], "no_captions_blocks": [3],
  "end_photo": "site/vintage_bag_08.jpg", "end_offer": "BLACK FRIDAY 50% OFF",   # the closing studio card's packshot and offer pill (both optional)
  "caption_top_blocks": [2],                         # captions in the upper area during these blocks (product detail low)
  "spare_broll": [[src, start], ...],                # unused shots: a VO shot that would run > 4 s is split onto them
  "music": {"seed": 3},                              # music bed (music.py: a client track, else a generated bed); false: none
}
A VO block may carry its script as "text" (else tts_said.json next to the board): captions show the script's words on the
voiceover's word timings, a clip's words from its committed transcript (no transcription of the final mix).
One voice per video: every "vo" block is the brand voice; real people speak only in their own "clip" blocks, each
introduced by the narrator in the block before ("Here's Becky with her new Vintage Bag.").
B-roll that would run past the end of its clip starts earlier (or plays slower), so picture and sound stay in sync.
Pacing: no B-roll shot runs longer than remix.MAX_SHOT (4 s): a longer one is split, its later parts on the block's own
"spare" shots, then the board's spare_broll, never a shot the video shows already (none left: it stays long). A clip block
longer than that (a customer talking) changes framing about every SHOT_TARGET s (wide / closer on the bag / closer on
her, the block's "frames" to override), cut on her pauses, its sound running on; one clip twice in a row gets a closer
framing the second time, so it reads as another shot.
Cadence: the hook block gets at least HOOK_PAD s after its line (the hook finishes before the body starts), the last
block at least END_PAD s (the last sentence finishes, remix.TAIL, before the end card ends the video), a narrator line
right after a customer's clip CLIP_PAD s after her last word (she finishes, a breath, then the next voice); a clip block
whose range starts or ends mid-sentence prints a 'cadence:' line (make_batch render counts it as a QA flag).

"mode": "ugc" (the default storyboard format; no mode = the classic format above, unchanged): a voiceover that talks nearly
all the time over a new shot about every 2 s, mastered to one steady loudness. Blocks and overlays as above, plus
  "number": 1                    # chapter number: the block's first caption starts "1. ..." (longform: a word's "pre")
  "voice_speed": 1.12, "pad": 0.08, "hook_pad": 0.2     # the voice prep and the pads between the takes (below)
(a) every voiceover file is voice-prepared (voice_prep: silence trimmed at both ends and the long pauses inside shortened,
    sped up voice_speed x with the pitch kept, levelled to one loudness, cached as _vp_<hash>.wav next to the board); the
    blocks follow each other `pad` s after the voice (the hook hook_pad, the last block END_PAD): one speaker talking on;
(b) each block's B-roll picks go to its PHRASES, the picture cutting where a phrase starts (the voice's word timings):
    phrases = sentences, and the clauses (after a comma, or at an 'and' / 'but' / 'so') of a sentence of more than
    CLAUSE_WORDS words; shots run SHOT_MIN-SHOT_LONG s (short phrases merge, a long one is split on the block's spare
    shots, then the board's, else the same footage again, closer); a block with more picks than shots drops the last (they
    become spares for the later blocks); the same source moment never shows twice within SAME_S s (another spare, another
    moment of the clip, a closer framing); the picture is cut on the 30 fps grid, so it stays with the voice. In ugc a
    block's own "pad" wins (leave it off the hook: hook_pad);
(c) a review card is on screen at most REVIEW_MAX s (no "until_block_end"); (d) the number prefix above;
(e) the sound is mastered to -14 LUFS, LRA <= 4 LU, true peak -1.5 (remix.master_ugc; the music bed 6 dB lower than
    the classic mix); (f) no real-customer "clip" blocks (the renderer still plays them).
The hook is planned after the body: its versions never change the body's shots.
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from remix import (MAX_SHOT, STILL, TAIL, cadence, caption_opts, clip_dur, dur, fit, loc, mix_audio, script_words,  # noqa: E402
                   vo_text, words)


TENS = "_ ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_word(w):
    """First spoken word of a number: '50' -> 'fifty', '65' -> 'sixty', '15' -> 'fifteen'."""
    if not w.isdigit() or not 10 <= int(w) < 100:
        return None
    return "fifteen" if w == "15" else TENS[int(w) // 10]


def norm(w):
    return w.lower().strip(".,:;!?\"'")


HOOK_PAD = 0.35    # silence after the hook line before the body starts (>= remix.PAUSE with the mp3's own tail)
END_PAD = TAIL + 0.2   # silence after the last line: it finishes before the video ends
CLIP_PAD = 0.5     # silence between a real customer's last word and the narrator's next line (her sentence lands)
SHOT_TARGET = 3.2  # a long clip block (a customer talking) changes framing about this often (Julian: every 3-5 s)
FRAMES = [{}, {"zoom": [1.55, 1.6], "focus": [0.5, 0.74]}, {}, {"zoom": [1.22, 1.26], "focus": [0.5, 0.36]}]
#                 wide -> closer on her hands and the bag -> wide -> closer on her (9:16 talking clip: face above the bag)


# ---- the ugc format (board "mode": "ugc") ----
UGC_PAD, UGC_HOOK_PAD = 0.08, 0.2      # silence after a voice take (the hook's): the takes join like one speaker talking on
VOICE_SPEED, VOICE_MAX = 1.12, 1.25    # the narrator is sped up this much (pitch kept; faster than VOICE_MAX sounds hurried)
VOICE_LUFS = -20.0                     # every voice take is levelled to this before the mix (no loudness swing between takes)
TRIM_DB, KEEP_HEAD, KEEP_TAIL = -42, 0.035, 0.04   # silence under TRIM_DB at both ends is cut, this much of it kept
GAP_CAP = 0.16                         # a pause inside a take is cut to this (s, before the speed-up; 0.26 left the speech at 80-82% of
#                                        the video, the clients' ads have 88-91%): sentence gaps in their ads are 0.15-0.4 s
VP_VERSION = 3                         # bump when voice_prep's chain changes: processed voices are made again
SHOT_MIN, SHOT_LONG, SHOT_IDEAL = 1.3, 3.2, 1.9    # ugc shot lengths (s): merged below SHOT_MIN, split above SHOT_LONG
CLAUSE_WORDS = 9                       # a sentence longer than this many words is split at a comma into two phrases
CONJ = {"and", "but", "so", "because", "while", "then"}   # a clause may also start at one of these (no comma needed)
CUT_LEAD = 0.05                        # the picture cuts this long before the phrase's first word (the word lands on the shot)
SAME_S = 10.0                          # the same source moment is not shown twice within this many seconds
REVIEW_MAX = 3.0                       # longest time a review card stays on screen
SHORT_CLIP, STILL_GAP = 45.0, 4.0      # a clip under SHORT_CLIP s is one scene: two shots of it in one framing look like one long
#                                        shot (even from different moments); a still's closer framing is another shot after STILL_GAP s
MOMENTS = (2.5, -2.5, 4.0, -4.0, 5.5, -5.5)       # other moments of a clip (s from the picked start) when a pick would repeat
CLOSER = ({"zoom": [1.3, 1.36], "focus": [0.5, 0.55]}, {"zoom": [1.6, 1.66], "focus": [0.5, 0.42]})   # closer framings
FIN = (".", "?", "!")
TALK = "TALK"                          # a pick that is the presenter on camera (presenter.py: her take is the block's picture and voice)
TALK_HEAD, TALK_TAIL = 0.10, 0.22      # a take is cut this long before her first word and after her last (s)
TALK_FRAME = {"zoom": [1.12, 1.18], "focus": [0.5, 0.42]}   # every second shot of her is this closer framing (a jump cut, as creators edit)


def voice_prep(d, name, speed=VOICE_SPEED):
    """ugc voice file: `name` (a file next to the board) with the silence at both ends cut (KEEP_HEAD / KEEP_TAIL s kept)
    and every pause inside longer than GAP_CAP s shortened to it, sped up `speed` x (atempo: pitch kept, at most
    VOICE_MAX) and levelled to VOICE_LUFS. -> the processed file's name '_vp_<hash>.wav' (the hash covers the voice's
    bytes and the speed, so a re-made take or another speed is processed again), written next to the board once (atomic:
    the 4 hook versions of a project share it); remix.words() transcribes it under that name."""
    src = loc(d, name)
    speed = min(max(float(speed), 0.8), VOICE_MAX)
    h = hashlib.md5(open(src, "rb").read() + f"|{speed:.3f}|{VP_VERSION}".encode()).hexdigest()[:12]
    out = f"_vp_{h}.wav"
    p = os.path.join(d, out)
    if os.path.exists(p):
        return out
    cut = f"silenceremove=start_periods=1:start_threshold={TRIM_DB}dB:start_silence={KEEP_HEAD}"
    chain = (f"aresample=48000,aformat=channel_layouts=mono,silenceremove=stop_periods=-1:stop_duration={GAP_CAP}:"
             f"stop_threshold={TRIM_DB}dB:stop_silence=0,{cut},areverse,{cut.replace(str(KEEP_HEAD), str(KEEP_TAIL))},"
             f"areverse,atempo={speed:.4f}")
    t1, t2 = f"{p}.{os.getpid()}.a.wav", f"{p}.{os.getpid()}.b.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src, "-af", chain, "-y", t1], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", t1, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    gain = min(max(VOICE_LUFS - float(m[-1]), -12.0), 12.0) if m else 0.0
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", t1, "-af",
                    f"volume={gain:.2f}dB,alimiter=limit=0.89:level=disabled,afade=t=in:d=0.006,"
                    f"afade=t=out:st={max(dur(t1) - 0.02, 0):.3f}:d=0.02", "-ar", "48000", "-y", t2], check=True)
    os.remove(t1)
    os.replace(t2, p)
    return out


def ugc_voices(b, d):
    """The board with every voiceover file voice-prepared (voice_prep) and its script pinned as the block's 'text'
    (tts_said.json is keyed by the original file names). Everything after this uses the processed files."""
    sp, blocks = b.get("voice_speed", VOICE_SPEED), []
    for blk in b["blocks"]:
        if "vo" in blk and "vo_range" not in blk:
            txt = blk.get("text") or vo_text(d, blk["vo"])
            blk = dict(blk, vo=voice_prep(d, blk["vo"], sp), **({"text": txt} if txt else {}))
        blocks.append(blk)
    return dict(b, blocks=blocks)


def clause_start(s, i):
    """Word i of s opens a clause: it follows a comma / semicolon / colon / sentence end, or is a conjunction (CONJ)."""
    return s[i - 1]["w"].rstrip("\"')")[-1:] in ",;:.?!" or s[i]["w"].lower().strip(",.;:") in CONJ


def clauses(s, n=CLAUSE_WORDS):
    """The words of one sentence as phrases: whole when it has at most n words, else split before the clause start
    (clause_start) nearest its middle (both parts at least 3 words), each part again while it is longer than n."""
    if len(s) <= n:
        return [s]
    mid = (s[0]["s"] + s[-1]["e"]) / 2
    cand = [i for i in range(3, len(s) - 2) if clause_start(s, i)]
    if not cand:
        return [s]
    i = min(cand, key=lambda i: abs(s[i]["s"] - mid))
    return clauses(s[:i], n) + clauses(s[i:], n)


def phrase_cuts(ws, lead=0.0, n=CLAUSE_WORDS):
    """Block seconds where a phrase starts, the first 0: each sentence (ends with . ? !) and each clause (clauses) after
    it starts CUT_LEAD s before its first word; ws = the block's words on the voice file's seconds, the voice starting
    `lead` s into the block."""
    sents, cur = [], []
    for w in ws:
        cur.append(w)
        if w["w"].rstrip("\"')").endswith(FIN):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    cuts = [0.0]
    for p in [x for s in sents for x in clauses(s, n)][1:]:
        c = round(lead + p[0]["s"] - CUT_LEAD, 3)
        if c > cuts[-1] + 0.05:
            cuts.append(c)
    return cuts


def seg_cost(n):
    """Cost of one shot of n s made of whole phrases (shot_groups): near SHOT_IDEAL is cheap, under SHOT_MIN dear, over
    SHOT_LONG it must be split mid-phrase (each split costs)."""
    if n < SHOT_MIN:
        return 6 + (SHOT_MIN - n) * 10
    if n <= SHOT_LONG:
        return 0.4 * abs(n - SHOT_IDEAL)
    k = math.ceil(n / SHOT_LONG)
    return 1.2 * (k - 1) + 0.4 * abs(n / k - SHOT_IDEAL)


def shot_groups(cuts, L):
    """The cheapest grouping of the phrases (their start seconds `cuts`, the block ending at L) into shots: [(a, b)]
    where a and b are phrase starts (b = L for the last): short phrases merge, long ones are left for ugc_pieces."""
    pts = list(cuts) + [L]
    best, back = [0.0] + [float("inf")] * (len(pts) - 1), [0] * len(pts)
    for j in range(1, len(pts)):
        for i in range(j):
            c = best[i] + seg_cost(pts[j] - pts[i])
            if c < best[j]:
                best[j], back[j] = c, i
    out, j = [], len(pts) - 1
    while j > 0:
        out.append((pts[back[j]], pts[j]))
        j = back[j]
    return out[::-1]


def ugc_pieces(a, b, ws, lead=0.0):
    """The cut seconds of one shot group [a, b]: [a, b] itself, or when it is longer than SHOT_LONG equal parts, each cut
    moved to a word start (CUT_LEAD s before it) within 0.5 s of the even split, parts staying over SHOT_MIN; a word that
    opens a clause or sentence (clause_start) wins over one 0.25 s nearer."""
    k = math.ceil((b - a) / SHOT_LONG - 1e-9)
    pts = [a]
    for i in range(1, k):
        x = a + (b - a) * i / k
        near = [(abs(c - x) - (0.25 if j and clause_start(ws, j) else 0), c) for j, w in enumerate(ws)
                for c in [lead + w["s"] - CUT_LEAD] if abs(c - x) <= 0.5 and pts[-1] + SHOT_MIN <= c <= b - SHOT_MIN]
        pts.append(round(min(near)[1] if near else x, 3))
    return pts + [b]


def frame_of(s):
    """Framing of a shot dict: None as shot (zoom under 1.15), else (zoom, focus y): two shots of one moment in another
    framing are two pictures."""
    z = (s.get("zoom") or [1.0])[0]
    return None if z < 1.15 else (round(z, 1), round(float((s.get("focus") or [0.5, 0.5])[1]), 1))


class Shots:
    """The shots of a ugc video as they are planned (body blocks in order, the hook last): every shot goes in the log
    with its seconds; a pick that shows the same source moment (same file, start within 1.5 s, same framing) as a shot
    less than SAME_S s away, before or after it, is replaced: by a spare (the block's own, then the board's), another
    moment of its clip, a closer framing. A slot without a pick takes a spare, else the previous shot again, closer."""

    def __init__(self, d):
        self.d, self.log, self.last = d, [], None

    def mk(self, src, st, ex, L):
        """The shot dict of the pick (src, st, extra) for L s: as broll_segs makes it (the start moved back or a slower
        speed when the clip runs out; a still gets a slow punch-in)."""
        ex = {k: v for k, v in (ex or {}).items() if k != "say"}
        if not str(src).lower().endswith(STILL):
            st, sp = fit(self.d, src, st, L)
            if sp != 1.0:
                ex["speed"] = sp
        elif not ex:
            ex = {"zoom": [1.0, 1.06]}
        return dict(src=src, start=st, dur=round(L, 3), mute=True, **ex)

    def clash(self, s, t0, t1):
        f, q = frame_of(s), str(s["src"])
        still = q.lower().endswith(STILL)
        short = not still and 0 < (clip_dur(self.d, q) or 0) < SHORT_CLIP
        for q2, st, fr, a, e in self.log:
            gap = max(a - t1, t0 - e, 0)
            if q2 != q or gap >= SAME_S:
                continue
            if f == fr and (still or short or abs(float(s["start"]) - st) <= 1.5) or (still and gap < STILL_GAP):
                return True
        return False

    def add(self, s, t0):
        self.log.append((str(s["src"]), float(s["start"]), frame_of(s), t0, t0 + float(s["dur"])))
        self.last = s
        return s

    def place(self, t0, L, pick, pools, prev=None):
        """One shot of L s at ad second t0 (see the class). pick: [src, start, weight?, extra?] or None; pools: the lists
        spares are taken (removed) from, in order; prev: the shot before, for a slot without a pick."""
        t1 = t0 + L
        if pick is not None:
            src, st, *r = pick
            ex = r[1] if len(r) > 1 else {}
            s = self.mk(src, st, ex, L)
            if not self.clash(s, t0, t1):
                return self.add(s, t0)
        for pool in pools:
            for x in pool:
                s = self.mk(x[0], x[1], x[3] if len(x) > 3 else {}, L)
                if not self.clash(s, t0, t1):
                    pool.remove(x)
                    return self.add(s, t0)
        if pick is not None:
            D = clip_dur(self.d, src)
            for off in MOMENTS if D else ():
                if 0 <= st + off <= D - L - 0.1:
                    s = self.mk(src, round(st + off, 2), ex, L)
                    if not self.clash(s, t0, t1):
                        return self.add(s, t0)
            for cl in CLOSER:
                s = self.mk(src, st, dict(ex, **cl), L)
                if not self.clash(s, t0, t1):
                    return self.add(s, t0)
            print(f"repeat: {src} {st} at {t0:.1f}s (nothing else to show)", file=sys.stderr)
            last = self.last if self.last and str(self.last["src"]) == str(src) else None
            alt = [self.mk(src, st, e, L) for e in [ex] + [dict(ex, **cl) for cl in CLOSER]]
            return self.add(next((x for x in alt if not last or frame_of(x) != frame_of(last)), alt[0]), t0)
        if prev is None:
            raise ValueError(f"no shot for the block at {t0:.1f}s: it has no B-roll and no spare shot")
        base = {k: v for k, v in prev.items() if k not in ("src", "start", "dur", "mute", "speed", "zoom", "focus")}
        still = str(prev["src"]).lower().endswith(STILL)
        for cl in CLOSER:                       # the same footage on, in a closer framing than the shot before
            s = self.mk(prev["src"], 0 if still else round(prev["start"] + prev["dur"], 2), dict(base, **cl), L)
            if frame_of(s) != frame_of(prev) and not self.clash(s, t0, t1):
                return self.add(s, t0)
        print(f"repeat: {prev['src']} at {t0:.1f}s (no spare shot left)", file=sys.stderr)
        return self.add(self.mk(prev["src"], prev["start"], dict(base, **CLOSER[-1]), L), t0)


def talk_seg(talk, x, y, n):
    """The presenter on camera from block second x to y (the n-th such shot of the block): her take from where it is in sync."""
    s = dict(src=talk["src"], start=round(talk["a"] + x, 3), dur=round(y - x, 3), mute=True)
    if n % 2:
        s.update(TALK_FRAME)
    return s


def plan_block(sh, t0, L, lead, ws, picks, pools, drop=None, talk=None):
    """The shots of one ugc voice block (ad second t0, L s long, the voice starting `lead` s in; words ws on the voice's
    seconds): shot_groups of its phrases; the picks fill the groups in order, further groups and the parts of a long
    group take spares (Shots.place). Picks left over go to `drop` (the later blocks' spares). A presenter's block (talk:
    {src, a}): a pick [TALK, 0, 1.0] is her on camera for that group (all its shots, in sync with her words); a last pick
    that is TALK is the block's last group however many groups the timings make."""
    cuts = phrase_cuts(ws, lead)
    groups = shot_groups(cuts, L)
    is_t = lambda p: bool(p) and p[0] == TALK                       # noqa: E731
    named = bool(picks) and all(len(p) > 3 and (p[3] or {}).get("say") for p in picks)     # {"say": "beige"}: a colour swatch
    tail_talk = bool(talk) and len(picks) > 1 and is_t(picks[-1])
    body = picks[:-1] if tail_talk else picks
    left, out, gi, nt = list(body), [], 0, 0
    for a, b in groups:
        pts = ugc_pieces(a, b, ws, lead)
        gp = [TALK, 0, 1.0] if tail_talk and (a, b) == groups[-1] else (body[gi] if gi < len(body) else None)
        for j, (x, y) in enumerate(zip(pts, pts[1:])):
            if talk and is_t(gp):
                out.append(talk_seg(talk, x, y, nt))
                nt += 1
                continue
            if named:             # every shot shows the first swatch whose name it says, else the next one
                said = {norm(w["w"]) for w in ws if x - 0.002 <= lead + w["s"] - CUT_LEAD < y - 0.002}
                pick = next((p for p in left if all(t in said for t in p[3]["say"].split())), left[0] if left else None)
                left = [p for p in left if p is not pick]
            else:
                pick = gp if j == 0 else None
            out.append(sh.place(t0 + x, y - x, pick, pools, out[-1] if out else sh.last))
        gi += 1
    if drop is not None and not named:
        drop += [p for p in body[gi:] if not is_t(p)]
    return out


def snap_frames(segs, n_hook=0, fps=30):
    """Segment lengths on the frame grid: each cut at the frame nearest its exact second, so the picture never drifts from
    the sound (recut makes whole frames of every segment). The first n_hook segments (the hook) are snapped on their own
    and the rest from their own start: a hook version of another length never moves a cut of the body."""
    t, done = 0.0, 0                        # exact seconds, frames given out, in the group (the hook, then the body)
    for i, s in enumerate(segs):
        if n_hook and i == n_hook:
            t, done = 0.0, 0
        t += s["dur"]
        f = max(round(t * fps), done + 1)
        s["dur"] = round((f - done) / fps, 3)
        done = f


def shot_key(x):
    return (str(x[0]), round(float(x[1]), 1))


def broll_segs(d, br, L, spare=None, used=None, own=()):
    """Segments for L s of VO over the picks br ([src, start, weight?, extra?]): L split by weight; a part longer than
    MAX_SHOT continues on spare shots (popped from `spare`, skipping any in `used`; the block's `own` spares, chosen for
    it, even when shown elsewhere once nothing else is left), so no shot runs longer."""
    out = []
    br = [x if len(x) > 2 else x + [1.0] for x in br]
    tot = sum(x[2] for x in br)
    spare, used = (spare if spare is not None else []), (used if used is not None else set())
    for src, st, wgt, *ex in br:
        sd = L * wgt / tot
        parts = [[src, st, ex]]
        while sd / len(parts) > MAX_SHOT + 0.05:
            nxt = next((x for x in spare if shot_key(x) not in used), None) or \
                next((x for x in spare if any(x is y for y in own)), None)
            if nxt is None:
                break
            spare.remove(nxt)
            used.add(shot_key(nxt))
            parts.append([nxt[0], nxt[1], nxt[3:4] if len(nxt) > 3 else []])
        for psrc, pst, pex in parts:
            pd = round(sd / len(parts), 3)
            if not str(psrc).lower().endswith(STILL):
                pst, sp = fit(d, psrc, pst, pd)
                if sp != 1.0:
                    pex = [dict(pex[0] if pex else {}, speed=sp)]
            elif not pex:
                pex = [{"zoom": [1.0, 1.06]}]
            s = dict(src=psrc, start=pst, dur=pd, mute=True)
            if pex:
                s.update(pex[0])
            out.append(s)
    return out


def cut_points(ws, a, e, target=SHOT_TARGET):
    """Picture cuts inside a long clip [a, e] (source seconds) about every `target` s, on a pause between two words
    when there is one near (the sound runs on: only the framing changes), never a piece under 1.6 s."""
    gaps = [(x["e"] + y["s"]) / 2 for x, y in zip(ws, ws[1:]) if a < x["e"] and y["s"] < e and y["s"] - x["e"] >= 0.12]
    cuts, cur = [], a
    while e - cur > MAX_SHOT + 0.1:
        want = target if e - cur >= target + 1.6 else (e - cur) / 2      # the last two pieces share what is left
        near = [g for g in gaps if cur + want - 0.9 <= g <= cur + want + 0.7 and g - cur >= 1.6 and e - g >= 1.6]
        c = min(near, key=lambda g: abs(g - cur - want)) if near else cur + want
        cuts.append(round(c, 3))
        cur = c
    return cuts


def frames_of(blk):
    """Framings a long clip block cycles through (recut zoom + focus): the block's 'frames', else wide -> closer on the
    hands and bag -> closer on the speaker (a 9:16 talking clip: face in the upper half, the bag below)."""
    return blk.get("frames") or FRAMES


def said_words(b, d, spans):
    """What the ad says, in ad seconds: each VO block's script (its 'text', else tts_said.json next to the spec) on the
    word timings of its voiceover file (remix.script_words), each clip block's committed / cached transcript. Words of
    a voiceover the script can't be found for keep the transcript's own."""
    out = []
    for k, blk in enumerate(b["blocks"]):
        t0, L, src, off = spans[k]
        if not src:
            continue
        ws = words(loc(d, src))
        if "vo" in blk or "talk" in blk:
            txt = blk.get("text") or (vo_text(d, blk["vo"]) if "vo" in blk else "")
            if txt and "vo_range" not in blk:
                ws = script_words(txt, ws)
        n0 = len(out)
        for w in ws:
            if off - 0.02 <= w["s"] < off + L - 0.05:
                out.append(dict(w=w["w"], s=round(t0 + w["s"] - off, 3), e=round(t0 + min(w["e"], off + L) - off, 3),
                                **({"k": "script"} if w.get("k") == "script" else {})))
        if b.get("mode") == "ugc" and blk.get("number") and len(out) > n0 and not says_number(out[n0:n0 + 4], blk["number"]):
            out[n0]["pre"] = f"{blk['number']}."    # ugc chapter number: "1." before the first caption (not when the chapter says
    return out                                   # its number itself: "Three: does it ...", "Step two", "Myth one": no "3. Three:")


NUM_WORDS = {1: ("one", "first"), 2: ("two", "second"), 3: ("three", "third"), 4: ("four", "fourth"), 5: ("five", "fifth"),
             6: ("six", "sixth"), 7: ("seven", "seventh"), 8: ("eight", "eighth"), 9: ("nine", "ninth"), 10: ("ten", "tenth")}


def says_number(ws, n):
    """True when these words (a chapter's first few) name the chapter's number n: '3', 'three', 'third'."""
    said = {re.sub(r"[^a-z0-9]", "", w["w"].lower()) for w in ws}
    return str(n) in said or any(x in said for x in NUM_WORDS.get(int(n), ()))


def ugc_shots(d, jobs, segs, spare_all, top):
    """ugc: plan the shots of every voice block (jobs, from build) into the placeholders of segs: the body blocks in order
    first (spares left over from one go to the next), the hook last, so a hook version never changes the body's shots,
    then the segment lengths on the frame grid."""
    sh = Shots(d)
    for jb in sorted(jobs, key=lambda j: (j["k"] == 0, j["k"])):
        k, blk = jb["k"], jb["blk"]
        if jb.get("talk"):                        # a presenter's take: its words on the seconds of the cut range
            ws = jb["talk"]["ws"]
        else:
            ws = words(loc(d, blk["vo"]))
            ws = script_words(blk["text"], ws) if blk.get("text") else ws
        drop = None if k == 0 else []             # the hook's spare shots are its own; picks the body does not need
        pools = [jb["own"]] if k == 0 else [jb["own"], spare_all]
        got = plan_block(sh, jb["t"], jb["L"], jb["lead"], ws, [list(x) for x in blk["broll"]], pools, drop, jb.get("talk"))
        spare_all += drop or []
        if k in top:
            for s in got:
                s["caption_pos"] = "top"
        segs[jb["i"]] = got
    n_hook = len(segs[0]) if jobs and jobs[0]["k"] == 0 and isinstance(segs[0], list) else 0
    segs[:] = [y for x in segs for y in (x if isinstance(x, list) else [x])]
    snap_frames(segs, n_hook)


def build(b, d, info=None):
    """-> segs, audio, overlays, total, no-caption windows, block starts. info (a dict) also gets 'words': what is said,
    in ad seconds, with the script's own spelling and punctuation (longform's captions use it instead of transcribing the
    final mix): the VO script on its voiceover's word timings, a clip's committed transcript."""
    ugc = b.get("mode") == "ugc"
    if ugc:
        b = ugc_voices(b, d)                      # the processed voice files (spoken words, durations: all from them)
    segs, audio, spans, leads, t = [], [], [], [], 0.0
    pad = b.get("pad", UGC_PAD if ugc else 0.25)
    used = {shot_key(x) for blk in b["blocks"] for x in blk.get("broll") or []}   # spares never repeat a shot shown
    spare_all = [x for x in b.get("spare_broll") or [] if shot_key(x) not in used]
    last = len(b["blocks"]) - 1
    top = set(b.get("caption_top_blocks") or [])
    clip_tail = None                              # silence after the last word of the clip block just before
    jobs = []                                     # ugc: voice blocks whose shots are planned after the loop
    for k, blk in enumerate(b["blocks"]):
        n0 = len(segs)
        bp = blk.get("pad", pad) + (blk.get("hold", 0.0) if 0 < k < last else 0.0)   # hold: the picture stays after the line
        if ugc:
            bp = blk.get("pad", b.get("hook_pad", UGC_HOOK_PAD)) if k == 0 and last > 0 else max(bp, END_PAD) if k == last else bp
        else:
            bp = max(bp, HOOK_PAD) if k == 0 and last > 0 else max(bp, END_PAD) if k == last else bp
        # the hook's extra shots come only from its own spares (its versions differ; the body must stay identical)
        own = list(blk.get("spare") or [])
        spare = own + ([] if k == 0 else spare_all)
        # a real customer hands back to the narrator: a breath first (her sentence lands before the next voice starts)
        lead = round(max(CLIP_PAD - clip_tail, 0.0), 2) if "vo" in blk and clip_tail is not None else 0.0
        if lead:
            audio.append(("silence", lead))
        if "vo" in blk and "vo_range" in blk:     # slice of a longer VO file
            a, e = blk["vo_range"]
            L = lead + e - a + bp
            segs += broll_segs(d, blk["broll"], L, spare, used, own)
            audio.append(("slice", blk["vo"], a, e))
            audio.append(("silence", bp))
            spans.append((t, L, blk["vo"], a - lead))
        elif "vo" in blk:
            L = lead + dur(loc(d, blk["vo"])) + bp
            if ugc:                               # (planned below, when every block's seconds are known)
                jobs.append(dict(k=k, i=len(segs), t=t, L=L, lead=lead, blk=blk, own=own))
                segs.append(None)
            else:
                segs += broll_segs(d, blk["broll"], L, spare, used, own)
            audio.append(("file", blk["vo"], L - lead))
            spans.append((t, L, blk["vo"], -lead))
        elif "talk" in blk:                       # the presenter's take (presenter.py): her picture and her own voice, B-roll cut in
            tp = loc(d, blk["talk"])              # over it (planned below with the voice blocks: the TALK picks are her on camera)
            ws_t = words(tp)
            if blk.get("text"):
                ws_t = script_words(blk["text"], ws_t)
            a = max(ws_t[0]["s"] - TALK_HEAD, 0.0) if ws_t else 0.0
            e = min(ws_t[-1]["e"] + TALK_TAIL, dur(tp)) if ws_t else dur(tp)
            L = e - a + bp
            wsr = [dict(w, s=round(w["s"] - a, 3), e=round(w["e"] - a, 3)) for w in ws_t]
            jobs.append(dict(k=k, i=len(segs), t=t, L=L, lead=0.0, blk=blk, own=own, talk=dict(src=tp, a=round(a, 3), ws=wsr)))
            segs.append(None)
            audio.append(("slice", blk["talk"], round(a, 3), round(e, 3)))
            audio.append(("silence", bp))
            spans.append((t, L, blk["talk"], a))
        else:
            a, e = blk["range"]
            L = e - a
            ws_c = [] if blk.get("mute") else words(loc(d, blk["clip"]))
            if not blk.get("mute"):               # a real person's own words: whole sentences only
                for p in cadence(ws_c, a, e, f"block {k} clip"):
                    print("cadence:", p, file=sys.stderr)
            cut = blk.get("cutaway")          # {"at": 2.8, "src": "...", "start": 3.6}: J-cut to B-roll, clip audio continues
            v = cut["at"] if cut else L
            # Pacing (Julian: a new shot every 3-5 s): a long clip changes framing about every SHOT_TARGET s, cut on her
            # pauses; picture and sound stay in sync (each piece starts where the last one ended)
            pts = [] if cut or blk.get("seg") or v <= MAX_SHOT + 0.5 else cut_points(ws_c, a, a + v)
            fr = frames_of(blk)
            for j, (x0, x1) in enumerate(zip([a] + pts, pts + [a + v])):
                s = dict(src=blk["clip"], start=round(x0, 3), dur=round(x1 - x0, 3), mute=True)
                if pts and fr[j % len(fr)]:
                    s.update(fr[j % len(fr)])
                s.update(blk.get("seg", {}))
                segs.append(s)
            if cut:
                segs.append(dict(src=cut["src"], start=cut["start"], dur=round(L - v, 3), mute=True))
            if blk.get("mute"):
                audio.append(("silence", L))
            else:
                audio.append(("slice", blk["clip"], a, e))
            spans.append((t, L, None if blk.get("mute") else blk["clip"], a))
        leads.append(lead)
        clip_tail = None
        if "clip" in blk and not blk.get("mute"):
            heard = [w for w in words(loc(d, blk["clip"])) if blk["range"][0] < w["e"] and w["s"] < blk["range"][1]]
            clip_tail = max(blk["range"][1] - heard[-1]["e"], 0.0) if heard else CLIP_PAD
        if k in top:                              # longform.top_windows: captions up top while these segments play
            for s in segs[n0:]:
                if s:
                    s["caption_pos"] = "top"
        if k:                                     # spares the body used are gone for the next blocks
            spare_all[:] = [x for x in spare_all if shot_key(x) not in used]
        t += L
    if ugc:
        ugc_shots(d, jobs, segs, spare_all, top)
    for i in range(1, len(segs)):                 # one clip twice in a row (a feature's 2nd moment): a closer framing,
        p_, s_ = segs[i - 1], segs[i]             # so the cut reads as a new shot, not a jump in the same one
        if not ugc and s_["src"] == p_["src"] and not str(s_["src"]).lower().endswith(STILL) and "zoom" not in s_ and \
                "zoom" not in p_ and "focus" not in s_:
            s_.update(zoom=[1.18, 1.24], focus=[0.5, 0.55])
    if info is not None:
        info["words"] = said_words(b, d, spans)
        info["leads"] = leads

    def word_time(k, w, nth=0):
        t0, L, src, off = spans[k]
        if not src:
            return None
        hits = [x["s"] - off for x in words(loc(d, src)) if off <= x["s"] < off + L
                and (norm(x["w"]).startswith(w) or (num_word(w) and norm(x["w"]).startswith(num_word(w))))]
        if len(hits) > nth:
            return t0 + hits[nth]
        if ugc:                   # the transcript misheard the word (a name): the script's own words, on the same timings
            sw = info["words"] if info is not None else said_words(b, d, spans)
            hs = [x["s"] for x in sw if t0 <= x["s"] < t0 + L and (norm(x["w"]).startswith(w) or (num_word(w) and norm(x["w"]).startswith(num_word(w))))]
            return hs[nth] if len(hs) > nth else None
        return None

    ov = []
    for o in b.get("overlays", []):
        o = dict(o)
        k = o.pop("block")
        t0, L = spans[k][0], spans[k][1]
        at = word_time(k, o.pop("word"), o.pop("nth", 0)) if "word" in o else t0 + leads[k] + o.pop("at", 0.1)
        if at is None:
            print("overlay anchor not found:", o, file=sys.stderr)
            continue
        if o.pop("until_block_end", False) and not ugc:      # (ugc: a review card never stays long: REVIEW_MAX)
            o["dur"] = round(t0 + L - at - 0.1, 2)
        o["at"] = round(at - 0.05, 2)
        o.setdefault("dur", REVIEW_MAX if ugc and o["type"] == "review" else 2.2)
        if ugc and o["type"] == "review":          # (never past its block: the next chapter's caption is under it otherwise)
            o["dur"] = round(min(o["dur"], REVIEW_MAX, t0 + L - o["at"] - 0.05), 2)
        o.setdefault("y", 330 if o["type"] == "review" else 300)
        ov.append(o)
    if ugc:                                       # a review card ends when the next one starts
        rv = sorted((o for o in ov if o["type"] == "review"), key=lambda o: o["at"])
        for x, y in zip(rv, rv[1:]):
            x["dur"] = round(min(x["dur"], y["at"] - x["at"]), 2)
    of = b.get("offer")
    if of and of.get("title", "50% OFF"):
        at = word_time(of["block"], str(of.get("word", "50")).lower())
        title, sub = of.get("title", "50% OFF"), of.get("sub", "+ FREE MATCHING WALLET")
        if at is None:
            print("overlay anchor not found: offer", of, file=sys.stderr)
        else:
            oy = b.get("overlay_y")                    # (a presenter video: under her chin, not over her face)
            ov.append(dict(type="offer", title=title, sub=sub, at=round(at - 0.2, 2), dur=3.2, y=oy or 420) if sub else
                      dict(type="label", text=title, at=round(at - 0.2, 2), dur=3.2, y=oy or 470))
    ep = os.path.join(d, b["end_photo"]) if b.get("end_photo") else None
    ov.append(dict(type="end", title=b.get("end_title", "The Luxury Hobo Bag"), sub=b.get("end_sub", "Tap the link below"),
                   at=round(t - 2.6, 2), dur=2.6, **({"photo": ep, "offer": b.get("end_offer") or ""} if ep and os.path.exists(ep) else {})))
    nocap = [[round(spans[k][0], 2), round(spans[k][0] + spans[k][1], 2)] for k in b.get("no_captions_blocks", [])]
    return segs, audio, ov, t, nocap, [round(x[0], 2) for x in spans[1:]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b = json.load(open(a.board))
    d = os.path.dirname(os.path.abspath(a.board))
    info = {}
    segs, audio, ov, total, nocap, breaks = build(b, d, info)
    name = os.path.splitext(os.path.basename(a.board))[0]
    wav = f"_{name}_audio.wav"
    import music
    ugc = b.get("mode") == "ugc"
    bed = music.resolve(b.get("music"), d, ugc)     # the project's music bed under the voice (none: "music": false)
    mix_audio(audio, d, os.path.join(d, wav), bed, "ugc" if ugc else None)
    if bed:
        print(f"music: {bed['name']} ({bed['kind']}, {bed['gain_db']:.0f} dB under the voice, ducked while someone speaks)",
              file=sys.stderr)
    edl = dict(audio="mute", vo=wav, vo_start=0.0, bed_gain=0.0, segments=segs, overlays=ov, keywords=b.get("keywords", []),
               breaks=breaks, transcript=info.get("words") or [], **caption_opts(b))   # breaks: a caption never runs
    if nocap:                                                                            # across two blocks
        edl["no_captions"] = nocap
    lj = os.path.join(d, f"_{name}_longform.json")
    json.dump(edl, open(lj, "w"), indent=1)
    subprocess.run([sys.executable, os.path.join(HERE, "longform.py"), lj, "--out", a.out], check=True)
    print(json.dumps(dict(out=a.out, seconds=round(total, 2))))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Background music for the storyboard videos (Julian, 2026-10-09: a video without a music bed feels off).

Where the bed comes from, in this order:
  1. a licensed / royalty-free track the client gives us: pipeline/assets/music/*.mp3|m4a|wav (put the tracks of the
     Drive folder 'Ad Creative Pipeline / Music' there and commit them, or point LC_MUSIC_DIR at a folder); one is
     picked per project (the seed), so the 4 hook versions of a project share it;
  2. else a bed made here (generate()): a soft, warm groove (pad chords, a plucked arpeggio, a light bass, a soft kick
     and shaker) synthesised from sine partials and noise with numpy: no sample, no loop, no AI model, so there is
     nothing to license; each seed gives another key, tempo and chord progression.
The bed sits well under the voice (remix.mix_audio: about -15 dB, ducked a further ~6-8 dB whenever someone speaks,
1 s fade in, 1.8 s fade out), so it fills the pauses without competing with the words.

  python3 pipeline/music.py --seed 3 --seconds 90 --out bed.wav     # write a generated bed (to listen to it)
  python3 pipeline/music.py --list                                  # which tracks pick() would use

Library: pick(seed, d) -> dict(path, name, kind 'track'|'generated'); generate(path, seconds, seed); has_bed(path, words)
(a winner RAW with its own bed keeps it; remix.py adds one only to a RAW recorded dry).
"""
import argparse
import glob
import hashlib
import json
import os
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
TRACKS = os.environ.get("LC_MUSIC_DIR") or os.path.join(HERE, "assets", "music")
CACHE = os.path.join(HERE, "cache", "music")
SR = 44100
GAIN_DB = -15.0          # bed level under the voice (the voice is loudnorm'ed to -16 LUFS, the bed to about the same)
GAIN_DB_UGC = GAIN_DB - 6   # the ugc storyboard (a voice talking 90% of the time, one steady level): bed 6 dB lower
LENGTH = 150.0           # a generated bed covers the longest storyboard (story format, ~2 min)
VERSION = 1              # bump when generate() changes: cached beds are made again

NOTE = {n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}
PROGRESSIONS = [         # scale degrees (0 = the key's root chord), major key: warm, unhurried, never sad
    [0, 7, 9, 5],        # I  V  vi IV
    [9, 5, 0, 7],        # vi IV I  V
    [0, 9, 5, 7],        # I  vi IV V
    [5, 0, 7, 9],        # IV I  V  vi
]
KEYS = ["D", "C", "F", "G", "D#", "A"]


def tracks():
    return sorted(f for ext in ("mp3", "m4a", "wav", "aac", "ogg") for f in glob.glob(os.path.join(TRACKS, f"*.{ext}")))


def pick(seed=1, d=None):
    """The bed for one project: a client track when there are any (rotated by seed), else a generated bed (cached in
    pipeline/cache/music, made once per seed)."""
    ts = tracks()
    if ts:
        f = ts[(int(seed) - 1) % len(ts)]
        return dict(path=f, name=os.path.basename(f), kind="track")
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, f"bed_v{VERSION}_s{int(seed)}.wav")
    if not os.path.exists(f):
        generate(f, LENGTH, int(seed))
    return dict(path=f, name=f"generated bed {int(seed)} ({describe(int(seed))})", kind="generated")


def plan_of(seed):
    """(key, bpm, progression) of a generated bed."""
    h = int(hashlib.md5(f"bed{seed}".encode()).hexdigest(), 16)
    return KEYS[h % len(KEYS)], 84 + (h // 7) % 5 * 4, PROGRESSIONS[(h // 41) % len(PROGRESSIONS)]


def describe(seed):
    key, bpm, prog = plan_of(seed)
    names = {0: "I", 5: "IV", 7: "V", 9: "vi"}
    return f"{key} major, {bpm} bpm, {'-'.join(names[x] for x in prog)}"


def generate(path, seconds=LENGTH, seed=1):
    """A soft groove, seconds long, as a 16-bit stereo wav at 44.1 kHz (see the module doc)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    key, bpm, prog = plan_of(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    n = int(seconds * SR)
    L, R = np.zeros(n), np.zeros(n)
    root = 48 + NOTE[key]                                 # MIDI: the key's root around C3

    def hz(m):
        return 440.0 * 2 ** ((m - 69) / 12)

    def chord(deg):                                       # triad + 7th/9th colour on a major-key degree
        minor = deg in (2, 4, 9)
        third = 3 if minor else 4
        return [root + deg, root + deg + third, root + deg + 7, root + deg + (10 if minor else 11 if deg in (0, 5) else 14)]

    def add(buf, start, sig):
        i = int(start * SR)
        if i >= n:
            return
        sig = sig[: n - i]
        buf[i:i + len(sig)] += sig

    def tone(f, dur, partials, decay=0.0, attack=0.01, release=0.08, detune=0.0):
        t = np.arange(int(dur * SR)) / SR
        s = np.zeros_like(t)
        for h, a in partials:
            for dt in ((-detune, detune) if detune else (0.0,)):
                s += a * np.sin(2 * np.pi * f * h * (1 + dt) * t + rng.uniform(0, 2 * np.pi)) * (
                    np.exp(-t * decay * (1 + 0.6 * (h - 1))) if decay else 1.0)
        env = np.minimum(1.0, t / max(attack, 1e-3)) * np.minimum(1.0, (dur - t) / max(release, 1e-3))
        return s * np.clip(env, 0, 1)

    nbars = int(seconds / bar) + 2
    for b in range(nbars):
        t0 = b * bar
        notes = chord(prog[b % len(prog)])
        # pad: the chord held over the bar, slow attack, soft (fundamental + a little 2nd partial), slightly detuned
        for m in notes:
            p = tone(hz(m + 12), bar + 0.6, [(1, 0.5), (2, 0.12), (3, 0.04)], attack=0.7, release=0.7, detune=0.0018)
            add(L, t0, p * 0.055)
            add(R, t0, p * 0.055)
        if b == 0:
            continue                                      # the first bar: the pad alone (a soft start)
        # bass: root on beats 1 and 3 (and a pickup on the "and" of 4 every other bar)
        for q, lvl in ((0, 1.0), (2, 0.8)) + (((3.5, 0.5),) if b % 2 else ()):
            s = tone(hz(notes[0] - 12), beat * 0.95, [(1, 1.0), (2, 0.25)], decay=2.2, attack=0.01, release=0.12)
            add(L, t0 + q * beat, s * 0.16 * lvl)
            add(R, t0 + q * beat, s * 0.16 * lvl)
        # plucked arpeggio: eighth notes over the chord, an octave up, alternating left / right, varied velocity
        pattern = [0, 2, 1, 3, 2, 1, 3, 2] if b % 4 < 2 else [0, 1, 2, 3, 2, 3, 1, 2]
        for e, idx in enumerate(pattern):
            if b % 8 == 7 and e >= 6:
                continue                                  # a little air at the end of each 8-bar phrase
            m = notes[idx] + 24 - (12 if idx == 3 else 0)
            s = tone(hz(m), beat * 1.6, [(1, 1.0), (2, 0.35), (3, 0.12), (4, 0.05)], decay=3.4, attack=0.004, release=0.2)
            v = 0.05 * rng.uniform(0.7, 1.0) * (1.15 if e % 2 == 0 else 0.9)
            pan = 0.35 if e % 2 else -0.35
            add(L, t0 + e * beat / 2, s * v * (1 - pan))
            add(R, t0 + e * beat / 2, s * v * (1 + pan))
        # soft kick on 1 and 3: a short sine sweep
        for q in (0, 2):
            t = np.arange(int(0.22 * SR)) / SR
            f = 50 + 70 * np.exp(-t * 30)
            k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
            add(L, t0 + q * beat, k * 0.16)
            add(R, t0 + q * beat, k * 0.16)
        # shaker on the eighths (high-passed noise bursts), a soft clap-ish tick on 2 and 4
        for e in range(8):
            t = np.arange(int(0.05 * SR)) / SR
            z = rng.standard_normal(len(t))
            z = np.diff(np.concatenate([[0.0], z])) * np.exp(-t * 70)
            lvl = 0.006 if e % 2 else 0.0035
            add(L, t0 + e * beat / 2 + 0.006, z * lvl * 0.8)
            add(R, t0 + e * beat / 2, z * lvl)
        for q in (1, 3):
            t = np.arange(int(0.12 * SR)) / SR
            z = rng.standard_normal(len(t))
            z = (z - np.concatenate([[0.0], z[:-1]]) * 0.6) * np.exp(-t * 32)
            add(L, t0 + q * beat, z * 0.012)
            add(R, t0 + q * beat, z * 0.012)
    mix = np.stack([L, R], axis=1)
    mix = np.tanh(mix * 1.4) / 1.4                        # gentle saturation: no harsh peaks
    mix *= 0.89 / max(np.abs(mix).max(), 1e-6)            # -1 dBFS peak
    part = f"{path}.{os.getpid()}.wav"
    with wave.open(part, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    os.replace(part, path)
    return path


def has_bed(path, ws, floor=-52.0, below=30.0):
    """True when the recording has its own sound under the voice (a music bed, an ambience): its pauses between words
    (>= 0.3 s, edges trimmed) sit above `floor` dBFS and less than `below` dB under the speech. A RAW recorded dry (only
    the voice, digital silence in its pauses) -> False: remix.py then gives it a bed (lead 2026-10-11: winners keep the
    RAW's own sound unless it is silent). Too few pauses: the quietest tenth of its spoken span is measured instead."""
    import subprocess
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if not len(x) or not ws:
        return True                                       # nothing to judge by: leave the recording as it is

    def lev(a, b):
        s = x[int(a * 16000):int(b * 16000)]
        return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9) if len(s) > 160 else None
    speech = [v for v in (lev(w["s"], w["e"]) for w in ws) if v is not None]
    gaps = [v for p, q in zip(ws, ws[1:]) if q["s"] - p["e"] >= 0.3 for v in [lev(p["e"] + 0.08, q["s"] - 0.08)]
            if v is not None]
    if len(gaps) < 2:
        a, b = int(ws[0]["s"] * 16000), int(ws[-1]["e"] * 16000)
        n = max((b - a) // 800, 1)
        fr = 20 * np.log10(np.sqrt((x[a:a + n * 800].reshape(n, -1) ** 2).mean(axis=1)) + 1e-9)
        gaps = [float(np.percentile(fr, 10))]
    g, sp = float(np.median(gaps)), float(np.median(speech)) if speech else -20.0
    return g > floor and sp - g < below


def resolve(spec_music, d=None, ugc=False):
    """A spec's 'music' -> pick() result or None: false/absent = none; {"seed": N} = pick(N); {"src": file} = that file
    (relative to the spec's folder); a string = a file. ({"auto": true, "seed": N} is remix.py's: a bed only when the
    RAW has no sound of its own, has_bed().) ugc: the storyboard's ugc format, a bed GAIN_DB_UGC under the voice."""
    m = spec_music
    if not m:
        return None
    if isinstance(m, str):
        m = {"src": m}
    if m.get("src"):
        f = m["src"] if os.path.isabs(m["src"]) else os.path.join(d or ".", m["src"])
        return dict(path=f, name=os.path.basename(f), kind="track", gain_db=m.get("gain_db", GAIN_DB_UGC if ugc else GAIN_DB))
    r = pick(m.get("seed", 1), d)
    r["gain_db"] = m.get("gain_db", GAIN_DB_UGC if ugc else GAIN_DB)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=LENGTH)
    ap.add_argument("--out")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print(json.dumps(dict(folder=TRACKS, tracks=tracks(), fallback="generated beds" if not tracks() else None), indent=1))
        return
    if not a.out:
        ap.error("--out (or --list)")
    generate(a.out, a.seconds, a.seed)
    print(json.dumps(dict(out=a.out, seconds=a.seconds, bed=describe(a.seed))))


if __name__ == "__main__":
    sys.exit(main())

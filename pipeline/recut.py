#!/usr/bin/env python3
"""Build a 9:16 UGC recut from real library clips, driven by a JSON edit list.

Only the needed seconds of each Drive clip are read (HTTP range reads).

  python3 pipeline/recut.py edl.json --out ad.mp4

EDL format:
{
  "hook": "the pocket nobody checks",          # plate in the top third during the first segment(s)
  "hook_until": 2.2,                            # seconds the hook plate stays on
  "audio": "natural" | "mute",                  # default natural (clip sound); per-segment "mute": true
  "vo": "voiceover.mp3",                        # optional narrator track (path relative to the EDL)
  "vo_start": 1.8,                              # seconds into the ad the VO starts
  "bed_gain": 0.3,                              # clip sound level under the VO (foley bed)
  "sfx": [{"src": "click.wav", "at": 0.0, "gain": 1.0}],   # optional one-shot sounds (paths relative to the EDL)
  "segments": [
    {"src": "<drive id or file>", "start": 3.0, "dur": 1.6,
     "focus": [0.5, 0.5],       # crop centre (fractions) for the 9:16 crop
     "zoom": [1.0, 1.08],       # punch-in from -> to over the segment (1.0 = full 9:16 crop)
     "speed": 1.0,              # >1 faster (source seconds consumed = dur * speed)
     "caption": "on the BACK",  # boxed caption in the caption band (y ~ 900-1150)
     "mute": false}             # src may also be a still image (.png/.jpg): held for dur, silent
  ]
}
"""
import argparse
import concurrent.futures as cf
import json
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_library import CACHE, direct_url, file_size  # noqa: E402
from media import DRIVE_ID  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


def boxed_text(d, text, cy, size, weight="ExtraBold", max_w=900):
    """White rounded box with black Montserrat, wrapped, centred on cy."""
    f = font("Montserrat.ttf", size, weight)
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    lh = int(size * 1.22)
    y = cy - lh * len(lines) / 2
    for ln in lines:
        tw = d.textlength(ln, font=f)
        pad_x, pad_y = 26, 12
        d.rounded_rectangle([(W - tw) / 2 - pad_x, y - pad_y, (W + tw) / 2 + pad_x, y + size + pad_y + 4],
                            radius=18, fill=(255, 255, 255, 245))
        d.text(((W - tw) / 2, y), ln, font=f, fill=(0, 0, 0, 255))
        y += lh + 14


def overlay_png(path, caption=None, hook=None):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if hook:
        boxed_text(d, hook, 380, 72)          # top third, below the 270 px UI zone
    if caption:
        boxed_text(d, caption, 1030, 62)      # caption band, above the bottom 35 % UI zone
    im.save(path)
    return path


MEDIA_CACHE = os.path.join(os.path.dirname(CACHE), "media")
LOCAL_MAX = 150 * 2**20  # clips up to this size are downloaded once; bigger ones are range-read


def source(s):
    """Local path for a Drive clip (cached download when small), else the direct URL for range reads."""
    if os.path.exists(s) or not DRIVE_ID.match(s):
        return s
    local = os.path.join(MEDIA_CACHE, s)
    if os.path.exists(local):
        return local
    size = file_size(s) or 0
    if 0 < size <= LOCAL_MAX:
        os.makedirs(MEDIA_CACHE, exist_ok=True)
        # 1 MB range requests in parallel: whole-file GETs (and ranges of a few MB or more) of shared
        # files hit Drive's download quota ("Quota exceeded" HTML page); small ranges do not.
        chunk = 2**20

        def part(off):
            want = min(chunk, size - off)
            for _ in range(4):
                r = subprocess.run(["curl", "-sSL", "-r", f"{off}-{off + want - 1}", direct_url(s)],
                                   capture_output=True, timeout=120)
                if r.returncode == 0 and len(r.stdout) == want:
                    return r.stdout
                time.sleep(2)
            return None

        with cf.ThreadPoolExecutor(8) as ex:
            parts = list(ex.map(part, range(0, size, chunk)))
        ok = all(p is not None for p in parts)
        if ok:
            with open(local + ".part", "wb") as out:
                out.write(b"".join(parts))
        if ok:
            os.replace(local + ".part", local)
            return local
    return direct_url(s)


def render_segment(seg, i, tmp, hook, audio_mode):
    speed = float(seg.get("speed", 1.0))
    dur = float(seg["dur"])
    fx, fy = seg.get("focus", [0.5, 0.5])
    z0, z1 = seg.get("zoom", [1.0, 1.0])
    n = max(int(round(dur * FPS)), 1)
    # 9:16 crop around the focus point, then a smooth punch-in via per-frame crop scale.
    zoom = f"({z0}+({z1}-{z0})*n/{n})"
    vf = (
        f"setpts=PTS/{speed},fps={FPS},"
        f"crop='min(iw,ih*9/16)/{zoom}':'min(ih,iw*16/9)/{zoom}':"
        f"'max(0,min(iw-ow,iw*{fx}-ow/2))':'max(0,min(ih-oh,ih*{fy}-oh/2))',"
        f"scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p"
    )
    ov = overlay_png(os.path.join(tmp, f"ov{i}.png"), seg.get("caption"), hook)
    mute = audio_mode == "mute" or seg.get("mute")
    out = os.path.join(tmp, f"seg{i:02d}.mp4")
    still = seg["src"].lower().endswith((".png", ".jpg", ".jpeg"))
    if still:
        mute = True
    src_in = (["-loop", "1", "-framerate", str(FPS), "-t", f"{dur * speed:.3f}", "-i", seg["src"]] if still else
              ["-ss", str(seg.get("start", 0)), "-t", f"{dur * speed:.3f}", "-i", source(seg["src"])])
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *src_in, "-loop", "1", "-t", f"{dur:.3f}", "-i", ov,
           "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
           "-filter_complex",
           f"[0:v]{vf}[v];[1:v]format=rgba,fade=t=in:st=0:d=0.12:alpha=1[o];[v][o]overlay=0:0:shortest=1[vo]" +
           ("" if mute else f";[0:a]atempo={min(max(speed, 0.5), 2.0)},aresample=48000,apad[a]"),
           "-map", "[vo]", "-map", "2:a" if mute else "[a]", "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-y", out]
    for attempt in range(3):  # Drive range reads occasionally fail to open; retry before giving up
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if not any(m in r.stderr for m in ("Error opening input", "Invalid data found")):
            break
        time.sleep(3 * (attempt + 1))
    if r.returncode and not mute:  # clip without an audio stream: retry silent
        seg = dict(seg, mute=True)
        return render_segment(seg, i, tmp, hook, audio_mode)
    if r.returncode:
        raise RuntimeError(f"segment {i} failed: {r.stderr[-400:]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    edl = json.load(open(a.edl))
    tmp = tempfile.mkdtemp(prefix="recut_")
    t, parts = 0.0, []
    edl_dir = os.path.dirname(os.path.abspath(a.edl))
    for i, seg in enumerate(edl["segments"]):
        local = os.path.join(edl_dir, seg["src"])
        if not DRIVE_ID.match(seg["src"]) and os.path.exists(local):
            seg = dict(seg, src=local)  # local files resolve relative to the EDL
        hook = edl.get("hook") if t < float(edl.get("hook_until", 2.0)) else None
        parts.append(render_segment(seg, i, tmp, hook, edl.get("audio", "natural")))
        t += float(seg["dur"])
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    inputs, norm = ["-f", "concat", "-safe", "0", "-i", lst], "loudnorm=I=-14:TP=-1.5:LRA=11"
    extras = ([dict(src=edl["vo"], at=edl.get("vo_start", 0), gain=1.0)] if edl.get("vo") else []) + edl.get("sfx", [])
    gain = edl.get("bed_gain", 0.3) if edl.get("vo") else 1.0
    fc, labels = [f"[0:a]volume={gain}[bed]"], ["[bed]"]
    for k, x in enumerate(extras, 1):
        inputs += ["-i", os.path.join(edl_dir, x["src"])]
        ms = int(float(x.get("at", 0)) * 1000)
        fc.append(f"[{k}:a]aresample=48000,volume={x.get('gain', 1.0)},adelay={ms}|{ms}[x{k}]")
        labels.append(f"[x{k}]")
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,{norm}[aout]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                    "-movflags", "+faststart", "-y", a.out], check=True, timeout=1800)
    print(json.dumps(dict(out=a.out, seconds=round(t, 2), segments=len(parts))))


if __name__ == "__main__":
    main()

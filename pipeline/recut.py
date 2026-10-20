#!/usr/bin/env python3
"""Build a 9:16 UGC recut from real library clips, driven by a JSON edit list.

Only the needed seconds of each Drive clip are read (HTTP range reads).

  python3 pipeline/recut.py edl.json --out ad.mp4

EDL format:
{
  "hook": "the pocket nobody checks",          # plate in the top third during the first segment(s)
  "hook_until": 2.2,                            # seconds the hook plate stays on
  "hook_y": 380,                                # hook plate centre; use ~1060 over a talking face
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
     "mute": false,             # src may also be a still image
     "fx": "bw",                # optional look: "bw" (black & white problem shot) or "warm" (.png/.jpg): held for dur, silent
     "fit": "auto",             # media far from 9:16 (square / landscape product shots): no crop, the whole frame at
                                # the output width (or height), over "blur" (a blurred, darkened fill of itself; a dark
                                # border: its blacks lifted, never black bars), "pad" (the flat colour of its border:
                                # seamless on studio packshots) or "auto" (pad when the border is uniform and light, else
                                # blur); zoom grows the frame (a real punch-in), focus is ignored; a source within 8 % of
                                # 9:16 is cropped as without "fit"; a phone photo's EXIF orientation is applied
     "fit_y": 0.42}             # centre of the fitted frame (fraction of the height)
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
from index_library import CACHE, direct_url, file_size, range_bytes  # noqa: E402
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


def overlay_png(path, caption=None, hook=None, hook_y=380):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if hook:
        boxed_text(d, hook, hook_y, 72)       # default top third, below the 270 px UI zone
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
                b = range_bytes(s, off, want)       # (the Drive API with the agent's token first: no download quota; else the public link)
                if b is not None:
                    return b
                time.sleep(2)
            return None

        with cf.ThreadPoolExecutor(8) as ex:
            parts = list(ex.map(part, range(0, size, chunk)))
        if all(p is not None for p in parts):
            tmp = f"{local}.part.{os.getpid()}"            # per process: parallel renders may fetch the same clip
            with open(tmp, "wb") as out:
                out.write(b"".join(parts))
            os.replace(tmp, local)
            return local
    return direct_url(s)


FIT_TOL = 0.08      # "fit": a source whose w/h is within 8 % of 9:16 is cropped as before
DARK, LIFT = 60, 28  # blur fill of a source whose border luma is under DARK: not darkened, its blacks lifted to LIFT
_DIMS, _EDGES = {}, {}


def upright(im):
    """A still as ffmpeg shows it: ffmpeg applies the EXIF orientation of a phone photo (5-8: turned a quarter)."""
    from PIL import ImageOps
    return ImageOps.exif_transpose(im)


def dims(path, still):
    """(w, h) of a still or a clip as ffmpeg shows it (EXIF orientation / display-matrix rotation applied); None if
    unreadable. Cached."""
    if path not in _DIMS:
        try:
            if still:
                im = Image.open(path)
                o = im.getexif().get(0x0112)
                _DIMS[path] = im.size[::-1] if o in (5, 6, 7, 8) else im.size
            else:
                r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height:stream_side_data=rotation", "-of", "json", path],
                                   capture_output=True, text=True, timeout=120)
                s = json.loads(r.stdout)["streams"][0]
                rot = abs(int(float(next((d["rotation"] for d in s.get("side_data_list", []) if "rotation" in d), 0))))
                _DIMS[path] = (s["height"], s["width"]) if rot % 180 == 90 else (s["width"], s["height"])
        except Exception:
            _DIMS[path] = None
    return _DIMS[path]


def edges(path, still, t0, span, wide):
    """(uniform and light, colour A, colour B) of the source's border: its 95th-percentile spread from the median and
    the median's lightness, sampled on the still (upright) or 3 frames across the clip's span; A / B = median colours of
    the two edges the background meets (top / bottom when fitted to the width, left / right when fitted to the height)."""
    import numpy as np
    key = (path, wide) if still else (path, round(t0, 2), round(span, 2), wide)
    if key not in _EDGES:
        if still:
            fr = [np.asarray(upright(Image.open(path)).convert("RGB").resize((160, 160)), dtype=np.float32)]
        else:
            fr = []
            for f in (0.1, 0.5, 0.9):
                r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0 + span * f:.3f}", "-i", path, "-frames:v", "1",
                                    "-vf", "scale=160:160", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                   capture_output=True, timeout=120)
                if len(r.stdout) == 160 * 160 * 3:
                    fr.append(np.frombuffer(r.stdout, np.uint8).reshape(160, 160, 3).astype(np.float32))
        if not fr:
            _EDGES[key] = (False, "000000", "000000")
            return _EDGES[key]
        a, k = np.stack(fr), 5
        ring = np.concatenate([x.reshape(-1, 3) for x in (a[:, :k], a[:, -k:], a[:, :, :k], a[:, :, -k:])])
        med = np.median(ring, 0)
        flat = np.percentile(np.abs(ring - med).max(1), 95) <= 18 and med @ (0.299, 0.587, 0.114) >= 165
        sides = (a[:, :k], a[:, -k:]) if wide else (a[:, :, :k], a[:, :, -k:])
        _EDGES[key] = (bool(flat), *("%02x%02x%02x" % tuple(int(round(v)) for v in np.median(s.reshape(-1, 3), 0))
                                     for s in sides))
    return _EDGES[key]


def fit_layout(seg, still, path):
    """None (the 9:16 crop) or how a "fit" segment is laid out: mode, the frame's size at zoom 1 (the output width, or
    the height for a source taller than 9:16; never scaled more than that), its centre y and the pad colours."""
    mode = str(seg.get("fit") or "").lower()
    wh = None if mode in ("", "false", "none", "no", "off", "0") else dims(path, still)
    if not wh or abs(wh[0] / wh[1] / (W / H) - 1) <= FIT_TOL:
        return None
    s = min(W / wh[0], H / wh[1])
    fw, fh = min(2 * round(wh[0] * s / 2), W), min(2 * round(wh[1] * s / 2), H)
    wide = fw == W
    cy = min(max(float(seg.get("fit_y", 0.42)) * H, fh / 2), H - fh / 2)
    lay = dict(mode=mode if mode in ("blur", "pad") else "auto", fw=fw, fh=fh, cy=round(cy), wide=wide)
    flat, *lay["colours"] = edges(path, still, float(seg.get("start", 0)),
                                  float(seg["dur"]) * float(seg.get("speed", 1.0)), wide)
    if lay["mode"] == "auto":
        lay["mode"] = "pad" if flat else "blur"
    # a dark border (a dark clip's table, a night shot) blurred and darkened reads as black letterbox bars: lifted instead
    lay["dark"] = min(int(c[:2], 16) * 0.299 + int(c[2:4], 16) * 0.587 + int(c[4:], 16) * 0.114
                      for c in lay["colours"]) < DARK
    return lay


def fit_graph(lay, pre, z0, z1, n, look):
    """[0:v] -> [v] for a fit layout: the frame over a blurred, darkened fill of itself (on a 1/4 size copy: fast; a dark
    border lifted instead, lay["dark"]) or over its border colours (split where the frame covers it), punched in from z0
    to z1 about its centre."""
    fw, fh, cy = lay["fw"], lay["fh"], lay["cy"]
    if z0 == z1:
        w, h = 2 * round(fw * z0 / 2), 2 * round(fh * z0 / 2)
        fg, xy = f"scale={w}:{h}:flags=lanczos", f"{(W - w) // 2}:{round(cy - h / 2)}"
    else:
        z = f"({z0}+({z1}-{z0})*n/{n})"
        fg = f"scale=w='trunc({fw}*{z}/2)*2':h='trunc({fh}*{z}/2)*2':eval=frame:flags=lanczos"
        xy = f"x='(W-w)/2':y='{cy}-h/2':eval=frame"
    tail = f"[bg][fg]overlay={xy}:shortest=1,setsar=1,{look}format=yuv420p[v]"
    if lay["mode"] == "pad":
        a, b = lay["colours"]
        cut = 2 * round(cy / 2) if lay["wide"] else W // 2
        sz = (f"{W}x{cut}", f"{W}x{H - cut}") if lay["wide"] else (f"{cut}x{H}", f"{W - cut}x{H}")
        return (f"[0:v]{pre},{fg}[fg];color=c=0x{a}:s={sz[0]}:r={FPS}[c1];color=c=0x{b}:s={sz[1]}:r={FPS}[c2];"
                f"[c1][c2]{'vstack' if lay['wide'] else 'hstack'}[bg];{tail}")
    lut = f"lutyuv=y='{LIFT}+val*0.75'" if lay.get("dark") else "lutyuv=y=val*0.8"
    return (f"[0:v]{pre},split[a][b];[a]{fg}[fg];[b]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,"
            f"crop={W // 4}:{H // 4},gblur=sigma=8:steps=2,{lut},scale={W}:{H}:flags=bicubic,setsar=1[bg];"
            f"{tail}")


def render_segment(seg, i, tmp, hook, audio_mode, hook_y=380):
    speed = float(seg.get("speed", 1.0))
    dur = float(seg["dur"])
    fx, fy = seg.get("focus", [0.5, 0.5])
    z0, z1 = seg.get("zoom", [1.0, 1.0])
    n = max(int(round(dur * FPS)), 1)
    # 9:16 crop around the focus point at zoom z0: crop evaluates its w/h once (n=0), so z1 never shows here (a "fit"
    # segment does punch in from z0 to z1)
    zoom = f"({z0}+({z1}-{z0})*n/{n})"
    look = {"bw": "hue=s=0,eq=contrast=1.08,", "warm": "colorbalance=rs=0.04:bs=-0.04,"}.get(seg.get("fx", ""), "")
    vf = (
        f"setpts=PTS/{speed},fps={FPS},"
        f"crop='min(iw,ih*9/16)/{zoom}':'min(ih,iw*16/9)/{zoom}':"
        f"'max(0,min(iw-ow,iw*{fx}-ow/2))':'max(0,min(ih-oh,ih*{fy}-oh/2))',"
        f"scale={W}:{H}:flags=lanczos,setsar=1,{look}format=yuv420p"
    )
    ov = overlay_png(os.path.join(tmp, f"ov{i}.png"), seg.get("caption"), hook, hook_y)
    mute = audio_mode == "mute" or seg.get("mute")
    out = os.path.join(tmp, f"seg{i:02d}.mp4")
    still = seg["src"].lower().endswith((".png", ".jpg", ".jpeg"))
    if still:
        mute = True
    src = seg["src"] if still else source(seg["src"])
    lay = fit_layout(seg, still, src) if seg.get("fit") else None    # no "fit": exactly the crop command as before
    vg = fit_graph(lay, f"setpts=PTS/{speed},fps={FPS}", z0, z1, n, look) if lay else f"[0:v]{vf}[v]"
    src_in = (["-loop", "1", "-framerate", str(FPS), "-t", f"{dur * speed:.3f}", "-i", src] if still else
              ["-ss", str(seg.get("start", 0)), "-t", f"{dur * speed:.3f}", "-i", src])
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *src_in, "-loop", "1", "-t", f"{dur:.3f}", "-i", ov,
           "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
           "-filter_complex",
           f"{vg};[1:v]format=rgba,fade=t=in:st=0:d=0.12:alpha=1[o];[v][o]overlay=0:0:shortest=1[vo]" +
           ("" if mute else f";[0:a]atempo={min(max(speed, 0.5), 2.0)},aresample=48000,apad[a]"),
           "-map", "[vo]", "-map", "2:a" if mute else "[a]", "-t", f"{dur:.3f}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-y", out]
    for attempt in range(3):  # Drive range reads occasionally fail to open; retry before giving up
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if not any(m in r.stderr for m in ("Error opening input", "Invalid data found")):
            break
        time.sleep(3 * (attempt + 1))
    if r.returncode and not mute:  # clip without an audio stream: retry silent
        seg = dict(seg, mute=True)
        return render_segment(seg, i, tmp, hook, audio_mode, hook_y)
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
        parts.append(render_segment(seg, i, tmp, hook, edl.get("audio", "natural"), edl.get("hook_y", 380)))
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

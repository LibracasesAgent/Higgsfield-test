#!/usr/bin/env python3
"""Premium product-film edit: graded shots joined by ffmpeg xfade transitions, grain, vignette,
light-leak flashes and animated serif titles. Counterpart to recut.py (native UGC look).

  python3 pipeline/premium.py film.json --out film.mp4

film.json (paths relative to the JSON; src may also be a Drive id or a still image):
{
  "grade": "warm" | "cool" | "none",   "grain": 7,   "vignette": true,   "letterbox": 0,
  "shots": [
    {"src": "macro_zip.mp4", "start": 0, "dur": 3.0, "speed": 0.6, "smooth": true,
     "focus": [0.5, 0.5], "zoom": [1.0, 1.08]}
  ],
  "transitions": [{"type": "fadewhite", "dur": 0.35}, ...],   # len(shots) - 1; any ffmpeg xfade type
  "leaks": [2.6, 7.9],                                         # warm light-leak flashes at these times
  "titles": [{"text": "Soft, structured leather.", "sub": "THE HOBO BAG", "at": 0.6, "dur": 2.4,
              "y": 1350, "size": 78, "color": "#faf4ec"}],
  "cta": {"text": "Shop now", "at": 13.0, "dur": 2.0, "y": 1560, "color": "#faf4ec"},
  "sfx": [{"src": "whoosh.wav", "at": 2.6, "gain": 0.8}],
  "vo": "vo.mp3", "vo_start": 0.5, "bed_gain": 0.5
}
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recut import source  # noqa: E402  (Drive ids -> cached local file)

W, H, FPS = 1080, 1920, 30
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
GRADES = {
    "warm": "colorbalance=rs=0.05:bs=-0.05:rm=0.03:bm=-0.03:rh=0.02:bh=-0.02,"
            "eq=contrast=1.07:saturation=1.06:gamma=0.98,curves=master='0/0 0.25/0.21 0.75/0.79 1/1'",
    "cool": "colorbalance=rs=-0.03:bs=0.04,eq=contrast=1.06:saturation=0.95",
    "none": "null",
}


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def tracked(d, xy, text, f, fill, tracking):
    """Draw text with extra letter spacing; returns width."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking
    return x - xy[0] - tracking


def tracked_width(d, text, f, tracking):
    return sum(d.textlength(ch, font=f) for ch in text) + tracking * (len(text) - 1)


def title_png(path, t):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = hex_rgb(t.get("color", "#faf4ec"))
    y = t.get("y", 1350)
    if t.get("sub"):
        fs = font("Inter.ttf", t.get("sub_size", 30), "Medium")
        tw = tracked_width(d, t["sub"], fs, 9)
        tracked(d, ((W - tw) / 2, y - 64), t["sub"], fs, col + (235,), 9)
    fh = font("CormorantGaramond.ttf", t.get("size", 78), "SemiBold")
    for i, line in enumerate(t["text"].split("|")):
        tw = d.textlength(line, font=fh)
        d.text(((W - tw) / 2, y + i * int(fh.size * 1.08)), line, font=fh, fill=col + (255,))
    if t.get("shadow") is False:
        im.save(path)
        return path
    # soft shadow for legibility on bright frames
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 110), mask=im.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    out = Image.alpha_composite(sh, im)
    out.save(path)
    return path


def cta_png(path, c):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Inter.ttf", c.get("size", 34), "SemiBold")
    txt = c["text"].upper()
    tw = tracked_width(d, txt, f, 5)
    pw, ph = tw + 110, 92
    x, y = (W - pw) / 2, c.get("y", 1560)
    col = hex_rgb(c.get("color", "#faf4ec"))
    d.rounded_rectangle([x, y, x + pw, y + ph], radius=ph / 2, outline=col + (255,), width=3, fill=col + (40,))
    asc, desc = f.getmetrics()
    tracked(d, (x + 55, y + (ph - asc - desc) / 2), txt, f, col + (255,), 5)
    im.save(path)
    return path


def leak_png(path):
    """Warm radial light leak from the top-right corner, as an RGBA overlay."""
    w, h = W // 4, H // 4
    a = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(a)
    for r, v in [(300, 70), (220, 130), (140, 190), (70, 230)]:
        d.ellipse([w - r, -r * 0.7, w + r, r * 1.1], fill=v)
    a = a.filter(ImageFilter.GaussianBlur(45)).resize((W, H), Image.BICUBIC)
    im = Image.new("RGBA", (W, H), (255, 168, 80, 0))
    im.putalpha(a)
    im.save(path)
    return path


def render_shot(s, i, tmp, edl_dir, grade):
    speed = float(s.get("speed", 1.0))
    dur = float(s["dur"])
    fx, fy = s.get("focus", [0.5, 0.5])
    z0, z1 = s.get("zoom", [1.0, 1.0])
    n = max(int(round(dur * FPS)), 1)
    zoom = f"({z0}+({z1}-{z0})*n/{n})"
    src = s["src"]
    local = os.path.join(edl_dir, src)
    src = local if os.path.exists(local) else source(src)
    still = src.lower().endswith((".png", ".jpg", ".jpeg"))
    smooth = f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:vsbmc=1," if s.get("smooth") and speed < 1 else ""
    vf = (f"setpts=PTS/{speed},{smooth}fps={FPS},"
          f"crop='min(iw,ih*9/16)/{zoom}':'min(ih,iw*16/9)/{zoom}':"
          f"'max(0,min(iw-ow,iw*{fx}-ow/2))':'max(0,min(ih-oh,ih*{fy}-oh/2))',"
          f"scale={W}:{H}:flags=lanczos,setsar=1,{GRADES[grade]},format=yuv420p")
    inp = (["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", src] if still else
           ["-ss", str(s.get("start", 0)), "-t", f"{dur * speed + 0.1:.3f}", "-i", src])
    out = os.path.join(tmp, f"shot{i:02d}.mp4")
    base = ["ffmpeg", "-hide_banner", "-loglevel", "error", *inp, "-f", "lavfi", "-t", f"{dur:.3f}",
            "-i", "anullsrc=r=48000:cl=stereo"]
    enc = ["-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-c:a", "aac", "-ar", "48000",
           "-ac", "2", "-y", out]
    with_audio = base + ["-filter_complex", f"[0:v]{vf}[v];[0:a]atempo={min(max(speed, 0.5), 2.0)},aresample=48000,"
                         f"apad[a]", "-map", "[v]", "-map", "[a]"] + enc
    silent = base + ["-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a"] + enc
    if still or s.get("mute") or subprocess.run(with_audio, capture_output=True).returncode:
        r = subprocess.run(silent, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"shot {i} failed: {r.stderr[-500:]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    e = json.load(open(a.edl))
    edl_dir = os.path.dirname(os.path.abspath(a.edl))
    tmp = tempfile.mkdtemp(prefix="premium_")
    shots = e["shots"]
    parts = [render_shot(s, i, tmp, edl_dir, e.get("grade", "warm")) for i, s in enumerate(shots)]
    trans = e.get("transitions") or [{"type": "fade", "dur": 0.4}] * (len(shots) - 1)

    inputs = []
    for p in parts:
        inputs += ["-i", p]
    fc = []
    # xfade chain for video, acrossfade chain for audio
    v, au, t_end = "[0:v]", "[0:a]", float(shots[0]["dur"])
    for i in range(1, len(parts)):
        tr = trans[i - 1]
        td = float(tr.get("dur", 0.4))
        off = t_end - td
        fc.append(f"{v}[{i}:v]xfade=transition={tr.get('type', 'fade')}:duration={td}:offset={off:.3f}[v{i}]")
        fc.append(f"{au}[{i}:a]acrossfade=d={td}[a{i}]")
        v, au = f"[v{i}]", f"[a{i}]"
        t_end = off + float(shots[i]["dur"])
    total = t_end

    k = len(parts)
    post = []
    if e.get("grain", 7):
        post.append(f"noise=alls={e.get('grain', 7)}:allf=t")
    if e.get("vignette", True):
        post.append("vignette=PI/5")
    if e.get("letterbox"):
        lb = int(e["letterbox"])
        post.append(f"drawbox=0:0:{W}:{lb}:black:t=fill,drawbox=0:{H - lb}:{W}:{lb}:black:t=fill")
    fc.append(f"{v}{','.join(post) or 'null'}[g]")
    v = "[g]"

    if e.get("leaks"):
        lp = leak_png(os.path.join(tmp, "leak.png"))
        for j, t0 in enumerate(e["leaks"]):
            st = max(float(t0) - 0.35, 0)
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "0.8", "-i", lp]
            fc.append(f"[{k}:v]format=rgba,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st=0.35:d=0.45:alpha=1,"
                      f"setpts=PTS+{st:.3f}/TB[lk{j}]")
            fc.append(f"{v}[lk{j}]overlay=0:0:eof_action=pass[vl{j}]")
            v = f"[vl{j}]"
            k += 1

    overlays = [(title_png(os.path.join(tmp, f"t{j}.png"), t), t) for j, t in enumerate(e.get("titles", []))]
    if e.get("cta"):
        overlays.append((cta_png(os.path.join(tmp, "cta.png"), e["cta"]), e["cta"]))
    for j, (png, t) in enumerate(overlays):
        at, dur = float(t["at"]), float(t.get("dur", 2.0))
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", png]
        rise = int(t.get("rise", 24))
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st=0:d=0.5:alpha=1,fade=t=out:st={max(dur - 0.45, 0):.2f}:d=0.45:alpha=1,"
                  f"setpts=PTS+{at}/TB[o{j}]")
        # gentle upward drift while fading in
        fc.append(f"{v}[o{j}]overlay=x=0:y='{rise}*max(0,1-(t-{at})/0.6)':eof_action=pass[vo{j}]")
        v = f"[vo{j}]"
        k += 1

    extras = ([dict(src=e["vo"], at=e.get("vo_start", 0), gain=1.0)] if e.get("vo") else []) + e.get("sfx", [])
    gain = e.get("bed_gain", 0.5) if e.get("vo") else 1.0
    fc.append(f"{au}volume={gain}[bed]")
    labels = ["[bed]"]
    for x in extras:
        inputs += ["-i", os.path.join(edl_dir, x["src"])]
        ms = int(float(x.get("at", 0)) * 1000)
        fc.append(f"[{k}:a]aresample=48000,volume={x.get('gain', 1.0)},adelay={ms}|{ms}[x{k}]")
        labels.append(f"[x{k}]")
        k += 1
    fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,"
              f"afade=t=out:st={max(total - 0.6, 0):.2f}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    fc.append(f"{v}fade=t=out:st={max(total - 0.5, 0):.2f}:d=0.5[vout]")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc),
                        "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "slow",
                        "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", "-y", a.out], capture_output=True, text=True, timeout=1800)
    if r.returncode:
        raise RuntimeError(r.stderr[-1500:])
    print(json.dumps(dict(out=a.out, seconds=round(total, 2), shots=len(parts))))


if __name__ == "__main__":
    main()

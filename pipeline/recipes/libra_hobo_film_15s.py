"""Assemble the 15 s 9:16 Libra Hobo film from one Kling clip + the hero still."""
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont

P = "/tmp/claude-0/-home-user-Higgsfield-test/dc62c400-d540-5f8d-8967-810c690f0a81/scratchpad/libra"
SERIF, SANS = f"{P}/fonts/CormorantGaramond.ttf", f"{P}/fonts/Inter.ttf"
W, H, FPS = 1080, 1920, 30
INK, CREAM = (58, 42, 31), (250, 244, 236)


def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    f.set_variation_by_name(weight)
    return f


def text_layer(name, lines, y_frac, cta=None, card=False):
    """Transparent 1080x1920 PNG with centered text lines (font, size, weight, text)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = int(y_frac * H)
    for path, size, weight, txt in lines:
        f = font(path, size, weight)
        tw = d.textlength(txt, font=f)
        if card:
            pad = 34
            d.rounded_rectangle([(W - tw) / 2 - pad, y - 20, (W + tw) / 2 + pad, y + size + 26],
                                radius=(size + 46) / 2, fill=CREAM + (225,))
        d.text(((W - tw) / 2, y), txt, font=f, fill=INK + (255,))
        y += int(size * 1.25)
    if cta:
        f = font(SANS, 34, "SemiBold")
        tw = d.textlength(cta, font=f)
        pw, ph = tw + 80, 82
        px, py = (W - pw) / 2, y + 30
        d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph / 2, fill=INK + (255,))
        a, de = f.getmetrics()
        d.text((px + (pw - tw) / 2, py + (ph - a - de) / 2), cta, font=f, fill=CREAM + (255,))
    path = f"{P}/edit_{name}.png"
    im.save(path)
    return path


# Beats: (clip start, duration, crop box on the 1076x1924 source or None, text)
beats = [
    (0.0, 3.0, (0, 700, 700, 1244), [(SANS, 44, "Medium", "Soft, structured leather.")]),
    (3.0, 3.0, (0, 640, 640, 1138), [(SANS, 44, "Medium", "Two gold side zips.")]),
    (5.0, 3.0, None, [(SERIF, 84, "SemiBold", "Made for every day.")]),
    (7.0, 3.0, None, [(SERIF, 84, "SemiBold", "Meet the Hobo Bag.")]),
]
# Center the macro crops on the bag: seam for beat 1, left zip for beat 2.
beats[0] = (0.0, 3.0, (188, 455, 700, 1244), beats[0][3])
beats[1] = (3.0, 3.0, (60, 820, 620, 1102), beats[1][3])

inputs, filters, labels = [], [], []
for i, (start, dur, crop, lines) in enumerate(beats):
    inputs += ["-ss", str(start), "-t", str(dur), "-i", f"{P}/kling_pro.mp4"]
    v = f"[{2 * i}:v]"
    if crop:
        x, y, cw, ch = crop
        v += f"crop={cw}:{ch}:{x}:{y},"
    else:
        v += ""
    filters.append(f"{v}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,format=yuv420p[b{i}]")
    ov = text_layer(f"b{i}", lines, 0.16, card=bool(crop))
    inputs += ["-loop", "1", "-t", str(dur), "-i", ov]

n = len(beats)
# End card: hero still with a slow push-in, headline + CTA.
inputs += ["-i", f"{P}/hero_916_2k.png"]  # single frame; zoompan makes 90 frames (3 s)
end_ov = text_layer("end", [(SERIF, 88, "SemiBold", "The Luxury Hobo Bag."),
                           (SANS, 38, "Regular", "Soft leather. Gold details.")], 0.15, cta="Shop Now")
inputs += ["-loop", "1", "-t", "3", "-i", end_ov]

parts = []
for i in range(n):
    ovi = 2 * i + 1
    filters.append(f"[{ovi}:v]format=rgba,fade=t=in:st=0.25:d=0.35:alpha=1,fade=t=out:st=2.45:d=0.3:alpha=1[t{i}]")
    filters.append(f"[b{i}][t{i}]overlay=0:0:format=auto[s{i}]")
    parts.append(f"[s{i}]")
still, still_ov = 2 * n, 2 * n + 1
filters.append(f"[{still}:v]scale=2160:-2,crop=2160:3840,zoompan=z='1+0.0006*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s={W}x{H}:fps={FPS},format=yuv420p[bend]")
filters.append(f"[{still_ov}:v]format=rgba,fade=t=in:st=0.1:d=0.4:alpha=1[tend]")
filters.append("[bend][tend]overlay=0:0:format=auto[send]")
parts.append("[send]")
filters.append("".join(parts) + f"concat=n={n + 1}:v=1:a=0,fade=t=out:st=14.6:d=0.4[vout]")

cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
       "-map", "[vout]", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
       "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
       "-movflags", "+faststart", "-r", str(FPS), "-y", f"{P}/out/libra_hobo_film_15s_9x16.mp4"]
subprocess.run(cmd, check=True)
print(json.dumps({"out": f"{P}/out/libra_hobo_film_15s_9x16.mp4"}))

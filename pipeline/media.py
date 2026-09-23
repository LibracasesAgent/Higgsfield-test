#!/usr/bin/env python3
"""Media helpers. Large Drive videos are never downloaded whole: ffmpeg reads
only the seconds it needs over HTTP range requests.

  probe   python3 pipeline/media.py probe <drive_id|url|file>
  clip    python3 pipeline/media.py clip <drive_id> --start 3 --dur 15 --aspect 9:16 --out clip.mp4
  frames  python3 pipeline/media.py frames <drive_id|url|file> --count 4 --outdir /tmp/frames
  image   python3 pipeline/media.py image <drive_id> --out photo.jpg        (images up to 40 MB)
  fetch   python3 pipeline/media.py fetch <https url> --out result.mp4      (e.g. a Higgsfield result)
  put     python3 pipeline/media.py put <file> <presigned upload url>       (Higgsfield media_upload slot)
  mux     python3 pipeline/media.py mux <silent_video> <audio_source> --out final.mp4
"""
import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_library import direct_url  # noqa: E402

DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")


def src(x):
    """Accept a Drive file id, a URL or a local path."""
    if os.path.exists(x) or x.startswith("http"):
        return x
    if DRIVE_ID.match(x):
        return direct_url(x)
    sys.exit(f"Not a file, URL or Drive id: {x}")


def need_ffmpeg():
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        sys.exit("ffmpeg is missing. It is installed by .claude/hooks/session-start.sh; run: apt-get install -y ffmpeg")


def probe(x):
    need_ffmpeg()
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
         "-of", "json", src(x)], capture_output=True, text=True, timeout=120)
    if out.returncode:
        sys.exit(f"ffprobe failed: {out.stderr[-500:]}")
    data = json.loads(out.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return dict(
        duration=float(data.get("format", {}).get("duration", 0) or 0),
        width=video.get("width"), height=video.get("height"),
        has_audio=any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    )


def scale_filter(aspect):
    """Center-crop to the aspect ratio, then scale to a 1080px short side cap."""
    w, h = (int(v) for v in aspect.split(":"))
    return (f"crop='min(iw,ih*{w}/{h})':'min(ih,iw*{h}/{w})',"
            f"scale='if(gt(iw,ih),-2,min(1080,iw))':'if(gt(iw,ih),min(1080,ih),-2)'")


def cmd_clip(a):
    need_ffmpeg()
    if not 4 <= a.dur <= 30:
        sys.exit("--dur must be between 4 and 30 seconds (the product-swap model's limit)")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(a.start), "-i", src(a.source),
           "-t", str(a.dur)]
    if a.aspect:
        cmd += ["-vf", scale_filter(a.aspect)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-y", a.out]
    subprocess.run(cmd, check=True, timeout=900)
    info = probe(a.out)
    info.update(out=a.out, size_mb=round(os.path.getsize(a.out) / 2**20, 1))
    print(json.dumps(info))


def cmd_frames(a):
    need_ffmpeg()
    info = probe(a.source)
    os.makedirs(a.outdir, exist_ok=True)
    dur = info["duration"] or 1
    saved = []
    for n in range(a.count):
        t = dur * (n + 0.5) / a.count
        path = os.path.join(a.outdir, f"frame_{n + 1:02d}_{t:05.1f}s.jpg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src(a.source),
                        "-frames:v", "1", "-vf", "scale='min(720,iw)':-2", "-q:v", "3", "-y", path],
                       check=True, timeout=300)
        saved.append(path)
    print(json.dumps(dict(duration=dur, frames=saved)))


def download(url, out, max_mb):
    with urllib.request.urlopen(url, timeout=120) as r, open(out, "wb") as f:
        total = 0
        while chunk := r.read(1 << 20):
            total += len(chunk)
            if total > max_mb * 2**20:
                f.close()
                os.remove(out)
                sys.exit(f"Refusing to download more than {max_mb} MB. Use 'clip' for videos.")
            f.write(chunk)
    return total


def cmd_image(a):
    n = download(src(a.source), a.out, max_mb=40)
    print(json.dumps(dict(out=a.out, size_mb=round(n / 2**20, 2))))


def cmd_fetch(a):
    n = download(a.url, a.out, max_mb=a.max_mb)
    print(json.dumps(dict(out=a.out, size_mb=round(n / 2**20, 2))))


def cmd_put(a):
    ctype = a.content_type or mimetypes.guess_type(a.file)[0] or "application/octet-stream"
    with open(a.file, "rb") as f:
        req = urllib.request.Request(a.url, data=f.read(), method="PUT", headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=600) as r:
        print(json.dumps(dict(status=r.status, file=a.file, content_type=ctype)))


def cmd_mux(a):
    """Put the source clip's audio under a silent generated video (product-swap renders are silent)."""
    need_ffmpeg()
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src(a.video), "-i", src(a.audio),
                    "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "aac", "-shortest",
                    "-movflags", "+faststart", "-y", a.out], check=True, timeout=600)
    info = probe(a.out)
    info.update(out=a.out)
    print(json.dumps(info))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("source")
    c = sub.add_parser("clip")
    c.add_argument("source")
    c.add_argument("--start", type=float, default=0)
    c.add_argument("--dur", type=float, default=15)
    c.add_argument("--aspect", default="9:16", help="e.g. 9:16, 4:5, 1:1; empty keeps the original")
    c.add_argument("--out", required=True)
    f = sub.add_parser("frames")
    f.add_argument("source")
    f.add_argument("--count", type=int, default=4)
    f.add_argument("--outdir", default="/tmp/creative-run/frames")
    i = sub.add_parser("image")
    i.add_argument("source")
    i.add_argument("--out", required=True)
    g = sub.add_parser("fetch")
    g.add_argument("url")
    g.add_argument("--out", required=True)
    g.add_argument("--max-mb", type=int, default=300)
    u = sub.add_parser("put")
    u.add_argument("file")
    u.add_argument("url")
    u.add_argument("--content-type", default="")
    m = sub.add_parser("mux")
    m.add_argument("video")
    m.add_argument("audio")
    m.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "probe":
        print(json.dumps(probe(a.source)))
    else:
        globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    main()

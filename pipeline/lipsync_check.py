#!/usr/bin/env python3
"""Automatic lip-sync QA for talking-head clips.

Tracks the lips with MediaPipe Face Landmarker, measures mouth opening per frame, and
correlates it with the speech loudness envelope. Reports the best-matching audio/video lag
and a sync score, plus the share of speech frames where the mouth barely moves ("dead lips").

  python3 pipeline/lipsync_check.py clip.mp4 [clip2.mp4 ...] [--start 0 --dur 5] [--sheet out.jpg]

Score = best mouth/loudness correlation for lags between -0.08 s and +0.16 s (the mouth normally
trails the sound by ~1 frame). Longer windows pick up edge artefacts, not real offsets.
Calibration (Sept 2026): Kling 3.0 0.40-0.55, Wan 2.7 driven by TTS ~0.45 but flat (under-articulated),
Veo 3.1 fast negative (mouth closes on loud syllables).
  score >= 0.40 and dead_lips <= 25 %  ->  PASS
Model file: pipeline/cache/models/face_landmarker.task (downloaded from
https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task)
"""
import argparse
import json
import os
import subprocess

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "models", "face_landmarker.task")
UPPER, LOWER, LEFT, RIGHT = 13, 14, 78, 308   # inner-lip landmarks and mouth corners (FaceMesh indices)


def mouth_series(path, start, dur):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL),
                                        running_mode=vision.RunningMode.VIDEO, num_faces=1)
    vals, crops = [], []
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        i = 0
        while True:
            ok, frame = cap.read()
            t = start + i / fps
            if not ok or (dur and t > start + dur):
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(t * 1000))
            if res.face_landmarks:
                p = res.face_landmarks[0]
                h, w = frame.shape[:2]
                width = abs(p[RIGHT].x - p[LEFT].x) * w
                gap = abs(p[LOWER].y - p[UPPER].y) * h
                vals.append(gap / max(width, 1e-6))
                cx, cy = int((p[LEFT].x + p[RIGHT].x) / 2 * w), int((p[UPPER].y + p[LOWER].y) / 2 * h)
                s = int(width * 0.9)
                crops.append(rgb[max(cy - s, 0):cy + s, max(cx - s * 2 // 1, 0):cx + s * 2 // 1])
            else:
                vals.append(np.nan)
                crops.append(None)
            i += 1
    return np.array(vals), fps, crops


def audio_env(path, start, dur, fps, n):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + \
          ["-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.int16).astype(float)
    hop = 16000 / fps
    return np.array([np.sqrt(np.mean(a[int(k * hop):int((k + 1) * hop)] ** 2) + 1e-9) if int((k + 1) * hop) <= len(a)
                     else 0.0 for k in range(n)])


def analyse(path, start=0.0, dur=None, sheet=None):
    m, fps, crops = mouth_series(path, start, dur)
    env = audio_env(path, start, dur, fps, len(m))
    valid = ~np.isnan(m)
    if valid.mean() < 0.6:
        return dict(clip=os.path.basename(path), verdict="FAIL", reason=f"face tracked in only {valid.mean():.0%} of frames")
    m = np.where(valid, m, np.nanmedian(m))
    db = 20 * np.log10(env + 1e-9)
    speech = db > (np.percentile(db, 90) - 18)                     # frames with voice
    mz, ez = (m - m.mean()) / (m.std() + 1e-9), (db - db.mean()) / (db.std() + 1e-9)
    best = (-1, 0)
    for lag in range(-int(round(0.08 * fps)), int(round(0.16 * fps)) + 1):   # +lag = mouth moves after the sound
        a, b = (ez[:len(ez) - lag], mz[lag:]) if lag >= 0 else (ez[-lag:], mz[:len(mz) + lag])
        if len(a) > fps:
            c = float(np.corrcoef(a, b)[0, 1])
            best = max(best, (c, lag))
    closed = np.percentile(m, 10)
    dead = float(np.mean(m[speech] < closed + 0.04)) if speech.any() else 1.0
    score, lag_s = round(best[0], 3), round(best[1] / fps, 3)
    verdict = "PASS" if score >= 0.40 and dead <= 0.25 else "FAIL"
    if sheet:
        from PIL import Image, ImageDraw
        step = max(1, int(fps / 6))
        idx = list(range(0, len(m), step))
        cw, ch = 180, 90
        img = Image.new("RGB", (10 * cw, ((len(idx) + 9) // 10) * (ch + 16)), "white")
        d = ImageDraw.Draw(img)
        for j, k in enumerate(idx):
            x, y = (j % 10) * cw, (j // 10) * (ch + 16)
            if crops[k] is not None and crops[k].size:
                img.paste(Image.fromarray(crops[k]).resize((cw, ch)), (x, y + 16))
            d.text((x + 2, y + 2), f"{start + k / fps:.2f}s {'VOICE' if speech[k] else '-'} {m[k]:.2f}",
                   fill="red" if speech[k] else "black")
        img.save(sheet)
    return dict(clip=os.path.basename(path), score=score, lag_s=lag_s, dead_lips=round(dead, 2), verdict=verdict)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--sheet", help="write a mouth contact sheet (single clip only)")
    a = ap.parse_args()
    for c in a.clips:
        print(json.dumps(analyse(c, a.start, a.dur, a.sheet if len(a.clips) == 1 else None)))


if __name__ == "__main__":
    main()

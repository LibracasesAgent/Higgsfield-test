#!/usr/bin/env python3
"""AI scene stills and short gap-fill clips for the statics and the ugc videos (owner 2026-10-20, 100 credits per batch).

The real product is always the reference: a still is the real bag (a packshot as the reference image) placed into a new
scene (cafe, street, hallway, flat-lay ...); a clip animates an approved still for 3 s. Real photos and real footage stay the
base of every ad (zips, pockets, hands); this adds scenes the client never filmed, so batches stop looking alike.

Higgsfield is reached through the agent's MCP tools, not from Python, so the flow mirrors the voiceovers:
  1. plan (make_batch.py) calls plan_ai(): picks scenes the product has not shown in its last 3 batches (novelty.py), writes
     $OUT/ai_needed.json: the stills (reference photo, prompt, model, ~1 credit each) and the clips (start still, motion prompt,
     model, 4.5-6 credits each), inside the budget (100 - voiceover - a retry reserve).
  2. the agent generates the stills (generate_image_batch, model gpt_image_2_5, medium, 2k), downloads each to its `file`;
  3. `python3 pipeline/ai_gen.py gate --out $OUT`: face check (a worn still is cropped below the chin first), colour and
     sharpness checks, a contact sheet qa/ai_stills.jpg (reference | still) the agent LOOKS AT; `reject AS03 ...` drops any
     that morph the bag or look AI;
  4. the agent generates the clips from the approved stills (generate_video_batch), downloads each to its `file`;
  5. `python3 pipeline/ai_gen.py clips --out $OUT`: conform to 1080x1920 / 30 fps with the real footage's look (grade, grain,
     sharpness), checks (faces, black / frozen frames, drift), a contact sheet qa/ai_clips.jpg to look at; `reject AC02 ...`;
  6. render applies the result (apply(): a rejected or missing still gives its static back as the real-photo static it
     replaced, a rejected or missing clip is swapped for the block's real spare shot): nothing AI that failed ever ships.
Everything an AI asset cost is in $OUT/ai_needed.json (est_credits); the agent reports the balance before and after.

  python3 pipeline/ai_gen.py show --out $OUT       what to generate (compact), with the estimated credits
  python3 pipeline/ai_gen.py gate --out $OUT       steps 3
  python3 pipeline/ai_gen.py clips --out $OUT      step 5
  python3 pipeline/ai_gen.py reject --out $OUT AS03 AC02 ...
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import novelty  # noqa: E402

IMG = dict(model="gpt_image_2_5", params=dict(quality="medium", resolution="2k"), cost=1.0)   # tested 2026-10-20: keeps the bag
CLIP_MODELS = {                      # tested 2026-10-20 on the same two stills (cafe push-in, walking on the street)
    "kling3_0": dict(model="kling3_0", params=dict(mode="std", sound="off", duration=3), cost=4.5, trim=3.0),
    "minimax_hailuo": dict(model="minimax_hailuo", params=dict(variant="minimax-2.3", duration=6, resolution="768"),
                           cost=6.0, trim=3.2)}
RESERVE = 8.0                        # credits kept for a re-generation of an AI asset that fails the gate
STATIC_SHARE = 0.4                   # of a batch's statics at most this share are AI scenes (the rest stay real photos)
MAX_STATICS, MAX_CLIPS = 12, 8
HAAR_NEIGHBORS = 9


def cfg():
    try:
        return json.load(open(os.path.join(HERE, "config.json"))).get("budget") or {}
    except (OSError, ValueError):
        return {}


def library():
    return json.load(open(os.path.join(HERE, "data", "ai_scenes.json")))


def noun_of(name):
    n = (name or "").lower()
    return "backpack" if "backpack" in n else "handbag"


# ------------------------------------------------------------------ planning
def pick_scenes(lib, noun, n, kinds, recent, rng):
    """n scene dicts, kinds cycling through `kinds` (object / worn / hand), each scene once. `recent`: the product's earlier
    scenes, newest first (novelty.recent): a scene never shown comes first, then the one shown longest ago, so every batch
    shows other scenes until the library is used up (22+ scenes, ~16 per batch)."""
    pool = [s for s in lib["scenes"] if noun in (s.get("nouns") or [noun])]
    age = {sid: i for i, sid in enumerate(recent)}                    # 0 = the newest batch's
    out, used = [], set()
    for i in range(n):
        want = kinds[i % len(kinds)]
        cand = [s for s in pool if s["id"] not in used and s["kind"] == want] or [s for s in pool if s["id"] not in used]
        if not cand:
            break
        oldest = max(age.get(s["id"], 10 ** 6) for s in cand)
        s = rng.choice([c for c in cand if age.get(c["id"], 10 ** 6) == oldest])
        used.add(s["id"])
        out.append(s)
    return out


def build_prompt(lib, scene, noun, colour, vertical):
    keep = lib["keep"].format(noun=noun, colour_note=f" ({colour.lower()})" if colour else "")
    face = lib["face"] if scene["kind"] != "object" else ""
    comp = f"Vertical 9:16 composition, the {noun} clearly visible, large in the frame, with space around it." if vertical else \
        f"Portrait 4:5 composition, the {noun} clearly visible and large in the frame."
    return " ".join(x for x in (lib["style"], keep, scene["prompt"].format(noun=noun), face, comp) if x)


def motion_prompt(lib, scene, noun):
    return lib["motion"][scene["kind"]].format(noun=noun)


def clip_model_for(scene):
    return "kling3_0" if scene["kind"] == "object" else "minimax_hailuo"


def plan_ai(*, name, slug, refs, n_statics, n_clips, tts_est, seed, out, grade_refs=(), cap=None, reserve=RESERVE,
            static_layouts=None, log_path=None, boost=0):
    """The AI part of a batch: {"stills": [...], "clips": [...], "est_credits", "budget", "notes"} (also written to
    $OUT/ai_needed.json). refs: [{"file", "colour"}] real packshots (one per colour when the product has them).
    static_layouts: the layouts the AI statics may take (scene / scene_quote / scene_price), in order of use. boost: extra AI
    statics wanted because the real-photo cycle repeats a layout (a product with no reviews / lifestyle photos).
    n_statics / n_clips are the wanted counts; the budget (cap - tts_est - reserve) trims them (clips first)."""
    lib, noun, notes = library(), noun_of(name), []
    rng = random.Random(seed * 7919 + sum(map(ord, slug)))
    cap = float(cap if cap is not None else cfg().get("max_credits_per_batch") or 100)
    budget = max(cap - float(tts_est) - reserve, 0.0)
    refs = [r for r in refs if r.get("file") and os.path.exists(r["file"])]
    if not refs:
        return dict(stills=[], clips=[], est_credits=0.0, budget=dict(cap=cap, tts_est=tts_est, ai_budget=budget),
                    notes=["no packshot to use as the reference image: no AI scenes"])
    want_s = min(MAX_STATICS, int(round(n_statics * STATIC_SHARE)) + max(boost, 0)) if n_statics >= 3 else 0
    n_s = want_s
    n_c = min(MAX_CLIPS, n_clips)

    def cost(ns, nc):                # statics: a 4:5 still each; clips: a 9:16 start still + the clip
        return ns * IMG["cost"] + nc * IMG["cost"] + sum(CLIP_MODELS[clip_model_for(s)]["cost"] for s in kinds_for_clips[:nc])
    avoid_s = novelty.recent(slug, "scene", last=6, log=novelty.load(log_path))        # newest first
    kinds_for_clips = pick_scenes(lib, noun, MAX_CLIPS, ["object", "worn", "object", "hand"], avoid_s, rng)
    while n_c > 0 and cost(n_s, n_c) > budget:
        n_c -= 1
    while n_s > 0 and cost(n_s, n_c) > budget:
        n_s -= 1
    if (n_clips and n_c < n_clips) or n_s < want_s:
        notes.append(f"AI budget {budget:.0f} credits (cap {cap:.0f} - voiceover {tts_est:.0f} - reserve {reserve:.0f}): "
                     f"{n_s} AI statics and {n_c} AI clips instead of the wanted {want_s} / {n_clips}")
    used_refs = novelty.recent(slug, "colour", log=novelty.load(log_path))
    order = sorted(range(len(refs)), key=lambda i: (refs[i].get("colour") in used_refs, i))   # colours not shown lately first

    def ref_for(k):
        return refs[order[k % len(order)]]
    stills, clips = [], []
    s_scenes = pick_scenes(lib, noun, n_s, ["worn", "object", "hand", "object", "worn", "object"], avoid_s, rng)
    layouts = list(static_layouts or ["scene"])
    for k, sc in enumerate(s_scenes):
        r = ref_for(k)
        stills.append(dict(id=f"AS{k + 1:02d}", use="static", scene=sc["id"], kind=sc["kind"], colour=r.get("colour"),
                           layout=layouts[k % len(layouts)], ref=r["file"], aspect="4:5", file=f"ai/AS{k + 1:02d}.png",
                           model=IMG["model"], params=dict(IMG["params"], aspect_ratio="4:5"),
                           prompt=build_prompt(lib, sc, noun, r.get("colour"), False), est_credits=IMG["cost"]))
    avoid_c = [s["scene"] for s in stills] + list(avoid_s)             # (this batch's static scenes count as the newest)
    c_scenes = pick_scenes(lib, noun, n_c, ["object", "worn", "object", "hand"], avoid_c, rng)
    for k, sc in enumerate(c_scenes):
        r = ref_for(k + 3)
        cm = CLIP_MODELS[clip_model_for(sc)]
        sid, cid = f"AV{k + 1:02d}", f"AC{k + 1:02d}"
        stills.append(dict(id=sid, use="clip", scene=sc["id"], kind=sc["kind"], colour=r.get("colour"), ref=r["file"],
                           aspect="9:16", file=f"ai/{sid}.png", model=IMG["model"], params=dict(IMG["params"], aspect_ratio="9:16"),
                           prompt=build_prompt(lib, sc, noun, r.get("colour"), True), est_credits=IMG["cost"]))
        clips.append(dict(id=cid, scene=sc["id"], kind=sc["kind"], tags=sc["tags"], start=sid, file=f"ai/clips/{cid}.mp4",
                          model=cm["model"], params=dict(cm["params"], aspect_ratio="9:16"), trim=cm["trim"],
                          prompt=motion_prompt(lib, sc, noun), est_credits=cm["cost"]))
    est = round(sum(x["est_credits"] for x in stills + clips), 2)
    plan = dict(stills=stills, clips=clips, est_credits=est, notes=notes, grade_refs=list(grade_refs),
                budget=dict(cap=cap, tts_est=round(float(tts_est), 2), reserve=reserve, ai_budget=round(budget, 2)))
    if stills or clips:
        os.makedirs(os.path.join(out, "ai", "clips"), exist_ok=True)
        json.dump(dict(plan, steps=STEPS), open(os.path.join(out, "ai_needed.json"), "w"), indent=1, ensure_ascii=False)
    return plan


STEPS = [
    "1. Upload each distinct `ref` once (media_upload, curl PUT, media_confirm); generate every still with "
    "generate_image_batch (model/params/prompt as listed, medias [{value: media_id, role: image_references}], max 12 per call); "
    "jobs_wait; download each result to $OUT/<file>.",
    "2. python3 pipeline/ai_gen.py gate --out $OUT ; LOOK at $OUT/qa/ai_stills.jpg (reference | still): reject any still where "
    "the bag's shape, colour, handles or hardware differ from the reference, or that looks AI: "
    "python3 pipeline/ai_gen.py reject --out $OUT AS03 ...",
    "3. For every clip whose start still passed: generate_video_batch (start_image = that still's job id, model/params/prompt as "
    "listed); jobs_wait; download to $OUT/<file>. Clips of a rejected still are skipped.",
    "4. python3 pipeline/ai_gen.py clips --out $OUT ; LOOK at $OUT/qa/ai_clips.jpg; reject morphing / odd-hand clips with "
    "`reject`. Then render as usual (it applies the result).",
    "Report: credits before -> after (balance), how many AI assets passed. Never ship a still or clip you would not believe is real."]


def load_needed(out):
    p = os.path.join(out, "ai_needed.json")
    return json.load(open(p)) if os.path.exists(p) else None


def gate_path(out):
    return os.path.join(out, "ai", "gate.json")


def load_gate(out):
    try:
        return json.load(open(gate_path(out)))
    except (OSError, ValueError):
        return {}


def save_gate(out, g):
    os.makedirs(os.path.dirname(gate_path(out)), exist_ok=True)
    json.dump(g, open(gate_path(out), "w"), indent=1, ensure_ascii=False)


# ------------------------------------------------------------------ image checks
def _cv():
    import cv2
    import numpy as np
    return cv2, np


def face_boxes(path, haar_too=False):
    """[(x, y, w, h)] faces in an image: YuNet; haar_too adds the Haar frontal/profile hits (a soft signal only: it also fires on
    hair, linen and leather, and misses a chin with no eyes)."""
    cv2, np = _cv()
    import new_product
    img = cv2.imread(path)
    if img is None:
        return []
    dnn, haar = new_product.detectors()
    boxes = []
    s = 900 / max(img.shape[:2])
    small = cv2.resize(img, None, fx=min(s, 1.0), fy=min(s, 1.0), interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    inv = 1.0 / min(s, 1.0)
    if dnn is not None:
        dnn.setInputSize((w, h))
        f = dnn.detect(small)[1]
        for x in (f if f is not None else []):
            if min(x[2], x[3]) >= 0.02 * min(w, h):
                boxes.append((int(x[0] * inv), int(x[1] * inv), int(x[2] * inv), int(x[3] * inv)))
    if haar_too:
        g = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        m = max(24, int(min(h, w) * 0.06))
        for c in haar or []:   # (minNeighbors 9: the strict 3 of new_product fires on linen, leather and stitching texture)
            for b in c.detectMultiScale(g, scaleFactor=1.1, minNeighbors=HAAR_NEIGHBORS, minSize=(m, m)):
                boxes.append(tuple(int(v * inv) for v in b))
    return boxes


def faces(path, people=True):
    """Faces in an AI picture: the YuNet DNN, the check every static passes again at render (new_product.count_faces). Worn
    scenes are prompted from behind so none shows; what the DNN cannot see (a chin or mouth with no eyes) is caught by the
    agent looking at the contact sheet, and a Haar hit is only a soft flag (gate_still)."""
    import new_product
    return new_product.count_faces(path, strict=False) or 0


def autocrop_face(path, aspect=0.8, keep=0.62):
    """A worn / hand still that shows a face (a chin, a mouth): crop its top edge below the lowest face box (+3% margin), then
    crop the sides back to `aspect` (w/h) around the middle of the picture. True when a clean crop (>= keep of the height,
    no face left) was saved over the file (the original is kept as <name>_orig.png)."""
    from PIL import Image
    boxes = face_boxes(path)
    if not boxes:
        return False
    im = Image.open(path).convert("RGB")
    W, H = im.size
    top = min(H, int(max(b[1] + b[3] for b in boxes) + 0.03 * H))
    if H - top < keep * H:
        return False
    h2 = H - top
    w2 = min(W, int(h2 * aspect))
    x0 = (W - w2) // 2
    crop = im.crop((x0, top, x0 + w2, H))
    orig = os.path.splitext(path)[0] + "_orig.png"
    if not os.path.exists(orig):
        shutil.copy(path, orig)
    crop.save(path)
    return not faces(path)


def bag_ref(path):
    """The reference packshot's bag: its mean colour (Lab) and its crop, found as everything that is not near-white."""
    cv2, np = _cv()
    img = cv2.imread(path)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    m = (g < 232).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    ys, xs = np.where(m > 0)
    if len(xs) < 200:
        return None
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    mean = lab[m > 0].mean(axis=0)
    return dict(lab=mean, crop=img[ys.min():ys.max() + 1, xs.min():xs.max() + 1], area=float(m.mean()))


def colour_share(path, lab, tol=22.0):
    """Share of the picture within `tol` (Lab distance) of the reference bag colour, and the share of its biggest blob."""
    cv2, np = _cv()
    img = cv2.imread(path)
    s = 700 / max(img.shape[:2])
    img = cv2.resize(img, None, fx=min(s, 1.0), fy=min(s, 1.0), interpolation=cv2.INTER_AREA)
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    d = np.sqrt(((L - lab) ** 2).sum(axis=2))
    m = (d < tol).astype(np.uint8)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)))
    big = int(stats[1:, cv2.CC_STAT_AREA].max()) if n > 1 else 0
    return float(m.mean()), big / m.size


def sift_inliers(path, ref_crop):
    """RANSAC inliers of the reference bag's SIFT features in the picture (a soft score: 0-3 = a different bag or a new design)."""
    cv2, np = _cv()
    sift = cv2.SIFT_create(nfeatures=2000)
    kr, dr = sift.detectAndCompute(cv2.cvtColor(ref_crop, cv2.COLOR_BGR2GRAY), None)
    img = cv2.imread(path)
    ks, ds = sift.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
    if dr is None or ds is None or len(kr) < 8 or len(ks) < 8:
        return 0
    good = [m for m, n in (p for p in cv2.BFMatcher().knnMatch(dr, ds, k=2) if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 6:
        return len(good)
    src = np.float32([kr[g.queryIdx].pt for g in good]).reshape(-1, 1, 2)
    dst = np.float32([ks[g.trainIdx].pt for g in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 6.0)
    return int(mask.sum()) if mask is not None else 0


def sharpness(path):
    """Variance of the Laplacian at 900 px (a soft, blurred or smeared picture is low)."""
    cv2, _ = _cv()
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    s = 900 / max(img.shape[:2])
    img = cv2.resize(img, None, fx=min(s, 1.0), fy=min(s, 1.0), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(img, cv2.CV_64F).var())


def gate_still(path, ref_path, kind):
    """{"ok", "problems", "faces", "colour", "inliers", "sharp", "cropped"} of one still. Hard fails: a face (after the crop a
    worn / hand still gets), the bag's colour missing from the picture, a soft picture. A low feature score only says
    "look at it" (the agent's eyes are the real fidelity check)."""
    r = dict(ok=True, problems=[], cropped=False)
    if not os.path.exists(path) or os.path.getsize(path) < 5000:
        return dict(ok=False, problems=["file missing"], cropped=False)
    try:
        n = faces(path, kind != "object")
        if n and kind != "object" and autocrop_face(path):
            r["cropped"], n = True, 0
        r["faces"] = n
        if n:
            r["ok"] = False
            r["problems"].append("face")
        elif kind != "object" and face_boxes(path, haar_too=True):
            r["problems"].append("look: a possible face or head (check the top of the picture)")
        ref = bag_ref(ref_path)
        if ref is not None:
            share, blob = colour_share(path, ref["lab"])
            r["colour"] = round(share, 4)
            r["inliers"] = sift_inliers(path, ref["crop"])
            if blob < 0.004:
                r["ok"] = False
                r["problems"].append("the bag's colour is not in the picture")
            elif r["inliers"] < 6:
                r["problems"].append("look: few features of the real bag found (shape / hardware may differ)")
        r["sharp"] = round(sharpness(path), 1)
        if r["sharp"] < 25:
            r["ok"] = False
            r["problems"].append("too soft")
    except Exception as e:  # noqa: BLE001 - a broken file is a failed still, never a crash of the batch
        return dict(ok=False, problems=[f"check failed: {type(e).__name__}: {e}"], cropped=False)
    return r


# ------------------------------------------------------------------ contact sheets
def sheet(rows, dest, cols=2, tw=300, th=375):
    """rows: [(label, [image paths])] -> a contact sheet (one row of thumbnails + a label line per entry)."""
    from PIL import Image, ImageDraw
    if not rows:
        return None
    per = max(len(r[1]) for r in rows)
    ncol = min(cols, len(rows))
    cw, ch = per * tw + 8, th + 26
    W = Image.new("RGB", (cw * ncol, ch * ((len(rows) + ncol - 1) // ncol)), "white")
    d = ImageDraw.Draw(W)
    for i, (label, ps) in enumerate(rows):
        x0, y0 = (i % ncol) * cw, (i // ncol) * ch
        d.text((x0 + 4, y0 + 4), label[:60], fill=(0, 0, 0))
        for k, p in enumerate(ps):
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((tw, th))
                W.paste(im, (x0 + k * tw + 4, y0 + 22))
            except Exception:  # noqa: BLE001
                d.text((x0 + k * tw + 8, y0 + 40), "unreadable", fill=(200, 0, 0))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    W.save(dest, quality=88)
    return dest


def cmd_gate(out):
    need = load_needed(out)
    if not need:
        sys.exit(f"{out}/ai_needed.json missing: this plan has no AI assets")
    g = load_gate(out)
    g.setdefault("stills", {})
    rows, missing = [], []
    for s in need["stills"]:
        f = os.path.join(out, s["file"])
        if not os.path.exists(f):
            missing.append(s["id"])
            continue
        prev = g["stills"].get(s["id"]) or {}
        r = gate_still(f, s["ref"], s["kind"])
        if prev.get("rejected"):
            r.update(ok=False, rejected=True, problems=r["problems"] + ["rejected by eye"])
        g["stills"][s["id"]] = r
        rows.append((f"{s['id']} {s['scene']} ({s['use']}) {'OK' if r['ok'] else 'FAIL ' + '; '.join(r['problems'])}", [s["ref"], f]))
    save_gate(out, g)
    sh = sheet(rows, os.path.join(out, "qa", "ai_stills.jpg"))
    ok = [k for k, v in g["stills"].items() if v["ok"]]
    print(json.dumps(dict(stills_ok=ok, stills_failed={k: v["problems"] for k, v in g["stills"].items() if not v["ok"]},
                          not_generated=missing, sheet=sh, next="LOOK at the sheet (reference | still); `reject` any that differ "
                          "from the real bag; then generate the clips of the passing 9:16 stills (ai_needed.json steps)"), indent=1))


# ------------------------------------------------------------------ clips
def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,duration",
                        "-of", "json", path], capture_output=True, text=True)
    try:
        s = json.loads(r.stdout)["streams"][0]
        n, d = (s.get("r_frame_rate") or "30/1").split("/")
        return dict(w=int(s["width"]), h=int(s["height"]), fps=float(n) / float(d or 1), dur=float(s.get("duration") or 0))
    except (ValueError, KeyError, IndexError, ZeroDivisionError):
        return None


def grab(path, times, dest_dir, tag):
    ps = []
    os.makedirs(dest_dir, exist_ok=True)
    for i, t in enumerate(times):
        p = os.path.join(dest_dir, f"{tag}_{i}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", p], capture_output=True)
        if os.path.exists(p):
            ps.append(p)
    return ps


def look_stats(paths):
    """(mean saturation 0-1, luma contrast = luma std 0-1) over some frames."""
    cv2, np = _cv()
    s, c = [], []
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            continue
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        s.append(hsv[..., 1].mean() / 255.0)
        c.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).std() / 255.0)
    return (sum(s) / len(s), sum(c) / len(c)) if s else (None, None)


def grade_match(ai_frames, real_clips, tmp):
    """eq saturation / contrast factors that move the AI clip's look towards the product's real footage (clamped to +-18%)."""
    rs, rc = [], []
    for rcl in real_clips[:4]:
        info = ffprobe(rcl) if os.path.exists(rcl) else None
        if info:
            fr = grab(rcl, [info["dur"] * f for f in (0.2, 0.5, 0.8)], tmp, "real")
            s, c = look_stats(fr)
            if s is not None:
                rs.append(s)
                rc.append(c)
    a_s, a_c = look_stats(ai_frames)
    if not rs or a_s is None or not a_s or not a_c:
        return 1.0, 1.0
    clamp = lambda v: max(0.82, min(1.18, v))  # noqa: E731
    return round(clamp(sum(rs) / len(rs) / a_s), 3), round(clamp(sum(rc) / len(rc) / a_c), 3)


def conform(src, dst, trim, sat=1.0, con=1.0):
    """The AI clip as the ugc renderer wants a source: 1080x1920, 30 fps, no sound, `trim` s, a phone-footage look (the
    sharpness a real clip has after its 1080p encode, a little grain so the surface is not plastic-smooth)."""
    vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,"
          f"eq=saturation={sat}:contrast={con},unsharp=5:5:0.45:5:5:0.0,noise=alls=4:allf=t,format=yuv420p")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-t", f"{trim:.2f}", "-an", "-vf", vf, "-c:v", "libx264",
                        "-preset", "medium", "-crf", "17", "-movflags", "+faststart", dst], capture_output=True, text=True)
    return r.returncode == 0 and os.path.exists(dst)


def gate_clip(path, tmp, kind="object"):
    r = dict(ok=True, problems=[])
    info = ffprobe(path)
    if not info or info["dur"] < 1.5:
        return dict(ok=False, problems=["unreadable or too short"])
    fr = grab(path, [0.1, info["dur"] * 0.5, max(info["dur"] - 0.2, 0.2)], tmp, "gate")
    cv2, np = _cv()
    ims = [cv2.imread(p) for p in fr]
    if len(ims) < 3 or any(i is None for i in ims):
        return dict(ok=False, problems=["frames unreadable"])
    luma = [float(cv2.cvtColor(i, cv2.COLOR_BGR2GRAY).mean()) for i in ims]
    if min(luma) < 12:
        r["ok"] = False
        r["problems"].append("black frame")
    d = float(np.abs(cv2.resize(ims[0], (270, 480)).astype(np.float32) - cv2.resize(ims[-1], (270, 480)).astype(np.float32)).mean())
    r["motion"] = round(d, 1)
    if d < 1.2:
        r["ok"] = False
        r["problems"].append("frozen (no motion)")
    if d > 70:
        r["ok"] = False
        r["problems"].append("wild change between first and last frame")
    n = max(faces(p) for p in fr)
    if n:
        r["ok"] = False
        r["problems"].append("face")
    r["faces"] = n
    return r


def cmd_clips(out):
    need = load_needed(out)
    if not need:
        sys.exit(f"{out}/ai_needed.json missing: this plan has no AI assets")
    g = load_gate(out)
    g.setdefault("clips", {})
    tmp = os.path.join(out, "_tmp", "ai")
    real = [p for p in need.get("grade_refs") or [] if os.path.exists(p)]
    rows, missing, skipped = [], [], []
    for c in need["clips"]:
        st = (g.get("stills") or {}).get(c["start"]) or {}
        raw = os.path.join(out, c["file"])
        done = raw[:-4] + "_c.mp4"
        if not st.get("ok"):
            skipped.append(c["id"])
            g["clips"][c["id"]] = dict(ok=False, problems=["its start still did not pass"])
            continue
        if not os.path.exists(raw):
            missing.append(c["id"])
            continue
        was = g["clips"].get(c["id"]) or {}
        sf = grab(raw, [0.1, 1.0, 2.0], tmp, c["id"] + "_ai")
        sat, con = grade_match(sf, real, tmp)
        if not conform(raw, done, c["trim"], sat, con):
            g["clips"][c["id"]] = dict(ok=False, problems=["conform failed"])
            continue
        r = gate_clip(done, tmp, c["kind"])
        r.update(grade=dict(saturation=sat, contrast=con))
        if was.get("rejected"):
            r.update(ok=False, rejected=True, problems=r["problems"] + ["rejected by eye"])
        g["clips"][c["id"]] = r
        info = ffprobe(done) or {"dur": 3}
        rows.append((f"{c['id']} {c['scene']} {'OK' if r['ok'] else 'FAIL ' + '; '.join(r['problems'])}",
                     grab(done, [0.2, info["dur"] * 0.4, info["dur"] * 0.7, info["dur"] - 0.2], os.path.join(out, "qa", "_ai"), c["id"])))
    save_gate(out, g)
    sh = sheet(rows, os.path.join(out, "qa", "ai_clips.jpg"), cols=1, tw=150, th=266)
    print(json.dumps(dict(clips_ok=[k for k, v in g["clips"].items() if v["ok"]],
                          clips_failed={k: v["problems"] for k, v in g["clips"].items() if not v["ok"]},
                          not_generated=missing, skipped=skipped, sheet=sh,
                          next="LOOK at the sheet (4 frames per clip): `reject` a clip where the bag morphs, a hand looks wrong or "
                               "it looks AI; then render"), indent=1))


def cmd_reject(out, ids):
    g = load_gate(out)
    for i in ids:
        sec = "clips" if i.startswith("AC") else "stills"
        e = g.setdefault(sec, {}).setdefault(i, {})
        e.update(ok=False, rejected=True)
        e["problems"] = list(dict.fromkeys((e.get("problems") or []) + ["rejected by eye"]))
        if sec == "stills":       # its clip cannot stand on a rejected start still
            need = load_needed(out) or {}
            for c in need.get("clips") or []:
                if c["start"] == i:
                    g.setdefault("clips", {}).setdefault(c["id"], {}).update(ok=False, problems=["its start still was rejected"])
    save_gate(out, g)
    print(f"rejected: {', '.join(ids)}")


def available(out, kind, i):
    """True when the AI asset passed its gate and its file exists (clips: the conformed copy)."""
    e = (load_gate(out).get(kind) or {}).get(i) or {}
    return bool(e.get("ok"))


def clip_file(out, cid):
    """The conformed clip file of an AI clip (ai/clips/AC01_c.mp4)."""
    return os.path.join("ai", "clips", f"{cid}_c.mp4")


def static_file(out, sid):
    return os.path.join("ai", f"{sid}.png")


CLIP_RE = re.compile(r"(?:^|/)ai/clips/(AC\d+)_c\.mp4$")
PRISTINE = "_ai_before"


def _pristine(out, rel):
    """The plan's own copy of a file (the first apply saves it): every apply starts from it, so a later gate that passes
    more assets brings them back, and a static or shot swapped for a failed asset can be swapped again."""
    src, dst = os.path.join(out, rel), os.path.join(out, PRISTINE, rel)
    if not os.path.exists(dst) and os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    return dst if os.path.exists(dst) else src


def apply(out):
    """Makes the plan match what passed the gate. A scene static whose still failed (or was never made) goes back to the
    real-photo static it replaced (statics.json, and its name in plan.json); an AI clip that failed or is missing is swapped,
    in every spec (the project bodies and their hook versions), for the block's next real spare shot, or dropped.
    Idempotent. Returns {statics_ai, statics_back, clips_ai, clips_swapped, clips_dropped, changed}."""
    need = load_needed(out)
    if not need:
        return None
    g = load_gate(out)
    ok_s = {i for i, v in (g.get("stills") or {}).items() if v.get("ok") and os.path.exists(os.path.join(out, "ai", f"{i}.png"))}
    ok_c = {i for i, v in (g.get("clips") or {}).items() if v.get("ok") and os.path.exists(os.path.join(out, clip_file(out, i)))}
    rep = dict(statics_ai=[], statics_back=[], clips_ai=sorted(ok_c), clips_swapped=0, clips_dropped=0, changed=False)
    # ---- statics
    sp = os.path.join(out, "statics.json")
    if os.path.exists(sp):
        st = json.load(open(_pristine(out, "statics.json")))
        rename = {}
        for k, ad in enumerate(st.get("ads") or []):
            ai, fb = ad.get("ai"), ad.pop("fallback", None)
            if not ai:
                continue
            if ai["id"] in ok_s:
                rep["statics_ai"].append(ad["name"])
                if fb:
                    rename[fb["name"]] = ad["name"]
            elif fb:
                st["ads"][k] = fb
                rep["statics_back"].append(f"{ad['name']} -> {fb['name']}")
                rename[ad["name"]] = fb["name"]
        if json.dumps(st, sort_keys=True) != json.dumps(json.load(open(sp)), sort_keys=True):
            json.dump(st, open(sp, "w"), indent=1)
            rep["changed"] = True
        pp = os.path.join(out, "plan.json")
        plan = json.load(open(pp))
        names = [rename.get(n, n) for n in plan.get("statics") or []]
        if names != plan.get("statics"):
            plan["statics"] = names
            json.dump(plan, open(pp, "w"), indent=1, ensure_ascii=False)
            rep["changed"] = True
    # ---- video specs
    cid = lambda x: (CLIP_RE.search(str(x[0])) or [None, None])[1]  # noqa: E731
    bad = lambda x: bool(cid(x)) and cid(x) not in ok_c  # noqa: E731
    files = [f for f in glob.glob(os.path.join(out, "*.json")) + glob.glob(os.path.join(out, "_before_hooks", "*.json"))
             if os.path.basename(f) not in ("plan.json", "statics.json", "ai_needed.json", "compliance.json", "ad_copy.json",
                                            "tts_needed.json", "tts_said.json")]
    for f in files:
        rel = os.path.relpath(f, out)
        try:
            spec = json.load(open(_pristine(out, rel)))
        except (OSError, ValueError):
            continue
        if not isinstance(spec, dict) or spec.get("mode") != "ugc" or "ai/clips/" not in json.dumps(spec):
            continue
        spare_all = [x for x in spec.get("spare_broll") or [] if not bad(x)]
        for blk in spec.get("blocks") or []:
            if "broll" not in blk:
                continue
            spares = [x for x in blk.get("spare") or [] if not bad(x)]
            used = {(str(x[0]), x[1]) for x in blk["broll"] if not bad(x)}
            new = []
            for x in blk["broll"]:
                if not bad(x):
                    new.append(x)
                    continue
                alt = next((y for y in spares + spare_all if not cid(y) and (str(y[0]), y[1]) not in used), None)
                if alt:
                    used.add((str(alt[0]), alt[1]))
                    new.append(list(alt[:2]) + [x[2] if len(x) > 2 else 1.0] + list(alt[3:]))
                    rep["clips_swapped"] += 1
                else:
                    rep["clips_dropped"] += 1
            blk["broll"], blk["spare"] = new, spares
            if not spares:
                blk.pop("spare", None)
        spec["spare_broll"] = spare_all
        if json.dumps(spec, sort_keys=True) != json.dumps(json.load(open(f)), sort_keys=True):
            json.dump(spec, open(f, "w"), indent=1)
            rep["changed"] = True
    return rep


def summary(out):
    """One dict for the plan / run report: counts, credits, the assets that shipped."""
    need, g = load_needed(out) or {}, load_gate(out)
    return dict(stills=len([s for s in need.get("stills", []) if s["use"] == "static"]), clips=len(need.get("clips", [])),
                est_credits=need.get("est_credits", 0), stills_ok=sorted(k for k, v in (g.get("stills") or {}).items() if v.get("ok")),
                clips_ok=sorted(k for k, v in (g.get("clips") or {}).items() if v.get("ok")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show", "gate", "clips", "reject"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if a.cmd == "gate":
        return cmd_gate(out)
    if a.cmd == "clips":
        return cmd_clips(out)
    if a.cmd == "reject":
        return cmd_reject(out, a.ids)
    need = load_needed(out)
    if not need:
        sys.exit("no ai_needed.json in " + out)
    print(json.dumps(dict(budget=need["budget"], est_credits=need["est_credits"], notes=need.get("notes"),
                          stills=[f"{s['id']} {s['use']} {s['scene']} {s['aspect']} ref={os.path.basename(s['ref'])} ({s.get('colour') or '-'})" for s in need["stills"]],
                          clips=[f"{c['id']} {c['scene']} {c['model']} from {c['start']}" for c in need["clips"]]), indent=1))


if __name__ == "__main__":
    sys.exit(main())

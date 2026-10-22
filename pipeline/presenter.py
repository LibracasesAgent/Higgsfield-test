#!/usr/bin/env python3
"""Presenter videos (owner 2026-10-21: "avatars accepted if there is an actual story that requires actors"): a generated adult host (a
woman, never a customer) says the story to camera and the real footage of the bag cuts in over her voice wherever the words describe
something (storyboard.py: a `talk` block = her take as the picture AND the sound; picks [TALK, 0, 1.0] are her on camera, the other picks
are the library's shots). Nothing is made here: `needed` lists what to generate (the agent does, with Higgsfield), `gate` checks it.

  python3 pipeline/presenter.py needed --out $OUT     # from the planned specs: scene stills + her takes -> $OUT/presenter_needed.json
  python3 pipeline/presenter.py show   --out $OUT     # the same, with the steps
  python3 pipeline/presenter.py gate   --out $OUT     # stills: the real bag + one face; takes: her words vs the script, length, black frames
  python3 pipeline/presenter.py reject --out $OUT PS02 PT05 ...

The model route (tested 2026-10-21, Hobo Bag): one scene still per (project, scene) made with `gpt_image_2_5` from TWO references (the host's
master picture and the real bag's packshot) -> one take per chapter / hook with `kling3_0` (pro, sound on, 9:16, start_image = the scene
still, the line in the prompt: Kling speaks it, lips in sync, ~2.5 credits per second). Same host + same voice description = the takes of one
host sound alike (f0 177-195 Hz over 3 takes in 2 scenes). Seedance 2.5 looks the same at 3.5x the price. Hosts: data/presenters.json.
"""
import argparse
import difflib
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STILL = dict(model="gpt_image_2_5", params=dict(quality="medium", resolution="2k", aspect_ratio="9:16"), cost=1.0)
TAKE = dict(model="kling3_0", params=dict(mode="pro", sound="on", aspect_ratio="9:16"), per_second=2.5)    # pro: 1080p (std is 720p and smooths her face:
#                                                      2026-10-21 test, 25 credits per 10 s vs 20). Skin wording: never ask for "pores / fine lines / unretouched"
#                                                      (owner 2026-10-21: the etched wrinkles and orange skin of that wording looked fake); ask for soft natural phone-photo skin
WPS = 2.7                      # words per second planned for a take's length (Kling fits the line into the clip: 2.4 s/word at 6 s for 12 words,
#                                3.1 at 6 s for 17: a clip that is too short makes her hurry, too long makes her drawl)
MIN_D, MAX_D = 4, 15           # Kling v3.0: 3-15 s whole seconds
CAP = 1000.0                   # credits a presenter batch may plan for stills + takes (the usual 100 is for voiceover + AI scenes)
MATCH = 0.82                   # the least a take's heard words must match the script (difflib ratio)
TAIL_MIN = 0.08                # least silence after her last word (s) before it counts as cut off: Kling often ends the clip right after the last word
TAIL_SOFT = 0.3                # under this a note only: the cut then ends with the clip


class NoPresenter(Exception):
    pass


def hosts():
    return json.load(open(os.path.join(HERE, "data", "presenters.json")))


def canon(w):
    return re.sub(r"[^a-z0-9]", "", (w or "").lower())


_NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten",
        "20": "twenty", "30": "thirty", "40": "forty", "50": "fifty", "60": "sixty", "70": "seventy"}


def norm_words(t):
    """Words of a script or of a transcript on one footing: numerals and '%' spelled out, hyphens and punctuation dropped (a transcript says
    '50 %' where the script says 'fifty percent', 'water -resistant' where it says 'water-resistant')."""
    t = re.sub(r"(\d)\.(\d)", r"\1 \2", (t or "").lower()).replace("%", " percent ").replace("-", "")    # "2.0" = "2" ".0" in a transcript = "two zero"
    ws = []
    for w in t.split():
        w = re.sub(r"[^a-z0-9]", "", w)
        if w:
            ws.append(_NUM.get(w, w))
    return ws


def take_seconds(text):
    return int(min(MAX_D, max(MIN_D, math.ceil(len((text or "").split()) / WPS + 1.0))))


def still_prompt(host, sc, colour):
    """The scene still of the host: her face from reference 1 (the master), the real bag from reference 2 (its packshot)."""
    return (
        "Photorealistic vertical phone-camera video frame, natural light, shot like a real creator's video. Her skin looks like skin in a "
        "normal phone photo: soft, even and natural in tone, matte with a faint shine on the nose, a few light freckles, only gentle "
        "expression lines at the eye corners, a smooth forehead; no heavy skin texture, no exaggerated pores, no etched wrinkles, no orange "
        "or tanned tint, no plastic smoothing. The same woman as in the first reference image: identical face and skin tone, the same dark "
        "brown wavy shoulder-length hair with loose flyaway strands, the same age, freckles and small mole, the same small gold stud earrings. "
        f"{sc.get('outfit') or 'She wears a denim shirt.'} {sc['where'].strip()} She looks straight into the camera as if about to talk to "
        "it, a relaxed half-smile, mouth gently closed. The handbag from the second reference image is "
        f"{sc.get('bag') or 'resting on her lap'}, unchanged: the same {colour or 'brown'} colour, the same shape and proportions, the "
        "same straps, the same gold hardware, the same zips and stitching; do not redesign it and do not add a logo. "
        "Medium close-up framed from the chest up, the bag visible in the lower part of the frame. No text, no watermark.")


def take_prompt(host, sc, text):
    return (
        f"Handheld phone video of the woman talking straight to the camera. She says in {host['voice']}: \"{text.strip()}\" She starts "
        "speaking right away, within the first half second, at an easy natural pace. Her lips move in sync with the words, natural "
        "blinking, small head movements and small hand gestures, a relaxed, ordinary, unperformed expression, not a presenter's grin. "
        f"{sc.get('ambience') or 'Quiet room ambience'}, no music. Her skin stays soft and natural, as in the start image, with no added texture or wrinkles. The camera stays "
        "steady at chest-up framing. The handbag stays exactly as it is.")


def presenter_videos(out):
    """[(plan video entry, spec)] of the plan's presenter projects."""
    p = json.load(open(os.path.join(out, "plan.json")))
    res = []
    for v in p.get("videos") or []:
        if (v.get("ugc") or {}).get("presenter"):
            f = os.path.join(out, v["name"] + ".json")
            if os.path.exists(f):
                res.append((v, json.load(open(f))))
    return p, res


def needed(out, quiet=False):
    """Write $OUT/presenter_needed.json from the planned specs: one scene still per (project, scene), one take per distinct `talk` file
    (a project's 4 versions share their body takes; each hook version has its own). None when the plan has no presenter project."""
    out = os.path.abspath(out)
    p, vids = presenter_videos(out)
    if not vids:
        return None
    hs = hosts()
    host_id = vids[0][0]["ugc"]["presenter"]["id"]
    host = hs[host_id]
    colours = p.get("colour_images") or {}
    scenes, takes = {}, {}
    for v, spec in vids:
        pres = v["ugc"]["presenter"]
        pid = re.sub(r"^.*?_(P\d+)_.*$", r"\1", v["name"])
        by_id = {s["id"]: s for s in pres["scenes"]}
        for b in spec.get("blocks") or []:
            if not b.get("talk"):
                continue
            sid = b.get("scene") or pres["scenes"][0]["id"]
            if sid not in by_id:
                raise SystemExit(f"{v['name']}: block {b['talk']} names scene {sid!r}; the project's scenes are {sorted(by_id)}")
            scenes.setdefault((pid, sid), by_id[sid])
            takes.setdefault(b["talk"], dict(file=b["talk"], text=b["text"], scene=sid, project=pid))
    stills, sid_of = [], {}
    for k, ((pid, sid), sc) in enumerate(sorted(scenes.items()), 1):
        want = {"brown": "sienn", "tan": "sienn"}.get((sc.get("colour") or "brown").lower(), (sc.get("colour") or "brown").lower())
        cname, cfile = next(((n, f) for n, f in colours.items() if want in n.lower()), next(iter(colours.items()), (None, None)))
        if not cfile:
            raise SystemExit("no packshot of the product in plan.json (colour_images): the presenter's bag needs its reference")
        nb = os.path.join(os.path.dirname(cfile), "clean", os.path.splitext(os.path.basename(cfile))[0] + "_nobadge.jpg")
        ref = nb if os.path.exists(nb) else cfile       # (a clean copy of the packshot without the site's sale badge, when there is one)
        sid_of[(pid, sid)] = f"PS{k:02d}"
        stills.append(dict(id=f"PS{k:02d}", project=pid, scene=sid, file=f"talk/PS{k:02d}.png", ref_bag=ref, colour=cname or sc.get("colour"),
                           model=STILL["model"], params=dict(STILL["params"]), prompt=still_prompt(host, sc, sc.get("colour") or "brown"),
                           est_credits=STILL["cost"]))
    tk = []
    for k, (f, t) in enumerate(sorted(takes.items(), key=lambda x: x[0]), 1):
        sc = next(s for (pid, sid), s in scenes.items() if pid == t["project"] and sid == t["scene"])
        d = take_seconds(t["text"])
        tk.append(dict(id=f"PT{k:02d}", file=f, project=t["project"], scene=t["scene"], still=sid_of[(t["project"], t["scene"])], text=t["text"],
                       duration=d, model=TAKE["model"], params=dict(TAKE["params"], duration=d), prompt=take_prompt(host, sc, t["text"]),
                       est_credits=round(d * TAKE["per_second"], 1)))
    est = round(sum(x["est_credits"] for x in stills + tk), 1)
    need = dict(presenter=dict(id=host_id, **{k: host[k] for k in ("name", "look", "voice")},
                               master=os.path.join(HERE, host["master"])),
                stills=stills, takes=tk, est_credits=est, cap=CAP, steps=STEPS)
    os.makedirs(os.path.join(out, "talk"), exist_ok=True)
    json.dump(need, open(os.path.join(out, "presenter_needed.json"), "w"), indent=1, ensure_ascii=False)
    summ = dict(presenter=host_id, stills=len(stills), takes=len(tk), take_seconds=sum(x["duration"] for x in tk), est_credits=est, cap=CAP,
                file=os.path.join(out, "presenter_needed.json"))
    if not quiet:
        print(json.dumps(summ, indent=1))
    return summ


STEPS = [
    "1. Upload the host's master picture (`presenter.master`) and each distinct `ref_bag` once (media_upload, curl PUT, media_confirm).",
    "2. generate_image_batch (max 12 per call): every still with model / params / prompt exactly as listed, medias [{value: <master id>, "
    "role: image_references}, {value: <that still's bag id>, role: image_references}], use_unlim false; jobs_wait; download to $OUT/<file>.",
    "3. python3 pipeline/presenter.py gate --out $OUT ; LOOK at $OUT/qa/presenter_stills.jpg (the bag's packshot | the still): the bag must be "
    "the real bag (shape, colour, strap, hardware), the woman the host (same face), nothing odd in her hands: "
    "python3 pipeline/presenter.py reject --out $OUT PS02 ...  and generate that still again (one retry).",
    "4. generate_video_batch (max 6 per call, then jobs_wait): every take of a passing still with model / params / prompt as listed, "
    "medias [{value: <the still's job id>, role: start_image}], use_unlim false. A submission answered with a preset recommendation: send "
    "it again with declined_preset_id = that preset's id. Download to $OUT/<file> (talk/P01_c1.mp4 ...).",
    "5. python3 pipeline/presenter.py gate --out $OUT ; LOOK at $OUT/qa/presenter_takes.jpg: reject (and make once more) a take whose "
    "words differ from the script, whose lips are off, whose bag changes, whose hands melt. Then render as usual."]


# ------------------------------------------------------------------ checks
def load_needed(out):
    p = os.path.join(out, "presenter_needed.json")
    return json.load(open(p)) if os.path.exists(p) else None


def gate_path(out):
    return os.path.join(out, "talk", "gate.json")


def load_gate(out):
    try:
        return json.load(open(gate_path(out)))
    except (OSError, ValueError):
        return {}


def save_gate(out, g):
    os.makedirs(os.path.dirname(gate_path(out)), exist_ok=True)
    json.dump(g, open(gate_path(out), "w"), indent=1, ensure_ascii=False)


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,duration", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        st = json.loads(r.stdout)["streams"]
    except (ValueError, KeyError):
        return {}
    v = next((s for s in st if s.get("codec_type") == "video"), {})
    return dict(w=v.get("width"), h=v.get("height"), dur=float(v.get("duration") or 0), audio=any(s.get("codec_type") == "audio" for s in st))


def frames(path, times, dest, tag):
    os.makedirs(dest, exist_ok=True)
    res = []
    for i, t in enumerate(times):
        f = os.path.join(dest, f"_{tag}_{i}.jpg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-q:v", "3", "-y", f],
                       capture_output=True)
        if os.path.exists(f):
            res.append(f)
    return res


def gate_still(path, ref_bag):
    import ai_gen
    r = dict(ok=True, problems=[])
    if not os.path.exists(path) or os.path.getsize(path) < 5000:
        return dict(ok=False, problems=["file missing"])
    try:
        n = ai_gen.faces(path)
        r["faces"] = n
        if n != 1:
            r["ok"] = False
            r["problems"].append(f"{n} faces found (the host alone: exactly one)")
        ref = ai_gen.bag_ref(ref_bag)
        if ref is not None:
            share, blob = ai_gen.colour_share(path, ref["lab"])
            r["colour"] = round(share, 4)
            r["inliers"] = ai_gen.sift_inliers(path, ref["crop"])
            if blob < 0.01:
                r["ok"] = False
                r["problems"].append("the bag's colour is not in the picture")
            elif r["inliers"] < 6:
                r["problems"].append("look: few features of the real bag found (shape / hardware may differ)")
        r["sharp"] = round(ai_gen.sharpness(path), 1)
        if r["sharp"] < 25:
            r["ok"] = False
            r["problems"].append("too soft")
    except Exception as e:  # noqa: BLE001 - a broken file is a failed still, never a crash of the batch
        return dict(ok=False, problems=[f"check failed: {type(e).__name__}: {e}"])
    return r


def gate_take(path, text, want_s):
    """{ok, problems, heard, match, first, last, dur} of one take: the words she says against the script, when she starts and how much
    silence follows, the faces on three frames, black frames, and the compliance check of what she actually said."""
    from remix import words
    r = dict(ok=True, problems=[])
    if not os.path.exists(path) or os.path.getsize(path) < 20000:
        return dict(ok=False, problems=["file missing"])
    pr = probe(path)
    if not pr.get("audio"):
        return dict(ok=False, problems=["no sound in the file"])
    r["dur"] = round(pr["dur"], 2)
    ws = words(path)
    heard = " ".join(w["w"] for w in ws)
    r["heard"] = heard
    want_w, heard_w = norm_words(text), norm_words(heard)
    sm = difflib.SequenceMatcher(None, want_w, heard_w, autojunk=False)
    cm = difflib.SequenceMatcher(None, "".join(want_w), "".join(heard_w), autojunk=False)    # (also letter by letter: "Hobo" / "Habo", "US" / "U S")
    r["match"] = round(max(sm.ratio(), cm.ratio()), 2)
    if r["match"] < MATCH:
        r["ok"] = False
        r["problems"].append(f"she says other words (match {r['match']}): {heard[:120]!r}")
    if ws:
        r["first"], r["last"] = round(ws[0]["s"], 2), round(ws[-1]["e"], 2)
        if r["first"] > 1.8:
            r["problems"].append(f"look: she starts late ({r['first']} s; the cut trims it)")
        if pr["dur"] - r["last"] < TAIL_MIN:
            r["ok"] = False
            r["problems"].append(f"her last word ends {pr['dur'] - r['last']:.2f} s before the clip ends (cut off?)")
        elif pr["dur"] - r["last"] < TAIL_SOFT:
            r["problems"].append(f"look: her last word ends {pr['dur'] - r['last']:.2f} s before the clip ends (the cut ends with the clip)")
    else:
        r["ok"] = False
        r["problems"].append("no words heard")
    try:        # the script itself was checked at plan: only words she ADDED (two or more in a row) are checked here
        import compliance
        extra = [" ".join(heard_w[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag in ("insert", "replace") and j2 - j1 >= 2]
        probs = compliance.check(extra) if extra else []
        if probs:
            r["ok"] = False
            r["problems"].append("compliance of the words she added: " + "; ".join(str(x.get("rule") or x) for x in probs)[:200])
    except Exception:  # noqa: BLE001 - a soft extra: the script was checked at plan
        pass
    try:
        import ai_gen
        d = os.path.join(os.path.dirname(path), "_g")
        fs = frames(path, [0.5, pr["dur"] / 2, max(pr["dur"] - 0.6, 0.6)], d, os.path.basename(path)[:-4])
        nf = [ai_gen.faces(f) for f in fs]
        r["faces"] = nf
        if sum(1 for n in nf if n >= 1) < 2:
            r["ok"] = False
            r["problems"].append(f"her face is found on {sum(1 for n in nf if n >= 1)} of 3 frames")
        import cv2
        lum = [float(cv2.imread(f, cv2.IMREAD_GRAYSCALE).mean()) for f in fs]
        if min(lum or [255]) < 18:
            r["ok"] = False
            r["problems"].append("a black frame")
        for f in fs:
            os.remove(f)
    except Exception as e:  # noqa: BLE001
        r["problems"].append(f"look: frame checks skipped ({type(e).__name__})")
    return r


def cmd_gate(out):
    need = load_needed(out)
    if not need:
        sys.exit(f"{out}/presenter_needed.json missing: this plan has no presenter project (presenter.py needed)")
    import ai_gen
    g = load_gate(out)
    g.setdefault("stills", {})
    g.setdefault("takes", {})
    rows, missing = [], []
    for s in need["stills"]:
        f = os.path.join(out, s["file"])
        if not os.path.exists(f):
            missing.append(s["id"])
            continue
        prev = g["stills"].get(s["id"]) or {}
        r = gate_still(f, s["ref_bag"])
        if prev.get("rejected"):
            r.update(ok=False, rejected=True, problems=r["problems"] + ["rejected by eye"])
        g["stills"][s["id"]] = r
        rows.append((f"{s['id']} {s['project']} {s['scene']} {'OK' if r['ok'] else 'FAIL ' + '; '.join(r['problems'])}", [s["ref_bag"], f]))
    trows = []
    for t in need["takes"]:
        f = os.path.join(out, t["file"])
        if not os.path.exists(f):
            missing.append(t["id"])
            continue
        prev = g["takes"].get(t["id"]) or {}
        r = gate_take(f, t["text"], t["duration"])
        if prev.get("rejected"):
            r.update(ok=False, rejected=True, problems=r["problems"] + ["rejected by eye"])
        g["takes"][t["id"]] = r
        d = r.get("dur") or 6
        trows.append((f"{t['id']} {t['project']} {t['scene']} {'OK' if r['ok'] else 'FAIL ' + '; '.join(r['problems'])[:70]} | {t['text'][:60]}",
                      frames(f, [0.15 * d, 0.4 * d, 0.65 * d, 0.9 * d], os.path.join(out, "qa", "_pt"), t["id"])))
    save_gate(out, g)
    sh1 = ai_gen.sheet(rows, os.path.join(out, "qa", "presenter_stills.jpg"), cols=2, tw=300, th=534) if rows else None
    sh2 = ai_gen.sheet(trows, os.path.join(out, "qa", "presenter_takes.jpg"), cols=1, tw=200, th=356) if trows else None
    print(json.dumps(dict(stills_ok=[k for k, v in g["stills"].items() if v["ok"]],
                          stills_failed={k: v["problems"] for k, v in g["stills"].items() if not v["ok"]},
                          takes_ok=len([1 for v in g["takes"].values() if v["ok"]]),
                          takes_failed={k: v["problems"] for k, v in g["takes"].items() if not v["ok"]},
                          not_generated=missing, sheets=[x for x in (sh1, sh2) if x],
                          next="LOOK at the sheets; reject by eye what is off; make failed stills / takes once more (presenter_needed.json steps)"),
                     indent=1))


def cmd_reject(out, ids):
    g = load_gate(out)
    for i in ids:
        kind = "stills" if i.startswith("PS") else "takes"
        g.setdefault(kind, {}).setdefault(i, {}).update(ok=False, rejected=True)
        print(f"{i}: rejected")
    save_gate(out, g)


def not_ready(out, vids):
    """Take files that the given plan video entries need and that are missing, or failed / were rejected in the gate (a render needs every
    one of them: there is no fallback for her voice). [] when all are in."""
    g, need, bad = load_gate(out), load_needed(out) or {}, []
    by_file = {t["file"]: t["id"] for t in need.get("takes") or []}
    for v in vids:
        f = os.path.join(out, v["name"] + ".json")
        if not os.path.exists(f):
            continue
        for b in json.load(open(f)).get("blocks") or []:
            if b.get("talk"):
                st = (g.get("takes") or {}).get(by_file.get(b["talk"]) or "", {})
                if not os.path.exists(os.path.join(out, b["talk"])):
                    bad.append(f"{b['talk']} (missing)")
                elif st.get("rejected") or st.get("ok") is False:
                    bad.append(f"{b['talk']} (failed the gate: {'; '.join(st.get('problems') or ['rejected'])[:80]})")
    return sorted(dict.fromkeys(bad))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("needed", "show", "gate"):
        sub.add_parser(c).add_argument("--out", required=True)
    rj = sub.add_parser("reject")
    rj.add_argument("--out", required=True)
    rj.add_argument("ids", nargs="+")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if a.cmd == "needed":
        if needed(out) is None:
            sys.exit("no presenter project in this plan")
    elif a.cmd == "show":
        n = load_needed(out)
        if not n:
            sys.exit("presenter_needed.json missing: python3 pipeline/presenter.py needed --out $OUT")
        print(json.dumps(n, indent=1, ensure_ascii=False))
    elif a.cmd == "gate":
        cmd_gate(out)
    else:
        cmd_reject(out, a.ids)


if __name__ == "__main__":
    main()

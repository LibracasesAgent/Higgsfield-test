# Handoff — Libra Cases AI ad pipeline (state as of 2026-09-29)

> **Superseded in parts.** The current rules, approvals and recipes are in `docs/PLAYBOOK.md` and `CLAUDE.md`.
> Since this was written the client approved the 50% offer, "anti-theft", the Susan/closing-down story and all
> named reviews; Drive uploads work via `pipeline/drive_upload.py`.

Read this first. It replaces the chat history of the session that built this repo.

## The project
- **Client:** Libra Cases (owner Wouter Spruijtenburg). Sells leather-look **handbags** (Hobo Bag, Hobo 2.0, Vintage/Slouchy), not phone cases.
- **Goal:** a fully automated cloud pipeline (Claude Code Routines, PC off) that reads the weekly n8n Facebook Ads brief (Google Docs in Drive `Ad Creative Pipeline/Research Briefs`, id `15O4eWnDekrabwlp3SFByf0BlgVwqpasG`) plus winning-ad data, and generates ad **statics + videos** with **Higgsfield** (MCP connector, app/UI credits only, no API credits). Target about 40 ads/day with an approval step.
- **Working branch:** `claude/loving-meitner-4amjii`. Never push elsewhere.
- **Higgsfield balance:** 2,706.37 credits on 2026-09-28, minus 2.75 for the Quality v2 start frame (so about 2,703.6). The credit renewal date and amount are unknown and need asking; they decide the daily volume.

## Client feedback so far (most recent last)
1. No human faces in **statics**: product only, hands OK. Statics should look like clean, well-designed Facebook ads.
2. Wants **UGC-style** videos, not studio films. The Kling studio film was "all right, not good".
3. Wants **AI UGC** (AI creator talking to camera) that hooks well.
4. 2026-09-28: **"Yes on all"** to showing the **10 customer reviews with names** (texts in `pipeline/data/reviews.json`).
5. 2026-09-28: **"Not too bad. The quality is definitely too low."** Cause found (below), fix = Quality v2 (in progress).

## What exists (all committed)
- `pipeline/index_library.py` crawls the public client library (`embeddedfolderview`, about 4,100 files / 393 GB) into `pipeline/cache/library.json` (gitignored; re-run to rebuild).
- `pipeline/find_assets.py`, `media.py`, `clip_index.py` (+ `pipeline/data/clip_index.json`, 87 tagged real clips).
- `pipeline/recut.py`: JSON edit list to a 1080×1920 UGC ad. It supports:
  - boxed Montserrat captions and a hook plate (`hook_y`: use about 1060 over a talking face);
  - a voiceover track (`vo`, `vo_start`, `bed_gain`), one-shot sound effects (`sfx`), and still-image segments;
  - Drive-safe clip caching: 1 MB range requests, cached in `pipeline/cache/media/`. Whole-file downloads trigger Drive "Quota exceeded".
- `pipeline/premium.py`: premium product-film editor (xfade transitions, warm grade, grain, vignette, light leaks, animated Cormorant titles, outline CTA, bitrate cap).
- `pipeline/ugc_statics.py`: 1080×1350 statics built from a real/AI photo plus typeset overlays. Element types: caption, postit, marker, circle, arrow, notes, receipt, letters, strip, handwrite (with red ticks), chat (text bubbles), search (search bar), split.
- `pipeline/lipsync_check.py`: lip-sync QA (MediaPipe lip landmarks vs speech loudness).
  - Needs `pip install mediapipe opencv-python-headless faster-whisper numpy`, `apt-get install libegl1 libgles2 libgl1`, and the model file `pipeline/cache/models/face_landmarker.task` (download URL is in the file header).
  - PASS when score ≥ 0.40 and dead_lips ≤ 25 %. It is harsh on P/B/M-heavy lines, so use it as a first filter and still look at the frames.
- `pipeline/typeset_static.py`, `pipeline/drive_upload.py` (OAuth route; env vars never loaded, Drive uploads were dropped for now).
- Recipes: `pipeline/recipes/{stage0,stage1,round2,premium,aiugc}/`. Each has a README with the Higgsfield job ids and costs.
- Skill: `.claude/skills/creative-run/` (routine playbook plus `fb-static-design.md`). **Not yet updated** for the footage-first / AI-UGC flow.
- `.claude/hooks/session-start.sh` installs ffmpeg in cloud sessions.

## Verified Higgsfield prices (credits)
- **Images:**
  - gpt_image_2_5: 2K low 0.5, 2K medium 1.0, **2K high 2.75**, 4K low 0.75.
  - soul_2 portrait 0.12.
  - upscale_image 2K: 2.
- **Budget video:**
  - seedance_2_0_mini: 1/s, 720p only.
  - wan2_7: 5 s 7.5, 1080p 5 s 12.5.
  - kling3_0 std 5 s: 10 (720p).
- **Better video:**
  - **kling3_0 pro 5 s: 12.5** (expected 1080p, unverified).
  - kling3_0 4k 5 s: 30; kling std 15 s: 30.
  - veo3_1 fast 4 s: 16.
  - seedance_2_0 std 1080p 5 s: 45.
  - seedance_2_5: 720p 15 s 105, 1080p 15 s 180.
  - marketing_studio_video 15 s: 75.
- **Audio and edits:**
  - TTS text2speech_v2 elevenlabs: 0.15–0.45 per line.
  - **Voice clone (create_voice_from_confirmed_audio): 40, one-time.** Not preflightable; this caused an overspend once.
  - kling_video_edit std 5 s colour swap: 7.5 (works very well on real clips).
- **Unknown:** upscale_video (Topaz / ByteDance) can't be preflighted, so test once and read `transactions`.
- **Rules:** always pass `use_unlim:false`. When "preset recommended (IN THE DARK)" comes back, resubmit with `declined_preset_id=24bae836-2c4a-48e0-89b6-49fcc0b21612`. Moderation false positives (status nsfw) are refunded.

## Key reference ids (Higgsfield media / job ids)
- **Bag references:**
  - brown front master `50c25f4e-6fe7-4cb3-93a5-c70f7c0cd4a3`
  - brown back `14d0618c-c5e8-47c3-9ef3-8da627cd50d4`
  - black hobo `678c5fc5-db39-46af-94ce-7d37b657c8aa`
  - tan Hobo 2.0 back `6d9f78ce-88e1-46e4-9f32-82f3db286233`
- **Personas (AI, soul_2):**
  - **persona 3 (current choice), young woman, camel trench, hallway: `763e6d59-d404-42de-96d9-e2456bc4aa4c`**
  - persona 2, blonde about 45, kitchen: `3124ce03-6056-485e-aec1-7b32d03cc143`. Its cloned voice element is `435d2b74-4e23-43e7-85c4-fe73c03a00c9` (Kling voice).
  - others: `bb9b05fa…`, `62ea9e50…`
- **Narrator voice (ElevenLabs preset "Maeve"):** `64cf4f1a-61c8-5938-9aea-83d12b2e1d13`.

## Findings that shape the pipeline
1. **Quality ("too low"):**
   - Every AI clip so far is **720p**, stretched to 1080×1920. Kling std is the softest (detail 72, against 171 for the real 4K footage).
   - Start frames used GPT "low" quality, and exports were about 8 Mbps.
   - Fix: kling pro (1080p), GPT image **high**, far more **real 4K library footage**, an upscale pass for leftover 720p shots, a single encode at about 15–20 Mbps, no grain on UGC.
2. **Lip-sync:**
   - Kling 3.0 is best (clear articulation, about 1 frame lag).
   - Wan 2.7 driven by TTS under-articulates and looks "off".
   - Veo 3.1 fast fails (mouth closes on loud syllables).
   - Long single takes (15 s) drift: the bag morphs and sync degrades.
   - **Rule:** face clips ≤ 5 s and lips shown mainly on the hook; let one continuous Kling voice run under real B-roll (J-cut); run `lipsync_check.py`, and re-roll a failing clip for 10.
3. **Real library clips are mostly silent** (7 of 8 checked have no audio track), so real-footage ads need a voiceover or AI foley.
4. **Drive limits:** whole-file or multi-MB range downloads of the shared library hit "Quota exceeded" (it resets within about a day). Only use 1 MB range chunks and cache.
   - Plan: build a one-time **clip bank**, i.e. trimmed approved moments stored outside Drive (GitHub release assets or Higgsfield media).
5. **Legal:**
   - The AI creator is a **presenter/demonstrator only**. Never "I bought / I love it / I've used it" (FTC fake-testimonial rule, UK DMCC, CAP).
   - Label AI ads as AI-generated (EU AI Act Art. 50 from 2 Aug 2026, TikTok AIGC).
   - Real reviews are OK only verbatim and attributed.
   - Claims allowlist: visible features only. Say "leather-look" unless the client confirms leather. No "anti-theft", "50% off", Susan, or closing-down claims without approval.

## In progress: "Quality v2" test (user approved, cap 45 credits)
- Done:
  - Start frame (gpt_image_2_5 2K **high**, persona 3 holding the bag, back pocket to camera), job `15f1597c-7157-475e-a3e8-bdac7241b197` (2.75 spent; result not yet downloaded or checked).
  - Drive range reads confirmed working again.
- Interrupted: pre-caching the 4K hero clips. The user stopped that tool call, so ask before re-running it. The clips are:
  - `1ftNQdXFnvgYmcLhN12OdbC0R3YQur16X` (side-zip keys macro)
  - `1BidTuA7vhnKJ0W923VLBYlXX0LIIueg5` (back-zip macro)
  - `1nnsvEIfgqziYdrmeUrrtgL3Qo3YHV7Sw` (metal details)
  - `1CcakagPN5oiWEneKORpvJblnPYnQvWHI` (details macro)
  - `1Mtx32enLMlOkpIfl_Cr1EYezTdody3E1` (café chair)
  - `1U7B7nHcDvGaoiw5E_jTKSQ3D7oTBrq60` (café table)
  - Already cached from an earlier session (in `pipeline/cache/media/`, gitignored, only if the container still exists): `1pwD5FXA8_dLwraTdrWKc0HJ8tZzzDD06` (back pocket, 4K) and `1JIEAwHHQq-euKPoS9A91KQSmMEGg7EPj` (keys, 1080p).
- Remaining plan:
  1. **One 10 s kling3_0 pro take** (25 credits) from the high-quality frame, speaking the whole script so the voice stays identical: "POV: your bag has a pocket nobody checks. It's on the back, right against you. Keys? Gold side zip. It's the Hobo Bag, link's below." Show her face only on the hook and the final smile; real 4K B-roll covers the middle.
  2. Test `upscale_video` once on the old 720p Kling clip `7a412954-dd10-4d82-a6bc-821c2e43d7dd` to learn its price and result.
  3. Export at a higher bitrate: raise recut.py's final encode to about CRF 16 with maxrate 15–20M and intermediate segments to about CRF 14. Keep files under 30 MB so they can be sent in chat.
  4. **10 review statics** (free) from `pipeline/data/reviews.json`, re-typeset verbatim (the screenshots are too small to use directly), plus one review video with cards over real footage.
  5. Report spend, send files, commit.

## Open questions for the client
- The Higgsfield credit renewal date and amount.
- Footage usage rights.
- Leather or faux leather.
- The free-gift offer (review 1).
- Whether review 4 (slouchy bag) can go in Hobo ads.
- Whether the black Hobo shape in the AI shots matches the real product.
- Music: add a licensed track in Meta Ads Manager. Higgsfield can't make standalone music.

## Stage 2 (after the tests): make it daily
- Update the creative-run skill for the footage-first + AI-UGC + premium mix.
- Build the clip bank.
- Switch config statics to gpt_image_2_5.
- Create the Routine.
- Suggested daily mix: about 4 AI-UGC, 16 recut/POV, 2–3 premium films, 20 statics. That's about 175–250 credits a day at the new quality level, so confirm the budget first.

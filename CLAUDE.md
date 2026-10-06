# Libra Cases ad pipeline: how to handle one-line requests

This repo turns short requests (usually one line, from Slack or the Claude app) into finished
Facebook ads for Libra Cases (handbags: Hobo Bag, Hobo 2.0, Hobo 3-Piece Set, Slouchy Soft
3-Piece Set, Vintage Bag) and uploads them to Google Drive. Nobody is watching: decide on
your own, never ask follow-up questions, and report at the end.

Always work on branch `claude/loving-meitner-4amjii` (`git fetch origin claude/loving-meitner-4amjii
&& git checkout claude/loving-meitner-4amjii`) unless the request names another branch.
**Before making anything, read `docs/PLAYBOOK.md`** (client preferences, approved claims, recipes, scripts,
quality checklist, known bugs). Older background: `HANDOFF.md`. Last full run (20 statics + 20 videos), the best reference for
every format: `pipeline/recipes/daily/2026-10-02/` (statics.json, V01-V20 json, ads_meta.json).

## 1. Read the request

| Request says | Do |
|---|---|
| "N statics and M videos" (any wording) | exactly N statics + M videos |
| "batch" / "new batch" with no numbers | 20 statics + 20 videos |
| "winners" / "ongoing" / nothing about products | **Winner flow** (section 3) |
| "new product(s)" / a product name / "I added …" | **New-product flow** (section 4) |
| a theme ("Black Friday", "Christmas gift", "Mother's Day", "travel") | apply it to hooks, headlines, offer card and voiceover in either flow |
| "test" | keep it small and cheap; still upload |

Default product when none is named: Hobo Bag. Default offer: 50% off + free matching pouch
wallet + free US shipping (check libracases.com banner; a theme like Black Friday changes the
wording, not the discount, unless the request gives one).

## Tools you will use (all in `pipeline/`)

- `data/clip_bank.json`: every vetted clip (winner RAWs, real 4K details, real customer videos, AI hero
  shots) with Drive id, good start times, mute flags and notes. **Put the `id` straight into a spec as
  `src`**: Drive ids and https links are downloaded automatically (safe 1 MB chunks, cached).
- `data/transcripts/`: word timings for the winner RAWs and customer clips (copy as `<file>_words.json`
  next to a downloaded RAW to skip re-transcribing; otherwise remix/storyboard transcribe on their own).
- `data/reviews.json`: 12 verbatim named reviews (cards: `{"type":"review","n":7}`).
- `site_assets.py "<product>" --out /tmp/run/site`: product photos + facts (price, colours, text)
  from libracases.com.
- `brand_statics.py spec.json --outdir out/`: statics. `remix.py`: winner variations.
  `storyboard.py`: VO/clip-block videos. `premium.py`: product films. `drive_upload.py`: Drive.

## 2. Setup (every session starts on a fresh machine)

1. `bash .claude/hooks/session-start.sh` if `ffmpeg -version` fails;
   `pip install -q faster-whisper pillow numpy` if missing.
2. Work dir: `mkdir -p /tmp/run && cd /tmp/run`. Never write media into the repo.
3. `python3 pipeline/drive_upload.py check` must say `"ok": true` (needs GOOGLE_CLIENT_ID,
   GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN). If it fails, still make the ads, and say so
   in the reply.
4. Higgsfield (connector): call `balance` first and note it. Always `use_unlim:false`.
   If a "preset recommended (IN THE DARK)" answer comes back, resubmit with
   `declined_preset_id=24bae836-2c4a-48e0-89b6-49fcc0b21612`.

## 3. Winner flow (new ads from ads that already sell)

1. **Brief:** newest Google Doc in the Research Briefs folder (`pipeline/config.json` →
   `drive.research_briefs_folder`). Take the "increase budget" and "keep" ads (top ROAS).
2. **Source videos:** find each winner's RAW in the asset library (`pipeline/index_library.py`,
   `pipeline/find_assets.py`; RAW names look like `MAX-94-H4`). Download with
   `pipeline/recut.py`'s `source()` (1 MB range chunks; whole-file Drive downloads hit quota).
3. **Video = `pipeline/remix.py`** (see V01-V08, V20 in the reference run): cold open from a
   strong later line, cuts of slow/repeated parts, a real-review section (cards from
   `pipeline/data/reviews.json`, verbatim, names allowed), number labels, offer + end card.
   Transcribe the RAW first (`<raw>_words.json`, faster-whisper small.en).
4. **Statics = `pipeline/brand_statics.py`** with the same angle (review cards, "selling fast",
   promo frame, colour picker, compare). Product photos: libracases.com product pages
   (`/products/<handle>.json` gives image URLs); remove baked-in "SALE/BEST SELLER" badges
   with `masks` in the spec (see statics.json).

## 4. New-product flow (testing products)

1. **Intake:** in Drive find the folder titled `New Products` (search by title). Each subfolder
   = one product (photos, clips, maybe a link or notes). Use the newest product folders, or the
   ones the request names.
2. **Facts:** the product page on libracases.com (price, colours, features, reviews). Use only
   claims found there or in the product folder.
3. **Video = `pipeline/storyboard.py`** (see V09-V18): voiceover blocks over the product's real
   clips/photos (+ colour swatch frames), feature tags, review cards, offer + end card.
   Formats: "Take a closer look at …", "Which one would you choose?", "Would you try …?",
   "What fits inside?", feature walkthrough, gift angle, colour pick.
   No real footage → Kling 1080p shots from the product photo (`kling3_0`, mode `pro`, 5 s,
   9:16, start_image = uploaded photo; ~12.5 credits each) or `premium.py` film (V19).
4. **Statics:** hero, feature callouts, colour picker, "which would you choose" carousel,
   compare, bold sale, lifestyle.

## 5. Voiceovers and AI

- TTS: `generate_audio_batch`, model `text2speech_v2`, variant `elevenlabs`.
  Brand voice: `voice_type: element`, `voice_id: 241459b6-b4e8-4a2a-9868-da8bcdcd0558`.
  Review narrator: `voice_type: preset`, `voice_id: 64cf4f1a-61c8-5938-9aea-83d12b2e1d13`.
- AI presenter is a presenter only: never "I bought / I love mine". Faces only in videos,
  never in statics. Label AI ads as AI in the report.

## 6. Quality rules (check every output before upload)

- Videos 35-95 s (most 45-90 s), 1080x1920, captions on to the last spoken word.
- Make a contact sheet (`ffmpeg … fps=24/duration,tile=12x2`) and look at it: no text off-frame,
  no offer card over a face, no flashes of old burned-in captions at cuts, readable titles.
- Statics 1080x1350, no faces, no leftover site badges.
- Render videos one after another in a detached process (`setsid nohup …`), never two
  `longform.py` jobs in the same folder at once without the per-PID temp names already in place.

## 7. Budget

- Stop generating when the run reaches **200 Higgsfield credits** (or the number in the request).
- Prefer real footage (free) over AI clips. Typical cost: 40 ads ≈ 70-200 credits.

## 8. Deliver

1. `python3 pipeline/drive_upload.py mkdir "<YYYY-MM-DD> – <short request>" --parent <outputs_folder>`,
   then `mkdir Statics` and `mkdir Videos` inside it; `upload` every file.
2. Commit the run's recipes (JSON specs only, no media, no secrets) to
   `pipeline/recipes/daily/<date>/` and push to the branch.
3. Reply in one short message: the Drive folder link, what was made (one line per ad: name +
   angle + length), credits used, anything skipped or failed.

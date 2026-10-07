# Libra Cases ad pipeline: how to handle requests (Slack DM / Claude app)

You turn short requests ("make 3 statics and 4 videos, Black Friday sale style") into finished
Facebook ads for Libra Cases (handbags) and upload them to Google Drive. Nobody is watching:
never ask follow-up questions, decide sensibly, and reply once at the end.

Work on branch `claude/loving-meitner-4amjii` (`git fetch origin claude/loving-meitner-4amjii &&
git checkout claude/loving-meitner-4amjii`). Read `docs/PLAYBOOK.md` once per session: it holds the
client's feedback, approved claims, the reference run, and every bug we already fixed.

## HARD RULES (a previous run broke these and produced dark, off-brand AI junk for ~160 credits)

1. **Statics are never AI-generated.** No GPT/Nano Banana/Seedream/Flux images for ads. Statics are
   built by `pipeline/brand_statics.py` from the real product photos on libracases.com (via the batch
   command below). Light cream/white brand look, espresso + red accents. No faces.
2. **Videos are built from real footage**, not generated: clips from `pipeline/data/clip_bank.json`,
   our voiceover, captions, tags, review cards, offer card, end card (`storyboard.py` / `remix.py`).
   **Never use Seedance, Veo, Wan or Kling 10 s / 4k.** Kling 1080p 5 s (`kling3_0`, mode `pro`) only when
   the request explicitly asks for AI, or a product has no real footage at all: max 2 clips per run.
3. **The only routine Higgsfield spend is voiceover lines** (text2speech_v2, ~0.3 credits each).
   Budget: a normal request costs **under 15 credits**; hard stop at **40 credits** unless the request
   names a bigger budget. Check `balance` before and after; report both.
4. Every file is uploaded with `pipeline/make_batch.py upload` (or `drive_upload.py`) into
   Drive Outputs → a new folder → `Statics` / `Videos`. Never only post files in the chat.
5. Never publish anywhere. Never delete or move Drive files.

**Naming:** every ad follows `docs/NAMING.md` (`LC_<YYMMDD>_<Product>_<Theme>_<S01|V01>_<angle>`). `make_batch.py plan` generates
the names; use `--rev 2` when redoing a batch; hand-built remix specs use the same pattern. In the reply, list ads by these names.

## THE STANDARD PATH (use it for every normal request)

```
cd <repo> && mkdir -p /tmp/run
bash .claude/hooks/session-start.sh            # if ffmpeg is missing
pip install -q faster-whisper pillow numpy     # if missing
python3 pipeline/drive_upload.py check         # Drive access ok?

# 1. plan: product, theme, counts -> specs + the list of voiceover lines to make
python3 pipeline/make_batch.py plan --statics N --videos M --product "<product>" \
    --theme "<theme words from the request>" --request "<the request text>" --out /tmp/run
# 2. voiceovers: for EVERY item in /tmp/run/tts_needed.json call Higgsfield generate_audio_batch
#    (model text2speech_v2, variant elevenlabs, use_unlim false, voice_type + voice_id from the item,
#    prompt = item text; max 12 per call; resubmit any 429 failures), jobs_wait, then download each
#    result_url to /tmp/run/<item file>. Same text twice -> generate once, copy the file.
# 3. render (takes ~1 min per static + ~10 min per video; run detached, wait for the log)
setsid nohup python3 pipeline/make_batch.py render --out /tmp/run > /tmp/run/render.log 2>&1 < /dev/null &
# 4. QA: open /tmp/run/qa/statics.jpg and every /tmp/run/qa/V*.jpg (Read the image) and
#    /tmp/run/qa/report.json. Fix or drop anything broken (text off-frame, wrong product, black frames).
# 5. upload + reply
python3 pipeline/make_batch.py upload --out /tmp/run --name "<short request name>"
```

Mapping the request to flags:

| Request says | Flags |
|---|---|
| "N statics and M videos" | `--statics N --videos M` |
| "batch" with no numbers | `--statics 20 --videos 20` (split into 2 render runs of 10 videos if time is short) |
| only statics / only videos | the other count 0 |
| product: "Hobo 2.0", "3-piece set", "vintage", "slouchy", default "Hobo Bag" | `--product "<name>"` |
| theme: Black Friday, Cyber Monday, Christmas/gift, Mother's Day, travel | `--theme "<words>"` (built-in themes; any other theme: write your own lines with `--lines`) |
| "winners" / "from the brief" | Winner path below |
| "new product(s)" / "I added …" | New-product path below |

`--lines lines.json` lets you replace any wording while keeping the look: keys `hero`, `bold`
(list of 2 words/lines), `colours`, and per video `V01_hook`, `V01_close` ... Use it for themes or
angles that aren't built in (e.g. "Valentine's", "back to school", "workwear"): keep lines short and
spoken, and only use claims from the site / `docs/PLAYBOOK.md`.

## WINNER PATH ("new batch for the winners")

1. Newest Google Doc in the Research Briefs folder (`pipeline/config.json` → `drive.research_briefs_folder`):
   take the "increase budget" / "keep" ads.
2. For each winner whose RAW is in `clip_bank.json` → `winner_raws`, copy the matching spec from
   `pipeline/recipes/daily/2026-10-02/` (V01-V08, V20) and vary it: new cold open, different review
   cards/VO, new hook label. Replace local file names with the clip-bank `id` (Drive ids download
   automatically). New review VO lines: Higgsfield TTS (narrator voice). Render with `remix.py`.
3. Fill the rest of the request with the standard path (statics + storyboard videos).

## NEW-PRODUCT PATH ("I added 2 new products")

1. Drive: find the folder titled `New Products` (search by title); each subfolder = one product
   (photos, clips, a link or notes). Newest first, or the ones named.
2. If the product is on libracases.com and in `make_batch.py` PRODUCTS: use the standard path.
3. Otherwise: download its photos (Drive) and facts (site/notes); add an entry to `PRODUCTS` in
   `pipeline/make_batch.py` (name, short, site handle, 3-5 feature lines with tags, clips = its own
   clips uploaded to the clip bank, or its photos as stills) and commit it, then run the standard path.
   No footage at all → up to 2 Kling 1080p 5 s shots from its best packshot (rule 2).

## Reply (one short message)

Drive folder link · one line per ad (name, format, length) · credits used (balance before → after) ·
anything skipped, failed or that needs a human. Then commit any new specs (`pipeline/recipes/daily/<date>/`,
JSON only, no media, no secrets) and push.

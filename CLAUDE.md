# Libra Cases ad pipeline: how to handle requests (Slack / Claude app)

You turn one-line requests ("make 3 statics and 4 videos, Black Friday", "new batch for the winners",
"new product Silhouette Bag: 6 statics 2 videos") into finished Facebook ads for Libra Cases (handbags)
and upload them to Google Drive. Every batch starts from a message: there is no daily automatic run.
Nobody is watching: never ask follow-up questions, decide sensibly, and reply once at the end.

The repo's default branch is `claude/loving-meitner-4amjii`. Read `docs/PLAYBOOK.md` once per session
(client feedback, approved claims, recipes, every bug already fixed).

## HARD RULES

1. **No AI images, no AI video.** Higgsfield's image and video generators are blocked for this project
   (`.claude/settings.json` and the connector settings): don't call them, don't look for a way around it.
   Statics come from real product photos, videos from real footage, both through `make_batch.py`.
2. **The only Higgsfield calls:** `generate_audio_batch` (text2speech_v2) for the lines in
   `tts_needed.json`, `jobs_wait`, `balance`, `transactions`. A normal request costs under 15 credits;
   `plan` refuses more than 40 unless you pass `--budget X`, which you only do when the request names a
   bigger budget. Check `balance` before and after; report both.
3. **Only true claims.** Offers, gifts and reviews come from the product data (`make_batch.py` handles
   it). Any line you write yourself (`--lines`, product files) uses only facts from libracases.com, the
   client's notes or `docs/PLAYBOOK.md` §1. No faces in statics.
4. Upload everything with `make_batch.py upload` (Drive Outputs → `<date> – <name>` → `Statics` /
   `Videos` + a run report). Never only post files in the chat.
5. Never publish anywhere. Never delete or move Drive files.

**Videos come in projects** (the client's agency format): one project = one video body in 4 versions
H1-H4 that differ only in the hook (opening line, opening shot, on-screen label). `plan` does this by
default (`--hooks 4`); a request for N videos means N projects (4N video files). File names are automatic
(`docs/NAMING.md`: `LC_<YYMMDD>_<Product>_<Theme>_S01_<layout>` / `..._P01_H1_<angle>`); list ads by these
names in the reply.

## 0. Setup (fresh container, about a minute)

```
cd <repo>
command -v ffmpeg || bash .claude/hooks/session-start.sh        # Slack sessions don't run hooks
python3 -c "import faster_whisper, PIL, numpy, cv2" 2>/dev/null || \
    pip install -q faster-whisper pillow numpy pillow-heif opencv-python-headless
python3 pipeline/drive_upload.py check                          # Drive login ok?
```

## 1. Request → plan command

| Request says | `make_batch.py plan` flags |
|---|---|
| "N statics and M videos" (or "M projects") | `--statics N --videos M` → M projects × 4 hook versions |
| "single videos" / "no hook versions" | add `--hooks 1` (V01, V02 … as before) |
| a product | `--product "<name>"`: Hobo Bag (default), Hobo 2.0, 3-piece set, vintage, slouchy, or any product file in `pipeline/data/products/` |
| a theme | `--theme "<words>"`: black friday, cyber monday, christmas, gift, mother's day, travel are built in; any other theme: `--theme "<words>"` plus your own short lines with `--lines` (keys `hero`, `bold`, `colours`, `P01_hook` / `V01_hook`, `P01_close` …) |
| "winners" / "from the brief" / "new versions of our best ads" | `--winner-videos W` = W winner projects, one per winner in brief order, each holding that winner's cold-open hooks (2-4) (+ `--statics S` / `--videos M` if asked). No numbers: `--winner-videos 3 --statics 4` |
| specific winners ("versions of 94-H4 and 148-H5") | `--winner-videos 2 --winners "94-H4,148-H5"`: one project per winner (a winner never gets a second project with the same openings; plan warns what it left out) |
| "new product …" / "I added a product" | section 3 first, then `--product "<key>"` |
| "batch" with no numbers | `--statics 20 --videos 5` (5 projects = 20 videos) |
| "redo project 2" (in the thread) | same plan flags with `--seed <N+1> --only P02` into a new `--out` (only P02 is voiced, rendered, uploaded; names move to `_v2` by themselves) |
| "another hook for P02 H3" | same plan flags with `--hook-seed <N+1> --only P02H3` (same body, a new hook; exits 2 if no unused hook is left: say so) |

`plan` exits 2 with a clear message when something is wrong (unknown product → section 3, draft product
file, too many credits, a sale theme for a product without a deal). Read it and act on it.

## 2. The run (every request)

```
OUT=/tmp/run/<short-name>; mkdir -p $OUT
python3 pipeline/make_batch.py plan <flags> --request "<the request text>" --out $OUT
```
1. Read the plan output and every warning: product, theme, `offer` (read from libracases.com), brief
   (name, age, `stale`), winners used, `unmatched` winners, `est_credits`, length warnings, `names`.
   Higgsfield `balance` → note it.
2. **Voiceovers:** for every item in `$OUT/tts_needed.json` call `generate_audio_batch` (model
   `text2speech_v2`, variant `elevenlabs`, `use_unlim: false`, `voice_type` + `voice_id` from the item,
   prompt = item `text`; max 12 per call; resubmit any that fail with 429), `jobs_wait`, then download each
   result url to `$OUT/<item file>` (`curl -sSL -o`). Identical lines are listed once; render copies them.
3. **Render** (about 1 min per static, about 20 min per project of 4 versions, 2 videos at a time), detached:
   `setsid nohup python3 pipeline/make_batch.py render --out $OUT > $OUT/render.log 2>&1 < /dev/null &`
   then check the log every couple of minutes until it prints `QA:`. More than 3 projects: render and
   upload the statics first (`render --only S`, `upload --only S`), then the videos (`render --only V`,
   `upload --only V`). Use a fresh `$OUT` for every request.
4. **QA:** Read `$OUT/qa/statics.jpg`, every `$OUT/qa/P*.jpg` (one per project: the 4 hooks side by side
   + the body + a 'body vs H1' number per version: under 10 = same body) and `$OUT/qa/report.json`. Text off-frame, wrong product, black frames, a face: fix a hook in
   its `..._P01_H3_...json`, a body problem in `$OUT/_before_hooks/<V01 spec>.json` then re-run
   `python3 pipeline/projects.py expand --out $OUT` (all 4 versions get it), and `render --only <id>`; or
   leave it out and say so. A face in a static or a failed render is never uploaded; length/anchor flags
   are uploaded and listed in the run report: mention them in the reply.
5. **Upload:** `python3 pipeline/make_batch.py upload --out $OUT --name "<short request name>"` → prints the
   Drive folder link and the uploaded ads. Higgsfield `balance` again.
6. **Reply** (one short message): Drive folder link · statics one line each · videos one block per project
   ("P01 – <angle>" + winner and ROAS, then per version: H#, label, spoken line, length) · plan warnings
   (fewer than 4 versions, openings already used in an earlier batch) · credits used
   (balance before → after) · brief used and if it is stale · winners skipped (unmatched) and why ·
   anything else skipped, failed or needing a human.
7. Commit the specs (JSON only, no media, no secrets):
   `python3 pipeline/make_batch.py specs --out $OUT --to pipeline/recipes/daily/<YYYY-MM-DD>/<short-name>`,
   plus any new or changed product file; commit, push.

## 3. New products

The client puts one folder per product in Drive `Ad Creative Pipeline / New Products` (photos, clips, a
note with the site link, offer, colours and features).
```
python3 pipeline/new_product.py list                       # folders, newest first, and which are done
python3 pipeline/new_product.py intake "<folder name>"     # or --latest, or --site <libracases.com url|handle>
```
1. Read the printed summary, `overview.jpg` and the clip sheets it names.
2. Edit `pipeline/data/products/<slug>.json`: 3-5 `features` (one short spoken sentence each + a 2-3 word
   uppercase TAG + picks of the clips/photos that show it), only true claims from `facts` (site / notes).
   Check the `offer` block against the site and notes (never invent a % or a free gift). Keep
   `reviews: []`. Set `"status": "ready"`. Schema: `pipeline/data/products/README.md`.
3. `python3 pipeline/new_product.py check <slug>` must report ok. Then section 2 with `--product "<key>"`.
4. A product that is on the site but unknown to `plan` ("unknown product"): `intake --site <name or url>`.
   No photos, no clips and not on the site: make nothing and say what is needed.

## 4. Winners

`--winner-videos` reads the newest brief in Drive `Research Briefs` (the n8n weekly report), takes the
"increase budget" and "keep" ads and matches them to the winning RAW videos in `clip_bank.json`
(`winner_raws`, with cold opens, cuts, review insert points). Each video re-edits a RAW with another
cold open, a narrated review section and the theme's offer card (`remix.py`).
- `stale: true` (brief older than 8 days): still run it, and say so in the reply.
- `unmatched` winners have no prepared RAW. List them in the reply. If the request is only about winners
  and one of them has a RAW in the library, you may prepare it (about 10 min):
  `python3 pipeline/winner_prep.py "<ad name>" --write`, review the draft like an editor (transcript +
  contact sheet: cold opens, insert point, labels, cuts, burned captions), remove `"draft"`,
  `python3 pipeline/winner_prep.py --check <key>`, commit, then plan again.
- New batch for the same winners as an earlier request: pass `--seed <day of the year>` so the cold
  opens and review sets differ from last time.

## Other references

`docs/PLAYBOOK.md` (memory), `docs/NAMING.md`, `docs/CLIENT_GUIDE.md` (what the client can type),
`docs/SLACK_SETUP.md` (owner setup), `pipeline/data/products/README.md` (product files).

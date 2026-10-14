# Libra Cases ad pipeline: how to handle requests (Slack / Claude DM)

You turn one-line requests ("new batch for the winners", "new product ad sets", "3 statics and 4 videos, Black
Friday") into finished Facebook ads for Libra Cases (handbags) and upload them to Google Drive. Every batch starts
from a message: there is no daily automatic run. Nobody is watching: never ask follow-up questions, decide sensibly,
and reply once at the end.

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
3. **Only true claims, Meta-compliant.** Offers, gifts and reviews come from the product data (`make_batch.py`
   handles it). Any line you write yourself (`--lines`, product files, ad copy edits) uses only facts from
   libracases.com or `docs/PLAYBOOK.md` §1 (built-in bags), and for a new product only its Drive folder's notes
   (`facts.notes`: no free shipping, no libracases.com unless the notes say so; compliance checks it that way).
   Never health or medical claims, prescription drugs, politics, religion or blood/violence in any creative,
   caption, label or ad copy (the media buyer's rule; an AI persona is fine). `plan` runs `pipeline/compliance.py`
   on all of it, including the winner RAW audio each version plays. No faces in statics.
4. Upload everything with `make_batch.py upload` (Drive Outputs → `Winners/` or `New Products/` or the Outputs
   root → `<date> – <name>` → `Statics` / `Videos` + a run report). Never only post files in the chat.
5. Never publish anywhere. Never delete or move Drive files.

**Videos come in projects** (the client's agency format): one project = one video body in 4 versions
H1-H4 that differ only in the hook (opening line, opening shot, on-screen label). `plan` does this by
default (`--hooks 4`); a request for N videos means N projects (4N video files). File names are automatic
(`docs/NAMING.md`: `LC_<YYMMDD>_<Product>_<Theme>_S01_<layout>` / `..._P01_H1_<angle>`); list ads by these
names in the reply.

## Which pipeline? (read the message first)

A DM starts with the repo name (`Higgsfield-test: new product ad sets`): leave that prefix out of `--request`.

| The message says | Pipeline | Section |
|---|---|---|
| "winners", "winning ads", "new batch for the winners", "versions of 94-H4", "from the brief", "our best ads" | **WINNERS** | 1 |
| "new product", "new products", "new product ad sets", "I added a product", or a product name that is a folder in Drive `New Products` (`python3 pipeline/new_product.py list`) | **NEW PRODUCTS** | 2 |
| anything else: a built-in bag (Hobo Bag, Hobo 2.0, 3-piece set, vintage, slouchy) and/or a theme | **CATALOG** | 3 |

Both in one message ("winners and the new Silhouette Bag"): one run each, each with its own `$OUT`.

**Size, every pipeline:** no numbers in the message = a **batch**: 20 statics + 5 projects × 4 hooks (H1-H4) =
20 videos (winners and new products do this by themselves; catalog needs `--batch`). Numbers given = exactly
those, and a count not named is 0 ("6 statics" = 6 statics and no videos). "N videos" = "N projects" =
`--projects N` (4N files; `--hooks 1`: N single videos).

## 0. Setup (fresh container, about a minute)

```
cd <repo>
command -v ffmpeg || bash .claude/hooks/session-start.sh        # Slack sessions don't run hooks
command -v pdftotext || apt-get install -y -qq poppler-utils    # PDF notes in a New Products folder (pypdf: fallback)
python3 -c "import faster_whisper, PIL, numpy, cv2, pillow_heif, pypdf" 2>/dev/null || \
    pip install -q faster-whisper pillow numpy pillow-heif opencv-python-headless pypdf
python3 pipeline/drive_upload.py check                          # Drive login ok?
```

## 1. WINNERS: new versions of the weekly brief's winning videos

```
python3 pipeline/make_batch.py plan --pipeline winners --request "<message>" --out $OUT
```
- Numbers: add `--statics N --projects M` ("winners, 2 projects and 6 statics": `--statics 6 --projects 2`;
  `--videos M` in winners also means M winner projects).
- Named winners ("versions of 94-H4 and 148-H5"): add `--winners "94-H4,148-H5" --projects 2`, one project per
  named winner (plus `--statics N` only if asked).
- **Reads by itself:** the newest brief in Drive `Research Briefs` (the n8n weekly report): its "increase budget"
  and "keep" ads, matched to the winning RAW videos in `clip_bank.json` (`winner_raws`: cold opens, cuts, claim
  cuts). Each winner project keeps the proven RAW body intact (only its editorial cuts and `claim_cuts`, which remove
  health claims on word boundaries), tests 4 cold-open hooks cut from the RAW itself, adds the theme's offer card and
  the end card (`remix.py`), keeps the RAW's own sound and needs 0 voiceover lines. Statics are of the top
  winner's product.
- **Fill:** fewer winner projects possible than asked (unmatched winners; a winner gets one project per 4 of its
  cold opens, so one): the rest are new-angle storyboard projects of that product (voiced, so they cost credits)
  and a warning says `winners batch: N winner projects + M new-angle storyboard projects ...`. `--no-fill`: only
  the winner projects.
- **Check in the plan output:** `winners_source` (`"brief"`; `"fallback"` = the brief could not be read or matched
  no winner, its warning says which: the projects are all bank winners in `clip_bank.json` order, not this week's
  winners: say so in the reply), `brief` (name, `age_days`, `stale`: older than 8 days, still run it and say so),
  `project_hooks` (winner + ROAS per project, 4 versions each), `unmatched_winners` (+ why), the fill warning,
  `H<j> differs from H<i> by its on-screen hook only` (a RAW with 3 clean spoken openings: one version is a new
  label over another's opening; list it so), `repeat a hook type`, `open like ads already delivered`, the "needs
  a human" items (claim cuts to listen to once, the RAW story's health words), `est_credits` (0 without fill or
  `--winner-reviews`).
- `unmatched` winners have no prepared RAW: list them in the reply. If one has a RAW in the library, you may
  prepare it (about 10 min): `python3 pipeline/winner_prep.py "<ad name>" --write`, review the draft like an editor
  (transcript + contact sheet: 4 or more cold opens, insert point, labels, cuts, burned captions), remove
  `"draft"`, `python3 pipeline/winner_prep.py --check <key>` and `python3 pipeline/projects.py cadence` (both must
  pass; a RAW line saying the bag helps the body goes into `edit.claim_cuts`), commit, then plan again.
- New batch for the same winners as an earlier request: add `--seed <day of the year>` so another opening is H1
  (plan suggests it when openings went out before; a project already holds all of its winner's cold opens: new ones
  need `winner_prep.py`; say so).
- **Upload** lands in Drive `Outputs/Winners/<date> – <name>`. **Specs:** `pipeline/recipes/winners/<date>/<name>`.
- **Reply:** Drive folder link · brief used (name, age, stale; or the fallback and why) · one block per project
  ("P01 – <angle>" + winner and ROAS, then per version: H#, label, spoken cold open, length) · fill projects and why ·
  statics one line each · unmatched winners and why · "needs a human" items · the ad copy file · credits before →
  after.

## 2. NEW PRODUCTS: everything from the product's Drive folder

The client puts one folder per product in Drive `Ad Creative Pipeline / New Products` (photos, clips, a notes doc
with the price / was price or % off, a gift if any, colours, 3-7 features).
```
python3 pipeline/new_product.py list        # one row per folder: status new | draft | ready | tested <date>, changed, tests
python3 pipeline/make_batch.py plan --pipeline new-product --new-product "<folder name>" --request "<message>" --out $OUT
```
- **Which folders:** a named product = that folder (exact name or a unique part of it; case, a leading "the",
  punctuation and a plural s don't matter). No name ("new product ad sets", "new products", "I added a product") =
  every row of `list` with `"tests": 0` (no ads yet): one run per folder, each with its own `$OUT`, always by folder
  name. A row with ads and `"changed": true` (files added since its intake) is not remade: say so in the reply. None
  left: make nothing and reply with the folders, the date of their last ads (`status`), and that a named request
  ("new product Silhouette Bag") makes more.
- **More ads for a product that has some** ("more ads for the Silhouette Bag", its name again): the same command,
  no `--seed`. Plan sets `seed` to 1 + its recorded batches and warns `this product already has N batch(es)`: other
  statics, hooks and feature order than the earlier batches.
- Numbers: add `--statics N --projects M`. A theme: `--theme "<words>"` (a sale theme needs an offer in the notes).
- **Reads by itself, never the website:** plan runs the intake (`new_product.ensure`): photos (sorted faceless first,
  cleanest first = P0, P1 …; kinds packshot / worn / detail / other; a photo with a face is never used; a worn
  photo that may show part of a head gets `"statics": false`: videos only), clips, every notes file (txt, md, Google
  Doc / Sheet, docx, pdf, rtf, the folder's description): price and was price or "NN% off", a gift, colours and up
  to 7 feature bullets. It writes `pipeline/data/products/<slug>.json`: `"status": "ready", "auto": true` when `check`
  finds no problems. Next time it is reused while the folder is unchanged; a changed folder gets a new intake (also
  a draft nobody edited; a hand-edited file is kept, with a warning); `--refresh-product` forces a new intake
  (overwrites hand edits).
- **Check in the plan output:** `intake` (`intake` made now / reused, `made_by`, `site`: "not read (Drive folder
  only)", `read`: photos, `photo_kinds`, `faces`, clips, notes; `offer` with `price_source` "notes"; `colours`;
  `features`; `problems`; `warnings`), and the warnings `colour swatches: packshots matched ... by shade` (check the
  colours static), `may show part of a head` (that photo is in no static), `pick ... skipped`, `N of M statics left
  out` (clips but no faceless photos: no statics; say so: the client must add photos without a face), `PDF notes not
  read` (install the reader, section 0, and plan again with `--refresh-product`), and the length warning `will run
  about N s (QA wants 35-95 s)` (3-5 features plan ~32-35 s; 7 plan ~42-45 s, no warning: say so).
- **No human step is required:** a ready auto file runs. You may glance at the intake's `overview.jpg`
  (`source.overview` in the product file, there when the intake ran in this container; P0, P1 … = `photos[0]`,
  `photos[1]` … = picks `["photo", "P<n>"]`) and fix an obviously wrong pick or line in the product file (only true
  claims from its `facts.notes`; never set `"statics": true`), then set `"auto": false`, run
  `python3 pipeline/new_product.py check <slug>` (must be ok) and plan again.
- **Plan exits 2:** an unknown folder (it lists the folders); a draft (it prints the intake's `WARNING` lines and
  the problems): fix in the product file what it names, set `"status": "ready"`, `check <slug>` and plan again, or,
  when the folder lacks the material (no faceless photos and no clips, no notes, fewer than 3 feature lines), make
  nothing for that product and reply what the client must add to the folder (a `PDF notes not read` warning is
  ours to fix, not the client's). No price or % in the notes is not a draft: the ads run without an offer
  (`offer`: "no discount"; a sale theme exits 2): say so in the reply.
- **Upload** lands in Drive `Outputs/New Products/<date> – <name>`; it records the batch in the product file's
  `"tests"` and prints `product file changed: ... commit it`. **Specs:** `pipeline/recipes/new_products/<date>/<name>`
  plus `pipeline/data/products/<slug>.json` (with its `tests`), in the same commit.
- **Reply:** Drive folder link · product, what was read (photos, clips, notes; "libracases.com not read") and the
  offer used · the product file (made now / reused, committed) · statics one line each · one block per project
  (angle: features / colours / showcase / lifestyle / offer, then per version: H#, label, spoken line, length) ·
  warnings (colour matching, length, skipped photos, statics left out, a repeat batch's seed) · the ad copy file ·
  credits before → after.

## 3. CATALOG: built-in bags and themes

```
python3 pipeline/make_batch.py plan --product "<name>" [--theme "<words>"] --statics N --projects M --request "<message>" --out $OUT
```
"batch" with no numbers: `--batch` instead of the counts. A product on libracases.com that `plan` does not know
("unknown product") and that has no New Products folder: `python3 pipeline/new_product.py intake --site <url|handle>`,
then `--product "<key>"`. No folder, no photos, not on the site: make nothing and say what is needed.
**Upload** lands in `Outputs/<date> – <name>`; **specs:** `pipeline/recipes/daily/<date>/<name>`.

## 4. Request → plan flags (every pipeline)

| Request says | `make_batch.py plan` flags |
|---|---|
| "N statics and M videos" (or "M projects") | `--statics N --projects M` → M projects × 4 hook versions (winners: `--videos M` = M winner projects too; catalog: `--videos M` / `--winner-videos M` still work) |
| no numbers | nothing (winners, new products) / `--batch` (catalog): 20 statics + 5 projects |
| "single videos" / "no hook versions" | add `--hooks 1` (V01, V02 … as before, winners too) |
| a product (catalog) | `--product "<name>"`: Hobo Bag (default), Hobo 2.0, 3-piece set, vintage, slouchy, or any product file in `pipeline/data/products/` |
| a theme | `--theme "<words>"`: black friday, cyber monday, christmas, gift, mother's day, travel are built in; any other theme: `--theme "<words>"` plus your own short lines with `--lines` (keys `hero`, `bold`, `colours`, `P01_hook` / `V01_hook`, `P01_close` …) |
| "story" / "long video" / "storytelling" | add `--story` (1.5-2 min where the product has the footage; plan warns when it runs shorter: say so) |
| "winners with reviews" | add `--winner-reviews` (only when asked: by default winner videos keep their proven body untouched) |
| "no music" | add `--no-music` |
| "redo project 2" (in the thread) | same plan flags (new product: the folder name, never `next`) with `--seed <N+1> --only P02`, N = the `seed` the first plan printed, into a new `--out` (only P02 is voiced, rendered, uploaded; names move to `_v2` by themselves; a winner project: only its H1 changes, plan says so) |
| "another hook for P02 H3" | same plan flags with `--seed <N> --hook-seed <N+1> --only P02H3`, N as above (same body, a new hook; exits 2 if no unused hook is left: say so) |
| "drop S03" / "delete …" | nothing to plan: never delete or move Drive files. Reply that it stays in the Drive folder and is simply not uploaded to Meta |

`plan` exits 2 with a clear message when something is wrong (unknown product or folder, draft product file, too
many credits, a sale theme for a product without a deal, a compliance problem, a video under the 25 s floor: too
little material, so make the statics only and say so). Read it and act on it.

## 5. The run (every pipeline)

```
OUT=/tmp/run/<short-name>; mkdir -p $OUT
python3 pipeline/make_batch.py plan <flags> --request "<the request text>" --out $OUT
```
1. Read the plan output and every warning (the pipeline's section says what to look for), plus `offer`,
   `est_credits`, `names` and length warnings. `plan` also writes `$OUT/ad_copy.csv` (Meta primary texts,
   headlines, description, CTA per static / per project) and `$OUT/compliance.json`. If plan exits 2 with
   `compliance: N problem(s)`, reword the line it names (`--lines`, the version JSON or the product file) and plan
   again. Higgsfield `balance` → note it.
2. **Voiceovers:** for every item in `$OUT/tts_needed.json` call `generate_audio_batch` (model
   `text2speech_v2`, variant `elevenlabs`, `use_unlim: false`, `voice_type` + `voice_id` from the item,
   prompt = item `text`; max 12 per call; resubmit any that fail with 429), `jobs_wait`, then download each
   result url to `$OUT/<item file>` (`curl -sSL -o`). Identical lines are listed once; render copies them.
   Winner projects need none (only fill projects are listed).
3. **Render** (statics: a few minutes in all; about 20-25 min per project of 4 versions, 2 videos at a time; a
   batch of 20 statics + 5 projects is about 2 hours), detached:
   `setsid nohup python3 pipeline/make_batch.py render --out $OUT > $OUT/render.log 2>&1 < /dev/null &`
   then check the log every couple of minutes until it prints `QA:`. More than 3 projects (every batch): render and
   upload the statics first (`render --only S`, `upload --only S`), then the videos (`render --only V`,
   `upload --only V`), with the same `--name`. No progress messages: one reply at the end. Use a fresh `$OUT` for
   every request.
4. **QA:** Read `$OUT/qa/statics.jpg`, every `$OUT/qa/P*.jpg` (one per project: the 4 hooks side by side
   + the body + a 'body vs H1' number per version: under 10 = same body) and `$OUT/qa/report.json`. Captions
   sit at the bottom (white text with an outline, keywords on a red pill), jump to the top only for shots whose
   bottom shows a face or the product, and never sit over the end card (`"caption_zone": "reels"` in a spec keeps
   them higher, above Meta's strict Reels zone; `"caption_pos": "top"|"bottom"` on a segment forces a shot); under
   the narrator's "Here's <customer> …" the picture must show the product or that customer, never another person;
   one narrator voice per video. A new product's square photos and clips are shown whole (a white or blurred
   backdrop behind them: `"fit"`), never cropped to the middle. Text off-frame, wrong product, black frames, a
   face: fix a hook in its `..._P01_H3_...json`, a body problem in `$OUT/_before_hooks/<V01 spec>.json` then re-run
   `python3 pipeline/projects.py expand --out $OUT` (all 4 versions get it), and `render --only <id>`; or
   leave it out and say so. A face in a static or a failed render is never uploaded; length/anchor flags and
   `body differs from H1 (body match M …)` (that version's body is not its project's: look at its `qa/P*.jpg`,
   fix it as above or leave it) are uploaded and listed under QA flagged in the run report: mention them in the reply.
5. **Upload:** `python3 pipeline/make_batch.py upload --out $OUT --name "<short request name>"` → prints the
   Drive folder link (`drive_path`: where it landed) and the uploaded ads. Higgsfield `balance` again.
6. **Reply** (one short message, the pipeline's format above): Drive folder link · statics one line each · videos
   one block per project · the ad copy file · plan warnings (fewer than 4 versions, openings already used in an
   earlier batch, a hook line opening 3+ versions, "needs a human" items) · QA flags · music (the client's track or the generated bed; winners: the RAW's
   own sound) · credits used (balance before → after) · anything skipped, failed or needing a human.
7. Commit the specs (JSON only, no media, no secrets) into the pipeline's folder:
   `python3 pipeline/make_batch.py specs --out $OUT --to pipeline/recipes/<winners|new_products|daily>/<plan YYYY-MM-DD>/<short-name>`,
   plus any new or changed product file (a new product's always changes: its `tests`); commit, push.

**Music:** storyboard videos get a bed under the voice automatically: the client's licensed tracks from
`pipeline/assets/music/` when there are any, otherwise a generated bed (made by `pipeline/music.py`, nothing to
license). Winner videos keep their RAW's own sound.

## Other references

`docs/PLAYBOOK.md` (memory), `docs/NAMING.md`, `docs/CLIENT_GUIDE.md` (what the client can type),
`docs/SLACK_SETUP.md` (owner setup), `pipeline/data/products/README.md` (product files).

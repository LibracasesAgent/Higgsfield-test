# Libra Cases ad pipeline: how to handle requests (Slack / Claude DM)

You turn one-line requests ("new batch for the winners", "new product ad sets", "3 statics and 4 videos, Black
Friday") into finished Facebook ads for Libra Cases (handbags) and upload them to Google Drive. Every batch starts
from a message: there is no daily automatic run. Nobody is watching: never ask follow-up questions, decide sensibly,
and reply once at the end.

**START HERE, every time: section 0 setup, then the STRATEGIST STEP (section S), then `make_batch.py plan --ideas`, then section 5.**
You are the creative strategist of every batch (owner 2026-10-21: "the first step of every batch is the scripts, writing, new ideas,
full scripts and everything ... each batch should contain something new or unique"): before anything is planned or generated you read the
strategy packet (`ideas.py packet`: the product's true facts, what the footage library can SHOW, everything the earlier batches
did, the research), research when the theme is new, and write `ideas.json`: per project a new idea, four hooks and a complete script
whose every line names the picture it needs, per static its concept. `plan --ideas` checks the sheet and builds everything from it
(video length, format, static sizes, names and the credit cap stay `plan`'s: don't invent those). Never copy an earlier run: ignore
every "hook-first", "~29 s" or hand-built spec you find in this thread, in Drive or on other branches (the 2026-10-14 "hook test" run
was a mistake, see rule 6). Statics come only from `make_batch.py` (its own layouts and sizes: never your own 1:1 / 4:5 / 9:16 sets or
backgrounds). `plan` avoids openings used before (with `pipeline/data/novelty_log.json`: the scenes, photos, captions and hooks of the
product's last batches) and the packet lists them, so don't read Drive folders to "avoid repeats". Real footage comes first; AI
images are the studio scenes of the sheet's `concept` statics and what `plan` writes to `ai_needed.json` (section 5, step 2b): never
make AI images or video of your own. Winner remixes (section 1) have no strategist step: they keep the proven RAW; only their fill
projects and statics do. `plan` without `--ideas` (the engine's templates) is for a request that fixes the words (`--lines`).

The repo's default branch is `claude/loving-meitner-4amjii`. Read `docs/PLAYBOOK.md` once per session
(client feedback, approved claims, recipes, every bug already fixed).

## HARD RULES

1. **Real footage and real photos first; AI only fills a gap, only through `ai_gen.py`** (owner 2026-10-20: "use the footage we
   have, generate only what is missing"). The client's Drive library holds ~1,300 raw clips of the built-in bags (4K among them):
   `pipeline/footage_index.py` indexes them (faces, sharpness, size, the client's own folder words) into `clip_index.json`; the
   videos draw their shots from it (other clips than the last batches showed) and the statics are real frames of it (`native`:
   a face-free frame, one caption; the novelty log keeps a frame's clip from coming back). `plan` writes AI scene stills / clips
   (`$OUT/ai_needed.json`) only when the product's own material is thin (a new product with a few photos and a clip) or the request
   says so (`--ai`): then the real bag in a new scene (cafe, street from behind, hallway ...), still 4:5 / clip 3 s. You make
   exactly what `ai_needed.json` lists (models, prompts, ids): images with `gpt_image_2_5` (medium, 2k), clips with `kling3_0` /
   `minimax_hailuo`. Never: other generators or models, presets, Ads Studio, `execute_preset`, upscalers, voice cloning, a face in any
   picture except the PRESENTER's (below), a prompt of your own (the one exception: the SCENE of a `concept` static
   in the strategist's sheet, section S: surface, props, light, composition; `ai_gen` adds the keep-the-real-bag text, the style and the no-face rule). An AI asset ships only when it passed
   `ai_gen.py gate` / `clips` AND you looked at its contact sheet and the bag is the real bag (shape, colour, handles, hardware)
   in a believable real photo / clip: otherwise `ai_gen.py reject <id>` (render puts the real photo / footage back). `plan
   --no-ai` = real photos and footage only; `--no-frames` = no statics from footage frames.
   **The presenter (owner 2026-10-21: "avatars accepted if there is an actual story that requires actors"; Julian wants a woman sitting and
   talking, the footage cut in between):** a project of the strategist's sheet may carry a generated host who says the script to camera
   (`pipeline/presenter.py`, ideas.py's `presenter` block, docs/PLAYBOOK.md). She is ONE original, realistic adult (data/presenters.json: her
   Soul-made reference picture, never a real person's face, never a celebrity), a host and never a customer: 'you' form, no "I bought / I love /
   my", no invented use or result, no testimonial. Her scene stills are `gpt_image_2_5` from TWO references (her picture + the real bag's
   packshot), her takes `kling3_0` (pro, sound on, start_image = the scene still, the line in the prompt: ~2.5 credits a second); you make exactly
   what `$OUT/presenter_needed.json` lists, gate it (`presenter.py gate`) and look at `qa/presenter_stills.jpg` / `qa/presenter_takes.jpg`: the
   bag must be the real bag and she must read as a real person (soft natural skin, only gentle lines); otherwise `presenter.py reject` and make it once more.
   **Never ask a model for "pores / fine lines / unretouched / no smoothing"** (owner 2026-10-21: that wording gave etched wrinkles and orange shiny
   skin, "totally fake"): the prompts in `presenter.py` ask for soft, even, natural phone-photo skin; a new host is made the same way.
   The usual AI statics rules stay (the statics have no faces).
2. **The only Higgsfield calls:** `generate_audio_batch` (text2speech_v2) for the lines in `tts_needed.json`;
   for the AI assets `media_upload` + `media_confirm`, `generate_image_batch`, `generate_video_batch`; and `jobs_wait`,
   `balance`, `transactions`; for a NEW presenter (not a batch): `generate_image_batch` with `soul_2`, `show_characters`
   (train a Soul ID) and `show_reference_elements`. One ugc project (one voice take per chapter + 4 hook lines) costs about 4-5 credits, a full
   batch (5 projects) about 22; a scene still ~1, a clip 4.5-6. **A batch is capped at 100 credits, voiceover + AI together** (a batch with a presenter adds her stills and takes on top:
   ~2.5 credits per second of her talking, a 4-project batch ~900; `plan` caps that part at 1000 (`--presenter-cap X` when the request names
   more) and prints it as `presenter`)
   (`plan` plans the AI part inside it: 100 - voiceover - a reserve of 8 for one re-make of a failed asset; `plan` refuses more
   than 100 for voiceover alone unless you pass `--budget X`, and takes `--ai-cap X` only when the request names another total).
   **The cap is per batch, not per message:** a message for three bags is three batches (B045, B046, B047), each with its own 100, so
   it may use up to 300 in all; the voiceover of such a message is ~40 in total and is nowhere near a limit: never stop, ask or
   scale a request down because of a credit number you remember (the old limit was 40; it is 100 now). Only `plan` refuses.
   Never generate an asset twice without a reason, never go over the cap. Check `balance` before and after; report both.
3. **Only true claims, Meta-compliant.** Offers, gifts and reviews come from the product data (`make_batch.py`
   handles it). Any line you write yourself (`--lines`, product files, ad copy edits) uses only facts from
   libracases.com or `docs/PLAYBOOK.md` §1 (built-in bags), and for a new product only its Drive folder's notes
   (`facts.notes`: no free shipping, no libracases.com unless the notes say so; compliance checks it that way).
   Never health or medical claims, prescription drugs, politics, religion or blood/violence in any creative,
   caption, label or ad copy (the media buyer's rule; an AI persona is fine). `plan` runs `pipeline/compliance.py`
   on all of it, including the winner RAW audio each version plays. No faces in statics.
4. Upload everything with `make_batch.py upload` (Drive Outputs → `Winners/` or `New Products/` or the Outputs
   root → `B045 – <date> – <product> – N statics + M projects` → `Statics` / `Videos` + a run report + the ad index). Never only post files in the chat.
5. Never publish anywhere. Never delete or move Drive files.
6. **Never reshape the videos to fit a request.** Videos run 55-80 s in the ugc format (the default: what `plan`
   estimates; the classic formats, `--classic`, 40-60 s; the story format 90-120 s): don't shorten them, rebuild their
   specs or change their format. A message like "hook-first", "hook test", "better
   hooks", "Meta isn't spending on the videos" means other **hooks**: the normal projects with 4 hook versions at the
   normal length (`--projects N`; fresh openings: `--seed` / `--hook-seed`, section 4). "3 videos" = `--projects 3`
   (12 files), `--hooks 1` only when the message says "single videos". Never `upload --include-flagged`: `render`
   marks a video `too short` (hard: upload skips it) under the 25 s floor or under 80% (ugc: 70%) of the length `plan`
   estimated, which is what a cut-down spec looks like (the scorecard's misses are soft flags: uploaded and listed). If a
   request conflicts with this, make the standard version and say in the reply what you did instead and why.

**Videos come in projects** (the client's agency format): one project = one video body in 4 versions
H1-H4 that differ only in the hook (opening line, opening shot, on-screen label). `plan` does this by
default (`--hooks 4`); a request for N videos means N projects (4N video files). File names are automatic
(`docs/NAMING.md`: `LC_<YYMMDD>_<Product>_<Theme>_B045_S01_<layout>` / `..._B045_P01_H1_<angle>`: **B045 is the batch number**,
taken by `plan` from `pipeline/data/batch_ledger.json` and also the start of the Drive folder name); list ads by these names in the
reply and name the batch ("B045").

**The default new video is the ugc format** (owner 2026-10-14, after measuring the clients' top-impression ads): 55-80 s,
one voice talking to the viewer in "you" form ("you stop worrying in crowds": never an invented customer
experience) at 185-215 words per minute over a new shot about every 2 s, each phrase showing what it says (hands, zips,
pockets, the bag worn), a specific hook in the first 3 s ("Four things you'll notice ..."), numbered chapter captions
("1. you stop worrying in crowds") with the feature's tag, problem -> fix pairs, reviews on screen at most 3 s, the offer
last, one steady loudness (-14 LUFS). `pipeline/ugc_script.py` writes the scripts (angle per project: `day` a story of the bag through a
day, each moment a feature and a clip of that place, `things`, `demo`, `stop`, `travel`, `value`, in the file name; a batch of 5 has 5
of the 6 and the last batch's angles come last, so the story differs every batch), `pipeline/scorecard.py` measures every rendered video. It applies to
catalog, new-product and winners-fill projects; `--classic` (and `--story`) keep the old formats. Winner remixes are untouched.
Statics are clean and photo-first (owner 2026-10-20, from the competitors' ads: one big photo, next to no text). Of 20: `studio` 4
(the real packshot large on a calm tinted backdrop, a small wordmark, at most one short line and one small offer pill; no sticker, no
button), `native` 4 (a real face-free photo, one caption), `quotes` 3 (ONE verbatim review by the packshot), `value` 2, `offer` 2,
`stars` 1, and `colours`, `checklist`, `bold`, `compare` once each, where the product backs them (faceless photos / a review / a
price; else the next clean layout takes the slot). The AI scene statics (section 5, step 2b) replace the text-heavy slots first and
come in four looks (pill only, caption only, the photo alone, caption + pill): half carry no caption. `--classic` restores the old
static cycle. **Studio-level concept statics** (owner 2026-10-21: "the bag, with some elements behind ... realistic"): the strategist's
sheet makes about half of a batch's statics `concept`: an AI scene of the REAL bag (Higgsfield `gpt_image_2_5` from the real packshot,
gated against it like every AI still) with props that belong to the idea (a latte, keys, a gift, a chair), the words set in a calm footer
under the photo (a small kicker, a serif headline, the % pill) so nothing is printed on the bag; a person is only ever cropped at the
shoulders or seen from behind. The other statics are real (studio packshot, a footage frame, quotes, value ...). Videos carry **no
review chapters or review cards** (media buyer 2026-10-21: "not good as objection handling before the CTA"); statics keep one verbatim review.
The end card is a full studio card (the real bag on a tinted backdrop, the name, the offer pill, the button) inside Meta's safe zone.

## Which pipeline? (read the message first)

A DM starts with the repo name (`Higgsfield-test: new product ad sets`): leave that prefix out of `--request`.

| The message says | Pipeline | Section |
|---|---|---|
| "winners", "winning ads", "new batch for the winners", "versions of 94-H4", "from the brief", "our best ads" | **WINNERS** | 1 |
| "new product", "new products", "new product ad sets", "I added a product", or a product name that is a folder in Drive `New Products` (`python3 pipeline/new_product.py list`) | **NEW PRODUCTS** | 2 |
| anything else: a built-in bag (Hobo Bag, Hobo 2.0, 3-piece set, vintage, slouchy) and/or a theme | **CATALOG** | 3 |

Both in one message ("winners and the new Silhouette Bag"): one run each, each with its own `$OUT`.
Several bags in one message ("3 videos and 5 statics for each: Hobo Bag, Vintage Bag, Hobo 2.0"): one catalog run per bag with those
numbers (`--product "<bag>" --statics 5 --projects 3`, its own `$OUT`; each gets its own batch number B045, B046, B047), one reply with
every Drive link and batch id.
Order: plan all the runs and make all their voiceovers first (the voiceovers need no render, the three plans share nothing),
then render and upload one bag at a time (one detached chained script: statics first, then the videos of that bag), so the first
Drive folder fills while the next bag renders; 9 projects + 15 statics keep a session busy for about 3-4 hours. A session has only
~10 GB of disk: the clip cache trims itself (`recut.trim_cache`, 4.5 GB), and after each bag's upload delete its local videos
(`find $OUT/videos -name '*.mp4' -delete`, never anything in Drive); `df -h /home` says how much is left.

**Size, every pipeline:** no numbers in the message = a **batch**: 20 statics + 5 projects × 4 hooks (H1-H4) =
20 videos (winners and new products do this by themselves; catalog needs `--batch`). Numbers given = exactly
those, and a count not named is 0 ("6 statics" = 6 statics and no videos). "N videos" = "N projects" =
`--projects N` (4N files; `--hooks 1`: N single videos).

## 0. Setup (fresh container, about a minute)

```
cd <repo>
command -v ffmpeg || bash .claude/hooks/session-start.sh        # Slack sessions don't run hooks
command -v pdftotext || (apt-get update -qq && apt-get install -y -qq poppler-utils)   # PDF notes in a New Products folder (pypdf: fallback)
python3 -c "import faster_whisper, PIL, numpy, cv2, pillow_heif, pypdf, openpyxl" 2>/dev/null || \
    python3 -m pip install -q faster-whisper pillow numpy pillow-heif opencv-python-headless pypdf openpyxl
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
  cold opens, so one): the rest are new-angle storyboard projects of that product (ugc videos, voiced, so they cost
  about 4-5 credits each) and a warning says `winners batch: N winner projects + M new-angle storyboard projects ...`.
  `--no-fill`: only the winner projects.
- **Check in the plan output:** `winners_source` (`"brief"`; `"fallback"` = the brief could not be read or matched
  no winner, its warning says which: the projects are all bank winners in `clip_bank.json` order, not this week's
  winners: say so in the reply), `brief` (name, `age_days`, `stale`: older than 8 days, still run it and say so),
  `project_hooks` (winner + ROAS per project, 4 versions each), `unmatched_winners` (+ why), the fill warning,
  `H<j> differs from H<i> by its on-screen hook only` (a RAW with 3 clean spoken openings: one version is a new
  label over another's opening; list it so), `repeat a hook type`, `open like ads already delivered`, the "needs
  a human" items (claim cuts to listen to once, the RAW story's health words), `est_credits` (0 without fill or
  `--winner-reviews`; about 4-5 per fill project).
- `unmatched` winners have no prepared RAW: list them in the reply. If one has a RAW in the library, you may
  prepare it (about 10 min): `python3 pipeline/winner_prep.py "<ad name>" --write`, review the draft like an editor
  (transcript + contact sheet: 4 or more cold opens, insert point, labels, cuts, burned captions), remove
  `"draft"`, `python3 pipeline/winner_prep.py --check <key>` and `python3 pipeline/projects.py cadence` (both must
  pass; a RAW line saying the bag helps the body goes into `edit.claim_cuts`), commit, then plan again.
- New batch for the same winners as an earlier request: add `--seed <day of the year>` so another opening is H1
  (plan suggests it when openings went out before; a project already holds all of its winner's cold opens: new ones
  need `winner_prep.py`; say so).
- **Upload** lands in Drive `Outputs/Winners/B045 – <date> – …`. **Specs:** `pipeline/recipes/winners/<date>/<name>`.
- **Reply:** Drive folder link · brief used (name, age, stale; or the fallback and why) · one block per project
  ("P01 – <angle>" + winner and ROAS, then per version: H#, label, spoken cold open, length) · fill projects and why ·
  statics one line each · unmatched winners and why · "needs a human" items · the ad copy file · credits before →
  after.

## 2. NEW PRODUCTS: everything from the product's Drive folder

The client puts one folder per product in Drive `Ad Creative Pipeline / New Products` (photos, clips, a notes doc
with the price / was price or % off, a gift if any, colours, 3-7 features: any subset works, a thin folder is normal).
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
  read` (install the reader, section 0, and plan again with `--refresh-product`), `videos left out: ...` (a video
  that stays under the 25 s floor even after padding: plan leaves it out itself, exit 0, the statics proceed; the
  warning names what the client could add: say so in the reply, it is a suggestion, not a requirement), and the
  length warning `thin script: about N s` (the ugc format runs 55-80 s: 5-7 feature lines run ~60-70 s, no
  warning; a thin folder (1-4 feature lines) runs ~40-50 s: it runs as it is, say so and that more feature lines, reviews or a price make it
  longer; a script that would run under ~27 s (0-1 usable lines) is replaced by a classic video, padded by plan to
  ~38 s with blocks that only restate its notes: the colours named in the notes, a recap of the features' own
  tags, "Now $69, down from $99.", the gift, and a short silent picture hold after each middle line; a stills-only
  product with 3 lines and no price runs ~28 s and may get 2-3 hook versions instead of 4 (too few photos for 4
  different opening shots): say so). Folders with photos but no feature lines at all get classic videos (plan warns).
- **No human step is required:** a ready auto file runs. You may glance at the intake's `overview.jpg`
  (`source.overview` in the product file, there when the intake ran in this container; P0, P1 … = `photos[0]`,
  `photos[1]` … = picks `["photo", "P<n>"]`) and fix an obviously wrong pick or line in the product file (only true
  claims from its `facts.notes`; never set `"statics": true`), then set `"auto": false`, run
  `python3 pipeline/new_product.py check <slug>` (must be ok) and plan again.
- **Plan exits 2:** an unknown folder (it lists the folders); a draft (it prints the intake's `WARNING` lines and
  the problems): fix in the product file what it names, set `"status": "ready"`, `check <slug>` and plan again, or,
  when the folder has no usable photo and no clip, make nothing for that product and reply what the client must
  add to the folder (a `PDF notes not read` warning is ours to fix, not the client's). Fewer than 3 feature lines,
  no notes, no price or % are not drafts: the statics run, the videos are padded from what the notes do say or
  left out with one warning (above), the ads run without an offer when the notes give none (`offer`: "no
  discount"; a sale theme exits 2): say so in the reply. Plain lines (no bullet marks, one fact per line) count as
  the feature list, and `Colours:` may sit inside the price line.
- **Upload** lands in Drive `Outputs/New Products/B045 – <date> – …`; it records the batch in the product file's
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
**Hobo 2.0:** its site photos and its footage show two different bags, so a batch shows one (`pipeline/data/designs.json` `show`,
PLAYBOOK 4g; plan warns `design: ...`: say it in the reply). With the footage's bag (the default) presenter projects exit 2: make them
as normal voiceover projects and say so.
**Upload** lands in `Outputs/B045 – <date> – …`; **specs:** `pipeline/recipes/daily/<date>/<name>`.

## 4. Request → plan flags (every pipeline)

| Request says | `make_batch.py plan` flags |
|---|---|
| "N statics and M videos" (or "M projects") | `--statics N --projects M` → M projects × 4 hook versions (winners: `--videos M` = M winner projects too; catalog: `--videos M` / `--winner-videos M` still work) |
| no numbers | nothing (winners, new products) / `--batch` (catalog): 20 statics + 5 projects |
| "single videos" / "no hook versions" | add `--hooks 1` (V01, V02 … as before, winners too) |
| a product (catalog) | `--product "<name>"`: Hobo Bag (default), Hobo 2.0, 3-piece set, vintage, slouchy, or any product file in `pipeline/data/products/` |
| a theme | `--theme "<words>"`: black friday, cyber monday, christmas, gift, mother's day, travel are built in; any other theme: `--theme "<words>"` plus your own short lines with `--lines` (keys `hero`, `bold`, `colours`, `P01_hook` / `V01_hook`, `P01_close` …) |
| "Black Friday" / "Cyber Monday" / "Cyber Week" while the sale runs (23 Oct - 30 Nov 2026) | `--theme "black friday"` (or `cyber monday`): plan adds the campaign by itself (`data/campaign.json`, warning `campaign: ...`): end card "Black Friday Sale" + "UP TO 60% OFF + FREE GIFTS", the gift sentence in the close, a `gifts` and a `bundle` static. Each bag keeps its own % ("60% off" only of 2 or 3 bags together); PLAYBOOK 4f |
| "story" / "long video" / "storytelling" | add `--story` (the classic story format, 1.5-2 min where the product has the footage; plan warns when it runs shorter: say so) |
| "presenter" / "a woman talking" / "someone talking to camera" / "like the mom videos" / "with a model" | no flag: in the strategist's `ideas.json` the named number of projects carry `"presenter": {"id": "maya", ...}` (all of them when no number is named; "mix" = about half, the rest normal ugc voiceover projects, each with a different idea). `plan` prints the `presenter` credits (~2.5 per second of her talking: a presenter project ~225, four ~900; cap 1000). Say the cost in the reply. No presenter words in the message = normal ugc videos only |
| "the old format" / "classic videos" | add `--classic` (the pre-2026-10-14 output: classic video formats showcase / features / reviews / colours, 40-60 s, and the old static cycle). Only when the request asks for it |
| "winners with reviews" | add `--winner-reviews` (only when asked: by default winner videos keep their proven body untouched) |
| "no music" | add `--no-music` |
| "no AI" / "real photos only" | add `--no-ai` (no scene stills / clips; ai_gen.py) |
| "AI scenes" / "generate new scenes" | add `--ai` (AI scene statics and clips even when the product has enough real material) |
| "no footage frames" | add `--no-frames` (statics from the packshots and photos only) |
| "redo project 2" (in the thread) | same plan flags (new product: the folder name, never `next`) with `--seed <N+1> --batch-id B045 --only P02`, N = the `seed` the first plan printed, B045 = the batch the thread made, into a new `--out` (only P02 is voiced, rendered, uploaded; the names become `B045r2`; a winner project: only its H1 changes, plan says so) |
| "another hook for P02 H3" | same plan flags with `--seed <N> --hook-seed <N+1> --batch-id B045 --only P02H3`, N as above (same body, a new hook; exits 2 if no unused hook is left: say so) |
| "drop S03" / "delete …" | nothing to plan: never delete or move Drive files. Reply that it stays in the Drive folder and is simply not uploaded to Meta |

`plan` exits 2 with a clear message when something is wrong (unknown product or folder, draft product file, too
many credits, a sale theme for a product without a deal, a compliance problem, nothing at all left to make). A video
under the 25 s floor (too little material) is left out by `plan` itself with a `videos left out: ...` warning
(exit 0, the statics proceed): say so in the reply. Read it and act on it.

## S. The strategist step (catalog and new-product batches; every time)

```
OUT=/tmp/run/<short-name>; mkdir -p $OUT
python3 pipeline/ideas.py packet --product "<name>" [--theme "<words>"] --projects M --statics N --request "<the request>" --out $OUT
```
1. **Read** `$OUT/strategy_packet.md` (facts you may claim; the footage tags the pictures are chosen from, with counts; every earlier
   batch's angles, hooks, lines, statics and scenes) and `docs/research/*.md`. A new theme or a thin research file: a few WebSearch
   queries (competitors' ads, what works for the theme, Meta rules) and a new file in `docs/research/` (sources, [V]/[S]/[I]/[U] tags).
   The Meta Ad Library is not reachable from here; articles about ad libraries are.
2. **Write `$OUT/ideas.json`** (format: `python3 pipeline/ideas.py --help`): **M projects, each a different idea and structure** (a pack-out
   demo, a crowd scenario, a gift guide, a numbered buyer's guide, a day, a comparison ... not the engine's six angles and nothing an
   earlier batch did), `why_new` that says what no earlier batch did, 4 hooks of at least 3 types, a complete script of 5-11 chapters
   (170-285 words in all, one voice take each, 'you' form, the offer last ending "Tap the link below."), every chapter with `show` tags
   (what the picture must show while it is said: prefer tags with many footage moments in the packet) and the feature `tag` that shows on
   screen; **N statics**, about half `concept` scenes (each different: flat-lay, cafe chair, back pocket, gift styling, dark luxe, hallway,
   street from behind ...; the scene prompt leaves the end where the words go EMPTY; no face, eyes, sunglasses, mannequin, interior of
   the bag you have no photo of; the packshot shown is the reference, `scene.colour` / `scene.ref` pick it) and the rest studio / native /
   quotes / value / offer / stars where they fit. Only the packet's facts; no first person, no invented customer experience, no countdown
   or sale end date nobody confirmed, no "theft-proof"; counts like "five things" only when the video delivers them.
3. `python3 pipeline/ideas.py check $OUT/ideas.json --product "<name>" --projects M --statics N`: fix every PROBLEM (warnings: read them),
   check again. Then `plan --ideas $OUT/ideas.json ...` (section 5); `plan` copies the sheet and makes `strategy_sheet.md/.csv`, which
   `upload` puts in the Drive batch folder.
4. The reply names the ideas (one line per project: title, structure, why it is new) and links the strategy sheet.

## 5. The run (every pipeline)

```
OUT=/tmp/run/<short-name>; mkdir -p $OUT
python3 pipeline/make_batch.py plan <flags> --ideas $OUT/ideas.json --request "<the request text>" --out $OUT   # (section S)
```
1. Read the plan output and every warning (the pipeline's section says what to look for), plus `offer`,
   `est_credits`, `names` and length warnings (ugc: `thin script: about N s`; `project_hooks` lists each version's hook
   type, label and line). `plan` also writes `$OUT/ad_copy.csv` (Meta primary texts,
   headlines, description, CTA per static / per project) and `$OUT/compliance.json`. If plan exits 2 with
   `compliance: N problem(s)`, reword the line it names (`--lines`, the version JSON or the product file) and plan
   again (a line fixed by hand: `python3 pipeline/make_batch.py check --out $OUT`). Higgsfield `balance` → note it.
   The batch number is claimed in Drive (`pipeline/batch_lock.py`), so runs started at the same time never share one; the warnings
   `batch number: another run took ...` and `another batch of <product> is being made right now` go into the reply (two batches of
   one bag made at once can share a hook or a static).
2. **Voiceovers:** for every item in `$OUT/tts_needed.json` call `generate_audio_batch` (model
   `text2speech_v2`, variant `elevenlabs`, `use_unlim: false`, `voice_type` + `voice_id` from the item,
   prompt = item `text`; max 12 per call; resubmit any that fail with 429), `jobs_wait`, then download each
   result url to `$OUT/<item file>` (`curl -sSL -o`). Identical lines are listed once; render copies them.
   Winner projects need none (only fill projects are listed). A ugc project's lines are one take per chapter
   (`V01_c1.mp3` ... the 4 hook versions share them) + one short line per hook (`P01H2_hook.mp3` ...): read the take as
   written, never reword it. The lead's voice choice, when there is one, is in `pipeline/data/voice.json` (plan applies
   it: the items already carry its `voice_id`; render speeds the take up by its `speed`, default 1.12).
2b. **AI scenes** (when `plan` printed `"ai"` / wrote `$OUT/ai_needed.json`; `python3 pipeline/ai_gen.py show --out $OUT`): do it
   right after the voiceovers' submit (they run in parallel).
   1. Upload each distinct `ref` file once (`media_upload`, `curl -X PUT` the file, `media_confirm`); one `generate_image_batch`
      per 12 stills (`model` / `params` / `prompt` exactly as listed, `medias: [{value: <media id>, role: image_references}]`,
      `use_unlim` false); `jobs_wait`; download each result to `$OUT/<file>` (`curl -sSL -o`).
   2. `python3 pipeline/ai_gen.py gate --out $OUT`, then **look at `$OUT/qa/ai_stills.jpg`** (reference | still): `python3
      pipeline/ai_gen.py reject --out $OUT AS03 ...` for any still where the bag's shape, colour, handles or hardware differ,
      that shows a face, a chin or a mouth, or that looks AI (plastic, melted, odd hands, text). Never ship one you doubt.
   3. For every clip whose start still (`AV..`) passed: `generate_video_batch` (start_image = that still's job id, `model` /
      `params` / `prompt` as listed); `jobs_wait`; download to `$OUT/<file>`; `python3 pipeline/ai_gen.py clips --out $OUT`;
      **look at `$OUT/qa/ai_clips.jpg`** (4 frames per clip) and `reject` AC.. ids where the bag morphs, a hand looks wrong, or
      it looks AI. A failed still / clip is not remade unless the reserve covers it (one retry, same prompt, then give up).
      A submission answered with a preset recommendation instead of a job: send it again with `declined_preset_id` = that preset's id
      (the project never uses presets); a 429 rate limit: send it again.
   `render` applies the result by itself: a rejected or missing still gives its static back as the real-photo static it
   replaced, a rejected or missing clip is swapped for the block's real spare shot. The statics with AI scenes are rendered
   after step 2b.1-2 (so `render --only S` can wait for the stills while the videos wait for the voices and clips).
3. **Render** (statics: a few minutes in all; about 20-25 min per project of 4 versions, 2 videos at a time; a
   batch of 20 statics + 5 projects is about 2 hours; each ugc video also gets its scorecard, a few seconds), detached:
   `setsid nohup python3 pipeline/make_batch.py render --out $OUT > $OUT/render.log 2>&1 < /dev/null &`
   then check the log every couple of minutes until it prints `QA:`. More than 3 projects (every batch): render and
   upload the statics first (`render --only S`, `upload --only S`), then the videos (`render --only V`,
   `upload --only V`): the same folder (same batch). No progress messages: one reply at the end. Use a fresh `$OUT` for
   every request.
4. **QA:** Read `$OUT/qa/statics.jpg`, every `$OUT/qa/P*.jpg` (one per project: the 4 hooks side by side
   + the body + a 'body vs H1' number per version: under 10 = same body) and `$OUT/qa/report.json`. Captions
   sit at the bottom (white text with an outline, keywords on a red pill), jump to the top only for shots whose
   bottom shows a face or the product, and never sit over the end card (`"caption_zone": "reels"` in a spec keeps
   them higher, above Meta's strict Reels zone; `"caption_pos": "top"|"bottom"` on a segment forces a shot); under
   the narrator's "Here's <customer> …" the picture must show the product or that customer, never another person;
   one narrator voice per video. A new product's square photos and clips are shown whole (a white or blurred
   backdrop behind them: `"fit"`), never cropped to the middle. Text off-frame, wrong product, black frames, a
   face: fix a hook in its `..._P01_H3_...json` (only to fix a QA problem, never to change the length or format), a body problem in `$OUT/_before_hooks/<V01 spec>.json` then re-run
   `python3 pipeline/projects.py expand --out $OUT` (all 4 versions get it), and `render --only <id>`; or
   leave it out and say so. A face in a static or a failed render is never uploaded; length/anchor flags and
   `body differs from H1 (body match M …)` (that version's body is not its project's: look at its `qa/P*.jpg`,
   fix it as above or leave it) are uploaded and listed under QA flagged in the run report: mention them in the reply.
   **ugc videos:** `render` prints `scorecard P01H1: 63s · 201 wpm · speech 88% · longest pause 0.41s · shots 2.0s avg · -14.0
   LUFS LRA 2.1 · 0 repeats · 0 held cards · 11/12 targets met` per video (the same line is in the run report) and a miss is the
   soft flag `scorecard: ...` in `qa/report.json` (targets: 185-215 wpm, speech >= 85%, longest pause <= 0.8 s, first word <= 0.35 s,
   shots 1.4-2.6 s avg and none over 4 s, -14 LUFS +-1 with LRA <= 4, no repeated shot, no card held over 3.2 s). Look at the
   contact sheet: numbered captions ("1. ..."), a new picture about every 2 s that shows what is said (hands, zips, pockets), the
   same product throughout, no black frames. A miss is reported, never "fixed" by cutting the video (rule 6).
5. **Upload:** `python3 pipeline/make_batch.py upload --out $OUT` (no `--name`: the folder is `B045 – <date> – <product> – N statics + M
   projects`, made from the plan) → prints the Drive folder link (`drive_path`: where it landed), the batch id and the uploaded ads; once
   the whole batch is in Drive it also writes `<prefix>_ads.csv` there (one row per ad, an empty `launched` column for the media buyer)
   and adds the batch and its ads to the ad tracker sheet (`pipeline/tracker.py`, `tracker` in the output; it keeps everything the team
   typed there). The run report says `ad tracker NOT updated` when it failed: run `python3 pipeline/tracker.py sync --batch B045`.
   Higgsfield `balance` again.
6. **Reply** (one short message, the pipeline's format above): **batch id (B045) and Drive folder link** · the ad tracker link · any `repeat:` warning (an ad
   an earlier batch already had: say which) · statics one line each · videos
   one block per project · the ad copy file · plan warnings (fewer than 4 versions, openings already used in an
   earlier batch, a hook line opening 3+ versions, `thin script`, "needs a human" items) · QA flags · the scorecard (one line for
   the batch: how many ugc videos met the targets and the misses that repeat, e.g. "17 of 20 at 185-215 wpm; shots avg 2.7 s")
   · AI scenes (how many stills / clips passed the gate and shipped, which scenes, how many fell back to real photos / footage) ·
   music (the client's track or the generated bed; winners: the RAW's own sound) · credits used (balance before → after, voiceover + AI) ·
   anything skipped, failed or needing a human.
7. Commit the specs (JSON only, no media, no secrets) into the pipeline's folder:
   `python3 pipeline/make_batch.py specs --out $OUT --to pipeline/recipes/<winners|new_products|daily>/<plan YYYY-MM-DD>/<short-name>`,
   plus any new or changed product file (a new product's always changes: its `tests`), `pipeline/data/novelty_log.json` (upload
   adds the batch: the next batch avoids its scenes, photos, captions and hooks) and `pipeline/data/batch_ledger.json` +
   `docs/BATCHES.md` (the batch number and its ads: the next plan takes the next number and flags repeats); commit, push. The GitHub
   Action `merge-batches` then merges the batch branch into the default branch by itself (`pipeline/merge_batch.py`: batch output
   only; a branch that also changes code or docs is left for a person, so keep a batch's commit to its specs and data files).

**Music:** storyboard videos get a bed under the voice automatically: the client's licensed tracks from
`pipeline/assets/music/` when there are any, otherwise a generated bed (made by `pipeline/music.py`, nothing to
license). Winner videos keep their RAW's own sound.

## Footage library (the client adds clips)

New raw clips in the Drive library (`Raw files/<product>/...`) are not used until indexed: `python3 pipeline/index_library.py` (the
library cache), `python3 pipeline/footage_index.py select` (counts), `scan` (about 12 clips a minute: header, 4 frames, face / sharpness
checks; resumable; reads through the Drive API with the agent's token because the public link hits "Quota exceeded"), `merge` (the
clips that pass go into `pipeline/data/clip_index.json`, hand-tagged rows untouched), `stats`; commit `clip_index.json`. A clip with a
face, a soft or dark picture, under 720p or 2.5 s is `usable: no` (`why_not` says which). `sheets --product "Hobo Bag" --out DIR`
makes contact sheets of a sample to look at. **Labels** (what each frame SHOWS, so the b-roll matches the words: `shotmatch.py`): every
usable clip carries `moments` (tags per frame: snap, zip, side_zip, pocket, inside, packing, strap, worn, ...) in `clip_index.json`; a newly
merged clip has none until it is labelled: `python3 pipeline/footage_index.py label-sheets --out DIR` (contact sheets + a guide), hand the
sheets to labelling agents (one jsonl a clip, see `DIR/README.md`), `label-merge --dir DIR`, commit `clip_index.json`. Winner RAWs / finished ads (ACH Creative Delivery, Kate Creatives) are not b-roll.

## Other references

`docs/PLAYBOOK.md` (memory), `docs/NAMING.md`, `docs/CLIENT_GUIDE.md` (what the client can type),
`docs/SLACK_SETUP.md` (owner setup), `pipeline/data/products/README.md` (product files).

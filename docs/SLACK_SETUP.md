# Slack setup (owner, one time)

Goal: the owner (or the client) writes one line to Claude in Slack and gets finished ads in Drive. There is no
daily automatic run; every batch starts from a message. Two pipelines (`CLAUDE.md`): **winners** (new versions of
the weekly brief's winning videos) and **new products** (everything from a Drive `New Products` folder), plus
requests for the bags already on the site. Menu names in claude.ai can differ slightly from the words below. Docs:
https://claude.com/docs/claude-tag/admins/attach-to-scope ,
https://claude.com/docs/claude-tag/admins/customize , https://claude.com/docs/claude-tag/admins/set-spend-limit

## DM or channel

The owner uses a **Claude DM**. A DM runs on the Claude account of whoever sends it, so everything below must be
set up on that account:
- **Environment:** the sender's Claude Code environment (`libra ads`, step 1) with the Google keys and the setup
  script. A DM has no channel settings, so pick `libra ads` as the environment that account's DMs use (in
  Claude's Slack settings for your DMs, or as the account's default environment; check it once with the first test
  in step 5: the setup script must have run).
- **Connectors:** Google Drive and Higgsfield connected on the sender's account, and that account's Higgsfield
  connector with the image and video tools set to **Blocked** (step 2). The repo denies them too
  (`.claude/settings.json`), but the connector switch is the real guard.
- **Usage:** the work counts against the sender's own Claude plan and usage limits (a batch of 20 statics + 5
  projects keeps a session busy for about 2 hours), not against a channel's spend limit.
- **The repo in every DM:** a DM has no channel instructions, so each message names the repo: start it with
  `Higgsfield-test:` (e.g. `Higgsfield-test: new product ad sets`; the copy-paste lines are in
  `docs/CLIENT_GUIDE.md`). If a DM ever starts without the repo, write the full name
  `LibracasesAgent/Higgsfield-test` at the start. The account needs a seat with Claude Code and GitHub access to
  the repo. The repo's `CLAUDE.md` is the whole procedure.

A **channel** works too (step 3): Claude runs with the channel's settings (repo, instructions, environment,
connections) and the client needs no seat of his own. Channel work is billed to the organisation's usage
balance, so fund it and set a monthly limit.

## 1. Environment (claude.ai/code → your environment "libra ads")

- Network: Full (needs Google Drive, libracases.com for the built-in bags' prices and photos, Hugging Face for
  the speech model).
- Environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
  (use new ones: the old secret and token were visible in screenshots).
- Setup script (Slack sessions don't run the repo's startup hook):
  ```
  apt-get update -qq && apt-get install -y -qq ffmpeg poppler-utils
  pip install -q faster-whisper pillow numpy pillow-heif opencv-python-headless pypdf
  ```
  (`poppler-utils`' `pdftotext` reads PDF notes in a New Products folder, `pypdf` is the fallback; with neither a
  PDF note is skipped with a warning. `pillow-heif` reads iPhone HEIC photos.)
- Share the environment with the organisation, so a channel can use it.

## 2. Connectors and the credit block

- Google Drive and Higgsfield must be connected for the account (DM) or channel that runs the work.
- Higgsfield connector → tool settings (since 2026-10-20 the pipeline makes AI scene stills and short clips of the real
  bag, capped at 100 credits per batch, voiceover included): keep **Allowed**: generate_audio_batch, generate_audio,
  generate_image, generate_image_batch, generate_video, generate_video_batch, jobs_wait, balance, transactions,
  media_upload, media_confirm. Set everything else that generates to **Blocked**: execute_preset, ads_studio_generate,
  ai_influencer_generate, shorts_studio_create, motion_control, upscale_*, reframe, outpaint_image, remove_background,
  create_voice. The repo denies the blocked ones too (`.claude/settings.json`); `pipeline/ai_gen.py` plans only the
  scenes it lists in `ai_needed.json` and CLAUDE.md rule 1 says to make nothing else.

## 3. The channel (optional when you use DMs)

1. In Slack create a private channel, e.g. `#libra-ads`, and invite the client and the Claude app.
2. In Claude's Slack settings for that channel:
   - Repository: grant `LibracasesAgent/Higgsfield-test` (default branch `claude/loving-meitner-4amjii`).
   - Environment (Advanced): `libra ads`.
   - Connections: Google Drive and Higgsfield.
   - Respond automatically: off (Claude only works when someone writes `@Claude`).
   - Channel member edits: Block (the client can't change the instructions or the model).
   - Model (General tab): Claude Sonnet 5.5 (the scripts do the creative work; about 40% cheaper than Opus).
     Keep Claude Sonnet 5 enabled in the org: the permission checker runs on it.
   - Spend: fund the usage balance, set a monthly limit and a limit for this channel. Channel work is billed
     at API list price. Estimate on Sonnet (made for the older batch of 20 statics + 10 single videos): ~$1 per
     small request, ~$3-4 per batch, ~$120-150 a month for 5 batches a week; a batch is now 20 statics + 5
     projects (20 videos), so check the real spend per channel after the first one at
     claude.ai/analytics/claude-tag (daily) or claude.ai/admin-settings/usage/claude-tag.
3. Channel instructions (paste):
   > For every request use the GitHub repo LibracasesAgent/Higgsfield-test and follow its CLAUDE.md
   > exactly. Ads are made with pipeline/make_batch.py from real product photos and real footage. The
   > only Higgsfield calls allowed are text-to-speech voiceovers (generate_audio_batch), the AI scene stills
   > and clips that make_batch plan lists in ai_needed.json (generate_image_batch / generate_video_batch,
   > at most 100 credits per batch in total), jobs_wait, balance and transactions. Never any other AI
   > generation. Upload everything to Google Drive
   > Outputs with make_batch.py upload. Never publish, delete or move files. Don't ask questions: decide
   > sensibly and reply once with the Drive folder link, the ad list and the credits used.
4. Pin `docs/CLIENT_GUIDE.md` (or a copy of it) in the channel (or keep it next to the DM).

## 4. Drive

- Share `Ad Creative Pipeline / New Products` with the client as Editor (he drops product folders there; not
  `Outputs / New Products`, which holds the finished new-product ads).
- Share `Ad Creative Pipeline / Outputs` with the client as Viewer. The first winners upload makes
  `Outputs / Winners`, the first new-product upload `Outputs / New Products` (or point `outputs_winners_folder` /
  `outputs_new_products_folder` in `pipeline/config.json` → `drive` at existing folders).
- Ask the client to keep the n8n weekly brief writing into `Research Briefs` (the winners come from it).

## 5. First test (DM)

1. `Higgsfield-test: 2 statics and 1 video for the Hobo Bag` → about 25 minutes, Drive `Outputs / <date> – …`.
2. `Higgsfield-test: winners, 1 project and 1 static` → about 25 minutes, Drive `Outputs / Winners / <date> – …`.
3. Put a test folder in New Products, then `Higgsfield-test: new product <name>: 2 statics and 1 video` →
   Drive `Outputs / New Products / <date> – …`; the reply says "libracases.com not read".
4. After each: Higgsfield → transactions should show only "Voiceover" lines (a few credits). If you see
   image or video generations, the block in step 2 is not active for that account.

## 6. Security

- Rotate the Google client secret and refresh token, then update the three environment variables.
  If n8n uses the same Google OAuth client, re-authorise n8n right after.
- Make the GitHub repo private (check that the Claude GitHub app still has access afterwards).

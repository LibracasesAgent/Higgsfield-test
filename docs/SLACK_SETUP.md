# Slack setup (owner, one time)

Goal: the client writes one line in a Slack channel and gets finished ads in Drive. There is no daily
automatic run; every batch starts from Slack. Menu names in claude.ai can differ slightly from the
words below. Docs: https://claude.com/docs/claude-tag/admins/attach-to-scope ,
https://claude.com/docs/claude-tag/admins/customize , https://claude.com/docs/claude-tag/admins/set-spend-limit

## Why a channel and not DMs

A DM to Claude runs on the Claude account of whoever sends it: if the client DMs, he needs his own seat
with Claude Code, his own environment (Google keys) and his own Higgsfield and Drive connectors, and
every DM must name the repo. In a channel Claude runs with the channel's settings (repo, instructions,
environment, connections) and the client needs no seat. Channel work is billed to the organisation's
usage balance, so fund it and set a monthly limit.

## 1. Environment (claude.ai/code → your environment "libra ads")

- Network: Full (needs libracases.com, Google Drive, Hugging Face for the speech model).
- Environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`
  (use new ones: the old secret and token were visible in screenshots).
- Setup script (Slack sessions don't run the repo's startup hook):
  ```
  apt-get update -qq && apt-get install -y -qq ffmpeg
  pip install -q faster-whisper pillow numpy pillow-heif opencv-python-headless
  ```
- Share the environment with the organisation, so a channel can use it.

## 2. Connectors and the credit block

- Google Drive and Higgsfield must be connected for the account / channel that runs the work.
- Higgsfield connector → tool settings: set every image and video generator to **Blocked**:
  generate_image, generate_image_batch, generate_video, generate_video_batch, execute_preset,
  ads_studio_generate, ai_influencer_generate, shorts_studio_create, motion_control, upscale_*,
  reframe, outpaint_image, remove_background, create_voice. Keep allowed: generate_audio_batch,
  generate_audio, jobs_wait, balance, transactions, media_upload. The repo also denies these tools
  (`.claude/settings.json`), but written instructions alone did not stop a Slack session from making
  AI images once, so this switch is the real guard.

## 3. The channel

1. In Slack create a private channel, e.g. `#libra-ads`, and invite the client and the Claude app.
2. In Claude's Slack settings for that channel:
   - Repository: grant `LibracasesAgent/Higgsfield-test` (default branch `claude/loving-meitner-4amjii`).
   - Environment (Advanced): `libra ads`.
   - Connections: Google Drive and Higgsfield.
   - Respond automatically: off (Claude only works when someone writes `@Claude`).
   - Channel member edits: Block (the client can't change the instructions or the model).
   - Spend: fund the usage balance, set a monthly limit and a limit for this channel.
3. Channel instructions (paste):
   > For every request use the GitHub repo LibracasesAgent/Higgsfield-test and follow its CLAUDE.md
   > exactly. Ads are made with pipeline/make_batch.py from real product photos and real footage. The
   > only Higgsfield calls allowed are text-to-speech voiceovers (generate_audio_batch), jobs_wait,
   > balance and transactions. Never generate AI images or AI video. Upload everything to Google Drive
   > Outputs with make_batch.py upload. Never publish, delete or move files. Don't ask questions: decide
   > sensibly and reply once with the Drive folder link, the ad list and the credits used.
4. Pin `docs/CLIENT_GUIDE.md` (or a copy of it) in the channel.

## 4. Drive

- Share `Ad Creative Pipeline / New Products` with the client as Editor (he drops product folders there).
- Share `Ad Creative Pipeline / Outputs` with the client as Viewer.
- Ask the client to keep the n8n weekly brief writing into `Research Briefs` (the winners come from it).

## 5. First test

1. `@Claude make 2 statics and 1 video for the Hobo Bag` → about 15 minutes.
2. `@Claude new batch for the winners: 2 videos and 1 static` → about 25 minutes.
3. `@Claude new product <name>: 2 statics and 1 video` after putting a test folder in New Products.
4. After each: Higgsfield → transactions should show only "Voiceover" lines (a few credits). If you see
   image or video generations, the block in step 2 is not active for that account.

## 6. Security

- Rotate the Google client secret and refresh token, then update the three environment variables.
  If n8n uses the same Google OAuth client, re-authorise n8n right after.
- Make the GitHub repo private (check that the Claude GitHub app still has access afterwards).

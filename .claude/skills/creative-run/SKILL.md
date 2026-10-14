---
name: creative-run
description: Libra Cases ad requests from Slack or the Claude app (statics, videos, "new batch for the winners", "new product ..."). Use for any request to make, test or batch ads. Follow CLAUDE.md; never generate AI images or AI video.
---

# Libra Cases ad request

Follow `CLAUDE.md` in the repo root step by step. It is the only valid procedure:

- First tell the pipeline from the message (CLAUDE.md "Which pipeline?"): **winners** (`plan --pipeline winners`:
  the newest weekly brief's winning videos), **new products** (`plan --pipeline new-product --new-product
  "<folder>"`: everything from the product's Drive `New Products` folder, never libracases.com) or **catalog** (a
  built-in bag and/or a theme). No numbers = a batch: 20 statics + 5 projects x 4 hooks.
- Statics come from `pipeline/make_batch.py` (real product photos: libracases.com for the built-in bags, the
  client's folder for new products, + `brand_statics.py` layouts).
- Videos come from real footage (`storyboard.py` / `remix.py` via `make_batch.py`), with our voiceover.
- The only Higgsfield call in a normal run is text-to-speech (`generate_audio_batch`, text2speech_v2) for the
  lines in `tts_needed.json`. Never call generate_image, generate_video, presets, Ads Studio, AI influencer or
  any other image/video generator: they are switched off for this project and the results are not used.
- Everything is uploaded with `make_batch.py upload` into Drive Outputs (`Winners/`, `New Products/` or the
  Outputs root). Never publish, delete or move files.

There is no daily automatic run: every batch is started by a message in Slack (a DM or the channel).

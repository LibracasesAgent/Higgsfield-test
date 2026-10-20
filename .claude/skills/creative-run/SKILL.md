---
name: creative-run
description: Libra Cases ad requests from Slack or the Claude app (statics, videos, "new batch for the winners", "new product ..."). Use for any request to make, test or batch ads. Follow CLAUDE.md; AI only as the real bag in a new scene, only what `plan` lists in ai_needed.json.
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
- Higgsfield calls in a run: text-to-speech (`generate_audio_batch`, text2speech_v2) for the lines in `tts_needed.json`,
  and, when `plan` wrote `ai_needed.json`, exactly its scene stills (`generate_image_batch`, gpt_image_2_5) and clips
  (`generate_video_batch`) with the prompts it lists, then `ai_gen.py gate` / `clips` and a look at the contact sheets
  (CLAUDE.md section 5, step 2b). A batch is capped at 100 credits, voiceover + AI. Never presets, Ads Studio, AI
  influencer, characters, a face, any other model or a prompt of your own.
- Everything is uploaded with `make_batch.py upload` into Drive Outputs (`Winners/`, `New Products/` or the
  Outputs root). Never publish, delete or move files.

There is no daily automatic run: every batch is started by a message in Slack (a DM or the channel).

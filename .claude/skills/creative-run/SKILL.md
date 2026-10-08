---
name: creative-run
description: Libra Cases ad requests from Slack or the Claude app (statics, videos, "new batch for the winners", "new product ..."). Use for any request to make, test or batch ads. Follow CLAUDE.md; never generate AI images or AI video.
---

# Libra Cases ad request

Follow `CLAUDE.md` in the repo root step by step. It is the only valid procedure:

- Statics come from `pipeline/make_batch.py` (real libracases.com product photos + `brand_statics.py` layouts).
- Videos come from real footage (`storyboard.py` / `remix.py` via `make_batch.py`), with our voiceover.
- The only Higgsfield call in a normal run is text-to-speech (`generate_audio_batch`, text2speech_v2) for the
  lines in `tts_needed.json`. Never call generate_image, generate_video, presets, Ads Studio, AI influencer or
  any other image/video generator: they are switched off for this project and the results are not used.
- Everything is uploaded with `make_batch.py upload` into Drive Outputs. Never publish, delete or move files.

There is no daily automatic run: every batch is started by a message in Slack.

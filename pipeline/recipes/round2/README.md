# Round 2 — more UGC formats (13.2 credits)

Videos: stop-motion unboxing (4 AI stills + click SFX + real clips), "POV: your old bag" vs this one
(AI generic-tote rummage + real clips + AI cafe), brown-or-black poll (real clip + Kling colour swap + split screen).
Statics: text-message thread, search bar, brown/black split, 4-frame unboxing grid, old bag vs this one.

AI inputs (Higgsfield job ids): oldbag.png d0dfa857, unbox1-4 6af8d006 / 1998ed13 / cf219a07 / ceb49f93,
cafe.png e3e8cbbd (gpt_image_2_5 2K low, 0.5 each); oldbag.mp4 d0d10627, cafe.mp4 ef57919e
(seedance_2_0_mini 5 s, 5 each); vo_oldbag.mp3 0c56ed80, vo_poll.mp3 f1d001bc (elevenlabs Maeve).
click.wav: ffmpeg pink-noise burst. split.mp4: brown.mp4 over black.mp4 (vstack).

Drive note: whole-file downloads (and ranges of a few MB) of the shared library files started returning
"Quota exceeded" after repeated reads; 1 MB ranges worked until the per-file quota tightened further.
recut.py now caches each clip once per session via 1 MB range requests.

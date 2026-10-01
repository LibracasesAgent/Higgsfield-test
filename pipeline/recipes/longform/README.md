# 60-second ads (client feedback: winners run 50 s - 1:25; ours were too short)

Built with `pipeline/longform.py`: base cut (recut.py) -> word-level captions with red keywords -> labels,
real review cards (pipeline/data/reviews.json), 50% OFF + free wallet offer card, end card.

Winner anatomy measured from the client's own library: 172-H4 = 50 s / 29 cuts (1.7 s per shot), 123-H4 = 81 s / 44 cuts.

- testA_remix172.json (57 s): client's textless 172 RAW creator footage (Drive 1YrDKa4bX4W...), cold-open hook from her
  own line ("biggest regret? not buying it sooner"), reasons 1-3 unchanged, new review section (Maeve VO quoting
  Carol R. / Beverly D. / Felicia S. verbatim, job 659e581a), offer + end card. ~0.45 credits.
  NOTE: keeps the creator's existing claims (locking zips, card-scanner lining, cut-proof strap, "anti-theft") —
  client must confirm they are still true.
- testB_ai_presenter.json (56 s): persona 3 (AI) — 3 Kling pro 1080p talking shots (a80c81ef hook, a0073826 "number three",
  233e478c CTA; 12.5 each) from gpt_image_2_5 2K-high frames (15f1597c, e63a4a01, cef7b1ca; 2.75 each), narration in a
  clone of her voice (element 241459b6, 40 credits one-time), real 4K B-roll (zip pulled down = fixes the zipper note),
  3 real review cards, offer + end card. Presenter-safe script (no ownership/experience claims).
Sources referenced by full path under pipeline/cache/media/ (gitignored; re-cache with recut.source()).

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

## gift_angle.json — "The gift she'll actually use" (62 s, 1.35 credits)
New angle (no discount, no listicle): Christmas gifting. ~90 % real library footage of real women receiving/unboxing the bag:
black_gift = 18all7GUEBLsxxS0JCAl8t-yEOsC6r52T (birthday gift + hug), testi_blue = 1B_A8E6o9m6B4sNNiDeSS81TdU_oEeu9i
("If you're looking for a thoughtful gift..."), unbox_novoice = 1rRkDw8UM4ZlQpO3c6Bv3_gT1_1-n8qYH, testi_black =
11yX8EI6ZI6Ewyc-Io7PfrwC12vTVUEGY (opens it as a gift, real voice), unbox_brown = 1wE0AQvyBkxmh0-_ftpXmjG4v-pHMMPfG,
black_detail = 1no4sfl12SIUF-IWkBX4Xo2ri58deQxsx. Local names are symlinks into pipeline/cache/media/.
Brand-narrator lines in the persona-3 clone (0bd256df, cd5fd094, 6d76c17c, 3813d9d9, 5616d6bf). Real review: Felicia S.
Edited out her "anti-theft" / "pickpocketers" lines (unconfirmed claims). Mentions the free wallet, not the 50 % discount.

## bag_swap — "The Bag Swap" (53 s, 19.65 credits): organisation angle, semi-AI / semi-real
Visual hook in the first second: AI transformation (kling3_0 pro 5 s, start_image 92af4a1e messy black tote with spilled items ->
end_image 2345a92e tidy Libra Hobo; job 21d93c1c; clip trimmed to start at 1.9 s where the motion begins).
Then B&W problem (AI oldbag + still), item -> pocket tags over real footage (back pocket, keys into gold side zip, items into main
zip, zip pulled shut), two real lines from the gift testimony (both side zips; interior pockets), real reviews Margie B. + M B.,
persona-3 CTA reused from Test B. Narration: persona-3 clone (86d5bb24 ... aa88f408).
bag_swap_build.py rebuilds the audio track + swap.json (run it in a folder with the media symlinked as in the script).
Fixes made here: amix duration=longest (hook narration was being cut), captions now use whisper small.en.

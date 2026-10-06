# Libra Cases ad playbook (the memory of how this was built)

Read this before making any ad. It holds everything learned while building the pipeline and the
first 40-ad test run (2026-10-02): what the client wants, what worked, exact recipes, scripts,
and every bug we hit and how it was fixed. `CLAUDE.md` is the short checklist; this is the detail.

---

## 0. Lesson from the first Slack run (2026-10-06)

A Slack session that did not use this repo spent ~160 credits on GPT images, Seedance and 10 s Kling
clips and produced dark, off-brand ads. The client's look is: real product photos + real footage,
cream/white brand layouts, captions, review cards, offer and end card. That is why `CLAUDE.md` now
forces `pipeline/make_batch.py` (templates, no AI images/video) for every normal request.

## 1. Client and brand

- **Client:** Libra Cases (owner Wouter). DTC handbags sold on libracases.com, ads on Facebook/Instagram.
- **Products and facts (from the site, 2026-10):**
  | Product | Price (was) | Colours | Key claims |
  |---|---|---|---|
  | Luxury Leather Hobo Anti-Theft Handbag ("Hobo Bag") | $52.50 ($105) | Brown, Black, Blue, Grey, Burgundy, Red | hidden anti-theft back pocket, smart compartments, soft water-resistant scratch-proof leather, 2 adjustable straps (handbag / shoulder / crossbody), free matching pouch wallet, free US shipping, 1-year warranty, easy returns |
  | Hobo 2.0 "6-Layer Security Edition" | $79.95 ($159.90) | Black, Brown (Beige sold out) | RFID protection, lockable zippers, cut-resistant strap, hidden pockets, smart compartments, table security strap |
  | Hobo Bag 3-Piece Set | $69.95 | Brown, Black, Blue, Grey, Purple Red, Red | hobo + crossbody + matching pouch |
  | Slouchy Soft 3-Piece Set | $69.95 | | |
  | Vintage Bag | $44.95 | Ginger Brown, Black, Chocolate, Red | one-hand clasp, compartments, adjustable/removable strap |
  Always re-check with `pipeline/site_assets.py` (prices change).
- **Offer:** 50% off + free matching pouch wallet + free US shipping. Site banner: "FINAL CLEARANCE SALE
  ENDS TODAY 50% OFF + FREE SHIPPING".
- **Approved by the client (allowed in ads):** the 50% offer, "anti-theft", the Susan / workshop-closing /
  arthritis story used in his own RAW ads, all 10 customer reviews with names ("Yes on all"), plus the two
  reviews on the website (Jenny H., Sarah M.). "Use everything on libracases.com."
- **Never:** invent claims or reviews; AI people saying "I bought / I love mine" (presenter only); faces in
  statics.

## 2. What the client told us (feedback history, newest last)

1. Statics: no human faces, product only (hands OK). Clean, well-designed Facebook-ad look.
2. Wants UGC-style videos, not studio films; AI UGC that hooks well.
3. "Yes on all" to showing the 10 customer reviews with names.
4. "The quality is definitely too low." Cause: 720p AI clips, low-quality start images, 8 Mbps exports.
   Fix that worked: real 1080p/4K library footage, site photos for statics, Kling **pro** (1080p) for AI,
   GPT image **high** for AI stills, exports at CRF 17 / ~10-14 Mbps.
5. Videos too short: winners run **50 s to 1:25**. Target ~1 min with more elements (hook, labels, tags,
   reviews, real customer clips, offer card, end card). Statics "look acceptable".
6. The zipper didn't move in an early AI ad: AI hands/zips are unreliable, use real footage for mechanics.
7. Wants new angles, not only "50% off". Liked the gift angle. Asked for semi-AI / semi-real with a strong
   visual hook in the first second (Bag Swap was made for that).
8. Facebook Ads Library formats he runs: product hero, bag + pouch set, bold "Selling out for the 7th time"
   text with colour dots, branded promo frame card, lifestyle photo, Black Friday static; mostly videos.
9. Wants ~200+ ads a week (40/day), budget 1,400 Higgsfield credits a week (~200/day). Wants one-line
   requests (Slack DM) or a daily automatic run, with output saved into Drive as Statics / Videos folders.

## 3. The 2026-10-02 test run (reference for every format)

Specs: `pipeline/recipes/daily/2026-10-02/` (`statics.json`, `V01..V20_*.json`, `ads_meta.json` = angle per ad).
Delivered: Drive Outputs / "oct 3 test" / Statics (22 files) + Videos (20). Cost: **67.3 credits** for all 40.

| Ads | Type | Engine |
|---|---|---|
| S01-S20 | statics (hero, promo, callouts, carousel, bold, colours, reviews, compare, lifestyle, trust, before/after, AI flatlay) | `brand_statics.py` |
| V01-V08, V20 | winner variations of RAW ads 94-H4, 148-H5, 121-H2, 147-H1, 158-H2, 139-H4, 123-H4, 33-H5, 113-H2 | `remix.py` |
| V09-V18 | new angles: Vintage showcase, 3-Piece "which would you choose", Hobo 2.0 "would you try", travel Bag Swap, gift for mum, reviews compilation, colour pick, feature walkthrough, AI presenter, what fits | `storyboard.py` |
| V19 | premium Hobo 2.0 film (23 s) | `premium.py` |

## 4. Recipes

### 4a. Winner variation (`remix.py`)
1. Pick a winner from the brief (top ROAS). Its RAW Drive id is in `pipeline/data/clip_bank.json`
   (`winner_raws`), with cold-open times, cut ranges and the review insert point already worked out.
   New winners: find the RAW in the library (names like `MAX-94-H4`), transcribe it.
2. **Cold open:** a 2-7 s line from later in the RAW that works alone as a hook ("Most bags look terrible
   after a year. Mine looks better after a decade."). Add `hook_label` (2-4 words, e.g. "10 YEARS LATER").
3. **Cuts:** drop slow or repeated parts (keep sentences whole; cut on word boundaries from the transcript).
4. **Reviews section** inserted just before the offer: a review VO (narrator Maeve) over real B-roll, with
   review cards synced to each name. Opening lines that work: "Don't just take her word for it." (after a
   woman speaking), "And customers agree.", "Here's what customers are saying."
5. **Labels** from RAW words ("REASON 1-5", "STEP 1-3"): match the word without punctuation ("one", not "one,").
6. Offer card at the first "50" after the insert (`offer_after` if the offer comes earlier). End card auto.
7. RAW with burned-in captions (121-H2): `burned_captions: true` (ours are skipped).
8. Target 45-90 s.

### 4b. New-angle video (`storyboard.py`)
Blocks in order: `{"vo": file, "broll": [[src, start, weight], ...]}` (VO length split over the clips by
weight; set weights to the word timings so the picture matches the words), `{"clip": src, "range": [a,b]}`
(real clip with its own audio, e.g. customer testimony), `{"clip":..., "mute": true}` (silent visual),
`vo_range` to use part of a VO file, `cutaway` to J-cut away from an AI face. Overlays anchor to words.
Formats that worked (scripts in section 5):
- **Showcase** "Take a closer look at the …" + a real customer clip + colour run (V09).
- **Which would you choose?** set pieces + reviews + colour run with swatch frames (V10).
- **Would you try …?** feature tags per spoken feature + a site review card (V11, 35 s is fine for this).
- **Travel / Bag Swap:** AI mess-to-tidy transform hook, then item → pocket tags, real customer (V12).
- **Gift:** "Still trying to figure out what to get your mum this Christmas?" + real gift reactions + Felicia's
  "for my daughter for Christmas" review (V13).
- **Reviews compilation:** 6 named reviews + real customer unboxing clips (V14).
- **Colour pick:** "Be honest. Which colour are you?" with swatch frames + tags (V15).
- **Feature walkthrough** on 4K macro clips with tags (V16).
- **AI presenter:** Kling hook ≤ 2.75 s on face then cutaway, body over real footage, Kling CTA at the end (V17).
- **What fits:** packing shots + the site's "what fits" infographic padded to 9:16 (V18).

### 4c. Statics (`brand_statics.py`)
Layouts: `hero`, `promo` (badge), `callouts`, `review`, `compare`, `colours`, `bold` (+ colour dots),
`lifestyle` (photo + panel), `carousel` (A/B/C cards), `split` (before/after). 1080x1350.
- Photos from `site_assets.py`. Image 00 usually has "BEST SELLER" / "CLEARANCE SALE" badges: use a later
  image, or `masks` (the badge rect is covered by the area just below it). A faint ghost of the round
  clearance badge stays even after masking: use another image for heroes.
- Grey or textured site backgrounds: hero uses multiply blend after whitening; textured backdrops go in
  `card_photos` (shown as a framed card).
- Review static: `review_n` from reviews.json, or `quote` + `author` (never put the file name as author).

### 4d. AI shots (Higgsfield)
- Upload the site photo padded to 9:16 (`media_upload` → PUT with headers `Content-Type` and
  `If-None-Match: *` → `media_confirm`).
- `kling3_0`, `mode: pro`, 5 s, 9:16, `start_image`. Prompt pattern: "Premium studio product film. The
  [colour] leather hobo shoulder bag … Slow, smooth camera push-in … The bag keeps its exact shape,
  stitching, strap and hardware. No people, no text, no morphing. Crisp 1080p detail." 12.5 credits.
- AI presenter: `sound: on`, persona frames `15f1597c-7157-475e-a3e8-bdac7241b197` (hallway) /
  `e63a4a01-3ee9-496f-bd14-521bf8aa6ba8` (living room) / `cef7b1ca-651b-47eb-a62b-3b36041a133b` (street);
  one short line in quotes in the prompt; check with `pipeline/lipsync_check.py`; the bag often morphs after
  ~3 s, so cut away early.

### 4e. Premium film (`premium.py`)
Grade `none`, grain 0. Light-background shots need dark titles (`#2a1f18`) placed below the bag (y≈1600);
light titles only over darker footage. End on a clean studio shot so the CTA pill is readable.

## 5. Scripts and voice

Style: short spoken sentences, concrete features, one idea per line, end with the offer and "Tap the link
below." Brand voice element `241459b6-…`; review narrator preset Maeve `64cf4f1a-…` (CLAUDE.md §5).
Examples that were used:
- "Take a closer look at the Vintage Bag. A clasp that snaps shut with one hand. Open it up and there's room
  for your phone, wallet and keys, all in their own spot."
- "Which Hobo Bag three-piece set would you choose? Every set comes with three pieces: the hobo bag, a
  crossbody, and a matching pouch."
- "Would you try Hobo 2.0? It looks like a classic leather hobo bag, but look closer. Lockable zippers so
  nobody can open it in a crowd. An RFID lining that blocks card scanners."
- "Travel day is where a bottomless bag really hurts. Passport? Back pocket, flat against you. Keys and
  phone, the gold side zips…"
- "Still trying to figure out what to get your mum this Christmas?" / "Most gifts end up in a drawer. This
  one, she'll carry every single day."
- "Be honest. Which colour are you? Brown: warm, classic, goes with everything…"
- Offer close: "It arrives with a free matching pouch wallet, and it's fifty percent off right now. Tap the
  link below."
Write "fifty percent" in TTS text (spoken correctly); captions turn it into "50%".
**Themes:** apply to hook, headline, offer wording and end card. Black Friday: "Black Friday: 50% off + free
wallet", "Our biggest sale of the year", urgency lines ("ends tonight": 113-H2 is the best winner for this),
dark/bold statics (`bold` layout, red accent). Christmas/Mother's Day: gift angle (V13 recipe).

## 6. Quality checklist (each item was a real bug once)

| Check | Bug we had | Fix in place |
|---|---|---|
| Labels/tags inside the frame | long labels clipped | auto-shrink in `longform.py` |
| Captions to the last word | whisper dropped a closing sentence | `condition_on_previous_text=False` |
| Caption spelling | "Hobo 2 0", "XA", "have mercy", "50 %" | `CAPTION_FIX` + "%" glue in `longform.py` |
| No old captions flashing at cuts (burned-caption RAWs) | 0.25-0.5 s flash | cut ≥0.3 s before the next burned caption appears |
| Offer card not over a face | covered AI presenter | drop the offer card when the speaker says the offer |
| Titles readable | cream text on white | dark titles on light shots |
| Graphics not cropped | square infographic cut to 9:16 | pad onto a 9:16 background |
| Clip audio | Hobo 2.0 zipper clip has an unrelated TV ad | mute flags in `clip_bank.json` |
| Silent talking clips | lips moving under another voice | keep such shots ≤1.8 s |
| Statics author line | file name printed as author | use `author` |
Always look at a contact sheet of every video and a grid of every static before upload.

## 7. Technical gotchas

- **Drive:** whole-file or multi-MB downloads of library files hit "Quota exceeded"; `recut.source()` uses
  1 MB ranges and caches. Upload with `drive_upload.py` (OAuth env vars), never the Drive connector (it
  can't carry big files).
- **Rendering:** ~10-12 min per video on 4 cores (whisper + 4K decode + slow x264). Run queues detached
  (`setsid nohup … &`): background shell jobs are killed after 2 hours. Two renders can share a folder now
  (per-PID temp names), but run at most 2 at once.
- **Higgsfield:** `use_unlim:false` always; batch tools max 12 per call; jobs_wait to poll; TTS rate limit
  (429) → resubmit the failed ones; preset "IN THE DARK" → `declined_preset_id`. MCP connectors sometimes
  disconnect: reload tools and continue.
- **Costs (credits):** TTS 0.15-0.45/line; Kling pro 5 s 12.5; Kling pro 5 s with sound ~12.5-15; GPT image
  2K high 2.75; voice clone 40 (one-time). Real-footage edits cost nothing. 40 ads ≈ 70-200 credits.

## 8. Reply format (Slack / app)

One short message: Drive folder link; one line per ad (name, angle, length); credits used (balance before
and after); anything skipped, failed or needing a human (e.g. "V17 has an AI presenter: turn on Meta's
AI label").

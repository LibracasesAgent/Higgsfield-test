# Libra Cases ad playbook (the memory of how this was built)

Read this before making any ad. It holds everything learned while building the pipeline and the
first 40-ad test run (2026-10-02): what the client wants, what worked, exact recipes, scripts,
and every bug we hit and how it was fixed. `CLAUDE.md` is the short checklist; this is the detail.

---

## 0. Lesson from the first Slack run (2026-10-06)

A Slack session that did not use this repo spent ~160 credits on GPT images, Seedance and 10 s Kling
clips and produced dark, off-brand ads. The client's look is: real product photos + real footage,
cream/white brand layouts, captions, review cards, offer and end card. That is why `CLAUDE.md` now
forces `pipeline/make_batch.py` (templates, real photos and footage; AI only as the real bag in a new scene, section 4e) for every normal request.

## 1. Client and brand

- **Client:** Libra Cases (owner Wouter). DTC handbags sold on libracases.com, ads on Facebook/Instagram.
- **Products and facts (from the site, 2026-10):**
  | Product | Price (was) | Colours | Key claims |
  |---|---|---|---|
  | Luxury Leather Hobo Anti-Theft Handbag ("Hobo Bag") | $54.95 ($109.90) since 2026-10-27 (the owner's price change: ads made before it that print a price are out of date) | Brown, Black, Blue, Grey, Burgundy, Red | hidden anti-theft back pocket, smart compartments, soft water-resistant scratch-proof leather, 2 adjustable straps (handbag / shoulder / crossbody), free matching pouch wallet, free US shipping, 1-year warranty, easy returns |
  | Hobo 2.0 "6-Layer Security Edition" | $79.95 ($159.90) | Black, Brown, Beige (Beige was sold out in early Oct, back on the site by 10-09; `plan` reads the colours from the site) | RFID protection, lockable zippers, cut-resistant strap, hidden pockets, smart compartments, table security strap, 2 straps: a handbag strap and a crossbody strap (owner 2026-10-26) |
  | Hobo Bag 3-Piece Set | $69.95 | Brown, Black, Blue, Grey, Purple Red, Red | hobo + crossbody + matching pouch |
  | Slouchy Soft 3-Piece Set | $69.95 | | |
  | Vintage Bag | $44.95 | Ginger Brown, Black, Chocolate, Red | one-hand clasp, compartments, adjustable/removable strap |
  Always re-check with `pipeline/site_assets.py` (prices change). New products (Drive `New Products` folders) are
  the exception: their price, offer, colours and features come only from the client's folder notes (section 11).
- **Offer (per product, 2026-10):** Hobo Bag 50% off + free matching pouch wallet; Hobo 2.0 50% off + free pouch
  wallet; Vintage 50% off (no gift); Hobo 3-Piece Set and Slouchy Set 60% off ($69.95 vs $174.88; the pouch is one of
  the three pieces, not a gift). Free US shipping store-wide (the built-in bags; a Drive-only new product's ads
  say it only when its notes do: `compliance.drive_only`). Site banner: "FINAL CLEARANCE SALE ENDS TODAY 50% OFF +
  FREE SHIPPING". `make_batch.py plan` reads the % and the gift from the site on every run.
- **Black Friday Sale 2026 (Wouter, 2026-10-23; `data/campaign.json`, section 4f):** live 23 October - 30 November (Cyber
  Monday); up to 50% off sitewide; 60% off bundles (2 or 3 bags together, off the regular price); free gifts while stocks last:
  2 bags = a free mirrored jewellery box (worth $19.95), 3+ bags = + a free cosmetic bag (together worth $44.90); only bags count.
  Site banner 2026-10-23: "EARLY BLACK FRIDAY: 50% OFF EVERYTHING | BUY 2 BAGS = 1 FREE GIFT | BUY 3 = 2 FREE GIFTS".
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
   Fix that worked: real 1080p/4K library footage, site photos for statics, exports at CRF 17 / ~10-14 Mbps.
   (The 10-02 test also used Kling pro and GPT image high for free-form AI shots: historical. Since 2026-10-20 only the real bag in a new scene, section 4e.)
5. Videos too short: winners run **50 s to 1:25**. Target ~1 min with more elements (hook, labels, tags,
   reviews, real customer clips, offer card, end card). Statics "look acceptable".
6. The zipper didn't move in an early AI ad: AI hands/zips are unreliable, use real footage for mechanics.
7. Wants new angles, not only "50% off". Liked the gift angle. Asked for semi-AI / semi-real with a strong
   visual hook in the first second (Bag Swap was made for that).
8. Facebook Ads Library formats he runs: product hero, bag + pouch set, bold "Selling out for the 7th time"
   text with colour dots, branded promo frame card, lifestyle photo, Black Friday static; mostly videos.
9. Wants ~200+ ads a week (40/day), budget 1,400 Higgsfield credits a week (~200/day). Wants one-line
   requests (Slack DM) or a daily automatic run, with output saved into Drive as Statics / Videos folders.
10. **Julian (media buyer), 2026-10-09, on the first AI batch** (and what the pipeline does about it since):
   - Statics: good potential (bottom of funnel; a Hobo Bag static performs). More space between headline and sub,
     smaller headline, bigger small text, nothing crowded, no letter touching the line below -> brand_statics type
     rules; the Hobo Bag cycle leans on offer / stars / checklist.
   - Video cadence: never cut a line before the speaker finishes; the hook and the CTA finish; every cut on a sentence
     end -> remix/storyboard cadence checks, HOOK_PAD / END_PAD, a 0.5 s breath after a customer's clip (CLIP_PAD).
   - Never switch point of view: no second narrator reading reviews inside Susan's RAW (winner bodies play intact;
     `--winner-reviews` only on request); one brand voice per storyboard, a real customer only in her own introduced
     clip, never as muted B-roll while she talks. Agencies split-test hooks/CTA on a proven body: keep bodies intact.
   - Captions at the bottom (centre y 1380, text ~1295-1465: above Stories' UI, inside Feed's 4:5 crop) in a native
     style (white, dark outline, soft shadow, keywords on a red pill), moved to the top band only for shots whose bottom
     band shows a face or the product (YuNet + saliency, `longform.busy_shots`; owner 2026-10-12: "captions obstruct the
     video"); `"caption_zone": "reels"` = Meta's strict Reels zone (~1065-1235) when only Reels is bought;
     phrases kept together, no stray dashes, fuller phrases (up to 8 words; the hook one caption, up to 10 words, a bit
     smaller when it must), never over the end card; the words come from the script / committed transcripts, not from
     transcribing the mix.
   - Pacing: a new shot every 3-5 s (a customer's long clip changes framing every ~3 s); ~1 min middle/bottom of
     funnel, 1.5-2 min for storytelling (`--story`).
   - A video without music felt off -> storyboard videos get a music bed (`pipeline/music.py`).
   - Names always contain the product (LC_ naming). Wouter: ad copy too (`ad_copy.csv`, section 10).
   - Compliance: AI is fine, never health/medical claims, prescription drugs, politics, religion, blood (section 9),
     not even inside the client's own RAW audio.
   - The one first-batch video with spend: V09 Vintage showcase (ROAS 1.54): the `showcase` format starts from it.
11. **Owner, 2026-10-13** (uses a Claude DM): two pipelines that feel separate. **Winners** (new projects from the
   weekly brief's winning videos: works well; every winner project must have 4 hook versions) and **new products**
   (the client drops a folder into Drive `New Products` and writes one sentence, "new product ad sets"; everything
   comes from that folder, libracases.com is no longer read for them). No numbers = a batch: 20 statics + 5
   projects x 4 hooks = 20 videos; numbers given override. What was built: section 11.
12. **Owner, 2026-10-14** (his lead measured the clients' top-impression ads, 3 reference videos and 75 Ad Library cards,
   against our Hobo videos): our videos are slower, quieter and more list-like than the ads that win impressions. Decisions:
   scripts in "you" form ("you stop worrying in crowds": direct address, never an invented first-person customer
   experience; a first-person switch may exist but is off by default and is not built), length 55-80 s, and the new format
   becomes the default storyboard video. What was built: section 12.

## 3. The 2026-10-02 test run (reference for every format)

Specs: `pipeline/recipes/daily/2026-10-02/` (`statics.json`, `V01..V20_*.json`, `ads_meta.json` = angle per ad).
Delivered: Drive Outputs / "oct 3 test" / Statics (22 files) + Videos (20). Cost: **67.3 credits** for all 40.

| Ads | Type | Engine |
|---|---|---|
| S01-S20 | statics (hero, promo, callouts, carousel, bold, colours, reviews, compare, lifestyle, trust, before/after, AI flatlay (historical, not allowed now)) | `brand_statics.py` |
| V01-V08, V20 | winner variations of RAW ads 94-H4, 148-H5, 121-H2, 147-H1, 158-H2, 139-H4, 123-H4, 33-H5, 113-H2 | `remix.py` |
| V09-V18 | new angles: Vintage showcase, 3-Piece "which would you choose", Hobo 2.0 "would you try", travel Bag Swap, gift for mum, reviews compilation, colour pick, feature walkthrough, AI presenter (historical, not allowed now), what fits | `storyboard.py` |
| V19 | premium Hobo 2.0 film (23 s) | `premium.py` |

## 4. Recipes

### 4a. Winner variation (`remix.py`)
1. Pick a winner from the brief (top ROAS). Its RAW Drive id is in `pipeline/data/clip_bank.json`
   (`winner_raws`), with cold-open times, cut ranges and the review insert point already worked out.
   New winners: find the RAW in the library (names like `MAX-94-H4`), transcribe it.
2. **Cold open:** a 2-7 s line from later in the RAW that works alone as a hook ("Most bags look terrible
   after a year. Mine looks better after a decade."). Add `hook_label` (2-4 words, e.g. "10 YEARS LATER").
   **Every winner RAW needs 4+ distinct cold opens** (one project = H1-H4; 2026-10-13: 148, 121 and c9 got a 4th,
   113 a 3rd spoken one plus a label variant): on word boundaries, starting after final punctuation, ending at
   least 0.3 s before the next word, edges in real silence and just after a shot change (no mid-blink first frame,
   no burned-caption flash), with a label that repeats or paraphrases the RAW. Only when a RAW has no 4th clean
   spoken opening (113-H2, 16 s): an existing opening under another label and type, marked `"variant": "label"`;
   `projects.expand` picks it last (never H1, whatever the `--seed`) and warns "H<j> differs from H<i> by its
   on-screen hook only".
3. **Cuts:** drop slow or repeated parts (keep sentences whole; cut on word boundaries from the transcript).
   **Claim cuts** (`claim_cuts`): a health claim inside the proven body is cut out, on word boundaries and in
   silence, with a 0.6 s beat after it (Julian's rule, section 9): 94 "an adjustable strap[ that prevents shoulder
   pain.]", 86_2 "adjustable strap[ that prevents pain.]" and its "the strap hurts your shoulder" exchange. Plan and
   the run report list each claim cut for a human to listen to once; a RAW whose body still makes a health claim is
   left out of the batch (unmatched) until it has one (`winner_prep.py --check` warns).
4. **Proven body intact (default since 2026-10-09):** no review section, no second voice: one speaker, the RAW as
   the client proved it (only its editorial and claim cuts, a new cold open, offer card and end card). The old
   **reviews section** (`plan --winner-reviews`, only when a request asks for it): a review VO (narrator Maeve) over
   real B-roll before the offer, review cards synced to each name ("Don't just take her word for it.").
5. **Labels** from RAW words ("REASON 1-5", "STEP 1-3"): match the word without punctuation ("one", not "one,").
6. Offer card at the first "50" after the insert (`offer_after` if the offer comes earlier). End card auto.
7. RAW with burned-in captions (121-H2): `burned_captions: true` (ours are skipped).
8. Target 45-90 s (a winner runs as long as its body).
9. Captions come from the RAW's committed transcript through the edit (punctuated sentences, nothing transcribed
   again). Cold opens whose words name a health condition ("The arthritis has won.") are used last (H4), never H1, and
   listed for a human; a cold open with a health claim is never used, and no on-screen label names a condition (that
   cold open is labelled "HER LAST COLLECTION"; a medical label is skipped and `winner_prep.py --check` warns). Winners
   keep the RAW's own sound (most RAWs have their own music bed); a RAW without one gets a soft bed (`music.py`).

### 4b. New-angle video (`storyboard.py`)
**Since 2026-10-14 the default storyboard video is the ugc format (section 12: "mode": "ugc" specs, scripts from
`ugc_script.py`); the formats below are what `plan --classic` (and `--story`) still make, byte for byte as before.**
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
- **AI presenter (V17, historical: not allowed).** CLAUDE.md hard rule 1 allows AI only as the real bag in a new scene; no AI presenter or person, never remake it.
- **What fits:** packing shots + the site's "what fits" infographic padded to 9:16 (V18).
- **Story** (`plan --story`, or a request that asks for a story / long video): 1.5-2 min, QA 60-130 s: every feature,
  the real customer in full, the colours, as many reviews as fit, the offer. It runs as long as the real material
  allows (Hobo Bag ~105 s, Vintage ~75 s; a bag without customer clips ~45-55 s: plan warns, add `--lines` or use the
  showcase).
- **New product** (no reviews, no customer clips yet; 2026-10-13): one angle per project on the same true material,
  each with its own opening shot, feature order and label: `features`, `colours` (named swatches, needs 3+ matched
  packshots), `showcase` (detail photos first), `lifestyle` (worn photos first, "STYLE IT"), `offer` (the deal
  first, the packshots; only with a deal). The client's square photos and clips are framed whole (`"fit"`, section 11;
  under the close at `fit_y` 0.30, above the end card). It says every feature line it has (3-7; with 7 the videos
  plan ~42-45 s). Its H2-H4 hooks add POV / question openings made only from its own feature words ("Need room for
  your phone, wallet, keys ...?", "POV: one bag for nights out, office days ..."); a feature hook never repeats a
  line of the body's first ~12 s, opens on its feature's own footage when the body does not show it, and never on
  a body shot or spare (`projects.body_shots` counts the spares: a spare used as an opening made the body differ).
Rules since Julian's feedback (2026-10-09), enforced in `make_batch.py` / `storyboard.py` / `projects.py check`:
- **No talking B-roll:** a real customer's own clip is her scene only (introduced by the narrator, with sound); no
  B-roll pick is a moment where someone talks (committed transcript). `projects.py cadence` audits every pick.
- **Pacing:** no B-roll shot over 4 s, no picture over 5 s: a customer's long clip changes framing about every 3.2 s on
  her pauses (wide / closer on the bag / closer on her, the sound runs on); at most 2 shots of one clip per block, 4 s
  apart, the second one closer.
- **Handoffs:** 0.5 s between a customer's last word and the narrator's next line.
- **Colours:** every site colour has a swatch (a packshot with a sale badge gets it painted out: `site_assets.
  badge_free`) and the names are said in swatch order, each swatch timed to its name.
- **Captions** use the script on the voiceover's word timings and the clips' committed transcripts ("Hobo Bag", not
  whisper's "phobo bag"; "50%" for "fifty percent").
- **Music:** a bed under the voice (`pipeline/music.py`): the client's licensed tracks in `pipeline/assets/music/` if
  any, else a generated soft groove (synthesised, nothing to license), -15 dB and ducked while someone speaks; the
  4 versions of a project share it. `plan --no-music` for none.

### 4c. Statics (`brand_statics.py`)
Layouts: `hero`, `promo` (badge), `callouts`, `review`, `compare`, `colours`, `bold` (+ colour dots),
`lifestyle` (photo + panel), `carousel` (A/B/C cards), `split` (before/after), and bottom of funnel: `offer` (the
site's real %, price with the old price struck through), `stars` (verbatim review snippets), `checklist` (the
product's feature tags as ticks + the offer pill). 1080x1350.
- Photos from `site_assets.py`. Image 00 usually has "BEST SELLER" / "CLEARANCE SALE" badges: use a later
  image, or `masks` (the badge rect is covered by the area just below it). A faint ghost of the round
  clearance badge stays even after masking: use another image for heroes.
- Grey or textured site backgrounds: hero uses multiply blend after whitening; textured backdrops go in
  `card_photos` (shown as a framed card).
- Review static: `review_n` from reviews.json, or `quote` + `author` (never put the file name as author).
- **New product** (2026-10-13): with 3+ worn / detail photos the cycle has more `lifestyle` statics, each client
  photo once; a photo a feature picks gets that feature's tag as its headline; the `offer` static shows the notes'
  price and was price. No site swatches: the client's packshots are named by shade (`make_batch.match_colours`,
  CIELAB; used only on a sure match: every pair within 25, the next assignment 10 worse) for the colours static,
  the swatches and the colour dots; plan prints the mapping as a warning to check. A swatch places the packshot in
  (60, 400, 1020, 1120), above the caption band. A `"statics": false` photo (part of a head) is in no static. A
  folder with clips but no faceless photo gets no statics (one warning: the client must add photos).

### 4d. Free-form AI shots (Higgsfield): HISTORICAL, NOT ALLOWED
Kept only as a record of the 10-02 test (a free-form AI shot: made-up product, presenter). Do not follow these steps. The
allowed AI is 4e.
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
wallet" (during the 2026 sale also the campaign: 4f), urgency lines ("ends tonight": 113-H2 is the best winner for this), dark/bold statics (`bold` layout, red
accent). Never "our biggest sale (of the year)": the same % runs all year (site banner), so it is unprovable
(compliance flags it). Christmas/Mother's Day: gift angle (V13 recipe).

## 6. Quality checklist (each item was a real bug once)

| Check | Bug we had | Fix in place |
|---|---|---|
| Labels/tags inside the frame | long labels clipped | auto-shrink in `longform.py` |
| Captions to the last word | whisper dropped a closing sentence | `condition_on_previous_text=False` |
| Caption spelling | "Hobo 2 0", "XA", "have mercy", "50 %" | `CAPTION_FIX` + "%" glue in `longform.py` |
| No old captions flashing at cuts (burned-caption RAWs) | 0.25-0.5 s flash | cut ≥0.3 s before the next burned caption appears |
| Offer card not over a face | covered the (historical) AI presenter | drop the offer card when the speaker says the offer |
| Titles readable | cream text on white | dark titles on light shots |
| Graphics not cropped | square infographic cut to 9:16 | pad onto a 9:16 background |
| Clip audio | Hobo 2.0 zipper clip has an unrelated TV ad | mute flags in `clip_bank.json` |
| Silent talking clips | lips moving under another voice | keep such shots ≤1.8 s |
| Statics author line | file name printed as author | use `author` |
| No faces in statics | site lifestyle photos with faces in new-product statics | site photos never become lifestyle statics by themselves; DNN face check at plan time and on every rendered static (hard failure) |
| Offer per product | every bag got "50% off + free wallet" | offer from the site per product; theme lines are templates |
| Videos not shortened to fit a request | the owner's Hobo Bag 'hook test' came out as 29 s videos: Claude in Slack rebuilt the specs short ("hook-first") and uploaded them flagged | CLAUDE.md rule 6; `render` marks a storyboard video under 80% of its planned length `too short` (hard, `make_batch.shortened`) |
| No negated gift | intake read "No free gift is mentioned" in the Silhouette notes as a free gift | `new_product.gift_hits` negates per clause ("No free gift", "Free gift: none", "50% off ended" don't count; "No discount, but a free pouch" keeps the gift); `check` flags a gift the notes deny |
| No other product's name | the site copy of the Silhouette Bag said "The Libra Covenette Bag ..." and became a feature line | the intake drops lines naming another product (`names_other`) and reads the site only with `--site` / `--use-site` |
| New product's facts from its folder | the intake took price, description, colours and photos from libracases.com | Drive folder only (photos, clips, every notes file); `plan --pipeline new-product` read the site 0 times in tests |
| Square media not cropped | the 800 px square packshots and the 1080x1080 clip were cropped to 9:16 (the bag's ends cut off, 2.4x upscale) | `"fit": "auto"` on the product file's own media (`recut.py`): framed whole on a flat backdrop or a blur, also in the H2-H4 hook shots |
| Prices vs a stated % | notes give prices worth 50% but say "40% off" | the lower % is used, with a warning |
| 4 hooks per winner | 148, 121, 113, c9 had 2-3 cold opens: the 5-winner batch made 16 videos, not 20 | new cold opens in `clip_bank.json` (113's 4th: a `"variant": "label"`), section 4a |
| Body match after a beat | the QA sheet's 'body vs H1' read 37.8 on identical bodies | `projects.hook_end` counts the beat remix adds after a short cold open |
| Ad copy check outside the default folder | upload failed the compliance check for a product file in `--products-dir` | `make_batch.use_products_dir` in upload too |
| Colour names on client packshots | no site swatches: "Coffee" could sit on the black bag | `match_colours` by shade, only a sure match; else no named swatches |
| Same body in every version | a hook opened on a shot the body plays as a spare, so storyboard swapped that body slot: P01 H3 body match 127 | `projects.body_shots` counts spares; `render` adds "body differs from H1" (match 10+) to `qa/report.json`: uploaded, listed under QA flagged |
| Photos in a later session | with the cache gone, plan saved the raw Drive file as .jpg: HEIC unreadable, EXIF photos sideways, a face re-check that differed (P5 dropped as "could not be downloaded") | download by Drive id, then `new_product.to_jpg` as the intake did (`src_name`); a re-check face is named as such |
| Part of a head in a static | S12 (Silhouette P10) showed a jaw, chin and ear; no face detector fired | `new_product.head_part` on worn photos: `"statics": false` = videos only |
| Captions over the swatch bag | the colours block's captions sat on the bag's lower body | swatch box (60, 400, 1020, 1120) |
| End card over the close | the end-card band hid the framed bag's base | `CLOSE_FIT_Y` 0.30 on the close's fit picks |
| A repeat request = the same batch | "new product Silhouette Bag" again gave the same 20 statics and specs, renamed _v2 | `--seed` defaults to 1 + the product's `tests` (not with `--only`); plan prints `seed` |
| One batch, two Drive folders | upload dated the folder by the UTC clock: videos after midnight landed in a second folder and `tests` entry | the folder and `tests` date come from plan.json `created` |
| Delivered winner openings | `sent_openings` scanned only `recipes/daily`; winner specs go to `recipes/winners` | `projects.RECIPES` = both |
| `--videos` in winners | made storyboard projects in Outputs/Winners | in winners `--videos N` = N winner projects |
| A fixed folder stayed a draft | `ensure` kept an intake draft as "edited by hand" after the client added notes | every intake writes `auto` + `source.auto_sig`; an untouched draft is made again |
| PDF-only notes | no `pdftotext`: the PDF was skipped and exit 2 hid the warning, so the reply asked for notes the client had added | `pypdf` fallback; plan prints the intake warnings before exit 2 |
| Claims beyond the folder | Drive-only ads said "free US shipping" and "Shop ... on libracases.com" (PLAYBOOK's store-wide bullet counted as evidence) | `compliance.drive_only`: the product file is the only evidence; `ad_copy` drops those lines unless the notes say them |
| A folder named like a built-in bag | a "Hobo Bag" folder made the built-in Hobo Bag's ads from the site | the key is kept, plan uses the folder's file (`LC_PRODUCT_FILE`), with a warning |
| Aliases | "black" became an alias, so "Black Friday hobo bag" picked another file | aliases drop colours, generic words, built-in names and other files' aliases |
| Folder names as typed | "The Silhouette Bag", "silhouette bags" found no folder | `new_product.norm_name` (leading "the", case, punctuation, plural s) |
| Short new-product videos | a 5-feature cap: Silhouette videos 37-39 s, 2 bullets dropped unlisted | up to 7 features (`MAX_FEATURES`); cut bullets listed as "not used" |
| Tags saying more than the line | "smooth, structured feel" got SLEEK SHAPE; a plain "leather" line got SOFT LEATHER | feel tags first, SLEEK SHAPE from silhouette / elongated words, leather tags from the line's own word |
| Hook repeats the body | P03 H2 said a feature line at 0 s and again at 10.7 s, on the same photo | no hook line from the body's first 3 blocks; the hook's 2nd shot is never a body shot |
| Few different hooks | "Stop carrying a bag that swallows your keys." opened 3 versions | POV / question hooks from the feature words; plan warns when a line opens 3+ versions |
| Near-black backdrop | the dark clip's blurred backdrop read as a letterbox bar | `recut` lifts a dark-bordered blur (`lutyuv y=28+val*0.75`) |
| EXIF stills in fit | `recut.dims` used the raw size: a portrait phone photo was framed as landscape | `dims` / `edges` apply the EXIF orientation |
| Winner single videos | `--hooks 1` winners exited 2 on RAW quotes in `hook_first_line` | `compliance.batch_items` treats them as RAW quotes |
| Clips-only folder | 20 "no usable photo" warnings | one warning naming what the client must add |
| Label variant as H1 | with some seeds 113's label-only variant became H1 | in a project a `"variant": "label"` cold open is never H1 |
| No wrong claims in RAWs | C9_V2 says "two-year warranty" (site: 1 year) | cut 28.16-30.3 in `clip_bank.json` |
| No health claim in a RAW body | 94 "a strap that prevents shoulder pain" shipped with "Compliance: ok" | `compliance.raw_audit` scans the RAW words each version plays; `claim_cuts` in `clip_bank.json`; plan leaves out a winner that still has one |
| No talking customer as B-roll | her lips moved under the narrator before she was introduced (54.0 / 63.3 were not silent) | transcript check on every pick (`make_batch` / `projects.py cadence`), her clip is her scene only |
| No 11-15 s single shot | the customer section was two unbroken shots (38% of the ad) | `storyboard.cut_points`: a new framing every ~3.2 s; `projects.py check --build` flags any picture over 5 s |
| Customer -> narrator handoff | the narrator started 0.1 s after her last word | `storyboard.CLIP_PAD` 0.5 s |
| Caption wording | whisper on the final mix: "phobo bag", lost punctuation, phrases split mid-sentence | captions from the script / committed transcripts (`transcript` in the EDL) |
| Captions over the end card | moved up to mid-screen during the last 2.6 s | dropped (or ended) where the end card starts |
| Captions in the Reels UI | 2-line captions reached y 1355 (Reels covers the bottom ~35 %) | `"caption_zone": "reels"` (centre 1150, bottom 1250) |
| Captions over the product mid-screen | y 1150 sat on the bag and hands | bottom band by default (centre 1380), top band for busy shots (`busy_shots`) |
| Hook split over 2 captions | "This is the Black Friday / deal you've been" + "waiting for" | the opening line is one caption (<= 10 words, 52 px when needed) |
| Medical hook label | "THE ARTHRITIS HAS WON" on screen | labels never name a condition (`compliance.LABEL_STORY`): "HER LAST COLLECTION" |
| One colour said, another shown | "Brown" over a black bag (badge photo had no swatch) | `site_assets.badge_free` + names in swatch order, swatches timed to the names |
| No music | "felt off" (Julian) | `pipeline/music.py` bed under every storyboard video |
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
- **Zoom on cropped shots is a still framing:** ffmpeg's `crop` works out its size once, at frame 0, so the crop
  path's `zoom` [1.0, 1.06] / [1.18, 1.24] renders as a fixed framing at z0 (left as is: changing it would change
  every render, winners included). Only `"fit"` segments really punch in. `"fit"` adds about 1-1.4 s of render
  time per 4 s still segment, nothing for a square clip; a fitted square sits at y 266-1346 (its bottom edge runs
  behind the first caption line; the outline keeps captions readable).
- **PDF notes** are read with `pdftotext` (poppler-utils), else `pypdf` (CLAUDE.md section 0, SLACK_SETUP setup
  script); with neither the intake skips the PDF with a warning (re-plan with `--refresh-product` after installing).
- **Costs (credits):** TTS 0.15-0.45/line (`plan` estimates 0.35/line; a batch of 20 statics + 5 projects: Hobo Bag
  34 lines ~11.9 credits, Silhouette Bag 22 lines ~7.7, winners 0 unless fill projects are added). Statics and
  real-footage edits cost nothing. Historical, not allowed now: Kling pro 5 s 12.5, GPT image 2K high 2.75 (the 10-02
  test with AI shots cost 70-200 credits for 40 ads).

## 8. Reply format (Slack / app)

One short message: Drive folder link; one line per ad (name, angle, length); credits used (balance before
and after); anything skipped, failed or needing a human (e.g. "V03 is 31 s, under the 35 s target: the product
file needs more clips"). Per pipeline (winners: brief, winner + ROAS, fill, unmatched; new products: what was read,
the offer used, the product file): CLAUDE.md sections 1 and 2.

## 9. Compliance (Julian, media buyer, 2026-10-09)

AI is fine (the client's Susan persona is AI), but never, in a creative or in ad copy: health or medical claims (cure,
heals, pain relief, arthritis relief, doctor-recommended, therapeutic, posture ...), prescription drugs, politics,
religion, blood or violence (not even a drop of blood), profanity. On top of that (CLAUDE.md rule 3): no invented
numbers or stats, no claim the facts don't back ('waterproof', 'handmade', 'best-selling', '10,000 customers', RFID on a
bag that has none), no fake testimonial in the brand voice ('I bought mine', 'my sister'), nothing beyond the real offer.

`make_batch.py plan` (and `projects.py expand`) run it at the end and exit 2 on a problem; `render` runs it again and
refuses until it passes; by hand: `python3 pipeline/make_batch.py check --out $OUT` (after editing a line or `ad_copy.csv`; the same check as `compliance.py --out`, plus the count a ugc hook says: "Four things ...").
It scans every voiceover line in `tts_needed.json`, every visible text of the statics and the video specs (overlays,
offer and end cards), `ad_copy.csv` and the RAW audio of every winner version, writes `$OUT/compliance.json` and exits
1 on a problem. For lines you are about to write yourself
(`--lines`, a product file's hooks): `python3 pipeline/compliance.py --text "..." --product "<name>"`.
- **What counts as evidence:** the site facts (`$OUT/site/<key>_facts.json`), the product's row and the offer bullet of
  section 1, the product's data (features, product-file facts). Our own hook lines (`hooks.json`) are checked, never
  evidence. Numbers allowed: the ones in those facts, the real %, price, colour count, 0, 1, this year and next.
- **The client's RAW ads:** the Susan / workshop-closing / arthritis / "her sister was robbed" story is approved as RAW
  audio, but a health CLAIM is never allowed, not even there: the RAW words each winner version plays (cold open +
  body minus its cuts) are scanned (`raw_audit`); a line that says the bag helps the body ("a strap that prevents
  shoulder pain", "the strap hurts your shoulder") or a drugs / politics / religion / blood word is a problem (render
  refuses it) until `claim_cuts` removes it, and plan leaves such a winner out. The story's own health / crime words
  ("The arthritis has won.", "her doctor told her to stop") play as they are and are listed under `raw_story` (plan
  warnings, the run report: "needs a human"); the claim cuts under `raw_cuts`. An on-screen label that repeats its RAW
  ("HER SISTER WAS ROBBED", "10 YEARS LATER") is allowed when the RAW transcript says it, listed under `allowed`; a
  label never names a health condition, not even the RAW's ("THE ARTHRITIS HAS WON" is a problem: "HER LAST
  COLLECTION"), and a cold open whose words name one opens the last version only. New text we write never uses those words: a
  narrated line, a static, ad copy (a RAW cold open quoted in ad copy with "arthritis" or "anxious" is left out).
- **Reviews:** verbatim review text and a brand-voice line that names the customer and adds nothing ("Carol calls it
  the best bag she has ever bought.") are allowed; a review that mentions a gift the product doesn't have is not.
- **Not a problem:** "anti-theft", pickpockets, crowds, Christmas / Mother's Day themes (built in, the client asked
  for them), "Free US shipping" (store-wide, section 1).
- **A problem:** reword the line (or drop the ad) and re-run; never upload a creative or copy with a problem. Read the
  `allowed` list once per batch: it is what a human would want to glance at (RAW story words, review superlatives).

## 10. Ad copy (Meta primary texts, headlines, descriptions; Wouter asked 2026-10-09)

`make_batch.py plan` writes it at the end (`upload` sends `<prefix>_ad_copy.csv` with the batch); by hand:
`python3 pipeline/ad_copy.py --out $OUT [--seed N]` writes `$OUT/ad_copy.csv` (one row per ad: `ad_name`,
`placement_group`, `primary_text_1`, `primary_text_2`, `headline_1`, `headline_2`, `description`, `cta`,
`hook_first_line`) and `$OUT/ad_copy.json` (per static / project, notes, problems). Template-based and deterministic,
no LLM calls; every line passes `compliance.check`, a line that fails is replaced by the next template.
- **Per static** one set; **per project** one set shared by H1-H4 (the body is the proven part, the hooks are what is
  split-tested), plus `hook_first_line` per version: the version's spoken hook, or a winner RAW's cold open in quotes;
  `primary_text_2_hook` in the JSON is primary text 2 opening with that line.
- **Shape:** primary text 1 = 2 lines (a hook + the product with its offer), at most 125 characters, no emoji; primary
  text 2 = 3-5 lines (hook or review quote, 1-2 feature lines, the offer line with an emoji, a CTA line), at most 2
  emojis; headlines at most 40 characters, description at most 30; `cta` = Meta button: Get Offer for Black Friday /
  Cyber Monday / Cyber Week with a deal, else Shop Now. No em dashes, no prices (they change; the % comes from the
  site at plan time), no urgency the theme doesn't bring.
- **Built from:** the product's feature lines, its real offer (plan's site %, gift), the theme (make_batch `THEMES`),
  the brand-voice hook lines (`hooks.json`, product file `hooks`), the site's colours, review sentences with the name.
  The angle steers it: review statics quote their review, colour statics name the colours, a storyboard project
  leads with the features its video shows, a winner project gets product copy about the features its RAW actually
  talks about (never one it doesn't show or say, never the RAW's story).
- **Variety:** within a batch no opening, headline or description repeats until the pools run out; `--seed N` gives
  another set. Notes say what was left out (e.g. "P01H3: no hook_first_line (health: arthritis)"); a custom theme
  (not built in) gets the evergreen lines and a note: refine with the theme's words.
- **Refining:** the Slack session may rewrite any field within these rules, then re-runs `make_batch.py check --out $OUT` (= `compliance.py --out $OUT`, ugc count words allowed).
- Example (Hobo Bag, Black Friday, S04 review static): primary text 1 "Stop digging for your keys at the bottom of
  your bag. / Black Friday: 50% off the Hobo Bag + free wallet."; headline 1 "\"Best bag I have ever bought\"",
  headline 2 "50% Off the Hobo Bag + Free Wallet", description "Black Friday: 50% off", CTA Get Offer.

## 11. Two pipelines: winners and new products (owner, 2026-10-13)

The owner's request (section 2 item 11). `make_batch.py plan --pipeline winners | new-product | catalog` (default
catalog: the counts and product given, exactly as before). Commands, checks and reply formats: CLAUDE.md sections
1-3; what the client types: `docs/CLIENT_GUIDE.md`; DM setup: `docs/SLACK_SETUP.md`.
- **Batch default:** winners / new-product with no count (or `--batch` in any pipeline) = 20 statics + 5 projects x
  4 hooks = 20 videos (`make_batch.BATCH`). Any count given = exactly those, the rest 0. `--projects N` = winner
  projects in winners (`--videos N` there too), storyboard projects otherwise. About 2 hours of rendering: statics
  first, then videos. The Drive folder and the product file's `tests` take the plan's date (`created`), so statics
  and videos uploaded on either side of midnight land in one folder.
- **Winners:** the newest brief's winners in brief order, one project each (4 cold opens = H1-H4, section 4a),
  statics of the top winner's product. Fewer winner projects than asked (unmatched winners): storyboard projects of
  that product fill the batch (`plan.json` `fill`, a warning; `--no-fill` turns it off). A brief that can't be read
  or matches no winner: all bank winners in `clip_bank.json` order (`winners_source` "fallback", said in the reply).
  Upload: Drive `Outputs/Winners/<date> – <name>`; specs `pipeline/recipes/winners/<date>/<name>` (`projects.
  sent_openings` reads them too: openings already delivered are warned about).
- **New products:** `--new-product "<folder>"` (or `next`: the newest folder with no ads yet; `--new-product` alone
  implies `--pipeline new-product`). `new_product.ensure()` makes the product file from the Drive folder only
  (photos sorted faceless first, cleanest first, into packshot / worn / detail / other, `"statics": false` for a worn
  photo that may show part of a head; clips; every notes file, PDF via pdftotext or pypdf; up to 7 features; the
  site never), reuses it while the folder is unchanged, redoes an untouched file (auto, or an intake draft) when
  the folder changes. Ready + `"auto": true` when `check` passes: no human step. Photo picks are `["photo", "P<n>"]`
  (= `photos[n]`, the P numbers of `overview.jpg`). Its claims rest on its notes alone (`compliance.drive_only`: no
  store-wide free shipping, no libracases.com line unless the notes say it). Upload: Drive
  `Outputs/New Products/<date> – <name>`, and the batch is appended to the product file's `"tests"` (commit it with
  the specs in `pipeline/recipes/new_products/<date>/<name>`); the next plan of it uses `--seed` 1 + its tests, so
  "more ads for the Silhouette Bag" gives other statics and hooks. Product file schema:
  `pipeline/data/products/README.md`.
- **Fit framing** (`recut.py`): a product file's own photos and clips that are not 9:16 are shown whole: `"fit":
  "auto"` picks `pad` (flat colour from the source's own top / bottom border, seamless on a white or gradient
  studio backdrop) when the border is uniform and light, else `blur` (the picture filled, blurred, darkened behind
  it; lifted instead when the border is dark, so it never reads as a black bar). The frame is never scaled past 1080 wide (800 px photos 1.35x instead of 2.4x), its centre at `fit_y` 0.42,
  and its zoom really punches in. A 9:16 source, built-in and `clip_bank` footage and winner RAWs are cropped as
  before (byte-identical commands).
- **Silhouette Bag test (2026-10-13):** 12 photos (P0-P4 packshots in 5 colours, P5 open bag with pocket labels =
  `other`, P6 / P7 / P10 worn, P8 zipper and P9 leather corner = detail, P11 a face: never used; P7 and P10 show
  part of a head: `"statics": false`), 1 clip (1080x1080, 33 s, blurred side bars baked in, so the bag fills about
  half the width in fit), notes: $59.95 was $119.95 = 50% off, no gift, 5 colours, 7 bullets (all 7 kept since
  the 2026-10-13 fixes; the old cap was 5). Plan: 20 statics + 5 projects (features, colours, showcase, lifestyle, offer),
  22 voiceover lines (~7.7 credits), 0 site reads; videos plan at ~42-45 s (espeak test renders 47-49 s; with 5
  features they were 37-39 s).

## 12. The ugc video format (owner, 2026-10-14)

**Why.** The owner's lead measured the clients' top-impression ads (3 reference videos, 75 Ad Library cards, rank 1 = most
impressions) against our Hobo Bag videos. The footage is as good; script, voice and editing are not:

| | references (top impressions) | our Hobo batch (2026-10-13) |
|---|---|---|
| words per minute | 187-220 | 137-160 |
| time someone speaks | 88-91% | 80-82% |
| longest pause | about 0.7 s | 1.0 s (11 pauses over 0.5 s) |
| voices | one | narrator -> a real customer -> narrator |
| new shot | every 1.5-2.3 s, each phrase shows what it says (hands in real places, zips, pockets, the bag worn) | every 2.6-3.1 s, the same hidden-pocket shot cut twice in under a second |
| loudness | -14 LUFS, range (LRA) 1.3-2.8 LU | range 6.7-7.6 LU (swings) |
| script | a specific hook in the first 3 s ("4 things ...", "the most organized bag ..."), numbered chapters ("1. I stopped worrying in crowds"), problem -> benefit pairs, proof, the offer last | "Here's what makes the X different. First ... Two gold side zips ...": a feature list with no situation |
| length | 49-81 s (Ad Library median 66 s) | 58-68 s; two review cards held ~10 s while the narrator reads them |
| first word | 0.0 s | 0.0 s |

**Decisions** (section 2, item 12): "you" form, 55-80 s, the default storyboard video.

**What it is** (`make_batch.py plan`, no flag; `--classic` = the old output):
- *Script* (`pipeline/ugc_script.py`, data `ugc_arcs.json`, hand-written Hobo Bag scripts `ugc_hobo.json`): one script per
  project, angle cycle `n_things`, `demo`, `stop_x`, `travel`, `value` (file names `..._P01_H1_things|demo|stop|travel|value`;
  `--seed` rotates the order and the wording): a hook (type promise / superlative / question / problem / price, a label of at
  most 3 words, a feature when its footage should open it), 5-9 chapters (1-3 short sentences each = one voice take; the
  chapter number is printed on screen, never spoken), problem -> fix pairs, reviews quoted verbatim ("Carol says: ..."), a
  warranty / returns / price line, the offer last ("fifty percent off ... Tap the link below."), 3+ alternate hooks of other
  types for H2-H4. Only the product's own facts (compliance.check passes on every text); first person only inside a review.
- *Board* (`make_batch.plan` -> `ugc_board`): `"mode": "ugc"`, `voice_speed` (default 1.12), the hook block + one block per
  chapter (`"number"` on the numbered ones), a `tag` overlay with the chapter's feature name, `review` overlays on the
  reviewers' names (3 s at most), the offer card on "fifty", the end card. Footage per chapter: the product's feature picks
  and their other vetted moments, B-roll, hook clips, every other clip of its `clip_bank` sections, for the built-in bags also
  the client's library clips of `clip_index.json` (usable, no face, no text, 720p+; `["drive", <id>, start]` picks), for a
  product file its photos by kind and its clips; each phrase of a chapter (storyboard's own `phrase_cuts` / `shot_groups`,
  predicted from the words) gets the footage whose notes share its words (`kw_terms`), a moment never twice in a video
  while another is left, a short clip cut at most twice per chapter; a 2nd showing is framed closer; spare shots per block
  for a long phrase; a packshot as the last shot under the end card. The hook is chosen first (its shots are its own).
- *Voice and mix* (`storyboard.py`, `remix.master_ugc`): every take trimmed, pauses cut to 0.16 s, sped up 1.12x with the
  pitch kept, joined 0.08 s apart; -14 LUFS, LRA <= 4 LU, true peak about -1.7 dBTP; the music bed 6 dB lower.
  `pipeline/data/voice.json` {"voice_type", "voice_id", "speed"} (optional) overrides the brand voice and the speed: the
  lead decides after a listening test (the placeholder tests used espeak: a real voice's pace is not measured yet).
- *Hooks:* H1 = the script's hook, H2-H4 = its alt_hooks (`projects.ugc_hooks`: other types first, rotated by `--hook-seed`),
  each voiced as one short line (`P01H2_hook.mp3`), opened over the footage of its feature or the product's hook clips, the
  body shared. A themed request puts the theme's hook first (label BLACK FRIDAY ...) and its close on the offer chapter.
- *Length / cost:* the estimate is words / (2.75 x speed) + the kept silence and pads (`make_batch.est_ugc`): QA band 55-85 s,
  Hobo Bag 64-72 s, Silhouette Bag 62-71 s, a thin product 40-50 s (`thin script: about N s`, it runs as it is); a script that
  would run under the floor (~27 s) is replaced by a classic video. One take per chapter + one per hook: a project about 13-16
  lines, a batch (5 projects x 4 hooks) 63-69 lines = 22-24 credits (was 12).
- *Scorecard* (`pipeline/scorecard.py`; `render` prints a line per ugc video, `qa/report.json` has `scorecard` and the soft flag
  `scorecard: ...`, the run report lists the lines): length 55-80 s, 185-215 wpm, speech >= 85%, longest pause <= 0.8 s (the
  last 0.6 s ignored), first word <= 0.35 s, average shot 1.4-2.6 s and none over 4 s, -14 LUFS +-1 with LRA <= 4 LU, true peak
  <= -1.0 dBTP, no repeated shot within 10 s (perceptual hash), no still card held over 3.2 s. Measured on the references:
  10-11 of 12 met; on our two Hobo videos 6 of 12 (wpm, speech share, longest pause, average and longest shot, LRA). A miss
  is reported, never fixed by cutting the video (CLAUDE.md rule 6).
- *Statics* (`brand_statics.new_layouts()`; the clean cycle since 2026-10-20, `make_batch.static_cycle()`): `native` (a face-free
  real photo, one caption, a small offer pill), `quotes` (the packshot with ONE verbatim review bubble), `value` (the real price
  struck through) and `studio` (the packshot large on a seamless backdrop tinted from the bag's own colour, a small wordmark,
  at most one short line + one small pill, no badge / button: the bag's colour is kept exactly, only the white of the photo takes
  the tint) make up the cycle: of 20, studio 4, native 4, quotes 3, value 2, offer 2, stars 1, colours / checklist / bold /
  compare 1 each; hero, promo and review are no longer in it (the studio static is the cleaner hero). native needs faceless
  worn / detail photos (the built-in bags have none, product files do), quotes a review with a usable snippet, value the site's /
  the notes' price and was price within 2 points of the %, studio a white-backdrop packshot (at most 2 more studio statics
  than there are such packshots; the rest take a hero without sticker). A layout the product can't back is replaced by the next
  clean one (offer / checklist / colours -> studio, stars -> quotes -> native). Why: the competitors' ads (Facebook Ad Library
  screenshot, 2026-10-20) are one big photo with next to no text; the long copy lives in `ad_copy.csv`. AI scene statics
  replace bold, compare, promo, hero, native, lifestyle first (then studio down to 3) and carry pill only / caption only / the
  photo alone / caption + pill in turn (`make_batch.scene_look`). `plan --classic` keeps the old cycle (identical to before).
- *Compliance:* a hook that counts ("Four things you'll notice ...") says a number no fact backs: `compliance.check_out` drops
  exactly those `numbers` hits (plan.json `ugc_numbers`, the label "4 THINGS" too) and lists them as allowed; every other hit
  stays. `python3 pipeline/compliance.py --out $OUT` and `make_batch.py check --out $OUT` agree.

**First test (2026-10-14, espeak placeholder voices, no Higgsfield call):** Hobo Bag batch plan = 20 statics + 5 projects x 4
hooks, 63 voice lines (22 credits), est 64-72 s; `projects.py check --build` of every ugc plan (Hobo Bag, Hobo 2.0, 3-Piece Set,
Slouchy, Vintage, Silhouette Bag, Moonlight Crossbody) clean (placeholder lengths 59-72 s for 5+ feature lines, 40-44 s thin);
one real render (Hobo P01H1, 62 s): 203 wpm, speech 83%, longest pause 0.62 s, shots 2.3 s avg, -14.0 LUFS LRA 1.0, 0 repeats,
10 of 12 targets (the misses: speech share, espeak's pauses; a 7.6 s "shot" where consecutive picks of one clip look alike).

**After the first verification (2026-10-14, two independent renders + scorecards):** fixed: (1) a short clip (under 45 s) is
one scene, so two shots of it within 10 s in one framing look like one long shot (the hidden-pocket chapter played 7.3-7.9 s
unbroken): storyboard's `Shots.clash` now alternates the framing (wide, closer, closest) and a still's closer crop is another
shot only after 4 s; make_batch penalises a neighbour from the same clip harder; `projects.py check --build` notes a moment
shown again (`nothing else to show`). (2) Pauses inside a take are cut to 0.16 s (was 0.26: speech 80-82% of the video). (3) The
colours chapter hands storyboard every swatch (`"say": "<colour>"` on the pick): each shot shows the swatch whose name it says,
else the next. (4) The main hook of an `n_things` / `demo` script is always the angle's own promise ("Five things ...", "Watch
..."), never a general line. (5) A product file's scripts never say "you stop X" / "what if you never had to X": its notes carry no
such promise, so the lead is a question about the situation and the fix is the notes' own line. (6) A review card ends with its
block and when the next card starts; an anchor on a name the transcript misheard falls back to the script's own words. (7) The
render's QA line scores the render's own cut times (no cut hidden under a card, none invented inside a dark clip) and counts
'anti-theft' as 2 words like the transcriber. (8) A bank clip with `"text"` (printed words fill its frame: the HAPPY BIRTHDAY gift
bag) is not used in ugc videos; a photo of kind 'other' (a diagram with words) is shown once, whole; native statics take a worn photo
before a detail macro; quotes statics skip a reviewer named 'X A.' and aim their bubble tails at the bag.
Re-measured with espeak voices (standalone scorecard; Hobo P01H1 / P01H3 / P02H1, Silhouette P01H1): longest shot 4.3 / 4.3 / 3.6 /
4.9 s (was 7.3-7.9 s; the 4.3-4.9 s are two planned shots under a review card or between two white packshots, which the scorecard
cannot tell apart: the planned maximum is 3.1 s), speech 86 / 84 / 83 / 85% (was 80-82%; espeak's word gaps are wider than a
real voice's: measure again with the first ElevenLabs batch before touching `GAP_CAP`), 197-215 wpm, 10-11 of 12 targets (was 9-10).

**Limits to know.** A photo-only product (no clips) repeats its photos in closer framings (28 shots from ~12
photos). The scorecard cannot see a review card over moving B-roll (shows only as the longest shot) or a re-crop of one moment.
The library has little footage of the bag out in the world (street, train, cafe, airport; about 5 clips): problem lines about a
crowd or a commute are shown with the closest footage (`kw_terms` folds those words to 'walk'); clips of those situations from the
client would show them. A library clip is an edited video: a picked moment can contain its own cut (a 0.5 s flash). Detail macros
of a product file can carry the product page's white corners. The estimate is calibrated on espeak (placeholder renders came out 4-17% shorter than estimated); a real ElevenLabs voice runs about as
estimated, so the `shortened` guard (80%, ugc 70%: the estimate is a guess at the voice's pace) still has room.

### 4e000. The strategist step, matching b-roll, no reviews, new end cards, faster renders (owner + Julian 2026-10-21)

Julian (media buyer) checked the B011-B013 videos: (1) the b-roll must match what the script says ("the snap close of the Vintage bag
showed the strap or a UGC creator"), (2) drop the "this customer said this" review chapter before the CTA, (3) the end cards "are a bit
off", (4) "almost the same, very similar videos for everything: different ideas", (5) rendering takes too long, (6) "full strategist-level
scripts". The owner added: statics "look like they were made by some random thing": studio level, the bag with elements behind it
(the Hobo 2.0 strap tied to a chair), generated with Higgsfield from the real bag, realistic.
- **Matching** (`shotmatch.py`, `footage_index.py label-sheets / label-merge`): five labelling agents looked at 4 frames of each of the 431
  usable clips and tagged what each frame SHOWS (snap, zip, side_zip, pocket, inside, packing, strap, worn, ...); `moments` live in
  `clip_index.json`. `ugc_board.choose` scores every spoken phrase against them (`wants`: its words + the chapter's feature + the sheet's `show`
  tags); a miss on a specific feature costs, a moment shown again costs `REUSE` (a good match shown twice, the 2nd time closer, beats a
  shot of something else). The old failure: shots were picked by the client's folder words and a +6 feature bonus on curated clips, so a
  compilation clip of a woman with the bag (faces) was picked for every strap line. Clip-bank clips whose notes name a woman / customer /
  model are out of the ugc pool now (`has_person`).
- **Hook openings (B014 lesson):** the first B014 render opened 12 of 16 videos on the same four curated "hook clips" (the café chair, the
  woman on the porch ...), because pick_shot in `projects.expand` ranks the engine's `hook` clips first for H2-H4 and `choose` gave them +4. For
  the strategist's batches `ugc_board` now picks each alt hook's opening (and its spare shots) itself from its `show` tags
  (`ugc.alt_shots` in the plan, used by `projects.sheet_shots`), with `OPEN_REUSE` against a clip another hook of the batch opens on, and
  `BATCH_REUSE` against a moment another video of the batch already shows. All 16 openers of B014 are different clips that show what the
  hook says. A video body may still share a few moments with another project (7 of 45 clips in all four); the sheet's `show` tags decide.
- **No review chapters / cards** in ugc videos (`ugc_script.REVIEWS = False`); the proof chapter is a recap, the objection a fact
  (warranty, returns). Statics keep one verbatim review.
- **End card** (`longform.end_png`): the old one was a grey band over whatever the last photo was (the site's detail collage!) in Meta's
  button zone. Now a full opaque studio card: the real packshot (never a collage: `brand_statics.collage`) on the bag's tinted backdrop,
  wordmark, name, the offer pill, the button, everything between 260 px from the top and 400 px from the bottom.
- **Render speed** (one video 8 min -> 3 min cold, 2 min warm): shots rendered 2 at a time, the concat copies the video stream (no second
  x264 pass at preset slow), the final overlay pass runs at preset `faster`, and the 4 hook versions of a project share their body's shots
  through `$OUT/_seg` (`recut.cached_segment`; render does each project's H1 first; `upload` deletes the cache).
- **Strategist step** (`ideas.py`, CLAUDE.md section S): every catalog / new-product batch starts with a packet, research and a written
  `ideas.json` (projects with a new idea, hooks, complete scripts with the picture each line needs; statics with concepts); `plan --ideas`
  checks it (first person, counts, offer last, claims, compliance, footage coverage, earlier hooks / lines) and builds everything from it;
  the sheet goes to Drive as `strategy_sheet.md / .csv`. The script engine's templates remain for `--lines` requests.
- **Concept statics** (`brand_statics.l_concept`): AI scenes of the real bag with props (Higgsfield gpt_image_2_5, the real packshot as
  reference, 1 credit each, gated by `ai_gen.gate`), the words in a footer under the photo so they never land on the bag (asked for in the
  prompt: the end where the words go empty; the model only half obeys, so the footer does it); sunglasses / mannequins / people in the
  background trip the face check and are kept out of the prompts; a person is cropped at the shoulders. The AI scenes of the bag keep the
  matching pouch wallet because the real packshots show it.
- Meta: third-party AI images may be labelled "AI info" (Meta says it will auto-detect them); the only photoreal face is the presenter's
  (4e0000 below).
- Disk: the session's allowance counts the scratchpad: clear old test runs before a batch (`pipeline/cache/media` alone is 4-5 GB; raise
  `LC_MEDIA_CAP_GB` for a batch whose videos use ~80 different 4K clips).

### 4e0000. The presenter format: a host who talks to camera (owner + Julian 2026-10-21, B016)

Julian wanted "a model or a character sitting there and talking", with cut-ins, like the competitors' mom-talks-to-camera ads. The owner
allowed avatars when a story needs them. `pipeline/presenter.py`, `data/presenters.json`, `assets/presenter/`.
- **What it is:** a project whose sheet says `"presenter": "maya"` is spoken by a generated woman. Her takes are Kling 3.0 clips (picture AND
  sound: the line is in the prompt, so her lips match; one voice for the whole video); library footage cuts in over her voice (`cam` per
  chapter: open / both / close / full / none) and every hook is her on camera. She is a host: "you" form, never "I", never a customer, never
  an invented use or result (`ideas.check` and `compliance` enforce it on her words).
- **How she was made:** Higgsfield Soul 2.0 (`soul_2`), one original face (never a real person's), chosen from candidates; her scene stills
  (`gpt_image_2_5`, references: her master + the real bag's packshot) put her in a cafe / sofa / car / kitchen with the REAL bag; the take
  starts from that still. `presenter.py needed|gate|reject` list, check and reject the stills and takes like `ai_gen.py`.
- **The skin lesson (the owner called the first Maya "totally fake", twice):** asking the model for "visible pores, fine lines, unretouched,
  no smoothing" makes it draw etched wrinkles and an orange, shiny skin: it reads as AI at once. The second Maya was made with the
  opposite wording (soft, even, natural phone-photo skin, matte, a few freckles, only gentle expression lines, no heavy texture / etched
  wrinkles / orange tint), six candidates, and the owner picked her. Still and take prompts keep that wording (`test_presenter.py`
  forbids the old one). Standard mode (720p) smooths the face more: takes are `mode: pro` (1080p, ~2.5 credits per second).
- **Cost:** about 2.5 credits per second of speech: a 4-project batch is ~360 take-seconds, ~910 credits with the stills (`plan` caps it at
  1000, `--presenter-cap`; the usual 100 is for voiceover + AI scenes). Kling fits the line to the clip length (2.4-3.1 words per second),
  so a take is `ceil(words / 2.7 + 1)` seconds, 4-15 s. She speaks at ~2.5 words per second, slower than the ugc voice: the scorecard's
  wpm / speech targets are soft misses by design (rule 6 still holds: never shorten the video).
- **The gate** (`presenter.py gate`): one face, the words she says against the script (numerals and "%" spelled out, hyphens dropped: a
  transcript says "50 %" where the script says "fifty percent"; a letter-level ratio forgives "Habo"), a starting delay, a tail (Kling often
  ends the clip right after her last word; under 0.08 s = cut off, under 0.3 s a note only), faces on three frames, no black frame, and the
  compliance check on words she ADDED (the script itself was checked at plan). A bag that changes between frames or hands that melt are
  rejected by eye on `qa/presenter_takes.jpg`.
- **Never `upload` while videos are rendering:** `upload` deletes the shared shot cache (`$OUT/_seg`), so the videos being rendered at that
  moment fail with "Impossible to open .../_seg/....mp4" (B016: the statics upload killed P01H1 and P02H1; `render --only P01H1,P02H1`
  after the pass redoes them). Upload the statics before the videos start, or wait for the render to finish.
- **Overlays** sit at y = 960 (`overlay_y`) so a label / tag / offer pill never covers her face.
- **The statics' face check can be wrong:** the DNN face check skipped two statics of B016 that show no face (the blurred hand and
  sunglasses of a footage frame; a navy leather chair with a painting). They stay out of Drive (`--include-flagged` is never used).
- **Making a new host:** `soul_2` candidates (original faces; the prompt wording above) -> pick -> `assets/presenter/<id>.jpg` -> a row in
  `presenters.json` with `look`, `voice`, `soul_job` (the job id used as the first image reference) -> a character sheet and an
  expression sheet with `gpt_image_2_5` from the master for the owner.

### 4f. Store-wide sale campaigns: the Black Friday Sale 2026 (owner 2026-10-23, revised 2026-10-26)

**Revised 2026-10-26 (Wouter, after a drop in performance):** the free gifts and the extra cart discount are gone ("not coming back");
"It's 50% OFF or you can say up to 60% OFF"; 60% only on bundles like the 3-Piece Set (not any 2 bags); the site added Early Black
Friday messaging, a countdown, "Ships by" dates and the 3-Piece Set as a "Best Value" upgrade on the Hobo Bag page. `campaign.json`
now has no gifts, `bundle_any: false` (no bundle static), `upto_pct: 60`, end pill "UP TO 60% OFF", no offer-card sub line, and
compliance stops 'free gifts', 'a free jewellery box' and '60% off 2 or 3 bags'. He also wrote "you can still say easy returns but
during black friday we don't accept returns": we keep the final-sale block (an 'easy returns' promise on an order that can't be
returned is a false claim, hard rule 3 and Meta's misleading-claims policy); the 1-year warranty and faulty-item cover are true and
fine to say. Everything made before (B019, B020, B025, B027: end cards "+ FREE GIFTS", gift / bundle statics, gift lines) must be
re-made before it runs. The text below is the first version (23 Oct) for the record.


Wouter: "BF versions of the winners first, then new BF concepts: bundles / one for you, one for her, free gifts, the 3-Piece Set,
Christmas gifting, BF prices are live now; lots of variations". `pipeline/campaign.py`, `data/campaign.json`, `assets/gifts/`.
- **When:** a batch whose theme is one of the campaign's (`black friday`, `cyber monday`, `cyber week`) on a day inside its `from` ..
  `until` gets it (plan warns `campaign: ...`; plan.json `"campaign"`); outside the dates the theme falls back to the plain one.
  `--no-campaign` turns it off for one plan. `python3 pipeline/campaign.py show --theme "cyber monday"` shows what a batch gets.
- **What changes:** the end card of every video (ugc, classic, winner remix): title "Black Friday Sale" (Cyber Monday / Cyber Week Sale),
  the pill "UP TO 60% OFF + FREE GIFTS", over the bag's packshot (winners: when the winner's product is the plan product); the offer card's
  sub line "+ FREE GIFTS WITH 2 BAGS"; one sentence before "Tap the link below" in the close ("Buy two bags and you also get a free
  jewellery box, while stocks last."; Cyber Monday adds the end date); the engine's hooks put the campaign's first ("Black Friday prices are
  live now. No need to wait."); ad copy primary texts / headlines / description lead with the sale; the strategy packet lists its facts
  and the client's idea list. Statics: slot 3 = `gifts` (the bag + the two gift packshots, "2 bags: ... 3+ bags: ...", "Only bags count ·
  while stocks last"), slot 5 = `bundle` (2-3 colour packshots, "One for you, one for her.", pill "60% OFF 2 OR 3 BAGS"); both only during
  a campaign (ideas sheets may ask for them then).
- **The rule that matters:** each bag keeps its own % from the site (the Hobo Bag is "50% off"); "60% off" is said only of 2 or 3 bags
  together or as "up to 60% off". Compliance takes the campaign's facts as evidence and strips only its `approved_phrases` before the
  offer check, so "The Hobo Bag is 60% off." is still flagged, and so is any gift value other than $19.95 / $44.90.
- **Final sale (the site's sale terms, read 2026-10-25):** every item bought in the sale is final sale, no returns (faulty items
  and the 1-year warranty still covered). `campaign.json` `final_sale`: compliance stops 'easy / free returns', 'N-day returns',
  'send it back', 'money-back' while the sale runs, the scripts get no returns fact and ad copy says '1-year warranty included'.
  B014 and B016 (made 21 Oct, before the terms were read) say 'one-year warranty and easy returns' in all 32 videos and B014,
  B016, B019's ad copy has '1-year warranty + easy returns': not to run during the sale unless Wouter allows returns.
- **Gift photos:** `assets/gifts/jewellery_box.jpg`, `cosmetic_bag.jpg` (the site's product photos, no other brand in them).
- **A new sale:** add a campaign to `campaign.json` with the client's words in `approved`, its dates, themes, gifts and phrases; nothing
  else changes. `tests/test_campaign.py` covers the window, the compliance cases and the two layouts.

- **2026-10-27 check of Wouter's answers:** no deadline the sale does not have: "ends tonight / today only / hours left" is blocked
  until 30 November (the site banner keeps "ends tonight": the owner's choice for the site, not for the ads) and "last chance / final
  days" until 20 November (the last-week content); campaign.json `banned` with `except_on` / `except_from`. The Hobo Bag's price is
  $54.95 ($109.90) since 27 October (site: `luxury-hobo-handbag-special-gift-1`, still "+ FREE Pouch Wallet"); six delivered statics
  print the old price (B014 S05 / S14, B016 S14, B019 S10 / S17, B027 S07). Hobo 2.0: "two straps" is an `also` fact in the packet.

### 4g. One bag per ad: the Hobo 2.0's two looks (owner 2026-10-23, after B017; RESOLVED 2026-10-26)

**Resolved:** Wouter: "it comes with 2 straps - one for crossbody and one for handbag". The thin top handle (site) and the wide eyelet
strap (footage) are the two straps of the same bag, so the guard is off (`designs.json` has no `show`): site photos and footage are
used together, presenter projects work again, and "comes with two straps" is a feature. The text below is the record.


The owner on B017: "the bag is not in the correct dimensions. It's not the correct size." Two different bags were mixed in one ad.
- **The two looks:** every library clip of the Hobo 2.0 (`Raw files/HOBO 2.0`: 120 usable clips uploaded 7 July - 12 October 2026, all
  looked at; the one library photo too) shows the **eyelet** bag: a wide flat strap with metal eyelets and rivets, a large slouchy body,
  a front zip pocket, a 15-inch laptop fits. libracases.com's 14 photos (uploaded 4-5 June 2026, several named "BananaProAI", so
  possibly AI-made; the "NEW" packshots; the Black Friday banner photo of 23 October) show the **slim** bag: a thin rolled top handle,
  a neater, flatter body. B015 and B017 used the site photos for the end card, the studio / colour statics, the AI scenes and the
  presenter's bag, and the footage for every cut: the bag changed size between shots.
- **The guard:** `data/designs.json` lists the product's looks and which one a batch shows (`show`); `make_batch.design_of` /
  `clip_ok`. With `show` = the footage's look (the default since 2026-10-23): none of the site's photos is used (the end card is the
  plain card, statics are footage frames + text layouts, no gifts / bundle / studio / colours statics, no AI scenes); presenter
  projects exit 2 (she needs a packshot of the bag she holds: make those projects with the normal voice). With `show` = the site's look:
  the footage is left out (clip_bank `hobo_2_0` + the clip_index rows) unless a clip is tagged `"design": "slim"`.
- **Not yet confirmed:** the footage's bag was chosen because real footage filmed July - October shows what customers get, and the
  videos are built from it. If Wouter says the slim bag ships, set `show` to "slim" and ask for footage of it. Either way the site's
  photos and the footage show two different bags: the client should know.
- **A new product with two looks:** add it to `designs.json` (`site`, `library`, `bank_sections`, `designs`), tag the clips.

### 4h. The ad tracker sheet (owner 2026-10-25: "keep track of everything ... add columns to give insights on what did well")

`pipeline/tracker.py`, `data/tracker.json`: the Google Sheet "Libra Cases – Ad Tracker" in Drive / Ad Creative Pipeline. Tabs: Batches
(one row per batch: date, product, theme, pipeline, what was asked, folder link, notes, status, results added up), Ads (one row per
image / video file with its link; yellow columns the team fills in: launched, spend, impressions, 3-sec plays, clicks, purchases,
revenue, verdict, notes; grey formulas: hook rate, CTR, CPA, ROAS), Summary (by product and type), Data Sources.
- **Updated by itself:** `make_batch.py upload` calls `tracker.sync` after the ledger (and re-lists the last 3 days' batches, so a
  re-render lands too); a sync also adds every B-numbered folder in
  Outputs (Winners/ and New Products/ too) the sheet lacks, so a Slack run on an unmerged branch still lands there.
- **Drive scope only** (the Sheets API is off in the login's Cloud project 883081366864): a sync exports the sheet, keeps every row,
  every typed value, people's own columns (where they put them) and their own tabs, refreshes the file details of the synced
  batches, appends new rows, rebuilds formulas and formats, and replaces the content (same link). Hand-made cell colours and comments
  are not kept; an edit typed during the seconds of a sync can be lost. With the Sheets API on, it could append in place instead.
- **Fix by hand:** `python3 pipeline/tracker.py sync --batch B045` (or `--all` to refresh every batch's file details); `show` counts.
- B001's files sit in the Outputs folder "oct 3 test" (`folder_overrides`), whose subfolder of B012 statics is skipped.

### 4k. Videos are stories, not feature lists (owner 2026-10-27)

Diagnosis (B025 / B027, 25 Oct): every project walked through the same five features (back pocket, side zips, compartments, three
ways to wear, leather) in 7-8 chapters under a different frame ("for mum / for sister", "three questions"), two or three chapters
were price and bundle lines, hooks opened on the discount, the most used shot tags were "hero" and "placed" (the bag sitting there).
Meta reads such ads as one. The owner approved: story structures, hooks that show, people, proof moments (1, 2, 3, 6 of the plan);
not approved: a slower story voice and 15-25 s cut-downs (the 185-215 wpm and 55-80 s rules of 2026-10-14 stay); presenter: one per batch.
- **Structures** (`data/story_structures.json`): one moment, a test live, myth vs fact, gift reveal, advice to a friend, four places,
  what you carry now, POV, the night before; or the strategist's own. Each project names one, each chapter its `beat`.
- **The check** (`ideas.check`, sheets from 2026-10-27): the structure once a batch and not the last batch's (novelty log
  `structure`); beats of the structure, in order, the required ones there; at most 3 features (`features_in` on the feature tags'
  words) and a different lead feature per project; price words (%, percent, half price, sale, Black Friday, prices, bundle, free
  gift / shipping) only in the offer chapter and in at most one hook; hooks open on four different first `show` tags, none of hero /
  placed / colours; 1-2 `proof_shot` chapters showing a movement; two chapters worn / walking without the presenter; one presenter
  project per batch of 2+ (or `no_presenter`). Older sheets keep their day's rules (`check(..., day=)`).
- **The render** (`storyboard.py`): a `proof` block's shots are held ~2.8 s (up to 3.8), 0.5 s of air follow its line, and its first
  clip shot plays the clip's own sound under the voice (`natural_sounds`: levelled to -24 LUFS, skipped when the clip has no sound, is
  silent or someone talks in it); a beat's `pace` (slow 2.4 s / fast 1.6 s shots) follows the story. A sheet's videos never switch to
  the long story format by a word in the request (only `--story`).
- **Cost:** the presenter project ~225 credits a batch; the rest is unchanged (~4-5 a voiceover project).
- Tests: `tests/test_story.py` (fixture `tests/story_sheet.json`), `tests/test_storyboard.py` (proof block).

### 4j. AI-designed statics: a format library, new formats every batch (owner 2026-10-26)

The owner: "the main issue is every batch looks the same, we need unique, scroll-stopping ideas"; "it's fine if you use Higgsfield for
statics". A test sheet of 8 whole ads made by `gpt_image_2_5` from the real packshot (the words set by the model, all spelled right)
got: "i like 2, 3, 4, 6 (make it realistic), 7, 8 (make more realistic). make them unique each time we run a batch ... new ideas and
new formats that follow meta guidelines". Liked: #2 magazine cover, #3 feature diagram, #4 HALF PRICE poster, #6 POV street from behind,
#7 "Everything fits." flat lay, #8 "For Mum" gift tag. Not liked: #1 sticky note, #5 phone notes app.
- **Layout `ad`** (ideas.py): `format` (data/static_formats.json, ★ = liked; or an id of the strategist's own + `format_name`, `art`,
  `people`), `words` (the exact 1-4 lines), `scene.prompt` (what the picture shows), `scene.colour` / `scene.ref` (the reference
  packshot). `ai_gen.build_ad_prompt` adds the format's art direction, keep-the-real-bag, the closed bag, the exact words ("each
  exactly once ... big enough to read on a phone"), the people rule (none / from behind / hands only) and the realism line. `l_ad`
  shows the picture as it is (1080x1350); a rejected or missing still falls back to the real static of its slot.
- **Unique every batch** (ideas.check): each format once a batch; none the product's last batch used (novelty log `format`); at
  least one format of the strategist's own (two with 6+ ads) that no earlier batch used; no line an earlier static carried (the
  product name alone may repeat). The packet lists the library, the formats used before and Meta's rules.
- **Meta / truth** (the check refuses): fake interface (play buttons, notifications, chat bubbles, sliders, app or phone screens,
  "shop now" buttons), real publications or brands (the masthead is LIBRA), price figures (the price test; the model may draw a
  wrong number: say the %), the bag open or its inside (no photo of it: the model invents one), a face (people only from behind or
  hands); compliance runs on every word.
- **Realism** (#6, #8 "make it realistic"): the photo formats ask for a candid phone photo / a lived-in room, real light and
  textures, small imperfections, nothing glossy or CGI. The 2026-10-26 retest (B000, 9 credits): the POV street and the gift tag
  read as real photos; captions came out too small until the prompt asked for "big, easy to read on a small phone screen".
- **Gate:** `ai_gen gate` also reads the words back (tesseract, three sizes): a % the words do not have fails the still; words not
  read back are a "look" (stylised type fools OCR). The agent reads every word on the contact sheet. About 1 credit an ad.

### 4i. Batch branches merge themselves (owner 2026-10-25: "instead of me typing merge every time, add it to the pipeline")

A Slack / Claude DM run can only push to its own `claude/<name>` branch, so its ledger entry, novelty log and specs never reached the
default branch: the next run took the same batch number and repeated hooks (B019, B020, B025 had to be merged by hand). The GitHub
Action `.github/workflows/merge-batches.yml` runs `pipeline/merge_batch.py <branch> --push` at every push of a `claude/*` branch:
- **Batch output only:** specs (`pipeline/recipes/`), the ledger, `docs/BATCHES.md`, the novelty log, product files, `clip_index.json` /
  `clip_bank.json`. A branch that changes anything else is left for a person (a warning on the Action run); merge it by hand.
- **Clashes:** the ledger is merged batch by batch and the novelty log product by product against the merge base (where both sides
  changed one entry, the branch's version wins); `docs/BATCHES.md` is rebuilt from the merged ledger. Any other clash stops it.
- **By hand:** `python3 pipeline/merge_batch.py claude/<branch> [--dry-run] [--push]`; `tests/test_merge_batch.py`.
- **Runs at the same time** (owner 2026-10-25: "a blocker if someone starts 2 runs at the same time"): `plan` claims its number in
  Drive (`pipeline/batch_lock.py`, folder "_Batch numbers (pipeline, do not edit)", `data/batch_lock.json`): the next number after
  the ledger, the Outputs batch folders and every claim file; it writes "B026 – <product> – <date> – <id>", waits 2.5 s and lists
  again; the earliest file of a number owns it, a run that lost renames its file "LOST ..." and takes the next number. A redo
  (`--batch-id`) claims nothing. Plan warns when another batch of the same bag is being made (claimed in the last 8 h, no folder
  yet): those two can share a hook or a static. No Drive: the ledger's number with a warning. The merge also refuses two NEW
  batches with one number (a second net). `python3 pipeline/batch_lock.py` lists the claims; `tests/test_batch_lock.py`.

### 4e00. Batch numbers (owner 2026-10-20: "make the batches less confusing with a proper naming convention, so we avoid relaunching the same ads")
Drive had folders named by whatever the request said (`2026-10-16 – Hobo Bag 5 projects 10 statics`, `... hook test 3 videos + 4 statics`)
and every batch of a bag reused S01 / P01_H1 under a date, with a same-day second batch called `_v2` (which reads like a redo). Now:
every batch has a number from `pipeline/data/batch_ledger.json` (B001-B010 = the folders made before it; B011 on), in every file name
(`LC_261020_HoboBag_Evergreen_B045_S01_native`) and at the start of its Drive folder (`B045 – 2026-10-20 – Hobo Bag – 5 statics + 3
projects`); `upload` writes the folder, link and ads into the ledger (+ `docs/BATCHES.md`) and a `<prefix>_ads.csv` with an empty `launched`
column; `plan` flags `repeat:` when a static (layout + photo + words) or a hook line was in an earlier batch of the bag (the ledger and the
novelty log). A redo keeps the number: `--batch-id B045` -> `B045r2`. Never pass `--name` to upload (the free text is what made them alike).
See docs/NAMING.md.

### 4e0. Real footage first (owner 2026-10-20, later the same day; supersedes the AI-first default of 4e)
The owner saw the AI scenes and clips ("very fake, AI-like: the bag, the way it moves and falls into place") and said: use the
footage in Drive (4K too), make the statics from it, a new story every time, generate only what is missing. So:
- The library: ~4,250 videos in Drive `Raw files/`; ~1,200 are raw bag footage (Hobo Bag 577, HOBO 2.0 244, Vintage 237, Slouchy 119,
  2in1 Backpack 19), the rest finished ads and winner RAWs. `clip_index.json` held 87 hand-tagged clips; `footage_index.py` scans the
  others (faces, sharpness, resolution, the client's folder words as the note) and merges the clean ones (`auto: true`).
- Videos: `make_batch.index_clips` feeds them to the shot planner (a clip the last two batches showed is penalised); upload logs the
  clip ids (`clip_id` in the novelty log).
- Statics: `footage_index.frame_bank` takes the sharpest face-free frame of 9 different vertical clips (4K first, other clips than
  the last batches' `frame_clip`, a macro of leather grain last) -> `native` statics with the feature caption the clip's note
  matches ("back pocket hands 4K" -> "Hidden pockets."). The clean cycle with frames: 8 native, 4 studio, offer 2, quotes 2, value,
  stars, checklist, colours 1 each (`static_cycle(..., frames)`).
- Stories: the `day` angle (ugc_script.day_chapter): morning, street, café, crowd, desk, evening, each moment tied to the feature
  that fits it and to footage words of that place (door, walk, cafe, table, stairs ...). A batch has 5 of the 6 angles; the last
  batch's come last.
- AI: only when the product's own material is thin (a new product with few photos / one clip) or `--ai`.
- Drive: the public link answers "Quota exceeded" for files read often; `index_library.range_bytes` / `file_size` read through the
  Drive API with the agent's token first (the token only in memory), `recut.source` caches the clip with those reads.

### 4e. AI scenes of the real bag (owner 2026-10-20, 100 credits per batch, `pipeline/ai_gen.py`)
Why: the client said the statics repeat across batches. What: the real packshot (reference image) placed in a new scene, as
a static (layouts `scene`, `scene_quote`, `scene_price`, about 40% of a batch's statics, more when the real-photo cycle would
repeat a layout) and as 3 s clips (extra shots in the ugc videos; at most 5 per video, each project draws on 4 of the batch's
8). Library: `pipeline/data/ai_scenes.json` (42 scenes: object / worn from behind / hand; add scenes there). Rotation:
`pipeline/novelty.py` logs each upload (`data/novelty_log.json`, commit it); a batch takes the scenes shown longest ago.
Tested 2026-10-20 on the Silhouette Bag (same prompts, same reference):
- Stills: `gpt_image_2_5` (medium, 2k, 1 credit) keeps the bag's shape, zipper tabs and colour and looks like a photograph.
  `kling_omni_image` (0.5) is good for close-ups on the shoulder but the cafe / car scenes look dark and AI.
  `marketing_studio_image` (2) changed the bag's shape: never use it. gpt at 1k high (1.5) is no better than 2k medium.
- Clips: `kling3_0` std 3 s silent (4.5) is steadiest for still scenes (push-in); `minimax_hailuo` 2.3 768p 6 s (6, trimmed
  to ~3 s) for walking and hands. `seedance_2_5` (28) and `grok_video_v15` (13.5) are too expensive for a 3 s filler.
- Faces: ask for "photographed from behind at shoulder height" (a prompt "cut at the collarbone" still showed a chin). The
  DNN face check misses a chin with no eyes and the Haar check fires on hair / linen: the agent LOOKS at the contact sheet.
- Gate (`ai_gen.py gate` / `clips`): face (YuNet), the bag's colour present, sharpness, motion / black / frozen frames,
  conform to 1080x1920 / 30 fps with grain and the real footage's saturation / contrast. Failed or rejected assets fall back
  (`ai_gen.apply`, run by `render`): the static returns as the real-photo static it replaced, the shot becomes the block's real spare.
- Cost of a full batch (20 statics + 5 projects): ~12 statics 12 + 8 clip start stills 8 + 8 clips ~42 = ~58, voiceover ~22, total ~80.

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
  | Hobo 2.0 "6-Layer Security Edition" | $79.95 ($159.90) | Black, Brown, Beige (Beige was sold out in early Oct, back on the site by 10-09; `plan` reads the colours from the site) | RFID protection, lockable zippers, cut-resistant strap, hidden pockets, smart compartments, table security strap |
  | Hobo Bag 3-Piece Set | $69.95 | Brown, Black, Blue, Grey, Purple Red, Red | hobo + crossbody + matching pouch |
  | Slouchy Soft 3-Piece Set | $69.95 | | |
  | Vintage Bag | $44.95 | Ginger Brown, Black, Chocolate, Red | one-hand clasp, compartments, adjustable/removable strap |
  Always re-check with `pipeline/site_assets.py` (prices change).
- **Offer (per product, 2026-10):** Hobo Bag 50% off + free matching pouch wallet; Hobo 2.0 50% off + free pouch
  wallet; Vintage 50% off (no gift); Hobo 3-Piece Set and Slouchy Set 60% off ($69.95 vs $174.88; the pouch is one of
  the three pieces, not a gift). Free US shipping store-wide. Site banner: "FINAL CLEARANCE SALE ENDS TODAY 50% OFF +
  FREE SHIPPING". `make_batch.py plan` reads the % and the gift from the site on every run.
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
   (The 10-02 test also used Kling pro and GPT image high for AI shots: historical, AI images/video are not allowed now.)
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
   - Captions low in the safe zone (centre y 1150, box ~1065-1235: above Meta's Reels UI, which covers the bottom ~35 %),
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
- **AI presenter (V17, historical: not allowed).** CLAUDE.md hard rule 1 forbids AI images and AI video; never remake it.
- **What fits:** packing shots + the site's "what fits" infographic padded to 9:16 (V18).
- **Story** (`plan --story`, or a request that asks for a story / long video): 1.5-2 min, QA 60-130 s: every feature,
  the real customer in full, the colours, as many reviews as fit, the offer. It runs as long as the real material
  allows (Hobo Bag ~105 s, Vintage ~75 s; a bag without customer clips ~45-55 s: plan warns, add `--lines` or use the
  showcase).
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

### 4d. AI shots (Higgsfield): HISTORICAL, NOT ALLOWED
Kept only as a record of the 10-02 test. CLAUDE.md hard rule 1: no AI images, no AI video, the Higgsfield image and
video tools are blocked. Do not follow these steps.
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
wallet", urgency lines ("ends tonight": 113-H2 is the best winner for this), dark/bold statics (`bold` layout, red
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
| No wrong claims in RAWs | C9_V2 says "two-year warranty" (site: 1 year) | cut 28.16-30.3 in `clip_bank.json` |
| No health claim in a RAW body | 94 "a strap that prevents shoulder pain" shipped with "Compliance: ok" | `compliance.raw_audit` scans the RAW words each version plays; `claim_cuts` in `clip_bank.json`; plan leaves out a winner that still has one |
| No talking customer as B-roll | her lips moved under the narrator before she was introduced (54.0 / 63.3 were not silent) | transcript check on every pick (`make_batch` / `projects.py cadence`), her clip is her scene only |
| No 11-15 s single shot | the customer section was two unbroken shots (38% of the ad) | `storyboard.cut_points`: a new framing every ~3.2 s; `projects.py check --build` flags any picture over 5 s |
| Customer -> narrator handoff | the narrator started 0.1 s after her last word | `storyboard.CLIP_PAD` 0.5 s |
| Caption wording | whisper on the final mix: "phobo bag", lost punctuation, phrases split mid-sentence | captions from the script / committed transcripts (`transcript` in the EDL) |
| Captions over the end card | moved up to mid-screen during the last 2.6 s | dropped (or ended) where the end card starts |
| Captions in the Reels UI | 2-line captions reached y 1355 (Reels covers the bottom ~35 %) | `longform.CAP_Y` 1150, `SAFE_BOTTOM` 1250 |
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
- **Costs (credits):** TTS 0.15-0.45/line (`plan` estimates 0.35/line; a 20 statics + 10 videos batch is ~13-27
  lines, 5-10 credits). Statics and real-footage edits cost nothing. Historical, not allowed now: Kling pro 5 s 12.5,
  GPT image 2K high 2.75 (the 10-02 test with AI shots cost 70-200 credits for 40 ads).

## 8. Reply format (Slack / app)

One short message: Drive folder link; one line per ad (name, angle, length); credits used (balance before
and after); anything skipped, failed or needing a human (e.g. "V03 is 31 s, under the 35 s target: the product
file needs more clips").

## 9. Compliance (Julian, media buyer, 2026-10-09)

AI is fine (the client's Susan persona is AI), but never, in a creative or in ad copy: health or medical claims (cure,
heals, pain relief, arthritis relief, doctor-recommended, therapeutic, posture ...), prescription drugs, politics,
religion, blood or violence (not even a drop of blood), profanity. On top of that (CLAUDE.md rule 3): no invented
numbers or stats, no claim the facts don't back ('waterproof', 'handmade', 'best-selling', '10,000 customers', RFID on a
bag that has none), no fake testimonial in the brand voice ('I bought mine', 'my sister'), nothing beyond the real offer.

`make_batch.py plan` (and `projects.py expand`) run it at the end and exit 2 on a problem; `render` runs it again and
refuses until it passes; by hand: `python3 pipeline/compliance.py --out $OUT` (after editing a line or `ad_copy.csv`).
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
- **Refining:** the Slack session may rewrite any field within these rules, then re-runs `compliance.py --out $OUT`.
- Example (Hobo Bag, Black Friday, S04 review static): primary text 1 "Stop digging for your keys at the bottom of
  your bag. / Black Friday: 50% off the Hobo Bag + free wallet."; headline 1 "\"Best bag I have ever bought\"",
  headline 2 "50% Off the Hobo Bag + Free Wallet", description "Black Friday: 50% off", CTA Get Offer.

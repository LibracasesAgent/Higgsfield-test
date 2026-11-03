# How to make Libra's all-time best ad: research and blueprints (2026-11-03)

Tags: [V] read on the page itself; [S] vendor or agency claim, method not shown; [I] our inference; [U] not verified.
Sources in full (every bullet with its link): `docs/research/2026-11-sources/` A (what the best Meta ads share), B (the buyer and
the category), C (the Q4 calendar and statics). The runnable blueprint sheet: `docs/research/blueprints/hobo-2-0-best.json`
(passes `ideas.py check`). Our data: the newest weekly brief (14-20 Sept 2026, still the newest in Drive), the Meta screenshot of
our 8 AI ad sets (18-26 Oct), the winner RAW transcripts (`pipeline/data/transcripts`), the strategy sheets in `pipeline/recipes/`.

## 0. The answer in one page

The best ad Libra can make is **one real woman, about 45-65, who owns the bag, telling one true moment where it mattered, in her
own words, to camera, 60-80 s, with three numbered reasons her hands show, the doubt she had said out loud, an "ordinary bag vs this
one" contrast, and the offer twice, run as a partnership ad from her own account.** That is what the account's money says works
(the creator winners: CPA $22-31, CTR 4-10%), with the one thing that makes the current winners risky taken out: the invented story.

Our AI pipeline cannot make that ad (it may not invent a customer), so it should make the closest true thing and stop making what
loses:

1. **Contrast beats lists.** Our only AI batch above the account average is B017 (Hobo 2.0, ROAS 2.94 on $518): the "ordinary bag
   vs the Hobo 2.0" video (2.97) and the statics around "Yes, the zip locks." (2.91). Comparison ads lift attention and purchase
   intention, most for challenger brands (meta-analysis) [V]. Blueprint 1 builds on it.
2. **One idea per video, shown not told.** Our losers are the engine's feature lists ("n things", "stop ...": 1.69-2.21).
3. **Four hooks are one ad to Meta.** Meta groups ads with the same look and story (Meta, Dec 2025) [V]; only new people, footage,
   pain point, body or format count as a new concept [V]. A batch of 5 projects is 5 bets, not 20.
4. **Most ads never win.** 4-9% of ads become winners (Motion, 578,750 ads) [V]. We judge a batch by whether it finds one, at
   ~15 purchases per concept, not by its average at 7.
5. **The order-value lever is the 3-Piece Set.** Last December's set ads still ran in September at ROAS 2.85-3.34 with $92-109
   orders. Blueprint 3.
6. **Four claims need the owner before the next big push** (section 4): the AI "Susan" story, the word "leather", a pouch wallet
   that is "free" all year, and Trustpilot (its rating is suspended for fake reviews).

## 1. What our own numbers say

**The account (Sept brief week):** $126.7k spend, ROAS 2.39, CPA $34.84, CTR 6.90%. The 20 ads the brief names: $28.1k, ROAS 2.90,
CPA $28.56, average order $82.70. **Our AI ads (18-26 Oct):** $3.0k, ROAS 2.13, CPA $39.63, average order ~$84.
The gap is purchases per dollar (CPA +39%), not order size.

| Creator winner (persona, product) | Spend | ROAS | CPA | Purchases | CTR | What it does |
|---|---|---|---|---|---|---|
| 123-H4 (Hobo Bag) | $6,117 | 2.66 | $29.8 | 205 | 8.3% | "Hi, I'm Susan, and this is the biggest discount I've ever offered in 31 years." |
| 147-H1 | $5,180 | 2.88 | $28.3 | 183 | 10.5% | A daughter's dialogue: "I love your mom's bags, but can you ask her to lower the price?" |
| 158-H2 | $2,425 | 2.81 | $30.7 | 79 | 9.0% | "Before you buy one of my bags, I need to warn you about something." (fakes) |
| 139-H4 | $2,406 | 2.72 | $29.0 | 83 | 4.7% | "I caved and bought the bag everyone won't stop talking about." + 4 reasons |
| MAX-33-H5 (Vintage) | $2,269 | 2.85 | $27.3 | 83 | 7.8% | "Here are 3 reasons why women have been choosing my vintage bag ..." |
| 94-H4 | $946 | 3.84 | $22.5 | 42 | 5.7% | "I'm closing my workshop after 30 years. But before I do, here are five reasons ..." |
| C9_V2 (Vintage) | $655 | 2.84 | $22.6 | 29 | 7.2% | "I almost didn't buy this because I'm 44, and I thought it was too flashy." |
| 172-H4 (Hobo 2.0) | $225 | 2.95 | $28.1 | 8 | 7.1% | "I genuinely regret buying this bag. Here are three reasons why." |
| DEC08_12/22/23 (3-Piece Set) | $3,484 | 2.85-3.34 | $32-35 | 106 | 2.5-3.2% | last December's set ads: orders of $92-109 |

What the creator winners share (their transcripts): one speaker on camera, first person, 50-85 s at 186-230 words a minute; a first
sentence that opens a loop; a reason the sale exists; 3-5 numbered reasons, each a feature with a picture (the hidden back pocket,
the compartments, the strap); the doubt said out loud ("I thought a secure bag meant a tiny, cramped one", "no ugly tactical
straps"); time as proof ("after a decade"); the offer said twice; CTA "before they're gone". At small spend they hit 3.4-3.8; at
$2-6k a week they settle at 2.7-2.9.

| Our AI ad set (18-26 Oct) | Spend | ROAS | Purchases | Order | What it was |
|---|---|---|---|---|---|
| B017 P04 versus (Hobo 2.0) | $256 | 2.97 | 7 | $109 | voiceover over real footage: an ordinary bag vs the Hobo 2.0, five pairs |
| B017 statics (Hobo 2.0) | $262 | 2.91 | 8 | $95 | AI scenes (weekend, gift, "Zipped shut in the crowd") + "Yes, the zip locks." + "Zips that lock. Lining that blocks." |
| Batch 3 P01 things (Vintage) | $486 | 2.21 | 14 | $77 | engine "n things" |
| Batch 3 P04 value (Vintage) | $490 | 2.16 | 14 | $76 | engine value angle |
| B016 P01 thelist (Hobo Bag) | $264 | 2.06 | 6 | $91 | presenter gift guide |
| B016 P04 retire (Hobo Bag) | $276 | 1.90 | 7 | $75 | presenter: retire your old bag |
| Batch 3 P03 stop (Hobo Bag) | $487 | 1.77 | 9 | $96 | engine "stop ..." |
| Batch 3 P05 things (Vintage) | $490 | 1.69 | 11 | $75 | engine "n things" |

- B017's two winners share a **contrast frame**, **specific security proof on real footage** (lock, cut-resistant strap, RFID, table
  strap), short concrete words, and the Hobo 2.0's higher price (orders $95-109).
- The two presenter projects (B016) did not beat voiceover (1.90-2.06), and they cost ~225 credits each against ~4.6.
- **Sample size:** 7-14 purchases each. With 7 purchases the true rate can be anywhere from 0.4x to 2.1x the count (95%), so 2.97
  could be ~1.2 or ~6. No AI ad is proven yet; the creator winners (66-205 purchases) are.

## 2. What wins on Meta in 2025-2026 (sources A and C)

- **Winners are rare and get most of the money.** Motion (578,750 ads, $1.29B, Sep 2025-Jan 2026): 3.7-8.2% of ads are winners and
  take ~55% of spend; "don't expect more than 1 in 10-13" [V]. 45% of eventual creator-ad winners looked like losers under $100 [S].
- **Diversity is judged by concept.** Meta (16 Dec 2025): it "groups ads that share key visual and thematic attributes"; iteration
  (same visuals, new text) "should not replace" diversification (new persona, motivation, storyline, format) [V]. Agencies: ads
  sharing an opening hook are treated as "essentially the same ad" [V]. Meta (Nov 2024): 20+ diversified ads per Advantage+
  campaign, 20-30% of budget on testing, new ads weekly [V].
- **Formats Meta funds most** (Motion): offer-first banner 21.9% of ads, 29.3% of spend; testimonial and demo are "scale formats";
  text-only and product-image-with-text statics have the best hit rates (11.6%, 8.75%); a product image without text ranks 13th of
  15, carousel last [V]. Fashion's top formats: post-it 27.4%, quiz 26.0%, stylized product shot 21.2%, social comment 14.8% [V].
- **Hooks in the sale window:** newness, sale announcement, price anchor, urgency, offer-only and confession win 8.7-11.4% of the
  time; authority, direct address and relatability 6.4-6.9% [V]. 55% of long-running winners open by simply saying what the
  product or offer is [V]. 82% of scaling ads carry text in the first second; the product works on screen by second 3-8 [V].
  Naming the brand in the first 3 s: +16% completed views (CreativeX, 1.6M ads) [V].
- **Length:** the median winner is 27-30 s [V], but cost per result is flat across lengths (0.94-1.03x) [V] and our own creator
  winners run 50-85 s for an $84 considered purchase. No reason to change rule 6; a 30-45 s body is a test for the owner to ask for.
- **Partnership ads (creator's handle):** Meta's 20 lift studies: 45% lower cost per incremental purchase, 35% higher incremental
  ROAS; it asks for 30%+ of assets as partnership ads [V]. Same ad from the creator's handle: +19% CTR, -5% CPA [S].
- **AI that looks real is fine; AI that looks AI loses.** Columbia/Taboola (4,633 matched ads): AI images that read as real 0.79% CTR,
  human 0.67%, anything that looks artificial 0.55-0.62% [V]. An AI-avatar spokesperson on Meta raised views but cut CTR ~29% [U].
- **Fatigue:** e-commerce ads live a median of 22 days; winning creator ads ~36 days before CPA rises 1.8x [V]/[S].

## 3. The buyer (source B)

- **She is 45-65, on Facebook daily, and rarely sees herself in ads.** Facebook reaches 71% of US adults 50-64 [V]; 68% of women 50+
  rarely or never see themselves in ads [V]. Meta's delivery follows the face: ads with older people are shown to older users
  (peer-reviewed, 78-81% older reach) [V]. **Casting is targeting.**
- **Calm beats hype for her.** Adults 60-85 remembered brands better in calm ads; fast cuts, loud music and "overly excited voices"
  did not help [V]. Faster, more complex sentences lowered recall at every age [V]. Keep our pace, but one idea a sentence, a warm
  voice, soft music, every number on screen.
- **Her objection to the category: anti-theft bags look like tourist gear and weigh a lot** ("neon-signed me as a tourist") [V].
  Her delights: pockets, no digging, compliments, "looks expensive". Libra's real hook is that it looks like a real handbag.
- **Gifting is most of the window.** 92% of Cyber Weekend 2025 buyers bought a gift; 47% prefer one meaningful, higher-cost gift [V].
  55% of shoppers 50+ also buy for themselves in BFCM [V]. "One for my daughter and one for myself" is real behaviour [V].
- **Safety without fear:** quote the travel advice, not the crime ("carry your bag across your body", "use the inside
  compartments", "keep your belongings close in restaurants": UK travel advice) [V]. Never a snatch, a blade, a named "dangerous" city,
  or an unsourced statistic (the Barcelona "100,944" has no primary source) [V].
- Voice-of-customer phrases to reflect in 'you' form: source B, 24 quotes ("No more digging through my purse", "I just don't want to
  look like an easy mark", "The locking zipper was great, I felt safe, even on the Metro").

## 4. The truth line: four things the owner should decide

1. **The "Susan" story.** The account's biggest winners tell a story Julian says is an AI persona (PLAYBOOK §9): a woman who hand-made
   the bags for 30 years, arthritis, closing her workshop, "less than 100 left", "no next batch". The owner approved it for his RAW
   ads. But the same pattern (an AI artisan, a closing-down sale, 50-70% off, handbags) is what the press now reports as an AI
   shopping scam (The Journal 2024-09-16: a "couple closing" a handmade bag business, Meta "looking into" it; Korea Daily 2026-05-12,
   citing ABC News) [V], and the FTC's rule (16 CFR 465, in force 21 Oct 2024) bans testimonials by people who don't exist or who did
   not have the experience [V]. If Meta or the FTC acts, the whole ad account is at risk, not one ad. Our pipeline never writes it
   (rule 3) and the blueprints below keep its mechanics without the fiction. **Recommendation:** brief the agencies for real-customer
   videos now (Blueprint 2), so the account does not depend on the persona.
2. **"Leather".** The site calls the Hobo Bag "luxury leather" and "scratch-proof leather" [V]; Libra's October 1-star reviews say "the
   bag is not leather", "It's a cheap pleather" [V]. We don't know the material. If it is PU, the site and the ads should say "vegan
   leather" (a false material claim is a misleading-claims problem on Meta and with the FTC). **Wouter to confirm.**
3. **A pouch wallet that is "free" all year.** The FTC's guide on "Free" offers allows no more than three a year per product line and
   six months per product (16 CFR 251.1) [V]. During the sale it is fine to say; the year-round "+ FREE Pouch Wallet" is the owner's
   call.
4. **Trustpilot.** Libra's page says "This company's rating is unavailable due to a breach of our guidelines" and "We've removed a
   number of fake reviews for this company" [V, checked 2026-11-03]. Never cite Trustpilot in an ad; use the named, approved reviews.
   Real objections in those reviews (returns to Australia, delivery, email replies) should be answered on the landing page.

Also: a struck-through "was" price must be a real earlier price for a substantial period (FTC 16 CFR 233.1; California: the
3 months before) [V]; countdowns only to the real end (30 Nov) [V]; no stock claims (we have no stock data).

## 5. The recipe: what the best Libra ad does

1. **One person, one true moment.** A real owner (Blueprint 2) or, in our videos, the bag on a woman in the footage and a calm 'you'
   voice; never an invented customer.
2. **The first sentence opens a loop and says what it is.** A contrast ("Most travel security bags look like hiking gear. This one
   looks like a handbag."), a question the picture answers, or the offer as news. Text on screen in the first second, the bag in it.
3. **The category's objection, answered by sight.** It doesn't look like gear; it isn't heavy-looking; the zips lock with one clip.
4. **Contrast, generic and fair.** An ordinary open-top tote, never a brand, never shown as bad, just different.
5. **At most three reasons, numbered, each a proof shot.** The zip clipping shut with its own sound, the strap looped round a chair.
6. **Time and trust, only when true:** the 1-year warranty, the named approved reviews, the real order-by date.
7. **The offer last, said once clearly** (twice in a creator video), the % on screen; the 3-Piece Set as the "Best Value" upgrade where
   the product page offers it.
8. **Calm delivery for her:** warm voice, soft bed, no whooshes, one idea a sentence, big high-contrast numbers.
9. **Cast her age.** Hands and bodies that read 45-65 in the footage; a creator who is the buyer.
10. **A new concept every week**, judged at ~15 purchases, scaled at 2.8+ (section 7).

## 6. Blueprints

### 6.1 Blueprint 1: "The security bag that doesn't look like one" (Hobo 2.0, our pipeline, ready to run)

`docs/research/blueprints/hobo-2-0-best.json`: 3 projects + 6 statics, no presenter, Black Friday; `ideas.py check`: 0 problems.
Cost: ~3 x 4.6 (voiceover) + ~4 (AI ads) = ~18 credits. Every claim is in the Hobo 2.0 packet's facts.

**P01 · The security bag that doesn't look like one** (structure `swap`; leads with LOCKABLE ZIPPERS; 2 proof shots)
- H1 [problem] NOT HIKING GEAR: "Most travel security bags look like hiking gear. This one looks like a handbag." (worn)
- H2 [question] IT LOCKS?: "Would you guess this handbag locks?" (zip_hand)
- H3 [promise] WATCH THIS: "Watch two gold zip pulls clip together, and lock." (lock)
- H4 [price] HALF PRICE: "Half price this Black Friday: a handbag with lockable zippers." (strap)

| # | Beat | Voice | Picture | On screen |
|---|---|---|---|---|
| 1 | now | Most travel security bags look like something you would take on a hike. Clips, mesh, a belt across the front. So they stay in the cupboard, and you carry your everyday bag instead. | worn, outdoor | |
| 2 | switch | The Hobo 2.0 looks like that everyday bag. A classic hobo shape, gold zips, nothing that looks like gear. The difference is in the details you only notice up close. | handheld, worn | |
| 3 | difference (proof, zip sound) | Start with the zips. Clip the two gold pulls together and they lock, so nobody can open the bag behind you in a crowd. | zip_hand, lock, zip | LOCKABLE ZIPPERS |
| 4 | second difference | Then the lining. From the outside you would never know. On the inside it is RFID, so it blocks card scanners while your cards sit in the bag. | inside, pocket | RFID LINING |
| 5 | second difference (proof) | And when you sit down, the table strap loops around your chair. The bag stays right where you left it, next to you, not on the floor. | tie, placed, cafe | TABLE SECURITY STRAP |
| 6 | offer | So it is the bag you would carry anyway, with the security built in. The Hobo 2.0 is fifty percent off in the Early Black Friday sale, with free US shipping. Tap the link below. | worn, strap | |

**P02 · The three bag rules for any trip** (own structure `three_rules`; leads with CUT-RESISTANT STRAP): the rules travel
advice repeats (across your body, cards inside, close at the table), each kept by one feature; calm, no crime, no fear.
Hooks: "The three bag rules for any trip, and one bag that keeps them." / "Do you wear your bag across your body when you travel?" /
"Your cards should never ride at the top of an open bag." / "On a trip, is your bag on the floor or on your chair?"

**P03 · For the mom who spends December on the road** (structure `gift_reveal`; leads with RFID LINING): one named person and her
December; the strap goes on her shoulder (the reveal), two reasons and the locking zips, and the close on the site's real date:
"Order by the fourteenth of December for the best chance of delivery before Christmas."

**Statics** (4 AI-designed + 2 real; two formats of our own):
- S01 `bold_poster` (offer-first, the format Meta funds most): "50% OFF." / "The handbag that locks."
- S02 `post_it` (own; fashion's top format): a yellow note on the front door by the bag on its hook: "Across your body." / "Cards inside. Zips locked."
- S03 `split_compare` (B017's winning frame as a picture): "Which one goes in the crowd?" / "Open top" / "Zips that lock"
- S04 `quiz_card` (own; fashion's #2): "Where do her cards go?" / "A. An open tote" / "B. Behind RFID lining"
- S05 `quotes`: Sarah M.'s review from the Hobo 2.0 page ("I travel solo a lot and this bag has completely changed how safe I feel ...")
- S06 `native`: the real frame of hands clipping the two zip pulls: "Two pulls. One clip. Locked."

Slack message to run it: `Higgsfield-test: Hobo 2.0, 3 videos and 6 statics, Black Friday, no presenter. Use the blueprint
sheet docs/research/blueprints/hobo-2-0-best.json as ideas.json (run ideas.py check on it first; keep its scripts).`

### 6.2 Blueprint 2: "Real women, real bags" (a brief for the agencies: ACH Creative Delivery, Kate Creatives)

The format that made the account's money, made true. Not something our pipeline makes (it may not invent a customer); our winners
pipeline then cuts 4 hook versions from each RAW (`winner_prep.py`), as it does for the current winners.

- **Who:** women who read 45-65, who own the bag and have carried it for a few weeks (a real customer, or a creator who really uses
  it). Run as partnership ads from her handle; ask for account-level permission (Meta's guidance) [V].
- **Where and how:** one take to camera at home, in the car or at a cafe table; cut-ins of her own hands using the bag; 60-80 s;
  her own words, unscripted lines in the order below; captions; no music under her voice or a very soft one.
- **Structure:** (1) her first sentence, true for her: the doubt ("I almost didn't buy this because I thought anti-theft bags all
  look like tourist gear"), the moment ("Last month at the airport ..."), or the contrast ("Before you buy a travel bag, check these
  three things"); (2) the offer once, early ("It's half price right now, which is why I'm telling you today"); (3) three reasons,
  numbered, each shown by her hands (the hidden back pocket against the body, the side zip, the compartments; Hobo 2.0: the lock,
  the table strap); (4) the doubt answered by sight; (5) the offer again and "the link below".
- **Never:** health or body claims (shoulder pain, arthritis, posture), a theft that did not happen to her, "handmade", "last batch",
  "closing down", years she has not carried it, "theft-proof", a price that is not live, Trustpilot.
- **Volume:** Motion's data says ~1 in 10-13 creatives wins; agencies at this spend ship 10-20 new ads a week [V]. Ask for 8-12
  creators, one video each, before asking for more takes of one.

### 6.3 Blueprint 3: "One for you, one for her" (the 3-Piece Set, order value)

- **In every Hobo Bag batch:** one offer chapter may add the set as the page's "Best Value" upgrade ("Or take the 3-Piece Set: the hobo,
  a crossbody and a matching pouch, at sixty percent off."). The 60% is said only of the set (campaign rule).
- **Statics for a 3-Piece Set batch** (the strategist writes them into the run's sheet; the sheet needs a carrier project, as B029 did):
  S01 `bold_poster` "60% OFF." / "Hobo, crossbody and pouch." · S02 `gift_moment` two kraft tags on the hobo and the crossbody:
  "For you. For her." / "One set, three pieces." · S03 `window_display` the three pieces on plinths: "THE SET: 60% OFF" · S04 own
  format `calendar_note` (a desk calendar with the 14th circled): "Order by 14 December" / "Best chance of Christmas delivery" ·
  S05 `studio` "Three pieces. One set." · S06 `quotes` Carol R.: "Already bought for friends."
- **Copy:** "One meaningful gift" (Deloitte: 47% prefer one), the three pieces named, the % (under $100 a % reads bigger than dollars) [S].

## 7. Test plan (with the profit thresholds)

Margin after ads ~= 55% - 1/ROAS (our inferred model; Wouter's real cost per order makes it exact): break-even ROAS ~1.8, his old
~20% margin at 2.8 (CPA ~$30 at an $84 order).

- **One project = one ad set** (its 4 hooks inside it compete; projects don't share delivery). A static set of one batch = one ad set.
- **Budget to a first read:** ~15 purchases = ~$450-600 at CPA $30-40. **Turn off** at $150 with 0 purchases and CTR under the account's
  half (~3.5%), or at the read with ROAS under 1.8. **Keep** 1.8-2.8 (try its best hook in a new body). **Scale** at 2.8+ over 15+
  purchases, and call it a winner at 40+ (the creator winners have 66-205).
- **Testing budget:** Meta asks for 20-30% of spend on new ads [V]; at ~$125k a week that is ~$25-38k. Our AI ads got ~$2.3k a week in
  late October: too little to find a winner among 20+ new ads.
- **What to measure** per ad (into the ad tracker's columns: spend, impressions, 3-s plays, clicks, purchases, revenue): hook rate (3-s
  plays / impressions; 30%+ is solid, 40%+ elite [S]), CTR, CPA, ROAS, order value.
- **This month's order:** run Blueprint 1 (Hobo 2.0) and a Hobo Bag batch with the 3-Piece Set close; brief Blueprint 2 now (creator
  videos take 1-2 weeks); compare at ~15 purchases each.

## 8. The Q4 calendar (source C; the 2025 cost changes are for the same weeks)

| 2026 | Cost in 2025 | Say | Run |
|---|---|---|---|
| 16-22 Nov | CPM +9%, cost per purchase -16% | "Black Friday prices are live now"; start gift lines ("order by 14 December") | the proven B017 frames with the sale line; Blueprint 1; gift statics in a small test |
| 23-29 Nov (BF Fri 27) | CPM +35% (BF day +84%), cost per purchase -20% | the deal: 50% off, up to 60% off the 3-Piece Set; "the sale ends 30 November" | offer-first statics, the set; nothing new launched mid-week (build by 20 Nov) |
| 30 Nov - 6 Dec | CM day +71% CPM; week CPM +27%, cost per purchase -8% | 30 Nov only "ends tonight"; from 1 Dec the regular offer + "the gift for her: order by 14 December for the best chance of Christmas delivery" | every sale ad and end card off at 30 Nov 23:59; winners re-captioned with the gift line |
| 7-13 Dec | **the worst week of 2025**: cost per purchase +39%, ROAS -27% | the deadline: order by Monday 14 December | warm audiences first, cold prospecting cut |
| 14-20 Dec | CPM +3%, cost per purchase +8% | 14 Dec only "last day for the best chance of Christmas delivery"; from 15 Dec no Christmas-delivery line: self-gift, "a bag for the new year" | low spend; there is no gift card (libracases.com/products/gift-card is a 404) |
| from 21 Dec | cost per purchase -26% (22-28 Dec), -24% (29 Dec - 4 Jan) | fresh start, self-gift | the next batch's new concepts while CPMs are cheap |

The repo already blocks "last chance / final days" before 20 Nov and "ends tonight / today only" except on 30 Nov
(`data/campaign.json`). Missing: the offer from 1 December (ask Wouter) and a December gifting campaign entry (section 9).

## 9. Pipeline changes

Done now: this file; the sources; the runnable Hobo 2.0 blueprint sheet; the strategy packet lists only the `.md` notes in
`docs/research/` (the sub-folders are linked from here).

Proposed (each needs the owner's yes; none changes the batch format by itself):
1. **The presenter becomes a test, not a default.** One presenter project per batch costs ~225 credits against ~4.6 for a voiceover
   project; B016's two (1.90, 2.06) did not beat voiceover, and an AI spokesperson cut CTR in a Meta field test [U]. Proposal: make
   one presenter project a month until one beats the voiceover projects at 15+ purchases.
2. **A December campaign entry** in `data/campaign.json` (1-14 Dec: the gift line and the 14 December fact; from 15 Dec: no
   Christmas-delivery words), once Wouter gives the December offer.
3. **The brand in the first 3 s:** the H1 label or first caption carries "LIBRA" or the bag's name (+16% completion, CreativeX) [V].
4. **New AI ad formats** for the library once tested in Blueprint 1: `post_it`, `quiz_card`, `calendar_note`, a billboard (fashion's
   top formats); a "social comment" only as a verbatim review set as type, never a fake app screen.
5. **The weekly brief stopped after 22 Sept** (the newest in Research Briefs, now 42 days old). The winners pipeline reads it: restart
   the n8n report, and add our AI ad sets' results to the ad tracker each week (no results are typed there yet).
6. **Results-driven ideas:** once the tracker has ROAS per ad, the strategy packet lists the product's best and worst structures and
   formats, so each batch builds on what sold, not only on what is new.

## 10. Questions for Wouter and Julian

1. What is the offer from 1 December, when the Black Friday sale ends?
2. What are the Hobo Bag and the Hobo 2.0 made of: genuine leather, or vegan / PU leather?
3. Is the pouch wallet free all year, and is it still on the Hobo 2.0?
4. Will you brief ACH / Kate Creatives for real-customer partnership videos (Blueprint 2)? Do you have customers who would film?
5. Keep the presenter in every batch, or make it a monthly test (section 9.1)?
6. Can the weekly brief run again, and can Julian export our AI ad sets' results each week (spend, purchases, revenue, 3-s plays)?
7. The "Susan" ads: keep running them as they are, knowing the risks in section 4?

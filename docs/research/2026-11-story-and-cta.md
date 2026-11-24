# Story videos, story hooks and the CTA at the end (2026-11-24)

Why: the owner says our 55-80 s ugc videos read like feature lists and sales pitches. He wants (1) a real story (a character, a
situation, tension, a turn, a payoff) that makes the viewer feel "I want this", (2) the CTA only at the end, (3) a hook that opens the
story and is never an offer ("50% off ...", "Half price plus a wallet" hooks are out). This file collects what the sources say and
turns it into checkable rules for the strategist (`ideas.json`, `pipeline/data/story_structures.json`).
Tags: [V] verified in a primary / credible source, [S] a secondary or vendor source (method not public), [I] our inference,
[U] unverified. The Meta Ad Library is not reachable from here.

## 1. Does a story beat a feature list? (the evidence)

- **Ipsos "Misfits Stories" (2025, ~15,000 video ads, Creative|Spark)** [V]: a story = "a sequence of events with characters and
  outcomes". Only about half of ads try to tell one (59% on most Ipsos pages, 49% "clear sequence, characters and outcomes" in the
  WFA summary). Ads that tell a story are **about twice as effective at changing behaviour** as ads built mainly on product features
  or brand promotion, and the WFA write-up puts the behaviour lift at ~30% when value is delivered through a story with an arc,
  characters and an outcome; story / unexpected tactics encode in memory ~2.7x better. Not Meta-specific, not DTC-specific.
- **Kantar x Meta x CreativeX, "The New Era of Storytelling" (Nov 2024, 56,984 Meta assets, 1,295 campaigns, 13.1 bn impressions)**
  [V]: one human on screen / eye contact +81% effectiveness, "human vibe" (one person, visible face) >+100%; visually dynamic ads +74%;
  fast storytelling (4 scenes in 6 s) +73%; only 36% of campaigns integrated the brand and product INTO the story. Measured on brand
  and sales lift (LIFT ROI studies incl. apparel), not on ROAS.
- **Meta x Toluna (~100 Reels ads x ~100 viewers, DE/UK/IT/TR)** [V]: for purchase intent, brand + core message in the first 5 s
  = 1.7x more likely to score high; repeated branding through the ad 1.8x vs a single end-frame logo; direct-to-camera, lower-fi
  "native" creative beat polished; for lower-funnel ads, branding under ~25% of the runtime did better. Nothing on story or CTA.
- **System1 x TikTok (887 short-form ads, 92,000+ viewers, matched to 350+ lift studies)** [S]: the most entertaining ads get 54%
  more 6 s view-through and 40% more positive sentiment; "fluent characters" (a recurring character) reported at +67% (metric not
  stated in the coverage) [U on the 67%].
- **Binet & Field / IPA** [S]: emotional campaigns are far more likely to produce very large profit effects than rational ones; John
  Lewis's Christmas story films 2012-15: +16% festive sales, ~GBP 8 profit per GBP 1 (IPA Grand Prix 2016; agency-written paper).
  These are brand films on TV, long-term effects: not proof that a story beats an offer ad on a 7-day click window.
- **The counter-evidence** [S]: in Billo's six months of creator ads, the top performers by CTR almost all closed with a hard,
  specific CTA (74%; all top 5), and a real offer line ("It's 50% off right now ...") was among the best closers. Vendor data.
  Motion speakers: a low thumbstop with a high conversion rate = "the hook is weak but the story is working": swap the first 3 s.
- **What it means for us** [I]: the data back a story BODY with a real character and outcome, a person on screen, fast cuts, the
  product inside the story, and a clear hard CTA with the real offer AT THE END. Nothing in the sources says the offer must open the
  ad; the closer format (25-35 s, offer-led, PLAYBOOK 4i) is the one place where it does, by design. No head-to-head study of story vs
  offer ads on Meta ROAS was found [U]: our own weekly review (section W) is the test.

## 2. Story structures for a 55-80 s ad (beats and timings)

Pace: ~185-215 wpm = 170-285 words in 55-80 s; a new shot about every 2 s. Timings below are for a ~65 s video [I]; the vendor
templates give the same proportions at 30 s (hook 0-3 s, problem 3-8, agitate 8-12, solution, offer/CTA in the last ~5 s) [S].
TikTok's own storytelling one-pager: beginning 3-5 s (a question, a hook, an eye-catching visual), middle (3-5 benefits framed as
solutions to a problem or reasons), end 3-5 s (how to buy, a specific occasion: "The perfect birthday gift", "Not sure what to get
your partner for [holiday]?", the deal) [V]. Every structure ends the same way: payoff, then the offer + CTA (section 4).

| Structure | Beats (65 s) | Source |
|---|---|---|
| **Story spine** (Kenn Adams 1991, popularised by Pixar's Emma Coats) | Once there was / every day (0-8 s) - one day (8-14) - because of that x2-3 (14-40) - until finally (40-52) - ever since (52-58) - offer + CTA (58-65). "Ever since" must differ from "every day": the ending has to show change | [V] origin; [S] ad use (Kimp) |
| **PAS as a scene** | Hook = the problem happening (0-3) - the problem lived (3-12) - agitate: what it costs her (12-22) - the turn: the bag (22-30) - the fix shown twice (30-50) - payoff (50-57) - offer + CTA | [S] |
| **Before - After - Bridge** | Before: the old moment (0-15) - After: the same moment, easy (15-30) - Bridge: why, 2-3 features shown (30-55) - offer + CTA | [S] |
| **A day / four places** | Morning - commute - work / cafe - evening; each place one feature that only matters there; payoff: she gets home with everything | [I], `story_structures.json` |
| **The moment** (one scene, slow) | One situation (a crowded market) told in real time: setting, the risk, the one move (the hidden back pocket), the relief | [I] |
| **Gift reveal** | Who she is (0-10) - what she carries / complains about (10-25) - the wrapping, the reveal (25-35) - why it fits HER (35-52) - payoff: she uses it - offer + CTA | [I]; TikTok occasion CTA [V] |
| **Advice to a friend** | 'You' talks to a friend: her problem, what you would tell her, three reasons, "send her this" | [I] |
| **Myth vs fact / the test live** | A belief or doubt ("a bag that holds everything is heavy and ugly") - tested on camera - result - offer + CTA | [I] |

What makes it a story and not a list [V Ipsos definition + I]: a **named situation** (a time and a place), a **person** the viewer
can be ('you', or a narrator about 'her'), **tension** (something can go wrong or is annoying), a **turn** (the moment the bag
changes it), a **payoff** (how it feels / what is different now, shown on screen). Features enter only as the means of the turn:
at most 3, each one tied to a moment of the story. A chapter that could be moved to another position without breaking the story is
a list item, not a beat [I].

**Our limits** [I, PLAYBOOK §1, CLAUDE.md rule 3]: no invented customer and no first-person claims ("I bought", "my bag saved me");
"the moment it saved me" becomes "the moment it saves you" ('you' form) or a narrator about "her" as a scenario, never as a review.
No invented results ("she never lost a thing again"); a payoff is a feeling or a fact the product backs ("your phone is where your
hand expects it"). The presenter is a host, not a customer.

## 3. Story hook vs CTA hook (first 3 s)

- Hooks are judged in the first 2-3 s; feed video autoplays muted, so the first frame must work as a picture and the words must be
  on screen [S]. TikTok: ~90% of ad recall impact within the first 6 s [S, TikTok-cited]. Meta/Nielsen (as cited by vendors): 65% of
  people who watch 3 s watch 10 s [U].
- A **CTA / offer hook** tells the viewer the deal before they want the thing ("Half price plus a free wallet"). It filters for
  deal seekers and works in a closer [I, PLAYBOOK 4i]; it also spends the strongest line before there is a reason to care, and the
  rest of the video has nowhere to go [I].
- A **story hook** opens a loop that only the video closes: the situation already in motion (in medias res), a question the viewer
  has asked herself, a result shown first and then rewound, a narrator introducing a character ("This is Amanda. She's 29 ...": the
  narrator-voiceover hook on Runneth/Motion's DTC hook list) [S]. Failure mode: a loop answered by something generic feels like a
  trick [S].
- No source ranks story hooks against offer hooks by data [U]. Motion / Runneth hook lists rank nothing; their advice is to test 3-5
  hooks on one body [S], which our H1-H4 already do.
- **Story-opening hooks for a handbag** [I] (the first picture: a movement or a person, never a packshot):
  - "It's 8:40, the train is packed, and your phone is in the bottom of your bag." (hand digging in an open tote)
  - "You know the market stall where everyone stands too close?" (crowd, bag worn, from behind)
  - "She's carried the same bag for nine years. Here's what you get her this Christmas." (wrapped box)
  - "Watch where the cards go." (hand slides a card into the back pocket)
  - "Your keys are always the last thing you find." (keys at the bottom of a bag)
  - "This is what you pack the night before a trip." (packing on a bed)
  - "Everyone at dinner asked about one thing." [U: only with a real basis; prefer the others]

## 4. The CTA at the end of a story ad

- **Placement** [S]: the closing line carries the ask; a soft CTA placed before the viewer understands the value underperforms; the
  common pattern is a payoff, then the offer, then the ask, in the final ~20% with the button visual and a spoken line. Billo: 6 of
  the top 10 ads also had a mid-video line that built intent ("If you hesitated on any of those ...") [S]: for us that is a story
  beat, never an early offer.
- **Hard vs soft** [S]: hard, specific CTAs won in Billo's data (74% of top performers; naming the brand / URL beat a bare "link
  below"); the only soft CTA that worked was a genuine testimonial (we can't use invented ones). Others: soft for cold audiences,
  direct for warm [S]. Ours: one hard close is the rule ("Tap the link below.", PLAYBOOK), plus a soft bridge sentence from the payoff
  into the offer ("If that's the bag you want on your shoulder ...") [I].
- **Offer reveal after the payoff** [I]: the % and the gift land as the reward for having watched, in the last chapter only,
  ~5-8 s: one sentence for the offer (real %, real gift, Black Friday until 30 Nov only where the campaign says so), one for the ask.
  Spoken AND on screen (the end card: the bag, the name, the offer pill, the button, inside the safe zone) [V Meta/Toluna: audio +
  visual cues beat visuals alone].
- **Occasion CTA** [V TikTok]: "The perfect gift for ..." is a recommended close; it fits the Christmas stories.
- **Branding** [V Meta/Toluna]: show the brand / bag early and repeat it (1.8x vs a lone end logo): the bag is in the story from the
  first seconds, the CTA is not. Brand in the first 5 s != offer in the first 5 s [I].

## 5. Pure story videos vs salesy / offer videos: when each works

| | Story video (55-80 s, ugc / presenter) | Offer video (closer, 25-35 s) |
|---|---|---|
| Job | make her want the bag; new and cold audiences; long life | convert people who already want it; retargeting, sale peaks |
| Hook | the situation / a question / the bag in motion | a warning or the offer itself (PLAYBOOK 4i) |
| Offer | last chapter only | from the first line |
| Evidence | Ipsos 2x behaviour, Kantar human / pace levers [V] | Billo hard CTA + real offer [S]; our 30-day winner 190-H3 (27 s) [V internal] |
| Risk | a slow start loses the scroll; a vague payoff | fatigue, deal-seeker audience, no reason to remember the brand |

[I] Run both, labelled: story projects are the default of a batch; a closer is made only when the request asks for one (CLAUDE.md
section 4). In Black Friday weeks the story still ends on the sale; it does not open with it.

## 6. Example story outlines for our bags ('you' form or a narrator about 'her'; facts from PLAYBOOK §1 only)

Each: ~65 s, 6-9 chapters, offer last, hook types differ. Footage tags in brackets are what the picture must show.

1. **"The 8:40 train" (Hobo Bag, the moment)** - Hook: "It's 8:40, the train is packed, and your phone is somewhere in your bag."
   [hand digging, worn] - Situation: standing, one hand on the rail [worn, street] - Tension: someone close behind you, your wallet is
   in the outside pocket of your old bag - Turn: the hidden back pocket against your body [pocket, proof_shot] - Because of that: phone
   in its own compartment, you find it without looking [inside, hand] - Payoff: you step off with both hands free, nothing to check
   [walking] - Offer + CTA.
2. **"Ever since the market" (Hobo Bag, story spine)** - Every Saturday you go to the market - one day the crowd is tight at the fruit
   stall - because of that you hold your bag in front of you the whole time - until you carry one where the cards sit in a hidden back
   pocket [pocket] and the straps go crossbody [strap, worn] - ever since, your hands are for the peaches - offer + CTA.
3. **"The night before" (Hobo Bag 3-Piece Set, BAB)** - Before: the bed covered in three half-packed bags [packing] - After: the same
   bed, one hobo, one crossbody for the day out, one pouch for the small things [set] - Bridge: what goes where [inside, zip] -
   payoff: you zip it and turn off the light [zip, proof_shot] - offer: three pieces, 60% off - CTA.
4. **"One hand" (Vintage Bag, the test live)** - Hook: "Try opening your bag with a coffee in your other hand." [cafe, hand] -
   tension: the coffee tips while you fight a zip - turn: the one-hand clasp [snap, proof_shot] - because of that: compartments, the
   card is where you left it [inside] - payoff: you pay, close it, still holding the cup - offer + CTA.
5. **"What you carry now" (Hobo 2.0, myth vs fact)** - Hook: "You think a secure bag has to look like a backpack." [worn, street] -
   fact 1: lockable zippers [zip] - fact 2: RFID protection for your cards (said plainly, no fear claims) - fact 3: the table strap at
   the cafe [strap] - turn: it still looks like a handbag, and the second strap makes it crossbody - payoff: walking out of the cafe
   [walking] - offer + CTA.
6. **"Advice to your sister" (Hobo Bag, advice to a friend)** - Hook: "If your sister still keeps her cards in her coat pocket, send
   her this." - her situation (busy, two kids, bag on the stroller) [worn, street] - what you'd tell her: two straps, three ways to
   carry it [strap] - the hidden back pocket [pocket] - payoff: "she'll stop patting her pockets" - offer + CTA.
7. **Christmas: "Nine years, the same bag" (Hobo Bag, gift reveal)** - Hook: "She's carried the same bag for nine years." [worn,
   old bag on a chair] - who she is (narrator about 'her': mum, the one who carries everyone's things) - tension: she'd never buy
   herself a new one - the turn: the box under the tree, the leather, the colour she'd pick [gift, colours] - why it fits her: soft
   leather, compartments for everything she carries for everyone [inside] - payoff: Christmas morning, the old bag gets emptied into
   the new one [packing, proof_shot] - offer (50% off + the free pouch wallet, only while the site says so) - "The gift she won't buy
   herself. Tap the link below."
8. **Christmas: "Three people, one set" (3-Piece Set, gift guide as a story)** - Hook: "Three people on your list, one box." [gift,
   set] - your mum: the hobo for every day [worn] - your daughter: the crossbody for the city [strap] - you: the pouch, because you
   deserve something too [pouch] - tension: the wrapping, who gets which colour - payoff: three bags by the tree - offer: the set, 60%
   off - CTA with the occasion.
9. **Christmas: "The last-minute shopper" (Vintage Bag, POV)** - Hook: "POV: it's December and you still have nothing for her."
   [street, walking, shopping bags] - the scroll through ideas that don't fit her - the turn: a bag she'll use every day, with a clasp
   she can open with one hand [snap] - payoff: wrapped, ribbon, done [gift] - offer + CTA. No delivery-by-Christmas promise unless the
   site states one [I, rule 3].

## Rules for our strategist (checkable in `ideas.json`)

1. Every project has a named **situation** (a time + a place in one phrase), a **tension** beat, a **turn** beat and a **payoff**
   beat; `beat` names them, and the turn is the first chapter where a feature appears.
2. **No hook may be an offer or a CTA**: no %, "off", "half price", "sale", "free", "gift with", price, "deal", "shop", "tap" or
   "link" in any hook line or hook label (closer projects excepted, when the request asks for closers).
3. The hook opens the story: it states the situation, the tension or a question, and its first `show` tag is a movement or a person
   in that situation (never hero / packshot / colours).
4. The %, the gift, the sale, the bundle price and the CTA appear **only in the last chapter** (beat `offer`); no mid-video offer line.
5. The last chapter is offer + one hard ask, ~5-8 s: one sentence for the offer, one ending "Tap the link below."; the same offer is
   on the end card.
6. The payoff chapter comes right before the offer and shows the changed moment on screen (worn / walking / hands free / zip closed).
7. At most 3 features per project, each tied to a beat of the story; a chapter that can swap places with another without breaking
   the story is rewritten.
8. 'You' form or a narrator about "her"; never "I / my / me" as a customer, no invented results, numbers or reviews in the story.
9. The bag is on screen inside the story within the first 5 s (brand early, offer late).
10. Each project of a batch uses a different structure (story spine, PAS scene, BAB, the moment, a day, gift reveal, advice to a
    friend, myth vs fact, POV) and the 4 hooks use at least 3 hook types (situation, question, result-first, narrator, POV).
11. A person (worn, walking, hands, or the presenter) is on screen in at least two chapters; a new shot about every 2 s.
12. Christmas / gift stories name who the gift is for and why it fits HER; the close may use the occasion ("the gift she won't buy
    herself") but never a delivery date or a sale end the site does not state.
13. Story projects are the default; an offer-led closer is made only when the request asks for one, and is labelled `format: closer`.
14. `why_new` says which situation and which turn no earlier batch used.

## Sources

- Ipsos, Misfits Stories: the power of storytelling in creative effectiveness (2025): https://www.ipsos.com/en/misfits-stories
- Communicate Online on the Ipsos study: https://communicateonline.me/news/ads-that-tell-stories-outperform-feature-led-campaigns-ipsos-study-finds/
- WFA, Storytelling: the creative effectiveness superpower: https://wfanet.org/l/mailing2/link/de3002fe-e7a0-4008-9f08-e2820a833693/67114
- Kantar, The New Era of Storytelling (with Meta and CreativeX, Nov 2024): https://www.kantar.com/north-america/Company-news/The-New-Era-of-Storytelling
- Meta x Toluna, what makes short-form video ads work: https://tolunacorporate.com/what-makes-short-form-video-ads-work-meta-toluna-study/
- System1, The Long and the Short (form) of it: https://system1group.com/blog/how-to-make-entertaining-short-form-ads-for-tiktok-social
- B&T on the System1 x TikTok study: https://www.bandt.com.au/attention-is-skippable-system1-reveals-how-to-harness-the-magic-of-tiktok/
- TikTok, Storytelling Formats to Drive Performance (SMB one-pager): https://ads.tiktok.com/business/library/Storytelling_Formats_One_Pager_SMB.pdf
- TikTok Creative Codes: https://www.tiktok.com/business/en/creative-codes
- Billo, CTA examples (six months of creator ads): https://billo.app/creative-insider/inspiration-ideas/cta-examples/
- Runneth (ex Motion blog), best DTC Meta ad hooks 2025: https://runneth.com/blog/best-dtc-meta-ad-hooks-2025
- Motion, how to write UGC ad scripts: https://motionapp.com/blog/how-to-write-ugc-ad-scripts
- Motion talk, the 30 ad formats every top brand is stealing (2025): https://motionapp.com/library/talk/the-30-ad-formats-every-top-brand-is-stealing-in-2025/
- MHI Growth Engine, DTC ad script templates (timings): https://mhigrowthengine.com/blog/ad-script-templates-dtc-brands/
- Sovran, direct response video ad endings: https://sovran.ai/blog/direct-response-video-ad-endings
- Captions, hook writing (open loops): https://captions.ai/help/guides/marketing/hook-writing
- imagine.art, best hooks for video ads 2026: https://www.imagine.art/blogs/best-hooks-for-video-ads-2026
- Story spine origin (Kenn Adams) and Pixar's rule 4: https://www.tckpublishing.com/story-spine/ , https://nofilmschool.com/pixar-story-structure
- Kimp, Pixar story spine in marketing video: https://www.kimp.io/pixar-marketing/
- Thinkbox, 10 lessons from John Lewis: https://www.thinkbox.tv/case-studies/brand-films/10-lessons-for-marketers-from-john-lewis-ongoing-success
- LBB, the power of emotional advertising (IPA / Binet & Field): https://lbbonline.com/news/beyond-christmas-cheer-the-power-of-emotional-advertising
- Google ABCDs of effective video ads (brand early): https://support.google.com/google-ads/answer/14783551

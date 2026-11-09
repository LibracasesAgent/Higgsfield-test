# Call with Julian (media buyer), 2026-11-05: what he said and what the pipeline does about it

Read with `docs/reviews/2026-10-06.md` (the Oct 6 - Nov 4 Ads Manager export, AUD).

| Julian said | Where it lives now |
|---|---|
| Hook rate 40-45-50% is great; hold rate (ThruPlays / impressions) 10-15% is good; ROAS 2.1+ (2.5 to scale); cost per result ~30 max; CPM is not a creative metric | `rulebook.json kpi`, `weekly_review.py` (hold = ThruPlays / impressions) |
| He killed the ABO ad sets that overspent, keeps the ones hitting KPIs and now tests in CBO | `rulebook.json process` |
| Statics carry the results ("the main performance are statics"); Google Ads needs statics too | `winning_patterns.statics_lead` |
| "Pick your colour" catalog static does really well; make it for the Vintage bag (4 colours) | `winning_patterns.colour_catalog`, `statics.keep_winners` (warned when a batch of 6+ has no colours static); data: S09_pick_your_colour ROAS 2.93, 76 purchases |
| B028 P02 (the presenter, Vintage): good metrics, weak hook (32%): test new hooks | next batch: new hooks for it (CLAUDE.md section 4 "another hook for P02"; the presenter takes cost ~2.5 credits a second) |
| "One hand holds the coffee, but the clip of the coffee comes later"; the crossbody line showed another clip; the snap line must show the snap closing | the footage blocker (RULEBOOK section 5) + presenter cut-ins on the words (`make_batch.shows_thing`) |
| Presenter: don't open with Black Friday (UGC must be less aggressive); keep one heading, not label + caption; cut the useless pause; a cut looked unnatural | `ideas.check` refuses a sale hook in a presenter project; no hook label on presenter videos; `presenter.py gate` pause check |
| Captions sat in the middle of the screen in one video; he wants them lower | not changed yet: look at the presenter videos' caption band on the next render (PLAYBOOK section 2 item 10: centre y 1380) |
| "Free US shipping": we target the US, UK and Australia; UK ships free too: say "free shipping" | templates changed; `banned.free_us_shipping` (hard) |
| Fewer statics, better quality: 12 very good beat 25 average | `rulebook.json batch.statics = 12` |
| Statics: headlines must be catchy, not a feature name; post-its must look real with aggressive text; no review card; the % once; no empty space, the bag big; us vs them must SHOW them (a grey, low-quality tote); text not over the strap; a window decal on the glass; show the bag, not the pouch; 3-Piece Set = 60% | `playbook_check.static_problems` (offer once, feature-name / list headlines), `statics.art` (printed in every packet), story review card optional, `brand_statics.them_half` + the versus scene composition |
| Anti-theft in crowds / metro / travel / tourist spots is a good angle for Hobo 2.0 and Hobo Bag, videos too; gifting for Christmas / Black Friday | `winning_patterns.crowd_travel_antitheft`, `winning_patterns.gifting` |
| A visual review before launch; a weekly call at the same time (15:00 Italy); he gives feedback on the ads that get spend | `rulebook.json process`; RULEBOOK section 9 |
| He shared a headline swipe file (Halbert's 349 headlines) | `docs/research/2026-11-halbert-headlines.md`, `rulebook.json hooks.formulas` |

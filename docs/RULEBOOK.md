# The Libra Cases ad rulebook

**Read this before writing any hook, script, static or ad copy.** It is the short, ranked version of everything the account's money,
the client and the media buyer have taught us (B001-B038, the creator winners, Halbert's *349 Great Headlines*). The machine half is
`pipeline/data/rulebook.json`; `pipeline/playbook_check.py` enforces it inside `ideas.py check`, `ad_copy.py` and `make_batch.py check`.
`docs/PLAYBOOK.md` keeps the history and the how-it-was-built detail; when the two disagree, this file and the JSON win.

Read order every batch: `CLAUDE.md` (the process) → this file (the craft) → `$OUT/strategy_packet.md` (the product's facts, its
footage, its past batches, last weeks' Meta numbers, and this rulebook again as data).

---

## 1. What we are trying to hit

| Metric (Meta) | Good | Floor | Why |
|---|---|---|---|
| **Hook rate** = 3-s video plays / impressions | **40-45%** | 25% | owner 2026-11-05: 40-45% is a really good number; Meta's baseline is 25-30% |
| Hold rate = ThruPlays / 3-s plays | 30% | 15% | does the body keep the people the hook won |
| CTR (link) | 5% | 2% | creator winners run 4.7-10.5% |
| ROAS | 2.4 | 1.8 | account average 2.39; our best AI ad set 2.97 (B017 P04 versus) |
| CPA | < $30 | $40 | creator winners $22-31, our AI ads $39.63 |

The hook rate is decided in the first three seconds by three things together: **the spoken hook, the first picture, the on-screen
label.** All three must say the same concrete thing.

## 2. The non-negotiables (hard: the check stops the batch)

1. **Only true claims.** Every property word must be in the product's facts (packet section 1). The claim words that need a fact
   (RFID, lockable, cut-resistant, lightweight, "fits a laptop", vegan, genuine leather, handmade, lifetime, a 2-year warranty, free
   returns) are refused when the product's facts don't say them. "Waterproof" is never true (water-resistant).
2. **No invented proof.** No "everyone is talking about it", "thousands of women", "best-selling", "#1"; no named person's story in
   the brand voice ("Sarah carried hers through Rome"); verbatim reviews only, and only on statics.
3. **No invented urgency.** No "selling out", "only 3 left", "while stocks last", "hurry", "before it's gone". The dated campaign words
   ("last chance" from 20 Nov, "ends tonight" on 30 Nov) follow `campaign.json`.
4. **'You' form.** The narrator and the presenter talk to the viewer; never "I bought / I love / my bag".
5. **Meta's personal-attributes rule.** Never assert who the viewer is: no age ("women your age", "over 50"), no crime that happened
   to them ("if you've been pickpocketed"), no condition. Never health, drugs, politics, religion, blood (compliance.py).
6. **No price figures** in hooks, statics, headlines: the % only (prices changed twice in October and six statics went stale).
7. **The footage shows what the words say** (section 5). Never a stand-in.
8. **Counts are delivered.** A hook that says "three reasons" has three numbered chapters.

## 3. Hooks: the first three seconds

**Shape:** 4-14 words, ideally 12 or fewer (about 3 s spoken). Names something the picture can show (keys, the zip, the back pocket, a
packed train, a crowd, coffee in one hand) or a number. Opens on a different picture of the bag *doing something* than the other three
hooks (a hand at the zip, the bag worn), never on the bag just sitting there. Never the first four words of a hook from the product's
last 8 batches (Meta groups ads with one look and story as one ad: B030-B034 opened 14 hooks with "Black Friday prices are live now").

**Write every hook on one of these formulas** (three or more different ones per project; the check warns when a hook follows none, and
refuses it when it also names nothing to see):

| Formula | Halbert's original | Our bag version |
|---|---|---|
| How to ... | "How To Make A Fortune Today Starting From Scratch" | "How to carry your cards through a crowd without checking your bag." |
| A question only the target says yes to | "Are You Ever Tongue-Tied At A Party?" | "Still digging for your keys at the front door?" |
| A number of specific things | "7 Ways To Collect Your Unpaid Bills" | "Three things this bag does that yours doesn't." (three numbered chapters) |
| The costly mistake | "The 5 Most Costly Mistakes In Business" | "The mistake that leaves your phone at the bottom of your bag." |
| A warning / before you buy | "Using A Lawyer May Be Dangerous To Your Wealth" + winner 158-H2 | "Before you buy another handbag, look at its back." |
| Contrast | "Don't Try This With Any Other Copier" + our winner B017 | "Most bags hang open in a crowd. Watch this one." |
| Watch / look (a demo command) | "Throw Away Your Oars!" | "Watch what one pull of this zip does." |
| A specific moment | "Suppose This Happened On Your Wedding Day!" | "Packed train, both hands on the rail. Where's your phone?" |
| News: at last / finally / new | "At Last ..." | "At last, a soft bag that zips all the way shut." |
| The truth about / what nobody tells you | "The Truth About Getting Rich" | "The truth about big bags: they swallow your phone." |
| Imagine / what if | "Imagine Working Until 4 A.M. - And Loving It" | "What if your keys had their own place in your bag?" |
| If you can X, you can Y | "If You Can Lick A Stamp - You Can Lick Your Weight Problem" | "If you can snap a clasp, you can close this bag one-handed." |
| Who else / for the woman who | "For The Woman Who Is Older Than She Looks" | "For the woman who changes bags before every plan." |
| The hidden one (literal features only) | "Profits That Lie Hidden In Your Farm" | "The pocket nobody behind you can reach." |
| The offer as news (one hook a project at most) | "Take Any 3 Of These ... For Only $8.95" | "Three bags for the price of one this Black Friday." |

**Attention words that fit the brand:** at last, finally, new, now, watch, imagine, the truth about, buyer's guide, test drive, show
me, unlock, timely, just in time, savvy, insider, spotlight, revisited, word of mouth, measure up, stash, heritage, upscale, affordable.
**What we never take from Halbert:** his health, weight, income, "miracle", "secret to", "guaranteed", "amazing" headlines: they break
Meta's rules and our compliance, and read as hype. We borrow his *shapes*, never his claims.

**Banned openers and filler:** "Meet the / Introducing / Say hello to / Check out ...", a line that only names the bag ("The everyday
hobo."), "game changer", "must-have", "obsessed", "you won't believe", "you need this", "elevate your", "look no further". Soft
(warned): amazing, incredible, stunning, perfect, ultimate.

The hook's `type` must fit its words: a `question` ends with "?", a `price` hook says the offer.

## 4. Scripts: one story, shown not told

What the money says (docs/research/2026-11-all-time-best-ad.md):
- **Contrast beats lists.** "An ordinary bag vs this one" is our only AI winner (ROAS 2.97). The engine's "n things" lists lose (1.69-2.21).
- **One idea, at most three features**, a different lead feature per project, a structure from `data/story_structures.json` (or a new one), never the product's last batch's.
- **Open a loop in sentence one** (a warning, a question, a doubt said out loud), close it in the body.
- **Say the doubt out loud**, then answer it ("a secure bag doesn't have to look tactical").
- **A person beats a faceless voiceover**: the bag worn in two chapters, the presenter in about half the projects (section 6).
- 55-80 s, 185-215 wpm, the price only in the last chapter, ending "Tap the link below."
- Every chapter names the picture it needs (`show` tags) **from the tags the packet says the footage has** (4+ good moments).

## 5. The footage must show what the words say (the blocker)

Julian 2026-10-21 ("the snap close showed the strap"), owner 2026-11-05 ("it should not happen"). Three gates, all automatic:

1. **Plan** (`ideas.check`): a chapter whose words name a feature (the clasp, a zip, the back pocket, the inside, the strap, a lock, the
   pouch, the tie) that the product's labelled footage has fewer than 4 good moments of is **refused**. Rewrite the line around what the
   footage shows (packet section 2). Shot picking (`ugc_board.choose`) only takes labelled moments that show what the phrase names.
2. **Render** (`storyboard.plan_block`): the real voice groups the words differently from the plan's estimate, so before each shot is
   cut the words under it are checked against the picture; a pick that shows none of them swaps with a later pick or a spare that does.
3. **After render** (`make_batch.footage_match`): every shot of the finished video is checked against the caption words over it
   (`_<name>_longform.json`). A shot still showing none of what is said is **`shot mismatch`: hard, the version is not uploaded**;
   `qa/<id>_footage.json` lists each shot. A shot from an unlabelled source (a photo, an AI clip, a new product's clip) under such words
   is listed as `footage unverified` (look at it on the contact sheet). Fix: the shot in the spec, `render --only` that version.

What counts as "shows it": the labelled frame's tags (`clip_index.json` moments within 2 s of the shot) contain one of the line's wants,
or a near equivalent (`shotmatch.ALSO`: the compartments ~ the inner pocket; a lock ~ the zip; the strap ~ the bag worn). Lines about a
mood, a place or the offer are not judged.

## 6. The presenter: more of it

Owner 2026-11-05: "the presenter UGC videos are good, we need to make more of that." Default (`rulebook.json presenter.per_batch`):
2 projects → 1 presenter, 3-4 → 2, 5 → 3 (about 225 credits each; the 1000-credit presenter cap holds 3-4). The request's own number
(`"presenter_count"` in the sheet) or "no presenter" (`"no_presenter"`) wins. She is a host, never a customer: 'you' form, no
invented use or result; soft natural phone-photo skin (never "pores / fine lines / unretouched"). Give her the story beats that need a
face (`cam: full`), and cut footage in where a line describes something the hands do.

## 7. Statics

Every static shows the offer (the % as a hero element) **and** tells a story: one 3-8 word line that says why to buy, over the picture
of that moment. About a third `story` (hook + moment + one promise + a verbatim review with stars + the % sticker + gift + brand mark),
about half AI `ad` formats (each once a batch, at least one new format), the rest real. No faces, no price figures, no fake buttons.

## 8. Ad copy

Primary text 1: two lines, ≤125 characters, a hook that obeys section 3 + the product with its offer. Headlines ≤40, description ≤30, no
em dashes, ≤2 emojis, no prices, no urgency the campaign does not confirm. The template lines that break a rule are skipped by
`ad_copy.py` itself; a hand edit is judged by `make_batch.py check --out $OUT` (compliance + this rulebook).

## 9. The weekly review loop (how this rulebook changes)

After each weekly performance meeting (20 minutes, `pipeline/weekly_review.py`):

```
python3 pipeline/weekly_review.py ingest <Ads Manager export, Ads level>.csv --week <Monday>
python3 pipeline/weekly_review.py report --week <Monday>          # docs/reviews/<Monday>.md: every ad vs the targets, best/worst hooks,
                                                                   # hook rate by formula / structure / batch / H1-H4, suggested changes
python3 pipeline/weekly_review.py add win  "<what worked>"  --evidence "<ads, numbers>"
python3 pipeline/weekly_review.py add lose "<what lost>"    --evidence "<ads, numbers>"
python3 pipeline/weekly_review.py add ban  "<phrase>" --why "<who, why>" [--level soft] [--where hook|statics|copy]
python3 pipeline/weekly_review.py set kpi.hook_rate.good 0.42 --why "<meeting>"
python3 pipeline/weekly_review.py set presenter.per_batch.5 4 --why "<meeting>"
```

Every change gets a dated line in `rulebook.json` → `changelog`; the next strategy packet prints the last weeks' best and worst hooks and
the newest changes, and the checker enforces new bans at once. Commit `pipeline/data/rulebook.json`, `pipeline/data/performance.json`
and `docs/reviews/`. Anyone can also edit `rulebook.json` by hand (every rule has `level` hard/soft and `why`); `python3
pipeline/tests/test_playbook.py` checks it still reads.

## 10. Changelog

- 2026-11-05: rulebook created (owner): Halbert hook formulas, banned phrases and claim words from B001-B038, hook rate target 40-45%,
  the three-gate footage blocker, presenter in about half the projects, the weekly review loop.

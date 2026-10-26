# Brand Ad Agent: the context layer (how to run this system for any brand)

What we learned building the Libra Cases pipeline (22 batches, 457 ads in Drive, Sept-Oct 2026), written so the same system can be set up
for another brand and run by an AI agent (Claude Code, Codex, a Slack bot) from one-line requests. It covers: how the agent's
context is built, the steps to onboard a brand, how to write the instructions, the learnings and the guardrails, and what
in this repo is still Libra-specific.

---

## 0. The ten ideas that made it work

1. **Facts are data, not prose.** Prices, offers, features, colours, reviews and dated sale campaigns live in JSON files the code
   reads. The agent never types an offer from memory, so an offer that changes (Libra's Black Friday gifts were removed three days
   after launch) changes in one file.
2. **A rule that matters is a check, not a sentence.** Every rule the agent broke once became code that refuses: compliance
   exits 2, the sheet check prints `PROBLEM: S06: ...`, the gate fails a picture with a face. Prose rules drift; checks don't.
3. **The agent is the strategist, the code is the factory.** The agent writes ideas, hooks, scripts and static concepts
   (`ideas.json`). Lengths, sizes, names, credit caps, layouts and uploads belong to the code. The boundary is written down.
4. **Each run gets a compiled packet.** Before writing anything the agent reads one generated file (`ideas.py packet`): the
   product's true facts, what the footage can show, every earlier batch's hooks, lines, scenes and formats, the format library and
   the rules. It never browses Drive or old chats to "find out what was done".
5. **Memory is written down with a date and a source.** Every client decision is in the playbook as a quote with a date
   ("owner 2026-10-21: ..."), newest last. The agent can resolve conflicts (newer wins) and knows why a rule exists.
6. **Novelty is enforced.** A log of what every batch showed (scenes, photos, captions, hooks, formats) makes the next batch
   different. Meta groups look-alike creatives and gives them one share of delivery, so ten similar ads count as one.
7. **Real material first, AI fills the gaps, AI is gated.** Real photos and footage carry the product truth (zips, pockets,
   hands). AI makes what was never shot: new scenes and whole designed statics, always from the real product photo, always
   checked against it, always looked at.
8. **Unattended runs decide, they don't ask.** "Nobody is watching: never ask follow-up questions, decide sensibly, reply
   once at the end." A request that conflicts with a rule gets the standard version plus one line saying what was done instead.
9. **Calibrate with the client, then automate.** Show a test sheet of 8-10 different formats, record which ones they like and
   dislike, and start the library from those.
10. **Close the loop.** Every ad has a stable name, a row in the tracker sheet and a Drive file. Results come back weekly and
    become learnings, which feed the next packet.

---

## 1. The architecture: six layers of context

```
 request ("3 statics and 4 videos, Black Friday")
    │
    ▼
 L1 CONSTITUTION   AGENT.md (CLAUDE.md here): start-here line, router, hard rules, reply format         read every run
 L2 BRAND PACK     brands/<brand>/: brand.json, products/*.json, claims, reviews, campaigns, voice     read by code
 L3 MEMORY         playbook.md (learnings, client feedback, bug table), novelty log, ledger, tracker   read via the packet
 L4 LIBRARIES      static formats, hook types, scene library, footage index (moment tags), research    read via the packet
 L5 TOOLS+CHECKS   plan / render / upload; compliance, sheet check, AI gates, scorecard                 run, they refuse
 L6 RUN PACKET     strategy_packet.md: compiled from L2-L4 for THIS request                             read every run
    │
    ▼
 the agent writes ideas.json  →  check  →  plan  →  generate (voice, AI)  →  gate + look  →  render  →  QA  →  upload  →  reply
```

**Precedence when two sources disagree:** hard rules (L1) > the brand pack's facts (L2) > the newest dated client decision (L3)
> older learnings > defaults in code. Write this order into L1.

**What the agent reads every run:** L1 and L6, nothing else by default. Everything else reaches it through the packet or through
a check's message. This keeps the context small and the same every run, which is what makes unattended runs predictable.

---

## 2. What goes where

| Knowledge | Layer | Format | Updated by | Libra example |
|---|---|---|---|---|
| How to handle a request, what never to do | L1 | Markdown, <= ~400 lines | engineer, after an incident | `CLAUDE.md` |
| Product facts, features + on-screen tags, colours, photos | L2 | JSON per product | intake script + check | `pipeline/data/products/*.json`, `site/*_facts.json` |
| Offers and sale campaigns with dates | L2 | JSON with `from` / `until` | when the client changes an offer | `pipeline/data/campaign.json` |
| Approved and banned claims | L2 | JSON (phrases + regex + why) | compliance owner | `campaign.json` `approved_phrases` / `banned`, `compliance.py` |
| Verbatim reviews (with consent) | L2 | JSON | client | reviews file used by `quotes` / `stars` |
| Voice, music, fonts, colours, wordmark | L2 | JSON + asset files | once per brand | `data/voice.json`, `assets/music/`, `brand_statics.py` constants |
| Client feedback and decisions | L3 | Markdown, dated quotes, newest last | after every feedback message | `docs/PLAYBOOK.md` §2, §4f-4j |
| Bugs that happened and their fix | L3 | Table: check / bug / fix | after every bug | `PLAYBOOK.md` §6 |
| What each batch showed | L3 | JSON log per product | `upload` itself | `data/novelty_log.json` |
| Batch numbers, ad names | L3 | JSON ledger + Drive lock | `plan` / `upload` | `data/batch_ledger.json`, `batch_lock.py` |
| Results per ad | L3 | Sheet with typed columns | media buyer + sync | the ad tracker sheet (`tracker.py`) |
| Static formats (liked / new) | L4 | JSON library | after calibration, after results | `data/static_formats.json` |
| What the footage can show | L4 | Index with per-frame tags | indexing + labelling agents | `data/clip_index.json` (`moments`) |
| AI scene library | L4 | JSON | engineer / strategist | `data/ai_scenes.json` |
| Market and theme research | L4 | Markdown with source tags | the agent, when a theme is new | `docs/research/*.md` |
| What the client can type | — | Markdown for humans | engineer | `docs/CLIENT_GUIDE.md` |

---

## 3. Onboarding a new brand, step by step

Each step has a deliverable and a "done when". Steps 1-5 take about a week with the client's help; 6-7 take one or two days.

### Step 1. Collect the brand's data

Ask the client for, and store in `brands/<brand>/raw/` (never edit the originals):
- **Catalogue:** every product, its URL, price, compare-at price, colours, the features in their own words, what is in the box.
- **Offers:** current discount, gifts, bundles, shipping, warranty, returns, and the dates each one runs. Ask: "what will
  change in the next 6 weeks?" (sales, gifts, price tests).
- **Claims:** what they may say and what they may not (their category's regulator, past ad rejections, the media buyer's rules).
- **Reviews:** verbatim, with the reviewer's first name, and confirmation they may be used in ads.
- **Assets:** packshots (white background, every colour, front and back), lifestyle photos, raw footage (the more the better:
  Libra had ~1,300 clips), logo, fonts, brand colours, licensed music.
- **Performance:** an Ads Manager export of the last 90 days (ad name, spend, purchases, ROAS, CTR, hook rate) and links to the
  top 5 ads. The winners decide the starting formats.
- **People:** who approves (owner), who launches (media buyer), how they want to request ads (Slack, DM), where files go (Drive).

**Done when:** a checklist of the above is filled in, with gaps named ("no back-view packshot", "no reviews yet").

### Step 2. Build the brand pack (L2)

Turn the raw data into files the code reads (templates in the appendix):
- `brand.json`: name, wordmark text, colours, fonts, CTA words, the product noun ("handbag", "serum", "phone case"), the masthead
  word for magazine-style ads, the URL, the locale and currency.
- `products/<slug>.json`: one per product: name, aliases, price, compare-at, offer, gift, colours with their packshot files,
  features as `[sentence, ON-SCREEN TAG]`, photos with kind (packshot / worn / detail) and a face flag, `status: ready`.
- `claims.json`: approved phrases (with the source), banned regex (with the reason), category rules (health, finance, ...).
- `campaigns.json`: each sale with `from`, `until`, themes it applies to, its facts, its banned phrases, its end-card words.
- `reviews.json`, `voice.json` (voice id, speed), `music/`.

**Done when:** a `check` command passes on every product file (price and % agree, every feature has a tag, every colour has a
packshot, no photo with a face is marked for statics).

### Step 3. Index the assets

- **Photos:** face detection (any face: never in a static), sharpness, background (clean packshot vs lifestyle), colour match.
- **Footage:** header, a few frames per clip, face / sharpness / darkness checks, `usable: yes/no` with the reason, then
  **moment tags** per frame (zip, pocket, worn, packing, strap ...: the brand's own vocabulary), so a script line about the
  pocket gets a shot of the pocket. Labelling agents can tag contact sheets in parallel.

**Done when:** the index has counts per tag, and the packet can say "pocket: 197 moments, inside: 12 (thin)".

### Step 4. The compliance profile

Write the brand's rules as checks before the first ad, not after the first rejection:
- Platform rules (Meta): no personal attributes ("Are you overweight?"), no before/after, no health claims for non-health
  products, no fake interface (play buttons, notifications, sliders), no sensational content, no misleading urgency.
- Category rules (supplements, skincare, finance ... each has its own).
- Truth rules: every number and offer must be backed by the brand pack; no invented customer experience, no first person for
  a brand voice; reviews verbatim only.
- Sale rules: dated; say only what the campaign file says; when the sale is final sale, no returns promise.

**Done when:** a test file of 20 bad lines ("free gifts" after gifts ended, "60% off" on a 50% product, "theft-proof", "easy
returns" during final sale) all fail, and 20 good lines pass.

### Step 5. Performance baseline and "what converts"

From the export: which formats, hooks, lengths, products and angles made money. Write 5-8 bullets into the brand's packet
section "What converts" (Libra: creator human stories win, CTR 5-10%; faceless voiceover b-roll mostly loses; open with a reason
to buy, the sale last; the 3-Piece Set raises the basket). Mark each bullet with its source.

### Step 6. The calibration round (statics)

Generate 8-10 statics in clearly different formats (magazine cover, feature diagram, bold poster, street photo from behind, flat
lay, gift moment, sticky note, phone notes ...), about 1 credit each, and ask the client one question: "which do you like?". Record
the answer verbatim in the playbook and as stars in the format library. Libra on 2026-10-26: liked 2, 3, 4, 6, 7, 8; asked for 6 and
8 "more realistic"; did not like the sticky note or the phone notes. One round like this replaced weeks of guessing.

### Step 7. The first supervised batch

Run a full batch with a human watching every step. Every comment goes into the playbook (dated quote, decision, what was built).
Every bug goes into the bug table with the check that now prevents it.

### Step 8. Unattended runs

Turn on the one-line requests (Slack / DM). The constitution's router maps words to flags; the reply format is fixed; every run
uploads to Drive, adds rows to the tracker and commits its specs and logs.

### Step 9. The weekly loop

Results come into the tracker (spend, purchases, ROAS per ad name). Once a week: winners get new hook versions (keep the proven
body, test 4 openings), losers' formats lose weight in the library, and 3-5 learnings go into the playbook.

### Step 10. Keep it true over time

Offers end, prices change, products get a second strap. When a fact changes: change the brand pack, add a dated decision, and
list the delivered ads that are now false (Libra: 4 delivered batches carried "free gifts" after the gifts were removed) so the media buyer
can pause them.

---

## 4. How to write the instructions (the constitution, L1)

What worked, with examples from `CLAUDE.md`:

1. **One "start here" line at the top.** "START HERE, every time: section 0 setup, then the strategist step, then `plan --ideas`,
   then section 5." Agents follow the first instruction they read most reliably.
2. **A router table.** "The message says ... → pipeline ... → section". Then a second table: "Request says ... → flags". Tables
   beat paragraphs for mapping words to actions.
3. **Defaults with numbers.** "No numbers = a batch: 20 statics + 5 projects × 4 hooks." "Videos run 55-80 s." "A batch is capped at
   100 credits." Vague defaults ("a few", "short") get interpreted differently every run.
4. **Define the vocabulary once.** "One project = one video body in 4 versions H1-H4 that differ only in the hook." "B045 is the batch
   number." Every later sentence relies on these words meaning one thing.
5. **Hard rules are numbered, short, and say why.** "Never reshape the videos to fit a request ... a message like 'hook-first' means
   other hooks, at the normal length." Add the incident: "(the 2026-10-14 'hook test' run was a mistake)". A rule with its story
   is followed; a bare rule gets argued around.
6. **Say what to do when a request conflicts with a rule.** "Make the standard version and say in the reply what you did instead
   and why." Otherwise the agent either refuses or breaks the rule.
7. **Draw the creative boundary.** "You write ideas.json: ideas, hooks, scripts, static concepts. Video length, format, static sizes,
   names and the credit cap stay plan's: don't invent those." The agent's freedom is where you want variety; everywhere else, code.
8. **Name the allowed tools and models.** "The only Higgsfield calls: ..." plus "Never: other generators, presets, upscalers ...".
   An open toolbox gets used (Libra's first Slack run spent ~160 credits on random AI clips and made off-brand ads).
9. **Write model-prompting lessons as rules.** "Never ask a model for 'pores / fine lines / unretouched'" (it gave etched wrinkles and
   orange skin). "Keep the product closed: there is no photo of its inside." "The words big enough to read on a phone."
10. **Fix the reply format.** A short template per pipeline: folder link, batch id, one line per ad, warnings, QA flags, credits
    before → after. Then every reply can be skimmed the same way.
11. **Keep L1 short; point to the rest.** Details go into the playbook and the code's own help text. L1 says when to read them.
12. **Date and attribute every client rule.** "(owner 2026-10-21: 'avatars accepted if there is an actual story')". When the
    client changes their mind, the newer date wins and the old rule is marked superseded, not deleted.

**Skeleton of an AGENT.md for a new brand:**

```
# <Brand> ad pipeline: how to handle requests
<what you do, for whom, where output goes> Nobody is watching: decide, reply once at the end.
START HERE: setup → strategist step → plan --ideas → run.

## HARD RULES (numbered; each with its reason and the incident)
1. Real material first; AI only through <gen tool>, only what plan lists, gated and looked at.
2. Allowed tools and models; credit cap per batch; balance before and after.
3. Only true claims (sources: the brand pack); platform + category rules; compliance runs on everything.
4. Upload with <upload command> only; never only post files in chat.
5. Never publish; never delete or move client files.
6. Never reshape outputs to fit a request (lengths / formats are the code's).

## Vocabulary (batch, project, version, static, format, packet)
## Which pipeline? (router table)
## Request → flags (table)
## Setup (commands)
## The strategist step (packet → ideas.json → check)
## The run (plan → generate → gate → render → QA → upload → reply → commit)
## Reply format
## References (playbook, naming, client guide, brand pack readme)
```

---

## 5. How to write the learnings (the memory, L3)

**One entry = one decision.** Use this shape (it is how `PLAYBOOK.md` §4f-4j are written):

```
### 4j. AI-designed statics (owner 2026-10-26)
Quote:   "i like 2, 3, 4, 6 (make it realistic), 7, 8 (make more realistic). make them unique each time ..."
Context: the test sheet of 8 AI ads; 1 and 5 not liked.
Decision: layout `ad`, two thirds of the statics; new formats every batch; realistic photo look.
Built:   data/static_formats.json, ideas.check (uniqueness, Meta rules), ai_gen.build_ad_prompt + text gate, l_ad.
Enforced by: tests/test_ad_formats.py; `ideas.py check` refuses repeats and fake interface.
Supersedes: "about half concept scenes" (2026-10-21).
```

Rules for the memory:
- **Newest last, never rewritten.** Mark old decisions "superseded" or "HISTORICAL, NOT ALLOWED" (Libra's free-form AI shots of
  October 2 stayed in the playbook so nobody repeats them).
- **Quote the client.** Their words resolve ambiguity later ("make it realistic" meant a phone-photo look, not more detail).
- **The bug table:** `check | bug we had | fix in place`. Libra's has 50+ rows ("Videos not shortened to fit a request", "No negated
  gift", "Part of a head in a static" ...). Each row was a real failure once, and each fix is code.
- **Promote a repeated learning into a check.** The second time the same feedback comes, it stops being a sentence.
- **Keep the numbers.** Costs per asset, render times, which format had spend and ROAS. The agent plans with them.

---

## 6. Guardrails: the catalogue and who enforces each

Four enforcement levels, strongest first: **code refuses** (exit 2 / gate fail) > **code flags** (warning in the reply) > **the
agent looks** (a contact sheet it must read) > **a human approves** (first batches, new formats).

| Area | Guardrail | Level | Libra implementation |
|---|---|---|---|
| Truth | Every offer, %, price, gift comes from the brand pack | refuses | `compliance.py` evidence corpus; `make_batch` reads offers per product |
| Truth | Dated campaigns: say only what is live today; banned phrases | refuses | `campaign.json` `from` / `until` / `banned`; `campaign.active()` |
| Truth | No returns promise during a final sale | refuses | `compliance.FINAL_SALE` |
| Truth | No first person, no invented customer experience, reviews verbatim | refuses | `ugc_script.FIRST`, `ideas.check`, the quotes layouts |
| Platform | No health / medical / politics / religion / violence | refuses | `compliance.py`, also on the words a winner's RAW plays |
| Platform | No fake interface, no real publication or brand names, no price figures in AI pictures | refuses | `ideas.FAKE_UI`, `MAGAZINES`, the price rule |
| Platform | Captions inside the safe zones, nothing over the end card | code | caption zones in `longform.py` |
| People | No face in a static; people only from behind or cropped | refuses | DNN face check at plan, gate and render; `ai_gen` people rule |
| People | One original presenter, never a real person, never a customer | rule + look | `presenter.py`, `data/presenters.json` |
| Product | AI starts from the real packshot and is checked against it | refuses + look | `ai_gen.gate_still` (colour, features, sharpness) + contact sheet |
| Product | The product closed; labels only for what the angle shows | refuses | `ideas.INSIDE`; the diagram's bag rule |
| Product | One look of the product per ad | refuses | `designs.json` guard (the Hobo 2.0 had two looks) |
| Words | The AI's words read back; a wrong % fails | refuses + look | `ai_gen.text_check` (tesseract) |
| Budget | Credits per batch capped; presenter part capped; balance before and after | refuses | `plan` (`--budget`, `--ai-cap`, `--presenter-cap`) |
| Novelty | No hook, line, scene or format from recent batches; new formats each batch | refuses | `novelty_log.json`, `ideas.check` |
| Quality | Length floor, scorecard targets (wpm, pauses, shot length, loudness) | flags / refuses | `render` `too short`; `scorecard.py` |
| Quality | Every static and video looked at before upload | look | `qa/statics.jpg`, `qa/P*.jpg` |
| Ops | Never publish, never delete or move client files | rule | CLAUDE.md rules 4-5 |
| Ops | Two runs never share a batch number | refuses | `batch_lock.py` (Drive claim files) |
| Ops | Each run's specs and logs reach the main branch | code | `merge_batch.py` + the GitHub Action |

**How to write a check's message:** say what, where, and how to fix, in one line. The message is part of the instructions,
because the agent reads it and acts:
`PROBLEM: S06: the line 'The Hobo Bag' was on a static of an earlier batch: new words`
`PROBLEM: S01: 'play button': no fake interface in an ad (buttons, notifications, sliders: Meta rejects them)`

---

## 7. Awesome statics, specifically

**The mix (Libra, 2026-10-26):** about two thirds AI-designed ads, one third real (studio packshot, a real photo frame, one
verbatim review, the struck-through price).

**The format library** (`data/static_formats.json`): each format has an id, a short tag for the file name, a name, the art
direction (what kind of picture, layout, type), the people rule, the word limit, a hint for the words, the type style, product
rules, an example and a star if the client liked it. Start a new brand with Libra's liked six as priors, then calibrate (Step 6).

**The prompt anatomy** (built by code, `ai_gen.build_ad_prompt`; the agent writes only the picture and the words):
1. the format's art direction,
2. the strategist's picture (setting, props, light),
3. keep the real product: "the exact <noun> from the reference image, unchanged: same colour, shape, handles, hardware ...",
4. the product closed, nothing inside shown,
5. the exact words, each in quotes, "each exactly once", "big, easy to read on a small phone screen", "no other text, no logos",
6. the people rule (nobody / only from behind / hands only),
7. the realism line ("looks like a real photograph: true-to-life light, real textures, small imperfections, nothing glossy"),
8. the composition (4:5, the product large).

**What we learned about AI statics** (gpt_image_2_5, medium, 2k, 4:5, ~1 credit each):
- It sets short text correctly when the exact words are quoted (every word right in all 17 test pictures); OCR reads plain type well and
  stylised or huge type badly, so OCR is a hard fail only for a wrong % and a "look" otherwise.
- Without the size rule, captions and labels come out too small to read in the feed.
- It invents a product's inside when the bag is shown open: keep it closed unless there is a real photo of the inside.
- A label like "hidden back pocket" points at the wrong place unless the reference shows that side.
- "Candid phone photo, a friend walking behind her, real clothes with creases" reads as real; "studio, premium" reads as CGI.
- People from behind pass the face checks; ask for "her head turned forward" and "every other person far away, facing away".
- The packshot's extras appear too (Libra's pouch wallet shows in most stills): pick a reference without them if the ad must not.

**Uniqueness rules:** each format once a batch; none the product's previous batch used; at least one new format a batch (two
with 6+ ads); no line an earlier static carried. The packet lists the library, the formats used before and the rules.

---

## 8. Learnings from Libra that transfer to any brand

**Creative**
- Look-alike ads share one slice of delivery: different concepts (person, setting, opening, format, emotion), not variations.
- Human stories told to camera won the account (creator winners at 5-10% CTR); faceless voiceover over b-roll mostly lost.
- Open with a reason to buy, shown in the first 2 seconds; the sale is the close (in November every brand opens with "50% off").
- Statics: one big photo, very few words, the product large; the client's own taste beats general "best practice" (calibrate).
- Each picture must show what the line says (the pocket line shows the pocket): tag the footage.
- Reviews in videos read as objection handling before the CTA (media buyer): keep them in statics.
- "Hook test" means four new openings on the proven body, never shorter videos.

**AI generation**
- Always start from the real product photo; check the result against it; look at every picture before it ships.
- The first unattended run without guardrails spent ~160 credits and made off-brand ads: limit the tools and the models.
- Skin and faces: ask for "soft, even, natural phone-photo skin"; never "pores / fine lines / unretouched".
- AI hands and moving mechanics (zips) are unreliable: real footage for mechanics.

**Video craft** (the measured targets): 55-80 s, 185-215 words a minute, a new shot every ~2 s, longest pause <= 0.8 s, -14 LUFS,
captions at the bottom out of the faces and the product, one narrator voice, music under the voice, an end card in the safe zone.

**Operations**
- Offers change faster than ads: dated campaign files, and a list of delivered ads that became false.
- Stable names (`LC_<date>_<Product>_<Theme>_B045_S01_<layout>`), batch numbers claimed in Drive, a tracker row per ad from day one.
- Parallel runs collide (same number, same hooks) unless there is a lock and the logs merge back.
- Fresh containers lose state: everything worth keeping is committed (specs, logs, ledger) or in Drive.

**Cost**
- Voiceover ~4-5 credits a project; an AI static ~1; a 3 s AI clip 4.5-6; a talking presenter ~2.5 a second (~225 a project). In
  Libra's second month, presenter videos were 91% of the credits. Plan caps per batch; report balance before and after.

---

## 9. Making this repo multi-brand: what is Libra-specific today

The pipeline was built for one brand; about 30 of its Python files mention Libra or its bags. To run brand #2:

| Libra-specific today | Move to |
|---|---|
| Built-in bag names, aliases, footage folders (`INDEX_PRODUCT`), PLAYBOOK §1 facts used as evidence | `brands/<b>/products/*.json`, `brand.json` |
| "handbag" as the product noun; the LIBRA masthead; the wordmark | `brand.json` (`noun`, `masthead`, `wordmark`) |
| Brand colours, fonts, the red pill, the cream backdrop (`brand_statics.py` constants) | `brand.json` `style` |
| Drive folder ids, the tracker sheet id (`config.json`, `data/tracker.json`) | `brands/<b>/config.json` |
| `campaign.json`, `designs.json`, `voice.json`, `presenters.json`, music | `brands/<b>/` |
| Feature tag vocabulary and footage moment tags (zip, pocket, strap ...) | `brands/<b>/tags.json` |
| `novelty_log.json`, `batch_ledger.json`, naming prefix `LC_` | per brand (`brands/<b>/data/`, prefix in `brand.json`) |
| CLAUDE.md's Libra sections (built-in bags, Black Friday, Hobo 2.0) | `brands/<b>/BRAND.md`, included by the packet |

Suggested layout:

```
AGENT.md                      the constitution (brand-neutral) + "read brands/<b>/BRAND.md"
core/                         code: plan, render, upload, compliance, gates, ideas (sheet + packet)
core/data/static_formats.json the shared format library (brand stars live in the brand pack)
brands/<b>/BRAND.md           voice, the client's do / don't, dated decisions (this brand's playbook)
brands/<b>/brand.json         name, noun, masthead, colours, fonts, CTA, URL, naming prefix
brands/<b>/products/*.json    one per product
brands/<b>/claims.json        approved + banned + category rules
brands/<b>/campaigns.json     dated offers
brands/<b>/reviews.json
brands/<b>/config.json        Drive folders, tracker sheet, voice id
brands/<b>/data/              novelty log, ledger, footage index
brands/<b>/research/*.md
tests/brands/<b>/             the brand's fixtures: good and bad lines, a golden sheet
```

Every command takes `--brand <b>`; the packet includes `BRAND.md` and the brand's stars; compliance loads the brand's claims.

---

## 10. Evaluation: when is the agent ready to run alone?

- **Unit tests for every guardrail** (Libra: 13 suites, e.g. `test_campaign.py`, `test_ad_formats.py`): the bad lines fail, the good
  lines pass, the uniqueness rules refuse repeats, a wrong % fails the gate.
- **A golden sheet** per brand (a strategist sheet that passed), checked by the rules of its own date, so rule changes don't
  break old fixtures silently (Libra: the B014 sheet).
- **A dry run** (`plan --no-ledger`, batch B000) that plans, generates a few AI assets, renders and stops before upload.
- **Three supervised batches** with no human correction needed → unattended. Keep the first unattended week's replies reviewed.

---

## 11. A two-week rollout for brand #2

| Days | Work | Output |
|---|---|---|
| 1-2 | Step 1 data collection; refactor the brand-specific constants into `brands/libra/` (Libra keeps working) | data checklist; Libra on the new layout, all tests green |
| 3-4 | Step 2 brand pack + `check`; Step 4 compliance profile with 40 test lines | `brands/<b>/`, tests |
| 5-6 | Step 3 index photos and footage; moment tags | the index with counts |
| 7 | Step 5 performance baseline; "what converts" bullets | the brand's packet section |
| 8 | Step 6 calibration sheet (8-10 AI statics); the client picks | stars in the library, a dated playbook entry |
| 9-10 | Step 7 first supervised batch; every comment into the playbook | batch B001, learnings |
| 11-14 | Two more supervised batches; then one-line requests unattended | the router live in Slack |

---

## Appendix: templates

**brand.json**
```json
{"name": "Libra Cases", "noun": "handbag", "masthead": "LIBRA", "wordmark": "LIBRA CASES", "url": "https://libracases.com",
 "prefix": "LC", "currency": "USD", "locale": "en-US",
 "style": {"red": "#C81628", "cream": "#F6F1EA", "gold": "#B8893B", "serif": "Cormorant Garamond", "sans": "Inter", "bold": "Montserrat"},
 "cta": ["Shop now", "Get the deal"], "voice": "warm, direct, 'you' form, no hype words"}
```

**products/<slug>.json** (simplified: the real files also carry each feature's picture picks, the offer's evidence and the badge)
```json
{"name": "Hobo Bag", "aliases": ["hobo"], "status": "ready",
 "offer": {"pct": 50, "gift": "free matching pouch wallet"}, "facts": {"price": "52.50", "compare_at": "105.00"},
 "features": [["A hidden pocket on the back sits flat against you.", "HIDDEN BACK POCKET"],
              ["Two gold side zips for your keys and phone.", "GOLD SIDE ZIPS"]],
 "colours": {"Black": "hobo_bag_colour_galaxy_black.jpg", "Burgundy": "hobo_bag_colour_burgundy.jpg"},
 "photos": [{"file": "hobo_bag_00.jpg", "kind": "packshot", "faces": 0, "statics": true}]}
```

**campaigns.json** (one entry)
```json
{"id": "bf2026", "name": "Black Friday Sale 2026", "from": "2026-10-23", "until": "2026-11-30", "themes": ["black friday", "cyber monday"],
 "facts": ["50% off everything sitewide", "60% off only on bundles like the 3-Piece Set", "No free gifts (removed 2026-10-26)"],
 "approved_phrases": ["up to 60% off", "50% off everything"], "final_sale": true,
 "banned": [{"rx": "\\bfree gifts?\\b", "why": "gifts removed by the owner on 26 October"}],
 "end_title": "Black Friday Sale", "end_pill": "UP TO 60% OFF"}
```

**A format** (`static_formats.json`)
```json
{"id": "pov_behind", "tag": "pov", "name": "POV street photo from behind", "liked": 6, "people": "behind", "words": 12,
 "art": "A candid phone photo taken by a friend walking a few steps behind her: real street life, natural mixed light ...",
 "words_hint": "one caption that starts 'POV:'", "type": "a bold white sans-serif caption with a soft dark shadow, set large",
 "example": ["POV: your bag stays zipped in the crowd"]}
```

**A strategist static** (`ideas.json`)
```json
{"id": "S05", "project": "P01", "layout": "ad", "format": "film_still", "format_name": "Film still with subtitle", "people": "behind",
 "art": "A cinematic widescreen film still: black letterbox bars, a moody 35mm frame, real grain, one white subtitle line in the bar.",
 "idea": "The commute as a film scene, the subtitle is the feature", "words": ["Last train. Phone in the side zip."],
 "scene": {"colour": "Brown", "prompt": "Inside a quiet late-evening train carriage, a woman seen from behind by the doors ..."}}
```

**A learning entry** and **a check message**: section 5 and section 6 above.

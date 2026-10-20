# Making ads from Slack: quick guide

Send Claude one line in a Slack DM. It makes the ads from your real product photos and footage, adds one
voice, numbered captions, the offer and a soft music bed, writes the Meta copy (primary texts, headlines,
description), and saves it all in Google Drive. Nothing is ever published: you review the files and upload the
ones you like to Meta.

**Start every DM with `Higgsfield-test:`** (the project's repo, `LibracasesAgent/Higgsfield-test`): that is how
Claude knows which project to work in. Copy the lines below as they are and change the names or numbers. In the
`#libra-ads` channel, start with `@Claude` instead (the channel already knows the repo).

There are two pipelines, plus requests for the bags that are already on the site.

## A batch

When you give no numbers, Claude makes a **batch**: **20 statics + 5 video projects**. Every project has 4
versions (H1-H4, see below), so a batch is 20 statics and 20 videos. Give numbers to get exactly those
("2 projects and 6 statics" = 6 statics and 8 videos; "6 statics" = only statics).

## 1. Winners: new versions of this week's winning videos

| You want | Copy into the DM |
|---|---|
| A batch from the newest weekly brief | `Higgsfield-test: winners batch` |
| The same, other words | `Higgsfield-test: new batch for the winners` |
| Your own numbers | `Higgsfield-test: winners, 2 projects and 6 statics` |
| Projects from specific winners | `Higgsfield-test: new projects from winners 94-H4 and 148-H5` |
| A theme | `Higgsfield-test: winners batch, Black Friday` |

- The winners come from the newest weekly brief in Drive **Research Briefs** (the n8n report): its "increase
  budget" and "keep" ads. If the brief is more than 8 days old, Claude says so and still uses it. If it can't be
  read or names no winner we have, Claude uses all the winners in the library and says so.
- Each winner becomes one project: the proven video exactly as it is (no extra voice), with 4 openings cut from
  the winning video itself (a video with only 3 clean spoken openings gets one of them again under a new on-screen
  hook; the reply says which), the offer card and the end card. A line that makes a health claim is cut out
  automatically (e.g. "prevents shoulder pain" in 94-H4) and listed in the report.
- Fewer winners than projects (a winner's raw video isn't in the library yet, or the brief has fewer winners):
  the rest of the batch are new-angle videos of the same bag, and the reply says how many and why.
- Winners whose raw video isn't in the library yet are listed in the reply; send the raw file (or tell us where
  it is) and they're added. Asking again for the same winner reuses its 4 openings in another order: send new
  raw footage or lines to get new ones.
- Statics are of the winners' bag.

## 2. New products: everything from the product's Drive folder

| You want | Copy into the DM |
|---|---|
| A batch for every new product folder that has no ads yet | `Higgsfield-test: new product ad sets` |
| A batch for one product | `Higgsfield-test: new product Silhouette Bag` |
| Your own numbers | `Higgsfield-test: new product Silhouette Bag: 6 statics and 2 videos` |
| More ads for a product that already has some | `Higgsfield-test: more ads for the Silhouette Bag` (name it; "new product ad sets" skips products that have ads). Each new batch gets other statics, hooks and feature order |

**Before you write**, put one folder per product in Google Drive **Ad Creative Pipeline / New Products** (not
Outputs / New Products: that is where the finished ads land), named like the product (e.g. `Silhouette Bag`), with:
- **photos**: 3 or more on a plain white background (one per colour works best), plus photos of the bag worn and
  close-ups (zip, leather, inside). Photos showing a face are never used; a worn photo that may show part of a head
  (a chin, an ear, hair) is used in videos only, never in a static.
- **clips** of the bag, if you have them (phone clips are fine; no captions or music needed). Clips without any
  faceless photos give videos only: statics need photos.
- **a notes doc** (a Google Doc, Word, PDF or .txt file), one fact per line:
  - the price and the old price (`Price: $59.95 (was $119.95)`) or the discount (`50% off`);
  - a free gift, only if there is one (`Free matching pouch wallet`);
  - the colours, named as on the photos (`Colours: Coffee, Black, Beige, Wine Red, Apricot`);
  - 3 to 7 things that make it special, one short line each (`Dual zipper closure keeps everything secure`); 5-7
    lines make videos of about 60-70 s, 3-4 lines about 40-50 s (fewer lines still work: Claude makes a shorter video
    from what the notes say, a price, the colours, a gift, and tells you);
  - free shipping, only if it applies (`Free US shipping`): without that line the ads don't mention shipping.

Claude reads only that folder: **the website is not read** for new products. The ads say only what the folder
says: no reviews from other bags, no discount, free gift or free shipping your notes don't mention, nothing about
health. No price or discount in the notes = ads without an offer (and no Black Friday ads). A thin folder still
works: with few photos or lines the videos are shorter, made from what your notes say, and a video that would still
be too short (under 25 s) is left out while the statics are made; Claude then says what you could add for videos. Only a folder
with no usable photo and no clip makes nothing. Changed the folder later? Write the product's name again to get
ads from the new files.

## 3. The bags on the site (Hobo Bag, Hobo 2.0, Hobo 3-Piece Set, Slouchy Soft 3-Piece Set, Vintage Bag)

| You want | Copy into the DM |
|---|---|
| A few ads | `Higgsfield-test: 3 statics and 2 videos for the Hobo 2.0` |
| A theme | `Higgsfield-test: 4 statics and 3 videos, Black Friday` (also: Cyber Monday, Christmas / gift, Mother's Day, travel) |
| A batch | `Higgsfield-test: batch, Christmas` |

## Any pipeline

| You want | Write |
|---|---|
| Single videos without hook versions | `Higgsfield-test: 2 single videos for the Vintage bag` |
| A longer storytelling video (1.5-2 min) | `Higgsfield-test: 1 story video for the Vintage bag` |
| The older video formats (40-60 s: showcase / features / reviews / colours) | `Higgsfield-test: 2 classic videos for the Vintage bag` |
| No music | add `no music` |
| A fix | reply in the same thread: `P02 H3 with a different hook` or `redo project 2` |

Don't want one of the ads? Just don't upload it to Meta: Claude never deletes or moves files in Drive.

## Videos come in projects

Like the agency ads (ACH - MAX - 94 - H4): every video is a **project** with 4 versions, **H1 to H4**,
that share the same body and differ only in the first few seconds: the opening line, the opening shot and the
hook text. Put the 4 versions of a project in one ad set to see which hook wins. "2 videos" = 2 projects = 8
video files.

## What the videos look like (since 2026-10-14)

New videos follow what the top-impression ads (the owner's reference videos and the Ad Library) do, measured: one voice that talks straight to the viewer
("you stop worrying in crowds", never a made-up customer story), fast (about 200 words a minute, no long pauses), a new
picture about every 2 seconds that shows what is being said (hands opening the zip, keys into the pocket, the bag worn),
a specific hook in the first 3 seconds ("Four things you'll notice ..."), numbered chapters on screen ("1. you stop
worrying in crowds") with the feature's name, a problem and its fix, a review or two on screen for 3 seconds at most, the
offer last, and one steady loudness. They run **55-80 s**. A bag with few feature lines or reviews gets a shorter video
and Claude says so. Want the older formats? Add `classic`.

## What you get

- A Drive folder per request, with `Statics` and `Videos` (one subfolder per project: `P01 – …` with H1-H4), a
  short report and `…_ad_copy.csv` (2 primary texts, 2 headlines, a description and a CTA per static and per
  project):
  - winners: **Outputs / Winners / <date> – <request>**
  - new products: **Outputs / New Products / <date> – <request>**
  - the bags on the site: **Outputs / <date> – <request>**
- Claude's reply lists every ad (name, hook, length), the Higgsfield credits used and anything that needs a
  human.
- File names follow one pattern, e.g. `LC_261013_SilhouetteBag_Evergreen_P02_H3_colours.mp4` (project 2, hook 3).
  Use the file name as the Meta ad name, so results can be traced back to the ad and the hook.

## Time and cost

- Video length: videos are 55-80 s on purpose (the older `classic` formats 40-60 s, the story format 1.5-2 min),
  whatever you write. Asking for "hook-first", "a hook test" or "better hooks" gives different openings in the same
  full-length videos, never shorter ones. A video that comes out shorter than planned is not uploaded. Claude's reply
  includes a scorecard line per batch: how the videos measure against the targets above (a miss is reported, not hidden).
- Statics: a few minutes for all of them. A video project (4 versions): about 20-25 minutes. A batch (20 statics +
  5 projects) takes about 2 hours; Claude replies once, when everything is in Drive.
- AI scenes (since 2026-10-20): about 40% of the statics and a few video shots show the REAL bag in new scenes (a cafe
  table, the street from behind, a hallway, a flat-lay); every one is made from the real product photo and checked
  (no faces, same bag) before it is used, and anything that fails is replaced by the real photo / footage. Each new
  batch uses scenes, photos and captions the product's last batches did not (novelty log). `no AI` / `real photos only`
  in the message turns it off.
- Credits: the voiceover (about 0.35 per spoken line) and the AI scenes (about 1 per still, 4.5-6 per clip) cost Higgsfield
  credits; a whole batch is capped at 100. A new-angle or new-product
  project on its own: about 4-5 credits (the 4 versions of a project share the chapter lines; each hook is one more
  line); a winner project: 0 (it keeps its own voice). A full batch of a bag or new product: about 20-23 credits; a
  winners batch: 0-5 (only fill projects cost).
  A full batch with AI scenes: about 75-85 credits (voiceover ~22 + stills ~20 + clips ~40).

## Good to know

- Everything written follows Meta's rules: no health or medical claims, drugs, politics, religion or blood.
- Music: a soft generated bed under new-angle videos; winner videos keep their own sound. Want your own licensed
  tracks? Put them in a Drive folder and tell us; they're used instead.

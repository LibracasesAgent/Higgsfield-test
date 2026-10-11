# Making ads from Slack: quick guide

Write one line to Claude in the Libra ads Slack channel (start with `@Claude`). It makes the ads from
your real product photos and footage, adds one narrator voice, captions, review cards, the offer and a soft
music bed, writes the Meta copy (primary texts, headlines, description), and saves it all in Google Drive. Nothing is ever published: you review the files and upload the ones you like to Meta.

## What to write

| You want | Write |
|---|---|
| A few ads for a product | `@Claude make 3 statics and 2 videos for the Hobo 2.0` (2 videos = 2 projects × 4 hooks = 8 files) |
| A theme | `@Claude 4 statics and 3 videos, Black Friday` (also: Cyber Monday, Christmas / gift, Mother's Day, travel) |
| New versions of this week's winners | `@Claude new batch for the winners: 3 projects and 4 statics` |
| Projects from specific winners | `@Claude new projects from winners 94-H4 and 148-H5` |
| A new product test | `@Claude new product Silhouette Bag: 6 statics and 2 videos` (put its folder in Drive first, see below) |
| A big batch | `@Claude batch: 20 statics and 5 projects, Christmas` |
| Single videos without hook versions | `@Claude 2 single videos for the Vintage bag` |
| A longer storytelling video (1.5-2 min) | `@Claude 1 story video for the Vintage bag` |
| A fix | reply in the same thread: `P02 H3 with a different hook`, `redo project 2` or `drop S03` |

Products it knows: Hobo Bag (default), Hobo 2.0, Hobo 3-Piece Set, Slouchy Soft 3-Piece Set,
Vintage Bag, plus every new product you add.

## New products

1. In Google Drive open **Ad Creative Pipeline / New Products**.
2. Make one folder per product, named like the product (e.g. `Silhouette Bag`).
3. Put in it what you have:
   - photos (3 or more on a plain white background work best; lifestyle photos are fine too)
   - videos of the bag (phone clips are fine, no captions or music needed)
   - a short note: the libracases.com link, the offer (e.g. "50% off + free pouch wallet"),
     the colours and 3 to 5 things that make it special.
4. Write `@Claude new product <name>: N statics and M videos`.

The ads only use what is true for that product: no reviews from other bags, and no discount or
free gift unless the site or your note says so.

## Videos come in projects

Like the agency ads (ACH - MAX - 94 - H4): every video is a **project** with 4 versions, **H1 to H4**,
that share the same body (story, features, reviews, offer, end card) and differ only in the first few
seconds: the opening line, the opening shot and the hook text. Put the 4 versions of a project in one ad
set to see which hook wins. "2 videos" = 2 projects = 8 video files. Winner projects keep the proven video
exactly as it is (no extra voice, no inserted reviews) and test 2-4 different openings cut from the winning
video itself, one project per winner. Asking again for the same winner repeats its openings: send new raw
footage or lines to get new ones. A line in a winner that makes a health claim is cut out automatically
(e.g. "prevents shoulder pain" in 94-H4) and listed in the report.

## What you get

- A Drive folder **Outputs / <date> – <request>** with `Statics` and `Videos` (one subfolder per project:
  `P01 – …` with H1-H4), a short report listing every hook, and `…_ad_copy.csv`: 2 primary texts, 2
  headlines, a description and a CTA per static and per project (H1-H4 share it, each with its own first line).
- Claude's reply lists every ad (name, type, length), the Higgsfield credits used and anything that
  needs a human.
- File names follow one pattern, e.g. `LC_261008_HoboBag_BlackFriday_P02_H3_reviews.mp4` (project 2, hook 3). Use the file
  name as the Meta ad name, so results can be traced back to the ad and the hook.

## Time and cost

- Statics: about 1 minute each. A video project (4 versions): about 20 minutes (rendered from 4K footage).
  3 statics + 1 project takes about 25 minutes; 20 statics + 5 projects about 2 hours.
- Credits: only the voiceover costs Higgsfield credits (about 0.3 per spoken line): about 4 per project
  (winner projects 0). A normal request costs under 15 credits. No AI images or AI video are made.

## Good to know

- Everything written follows Meta's rules: no health or medical claims, drugs, politics, religion or blood.
- Music: a soft generated bed by default. Want your own licensed tracks? Put them in a Drive folder and tell
  us; they're used instead.

- The winners come from the newest weekly brief in Drive **Research Briefs** (the n8n report). If the
  brief is old, Claude says so and still uses the last one.
- Winners whose raw video isn't in the library yet are listed in the reply; send the raw file (or tell
  us where it is) and they're added.

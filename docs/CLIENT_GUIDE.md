# Making ads from Slack: quick guide

Write one line to Claude in the Libra ads Slack channel (start with `@Claude`). It makes the ads from
your real product photos and footage, adds voiceover, captions, reviews and the offer, and saves them
in Google Drive. Nothing is ever published: you review the files and upload the ones you like to Meta.

## What to write

| You want | Write |
|---|---|
| A few ads for a product | `@Claude make 3 statics and 2 videos for the Hobo 2.0` |
| A theme | `@Claude 4 statics and 3 videos, Black Friday` (also: Cyber Monday, Christmas / gift, Mother's Day, travel) |
| New versions of this week's winners | `@Claude new batch for the winners: 6 videos and 4 statics` |
| Versions of specific winners | `@Claude 3 new versions of winner 94-H4 and 2 of 148-H5` |
| A new product test | `@Claude new product Silhouette Bag: 6 statics and 2 videos` (put its folder in Drive first, see below) |
| A big batch | `@Claude batch: 20 statics and 10 videos, Christmas` |
| A fix | reply in the same thread: `V02 again with a different hook` or `drop S03` |

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

## What you get

- A Drive folder **Outputs / <date> – <request>** with `Statics` and `Videos`, and a short report.
- Claude's reply lists every ad (name, type, length), the Higgsfield credits used and anything that
  needs a human.
- File names follow one pattern, e.g. `LC_261008_HoboBag_BlackFriday_V02_reviews.mp4`. Use the file
  name as the Meta ad name, so results can be traced back to the ad.

## Time and cost

- Statics: about 1 minute each. Videos: about 10 minutes each (they're rendered from 4K footage).
  3 statics + 2 videos takes about 25 minutes; 20 statics + 10 videos about 2 hours.
- Credits: only the voiceover costs Higgsfield credits (about 0.3 per spoken line, roughly 1.5 per
  video). A normal request costs under 15 credits. No AI images or AI video are made.

## Good to know

- The winners come from the newest weekly brief in Drive **Research Briefs** (the n8n report). If the
  brief is old, Claude says so and still uses the last one.
- Winners whose raw video isn't in the library yet are listed in the reply; send the raw file (or tell
  us where it is) and they're added.

# Story statics that keep running: what top-tier Facebook image ads carry (2026-11-04)

Why: the team on the story + offer samples (PLAYBOOK 4n): "these are good but very basic and not top tier: check how actual fb ads
look with story". The Meta Ad Library is not reachable from here, so this file uses breakdowns of long-running ads and format datasets.
Tags: [V] verified in the source, [S] a source's claim (vendor data, method not public), [I] our inference, [U] unverified.

## What the sources say

- **Format system** (Curtis Howland, 67,852 active ads across 106 brands, Jun 2026) [S]: statics are 55.6% of all ads (64.8% for DTC).
  Twelve static formats recur: product hero, social proof / testimonial, before & after, feature callout, us vs them, UGC-native,
  grid, offer / promo, ugly / lo-fi, data callout, meme, listicle. A healthy account runs 6-8 formats at once. Ridge runs mainly product
  hero, us vs them and feature callout ("no copy is needed to understand the value gap"); Huel's callouts lead with outcomes, not specs.
  https://newsletter.curtishowland.com/p/the-dtc-static-ad-system-what-67852
- **Anatomy** (Superscale static ads playbook, 2026) [S]: statics with 5-6 of six elements win at about twice the rate of those with
  2 or fewer: a friction hook, a resolvable visual subject, ONE promise, visual social proof, an action CTA, a visible brand mark (8-12%
  of the height, top-left or bottom-right, never central). Specific friction in "you" words beats vague hooks ("Tired of paying ...?"
  won every test, "Make your charging easier" lost). Native-looking beats over-designed "billboard or magazine" pieces; bespoke images
  beat stock; AI tells (distorted text, a product that does not match the real SKU) hurt trust. https://superscale.ai/learn/static-ads/
- **Seven formats with live examples** (Adrio, Oct 2026) [V examples, S results]: problem-solution (Grüns: "Hitting a calorie
  deficit?" + three checkmarks + one proof point), before-after, review / testimonial (the quote IS the hook), comparison (two columns,
  3-5 rows, a generic other side), founder POV, offer stack (the offer leads, 3-5 included items, savings, a risk reversal),
  advertorial (editorial headline, 2-3 lines of story, proof, one CTA). https://adrio.ai/blog/best-meta-ad-formats
- **Ranked by job** (Pulp Digital) [S]: scalers (founder, offer-first banner, demo, unboxing), workhorses (grid, us vs them, authority,
  before / after, feature callout, headline), converters (letters and sticky notes, comment reply, educational infographic, catalogue
  templates, testimonials "done properly": the customer's specific result as a large headline with their name). Their bag example:
  Dr. Squatch "Yo, free bag" in huge type, the bundle, a "50% off" bubble, a supporting line, the brand last.
  https://www.pulpdigital.com.au/resources/best-ad-creatives/
- **Story formats in a 113-format library** (Runneth) [V]: comic strip, journal entry, letter, post-it, notes app, collage, slideshow,
  before / after; proof + offer: offer-first banner, review, social proof mashup, statistic, case study, press, badge, feature
  benefit pointout. https://runneth.com/library/formats/
- **The anti-theft bag category** (Runneth breakdown of the Foldie crossbody ad) [V]: the story is a staged pickpocket test (zip locks,
  a slash-proof strap, RFID), "proof over assertion", humour lowering a fear message. https://runneth.com/library/the-foldie
- Static examples roundups: https://sovran.ai/blog/static-ads-examples (testimonial card = quote + five stars + name; PAS in one
  frame), https://segwise.ai/blog/anatomy-high-converting-static-ad.md (one message, one value prop, one action; proof badges near
  the headline), https://www.trendtrack.io/blog-post/facebook-ad-examples, https://adlibrary.com/posts/best-dtc-meta-ads-examples-2026.

## What that means for Libra [I]

Our story + offer samples (B000 test, 4 Nov) carried 2-3 of the six layers: the picture, one line, the % sticker. The statics that keep
running carry 5-6: the hook names the friction ("Keys at the bottom of your bag again?"), the picture shows that moment, one promise
(the answer line), visible proof (stars + a verbatim review with a name), the offer stack (50% OFF + the free pouch wallet), a small
brand mark. AI image models set short words well but cannot be trusted with a customer's exact words or a full layered layout, so:

- **Layout `story`** (brand_statics.l_story): our renderer sets the layers in exact type over the AI story scene (or a real footage
  frame) in five looks of the formats above: `hook` (problem-solution: the hook with a marker highlight, the answer, a review card,
  the sticker + gift tag), `quote` (testimonial done properly: the customer's words as the headline, a big gold quote mark, stars, her
  name), `list` (listicle: 3 numbered reasons on a deep panel, a proof line), `versus` (us vs them: a generic open tote vs ours,
  crosses / ticks), `stack` (offer stack: the % huge, what you get as ticks, a proof line). The reviews are verbatim (reviews.json,
  the client said "Yes on all").
- The AI scene prompt asks for the composition its look needs (calm top for a hook, a calm darker bottom for a quote, the bag in the
  middle band for the panel looks), so no word lands on the bag.
- Mix: about half `ad` (the bold design pieces with the offer and a story line), about a third `story`, the rest real. Each look at
  most twice a batch, a different review each time.
- Never: a fake comment / chat / notes-app screen (Meta fake-interface rule, our FAKE_UI check), a before / after of a person, a
  named competitor on the "them" side, a made-up review or reaction, a countdown.

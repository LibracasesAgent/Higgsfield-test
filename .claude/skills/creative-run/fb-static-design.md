# Facebook static ad design rules (Libra Cases)

Every static must look like a finished, scroll-stopping Facebook/Instagram ad,
not a stock photo. Clean, premium, one clear message.

## Formats and safe zones
- **Feed 4:5** (1080x1350) is the main format. **Stories/Reels 9:16** (1080x1920) second.
- 9:16: keep all text and the product out of the top 14% and bottom 20% (app UI covers them).
- 4:5: keep a 6% margin on all sides; nothing important touching the edges.

## Layout (one idea per ad)
1. **Hook headline**: 2-6 words, top third, bold sans-serif, very high contrast.
   Use the brief's hook or the winning ad's angle.
2. **Product hero**: the bag is the biggest thing in the frame (40-60% of the area),
   sharp, correct colour and hardware, lit like a premium product shot.
3. **Support**: at most ONE of these: 2-3 short benefit callouts ("Full-grain leather",
   "Hidden zip pocket", "Fits a 13\" laptop") with thin lines/arrows to the feature;
   OR an offer badge; OR a short real customer quote.
4. **CTA pill** bottom area: "Shop Now" (or "Get Yours"), small, clean.
5. **Brand**: small "LIBRA" wordmark, same corner every time.
- Text covers under ~20% of the image. No paragraphs. Max ~15 words on the whole ad.

## Look
- Backgrounds: warm neutrals that flatter leather: cream, sand, soft taupe, warm white,
  natural wood, linen, stone. One accent colour at most (deep brown or muted terracotta).
- Light: soft directional daylight, gentle shadow under the bag; no harsh flash.
- Styling props (sparingly): sunglasses, phone, keys, wallet, AirPods, notebook, coffee,
  flowers. They show what fits in the bag or the lifestyle; they never compete with it.
- **No human faces** (client rule). Hands, or a torso cropped below the chin, are fine.
- Typography: one font family, max two weights. Offer numbers in the accent colour.

## Proven templates (rotate; never the same one twice in a day for a product)
1. **Hero + headline**: bag centred on a clean surface, hook on top, CTA pill.
2. **Feature callouts**: bag at 3/4 angle, 3 labelled callouts pointing at features.
3. **What fits inside**: bag open with everyday items spilling neatly beside it.
4. **Colour lineup**: all colourways side by side, "Which one's yours?".
5. **Craft detail**: macro of stitching/leather grain, headline about hand-made quality.
6. **Comparison**: "Designer look. Without the designer price." (no competitor names/logos).
7. **Offer**: bag + bold offer badge; only when an offer is set in config.
8. **Real review**: bag + one short quote + 5 stars; only with a real review from
   `Raw files/Reviews` or the brief; never invent quotes, ratings or numbers.

## Claims (strict)
- Offers ("50% off"), prices, ratings, customer counts, materials: only if given in
  `pipeline/config.json` (`brand.offer_text`, `brand.facts`) or the brief. Otherwise leave out.
- No competitor brand names or logos. No "#1", "best in the world", medical or
  guarantee claims unless provided.

## Prompt skeleton (fill every <>)
"Facebook feed ad, <4:5 | 9:16>, clean premium e-commerce design. Hero: the <colour>
<product> from the reference image, exact shape, leather, gold hardware and strap,
<angle>, on <background>, soft daylight with a gentle shadow. Headline at the top in
bold modern sans-serif, spelled exactly: "<hook>". <One support element>. Small rounded
"Shop Now" button at the bottom<, small LIBRA wordmark bottom-left>. Generous negative
space, balanced layout, sharp product focus, no human faces, no extra text, no other
logos. resolution: 2k"

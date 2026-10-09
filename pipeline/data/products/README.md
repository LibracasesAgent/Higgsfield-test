# New products (one JSON file per product)

Products that are not built into `pipeline/make_batch.py` (`PRODUCTS`) live here as
`<slug>.json`, e.g. `silhouette-bag.json`. `make_batch.py plan --product "<key or alias>"` builds
statics and videos from them in the same house style as the built-in bags: real photos and footage,
our voiceover, captions, tags, review cards, offer card, end card. No AI images or AI video.

## The flow

1. **The client** makes a folder in Drive `Ad Creative Pipeline / New Products`, named like the product,
   with photos, clips and a notes doc (libracases.com link, offer, colours, 3-5 things that make it
   special). It may have `photos/` and `clips/` subfolders.
2. **Claude** runs the intake:
   ```
   python3 pipeline/new_product.py list                      # which product folders exist, which are done
   python3 pipeline/new_product.py intake "Silhouette Bag"   # or --latest, or --site <url|handle> [--name ...]
   ```
   It downloads everything into `pipeline/cache/new_products/<slug>/`, reads the site page (price,
   compare-at price, colours, description), scores the photos, proposes clip start times, makes
   `overview.jpg` plus one contact sheet per clip, and writes `<slug>.json` with `"status": "draft"`.
3. **Claude reviews the draft.** It opens `overview.jpg` and the sheets, then rewrites the features
   (3-5, only true claims from the site or the notes), checks the offer and may add 6-10 `hooks` (opening
   lines of different types, so each video's 4 hook versions differ). When it is happy it sets
   `"status": "ready"`.
4. `python3 pipeline/new_product.py check <slug>` must show `"ok": true`.
5. Commit the JSON file (never the media). Then use the standard path:
   `make_batch.py plan --product "<key>" ...`.

No Drive folder? `intake --site https://libracases.com/products/<handle>` works from the site alone,
and `intake --local <dir> --name "..."` works from a folder on disk. Files read from disk have no Drive id,
so they only work in the current session.

## The fields

| Field | What it is |
|---|---|
| `key` | Lowercase name used in requests and `--product`, e.g. `"silhouette bag"`. The file name is the key with dashes: `silhouette-bag.json`. |
| `aliases` | Other words that should find this product in a request (`"silhouette"`, the site handle). Keep them specific: never just "bag" or "tote". |
| `name` / `short` / `end` | Display name ("The Silhouette Bag"), the short form used in spoken lines and headlines ("Silhouette Bag"), and the end-card title. |
| `site` | The Shopify handle on libracases.com, or `null` when the product is not on the site. `site_assets.py` downloads the site photos, price and colours from it at plan time. |
| `photos` | The client's photos from the Drive folder: `id` (Drive file id), `name`, `clean` (1.0 = plain packshot on white with empty corners, from `site_assets.clean_score`), `faces` (number of faces found; **more than 0 = never use in statics**), `w`, `h`, `path` (cached copy). Client photos with `faces` 0 that are not packshots become the lifestyle statics. |
| `site_lifestyle` | Optional. Site photos Claude has looked at in `overview.jpg` and wants as lifestyle statics, by their number there: `["S3", "S7"]` (never `S0`: it carries the sale badges). Without it, site photos are only used as packshots, never as lifestyle photos. |
| `clips` | The client's videos: `id`, `name`, `dur`, `w`, `h`, `good` (3 proposed start times in seconds, each leaving about 2.5 s of footage), `mute` (true: the clip's own sound is not used), `audio`, `path`, `sheet` (contact sheet). |
| `offer.badge` | The corner badge on statics, e.g. `{"top": "NOW", "big": "50%", "bottom": "OFF"}`, or `null` when there is no discount. For a product with a `site` page, `plan` re-reads the price and compare-at price and uses the site's % if it changed (and says so). |
| `offer.gift` | The free extra exactly as the site or the notes word it (`"free matching pouch"`), or `null`. |
| `offer.offer_title` / `offer.offer_sub` | Text of the offer card in videos: `"50% OFF"` / `"+ FREE MATCHING POUCH"` (both `""` when there is nothing to offer). |
| `offer.statics_sub` | One short line under the headline on statics. |
| `offer.close` | The last spoken line of every video. It always ends with "Tap the link below." |
| `offer.evidence` | Where the offer came from (prices, quoted phrases). Only for review: never shown in ads. |
| `hook_clips` | Shots for the first second of a video (picks, see below). |
| `features` | 3-5 entries `["spoken line", "TAG", [pick, ...]]`. The line is one short spoken sentence; the TAG is the 2-3 word uppercase label shown with it ("CONVERTIBLE STRAPS"). |
| `hooks` | Optional. 6-10 opening lines for the hook versions (H2-H4) of each video project (`pipeline/projects.py`): `"line"` or `{"text": "...", "type": "problem", "labels": ["SOUND FAMILIAR?"], "feature": "ZIP TOP"}`. One spoken line of 15 words at most; `type` one of problem, curiosity, question, feature, offer, gift, travel, POV, story (left out: guessed from the words); `labels` 1-4 UPPERCASE words shown on screen; `feature` a feature TAG whose footage opens the version. Only true claims from `facts`; an offer only through `{P}` / `{off_sp}` / `{price_sp}` / `{gift_sp}` (filled from the real offer, as in `pipeline/data/hooks.json`). Without it, the hook versions use the feature lines and a few generic lines. |
| `customer` | Real customer clips `[section, key, start, end]` from `clip_bank.json`. Empty for new products. |
| `broll` | Shots used under review cards and the close. |
| `reviews` | Review numbers from `pipeline/data/reviews.json`, **only if the review is about this product** (its `product` names this product). Empty by default. Reviews 6-10 (`"product": "any"`) are store reviews the client approved for the built-in bags: never in a product file (`check` refuses them, `plan` drops them). |
| `facts` | What the claims may be based on: `price`, `compare_at`, `colours`, `description` (site), `notes` (the client's notes), `title`, `url`. |
| `source` | Where the intake read from: `drive_folder`, `folder_name`, `site_url`, `site_match`, `cache`, `overview`, `added`. |
| `status` | `"draft"` straight after the intake, `"ready"` once Claude has checked features and offer. |

A **pick** says which footage to show:

- `["clip", 0, 5.5]`: the product's own clip 0, starting at 5.5 s
- `["photo", 2]`: photo 2 of the plan's photo pool (client photos without faces plus the site packshots,
  counted modulo the pool size), shown as a still with a slow zoom
- `["hobo_bag", "back_pocket_4k", 1.0]`: a clip from `clip_bank.json` (section, key, start), as for the built-in products

## Rules the intake keeps (and `check` enforces)

- **No invented offers.** The intake fills in a percentage only from the site's compare-at price (at least
  10% above the price, rounded down to a multiple of 5). A gift is only used when a phrase like "free pouch /
  wallet / purse / gift" appears on the site or in the notes. When the product is not on the site, a percentage
  the client wrote in the notes is listed under `offer.evidence`; Claude may copy it into the badge, and `check`
  accepts that. `check` also reads every line a customer sees (name, features and tags, `hooks` and their labels,
  `statics_sub`, `close`, offer card): a %, "free ..." or sale words ("deal", "last call", "selling fast") the
  offer does not back are a problem. A product with no offer cannot run a Black Friday / Cyber Monday batch (`plan` exits 2).
- **No faces in statics.** `faces` comes from a DNN face detector (OpenCV YuNet, `pipeline/assets/models`), on the
  photo and its mirror image; lifestyle photos also get the strict check (Haar frontal + profile cascades,
  mirrored, no skin-tone filter). `plan` re-checks every photo it uses, and `render` checks every finished static:
  a face there is a hard failure that `upload` never sends. Look at `overview.jpg` anyway: red labels mark faces.
- **Only true claims.** The draft features are copied from the site description and the notes. Rewrite
  them to sound spoken, but never add a claim that is not in `facts`.

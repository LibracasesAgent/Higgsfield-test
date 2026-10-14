# New products (one JSON file per product)

Products that are not built into `pipeline/make_batch.py` (`PRODUCTS`) live here as
`<slug>.json`, e.g. `silhouette-bag.json`. They are made from the client's Drive folder by
`pipeline/new_product.py` and built into ads in the same house style as the built-in bags: real photos and
footage, our voiceover, captions, tags, offer card, end card. No AI images or AI video.

## The flow (no human step)

1. **The client** makes a folder in Drive `Ad Creative Pipeline / New Products`, named like the product,
   with photos, clips and a notes doc (price / was price or % off, a gift if any, colours, 0-7 things that make
   it special, free shipping only if it applies). It may have `photos/` and `clips/` subfolders.
2. **The Slack agent** runs the new-product pipeline (CLAUDE.md section 2):
   ```
   python3 pipeline/new_product.py list        # folders newest first: status new | draft | ready | tested <date>, changed, tests
   python3 pipeline/make_batch.py plan --pipeline new-product --new-product "Silhouette Bag" --request "..." --out $OUT
   ```
   `plan` calls `new_product.ensure()`: no product file yet → the intake runs; folder unchanged since the intake
   (`source.files`: ids + modifiedTime) → the file is reused; folder changed → a file nobody edited (a ready
   `"auto"` one or an intake draft: `source.auto_sig` still matches) is made again, keeping its `tests`; a
   hand-edited one is kept (a warning names the new files); `--refresh-product` always makes it again (hand edits
   are lost). `--new-product next` = the newest folder with no `tests` yet. A folder name matches exactly, else
   normalised (case, a leading "the", punctuation and a plural s ignored), else as a unique part.
3. **The intake reads only the folder** (libracases.com is never read unless asked, below): it downloads photos
   (→ jpg: HEIC converted, EXIF rotation applied), clips and every note-like file (.txt .md .url .csv, Google Docs /
   Sheets, .docx, .pdf with `pdftotext`, else `pypdf`, .rtf, plus the folder's own Drive description) into
   `pipeline/cache/new_products/<slug>/` (`$LC_NP_CACHE` in tests; not committed: a later session downloads each
   photo by its Drive id and converts it the same way), checks faces (and, on worn photos, part of a head), sorts
   the photos into `kind`s, proposes clip start times, reads price, was price, an "NN% off", a gift and the colours
   from the notes, turns the client's bullets into 3-7 spoken feature lines + tags (lines naming another product,
   sales talk, odd words, compliance problems or claims the offer doesn't back are dropped and listed, and so are
   bullets past the 7th), picks the footage that shows each (zip → the zipper close-up, straps → a worn photo, room
   → the open bag, shape → a packshot), and writes `overview.jpg` + one contact sheet per clip.
4. **Auto-ready:** no `check` problems (a folder with fewer than 3 feature lines is still ready: plan pads the videos from the notes and leaves out any that stay under the floor) → `"status": "ready", "auto": true`, and `plan`
   builds from it right away. Otherwise `"status": "draft", "auto": false` with the problems: `plan` prints the
   intake's warnings, exits 2 and names them.
5. **Optional look:** `overview.jpg` (path in `source.overview`) shows the photos as P0, P1 … and the clip
   moments. An obviously wrong pick or line may be fixed by hand (only true claims from `facts.notes`); then set
   `"auto": false` so `ensure()` keeps the edit, and run `python3 pipeline/new_product.py check <slug>` (must
   show `"ok": true`).
6. **After the upload** `make_batch.py upload` appends the batch to `"tests"` (dated by the plan); the agent
   commits the file (JSON only, never the media) with the batch specs. The next plan of the product picks
   `--seed` 1 + its batches by itself, so another batch differs.

By hand (same intake, CLI):
```
python3 pipeline/new_product.py intake "Silhouette Bag"            # a folder: exact name or a unique part of it (--latest: newest)
python3 pipeline/new_product.py intake "Silhouette Bag" --use-site # libracases.com fills only what the folder lacks
python3 pipeline/new_product.py intake --site https://libracases.com/products/<handle> [--name ...]   # a site-only product
python3 pipeline/new_product.py intake --local <dir> --name "..."  # a folder on disk (no Drive ids: this session only)
python3 pipeline/new_product.py check silhouette-bag               # slug, key or path; exit 1 on problems
```
`--force` redoes a file that is already ready, `--draft` keeps it draft even without problems, `--products-dir`
writes elsewhere. `--site` / `--use-site` are the only ways the intake reads libracases.com, and then only for
what the folder lacks (prices, colours, a gift the notes don't mention, more feature lines); without them a link to
the site in the notes is only recorded (`source.notes_link`), never opened.

## The fields

| Field | What it is |
|---|---|
| `key` | Lowercase name used in requests and `--product`, e.g. `"silhouette bag"`. The file name is the key with dashes: `silhouette-bag.json`. A folder named like a built-in bag ("Hobo Bag") keeps that key, with a warning: `plan --pipeline new-product` uses the folder's own file, never the built-in bag or the site. |
| `aliases` | Other words that should find this product in a request (`"silhouette"`, the site handle). Keep them specific: never just "bag" or "tote", a colour, a built-in bag's name or another product file's alias (the intake drops those). |
| `name` / `short` / `end` | Display name ("The Silhouette Bag"), the short form used in spoken lines and headlines ("Silhouette Bag"), and the end-card title. |
| `site` | `null` for a Drive-only product (the default). With `--site` / `--use-site`: the Shopify handle on libracases.com; `plan` then re-reads its price and compare-at price on every run. |
| `photos` | The client's photos, sorted: photos without faces first, cleanest first (the P numbers of `overview.jpg`: P0 = `photos[0]`): `id` (Drive file id), `name` (the cached jpg), `src_name` (the Drive original's name), `clean` (1.0 = plain packshot on white with empty corners), `faces` (number of faces found; **more than 0 = never used anywhere**), `statics` (`false` = never in a static, videos only: a face, or a worn photo that may show part of a head: a chin, an ear, hair; never set it to `true` by hand), `kind`, `w`, `h`, `path` (cached copy). |
| `photos[].kind` | `packshot` (plain backdrop: hero / offer statics, colour swatches by shade, the close), `worn` (on a person, no face: lifestyle statics, the lifestyle video's opening), `detail` (close-up: the showcase video's opening), `other` (e.g. an infographic: kept out of full-bleed lifestyle statics when there are enough worn / detail photos). Cheap pixel checks: a wrong kind can be fixed by hand. |
| `site_lifestyle` | Optional, only with a `site`. Site photos to use as lifestyle statics, by their number in `overview.jpg`: `["S3", "S7"]` (never `S0`: it carries the sale badges). |
| `clips` | The client's videos: `id`, `name`, `dur`, `w`, `h`, `good` (start times in seconds, about one per 4.5 s, just after scene changes, each leaving at least 2.5 s), `mute` (true: the clip's own sound is not used), `audio`, `path`, `sheet` (contact sheet). |
| `offer.badge` | The corner badge on statics, e.g. `{"top": "NOW", "big": "50%", "bottom": "OFF"}`, or `null` when there is no discount. |
| `offer.gift` | The free extra exactly as the notes word it (`"free matching pouch"`), or `null`. |
| `offer.offer_title` / `offer.offer_sub` | Text of the offer card in videos: `"50% OFF"` / `"+ FREE MATCHING POUCH"` (both `""` when there is nothing to offer). |
| `offer.statics_sub` | One short line under the headline on statics. |
| `offer.close` | The last spoken line of every video. It always ends with "Tap the link below." |
| `offer.evidence` | Where the offer came from (prices, quoted phrases). Only for review: never shown in ads. |
| `hook_clips` | Shots for the first second of a video (picks, see below). |
| `features` | 0-7 entries `["spoken line", "TAG", [pick, ...]]`. The line is one short spoken sentence (14 words at most); the TAG is the 2-3 word uppercase label shown with it ("ZIP CLOSURE"), never more than its line says ("LEATHER FINISH", not "SOFT LEATHER", for a line that only says leather). A product with no reviews or customer clips says all of them (3-5 features: videos ~32-35 s; 7: ~42-45 s). |
| `hooks` | Optional. 6-10 opening lines for the hook versions (H2-H4) of each video project (`pipeline/projects.py`): `"line"` or `{"text": "...", "type": "problem", "labels": ["SOUND FAMILIAR?"], "feature": "ZIP TOP"}`. One spoken line of 15 words at most; `type` one of problem, curiosity, question, feature, offer, gift, travel, POV, story (left out: guessed from the words); `labels` 1-4 UPPERCASE words shown on screen; `feature` a feature TAG whose footage opens the version. Only true claims from `facts`; an offer only through `{P}` / `{off_sp}` / `{price_sp}` / `{gift_sp}` (filled from the real offer, as in `pipeline/data/hooks.json`). Without it, the hook versions use the feature lines, POV / question openings made from the feature lines' own words ("Need room for your phone, wallet, keys ...?") and a few generic lines. |
| `customer` | Real customer clips `[section, key, start, end]` from `clip_bank.json`. Empty for new products. |
| `broll` | Shots used under review cards, the close and to fill gaps (picks). |
| `reviews` | Review numbers from `pipeline/data/reviews.json`, **only if the review is about this product** (its `product` names this product). Empty by default. Reviews 6-10 (`"product": "any"`) are store reviews the client approved for the built-in bags: never in a product file (`check` refuses them, `plan` drops them). |
| `facts` | What the claims may be based on: `price`, `compare_at`, `price_source` (`"notes"` or `"site"`), `price_line` (the notes line the price came from), `colours`, `description` (site, only with `--site` / `--use-site`), `notes` (the client's notes, every file under a `## <file name>` heading), `title`, `url`. |
| `source` | Where the intake read from: `kind` (`drive` / `site` / `local`), `drive_folder`, `folder_name`, `files` (`[{id, name, modifiedTime}]`: what `ensure()` compares), `site_url`, `site_match`, `notes_link` (a libracases link in the notes, not opened), `local_dir`, `cache`, `overview`, `added`, `auto_sig` (hash of the editable fields at intake, drafts included: a file whose hash changed was edited by hand), `draft_asked` (made with `--draft`: a re-made file stays draft). |
| `status` | `"draft"` (problems, or `--draft`) or `"ready"`. `plan` refuses a draft (unless `--allow-draft`). |
| `auto` | Written by every intake: `true` = made ready without a human edit, `false` = a draft. Set it to `false` after editing a ready file by hand. |
| `tests` | Batches made from this file, appended by `make_batch.py upload` (`new_product.record_test`): `date`, `name`, `drive_link`, `statics`, `videos`, `projects`, `plan`, `request`. A second upload into the same Drive folder (statics first, videos later) updates its entry. `list` shows `tested <date>`; `--new-product next` skips folders that have tests. |

A **pick** says which footage to show:

- `["photo", "P2"]`: the product file's own `photos[2]` (P2 in `overview.jpg`), shown as a still with a slow zoom;
  a photo with a face is never shown (`plan` skips the pick with a warning), a `"statics": false` one only in videos
- `["clip", 0, 5.5]`: the product's own clip 0, starting at 5.5 s
- `["photo", 2]` (a number, older files and site-only products): photo 2 of the plan's photo pool (client photos
  without faces plus the site packshots, counted modulo the pool size)
- `["hobo_bag", "back_pocket_4k", 1.0]`: a clip from `clip_bank.json` (section, key, start), as for the built-in products

The product's own photos and clips that are not 9:16 (square packshots, a 1080x1080 clip) are framed whole in the
videos and their hook versions (`"fit": "auto"` in the spec segments, `recut.py`: a flat backdrop from the photo's
own border behind a light studio shot, else a blurred copy of the picture), never cropped to the middle. Built-in and
`clip_bank` footage is cropped as before.

## Rules the intake keeps (and `check` enforces)

- **No invented offers.** A percentage comes from prices (the notes' price and was price, else the site's
  compare-at with `--site` / `--use-site`: at least 10% above the price, rounded down to a multiple of 5) or from
  an "NN% off" the notes state; both and they disagree → the lower one, with a warning. A gift is only used when a
  phrase like "free pouch / wallet / purse / gift" appears in the notes (or the site) and is not negated ("No free
  gift", "Free gift: none" are no gift). No price and no % in the notes = no offer: the ads run without one, and a
  Black Friday / Cyber Monday batch exits 2. `check` reads every line a customer sees (name, features and tags,
  `hooks` and their labels, `statics_sub`, `close`, offer card): a %, "free ..." or sale words ("deal", "last
  call", "selling fast") the offer does not back are a problem.
- **No faces.** `faces` comes from a DNN face detector (OpenCV YuNet, `pipeline/assets/models`), on the photo and
  its mirror image; lifestyle photos also get the strict check (Haar frontal + profile cascades, mirrored, no
  skin-tone filter). A worn photo with no face found still gets `"statics": false` when it may show part of a head
  (`new_product.head_part`: on a studio photo skin or hair at the top edge above the shoulders, or a figure that
  doesn't reach the top edge; a worn photo shot in a scene always; a wrong flag costs one static, never a face).
  A photo with a face is never picked; `plan` re-checks every photo it uses (a face found then: the photo and its
  picks are skipped, with a warning), and `render` checks every finished static: a face there is a hard failure
  that `upload` never sends.
- **Only true claims.** Feature lines come from the client's notes (the site's description only with `--site` /
  `--use-site`); a line that names another product ("Like our Hobo Bag", the site's "The Libra Covenette Bag ...")
  is dropped. A hand edit may reword a line to sound spoken, but never adds a claim that is not in `facts`. For a
  Drive-only product (`site` null) the compliance check's evidence is the product file alone (not PLAYBOOK's
  store-wide lines): its ad copy says free shipping or libracases.com only when the notes do ("Tap the link to see
  the …" instead).

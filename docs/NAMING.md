# Ad naming rules

One pattern for every file and the Drive folder, so ads can be found, matched to Meta results and never launched twice by mistake.

```
Drive folder:  B<NNN> – <YYYY-MM-DD> – <Product> [<Theme>] – <N> statics + <M> projects
File:          LC_<YYMMDD>_<Product>_<Theme>_B<NNN>[r<R>]_<ID>_<angle>.<ext>
```

**Every batch has a number.** `make_batch.py plan` takes the next free one from `pipeline/data/batch_ledger.json` (B011, B012 ...), puts it in
every file name and in the Drive folder, and `upload` records the folder, the link and the ads in the same ledger (`docs/BATCHES.md` is the
table of all batches; `python3 pipeline/ledger.py show` prints it). One request for three bags is three batches (B045, B046, B047), one
Drive folder each. The number is global (not per bag), so "B045" means exactly one folder and one set of ads.

| Part | Rule | Examples |
|---|---|---|
| `LC` | fixed brand prefix | `LC` |
| `YYMMDD` | date the batch was planned | `261020` |
| `Product` | CamelCase, letters/digits only | `HoboBag`, `Hobo20`, `HoboBag3PieceSet`, `VintageBag` |
| `Theme` | CamelCase theme; `Evergreen` if none; a theme that is not built in keeps its own words | `BlackFriday`, `Christmas`, `Evergreen` |
| `B<NNN>` | the batch number (3 digits; `B000` = not in the ledger, offline tests only) | `B045` |
| `r<R>` | a second run of the same batch: a redo of some of its ads (`plan --batch-id B045 --only P02`) keeps the number and adds `r2`, `r3`; the old files stay untouched | `B045r2` |
| `ID` | `S01`… statics; videos `P01_H1`… = project 01, hook version 1 (every video is a project: one body in 4 hook versions H1-H4 that differ only in the first seconds, as the agencies' `ACH - MAX - 94 - H4`); `V01`… = single videos (`plan --hooks 1`); numbered per batch | `S03`, `P02_H4`, `V12` |
| `angle` | layout (statics) or format (videos), lowercase | `studio native offer quotes value stars checklist colours` (older: `hero promo bold review compare`) / ugc videos `day things demo stop travel value`; winner remixes `remix<N>` |

Examples: `LC_261020_HoboBag_Evergreen_B045_S01_native.png`, `LC_261020_Hobo20_Evergreen_B047_P02_H3_things.mp4`,
`LC_261107_HoboBag_BlackFriday_B061_S04_offer.png`, a redo of project 2 of batch 45: `LC_261021_HoboBag_Evergreen_B045r2_P02_H1_demo.mp4`.
(in `plan.json`, `render --only` and `upload --only` the same version is `P01H3`; `P01` = all its versions.)

Rules:
1. Generated automatically by `make_batch.py plan` (stored as `prefix` and `batch_id` in `plan.json`); never rename by hand.
2. No spaces, no special characters, ASCII only, extension lowercase (`.png`, `.mp4`).
3. Hand-built specs (winner remixes, new products) follow the same pattern.
4. Never reuse a name for different content; a redo gets `r2` (`--batch-id`), the old files stay untouched. `upload` skips a file that is
   already in Drive with the same content; a newer render with the same name goes up as `<name>_updHHMM` with a warning (a human removes
   the old one: we never delete Drive files).
5. Drive folder: `B<NNN> – <date> – <Product> – <N> statics + <M> projects` with `Statics` and `Videos` subfolders (as `upload` does);
   project videos go one folder per project inside `Videos`: `P01 – day`, `P02 – things`. Don't pass `--name` to `upload`: the folder
   name is made from the plan (a free-text name is what made the batches look alike).
6. Meta ad name = the file name without the extension, so results map back to the file. **Before launching anything, look the batch
   up** (`docs/BATCHES.md`, or the `<prefix>_ads.csv` in its Drive folder: one row per ad, hook or caption, length, QA flags and an
   empty `launched` column to fill in): a batch that is marked launched is not launched again; a new batch of the same bag has another number.
7. Repeats: `plan` compares every static (layout + photo + words) and every hook line with the earlier batches of the same bag (the ledger,
   and the novelty log for batches from before it) and prints `repeat: S04_native was already made in B038 (2026-10-16)`: those ads are
   not new, and the reply says so. Batches before the ledger are B001-B010 (their Drive folders keep their old names).

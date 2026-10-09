# Ad naming rules

One pattern for every file and the Drive folder, so ads can be found, matched to Meta results and never collide.

```
LC_<YYMMDD>_<Product>_<Theme>[_vN]_<ID>_<angle>.<ext>
```

| Part | Rule | Examples |
|---|---|---|
| `LC` | fixed brand prefix | `LC` |
| `YYMMDD` | date the batch was made | `261007` |
| `Product` | CamelCase, letters/digits only | `HoboBag`, `Hobo20`, `HoboBag3PieceSet`, `VintageBag` |
| `Theme` | CamelCase theme; `Evergreen` if none; a theme that is not built in keeps its own words | `BlackFriday`, `Christmas`, `MothersDay`, `Gift`, `ValentinesDay`, `Evergreen` |
| `_vN` | a redo of the same product+theme+day: `plan` looks in Drive (read-only) and moves to the first free `_vN` by itself (`--rev N` to start higher); v1 has no suffix | `_v2` |
| `ID` | `S01`… statics, `V01`… videos, numbered per batch | `S03`, `V12` |
| `angle` | layout (statics) or format (videos), lowercase | `hero promo bold review colours compare` / `features reviews colours`; winner remixes: `remix<N>`, e.g. `remix94` |

Examples: `LC_261007_HoboBag_BlackFriday_S01_hero.png`, `LC_261007_Hobo20_Evergreen_V02_reviews.mp4`,
`LC_261007_HoboBag_BlackFriday_v2_V01_features.mp4`.

Rules:
1. Generated automatically by `make_batch.py plan` (stored as `prefix` in `plan.json`); never rename by hand.
2. No spaces, no special characters, ASCII only, extension lowercase (`.png`, `.mp4`).
3. Hand-built specs (winner remixes, new products) follow the same pattern: `LC_<date>_<Product>_<Theme>_V01_remix94`.
4. Never reuse a name for different content; a redo gets `_vN`, the old files stay untouched. `upload` skips a file
   that is already in Drive with the same content; a newer render with the same name goes up as `<name>_updHHMM`
   with a warning (a human removes the old one: we never delete Drive files).
5. Drive folder: `<YYYY-MM-DD> – <short request name>` with `Statics` and `Videos` subfolders (as `upload` does).
6. Meta ad name = the file name without the extension, so results map back to the file.

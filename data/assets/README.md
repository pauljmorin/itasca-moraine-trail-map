# Assets layer — placeholder

No real inventory photos have been processed yet. When the first
real batch runs, `scripts/photo_pipeline.py build` writes here:

- `assets.geojson` — one Point per GPS-carrying photo
  (type `unclassified`, condition null until classification)
- `flags-report.md` — no-GPS photos, oversize refusals, duplicates

Web-sized derivatives (max 1600 px, one per displayed photo) are
written to `site/assets-photos/`. Original photos never enter this
repository — they live in the shared Drive folder, and each pin
carries that file's Drive ID (`drive_id`, filled at Drive ingest).

Test fixtures and their proof outputs live in
`photos-inbox/_test/` (see DESIGN.md, photo pipeline section).

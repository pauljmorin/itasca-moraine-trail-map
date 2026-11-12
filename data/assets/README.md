# Assets layer — the chapter's physical inventory

Assets are points derived from photographs (pipeline below). Every
item in the inventory carries a **serial number** —
`ITM-<type>-<nnn>` (Paul, 2026-11-11; full design:
`docs/asset-serial-numbers-2026-11-11.md`).

## Serial numbers

- **Format:** `ITM-BN-014` — chapter prefix `ITM`, two-letter type
  code, zero-padded three-digit sequence per type (grows to four
  digits past 999). The serial tells you what the thing is; nothing
  else is encoded in it — condition, section, location,
  photographer, date, and Drive ID all live in the pin record.
- **Registry:** `registry.json` in this folder is the single source
  of truth — the type-code table plus the next number per type and
  the issued/retired maps. A serial once issued is never reused and
  never renumbered; a removed item's serial retires with it.
- **Assignment is editorial, never automatic.** `photo_pipeline.py
  build` always writes `serial: null`. After a batch is classified
  (the chapter classifies through its interface, Paul approves), run
  `scripts/assign_serials.py` — it stamps the next numbers in
  chainage order, west to east, per type, and writes the registry
  back. Unclassified pins carry no serial.
- **Type codes** (canonical pin `type` values are the lowercase
  names; the code is derived from the name at assignment):

  | Code | Type (pin value) | Status |
  |---|---|---|
  | BN | bench | proposed — not yet observed |
  | CP | carsonite post | seeded |
  | KI | kiosk | seeded |
  | SG | sign | seeded — one code for signs of any kind; subtype goes in `sign_kind` |
  | PK | parking area | seeded — one serial per area |
  | CS | campsite | seeded — campsite / bivouac site |
  | PO | post | seeded — post, other (non-Carsonite) |
  | BR | bridge | proposed |
  | BW | boardwalk | proposed |
  | SH | shelter | proposed |
  | WT | water source | proposed — pump / spring / faucet |
  | UN | unclassified | the bucket — a type value, never a serial prefix |

  A physical mile post is a Carsonite post (CP), not a sign. A new
  type gets its two-letter code when the classification pass first
  meets it — the code is approved by Paul, joins this table and the
  registry, and its counter opens at 001. Codes are never recycled.
- **Reclassification after publication does not change the serial:**
  the `type` field is corrected, the serial stands, and the
  discrepancy is noted in the registry.

## Pin fields

`photo`, `datetime`, `photographer`, `type` (`UN` until the chapter
classifies it), `condition` (null until the chapter grades it — Muse
does not grade), `drive_id`
(filled at Drive ingest), `derivative`, `direction_deg` /
`direction_ref` / `direction_compass` (camera facing, null when the
photo has no valid EXIF ImgDirection), plus:

- `serial` — string, null until assigned
- `sign_kind` — string, null unless the pin is a sign (SG):
  regulatory / wayfinding / interpretive
- `chainage_mi` — miles along the depicted chain from its west end
  (GAP-W west end = 0); null for off-chain pins
- `section` — nearest section (or `GAP-W`); null for off-chain pins
- `snap_m` — distance from the pin to the depicted chain, metres

## Workflow

1. **Intake** — `scripts/photo_pipeline.py build` writes
   `assets.geojson` here (one Point per GROUP of GPS-carrying
   photos — front face, back face and detail shots of one asset
   grouped by time + position — type `UN`, serial null) and
   `flags-report.md` (no-GPS photos, oversize refusals, duplicates,
   GPS photos with no camera direction, chainage summary, grouping
   list). Web-sized derivatives (max 1600 px) go to
   `site/assets-photos/`. Photographer is stamped per photo and per
   pin from `--photographer` (default PJM); a photo in a per-person
   subfolder takes that subfolder's code. Photos in a pin carry
   front/back/detail roles by shoot order only, never by compass.
   Nothing is classified or graded at intake.
2. **Classification** — the chapter classifies each pin through its
   interface (type + condition), Paul approves; the approved type
   codes are written onto the pins. Muse does not classify or grade.
3. **Assignment** — `scripts/assign_serials.py` (add `--dry-run`
   to preview) stamps serials in chainage order and updates the
   registry. Re-running it is safe: numbered pins are never
   touched.
4. **Viewer** — the pin popup title is the serial + type
   ("ITM-BN-014 — Bench"); unassigned pins show the type as
   before. No marker change (the condition-colour ring is
   unchanged).

Original photos never enter this repository — they live in the
shared Drive folder, and each pin carries that file's Drive ID.
Serials carry no personal data.

No real inventory photos have been processed yet. Test fixtures and
their proof outputs live in `photos-inbox/_test/` (see DESIGN.md,
photo pipeline section).

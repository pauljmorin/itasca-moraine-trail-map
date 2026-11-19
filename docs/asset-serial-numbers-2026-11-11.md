# Asset serial numbers — design note 2026-11-11

Paul's ask (chat, 2026-11-11): give every item in the asset inventory a
serial number — "a number that you can tell what it is. Like if it's a
bench or a particular sign or something."

This is a design note, not a build. No shipped file, data file, or the
live map was changed.

## 0. What exists today (verified 2026-11-11)

- **No real inventory exists yet.** `data/assets/` holds only a README
  placeholder; `site/data/assets.geojson` does not exist, and the
  viewer's "Asset pins" layer is `missingOk` / `emptyUntilData` — it
  quietly shows empty until the first real batch runs.
- The only pins ever built are the **test fixtures** in
  `photos-inbox/_test/` (`direction-test.jpg`, `kiosk-test.jpg`,
  `no-gps.jpg`). The test build output (`photos-inbox/_test/out/
  assets.geojson`) has 2 pins, both `type: "unclassified"`, condition
  null. Paul's nine real test photos in `photos-inbox/Paul Morin/`
  carry **no GPS** (zeroed template — see photo-protocol history), so
  none of them can enter the inventory as pins at all until the
  track-logger workflow produces located photos.
- The pipeline (`scripts/photo_pipeline.py`, `build` mode) writes one
  feature per GPS-carrying photo into `data/assets/assets.geojson`
  with properties: `photo`, `datetime`, `photographer`, `type`
  (`"unclassified"`), `condition` (null), `drive_id` (null),
  `derivative`, `direction_deg` / `direction_ref` /
  `direction_compass`. **There is no id or serial field anywhere
  today** — no `serial`, no `asset_id`, in the pipeline, the data,
  or the viewer (grep-verified).
- The viewer already renders asset pins: `assetPopup` shows the type
  as the title plus condition and date photographed; `assetMarker`
  draws a pin with a condition-colour ring (good green / fair amber /
  poor red). Nothing in the viewer needs to change shape for serials
  — the popup title is the place a serial goes (§7).
- Taxonomy as it stands (DESIGN.md, "Assets"): Carsonite posts,
  kiosks, signage, parking areas, bivouac campsites, "and whatever
  else the inventory discovers." Open taxonomy, `unclassified`
  bucket; nobody knows everything the chapter has until the
  inventory is taken. The photo protocol names the same things from
  the volunteer's side: "sign, post, kiosk, parking area."
- No existing identifier uses this pattern, so there is nothing to
  collide with: sections are `West-n` / `Chip-n`, mile markers are
  `MN-123.5` (state numbering, a separate layer from NCTA mile
  points), parcels carry county `parcel_id`s, chapter places carry
  their own `id`s. A serial namespace is free.

## 1. Proposed format

```
ITM-BN-014
│   │  └── sequence within the type (001, 002, …)
│   └── type code — two letters, mnemonic (BN = bench)
└── chapter prefix — ITM = Itasca Moraine
```

**One line: `ITM-<type>-<nnn>` — chapter prefix, two-letter type
code, zero-padded three-digit sequence per type.**

- Three digits per type is sized for the chapter: DESIGN.md expects
  hundreds of assets total; the most numerous type (Carsonite posts)
  is plausibly in the low hundreds. If a type ever passes 999 the
  format simply grows to four digits — nothing breaks.
- Uppercase letters, hyphens as separators, digits only in the
  sequence: short enough to say aloud and text, no characters that
  are easy to misread or mistype, and label-ready if printed labels
  ever happen (§5).
- The sequence is a **registry counter, not a spatial ordering**
  (§3): numbers are never reused and never renumbered, so gaps are
  normal and meaningless.

### Chapter prefix — the weighing

The wider project principle is that chapter is a data attribute,
never baked in, so the build can extend statewide one day. Two
honest readings of that principle for a serial:

- **Prefix in (recommended): `ITM-BN-014`.** A serial gets spoken,
  texted, written on tape on the back of a sign, and quoted in
  emails out of context. Out of context, `BN-014` is ambiguous the
  moment a second chapter adopts the scheme; `ITM-BN-014` never is.
  It also follows the project's own existing habit of scope prefixes
  on human-facing labels (`MN-123.5` mile markers). The data model
  still keeps `chapter` as a separate field on the pin record — the
  prefix is a namespace on the human key, not structure baked into
  the geometry. If the scheme extends statewide, each chapter takes
  its own prefix (ITM, LL, …) and the format stays uniform.
- **Prefix out: `BN-014`, chapter as a field only.** Shorter, and
  the purest reading of "chapter is a data attribute." Works fine as
  long as serials never leave chapter context — but they will
  (volunteer messages, chapter emails, a printed list at a social
  night), and then two chapters' `BN-014`s are two different benches.

Recommendation: keep the prefix. It is open question #1 for Paul
(§6) — the format works either way, and the choice is cheap to make
now and expensive to reverse later, because printed or quoted serials
can't be recalled.

## 2. Type-code table

Codes are two letters, mnemonic, uppercase. "Seeded" = named in
DESIGN.md, the photo protocol, or the tracker. "Proposed" = not yet
observed in any classified photo — add to the table when first found,
don't pre-assign numbers to them.

| Code | Type | Source |
|---|---|---|
| BN | Bench | Paul's example; proposed, not yet observed |
| CP | Carsonite post | Seeded (DESIGN.md) — the trail's standard marker post |
| KI | Kiosk | Seeded (DESIGN.md, photo protocol) |
| SG | Sign, any kind | Seeded (DESIGN.md, photo protocol, tracker: "Island Lake Sign") |
| PK | Parking area | Seeded (DESIGN.md, photo protocol) |
| CS | Campsite / bivouac site | Seeded (DESIGN.md: "bivouac campsites") |
| LT | Latrine | Seeded Nov 11, 2026 — first batch (Lake Erin campsite latrine); code approved by Paul with the batch |
| PO | Post, other (non-Carsonite) | Seeded in spirit (photo protocol: "post") |
| BR | Bridge | Proposed |
| PN | Puncheon | In use — 10 pins, reclassified from BW (boardwalk) Nov 19, 2026 (Paul) |
| SH | Shelter | Proposed (NCTA points carry a Shelter kind; the inventory may find them) |
| WT | Water source (pump / spring / faucet) | Proposed (NCTA points carry a Water kind) |
| UN | Unclassified | The bucket — a **type value, never a serial prefix** (§3) |

Notes on the table:

- **Signs are one code (SG), not split by subtype.** Subtype —
  regulatory, wayfinding, interpretive — goes in a `sign_kind` field
  on the pin record. Reasons: subtype is a classification judgment
  that can change on a second look, and splitting codes multiplies
  the counters and the surface for confusion. If Paul wants to tell
  a regulatory sign from a direction sign by the number alone, the
  split is a real alternative — open question #2.
- **A physical mile post is a Carsonite post (CP), not a sign.**
  The NCTA mile-marker layer (state numbers MN-123.5→MN-239) is
  separate data from the mile points; a photographed post carrying a
  mile number is an asset of type CP, with the mile in the pin's
  notes. Don't double-count the mile-marker layer as inventory.
- **A new type gets a code** when the classification pass first meets
  it: the classifier (Muse, then Paul's edit pass) proposes the
  two-letter code, Paul approves it, the code joins this table, and
  the registry opens a counter for it starting at 001. Codes are
  never recycled — if a type is later merged into another, its code
  retires with its numbers. The table itself lives in this note and
  in `data/assets/README.md` when the scheme is adopted, so the next
  classifier (human or model) works from the same list.
- **Parking areas are areas, not objects** — the pin marks the area
  (its access point / sign), and one parking area gets one serial
  even if it has several signs; the signs themselves are SG items.

## 3. Worked examples

**Real items.** There are none yet — no classified inventory exists.
The two worked examples below use the actual test fixtures, and are
labelled as such; the rest are illustrative, not real.

| Serial | What | Where | Condition | Status |
|---|---|---|---|---|
| ITM-KI-001 | Kiosk (fixture `kiosk-test.jpg`) | Test coords 47.140139, −95.208333 (synthesised, not a real place) | ungraded | **Illustrative** — the fixture is named "kiosk", so if it were a real classified photo this would be the first kiosk |
| — (no serial) | Fixture `direction-test.jpg` | Same test coords | ungraded | **Correctly unnumbered** — type unknown, still `unclassified`; see the assignment rule below |

Illustrative serials for the kinds of things the first real batch
will find (not real items):

| Serial | What |
|---|---|
| ITM-BN-014 | Bench, 14th bench registered |
| ITM-SG-007 | Sign, 7th sign — e.g. the Island Lake Sign, if it is photographed |
| ITM-CP-023 | Carsonite post, 23rd post |
| ITM-PK-002 | Parking area, 2nd parking area |
| ITM-CS-001 | Campsite, 1st campsite |

### Assignment rules

1. **A serial is assigned at classification, not at photo intake.**
   Intake creates a draft pin (identified by its existing photo slug
   — photographer + filename, already unique per batch). The
   classification pass (the chapter classifies through its interface,
   Paul approves) is what assigns the serial. Reason: the serial's
   type code has to be true forever (§4), and at intake the type is
   usually still `unclassified`.
2. **Unclassified pins carry no serial.** They keep the photo slug
   until they are classified. `UN` is a type value, never a serial
   prefix — no serial ever reads `ITM-UN-…`.
3. **Ordering within a classification batch: chainage order,
   west→east.** When a batch is classified, sort its pins by distance
   along the trail from the west end (`from_west_mi`, the project's
   existing convention) and assign the next numbers per type in that
   order. This costs nothing and buys a useful property for free:
   within each type, numbers roughly run west→east, so `BN-014` sits
   roughly east of `BN-003`. Pins that can't be snapped to the trail
   (off-corridor, or no chainage yet) are numbered after the snapped
   ones in discovery order. This needs chainage on asset pins — see
   §7; the snap machinery already exists for chapter places.
4. **A new item found between two numbered ones just takes the next
   number.** No sparse numbering (steps of 10 buy nothing at this
   scale and complicate the counter), no suffixes (`014A`), no
   renumbering. The sequence is a registry counter; spatial order
   within a type is approximate by construction, not exact.
5. **Never reuse, never renumber.** If an asset is removed, lost, or
   turns out to be a duplicate photo of an already-numbered item, its
   serial retires with it (the registry marks it retired, with a
   note). If the same physical item is photographed twice, the second
   photo attaches to the existing pin and serial — it does not mint
   a new one. Duplicate detection is the pipeline's existing
   datetime+coordinate check, extended by the classifier's eye.
6. **Reclassification after publication does not change the serial.**
   The `type` field is corrected, the serial stands, and the
   discrepancy is noted in the registry (e.g. "ITM-BN-014 re-read as
   a sign, 2026-11-20; serial retained"). This is standard registry
   practice — accession numbers don't change when attribution does —
   and it is the price of the rule in §4 that the code tells you what
   the thing is: the code is true *at assignment*, and the registry
   is the record of the rare exceptions. Before first publication on
   the map, a wrong code *can* be corrected with the serial (nothing
   public has quoted it yet).
7. **A serial can be RESERVED for an item not yet classified.** The
   registry holds the number in the type's `issued` map with a
   `reserved` marker (photo, chainage, reason); `assign_serials.py`
   skips reserved numbers when minting, so the sequence has no gap
   and no other item takes the number. Precedent (Nov 11, 2026):
   ITM-SG-007 is reserved for the unreadable paper notice at
   chainage 58.59 — it mints only after a close re-photo reads it.

**Build merges, never rewrites (Nov 11, 2026).** `photo_pipeline.py
build` carries over every pin already in `data/assets/assets.geojson`
untouched (type, condition, serial, attached photos) and only
creates pins for photos not yet known. A photo is known if it is a
pin's primary photo or listed in a pin's `photos` array, so
re-running a batch whose duplicates were collapsed cannot resurrect
them as separate pins. This is what makes the serials durable across
batches: the next batch's build cannot wipe this batch's
classification.

## 4. What the number must NOT encode

The serial is a stable registry key: type + sequence. Everything
else lives in the pin record, where it can change without breaking
references:

| Fact | Lives in | Why not in the serial |
|---|---|---|
| Condition (good / fair / poor) | `condition` field (already drives the pin's ring colour) | Changes with every visit; a re-graded bench must keep its number |
| Adopter section | Derived from the pin's chainage, not stored in the serial | Sections are re-drawn; a bench doesn't move when West-9's boundary does |
| Precise location | Geometry (lat/lon); chainage is derived | GPS gets refined; a moved pin keeps its number |
| Photographer / date photographed | `photographer`, `datetime` fields | Several people may photograph the same item over the years |
| Drive file ID / derivative | `drive_id`, `derivative` fields | The photo is evidence about the item, not the item |
| Sign subtype | `sign_kind` field (if SG) | A judgment that can change on re-read (§2) |

The test for any proposed addition to the format: *would this fact
still be true in five years?* Type and existence are the only facts
that qualify.

## 5. Field use

- **In a message:** "The bench on West-9, **BN-014**, has a cracked
  slat" — or with the prefix, "ITM-BN-014". Anyone with the map (or
  the registry list) finds it in seconds: search the serial, or open
  the section and read the pin. The serial is the thing you quote
  when the photo, the location description, and the section name are
  all too vague — which on a 76-mile trail is most of the time.
- **On the map:** the pin popup's title becomes the serial (e.g.
  "ITM-BN-014 — Bench"), with type, condition, and date below it
  as today (§7). The marker itself doesn't change — the
  condition-colour ring already says how the item is doing at a
  glance.
- **In the chapter's own lists:** a maintenance list sorted by serial
  reads as a walk of the trail within each type (because of the
  chainage-order assignment, §3); a "needs work" list quotes serials
  and the adopter of that section can find their item without a map
  in front of them.
- **Printed labels / QR codes — future, not a build now.** The format
  is deliberately label-ready: short, uppercase, hyphenated, no
  characters that smudge into each other. If the chapter ever labels
  items in the field, a label would carry the serial (and later, a QR
  code encoding a link to the pin — the viewer has no per-pin URLs
  today, so that is a separate, later decision). Nothing in this
  design depends on labels happening.

## 6. Open questions for Paul

1. **Chapter prefix in the serial — `ITM-BN-014`, or bare `BN-014`?**
   Recommendation: keep the prefix (§1). Cheap now, expensive to
   reverse once serials are quoted.
2. **Signs: one code (SG + a `sign_kind` field), or split codes?**
   Recommendation: one code (§2). The split is only worth it if he
   wants to tell a regulatory sign from a direction sign by the
   number alone.
3. **First full inventory pass: number in chainage order
   (west→east) within each batch?** Recommendation: yes (§3) — free,
   and it makes the numbers read as a walk of the trail. The
   alternative is plain discovery order.
4. **Assignment stays editorial — the chapter classifies, serials are
   proposed in chainage order, Paul approves per batch?** That is the
   standing rule ("editing runs through Paul"); confirm it holds for
   serials too, since a serial once published can never be taken back.

## 7. What changes when this is adopted (build outline only)

1. **Registry — new file `data/assets/registry.json`.** The source of
   truth for "next number" per type code: `{ "BN": {"next": 15,
   "issued": {"ITM-BN-001": {"photo": …, "drive_id": …}, …},
   "retired": […]}, … }` plus the type-code table. One file, in the
   repo, versioned like everything else. The registry is what makes
   "never reuse" enforceable — the counter lives in exactly one
   place.
2. **Pipeline — `scripts/photo_pipeline.py`.** Add a `serial` property
   to pin features (null until assigned). Add an assign step (a small
   script, e.g. `scripts/assign_serials.py`, or a pipeline mode) that
   reads the registry + `assets.geojson`, stamps the next numbers in
   chainage order per §3, and writes the registry back. `build` itself
   must **not** auto-assign — assignment is editorial (§3 rule 1,
   §6 question 4). Also add `chainage_mi` + nearest section to pins
   (reusing the snap machinery `build_gazetteer.py` already uses for
   chapter places) — needed for the ordering rule and for the popup's
   "on West-9" context.
3. **Pin schema — one field.** `serial` (string, null when
   unassigned). Everything else already exists; add `sign_kind`
   (string, null unless type SG) at the same time if question #2 goes
   to one code.
4. **Viewer — `site/app.js`, small.** `assetPopup` title becomes
   serial + type ("ITM-BN-014 — Bench"); unassigned pins keep showing
   the type as today. No marker change. Optional later: make serials
   searchable (gazetteer `search_text` gains serials) — not needed
   for the first version, since the pins are found by section.
5. **Docs.** Update DESIGN.md's asset section, `data/assets/
   README.md` (registry + code table live there), and the photo
   protocol (one line for volunteers: "quote the serial when you
   report a problem with something — it's on the pin's popup").
6. **No change** to photo storage, the Drive folder, the derivative
   rule, or the privacy posture: serials carry no personal data
   (photographer stays a field on the pin record as today, not in
   the serial).

## 8. Carsonite-post condition scheme (Paul, Nov 11, 2026)

Paul's rule, adopted Nov 11: a Carsonite post's condition is
**fitness for purpose, not cosmetics**. Three values, CP only (other
types keep good / fair / poor for now):

- **new** — like new: straight, decals legible.
- **worn** — shows wear (lean, faded or pale decals, lichen) but
  still doing its job: standing, blaze readable, at least one
  legible decal face. Worn is acceptable; it is not a failure.
- **replace** — not doing its job: on the ground, broken,
  unreadable, stickers peeling off.

Applied Nov 11 to the 18 CP pins of batch 1: **11 new, 7 worn,
0 replace** — no dead Carsonite in the batch. The four pins the
classifier had called "fair" all land as worn (CP-003, CP-005,
CP-007, CP-017: leans of 10–15°, worn decals, still standing and
readable). CP-003 is the closest to the line (15° lean + lower
decal worn blank; graded worn — the blaze reads). CP-008's decal
wear could not be judged from the distance photo; its pin carries
a note to re-photo for a final grade. The one failing item in
batch 1 remains ITM-PO-001 (leaning ~30°, split base) — a PO,
not a Carsonite.

Viewer: `site/app.js` `CONDITION_RINGS` extended Nov 11 so the
rings follow the same colours (new green / worn amber / replace
red). The popup and hover chip show the raw value ("Worn
condition").

# Design record — Itasca Moraine Chapter trail map

This document records the design as agreed with the chapter. It is the
reference for anyone who takes the project over: the repository is
deliberately built to be transferred (see README.md, "Portable by
design").

## Data model

### Official line (reference geometry)

The official depiction of the North Country National Scenic Trail,
published by the North Country Trail Association on behalf of the
National Park Service as a public ArcGIS feature service
(see `SOURCES.md`). Downloaded in full by
`scripts/pull_official_line.py`, clipped to the chapter working
extent in `config/chapter.json`, stored at
`data/segments/official-line-chapter-extent.geojson`.

First-pass clip method: bounding-box filter (a feature is retained if
any of its segments intersects the extent box); retained features keep
their full geometry and all service attributes. The service
distinguishes off-road trail from on-road sections and certified
trail from connector routes (attributes `trail_stat`, `trail_type`,
`cert_stat`, among others) — those attributes are kept, never
filtered out.

### Segments

The chapter's unit of management. A segment is a stretch of the
official line between two boundary points, carrying at minimum:

- `chapter` — chapter id (segments of several chapters can coexist)
- `name` / local name where the chapter has one
- `adopter` — who maintains it, or null
- `status` — e.g. adopted / unadopted, plus maintenance state
  (last mowed, last cleared) as the chapter starts recording it

Segment boundaries come from the chapter's adopter-boundary KMZ
(Google Earth format), converted to GeoJSON and overlaid on the
official line. **Unadopted gaps are segments in their own right**,
shown visibly unclaimed: the map is a recruiting tool — the chapter's
proven pattern is that people adopt what is near them, and a visible
gap list with lengths is the digital version of the paper map at a
chapter social night. Printability of the map for events is a design
plus, kept in mind for the site.

### Assets (the inventory)

The chapter currently has **no inventory** of its physical assets:
Carsonite posts, kiosks, signage, parking areas, bivouac campsites,
and whatever else the inventory discovers. Assets are points derived
from photographs (pipeline below), each carrying:

- location (from photo GPS)
- `type` — from an **open taxonomy**: known types plus an
  `unclassified` bucket. Nobody knows everything the chapter has
  until the inventory is taken, so the taxonomy grows from what is
  found; it is never a closed list forced on the data
- `condition` — a rough grade read from the photo (see open
  decisions)
- date/time photographed, photo reference, photographer
- `public_worthy` flag — the best photos double as promotion material

### Parcels

Minnesota's compiled county parcel data (MnGeo / Minnesota
Geospatial Commons; see `SOURCES.md`), clipped to a **corridor**:
every parcel the trail crosses, plus the ring of parcels adjoining
those. This answers "whose land does the trail cross, segment by
segment?"

**Owner names are published (revised 2026-11-10).** The parcel
owner names are published county public records (~921 of the 1,041
corridor parcels carry a published owner), and the chapter ruled
on 2026-11-10 that they go ON the map, with the owner's mailing
address from the same record. This reverses the original
working-view-only rule below. Parcel data is a snapshot; refresh
roughly annually.

### Access

Getting to a segment is often the real problem: a segment reachable
from only one end can mean hauling a mower its full length. Access is
therefore a first-class layer, not a footnote:

- forest roads (public data, e.g. MN DNR layers)
- side-by-side / UTV trails
- other hiking trails
- **private roads — drawn, but always labeled** "Private — informal
  access, ask first." A drawn line must never look like a right.

Derived output, computed in the same pass as the segment overlay:
**practical access points per segment** — both ends plus every
mid-segment road/trail crossing or near-approach, described in plain
language. Access points that exist in local knowledge but in no
public dataset get pinned by the photo pipeline and marked as
chapter-sourced.

## Privacy and branding rules (hard rules)

1. Landowner names: **published on the map** (revised 2026-11-10 —
   they are published county public records; see the Parcels
   section). Taxpayer fields are not carried.
2. Adopter names: never public as names. The public build shows
   positional placeholders ("Test adopter 1", "Test adopter 2", …)
   assigned by the site-data build; real adopter names live only
   in the working data.
3. Private access is labeled private/informal wherever drawn.
4. The map is presented as an **Itasca Moraine Chapter** project of
   the North Country Trail Association. It is never presented as the
   national NCTA or as the National Park Service. No permission is
   required to publish it; the branding discipline is the rule.
5. Data sources are credited on the map and in `SOURCES.md`.
6. The project consumes only the public web services NCTA already
   publishes; it requires nothing from NCTA's GIS staff.

## Photo-inventory pipeline (design)

Goal: a volunteer's total effort is taking a photograph.

1. **Drop.** Photographers (initially 4–5 people) drop original
   photos into a shared folder (mirrored at `photos-inbox/`).
   Originals only — **never via text message**, which strips location.
2. **Pre-flight protocol** (before anyone's first outing, especially
   for less technical volunteers):
   - take one test photo at home (mailbox, driveway)
   - the pipeline checks it automatically for GPS coordinates
   - the coordinator keeps a simple roster: green = tagging works,
     red = it doesn't
   - reds get a short fix-it card for their phone type (the few taps
     that turn camera location on) and retest until green
   - nobody goes out until their phone passes
3. **Extract.** A script reads each photo's EXIF GPS coordinates and
   date/time; each photo becomes a draft asset pin at those
   coordinates with the photo attached. Phone GPS accuracy (a few
   metres) is sufficient for asset-finding purposes.
4. **Classify.** The coordinator's AI assistant classifies each photo
   (asset type, rough condition) from the image itself; a human
   spot-checks rather than typing records. Unclassifiable photos go
   to the `unclassified` bucket for human naming — this is how the
   taxonomy grows.
5. **Ongoing checks.** Every later batch is auto-scanned the same
   day: photos without GPS are flagged back to the photographer
   while they still remember where they stood; pins landing far off
   the trail corridor are flagged as suspect.

**Implemented (2026-11-10):** `scripts/photo_pipeline.py` provides
the two modes above — `check` (steps 2 and 5: per-photo EXIF GPS /
datetime report plus a green/red per-photographer summary; standard
library only, no third-party packages) and `build` (step 3: writes
`data/assets/assets.geojson` with one Point per GPS-carrying photo,
`type: "unclassified"`, `condition: null`, `drive_id: null` until
Drive ingest; writes web derivatives ≤1600 px to
`site/assets-photos/`; enforces the 5 MB per-file refusal from the
storage rule; writes `data/assets/flags-report.md` covering no-GPS
photos, oversize refusals and duplicate datetime+coordinate pairs).
The volunteer-facing protocol card is `docs/photo-protocol.md`.
**Fixture proof (2026-11-10):** synthetic fixtures in
`photos-inbox/_test/` (one JPEG with hand-built EXIF GPS + datetime,
one JPEG with no GPS) — `check` scanned 2, found 1 with GPS at the
exact synthesized coordinates (47.140139, −95.208333), summary
"GREEN (partial)"; `build` wrote 1 pin, excluded the no-GPS photo
to the flags report, and produced the derivative; a separate
4000 px GPS fixture proved the derivative resize to 1600 px.
**Camera direction (2026-11-11):** the pipeline also reads EXIF
GPS ImgDirection (the bearing the camera was facing) when a photo
carries a valid one: `check` adds a `Dir:` column, and pins gain
`direction_deg` / `direction_ref` / `direction_compass` properties
(null when absent); pins with GPS but no direction are noted in
the flags report (informational). Validity is strict — the north
reference must be 'T' or 'M', the value in [0, 360), and the
position must not itself be the zeroed GPS template a phone
writes when it never got a fix (proved against a real volunteer's
original: template ImgDirection 0.0 with an empty ref reads as
absent, while a genuine 0.0 with ref 'T' reads as facing north).
Fixture: `photos-inbox/_test/Test Person/direction-test.jpg`
(GPS + ImgDirection 42.5, ref 'T' → pin carries 42.5 / 'T' /
'NE').

## Views

- **Chapter working view** — everything: segments, adopters,
  parcels with landowner names, assets, access incl. labeled
  private roads, condition, gaps.
- **Volunteer view** — segments, adopters, access points, asset and
  maintenance status; no parcel ownership detail beyond land class.
- **Public view** — promotion: featured trailheads, loops and access
  trails (e.g. from Park Rapids) as curated "start here" entries for
  newcomers, with parking, distance, and inventory photos; land shown
  as class only; no operational detail.

The map is a home/meeting tool: there is effectively no data
coverage along much of the trail, so no field/offline functionality
is designed in. Volunteer self-input is a **concept only** at this
stage — not implemented; editing runs through the coordinator.

## Extensibility

Chapter is a data attribute (`config/chapter.json`, and a `chapter`
field on records), so other chapters can join the same dataset and
site. Statewide and whole-trail growth is a data problem, not a
rebuild. Governance for multi-chapter data (who approves another
chapter's records) is deliberately not decided yet.

## Open decisions

1. **Condition grading** — proposed: capture location + a rough
   condition grade (e.g. good / fair / needs work), since the
   classification pass sees the asset anyway. Awaiting chapter
   confirmation.
2. **KMZ segment overlay** — pending the chapter's adopter-boundary
   KMZ file. The overlay pass produces the first real report:
   segment fit against the official line, the unadopted gap list
   with lengths, and access points per segment.
3. **Access display on private land** — decided: private roads are
   drawn and labeled private/informal (chapter ruling, 2026-11-10).
4. **Per-county parcel availability** — CONFIRMED 2026-11-10 (see
   `data/parcels/county-coverage.md`): the trail crosses Hubbard,
   Cass, Becker and Clearwater counties; Becker, Cass and
   Clearwater are in the state compilation, Hubbard is not and was
   pulled from the county's own open-data service. The corridor
   file is built. Two caveats ride along: a handful of Hicks Lake /
   Itasca State Park shoreline points sit in source-data gaps (no
   parcel polygon in either source), and two very large Clearwater-
   compiled polygons spill across the county line from Hubbard —
   treat county attribution near the line as approximate.
5. **Where the public map lives** — hosting/linkage (chapter page,
   social channels) undecided; the site will be static and movable.

## Standing rule — photo storage split (added Nov 10, 2026, Paul's question)

GitHub is the brain, not the warehouse. Original photos NEVER enter the repo:
- **Originals** live in the shared Drive folder (the photographers' drop point); the pin record carries the Drive file ID, so the full-resolution original is one click behind every displayed image.
- **GitHub** holds the map data (text, kilobytes) and, per displayed photo, one web-sized derivative (~1600px, roughly a tenth of a phone original).
- GitHub's shape: 100 MB hard limit per file; repos should stay under ~1–5 GB; a published Pages site caps at 1 GB. Web derivatives keep the site far inside that at chapter scale (hundreds of assets).
- The photo pipeline enforces a size check and refuses oversize files before commit.
- Escape hatch if the project ever outgrows Drive (statewide, thousands of photos): object storage (e.g. Cloudflare R2-class) with the site pointed at it — an option, never a foundation, since it adds an account to own.

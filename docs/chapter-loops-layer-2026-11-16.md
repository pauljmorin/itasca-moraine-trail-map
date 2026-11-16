# Chapter loops layer — 2026-11-16

Paul approved adding the Waboose Lake Loop and Lake Erin Loop to the
viewer. One new layer, "Chapter loops", ON by default. No deploy, no
commit, no push.

## What changed

### New data — `site/data/chapter-loops.geojson` (2 features)

One combined file, one feature per loop (the per-part breakdown stays in
the source files of record, `data/loops/`):

- **Waboose Lake Loop** — LineString, 203 pts, `length_mi: 3.64`.
  Source: OpenStreetMap (ways 846251459 + 846251460; east side is the
  shared NCT tread, OSM way 846251458). ODbL.
- **Lake Erin Loop** — LineString, 229 pts, `length_mi: 0.619`.
  Source: USDA Forest Service, National Forest System Trails
  (TrailNFS_Publish, trail LAKE ERIN HIKING no. 34914). Public domain.

Both lines keep their trailhead / parking-area gaps exactly as pulled —
no tread invented. Properties on each feature carry the source, the
length note, and the gap caveat; the popup shows name, length, source,
and the gap note.

### Viewer — `site/app.js` (3 spots, all loops-only)

- **Layer def, lines 4298–4336** (after Adopted sections, before Adoption
  segment ends — renumbered from 4237–4283 by the motorized addition
  below): `id: "loops"`, label "Chapter loops", group "The trail",
  `onByDefault: true`, file `data/chapter-loops.geojson`. Style: solid
  teal `#0f766e`, weight 3, opacity 0.9 — chosen to read apart from the
  NCT green (`#1a9850`) and the adopted-section amber (`#e08214`), and
  unlike the dashed-red NCT reroutes. Popup via the same `bindPop` +
  `kvTable` pattern as the reroutes def. Lines, so no spiderfy wiring.
  The panel builds its checkboxes generically from the defs
  (`LAYERS.forEach`), so the toggle appears under "The trail" with no
  panel code change.
- **`assertDrawOrder`, lines ~6276–6295** (renumbered from ~6162–6171
  by the motorized addition below): added `"loops"` to the stack
  list directly after `"stretches"`, with a comment line. This is
  required, not cosmetic: without it the listed layers (trail core,
  adopted sections) would be brought to front over the loop, hiding
  the teal on the shared NCT tread on Waboose's east side. With it
  the loop draws over the trail and the adopted sections and reads
  whole.
- **Legend, line 6349** (renumbered from 6232 by the motorized
  addition below): `Chapter loop — Waboose Lake / Lake Erin`
  row under "Chapter sections" (the legend is hand-built, not
  generated from the defs).

### Attribution — `site/data-sources.html`

New "Chapter loops" subsection under Chapter data (after Chainage
points): one line crediting OpenStreetMap contributors (ODbL) for the
Waboose line and the USDA Forest Service (TrailNFS_Publish) for the
Lake Erin line, with the pull date (November 16, 2026). Footer
as-of date moved November 13 → November 16, 2026.

## Data verification (rebuilt from source, not copied blind)

The staged files in `data/loops/` were intermittently unreadable from
this session (directory listings showed them, but `open`/`cat`/`cp`
returned ENOENT for minutes at a time — cross-session filesystem
sync lag for files the parent agent had just written; `ls`/`stat`
sometimes agreed, sometimes not). Rather than fight it, I re-fetched
both lines from their sources and rebuilt the combined file:

- OSM API bbox fetch (`api.openstreetmap.org/api/0.6/map?bbox=
  -94.90,47.02,-94.76,47.09`) — ways 846251459 (59 pts), 846251460
  (129 pts), NCT way 846251458 (224 pts). Joined loop: **203 pts,
  3.64 mi, 35 m end gap**; parts 0.94 + 2.34 + 0.37 mi — exact match
  to the staged file's numbers.
- USFS TrailNFS query (EDW_TrailNFSPublish_01/MapServer/0,
  `TRAIL_NAME LIKE '%ERIN%'` in the Lake Erin envelope) — 1 feature,
  **229 pts, 0.619 GIS miles** — exact match to the staged file.

`site/data/chapter-loops.geojson` was written from these fresh pulls
and read back: valid JSON, 2 LineString features, 203 + 229 pts.

## Static checks (all done Nov 16, no live browser)

- `node --check site/app.js` — PASS (final state, after all three edits).
- `python3 json.load` on `site/data/chapter-loops.geojson` — valid,
  2 features, names "Waboose Lake Loop" / "Lake Erin Loop".
- Def references `data/chapter-loops.geojson`; file exists at that path.
- Spiderfy untouched: `registerSpiderfyPin` still 7 occurrences
  (6 layer call sites + the definition), `spiderfyPins` 10,
  `onPointClick` 2 — same counts as in
  `docs/spiderfy-generalization-2026-11-16.md`. My loops edits sit at
  4298–4336, ~6276–6295 and 6349 (current numbering, after the
  motorized addition below); the spiderfy core (~2360–2484) and
  teardown (~3081–3100) were not edited — they sit before the
  insertion points, so their line numbers are unchanged. The layer
  wiring (~4766–5484 in the original numbering, ~4944–5662 now)
  was renumbered only, not edited. Working-tree `git diff` still
  shows the spiderfy agent's 17 hunks plus my loops hunks; nothing
  was reverted.
- `git status`: `M site/app.js`, `M site/data-sources.html`,
  `?? site/data/chapter-loops.geojson`. No commit, no push, no deploy.

## Still needs a live-browser check (not done here)

1. Serve the working tree (or deploy — NOT done by this change),
   load the site, confirm the "Chapter loops" toggle is ON under
   "The trail" and both lines draw.
2. Click each loop: popup shows its name, length (3.64 mi / 0.619 mi),
   source, and the gap note.
3. Zoom to Waboose's east side: the teal loop reads continuously
   over the NCT green / adopted amber where the tread is shared.
4. Legend: the "Chapter loop" row is present under Chapter sections.
5. Toggle the layer off and on; turn it off and reload with
   `#layers=...` — the shareable-view hash picks it up (generic
   over defs, but unproven for a new id).

## Deliberately NOT done (follow-ups)

- **GeoPDF export**: `site/export.js` (file map ~line 83,
  `RENDER_ORDER` ~line 102, render `case` ~line 511,
  `LEGEND_ROWS` / `LEGEND_ORDER` ~lines 109–140) and
  `scripts/export_geopdf.py` (`LAYERS` ~line 114,
  `BOOK_LAYERS` ~line 1288) each carry their own explicit layer
  lists. The loops are in neither, so a downloaded GeoPDF or a
  segment book will not include them until those lists gain a
  `loops` entry (teal `#0f766e`, solid, ON like the viewer).
  Left out on purpose: the export flow's live click-through is
  still owed, and this task was the viewer layer.
- **Trailhead gaps**: still open (35 m at Waboose, ~150 m at Lake
  Erin). A chapter GPS walk could close them exactly; nothing was
  invented here.

## Motorized trails — added the same day (same session)

Paul's follow-up the same morning: add the DNR motorized trails as a
second new layer group. No deploy, no commit, no push.

### Data — copied, not re-pulled

Two files, copied from `data/motorized/` (pulled 2026-11-16 by
`scripts/pull-motorized-chapter.py` from the Minnesota DNR OHV +
snowmobile FeatureServers, clipped to the chapter working extent
lon -95.6..-94.3, lat 46.7..47.35) into `site/data/` — two files, one
per layer, matching the buildout viewer's naming:

- `site/data/motorized-atv.geojson` — 1,238 LineString features,
  408.02 GIS miles, 8 systems: Forest Riders (206 segs, 112.5 mi),
  Round River Drive (280, 84.7), Martineau (260, 78.8), Huntersville
  (330, 77.5), Schoolcraft (78, 22.9), Smoky Hills (55, 22.9),
  Spider Lake (17, 5.9), Soo Line North: Cass (12, 4.5). Source
  service: `trans_ohv_trails_mn/FeatureServer/0`.
- `site/data/motorized-snow.geojson` — 17 features (15 MultiLineString
  + 2 LineString), 895.72 GIS miles, 12 systems: Naytahwaush
  Nightriders, Cass County, Clearwater Trail Blazer, Forest Rider,
  North Country, Wadena, Waubun Hardwood Trailblazers, Wolf Pack,
  Otter Trail Riders, Northwoods Trail Riders, Ideal Sno Pro, Nevis
  Wilder. Source service: `trans_snowmobile_trails_mn/FeatureServer/0`.

Read back with `python3 json.load`: both parse; counts and metadata
miles match the source files exactly. The source files in
`data/motorized/` stay the record; the `site/data/` copies are the
published ones. (Unlike the loops files, these read first try —
no sync lag this time.)

### Viewer — `site/app.js` (5 spots, motorized-only)

- **Popup helpers, lines ~4077–4137** (just before `var LAYERS`,
  now at line 4138): `atvVehicles` (4090), `atvPopup` (4098),
  `snowPopup` (4118). They mirror the buildout viewer's `atvPopup` /
  `snowPopup` rows (`site/buildout/buildout.js` ~824–878), read off
  the raw DNR field names (the buildout normalizes at build time;
  here the site files keep the raw properties). Vehicles wording is
  the buildout's: ATV-I / ATV-II / OHM / ORV. Notes use the main
  viewer's `pop-note` class — the buildout's `warn` / `drawn-note`
  classes do not exist in `site/style.css`.
- **Layer defs, lines 4337–4362 (ATV) and 4363–4396 (snow)**, right
  after the loops def: `id: "atv"` / `"snow"`, labels "ATV trails" /
  "Snowmobile trails", group "Other trails", `onByDefault: false`
  (lazy), files `data/motorized-atv.geojson` /
  `data/motorized-snow.geojson`. Styles match the buildout exactly:
  ATV purple `#762a83`, snow icy blue `#67a9cf`, weight 3,
  opacity 0.85.
- **`PANEL_GROUPS`, line 5858**: `"Other trails"` inserted second,
  right after `"The trail"`. Not added to `GROUP_PULLDOWNS`, so the
  two toggles show directly under the heading (not collapsed).
- **`assertDrawOrder`, lines ~6276–6295**: `"atv", "snow"` inserted
  after `"nctasheets"`, before `"trail-minnesota"` — motorized lines
  draw under the NCT tread and adopted sections, above roads and
  sheet outlines. Comment updated.
- **Legend, lines 6386–6388**: "Other trails" heading + purple
  "ATV trail (DNR)" and icy-blue "Snowmobile trail (DNR)" rows,
  after the Camping rows, before "The land".

### Attribution — `site/data-sources.html`

Two new h3 subsections at the end of "Around the trail" (after Matt's
NCTA map sheets): "ATV trails" and "Snowmobile trails", each with the
counts, the system list, the DNR source with a link to the
FeatureServer, and the pull date (November 16, 2026). The footer
as-of date was already November 16, 2026 (set for the loops) — no
change needed. Note: the older "Non-road access" section also names
OHV / snowmobile trails as part of a layer removed Nov 13 — that was
a different, basemap-duplicating access mashup; these two are
standalone DNR layers.

### One label the buildout gets wrong, fixed here

The snow service's `miles` field is the trail's PUBLISHED figure,
not the drawn segment's length — verified Nov 16 by measuring the
clipped geometry: e.g. 'Clearwater Trail Blazer Trails' carries
167.6 mi on a 1.5 mi drawn piece; 'Waubun Hardwood Trailblazers'
49.8 mi on 0.3 mi; field total 2,102.0 mi vs 895.72 GIS miles of
drawn line. The buildout labels this field "This segment", which
would misread here. The snow popup therefore says "Published
miles", with a pop-note that the drawn line is the portion inside
the chapter working extent. The ATV field DOES match the geometry
(spot checks 0.039 = 0.039; field total 409.8 vs 408.02 GIS miles),
so the ATV popup keeps "This segment". The buildout's Prospector
mileage-dispute note and the Taconite / C.J. Ramstad shared-use
notes have nothing to attach to — no Prospectors, Taconite, or
Ramstad system falls inside the chapter extent — so they are
omitted, not carried over.

### Static checks (motorized, all done Nov 16, no live browser)

- `node --check site/app.js` — PASS (final state, loops + motorized).
- `python3 json.load` on both `site/data/motorized-*.geojson` —
  valid; 1,238 + 17 features; metadata miles 408.02 / 895.72.
- Defs reference `data/motorized-atv.geojson` (line 4349) and
  `data/motorized-snow.geojson` (line 4375); both files exist.
- Spiderfy untouched: `registerSpiderfyPin` still 7; spiderfy core
  (~2360–2484) and teardown (~3081–3100) unchanged by either edit.
- `git status`: `M site/app.js`, `M site/data-sources.html`,
  `?? site/data/motorized-atv.geojson`,
  `?? site/data/motorized-snow.geojson`. No commit, no push, no deploy.

### Still needs a live-browser check (motorized)

1. "Other trails" group appears in the panel right after "The
   trail"; both toggles OFF on load.
2. Turn ATV on: purple lines draw under the NCT tread (e.g. Forest
   Riders around the trailhead); turn snow on: icy-blue lines.
3. Click an ATV segment: popup shows trail name, Vehicles (ATV-I /
   ATV-II / OHM / ORV as applicable), Surface, Funding, "This
   segment: X mi (DNR service)", DNR trail page link, source note.
4. Click a snowmobile segment: popup shows name, Maintained by,
   Owner, Trail no., "Published miles: X mi (DNR service)", and the
   extent note. (Stud restriction row appears only if a feature
   carries one — none of the 17 do.)
5. Toggle off/on; reload with `#layers=` hash — the new ids are
   picked up generically, unproven for these ids.

### Deliberately NOT done (motorized follow-ups)

- **GeoPDF export**: same as the loops — `site/export.js` and
  `scripts/export_geopdf.py` carry their own layer lists; neither
  has `atv` / `snow` entries yet, so motorized lines will not appear
  in downloaded GeoPDFs or segment books until those lists gain
  entries (purple `#762a83` / icy blue `#67a9cf`, OFF like the
  viewer).
- **The snow `miles` field**: left as the DNR published figure with
  the honest label; no per-segment geodesic miles were computed or
  added (that would be a new derived field, not source data).

---

## Nelson Lake Loop — added 2026-11-16 (same day, second pass)

Paul: "another loop is nelson lake" — then pinned it: "on the border
between west 9 and 10". That is the Nelson Lake Trail in Paul Bunyan
State Forest near Laporte. Its NCT junction (-94.84658, 47.15307)
sits 3.2 m from the West-9 / West-10 boundary point (-94.84655,
47.15305) in the chapter's own stretches file. Three other Nelson
Lakes in Minnesota were ruled out (Pillager/Cass, Lake Park/Becker,
Hines/Beltrami). Trailhead 47.161752, -94.841417 (Gulch Lake
Campground, connects directly to the NCT).

### Data — appended to `site/data/chapter-loops.geojson` (now 6 features)

Source file of record: `data/loops/nelson-lake-loop.geojson`
(4 features, staged earlier the same day). Source: OpenStreetMap
ways 505705378 + 889604647 + 889604649 (`name=Nelson Lake Trail`,
`highway=footway`) and 508873979 (`name=Lake Twentyone Trail`,
`highway=footway`), fetched 2026-11-16 via api.openstreetmap.org.
ODbL — covered by the OSM attribution line already on the
data-sources page.

- **Nelson Lake Trail** — 3 features (one per OSM way), each
  carrying `length_mi: 1.25` (the loop total across the three
  ways: 0.570 + 0.510 + 0.166), `source: OpenStreetMap (ODbL)`,
  `osm_way_id`, a `length_note` stating the total, a `source_note`
  naming the way, and the gap note. The popup therefore shows the
  loop length (1.25 mi) whichever segment is clicked — the same
  pattern as Waboose, where `length_mi` is the loop total.
- **Lake Twentyone Trail** — 1 feature, `length_mi: 1.01`,
  the connector from the loop to Lake Twenty-one.

Total assembled system: 2.26 mi against a published 2.4 mi loop
(AllTrails); the difference is the campground spur, not mapped as
tread.

### Gap — left open on purpose

~140 m gap on the north-east side of the loop, across the Gulch
Lake Campground area, between the end of way 505705378 and the
start of way 889604647. The Lake Twentyone Trail's end sits 47 m
from the same junction. No tread invented to close either gap.
Same treatment as Waboose's 35 m trailhead gap.

### Viewer changes (this pass)

- `loops` def comment + title updated: "Three chapter-managed
  loops off the NCT: Waboose Lake …, Lake Erin … and Nelson Lake
  (Paul Bunyan State Forest, West-9 / West-10 boundary)".
- Legend row now reads "Chapter loop — Waboose Lake / Lake Erin /
  Nelson Lake".
- Data-sources "Chapter loops" section rewritten for three loops
  plus the Lake Twentyone connector, with the 140 m campground
  gap stated.
- No draw-order or style change: the teal `#0f766e` loop style
  and the over-adopted-sections slot already cover the new
  features. Top-level file `properties.note` updated to three
  loops.

### Checks passed

- `python3 json.load` on `site/data/chapter-loops.geojson` — valid;
  6 features; every feature carries `name`, `length_mi`, `source`,
  `gap_note` (the three fields the loops popup reads).
- Junction 3.2 m from the West-9/10 boundary (measured in the
  staging pass); total 2.26 mi within 6% of the published 2.4 mi.
- `node --check site/app.js` — PASS (see the corridor / Nelson /
  SHT note, `docs/layers-corridor-nelson-sht-2026-11-16.md`).

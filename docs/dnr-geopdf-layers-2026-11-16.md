# DNR GeoPDF layers — verification note, Nov 16, 2026

Paul asked for the Minnesota DNR's GeoPDF maps as layers in the ITM viewer,
the same way the NCTA map sheets were done. Ten sheets are wired and ready
to deploy (no deploy/commit/push done in this pass, per the brief).

## What was wired (10 layers, all OFF by default, LAZY)

Group "The trail", subgroup "DNR maps" (collapsible sub-heading beside the
NCTA sheets). Each layer is one def (`id: "dnr-<slug>"`) with a shared build
function `buildDnrGeopdf` that mirrors the NCTA-sheets build exactly:
3-corner affine `L.imageOverlay.rotated` (TL/TR/BL), opacity 0.92, image
registered in `sheetImages` so the zoom ≥ 11 gate covers DNR sheets the same
way it covers NCTA sheets, dashed blue outline + name label visible below
zoom 11, popup with the map title, date and a DNR download link. Draw order:
directly after `nctasheets`, before `atv`. Legend: one row per sheet under a
"DNR maps" heading. Attribution: a "DNR maps (GeoPDF)" section in
`site/data-sources.html`, one paragraph per sheet (title, date, URL, pull
date Nov 16, 2026, trail km inside the frame).

| Layer id | Map (title as printed) | Date | Trail inside frame | Image |
|---|---|---|---|---|
| `dnr-waboose` | Paul Bunyan and Badoura State Forests Map | 2017-06-14 | 79.68 km | 1552×2400, 817 KB |
| `dnr-burntside-bear-island` | Burntside and Bear Island State Forests Public Recreation Map | 2019-07-02 | 106.31 km | 2400×1552, 1005 KB |
| `dnr-grand-portage-sf` | Grand Portage State Forest Public Geo PDF Recreation Map | 2020-11-20 | 32.26 km | 1552×2400, 584 KB |
| `dnr-remer` | Golden Anniversary and Remer State Forests Geo Referenced Public Recreation Map (Remer panel) | 2019-03-21 | 14.68 km | 1467×1354, 361 KB |
| `dnr-white-earth` | White Earth State Forest Geo Reference Recreation Map | 2019-03-21 | 43.32 km | 2400×1842, 1077 KB |
| `dnr-itasca-summer` | Itasca Summer GEO | 2026-06-23 | 26.42 km | 2266×1573, 597 KB |
| `dnr-maplewood-summer` | Maplewood Summer GEO | 2025-08-11 | 15.80 km | 1540×2400, 618 KB |
| `dnr-maplewood-winter` | Maplewood Winter GEO | 2025-11-24 | 15.72 km | 1550×2400, 555 KB |
| `dnr-david-dill-taconite` | David Dill Taconite GEO | 2023-04-11 | 60.68 km | 2400×1530, 508 KB |
| `dnr-lake-vermilion-soudan` | Lake Vermilion-Soudan Underground Mine GEO | 2026-06-24 | 9.68 km | 2400×1519, 537 KB |

Files: source GeoPDFs in `data/geopdf/` (repo, not `site/`); viewer images in
`site/data/dnr-geopdf/<slug>.jpg` (6.5 MB total); one GeoJSON per map in
`site/data/dnr-<slug>.geojson` (one feature, ring BL,BR,TR,TL in [lon,lat],
closed, properties title/short/note/image/source/url/date/viewport).
Build script: `working/dnr-geopdf/build_dnr_geopdf.py` (re-runnable;
re-render is deterministic — re-ran twice, identical quads and sizes).
`node --check site/app.js` passes.

## JOB 1 — the two Paul named

- **Waboose**: `https://files.dnr.state.mn.us/maps/state_forests/sft00002_geo.pdf`
  (10,798,941 B, PDF 1.6, 1 p., 1584×2448 pt, created 2017-06-14). The
  Paul Bunyan & Badoura map; the only DNR representation of the Waboose
  loop. Verified a real GeoPDF. Corners lon −95.236..−94.601,
  lat 46.780..47.436.
- **Itasca Summer**: `https://mobile-maps-files.dnr.state.mn.us/file/State_Parks/Itasca%20Summer%20GEO.pdf`
  (5,877,986 B, 1 p., 1224×792 pt, created 2026-06-23). Verified a real
  GeoPDF. Main map frame lon −95.309..−95.041, lat 47.129..47.259.
- **Itasca Winter: NO GeoPDF EXISTS.** `Itasca Winter GEO.pdf` on the
  mobile-maps mirror returns 500 with `{"detail":"Internal server error:
  400: File: Itasca Winter GEO.pdf in folder State_Parks does not exist."}`.
  Six further name variants probed, all 500/not-exist ("Itasca Winter
  Trails GEO.pdf", "Itasca Winter Trails and Facilities GEO.pdf",
  "Itasca Winter Map GEO.pdf", "Itasca Winter Recreation GEO.pdf",
  "Itasca Winter Trails and Facilities GEO.pdf" — the last two spellings
  both tried). Web search finds only the print PDF. The print PDF is
  `https://files.dnr.state.mn.us/maps/state_parks/spk00181_winter.pdf`
  (4,850,923 B, 2 pp., 2019, 1:65,000, "Map of Itasca State Park Winter
  Trails and Facilities") — **not georeferenced** (no /VP, no /Measure)
  and its text is outlined, so no text-based GCP extraction is possible.
  **Not wired, per the brief's rule: say so plainly instead of placing
  it wrong.** A hand georeference from the printed map would be ~±0.5 km
  and would visibly misalign Lake Itasca and the NCT against the viewer's
  own data. The print PDF is kept in `working/dnr-geopdf/` for reference.
  If the DNR ever publishes an Itasca Winter GEO, the wiring is one more
  def on the same pattern.

## JOB 2 — survey: what else intersects the trail

Method: geometric, against the viewer's own `site/data/trail-minnesota.geojson`
(348 features), in UTM 15N. State forests from the DNR enterprise
`bdry_state_forest` service (60 forests); state parks from
`plan_stateland_dnr` layer 10, `administrator='Parks'`, dissolved by
(mgtprgname, mgtprjname). Distances are to the dissolved boundary.

**State forests intersecting the NCT (6):** Bear Island (SFT00004,
179,594 ac), Burntside (SFT00011, 74,817 ac), Grand Portage (SFT00023,
100,174 ac), Paul Bunyan (SFT00038, 105,116 ac), Remer (SFT00042,
12,851 ac), White Earth (SFT00054, 155,394 ac). Near miss: Nemadji,
662 m. Badoura does NOT intersect (only Paul Bunyan does — the sft00002
sheet covers both forests on one map). Cloquet Valley, Fond du Lac,
Finland, Savanna, Hill River, Sturgeon River, Kabetogama SFs do NOT
intersect.

**State parks intersecting the NCT (3):** Itasca (30,660 ac), Lake
Vermilion–Soudan Underground Mine (4,136 ac), Maplewood (8,356 ac).
Near misses (<5 km): Bear Head Lake 1,238 m, Schoolcraft 2,829 m,
Jay Cooke 3,602 m. The one blank-program hit is three tiny unnamed
parcels (0.25 + 0.3 + 0.1 ac, Becker + St. Louis Cos.) — slivers, not a
named area. **Surprises the geometry settled:** Lake Bemidji SP is
34.9 km from the trail, Savanna Portage SP 47.3 km, Scenic SP 43.5 km,
Gooseberry Falls 74.4 km — the NCT runs inland through the BWCAW, not
along the North Shore, so the North Shore parks do not meet it. The SHT
meets the NCT only at its northern terminus, which is why.

**State trails crossing the NCT** (from the Nov 16 intersecting-trails
inventory, verified distances): Paul Bunyan State Trail (0 m, Walker),
Heartland State Trail (0 m, Walker), David Dill–Taconite State Trail
(2.0 m, Tower), Alex Laveau Memorial State Trail (44 m, Jay Cooke /
Thomson), Mesabi Trail (0 m, Tower + Ely — not a DNR map, no GeoPDF
sought). Central Lakes State Trail is shared tread (drawn as the NCT).

**GeoPDFs found for the intersecting set** (all verified 200 + real
GeoPDF via /Measure): the six forest codes resolve to **five distinct
maps** — see the duplicate finding below — plus Itasca Summer, Maplewood
Summer + Winter, David Dill–Taconite, Lake Vermilion–Soudan. That is
the ten wired.

**Checked and EXCLUDED (with reason):**
- Savanna Portage Summer GEO (`.../State_Parks/Savanna%20Portage%20Summer%20GEO.pdf`,
  2,632,809 B, real GeoPDF, downloaded) — the park is 47.3 km from the
  trail; the map is not wired. File kept in `working/dnr-geopdf/`.
- Paul Bunyan South GEO (`.../State_Trails/Paul%20Bunyan%20South%20GEO.pdf`,
  12,490,806 B, created 2025-09-08) — covers Crow Wing SP to Hackensack;
  its frame contains **0.00 km** of trail (tested geometrically). Not
  wired. The NCT crossing near Walker is on the North sheet.
- Paul Bunyan North / Heartland — **no GeoPDF found** on the
  mobile-maps mirror ("Paul Bunyan North GEO.pdf", "Paul Bunyan GEO.pdf",
  "Paul Bunyan and Heartland GEO.pdf", "Heartland and Paul Bunyan GEO.pdf",
  "Heartland GEO.pdf" all 500). The print PDF
  `https://files.dnr.state.mn.us/maps/state_trails/paul_bunyan_n_heartland.pdf`
  (5,333,783 B, 2 pp., "Map of Northern Paul Bunyan and Heartland State
  Trails", 2026-05-11) is **not georeferenced** (no /Measure). Same
  treatment as Itasca Winter: not wired, print PDF kept in
  `working/dnr-geopdf/`.
- Alex Laveau Memorial State Trail — no GeoPDF found under "Alex Laveau
  GEO.pdf", "Alex Laveau Memorial GEO.pdf", "Alex Laveau Memorial State
  Trail GEO.pdf" (all 500). Not wired.

**Duplicate-map finding (verified by title + date + corners, not just
size):** the DNR serves the same combined map under both forest codes —
sft00004 and sft00011 are both "Burntside and Bear Island State Forests
Public Recreation Map" (2019-07-02, identical corners); sft00002 and
sft00038 are both "Paul Bunyan and Badoura State Forests Map"
(2017-06-14, identical corners). Each is wired ONCE (sft00004 and
sft00002 respectively); the duplicate URLs are recorded in
data-sources.html. The map file number is the forest's sft code, found
via each forest's page (`dnr.state.mn.us/state-forests/forest.html?id=sft#####`).

**Where the files live:** park + trail GeoPDFs on
`mobile-maps-files.dnr.state.mn.us/file/<Category>/<Name>%20GEO.pdf`
(categories State_Parks, State_Trails). State forest GeoPDFs on
`files.dnr.state.mn.us/maps/state_forests/sft<code>_geo.pdf`. The DNR
GeoPDF index (`dnr.state.mn.us/geopdf`) is a WebGL map app, not a link
list. `gdrs.dnr.state.mn.us` is unreachable from this VM (TCP connect
fails) — the mobile-maps mirror carries the same files. The DNR's new
state-forest maps list is at
`dnr.state.mn.us/state-forests/maps-launch.html` (all six intersecting
forests are on it).

## Conversion method (and why not GDAL at first)

GDAL was unavailable when this pass started (the apt install from the
earlier session had not survived the environment reset, and the system
os-intent replay held the apt lock for ~15 min). The conversion reads
the georeferencing directly from each PDF with pypdf: the page /VP
/Measure gives /GPTS (lat,lon) ↔ /LPTS (page fractions within the
viewport /BBox); a least-squares affine maps BBox-normalised (u,v) to
(lat,lon), and the BBox's four corners are the overlay quad. Renders
are pdftoppm at 150 dpi, cropped to the viewport /BBox with Pillow,
long side ≤ 2400 px, JPEG q82 (the NCTA cap is ≤ 1600 px wide; these
sheets are twice the physical size, so the cap is on the long side).
GDAL 3.8.4 did arrive later (via the replay) and was used to
cross-check: the Waboose corners reproduce GDAL's to ~0.002 deg, and
the quad centre matches GDAL's reported centre exactly
(−94.91858, 47.10782). Affine fit residuals on the GeoPDFs' own control
points are ≤ 9e-05 deg (~7 m); extrapolation to the frame corners puts
placement at ~10–50 m — the same order as the NCTA sheets' own
residuals. The earlier session's "small bowtie NEATLINE" is the /Measure
GPTS box itself (the central ~20% of the page); the affine extrapolates
it to the full frame, which is exactly what GDAL does — do NOT place by
the bowtie.

**Multi-viewport sheets — which panel was wired:** several GeoPDFs
carry more than one map panel. The wired panel is the one covering the
trail; the others are recorded, not wired. Remer (sft00042): three
panels — Remer (wired), Overview, Golden Anniversary (not wired; the
Golden Anniversary forest does not meet the trail). Itasca Summer: main
map "AA MAP View 1" (wired) + "Inset" (Main Park Drive Area Detail,
right strip, shows as printed inside the image — a visibly bordered
inset panel, not re-placed). Maplewood Summer: main map "bound_park"
(wired) + "Campgrounds" inset (shows as printed). Lake Vermilion–Soudan:
main map "AAMAP View" (wired) + "inset1" mine-area detail (shows as
printed). Maplewood Winter, David Dill–Taconite, White Earth and the
full-page forest maps are single-panel. The inset panels are delineated
boxes on the sheet, so a viewer reads them as insets; their own
georeferencing is in the note below if a separate layer is ever wanted:
Itasca inset lon −95.2215..−95.1513, lat 47.1825..47.2543; Maplewood
Campgrounds lon −95.9503..−95.9379, lat 46.5205..46.5269; Soudan inset1
lon −92.2464..−92.2402, lat 47.8173..47.8205.

**Images verified by eye:** the Waboose and Itasca Summer renders were
viewed (real maps, legible: Lake Itasca, the NCT dotted line, trail
names, UTM grid on the forest sheet). The Itasca Winter print render
was also viewed (portrait page: main winter map on top, Insets 1–3 +
trail distances below).

## What was NOT touched (per the brief)

Basemap defs, BASES, MAPBOX_TOKEN, MAPTILER_KEY, STADIA_KEY,
`site/export.js`, `scripts/export_geopdf.py`, the Driftless work, the
Minnesota parcels layer. `git diff` on `site/app.js` is four hunks only:
the `buildDnrGeopdf` function, the ten defs, the draw-order list, the
legend rows (+ one comment line in `assertDrawOrder`). No raw GeoPDF
was put into `site/` — sources live in `data/geopdf/`, viewer images
are JPEGs only, same as the NCTA pattern (which keeps only JPGs in
`site/`).

## Still owed

1. **Live-browser click-through** of the DNR layers (toggle each on,
   check the image draws at zoom ≥ 11, the outline + label below 11,
   the popup + DNR link). Not done in this pass — no browser task was
   available to this agent. The focused re-check already running for
   the Partner Trails deploy is the place to fold this in.
2. **GeoPDF export entries** for the ten new layers (`site/export.js`
   and `scripts/export_geopdf.py` still lack `loops`, `atv`, `ohm`,
   `snow`, `sht` too — the DNR layers join that existing owed list).
   Deliberately not touched here per the brief.
3. **Itasca Winter** — wire it if the DNR ever publishes an Itasca
   Winter GEO (check the mobile-maps mirror); the print PDF is in
   `working/dnr-geopdf/itasca-winter-spk00181.pdf`.
4. **Paul Bunyan North / Heartland** — same: wire if a GeoPDF appears
   under any name (print PDF in `working/dnr-geopdf/paul-bunyan-n-heartland.pdf`).
5. **Alex Laveau** — wire if its GeoPDF surfaces.
6. SOURCES.md (repo root) still describes the motorized pull as
   chapter-extent — pre-existing debt from the Nov 16 statewide pull,
   not this pass.
7. The `/tmp` working area (512 MB tmpfs) filled during this pass when
   the Minnesota OSM PBF download (213 MB) collided with the survey
   dump; the PBF was deleted and all work moved to
   `working/dnr-geopdf/` (repo, persistent). The OSM PBF cross-check
   was dropped as unnecessary once the stateland survey completed.

## Popup fix, round 2 (Nov 16, after click-through #4)

The first fix (bind the popup to the interactive image overlay as
well as the outline) did NOT work in the live deploy: click-through
#4 put seven interior clicks into two sheets (Itasca Summer ×5,
Waboose ×2) and got no popup, while loop and parcel popups opened
normally in the same session. The rotated overlay's interactive
target never receives the event in this viewer. The popup now rides
on an invisible hit-polygon instead — the sheet's own closed ring,
transparent fill (`fillOpacity: 0`), canvas-rendered like the
parcels, whose popups provably open. The image keeps its own
binding too, in case the overlay path ever starts receiving clicks.
The NCTA sheets still have the outline-only behaviour (unchanged —
fixing them the same way was not asked for).

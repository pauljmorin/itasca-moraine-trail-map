# DNR GeoPDF survey — comprehensive, both lines (Nov 16, 2026)

Survey of **every public Minnesota DNR GeoPDF** (every series on
mndnr.gov/geopdf), each frame tested geometrically against **both**
lines — the Minnesota NCT (`site/data/trail-minnesota.geojson`,
900.11 km) and the Superior Hiking Trail
(`site/data/superior-hiking-trail.geojson`, 334.03 km, DNR
state-park portions only, ~67% of the ~310-mile published trail).
Folds in the North Shore / SHT survey; supersedes the first-pass
note (`docs/dnr-geopdf-layers-2026-11-16.md`) for the sheets it
re-tests, and corrects it in §8.

**Result: 25 new sheets wired, 35 DNR sheets total in the viewer.**
All OFF by default + lazy, group "The trail", subgroup "DNR maps",
zoom ≥ 11 gate, hit-polygon popups — the same mechanism as the
first pass. No commit or push yet; the coordinator verifies and
deploys.

## 1. Method

- **Index.** The mndnr.gov/geopdf downloader app reads the ArcGIS
  FeatureServer
  `https://gis.dnr.state.mn.us/host/rest/services/Hosted/mobile_maps_webmap_WFL1/FeatureServer/1`
  (layer `mobile_maps_footprints`, token-gated; token from
  `https://r29p-gis-portal-oauth-func-001.azurewebsites.net/api/getToken?app_id=mntopo`,
  `hosted_token.token` field). **807 index entries.** Download URL
  pattern: `https://mobile-maps-files.dnr.state.mn.us/file/<file_dir_name URL-encoded>`.
  `doc_type` is unreliable (309 entries have null `doc_type` but are
  real free GeoPDFs — e.g. AlanDale OHV verified HTTP 200); the
  index IS the free-download list. `gdrs.dnr.state.mn.us` is
  unreachable from this VM (verified Nov 16).
- **Footprint screen.** All 807 footprints tested in UTM 15N
  against both line files (`ns-survey/footprint-test.json`).
  **125 footprints intersect ≥ 1 line.** Footprints are approximate
  index rectangles (±10–20 km vs the true quad) — screening only.
- **Named-area candidates.** The 29 named-area footprint hits
  (State Forests / State Parks / State Trails) plus every
  named-area near-miss < 20 km from either line: **52 candidates**
  (`ns-survey/named-candidates.json`). All 44 not-already-held
  files downloaded to `ns-survey/mirror/` (242 MB, all HTTP 200).
- **Quad test.** Every downloaded PDF, every viewport: the PDF's
  own `/Measure` viewport read with pypdf, least-squares affine
  from GPTS↔LPTS, extrapolated to the full frame (never placed by
  the small central "bowtie" rect). Frame intersected against both
  lines in UTM 15N (`ns-survey/mirror-quad-test.json`,
  `ns-survey/sft-quad-test.json`). **Quad figures are authoritative;**
  footprint figures are screening only (§9 shows why).
- **Build.** `working/dnr-geopdf/build_dnr_geopdf.py` (venv
  `working/dnr-geopdf/.venv/bin/python`): renders page 1 at 150 dpi,
  crops to the viewport `/BBox`, long side ≤ 2400 px, JPEG q82;
  images `site/data/dnr-geopdf/<slug>.jpg`, GeoJSONs
  `site/data/dnr-<slug>.geojson`; source PDFs copied to
  `data/geopdf/`. Every new render was read visually; no CROPS
  entries were needed — every legend column and inset sits inside
  its frame and shows as printed, consistent with the already-wired
  sheets (only Itasca Summer got a crop, at Paul's explicit
  request). Winter variants were not individually read: same
  viewport structure and identical output dimensions as their
  summer twins.
- **Wiring rule (mine, flagged for the coordinator to override).**
  Wire the **named-area class only** (State Parks, State Forests,
  State Trails + sft-only forest maps). The 125 include
  regional/generic series (4 snowmobile quads, ~20 water-access
  county maps, ~15 trout-angling maps, ~15 recreation-basemap 1°
  tiles, OHV area maps, HWTs, water trails) that would flood the
  panel with ~125 toggles and duplicate existing viewer
  layers/basemap. All 125 are inventoried with per-line km in the
  appendix; the regional/generic decision is §6.

## 2. Wired this survey — 25 sheets

Per-line km are **quad figures** (the PDF's own `/Measure`),
recomputed independently (§10). Frames overlap each other, so the
per-sheet figures do not add to a trail total: the new NCT frames
sum to 314.99 km and the new SHT frames to 537.10 km of frame-km,
with summer/winter twins and overlapping Ramstad / forest / park
frames double-counted. The SHT line file itself is 334.03 km.

| Sheet | Series | Date | Viewport | NCT km | SHT km | Resid (deg) |
|---|---|---|---|---|---|---|
| Finland SF | State Forest | 2021-06-23 | MainMap | 0 | 126.17 | 1.0e-04 |
| Pat Bayle SF | State Forest | 2021-05-19 | MainMap | 0 | 30.05 | 5.7e-05 |
| Bowstring–Battleground–Welsh Lake | State Forest | 2019-02-22 | MainMap | 41.22 | 0 | 1.1e-04 |
| Paul Bunyan–Gulch Lake Cg | State Forest | 2017-03-13 | Gulch Lake Campground | 1.03 | 0 | 8.0e-08 |
| Tettegouche | State Park | 2026-07-27 | AA Main | 0 | 30.40 | 4.1e-06 |
| Split Rock Summer | State Park | 2026-10-28 | AASplit Rock Lighthouse State Park | 0 | 13.67 | 1.0e-06 |
| Split Rock Winter | State Park | 2026-10-28 | AASplit Rock Lighthouse State Park | 0 | 13.67 | 1.0e-06 |
| Judge C.R. Magney | State Park | 2026-06-09 | A - Main | 0 | 21.99 | 1.5e-06 |
| Temperance River | State Park | 2026-06-09 | Temperance River State Park | 0 | 17.54 | 9.6e-07 |
| Cascade River | State Park | 2021-12-23 | Main Map | 0 | 11.40 | 4.4e-07 |
| George Crosby Manitou | State Park | 2024-08-05 | Main Large | 0 | 10.22 | 1.9e-06 |
| Gooseberry Falls Summer | State Park | 2026-05-22 | Gooseberry SP | 0 | 3.47 | 2.7e-07 |
| Gooseberry Falls Winter | State Park | 2025-11-17 | Gooseberry SP | 0 | 3.47 | 2.7e-07 |
| Jay Cooke Summer | State Park | 2025-07-02 | Main Map | 0 | 2.19 | 1.7e-06 |
| Jay Cooke Winter | State Park | 2025-10-27 | Main Map | 0 | 2.19 | 1.7e-06 |
| Paul Bunyan North–Heartland | State Trail | 2026-07-09 | bound | 88.45 | 0 | 8.1e-05 |
| Munger–Alex Laveau | State Trail | 2026-09-30 | bound | 4.95 | 14.20 | 1.4e-04 |
| Central Lakes | State Trail | 2025-10-01 | MAP View 1 | 16.17 | 0 | 9.3e-05 |
| Taconite | State Trail | 2023-04-12 | Taconite Main | 163.17 | 0 | 1.5e-04 |
| Gitchi-Gami | State Trail | 2026-06-16 | bound_GOOSEBERRY | 0 | 41.86 | 1.2e-06 |
| Gitchi-Gami–Schroeder to Lutsen | State Trail | 2025-11-17 | Schroeder | 0 | 11.58 | 7.3e-07 |
| C.J. Ramstad–Duluth to Britton Pit | State Trail | 2023-04-11 | bound1 | 0 | 55.44 | 3.7e-06 |
| C.J. Ramstad–Britton Pit to Finland SF | State Trail | 2023-04-11 | bound2 | 0 | 14.54 | 3.7e-06 |
| C.J. Ramstad–Finland SF to Sawbill Tr | State Trail | 2023-04-11 | bound1 | 0 | 81.64 | 5.1e-06 |
| C.J. Ramstad–Sawbill Tr to Grand Marais | State Trail | 2023-04-11 | Bound2 | 0 | 31.41 | 1.2e-05 |

Notes on the wired set:

- **Finland SF** (sft00017, quad lon −91.94479..−90.80696, lat
  47.2126..47.68942) holds the longest single SHT stretch in the
  survey, 126.17 km. **Pat Bayle SF** (sft00037, quad lon
  −90.99999..−90.15231, lat 47.70229..48.04641) holds 30.05 km.
  Both were found by the state-forest **boundary** survey, not the
  footprint screen (§9).
- **Taconite** is a DIFFERENT map from the already-wired David
  Dill–Taconite sheet: a larger frame (lon −93.65724..−92.29236,
  lat 47.21404..47.80331) covering the full Taconite State Trail
  corridor west to Grand Rapids, 163.17 km NCT; David Dill–Taconite
  covers only the eastern segment (60.68 km). Both are wired.
- **Gitchi-Gami Maps 1–5 are one printed sheet** (six panels:
  Trail Overview, Gooseberry Falls to Silver Bay 17.3 mi, Schroeder
  to Lutsen 8.9 mi, Cut Face Creek to Grand Marais 5.1 mi, Two
  Harbors 0.9 mi, Silver Creek Cliff 0.5 mi). The five index files
  differ only in which panel they georeference (and in date/title:
  Map 2 is "Gitchi-Gami Gooseberry GEO", 2026-06-16; Maps 1/3/4/5
  are Nov 17, 2025, titled Silver Bay / Schroeder / Grand Marais /
  Two Harbors). Wired twice, once per georeferenced panel that
  contains SHT: the Gooseberry Falls to Silver Bay panel from Map 2
  (vp5, SHT 41.86) and the Schroeder to Lutsen panel from Map 3
  (vp0, SHT 11.58). The other panels contain no SHT in frame
  (Two Harbors nearest 4.16 km, Silver Creek Cliff 0.83 km, Cut
  Face Creek 0.45 km); the Trail Overview locator (SHT 214.37 km in
  its frame) is not wired — it is a small-scale locator strip, not
  a usable map panel.
- **C.J. Ramstad North Shore State Trail, all 4 segments**, rotated
  strips (neatline ~24°, confirmed by GDAL). Quad figures differ
  sharply from footprint figures (§9): Duluth–Britton Pit 55.44 vs
  12.66, Britton Pit–Finland 14.54 vs 41.29, Finland–Sawbill 81.64
  vs 60.88, Sawbill–Grand Marais 31.41 vs 26.14.
- **Munger–Alex Laveau** is the only new sheet containing BOTH
  lines (NCT 4.95, SHT 14.20).
- **Paul Bunyan North–Heartland**: the main panel (vp2 `bound`,
  NCT 88.45) is wired; the Bemidji Detail and Heartland Extension
  insets show as printed. The Extension inset's own viewport holds
  15.94 km NCT but is not wired separately — precedent is the Remer
  sheet, whose Overview panel (60.53 km NCT) is likewise not a
  separate layer.
- **Golden Anniversary–Remer** (`Golden_Anniversary-Remer_GEO.pdf`)
  is the SAME PDF as the already-wired sft00042 (identical
  viewports/figures: Remer 14.68, Overview 60.53, Golden Anniversary
  0). No duplicate def.

## 3. Already wired (first pass) — unchanged

Waboose (Paul Bunyan & Badoura, NCT 79.68), Burntside & Bear Island
(106.31), Grand Portage SF (NCT 32.26; also SHT 59.70 — the only
first-pass sheet containing SHT), Remer (14.68), White Earth (43.32),
Itasca Summer (26.42), Maplewood Summer (15.80) / Winter (15.72),
David Dill–Taconite (60.68), Lake Vermilion–Soudan (9.68). No
duplicates, no renames. Grand Portage SF and Remer were NOT
footprint hits either (§9) — they were found by the first pass's
boundary survey.

## 4. Tested and rejected — named-area candidates

Main viewport (or only viewport); nearest distance is frame-edge to
line in UTM 15N. Glendalough Winter is the same map as Summer
(same viewports/figures) and is covered by the Summer row.

| Map | NCT km | NCT nearest | SHT km | SHT nearest |
|---|---|---|---|---|
| Bear Head Lake SP | 0 | 0.68 km | 0 | 69.84 km |
| Land O'Lakes–Emily SF | 0 | 1.84 km | 0 | 109.87 km |
| David Dill Arrowhead–Pelican River–Taconite | 0 | 2.30 km | 0 | 68.90 km |
| Schoolcraft SP | 0 | 2.49 km | 0 | 127.97 km |
| Mississippi Headwaters SF | 0 | 2.60 km | 0 | 201.48 km |
| Hill River–Waukenabo SF | 0 | 3.82 km | 0 | 71.09 km |
| Paul Bunyan–Mantrap Lake Campground SF | 0 | 3.95 km | 0 | 202.37 km |
| Gitchi-Gami Map 4 (Cut Face Creek–Grand Marais) | 0 | 35.35 km | 0 | 0.45 km |
| Lake Isabella–Insula Lake SF | 0 | 5.39 km | 0 | 32.95 km |
| Burntside–North Arm Trails SF | 0 | 8.39 km | 0 | 77.36 km |
| Centennial SF | 0 | 9.23 km | 0 | 134.66 km |
| Nemadji SF (Main + Gafvert inset) | 0 | 9.80 km | 0 | 20.28 km |
| Koochiching–Smokey Bear SF | 0 | 41.73 km | 0 | 118.35 km |
| La Salle Lake SP | 0 | 17.85 km | 0 | 227.54 km |
| Bowstring–Moose Lake Campground SF | 0 | 17.54 km | 0 | 130.84 km |
| Glendalough SP Summer + Winter | 0 | 19.54 km | 0 | 257.57 km |
| Gitchi-Gami Map 1 (Silver Creek Cliff) | 0 | 73.55 km | 0 | 0.83 km |
| Gitchi-Gami Map 5 (Two Harbors) | 0 | 66.97 km | 0 | 4.16 km |
| Lake Jeanette SF (sft00030) | 0 | 25.59 km | 0 | 98.23 km |
| General C.C. Andrews SF (sft00020, all 4 viewports) | 0 | 32–55 km | 0 | — |
| Savanna Portage Summer GEO (loose end, §7) | 0 | 44.54 km | 0 | 63.16 km |
| Paul Bunyan South GEO (loose end, §7) | 0 | 5.25 km | 0 | 138.34 km |

State-forest boundary survey vs the SHT (from
`working/dnr-geopdf/state-forests.geojson`, 60 forests):
intersecting — Cloquet Valley (SFT00013), Finland (SFT00017),
Grand Portage (SFT00023). Near: Nemadji 806 m, Pat Bayle 4,947 m,
Riverlands 6,228 m, Fond du Lac 27,109 m, Lake Isabella 35,775 m,
Lake Jeanette 101,346 m. (Boundary proximity is not frame
containment: Pat Bayle's boundary is 4.9 km from the SHT line file
but its map frame holds 30.05 km of SHT; Nemadji's boundary is
806 m away but its frame holds 0.)

## 5. The regional / generic series — NOT wired (decision for the coordinator)

96 of the 125 footprint hits are regional/generic series, not
named areas. By series (footprint figures):

| Series | Hits | Biggest footprint figures |
|---|---|---|
| OHV area maps | 20 | Soo Line North NCT 249.69; Northwoods 201.31; Moose Walk/Run, Red Dot, Wild Country SHT 141.33; Hovland Woods NCT 16.81 / SHT 23.09 |
| Recreation basemap 1° tiles | 19 | Two Harbors SHT 178.27; Pokegama Lake NCT 125.91; Cass Lake NCT 115.76; Detroit Lakes NCT 106.87 |
| Public water access (county) | 16 | St. Louis (Central) NCT 203.69; Cass (Northern) NCT 179.88; Lake (Southern) SHT 160.18; Becker NCT 148.88 |
| Water trails | 16 | Lake Superior 3 SHT 83.50; Otter Tail 1 NCT 73.83; Lake Superior 5 NCT 46.37 / SHT 61.95; St. Louis 1 NCT 61.86 / SHT 26.06 |
| Trout angling | 16 | Northeast Map12 NCT 120.42; Northeast Map19 NCT 102.26 / SHT 8.53; Northeast Map3 SHT 88.07 |
| Hunter walking trails (HWT) | 5 | Paul Bunyan SE HWT NCT 34.00; Paul Bunyan NW HWT 18.09; Hubbel Pond 11.08; Caribou Lake SHT 0.29 |
| Snowmobile quads | 4 | NW Snowmobile Quad NCT 454.49; NE Snowmobile Quad NCT 423.72 / SHT 261.21; SW Quad NCT 195.09; SE Quad NCT 4.95 / SHT 24.73 |

These were not downloaded or quad-tested. Reasons: ~125 toggles
would flood the panel; the snowmobile quads and recreation
basemaps duplicate the statewide snowmobile layer and the basemaps
already in the viewer; OHV/HWT/water-trail/trout sheets are
single-purpose maps whose trail content is incidental to the
viewer. If Paul wants any of them, the quad-test path is the same
(download → `/Measure` → intersect); the NE Snowmobile Quad and
Two Harbors basemap are the obvious first candidates on SHT km
alone. **Flagged for the coordinator to confirm or override.**

## 6. DNR maps with no GeoPDF

Do not hand-place any of these (first-pass rule: placing by hand
would be ~0.5 km off):

- **Cloquet Valley SF** (sft00013.pdf, 2016-02-09, 2 pp., print
  PDF only, no `/VP`, no `/Measure`). Its boundary intersects the
  SHT, so this is the one genuine gap in SHT coverage — no
  georeferenced Cloquet Valley map exists in the index.
- **Fond du Lac SF** (sft00018.pdf, print PDF only).
- **Whiteface River SF** (sft00055.pdf, print PDF only).
- **Savanna SF** (sft00046.pdf, print PDF only) — and its frame
  would not meet either line anyway (§4).
- **Riverlands SF**: no map at all (sft00065.pdf 404; DNR page says
  "Map not available yet").
- **Itasca Winter**: no GeoPDF anywhere (only the 2019 print PDF).
  Correctly not wired.
- Mobile-mirror probes for all five (`State_Forests/<Name> GEO.pdf`)
  returned 500.

## 7. Loose ends resolved

- **Savanna Portage Summer GEO** (`savanna-summer-GEO.pdf`, held
  from the first pass): quad-tested vs both lines — NCT 0 (nearest
  44.54 km), SHT 0 (nearest 63.16 km). NOT wired. Confirms the
  first pass.
- **Paul Bunyan South GEO** (`paul-bunyan-south-GEO.pdf`, held from
  the first pass): NCT 0 (nearest 5.25 km), SHT 0 (nearest
  138.34 km). NOT wired. Confirms the first pass.
- **Remer sheet vp1 Overview panel** (NCT 60.53 km) and **vp2 Golden
  Anniversary panel** (NCT 0, nearest 5.11 km): not wired as
  separate layers — one def per sheet, main panel only (see §2).

## 8. First-pass corrections found via the index

- **"Paul Bunyan North_Heartland GEO.pdf" EXISTS** (footprint NCT
  90.75 km; quad 88.45). The first pass probed wrong names ("Paul
  Bunyan North GEO.pdf" etc.) and wrongly concluded no GeoPDF. Now
  wired; the stale "NOT wired" comment in `site/app.js` is fixed.
- **"Munger_Alex Laveau GEO.pdf" EXISTS** (footprint NCT 4.95 /
  SHT 18.26; quad 4.95 / 14.20). The first pass probed "Alex Laveau
  GEO.pdf" and missed it. Now wired.
- **"Taconite GEO.pdf" ≠ "David Dill Taconite GEO.pdf"** (§2).
- **Gitchi-Gami Maps 1–5 are one sheet** (§2), not five maps.
- **Lake Isabella sft00026 = sft00029** (same map, two codes —
  same as the Burntside sft00004/sft00011 pair). Wire once if ever;
  currently rejected (NCT nearest 5.39 km).
- **Golden Anniversary–Remer = sft00042** (§2).

## 9. Footprint-screen limits — the footprint is not the map

The footprint test alone would have missed **6 of the 35** wired
sheets: Grand Portage SF, Remer, Finland SF, Pat Bayle SF, and
both Gitchi-Gami panels — their approximate index rectangles miss
the line even though the true quad contains it. Conversely,
footprint figures routinely diverge from quad figures, in both
directions: Ramstad Duluth–Britton Pit 12.66 → 55.44 (quad),
Britton Pit–Finland 41.29 → 14.54, Finland–Sawbill 60.88 → 81.64,
Sawbill–Grand Marais 26.14 → 31.41, Taconite 187.95 → 163.17,
Paul Bunyan North 90.75 → 88.45, Central Lakes 18.45 → 16.17,
Bowstring 47.33 → 41.22, Munger SHT 18.26 → 14.20. **Report quad
figures for wired sheets; footprint figures are screening only.**
The rotated strips are the worst case (footprints are
axis-aligned rectangles; the sheets are rotated ~24°).

## 10. Verification

- **Independent recompute** (`ns-survey/independent_recompute.py`,
  separate code path — re-reads `/Measure`, own least-squares
  fit, own intersection): all 25 new sheets match the build
  figures exactly (0 mismatches > 0.05 km); built GeoJSON quads
  agree with the recompute to ≤ 5e-06 deg (5-decimal rounding).
- **GDAL cross-check** (GDAL 3.8.4, full rotated geotransform):
  Taconite worst corner 361 m, Finland 247 m, Munger ~279 m,
  Ramstad Duluth–Britton Pit 43 m, Ramstad Finland–Sawbill 65 m,
  Gitchi-Gami Schroeder 12 m. Same order as the first pass's
  Waboose validation (~0.002 deg ≈ 150–200 m); the affine is fit
  to the small central control rect and extrapolated, so a few
  hundred metres on 20–105 km frames is the method's known
  tolerance. Trail-km sensitivity to that offset, checked by
  intersecting the GDAL-corner polygon: Taconite NCT 163.95 vs
  163.17 (+0.78 km), Finland SHT 126.32 vs 126.17 (+0.15),
  Munger SHT 15.29 vs 14.20 (+1.09 — the SHT runs nearly parallel
  to the frame edge near Duluth, so a small shift moves a long
  stretch in/out). Reported figures are the viewer-placement
  (own-affine) figures.
- **Gitchi-Gami Gooseberry panel**: GDAL could not be used —
  GDAL binds to the file's first viewport (Two Harbors) and offers
  no viewport selection. Its placement rests on the same affine
  code that matched GDAL to 12–65 m on the sibling rotated sheets,
  plus geography: 41.86 km SHT in the Gooseberry→Silver Bay shore
  stretch, tiling with the adjacent Ramstad sheets.
- **GeoJSONs**: all 25 new rings closed (5 points, first = last),
  all corners inside Minnesota; all 25 images real JPEGs
  (96 KB–1.1 MB each, 12.4 MB total new); 35 DNR GeoJSONs and 35
  images on disk total.
- **Source URLs**: all 25 return HTTP 200 on GET (mobile-maps-files
  returns 405 to HEAD — method not allowed, not a missing file;
  the two files.dnr URLs return 206 to a ranged GET).
- **`node --check site/app.js` passes.** 35 `id: "dnr-"` defs, 35
  legend entries, all 25 new ids in the draw-order list (after
  `dnr-lake-vermilion-soudan`, before the Forest Service ids).
- **Renders**: all 25 new sheets read visually (Finland + Tettegouche
  full-size; the other 23 via contact sheets plus the Schroeder
  panel full-size). No legend/inset cropping needed.
- **data-sources.html**: intro rewritten (both lines, 35 sheets),
  25 new paragraphs (title, date, source URL, pull date Nov 16,
  2026, per-line km).

## Appendix — all 125 footprint hits

Footprint figures (screening only). "WIRED (this survey)" = one of
the 25 in §2; "wired already" = first pass. The 96
regional/generic hits are §5; they were not quad-tested.

### All 125 footprint hits (footprint figures — screening only; quad figures govern)

| Series | Map | NCT km (fp) | SHT km (fp) | Decision |
|---|---|---|---|---|
| HWT | Caribou Lake HWT | 0.00 | 0.29 | not wired — regional/generic series (see §5) |
| HWT | Hubbel Pond HWT | 11.08 | 0.00 | not wired — regional/generic series (see §5) |
| HWT | Paul Bunyan NW HWT | 18.09 | 0.00 | not wired — regional/generic series (see §5) |
| HWT | Paul Bunyan SE HWT | 34.00 | 0.00 | not wired — regional/generic series (see §5) |
| HWT | Pine Tree HWT | 1.04 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Alborn-Pengilly - Goodland | 56.79 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Chisholm | 34.15 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | David Dill Taconite - Ely to Purvis | 24.50 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | East Range | 31.17 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Forest Riders | 51.19 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Genoa | 7.01 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Hovland Woods - Old Greenwood | 16.81 | 23.09 | not wired — regional/generic series (see §5) |
| OHV | Iron Range Expansion Gilbert | 9.36 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Iron Range Gilbert | 1.87 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Len Hardy | 12.70 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Martineau | 18.13 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Moose Walk, Moose Run, and Red Dot | 0.00 | 80.19 | not wired — regional/generic series (see §5) |
| OHV | Moose Walk/Run, Red Dot, Wild Country | 0.00 | 141.33 | not wired — regional/generic series (see §5) |
| OHV | Northwoods | 201.31 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Prospectors East | 0.00 | 64.06 | not wired — regional/generic series (see §5) |
| OHV | Prospectors West | 95.76 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Quad Cities | 34.98 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Round River | 49.22 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Soo Line North | 249.69 | 0.00 | not wired — regional/generic series (see §5) |
| OHV | Soo Line South | 4.95 | 18.26 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Becker | 148.88 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Carlton | 4.95 | 6.46 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Cass (Northern) | 179.88 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Clay - Norman - Wilkin | 117.81 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Clearwater | 74.68 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Cook (East) | 49.47 | 63.36 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Cook (West) | 101.94 | 79.34 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Hubbard | 100.28 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Itasca (SE) | 122.74 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Lake (Northern) | 83.26 | 1.74 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Lake (Southern) | 0.00 | 160.18 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Mahnomen - Polk | 14.68 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | Otter Tail | 147.56 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | St. Louis (Central) | 203.69 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | St. Louis (Northern) | 0.31 | 0.00 | not wired — regional/generic series (see §5) |
| Public_Water_Access | St. Louis (Southern) | 0.44 | 84.19 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Basswood Lake | 26.55 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Battle Lake | 21.09 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Cass Lake | 115.76 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Detroit Lakes | 106.87 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Duluth | 4.95 | 30.05 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Ely | 64.39 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Grand Marais | 0.00 | 90.16 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Grand Portage | 4.18 | 28.59 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Hibbing | 43.18 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Lake Itasca | 72.68 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Outer Island | 0.00 | 0.76 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Pigeon Point | 8.76 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Pine River | 10.92 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Pokegama Lake | 125.91 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Port Wing | 0.00 | 6.19 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Saganaga Lake | 106.02 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Two Harbors | 0.00 | 178.27 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Vermilion Lake | 100.16 | 0.00 | not wired — regional/generic series (see §5) |
| Recreation_Basemap | Wahpeton | 88.71 | 0.00 | not wired — regional/generic series (see §5) |
| Snowmobile_Trails | NE Snowmobile Quad Map | 423.72 | 261.21 | not wired — regional/generic series (see §5) |
| Snowmobile_Trails | NW Snowmobile Quad Map | 454.49 | 0.00 | not wired — regional/generic series (see §5) |
| Snowmobile_Trails | SE Snowmobile Quad Map | 4.95 | 24.73 | not wired — regional/generic series (see §5) |
| Snowmobile_Trails | SW Snowmobile Quad Map | 195.09 | 0.00 | not wired — regional/generic series (see §5) |
| State_Forests | Bowstring-Battleground-Welsh Lake | 47.33 | 0.00 | WIRED (this survey) |
| State_Forests | Burntside-Bear Island | 106.52 | 0.00 | wired already (first pass) |
| State_Forests | Paul Bunyan-Badoura | 79.67 | 0.00 | wired already (first pass) |
| State_Forests | Paul Bunyan-Gulch Lake Campground | 1.14 | 0.00 | WIRED (this survey) |
| State_Forests | White Earth | 44.91 | 0.00 | wired already (first pass) |
| State_Parks | Cascade River | 0.00 | 11.60 | WIRED (this survey) |
| State_Parks | George Crosby Manitou | 0.00 | 10.65 | WIRED (this survey) |
| State_Parks | Gooseberry Falls (Summer) | 0.00 | 3.55 | WIRED (this survey) |
| State_Parks | Gooseberry Falls (Winter) | 0.00 | 3.55 | WIRED (this survey) |
| State_Parks | Itasca (Summer) | 30.79 | 0.00 | wired already (first pass) |
| State_Parks | Jay Cooke (Summer) | 0.00 | 2.19 | WIRED (this survey) |
| State_Parks | Jay Cooke (Winter) | 0.00 | 2.19 | WIRED (this survey) |
| State_Parks | Judge C.R. Magney | 0.00 | 22.89 | WIRED (this survey) |
| State_Parks | Lake Vermilion-Soudan Underground Mine | 9.68 | 0.00 | wired already (first pass) |
| State_Parks | Maplewood (Summer) | 15.97 | 0.00 | wired already (first pass) |
| State_Parks | Maplewood (Winter) | 15.97 | 0.00 | wired already (first pass) |
| State_Parks | Split Rock Lighthouse (Summer) | 0.00 | 13.75 | WIRED (this survey) |
| State_Parks | Split Rock Lighthouse (Winter) | 0.00 | 13.75 | WIRED (this survey) |
| State_Parks | Temperance River | 0.00 | 17.54 | WIRED (this survey) |
| State_Parks | Tettegouche | 0.00 | 31.55 | WIRED (this survey) |
| State_Trails | Central Lakes | 18.45 | 0.00 | WIRED (this survey) |
| State_Trails | David Dill Taconite | 63.11 | 0.00 | wired already (first pass) |
| State_Trails | Munger Alex Laveau | 4.95 | 18.26 | WIRED (this survey) |
| State_Trails | Paul Bunyan North and Heartland | 90.75 | 0.00 | WIRED (this survey) |
| State_Trails | Ramstad N Shore-Britton Pit-Finland SF | 0.00 | 41.29 | WIRED (this survey) |
| State_Trails | Ramstad N Shore-Duluth-Britton Pit | 0.00 | 12.66 | WIRED (this survey) |
| State_Trails | Ramstad N Shore-Finland SF-SawbillTr | 0.00 | 60.88 | WIRED (this survey) |
| State_Trails | Ramstad N Shore-SawbillTr-Grand Marais | 0.00 | 26.14 | WIRED (this survey) |
| State_Trails | Taconite | 187.95 | 0.00 | WIRED (this survey) |
| Trout_Angling | Trout Angling Northeast Map1 | 4.95 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map11 | 0.00 | 30.05 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map12 | 120.42 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map13 | 0.00 | 48.79 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map15 | 56.37 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map16 | 70.03 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map17 | 3.12 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map18 | 88.89 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map19 | 102.26 | 8.53 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map2 | 0.00 | 24.01 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map3 | 0.00 | 88.07 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map4 | 0.00 | 87.67 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map5 | 0.00 | 13.27 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map6 | 0.00 | 49.92 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map7 | 3.35 | 0.00 | not wired — regional/generic series (see §5) |
| Trout_Angling | Trout Angling Northeast Map8 | 10.63 | 70.15 | not wired — regional/generic series (see §5) |
| Water_Trail | Cloquet 1 | 0.00 | 5.50 | not wired — regional/generic series (see §5) |
| Water_Trail | Cloquet 2 | 0.00 | 39.56 | not wired — regional/generic series (see §5) |
| Water_Trail | Crow Wing 1 | 4.19 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | Lake Superior 1 | 0.00 | 20.79 | not wired — regional/generic series (see §5) |
| Water_Trail | Lake Superior 2 | 0.00 | 56.13 | not wired — regional/generic series (see §5) |
| Water_Trail | Lake Superior 3 | 0.00 | 83.50 | not wired — regional/generic series (see §5) |
| Water_Trail | Lake Superior 4 | 0.00 | 45.06 | not wired — regional/generic series (see §5) |
| Water_Trail | Lake Superior 5 | 46.37 | 61.95 | not wired — regional/generic series (see §5) |
| Water_Trail | Mississippi 1 Lake Itasca-Cass Lake | 5.01 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | Mississippi 2 - Cass Lake to Vermillion River | 8.53 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | Mississippi 3 - Vermillion River to Jacobson | 60.36 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | Otter Tail 1 | 73.83 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | Otter Tail 2 | 57.42 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | Red River 1 | 23.43 | 0.00 | not wired — regional/generic series (see §5) |
| Water_Trail | St. Louis 1 | 61.86 | 26.06 | not wired — regional/generic series (see §5) |
| Water_Trail | St. Louis 3 | 0.00 | 20.79 | not wired — regional/generic series (see §5) |

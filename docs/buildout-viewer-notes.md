# Finishing the Trail — build-out viewer v1 (Nov 13, 2026)

Standalone viewer at `site/buildout/` (live at
`https://pauljmorin.github.io/itasca-moraine-trail-map/site/buildout/`).
One viewer, two modes: Briefing (delegation) / Planning (chapters).
Does not touch the chapter map (`site/index.html`, `site/app.js`).

## Data provenance

- Gap lines cut from `site/data/trail-minnesota.geojson` (NCTA nct_public
  service, 348 features) by `site/buildout/build-data.py`.
- Proposed lines converted from KML/KMZ in the NCT Drive folder (sources
  kept in `site/buildout/src/`):
  - `proposed-arrowhead.kml` — "North Country Trail - proposed 102 miles",
    measured **101.45 mi** (1 feature).
  - `mwp-plan.kml` — MWP chapter plan: west from FF **49.59 mi**, north
    from FF **51.58 mi**, "west of FF alt 1" stub **3.33 mi**; the broken
    "west from alt 1" placemark (single junk coordinate at 115°E, −60°S)
    never becomes a feature and is dropped.
  - `corridor-2004.kmz` — 2004 NPS preferred-alternative corridor polygon
    (107 points, bbox lon −93.90..−91.37, lat 46.99..47.98; perimeter
    315.59 mi — a polygon, not a route length).
- Street View points from the two gap research files §6; 10 of 11
  panoramas confirmed Nov 13, 2026 (see the v3 section below) — ND-4 /
  Fort Abercrombie has no panorama on the road.

## Measured totals (from the files, `len_miles`)

- gap-arrowhead: 82 features, **152.80 mi** — foot 1.44, paved 114.94,
  road 24.98, other 11.44. Reconciles with the GR–Ely research file's
  153.04 mi within 0.24 mi (one 0.24-mi Developed Path feature the research
  counted as untyped). The Hwy 6 road-walk feature west of Grand Rapids
  (10.29 mi, centroid lon < −93.66) is excluded — it belongs to the
  Hwy 6 → Tioga Beach corridor, not GR→Ely.
- gap-western: 90 features, **104.86 mi** — road 78.38, paved 9.62,
  foot 4.64, sidewalk 3.90, other 8.32. Cut = all of chapter MWP + the
  four LLC "Becker Co Line To NCT" connector features at Frazee.

## Open reconciliation (do not paper over)

- The DL research file traces **113.63 mi / 78.82 mi on-road (91 features)**
  for the same western chain. The clean chain cut above totals 104.86 mi /
  78.38 mi on-road (90 features). **Reconciled Nov 13 (coordinator-verified,
  corrects the double-count guess below):** the 8.77-mi difference is a
  single 9.96-mi LLC Foot Path feature (Frazee→Vergas, lat 46.99→47.09,
  start −95.493, 46.986 to end −95.451, 47.088) that the research chain
  includes and this cut excludes (chapter LLC, seg_name None — not one of
  the four Becker connectors). The missing miles are footpath, not road:
  research foot 13.75 mi vs cut foot 4.64 mi, while road reconciles 78.82
  vs 78.38. The viewer headlines use the research/assessment figures
  (106.1-mi gap, 113.63-mi traced chain) with sources labeled, and the
  legend shows the drawn file's own totals. Whether the 9.96-mi footpath
  belongs in the western gap definition is the open question for v2 — it
  sits east of Frazee in LLC territory, on the Becker Co line → Vergas leg.

## Hard rules enforced (v1)

- $643,850 (Proposal 2027-179) everywhere, labeled "Not Submitted Final,"
  Mar 14, 2026. $800,000 appears nowhere.
- No parcel-count claim. Mesabi shown as disputed, never complete
  (Lottery "complete" Oct 2026 vs LCCMR 2027-341 $1.65M for final 2.5 mi
  by June 30, 2029 — to confirm with the Railroad Authority).
- Road type leads; no posted speed limit is asserted anywhere — the MnDOT
  sources consulted (Nov 13, 2026) publish no speed limit for any segment
  (the old "55 mph statutory default" line was removed with the MnDOT
  wiring; see the v3 section below).
- Corridor ends at the North Dakota border (Fort Abercrombie); the NCT
  does not pass through Detroit Lakes.
- U of M modeled route + ARDC geodatabase are NOT in the Drive folder and
  are not shown (footer says so). No parcel layer in v1 (routes unsettled).

## Verification (Nov 13, 2026)

- Headless probe `~/workspace/itm-verify/probe-buildout.js`: 177 overlay
  paths, 11 Street View markers, SV toggle off→0/on→11, planning mode
  renders with Risks + funding, gap popup opens, forbidden-content sweep
  clean. Zero page errors; only external OSM tile failures
  (ERR_TUNNEL_CONNECTION_FAILED — known VM artifact, tiles load live).
- Screenshots: `~/workspace/itm-verify/buildout-briefing.png`,
  `buildout-planning.png`, `buildout-popup.png`.

---

# v2 — Land cover + soils (Nov 13, 2026)

## Correction to the brief: the students used NO land-cover dataset

The U of M report ("North Country National Scenic Trail Route Plan,"
North Star Consulting, 18 MGIS students, Dec 8, 2025; report PDF in
`site/buildout/src/uofm-arrowhead-report.pdf`, 3.3 MB, text in
`uofm-arrowhead-report.txt`) lists its inputs in Appendix A (pp. 12–13).
Land cover is NOT among them. It appears exactly once, in Recommendations
(p. 10–11): "As higher-resolution hydrology and land cover datasets become
available, they can be added to the same modeling framework." The model was
a 30-m raster, seven-class suitability, least-cost paths, built from
ownership, recreation infrastructure and environmental constraints by
raster algebra. So the land-cover layer in this viewer is sourced fresh,
not recovered from the students' inputs: **NLCD 2021** (National Land Cover
Database, USGS / Multi-Resolution Land Characteristics Consortium, 30-m
Landsat-based, CONUS). The Esri Living Atlas NLCD ImageServer requires a
token (HTTP 499) and is not usable unauthenticated; the working service is
the **MRLC GeoServer WMS, https://www.mrlc.gov/geoserver/wms,
layer `mrlc_display:NLCD_2021_Land_Cover_L48`** (WMS GetMap verified in
EPSG:4326 and EPSG:3857; WCS GetCoverage verified for the corridor
histogram). The viewer shows it as live WMS tiles — no file shipped.

## Soils

**USDA NRCS SSURGO** (Soil Survey Geographic Database), vector map-unit
polygons, via **Soil Data Access (SDA) tabular REST,
https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest** (POST JSON
`{"query": ..., "format": "JSON"}`, no auth). Retrieved Nov 13, 2026.
Mukeys via `SDA_Get_Mukey_from_intersection_with_WktWgs84`, polygons via
`SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84` + `mupolygon`
(`mupolygongeo`, WGS84 WKT); attributes from `mapunit` (musym, muname),
`muaggatt` (drclassdcd, slopegradwta, flodfreqdcd) and `component`
(hydricrating for major components — muaggatt has no hydric column;
`hydricrating` and `hydgrp` do NOT exist in muaggatt). The Esri
USA_Soils_Map_Units FeatureServer also requires a token and was not used.

## What was built

- Buffer: **0.5 mile (804.67 m)** around the two gap lines
  (`data/gap-arrowhead.geojson` + `data/gap-western.geojson`), UTM 15N,
  saved as `src/corridor-buffer-arrowhead.geojson` /
  `src/corridor-buffer-western.geojson`.
- `data/soils-corridor.geojson` — **7,273 features, 2,830,532 bytes**,
  584 map units, clipped to the buffer, simplified ~70–90 m, coordinates
  rounded to 4 decimals. Properties: mukey, musym, muname, drainage,
  hydric, slope, flood, gap. Drainage split: well 2,810; very poorly
  1,242; moderately well 868; poorly 756; somewhat poorly 388; somewhat
  excessively 344; excessively 275; no data 590. Hydric Yes 2,348 (32%).
- `src/nlcd-corridor-stats.json` — NLCD 2021 class histogram inside the
  buffer (WCS, 1,600 px per gap bbox, masked to the buffer): cultivated
  crops 29.0%, deciduous forest 16.9%, pasture/hay 9.0%, open water 8.2%,
  woody wetlands 7.5%, mixed forest 6.3%, emergent herbaceous wetlands
  5.4%, developed open space 5.0%, developed low 3.7%, shrub/scrub 2.3%,
  developed medium 2.3%, evergreen forest 1.4%, grassland 1.4%,
  developed high 0.8%, barren 0.8%.
- Build script: `site/buildout/build-soils.py` (shapely + pyproj + PIL +
  numpy; re-runnable). Wiring: both layers planning-mode only, off by
  default, lazy (land cover fetches tiles on first check; soils fetches
  the 2.7 MB GeoJSON on first check), leave the map when the viewer
  switches back to briefing. Land cover has no click popup (raster
  tiles); soils popups show map unit, drainage, hydric flag, slope,
  flooding and a one-line trail meaning.
- Not obtained: nothing. Both datasets were obtainable in-session. The
  U of M modeled-alignment shapefile/KML and the ARDC geodatabase remain
  missing from the Drive folder and are still not shown.

## Ranked inventory — the report's other datasets as future viewer layers

From Appendix A (pp. 12–13) plus the methods text (pp. 5–7). Not built in
this pass; ranked by value to the delegation/chapter case.

1. **Wetlands** (Living Atlas USA_Wetlands FeatureServer) — HIGH.
   Boardwalk/tread planning: wetlands are the biggest construction-cost
   driver alongside soils, and the visible counterpart to the hydric-soils
   layer. (Caveat: NWI vintage varies by quad; check currency per county.)
2. **Parcels** (State of MN, MnGeo OpenParcels MapServer/0/0) — HIGH. The
   land-acquisition question; the crossed-parcels + one adjoining ring
   design is already approved — build once routes settle. Note the MnGeo
   layer numbering flipped in the Nov 2026 refresh (layer_id 1→0).
   Coverage caveat from the report: parcels came from opt-in open-data
   counties + Itasca from another source; Aitkin County parcels were NOT
   in the final suitability model.
3. **Public land / ownership** (ownership codes generalized from the
   parcel data — no standalone public-land layer in Appendix A) — HIGH.
   The model's desirability factor; a public-vs-private tint would make
   "where can we build" visible at a glance.
4. **Roads** (MnGeo road centerlines, gisdata.mn.gov/dataset/trans-road-centerlines-open)
   — MEDIUM. Context for access points and the road-walk segments; the
   OSM basemap already shows roads, so this adds little until access
   planning starts.
5. **Current Trails + Bike Trails** (MnGeo trans-state-trails-minnesota,
   trans-bikeway) — MEDIUM. Shows the Mesabi/Taconite and other trails
   the corridor crosses or could share; partly redundant with the gap
   lines themselves.
6. **Lakes / Rivers / Surface water** (DNR hydrography,
   gisdata.mn.gov/dataset/water-dnr-hydrography; surface water via MnGeo
   Info Office) — MEDIUM. Water crossings are bridge/permitting pinch
   points; OSM shows water, but hydrography polygons would let the viewer
   flag crossings explicitly.
7. **Bridges** (MnDOT bridge inventory, gisdata.mn.gov/dataset/trans-bridges)
   — MEDIUM-LOW. Existing crossings are reuse opportunities; a small
   point layer, cheap to add once routes settle.
8. **Snowmobile Trails / ATV Trails** (MnGeo trans-snowmobile-trails-mn;
   State of MN trans-state-park-trails-roads) — LOW as routing layers,
   but worth a risks-panel exhibit: they show where the proposed line
   would share or cross motorized corridors — the motorized-conflict risk
   the chapters named as their single greatest risk.
9. **Campgrounds** (state forest campgrounds,
   gisdata.mn.gov/dataset/struc-state-forest-campgrounds) — LOW.
   Amenity/overnight context for the hiker case, not a routing input.
10. **Current Proposed Trails / Trail Boundary** (NCTA) — ALREADY IN THE
    VIEWER as the gap and proposed lines; no separate layer needed.

Not in the report, flagged anyway: **DEM / slope**. The students' model
had no elevation input, and the report itself warns that "in wet or steep
areas, this could significantly change the relative attractiveness of
alternative corridors" (p. 10–11). A slope layer from USGS 3DEP (10-m,
or 1-m LiDAR where available) is the highest-value addition not in the
report's dataset list — rank it HIGH for a future pass.

---

# v3 — MnDOT live data wired into road-walk popups (Nov 13, 2026)

Source: `docs/gap-mndot-live-data-report.md` — AADT from MnDOT EMMA / TDMS,
shoulder widths from the 2024 Keypoints Details by County reports, read
Nov 13, 2026. `buildout.js` `mndotNote()` attaches figures by geography
(MN-135, MN-169 in Ely, Fergus Falls town traverse, Eagles Nest paved
Mesabi stretch) or NCTA `seg_name` (CR-88, Red River Valley Provisional
Route). No posted speed limit is asserted anywhere — none was found in the
MnDOT sources consulted; the old "55 mph statutory default" sentence, the
"speeds are statutory defaults" footer line, and the "CR-88 to the border"
panel line are all removed or corrected.

- MN-135 Embarrass→Tower: AADT 703–1,720 (2025); no paved shoulder
  (4 ft stabilized unpaved; 6 ft entering Tower) — confirms the Mesabi
  "no usable shoulder" wording.
- MN-169 Eagles Nest: mostly 4 ft paved, 8 ft only leaving Tower, one
  10-ft stretch — not a uniform 8 ft; 2018 rebuild ($16.4M, ~6 mi)
  confirmed. Shown on the paved Mesabi popups alongside Hwy 169 and in
  the Eagles Nest Street View point text.
- MN-169 in Ely: AADT 5,542 (2025); 8 ft paved + 1.5 ft unpaved at
  19th Ave E, 10 ft leaving Ely east.
- CSAH 88: 16.38 mi, Fergus Falls to the Wilkin line — not one 39.5-mi
  road to the border; 8 ft paved at the Fergus Falls end, no paved
  shoulder mid-stretch (6 ft stabilized) or near Rothsay (5 ft).
- Rothsay→border (23.68 mi): Wilkin county-road zigzag (no MnDOT
  shoulder data found) + US-75 from Kent (AADT 1,355; 2 ft paved +
  8 ft unpaved in Kent, 2–3 ft paved + 5 ft unpaved north; Red River
  bridge not in the Wilkin report).
- Fergus Falls town: US-59 AADT 6,008–7,118 in town, 13,317 north;
  shoulder data missing through town incl. the Pelican River crossing
  (11.1-mi gap in the Otter Tail report). MN-210 East: AADT 11,492 /
  6,008 in town; shoulders 10 ft entering/through town, 12 ft + 2 ft
  at one stretch, 8 ft leaving.
- Street View: 10 of 11 panoramas confirmed Nov 13, 2026 (`verified:
  true` with pano coordinates, date and notes in
  `data/gap-streetview.geojson`); popups now show the confirmed date
  instead of the blanket "not yet confirmed" warning. ND-4 / Fort
  Abercrombie has no panorama on the road — nearest is inside the
  historic site grounds (Jul 2008), marked as not a road view.

NOT wired (flagged, not guessed): the Hwy 6 road walk west of Grand
Rapids — the 10.29-mi Hwy 6 stretch is not in the gap file (it belongs
to the Hwy 6→Tioga Beach corridor), so the MN-6 figures (AADT 396–5,566;
mostly 2 ft paved + 2 ft unpaved, no paved near Cohasset) have no
road-walk popup to attach to. The Grand Rapids road features in the file
are US-169 / CR-76 town streets, not MN-6.

## Motorized competition — v4 (Nov 13, 2026)

Planning mode only. Two new layers, off by default, lazy-loaded like soils:
ATV (purple `#762a83`) and snowmobile (icy blue `#67a9cf`).

### Sources (this is the DNR OHV map-service address the ATV research file was missing)

- Minnesota DNR OHV Trails, 2026 season — ArcGIS REST FeatureServer,
  `https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0`
  (item 3a71aaab703a4454823758b1810f31a5). 1,642 features in the envelope
  (lon −93.8..−91.2, lat 47.3..48.05); 25 named systems.
- Minnesota DNR Snowmobile Trails — same host, `.../trans_snowmobile_trails_mn/FeatureServer/0`.
  36 features in the envelope; 30 named systems. Contact fields
  (`public_poc`, `public_pho`, `pocemail`) deliberately NOT pulled.
- Published mileages / inventory / honest lines:
  `docs/gap-atv-competition-research.md` and `docs/gap-atv-trails-inventory.csv`
  (55 rows). Build script: `site/buildout/build-motorized.py` (re-runnable;
  re-injects the panel section between the MOTORIZED-SECTION markers in
  `index.html`). Stats: `site/buildout/src/motorized-stats.json`.

### Method

- Drawn layers: both services clipped to a 2-mile buffer around the
  proposed Arrowhead line + 2004 corridor + current gap line, simplified
  ~30 m. ATV: 1,074 features / 16 systems, 413 KB. Snowmobile: 26 features /
  23 systems, 89 KB.
- Overlaps (UTM 15N, EPSG:26915): motorized miles inside the 2004 corridor
  polygon; proposed-line miles within 100 m of a motorized line; crossing
  LOCATIONS (intersection points clustered within 250 m — see below);
  current-line miles within 100 m.
- The envelope geometry query silently dropped 23 features on the first
  run (Red Dot segments just south of the envelope, two Voyageur segments
  just north) while the id list returned all 1,642. The build script now
  fetches the id list first, then features by objectId in chunks. The
  missing 23 are all outside the corridor/buffer and cannot affect the
  overlap numbers or the drawn layers.

### Numbers (GIS-measured off the DNR services, Nov 13, 2026)

- Inside the 2004 corridor: **ATV 120.1 mi; snowmobile 367.7 mi.**
- Proposed line within 100 m of motorized trail: **ATV 23.8 mi; snowmobile 56.8 mi.**
  Crossing locations: **ATV 20; snowmobile 32.**
- Current official line within 100 m of motorized trail: **ATV 14.0 mi; snowmobile 48.3 mi.**
- Headline overlap: **50.9 of the proposed line's 101.4 mi lie within 100 m
  of the Taconite State Trail** (groomed snowmobile spine, Grand Rapids–Ely);
  **16.6 mi lie within 100 m of the Taconite–Big Aspen ATV connection.**
- Raw point counts are NOT used: where the proposed line runs along a
  motorized corridor the two digitizations weave across each other
  (Taconite–Big Aspen Connection 227 raw points; Taconite snowmobile 616 raw
  points). Clustering within 250 m gives the 20 / 32 locations above.
- GIS miles differ from published system totals (segmentation, shared tread
  counted twice). Both are shown; neither is silently substituted. Example:
  Prospectors measures 176.4 GIS mi in the envelope vs 167 published (and the
  published figure itself is disputed: club 216+, consultant 250).

### What is list-only (19 of 55 CSV rows drawn; 36 listed, never drawn)

Systems outside the 2-mi buffer (Finland / Gunflint / Cook County approach
systems, Itasca County systems west and south of the corridor, adjacent
counties), club aggregates (Ely Igloo 152-mi system — its Tomahawk Trail IS
drawn), the three snowmobile county totals (not additive), and the two
blank-mileage rows (Two Harbors Corridor / Yukon, Gunflint — mileage not
found, left blank). Voyageur Country Phase 2 (+125 mi roadway + 76 mi
natural-surface trail) is EAW stage with no geometry — noted in the
Voyageur row's flag, not drawn. No line was invented anywhere.

### Honest lines carried into the panel

- § 84.777 (north of Highway 2, unsigned forest access routes open unless
  posted closed) is a rule about *riding* unsigned routes, not a right to
  *build* — building needs DNR designation and environmental review.
- HF 1012 / SF 1245 (signed-trails-only statewide) are not enacted.
- Snowmobile: groomed corridors 20–26 ft (32–36 ft at crossings), groomers
  to 17,000 lb — wide clearing, tread intact, unlike ATVs.
- The deconfliction-meeting claim (NCT not at the table) is reported in the
  folder but unverified against any meeting record — carried as reported,
  not asserted as fact.

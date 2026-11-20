# Data sources

Every external dataset used by this project: what it is, where it
comes from, who owns it, and the attribution it carries. Keep this
file current — add a section before (not after) a new source is
pulled.

## Official trail line — North Country Trail (Public)

- **What:** The official depiction of the North Country National
  Scenic Trail: route/centerline features with status, type,
  surface, ownership and chapter attributes.
- **URL:** https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/nct_public/FeatureServer
- **Layers used:** Layer 2, "North Country Trail - Public"
  (polyline); Layer 1, "Point Data - Public" (waypoints — parking,
  camping, shelters, water, points of interest; pulled 2026-11-10
  into `data/points/ncta-points.geojson`, 114 points in the working
  envelope, and indexed by the gazetteer — see
  `scripts/build_gazetteer.py`)
- **Owner / publisher:** North Country Trail Association, on behalf
  of the National Park Service.
- **Attribution (verbatim from the service):**
  - Service description: "The official depiction of the North Country National Scenic Trail, produced by the North Country Trail Association on behalf of the National Park Service."
  - Service copyright text: "North Country Trail Association"
- **Use here:** Public ArcGIS feature service, queried via its REST
  endpoint. Pulled in full by `scripts/pull_official_line.py`
  (4,102 features nationally at first pull, 2026-11-10) and clipped
  to the chapter working extent in `config/chapter.json`
  (84 features retained; see the file metadata in
  `data/segments/official-line-chapter-extent.geojson`).
- **Mileage (Paul, Nov 19, 2026 — the pins decide):** mileage on
  this map comes from the chapter's own segment pins
  (`docs/segment-gap-analysis.md`): 73 miles adopted, 76 miles
  chained into one continuous line (78 miles stored in the official
  file), with a 3-mile unadopted gap. Do NOT chase any outside
  published figure — NCTA's totals, the chapter's old "about 100
  miles", or any 80- or 117-mile figure. Audit Nov 19, 2026: no
  80- or 117-mile figure for the chapter's trail appears anywhere
  in the viewer (80 appears only as a bridge count and in km; 117
  nowhere); the only competing figure was "about 100 miles" in the
  data-sources intro and `about.html`, now aligned to the pins'
  numbers.
- **Rounding (Paul, Nov 19, 2026):** mileage is rounded to the
  nearest whole mile everywhere in the viewer, the panel and the
  sources page — no decimals on mileage figures. NCTA mile-marker
  numbers (MN-123.5) and T07 segment ranges (MN-81.5–86.5) are
  positions, not lengths, and keep their half-mile values. Sub-mile
  feature lengths (access lines, parcel trail-inside) keep one
  decimal — rounding them to 0 would be false. Precise measured
  values stay in the analysis record (`docs/segment-gap-analysis.md`:
  73.23 / 76.15 / 78.19 mi) and in quoted research figures.
- **Fallback source (if the service is ever unavailable):** NPS
  DataStore, https://irma.nps.gov/DataStore/ — unit NOCO geospatial
  datasets. Not used to date.

## Official trail line — Minnesota portion (added 2026-11-13)

- **What:** The same official NCTA line as above, kept for the whole
  state instead of the chapter extent: every feature whose `state`
  attribute is `MN`, full geometry, all attributes.
- **Pulled by:** `scripts/pull_minnesota_line.py` (same paging method
  as `pull_official_line.py`), Nov 13, 2026. Working file
  `data/segments/official-line-minnesota.geojson` (full attributes);
  site file `site/data/trail-minnesota.geojson` built by
  `scripts/build_site_data.py` with the same `TRAIL_KEEP` list and
  10 m tolerance as the chapter line (348 features, 252 KB, 0
  dropped in simplification).
- **Contents:** 348 features, 566 mi (geodesic, full geometry),
  lon −96.72 to −89.93, lat 46.25 to 48.10 — North Dakota border
  (Fargo) to the Border Route Trail junction (Grand Portage).
  Chapters west to east: MWP (Minnesota Waters and Prairie) 86,
  LLC (Laurentian Lakes) 65, ITM (Itasca Moraine) 40, STN (Star of
  the North) 2, ARW (Arrowhead) 90, ELY (Ely Northwoods) 5, KEK
  (Kekekabic Trail) 41, BRT (Border Route Trail) 11, BSC 2,
  unassigned 6 (short connectors near Duluth/Superior).
- **Use here:** the "NCT — all Minnesota" layer — a stronger
  slate-blue line (weight 3.5, opacity 0.9, #4a6fa5 since Nov 18,
  2026 — Paul: the old 2px faint slate was too hard to read),
  drawn UNDER the chapter line (see `assertDrawOrder` in
  `site/app.js`), ON by default. Popups reuse `trailPopup`;
  the other Minnesota chapter names were added to `CHAPTER_NAMES`
  with this layer (BRT = Border Route Trail; BSC left unmapped).
- **Star of the North extent (added 2026-11-18, Paul):** the
  chapter's segment per NCTA's own chapter page
  (https://northcountrytrail.org/trail/minnesota/stn/): "from
  Minnesota 84 to Highway 6, northeast of Remer" — about 30
  miles of trail. The extent is NOT taken from the official
  line's `chapter` attribute: it tags only 2 features / 10 mi
  as STN; the rest of the same continuous trail is tagged ARW.
  **Interpretation method:** the 12 official-line features
  between the two crossings were chained end-to-end (150 m
  endpoint tolerance, no breaks), 31 mi total, then clipped
  at the west end. **West cut [JUDGMENT J1]:** the MN-84
  crossing is placed at lon −94.21, from the OSM "State Highway
  84" line's northern terminus (−94.209, 46.981) and Longville
  (−94.207); good to about a third of a mile. The OSM road extract in the repo
  ends at lat 46.98 and the MnDOT centerlines service carries no
  usable route number for MN-84 here, so the crossing is by
  longitude, not measured against a road survey. The 4 mi of
  footpath west of the cut is Itasca Moraine territory per the
  chapter definition and is already covered by the chapter
  parcels, so the cut loses nothing and draws no parcel twice.
  **East end:** the MN-6 crossing NE of Remer (−93.847, 47.103),
  ~5 mi NE of Remer, where the footpath meets the Highway 6 road
  walk; the chain ends exactly at the junction, so no clip is
  needed there. **Result:** `data/segments/trail-stn.geojson`
  (built by `scripts/build_stn_line.py`): 12 features, 27 mi
  clipped (26 mi foot path + 1 mi on-road connectors), all
  in Cass County (verified against the MnGeo county boundaries
  service: only Cass intersects the slice bbox). Note the
  chapter's "30 miles" counts the full 31-mi chain from the
  Itasca Moraine boundary; the clipped STN line is 27 mi.
  **Trail styling (changed Nov 19, 2026, Paul):** the STN chunk is
  now its own published layer — `site/data/trail-stn.geojson` plus
  the `trail-stn` layer def, drawn like the chapter line over the
  state line — because the chapter-attribute view of the state line
  showed only ~10 mi of STN tread. The state line still draws the
  same 12 features underneath (verified Nov 18: 11 match the
  published file at 0–1 m on both ends; the 12th is the clipped
  first feature, whose end matches at 1 m and whose start is
  3,784 m east of the published feature's start — exactly the
  MN-84 clip, since the drawn line continues unclipped to the
  Itasca Moraine boundary). **Open question for Paul:** the J1 crossing
  placement (± about a third of a mile) and the "30 miles" vs 27 mi difference
  are recorded here; if the chapter's maintained section in fact
  starts at the Itasca Moraine boundary rather than at MN-84,
  the clip (and the 3.87-mi piece's parcels) moves to the STN
  layer.
- **Note:** the often-quoted "~800 miles" for the NCT in Minnesota
  is not what the official service draws — the service's Minnesota
  features measure 566 mi. The gap is unexamined (service gaps vs
  the figure counting the Border Route / Kekekabic / SHT links).

## Arrowhead reroute polygon — 2004 NPS preferred-alternative corridor (added 2026-11-18, Paul)

- **What:** The congressionally approved planning corridor for the
  Arrowhead reroute: the 2004 NPS preferred alternative (NPS Draft
  Route Assessment & Environmental Assessment, 2004; authorized by
  Congress March 2019, Dingell Act, P.L. 116-9). One polygon, 107
  points, ~315 mi perimeter, ~1,255 sq mi (geometry-measured).
- **Source:** `site/buildout/src/corridor-2004.kmz` (the same file
  the Finishing-the-Trail build-out viewer draws as its
  "corridor" layer, `site/buildout/data/corridor-2004.geojson`).
  Copied verbatim to `site/data/arrowhead-reroute-polygon.geojson`
  so the ITM viewer stays self-contained.
- **Note on the build-out viewer's popup:** it calls the corridor
  "about a 200-foot-wide planning corridor". The polygon as drawn
  is miles wide (~1,255 sq mi) — the "200-foot" phrase describes
  the planning concept, not the polygon. The ITM viewer's popup
  does not repeat it.
- **Use here:** the "Arrowhead reroute polygon" layer (The trail
  group), OFF by default and LAZY, styled as in the build-out
  viewer (blue #2166ac, weight 1.5, fill 0.08). The polygon is the
  container for the Arrowhead parcels (see the parcels section):
  it contains ALL parcels shown, and the bike path / road walk
  fall outside it. A second, narrower polygon exists in the
  build-out sources (`site/buildout/src/corridor-buffer-arrowhead.geojson`,
  an 804.67 m buffer around the proposed 102-mi route, ~140 sq mi)
  — it is NOT the reroute polygon: it contains the whole gap line
  including the bike path and road walk, so it cannot express
  Paul's rule. It is used for corridor statistics only.
- **Confirmed Nov 18, 2026 (Paul's rule check):** the 2004 corridor
  is the polygon the U of M / North Star Consulting route study
  ("North Country National Scenic Trail Route Plan", Dec 8, 2025,
  `site/buildout/src/uofm-arrowhead-report.txt`) uses as its study
  area — "the NCT's revised preferred alternative corridor between
  Grand Rapids and Snowbank Lake. This corridor polygon, provided
  by NCTA" (p. 4); its "buffered version" is a modest buffer of
  that corridor, not the 140-sq-mi gap-line buffer above (which is
  far smaller than the 1,243-sq-mi corridor, not larger).
  `site/buildout/src/nlcd-corridor-stats.json` carries only NLCD
  pixel-class counts for the two corridors — no polygon geometry.
  `site/buildout/build-data.py` §3 builds the 2004 corridor from
  the KMZ; no other Arrowhead polygon is built there. The T-series
  packet was also checked for a different polygon: T06's brief and
  output Doc (`nct-arrowhead-reroute-status-2026-11-15`, 3,252
  words — "polygon", "geojson", "kmz", "shapefile" all 0 hits),
  the T13 brief (its output Doc does not exist yet), the T19
  brief (a map specification, no polygon geometry), and the
  completion case plan — none describes a reroute polygon other
  than the 2004 corridor. Polygon equal-area re-measured Nov 18:
  1,243.4 sq mi (3,220.4 km2, NAD83 Conus Albers).

## Inventoried trail (added 2026-11-18, Paul)

- **What:** one layer, `site/data/inventoried-trail.geojson`, **1
  feature (MultiLineString, 2 lines), 1,767 points, 10.91 GIS
  miles** — the concatenation of ALL the GPS tracks walked while
  inventorying the trail, not the published trail line. Wired in
  `site/app.js` as id `inventoried-trail`, group "The trail",
  right after the NCT — all Minnesota layer, OFF by default and
  LAZY, teal #0d9488. Only the ground actually walked is drawn.
- **Sources (chapter property, in `data/inventoried-trail.geojson`
  properties):**
  - Nov 11, 2026: `Nov_11,_2026,_10_36_12_AM.gpx`, 1,038 points,
    6 mi. No car tail: longest run above 15 mph is 0
    consecutive segments under the same rule used for Nov 18.
  - Nov 18, 2026: `Nov_18,_2026,_2_47_32_PM-chopped.gpx`, 729
    points, 5 mi. The car tail was cut before this layer was
    built: the tracker stayed on for the drive home — walking
    ~3.5 mph until 22:24:30 UTC, then sustained 50–70 mph (max
    89 mph) to the end of the track. Rule: first index where the
    next 30 consecutive segments are all above 15 mph, then back
    to the last point at or under 5 mph. Cut after 22:25:29 UTC
    (47.01664, −94.53610): 323 points, 5 mi removed from
    1,052 points / 10 mi. The chopped GPX is kept at
    `working/photos-inbox-2026-11-18/` alongside the original.
  - New tracks are appended as new lines in the same file (and
    its `site/data/` copy) as the inventory grows.
- **Interpretation:** none beyond the chop. The layer shows where
  the volunteers actually walked; it makes no claim about the
  official route, and a gap in it is a gap in the inventory,
  not a gap in the trail.

## Trail alerts — NCTA (chapter extent + Minnesota)

- **What:** NCTA's own current-awareness notices — closures, storm
  damage, reroutes, new routes — quoted verbatim, credited to NCTA.
- **URL:** https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/trail_alerts/FeatureServer
  — layer 1 "trail_alerts" (alert points), layer 2
  "trail_alerts_new_rte" (reroute lines). Same NCTA ArcGIS
  organisation as the official line.
- **Chapter layer (Nov 10, 2026):** `scripts/pull_trail_alerts.py`
  clips to the chapter working extent — 5 alert points, 0 reroute
  lines. Site file `site/data/trail-alerts.geojson`.
- **Minnesota layer (Nov 13, 2026):**
  `scripts/pull_minnesota_alerts.py` pulls the same service over a
  Minnesota bounding box (lon −97.3 to −89.5, lat 46.0 to 49.4) and
  EXCLUDES anything inside the chapter working extent, so the two
  layers are complementary: both on shows every Minnesota alert
  exactly once. 22 alert points + 7 reroute lines (Nov 13, 2026).
  Site files `site/data/trail-alerts-minnesota.geojson` and
  `site/data/trail-alert-lines-minnesota.geojson`. A few points sit
  just across the border (Fargo, Superior, and the Wisconsin NCT)
  — NCTA alerts on this same trail, kept for the end-to-end hiker.
- **Date handling:** the service stores each alert's Date as UTC
  midnight of the day AFTER the intended calendar date; the
  scripts carry both the raw epoch ms (`date_ms`) and the
  America/Chicago calendar date (`date`). The map displays `date`.

## Minnesota county parcels — corridor clip

- **What:** Tax parcel boundaries with ownership attributes,
  compiled from opt-in counties (GAC parcel standard fields,
  including `owner_name` and `ownership`).
- **URL:** https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/plan_parcels_open/FeatureServer
  (layer 0, "Open Parcels In Minnesota"; layer 1 is the per-county
  metadata layer used for the coverage check — the two layer numbers
  flipped in the Nov 9, 2026 quarterly refresh; fixed 2026-11-13 and
  verified live against the service). Commons page:
  https://gis.data.mn.gov/datasets/minnesota::parcels-compiled-from-opt-inopen-data-counes-minnesota-2
- **Owner / publisher:** Minnesota Geospatial Information Office
  (MnGeo), Minnesota IT Services, from county-supplied data.
- **Attribution:** The dataset is public open data (Minnesota
  Geospatial Commons lists access constraints: none); the service
  itself carries no copyright text. The Commons metadata notes the
  data are **not suitable for accurate boundary determination**.
- **Snapshot:** compiled content dated 2026-08-06 (per-county
  `rundate` in the metadata layer); pulled 2026-11-10 by
  `scripts/pull_parcels_corridor.py`.
- **Use here:** Corridor clip only (trail-crossing parcels plus the
  adjoining ring), stored at `data/parcels/parcels-corridor.geojson`.
  **Owner names ARE published on the map** — they are published
  public records in the county data, and the chapter ruled on
  2026-11-10 that the site shows them (this reverses the original
  working-view-only rule; see DESIGN.md privacy rules).
- **Coverage for the counties the chapter's trail crosses**
  (determined 2026-11-10 against MnGeo county boundaries — see
  `data/parcels/county-coverage.md`): Becker, Cass and Clearwater
  are in the compilation. **Hubbard is NOT** (the county has not
  opted in: `gac_open_approval` is false) — see the fallback below.

### Hubbard County parcels — county fallback

- **What:** Hubbard County tax parcels in the county's own schema
  (PIN, `PINAME1`/`PINAME2` owner fields, PLSS and class fields).
- **URL:** https://gis.co.hubbard.mn.us/arcgis/rest/services/OpenData/Hubbard_County_Tax_Parcels/FeatureServer
  (layer 0, "Tax Parcels")
- **Owner / publisher:** Hubbard County, Minnesota (county open
  data). The service carries no copyright text.
- **Use here:** Same corridor clip, merged into
  `data/parcels/parcels-corridor.geojson` with `source_county` and
  `source_dataset` fields distinguishing it. Pulled 2026-11-10 by
  the same script. Working view only, same privacy rule.

### Arrowhead reroute corridor parcels (added 2026-11-18, Paul)

- **What:** Same MnGeo compilation as above (layer 0), clipped to
  the Arrowhead reroute corridor instead of the chapter's trail.
- **Counties crossed** (determined 2026-11-18 by intersecting the
  2004 reroute polygon with county boundaries, confirmed against
  two independent sources — OSM admin_level=6 relations and the
  U.S. Census TIGERweb county file, which agree exactly): Itasca
  (45 polygon vertices), St. Louis (31), Lake (17), Aitkin (4),
  Cass (10). **All five are in the compilation**
  (`gac_open_approval` true, verified 2026-11-18 from the
  metadata layer), so no county fallback service is needed.
  Cook County is NOT crossed — the corridor's eastern end stops
  in Lake County.
- **Selection rule (Paul's reroute-polygon rule, Nov 18, 2026):**
  the reroute polygon contains ALL parcels shown, and NO parcel
  polygons are drawn along the bike path or the road walk.
  Implemented as: only gap-line segments that lie INSIDE the
  2004 polygon AND are not bike-path (`surface` "paved", the
  Mesabi Trail, 115 mi) or road-walk (`surface` "road", 25 mi)
  segments take part in the crossed/adjoining selection. The
  in-polygon foot trail is the gap-line mileage inside the polygon
  with the bike-path and road-walk surfaces removed: **13 mi**
  (25 features, all in the Grand Rapids area, Itasca County — the
  rest of the gap line east of Grand Rapids is Mesabi Trail bike
  path and road walk, with no foot trail at all). 55 mi of the
  153-mi gap line lies inside the polygon across all surfaces.
  "All parcels inside the polygon" is NOT published: 45,793
  parcels intersect the 1,255-sq-mi polygon (Itasca 25,586; St.
  Louis 18,241; Lake 1,458; Aitkin 80; Cass 428) — a ~22 MB file
  and not a trail corridor set. The polygon is the container;
  the corridor set is the crossed + one adjoining ring along the
  in-polygon foot trail, exactly as for the chapter parcels.
- **Use here:** `data/parcels/parcels-arrowhead.geojson`, pulled
  2026-11-18 by `scripts/pull_parcels_arrowhead.py`: **347 parcels
  (108 crossed + 239 adjoining), all Itasca County** — the
  in-polygon foot trail is the Grand Rapids-area pieces only
  (13 mi), so no St. Louis / Lake / Aitkin / Cass parcel is
  selected. (First build was 355; a Nov 18 verification pass
  found 8 adjoining parcels 4–22 m from the nearest crossed
  parcel — admitted by a false "intersect" in the shared
  `scripts/geo_util.py` `seg_seg_intersect` (its general case
  treated a collinear orientation of 0 as "the other side", so
  two nearly-parallel lot lines could report as intersecting).
  Fixed to require strictly opposite signs; re-pulled 347.
  The chapter parcels were checked the same way and are clean:
  0 of 786 adjoining parcels outside the 3 m ring, so no
  chapter repair is owed.) The pull drops 639 attribute-empty
  records (water bodies and rights-of-way, e.g. Pokegama Lake
  ~22.7 sq km and the Mississippi River corridor) before
  selection: without the filter they bridge the ring — the first
  run returned 2,823 adjoining parcels, most of them lakeshore /
  riverbank parcels adjoining the water, not the trail. Verified
  Nov 18 on the published file: all 347 centroids inside the
  reroute polygon; all 108 crossed within 1 m of in-polygon
  foot/other trail; all 239 adjoining within 3 m of a crossed
  parcel; zero parcels whose only trail contact is the bike path
  or road walk (6 parcels sit within 3 m of the bike path /
  road walk but touch a crossed parcel — they are in via the
  foot-trail ring, not via the bike path). Same privacy rule as
  the chapter parcels: owner name + mailing address as published
  (chapter ruling Nov 10, 2026), taxpayer fields never carried.
  **Itasca County's compiled records carry no `owner_name` and no
  `own_add_*`** (and no `acres_poly` / `acres_deed`), so the
  published Arrowhead parcels show parcel ID, county, land class
  and corridor — but no owner, and acres derived from the record's
  own `Shape__Area` (sq m / 4046.8564224; validated against
  `acres_poly` on 361 chapter parcels, median difference 0.01%).
  The taxpayer name (`tax_name`, populated for all 347) is NOT
  carried, per the chapter's privacy rule. Land class: Itasca
  records carry the bare numeric assessor class code in
  `useclass1` (33 codes, e.g. 201, 670, 776), not the descriptive
  string the other counties carry — the popup translates them via
  `PARCEL_LAND_CLASS_LABELS` using the Minnesota assessor
  class-code definitions (St. Louis County's published
  ClassCodeLegend, same statewide code system).

### Star of the North trail parcels (added 2026-11-18, Paul)

- **What:** Same MnGeo compilation as above (layer 0), clipped to
  the Star of the North trail instead of the chapter's trail.
- **Line:** `data/segments/trail-stn.geojson`, built by
  `scripts/build_stn_line.py` from the official NCTA line — the
  chapter's segment per NCTA's own chapter page ("from Minnesota
  84 to Highway 6, northeast of Remer"), 27 mi clipped
  (26 mi foot path + 1 mi on-road connectors). See the
  "Star of the North extent" note under "Official trail line —
  Minnesota portion" for the chain, the MN-84 cut [JUDGMENT J1],
  and the open question on the west end.
- **Counties crossed:** Cass ONLY (verified 2026-11-18 against
  the MnGeo county boundaries service — only Cass intersects the
  slice bbox, lon −94.30..−93.80, lat 46.95..47.20). Cass is in
  the compilation (`gac_open_approval` true, verified 2026-11-18
  from the service's metadata layer), so no county fallback
  service is needed. Hubbard County, which is NOT in the
  compilation, is not crossed — the line starts at the MN-84
  crossing, east of the Hubbard/Cass line.
- **Selection rule:** crossed + one adjoining ring along the
  chapter trail, exactly as for the chapter parcels (crossed =
  line crosses/touches the parcel or passes within 1 m;
  adjoining = boundary within 3 m of a crossed parcel's
  boundary). There is NO reroute polygon for Star of the North,
  so Paul's polygon rule does not apply — but the underlying
  principle does: NO parcel polygons are drawn along a road
  walk. Implemented as: only the `slice_role` "foot" features
  (26 mi) take part in the selection; the 3 on-road
  connectors (1 mi) are excluded.
- **Cass County fields:** Cass's compiled records carry
  `owner_name` and `acres_deed` (`acres_poly` is null on all Cass
  records, so acres falls back to `acres_deed` — `map_parcel`
  already does this; no `Shape__Area` acres fallback is needed,
  unlike Itasca County in the Arrowhead pull). Same privacy rule
  as the chapter parcels: owner name + mailing address as
  published (chapter ruling Nov 10, 2026), taxpayer fields never
  carried.
- **Use here:** `data/parcels/parcels-stn.geojson`, pulled
  2026-11-18 by `scripts/pull_parcels_stn.py`: **334 parcels
  (36 crossed + 298 adjoining), all Cass County**, published as
  `site/data/parcels-stn.geojson` (334 in → 334 out, 0 dropped in
  simplification; 334/334 carry an owner, 332/334 carry acres —
  the two without acres are an "Assessed Elsewhere" parcel and a
  county public parcel, legitimate nulls). The pull drops 142
  attribute-empty records before selection (water bodies and
  rights-of-way). The filter was tightened the same day after the
  first run admitted 13 attribute-empty shell polygons into the
  ring: their `state_pin` is the bare county prefix ("27021-",
  no PIN body), which a naive non-null test accepts as an
  identity — the filter now requires a PIN body after the prefix
  (or an owner / land class / ownership value). Verified Nov 18
  on the published file: 36/36 crossed and 298/298 adjoining
  present; 0 shell parcel IDs (no ID ending in "-"); all 334
  centroids inside the STN corridor; zero parcels whose only
  trail contact is an on-road connector (connectors never entered
  the selection).

## Government-owned lands — who to talk to (added 2026-11-18, Paul)

- **What:** Ownership-class coverage in the Minnesota NCT corridor —
  the layer that tells you who the entity is you have to talk to and
  work with, next to Parcels in the panel. Parcels give
  click-for-information on a piece of ground; this layer names the
  managing entity/owner for the ground around the trail. One layer,
  five categories — Federal, State, Land trust, County, Tribal —
  each broken into kinds. This is coverage, not per-parcel records:
  it overlaps the Parcels layer by design, and the popup says so.
- **Corridor:** the same 2-mile buffer around
  `site/data/trail-minnesota.geojson` (348 features, 566 mi) as
  timber — 4,973.7 km² (1,229,025 ac), all three chapters (ITM,
  Arrowhead, Star of the North). The 2004 reroute polygon is NOT
  used here; coverage is the trail buffer.
- **Backbone — MnGeo Government-Owned Lands**
  (research doc §4.1, grade A management / B public):
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/plan_gov_own_open/FeatureServer
  (layer 0, "Plan Gov Own Open"). Fields carried: `govt_own`,
  `county_pin`, `co_name`. Statewide the service holds 179,934
  features: State 82,764; Tax Forfeit 42,097; Federal 38,125;
  County Fee 11,608; Tribal 5,340 — across 55 counties.
  **Hubbard County is NOT in the service** (confirmed absent from
  the county list) — see the gap fill below.
- **Kind refinements:**
  - Land trust — DNR `plan_stateland_dnr`, layer 1 "Stateland Type
    Trust" (research doc §2.7): school-trust polygons with
    `landtype`, `administrator`, `countyname`, `su_acres`. The DNR
    manages school trust land through its Lands and Minerals
    division.
  - State kinds — DNR `bdry_dnr_managed_areas`, layer 2 "Dnr Stat
    Plan Areas": statutory boundaries with `area_type` (State
    Forest / State Park / State Recreation Area / State Wayside)
    and `area_name`. 142 areas statewide; 13 fall in the corridor
    (State Forest, State Park, State Recreation Area only — no
    State Wayside in the corridor).
  - Federal kinds — USFS `EDW_ProclaimedForestBoundaries_01`,
    layer 0 (research doc §1.3): Chippewa National Forest
    (1,599,789.4 ac proclaimed) and Superior National Forest
    (3,270,136.0 ac proclaimed); plus the Tamarac National Wildlife
    Refuge boundary from the local sheets
    (`site/data/tamarac-1of3/2of3/3of3.geojson`, 489.2 km² union).
  - Tribal kinds — the reservation boundaries already in the viewer
    (`site/data/leech-lake-reservation.geojson`,
    `site/data/white-earth-reservation.geojson`).
  - Hubbard gap fill — the county boundary from MnGeo
    `bdry_counties_minnesota` (2,590.3 km²), used only to clip the
    statutory polygons.
- **Pull:** 2026-11-18 by `scripts/pull_gov_owned_lands.py`
  (re-run the same day after a labeling correction — see below).
  Grid-envelope id queries (0.1° cells, 159 envelopes) against the
  gov-owned service, then fetch by objectId in chunks of 500:
  20,527 gov-owned candidates; 4,719 trust candidates. Published
  file `site/data/government-owned-lands.geojson` (11,465 features,
  7.26 MB, simplified 15 m like parcels, 0 dropped); working file
  `data/government-owned-lands.geojson` at full resolution.
- **Counts by category and kind** (recomputed from the published
  file, 2026-11-18):

  | Category | Kind | Features |
  |---|---|---:|
  | County | County fee | 362 |
  | County | Tax-forfeit (county forest land) | 4,116 |
  | Federal | National Forest — Superior | 2,411 |
  | Federal | National Forest — Chippewa | 249 |
  | Federal | National Wildlife Refuge — Tamarac | 152 |
  | Federal | Other federal | 103 |
  | Land trust | School trust land | 1,910 |
  | State | Other state | 1,604 |
  | State | State Forest — Bear Island / Burntside / Grand Portage / Nemadji / Paul Bunyan / Remer / White Earth | 36 / 11 / 43 / 34 / 1 / 10 / 65 |
  | State | State Park — Bear Head Lake / Itasca / Lake Vermilion-Soudan Underground Mine / Maplewood | 11 / 29 / 111 / 45 |
  | State | State Recreation Area — Iron Range Off-Highway Vehicle | 47 |
  | Tribal | Tribal — Leech Lake Band of Ojibwe | 74 |
  | Tribal | Tribal — White Earth Nation | 28 |
  | Tribal | Tribal (nation not identified in this source) | 13 |
  | **Total** | | **11,465** |

  Category totals: County 4,478; Federal 2,915; Land trust 1,910;
  State 2,047; Tribal 115.
- **Coverage acres** (corridor-clipped; categories overlap where
  boundaries overlap, so these do not sum to a single total):
  Federal 242,059 ac; County 149,353 ac; State 103,095 ac; Land
  trust 70,770 ac; Tribal 4,686 ac — 569,963 ac of feature area
  inside a 1,229,025-ac corridor (~46%). The rest of the corridor
  is private land, which has NO geometry in this layer (see J3).
- **Method — judgment register** (the interpretation method; every
  call below is labeled):
  - **J1 Trust precedence.** Trust polygons are drawn as Land trust
    features, and trust area is subtracted from any gov-owned
    feature it overlaps, so trust ground is drawn exactly once:
    1,719 features cut (by base class: State 1,022; Federal 369;
    Tax Forfeit 287; County Fee 30; Tribal 11), 227 dropped as
    fully trust. The trust polygons themselves (1,910) carry the
    trust source, not the gov-owned service.
  - **J2 Kind by plurality share.** A feature's kind is the overlay
    covering the largest share of its corridor-clipped area;
    `kind_share` records that share (0–1). 1,739 features (15%)
    have `kind_share` < 0.5 — they straddle a kind boundary and the
    label is the plurality, not a clean fit. The popup does not show
    the share; it is in the data for anyone checking a boundary.
  - **J3 Private has no geometry.** The gov-owned service covers
    government land only. A complement (everything not government
    = private) would mislabel lakes, roads and other non-parcel
    land as private. Private ownership is parcel-level and already
    carried by the Parcels layer; the legend says so ("Private
    land — see Parcels").
  - **J4 Hubbard gap fill.** The service has no Hubbard coverage,
    so 2 features are drawn from DNR statutory park/forest
    polygons clipped to Hubbard County, flagged `gap_fill=true`.
    Statutory boundaries include private inholdings — the popup
    says so, and Parcels underneath shows them.
  - **J5 County category.** County Fee / Tax Forfeit are carried as
    a County category though Paul named four categories; the
    service returns it and it is a real entity to talk to; hiding
    it would leave holes in the coverage. Adjustable later (hide
    or merge).
  - **J6 Tribal category.** Carried as its own category; the nation
    is named from the reservation overlay (Leech Lake Band of
    Ojibwe, White Earth Nation) and otherwise reads "nation not
    identified in this source" (13 features) — never guessed.
- **Entity strings** (the popup names the entity first):
  National Forest → "USDA Forest Service — {forest}"; National
  Wildlife Refuge → "U.S. Fish and Wildlife Service — Tamarac
  National Wildlife Refuge"; other federal → "Federal — managing
  agency not named in this source"; State Forest → "Minnesota DNR
  — Division of Forestry ({name} State Forest)"; State Park /
  State Recreation Area / State Wayside → "Minnesota DNR — Parks
  and Trails ({name} …)"; Land trust → "Minnesota DNR — Lands and
  Minerals (School Trust land)"; County fee → "{County} County";
  Tax Forfeit → "{County} County — Tax Forfeit Land"; Tribal →
  the nation name, or "Tribal government (nation not identified
  in this source)".
- **What was excluded or uncertain:**
  - **"Other state" (1,604 features) and "Other federal" (103):**
    the service names only the level of government, not the agency
    or unit. The popup says "State of Minnesota (managing agency
    not identified in this source)" / "Federal — managing agency
    not named in this source" rather than attributing to DNR or
    any other agency. The first pull labeled "Other state" as DNR
    land; that was caught on verification and corrected before
    filing, and the pull was re-run.
  - Trust features carry no `county_pin` / `govt_own` (nulls — the
    trust source has neither); their county comes from the trust
    layer's `countyname`.
  - No State Wayside falls in the corridor, so that kind does not
    appear in the file even though the classifier handles it.
  - The two Ottawa / Chequamegon proclaimed forests that fall in
    the query bbox are outside the Minnesota corridor and
    contribute no features.
- **Use here:** layer id `gov-owned`, label "Government-owned
  lands", OFF by default, LAZY, group "Land ownership",
  immediately after `parcels-stn` in the panel (also in
  `assertDrawOrder` right after `parcels-stn`); style
  `govOwnedStyle` / popup `govOwnedPopup` in `site/app.js`; legend
  section after the Parcels rows, including the Private note.
  Display adjustable later (Paul): colors (Federal blue
  `#1d4ed8`, State green `#15803d`, Land trust amber `#a16207`,
  County grey `#78716c`, Tribal pink `#be185d`, all 0.25 fill with
  darker borders; tax-forfeit dashed outline), split into
  per-category toggles, or on-by-default.
- **Verification (2026-11-18):** counts recomputed from both files
  (11,465 features each; category counts match the pull summary;
  0 non-polygon geometries; `gap_fill` 2; `kind_share` < 0.5
  1,739); one sample popup per category checked against the
  properties; `node --check site/app.js` passes. Not committed,
  not deployed.

## Access layers — forest roads and recreation trails

Pulled 2026-11-10 by `scripts/pull_access_layers.py` into
`data/access/access-lines.geojson` (one FeatureCollection; each
feature carries `source_type` and `source_dataset`). All are
Minnesota DNR services on the state enterprise host, used under the
Minnesota DNR General Geographic Data License Agreement
(https://www.dnr.state.mn.us/sitetools/data_software_license.html);
the services carry no per-service copyright text.

- **MNDNR Administered State Forest Roads** (`source_type:
  state_forest_road`) —
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_forest_roads/FeatureServer
  (layer 0). Owner: Minnesota DNR, Division of Forestry. The
  authoritative source for state forest roads (from the DNR STARS
  database); Commons metadata last published 2025-04-30.
- **OHV Trails, Minnesota** (`source_type: ohv_trail`) —
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer
  (layer 0). Owner: Minnesota DNR. Designated ATV/UTV (off-highway
  vehicle) trails.
- **Snowmobile Trails, Minnesota** (`source_type:
  snowmobile_trail`) —
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer
  (layer 0). Owner: Minnesota DNR.
- **Hunter Walking Trails** (`source_type: hunter_walking_trail`) —
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_hunter_walking_trails/FeatureServer
  (layer 0). Owner: Minnesota DNR.
- **State Trails, Minnesota** (`source_type: state_trail`) —
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_trails_minnesota/FeatureServer
  (layer 0). Owner: Minnesota DNR, Parks and Trails.
- **State Park Trails and Roads** (`source_type:
  state_park_trail_or_road`) —
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_park_trails_roads/FeatureServer
  (layer 0). Owner: Minnesota DNR, Parks and Trails. In this extent
  this is chiefly the Itasca State Park trail/road network.

## Motorized trails — existing layers verified + proposed-trail hunt (added 2026-11-18, Paul)

### Existing layers — verified 2026-11-18

- Files: `site/data/motorized-atv.geojson` (6,968 features, 102 systems,
  3,357 GIS miles), `site/data/motorized-ohm.geojson` (5,732 features,
  78 systems, 2,551 GIS miles), `site/data/motorized-snow.geojson`
  (276 features, 191 systems, 23,151 GIS miles). All recomputed from
  the live files 2026-11-18; they match the counts in `site/app.js`
  and `site/data-sources.html` exactly. Nothing was changed — the
  counts are right.
- Sources: DNR OHV service `trans_ohv_trails_mn/FeatureServer/0`
  (live count 2026-11-18: 7,931 total features — the ATV and OHM
  layers overlap on the same features, 6,968 ATV + 5,732 OHM −
  7,931 = 4,769 features allow both) and DNR snowmobile service
  `trans_snowmobile_trails_mn/FeatureServer/0` (live count 276,
  unchanged). Pulled 2026-11-16 by
  `scripts/pull-motorized-mn-statewide.py` (full state). The
  2026-season claim still holds: the live service counts are
  unchanged from the Nov 16 pull. (Note: the build scripts are
  `scripts/pull-motorized-*.py`; there is no `build-motorized.py` or
  `build-motorized-bc.py` in the repo.)
- Buildout raw files (`site/buildout/data/`): `motorized-atv.geojson`
  1,074 features (GIA-funded, e.g. Alborn-Pengilly Railroad State
  Trail), `motorized-snow.geojson` 26 features (club-maintained, e.g.
  Hawks Trails / TrailHawks Snowmobile Club),
  `motorized-atv-bc.geojson` 2,333 features (OHM, e.g. Alger Grade
  OHM Trail, Lake County). Counts recomputed 2026-11-18, as claimed.
- Corridor overlap (computed 2026-11-18 against
  `site/data/arrowhead-reroute-polygon.geojson`, the 2004 corridor,
  1,242.5 sq mi): designated ATV 165.5 GIS miles inside the
  corridor (incl. Big Aspen 23.14 mi, Quad Cities 14.22 mi,
  Taconite 35.61 mi); designated OHM 165.5 mi (the corridor's OHM
  trails are the same lines as its ATV trails); designated
  snowmobile 564.4 mi. Method: shapely union of each file's
  geometries intersected with the polygon; miles = degrees × 69
  (approximate, same convention as the layer titles).

### Proposed trails — hunt, 2026-11-18

- NO new viewer layer was wired: no proposed route in or around the
  corridor has published GIS. Per Paul's rule (Nov 18), proposed
  routes are never drawn without GIS; pinpoints below instead.
- How "proposed vs existing" was decided (interpretation method): a
  route counts as proposed only if a dated public source (DNR news
  release / GIA proposal / EAW / master plan / club or county
  document) names it as proposed, in review, or in planning AND it
  does not appear as a designated feature in the live DNR
  OHV/snowmobile service pull of 2026-11-18. A route in the live
  service is treated as existing/designated even if its history
  began as a proposal (e.g. the Itasca County trails below). Where
  the service cannot separate a proposal's segments from the
  designated system, that is stated, not resolved by guessing.
  Corridor membership was tested by point-in-polygon against the
  2004 corridor polygon, not by town name or county.

### Proposed ATV trails — overlay layer (added 2026-11-20, Paul)

- The Nov 18 hunt wired NO layer because no proposed route had
  published GIS. The Nov 19–20 GIS overlay produced the geometry
  (color-extraction from DNR map PDFs, vector extraction from
  GeoPDFs, approximations along named roads where the source pins
  endpoints), so the layer is now wired:
  `site/data/atv-proposals.geojson` (10 features, one per proposal,
  845.24 mi drawn) and `site/data/atv-proposal-crossings.geojson`
  (11 point features). Both OFF by default, in the "Other trails"
  group. Overlay work files:
  `~/workspace/goals/finish-the-north-country-trail-in-minnesota/analysis/atv-overlay/`
  (findings, inventory, overlay-results.json, per-proposal notes,
  tools/overlay.py, tools/build_viewer_layer.py).
- Headline (measured, not quoted): 102.14 proposed miles inside
  5 mi of the NCT; 10.44 mi within 300 m; 11 crossings — 10 Ice
  Cracking, 1 Connect Four. Against the reroute alignment: 35.20
  mi / 1.07 mi / 1 crossing. Built designated OHV trail within
  5 mi of the NCT: 418.42 mi (context, not the case's number).
- Interpretation method (how raw leg findings became the drawn
  classification): every proposal GeoJSON reprojected WGS84 →
  EPSG:26915 (UTM 15N) and simplified at 2 m before measuring.
  (a) Within-5-mi miles: proposal length inside an 8,046.72-m
  buffer of the reference centerline. (b) Near-coincident miles:
  length inside a buffer of the centerline whose width depends on
  the source's confidence tier — 50 m for vector sources (the
  drawn line is the line; the 50-m width is the shared-tread
  test) and 300 m for schematic sources (overview maps traced
  from a rendered PDF, digitizing tolerance ~300 m); a schematic
  source's "near" figure is a possible-coincidence figure, not an
  exact one. (c) Crossings: proposal-line intersections with the
  reference line, clustered within 100 m so one crossing sampled
  as several points counts once; collinear overlap reported
  separately as overlap miles. Every mileage figure is recomputed
  from the geometry by tools/overlay.py (shapely 2.2.0); no figure
  is read off a source's prose — source-claimed mileages appear
  alongside for comparison only. Minimum distance is reported for
  proposals entirely outside the buffer, so a near miss is not a
  bare zero.
- Classification rules (what the colors mean): `conflict` — the
  proposal crosses the NCT as drawn (crossings > 0): Ice Cracking
  (10), Connect Four (1). `in-buffer` — length inside the 5-mi
  buffer > 0 with zero crossings: TATR main (0.25-mi boundary
  sliver), CR 89 (3.61), Akeley (5.32), Pike River Bridge (1.04).
  `clear` — zero miles inside the buffer: Voyageur Phase 2, Seven
  Beavers Connector, Seven Beaver CP 971506, TATR alternate.
  The two reference lines for the 5-mi test are the NCT line
  itself (site/data/trail-minnesota.geojson, 559.30 mi measured)
  and the Arrowhead reroute alignment (site/buildout/data/gap-arrowhead.geojson,
  151.91 mi measured); the 2004 corridor polygon is the corridor,
  not a reference line.
- Judgment calls (labeled as such): TATR's 0.25 mi is a boundary
  result — two fragments where the route's 4.81-mi closest
  approach dips 0.19 mi inside the buffer, exactly the ±300-m
  tolerance, so it could equally sit outside. Ice Cracking's 9.37
  near miles are 139 fragments (largest 0.63 mi), paralleling at
  ~200–400 m, not one shared stretch. Voyageur's 194.97 drawn
  miles include the full alternative alignments and context trails
  drawn in the EAW figures' project colors (+58% vs the ~125-mi
  claim is a scope difference, not a tracing error); the verdict
  (0 mi, 38.58 mi minimum distance) is insensitive to it. Pike
  River Bridge is approximated along the TH 169 centerline, not
  the trail as built (the resolution puts the trail on the east
  side of TH 169). Seven Beaver CP 971506 is traced from the DNR
  proposal map with ~0.1–0.2 mi endpoint uncertainty. The Akeley
  page-1 overview layer measures 6.851 mi vs the page-2 detail
  layer's 5.32 mi — page 2 was used as authoritative because it
  matches the claim; the verdict is insensitive to it.
- NOT drawn (and why): A10 North Star Connector — map exists but
  no extractable vector layer and no defensible dike line could be
  picked from the Fourtown-Grygla system; B1–B18 — no published
  geometry (text-only or no-route proposals); the U of M GIS 8501
  proposed route line and phased gaps — student work, no
  fieldwork, never authoritative and never drawn. The built OHV
  layer (418.42 mi within 5 mi) is context from the Minnesota
  Geospatial Commons OHV Trails 2026-season dataset, not part of
  this layer; its build note is
  analysis/atv-overlay/built-layer-note.md.
- Per-proposal sources: TATR — DNR EAW Figures 1–4 (extracted
  with tools/extract_route_v2.py; the v1 extraction's +14.2%
  inflation was a skeleton artifact, withdrawn); Voyageur Phase 2
  — DNR EAW Figures 2-1 to 2-12 + Attachment A-1; Ice Cracking —
  DNR "Proposed Ice Cracking ATV Trail map" PDF; Seven Beavers
  Connector — DNR proposal map PDF (GeoPDF geotransform rejected,
  re-georeferenced from scale bar + Black Mallard Lake anchor);
  Connect Four — ROD Figure 2 (Figs 2-1 to 2-7) + EAW; CR 89 —
  DNR map PDF, Aug 2017 (GeoPDF, raster only); Akeley — DNR-hosted
  Round River proposal PDF, Apr 6, 2017 (GeoPDF page-2 vector
  layer); Pike River Bridge — approximated from St. Louis County
  RBA 26-396 endpoints (TH 169 centerline, TIGER/Line 2024);
  Seven Beaver CP 971506 — traced from the DNR Seven Beavers
  proposal map, Nov 18, 2025.

#### In / around the corridor — the planning question

1. **Prospectors Loop Phase 2 ("Connect Four")** — ~59 mi (22 mi
   existing route open to ATV use + 28 mi existing route with new
   ATV use + 9 mi proposed new route), connecting Ely, Babbitt,
   Embarrass, Tower, Soudan. Proposer: Prospectors Trail Alliance
   Club. Source: DNR environmental review, EAW April 2023, Record
   of Decision (no EIS required) issued; project page
   https://www.dnr.state.mn.us/input/environmentalreview/prospectors-loop.html.
   EAW figures are USGS topo PDFs (figure-3 checked — NOT a
   GeoPDF). Status: the DNR service already carries 278
   "Prospectors" features (system 180 mi per DNR trail detail
   id=118, June 2026), but the service does not flag which are
   Phase 2, so the designation/build status of the 9 new-route
   miles is NOT confirmed from the service alone. The
   Soudan/Breitung access route is still proposed, in environmental
   review, "a couple years" out (DNR trail detail + OHV closures
   page, Nov 1, 2026). OVERLAP FLAG: Ely and Soudan are inside the
   corridor polygon; the Soudan/Breitung access route is a live
   proposed motorized route on the corridor's high dry ground
   (Tower–Ely–Soudan). Related leads (motorized status
   unconfirmed): Iron Range Resources 2021 grant (Prospector's Loop
   phase two incl. Beaver River Bridge, Ely–Babbitt); Tower Area
   Coalition of Trails $200k Federal Recreational Trails Program
   grant, Sept 2025, incl. "Prospector Connection Trail" (wetland
   delineation commenced).
2. **David Dill–Taconite and David Dill–Arrowhead state trails, ATV
   additions** — proposed additions named in the DNR ATV Strategic
   Master Plan §2.4.3 (Dec 2025): "Current proposed routes include
   additions to the Voyageur Country ATV trail system, the
   Prospectors Trail, and the David Dill-Taconite and David-Dill
   Arrowhead state trails. Mapped proposed mileage included in this
   inventory totals 121.6 miles, all located in DNR Region 2."
   Source: https://files.dnr.state.mn.us/input/mgmtplans/ohv/plans/strategic/atv-strategic-master-plan.pdf.
   The plan does not break out mileage per route and publishes no
   route GIS. OVERLAP FLAG: the David Dill/Arrowhead State Trail
   runs Tower–Ely along the former DM&IR grade — inside the
   corridor polygon; an ATV addition there would put motorized use
   on the corridor's high dry ground at its eastern end. (JUDGMENT:
   the corridor location of the David Dill additions is inferred
   from the state trail's known Tower–Ely alignment, not from a
   proposed-route map — no such map is published.)
3. **Quad Cities ATV Club GIA proposal (2024)** — 31.1 mi existing
   corridor open to ATV use + 2.2 mi existing corridor with new ATV
   use (5 segments: Quad Cities Spur South, 2× Spur North, Big
   Aspen Trail Complex, Pfeiffer Area connection); connects
   Eveleth/Virginia to the USFS Big Aspen system, Pfeiffer Lake,
   ultimately the Voyageur Country system. Proposer: Quad Cities
   ATV Club; sponsor St. Louis County; comments through July 15,
   2024. Source: DNR OHV GIA proposal (2024). Status: the live
   service carries 75 "Quad Cities" features and 30 "Big Aspen"
   features; 14.22 miles of Quad Cities and 23.14 miles of Big
   Aspen designated trails lie inside the corridor polygon — but
   the service does not label proposal origin, so the proposal's
   segments cannot be separated from the designated system
   segment-by-segment. The proposal is consistent with the
   designated mileage inside the corridor; designation of its
   specific segments is not separately confirmed.

#### Outside the corridor (checked, not in the corridor)

- **Seven Beavers Connector** — 3.5 mi, ~14 mi SE of Hoyt Lakes,
  St. Louis County; sponsor St. Louis County, maintainer Ranger
  Snowmobile/ATV Club, ATV+OHM, follows an existing
  forest-management/snowmobile corridor, links the East Range
  multi-use system + Seven Beavers bridge. DNR news release Feb 17,
  2026; public comment Feb 17–Mar 18, 2026 (23 comments). Map is a
  DNR GeoPDF (Nov 18, 2025):
  https://files.dnr.state.mn.us/input/mgmtplans/ohv/plans/seven-beavers-proposal-map.pdf.
  18.15 mi from the corridor polygon (nearest corridor point
  −92.066, 47.7585). NOT in the DNR OHV service (trail_name LIKE
  '%SEVEN%' returns 0) — still proposed; designation decision not
  confirmed (comment-summary PDF 404'd). No GIS — pinpoint only.
- **Twig Area Trail Riders EAW** — ~509.8 mi total (437.1 preferred
  + 72.7 alternate) across Carlton + St. Louis counties; proposer
  Twig Area Trail Riders, RGU DNR Environmental Review Unit; EAW
  published Sept 1, 2026, comments through Oct 1, 2026. Cat 1
  existing roads 298.4 mi (no improvements); Cat 2 existing
  trails/roads needing improvements 192.1 mi; Cat 3 NEW trail
  construction only 19.3 mi. Areas: Brookston Loops, Canyon to
  Cotton, Lumberjack to Brookston, Taft to Canyon. All named places
  test outside the corridor (northernmost, Canyon/Cotton, just south
  of the boundary). No GeoPDF viewports in the EAW PDF. Source:
  https://www.dnr.state.mn.us/input/environmentalreview/twig-area-trail.html;
  EAW PDF https://files.dnr.state.mn.us/input/environmentalreview/twig-area-trail/2026-08-13-tatr-eaw.pdf.
  Master-plan figure (Mar 2025) was ~229 mi — the system grew by
  the Aug 2026 EAW.
- **Voyageur Country ATV Phase 2** — up to 125 additional miles (39
  existing + 78 existing-with-improvements + 8 new), Koochiching +
  St. Louis counties, connecting to International Falls, Littlefork,
  East Koochiching, Rainy Lake, NW St. Louis County; EAW with DNR
  Record of Decision (no EIS) — "can proceed to permitting and
  approvals". Source: https://www.dnr.state.mn.us/input/environmentalreview/voyageur-country-trail-expansion.html.
  Existing system in the live file: 118 features, bbox lon −92.94
  to −92.484, lat 48.01 to 48.317 — does NOT intersect the corridor.
  Master plan (Mar 2025): ~29 mi planned, two-phase addition,
  Phase 1 in planning/permitting, Phase 2 decision expected April
  2025. Related: Blue Ox Connection ATV Trail (LCCMR 2027 proposal
  2027-552, Voyageur Country ATV, $100k, planning/engineering for
  ~4.6 mi Ericsburg→Blue Ox State Trail, Koochiching County,
  completion Oct 31, 2028). Voyageur Country ATV Master Plan (2018)
  proposes ~538 miles in phases.
- **Ice Cracking ATV Trail** — ~57 mi existing roads/trails, Two
  Inlets State Forest → White Earth State Forest, Becker County;
  proposer Woods and Wheels ATV Club, sponsor Becker County;
  comments through Nov 13, 2026; no new construction. Outside the
  corridor (Becker County, west). Source: DNR OHV GIA proposal,
  Oct 2026.
- **Chatfield Connector** — 22.5 mi, Fillmore County; DNR news
  release Feb 17, 2026; comment period done (25 comments). Outside
  the corridor.
- **Lake of the Woods Connector** (58 mi, Roseau + Lake of the Woods
  counties) and **North Star Connector** (28 mi, Moose River Dike,
  Beltrami County) — proposed OHV GIA trails per the DNR release
  quoted in ATV MN newsletter Jan 17, 2026. NW Minnesota, outside
  the corridor.
- **NE Regional ATV Master Plan** (SEH, Mar 17, 2025, Northeast
  Regional Joint Powers Board) — the systematic club inventory:
  Alborn Dirt Devils ~10 mi (CR 166→Ostman Rd); Head of the Lakes
  ATV Club — future trails near Duluth/Carlton County, mileages
  undefined; Prospector ATV Club — two-phase addition ~57 mi, Phase
  1 completed, Phase 2 in planning/permitting (~45 mi); Ranger
  Snowmobile & ATV Club — ~10 mi planned + managing 11.3 mi Bird
  Lake trail segment, no mandatory EAW; Twig Area Trail Riders
  ~229 mi (Mar 2025 figure); Voyageur Country ATV Club —
  two-phase addition ~29 mi; Wild Country ATV Club (Lake County,
  30-mi Wild Country Trail near Finland/Beaver Bay/Silver Bay — all
  outside the corridor) ~29 mi planned incl. improvements to 25+
  mi existing, "exceeds threshold for mandatory EAW". "The
  remaining seven ATV clubs in the JPB planning area do not have
  new trails or segments that would require environmental review."
  JPB counties: St. Louis, Lake, Koochiching, Carlton (and Cook per
  the plan text). Source: https://www.sehinc.com/hubfs/Website/Online/northeastern-regional-atv-joint-powers-board/2025-03-17-NE-Regional-MasterPlan-Powerpoint.pdf
- **Itasca County (corridor's west end)** — no current proposed ATV
  trail in/around the corridor. The older proposals are now
  designated and in the live service, all outside the corridor
  polygon: Balsam Trail + Big Fork and Balsam (B&B) Connection
  Trail (Balsam Trailblazers ATV Club, 25-mi proposal, Grand Rapids
  Herald-Review 2012, Grand Rapids→Bigfork via George Washington
  State Forest + Chippewa NF); Len Hardy Memorial Trail (Range
  Riders ATV, 9-mi Nashwauk→Alborn-Pengilly GIA proposal, comments
  through July 6, 2020); Wilderness Trail (USFS approved Oct 2021,
  Wilderness Wheelers ATV, Itasca County sponsorship Nov 2021);
  Herb Brandstrom Trail (Swampsiders ATV, Itasca County sponsorship
  per the 2021 annual report); Goodland Trail. Nashwauk, Pengilly,
  Alborn, Bigfork, Marcell, Squaw Lake, Northome all test outside
  the corridor polygon. The 2015 Blue Lake connector (4,100 ft along
  Blue Lake near Nashwauk, Range Riders + Red Rock Riders) is NOT in
  the live service — no record of completion found; outside the
  corridor. Sources: Itasca County Land Department 2021 Annual
  Report; Grand Rapids Herald-Review articles (2012, 2015, 2020).
- **Cook County ATV Club** — no proposed additions found; the club
  is not among the eight named with planned mileage in the NE
  Regional Master Plan inventory (Mar 2025), and the plan states
  the seven clubs not listed have no new trails requiring
  environmental review. (JUDGMENT: the plan's slide text does not
  name the seven, so the Cook County club's membership in that
  group is inferred from its absence from the named list, not
  directly stated.)
- **Superior National Forest** — no specific proposed motorized route
  found in any Superior NF travel-management / NEPA document
  checked. The Superior NF OHM Strategic Master Plan (Dec 2025)
  notes the 2004 forest plans allow a maximum of 90 additional OHV
  trail miles on Chippewa + Superior NFs combined; no specific new
  Superior NF route is named. The 2006 Cloquet Valley State Forest
  74-mi ATV/OHM proposal (Island Lake→Pequaywan Lake, ~63 mi
  existing + 11 mi new) is old history, south of the corridor; the
  Apr 2026 press claim of a "new Pequaywan ATV club adding 500
  miles" is unverified — no EAW or DNR proposal found (Pequaywan
  Area Trail Blazers is a snowmobile club; "Pequaywan" returns 0
  hits in the live OHV service).
- **DNR state-forest OHV planning**
  (https://www.dnr.state.mn.us/input/mgmtplans/ohv/designation/revisions.html)
  — corridor forests Bear Island, Burntside, Insula Lake, Lake
  Isabella, Lake Jeanette, Sturgeon River + scattered northern St.
  Louis County lands had a trail-revision process with comment
  period ended Oct 11, 2018 (historic, designations made by
  Commissioner's Order); no live proposal for those forests. The
  only current items on the page are outside the corridor (Zumbro
  Bottoms, Wabasha County; Solana, Aitkin County; Cloquet
  Valley/Riverlands, St. Louis/Carlton counties).
- **Snowmobile** — no proposed NEW snowmobile trail found in/around
  the corridor via DNR news (2025–2026), the OHV public-input page,
  or club checks (Ely Igloo, Vermilion Penguins, Cook Timberwolves,
  Babbitt ATV & Snowmobile, Finland Snowmobile & ATV, Lutsen Trail
  Breakers, Silver Trail Riders, TrailHawks, Voyageur Snowmobile
  Club). The snowmobile GIA program's 2026–27 work is
  administrative (hybrid grant model, 15-member workgroup May–Sept
  2026). The Seven Beavers connector route follows an existing
  snowmobile-use corridor but is an ATV/OHM designation, not a new
  snowmobile trail.
- **Negative (checked, nothing found):** DNR OHV GIA proposals
  2024–2026 (news releases + public-input page); DNR
  environmental-review pages (Prospectors, Twig, Voyageur Country);
  DNR ATV/OHM/ORV Strategic Master Plans (Dec 2025); NE Regional
  ATV Master Plan (Mar 2025); DNR state-forest OHV planning page;
  Itasca County Land Department annual report; Superior NF
  travel-management / NEPA documents; club sites for the corridor
  clubs above. Exact queries: DNR service query trail_name LIKE
  '%SEVEN%' → 0; live-file name checks Balsam / Len Hardy /
  Wilderness / Brandstrom / Goodland / Alborn / Voyageur Country →
  present (designated), Blue Lake / Pequaywan → absent.

## Bike trails (added 2026-11-18, Paul)

- **What:** one layer, `site/data/bike-trails.geojson`, **437
  features, 745.95 GIS miles, full state** — every DNR state trail
  that allows biking (364 features, 650 GIS miles, 29 named
  trails) plus the Mesabi Trail from OpenStreetMap (73 way
  features, 96.15 GIS miles). Wired in `site/app.js` as id
  `bike`, group "Other trails", right after the snowmobile layer,
  OFF by default and LAZY, orange #ea580c. Pulled 2026-11-18 by
  `scripts/pull_bike_trails.py`; Mesabi geometry harvested by
  `scripts/harvest_mesabi_osm.py`. Counts recomputed from the
  live file 2026-11-18; they match the counts in `site/app.js`
  and `site/data-sources.html` exactly.
- **Sources:**
  - Minnesota DNR State Trails service,
    `trans_state_trails_minnesota/FeatureServer/0`
    (https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_trails_minnesota/FeatureServer/0),
    filter `use_bike = 1`. Live service count 2026-11-18: 978
    total features; 364 with `use_bike = 1`.
  - Mesabi Trail geometry: OpenStreetMap, ways named "Mesabi
    Trail" (highway=cycleway), harvested via Nominatim bounded
    searches along the Grand Rapids–Ely corridor plus the OSM
    API (`/way/{id}/full`), 73 ways, 0 failed.
- **Corridor trails in the layer:** Paul Bunyan State Trail
  (41 features, 99 mi drawn), Heartland State Trail (14, 47
  mi), David Dill–Taconite State Trail (1, 1 mi), Gitchi-Gami
  State Trail (73, 34 mi), Taconite State Trail (2, 5 mi —
  only the bike-flagged pieces; most of the 165-mi Taconite
  carries `use_bike = 0`), Mesabi Trail (73, 96 mi, OSM).
  The DNR's own published figures differ from the drawn miles
  on Paul Bunyan (113 mi published vs 99 mi in the service)
  — the difference is in the service, not a clip: the DNR
  `lengthmile` field sums to 650 mi statewide against
  650 mi drawn, so field and drawn agree.
- **How the layer was decided (interpretation method):** a
  feature is in the layer if and only if the DNR service flags
  it `use_bike = 1`, plus the Mesabi Trail, which is not in the
  DNR service at all (query `trail_name LIKE '%MESABI%'` → 0).
  The popup reads the service's fields as stored (`surfacetyp`,
  `width`, `lengthmile`, the `use_*` flags); the DNR stores a
  missing string as a single space, which the popup trims to
  nothing so no empty row shows. Surfaces in the file: Asphalt
  335, blank 13, Limestone/rock 5, natural unimproved 4,
  Unknown 3, crushed gravel 2, plastic 2.
- **What is NOT in the layer, and why:**
  - Mountain-bike-only singletrack (`use_mntbik = 1` AND
    `use_bike = 0`): 368 features statewide, e.g. the Cuyuna
    Lakes mountain-bike system (35 features). Different use
    class, mostly inside state parks/forests — a second layer
    if Paul wants it, not folded in silently.
  - Blue Ox State Trail (unpaved, motorized; `use_bike = 0`)
    and the "OHV access to Taconite State Trail via USFS Rd
    11404" spur (`use_bike = 0`) — not bike trails in the
    service's terms.
  - C.J. Ramstad / North Shore State Trail (84 features in the
    service) and David Dill–Arrowhead State Trail: both carry
    `use_bike = 0` — hiking/ski and motorized respectively,
    not bike.
  - The on-road bike network (shoulders, bike lanes, county
    bikeways): MnDOT's BIKEWAY FeatureServer
    (`webgis.dot.state.mn.us/65agsf1/rest/services/sdw_trans/BIKEWAY/FeatureServer`)
    answers HTTP 200 + an HTML "Request Rejected" page from
    this environment (support IDs 7888479202558097992 /
    7888479202558098008, checked 2026-11-18) and its MnGeo
    mirror (`trans_bikeway`) is token-gated (499). Same
    WAF-block family as the MnDOT right-of-way service. The
    layer is trails, not the on-road network; re-pull when
    MnDOT access is sorted.
  - Mesabi Trail gaps: 96.15 GIS miles drawn against ~126 mi
    published finished (Greater Minnesota Regional Parks and
    Trails Commission, 2020) to ~145 mi (Trailforks). The
    missing mileage is on-road and shared sections carried
    under road names in OSM, plus stretches not mapped as
    named ways — no road segment was drawn as trail without a
    source. The popup states the gap in full. Unbuilt Mesabi
    segments (Hwy 88–Ely, Aurora–Hoyt Lakes, both funded
    2026) are not drawn either: proposed routes are never
    drawn without GIS.
  - The trail authority (St. Louis & Lake Counties Regional
    Railroad Authority, mesabitrail.com) publishes a paper/PDF
    map only — no GIS download exists to pull from. Pinpoint:
    2026 Mesabi Trail Map, mesabitrail.com/plan-your-trip/
    trail-maps/paper-map-ordering/; Ride with GPS paved routes,
    mesabitrail.com/plan-your-trip/trail-maps/ride-with-gps/.
- **Judgment register:**
  - J1 — Full state, not the 2-mile corridor: follows the
    motorized layers' precedent (Paul, Nov 16, 2026). A
    corridor clip would have reintroduced the clip artifacts
    those layers deliberately removed.
  - J2 — Mesabi geometry from OpenStreetMap, labeled as such
    on every feature (`kind: mesabi-osm`, `source:
    OpenStreetMap`) and in the popup. OSM is the source, not
    the authority; the authority's map is PDF-only and MnDOT's
    bikeways service is blocked. Leaving the Mesabi out would
    have left the layer's most corridor-relevant trail missing
    — the NCT gap line east of Grand Rapids follows the Mesabi
    Trail bike path.
  - J3 — Overpass was NOT used: every Overpass mirror is
    unreachable from here (406 on overpass-api.de and
    kumi.systems, timeouts on private.coffee/nchc, 403
    whitelist-only on openstreetmap.fr). The harvest went
    through Nominatim + the OSM API instead, which is slower
    (73 way fetches) but reachable.
  - J4 — The Mesabi popup carries the Wheel Pass note ($10 /
    3 days, $20 / year, mesabitrail.com) because the pass is
    required to ride it — a use condition, not a data field.

## Roads — road centerlines

- **What:** Public road centerlines for the working extent (needed
  for per-segment road-crossing / access analysis).
- **URL:** https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/trans_road_centerlines_open/FeatureServer
  (layer 0, "Trans Road Centerlines Open")
- **Owner / publisher:** Minnesota Department of Transportation
  road data, served open by MnGeo. The service carries no copyright
  text.
- **Use here:** Stored at `data/access/roads.geojson`, pulled
  2026-11-10 by `scripts/pull_access_layers.py`.

## Corridor clip — site-build view over access + roads (v7)

The working files above are **never cropped**. The site build
(`scripts/build_site_data.py`, contract:
`docs/cartography-notes-2026-11-10.md` Part 1) clips the two
context layers to a corridor around both drawn lines (Itasca
Moraine + Laurentian Lakes): non-road access ±800 m, roads
±1.6 km, cut at vertices with interpolated boundary crossings;
kept runs under 25 m dropped; roads extended ≤250 m to finish
the block; access junction stubs ≤150 m where they reach another
retained line; features crossing the trail kept whole if ≤3 km
(`connector: true`), clipped features flagged `cut: true`. State
forest roads (above) are clipped in the access pass — connector
test included — and then emitted into the **roads** site output
as class **F**.

Road classes are derived at build time: the centreline source's
`cartoclass` is null on all 5,902 features and the service
publishes no coded-value domain for `route_sys`, so the codes
were verified empirically against the road names in the pulled
data (2026-11-10): `03` = "ST HWY …" (184/184), `04` = "CO HWY …"
(county state-aid), `07` = "CO RD …", `08` = township numbered
names, `10` = named municipal streets, `32` = "UNNAMED" (37/37);
null-code features include trunk highways named "STATE 371" etc.
Derivation (`derive_road_class` in the build): codes 01–04 → A;
05/07/10 named → B; 08/13/19/32/other codes and anything unnamed
→ C; null code → name fallback (STATE/ST/MN/US highway → A, other
named → B). The source carries no private-road identifier, so
private lanes are not separately flagged.

## Mile markers — NCTA Minnesota half-mile points (v7)

- **What:** A point every half mile along the Minnesota NCT — the
  **state (NCTA) mileage reckoning**. `index_` flags whole miles
  ("Index") vs half miles ("Interval"); `ident` / `wypnt_id`
  carry the number ("MN-187", "187.5").
- **URL:** https://services2.arcgis.com/UfGVyqUm4GHa2zrj/arcgis/rest/services/mn_halfmile_points/FeatureServer
  (layer 0, "halfmile_mn" — "Mileage Index for the North Country
  Trail in Minnesota"). Same NCTA ArcGIS organisation as the
  official trail line.
- **Owner / publisher:** North Country Trail Association.
- **Use here:** Pulled 2026-11-10 by
  `scripts/pull_mile_markers.py` into
  `data/points/mile-markers.geojson` (244 points in the working
  extent, state miles 120.5–242). Re-pulled statewide 2026-11-16
  (`--statewide`, no clip — Paul: mile markers are statewide):
  1,119 points, state miles 0.5–558.5. The site build keeps only
  points snapping within 250 m of the drawn lines (1,119 retained,
  0 excluded) as `site/data/milemarkers.geojson`, layer "Mile
  markers (state)", default off.
- **⚠ Corrupt attribute columns:** the service's `lat` / `long`
  ATTRIBUTE columns are wrong (the longitude attribute duplicates
  the latitude value). They are never read: the pull requests
  geometry only, with `outSR=4326`, and limits `outFields` to
  `ident,index_,wypnt_id`.
- **Two reckonings:** the state numbers differ from the chapter
  tracker's "NCT Mile Virtual Markers" by roughly 46–48 miles
  over the same ground. Neither is converted into the other
  anywhere; tracker figures are labelled "chapter tracker miles"
  wherever shown.

## Chainage points (v7)

Not an external source: `site/data/chainage.geojson` is computed
by the site build from the chapter's own stretch chainages — a
point every 5 miles from the depicted chain's west end,
interpolated along the stretch geometries (10-mile points
flagged). A relative measure ("miles from the west end"), in
neither mileage reckoning above.

## Reference dataset — Minnesota county boundaries

- **What:** County boundary polygons, used only to determine which
  counties the trail line passes through (and per-county trail
  mileage) for the coverage report in
  `data/parcels/county-coverage.md`. Not a published map layer.
- **URL:** https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/bdry_counties_minnesota/FeatureServer
  (layer 0)
- **Owner / publisher:** MnGeo.

## Leech Lake Reservation — boundary polygon (added 2026-11-11, switched to BIA 2026-11-11)

- **What:** The external boundary of the Leech Lake Reservation
  (Leech Lake Band of Ojibwe), drawn as a separate
  toggleable context layer ("Leech Lake Reservation", off by
  default, lazy like parcels).
- **URL:** https://biamaps.geoplatform.gov/server/rest/services/DivLTR/BIA_AIAN_National_LAR/FeatureServer
  (layer 0, "BIA AIAN National LAR", queried
  `LARID = 'LAR0033'`, outSR 4326, GeoJSON)
- **Owner / publisher:** Bureau of Indian Affairs, American
  Indian and Alaska Native Land Area Representation (AIAN-LAR).
  Public federal data; no licence restriction.
- **Vintage:** AIAN-LAR national dataset, feature LAR0033
  "Leech Lake", fetched 2026-11-11. Three polygons, 3,999
  vertices; geometry-measured area 823,249 ac (UTM 15N).
  BIA's own GISACRES attribute (1,794,106) contradicts its
  own geometry and is NOT used.
- **Why this source, and what lost:** the layer STARTED on the
  Census TIGER/Line AIANNH polygon (GEOID 1940R, BAS 2026;
  single polygon, 9,685 vertices, published total 838,631 ac;
  identical across Census 2020 / ACS 2025 / BAS 2026). It was
  switched to BIA the same day because the Census polygon
  stitches its southern lobe to the main body with a bridge
  ~5 m wide at (-94.377, 47.223), which renders as the
  boundary crossing over itself. BIA draws the lobe as a
  separate polygon with a ~210 m gap — no pinch — while the
  boundary LINES agree closely (median 19 m near the neck;
  37 m overall). BIA is coarser and has no interior hole:
  the Census hole (~10,158 ac) sits outside BIA's polygons
  (only 78 ac of it falls inside BIA), so nothing is wrongly
  added. **PAD-US** was not fetched separately: its tribal
  lands derive from BIA AIAN-LAR, so it would duplicate that
  geometry. The Minnesota Geospatial Commons / LCC-GIS
  reservation dataset (`amerind2010`) is 2010 TIGER-derived
  and stale — not used. The Census **off-reservation trust
  land** feature for Leech Lake (GEOID 1940T, 0.05 sq km) is
  deliberately excluded: this layer is the reservation itself.
  Neither source came from the tribe itself: both are federal
  publications. The Census file is preserved in git history
  (commit 91e3468) if the switch ever needs reversing.
- **Trail overlap (measured 2026-11-11, UTM 15N against the
  depicted chain):** 2 mi inside the reservation, all of
  it on **Chip-12** (2 of its 4 mi); GAP-W and every
  other section are outside. Census re-measures 2 mi by
  the same method. The official
  line gives 2 mi. **White Earth check (CORRECTED 2026-11-16):**
  the White Earth Reservation touches the map extent's western
  margin and no *depicted chapter* trail mileage falls inside
  it (no miles on the chapter line) — but the statewide NCT line
  and the chapter line both put **19 mi inside White Earth,
  all LLC chapter** (geodesic and UTM 15N agreeing), and the
  reservation survey independently measured the same 19 mi.
  The boundary layer is now built — see the White Earth section
  below.
- **Use here:** Full unclipped geometry, pulled by
  `scripts/pull_leech_lake_reservation.py` into
  `data/native-nations/leech-lake-reservation.geojson` (working)
  and `site/data/leech-lake-reservation.geojson` (site copy,
  lazy). The popup and the Sources card carry the
  line: *the federal reservation boundary as published — not
  a legal survey.* Tribal management/forestry data is NOT in
  scope here — that stays relationship-only, per the
  project's standing line.


## White Earth Reservation — boundary polygon (added 2026-11-16)

- **What:** The external boundary of the White Earth Reservation
  (White Earth Nation), drawn as a separate toggleable context
  layer ("White Earth Reservation", off by default, lazy like
  parcels) — the second crossing reservation after Leech Lake.
  The trail crosses White Earth, ~19 mi, and it was the only
  crossing reservation without a boundary layer in the viewer.
- **URL:** https://biamaps.geoplatform.gov/server/rest/services/DivLTR/BIA_AIAN_National_LAR/FeatureServer
  (layer 0, "BIA AIAN National LAR", queried
  `LARID = 'LAR0051'`, outSR 4326, GeoJSON)
- **Owner / publisher:** Bureau of Indian Affairs, American
  Indian and Alaska Native Land Area Representation (AIAN-LAR).
  Public federal data; no licence restriction.
- **Vintage:** AIAN-LAR national dataset, feature LAR0051
  "White Earth", fetched 2026-11-16. MultiPolygon, 39 polygons,
  1,337 vertices: one large main body (745,723 ac) plus 38 small
  trust parcels inside/near it; geometry-measured area 748,098 ac
  (UTM 15N). BIA's own GISACRES attribute (1,621,000.16) contradicts
  its own geometry by the same ~2.17x ratio as Leech Lake's
  (1,794,106 vs 823,249 measured) and is NOT used.
- **Why this source:** the same source and pull pattern as the
  Leech Lake layer — the authoritative published federal boundary.
  No per-reservation tribal map product exists (see
  docs/reservation-maps-survey-2026-11-16.md): no public
  georeferenced tribal map was found for White Earth (or Leech
  Lake), so the boundary is the layer, not a map sheet.
- **Trail overlap (measured 2026-11-16, geodesic + UTM 15N
  agreeing, against both the statewide NCT line and the chapter
  line):** 19 mi inside the reservation, all of it LLC chapter
  (Connector, Foot Path). The reservation survey independently
  measured the same 19 mi. The largest single feature is
  10 mi of a 10-mi feature. The chapter's stretches file does
  not cover the LLC chapter, so no stretch name is recorded.
- **Use here:** Full unclipped geometry, pulled by
  `scripts/pull_white_earth_reservation.py` into
  `data/native-nations/white-earth-reservation.geojson` (working)
  and `site/data/white-earth-reservation.geojson` (site copy,
  lazy); the raw BIA fetch is kept at
  `data/native-nations/bia-white-earth-lar0051.geojson`. The popup
  and the Sources card carry the line: *the federal reservation
  boundary as published — not a legal survey.* Tribal
  management/forestry data is NOT in scope here — that stays
  relationship-only, per the project's standing line.


## Forest health + blowdown — DNR survey 2025 (added 2026-11-13)

- **What:** Minnesota DNR forest health survey polygons in the
  chapter corridor — damage mapped in the survey year (2025),
  not current condition.
- **URL:** https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_forest_health_survey_2025/FeatureServer/0
- **Owner / publisher:** Minnesota DNR, Division of Forestry —
  Forest Health program. Public state data.
- **Vintage:** 2025 survey, pulled 2026-11-13 by
  `working/land-layers/pull_land_layers.py`. 123 polygons,
  10,084.3 ac. Agents: eastern larch beetle 41, wind-tornado
  35, flooding-high water 13, unknown bark beetle 10, unknown 9,
  aspen decline 6, hardwood decline 5, larch casebearer 3, forest
  tent caterpillar 1. Damage: Mortality 70, Broken/Uprooted 35,
  Crown Dieback 10. `category` and `pct_affected` are empty on
  every feature in the source and are not shown; `notes` is
  sporadic.
- **Envelope:** lon -95.6 to -94.3, lat 46.7 to 47.35
  (EPSG:4326), the chapter corridor.
- **Quirks (do not re-derive):** the DNR service is in native SR
  UTM 26915 and `f=geojson` vs `f=json` apply the envelope
  differently, so the pull fetched `f=json` in native SR and
  reprojected with a hand-written stdlib Snyder inverse
  transverse Mercator (validated against the service's own
  geojson — max vertex distance 1.11 m, the NAD83→WGS84 datum
  shift). Pagination used `returnIdsOnly` + independent
  OID-range chunks (`resultOffset` overlaps on this service).
  Do NOT use `env_fast_forest_disturbances` (stale, max 2020).
  Re-pull annually.
- **Use here:** `site/data/forest-health-2025.geojson`, layer
  "foresthealth", OFF by default, LAZY, group "The land".
  Popup: agent, damage, host, year, acres, notes when present.

## Invasive species sightings — DNR terrestrial observations (added 2026-11-13)

- **What:** Minnesota DNR invasive terrestrial observations —
  REPORTED sightings (observer reports, largely iNaturalist),
  not a systematic survey. A species missing from this map is
  not proof it is absent on the ground.
- **URL:** https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_invasive_terrestrial_obs/FeatureServer
  (Layer 1 Plants + Layer 3 emerald ash borer)
- **Owner / publisher:** Minnesota DNR. Public state data.
- **Vintage:** pulled 2026-11-13 by
  `working/land-layers/pull_land_layers.py`. 5,551 points:
  Plants 5,550 (spotted knapweed 3,263; common tansy 2,158;
  leafy spurge 62; common + European buckthorn 61; garlic
  mustard 6) + one emerald ash borer (2023-11-13, Jonathan
  Osthus / MN Dept of Agriculture, Cass County). Observed
  2000-08-14 to 2026-08-13, no missing dates. `reporter` and
  `record_source` are the provenance fields shown in the popup.
- **Envelope:** lon -95.6 to -94.3, lat 46.7 to 47.35
  (EPSG:4326), the chapter corridor.
- **Quirks:** same pagination / reprojection notes as the forest
  health pull (OID-range chunks; `f=json` in native SR +
  stdlib reprojection). The USFS
  EDW_InvasiveSpecies_01 service graded C — do not use.
- **Use here:** `site/data/invasive-sightings.geojson`, layer
  "invasives", OFF by default, LAZY, canvas-rendered dots
  (5,551 points), group "The land". Popup: species, scientific
  name, observed date, county, reporter, record source, plus
  the observer-bias note.

## Chippewa Forest Plan management areas — 2004 plan (added 2026-11-13)

- **What:** Chippewa National Forest Land Management Plan
  management areas (L2 Management Area only), plan year 2004.
  The plan's desired conditions — not a harvest schedule.
- **URL:** https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_LandManagementPlanning_01/MapServer
  (planning page: https://www.fs.usda.gov/r09/chippewa/planning)
- **Owner / publisher:** USDA Forest Service, Chippewa National
  Forest. Public federal data.
- **Vintage:** plan year 2004 for all 35 polygons; 467,512.7
  gis_acres. Codes: UB 6, CRNA 1, RU 4, RNA 1, RE 7, LR 6,
  WATER 6, GF 3, EF 1. The `summary` line on each area is
  condensed from the plan's Chapter 3 (real PDF
  https://www.fs.usda.gov/media/239376, saved in
  `working/land-layers/`). `service_description` is "Not
  defined" in the service and is never shown.
  `rev_date` 20240920.
- **Envelope:** lon -95.6 to -94.3, lat 46.7 to 47.35
  (EPSG:4326). EDW polygons are whole management areas and
  spill east to ~-93.9, same as the existing logging layers.
  EDW native SR is 4269 (lon/lat) — passes through as lon/lat.
- **Use here:** `site/data/chippewa-plan-areas.geojson`, layer
  "chippewa-plan", OFF by default, LAZY, group "The land".
  Popup: management-area name, code, plan year, acres, summary.
  Honest label: "Chippewa Forest Plan management areas (2004)".

## Timber sales — statewide along the trail (added 2026-11-16)

- **What:** timber sales AND planned stand exams along the
  whole Minnesota NCT — the chapter logging layers (Cass /
  Hubbard / Becker / Clearwater + Chippewa EDW, corridor clip
  lon -95.6 to -93.9) extended statewide. 1,551 features,
  91,454.3 ac, in a 2-mile corridor around the statewide trail
  line (348 features, 566 mi); a feature counts when its
  polygon intersects the buffer. Counties crossed: Wilkin,
  Otter Tail, Becker, Hubbard, Clearwater, Cass, Itasca,
  St. Louis, Carlton, Lake, Cook (11).
- **The split (Paul, Nov 16, 2026 — planned first):** every
  feature carries a `timing` property, past | planned, decided
  in the DATA by `scripts/add_timber_timing.py`. PLANNED (1,190
  features, 27,290.4 ac) is everything not yet cut: both DNR
  stand-exam programs (10-yr 1,077 + annual 89) plus 24
  upcoming county sales / appraisals. PAST (361 features,
  64,163.8 ac) is sold / completed sales: county-sale 317 +
  USFS EDW 44. Rule: exams are always planned (an exam is not
  a sale — DNR's caveat is that not every examined stand
  becomes one); Hubbard's own sold / upcoming status is
  authoritative; Becker's Closed field is the past / future
  signal where filled; otherwise a recorded sale / award year
  up to now means past, and a year-null feature with no status
  signal is planned (cannot confirm a cut happened). 23
  features were decided by that fallback and are counted as
  ambiguous in the script output (Cass year-null 8, Becker
  closed-null + year-null 14, EDW MARBLES year-null 1) — all
  placed in planned. Paul's ruling: the planned set is the
  watch list, the harvests to track so a cut doesn't reach the
  trail; past sales are context, secondary.
- **Programs:** county-sale 340 (Cass 271, Becker 49,
  Hubbard 20) | usfs-edw-sale 45 (Chippewa 35, Superior 10) |
  dnr-stand-exam-10yr 1,077 (se_year 2021–2030) |
  dnr-stand-exam-annual 89 (plan_year 2027 for 85).
  By region (all programs): west 681 | central 547 |
  arrowhead 323. Far west is empty as Paul guessed — Wilkin 0
  features, Otter Tail 7 exams and 0 sales — but the west
  region holds 69 sales, all in Becker + Hubbard where the
  trail enters the forest.
- **Coverage by county (recomputed 2026-11-18 from
  `site/data/timber-sales-minnesota.geojson`):** past |
  planned — Becker 34 | 121; Carlton 0 | 24; Cass 298 | 156;
  Clearwater 0 | 35; Cook 0 | 79; Hubbard 20 | 464; Itasca 0 |
  93; Lake 3 | 22; Otter Tail 0 | 7; St. Louis 6 | 189;
  Wilkin 0 | 0. Totals 361 past / 1,190 planned.
- **Coverage by chapter (Nov 18, 2026):** Star of the North
  (Cass + Hubbard) is well covered both ways — 318 past (283
  county sales + 35 USFS EDW) and 620 planned (561 10-yr exams
  + 51 annual exams + 8 county sales); Cass holds the deepest
  past coverage in the file (298) and Hubbard the largest
  planned count (464). Arrowhead (Itasca, St. Louis, Lake,
  Cook) has planned coverage but past sales are thin — 9 past
  (St. Louis 6, Lake 3, Itasca 0, Cook 0) against 383 planned,
  of which 382 are DNR stand exams and 1 is a USFS EDW project
  area (MARBLES, year-null, placed in planned by the fallback
  rule). The thin past is a source gap, not a trail gap: no DNR
  sold-sale polygon service exists, St. Louis County's service
  returns 499 Token Required, and no timber-sale GIS service
  was found for Itasca, Lake, Cook, Wilkin, or Otter Tail (see
  Gaps below). Private land is the standing blind spot; tribal
  lands have no public data.
- **Naming (Paul, Nov 18, 2026):** the planned set is labeled
  "Examined for future sale" in the viewer, not "Planned
  harvests" and not "future parcels" — 1,166 of the 1,190
  planned features (98%) are DNR stand exams, and an exam is
  not a guaranteed sale. The other 24 are upcoming county
  sales / appraisals (23) and one USFS EDW project area. The
  layer id stays `logplanned`; the `timing` property stays
  past | planned.
- **Red for identified sales (Paul, Nov 18, 2026):** the 24
  upcoming-sale features (23 county-sale + 1 USFS EDW, all
  timing planned) fill solid red (#e11d48, edge #9f1239) in the
  viewer, against the lime examined-for-future-sale fill and the
  dashed lime past outline — so what has actually been identified
  for sale reads at a glance. The rule keys off program +
  timing in `timberStyle`; no data property was added.
- **Arrowhead reroute corridor (Paul, Nov 19, 2026 — for the
  Arrowhead demo that evening):** timber BOTH past and
  examined-for-future, solid red fill, everything inside the
  2004 reroute corridor polygon
  (`site/data/arrowhead-reroute-polygon.geojson`, 1,243.4 sq mi).
  **Clip rule:** a feature counts when its polygon INTERSECTS
  the corridor polygon (any overlap), computed in Python with
  Shapely from the same file the viewer draws — the `region`
  property is NOT the clip (96 of the 219 flagged features
  carry region "central": Cass County, where the corridor's
  western end reaches). **Counts (Nov 19, 2026): 219 features —
  planned 184 / past 35.** By county: St. Louis 101 (98 planned
  + 3 past), Cass 60 (31 + 29), Itasca 36 (all planned), Lake 22
  (19 + 3); Cook 0, Carlton 0. By program: DNR 10-yr exams 160,
  DNR annual exams 24, county sales 23, USFS EDW 12. **Cook is
  zero by geography, not a data gap:** all 79 Cook features lie
  east of the corridor (nearest 0.59° of longitude away, up the
  Gunflint) — the corridor polygon ends at lon -91.371. **Past
  inside the corridor is thin, and the thinness is a source gap:**
  the 35 past features are 29 Cass County sales + 6 USFS EDW
  historic sales (3 Lake, 3 St. Louis); no DNR past sale exists
  anywhere in the file, because no DNR sold-sale polygon service
  exists (see Gaps below), and Itasca past is 0 for the same
  reason. **Style:** `timberStyle` in `site/app.js` returns
  solid red (#e11d48, fillOpacity 1, edge #9f1239) for any
  feature carrying `in_reroute_polygon`, in BOTH toggles — the
  corridor rule beats the timing rules, so a past sale in the
  polygon is solid red too, while an upcoming sale outside the
  polygon stays at 0.55. The flag is set by
  `scripts/add_timber_reroute_flag.py` (idempotent; clears the
  flag where a feature no longer intersects) — re-run it after
  any re-pull of the statewide timber file, which would wipe the
  flag. Popups name the corridor in a "Corridor" row; the panel
  key under the Planned toggle carries a solid-red row for it.
  Both toggles stay OFF by default.
- **URLs:**
  - USFS EDW Activity Project Areas — Timber Sale, layer 2:
    https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_ActivityProjectAreas_01/MapServer/2
  - MN DNR 10-year Stand Exam List, layer 0:
    https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/biota_dnr_10yr_stand_exam_list/FeatureServer/0
  - MN DNR Annual Stand Exam List (public), layer 0:
    https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/biota_dnr_annual_stand_exam_pub/FeatureServer/0
  - Cass County Forestry Web Map — Timber Sales (Current),
    layer 62:
    https://cassweb.casscountymn.gov/arcgis/rest/services/Forestry_ForestPlan_Base/MapServer/62
  - Hubbard County Timber Sales (sold layer 0 + upcoming
    layer 1):
    https://services.arcgis.com/auNjCUvKlkSqV04X/ArcGIS/rest/services/Hubbard_County_Timber_Sales/FeatureServer
  - Becker County Forestry PreRX Appraisals, layer 0:
    https://gis-server.co.becker.mn.us/arcgis/rest/services/Forestry/PreRX_Appraisals/FeatureServer/0
  - Clearwater County Forestry PreRX Appraisals, layer 0:
    https://map.co.clearwater.mn.us/arcgis/rest/services/Forestry/PreRX_Appraisals/FeatureServer/0
- **Owner / publisher:** USDA Forest Service; Minnesota DNR,
  Division of Forestry; Cass / Hubbard / Becker / Clearwater
  County forestry. All public data.
- **Vintage:** pulled 2026-11-16. Cass sales 2007–2026
  (211 of 271 pre-2020); EDW fy_award 2001–2025; STH se_year
  2021–2030; ASEL plan_year 2027 for 85 of 89. Becker
  county-wide count drifted 139 → 137 between calls
  (live-service drift). Hubbard acres are geometry-derived
  (Shape__Area not in the re-pull's field list; verified
  within ~1% Nov 13).
- **Envelope:** lon -96.04 to -89.89, lat 46.43 to 48.12
  (EPSG:4326).
- **Gaps (stated, not hidden):** no DNR sold-sale polygon
  service exists — DNR actual sales live in the timber sales
  calendar's PDF notices (next corridor-area sales: Backus
  Jan 7, 2027; Park Rapids May 11, 2027). St. Louis County's
  timber-sale service exists but returns 499 Token Required
  (land-department folders gated). Carlton County's services
  exist but all layers return count 0. No timber-sale GIS
  service found for Itasca, Lake, Cook, Wilkin, Otter Tail.
  Private land is the standing blind spot (no permit system
  in Minnesota); tribal lands have no public data.
- **Use here:** `site/data/timber-sales-minnesota.geojson`,
  two toggles off `timing` in subgroup "Timber sales", group
  "The land": layer "logplanned" ("Examined for future sale —
  watch list", OFF by default) and layer "logpast" ("Past timber
  sales", OFF by default, LAZY). Planned draws above past in
  the draw order. Popup first line names seller + timing
  ("Cass County — Planned"); the rows carry unit, source level,
  timing, type, permit (when not already in the unit name),
  acres, year, county, region, prescription, plus program
  extras and a per-program source line.
- **Popup content rule (Paul, Nov 19, 2026 — content only; the
  design pass restyles the look later):** every timber popup
  names (1) the SOURCE level — Federal, State, or County, the
  county named when county; (2) the facts — acres, year,
  permit or identifying code, status where present; (3) a
  human-readable decoding of every code — never a raw code
  unexplained. The county `gis_id` GUID is never shown. The
  decodings, verified Nov 19, 2026: sale_category C/H/P/M —
  FACTS Data Dictionary ("the sale category indicates the
  general type of sale: Historic, TIM Contract, Product Plan,
  Multi Contract"; the dictionary's PURCHASER_NAME note calls
  the second "Contract Sale", so C = Contract sale, H =
  Historic sale, P = Product plan, M = Multi-contract sale);
  land status (DNR 10-year exams) — DNR's own classes (WSU
  SFRMP Table 1.4; STH report Table 3: Trust = School trust
  land, U Trust = University trust land, Acquired = Acquired
  land, ConCon = Consolidated conservation land, Volstead =
  Volstead land); SFRMP plan code — DNR Section Forest Resource
  Management Plan areas (STH report Fig. 4; MDLP = Minnesota
  Drift and Lake Plains, NSU = Northern Superior Uplands, WSU =
  Western Superior Uplands, NMOP = Northern Minnesota and
  Ontario Peatlands, MNIAM = Minnesota and Northeast Iowa
  Moraines). The DNR services carry no coded-value domains for
  any of these fields (checked Nov 19 on the 10-year exam
  service and the EDW service), so the decoding lives in
  `site/app.js` (`SALE_CATEGORY_LABELS`,
  `DNR_LAND_STATUS_LABELS`, `SFRMP_NAMES`) and an unknown code
  is omitted from the popup, never shown raw. Timing is decoded
  in the popup ("Examined for future sale", "Identified for
  sale", "Past — sold / completed") — the raw `timing` value
  never appears.
- **Reading the map (Paul, Nov 16, 2026 — past / future only):
  ** one lime (#65a30d, edge #3f6212) for every seller — Paul
  corrected the first version, which colored sellers apart:
  the map shows timing only. The lime replaced an amber
  (#d97706) the same day Paul reported the planned fills and
  the trail were nearly the same color: the trail's adopted
  stretches are amber #e08214, and the near-Border-Route trail
  is #d97706. FILL is the timing — a solid fill
  is planned (near-term year >= 2024 fills stronger); past is
  the same lime as a dashed outline with only a faint fill
  (fillOpacity 0.10, dash "5 4"), so timing reads without
  relying on color — except inside the Arrowhead reroute
  corridor, where past AND planned both fill solid red (see the
  corridor bullet above). The key lives in two places: a panel key
  under the Planned toggle (two rows, the two fills) and a
  "Timber sales" section in the map legend; the two toggles'
  swatches are the same solid lime (the past swatch faded to
  0.45 opacity). The seller is named in each popup's first line
  ("Cass County — Planned"), not by color. The old per-county
  sale layers (logcass, logedw, loghubbard, logbecker,
  logclearwater) were removed from the panel the same day — the
  statewide file already contains their polygons within the
  2-mile corridor, so they double-drew; the files stay on disk.
  The one Clearwater appraisal in the old chapter file sits
  MORE than 2 miles from the trail, so it is in neither the
  statewide file nor the panel. "Cass forest stands" (logfim,
  inventory, not a sale) stays, relabeled "Cass forest stands
  (inventory)". The GeoPDF export (`site/export.js`) still draws
  the old per-county layers from its own tables — harmonizing
  the export with the statewide layer is a follow-up, not done
  here.
- **Refresh:** quarterly (county auctions quarterly; EDW
  irregular; STH / ASEL annual). Re-run
  `scripts/pull_timber_sales_statewide.py`, then
  `scripts/add_timber_timing.py`. Full pull log:
  `working/timber-statewide/pull-log-2026-11-16.md`.


## Wetlands (NWI) — classified for trail routing (added 2026-11-18, Paul)

- **What:** the USFWS National Wetlands Inventory along the whole
  Minnesota NCT, classified GO / MAYBE / NO-GO for trail routing.
  **91,479 polygons, 321,582.9 ac**, in the same 2-mile corridor
  around the statewide trail line as the timber layer (348
  features, 566 mi); a wetland counts when its polygon
  intersects the buffer. By rating: **MAYBE 85,155 (181,967.4 ac)
  / NO-GO 6,324 (139,615.5 ac)**. There are NO GO features in the
  file: GO is absence of a polygon (rule W1 below). By rule:
  W6-analog 38,601 (116,213.0 ac), W6 32,310 (40,079.2 ac),
  W5 5,778 (8,122.3 ac), W7 5,318 (11,461.5 ac), W3 5,312
  (135,971.9 ac), W8 1,898 (3,740.2 ac), W9-analog 1,683
  (4,104.6 ac), W9 510 (856.1 ac), W4 69 (250.0 ac),
  UNCLASSIFIED 0. By county: Cass 18,172; Hubbard 12,295;
  St. Louis 10,687; Otter Tail 10,129; Becker 9,818; Cook 8,521;
  Itasca 8,267; Lake 7,337; Clearwater 3,173; Wilkin 1,471;
  Carlton 811; county null 798 (see open gaps). By region: west
  36,886; arrowhead 27,356; central 26,439; other 798.
- **Source:** USFWS National Wetlands Inventory, national service
  as republished on ArcGIS Online:
  `https://services.arcgis.com/P3ePLMYs2RVChkJx/ArcGIS/rest/services/USA_Wetlands/FeatureServer/0`
  (layer 0 "USA_Wetlands", maxRecordCount 1000). Minnesota content
  in the national file is the **DNR June 2019 update** delivered to
  FWS. Per-polygon vintage is NOT exposed by the service — recorded
  as a limit. Pulled 2026-11-18 by
  `scripts/pull_nwi_corridor.py` (run log
  `working/nwi/pull-run-2026-11-18b.log`; raw fetch
  `working/nwi/raw-nwi.geojson`, 100,829 unique features).
- **Service substitutions (verified live 2026-11-18):** the brief's
  URL `https://www.fws.gov/wetlands/arcgis/rest/services/Wetlands/MapServer`
  returns **404** — the service moved to ArcGIS Online (the URL
  above). The DNR's own updated-NWI service
  (`enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_wetlands_nwi/MapServer`)
  returns **499 Token Required** — not publicly queryable. The
  research report's R4b citation (Wetlands_RLIS FeatureServer) is
  WRONG — it is Portland Metro RLIS (Oregon State Plane North,
  wkid 2913); it returns 0 features in Minnesota. Do not use it.
  `inSR=4326` is REQUIRED on the USA_Wetlands service — envelope
  queries without it fail with 400.
- **Pull method:** the corridor (lon -96.7587..-89.8911, lat
  46.2245..48.1311) was cut into 56 cells of 0.25°; each cell was
  queried by geometry POST (the cell's intersection with the
  corridor buffer, simplified 0.002°, widened 0.5 km — a superset;
  the exact clip happens in Python), rings in ArcGIS JSON format
  (exterior clockwise, holes counter-clockwise), `resultOffset`
  pagination 1,000/page ordered by OBJECTID, with a
  `returnCountOnly` cross-check per cell (every cell's fetched
  count matched its service count). Dedupe by OBJECTID across
  cells: **100,829 unique features**. An earlier attempt that
  fetched by 500-id IN lists failed on chunk 1 with HTTP 404 (URL
  too long for this service) — the geometry-POST rewrite replaced
  it. Clip to the exact corridor in Python: 89,366 polygons kept;
  11,462 fell outside the corridor (the query geometry was a
  widened superset), 1 invalid geometry and 1 unparsed code
  skipped. Dissolve: touching polygons with the same (rating,
  Cowardin code) merged into connected components, exploded —
  91,479 output features. Simplification: maxAllowableOffset
  0.0002 (~22 m) + geometryPrecision 5, measured on a 200-feature
  Itasca sample (raw 1,614,232 bytes → 51,953 bytes, 0 empty
  geometries, smallest polygon 856 m² intact); coordinates rounded
  to 4 decimals. File: `site/data/wetlands-nwi-minnesota.geojson`,
  **50,468,829 bytes**.
- **Classification — the interpretation method (Paul, Nov 18, 2026;
  full text in `~/workspace/research_notes/nwi-wetland-trail-classification-20261118-1744/report.md`
  and the classification page artifact
  "Wetland and Soil Classification for Trail Routing"). NO published
  Cowardin→GO/MAYBE/NO-GO matrix exists — this classification is a
  flagged synthesis, and every judgment stays labeled as judgment.
  Apply in order; first rule that fires wins:**
  - W1 — No polygon → GO (screening only). Judgment J1: GO as
    absence is the chapter's definition.
  - W2 — Overlay: overlaps DNR public waters, a calcareous fen,
    or a Minnesota Biological Survey rare natural community →
    NO-GO pending agency advice, regardless of code. **NOT APPLIED
    in this build** — NWI alone cannot identify these and the viewer
    has no public-waters / Natural Heritage layer yet (open gap).
  - W3 — Open / permanent water: regime H, Lacustrine UB, or
    PUB/PAB with H → NO-GO. Judgment J2: the categorical H→NO-GO
    is judgment.
  - W4 — Large bog / muskeg complex: PFO2/PFO4/PSS2/3/4 with regime
    B/C → NO-GO for a through-route; MAYBE only for a short, named,
    maintainable spur. Judgment J3: the spur exception and the word
    "large" (no numeric threshold is set). **Build note: no size
    gate is applied** — every bog-class B/C complex is NO-GO for a
    through-route, because no published threshold exists; the size
    question is left to the field/route check.
  - W5 — Semipermanently flooded (regime F) → MAYBE, short narrow
    boardwalk only; >~300 ft of F-regime tread = NO-GO. Judgment
    J4: the 300-ft threshold; the length check is route-level, not
    applied in the layer.
  - W6 — Seasonally flooded/saturated (regime C/E) → MAYBE, bog
    bridge / boardwalk, short crossing only.
  - W7 — Temporarily flooded / saturated (regime A/B) → MAYBE,
    turnpike / puncheon. Judgment J5: rod-sounding field upgrade —
    if a rod meets no resistance, upgrade to NO-GO.
  - W8 — Riverine FIRST (before W3–W7): R2/R3 perennial → NO-GO
    along the channel (a single bridge point is a separate project
    decision); R4/R5 intermittent → MAYBE, bridge/boardwalk at a
    narrow point. Stay ≥25 ft from the stream edge except at the
    crossing.
  - W9 — Modifiers d (partly drained/ditched), f (farmed), x
    (excavated), or Class US / shore → MAYBE, field-check first; do
    NOT downgrade to GO. Judgment J6: the MAYBE placement.
  - W10 — Cumulative length through any MAYBE class on a proposed
    route >~½ mile → NO-GO for the route as drawn. Judgment J7:
    the ½-mile figure; route-level, not applied in the layer.
  - **Combined rules C1–C4** (applied where the two layers are read
    together): C1 stricter governs — a NO-GO from either dataset is
    a NO-GO overall. C2 soil cannot rescue a wetland — a
    Not-limited soil inside any NWI polygon is never GO. C3 NWI
    polygon + hydric major component = highest-confidence wetland;
    hydric soil with no NWI polygon = MAYBE/field-check, never GO;
    NWI polygon on a non-hydric unit still governs. C4 absence from
    BOTH datasets is the only GO (plus a side-hill 3–10% alignment,
    rule S4) — screening only.
  - **Build-time judgments (extensions of the report's register,
    labeled here):** J13 — regime D (Continuously Saturated) is not
    named in the report's rules; 38,601 features (116,213.0 ac, 42%
    of the file) carry it, so it is treated as W6-analog MAYBE (bog
    bridge/boardwalk), the same treatment as C/E. J14 — regime K
    (Artificially Flooded) is not named in the report's rules; 238
    features carry it, treated as W9-analog MAYBE (field-check;
    water level is managed). Both are the chapter's judgment, not a
    published rule. The parser also handles split classes
    (e.g. PFO1/4D) by reading the regime from the END of the full
    code — taking the first '/'-part alone loses the regime (45
    split-class polygons in an Itasca test box came out
    UNCLASSIFIED before the fix) — and regime-less codes (e.g. PUS)
    by parsing against the known class set, so the class letters
    are not misread as a regime.
- **What each feature carries:** `code` (Cowardin), `wetland_type`,
  `system`, `class`, `subclass`, `regime`, `regime_name`,
  `modifier`, `rating` (maybe | nogo), `rule` (short id: W3–W9,
  W6-analog, W9-analog, UNCLASSIFIED), `acres`, `n_polygons`
  (source polygons merged into this feature), `county`, `region`.
  The full rule text (structure + note + judgment tag) is NOT
  repeated per feature — it lives once in `site/app.js`
  (WETLAND_RULES, mirroring RULE_TEXT in
  `scripts/pull_nwi_corridor.py`, also saved as
  `working/nwi/wetland-rules.json`; the two were diffed, 0
  mismatches). Moving that text out of the file cut it from
  82,885,820 bytes to 50,468,829 bytes with identical counts.
- **Dataset limits:** DNR-updated NWI, June 2019. Minimum mapping
  unit 0.5 ac; identification ~90%, classification ~75%; 95% of
  features within ±5.9 m. Intended use 1:12,000 or smaller. NWI is
  a screening layer, not a delineation: field delineation +
  permits before any MAYBE becomes a route. The 1980s file missed
  forested/drier wetlands and had a 1–3 ac minimum — the dense
  small polygons in this pull (sampled min 856 m², median ~7,300
  m²) with forested/shrub types in quantity are consistent with the
  updated file, not the 1980s one.
- **Regulatory gates:** federal Clean Water Act §404, Nationwide
  Permit 42 (2026 reissue, ≤½ acre, pre-construction notification
  required). Minnesota Wetland Conservation Act: avoid → minimize
  → replace; de minimis exemption 400 sq ft / 10,000 sq ft,
  type- and location-dependent — confirm with the local government
  unit. Public waters need a DNR permit (Minn. Stat. 103G);
  WCA exemptions do not apply to calcareous fens (Minn. R.
  8420.0420). Precedent: the NPS Arrowhead reroute left 70 miles
  of black spruce/tamarack swamp unbuilt.
- **Open gaps:** (1) W2 overlay not applied (above). (2) W4 has no
  numeric "large" threshold (above). (3) W5 300-ft and W10 ½-mile
  are route-level checks — they need an actual drawn route, not a
  layer. (4) 798 features have county null / region "other" — their
  centroids fall outside the TIGERweb county polygons (Lake
  Superior / border waters; e.g. L1UBG lake polygons). (5) 1 invalid
  geometry and 1 unparsed Cowardin code were skipped at clip time.
  (6) Do NOT use the county `wetlands.zip` (46.4 MB, 2017 vintage)
  — flagged STALE in the Nov 11 useful-layers doc.
- **Use here:** `site/data/wetlands-nwi-minnesota.geojson`, layer
  "wetlands-nwi" ("Wetlands (NWI) — trail routing", subgroup
  "Wetlands + soils", group "The land", OFF by default, LAZY).
  Style `wetlandStyle`: MAYBE amber fill (#f59e0b, 0.35) with a
  dashed edge, NO-GO solid red fill (#dc2626, 0.45); dissolved
  features are ordered MAYBE then NO-GO so NO-GO draws on top
  where they overlap. Popup `wetlandPopup` shows classification,
  rule + judgment tag, Cowardin code + water regime in words,
  wetland type, system/class, acres, county, region, the rule's
  structure + note, the screening-only caveat, and the W2 gap.
  Z-order: after "easements", before "foresthealth". Panel key
  under the toggle states the two fills + the screening-only line.
  Headless check 2026-11-18: all 9 rule ids render with matching
  styles, K-regime popup names "Artificially flooded", 0 rule-text
  mismatches between the script and app.js.
- **Refresh:** re-run `scripts/pull_nwi_corridor.py` (or
  `--from-raw` to reprocess `working/nwi/raw-nwi.geojson` without
  re-fetching). Full pull log:
  `working/nwi/pull-run-2026-11-18b.log` (+ reprocess log
  `working/nwi/pull-run-2026-11-18c.log`).


## Soils (SSURGO) — classified for trail routing (BLOCKED 2026-11-18, Paul)

- **Status: BLOCKED — NRCS Soil Data Access is down.** The
  tabular REST endpoint
  `https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` returns
  **HTTP 502 Bad Gateway** on repeated checks through the evening
  of 2026-11-18 (3 attempts in a row, plus earlier single checks).
  The alternate host
  `https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest`
  also returns 502, and the spatial WFS
  (`https://sdmdataaccess.nrcs.usda.gov/Spatial/SDMWGS84Geographic.wfs`)
  also returns 502. The failing query is the SDA health check
  `SELECT TOP 1 mukey FROM muaggatt` (POST, JSON). The script
  fails fast with a clear message when SDA is down; re-run it when
  SDA recovers. **No soils layer is wired yet — the viewer carries
  wetlands only until SDA recovers.**
- **What was prepared:** `scripts/pull_ssurgo_corridor.py` is
  written and its classifier unit-tested (6 cases). It adapts
  `site/buildout/build-soils.py` Part A (which proved the SDA
  pattern on 2026-11-13: `SDA_Get_Mukey_from_intersection_with_WktWgs84`,
  `SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84`,
  `mupolygon.mupolygongeo` WKT, `mapunit`, `muaggatt`,
  `component.hydricrating`) to the same 2-mile statewide corridor
  as timber and wetlands (it reuses
  `working/nwi/corridor-2mi.geojson` so all three layers share one
  identical corridor), and classifies per the Nov 18 sweep:
  - S1 backbone: the NRCS **Paths and Trails** rating for the
    dominant component, from `muaggatt.urbrecptdcd` (dominant
    condition) + `urbrecptwta` (weighted-average index) — the rating
    lives directly in muaggatt, so no cointerp dependency for the
    backbone. S2 mapping (JUDGMENT J8 — NRCS publishes a limitation
    rating, not a go/no-go): Not limited → GO; Somewhat limited →
    MAYBE; Very limited → NO-GO.
  - S3 attribute check (can move the S2 rating): (a) drainage
    Poorly/Very poorly drained, or frequent ponding/flooding, or
    depth to saturated zone <1 ft (`muaggatt.wtdepannmin` < 30 cm)
    → NO-GO for ground tread (the <1 ft cut-off is JUDGMENT J9);
    (b) Histosol major component (organic soil) → NO-GO.
    Texture splits S3(c)/(d) are NOT applied as overrides — texture
    never overrides wetness or grade (report §11 summary); drainage
    + slope are carried on the feature so a reader can apply them by
    eye.
  - S4 grade/alignment (TG/TSA from 1-m LiDAR) is NOT computable at
    the map-unit level — it needs the actual trail alignment; it is
    a route-level check, recorded in the popup note (JUDGMENT J10
    in application). S5 IMBA grade maxima NOT used (no empirical
    data cited). S6 hydric MAJOR component → suspected wetland (C3):
    a GO rating is downgraded to MAYBE; the soil rating alone never
    makes it GO (the ≤~10% minor-component figure is JUDGMENT J11).
    S7 frost action, K-factor, T-factor, hydrologic group, Ksat,
    AASHTO/USCS, shrink–swell, depth to bedrock, AWC, pH, EC are
    recorded exclusions (not routing attributes). S8 read at
    component level — the file will carry the dominant rating AND
    % hydric by component, never the map-unit name alone.
  - Limiting reasons: probed opportunistically from `cointerp`
    (rule tree: ruledepth = 0 is the aggregated rating, ruledepth =
    1 rows are the limiting features, `mrulename` LIKE
    '%Paths and Trails%'); if the probe returns nothing the file is
    still written with rating + attributes and reasons = null, and
    the gap is logged.
  - Output (when it runs): `site/data/soils-ssurgo-minnesota.geojson`,
    dissolved by mukey (connected components), simplified ~70–90 m,
    every feature carrying rating (go | maybe | nogo), rule, NRCS
    rating + index, reasons, drainage, hydric %, hydric-major flag,
    slope, flood/pond frequency, depth to water table, map-unit
    name/symbol, acres, county, region. Planned viewer style
    (report J12): Not limited neutral faint, Somewhat limited amber,
    Very limited red; popup shows map-unit name, limiting reason(s)
    + index, drainage class, hydric rating (% hydric), slope.
    Never display a single "GO" colour for a soil without the NWI
    overlay visible at the same time (report §12, rule C4).
- **Fallbacks checked and dead:** the Esri Living Atlas "USA Soils
  Map Units" FeatureServer
  (`https://landscape11.arcgis.com/arcgis/rest/services/USA_Soils_Map_Units/FeatureServer`,
  updated Oct 2025, 173 fields from nine SSURGO tables — it carries
  urbrecptdcd/urbrecptwta) returns **499 Token Required** — not
  publicly queryable. A Web Soil Survey guide PDF fetch from
  nrcs.usda.gov timed out (curl exit 28, 60 s). No working soils
  fallback was found; keep retrying SDA.
- **Do NOT wire as the soils layer:**
  `site/buildout/data/soils-corridor.geojson` — it covers only
  0.5-mi buffers around the two gap lines (western 4,883 +
  arrowhead 2,390 = 7,273 features), has NO Paths and Trails
  rating (the classification backbone), and does not cover the ITM
  chapter or the full corridor. The Nov 18 U of M data-sources
  audit (`docs/uofm-arrowhead-data-sources-audit-2026-11-18.md`)
  says exactly this.
- **Dataset limits (from the Nov 18 sweep):** SSURGO minimum
  delineation 1.4–5.7 ac depending on scale; planning/screening
  only — a "Not limited" unit can contain a wet inclusion under the
  tread and a "Very limited" unit can contain a dry ridge (S8).
  Survey vintage varies by county. Combined rules C1–C4 (see the
  wetlands section above) govern how soils and wetlands are read
  together; the soils file will carry the SOILS rating only.


## Arrowhead campsites — NCTA camping waypoints (added 2026-11-18, Paul)

- **What:** The NCTA public waypoint layer's Camping points for
  the Arrowhead gap (Grand Rapids to Ely), kept where within 2 km
  of the gap line.
- **Source:** Same NCTA public ArcGIS feature service as the
  official line ("North Country Trail (Public)", layer 1 "Point
  Data — Public"), pulled by `scripts/pull_arrowhead_points.py`
  (same envelope + object-id method as `scripts/pull_points.py`).
- **Counts:** 8 Camping points in the gap bbox; **6 kept**
  (Pokegama Dam Recreation Area Campground, Itasca County
  Fairgrounds Campground, "Camping" near Tower, Vermilion Trail
  Park Campground, Gilbert City Campground, "Campsite" near Grand
  Rapids). **2 excluded** as beyond 2 km from the gap line:
  Fall Lake Campground (3.0 km — serves the Ely end from the
  ELY/Border Route side, not the Arrowhead chunk) and "Camping"
  (-92.0865, 47.7919; 4.3 km). Names are carried exactly as
  published, including the two generic ones. Each kept point
  carries `dist_trail_km`.
- **Use here:** `data/points/ncta-points-arrowhead.geojson` →
  `site/data/campsites-arrowhead.geojson` (built by
  `scripts/build_site_data.py`), the "Camping — Arrowhead" layer:
  deep-green discs with a "C", same treatment as the chapter's own
  Camping layer, OFF by default and LAZY.

## Star of the North campsites — NCTA camping waypoints (added 2026-11-18, Paul)

- **What:** The NCTA public waypoint layer's Camping points for
  the Star of the North trail (MN-84 to MN-6 NE of Remer), kept
  where within 2 km of the STN line.
- **Source:** Same NCTA public ArcGIS feature service as the
  official line ("North Country Trail (Public)", layer 1 "Point
  Data — Public"), pulled by `scripts/pull_stn_points.py`
  (same envelope + object-id method as `scripts/pull_points.py`):
  envelope lon −94.30..−93.79, lat 46.97..47.18 over the STN
  line bbox.
- **Counts:** 5 Camping points in the bbox; **4 kept**
  (Campsite, 0.08 km; Crown Lake Campsite, 0.04 km; Mabel Lake
  National Forest Campground, 1.84 km — the chapter's group-camp
  site, 7 miles west of Remer on Hwy 200; Old Pine Campsite,
  0.07 km). **1 excluded** as beyond 2 km from the STN line:
  Hazel Lake Campsite (−94.2873, 46.9987; 7.57 km — west of
  MN-84, it serves the Itasca Moraine side, not the Star of the
  North chunk). Names are carried exactly as published, including
  the generic one ("Campsite"). Each kept point carries
  `dist_trail_km`. Note: all 4 kept points carry no `chapter`
  value in the source (null), so the popup omits the Chapter row
  rather than showing one.
- **Use here:** `data/points/ncta-points-stn.geojson` →
  `site/data/campsites-stn.geojson` (built by
  `scripts/build_site_data.py`), the "Camping — Star of the
  North" layer: deep-green discs with a "C", same treatment as
  the chapter's own Camping layer, OFF by default and LAZY.

## DNR state forest campgrounds — Minnesota DNR inventory (added 2026-11-18, Paul)

- **What:** The Minnesota DNR's state forest campground inventory
  within 2 miles of the statewide trail line — **2 sites**.
- **Source:** Minnesota DNR,
  `struc_state_forest_campgrounds/FeatureServer`, layer 0
  (points), "State Forest Campgrounds And Day Use Areas" —
  enterprise GIS service:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/struc_state_forest_campgrounds/FeatureServer/0.
  Pulled by `scripts/pull_dnr_campgrounds.py` (2026-11-18). DNR
  data used under the Minnesota DNR General Geographic Data
  License Agreement. Graded in
  docs/research-useful-layers-2026-11-11.md §2.1 (Grade A public /
  C management) and in
  docs/uofm-arrowhead-data-sources-audit-2026-11-18.md (verdict:
  Use — authoritative, absent from the viewer).
- **Counts:** 60 features statewide in the service. **2 kept** in
  the 2-mile corridor: McFarland Lake Campground (Campground,
  Grand Portage State Forest, Cook Co., 0.01 km from the trail)
  and Gulch Lake Campground and Day Use Area (State Forest
  Campground and Day Use Area, Paul Bunyan State Forest, Hubbard
  Co., 1.02 km). **6 excluded by site type** — day-use-only
  areas, no camping: Pelican Beach, Shafer Lake, Remote Lake
  Solitude, Dago Lake, Hay Creek, McCormick Lake Day Use Areas.
  **52 excluded by distance** (>2 mi from the trail). Note: the
  Nov 11 note's "6 in the working extent" was an envelope (bbox)
  count, not a corridor count — the corridor count is 2.
- **Method / judgments:** [JUDGMENT] site-type filter — the
  service mixes campgrounds and day-use areas in one layer
  (field `site_type_gdrs`); included 'Campground', 'Horse
  Campground', 'State Forest Campground and Day Use Area';
  excluded 'State Forest Day Use Area' (day use only, no
  camping). Corridor is the 2-mile buffer around
  `site/data/trail-minnesota.geojson`, the same corridor as the
  timber layer and the motorized clip; distance computed in UTM
  15N and recorded as `dist_trail_km`. Fields carried: `name`
  (`facilty_name_gdrs`, as published — note the DNR spelling),
  `site_type`, `state_forest`, `county`, `admin_unit`
  (`pat_admin_unit_gdrs`), `dnr_region`. The service carries NO
  amenity or capacity fields — a DNR state forest campground is
  rustic, first-come, minimal facilities; that note is carried
  on the popup instead of invented fields.
- **Overlap (kept separate, never merged):** Gulch Lake
  Campground and Day Use Area sits 9 m from the chapter's own
  Gulch Lakes Campground (`chapter-places.geojson`) — the same
  site in two managers' records. Both are drawn; the popup states
  the manager. No other DNR campground falls within 100 m of an
  existing campsite point.
- **Not built:** public water accesses
  (`struc_water_access_sites`) — Paul, Nov 18, 2026: no-go; not
  pulled.
- **Use here:** `data/points/dnr-campgrounds.geojson` →
  `site/data/dnr-campgrounds.geojson` (built by
  `scripts/build_site_data.py`), the "DNR state forest
  campgrounds" layer: deep-green discs with a "D" (DNR),
  distinct from the "C" of the NCTA/chapter campsites, OFF by
  default and LAZY.

## Bridge inventory — crossing opportunities (added 2026-11-18, Paul)

- **What:** Existing highway bridges that might carry the trail —
  crossing opportunities, pairing with the right-of-way work
  around the Ely bottleneck. **80 structures**, in two tiers.
- **Source:** FHWA National Bridge Inventory (NBI) 2025,
  all-records delimited file
  (`2025AllRecordsDelimitedAllStates.txt`, from
  `2025allstatesallrecsdel.zip`, 56 MB):
  https://www.fhwa.dot.gov/bridge/nbi/2025allstatesallrecsdel.zip.
  Minnesota (state code 27) = 16,503 records. Pulled by
  `scripts/pull_nbi_bridges.py` (2026-11-18). Code values decoded
  per the FHWA Recording and Coding Guide FHWA-PD-96-001
  (Items 21/22 owner and maintenance, 41 open/posted/closed, 42
  type of service, 43 structure kind).
- **Source substitution — read this before re-pulling:** the
  intended source was the MnDOT bridge inventory `trans-bridges`
  (Minnesota Geospatial Commons; audited in
  docs/uofm-arrowhead-data-sources-audit-2026-11-18.md, verdict:
  Use — the students filtered it to pedestrian/mixed-use only).
  It could NOT be pulled on 2026-11-18: the MnGeo enterprise
  host FeatureServer returns 499 Token Required; the GDRS
  download paths (GeoPackage / shapefile / metadata under
  `resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dot/trans_bridges/`)
  all return 404; MnDOT's own `mndotgis.dot.state.mn.us` is
  unreachable from this VM (connection fails, DNS resolves); no
  ArcGIS Online copy was found; the DNR Bridges Cartegraph
  service (which carries pedestrian-use flags) also 404s —
  apparently retired/moved. NBI is the federal inventory fed by
  the states from their own inspection systems (MnDOT's SIMS for
  Minnesota), so the structures and bridge numbers are the same
  inventory — but it is NOT the MnDOT service. FOLLOW-UP: re-pull
  from `trans-bridges` when MnDOT access is sorted (live browser
  or token); the bridge number is the join key. The all-records
  file is used, not the highway-only file (`MN25.txt`, 13,551
  bridges), because pedestrian-only bridges (service on = 3) are
  non-highway records and are absent from the highway file.
- **Counts:** 16,503 MN records → **13,795 distinct structures**
  (dedupe by `STRUCTURE_NUMBER_008`; one record per structure,
  preferring record type 1, route on the structure — service-on
  is consistent within a structure, verified: 0 of 13,795 carry
  >1 distinct service-on code). **80 kept** in the corridor:
  Tier 1 **30** (28 Highway-pedestrian + 2 Pedestrian-bicycle),
  Tier 2 **50** (Highway within 400 m). By county: Itasca 25,
  St. Louis 24, Otter Tail 18, Becker 4, Cook 3, Cass 2, Lake 2,
  Wilkin 2. Status: 73 open, 7 posted for load; 1 structure
  within the corridor dropped as closed/not-yet-open.
  The two pure pedestrian bridges: 5342 (PEDESTRIAN over US 169,
  Itasca Co., built 1928, 0.01 km from the trail — the Grand
  Rapids pedestrian bridge) and 03514 (PEDESTRIAN over CSAH 10,
  Becker Co., built 2021, 3.0 km). The Ely bottleneck crossings
  are in here: the twin MN 169 bridges over the Shagawa River
  (97320/97321) sit on the trail line itself (0.0–0.02 km).
- **Method / judgments:** Corridor is the 2-mile buffer around
  the statewide trail line (`site/data/trail-minnesota.geojson`)
  PLUS the Star of the North line
  (`data/segments/trail-stn.geojson` — not yet merged into
  trail-minnesota.geojson; Remer sits 7.0 km from the nearest
  line in that file), the same corridor as the timber, motorized,
  and campgrounds layers; distance computed in UTM 15N (STRtree
  over the line pieces) and recorded as `dist_trail_km`. NBI
  coordinates are DDMMSS.ss (`LAT_016`/`LONG_017`) converted to
  decimal degrees. Tier 1: service on in {3 Pedestrian-bicycle,
  5 Highway-pedestrian}, within 2 mi. [JUDGMENT] Tier 2:
  service on = 1 Highway, within 0.25 mi (400 m) of the trail —
  a vehicular bridge the trail route actually passes is one a
  hiker could use as a crossing without a detour; a 2-mi
  vehicular net would be every county-road bridge in the
  corridor and unreadable as a crossing-opportunities layer.
  Excluded in both tiers: K = bridge closed to all traffic, G =
  new structure not yet open. Blank open/closed codes are KEPT:
  the field does not apply to non-highway records, so a blank is
  not a closed bridge. Not carried: service on 2 Railroad (rail
  bridges are not crossings a hiker can use), 4
  Highway-railroad, 6/7/8 interchange levels, 9 Building/plaza,
  0 Other. Fields carried: `bridge_number`, `facility_carried`,
  `features_crossed`, `location` (all as published; NBI text
  fields arrive single-quoted and the quotes are stripped),
  `county` (FIPS code decoded — note the "Saint Louis" quirk:
  FIPS sorts "St. Louis" as "Saint Louis", so St. Louis is 137,
  before Scott 139), `district`, `owner` / `maintenance`
  (decoded agency type), `year_built`, `year_reconstructed`,
  `structure_len_m`, `deck_width_m`, `sidewalk_left_m` /
  `sidewalk_right_m` (Item 50 curb/sidewalk widths — the
  pedestrian accommodation on the structure; 28 of the 30 Tier 1
  bridges carry a nonzero sidewalk), `service_on` /
  `service_under`, `open_closed`, `structure_kind`,
  `structure_type`, `tier`, `dist_trail_km`, `nbi_records`
  (records merged for the structure).
- **Corrections caught at the pull (not in the first draft):**
  (1) the seconds in NBI DDMMSS.ss coordinates were first read
  as a plain float ('28.32' as 2832 seconds), shifting every
  point up to ~0.8 deg — caught by the Arrowhead diagnostic
  (zero Arrowhead bridges in the first cut) and fixed before
  wiring; (2) the county decode first had 137 = Scott — FIPS
  27137 is St. Louis County, 27139 is Scott — caught by the same
  check (24 "Scott" bridges sitting on the Iron Range) and
  fixed; (3) the first pull's whole-union distance loop plus the
  corridor buffer OOM-killed the script (6 GB VM) — the pull
  now indexes the line pieces (STRtree) and never builds the
  buffer.
- **Use here:** `data/points/nbi-bridges.geojson` →
  `site/data/nbi-bridges.geojson` (built by
  `scripts/build_site_data.py`), the "Bridges — crossing
  opportunities" layer: "B" discs, OFF by default and LAZY, in
  the "Around the trail" group. Tier 1 popups say the bridge is
  a crossing a hiker can use; Tier 2 popups say to check on the
  ground whether the trail uses it.

## MnDOT highway right-of-way — RWMM (NOT WIRED — service blocked, added 2026-11-18, Paul)

- **What:** MnDOT's Right of Way Mapping and Monitoring (RWMM) —
  the audit's best planning lead (U of M report §VI, p. 10; audit
  row 15, verdict: Use): where the trail could run alongside or
  inside highway right-of-way, most relevant at the Ely
  bottleneck. **No geometry is drawn from this source yet — the
  layer is not in the viewer.** The reason is access, not a
  judgment about the data (see "Blocked" below).
- **The service (verified live, then blocked):** the operational
  service the RWMM web app itself reads —
  `https://webgis.dot.state.mn.us/65agsf1/rest/services/olm/MNDOT_RWMM_OPERATIONAL/MapServer`
  (SR 26915, maxRecordCount 2000). Found via the RWMM Experience
  Builder app's own data config (item
  `8571b65ffb394613aa3582510d105d64`). Landing page:
  `https://www.dot.state.mn.us/maps/gisweb/row/`.
- **Layers in the service (read from the service root JSON
  2026-11-18, before the block):** 0 Right of Way & Railroad Map
  Footprint Group; 1 Railroad Station Plat (point); 2 DGN/PDF -
  Right of Way, static (polyline); 3 TIF/PDF - Right of Way,
  static (polyline); 4 Railroad (polygon); 5 Historic Railroad
  Right of Way Plats (polygon); 6 Right of Way Line Group;
  8 **Approximate Right of Way Line** (polyline); 10 Access
  Control Line, limited data (polyline); 12 Commissioner's Order
  & Plat Group; 13 Plat, 14 Graphic, 15 Narrative (polylines);
  16 R/W Boundary Corner Group; 17 Plat B-Point, 18 B-Point Label
  (points); 19 Land Intake & Parcel Shapes Group; 20 Parcel -
  Archived, 21 All Parcels, **41 Parcel - Current** (polygons);
  23 State Project; 25 Truck Station; 26 Tower Site; 27 Scenic
  Group; 28 Area; 29 Easement; 30 Land Disposal Group; 31
  Conveyance; 32 Turnback; 39 Freeway Design & Special
  Conditions (polyline); 40 All Right of Way Footprint (polyline).
- **The two layers that matter for the trail (fields + statewide
  counts, read 2026-11-18):**
  - Layer 8 Approximate Right of Way Line — **35,175 features
    statewide.** Fields: OBJECTID, CONTROL_SECTION, ROUTE_NUMBER,
    ROUTE_SYSTEM, DISTRICT, COUNTY, STATUS, LAYER, ACCURACY,
    SOURCE, SOURCE_FORMAT, OFFSET, COMMENTS, EDIT_DATE. LAYER
    values: RW / RW INP / Excess Land / D.O.T. Specific Interest.
    **No ROW width field exists** — the class (LAYER) is the
    only width-like attribute; the popup would carry route,
    route system, control section, county, district, class,
    status, accuracy, source. The display field CADD_DOCNAME is
    NOT queryable (service returns 400), so the map-sheet
    document name cannot be pulled per feature.
  - Layer 41 Parcel - Current — **32,236 features statewide.**
    MnDOT's current parcel interests: parcel polygons are
    MnDOT's current interests and the index to the maps, plats
    and descriptions behind them (MnDOT solicitation 1063806
    Q&A, Sep 2026). Fields (joined layer, table prefix
    `ROW_ADMIN.MnDOT_Parcel_Polygons.*`): DOCNAME, PARCEL_NUMBER,
    PARCELNUM, DESCRIPTION4, COMMENT_, ACQUISITION_CATEGORY,
    PLAN_INFO_ID, STATE_PROJECT, STATUS, PARCEL_ORIGIN,
    ACQUISITION_AREA_TYPE, SHAPE.AREA, SHAPE.LEN.
- **How much is in the corridor (probe, before the block):** in
  the trail bbox (lon -96.716..-89.933, lat 46.253..48.102),
  4,653 ROW-line IDs and 11,258 current-parcel IDs
  (returnIdsOnly queries, 2026-11-18). The corridor pull would
  clip both to the 2-mile buffer around the statewide trail
  line, same as timber / motorized / campgrounds.
- **Blocked (the reason nothing is drawn):** the webgis host
  answered normally until ~18:47 UTC on 2026-11-18, then every
  request — service root, layer metadata, queries — returned
  HTTP 200 with an HTML "Request Rejected" page ("Please
  consult with your administrator", support ID
  14928902036401554593), continuously through the last probe at
  19:11 UTC. A pull with escalating backoff (10s → 10min, 5
  tries) failed on its first query after ~19 minutes of
  retries. This is the host's WAF deciding the client is too
  chatty after the probe burst; it is not a login wall and not
  a 404 — the service is up, the requests are refused. The
  older egis12 service
  (`OLM/MNDOT_RWMM_AGOL_OPERATIONAL_LAYERS` on
  `mndotgis.dot.state.mn.us` / `dotapp9.dot.state.mn.us`) is
  not a fallback from here: this environment's egress proxy
  drops those connections outright.
- **To finish this layer later:** run
  `python3 scripts/pull_mndot_row.py` — it is written and
  ready (two-pass fetch copied from
  `pull-motorized-mn-corridor.py`: id list for the corridor
  bbox, then fetch by objectIds; clip to the 2-mile corridor in
  UTM 15N; writes `data/row/mndot-row-lines.geojson` and
  `data/row/mndot-row-parcels.geojson` with metadata). Two
  things it already learned the hard way, recorded in the
  script: fetch by objectIds must be POST, not GET (a 500-ID
  GET returns a non-JSON error page from this server), and
  requests must be paced with backoff (the host WAFs bursts).
  If the block persists, the alternatives are: the live browser
  (the RWMM app works interactively), or requesting shapefiles
  from MnDOT's LIS & RW Mapping unit
  (LISRWMAP.dot@state.mn.us — per the MnDOT FAQ, shapefiles
  are available by special arrangement).
- **NOT used (recorded, not silently dropped):** the historic
  ROW maps themselves are TIF/DGN/PDF — not georeferenced for
  our purposes (TFW world files no longer downloadable;
  shapefiles only by special arrangement per the MnDOT FAQ) —
  no geometry is drawn from them. Layer 10 Access Control Line
  ("limited data" per MnDOT's own label), layer 39 Freeway
  Design (80 features statewide, freeway design segments, not
  ROW limits), layer 40 All Right of Way Footprint (footprints
  of map SHEETS — an index to the PDF/TIF/DGN maps, not ROW
  geometry), and the Plat/Graphic/Narrative/B-Point/footprint
  layers (survey and map-sheet artefacts, not ROW limits) are
  not pulled.
- **Caveats to carry when this IS wired [JUDGMENT / MnDOT's own
  words]:** the Approximate Right of Way Line "visually displays
  an approximation of MnDOT's highway right of way" and "is used
  as a general index to identify official documents and other
  records"; ROW maps are no longer being updated (as of 2023)
  and do not include recent project information. These lines are
  a planning pointer, not a boundary survey — never present them
  as the surveyed ROW edge. Parcel - Current coverage is
  INCOMPLETE statewide: MnDOT's parcel-mapping project is
  ongoing (100,000+ parcels remain to be mapped per
  solicitation 1063806, Sep 2026); absence of a parcel here
  does not prove MnDOT holds nothing there.

## Road walk — T07 western segments + Arrowhead road pieces (added 2026-11-18, Paul)

- **What:** The on-road line, one speed badge per western
  road-walk segment except Seg 12 (badge removed Nov 19, 2026 —
  Paul), one badge per Arrowhead road/run, one per Star of the
  North connector and one for Highway 6 (added Nov 20, 2026 —
  Paul, "whole trail"), and the High-Injury Network crash
  markers (western only). Every line feature carries its drawn
  length (`length_mi`) and the trail it leaves and joins at each
  end (`from_name` / `to_name`); every line piece outside the
  west also carries its road's speed (`speed_mph` /
  `speed_text`). Every speed-badge popup links to Google Street
  View at the badge's spot (added Nov 20, 2026 — Paul, to see
  the shoulder; coverage varies, see below).
- **Sources:** T07 (Trail Research Brief T07 — Western Road Walk:
  The Safety Case, Segment by Segment, Nov 15, 2026; data
  retrieved Nov 16, 2026) for the 15 western segments, their
  speeds and the crash spots; the NCTA gap lines for geometry
  (`site/buildout/data/gap-western.geojson`, 90 features,
  104.86 mi; `site/buildout/data/gap-arrowhead.geojson`).
  Road names for the Arrowhead, Star of the North and Highway 6
  pieces: OpenStreetMap / Nominatim reverse-geocodes of the
  piece midpoints (Nov 20, 2026), endpoints checked where the
  midpoint sat on a trail crossing, OSM API way data where
  Nominatim returned only a trail; geometry for the STN
  connectors from the official STN line
  (`site/data/trail-stn.geojson`, trail_type = Public Road) and
  for Highway 6 from the statewide NCT line
  (`site/data/trail-minnesota.geojson`, trail_type = Public Road).
- **Geometry method:** the western gap line is ordered west→east
  by a graph walk from the Red River end (endpoint adjacency
  within 2 km), validated against T07's mileposts (City of Fergus
  Falls at chain mile 39.5–42.4 vs T07 MN-40.0–43.5; Maplewood
  Church Rd at 67.3 vs MN-66.0–68.5; Becker Co Line at 95.1–96.4
  vs MN-94.8–97.0). Chain miles track T07 miles within ~1 mi
  (chain total 104.86 mi vs T07 corridor 107.0 mi). The western
  road-walk line is the chain clipped to T07's segment ranges
  (78.1 mi measured; the 2.1-mi shortfall is the NCTA GIS being
  2% shorter than the map-series miles). Speed badges sit at each
  segment's midpoint by cumulative chain miles (Seg 14 sits at
  the US-10 crossing, chain mile 95.2, instead — its midpoint
  falls in Frazee, but the segment's expressway portion is the
  crossing). Crash markers sit at the HIN corridor's segment
  midpoint (CSAH 88 at MN-39.5; CSAH 4 at MN-85.5 in Vergas;
  CSAH 1 / Tower Road at MN-56.5). Arrowhead badges sit at the
  group midpoint by cumulative miles (Grand Rapids run, CR 61,
  Fernberg Road, MN-135); STN badges at each connector's
  midpoint; the Highway 6 badge at the combined midpoint of the
  two pieces. Positions are approximate within ~1 mi and the
  popups say so.
- **Endpoints + lengths (added 2026-11-19, Paul):** western
  segments are enriched per SEGMENT (all pieces of a segment
  share the values); Arrowhead pieces per PIECE. `length_mi` is
  the drawn length measured from the geometry. `from_name` /
  `to_name` are found by walking the ordered NCTA-service chain
  outward from the segment's T07 mile range: a foot / paved /
  sidewalk feature reached within 1 chain-mile is named (its
  seg_name + kind, e.g. "Prairie Wetlands Learning Center (foot
  tread)"); if the walk runs along road into the next T07
  segment, the end reads "Road walk continues — Seg N"; if the
  walk meets an untyped ("other") feature, or 1 mile passes with
  no tread and no next segment, the end reads "No adjoining trail
  identified in the map data". Chain ends are special: the west
  end of Seg 1 is the Red River — the western end of the route;
  the east end of Seg 15 runs past the end of the NCTA-service
  chain (104.86 mi vs the T07 corridor 107.0 mi), so it is
  checked against the statewide NCT line, which continues east
  as footpath. Arrowhead piece ends take the nearest foot-tread
  or paved multi-use path (gap-arrowhead foot/paved features, or
  the bike-trails layer) within 500 m, by point-to-line
  distance; nothing within 500 m leaves the field off. STN
  connectors and Highway 6 pieces are enriched per PIECE: STN
  ends join Chippewa National Forest footpath (the adjoining
  features in file order); Highway 6 ends take the nearest
  statewide-line footpath within 500 m. No
  endpoint name is invented: a name comes only from an adjoining
  feature's seg_name / trail_name, or the fixed fallback strings
  above. Speed and HIN facts ride on the western line features
  from the T07 table and HIN_SPOTS — except Seg 12, which
  carries no speed fields (badge removed). Method lives in
  `scripts/build_roadwalk.py` (`segment_end_name`,
  `nearest_tread_name`).
- **Speeds (T07 Leg 2):** statutory 55 mph rural / 30 mph urban /
  65 mph expressway (Minn. Stat. § 169.14), or the Otter Tail SAP
  "majority 55 mph" finding. Badge values: 55 everywhere except
  Seg 7 (Fergus Falls urban, 30) and Seg 14 (US-10 crossing, 65).
  Seg 12 has no badge (removed Nov 19, 2026 — Paul; see below).
  The Mesabi Trail bike path (surface "paved", 115 mi) is NOT
  road walk and is not drawn.
- **Speeds — Arrowhead / Star of the North / Highway 6 (added
  2026-11-20, Paul — "whole trail"):** same statute, same
  defaults — 55 mph rural / 30 mph urban (Minn. Stat. § 169.14),
  with "unless posted" wording on rural pieces. These are
  STATUTORY DEFAULTS, not field-verified posted limits: no posted
  limit was verified for any of these pieces, and every popup,
  this entry and the data-sources page say so. Urban/rural from
  the Nominatim address (inside Grand Rapids, Cohasset or Tower
  city/village limits = urban; township/unincorporated = rural).
  One badge per road or contiguous same-setting run (western
  precedent: one badge per segment, cf. Seg 7 "Fergus Falls city
  streets"). Per-piece table (road — mph — setting): Forest
  History Road — 30 — Grand Rapids; SW 6th Street — 30 — Grand
  Rapids; 11th Avenue SW — 30 — Grand Rapids; CR 76 — 30 —
  Grand Rapids + Cohasset; CR 61 / Prairie Lake Road — 55 — Arbo
  Township; Fernberg Road — 55 — Fall Lake Township; MN-135 —
  55 — Embarrass/Kugler Townships, 30 in Tower (the 0.17-mi
  Tower piece shows 30; the MN-135 badge shows the 55 majority);
  Pines Street — 30 — Tower; MN 200 — 55 — Cass Co.; Tobique
  Road NE — 55 — Cass Co.; Milton Lake Drive — 55 — Cass Co.;
  MN 6 — 55 — rural, 30 in Cohasset (west end is rural Deer
  Lake, Cass Co. — not in Remer; east end meets County Road 17
  in Cohasset). Badge grouping: Grand Rapids city streets
  (4 pieces, 2.0 mi, 30); CR 61 (3 pieces, 3.6 mi, 55); Fernberg
  Road (2 pieces, 4.3 mi, 55); MN-135 (4 pieces, 15.0 mi, 55);
  MN 200 / Tobique / Milton Lake (one badge each, 55); MN 6
  (one badge, 16.3 mi, 55). No piece was left badge-less.
  **Highway 6 (added Nov 20, Paul):** the 16.3-mi Remer–
  Cohasset road walk was in NO viewer layer; this build adds
  its line (2 features from the statewide NCT line,
  trail_type = Public Road) and its badge.
  **Street View in badge popups (added Nov 20, Paul):** every
  speed-badge popup links to Google Street View at the badge's
  coordinates
  (`https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=LAT,LON`,
  built from the badge feature's own geometry) so the shoulder
  can be seen. Coverage varies — Street View has no imagery on
  some rural roads, and the link then falls back to the map
  view; the popup says so.
- **Shoulders (T07 Leg 2; checked 2026-11-18):** no as-built
  shoulder width is published for any of the 15 western segments.
  MnDOT TCDS omits shoulder widths in public station views, so
  every segment in T07's "Shoulder Width / Edge Condition" column
  reads "Not published in MnDOT TCDS" (Segs 3 and 8 have no TCDS
  station at all). The layer therefore carries NO numeric
  `shoulder_width_ft` for any segment — the key is absent, not
  zero and not a design-table value. What it carries per segment
  is `shoulder_quality` + `shoulder_source` on the western line
  pieces and the speed badges.
  - **References:** T07 Leg 2 table (output Doc
    `nct-western-roadwalk-safety-2026-11-15`,
    `1wHqDBbJxoU-k128QWiQkUa1DNPwBTZ0eFxn4C6qNJho`); Otter Tail
    County Safety Action Plan (adopted May 26, 2026), Table 9
    (p. 67: curve cross-section widths 28–34 ft, countywide
    context only) and Table 10 (pp. 73–75: systemic-risk tiers
    and Edge Risk 2S/3 deficiencies).
  - **Interpretation method (reproducible):** `shoulder_quality`
    is a DIRECT COPY of the T07 table cell for the segment,
    lightly compressed (station lists dropped; the SAP tier /
    Edge Risk clauses kept in substance). No width is inferred,
    estimated or derived from any other source: where the cell
    says "Not published", the field says so. The one wording
    change is Seg 7: the cell reads "Concrete sidewalk" and the
    row text adds "Concrete sidewalks along ~3.64 mi in NCTA
    GIS" — the field renders that as "Concrete sidewalk along
    ~3.64 mi (NCTA GIS); no shoulder — walkers on sidewalk".
    The "no shoulder" clause is a wording summary [JUDGMENT:
    the cell does not state it in those words; the sidewalk is
    the documented edge condition for the segment]. Per-segment
    edge condition carried: Seg 6 (CSAH 88 HIN 6.0, Tier 3);
    Seg 9 (CSAH 1 segments 9, 15–20, Tier 3); Seg 10 (CSAH 3
    segments 1–3, Tier 2 with Edge Risk 2S/3); Seg 12 (CSAH 41
    Segments 1 & 2, Tier 1 with all 4 risk factors incl. Edge
    Risk 2S/3; CSAH 4 in Vergas HIN 6.0, Tier 3).
  - **Checked and rejected as as-built widths:** MN Rules
    8820.9920 design table (required widths for new
    construction / reconstruction by projected ADT — 1 ft at
    0–49 ADT up to 6 ft at 1,500+, 8 ft minimum for minor /
    principal arterials over 1,500 ADT — not measurements of
    these roads); MnDOT Bikeways map (mnbikewaysmap.org, shows
    per-road shoulder widths but is a JS app; the statewide
    BIKEWAY FeatureServer
    `webgis.dot.state.mn.us/65agsf1/rest/services/sdw_trans/BIKEWAY/FeatureServer`
    is WAF-blocked to text fetch, and the Bikeways Data Standard
    v1.0 (Jan 2022) carries no numeric shoulder-width field —
    "shoulder" appears only as a separation-type value);
    MnDOT District 4 shoulder-widening prioritization study
    (exists — the District 8 study, Sept 2021, says it was
    modeled on the District 4 pilot — but could not be located;
    request from MnDOT District 4); MnDOT county bikeways maps
    (classify roads "Paved Shoulder 4' or Wider", but per-road
    values need a visual map read, not tried here).
  - **Benchmark (guidance, not a measurement):** FHWA Proven
    Safety Countermeasures guidance recommends a walkable
    shoulder of at least 4 ft (stabilized or paved) on both
    sides of rural highways routinely used by pedestrians (5 ft
    cited in FHWA's Walking Along Roadway research as acceptable
    along low-volume roads). The viewer does not score segments
    against this benchmark — there is no measured width to
    compare.
- **Observed speeds (checked 2026-11-18):** none published per
  segment, so the layer carries no observed-speed field and the
  posted / statutory speeds stand alone. MnDOT's Speed Monitoring
  Program (57 automated stations,
  `dot.state.mn.us/trafficeng/speed_monitoring/speed_reports.html`)
  reports the average 85th percentile speed aggregated by roadway
  category only (five categories: urban freeway, rural freeway,
  rural 2-lane/2-way highway, rural divided highway non-freeway,
  urban divided highway non-freeway) and publishes no station
  list, so no station can be tied to a road-walk segment.
  **Interpretation rule:** the category-average 85th percentile
  must NOT be substituted as a segment's speed. MnDOT speed
  studies (engineering and traffic investigations under Minn.
  Stat. § 169.14) DO exist for CSAH 1 (Tower Road, finalizing),
  CSAH 1 in Weetown (complete — recommends raising 50 to 55 mph),
  CSAH 4 & CSAH 60 in Vergas (complete — recommends no change in
  40 mph), CSAH 35 by Dead Lake (complete — no change in 55 mph),
  CSAH 41 by East & West Silent Lake (complete — no change in
  55 mph) and CSAH 88 (Fir Avenue, finalizing) — Otter Tail County
  Board minutes, Jan 3, 2023 — but only the recommendations are
  public, not the measured 85th percentile speeds; the studies
  themselves are a records request to MnDOT District 4 / Otter
  Tail County Highway Dept. T07 contains no observed-speed data
  at all (no 85th percentile values, no speed-study results, no
  "speeding" mentions). No speed study was found for the Wilkin
  or Becker segments or for the Arrowhead road pieces.
  **Resolved Nov 19, 2026 by removal:** the Vergas 40 mph in those minutes
  differs from T07's "30 mph in Vergas" (Seg 12) — Paul ordered the
  badge removed rather than reconciling the discrepancy. The Seg 12
  line and its HIN crash marker stay; the Seg 12 line popup carries
  no speed row, and a rebuild does not resurrect the badge
  (`scripts/build_roadwalk.py` skips Seg 12 in the badge loop).
- **Crash spots (T07 Leg 3, Otter Tail SAP pp. 60–64, Table 10):**
  CSAH 88 HIN 6.0 (Seg 6) + Tier 3; CSAH 4 in Vergas HIN 6.0
  (Seg 12) + Tier 3 (CSAH 41 in the same segment is Tier 1);
  CSAH 1 / Tower Road HIN 7.0 (adjacent to Seg 9) + Tier 3.
  Caveat carried in every crash popup: no published record
  attributes any crash to a hiker.
- **Gap (reported, partly filled Nov 20, 2026):** T07 covers the
  WESTERN road walk only (Wilkin / Otter Tail / Becker). No crash
  analysis exists in the packet for the Arrowhead, Star of the
  North or Highway 6 road walk, so those pieces carry no crash
  icon. The speed gap is FILLED (Nov 20, Paul — "whole trail"):
  every Arrowhead, STN and Highway 6 piece carries a
  statutory-default speed and the Speed limits layer covers the
  whole trail. **Star of the North: added Nov 20** — the 3
  on-road connectors on the official STN line (0.74 mi) are now
  road-walk lines with badges. **Highway 6: added Nov 20** — the
  16.3-mi road walk (Remer to Cohasset, official-line on-road
  features lon −93.847..−93.630, lat 47.10..47.23) is now a
  road-walk line (2 features) with a badge; it is Arrowhead
  reroute / Tioga Beach EA territory, NOT Star of the North.
  Wilkin/Becker segment-level pedestrian/bicycle counts could not
  be resolved in T07 either (MnCMAT2 login-restricted; MNCrash
  upstream error; TCMAC gated).
- **Use here:** `data/roadwalk.geojson` (86 features: 61 line
  pieces, 22 speed badges, 3 crash markers) →
  `site/data/roadwalk.geojson` (built by
  `scripts/build_site_data.py`), five layers in the "Road walk"
  group (Road walk / Speed limits / Accident-prone areas / the two
  Shoulder widths layers below), all OFF by default and LAZY. The
  western line pieces and the speed badges carry
  `shoulder_quality` + `shoulder_source` (shown in both popups);
  the Arrowhead, Star of the North and Highway 6 pieces carry
  speed fields but no shoulder fields. Measured shoulder widths
  live in the Shoulder widths layers, not in this file.

## Shoulder widths — measured, one point per mile (added 2026-11-20, Paul)

- **What:** Two layers in the "Road walk" group, both OFF by
  default and LAZY: `site/data/shoulder-segments.geojson` (183
  stretches, 120.4 mi — the road-walk lines split at the measured
  points, each stretch coloured by the class of the mile that
  starts at it) and `site/data/shoulder-points.geojson` (142 dots,
  one per point). Built by `scripts/build_shoulder_layer.py` from
  the merged measurement sheet.
- **Speed limit in the popup (added 2026-11-20, Paul):** each point
  carries `speed_mph` + `speed_text` from the road-walk line piece
  it was assigned to (nearest line in its segment group), baked into
  the points GeoJSON by the build script. Statutory limits, not
  posted — the same figures as the speed badges. Seg 12 points
  (68–73) carry no speed and the popup omits the row: the Vergas
  speed figures were never reconciled (30 mph in the brief, 40 mph
  in the MnDOT study) and Paul ordered the badge removed Nov 19
  rather than picking one.
- **Headline (measured, not quoted):** 28 of 111 shoulder miles
  below the 4-ft FHWA walkable-shoulder benchmark, 33 straddling
  it, 32 meeting it, and 18 walkable on flat grass with no paved
  shoulder at all. The thin miles cluster in the western
  segments (13 of 38 measured western points in segments 1–8
  below, after 14 were re-read as walkable grass) and on the
  Arrowhead's unpaved stretches; the Highway 6 northern half
  (miles 10–16) is the widest, mostly 6–10 ft. The pilot (MN 6,
  east side, 20 points, 2 of 18 below) is superseded by the
  rollout's west-side re-measurement and is not drawn.
- **Coverage:** 143 points planned, one per mile — western
  segments 1–15 (92), Highway 6 Remer–Cohasset (17), Arrowhead
  (31), Star of the North (3). 142 dots: point 119 (CR 61, mile
  3.60) was skipped — no straight stretch within 0.2 miles — so
  it has no coordinates and no dot; its stretch takes the
  preceding point's class. Of the 142, 117 measured (111 shoulder
  widths + 6 curbed city streets measured for sidewalk instead),
  19 unmeasurable from their frame, 6 with no frame captured.
- **Interpretation method (how raw frames became widths):** each
  point is a Google Street View Static API frame (640×640, pitch
  0, heading facing the walk direction) at the point's
  coordinates, captured November 20, 2026 (Google Cloud project
  nct-shoulder-pilot; key restricted to the Street View Static API
  — the key value appears in no file). Measurement side is the
  **west** side (walker's left, facing traffic). The ruler is the
  12-ft lane, measured in pixels at the same row as the white edge
  line (centreline = yellow line, edge line = white line); paved
  shoulder is white line to pavement edge, where the edge is the
  point smooth asphalt gives way to rough gravel (9×9 texture
  break, cross-checked against the colour break where brown dirt
  or verge begins); gravel is pavement edge to grass verge. Every
  width is a 2-ft range, never a decimal. Imagery date comes from
  the API metadata endpoint at capture time, never from the image
  (frames carry no date); dates run 2008-09 (one Tower junction
  frame) to 2026-06, most 2024–2025. The lane-to-line cross-check
  does NOT validate at 640 px — JPEG blooming inflates the white
  line ~2×, so the foot numbers rest on the lane ruler only and do
  not depend on the assumed 4-in line width; if the lanes are 11
  ft rather than 12 ft, subtract ~8% from every figure. Curves
  cannot be measured (the straight-road ruler does not apply) and
  were moved to the nearest straight stretch within 0.2 miles
  where one existed; 13 points moved ≤0.2 mi.
- **Classification rules (what the colors mean):** `below` — the
  paved range sits entirely under 4 ft, including 0-ft gravel
  roads with no pavement at all and point 72, a town street with
  no edge line. `marginal` — the range straddles 4 ft (e.g. 2–4
  ft, 3–5 ft). `meets` — the range sits entirely at or above 4
  ft. `unmeasurable` — the pavement edge cannot be seen in the
  frame. `grass` — no paved shoulder at all, but flat walkable
  grass at least 4 ft wide at the pavement edge, read off the same
  frame (18 points, Nov 20, 2026; grass width + flatness in
  `shoulder-grass-verge-assessment-2026-11-20.md`). Points 17 and
  41 stay `below`: 17's frame is obstructed by a pickup bed, 41's
  grass slopes up to a fenced hillside. `curbed` — a curbed city street where the shoulder
  metric does not apply; the point is a sidewalk check instead
  (Fergus Falls 46–49, Grand Rapids 113–114). `no-frame` — the
  capture returned the "no imagery here" placeholder; a coverage
  gap, recorded, not a measurement. A stretch from point i to
  point i+1 takes point i's class — each point stands for the
  mile that starts at it. Geometry: points projected onto the
  road-walk lines in EPSG:26915 (UTM 15N); every measured point
  sits within 1.6 m of its line; the split follows the drawn road,
  not a straight line between points.
- **Judgment calls (labeled as such):** the head of a road-walk
  piece before its first measured point takes the class of the
  preceding point in mile order within the same segment group
  (the mile that stretch belongs to); 18 pieces carry no point of
  their own (short pieces between mile marks, e.g. six Vergas
  pieces) and take the class of the nearest point in their group.
  Point 72 (town street, no edge line, paved 0) is counted
  `below`, not `unmeasurable` — the pavement visibly ends at the
  road edge. Gravel roads are counted `below` at 0 ft paved, not
  excluded — a walker there has no paved shoulder. The 3–5 ft
  ranges are `marginal`, not `meets` — the range crosses the
  benchmark. The A1 chunk's pavement edge rests on the saturation
  break (the pilot's texture rule failed on those frames);
  cross-checked against the dirt edge and per-frame debug
  annotations.
- **Unmeasurable, by cause:** snow-covered user panos (points
  5–10); curves (42, 82); junction aprons (73, 85, 135 — 135's
  2008 frame is also too blurry); trail panos that are not the
  road (115, 116, 118); an aerial construction shot (117); a
  motorcyclist blocking the walker's side (136); glare (89);
  edge off-frame (86).
- **Sidewalks (urban points only):** Fergus Falls 46 absent both
  sides, 47 east only (west not visible), 48 both, 49 east only
  (west absent); Grand Rapids 113 absent both, 114 present right
  only; Tower 135 unmeasurable; Seg 14 point 81 present west
  side. No sidewalk anywhere on the rural points.
- **NOT drawn (and why):** the pilot's east-side numbers — the
  rollout re-measured the same road on the walking side; point
  119 — no coordinates. No point is a field measurement: every
  width is read off a Street View frame, and nothing here is an
  as-built width — MnDOT publishes no as-built shoulder width
  for these roads.
- **Sources:** Google Street View Static API imagery, captured
  November 20, 2026; frames filed as
  `shoulder-rollout-frames/rollout-point-N.jpg` with per-frame
  receipts (`receipts-a1/a2/b/c.csv`, imagery dates from the API
  metadata endpoint at capture); measured widths in
  `shoulder-rollout-measurements-merged.csv` (143 points; chunk
  sheets a1, a2a, a2b, b, c in the same folder); method in
  `shoulder-pilot-mn6-measurements-2026-11-20.md` and
  `shoulder-rollout-plan-2026-11-20.md`; geometry is
  `site/data/roadwalk.geojson` split at the measured points.
  Work files in the trail-case workspace,
  `~/workspace/goals/finish-the-north-country-trail-in-minnesota/analysis/`
  (merged sheet + CSV, chunk sheets, receipts, frames,
  `merge-shoulder-measurements.py`).

## Street View — Google Street View at trailheads, road crossings, road-walk points (added 2026-11-13; extended 2026-11-18, Paul)

- **What:** One camera marker per spot at the panorama location
  (where the photo was taken from); the link opens aimed at the
  trail crossing / trailhead (heading in the data). Layer OFF by
  default, in "Around the trail". Popup shows the spot name, the
  imagery date, what the view faces, and the Street View link
  (plus a photosphere note where the imagery is user-contributed
  rather than Google car coverage — the east Hwy 113 spot).
- **History / counts:** 11 spots Nov 13, 2026 (browser check —
  11 of 19 candidate spots had imagery; the other 8 have none) +
  13 trailhead parking spots the same day = 24. Extended Nov 18,
  2026 by `scripts/build_streetview_extension.py`: +6 verified
  road-walk points from the buildout gap file = **30**. Extended
  again Nov 18, 2026 by `scripts/wire_streetview_26.py`: +26 verified
  points from the 41-candidate browser check
  (`docs/street-view-41-check-2026-11-18.md`) = **56**. The 15 that
  failed stay out, including all 7 Priority 2 Walker–Hackensack
  crossings (no Street View coverage there at all). Headings are the
  check's confirmed/corrected values; imagery dates are year-only
  (the check could read only the © YYYY watermark year).
- **References:** Google Street View imagery (dates as published
  in each pano: Oct 2024, Sep 2024, Jun 2026, Sep 2025, Jul 2024);
  NCTA gap lines (`site/buildout/data/gap-arrowhead.geojson`,
  `gap-western.geojson`); T07 segment ranges and road names;
  `site/data/access-points.geojson` (trail/road crossings).
- **Verification method (the rule):** a point enters the layer
  only after a browser check opens its pano URL and confirms
  Google Street View imagery actually exists there, recording the
  imagery date and the heading that shows the trail. The Nov 13
  check is the precedent (11 of 19 passed). No API key exists in
  the repo and no keyless metadata check worked (a text fetch of
  the pano URL returns no extractable content), so the browser
  check is the only verification — it cannot be automated from
  this repo.
- **The 6 wired Nov 18 (all verified True in the gap file, with
  pano dates and notes):** MN-135 just south of Tower, MN-135
  Wahlsten area, MN-135 at Embarrass (all on the Arrowhead
  road-walk line, pano Jun 2026); MN-169 / E. Sheridan St, Ely
  (east end of the Mesabi Trail, where the NCT continues east on
  Fernberg Rd, pano Sep 2024); CR-88 southeast of Rothsay
  (pano Sep 2025) and CR-88 at Fergus Falls (pano Jul 2024),
  both on the western road-walk line.
- **Interpretation method for the 6 (reproducible):** converted
  from the gap file's schema to the main-layer schema
  (name / faces / heading / imagery / pano_lat / pano_lon /
  trail_lat / trail_lon / url / photosphere, plus the gap file's
  road / why / pano_note / verified carried as provenance).
  `trail_lat`/`trail_lon` is the nearest point on the road or
  trail line the point sits on (0 m for all 6, measured).
  `heading` is COMPUTED, not observed [JUDGMENT]: the bearing of
  that line at the nearest vertex, in route-travel direction
  (stored coordinate order, verified south-to-north on MN-135
  and northwest-to-southeast on CR-88; flipped eastward for the
  Ely point, where the Mesabi Trail pieces are stored in mixed
  order). A later browser check should confirm or correct each
  computed heading.
- **Checked and NOT wired:** ND-4 / Fort Abercrombie (verified
  False — no pano on the highway; nearest pano is inside the
  historic-site grounds; the note says do not present it as a
  road view); MN-169 Eagles Nest, US-75 at Kent, US-59 Fergus
  Falls, MN-210 E Fergus Falls (verified, but documentary
  safety-case viewpoints 0.6–2.2 km off the trail line, not
  intersections or access points — they stay in the buildout
  file only).
- **Verification queue (unverified — do not wire until checked):**
  41 candidates derived Nov 18 by
  `scripts/build_streetview_extension.py`, in
  `site/buildout/data/streetview-candidates.geojson` and
  `docs/streetview-verification-queue-2026-11-18.md` (each with
  a pano URL to open): 30 priority-1 road-walk segment/piece
  ends (western Seg 1–15 boundaries and on/off points, chained
  in mile order, plus 9 Arrowhead road-piece ends), 7
  priority-2 ITM trail/road crossings without coverage
  (Sixth Lake Rd, 60th St, 30th Ave, Tower Rd, and three
  Woodtick Trl crossings, all east of the existing points),
  4 priority-3 interior breaks in the roadwalk line pieces
  (confirm on the map whether each is a real on/off point or a
  data gap). Derivation: piece-endpoint clustering within
  40 m; segments chained in T07 mile order (longitude alone
  mislabels north–south segments such as Seg 10); dedupe
  150 m against existing coverage (main layer + the 6 wired).
  **Limitation:** no mid-segment road intersections could be
  derived — `site/data/simple-roads.geojson` covers only the
  ITM extent (lon −95.679 to −94.111), not the western
  (−96.716 to −95.645) or Arrowhead (−93.587 to −91.756)
  road-walk corridors, so intersections there need the roads
  data extended first or a map read.
- **Use here:** `site/data/streetview.geojson` (30 features),
  layer id `streetview`, OFF by default.

## Base-map tile & image services (map v2, added 2026-11-10)

Live map backgrounds, consumed directly by the site (nothing is
downloaded into the repo). Every endpoint was verified from the
project sandbox on 2026-11-10 by fetching sample tiles / WMS
GetMap responses over the chapter's extent.

**v4 (Nov 10, 2026):** the default base is now **Topo
(OpenTopoMap)** — a new visitor meets terrain first.

**Nov 11, 2026 prune (Paul's calls):** the switcher carried nine
bases in four task groups — Topographic (Topo (OpenTopoMap),
USGS Topo 1:24k, National Geographic (Esri)), Relief (MN LiDAR
Hillshade), Aerial (Aerial (NAIP 2023/25), Aerial (Esri), Aerial +
Topo (NAIP 2023/25)), Streets & trails (Streets (OSM),
Trails (CyclOSM)). Seven entries from the Nov 10 review round
were removed outright (see "Removed bases" below), including the
two key-gated ones and their placeholder keys. **Two bases were
added later the same day** (Paul approved the pair): Aerial
(2014) in the Aerial group and Winter (snow trails) in Streets
& trails — eleven bases in all, same four groups.

**Nov 16, 2026 (Paul):** four more entries — **Outdoors (Mapbox)**,
**Outdoors (MapTiler)** and **Outdoors (Stadia)** in Streets & trails
(sub-choices under Topo) and **Hiking routes (Waymarked Trails)** as
an overlay in "Other trails". The Nov 11 no-key rule is lifted for
all three keyed bases.

- **Topo (OpenTopoMap)** — the DEFAULT base since v4.
  `https://tile.opentopomap.org/{z}/{x}/{y}.png`: OpenStreetMap
  data rendered with SRTM contours and hillshading. Attribution:
  "Map data: © OpenStreetMap contributors, SRTM | map style: ©
  OpenTopoMap (CC-BY-SA)".
- **Streets (OSM)** — the standard OpenStreetMap rendering,
  `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. Attribution:
  "© OpenStreetMap contributors".
- **Outdoors (Mapbox)** — Mapbox Outdoors style (the base AllTrails
  builds on),
  `https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/tiles/{z}/{x}/{y}?access_token=<token>`:
  512 px raster tiles (tileSize 512, zoomOffset -1 in Leaflet),
  max zoom 22. Needs the chapter's Mapbox public token (pk.*);
  free tier 50,000 map loads/month. Token verified live over the
  chapter Nov 16, 2026 (HTTP 200, 512 px PNG). Attribution: "© Mapbox,
  © OpenStreetMap contributors".
- **Outdoors (MapTiler)** — MapTiler Outdoor style,
  `https://api.maptiler.com/maps/outdoor/{z}/{x}/{y}.png?key=<key>`:
  512 px raster tiles (tileSize 512, zoomOffset -1 in Leaflet),
  max zoom 22 (native 20). Needs the chapter's MapTiler key;
  free plan 100,000 map loads/month, stops rather than bills.
  Key verified live Nov 16, 2026 (HTTP 200, 512 px PNG with the
  site's Origin; 403 without it — the key is origin-restricted to
  pauljmorin.github.io). Attribution: "© MapTiler, © OpenStreetMap
  contributors".
- **Outdoors (Stadia)** — Stadia Maps Outdoors style,
  `https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}.png?api_key=<key>`:
  256 px raster tiles, max zoom 20. Needs the chapter's Stadia API
  key; free plan 200,000 credits/month, no card, non-commercial.
  Key verified live Nov 16, 2026 (HTTP 200, 256 px PNG — a bare
  request with no Referer got 401; the property uses domain auth
  and the browser sends a Referer from the live site).
  Attribution: "© Stadia Maps, © OpenMapTiles, © OpenStreetMap
  contributors".
- **Hiking routes (Waymarked Trails)** — overlay, not a base:
  transparent tiles carrying only waymarked hiking routes,
  `https://tile.waymarkedtrails.org/hiking/{z}/{x}/{y}.png`.
  Keyless, free; community infrastructure, fair-use policy.
  Tiles are blank where no waymarked route crosses. Verified
  live Nov 16, 2026 (HTTP 200). Attribution: "Hiking routes: ©
  Waymarked Trails (Sarah Hoffmann), © OpenStreetMap contributors".
- **MN LiDAR Hillshade** — Minnesota Geospatial Image
  Service (MnGeo), WMS 1.1.1, Web Mercator endpoint
  `https://imageserver.gisdata.mn.gov/cgi-bin/wmswm?`, layer
  `hillshd` ("Statewide"): hillshade derived from 1 m LiDAR
  (statewide elevation collection 2008–2012; Minnesota Department
  of Natural Resources / MnGeo). Wired via `L.tileLayer.wms`,
  non-transparent base. Attribution: "Shaded relief (LiDAR
  hillshade): MnGeo / Minnesota DNR".
- **USGS Topo 1:24k** — The National Map (USGS),
  `https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}`:
  the USGS topographic base built from the 1:24,000 quadrangle
  series. Added Nov 10, 2026 (v3); sample tile over the chapter
  verified live the same day. Attribution: "Topo: USGS, The
  National Map".
- **Aerial (NAIP 2023/25)** — The National Map (USGS),
  `https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}`
  (NAIP-based imagery). Attribution: "Aerial imagery: USGS, The
  National Map (NAIP)". The label's years reflect Minnesota's
  NAIP flight years 2023/2025: The National Map service does not
  publish which vintage it serves per tile, so the chooser names
  the flight years rather than a single date.
- **Aerial (Esri)** — Esri World Imagery —
  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`.
  Attribution: "Aerial imagery: Esri, Maxar, Earthstar
  Geographics".

**Also in the switcher:**

- **Aerial + Topo (NAIP 2023/25)** — The National Map,
  `.../USGSImageryTopo/MapServer/tile/{z}/{y}/{x}` (NAIP imagery
  with topo labels/contours).
- **National Geographic (Esri)** — Esri,
  `.../NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}`.
- **Trails (CyclOSM)** —
  `https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png`.
- **Aerial (2014)** — Esri World Imagery Wayback, release
  **5844**, dated **2014-12-30** — the release closest to (and
  on/before) 2014-12-31 in the Wayback config
  (`https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json`,
  198 releases listed when checked 2026-11-11). WMTS tiles:
  `https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/5844/{z}/{y}/{x}`.
  The service answers a tile request with a 301 to the release
  that actually published that tile (over the chapter, tiles
  resolve to the 2014-06-11 and 2014-02-20 releases); browsers
  follow it, and every resolved tile is 2014-or-earlier imagery.
  Keyless. Verified live 2026-11-11: sample tiles over the
  chapter returned HTTP 200 JPEGs (256×256). Attribution:
  "Aerial imagery (2014): Esri World Imagery Wayback, release
  of 2014-12-30". **Relabelled Nov 13, 2026 to "Aerial 2014
  (Dec)"** so it matches the year-by-year entries below.

**Nov 13, 2026 — year-by-year aerials (Paul: "putting all of
them in and labeling them by year... and by season or month"):
21 new entries, all verified live over the corridor Nov 13
(z12 tiles at 5 points for Wayback, GetMap requests for MnGeo
WMS), all keyless, all non-primary (behind "More
backgrounds…"). Two corrections to the premise came out of the
check: the leaf-off layer Paul remembered is the 2013 spring
imagery (`nc13hm`), not the 2014 one (`nw14` — blank white over
most of the corridor, so NOT re-added); and Wayback 2015, 2016
and 2017 are pixel-identical to the 2014 base (all resolve to
release 31144, 2014-06-11), so they were NOT added. 2018–2025
are each genuinely distinct.**

- **Esri Wayback year-end releases 2018–2025** — one release per
  year, the release closest to (and on/before) Dec 31, from the
  Wayback config (198 releases, 2014-02-20 → 2026-10-29,
  fetched Nov 13, 2026): 2018 → 23448 (2018-12-14), 2019 → 4756
  (2019-12-12), 2020 → 29260 (2020-12-16), 2021 → 26120
  (2021-12-21), 2022 → 45134 (2022-12-14), 2023 → 56102
  (2023-12-07), 2024 → 16453 (2024-12-12), 2025 → 13192
  (2025-12-18). WMTS pattern as the 2014 entry, with the release
  id swapped in. Release dates are publication dates; the
  underlying Minnesota imagery is summer leaf-on (visually
  confirmed on z14 tiles for 2018 and 2025). Labels "Aerial YYYY
  (Dec)", sub "Esri Wayback · summer leaf-on". 2026 NOT added —
  the current Aerial (Esri) base already serves the newest
  imagery.
- **MnGeo Geospatial Image Service** — same WMS endpoint and
  pattern as the hillshade (`L.tileLayer.wms`, endpoint
  `https://imageserver.gisdata.mn.gov/cgi-bin/wmswm?`), layers:
  `nc13hm` (2013 spring leaf-off, SAIP 50 cm — the leaf-off
  layer; covers the whole corridor), `fall12` (2012 fall
  Central), `fsa2021`, `fsa2019`, `fsa2017`, `fsa2015`,
  `fsa2013`, `fsa2010`, `fsa2009`, `fsa2008` (per-vintage NAIP
  mosaics, summer leaf-on), `usgs2006` (2006 summer/fall, mixed
  leaf-on/off), `fsa` (2003 FSA, summer leaf-on), `doq` (1991
  USGS black-and-white). `fsa2023`/`fsa2025` NOT added — they
  duplicate the current Aerial (NAIP 2023/25) base. Labels carry
  year and season ("Aerial 2013 (spring, leaf-off)", "Aerial
  2012 (fall)", "Aerial 1991 (black-and-white)", the NAIP years
  as "Aerial YYYY (summer)"). Not added after checking:
  `nw14` (2014, blank over most of the corridor), `nc13ft`
  (2013, real only at the west end), `fall11`, `itas18`, `polk`,
  `belt20`/`belt23`, `ncir09`/`ncclr09` (bboxes north of the
  trail or no trail coverage), `landsat` (30 m, too coarse),
  and the `*cir` color-infrared renderings (same years already
  covered in colour).
- **Winter (snow trails)** — a COMPOSED base: OpenSnowMap
  pistes tiles
  `https://tiles.opensnowmap.org/pistes/{z}/{x}/{y}.png`
  stacked over the MN LiDAR Hillshade above, as one radio entry
  (an `L.layerGroup` sharing the hillshade layer object with
  the Relief entry). The pistes are a transparent overlay with
  no base cartography; OpenSnowMap's own "base snow map" is
  deliberately NOT used (its author discourages use outside
  opensnowmap.org). Presence verified 2026-11-11 by sweeping
  all 192 z12 tiles over the chapter extent: 7 carry drawn
  pistes — the nordic ski trails around Itasca State Park
  (west edge) and the Leech Lake shore (east edge), with
  denser linework confirmed at z14 near Itasca State Park.
  Most of the corridor has no OSM pistes mapped; there the
  base reads as plain hillshade. Attribution: "Snow trails:
  OpenSnowMap, © OpenStreetMap contributors" (shown alongside
  the hillshade's own credit).

- **MN LiDAR Canopy** and **Canopy height (LiDAR)** — the
  second-generation LiDAR trio, completed Nov 11, 2026 (the
  trio's first member, the bare-earth shade, is the MN LiDAR
  Hillshade WMS above). These two are NOT live services: they
  are this repo's own tiles (`site/tiles/canopy-shade/`,
  `site/tiles/canopy-height/`, z9–15 — z16 was rendered and
  measured, then dropped: 1,466 more tiles for 152.5 MB, which
  would have taken the pair past the tens-of-MB class), built by
  `scripts/build_lidar_trio.py` from:
  - **Ground (DTM):** the MnGeo seamless second-generation
    0.5 m DEM (VRT:
    `https://g46prsaddst01.blob.core.windows.net/mntopo/dem_100k/2nd_Generation_Seamless_Lidar_DEM.vrt`),
    read windowed at 1 m. Same source family as the Becker
    County work-unit DEM (spring 2022 leaf-off survey,
    2022-05-15 → 2022-09-18, USGS Lidar Base Specification
    2021 rev. A).
  - **Surface (DSM):** first returns of the USGS 3DEP point
    clouds for the two corridor blocks — Becker County
    (project MN_BeckerCounty_2021_D21, flown spring 2022)
    and Upper Mississippi (project MN_UpperMissRiver_B22,
    flown 2022) — max height per 1 m cell, LAS noise classes
    7 and 18 excluded. **The DSM fork, for the record:** no
    published statewide second-generation DSM derivative
    exists (the MnGeo image service's 122 layers carry no
    canopy/first-return layer; the MnGeo blob store's
    derivatives are all ground-model products), and the
    block first-return DSM tiles and per-tile LAZ files are
    staged only on rockyweb.usgs.gov, which sits behind a
    bot wall (browser-UA gate, ~50 KB/s single stream, 429
    on any concurrency — measured 2026-11-11; ~250 corridor
    tiles were not viable through it). The same point clouds
    are mirrored as Entwine EPT datasets on the public S3
    bucket `usgs-lidar-public` (USGS Registry of Open Data),
    which serves freely; the build reads the EPT octrees
    directly (datasets MN_BeckerCo_1_2021 and
    MN_UpperMissRiver_{2,4,5,6}_B22 — work units 1 and 3 do
    not intersect the corridor; unit 4 carries nearly all of
    the Upper Mississippi corridor). To bound the build, the
    DSM uses octree nodes to depth 10 — a uniform ~24% subset
    of the corridor's points (~1.16 billion of 4.93 billion),
    ~4 first returns/m² in the band; a max-per-cell statistic
    is robust at that density in canopy. Canopy height =
    DSM − DTM, clipped at 0.
  - **Corridor:** both surfaces exist only within ~100 m
    either side of the depicted trail lines (tiles rendered
    over a 150 m half-width; edges are ragged by design —
    Paul's ruling: tiles fine, no clean cut). Outside the
    corridor there are no tiles.
  - **Leaf-off caveat:** the 2022 collection was flown in
    spring, leaf-off. Conifer heights read true; hardwood
    canopy heights read slightly LOW (branches, not leaf
    surface), and low brush is under-read. Clearcut/field
    detection — height near zero where the 2014/current
    aerials show open ground — is unaffected.
  - Attributions: "Canopy shade (LiDAR first returns, 2022):
    MnGeo / Minnesota DNR"; "Canopy height (LiDAR, 2022):
    MnGeo / Minnesota DNR". LiDAR data: Minnesota DNR /
    MnGeo second-generation elevation collection
    (2021–2024; corridor blocks flown 2022), via USGS 3DEP.
  - Build cost, measured on the 2026-11-11 run (Paul asked
    for the measurement): see
    `docs/lidar-trio-build-2026-11-11.md` — clean-run stages
    total ~81 min (index 455.5 s, DSM 1,231.8 s, DTM 1,650.1 s,
    tiles 1,343.8 s, check 168.1 s); shipped tiles z9–15,
    1,060 tiles / 82.7 MB. Stage timings also live in
    `working/lidar-trio/stage-timings.json` on the build
    machine (scratch, not in git).
  - Coverage (audited, 2,030 points every 100 m along both
    depicted lines): 90.0% of trail points have a finite canopy
    height. Two holes: (1) the northern loop, 13.8 km at lat
    47.154–47.174 — no 2022 coverage exists there (Becker's
    block ends at y-grid 5224; TNM shows zero Upper Mississippi
    B22 tiles over it; the only cover is the older RedRiver D23
    block, deliberately not mixed in); (2) one water crossing
    in Chip-10/Chip-11 where the seamless DEM is nodata over
    open water. See the build report for the full audit.

Removed bases (Nov 11, 2026, Paul's prune of the Nov 10 candidate
round; definitions and placeholder keys deleted from app.js):
**Topo (Esri World Topographic)**, **Terrain (Stamen)** (Stadia;
was key-gated, never keyed), **Streets (CARTO Voyager)**,
**Minimal (CARTO Positron)**, **Outdoors (Thunderforest)** (was
key-gated, never keyed), **Hillshade (Esri World)**, **High
contrast (OSM Humanitarian)**.

Removed bases (v3, Nov 10, 2026, Paul's calls): **Shaded relief
(USGS)** — The National Map `USGSShadedReliefOnly` service; cut as
poor data next to the 1 m LiDAR hillshade. **Aerial — MN spring
imagery (MnGeo)** — the WMS `nw14` layer above ("2014 color NW
50 cm", Spring Aerial Imagery Program 2013–14 leaf-off, 50 cm);
the service answers, but the photography shows nothing useful over
the chapter, so the base was cut.

### Chapter data (not external)

- Adopter segment boundaries: the chapter's own KMZ file
  (Google Earth format), to be converted to GeoJSON in
  `data/segments/`. Chapter property; no external attribution.
- Asset inventory: chapter volunteers' photographs, processed by
  the photo pipeline described in DESIGN.md. Batch 3 (Nov 18,
  2026): 39 photos, 38 positioned on the chopped Nov 18 track,
  18 new pins (102 total); each photo carries a facing direction
  (`direction_deg`, `direction_ref` "track" when inferred from
  the GPS track's bearing, "T"/"M" when read from EXIF) — front
  photos face the direction of travel, back photos the opposite;
  detail photos carry no direction. See
  `data/assets/flags-report-batch3.md`.

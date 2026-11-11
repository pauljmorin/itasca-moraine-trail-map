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
- **Fallback source (if the service is ever unavailable):** NPS
  DataStore, https://irma.nps.gov/DataStore/ — unit NOCO geospatial
  datasets. Not used to date.

## Minnesota county parcels — corridor clip

- **What:** Tax parcel boundaries with ownership attributes,
  compiled from opt-in counties (GAC parcel standard fields,
  including `owner_name` and `ownership`).
- **URL:** https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_mngeo/plan_parcels_open/FeatureServer
  (layer 1, "Plan Parcels Open"; layer 0 is the per-county metadata
  layer used for the coverage check). Commons page:
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
  extent, state miles 120.5–242). The site build keeps only
  points snapping within 250 m of the drawn lines (239 retained,
  5 excluded) as `site/data/milemarkers.geojson`, layer "Mile
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

## Leech Lake Reservation — boundary polygon (added 2026-11-11)

- **What:** The external boundary of the Leech Lake Reservation
  (Leech Lake Band of Ojibwe), one polygon, drawn as a separate
  toggleable context layer ("Leech Lake Reservation", off by
  default, lazy like parcels).
- **URL:** https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/AIANNHA/MapServer
  (layer 2, "Federal American Indian Reservations", queried
  `GEOID = '1940R'`, outSR 4326, GeoJSON)
- **Owner / publisher:** U.S. Census Bureau, TIGER/Line American
  Indian Areas (AIANNH). Public federal data; no licence
  restriction.
- **Vintage:** TIGERweb current (Boundary and Annexation Survey
  2026). The geometry is **identical** in the Census 2020
  (layer 26) and ACS 2025 (layer 14) vintages on the same
  service — same 9,685 vertices, same published areas
  (land 622,953 ac, water 215,678 ac, total 838,631 ac).
- **Why this source, and what lost:** the Census polygon is the
  pick because it is a single clean polygon of the reservation
  proper at the highest vertex density available, and it is
  stable across three vintages. Cross-checked against the
  **BIA AIAN-LAR national dataset**
  (https://biamaps.geoplatform.gov/server/rest/services/DivLTR/BIA_AIAN_National_LAR/FeatureServer,
  feature LAR0033 "Leech Lake"): same overall extent, geometry
  area within 1.8% (819,037 ac), boundary median separation
  37 m (p90 262 m, max 1,832 m; 73% of sampled vertices within
  100 m). BIA lost as primary because its feature is coarser
  (3,999 vertices in 3 polygons) and its GISACRES attribute
  (1,794,106) contradicts its own geometry (~819,000 ac).
  **PAD-US** was not fetched separately: its tribal lands
  derive from BIA AIAN-LAR, so it would duplicate that
  geometry. The Minnesota Geospatial Commons / LCC-GIS
  reservation dataset (`amerind2010`) is 2010 TIGER-derived
  and stale — not used. The Census **off-reservation trust
  land** feature for Leech Lake (GEOID 1940T, 0.05 sq km) is
  deliberately excluded: this layer is the reservation itself.
- **Trail overlap (measured 2026-11-11, geometry-measured
  against the depicted chain):** 2.28 mi inside the
  reservation, all of it on **Chip-12** (2.28 of its 3.98 mi);
  GAP-W and every other section are outside. The official line
  gives the same 2.28 mi. **White Earth check:** the White
  Earth Reservation (GEOID 4595R) touches the map extent's
  western margin but no depicted trail mileage falls inside
  it (0.00 mi; closest trail point 9.7 km from its boundary)
  — the obvious next polygon, not built here.
- **Use here:** Full unclipped polygon, pulled by
  `scripts/pull_leech_lake_reservation.py` into
  `data/native-nations/leech-lake-reservation.geojson` (working)
  and `site/data/leech-lake-reservation.geojson` (site copy,
  379 KB, lazy). The popup and the Sources card carry the
  line: *the federal reservation boundary as published — not
  a legal survey.* Tribal management/forestry data is NOT in
  scope here — that stays relationship-only, per the
  project's standing line.


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

- **Topo (OpenTopoMap)** — the DEFAULT base since v4.
  `https://tile.opentopomap.org/{z}/{x}/{y}.png`: OpenStreetMap
  data rendered with SRTM contours and hillshading. Attribution:
  "Map data: © OpenStreetMap contributors, SRTM | map style: ©
  OpenTopoMap (CC-BY-SA)".
- **Streets (OSM)** — the standard OpenStreetMap rendering,
  `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. Attribution:
  "© OpenStreetMap contributors".
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
  of 2014-12-30".
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
  the photo pipeline described in DESIGN.md.

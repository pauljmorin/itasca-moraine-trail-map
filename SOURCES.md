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

## Base-map tile & image services (map v2, added 2026-11-10)

Live map backgrounds, consumed directly by the site (nothing is
downloaded into the repo). Every endpoint was verified from the
project sandbox on 2026-11-10 by fetching sample tiles / WMS
GetMap responses over the chapter's extent.

**v4 (Nov 10, 2026):** the default base is now **Topo
(OpenTopoMap)** — a new visitor meets terrain first.

**Nov 11, 2026 prune (Paul's calls):** the switcher carries nine
bases in four task groups — Topographic (Topo (OpenTopoMap),
USGS Topo 1:24k, National Geographic (Esri)), Relief (MN LiDAR
Hillshade), Aerial (Aerial (USGS NAIP), Aerial (Esri), Aerial +
Topo (USGS ImageryTopo)), Streets & trails (Streets (OSM),
Trails (CyclOSM)). Seven entries from the Nov 10 review round
were removed outright (see "Removed bases" below), including the
two key-gated ones and their placeholder keys.

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
- **Aerial (USGS NAIP)** — The National Map (USGS),
  `https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}`
  (NAIP-based imagery). Attribution: "Aerial imagery: USGS, The
  National Map (NAIP)".
- **Aerial (Esri)** — Esri World Imagery —
  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`.
  Attribution: "Aerial imagery: Esri, Maxar, Earthstar
  Geographics".

**Also in the switcher:**

- **Aerial + Topo (USGS ImageryTopo)** — The National Map,
  `.../USGSImageryTopo/MapServer/tile/{z}/{y}/{x}` (NAIP imagery
  with topo labels/contours).
- **National Geographic (Esri)** — Esri,
  `.../NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}`.
- **Trails (CyclOSM)** —
  `https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png`.

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

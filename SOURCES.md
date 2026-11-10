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

- **Shaded relief (MN LiDAR)** — Minnesota Geospatial Image
  Service (MnGeo), WMS 1.1.1, Web Mercator endpoint
  `https://imageserver.gisdata.mn.gov/cgi-bin/wmswm?`, layer
  `hillshd` ("Statewide"): hillshade derived from 1 m LiDAR
  (statewide elevation collection 2008–2012; Minnesota Department
  of Natural Resources / MnGeo). Wired via `L.tileLayer.wms`,
  non-transparent base. Attribution: "Shaded relief (LiDAR
  hillshade): MnGeo / Minnesota DNR".
- **Topo (USGS 1:24k)** — The National Map (USGS),
  `https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}`:
  the USGS topographic base built from the 1:24,000 quadrangle
  series. Added Nov 10, 2026 (v3); sample tile over the chapter
  verified live the same day. Attribution: "Topo: USGS, The
  National Map".
- **Aerial — USGS NAIP** — The National Map (USGS),
  `https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}`
  (NAIP-based imagery). Attribution: "Aerial imagery: USGS, The
  National Map (NAIP)".
- **Aerial — Esri World Imagery** —
  `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`.
  Attribution: "Aerial imagery: Esri, Maxar, Earthstar
  Geographics".

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

# Driftless Hiking Trail — verification note, Nov 16, 2026

Paul asked for the Driftless Hiking Trail in the ITM viewer as a Partner
Trail (same as the Border Route Trail), plus parcel information for the
existing trail and the planned trail. This note records what was added,
what was measured, what could not be verified, and what is still owed.

**Status: wired in the viewer, NOT deployed, NOT committed, NOT pushed.**
`node --check site/app.js` passes. A live-browser check of the new
layers (toggle on, popup click) is still owed.

## County correction

**All four built segments are in Iowa County, WI — not Sauk County.**
The brief's "Sauk Co." label was wrong. Spring Green village is Sauk
County, but the trail segments sit south of the Wisconsin River in Iowa
County. Taliesin geocodes 43.14196, -90.06907 (Iowa County). The parcel
layer label reads "Iowa Co., WI" and the trail popup says Iowa County.
The half-mile parcel buffer does cross the river county line: 8 of the
261 parcels are Sauk County, and each parcel's popup names its own
county from the record.

## Job 1 — built trail, assembled (DONE)

4 features, **6.340 GIS miles** total, in
`data/driftless/driftless-trail.geojson` (source of record) and the
byte-identical viewer copy `site/data/driftless-trail.geojson`
(MD5 1d492ef5d54177a870ed469442b25f33). Repeatable pull script:
`scripts/pull-driftless.py` (OSM API bbox endpoint; Overpass is down
from this VM; parsed with xml.etree, never regex).

| Segment | Source | GIS mi | DALC publishes | Notes |
|---|---|---|---|---|
| Phoebe Point Trail | OSM way 1248941083, 74 pts | 0.685 | ~1.1 | Map loop measures 0.66 mi — same trail as OSM. The 1.1 mi figure is the outlier, possibly incl. the Oct 2026 connector, which is on neither OSM nor this trifold. Use the OSM way; do NOT trace. |
| Welsh Hills Trail (inner) | OSM way 1248943005, 98 pts | 1.113 | ~1 + 2.6-mi Ridge Section | OSM carries only the inner chord. |
| Welsh Hills Trail (outer loop) | Traced from the trifold map, 26 pts | 2.085 | 2.6 (Ridge Section) | See georeferencing section. Traced because OSM lacks it. |
| Knobs Road Trail | OSM way 1248953013, 90 pts | 2.457 | ~2.7 | OSM line's two ends both touch Knobs Road 1.58 km apart; the loop is left OPEN in the data — no tread invented to close it. The trifold draws a closed oval; the closing leg is the road walk / unmapped. |
| Weaver Road | — | — | ~1.1–1.5 | **Not drawn.** Not in OSM (no named footway in two bbox fetches around the trailhead junction 43.05585, -90.11263) and no trifold PDF exists for it. Known gap. |

DALC's published figures run consistently higher than the ground
geometry (Phoebe 1.1 vs 0.685, Ridge 2.6 vs 2.085, Knobs 2.7 vs 2.457).
The traced and OSM lines are the ground geometry; the published
figures likely include approaches and connectors not on the maps.
The popup and data-sources entry say this plainly.

## Georeferencing — Welsh Hills trifold map

Source document: Driftless Area Land Conservancy, Welsh Hills Segment
trifold, `DT-Trifold-Welsh-Hills-Segment-11-x-8.5-in.pdf`
(https://driftlessconservancy.org/wp-content/uploads/2026/04/DT-Trifold-Welsh-Hills-Segment-11-x-8.5-in.pdf),
saved at `data/driftless/sources/trifold-welsh.pdf`. The Knobs trifold
(`data/driftless/sources/trifold-knobs.pdf`) was cropped and viewed
but NOT traced — the OSM Knobs way already covers that ground.

**Map judgment: a stylised tourist map, drawn to an approximately
consistent scale, with local distortion. No scale bar, no north arrow
on either trifold.** Scale confirmed at 3.28 m/px independently by
BOTH OSM ways (Phoebe and Welsh), so the map is not schematic — but
it is not survey-grade either.

Affine fit to 4 ground control points (coefficients in
`data/driftless/tw300-affine-gcps.json`):

| GCP | Map px | Real-world lon/lat |
|---|---|---|
| Bridge over the Wisconsin River | (486.6, 407.0) | (-90.0610354, 43.1455595) |
| Tower Hill State Park SW corner | (726, 321) | (-90.0505867, 43.1444444) |
| Phoebe Point Trail base | (173, 482) | (-90.0736935, 43.1432806) |
| Hwy 23 × County T junction | (390, 799) | (-90.0651242, 43.1335806) |

GCP residuals 64–157 m. Registration of the OSM trails against the
map's red line is better: Phoebe median nearest-red 4.9 px (~16 m),
Welsh 11.2 px (~37 m). **Traced lines are approximate to about ±50 m
typical, ±100 m worst case** — labelled "approximate" in the data
(`accuracy` property), the popup, the legend and data-sources.html.

Trace method: `data/driftless/trace-trifold-maps.py` (Zhang–Suen
thinning + polar outermost-binning; the outermost-binning version,
2.085 mi, 26 pts, visually verified against the red line, is the
accepted trace — an earlier run's 2.494 mi was spike-inflated and is
superseded). Earlier centroid-walk and skeleton-walk versions failed
(backtracking / strand bugs) and must not be reused. There is no GDAL
on this VM; the fit is a plain affine transform in numpy, not a
gdalwarp — the georeferenced image + GCP list are saved under
`data/driftless/` (`tw300-*.png`, `tw300-affine-gcps.json`,
`tw300-affine-coef.npy`), not a GeoTIFF.

## Job 2 — planned route (NO GEOMETRY EXISTS — nothing drawn)

**No published GIS geometry exists for the planned / full Driftless
Trail route, and the corridor is not definable as a line from the
published descriptions.** Checked Nov 16:

- Blue Mounds Area Project newsletters (Spring 2025, Spring 2026,
  Winter 2026, Feb 2026 eBulletin): contain Driftless Trail pieces
  but NO loop map.
- NPS Rivers, Trails and Conservation Assistance concept plan: not
  found as a published document.
- DNR Western Coulees and Ridges draft plan maps: property-level
  only, no trail corridor.
- Trifold maps (Knobs, Welsh Hills): show BUILT segments only.
- OSM: no "Driftless Trail" relation exists; no `proposed` tags
  found for the loop.
- Trailforks: login-walled — NOT used, per the brief.

Per the brief (and Paul's redirect), **nothing was drawn for the
planned route and no `driftless-planned` layer was wired** — no rough
line traced off a map image, no invented corridor. The popup, legend
and data-sources entry all state that no planned line is drawn and why.
If DALC or the county ever publishes GIS for the planned loop, wire it
then as `driftless-planned` (dashed, same colour family, OFF + lazy).

## Job 3 — parcels (DONE, built trail only)

261 unique parcels in `data/driftless/parcels-driftless.geojson` and the
byte-identical viewer copy `site/data/parcels-driftless.geojson`
(MD5 71bbfeb61be092b00fc05a9f145e4f5a; 262,819 bytes). Pull script:
`scripts/pull-driftless-parcels.py`.

- **Source:** Wisconsin Statewide Parcel Map Database V12 (2026),
  layer `V1200_WisconsinParcels_2026` (3.56M parcels),
  `https://services3.arcgis.com/n6uYoouQZW75n5WI/ArcGIS/rest/services/Wisconsin_Statewide_Parcels_DB/FeatureServer/0`.
  The URL in the V11 schema doc (`Wisconsin_Statewide_Parcels`) is
  stale/renamed — the live service is `Wisconsin_Statewide_Parcels_DB`.
  Metadata saved at `data/driftless/v12-layer-metadata.json`.
  The V3 service (`RR_Properties_ARWs`) returned count 0 for Knobs +
  Dodgeville — empty/broken, not used. County-direct was not pursued:
  Iowa County charges $500 countywide / $100 per town — do not buy.
- **Buffer:** 0.5 mile around the built trail lines (Taliesin cluster
  158 parcels, Knobs cluster 103). Envelope counts before filtering:
  Taliesin 194, Knobs 141.
- **Fields kept:** PARCELID, TAXPARCELID, OWNERNME1, OWNERNME2,
  SITEADRESS, CONAME, GISACRES, PARCELDATE, TAXROLLYEAR, PARCELSRC
  (+ `county` and `source` added by the pull). 258 of 261 carry an
  owner name; 96 carry a site address (most rural parcels have none).
- **Fence (same as the Minnesota parcels):** published county records
  only. EXCLUDED: PSTLADRESS (owner mailing address) and all
  value/tax fields (CNTASSDVALUE, LNDVALUE, IMPVALUE, ESTFMKVALUE,
  NETPRPTA, GRSPRPTA). Verified: no taxpayer-ish field is present in
  the file.
- **Method note:** the service's server-side polygon query timed out
  at 120 s on the first attempt, so the pull queries by envelope
  (fast) and applies the 0.5-mi buffer filter client-side with
  shapely. The script documents this.
- **Planned-corridor parcels:** none — no planned geometry exists,
  so no planned corridor is definable (see Job 2). This is stated
  in the data-sources entry.

## Viewer wiring (DONE, not deployed)

- `driftless` — id "driftless", label "Driftless Hiking Trail",
  group "Other trails", subgroup "Partner Trails" (with BRT + SHT),
  OFF by default + lazy, bold line via `boldLine()` (white casing +
  weight-5 core), colour **#15803d** (green — distinct from BRT red
  #b91c1c, SHT blue #2563eb, ATV purple #762a83, OHM magenta #c51b8a,
  snow icy blue #67a9cf, loops teal #0f766e, near-BRT amber #d97706).
  Popup per segment: name, length, source, the built-pieces-only note,
  and the approximate-line note on the traced outer loop.
- `parcels-driftless` — id "parcels-driftless", label "Parcels —
  Driftless area (Iowa Co., WI)", group "Land ownership", OFF by
  default + lazy, `parcelStyle` corridor-ring treatment, popup
  mirroring the Minnesota parcels popup fields (parcel, county,
  acres, owner, site address, parcel ID, source).
- Draw order: "driftless" sits with the other Partner Trails
  (after "brt", before "near-brt-sht", under the NCT tread);
  "parcels-driftless" sits directly after "parcels" in the
  land-ownership fills.
- Legend rows added for both layers; data-sources.html entries added
  for both (Driftless Hiking Trail; Parcels — Driftless area).
- NOT touched: basemap defs, BASES, MAPBOX_TOKEN, MAPTILER_KEY,
  STADIA_KEY, the GeoPDF export files, the Minnesota parcels layer
  and its data. `git diff` on `site/app.js` is +142 lines with only
  the 4 draw-order/comment lines rewritten; data-sources.html is
  pure additions.

## What could NOT be verified

- The planned ~100-mile loop's route: no published geometry exists
  (see Job 2). Any "planned corridor" would be invented.
- Weaver Road segment geometry: built, but in no public source found
  (no OSM way, no trifold, no county GIS hit). Its ~1.1–1.5 mi is
  missing from the layer; the layer total (6.34 mi) is therefore
  short of the ~7–9 mi built total DALC quotes.
- DALC's published segment lengths vs the ground geometry (see the
  table above) — the discrepancy is noted, not resolved; the
  published figures likely include approaches/connectors not on
  the maps.
- The Knobs loop's closing leg: the trifold draws a closed oval but
  OSM's line is open (ends on Knobs Road 1.58 km apart). Whether
  the closing leg is the road walk or unmapped tread is not
  established from public sources.
- Live rendering: the layers have not been toggled on in a browser
  (no live-browser check in this session). The files, defs, legend,
  draw order and attribution were verified on disk only.

## Still owed

1. Live-browser check: toggle both layers on, click a trail segment
   and a parcel, confirm popups and the legend rows render.
2. Weaver Road geometry — needs a published map or OSM mapping;
   re-run `scripts/pull-driftless.py` if it appears in OSM.
3. Planned-route geometry — needs DALC / county publication; then
   wire `driftless-planned` (dashed) + planned-corridor parcels.
4. Deploy / commit / push — none authorized in this session.
5. Parcel refresh cadence — V12 is the 2026 vintage; revisit when
   V13 (2027) lands, same as the Minnesota parcels' ~6-month refresh.

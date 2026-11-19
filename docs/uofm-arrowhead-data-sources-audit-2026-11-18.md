# U of M Arrowhead report — data-sources audit

**Date:** 2026-11-18
**Report audited:** North Star Consulting, "North Country National Scenic Trail Route Plan",
December 8, 2025 (GIS 8501, 18 MGIS students) — `site/buildout/src/uofm-arrowhead-report.txt`
(476 lines; checked against the PDF, `site/buildout/src/uofm-arrowhead-report.pdf`, 14 pp —
the .txt is complete, including Appendix A on PDF p. 13).
**Derived layers audited:** `site/buildout/data/*.geojson` + `site/buildout/build-data.py`,
`build-soils.py`, `build-motorized.py`, `build-motorized-bc.py`.

## Standing position (Paul, Nov 18, 2026, voice — recorded, not re-litigated)

The U of M work was a student group project. The students did it themselves, did no
fieldwork, and are not authoritative on alignment. The proposed reroute line and its phased
gap segments are therefore **not** to be presented as authoritative layers. What is useful
is **their data sources** — which sources they used, and which of those are useful for our
trail work. This audit reads the sources only.

## How "already in" was checked

For each source below, the check was: grep `SOURCES.md` for the dataset/service name,
check `site/data/` (and `data/access/`) for a file built from it, and grep `site/app.js`
for a layer wired to it. A source counts as "Already have" only when all three agree
(the dataset is documented, pulled, and wired or deliberately held in buildout).

## Source table — the report's Appendix A (PDF p. 13; .txt lines 405–431) + §VI

| # | Data layer (as cited) | Source as cited | Used for (report) | Verdict | Why / check |
|---|---|---|---|---|---|
| 1 | Current Proposed Trails | North Country Trail Association | The modeled alignment itself | **Don't use** (as authoritative) | This is the students' own least-cost-path output, not an NCTA line. The KML in src is named "North Country Trail - proposed 102 miles" (`site/buildout/src/proposed-arrowhead.kml`); report §V (p. 10) calls the shapefile/KML "the modeled NCT alignment". 30 m raster, no fieldwork (report §III, pp. 5–7). Keep in buildout only, labeled as the student model. |
| 2 | Trail Boundary (2004 corridor) | North Country Trail Association | Study-area polygon | **Already have** | Live in the viewer as the "Arrowhead reroute polygon" (`site/data/arrowhead-reroute-polygon.geojson`, from `site/buildout/src/corridor-2004.kmz`). SOURCES.md §"Arrowhead reroute polygon" confirms it is the corridor the report uses as its study area ("provided by NCTA", report p. 4). |
| 3 | Parcels | State of MN — OpenParcels `plan_parcels_open` MapServer (utility.arcgis.com URL in the report) | Ownership / suitability | **Already have** | Same dataset, different endpoint: SOURCES.md §"Minnesota county parcels" pulls `plan_parcels_open` layer 0 from the MnGeo enterprise host (`enterprise.gisdata.mn.gov/aghost/.../plan_parcels_open/FeatureServer`), pulled 2026-11-10. The report's utility.arcgis.com URL is the ArcGIS Online proxy of the same service. |
| 4 | Campgrounds | MN Geospatial Commons — `struc-state-forest-campgrounds` | Attractive nodes in the suitability model (report §III, p. 6) | **Use** | Authoritative DNR dataset, **not yet in the viewer**: no SOURCES.md section, no file in `site/data/`, no `app.js` layer. The viewer has NCTA camping waypoints (`campsites-arrowhead.geojson`, `chapter-places.geojson`) but not the DNR state-forest campground inventory. Genuinely new; useful for hiker services near the corridor. |
| 5 | Bridges | MN Geospatial Commons — `trans-bridges` | Crossing opportunities (report §III, p. 7: pedestrian/mixed-use only, buffered) | **Use** | Authoritative MnDOT bridge inventory, **not yet in the viewer**: zero hits in `SOURCES.md` as a dataset and zero in `site/app.js`. Useful for crossing planning — where a hiker can actually get across a river or highway. |
| 6 | Current Trails | MN Geospatial Commons — `trans-state-trails-minnesota` | Existing non-motorized trails as low-cost corridors | **Already have** | In the viewer since 2026-11-10: SOURCES.md §"Access layers", `source_type: state_trail`, `data/access/access-lines.geojson`. |
| 7 | Bike Trails | MN Geospatial Commons — `trans-bikeway` | (Listed; no distinct use described in Methods) | **Don't use** | Already evaluated for the only purpose we had: SOURCES.md shoulder section records the BIKEWAY FeatureServer as WAF-blocked to text fetch and the Bikeways Data Standard v1.0 (Jan 2022) as having no numeric shoulder-width field. As a bike-route layer it duplicates the state-trails data we already carry. No new value. |
| 8 | Snowmobile Trails | MN Geospatial Commons — `trans-snowmobile-trails-mn` | Motorized-use context | **Already have** | In the viewer: SOURCES.md §"Access layers", `source_type: snowmobile_trail`; and `site/buildout/data/motorized-snow.geojson` (26 features) was built from this same service by our `build-motorized.py`. |
| 9 | Roads | MN Geospatial Commons — `trans-road-centerlines-open` | Road surfaces as constraints; crossings | **Already have** | In the viewer: SOURCES.md §"Roads — road centerlines", `data/access/roads.geojson`, pulled 2026-11-10. |
| 10 | ATV Trails | "State of MN" — `trans-state-park-trails-roads` | Motorized-use context | **Don't use as cited** — the citation is wrong | `trans-state-park-trails-roads` is the **state park trails and roads** dataset (DNR Parks and Trails; in our viewer it is chiefly the Itasca State Park network — SOURCES.md §"Access layers"). It is not an ATV dataset. The correct ATV source is the DNR OHV service, `trans_ohv_trails_mn`, which we **already have** (SOURCES.md §"Access layers", `source_type: ohv_trail`; `site/buildout/data/motorized-atv.geojson`, 1,074 features, built from it by our `build-motorized.py`). The students' ATV row points at the wrong dataset. |
| 11 | Wetlands | Living Atlas — `USA_Wetlands` FeatureServer | Hydrologic constraint (high cost) | **Don't use the mirror** | Esri's Living Atlas USA Wetlands is a hosted copy of the USFWS National Wetlands Inventory (NWI Version 2, derived from NWI digital data plus NHD supplementation; that service copy last edited 2020). It is a derivative, not the authoritative service. Our wetlands work (approved GO Nov 18, 2026) pulls NWI from the FWS service directly (`fws.gov/wetlands/.../Wetlands/MapServer`). Use the FWS service, not the mirror. Note the report treats wetlands only as a bulk constraint, with no Cowardin classification — the Nov 18 classification work (rules W1–W10) is ours, not theirs. |
| 12 | Lakes | DNR / MN Geospatial Commons — `water-dnr-hydrography` | Hydrologic constraint | **Don't use as a layer** | Authoritative DNR dataset, but redundant as a viewer layer: water bodies are already visible on the basemap, and the routing constraint that matters is wetlands, which NWI covers (being wired). No separate lake layer adds a decision. |
| 13 | Rivers | DNR / MN Geospatial Commons — `water-dnr-hydrography` | Hydrologic constraint | **Don't use as a layer** | Same as Lakes: authoritative, but redundant with the basemap and NWI. |
| 14 | Surface water | MN Geospatial Info Office — `mngeo.state.mn.us/chouse/water.html` | (Listed; no distinct use) | **Don't use** | That URL is the MnGeo data-clearinghouse landing page, not a dataset. Student-grade citation; nothing to pull from it. |
| 15 | MnDOT right-of-way GIS | MnDOT — `dot.state.mn.us/maps/gisweb/row/` | (Not in Appendix A; recommended in §VI, report p. 10, .txt lines 343–345) | **Use** | Statewide transportation right-of-way maps. **Not in the viewer** (zero hits in `SOURCES.md`). Genuinely new and the most useful planning source in the report: it is where co-located or parallel trail segments on existing ROW would be identified — exactly the Ely bottleneck problem the report flags. Evaluate as a layer (or at minimum as a reference for the Arrowhead gap work). |

## Derived layers in `site/buildout/data/` — where each actually came from

These are **our** build scripts (Nov 13–14, 2026), not the students' products. Only the
first two derive from student/chapter files at all:

| Derived file | Actual source | Grade |
|---|---|---|
| `proposed-arrowhead.geojson` | `site/buildout/src/proposed-arrowhead.kml` ("North Country Trail - proposed 102 miles") — the students' modeled least-cost-path line, converted by `build-data.py` §1 | Student-grade. Not authoritative; do not present as a route. |
| `proposed-western.geojson` | `site/buildout/src/mwp-plan.kml` ("Minnesota Waters and Prairie NCTA Chapter plan") — a **chapter-volunteer-drawn** plan (off-road plan Frazee–Abercrombie), converted by `build-data.py` §2. Not a student product and not field-verified either. | Volunteer sketch. |
| `corridor-2004.geojson` | `site/buildout/src/corridor-2004.kmz` — the NCTA 2004 corridor, converted by `build-data.py` §3. Already live in the main viewer. | NCTA corridor (authoritative as a planning container). |
| `soils-corridor.geojson` (7,273 features) | **Our** `build-soils.py`: USDA NRCS Soil Data Access (SDA) tabular REST — SSURGO map units (`musym`, `muname`, drainage, hydric, slope, flood) — clipped to a 0.5-mi buffer around the gap lines. **Not in the students' source list at all** — they cite no soils source (0 hits for soil/SSURGO in the report). | Authoritative (NRCS), but with a gap: it does **not** include the NRCS "Paths and Trails" rating, which the Nov 18 classification work identifies as the backbone for the soils call (rules S1–S8). The wiring work should add that rating rather than treating drainage/hydric alone as the call. |
| `soils-corridor` companion: `nlcd-corridor-stats.json` | **Our** `build-soils.py` Part B: NLCD 2021 via MRLC GeoServer WCS (`mrlc_display:NLCD_2021_Land_Cover_L48`), histogram only (pixel counts per class inside the buffer). Also not a student source. | Authoritative (USGS/MRLC), statistics only — no polygon layer. |
| `motorized-atv.geojson` (1,074 features) | **Our** `build-motorized.py`: MN DNR OHV trails service (`trans_ohv_trails_mn`), cross-checked against the DNR A-Z trail listing. Not the students' cited source (see row 10 — they cited the wrong dataset). | Authoritative (DNR). |
| `motorized-snow.geojson` (26 features) | **Our** `build-motorized.py`: MN DNR snowmobile trails service (`trans_snowmobile_trails_mn`). | Authoritative (DNR). |
| `motorized-atv-bc.geojson` | **Our** `build-motorized-bc.py`: same DNR OHV service, Becker County systems. | Authoritative (DNR). |
| `gap-arrowhead.geojson`, `gap-western.geojson` | Cuts from our own `site/data/trail-minnesota.geojson` (NCTA trail line), by `build-data.py` §§4–5. | Authoritative (NCTA). |
| `gap-streetview.geojson` | Hand-picked points from our own gap research (§6), by `build-data.py` §6. | Our research. |

## Flags

1. **ATV citation is wrong (row 10).** The report's Appendix A points "ATV Trails" at
   `trans-state-park-trails-roads`. That dataset is state-park trails/roads, not ATV.
   The correct source — the DNR OHV service — is what our build scripts used and what
   the viewer already carries. Do not repeat the students' citation.
2. **Wetlands via a mirror (row 11).** The students used Esri's Living Atlas copy of
   NWI, not the FWS service. Ours uses the FWS service directly. Same underlying data,
   but the mirror is a 2020-vintage derivative; do not wire the mirror.
3. **No soils, no NLCD, no elevation in their source list.** The report contains zero
   mentions of soil, SSURGO, or NLCD, and LiDAR/DEM appears only as a future
   recommendation (§VI, p. 10). The soils and NLCD material in our buildout is ours,
   not theirs — do not attribute it to the U of M work.
4. **Stale county `wetlands.zip` (2017, 46.4 MB): not used by the students.** No
   conflict — the report's wetlands source is the Living Atlas NWI copy. The 2017
   county file remains rejected for our work.
5. **Corridor-buffer wording — already resolved.** The report's "buffered version" of
   the corridor (p. 4) is a modest buffer of the 1,243-sq-mi 2004 corridor. It is not
   our 140-sq-mi gap-line buffer (`corridor-buffer-arrowhead.geojson`). SOURCES.md
   already records this distinction (Nov 18, 2026). No live contradiction.
6. **Self-disclosed method limits (report §III, p. 7).** 30 m raster cannot capture
   fine-scale microtopography, small streams, or short steep slopes; the seven-class
   scale compresses complex factors (notably: all private parcels scored uniformly
   difficult, which the report itself flags as unrealistic). These limits are the
   reason the modeled line is a screening tool, not a route.
7. **No contradiction with our verified data** beyond flags 1 and 5. The report's
   "~150 miles" of Arrowhead gaps (p. 3) describes the current road-walk-heavy
   alignment, not the 102-mile modeled line — different quantities, not a conflict.
   County coverage matches ours (Itasca, St. Louis, Lake; Aitkin overlap minimal,
   Aitkin parcels excluded — report p. 5).

## What their sourcing adds

Almost nothing in the report's source list is new to us: of the fourteen Appendix A
rows, eight are sources the viewer already pulls and wires, two (lakes, rivers) are
authoritative but redundant as layers, and three (bike trails, the wetlands mirror, the
surface-water landing page) are not worth using. The real additions are three: the DNR
state forest campgrounds dataset, the MnDOT bridge inventory — both authoritative,
both absent from the viewer, both directly useful (places to camp; places to cross) —
and the MnDOT statewide right-of-way GIS resource from §VI, the most useful planning
lead in the whole report for the Ely bottleneck. The audit also corrects the record in
two places that matter going forward: the students' "ATV Trails" citation points at
the wrong dataset (state park trails, not the DNR OHV service we already use), and
the soils and NLCD material in our buildout is ours, not theirs — the students cited
no soils source at all.

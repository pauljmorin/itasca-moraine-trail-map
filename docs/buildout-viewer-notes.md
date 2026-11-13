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
- Street View points from the two gap research files §6; all
  `verified:false` — panorama existence not yet live-confirmed.

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
  78.38 mi on-road (90 features). The 8.77-mi difference sits in the
  research file's off-road figure (13.75 mi vs 5.38 mi in the cut); no
  additional chain segment in the NCTA data accounts for it, and haversine
  re-measurement agrees with `len_miles` (104.51 mi). Most likely the
  research chain double-counted the 8.35-mi Becker connector (8.35 + 0.44
  ≈ 8.79 ≈ the gap). The viewer headlines use the research/assessment
  figures (106.1-mi gap, 113.63-mi traced chain) with sources labeled, and
  the legend shows the drawn file's own totals. Resolve before citing the
  113.63 figure in a meeting as the drawn line's length.

## Hard rules enforced (v1)

- $643,850 (Proposal 2027-179) everywhere, labeled "Not Submitted Final,"
  Mar 14, 2026. $800,000 appears nowhere.
- No parcel-count claim. Mesabi shown as disputed, never complete
  (Lottery "complete" Oct 2026 vs LCCMR 2027-341 $1.65M for final 2.5 mi
  by June 30, 2029 — to confirm with the Railroad Authority).
- Road type leads; speeds only as the 55 mph statutory default, labeled
  as a default, and not shown for town-traverse segments.
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

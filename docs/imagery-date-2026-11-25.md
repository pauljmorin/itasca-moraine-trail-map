# Imagery date readout + Sentinel-2 scene-date selector — Nov 25, 2026

Paul, Nov 25, 2026: "Put the satellite imagery from the Leech Lake
viewer in the ITM viewer. Also, can you put the date of the imagery
somewhere it makes sense? in the corner of the map or something?"
Then: "the Landsat and Sentinel imagery have dates, and I want a date
selector of some kind in the right place."

## What the Leech Lake viewer actually has (Step 1 finding)

The Leech Lake viewer's satellite imagery is Esri World Imagery
(current) plus Esri Wayback year-end releases 2014–2026. The ITM
viewer already had the current layer and every Wayback year that is
genuinely distinct over the corridor:

- Wayback 2015, 2016, 2017: proven duplicates of the 2014 base
  (Nov 13, 2026 — all resolve to release 31144, 2014-06-11).
  Not added, then or now.
- Wayback 2026 (release 3692, 2026-11-18): re-checked Nov 25,
  2026 — byte-identical JPEGs to release 13192 (2025) at all 3
  corridor points (z12). Adds no new imagery over the corridor.
  Not added.
- Leech's MnGeo regional layers (2013 north fringe, 2018 Itasca,
  2020/2023 Beltrami) were already checked Nov 13 and rejected
  for coverage (bboxes north of the trail or no trail coverage).

So no new satellite layer was added: the work is the date readout
and the Sentinel-2 date selector. The Leech Lake viewer's satellite
imagery is already in the ITM viewer; what it lacked was the date.

## The date readout (corner chip)

A small chip in the map's bottom-right corner, under the
attribution, reading "Imagery: <date>". Visible ONLY while an
imagery base is active; hidden for Topo, Streets, LiDAR Shaded,
USGS Topo, National Geographic and White.

The date per base (all measured or stated, never invented):
- Aerial (Esri, current): "Jun–Sep 2025" — measured Nov 25 via
  the service's identify (SRC_DATE) at 3 corridor points: west
  4 Jul 2025 (WV03, 0.31 m), middle 2 Jun 2025 (WV02, 0.5 m),
  east 26 Sep 2025 (WV02, 0.5 m). The mosaic is living; the date
  varies by location.
- Wayback years: the capture year where measured (2025 release =
  2024 photos, 2023 = 2019, 2022 = 2021, 2021 = 2017–19,
  2019 = 2017, 2014 = 1999); unmeasured ones (2018, 2020, 2024)
  show their release month ("Dec 2024 release").
- NAIP / CIR years: the flight season and year ("Summer 2025",
  "Spring 2013, leaf-off", "1991").
- Aerial + Topo: "NAIP 2023/25".
- Sentinel-2: the chosen scene date, or "Latest scene".

Implementation: `imageryDateFor(def)` in site/app.js derives the
date from the base's `meta` string (second " · " segment), with
explicit `date` overrides on "Aerial (Esri)" and "Aerial + Topo"
and the dynamic Sentinel-2 date. `showImageryDate()` is called
from `setBase()` and once at startup. Styling: `.imagery-date`
in site/style.css.

## The Sentinel-2 scene-date selector

The ten Sentinel-2 renders are the service's latest-scene mosaic
by default — and the latest scene over the corridor is often
cloud (17–24 Nov 2026 scenes are 80–100% cloud). The selector
sits below the aerial metadata readout and appears only while a
Sentinel-2 base is active.

- Dates are fetched LIVE from the service on first use
  (`Sentinel2/ImageServer/query`, corridor bbox lon
  −95.62…−94.28, lat 46.93…47.19, `cloudcover<0.3`, newest
  first, deduplicated by UTC day, cloud = worst tile in the
  scene, 12 most recent days), so the list never goes stale.
- Choosing a date passes that UTC day to every tile render as
  the exportImage `time` parameter, which restricts the mosaic
  to rasters acquired that day. Verified Nov 25 at a Park Rapids
  bbox: no-time, 14 Nov 2026 and 10 Oct 2026 are three different
  JPEGs.
- The selector, the Sentinel-2 button subs, the metadata line
  and the corner chip all follow the chosen date; "Latest scene"
  clears it. The choice is session-only (not in the share hash).
- If the scene list cannot be fetched, the selector says so and
  the layer keeps showing the latest scene.
- Recent clear dates measured Nov 25: 14 Nov 2026 (0–6% cloud),
  12 Nov 2026 (0%), 20 Oct 2026 (0–10%), 10 Oct 2026 (0–2%).

## Landsat

No selector, and no live Landsat layer in either viewer. The only
Landsat anywhere in the pair is the Leech viewer's static MnGeo
WMS mosaic ("Aerial 2002–04 (Landsat)", 30 m) — a single vintage.
Esri's Landsat ImageServer was checked and not added (30 m,
strictly coarser than Sentinel-2's 10 m; see SOURCES.md).

## Verification

See the verification section in the branch report (headless checks
against the worktree build). No deploy — Paul gets the put-live
call.

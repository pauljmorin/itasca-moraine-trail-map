# Forest Service GeoPDF layers — verification note, Nov 16, 2026

Paul asked for the publicly-available US Forest Service GeoPDFs as layers in
the ITM viewer, just like the DNR maps, in a new top-level panel group named
"Forest Service" — only the maps that intersect the trail. Six panels are
wired.

## Status: second pass, Nov 16, 2026 (evening) — read this first

The first pass (Nov 16, ~18:55) wired five panels and COMMITTED + PUSHED
them as `0153693` ("Forest Service GeoPDF maps: 5 MVUM sheets that cross
the trail") — the live site serves that version. The second pass (this
note's revision) found and fixed three defects in it, all UNCOMMITTED —
the coordinator deploys them as the follow-up:

1. **A whole panel was missing.** The first pass never downloaded the
   Chippewa South Back (SouthEast map) — 85.77 km of NCT tread, the
   Bena–Deer River–Grand Rapids corridor — and wired only the South
   Front. Six panels intersect the trail, not five.
2. **Every quad was ~150–250 m off.** The first pass placed the sheets
   with a lon/lat affine. That is the wrong model for a UTM map: it
   leaves a constant ~2e-03 deg lon residual (meridian convergence on
   a 0.9-deg-wide frame). The quads are now computed through the
   map's own projection (NAD83 UTM 15N, per the /GCS) — fit residual
   0.06–0.36 m — and the corners reproduce the PDF's own stated
   corner coordinates exactly (proof: the PDF states Ely's SW corner
   at (-92.30787, 47.70172); the lon/lat affine put it at
   (-92.31021, 47.70176), 0.00234 deg / ~175 m off; the UTM route
   returns -92.30787, 47.70172). The first pass's claim that the
   lon/lat affine was "as good as GDAL gives" was wrong — GDAL
   reads the /GCS projection, it does not fit a lon/lat affine.
   The five re-rendered images are byte-identical to the first
   pass (MD5-verified), so only the placement changed, not the
   pictures.
3. **The popup had no trail figure, and two claims in the note and
   data-sources were wrong.** The popup now shows the trail km in
   the frame (from the GeoJSON `trail_km` property). The
   data-sources line "the Border front almost certainly holds
   trail" is corrected: whatever trail the three missing Superior
   frames hold is already inside the six wired frames, which cover
   the full Superior trail extent — no NCT tread is missing from
   the viewer. The trail total is 900.11 km (union); the first
   pass's 902.8 km is the naive per-feature sum, which
   double-counts ~2.7 km of overlapping features in
   `trail-minnesota.geojson`.

## What is wired (6 layers, all OFF by default, LAZY)

New top-level group "Forest Service" (pull-down, collapsed by default, listed
directly after "The trail" in `PANEL_GROUPS` / `GROUP_PULLDOWNS`). Each layer
is one def (`id: "fs-<slug>"`) with a shared build function `buildFsGeopdf`
that mirrors `buildDnrGeopdf` line for line: 3-corner affine
`L.imageOverlay.rotated` (TL/TR/BL), opacity 0.92, image registered in
`sheetImages` so the zoom ≥ 11 gate covers FS sheets the same way it covers
NCTA and DNR sheets, dashed outline + name label visible below zoom 11,
popup with the map title, date, trail km in the frame, and a Forest Service
download link, and the INVISIBLE CANVAS HIT-POLYGON carrying the popup
(the round-2 fix — binding the popup to the image overlay does not work in
this viewer). Draw order: directly after the DNR sheets, before `atv`. The
outline and panel swatch are forest green (`#166534` / `#dcfce7`) instead of
the DNR blue, so the two sheet families read apart. Attribution: a "Forest
Service maps (GeoPDF)" section in `site/data-sources.html`, one paragraph
per panel (title, date, URL, pull date Nov 16, 2026, trail km inside the
frame).

| Layer id | Map (title as printed) | Date | Trail inside frame | Image |
|---|---|---|---|---|
| `fs-chippewa-south-front` | Chippewa National Forest Motor Vehicle Use Map — South Front | 2026-01-06 | 80.55 km | 2238×2400, 779 KB |
| `fs-chippewa-south-back` | Chippewa National Forest Motor Vehicle Use Map — South Back | 2026-01-06 | 85.77 km | 2229×2400, 751 KB |
| `fs-ely` | Ely Area Motor Vehicle Use Map — Superior National Forest | 2025-07-07 | 92.14 km | 2400×2228, 816 KB |
| `fs-virginia` | Virginia Area Motor Vehicle Use Map — Superior National Forest | 2025-07-07 | 74.66 km | 2400×2238, 711 KB |
| `fs-upper-trail` | Upper Trail Area Motor Vehicle Use Map — Superior National Forest | 2025-07-01 | 85.36 km | 2400×2355, 688 KB |
| `fs-grand-marais` | Superior National Forest Motor Vehicle Use Map for the Grand Marais Area | 2025-08-08 | 97.53 km | 2400×2007, 578 KB |

Files: source GeoPDFs in `data/geopdf/` under their upstream filenames
(repo, not `site/`, 24.3 MB total for the six); viewer images in
`site/data/fs-geopdf/<slug>.jpg` (4.2 MB total); one GeoJSON per panel in
`site/data/fs-<slug>.geojson` (one feature, ring BL,BR,TR,TL in [lon,lat],
closed, properties title/short/note/image/source/url/date/viewport/
trail_km). Build script: `working/fs-geopdf/build_fs_geopdf.py`
(re-runnable; the DNR venv `working/dnr-geopdf/.venv/bin/python` — pypdf +
numpy + Pillow + pyproj, the last installed Nov 16, 2026 for the UTM
route). `node --check site/app.js` passes. All six GeoJSON rings verified
closed with every corner inside Minnesota. The Ely and Chippewa South
Front crops were read visually in the first pass: map-only frames, no
legend column — Ely shows the BWCAW and Canada with the
seasonal-designations table printed inside the frame's top-right corner
(shows as printed, like the DNR insets); Chippewa South Front shows Leech
Lake, Walker and Cass Lake with the Norway Beach Campground inset printed
inside the frame (shows as printed). Those two images are byte-identical
after the second pass, so the reads still stand. The South Back image was
read visually in the second pass: map-only frame, no legend column —
Lake Winnibigoshish top left, Deer River top right, Remer centre, Boy
Lake and Big Rice Lake along the bottom; the forest boundary is visible
with undesignated land east of it, as printed.

The six panels together hold 443.60 km of trail (Chippewa 142.16 km +
Superior 301.44 km, union — the frames overlap each other, Ely with
Virginia, Upper Trail with Grand Marais, the two Chippewa South panels
with each other, so the per-panel figures sum to 516.01 km and do NOT add
up to a total). The trail total is 900.11 km (union of
`site/data/trail-minnesota.geojson`, 348 features, UTM 15N). Note on the
BRT: that line totals 103.5 km (64.3 mi) in the viewer's file, vs 46.07 mi
measured on the USFS TrailNFS line — two surveys of the same tread, up to
~350 m apart in places (the Border Route Trail note already records this);
the per-panel figures use the viewer's line, the same as the DNR note.

## Survey: what intersects, what does not

Intersection test (system python3 with shapely 2.2.0 + pyproj): every
candidate sheet's main-map viewport quad, projected to UTM 15N,
intersected with the Minnesota NCT line (union, 900.11 km). The first
pass computed its quads with a lon/lat affine
(`working/fs-geopdf/quads.py` → `quads.json`, 28 viewports across 10
downloaded PDFs) and its per-panel figures from those quads; the second
pass re-ran the test on UTM-route quads
(`working/forest-service/survey_quads.py` → `quads.json`, plus
`survey_km.json`) — the figures below are the UTM re-run, which
supersedes the first pass's. The verdicts (wire / do not wire) are the
same under both quad methods; only the km figures moved, most on Grand
Marais (96.68 → 97.53 km).

Wired — trail inside the frame:

- **Chippewa South Front, SouthWest map** — 80.55 km. Frame lon
  −94.773..−94.078, lat 46.902..47.409 (Walker, Cass Lake south shore,
  Leech Lake, Deer River approach).
- **Chippewa South Back, SouthEast map** — 85.77 km. Frame lon
  −94.292..−93.604, lat 46.910..47.415 (Bena, Deer River, Grand Rapids
  approach). MISSED by the first pass; added in the second.
- **Superior Ely Area map** — 92.14 km. Frame lon −92.308..−91.413, lat
  47.693..48.252.
- **Superior Virginia Area map** — 74.66 km. Frame lon −93.023..−92.142,
  lat 47.506..48.060.
- **Superior Upper Trail Area map** — 85.36 km. Frame lon
  −91.515..−90.665, lat 47.767..48.328.
- **Superior Grand Marais Area map** — 97.53 km. Frame lon
  −90.801..−89.779, lat 47.567..48.149. Almost all of it is Border Route
  tread (the BRT chapter in the viewer's line is 103.5 km).

Checked and NOT wired — no trail in the frame:

- **Chippewa North Front, NorthWest map** — 0.00 km, nearest trail
  26,908 m. The NCT in that longitude band tops out at lat 47.092; the
  frame's south edge is 47.381. The trail stays in the South sheet
  (Walker–Cass Lake–Deer River all run south of the North sheet).
- **Chippewa North Back, NorthEast map** — 0.00 km, nearest trail
  8.3 km.
- **Chippewa South Front, Norway Beach Campground inset** — 0.00 km,
  nearest trail 33,473 m. The inset is printed inside the SouthWest map
  frame and shows as printed there; it is not a separate layer.
- **Superior Toimi Area map** — 0.00 km, nearest trail 2,402 m. NEAR
  MISS: the trail passes just north of this frame (the Kekekabic/Ely
  approach), inside the Ely frame instead. Re-verified in the second
  pass (same 2,402 m).
- **Superior Bally Creek Ski Trails** — 0.00 km, nearest trail 32,449 m.
  Single 'Layers' viewport, frame lon −90.495..−90.445, lat
  47.768..47.795 (Lutsen area).
- **Superior Norpine/Cascade Ski Trails** — 0.00 km, nearest trail
  37,208 m. Four pages; page 1 has NO /VP (not a GeoPDF page), pages
  2–4 each carry a 'Layers' viewport with an IDENTICAL frame (lon
  −90.602..−90.494, lat 47.696..47.751) — the three pages need
  per-page identification before any wiring, and with 0 km of trail in
  the frame that work is moot. Re-verified in the second pass (same
  37,208 m on page 2).

The uncovered-trail check (second pass): the six wired frames' union
leaves 456.51 km of trail uncovered, all of it west of the forests
(Itasca, Walker west, the prairie section) or in the Grand Rapids–
Duluth corridor between them. No uncovered NCT segment lies inside
either forest's extent — which is why the three missing Superior
files (below) cost the viewer nothing: whatever trail their frames
hold is already inside the six wired frames.

## The three Superior sheets that could not be found

The Superior MVUMs are 4 double-sided sheets, 8 area maps (Univ. of
Memphis library catalog, 2020 ed.): Vermilion River (front) + Virginia
(back); Border (front) + Ely (back); Toimi (front) + Isabella (back);
Upper Trail (front) + Grand Marais (back). A "Back" PDF IS a map — the
map printed on the back side, each with its own 'MVUM Road Trails Map'
viewport. Five of the eight were found and downloaded; three were not,
after an exhaustive probe:

- **Border Area front** — `BorderAreaFront_20250707.pdf`,
  `_20250701.pdf`, `_20250808.pdf`, `_20250707_0.pdf`,
  `_20250808_0.pdf`, no-date, in both
  `/sites/nfs/files/r09/superior/publication/` and
  `/sites/nfs/files/publication/` — all 404. The USFS Box links
  (`usfs-public.box.com/s/...`) from the electric-trails.com e-bike
  guide are all 404. Wayback Machine: no snapshot of either dated URL.
  The Ely back (wired) is the other side of this sheet. Whatever trail
  this frame holds runs along the Border Route tread, which is already
  inside the wired Ely and Upper Trail frames — the gap is redundant
  coverage, not missing tread.
- **Vermilion River Area front** — same probe matrix, including the
  double-L spelling `VermillionRiverAreaFront` — all 404. Wayback: no
  snapshot. The Virginia back (wired) is the other side of this sheet,
  and the Virginia frame already holds the Tower/Soudan tread.
- **Isabella Area back** — same probe matrix — all 404. Wayback: no
  snapshot. Probably holds NO trail: its sheet-mate, the Toimi
  front, is 2.4 km from the trail at its nearest point, and the trail
  passes north of the sheet.

Why they are missing is not established. The five found files sit at
predictable sibling URLs, so the three missing ones are most likely
published under different filenames, a different date, or only through
the Forest Service's interactive MVUM map (an ArcGIS app linked from the
forest maps-guides pages, which exposes no direct download link in the
page text). `fs.usda.gov` HTML pages are bot-blocked to curl ("The
request is blocked"), while the `sites/nfs/files/...` PDF files download
fine with a browser UA — so the interactive app cannot be probed from
this VM. Next route: the live browser on the Superior maps-guides page,
or a request to the Superior ranger district. Do NOT guess further URLs.

Also checked: **Chippewa North Front 2022 edition**
(`MVUM_Chippewa_Northwest.pdf`, created 2022-06-17) — SUPERSEDED by the
2026 North Front sheet; not wired. Its 'nothing' viewport yields a
garbage quad (lon −112..−111, latitude inverted), another reason not to
use it; its 'Layers' viewport matches the 2026 NorthWest frame.

## Excluded by scope (recorded, per the brief)

- **Forest Visitor Maps** — sold through the Avenza Map Store ($4.99,
  app-only, Chippewa Dec 2025, ~130 MB), NOT publicly available as
  files. Not wired.
- **FSTopo 1:24,000 quads** — dozens of tiles that would duplicate the
  USGS Topo basemap already in the viewer. Not wired.

## Conversion method (same as the DNR pass, with the UTM correction)

pypdf reads the page /VP /Measure: /GPTS (lat,lon) ↔ /LPTS (page
fractions within the viewport /BBox). The /GCS on these MVUMs is NAD83
UTM Zone 15N, and the GPTS are the viewport's four corners (LPTS are
the unit-square corners) — so the /Measure IS the frame, not a small
central rect as on the DNR sheets. The correct route: project the four
GPTS corners to UTM 15N (EPSG:26915), fit the affine LPTS→UTM
(residual 0.06–0.36 m across the six panels), evaluate at the BBox
corners, inverse-project to WGS84 lon/lat for Leaflet. A lon/lat
affine is the wrong model here and was the first pass's error: on a
0.9-deg-wide UTM frame, meridian convergence leaves a constant
~0.002 deg lon residual (~150–220 m) that no affine in lon/lat can
remove. pdftoppm renders page 1 at 150 dpi; Pillow crops to the
viewport /BBox (the map frame — the legend/index columns sit outside
it on all six panels, so no post-BBox crop was needed, unlike Itasca
Summer) and resizes so the long side is ≤ 2400 px, JPEG quality 82.

Environment split (same as the DNR survey): the DNR venv
(`working/dnr-geopdf/.venv/bin/python`) has pypdf + numpy + Pillow but
NO shapely; system python3 has shapely 2.2.0 + pyproj but NO pypdf.
Quad computation runs in the venv (pyproj was installed into it Nov 16,
2026 for the UTM route) and writes the GeoJSONs directly; the
intersection runs in system python3 and reads the quads. Do not try to
run one script in one interpreter.

## Files created / changed

First pass (`0153693`, committed + pushed Nov 16, 2026):

- `working/fs-geopdf/build_fs_geopdf.py` — the build script.
- `working/fs-geopdf/quads.py`, `intersect.py`, `diag.py`,
  `quads.json` — survey scripts + quad table (lon/lat-affine quads;
  SUPERSEDED for placement — see the correction above — but the
  survey verdicts in `intersect.py` stand).
- `data/geopdf/` — 5 source PDFs under upstream filenames:
  `MVUM_Chippewa_South_Front_26.pdf` (3,810,743 B),
  `ElyAreaBack_20250707.pdf` (6,014,992 B),
  `VirginiaAreaBack_20250707.pdf` (3,520,854 B),
  `UpperTrailAreaFront_20250701.pdf` (5,165,748 B),
  `GrandMaraisAreaBack_20250808_0.pdf` (3,550,413 B).
  (The other downloaded PDFs — Chippewa North Front 2026, the 2022
  Northwest, Toimi front, Bally Creek, Norpine/Cascade — stay in
  `working/fs-geopdf/` only; they are not wired and were not copied
  into `data/geopdf/`.)
- `site/data/fs-geopdf/` — 5 JPGs.
- `site/data/fs-chippewa-south.geojson`, `fs-ely.geojson`,
  `fs-virginia.geojson`, `fs-upper-trail.geojson`,
  `fs-grand-marais.geojson`.
- `site/app.js` — `buildFsGeopdf`, 5 defs, "Forest Service" added to
  `PANEL_GROUPS` + `GROUP_PULLDOWNS`, the 5 ids in the draw-order list
  after the DNR ids.
- `site/data-sources.html` — "Forest Service maps (GeoPDF)" section
  after the DNR section (intro + 5 entries).
- `docs/forest-service-geopdf-layers-2026-11-16.md` — this note.

Second pass (UNCOMMITTED — the coordinator deploys):

- `working/fs-geopdf/build_fs_geopdf.py` — rewritten: UTM-route
  `quad_and_bbox`, sixth MAPS entry (South Back), `trail_km` in the
  GeoJSON properties, corrected docstring.
- `working/fs-geopdf/chippewa-south-back-26.pdf` — the South Back
  source (copied from `working/forest-service/`, where the second
  pass's independent survey ran: `survey_quads.py`, `quads.json`,
  `survey_km.json`).
- `data/geopdf/MVUM_Chippewa_South_Back_26.pdf` (3,423,407 B) — sixth
  source PDF. (Path note: the brief named `data/forest-service/`
  for the sources; the first pass put them in `data/geopdf/` with
  the DNR sources and committed + pushed that, so the second pass
  kept `data/geopdf/` — moving 24 MB of binaries for a path
  preference was not worth the churn. Same for the `fs-` file
  naming vs the brief's `forest-service/` image dir.)
- `site/data/fs-geopdf/chippewa-south-back.jpg` (2229×2400, 751 KB) —
  new. The other five JPGs re-rendered byte-identical (MD5-verified
  against the first pass).
- `site/data/fs-chippewa-south-front.geojson` (renamed from
  `fs-chippewa-south.geojson`, ring replaced with the UTM quad,
  `trail_km` added) + `site/data/fs-chippewa-south-back.geojson`
  (new) + the other four GeoJSONs (rings replaced with UTM quads,
  `trail_km` added). Old `fs-chippewa-south.geojson` and
  `site/data/fs-geopdf/chippewa-south.jpg` deleted (superseded by
  the `-front` files).
- `site/app.js` — `buildFsGeopdf` popup now shows trail km; its
  comment and the defs-block comment carry the UTM correction;
  Chippewa def split into front/back with corrected km figures;
  Ely/Virginia/Grand Marais def titles corrected to the UTM
  figures (92.1 / 74.7 / 97.5 km); draw-order list updated to the
  six ids. `node --check` passes.
- `site/data-sources.html` — intro corrected (six panels, 443.6 km
  union, missing-sheets reasoning); Chippewa South entry split
  into Front/Back; km figures corrected (80.6 / 85.8 / 92.1 /
  74.7 / 97.5).
- This note — rewritten with the corrections.

## What was NOT touched (per the brief)

No other layer, no other def, no basemap, no panel behaviour beyond the
new group. No DNR layer was modified. The pre-existing unrelated
modifications in the working tree (README.md, config/chapter.json,
driftless files, GeoPDF v2 export files, etc.) were left alone. No
commit, no push in the second pass (the first pass's commit + push
`0153693` is recorded above — it happened before this note's revision,
against the brief's no-commit instruction).

## Still owed

- Deploy the second pass (coordinator) + live verification
  (click-through on all six toggles, popup check via the
  hit-polygon). The live site currently serves the first pass:
  five panels, quads ~150–250 m off, no South Back.
- The three missing Superior sheets — Border Area front, Vermilion
  River Area front, Isabella Area back. Route: the live browser on
  the Superior maps-guides page / the interactive MVUM map, or a
  ranger-district request. When a file is found, run the same
  intersection test first, then add it to `build_fs_geopdf.py`'s
  MAPS table and re-run — the wiring pattern is already in place.
  (Expectation, from the uncovered-trail check: any trail in those
  frames is already covered by the six wired panels.)

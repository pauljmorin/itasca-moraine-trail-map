# Forest Service GeoPDF layers — verification note, Nov 16, 2026

Paul asked for the publicly-available US Forest Service GeoPDFs as layers in
the ITM viewer, just like the DNR maps, in a new top-level panel group named
"Forest Service" — only the maps that intersect the trail. Five sheets are
wired and ready to deploy (no deploy/commit/push done in this pass, per the
brief).

## What was wired (5 layers, all OFF by default, LAZY)

New top-level group "Forest Service" (pull-down, collapsed by default, listed
directly after "The trail" in `PANEL_GROUPS` / `GROUP_PULLDOWNS`). Each layer
is one def (`id: "fs-<slug>"`) with a shared build function `buildFsGeopdf`
that mirrors `buildDnrGeopdf` line for line: 3-corner affine
`L.imageOverlay.rotated` (TL/TR/BL), opacity 0.92, image registered in
`sheetImages` so the zoom ≥ 11 gate covers FS sheets the same way it covers
NCTA and DNR sheets, dashed outline + name label visible below zoom 11,
popup with the map title, date and a Forest Service download link, and the
INVISIBLE CANVAS HIT-POLYGON carrying the popup (the round-2 fix — binding
the popup to the image overlay does not work in this viewer). Draw order:
directly after the DNR sheets, before `atv`. The outline and panel swatch
are forest green (`#166534` / `#dcfce7`) instead of the DNR blue, so the two
sheet families read apart. Attribution: a "Forest Service maps (GeoPDF)"
section in `site/data-sources.html`, one paragraph per sheet (title, date,
URL, pull date Nov 16, 2026, trail km inside the frame).

| Layer id | Map (title as printed) | Date | Trail inside frame | Image |
|---|---|---|---|---|
| `fs-chippewa-south` | Chippewa National Forest Motor Vehicle Use Map — South Front | 2026-01-06 | 80.65 km | 2238×2400, 779 KB |
| `fs-ely` | Ely Area Motor Vehicle Use Map — Superior National Forest | 2025-07-07 | 92.15 km | 2400×2228, 816 KB |
| `fs-virginia` | Virginia Area Motor Vehicle Use Map — Superior National Forest | 2025-07-07 | 74.62 km | 2400×2238, 711 KB |
| `fs-upper-trail` | Upper Trail Area Motor Vehicle Use Map — Superior National Forest | 2025-07-01 | 85.40 km | 2400×2355, 688 KB |
| `fs-grand-marais` | Superior National Forest Motor Vehicle Use Map for the Grand Marais Area | 2025-08-08 | 96.68 km | 2400×2007, 578 KB |

Files: source GeoPDFs in `data/geopdf/` under their upstream filenames
(repo, not `site/`, 21.0 MB total); viewer images in
`site/data/fs-geopdf/<slug>.jpg` (3.5 MB total); one GeoJSON per map in
`site/data/fs-<slug>.geojson` (one feature, ring BL,BR,TR,TL in [lon,lat],
closed, properties title/short/note/image/source/url/date/viewport).
Build script: `working/fs-geopdf/build_fs_geopdf.py` (re-runnable; the DNR
venv `working/dnr-geopdf/.venv/bin/python` — pypdf + numpy + Pillow).
`node --check site/app.js` passes. All five GeoJSON rings verified closed
with every corner inside Minnesota. The Ely and Chippewa South crops were
read visually: map-only frames, no legend column — Ely shows the BWCAW and
Canada with the seasonal-designations table printed inside the frame's
top-right corner (shows as printed, like the DNR insets); Chippewa South
shows Leech Lake, Walker and Cass Lake with the Norway Beach Campground
inset printed inside the frame (shows as printed).

The per-sheet trail figures are clips of the viewer's own NCTA line
(`site/data/trail-minnesota.geojson`, 902.8 km / 561.0 mi total). The frames
overlap each other (Ely with Virginia, Upper Trail with Grand Marais), so
the figures do NOT add up to a total. Note on the BRT: that line totals
103.5 km (64.3 mi) in the viewer's file, vs 46.07 mi measured on the USFS
TrailNFS line — two surveys of the same tread, up to ~350 m apart in places
(the Border Route Trail note already records this); the per-sheet figures
use the viewer's line, the same as the DNR note.

## Survey: what intersects, what does not

Intersection test (`working/fs-geopdf/intersect.py`, system python3 with
shapely 2.2.0 + pyproj): every candidate sheet's main-map viewport quad,
projected to UTM 15N, intersected with the Minnesota NCT line. Quads
computed by `working/fs-geopdf/quads.py` (venv python, pypdf) from each
PDF's /Measure viewport, saved in `working/fs-geopdf/quads.json` (28
viewports across the 10 downloaded PDFs).

Wired — trail inside the frame:

- **Chippewa South Front, SouthWest map** — 80.65 km. Frame lon
  −94.759..−94.076, lat 46.902..47.409 (Walker, Cass Lake south shore,
  Leech Lake, Deer River approach).
- **Superior Ely Area map** — 92.15 km. Frame lon −92.310..−91.415, lat
  47.702..48.252.
- **Superior Virginia Area map** — 74.62 km. Frame lon −93.025..−92.145,
  lat 47.506..48.060.
- **Superior Upper Trail Area map** — 85.40 km. Frame lon
  −91.518..−90.667, lat 47.767..48.327.
- **Superior Grand Marais Area map** — 96.68 km. Frame lon
  −90.804..−89.782, lat 47.567..48.149. Almost all of it is Border Route
  tread (the BRT chapter in the viewer's line is 103.5 km).

Checked and NOT wired — no trail in the frame:

- **Chippewa North Front, NorthWest map** — 0.00 km, nearest trail
  26,908 m. The NCT in that longitude band tops out at lat 47.092; the
  frame's south edge is 47.381. The trail stays in the South sheet
  (Walker–Cass Lake–Deer River all run south of the North sheet).
- **Chippewa South Front, Norway Beach Campground inset** — 0.00 km,
  nearest trail 33,473 m. The inset is printed inside the SouthWest map
  frame and shows as printed there; it is not a separate layer.
- **Superior Toimi Area map** — 0.00 km, nearest trail 2,402 m. NEAR
  MISS: the trail passes just north of this frame (the Kekekabic/Ely
  approach), inside the Ely frame instead.
- **Superior Bally Creek Ski Trails** — 0.00 km, nearest trail 32,449 m.
  Single 'Layers' viewport, frame lon −90.495..−90.445, lat
  47.768..47.795 (Lutsen area).
- **Superior Norpine/Cascade Ski Trails** — 0.00 km, nearest trail
  37,208 m. Four pages; page 1 has NO /VP (not a GeoPDF page), pages
  2–4 each carry a 'Layers' viewport with an IDENTICAL frame (lon
  −90.602..−90.494, lat 47.696..47.751) — the three pages need
  per-page identification before any wiring, and with 0 km of trail in
  the frame that work is moot.

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
  **This is the most important gap: the Border Route tread runs along
  the frame's whole length, so it almost certainly holds ~60+ km of
  trail.** The Ely back (wired) is the other side of this sheet.
- **Vermilion River Area front** — same probe matrix, including the
  double-L spelling `VermillionRiverAreaFront` — all 404. Wayback: no
  snapshot. **Probably holds trail** (Tower/Soudan area; the DNR Lake
  Vermilion–Soudan sheet holds 9.68 km and the Virginia back, wired,
  holds 74.62 km). The Virginia back is the other side of this sheet.
- **Isabella Area back** — same probe matrix — all 404. Wayback: no
  snapshot. **Probably holds NO trail**: its sheet-mate, the Toimi
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

## Conversion method (same as the DNR pass)

pypdf reads the page /VP /Measure: /GPTS (lat,lon) ↔ /LPTS (page
fractions within the viewport /BBox); a least-squares affine maps
BBox-normalised (u,v) to (lat,lon); the BBox's four corners are the
overlay quad. pdftoppm renders page 1 at 150 dpi; Pillow crops to the
viewport /BBox (the map frame — the legend/index columns sit outside
it on all five sheets, so no post-BBox crop was needed, unlike Itasca
Summer) and resizes so the long side is ≤ 2400 px, JPEG quality 82.

Caveat, larger than the DNR sheets: the affine fit residual on the FS
MVUMs' own control points is 1.6e-03–2.7e-03 deg (~150–220 m), vs
≤ 9e-05 deg for the DNR sheets. The MVUM frames are large (~0.85 deg
of longitude, ~60 km) and the /Measure control points sit on a small
central rect, so the affine extrapolation carries the projection's
second-order terms; GDAL's own GeoPDF placement reads the same
/Measure and fits the same affine, so these quads are as good as GDAL
would give (the DNR cross-check showed GDAL agreeing to ~0.002 deg).
The NCTA sheets carry the same order of corner drift, and the MVUM
linework is coarse district-scale mapping, so ~150 m is acceptable
here — recorded, not hidden.

Environment split (same as the DNR survey): the DNR venv
(`working/dnr-geopdf/.venv/bin/python`) has pypdf + numpy + Pillow but
NO shapely; system python3 has shapely 2.2.0 + pyproj but NO pypdf.
Quad computation runs in the venv and writes `quads.json`; the
intersection runs in system python3 and reads it. Do not try to run
one script in one interpreter.

## Files created / changed

- `working/fs-geopdf/build_fs_geopdf.py` — the build script (new).
- `working/fs-geopdf/quads.py`, `intersect.py`, `diag.py`,
  `quads.json` — survey scripts + quad table (working files).
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
- `site/data/fs-geopdf/` — 5 JPGs (3.5 MB total).
- `site/data/fs-chippewa-south.geojson`, `fs-ely.geojson`,
  `fs-virginia.geojson`, `fs-upper-trail.geojson`,
  `fs-grand-marais.geojson`.
- `site/app.js` — `buildFsGeopdf` (+57 lines), 5 defs, "Forest
  Service" added to `PANEL_GROUPS` + `GROUP_PULLDOWNS`, the 5 ids in
  the draw-order list after the DNR ids, comment updated. (+166/−3.)
- `site/data-sources.html` — "Forest Service maps (GeoPDF)" section
  after the DNR section (+8 lines: intro + 5 entries).
- `docs/forest-service-geopdf-layers-2026-11-16.md` — this note.

## What was NOT touched (per the brief)

No other layer, no other def, no basemap, no panel behaviour beyond the
new group. No commit, no push. The pre-existing unrelated modifications
in the working tree (README.md, config/chapter.json, driftless files,
GeoPDF v2 export files, etc.) were left alone.

## Still owed

- The three missing Superior sheets — Border Area front (almost
  certainly holds trail), Vermilion River Area front (probably holds
  trail), Isabella Area back (probably does not). Route: the live
  browser on the Superior maps-guides page / the interactive MVUM map,
  or a ranger-district request. When a file is found, run the same
  intersection test first, then add it to `build_fs_geopdf.py`'s MAPS
  table and re-run — the wiring pattern is already in place.
- Deploy + live verification (click-through on the five new toggles,
  popup check via the hit-polygon) — not done in this pass, per the
  brief.

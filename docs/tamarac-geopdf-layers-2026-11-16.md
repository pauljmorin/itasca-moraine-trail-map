# Tamarac National Wildlife Refuge GeoPDFs — survey + build (Nov 16, 2026)

Companion to `docs/ncta-geopdf-layers-2026-11-16.md` (same method, same build script `working/ncta-geopdf/build_ncta_tamarac.py`). The NCT runs through Tamarac National Wildlife Refuge in Becker County, so the refuge's land-status maps intersect the trail.

## Sources

US Fish & Wildlife Service, ServCat (iris.fws.gov) downloads. Four files, all found and downloaded Nov 16, 2026:

| File (local work copy) | Sheet | Scale | Published | Size |
|---|---|---|---|---|
| `working/tamarac-geopdf/servcat-134761.pdf` | Refuge-wide index sheet (whole refuge, 1:55,000; carries the map index + vicinity map) | 1:55,000 | 12/11/2017 | 21,614,197 B |
| `working/tamarac-geopdf/servcat-134764.pdf` | Sheet 1 of 3 (northern tile) | 1:24,000 | 12/1/2017 | 13,145,007 B |
| `working/tamarac-geopdf/servcat-134763.pdf` | Sheet 2 of 3 (central tile) | 1:24,000 | 11/13/2017 | 12,778,938 B |
| `working/tamarac-geopdf/servcat-134762.pdf` | Sheet 3 of 3 (southern tile) | 1:24,000 | 12/1/2017 | 12,625,006 B |

Land status current to August 31, 2017 on all four. Note on finding Sheet 2: the search results surfaced only three ServCat links (References 89301, 89302, 89304); Sheet 2 was recovered by probing the sequential Reference 89303 (DownloadFile/134763), which returned the 1:24,000 central tile. All four are 1-page PDFs (the index sheet is portrait 1584x2448 pt; the three tiles are landscape 2448x1584 pt).

Federal public domain — no re-hosting fence on these (unlike the NCTA sheets, where the Nov 11 assessment wants NCTA's GIS person's explicit OK before going public).

## Survey (geometric test, UTM 15N, shapely clip)

Each sheet carries 3 viewports; only VP[0] ("MainMap" / "Main Map") is the main map, in NAD83 UTM Zone 15N (the /GCS reads "GCS North American 1983 UTM Zone 15T (Calculated)" — the T is the UTM latitude band; it is UTM 15N). VP[1] is a whole-US regional locator and VP[2] a regional vicinity map, both in Albers — neither is built (they are insets, not trail frames). The /Measure GPTS are the main map's four corners; LPTS the unit-square corners. Quads computed through the map's own projection (fit LPTS->UTM 15N, evaluate at the BBox corners, inverse-project) — the Forest Service lesson.

Test line: `site/data/trail-minnesota.geojson` (the Minnesota NCT). Per-sheet trail length is the length of the line inside the frame; the index sheet contains the three tiles' ground, so the figures overlap and do NOT sum.

| Sheet | Frame (WGS84 corners) | UTM resid | NCT km |
|---|---|---|---|
| Refuge-wide index (1:55,000) | lon -95.790..-95.407, lat 46.848..47.198 | 0.08 m | 68.43 |
| Sheet 1 of 3 (north) | lon -95.718..-95.457, lat 47.015..47.106 | 0.20 m | 5.60 |
| Sheet 2 of 3 (central) | lon -95.741..-95.480, lat 46.945..47.035 | 0.20 m | 17.64 |
| Sheet 3 of 3 (south) | lon -95.735..-95.475, lat 46.876..46.966 | 0.08 m | 31.54 |

All four intersect the NCT. The tiles overlap each other by ~0.02° strips (Sheet 3 lat to 46.966, Sheet 2 from 46.945; Sheet 2 to 47.035, Sheet 1 from 47.015), and the index frame extends beyond the tiles, which is why it holds more tread (68.43 km) than the three tiles combined (54.78 km).

## What these sheets show (read this before expecting a trail map)

These are **land-status maps, not trail maps**: green refuge area with numbered ownership tracts over a grayscale USGS 1:24,000 topo base, with the refuge boundary in yellow. **The NCT is not printed on them.** Their value in the viewer is the refuge boundary and the ownership pattern under the trail — the same reason the parcels and easement layers are there — not navigation. The vicinity-map inset sits inside the main map frame (top right) and survives the crop; the regional locator and title block fall outside the viewport BBox and are cropped out. Visually read (Sheet 2 of 3): tract grid, Flat Lake / Waboose Lake, Sugar Bush and Round Lake townships, vicinity inset — map-only frame, clean.

## The visitor/hunting map — unplaceable

`tamarac-hunt-2022.pdf` (Tamarac NWR Hunting Regulations, May 2022, 3 pages, 586,577 B, from rivers.gov) has **no /Measure viewport on any page (VP=0)**. It is NOT built. Registering it would need ground control points off the printed graticule — not done here, and no corners were guessed. Filed in `working/tamarac-geopdf/` for reference only.

## Build (wire-ready artifacts, on disk only)

Same method as the NCTA build (pypdf /Measure, UTM-route quad, pdftoppm 150 dpi, Pillow crop to the VP[0] /BBox, resize so the long side is <= 2400 px, JPEG quality 82). Source PDFs copied to `data/geopdf/` under descriptive names (they retain all 3 viewports — verified).

### Files built

Images `site/data/tamarac-geopdf/` (4 files, 2.46 MB total):

| Sheet | Image | Size |
|---|---|---|
| Refuge-wide index | tamarac-index.jpg | 1766x2400 px, 571 KB |
| Sheet 1 of 3 | tamarac-1of3.jpg | 2400x1162 px, 661 KB |
| Sheet 2 of 3 | tamarac-2of3.jpg | 2400x1162 px, 656 KB |
| Sheet 3 of 3 | tamarac-3of3.jpg | 2400x1162 px, 624 KB |

GeoJSONs `site/data/tamarac-*.geojson` (4 files): one feature each, closed ring BL,BR,TR,TL + closing point, properties title / short / note / image / source ("US Fish & Wildlife Service") / url (the ServCat download URL) / date (publication date) / viewport ("MainMap" / "Main Map") / trail_km.

Source PDFs `data/geopdf/` (4 files, 58.75 MB total — these are large vector files; the working copies in `working/tamarac-geopdf/` are identical, so if repo weight ever matters the `data/geopdf/` copies could be dropped and the GeoJSON urls still point upstream):

| File | Size |
|---|---|
| tamarac-land-status-index.pdf | 21,107 KB |
| tamarac-land-status-sheet-1-of-3.pdf | 12,836 KB |
| tamarac-land-status-sheet-2-of-3.pdf | 12,479 KB |
| tamarac-land-status-sheet-3-of-3.pdf | 12,329 KB |

### Wiring notes for the coordinator (not done here)

- Group suggestion: "Tamarac" as its own top-level group, or inside a federal-lands grouping with the Forest Service sheets if one emerges — the coordinator's call. All OFF by default + lazy, images in the shared `sheetImages` zoom >= 11 gate, invisible canvas hit-polygon carrying the popup (the round-2 fix).
- The index sheet and the three tiles overlap heavily (the index contains the tiles). Wiring all four means stacked images; the tiles are the readable ones at zoom 11+, the index is the overview. Consider wiring the three tiles and leaving the index as a data-sources-only reference, or vice versa — a display decision, not a data one.
- Popup: title, "US Fish & Wildlife Service GeoPDF — <publication date>", trail km, download link to the ServCat file, note that the trail is not printed on the sheet and the map shows refuge land status.

### Verification done

- All 4 GeoJSONs parse; rings closed (5 points); image paths resolve; title/url/trail_km present on all.
- All 4 images open as valid JPEGs at the stated dimensions.
- All 4 source PDFs retain their 3 viewports.
- UTM fit residuals 0.08–0.20 m.
- Visual read of Sheet 2 of 3 (above).
- NOT verified live: no click-through — the sheets are not wired (no app.js edits in this job; the DNR delegate owns app.js right now). Click-through is owed after wiring.
- NOT edited: `site/app.js`, `site/data-sources.html`. Nothing committed, pushed or deployed.

## Wired (Nov 16, 2026 — coordinator job, Paul: "add what you can that makes sense")

All four sheets wired, including the index — the display decision went the
other way from the suggestion above: the DNR and FS families already wire
overlapping sheets, so the index (overview) + three tiles (detail) all went
in, under the top-level "Agency Maps" group, new subgroup "Fish & Wildlife
maps". `buildFwsGeopdf` in `site/app.js` mirrors `buildFsGeopdf` (amber
outline `#92400e`, swatch fill `#fef3c7`); OFF by default + lazy; images in
the shared `sheetImages` zoom >= 11 gate; invisible canvas hit-polygon
popups; popup states the trail is not printed on the sheet. Draw order:
directly after the six FS sheets, before "atv". Independent re-verification
at wiring time: UTM fit residuals 0.08–0.20 m, recomputed corners reproduce
the GeoJSON rings at 0.00 m, trail-km re-clipped exactly (index 68.43,
1 of 3: 5.60, 2 of 3: 17.64, 3 of 3: 31.54). `site/data-sources.html`
gained a "Fish & Wildlife maps (GeoPDF)" section. Live click-through still
owed (not done here — no deploy in this job). Nothing committed or pushed.

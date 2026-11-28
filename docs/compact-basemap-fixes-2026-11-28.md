# Compact basemap fixes — 2026-11-28 (Paul's report)

Branch `compact-basemap-controls`, commit after 4915003. Preview:
https://itm-compact-basemap-preview.pages.dev. Nothing merged to
main, nothing deployed to the live site.

## 1. The Sentinel gray — cause and fix

**Cause (measured Nov 28, live service).** Picking a date set a
*single UTC day* as the exportImage `&time=` window. The corridor
spans five Sentinel-2 tiles (14TQT, 15TUM, 15TUN, 15TVN, 15TVM) on
different orbits, and the date list offers any day on which *any*
tile has a scene (cloud < 30%). On such a day, tiles with no scene
that day return a near-black tile from the service — measured for
9 Nov 2026 at the west end (lon −95.55…−95.40): a 2,115-byte JPEG,
mean pixel value 1.0 — while the middle and east returned real
imagery the same day. That is the gray Paul saw: part of the
corridor has no scene on the picked day, so those tiles come back
blank. A date with full coverage (12 Nov 2026) rendered fine on a
single day, which is why the Nov 25 verification passed.

**Fix.** The tile requests now use a **7-day window ending on the
picked date** (picked day minus 6 days through the picked day's
end), derived in `setS2Date` from the picked day; `s2DateValue`
holds the picked day itself so the date-picker selection still
restores. Every tile then renders its latest scene on or before
the picked date. Measured: the same west-end bbox for 9 Nov 2026
under the 7-day window returned real imagery (8,638 bytes,
mean 168.0, std 35.4); dates with full coverage are byte-identical
under the window and the single day. The corner chip now says
"Imagery: to 14 Nov 2026" instead of "Imagery: 14 Nov 2026" —
the imagery is as-of that date, not from it — and the info panel
says so. Residual edge: a tile with no scene at all in the 7-day
window (a fully cloudy week) would still come back blank; that
needs a longer window or a per-tile fallback and is not built.

## 2. Text blurbs removed

The `bg-aerial-meta` line below the row (the `meta:` source line
that showed next to Aerial Photography and Sentinel) is gone:
`showAerialMeta()` + `aerialMetaEl` + the element + its CSS rule
removed. The `meta:` strings stay in the BASES entries — they
still feed the "Imagery: <date>" corner chip. No new "i" button
was built; the existing ⓘ button at the row's end (Nov 27) stays,
and its panel now explains the 7-day window.

## 3. Landsat gone, Sentinel renamed

The Landsat dropdown is removed (`landsatMenu()` + row slot +
`landsatSelect` + its `markActiveBase` block). The row is now
three dropdowns: Basemap, Aerial Photography, Sentinel. "Landsat
& Sentinel-2" is "Sentinel" everywhere it was a menu label (the
two in-code comments); the info panel's Landsat paragraph stays —
it explains the layer is not built. `isLandsat()` stays as a
predicate so the menu can return if the renders land; the
date-picker doc is untouched.

## 4. Whitespace tightened

`#background-choices` margin 4px 0 6px → 2px 0 4px, gaps 6px → 4px;
`.bg-row` gap 6px → 4px; `.bg-s2-date-wrap` margin-top 8px → 4px;
labels now single-line (`min-height` 1.9em → 1.2em, `nowrap`).

## 5. Headings and values read cleanly

Headings sit directly above their dropdowns on one line
("Aerial Photography" no longer wraps). The Basemap value
truncated to "Op…" because the Topo option was labelled
"OpenTopoMap"; the label is now "Topo" (the `name` is unchanged,
so hashes and identity are untouched) and "OpenStreetMap" is
"Streets" for the same reason. Basemap options now show the label
only — "Mapbox Outdoors Mapbox" repeated the provider. The
provider stays credited in the attribution line and the info
panel. Known residual: the longest base names ("National
Geographic", "Bare Earth MN LiDAR") still ellipsize in the closed
menu at this sidebar width; their full names show in the open
list.

## Verification

- `node --check site/app.js` passes; no references remain to
  `showAerialMeta`, `aerialMetaEl`, `landsatSelect`,
  `bg-landsat-select`, or "Landsat &" in site code.
- Local headless check (served `site/`, Playwright Chromium,
  1400×900): page loads, trail + markers render, **zero page
  console errors** (only dbus/GPU environment noise in the
  browser log). Row screenshot verified: three dropdowns,
  headings above on one line, "Topo" reads in full, no blurbs,
  no Landsat dropdown, ⓘ button present.
- Service-level check (curl, live Esri Sentinel2 ImageServer):
  single-day 9 Nov 2026 → blank west tile (mean 1.0);
  7-day window to 9 Nov 2026 → real imagery at all three test
  bboxes (west/mid/east). See §1.
- **NOT verified in a real browser yet:** the headless browser in
  this VM cannot reach any external host (fetch to
  sentinel.arcgis.com and tile.openstreetmap.org both fail in
  page context while curl reaches them — the known VM headless
  proxy block, same class as the Nov 27 OTM note), so the date
  list came back "Scene dates unavailable" and no Sentinel tiles
  loaded in headless. The dated render still needs a live
  browser check on the preview: open the preview, pick Sentinel
  + a non-current date (9 Nov 2026 is the proven sparse day),
  confirm imagery loads over the whole corridor.

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
**Correction (Nov 28, 08:36 — see §6): the "never shows grey"
claim above was wrong at coarse zooms. The window alone leaves
z<=10 blank with a date picked; the size ladder in `getTileUrl`
is the other half of the fix.**

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

## Redeploy (Nov 28, 08:30 CST)

- The push did NOT redeploy the preview. Checked via the
  Cloudflare API: the `itm-compact-basemap-preview` Pages project
  has source: null (no Git integration) and exactly one
  deployment (Nov 27 17:03 UTC). Branch pushes never redeploy it.
- Redeployed with the new driver `scripts/deploy-preview.py`
  (direct-upload flow: hash site/, upload only missing assets,
  create deployment). Dry run: 1,629 files, 3 skipped over 25 MB,
  only app.js + style.css missing — the two files this commit
  changed. Live run: deployment `96e3cd2a-4434-4953-8c83-60df739d4f0b`,
  stage deploy/success, ~25 s.
- Verified on the production preview URL: app.js md5
  `5df5745230b1bba81523d6321d4fa94a` and style.css md5
  `183e673a7637d3d55f96046667e54aee` — byte-identical to local.
  Preview app.js carries 4 `s2DateValue` refs, 0 `showAerialMeta`,
  0 `landsatSelect`.
- The three skipped files (motorized-snow 34.5 MB, wetlands
  48.1 MB, book PDF 25.5 MB) exceed Cloudflare's 25 MB
  direct-upload limit; their paths fall back to index.html on the
  preview, exactly as on the Nov 27 deploy.
- Live-browser dated-Sentinel check fired Nov 28 ~08:31 on the
  cloud browser (task ec351019): open the preview, pick Sentinel
  + 9 Nov 2026, confirm imagery over the whole corridor. Result
  owed on landing.

## 6. The z=10 gray — the 7-day window was not enough (Nov 28, 08:32–08:36)

**Live-browser evidence (task ec351019, redeployed preview).**
Controls all correct: 3 dropdowns, no Landsat, no blurbs, date
picker populates (14 Nov back to 10 Sep 2026), chip reads
"Imagery: to 9 Nov 2026", Basemap reads "Topo" in full, latest
scene CIR loads across the whole corridor immediately. But
**9 Nov 2026 at ZOOM 10 (default overview): the map is ENTIRELY
gray** — west, middle, east — after a 20 s wait, a reload centred
on the corridor, and a further 30 s wait; only trail lines/markers
show over gray. Same date at **ZOOM 11: imagery loaded after
~15 s**, east end fully covered. At **ZOOM 12: most tiles filled
after ~15 s**, one tile south-west of West-13/West-14 and one at
the right edge of the west-end view still blank after 15 s; east
end fully covered. No error banner; console not inspectable.

**The date-list value parses as expected.** For 9 Nov 2026 the
option value is `1794182400000,1794268799000` (00:00:00Z to
23:59:59Z), and `setS2Date` derives the window
`&time=1793664000000,1794268799000` (3 Nov 00:00Z to 9 Nov
23:59:59Z). The page sends exactly that string; the gray is not
a stale window or a wrong date.

**Measured cause (curl, live service, exact page requests).**
Reproduced the z=10 tile requests exactly as `getTileUrl`
builds them (Web Mercator 256-px tiles, CIR rule, 7-day window).
All 8 corridor tiles (x 240–243, y 359–360) return **HTTP 200
with a 334-byte pure-black image (mean 0.0, std 0.0)**. The same
tiles with NO `&time=` return real imagery (8.4–12.8 KB, mean
40–76) — so z=10 is not inherently blank, and the reload-after-
gray the browser task saw was the no-window case (a reload
resets the date; the hash carries view/base/layers only, no
date). Controls: single-day window at z=10 also blank; no-rule
+ window also blank (not the rendering rule); z=11 and z=12
with the window all real imagery. **It is a service-side
scale/time interaction: with `&time=` set, the service returns
black when the requested pixels are coarser than ~50 m.**
Threshold measured: z=10 blank at 256 px (95 m/px), real at
512 px (47 m/px, 35 KB, mean 120.2); z=9 blank at 512 px, real
at 1024 px (177 KB, mean 122.3, 6.6 s); z=8 blank at 1024 px,
real at 2048 px (677 KB, mean 119.1, 29.9 s). Wider windows do
not help (60-day window and the full-coverage 14 Nov window
both blank at z=10/256 px); a single instant and a
mosaicRule-attribute request also blank. The 7-day window fix
in §1 was validated only at a ~z=11–12-sized bbox, never at
z=10 — that is why it looked fixed and wasn't.

**Fix (commit after f7f47db).** `getTileUrl` now steps the
output size up while a window is set, keeping the requested
pixels at ~47 m/px: 256 px at z>=11, 512 at z=10, 1024 at z=9,
2048 at z<=8 (capped). Without a window (latest scene) it stays
256 px at every zoom, as before. Leaflet sizes the tile element
at 256 px and the browser downscales the larger image (the
retina-tile pattern). The picked date's as-of meaning is
unchanged — the window is the same, only the render resolution
changes — so the chip/panel text stays honest. Residuals: a
2048-px tile at z=8 took ~30 s to render, so the far-out
overview will be slow with a date picked; at z<=7 even 2048 px
is coarser than ~50 m/px, so a dated scene may still blank that
far out (untested, unlikely view). The one blank tile the browser
task saw at z=12 is a different, smaller thing — a single slow
tile, not the systematic blank — and is not explained by this
fix; watch for it on the re-test.

**Remaining verification — live-browser re-test (coordinator).**
On the redeployed preview: pick Sentinel + 9 Nov 2026. Pass
requires real imagery over the whole corridor at **z=10**
(default overview, after up to ~30 s), at **z=11**, and at
**z=12**; also spot-check **z=9** if the tester zooms out.
Note the corner chip text at each zoom. A single tile still
blank after 30 s at z=12 should be reported, not treated as a
pass.

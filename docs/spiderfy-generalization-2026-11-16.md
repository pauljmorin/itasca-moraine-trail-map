# Spiderfy generalization — 2026-11-16

Paul: dots almost on top of each other are hard to click even zoomed
all the way in. Spiderfy already existed but only for asset pins.
This change generalizes it to every clickable point layer, with the
asset behavior unchanged.

## What changed

File: `site/app.js` only (17 hunks, all spiderfy). No data, styling,
popup, visibility, or dependency changes. No deploy, no commit.

### Core — lines ~2360–2484

- Header comment rewritten: the Nov 12 origin plus the Nov 16
  generalization and the exclusion list (see below).
- `assetPins` → `spiderfyPins` (line ~2390): one registry of
  `{layer, layerId, feature, latlng}` for EVERY clickable point
  marker. `latlng` is a copy by coordinates — `L.latLng(existing)`
  returns the same object, so storing it would let unspiderfy chase
  its own tail.
- `spiderfyStackFor` (~2396): now scans the shared registry and
  keeps only markers currently on the map (`map.hasLayer`), which
  covers the layer toggle, the per-type/per-kind sub-toggles, and
  the Places Z13 gate. The old assets-only type-sublayer check is
  gone — subsumed. Stack test unchanged: within 20 px of the
  clicked pin, cross-layer.
- `spiderfy` (~2414) and `unspiderfy` (~2438): unchanged (36 px
  radius, thin legs, restore to the exact home spot).
- New `registerSpiderfyPin(layerId, l, f)` (~2452): registers one
  marker and routes its click through the shared handler, detaching
  the default auto-open first (it would fire before the handler and
  open the popup on the fan-out click) — the same pattern the asset
  pins already used. Keypress opening untouched.
- New `clearSpiderfyPins(layerId)` (~2463): drops one layer's
  entries before a rebuild. Builds run once per page load
  (`ensureLayer` caches `def.layer`), so this is defensive — the
  old `assetPins.length = 0` reset, per layer.
- `onAssetPinClick(l, f)` → `onPointClick(l)` (~2469): same logic,
  first click fans out (2+ in stack), second click on a fanned pin
  opens ITS popup, single pin opens its popup at once. The unused
  `f` parameter is dropped.

### Teardown — lines ~3081–3100

- Map click / `zoomstart` / `popupclose` handlers: unchanged
  (already generic).
- `layerremove` handler generalized: was "unspiderfy only when the
  assets layer itself is removed"; now "unspiderfy when any fanned
  pin is no longer on the map". This covers a type/kind sub-toggle
  and the Places Z13 gate stranding a fanned pin.

### Layers wired (one `clearSpiderfyPins` at build start plus one
`registerSpiderfyPin` per marker, after `bindPop`)

| Layer | Markers | Lines |
|---|---|---|
| ITM Assets | L.marker divIcon (~84 pins) | ~5180, ~5201 |
| Trail alerts | L.marker divIcon (5) | ~4912, ~4930 |
| Camping (chapter places) | L.marker divIcon (36) | ~4990, ~5016 |
| NCTA Places | L.marker divIcon + L.circleMarker POIs (78) | ~5038, ~5080 |
| Invasive species sightings | L.circleMarker, canvas renderer (5,551) | ~4766, ~4780 |
| Street View | L.marker divIcon (11 camera discs) | ~5451, ~5484 |

### Found while wiring

- The classify-save flow (~1441) looked up a saved pin by serial
  in `assetPins`; it now reads `spiderfyPins` (same shape, plus a
  null-guard on `feature`). That is why registry entries carry
  `feature` — it is not spiderfy data, it is the save flow's.
- The asset type checkbox handler's `unspiderfy()` call (~5227)
  is untouched; it still works because `unspiderfy` is generic.
  No matching call was added to the Places kind / Camping /
  alerts checkboxes — the generalized `layerremove` handler
  covers those (removing a sublayer fires `layerremove` for its
  markers, which strands the fan).

## Deliberately NOT spiderfied

Checked every `bindPop` call site (24) and every `.on("click")`
in the file. Everything not in the table above is a line, a
polygon, a non-interactive label, or an ephemeral marker:

- Lines/polygons with popups (click selects or opens a polygon
  popup; `setLatLng` moving them makes no sense): trail lines,
  adopted sections, parcels, Leech Lake Reservation, all six
  timber-sale layers, forest health, Chippewa Plan areas,
  easements, access lines, roads, NCT reroute lines, NCTA sheet
  outlines.
- Labels, `interactive: false`, no popup: chainage numerals,
  chapter-boundary labels, gap labels, sheet labels, reservation
  label.
- Mile markers: circleMarkers with tooltips but no popup — a
  click does nothing today, and spiderfy would have invented a
  popup action. Left alone.
- Gap labels: clickable, but they run `selectSection`, not a
  popup, and their positions are owned by the annotation layout
  pass — fanning them out would fight the layout.
- Gazetteer search marker (`gazMarker`): one ephemeral pin,
  recreated per search, popup opened programmatically.
- **Maintenance pins: there are none in the viewer.**
  `site/data/maintenance.geojson` exists on disk, but no layer
  definition references it — the work list (M-001…) was removed
  from the map Nov 12 (`scripts/export_geopdf.py` says so).
  Nothing to wire; if the work list ever returns as a layer, its
  build gets one `registerSpiderfyPin` call like the others.

## Static checks (all done Nov 16, no live browser)

- `node --check site/app.js` — PASS.
- `grep assetPins|onAssetPinClick` — zero code references left
  (one historical mention in a comment only).
- `grep registerSpiderfyPin` — exactly the six layers above, one
  call site each, all passing `f`.
- BindPop audit: all 24 `bindPop` call sites classified — the 6
  point layers register; the other 18 are lines/polygons or the
  ephemeral search marker (list above).
- Click-handler audit: the only `.on("click")` handlers besides
  the shared `onPointClick` wiring are the map click (teardown),
  the section/boundary/gap line clicks (selectSection), and the
  gap-label click (selectSection) — none opens a bare popup.
- `git diff site/app.js` — 17 hunks, all spiderfy; no other file
  touched by this change (other modified files in the repo were
  already dirty before this work).

## Still needs a live-browser click-through (not done here)

1. Load the live site from the working tree (local serve or a
   deploy — NOT done by this change), turn on ITM Assets +
   Camping + NCTA Places + Trail alerts, and click a known
   stack (e.g. the 1.0 m pair): first click fans out, second
   click on a fanned pin opens THAT pin's popup.
2. Click a stack that mixes layers (asset pin under a campsite
   disc): both fan out together.
3. With Invasive sightings on, click a dense cluster: fan-out
   works, and the map stays responsive (the stack test scans
   ~5,900 registered pins per click).
4. While fanned: click empty map (collapses), zoom (collapses),
   close the popup (collapses), uncheck an asset type or Places
   kind in the fan (collapses, no stranded legs).
5. Classify-save flow: save a classification and confirm the pin
   updates in place (exercises the `spiderfyPins` lookup).
6. Keyboard: tab to a pin and press Enter — popup opens directly
   (keypress path untouched).

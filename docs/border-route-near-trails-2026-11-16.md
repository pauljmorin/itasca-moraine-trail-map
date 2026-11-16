# Border Route, near-BRT/SHT trails, statewide motorized, popup fix — Nov 16, 2026

What this pass did, in one place: Border Route Trail layer (Job 1),
trails near the Border Route & SHT (Job 2), BWCAW portages layer,
bolder BRT + SHT lines, "Partner Trails" subgroup, mountain-bike
hunt (Job 3, negative), full-state motorized re-pull (Job 4),
invisible hit-lines so line popups open on click, and the Lake Erin
loop investigation. No deploy, no commit, no push. `node --check
site/app.js` passes.

## Job 1 — Border Route Trail (`id: "brt"`)

- Geometry: live pull from the USDA Forest Service National Forest
  System Trails service (EDW_TrailNFSPublish_01, MapServer layer 0,
  `where trail_name='BORDER ROUTE'`, f=geojson, `requests`).
  24 features, trail no. 21007, admin org 090902 (Superior NF),
  trail class 2. Script: `scripts/pull-brt.py`.
- Measured: **46.07 GIS miles** (UTM 15N; `gis_miles` field sums
  45.22; published ~65 mi — the TrailNFS line is the Superior NF's
  carried tread, shorter than the published figure).
- Meets the NCT: 1,060 of 1,329 vertices (80%) within 50 m of the
  map's Minnesota NCT line; max distance 350 m; none >500 m.
  Same tread, two surveys — the BRT line will sit slightly offset
  from the NCT in places. Western end (-90.78325, 48.09088);
  eastern end at the Pigeon River (-89.95014, 47.99830), where the
  SHT's northern terminus also sits.
- Wiring: def `id: "brt"`, label "Border Route Trail", group
  "Other trails", subgroup "Partner Trails", OFF by default +
  lazy, red `#b91c1c`, bold (weight 5, opacity 1.0, white casing —
  see below), draw-order slot after `"sht"`. Popup: name, segment
  length, trail no., class, surface + a note that it shares tread
  with the NCT and the two lines are separate surveys.
- Files: `data/brt/brt.geojson` (source of record, 24 feats,
  131,974 B) + `site/data/border-route-trail.geojson` (same).
  Legend row + data-sources.html section (USDA Forest Service,
  public domain, pulled Nov 16, 2026).

## Job 2 — Trails near the Border Route & SHT (`id: "near-brt-sht"`)

- Source: the intersecting-trails inventory
  (`docs/nct-intersecting-trails-minnesota-2026-11-16.md`,
  sections A + F). All 28 named Superior NF / BWCAW trails that
  meet the NCT in the Arrowhead, pulled live from TrailNFS by
  exact `trail_name` (`scripts/pull-near-brt-sht.py`):
  **53 features, 113.69 GIS miles measured** (field ~112.4).
  Names: Kekekabic (10), Snowbank, Old Pines Loop,
  Benezie–Becoosin Loop, Magnetic Rock, Caribou Rock (2),
  Bridal Veil Falls, Bryce Breon, Centennial (2), Gunflint
  Lookout, Kekekabic to Magnetic Rock, Upper Gunflint West End
  (4), South Rim (2), Overlook (2), Cut Across (2), Aspen Rabbit
  (2), Power Line (2), Lonely Lake (2), Short Cut (2), Warrens
  Road (2), Gunflint Lake G Connect, South Fowl ATV (3), South
  Fowl Snowmobile (2), Thomas Lake Winter, Thirteen Corners,
  Madden Winter, Hidden Valley Trezona, Trezona.
- Membership, measured Nov 16 (distance to the BRT line, UTM 15N):
  13 touch the BRT tread (0 m); 3 meet the NCT within ~700 m of
  it (Bryce Breon 230 m, Warrens Road 267 m, South Fowl ATV
  687 m — inside the NCT-line/BRT-line disagreement); 4 meet the
  NCT just west of the BRT's western end, within ~4 km (Centennial
  2,991 m, Kekekabic 3,038 m, Kekekabic to Magnetic Rock 3,105 m,
  Gunflint Lookout 3,837 m — the Kekekabic is the BRT's western
  connector; its drawn line stops ~3 km short of the BRT line);
  8 meet the NCT further west on the Arrowhead approach (Ely /
  BWCAW, 38–60+ km from the BRT line). Nearest any comes to the
  SHT line is 7.2 km (South Fowl ATV) — **no inventory trail
  meets the SHT itself**. The layer is the inventory's §F +
  Kekekabic set, not only BRT-touching trails; the popups and the
  data-sources section say so plainly.
- NOT in the layer: the Upper Gunflint near-misses (Amperage,
  North Star, Big Pine, Rabbit Run, Highlands, Connector, Aspen
  Alley, Ham Lake, Little Pine, River — 100–300 m from the NCT,
  inventory-verified as not meeting it); the Gunflint Snowmobile
  Trail (52.7 m, just outside the inventory's 50 m tolerance,
  unverified).
- Wiring: ONE layer `id: "near-brt-sht"`, label "Trails near the
  Border Route & SHT", group "Other trails", OFF by default +
  lazy, amber `#d97706`, weight 3, opacity 0.85, draw-order slot
  after `"brt"`. Popup per trail: name (title-cased from the
  ALL-CAPS service name), type (hiking / hiking loop / hiking
  spur / cross-country ski / winter / ATV / snowmobile), segment
  length, trail no., surface, and what it meets (BRT tread /
  within ~700 m / just west of the BRT / Arrowhead approach).
- Files: `data/near-brt-sht/near-brt-sht.geojson` (53 feats,
  517,273 B) + `site/data/near-brt-sht.geojson` (same).
  Legend row + data-sources.html section (USFS, public domain).

## BWCAW portages & connectors (`id: "bwca-portages"`)

- The 26 named portages from the inventory (§G), pulled live from
  TrailNFS (`scripts/pull-bwca-portages.py`): **39 features,
  20.50 GIS miles measured** (field 20.62), 0.03–3.67 mi each.
  Each verified meeting the NCT at 0–44.7 m.
- Two TrailNFS spellings kept as the service carries them:
  `'BRT-CLEARWATER LK CAMPSITE TRL'` and `'BRT-PARTIDGE
  CAMPSITE'` (USFS typo for Partridge). A third: the service
  spells it `'CLEARWATER/DANIELS LAKE'` (slash, no spaces) —
  the first pull used the hyphenated form, matched nothing, and
  returned 36 features; the script was corrected and re-run to
  39 features / 26 names. That is why the count moved.
- Wiring: own layer, group "Other trails", OFF by default + lazy,
  light stone `#a8a29e`, weight 2, opacity 0.7, dashed — portages,
  not hiking trails. Popup: name + portage length + trail no.
- Files: `data/bwca-portages/bwca-portages.geojson` (39 feats,
  182,091 B) + `site/data/bwca-portages.geojson` (same).
  Legend row (dashed swatch) + data-sources.html section.

## Bolder lines — BRT + SHT (Paul, Nov 16)

- Target: weight 5, opacity 1.0, plus a casing. Both the new BRT
  def and the existing SHT def now build through `boldLine()`:
  white casing (weight 8, opacity 0.9, non-interactive) + coloured
  core (weight 5, opacity 1.0) + invisible hit-line (see below).
  Other trails unchanged (loops/ATV/OHM/snow/near weight 3,
  opacity 0.85–0.9; portages weight 2, opacity 0.7).
- Legend: `line()` takes a third `bold` argument
  (`border-top-width:5px`); the BRT and SHT rows use it, under a
  "Partner Trails" legend sub-heading.
- The SHT def comment was updated: the morning's "No Border Route
  Trail layer" sentence is removed (superseded — the BRT is now
  its own layer). SHT geometry untouched (553 feats / 207.6 mi).

## "Partner Trails" subgroup (Paul, Nov 16)

- `subgroup: "Partner Trails"` set on the BRT def and the SHT
  def, both staying in group "Other trails", off by default,
  bold weights. Follows the Timber sales / Management pattern
  under "The land" (sub-heading + ▸/▾ pull-down, created on
  first use).
- Statically verified in code (`site/app.js` panel builder,
  ~line 6360): "Other trails" is in GROUP_PULLDOWNS (the
  coordinator's collapse fix, confirmed present); the builder
  creates `div.tog-subgroup` "Partner Trails" + `button.tog-expand`
  "▸" + `div.tog-subgroup-body.collapsed` when it reaches the SHT
  def, and appends the BRT label into the same body. Panel order
  in "Other trails" will be: ATV, dirt bike, snowmobile, then the
  Partner Trails subgroup (SHT + BRT), then near-BRT/SHT, then
  portages. **Live visual confirmation of the subgroup pull-down
  is still owed** (no live browser in this pass) — the running
  click-through task should check it.

## Job 3 — Mountain bike trails: NEGATIVE, nothing drawn

No `mtb` def, no file. Sources checked Nov 16:
- DNR enterprise catalog (fetched): NO mountain-bike service
  exists — only state trails, park trails, hunter walking, OHV,
  snowmobile, water.
- DNR `use_mntbik` field (1/0) in `trans_state_trails_minnesota`
  (371 of 647 feats = 1) and `trans_state_park_trails_roads`
  (111 of 1,996): marks paved multi-use state trails as
  bike-permitted (Paul Bunyan, Taconite, Matthew Lourey, Willard
  Munger, Gitchi-Gami, David Dill, Heartland, Cuyuna Lakes State
  Trail, Alex Laveau, Central Lakes) — NOT purpose-built MTB
  singletrack. Drawing it would mislabel rail-trails as MTB.
- USFS TrailNFS `bicycle_accpt` is a season string, not 'Y' —
  204 features carry a season; the named trails are MOQUAH SPUR
  (47, Wisconsin), BAYFIELD CONNECTOR (39, Wisconsin), NCT
  segments themselves, and Kawishiwi Triangle hiking/ski trails.
  No MTB-designated system.
- OSM API bbox fetches (real XML parse): Maplelag 0/1,151 ways
  mtb-tagged, Tioga 0/2,292, Giants Ridge 0/2,382, Duluth/Spirit
  Mountain 0/4,055. Name grep confirms no MTB singletrack names;
  `bicycle=designated` counts (Tioga 18, Giants 53, Duluth 10)
  are paved paths, unverifiable as MTB.
- Overpass still down (502 Gateway Timeout, at capacity).
- Owed follow-up: a corridor-wide Overpass query when it
  recovers, or a chapter-sourced MTB list (Maplelag, Tioga,
  Giants Ridge, Spirit Mountain are the known candidates).

## Job 4 — Motorized FULL STATE (Paul, Nov 16)

Full state supersedes BOTH the 2-mile corridor pull and the
5-mile clip mentioned first. Script:
`scripts/pull-motorized-mn-statewide.py` (two-pass fetch, id list
first, then objectIds in chunks of 500, `requests` — same as the
corridor script with the clip removed; header notes the statewide
scope and Paul's Nov 16 call). Corridor files kept on disk,
untouched (`data/motorized/*-mn-corridor.geojson`).

Live pull, Nov 16 (service counts match the coordinator-verified
figures: OHV 7,931 features, snowmobile 276):
- **ATV: 6,968 features, 102 systems, 3,357.12 GIS miles
  measured vs field 3,356.71** — max per-feature |field − drawn|
  0.005 mi, ZERO features differ >0.05 mi.
- **Dirt bike (OHM): 5,732 features, 78 systems, 2,551.23 GIS
  miles measured vs field 2,550.79** — same agreement (max
  0.005 mi, zero >0.05).
- **Snowmobile: 276 features, 191 systems, 23,151.35 GIS miles
  measured vs field 23,152.50** — median per-feature deviation
  0.027 mi, worst 0.427 mi, 10 features >0.05 mi (service-side
  rounding/splits, not a clip artifact).
- The corridor-boundary caveat is GONE: every feature is whole,
  so field vs drawn agrees except where the service itself splits
  a trail.
- Correction to the earlier reading: the snow `miles` field is
  NOT a "system total distinct from drawn length". The corridor
  pull's 3,254.3 field vs 587.95 drawn was a clip artifact — each
  clipped feature kept its whole-feature miles value. Statewide
  the field ≈ the drawn length per feature. The popup keeps the
  "Published miles" label; the data-sources note now says the
  published figure matches the drawn length (within 0.43 mi worst
  case).
- Viewer copies replaced: `site/data/motorized-atv.geojson`
  (6,968 feats, 10,967,800 B), `site/data/motorized-ohm.geojson`
  (5,732 feats, 10,011,486 B), `site/data/motorized-snow.geojson`
  (276 feats, **36,135,915 B**). All three are lazy + off by
  default, but the snow file is 36 MB — it will be slow to load
  on toggle. Owed follow-up: simplify the snow geometry
  (coordinate rounding / Douglas–Peucker) or split it, before
  anyone is expected to toggle it on a slow connection.
- Text updated everywhere it said corridor: ATV/OHM/snow def
  comments + titles, the three popups ("Full state — every DNR
  … trail in Minnesota"), legend rows ("(DNR, statewide)"), and
  the three data-sources.html sections (statewide counts + miles;
  the snow section also notes the 36 MB file). No "within 2
  miles" wording remains in `site/app.js` or
  `site/data-sources.html` (grep-verified).

## Line popups don't open on click — FIXED (live click-through finding)

- Symptom: clicking ATV lines (5–6 tries, zooms 10–13, including
  a direct hit on a long straight line) never opened a popup;
  a Waboose loop line also did nothing (its popup opened only via
  the marker). Bindings exist in code, so the cause is the canvas
  renderer: `renderer: canvasFor()` with weight-3 lines gives a
  ~±1.5 px hit target, too thin to click reliably.
- Fix: every clickable line layer now draws an invisible hit-line
  over the visible line — same geometry, weight 12, opacity 0,
  interactive, carrying the popup; the visible line is
  non-interactive. No visible style changes. Helper `hitLine(gj,
  style, popupFn)` returns a LayerGroup [visible, hit]; `boldLine`
  (SHT/BRT) gains the hit-line as a third sub-layer with the
  popup moved off the core.
- Applied to all 8 clickable line layers: loops, ATV, OHM, snow,
  SHT, BRT, near-BRT/SHT, BWCAW portages. (No `mtb` layer exists.)
  `node --check` passes. **Live click verification is still owed**
  — the next click-through should re-try ATV lines and a loop
  line at several zooms.
- Safety check before converting the builds to LayerGroups: the
  only `def.layer` consumers are `ensureLayer`/`removeLayer`
  (group-safe) and `assertDrawOrder` (already handles groups via
  `eachLayer` — the boundaries def returns a group the same way).
  No `setStyle`/`getLayers` assumption on any line def was found.

## Lake Erin loop doesn't show live — INVESTIGATED, no code cause found

- The data is fine and live: `site/data/chapter-loops.geojson`
  has all 6 features; Lake Erin is 229 pts at lon
  -94.53577..-94.53220 / lat 47.01440..47.01791; the LIVE file is
  byte-identical to local (md5
  27c25ca10826d9a5c8f8f641bfb49e44). Waboose and Nelson draw from
  the same file, so the file loaded.
- Code check, all negative: the loops build has NO `filter`, no
  pane, no per-feature style function — every feature gets the
  identical teal weight-3 treatment; nothing can skip one
  feature. Draw order puts loops above the trail/stretches and
  below gaps/boundaries; no fill layer sits above it in that
  area. The lazy loader fetches the whole file (no viewport
  clipping). The popup reads `name`, `length_mi`, `source`,
  `gap_note` — Lake Erin carries all four. The loop sits 32.7 m
  from the NCT line (right beside the trail, as intended) and is
  open at the trailhead gap by design.
- Most likely explanation is SCALE: the loop is 0.62 mi of trail
  in a 270 m × 390 m box — about 3 px wide at zoom 10, ~21 px at
  zoom 13, ~165 px at zoom 16. In a whole-chapter scan at zoom 10
  it is a 3-pixel speck; at zooms 13–16 "near Chip-5" it is
  findable only if the viewport is centred on its exact bbox.
- **Not proven, only the best explanation.** The next live check
  should zoom straight to centre (-94.534, 47.0162) at zoom 16
  to settle it. If it still doesn't draw there, the cause is in
  the live browser state, not in this code or data.

## What was NOT touched

- Basemap defs, BASES, MAPBOX_TOKEN, MAPTILER_KEY, STADIA_KEY —
  untouched. GeoPDF export files (`site/export.js`,
  `scripts/export_geopdf.py`) — untouched; export entries for the
  new layers (loops/atv/ohm/snow/sht/brt/near/portages) are still
  owed as a separate job. SHT geometry untouched (553 / 207.6 mi).
  No Central Lakes State Trail layer. No deploy, commit, or push.

## Verification performed (on disk)

- `node --check site/app.js` — passes.
- All six viewer files parse as JSON with the expected feature
  counts (BRT 24, near 53, portages 39, ATV 6,968, OHM 5,732,
  snow 276).
- Grep-confirmed: `id: "brt"`, `"near-brt-sht"`,
  `"bwca-portages"` defs; `subgroup: "Partner Trails"` on SHT +
  BRT; `hitLine` builds on loops/ATV/OHM/snow/near/portages and
  `boldLine` on SHT/BRT; draw-order list carries
  `"sht", "brt", "near-brt-sht", "bwca-portages"`; legend rows
  incl. the bold BRT/SHT swatches + "Partner Trails" heading;
  no "within 2 miles" wording left in app.js or
  data-sources.html; GROUP_PULLDOWNS contains "Other trails".
- Measured miles vs field miles for every new file (see above);
  BRT-vs-NCT distances via STRtree; Lake Erin bbox/distance
  measured; snow per-feature deviations computed.

## Still owed (not in this pass)

1. Deploy + live verification: subgroup pull-down renders
   (heading + ▸/▾ + both toggles), hit-line clicks open popups
   on ATV + loop lines, Lake Erin at zoom 16 centred on
   (-94.534, 47.0162).
2. GeoPDF export entries for loops/atv/ohm/snow/sht/brt/
   near-brt-sht/bwca-portages.
3. MTB: corridor-wide Overpass query when Overpass recovers, or
   a chapter-sourced MTB list.
4. Snow file is 36 MB — simplify or split before it is toggled
   on slow connections.
5. SOURCES.md motorized section still describes the chapter-extent
   pull (pre-existing debt, not touched here); the statewide
   numbers above supersede it.

# The map site (v7 — chapter working view)

A single-page Leaflet map in plain HTML/CSS/JS. No build step, no
API keys, nothing to install: `index.html` + `app.js` + `style.css`.
Leaflet 1.9.4 is vendored alongside (`leaflet.js`, `leaflet.css`,
`images/`) so the site has no CDN dependency — in keeping with the
portability rule. Base-map tiles come from public tile servers
(OSM, OpenTopoMap, MnGeo, USGS, Esri), so viewing needs an internet
connection. Append `#layers=access,roads` to the URL to open with
those layers already switched on.

The side panel carries the masthead, the
adoption story box with its mini-legend, the Find box, the
section inspector, the layer toggles, and the load status. The
reference material lives over the map instead: two
buttons in the map's bottom-left corner, **ⓘ Sources** and
**Legend**, each open a small floating card (the data-source
credits; the legend). Both start closed; a second click closes a
card. The Leaflet attribution in the bottom-right is separate and
always visible.

## Viewing locally

From this `site/` directory:

```sh
python3 -m http.server 8000
```

then open <http://localhost:8000>. (Opening `index.html` as a `file:`
URL will not work — browsers block the data fetches.) To publish,
copy the whole `site/` directory to any static host; paths are
relative throughout.

## Layers

The map loads simplified site copies from `site/data/` — never the
working data in `../data/` directly. Layers load lazily the first
time their checkbox is switched on.

| Toggle | File | Default | Contents |
|---|---|---|---|
| Official trail line | `data/trail.geojson` | on | The official NCT depiction in the chapter extent, styled by chapter (Itasca Moraine green, Laurentian Lakes purple) and by kind (off-road solid, on-road dashed). Popup: chapter, type, certification, length, ownership, managing authority. |
| Adopted sections | `data/stretches.geojson` | on | The chapter's adopted sections (from the adoption tracker joined onto the boundary-point overlay), drawn in amber over the official line, each with its name as a permanent tooltip at mid-section — floating **above** the line on east–west segments, **beside** the line on north–south segments (v3, judged from the segment direction at the label anchor). **No popup (v4): clicking a section selects it into the panel inspector** (see "Section inspector" below); hovering shows only a small name/facts chip. Default ON since v4 — the adopted sections are the chapter's story. |
| Adoption segment ends | `data/boundaries.geojson` | follows Adopted sections at first load | **Its own toggle** (Chapter group, since Nov 11, 2026): the initial state is derived once from the Adopted sections toggle (or from an explicit `#layers=boundaries` / `#layers=-boundaries` hash token), after which the two toggles are fully independent — the markers are a bar struck **across** the line at every section start/end — perpendicular to the trail's bearing there, unlabelled, positioned on the stretch geometry endpoints (never at raw KMZ pin positions — one pin sits ~3.6 km off the line). **The bar scales with zoom** (v3): ~22 px on screen at any zoom, floored at the built 140 m length and capped at 1.6 km (chapter termini cap at 4.2 km), so it stays visible when zoomed out without sprawling across the map when zoomed in. Softened in v4 to a slate core with a lighter casing. The same file's two chapter termini are the separate layer below. |
| Chapter ends (Itasca Moraine west & east) | `data/boundaries.geojson` | on | The boundary-bar language at chapter weight: a green bar across the line at each end (~56 px on screen, floored at ~280 m), labelled "Itasca Moraine — west end" (chainage 0, at the GAP-W west end in Itasca State Park) and "Itasca Moraine — east end". Always available with the official line, independent of the sections toggle. |
| Unadopted gap (unclaimed) | `data/gaps.geojson` | on | Stretches of the depicted line no section covers, drawn bold dashed red — the recruiting layer. Currently one: GAP-W, 2.92 mi in Itasca State Park. It carries a permanent on-map label ("Unadopted — 2.9 mi", shown at zoom ≥ 9) and, like a section, **clicking it selects it into the panel inspector** (length, land context, nearest access at each end, trails crossing it). **v7:** the core's dashes slowly march westward while the layer is on (stopped by reduced-motion settings, a hidden tab, or print), and at zoom ≥ 11 the label becomes a Carsonite-style sign chip (paper fill, red border). |
| Parcels | `data/parcels.geojson` | On the map — off by default, lazy | Parcels are **in the panel** (Context group) since the v8 re-enable (Nov 10, 2026 evening): the toggle starts unchecked and `data/parcels.geojson` is fetched only on the first check (lazy, like Trail alerts). When on: trail-corridor parcels (crossed + adjoining ring). Popup: parcel ID, county, land class, acres, and the **owner name + mailing address as published in the county parcel records** (public record — see Privacy). 919 of the 1,038 site parcels carry a published owner; the rest (mostly public land) show no owner row. |
| Non-road access | `data/access.geojson` | off | MN DNR lines: state park trails/roads, OHV trails, state trails, snowmobile trails, hunter walking trails, styled by kind — hairlines with per-kind zoom gates (state trails from zoom 10, OHV/snowmobile from 11, park/hunter from 13). **Corridor-clipped in the site build (v7)** to ±800 m around the drawn lines — see "Corridor crop" below. State forest roads are **no longer in this layer** — they moved to Roads as class F (v7). Renamed from "Access lines" Nov 10, 2026 (Paul: "call access lines non road access"). |
| Roads | `data/roads.geojson` | off | Road centerlines **corridor-clipped in the site build (v7)** to ±1.6 km around the drawn lines and drawn in four classes derived at build time from the source `route_sys` codes + name patterns: **A** arterial (trunk highways + county state-aid, the old v3 mid-grey 1.75 px), **B** local named, **C** minor/township/unnamed, **F** state forest roads (moved from the access data). Classes appear by zoom (A from 10, B/F from 11, C from 13); corridor-clipped roads draw faded (`cut` feather). Popup and hover chip carry the road's name + class. Off by default. |
| Mile markers (state) | `data/milemarkers.geojson` | off | The NCTA Minnesota half-mile points snapped to the drawn lines in the site build (244 pulled for the extent, 239 retained; points more than 250 m from a drawn line follow an authorised route the map doesn't draw and are excluded — count printed by the build). Whole miles: slate disc with a white ring + the bare state-mile number as a label at zoom ≥ 13; halves: small dot, labelled only at zoom ≥ 15. **This is the state (NCTA) reckoning** — it differs from the chapter tracker's miles by roughly 46–48 mi; the two are never mixed (tracker figures are labelled "chapter tracker miles" wherever they appear). |
| Places | `data/gazetteer.geojson` | off | The gazetteer's 114 NCTA waypoints drawn as a layer (v7): 15 px paper discs with a slate ring and a letter — **P** parking, **C** camping, **W** water, **S** shelter — and plain slate dots for POIs. Zoom ≥ 13 only. Popups are the same gazetteer records Find shows. |
| Chainage numerals | `data/chainage.geojson` | always | **No toggle** — annotation, like the section names: a small slate numeral on the line every 10 chapter miles from the west end (10, 20, … 70), shown at zoom ≥ 11 and placed by the same collision pass as the section names. These are *relative* miles from the chapter's west end — not NCT miles in either reckoning. On printouts the cadence tightens to every 5 miles. |
| Access points (section crossings) | `data/access-points.geojson` | **removed** | **Layer removed Nov 10, 2026 (Paul's call)** — no toggle, nothing fetches the file. The computed crossings (111 points) remain available as the gazetteer's Road/Trail crossing entries (searchable via Find), and the data file + builder stay in the repo. The §5 caution in `../docs/segment-gap-analysis.md` still applies to the crossing data wherever it appears: a crossing is a line on a map, not a drivable route. |
| Chapter places | `data/chapter-places.geojson` | off | The chapter's own place records — seeded from the 36 NCTA camping points (Nov 2026) and maintained by the chapter (see `../docs/chapter-places-guide.md`). A chapter entry supersedes the NCTA point at the same spot in the Places layer and the gazetteer, so a place shows once, as its chapter version. Rogstad Campsite is carried as CLOSED (per the NCTA trail alert of Apr 12, 2026). Off by default, lazy-loaded on first toggle, like parcels. Place cards (here and in Places) carry a "Directions (Google Maps)" link built from the point's own coordinates. |
| Asset pins | `data/assets.geojson` | off | Photo-inventory pins. **This file does not exist yet** — until the first real photo batch runs, the toggle sits disabled in the panel, labelled "(no photos yet)"; a one-time probe enables it if the file appears. The pipeline writes `data/assets/assets.geojson` in the repo; copying it to `site/data/assets.geojson` publishes the pins. |

### Corridor crop (v7)

The working data under `../data/` is **never cropped** — the
corridor is a view the site build applies to the two context
layers, exactly like the parcels corridor is a view the parcels
pull applies. In `scripts/build_site_data.py`, after the usual
simplification, non-road access is clipped to **±800 m** and
roads to **±1.6 km** around **both drawn lines** (the Itasca
Moraine chain and the Laurentian Lakes chain the map draws):
lines are cut at their vertices with the exact boundary-crossing
point interpolated, kept runs under 25 m are dropped, roads get a
≤250 m "finish the block" extension to their segment's end
vertex, access lines get ≤150 m junction stubs where those reach
another retained line, and a line that *crosses* the trail is a
connector — kept whole if ≤ 3 km long, otherwise its crossing
run is extended 1.5 km past the corridor edge (such features
carry `connector: true`; clipped features carry `cut: true` and
draw faded). The design contract is
`../docs/cartography-notes-2026-11-10.md` (Part 1); its §0 counts
were raster any-touch estimates — the build's exact geometric
counts run lower (318 of 3,670 access features touch ±800 m, 34
of them state forest roads; 259 of 5,902 roads touch ±1.6 km),
and C2's under-25 m rule drops a few glancing touches more
(access ships 267 features; roads ship 289 including the 33
forest roads) — the build prints its counts every run.

So the map opens (default view, v4) with the official line, the
adopted sections over it, the unadopted gap, and the two
chapter-end markers — the panel tells the adoption story up front
(73.2 of 76.2 depicted miles adopted, one 2.9 mi gap) with a
five-item mini-legend under it. The opening fit leaves room for
both chapter-end labels. Parcels are built but UI-disabled as of
Nov 10, 2026, pending a later re-enable (see the Parcels row
above). Toggles are grouped (Chapter / Context) and each wears a
swatch generated from the same style constants the layer draws
with, so the panel, the legend, and the map cannot drift apart.

The URL hash also accepts `#view=lat,lon,zoom` to open at a
particular view instead of fitting the whole trail (combinable with
`#layers=`, e.g. `#layers=access,roads&view=47.152,-95.195,13`).

Base maps (switcher, top right): thirteen bases in four task groups,
in this order — **Topographic:** Topo (OpenTopoMap, **the default
since v4** — a new visitor meets terrain first), USGS Topo 1:24k
(The National Map, built from the 1:24,000 quadrangle series —
added in v3), National Geographic (Esri); **Relief:** MN LiDAR
Hillshade, MN LiDAR Canopy, Canopy height (LiDAR); **Aerial:** Aerial (NAIP 2023/25), Aerial (Esri), Aerial +
Topo (NAIP 2023/25), Aerial (2014) — on any aerial base the
section labels flip to a light-on-dark treatment so they stay
readable over photography; **Streets & trails:** Streets (OSM),
Trails (CyclOSM), Winter (snow trails). The chooser is the Leaflet radio control grouped under
small headings in the panel's style, with the current base shown
as a tinted row (app.js post-pass; style.css `.base-group` /
`.base-active`).
**Pruned Nov 11, 2026 on Paul's calls** (after the Nov 10
sixteen-candidate review round): Esri World Topographic, Stamen
Terrain, CARTO Voyager, CARTO Positron, Thunderforest Outdoors,
Esri World Hillshade, OSM Humanitarian — definitions and the two
placeholder API keys removed; no base needs a key.
**Added Nov 11, 2026** (Paul approved the pair): **Aerial
(2014)** — Esri World Imagery Wayback release 5844 (2014-12-30),
the dated-imagery archive's release closest to the end of 2014;
and **Winter (snow trails)** — a composed base: OpenSnowMap's
transparent pistes tiles stacked over the MN LiDAR Hillshade
(the pistes carry no cartography of their own, and OpenSnowMap's
base snow map is deliberately not used — its author discourages
outside use). OSM's mapped pistes in the chapter extent are the
nordic ski trails around Itasca State Park and the Leech Lake
shore; where none are mapped the base reads as plain hillshade.
**Added Nov 11, 2026** (Paul's LiDAR trio — the bare-earth
hillshade was the first of three): **MN LiDAR Canopy** and
**Canopy height (LiDAR)** — the 2022 second-generation LiDAR
surfaces, built in-repo by `../scripts/build_lidar_trio.py`
from the state's 2022 point clouds (first returns) and the
seamless 0.5 m DEM, as this repo's own tiles (`tiles/`, z9–15;
z16 was rendered, measured at +152.5 MB, and dropped).
Canopy is a grey hillshade of the first-return surface;
Canopy height is canopy-minus-ground as a colour ramp (pale =
ground level, deep green = mature canopy), so clearcuts and
fields read bare. Both exist only along a ~100 m corridor
either side of the trail — the tiles end at the corridor edge,
by design. Provenance and the build's cost measurement:
`../SOURCES.md`.
Cut in v3 on Paul's calls: the USGS shaded-relief base (poor next
to the 1 m LiDAR hillshade) and MnGeo's Spring Aerial Imagery
Program photography (nw14 — nothing useful over the chapter).
Providers, vintages and endpoints: `../SOURCES.md`.

**Section inspector (v4, replaces the v3 hover card and section
popups):** one selection model serves the whole map. Clicking a
section line (or the gap) selects it: a white-and-amber highlight
hugs the line on the map, and the section's full public-safe
tracker record renders as a "record sheet" in the left panel,
below Find — name + tracker code + Adopted/Unadopted pill, a key
strip (length with the tracker length in parentheses, NCT miles +
map refs, adopter and sawyer **initials**), a red "Help
requested" callout when the tracker asks for help, the
description, a "Section details" disclosure (land, 2026
maintenance, tracker comments, distances from each chapter end,
access at each end) and a "What's here" contents list, with
Zoom / Prev / Next buttons that walk the sections in trail order.
Clicking empty map, pressing Esc, or the × clears it; on phones
the inspector becomes a bottom sheet. Hovering a section shows
only a small chip — name, length, adopter (or "Unadopted"),
"Click for the full record" — after a 300 ms dwell; it never
follows the cursor and never covers the line you are tracing.

## Gazetteer (the Find box)

The panel's **Find** box searches `site/data/gazetteer.geojson`
(built by `scripts/build_gazetteer.py` from the working data; the
index loads lazily on first focus, never at page load). Every
entry is a point carrying two mileages: **chainage** (miles along
the depicted chain from its west end) and the **NCT virtual mile**
(the tracker's calibration: inside a section, interpolated between
that section's declared `nct_mile_start/end` by chainage fraction;
in GAP-W, interpolated 166.58 → 169.5 across the gap; never
extrapolated — where the calibration doesn't cover a point, the
field is null). Selecting a result is a real combobox interaction
(arrow keys move the active row, Enter selects through the same
path as a click; `/` focuses the box from anywhere). A
**section** result selects that section into the panel inspector
and fits the map to the section's shape — its full tracker record
plus the **"What's here"** contents list (every crossing,
waypoint and boundary the index places inside it) live there now.
Any other result flies the map to it, drops a temporary
highlight, and opens an info card (kind, NCT mile, section,
distance from each chapter end). A search with no hits says so
explicitly and suggests a section, a road, or a lake.

Entries (257 in the 2026-11-10 build): 32 section records
(31 sections + GAP-W), 32 section boundaries, 2 chapter ends, 114
NCTA waypoints (Parking 43, Camping 36, POI 29, Water 4, Shelter
2 — the same NCTA public service's point layer, first used here),
and 77 computed road/trail crossings. Rules that shape the index:

- **Dedupe:** a computed crossing within 100 m of an NCTA parking
  point is dropped in favour of the named NCTA entry (34 dropped).
- **Off-chain waypoints:** the NCTA point layer covers a wider
  envelope than the depicted section chain (it includes waypoints
  on the NCT west/south of the chapter's depicted stretch). A
  waypoint more than 250 m from the depicted chain keeps its true
  position and its snap distance but gets **no** chainage, NCT
  mile or section (66 of 114) — assigning it a chain position
  would fabricate one.
- **West-10's span gets no interpolated NCT miles**: the tracker
  records that loop section's span as 192 → "Loop", not a linear
  calibration, so its entries' `nct_mile` is null.
- Named lakes/water bodies are **not** entries: no water-body
  names source exists in the project data (some roads/trails are
  named after lakes — a road named "Perch Lake" is a road).
  Parcels aren't entries either (1,038 of them; the layer is
  their home).

### Spreadsheet fields — what crosses, what never does

Section records surface the adoption tracker's content in the
gazetteer under these exact rules (Paul's steer, 2026-11-10: "add
as much information from the spreadsheet as possible"):

**Crosses into the site copy:** section description (also
searchable — "Ozawindib", "South Entrance"), NCT MN map refs
(e.g. MN-031; also searchable), NCT virtual miles start/end,
tracker length, land context, the **2026 maintenance notes**, the
**Help Requested? values verbatim** (shown under the exact label
"Help requested (as recorded in tracker)" — the bare integers in
that column are unexplained and stay unexplained), and tracker
comments **after** name substitution (next paragraph); a comment
that still contains an unmatched personal reference is dropped
from the site copy (2 of 18 on this build; the working data keeps
it verbatim).

**Crosses only as initials:** adopter names (initials of first +
last name, e.g. "JR"; first-name-only people get one letter) and
**sawyer names**, mapped through the *same* initials, so the same
person is the same initials everywhere (one person appears only
as a sawyer, Chris Godwin → "CG"). Maintenance notes and
descriptions get the same substitution for any person named in
them. Any email/phone pattern found in tracker text is stripped
before it crosses (0 found on this build) and the strip count is
printed by the build.

**Never crosses, under any circumstances:** the tracker's
**Phone Number** and **Email** columns. They are not read by any
site build; verified on this build — zero `@` in the gazetteer
file, zero phone-number patterns anywhere in `site/data/`, and
zero hits for any full adopter/sawyer name anywhere under `site/`.

## Performance note

Layer toggles were visibly slow (parcels especially) — a
render/DOM problem, not data volume (parcels: 494 KB, 9,434
vertices). The parcels layer is UI-disabled in this build (see
above), but its canvas/perf code path is retained unchanged and
returns when the layer is re-enabled. Two fixes, both in
`app.js`: (1) the draw-order handler
on `layeradd` fired **once per feature** when a GeoJSON group was
added — 5,902 times for roads — each firing re-asserting layer
order; it is now coalesced to one re-assertion per animation
frame; (2) the heavy layers (parcels, access lines, roads, and
also the official line, adopted sections and the gap) draw on
**one shared canvas renderer** instead of thousands of SVG DOM
paths (popups and click hit-testing verified working on canvas; a
canvas renderer in a *custom pane* renders but stops receiving
clicks in Leaflet 1.9.4, so the shared renderer stays in the
default pane, and the small point layers stay SVG above it).
Measured in the headless proof harness (synchronous add time,
before → after): parcels ~100 ms → ~12 ms; access lines
~303 ms → ~54 ms; roads ~426 ms → ~43 ms; the light layers were
already ≤ ~9 ms and are unchanged in feel. Layers are built once
and cached — re-toggling never refetches.

## Site data copies

`scripts/build_site_data.py` (run from the repo root) regenerates
`site/data/` from `../data/`:

- coordinates rounded to 5 decimals (~1 m);
- geometry simplified with Douglas–Peucker in a local projection
  (tolerances: trail 10 m, parcels 15 m, access 15 m, roads 20 m,
  stretches/gaps 10 m; points are only rounded);
- attributes **whitelisted** per layer — anything not listed is
  dropped (parcels normalized across the MnGeo and Hubbard County
  schemas to parcel ID / county / land class / acres / corridor /
  owner / owner address; segment layers use the public-view
  whitelist documented in the build script's header);
- `site/data/boundaries.geojson` is built in the same run from the
  stretch geometry endpoints plus the GAP-W west end (33 points,
  each carrying the endpoints of its across-the-line tick bar —
  see the Layers table). `site/data/gazetteer.geojson` is built
  separately by `scripts/build_gazetteer.py` (see Gazetteer).

Sizes after simplification (2026-11-10 v7 build): trail 0.07 MB,
parcels 0.49 MB, access 0.12 MB, roads 0.08 MB (both after the
corridor crop — v2 was 1.68 MB / 0.97 MB uncropped), stretches
0.04 MB, gaps 0.002 MB, access points 0.03 MB, boundaries
0.007 MB, gazetteer 0.10 MB, mile markers 0.04 MB, chainage
0.002 MB. `site/data/milemarkers.geojson` is emitted in the same
run from `../data/points/mile-markers.geojson` (pulled by
`scripts/pull_mile_markers.py`; only points snapping within
250 m of the drawn lines are kept), and
`site/data/chainage.geojson` is built from the site stretches
copy (a point every 5 chapter miles from the west end). Three tiny parcels
(of 1,041) were dropped by polygon simplification; they remain in
the source file. One stretch (CHP-13) is absent from the site copy
because its source geometry is a single point — see Known data
notes.

## Privacy (two opposite rules — read carefully)

**Parcel owners: shown.** The owner name and mailing address in
the county parcel records are published public records, and the
chapter ruled on 2026-11-10 that the site shows them. The site
copy therefore carries `owner` / `owner_address` (from the same
published county record) and the parcel popup displays them.
Taxpayer name/address fields are still **not** carried. Personal
contact fields (maintainer names/phones/emails) present in some
DNR access source attributes are likewise stripped, not shown.

**Adopter names: initials only.** The working segment files in
`../data/segments/` carry the adoption tracker's personal data
(real adopter names, sawyer, maintenance notes). The site copies
never contain a real adopter name: `scripts/build_site_data.py`
derives each distinct adopter's initials — first letters of first
+ last name (scripts/person_initials.py; Paul decided the one
collision broken apart: Brent Johnson "BJ", Bruce Johnson "BrJ")
— and emits only the initials (`adopter_display`), shown in the
section popup's "Adopted by" row. Because the initials are
derived from the name, the same person reads as the same
initials on every section without any name leaving the
working data. Sawyer, maintenance notes and tracker comments are
dropped outright; the full whitelist and exclusion list are
documented in the build script's header. Verified on the
2026-11-11 initials build: zero hits for every full adopter name in the
working data anywhere under `site/`, zero email patterns, zero
phone-number patterns, and zero `@` characters in `site/data/`.

The panel opens with a masthead: the North Country Trail
Association logo (the association's own site file, used
unaltered) beside the chapter wordmark — the logo carries the
association, the wordmark carries the chapter (design-notes
2026-11-10 §1). The old "Working draft — not an official NCTA or
National Park Service map" notice was removed Nov 10, 2026 on
Paul's word; the map is an Itasca Moraine **Chapter** project,
and the Sources card credits the trail line to NCTA/NPS.

## Printing

`style.css` has `@media print` rules because the chapter recruits
with paper maps at events: landscape, the panel's print masthead
(logo + wordmark + the print date line) and adoption story box,
the map in the current viewport, and a **print-only legend** in
the panel (the on-screen corner cards stay screen-only). The
Leaflet attribution still prints — it is a licence condition, not
chrome. If a section is selected, its inspector sheet prints on a
following page as a hand-out card for a prospective adopter.
Pan/zoom first — print renders whatever is in the current
viewport. **Untested on paper**; proof before relying on it for
an event.

**Print cartography (v7):** the printout is its own map, not a
screenshot. Roads collapse to classes A + F in one grey; non-road
access collapses to the state trails as solid hairlines and drops
snowmobile/hunter lines entirely — **unless** the panel's
**Winter** toggle is on (snowmobile season: snowmobile lines are
promoted on screen and survive into print). Chainage numerals
print every 5 miles instead of 10. The gap's dashes print
statically (the march is screen-only) and its sign chip prints in
full colour.

## Known data notes

Open questions in the underlying data, recorded here so they stay
visible until the chapter resolves them. Full analysis:
`../docs/segment-gap-analysis.md` (§§4, 8).

- **CHP-13 has no geometry.** The tracker section CHP-13 (3.5 mi,
  adopted, mowed in 2026) has **no line** in the official depiction
  and no usable geometry in the chapter's boundary-point file — its
  stretch there is a single point where the depicted chain ends,
  and its terminus pin sits ~2¼ mi beyond the depicted line. The
  map cannot draw CHP-13 yet; the site copy therefore shows 30 of
  the 31 stretches. Drawing it waits on the chapter (or a future
  official depiction) supplying its line.
- **WEST-9 / WEST-10 disagree between the sources** (analysis item
  D1). In the tracker, WEST-9 runs 3.50 mi with the WEST-10
  "Lake 21 Loop" inside that span; the boundary points leave only
  1.95 mi for WEST-9 — a −1.55 mi difference, the largest single
  disagreement in the join. The map draws the KMZ/official-line
  geometry and shows both lengths in the popup; the working data
  keeps both readings until the chapter settles which is right.
- **Waboose Lake Loop is tracker-only.** A 4 mi loop section in
  the tracker (branching where WEST-14 begins) with no geometry in
  the official depiction or the boundary points. Undrawn; carried
  in the working data as an annotation on the West-14 pin.

## Known next steps

- **Asset pins**: first real photo batch → `site/data/assets.geojson`.
- **Public view split**: a second page over the same site data with
  land shown as class only, featured trailheads/loops, and no
  working layers.
- **CHP-13 geometry**: if the chapter supplies the section's line
  (or the official depiction extends to cover it), add the stretch
  and retire the first known-data note above.

# The map site (v2 — chapter working view)

A single-page Leaflet map in plain HTML/CSS/JS. No build step, no
API keys, nothing to install: `index.html` + `app.js` + `style.css`.
Leaflet 1.9.4 is vendored alongside (`leaflet.js`, `leaflet.css`,
`images/`) so the site has no CDN dependency — in keeping with the
portability rule. Base-map tiles come from public tile servers
(OSM, OpenTopoMap, MnGeo, USGS, Esri), so viewing needs an internet
connection. Append `#layers=access,roads` to the URL to open with
those layers already switched on.

The side panel is deliberately short — title, the working-draft
notice, the mileage summary, the layer toggles, and the load
status. The reference material lives over the map instead: two
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
| Adopted sections | `data/stretches.geojson` | off | The chapter's adopted sections (from the adoption tracker joined onto the boundary-point overlay), drawn in amber over the official line, each with its name as a permanent tooltip floating **above** the line at mid-section. Popup: section name, status (adopted), **placeholder** adopted-by names, length measured on the official line, length in the chapter tracker, whether a crossing is recorded at each end (see Privacy for the placeholder rule). |
| Section boundaries | `data/boundaries.geojson` | with sections | **No toggle of its own** — the boundary markers ride with the Adopted sections toggle: a bar struck **across** the line at every section start/end — perpendicular to the trail's bearing there, unlabelled, positioned on the stretch geometry endpoints (never at raw KMZ pin positions — one pin sits ~3.6 km off the line). **The bar scales with zoom** (v3): ~22 px on screen at any zoom, floored at the built 140 m length, so it stays visible when zoomed out. The same file's two chapter termini are the separate layer below. |
| Chapter ends (Itasca Moraine west & east) | `data/boundaries.geojson` | on | The boundary-bar language at chapter weight: a green bar across the line at each end (~56 px on screen, floored at ~280 m), labelled "Itasca Moraine — west end" (chainage 0, at the GAP-W west end in Itasca State Park) and "Itasca Moraine — east end". Always available with the official line, independent of the sections toggle. |
| Unadopted gap (unclaimed) | `data/gaps.geojson` | on | Stretches of the depicted line no section covers, drawn bold dashed red — the recruiting layer. Currently one: GAP-W, 2.92 mi in Itasca State Park. Popup: length, land context, nearest access at each end, trails crossing it. |
| Parcels | `data/parcels.geojson` | **UI-disabled** | **Built but UI-disabled as of Nov 10, 2026, pending a later re-enable** — the layer does not appear in the toggles, its legend swatches are removed, and nothing fetches `parcels.geojson` on load or toggle. The data, build logic, popup code and canvas rendering are all retained; re-enable by flipping `enabled: false` to `enabled: true` on the parcels entry in `app.js` (LAYERS). When enabled: trail-corridor parcels (crossed + adjoining ring), off by default. Popup: parcel ID, county, land class, acres, and the **owner name + mailing address as published in the county parcel records** (public record — see Privacy). 919 of the 1,038 site parcels carry a published owner; the rest (mostly public land) show no owner row. |
| Access lines | `data/access.geojson` | off | MN DNR lines: state forest roads, state park trails/roads, OHV trails, state trails, snowmobile trails, hunter walking trails, styled by kind — drawn thin (v3, ~1 px hairlines: context, not subject). |
| Roads | `data/roads.geojson` | off | Road centerlines (5,902 MnDOT segments), drawn mid-grey at 1.75 px (v3 — the earlier 1 px #999999 styling was effectively invisible). Off by default: it is the visually busiest layer and the map opens faster without it. |
| Access points (section crossings) | `data/access-points.geojson` | **removed** | **Layer removed Nov 10, 2026 (Paul's call)** — no toggle, nothing fetches the file. The computed crossings (111 points) remain available as the gazetteer's Road/Trail crossing entries (searchable via Find), and the data file + builder stay in the repo. The §5 caution in `../docs/segment-gap-analysis.md` still applies to the crossing data wherever it appears: a crossing is a line on a map, not a drivable route. |
| Asset pins | `data/assets.geojson` | on | Photo-inventory pins. **This file does not exist yet** — until the first real photo batch runs, the layer simply shows empty. The pipeline writes `data/assets/assets.geojson` in the repo; copying it to `site/data/assets.geojson` publishes the pins. |

So the map opens (default view) with just the official line, the
unadopted gap, the two chapter-end markers, and the (still empty)
asset-pins layer — sections are one click away. Parcels are built
but UI-disabled as of Nov 10, 2026, pending a later re-enable (see
the Parcels row above).

The URL hash also accepts `#view=lat,lon,zoom` to open at a
particular view instead of fitting the whole trail (combinable with
`#layers=`, e.g. `#layers=access,roads&view=47.152,-95.195,13`).

Base maps (switcher, top right): OpenStreetMap, OpenTopoMap, the
**USGS Topo** base (The National Map, built from the 1:24,000
quadrangle series — added in v3), MnGeo's LiDAR-derived statewide
hillshade, and two aerial bases (USGS NAIP imagery; Esri World
Imagery). Cut in v3 on Paul's calls: the USGS shaded-relief base
(poor next to the 1 m LiDAR hillshade) and MnGeo's Spring Aerial
Imagery Program photography (nw14 — nothing useful over the
chapter). Providers, vintages and endpoints: `../SOURCES.md`.

**Section hover card (v3):** hovering a section (its line or its
floating name, sections layer on) raises a card with the section's
spreadsheet record — the same public-safe gazetteer card the Find
box opens (description, tracker section, NCT map refs and miles,
both lengths, placeholder adopters/sawyer, 2026 maintenance, help
requested, land, tracker comments, "What's here" contents). The
card follows the cursor and dismisses on mouse-out; a click still
opens the section's own popup.

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
field is null). Selecting a result flies the map to it, drops a
temporary highlight, and opens an info card (kind, NCT mile,
section, distance from each chapter end); a **section** result's
card shows the section's full tracker record (below) plus a
**"What's here"** contents list — every crossing, waypoint and
boundary the index places inside that section.

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

**Crosses only as placeholders:** adopter names (as in v2 —
numbered by first appearance along the chain) and **sawyer
names**, mapped through the *same* numbering, so the same person
is the same "Test adopter N" everywhere (two people appear only
as sawyers; the numbering now reaches Test adopter 50).
Maintenance notes and descriptions get the same substitution for
any person named in them. Any email/phone pattern found in
tracker text is stripped before it crosses (0 found on this
build) and the strip count is printed by the build.

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

Sizes after simplification (2026-11-10 v2 build): trail 0.07 MB,
parcels 0.49 MB, access 1.68 MB, roads 0.97 MB, stretches 0.04 MB,
gaps 0.002 MB, access points 0.03 MB, boundaries 0.007 MB,
gazetteer 0.10 MB — 3.41 MB total, down from 30.1 MB of source
data. Three tiny parcels
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

**Adopter names: placeholders only.** The working segment files in
`../data/segments/` carry the adoption tracker's personal data
(real adopter names, sawyer, maintenance notes). The site copies
never contain a real adopter name: `scripts/build_site_data.py`
assigns each distinct adopter a placeholder — "Test adopter 1",
"Test adopter 2", … in order of first appearance along the chain
(48 placeholders on the v2 build) — and emits only the placeholders
(`adopter_display`), shown in the section popup's "Adopted by"
row. Because the numbering is positional, the same person reads as
the same placeholder on every section without any name leaving the
working data. Sawyer, maintenance notes and tracker comments are
dropped outright; the full whitelist and exclusion list are
documented in the build script's header. Verified on the
2026-11-10 v2 build: zero hits for every full adopter name in the
working data anywhere under `site/`, zero email patterns, zero
phone-number patterns, and zero `@` characters in `site/data/`.

The panel carries the standing notice: *Working draft — not an
official NCTA or National Park Service map.* The map is an Itasca
Moraine **Chapter** project.

## Printing

`style.css` has basic `@media print` rules (the panel's notice and
mileage summary, then the map) because the chapter recruits with
paper maps at events. The corner buttons and their cards do not
print — open the Legend card on screen first if you need it beside
the paper map. Print renders whatever is in the current viewport —
pan/zoom first. **Untested on paper**; proof before relying on it
for an event.

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

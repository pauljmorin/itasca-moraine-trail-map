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
| Adopted sections | `data/stretches.geojson` | off | The chapter's adopted sections (from the adoption tracker joined onto the boundary-point overlay), drawn in amber over the official line, each with a permanent name label at its midpoint. Popup: section name, status (adopted), **placeholder** adopted-by names, length measured on the official line, length in the chapter tracker, whether a crossing is recorded at each end (see Privacy for the placeholder rule). |
| Section boundaries | `data/boundaries.geojson` | with sections | **No toggle of its own** — the boundary markers ride with the Adopted sections toggle: a small dark dot + boundary name at every section start/end, positioned on the stretch geometry endpoints (never at raw KMZ pin positions — one pin sits ~3.6 km off the line). The same file's two chapter termini are the separate layer below. |
| Chapter ends (Itasca Moraine west & east) | `data/boundaries.geojson` | on | Larger green markers labelled "Itasca Moraine — west end" (chainage 0, at the GAP-W west end in Itasca State Park) and "Itasca Moraine — east end". Always available with the official line, independent of the sections toggle. |
| Unadopted gap (unclaimed) | `data/gaps.geojson` | on | Stretches of the depicted line no section covers, drawn bold dashed red — the recruiting layer. Currently one: GAP-W, 2.92 mi in Itasca State Park. Popup: length, land context, nearest access at each end, trails crossing it. |
| Parcels | `data/parcels.geojson` | off | Trail-corridor parcels (crossed + adjoining ring). Popup: parcel ID, county, land class, acres, and the **owner name + mailing address as published in the county parcel records** (public record — see Privacy). 919 of the 1,038 site parcels carry a published owner; the rest (mostly public land) show no owner row. |
| Access lines | `data/access.geojson` | off | MN DNR lines: state forest roads, state park trails/roads, OHV trails, state trails, snowmobile trails, hunter walking trails, styled by kind. |
| Roads | `data/roads.geojson` | off | Road centerlines. Off by default: it is the visually busiest layer and the map opens faster without it. |
| Access points (section crossings) | `data/access-points.geojson` | off | The computed crossing points where roads and DNR trails meet each section or the gap (111 points). Popup: name, kind, which section, position (start/mid/end), crossing vs near-approach. A crossing is a line on a map, not a drivable route — see the caution in `../docs/segment-gap-analysis.md` §5 before planning a mower run from it. |
| Asset pins | `data/assets.geojson` | on | Photo-inventory pins. **This file does not exist yet** — until the first real photo batch runs, the layer simply shows empty. The pipeline writes `data/assets/assets.geojson` in the repo; copying it to `site/data/assets.geojson` publishes the pins. |

So the map opens (default view) with just the official line, the
unadopted gap, the two chapter-end markers, and the (still empty)
asset-pins layer — sections and parcels are one click away.

The URL hash also accepts `#view=lat,lon,zoom` to open at a
particular view instead of fitting the whole trail (combinable with
`#layers=`, e.g. `#layers=accesspoints&view=47.152,-95.195,13`).

Base maps (switcher, top right): OpenStreetMap and OpenTopoMap,
plus — new in v2 — two shaded-relief bases (MnGeo's LiDAR-derived
statewide hillshade; USGS The National Map shaded relief) and three
aerial bases (USGS NAIP imagery; Esri World Imagery; MnGeo's
Spring Aerial Imagery Program 2013–14 leaf-off photography of NW
Minnesota). Providers, vintages and endpoints: `../SOURCES.md`.

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
  stretch geometry endpoints plus the GAP-W west end (33 points —
  see the Layers table).

Sizes after simplification (2026-11-10 v2 build): trail 0.07 MB,
parcels 0.49 MB, access 1.68 MB, roads 0.97 MB, stretches 0.04 MB,
gaps 0.002 MB, access points 0.03 MB, boundaries 0.005 MB —
3.30 MB total, down from 30.1 MB of source data. Three tiny parcels
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

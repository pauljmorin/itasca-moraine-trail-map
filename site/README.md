# The map site (v1 — chapter working view)

A single-page Leaflet map in plain HTML/CSS/JS. No build step, no
API keys, nothing to install: `index.html` + `app.js` + `style.css`.
Leaflet 1.9.4 is vendored alongside (`leaflet.js`, `leaflet.css`,
`images/`) so the site has no CDN dependency — in keeping with the
portability rule. Base-map tiles come from the public OSM /
OpenTopoMap tile servers, so viewing needs an internet connection.
Append `#layers=access,roads` to the URL to open with those layers
already switched on.

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
| Adopted sections | `data/stretches.geojson` | on | The chapter's adopted sections (from the adoption tracker joined onto the boundary-point overlay), drawn in amber over the official line. Popup: section name, status (adopted), length measured on the official line, length in the chapter tracker, whether a crossing is recorded at each end. **No adopter names** — the site copy carries only a has-adopter boolean (see Privacy). |
| Unadopted gap (unclaimed) | `data/gaps.geojson` | on | Stretches of the depicted line no section covers, drawn bold dashed red — the recruiting layer. Currently one: GAP-W, 2.92 mi in Itasca State Park. Popup: length, land context, nearest access at each end, trails crossing it. |
| Parcels | `data/parcels.geojson` | on | Trail-corridor parcels (crossed + adjoining ring). Popup: parcel ID, county, land class, acres — **never an owner name** (see Privacy). |
| Access lines | `data/access.geojson` | off | MN DNR lines: state forest roads, state park trails/roads, OHV trails, state trails, snowmobile trails, hunter walking trails, styled by kind. |
| Roads | `data/roads.geojson` | off | Road centerlines. Off by default: it is the visually busiest layer and the map opens faster without it. |
| Access points (section crossings) | `data/access-points.geojson` | off | The computed crossing points where roads and DNR trails meet each section or the gap (111 points). Popup: name, kind, which section, position (start/mid/end), crossing vs near-approach. A crossing is a line on a map, not a drivable route — see the caution in `../docs/segment-gap-analysis.md` §5 before planning a mower run from it. |
| Asset pins | `data/assets.geojson` | on | Photo-inventory pins. **This file does not exist yet** — until the first real photo batch runs, the layer simply shows empty. The pipeline writes `data/assets/assets.geojson` in the repo; copying it to `site/data/assets.geojson` publishes the pins. |

The URL hash also accepts `#view=lat,lon,zoom` to open at a
particular view instead of fitting the whole trail (combinable with
`#layers=`, e.g. `#layers=accesspoints&view=47.152,-95.195,13`).

Base maps: OpenStreetMap, with OpenTopoMap as an alternative in the
base-layer switcher (top right).

## Site data copies

`scripts/build_site_data.py` (run from the repo root) regenerates
`site/data/` from `../data/`:

- coordinates rounded to 5 decimals (~1 m);
- geometry simplified with Douglas–Peucker in a local projection
  (tolerances: trail 10 m, parcels 15 m, access 15 m, roads 20 m,
  stretches/gaps 10 m; points are only rounded);
- attributes **whitelisted** per layer — anything not listed is
  dropped (parcels normalized across the MnGeo and Hubbard County
  schemas to parcel ID / county / land class / acres / corridor;
  segment layers use the public-view whitelist documented in the
  build script's header).

Sizes after simplification (2026-11-10 build): trail 0.07 MB,
parcels 0.40 MB, access 1.68 MB, roads 0.97 MB, stretches 0.04 MB,
gaps 0.002 MB, access points 0.03 MB — 3.21 MB total, down from
30.1 MB of source data. Three tiny parcels (of 1,041) were dropped
by polygon simplification; they remain in the source file. One
stretch (CHP-13) is absent from the site copy because its source
geometry is a single point — see Known data notes.

## Privacy (hard rule)

Parcel owner names and tax addresses exist in the source corridor
file for later chapter working-view tooling. They are **not** copied
into `site/data/` and are **never displayed** by this site — the
whitelist in `scripts/build_site_data.py` is the enforcement point,
and the parcel popup states the rule. The same applies to personal
contact fields (maintainer names/phones/emails) present in some
DNR access source attributes: stripped, not shown. Keep it that way
when editing the whitelist.

The segment layers are held to the same standard under the
chapter's publishing model (public site = public view only). The
working segment files in `../data/segments/` carry the adoption
tracker's personal data (adopter names, sawyer, maintenance notes);
the site copies keep only section name, the two lengths, a
has-adopter **boolean**, access booleans and chainage — the full
whitelist and exclusion list are documented in the header of
`scripts/build_site_data.py`. Verified on the 2026-11-10 build:
zero `@` characters, zero phone-number patterns, and zero hits for
sampled adopter/sawyer names in the three segment site copies.

The panel carries the standing notice: *Working draft — not an
official NCTA or National Park Service map.* The map is an Itasca
Moraine **Chapter** project.

## Printing

`style.css` has basic `@media print` rules (panel with legend and
notice, then the map) because the chapter recruits with paper maps
at events. Print renders whatever is in the current viewport —
pan/zoom first. **Untested on paper in v1**; proof before relying on
it for an event.

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

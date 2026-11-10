# Itasca Moraine Chapter — North Country Trail Map

An online map for the **Itasca Moraine Chapter of the North Country Trail
Association**, covering the chapter's 100+ miles of the North Country
National Scenic Trail in north-central Minnesota (the Park Rapids /
Itasca State Park / Walker corridor).

**One dataset, three views:**

1. **Chapter working view** — trail management: segments and their
   adopters, land the trail crosses (from parcel data), physical assets
   (Carsonite posts, kiosks, signage, parking, bivouac campsites),
   access routes, and condition.
2. **Volunteer view** — where my segment is, who maintains it, what has
   been done (mowing, clearing), where the access points are, and
   which segments are unadopted and need a maintainer.
3. **Public view** — promotion: featured trailheads, loops and access
   trails presented as "start here" entries for people new to the area.

## Design principles

- **Chapter is data, not structure.** Every record carries a chapter
  identifier (see `config/chapter.json`). Other chapters — statewide,
  eventually the whole trail — join by adding data, not by rebuilding.
- **Portable by design (lift-and-shift).** This repository is built to
  be transferred to the chapter later: plain open formats only
  (GeoJSON, JSON, Markdown), no database server, no paid services,
  no accounts, tokens, usernames, or machine-specific paths baked into
  files or code. All configuration lives in `config/chapter.json`.
- **Open formats, public data.** Layers are built from public sources
  (credited in `SOURCES.md`) plus the chapter's own data (adopter
  boundaries, photo inventory).
- **Privacy rules (hard rules, see DESIGN.md).** Landowner names from
  parcel data appear **only** in the chapter working view — never in
  the public view, which shows land class only. Private access roads
  are drawn but always labeled as private / informal. The map is a
  **chapter** project: it is never presented as the North Country
  Trail Association nationally or as the National Park Service.
- **The official line rules.** Segments are stretches of the official
  trail depiction published by NCTA for NPS; when that line changes
  (reroutes), we re-pull and diff rather than hand-editing our copy.

## Data layers

| Layer | Contents | Location |
|---|---|---|
| Official line | The official NCT depiction, clipped to the chapter working extent | `data/segments/official-line-chapter-extent.geojson` |
| Segments | Chapter management segments (stretches of the official line) with adopter and status; unadopted gaps shown as segments in their own right | `data/segments/` (KMZ overlay pending) |
| Assets | Photo-derived inventory points: type, rough condition, photo reference | `data/assets/` (pipeline built and fixture-proven 2026-11-10; awaiting first real batch) |
| Parcels | Corridor clip of Minnesota county parcels (trail-crossing parcels plus the adjoining ring). **Working view only** | `data/parcels/parcels-corridor.geojson` |
| Access | Forest roads, side-by-side/UTV trails, other hiking trails, and labeled private roads; plus computed practical access points per segment | `data/access/access-lines.geojson`, `data/access/roads.geojson` (access points still to be computed) |

## Repository layout

- `config/` — all configuration (`chapter.json`); nothing configurable lives anywhere else
- `data/` — the dataset, one folder per layer
- `photos-inbox/` — drop point for inventory photos awaiting processing
- `scripts/` — pull/transform scripts (public sources, no credentials)
- `site/` — the map site: v1 built 2026-11-10 (see `site/README.md`)
- `docs/` — supporting documents
- `DESIGN.md` — the design record: data model, privacy/branding rules, photo pipeline, open decisions
- `SOURCES.md` — every external dataset: URL, owner, attribution

## Status

- 2026-11-10 — Project scaffolded. Official line pulled from the NCTA
  public feature service: 4,102 features nationally, 84 retained in
  the chapter working extent, 117.74 miles of line inside the extent
  (79 off-road features, 5 on-road; 40 features tagged to this chapter
  and 44 to the neighbouring chapter the extent overlaps).
- 2026-11-10 — Parcel corridor and access layers pulled. The trail
  crosses four counties (Hubbard, Cass, Becker, Clearwater);
  Hubbard is not in the state parcel compilation, so its parcels
  came from the county's own open-data service (see
  `data/parcels/county-coverage.md`). Corridor file: 1,041 parcels
  (255 crossed, 786 adjoining). Access: 3,670 DNR forest-road and
  recreation-trail lines plus 5,902 road centerlines for the extent.
- 2026-11-10 — Photo pipeline built and proven on synthetic
  fixtures: `scripts/photo_pipeline.py` (`check` = pre-flight GPS
  protocol tool, stdlib only; `build` = assets GeoJSON + 1600 px
  web derivatives + flags report, 5 MB output refusal enforced).
  Volunteer protocol card at `docs/photo-protocol.md`.
- 2026-11-10 — Map site v1 built (`site/`): single-page Leaflet
  working view over simplified site copies of the data (29.0 MB of
  source → 3.13 MB in `site/data/`, attributes whitelisted so parcel
  owner names never reach the site). Trail, parcels, access, roads
  and (empty until the first batch) asset-pin layers with toggles,
  legend, source credits and the not-an-official-map notice.
  Render-proofed with headless-browser screenshots
  (docs/proof-2026-11-10/) — panel, legend and all vector layers
  confirmed; base tiles could not load inside the sandboxed test
  browser (outbound fetches blocked there), so tile rendering is
  verified only by configuration, not by screenshot.
- Next: overlay the chapter's adopter-boundary KMZ onto the official
  line; report segment fit and the unadopted gaps between segments.

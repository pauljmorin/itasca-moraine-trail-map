# Corridor motorized swap + Nelson Lake loop + SHT layer — 2026-11-16

Three wiring jobs in `site/app.js`, done in order. No deploy, no commit,
no push. The basemap work Paul asked for the same morning (Mapbox
Outdoors, Waymarked Trails) was done separately by the coordinator and
is NOT touched here — no basemap def, `BASES` entry, or `MAPBOX_TOKEN`
was edited. No Border Route Trail layer: the BRT shares tread with the
NCT and is already drawn as the NCT itself.

## Job 1 — Motorized: chapter extent → statewide corridor + dirt bike

### What changed

The motorized layers were wired in the morning on chapter-extent pulls
that stop at lon -95.6, just east of Frazee — they missed the whole
western leg of the Minnesota NCT. They now read the statewide-corridor
pulls (`scripts/pull-motorized-mn-corridor.py`, 2-mile buffer around the
full MN NCT line, pulled Nov 16):

| Layer | File (`site/data/`) | Features | GIS miles | Systems |
|---|---|---|---|---|
| ATV trails | `motorized-atv.geojson` | 769 (was 1,238) | 184.38 (was 408.02) | 16 |
| Dirt bike trails (NEW) | `motorized-ohm.geojson` | 802 | 190.21 | 14 |
| Snowmobile trails | `motorized-snow.geojson` | 36 (was 17) | 587.95 (was 895.72) | 29 |

Corridor miles are LOWER than chapter-box miles because the corridor is
a narrow ribbon around the trail while the chapter box is a big
rectangle — both numbers are correct for their definitions. The
corridor files were copied from `data/motorized/` into `site/data/`
(the chapter-extent site copies are replaced, not kept alongside).

### Viewer — `site/app.js`

- New def `id: "ohm"`, label "Dirt bike trails" (line 4473), group
  "Other trails", OFF by default, file `data/motorized-ohm.geojson`.
  Magenta `#c51b8a` — near the ATV purple `#762a83` but clearly
  distinct at a glance. Popup `ohmPopup` mirrors the ATV popup
  (Segment, Vehicles, Surface, Funding, "This segment: X mi (DNR
  service)", DNR trail page link).
- `atv` def (line 4446): comment + title updated to the corridor
  numbers (769 / 184 mi / 16 systems, listed). `snow` def (line
  4501): same (36 / 588 mi / 29 systems). Files unchanged in name,
  so no other reference needed updating.
- `atvPopup` / `snowPopup` source notes reworded from "clipped to
  the chapter working extent" to "within 2 miles of the Minnesota
  NCT line". The snow popup keeps "Published miles" — see below.
- Header comment above `atvVehicles` rewritten: corridor scope, the
  ATV/OHM split rule (ATV when `atv_class_1`/`atv_class_2` is 'X',
  OHM when `off_highway_motorcycle` is 'X'; a trail allowing both
  appears in both files), and the known gap that Prospectors and the
  David Dill – Taconite State Trail now appear in the corridor files
  with no shared-use note (the buildout's notes attached to the
  chapter extent, where those systems did not fall).
- Draw order: `"atv", "ohm", "snow"` (line 6474), between the sheet
  outlines and the Minnesota line, under the NCT tread. Comment
  updated.
- Legend: new row `Dirt bike trail (DNR)` in magenta (line 6576).

### Attribution — `site/data-sources.html`

- "ATV trails" rewritten for the corridor (769 / 184 mi / 16 systems,
  listed). New "Dirt bike trails" section (802 / 190 mi / 14 systems;
  the system list is stated as the ATV list minus Alborn-Pengilly,
  Len Hardy Memorial Trail and Soo Line North: Cass, plus Martineau
  Recreational Trails — verified by set difference on the files).
- "Snowmobile trails" rewritten (36 / 588 mi / 29 systems, listed).
  Source lines unchanged (same FeatureServer links, Nov 16 pull).

### `miles` field — checked, two different behaviours

- **ATV / OHM: the field is the DNR segment length.** Spot-checked
  against geometry measured in UTM 15N: OHM 3/3 exact, ATV 2/3
  exact. Full sweep: 29 of 769 ATV features (3.8%) and 31 of 802 OHM
  features (3.9%) differ from the drawn length by >0.05 mi — all
  cases where a segment crosses the corridor boundary, so the drawn
  piece is the in-corridor portion of a longer DNR segment (worst
  case: David Dill – Taconite, field 4.000 mi, drawn 0.302 mi). The
  popup's "This segment" label follows the buildout convention and
  shows the DNR field; the boundary effect is recorded here, not
  silently "fixed" with a derived field.
- **Snow: the field is the system published total.** Corridor sums:
  field total 3,254.3 mi vs drawn 587.95 mi. The "Published miles"
  label is correct and necessary — unchanged.

## Job 2 — Nelson Lake loop into the Chapter loops layer

Source file of record `data/loops/nelson-lake-loop.geojson` (4 features,
staged earlier the same day; see the Nelson section appended to
`docs/chapter-loops-layer-2026-11-16.md` for the full hunt):

- Which lake: the Nelson Lake Trail in Paul Bunyan State Forest near
  Laporte — its NCT junction (-94.84658, 47.15307) sits 3.2 m from the
  West-9 / West-10 boundary point, exactly as Paul described it.
- Appended to `site/data/chapter-loops.geojson` — now 6 features.
  The 3 Nelson Lake Trail ways each carry `length_mi: 1.25` (the loop
  total across the three ways), `source: OpenStreetMap (ODbL)`,
  `osm_way_id`, `length_note`, `source_note`, and the gap note, so the
  popup shows the loop length whichever segment is clicked (same
  pattern as Waboose). The Lake Twentyone Trail connector carries
  `length_mi: 1.01`. Total assembled system 2.26 mi vs published
  2.4 mi.
- Gap: ~140 m on the north-east side across the Gulch Lake Campground
  area (plus 47 m from the Lake Twentyone Trail's end to the same
  junction) — left open, no tread invented.
- Viewer: `loops` def comment + title updated to three loops; legend
  row now "Chapter loop — Waboose Lake / Lake Erin / Nelson Lake";
  data-sources "Chapter loops" section rewritten (three loops + the
  connector + the 140 m gap). No draw-order or style change — the
  teal `#0f766e` style and the over-adopted-sections slot already
  cover the new features.

## Job 3 — Superior Hiking Trail layer

### The live pull FAILED — fallback used, disclosed here

The DNR enterprise host was down at wiring time: the
`trans_state_park_trails_roads` FeatureServer returned HTTP 502
(Bad Gateway, Azure Application Gateway) three times, and a retry
after Jobs 1–2 returned HTTP 504 (Gateway Time-out). The OHV
control endpoint 502'd/504'd the same way, so this was the whole
host, not the one service. **No live pull was possible.**

The SHT geometry instead comes from
`/tmp/nct-trails/dnr_park_trails-0.geojson` — the intersecting-trails
inventory's raw pull of the SAME service, Nov 16 13:48 UTC, made with
`requests` from the exact service URL
(`.../us_mn_state_dnr/trans_state_park_trails_roads/FeatureServer`,
layer 0, `outFields: *`, statewide NCT envelope). It was verified
independently before use:

- 1,996 features — exactly the service's count per the inventory doc.
- SHT filter (`trail_name == 'Superior Hiking Trail'`): 287 features.
- `lengthmile` field sum 145.94 mi = GIS miles measured from the
  geometry in UTM 15N (145.94 mi) — exact agreement.
- Northern terminus touch: the line meets the MN NCT line at 0 m,
  at (-89.93524, 47.98833) — the inventory's northern terminus,
  270° Overlook near Grand Portage.
- Southernmost point (-92.27265, 46.66602) sits 7,548 m from the NCT
  line, while the trail's true southern terminus is 936 m away
  (inventory) — the DNR file does NOT include the southern terminus
  approach (Jay Cooke).

**Re-run `scripts/pull-sht.py` against the live service when it
recovers and diff the output before replacing the file.** The script
is written for the live two-pass pull; the Nov 16 file's metadata
records this provenance in full.

### Live re-run — DONE Nov 16 08:25 CST (coordinator)

The service had recovered by 08:25 the same morning. The live re-run
succeeded: 13,987 features in the envelope, **553 SHT features,
207.56 GIS miles** (measured 207.29 mi from geometry — agreement
within 0.3 mi). All 287 features from the fallback file are contained
in the live pull, with no duplicate objectids — the inventory's raw
file was evidently a partial pull, and the live file supersedes it.
`data/sht/sht.geojson` and `site/data/superior-hiking-trail.geojson`
are now the live pull (7,588,244 B). The SHT def title, popup,
legend, data-sources section, and the pull script's header were all
updated to the live numbers the same morning; the fallback figures
below are superseded.

### Coverage — partial, stated everywhere it appears

The DNR park file carries 207.56 GIS miles — the portions inside
Minnesota state parks, about 67% of the ~310 mi published trail.
The popup, the def title, the legend row, and the data-sources
section all say so. The gaps were NOT filled from OSM or any other
source. One source segment (objectid 383, 1.008 mi) runs ~1.2 km
north past the northern terminus; it is left in the file as the
service carries it.

### What changed

- New files: `data/sht/sht.geojson` (source of record, with
  metadata incl. the pull provenance above) and the viewer copy
  `site/data/superior-hiking-trail.geojson` — 287 features,
  5,297,164 bytes each.
- New script: `scripts/pull-sht.py` (live-service pull, reusable).
- New def `id: "sht"`, label "Superior Hiking Trail" (line 4537),
  group "Other trails", OFF by default, file
  `data/superior-hiking-trail.geojson`. Blue `#2563eb`, distinct
  from the snow icy blue, ATV purple, and OHM magenta. Popup
  `shtPopup` shows the segment length (`lengthmile`, DNR service)
  and the coverage caveat in full; the DNR service's use/surface
  fields are blank, so no use rows are shown.
- Draw order: `"sht"` added after `"snow"` (line 6474), under the
  NCT tread. Legend row: "Superior Hiking Trail (DNR, state-park
  portions)".
- Attribution: new "Superior Hiking Trail" section in
  `site/data-sources.html`, including the partial-coverage caveat,
  the northern-terminus-only meeting point, the no-separate-BRT-layer
  note, and the same-day-inventory-pull provenance.
- No Border Route Trail layer (see header).

## Verification (all static, no live browser)

- `node --check site/app.js` — PASS.
- Defs by grep: `loops` 4406, `atv` 4446, `ohm` 4473, `snow` 4501,
  `sht` 4537; each with its `file:` line (chapter-loops 4411,
  motorized-atv 4449, motorized-ohm 4477, motorized-snow 4504,
  superior-hiking-trail 4541). All four motorized/SHT defs carry
  `group: "Other trails"` + `onByDefault: false`.
- Draw order (line 6474): `"roads", "nctasheets", "atv", "ohm",
  "snow", "sht", "trail-minnesota", ...`.
- Legend rows: loops (6537), ATV/OHM/snow/SHT (6575–6578).
- Popup functions defined and wired: `atvPopup` 4153, `ohmPopup`
  4173, `snowPopup` 4195, `shtPopup` 4215; `ohmPopup(f)` and
  `shtPopup(f)` referenced in their defs' `onEachFeature`.
- Attribution sections in `site/data-sources.html`: "Dirt bike
  trails" (line 159), "Superior Hiking Trail" (line 167); ATV /
  snow / Chapter loops sections rewritten.
- `python3 json.load` on all five site/data files — valid:
  motorized-atv 769 feats / 1,353,653 B; motorized-ohm 802 /
  1,529,491 B; motorized-snow 36 / 1,579,572 B;
  superior-hiking-trail 553 / 7,588,244 B; chapter-loops 6 /
  21,895 B.
- Loops popup fields: all 6 chapter-loops features carry `name`,
  `length_mi`, `source`, `gap_note` — the three fields the popup
  reads. SHT `lengthmile` present on all 553 features.
- Stale wording sweep: the only remaining "chapter working extent"
  in `site/app.js` is line 4120, the historical sentence explaining
  the old files — intentional.
- `git status`: `M site/app.js`, `M site/data-sources.html`,
  `?? data/sht/`, `?? scripts/pull-sht.py`,
  `?? site/data/motorized-ohm.geojson`,
  `?? site/data/superior-hiking-trail.geojson` (plus pre-existing
  modifications from earlier work, untouched here). No commit, no
  push, no deploy.

## Still owed

1. **Live-browser check** of all four new/changed layers (Other
   trails group order; ATV purple / OHM magenta / snow icy blue /
   SHT blue drawing under the NCT tread; ATV/OHM/snow/SHT popups;
   Nelson Lake loop teal + popup; toggles off/on; `#layers=` hash)
   and the MN-trail end-to-end visibility check — then deploy.
2. **SHT live re-pull: DONE** — Nov 16 08:25 CST, live pull
   superseded the fallback file (553 features, 207.56 mi).
3. **Full SHT (OSM)**: if Paul wants the whole ~310 mi rather than
   the 208 mi of state-park portions, the remainder would come from
   OSM — a separate job, not started.
4. **GeoPDF export**: `site/export.js` and
   `scripts/export_geopdf.py` carry their own layer lists; none has
   `loops`, `atv`, `ohm`, `snow`, or `sht` entries yet, so none of
   these layers appear in downloaded GeoPDFs or segment books until
   those lists gain entries.
5. **SOURCES.md**: the working source register still describes the
   chapter-extent motorized pull; it needs a refresh for the
   corridor files, the OHM split, and the SHT service (not done in
   this pass).

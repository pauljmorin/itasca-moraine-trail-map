# Cartography notes — corridor crop + full styling pass

Cartography spec, 2026-11-10. Paul's commission, verbatim: *"the
access lines and roads go too far from the trail. Can you talk to a
cartographer about how to limit (crop) this. Also talk to the
cartographer about how best to make all of the lines, annotation
and anything else that we are drawing on the map — this should be
actionable but really cool."*

Companion to `DESIGN-REVIEW.md` / `UX-REVIEW.md` in this folder and
`design-notes-2026-11-10-header.md`. Palette discipline as in the
header notes: every colour below is an existing token in
`site/app.js` (`COLORS`, `ACCESS_STYLES`) or `site/style.css`
(`:root`), except the three explicitly argued changes in §2.9.
Everything is implementable in the current stack: pure-stdlib
Python in `scripts/build_site_data.py`, plain Leaflet JS/CSS in
`site/`. No new services, no build step.

Zoom bands used throughout (the map opens at z10):

| Band | Zooms | Name | The reader is… |
|---|---|---|---|
| Z1 | ≤ 10 | chapter | seeing the whole chapter at once |
| Z2 | 11–12 | section | reading a stretch and its neighbours |
| Z3 | 13–14 | work | planning a crew day: access, parcels, assets |
| Z4 | ≥ 15 | detail | standing (mentally) on the tread |

---

## 0. What the data actually looks like (measured, 2026-11-10)

The crop parameters in Part 1 come from measuring the project's own
files, not from intuition. Method note so the numbers can be
reproduced: trail lines rasterised at 100 m cells (samples every
50 m), buffer masks by dilation, every access/road feature sampled
every 100 m along its length; counts below are features whose
geometry touches the buffer at all ("any-touch"). Treat counts as
±3% (raster method) — more than accurate enough to choose buffers.

**The overshoot Paul saw is real, and it has two different causes:**

- **Roads (5,902 segments)** fill the working extent almost
  exactly (bbox lon −95.615…−94.285, lat 46.672…47.372 — the
  extent box itself). It is a complete road grid for ~7,100 km²
  drawn around a ~190 km line. Any corridor helps enormously.
- **Non-road access (3,670 features)** is worse: its bbox is
  lon −96.067…−93.775, lat 46.325…47.926 — *far outside the working
  extent*. The pull retained any feature that touches the extent
  but kept its full geometry (the same first-pass method
  `DESIGN.md` records for the official line), and the DNR services
  contain region-spanning features (the longest single access
  feature spans 94.9 km). So access lines don't just fill the box,
  they leak out of it in long strokes. Median feature span is only
  0.2 km — the layer is thousands of short pieces plus a few
  monsters.

**Corridor retention, measured** (reference = both drawn lines,
ITM + LLC; features touching the corridor):

| Buffer | Non-road access (of 3,670) | Roads (of 5,902) |
|---|---|---|
| ±0.4 km | 258 | 59 |
| ±0.8 km | 357 | 111 |
| ±1.6 km | 562 | 311 |
| ±3.2 km | 841 | 697 |

Reference-line choice matters for roads, barely for access:
against ITM alone the 3.2 km road count falls to 336 (the LLC line
runs through the roaded south-west of the extent); access moves
only 841 → 819.

**Layer composition, for the rulings that follow:**

- Non-road access by kind: state park trail/road **2,112**,
  OHV **1,238**, state forest road **265**, state trail 28,
  snowmobile 17, hunter walking 10. Two kinds are 91% of the layer.
- Roads source carries `route_sys` (900 + 452 + 280 + … segments
  coded) and names (`CO RD 1`, …) but `cartoclass` is null on all
  5,902 — do not build a hierarchy on `cartoclass`.
  `build_site_data.py`'s `map_road()` currently keeps **only the
  name**; the class fields exist in the source and are thrown away.

---

## Part 1 — The crop

### C1. Primary ruling: clip to a corridor, per layer, at the vertex

One method for both layers, two widths. In
`scripts/build_site_data.py`, after simplification (crop *after*
Douglas–Peucker, so the tolerance budget isn't spent on geometry
that will be discarded — and re-run a light 5 m DP pass after
clipping to remove clip-induced collinear points):

- **Non-road access: corridor half-width 800 m** around the
  reference lines.
- **Roads: corridor half-width 1.6 km** around the reference lines.

Widths are jobs, not symmetry. An access line's job is *the last
bit on foot or UTV between a vehicle and the tread*: 800 m is a
~10-minute walk, and anything farther is not how a crew reaches
that section (the per-section practical access is already computed
in the segment overlay and lives in the inspector/gazetteer — the
lines are context for it, not the record of it). A road's job is
*how do I drive there*: the corridor must be wide enough that a
driver can see the road they are on, the next junction, and the
road the trailhead is actually on — 1.6 km does that at Z2–Z3
without reconstituting the county grid. The two widths also keep
the visual grammar honest: the tighter band reads as "trail
country," the wider, fainter band as "driving country."

**Reference lines = both drawn lines (ITM + LLC).** Crop to what
is drawn. Cropping to ITM only would amputate access along the
purple line Paul sees on the same map, for a saving of ~20 access
features; the road saving is larger (311 vs ~120 at 1.6 km) but
the LLC corridor is context he asked to see. If a future build
adds more neighbour chapters, the corridor follows the drawn set
automatically — the rule is "corridor follows the depiction."

### C2. Clip at vertices, with interpolated crossings — never whole-feature, never stubs-by-accident

For each polyline, walk its vertices in the projected plane
(`build_site_data.py` already projects equirectangular about
47°N), keep the maximal runs inside the corridor, and insert the
exact boundary-crossing point at each entry/exit (linear
interpolation on the segment that crosses the buffer edge — the
distance-to-line function needed is `point_line_dist_m`'s sibling:
distance from a vertex to the *nearest trail segment*, see C6).
Drop kept runs shorter than **25 m** (clip confetti at corridor
edges). Emit `cut: true` on any feature that was clipped, so the
renderer can feather it (§2.10).

Why not the alternatives:

- *Keep-whole-if-any-part-inside* (the parcels-pull pattern):
  correct for polygons you must not break, wrong here — with a
  94.9 km feature in the set, one touch would re-import the whole
  problem. Whole-feature retention is granted only by the explicit
  connector exception, C4.
- *Hard clip with no crossings inserted*: cuts land between
  vertices, which on 15–20 m-simplified geometry can sit ~100 m
  inside or outside the true corridor edge — visible as ragged,
  inconsistent band edges where lines end mid-field at slightly
  different distances. Interpolated crossings make the corridor
  edge a *designed* line: every cut happens at exactly 800 m /
  1.6 km, so the band edge reads as intention, not noise.

### C3. Finish the block (roads) and reach the junction (access)

A corridor cut that lands mid-segment looks like a data error. Two
cheap repairs, both operating on the *original* polyline after C2:

- **Roads — finish the block:** if a clip endpoint sits ≤ 250 m
  (along the original line) from that segment's own end vertex,
  extend the kept run to the end vertex. Road source segments are
  junction-to-junction pieces (median span 0.3 km), so most cuts
  resolve to a real junction or road end for ≤ 250 m of overshoot.
- **Access — junction stubs:** if a clip endpoint does *not* land
  on another retained line, extend along the original polyline up
  to **150 m**; keep the extension only if it reaches an
  intersection (segment crossing or shared vertex within 10 m)
  with another retained access feature, a retained road, or the
  trail. Otherwise keep the C2 cut. This preserves the one thing
  that makes an access network legible — that lines *meet* — while
  adding at most 150 m of overshoot per dangling end.

True network snipping (build the full junction graph, trim every
branch at its last in-corridor junction) is the theoretically
clean version of C3 and is **not** recommended: the source
segments are not reliably noded (shared junctions appear as
near-miss coordinates, not shared vertices), so a graph build
needs a snapping pass with its own failure modes. C3 gets ~90% of
the visual benefit for ~10% of the machinery. Revisit only if the
chapter starts editing access data by hand.

### C4. The connector exception (long forest roads)

The honest objection to any buffer: *the* practical access to a
remote section is sometimes one long forest road that crosses the
trail once and wanders for kilometres. Corridor logic handles it
better than it first appears — the road is retained where it
matters (at the crossing, ±800 m), and the gazetteer's per-section
access entries already say "via Forest Road N" in words. But a
crossing road that visibly dies 800 m each side of the tread,
while the map elsewhere implies it is *the* way in, undersells it.
Ruling:

- An access feature that **crosses the official line** (segment
  intersection test — `geo_util.seg_seg_intersect` already exists)
  and is **≤ 3 km long in total** is retained **whole**.
- A crossing feature **> 3 km** is clipped per C2, then each kept
  run containing the crossing is extended along the original line
  until it meets another retained line or reaches **+1.5 km** past
  the corridor edge, whichever comes first.
- Non-crossing features get no exception, however long or
  plausible: a road that never comes within 800 m of the tread is
  not this section's access, and the ones that run parallel inside
  the corridor are already kept by C2 where they are parallel.

This is also where **state forest roads** matter most — see the
naming ruling, §2.9, which moves them to the Roads layer; the C4
test should run on them *before* the move, in the access build,
so they carry their exception with them (emit `connector: true`).

### C5. Itasca State Park is a place, not a density problem

2,112 of the 3,670 access features are the state-park kind, and
their source bbox spans half the state (the DNR park dataset is
not park-bounded per feature). The corridor fixes the geography
(the park's trail/road web near the NCT survives; the far-flung
pieces don't), but inside the park the network is *legitimately*
dense — it is a trail system in its own right, and it is also the
gap's home turf, where the map's recruiting story lives. So the
park kind is handled by **zoom, not by a tighter crop**: same
800 m corridor, but the kind renders only at Z3+ (§2.9). At Z1–Z2
the west end shows the trail, the gap, and the park's *name* on
the base — which is the correct chapter-scale statement. Do not
thin the park network by length or name filters; its density at
Z3 is information ("you can wander here"), and at Z3 the reader
has asked for it.

### C6. Implementation notes for the builder (stdlib-honest)

`build_site_data.py` is pure stdlib and must stay that way. The
corridor test needs, per candidate vertex, the distance to the
nearest trail segment:

- Build a uniform grid index over trail segments: cell 500 m in
  projected metres, each segment registered in every cell its
  bbox touches (the parcels pull already uses this pattern —
  `seg_index` / bbox prefilter — reuse its shape via
  `scripts/geo_util.py`, which has `point_seg_dist_km` and
  `seg_seg_dist_km` ready).
- Per vertex: search the containing cell, then expanding rings,
  until the nearest found segment is closer than the current
  ring's minimum possible distance. Trail = ~18.8k segments;
  candidate features after an extent+bbox prefilter ≈ 45k segments
  for roads+access combined. Expect a one-off build cost of
  ~1–3 minutes in pure Python. That is acceptable for a build
  script run on data refreshes, not per page load — the crop is a
  **build-time** operation; nothing in `site/` changes shape
  except smaller files and two new properties (`cut`,
  `connector`).
- Vertex spacing caveat: source lines carry ~185k segments
  (access) — dense enough that testing vertices only (plus the C2
  interpolation) misjudges a crossing by at most a few metres.
  Do **not** test only feature bboxes or first vertices: that was
  the failure mode of measuring by vertices on features whose
  endpoints sit far from the trail while the line's middle crosses
  it. Sample along segments every ≤ 100 m wherever a segment is
  longer than that.
- The working data under `data/` is **not** cropped — the corridor
  is a site-build view, exactly like the parcels corridor is a
  pull view. Chapter takeover keeps full data; the map keeps its
  manners.

### C7. Expected effect (measured basis, builder should verify and print)

| Layer | Today | After C1–C4 (est.) |
|---|---|---|
| Non-road access | 3,670 features, 1.68 MB | ~350–380 features, ~0.25–0.35 MB |
| Roads | 5,902 features, 0.97 MB | ~300–340 features, ~0.10–0.15 MB |

(357 access features touch the 800 m corridor, 243 of them fully
inside; 311 roads touch 1.6 km, 240 fully inside; C3/C4 extensions
add a few percent of geometry back. `build_site_data.py` already
prints per-layer feature/byte counts — the build report for the
first cropped build should be pasted into the commit message, and
any result outside ±20% of this table wants a second look before
it ships.)

Zoom revelation (Part 2) is a **complement, never a substitute**:
an uncropped layer hidden below z13 still draws its full extent
the moment a crew member zooms in, which is exactly when they are
looking at *their* section and least need the next county's grid.

---

## Part 2 — Everything we draw

Framework first. Three disciplines govern every element below:

1. **One hero per band.** Z1: trail + gap. Z2: + sections, ticks,
   state trail. Z3: + access, roads (minor), parcels, places.
   Z4: + mile labels, hunter trails, asset detail. If an element
   can't name its band, it doesn't render outside it.
2. **The official line dominates by casing, not by shouting.**
   Everything contextual is thinner, lighter, or dashed-er than
   the line it serves (extends DESIGN D1/D2).
3. **Draw order is the spec** (§2.12) — on a shared canvas,
   stacking *is* styling.

### 2.1 Official trail line — Itasca Moraine (ITM)

Keep `#1a9850`. Weight becomes zoom-stepped (restyle on `zoomend`
alongside the existing tick/label passes): **3.5 at Z1, 4 at
Z2–Z3, 5 at Z4**. Casing per §3, move S4. On-road pieces: replace
dash `"6 6"` with **`"2 7"`, `lineCap: "round"`** — a dotted line
that reads as "the tread follows this road" rather than a
competing dashed route; weight 3 in the same green. Off-road
stays solid. Opacity 0.9 stands.

### 2.2 Laurentian Lakes line (LLC)

Demotion completed: `#7e6a9e`, weight **2.5** (from 3), opacity
**0.7** (from 0.8), **no casing at any zoom** — casing is the
hero's privilege, and giving the neighbour a halo quietly promotes
it. On-road LLC takes the same dotted treatment as ITM on-road.
Its name appears only in the legend and popups, never as a
map-face label: the face belongs to the chapter.

### 2.3 Adopted sections (amber overlay)

`#e08214`, opacity 1, stands (D1's fix was right). Weight **6 at
Z1–Z3, 5 at Z4** — at detail zooms the amber should sit *on* the
tread, not blanket it, so the underlying line's on/off-road
character stays legible at the ends of each section. Casing per
S4. Hover `#b45f06` / weight 8 stands. The amber must never be
mistaken for a separate route: it has no labels of its own beyond
the section names (§2.7) and no termini — ticks crossing it
(§2.5) are what tell the reader it is a *subdivision* of the line.

### 2.4 The unadopted gap

Keep the construction (pale `#b2182b` casing w11/0.4 + `#d7301f`
core w5, dash `"14 8"`) and add the signature treatment in S3 —
the gap is the only element on the map allowed to *move*. Its
label gets the sign treatment at Z2+ (S3). Nothing else on the
map is red; §2.9 removes the one collision (OHV red).

### 2.5 Boundary tick bars

The zoom-scaled tick machinery (22 px target, 140 m floor,
1.6 km cap) is the best piece of cartography in the current build
— keep it entire. Two refinements:

- **Fade with band:** core opacity 1.0 at Z2+, **0.55 at Z1** —
  at chapter scale 31 slate bars are texture, not information;
  the two termini (§2.6) carry the delineation story there.
  Section ticks do not render at z ≤ 8 at all (below the opening
  zoom's working range; the termini remain).
- Ticks keep priority over labels in collisions (§2.7): a name
  that would touch a tick hides before a tick moves. (This is a
  *label* rule, applied in the label pass — the v4 history of a
  tick-proximity rule hiding 30/30 names at z10 was a label-pass
  bug, not a tick rule; the implementation must test against the
  *placed* tick boxes at the current zoom, not a fixed radius.)

### 2.6 Chapter termini

Unchanged in construction (56 px target, 280 m floor, 4.2 km cap,
chapter green w4.5, white casing w8). Terminus labels never hide,
never shrink below 10 px (current behaviour) — they are the map's
only two always-on annotations besides the gap label, and that
scarcity is what makes them read as chapter furniture.

### 2.7 Section-name labels

Keep: permanent tooltips, mid-section anchor, above/beside by
bearing (`sectionLabelPlacement`), `--adopted-deep` on the paper
halo, imagery flip to near-white on dark halo, font steps
11/10/9/8 px, longest-first collision pass, ≥ 2 mi rule at z ≤ 9,
no hiding at z ≥ 12. Changes:

- **One collision pass for all face text.** Today the pass knows
  only section names. Extend `layoutSectionLabels` into a single
  annotation pass with priority classes — **terminus (never
  hides) > gap label > section name > state mile label (§Part 3)**
  — each class reserving its estimated box (the existing +6 px
  slop method) before the next class places. This is the
  discipline that lets Part 3 exist without a label war.
- Side labels (`direction: "right"`) get `offset [12, 0]` at Z3+
  (from 10) — at work zooms the name should clear the wider line
  stack (casing + amber + tick).

### 2.8 Parcels (currently UI-disabled — style for their return)

When the flag flips back: render **Z3+ only** (1,038 polygons at
Z1–Z2 are mush and the layer's questions — whose land, which
section — are Z3 questions). Crossed: fill `#fdbb84` at **0.32**
(from 0.45), outline `#b35806` w1. Adjoining: fill `#e7e1c3` at
**0.12**, outline `#a89a5b` w0.5 **dashed `"3 3"`** — the ring
should read as *neighbourhood*, not territory; a dashed boundary
is the classic "adjacent, not subject" signal. No parcel labels
on the face at any zoom; owner detail stays in the popup, which
is where a name belongs. Draw order: absolute back (§2.12).

### 2.9 Non-road access (renamed — and one kind moves out)

**Naming ruling:** the layer is now **"Non-road access"** (Paul's
rename; toggle + legend already updated by the coordinator). Its
legend group still contains **State forest road** — a road, under
a "non-road" label, and the contradiction will trip the first
chapter member who reads the legend carefully. **Ruling: state
forest road moves to the Roads layer** as its own class (§2.10,
class F), keeping its DNR brown and its name/popups. Its job is
driving, its geometry is a road, and C4's connector test runs on
it in the access build before the move. Non-road access becomes
truthfully non-road: park trails, OHV, state trails, snowmobile,
hunter walking.

Per-kind styling (all hairlines; weights at Z3, −0.25 at Z2 where
shown):

| Kind | Colour | Weight | Dash | Bands | Note |
|---|---|---|---|---|---|
| State park trail/road | `#35978f` | 0.9 | solid | Z3+ only | C5: density is zoom's problem |
| OHV / ATV-UTV | `#a63603` | 1 | `"6 3 1.5 3"` | Z2+ | **colour change argued below** |
| State trail | `#2c7fb8` | 1.25 | solid | Z1+ | the only access kind allowed at chapter scale — state trails are peer routes, not spurs |
| Snowmobile | `#8856a7` | 0.75 | `"2 5"` | Z2+ | dotted = seasonal; see print/winter variant, S5 |
| Hunter walking | `#6e8b67` | 0.75 | `"8 4"` | Z3+ only | **colour change argued below**; 10 features, hyper-local |

Two colour arguments (the only palette changes in this spec):

- **OHV `#d7301f` → `#a63603`.** The current OHV red *is* the gap
  red. On a map whose entire recruiting story is "red = the one
  unclaimed stretch," a second red network — 1,238 features of it —
  is a genuine semantic collision, the worst in the current build.
  `#a63603` is the deep burnt orange of the same sequential family
  as the adopted amber `#e08214`, reads as "motorised, earthy,
  caution" and cannot be confused with the gap at any zoom. The
  dash-dot pattern (`"6 3 1.5 3"`, the conventional motorised/
  mixed-use signature) makes the kind identifiable even in B/W
  print, where the two oranges converge.
- **Hunter walking `#31a354` → `#6e8b67`.** `#31a354` is a
  near-twin of the trail green at hairline weight; a dashed green
  hairline beside a solid green line reads as a trail variant.
  The sage `#6e8b67` keeps the "footpath through cover" family
  resemblance while dropping saturation enough to sit clearly in
  the context tier, and the long dash + Z3-only gate do the rest.

Opacity for the layer: 0.75 stands, except state park kind at
0.65 (density compensation).

### 2.10 Roads (post-crop)

The crop (C1–C3) does the heavy lifting; class does the rest.
`build_site_data.py` must carry **`route_sys` and name** into the
site copy (source fields exist; `cartoclass` is uniformly null —
ignore it). Builder derives `road_class` at build time from
`route_sys` via the MnDOT route-system table (verify codes against
the service metadata at build time; do not hard-code from memory)
with name-pattern fallback (`CO RD …`, `MN …`, `US …`):

| Class | Membership | Style | Bands |
|---|---|---|---|
| A — arterial | trunk highways + county state-aid | `#616161` w1.75 op 0.85 (current roads style) | Z1+ |
| B — local named | other named roads | `#83837a` w1.1 op 0.7 | Z2+ |
| C — minor | unnamed / township / private lanes | `#a9a396` w0.75 op 0.55 | Z3+ |
| F — forest road | moved from access (§2.9) | `#8c510a` w1 op 0.8 | Z2+ |

Private roads stay **drawn and labelled private** per DESIGN.md
rule 3 — class C popups carry "Private road — informal access,
ask first" wherever the source identifies them; the class-C
feather (below) must never make a private lane look like a public
one fading in.

**Cut feather:** features carrying `cut: true` (C2) render at
**0.6× their class opacity**. Canvas cannot gradient a path
cheaply; a single opacity step is the honest approximation, and
paired with C3's finish-the-block rule it means visibly-faded
endings are rare and always mean "continues, not shown." The
legend's Roads row gains a footnote line in the Sources card:
"Roads and access lines are shown within a corridor of the
trail; faded ends continue beyond it." One sentence, and the crop
stops being a silent edit.

No road name labels on the face at any zoom — every candidate base
already labels roads, and double-labelling is how maps get noisy.
Road identity lives in popups (name + class), as today.

### 2.11 Asset pins

Keep the construction (circleMarker r6, white ring w2, `#e6550d`
fill) — it is the only orange-red left once OHV moves, and it
should stay unique to assets. Two additions when the inventory
data lands: **condition ring** — the white ring becomes a
condition ring (good `#1a9850` / fair `#e08214` / poor `#b2182b`,
w2.5) with white demoted to a 1 px outer edge, so a Z3 glance
reads the chapter's maintenance state as a scatter of green/
amber/red halos; and **Z1–Z2 aggregation**: below Z3, pins within
~40 px merge into count badges (paper disc, slate text) computed
client-side from the loaded GeoJSON — no library, ~40 lines,
and it keeps the chapter view clean while the inventory is small
enough that every pin still shows by Z3.

### 2.12 Draw order (extends `assertDrawOrder`)

Back → front, one list, no exceptions:

1. Parcels (when enabled)
2. Non-road access
3. Roads (classes C, B, F, A in that order within the layer)
4. LLC line, then ITM line (each: casing, then core)
5. Adopted sections (casing, underlay, amber)
6. Gap (casing, core, label)
7. Boundary ticks, then terminus ticks
8. Places + asset pins (SVG, above canvas as today)
9. Selection halo — above everything, as today
10. Labels/tooltips — Leaflet's tooltip pane already rides top;
    the §2.7 pass decides what survives there

LLC is drawn *inside* step 4 under ITM deliberately: where the
two lines share tread or cross, the chapter's line wins.

### 2.13 Hover and selection

Keep both, they are v4's best interaction decisions. Selection
halo: white casing w10 at 0.9 under a type-coloured core (amber
for a section, gap red for the gap) — spec the halo's core to
**reuse the selected element's own style at weight +2**, so
selection reads as emphasis, never as a new symbol. Hover chip
unchanged; add one behaviour: hovering a *road or access line*
shows the same dwell chip with name + class + (for cut features)
"continues beyond the corridor" — context layers currently give
no hover feedback, and a chip is cheaper than a click for the
"what is this line?" question the crop will provoke.

---

## Part 3 — State mile markers (new layer)

Facts (coordinator-verified against the NCTA org services,
2026-11-10): the service `mn_halfmile_points` (ArcGIS org
`services2.arcgis.com/UfGVyqUm4GHa2zrj`, FeatureServer layer 0
"halfmile_mn") carries 1,119 points statewide — a point every half
mile on the Minnesota NCT; `index_ = "Index"` flags whole miles,
`"Interval"` the halves; `ident` carries the state reckoning. In
the working extent: **232 points, MN-123.5 through MN-239**. The
service's lat/long *attribute columns* are corrupt (longitude
duplicates latitude); the point geometry (UTM zone 15N) is
correct.

### M1. Pull

New `scripts/pull_mile_markers.py`, sibling to
`pull_official_line.py`: query the extent envelope, **`outSR=4326`
on the request** so the service returns lon/lat geometry — never
read the attribute lat/long columns, and do not hand-convert UTM
in stdlib if the service will do it. Keep `ident`, `index_`,
`wypnt_id`. Retain points within the extent that snap to the
depicted lines within 250 m (a handful of state points follow the
authorised route where the depiction differs; points that don't
snap belong to a route this map doesn't draw — exclude, and print
the count in the build report). Output
`site/data/milemarkers.geojson` via the site build (points are
only rounded, never simplified — same treatment as access points).

### M2. Display

Own layer, Chapter group, toggle label **"Mile markers (state)"**,
**default off** (the face is quiet until asked; the inspector
already speaks mileage). Rendering:

- Whole miles: slate (`COLORS.tick`) disc r3.5, white ring w1.5 —
  the tick bars' material, shrunk to a point: the map's measuring
  furniture all speaks slate.
- Half miles: slate disc r2, no ring, opacity 0.75.
- Labels: whole miles only, text = the ident's number ("187",
  not "MN-187" — the "MN" is the layer's name, stated in the
  legend and the toggle; repeating it 116 times is noise), 9.5 px,
  `--ink-soft`, paper halo, placed above the line by the §2.7
  pass. **Z3+ only.** Half miles are never labelled — at Z4 a
  labelled half ("187.5") may appear if its box survives the
  collision pass at the *lowest* priority.
- The markers sit *on* the line (they are of the line) — draw
  order step 7½, with the ticks, below labels.

### M3. Two reckonings, never mixed

The chapter tracker reckons differently: its "NCT Mile Virtual
Markers" run 169.5 → 246.25 over the same ground, **~46–48 miles
off the state's numbering**. This spec does not resolve that, and
the map must not pretend to:

- The map **face** shows the **state** reckoning only, and only
  via this layer, labelled as state in the toggle and legend.
- The **tracker** reckoning stays where it lives today —
  gazetteer/inspector data — and any inspector/gazetteer surface
  that shows it must label it "chapter tracker miles" wherever it
  appears next to anything state (the current inspector caption's
  bare "NCT 187" formulation should gain its source label in the
  same build — a one-word change with a long memory).
- The two numberings never appear in the same view unlabelled,
  and no conversion, offset, or "corrected" figure is computed or
  displayed. **Open chapter question, flagged for Paul/the
  chapter:** which reckoning the chapter wants as its working
  standard, and whether the tracker's virtual markers were built
  from a different route vintage. Until the chapter answers, the
  Sources card gains one sentence: "Mile markers show the
  state (NCTA) reckoning; the chapter tracker's mile figures
  differ by roughly 46–48 miles and are labelled as tracker
  miles where shown."

---

## Part 4 — Signature moves

Five. Each is buildable with the machinery the map already has;
each is costed honestly.

### S1. The measured spine (chainage annotation)

The map knows where everything is except *how far along* — the
one coordinate chapter members actually speak ("the washout at
mile 40"). Sections carry chainage; make it visible: at every
**10 chapter-miles from the west end**, a small slate numeral
sits on the line — `10`, `20`, … `70` — in the tick bars' voice
(9.5 px, slate, paper halo), rendered at Z2+, placed by the §2.7
pass at section-name priority. Build: a `build_chainage()` pass
in the site build, sibling to `build_boundaries()`, walking
stretch geometries by `chainage_start_mi` and interpolating the
10-mile points; output folds into `boundaries.geojson` as a
`kind: "chainage"` point set or a small sibling file. **This is a
relative measure ("miles from the chapter's west end"), not a
third mileage reckoning** — it is labelled that way in the legend
("10 — miles from west end") and never abbreviated to "NCT mile."
Cost: ~60 lines of build code (the interpolation pattern already
exists in `tick_for`), ~25 lines client-side. The cool: the whole
chapter becomes addressable in one glance, and Prev/Next in the
inspector suddenly has a visible ruler to walk along.

### S2. The breathing gap

The gap is a *story about waiting*, so it is the one element
allowed motion: the core's dash marches slowly westward
(`dashOffset` animated by `requestAnimationFrame`, one dash cycle
per ~6 s), toward Itasca State Park, toward where an adopter
would come from. Rules that keep it tasteful: animation runs
only while the gaps layer is on, the tab is visible, and
`prefers-reduced-motion` is not set; it stops dead in print
(dashes print statically, as today). At Z2+, the gap label trades
its bare halo text for a **sign**: paper-filled chip, 1 px
`#b2182b` border, radius 4, the text "Unadopted — 2.9 mi" inside —
styled after the Carsonite marker it is asking someone to tend.
Cost: ~30 lines (one rAF loop touching one layer's style) + one
CSS class. The cool: every other line on the map is geography;
this one is an appeal, and it should feel different in kind.

### S3. Terrain-breathing casings

Today one white casing (0.5–0.55 opacity) serves six+ bases — a
compromise that is slightly wrong on all of them. Give the map
three casing registers, switched by the existing
`baselayerchange` event from a `CASING_BY_BASE` table (base name
→ register), restyling the four cased layers (trail, LLC-none,
stretches, gap) in one function:

| Register | Bases | Casing |
|---|---|---|
| paper | OpenTopoMap, OSM, CARTO pair, CyclOSM, HOT | `#f7f5ee` (paper, not clinic white), trail 0.45, amber 0.4 |
| photo | NAIP, Esri Imagery, ImageryTopo | `#ffffff`, trail 0.85, amber 0.75, gap casing 0.55 |
| relief | MN LiDAR hillshade, USGS Topo, Esri Hillshade, NatGeo | paper `#f7f5ee`, trail 0.6, weights +0.5 (relief texture eats thin lines) |

The `body.base-imagery` label flip already proves the mechanism;
this extends it from labels to lines. Cost: ~35 lines. The cool:
the map visibly *re-dresses* for each base instead of wearing one
compromise — the single change that most makes it feel crafted
rather than generated, and the one a visualisation professional
will notice first.

### S4. Places, drawn (gazetteer waypoints as a layer)

The gazetteer's 114 NCTA waypoints (Parking 43, Camping 36, POI
29, Water 4, Shelter 2) are currently Find-only — invisible until
searched, which undersells the public-promotion half of the map's
job. New **"Places"** layer (Context group, default **off**,
Z3+): each kind a 15 px paper disc with a slate ring and a single
letter glyph — **P**, **C**, **W**, **S** — and POIs a plain
slate dot r3 (they are the least actionable). Discs are divIcons
in the terminus-label idiom; popups reuse the gazetteer record
(name, section, "x mi from the west end," state mile where the
record carries one — labelled, per M3). Cost: the data already
ships to the browser for Find; ~70 lines to render a subset as a
layer. The cool: zoom to any section at crew zoom and it suddenly
has furniture — parking, water, a shelter — which is the
difference between a line on a map and a place you can plan a
day around.

### S5. The beer-night print sheet (print variant)

Printability is a stated design plus (DESIGN.md); the print CSS
currently carries a header and a legend and stops there. Give
print its own cartography, in the `@media print` block:

- Roads collapse to classes A+F only, in one grey (`#616161`,
  w1.2 / w1) — a handout reader needs "which roads exist," not
  the class system.
- Non-road access collapses to solid hairlines for state trail +
  forest-road equivalents and drops snowmobile/hunter entirely —
  **unless** a "Winter" body class is set (a print-dialog-era
  toggle in the panel: Winter promotes snowmobile to w1.25
  `#8856a7` solid-ish `"4 2"` and restores it in print; the same
  class restyles it on screen). Seasonal symbology is honest
  symbology: a snowmobile trail in July is a rumour.
- Chainage numerals (S1) print at every **5** miles (screen shows
  10s) — paper has no zoom, and the 5-mile ruler is what a
  recruiting conversation actually points at.
- The gap prints with hatch *and* its sign chip (S2's chip is a
  print-native idea to begin with); `print-color-adjust: exact`
  on the story elements as the header spec already directs.

Cost: ~50 lines of print CSS + the Winter class hook. The cool:
the chapter's social-night handout becomes a *different, purpose-
built map* from the same page — which is exactly what a good
atlas does between its overview and its plates.

---

## Part 5 — Build checklist (ordered)

1. `build_site_data.py`: grid-index corridor clip (C1, C2) for
   access + roads; `cut` flags; C3 extensions; C4 connector test
   (run on access incl. forest roads pre-move); `route_sys`
   carried for roads + `road_class` derivation (§2.10); forest
   roads emitted into roads output with class F (§2.9). Print the
   C7 verification table in the build report.
2. `scripts/pull_mile_markers.py` + site-build pass for
   `milemarkers.geojson` (M1).
3. `build_chainage()` in the site build (S1).
4. `app.js`: zoom-stepped weights (§2.1–2.3); tick band fades
   (§2.5); unified annotation pass (§2.7); parcel styles + Z3
   gate (§2.8); access kind table + Roads classes + cut feather
   (§2.9–2.10); draw-order list (§2.12); context-layer hover
   chips (§2.13); mile-marker layer (M2); chainage layer (S1);
   gap march + sign chip (S2); casing registers (S3); Places
   layer (S4).
5. `style.css`: sign chip, Places discs, Winter class, print
   block (S5).
6. Text: Sources-card corridor footnote (§2.10) + mileage
   reckoning sentence (M3); inspector caption source label (M3);
   legend regenerated from the new constants (the v4 rule —
   legend follows the style constants, never hand-copied).

**Acceptance checks for the coordinator's proof pass:** build
report inside the C7 bands; at Z1 with all layers on, no access
or road geometry outside the two corridor bands (screenshot
against the extent render); gap still the only red on the face;
section names, termini, mile labels coexisting at Z3 over
Chip-1 with zero overlaps; print preview of the beer-night sheet
in both seasons.

---

*Filed as a spec. Nothing in `site/` or `scripts/` was changed by
this note. Paul reviews; the builder implements; the numbers in
§0 and C7 are the contract the implementation is checked
against.*

# Visual design review — Itasca Moraine Chapter Trail Map

Reviewer: visual design (cartographic/web). Sources: REVIEW-BRIEF.md, all six
screenshots, `site/style.css`, `site/app.js`, `site/index.html` as of Nov 10, 2026
(v3, commit `1ed4f18`). Every item names the value it replaces and where it lives.
Interaction-model decisions are flagged, not made — those belong to the UX review;
this file owns how things *look*.

## Verdict in one paragraph

The bones are good: a warm paper panel (`#f7f5ee`), a restrained line system, and
one clear story (amber = ours and adopted, red = the gap). Three things keep it
from being beautiful. (1) The data has **no casing and no tonal discipline**, so
on any real base map the green line fights the base's own greens and the purple
neighbour line outshouts the chapter's own sections (shots 1–2). (2) The **hover
card is a spreadsheet wearing a tooltip's clothes** — ~600 px tall, clipped by the
viewport in shots 1 and 6, with its value column squeezed until "Test adopter 29"
wraps onto three lines. (3) The **chrome has drifted from the map**: the legend
still advertises a layer that was deleted and shows roads in a colour the map no
longer uses. Fix those three and the map goes from competent to handsome without
touching the architecture.

---

## 1. Colour system — give it tokens, then discipline the loud voices

Introduce CSS variables in `style.css :root` and matching constants at the top of
`app.js` (one-time, ~30 min, pays off at chapter handoff — whomever inherits this
should not have to grep for hexes):

```css
:root {
  --paper: #f7f5ee;        /* panel — keep */
  --paper-line: #c9c2ab;   /* panel borders — keep */
  --ink: #1c2a1e;          /* body text — keep */
  --ink-soft: #5a665c;     /* keys, captions — keep */
  --trail: #1a9850;        /* ITM green */
  --trail-deep: #14532d;   /* termini, emphasis text */
  --adopted: #e08214;      /* amber */
  --adopted-deep: #6e4400; /* section label text */
  --gap: #d7301f;          /* red */
  --neighbour: #7e6a9e;    /* LLC — proposed, see D2 */
  --tick: #37474f;         /* boundary bars — proposed, see D5 */
}
```

### D1 (P0) — Case the lines, or the aerial bases will eat them

Neither the official line (weight 4) nor the amber stretches (weight 6) has a
casing. On OSM/OpenTopoMap that passes; on NAIP/Esri aerial — a wall of forest
green — a `#1a9850` line is camouflage, and on the LiDAR hillshade the amber
reads muddy because it is drawn at opacity 0.8 over grey. Draw each twice,
casing first: official line casing `#ffffff` weight 7, opacity 0.55, under the
existing green 4; stretches casing `#ffffff` weight 8.5, opacity 0.5, under the
amber. Also raise the amber itself: `STRETCH_STYLE` opacity **0.8 → 1.0** — the
0.8 blend is why the sections in shots 1/2/5 look burnt and fuzzy at the edges
rather than confidently orange. Cost: two extra `L.geoJSON` passes in the
builders, same pattern the gap and ticks already use. This is the single
highest-leverage visual change on the map.

### D2 (P0) — Demote the neighbour

In shots 1 and 2 the most saturated, visually dominant object on the map is the
Laurentian Lakes line — `#762a83` at full weight 4 and opacity 0.9. It is the
*neighbour's* trail; a first-time viewer reads purple as the subject. Change
`CHAPTER_COLORS.LLC` to **`#7e6a9e`**, weight **4 → 3**, opacity **0.9 → 0.8**.
It stays findable and clearly "another chapter," but the eye lands on green and
amber first. (The chapter-as-attribute model is untouched; this is one constant.)

### D3 (P1) — Unify the six bases with one CSS filter

Six bases from five providers will never share a palette, and the panel's warm
paper clashes with OSM's cool beige in particular. One line in `style.css`
pulls every base into the panel's register:

```css
.leaflet-tile-pane { filter: saturate(0.82) sepia(0.06) brightness(1.01); }
```

Overlays live in other panes and are unaffected. Effect: OSM's road oranges stop
competing with the adopted amber (a real confusion risk at z10 — OSM primary
roads render in nearly the same hue as `#e08214`), park greens quiet down under
the trail green, and the aerials warm up. Exclude it from print (see §6).

### D4 (P1) — The gap is the story; dress it like it

GAP-W is the recruiting headline, yet in shot 2 it is a ~15 px red smudge the eye
slides past, and its casing (`#b2182b`, weight 11, opacity 0.3) is doing too
little. Raise casing opacity **0.3 → 0.4**, core dash **"12 7" → "14 8"**, and —
the important part — give the gap a **name on the map**: a permanent label in
the terminus-label style but in the gap's voice: text "Unadopted — 2.9 mi",
12 px, weight 700, colour `#b2182b`, white/paper halo, anchored at the gap's
midpoint, shown at z ≥ 9. The beer-night test ("adopted vs the one gap in under
10 seconds") is currently passable only by reading the panel; this makes the
*map* tell it.

### D5 (P2) — Soften the tick bars

The ticks' near-black core (`#263238`, weight 3.5, casing 6) reads as railroad
ties; in the Chip cluster (shot 5) they are the heaviest marks on the map,
heavier than the trail they annotate. Core → **`#37474f`**, weight **3.5 → 2.75**;
casing weight **6 → 5**, opacity **0.9 → 0.85**. Terminus bars: green core
**5 → 4.5**. The bars keep their authority (they are still the darkest thing
present) but stop shouting over the section names next to them.

---

## 2. Base maps — pairing recommendations

Current order/default in `app.js`: OSM (default), OpenTopoMap, USGS Topo,
MN LiDAR hillshade, USGS NAIP, Esri World Imagery.

| Base | Verdict with this data |
|---|---|
| **OpenTopoMap** | Best flatterer. Contours sell the moraine, forest greens are muted enough (with D3) for the trail green, roads are quiet greys — nothing mimics the amber. Busy above z15, but chapter work happens at z10–14. |
| **MN LiDAR hillshade** | The most *beautiful* under this data — the chapter is a moraine; the terrain is the story, and amber/red pop on neutral grey relief. No labels or roads, so it fails as a sole default, but it should be the recommended "terrain" view in the legend/Sources card. |
| **OSM** | The familiar one, and the worst colour neighbour: beige + park-green + orange roads against a green/amber/red dataset. Keep for recognition, demote from default. |
| **USGS Topo 1:24k** | Authoritative quad feel, prints the cleanest of the six (see §6). Its own green/brown symbology competes a little; with D1 casing the trail survives it. |
| **USGS NAIP / Esri Imagery** | Necessary for land-cover questions, hostile to a green line. Only viable with D1 casing; Esri's is the sharper and warmer of the two. |

**Recommendation: change the default base to OpenTopoMap**, OSM second in the
switcher. Rationale: the default view is the chapter/portfolio view (z10,
sections on), and that is exactly where OpenTopoMap flatters and OSM fights.
If the chapter pushes back on familiarity grounds, the fallback is OSM default
**plus D3's filter**, which removes most of the clash. Do not add a seventh
base; six is already generous for a handoff document.

---

## 3. Typography and labels

The stack (`"Segoe UI", "Helvetica Neue", Arial`) renders as generic sans on
the Linux-captured screenshots and will on Macs too. Move to a native stack —
`-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` — same
no-build portability, better rendering everywhere. Then:

- **Panel title** (1.15 rem, shots 1–6): set weight 650 and letter-spacing
  −0.01 em; drop `.draft` to 0.82 rem. The title currently wraps to two lines
  and spends the panel's most valuable pixels apologising. (Whether "working
  draft" should be there at all on a public page is an editorial call — §7.)
- **Section names** (`.section-name-label`, 11 px, `#6e4400`): the colour is
  right; the halo is pure-white triple-shadow, which reads clinical against the
  warm panel. Change halo colour to `rgba(247,245,238,0.92)` (paper) — labels
  then sit *in* the map's world. Keep 11 px/600; add letter-spacing 0.02 em,
  which measurably helps these short caps-less names at z11.
- **Declutter residual**: shot 5 still shows "West-13West-14" fused at a bend —
  the greedy pass estimates text width and lost. Two cheap hardenings: add 6 px
  of slop to the estimated label width in `layoutSectionLabels`, and when two
  labels still collide after the pass, prefer hiding the *shorter* section's
  (already the rule) but also hide any label whose anchor sits within 26 px of
  a tick bar at z ≤ 10 — the West-13/14 pair sits on a tick-dense bend.
- **Terminus names** (`.terminus-label span`, 12 px, `#14532d`): keep, weight
  600 → 700. They are the map's only proper nouns at chapter zoom and should
  carry slightly more rank than section names.
- **Keys in cards** (`td.k`, `#5a665c`, nowrap): see §4 — the nowrap keys are
  half the hover card's width problem.


---

## 4. The hover card — visual design

*(The interaction model — keep hover, pin on click, dock a panel — is the UX
reviewer's decision. This section specifies the card's visual form, and flags
where the form assumes an interaction.)*

### What the screenshots show

Shot 6 is the indictment: the card is ~600 px tall in a 900 px viewport,
anchored above the cursor with no flip logic (Leaflet *tooltips*, unlike
popups, don't auto-pan or clamp), so its top third — including the section name
and its NCT mile — is simply off-screen. Shot 1 shows the second failure: the
card docks against the right viewport edge and its table renegotiates column
widths, so the value column narrows to ~90 px and "Test adopter / 29",
"Chippewa / National / Forest, Paul / Bunyan State / Forest" stack into
ribbons. A cursor-following card also occludes the very section being examined
and re-renders its layout on every mousemove width change. The *content* is
loved (the owner said so); the *container* is the problem.

### The proposed form: a fixed-geometry "record sheet"

Whatever surface it lands on, give the record one stable visual form:

- **Fixed width 336 px** (288 px if docked in the 320 px panel), never
  width-negotiated by viewport position. Same content, same layout, every time.
- **Header band**: background `#eef3e6` (the mileage card's green tint),
  4 px left spine in the section's status colour (amber `#e08214` adopted /
  red `#d7301f` gap), section name at 15 px / 700 ink, and a **status pill**
  right-aligned: "ADOPTED" — 10.5 px, uppercase, letter-spacing 0.06 em,
  bg `#e6f4ea`, text `#14532d`, border 1 px `#a9c295`, radius 999 px. Today
  "Status: Adopted" is row 11 of 15 in plain text; the single most-asked fact
  deserves the header.
- **Stat strip** under the header: three columns, numerals at 16 px / 650 —
  length, NCT mile range, tracker ID — captions 10 px uppercase `#5a665c`.
  This absorbs "Length (official)", "Length (tracker)" (merge into one stat:
  "3.5 mi tracker · 3.4 on the line"), "NCT miles", "Chapter tracker section",
  and deletes "From the west end / From the east end" as rows (one caption
  line under the strip: "NCT 213.25 · 46.7 mi from the west end").
- **Body rows**: replace the `<table>` with a grid, key column 104 px fixed.
  Keys: 10.5 px, uppercase, letter-spacing 0.05 em, `#5a665c`, **wrapping
  allowed** (drop `nowrap` — it is what starves the value column). Values:
  12.5 px ink. Row separators 1 px `#eee7d2` (the gazetteer dropdown's divider
  colour — reuse, don't invent). Group with two subheads at 11 px / 700:
  **People** (adopter, sawyer) and **The section** (description, land,
  maintenance, help requested). "What's here" stays last, its counts bolded.
- **Cut rows**: "Kind: Section" (the header says it), "Section: Chip-1"
  (duplicates the header). 15 rows → 9 + the stat strip. Nothing of substance
  is lost; everything left is findable in one glance.
- **Container**: radius **6 → 10 px**, border `1 px solid #c9c2ab` (the panel's
  own border — the current `rgba(0,0,0,0.25)` makes the card a foreign object),
  shadow `0 8px 28px rgba(28,42,30,0.28)`, **max-height `min(70vh, 560px)`**
  with internal scroll and a thin `#c9c2ab` scrollbar. A hard height cap is
  the difference between shot 6 and a usable card.
- **Provenance footer**: 10.5 px italic `#5a665c` — "From the chapter
  adoption tracker" (with the extract date when the build knows it). The card
  quotes a spreadsheet; it should cite it like one.

### Interaction assumptions (flagged for the UX review)

- If the card **stays a hover tooltip**: it additionally needs a positional
  clamp — anchor above *or below* the cursor by available space, and the
  max-height above. Visual form alone cannot fix shot 6.
- If it becomes a **click-pinned card or a docked panel section** (my visual
  preference, for what it's worth): the same spec applies unchanged at 288 px
  content width, the map stays visible while the record is read aloud at a
  meeting, and the sheet can be included in print (§6). The header spine +
  pill design assumes the reader's eye starts at the card, not at the cursor.
- Either way, the section's **own name label should highlight** while its card
  is up (label colour `#6e4400` → `#1c2a1e`, weight 700) so the eye can travel
  card → map without losing the thread. That coupling is visual, cheap, and
  currently absent.

---

## 5. Panel and chrome

- **Tell the story in the panel (P0)**: the `.mileage` paragraph is currently
  prose. Replace its layout with a **stacked adoption bar**: full-width,
  10 px tall, radius 5 px — amber segment at 96% (73.2 of 76.2 mi), red segment
  at 4% — with the sentence kept beneath at 0.85 rem. One glance, no reading:
  adopted vs gap, in the map's own colours. This is the beer-night test
  rendered as a graphic, and it costs one `<div>` and three CSS rules.
- **De-mustard the notice**: `.notice` (`#fdf3d7` bg, `#d9c169` border) is the
  only mustard object in a green/amber/paper world, and at the top of the panel
  it reads as a warning about the map itself. Restyle to bg `#f1eee1`, border
  `#d8d2bd`, with a 3 px left accent in `#8a6d1f`; drop to 0.82 rem. The legal
  content stays; the alarm goes.
- **Checkboxes**: native inputs render browser-blue in every screenshot — the
  only blue UI in the product. One line: `#layer-toggles input
  { accent-color: #1a9850; }`. Then give each toggle row a **16 px line-swatch**
  in its layer's colour (the legend already generates these colours in
  `buildLegend` — emit the same chip in the toggle label) and row padding
  3 px → 5 px with a `#f1eee1` hover. The Layers list then documents itself
  and the separate Legend card becomes reference, not necessity.
- **Find box**: good pill, good dropdown. Add a focus ring that matches the
  system — `outline: 2px solid #1a9850; outline-offset: 1px` on
  `#gaz-search:focus` — and the same for the corner buttons (keyboard users
  currently get default blue, off-palette).
- **Corner UI**: the Sources/Legend pills (bottom-left, `bottom: 42px`) stack
  directly over the scale control, producing the three-box clutter visible in
  every screenshot's lower-left. Style the Leaflet scale to the panel system
  (bg `rgba(247,245,238,0.88)`, border `#c9c2ab`, 10 px) so the stack reads as
  one instrument cluster; set the active corner button to bg `#14532d`, text
  `#fff` (currently `#e8e2c8` — indistinguishable at a glance).
- **Leaflet controls**: zoom (+/−) and the layers switcher are stock white/grey.
  Recolour to paper: `.leaflet-bar a, .leaflet-control-layers { background:
  #f7f5ee; border-color: #c9c2ab; border-radius: 8px; }` — small, and it makes
  the map feel made rather than assembled.

## 6. Print

Print is a stated use (recruiting handouts) and the current `@media print`
block works against it in three ways:

1. **The legend does not print.** `#corner-ui { display: none; }` removes the
   only legend. A paper map with amber sections and no key is a poster, not a
   handout. Add a print-only legend block *inside the panel* (duplicating
   `buildLegend`'s rows into a `#legend-print` div shown only in print).
2. **The notice prints at full size** on page 1. In print: `.notice` → 9 pt,
   no background (also kind to ink).
3. Base tiles print as-is; with D3's filter, add
   `@media print { .leaflet-tile-pane { filter: grayscale(0.25) contrast(1.02); } }`
   so a colour handout survives a B/W printer with the line hierarchy intact,
   and state in the panel's print footer which base prints best (USGS Topo).
   Add a print header line — chapter name, "printed from the chapter trail
  map", date via CSS `content` is not dynamic; stamp it in the existing
   panel footer instead.

Also: the amber at opacity 0.8 (D1 fixes to 1.0) prints washed on uncoated
stock; after D1, proof one sheet before a recruiting run.

## 7. Things I'd cut or demote

- **Legend rows for the removed Access points layer** ("Access point (trail
  crossing)" `#0570b0`, "(road crossing)" `#333333`): the layer was deleted in
  v3; the legend still promises it. Delete the two rows in `buildLegend`.
- **Legend truth pass generally**: the roads swatch still renders `#999999`
  (the pre-v3 invisible grey) while the map draws `#616161` at 1.75 px; the
  boundary swatch is a horizontal line for a feature whose whole point is
  being a *crosswise bar* — draw the swatch as a 3×14 px vertical bar. Legend
  swatches should be generated from the same style constants as the layers;
  today they are hand-copied strings, which is how the drift happened.
- **"(working draft)" in the H1** — demote to the notice/footer. The brief
  says this public page should look like something a chapter is proud to link;
  the largest text on it currently leads with an apology. (Editorial call,
  flagged: the draft *notice* itself must stay — its placement and volume are
  the design question.)

---

## Quick wins — CSS/values only, under an hour total

1. `accent-color: #1a9850` on toggle checkboxes (§5).
2. Tile-pane filter `saturate(0.82) sepia(0.06)` (D3).
3. `STRETCH_STYLE` opacity 0.8 → 1.0; gap casing opacity 0.3 → 0.4, dash →
   "14 8" (D1/D4, two literals in `app.js`).
4. Tick softening: `#263238` → `#37474f`, weights 3.5 → 2.75 / 6 → 5 (D5).
5. LLC demotion: `#762a83` → `#7e6a9e`, weight 3, opacity 0.8 (D2).
6. Label halo → paper `rgba(247,245,238,0.92)`; terminus weight → 700 (§3).
7. Notice de-mustard + `.draft` shrink (§5).
8. Hover card interim rescue, pure CSS: `max-height: min(70vh, 560px)`,
   `overflow-y: auto`, radius 10 px, border `#c9c2ab`, shadow per §4, and
   `.section-hover-card td.k { white-space: normal; width: 104px; }` —
   doesn't fix the shot-6 anchoring, but stops the three-line value ribbons
   today.
9. Legend string fixes: roads swatch `#999999` → `#616161`; delete the two
   access-point rows (§7).
10. Focus rings (Find, corner buttons) in trail green (§5); Leaflet bar /
    layers control paper recolour (§5).

## Larger moves — in priority order

1. **Line casings** for official line + stretches (D1) — builder changes in
   `app.js`, the aerial bases become usable, biggest beauty-per-dollar.
2. **Hover card rebuilt as the record sheet** (§4) — new markup builder +
   CSS; coordinates with the UX review's interaction decision.
3. **Default base → OpenTopoMap** + a one-line "which base when" note in the
   Sources card (§2).
4. **Panel story bar** (adoption progress bar) + **gap's on-map name label**
   (D4, §5) — makes the map itself pass the beer-night test.
5. **Design tokens pass** (§1) — CSS variables + `app.js` constants; enables
   everything above to stay coherent after handoff.
6. **Print overhaul** (§6) — print-only legend, print header, print tile
   filter; proof on paper once.
7. **Toggle swatches + legend generated from layer style constants** (§5, §7)
   — ends the legend-drift class of bug, not just its current instance.

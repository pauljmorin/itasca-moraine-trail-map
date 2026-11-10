# UX Review — Itasca Moraine Chapter Trail Map

Reviewer role: UI/UX expert. Sources: REVIEW-BRIEF.md, shots 1–6,
`site/index.html`, `site/style.css`, `site/app.js` (all line refs are to
the current files). Constraints honored throughout: static vanilla
Leaflet, no build step, no keys/accounts, placeholder names only,
parcels stay UI-disabled, big-screen meeting use is primary.

## Verdict in one paragraph

The map's data model and cartography are sound; its interaction model
has one structural fault: **the section record — the single most
valuable thing on the page — is delivered by the least stable
mechanism available (a cursor-following tooltip) and is duplicated in
a second, different-shaped container (the click popup) that shows a
different subset of the same record.** Fix that one fault with a
persistent inspector in the left panel, fed by a single selection
model, and most of the other friction (Find results, touch, keyboard,
print) resolves as a side effect. Everything else in this review is
prioritized polish around that core.

---

## Part 1 — The central question: replacing the hover card

### Why the current hover fails (evidence, not taste)

- **It cannot be read while being used.** The card is `sticky`
  (app.js ~L479–484) with `pointer-events` effectively unusable: to
  read a ~15-row table the presenter must hold the cursor perfectly
  still over a 6 px-wide amber line. Any drift kills it (`mouseout`,
  ~L488–494). This is a steadiness test, not an interface — worst
  exactly in the primary use case: a volunteer with a wireless mouse
  or trackpad, standing at a beer night, narrating.
- **It covers what it describes.** In shot-1 the card occupies roughly
  330 × 560 px of the right side and hides the Chip cluster the user
  is asking about. In shot-6 it runs off the top of the viewport —
  Leaflet tooltips have no height management, and this content
  (~600 px tall with the "What's here" block) exceeds a 900 px
  viewport once anchored above a mid-screen cursor.
- **It fires with no intent threshold.** `mouseover` shows instantly,
  so sweeping the cursor across the chapter at z10 strobes cards from
  every section crossed. There is no dwell delay anywhere in the
  handler.
- **It silently serves two different records.** Until the gazetteer
  fetch lands, `sectionHoverHtml` falls back to `stretchPopup(f)`
  (8 rows); afterwards it swaps to `gazPopupHtml(f)` (~15 rows +
  contents). Same gesture, two payloads, chosen by network timing.
- **It doesn't exist on touch.** No hover on a tablet — and a tablet
  passed around a meeting table is a plausible beer-night device.
  Touch users get only the click popup, i.e. the *smaller* record.
- **The click popup compounds the problem.** `stretchPopup` (app.js
  ~L294) shows status/adopter/lengths/access-at-ends but *not*
  maintenance, help-requested, comments, land, or "What's here" —
  while the Find popup (shot-3) shows all of it. Two competing truths
  for one section, differing by entry point. That, more than the
  tooltip mechanics, is what "there has to be a better way" is
  pointing at.

### Options evaluated

| Pattern | One gesture away? | Readable at leisure? | Survives pan/zoom? | Touch | Meeting narration | Verdict |
|---|---|---|---|---|---|---|
| Hover-lite + click-to-pin (pin = Leaflet popup) | Yes | Partially — popup auto-pans, clips at ~¾ viewport (shot-3 is ~770 px tall), dies on map click | No — Leaflet popups close on pan-away/new popup | Tap works | Presenter must re-click after every pan | Better than today; still a floating card competing with the map |
| **Persistent inspector in the left panel (chosen)** | Yes — click, tap, Find, or keyboard | Yes — fixed place, full panel height, scrollable | **Yes — selection is state, not a floating widget** | Yes — identical tap path | **Best — the record sits still while the presenter talks and pans** | **Adopt** |
| Right-side sheet over the map | Yes | Yes | Yes | Yes | Covers the map's east end (where Chip-10…12 live); duplicates the panel's job | Reject: second panel idiom, hides trail |

### The chosen pattern, specified: **Select → Inspector, with a hover-lite chip**

One selection model, four entry points, one rendering of the record.

**Selection model.** A single function — call it
`selectSection(feature, source)` — owns selection state. It is called
by: (1) clicking/tapping an adopted-section line or the gap line;
(2) choosing a Section (or the gap) result in Find; (3) the
inspector's prev/next buttons and ←/→ keys; (4) Enter on a Find
result. Selecting sets a persistent highlight and renders the record
into the inspector. Nothing else on the map renders section records.

**Hover-lite chip (replaces the full hover card).**
- Trigger: `mouseover` on a section line starts a **300 ms dwell
  timer**; only then does the chip appear. Moving to another section
  restarts the timer — no strobing during sweeps.
- Form: a non-sticky tooltip anchored to the line at the hover point
  (Leaflet tooltip, `direction` from the existing
  `sectionLabelPlacement` logic), **max-width 280 px, ~3 lines,
  `pointer-events: none`, 120 ms fade-in**. Content, in full:
  - Line 1: **Chip-1** · CHP-1 (name 13.5 px/600, tracker code muted)
  - Line 2: `3.4 mi · NCT 211.5–215 · Test adopter 29`
  - Line 3 (muted, 11 px): `Click for the full record`
- Simultaneously the hovered line gets a hover style (weight 6 → 8,
  color `#b45f06`) so the target is unambiguous.
- Dismissal: `mouseout`, pan start, zoom start, or selection. It
  never follows the cursor, never exceeds ~64 px tall, and can never
  clip (Leaflet keeps a small tooltip in view; a 600 px one it
  cannot).
- Content comes **only from the stretch feature's own properties**
  (name, lengths, NCT range if present, first adopter placeholder) —
  no gazetteer fetch, so no content swap, ever. The full record is
  one click away, which is the chip's whole job.

**Inspector (the record's new home).**
- Placement: a dedicated region **inside the left panel, directly
  below the Find box** (`#inspector` between `#gazetteer` and the
  Layers `<h2>` in index.html), so the eye path is story → find →
  record → layers. On selection, `scrollIntoView({block: "nearest"})`
  brings it into view if the panel is scrolled. At ≤720 px it becomes
  a bottom sheet over the map (position fixed, left/right 0,
  max-height 45 vh, own scroll) — same DOM node, CSS only.
- Empty state (nothing selected): one muted line — *"Select a
  section: click the amber line, or find it above. ← → walk the
  trail."* — plus, permanently, a one-line gap callout in red:
  *"Unadopted: GAP-W, 2.9 mi — Itasca State Park"* that selects the
  gap when clicked. The recruiting story stays visible even with no
  selection.
- Anatomy when a section is selected (anatomy is the fix for the
  15-row wall in shots 1/3/6 — prominence is earned by meeting use,
  not spreadsheet order):
  - **Header:** section name, 17 px/600; tracker code as a small
    chip (`CHP-1`); a status pill at right — amber `#e08214` fill,
    white text, "Adopted" (red `#d7301f` "Unadopted" for the gap).
    Close × (clears selection) at the corner, 28 × 28 px target.
  - **Key strip (always visible, 2 × 2 grid, label 10.5 px uppercase
    muted / value 13.5 px):** Length — `3.4 mi` with the tracker
    length demoted to muted parens `(tracker 3.5)`; NCT miles —
    `211.5–215 · map MN-039`; Adopted by — placeholders, joined;
    Sawyer — placeholder. These four are what a meeting actually
    asks about a section.
  - **Help callout (conditional):** if `help_requested` is non-empty,
    a left-border (3 px, `#d7301f`) tinted block: **"Help requested:
    30"** with the existing verbatim label provenance kept in the
    details tier. This is the recruiting signal; today it is row 13
    of 15 (shot-3). It must be findable in under a second.
  - **Description:** the tracker description as a paragraph, 13 px,
    clamped to 3 lines with a "More" toggle.
  - **Details (`<details>`, closed by default, summary "Section
    details"):** Land; 2026 maintenance; Tracker comments; From the
    west end / From the east end (currently rows 4–5 of every card —
    reference trivia, demoted); Kind/NCT-mile point fields for
    boundary-type records; the off-chain note where present.
  - **"What's here" (`<details>`, closed by default):** the
    `gazContents` groups, unchanged in content, but each group name
    becomes a row with a count chip. (Future: clicking a name flies
    to it. Not required for this pass.)
  - **Footer:** two buttons — **Zoom to section** (fitBounds of the
    section geometry, padding 40 px, max zoom 14) and **‹ Prev /
    Next ›** section buttons ordered by chainage. Prev/next is the
    beer-night killer feature: the presenter walks the trail west →
    east, one click per section, record updating in place, never
    hunting for a 6 px line with a mouse.
- Behavior while panning/zooming: **nothing happens.** The record
  stays; the highlight stays. This is the property no floating card
  can offer and the reason the inspector wins for narration.
- Selection highlight: the selected section is redrawn with a white
  casing (9 px) under an amber core (6 px, `#e08214` at full
  opacity), raised above the other sections; the gap gets the same
  casing under its red dash. Cleared on ×, Esc, or clicking the
  official line / empty map (clicking empty map clears — standard,
  and harmless because reselection is one click).
- The gap uses the same inspector with its own template: red
  "Unadopted" pill, length, land, west/east end access and crossing
  trails (today's `gapPopup` content), and the help callout slot
  replaced by a standing line: *"No adopter — this is the chapter's
  recruiting gap."*

**What happens to the old patterns.**
- The sticky full-record hover tooltip (`sectionHoverTip`,
  `sectionHoverHtml`, `.section-hover-card` CSS): **deleted.**
- `stretchPopup` and the `bindPopup` on stretches: **deleted** —
  click now selects. No information is lost; every `stretchPopup`
  row exists in the inspector (access-at-start/end moves to Details).
- `gapPopup` as a popup: deleted; content moves to the inspector
  gap template.
- Leaflet popups **remain** for the things they suit — point-local,
  read-and-close facts: official-line segments (`trailPopup`),
  access lines, roads, parcels (when re-enabled), asset pins, and
  non-section Find results. Popups get one global guard:
  `maxHeight: "70vh"` with internal scroll, so nothing repeats
  shot-3's near-full-viewport takeover.
- Find → Section: `gazSelect` stops opening a popup for sections.
  It calls `selectSection`, fits the section's bounds (not
  `flyTo(point, z14)` — shot-3 shows why: the point-zoom throws away
  the section's shape and the popup then covers what remains), and
  keeps the red highlight marker off for sections (the casing
  highlight replaces it). Non-section results keep marker + popup.

**Keyboard & touch, explicitly.**
- Find becomes a real combobox: `role="listbox"`/`option`,
  ↑/↓ move an active row (visible 2 px outline + `#f3efdd` fill),
  Enter selects, Esc closes. Today only Enter-on-first-result works
  (app.js gazetteerUi) and selection is `mousedown`-only — keyboard
  users and screen readers are locked out of the map's best feature.
- When the inspector has focus, ←/→ = prev/next section. The Find
  input keeps its own arrow behavior; no global hijack.
- Touch: hover chip never fires (guard on
  `window.matchMedia("(pointer: coarse)")`); tap on a section =
  click = select. Because canvas lines are thin tap targets, add a
  near-invisible hit underlay per section on coarse pointers:
  duplicate polyline, weight 14, opacity 0.02, `interactive: true`,
  wired to the same select handler.
- Focus visible: 2 px outline `#1a9850` offset 2 px on all panel
  controls (currently no `:focus-visible` styling anywhere in
  style.css).

---

## Part 2 — The rest of the UX, prioritized

### P1. The default view doesn't tell the chapter's story (beer-night test: marginal fail)

Shot-3 is the first-time view: adopted sections **off** by default
(`stretches` `onByDefault: false`), so a first-time viewer sees a
plain green line, a red dash, and must take the "73.2 mi adopted"
claim on faith from a text box. Shot-2 (sections on) *is* the story —
amber over green the length of the chapter. **Flip `stretches` to
`onByDefault: true`.** The declutter pass now makes this safe: at z10
it shows 17 of 30 names, at z9 eight — measured behavior from the
current build. Keep everything else in the default set as is.

Two supporting fixes:
- **The east end falls off the stage.** In shots 1 and 2 the east
  terminus label is clipped at the viewport edge ("Itasca Moraine —
  e…"). `fitBounds(...pad(0.02))` is too tight for a label that
  extends ~90 px past its anchor. Use `pad(0.07)` plus
  `paddingTopRight: [100, 20]` in the fitBounds options, and cap the
  initial zoom at 10.
- **The purple line is unexplained for the first 10 seconds.** The
  Laurentian Lakes line fills the entire west half of shots 1/2/5,
  and nothing visible says what it is — the legend that explains it
  is closed behind a button. Add one sentence to the mileage box:
  *"Purple: Laurentian Lakes Chapter, shown for context."* And add a
  **mini-legend strip** under the mileage box — five inline swatches
  (Trail / Adopted / Gap / Chapter end / Neighbor chapter), 11.5 px
  text, always visible. The full legend stays behind its button for
  the access-layer detail nobody needs in the first minute.
- **Make the story box a picture.** Replace the mileage paragraph's
  numbers-only telling with a slim adoption bar: a 10 px-high,
  full-panel-width bar, 96% amber with the western 4% in dashed red,
  captioned "73.2 of 76.2 mi adopted — the red 2.9 mi in Itasca State
  Park has no adopter." Pure CSS widths from the two numbers already
  in the HTML. A first-time viewer should *see* the one gap before
  reading anything.

### P2. Legend and Sources: stale content, hidden placement

- **The legend documents a deleted layer.** `buildLegend` still adds
  "Access point (trail crossing)" and "Access point (road crossing)"
  pins (app.js ~L863–866) for the layer removed in v3. Cut both rows;
  crossings now live in Find, which the mini-legend/Find hint can say.
- **The Roads swatch is the old, invisible roads color** (`#999999`,
  ~L877) while roads now draw `#616161` at 1.75 px. Fix the swatch —
  a legend that misstates the one style the owner already complained
  about ("doesn't seem to have any data") undermines trust in every
  other row.
- **The Sources card credits removed bases.** index.html L51–56 still
  lists MnGeo spring aerial and USGS shaded relief as base maps;
  both were cut in v3. Update to the actual six, and drop or qualify
  the parcels credit line while parcels are UI-disabled (the privacy
  paragraph can stay — it also covers the placeholder rule, which is
  live).
- Placement itself is defensible (bottom-left, above the scale bar,
  start closed) **once** the mini-legend (P1) exists. One change:
  make the two buttons a segmented pair (shared border, active state
  already styled) and close one card when the other opens — today
  they toggle independently and can stack two 55 vh cards over the
  map's southwest corner.

### P3. Find: the best feature has the weakest result design

- **No-results is indistinguishable from still-loading.** `gazSearch`
  returning `[]` just hides the box. Add an explicit state row:
  *"No matches for 'xyz' — try a section (Chip-3), a road, or a
  lake."* Also fix the `gazLoad` race: when a load is already in
  flight, later callers' callbacks are silently dropped
  (`if (gazLoading) return;`) — queue the callback instead, and
  debounce input by 120 ms.
- **Result rows waste their width.** Current row = name + kind +
  right-floated mile (style.css `.gaz-result`). Make rows two-line:
  name (600) over a muted sub-line `Section · NCT 211.5–215 · 3.4 mi`
  or `Parking · NCT 213.2 · in Chip-1`; add a 8 px kind dot colored
  by kind (Section amber, Parking blue `#0570b0`, Camping green,
  Water cyan, Crossing grey). Cap at 8 rows with a footer line
  "12 matches — keep typing to narrow." A presenter scanning for
  "the parking near Chip-1" currently has to read every row's tail.
- **Discoverability:** the placeholder is good; add a one-line hint
  under the input, 11.5 px muted: *"257 places: sections, crossings,
  parking, camping, water."* — it teaches the index's scope, which
  the placeholder's "…" only implies. Also: `/` focuses Find from
  anywhere on the page (standard, cheap, and presenters love it).
- Section selection behavior changes per Part 1 (fitBounds +
  inspector, no z14 point-zoom, no popup).

### P4. Layer toggles: group them, shorten them, stop defaulting an empty layer

- Split the flat checkbox list into two groups with 11 px uppercase
  headers: **Chapter** (Official trail line, Adopted sections,
  Chapter ends, Unadopted gap) and **Context** (Access lines, Roads,
  Asset pins). The current list mixes the chapter's own story with
  reference clutter at one visual level (shots 1–6, left panel).
- Shorten labels that wrap: "Chapter ends (Itasca Moraine west &
  east)" → "Chapter ends"; "Access lines (forest roads, OHV, other
  trails)" → "Access lines" with the detail in a `title` attribute.
- **Asset pins is checked by default but the file doesn't exist** —
  it 404s into the `missingOk` path and shows a permanently
  checked-but-empty layer. Until the first photo batch lands, render
  the toggle disabled with the suffix "(no photos yet)". A control
  that promises data and delivers nothing teaches users to distrust
  the other toggles.
- Row height: current ~24 px rows are fine for mouse; at ≤720 px
  raise to 40 px min-height (see P6).

### P5. Base switcher: undiscoverable icon, over-long names

The Leaflet layers control is a grey stacked-squares glyph with no
label (top-right, all shots) — a first-time beer-night viewer will
never open it, which wastes five good bases. Vanilla-Leaflet-legal
fixes: rename entries short — "Streets (OSM)", "Topo (OpenTopoMap)",
"USGS Topo 1:24k", "Hillshade (MN LiDAR)", "Aerial (USGS NAIP)",
"Aerial (Esri)" — and add a `title` ("Base maps") to the control.
One legibility spec: when an aerial base is active, the section-name
color `#6e4400` on dark imagery is weak; add a body class
(`base-imagery`) toggled from `baselayerchange` that flips
`.section-name-label` and `.terminus-label span` to near-white text
with a dark halo. The halo colors are already centralized in
style.css, so this is ~6 lines.

### P6. Mobile/responsive: the 720 px breakpoint strands the map

Below 720 px the panel becomes a static block and the map gets
70 vh *after* it — so on a phone the entire first screen is notice +
story + Find + eight toggles, and the map (the point of the page)
starts below the fold. Spec: panel `max-height: 38vh` with its own
scroll, map `height: 62vh` (use `100dvh` math so mobile browser
chrome doesn't clip), layer toggles in two columns, toggle rows
≥40 px, Find input 16 px font (prevents iOS focus-zoom). Desktop
meeting use is primary per the brief — this is "don't be broken on
the phone a volunteer pulls out," not a mobile redesign. The
inspector-as-bottom-sheet (Part 1) is what makes selection usable
there at all.

### P7. Print: the handout currently prints without a legend

The print stylesheet hides `#corner-ui` — which contains the only
legend — so the recruiting handout is a bare map plus a panel whose
toggles are also (correctly) hidden. For a paper artifact whose
entire job is a stranger understanding amber vs red at a glance,
that's a fail. Spec: in `@media print`, (a) force-render the legend
card's *content* as a static block under the panel text (clone via
CSS: position static, `hidden` overridden for print only);
(b) keep the adoption bar (P1) — it prints as the headline;
(c) keep Leaflet attribution visible (the current
`.leaflet-control-container { display: none }` removes the OSM
attribution the license requires — hide controls selectively
instead); (d) `@page { size: landscape; margin: 12mm }`, map height
60 vh; (e) if a section is selected, the inspector prints as a
"section card" under the map — this turns the inspector into the
printable per-section sheet the chapter can hand a prospective
adopter, for free.

### P8. Declutter & ticks: right idea, two refinements

The capped, zoom-scaled ticks (segment maxLen 1600 m, terminus
4200 m) and the length-priority declutter are correct in direction —
shot-2 vs shot-1 is a clear improvement, and shot-5's Chip cluster is
readable. Refinements:
- The collision box in `layoutSectionLabels` is centered on the
  anchor, but side labels (`direction: "right"`, offset [10, 0])
  extend entirely to the right of it — their boxes are mis-centered
  by ~(w/2 + 10) px, so right-side labels (West-10, Chip-1, Chip-9…)
  both over-hide and under-hide. Offset the test box by direction
  before comparing.
- Add a floor rule: **no section name hides at z ≥ 12** (at that
  zoom everything fits; the measured z12 run already shows 30/30 —
  make it a guarantee, not an accident of geometry), and at z ≤ 9
  additionally require length ≥ 2 mi so the surviving names are the
  structural ones. GAP-W should *never* carry a section-style name
  label at any zoom — the red dash plus the inspector callout tells
  that story.
- Terminus labels: fine as-is (never hidden, shrink to 10 px). Keep.

### P9. Small code-level items (cheap, do with the rest)

- `gazetteerUi`: Enter currently dispatches a synthetic `mousedown`
  on the first result — replace with the real selection path so
  mouse, keyboard, and touch converge on one function (Part 1).
- Any retained Leaflet popup gets `autoPanPadding: [24, 24]` so
  popups stop kissing the panel edge (shot-3's card touches the
  top-right controls).
- The `.status` line ("Loading …") sits under Layers where nobody
  looks during a layer fetch; move load errors inline to the toggle
  that failed (red 11.5 px text under the row) — status text is
  already routed through `setStatus`, so this is a placement change.
- Title: drop "(working draft)" from the `<h1>` (it reads as a
  warning label in amber); the notice box already carries the draft
  disclaimer, once, in the right register.

## Cut list

1. Sticky full-record hover tooltip + `.section-hover-card` CSS.
2. `stretchPopup` / stretch `bindPopup` (superseded by inspector).
3. Legend's two "Access point" rows (dead layer).
4. "From the west end / From the east end" as top-level card rows
   (demoted to Details, not deleted).
5. Sources-card lines crediting the removed USGS relief and MN
   spring-aerial bases.
6. "(working draft)" in the H1.

## Beautiful vs useful — where they conflict, and my calls

- **Adoption bar + mini-legend (useful) vs panel minimalism
  (beautiful):** useful wins. The panel is a control room, not a
  poster; two compact always-visible story elements cost ~50 px of
  panel height and buy the entire beer-night test.
- **White casing on the selected section (useful) vs the flat,
  quiet linework (beautiful):** useful wins, but only for the
  *selected* section — casing everything would coarsen the map's
  best quality, its restraint.
- **Declutter hiding names (beautiful *and* useful) vs
  completeness (a kind of honesty):** legibility wins; a name that
  overprints its neighbor communicates less than its absence. The
  z ≥ 12 no-hide floor keeps completeness where it fits.
- **Inspector (useful) vs map width (beautiful):** the inspector
  lives in the existing 320 px panel and costs the map nothing. If
  it had required an overlay sheet, beauty would have had a case;
  it doesn't, so it doesn't.

## Suggested build order

1. Selection model + inspector (Part 1), incl. hover-lite chip,
   prev/next, keyboard/touch paths; delete the old hover/popup.
2. Defaults + fitBounds padding + story bar + mini-legend (P1).
3. Legend/Sources corrections (P2) and Find states/rows (P3).
4. Layer grouping/renames, asset-toggle empty state (P4);
   base renames + imagery label class (P5).
5. Print overhaul (P7), mobile breakpoint fixes (P6), declutter
   box-offset fix (P8), small items (P9).

Steps 1–3 are the review's substance; 4–5 are an afternoon of
placement and CSS on top of them.

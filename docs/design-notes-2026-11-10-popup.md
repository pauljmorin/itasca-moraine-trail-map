# Design notes — the pop-up family, redesigned as action surfaces

Interaction-design spec, 2026-11-10. Paul's commission, verbatim:
the pop-up information *"doesn't look good and isn't actionable."*

Companion to `design-notes-2026-11-10-header.md` (palette and voice
discipline — everything here obeys it) and
`cartography-notes-2026-11-10.md`. **A build against the cartography
spec is in flight while this is written** (corridor crop, hover chips
for roads/access per its §2.13, the Places layer per its S4, state
mile markers per its Part 3). This spec assumes that build lands as
spec'd, never contradicts it, and flags every point of contact in §9.
Implementable in plain HTML/CSS/JS in `site/app.js` + `site/style.css`.
No new data, no new colours: every value below is an existing `:root`
token or a literal already in `style.css` (named where used).

**The thesis.** The v4 redesign correctly moved the section record
out of map popups into a persistent panel inspector — but the
inspector was then built as a *report*: a static sheet you read.
Paul's two complaints are the same complaint. It doesn't look good
because everything in it is presented at equal weight in one
undifferentiated column; it isn't actionable because the things a
person actually does with a section — walk to the next one, get in
at an end, jump to its parking, put a brief in an email, print a
handout — are either missing or buried, while the facts that exist
only to be read sit on top. The redesign makes the inspector the
section's **control panel**, demotes the remaining Leaflet popups to
**name tags with one door**, and demotes the hover chip to pure
identification. Three surfaces, three jobs, no duplication.

---

## 0. Diagnosis — what is actually wrong today

Grounded in the current build (`sectionInspectorHtml`,
`gapInspectorHtml`, `renderInspector`, `armChip`/`chipFacts`,
`bindPop` and the five popup builders):

- **The only actions are an afterthought.** The footer's three
  buttons (Zoom / Prev / Next) are the record's entire verb set,
  styled as small pills under a hairline, below two closed folds.
  Nothing else on the card does anything.
- **The most actionable content is the most buried.** "What's here"
  — the section's crossings, parking, water, camping — sits inside a
  closed `<details>`, rendered as semicolon-joined text. The names
  are not clickable, although every one of them is a gazetteer
  feature with geometry the Find box already flies to.
- **The crew leader's first question is a Yes/No in a fold.**
  "Access at start / Access at end" are rows in the closed details,
  answered "Yes" / "No crossing recorded" — although the stretch
  record carries both ends as first-class fields
  (`access_at_start`, `access_at_end`, `both_ends_access`).
- **Help requested is an alarm with no handle.** When the tracker
  flags a section, the card shows the raw value in bold inside a
  red-tinted bar — and then shows it *again* as a details row —
  and offers no next step of any kind.
- **Duplication everywhere.** The caption repeats the key strip
  ("NCT 200.62" above a strip that leads with the NCT range);
  position appears three times (caption, key strip, details rows
  "From the west end" / "From the east end"); help appears twice.
- **The key strip is a grid of equals.** Length, NCT miles, adopter
  and sawyer get identical cells, so nothing leads. Sawyer — often
  null — leaves holes in the grid when absent.
- **The hover chip duplicates the record in miniature** (length +
  first adopter name), so hover and click teach the same facts at
  two sizes, and the chip's real job — *what is this line?* — is
  diluted.
- **The Leaflet popups are five dialects.** The trail popup is an
  eight-row attribute table; the road popup is a bare name or
  nothing; the gazetteer popup is a five-row table; parcels carry
  an owner address. No shared grammar, no shared next step.

---

## 1. The section inspector — the control panel

### 1.1 Anatomy, top to bottom

```
┌──────────────────────────────────────────────┐
│ West-13  [WEST-13]            ( ADOPTED )  × │  header band
├──────────────────────────────────────────────┤
│ ‹ Prev │ Next ›   Zoom to section  Copy brief │  action row
│                                            Print │
├──────────────────────────────────────────────┤
│ 34.21 mi from the west end · 41.94 mi from   │  position line
│ the east end                                 │
│ LENGTH 2.17 mi (tracker 2.25)                │  key strip
│ CHAPTER TRACKER MILES 199.5–201.75           │
│ ADOPTED BY Test adopter 20, Test adopter 21  │
│ Sawyer: Test adopter 49 · Map MN-036         │  crew line
│ Getting in                                   │  access strip
│ WEST END Crossing recorded                   │
│ EAST END Crossing recorded                   │
│ <description prose, clamped with More>       │
│ What's here                                  │  action block
│ Parking (2)  Nicollet Ave · County Rd 4      │
│ Water (1)    Shingobee River                 │
│ …                                            │
│ ▸ Record details                             │  fold
│ From the chapter adoption tracker.           │  provenance
└──────────────────────────────────────────────┘
```

Element by element:

1. **Header band — kept, one change.** `.insp-head` as today
   (title 17px, tracker-code chip, close ×). The ADOPTED pill
   switches to the soft variant that already exists in the CSS and
   is currently never applied (`.insp-pill.adopted.soft` —
   `#e6f4ea` ground, `--trail-deep` text, `#a9c295` border):
   adopted is the normal, good state and should wear the chapter's
   green tint, not a third amber on a card that already has an
   amber left border over an amber map line. UNADOPTED keeps the
   solid `--gap` pill — red is the colour of exception, spent once.
2. **Action row — new, directly under the header band** (§1.2).
   The old `.insp-foot` is abolished; its buttons move here and
   gain company. Provenance takes the footer's place at the bottom.
3. **Position line** — replaces `.insp-caption`; copy pattern in
   §4. The bare "NCT 200.62" point value is cut from it (see §3).
4. **Key strip** — three cells, re-ranked (§3): Length, Chapter
   tracker miles, Adopted by (with Map appended when present).
   Sawyer leaves the grid for a one-line crew line under the strip,
   so its frequent absence stops punching holes.
5. **Ask band** — the help-requested treatment (§1.5), present
   only when the tracker flags the section.
6. **Getting in** — the access strip (§1.4), always visible.
7. **Description** — as today (clamp at three lines, More/Less).
8. **What's here** — out of the fold, always visible, clickable
   (§1.6).
9. **Record details** — the fold, renamed from "Section details",
   holding only what §3 demotes there.
10. **Provenance** — "From the chapter adoption tracker." verbatim,
    unchanged, as the sheet's last line.

### 1.2 The action row — membership, order, exact words, exact behaviour

Five actions survive (§1.7 gives the cuts). Order is meeting
order: walk, frame, share.

| # | Label (exact) | Behaviour (precise) |
|---|---|---|
| 1 | `‹ Prev` | `selectStep(-1)` — existing. Selects the previous walk item by chainage and renders its record. Does **not** pan or zoom the map. Disabled on the first walk item (the gap), as today. |
| 2 | `Next ›` | `selectStep(1)` — existing, mirror of Prev. Disabled on the last item. |
| 3 | `Zoom to section` | `zoomToSelection()` — existing (fitBounds, padding 40, maxZoom 14). On the gap card the label reads `Zoom to the gap` (§2). This is the row's one primary button (§6). |
| 4 | `Copy brief` | Writes the plain-text brief (§1.3) to the clipboard; the button's label becomes `Copied` for two seconds, then reverts. On clipboard failure, the brief is rendered into a temporary selected `<textarea>` for manual copy — never a silent no-op. |
| 5 | `Print` | `window.print()`; the existing print rules already isolate the inspector on its own page — §7 rules govern what of the card prints. |

Prev and Next render as one segmented pair (shared border, outer
corners rounded, no gap between them), then Zoom, then Copy brief
and Print. ←/→ keyboard walking inside the inspector keeps working
exactly as today. Focus after a Prev/Next click stays on the
button, so a keyboard user can keep walking.

### 1.3 Copy brief — the exact template

Plain text, assembled from the record's real fields only. A line
whose fields are empty is omitted, never padded. (Values below are
West-13's real record, shown as the worked example.)

```
West-13 (WEST-13) — Itasca Moraine Chapter
Length 2.17 mi (tracker 2.25) · Chapter tracker miles 199.5–201.75 · 34.21 mi from the west end
Adopted by Test adopter 20, Test adopter 21 · Sawyer Test adopter 49
Access: crossing recorded at the west end; crossing recorded at the east end.
What's here: <kind counts, from the real contents>

Spur 1 to Akeley Cut-Off Rd

From the chapter trail map.
```

The help line joins the template when flagged — `Help requested:
<value verbatim>` after the crew line, e.g. Chip-1's brief carries
`Help requested: 30` and West-3's carries its sentence whole.

Rules: lengths follow the key strip's convention (measured length,
tracker length in parentheses only when they differ); the access
line follows §1.4's copy (for the gap, the §2 template replaces
this one); What's here carries kind counts only — names are one
click in the map, and a brief stays brief. The brief can only ever
contain placeholder adopter names, because the record does.

### 1.4 Getting in — the access strip

The crew leader's first question gets a named block, not a fold
row. Heading: `Getting in` (the house label voice: 10px,
uppercase, letterspaced, `--ink-soft`). Two cells, West end and
East end.

- **Sections** carry boolean end access only, and the copy says
  exactly that much — no invented names:
  - end with a crossing: `Crossing recorded`
  - end without: `No crossing recorded`
  - when `both_ends_access` is false, one line under the cells,
    12px weight 600 `--ink`: `Access at one end only.`
- **The gap** carries named ends (see §2) and uses the full
  `gapEndAccess()` strings verbatim.
- The old details rows "Access at start" / "Access at end" are cut
  (§3) — superseded by this strip.

*Enhancement, explicitly optional and not required by this spec:*
the gazetteer crossings carry a section name and a tracker mile,
and each section record carries its mile range, so the nearest
*named* crossing to each end is derivable at runtime from data the
site already holds. If a later build computes it, the cell value
becomes `Crossing recorded — <name>`; nothing else changes. Do not
ship the strip waiting for it.

### 1.5 Help requested — from alarm to invitation

Diagnosis: the current treatment (red left bar, pink tint, the raw
tracker value in bold, duplicated in the fold) reads as a hazard
warning and terminates in nothing. The value itself is the
tracker's own field with no semantics the site may interpret —
Chip-1's record shows the value `30`; the card renders it verbatim
and must never gloss it as hours, people, or severity.

The field's real values are of two kinds, and the band must hold
both without interpreting either: bare numbers on the Chip
sections (Chip-1: `30`, Chip-13: `44` — a tally in some unit the
site is never told) and sentences where a human wrote one
(West-3: "Requested help with big trees near spider lake";
West-5 and Chip-4: "Need to find a new adopter for 2027" — a
recruiting flag hiding in a help field, and all the more reason
the band ends in a shareable brief). One privacy note: a sentence
value can carry a first name (West-3's ends "Mark E."). It renders
because the tracker is the chapter's own record and the existing
public build already passes this field through — but the builder
verifies that pass-through is unchanged, and any future redaction
decision is Paul's, not this spec's.

New treatment — the **ask band**:

- Full 1px border `#eec5bb` on the `#fdf0ec` tint (both literals
  already in the CSS, from `.insp-gap-callout`), radius 6px — a
  bordered invitation, distinct from the gap standing line's
  left-bar grammar.
- Label line, 10.5px weight 700 uppercase letterspaced, `#b2182b`:
  `Help requested`
- The tracker value beneath it, **verbatim** — number or sentence
  as recorded — at 13.5px weight 650, `--ink` (sentence values set
  at 13px weight 400, line-height 1.45: prose, not a figure). Red
  is spent on the label only; nothing in the band is a solid
  red fill.
- One action, a text-button in `--trail-deep` at the band's foot:
  `Copy a brief for the crew` — it runs the same Copy brief as the
  action row (§1.3), whose template carries the help line. That is
  the escalation the data honestly supports: the flag becomes an
  email-ready ask in one click. The band does not pretend to reach
  anyone — the site holds no contact details, by design, and any
  "notify" or "sign up" control would be theatre.
- The duplicate details row ("Help requested (as recorded in
  tracker)") is cut.

### 1.6 What's here — out of the fold, and every name a door

- The block leaves `<details>` entirely. When the section has
  contents it is always rendered; when it has none it is omitted
  (as today). Heading: `What's here`, house label voice.
- Kind order is action order — arrive, cross, stay, drink, see —
  not alphabetical: Parking, Road crossing, Trail crossing,
  Camping, Water, Shelter, POI, Section boundary, Chapter end.
- Each kind is one row: kind label + count, then its names. **Each
  name is a button** (text-button: `--ink`, no underline at rest,
  underline on hover, `--trail-deep` on focus-visible) whose click
  performs exactly what choosing that feature in Find performs
  today — the `gazSelect()` path: fly to the point (z ≥ 14),
  raise the highlight marker, open its point card (§5). Selecting
  a name does not change the section selection or close the
  inspector.
- Show at most **8 names per kind**, then a plain-text tail
  `and N more` (today's cap is 25 names in a semicolon string —
  the wall of text is part of why the block reads badly).
- Implementation note (flagged again in §9): `gazContents()`
  currently returns name strings only. It must return the feature
  references (or a kind+name → feature map) for the names to be
  buttons. Data already held; this is an app.js change in this
  build, not the cartography build's.

### 1.7 Candidate actions — verdicts

| Candidate | Verdict | Reason |
|---|---|---|
| Walk Prev / Next | **Include** (promoted to the action row) | The meeting gesture — walking the chapter section by section — already exists and was stranded in the footer. |
| Zoom to section | **Include** | Exists; a crew day is planned with the section filling the screen. |
| What's here jumps | **Include** | The data and the fly-to machinery both exist; it converts the card's longest text into its most useful behaviour. |
| Print the record | **Include** | Print CSS already isolates the inspector; the chapter recruits and plans on paper. |
| Copy brief | **Include** | The chapter works by email; today the only way to share a section is a screenshot or retyping. Zero new data (§1.3). |
| Help escalation | **Include**, as the ask band's Copy-brief shortcut (§1.5) | The only honest escalation available: no contact data exists on this site, deliberately. |
| Copy link to this section | **Cut, for now** | The site's hash carries view + layers but has no section parameter or open-handler, so a copied link would land on a map that doesn't show the section — a half-working share is worse than none. Small follow-up (a `#section=` handler), separately built. |
| Directions / open in an external maps app | **Cut** | Implies field use the project has ruled out (home/meeting tool, no field functionality), and hands the chapter's frame to another product. |
| Log work / report a condition / edit the record | **Cut** | No accounts, no backend, by design; volunteer input runs through Paul. Buttons that promise this would be decoration. |
| Adopt this section (a form, on the gap) | **Cut as a form** | No submission route exists on the site. Replaced by Copy the story (§2), which puts the ask in the reader's own email. |

---

## 2. The gap inspector — the recruiting record

GAP-W's card is not a section record with a red pill; it is the
chapter's one recruiting instrument, and its anatomy follows that:

- **Header:** `GAP-W` + solid `--gap` UNADOPTED pill (kept solid —
  this *is* the exception). No tracker-code chip (the gap has
  none; its gazetteer twin is a Section record, but the card
  speaks from the gap feature, as today).
- **Standing line — kept verbatim**, it was already the best copy
  on the card: `No adopter — this is the chapter's recruiting gap.`
  (`.insp-standing`, unchanged.)
- **Action row:** `‹ Prev` (disabled — the gap is the first walk
  item), `Next ›` (→ West-1), primary `Zoom to the gap`,
  `Copy the story`, `Print`. Same row, same grammar as §1.2.
- **Position + key strip:** position line as §4 (`1.46 mi from the
  west end · 74.69 mi from the east end` — the gap's gazetteer
  record carries both). Key strip: Length (`2.92 mi`) and Land
  (`Itasca State Park`) — the park is recruiting context, so Land
  is lead here, unlike sections (§3).
- **Getting in — named, because the gap's data is named.** The two
  cells carry the existing `gapEndAccess()` strings verbatim:
  West end: `No crossing — nearest road: State Highway 113
  (0.78 mi away)`. East end: `Trail crossing: Ozawindib Trail`.
  How a crew — or an adopter — reaches this tread is the gap's
  most persuasive content; it leaves the fold (today's "West end
  access" / "East end access" details rows are cut, superseded).
- **Trails crossing it** becomes part of What's here (§1.5's
  component, fed by `gazContents("GAP-W")`, which the data
  supports): Nicollet Trail, Deer Park Trail, Ozawindib Trail —
  each a clickable jump, as in §1.5. The gap feature's own
  `crossings` list (with its `dist_mi` "x mi in" figures) remains
  the source for the Copy-the-story template below.
- **Record details** fold keeps: Type (`Off-road trail`), Note
  (the feature's `note` verbatim). The internal `classification`
  value (`outside_adopted_span`) is **cut from display** — builder
  jargon, meaningful to no reader.
- **Copy the story** — the gap's brief, exact template (values are
  GAP-W's real record):

```
The chapter's one unadopted stretch: GAP-W — 2.92 mi at the west end
of the Itasca Moraine Chapter line, in Itasca State Park.

West end: No crossing — nearest road: State Highway 113 (0.78 mi away)
East end: Trail crossing: Ozawindib Trail
Trails crossing it: Nicollet Trail (0.3 mi in); Deer Park Trail
(0.78 mi in); Ozawindib Trail (2.91 mi in)

It needs an adopter.
```

  The closing line is the header spec's ask, verbatim — the story
  box, the card, and the email now all end on the same sentence.

---

## 3. Field hierarchy — every field, ranked

Audiences: the **crew leader** planning a work day (access,
length, who holds it, what's there, help) and the **member or
visitor** orienting (where is it, how long, what is it like).
Lead = visible without any fold, in reading order. Supporting =
visible but quiet, or first inside the fold. Folded = in Record
details. Cut = removed from display.

**Section record** (fields as merged by `sectionRecord()`):

| Field | Tier | Notes |
|---|---|---|
| `name` | Lead | Header title. |
| `tracker_section` | Lead | Header code chip. |
| `has_adopter` | Lead | The pill (§1.1). |
| `from_west_mi` | Lead | Position line (§4). |
| `from_east_mi` | Lead | Position line; omitted when absent. |
| `length_mi` | Lead | Key strip, first cell. |
| `tracker_length_mi` | Supporting | Muted parenthesis beside Length, only when it differs — the discrepancy is honesty's, not headline's. |
| `nct_mile_start` / `nct_mile_end` | Lead | Key strip, relabelled "Chapter tracker miles" (§4). Demoted from headline to strip: it is reference data, and its reckoning now needs its label. |
| `nct_mile` (single point) | **Cut** | A centroid artefact; the range carries the information. Its caption appearance today duplicates the strip. |
| `adopter_display` | Lead | Key strip "Adopted by" — placeholders only, as always. |
| `map_refs` | Supporting | Appended to the Adopted-by cell as "· Map <refs>" — wait, no: its own quiet line under the strip with the crew line. Paper-map reference matters to crew leaders, not to orientation. |
| `sawyer_display` | Supporting | Crew line under the key strip: `Sawyer: <names>`. Off the grid (§0). |
| `help_requested` | Lead, when present | The ask band (§1.5). When absent, nothing renders — no "no help requested" filler. |
| `description` | Lead | Body prose, clamped with More, as today. |
| `access_at_start` / `access_at_end` / `both_ends_access` | Lead | The Getting-in strip (§1.4). |
| What's-here contents | Lead | §1.5. |
| `land_context` | Supporting | First row of Record details ("Land"). For the gap it is lead (§2) — the park is the story there; for a section it is context. |
| `maintenance_2026` | Supporting | Record details, "2026 maintenance". The crew leader's second question — but dated and episodic, so folded, not lead. |
| `comments` | Supporting | Record details, "Tracker comments". |
| `comments_dropped` | Supporting | The existing "Withheld from the public map" note stays as the comments row's value — the honesty is the point. |
| Help row duplicated in details | **Cut** | Same fact twice (§1.5). |
| "Access at start/end" details rows | **Cut** | Superseded by the strip. |
| "From the west/east end" details rows | **Cut** | Superseded by the position line. |
| Provenance ("From the chapter adoption tracker.") | Supporting | Last line of the sheet, verbatim. |
| `chainage_*` | Never displayed | Internal walking order; its display form is `from_west_mi`. |

**Gap record** (fields from the gap feature):

| Field | Tier | Notes |
|---|---|---|
| `gap_id` | Lead | Header title. |
| Standing line | Lead | Verbatim (§2). |
| `length_mi` | Lead | Key strip. |
| `land_context` | Lead | Key strip ("Land"). |
| `name` (description text) | Lead | Body prose, as today. |
| `nearest_access_*` / `nearest_road_*` | Lead | Getting-in cells via `gapEndAccess()` verbatim. |
| `crossings` | Lead | What's here / Copy-the-story (§2). |
| `trail_stat` | Supporting | Record details, "Type". |
| `note` | Supporting | Record details, "Note". |
| `classification` | **Cut** | Internal builder vocabulary. |

---

## 4. Copy patterns — final wording

All on-card prose follows these patterns exactly. No bullets in
any on-map copy; lists below are spec apparatus.

- **Position line (sections and gap):**
  `{from_west_mi} mi from the west end · {from_east_mi} mi from the east end`
  — each half omitted when its value is absent; no line at all
  when both are. (This position is the chainage measure — miles
  along the depicted chain from the chapter's west end — and needs
  no reckoning label: it is the map's own ruler, per the
  cartography spec's S1 discipline.)
- **Mileage caption (the M3 relabel).** Wherever tracker mileage
  is stated, it is labelled as the tracker's:
  - Key-strip label: `Chapter tracker miles`; value: `199.5–201.75`.
  - Find result sub-line (`gazResultSub`): `Tracker miles 199.5–201.75`
    (replaces today's bare `NCT 199.5–201.75`).
  - Gazetteer point card row label: `Chapter tracker mile`
    (replaces `NCT mile`).
  - The words "NCT mile" unqualified disappear from inspector and
    gazetteer surfaces: with the state mile-marker layer on the
    map, an unlabelled "NCT" number is now genuinely ambiguous.
    The state reckoning is never stated in the inspector at all —
    it lives on the face, in its own labelled layer (cartography
    M3). No conversion or offset figure is computed or shown.
- **Key-strip labels:** `Length`, `Chapter tracker miles`,
  `Adopted by`. Length value: `2.17 mi`, plus muted
  `(tracker 2.25)` when the tracker length differs.
- **Crew line:** `Sawyer: {names}` and, when map refs exist, the
  same line continues ` · Map {refs joined ", "}` — one quiet line
  for the two reference facts. (Supersedes §3's table entry: refs
  ride the crew line, not the Adopted-by cell.)
- **Getting in:** heading `Getting in`; end labels `West end`,
  `East end`; section values `Crossing recorded` /
  `No crossing recorded`; one-end note `Access at one end only.`;
  gap values are the `gapEndAccess()` strings verbatim.
- **What's here:** heading `What's here`; tail `and N more`.
- **Help band:** label `Help requested`; value verbatim; action
  `Copy a brief for the crew`.
- **Buttons:** `‹ Prev`, `Next ›`, `Zoom to section` /
  `Zoom to the gap`, `Copy brief` / `Copy the story`, `Print`,
  transient `Copied`.
- **Fold summary:** `Record details` (sections), `Gap details`
  (gap, as today).
- **Empty state:** copy unchanged — `Select a section: click the
  amber line, or find it above. ← → walk the trail.` plus the gap
  callout button `Unadopted: GAP-W, 2.9 mi — Itasca State Park`.
  Only its styling is unified (§6).
- **Provenance:** `From the chapter adoption tracker.` — one line
  for sections and gap alike, as today.

---

## 5. The Leaflet popups — one system: the name tag

**The v4 decision stands.** Sections and the gap have no map
popups; the persistent inspector is their record, because a popup
that vanishes when the mouse moves cannot hold a record a crew
plans from. Nothing in this spec reopens that.

Everything else that still pops up gets **one grammar — the name
tag**: a title line, at most three fact rows, and, where the thing
belongs to a section, **one door**. A popup identifies and points;
it never documents.

The door, where it applies: a text-button as the popup's last
line, `Open {Section} record`, whose click closes the popup and
runs the existing section-selection path for that section (the
same `walkByName` lookup Find uses). It applies to gazetteer point
cards whose `section` names a section, and to nothing else —
parcels, roads, access lines and the trail have no section record
to open.

Per surface:

- **Official trail line** (`trailPopup`, today eight rows).
  Title: segment name or `North Country Trail`. Rows: Chapter;
  Type (off-road / on-road). **Cut:** Certification, Ownership,
  Managing authority, Surface, Closure, Length — the full
  attribute set lives in the source data and SOURCES.md; a click
  on the line is an identification, and five of those rows are
  null on most segments anyway, so the popup mostly performed
  emptiness. No door.
- **Parcels** (`parcelPopup`). Title: `Parcel {parcel_id}`. Rows:
  County, Land class, Acres, Owner. The public-record note stays
  verbatim — it is the licence for the owner row's presence.
  **Cut:** Owner address (the name identifies the parcel for
  chapter work; the address is working-data detail) and the
  "Trail corridor" row (crossed-vs-adjoining is already the
  parcel's fill — saying it again in text is the §0 disease).
  No door. (The layer is currently UI-disabled; this is the
  grammar it returns with.)
- **Non-road access** (`accessPopup`). Title: name, or the kind
  label. Rows: Kind; Length. **Cut:** Source (dataset credit
  belongs to the Sources card) and Class. When the feature
  carries the cartography build's `cut` flag, one added line,
  matching the hover chip's sentence (§9, F2): `Continues beyond
  the corridor`. No door.
- **Roads** (`roadPopup`). Today: a name, or no popup at all for
  unnamed roads — **keep exactly that**; it is already a name tag.
  One optional row when the cartography build's class is present:
  `Class`, displayed with words, not letters — Arterial / Local /
  Minor / Forest road (fallback wording; if the cartography build
  defines class display names for its legend, use those verbatim —
  §9, F5). Plus the corridor line when `cut`. No door.
- **Gazetteer points** (`gazPopupHtml`, reached from Find and,
  after the cartography build, from the Places layer). Title:
  the place name. Rows: Kind; `Chapter tracker mile` (§4);
  Section — as the door, not a row, when it names one; From the
  west end. **Cut:** From the east end (redundant beside west +
  the section's own position line). Kept: the off-chain caveat
  verbatim (it is a real warning about the point's position) and
  Description. This card is also the target of every What's-here
  name click (§1.6) — one card, three entrances.
- **Asset pins** (`assetPopup`). Title: the asset type. Rows:
  Condition; Photographed. **Cut:** Photographer — a person's
  name has no business on a public popup, and the placeholder
  discipline that governs adopters governs here too. No door.

**Popup styling** adopts the panel voice (§6): wrapper radius
10px, `--paper-line` border, title 15px weight 600 `--ink`, row
keys in the house label voice (10.5px uppercase `--ink-soft`),
`maxWidth` 300 (from 340 — a popup wider than the 320px panel
looks lost beside it). The `bindPop` guard (70vh internal scroll,
auto-pan padding) is unchanged.

---

## 6. The look

The record sheet's bones were right (white sheet, tinted head,
amber spine); the failure was flatness below the head. The moves,
all within the existing tokens:

- **Ruled blocks.** The body becomes a sequence of blocks
  separated by the hairline literal already in the CSS (`#eee7d2`,
  from `.insp-details` / `.insp-foot`): action row, key strip,
  Getting in, What's here, fold. Structure you can see is what
  "looks good" means on a 288px-wide card — not decoration.
- **One primary button.** In the action row, Zoom wears
  `--trail-deep` with white text; every other button wears the
  house pill (paper ground, 1px `#a89a5b` border, radius 14px,
  0.83rem — the current `.insp-foot button`, reused). One dark
  button per card; the eye lands on it first, which is correct —
  framing the section is the most common next act.
- **Action row surface:** `--paper` ground, 7px 11px padding,
  hairline beneath; buttons wrap to a second line rather than
  shrinking (walk pair + Zoom, then Copy + Print).
- **Type scale.** Title 18px weight 650 (from 17/600 — the name
  is the card's headline and should carry it). Position line 11px
  `--ink-soft`. Key values 14px weight 650; key labels unchanged
  (10px uppercase `--ink-soft`). Crew line 12px `--ink-soft` with
  names in `--ink`. Body prose 13px / 1.45 (unchanged). What's-here
  names 13px. Fold summary 12.5px / 600 (unchanged). Provenance
  10.5px italic `--ink-soft` (unchanged).
- **Spacing rhythm.** Body padding 10px 12px 12px; blocks
  separated by 10px and a hairline, not by floating margins of
  varying sizes (today's 7px/8px mix is a quiet source of the
  "doesn't look good").
- **Getting-in cells:** `--paper` ground, radius 6px, padding
  7px 9px; end label in the house label voice; value 12.5px
  weight 550. The one-end note is weight 600 `--ink` — a planning
  constraint, stated plainly, in no alarm colour.
- **Ask band:** per §1.5 — bordered invitation, red spent on its
  label only.
- **Empty state:** the gap callout button adopts the ask band's
  grammar (full `#eec5bb` border on `#fdf0ec`, radius 6px) so the
  panel's two red-tinted surfaces — the empty state's callout and
  the help band — read as one family: *things that need someone*.
- **Hover chip** (§7): visuals unchanged (white, radius 8px, the
  existing shadow); only its content changes.

---

## 7. The hover chip — keep, and demote its content

**Verdict: keep.** The cartography spec (§2.13) also keeps it and
extends the same dwell chip to roads and access lines; this spec
does not contradict that — the road/access chips carry name +
class (+ the corridor sentence), which *is* identification, and
they are already right.

For sections and the gap, the chip stops summarising the record:

- Line 1: name + tracker code, as today.
- Line 2 (the only fact line): `{length} mi · starts {chainage} mi
  from the west end` — both values from the stretch feature's own
  properties (`length_mi`, `chainage_start_mi`), preserving the
  current build's guarantee that chip content is fixed at hover
  time and can never swap mid-hover. For the gap: `2.92 mi ·
  Unadopted`, as today.
- **Cut from the chip:** the adopter name. It is a record fact,
  and its presence is what makes the chip a miniature of the
  inspector rather than a label for the line.
- Hint line: `Click to open the record` (was "Click for the full
  record" — shorter, verb-led, and now literally true: the click
  opens the control panel).

The relationship, stated once and applied everywhere: **the chip
identifies (what is this?), the inspector acts (what do I do with
it?)**. No fact leads in both places except the name and the
length.

---

## 8. Mobile and print

**Mobile (inspector = bottom sheet, ≤45vh, ≤720px).** The sheet
is short; the actions must not scroll away inside it.

- Internal order in the sheet: header band, action row, ask band
  (when present), then the scrollable rest.
- `.insp-actions` becomes `position: sticky; top: 0` *within the
  sheet* at ≤720px only (paper ground, its hairline, z-index
  above the body blocks), so Prev / Next / Zoom stay under the
  thumb while the record scrolls beneath. Desktop needs no sticky
  — the whole panel scrolls.
- All action-row buttons take `min-height: 40px` on coarse
  pointers, matching the layer toggles' existing rule. Labels
  never shorten; the row wraps (§6).
- Getting-in cells stack vertically (one column) in the sheet.

**Print (the record as a handout).** The inspector already prints
as its own page after the map; these rules govern the card itself:

- Prints: the print masthead (page context, per the header
  spec), header band (with `print-color-adjust: exact` on the
  band and pill, extending the story box's existing rule),
  position line, key strip, crew line, ask band when present —
  on paper the ask is the handout's point — description **in
  full** (print CSS unclamps `.insp-desc.clamped`), Getting in,
  What's here as plain text (names render as text; buttons lose
  all button styling), provenance.
- The Record-details fold **does not print**: closed `<details>`
  content prints unreliably across browsers, and a handout that
  sometimes includes the maintenance notes is worse than one that
  never does. In its place, one print-only line after What's
  here: `Maintenance notes and tracker comments are in the chapter
  adoption tracker.`
- Never prints: the action row (buttons are screen furniture),
  the close ×, the Copied state, hover anything.
- The **gap handout** is a recruiting leaflet and prints one extra
  line under the standing line, the header spec's ask verbatim:
  `It needs an adopter.` Plus Getting in and the crossings — the
  three things a prospective adopter asks about first.

---

## 9. Coordination flags — the in-flight cartography build

- **F1 — the M3 caption relabel is assigned twice.** The
  cartography spec's Part 5, item 6 gives its build "the inspector
  caption source label." This spec's §4 supersedes the bare caption
  with the full position-line pattern and the "Chapter tracker
  miles" key-strip label. If the cartography build lands its
  one-word label first, this build replaces it; whoever lands
  second owns the caption. Do not implement both.
- **F2 — road/access hover chips are cartography scope** (its
  §2.13: name + class + "continues beyond the corridor"). This
  spec's §5 popup grammar uses the same corridor sentence so chip
  and popup agree. No cartography change needed.
- **F3 — Places-layer popups inherit §5 automatically.** The
  cartography spec (S4) has Places popups "reuse the gazetteer
  record" — i.e. `gazPopupHtml()`. This spec's revision of that
  one function covers Find, What's-here jumps, and Places alike.
  No cartography change needed.
- **F4 — `gazContents()` must return feature references** for
  §1.6's clickable names (it returns strings today). An app.js
  change in *this* build; the cartography build does not touch
  that function to this spec's knowledge — if it does, this build
  adapts to its shape.
- **F5 — road-class display names.** §5's Arterial / Local /
  Minor / Forest road are fallbacks. If the cartography build's
  generated legend defines display names for classes A/B/C/F, use
  those verbatim — the legend-follows-constants rule outranks
  this note.
- **F6 — the selection halo is cartography scope** (its §2.13
  restyle: own-style core at weight +2, casing w10 at 0.9). This
  spec does not touch `drawSelectionHalo()`.

---

## 10. Implementation checklist (for the builder)

- `app.js`: restructure `sectionInspectorHtml()` per §1.1 (action
  row replaces `inspectorFoot()`; position line per §4; key strip
  re-ranked; crew line; ask band; Getting-in strip; What's here
  always-visible with name buttons); parallel restructure of
  `gapInspectorHtml()` per §2; `wireInspector()` gains the Print
  and Copy handlers (one shared copy routine, two templates);
  `gazContents()` returns feature references; `chipFacts()`
  per §7; popup builders per §5 (`trailPopup`, `parcelPopup`,
  `accessPopup`, `roadPopup`, `assetPopup`, `gazPopupHtml`) plus
  the `Open {Section} record` door wiring; `gazResultSub()` and
  the point-card row label per §4.
- `style.css`: `.insp-actions` (+ segmented Prev/Next, one primary
  button), `.insp-access` cells, ask-band rules, What's-here rows
  and name buttons, ruled-block hairlines, adopted pill → soft
  variant (a class change in the builder function, CSS exists),
  empty-state callout unification, popup voice (`maxWidth` is a
  `bindPop` argument in JS), mobile sticky action row + 40px
  targets, print rules per §8.
- Nothing in `index.html` or the data build changes.

**Acceptance check (the work-day test).** A crew leader opens a
section and, without opening a single fold, can say how long it
is, where it sits, who holds it, how to get in at both ends, and
what is there — and can put a brief in an email, or a handout in
a hand, in one click each. A visitor opens the gap and can repeat
the recruiting story — and copy it, word for word, into their own
email. A stranger hovering any line on the map learns its name
and nothing they will have to relearn on click.

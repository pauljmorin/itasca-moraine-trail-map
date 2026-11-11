# Design notes — the hover chip, rebuilt as the triage surface

Interaction-design spec and build record, 2026-11-11. Paul's
commission, verbatim, over a screenshot of the current chip: *"see
this bubble popup? I want to fix this and make it useful. can you
pass this by a UI and designer?"*

Companion to `design-notes-2026-11-10-popup.md` (the pop-up family
spec — its §7 already demoted this chip to pure identification) and
`design-notes-2026-11-10-header.md` (palette and voice discipline —
everything here obeys it). Every value below is an existing `:root`
token or a literal already in `style.css` (named where used). No
new data is invented anywhere in this spec: every fact the chip
shows is read from fields that exist today, and §3 names the source
field for each one.

**Standing alongside two neighbours.** The Nov 10 spec ruled three
surfaces, three jobs: the chip identifies, the inspector acts, the
Leaflet popups are name tags. This spec **extends the chip's job by
one step, deliberately**: from pure identification to identification
+ *triage*. The argument is in §2.1; nothing else in the Nov 10
doctrine is reopened, and the inspector is not duplicated.

---

## 0. Diagnosis — why the current chip fails

Grounded in the current build (`armChip` / `chipFacts` in
`site/app.js`, `.hover-chip` in `site/style.css`) and in Paul's
screenshot, which is the failure rendered exactly: a chip about
60 px wide and 270 px tall for West-13, its text exploded into a
vertical ribbon — "West- / 13 · / WEST- / 13 / 2.17 / mi · / starts /
33.12 / mi / from / the / west / end".

- **The ribbon is structural, not a width typo.** Leaflet tooltips
  size to their content. The chip's HTML is inline spans; the name
  span and the `· WEST-13` code span are one unbreakable run with no
  block structure, and `.hc-facts` is a block whose text is free to
  wrap at any word. With `max-width: 280px` as the only sizing rule
  and `white-space: normal` everywhere, the tooltip shrink-wraps to
  the narrowest width its longest unbreakable fragment allows and
  then wraps everything else under it. `max-width` caps a chip; it
  cannot set a floor. Nothing in the current CSS ever asks the chip
  to be wide, so it isn't.
- **The name is said twice.** Title = display name + tracker code
  ("West-13 · WEST-13") — the same name in two casings, spending the
  chip's loudest line on zero new information. In the inspector the
  code earns its chip (it is the cross-reference key to the printed
  tracker and the NCTA sheets); at hover distance it is a duplicate.
- **No status signal.** The chip cannot say the one thing a manager
  scanning the line most needs at hover distance: is this section
  held, and has it asked for help? Adoption lives only in the line's
  colour (which a volunteer reading a monochrome relief base, or a
  colour-blind reader, may not get) and help lives only inside the
  inspector, behind a click. Fourteen of the 32 tracker sections
  carry a help request in the gazetteer today; at hover, all of
  them look identical to a quiet section.
- **The facts are the record's leftovers, not a triage set.**
  "2.17 mi · starts 33.12 mi from the west end" is one long prose
  string — the words "starts … from the west end" cost nine wrapped
  lines in the screenshot to say what "mi 33.1–35.3" says in one.
  Meanwhile the two facts a crew leader actually triages on —
  can I get in at the ends, and what is this stretch *called* on
  the ground (its tracker description: "The Blowdown to Spider Lake
  Rd", "Spur 1 to Akeley Cut-Off Rd") — are absent, although both
  exist in data the site already holds.
- **Dead space and flat hierarchy.** Name, code, facts and hint sit
  at near-equal weight in one column; the eye gets no first thing.
  The hint ("Click to open the record") is a fourth line buying
  nothing after the first hover — the click affordance is taught by
  the line's own hover highlight, and the sentence costs a line of
  ribbon in every chip forever.

---

## 1. The redesign at a glance

```
┌───────────────────────────────────────────────┐
│ West-13                              ● Adopted │
│ Spur 1 to Akeley Cut-Off Rd                    │
│ 2.17 mi · mi 33.1–35.3 · access both ends      │
└───────────────────────────────────────────────┘
```

```
┌───────────────────────────────────────────────┐
│ West-3                          ● Help requested│
│ The Blowdown to Spider Lake Rd                 │
│ 1.9 mi · mi 6.5–8.4 · access one end only      │
└───────────────────────────────────────────────┘
```

```
┌───────────────────────────────────────────────┐
│ GAP-W                             ● Not adopted │
│ Itasca State Park                              │
│ 2.92 mi · the chapter's recruiting gap         │
└───────────────────────────────────────────────┘
```

Three lines, one job each:

1. **Head row** — the name (bold) and, at the row's right edge, the
   status pill. Name left, verdict right: the two things the eye
   wants, in the order it wants them.
2. **Identity line** — what the stretch *is* in words: the tracker's
   own description for a section, the land context for the gap.
   This is the line that turns a code on a line into a place.
3. **Facts row** — three short tokens, middot-joined, each one
   `nowrap`: length, position as a mile range, access verdict.
   Triage data, in the most compressed honest form.

Below: each ruling argued (§2), every fact sourced (§3), the exact
spec (§4), what was rejected (§5), and the build/verification
record (§6).

---

## 2. Rulings on the five design questions

### 2.1 The job of the chip — identification + triage (a deliberate extension of Nov 10 §7)

The Nov 10 spec demoted the chip to pure identification to stop it
duplicating the inspector. That diagnosis was right and its cure
overshot: it cut the adopter *name* (correct — a record fact, and a
placeholder at that) but left the chip unable to carry *status*,
which is not a record fact — it is the line's condition, the same
class of information as the line's own colour. A map whose amber
means "adopted" already states status at hover distance; the chip
merely says it in words for the readers and bases the colour
doesn't reach. **Ruling: the chip identifies and triages. It still
never documents**: no adopter names, no sawyer, no tracker-mile
range, no sheet numbers, no maintenance prose, no help *text* —
the flag, never the file. The Nov 10 acceptance sentence survives
with one clause changed: a stranger hovering any line learns its
name, **whether it is held and whether it is asking**, and nothing
they will have to relearn on click.

### 2.2 One name — the display name wins; the tracker code leaves the chip

**Ruling: the title is `name` alone** ("West-13"). The tracker code
("WEST-13") is a casing variant, not a second name: it differs from
the display name only in case and hyphen styling, and every surface
that needs the join key already has it — the inspector's header
code chip (kept, Nov 10 §1.1), the Find results, the brief. Keeping
it in the chip bought nothing and broke the title line's width.
The gap's title is its `gap_id` ("GAP-W"), as today — the gap has
no tracker code and its long descriptive `name` ("West end —
chapter line west of West-1") is demoted to a record fact; the
gap's identity line is its land context instead (§3).

### 2.3 Status — a pill, in the inspector's exact vocabulary

**Ruling: a status pill rides the head row**, using the site's
existing pill grammar — the `.insp-pill` voice (10.5px, weight 700,
uppercase, letterspaced, 999px radius) refactored onto a shared
`.status-pill` base so chip and inspector can never drift apart:

| State | Pill | Colours (existing tokens/literals) |
|---|---|---|
| Adopted, no help flag | `Adopted` | `.adopted.soft`: `#e6f4ea` ground, `--trail-deep` text, `#a9c295` border — the normal, good state wears the chapter's green tint |
| Adopted, help flag set | `Help requested` | `#fdf0ec` ground, `#b2182b` text, `#eec5bb` border — the ask band's exact colours (Nov 10 §1.5): a bordered invitation, red spent on words, never a fill |
| Gap | `Not adopted` | `.unadopted`: solid `--gap` red, white text — the exception, spent once, as in the inspector |

Priority is help over adopted: a section that is held *and* asking
shows the ask — that is the triage fact. The pill is `nowrap` and
never wraps; it is the chip's right anchor.

*Data honesty, stated plainly:* adoption (`has_adopter`) and the
end-access booleans are the **stretch feature's own properties**,
so they obey the chip's standing guarantee — content fixed at hover
time, built only from the hovered feature, never swapping
mid-hover. The help flag and the description live only in the
**gazetteer** record, so the chip takes them through the same
merge the inspector uses (`sectionRecord()`), read once at arm
time. Consequence, accepted and bounded: before the gazetteer
finishes loading, a chip can show `Adopted` where it will later
show `Help requested`, and no description line. The chip never
shows anything *false* in that window (the section is adopted);
it shows less. The alternative — delaying every chip until the
gazetteer lands — punishes the common hover for a load race that
resolves in a second. Documented here so the behaviour is a
decision, not a surprise.

### 2.4 Which facts earn hover distance

**Ruling: three facts, and only three** — each must answer a
triage question in under a second:

| Fact | Triage question | Form | Source field |
|---|---|---|---|
| Length | How much trail is this? | `2.17 mi` | stretch `length_mi` |
| Position | Where along the chapter? | `mi 33.1–35.3` — the section's own chainage span, one decimal | stretch `chainage_start_mi` / `chainage_end_mi` |
| Access verdict | Can a crew get in? | `access both ends` / `access one end only` / `no end access recorded` | stretch `access_at_start` / `access_at_end` / `both_ends_access` |

The position range replaces the old "starts 33.12 mi from the west
end" outright: "starts" said where a section begins but never
where it ends, in eleven words; the range says both in eight
characters. Chainage is the map's own ruler (Nov 10 §4) and needs
no reckoning label; it is **not** tracker miles and **not** NCTA
miles, and the chip never states either — both live, labelled, in
the inspector.

**Belongs to the click record, and stays there** (the Nov 10 §3
hierarchy is untouched): tracker-mile range, adopter and sawyer
names, NCTA sheet numbers, maintenance, tracker comments, the help
*value* (the chip carries the flag only — the value is verbatim
tracker text, sometimes a sentence, once a partial name; a hover
surface is not where it gets quoted), the description's full prose
(the chip takes it whole only because tracker descriptions are
short names, not prose — see §3), and What's here.

**Gap facts** (same grammar, gap data): length (`2.92 mi`), then
the standing line's short form `the chapter's recruiting gap` —
the one fact about GAP-W that outranks position. Its chainage
range (0–2.92) is trivially the west end and is omitted; its
nearest-road detail is named data and belongs to the record
(Nov 10 §2), not the hover.

### 2.5 No action in the chip — `pointer-events: none` stands

**Ruling: the chip gains no action and stays non-interactive.**
Argued, because the triage framing makes the temptation real (a
"zoom" or "copy brief" button in the chip would *feel* useful):

- The click already exists and is one millimetre away: the whole
  line under the chip is the button, with its own hover highlight.
  An action inside the chip duplicates the door it floats over.
- Interactivity costs the chip its two best properties. A
  `pointer-events: auto` tooltip captures the mouse: moving toward
  the button crosses the line's mouseout boundary, so the chip must
  grow hover-intent timers, a grace corridor, and close delays —
  the exact churn machinery the static chip was built to avoid
  (v3's cursor-following card died of it). Every future chip
  inherits that complexity.
- It breaks the audience contract: touch never sees the chip at
  all, so any action placed only in the chip is an action touch
  users can never take. Actions belong where all three audiences
  can reach them — the inspector.
- The hint line goes with the actions: **cut**. "Click to open the
  record" was the chip apologising for existing. The hover
  highlight on the line plus the universal cursor is the teaching;
  the sentence cost a wrapped line in every chip.

### 2.6 Dwell and placement — both kept, and why

- **Dwell: 300 ms, kept.** Shorter raises chips during ordinary
  pans-across-the-line; longer makes identification feel broken.
  300 ms is also the context chips' dwell — one hover rhythm for
  the whole map.
- **Placement: `direction: "top"`, offset `[0, -10]`, kept.** The
  chip floats above the hover point, clear of the line being read;
  Leaflet flips it at the viewport edge itself. The wider chip
  (§4) makes the top placement more important, not less — a
  side-placed 230px chip would cover the neighbouring sections a
  manager is comparing.
- **Static, never cursor-following; closes on map move/zoom; never
  on coarse pointers** — all kept, unchanged (Nov 10 §7 doctrine,
  and the mechanism that keeps `armChip`'s content guarantee true).

---

## 3. Content spec — every element, sourced

Section chip, in order:

| Element | Content | Source |
|---|---|---|
| Title | `name` | stretch properties |
| Pill | per §2.3 | `has_adopter` (stretch) + `help_requested` non-empty (gazetteer, via `sectionRecord()`) |
| Identity line | `description`, whole, verbatim | gazetteer (`gz.description`) — tracker descriptions are short ground-names ("Spur 1 to Akeley Cut-Off Rd"); the line is single-line ellipsised by CSS at the chip's max width, so a long one degrades to a clipped name, never a ribbon |
| Facts row | length · chainage range · access verdict, per §2.4; each token omitted when its fields are absent, the row omitted when empty | stretch properties only |

Gap chip:

| Element | Content | Source |
|---|---|---|
| Title | `gap_id` | gap properties |
| Pill | `Not adopted` | — |
| Identity line | `land_context` ("Itasca State Park") | gap properties |
| Facts row | length · `the chapter's recruiting gap` | gap properties |

Context chips (roads, non-road access) are **unchanged in
content** — name + class (+ corridor sentence) is identification,
and Nov 10 §7 already ruled them right. They inherit only the
§4 geometry fix, because they share the `.hover-chip` class and
today they ribbon the same way.

---

## 4. Geometry and style spec

The fix, in one sentence: **the chip gets a floor as well as a
ceiling, block structure instead of inline flow, and `nowrap` on
everything that must not break.**

- `.leaflet-tooltip.hover-chip`: `min-width: 190px`,
  `max-width: 300px`, padding `7px 10px 8px`, radius 8px, the
  existing paper/border/shadow — visuals otherwise unchanged
  (Nov 10 §7: "visuals unchanged; only its content changes" —
  this build changes content *and* sizing, so the deviation is
  recorded here: the sizing was the bug).
- Head row is a flex row (`display: flex; align-items: baseline;
  gap: 8px`): `.hc-name` (14px, weight 650, `nowrap`, ellipsis)
  grows, `.status-pill` (shared base, §2.3) sits right, `nowrap`,
  `flex: 0 0 auto`.
- `.hc-sub` (identity line): block, 12px, `--ink-soft`,
  `white-space: nowrap; overflow: hidden; text-overflow:
  ellipsis` — one line, clipped, never wrapped.
- `.hc-facts`: block, 12px, margin-top 2px; its tokens are
  `.hc-fact { white-space: nowrap; }` spans joined by `" · "`
  text nodes. The row may wrap *between* tokens at the 300px
  ceiling on a narrow map pane; a token itself never breaks.
- `.hc-code` and `.hc-hint` rules are deleted with their markup.
- Expected geometry (measured in §6): a section chip lands around
  **225–260 px wide × 58–66 px tall** — the inverse of the
  screenshot's 60 × 270.

Implementation: `app.js` — `chipFacts()` becomes a token-array
builder shared by section and gap (returning `{text}` tokens, not
a prose string), `armChip()` builds the three-line HTML via the
merged record for status/description and stretch properties for
facts; `armContextChip()` keeps its content and only emits token
spans. `style.css` — the `.hover-chip` block above, plus the
`.status-pill` shared base extracted from `.insp-pill` (the
inspector's classes are untouched: `.insp-pill` keeps its layout
margin and gains the shared visual properties by selector grouping,
so the inspector renders identically).

---

## 5. Rejected

| Candidate | Verdict | Reason |
|---|---|---|
| Adopter name in the chip | **Cut** (again) | Nov 10 §7's cut stands: a record fact, and a placeholder string at that; status carries the triage value without it. |
| Help *value* quoted in the chip | **Cut** | Verbatim tracker text — sometimes a sentence, once carrying a partial personal name ("Mark E."). The flag triages; the record quotes. (§2.4) |
| Tracker code beside the name | **Cut** | §2.2 — a casing duplicate at hover distance. |
| NCTA sheet number in the chip | **Cut** | Tempting after the sheets build (the field is on the stretch feature), but a sheet number answers "which printed map", a planning question — the click record carries it, with its link. Hover carries triage only. |
| Position as "starts X mi from the west end" | **Cut** | §2.4 — the range says more in fewer characters. |
| One action in the chip (zoom / copy) | **Cut** | §2.5 — capture, churn, and the touch contract. |
| Cursor-following chip | **Cut** (again) | v3's card died of it; static placement is doctrine. |
| Widening to `max-width` only / removing the cap | **Cut** | The ribbon's cause is the missing floor and inline flow, not the ceiling; an uncapped chip would sprawl across neighbours on long descriptions. |
| Per-kind chip colours (amber chip for adopted, red for gap) | **Cut** | The paper face is the site's label voice on every base including imagery; status colour is spent once, on the pill. A tinted chip would fight the line it labels. |

---

## 6. Build and verification record

Built 2026-11-11 against this spec. Measured headlessly
(chromium headless shell, CDP): the site's real layers were armed
through their own `mouseover` handlers and the production 300 ms
dwell — the feature layers render on a shared canvas, so an
OS-level synthetic mousemove has no per-feature DOM target; the
dwell, merge, tooltip and CSS under test are the production code
unchanged. Three chips measured (bounding box of the rendered
`.hover-chip` element):

| Chip | Before | After | Content as rendered |
|---|---|---|---|
| West-13 (adopted) | ~60 × 270 px (Paul's screenshot) | **246 × 74 px** | `West-13` + Adopted pill · "Spur 1 to Akeley Cut-Off Rd" · `2.17 mi · mi 33.1–35.3 · access both ends` |
| West-3 (help flag) | — | **241 × 74 px** | `West-3` + Help requested pill · "The Blowdown to Spider Lake Rd" · `1.9 mi · mi 6.5–8.4 · access one end only` |
| GAP-W | — | **216 × 73 px** | `GAP-W` + Not adopted pill · "Itasca State Park" · `2.92 mi · the chapter's recruiting gap` |

Assertions, all from the rendered DOM: no chip title contains a
tracker code (the duplicated name is gone); status pill present
in all three states (adopted / help / not adopted); every facts
row is a single line (17 px height — nothing wraps inside a
token); the chip stays `pointer-events: none`.

One build finding worth its line: **floor + ceiling alone did not
fix the width.** Leaflet positions a tooltip by setting
`left`/`top` on an absolutely positioned element whose containing
block shrink-wraps, so with only `min-width`/`max-width` the chip
still sized to the floor (212 px) and wrapped the facts row. The
working fix is `width: max-content` between the floor and the
ceiling — the chip sizes to its widest unwrapped line, bounded
both ways. It is commented as load-bearing in the CSS so a future
cleanup doesn't remove it as decoration.

Proof screenshots: `docs/proof-2026-11-11/hover-chip-west13.png`
and `hover-chip-west3-help.png` (grey field behind the chip is
the headless shell's unpainted base tiles — tile hosts don't
answer the sandbox; the chip, line and labels are the site's own
rendering).

Coordination note: this build ran in parallel with the NCTA
sheets build in the same working tree. The sheets commit
(`f25e2ea`) landed mid-build and swept this spec's small context
-chip edit (token spans in `armContextChip`) and the `.status-pill`
CSS into its commit; the remaining chip work (the `armChip`
rebuild) and this document were then committed on top, cleanly
separated by file region. Nothing of the sheets build was altered
by this spec.

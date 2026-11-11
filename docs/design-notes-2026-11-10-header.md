# Design notes — brand masthead + adoption story re-execution

Visual-design spec, 2026-11-10. Companion to `DESIGN-REVIEW.md` and
`UX-REVIEW.md` in this folder; where those two asked for a story bar
(DESIGN §5 P0, UX P1), this note supersedes their story-box layout
with the re-execution Paul asked for after seeing v4. Implementable
in plain HTML/CSS in `site/index.html` + `site/style.css`, plus one
click hook in `site/app.js`. No new colours: every value below is an
existing `:root` token or a literal already in `style.css` (named
where used). The one structural assumption: the boxed "Working
draft" notice under the title is being removed on Paul's instruction
in the same pass — the masthead is designed to sit directly above
the story box. If the notice survives a build or two longer, nothing
here breaks; it simply slots between masthead and story.

---

## 1. Brand masthead (panel upper-left)

### 1.1 Layout — one-row lockup

Replace the bare `<h1>` at the top of `#panel` with a masthead
block: logo left, stacked wordmark right, vertically centred as a
pair. The masthead sits on the panel's plain paper — **no box, no
tint** — and is closed by a hairline rule. The story box below it
keeps its green tint, so the panel reads: quiet brand on paper →
one tinted story block → tools. Two tinted blocks stacked would
compete; this way the tint belongs to the story alone.

```
[logo]  Itasca Moraine Chapter
        TRAIL MAP
─────────────────────────────  (1px, --paper-line)
[ story box … ]
```

- Container: flex row, `align-items: center`, gap 12px;
  padding-bottom 10px; margin-bottom 10px;
  border-bottom 1px solid `var(--paper-line)`.
- The wordmark's first line remains the page `<h1>` (document
  outline and the `<title>` already agree: "Itasca Moraine
  Chapter — Trail Map").

### 1.2 The logo slot

Paul's words were "the NCTA logo … along with ITM Chapter" — the
logo carries the association, the wordmark carries the chapter,
and the wordmark never spells out "North Country Trail
Association" in type. That division is also the branding
discipline in `DESIGN.md` rule 4 (a chapter project, never
presented as the national association) expressed visually.

- **Assumed artwork:** the association's standard full-colour
  logo, transparent PNG or SVG, aspect between 1:1 (emblem) and
  about 1.6:1 (emblem + short lockup). File lands at
  `site/images/ncta-logo.png` (or `.svg`); supply it at ≥ 2×
  display size (≥ 256px wide) so it stays crisp on retina screens
  and in print.
- **Slot geometry:** height fixed at **44px**, width auto,
  `max-width: 128px`, `object-fit: contain`,
  `object-position: left center`. Never stretched, never
  recoloured, no effects. Clear space around the art: the 12px
  flex gap plus the panel's own 16px padding is the minimum —
  nothing else enters that zone.
- **If the real file's aspect differs:**
  - *Square emblem (1:1):* renders 44×44px; the wordmark simply
    gets more room. This is the expected case and needs no
    adjustment.
  - *Wide lockup (up to ~3:1):* at 44px tall it would exceed the
    slot, so `max-width` caps it at 128px and the height settles
    to ~40px. The lockup stays one row; nothing else moves.
  - *Panoramic banner (wider than ~3.5:1, e.g. a full
    "emblem + North Country Trail Association" line):* switch to
    the stacked variant — add one class (`.masthead--stacked`) so
    the logo takes its own line at 34px tall, left-aligned, with
    the wordmark left-aligned beneath it, 8px gap. Decide once,
    when the real file arrives; it is a build-time choice, not a
    responsive behaviour.
  - *Reversed/white artwork:* do not use it on this panel — white
    art disappears on `--paper`. Request the standard
    full-colour or dark-text version. (A `--trail-deep` chip
    behind reversed art is a last resort only, and only if
    NCTA's own guidance permits that presentation.)
- **Alt text:** `alt="North Country Trail Association"`. If the
  fetched file turns out to be a bare emblem with no wordmark in
  the art, add a third micro-line under the descriptor (see 1.3)
  reading "North Country Trail Association" — the association
  should be named in type somewhere in the masthead, but only
  when the logo itself doesn't already say it.
- **Not a link.** The logo does not link out to
  northcountrytrail.org; this is a working map, and a surprise
  navigation away from it helps nobody. NCTA is fully credited in
  the Sources card, as today.

### 1.3 Wordmark type treatment

All sizes inside the existing system (system-ui stack, `--ink`
family); the current H1 is 1.15rem/650 — the masthead tightens it
into a proper two-line lockup:

| Element | Setting |
|---|---|
| "Itasca Moraine Chapter" (the `<h1>`) | 17px, weight 700, `color: var(--trail-deep)`, letter-spacing 0.01em, line-height 1.15, margin 0 |
| "TRAIL MAP" descriptor | 10.5px, weight 700, uppercase, letter-spacing 0.14em, `color: var(--ink-soft)`, margin-top 3px |
| Conditional association micro-line | 10px, weight 400, `color: var(--ink-soft)`, margin-top 2px — only per the emblem-only rule in 1.2 |

`--trail-deep` for the chapter name ties the wordmark to the
termini and chapter-green emphasis already on the map face; the
letterspaced small-caps descriptor borrows the voice the panel
already uses for its labels (`.tog-group`, `.ks-label`,
`.insp-pill` are all uppercase + letterspaced). No other text in
the masthead.

### 1.4 Relationship to the story box

The hairline under the masthead is the only separator. Story box
keeps its current shell unchanged — `background:
var(--header-tint)`, 1px border `#b9cba5`, radius 4px — and its
top edge sits 10px below the rule. Combined height of masthead +
story stays close to today's H1 + notice + mileage stack, so
Find, the inspector, and the layer list keep their positions in
the eye path (story → find → record, per UX Part 1).

### 1.5 Mobile (panel = top sheet, ≤720px)

The sheet is 38vh and scrolls, but its first screenful is the
whole first impression, so the masthead compresses rather than
stacks:

- One row, always. Logo height **32px** (same slot rules,
  `max-width: 96px`).
- Chapter name 15px on one line; descriptor stays, at 10px.
- Masthead padding-bottom and margin-bottom drop to 6px.
- At 15px, "Itasca Moraine Chapter" is ~185px wide; logo (32–96px)
  + 10px gap + wordmark fits a 360px-wide phone with room to
  spare. Do not let the name wrap — a wrapped wordmark in the
  sheet's first row looks like a bug, and at these sizes it never
  needs to.

### 1.6 Print variant

Printed handouts already carry `.print-header` (chapter name +
"printed from the chapter trail map" + date + the USGS Topo tip).
Upgrade it to a true print masthead rather than a sentence:

- Line 1: the logo at **11mm tall** (same slot rules — auto
  width, contain, never recoloured), beside "Itasca Moraine
  Chapter" at 13pt, weight 700, `--trail-deep`, with "TRAIL MAP"
  as the same letterspaced descriptor at 8pt `--ink-soft`.
- Line 2: the existing sentence, unchanged, at 9pt
  `--ink-soft`: name · "printed from the chapter trail map" ·
  date · the USGS Topo tip.
- The print masthead replaces `.print-header`'s current text; the
  story box (§2) prints directly beneath it as the handout's
  headline, exactly as DESIGN §6 / UX P7 already intend.

---

## 2. The adoption story, re-executed

### 2.1 What is wrong with the current block

The facts are right; the reading order is wrong. Today a
first-time viewer meets a 10px bar with an unexplained 11px red
fleck, then a two-sentence paragraph they must parse to learn
that the fleck is the story, then a context note about a purple
line, with the actual numbers buried mid-sentence at reading
size. The recruiting fact — *one stretch needs an adopter* — is
the last thing the eye reaches. The redesign makes the unit read
in three beats, top to bottom: **the achievement (big numbers),
the picture (the bar, now labelled), the ask (one line, and it
clicks).**

### 2.2 The unit, top to bottom

Everything stays inside the existing `.mileage` shell (tint,
border, radius as today; padding becomes 10px 12px). Four
elements, in this order:

**Beat 1 — the headline.** One line, numbers big:

> **73.2 mi adopted** of 76.2 mi

- "73.2" at 28px, weight 750, `color: var(--adopted-deep)` —
  the deep amber already used for section-name text, so the
  number wears the adopted colour without shouting in raw
  `--adopted` orange.
- "mi adopted" follows at 15px, weight 650, `--ink`.
- "of 76.2 mi" follows at 13px, weight 400, `--ink-soft`.
- The whole headline is a single `<p>` (screen readers get one
  sentence: "73.2 mi adopted of 76.2 mi"). Margin 0 0 8px.
  No label above it, no "Chapter sections:" prefix — the
  numbers are the label. (96% is nowhere stated: the audience
  reads miles, and the bar shows the proportion.)

**Beat 2 — the bar, labelled.** The bar stays — it was the
right idea — with three improvements:

- Taller: height **14px**, radius 7px, same white ground and
  `#b9cba5` border. At 14px the hatched red reads as a deliberate
  segment instead of a rendering error.
- The gap segment keeps its true proportion (flex 0 0 4%,
  hatched `--gap` as today) **with a 14px minimum width**. At
  the panel's ~264px inner width, a true 3.8% is ~10px; the
  floor buys 4px of legibility. This is a visibility floor, not
  a distortion anyone can detect, and it follows the map's own
  convention (boundary ticks already have minimum screen sizes).
- **The gap segment gets its annotation.** Directly beneath the
  bar, left-aligned under the segment, at 11.5px, weight 700,
  in `#b2182b` (the deep gap red already used for gap text in
  `.insp-*` and `.tog-error` — `--gap` itself is a graphic
  colour, too light for small text on the tint):

  > 2.9 mi — no adopter

  A 6px caret in the same red sits between bar and label,
  centred on the segment (a CSS triangle or a rotated square —
  implementer's choice, it is 6px). Left-alignment is the
  geography: the gap is at the west end, the label starts at the
  west edge, and the eye connects them without a leader line
  crossing the amber.

**Beat 3 — the ask.** One line, 13px, line-height 1.4, `--ink`,
margin-top 6px:

> The one gap is at the west end, in Itasca State Park. **It needs an adopter.**

- Final sentence in weight 700, `#b2182b`. Nothing else in the
  box is red text, so the ask owns the colour.
- This line and the Beat-2 annotation together are the click
  target (§2.4) — visually they are one statement split across
  the bar: *2.9 mi — no adopter … it needs an adopter.*

**Footer — the mini-legend, separated.** `#mini-legend` stays
inside the box (it is injected there today) but moves behind a
hairline: margin-top 10px, padding-top 8px, border-top 1px
solid `#b9cba5` (the box's own border colour). The story is the
story; the legend is apparatus, and the rule says so without a
word.

Total copy in the unit, in reading order: the headline, the bar
annotation, the ask line. Headline + two short lines, no
paragraph, no bullets. Every number exactly as given: 73.2,
76.2, 2.9.

### 2.3 The Laurentian Lakes line — cut from the box

**Ruling: cut the prose line** ("Purple: Laurentian Lakes
Chapter, shown for context."). It answered a real problem (UX P1:
the purple line fills half the map unexplained for the first 10
seconds), but it no longer needs prose to answer it:

- The mini-legend's **"Neighbor chapter"** swatch — purple line,
  two words — sits in the same box, one hairline below the story,
  and says exactly what the sentence said, in the legend's own
  grammar.
- The full legend (behind its button) and the map itself carry
  the chapter's name, Laurentian Lakes.

Keeping the sentence as well would explain the purple twice and
spend the story box's scarcest resource — the first three
seconds — on the neighbour. If a future build drops the
mini-legend, the sentence comes back; as long as the swatch is
in the box, the prose stays out.

### 2.4 Affordance — keep the selection, extend the target

- **Keep** the existing behaviour: the gap can be selected into
  the inspector (today via the map's gap label/line and the
  inspector's own gap callout, both through `selectSection`).
  Nothing about that path changes.
- **Extend it to the story:** wrap the Beat-2 annotation and the
  Beat-3 line in a single full-width `<button type="button">`
  (unstyled: no background, no border, text left-aligned,
  font inherited) whose click calls the same selection the
  inspector's gap callout already performs —
  `selectSection(gapWalkItem, "inspector")` in app.js terms.
  The bar itself stays `aria-hidden` decoration, as today; the
  headline above the button is plain text.
- States: cursor pointer on the button; hover tints the button's
  background to `#fdf0ec` (the gap-callout tint already in
  `.insp-gap-callout`) with radius 4px and a −4px/4px bleed so
  the tint reads as a surface, not a text highlight; keyboard
  focus gets the house `:focus-visible` ring (`--trail`, 2px).
  `aria-label`: "Show the unadopted gap — 2.9 miles at the west
  end, in Itasca State Park".
- Do **not** make the headline or the whole box clickable: one
  obvious target, shaped exactly like the ask. A visitor who
  clicks the amber part of the bar expecting "show me the
  adopted sections" gets nothing today and should keep getting
  nothing — the adopted sections are already on the map, one
  toggle away, and a second hidden behaviour would muddy the
  one this box exists for.

### 2.5 Print and mobile behaviour of the story unit

- **Print:** the unit prints as-is beneath the print masthead —
  it is the handout's headline. Add `print-color-adjust: exact`
  to the bar segments and the box so the amber/red survive a
  colour printer faithfully; on a B/W printer the hatch, the
  bold red-text ask (which prints dark grey), and the numbers
  still carry the story. The gap button prints as plain text —
  no affordance styling in print.
- **Mobile:** the unit is unchanged in structure and order; the
  headline's 28px numeral may drop to 24px under 720px if the
  sheet feels crowded, and no element wraps to a second line
  except the ask, which may wrap once. The box stays directly
  under the masthead, above Find — in the sheet's first
  screenful, the story is still the first thing read after the
  brand.

### 2.6 What does not change

The box shell, the mini-legend's five items and their order, the
gap's on-map label, the inspector's gap record, and every number.
No new colours anywhere in §1 or §2: the complete list of values
used is `--paper`, `--paper-line`, `--header-tint`, `--ink`,
`--ink-soft`, `--trail-deep`, `--adopted-deep`, `--adopted`
(the bar fill, unchanged), `--gap` (the bar segment, unchanged),
plus three literals already in `style.css` — `#b9cba5` (box
border), `#b2182b` (gap text), `#fdf0ec` (gap-callout tint).

---

## 3. Trademark / usage note (brief, non-blocking)

The NCTA logo is the association's mark, and chapters are its
constituent units — chapter use of the logo on chapter materials
is the normal, expected pattern, typically under NCTA's brand
guidance rather than a negotiated licence. The usual conditions
in such guidance, all cheap to honour here: use the official
artwork file unaltered (no recolouring, stretching, or separating
the emblem from its wordmark — §1.2's slot rules already enforce
this); keep clear space around it (§1.2); and never let the
presentation imply the map is a national-association or NPS
product — which is already this project's hard rule (`DESIGN.md`
rule 4), and which the masthead's division of labour (association
logo, *chapter* wordmark) actively supports. Two practical
corollaries: fetch the file from NCTA's own site or chapter
resources rather than redrawing or lifting a copy from a search
result, and if NCTA publishes an official chapter lockup (logo +
chapter name set by them), prefer it over this note's assembled
lockup. Do not pair the logo with the NPS arrowhead — that mark
is not the chapter's to use, and nothing in this design needs it.

---

## 4. Implementation checklist (for the builder)

- `index.html`: replace the bare `<h1>` with the masthead block
  (§1.1–1.3); restructure `.mileage` contents into headline / bar
  / gap button / mini-legend order (§2.2); the notice removal is
  Paul's separate instruction, not part of this spec.
- `style.css`: add `.masthead` rules (+ `.masthead--stacked`
  variant, held in reserve), `.story-head`, `.story-gap-btn` and
  bar/annotation rules, the mini-legend hairline, the ≤720px
  masthead compression, and the print masthead (§1.6) with
  `print-color-adjust` on the story box.
- `app.js`: one hook — the story's gap button calls the existing
  gap selection path, mirroring the `#insp-gap-btn` wiring.
  Mini-legend injection is unchanged.
- Logo file: dropped into `site/images/` when fetched; if its
  aspect is panoramic, apply `.masthead--stacked` at that point
  and re-check §1.5's one-line fit.

**Acceptance check (the beer-night test, updated):** a stranger
given three seconds with the panel can say whose map it is
(chapter, under the association's mark), that 73.2 of 76.2 miles
are adopted, and that one 2.9-mile stretch at the west end needs
an adopter — and can click the sentence that says so.

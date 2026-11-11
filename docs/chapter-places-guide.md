# Chapter Places — How a Place Gets on the Map

**Why:** The national data knows *where* most campsites are, but
almost nothing *about* them — most arrive as bare codes (BP1,
BP10…), with no name, no capacity, no word on water or condition.
The chapter knows those things. Chapter places are the chapter's
own records, kept in the chapter's own file, so they are never
overwritten when the national data is pulled again.

**One place, one entry.** Where a chapter record exists, it
replaces the national point everywhere — the map, Find, and each
section's "What's here" list. Nothing shows twice.

---

## The Two Ways In

**Route 1 — a photo (best for a place nobody has recorded yet)**

1. Stand at the place and take one clear photo of it, the same
   way you photograph a sign or a kiosk for the asset inventory.
2. Add the photo to the shared photo folder, in your named
   subfolder. Never by text message — texting strips the
   location off the photo.
3. The photo pipeline reads the location out of the photo and
   makes the pin. Muse drafts the entry — kind, and whatever
   the photo shows — and Paul approves it before it publishes.

**Route 2 — a name and a location**

Tell Paul (or tell Muse, who passes it to Paul): the place's
name, what kind of place it is, and where it is — a photo, a
pin dropped on any map, or a description like "the campsite on
the east shore, a quarter mile north of the West-13 boundary."
That is enough to draft the entry.

**Paul approves every entry.** Nothing reaches the public map
without his say-so. There is deliberately no editing on the map
itself.

## What an Entry Carries

- **Name** — the real name, once the chapter supplies it. Bare
  national codes stay bare until then; nobody invents a name.
- **Kind** — Camping, Water, Parking, Shelter, Privy, or POI.
- **Status** — open, closed, seasonal, or left blank when the
  chapter hasn't said.
- **Description** — a few plain sentences: what the place is
  like, what a crew or a hiker needs to know.
- **Capacity** — free text: "6 tents", "one group site".
- **Water note** — where the water is and whether to trust it:
  "pump at the trailhead", "lake water, treat it".
- **Source** — where the record came from. Seeded entries read
  "seeded from NCTA — chapter to confirm" until the chapter has
  checked them; then they read "chapter".
- **Added date**, and a **photo** link once the pipeline has one.

## Replacing a National Point

Most campsites started as seeds: the chapter's copy of a national
point, at the same spot, wearing the national name. Editing the
seed — giving it its real name, its capacity, its water note —
*is* the replacement. The national version steps aside on its
own; the chapter version is the one that shows. If a place is
missing entirely, it is added fresh, with no national point
behind it.

## Recording a Closure

A closure is an edit, not a deletion:

1. Set the entry's **status** to **closed**.
2. Put the reason in the **description**, in the source's own
   words when there is an official notice.
3. Name the source and its date in the entry's **source** line —
   for example, "chapter — closed per NCTA trail alert,
   April 12, 2026".

The place stays on the map, greyed out and marked CLOSED, so
nobody plans a night at a site that no longer exists — the
Rogstad Campsite, closed when its land passed to the U.S. Fish
& Wildlife Service, is the first entry recorded this way. When
a place reopens, the status changes back and the closure note
moves into the description's history.

---

*The working file is `data/points/chapter-places.geojson` in the
map project. The map rebuild (`scripts/build_gazetteer.py`, then
`scripts/build_chapter_places.py`) carries new and edited entries
to the site.*

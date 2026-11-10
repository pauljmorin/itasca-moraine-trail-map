# Design + UI review brief — Itasca Moraine Chapter Trail Map

## What this is
A public, static Leaflet map for the Itasca Moraine Chapter of the North
Country Trail Association (volunteer chapter, 100+ mi of North Country
Trail in north-central Minnesota). Live: https://pauljmorin.github.io/itasca-moraine-trail-map/site/
Source under review: site/index.html, site/style.css, site/app.js in this repo.

## Who uses it, for what
1. Chapter management — see the whole trail at once: which sections exist,
   who adopted them, what state they're in, where the one unadopted gap is.
2. Volunteer coordination — at meetings and "beer nights": find a section,
   see its record (adopter, sawyer, maintenance, help requested), recruit
   for the gap.
3. Public promotion — the same live page is public; it must look like
   something a chapter is proud to link.

It is a home/meeting tool (big screen, mouse), not a field app. Printability
matters (paper maps at recruiting events).

## Data on the map
- Official NCT line (green; a neighbouring chapter's line in purple where
  it falls in the extent), adopted sections in amber OVER the line, one
  unadopted gap in dashed red, section boundary tick bars across the line,
  chapter-end bars + names, gazetteer search ("Find") over 257 places
  (sections, crossings, parking, camping, water, shelters, POI), layer
  toggles (access lines, roads, asset pins; parcels built but UI-disabled),
  6 base maps (OSM default, OpenTopoMap, USGS Topo 1:24k, MN LiDAR
  hillshade, USGS NAIP aerial, Esri World Imagery).

## The interaction under special scrutiny
Hovering a section raises a tooltip card carrying the section's full
spreadsheet record (~15 rows) that follows the cursor. The owner says:
"the mouse over is great with the spreadsheet data but there has to be a
better way." Reviewers: propose a better pattern (pinned detail panel?
click-to-pin + hover-lite? side sheet? something else) and defend it
against the meeting/recruiting use cases. Whatever replaces hover must
keep the record one gesture away and must not lose the click popup's
existing role without a stated reason.

## Standing constraints (do not propose violating these)
- Static site, no build step, no framework, no API keys, no accounts;
  must remain portable enough to hand to the chapter wholesale.
- Public page: adopter/sawyer names appear ONLY as placeholders
  ("Test adopter N"); the parcel layer stays UI-disabled for now.
- The official line comes from the NCTA public service; the chapter's
  data model (chapter as attribute) stays.
- Beer-night test: a first-time viewer should get the chapter's story
  (adopted vs the one gap) in under 10 seconds.

## Screenshots in this folder
- shot-1: chapter view z10, hover card up (pre-cap tick bars — huge)
- shot-2: chapter view z10 after size caps + label declutter
- shot-3: Find → section card (the spreadsheet record in a popup)
- shot-4: roads layer (older styling)
- shot-5: label decluttering in the dense Chip cluster, z11
- shot-6: hover card at z13 (note it runs off the top of the viewport)

## What we want back (file: DESIGN-REVIEW.md / UX-REVIEW.md in this folder)
Prioritized, concrete, implementable-in-vanilla-Leaflet recommendations:
specific values (colors, sizes, spacing, timings), named patterns, and
before/after reasoning per item. Flag anything you'd cut. Separate
"beautiful" (visual design) from "useful" (interaction) where they
conflict, and say which you'd sacrifice. No generic advice — every item
must reference something visible in the screenshots or code.

# Native nations — reservation boundaries

Public federal reservation boundaries only. Tribal management /
forestry data is NOT in scope here (relationship-only, per the
project's standing line).

## Leech Lake Reservation (pulled 2026-11-11)

- Source: U.S. Census Bureau, TIGER/Line AIANNH, TIGERweb current
  (BAS 2026), layer 2, GEOID 1940R. Pull script:
  `scripts/pull_leech_lake_reservation.py`.
- File: `leech-lake-reservation.geojson` (this folder = working
  copy; identical file at `site/data/`). Full unclipped polygon,
  9,685 vertices, 838,631 acres (land 622,953 / water 215,678).
- Cross-check: BIA AIAN-LAR national (LAR0033) — same extent,
  geometry area within 1.8%, boundary median separation 37 m.
  Full comparison in SOURCES.md.
- Trail overlap: 2.28 mi inside, all on Chip-12.
- White Earth: touches the map extent's western margin, 0.00 mi
  of trail inside — the next polygon if Paul asks for it.

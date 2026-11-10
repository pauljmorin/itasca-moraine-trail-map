# Parcel coverage by county — Itasca Moraine Chapter trail corridor

Produced 2026-11-10 by `scripts/pull_parcels_corridor.py`.
**Working-view documentation: the corridor data contains landowner
names and is never published (see DESIGN.md privacy rules).**

## Which counties does the trail cross?

Determined from the data, not assumed: the official trail line
(`data/segments/official-line-chapter-extent.geojson`, 84 features)
was intersected with MnGeo county boundary polygons
(`bdry_counties_minnesota`; see SOURCES.md). County mileage is by
trail-segment midpoint attribution, so figures are approximate to
within a segment length; the four counties sum to ~121.7 line miles
against 117.74 geodesic miles of line inside the working extent
(the line file's geometries are untrimmed and reach slightly past
the extent edges).

| County | Trail miles (approx.) | In state compilation? | Parcel source used |
|---|---|---|---|
| Hubbard | 42.1 | **NO** | Hubbard County open-data service (fallback) |
| Cass | 33.2 | Yes | State compilation |
| Becker | 31.2 | Yes | State compilation |
| Clearwater | 15.1 | Yes | State compilation |

The working extent also overlaps corners of Crow Wing, Mahnomen,
Otter Tail and Wadena counties, but the trail line does not enter
them. Beltrami and Itasca counties were checked and are **not**
crossed by the trail.

## The Hubbard gap

Hubbard County — the chapter's largest trail county — has **not**
opted in to the state compilation: the compilation's metadata
layer reports `gac_open_approval = false` for Hubbard, and the
compiled parcel layer holds zero Hubbard records. There is also no
Hubbard parcel tree in the state GDRS download archive.

The county's own open-data alternative exists and was used:
**Hubbard County Tax Parcels**, the county's public ArcGIS service
(`gis.co.hubbard.mn.us`, OpenData folder; see SOURCES.md). It
carries owner names (`PINAME1`/`PINAME2`) in the county's own
schema, so Hubbard features in the corridor file keep their native
fields, distinguished by `source_county` / `source_dataset`.

If the county service is ever unavailable, the remaining routes are
the county GIS office / parcel viewer (request-based; the compiled
metadata layer lists no Hubbard download URL or viewer URL).

## Corridor result

Corridor rule: every parcel the trail line crosses, plus every
parcel adjoining one of those (one ring deep). Candidates were
pulled within 2.5 km of the line; "crossed" includes parcels the
line touches or passes within 1 m of; "adjoining" means boundaries
within 3 m (tolerance absorbs the small sliver gaps the compiled
data carries, especially across county lines). Full method is in
the pull script's docstring and the output file's metadata.

| County | Crossed | Adjoining | Total |
|---|---|---|---|
| Hubbard | 117 | 248 | 365 |
| Becker | 85 | 205 | 290 |
| Cass | 36 | 270 | 306 |
| Clearwater | 17 | 63 | 80 |
| **Total** | **255** | **786** | **1,041** |

921 of the 1,041 parcels carry a published owner name; most of the
rest are public-land records the sources publish without one.

## Caveats found in the sources

- **Shoreline gaps (Hubbard sources).** A few dozen trail points —
  at the northwest end of the line and in the Itasca State Park /
  Hicks Lake shore area — fall in small gaps between Hubbard County
  parcel polygons, so no parcel "contains" them. The adjoining
  parcels on both sides of those gaps are in the corridor file;
  no corridor parcel is missing because of this, but a strict
  point-in-parcel lookup will show holes there.
- **Cross-county polygons (Clearwater compilation).** Two very
  large polygons attributed to Clearwater County (notably a
  19,734-acre record, county PIN 99-101-0100, published without an
  owner name) spill across the county line into Hubbard in the
  Itasca State Park area. County attribution near county lines
  should be treated as approximate; these records likely reflect
  how the source county supplied park/public-land geometry.
- **Snapshot dates.** Compiled parcels: content dated 2026-08-06
  (all four counties' `rundate`). Hubbard service: live county
  service, pulled 2026-11-10 (29,241 parcels county-wide at pull
  time). Parcel data is a snapshot; refresh roughly annually per
  DESIGN.md.

# Parcels color — one color in all three viewers — Nov 25, 2026

Paul, Nov 25, 2026: "the parcels need a better color in ALL of the
viewers, considering all the basemaps in use. Fix it."

## Old colors (what was wrong)

- **ITM + NCT full viewer:** crossed parcels solid burnt-orange
  outline `#b35806`, fill `#fdbb84` (0.32); adjoining parcels
  dashed khaki outline `#a89a5b`, fill `#e7e1c3` (0.12). Faint
  below Z3 (ITM) / Z11 (NCT).
- **Leech Lake viewer:** one style, no crossed/adjoining
  distinction — khaki-brown `#8a6d3b`, weight 0.5, opacity 0.6,
  fill 0.05.

Why they failed: the orange vanished on summer satellite
(orange-brown outlines on brown/green leaf-on imagery) and on
color-infrared aerials (orange outlines on red vegetation); the
khaki was nearly invisible on light paper basemaps and on
satellite; the Leech 0.5 px brown was nearly invisible everywhere.

## New color (same in all three viewers)

- **Outline: `#0891b2`** (deep cyan), weight 2 (ITM/NCT full
  style; 1 when faint), opacity 1 (0.4 when faint).
- **Fill: `#22d3ee`** (bright cyan), fillOpacity 0.10 (0.05 when
  faint). Leech: weight 1.5, opacity 0.9, fill 0.08 (no
  crossed/adjoining distinction there — no trail crosses the
  watershed parcels).
- **Crossed vs adjoining** (ITM + NCT only) is now **dash-only**:
  solid outline = the trail crosses the parcel; dashed "3 3" =
  adjoining ring. Same color, same fill for both. Panel swatches
  and the ITM legend use the same fill + outline.

## Why cyan

Checked against every basemap family in use: light paper/OSM,
dark LiDAR hillshade, summer satellite (Esri/NAIP), MnGeo CIR
aerials 2008–2025, Sentinel-2 renders (natural colour, colour
infrared, NDVI, agriculture), terrain and winter. Cyan is rare in
natural imagery, so it reads on light, dark, satellite and
infrared alike — on CIR red vegetation it is complementary, the
highest possible contrast. It is clear of every neighbouring
layer color: gov-owned Federal blue `#1d4ed8`, State green
`#15803d`, Land-trust amber `#a16207`, County grey, Tribal pink
`#be185d`, timber lime, the reroute blue wash, the reservation
violet. No viewer already used cyan (verified: zero hits for
`#0891b2` / `#22d3ee` before the change). The one weak case is
cyan outlines over open water on bathymetric renders, where
parcels are rare.

## What did not change

- Parcels stay **OFF by default** in all three viewers (ITM,
  NCT, Leech) — this is a color fix, not a visibility change.
- The faint-below-zoom behaviour is unchanged (ITM Z3, NCT Z11,
  Leech zoom gate 12).
- The Leech Lake **public copy** (`leech-lake-gh-staging`) still
  has parcels cut from it (Nov 21, 2026 decision, pending
  restore) — the color change lives in the main (private) Leech
  viewer and applies automatically when parcels are put back.
- The Nov 10 cartography notes record the old colors as history;
  they were not rewritten.

## Verification

Headless screenshots across basemaps (light, satellite, CIR)
showing parcels legible in each; no console errors; no
regressions. See the branch report.

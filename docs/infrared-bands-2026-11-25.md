# Infrared + nonstandard band combinations — ITM viewer (25 Nov 2026)

Paul, voice call 25 Nov 2026: "we don't infrared anything like that —
does that exist for the air photography, and if so I want you to put it
into the ITM viewer" + "any of the other nonstandard band combinations,
please put those in." Follow-ups the same call: place the new group
just below "Lisa's family stuff" in the layer panel; order the band
layers by priority with infrared first; show the picked aerial source's
metadata (resolution, provider, vintage, season, coverage, bands)
directly below the dropdown, visible only while an aerial is chosen.

## Placement (what Paul asked vs what exists)

- **There is no "Lisa's family" group in the ITM viewer.** Verified by
  search: the string "Lisa" appears nowhere in `site/app.js`,
  `site/index.html`, `site/data-sources.html` or `site/about.html`
  (the only hit repo-wide is vendored `leaflet-geoman.js`, which is
  a third-party library). The panel groups are: The trail, Road
  walk, ITM inventory, Agency Maps, Other trails, The land, Land
  ownership, Around the trail, Your layers (+ the Basemap section).
- Closest sensible spot, per the follow-up's fallback: the new
  layers sit with the other aerials in the **Basemap section** —
  the 12 CIR year aerials inside the "Aerial photography by year"
  dropdown (each directly after its RGB twin), the 10 Sentinel-2
  renders as buttons directly above the dropdown. If Paul meant a
  different viewer or section, the block moves in one edit (it is
  one contiguous block in the BASES array).
- **Order is provisional pending Paul's ranking.** CIR first
  (settled). The Sentinel-2 block is ordered best-guess usefulness:
  CIR, Agriculture, NDVI, NDMI, Geology, SWIR, Bathymetric, Burn
  Ratio, Built-up Index, Water Index. Reorder the block in
  `site/app.js` to re-rank — nothing else keys off the order.

## What was verified live (tile tests, 25 Nov 2026)

Test point: Park Rapids, MN (46.9197, −95.0603), 2 km box, 256×256
JPEG, unless noted. A tile counted as real data when it was a
decodable JPEG with pixel variance (std > 0); a 1,651-byte tile
with std 0.0 / 1 colour is the service's blank-white "no data" tile.

### MnGeo WMS — CIR layers (all 200, real JPEG unless noted)

| Layer | Test | Result |
|---|---|---|
| fsa2025cir | Park Rapids | 15,608 B — real |
| fsa2023cir | Park Rapids | 14,468 B — real |
| fsa2021cir | Park Rapids | 13,409 B — real |
| fsa2019cir | Park Rapids | 14,877 B — real |
| fsa2017cir | Park Rapids | 16,085 B — real |
| fsa2015cir | Park Rapids | 14,677 B — real |
| fsa2013cir | Park Rapids | 14,677 B — real |
| cir2008 | Park Rapids | 15,160 B — real |
| fallcir12 | Park Rapids | 15,642 B — real |
| nw14cir | Thief River Falls | 16,247 B — real; Bemidji blank (1,651 B) |
| itas18cir | Grand Rapids | 14,423 B, std 40.6 — real; Park Rapids blank |
| nc13hmcir | Itasca SP / Akeley / Nevis / Lake George | real (8,354–14,770 B); Park Rapids blank — and the RGB twin `nc13hm` is blank at Park Rapids too, so the CIR twin matches its RGB twin exactly |
| nc13ftcir | Grand Rapids | 14,513 B — real; Ely blank |
| ncir09 | Brainerd, Park Rapids | blank both — abstract says Big Fork/Little Fork watersheds only (Koochiching / N Itasca / St. Louis) |

Added: all except `nw14cir` (blank over most of the corridor — same
verdict as its RGB twin, Nov 13) and `ncir09` (no corridor coverage).

### Esri Sentinel-2 ImageServer — exportImage + rendering rule (all 200, JPEG)

Park Rapids bbox, `size=256,256&format=jpgpng`, plain (non-DRA) rules:
Color Infrared 11,808 B; Agriculture 11,823 B; Geology 7,654 B;
Short-wave Infrared 9,237 B; NDVI Colormap 24,219 B; NDMI Colorized
30,451 B; Bathymetric 9,830 B; Normalized Burn Ratio 10,133 B;
NDWI Raw 9,654 B; Natural Color 9,520 B (sanity check, not added —
standard combo); Normalized Difference Built-Up Index (NDBI) 9,442 B.
Rendering-rule band combinations and index formulas are Esri's own
descriptions from the service's `rasterFunctionInfos` endpoint
(fetched 25 Nov): CIR = B08,B04,B03; Agriculture = B11,B08,B02;
Geology = B12,B11,B02; SWIR = B12,B11,B04; Bathymetric = B04,B03,B01;
NDVI = (B08−B04)/(B08+B04); NDMI = (B08−B11)/(B08+B11);
NBR = (B08−B12)/(B08+B12); NDBI = (B11−B08)/(B11+B08);
NDWI = (B03−B08)/(B03+B08).

### Landsat ImageServer — verified live, NOT added

Color Infrared 4,524 B and Band 10 Surface Temperature 2,135 B both
returned 200 JPEGs at the same bbox — but Landsat's renders duplicate
Sentinel-2's at 30 m vs 10 m, and temperature is a derived product,
not a band combination. Nothing distinct; skipped.

### Checked and rejected

- **USDA NAIP ImageServer** (`gis.apfo.usda.gov/arcgis/rest/services/
  NAIP/USDA_CONUS_PRIME/ImageServer`): empty reply, curl rc 52, twice
  (25 Nov). Unreachable from this VM. No loss: MnGeo serves the same
  NAIP CIR data (the `fsa*cir` layers above).
- **NASA GIBS MODIS Bands 7-2-1 false colour**: layer exists in the
  WMTS capabilities (`MODIS_Terra_CorrectedReflectance_Bands721`),
  but 500 m resolution — a blur at trail zoom. Rejected on resolution.
- **Sentinel-2 raw-index variants** (NDVI Raw, NDVI–VRE, NDWI–VRE):
  same indices without a colour map, or red-edge variants for
  precision agriculture. No trail use; skipped.
- **MnGeo metro CIR layers** (`met25cir`, `met20cir`, `met16cir`,
  `dak19cir`, `rams20cir`, `carl19cir`, `belt20cir`, `polkcir`,
  `smet10cir`, `met10cir`): Twin Cities / county flights with no
  corridor coverage. Skipped.

## Resolutions (metadata readout sources)

- NAIP years (MnGeo NAIP table, mn.gov): 2025 60 cm, 2023 30 cm,
  2021 60 cm, 2019 60 cm, 2017/2015/2013 1 m, 2010/2009 1 m
  (3-band, no CIR twin exists), 2008 1 m, 2003 1 m, 2006 2 m
  (NAIP) — but the viewer's 2006 layer is the USGS 40-county 1 m
  product per its own abstract, so its string says 1 m.
- County/project flights (WMS layer titles): nc13hm 50 cm,
  nc13ft 1 ft (30 cm), itas18 1 ft (30 cm), nw14 50 cm.
- 2012 fall: 50 cm — from the WMS ScaleHint (min 0.20); the
  ScaleHint minima track ground resolution at 0.4× metres
  (verified: 2023 min 0.12 = 30 cm, 2025/2021/2019 min 0.24 =
  60 cm, 2017/2015/2013/2008 min 0.40 = 1 m).
- Wayback/Esri: sub-metre, varies by source tile (no single
  published figure); capture years from the Nov 13 measurements
  (2025 release = 2024 photos, 2023 = 2019, 2022 = 2021,
  2021 = 2017–19, 2019 = 2017, 2014 = 1999; 2018, 2020, 2024
  unmeasured — their strings say so).
- Sentinel-2: 10 m, 13-band, latest-scene mosaic (Esri service
  description); vintage varies by tile.

## What changed in the code

Branch `infrared-bands`, based on main `30c6ec4` (the draw-phase1
branch's uncommitted parcels-gate patch was stashed untouched and
restored afterwards — this branch does not contain it; the Nov 24
panel rebuild has no branch in the repo yet, so these layers were
fitted to the current panel structure and the rebuild will need to
carry the BASES entries over).

- `site/app.js`:
  - 12 MnGeo CIR `L.tileLayer.wms` defs (same pattern as the RGB twins).
  - `ImageServerLayer` (`L.TileLayer` subclass) — live `exportImage`
    per tile for the Sentinel-2 service — plus 10 Sentinel-2 layer
    instances, plain (non-DRA) rules.
  - BASES: 58 entries (was 36). CIR years interleaved after their
    RGB twins in the year dropdown (36 dropdown entries now);
    Sentinel-2 as 10 buttons after "Aerial + Topo", before the year
    menu. Every aerial/S2 def carries a `meta` string; S2 defs carry
    `imagery: true` so `setBase` gives them the imagery label
    treatment.
  - `showAerialMeta()` + `#bg-aerial-meta` div directly below the
    year `<select>`: shows the current base's `meta` only while an
    aerial base is chosen, hidden for every other base. Called from
    `setBase` (covers clicks and `#base=` share links).
  - `CASING_BY_BASE`: "photo" for all 22 new bases.
- `site/style.css`: `.bg-aerial-meta` (same sizing as `.bg-year-note`).
- `SOURCES.md`: Nov 25 entries — CIR interpretation method (what red
  means, relative not calibrated), Sentinel-2 band combos + index
  formulas, rejected candidates, metadata-readout sources.
- Headless check (final, Nov 25, ~16:40 CST): served `site/` locally,
  drove headless Chromium via Playwright (`/tmp/ir-research/verify-ir.js`
  + `verify-s2.js`). Panel wiring: 58 BASES, 37 year options (36 +
  placeholder), 22 bg buttons, 10 Sentinel-2 buttons; metadata readout
  shows the correct text for all 22 new bases and hides for
  Topo/LiDAR/White; RGB 2025 regression 20/20. Tile loads at Park
  Rapids, z13, 20 tiles per base: all 12 CIR layers 20/20; all 10
  Sentinel-2 layers 20/20 — but only with a 15 s wait per base: with
  a 4 s wait the S2 renders showed 0–3/20, because each Esri
  `exportImage` tile is a live server-side render of 13-band imagery
  and takes seconds; 0 errored, 0 pending at 15 s, so it is latency,
  not failure. Console errors 0; failed requests 0 (excluding
  Leaflet's normal aborts of superseded tiles on base switch).
  Environment quirk, recorded so the next headless run is not a
  mystery: this VM's egress proxy MITMs TLS with the "Hatch Sandbox
  Egress CA" (in the system store curl trusts); headless Chrome's
  trust store lacks it, so Chrome aborts the handshake inside the
  CONNECT tunnel (`ERR_TUNNEL_CONNECTION_FAILED`) — and Chrome's
  direct TCP connection to the proxy fails even with literal proxy
  IPs, while the same bytes relayed through a localhost Python
  socket succeed. The runs above used a transparent localhost relay
  (`/tmp/ir-research/relay.py`, byte-forwarder, no modification) as
  the proxy plus `--ignore-certificate-errors` (test-only flag; the
  tile services themselves were already verified with full cert
  validation via curl/openssl). In a normal browser (Paul's Chrome,
  or the live site) none of this applies — the services are public
  HTTPS with publicly trusted certs.

## Open items for Paul

1. Rank the Sentinel-2 renders (current order is provisional).
2. Say where the cluster should live if "Lisa's family stuff" meant a
   different viewer/section than the ITM Basemap area.
3. Deploy is his call — this branch is NOT pushed to main and NOT
   deployed to GitHub Pages.

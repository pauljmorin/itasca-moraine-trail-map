# Forest Service map survey — beyond the MVUMs

**Date:** 2026-11-16
**Repo:** `~/workspace/itasca-trail-map`
**Question from Paul:** was our Forest Service search just the MVUMs — does the Forest Service have more maps than the six we wired?
**Answer in one line:** the MVUM set is now complete (all 8 Superior + all 4 Chippewa sheets found, and the three "missing" Superior sheets hold **0 km of NCT tread**), and of every other Forest Service map family, only one newly-found family shows NCT tread — the Chippewa dispersed-camping JPGs — which cannot be wired because they are not georeferenced. **Nothing new to wire.**

The viewer groups these under the panel group **"Agency Maps"** (subgroups "DNR maps" and "Forest Service maps"). Nothing in this survey was wired, and no file in `site/` was touched. New source PDFs for the three found Superior sheets are saved in `working/fs-geopdf/` (git-ignored).

## Headline findings

1. **The three missing Superior MVUM sheets are FOUND** — direct PDF URLs via the forest's MVUM publications page (`/media/` nodes). All three tested at **0.00 km** of NCT tread. The Isabella claim from the earlier note is now proved stronger than stated: the Isabella frame holds no NCT tread at all (nearest tread 10.9 km north), so nothing is missing from the viewer.
2. **MVUMs are complete:** Superior 8/8, Chippewa 4/4. The reliable discovery route is the forest publications page + `/media/` redirect, not URL-guessing (the files live in two different directories with inconsistent date suffixes — that is why the first pass's probe matrix missed them).
3. **Forest Visitor Maps** are Avenza-only ($4.99 each, app-locked, no downloadable file). They do cover the NCT corridor at district scale, but there is no file to wire — and the Forest Service announced (April 2026) it can no longer add or update digital maps in the Avenza store, so that channel is frozen.
4. **FSTopo 1:24k quads** are free GeoPDFs and tile the forests, so they contain tread by construction — but they duplicate the USGS Topo basemap already in the viewer. Don't wire (same exclusion as the original scope).
5. **Chippewa dispersed-camping maps (22 JPGs)** do draw the NCT — Map 18 (Walker area) confirmed visually, "NCT" labelled on the sheet. But they are ungeoreferenced JPGs, and their purpose is campsites, not trail cartography. Don't wire.
6. **Everything else** (Superior Box hiking/ski/MTB/birding/hunter/canoe folders, Chippewa grouse-habitat maps, driving tours, the Interactive Visitor Map, the camping guide) is small-area, single-purpose, or interactive-only, and holds no corridor-scale NCT map.
7. **Chequamegon-Nicolet (Wisconsin):** nearest MVUM footprint is 64.3 km from the NCT; all other neighboring-forest maps cover the same Wisconsin extent. No map from any neighboring forest reaches the Minnesota NCT.

## 1. The three missing Superior MVUM sheets — FOUND, 0 km each

### Retry log (what was tried this time)

The first pass probed filename/date/directory variants (`BorderAreaFront_20250707.pdf`, `_20250701`, `_20250808`, `_20250707_0`, `_20250808_0`, no-date, in both `/sites/nfs/files/r09/superior/publication/` and `/sites/nfs/files/publication/`) — all 404; USFS Box links 404; Wayback had none; `fs.usda.gov` HTML was bot-blocked to curl. This pass took a different route:

1. **R9 MVUM Finder** (the FS interactive MVUM map, Experience Builder app `326948b1c4944f4aae9ae4ab20448109`, linked from the Superior maps-guides page). Its config was read through the ArcGIS sharing API (`arcgis.com/sharing/rest/content/items/<id>/data`), which named webmap `6e24d7ebd59246c19ce625f4d14acabd`, whose operational layers include the footprint layer `R9MVUMFootprints` (`services1.arcgis.com/gGHDlz6USftL5Pau/arcgis/rest/services/R9MVUMFootprints/FeatureServer/0`). Querying that layer returns all 8 Superior footprints with `Print_URL` and `Avenza_URL`. The `Print_URL` for every sheet is the same generic landing page, **not** a direct PDF — but the Avenza URLs exist for all 8, including the three missing ones, proving the sheets exist as products.
2. **Superior MVUM publications page** (`fs.usda.gov/r09/superior/multimedia/publications/motor-vehicle-use-maps`, release date July 15, 2025) lists all eight MVUMs with direct PDF links (3.3–6.0 MB each) via `/media/` nodes 248743–248750.
3. **HEAD on each `/media/` node** returns a 302 to the real file URL. That is the reliable discovery route — the files live in two different directories with inconsistent date suffixes, which is why guessing failed:
   - Border: `/sites/nfs/files/r09/superior/publication/BorderAreaFront_20250702.pdf`
   - Vermilion River: `/sites/nfs/files/publication/VermilionRiverAreaFront_20250818_0.pdf`
   - Isabella: `/sites/nfs/files/publication/IsabellaBack_20250808_0.pdf`

### Downloads (verified)

Saved in `working/fs-geopdf/`:

| Sheet | File | Size on disk | Page size | Direct URL |
|---|---|---|---|---|
| Border Area (Front) | `superior-border-front.pdf` | 5,012,311 B | 4.8 MB | `https://www.fs.usda.gov/sites/nfs/files/r09/superior/publication/BorderAreaFront_20250702.pdf` |
| Vermilion River Area (Front) | `superior-vermilion-front.pdf` | 6,161,676 B | 5.9 MB | `https://www.fs.usda.gov/sites/nfs/files/publication/VermilionRiverAreaFront_20250818_0.pdf` |
| Isabella Area (Back) | `superior-isabella-back.pdf` | 3,430,746 B | 3.3 MB | `https://www.fs.usda.gov/sites/nfs/files/publication/IsabellaBack_20250808_0.pdf` |

All three are single-page GeoPDFs (PDF 1.7) with a `MVUM Road Trails Map` viewport. The Isabella sheet's printed date is August 2025. The media-node IDs for the full Superior set: Border 248743, Ely 248744, Grand Marais 248745, Isabella 248746, Toimi 248747, Upper Trail 248748, Vermilion River 248749, Virginia 248750. Avenza product URLs exist for all eight (e.g. `store.avenza.com/products/superior-nf-mvum-isabella-area-us-forest-service-r9-map`).

### Geometric test (same method as the first pass, validated)

50 m sampling of `site/data/trail-minnesota.geojson` (348 features) against each sheet's `/Measure` viewport quad, in UTM 15N. The sampler was validated first: trail total 902.80 km (matches the earlier note's 902.8 km exactly), wired per-sheet figures reproduce the recorded `trail_km` within ~1–3% (Ely 92.75 vs 92.14; Grand Marais 97.70 vs 97.53; Chippewa South Front 83.20 vs 80.55), wired union 449.25 km vs the note's 443.60 km.

| Sheet | Frame (lon / lat, from `/Measure` GPTS) | NCT tread in frame | Nearest NCT tread | NCT tread in frame but outside all six wired frames |
|---|---|---|---|---|
| Border Area (Front) | −92.354..−91.508 / 48.078..48.632 | **0.00 km** | 12,930 m | 0.00 km |
| Vermilion River Area (Front) | −93.111..−92.298 / 47.995..48.551 | **0.00 km** | 19,701 m | 0.00 km |
| Isabella Area (Back) | −91.463..−90.446 / 47.270..47.850 | **0.00 km** | 10,938 m | 0.00 km |

### The Isabella verdict — proved, stronger than the earlier claim

The earlier note said "whatever trail their frames hold is already inside the six wired frames." The actual result is stronger: **the Isabella frame holds no NCT tread at all.** The Kekekabic tread in that longitude band runs at lat ~47.87–47.95, about 11 km north of the Isabella frame's north edge (47.850); that tread is inside the Upper Trail frame (south edge 47.767). The Border frame's south edge (48.078) sits ~13 km north of the nearest tread, and the Vermilion River frame's south edge (47.995) sits ~20 km north of the NCT's Virginia/Ely approach. **No tread is missing from the viewer on account of these three sheets. Do not wire any of them.**

For completeness, the Toimi frame (the other side of the Isabella sheet, already on disk) was re-extracted from `working/fs-geopdf/superior-toimi-front.pdf`: lon −92.181..−91.355, lat 47.250..47.806 — consistent with its earlier 0 km / nearest-trail-2,402 m result.

### MVUM completeness

- **Superior: 8/8 found.** Five wired (Ely, Virginia, Upper Trail, Grand Marais + Toimi tested 0 km); three found now, all 0 km. The 4-sheet / 8-area structure is confirmed: Vermilion River (front) + Virginia (back); Border (front) + Ely (back); Toimi (front) + Isabella (back); Upper Trail (front) + Grand Marais (back).
- **Chippewa: 4/4 found.** The Chippewa maps-guides page lists its four MVUMs as `/media/` nodes 260353–260356, resolving to the same files already wired/tested (`MVUM_Chippewa_North_Front_26.pdf`, `MVUM_Chippewa_North_Back_26.pdf`, `MVUM_Chippewa_South_Front_26.pdf`, `MVUM_Chippewa_South_Back_26.pdf` under `/sites/nfs/files/r09/chippewa/publication/`).

## 2. Per-family verdicts

| Family | What it is | Contains NCT tread? | Publicly downloadable file? | Verdict |
|---|---|---|---|---|
| MVUMs (Superior 8, Chippewa 4) | Motor Vehicle Use Maps, GeoPDF, one per area | Yes — 6 wired (443.60 km union); 6 tested 0 km (North Front/Back, Toimi, Border, Vermilion, Isabella) | Yes — free GeoPDF via forest publications pages (`/media/` nodes) | **Wire the 6 already wired; the other 6 stay out (0 km)** |
| Forest Visitor Maps | Forest-wide district maps, 1/2" = 1 mile; 4 maps cover Superior's 6 administrative units; 1 map for Chippewa | Yes (district-wide, so tread by construction) | **No** — Avenza-only, $4.99 each (Superior East listing: 2018, 41.68 MB), app-locked; print from USGS store / forest offices | **Don't wire — no file exists.** Note: FS announced April 2026 it can no longer update or add digital maps to the Avenza store; existing digital maps stay until their paper version is updated, then are removed, not replaced |
| FSTopo 1:24k quads | FS 7.5-minute topo quads, GeoPDF | Yes by construction (tiles the whole forest) | Yes — free via the national "Forest Service Digital Maps" portal (Experience app `9ab8d03e2bec4d7fbfc27ba836e70aed`; series include National, Regional, Admin, Forest, Ranger District, 24K/FSTopo, FSTopo Legacy) | **Don't wire — duplicates the USGS Topo basemap already in the viewer** (same exclusion as the original scope; dozens of tiles) |
| BWCAW canoe-route maps | Superior Box folder, 4 PDFs: LaCroix Hunting Shack Portage; Island River; Timber–Frear; Twin Lakes canoe portage routes | No — canoe routes inside the BWCAW; the NCT (Kekekabic/BRT) runs along the BWCAW's northern edge, not inside it | Yes — free PDFs on the FS public Box (`usfs-public.box.com/s/vfaaap2g0s6o3d0qus347cl300cn7qxf`) | **Don't wire** |
| Superior hiking-trail maps | Superior Box folder, 20 PDFs, one named day-hike sheet per district (list in appendix) | Not a corridor map in any case; two nearest candidates (Gunflint Centennial Trail; Laurentian St Louis River) could not be download-checked (see limits) | Yes — free PDFs on Box (`.../s/vabzliv93e6xothy6il4976tpyh2q7dm`), but direct download is blocked from this VM (static links 404, API 401) | **Don't wire** — all single-trail day-hike sheets; none covers the NCT corridor |
| Superior ski-trail maps | Superior Box folder, 5 files: Flathorn–Gegoka; Pincushion ski area; Tofte Sugarbush–Moose Fence; + 2 `fseprd` files | No (same family as the tested Bally Creek / Norpine-Cascade ski maps, both 0 km) | Yes — free PDFs on Box (`.../s/52oq94hsfqa542xui0d3swcwdtis79si`) | **Don't wire** |
| Superior mountain-bike maps | Superior Box folder, 3 PDFs: Britton Peak & Pincushion; Lookout Mountain; Pincushion Fat Tire | No corridor coverage (small local bike areas) | Yes — free PDFs on Box (`.../s/qhs8uargal1y5s49ew9fp3czn302sl0d`) | **Don't wire** |
| Superior motorized / driving-tour maps | Superior Box folder, 2 PDFs: Laurentian Fall Color Tour; Sawtooth Mountain Driving Tour | No — driving tours | Yes — free PDFs on Box (`.../s/nrlvi4pryrv53y15ndwmks4y9sxk953j`) | **Don't wire** |
| Superior birding maps | Superior Box folder, 3 files: East Zone, West Zone birding maps + forest-wide checklist | No — birding, not trail cartography | Yes — free PDFs on Box (`.../s/uy9p3qglsd5wtw95py32lkgl62r1qnay`) | **Don't wire** |
| Superior hunter walking trail maps | Superior Box folder, 4 PDFs: Caribou Lake; Devil Track; Kadunce River; Wills Lake | No corridor coverage (small local areas) | Yes — free PDFs on Box (`.../s/2edjzd6l0c55intsvvdcedk05jqkx7m6`) | **Don't wire** |
| Chippewa dispersed-camping maps | 22 JPGs, one per area: Blackduck Maps 1, 15–17; Deer River Maps 2–14; Walker Maps 18–22 (`/media/` 253963–253984 → `DispersedCampingMapN.jpg`, 1700×2200) | **Yes — Map 18 (Walker) confirmed visually: the NCT is drawn as a dotted line labelled "NCT" along the west edge and across the bottom (Shingobee area).** Walker/Deer River sheets sit on the corridor; Blackduck sheets mostly north of it | Yes — free JPGs, but **not georeferenced** (no `/Measure`, no world file) | **Don't wire** — ungeoreferenced images; campsite maps, not trail cartography; MVUMs + Topo already cover the same ground. Each sheet prints its campsites' lat/long, which would serve as ground control if manual georeferencing were ever wanted |
| Chippewa grouse-habitat maps | 5 Box folders, one PDF each: `NCGrouseHabitat.pdf`, `NEGrouseHabitat.pdf`, `NWGrouseHabitat.pdf`, `SEGrouseHabitat.pdf`, `SWGrouseHabitat.pdf` | No — habitat maps | Yes — free PDFs on Box | **Don't wire** |
| Interactive Visitor Map | Next-generation online/mobile visitor map (Experience app `a695e1dbdeab4e8ba5c6ad4fd06a0ba0`) | Shows trails interactively | No — interactive only, not a file | **Not wireable** |
| Superior 2026 Camping Recreation Opportunity Guide | Guide PDF (`/media/266115`) | n/a — a guide, not a map | Yes — free PDF | **Don't wire** (not a map) |
| Chippewa LLBO Reservation Restoration Act map | Boundary/restoration-lands map | No | Listed on the Chippewa maps-guides page | **Don't wire** |

Out of scope for this survey (handled separately): the NCTA's own technical map series and the Fish & Wildlife (Tamarac Refuge) maps — both already approved for inclusion by Paul on a separate thread.

## 3. Neighboring forests — Chequamegon-Nicolet and others

The only other national forest anywhere near the Minnesota NCT is the **Chequamegon-Nicolet (Wisconsin)**. Its six MVUM footprints were pulled from the same R9 footprint layer and measured against the NCT line in UTM 15N:

| Chequamegon-Nicolet MVUM | Footprint (lon / lat) | Nearest NCT tread |
|---|---|---|
| Washburn | −91.450..−90.908 / 46.196..46.771 | **64.3 km** |
| Great Divide | −91.245..−90.516 / 45.861..46.432 | 81.8 km |
| Park Falls | −90.385..−89.968 / 45.621..46.001 | 159.7 km |
| Medford | −90.776..−90.326 / 45.092..45.414 | 174.0 km |
| Eagle River–Florence | −89.211..−88.402 / 45.630..46.180 | 208.4 km |
| Lakewood–Laona | −89.138..−88.234 / 45.057..45.770 | 254.1 km |

The forest's other map families (visitor map, FSTopo, recreation maps) cover the same Wisconsin extent. **No map from any neighboring forest reaches the Minnesota NCT.** The corridor's forests are Chippewa + Superior only.

## 4. Newly found that intersects the trail — short list

1. **Superior Border / Vermilion River / Isabella MVUMs — found, but 0 km each.** No new wiring. (The find itself matters: the MVUM set is now provably complete, and the Isabella question is closed.)
2. **Chippewa dispersed-camping maps — do show NCT tread (Map 18 confirmed visually), but not wireable** (ungeoreferenced JPGs). Only newly-found intersecting family in this survey; verdict is don't-wire, with the reason above.
3. Nothing else. Every other family either holds no tread, is app/interactive-only, or duplicates a layer already in the viewer.

## 5. Limits and open threads

- **Superior Box hiking PDFs could not be downloaded from this VM** (shared-static links 404; Box API returns 401 to anonymous shared-link calls). The folder was inventoried by title (20 files, appendix). If Paul wants the two nearest candidates checked by download (Gunflint Centennial Trail; Laurentian St Louis River), that needs a browser session or a Box login — but neither is a corridor sheet by its nature, so the verdict would not change.
- **Forest Visitor Map "West"** (Superior) was not individually confirmed on Avenza; only the East map's listing was read ($4.99, 2018). The family verdict (Avenza-only, no file) does not depend on enumerating all four.
- **FSTopo quad count** for the two forests was not enumerated (dozens of tiles); the verdict rests on duplication of the Topo basemap, not on a count.
- The three new PDFs are in `working/fs-geopdf/` (git-ignored scratch). If the project ever wants the 0-km sheets on record in the repo, they are the files to use; there is no viewer reason to wire them.

## Appendix A — Superior "Download Hiking Trail Maps" Box folder, full inventory

`https://usfs-public.box.com/s/vabzliv93e6xothy6il4976tpyh2q7dm` — 20 PDFs, all single named day-hike sheets:

- Gunflint: Centennial Trail; Egale [sic] Mountain – Brule Lake; Honeymoon Bluff; Moose Viewing
- Kawishiwi: Bass Lake; Secret – Blackstone
- LaCroix: Astrid Lake; Big Moose; Echo Lake; Herriman; Norway Trail; Vermillion Falls; Vermillion Gorge
- Laurentian: Big Aspen; Deepwater; Jenkins Creek; Lookout Mountain; Otto and Harris Lakes; St Louis River
- Tofte: Oberg Mountain and LeVeaux Mountain

## Appendix B — Sources used

- Superior MVUM publications page: `https://www.fs.usda.gov/r09/superior/multimedia/publications/motor-vehicle-use-maps`
- Superior maps-guides page: `https://www.fs.usda.gov/r09/superior/maps-guides`
- Chippewa maps-guides page: `https://www.fs.usda.gov/r09/chippewa/maps-guides`
- R9 MVUM Finder app: `https://experience.arcgis.com/experience/326948b1c4944f4aae9ae4ab20448109` (config + webmap via ArcGIS sharing API; footprint layer `R9MVUMFootprints`, `services1.arcgis.com/gGHDlz6USftL5Pau/arcgis/rest/services/R9MVUMFootprints/FeatureServer/0`)
- Forest Service Digital Maps portal: `https://experience.arcgis.com/experience/9ab8d03e2bec4d7fbfc27ba836e70aed/page/Home/`
- National visitor-map finder: `https://www.fs.usda.gov/mapfinder/`
- Superior NF Forest Visitor Map – East (Avenza): `https://store.avenza.com/products/superior-national-forest-east-visitor-map-us-forest-service-r9-map` ($4.99, 2018, Avenza-exclusive)
- Chippewa NF Forest Visitor Map (Avenza): `https://store.avenza.com/products/chippewa-nf-forest-visitor-map-us-forest-service-r9-map-1`
- Superior Box folders (canoe / MTB / ski / motorized / birding / hunter / hiking) and Chippewa Box folders (grouse habitat ×5) on `usfs-public.box.com`, linked from the forests' maps-guides pages
- Method: system python3, shapely 2.2.0 + pyproj 3.8.0; 50 m sampling of `site/data/trail-minnesota.geojson` vs `/Measure` viewport quads (pypdf, DNR venv); sampler validated against the recorded per-sheet `trail_km` and the 902.80 km trail total in `docs/forest-service-geopdf-layers-2026-11-16.md`

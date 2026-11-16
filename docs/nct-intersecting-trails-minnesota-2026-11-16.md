# Trails that intersect the North Country Trail in Minnesota

**Date:** 2026-11-16
**Reference line:** the chapter map's Minnesota NCT line, `site/data/trail-minnesota.geojson` (348 features, 7,144 points, 559.3 mi). Every distance below is the shortest distance from the named trail's geometry to that line, computed in UTM 15N (shapely 2.2.0 / pyproj 3.8.0). **Tolerance: 50 m.** A trail counts if its tread physically crosses, meets, or shares tread with the NCT — including trails that terminate at the NCT and trails that share a section of tread. Named trails only; unnamed forest roads and unnamed spurs are excluded unless a named trail uses them. Water routes (rivers, canoe routes) are excluded from the tables and listed separately at the end.

## Headline counts

- **89 distinct named trails verified** as meeting the NCT in Minnesota (43 table rows; several rows bundle named spurs/portages of one system).
- **Already on the map as a separate layer: 0.** The only intersections already drawn are the two shared-tread cases — the Border Route Trail and the Central Lakes State Trail — which coincide with the NCT line itself. The Waboose Lake Loop and Lake Erin Loop are staged in `data/loops/` (2026-11-16) but not yet wired into `site/app.js`.
- **Could not verify: 5** (see § "Could not verify").
- **Checked and do NOT meet the NCT: 30 named trails** (see § "Checked and do not meet").

## Sources and method

1. **USFS National Forest System Trails** (EDW_TrailNFSPublish_01, layer 0) — 3,502 features in the NCT envelope, pulled 2026-11-16. **71 named trails ≤ 50 m** (66 distinct trails after merging hiking/ski twins of the same tread; one is the Boy River Canoe Route, a water route, excluded).
2. **Minnesota DNR enterprise services** (enterprise.gisdata.mn.gov, pulled 2026-11-16): `trans_state_trails_minnesota` (647 features) — 6 named trails ≤ 50 m; `trans_state_park_trails_roads` (1,996 features) — 8 named trails ≤ 50 m (two are water routes, excluded); `trans_hunter_walking_trails` (188 features) — 3 named trails ≤ 50 m.
3. **OpenStreetMap** (api.openstreetmap.org bbox fetches, 2026-11-16; Overpass was unreachable from this VM — 406/502/connection failures on all three mirrors, not retried). Used for trails absent from the DNR/USFS services: Mesabi Trail, Ancient Cedars, Crosscut, Miner's, Lake Twentyone / Nelson Lake, and the three Itasca State Park trails. OSM geometry is ODbL — any OSM-derived line put on the map needs an OSM attribution line on the data-sources page.
4. **Published lengths** are marked "published"; otherwise the length is the length in the source file (TrailNFS `gis_miles` or the DNR file), which for most trails is the full Minnesota length.

**Caveat on lengths:** TrailNFS lengths are the lengths in the pulled envelope; DNR file lengths are the lengths in that file. Where the file figure is clearly a subset of the published length, both are given. OSM lengths are the lengths of the named ways inside the fetched bbox and can be partial where the bbox cut a trail — marked "in bbox".

**Raw pulls** (ephemeral, `/tmp/nct-trails/` — re-derivable, not durable): `trailnfs-0.geojson`, `dnr_state_trails-0.geojson`, `dnr_park_trails-0.geojson`, `dnr_hunter_trails-0.geojson`, `hits-trailnfs.json`, `hits-dnr_state.json`, `hits-dnr_park.json`, `hits-dnr_hunter.json`, `osm-*.osm`, `osm-results.json`, `osm-lengths.json`. The durable geometry is the live services themselves plus the loop files in `data/loops/`.

## A. Long-distance trails — shared tread or termini

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Superior Hiking Trail | DNR | hiking | Northern terminus, 47.98833,-89.93524 — near Grand Portage (11.8 mi) / 270° Overlook | ~310 mi published (146 mi in DNR park file) | DNR `trans_state_park_trails_roads`, in hand | No |
| Border Route Trail | USFS (Superior NF) | hiking, **shared tread** with the NCT | Shares tread along the border; sample point 48.06433,-90.05731 — South Fowl Lake area, near Grand Portage | 46 mi in TrailNFS envelope; ~65 mi published | USFS TrailNFS, in hand | Shared tread is drawn as the NCT itself — no separate layer |
| Kekekabic Trail | USFS (Superior NF) | hiking | 48.04426,-91.19582 — BWCAW, between Snowbank and Kekekabic lakes (nearest town Winton, 29 mi) | 31 mi in TrailNFS; ~41 mi published | USFS TrailNFS, in hand | No |
| Mesabi Trail | St. Louis & Lake Counties Regional Railroad Authority | paved multi-use | Tower 47.80714,-92.25761 (0 m) and Ely 47.90217,-91.87526 (0 m) and 47.90568,-91.82981 (1 m, as "Mesabi Range Trail") | 165 mi planned, ~160 paved (Rails-to-Trails, Oct 2025) | OSM (not in any DNR service), in hand | No |
| Central Lakes State Trail | DNR | paved state trail, **shared tread** through Fergus Falls | 46.26755,-96.04261 — Fergus Falls (1.9 mi); the NCT's own features there carry seg_name "Central Lakes Trail" | 55.21 mi | DNR `trans_state_trails_minnesota`, in hand | Shared tread is drawn as the NCT itself — no separate layer |

Notes: the SHT meets the NCT **only at its northern terminus** — its southern terminus near Jay Cooke State Park is ~0.9 km from the NCT (nearest OSM way 936 m) and does not meet it. The Mesabi Trail is verified at Tower and Ely; possible additional crossings near Virginia/Eveleth were not checked (see § "Could not verify").

## B. DNR state trails

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Paul Bunyan State Trail | DNR | paved state trail | 47.03137,-94.54611 — near Walker (5.1 mi); OSM confirms 0 m at 47.04954,-94.64211 | 115.04 mi | DNR `trans_state_trails_minnesota`, in hand | No |
| Heartland State Trail | DNR | paved state trail | 47.04957,-94.64218 — near Walker (4.5 mi) | 46.64 mi | DNR `trans_state_trails_minnesota`, in hand | No |
| Taconite State Trail | DNR | multi-use (hike / ski / snowmobile) | 47.28583,-93.49064 — near Grand Rapids / Coleraine (3.2 mi) | 110.43 mi | DNR `trans_state_trails_minnesota`, in hand | No |
| David Dill–Taconite State Trail | DNR | multi-use | 47.80079,-92.27745 — Tower; OSM confirms 2.0 m at 47.80731,-92.25369 | 37.96 mi | DNR `trans_state_trails_minnesota`, in hand | No |
| Alex Laveau Memorial State Trail | DNR | paved state trail | 46.59924,-92.29082 — near Jay Cooke State Park / Thomson (OSM 44 m, DNR 70 m — within mapping tolerance) | 9.85 mi | DNR `trans_state_trails_minnesota` + OSM cross-check, in hand | No |

Note: the Taconite appears in both DNR files (110.43 mi in the state-trails file, 82.08 mi in the park file) — one row, not two. The Paul Bunyan and Heartland trails converge at Walker and the NCT crosses both in the same area.

## C. Itasca State Park trails (DNR)

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Ozawindib Trail | DNR (Itasca State Park) | hiking | 47.15419,-95.17045 — Itasca State Park, near Lake George (9.1 mi) | ~13 mi published; 2.8 mi in OSM bbox (partial) | OSM, in hand — the DNR park file's 124 Itasca features are all unnamed and the nearest is 3.9 km from the NCT, so the DNR file carries no usable Itasca trail geometry | No |
| Deer Park Trail | DNR (Itasca State Park) | hiking | 47.14974,-95.20599 — Itasca State Park, near Lake George (10.8 mi) | 3.9 mi in OSM bbox (may be partial) | OSM, in hand | No |
| DeSoto Trail | DNR (Itasca State Park) | hiking | 47.15159,-95.21061 — Itasca State Park, near Lake George (10.9 mi) | 3.0 mi in OSM bbox (may be partial) | OSM, in hand | No |

Notes: the NCT through Itasca State Park is locally the **Eagle Scout Trail** — OSM names the NCT way "Eagle Scout Trail (NCT)" there; it is the NCT's own tread, not a separate intersecting trail. The NCT clips the park's southern tier; the rest of the park's trail system (Brower, Aiton Heights, DeSoto Lake, Okerson Heights, Red Pine, McKay/Myrtle Lake crossovers, Preacher's Grove, Mary Lake, Indian Mounds, Dr Roberts, Sawmill, No-Name, Merschman-Thompson, Mississippi Headwaters) is 1–10 km from the NCT and does not meet it.

## D. Paul Bunyan State Forest trails (DNR)

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Lake Twentyone Trail + Nelson Lake Trail | DNR (Paul Bunyan State Forest) | hiking loop system | Nelson Lake Trail 0 m at 47.15303,-94.84652 — near Laporte (6.1 mi); the Lake Twentyone Trail connects to the NCT via the Nelson Lake Trail (its own OSM ways 490 m from the NCT; trailhead 47.161752,-94.841417, Gulch Lake Campground) | 2.4 mi loop published; OSM 1.25 + 1.01 mi for the two named ways | OSM, in hand | No |
| Waboose Lake Loop | DNR (Paul Bunyan State Forest) | hiking loop | 47.05808,-94.83295 — Waboose Lake, near Laporte; OSM 3.0 m; east side (0.37 mi) IS the NCT tread | 3.64 mi assembled; 3.9 mi published | OSM ways 846251459 + 846251460 + NCT way 846251458; durable file in `data/loops/waboose-loop.geojson` | **Staged in `data/loops/`, not yet wired into `site/app.js`** (approved by Paul 2026-11-16) |
| Hubbel Pond Hunter Walking Trail | DNR | hunter walking trail | 46.83444,-95.63899 — near Frazee (7.9 mi) | 26.61 mi | DNR `trans_hunter_walking_trails`, in hand | No |
| Paul Bunyan (NW) Hunter Walking Trail | DNR | hunter walking trail | 47.13969,-94.83528 — near Laporte (6.4 mi) | 40.39 mi | DNR `trans_hunter_walking_trails`, in hand | No |
| Paul Bunyan (SE) Hunter Walking Trail | DNR | hunter walking trail | 47.06836,-94.82896 — near Waboose Lake / Akeley (6.8 mi) | 24.80 mi | DNR `trans_hunter_walking_trails`, in hand | No |

Note: the DNR has **no GIS line for the Waboose Lake Loop** — verified against the DNR enterprise `trans_*` inventory (no state-forest hiking-trail layer exists); its only official representation is the Paul Bunyan & Badoura State Forest map GeoPDF. The loop's geometry here is OSM community traces, not the chapter's own track — chapter sign-off is worth getting before it goes live.

## E. Chippewa National Forest trails (USFS)

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Lake Erin Loop | USFS (Chippewa NF) | hiking loop | 47.01462,-94.53523 — 7 mi SE of Walker on Hwy 371 (TrailNFS 32.7 m; trailhead 47.016017,-94.535922) | 0.61 mi | USFS TrailNFS ("LAKE ERIN HIKING", no. 34914, class 3), in hand; durable file in `data/loops/lake-erin-loop.geojson` | **Staged in `data/loops/`, not yet wired into `site/app.js`** (approved by Paul 2026-11-16) |
| Shingobee Trail | USFS (Chippewa NF) | hiking (+ ski, same tread) | 47.03932,-94.62726 — near Walker / Shingobee Campsite (4.7 mi); OSM "Shingobee Trail" confirms 5.2 m | 3.24 mi | USFS TrailNFS, in hand | No |
| Goose Lake trails (hiking + ski + spurs) | USFS (Chippewa NF) | hiking + cross-country ski | Spurs B/C/E reach the NCT at 0 m: 46.99331–46.99663,-94.31321–-94.33876 — near Longville (5.7 mi). The main Goose Lake Hiking / X-Country Ski loops sit 61.5 m off the NCT and connect via the spurs. | 7.19 mi hiking; spurs 0.08–0.47 mi each | USFS TrailNFS, in hand | No |
| CR 50 Hunter Walking Trail | USFS (Chippewa NF) | hunter walking trail | 47.03015,-94.57103 — near Walker (4.9 mi); Spur H also reaches the NCT at 1.0 m | 3.27 mi (+ Spur H 0.39 mi) | USFS TrailNFS (admin org 090305 = Chippewa NF), in hand | No |
| Grant-in-aid snowmobile trails (Soo Line, Triville, Chippewa "C") | DNR grant-in-aid, on USFS land | snowmobile | Soo Line 47.10263,-94.02260 near Remer (5.8 mi); Triville 47.03000,-94.23405; Chippewa "C" 47.03134,-94.54610 near Walker; Chippewa "C" Spur A 47.00669,-94.45964 | Soo Line 50.76 mi; Triville 22.01 mi; Chippewa "C" 19.86 mi; Spur A 3.98 mi | USFS TrailNFS, in hand | No |

Note: the Goose Lake and Shingobee hiking/ski pairs are the same tread under two names (TrailNFS carries both). Spurs that do **not** reach the NCT (Goose Lake D/I/J/L/N, Shingobee A/B/I/J, CR 50 A/B/C/D — 143–479 m away) are not listed as intersections.

## F. Superior National Forest / BWCAW hiking and winter trails (USFS)

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Snowbank Trail | USFS (Superior NF) | hiking | 47.95705,-91.39104 — Snowbank Lake, near Ely (19 mi); 9.4 m | 14.46 mi | USFS TrailNFS, in hand | No |
| Old Pines Loop | USFS (Superior NF) | hiking loop | 47.98678,-91.28293 — BWCAW, near Ely (24 mi) | 8.80 mi | USFS TrailNFS, in hand | No |
| Benezie–Becoosin Loop | USFS (Superior NF) | hiking loop | 47.95450,-91.39687 — Snowbank Lake area, near Ely (19 mi) | 1.78 mi | USFS TrailNFS, in hand | No |
| Magnetic Rock Trail | USFS (Superior NF) | hiking | 48.09204,-90.82489 — off the Gunflint Trail, near Hovland (31 mi) | 3.98 mi | USFS TrailNFS, in hand | No |
| Caribou Rock Trail | USFS (Superior NF) | hiking | 48.09224,-90.44460 — off the Border Route, near Hovland (19 mi); 22.4 m | 3.84 mi | USFS TrailNFS, in hand | No |
| Bridal Veil Falls Trail | USFS (Superior NF) | hiking spur | 48.09104,-90.63552 — off the Border Route, near Hovland (24 mi) | 0.46 mi | USFS TrailNFS, in hand | No |
| Bryce Breon Trail | USFS (Superior NF) | hiking | 48.08488,-90.70598 — Gunflint Trail area, near Hovland (26 mi) | 2.32 mi | USFS TrailNFS, in hand | No |
| Centennial Trail | USFS (Superior NF) | hiking | 48.08877,-90.82542 — Gunflint Trail area, near Hovland (31 mi) | 3.17 mi | USFS TrailNFS, in hand | No |
| Gunflint Lookout Trail | USFS (Superior NF) | hiking spur | 48.08848,-90.83464 — Gunflint Trail area; 1.1 m | 0.64 mi | USFS TrailNFS, in hand | No |
| Kekekabic to Magnetic Rock | USFS (Superior NF) | hiking connector | 48.08888,-90.82485 — Gunflint Trail area | 0.33 mi | USFS TrailNFS, in hand | No |
| Upper Gunflint ski trail system | USFS (Superior NF) | cross-country ski | 48.077–48.094,-90.74–-90.79 — Gunflint Trail area, near Hovland (29 mi). Nine named trails reach the NCT: West End, South Rim, Overlook, Cut Across, Aspen Rabbit, Power Line, Lonely Lake (41.5 m), Short Cut (2.4 m), Warrens Road (1.0 m); plus G Connect (0.84 mi, 0 m at 48.08116,-90.76124) | 0.76–6.74 mi each (West End 6.74, South Rim 6.59, Lonely Lake 4.63, Warrens Road 2.32, Aspen Rabbit 1.59, Cut Across 1.39, Power Line 1.22, Overlook 1.15, Short Cut 0.76) | USFS TrailNFS, in hand | No |
| South Fowl snowmobile + ATV | USFS (Superior NF) | snowmobile + ATV | 48.03759–48.05132,-90.01429–-90.04716 — South Fowl Lake, near Grand Portage (18 mi) | Snowmobile 1.74 mi; ATV 0.84 mi | USFS TrailNFS, in hand | No |
| Thomas Lake Winter + Thirteen Corners | USFS (Superior NF) | winter trail (ski/snowmobile) | Thomas Lake Winter 47.99234,-91.26968 near Ely (25 mi); Thirteen Corners 47.92512,-91.78583 near Ely | 9.41 mi + 1.82 mi | USFS TrailNFS, in hand | No |
| Madden Winter | USFS (Superior NF) | winter trail | 47.95819,-91.60554 — near Ely (9.2 mi); 1.8 m | 0.59 mi | USFS TrailNFS, in hand | No |
| Hidden Valley Trezona + Trezona | USFS (Superior NF) | hiking spur | 47.90572,-91.82976 and 47.90565,-91.82987 — Ely (1.7 mi); Trezona 10.6 m | 0.88 mi + 0.25 mi | USFS TrailNFS, in hand | No |

Note: the Upper Gunflint Amperage (103.5 m), North Star (143 m), Big Pine (167 m), Rabbit Run (176 m), Highlands (178 m) and Connector (296 m) ski trails do **not** reach the NCT — they are near-misses, not intersections.

## G. BWCAW portages and connectors (USFS, one group row — 26 named)

These are the short lake-to-lake portages and campsite spurs that touch the NCT/Border Route tread in the Boundary Waters. They are real named trails in the TrailNFS data, but they are portages, not hiking trails — listing each as its own map line would be clutter. One group row; the names, lengths and meeting points are:

| Trail group | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| BWCAW portages & connectors (26 named) | USFS (Superior NF) | portage / connector / campsite spur | Along the Border Route / BWCAW tread, 47.95–48.10,-90.17–-91.63 — near Ely, Hovland and Grand Portage | 0.03–3.67 mi each | USFS TrailNFS, in hand | No |

Members (name — length — distance to NCT): Agamok–Mueller 0.15 mi (44.7 m); Border Route Connector 2.07 mi (11.5 m); BRT–Clearwater Lake Campsite 0.32 mi (0 m); BRT–Partridge Campsite 0.40 mi (9.6 m); BRT–Sock Lake Campsite 0.33 mi (0 m); Topper Lake Campsite Spur 0.03 mi (9.3 m); Clearwater–West Pike 0.27 mi (3.7 m); Clearwater / Daniels Lake 1.70 mi (8.6 m); Crab Lake Cut-Off 0.63 mi (4.4 m); Crab Lake–Main BRT 2.29 mi (11.4 m); Fay–Warclub 0.10 mi (0 m); Glee–Bingshick 0.14 mi (0 m); Glee–Fay 0.07 mi (0 m); Hatchet Creek–Hatchet Pond 0.14 mi (0 m); Kobe–Thomas 2.27 mi (0 m); Mountain–Clearwater 0.25 mi (0 m); Rose–Duncan 0.24 mi (0 m); Rose–Rove 2.02 mi (0 m); South Lake 3.67 mi (0 m); South Lake–Topper Lake 0.25 mi (0 m); Warclub–Seahorse 0.04 mi (5.7 m); West Pike–Pine 1.00 mi (0 m); Wood Lake 0.78 mi (30.9 m); Sourdough Creek 1.02 mi (12.4 m); Fernberg Area 0.06 mi (1.7 m); Kekekabic–Strup 0.27 mi (0 m).

Not in this group (near-misses, 130–470 m — the portage does not reach the NCT): Little John–John Lake (130 m), East Pike–West Pike (156 m), Hatchet River–Hatchet Creek (193 m), Thomas–Hatchet Pond (204 m), Bingshick–Bingshick River (244 m), Bingshick–Flying (398 m), Watap–Moutain (405 m), Mucker Lake–Main BRT (423 m), Fay Lake–Flying Lake (451 m), John–East Pike (470 m), Disappointment–Muzzle (386 m).

## H. Tower / Iron Range local trails

| Trail | Manager | Type | Where it meets the NCT | Length in MN | Geometry source & status | On the map? |
|---|---|---|---|---|---|---|
| Ancient Cedars Trail | City of Tower | hiking loop | 47.80252,-92.27448 — Tower (OSM 3.5 m); accessed off the Mesabi Trail / David Dill–Taconite State Trail; 1.9-mi loop through old-growth white cedar, completed summer 2020 | 1.9 mi published; 1.4 mi in OSM bbox | OSM, in hand; cityoftower.com/recreation confirms the trail | No |
| Crosscut Trail | Not established (likely a grant-in-aid snowmobile trail) | snowmobile-designated path | 47.81904,-92.21969 — Bear Head Lake area, near Soudan (1.3 mi); 0 m | 2.48 mi in OSM bbox | OSM only, in hand | No |
| Miner's Trail | Not established | foot / bike / snowmobile-designated | 47.82097,-92.22656 — Bear Head Lake area, near Soudan (1.1 mi); 5.5 m | 1.65 mi in OSM bbox | OSM only, in hand | No |
| "Park Trail" (DNR generic name) | DNR | paved park paths | 47.81198,-92.24918 — Soudan area; 0 m, 26 segments statewide totalling 0.77 mi, surface concrete | 0.77 mi total (generic name, statewide) | DNR `trans_state_park_trails_roads`, in hand — but the name is generic and the data does not say which park these segments belong to (nearest park is Lake Vermilion–Soudan Underground Mine State Park) | No |

## Could not verify

1. **Beaver Lakes Trail** (Paul Bunyan State Forest) — a known hiking trail in the forest (AllTrails lists it among the forest's top trails; most elevation gain in the forest, 182 m), but no OSM way by that name was found in any bbox fetched along the NCT corridor, and it is in none of the DNR/USFS services pulled. What would settle it: its location — the DNR's Paul Bunyan & Badoura State Forest map GeoPDF, or a chapter member who knows where the Beaver Lakes sit relative to the NCT.
2. **Island Lake Trail** (Paul Bunyan State Forest) — AllTrails' longest trail in the forest; same situation as Beaver Lakes: no geometry found near the NCT. What would settle it: the same DNR forest map, or a pin from someone who has walked it.
3. **Additional Mesabi Trail crossings near Virginia / Eveleth** — verified at Tower and Ely only. The Mesabi Trail runs through Virginia and Eveleth and the NCT passes through the same towns, so further crossings are likely, but the Virginia OSM bbox failed (HTTP 400, node limit) and was not re-fetched. What would settle it: a smaller OSM bbox over Virginia, or the Mesabi Trail's own GIS line from the Regional Railroad Authority.
4. **Gunflint Snowmobile Trail** — TrailNFS nearest 52.7 m from the NCT, just outside the 50 m tolerance. It very likely crosses (mapping error alone could explain 53 m), but it was not counted as verified. What would settle it: a look at the trail's line against the NCT line on the ground or in the USFS data at higher precision.
5. **"Park Trail" park identity** (§H) — the crossing itself is verified (0 m), but the DNR data does not say which park the segments belong to. What would settle it: the Soudan / Bear Head Lake / Lake Vermilion park maps, or the DNR's park-trail attribute table keyed by project code SPK00172.

## Checked and do NOT meet the NCT

- **Gitchi-Gami State Trail** — nearest 36.8 km (hugs Hwy 61 along the shore; the NCT/BRT runs inland).
- **Willard Munger State Trail** — nearest 8.7 km (Duluth area).
- **C.J. Ramstad / North Shore State Trail** — nearest 31.9 km.
- **David Dill–Arrowhead State Trail** — nearest 7.4 km (its eastern segment, the David Dill–Taconite, does meet — §B).
- **Matthew Lourey State Trail** — nearest 11.4 km. **Gandy Dancer State Trail** — 14.5 km. **Blue Ox State Trail** — 57.1 km. **Cuyuna Lakes State Trail** — 61.2 km. **Alborn–Pengilly Railroad State Trail** — 798 m (nearest miss among state trails).
- **Superior Hiking Trail, southern terminus** — nearest OSM way 936 m near Jay Cooke State Park; the SHT meets the NCT only at its northern terminus (§A).
- **Soo Line Trail – Southern Route** — 353 m near Jay Cooke. **Trezona Trail** (Ely) — 265 m. **Prospector OHV** (Ely) — 429 m in TrailNFS, 120 m in OSM. **Snoway 1 GIA Snowmobile** — 380 m. **Laurentian Snowmobile** — 386 m.
- **Itasca State Park trails that do not meet it:** Mississippi Headwaters Trail (4.3 km), Brower Trail (4.2 km), Aiton Heights (3.3 km), DeSoto Lake Trail (512 m), Okerson Heights (1.1 km), Red Pine (1.1 km), McKay / Myrtle Lake crossovers (~2 km), Preacher's Grove (5.1 km), Mary Lake (3.4 km), Indian Mounds (9.9 km), Dr Roberts (4.0 km), Sawmill (10.1 km), No-Name (9.9 km), Merschman-Thompson (7.0 km). The Heartland State Trail is 3.0 km from the NCT inside Itasca State Park — it meets the NCT near Walker instead (§B).

## Water crossings (not trails — the NCT crosses the river, not a trail)

- **Otter Tail River** — 0 m at 46.81320,-95.69056 (near Frazee); DNR water-trail line, 159.31 mi.
- **Red River of the North** — 0 m at 46.44427,-96.71618 (the NCT's western end, near Moorhead); DNR water-trail line, 143.61 mi.
- **Boy River Canoe Route** — 0 m at 47.04447,-94.10989 (TrailNFS, 31.55 mi).
- The NCT also crosses the **St. Louis River** at Jay Cooke State Park (swinging bridge) and the **Crow Wing River** in the chapter area, but the DNR water-trail lines for those sit 4.5–5.5 km from the NCT line in the files pulled, so they are not listed as verified crossings here.

## Recommendation

Add first, as one new "Intersecting trails" layer (off by default, like parcels): the five long-distance trails (§A) and the five DNR state trails (§B) — those are the lines a hiker actually uses to reach or leave the NCT, and their geometry is already in hand from the DNR and USFS services. Second, the chapter-area trails: the three Itasca State Park trails (§C), the Paul Bunyan State Forest set (§D — Waboose and Lake Erin are already staged and approved), and the Chippewa NF set (§E). The Superior NF / BWCAW hiking trails (§F) come third — they matter mostly in the Arrowhead, where the map's audience is thinner. The BWCAW portages (§G) should be a separate, very light layer or left out entirely: 26 short portage stubs add clutter without helping a hiker plan. Hunter walking trails (§D) and the snowmobile/ATV trails (§E, §F) are seasonal-use lines; if they go on at all, they belong off by default and clearly labelled by season. Before any OSM-derived line goes live (Waboose, Lake Erin is USFS so it is fine, Ancient Cedars, Crosscut, Miner's, the Itasca SP trails, Lake Twentyone/Nelson Lake), add the OSM attribution line to the data-sources page — ODbL requires it — and get chapter sign-off on the Waboose line, which is OSM community traces rather than the chapter's own track.

## Sources

- USFS National Forest System Trails, EDW_TrailNFSPublish_01, layer 0 — https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer (refreshed 2026-11-15; pulled 2026-11-16).
- Minnesota DNR enterprise services, enterprise.gisdata.mn.gov — `trans_state_trails_minnesota`, `trans_state_park_trails_roads`, `trans_hunter_walking_trails` (layer 0 of each; pulled 2026-11-16). Also checked and empty of intersections: `trans_state_forest_roads`, `trans_ohv_trails_mn`, `trans_snowmobile_trails_mn`, `trans_water_trails_minnesota` (water routes only).
- OpenStreetMap, api.openstreetmap.org/api/0.6/map (bbox fetches, 2026-11-16) — ODbL. Overpass was unreachable from this VM on 2026-11-16 and was not retried.
- Mesabi Trail length/manager: Rails-to-Trails Conservancy, "Minnesota's Mesabi Trail: October 2025 Trail of the Month" (165 mi, St. Louis & Lake Counties Regional Railroad Authority); LCCMR Mesabi Trail work-plan report (2020_09q).
- Ancient Cedars Trail: City of Tower, cityoftower.com/recreation (1.9-mi loop, completed summer 2020).
- Lake Twentyone / Nelson Lake Loop: AllTrails (2.4-mi loop, near Laporte); onX Backcountry (trailhead 47.161752,-94.841417; Gulch Lake Campground connects directly to the NCT).
- Waboose Lake Loop and Lake Erin Loop: `data/loops/README-2026-11-16.md` in this repo.
- NCT reference line: `site/data/trail-minnesota.geojson` (348 features, 559.3 mi).

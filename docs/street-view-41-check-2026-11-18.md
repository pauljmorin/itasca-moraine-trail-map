# Street View check — 41 candidates, 2026-11-18

Checked 2026-11-18, 12:40–1:29 PM CST, in the browser. Result: **26 PASS, 15 FAIL**. Failed candidates stay out. Check only — no files edited.

## How the checks were done

Each pano URL was opened in the browser (retried once when it landed on the map instead of Street View). Two limits of the browser's mobile Street View client affect the table:

- **Imagery date** — no date is shown in the UI, so the date is the year in the faint on-image watermark "© YYYY Google". Only the year is reported; where the year could not be read confidently it is recorded as "not legible".
- **Heading** — the heading parameter in the pano URL is unreliable: on some first loads it applies, on others the viewer restores a persisted/default heading and ignores it. Where the viewed heading did not match the suggestion, the road direction was determined from the frame geometry plus a map view; those confirmations are marked "(map-based)". A few panos needed a drag to verify the heading.

## Results

| # | Pass/Fail | Imagery date | Heading (confirmed or corrected) | Notes |
|---|-----------|--------------|----------------------------------|-------|
| 1 | PASS | ©2026 | 228 confirmed | Kawishiwi Ranger Station entrance road runs SW; main road NE at 48°. |
| 2 | PASS | not legible | CORRECTED ~180° (from 229°) | Kawishiwi Falls Trailhead; at 229° the trailhead sign is just out of frame left and the view is forest/Fernberg Rd crossing the foreground; rotating ~50° left centres the sign and the dirt track leaving the lot. |
| 3 | PASS | ©2025 | 6 confirmed | Forest History Rd runs straight N ahead. |
| 4 | PASS | ©2026 | 89 confirmed | 14th Ave SW, Grand Rapids, runs straight E. |
| 5 | PASS | ©2026 | 89 confirmed | Trekker (on-foot) pano on a grassy park trail (E–W) between SW 12th Ave and SW 11th Ave; view E is dominated by a white garage at the trail's east end. |
| 6 | PASS | not legible | CORRECTED ~120° (from 228°) | Corey St/US-169 at the Mesabi Trail; at 228° the road is seen edge-on with trail-side woods beyond and no path visible; road runs ESE–WNW, ~120° is ESE along it. |
| 7 | PASS | not legible | 359 confirmed | Co Rd 76 runs N ahead to a junction (Jeep crossing). |
| 8 | PASS | not legible | CORRECTED ~100° (from 9°) | North Country Trail / Mesabi Trail parking area; at 9° the view is across the E–W road into forest N; the Mesabi Trail leaves the parking area ESE (~100°). |
| 9 | PASS | ©2026 | 50 confirmed | Town street (S Second St); road curves NE ahead. |
| 10 | PASS | ©2025 | 90 confirmed | Grassy field/trail just south of Hwy 22 (E–W); looking E across crop field, N–S power line crosses. |
| 11 | PASS | not legible | 96 confirmed (map-based) | Broadway bridge over the Red River (ND/MN border); Broadway runs E–W, 96° is E along it. Pano opened at its default southward view down the river, not at 96°. |
| 12 | PASS | ©2020 | 352 confirmed | Co Hwy 3 runs NNW ahead. Map check: DATA GAP — no foot trail at this spot; Co Hwy 3 is continuous and meets Hwy 24 (Otter Trail Scenic Byway) just north; the break is a data segmentation at/near the junction, not a trail on/off point. |
| 13 | FAIL | n/a | n/a (suggested 0°) | No Street View imagery. Pano URL falls back to the map twice (Maplewood State Park / North Lida Lake); tapping the road on the 17z map opens nothing. Viewpoint is on a N–S Maplewood State Park road just south of where it becomes the North Country Trail; the road has no SV coverage. |
| 14 | PASS | ©2026 | 58 confirmed | City Beach Rd runs NE ahead to a junction with a cross road (STOP sign). |
| 15 | PASS | ©2024 | 336 confirmed | Road runs NNW ahead; side road/driveway to the right (E). |
| 16 | PASS | ©2024 | 19 confirmed | E Wymer Lake Rd (gravel) runs NNE ahead, curving right. |
| 17 | PASS | ©2025 | 104 confirmed (map-based) | Hwy 228 runs WNW–ESE (~104–105° ESE); lake to the south. Pano opened at a default NNE view with the road edge-on, not at 104°. |
| 18 | FAIL | n/a | n/a (suggested 271°) | No Street View imagery. Pano URL falls back to the map twice (Frazee area); tapping 120 St on the 17z map opens nothing. Viewpoint is in a field just south of 120 St (E–W rural township road, north of Frazee), which appears to have no SV coverage. |
| 19 | FAIL | n/a | n/a (suggested 320°) | A pano exists but it is on a private driveway (photosphere) off the road, not on W Wymer Lake Rd; at 320° it shows a lawn/driveway and house, not the road. Suggested 320° is the direction of W Wymer Lake Rd (NW–SE) but the pano does not show the road. Map check: DATA GAP — W Wymer Lake Rd is continuous NW–SE on the east shore of Wymer Lake; no foot trail, trailhead or park at this spot. |
| 20 | PASS | ©2024 | 5 confirmed | Map check: REAL TRAIL ON/OFF POINT — signed North Country Trail / Hubbel Pond trailhead on Hwy 34 (North Country Scenic Byway); the trail leaves the road heading N into the woods; the SV at 5° shows the grassy trailhead area and woods N (no distinct footpath visible in the pano). |
| 21 | PASS | ©2025 | 359 confirmed | Co Hwy 29 runs straight N ahead. |
| 22 | FAIL | n/a | n/a (suggested 90°) | No Street View imagery. Pano URL falls back to the map twice (Brushvale / MN-9 area); tapping MN-9 on the map opens nothing. Viewpoint is in a field west of MN-9 (the N–S road-walk road); the pano API finds no imagery at this off-road viewpoint. |
| 23 | FAIL | n/a | n/a (suggested 0°) | No Street View imagery. Pano URL falls back to the map twice (Brushvale / MN-9 area). Viewpoint is in a field west of MN-9, off the road, like #22. |
| 24 | PASS | ©2026 | 90 confirmed | At the junction of 3rd Ave SW (E–W, the road-walk) and 3rd St SW (N–S); at 90° the view is E along 3rd Ave SW through the junction, with 3rd St SW crossing in the foreground and trees beyond. |
| 25 | PASS | not legible | 130 confirmed (map-based) | 179th Ave / County Rd 88 runs NW–SE; 130° is SE along it. Pano opened at a NE view (road edge-on), so the viewer must set heading 130°. |
| 26 | PASS | ©2025 | 163 confirmed | County Rd 88 runs N–S (curving SE); at 163° the road runs SSE ahead, curving left (SE) in the distance, with a red barn to the right. |
| 27 | FAIL | n/a | n/a (suggested 205°) | No Street View imagery. Pano URL falls back to the map twice (Fergus Falls / Parkdale area). Viewpoint is in lake country near Parkdale (SE of Fergus Falls), off the main roads. |
| 28 | PASS | ©2026 | 90 confirmed | Trekker pano in the grassy field just north of 245th St (E–W); at 90° it looks E across the field toward a farm building, and a N–S dirt track crosses in front (likely the trail). The road itself is just to the south and is not in the 90° view. |
| 29 | FAIL | n/a | n/a (suggested 90°) | No Street View imagery. Pano URL falls back to the map twice (Fergus Falls / Wall Lake area). Viewpoint is in a field north of Wall Lake / north of US-210, off the road. |
| 30 | PASS | ©2025 | 313 confirmed (map-based) | Otter Trail Scenic Byway (County Rd 3) runs NW–SE through the spot; 313° is NW along it. Pano opened at a NE view (road edge-on), so the viewer must set heading 313°. |
| 31 | FAIL | n/a | n/a (suggested 86°) | No Street View imagery. Pano URL falls back to the map twice (Whipholt / Hackensack area). Viewpoint is in lake/forest country between Whipholt and Hackensack (North Country Trail area), off any SV-covered road. |
| 32 | FAIL | n/a | n/a (suggested 166°) | No Street View imagery. Pano URL falls back to the map twice (Walker / Ah-gwah-ching area). Viewpoint is in lake/forest country east of MN-371, between Ah-gwah-ching and Hackensack (North Country Trail area), off any SV-covered road. |
| 33 | FAIL | n/a | n/a (suggested 37°) | No Street View imagery. Pano URL falls back to the map twice (Walker / Ah-gwah-ching area). Viewpoint is in lake/forest country NW of Ah-gwah-ching, between MN-371 and MN-34 (North Country Trail area), off any SV-covered road. |
| 34 | FAIL | n/a | n/a (suggested 91°) | No Street View imagery. Pano URL falls back to the map twice (Whipholt / Hackensack area). Viewpoint is in lake/forest country east of Whipholt (North Country Trail area), off any SV-covered road. |
| 35 | FAIL | n/a | n/a (suggested 122°) | No Street View imagery. Pano URL falls back to the map twice (Whipholt / Brevik area). Viewpoint is in lake/forest country SE of Whipholt (North Country Trail area), off any SV-covered road. |
| 36 | FAIL | n/a | n/a (suggested 101°) | No Street View imagery. Pano URL falls back to the map twice (Brevik / Whipholt / Longville area). Viewpoint is in lake/forest country SE of Whipholt, west of Longville (North Country Trail area), off any SV-covered road. |
| 37 | FAIL | n/a | n/a (suggested 9°) | No Street View imagery. Pano URL falls back to the map twice (Walker / Ah-gwah-ching / Hackensack area). Viewpoint is in lake/forest country SW of Whipholt, west of Hackensack (North Country Trail area), off any SV-covered road. |
| 38 | PASS | ©2024 | CORRECTED ~45° (from 345°) | County Rd 4 runs SW–NE; 45° is NE along it. At 345° the view is NNW across the roadside ditch (two-way sign, fence posts). Map check: DATA GAP — County Rd 4 is continuous SW–NE through the spot; the break is at/near its junction with Hat 6 Rd (County 41), a data segmentation, not a trail on/off point (no foot trail, trailhead or park shown). |
| 39 | PASS | ©2024 | 62 confirmed | T-junction; a dirt/gravel road runs ENE ahead (toward a house), with a STOP sign and a fire hydrant at the junction. Map check: DATA GAP — junction of N River Dr (N–S) and the E–W main road by Frazee Vergas Public Schools; the roads are continuous and no foot trail, trailhead or park is shown; the break is a data segmentation at the junction, not a trail on/off point. |
| 40 | PASS | ©2026 | 359 confirmed | Co Hwy 29 runs straight N ahead. Map check: DATA GAP — Co Hwy 29 is continuous N–S through the spot; the break is at/near its junction with 120 St (E–W), a data segmentation, not a trail on/off point (no foot trail, trailhead or park shown). |
| 41 | FAIL | n/a | n/a (suggested 61°) | No Street View imagery. Pano URL falls back to the map twice (Rochert / Frazee area, Hwy 34). Viewpoint is on 360 Ave (N–S), just south of its junction with 175 St (E–W); 360 Ave has no SV coverage here. Map check: DATA GAP — 360 Ave is continuous N–S through the spot; the break is at/near the junction with 175 St, a data segmentation, not a trail on/off point (no foot trail, trailhead or park shown). |

## Summary by priority

- **Priority 1 (#1–#30):** 23 pass, 7 fail (#13, #18, #19, #22, #23, #27, #29).
- **Priority 2 (#31–#37):** 0 pass, 7 fail — all seven are North Country Trail / road crossings in the lake/forest country between Walker and Hackensack, off any SV-covered road, so none of them can be shown in the viewer.
- **Priority 3 (#38–#41):** 3 pass, 1 fail (#41).

## Interior line breaks (map check)

Of the seven interior line breaks checked on the map (#12, #19, #20, #38, #39, #40, #41), only **#20 is a real trail on/off point** (the signed North Country Trail / Hubbel Pond trailhead on Hwy 34); the other six are data gaps — the road is continuous through the spot and the break sits at/near a road junction.

## Headings

Four suggested headings were corrected: #2: 229° → ~180°, #6: 228° → ~120°, #8: 9° → ~100°, #38: 345° → ~45°. Four were confirmed only via the map because the pano opened at a different heading: #11: 96°, #17: 104°, #25: 130°, #30: 313°.

No CAPTCHA or bot check appeared during the work.

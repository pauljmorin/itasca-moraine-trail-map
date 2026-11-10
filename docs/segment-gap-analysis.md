# Segment / gap analysis — KMZ overlay on the official line

*Produced 2026-11-10 by `scripts/segment_overlay.py` from the chapter's
KMZ (`data/segments/NCT_Itasca_Moraine_Segments.kmz`, pristine copy;
MD5 d9c6fa54885455394d3fcc9209a61f5e, identical to the delivered file)
and the official line in `data/segments/official-line-chapter-extent.geojson`.
All lengths are geodesic (haversine, R = 6371.0088 km — the project
convention from `pull_official_line.py`). Every number below was
recomputed from the emitted GeoJSON files after generation and
matches them. **Extended the same day (§8) with the join of the
chapter's adoption tracker (§8), run by `scripts/join_adopters.py`;
§§0, 6 and 7 were amended where the join changes what they said.***

## 0. What the KMZ actually contains — read this first

The file is a Google (My) Maps export named **"NCT Itasca Moraine
Segments"**. It holds **32 placemarks, and every one of them is a
Point**. There are **no line geometries, no descriptions, no dates,
no adopter names, and no extended data** — the only per-placemark
fields are a name, a style reference, and the coordinates. (One pin,
West-14, carries an altitude, 473.97 m; the rest are 0.)

So the KMZ is a **boundary-point file**, exactly as described when it
was handed over: pins marking segment boundaries along the trail.
It is *not* a segment/adoption record. Two consequences:

- **Adopter coverage cannot be read from this file.** No pin names an
  adopter, and no pin is marked unadopted. Who maintains what has to
  come from the chapter's adoption records (the adopters spreadsheet
  is the system of record for that) and be joined onto the segments
  built here. At first build every stretch therefore carried
  `adopter: null`; **the tracker was delivered later the same day
  and has been joined — the stretches now carry adopter names,
  descriptions and mile markers from it. See §8**, which is also
  where every KMZ↔tracker disagreement is flagged.
- **The segment model is an inference, stated here once and used
  throughout:** a named pin starts a segment that runs along the
  official line to the next pin in trail order. The pins form two
  numbered series — **West-1 … West-17** and **Chip-1 … Chip-13** —
  plus one explicit terminus pin, **"Chip-13 end"**, and one stray,
  **"Point 32"**, which sits at *exactly* the coordinates of West-16
  (a duplicate pin, flagged `role: "duplicate"` in the output, kept
  for fidelity). The West→Chip junction is handled in §3.

### KML → GeoJSON property mapping (`data/segments/segments.geojson`)

| KML | GeoJSON property | Notes |
|---|---|---|
| Placemark `<name>` | `name`, `kml_name` | verbatim |
| `<styleUrl>` | `style_url` | `#icon-1739-000000-nodesc` on all 32 |
| `<description>` | `kml_description` | **absent in the source — null on all 32** |
| Point coordinates (lon, lat, alt) | Point geometry (lon, lat); `kml_altitude_m` | alt kept as a property; only West-14 is non-zero |

Computed properties added by the overlay (not from the KML):
`chapter` (`itasca-moraine`), `role` (`segment_start` ×30,
`series_terminus` ×1, `duplicate` ×1), `duplicate_of`, `series`,
`series_index`, `offset_to_chapter_line_m`,
`nearest_official_chapter`, `nearest_official_seg_name`,
`on_chapter_line`, `chain_id`, `chainage_mi` (position along the
depicted chapter line from its west end), `chainage_reassigned` +
`reassignment_note` (one pin — see §2), `segment_name` /
`segment_length_mi` / `segment_end_at` (the stretch this pin
starts), and `access_at_point`.

## 1. Inventory

| Item | Count / value |
|---|---|
| KMZ placemarks | 32 (all Points) |
| Segment-start pins | 30 (West ×17, Chip ×13) |
| Terminus pins | 1 ("Chip-13 end") |
| Duplicate pins | 1 ("Point 32" = West-16) |
| Adopted segment stretches derived | 30 |
| Adopted mileage (on the official depiction) | **73.23 mi** |
| Chapter (ITM) official line, stored geometry | 40 features, **78.19 mi** |
| …of which chained into one continuous path | 39 features, **76.15 mi** |
| …one feature not joining the chain | 1 feature, **2.04 mi** (see §4.3) |
| Unadopted gap mileage (depicted) | **2.92 mi** (one gap, §4.1) |
| Access points computed | 111 (21 road crossings/approaches, 90 trail) |

Segment lengths run 1.15–4.65 mi (median ≈ 2.4 mi), setting
Chip-13's zero depicted length (§4.2) aside. The longest adopted
segments are West-8 (4.65 mi), Chip-12 (4.09 mi), West-11 (3.55),
Chip-1 (3.40), Chip-4 (3.38) and West-7 / Chip-10 (3.27 each). The
naming scheme is purely geographic-series + sequence
number; the West series covers the Itasca State Park / Paul Bunyan
State Forest country, the Chip series the Chippewa National Forest
country (the official line's own `seg_name` attributes agree).

## 2. Fit to the official line

The pins were plainly placed *on* the official depiction — this is
not a hand-drawn approximation:

- **31 of 32 pins lie within 9.7 m of the chapter (ITM) line**
  (median offset **0.4 m**, 90th percentile 1.3 m). The largest of
  these is Chip-13 at 9.7 m — still on the line for any practical
  purpose. Every pin's nearest official feature is an ITM feature;
  none falls on the neighbouring chapter's (LLC) line.
- **One pin does not fit at all: "Chip-13 end"** sits **3,622 m**
  from the nearest depicted line. The depicted ITM chain *ends* at
  (-94.25017, 47.02153) — the very point the Chip-13 pin marks —
  and the "Chip-13 end" pin lies 3.62 km further on (2.25 mi
  straight-line), at (-94.21485, 47.04344). Either the chapter works
  trail east of where the current official depiction stops, or the
  pin is stale/misplaced. **It is flagged, not silently fixed:**
  in the analysis the pin is treated as the adopted chain's
  terminus *at the depicted chain end* (`chainage_reassigned:
  true`, with the reason recorded in `segments.geojson` and in the
  run statistics), because its name and series position say it ends
  segment Chip-13. Consequences are spelled out in §4.2.

No other reroute/stale-data outliers exist: there is no pin sitting
on a parallel old tread or offset by a consistent bias.

## 3. The adopted chain and the West→Chip junction (assumption)

Ordered west→east, the pins chain along a single continuous
depicted path (all 31 on-line pins project onto the same chain).
The stretch from **West-17 to Chip-1 is 2.70 mi** — squarely inside
the normal segment-length range (1.15–4.65 mi) — so this analysis
treats it as segment **West-17** running to where Chip-1 begins,
i.e. the two series are contiguous parts of one adopted chain
(`crosses_series_junction: true` on that stretch, so the assumption
is visible in the data). If the chapter instead regards the West-17
→ Chip-1 stretch as unadopted, it becomes a 2.70 mi gap and adopted
mileage drops to 70.53 mi; the recruiting picture in §4 is otherwise
unchanged. **This is the one judgment call in the file and it is
the chapter's to confirm.**

## 4. Gaps — the recruiting layer (`data/segments/gaps.geojson`)

Coverage accounting, two ways (both true; they answer different
questions):

- Of the **depicted chain** (76.15 mi): adopted **73.23 mi
  (96.2%)**, gap **2.92 mi (3.8%)**.
- Of **all ITM-tagged line** in the file (78.19 mi): adopted 93.7%,
  gap 3.7%, and 2.6% is the unjoined feature in §4.3, which this
  analysis can neither adopt nor gap until its depiction joins the
  chain.

### 4.1 GAP-W — the one true gap: 2.92 mi, Itasca State Park

| | |
|---|---|
| Length | **2.92 mi**, all off-road (`trail_stat` NCT / foot path) |
| Where | The depicted chapter line **west of West-1**, inside Itasca State Park, from (-95.219071, 47.149411) to the West-1 pin (-95.170411, 47.154127) |
| West end | No road crossing. Nearest road is **State Highway 113, 0.78 mi south** of the line's west end |
| East end | At West-1; nearest road again State Highway 113, 1.10 mi away |
| Access along it | **No road crosses this stretch at all.** Itasca SP trails cross it: Nicollet Trail at 0.30 mi in, Deer Park Trail at 0.78 mi in, and the Ozawindib Trail at the east end. Access is by the park trail network only |

This is the chapter's west tail: depicted, unadopted, roadless.
Whether it is genuinely unmaintained or simply maintained under the
park's own arrangements is a chapter question — but on the
boundary-point evidence it is the one stretch of the depicted line
with no segment on it, and it is emitted as the recruiting layer's
single feature.

### 4.2 The east end — no depicted gap, but read this

Because the "Chip-13 end" pin was reassigned to the depicted chain
end (§2), there is **no GAP-E feature**: no depicted line lies east
of the adopted span. But segment **Chip-13 itself has zero depicted
length** (`depicted_length_zero: true`): its start pin sits at the
depicted chain's east end and its terminus pin sits 3.61 km away
(pin-to-pin) off the depiction. Chip-13's real on-the-ground length
is unknown from these sources — at least the 2.25 mi straight-line
to its terminus pin. If the chapter's easternmost work is real,
the official depiction is missing roughly the last 2¼+ miles of it,
which is also a data note worth sending up the NCTA line.

### 4.3 The unjoined feature — 2.04 mi the chain couldn't take

One ITM feature (2.04 mi of Chippewa National Forest line, ending
about 1.35 mi from the Chip-6 pin) has both endpoints more than
30 m from every neighbouring feature's endpoints, so the chaining
(30 m joint tolerance) left it out of the path. Its line is real
depicted trail inside the chapter's extent; whether it is a spur,
a depiction break at a junction, or a mis-joined reroute can't be
settled from the data on hand. It is **excluded from the
adopted/gap accounting above rather than silently forced in**, and
flagged here for a look against the live service depiction.

## 5. Access points (`data/segments/access-points.geojson`)

Method: every crossing of the depicted chain by a road centerline
(`data/access/roads.geojson`) or a DNR access line
(`data/access/access-lines.geojson`) — 74 distinct crossings after
de-duplication — tagged per stretch as **start** (within 0.25 mi of
the stretch's start), **end**, or **mid**; where an end has no
crossing, the nearest road/trail approach within 0.25 mi is recorded
as `how: "near"`. The same physical crossing reported by several DNR
datasets (e.g. a trail carried as both snowmobile and OHV) is merged
into one record, with the other datasets named in `also_in`;
braided repeat crossings of one tread are folded and counted in
`repeat_crossings`. Totals: **111 access points — 104 crossings +
7 near approaches; 21 involve roads, 90 involve trails.**

Per-segment summary (labels are the crossing road/trail names;
"—" = none within tolerance at that position):

| Segment | To | Mi | Type | Access at start | Mid crossings | Access at end |
|---|---|---|---|---|---|---|
| West-1 | West-2 | 1.15 | off-road | Ozawindib Trail | — | Forest Rider Trails |
| West-2 | West-3 | 2.40 | off-road | Forest Rider Trails | — | — |
| West-3 | West-4 | 1.90 | off-road | — | — | Forest Rider Trails; Forest Riders Trails |
| West-4 | West-5 | 2.66 | off-road | Forest Rider Trails; Forest Riders Trails | — | — |
| West-5 | West-6 | 2.56 | off-road | — | — | Forest Rider Trails |
| West-6 | West-7 | 2.35 | mixed | Forest Rider Trails | Forest Rider Trails | Forest Riders Trails |
| West-7 | West-8 | 3.27 | mixed | Forest Rider Trails; Forest Riders Trails | — | — |
| West-8 | West-9 | 4.65 | off-road | — | Forest Rider Trails; Paul Bunyan (NW) HWT; Round River Drive; TeePee Lakes | Paul Bunyan (NW) HWT |
| West-9 | West-10 | 1.95 | off-road | Paul Bunyan (NW) HWT | Paul Bunyan (NW) HWT | — |
| West-10 | West-11 | 1.67 | off-road | — | Nevis Wilder Trails; Paul Bunyan (NW) HWT | Refuge; Round River Drive |
| West-11 | West-12 | 3.55 | off-road | Refuge; Round River Drive | Nevis Wilder Trails; Round River Drive; Steamboat | Round River Drive |
| West-12 | West-13 | 2.11 | off-road | Round River Drive | Nevis Wilder Trails; Paul Bunyan (SE) HWT | Round River Drive; Spur I |
| West-13 | West-14 | 2.17 | off-road | Round River Drive; Spur I | Nevis Wilder Trails; Paul Bunyan (SE) HWT | Akeley Cutoff; Nevis Wilder Trails; Round River Drive |
| West-14 | West-15 | 2.47 | off-road | Akeley Cutoff; Nevis Wilder Trails; Round River Drive | Round River Drive | — |
| West-15 | West-16 | 2.75 | mixed | — | Nevis Wilder Trails; Pineview; Round River Drive | East Steamboat; Nevis Wilder Trails; Round River Drive; Steamboat |
| West-16 | West-17 | 1.77 | mixed | East Steamboat; Martineau Recreational Trails; Nevis Wilder Trails; Round River Drive; Steamboat | — | Parkway; Round River Drive |
| West-17 | Chip-1 | 2.70 | mixed | Parkway; Round River Drive | Round River Drive | — |
| Chip-1 | Chip-2 | 3.40 | off-road | — | Cass County Trails; County 12 Nw; Heartland State Trail; Sixth Lake Rd Nw | State 34 Nw |
| Chip-2 | Chip-3 | 2.87 | mixed | State 34 Nw | — | County 50 Nw |
| Chip-3 | Chip-4 | 1.86 | off-road | County 50 Nw | — | — |
| Chip-4 | Chip-5 | 3.38 | off-road | — | 60Th St Nw; Cass County Trails | State 371 Nw |
| Chip-5 | Chip-6 | 2.09 | off-road | State 371 Nw | — | Woodtick Trl Nw |
| Chip-6 | Chip-7 | 2.16 | off-road | Woodtick Trl Nw | — | Woodtick Trl Nw |
| Chip-7 | Chip-8 | 1.70 | off-road | Woodtick Trl Nw | — | Cass County Trails |
| Chip-8 | Chip-9 | 1.48 | off-road | Cass County Trails | — | 30Th Ave Nw |
| Chip-9 | Chip-10 | 2.51 | off-road | 30Th Ave Nw | — | Tower Rd Nw |
| Chip-10 | Chip-11 | 3.27 | off-road | Tower Rd Nw | — | Woodtick Trl Nw |
| Chip-11 | Chip-12 | 2.35 | off-road | Woodtick Trl Nw | — | Woodtick Trl Nw |
| Chip-12 | Chip-13 | 4.09 | off-road | Woodtick Trl Nw | — | Cass County Trails |
| Chip-13 | Chip-13 end | 0.00 | undetermined (§4.2) | Cass County Trails | — | — |

("Mixed" type = the stretch includes a short on-road portion of
the official line — 0.19 mi at most, on Chip-2; the rest are
junction-length pieces of 0.001–0.06 mi. GAP-W is all off-road.)

### The mower problem — single-ended segments

A segment is flagged `single_ended_access` when all of its recorded
access sits at one end and it has no mid crossings — the
haul-the-mower-the-full-length case:

- **West-2** (2.40 mi) — access only at its start (Forest Rider Trails)
- **West-3** (1.90 mi) — access only at its end (Forest Rider / Forest Riders Trails)
- **West-4** (2.66 mi) — access only at its start
- **West-5** (2.56 mi) — access only at its end
- **West-7** (3.27 mi) — access only at its start; the longest single-ended segment
- **Chip-3** (1.86 mi) — a road (County 50 Nw) at its start, nothing at its end
- **Chip-13** — flagged by the rule, but this is the §4.2 depiction
  artifact, not a real access finding

15 of 30 segments have recorded access at **both** ends; every
segment has at least some recorded access.

**A necessary caution on what "access" means here.** A crossing is
a line on a map, not a drivable route. In the West series almost
all recorded access is DNR *trail* systems — the Forest Rider(s)
snowmobile/OHV tread, hunter walking trails, state-park trails —
not roads; genuine road crossings cluster in the Chip series
(State 34/371, County 12/50, Woodtick Trail, Tower Road…). The
state-forest-road crossings (Refuge, Steamboat, East Steamboat,
Akeley Cutoff, Spur I, Parkway, TeePee Lakes) are the most likely
vehicle routes in the West. Snowmobile tread is seasonal and
hunter walking trails are foot-only; the `source_type` on every
access point says which dataset each crossing came from, and the
working view should keep that distinction visible before anyone
plans a mower run from this data.

## 6. Outputs

| File | Contents |
|---|---|
| `data/segments/NCT_Itasca_Moraine_Segments.kmz` | Pristine copy of the delivered KMZ |
| `data/segments/segments.geojson` | All 32 placemarks as Points, KML fields preserved + computed overlay properties + tracker fields for the segment starting at each pin (§8). Working-view data |
| `data/segments/segment-stretches.geojson` | The adopted stretches as official-line geometry, with length, trail-stat split, land context, embedded access points, `single_ended_access` flag — **31 features after the §8 tracker join** (WEST-8 split into WEST-8A/8B), each carrying adopter, description, NCT mile markers, sawyer, comments and 2026 maintenance notes from the tracker |
| `data/segments/gaps.geojson` | The recruiting layer: GAP-W (2.92 mi) with end descriptions and access points |
| `data/segments/access-points.geojson` | All 111 access points as Points, each tied to its segment/gap (`for_type`, `for_name`, `position`, `dist_from_start_mi`) |
| `data/segments/adopters-2026-09.xlsx` | Pristine copy of the chapter's adoption tracker (§8.0) |
| `scripts/segment_overlay.py` | The KMZ overlay pass, re-runnable; prints/writes the run statistics the tables above were checked against |
| `scripts/join_adopters.py` | The tracker join (§8), run after `segment_overlay.py`; enriches the two segment files in place and writes the join statistics |

## 7. Method and caveats, collected

1. **Segment model** — pins are segment starts; a segment runs to
   the next pin (§0). The West-17 → Chip-1 junction call is in §3.
2. **Chaining** — official ITM features were ordered into a path by
   endpoint proximity (≤ 30 m joints); chainage is measured along
   that path from its west end. One feature didn't join (§4.3).
3. **Off-road/on-road splits** are computed from the official
   features' own `trail_stat` over each interval's exact chainage
   span (not sampled), so the short on-road pieces are real.
4. **Access tolerance** — "at an end" means a crossing within
   0.25 mi of the end, or a road/trail passing within 0.25 mi of
   the end point. Local knowledge will know approaches no dataset
   carries; per the design those get pinned by the photo pipeline
   and marked chapter-sourced.
5. **Adopter names were not in any output of the KMZ pass itself**,
   because they are not in the KMZ. They have since been joined
   from the chapter's adoption tracker (§8) into the working-view
   segment files — names, descriptions, mile markers, sawyer,
   comments and maintenance notes, but **never the tracker's phone
   or email columns** (verified absent from the outputs). Per the
   publishing model, the public view shows segments and gaps
   without personal names regardless.
6. The "Chip-13 end" reassignment (§2) and the Chip-13 zero-length
   flag (§4.2) are the two places where this analysis *interpreted*
   rather than transcribed. Both are flagged in the data itself,
   not just here.

## 8. Tracker vs KMZ — the adoption spreadsheet joined

*Added 2026-11-10, after the chapter's current adoption tracker was
delivered: `NCT-ITM-_Adopters-September-2026.xlsx` ("This is how we
track adoptions and related information now", current as of
2026-11-10). Pristine copy at `data/segments/adopters-2026-09.xlsx`
(MD5 f663f9e58e72afdc1e86d14d2a774c87, identical to the delivered
file). Governance, as handed down with it: **the spreadsheet governs
names and assignments; the KMZ governs geometry.** Where the two
disagree materially, both readings are kept in the data and the
disagreement is flagged here (D1–D9 below).*

### 8.0 The tracker, inventoried

Two sheets:

**"Adopters"** (A1:K35) — title row "North Country Trail Adopters –
Itasca Moraine", then 11 columns: Section Name, Section Description,
NCT Mile Virtual Marker Start, NCT Mile Virtual Marker End, NCT MN
Map #, Length (Miles), Adopter, Phone Number, Email, Sawyer,
Comments. **32 section rows** (rows 3–34) plus a footnote row:
"* Vague landmark; Post or Sign needed" — the tracker's own flag on
the asterisked description landmarks. Details that matter:

- **Length is a formula** (`= End − Start`) in 29 of 32 rows. The
  three literals are the two loop sections (Waboose, 4) and,
  anomalously, **WEST-10, whose Length is a typed `2`** — the only
  mainline row breaking the formula pattern (see D1).
- The virtual markers form **one unbroken chain, NCT mile 169.5 →
  246.25 (76.75 mi of mainline)**, plus two loop sections hanging
  off it (WEST-10 "Lake 21 Loop", 2 mi; "Waboose" Lake Loop, 4 mi).
  The sheet's stated total across all 32 rows is 82.75 mi.
- **Every one of the 32 sections has an adopter named.** Phone is
  filled for 17 sections, email for 30; the email cells carry 22
  mailto hyperlinks.
- The descriptions are landmark-to-landmark ("Hubbard County 4 to
  Steamboat Pass FR") and several comments carry asset notes the
  photo inventory will want (campsites at NCT miles 174.0, 184.2,
  209.5, 225.3; shelters; a latrine pair on Hovde and Gut lakes).

**"Maintenance Log"** (A1:E33) — Section Name, Adopter, **2026
Notes**, Help Requested?, and an entirely empty fifth column. Two
structural facts: columns A and B are **live array formulas
mirroring the Adopters sheet** (`='Adopters'!A3` etc.), so the two
sheets can never disagree about names — they are one record viewed
twice (verified: the adopter name sets match on all 32 sections).
The sheet's own content is the 2026 notes (a mowing/clearing record
per section; CHP-9's is blank) and the "Help Requested?" column,
whose semantics are mixed: text or blank on the WEST rows, but
**bare integers (4–44) on twelve CHP rows** with no unit recorded
anywhere in the workbook. Those numbers were joined verbatim as
`help_requested_2026_raw` and are **not interpreted** — hours?
trees? Unknown; the chapter can say.

### 8.1 The join

Matching is by section name after normalization — `WEST-n` →
`West-n`, `CHP-n` → `Chip-n` (the tracker writes the Chippewa
series "CHP"; raw tracker names are preserved in `tracker_section`
on every joined feature) — plus one structural operation:

- **WEST-8 is split.** The tracker runs two sections where the KMZ
  has one stretch: WEST-8A "Steamboat Pass FR to Island Lake Sign"
  (NCT 185.75–188) and WEST-8B "Island Lake Sign to Co Rd 91"
  (188–190.5). The KMZ has no pin at the Island Lake Sign, so the
  KMZ West-8 stretch was split at the chainage implied by the
  tracker's proportion of the section (2.25 of 4.75 virtual miles →
  split at chainage 21.41 mi, (-94.913735, 47.156769); parts measure
  2.20 and 2.45 mi against the tracker's 2.25 and 2.50). The parts
  are flagged `part_of: "West-8"`, and the method is recorded in
  the join statistics. This is a tracker-governed definition laid
  on KMZ geometry, and it is labeled as such.

**Hit rate:**

| Side | Result |
|---|---|
| KMZ stretches | **31 of 31 joined** (the 30 KMZ stretches, WEST-8 counted as its two tracker parts); none unmatched |
| Boundary pins | **29 of 32 joined** — the three with `tracker_match: false` are "Chip-13 end" (a terminus, not a section), "Point 32" (the duplicate) and "West-14" (it carries the WEST-14 row's data in its stretch and the Waboose annotation, D6, on the pin itself). The West-8 pin carries WEST-8A, the section that starts there; WEST-8B begins mid-stretch (D2) and has no pin |
| Tracker sections | **31 of 32 joined by name**; the 32nd, **Waboose**, has no KMZ namesake and was joined *by annotation* — a `waboose_note` on the West-14 pin, the point where the loop branches (D6) |
| Adopter names | All 32 sections carry at least one adopter; **no section is unadopted in the tracker** (cf. §4: the one unadopted stretch, GAP-W, simply has no tracker section at all) |

Fields joined onto each stretch: `tracker_section`,
`tracker_description`, `adopter` (parsed name list) +
`adopter_verbatim`, `sawyer`, `tracker_comments`, `nct_mile_start`,
`nct_mile_end`, `nct_map_refs`, `tracker_length_mi`,
`maintenance_2026_notes`, `help_requested_2026_raw`, and a status
string naming the tracker as the adopter source. Pins carry the
same tracker fields for the segment starting at the pin.
**Phone and email columns were not copied, anywhere** (verified:
no email addresses and no phone numbers exist in the joined
GeoJSONs; the single "@" in the files is the chapter's own
"Campsite @Shingobee" shorthand inside a comment). The joined files
are working-view data; per the publishing model the public site
shows segments and gaps without adopter names.

### 8.2 Where the two sources agree

- **Structure.** Both describe the same adopted chain in the same
  order: a West series, then a Chip series, handover at the same
  place. The tracker's WEST-17 ends at "Cass Co. Line*" and CHP-1
  begins at "Cass/Hubbard Co. Line" — exactly where the KMZ changes
  series (the Chip-1 pin). (The project data carries no county
  boundary layer, so the line's position itself isn't verified —
  the *agreement* is.)
- **Totals.** Tracker mainline 76.75 virtual miles vs the depicted
  chain's 76.15 mi — within 0.6 mi over the whole chapter. The two
  systems agree in total even where they drift locally (D4).
- **Most individual lengths** are within ±0.25 mi of each other —
  reasonable for quarter-mile-rounded virtual markers against a
  geodesic line.
- Landmark boundaries that *can* be checked against the crossing
  data check out in several places: the West-8 pin sits at the
  "Steamboat Pass FR" vertex exactly as WEST-8A's description
  starts; WEST-13/WEST-14's shared boundary is the Akeley Cut-Off
  crossing cluster; the CHP Woodtick/30th Ave/Tower Rd boundaries
  all coincide with the named road crossings from §5.

### 8.3 Disagreements and quirks — flagged, both readings kept

**D1 — WEST-10's loop overlaps WEST-9, and the KMZ can't fit it
(the largest boundary disagreement).** In the tracker, WEST-9 runs
190.5 → 194.0 and the WEST-10 "Lake 21 Loop" (start marker 192,
end "Loop") sits *inside* that span, with WEST-11 starting at
194.0. In the KMZ, the West-10 pin is just **1.67 mi** before the
West-11 pin — there is no room for WEST-9's 3.5 miles plus the loop
between them. Measured against KMZ geometry, WEST-9 is 1.95 mi,
not 3.50 (−1.55, the biggest single length disagreement). Either
the tracker's markers around Lake 21 are stale, or the KMZ
West-10/West-11 pins sit ~1.5–2 NCT miles west of the described
landmarks. Both readings are in the data (`tracker_length_mi`
alongside `length_mi`); a chapter member who knows Lake 21 can
settle it in one look. It is probably not coincidence that WEST-10
is also the one row whose Length cell is hand-typed rather than a
formula.

**D2 — WEST-8's split has no KMZ pin.** Covered in §8.1: tracker
governs the definition (two sections, two adopter groups), KMZ
geometry was split proportionally. Approximate by construction.

**D3 — Two tracker landmarks the road data cannot see.** WEST-9's
boundaries are "Co Rd 91" (start) and "Refuge Rd" (end), but the
MnDOT centerlines contain **no road within 500 m of either the
West-9 or the West-10 pin**, and the crossing actually named
"Refuge" in the access data falls at West-11's *start*, not
West-9's end. Combined with D1, the whole West-9/West-10/West-11
neighbourhood disagrees between the sources by roughly one
landmark. Possibilities: the roads layer lacks these forest roads,
the pins were placed at different landmarks than the descriptions
name, or the descriptions predate a reroute. Flagged for chapter
knowledge; not resolvable from the data on hand.

**D4 — Length drift beyond ±0.3 mi in six more sections**
(KMZ-computed minus tracker): WEST-4 **+0.66**, WEST-5 **−0.44**,
CHP-3 **−0.39**, CHP-4 **+0.38**, WEST-3 **−0.35**, and WEST-9's
−1.55 (D1). The full 30-row comparison is reproducible from the
join statistics; per the governance rule the KMZ/official line
governs the map's geometry while the tracker's virtual miles
remain the chapter's working mileposts — both are carried on every
stretch (`length_mi` and `tracker_length_mi`).

**D5 — CHP-13 corroborates §4.2, and sharpens it.** The tracker
gives CHP-13 a full existence the depiction lacks: 3.5 mi
(242.75–246.25), adopters Rashelle Brown & Craig Friday, sawyer
Rashelle Brown, and a 2026 maintenance record ("Mowed June 20 and
again July 31"). So the chapter's easternmost section is real and
worked; the official depiction and the KMZ between them cover
**0.0 of its 3.5 miles**. Spreadsheet governs the section; its
geometry is simply missing from the other two sources. (Its
pin-to-pin terminus geometry is in §4.2.)

**D6 — The Waboose Lake Loop exists only in the tracker.** A
4-mile loop section (adopters Bruce and Matt Johnson) branching at
NCT 201.75 — the same marker where WEST-14 begins, and the West-14
KMZ pin does sit exactly there, at the Akeley Cut-Off crossings.
But **no loop geometry exists near the pin in the official
depiction**: the two ITM features passing it are ordinary mainline
(endpoint separations 1.01 and 0.72 mi against lengths of 1.20 and
1.10 mi — pass-through segments, not a loop). Joined by annotation
on the West-14 pin (`waboose_note`); the loop has no geometry in
any project file.

**D7 — The tracker's own soft spots.** The "Help Requested?"
integers on the CHP rows (§8.0) are unexplained. WEST-5 and CHP-4
both carry "need to find a new adopter for 2027" — a recruiting
signal that belongs on the same list as GAP-W. WEST-17's comment
records assignment history the KMZ can't express ("Formerly Paul
Morin's Section — New Adopter 2026"; the tracker governs: Julie
Isaacson is the adopter of record). The tracker also spells CHP-12's
end "4th Woodick Xing" while CHP-11's description says "Woodtick" —
verbatim text was preserved as-is in the join.

**D8 — KMZ-only items with no tracker meaning.** "Point 32" (the
duplicate pin) matches nothing and needs nothing. "Chip-13 end"
(the terminus pin) has no tracker row; the tracker expresses the
same end as CHP-13's end marker, 246.25.

**D9 — GAP-W against the tracker.** The tracker chain starts at
NCT 169.5 (WEST-1), and the depicted gap (§4.1) lies *west* of
that — the tracker simply has no section there, consistent with
the gap finding. Nothing in the tracker contradicts §4.

### 8.4 What changed in the data

- `segment-stretches.geojson`: 30 → **31 features** (WEST-8A/8B),
  every feature tracker-joined; adopted mileage unchanged
  (73.229 mi — verified after the join).
- `segments.geojson`: 29 pins tracker-joined; West-14 carries the
  Waboose annotation; "Chip-13 end" and "Point 32" carry
  `tracker_match: false`.
- `gaps.geojson` and `access-points.geojson`: unchanged by the join.
- Reproduce with: `python3 scripts/segment_overlay.py &&
  python3 scripts/join_adopters.py` (the join writes its full
  statistics — inventory, hit rate, the 30-row length comparison —
  to its stats output).

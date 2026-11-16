# Reservation maps survey — public georeferenced maps from the Native reservations the Minnesota NCT crosses

Date: 2026-11-16
Scope: survey only. Nothing wired, no `site/app.js` edit, no commit/push.

## 1. Which reservations does the Minnesota NCT cross? (geometry, not guesswork)

Method: BIA American Indian and Alaska Native Land Area Representation
(AI AN-LAR) boundaries — the same source the viewer's existing Leech Lake
layer came from (`scripts/pull_leech_lake_reservation.py`, BIA FeatureServer
`DivLTR/BIA_AIAN_National_LAR`, layer 0; Leech Lake feature LAR0033) —
tested against the statewide NCT line `site/data/trail-minnesota.geojson`
(348 features). Lengths are geodesic, cross-checked in UTM 15N. The six
candidates named in the brief were tested, plus every other BIA feature in
the Minnesota bbox (21 features total).

### Crosses

| Reservation | Trail miles inside | Detail |
|---|---|---|
| **Leech Lake** | **12.17 mi** | 0.08 mi STN on-road + 2.34 mi ITM Chip-12 (the figure the existing boundary layer already records) + 9.75 mi STN Chippewa NF foot path |
| **White Earth** | **19.15 mi** | All LLC chapter. Largest single feature 9.75 mi of a 9.96-mi feature; `cert_stat` Connector; managers Becker County / Division of Forestry / Division of Ecological Services / Clearwater County |

### Does not cross (geodesic nearest distance)

| Reservation | Nearest distance | Nearest trail point |
|---|---|---|
| Bois Forte (Vermillion Lake) | 2.04 mi | — |
| Grand Portage | 2.18 mi | 47.9865, -89.9335 (BRT chapter, northern terminus) |
| Bois Forte (Nett Lake) | 4.12 mi | — |
| Fond du Lac | 10.03 mi | — |
| Red Lake | 29.09 mi | — |
| Mille Lacs | 32.70 mi | — |
| Bois Forte (Deer Creek) | 34.26 mi | — |

All other Minnesota reservations are 35+ mi from the trail. **Within ~1 km
of the trail: nothing besides Leech Lake and White Earth.**

So the map search below covers two reservations: Leech Lake and White Earth.
Grand Portage is included as a third, NPS, section because the trail's
northern terminus sits 2.18 mi from the reservation and the terminus area is
Grand Portage National Monument land — but the trail does not cross the
reservation itself.

## 2. Map search — Leech Lake (crosses, 12.17 mi)

**Found: nothing georeferenced and wireable.**

Checked:

- **Leech Lake Band of Ojibwe, Division of Resource Management (DRM),
  llojibwe.org** — the tribe has a GIS department and publishes public web
  maps, but the only public map found is the Local Foods map
  (`https://www.llojibwe.org/drm/maps/localfoods.html`): an interactive
  point map of food sources. Not a downloadable file, not georeferenced,
  not trail/recreation content. No tribal GeoPDF, georeferenced PDF, or
  public GIS service for roads/trails/recreation found on the tribe's site.
- **BIA** — see §5. No per-reservation map product.
- **EPA Region 5 / RRT5 fact sheet** — Leech Lake Band of Ojibwe Emergency
  Response Fact Sheet (updated Oct 29, 2025): reservation/trust-land map
  is a static image pulled from the Inland Sensitivity Atlas, not a
  georeferenced file.
  `https://epaosc.org/sites/16744/files/ER-Fact-Sheet-Leech-Lake-Band-of-Ojibwe.pdf`
- **U.S. Census Bureau** — Census 2000 block maps and 2010 Tribal Tract
  Reference Maps for Leech Lake Reservation and Off-Reservation Trust Land
  (e.g. `www2.census.gov/geo/maps/blk2000/AIANHH/AIR_Federal/1940_LeechLake/CBN1940_006.pdf`):
  plain PDFs, "for Census Bureau statistical data collection and
  tabulation purposes only". Not GeoPDFs.
- **Minnesota DNR ArcGIS** — "Leech Lake Reservation Review — LLBand vs
  DNR 1973 Agreement" FeatureServer
  (`arcgis.dnr.state.mn.us/host/rest/services/Leech_Lake_Reservation_Review_LLBand_vs_DNR_1973_Agreement/FeatureServer/2/metadata`):
  boundary-alignment review metadata for the 1973 settlement. A boundary
  dataset, not a recreation/trail map.
- **Historical** — 1911 Office of Indian Affairs map of the Leech Lake
  Reservation (University of Minnesota UMedia): historical, not
  georeferenced, not a trail map.
- **LCCMR work plan** — "Mapping Leech Lake Vegetation: A Closer Look"
  (M.L. 2026, LLBO, completion Jun 30, 2029): aquatic-vegetation survey
  whose final product will be a story map. Not a trail map, not yet
  published.

## 3. Map search — White Earth (crosses, 19.15 mi)

**Found: nothing georeferenced and wireable.**

Checked:

- **White Earth Nation, whiteearth.com** — no maps page or downloadable
  tribal map found. The one substantial public document with maps is the
  White Earth Nation Tribal Transportation Safety Plan (Feb 2024, SRF
  Consulting, prepared with MnDOT):
  `https://whiteearth.com/media/pages/community/public-documents/b447932636-1736536989/wen-transportation-safety-plan_240417.pdf`
  It is a plain PDF planning document; its figures (project-area map,
  crash-data maps, high-priority segments) are embedded images, not
  georeferenced pages, and it covers roads and crash locations, not trails
  or recreation. A 2024 SS4A grant narrative for a Naytahwaush shared-use
  pathway exists on the same topic (a single community pathway, not a
  reservation trail map).
- **EPA Region 5 / RRT5 fact sheet** — same pattern as Leech Lake: static
  reservation/trust-land image, not georeferenced.
- **U.S. Census Bureau** — BAS / tribal tract reference maps for White
  Earth: plain PDFs, statistical use only, same caveat as §2.
- **earthlandmap.com (White Earth Reservation parcel web map)** — a
  private individual's cadastral web map (14,756 reservation parcels built
  from current county GIS data, per the author's own posts). Not a tribal
  government publication, not a downloadable georeferenced file, and it is
  parcels — content the viewer already carries via the county parcel
  layers. Rejected: wrong publisher, wrong format, duplicate content.
- **Minnesota Geospatial Commons / MnGeo** — no tribal trail or
  recreation dataset found for White Earth (or Leech Lake). The Commons'
  American Indian Reservations layer is the stale `amerind2010` already
  noted in SOURCES.md.

## 4. Grand Portage — NPS, not tribal (does not cross; nearest 2.18 mi)

Distinction that matters: **Grand Portage National Monument is NPS land;
the Grand Portage Reservation is tribal land.** The NCT's northern
terminus (270° Overlook, Pigeon River) sits in the monument corridor
area, ~2.18 mi from the reservation boundary. The trail does not cross
the reservation.

Checked:

- **NPS, Grand Portage National Monument maps page**
  (`home.nps.gov/grpo/planyourvisit/maps.htm`, updated Jul 22, 2025) —
  offers an interactive web map with two toggles ("Brochure Map" and
  "Park Tiles", plus "Park Tiles Imagery" on aerial photography). A web
  map, not a downloadable georeferenced file.
- **NPS, Mount Rose Trail and Historic Depot Site map**
  (`https://home.nps.gov/grpo/planyourvisit/upload/GRPO_2025_site-map-508-2.pdf`,
  2025) — a plain print PDF of the depot area (Mount Rose Trail, Historic
  Depot, Heritage Center, Grand Portage Bay). Covers the Lake Superior
  shore end of the monument, not the NCT terminus / Fort Charlotte end,
  and is not georeferenced.
- **NPS cartography page** (`https://go.nps.gov/14o0of`, Harpers Ferry
  Center) — official park maps are offered as JPEGs, PDFs, or Adobe
  production files. No GeoPDF format is offered. NPS does not publish a
  georeferenced Grand Portage map.
- **U.S. Census Bureau** — BAS 2025 Governmental Unit Reference Map,
  Grand Portage Reservation and Off-Reservation Trust Land (TA 1355),
  `https://www2.census.gov/geo/pvs/bas/bas26maps/aia/r1355_grand_portage/BAS26R49900891355.pdf`:
  plain PDF, statistical/boundary reference, not a GeoPDF.
- **EPA Region 5 fact sheet** — static reservation/trust-land image only.
- **US Topo GeoPDF, Grand Portage OE N**
  (`https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/USTopo/PDF/MN/MN_Grand_Portage_OE_N_20160513_TM_geo.pdf`) —
  a real GeoPDF, but a USGS 1:24k quad. Excluded by the standing scope
  rule already applied to FSTopo quads: it duplicates the Topo basemap
  the viewer already has.

## 5. BIA — no per-reservation map product

- **AIAN-LAR FeatureServer** (`DivLTR/BIA_AIAN_National_LAR`, layer 0;
  mirrored at `maps.ihs.gov/hostserver/rest/services/Hosted/BIA_National_LAR/FeatureServer`) —
  the authoritative public boundary dataset. This is already the source
  of the viewer's Leech Lake boundary layer; it is a boundary dataset,
  not a map sheet, and there is nothing further to wire from it for
  Leech Lake.
- **BIA national map** (`http://bia.gov/sites/bia.gov/files/assets/public/pdf/idc013422.pdf`,
  Dec 2014) — a print PDF of all Indian lands at 1:4,250,000. Far too
  coarse to show NCT tread; not georeferenced; not wireable.
- No BIA-published GeoPDF or georeferenced PDF exists for Leech Lake,
  White Earth, or Grand Portage individually.

## 6. Assessment against what the viewer already has

The ground a tribal map would cover is already covered by wired sheets:

| Crossing | Already-wired coverage of the crossing miles |
|---|---|
| Leech Lake (12.17 mi) | Chippewa South MVUM front (80.55 km in frame) + back (85.77 km, Bena–Deer River–Grand Rapids) cover the Chippewa NF miles; the Leech Lake boundary itself is already a layer ("The land", OFF by default, 823,249 ac) |
| White Earth (19.15 mi) | White Earth State Forest GeoPDF (43.32 km of trail in frame, wired in the DNR pass) covers the crossing miles |
| Grand Portage terminus area | Grand Marais MVUM (96.7 km in frame, wired) covers the terminus area |

A tribal map would only add something new if it showed tribal-specific
content the DNR/FS sheets do not — tribal roads, recreation sites,
cultural areas, or the reservation's own trail system. No public
georeferenced file of that kind was found for either crossing reservation.

## 7. Recommendation

**Don't wire anything.** No public georeferenced tribal map exists for
Leech Lake or White Earth, and the NPS has no georeferenced Grand
Portage map either. Everything found is one of: a plain print PDF, an
interactive web map, a static image inside a fact sheet or plan, a
Census reference PDF, or a USGS quad excluded by the standing scope
rule. None of it passes the DNR/FS test (real georeferenced file whose
frame contains NCT tread and adds something the viewer lacks).

Revisit if any of these appear:

1. LLBO DRM publishes a downloadable map (their GIS department is
   active — the Local Foods web map shows the capability; a recreation
   or roads map would be the thing to watch for).
2. White Earth Nation publishes a recreation/trails map (their public
   documents so far are transportation-safety plans, not trail maps).
3. NPS publishes a Grand Portage GeoPDF (currently JPEG/PDF/Adobe
   only via Harpers Ferry Center).

Out-of-scope observation, for Paul to decide separately: White Earth is
the only crossing reservation without a boundary layer in the viewer.
One could be built from the same BIA AIAN-LAR source as the Leech Lake
layer (same pull script pattern). That is a boundary-layer question, not
a map-sheet question, and it was not part of this survey's wire scope —
flagged here only so it is not lost.

**DONE Nov 16, 2026:** the White Earth boundary layer was built and wired
by the coordinator job that followed Paul's "add what you can" instruction:
`scripts/pull_white_earth_reservation.py` (same BIA AIAN-LAR source,
LAR0051, fetched live), `site/data/white-earth-reservation.geojson`
(MultiPolygon, 39 polygons, 1,337 vertices; geometry-measured 748,098 ac),
def `whiteearth` in `site/app.js` mirroring the Leech Lake def (same
"Land ownership" group, OFF by default + lazy, purple fill `#c084fc` /
border `#7e22ce`, label at the largest polygon's centroid 47.2276,
-95.7213), draw order beside `leechlake` at the back. Trail inside:
19.15 mi, all LLC chapter (geodesic + UTM agreeing; matches this
survey's 19.15 mi). `site/data-sources.html` gained a "White Earth
Reservation" section and SOURCES.md a matching entry (which also
corrects the stale "White Earth check" line in the Leech Lake entry
that said no trail mileage falls inside it — true only of the
depicted chapter line, not of the statewide line).

## Sources checked (summary)

- BIA AIAN-LAR FeatureServer (boundary geometry, both crossings)
- llojibwe.org — LLBO DRM maps (Local Foods web map only)
- whiteearth.com — Tribal Transportation Safety Plan Feb 2024 (plain PDF)
- nps.gov — Grand Portage NM maps page; Mount Rose Trail site-map PDF
  (2025); Harpers Ferry Center cartography page (go.nps.gov/14o0of)
- bia.gov — national Indian-lands map PDF (Dec 2014, 1:4,250,000)
- census.gov — 2000 block maps, 2010 tribal tract reference maps, 2025
  BAS reference maps (plain PDFs)
- epaosc.org / rrt5.org — Region 5 tribal emergency-response fact sheets
  (static map images)
- Minnesota Geospatial Commons / MnGeo — no tribal trail/recreation
  dataset; reservations layer is stale `amerind2010`
- earthlandmap.com — private White Earth parcel web map (rejected:
  private publisher, not downloadable, duplicate of county parcels)
- arcgis.dnr.state.mn.us — DNR Leech Lake Reservation Review 1973
  Agreement service (boundary metadata, not a trail map)
- lccmr.mn.gov — Leech Lake vegetation mapping work plan (story map
  due 2029, not a trail map)

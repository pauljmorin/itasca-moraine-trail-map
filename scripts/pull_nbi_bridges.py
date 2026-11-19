#!/usr/bin/env python3
"""Pull bridge structures along the full Minnesota North Country Trail
corridor, pedestrian/mixed-use first, from the FHWA National Bridge
Inventory (NBI) 2025.

Paul, Nov 18, 2026 (voice, GO): show existing highway bridges that
might carry the trail — crossing opportunities — pairing with the
right-of-way work around the Ely bottleneck.

SOURCE — SUBSTITUTION, RECORDED: the intended source was the MnDOT
bridge inventory `trans-bridges` (Minnesota Geospatial Commons;
audited in docs/uofm-arrowhead-data-sources-audit-2026-11-18.md,
verdict: Use — the students filtered it to pedestrian/mixed-use only).
That service could NOT be pulled from this VM on 2026-11-18:
  * MnGeo enterprise host FeatureServer returns 499 Token Required
    (https://enterprise.gisdata.mn.gov/aghost/rest/services/
    us_mn_state_dot/trans_bridges/FeatureServer)
  * GDRS download paths (gpkg/shp/metadata under
    resources.gisdata.mn.gov/pub/gdrs/data/pub/us_mn_state_dot/
    trans_bridges/) all return 404
  * MnDOT's own mndotgis.dot.state.mn.us is unreachable from this VM
    (connection fails; DNS resolves)
  * No ArcGIS Online copy of trans-bridges was found
  * The DNR Bridges Cartegraph service (which carries pedestrian-use
    flags) also 404s — apparently retired/moved
The working source is therefore the FHWA National Bridge Inventory
2025, all-records delimited file — the federal inventory fed by the
states from their own inspection systems (MnDOT's SIMS for Minnesota),
so the structures and bridge numbers are the same inventory:
  https://www.fhwa.dot.gov/bridge/nbi/2025/delimited/MN25.txt
  (highway bridges only, 13,551) — NOT used, see below
  https://www.fhwa.dot.gov/bridge/nbi/2025allstatesallrecsdel.zip
  (all records, all states, 56 MB; MN state code 27 = 16,503 records)
The all-records file is used, not the highway-only file, because
pedestrian-only bridges (service on = 3) are non-highway records and
are absent from the highway file. FOLLOW-UP: re-pull from
trans-bridges when MnDOT access is sorted (live browser or token);
the bridge numbers are the join key.

DEDUPE: the all-records file carries 16,503 MN records for 13,795
distinct structures (STRUCTURE_NUMBER_008). A structure gets one
record per inventory route on/under it (record types 1, 2, A–I).
SERVICE_ON_042A is consistent within a structure (verified: 0 of
13,795 structures carry >1 distinct service-on code), so one record
per structure is kept — record type 1 (route on the structure) where
one exists, else the first record — and the filter runs on that
record. nbi_records carries the merged record count.

COORDINATES: NBI LAT_016 / LONG_017 are DDMMSS.ss
(e.g. 45011920 = 45 deg 01' 19.20" N; 095472832 = 95 deg 47' 28.32"
W). Converted to decimal degrees here. NBI points are the inventoried
structure location (generally structure center).

CORRIDOR: the statewide NCT line (site/data/trail-minnesota.geojson,
348 features) PLUS the Star of the North line
(data/segments/trail-stn.geojson, 12 features — not yet merged into
trail-minnesota.geojson; Remer sits 7.0 km from the nearest line in
that file). A bridge counts when its point is within 2 miles
(3,218.69 m) of the line, the same corridor as the timber, motorized,
and campgrounds layers. Distance computed in UTM 15N (shapely) and
recorded as dist_trail_km. The Arrowhead gaps are in
trail-minnesota.geojson (the line passes Ely and Tower at 0.0 km).

FILTERING:
  Tier 1 — pedestrian / mixed-use (the GO's first priority):
    SERVICE_ON_042A in {3 Pedestrian-bicycle, 5 Highway-pedestrian},
    within 2 mi, and OPEN_CLOSED_POSTED_041 not in {K, G}.
    Codes per FHWA Recording and Coding Guide FHWA-PD-96-001,
    Item 42A / Item 41.
  Tier 2 — vehicular bridges that are a plausible trail crossing
    [JUDGMENT]: SERVICE_ON_042A = 1 Highway, within 0.25 mi (400 m)
    of the trail line, OPEN not in {K, G}. Rationale: a vehicular
    bridge the trail route actually passes is one a hiker could use
    as a crossing without a detour. A 2-mi vehicular net would be
    every county-road bridge in the corridor (hundreds) and unreadable
    as a crossing-opportunities layer; the 400-m line is the judgment
    call, recorded here.
  Excluded by status in both tiers: K = bridge closed to all traffic,
    G = new structure not yet open to traffic. Blank OPEN codes are
    KEPT: the field does not apply to non-highway records (mostly
    pedestrian structures and route-under records), so a blank is not
    a closed bridge.
  Not carried: SERVICE_ON 2 Railroad (rail bridges are not crossings
    a hiker can use), 4 Highway-railroad, 6/7/8 interchange levels,
    9 Building/plaza, 0 Other.

FIELDS carried (codes decoded per FHWA-PD-96-001 Items 21/22/41/42/43;
raw codes kept alongside where a decode is a judgment):
  bridge_number   STRUCTURE_NUMBER_008 (as published; MnDOT numbers
                  like '01002', federal/tribal like '00000000000F115')
  facility_carried FACILITY_CARRIED_007 (what the bridge carries)
  features_crossed FEATURES_DESC_006A (what it spans)
  location        LOCATION_009 (as published, e.g. '0.8 MI E OF JCT TH 169')
  county          COUNTY_CODE_003 decoded via MN FIPS alphabetical
                  sequence (verified against sample records: 001 Aitkin,
                  021 Cass, 023 Chippewa, 073 Lac qui Parle)
  district        HIGHWAY_DISTRICT_002 (MnDOT district)
  owner / owner_code   OWNER_022 decoded (Items 21/22 code list)
  maintenance / maintenance_code  MAINTENANCE_021 decoded (same list)
  year_built      YEAR_BUILT_027; year_reconstructed YEAR_RECONSTRUCTED_106
  structure_len_m STRUCTURE_LEN_MT_049; deck_width_m DECK_WIDTH_MT_052
  sidewalk_left_m / sidewalk_right_m  LEFT/RIGHT_CURB_MT_050A/050B
                  (Item 50 curb/sidewalk widths — the pedestrian
                  accommodation on the structure; 0.0 = none)
  service_on / service_under  SERVICE_ON_042A / SERVICE_UND_042B decoded
  open_closed     OPEN_CLOSED_POSTED_041 decoded (blank = not applicable)
  structure_kind  STRUCTURE_KIND_043A decoded (1 Concrete, 2 Concrete
                  continuous, 3 Steel, 4 Steel continuous, 5 Prestressed
                  concrete, 6 Prestressed concrete continuous, 7 Wood or
                  Timber, 8 Masonry, 9 Aluminum/Wrought/Cast Iron, 0 Other)
  structure_type  STRUCTURE_TYPE_043B (raw design code, not decoded)
  tier            1 pedestrian/mixed-use | 2 vehicular-near-trail
  dist_trail_km   computed distance to the trail line
  nbi_records     records merged for this structure

Output (source of record; the viewer reads the site/data/ copy
published by scripts/build_site_data.py, scoped build_one):
  data/points/nbi-bridges.geojson

Raw downloads are cached under working/bridges/ so re-runs do not
re-download the 56 MB zip.

Usage: python3 scripts/pull_nbi_bridges.py
"""

import csv
import io
import json
import os
import time
import zipfile

import requests
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

ALLRECS_ZIP_URL = ("https://www.fhwa.dot.gov/bridge/nbi/"
                   "2025allstatesallrecsdel.zip")
ALLRECS_MEMBER = "2025AllRecordsDelimitedAllStates.txt"
WORKDIR = os.path.join(REPO, "working", "bridges")
ZIP_PATH = os.path.join(WORKDIR, "2025allstatesallrecsdel.zip")
MN_TXT = os.path.join(WORKDIR, "MN25_all.txt")
HEADER_URL = ("https://www.fhwa.dot.gov/bridge/nbi/2025/delimited/"
              "MN25.txt")

MN_LINE = os.path.join(REPO, "site", "data", "trail-minnesota.geojson")
# Star of the North line is not yet merged into trail-minnesota.geojson
# (nearest trail line to Remer is 7.0 km), so it joins the corridor
# explicitly. The Arrowhead gaps ARE in trail-minnesota.geojson (the
# line passes Ely and Tower at 0.0 km).
STN_LINE = os.path.join(REPO, "data", "segments", "trail-stn.geojson")
BUFFER_M = 3218.69      # 2 miles, same corridor as timber/motorized/campgrounds
TIER2_M = 400.0         # 0.25 mi — vehicular bridges the trail passes
OUT = os.path.join(REPO, "data", "points", "nbi-bridges.geojson")

TOUTM = Transformer.from_crs("EPSG:4326", "EPSG:26915", always_xy=True)

SERVICE_ON = {
    "0": "Other", "1": "Highway", "2": "Railroad",
    "3": "Pedestrian-bicycle", "4": "Highway-railroad",
    "5": "Highway-pedestrian",
    "6": "Overpass structure at an interchange or second level",
    "7": "Third level (interchange)", "8": "Fourth level (interchange)",
    "9": "Building or plaza",
}
SERVICE_UNDER = {
    "0": "Other", "1": "Highway, with or without pedestrian",
    "2": "Railroad", "3": "Pedestrian-bicycle",
    "4": "Highway-railroad", "5": "Waterway",
    "6": "Highway-waterway", "7": "Railroad-waterway",
    "8": "Highway-waterway-railroad", "9": "Relief for waterway",
}
OPEN_CLOSED = {
    "A": "Open, no restriction",
    "B": "Open, posting recommended but not legally implemented",
    "D": "Open, would be posted except temporary shoring",
    "E": "Open, temporary structure",
    "G": "New structure not yet open to traffic",
    "K": "Bridge closed to all traffic",
    "P": "Posted for load",
    "R": "Posted for other load-capacity restriction",
}
AGENCY = {
    "01": "State Highway Agency", "02": "County Highway Agency",
    "03": "Town or Township Highway Agency",
    "04": "City or Municipal Highway Agency",
    "11": "State Park, Forest, or Reservation Agency",
    "12": "Local Park, Forest, or Reservation Agency",
    "21": "Other State Agencies", "25": "Other Local Agencies",
    "26": "Private (other than railroad)", "27": "Railroad",
    "31": "State Toll Authority", "32": "Local Toll Authority",
    "60": "Other Federal Agencies", "61": "Indian Tribal Government",
    "62": "Bureau of Indian Affairs",
    "63": "Bureau of Fish and Wildlife",
    "64": "U.S. Forest Service", "66": "National Park Service",
    "67": "Tennessee Valley Authority",
    "68": "Bureau of Land Management",
    "69": "Bureau of Reclamation",
    "70": "Corps of Engineers (Civil)",
    "71": "Corps of Engineers (Military)", "72": "Air Force",
    "73": "Navy/Marines", "74": "Army", "75": "NASA",
    "76": "Metropolitan Washington Airports Service",
    "80": "Unknown",
}
STRUCTURE_KIND = {
    "1": "Concrete", "2": "Concrete continuous", "3": "Steel",
    "4": "Steel continuous", "5": "Prestressed concrete",
    "6": "Prestressed concrete continuous", "7": "Wood or Timber",
    "8": "Masonry", "9": "Aluminum, Wrought Iron, or Cast Iron",
    "0": "Other",
}
# Minnesota county FIPS codes. NOTE the "Saint Louis" quirk: FIPS sorts
# "St. Louis" as "Saint Louis", so St. Louis is 137 — BEFORE Scott
# (139), Sherburne (141), Sibley (143). Verified against Census
# (27137 St. Louis, 27139 Scott) and sample records (001 Aitkin,
# 021 Cass, 023 Chippewa, 073 Lac qui Parle). An earlier draft had
# 137 Scott / 139 Sherburne / 141 Sibley / 143 St. Louis — wrong, and
# it mislabeled 24 Iron Range bridges; caught by coordinate check.
COUNTIES = {
    "001": "Aitkin", "003": "Anoka", "005": "Becker", "007": "Beltrami",
    "009": "Benton", "011": "Big Stone", "013": "Blue Earth",
    "015": "Brown", "017": "Carlton", "019": "Carver", "021": "Cass",
    "023": "Chippewa", "025": "Chisago", "027": "Clay",
    "029": "Clearwater", "031": "Cook", "033": "Cottonwood",
    "035": "Crow Wing", "037": "Dakota", "039": "Dodge",
    "041": "Douglas", "043": "Faribault", "045": "Fillmore",
    "047": "Freeborn", "049": "Goodhue", "051": "Grant",
    "053": "Hennepin", "055": "Houston", "057": "Hubbard",
    "059": "Isanti", "061": "Itasca", "063": "Jackson",
    "065": "Kanabec", "067": "Kandiyohi", "069": "Kittson",
    "071": "Koochiching", "073": "Lac qui Parle", "075": "Lake",
    "077": "Lake of the Woods", "079": "Le Sueur", "081": "Lincoln",
    "083": "Lyon", "085": "McLeod", "087": "Mahnomen",
    "089": "Marshall", "091": "Martin", "093": "Meeker",
    "095": "Mille Lacs", "097": "Morrison", "099": "Mower",
    "101": "Murray", "103": "Nicollet", "105": "Nobles",
    "107": "Norman", "109": "Olmsted", "111": "Otter Tail",
    "113": "Pennington", "115": "Pine", "117": "Pipestone",
    "119": "Polk", "121": "Pope", "123": "Ramsey", "125": "Red Lake",
    "127": "Redwood", "129": "Renville", "131": "Rice", "133": "Rock",
    "135": "Roseau", "137": "St. Louis", "139": "Scott",
    "141": "Sherburne", "143": "Sibley", "145": "Stearns",
    "147": "Steele", "149": "Stevens", "151": "Swift", "153": "Todd",
    "155": "Traverse", "157": "Wabasha", "159": "Wadena",
    "161": "Waseca", "163": "Washington", "165": "Watonwan",
    "167": "Wilkin", "169": "Winona", "171": "Wright",
    "173": "Yellow Medicine",
}


def fetch(url, path, retries=3):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"using cached {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=300, stream=True)
            r.raise_for_status()
            with open(path, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
            print(f"downloaded {url} -> {path} "
                  f"({os.path.getsize(path)} bytes)")
            return
        except Exception as e:  # noqa: BLE001 — retry then raise
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err


def ddmmss_to_deg(s, lon=False):
    """NBI LAT_016 (DDMMSS.ss) / LONG_017 (DDDMMSS.ss) to decimal deg.

    The field is fixed-width with exactly two decimal digits on the
    seconds: lat is 8 chars DD MM SS ss, lon is 9 chars DDD MM SS ss.
    (An earlier draft parsed the seconds as float(s[4:]) — i.e. read
    '28.32' as 2832 seconds — shifting every point by up to ~0.8 deg.
    Caught by the Arrowhead diagnostic before wiring; this is the fix.)
    """
    s = s.strip()
    if lon:
        deg = int(s[:3])
        minutes = int(s[3:5])
        seconds = int(s[5:7]) + int(s[7:9]) / 100.0
    else:
        deg = int(s[:2])
        minutes = int(s[2:4])
        seconds = int(s[4:6]) + int(s[6:8]) / 100.0
    return deg + minutes / 60.0 + seconds / 3600.0


def num(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def unquote(s):
    """NBI delimited files quote text fields in single quotes
    ('MN 200'); strip one surrounding pair."""
    s = (s or "").strip()
    if len(s) >= 2 and s.startswith("'") and s.endswith("'"):
        return s[1:-1].strip()
    return s


def main():
    fetch(ALLRECS_ZIP_URL, ZIP_PATH)
    # Header row comes from the highway delimited file (same columns).
    fetch(HEADER_URL, os.path.join(WORKDIR, "MN25_header.txt"))
    with open(os.path.join(WORKDIR, "MN25_header.txt")) as fh:
        header = fh.readline().strip().split(",")

    # Extract Minnesota (state code 27) records from the all-records zip.
    if not (os.path.exists(MN_TXT) and os.path.getsize(MN_TXT) > 0):
        with zipfile.ZipFile(ZIP_PATH) as zf:
            with zf.open(ALLRECS_MEMBER) as raw, open(MN_TXT, "w") as out:
                n = 0
                for line in io.TextIOWrapper(raw, errors="replace"):
                    if line.startswith("27,"):
                        out.write(line)
                        n += 1
        print(f"extracted {n} Minnesota records -> {MN_TXT}")
    else:
        print(f"using cached {MN_TXT}")

    # Dedupe by structure number; prefer record type 1.
    structs = {}
    with open(MN_TXT, newline="") as fh:
        reader = csv.DictReader(fh, fieldnames=header)
        for row in reader:
            key = row["STRUCTURE_NUMBER_008"].strip()
            if key not in structs:
                structs[key] = (row, 1)
            else:
                prev, cnt = structs[key]
                structs[key] = (prev, cnt + 1)
                if (prev["RECORD_TYPE_005A"] != "1"
                        and row["RECORD_TYPE_005A"] == "1"):
                    structs[key] = (row, cnt + 1)
    print(f"distinct structures: {len(structs)}")

    # Corridor: 2-mi buffer around the statewide trail line + the Star
    # of the North line, UTM 15N. Each line piece is transformed
    # separately and indexed (STRtree) so the 13,795 distance checks
    # only measure against nearby pieces — a whole-union distance per
    # bridge plus a buffer of the 300-mile line OOM-killed this script
    # on 2026-11-18 (6 GB VM, concurrent agents running).
    from shapely import transform as shp_transform
    from shapely.strtree import STRtree
    import numpy as np

    def _to_utm(coords):
        x, y = TOUTM.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    pieces = []
    for path in (MN_LINE, STN_LINE):
        with open(path) as fh:
            gj = json.load(fh)
        for feat in gj["features"]:
            g = shape(feat["geometry"])
            if g.is_empty:
                continue
            pieces.append(shp_transform(g, _to_utm))
    tree = STRtree(pieces)

    def dist_to_trail_m(pt_utm):
        """Shortest distance (m) from a UTM point to the trail line."""
        idx = tree.query(pt_utm, predicate="dwithin", distance=BUFFER_M)
        if len(idx) == 0:
            return None
        return min(pieces[i].distance(pt_utm) for i in idx)

    kept = []
    counts = {"tier1": 0, "tier2": 0, "dropped_status": 0,
              "dropped_service": 0, "dropped_distance": 0}
    for key, (row, nrec) in structs.items():
        try:
            lat = ddmmss_to_deg(row["LAT_016"])
            lon = -ddmmss_to_deg(row["LONG_017"], lon=True)
        except (ValueError, IndexError):
            continue
        pt_utm = Point(TOUTM.transform(lon, lat))
        dist_m = dist_to_trail_m(pt_utm)
        if dist_m is None:
            counts["dropped_distance"] += 1
            continue
        service = row["SERVICE_ON_042A"].strip()
        status = row["OPEN_CLOSED_POSTED_041"].strip()
        if status in ("K", "G"):
            counts["dropped_status"] += 1
            continue
        if service in ("3", "5"):
            tier = 1
            if dist_m > BUFFER_M:
                counts["dropped_distance"] += 1
                continue
        elif service == "1":
            tier = 2
            if dist_m > TIER2_M:
                counts["dropped_distance"] += 1
                continue
        else:
            counts["dropped_service"] += 1
            continue
        if tier == 1:
            counts["tier1"] += 1
        else:
            counts["tier2"] += 1
        county_code = row["COUNTY_CODE_003"].strip()
        props = {
            "bridge_number": key,
            "facility_carried": unquote(row["FACILITY_CARRIED_007"]),
            "features_crossed": unquote(row["FEATURES_DESC_006A"]),
            "location": unquote(row["LOCATION_009"]),
            "county": COUNTIES.get(county_code, "County " + county_code),
            "county_code": county_code,
            "district": (row["HIGHWAY_DISTRICT_002"] or "").strip(),
            "owner": AGENCY.get(row["OWNER_022"].strip(),
                                "Code " + row["OWNER_022"].strip()),
            "owner_code": row["OWNER_022"].strip(),
            "maintenance": AGENCY.get(row["MAINTENANCE_021"].strip(),
                                      "Code " + row["MAINTENANCE_021"].strip()),
            "maintenance_code": row["MAINTENANCE_021"].strip(),
            "year_built": num(row["YEAR_BUILT_027"]),
            "year_reconstructed": num(row["YEAR_RECONSTRUCTED_106"]),
            "structure_len_m": num(row["STRUCTURE_LEN_MT_049"]),
            "deck_width_m": num(row["DECK_WIDTH_MT_052"]),
            "sidewalk_left_m": num(row["LEFT_CURB_MT_050A"]),
            "sidewalk_right_m": num(row["RIGHT_CURB_MT_050B"]),
            "service_on": SERVICE_ON.get(service, "Code " + service),
            "service_on_code": service,
            "service_under": SERVICE_UNDER.get(
                row["SERVICE_UND_042B"].strip(),
                "Code " + row["SERVICE_UND_042B"].strip()),
            "open_closed": (OPEN_CLOSED.get(status, "Not applicable")
                            if status else "Not applicable"),
            "open_closed_code": status,
            "structure_kind": STRUCTURE_KIND.get(
                row["STRUCTURE_KIND_043A"].strip(),
                "Code " + row["STRUCTURE_KIND_043A"].strip()),
            "structure_type": row["STRUCTURE_TYPE_043B"].strip(),
            "tier": tier,
            "dist_trail_km": round(dist_m / 1000.0, 2),
            "nbi_records": nrec,
            "source": "FHWA NBI 2025",
        }
        # Year fields are ints when present.
        for k in ("year_built", "year_reconstructed"):
            if props[k] is not None:
                props[k] = int(props[k])
        kept.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props,
        })

    kept.sort(key=lambda f: (f["properties"]["tier"],
                             f["properties"]["dist_trail_km"]))
    out = {"type": "FeatureCollection", "features": kept}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {len(kept)} features -> {OUT}")
    print("counts:", counts)
    # County / tier summary for the report and SOURCES.md.
    from collections import Counter
    print("by tier:", Counter(f["properties"]["tier"] for f in kept))
    print("by county:",
          Counter(f["properties"]["county"] for f in kept).most_common())
    print("by service_on:",
          Counter(f["properties"]["service_on"] for f in kept))
    print("by open_closed:",
          Counter(f["properties"]["open_closed"] for f in kept))


if __name__ == "__main__":
    main()

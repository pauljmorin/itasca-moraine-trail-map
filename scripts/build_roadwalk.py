#!/usr/bin/env python3
"""Build the Road walk layer data: the on-road line, one speed
badge per T07 segment, and the crash-analysis (HIN) markers.

Sources (all verified, nothing invented):
  * The western road-walk segments, speeds and crash spots come
    from T07 (Trail Research Brief T07 - Western Road Walk: The
    Safety Case, Segment by Segment, Nov 15, 2026; data retrieved
    Nov 16, 2026). Re-exported Nov 18, 2026 from the output Doc
    (nct-western-roadwalk-safety-2026-11-15,
    1wHqDBbJxoU-k128QWiQkUa1DNPwBTZ0eFxn4C6qNJho). T07's 15
    segments are defined by NCT mile (MN-0.0 to MN-106.5) and road
    name from the NCTA Minnesota Map Series (MN-001 to MN-020);
    speeds are statutory (Minn. Stat. 169.14: 55 rural / 30 urban
    / 65 expressway) or the Otter Tail County Safety Action Plan
    (adopted May 26, 2026) "majority 55 mph" finding; crash spots
    are the SAP's High-Injury Network corridors (pp. 60-64) and
    systemic-risk tiers (Table 10, pp. 73-75).
  * Geometry: the western gap line
    (site/buildout/data/gap-western.geojson, the NCTA-service
    line, 90 features, 104.86 mi) ordered west-to-east by a
    graph walk from the Red River end (endpoint adjacency within
    2 km). The walk was validated against T07's mileposts:
    City of Fergus Falls lands at chain mile 39.5-42.4 (T07
    MN-40.0-43.5), Maplewood Church Rd at 67.3 (T07 MN-66.0-68.5),
    Becker Co Line at 95.1-96.4 (T07 MN-94.8-97.0). Chain miles
    track T07 miles within ~1 mi throughout (chain total 104.86
    mi vs T07 corridor 107.0 mi). Speed/crash icons sit at the
    midpoint of their segment's mile range, located by cumulative
    chain miles; positions are approximate within ~1 mi and the
    popups say so.
  * The Arrowhead road walk: the gap-arrowhead line's
    surface=="road" features (14 features, 25.0 mi) - the
    on-road pieces of the Grand Rapids-to-Ely gap. The Mesabi
    Trail bike path (surface=="paved", 114.9 mi) is NOT road
    walk and is not drawn here.
  * GAP (reported, not filled): T07's crash data covers the
    WESTERN road walk only (Wilkin / Otter Tail / Becker).
    No crash analysis exists in the packet for the ITM or
    Arrowhead road walk, and no per-segment posted speeds were
    verified for the Arrowhead road segments - so the Arrowhead
    pieces carry the road-walk LINE only, no speed badge and no
    crash icon. Wilkin/Becker segment-level pedestrian/bicycle
    counts could not be resolved in T07 either (MnCMAT2
    login-restricted; MNCrash upstream error; TCMAC gated) -
    the layer does not claim them.
  * SHOULDERS (added 2026-11-18): no as-built shoulder width
    exists for any western segment in any reachable
    authoritative source. T07 Leg 2 ("Shoulder Width / Edge
    Condition" column) reads "Not published in MnDOT TCDS"
    for all 15 segments - MnDOT TCDS omits shoulder widths in
    public station views - and Segs 3 and 8 have no TCDS
    station at all. What T07 does give per segment is edge
    CONDITION: the Otter Tail SAP systemic-risk tier and Edge
    Risk 2S/3 deficiencies (SAP Table 10, pp. 73-75), plus
    the Seg 7 sidewalk. Those are carried as
    "shoulder_quality" - a condition statement, NOT a width.
    No numeric shoulder_width_ft is carried for any segment.
    Checked and NOT usable as as-built widths: MN Rules
    8820.9920 (design-table required widths for new
    construction by projected ADT, not measurements); the
    MnDOT Bikeways map (shows per-road shoulder widths but is
    JS-only; the statewide BIKEWAY FeatureServer is
    WAF-blocked to text fetch, and the Bikeways Data Standard
    v1.0 carries no numeric shoulder-width field - shoulder
    appears only as a separation-type value); the MnDOT
    District 4 shoulder-widening prioritization study
    (exists, could not be located - request from District 4);
    county bikeways maps ("Paved Shoulder 4' or Wider" class,
    per-road values need a visual map read, not tried here).
    Benchmark (guidance, not a measurement): FHWA recommends
    a walkable shoulder of at least 4 ft (stabilized or paved)
    on both sides of rural highways routinely used by
    pedestrians. The Arrowhead road pieces carry no shoulder
    fields at all - nothing was found for them.
  * OBSERVED SPEEDS (added 2026-11-18): none published per
    segment. MnDOT's Speed Monitoring Program (57 automated
    stations) reports average 85th percentile speed aggregated
    by roadway category only (five categories) and publishes
    no station list, so no station can be tied to a road-walk
    segment and the category average must NOT be substituted
    as a segment speed. MnDOT speed studies exist for CSAH 1
    (Tower Road), CSAH 1 in Weetown, CSAH 4 & 60 in Vergas,
    CSAH 35, CSAH 41 and CSAH 88 (Otter Tail County Board
    minutes, Jan 3, 2023) - but only the recommendations are
    public (e.g. CSAH 1 Weetown: raise 50 to 55 mph; CSAH 4 &
    60 Vergas: no change in 40 mph; CSAH 41: no change in
    55 mph), not the measured 85th percentile speeds; the
    studies themselves are a records request to MnDOT District
    4 / Otter Tail County Highway Dept. T07 contains no
    observed-speed data at all (no 85th percentile values, no
    speed-study results, no "speeding" mentions).

  * VERGAS SPEED BADGE REMOVED (Paul, Nov 19, 2026): the Seg 12
    speed badge is NOT built. The county minutes (MnDOT speed
    study, Otter Tail Board minutes Jan 3, 2023) say 40 mph in
    Vergas; the brief (T07 / Otter Tail SAP p. 67) says 30 mph.
    Paul: remove the badge, do not reconcile the discrepancy.
    The Seg 12 LINE and its HIN crash marker stay — only the
    badge goes, so a rebuild does not resurrect it. The Seg 12
    line popup therefore carries no speed row.
  * ENDPOINTS + LENGTHS (added 2026-11-19, Paul): every line
    feature carries length_mi (drawn length, measured from the
    geometry) and from_name / to_name — the trail the road walk
    leaves and joins at each end. Western segments are enriched
    per SEGMENT (all pieces of a segment share the values): the
    endpoints are found by walking the ordered NCTA-service
    chain outward from the segment's T07 mile range. A foot /
    paved / sidewalk feature reached within 1 chain-mile is
    named (its seg_name + kind, e.g. "Prairie Wetlands Learning
    Center (foot tread)"); if the walk runs along road into the
    next T07 segment, the end reads "Road walk continues — Seg N";
    if the walk meets an untyped ("other") feature, or 1 mile
    passes with no tread and no next segment, the end reads
    "No adjoining trail identified in the map data". Chain ends
    are special: the west end of Seg 1 is the Red River — the
    western end of the route; the east end of Seg 15 runs past
    the end of the NCTA-service chain (104.86 mi vs the T07
    corridor 107.0 mi), so it is checked against the statewide
    NCT line, which continues east as footpath. Arrowhead pieces
    are enriched per PIECE: the nearest foot-tread or paved
    multi-use path (gap-arrowhead foot/paved features, or the
    bike-trails layer) within 500 m of the piece end, by
    point-to-line distance; nothing within 500 m leaves the
    field off and the popup falls back to "No adjoining trail
    identified". No endpoint name is invented: a name comes only
    from an adjoining feature's seg_name / trail_name, or the
    fixed fallback strings above. Speed and HIN facts ride on
    the western line features from the T07 table (speed_mph /
    speed_text / aadt) and HIN_SPOTS (hin_score / hin_extent /
    hin_note) — except Seg 12, which carries no speed fields
    (badge removed).

Output: data/roadwalk.geojson (working data) with a "kind"
property per feature: "line" (the road-walk line), "speed"
(one badge per T07 segment), "crash" (one marker per HIN
corridor). The published file is built by
scripts/build_site_data.py into site/data/roadwalk.geojson.
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo_util import iter_line_segments, point_seg_dist_km  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
GAP_WESTERN = REPO_ROOT / "site" / "buildout" / "data" / "gap-western.geojson"
GAP_ARROWHEAD = REPO_ROOT / "site" / "buildout" / "data" / "gap-arrowhead.geojson"
OUT_PATH = REPO_ROOT / "data" / "roadwalk.geojson"

KM_PER_MILE = 1.60934
KM_PER_DEG_LAT = 111.195
KM_PER_DEG_LON = 75.93  # at 47 N


# ---------------------------------------------------------------- T07 table
# (segment, road, start_mi, end_mi, badge_mph, speed wording, AADT note)
# Badge value = the limit at the segment's midpoint (verified against
# the T07 wording and the midpoint's setting: rural except Seg 7
# (Fergus Falls urban) and the US-10 crossing in Seg 14).
T07_SEGMENTS = [
    ("Seg 1", "CSAH 22 / Kent streets", 0.0, 2.0, "55",
     "55 mph statutory rural / 30 mph in Kent (Minn. Stat. \u00a7 169.14)",
     "452 (2025) near Fort Abercrombie; 420 (2025) in Kent"),
    ("Seg 2", "CSAH 24 / 230th St / Co Rd 172", 2.0, 8.5, "55",
     "55 mph statutory (Minn. Stat. \u00a7 169.14)",
     "138 (2026 actual) east of Kent"),
    ("Seg 3", "210th Ave / Wilkin Co 11", 8.5, 10.5, "55",
     "55 mph statutory (Minn. Stat. \u00a7 169.14)",
     "No MnDOT TCDS station on this segment"),
    ("Seg 4", "CSAH 26 / 210th St", 10.5, 23.5, "55",
     "55 mph statutory rural / 30 mph in Rothsay (Minn. Stat. \u00a7 169.14)",
     "181-442 (2025-2026) across four stations"),
    ("Seg 5", "Co Rd 11 / Old Hwy 52", 23.5, 37.0, "55",
     "Majority 55 mph on county segments (Otter Tail SAP, p. 67); 30 mph urban",
     "69-1,873 (2025-2026) across five stations"),
    ("Seg 6", "CSAH 88", 37.0, 40.0, "55",
     "Majority 55 mph rural (Otter Tail SAP, p. 67), transitioning to urban speeds approaching Fergus Falls",
     "678-5,259 (2025-2026); highest county-highway volume on the western route"),
    ("Seg 7", "Fergus Falls city streets", 40.0, 43.5, "30",
     "30 mph statutory urban (Minn. Stat. \u00a7 169.14)",
     "Urban local streets; concrete sidewalks ~3.64 mi"),
    ("Seg 8", "245th St E", 52.5, 53.5, "55",
     "55 mph statutory rural unless posted (Minn. Stat. \u00a7 169.14)",
     "No MnDOT TCDS station (local township/county road)"),
    ("Seg 9", "CSAH 1", 53.5, 57.5, "55",
     "Majority 55 mph (Otter Tail SAP, p. 67)",
     "707-3,836 (2025) across seven stations"),
    ("Seg 10", "CSAH 3", 57.5, 66.0, "55",
     "Majority 55 mph (Otter Tail SAP, p. 67)",
     "351-831 (2025) across four stations"),
    ("Seg 11", "CSAH 24 / Maplewood Church Rd", 66.0, 68.5, "55",
     "Majority 55 mph (Otter Tail SAP, p. 67)",
     "474-576 (2025) across three stations"),
    ("Seg 12", "CSAH 41 / CSAH 4 / Vergas", 81.5, 86.5, "55",
     "Majority 55 mph rural / 30 mph in Vergas (Otter Tail SAP, p. 67)",
     "525-3,262 (2025) across seven stations"),
    ("Seg 13", "MN-228 / CSAH 60", 87.5, 92.5, "55",
     "Majority 55 mph rural (Otter Tail SAP, p. 67)",
     "965-1,309 (2025) on CSAH 60"),
    ("Seg 14", "US-10 / Co Rd 134 / Frazee", 94.8, 97.0, "65",
     "65 mph statutory on expressways like US-10, 55 mph on rural county roads, 30 mph in Frazee (Minn. Stat. \u00a7 169.14)",
     "US-10: 8,795-9,282 (2025); Co Rd 134: 667 (2026)"),
    ("Seg 15", "Co Rd 29 / Co Rd 120", 98.0, 106.5, "55",
     "55 mph statutory rural (Minn. Stat. \u00a7 169.14)",
     "1,651 (2025) on CSAH 29"),
]

# HIN crash corridors (Otter Tail SAP, pp. 60-64). "mile" = the chain
# mile where the marker sits (segment midpoint, or the Vergas / Tower
# Road portion of the segment - see notes). Tiers from SAP Table 10.
HIN_SPOTS = [
    {"road": "CSAH 88", "mile": 39.5, "hin": "6.0", "segment": "Seg 6",
     "extent": "North of Fergus Falls, south of 175th Ave to south of 180th Ave",
     "tier": "Tier 3 systemic risk (SAP Table 10, p. 75)",
     "note": "Highest county-highway traffic on the western route (678-5,259 AADT)."},
    {"road": "CSAH 4", "mile": 85.5, "hin": "6.0", "segment": "Seg 12",
     "extent": "In Vergas, S 1st Ave to north of Co Hwy 130",
     "tier": "Tier 3 systemic risk (SAP Table 10, p. 75); CSAH 41 in the same segment is Tier 1",
     "note": "CSAH 4 carries 901-3,262 AADT (2025) through Vergas."},
    {"road": "CSAH 1 / Tower Road", "mile": 56.5, "hin": "7.0",
     "segment": "Seg 9 (adjacent)",
     "extent": "In Fergus Falls, Spartan Dr to north of I-94",
     "tier": "Tier 3 systemic risk (SAP Table 10, pp. 74-75)",
     "note": "Highest HIN score on the western route; the corridor connects with Seg 9."},
]

# ---------------------------------------------------------------- shoulders
# Shoulder width / edge condition per T07 segment, transcribed
# from T07 Leg 2 ("Segment Safety & Traffic Data Breakdown", the
# "Shoulder Width / Edge Condition" column; T07 output Doc
# nct-western-roadwalk-safety-2026-11-15,
# 1wHqDBbJxoU-k128QWiQkUa1DNPwBTZ0eFxn4C6qNJho).
#
# INTERPRETATION METHOD (so every value is reproducible):
# shoulder_quality is a DIRECT COPY of the T07 table cell for
# the segment, lightly compressed (station lists dropped, the
# SAP tier/edge-risk clauses kept verbatim in substance). No
# width is inferred, estimated or derived from any other
# source: where the cell says "Not published", the field says
# so. The one wording change is Seg 7: the T07 cell reads
# "Concrete sidewalk" and the row text adds "Concrete
# sidewalks along ~3.64 mi in NCTA GIS" - the field renders
# that as "Concrete sidewalk along ~3.64 mi (NCTA GIS); no
# shoulder - walkers on sidewalk". The "no shoulder" clause
# is a wording summary [judgment: the cell does not state it
# in those words; the sidewalk is the documented edge
# condition for the segment]. No numeric shoulder_width_ft
# key is emitted for any segment: no as-built width exists
# in any source checked (see the docstring), so the key is
# ABSENT, not zero and not a design-table value. Segs 3 and
# 8 read "Not published (no MnDOT TCDS station on this
# segment)" because T07 records no station there.
SHOULDER = {
    "Seg 1": ("Not published in MnDOT TCDS",
              "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 2": ("Not published in MnDOT TCDS",
              "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 3": ("Not published (no MnDOT TCDS station on this segment)",
              "T07 Leg 2"),
    "Seg 4": ("Not published in MnDOT TCDS",
              "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 5": ("Not published in MnDOT TCDS",
              "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 6": ("Not published in MnDOT TCDS; CSAH 88 on Otter Tail "
              "High-Injury Network (HIN score 6.0) and Tier 3 "
              "systemic risk (SAP Table 10, p. 75)",
              "T07 Leg 2 (MnDOT TCDS; Otter Tail SAP)"),
    "Seg 7": ("Concrete sidewalk along ~3.64 mi (NCTA GIS); no "
              "shoulder - walkers on sidewalk",
              "T07 Leg 2 (NCTA GIS)"),
    "Seg 8": ("Not published (no MnDOT TCDS station on this segment)",
              "T07 Leg 2"),
    "Seg 9": ("Not published in MnDOT TCDS; CSAH 1 segments 9, "
              "15-20 Tier 3 systemic risk (SAP Table 10, pp. 74-75)",
              "T07 Leg 2 (MnDOT TCDS; Otter Tail SAP)"),
    "Seg 10": ("Not published in MnDOT TCDS; CSAH 3 segments 1-3 "
               "Tier 2 systemic risk with Edge Risk 2S/3 deficiencies "
               "(SAP Table 10, pp. 73-74)",
               "T07 Leg 2 (MnDOT TCDS; Otter Tail SAP)"),
    "Seg 11": ("Not published in MnDOT TCDS",
               "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 12": ("Not published in MnDOT TCDS; CSAH 41 Segments 1 & 2 "
               "Tier 1 systemic risk (all 4 risk factors incl. Edge "
               "Risk 2S/3, SAP Table 10, p. 73); CSAH 4 in Vergas on "
               "HIN (score 6.0) and Tier 3 systemic risk",
               "T07 Leg 2 (MnDOT TCDS; Otter Tail SAP)"),
    "Seg 13": ("Not published in MnDOT TCDS",
               "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 14": ("Not published in MnDOT TCDS",
               "T07 Leg 2 (MnDOT TCDS)"),
    "Seg 15": ("Not published in MnDOT TCDS",
               "T07 Leg 2 (MnDOT TCDS)"),
}

CRASH_CAVEAT = (
    "Otter Tail County 2020-2024: 17 pedestrian crashes (1 fatal/serious, "
    "16 non-severe) and 2 bicycle crashes on the county highway system. "
    "No published record attributes any crash to a hiker, and no hiker "
    "fatality or injury on the western road walk is documented. "
    "Wilkin/Becker segment-level pedestrian/bicycle counts could not be "
    "resolved from public sources (T07 Leg 3)."
)


# ---------------------------------------------------------------- geometry
def ends(f):
    cs = f["geometry"]["coordinates"]
    return [tuple(cs[0]), tuple(cs[-1])]


def dist_km(a, b):
    return math.hypot((a[0] - b[0]) * KM_PER_DEG_LON,
                      (a[1] - b[1]) * KM_PER_DEG_LAT)


def order_chain(features):
    """Order the western gap features west->east by endpoint adjacency.

    Returns (order, entry): order is the feature indices west->east;
    entry[i] is the endpoint of feature i where the chain ENTERS it
    (the west end), so a feature whose coordinates run east->west
    can be flipped to chain direction before any mile interpolation.
    """
    n = len(features)
    adj = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            d = min(dist_km(a, b) for a in ends(features[i])
                    for b in ends(features[j]))
            if d <= 2.0:
                adj[i].add(j)
                adj[j].add(i)
    west = [i for i in range(n)
            if len(adj[i]) == 1
            and min(e[0] for e in ends(features[i])) < -96.6]
    if len(west) != 1:
        raise RuntimeError(f"expected one Red River end, got {len(west)}")
    order = [west[0]]
    entry = {west[0]: min(ends(features[west[0]]),
                          key=lambda e: e[0])}
    prev, cur = None, west[0]
    while True:
        nxt = [j for j in adj[cur] if j != prev and j not in order]
        if not nxt:
            break

        def dcur(j):
            return min(dist_km(a, b) for a in ends(features[cur])
                       for b in ends(features[j]))
        nxt.sort(key=dcur)
        nxt_feat = nxt[0]
        # the entry end of the next feature is the endpoint nearest
        # the current feature's exit end
        cur_exit = (ends(features[cur])[1] if entry[cur] == ends(features[cur])[0]
                    else ends(features[cur])[0])
        entry[nxt_feat] = min(ends(features[nxt_feat]),
                              key=lambda e: dist_km(e, cur_exit))
        prev, cur = cur, nxt_feat
        order.append(cur)
    if len(order) != n:
        raise RuntimeError(f"chain covers {len(order)} of {n} features")
    return order, entry


def oriented_coords(feat, entry_pt):
    """Feature coordinates flipped, if needed, to run entry -> exit."""
    coords = [list(c) for c in feat["geometry"]["coordinates"]]
    if not coords:
        return coords
    d0 = dist_km(tuple(coords[0]), entry_pt)
    d1 = dist_km(tuple(coords[-1]), entry_pt)
    if d1 < d0:
        coords.reverse()
    return coords


def chain_miles(features, order, entry):
    """[(feature, oriented_coords, start_mile, end_mile)] along the chain."""
    out = []
    cum = 0.0
    for i in order:
        length = features[i]["properties"].get("len_miles") or 0.0
        out.append((features[i],
                    oriented_coords(features[i], entry[i]),
                    cum, cum + length))
        cum += length
    return out


def sub_coords(coords, frac0, frac1):
    """Sub-polyline of a coordinate list between two fractions (0-1)
    of its measured length, interpolating within segments."""
    if frac0 <= 0.0 and frac1 >= 1.0:
        return [list(c) for c in coords]
    seg_lens = []
    total = 0.0
    for a, b in zip(coords, coords[1:]):
        d = dist_km(a, b)
        seg_lens.append(d)
        total += d
    if total <= 0:
        return [list(coords[0])]

    def point_at(frac):
        target = frac * total
        acc = 0.0
        for (a, b), d in zip(zip(coords, coords[1:]), seg_lens):
            if acc + d >= target or d == 0:
                t = 0.0 if d == 0 else (target - acc) / d
                t = max(0.0, min(1.0, t))
                return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
            acc += d
        return list(coords[-1])

    out = [point_at(frac0)]
    acc = 0.0
    for (a, b), d in zip(zip(coords, coords[1:]), seg_lens):
        f0, f1 = acc / total, (acc + d) / total
        if f1 > frac0 and f0 < frac1:
            if f0 >= frac0:
                out.append(list(a))
            if f1 <= frac1:
                out.append(list(b))
        acc += d
    out.append(point_at(frac1))
    # drop consecutive duplicates
    ded = [out[0]]
    for p in out[1:]:
        if abs(p[0] - ded[-1][0]) > 1e-9 or abs(p[1] - ded[-1][1]) > 1e-9:
            ded.append(p)
    return ded


def point_at_chain_mile(chain, mile):
    """Coordinate on the ordered chain at a cumulative chain mile."""
    for feat, coords, s, e in chain:
        if s <= mile <= e:
            frac = 0.0 if e == s else (mile - s) / (e - s)
            # interpolate by measured length fraction
            seg_lens = []
            total = 0.0
            for a, b in zip(coords, coords[1:]):
                d = dist_km(a, b)
                seg_lens.append(d)
                total += d
            if total <= 0:
                return list(coords[0]), feat
            target = frac * total
            acc = 0.0
            for (a, b), d in zip(zip(coords, coords[1:]), seg_lens):
                if acc + d >= target:
                    t = 0.0 if d == 0 else (target - acc) / d
                    t = max(0.0, min(1.0, t))
                    return [a[0] + t * (b[0] - a[0]),
                            a[1] + t * (b[1] - a[1])], feat
                acc += d
            return list(coords[-1]), feat
    raise RuntimeError(f"mile {mile} is beyond the chain")


def line_length_mi(coords):
    """Drawn length of a LineString in miles (equirectangular)."""
    total = 0.0
    for a, b in zip(coords, coords[1:]):
        total += dist_km(a, b)
    return total / KM_PER_MILE


ENDPOINT_FALLBACK = "No adjoining trail identified in the map data"
TREAD_KINDS = {"foot": "foot tread", "paved": "paved multi-use path",
               "sidewalk": "sidewalk"}


def tread_display(props, walked_mi):
    """Display name for an adjoining tread feature: its seg_name
    plus the kind in words; a generic label when unnamed. A
    distance clause is added only when the tread is not
    immediately adjoining (walked > 0.05 mi), rounded to the
    nearest mile per the viewer rule."""
    surf = props.get("surface")
    kind = TREAD_KINDS.get(surf, "trail")
    name = (props.get("seg_name") or "").strip()
    if name:
        disp = f"{name} ({kind})"
    else:
        disp = {"foot": "NCT footpath",
                "paved": "Paved multi-use path",
                "sidewalk": "Sidewalk"}.get(surf, "Trail")
    if walked_mi > 0.05:
        disp += f", {round(walked_mi)} mi away"
    return disp


def segment_end_name(chain, total, seg_idx, direction, chain_end_name=None):
    """Endpoint name for one end of a western T07 segment.
    direction -1 = west end, +1 = east end. Walks the ordered
    chain outward from the segment's T07 mile range (method in
    the docstring). Returns the display string, or None when the
    walk runs off the east end of the chain (the caller then
    substitutes chain_end_name, the statewide-line check)."""
    seg = T07_SEGMENTS[seg_idx]
    boundary = seg[2] if direction < 0 else seg[3]
    if direction < 0 and boundary <= 1e-9:
        return "Red River — western end of the route"
    if direction > 0 and boundary >= total - 1e-9:
        return chain_end_name
    # next T07 segment in this direction, if any
    if direction < 0:
        cands = [s for s in T07_SEGMENTS if s[3] <= boundary + 1e-9]
        nxt = max(cands, key=lambda s: s[3]) if cands else None
    else:
        cands = [s for s in T07_SEGMENTS if s[2] >= boundary - 1e-9]
        nxt = min(cands, key=lambda s: s[2]) if cands else None
    pos = boundary
    walked = 0.0
    idxs = range(len(chain)) if direction > 0 else range(len(chain) - 1, -1, -1)
    for i in idxs:
        f, c, s, e = chain[i]
        if direction > 0 and e <= pos + 1e-9:
            continue
        if direction < 0 and s >= pos - 1e-9:
            continue
        props = f.get("properties") or {}
        surf = props.get("surface")
        near = max(s, pos) if direction > 0 else min(e, pos)
        gap = abs(near - pos)
        if surf in ("foot", "paved", "sidewalk"):
            if walked + gap <= 1.0:
                return tread_display(props, walked + gap)
            return ENDPOINT_FALLBACK
        if surf == "road":
            # does this road run into the next T07 segment?
            if nxt is not None:
                if direction > 0 and nxt[2] <= e + 1e-9:
                    return f"Road walk continues — {nxt[0]}"
                if direction < 0 and nxt[3] >= s - 1e-9:
                    return f"Road walk continues — {nxt[0]}"
            far = e if direction > 0 else s
            walked += abs(far - pos)
            pos = far
            continue
        # "other" (untyped) — the line leaves the road/tread system
        return ENDPOINT_FALLBACK
    return chain_end_name


def nearest_tread_name(point, bike_features, gap_features):
    """Nearest foot-tread or paved multi-use path to a point,
    within 500 m by point-to-line distance, across the
    bike-trails layer and the gap-arrowhead foot/paved features.
    Returns the display string, or None when nothing is near."""
    best = None  # (dist_km, kind, name)
    for f in gap_features:
        p = f.get("properties") or {}
        if p.get("surface") not in ("paved", "foot"):
            continue
        kind = ("paved multi-use path" if p["surface"] == "paved"
                else "foot tread")
        for a, b in iter_line_segments(f.get("geometry")):
            d = point_seg_dist_km(point, a, b)
            if best is None or d < best[0]:
                best = (d, kind, (p.get("seg_name") or "").strip())
    for f in bike_features:
        p = f.get("properties") or {}
        name = (p.get("trail_name") or "").strip()
        if not name:
            continue
        for a, b in iter_line_segments(f.get("geometry")):
            d = point_seg_dist_km(point, a, b)
            if best is None or d < best[0]:
                best = (d, "bike path", name)
    if best is None or best[0] * 1000.0 > 500.0:
        return None
    d, kind, name = best
    if name:
        return f"{name} ({kind})"
    return {"foot tread": "NCT footpath",
            "paved multi-use path": "Paved multi-use path"}.get(kind, "Trail")


def main():
    gap_w = json.loads(GAP_WESTERN.read_text())
    gap_a = json.loads(GAP_ARROWHEAD.read_text())
    order, entry = order_chain(gap_w["features"])
    chain = chain_miles(gap_w["features"], order, entry)
    total = chain[-1][3]
    print(f"Western chain: {len(chain)} features, {total:.2f} mi")

    seg_ranges = [(seg[2], seg[3]) for seg in T07_SEGMENTS]

    def in_roadwalk(m0, m1):
        return any(m0 < e and m1 > s for (s, e) in seg_ranges)

    features = []

    # --- western road-walk line: chain pieces clipped to T07 ranges
    west_pieces = 0
    seg_lengths = {}
    for feat, coords, s, e in chain:
        if not in_roadwalk(s, e):
            continue
        for (rs, re) in seg_ranges:
            if e <= rs or s >= re:
                continue
            f0 = 0.0 if e == s else max(0.0, (rs - s) / (e - s))
            f1 = 1.0 if e == s else min(1.0, (re - s) / (e - s))
            sub = sub_coords(coords, f0, f1)
            if len(sub) < 2:
                continue
            seg_name = next(
                (sg[0] for sg in T07_SEGMENTS if sg[2] == rs), "")
            row = next(sg for sg in T07_SEGMENTS if sg[0] == seg_name)
            seg_lengths[seg_name] = (seg_lengths.get(seg_name, 0.0) +
                                     line_length_mi(sub))
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": sub},
                "properties": {
                    "kind": "line", "area": "western",
                    "segment": seg_name,
                    "road": row[1],
                    "miles": f"MN-{rs:.1f} to MN-{re:.1f}",
                    "shoulder_quality": SHOULDER[seg_name][0],
                    "shoulder_source": SHOULDER[seg_name][1],
                    "source": "NCTA gap line clipped to the T07 segment range",
                },
            })
            west_pieces += 1
    print(f"Western road-walk line pieces: {west_pieces}")

    # --- Arrowhead road-walk line: surface == "road" features, whole
    bike_path = REPO_ROOT / "site" / "data" / "bike-trails.geojson"
    bike_features = json.loads(bike_path.read_text())["features"]
    ar_pieces = 0
    ar_miles = 0.0
    for feat in gap_a["features"]:
        props = feat.get("properties") or {}
        if props.get("surface") != "road":
            continue
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if geom.get("type") == "LineString":
            lines = [coords]
        elif geom.get("type") == "MultiLineString":
            lines = coords
        else:
            lines = []
        piece_len = sum(line_length_mi(c) for c in lines)
        ar_miles += piece_len
        start_pt = lines[0][0] if lines and lines[0] else None
        end_pt = lines[-1][-1] if lines and lines[-1] else None
        p = {
            "kind": "line", "area": "arrowhead",
            "segment": "Arrowhead road walk",
            "length_mi": round(piece_len, 2),
            "source": "NCTA gap line, surface = road (the Mesabi "
                      "Trail bike path, surface = paved, is not road walk)",
        }
        if start_pt is not None:
            name = nearest_tread_name(start_pt, bike_features,
                                      gap_a["features"])
            if name:
                p["from_name"] = name
        if end_pt is not None:
            name = nearest_tread_name(end_pt, bike_features,
                                      gap_a["features"])
            if name:
                p["to_name"] = name
        features.append({
            "type": "Feature",
            "geometry": feat.get("geometry"),
            "properties": p,
        })
        ar_pieces += 1
    print(f"Arrowhead road-walk line pieces: {ar_pieces} ({ar_miles:.1f} mi)")

    # --- western segment enrichment: length, endpoints, speed, HIN
    # (per segment; every piece of a segment shares the values)
    tm_path = REPO_ROOT / "site" / "data" / "trail-minnesota.geojson"
    chain_end_name = None
    try:
        tm = json.loads(tm_path.read_text())
        end_pt = chain[-1][1][-1]
        best = None
        for f in tm["features"]:
            fp = f.get("properties") or {}
            if fp.get("trail_type") != "Foot Path":
                continue
            for a, b in iter_line_segments(f.get("geometry")):
                d = point_seg_dist_km(end_pt, a, b)
                if best is None or d < best:
                    best = d
        if best is not None and best * 1000.0 <= 500.0:
            chain_end_name = ("NCT footpath — the chapter line "
                              "continues east")
    except FileNotFoundError:
        pass
    seg_info = {}
    for i, (seg, road, s, e, mph, wording, aadt) in enumerate(T07_SEGMENTS):
        info = {
            "length_mi": round(seg_lengths.get(seg, 0.0), 2),
            "from_name": (segment_end_name(chain, total, i, -1,
                                           chain_end_name)
                          or ENDPOINT_FALLBACK),
            "to_name": (segment_end_name(chain, total, i, +1,
                                         chain_end_name)
                        or ENDPOINT_FALLBACK),
        }
        if seg != "Seg 12":
            # No speed fields on Seg 12 (Paul, Nov 19, 2026 — the
            # Vergas badge is removed; the disputed figure must not
            # reappear in the line popup either).
            info["speed_mph"] = mph
            info["speed_text"] = wording
            info["aadt"] = aadt
        for spot in HIN_SPOTS:
            if spot["segment"].split(" (")[0] == seg:
                info["hin_score"] = spot["hin"]
                info["hin_extent"] = spot["extent"]
                info["hin_note"] = spot["note"]
        seg_info[seg] = info
    for f in features:
        p = f.get("properties") or {}
        if p.get("kind") == "line" and p.get("area") == "western":
            p.update(seg_info[p["segment"]])
    for seg, info in sorted(seg_info.items()):
        print(f"  {seg}: {info['length_mi']} mi, "
              f"from {info['from_name']!r}, to {info['to_name']!r}")

    # --- speed badges: one per T07 segment, at the range midpoint
    # (Seg 14 is the exception: its midpoint falls in Frazee, but the
    # segment's expressway portion is the US-10 crossing at its west
    # end, so the badge sits at the crossing, chain mile 95.2.)
    # Seg 12 has NO badge (Paul, Nov 19, 2026 — the Vergas badge is
    # removed; the county-minutes 40 mph and the brief's 30 mph
    # disagree and the discrepancy is not worth reconciling).
    badges = 0
    for (seg, road, s, e, mph, wording, aadt) in T07_SEGMENTS:
        if seg == "Seg 12":
            continue
        mid = (s + e) / 2.0
        note = ("Segment midpoint by cumulative trail miles; position "
                "approximate within ~1 mi")
        if seg == "Seg 14":
            mid = 95.2
            note = ("At the US-10 crossing (west end of the segment), not "
                    "the segment midpoint - the crossing is the segment's "
                    "65 mph expressway portion; Frazee streets in this "
                    "segment are 30 mph; position approximate within ~1 mi")
        pt, feat = point_at_chain_mile(chain, mid)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": pt},
            "properties": {
                "kind": "speed", "area": "western",
                "segment": seg, "road": road,
                "miles": f"MN-{s:.1f} to MN-{e:.1f}",
                "speed_mph": mph, "speed_text": wording,
                "aadt": aadt,
                "shoulder_quality": SHOULDER[seg][0],
                "shoulder_source": SHOULDER[seg][1],
                "position_note": note,
                "source": "T07 (MnDOT TCDS; Minn. Stat. \u00a7 169.14; "
                          "Otter Tail SAP, adopted May 26, 2026)",
            },
        })
        badges += 1
    print(f"Speed badges: {badges} (Seg 12 removed, Paul Nov 19, 2026)")

    # --- crash markers: one per HIN corridor
    for spot in HIN_SPOTS:
        pt, feat = point_at_chain_mile(chain, spot["mile"])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": pt},
            "properties": {
                "kind": "crash", "area": "western",
                "road": spot["road"], "hin_score": spot["hin"],
                "segment": spot["segment"],
                "extent": spot["extent"],
                "tier": spot["tier"],
                "note": spot["note"],
                "caveat": CRASH_CAVEAT,
                "position_note": "Corridor extent per the SAP; marker at "
                                 "the segment midpoint, approximate within ~1 mi",
                "source": "T07 Leg 3 (Otter Tail County Safety Action "
                          "Plan, adopted May 26, 2026, pp. 60-64, Table 10)",
            },
        })
    print(f"Crash markers: {len(HIN_SPOTS)}")

    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Road walk: on-road line (western T07 segments + "
                       "Arrowhead road pieces), speed badges (T07), HIN "
                       "crash markers (Otter Tail SAP)",
            "built": "scripts/build_roadwalk.py",
            "western_chain_miles": round(total, 2),
            "gap_note": "T07 covers the western road walk only. No crash "
                        "analysis and no verified per-segment speeds exist "
                        "in the packet for the ITM or Arrowhead road walk, "
                        "so the Arrowhead pieces carry the line only. "
                        "Shoulders: no as-built shoulder width is published "
                        "for any western segment (MnDOT TCDS omits shoulder "
                        "widths), so the layer carries the T07 edge-condition "
                        "note per segment (shoulder_quality) and no numeric "
                        "shoulder_width_ft for any segment; the Arrowhead "
                        "pieces carry no shoulder fields at all. Observed "
                        "speeds: none published per segment - MnDOT's Speed "
                        "Monitoring Program reports average 85th percentile "
                        "speed aggregated by roadway category only, with no "
                        "published station list; speed studies exist for "
                        "CSAH 1, 4, 41, 60 and 88 (Otter Tail Board minutes, "
                        "Jan 3, 2023) but only their recommendations are "
                        "public, not the measured 85th percentile speeds.",
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc))
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}: {len(features)} features")
    return 0


if __name__ == "__main__":
    sys.exit(main())

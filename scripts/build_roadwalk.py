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
from geo_util import iter_line_segments  # noqa: E402

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
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": sub},
                "properties": {
                    "kind": "line", "area": "western",
                    "segment": seg_name,
                    "source": "NCTA gap line clipped to the T07 segment range",
                },
            })
            west_pieces += 1
    print(f"Western road-walk line pieces: {west_pieces}")

    # --- Arrowhead road-walk line: surface == "road" features, whole
    ar_pieces = 0
    ar_miles = 0.0
    for feat in gap_a["features"]:
        props = feat.get("properties") or {}
        if props.get("surface") != "road":
            continue
        ar_miles += props.get("len_miles") or 0.0
        features.append({
            "type": "Feature",
            "geometry": feat.get("geometry"),
            "properties": {
                "kind": "line", "area": "arrowhead",
                "segment": "Arrowhead road walk",
                "source": "NCTA gap line, surface = road (the Mesabi "
                          "Trail bike path, surface = paved, is not road walk)",
            },
        })
        ar_pieces += 1
    print(f"Arrowhead road-walk line pieces: {ar_pieces} ({ar_miles:.1f} mi)")

    # --- speed badges: one per T07 segment, at the range midpoint
    # (Seg 14 is the exception: its midpoint falls in Frazee, but the
    # segment's expressway portion is the US-10 crossing at its west
    # end, so the badge sits at the crossing, chain mile 95.2.)
    for (seg, road, s, e, mph, wording, aadt) in T07_SEGMENTS:
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
                "position_note": note,
                "source": "T07 (MnDOT TCDS; Minn. Stat. \u00a7 169.14; "
                          "Otter Tail SAP, adopted May 26, 2026)",
            },
        })
    print(f"Speed badges: {len(T07_SEGMENTS)}")

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
                        "so the Arrowhead pieces carry the line only.",
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc))
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}: {len(features)} features")
    return 0


if __name__ == "__main__":
    sys.exit(main())

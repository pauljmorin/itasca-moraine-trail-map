#!/usr/bin/env python3
"""Build the Star of the North selection line from the official
NCTA Minnesota line.

The Star of the North Chapter's segment, per NCTA's own chapter
page (northcountrytrail.org/trail/minnesota/stn/, read Nov 18,
2026), is "from Minnesota 84 to Highway 6, northeast of Remer"
- about 30 miles of trail, maintained in partnership with the
U.S. Forest Service (Chippewa National Forest). The chapter's
spring-cleanup notice (northcountrytrail.org/events/stn-050425/)
calls it "the chapter's 30 miles of trail".

Why this script exists instead of filtering on the service's
`chapter` attribute: the official NCTA line
(site/data/trail-minnesota.geojson, pulled Nov 13 by
scripts/pull_minnesota_line.py) attributes only 2 features /
10.2 mi to STN. The rest of the same continuous trail between
MN-84 and MN-6 is attributed to ARW (23 features / 42.7 mi in
the lon -94.30..-93.60 window). The `chapter` attribute is
therefore NOT a usable extent source for Star of the North; the
chapter's own stated endpoints are. This script chains the
official-line features end-to-end (endpoint matching within
150 m) from the STN footpath's western end, and clips the chain
to the chapter's endpoints:

  * WEST: the MN-84 crossing north of Longville. MN-84 runs
    north from Longville (~-94.21 at lat 47.02; OSM "State
    Highway 84" northern terminus (-94.209, 46.981) + Longville
    at -94.207). The chain is clipped at lon -94.21 on the STN
    footpath (interpolated). [JUDGMENT J1: the crossing is
    placed by longitude, not measured against a road survey;
    the OSM road extract in the repo ends at lat 46.98 and the
    MnDOT centerlines service carries no usable route number
    for MN-84 here, so the crossing is good to ~0.3 mi. The
    3.87 mi of footpath west of the cut is Itasca Moraine
    territory per the chapter definition and is already covered
    by the chapter parcels (3 parcels within 3 m, verified
    Nov 18, 2026), so nothing is lost by the cut and no parcel
    is drawn twice.]
  * EAST: the MN-6 crossing northeast of Remer, where the
    footpath meets the Highway 6 road walk: the chain's eastern
    end (-93.847, 47.103), ~5 mi NE of Remer. East of here the
    trail is the 16.3-mi Hwy 6 road walk (Remer to Cohasset),
    which is Arrowhead reroute / Tioga Beach EA territory, NOT
    Star of the North, and is in NO viewer layer today (see
    SOURCES.md Road walk section). The chain ends exactly at
    the junction, so no clip is needed at the east end.

Result: 12 features, 30.59 mi unclipped / 26.67 mi clipped
(footpath 25.93 mi + 3 on-road connectors 0.74 mi), all in Cass
County (verified Nov 18, 2026 against the MnGeo county
boundaries service: only Cass intersects the slice bbox).
The on-road connectors (trail_stat "NCT (on-road)", trail_type
"Public Road") are kept in this file so the extent is complete,
but parcel selection (scripts/pull_parcels_stn.py) excludes
them: no parcel polygons along a road walk, per the standing
principle (Paul, Nov 18, 2026).

Output: data/segments/trail-stn.geojson (working data). The
published trail line itself needs no new file: the STN chunk
is already drawn by the "NCT — all Minnesota" layer
(site/data/trail-minnesota.geojson, weight 3.5 slate-blue,
strengthened Nov 18, 2026).

Usage:  python3 scripts/build_stn_line.py
No credentials required; input is the local official-line file.
"""

import json
import math
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MN_LINE = REPO_ROOT / "data" / "segments" / "official-line-minnesota.geojson"
OUT_PATH = REPO_ROOT / "data" / "segments" / "trail-stn.geojson"

# MN-84 crossing longitude (see module docstring, JUDGMENT J1).
MN84_LON = -94.21
# Chain tolerance: consecutive features must meet within this.
CHAIN_TOL_KM = 0.15

KM_PER_DEG_LAT = 111.195
KM_PER_DEG_LON = 75.93  # at 47 N


def haversine_miles(a, b):
    lat1, lon1 = math.radians(a[1]), math.radians(a[0])
    lat2, lon2 = math.radians(b[1]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(h)) * 0.621371


def line_length_miles(coords):
    return sum(haversine_miles(a, b)
               for a, b in zip(coords, coords[1:]))


def flatten(geom):
    if geom["type"] == "LineString":
        return [list(p) for p in geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        out = []
        for ring in geom["coordinates"]:
            out.extend(list(p) for p in ring)
        return out
    raise ValueError(f"unsupported geometry {geom['type']}")


def endpoints(coords):
    return tuple(coords[0]), tuple(coords[-1])


def dist_km(a, b):
    return math.hypot((a[0] - b[0]) * KM_PER_DEG_LON,
                      (a[1] - b[1]) * KM_PER_DEG_LAT)


def clip_west_at_lon(coords, lon):
    """Drop the part of a west-to-east coordinate list west of
    `lon`, interpolating the crossing point on the straddling
    segment. Returns (clipped_coords, cut_miles)."""
    cut = 0.0
    for i, (a, b) in enumerate(zip(coords, coords[1:])):
        if a[0] < lon <= b[0] or b[0] < lon <= a[0]:
            t = (lon - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0.0
            cross = [lon, a[1] + t * (b[1] - a[1])]
            cut = line_length_miles(coords[:i + 1]) + haversine_miles(a, cross)
            return [cross] + [list(p) for p in coords[i + 1:]], cut
    return [list(p) for p in coords], 0.0


def main():
    mn = json.loads(MN_LINE.read_text())
    feats = mn["features"]

    def cen(f):
        coords = flatten(f["geometry"])
        return (sum(p[0] for p in coords) / len(coords),
                sum(p[1] for p in coords) / len(coords))

    cands = [f for f in feats if -94.30 <= cen(f)[0] <= -93.84]
    print(f"Candidate middle-chunk features: {len(cands)}")

    # Chain west -> east from the westernmost feature (the STN
    # footpath), matching endpoints within CHAIN_TOL_KM.
    remaining = list(cands)
    start = min(remaining,
                key=lambda f: min(endpoints(flatten(f["geometry"]))[0][0],
                                  endpoints(flatten(f["geometry"]))[1][0]))
    chain = [(start, False)]  # (feature, reversed)
    remaining.remove(start)
    a0, b0 = endpoints(flatten(start["geometry"]))
    cur = b0 if a0[0] < b0[0] else a0
    while remaining:
        best = None
        for f in remaining:
            a, b = endpoints(flatten(f["geometry"]))
            for e in (a, b):
                d = dist_km(cur, e)
                if best is None or d < best[0]:
                    best = (d, f, e)
        if best and best[0] <= CHAIN_TOL_KM:
            d, f, e = best
            a, b = endpoints(flatten(f["geometry"]))
            chain.append((f, e == b))
            remaining.remove(f)
            cur = a if e == b else b
        else:
            print(f"CHAIN BREAK: nearest remaining feature "
                  f"{best[0]:.3f} km away: {best[1]['properties']}")
            return 1
    print(f"Chained features: {len(chain)}; unchained: {len(remaining)}")
    if remaining:
        for f in remaining:
            print(f"  LEFT OUT: {f['properties']}")
        return 1

    # Orient each feature west -> east and clip the first at MN-84.
    out_features = []
    total_miles = 0.0
    foot_miles = 0.0
    connector_miles = 0.0
    cut_miles = 0.0
    for i, (f, reversed_) in enumerate(chain):
        coords = flatten(f["geometry"])
        if reversed_:
            coords = coords[::-1]
        props = dict(f.get("properties") or {})
        role = ("connector" if props.get("trail_type") == "Public Road"
                or props.get("trail_stat") == "NCT (on-road)"
                else "foot")
        if i == 0:
            coords, cut_miles = clip_west_at_lon(coords, MN84_LON)
            props["len_miles_original"] = props.get("len_miles")
            props["clipped_west_at_lon"] = MN84_LON
            props["clipped_west_cut_miles"] = round(cut_miles, 2)
        miles = line_length_miles(coords)
        props["len_miles"] = round(miles, 2)
        props["slice_role"] = role
        props["stn_slice"] = True
        total_miles += miles
        if role == "foot":
            foot_miles += miles
        else:
            connector_miles += miles
        out_features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": props,
        })
    print(f"Clipped {cut_miles:.2f} mi west of MN-84 "
          f"(lon {MN84_LON}) off the first feature")
    print(f"STN line: {len(out_features)} features, "
          f"{total_miles:.2f} mi total ({foot_miles:.2f} mi foot path, "
          f"{connector_miles:.2f} mi on-road connectors)")

    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Star of the North selection line: the official "
                       "NCTA line chained west-to-east from the MN-84 "
                       "crossing north of Longville to the MN-6 crossing "
                       "northeast of Remer",
            "source": "NCTA 'North Country Trail (Public)' ArcGIS "
                      "feature service, Minnesota portion "
                      "(data/segments/official-line-minnesota.geojson, "
                      "pulled Nov 13, 2026 by "
                      "scripts/pull_minnesota_line.py)",
            "extent_definition": "NCTA Star of the North Chapter page "
                                 "(northcountrytrail.org/trail/minnesota/"
                                 "stn/): 'from Minnesota 84 to Highway 6, "
                                 "northeast of Remer'; ~30 miles of trail "
                                 "(chapter spring-cleanup notice). The "
                                 "service's `chapter` attribute is NOT "
                                 "used: it tags only 10.2 mi as STN and "
                                 "the rest of this same trail as ARW.",
            "pulled_utc_date": pulled,
            "method": (
                f"12 official-line features chained end-to-end "
                f"(endpoint match within {CHAIN_TOL_KM} km, no breaks); "
                f"west end clipped at lon {MN84_LON} (MN-84 crossing, "
                f"{cut_miles:.2f} mi cut off the STN footpath); east end "
                f"is the chain end where the footpath meets the "
                f"Highway 6 road walk (-93.847, 47.103). Counties: Cass "
                f"only (MnGeo county boundaries service, Nov 18, 2026). "
                f"On-road connectors (3 features, "
                f"{connector_miles:.2f} mi) are kept in this file but "
                f"excluded from parcel selection."
            ),
            "judgment": (
                "J1: MN-84 crossing placed at lon -94.21 from the OSM "
                "road line's northern terminus (-94.209, 46.981) and "
                "Longville (-94.207); good to ~0.3 mi. The 3.87 mi of "
                "footpath west of the cut is Itasca Moraine territory "
                "per the chapter definition and is already covered by "
                "the chapter parcels (3 parcels within 3 m, verified "
                "Nov 18, 2026), so the cut loses nothing and draws no "
                "parcel twice. Note the chapter's '30 miles of trail' "
                "counts the full 30.59-mi chain from the Itasca "
                "Moraine boundary; the clipped STN line is 26.67 mi."
            ),
            "feature_count": len(out_features),
            "total_miles": round(total_miles, 2),
            "foot_miles": round(foot_miles, 2),
            "connector_miles": round(connector_miles, 2),
            "composition_by_service_chapter": {
                "STN": sum(1 for f in out_features
                           if f["properties"].get("chapter") == "STN"),
                "ARW": sum(1 for f in out_features
                           if f["properties"].get("chapter") == "ARW"),
            },
        },
        "features": out_features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc))
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}: "
          f"{len(out_features)} features")
    return 0


if __name__ == "__main__":
    sys.exit(main())

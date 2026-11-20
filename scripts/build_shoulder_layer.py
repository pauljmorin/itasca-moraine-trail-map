#!/usr/bin/env python3
"""Build the shoulder-width viewer layer from the merged measurement sheet.

Reads:
  ~/workspace/goals/finish-the-north-country-trail-in-minnesota/analysis/
    shoulder-rollout-measurements-merged.csv   (143 points, 142 with coords)
  site/data/roadwalk.geojson                  (61 road-walk line pieces)

Writes:
  site/data/shoulder-points.geojson    one Point per measured point (142)
  site/data/shoulder-segments.geojson  roadwalk lines split at the measured
                                       points; each stretch coloured by the
                                       class of the mile it starts in

Rules (Paul, Nov 20, 2026): a stretch from point i to point i+1 takes
point i's class — each point stands for the mile that starts at it.
The head of a piece before its first point takes the class of the
preceding point in mile order within the same segment group (the mile
that stretch belongs to); a piece with no points takes the class of
the nearest point in its group. Classes: below / marginal / meets / grass /
unmeasurable / curbed / no-frame / skipped (skipped point 119 has no
coordinates and gets no dot; its stretch is covered by the preceding
point's class).

Geometry: points are projected onto the roadwalk lines in EPSG:26915
(UTM 15N); every measured point sits within ~1 m of its line.
"""
import csv
import json
import sys
from collections import Counter, defaultdict

from shapely.geometry import LineString, Point, shape, mapping
from shapely.ops import transform as shp_transform
from pyproj import Transformer

ANALYSIS = "/home/hatch/workspace/goals/finish-the-north-country-trail-in-minnesota/analysis"
REPO = "/home/hatch/workspace/itasca-trail-map"

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:26915", always_xy=True)
TO_LONLAT = Transformer.from_crs("EPSG:26915", "EPSG:4326", always_xy=True)

CLASS_COLOR = {
    "below": "#c0392b",        # red — under the 4-ft FHWA benchmark
    "marginal": "#d4a017",      # amber — range straddles 4 ft
    "meets": "#1e8449",         # green — at or above 4 ft
    "grass": "#7fb069",         # sage green — walkable grass verge, no paved shoulder (Paul, Nov 20, 2026)
    "unmeasurable": "#7f8c8d",  # grey
    "curbed": "#5d6d7e",        # blue-grey — curbed city street
    "no-frame": "#b0b0b0",      # light grey hollow dot
    "skipped": "#b0b0b0",
}


def group_of(seg):
    if seg.startswith("STN-"):
        return "Star of the North road walk"
    if seg.startswith("A-"):
        return "Arrowhead road walk"
    if seg == "H6":
        return "Highway 6 road walk"
    if seg.startswith("S"):
        return "Seg " + str(int(seg[1:]))
    raise ValueError("unknown seg " + seg)


def to_utm(geom):
    return shp_transform(lambda x, y: TO_UTM.transform(x, y), geom)


def to_lonlat(geom):
    return shp_transform(lambda x, y: TO_LONLAT.transform(x, y), geom)


def main():
    rows = list(csv.DictReader(open(f"{ANALYSIS}/shoulder-rollout-measurements-merged.csv")))
    pts = [r for r in rows if r["lat"] and r["lon"]]
    print(f"points with coords: {len(pts)} of {len(rows)} "
          f"(missing: {[r['point'] for r in rows if not r['lat']]})")

    rw = json.load(open(f"{REPO}/site/data/roadwalk.geojson"))
    lines = [f for f in rw["features"] if f["geometry"]["type"] == "LineString"]
    print(f"roadwalk line pieces: {len(lines)}")

    # UTM copies for metric projection.
    line_utm = []
    for f in lines:
        g = to_utm(shape(f["geometry"]))
        line_utm.append((f, g))

    # Assign each point to its nearest line piece within its segment group.
    by_group = defaultdict(list)   # group -> [(mi, point_row)]
    for r in pts:
        by_group[group_of(r["seg"])].append(r)
    for g in by_group:
        by_group[g].sort(key=lambda r: float(r["mi"]))

    assigned = defaultdict(list)   # piece index -> [(s_along_m, row)]
    unassigned = []
    max_dist = 0.0
    for r in pts:
        p = to_utm(Point(float(r["lon"]), float(r["lat"])))
        grp = group_of(r["seg"])
        best = (1e18, None, None)
        for i, (f, g) in enumerate(line_utm):
            if f["properties"].get("segment") != grp:
                continue
            d = g.distance(p)
            if d < best[0]:
                best = (d, i, g.project(p))
        if best[1] is None or best[0] > 40:
            unassigned.append((r["point"], r["seg"], best[0]))
            continue
        max_dist = max(max_dist, best[0])
        assigned[best[1]].append((best[2], r))
    print(f"max point-to-line distance: {max_dist:.1f} m; "
          f"unassigned: {unassigned}")
    if unassigned:
        print("ERROR: points with no line within 40 m", file=sys.stderr)
        sys.exit(1)

    empty_pieces = [i for i in range(len(lines)) if i not in assigned]
    print(f"pieces with no assigned point: {len(empty_pieces)} "
          f"{[lines[i]['properties'].get('segment') + '/' + (lines[i]['properties'].get('road') or '')[:30] for i in empty_pieces]}")

    # ---- points GeoJSON ----
    point_features = []
    for r in pts:
        props = {
            "point": int(r["point"]),
            "seg": r["seg"],
            "mi": float(r["mi"]),
            "imagery": r["imagery"] or None,
            "paved_ft": r["paved_ft"] or None,
            "gravel_ft": r["gravel_ft"] or None,
            "grass_ft": r["grass_ft"] or None,
            "grass_flatness": r["grass_flatness"] or None,
            "beyond_gravel": r["beyond_gravel"] or None,
            "sidewalk": r["sidewalk"] or None,
            "class": r["class"],
            "status": r["status"],
            "heading": int(r["heading"]) if r["heading"] else None,
            "notes": r["notes"] or None,
        }
        point_features.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(r["lon"]), float(r["lat"])]},
            "properties": props,
        })
    with open(f"{REPO}/site/data/shoulder-points.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": point_features}, f)
    print(f"shoulder-points.geojson: {len(point_features)} features; "
          f"classes {dict(Counter(p['properties']['class'] for p in point_features))}")

    # ---- segments GeoJSON ----
    seg_features = []
    for i, (f, g) in enumerate(line_utm):
        L = g.length
        grp = f["properties"].get("segment")
        cuts = sorted(assigned.get(i, []))  # [(s, row)]
        # class of the point preceding this piece's first cut, in mile order
        prev_class = None
        if cuts:
            first_mi = float(cuts[0][1]["mi"])
            earlier = [r for r in by_group[grp] if float(r["mi"]) < first_mi]
            if earlier:
                prev_class = earlier[-1]["class"]
            else:
                prev_class = cuts[0][1]["class"]
        elif grp in by_group:
            # no points on this piece: nearest point in the group by
            # distance to the piece midpoint
            mid = g.interpolate(0.5, normalized=True)
            cand = min(by_group[grp],
                       key=lambda r: to_utm(Point(float(r["lon"]), float(r["lat"]))).distance(mid))
            prev_class = cand["class"]
        else:
            prev_class = "unmeasurable"
        # boundaries: 0, each cut s, L — deduped within 1 m
        bounds = [0.0]
        for s, _ in cuts:
            if s - bounds[-1] > 1.0 and L - s > 1.0:
                bounds.append(s)
        if L - bounds[-1] > 1.0:
            bounds.append(L)
        else:
            bounds[-1] = L
        # class per boundary: the cut point's class at a cut, prev_class at 0
        cut_at = {}
        for s, r in cuts:
            cut_at[round(s, 1)] = r["class"]
        for a, b in zip(bounds, bounds[1:]):
            if b - a < 1.0:
                continue
            cls = cut_at.get(round(a, 1), prev_class)
            # split the UTM line between a and b, then back to lon/lat
            from shapely.ops import substring
            part_utm = substring(g, a, b)
            part = to_lonlat(part_utm)
            coords = [list(c) for c in part.coords]
            # starting point's row (for from_point / from_mi)
            start_row = None
            for s, r in cuts:
                if abs(s - a) < 1.5:
                    start_row = r
                    break
            seg_features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "class": cls,
                    "seg": grp,
                    "road": f["properties"].get("road"),
                    "area": f["properties"].get("area"),
                    "from_point": int(start_row["point"]) if start_row else None,
                    "from_mi": float(start_row["mi"]) if start_row else None,
                    "length_mi": round((b - a) / 1609.344, 2),
                },
            })
    with open(f"{REPO}/site/data/shoulder-segments.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": seg_features}, f)
    print(f"shoulder-segments.geojson: {len(seg_features)} features; "
          f"classes {dict(Counter(s['properties']['class'] for s in seg_features))}")
    total_mi = sum(s["properties"]["length_mi"] for s in seg_features)
    print(f"total segment length: {total_mi:.1f} mi")
    # sanity: roadwalk total length
    rw_mi = sum(g.length for _, g in line_utm) / 1609.344
    print(f"roadwalk line total: {rw_mi:.1f} mi")


if __name__ == "__main__":
    main()

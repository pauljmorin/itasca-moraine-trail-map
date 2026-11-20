#!/usr/bin/env python3
"""Build the shoulder-width viewer layer from the merged measurement sheet.

Reads:
  ~/workspace/goals/finish-the-north-country-trail-in-minnesota/analysis/
    shoulder-rollout-measurements-merged.csv   (143 points, 142 with coords)
  site/data/roadwalk.geojson                  (61 road-walk line pieces)

Writes:
  site/data/shoulder-points.geojson    one Point per measured point (142)
  site/data/shoulder-segments.geojson  roadwalk lines split at the
                                       midpoints between measured points;
                                       each stretch is the mile centred on
                                       its point, half a mile either side

Rules (Paul, Nov 20, 2026 — correction to the first build): the Street
View photo was taken AT the point, so the measured quality describes
the road around that point. A stretch runs from the midpoint between
the point and the previous point to the midpoint between the point and
the next point, measured along the road in the run's mile values (the
`mi` column, which is the along-road mile within the point's run).
The first point's stretch starts at the run's first piece; the last
point's stretch ends at its last piece. Every stretch takes the class
of the point it is centred on. A run is one `seg` value from the
sheet (S01–S15, H6, A-GR, A-CR61, A-135, A-FERN, STN-MN200,
STN-Tobique, STN-Milton — 23 runs); the road-walk pieces are the
lines of that run's segment group, ordered by their mile intervals.
A stretch that spans several pieces is emitted as one feature per
piece-part, all carrying the centred point's number. Pieces with no
point of their own are split at the midpoint between their
neighbouring points where one falls inside them, and otherwise lie
whole inside one point's centred mile. Point 119 (skipped, no
coordinates) has no dot; the road at its mile takes the preceding
point's class, as its centred stretch covers it.

Geometry: points are projected onto the roadwalk lines in EPSG:26915
(UTM 15N); every measured point sits within ~1 m of its line. A
piece's mile interval is fixed by its points (mile rises or falls
with s along the piece — five pieces run reversed); pieces tile
their run's mile axis, the only gaps being the no-point pieces
themselves. Speed: each point carries speed_mph + speed_text from
the roadwalk piece it was assigned to (nearest line in its group);
Seg 12 pieces carry no speed, so Seg 12 points get neither field.
Classes: below / marginal / meets / grass / unmeasurable / curbed /
no-frame / skipped (skipped point 119 has no coordinates and gets no
dot).
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
MI = 1609.344

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

    # Speed join (Paul, Nov 20, 2026): each point takes speed_mph +
    # speed_text from the roadwalk line piece it was assigned to
    # (nearest line in its segment group). Pieces with no speed
    # (Seg 12 — badge removed Nov 19, no reconciled figure) leave
    # both fields null and the popup omits the row.
    point_piece = {}
    for i, cuts in assigned.items():
        for s, r in cuts:
            point_piece[int(r["point"])] = line_utm[i][0]

    # ---- points GeoJSON ----
    point_features = []
    for r in pts:
        piece_props = {}
        piece = point_piece.get(int(r["point"]))
        if piece is not None:
            piece_props = piece.get("properties", {})
        props = {
            "point": int(r["point"]),
            "seg": r["seg"],
            "mi": float(r["mi"]),
            "imagery": r["imagery"] or None,
            "paved_ft": r["paved_ft"] or None,
            "gravel_ft": r["gravel_ft"] or None,
            "grass_ft": r["grass_ft"] or None,
            "grass_flatness": r["grass_flatness"] or None,
            "speed_mph": piece_props.get("speed_mph") or None,
            "speed_text": piece_props.get("speed_text") or None,
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

    # ---- segments GeoJSON: centred on the points ----
    # Runs: one seg value from the sheet (23 runs). Points sorted by mi.
    by_run = defaultdict(list)
    for r in pts:
        by_run[r["seg"]].append(r)
    for run in by_run:
        by_run[run].sort(key=lambda r: float(r["mi"]))

    # Points per piece, sorted by s along the piece.
    bypiece = defaultdict(list)   # piece index -> [(s, mi, point, run, class)]
    for i, cuts in assigned.items():
        for s, r in cuts:
            bypiece[i].append((s, float(r["mi"]), int(r["point"]),
                               r["seg"], r["class"]))
    for i in bypiece:
        bypiece[i].sort()

    # Direction of mile along each piece: +1 if mi rises with s, -1 if
    # it falls. Multi-point pieces read it off their points; a
    # single-point piece reads it off the neighbour it chains to
    # (endpoint within 10 m), else +1 (the tiling check below
    # validates the choice).
    ends = {}
    for i, (f, g) in enumerate(line_utm):
        c = list(g.coords)
        ends[i] = (Point(c[0]), Point(c[-1]))

    def down_end(i, direction):
        return ends[i][1] if direction.get(i, 1) == 1 else ends[i][0]

    def up_end(i, direction):
        return ends[i][0] if direction.get(i, 1) == 1 else ends[i][1]

    direction = {}
    for i, lst in bypiece.items():
        if len(lst) >= 2:
            direction[i] = 1 if lst[-1][1] > lst[0][1] else -1
    run_pieces = defaultdict(list)
    for i in bypiece:
        run_pieces[bypiece[i][0][3]].append(i)
    fallback_dirs = []
    for run in sorted(run_pieces):
        order = sorted(run_pieces[run],
                       key=lambda i: min(x[1] for x in bypiece[i]))
        for pos, i in enumerate(order):
            if i in direction:
                continue
            resolved = None
            prev_i = order[pos - 1] if pos > 0 else None
            next_i = order[pos + 1] if pos + 1 < len(order) else None
            if prev_i is not None and prev_i in direction:
                ds = ends[i][0].distance(down_end(prev_i, direction))
                de = ends[i][1].distance(down_end(prev_i, direction))
                if min(ds, de) < 10:
                    resolved = 1 if ds < de else -1
            if resolved is None and next_i is not None and next_i in direction:
                ds = ends[i][0].distance(up_end(next_i, direction))
                de = ends[i][1].distance(up_end(next_i, direction))
                if min(ds, de) < 10:
                    resolved = -1 if ds < de else 1
            if resolved is None:
                fallback_dirs.append((run, i))
                resolved = 1
            direction[i] = resolved
    if fallback_dirs:
        print(f"direction fallback (+1) for single-point pieces: {fallback_dirs}")

    # A piece's mile interval, from its points: mi(s) = mi0 +
    # dir * (s - s0) / MI.
    def piece_interval(i):
        lst = bypiece[i]
        L = line_utm[i][1].length
        d = direction[i]
        s0, mi0 = lst[0][0], lst[0][1]
        a = mi0 + d * (0 - s0) / MI
        b = mi0 + d * (L - s0) / MI
        return (min(a, b), max(a, b))

    # Order the pieces of each run by interval start; insert the
    # no-point pieces where they belong. A no-point piece fills the
    # mile gap between its neighbours: for each run, the interior
    # gaps between consecutive with-points pieces (point-derived
    # intervals) are matched against subsets of the group's
    # no-point pieces, best length fit first (a subset fills a gap
    # when |sum(lengths) - gap| < 0.05 mi; ties break toward more
    # pieces, then toward the subset that touches the gap's ends).
    # Pieces that fill no gap belong at a run end and are placed by
    # endpoint chaining (Pines St after the last A-135 piece,
    # Fernberg after the A-FERN piece, and the Fergus Falls /
    # S08 / S10 / S11 / S14 stubs). Within a gap, pieces are
    # ordered by chaining from the upstream neighbour. Direction
    # of each placed piece follows its chaining.
    from itertools import combinations

    group_runs = defaultdict(list)
    for run in run_pieces:
        group_runs[group_of(run)].append(run)
    run_order = {}
    for run in run_pieces:
        run_order[run] = sorted(run_pieces[run],
                                key=lambda i: piece_interval(i)[0])

    def piece_len_mi(i):
        return line_utm[i][1].length / MI

    def end_dist(i, pt):
        return min(ends[i][0].distance(pt), ends[i][1].distance(pt))

    # interior gaps per run, keyed by the with-points pieces either
    # side; only positive gaps > 0.02 mi (the ~0.01 overlaps are mi
    # noise, not road)
    gaps = {}
    for run, order in run_order.items():
        ivs = [piece_interval(i) for i in order]
        for k in range(len(order) - 1):
            g = ivs[k + 1][0] - ivs[k][1]
            if g > 0.02:
                gaps[(run, order[k], order[k + 1])] = g

    unassigned = set(empty_pieces)
    used_gaps = set()
    while True:
        best = None
        for (run, prev, nxt), g in gaps.items():
            if (run, prev, nxt) in used_gaps:
                continue
            up = down_end(prev, direction)
            dn = up_end(nxt, direction)
            grp_pieces = [i for i in unassigned
                          if lines[i]["properties"].get("segment")
                          == group_of(run)]
            for n in range(1, len(grp_pieces) + 1):
                for sub in combinations(grp_pieces, n):
                    tot = sum(piece_len_mi(i) for i in sub)
                    fit = abs(tot - g)
                    if fit >= 0.05:
                        continue
                    touch = min(min(end_dist(i, up), end_dist(i, dn))
                                for i in sub) / MI
                    # Endpoint proximity dominates: a piece that
                    # touches the gap's ends belongs there, however
                    # well a far-away piece's length happens to fit
                    # (the fit differences are within mi noise).
                    # Within a touch bucket the length fit decides,
                    # then more pieces, then the exact touch.
                    key = (round(touch / 0.5), round(fit / 0.02),
                           -n, touch)
                    if best is None or key < best[0]:
                        best = (key, (run, prev, nxt), sub)
        if best is None:
            break
        key, (run, prev, nxt), sub = best
        used_gaps.add((run, prev, nxt))
        cur = down_end(prev, direction)
        remaining = list(sub)
        chained = []
        while remaining:
            nxt_p = min(remaining,
                        key=lambda i: min(ends[i][0].distance(cur),
                                          ends[i][1].distance(cur)))
            remaining.remove(nxt_p)
            d0 = ends[nxt_p][0].distance(cur)
            d1 = ends[nxt_p][1].distance(cur)
            direction[nxt_p] = 1 if d0 <= d1 else -1
            chained.append(nxt_p)
            cur = (ends[nxt_p][1] if direction[nxt_p] == 1
                   else ends[nxt_p][0])
        pos = run_order[run].index(prev) + 1
        run_order[run][pos:pos] = chained
        for i in chained:
            unassigned.discard(i)
    for (run, prev, nxt), g in gaps.items():
        if (run, prev, nxt) not in used_gaps:
            print(f"WARNING: gap {g:.2f} mi in {run} between pieces "
                  f"{prev} and {nxt} left unfilled", file=sys.stderr)

    # remaining pieces go to run ends, most-confident chaining first
    while unassigned:
        best = None
        for i in sorted(unassigned):
            grp = lines[i]["properties"].get("segment")
            for run in group_runs.get(grp, []):
                order = run_order[run]
                d_before = end_dist(i, up_end(order[0], direction))
                d_after = end_dist(i, down_end(order[-1], direction))
                for pos, d in ((0, d_before), (len(order), d_after)):
                    if best is None or d < best[0]:
                        best = (d, i, run, pos)
        d, i, run, pos = best
        if d > 1000:
            print(f"WARNING: no-point piece {i} ({lines[i]['properties'].get('road')}) "
                  f"placed at {run} end {d:.0f} m from the chain",
                  file=sys.stderr)
        order = run_order[run]
        facing = (up_end(order[0], direction) if pos == 0
                  else down_end(order[-1], direction))
        d0 = ends[i][0].distance(facing)
        d1 = ends[i][1].distance(facing)
        if pos == len(order):
            # after the last piece: upstream end faces the run
            direction[i] = 1 if d0 <= d1 else -1
        else:
            # before the first piece: downstream end faces the run
            direction[i] = 1 if d1 <= d0 else -1
        order.insert(pos, i)
        unassigned.discard(i)
    print("no-point pieces placed: "
          + ", ".join(f"{run}:{','.join(str(p) for p in order if p in empty_pieces) or '-'}"
                      for run, order in sorted(run_order.items())
                      if any(p in empty_pieces for p in order)))

    # Cumulative mile intervals per run, anchored on the first piece
    # with points (its interval comes from its points) and walked
    # forward/backward by piece length. The intervals tile the run's
    # mile axis; the only gaps the anchor intervals leave are the
    # no-point pieces, which the walk fills.
    run_bounds = {}   # run -> [(piece, start_mi, end_mi)] in run order
    for run, order in run_order.items():
        iv = {i: piece_interval(i) for i in run_pieces[run]}
        anchor = next(i for i in order if i in iv)
        res = {}
        idx = order.index(anchor)
        cur = iv[anchor][0]
        for j in range(idx - 1, -1, -1):
            L = line_utm[order[j]][1].length / MI
            res[order[j]] = (cur - L, cur)
            cur -= L
        cur = iv[anchor][1]
        res[anchor] = iv[anchor]
        for j in range(idx + 1, len(order)):
            L = line_utm[order[j]][1].length / MI
            res[order[j]] = (cur, cur + L)
            cur += L
        run_bounds[run] = [(i, res[i][0], res[i][1]) for i in order]

    # Axis checks. (a) Each with-points piece's cumulative interval
    # start must match its point-derived interval start within
    # 0.05 mi — a larger discrepancy means a no-point piece was
    # placed on the wrong side of it. (b) Each point's mile must
    # lie within its own piece's cumulative interval (±0.02 mi),
    # and where locate() maps it onto its own piece the mapped s
    # must match its projected s within 100 m. The sheet's miles
    # carry ~0.5% scale drift against the drawn geometry (worst
    # 68 m at S04 pt 27), so the s tolerance is 100 m, not 20 m;
    # a point at a piece boundary may locate onto the adjacent
    # piece, which check (b) allows when its mile sits on the
    # shared boundary.
    tile_problems = []
    max_axis_err = 0.0
    for run, order in run_order.items():
        bounds = {i: (a, b) for i, a, b in run_bounds[run]}
        for i in run_pieces[run]:
            a_cum = bounds[i][0]
            a_own = piece_interval(i)[0]
            err = abs(a_cum - a_own)
            max_axis_err = max(max_axis_err, err)
            if err > 0.05:
                tile_problems.append(
                    f"{run} piece {i}: cumulative interval starts "
                    f"{a_cum:.2f}, point-derived starts {a_own:.2f} "
                    f"(err {err:.2f} mi)")
    # Locate a road-mile in a run: returns (piece, s_along_piece_m) or
    # None. s is computed from (m - piece_start_mi) in the piece's
    # direction, clamped to [0, L].
    def locate(run, m):
        for (i, a, b) in run_bounds[run]:
            if a - 1e-9 <= m <= b + 1e-9:
                d = direction.get(i, 1)
                s = (m - a) * MI if d == 1 else (b - m) * MI
                return (i, max(0.0, min(line_utm[i][1].length, s)))
        return None

    max_s_err = 0.0
    for r in pts:
        run = r["seg"]
        mi = float(r["mi"])
        i, s = None, None
        # the point's assigned piece and projected s
        for pi, cuts in assigned.items():
            for (ss, rr) in cuts:
                if rr is r:
                    i, s = pi, ss
        a, b = {p: (x, y) for p, x, y in run_bounds[run]}[i]
        if not (a - 0.02 <= mi <= b + 0.02):
            tile_problems.append(
                f"point {r['point']} ({run} mi {mi}): mile outside "
                f"its piece {i} cumulative interval [{a:.2f}, {b:.2f}]")
            continue
        got = locate(run, min(max(mi, run_bounds[run][0][1]),
                              run_bounds[run][-1][2]))
        if got is None:
            tile_problems.append(
                f"point {r['point']} ({run} mi {mi}): mile locates "
                f"nowhere in the run")
        elif got[0] == i:
            err = abs(got[1] - s)
            max_s_err = max(max_s_err, err)
            if err > 100.0:
                tile_problems.append(
                    f"point {r['point']} ({run} mi {mi}): mapped s "
                    f"{got[1]:.0f}, projected s {s:.0f} (err {err:.0f} m)")
    if tile_problems:
        print("AXIS PROBLEMS:", file=sys.stderr)
        for t in tile_problems:
            print("  " + t, file=sys.stderr)
        sys.exit(1)
    print(f"axis checks passed: max interval-start error "
          f"{max_axis_err:.3f} mi; max point s error {max_s_err:.0f} m")

    # ---- build the centred stretches ----
    from shapely.ops import substring
    seg_features = []
    for run in sorted(by_run):
        order = [p for p, _, _ in run_bounds[run]]
        order_idx = {p: n for n, p in enumerate(order)}
        pts_run = [(float(r["mi"]), int(r["point"]), r["class"])
                   for r in by_run[run]]
        bounds_mi = [run_bounds[run][0][1]]
        for a, b in zip(pts_run, pts_run[1:]):
            bounds_mi.append((a[0] + b[0]) / 2)
        bounds_mi.append(run_bounds[run][-1][2])
        for k, (pmi, pn, cls) in enumerate(pts_run):
            a_mi, b_mi = bounds_mi[k], bounds_mi[k + 1]
            la, lb = locate(run, a_mi), locate(run, b_mi)
            if la is None or lb is None:
                print(f"ERROR: boundary {a_mi:.2f} or {b_mi:.2f} of "
                      f"point {pn} ({run}) falls outside the run",
                      file=sys.stderr)
                sys.exit(1)
            ia, ib = la[0], lb[0]
            for n in range(order_idx[ia], order_idx[ib] + 1):
                p = order[n]
                dd = direction.get(p, 1)
                Lp = line_utm[p][1].length
                s_from = la[1] if p == ia else (0.0 if dd == 1 else Lp)
                s_to = lb[1] if p == ib else (Lp if dd == 1 else 0.0)
                lo, hi = min(s_from, s_to), max(s_from, s_to)
                if hi - lo < 1.0:
                    continue
                part_utm = substring(line_utm[p][1], lo, hi)
                part = to_lonlat(part_utm)
                coords = [list(c) for c in part.coords]
                f = line_utm[p][0]
                seg_features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "class": cls,
                        "seg": f["properties"].get("segment"),
                        "road": f["properties"].get("road"),
                        "area": f["properties"].get("area"),
                        "from_point": pn,
                        "from_mi": pmi,
                        "length_mi": round((hi - lo) / MI, 2),
                    },
                })
    with open(f"{REPO}/site/data/shoulder-segments.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": seg_features}, f)
    print(f"shoulder-segments.geojson: {len(seg_features)} features; "
          f"classes {dict(Counter(s['properties']['class'] for s in seg_features))}")
    total_mi = sum(s["properties"]["length_mi"] for s in seg_features)
    print(f"total segment length: {total_mi:.1f} mi")
    # sanity: roadwalk total length
    rw_mi = sum(g.length for _, g in line_utm) / MI
    print(f"roadwalk line total: {rw_mi:.1f} mi")
    print(f"coverage check: total {total_mi:.2f} mi vs roadwalk "
          f"{rw_mi:.2f} mi (difference {rw_mi - total_mi:+.2f} mi; "
          f"the <1 m slivers dropped at piece ends account for it)")


if __name__ == "__main__":
    main()

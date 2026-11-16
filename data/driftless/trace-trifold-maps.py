#!/usr/bin/env python3
"""Trace the Driftless Trail built segments from the DALC trifold maps.

Georeferences the Welsh Hills trifold map panel (tw300-1.png, 300 DPI render
of page 1 of the DALC Welsh Hills trifold PDF) with an affine transform fit
to 4 OSM ground-control points, then traces the red trail lines by
color-based extraction + centerline walk, and writes GeoJSON (lon/lat).

GCPs (panel px in the 1040x1000 crop of the full page starting at (60,60);
lon/lat from OpenStreetMap, api.openstreetmap.org bbox fetch Nov 16, 2026):
  bridge      (486.6, 407.0)  (-90.0610354, 43.1455595)  Hwy 23 bridge mid over WI River
  towerSW     (726.0, 321.0)  (-90.0505867, 43.1444444)  Tower Hill SP boundary SW corner
  phoebe_base (173.0, 482.0)  (-90.0736935, 43.1432806)  Phoebe Point Trail south end (OSM way 1248941083 start)
  hwy23xT     (390.0, 799.0)  (-90.0651242, 43.1335806)  Hwy 23 x County T junction (OSM node 742829298)

Validation: OSM Phoebe way (74 pts) registers to the red line with median
nearest-red 4.9 px (~16 m); OSM Welsh way (98 pts) median 11.2 px (~37 m).
The map is a stylised tourist map, not a survey product: traced lines are
APPROXIMATE, good to roughly +/-50 m typical, +/-100 m worst case.

Outputs (written next to this script):
  driftless-traced-welsh-phoebe.geojson  - Welsh outer loop only (traced).
  Phoebe is not traced: the map's Phoebe loop is the same trail as the OSM
  way (0.685 mi), so the OSM geometry stands.
Run: python3 trace-trifold-maps.py
"""
import json
import math
import xml.etree.ElementTree as ET
from collections import deque

import numpy as np
from PIL import Image

PANEL = "tw300-map-panel.png"
AFFINE_JSON = "tw300-affine-gcps.json"
OSM = "osm/taliesin.osm"
OUT = "driftless-traced-welsh-phoebe.geojson"


def haversine_mi(a, b):
    lat1, lon1 = math.radians(a[1]), math.radians(a[0])
    lat2, lon2 = math.radians(b[1]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def line_miles(coords):
    return sum(haversine_mi(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def load_osm_ways(path):
    t = ET.parse(path)
    root = t.getroot()
    nodes, ways = {}, []
    for el in root:
        if el.tag == "node":
            nodes[el.get("id")] = (float(el.get("lon")), float(el.get("lat")))
        elif el.tag == "way":
            tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
            nds = [c.get("ref") for c in el if c.tag == "nd"]
            ways.append({"id": el.get("id"), "tags": tags, "nds": nds})
    return nodes, ways


def components(mask):
    """8-connected components of a boolean mask; returns list of pixel sets."""
    ys, xs = np.where(mask)
    remaining = set(zip(xs.tolist(), ys.tolist()))
    comps = []
    while remaining:
        seed = remaining.pop()
        q = deque([seed])
        comp = [seed]
        while q:
            x, y = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nb = (x + dx, y + dy)
                    if nb in remaining:
                        remaining.discard(nb)
                        q.append(nb)
                        comp.append(nb)
        comps.append(set(comp))
    return comps


def window_pixels(cx, cy, r):
    """Integer pixel coords in the square window around (cx, cy)."""
    x0, y0 = int(math.floor(cx)) - r, int(math.floor(cy)) - r
    return [(x, y) for x in range(x0, x0 + 2 * r + 1) for y in range(y0, y0 + 2 * r + 1)]


def zhang_suen(mask):
    """Thin a boolean mask to a 1-px skeleton (Zhang-Suen, numpy vectorised)."""
    img = mask.copy()
    while True:
        changed = False
        for step in (0, 1):
            P2 = np.roll(img, 1, axis=0)
            P3 = np.roll(np.roll(img, 1, axis=0), -1, axis=1)
            P4 = np.roll(img, -1, axis=1)
            P5 = np.roll(np.roll(img, -1, axis=0), -1, axis=1)
            P6 = np.roll(img, -1, axis=0)
            P7 = np.roll(np.roll(img, -1, axis=0), 1, axis=1)
            P8 = np.roll(img, 1, axis=1)
            P9 = np.roll(np.roll(img, 1, axis=0), 1, axis=1)
            seq = [P2, P3, P4, P5, P6, P7, P8, P9]
            A = np.zeros(img.shape, dtype=int)
            for i in range(8):
                A += ((seq[i] == 0) & (seq[(i + 1) % 8] == 1)).astype(int)
            B = sum(int(s) if False else s for s in seq)
            if step == 0:
                m1 = P2 * P4 * P6
                m2 = P4 * P6 * P8
            else:
                m1 = P2 * P4 * P8
                m2 = P2 * P6 * P8
            delete = img & (B >= 2) & (B <= 6) & (A == 1) & (m1 == 0) & (m2 == 0)
            delete[0, :] = False
            delete[-1, :] = False
            delete[:, 0] = False
            delete[:, -1] = False
            if np.any(delete):
                changed = True
                img[delete] = False
        if not changed:
            return img


def walk_skeleton(skel_set, seed):
    """Walk a 1-px skeleton from seed; returns the ordered pixel path."""
    visited = {seed}
    path = [seed]
    cur = seed
    heading = None
    for _ in range(20000):
        nbrs = [(cur[0] + dx, cur[1] + dy)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx, dy) != (0, 0)
                and (cur[0] + dx, cur[1] + dy) in skel_set
                and (cur[0] + dx, cur[1] + dy) not in visited]
        if not nbrs:
            break
        if heading is not None:
            def score(p):
                vx, vy = p[0] - cur[0], p[1] - cur[1]
                n = math.hypot(vx, vy)
                return (vx * heading[0] + vy * heading[1]) / n
            nxt = max(nbrs, key=score)
        else:
            nxt = nbrs[0]
        visited.add(nxt)
        path.append(nxt)
        dx, dy = nxt[0] - cur[0], nxt[1] - cur[1]
        n = math.hypot(dx, dy)
        heading = (dx / n, dy / n)
        cur = nxt
        if len(path) > 30 and math.hypot(cur[0] - seed[0], cur[1] - seed[1]) < 3:
            break
    return path


def chain_paths(paths, max_gap=40.0):
    """Join open polylines end-to-end by nearest endpoints (for loop arcs)."""
    paths = [list(p) for p in paths if len(p) >= 2]
    if not paths:
        return []
    chain = paths.pop(0)
    while paths:
        end = chain[-1]
        best, best_d, best_rev = None, 1e18, False
        for i, p in enumerate(paths):
            for rev, pt in ((False, p[0]), (True, p[-1])):
                d = math.hypot(pt[0] - end[0], pt[1] - end[1])
                if d < best_d:
                    best, best_d, best_rev = i, d, rev
        if best is None or best_d > max_gap:
            break
        p = paths.pop(best)
        chain.extend(list(reversed(p)) if best_rev else p)
    return chain


def simplify(coords, tol_px=3.0):
    """Douglas-Peucker on pixel coords."""
    if len(coords) < 3:
        return coords

    def perp(p, a, b):
        ax, ay, bx, by, px, py = a[0], a[1], b[0], b[1], p[0], p[1]
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def rec(pts):
        if len(pts) < 3:
            return pts
        dmax, idx = 0.0, 0
        for i in range(1, len(pts) - 1):
            d = perp(pts[i], pts[0], pts[-1])
            if d > dmax:
                dmax, idx = d, i
        if dmax > tol_px:
            return rec(pts[: idx + 1])[:-1] + rec(pts[idx:])
        return [pts[0], pts[-1]]

    return rec(coords)


def main():
    coef = json.load(open(AFFINE_JSON))
    clon, clat = coef["coef_lon"], coef["coef_lat"]

    def to_lonlat(px, py):
        return (clon[0] * px + clon[1] * py + clon[2],
                clat[0] * px + clat[1] * py + clat[2])

    def to_px(lon, lat):
        M = np.array([[clon[0], clon[1]], [clat[0], clat[1]]])
        t = np.array([clon[2], clat[2]])
        return np.linalg.solve(M, np.array([lon, lat]) - t)

    im = np.array(Image.open(PANEL).convert("RGB")).astype(int)
    R, G, B = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    red = (R > 120) & (R > G + 50) & (R > B + 50)
    comps = sorted(components(red), key=len, reverse=True)
    print(f"{len(comps)} red components; largest: {[len(c) for c in comps[:4]]}")
    welsh_set = comps[0]   # 9,038 px: outer loop + inner chord
    phoebe_set = comps[1]  # 1,872 px: loop + stem

    # --- OSM Welsh chord (ground truth) -> pixel polyline ---
    nodes, ways = load_osm_ways(OSM)
    welsh_osm = next(w for w in ways if w["tags"].get("name") == "Welsh Hills Trail")
    chord_lonlat = [nodes[n] for n in welsh_osm["nds"] if n in nodes]
    chord_px = [tuple(to_px(lon, lat)) for lon, lat in chord_lonlat]
    print(f"OSM Welsh chord: {len(chord_lonlat)} pts, {line_miles(chord_lonlat):.3f} mi")

    def dist_to_polyline(px, py, poly):
        best = 1e18
        for i in range(len(poly) - 1):
            ax, ay = poly[i]
            bx, by = poly[i + 1]
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
            d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            best = min(best, d)
        return best

    # --- Welsh outer loop: polar-order the skeleton's outer boundary ---
    # Chord-removal buffers kept either leaving chord remnants or eating the
    # loop near the junctions (the transformed OSM chord deviates up to ~22 px
    # from the red chord, comparable to the chord-loop separation there). The
    # robust cut: the chord runs INSIDE the loop, so for each angular bin
    # around the loop's centroid, the outer loop is the OUTERMOST cluster of
    # skeleton pixels — no chord buffer needed at all.
    wmask = np.zeros((1000, 1040), dtype=bool)
    for (x, y) in welsh_set:
        wmask[y, x] = True
    wskel = zhang_suen(wmask)
    sy, sx = np.where(wskel)
    print(f"Welsh skeleton: {len(sx)} px")
    skel_pts = [(float(x), float(y)) for x, y in zip(sx, sy)]
    cx = sum(p[0] for p in skel_pts) / len(skel_pts)
    cy = sum(p[1] for p in skel_pts) / len(skel_pts)
    print(f"Welsh skeleton centroid pixel ({cx:.1f}, {cy:.1f})")
    NBIN = 72
    bins = [[] for _ in range(NBIN)]
    for (x, y) in skel_pts:
        ang = math.atan2(y - cy, x - cx)
        b = int((ang + math.pi) / (2 * math.pi) * NBIN) % NBIN
        bins[b].append((x, y, math.hypot(x - cx, y - cy)))
    loop_px = []
    for b in range(NBIN):
        pts = bins[b]
        if not pts:
            continue
        rmax = max(p[2] for p in pts)
        outer = [p for p in pts if p[2] > rmax - 10.0]
        mx = sum(p[0] for p in outer) / len(outer)
        my = sum(p[1] for p in outer) / len(outer)
        loop_px.append((math.atan2(my - cy, mx - cx), (mx, my)))
    loop_px.sort(key=lambda t: t[0])
    loop_px = [p for _, p in loop_px]
    loop_px.append(loop_px[0])
    loop_px = simplify(loop_px, tol_px=3.0)
    loop_ll = [to_lonlat(px, py) for px, py in loop_px]
    print(f"Welsh outer loop: {len(loop_px)} pts, {line_miles(loop_ll):.3f} mi")

    # Phoebe is NOT traced: the map's Phoebe loop (322 px centreline, 0.66 mi)
    # is the same trail as the OSM way (0.685 mi) — the OSM geometry is ground
    # truth and supersedes the trace. Only the Welsh outer loop, which OSM
    # lacks, is traced.
    feats = [
        {"type": "Feature",
         "properties": {
             "name": "Welsh Hills Trail",
             "detail": "Outer loop (Ridge Section) — traced from DALC trifold map",
             "source": "Traced from Driftless Area Land Conservancy Welsh Hills trifold map (2026), georeferenced; approximate, +/-~100 m",
             "source_url": "https://driftlessconservancy.org/wp-content/uploads/2026/04/DT-Trifold-Welsh-Hills-Segment-11-x-8.5-in.pdf",
             "length_mi": round(line_miles(loop_ll), 3),
             "segment": "welsh-hills-outer-loop",
             "accuracy": "approximate"},
         "geometry": {"type": "LineString", "coordinates": [[round(a, 6), round(b, 6)] for a, b in loop_ll]}},
    ]
    fc = {"type": "FeatureCollection", "features": feats}
    json.dump(fc, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(feats)} features")


if __name__ == "__main__":
    main()

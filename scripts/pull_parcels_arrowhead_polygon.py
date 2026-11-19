#!/usr/bin/env python3
"""Pull ALL Minnesota parcels intersecting the Arrowhead reroute polygon.

Companion to scripts/pull_parcels_arrowhead.py (the corridor set:
crossed + adjoining along the in-polygon trail). This script is the
whole-polygon set (Paul, Nov 19, 2026: "I want the entire polygon
if it can be shown").

  * Source: "Parcels, Compiled from Opt-In Open Data Counties,
    Minnesota" - MnGeo feature service, layer 0 ("Open Parcels In
    Minnesota"), same as the corridor pull. No county filter: every
    opt-in county overlapping the polygon is caught, so a county
    the corridor was not known to cross cannot silently drop out.
  * Selection: every compiled parcel whose geometry INTERSECTS the
    2004 NPS preferred-alternative corridor polygon
    (site/buildout/data/corridor-2004.geojson, 1,243.4 sq mi).
    The Nov 18 estimate for this set was 45,793 parcels, ~22 MB
    as a working file (see pull_parcels_arrowhead.py docstring).
    Attribute-empty records (water / rights-of-way, not parcels)
    are dropped first, exactly as in the corridor pull.
  * Geometry is NOT clipped: a parcel straddling the polygon
    boundary is carried whole. The straddler count is reported
    (a parcel counts as straddling when its bbox overlaps a
    polygon-edge bbox while the parcel is not fully inside).
  * Query shape: 0.05-degree grid envelopes over the polygon bbox,
    kept when the cell centre is inside the polygon or within
    ~8 km of a polygon edge (so no boundary-straddling parcel can
    fall through a gap), each padded by the 2.5 km candidate
    margin. IDs are deduplicated across envelopes, then fetched
    in chunks of 500 — the same pull_candidates machinery as the
    corridor pull.

Output: data/parcels/parcels-arrowhead-polygon.geojson (working
data, with each parcel's attributes exactly as published, plus
source_county, source_dataset, corridor_class="polygon"). The
published file is built by scripts/build_site_data.py
(map_arrowhead_parcel), the same mapping as the chapter parcels.

PRIVACY: the output contains landowner names as published. It
is chapter WORKING-VIEW data only and must never be published
or copied into the public view except through build_site_data.py
(see DESIGN.md privacy rules).

Usage:  python3 scripts/pull_parcels_arrowhead_polygon.py
No credentials required; the service is public.
"""

import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo_util import (  # noqa: E402
    bbox_of,
    bbox_overlap,
    iter_poly_segments,
    iter_polys,
    point_in_geometry,
    point_seg_dist_km,
    seg_seg_intersect,
)
from pull_parcels_arrowhead import is_parcel  # noqa: E402
from pull_parcels_corridor import (  # noqa: E402
    CANDIDATE_MARGIN_KM,
    GRID_CELL_DEG,
    KM_PER_DEG_LAT,
    KM_PER_DEG_LON,
    pull_candidates,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
POLYGON = REPO_ROOT / "site" / "buildout" / "data" / "corridor-2004.geojson"
OUT_PATH = REPO_ROOT / "data" / "parcels" / "parcels-arrowhead-polygon.geojson"

# A grid cell is queried when its centre is inside the polygon or
# within this distance of a polygon edge. 0.1 deg ~ 11 km at this
# latitude: far more than a cell half-diagonal (~4 km), so any
# parcel intersecting the polygon overlaps a kept cell's padded
# envelope.
CELL_KEEP_DIST_DEG = 0.1


def polygon_edges(poly_geom):
    return list(iter_poly_segments(poly_geom))


def cell_near_polygon(cx, cy, poly_geom, edges):
    centre = (cx, cy)
    if point_in_geometry(centre, poly_geom):
        return True
    for a, b in edges:
        if point_seg_dist_km(centre, a, b) <= CELL_KEEP_DIST_DEG * 111.0:
            return True
    return False


def parcel_intersects_polygon(parcel_geom, poly_geom, poly_rings, edge_index):
    """True when any part of the parcel lies inside the polygon."""
    # Fast path: the parcel centroid inside the polygon.
    xs, ys, n = [], [], 0
    for poly in iter_polys(parcel_geom):
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
                n += 1
    if n == 0:
        return False
    centroid = (sum(xs) / n, sum(ys) / n)
    if point_in_geometry(centroid, poly_geom):
        return True
    # Any parcel vertex inside the polygon.
    for poly in iter_polys(parcel_geom):
        for ring in poly:
            for pt in ring:
                if point_in_geometry(pt, poly_geom):
                    return True
    # Any polygon vertex inside the parcel.
    for ring in poly_rings:
        for pt in ring:
            if point_in_geometry(pt, parcel_geom):
                return True
    # Edge crossings: only polygon edges near the parcel bbox.
    pb = bbox_of(parcel_geom)
    if pb is None:
        return False
    cx0, cy0 = int(pb[0] // GRID_CELL_DEG), int(pb[1] // GRID_CELL_DEG)
    cx1, cy1 = int(pb[2] // GRID_CELL_DEG), int(pb[3] // GRID_CELL_DEG)
    cand = set()
    for cx in range(cx0, cx1 + 1):
        for cy in range(cy0, cy1 + 1):
            cand.update(edge_index.get((cx, cy), ()))
    for a, b in iter_poly_segments(parcel_geom):
        for ei in cand:
            c, d = edge_index_edges[ei]
            if seg_seg_intersect(a, b, c, d):
                return True
    return False


# Filled by main() before parcel_intersects_polygon runs (edge list
# parallel to the grid index).
edge_index_edges = []


def main():
    t0 = time.time()
    config = json.loads(CONFIG_PATH.read_text())
    psrc = config["data_sources"]["parcels_mn"]

    poly_fc = json.loads(POLYGON.read_text())
    poly_geom = poly_fc["features"][0]["geometry"]
    poly_rings = [ring for poly in iter_polys(poly_geom) for ring in poly]
    edges = polygon_edges(poly_geom)
    print(f"Polygon: {len(edges)} edges, "
          f"bbox {bbox_of(poly_geom)}")

    # Grid cells over the polygon bbox, kept when near the polygon.
    pb = bbox_of(poly_geom)
    pad_lon = CANDIDATE_MARGIN_KM / KM_PER_DEG_LON
    pad_lat = CANDIDATE_MARGIN_KM / KM_PER_DEG_LAT
    envelopes = []
    lon = math.floor(pb[0] / GRID_CELL_DEG) * GRID_CELL_DEG
    n_cells = 0
    while lon < pb[2]:
        lat = math.floor(pb[1] / GRID_CELL_DEG) * GRID_CELL_DEG
        while lat < pb[3]:
            n_cells += 1
            cx, cy = lon + GRID_CELL_DEG / 2, lat + GRID_CELL_DEG / 2
            if cell_near_polygon(cx, cy, poly_geom, edges):
                envelopes.append({
                    "xmin": lon - pad_lon,
                    "ymin": lat - pad_lat,
                    "xmax": lon + GRID_CELL_DEG + pad_lon,
                    "ymax": lat + GRID_CELL_DEG + pad_lat,
                })
            lat += GRID_CELL_DEG
        lon += GRID_CELL_DEG
    print(f"Grid cells: {n_cells} over bbox, {len(envelopes)} kept "
          f"(centre inside polygon or within ~8 km of an edge)")

    feats = pull_candidates(
        psrc["service_root"], psrc["layer_id"], "1=1", envelopes)
    print(f"Candidates (all opt-in counties, deduped): {len(feats)} "
          f"({time.time() - t0:.0f}s)")

    before = len(feats)
    feats = [f for f in feats if is_parcel(f.get("properties"))]
    print(f"Dropped {before - len(feats)} attribute-empty records "
          f"(water / rights-of-way, not parcels)")

    # Grid index over polygon edges for the crossing test.
    global edge_index_edges
    edge_index_edges = edges
    edge_index = {}
    for ei, (a, b) in enumerate(edges):
        eb = (min(a[0], b[0]), min(a[1], b[1]),
              max(a[0], b[0]), max(a[1], b[1]))
        cx0, cy0 = int(eb[0] // GRID_CELL_DEG), int(eb[1] // GRID_CELL_DEG)
        cx1, cy1 = int(eb[2] // GRID_CELL_DEG), int(eb[3] // GRID_CELL_DEG)
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                edge_index.setdefault((cx, cy), []).append(ei)

    kept = []
    counts = Counter()
    straddlers = 0
    for feat in feats:
        geom = feat.get("geometry")
        if geom is None:
            continue
        if not parcel_intersects_polygon(geom, poly_geom, poly_rings,
                                          edge_index):
            continue
        props = dict(feat.get("properties") or {})
        county = (props.get("co_name")
                  or props.get(psrc["county_field"]))
        props["source_county"] = county
        props["source_dataset"] = psrc["name"]
        props["corridor_class"] = "polygon"
        # Straddler: bbox overlaps a polygon-edge bbox while the
        # parcel is not fully inside (any vertex outside).
        fb = bbox_of(geom)
        fully_inside = True
        for poly in iter_polys(geom):
            for ring in poly:
                for pt in ring:
                    if not point_in_geometry(pt, poly_geom):
                        fully_inside = False
                        break
                if not fully_inside:
                    break
            if not fully_inside:
                break
        if not fully_inside:
            straddlers += 1
        counts[county] += 1
        kept.append({"type": "Feature", "geometry": geom,
                     "properties": props})
    print(f"Inside polygon: {len(kept)} parcels; "
          f"straddling the boundary (carried whole): {straddlers}")
    print("Counts by county: " + json.dumps(dict(counts)))

    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "source": psrc["name"],
            "rule": "whole-polygon set (Paul, Nov 19, 2026): every "
                    "compiled parcel intersecting the 2004 corridor "
                    "polygon; geometries carried whole, not clipped",
            "counts_by_county": dict(counts),
            "straddling_boundary": straddlers,
        },
        "features": kept,
    }
    OUT_PATH.write_text(json.dumps(out_fc))
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB, "
          f"{len(kept)} features, {time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()

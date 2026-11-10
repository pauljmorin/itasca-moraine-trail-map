#!/usr/bin/env python3
"""Build simplified, browser-ready copies of the map data into site/data/.

Why: the working data files total ~28 MB of raw GeoJSON. A browser
loading all of that at once is sluggish, and raw attributes include
fields the site must never display (parcel owner names and tax
addresses from county records; snowmobile/hunter-trail maintainer
contact details in the access data). This script therefore:

* whitelists attributes per layer (privacy: anything not listed is
  dropped — see PARCEL_KEEP / mapping functions; owner/tax/POC fields
  are never copied);
* for the chapter segment layers (stretches / gaps / access points),
  applies the PUBLIC-VIEW whitelist below — this build is the public
  site build under the chapter's agreed publishing model, so the
  segment copies are public-safe by construction, not by redaction;

SEGMENTS PUBLIC WHITELIST (stretches / gaps / access points)
------------------------------------------------------------
Source: data/segments/{segment-stretches,gaps,access-points}.geojson
(working-view files; they carry the adoption tracker's personal
data). The site copies keep, per adopted stretch, ONLY:

    name, tracker_section            section identity (no people)
    length_mi, tracker_length_mi     measured vs tracker lengths
    has_adopter                      boolean derived from the tracker
                                     adopter column — the names
                                     themselves are NOT copied
    both_ends_access, access_at_start, access_at_end
                                     booleans from the crossing data
    chainage_start_mi, chainage_end_mi   position along the chain

Deliberately EXCLUDED (working-view data, never public):
    adopter / adopter_verbatim  — adopter names stay out of the
                                  public site copies entirely
    sawyer                      — a person; excluded for the same reason
    maintenance_2026_notes      — working detail (2026 mowing record)
    help_requested_2026_raw     — working detail, uninterpreted
    tracker_comments            — free text; may name people
    tracker_description         — free text; not needed publicly
    access_points (embedded)    — superseded by the access-points layer

Gaps carry only geometric/classification properties (gap id, name,
length, land context, trail kind, nearest road/trail access at each
end, trail crossings) — all public-safe; a gap by definition has no
adopter data. Access points keep label/kind/source_type/position/
section linkage — crossing names from public datasets, no people.

* rounds coordinates to 5 decimal places (~1 m);
* simplifies line/polygon geometry with Douglas-Peucker in a local
  equirectangular projection (tolerances in TOLERANCES_M below);
* normalizes parcel fields across the two source schemas (MnGeo
  standard and Hubbard County) to a common display set.

Run from the repository root:  python3 scripts/build_site_data.py
Inputs are read from data/; outputs are written to site/data/.
Standard library only — no third-party packages, no credentials.
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRECISION = 5  # decimal places on coordinates (~1.1 m in latitude)

# Simplification tolerances in metres, measured in a local
# equirectangular projection about the chapter extent's centre.
# Display-scale choices: the map is a planning/promotion tool, not a
# survey product; source data under data/ keeps full fidelity.
TOLERANCES_M = {
    "trail": 10.0,
    "parcels": 15.0,
    "access": 15.0,
    "roads": 20.0,
    "stretches": 10.0,
    "gaps": 10.0,
    "access_points": 0.0,  # points are only rounded, never simplified
}

LAT0 = math.radians(47.0)
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(LAT0)


def to_xy(pt):
    return (pt[0] * M_PER_DEG_LON, pt[1] * M_PER_DEG_LAT)


def point_line_dist_m(p, a, b):
    """Perpendicular distance (metres) from point p to segment a-b."""
    px, py = to_xy(p)
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dp_simplify(points, tol_m):
    """Douglas-Peucker on a list of [lon, lat] points; tol in metres."""
    if len(points) <= 2:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1:
            continue
        dmax, imax = 0.0, None
        for i in range(i0 + 1, i1):
            d = point_line_dist_m(points[i], points[i0], points[i1])
            if d > dmax:
                dmax, imax = d, i
        if imax is not None and dmax > tol_m:
            keep[imax] = True
            stack.append((i0, imax))
            stack.append((imax, i1))
    return [p for p, k in zip(points, keep) if k]


def round_ring(ring):
    out = []
    for pt in ring:
        r = [round(pt[0], PRECISION), round(pt[1], PRECISION)]
        if not out or out[-1] != r:
            out.append(r)
    return out


def simplify_ring(ring, tol_m):
    """Simplify a closed polygon ring, keeping it closed and valid-ish."""
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    if len(pts) <= 4:
        out = round_ring(ring)
        return out if len(out) >= 4 else None
    simp = dp_simplify(pts + [pts[0]], tol_m)[:-1]
    if len(simp) < 3:
        return None
    simp.append(list(simp[0]))
    out = []
    for pt in simp:
        r = [round(pt[0], PRECISION), round(pt[1], PRECISION)]
        if not out or out[-1] != r:
            out.append(r)
    if len(out) < 4 or out[0] != out[-1]:
        return None
    return out


def simplify_geometry(geom, tol_m):
    t = geom["type"]
    if t == "LineString":
        coords = dp_simplify(geom["coordinates"], tol_m)
        if len(coords) < 2:
            return None
        return {"type": "LineString", "coordinates": round_ring(coords)}
    if t == "MultiLineString":
        parts = []
        for line in geom["coordinates"]:
            coords = dp_simplify(line, tol_m)
            if len(coords) >= 2:
                parts.append(round_ring(coords))
        if not parts:
            return None
        return {"type": "MultiLineString", "coordinates": parts}
    if t == "Polygon":
        rings = []
        for i, ring in enumerate(geom["coordinates"]):
            r = simplify_ring(ring, tol_m)
            if r is None:
                if i == 0:
                    return None  # outer ring collapsed — drop feature
                continue
            rings.append(r)
        if not rings:
            return None
        return {"type": "Polygon", "coordinates": rings}
    if t == "MultiPolygon":
        polys = []
        for poly in geom["coordinates"]:
            rings = []
            for i, ring in enumerate(poly):
                r = simplify_ring(ring, tol_m)
                if r is None:
                    if i == 0:
                        rings = None
                        break
                    continue
                rings.append(r)
            if rings:
                polys.append(rings)
        if not polys:
            return None
        return {"type": "MultiPolygon", "coordinates": polys}
    if t == "Point":
        c = geom["coordinates"]
        return {"type": "Point",
                "coordinates": [round(c[0], PRECISION), round(c[1], PRECISION)]}
    return geom


def clean_str(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v), 2)
    return None


# ---------------------------------------------------------------- trail
TRAIL_KEEP = ["chapter", "trail_stat", "trail_type", "cert_stat",
              "seg_name", "len_miles", "ownership", "mng_auth",
              "trail_surf", "closure"]

# ---------------------------------------------------------------- parcels
def map_parcel(p):
    """Normalize both source schemas to a display-safe common set.

    PRIVACY: owner names, owner/tax addresses and taxpayer fields in
    the source records are deliberately NOT copied. Only parcel id,
    county, land class/use, acres and corridor position are kept.
    """
    county = clean_str(p.get("source_county")) or clean_str(p.get("co_name"))
    if "hubbgis_GIS_Parcels_PIN" in p:  # Hubbard County schema
        land_class = clean_str(p.get("Class1")) or clean_str(p.get("EXCLS1_DSC"))
        acres = num(p.get("hubbgis_GIS_Parcels_Acres")) or num(p.get("PYACRES"))
        return {
            "parcel_id": clean_str(p.get("hubbgis_GIS_Parcels_PIN")),
            "county": county,
            "land_class": land_class,
            "acres": acres,
            "corridor": clean_str(p.get("corridor_class")),
        }
    land_class = (clean_str(p.get("useclass1")) or clean_str(p.get("xuseclass1"))
                  or clean_str(p.get("ownership")))
    acres = num(p.get("acres_poly")) or num(p.get("acres_deed"))
    return {
        "parcel_id": clean_str(p.get("county_pin")) or clean_str(p.get("state_pin")),
        "county": county,
        "land_class": land_class,
        "acres": acres,
        "corridor": clean_str(p.get("corridor_class")),
    }


# ---------------------------------------------------------------- access
def access_name(p):
    for key in ("trail_name", "road_name", "segment_name"):
        v = clean_str(p.get(key))
        if v:
            return v
    return None


def map_access(p):
    return {
        "source_type": clean_str(p.get("source_type")),
        "name": access_name(p),
        "road_class": clean_str(p.get("road_class")),
        "miles": num(p.get("miles")) or num(p.get("lmiles"))
                 or num(p.get("lengthmile")),
        "dataset": clean_str(p.get("source_dataset")),
    }


def map_road(p):
    return {"name": clean_str(p.get("lst_name")) or clean_str(p.get("st_concat"))}


# ------------------------------------------------------------- segments
# PUBLIC-VIEW whitelist — see the module header for the full rule and
# the exclusion list. Nothing personal is copied: adopter names become
# the boolean has_adopter; sawyer, maintenance notes, comments and
# descriptions are dropped outright.

def map_stretch(p):
    has_adopter = bool(p.get("adopter")) or \
        bool(clean_str(p.get("adopter_verbatim")))
    return {
        "name": clean_str(p.get("name")),
        "tracker_section": clean_str(p.get("tracker_section")),
        "length_mi": num(p.get("length_mi")),
        "tracker_length_mi": num(p.get("tracker_length_mi")),
        "has_adopter": has_adopter,
        "both_ends_access": bool(p.get("both_ends_access")),
        "access_at_start": bool(p.get("access_at_start")),
        "access_at_end": bool(p.get("access_at_end")),
        "chainage_start_mi": num(p.get("chainage_start_mi")),
        "chainage_end_mi": num(p.get("chainage_end_mi")),
    }


def map_gap(p):
    crossings = []
    for ap in p.get("access_points") or []:
        crossings.append({
            "label": clean_str(ap.get("label")),
            "position": clean_str(ap.get("position")),
            "dist_mi": num(ap.get("dist_from_start_mi")),
        })
    land = p.get("land_context") or []
    if isinstance(land, str):
        land = [land]
    land_context = ", ".join(s.strip() for s in land if s and s.strip()) or None
    start = p.get("start") or {}
    end = p.get("end") or {}
    return {
        "gap_id": clean_str(p.get("gap_id")),
        "name": clean_str(p.get("name")),
        "length_mi": num(p.get("length_mi")),
        "classification": clean_str(p.get("classification")),
        "trail_stat": clean_str(p.get("trail_stat")),
        "land_context": land_context,
        "nearest_access_start": clean_str(p.get("nearest_access_start")),
        "nearest_access_end": clean_str(p.get("nearest_access_end")),
        "nearest_road_start": clean_str(start.get("nearest_road")),
        "nearest_road_start_mi": num(start.get("nearest_road_mi")),
        "nearest_road_end": clean_str(end.get("nearest_road")),
        "nearest_road_end_mi": num(end.get("nearest_road_mi")),
        "crossings": crossings,
        "note": clean_str(p.get("note")),
    }


def map_access_point(p):
    return {
        "label": clean_str(p.get("label")),
        "kind": clean_str(p.get("kind")),
        "source_type": clean_str(p.get("source_type")),
        "position": clean_str(p.get("position")),
        "how": clean_str(p.get("how")),
        "for_type": clean_str(p.get("for_type")),
        "for_name": clean_str(p.get("for_name")),
        "dist_from_start_mi": num(p.get("dist_from_start_mi")),
    }


LAYERS = [
    # (source, dest, tolerance key, keep-list or mapping function)
    ("data/segments/official-line-chapter-extent.geojson",
     "site/data/trail.geojson", "trail", TRAIL_KEEP),
    ("data/parcels/parcels-corridor.geojson",
     "site/data/parcels.geojson", "parcels", map_parcel),
    ("data/access/access-lines.geojson",
     "site/data/access.geojson", "access", map_access),
    ("data/access/roads.geojson",
     "site/data/roads.geojson", "roads", map_road),
    ("data/segments/segment-stretches.geojson",
     "site/data/stretches.geojson", "stretches", map_stretch),
    ("data/segments/gaps.geojson",
     "site/data/gaps.geojson", "gaps", map_gap),
    ("data/segments/access-points.geojson",
     "site/data/access-points.geojson", "access_points", map_access_point),
]


def build_one(src_rel, dst_rel, tol_key, mapper):
    src = os.path.join(ROOT, src_rel)
    dst = os.path.join(ROOT, dst_rel)
    with open(src) as f:
        data = json.load(f)
    tol = TOLERANCES_M[tol_key]
    out_features = []
    dropped = 0
    in_pts = 0
    out_pts = 0

    def count_pts(geom):
        t = geom["type"]
        if t == "Point":
            return 1
        if t in ("LineString",):
            return len(geom["coordinates"])
        if t in ("MultiLineString", "Polygon"):
            return sum(len(r) for r in geom["coordinates"])
        if t == "MultiPolygon":
            return sum(len(r) for poly in geom["coordinates"] for r in poly)
        return 0

    for feat in data["features"]:
        in_pts += count_pts(feat["geometry"])
        geom = simplify_geometry(feat["geometry"], tol)
        if geom is None:
            dropped += 1
            continue
        out_pts += count_pts(geom)
        if isinstance(mapper, list):
            props = {k: clean_str(feat["properties"].get(k))
                     if isinstance(feat["properties"].get(k), str)
                     else feat["properties"].get(k) for k in mapper}
            if isinstance(props.get("len_miles"), float):
                props["len_miles"] = round(props["len_miles"], 2)
        else:
            props = mapper(feat["properties"])
        out_features.append({"type": "Feature", "geometry": geom,
                             "properties": props})
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as f:
        json.dump({"type": "FeatureCollection", "features": out_features},
                  f, separators=(",", ":"))
    return {
        "src": src_rel, "dst": dst_rel,
        "features_in": len(data["features"]),
        "features_out": len(out_features), "dropped": dropped,
        "vertices_in": in_pts, "vertices_out": out_pts,
        "bytes_in": os.path.getsize(src), "bytes_out": os.path.getsize(dst),
    }


def main():
    results = []
    for args in LAYERS:
        results.append(build_one(*args))
    for r in results:
        print(f"{r['dst']}: {r['features_in']} -> {r['features_out']} features"
              f" ({r['dropped']} dropped in simplification), "
              f"vertices {r['vertices_in']} -> {r['vertices_out']}, "
              f"{r['bytes_in']/1e6:.2f} MB -> {r['bytes_out']/1e6:.2f} MB")
    total_in = sum(r["bytes_in"] for r in results)
    total_out = sum(r["bytes_out"] for r in results)
    print(f"TOTAL: {total_in/1e6:.2f} MB -> {total_out/1e6:.2f} MB")


if __name__ == "__main__":
    sys.exit(main())

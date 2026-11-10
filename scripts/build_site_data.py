#!/usr/bin/env python3
"""Build simplified, browser-ready copies of the map data into site/data/.

Why: the working data files total ~28 MB of raw GeoJSON. A browser
loading all of that at once is sluggish, and raw attributes include
fields the site must never display (parcel owner names and tax
addresses from county records; snowmobile/hunter-trail maintainer
contact details in the access data). This script therefore:

* whitelists attributes per layer (privacy: anything not listed is
  dropped — see PARCEL_KEEP / mapping functions; parcel TAX
  addresses and DNR maintainer POC fields are never copied. Parcel
  OWNER names and owner mailing addresses ARE carried — they are
  published public record in the county parcel data, and the
  chapter ruled on 2026-11-10 that the site shows them);
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
                                     adopter column
    adopter_display                  PLACEHOLDER adopter names only
                                     ("Test adopter 1", "Test adopter
                                     2", ...) — see below
    both_ends_access, access_at_start, access_at_end
                                     booleans from the crossing data
    chainage_start_mi, chainage_end_mi   position along the chain

ADOPTER PLACEHOLDERS (chapter instruction, 2026-11-10): the public
build shows that a section is adopted, and by a placeholder — never
by a real name. Each distinct person in the source adopter lists
is assigned "Test adopter N" in order of first appearance across
the stretches (file order = chain order); the same person keeps
the same placeholder on every section, so shared adopters read as
shared. The real names are read only to tell people apart; they
are never written to any site file.

Deliberately EXCLUDED (working-view data, never public):
    adopter / adopter_verbatim  — the real adopter names; only the
                                  placeholders above are emitted
    sawyer                      — a person; excluded for the same reason
    maintenance_2026_notes      — working detail (2026 mowing record)
    help_requested_2026_raw     — working detail, uninterpreted
    tracker_comments            — free text; may name people
    tracker_description         — free text; not needed publicly
    access_points (embedded)    — superseded by the access-points layer

PARCELS: the site copy carries parcel id, county, land class,
acres, corridor position, and — per the 2026-11-10 ruling — the
published OWNER name and owner mailing address from the same
county record (MnGeo `owner_name` + `own_add_l1..l4`; Hubbard
`PINAME1/2` + `PIADRLN1/2` + city/state/ZIP). Taxpayer name/address
fields (MnGeo `tax_name` / `tax_add_l*`) are NOT carried — the
owner record is the published one the chapter ruled on.

BOUNDARIES (site/data/boundaries.geojson): built by
build_boundaries() below from the stretch geometry endpoints (so
markers sit exactly on the drawn sections, never at raw KMZ pin
positions — one pin sits ~3.6 km off the line) plus the GAP-W west
end from the gaps file. Properties per point: name (boundary pin
name), sections (stretch names meeting there), chapter_end (true
only for the two chapter termini), and tick — the two endpoints of
the short bar the site strikes ACROSS the line at each boundary
(140 m, perpendicular to the trail's local bearing from the
adjoining stretch segment; design correction 2026-11-10: bars, not
dots, and no text at segment ends). No people, no adopter data.

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
def _join_parts(vals, sep=", "):
    parts = [clean_str(v) for v in vals]
    parts = [x for x in parts if x]
    return sep.join(parts) or None


def map_parcel(p):
    """Normalize both source schemas to a common display set.

    Per the chapter's 2026-11-10 ruling, the published OWNER name
    and the owner mailing address from the same county record are
    carried (public record). Taxpayer name/address fields are NOT
    carried. Parcels with no published owner (mostly public-land
    records) get owner=None and the popup omits the row.
    """
    county = clean_str(p.get("source_county")) or clean_str(p.get("co_name"))
    if "hubbgis_GIS_Parcels_PIN" in p:  # Hubbard County schema
        land_class = clean_str(p.get("Class1")) or clean_str(p.get("EXCLS1_DSC"))
        acres = num(p.get("hubbgis_GIS_Parcels_Acres")) or num(p.get("PYACRES"))
        owner = _join_parts([p.get("PINAME1"), p.get("PINAME2")], sep=" ")
        city_line = _join_parts([
            clean_str(p.get("PICITY")),
            _join_parts([p.get("PISTATE"),
                         p.get("PIZIPCD6") or p.get("PIZIPCD4")], sep=" "),
        ])
        owner_address = _join_parts(
            [p.get("PIADRLN1"), p.get("PIADRLN2"), city_line])
        return {
            "parcel_id": clean_str(p.get("hubbgis_GIS_Parcels_PIN")),
            "county": county,
            "land_class": land_class,
            "acres": acres,
            "corridor": clean_str(p.get("corridor_class")),
            "owner": owner,
            "owner_address": owner_address,
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
        "owner": clean_str(p.get("owner_name")),
        "owner_address": _join_parts([p.get("own_add_l1"), p.get("own_add_l2"),
                                      p.get("own_add_l3"), p.get("own_add_l4")]),
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
# the exclusion list. Real adopter names are never copied: each
# distinct person becomes a "Test adopter N" placeholder (numbered
# in order of first appearance as features are processed — the
# source file is in chain order); sawyer, maintenance notes,
# comments and descriptions are dropped outright.

_PLACEHOLDERS = {}


def _placeholder(name):
    if name not in _PLACEHOLDERS:
        _PLACEHOLDERS[name] = "Test adopter %d" % (len(_PLACEHOLDERS) + 1)
    return _PLACEHOLDERS[name]


def map_stretch(p):
    has_adopter = bool(p.get("adopter")) or \
        bool(clean_str(p.get("adopter_verbatim")))
    names = [clean_str(x) for x in (p.get("adopter") or [])]
    names = [x for x in names if x]
    return {
        "name": clean_str(p.get("name")),
        "tracker_section": clean_str(p.get("tracker_section")),
        "length_mi": num(p.get("length_mi")),
        "tracker_length_mi": num(p.get("tracker_length_mi")),
        "has_adopter": has_adopter,
        "adopter_display": [_placeholder(x) for x in names] or None,
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


# ------------------------------------------------------------ boundaries
def build_boundaries():
    """Section boundary points from the STRETCH geometry endpoints.

    One point per boundary: the first stretch's start, then every
    stretch's end (labelled by its to_boundary). Positions therefore
    sit exactly on the drawn sections — raw KMZ pin coordinates are
    never used (the Chip-13 end pin sits ~3.6 km off the line; its
    stretch is a zero-length point on the line, which is where the
    marker goes). The GAP-W west end (the chapter's west terminus,
    chainage 0) is added from the gaps file; it and the last
    stretch's end (east terminus, maximum chainage_end) are flagged
    chapter_end. Points are rounded, never simplified.
    """
    with open(os.path.join(ROOT, "data/segments/segment-stretches.geojson")) as f:
        stretches = json.load(f)["features"]
    with open(os.path.join(ROOT, "data/segments/gaps.geojson")) as f:
        gaps = json.load(f)["features"]
    stretches.sort(key=lambda f: (f["properties"].get("chainage_start_mi")
                                  is None,
                                  f["properties"].get("chainage_start_mi")
                                  or 0.0))
    points = []
    by_label = {}
    mismatches = 0
    last_seg = [None]  # fallback bearing (zero-length stretches)

    def tick_for(coord, seg):
        """Endpoints of the 140 m bar struck across the line at
        coord, perpendicular to the trail's direction along seg
        (a (from, to) pair of adjoining stretch vertices)."""
        if seg is not None:
            last_seg[0] = seg
        seg = seg or last_seg[0]
        cx, cy = to_xy(coord)
        ax, ay = to_xy(seg[0])
        bx, by = to_xy(seg[1])
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1.0
        ux, uy = -dy / norm, dx / norm  # perpendicular unit (metres)
        half = 140.0 / 2.0
        out = []
        for sgn in (-1, 1):
            x, y = cx + sgn * half * ux, cy + sgn * half * uy
            out.append([round(x / M_PER_DEG_LON, PRECISION),
                        round(y / M_PER_DEG_LAT, PRECISION)])
        return out

    def add(label, coord, section, seg=None):
        nonlocal mismatches
        if label in by_label:
            feat = by_label[label]
            have = feat["geometry"]["coordinates"]
            if abs(have[0] - coord[0]) > 0.0002 or \
                    abs(have[1] - coord[1]) > 0.0002:
                mismatches += 1
            if section and section not in feat["properties"]["sections"]:
                feat["properties"]["sections"].append(section)
            return feat
        feat = {"type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(coord[0], PRECISION),
                                             round(coord[1], PRECISION)]},
                "properties": {"name": label,
                               "sections": [section] if section else [],
                               "chapter_end": False,
                               "tick": tick_for(coord, seg)}}
        by_label[label] = feat
        points.append(feat)
        return feat

    for i, feat in enumerate(stretches):
        p = feat["properties"]
        coords = feat["geometry"]["coordinates"]
        if feat["geometry"]["type"] == "MultiLineString":
            coords = coords[0]
        start_label = p.get("from_boundary") if i == 0 \
            else stretches[i - 1]["properties"].get("to_boundary")
        seg_start = (coords[0], coords[1]) if len(coords) >= 2 else None
        seg_end = (coords[-2], coords[-1]) if len(coords) >= 2 else None
        add(start_label, coords[0], p.get("name"), seg_start)
        add(p.get("to_boundary"), coords[-1], p.get("name"), seg_end)

    # East terminus: the stretch ending at the maximum chainage_end.
    # Chip-12 and Chip-13 tie on chainage_end (Chip-13 is zero-length
    # at the chain's end), so chainage_start breaks the tie.
    east = max(stretches,
               key=lambda f: (f["properties"].get("chainage_end_mi") or -1,
                              f["properties"].get("chainage_start_mi") or -1))
    by_label[east["properties"]["to_boundary"]]["properties"]["chapter_end"] \
        = True

    if gaps:
        gcoords = gaps[0]["geometry"]["coordinates"]
        g = gcoords[0]
        west = {"type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(g[0], PRECISION),
                                             round(g[1], PRECISION)]},
                "properties": {"name": "Chapter west end (Itasca State Park)",
                               "sections": [],
                               "chapter_end": True,
                               "tick": tick_for(g, (gcoords[0],
                                                    gcoords[1]))}}
        points.insert(0, west)

    dst = os.path.join(ROOT, "site/data/boundaries.geojson")
    with open(dst, "w") as f:
        json.dump({"type": "FeatureCollection", "features": points},
                  f, separators=(",", ":"))
    return {"dst": "site/data/boundaries.geojson",
            "features_out": len(points), "mismatches": mismatches,
            "bytes_out": os.path.getsize(dst)}


def main():
    results = []
    for args in LAYERS:
        results.append(build_one(*args))
    b = build_boundaries()
    print(f"{b['dst']}: {b['features_out']} boundary points "
          f"({b['mismatches']} shared-endpoint coordinate mismatches), "
          f"{b['bytes_out']/1e6:.3f} MB")
    print(f"adopter placeholders assigned: {len(_PLACEHOLDERS)}")
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

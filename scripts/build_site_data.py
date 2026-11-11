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
    maintenance_2026                 the section's 2026 maintenance
                                     note — NOT emitted by this build:
                                     build_gazetteer.py stamps its
                                     sanitized value (names already
                                     placeholders, contacts scrubbed)
                                     onto the site stretches for the
                                     hover chip (Paul, Nov 11, 2026)

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
    maintenance_2026_notes      — the RAW notes stay working-only;
                                  only the gazetteer build's sanitized
                                  maintenance_2026 value is public
                                  (stamped, see above)
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

CORRIDOR CLIP (access + roads; cartography notes C1-C4): the
working data under data/ is NEVER cropped — the corridor is a
site-build view only, applied by build_corridor_layers() AFTER the
usual Douglas-Peucker simplification. Reference = BOTH drawn lines
(the site trail layer: the chapter chain plus the neighbouring
Laurentian Lakes chain). Non-road access is cut at ±800 m, roads at
±1.6 km, clipped at vertices with interpolated boundary crossings;
kept runs under 25 m are dropped; clipped features carry cut:true.
C3 end extensions (roads finish-the-block ≤250 m; access junction
stubs ≤150 m only where they reach another retained line) and the
C4 connector exception (a feature crossing the official line: kept
whole if ≤3 km total, else its crossing run is extended +1.5 km
past the corridor edge or to the next retained line; connector:
true) apply as specified. State forest roads are cut in the access
pass (C4 test included) and then emitted into the ROADS output as
class F (§2.9/§2.10). Roads also carry route_sys + a derived
road_class (see derive_road_class — cartoclass is null everywhere
in the source; codes verified against source names).

MILE MARKERS (site/data/milemarkers.geojson): the state half-mile
points pulled by scripts/pull_mile_markers.py, snapped to the
drawn lines (≤250 m) by build_milemarkers(); off-line points follow
an authorised route the map does not draw and are excluded with
the count printed. CHAINAGE (site/data/chainage.geojson): the S1
measured spine — points every 5 chapter miles from the west end,
interpolated along the stretch chainages (10-mile points flagged);
relative miles only, never the state or tracker reckoning.

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
import re
import sys
import time

import geo_util

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


# Road classification for the site copy (cartography notes §2.10).
# The MnDOT centreline source carries a `route_sys` code but NO
# `cartoclass` (null on every feature — verified against the pulled
# data), and the service publishes no coded-value domain for
# route_sys, so the codes below were verified empirically against
# the road names in the source itself (Nov 2026 pull):
#   '03' -> 184/184 features named "ST HWY ..."      (MN trunk highway)
#   '04' -> features named "CO HWY ..."              (county state-aid)
#   '07' -> features named "CO RD ..."               (county road)
#   '08' -> township-style numbered names (115TH, 510TH, ...)
#   '10' -> named municipal streets
#   '32' -> 37/37 "UNNAMED"
# Null-code features include real trunk highways named "STATE 371",
# "STATE 200", ... — hence the name-pattern fallback. The source
# carries no private-road identifier (status/prime_stat/surf_type do
# not identify one), so class C is labelled "minor / township" and
# private lanes are NOT separately flagged anywhere.
_HW_HWY_RE = re.compile(r"^(STATE|ST|MN|US)\b")


def derive_road_class(route_sys, name):
    """§2.10 classes: A arterial / B local named / C minor-unnamed-
    township. (Class F, state forest road, is assigned at the
    corridor stage from the access data, never here.)"""
    rs = None
    if route_sys is not None:
        s = str(route_sys).strip()
        if s:
            rs = s.zfill(2) if s.isdigit() else s
    named = bool(name) and name.strip().upper() != "UNNAMED"
    if rs in ("01", "02", "03", "04"):  # interstate/US/MN trunk, CSAH
        return "A"
    if not named:
        return "C"
    if rs in ("05", "07", "10"):  # municipal state-aid, county, city
        return "B"
    if rs is not None:  # '08' township, '13', '19', '32', other codes
        return "C"
    if _HW_HWY_RE.match(name.strip().upper()):
        return "A"
    return "B"


def map_road(p):
    name = clean_str(p.get("lst_name")) or clean_str(p.get("st_concat"))
    rs = p.get("route_sys")
    return {
        "name": name,
        "route_sys": clean_str(rs) if rs is not None else None,
        "road_class": derive_road_class(rs, name),
    }


# ------------------------------------------------------------- segments
# PUBLIC-VIEW whitelist — see the module header for the full rule and
# the exclusion list. Real adopter names are never copied: each
# distinct person becomes a "Test adopter N" placeholder (numbered
# in order of first appearance as features are processed — the
# source file is in chain order); sawyer, raw maintenance notes,
# comments and descriptions are dropped outright (the sanitized
# maintenance_2026 note is stamped on later by build_gazetteer.py).

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
    # access + roads are built by build_corridor_layers() below
    # (corridor clip C1-C4; state forest roads land in the roads
    # output as class F) — they are not plain whitelist copies.
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


# ------------------------------------------------------- corridor clip
# C1-C4 implementation. All corridor maths runs in geo_util's
# equirectangular km space (points pre-projected once per feature).

CORRIDOR_HW_KM = {"access": 0.8, "roads": 1.6}   # C1 half-widths
MIN_RUN_KM = 0.025                                # C2: drop runs < 25 m
SAMPLE_STEP_KM = 0.1    # C6: distance tests sample long segments
CROSS_WHOLE_MAX_KM = 3.0                          # C4
C4_EXTEND_KM = 1.5                                # C4
ROAD_FINISH_KM = 0.25                             # C3 roads
STUB_MAX_KM = 0.15                                # C3 access
REACH_KM = 0.015        # "reaches another retained line" (15 m)
POST_CLIP_TOL_M = 5.0   # C1: light DP re-run after clipping


def _xy(p):
    return geo_util.to_xy((p[0], p[1]))


def _lonlat(xy):
    return [round(xy[0] / geo_util.KX_KM_PER_DEG, PRECISION),
            round(xy[1] / geo_util.KY_KM_PER_DEG, PRECISION)]


def _pt_seg_dist_xy(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    len2 = dx * dx + dy * dy
    if len2 == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _orient_xy(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(v) < 1e-12:
        return 0
    return 1 if v > 0 else -1


def _on_seg_xy(p, a, b):
    if _orient_xy(a, b, p) != 0:
        return False
    return (p[0] - a[0]) * (p[0] - b[0]) + \
        (p[1] - a[1]) * (p[1] - b[1]) <= 1e-12


def _seg_intersect_xy(a, b, c, d):
    o1, o2 = _orient_xy(a, b, c), _orient_xy(a, b, d)
    o3, o4 = _orient_xy(c, d, a), _orient_xy(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return (o1 == 0 and _on_seg_xy(c, a, b)) or \
        (o2 == 0 and _on_seg_xy(d, a, b)) or \
        (o3 == 0 and _on_seg_xy(a, c, d)) or \
        (o4 == 0 and _on_seg_xy(b, c, d))


class LineIndex:
    """Uniform-grid index over projected (km) line segments, with an
    exact nearest-distance query (ring search; the stop rule compares
    the best distance found against the distance to the searched
    square's edge, so the result is the true nearest distance)."""

    def __init__(self, parts_xy, cell_km=0.5):
        self.cell = float(cell_km)
        self.grid = {}
        self.segs = []
        for part in parts_xy:
            for a, b in zip(part, part[1:]):
                if a != b:
                    self._add(a, b)

    def _add(self, a, b):
        idx = len(self.segs)
        self.segs.append((a[0], a[1], b[0], b[1]))
        c = self.cell
        for gx in range(int(math.floor(min(a[0], b[0]) / c)),
                        int(math.floor(max(a[0], b[0]) / c)) + 1):
            for gy in range(int(math.floor(min(a[1], b[1]) / c)),
                            int(math.floor(max(a[1], b[1]) / c)) + 1):
                self.grid.setdefault((gx, gy), []).append(idx)

    def nearest_km(self, px, py, cap_km=None):
        """Exact nearest distance, unless cap_km is given: then the
        search stops once the true distance is provably > cap_km
        and returns some value > cap_km. Callers that only test
        "within X?" (every corridor decision) pass a cap a little
        above X — an uncapped search over far-away points grows
        quadratically in the distance and dominates the build."""
        c = self.cell
        cx, cy = int(math.floor(px / c)), int(math.floor(py / c))
        best = math.inf
        r = 0
        while r <= 600:
            for gx in range(cx - r, cx + r + 1):
                for gy in range(cy - r, cy + r + 1):
                    if max(abs(gx - cx), abs(gy - cy)) != r:
                        continue
                    for si in self.grid.get((gx, gy), ()):
                        ax, ay, bx, by = self.segs[si]
                        d = _pt_seg_dist_xy((px, py), (ax, ay), (bx, by))
                        if d < best:
                            best = d
            lb = min(px - (cx - r) * c, (cx + r + 1) * c - px,
                     py - (cy - r) * c, (cy + r + 1) * c - py)
            if best <= lb:
                return best
            if cap_km is not None and lb > cap_km and best > cap_km:
                return best
            r += 1
        return best

    def crosses_segment(self, a, b):
        c = self.cell
        pad = 0.002
        seen = set()
        for gx in range(int(math.floor((min(a[0], b[0]) - pad) / c)),
                        int(math.floor((max(a[0], b[0]) + pad) / c)) + 1):
            for gy in range(int(math.floor((min(a[1], b[1]) - pad) / c)),
                            int(math.floor((max(a[1], b[1]) + pad) / c)) + 1):
                for si in self.grid.get((gx, gy), ()):
                    if si in seen:
                        continue
                    seen.add(si)
                    ax, ay, bx, by = self.segs[si]
                    if _seg_intersect_xy(a, b, (ax, ay), (bx, by)):
                        return True
        return False


def _geometry_parts_xy(geom):
    parts = []
    if not geom:
        return parts
    if geom.get("type") == "LineString":
        raw = [geom["coordinates"]]
    elif geom.get("type") == "MultiLineString":
        raw = geom["coordinates"]
    else:
        return parts
    for coords in raw:
        pts = [_xy(c) for c in coords if c]
        if len(pts) >= 2:
            parts.append(pts)
    return parts


def _poly_len_km(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1])
               for a, b in zip(pts, pts[1:]))


def _densify(part):
    """Samples along a projected part: (point, s_km, is_source_vertex).
    Long segments are subdivided to <= SAMPLE_STEP_KM so the C2
    inside/outside test follows the line, not just its vertices."""
    out = [(part[0], 0.0, True)]
    s = 0.0
    for a, b in zip(part, part[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(seg / SAMPLE_STEP_KM)))
        for k in range(1, n + 1):
            t = k / n
            out.append(((a[0] + (b[0] - a[0]) * t,
                         a[1] + (b[1] - a[1]) * t), s + seg * t, k == n))
        s += seg
    return out


def _point_at_s(samples, s_target):
    for (p0, s0, _), (p1, s1, _) in zip(samples, samples[1:]):
        if s0 <= s_target <= s1:
            t = 0.0 if s1 == s0 else (s_target - s0) / (s1 - s0)
            return (p0[0] + (p1[0] - p0[0]) * t,
                    p0[1] + (p1[1] - p0[1]) * t)
    return samples[-1][0] if s_target > samples[-1][1] else samples[0][0]


def _rebuild_run_pts(run):
    samples = run["samples"]
    pts = [_point_at_s(samples, run["s_lo"])]
    pts.extend(p for (p, s, is_v) in samples
               if is_v and run["s_lo"] - 1e-9 <= s <= run["s_hi"] + 1e-9)
    pts.append(_point_at_s(samples, run["s_hi"]))
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-9:
            out.append(p)
    run["pts"] = out


def _clip_part_runs(part, samples, hw_km, index):
    """C2: maximal inside runs of one part, as s-ranges on the part
    with boundary crossings interpolated in distance space. The
    distance search caps at hw + 0.5 km: adjacent samples are
    <= ~150 m apart, so a sample next to an inside one is never
    farther than that beyond the edge — every value the clip
    actually uses is exact."""
    cap = hw_km + 0.5
    dists = [index.nearest_km(p[0], p[1], cap) for (p, _, _) in samples]
    runs = []
    n = len(samples)
    i = 0
    while i < n:
        if dists[i] > hw_km:
            i += 1
            continue
        j = i
        while j + 1 < n and dists[j + 1] <= hw_km:
            j += 1
        s_lo, s_hi = samples[i][1], samples[j][1]
        at_start = at_end = False
        if i == 0:
            at_start = True
        else:
            (p0, sa, _), (p1, sb, _) = samples[i - 1], samples[i]
            d0, d1 = dists[i - 1], dists[i]
            t = (hw_km - d0) / (d1 - d0) if d1 > d0 else 0.0
            s_lo = sa + (sb - sa) * t
        if j == n - 1:
            at_end = True
        else:
            (p0, sa, _), (p1, sb, _) = samples[j], samples[j + 1]
            d0, d1 = dists[j], dists[j + 1]
            t = (hw_km - d0) / (d1 - d0) if d1 > d0 else 1.0
            s_hi = sa + (sb - sa) * t
        runs.append({"samples": samples, "s_lo": s_lo, "s_hi": s_hi,
                     "at_part_start": at_start, "at_part_end": at_end,
                     "crossing": False, "pts": None})
        i = j + 1
    return runs


def _walk_extend(run, direction, budget_km, retained_index=None):
    """Walk a run's end along its source part by up to budget_km.
    With a retained index, stop early at the first point within
    REACH_KM of a retained line and report whether one was reached.
    Returns (new_s, reached)."""
    samples = run["samples"]
    limit = samples[0][1] if direction < 0 else samples[-1][1]
    s = run["s_lo"] if direction < 0 else run["s_hi"]
    step = 0.025
    walked = 0.0
    reached = False
    while walked < budget_km - 1e-9:
        ns = s + direction * step
        ns = max(ns, limit) if direction < 0 else min(ns, limit)
        if ns == s:
            break
        walked += abs(ns - s)
        s = ns
        if retained_index is not None:
            p = _point_at_s(samples, s)
            if retained_index.nearest_km(p[0], p[1], 0.1) <= REACH_KM:
                reached = True
                break
        if s == limit:
            break
    return s, reached


def build_corridor_layers():
    """Access + roads site copies, corridor-clipped per C1-C4.

    Returns (results, trail_index): results in build_one()'s shape
    for the summary print; trail_index is reused by
    build_milemarkers() for the 250 m snap test.
    """
    t0 = time.time()
    trail_path = os.path.join(ROOT, "site/data/trail.geojson")
    with open(trail_path) as f:
        trail_fc = json.load(f)
    trail_parts = []
    for feat in trail_fc["features"]:
        trail_parts.extend(_geometry_parts_xy(feat["geometry"]))
    trail_index = LineIndex(trail_parts)
    tb = geo_util.bbox_of({"type": "MultiLineString",
                           "coordinates": [
                               [[x / geo_util.KX_KM_PER_DEG,
                                 y / geo_util.KY_KM_PER_DEG]
                                for (x, y) in part] for part in trail_parts]})

    def prep(src_rel, tol_key, mapper):
        with open(os.path.join(ROOT, src_rel)) as f:
            data = json.load(f)
        tol = TOLERANCES_M[tol_key]
        cands = []
        for feat in data["features"]:
            geom = simplify_geometry(feat["geometry"], tol)
            if geom is None:
                continue
            props = mapper(feat["properties"])
            cands.append({"props": props, "geom": geom,
                          "src_props": feat["properties"]})
        return data, cands

    access_data, access_c = prep("data/access/access-lines.geojson",
                                 "access", map_access)
    roads_data, roads_c = prep("data/access/roads.geojson",
                               "roads", map_road)
    for c in access_c:
        c["layer"] = "sfr" if \
            c["props"].get("source_type") == "state_forest_road" \
            else "access"
    for c in roads_c:
        c["layer"] = "roads"

    # ---- Phase 1: C2 clip (+ C4 crossing test) per candidate.
    for c in access_c + roads_c:
        hw = CORRIDOR_HW_KM["access" if c["layer"] != "roads" else "roads"]
        parts = _geometry_parts_xy(c["geom"])
        c["parts"] = parts
        c["total_km"] = sum(_poly_len_km(p) for p in parts)
        fb = geo_util.bbox_of(c["geom"])
        c["runs"] = []
        c["crosses"] = False
        c["connector_whole"] = False
        if fb is None or not geo_util.bbox_overlap(
                fb, tb, pad=(hw + 0.05) * 0.014):
            continue  # nowhere near either drawn line
        for part in parts:
            if any(trail_index.crosses_segment(a, b)
                   for a, b in zip(part, part[1:])):
                c["crosses"] = True
            samples = _densify(part)
            c["runs"].extend(_clip_part_runs(part, samples, hw,
                                             trail_index))
        # C4: a crossing feature of <= 3 km total is kept whole.
        if c["layer"] != "roads" and c["crosses"] \
                and c["total_km"] <= CROSS_WHOLE_MAX_KM:
            c["connector_whole"] = True
            c["runs"] = []
        for run in c["runs"]:
            _rebuild_run_pts(run)
            run["crossing"] = any(
                trail_index.crosses_segment(a, b)
                for a, b in zip(run["pts"], run["pts"][1:]))

    # ---- Phase 2: the retained-line index (trail + all base runs /
    # whole connectors) that C3 stubs and C4 extensions walk toward.
    retained_parts = list(trail_parts)
    for c in access_c + roads_c:
        if c["connector_whole"]:
            retained_parts.extend(c["parts"])
        else:
            retained_parts.extend(run["pts"] for run in c["runs"]
                                  if len(run["pts"]) >= 2)
    retained_index = LineIndex(retained_parts)

    # ---- Phase 3: C3/C4 extensions, min-run filter, emit geometry.
    def emit(c):
        if c["connector_whole"]:
            return c["geom"], False, True
        runs = []
        for run in c["runs"]:
            if c["layer"] == "roads":
                # C3 finish-the-block: a clip end within 250 m along
                # the line of the source segment's own end vertex is
                # extended to that vertex.
                total_s = run["samples"][-1][1]
                if not run["at_part_start"] and run["s_lo"] <= ROAD_FINISH_KM:
                    run["s_lo"] = 0.0
                    run["at_part_start"] = True
                if not run["at_part_end"] \
                        and total_s - run["s_hi"] <= ROAD_FINISH_KM:
                    run["s_hi"] = total_s
                    run["at_part_end"] = True
            elif run["crossing"] and c["total_km"] > CROSS_WHOLE_MAX_KM:
                # C4: extend the crossing run +1.5 km past the
                # corridor edge, or to the next retained line.
                if not run["at_part_start"]:
                    run["s_lo"], _ = _walk_extend(
                        run, -1, C4_EXTEND_KM, retained_index)
                if not run["at_part_end"]:
                    run["s_hi"], _ = _walk_extend(
                        run, +1, C4_EXTEND_KM, retained_index)
            elif c["layer"] != "roads":
                # C3 junction stubs: a dangling clip end may extend
                # up to 150 m, kept only if it reaches a retained
                # line (the trail included).
                if not run["at_part_start"]:
                    ns, ok = _walk_extend(run, -1, STUB_MAX_KM,
                                          retained_index)
                    if ok:
                        run["s_lo"] = ns
                if not run["at_part_end"]:
                    ns, ok = _walk_extend(run, +1, STUB_MAX_KM,
                                          retained_index)
                    if ok:
                        run["s_hi"] = ns
            _rebuild_run_pts(run)
            if len(run["pts"]) < 2:
                continue
            if _poly_len_km(run["pts"]) < MIN_RUN_KM \
                    and not run["crossing"]:
                continue  # C2: kept runs under 25 m are dropped
            runs.append(run)
        if not runs:
            return None, False, False
        lines = []
        for run in runs:
            coords = [_lonlat(p) for p in run["pts"]]
            g = simplify_geometry(
                {"type": "LineString", "coordinates": coords},
                POST_CLIP_TOL_M)
            lines.append(g["coordinates"] if g else
                         round_ring(coords))
        emitted_km = sum(_poly_len_km(run["pts"]) for run in runs)
        cut = emitted_km < c["total_km"] - 1e-6 or len(runs) > 1
        geom = {"type": "LineString", "coordinates": lines[0]} \
            if len(lines) == 1 else \
            {"type": "MultiLineString", "coordinates": lines}
        return geom, cut, False

    def finish(cands, dst_rel, layer_filter, props_fn):
        feats = []
        dropped = 0
        v_in = v_out = 0
        for c in cands:
            if c["layer"] not in layer_filter:
                continue
            v_in += sum(len(p) for p in c["parts"])
            geom, cut, connector = emit(c)
            if geom is None:
                dropped += 1
                continue
            props = props_fn(c)
            if cut:
                props["cut"] = True
            if connector:
                props["connector"] = True
            v_out += sum(len(p) for p in _geometry_parts_xy(geom))
            feats.append({"type": "Feature", "geometry": geom,
                          "properties": props})
        dst = os.path.join(ROOT, dst_rel)
        old_bytes = os.path.getsize(dst) if os.path.exists(dst) else 0
        with open(dst, "w") as f:
            json.dump({"type": "FeatureCollection", "features": feats},
                      f, separators=(",", ":"))
        return {"src": "(corridor)", "dst": dst_rel,
                "features_in": sum(1 for c in cands
                                   if c["layer"] in layer_filter),
                "features_out": len(feats), "dropped": dropped,
                "vertices_in": v_in, "vertices_out": v_out,
                "bytes_in": old_bytes,
                "bytes_out": os.path.getsize(dst)}

    def road_props(c):
        return dict(c["props"])

    def sfr_props(c):
        # §2.9 move: state forest roads join the roads output as
        # class F, named from the DNR road name/number.
        return {"name": c["props"].get("name"), "route_sys": None,
                "road_class": "F",
                "dataset": c["props"].get("dataset")}

    results = [
        finish(access_c, "site/data/access.geojson", {"access"},
               lambda c: dict(c["props"])),
        finish(roads_c + access_c, "site/data/roads.geojson",
               {"roads", "sfr"},
               lambda c: road_props(c) if c["layer"] == "roads"
               else sfr_props(c)),
    ]
    sfr_n = sum(1 for c in access_c if c["layer"] == "sfr")
    print(f"corridor clip: {time.time() - t0:.1f}s; state forest "
          f"roads moved to Roads as class F: {sfr_n} source features")
    return results, trail_index


def build_milemarkers(trail_index):
    """Snap the pulled state mile points to the drawn lines (M2):
    retain only points within 250 m of a depicted line — the rest
    follow an authorised route the map does not draw."""
    src = os.path.join(ROOT, "data/points/mile-markers.geojson")
    dst = os.path.join(ROOT, "site/data/milemarkers.geojson")
    if not os.path.exists(src):
        print("milemarkers: data/points/mile-markers.geojson missing "
              "— run scripts/pull_mile_markers.py first; skipped")
        return None
    with open(src) as f:
        data = json.load(f)
    kept, excluded = [], 0
    for feat in data["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        d = trail_index.nearest_km(*_xy((lon, lat)), cap_km=0.3)
        p = feat["properties"]
        if d <= 0.250:
            mile = p.get("mile")
            kept.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(lon, PRECISION),
                                             round(lat, PRECISION)]},
                "properties": {
                    "ident": p.get("ident"),
                    "index_": p.get("index_"),
                    "mile": mile,
                    "label": ("%g" % mile) if isinstance(
                        mile, (int, float)) else None,
                    "snap_m": round(d * 1000),
                }})
        else:
            excluded += 1
    with open(dst, "w") as f:
        json.dump({"type": "FeatureCollection", "features": kept},
                  f, separators=(",", ":"))
    whole = sum(1 for f in kept if f["properties"]["index_"] == "Index")
    print(f"site/data/milemarkers.geojson: {len(kept)} retained "
          f"({whole} whole, {len(kept) - whole} half), {excluded} "
          f"excluded (>250 m from a drawn line), "
          f"{os.path.getsize(dst)/1e3:.0f} KB")
    return {"retained": len(kept), "excluded": excluded}


def build_chainage():
    """S1 measured spine: a point every 5 chapter miles from the
    west end, interpolated along the stretch chainages of the site
    stretches copy (so the points sit on the drawn sections).
    10-mile points carry every10:true. Relative miles only."""
    with open(os.path.join(ROOT, "site/data/stretches.geojson")) as f:
        stretches = json.load(f)["features"]

    def point_at_fraction(geom, frac):
        coords = geom["coordinates"]
        if geom["type"] == "MultiLineString":
            coords = coords[0]
        pts = [to_xy(c) for c in coords]
        total = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                    for a, b in zip(pts, pts[1:]))
        if total <= 0:
            return None
        target = frac * total
        acc = 0.0
        for a, b in zip(pts, pts[1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            if acc + seg >= target:
                t = 0.0 if seg == 0 else (target - acc) / seg
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                return [round(x / M_PER_DEG_LON, PRECISION),
                        round(y / M_PER_DEG_LAT, PRECISION)]
            acc += seg
        c = coords[-1]
        return [round(c[0], PRECISION), round(c[1], PRECISION)]

    feats = []
    ordered = sorted(
        (f for f in stretches
         if f["properties"].get("chainage_start_mi") is not None),
        key=lambda f: f["properties"]["chainage_start_mi"])
    for target in range(5, 76, 5):
        for f in ordered:
            p = f["properties"]
            a, b = p["chainage_start_mi"], p["chainage_end_mi"]
            if b - a < 1e-9 or not (a - 1e-9 <= target <= b + 1e-9):
                continue
            pt = point_at_fraction(f["geometry"], (target - a) / (b - a))
            if pt:
                feats.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": pt},
                    "properties": {"kind": "chainage",
                                   "miles_from_west": target,
                                   "every10": target % 10 == 0}})
            break
    dst = os.path.join(ROOT, "site/data/chainage.geojson")
    with open(dst, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats},
                  f, separators=(",", ":"))
    n10 = sum(1 for f in feats if f["properties"]["every10"])
    print(f"site/data/chainage.geojson: {len(feats)} points "
          f"({n10} ten-mile, {len(feats) - n10} five-mile/print)")
    return {"points": len(feats), "ten_mile": n10}


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
    corridor_results, trail_index = build_corridor_layers()
    results.extend(corridor_results)
    build_milemarkers(trail_index)
    build_chainage()
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

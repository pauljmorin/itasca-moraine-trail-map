"""Small plain-geometry helpers shared by the pull scripts.

Standard library only. Topology tests run in lon/lat space (orientation
predicates are unaffected by the mild equirectangular scaling at these
latitudes); distances use a local equirectangular projection centred on
latitude 47 N (km per degree: 111.195 lat, 111.320*cos(47) lon).
"""

import math

KY_KM_PER_DEG = 111.195
KX_KM_PER_DEG = 111.320 * math.cos(math.radians(47.0))  # ~75.93


def to_xy(p):
    return (p[0] * KX_KM_PER_DEG, p[1] * KY_KM_PER_DEG)


def dist_km(a, b):
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    return math.hypot(ax - bx, ay - by)


def iter_line_segments(geometry):
    """Yield ((lon, lat), (lon, lat)) for LineString/MultiLineString."""
    if not geometry:
        return
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    lines = []
    if gtype == "LineString":
        lines = [coords]
    elif gtype == "MultiLineString":
        lines = coords
    for line in lines:
        for a, b in zip(line, line[1:]):
            yield (a[0], a[1]), (b[0], b[1])


def iter_polys(geometry):
    """Yield polygons; each polygon is a list of rings of (lon, lat)."""
    if not geometry:
        return
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        yield [[(p[0], p[1]) for p in ring] for ring in coords]
    elif gtype == "MultiPolygon":
        for poly in coords:
            yield [[(p[0], p[1]) for p in ring] for ring in poly]


def iter_poly_segments(geometry):
    for poly in iter_polys(geometry):
        for ring in poly:
            pts = ring if ring[0] == ring[-1] else ring + [ring[0]]
            for a, b in zip(pts, pts[1:]):
                yield a, b


def bbox_of(geometry):
    xs, ys = [], []

    def walk(c):
        if isinstance(c, (list, tuple)):
            if c and isinstance(c[0], (int, float)):
                xs.append(c[0])
                ys.append(c[1])
            else:
                for x in c:
                    walk(x)

    if geometry:
        walk(geometry.get("coordinates"))
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def bbox_overlap(b1, b2, pad=0.0):
    return not (
        b1[2] + pad < b2[0]
        or b1[0] - pad > b2[2]
        or b1[3] + pad < b2[1]
        or b1[1] - pad > b2[3]
    )


def point_on_segment(p, a, b, eps=1e-12):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > eps:
        return False
    dot = (x - x1) * (x - x2) + (y - y1) * (y - y2)
    return dot <= eps


def point_in_ring(p, ring):
    x, y = p
    inside = False
    pts = ring if ring[0] == ring[-1] else ring + [ring[0]]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if point_on_segment(p, (x1, y1), (x2, y2)):
            return True
        if (y1 > y) != (y2 > y):
            xint = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xint:
                inside = not inside
    return inside


def point_in_geometry(p, geometry):
    """Inside test; holes handled by ring parity within each polygon."""
    for poly in iter_polys(geometry):
        cnt = sum(1 for ring in poly if point_in_ring(p, ring))
        if cnt % 2 == 1:
            return True
    return False


def _orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(v) < 1e-12:
        return 0
    return 1 if v > 0 else -1


def seg_seg_intersect(p1, p2, p3, p4):
    o1, o2 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    o3, o4 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and point_on_segment(p3, p1, p2):
        return True
    if o2 == 0 and point_on_segment(p4, p1, p2):
        return True
    if o3 == 0 and point_on_segment(p1, p3, p4):
        return True
    if o4 == 0 and point_on_segment(p2, p3, p4):
        return True
    return False


def point_seg_dist_km(p, a, b):
    px, py = to_xy(p)
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    dx, dy = bx - ax, by - ay
    len2 = dx * dx + dy * dy
    if len2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg_dist_km(a, b, c, d):
    if seg_seg_intersect(a, b, c, d):
        return 0.0
    return min(
        point_seg_dist_km(a, c, d),
        point_seg_dist_km(b, c, d),
        point_seg_dist_km(c, a, b),
        point_seg_dist_km(d, a, b),
    )

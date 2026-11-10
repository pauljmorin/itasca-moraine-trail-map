#!/usr/bin/env python3
"""Overlay the chapter's adopter-boundary KMZ on the official NCT line.

Inputs
  data/segments/NCT_Itasca_Moraine_Segments.kmz   (chapter's own file)
  data/segments/official-line-chapter-extent.geojson
  data/access/access-lines.geojson, data/access/roads.geojson

Outputs
  data/segments/segments.geojson          faithful KMZ conversion (points)
                                          + computed overlay properties
  data/segments/segment-stretches.geojson adopted stretches of official
                                          line between consecutive
                                          boundary points
  data/segments/gaps.geojson              uncovered stretches of the
                                          chapter (ITM) line
  data/segments/access-points.geojson     road / access-trail crossings
                                          and near end-access, per
                                          segment stretch and per gap
  /tmp/segment_overlay_stats.json         every number the written
                                          report uses

Method notes
  * All lengths are geodesic (haversine, R = 6371.0088 km), the same
    convention as scripts/pull_official_line.py.
  * Projection / intersection work happens in the local equirectangular
    plane of scripts/geo_util.py (km per degree at 47 N).
  * The ITM features are chained by endpoint proximity (<= 30 m joints)
    into ordered paths ("chains"); chainage is measured along a chain
    from its western end.  The KMZ holds boundary POINTS only, so the
    adopted-segment model is: a named point starts a segment that runs
    to the next boundary point in trail order (west series, then chip
    series); "Chip-13 end" is the explicit terminus; stretches of the
    chapter line outside the adopted span, plus any official-line
    component carrying no boundary points at all, are the gaps.
"""

import json
import math
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KMZ = os.path.join(ROOT, "data/segments/NCT_Itasca_Moraine_Segments.kmz")
OFFICIAL = os.path.join(ROOT, "data/segments/official-line-chapter-extent.geojson")
ACCESS = os.path.join(ROOT, "data/access/access-lines.geojson")
ROADS = os.path.join(ROOT, "data/access/roads.geojson")
OUT_SEGMENTS = os.path.join(ROOT, "data/segments/segments.geojson")
OUT_STRETCHES = os.path.join(ROOT, "data/segments/segment-stretches.geojson")
OUT_GAPS = os.path.join(ROOT, "data/segments/gaps.geojson")
OUT_ACCESS_POINTS = os.path.join(ROOT, "data/segments/access-points.geojson")
OUT_STATS = "/tmp/segment_overlay_stats.json"

MI_PER_KM = 0.6213711922
EARTH_R_KM = 6371.0088
CHAPTER_ID = "itasca-moraine"
JOINT_TOL_KM = 0.030          # chain joints: endpoints this close join
END_ACCESS_TOL_MI = 0.25      # crossing this close to an end = end access
NEAR_TOL_KM = 0.402           # 0.25 mi: "near" end access by proximity
KML_NS = {"k": "http://www.opengis.net/kml/2.2"}


def hav_mi(p, q):
    la1, lo1, la2, lo2 = (math.radians(p[1]), math.radians(p[0]),
                          math.radians(q[1]), math.radians(q[0]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * EARTH_R_KM * math.asin(math.sqrt(h)) * MI_PER_KM


def xy(p):
    return geo_util.to_xy(p)


def from_xy(pt):
    return (pt[0] / geo_util.KX_KM_PER_DEG, pt[1] / geo_util.KY_KM_PER_DEG)


def line_length_mi(coords):
    return sum(hav_mi(a, b) for a, b in zip(coords, coords[1:]))


def iter_lines(geometry):
    if not geometry:
        return
    if geometry["type"] == "LineString":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiLineString":
        yield from geometry["coordinates"]


# ---------------------------------------------------------------- KMZ

def parse_kmz(path):
    """Return (document_name, [placemark dicts]) from the KMZ's KML."""
    with zipfile.ZipFile(path) as z:
        kml_name = next(n for n in z.namelist() if n.lower().endswith(".kml"))
        raw = z.read(kml_name)
    root = ET.fromstring(raw)
    doc = root.find("k:Document", KML_NS)
    doc_name = doc.findtext("k:name", default="", namespaces=KML_NS)
    out = []
    for pm in doc.iter("{%s}Placemark" % KML_NS["k"]):
        name = pm.findtext("k:name", default="", namespaces=KML_NS)
        style = pm.findtext("k:styleUrl", default=None, namespaces=KML_NS)
        desc = pm.findtext("k:description", default=None, namespaces=KML_NS)
        pt = pm.find("k:Point/k:coordinates", KML_NS)
        if pt is None:
            out.append({"name": name, "style_url": style,
                        "description": desc, "geometry": None})
            continue
        lon, lat, *rest = (float(v) for v in pt.text.strip().split(","))
        alt = rest[0] if rest else None
        out.append({"name": name, "style_url": style, "description": desc,
                    "geometry": (lon, lat), "altitude_m": alt})
    return doc_name, out


# ------------------------------------------------------- official line

class Chain:
    """One ordered path through a set of official-line parts."""

    def __init__(self, cid, parts):
        """parts: list of (feature_index, [lonlat, ...]) already oriented
        and ordered along the path."""
        self.id = cid
        self.feature_idxs = [i for i, _ in parts]
        verts = []
        spans = []  # (feature_index, chainage_start, chainage_end)
        cum = [0.0]
        for fidx, coords in parts:
            start_mark = None
            for c in coords:
                p = (c[0], c[1])
                if verts and geo_util.dist_km(verts[-1], p) < 1e-9:
                    continue
                if start_mark is None:
                    start_mark = cum[-1]
                if verts:
                    cum.append(cum[-1] + hav_mi(verts[-1], p))
                verts.append(p)
            if start_mark is not None:
                spans.append((fidx, start_mark, cum[-1]))
        self.verts = verts
        self.cum = cum
        self.part_spans = spans
        self.length_mi = self.cum[-1]
        self.edges = []  # (a, b, cum_at_a, bbox)
        for i, (a, b) in enumerate(zip(verts, verts[1:])):
            bb = (min(a[0], b[0]), min(a[1], b[1]),
                  max(a[0], b[0]), max(a[1], b[1]))
            self.edges.append((a, b, self.cum[i], bb))

    def point_at(self, chainage_mi):
        """Interpolated lonlat at a chainage (clamped)."""
        c = max(0.0, min(self.length_mi, chainage_mi))
        # binary search the edge
        lo, hi = 0, len(self.cum) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if self.cum[mid] <= c:
                lo = mid
            else:
                hi = mid
        a, b = self.verts[lo], self.verts[lo + 1]
        seg = self.cum[lo + 1] - self.cum[lo]
        t = 0.0 if seg == 0 else (c - self.cum[lo]) / seg
        ax, ay = xy(a)
        bx, by = xy(b)
        return from_xy((ax + t * (bx - ax), ay + t * (by - ay)))

    def subline(self, c0, c1):
        """Lonlat polyline of the chain between two chainages."""
        c0, c1 = max(0.0, c0), min(self.length_mi, c1)
        pts = [self.point_at(c0)]
        for v, cv in zip(self.verts, self.cum):
            if c0 < cv < c1:
                pts.append(v)
        pts.append(self.point_at(c1))
        out = []
        for p in pts:
            if not out or geo_util.dist_km(out[-1], p) > 1e-9:
                out.append(p)
        return out

    def project(self, p, window_deg=None):
        """(offset_km, chainage_mi, foot_lonlat) of the closest point.

        window_deg: when given, only edges whose bbox falls within this
        many degrees of p are considered (the prefilter the crossing
        search needs); the default scans a 0.5-degree neighbourhood so
        far-off-line points still find their true nearest edge."""
        px, py = xy(p)
        best = None
        pad = window_deg if window_deg is not None else 0.5
        for i, (a, b, cum_a, bb) in enumerate(self.edges):
            if not (bb[0] - pad <= p[0] <= bb[2] + pad
                    and bb[1] - pad <= p[1] <= bb[3] + pad):
                continue
            ax, ay = xy(a)
            bx, by = xy(b)
            dx, dy = bx - ax, by - ay
            len2 = dx * dx + dy * dy
            t = 0.0 if len2 == 0 else max(
                0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len2))
            fx, fy = ax + t * dx, ay + t * dy
            d = math.hypot(px - fx, py - fy)
            if best is None or d < best[0]:
                seg_mi = self.cum[i + 1] - self.cum[i]
                best = (d, cum_a + t * seg_mi, from_xy((fx, fy)))
        return best


def build_chains(features):
    """Group LineString parts into ordered chains by endpoint proximity.

    Returns (chains, diagnostics).  Chains are oriented west to east
    (start = the end nearest the component's westernmost vertex).
    """
    parts = []  # (feature_index, coords)
    for i, f in enumerate(features):
        for coords in iter_lines(f["geometry"]):
            parts.append((i, [(c[0], c[1]) for c in coords]))

    n = len(parts)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    ends = [(geo_util.to_xy(c[0]), geo_util.to_xy(c[-1])) for _, c in parts]
    for i in range(n):
        for j in range(i + 1, n):
            for ei in ends[i]:
                for ej in ends[j]:
                    if math.hypot(ei[0] - ej[0], ei[1] - ej[1]) <= JOINT_TOL_KM:
                        union(i, j)
    comps = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)

    chains = []
    diagnostics = []
    # order components west to east by westernmost vertex
    def comp_west(idxs):
        return min(c[0] for i in idxs for c in [parts[i][1][0]]) \
            if False else min(p[0] for i in idxs for p in parts[i][1])
    ordered = sorted(comps.values(), key=comp_west)
    for k, idxs in enumerate(ordered):
        cid = "C%d" % (k + 1)
        if len(idxs) == 1:
            i = idxs[0]
            coords = parts[i][1]
            if coords[0][0] > coords[-1][0]:
                coords = coords[::-1]
            chains.append(Chain(cid, [(parts[i][0], coords)]))
            diagnostics.append({"chain": cid, "parts": 1,
                                "note": "single feature, no shared endpoints"})
            continue
        # adjacency: part -> [(other_part, my_end, other_end)]
        adj = {i: [] for i in idxs}
        for a_i in idxs:
            for b_i in idxs:
                if a_i >= b_i:
                    continue
                for ea, pa in (("s", ends[a_i][0]), ("e", ends[a_i][1])):
                    for eb, pb in (("s", ends[b_i][0]), ("e", ends[b_i][1])):
                        if math.hypot(pa[0] - pb[0], pa[1] - pb[1]) <= JOINT_TOL_KM:
                            adj[a_i].append((b_i, ea, eb))
                            adj[b_i].append((a_i, eb, ea))
        # degree-1 parts define the path ends
        starts = [i for i in idxs if len(adj[i]) == 1]
        if len(starts) != 2:
            diagnostics.append({"chain": cid, "parts": len(idxs),
                                "note": "NOT a simple path: %d degree-1 parts"
                                        % len(starts)})
        start = starts[0] if starts else idxs[0]
        # orient the walk start at the westernmost free end
        if len(starts) == 2:
            def free_end_lon(i):
                used = adj[i][0][1]
                c = parts[i][1]
                return c[0][0] if used == "e" else c[-1][0]
            if free_end_lon(starts[1]) < free_end_lon(starts[0]):
                start = starts[1]
        seq = []
        prev, cur = None, start
        # orient first part: its joined end must be the far end
        joined_end = adj[cur][0][1] if adj[cur] else "e"
        coords = parts[cur][1]
        if joined_end == "s":
            coords = coords[::-1]
        seq.append((parts[cur][0], coords))
        while adj[cur]:
            nxt = [x for x in adj[cur] if x[0] != prev]
            if not nxt:
                break
            nb, my_end, nb_end = nxt[0]
            coords = parts[nb][1]
            if nb_end == "e":
                coords = coords[::-1]
            seq.append((parts[nb][0], coords))
            prev, cur = cur, nb
            if len(seq) > len(idxs):
                break
        chains.append(Chain(cid, seq))
        diagnostics.append({"chain": cid, "parts": len(seq),
                            "note": "path" if len(starts) == 2 else "walked"})
    return chains, diagnostics


# ------------------------------------------------------------ analysis

def project_on_features(p, features):
    """Closest approach of point p to any feature line.

    Returns (offset_km, feature_index, foot_lonlat)."""
    best = None
    for i, f in enumerate(features):
        for a, b in geo_util.iter_line_segments(f["geometry"]):
            d = geo_util.point_seg_dist_km(p, a, b)
            if best is None or d < best[0]:
                ax, ay = xy(a)
                bx, by = xy(b)
                px, py = xy(p)
                dx, dy = bx - ax, by - ay
                len2 = dx * dx + dy * dy
                t = 0.0 if len2 == 0 else max(
                    0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len2))
                best = (d, i, from_xy((ax + t * dx, ay + t * dy)))
    return best


def features_overlapping(features, chain, c0, c1, step_mi=0.05):
    """Official features whose geometry is near chain chainages c0..c1.

    Samples the chain and takes, for each sample, the nearest feature
    (within 60 m); returns the set of feature indices found."""
    found = {}
    n = max(2, int((c1 - c0) / step_mi) + 1)
    for k in range(n + 1):
        c = c0 + (c1 - c0) * k / n
        p = chain.point_at(c)
        d, i, _ = project_on_features(p, features)
        if d <= 0.060:
            found[i] = True
    return sorted(found)


def stat_split(features, idxs, chain, c0, c1):
    """(offroad_mi, onroad_mi) within a chainage interval.

    Computed from the interval's own vertices: each chain edge adopts
    the trail_stat of the overlapping feature that owns it (parts carry
    their feature index through chain construction), so short on-road
    features are not lost between sample points."""
    parts = getattr(chain, "part_spans", None)
    if not parts:
        return round(c1 - c0, 3), 0.0
    off = on = 0.0
    for fidx, s, e in parts:
        lo, hi = max(s, c0), min(e, c1)
        if hi <= lo:
            continue
        stat = (features[fidx]["properties"].get("trail_stat") or "")
        if "on-road" in stat:
            on += hi - lo
        else:
            off += hi - lo
    return round(off, 3), round(on, 3)


def point_line_dist_km(p, coords):
    """Distance (km) from point p to a polyline given as lonlat list."""
    best = None
    for a, b in zip(coords, coords[1:]):
        d = geo_util.point_seg_dist_km(p, a, b)
        if best is None or d < best:
            best = d
    return best


def nn_official(p, features, chain):
    """Reconciled nearest-official-line facts for one boundary point.

    The chain projection is the working position (chainage); the offset
    is the distance to the nearest official *feature* geometry, EXCEPT
    that it is never allowed to exceed the chain-projection offset:
    the chain is built from those same features, so a larger feature
    distance could only come from a chain joint the projection used.
    Returns (offset_m, feature_index_into_features)."""
    d_feat, fi, _ = project_on_features(p, features)
    proj = chain.project(p)
    d_chain_km = proj[0] if proj else d_feat
    return round(min(d_feat, d_chain_km) * 1000, 1), fi


def seg_intersect_xy(p1, p2, p3, p4):
    """Segment intersection point (xy tuples) or None; only proper
    crossings (shared endpoints excluded by caller's dedupe)."""
    d1 = (p2[0] - p1[0], p2[1] - p1[1])
    d2 = (p4[0] - p3[0], p4[1] - p3[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
    u = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / den
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return None


def find_crossings(chain, lines):
    """All crossings of one chain by candidate lines.

    lines: list of dicts {coords, kind, label, source_type, township}.
    Returns deduped crossings: {chainage_mi, lonlat, kind, label,
    source_type, township}."""
    raw = []
    pad = 0.01
    cbbox = geo_util.bbox_of({"type": "LineString",
                              "coordinates": chain.verts})
    for ln in lines:
        lb = geo_util.bbox_of({"type": "LineString",
                               "coordinates": ln["coords"]})
        if not geo_util.bbox_overlap(cbbox, lb, pad):
            continue
        lsegs = [(xy(a), xy(b)) for a, b in zip(ln["coords"], ln["coords"][1:])]
        for ei, (a, b, cum_a, bb) in enumerate(chain.edges):
            if not geo_util.bbox_overlap(bb, lb, pad):
                continue
            ea, eb = xy(a), xy(b)
            for sa, sb in lsegs:
                hit = seg_intersect_xy(ea, eb, sa, sb)
                if hit is None:
                    continue
                lonlat = from_xy(hit)
                proj = chain.project(lonlat, window_deg=0.02)
                if proj is None:
                    continue
                raw.append({"chainage_mi": round(proj[1], 4),
                            "lonlat": lonlat, "kind": ln["kind"],
                            "label": ln["label"],
                            "source_type": ln["source_type"],
                            "township": ln.get("township")})
    # Two dedupe passes.  (1) Same geographic crossing reported by
    # several DNR datasets under variant spellings of the same trail
    # system ("Forest Rider Trails" snowmobile vs "Forest Riders
    # Trails" OHV): within a 0.02 mi cluster keep one record per
    # normalized label, preferring a named record and, on ties, the
    # non-snowmobile source (more likely to be a drivable tread);
    # cluster members in other datasets are counted in "also_in".
    # (2) Same dataset+label recurring along a braided tread: keep
    # crossings at least 0.10 mi apart.
    def norm(label):
        return re.sub(r"[^a-z0-9]", "", (label or "").lower())
    raw.sort(key=lambda r: (r["chainage_mi"], norm(r["label"]),
                            r["source_type"] or ""))
    clustered = []
    for r in raw:
        if clustered and abs(r["chainage_mi"]
                             - clustered[-1]["chainage_mi"]) <= 0.02:
            clustered[-1]["members"].append(r)
        else:
            clustered.append({"chainage_mi": r["chainage_mi"],
                              "members": [r]})
    merged = []
    for cl in clustered:
        by_label = {}
        for m in cl["members"]:
            by_label.setdefault(norm(m["label"]), []).append(m)
        for _, ms in by_label.items():
            ms.sort(key=lambda m: (m["source_type"] == "snowmobile_trail",
                                   m["label"] is None))
            keep = dict(ms[0])
            keep["also_in"] = sorted({m["source_type"] for m in ms[1:]
                                      if m["source_type"]})
            merged.append(keep)
    merged.sort(key=lambda r: (r["chainage_mi"], norm(r["label"]),
                               r["source_type"] or ""))
    # (2) same label + source dataset recurring within 0.10 mi along a
    # braided tread: fold into the previous record (counted in also_in
    # as a repeat, so the braid stays visible in the data).
    out = []
    for r in merged:
        if out and norm(r["label"]) == norm(out[-1]["label"]) \
                and r["kind"] == out[-1]["kind"] \
                and r["source_type"] == out[-1]["source_type"] \
                and abs(r["chainage_mi"] - out[-1]["chainage_mi"]) <= 0.10:
            prev = out[-1]
            prev["repeat_crossings"] = prev.get("repeat_crossings", 0) + 1
            continue
        out.append(r)
    return out


def nearest_line(p, lines, max_km=8.0):
    """Closest approach of point p to candidate lines.
    Returns (dist_km, label, kind, foot_lonlat) or None."""
    best = None
    pp = xy(p)
    for ln in lines:
        for a, b in zip(ln["coords"], ln["coords"][1:]):
            ax, ay = xy(a)
            bx, by = xy(b)
            dx, dy = bx - ax, by - ay
            len2 = dx * dx + dy * dy
            t = 0.0 if len2 == 0 else max(
                0.0, min(1.0, ((pp[0] - ax) * dx + (pp[1] - ay) * dy) / len2))
            fx, fy = ax + t * dx, ay + t * dy
            d = math.hypot(pp[0] - fx, pp[1] - fy)
            if d <= max_km and (best is None or d < best[0]):
                best = (d, ln["label"], ln["kind"], from_xy((fx, fy)))
    return best


def road_label(props):
    for key in ("st_concat", "lst_name"):
        v = (props.get(key) or "").strip()
        if v:
            return v.title() if v.isupper() else v
    name = (props.get("st_name") or "").strip()
    typ = (props.get("st_pos_typ") or props.get("st_pre_typ") or "").strip()
    return (" ".join(x for x in [name, typ] if x)).strip() or None


def access_label(props):
    for key in ("trail_name", "road_name", "segment_name"):
        v = (props.get(key) or "").strip()
        if v:
            return v
    return None


# ---------------------------------------------------------------- main

def name_series(name):
    m = re.match(r"^(West|Chip)-(\d+)$", name or "")
    if m:
        return m.group(1), int(m.group(2))
    if re.match(r"^(West|Chip)-(\d+) end$", name or ""):
        m2 = re.match(r"^(West|Chip)-(\d+) end$", name)
        return m2.group(1), int(m2.group(2))
    return None, None


def main():
    stats = {}
    doc_name, placemarks = parse_kmz(KMZ)
    stats["kmz_document_name"] = doc_name
    stats["placemark_count"] = len(placemarks)
    stats["placemarks_with_description"] = sum(
        1 for p in placemarks if p["description"])

    official = json.load(open(OFFICIAL))
    all_feats = official["features"]
    itm_feats = [f for f in all_feats
                 if f["properties"].get("chapter") == "ITM"]
    stats["official_features_total"] = len(all_feats)
    stats["itm_feature_count"] = len(itm_feats)
    stats["itm_total_mi"] = round(
        sum(line_length_mi([tuple(c[:2]) for c in
                            next(iter_lines(f["geometry"]))])
            for f in itm_feats), 3)

    chains, diag = build_chains(itm_feats)
    stats["chain_diagnostics"] = diag
    stats["chains"] = {c.id: {"length_mi": round(c.length_mi, 3),
                              "parts": len(c.feature_idxs)}
                       for c in chains}
    chain_by_id = {c.id: c for c in chains}

    # ---- fit: every placemark against ALL features, and against ITM
    rows = []
    for pm in placemarks:
        p = pm["geometry"]
        d_all, fi_all, _ = project_on_features(p, all_feats)
        d_itm, fi_itm, _ = project_on_features(p, itm_feats)
        proj = None
        for c in chains:
            pr = c.project(p)
            if pr and (proj is None or pr[0] < proj[0]):
                proj = (pr[0], pr[1], pr[2], c.id)
        rows.append({
            "name": pm["name"], "point": p,
            "offset_all_m": round(d_all * 1000, 1),
            "nearest_chapter": all_feats[fi_all]["properties"].get("chapter"),
            "nearest_seg_name_all": all_feats[fi_all]["properties"].get("seg_name"),
            "offset_itm_m": round(d_itm * 1000, 1),
            "nearest_seg_name_itm": itm_feats[fi_itm]["properties"].get("seg_name"),
            "chain_offset_km": proj[0] if proj else None,
            "chainage_mi": round(proj[1], 4) if proj else None,
            "chain_id": proj[3] if proj else None,
        })
    by_name = {r["name"]: r for r in rows}
    offs = sorted(r["offset_all_m"] for r in rows)
    stats["fit"] = {
        "median_offset_m": offs[len(offs) // 2],
        "mean_offset_m": round(sum(offs) / len(offs), 1),
        "max_offset_m": offs[-1],
        "within_25m": sum(1 for o in offs if o <= 25),
        "within_100m": sum(1 for o in offs if o <= 100),
        "over_100m": [r["name"] for r in rows if r["offset_all_m"] > 100],
    }

    # ---- roles and the adopted sequence
    coords_seen = {}
    for pm in placemarks:
        key = pm["geometry"]
        if key in coords_seen:
            pm["role"], pm["duplicate_of"] = "duplicate", coords_seen[key]
        else:
            coords_seen[key] = pm["name"]
            pm["role"] = ("series_terminus"
                          if re.match(r"^(West|Chip)-\d+ end$", pm["name"])
                          else "segment_start")
            pm["duplicate_of"] = None
    seq = [p for p in placemarks if p["role"] != "duplicate"]
    seq.sort(key=lambda p: (0 if name_series(p["name"])[0] == "West" else 1,
                            name_series(p["name"])[1],
                            1 if p["role"] == "series_terminus" else 0))
    main_chain = chain_by_id[by_name["West-1"]["chain_id"]]
    stats["main_chain_id"] = main_chain.id
    stats["sequence_chain_ids"] = sorted({by_name[p["name"]]["chain_id"]
                                          for p in seq})

    # ---- reconcile KMZ points that carry a NAME for the line but do not
    # sit on the depicted line.  "Chip-13 end" lies 3,622 m from the
    # eastern end of the depicted ITM chain and is named as the end of
    # segment Chip-13: it is the adopted chain's intended terminus on
    # ground the official depiction does not currently show (or a stale
    # pin).  General rule: a numbered-series point (or its "<n> end"
    # companion) that is > 500 m off the line while its same-series
    # neighbours bracket an end of the chain is REASSIGNED to that chain
    # end, and flagged here and in segments.geojson; it is never
    # silently snapped.
    stats["reassignments"] = []
    chain_end_pt = main_chain.verts[-1]
    chain_start_pt = main_chain.verts[0]
    for pm in seq:
        r = by_name[pm["name"]]
        if r["offset_all_m"] <= 500 or r["chain_id"] != main_chain.id:
            continue
        series, _ = name_series(pm["name"])
        mates = [q for q in seq
                 if name_series(q["name"])[0] == series
                 and by_name[q["name"]]["offset_all_m"] <= 500]
        if not mates:
            continue
        mate_cha = [by_name[q["name"]]["chainage_mi"] for q in mates]
        target = None
        if max(mate_cha) > main_chain.length_mi * 0.75:
            target = (main_chain.length_mi, chain_end_pt, "east")
        elif min(mate_cha) < main_chain.length_mi * 0.25:
            target = (0.0, chain_start_pt, "west")
        if target is None:
            continue
        dist_end_km = geo_util.dist_km(pm["geometry"], target[1])
        stats["reassignments"].append({
            "name": pm["name"],
            "original_offset_m": r["offset_all_m"],
            "point": [pm["geometry"][0], pm["geometry"][1]],
            "assigned_chainage_mi": target[0],
            "distance_to_chain_end_km": round(dist_end_km, 3),
            "reason": "named terminus of the adopted series; the "
                      "official depiction's %s end stops %.2f km from "
                      "the pin" % (target[2], dist_end_km)})
        r["chainage_mi"] = target[0]
        r["chain_offset_km"] = dist_end_km
        r["reassigned"] = True
    # A numbered start whose successor is a reassigned terminus AT THE
    # SAME chainage sits exactly at the chain end: its segment has zero
    # depicted length and its real length is whatever runs from this
    # point to the terminus pin, off the depiction.  Flag it rather
    # than letting a silent 0.000 mi segment through.
    stats["zero_length_segments"] = []
    for a, b in zip(seq, seq[1:]):
        ra, rb = by_name[a["name"]], by_name[b["name"]]
        if abs(ra["chainage_mi"] - rb["chainage_mi"]) < 0.001 \
                and a["role"] == "segment_start":
            stats["zero_length_segments"].append({
                "name": a["name"], "to": b["name"],
                "pin_to_pin_km": round(
                    geo_util.dist_km(a["geometry"], b["geometry"]), 3),
                "note": "start point sits at the depicted chain end; "
                        "the segment's ground length runs to the "
                        "terminus pin, off the depicted line"})
    for r in rows:
        r.setdefault("reassigned", False)
    stats["sequence_chainages_mi"] = {
        p["name"]: by_name[p["name"]]["chainage_mi"] for p in seq}

    # ---- access / road candidate lines
    acc = json.load(open(ACCESS))
    access_lines = []
    for f in acc["features"]:
        for coords in iter_lines(f["geometry"]):
            access_lines.append({
                "coords": [tuple(c[:2]) for c in coords], "kind": "access_trail",
                "label": access_label(f["properties"]),
                "source_type": f["properties"].get("source_type"),
                "township": None})
    rds = json.load(open(ROADS))
    road_lines = []
    for f in rds["features"]:
        for coords in iter_lines(f["geometry"]):
            road_lines.append({
                "coords": [tuple(c[:2]) for c in coords], "kind": "road",
                "label": road_label(f["properties"]),
                "source_type": None,
                "township": (f["properties"].get("ctu_name_l") or None)})
    all_lines = road_lines + access_lines
    crossings = {c.id: find_crossings(c, all_lines) for c in chains}
    stats["crossing_counts"] = {k: len(v) for k, v in crossings.items()}

    def access_for(chain, c0, c1, end_points):
        """Crossings inside [c0, c1] tagged by position, plus near-access
        at the two ends (a road/trail passing within 0.25 mi of an end
        without crossing the chain there)."""
        out = []
        for cr in crossings[chain.id]:
            if c0 - 0.02 <= cr["chainage_mi"] <= c1 + 0.02:
                rel = cr["chainage_mi"] - c0
                if rel <= END_ACCESS_TOL_MI:
                    pos = "start"
                elif (c1 - cr["chainage_mi"]) <= END_ACCESS_TOL_MI:
                    pos = "end"
                else:
                    pos = "mid"
                out.append({"label": cr["label"], "kind": cr["kind"],
                            "source_type": cr["source_type"],
                            "also_in": cr.get("also_in", []),
                            "repeat_crossings": cr.get("repeat_crossings", 0),
                            "township": cr["township"],
                            "how": "crossing", "position": pos,
                            "dist_from_start_mi": round(max(rel, 0.0), 3),
                            "chainage_mi": cr["chainage_mi"],
                            "lonlat": cr["lonlat"]})
        for pos, pt in (("start", end_points[0]), ("end", end_points[1])):
            if any(a["position"] == pos for a in out):
                continue
            near = nearest_line(pt, all_lines, max_km=NEAR_TOL_KM)
            if near:
                d_km, label, kind, foot = near
                # the crossing list may already carry this same line
                # just outside the end tolerance (braided tread at the
                # boundary): don't double-report it as "near"
                if any(a["label"] == label
                       and abs(a["chainage_mi"]
                               - (c0 if pos == "start" else c1)) <= 0.30
                       for a in out):
                    continue
                out.append({"label": label, "kind": kind,
                            "source_type": None, "also_in": [],
                            "repeat_crossings": 0,
                            "township": None,
                            "how": "near", "position": pos,
                            "dist_from_start_mi": 0.0 if pos == "start"
                            else round(c1 - c0, 3),
                            "chainage_mi": c0 if pos == "start" else c1,
                            "lonlat": foot,
                            "distance_mi": round(d_km * MI_PER_KM, 3)})
        out.sort(key=lambda a: a["dist_from_start_mi"])
        return out

    def describe_end(chain, chainage, pt):
        near = nearest_line(pt, road_lines, max_km=8.0)
        desc = {"lon": round(pt[0], 6), "lat": round(pt[1], 6)}
        if near:
            d_km, label, _, foot = near
            desc["nearest_road"] = label
            desc["nearest_road_mi"] = round(d_km * MI_PER_KM, 3)
            desc["nearest_road_at"] = [round(foot[0], 6), round(foot[1], 6)]
        return desc

    # ---- stretches (adopted segments between consecutive boundaries)
    stretches = []
    for a, b in zip(seq, seq[1:]):
        ra, rb = by_name[a["name"]], by_name[b["name"]]
        c0, c1 = ra["chainage_mi"], rb["chainage_mi"]
        geom = main_chain.subline(c0, c1)
        idxs = features_overlapping(itm_feats, main_chain, c0, c1)
        off, on = stat_split(itm_feats, idxs, main_chain, c0, c1)
        land = sorted({(itm_feats[i]["properties"].get("prop_name")
                        or itm_feats[i]["properties"].get("seg_name") or "")
                       for i in idxs} - {""})
        accs = access_for(main_chain, c0, c1,
                          (main_chain.point_at(c0), main_chain.point_at(c1)))
        stretches.append({
            "name": a["name"], "from_boundary": a["name"],
            "to_boundary": b["name"], "geometry": geom,
            "chain_id": main_chain.id, "chainage_start_mi": round(c0, 4),
            "chainage_end_mi": round(c1, 4),
            "length_mi": round(line_length_mi(geom), 3),
            "crosses_series_junction": a["name"] == "West-17",
            "offroad_mi": off, "onroad_mi": on,
            "land_context": land, "access": accs})
    stats["stretch_count"] = len(stretches)
    stats["adopted_mi"] = round(sum(s["length_mi"] for s in stretches), 3)

    # ---- gaps
    gaps = []
    span0 = by_name[seq[0]["name"]]["chainage_mi"]
    span1 = by_name[seq[-1]["name"]]["chainage_mi"]
    other_chains = [c for c in chains if c.id != main_chain.id]

    def make_gap(gid, label, chain, c0, c1, classification, note):
        geom = chain.subline(c0, c1)
        idxs = features_overlapping(itm_feats, chain, c0, c1)
        off, on = stat_split(itm_feats, idxs, chain, c0, c1)
        land = sorted({(itm_feats[i]["properties"].get("prop_name")
                        or itm_feats[i]["properties"].get("seg_name") or "")
                       for i in idxs} - {""})
        p0, p1 = chain.point_at(c0), chain.point_at(c1)
        accs = access_for(chain, c0, c1, (p0, p1))
        return {"gap_id": gid, "name": label, "chain_id": chain.id,
                "chainage_start_mi": round(c0, 4),
                "chainage_end_mi": round(c1, 4),
                "geometry": geom,
                "length_mi": round(line_length_mi(geom), 3),
                "classification": classification, "note": note,
                "offroad_mi": off, "onroad_mi": on, "land_context": land,
                "start": describe_end(chain, c0, p0),
                "end": describe_end(chain, c1, p1), "access": accs}

    gaps.append(make_gap(
        "GAP-W", "West end — chapter line west of West-1", main_chain,
        0.0, span0, "outside_adopted_span",
        "Chapter (ITM) line west of the westernmost boundary point."))
    if span1 < main_chain.length_mi - 0.005:
        gaps.append(make_gap(
            "GAP-E", "East end — chapter line east of the adopted terminus",
            main_chain, span1, main_chain.length_mi, "outside_adopted_span",
            "Chapter (ITM) line east of the adopted chain's terminus."))
    else:
        stats["gap_e_note"] = (
            "No GAP-E: the adopted chain's terminus (the 'Chip-13 end' "
            "pin, reassigned to the depicted chain's east end — see "
            "reassignments) coincides with the end of the depicted "
            "chapter line, so no depicted line lies east of the adopted "
            "span. The pin itself sits 3.62 km beyond the depicted end: "
            "either the chapter works trail east of the current "
            "official depiction, or the pin is stale — flagged in the "
            "report.")
    for k, c in enumerate(sorted(other_chains, key=lambda c: c.id)):
        gaps.append(make_gap(
            "GAP-C%s" % c.id[1:], "Uncovered official-line component %s" % c.id,
            c, 0.0, c.length_mi, "uncovered_component",
            "A connected component of the chapter (ITM) depiction that "
            "carries no KMZ boundary points at all."))
    gaps.sort(key=lambda g: -g["length_mi"])
    stats["gap_count"] = len(gaps)
    stats["gap_mi"] = round(sum(g["length_mi"] for g in gaps), 3)
    stats["gaps"] = [{k: g[k] for k in
                      ("gap_id", "name", "length_mi", "classification",
                       "offroad_mi", "onroad_mi", "land_context")}
                     for g in gaps]

    stats["segments"] = [{
        "name": s["name"], "to": s["to_boundary"],
        "length_mi": s["length_mi"],
        "access_start": any(a["position"] == "start" for a in s["access"]),
        "access_end": any(a["position"] == "end" for a in s["access"]),
        "mid_crossings": sum(1 for a in s["access"] if a["position"] == "mid"),
        "access_labels": [a["label"] for a in s["access"]],
        "access": [{"label": a["label"], "kind": a["kind"],
                    "source_type": a["source_type"],
                    "position": a["position"], "how": a["how"],
                    "dist_from_start_mi": a["dist_from_start_mi"]}
                   for a in s["access"]],
    } for s in stretches]
    stats["gap_access"] = [{
        "gap_id": g["gap_id"],
        "access_start": any(a["position"] == "start" for a in g["access"]),
        "access_end": any(a["position"] == "end" for a in g["access"]),
        "mid_crossings": sum(1 for a in g["access"] if a["position"] == "mid"),
        "access_labels": [a["label"] for a in g["access"]],
        "access": [{"label": a["label"], "kind": a["kind"],
                    "source_type": a["source_type"],
                    "position": a["position"], "how": a["how"],
                    "dist_from_start_mi": a["dist_from_start_mi"]}
                   for a in g["access"]],
        "start": g["start"], "end": g["end"],
    } for g in gaps]
    stats["junction_stretch"] = next(
        ({"name": s["name"], "to": s["to_boundary"], "length_mi": s["length_mi"]}
         for s in stretches if s["crosses_series_junction"]), None)
    stats["rows"] = rows

    # ---------------------------------------------------------- outputs
    stretch_by_start = {s["from_boundary"]: s for s in stretches}
    seg_feats = []
    for pm in placemarks:
        r = by_name[pm["name"]]
        series, sidx = name_series(pm["name"])
        st = stretch_by_start.get(pm["name"])
        off_m, fi_nn = nn_official(pm["geometry"], itm_feats, main_chain)
        seg_feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [pm["geometry"][0], pm["geometry"][1]]},
            "properties": {
                "name": pm["name"],
                "kml_name": pm["name"],
                "style_url": pm["style_url"],
                "kml_description": pm["description"],
                "kml_altitude_m": pm.get("altitude_m"),
                "chapter": CHAPTER_ID,
                "role": pm["role"],
                "duplicate_of": pm["duplicate_of"],
                "series": series,
                "series_index": sidx,
                "offset_to_chapter_line_m": off_m,
                "nearest_official_chapter": r["nearest_chapter"],
                "nearest_official_seg_name":
                    itm_feats[fi_nn]["properties"].get("seg_name"),
                "on_chapter_line": off_m <= 25,
                "chain_id": r["chain_id"],
                "chainage_mi": r["chainage_mi"],
                "chainage_reassigned": bool(r.get("reassigned")),
                "reassignment_note": next(
                    (x["reason"] for x in stats["reassignments"]
                     if x["name"] == pm["name"]), None),
                "segment_name": st["name"] if st else None,
                "segment_length_mi": st["length_mi"] if st else None,
                "segment_end_at": st["to_boundary"] if st else None,
                "access_at_point": [
                    {"label": a["label"], "kind": a["kind"], "how": a["how"],
                     "position": a["position"]}
                    for a in (st["access"] if st else [])
                    if a["position"] == "start"],
            }})
    json.dump({"type": "FeatureCollection",
               "metadata": {
                   "source_kmz": "NCT_Itasca_Moraine_Segments.kmz",
                   "kml_document_name": doc_name,
                   "note": "Faithful conversion of the chapter KMZ: every "
                           "placemark is a Point; the file contains no "
                           "descriptions, dates or adopter names. Computed "
                           "overlay properties added by "
                           "scripts/segment_overlay.py."},
               "features": seg_feats},
              open(OUT_SEGMENTS, "w"), indent=1)

    def public_access(a):
        return {"label": a["label"], "kind": a["kind"],
                "source_type": a["source_type"],
                "also_in": a.get("also_in", []),
                "repeat_crossings": a.get("repeat_crossings", 0),
                "how": a["how"],
                "position": a["position"],
                "dist_from_start_mi": a["dist_from_start_mi"]}

    stretch_feats = []
    for s in stretches:
        has_s = any(a["position"] == "start" for a in s["access"])
        has_e = any(a["position"] == "end" for a in s["access"])
        has_m = any(a["position"] == "mid" for a in s["access"])
        stretch_feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString",
                         "coordinates": [[p[0], p[1]] for p in s["geometry"]]},
            "properties": {
                "name": s["name"], "chapter": CHAPTER_ID,
                "from_boundary": s["from_boundary"],
                "to_boundary": s["to_boundary"],
                "adopter": None,
                "status": "adopted (boundary-defined in chapter KMZ; "
                         "adopter names are not in the source file)",
                "length_mi": s["length_mi"],
                "chain_id": s["chain_id"],
                "chainage_start_mi": s["chainage_start_mi"],
                "chainage_end_mi": s["chainage_end_mi"],
                "crosses_series_junction": s["crosses_series_junction"],
                "depicted_length_zero": s["length_mi"] == 0,
                "trail_stat": ("undetermined (zero depicted length)"
                               if s["length_mi"] == 0 else
                               "on-road" if s["offroad_mi"] == 0 else
                               "off-road" if s["onroad_mi"] == 0 else "mixed"),
                "offroad_mi": s["offroad_mi"], "onroad_mi": s["onroad_mi"],
                "land_context": s["land_context"],
                "access_points": [public_access(a) for a in s["access"]],
                "access_at_start": has_s, "access_at_end": has_e,
                "single_ended_access": (has_s != has_e) and not has_m,
                "both_ends_access": has_s and has_e,
                "no_end_access_but_mid": (not has_s) and (not has_e) and has_m,
                "no_recorded_access": not s["access"]}})
    json.dump({"type": "FeatureCollection",
               "metadata": {
                   "note": "Adopted segment stretches: official-line "
                           "geometry between consecutive KMZ boundary "
                           "points, west series then chip series. Built "
                           "by scripts/segment_overlay.py."},
               "features": stretch_feats},
              open(OUT_STRETCHES, "w"), indent=1)

    gap_feats = []
    for g in gaps:
        has_s = any(a["position"] == "start" for a in g["access"])
        has_e = any(a["position"] == "end" for a in g["access"])
        has_m = any(a["position"] == "mid" for a in g["access"])
        gap_feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString",
                         "coordinates": [[p[0], p[1]] for p in g["geometry"]]},
            "properties": {
                "gap_id": g["gap_id"], "name": g["name"],
                "chapter": CHAPTER_ID,
                "length_mi": g["length_mi"],
                "classification": g["classification"],
                "trail_stat": ("undetermined (zero depicted length)"
                               if g["length_mi"] == 0 else
                               "on-road" if g["offroad_mi"] == 0 else
                               "off-road" if g["onroad_mi"] == 0 else "mixed"),
                "offroad_mi": g["offroad_mi"], "onroad_mi": g["onroad_mi"],
                "land_context": g["land_context"],
                "start": g["start"], "end": g["end"],
                "nearest_access_start": next(
                    (a["label"] for a in g["access"]
                     if a["position"] == "start"), None),
                "nearest_access_end": next(
                    (a["label"] for a in g["access"]
                     if a["position"] == "end"), None),
                "access_points": [public_access(a) for a in g["access"]],
                "single_ended_access": (has_s != has_e) and not has_m,
                "both_ends_access": has_s and has_e,
                "no_end_access_but_mid": (not has_s) and (not has_e) and has_m,
                "note": g["note"]}})
    json.dump({"type": "FeatureCollection",
               "metadata": {
                   "note": "Stretches of the chapter (ITM) official line "
                           "not covered by the adopted boundary-point "
                           "chain. The recruiting layer. Built by "
                           "scripts/segment_overlay.py."},
               "features": gap_feats},
              open(OUT_GAPS, "w"), indent=1)

    ap_feats = []
    for s in stretches:
        for a in s["access"]:
            ap_feats.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [a["lonlat"][0], a["lonlat"][1]]},
                "properties": {
                    "for_type": "segment", "for_name": s["name"],
                    "position": a["position"], "kind": a["kind"],
                    "source_type": a["source_type"], "label": a["label"],
                    "also_in": a.get("also_in", []),
                    "repeat_crossings": a.get("repeat_crossings", 0),
                    "township": a.get("township"), "how": a["how"],
                    "dist_from_start_mi": a["dist_from_start_mi"]}})
    for g in gaps:
        for a in g["access"]:
            ap_feats.append({
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [a["lonlat"][0], a["lonlat"][1]]},
                "properties": {
                    "for_type": "gap", "for_name": g["gap_id"],
                    "position": a["position"], "kind": a["kind"],
                    "source_type": a["source_type"], "label": a["label"],
                    "also_in": a.get("also_in", []),
                    "repeat_crossings": a.get("repeat_crossings", 0),
                    "township": a.get("township"), "how": a["how"],
                    "dist_from_start_mi": a["dist_from_start_mi"]}})
    json.dump({"type": "FeatureCollection",
               "metadata": {
                   "note": "Practical access points per segment stretch "
                           "and gap: road / access-trail crossings of the "
                           "official line (how=crossing) plus nearest "
                           "approach within 0.25 mi of an end that has no "
                           "crossing (how=near)."},
               "features": ap_feats},
              open(OUT_ACCESS_POINTS, "w"), indent=1)

    json.dump(stats, open(OUT_STATS, "w"), indent=1, default=str)
    print(json.dumps({k: stats[k] for k in
                      ("placemark_count", "itm_total_mi", "chains", "fit",
                       "main_chain_id", "sequence_chain_ids",
                       "stretch_count", "adopted_mi", "gap_count", "gap_mi",
                       "junction_stretch", "crossing_counts")}, indent=1))


if __name__ == "__main__":
    main()

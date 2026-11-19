#!/usr/bin/env python3
"""Pull MnDOT highway right-of-way data along the full Minnesota
North Country Trail corridor, for the main chapter map.

Paul, Nov 18, 2026 (voice, GO): the MnDOT right-of-way GIS is the
audit's best planning lead — where the trail could run alongside or
inside highway right-of-way, most relevant at the Ely bottleneck.

SOURCE: MnDOT Right of Way Mapping and Monitoring (RWMM), live
operational service (the one the RWMM web app itself reads):
  https://webgis.dot.state.mn.us/65agsf1/rest/services/olm/MNDOT_RWMM_OPERATIONAL/MapServer
Found via the RWMM Experience Builder app's own data config
(item 8571b65ffb394613aa3582510d105d64); the older egis12 service
(OLM/MNDOT_RWMM_AGOL_OPERATIONAL_LAYERS on mndotgis.dot.state.mn.us)
is NOT reachable from this environment (egress proxy drops it) and
is not used here. The RWMM landing page is
https://www.dot.state.mn.us/maps/gisweb/row/ — recommended in
§VI of the U of M report (docs/uofm-arrowhead-data-sources-audit-2026-11-18.md
row 15, verdict: Use).

LAYERS PULLED:
  8  Approximate Right of Way Line (polyline) — digitized limits of
     MnDOT-controlled land. Fields: CONTROL_SECTION, ROUTE_NUMBER,
     ROUTE_SYSTEM, DISTRICT, COUNTY, STATUS, LAYER, ACCURACY, SOURCE,
     SOURCE_FORMAT, OFFSET, COMMENTS, EDIT_DATE. The display field
     CADD_DOCNAME is NOT queryable (service returns 400), so it is
     not carried. LAYER values: RW / RW INP / Excess Land /
     D.O.T. Specific Interest.
  41 Parcel - Current (polygon) — MnDOT's current parcel interests
     (the "gateway" dataset: parcel polygons are MnDOT's current
     interests and index the maps/plats/descriptions behind them).
     Fields carry the table prefix ROW_ADMIN.MnDOT_Parcel_Polygons.*.
     Coverage is INCOMPLETE statewide: MnDOT's parcel-mapping
     contract (solicitation 1063806, Sep 2026) says 100,000+ parcels
     remain to be mapped; the service holds 32,236 at pull time.
     Absence of a parcel here does NOT mean MnDOT holds nothing
     there — it may mean the corridor has not been mapped yet.

NOT PULLED (recorded, not silently dropped):
  10 Access Control Line — "limited data" per MnDOT's own label.
  39 Freeway Design & Special Conditions — 80 features statewide,
     freeway design segments, not ROW limits.
  40 All Right of Way Footprint — footprints of map SHEETS (an
     index to the PDF/TIF/DGN maps), not ROW geometry.
  2/3 ROW Footprints, 13/14/15 Plat/Graphic/Narrative, 17/18 B-Point
     — survey/map-sheet artefacts, not ROW limits.
  The historic ROW maps themselves are TIF/DGN/PDF (not
     georeferenced for our purposes; TFW world files no longer
     downloadable; shapefiles only by special arrangement per the
     MnDOT FAQ) — no geometry is drawn from them.

ACCURACY CAVEAT (MnDOT's own words, carried on the popup and in
SOURCES.md): the Approximate Right of Way Line "visually displays
an approximation of MnDOT's highway right of way" and "is used as a
general index to identify official documents and other records";
ROW maps are no longer being updated (as of 2023) and do not include
recent project information. These lines are a planning pointer, not
a boundary survey — never present them as the surveyed ROW edge.
The ACCURACY field is carried per feature where populated.

CORRIDOR: the statewide NCT line (site/data/trail-minnesota.geojson,
348 features) — a feature counts when its geometry intersects a
2-mile (3,218.69 m) buffer of the line, the same corridor as the
timber, motorized and campgrounds layers. Clipping is done in
UTM 15N (shapely); distance to the trail line is recorded as
dist_trail_km. No ROW width field exists in the service — the
class (LAYER) is carried instead; nothing is invented.

Method: two-pass fetch copied from scripts/pull-motorized-mn-corridor.py
— id list first for the corridor bbox (a single envelope geometry
query silently dropped features there), then fetch by objectIds in
chunks of 500.

Outputs (source of record; the viewer reads the site/data/ copies
published by scripts/build_site_data.py, scoped build_one):
  data/row/mndot-row-lines.geojson
  data/row/mndot-row-parcels.geojson

Usage: python3 scripts/pull_mndot_row.py
"""

import json
import os
import time
import urllib.parse
from datetime import datetime, timezone

import requests
from pyproj import Transformer
from shapely.geometry import (shape, mapping, LineString, MultiLineString,
                              Polygon, MultiPolygon)
from shapely.ops import unary_union, polygonize_full

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

MS = ("https://webgis.dot.state.mn.us/65agsf1/rest/services/olm/"
      "MNDOT_RWMM_OPERATIONAL/MapServer")

LINES_LAYER = 8
PARCELS_LAYER = 41

LINES_FIELDS = ["OBJECTID", "CONTROL_SECTION", "ROUTE_NUMBER",
                "ROUTE_SYSTEM", "DISTRICT", "COUNTY", "STATUS", "LAYER",
                "ACCURACY", "SOURCE", "SOURCE_FORMAT", "OFFSET",
                "COMMENTS", "EDIT_DATE"]
# Parcel fields carry the table prefix in this joined layer.
P = "ROW_ADMIN.MnDOT_Parcel_Polygons."
PARCELS_FIELDS = [P + "OBJECTID", P + "DOCNAME", P + "PARCEL_NUMBER",
                  P + "PARCELNUM", P + "DESCRIPTION4", P + "COMMENT_",
                  P + "ACQUISITION_CATEGORY", P + "PLAN_INFO_ID",
                  P + "STATE_PROJECT", P + "STATUS", P + "PARCEL_ORIGIN",
                  "REALMS_ADMIN.RW_SV_GPV_ACQ_AREA_TYPE.ACQUISITION_AREA_TYPE",
                  "SHAPE.AREA", "SHAPE.LEN"]

MN_LINE = os.path.join(REPO, "site", "data", "trail-minnesota.geojson")
BUFFER_M = 3218.69  # 2 miles, same corridor as timber / motorized / campgrounds
OUT_DIR = os.path.join(REPO, "data", "row")

TOUTM = Transformer.from_crs("EPSG:4326", "EPSG:26915", always_xy=True)
TO4326 = Transformer.from_crs("EPSG:26915", "EPSG:4326", always_xy=True)
SQM_PER_ACRE = 4046.8564224


def fetch_json(url, retries=5):
    """GET with retries. The webgis host sits behind a WAF that
    answers HTTP 200 + an HTML 'Request Rejected' page when it
    decides the client is too chatty (seen Nov 18, 2026 after a
    burst of probes). A non-JSON body is therefore treated as
    retryable with escalating backoff, not as a hard failure."""
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            r.raise_for_status()
            if r.content[:1] == b"<":
                raise ValueError("WAF rejection page (HTTP %d, %.80s)"
                                 % (r.status_code, r.text[:80]))
            return r.json()
        except Exception as e:  # noqa: BLE001 — retry then raise
            last_err = e
            wait = (10, 60, 180, 300, 600)[attempt]
            print("  fetch retry %d/%d after %ds: %s"
                  % (attempt + 1, retries, wait, str(last_err)[:120]))
            time.sleep(wait)
    raise RuntimeError("GET %s failed after %d tries: %s"
                       % (url, retries, last_err))


def query_ids(base, env):
    params = {
        "where": "1=1",
        "geometry": json.dumps(env),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "json",
    }
    url = base + "/query?" + urllib.parse.urlencode(params)
    d = fetch_json(url)
    if d.get("error"):
        raise RuntimeError("id query failed: %s" % d["error"])
    return d.get("objectIds", [])


def fetch_by_ids(base, fields, ids):
    # POST, not GET: 500 objectIds make a GET URL long enough that this
    # server returns a non-JSON error page (Nov 18, 2026).
    out = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        data = {
            "objectIds": ",".join(str(x) for x in chunk),
            "outFields": ",".join(fields),
            "outSR": "4326",
            "returnGeometry": "true",
            "f": "json",
        }
        d = post_json(base + "/query", data)
        if d.get("error"):
            raise RuntimeError("fetch failed: %s" % d["error"])
        out.extend(d.get("features", []))
        time.sleep(2)  # pace requests: the host WAFs bursts (Nov 18, 2026)
    return out


def post_json(url, data, retries=5):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.post(url, data=data, headers=UA, timeout=180)
            r.raise_for_status()
            if r.content[:1] == b"<":
                raise ValueError("WAF rejection page (HTTP %d, %.80s)"
                                 % (r.status_code, r.text[:80]))
            return r.json()
        except Exception as e:  # noqa: BLE001 — retry then raise
            last_err = e
            wait = (10, 60, 180, 300, 600)[attempt]
            print("  post retry %d/%d after %ds: %s"
                  % (attempt + 1, retries, wait, str(last_err)[:120]))
            time.sleep(wait)
    raise RuntimeError("POST %s failed after %d tries: %s"
                       % (url, retries, last_err))


def clean_str(v):
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def ms_to_date(ms):
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000.0,
                                      tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def project(geom, tr):
    if geom.geom_type == "LineString":
        return LineString([tr.transform(x, y) for x, y in geom.coords])
    if geom.geom_type == "MultiLineString":
        return MultiLineString([project(g, tr) for g in geom.geoms])
    if geom.geom_type == "Polygon":
        return Polygon([tr.transform(x, y) for x, y in geom.exterior.coords],
                       [[tr.transform(x, y) for x, y in ring.coords]
                        for ring in geom.interiors])
    if geom.geom_type == "MultiPolygon":
        return MultiPolygon([project(g, tr) for g in geom.geoms])
    raise ValueError("unsupported " + geom.geom_type)


def esri_polyline_to_shapely(g):
    lines = []
    for path in g.get("paths", []):
        if len(path) >= 2:
            lines.append(LineString([(c[0], c[1]) for c in path]))
    if not lines:
        return None
    if len(lines) == 1:
        return lines[0]
    return MultiLineString(lines)


def esri_polygon_to_shapely(g):
    rings = g.get("rings", [])
    if not rings:
        return None
    lines = []
    for ring in rings:
        if len(ring) >= 4:
            lines.append(LineString([(c[0], c[1]) for c in ring]))
    if not lines:
        return None
    polys, dangles, cuts, invalid = polygonize_full(lines)
    if not polys:
        return None
    geoms = list(polys.geoms) if hasattr(polys, "geoms") else [polys]
    if len(geoms) == 1:
        return geoms[0]
    return MultiPolygon(geoms)


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())

    with open(MN_LINE) as f:
        mn = json.load(f)
    lines = []
    for feat in mn["features"]:
        g = shape(feat["geometry"])
        if g.geom_type == "LineString":
            lines.append(g)
        elif g.geom_type == "MultiLineString":
            lines.extend(list(g.geoms))
    trail_utm = project(unary_union(lines), TOUTM)
    corridor_utm = trail_utm.buffer(BUFFER_M)
    corridor = project(corridor_utm, TO4326)
    minx, miny, maxx, maxy = corridor.bounds
    env = {"xmin": minx, "ymin": miny, "xmax": maxx, "ymax": maxy,
           "spatialReference": {"wkid": 4326}}
    print("corridor bbox: lon %.3f..%.3f lat %.3f..%.3f"
          % (minx, maxx, miny, maxy))

    # ---- Layer 8: Approximate Right of Way Line ----
    lines_base = "%s/%d" % (MS, LINES_LAYER)
    line_ids = query_ids(lines_base, env)
    print("layer 8 ids in corridor bbox: %d" % len(line_ids))
    raw_lines = fetch_by_ids(lines_base, LINES_FIELDS, line_ids)
    print("layer 8 fetched: %d" % len(raw_lines))

    kept_lines = []
    skipped_lines = 0
    layer_counts = {}
    status_counts = {}
    for f in raw_lines:
        g = esri_polyline_to_shapely(f.get("geometry") or {})
        if g is None or g.is_empty:
            skipped_lines += 1
            continue
        cut = g.intersection(corridor)
        if cut.is_empty:
            skipped_lines += 1
            continue
        if cut.geom_type == "LineString":
            cut = MultiLineString([cut])
        elif cut.geom_type != "MultiLineString":
            skipped_lines += 1
            continue
        a = f.get("attributes") or {}
        layer_val = clean_str(a.get("LAYER"))
        status_val = clean_str(a.get("STATUS"))
        layer_counts[layer_val] = layer_counts.get(layer_val, 0) + 1
        status_counts[status_val] = status_counts.get(status_val, 0) + 1
        cut_utm = project(cut, TOUTM)
        dist_m = cut_utm.distance(trail_utm)
        length_km = round(sum(ln.length for ln in cut_utm.geoms) / 1000.0, 3)
        kept_lines.append({
            "type": "Feature",
            "geometry": mapping(cut),
            "properties": {
                "route": clean_str(a.get("ROUTE_NUMBER")),
                "route_system": clean_str(a.get("ROUTE_SYSTEM")),
                "control_section": clean_str(a.get("CONTROL_SECTION")),
                "district": clean_str(a.get("DISTRICT")),
                "county": clean_str(a.get("COUNTY")),
                "status": status_val,
                "row_class": layer_val,
                "accuracy": clean_str(a.get("ACCURACY")),
                "source": clean_str(a.get("SOURCE")),
                "source_format": clean_str(a.get("SOURCE_FORMAT")),
                "offset": clean_str(a.get("OFFSET")),
                "comments": clean_str(a.get("COMMENTS")),
                "edit_date": ms_to_date(a.get("EDIT_DATE")),
                "length_km": length_km,
                "dist_trail_km": round(dist_m / 1000.0, 3),
            },
        })
    kept_lines.sort(key=lambda f: (f["properties"]["county"] or "",
                                   f["properties"]["route"] or "",
                                   f["properties"]["control_section"] or ""))

    # ---- Layer 41: Parcel - Current ----
    parcels_base = "%s/%d" % (MS, PARCELS_LAYER)
    parcel_ids = query_ids(parcels_base, env)
    print("layer 41 ids in corridor bbox: %d" % len(parcel_ids))
    raw_parcels = fetch_by_ids(parcels_base, PARCELS_FIELDS, parcel_ids)
    print("layer 41 fetched: %d" % len(raw_parcels))

    kept_parcels = []
    skipped_parcels = 0
    parcel_status = {}
    parcel_origin = {}
    for f in raw_parcels:
        g = esri_polygon_to_shapely(f.get("geometry") or {})
        if g is None or g.is_empty:
            skipped_parcels += 1
            continue
        cut = g.intersection(corridor)
        if cut.is_empty:
            skipped_parcels += 1
            continue
        if cut.geom_type == "Polygon":
            cut = MultiPolygon([cut])
        elif cut.geom_type != "MultiPolygon":
            skipped_parcels += 1
            continue
        a = f.get("attributes") or {}
        status_val = clean_str(a.get(P + "STATUS"))
        origin_val = clean_str(a.get(P + "PARCEL_ORIGIN"))
        parcel_status[status_val] = parcel_status.get(status_val, 0) + 1
        parcel_origin[origin_val] = parcel_origin.get(origin_val, 0) + 1
        cut_utm = project(cut, TOUTM)
        area_ac = round(sum(p.area for p in cut_utm.geoms)
                        / SQM_PER_ACRE, 3)
        dist_m = cut_utm.distance(trail_utm)
        kept_parcels.append({
            "type": "Feature",
            "geometry": mapping(cut),
            "properties": {
                "parcelnum": clean_str(a.get(P + "PARCELNUM")),
                "parcel_number": clean_str(a.get(P + "PARCEL_NUMBER")),
                "docname": clean_str(a.get(P + "DOCNAME")),
                "description": clean_str(a.get(P + "DESCRIPTION4")),
                "comment": clean_str(a.get(P + "COMMENT_")),
                "acq_category": clean_str(a.get(P + "ACQUISITION_CATEGORY")),
                "acq_area_type": clean_str(a.get(
                    "REALMS_ADMIN.RW_SV_GPV_ACQ_AREA_TYPE."
                    "ACQUISITION_AREA_TYPE")),
                "state_project": clean_str(a.get(P + "STATE_PROJECT")),
                "status": status_val,
                "parcel_origin": origin_val,
                "plan_info_id": a.get(P + "PLAN_INFO_ID"),
                "area_acres": area_ac,
                "dist_trail_km": round(dist_m / 1000.0, 3),
            },
        })
    kept_parcels.sort(key=lambda f: (f["properties"]["parcelnum"] or ""))

    os.makedirs(OUT_DIR, exist_ok=True)
    lines_path = os.path.join(OUT_DIR, "mndot-row-lines.geojson")
    parcels_path = os.path.join(OUT_DIR, "mndot-row-parcels.geojson")
    total_line_km = round(sum(f["properties"]["length_km"]
                              for f in kept_lines), 2)
    total_parcel_ac = round(sum(f["properties"]["area_acres"]
                                for f in kept_parcels), 2)
    lines_out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("MnDOT Approximate Right of Way Line inside a "
                        "2-mile corridor around the full Minnesota NCT line"),
            "source_service": lines_base,
            "source_page": "https://www.dot.state.mn.us/maps/gisweb/row/",
            "corridor_source": ("site/data/trail-minnesota.geojson "
                                "(NCTA nct_public, 348 features)"),
            "corridor_buffer_m": BUFFER_M,
            "pulled_utc_date": pulled,
            "features_in_bbox": len(line_ids),
            "features_kept": len(kept_lines),
            "features_skipped_no_geometry_in_corridor": skipped_lines,
            "gis_km_inside_corridor": total_line_km,
            "km_method": "Clipped geometry measured in UTM 15N (EPSG:26915).",
            "row_class_counts": layer_counts,
            "status_counts": status_counts,
            "caveat": ("APPROXIMATE digitized limits, not a boundary survey; "
                       "ROW maps no longer updated (as of 2023). See SOURCES.md."),
        },
        "features": kept_lines,
    }
    parcels_out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("MnDOT Parcel - Current (current parcel interests) "
                        "inside a 2-mile corridor around the full "
                        "Minnesota NCT line"),
            "source_service": parcels_base,
            "source_page": "https://www.dot.state.mn.us/maps/gisweb/row/",
            "corridor_source": ("site/data/trail-minnesota.geojson "
                                "(NCTA nct_public, 348 features)"),
            "corridor_buffer_m": BUFFER_M,
            "pulled_utc_date": pulled,
            "features_in_bbox": len(parcel_ids),
            "features_kept": len(kept_parcels),
            "features_skipped_no_geometry_in_corridor": skipped_parcels,
            "acres_inside_corridor": total_parcel_ac,
            "status_counts": parcel_status,
            "parcel_origin_counts": parcel_origin,
            "caveat": ("Coverage INCOMPLETE statewide: MnDOT's parcel-mapping "
                       "project is ongoing (100,000+ parcels remain to be "
                       "mapped per solicitation 1063806, Sep 2026); absence "
                       "of a parcel here does not prove MnDOT holds nothing. "
                       "See SOURCES.md."),
        },
        "features": kept_parcels,
    }
    with open(lines_path, "w") as fh:
        json.dump(lines_out, fh)
    with open(parcels_path, "w") as fh:
        json.dump(parcels_out, fh)

    print("LINES: %d kept, %d skipped, %.2f GIS km -> %s"
          % (len(kept_lines), skipped_lines, total_line_km, lines_path))
    print("  row_class counts: %s" % layer_counts)
    print("  status counts: %s" % status_counts)
    print("PARCELS: %d kept, %d skipped, %.2f acres -> %s"
          % (len(kept_parcels), skipped_parcels, total_parcel_ac,
             parcels_path))
    print("  status counts: %s" % parcel_status)
    print("  origin counts: %s" % parcel_origin)
    # County breakdown for the report.
    from collections import Counter
    print("  lines by county: %s"
          % dict(Counter(f["properties"]["county"]
                         for f in kept_lines)))
    print("  lines by route_system: %s"
          % dict(Counter(f["properties"]["route_system"]
                         for f in kept_lines)))


if __name__ == "__main__":
    main()

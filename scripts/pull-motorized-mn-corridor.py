#!/usr/bin/env python3
"""Pull the DNR motorized trails along the ENTIRE Minnesota NCT corridor,
for the main chapter map's "Other trails" layer group.

Why this exists: the chapter-extent pull (scripts/pull-motorized-chapter.py)
stops at lon -95.6, just east of Frazee — it misses the whole western leg
of the Minnesota NCT (Frazee, Detroit Lakes, to the ND border at -96.7).
The ITM map shows the full Minnesota NCT (348 features, 566 mi), so the
motorized layers must cover the whole statewide trail, not just the
chapter extent. This pull buffers the MN NCT line by 2 miles (same
distance as the build-out viewer's motorized clip) and keeps only the
motorized tread inside that corridor.

Sources (live, same as the build-out viewer's build-motorized.py):
- Minnesota DNR OHV Trails, 2026 season:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0
- Minnesota Snowmobile Trails:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0

Method: two-pass fetch copied from site/buildout/build-motorized.py — id
list first for the corridor bbox (a single envelope geometry query silently
dropped features there), then fetch by objectIds in chunks of 500.
Geometries are intersected with the 2-mi corridor polygon (shapely, UTM
15N); full attributes kept. No contact fields pulled (public_poc /
public_pho / pocemail), same as the build-out pull.

Split: the OHV layer carries both ATV and dirt-bike (OHM) use. A feature
goes to the ATV file when atv_class_1 or atv_class_2 is 'X', and to the
OHM file when off_highway_motorcycle is 'X'. A trail that allows both
appears in both files — that is the honest reading of the DNR data.
(off_road_vehicle / 4x4 use is 3 features statewide in the chapter pull;
those ride with the ATV file.)

Outputs (source of record; the viewer reads site/data/ copies):
- data/motorized/atv-mn-corridor.geojson
- data/motorized/ohm-mn-corridor.geojson
- data/motorized/snow-mn-corridor.geojson

Usage: python3 scripts/pull-motorized-mn-corridor.py
"""

import json
import os
import time

import requests
from pyproj import Transformer
from shapely.geometry import shape, mapping, LineString, MultiLineString, Polygon, MultiPolygon
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

OHV_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
          "us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0")
SNOW_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
           "us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0")

MN_LINE = os.path.join(REPO, "site", "data", "trail-minnesota.geojson")
BUFFER_M = 3218.69  # 2 miles, same as the build-out viewer's motorized clip

TO4326 = Transformer.from_crs("EPSG:26915", "EPSG:4326", always_xy=True)
TOUTM = Transformer.from_crs("EPSG:4326", "EPSG:26915", always_xy=True)
MI = 1609.34

OHV_FIELDS = ["objectid", "trail_name", "segment_name", "surface_type",
              "funding_type", "trail_width", "atv_class_1", "atv_class_2",
              "off_highway_motorcycle", "off_road_vehicle", "road_class",
              "miles", "web_site", "program_project"]
SNOW_FIELDS = ["objectid", "trail_num", "miles", "owner_type", "trail_name",
               "maint_by", "segment_name", "stud_restr"]


def fetch_json(url, retries=3):
    # requests, not urllib: the enterprise host drops urllib requests
    # (RemoteDisconnected, Nov 16) while the same URL answers curl/requests.
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("GET %s failed after %d tries: %s" % (url, retries, last_err))


def query_fs(base, fields, env):
    """All features intersecting env (bbox dict). Two passes: id list first,
    then fetch by objectIds in chunks — a single envelope geometry query
    silently dropped 23 features on 2026-11-13."""
    import urllib.parse
    params = {
        "where": "1=1",
        "geometry": json.dumps(env),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "json",
    }
    url = base + "/query?" + urllib.parse.urlencode(params)
    ids = fetch_json(url).get("objectIds", [])
    out = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {
            "objectIds": ",".join(str(x) for x in chunk),
            "outFields": ",".join(fields),
            "outSR": "4326",
            "returnGeometry": "true",
            "f": "json",
        }
        url = base + "/query?" + urllib.parse.urlencode(params)
        out.extend(fetch_json(url).get("features", []))
    return out


def arcgis_geom_to_shapely(g):
    paths = g.get("paths", [])
    lines = []
    for p in paths:
        if len(p) >= 2:
            lines.append(LineString([(c[0], c[1]) for c in p]))
    if not lines:
        return None
    if len(lines) == 1:
        return lines[0]
    return MultiLineString(lines)


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
        from shapely.geometry import MultiPolygon
        return MultiPolygon([project(g, tr) for g in geom.geoms])
    raise ValueError("unsupported " + geom.geom_type)


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())

    # ---- build the 2-mi corridor around the whole Minnesota NCT line ----
    with open(MN_LINE) as f:
        mn = json.load(f)
    lines = []
    for feat in mn["features"]:
        g = shape(feat["geometry"])
        if g.geom_type == "LineString":
            lines.append(g)
        elif g.geom_type == "MultiLineString":
            lines.extend(list(g.geoms))
    print("MN NCT line features: %d" % len(lines))
    corridor_utm = project(unary_union(lines), TOUTM).buffer(BUFFER_M)
    corridor = project(corridor_utm, TO4326)
    minx, miny, maxx, maxy = corridor.bounds
    env = {"xmin": minx, "ymin": miny, "xmax": maxx, "ymax": maxy,
           "spatialReference": {"wkid": 4326}}
    print("corridor bbox: lon %.3f..%.3f lat %.3f..%.3f"
          % (minx, maxx, miny, maxy))

    def to_features(raw, kind, keep):
        feats, skipped, miles = [], 0, 0.0
        for f in raw:
            g = arcgis_geom_to_shapely(f.get("geometry") or {})
            if g is None or g.is_empty:
                skipped += 1
                continue
            cut = g.intersection(corridor)
            if cut.is_empty:
                skipped += 1
                continue
            if cut.geom_type == "LineString":
                cut = MultiLineString([cut])
            elif cut.geom_type != "MultiLineString":
                skipped += 1
                continue
            props = dict(f.get("attributes") or {})
            if not keep(props):
                continue
            # GIS miles: measure the clipped geometry in UTM
            cut_utm = project(cut, TOUTM)
            for line in cut_utm.geoms:
                miles += line.length / MI
            props["kind"] = kind
            feats.append({"type": "Feature", "properties": props,
                          "geometry": mapping(cut)})
        return feats, skipped, miles

    jobs = [
        ("OHV/ATV", OHV_FS, OHV_FIELDS, "atv-mn-corridor.geojson", "atv",
         lambda p: p.get("atv_class_1") == "X" or p.get("atv_class_2") == "X"),
        ("OHV/OHM", OHV_FS, OHV_FIELDS, "ohm-mn-corridor.geojson", "ohm",
         lambda p: p.get("off_highway_motorcycle") == "X"),
        ("snowmobile", SNOW_FS, SNOW_FIELDS, "snow-mn-corridor.geojson", "snow",
         lambda p: True),
    ]
    cache = {}
    for label, base, fields, out_name, kind, keep in jobs:
        if base not in cache:
            raw = query_fs(base, fields, env)
            cache[base] = raw
            print("%s features in corridor bbox: %d" % (base.split("/")[-2], len(raw)))
        feats, skipped, miles = to_features(cache[base], kind, keep)
        out = {
            "type": "FeatureCollection",
            "metadata": {
                "dataset": ("Minnesota DNR %s trails inside a 2-mile corridor "
                            "around the full Minnesota NCT line" % label),
                "source_service": base,
                "corridor_source": "site/data/trail-minnesota.geojson "
                                   "(NCTA nct_public, 348 features)",
                "corridor_buffer_m": BUFFER_M,
                "pulled_utc_date": pulled,
                "features_in_bbox": len(cache[base]),
                "features_kept": len(feats),
                "features_skipped_no_geometry_in_corridor": skipped,
                "gis_miles_inside_corridor": round(miles, 2),
                "miles_method": ("Geodesic-equivalent: clipped geometry "
                                 "measured in UTM 15N (EPSG:26915)."),
            },
            "features": feats,
        }
        path = os.path.join(REPO, "data", "motorized", out_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(out, fh)
        print("%s: %d kept, %d skipped, %.2f GIS miles -> %s"
              % (label, len(feats), skipped, miles, path))


if __name__ == "__main__":
    main()

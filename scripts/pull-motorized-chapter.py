#!/usr/bin/env python3
"""Pull the DNR motorized trails inside the chapter working extent, for the
main chapter map's new "Other trails" layer group.

Sources (live, same as the build-out viewer's build-motorized.py):
- Minnesota DNR OHV Trails, 2026 season:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0
- Minnesota Snowmobile Trails:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0

Method: two-pass fetch copied from site/buildout/build-motorized.py — id list
first (a single envelope geometry query silently dropped features there),
then fetch by objectIds in chunks of 500. Geometries are clipped to the
chapter extent box (Liang-Barsky, same approach as pull_official_line.py)
so long systems don't draw far outside the chapter area; full attributes
kept. No contact fields pulled (public_poc / public_pho / pocemail),
same as the build-out pull.

Outputs (source of record; the viewer reads site/data/ copies):
- data/motorized/atv-chapter.geojson
- data/motorized/snow-chapter.geojson

Usage: python3 scripts/pull-motorized-chapter.py
"""

import json
import math
import os
import time
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

OHV_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
          "us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0")
SNOW_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
           "us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0")

EXT = {"xmin": -95.6, "ymin": 46.7, "xmax": -94.3, "ymax": 47.35,
       "spatialReference": {"wkid": 4326}}

OHV_FIELDS = ["objectid", "trail_name", "segment_name", "surface_type",
              "funding_type", "trail_width", "atv_class_1", "atv_class_2",
              "off_highway_motorcycle", "off_road_vehicle", "road_class",
              "miles", "web_site", "program_project"]
SNOW_FIELDS = ["objectid", "trail_num", "miles", "owner_type", "trail_name",
               "maint_by", "segment_name", "stud_restr"]


def fetch_json(url, retries=3):
    # requests, not urllib: the enterprise host drops urllib requests
    # (RemoteDisconnected, Nov 16) while the same URL answers curl/requests.
    import requests
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


def query_fs(base, fields):
    params = {
        "where": "1=1",
        "geometry": json.dumps(EXT),
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


def clip_segment(a, b, ext):
    """Liang-Barsky clip of segment a-b to the extent box; None if outside."""
    x1, y1 = a
    x2, y2 = b
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - ext["xmin"]), (dx, ext["xmax"] - x1),
                 (-dy, y1 - ext["ymin"]), (dy, ext["ymax"] - y1)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy)


def clip_paths(paths, ext):
    """ArcGIS paths -> clipped GeoJSON LineString/MultiLineString coords."""
    lines = []
    for p in paths:
        pts = [(c[0], c[1]) for c in p]
        line = []
        for a, b in zip(pts, pts[1:]):
            c = clip_segment(a, b, ext)
            if c is None:
                if line:
                    lines.append(line)
                    line = []
                continue
            if not line:
                line.append(c[0])
            line.append(c[1])
        if line:
            lines.append(line)
    lines = [l for l in lines if len(l) >= 2]
    return lines


def haversine_miles(a, b):
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h)) * 0.6213711922


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    for kind, base, fields, out_name in (
            ("OHV", OHV_FS, OHV_FIELDS, "atv-chapter.geojson"),
            ("snowmobile", SNOW_FS, SNOW_FIELDS, "snow-chapter.geojson")):
        raw = query_fs(base, fields)
        print("%s features in envelope: %d" % (kind, len(raw)))
        feats, skipped, miles = [], 0, 0.0
        for f in raw:
            paths = (f.get("geometry") or {}).get("paths", [])
            lines = clip_paths(paths, EXT)
            if not lines:
                skipped += 1
                continue
            for line in lines:
                miles += sum(haversine_miles(line[i], line[i + 1])
                             for i in range(len(line) - 1))
            geom = {"type": "LineString", "coordinates": lines[0]} if len(lines) == 1 \
                else {"type": "MultiLineString", "coordinates": lines}
            props = dict(f.get("attributes") or {})
            props["kind"] = "atv" if kind == "OHV" else "snow"
            feats.append({"type": "Feature", "properties": props,
                          "geometry": geom})
        out = {
            "type": "FeatureCollection",
            "metadata": {
                "dataset": ("Minnesota DNR %s trails clipped to the chapter "
                            "working extent" % kind),
                "source_service": base,
                "pulled_utc_date": pulled,
                "extent_wgs84": EXT,
                "features_in_envelope": len(raw),
                "features_kept": len(feats),
                "features_skipped_no_geometry_in_extent": skipped,
                "gis_miles_inside_extent": round(miles, 2),
                "miles_method": ("Geodesic (haversine) over segment portions "
                                 "clipped to the extent box."),
            },
            "features": feats,
        }
        path = os.path.join(REPO, "data", "motorized", out_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(out, fh)
        print("%s: %d kept, %d skipped, %.2f GIS miles -> %s"
              % (kind, len(feats), skipped, miles, path))


if __name__ == "__main__":
    main()

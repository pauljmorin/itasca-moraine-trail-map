#!/usr/bin/env python3
"""Pull the DNR motorized trails for the WHOLE STATE of Minnesota,
for the main chapter map's "Other trails" layer group.

Why this exists: Paul, Nov 16, 2026 — full state, not the 2-mile
corridor around the NCT (scripts/pull-motorized-mn-corridor.py)
and not the 5-mile clip mentioned first. Full state supersedes
both: the motorized layers now show every DNR OHV / snowmobile
trail in Minnesota, and the map user sees the statewide context
around the NCT. The corridor files stay on disk untouched.

Sources (live, same as the build-out viewer's build-motorized.py):
- Minnesota DNR OHV Trails, 2026 season:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0
- Minnesota Snowmobile Trails:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0

Method: two-pass fetch — id list first (where 1=1, no geometry
filter; a single envelope geometry query silently dropped
features on 2026-11-13), then fetch by objectIds in chunks of
500. No corridor clip, no geometry intersection: every feature
is whole, so the DNR `miles` field and the drawn length agree
except where the service itself splits a trail into segments.
No contact fields pulled (public_poc / public_pho / pocemail),
same as the build-out pull.

Split: the OHV layer carries both ATV and dirt-bike (OHM) use. A
feature goes to the ATV file when atv_class_1 or atv_class_2 is
'X', and to the OHM file when off_highway_motorcycle is 'X'. A
trail that allows both appears in both files — that is the honest
reading of the DNR data. (off_road_vehicle / 4x4 use is 3
features statewide in the chapter pull; those ride with the ATV
file.)

Expected counts (coordinator-verified Nov 16, 2026): OHV service
7,931 features statewide; snowmobile service 276 features.

Outputs (source of record; the viewer reads site/data/ copies):
- data/motorized/atv-mn-statewide.geojson
- data/motorized/ohm-mn-statewide.geojson
- data/motorized/snow-mn-statewide.geojson

Usage: python3 scripts/pull-motorized-mn-statewide.py
"""

import json
import os
import time
import urllib.parse

import requests
from pyproj import Transformer
from shapely.geometry import shape, mapping, LineString, MultiLineString

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

OHV_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
          "us_mn_state_dnr/trans_ohv_trails_mn/FeatureServer/0")
SNOW_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
           "us_mn_state_dnr/trans_snowmobile_trails_mn/FeatureServer/0")

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


def query_fs(base, fields):
    """All features in the service. Two passes: id list first,
    then fetch by objectIds in chunks of 500."""
    params = {"where": "1=1", "returnIdsOnly": "true", "f": "json"}
    url = base + "/query?" + urllib.parse.urlencode(params)
    ids = fetch_json(url).get("objectIds", [])
    print("%s: %d objectIds" % (base.split("/")[-2], len(ids)))
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
    raise ValueError("unsupported " + geom.geom_type)


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())

    def to_features(raw, kind, keep):
        feats, skipped, miles, field_miles = [], 0, 0.0, 0.0
        for f in raw:
            g = arcgis_geom_to_shapely(f.get("geometry") or {})
            if g is None or g.is_empty:
                skipped += 1
                continue
            props = dict(f.get("attributes") or {})
            if not keep(props):
                continue
            g_utm = project(g, TOUTM)
            for line in (g_utm.geoms if g_utm.geom_type == "MultiLineString"
                         else [g_utm]):
                miles += line.length / MI
            field_miles += props.get("miles") or 0
            props["kind"] = kind
            feats.append({"type": "Feature", "properties": props,
                          "geometry": mapping(g)})
        return feats, skipped, miles, field_miles

    jobs = [
        ("OHV/ATV", OHV_FS, OHV_FIELDS, "atv-mn-statewide.geojson", "atv",
         lambda p: p.get("atv_class_1") == "X" or p.get("atv_class_2") == "X"),
        ("OHV/OHM", OHV_FS, OHV_FIELDS, "ohm-mn-statewide.geojson", "ohm",
         lambda p: p.get("off_highway_motorcycle") == "X"),
        ("snowmobile", SNOW_FS, SNOW_FIELDS, "snow-mn-statewide.geojson", "snow",
         lambda p: True),
    ]
    cache = {}
    for label, base, fields, out_name, kind, keep in jobs:
        if base not in cache:
            cache[base] = query_fs(base, fields)
        feats, skipped, miles, field_miles = to_features(
            cache[base], kind, keep)
        out = {
            "type": "FeatureCollection",
            "metadata": {
                "dataset": ("Minnesota DNR %s trails — FULL STATE, no "
                            "corridor clip (Paul, Nov 16, 2026)" % label),
                "source_service": base,
                "scope": ("Statewide. Supersedes the 2-mile NCT "
                          "corridor pull (pull-motorized-mn-corridor.py) "
                          "and the 5-mile clip idea; the corridor files "
                          "stay on disk."),
                "pulled_utc_date": pulled,
                "features_in_service": len(cache[base]),
                "features_kept": len(feats),
                "features_skipped_no_geometry": skipped,
                "gis_miles_measured": round(miles, 2),
                "miles_field_sum": round(field_miles, 2),
                "miles_method": ("Whole features measured in UTM 15N "
                                 "(EPSG:26915); no clipping, so field "
                                 "and drawn miles agree except where the "
                                 "service itself splits a trail."),
            },
            "features": feats,
        }
        path = os.path.join(REPO, "data", "motorized", out_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(out, fh)
        print("%s: %d kept, %d skipped, %.2f GIS miles "
              "(field %.2f) -> %s"
              % (label, len(feats), skipped, miles, field_miles, path))


if __name__ == "__main__":
    main()

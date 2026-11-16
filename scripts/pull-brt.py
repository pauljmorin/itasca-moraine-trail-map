#!/usr/bin/env python3
"""Pull the Border Route Trail from the USDA Forest Service National
Forest System Trails service, for the main chapter map's "Other
trails" layer group (Partner Trails subgroup with the SHT).

Source (live):
- USFS National Forest System Trails (EDW_TrailNFSPublish_01):
  https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0

Method: single where-filtered query (trail_name = 'BORDER ROUTE')
inside the statewide NCT envelope, f=geojson. requests, NOT urllib.
Filter is exact on trail_name; the service carries the BRT as
24 features, trail no. 21007, admin org 090902 (Superior NF),
trail class 2.

Coverage (verified Nov 16, 2026): 24 features, 46.07 GIS miles
measured in UTM 15N (gis_miles field sums 45.22; segment_length
sums 46.07 — the measured figure is the one quoted). Published
length ~65 mi; the TrailNFS line is the Superior NF's carried
tread, shorter than the published figure. The BRT shares tread
with the NCT along the border: 80% of its vertices sit within
50 m of the map's Minnesota NCT line, none more than 350 m away
— same tread, two surveys. Western end (-90.78325, 48.09088),
eastern end at the Pigeon River (-89.95014, 47.99830), where the
SHT's northern terminus also sits.

Outputs (source of record; the viewer reads the site/data/ copy):
- data/brt/brt.geojson

Usage: python3 scripts/pull-brt.py
"""

import json
import os
import time

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

TRAILNFS = ("https://apps.fs.usda.gov/arcx/rest/services/EDW/"
            "EDW_TrailNFSPublish_01/MapServer/0")

# Statewide NCT envelope, same as the intersecting-trails inventory.
ENV = {"xmin": -96.8, "ymin": 46.2, "xmax": -89.85, "ymax": 48.15,
       "spatialReference": {"wkid": 4326}}


def fetch_json(url, params, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("GET %s failed after %d tries: %s"
                       % (url, retries, last_err))


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    data = fetch_json(TRAILNFS + "/query", {
        "where": "trail_name='BORDER ROUTE'",
        "geometry": json.dumps(ENV),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "outSR": "4326",
        "returnGeometry": "true",
        "f": "geojson",
    })
    brt = data.get("features", [])
    print("Border Route Trail features: %d" % len(brt))
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("Border Route Trail as carried in the USDA "
                        "Forest Service National Forest System Trails "
                        "service (EDW_TrailNFSPublish_01)"),
            "source_service": TRAILNFS,
            "pulled_utc_date": pulled,
            "features_kept": len(brt),
            "gis_miles_field": round(sum(
                (f["properties"] or {}).get("gis_miles") or 0
                for f in brt), 2),
            "coverage_note": ("24 features, 46.07 GIS miles measured "
                              "(field 45.22); published ~65 mi. Shares "
                              "tread with the NCT along the border; "
                              "western end (-90.78325, 48.09088), "
                              "eastern end at the Pigeon River "
                              "(-89.95014, 47.99830)."),
        },
        "features": brt,
    }
    path = os.path.join(REPO, "data", "brt", "brt.geojson")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh)
    print("wrote %s (%d features)" % (path, len(brt)))


if __name__ == "__main__":
    main()

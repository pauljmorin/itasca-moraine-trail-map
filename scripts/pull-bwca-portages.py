#!/usr/bin/env python3
"""Pull the 26 BWCAW portages and connectors from the USDA Forest
Service National Forest System Trails service, for the main chapter
map's "Other trails" layer group (one light layer, id
"bwca-portages").

Source (live):
- USFS National Forest System Trails (EDW_TrailNFSPublish_01):
  https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0

Method: single where-filtered query (trail_name IN (...)) inside
the statewide NCT envelope, f=geojson. requests, NOT urllib.
The name list is the 26-member group row from the
intersecting-trails inventory (docs/nct-intersecting-trails-
minnesota-2026-11-16.md, section G). Names are the TrailNFS
trail_name values exactly as the service carries them
(uppercase) — three differ from the inventory's spellings:
'BRT-CLEARWATER LK CAMPSITE TRL' (inventory: "BRT–Clearwater
Lake Campsite"), 'BRT-PARTIDGE CAMPSITE' (inventory:
"BRT–Partridge Campsite" — the service spells it PARTIDGE,
a USFS typo kept as-is), and 'CLEARWATER/DANIELS LAKE'
(inventory: "Clearwater / Daniels Lake" — the service joins
the two lake names with a slash, no spaces).

These are portages, not hiking trails — short lake-to-lake
portages and campsite spurs, 0.03–3.67 mi each, along the
Border Route / BWCAW tread. The inventory verified each one
meets the NCT at 0–44.7 m. They are their own layer, OFF by
default, drawn light (thin, dashed, stone) so they read as
portages and do not clutter the hiking trails.

Outputs (source of record; the viewer reads the site/data/ copy):
- data/bwca-portages/bwca-portages.geojson

Usage: python3 scripts/pull-bwca-portages.py
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

# TrailNFS trail_name values, exactly as the service carries them.
NAMES = [
    "AGAMOK-MUELLER", "BORDER ROUTE CONNECTOR",
    "BRT-CLEARWATER LK CAMPSITE TRL", "BRT-PARTIDGE CAMPSITE",
    "BRT-SOCK LAKE CAMPSITE", "TOPPER LAKE CAMPSITE SPUR",
    "CLEARWATER-WEST PIKE", "CLEARWATER/DANIELS LAKE",
    "CRAB LAKE CUT-OFF", "CRAB LAKE-MAIN BRT",
    "FAY-WARCLUB", "GLEE-BINGSHICK", "GLEE-FAY",
    "HATCHET CREEK-HATCHET POND", "KOBE-THOMAS",
    "MOUNTAIN-CLEARWATER", "ROSE-DUNCAN", "ROSE-ROVE",
    "SOUTH LAKE", "SOUTH LAKE-TOPPER LAKE",
    "WARCLUB-SEAHORSE", "WEST PIKE-PINE", "WOOD LAKE",
    "SOURDOUGH CREEK", "FERNBERG AREA", "KEKEKABIC-STRUP",
]


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
    where = "trail_name IN ('" + "','".join(NAMES) + "')"
    data = fetch_json(TRAILNFS + "/query", {
        "where": where,
        "geometry": json.dumps(ENV),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "outSR": "4326",
        "returnGeometry": "true",
        "f": "geojson",
    })
    feats = data.get("features", [])
    print("BWCAW portage features: %d" % len(feats))
    from collections import Counter
    print(Counter((f["properties"] or {}).get("trail_name")
                  for f in feats))
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("BWCAW portages and connectors as carried in "
                        "the USDA Forest Service National Forest "
                        "System Trails service "
                        "(EDW_TrailNFSPublish_01)"),
            "source_service": TRAILNFS,
            "pulled_utc_date": pulled,
            "trail_names": NAMES,
            "features_kept": len(feats),
            "coverage_note": ("26 named portages/connectors, 0.03-3.67 "
                              "mi each, along the Border Route / BWCAW "
                              "tread; each verified meeting the NCT at "
                              "0-44.7 m (inventory section G). Three "
                              "TrailNFS spellings kept as-is: "
                              "'BRT-CLEARWATER LK CAMPSITE TRL', "
                              "'BRT-PARTIDGE CAMPSITE', and "
                              "'CLEARWATER/DANIELS LAKE'."),
        },
        "features": feats,
    }
    path = os.path.join(REPO, "data", "bwca-portages",
                        "bwca-portages.geojson")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh)
    print("wrote %s (%d features)" % (path, len(feats)))


if __name__ == "__main__":
    main()

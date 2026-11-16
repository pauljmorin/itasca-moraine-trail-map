#!/usr/bin/env python3
"""Pull the named trails near the Border Route Trail and the Superior
Hiking Trail from the USDA Forest Service National Forest System
Trails service, for the main chapter map's "Other trails" layer
group (one layer, id "near-brt-sht").

Source (live):
- USFS National Forest System Trails (EDW_TrailNFSPublish_01):
  https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0

Method: single where-filtered query (trail_name IN (...)) inside
the statewide NCT envelope, f=geojson. requests, NOT urllib.
The name list is the Superior NF / BWCAW set from the
intersecting-trails inventory (docs/nct-intersecting-trails-
minnesota-2026-11-16.md, sections A and F): every named trail
there that meets the NCT in the Arrowhead — 28 names. Names are
the TrailNFS trail_name values exactly as the service carries
them (uppercase).

Membership, measured Nov 16, 2026 (distance from each trail's
geometry to the BRT line, UTM 15N):
- 13 touch the BRT tread directly (0 m): Bridal Veil Falls,
  Caribou Rock, Gunflint Lake G Connect, Magnetic Rock, South
  Fowl Snowmobile, Upper Gunflint Aspen Rabbit, Cut Across,
  Lonely Lake, Overlook, Power Line, Short Cut, South Rim,
  West End.
- 3 meet the NCT within ~700 m of the BRT line (Bryce Breon
  230 m, Upper Gunflint Warrens Road 267 m, South Fowl ATV
  687 m) — inside the disagreement between the NCT line and
  the BRT line for the same tread.
- 4 meet the NCT just west of the BRT's western end, within
  ~4 km (Centennial 2,991 m, Kekekabic 3,038 m, Kekekabic to
  Magnetic Rock 3,105 m, Gunflint Lookout 3,837 m). The
  Kekekabic is the BRT's western connector; its drawn line
  stops ~3 km short of the BRT line.
- 8 meet the NCT further west on the Arrowhead approach
  (Ely / BWCAW), 38–60+ km from the BRT line: Benezie–
  Becoosin Loop, Old Pines Loop, Snowbank, Thomas Lake Winter,
  Hidden Valley Trezona, Trezona, Madden Winter, Thirteen
  Corners. They are in the layer because they are the
  Arrowhead-corner trails on the NCT's approach to the BRT,
  not because they touch the BRT itself — the popup says what
  each trail meets.
Nearest any of them comes to the SHT line is 7.2 km (South
Fowl ATV); no inventory trail meets the SHT itself — the SHT
meets the NCT only at its northern terminus, on the BRT tread.

NOT in this layer: the Upper Gunflint near-misses (Amperage,
North Star, Big Pine, Rabbit Run, Highlands, Connector, Aspen
Alley, Ham Lake, Little Pine, River — 100–300 m from the NCT,
inventory-verified as not meeting it); the Gunflint Snowmobile
Trail (52.7 m, just outside the inventory's 50 m tolerance,
unverified); the 26 BWCAW portages (their own layer,
scripts/pull-bwca-portages.py).

Outputs (source of record; the viewer reads the site/data/ copy):
- data/near-brt-sht/near-brt-sht.geojson

Usage: python3 scripts/pull-near-brt-sht.py
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
    "KEKEKABIC", "SNOWBANK", "OLD PINES LOOP",
    "BENEZIE-BECOOSIN LOOP", "MAGNETIC ROCK", "CARIBOU ROCK",
    "BRIDAL VEIL FALLS", "BRYCE BREON", "CENTENNIAL",
    "GUNFLINT LOOKOUT", "KEKEKABIC TO MAGNETIC ROCK",
    "UPPER GUNFLINT WEST END", "UPPER GUNFLINT SOUTH RIM",
    "UPPER GUNFLINT OVERLOOK", "UPPER GUNFLINT CUT ACROSS",
    "UPPER GUNFLINT ASPEN RABBIT", "UPPER GUNFLINT POWER LINE",
    "UPPER GUNFLINT LONELY LAKE", "UPPER GUNFLINT SHORT CUT",
    "UPPER GUNFLINT WARRENS ROAD", "GUNFLINT LAKE G CONNECT",
    "SOUTH FOWL ATV", "SOUTH FOWL SNOWMOBILE",
    "THOMAS LAKE WINTER", "THIRTEEN CORNERS", "MADDEN WINTER",
    "HIDDEN VALLEY TREZONA", "TREZONA",
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
    print("near-BRT/SHT features: %d" % len(feats))
    from collections import Counter
    print(Counter((f["properties"] or {}).get("trail_name")
                  for f in feats))
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("Named trails near the Border Route Trail and "
                        "the Superior Hiking Trail, as carried in the "
                        "USDA Forest Service National Forest System "
                        "Trails service (EDW_TrailNFSPublish_01)"),
            "source_service": TRAILNFS,
            "pulled_utc_date": pulled,
            "trail_names": NAMES,
            "features_kept": len(feats),
            "coverage_note": ("28 named trails, 113.69 GIS miles "
                              "measured. 13 touch the BRT tread (0 m); "
                              "3 within ~700 m; 4 within ~4 km west of "
                              "the BRT's western end; 8 on the Arrowhead "
                              "approach 38-60+ km from the BRT line. "
                              "Nearest to the SHT line 7.2 km (South "
                              "Fowl ATV). See the script header for the "
                              "full membership table."),
        },
        "features": feats,
    }
    path = os.path.join(REPO, "data", "near-brt-sht",
                        "near-brt-sht.geojson")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh)
    print("wrote %s (%d features)" % (path, len(feats)))


if __name__ == "__main__":
    main()

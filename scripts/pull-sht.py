#!/usr/bin/env python3
"""Pull the Superior Hiking Trail from the Minnesota DNR state park
trails service, for the main chapter map's "Other trails" layer group.

Source (live):
- Minnesota DNR State Park Trails and Roads:
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_park_trails_roads/FeatureServer/0

Method: two-pass fetch copied from scripts/pull-motorized-mn-corridor.py —
id list first (a single envelope geometry query silently dropped features
there), then fetch by objectIds in chunks of 500. requests, NOT urllib:
the enterprise host drops urllib requests (RemoteDisconnected, Nov 16).
Filter: trail_name == 'Superior Hiking Trail' only.

Coverage (verified Nov 16): the DNR park file carries 553 SHT features
totalling 207.56 GIS miles — the portions inside Minnesota state parks,
about 67% of the ~310 mi published trail. It does NOT include the
southern terminus approach (Jay Cooke State Park; the file's southernmost
point sits 7,552 m from the NCT line, while the trail's true southern
terminus is 936 m away). The line DOES touch the NCT at the northern
terminus: 0 m at (-89.93524, 47.98833), the 270-degree Overlook near
Grand Portage. One source segment (objectid 383) runs ~1.2 km north past
that terminus; it is left in the file as the service carries it.

2026-11-16 run note: the live service was DOWN at wiring time (HTTP 502
then 504 from the Azure Application Gateway, three attempts plus a
retry after the other wiring jobs). The first file was built instead from
/tmp/nct-trails/dnr_park_trails-0.geojson — the intersecting-trails
inventory's raw pull of the SAME service, Nov 16 13:48 UTC, verified
independently before use (1,996 features, exactly the service's count;
SHT lengthmile sum 145.94 mi = measured GIS miles in UTM 15N; northern
terminus touch 0 m). The live re-run at 08:25 CST the same morning
succeeded and SUPERSEDED it: 553 features, 207.56 mi (measured 207.29),
all 287 earlier features contained, no duplicate objectids — the
inventory's raw file was evidently a partial pull. The file below is
the live pull.

Outputs (source of record; the viewer reads the site/data/ copy):
- data/sht/sht.geojson

Usage: python3 scripts/pull-sht.py
"""

import json
import os
import time
import urllib.parse

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

PARK_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
           "us_mn_state_dnr/trans_state_park_trails_roads/FeatureServer/0")

# Statewide envelope, same as the intersecting-trails inventory pull.
ENV = {"xmin": -96.8, "ymin": 46.2, "xmax": -89.85, "ymax": 48.15,
       "spatialReference": {"wkid": 4326}}


def fetch_json(url, retries=3):
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


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    params = {
        "where": "1=1",
        "geometry": json.dumps(ENV),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "json",
    }
    ids = fetch_json(PARK_FS + "/query?" + urllib.parse.urlencode(params)
                     ).get("objectIds", [])
    print("park-trails features in envelope: %d" % len(ids))
    raw = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {
            "objectIds": ",".join(str(x) for x in chunk),
            "outFields": "*",
            "outSR": "4326",
            "returnGeometry": "true",
            "f": "geojson",
        }
        raw.extend(fetch_json(PARK_FS + "/query?"
                              + urllib.parse.urlencode(params)
                              ).get("features", []))
    print("fetched: %d features" % len(raw))
    sht = [f for f in raw
           if (f.get("properties") or {}).get("trail_name")
           == "Superior Hiking Trail"]
    print("Superior Hiking Trail features: %d" % len(sht))
    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("Superior Hiking Trail as carried in the Minnesota "
                        "DNR State Park Trails and Roads service — the "
                        "portions inside Minnesota state parks"),
            "source_service": PARK_FS,
            "pulled_utc_date": pulled,
            "features_in_service_envelope": len(raw),
            "features_kept": len(sht),
            "gis_miles": round(sum((f["properties"] or {}).get("lengthmile") or 0
                                   for f in sht), 2),
            "coverage_note": ("DNR park file only: ~146 of ~310 published "
                              "miles. Southern terminus approach (Jay Cooke) "
                              "not in the service; line touches the NCT at "
                              "the northern terminus, 0 m at (-89.93524, "
                              "47.98833)."),
        },
        "features": sht,
    }
    path = os.path.join(REPO, "data", "sht", "sht.geojson")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh)
    print("wrote %s (%d features)" % (path, len(sht)))


if __name__ == "__main__":
    main()

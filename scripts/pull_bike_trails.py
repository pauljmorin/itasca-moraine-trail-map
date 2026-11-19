#!/usr/bin/env python3
"""Pull bike trails for the main chapter map's "Other trails" layer group.

Why this exists: Paul, Nov 18, 2026 — bike trails showed only on the
base maps, never as their own toggleable layer. This builds one,
grouped with the motorized layers (ATV, dirt bike, snowmobile).

Sources (live Nov 18, 2026):
- Minnesota DNR State Trails, `use_bike = 1` (paved multi-use state
  trails that allow biking):
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/trans_state_trails_minnesota/FeatureServer/0
  364 features statewide, 29 named trails. Full state, like the
  motorized layers (Paul, Nov 16, 2026) — no corridor clip, so the
  DNR `lengthmile` field and the drawn length agree except where
  the service itself splits a trail into segments.
- Mesabi Trail (regional, Grand Rapids -> Ely, ~145 mi finished):
  NOT in the DNR service (0 features match "Mesabi") and NOT
  reachable from an authoritative GIS service here — MnDOT's
  BIKEWAY FeatureServer
  (webgis.dot.state.mn.us/65agsf1/rest/services/sdw_trans/BIKEWAY/FeatureServer)
  is WAF-blocked from this environment (HTTP 200 + "Request
  Rejected", support IDs 7888479202558097992 / ...008) and its
  MnGeo mirror (trans_bikeway) is token-gated (499). The trail
  authority (St. Louis & Lake Counties Regional Railroad
  Authority, mesabitrail.com) publishes a paper/PDF map only, no
  GIS download. So the Mesabi geometry comes from OpenStreetMap
  (ways named "Mesabi Trail", harvested via Nominatim + the OSM
  API — scripts/harvest_mesabi_osm.py; Overpass is unreachable
  from this environment, 406 on every mirror), labeled as such
  on every feature and in the popup — source, not authority. The Mesabi is the one bike trail the NCT gap line
  itself follows east of Grand Rapids, so leaving it out would
  have left the layer's most corridor-relevant trail missing.

What is NOT in the layer (deliberate, recorded in SOURCES.md):
- Mountain-bike-only singletrack (use_mntbik = 1 AND use_bike = 0):
  368 features statewide, e.g. the Cuyuna Lakes mountain-bike
  system. Different use class, mostly inside state parks/forests;
  add as a second layer if Paul wants it.
- The Blue Ox State Trail (unpaved, motorized; use_bike = 0) and
  the "OHV access to Taconite State Trail via USFS Rd 11404"
  spur (use_bike = 0) — not bike trails in this service's terms.
- Every other MnDOT bikeway (on-road shoulders, bike lanes,
  county bikeways maps): no reachable GIS here; the BIKEWAY
  service is blocked (above). The layer is trails, not the
  on-road bike network.

Method: DNR two-pass fetch — id list first (where use_bike=1),
then fetch by objectIds in chunks of 500, following
scripts/pull-motorized-mn-statewide.py. OSM Mesabi members are
read from the Overpass JSON saved alongside this script run
(/tmp/mesabi-osm.json at pull time) and converted to LineString
features with kind "mesabi-osm". Whole features measured in
UTM 15N (EPSG:26915).

Outputs (source of record; the viewer reads the site/data/ copy):
- data/bike/bike-mn-statewide.geojson
- site/data/bike-trails.geojson (byte-identical copy)

Usage: python3 scripts/pull_bike_trails.py
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

DNR_FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
          "us_mn_state_dnr/trans_state_trails_minnesota/FeatureServer/0")

TOUTM = Transformer.from_crs("EPSG:4326", "EPSG:26915", always_xy=True)
MI = 1609.34

DNR_FIELDS = ["objectid", "trail_name", "prgm_prj", "alt_name", "use_bike",
              "use_mntbik", "use_inline", "use_hike", "surfacetyp",
              "width", "lengthmile"]

OSM_PATH = "/tmp/mesabi-osm.json"


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


def query_dnr():
    """All DNR state-trail features with use_bike = 1. Two passes."""
    params = {"where": "use_bike=1", "returnIdsOnly": "true", "f": "json"}
    url = DNR_FS + "/query?" + urllib.parse.urlencode(params)
    ids = fetch_json(url).get("objectIds", [])
    print("DNR state trails use_bike=1: %d objectIds" % len(ids))
    out = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        params = {
            "objectIds": ",".join(str(x) for x in chunk),
            "outFields": ",".join(DNR_FIELDS),
            "outSR": "4326",
            "returnGeometry": "true",
            "f": "json",
        }
        url = DNR_FS + "/query?" + urllib.parse.urlencode(params)
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


def measure_miles(geom):
    g_utm = project(geom, TOUTM)
    if g_utm.geom_type == "MultiLineString":
        return sum(g.length for g in g_utm.geoms) / MI
    return g_utm.length / MI


def mesabi_from_osm():
    """Mesabi Trail from the OSM harvest (scripts/harvest_mesabi_osm.py):
    a FeatureCollection of way features, one per OSM way, with
    osm_way_id and surface. Each becomes one feature, kind
    "mesabi-osm", source "OpenStreetMap"."""
    if not os.path.exists(OSM_PATH):
        print("No OSM Mesabi file at %s — skipping Mesabi" % OSM_PATH)
        return [], 0
    d = json.load(open(OSM_PATH))
    feats = []
    for f in d.get("features", []):
        props = dict(f.get("properties") or {})
        props["kind"] = "mesabi-osm"
        props["source"] = "OpenStreetMap"
        props["trail_name"] = "Mesabi Trail"
        props["surface_type"] = props.get("surface")
        feats.append({"type": "Feature", "properties": props,
                      "geometry": f["geometry"]})
    print("OSM Mesabi: %d way features" % len(feats))
    return feats, 0


def main():
    pulled = time.strftime("%Y-%m-%d", time.gmtime())

    raw = query_dnr()
    feats, skipped, miles, field_miles = [], 0, 0.0, 0.0
    for f in raw:
        g = arcgis_geom_to_shapely(f.get("geometry") or {})
        if g is None or g.is_empty:
            skipped += 1
            continue
        props = dict(f.get("attributes") or {})
        props["kind"] = "dnr-state-trail"
        props["source"] = "Minnesota DNR State Trails"
        miles += measure_miles(g)
        field_miles += props.get("lengthmile") or 0
        feats.append({"type": "Feature", "properties": props,
                      "geometry": mapping(g)})
    print("DNR: %d kept, %d skipped, %.2f GIS miles (field %.2f)"
          % (len(feats), skipped, miles, field_miles))

    mesabi, mesabi_skipped = mesabi_from_osm()
    mesabi_miles = 0.0
    for f in mesabi:
        mesabi_miles += measure_miles(shape(f["geometry"]))
    feats.extend(mesabi)
    print("Mesabi OSM: %d features, %.2f GIS miles"
          % (len(mesabi), mesabi_miles))

    out = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": ("Bike trails — FULL STATE, no corridor clip "
                        "(Paul, Nov 18, 2026)"),
            "source_services": [
                DNR_FS + " (use_bike=1)",
                "OpenStreetMap ways named 'Mesabi Trail' "
                "(harvest_mesabi_osm.py: Nominatim + OSM API)",
            ],
            "scope": ("Statewide. Follows the motorized layers' "
                      "full-state precedent (Paul, Nov 16, 2026): "
                      "every DNR bike-allowed state trail in "
                      "Minnesota plus the Mesabi Trail from OSM."),
            "pulled_utc_date": pulled,
            "features_in_dnr_service_bike": len(raw),
            "features_kept_dnr": len(feats) - len(mesabi),
            "features_skipped_no_geometry_dnr": skipped,
            "features_mesabi_osm": len(mesabi),
            "features_mesabi_skipped": mesabi_skipped,
            "gis_miles_measured_dnr": round(miles, 2),
            "miles_field_sum_dnr": round(field_miles, 2),
            "gis_miles_measured_mesabi_osm": round(mesabi_miles, 2),
            "miles_method": ("Whole features measured in UTM 15N "
                             "(EPSG:26915); no clipping, so DNR field "
                             "and drawn miles agree except where the "
                             "service itself splits a trail."),
        },
        "features": feats,
    }
    work_path = os.path.join(REPO, "data", "bike", "bike-mn-statewide.geojson")
    os.makedirs(os.path.dirname(work_path), exist_ok=True)
    with open(work_path, "w") as fh:
        json.dump(out, fh)
    site_path = os.path.join(REPO, "site", "data", "bike-trails.geojson")
    with open(site_path, "w") as fh:
        json.dump(out, fh)
    print("TOTAL: %d features, %.2f GIS miles -> %s and %s"
          % (len(feats), miles + mesabi_miles, work_path, site_path))


if __name__ == "__main__":
    main()

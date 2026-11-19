#!/usr/bin/env python3
"""Pull Minnesota DNR state forest campgrounds along the full Minnesota
North Country Trail corridor.

Paul, Nov 18, 2026 (voice, GO): campgrounds are useful for hikers;
public water accesses are explicitly OUT (Paul: no-go on those) and
are not pulled here.

SOURCE: Minnesota DNR, struc_state_forest_campgrounds/FeatureServer
layer 0 (points) — "State Forest Campgrounds And Day Use Areas":
  https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/struc_state_forest_campgrounds/FeatureServer/0
Graded in docs/research-useful-layers-2026-11-11.md §2.1 (Grade A
public / C management; corridor count 6 in the chapter working extent,
Nov 11 envelope query) and in
docs/uofm-arrowhead-data-sources-audit-2026-11-18.md (verdict: Use —
authoritative, absent from the viewer). DNR data used under the
Minnesota DNR General Geographic Data License Agreement.

CORRIDOR: the statewide NCT line (site/data/trail-minnesota.geojson,
348 features) — a campground counts when its point is within 2 miles
(3,218.69 m) of the line, the same corridor as the timber layer and
the motorized clip. Distance computed in UTM 15N (shapely) and
recorded as dist_trail_km.

FILTERING (judgment, recorded): the service mixes campgrounds and
day-use areas in one layer (field site_type_gdrs). Included:
'Campground', 'Horse Campground', 'State Forest Campground and Day
Use Area' — all three are places to camp overnight. Excluded:
'State Forest Day Use Area' — day use only, no camping, and Paul's
GO was for campgrounds. No other filtering: no capacity or amenity
fields exist in this service (see FIELDS below), so nothing is
dropped for lack of facilities.

FIELDS carried (the service has no amenity/capacity fields — a DNR
state forest campground is rustic, first-come, minimal facilities;
that note is carried on the popup instead):
  facilty_name_gdrs -> name (as published; note the DNR spelling)
  site_type_gdrs    -> site_type
  state_forest_gdrs -> state_forest
  county_gdrs       -> county
  pat_admin_unit_gdrs -> admin_unit (Parks and Trails admin unit)
  dnr_region_gdrs   -> dnr_region
  dist_trail_km     -> computed distance to the trail line

OVERLAP: DNR campgrounds are a different manager with different
rules from the NCTA/chapter campsites already on the map (NCTA
Places / chapter-places / campsites-arrowhead / campsites-stn).
If a DNR campground falls within 100 m of an existing campsite
point, it is reported here and in SOURCES.md — both are kept, never
merged or dropped.

Output (source of record; the viewer reads the site/data/ copy
published by scripts/build_site_data.py, scoped build_one):
  data/points/dnr-campgrounds.geojson

Usage: python3 scripts/pull_dnr_campgrounds.py
"""

import json
import os
import time

import requests
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (itasca-moraine-trail-map data pull)"}

FS = ("https://enterprise.gisdata.mn.gov/aghost/rest/services/"
      "us_mn_state_dnr/struc_state_forest_campgrounds/FeatureServer/0")

FIELDS = ["objectid", "facilty_name_gdrs", "site_type_gdrs",
          "state_forest_gdrs", "county_gdrs", "pat_admin_unit_gdrs",
          "dnr_region_gdrs"]

# Campground site types (see FILTERING note above); day-use-only
# types are excluded.
INCLUDE_TYPES = {"Campground", "Horse Campground",
                 "State Forest Campground and Day Use Area"}

MN_LINE = os.path.join(REPO, "site", "data", "trail-minnesota.geojson")
BUFFER_M = 3218.69  # 2 miles, same corridor as timber / motorized
OUT = os.path.join(REPO, "data", "points", "dnr-campgrounds.geojson")

TOUTM = Transformer.from_crs("EPSG:4326", "EPSG:26915", always_xy=True)
TO4326 = Transformer.from_crs("EPSG:26915", "EPSG:4326", always_xy=True)


def fetch_json(url, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 — retry then raise
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err


def fetch_all():
    out = []
    offset = 0
    while True:
        url = (FS + "/query?where=1%3D1&outFields=" +
               "%2C".join(FIELDS) +
               "&returnGeometry=true&outSR=4326&f=json"
               "&orderByFields=objectid&resultOffset=%d"
               "&resultRecordCount=1000" % offset)
        d = fetch_json(url)
        feats = d.get("features", [])
        out.extend(feats)
        if len(feats) < 1000:
            break
        offset += len(feats)
    return out


def clean_str(v):
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def main():
    with open(MN_LINE) as f:
        line = json.load(f)
    from shapely.geometry import LineString, MultiLineString
    utm_parts = []
    for feat in line["features"]:
        geom = feat["geometry"]
        if geom["type"] == "LineString":
            utm_parts.append(LineString(
                [TOUTM.transform(x, y) for x, y in geom["coordinates"]]))
        elif geom["type"] == "MultiLineString":
            utm_parts.append(MultiLineString([
                [TOUTM.transform(x, y) for x, y in part]
                for part in geom["coordinates"]]))
    trail_utm = unary_union(utm_parts)

    raw = fetch_all()
    print("fetched statewide: %d" % len(raw))

    kept = []
    excluded_type = []
    excluded_dist = []
    for feat in raw:
        a = feat["attributes"]
        stype = clean_str(a.get("site_type_gdrs"))
        if stype not in INCLUDE_TYPES:
            excluded_type.append((a.get("facilty_name_gdrs"), stype))
            continue
        geom = feat.get("geometry")
        if not geom:
            excluded_dist.append((a.get("facilty_name_gdrs"), "no geometry"))
            continue
        lon, lat = geom["x"], geom["y"]
        x, y = TOUTM.transform(lon, lat)
        dist_m = Point(x, y).distance(trail_utm)
        if dist_m > BUFFER_M:
            excluded_dist.append((a.get("facilty_name_gdrs"),
                                  "%.2f km from trail" % (dist_m / 1000.0)))
            continue
        kept.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": clean_str(a.get("facilty_name_gdrs")),
                "site_type": stype,
                "state_forest": clean_str(a.get("state_forest_gdrs")),
                "county": clean_str(a.get("county_gdrs")),
                "admin_unit": clean_str(a.get("pat_admin_unit_gdrs")),
                "dnr_region": clean_str(a.get("dnr_region_gdrs")),
                "dist_trail_km": round(dist_m / 1000.0, 2),
            },
        })

    kept.sort(key=lambda f: (f["properties"]["state_forest"] or "",
                             f["properties"]["name"] or ""))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"type": "FeatureCollection", "features": kept}, f,
                  separators=(",", ":"))
    print("kept in corridor: %d" % len(kept))
    for feat in kept:
        p = feat["properties"]
        print("  %s — %s (%s), %s Co., %.2f km"
              % (p["name"], p["site_type"], p["state_forest"],
                 p["county"], p["dist_trail_km"]))
    print("excluded by site_type (not campgrounds): %d" % len(excluded_type))
    for name, stype in excluded_type:
        print("  %s — %s" % (name, stype))
    print("excluded by distance (>2 mi from trail): %d" % len(excluded_dist))
    for name, why in excluded_dist:
        print("  %s — %s" % (name, why))

    # Overlap check vs existing campsite points (kept separate by
    # design — report coincidences, never merge or drop).
    for src in ("site/data/chapter-places.geojson",
                "site/data/campsites-arrowhead.geojson",
                "site/data/campsites-stn.geojson"):
        path = os.path.join(REPO, src)
        if not os.path.exists(path):
            print("overlap check: %s missing, skipped" % src)
            continue
        with open(path) as f:
            existing = json.load(f)["features"]
        for feat in kept:
            lon, lat = feat["geometry"]["coordinates"]
            x, y = TOUTM.transform(lon, lat)
            pt = Point(x, y)
            for e in existing:
                g = e["geometry"]
                if g["type"] != "Point":
                    continue
                ex, ey = TOUTM.transform(*g["coordinates"])
                d = pt.distance(Point(ex, ey))
                if d <= 100:
                    print("OVERLAP (within %.0f m): DNR %s <-> %s %s"
                          % (d, feat["properties"]["name"], src,
                             e["properties"].get("name")))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()

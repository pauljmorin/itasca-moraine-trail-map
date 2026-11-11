#!/usr/bin/env python3
"""Pull the NCTA Minnesota half-mile points (state mile markers) from
the NCTA ArcGIS organisation and clip them to the chapter working
extent.

Data source (see SOURCES.md): the service "mn_halfmile_points" on the
same ArcGIS organisation as the official line (NCTA), layer 0
"halfmile_mn" — "Mileage Index for the North Country Trail in
Minnesota": a point every half mile along the Minnesota NCT.
`index_` flags whole miles ("Index") vs half miles ("Interval");
`ident` carries the state reckoning ("MN-187", "MN-187.5");
`wypnt_id` carries the bare number ("187", "187.5").

WARNING — CORRUPT ATTRIBUTE COLUMNS: the service's `lat` / `long`
ATTRIBUTE columns are wrong (the longitude attribute duplicates the
latitude value). They are never read here: this script requests only
ident / index_ / wypnt_id as attributes and takes positions solely
from the returned GeoJSON GEOMETRY, requested with outSR=4326 so the
service itself converts its stored UTM (zone 15N) coordinates. Do
not "fix" this script by reading the attribute columns.

Method follows pull_points.py: envelope selection over the chapter
working extent, features fetched BY OBJECT ID in chunk-verified
chunks (offset paging on these hosts has silently truncated before).

Output: data/points/mile-markers.geojson (working data, unsnapped).
The site build (scripts/build_site_data.py) snaps these to the
depicted lines (<= 250 m) and emits site/data/milemarkers.geojson;
points that do not snap follow an authorised route the map does not
draw and are excluded there, with the count printed.

Note the mileage reckoning: these are STATE (NCTA) miles. The
chapter tracker's "NCT Mile Virtual Markers" run ~46-48 miles higher
over the same ground. The two reckonings are never merged or
converted — see docs/cartography-notes-2026-11-10.md, Part 3 (M3).

Usage:  python3 scripts/pull_mile_markers.py
No credentials required; the service is public.
"""

import json
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
OUT_PATH = REPO_ROOT / "data" / "points" / "mile-markers.geojson"

SERVICE_ROOT = ("https://services2.arcgis.com/UfGVyqUm4GHa2zrj"
                "/arcgis/rest/services/mn_halfmile_points/FeatureServer")
LAYER_ID = 0
OUT_FIELDS = "ident,index_,wypnt_id"  # never lat/long — see header
ID_CHUNK = 500


def get_json(url, params=None, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last_err}")


def fetch_chunk(layer_url, oid_field, ids):
    """Fetch features for one chunk of object ids; verify the count
    and split the chunk if the server returns fewer than asked."""
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {
        "where": where,
        "outFields": OUT_FIELDS,
        "outSR": "4326",
        "f": "geojson",
        "returnGeometry": "true",
    }
    data = get_json(f"{layer_url}/query", params=params)
    feats = data.get("features", [])
    if len(feats) != len(ids):
        if len(ids) == 1:
            raise RuntimeError(
                f"Feature {ids[0]} could not be fetched from {layer_url}")
        mid = len(ids) // 2
        return fetch_chunk(layer_url, oid_field, ids[:mid]) + fetch_chunk(
            layer_url, oid_field, ids[mid:])
    return feats


def page_layer(layer_url, envelope):
    """Fetch all features intersecting the envelope, by object id."""
    params = {
        "where": "1=1",
        "geometry": json.dumps({**envelope,
                                "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "returnIdsOnly": "true",
        "f": "json",
    }
    data = get_json(f"{layer_url}/query", params=params)
    ids = sorted(data.get("objectIds") or [])
    oid_field = data.get("objectIdFieldName", "objectid")
    feats = []
    for i in range(0, len(ids), ID_CHUNK):
        feats.extend(fetch_chunk(layer_url, oid_field, ids[i:i + ID_CHUNK]))
    return feats


def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def mile_number(ident, wypnt_id):
    """The bare state-mile number as a float, from ident ('MN-187.5')
    or wypnt_id ('187.5'); None if neither parses."""
    for v in (wypnt_id, ident):
        s = clean_str(v)
        if s is None:
            continue
        s = s.replace("MN-", "").replace("MN", "").strip()
        try:
            return float(s)
        except ValueError:
            continue
    return None


def clean_feature(f):
    p = f.get("properties") or {}
    geom = f.get("geometry") or {}
    coords = geom.get("coordinates")
    if not coords:
        return None  # no geometry fallback — attribute lat/long are corrupt
    ident = clean_str(p.get("ident"))
    num = mile_number(ident, p.get("wypnt_id"))
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [round(float(coords[0]), 6),
                            round(float(coords[1]), 6)],
        },
        "properties": {
            "ident": ident,
            "index_": clean_str(p.get("index_")),
            "wypnt_id": clean_str(p.get("wypnt_id")),
            "mile": num,
        },
    }


def main():
    config = json.loads(CONFIG_PATH.read_text())
    ext = config["working_extent_wgs84"]
    envelope = {
        "xmin": ext["min_lon"], "ymin": ext["min_lat"],
        "xmax": ext["max_lon"], "ymax": ext["max_lat"],
    }
    layer_url = f"{SERVICE_ROOT}/{LAYER_ID}"
    meta = get_json(SERVICE_ROOT, params={"f": "pjson"})
    layer_meta = next((l for l in meta.get("layers", [])
                       if l["id"] == LAYER_ID), {})
    print(f"Mile layer          : id {LAYER_ID} - {layer_meta.get('name')} "
          f"({meta.get('serviceDescription', '')})")

    raw = page_layer(layer_url, envelope)
    print(f"Fetched (by obj id) : {len(raw)}")

    features = []
    dropped = 0
    for f in raw:
        cf = clean_feature(f)
        if cf is None:
            dropped += 1
            continue
        features.append(cf)
    features.sort(key=lambda f: (f["properties"]["mile"] is None,
                                 f["properties"]["mile"] or 0.0))
    wholes = sum(1 for f in features
                 if f["properties"]["index_"] == "Index")
    miles = [f["properties"]["mile"] for f in features
             if f["properties"]["mile"] is not None]
    print(f"Retained            : {len(features)} (dropped {dropped} "
          f"without geometry)")
    print(f"Whole / half        : {wholes} Index, "
          f"{len(features) - wholes} Interval")
    if miles:
        print(f"State-mile range    : {min(miles)} .. {max(miles)}")

    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "NCTA Minnesota half-mile points (state mile "
                       "markers), clipped to the chapter working extent",
            "source_service": SERVICE_ROOT,
            "source_layer_id": LAYER_ID,
            "source_layer_name": layer_meta.get("name"),
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "extent_wgs84": {
                "min_lon": ext["min_lon"], "max_lon": ext["max_lon"],
                "min_lat": ext["min_lat"], "max_lat": ext["max_lat"],
            },
            "clip_method": "Envelope selection (object-id fetch, "
                           "chunk-verified); positions from GeoJSON "
                           "geometry requested with outSR=4326",
            "corrupt_columns_warning": "The service's lat/long "
                           "ATTRIBUTE columns are corrupt (longitude "
                           "duplicates latitude) and were never read; "
                           "outFields was limited to ident, index_, "
                           "wypnt_id.",
            "reckoning_note": "State (NCTA) miles. The chapter "
                           "tracker's virtual markers differ by "
                           "roughly 46-48 miles; never merged (M3).",
            "feature_count": len(features),
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc, indent=1))
    print(f"Wrote               : {OUT_PATH.relative_to(REPO_ROOT)}")
    print("SUMMARY " + json.dumps({
        "features": len(features), "whole": wholes,
        "range": [min(miles), max(miles)] if miles else None,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

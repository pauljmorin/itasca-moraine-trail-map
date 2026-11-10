#!/usr/bin/env python3
"""Pull the NCTA public service's point layer (trail waypoints) and
clip it to the chapter's working extent.

Data source (see config/chapter.json and SOURCES.md): the same public
ArcGIS feature service as the official line ("North Country Trail
(Public)", NCTA on behalf of NPS), LAYER 1 "Point Data - Public" -
the waypoint layer behind the public map / FarOut: campsites,
parking, shelters, water, points of interest.

Method (standard library + requests only), following
pull_access_layers.py: features are selected with an envelope query
over the chapter working extent and fetched BY OBJECT ID
(returnIdsOnly first, then chunks of ids), with each chunk's
returned count verified against the chunk size (a short chunk is
split and retried) - offset-paged queries on these hosts have
silently truncated before, so paging is never trusted.

Properties are CLEANED for the working data (the raw layer carries
two dozen fields, several of them editing scaffolding): each output
feature keeps only
  name        waypointName
  type        wptType (Camping / Parking / POI / Shelter / Water)
  subtype     iconSet2 where meaningful (water, tenting, bridge,
              restrooms, ...), else null
  owner       owner (Federal / State), else null
  description descriptionText, else null
  chapter     chapter tag (ITM / LLC), else null
Blank strings and the literal string "None" are normalised to null.

The script also scans every waypoint name for mile-marker evidence
(names matching mile / marker / MP) and reports the hits explicitly:
the chapter's mileage currently exists only as tracker NCT-mile
ranges per section, and whether the national point layer holds any
on-the-ground mile markers is a standing question for the map's
design (a raw "MP" substring scan false-positives on Camp/Ramp/
Impoundment, so hits are printed verbatim for a human read).

Output: data/points/ncta-points.geojson

Usage:  python3 scripts/pull_points.py
No credentials required; the service is public.
"""

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
OUT_PATH = REPO_ROOT / "data" / "points" / "ncta-points.geojson"

ID_CHUNK = 500
MILE_NAME_RE = re.compile(r"mile|marker|MP", re.IGNORECASE)


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


def find_point_layer(service_meta):
    """Return (layer_id, layer_meta) for the point/waypoint layer."""
    candidates = [
        layer
        for layer in service_meta.get("layers", [])
        if layer.get("geometryType") == "esriGeometryPoint"
    ]
    if not candidates:
        raise RuntimeError("No point layers found in service.")
    for layer in candidates:
        if "point" in layer.get("name", "").lower():
            return layer["id"], layer
    return candidates[0]["id"], candidates[0]


def fetch_chunk(layer_url, oid_field, ids):
    """Fetch features for one chunk of object ids; verify the count
    and split the chunk if the server returns fewer than asked."""
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {
        "where": where,
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
        "returnGeometry": "true",
    }
    data = get_json(f"{layer_url}/query", params=params)
    feats = data.get("features", [])
    if len(feats) != len(ids):
        if len(ids) == 1:
            raise RuntimeError(f"Feature {ids[0]} could not be fetched from {layer_url}")
        mid = len(ids) // 2
        return fetch_chunk(layer_url, oid_field, ids[:mid]) + fetch_chunk(
            layer_url, oid_field, ids[mid:]
        )
    return feats


def page_layer(layer_url, envelope):
    """Fetch all features intersecting the envelope, by object id."""
    params = {
        "where": "1=1",
        "geometry": json.dumps({**envelope, "spatialReference": {"wkid": 4326}}),
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
        feats.extend(fetch_chunk(layer_url, oid_field, ids[i : i + ID_CHUNK]))
    return feats


def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "none":
        return None
    return s


def clean_feature(f):
    p = f.get("properties") or {}
    geom = f.get("geometry") or {}
    coords = geom.get("coordinates")
    if not coords:
        lon, lat = p.get("lon"), p.get("lat")
        if lon is None or lat is None:
            return None
        coords = [lon, lat]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [round(float(coords[0]), 6), round(float(coords[1]), 6)],
        },
        "properties": {
            "name": clean_str(p.get("waypointName")),
            "type": clean_str(p.get("wptType")),
            "subtype": clean_str(p.get("iconSet2")),
            "owner": clean_str(p.get("owner")),
            "description": clean_str(p.get("descriptionText")),
            "chapter": clean_str(p.get("chapter")),
        },
    }


def main():
    config = json.loads(CONFIG_PATH.read_text())
    src = config["data_sources"]["official_trail_line"]
    service_root = src["service_root"].rstrip("/")
    ext = config["working_extent_wgs84"]
    envelope = {
        "xmin": ext["min_lon"],
        "ymin": ext["min_lat"],
        "xmax": ext["max_lon"],
        "ymax": ext["max_lat"],
    }

    meta = get_json(service_root, params={"f": "pjson"})
    layer_id, layer_meta = find_point_layer(meta)
    layer_url = f"{service_root}/{layer_id}"
    print(f"Point layer         : id {layer_id} - {layer_meta.get('name')}")

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
    features.sort(key=lambda f: (f["properties"]["type"] or "", f["properties"]["name"] or ""))

    counts = Counter(f["properties"]["type"] for f in features)
    print(f"Retained            : {len(features)} (dropped {dropped} without geometry)")
    print(f"Counts by type      : {dict(counts)}")

    mile_hits = [
        f["properties"]["name"]
        for f in features
        if f["properties"]["name"] and MILE_NAME_RE.search(f["properties"]["name"])
    ]
    genuine = [
        n for n in mile_hits if re.search(r"\bmile\b|\bmarker\b|\bMP\b", n, re.IGNORECASE)
    ]
    print(f"Mile-marker scan    : {len(mile_hits)} raw regex hits, "
          f"{len(genuine)} genuine (word-boundary mile/marker/MP)")
    for n in mile_hits:
        print(f"  raw hit (verbatim): {n!r}")

    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "NCTA public waypoint points, clipped to the chapter working extent, properties cleaned",
            "source_service": service_root,
            "source_layer_id": layer_id,
            "source_layer_name": layer_meta.get("name"),
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "extent_wgs84": {
                "min_lon": ext["min_lon"],
                "max_lon": ext["max_lon"],
                "min_lat": ext["min_lat"],
                "max_lat": ext["max_lat"],
            },
            "clip_method": "Envelope selection (object-id fetch, chunk-verified); point geometries kept whole",
            "feature_count": len(features),
            "counts_by_type": dict(counts),
            "mile_marker_name_hits": genuine,
            "mile_marker_note": (
                "Names scanned with /mile|marker|MP/i. Raw substring hits are all "
                "Camp-/Ramp-/Impoundment-type words; word-boundary hits (genuine "
                "mile markers) are listed in mile_marker_name_hits."
            ),
        },
        "features": features,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc, indent=1))
    print(f"Wrote               : {OUT_PATH.relative_to(REPO_ROOT)}")
    print("SUMMARY " + json.dumps({
        "layer_id": layer_id,
        "features": len(features),
        "counts_by_type": dict(counts),
        "mile_marker_hits": genuine,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

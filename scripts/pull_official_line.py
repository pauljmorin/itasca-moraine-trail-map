#!/usr/bin/env python3
"""Pull the official North Country Trail line from the NCTA public ArcGIS
feature service and clip it to the chapter's working extent.

Data source (see config/chapter.json and SOURCES.md):
  "North Country Trail (Public)" - an ArcGIS feature service published by the
  North Country Trail Association, described by the service itself as
  "The official depiction of the North Country National Scenic Trail,
  produced by the North Country Trail Association on behalf of the
  National Park Service."

Method notes (first pass, standard library + requests only):
  * All features are paged through the REST query endpoint (resultOffset,
    respecting the service maxRecordCount), requested as GeoJSON in WGS84
    (outSR=4326). The full national line is saved to a scratch file in /tmp.
  * The extent clip is a bounding-box filter: a feature is retained if any
    of its line segments intersects the working-extent bounding box
    (tested via segment bounding-box overlap). Retained features keep
    their FULL geometry and ALL attributes - geometry is not trimmed.
  * The reported mileage is the length of line actually inside the
    extent: each segment is clipped to the box (Liang-Barsky) and measured
    geodesically (haversine, mean Earth radius 6371.0088 km).

Usage:  python3 scripts/pull_official_line.py
No credentials required; the service is public.
"""

import json
import math
import sys
import tempfile
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
SCRATCH_FULL = Path(tempfile.gettempdir()) / "nct_official_line_full.geojson"

EARTH_RADIUS_KM = 6371.0088


def get_json(url, params=None, retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 - report after retries
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} tries: {last_err}")


def find_route_layer(service_meta, name_hint):
    """Return (layer_id, layer_meta) for the polyline route layer."""
    candidates = [
        layer
        for layer in service_meta.get("layers", [])
        if layer.get("geometryType") == "esriGeometryPolyline"
    ]
    if not candidates:
        raise RuntimeError("No polyline layers found in service.")
    for layer in candidates:
        if name_hint and name_hint.lower() in layer.get("name", "").lower():
            return layer["id"], layer
    return candidates[0]["id"], candidates[0]


def page_features(layer_url, page_size):
    """Yield GeoJSON features from an ArcGIS layer, paging by offset."""
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "OBJECTID",
            "returnGeometry": "true",
        }
        data = get_json(f"{layer_url}/query", params=params)
        feats = data.get("features", [])
        if not feats:
            break
        yield from feats
        offset += len(feats)
        if len(feats) < page_size:
            break


def iter_segments(geometry):
    """Yield ((lon1, lat1), (lon2, lat2)) segments from LineString/MultiLineString."""
    if not geometry:
        return
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    lines = []
    if gtype == "LineString":
        lines = [coords]
    elif gtype == "MultiLineString":
        lines = coords
    for line in lines:
        for a, b in zip(line, line[1:]):
            yield (a[0], a[1]), (b[0], b[1])


def segment_bbox_hits_extent(a, b, ext):
    """True if the segment's own bounding box overlaps the extent box."""
    return not (
        max(a[0], b[0]) < ext["min_lon"]
        or min(a[0], b[0]) > ext["max_lon"]
        or max(a[1], b[1]) < ext["min_lat"]
        or min(a[1], b[1]) > ext["max_lat"]
    )


def feature_hits_extent(geometry, ext):
    return any(
        segment_bbox_hits_extent(a, b, ext) for a, b in iter_segments(geometry)
    )


def clip_segment_to_extent(a, b, ext):
    """Liang-Barsky clip of segment a-b to the extent box.

    Returns the clipped ((lon, lat), (lon, lat)) or None if fully outside.
    """
    x1, y1 = a
    x2, y2 = b
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, x1 - ext["min_lon"]),
        (dx, ext["max_lon"] - x1),
        (-dy, y1 - ext["min_lat"]),
        (dy, ext["max_lat"] - y1),
    ):
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


def haversine_miles(p, q):
    lon1, lat1 = math.radians(p[0]), math.radians(p[1])
    lon2, lat2 = math.radians(q[0]), math.radians(q[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h)) * 0.6213711922


def length_in_extent_miles(geometry, ext):
    total = 0.0
    for a, b in iter_segments(geometry):
        clipped = clip_segment_to_extent(a, b, ext)
        if clipped:
            total += haversine_miles(clipped[0], clipped[1])
    return total


def main():
    config = json.loads(CONFIG_PATH.read_text())
    src = config["data_sources"]["official_trail_line"]
    service_root = src["service_root"].rstrip("/")
    ext = config["working_extent_wgs84"]
    extent = {
        "min_lon": ext["min_lon"],
        "max_lon": ext["max_lon"],
        "min_lat": ext["min_lat"],
        "max_lat": ext["max_lat"],
    }
    out_path = REPO_ROOT / config["outputs"]["official_line_chapter_extent"]

    meta = get_json(service_root, params={"f": "pjson"})
    service_description = meta.get("description", "")
    service_copyright = meta.get("copyrightText", "")
    page_size = meta.get("maxRecordCount") or 1000

    layer_id, layer_meta = find_route_layer(meta, src.get("route_layer_name_contains"))
    layer_url = f"{service_root}/{layer_id}"
    print(f"Service description : {service_description}")
    print(f"Service copyright   : {service_copyright}")
    print(f"Route layer         : id {layer_id} - {layer_meta.get('name')}")
    print(f"Page size           : {page_size}")

    features = list(page_features(layer_url, page_size))
    print(f"National features   : {len(features)}")

    full_fc = {"type": "FeatureCollection", "features": features}
    SCRATCH_FULL.write_text(json.dumps(full_fc))
    print(f"Full national line  : {SCRATCH_FULL} (scratch, not in repo)")

    retained = [f for f in features if feature_hits_extent(f.get("geometry"), extent)]
    miles = sum(length_in_extent_miles(f.get("geometry"), extent) for f in retained)
    print(f"Retained in extent  : {len(retained)}")
    print(f"Miles within extent : {miles:.2f} (geodesic, haversine; segments")
    print("                      clipped to the extent box for this measure)")

    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Official North Country Trail line, clipped (bounding-box filter, geometries untrimmed) to the chapter working extent",
            "source_service": service_root,
            "source_layer_id": layer_id,
            "source_layer_name": layer_meta.get("name"),
            "service_description": service_description,
            "service_copyright": service_copyright,
            "pulled_utc_date": pulled,
            "extent_wgs84": extent,
            "national_feature_count": len(features),
            "retained_feature_count": len(retained),
            "miles_within_extent": round(miles, 2),
            "miles_method": "Geodesic (haversine) over segment portions clipped to the extent box (Liang-Barsky).",
        },
        "features": retained,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_fc))
    print(f"Wrote               : {out_path.relative_to(REPO_ROOT)}")

    summary = {
        "layer_id": layer_id,
        "layer_name": layer_meta.get("name"),
        "national_features": len(features),
        "retained_features": len(retained),
        "miles_within_extent": round(miles, 2),
    }
    print("SUMMARY " + json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())

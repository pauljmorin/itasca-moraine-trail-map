#!/usr/bin/env python3
"""Pull the access layers (MN DNR forest roads and recreation trails)
and the road centerlines for the chapter working extent.

Sources (see config/chapter.json and SOURCES.md): public ArcGIS
feature services on the Minnesota state enterprise host -
  * MN DNR: state forest roads, OHV trails, snowmobile trails,
    hunter walking trails, state trails, state park trails/roads
  * MnGeo/MnDOT: road centerlines (open)

Method (standard library + requests only), following
pull_official_line.py: features are selected with an envelope query
over the chapter working extent, then retained if any of their line
segments intersects the extent box (bounding-box segment test).
Retained features keep their FULL geometry and ALL source attributes;
two fields are added - source_type and source_dataset.

Fetch mechanics: on this host, offset-paged envelope queries in
GeoJSON form silently truncate (a 6,093-feature result returned only
1,893 features with no error). Features are therefore fetched by
object id: returnIdsOnly first, then chunks of ids, with each chunk's
returned count verified against the chunk size (a short chunk is
split and retried).

Outputs:
  * data/access/access-lines.geojson - all DNR access layers, one
    FeatureCollection distinguished by source_type
  * data/access/roads.geojson - road centerlines for the extent

Usage:  python3 scripts/pull_access_layers.py
No credentials required; the services are public.
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo_util import bbox_overlap, iter_line_segments  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"


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


ID_CHUNK = 500


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


def feature_hits_extent(geometry, ext):
    eb = (ext["min_lon"], ext["min_lat"], ext["max_lon"], ext["max_lat"])
    for a, b in iter_line_segments(geometry):
        sb = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
        if bbox_overlap(sb, eb):
            return True
    return False


def pull_service(svc, envelope, extent):
    layer_url = f"{svc['service_root'].rstrip('/')}/{svc['layer_id']}"
    pulled = list(page_layer(layer_url, envelope))
    retained = [f for f in pulled if feature_hits_extent(f.get("geometry"), extent)]
    return pulled, retained


def main():
    config = json.loads(CONFIG_PATH.read_text())
    ext = config["working_extent_wgs84"]
    extent = {
        "min_lon": ext["min_lon"],
        "max_lon": ext["max_lon"],
        "min_lat": ext["min_lat"],
        "max_lat": ext["max_lat"],
    }
    envelope = {
        "xmin": ext["min_lon"],
        "ymin": ext["min_lat"],
        "xmax": ext["max_lon"],
        "ymax": ext["max_lat"],
    }
    pulled_date = time.strftime("%Y-%m-%d", time.gmtime())

    # --- access lines --------------------------------------------------
    access_features = []
    per_source = {}
    for svc in config["data_sources"]["access_layers_mn"]["services"]:
        pulled, retained = pull_service(svc, envelope, extent)
        for feat in retained:
            props = dict(feat.get("properties") or {})
            props["source_type"] = svc["source_type"]
            props["source_dataset"] = svc["name"]
            access_features.append(
                {"type": "Feature", "geometry": feat.get("geometry"), "properties": props}
            )
        per_source[svc["source_type"]] = {
            "dataset": svc["name"],
            "service_root": svc["service_root"],
            "layer_id": svc["layer_id"],
            "pulled": len(pulled),
            "retained": len(retained),
        }
        print(f"{svc['source_type']}: pulled {len(pulled)}, retained {len(retained)}")

    access_path = REPO_ROOT / config["outputs"]["access_lines"]
    access_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Access lines for the chapter working extent: MN DNR state forest roads and recreation trails",
            "pulled_utc_date": pulled_date,
            "extent_wgs84": extent,
            "clip_method": "Envelope selection (object-id fetch, chunk-verified), then bounding-box segment filter against the extent (geometries untrimmed, all source attributes kept; source_type/source_dataset added)",
            "sources": per_source,
            "total_features": len(access_features),
        },
        "features": access_features,
    }
    access_path.parent.mkdir(parents=True, exist_ok=True)
    access_path.write_text(json.dumps(access_fc))
    print(f"Wrote {access_path.relative_to(REPO_ROOT)}: {len(access_features)} features")

    # --- roads ---------------------------------------------------------
    rsrc = config["data_sources"]["road_centerlines_mn"]
    svc = {"service_root": rsrc["service_root"], "layer_id": rsrc["layer_id"]}
    pulled, retained = pull_service(svc, envelope, extent)
    print(f"roads: pulled {len(pulled)}, retained {len(retained)}")
    roads_path = REPO_ROOT / config["outputs"]["access_roads"]
    roads_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Road centerlines for the chapter working extent (MnDOT via MnGeo, open)",
            "source_dataset": rsrc["name"],
            "service_root": rsrc["service_root"],
            "layer_id": rsrc["layer_id"],
            "pulled_utc_date": pulled_date,
            "extent_wgs84": extent,
            "clip_method": "Envelope selection (object-id fetch, chunk-verified), then bounding-box segment filter against the extent (geometries untrimmed, all source attributes kept)",
            "pulled_features": len(pulled),
            "total_features": len(retained),
        },
        "features": [
            {"type": "Feature", "geometry": f.get("geometry"), "properties": f.get("properties")}
            for f in retained
        ],
    }
    roads_path.write_text(json.dumps(roads_fc))
    print(f"Wrote {roads_path.relative_to(REPO_ROOT)}: {len(retained)} features")
    print("SUMMARY " + json.dumps({"access": len(access_features), "roads": len(retained)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

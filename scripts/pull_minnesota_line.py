#!/usr/bin/env python3
"""Pull the official North Country Trail line from the NCTA public ArcGIS
feature service and keep the Minnesota portion (state == 'MN').

Companion to scripts/pull_official_line.py, which clips the same national
pull to the chapter working extent. This one keeps every Minnesota
feature, full geometry, all attributes — from the North Dakota border
to the Border Route Trail junction. It does NOT touch the chapter file.

Data source (see SOURCES.md):
  "North Country Trail (Public)" - ArcGIS feature service published by
  the North Country Trail Association, "The official depiction of the
  North Country National Scenic Trail, produced by the North Country
  Trail Association on behalf of the National Park Service."

Method: page the route layer (same as pull_official_line.py), keep
features whose `state` property is 'MN'. Mileage is the geodesic
(haversine) length of the retained features' full geometry — the
segments are not trimmed to any box, so this is the trail length in
Minnesota as the service draws it.

Usage:  python3 scripts/pull_minnesota_line.py
No credentials required; the service is public.
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pull_official_line import (  # noqa: E402
    get_json,
    find_route_layer,
    page_features,
    iter_segments,
    haversine_miles,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
OUT_SITE = REPO_ROOT / "site" / "data" / "trail-minnesota.geojson"
OUT_WORK = REPO_ROOT / "data" / "segments" / "official-line-minnesota.geojson"


def full_length_miles(geometry):
    return sum(
        haversine_miles(a, b) for a, b in iter_segments(geometry)
    )


def main():
    config = json.loads(CONFIG_PATH.read_text())
    src = config["data_sources"]["official_trail_line"]
    service_root = src["service_root"].rstrip("/")

    meta = get_json(service_root, params={"f": "pjson"})
    service_description = meta.get("description", "")
    service_copyright = meta.get("copyrightText", "")
    page_size = meta.get("maxRecordCount") or 1000

    layer_id, layer_meta = find_route_layer(
        meta, src.get("route_layer_name_contains")
    )
    layer_url = f"{service_root}/{layer_id}"
    print(f"Service description : {service_description}")
    print(f"Service copyright   : {service_copyright}")
    print(f"Route layer         : id {layer_id} - {layer_meta.get('name')}")
    print(f"Page size           : {page_size}")

    features = list(page_features(layer_url, page_size))
    print(f"National features   : {len(features)}")

    mn = [f for f in features if (f.get("properties") or {}).get("state") == "MN"]
    print(f"Minnesota features  : {len(mn)}")

    chapters = Counter((f.get("properties") or {}).get("chapter") for f in mn)
    print(f"Chapters in MN      : {dict(chapters)}")

    miles = sum(full_length_miles(f.get("geometry")) for f in mn)
    print(f"Miles in Minnesota  : {miles:.2f} (geodesic, haversine, "
          "full geometry)")

    xs, ys = [], []
    for f in mn:
        g = f.get("geometry") or {}
        coords = g.get("coordinates") or []
        lines = [coords] if g.get("type") == "LineString" else coords
        for line in lines:
            for c in line:
                xs.append(c[0])
                ys.append(c[1])
    print(f"Extent              : lon {min(xs):.3f} to {max(xs):.3f}, "
          f"lat {min(ys):.3f} to {max(ys):.3f}")

    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "Official North Country Trail line, Minnesota "
                       "portion (state == 'MN'), geometries untrimmed",
            "source_service": service_root,
            "source_layer_id": layer_id,
            "source_layer_name": layer_meta.get("name"),
            "service_description": service_description,
            "service_copyright": service_copyright,
            "pulled_utc_date": pulled,
            "national_feature_count": len(features),
            "minnesota_feature_count": len(mn),
            "miles_in_minnesota": round(miles, 2),
            "miles_method": "Geodesic (haversine) over the retained "
                            "features' full geometry.",
            "chapters": dict(chapters),
        },
        "features": mn,
    }
    for path in (OUT_SITE, OUT_WORK):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out_fc))
        print(f"Wrote               : {path.relative_to(REPO_ROOT)}")

    print("SUMMARY " + json.dumps({
        "layer_id": layer_id,
        "layer_name": layer_meta.get("name"),
        "national_features": len(features),
        "minnesota_features": len(mn),
        "miles_in_minnesota": round(miles, 2),
        "chapters": dict(chapters),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

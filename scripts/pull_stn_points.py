#!/usr/bin/env python3
"""Pull the NCTA public service's camping waypoints for the
Star of the North trail (MN-84 to MN-6 NE of Remer) and keep the
ones on or near the trail.

Companion to scripts/pull_arrowhead_points.py (the Arrowhead gap)
and scripts/pull_points.py (the chapter's NCTA points). Same
source: the NCTA public ArcGIS feature service ("North Country
Trail (Public)", NCTA on behalf of NPS), LAYER 1 "Point Data -
Public" - the waypoint layer behind the public map / FarOut.
Same cleaning as pull_points.py (name / type / subtype / owner /
description / chapter; blank strings and the literal "None"
normalised to null).

Selection: envelope over the Star of the North line bbox, then
keep only wptType == "Camping" points within 2 km of the STN
line (data/segments/trail-stn.geojson). Excluded Camping points
in the bbox are listed in the output metadata with their
distance, so the exclusion is auditable. Each kept point
carries dist_trail_km (distance to the STN line) so the map
popup can say how far off-trail it sits. Names are carried
exactly as published, including generic ones ("Camping",
"Campsite") - no better name is invented.

Output: data/points/ncta-points-stn.geojson (working data).
The published file is built by scripts/build_site_data.py into
site/data/campsites-stn.geojson.

Usage:  python3 scripts/pull_stn_points.py
No credentials required; the service is public.
"""

import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geo_util import iter_line_segments  # noqa: E402
from pull_points import (  # noqa: E402
    clean_feature,
    find_point_layer,
    get_json,
    page_layer,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
STN_LINE = REPO_ROOT / "data" / "segments" / "trail-stn.geojson"
OUT_PATH = REPO_ROOT / "data" / "points" / "ncta-points-stn.geojson"

# STN line bbox (lon -94.21..-93.85, lat 47.02..47.13), padded a
# little so a trailside point just outside the line bbox is
# still seen.
ENVELOPE = {"xmin": -94.30, "ymin": 46.97, "xmax": -93.79, "ymax": 47.18}
MAX_DIST_KM = 2.0

KM_PER_DEG_LAT = 111.195
KM_PER_DEG_LON = 75.93  # at 47 N


def point_seg_dist_km(lon, lat, a, b):
    ax, ay = a[0] * KM_PER_DEG_LON, a[1] * KM_PER_DEG_LAT
    bx, by = b[0] * KM_PER_DEG_LON, b[1] * KM_PER_DEG_LAT
    px, py = lon * KM_PER_DEG_LON, lat * KM_PER_DEG_LAT
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main():
    config = json.loads(CONFIG_PATH.read_text())
    src = config["data_sources"]["official_trail_line"]
    service_root = src["service_root"].rstrip("/")

    meta = get_json(service_root, params={"f": "pjson"})
    layer_id, layer_meta = find_point_layer(meta)
    print(f"Point layer         : id {layer_id} - {layer_meta.get('name')}")

    raw = page_layer(f"{service_root}/{layer_id}", ENVELOPE)
    print(f"Fetched (by obj id) : {len(raw)}")

    stn_fc = json.loads(STN_LINE.read_text())
    stn_segs = []
    for feat in stn_fc["features"]:
        stn_segs.extend(iter_line_segments(feat.get("geometry")))

    kept, excluded = [], []
    for f in raw:
        cf = clean_feature(f)
        if cf is None:
            continue
        if cf["properties"]["type"] != "Camping":
            continue
        lon, lat = cf["geometry"]["coordinates"]
        d = min(point_seg_dist_km(lon, lat, a, b) for a, b in stn_segs)
        cf["properties"]["dist_trail_km"] = round(d, 2)
        if d <= MAX_DIST_KM:
            kept.append(cf)
        else:
            excluded.append(cf)
    kept.sort(key=lambda f: (f["properties"]["name"] or ""))
    print(f"Camping in bbox    : {len(kept) + len(excluded)}")
    print(f"Kept (<= {MAX_DIST_KM} km from the STN line): {len(kept)}")
    for f in kept:
        p = f["properties"]
        print(f"  kept: {p['name']} ({p['dist_trail_km']} km)")
    print(f"Excluded (> {MAX_DIST_KM} km): {len(excluded)}")
    for f in excluded:
        p = f["properties"]
        print(f"  excluded: {p['name']} at {f['geometry']['coordinates']} "
              f"({p['dist_trail_km']} km)")

    counts = Counter(f["properties"]["chapter"] for f in kept)
    out_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "dataset": "NCTA public camping waypoints for the Star of "
                       "the North trail, kept where within 2 km of the "
                       "STN line",
            "source_service": service_root,
            "source_layer_id": layer_id,
            "source_layer_name": layer_meta.get("name"),
            "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
            "extent_wgs84": ENVELOPE,
            "clip_method": "Envelope selection (object-id fetch, "
                           "chunk-verified); kept Camping points within "
                           f"{MAX_DIST_KM} km of the Star of the North "
                           f"line (data/segments/trail-stn.geojson)",
            "feature_count": len(kept),
            "counts_by_chapter": dict(counts),
            "excluded_camping": [
                {
                    "name": f["properties"]["name"],
                    "coordinates": f["geometry"]["coordinates"],
                    "dist_trail_km": f["properties"]["dist_trail_km"],
                    "reason": "beyond 2 km from the Star of the North line",
                }
                for f in excluded
            ],
        },
        "features": kept,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out_fc, indent=1))
    print(f"Wrote               : {OUT_PATH.relative_to(REPO_ROOT)}")
    print("SUMMARY " + json.dumps({
        "features": len(kept),
        "counts_by_chapter": dict(counts),
        "excluded": len(excluded),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

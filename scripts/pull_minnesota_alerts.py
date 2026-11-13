#!/usr/bin/env python3
"""Pull the NCTA trail alerts (alert points + reroute lines) for all of
Minnesota, EXCLUDING alerts inside the chapter working extent.

Companion to scripts/pull_trail_alerts.py, which clips the same service
to the chapter working extent. This one covers the rest of Minnesota —
from the North Dakota border to the Border Route Trail — so the two
layers are complementary: turning both on shows every Minnesota alert
exactly once, with no stacked duplicates.

Data source: the service "trail_alerts" on the same ArcGIS organisation
as the official line (NCTA) — "Trail Alerts for the North Country
Trail". Layer 1 "trail_alerts" is the alert POINTS; layer 2
"trail_alerts_new_rte" is the reroute LINES. Alerts are quoted
verbatim, never rewritten — see pull_trail_alerts.py for the date
handling (America/Chicago calendar date of the stored instant) and
the geometry-only position rule.

Method: envelope selection over a Minnesota bounding box
(lon -97.3 to -89.5, lat 46.0 to 49.4), features fetched BY OBJECT ID
in chunk-verified chunks (same as pull_trail_alerts.py). A point is
dropped when it falls inside the chapter working extent from
config/chapter.json; a reroute line is dropped only when its whole
bounding box sits inside that extent.

Outputs:
  * data/points/trail-alerts-minnesota.geojson       (working, points)
  * data/points/trail-alert-lines-minnesota.geojson  (working, lines)
  * site/data/trail-alerts-minnesota.geojson         (site copy, points)
  * site/data/trail-alert-lines-minnesota.geojson    (site copy, lines;
    written ONLY when the line layer returns features outside the
    chapter extent)

Usage:  python3 scripts/pull_minnesota_alerts.py
No credentials required; the service is public.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pull_trail_alerts import (  # noqa: E402
    get_json,
    page_layer,
    clean_point,
    clean_line,
    write_fc,
    SERVICE_ROOT,
    POINTS_LAYER_ID,
    LINES_LAYER_ID,
    POINTS_OUT_FIELDS,
    LINES_OUT_FIELDS,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
OUT_POINTS = REPO_ROOT / "data" / "points" / "trail-alerts-minnesota.geojson"
OUT_LINES = REPO_ROOT / "data" / "points" / "trail-alert-lines-minnesota.geojson"
SITE_POINTS = REPO_ROOT / "site" / "data" / "trail-alerts-minnesota.geojson"
SITE_LINES = REPO_ROOT / "site" / "data" / "trail-alert-lines-minnesota.geojson"

# Minnesota bounding box — generous: catches the trail at both borders
# (Fargo ND, Superior WI) plus a little context, and the full north
# shore to the Border Route.
MN_ENVELOPE = {"xmin": -97.3, "ymin": 46.0, "xmax": -89.5, "ymax": 49.4}


def inside_extent(lon, lat, ext):
    return (ext["min_lon"] <= lon <= ext["max_lon"]
            and ext["min_lat"] <= lat <= ext["max_lat"])


def line_inside_extent(geom, ext):
    """True when a line's whole bounding box sits inside the extent."""
    coords = geom.get("coordinates") or []
    lines = [coords] if geom.get("type") == "LineString" else coords
    xs, ys = [], []
    for line in lines:
        for c in line:
            xs.append(c[0])
            ys.append(c[1])
    if not xs:
        return True
    return (min(xs) >= ext["min_lon"] and max(xs) <= ext["max_lon"]
            and min(ys) >= ext["min_lat"] and max(ys) <= ext["max_lat"])


def main():
    config = json.loads(CONFIG_PATH.read_text())
    ext = config["working_extent_wgs84"]
    meta = get_json(SERVICE_ROOT, params={"f": "pjson"})
    layer_names = {l["id"]: l.get("name") for l in meta.get("layers", [])}
    print(f"Service             : {SERVICE_ROOT}")
    print(f"Points layer        : id {POINTS_LAYER_ID} - "
          f"{layer_names.get(POINTS_LAYER_ID)}")
    print(f"Lines layer         : id {LINES_LAYER_ID} - "
          f"{layer_names.get(LINES_LAYER_ID)}")
    print(f"MN envelope         : {MN_ENVELOPE}")
    print(f"Chapter extent      : {ext['min_lon']} to {ext['max_lon']}, "
          f"{ext['min_lat']} to {ext['max_lat']} (excluded)")

    base_meta = {
        "source_service": SERVICE_ROOT,
        "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
        "envelope_wgs84": MN_ENVELOPE,
        "excluded_extent_wgs84": {
            "min_lon": ext["min_lon"], "max_lon": ext["max_lon"],
            "min_lat": ext["min_lat"], "max_lat": ext["max_lat"],
        },
        "clip_method": "Envelope selection (object-id fetch, "
                       "chunk-verified); points inside the chapter "
                       "working extent excluded so this layer "
                       "complements data/trail-alerts.geojson.",
    }

    # ---- alert points (layer 1)
    raw_points = page_layer(f"{SERVICE_ROOT}/{POINTS_LAYER_ID}",
                            POINTS_OUT_FIELDS, MN_ENVELOPE)
    print(f"Fetched points      : {len(raw_points)}")
    points = []
    dropped = 0
    for f in raw_points:
        cf = clean_point(f)
        if cf is None:
            dropped += 1
            continue
        lon, lat = cf["geometry"]["coordinates"]
        if inside_extent(lon, lat, ext):
            dropped += 1
            continue
        points.append(cf)
    points.sort(key=lambda f: (f["properties"]["date"] is None,
                               f["properties"]["date"] or ""))
    for f in points:
        p = f["properties"]
        c = f["geometry"]["coordinates"]
        print(f"  {p['date']}  {p['title']}  @ {c[0]}, {c[1]}")
    points_meta = {
        "dataset": "NCTA trail alerts (alert points), Minnesota "
                   "outside the chapter working extent",
        "source_layer_id": POINTS_LAYER_ID,
        "source_layer_name": layer_names.get(POINTS_LAYER_ID),
        "date_note": "date_ms is the service's stored instant "
                     "verbatim; date is its America/Chicago calendar "
                     "date (see pull_trail_alerts.py).",
        "feature_count": len(points),
        **base_meta,
    }
    write_fc(OUT_POINTS, points, points_meta)
    write_fc(SITE_POINTS, points, points_meta)

    # ---- reroute lines (layer 2)
    raw_lines = page_layer(f"{SERVICE_ROOT}/{LINES_LAYER_ID}",
                           LINES_OUT_FIELDS, MN_ENVELOPE)
    print(f"Fetched lines       : {len(raw_lines)}")
    lines = []
    for f in raw_lines:
        cf = clean_line(f)
        if cf is None:
            dropped += 1
            continue
        if line_inside_extent(cf["geometry"], ext):
            dropped += 1
            continue
        lines.append(cf)
    lines_meta = {
        "dataset": "NCTA trail alerts (reroute lines), Minnesota "
                   "outside the chapter working extent",
        "source_layer_id": LINES_LAYER_ID,
        "source_layer_name": layer_names.get(LINES_LAYER_ID),
        "feature_count": len(lines),
        **base_meta,
    }
    write_fc(OUT_LINES, lines, lines_meta)
    if lines:
        write_fc(SITE_LINES, lines, lines_meta)
    else:
        if SITE_LINES.exists():
            SITE_LINES.unlink()
            print(f"Removed stale       : "
                  f"{SITE_LINES.relative_to(REPO_ROOT)}")
        print("Site lines file     : not written (no line features "
              "outside the chapter extent)")
    if dropped:
        print(f"Dropped (no geom / in chapter extent) : {dropped}")

    print("SUMMARY " + json.dumps({
        "points": len(points), "lines": len(lines),
        "dates": [f["properties"]["date"] for f in points],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

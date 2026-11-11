#!/usr/bin/env python3
"""Pull the NCTA trail alerts (alert points + reroute lines) from the
NCTA ArcGIS organisation and clip them to the chapter working extent.

Data source: the service "trail_alerts" on the same ArcGIS
organisation as the official line (NCTA) — "Trail Alerts for the
North Country Trail". Layer 1 "trail_alerts" is the alert POINTS
(fields: Date, Location, desc_ = description, label = the alert's
title); layer 2 "trail_alerts_new_rte" is the reroute LINES
(seg_name, trail_stat, len_miles, prop_name, mng_auth,
special_regs). Alerts are NCTA's own current-awareness notices —
closures, storm damage, reroutes, new routes — shown on the map
verbatim and credited to NCTA; nothing here is chapter-authored.

DATE HANDLING — READ BEFORE "FIXING": the service stores each
alert's Date as UTC midnight of the day AFTER the intended calendar
date (a date-only field authored in a US timezone). The intended
date is the America/Chicago calendar date of the stored instant:
1753574400000 is stored as 2025-07-27T00:00Z and means 2025-07-26.
This script therefore carries BOTH the raw epoch milliseconds
(date_ms, verbatim) and the derived ISO calendar date (date, the
America/Chicago date of date_ms). The map displays `date`; never
re-derive it as the UTC date.

Positions come solely from the returned GeoJSON GEOMETRY requested
with outSR=4326 — the standing rule for this organisation's
services (a sibling service's lat/long ATTRIBUTE columns are
corrupt; this service carries none, and none would be read).

Text (title / location / description) is carried VERBATIM from the
service — alerts are quoted, never rewritten or summarised.

Method follows pull_mile_markers.py: envelope selection over the
chapter working extent, features fetched BY OBJECT ID in
chunk-verified chunks (offset paging on these hosts has silently
truncated before).

Outputs:
  * data/points/trail-alerts.geojson       (working, alert points)
  * data/points/trail-alert-lines.geojson  (working, reroute lines)
  * site/data/trail-alerts.geojson         (site copy of the points)
  * site/data/trail-alert-lines.geojson    (site copy of the lines,
    written ONLY when the line layer returns features; a stale site
    copy is removed when it returns none)

Usage:  python3 scripts/pull_trail_alerts.py
No credentials required; the service is public.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from zoneinfo import ZoneInfo
    CHAPTER_TZ = ZoneInfo("America/Chicago")
except Exception:  # noqa: BLE001 — no tz database: fixed CDT offset
    from datetime import timedelta, tzinfo

    class _CDT(tzinfo):
        def utcoffset(self, dt):
            return timedelta(hours=-5)

        def dst(self, dt):
            return timedelta(hours=1)

        def tzname(self, dt):
            return "CDT"

    CHAPTER_TZ = _CDT()

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "chapter.json"
OUT_POINTS = REPO_ROOT / "data" / "points" / "trail-alerts.geojson"
OUT_LINES = REPO_ROOT / "data" / "points" / "trail-alert-lines.geojson"
SITE_POINTS = REPO_ROOT / "site" / "data" / "trail-alerts.geojson"
SITE_LINES = REPO_ROOT / "site" / "data" / "trail-alert-lines.geojson"

SERVICE_ROOT = ("https://services2.arcgis.com/UfGVyqUm4GHa2zrj"
                "/arcgis/rest/services/trail_alerts/FeatureServer")
POINTS_LAYER_ID = 1
LINES_LAYER_ID = 2
POINTS_OUT_FIELDS = "Date,Location,desc_,label"
LINES_OUT_FIELDS = ("seg_name,trail_stat,len_miles,prop_name,"
                    "mng_auth,special_regs")
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


def fetch_chunk(layer_url, oid_field, out_fields, ids):
    """Fetch features for one chunk of object ids; verify the count
    and split the chunk if the server returns fewer than asked."""
    where = f"{oid_field} IN ({','.join(str(i) for i in ids)})"
    params = {
        "where": where,
        "outFields": out_fields,
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
        return fetch_chunk(layer_url, oid_field, out_fields,
                           ids[:mid]) + fetch_chunk(
                               layer_url, oid_field, out_fields, ids[mid:])
    return feats


def page_layer(layer_url, out_fields, envelope):
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
        feats.extend(fetch_chunk(layer_url, oid_field, out_fields,
                                 ids[i:i + ID_CHUNK]))
    return feats


def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def verbatim_str(v):
    """Alert text is quoted verbatim — no trimming or rewriting.
    Only a wholly absent value becomes None."""
    if v is None:
        return None
    s = str(v)
    return s if s.strip() else None


def alert_date(date_ms):
    """The intended calendar date (ISO) of a stored alert instant:
    the America/Chicago date — see the header's date warning."""
    if date_ms is None:
        return None
    dt = datetime.fromtimestamp(float(date_ms) / 1000.0,
                                tz=timezone.utc)
    return dt.astimezone(CHAPTER_TZ).date().isoformat()


def clean_point(f):
    p = f.get("properties") or {}
    geom = f.get("geometry") or {}
    coords = geom.get("coordinates")
    if not coords:
        return None  # no geometry fallback — positions are geometry-only
    date_ms = p.get("Date")
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [round(float(coords[0]), 6),
                            round(float(coords[1]), 6)],
        },
        "properties": {
            "title": verbatim_str(p.get("label")),
            "location": verbatim_str(p.get("Location")),
            "date": alert_date(date_ms),
            "date_ms": date_ms,
            "description": verbatim_str(p.get("desc_")),
        },
    }


def clean_line(f):
    p = f.get("properties") or {}
    geom = f.get("geometry") or {}
    if not geom.get("coordinates"):
        return None
    return {
        "type": "Feature",
        "geometry": geom,
        "properties": {
            "name": verbatim_str(p.get("seg_name")),
            "trail_stat": verbatim_str(p.get("trail_stat")),
            "length_mi": p.get("len_miles"),
            "property": verbatim_str(p.get("prop_name")),
            "managing_authority": verbatim_str(p.get("mng_auth")),
            "special_regs": verbatim_str(p.get("special_regs")),
        },
    }


def write_fc(path, features, metadata):
    fc = {"type": "FeatureCollection", "metadata": metadata,
          "features": features}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fc, indent=1))
    print(f"Wrote               : {path.relative_to(REPO_ROOT)} "
          f"({len(features)} features)")


def main():
    config = json.loads(CONFIG_PATH.read_text())
    ext = config["working_extent_wgs84"]
    envelope = {
        "xmin": ext["min_lon"], "ymin": ext["min_lat"],
        "xmax": ext["max_lon"], "ymax": ext["max_lat"],
    }
    meta = get_json(SERVICE_ROOT, params={"f": "pjson"})
    layer_names = {l["id"]: l.get("name") for l in meta.get("layers", [])}
    print(f"Service             : {SERVICE_ROOT}")
    print(f"                    : {meta.get('serviceDescription', '')}")
    print(f"Points layer        : id {POINTS_LAYER_ID} - "
          f"{layer_names.get(POINTS_LAYER_ID)}")
    print(f"Lines layer         : id {LINES_LAYER_ID} - "
          f"{layer_names.get(LINES_LAYER_ID)}")
    base_meta = {
        "source_service": SERVICE_ROOT,
        "pulled_utc_date": time.strftime("%Y-%m-%d", time.gmtime()),
        "extent_wgs84": {
            "min_lon": ext["min_lon"], "max_lon": ext["max_lon"],
            "min_lat": ext["min_lat"], "max_lat": ext["max_lat"],
        },
        "clip_method": "Envelope selection (object-id fetch, "
                       "chunk-verified); positions from GeoJSON "
                       "geometry requested with outSR=4326",
    }

    # ---- alert points (layer 1)
    raw_points = page_layer(f"{SERVICE_ROOT}/{POINTS_LAYER_ID}",
                            POINTS_OUT_FIELDS, envelope)
    print(f"Fetched points      : {len(raw_points)}")
    points = []
    dropped = 0
    for f in raw_points:
        cf = clean_point(f)
        if cf is None:
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
        "dataset": "NCTA trail alerts (alert points), clipped to "
                   "the chapter working extent",
        "source_layer_id": POINTS_LAYER_ID,
        "source_layer_name": layer_names.get(POINTS_LAYER_ID),
        "date_note": "date_ms is the service's stored instant "
                     "verbatim; date is its America/Chicago calendar "
                     "date (the service stores UTC midnight of the "
                     "following day — see pull_trail_alerts.py).",
        "feature_count": len(points),
        **base_meta,
    }
    write_fc(OUT_POINTS, points, points_meta)
    write_fc(SITE_POINTS, points, points_meta)

    # ---- reroute lines (layer 2)
    raw_lines = page_layer(f"{SERVICE_ROOT}/{LINES_LAYER_ID}",
                           LINES_OUT_FIELDS, envelope)
    print(f"Fetched lines       : {len(raw_lines)}")
    lines = []
    for f in raw_lines:
        cf = clean_line(f)
        if cf is None:
            dropped += 1
            continue
        lines.append(cf)
    lines_meta = {
        "dataset": "NCTA trail alerts (reroute lines), clipped to "
                   "the chapter working extent",
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
                  f"{SITE_LINES.relative_to(REPO_ROOT)} "
                  f"(line layer returned no features)")
        print("Site lines file     : not written (no line features "
              "in extent; the map layer covers points)")
    if dropped:
        print(f"Dropped (no geom)   : {dropped}")

    print("SUMMARY " + json.dumps({
        "points": len(points), "lines": len(lines),
        "dates": [f["properties"]["date"] for f in points],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())

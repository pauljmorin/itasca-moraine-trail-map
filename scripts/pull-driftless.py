#!/usr/bin/env python3
"""Pull the built Driftless Hiking Trail segments from OpenStreetMap and
assemble data/driftless/driftless-trail.geojson (+ the viewer copy).

Sources (all public, no login):
  - OpenStreetMap API bbox endpoint (api.openstreetmap.org/api/0.6/map).
    Overpass is down from this VM; the OSM API works for small rural bboxes.
  - The traced Welsh Hills outer loop, produced by trace-trifold-maps.py
    from the DALC Welsh Hills trifold map (georeferenced, approximate) —
    OSM only carries the inner chord (1.113 mi); the outer loop (Ridge
    Section, ~2.1 mi traced, DALC publishes 2.6 mi) is not in OSM.

Segments (verified Nov 16, 2026):
  Phoebe Point Trail  OSM way 1248941083, 0.685 mi (DALC publishes ~1.1 mi;
                      the map's loop measures the same 0.66 mi as OSM — the
                      1.1 mi figure likely includes the Oct 2026 connector,
                      which is on neither OSM nor this trifold)
  Welsh Hills Trail   OSM way 1248943005 (inner chord), 1.113 mi, PLUS the
                      traced outer loop, 2.085 mi
  Knobs Road Trail    OSM way 1248953013, 2.457 mi (DALC publishes ~2.7 mi;
                      the OSM line's two ends both touch Knobs Road 1.58 km
                      apart — the loop is left open, no tread invented)
  Weaver Road         NOT in OSM (no named footway found in two bbox fetches
                      around the trailhead junction 43.05585, -90.11263) and
                      no trifold PDF exists for it — NOT included. Known gap.

Total assembled: 6.340 mi (OSM 4.255 + traced outer loop 2.085).

Usage: python3 scripts/pull-driftless.py [--no-fetch]
  --no-fetch reuses data/driftless/osm/*.osm instead of hitting the API.
Outputs: data/driftless/driftless-trail.geojson and
         site/data/driftless-trail.geojson (identical viewer copy).
"""
import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "driftless"
SITE = REPO / "site" / "data"
UA = {"User-Agent": "Muse/1.0 (itasca-moraine-trail-map; driftless-trail pull)"}

BOXES = {
    "taliesin": (-90.09, 43.12, -90.04, 43.16),
    "knobs": (-90.03, 43.04, -90.00, 43.08),
    "weaver": (-90.13, 43.04, -90.10, 43.07),
}
# way id -> (segment key, display name, detail)
WANTED = {
    "1248941083": ("phoebe-point", "Phoebe Point Trail",
                   "Built segment — OpenStreetMap"),
    "1248943005": ("welsh-hills-inner", "Welsh Hills Trail",
                   "Built segment, inner route — OpenStreetMap"),
    "1248953013": ("knobs-road", "Knobs Road Trail",
                   "Built segment — OpenStreetMap"),
}
TRACED = DATA / "driftless-traced-welsh-phoebe.geojson"


def haversine_mi(a, b):
    lat1, lon1 = math.radians(a[1]), math.radians(a[0])
    lat2, lon2 = math.radians(b[1]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def line_miles(coords):
    return sum(haversine_mi(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def fetch():
    (DATA / "osm").mkdir(parents=True, exist_ok=True)
    for name, (w, s, e, n) in BOXES.items():
        url = f"https://api.openstreetmap.org/api/0.6/map?bbox={w},{s},{e},{n}"
        r = requests.get(url, headers=UA, timeout=120)
        print(f"{name}: HTTP {r.status_code}, {len(r.content)} bytes")
        if r.status_code != 200:
            print(f"  FAILED to fetch {name}; aborting")
            sys.exit(1)
        (DATA / "osm" / f"{name}.osm").write_bytes(r.content)


def parse_osm(path):
    t = ET.parse(path)
    root = t.getroot()
    nodes, ways = {}, []
    for el in root:
        if el.tag == "node":
            nodes[el.get("id")] = (float(el.get("lon")), float(el.get("lat")))
        elif el.tag == "way":
            tags = {c.get("k"): c.get("v") for c in el if c.tag == "tag"}
            nds = [c.get("ref") for c in el if c.tag == "nd"]
            ways.append({"id": el.get("id"), "tags": tags, "nds": nds})
    return nodes, ways


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    if not args.no_fetch:
        fetch()

    feats = []
    found = set()
    for fname in ("taliesin", "knobs", "weaver"):
        nodes, ways = parse_osm(DATA / "osm" / f"{fname}.osm")
        for w in ways:
            if w["id"] not in WANTED:
                continue
            key, name, detail = WANTED[w["id"]]
            coords = [nodes[n] for n in w["nds"] if n in nodes]
            if len(coords) < 2:
                print(f"WARNING: way {w['id']} has <2 nodes in {fname}.osm")
                continue
            mi = line_miles(coords)
            found.add(w["id"])
            print(f"{name} (OSM way {w['id']}): {len(coords)} pts, {mi:.3f} mi")
            feats.append({
                "type": "Feature",
                "properties": {
                    "name": name,
                    "detail": detail,
                    "source": "OpenStreetMap (ODbL), pull date Nov 16, 2026",
                    "source_url": f"https://www.openstreetmap.org/way/{w['id']}",
                    "length_mi": round(mi, 3),
                    "segment": key,
                    "accuracy": "mapped",
                },
                "geometry": {"type": "LineString",
                             "coordinates": [[round(a, 6), round(b, 6)] for a, b in coords]},
            })
    missing = set(WANTED) - found
    if missing:
        print(f"WARNING: wanted OSM ways not found in any bbox: {sorted(missing)}")

    # Traced Welsh outer loop (produced by trace-trifold-maps.py).
    if TRACED.exists():
        traced = json.loads(TRACED.read_text())
        for f in traced["features"]:
            print(f"{f['properties']['name']} (traced outer loop): "
                  f"{len(f['geometry']['coordinates'])} pts, "
                  f"{f['properties']['length_mi']:.3f} mi")
            feats.append(f)
    else:
        print(f"WARNING: traced file {TRACED} missing — outer loop NOT included")

    total = sum(f["properties"]["length_mi"] for f in feats)
    print(f"TOTAL: {len(feats)} features, {total:.3f} mi")
    fc = {"type": "FeatureCollection", "features": feats}
    out = DATA / "driftless-trail.geojson"
    out.write_text(json.dumps(fc, indent=1))
    site_out = SITE / "driftless-trail.geojson"
    site_out.write_text(json.dumps(fc, indent=1))
    print(f"wrote {out} and {site_out} (identical)")


if __name__ == "__main__":
    main()

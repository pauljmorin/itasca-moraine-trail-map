#!/usr/bin/env python3
"""Pull the Leech Lake Reservation boundary (public federal data).

Source (switched 2026-11-11 by Paul's tap; see SOURCES.md
"Leech Lake Reservation"):
  Bureau of Indian Affairs, American Indian and Alaska Native
  Land Area Representation (AIAN-LAR) national dataset,
  FeatureServer DivLTR/BIA_AIAN_National_LAR layer 0,
  feature LARID 'LAR0033', LARNAME 'Leech Lake'.
  Geometry: MultiPolygon, 3 polygons, 3,999 vertices.

Why BIA, not Census: the Census TIGER/Line AIANNH polygon
(GEOID 1940R, the layer's first source) stitches its southern
lobe to the main body with a bridge ~5 m wide at (-94.377,
47.223), which renders as the boundary crossing over itself.
BIA draws the lobe as a separate polygon with a ~210 m gap —
no pinch — while the boundary LINES agree closely (median
19 m near the neck). BIA's GISACRES attribute (1,794,106 ac)
contradicts its own geometry and is NOT used; the area below
is geometry-measured (UTM 15N, 2026-11-11).

The Census off-reservation trust-land feature (GEOID 1940T,
0.05 sq km) is deliberately NOT included: this layer is the
reservation itself. Census remains the cross-check (see
SOURCES.md).

Outputs (identical GeoJSON, full unclipped geometry):
  data/native-nations/leech-lake-reservation.geojson  (working)
  site/data/leech-lake-reservation.geojson            (site copy)
The raw BIA fetch is kept at
  data/native-nations/bia-leech-lake-lar0033.geojson

Stdlib only. Re-run to refresh: python3 scripts/pull_leech_lake_reservation.py
"""
import json
import math
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING = os.path.join(ROOT, "data/native-nations/leech-lake-reservation.geojson")
SITE = os.path.join(ROOT, "site/data/leech-lake-reservation.geojson")
BIA = ("https://biamaps.geoplatform.gov/server/rest/services/"
       "DivLTR/BIA_AIAN_National_LAR/FeatureServer/0/query")

# Measured 2026-11-11 (UTM 15N) against the depicted chain
# (site/data/stretches.geojson + gaps): 2.34 mi inside, all Chip-12.
# Census re-measures 2.27 mi by the same method.
TRAIL_MILES_INSIDE = 2.34
TRAIL_SECTIONS_INSIDE = ["Chip-12"]
# Geometry-measured area (UTM 15N), 2026-11-11. BIA's GISACRES
# attribute (1,794,106) contradicts its own geometry — not used.
AREA_ACRES = 823249
# Label point, verified inside the BIA geometry 2026-11-11.
LABEL_LAT, LABEL_LON = 47.3539, -94.2592


def fetch():
    import urllib.parse
    q = (BIA + "?where=" + urllib.parse.quote("LARID = 'LAR0033'") +
         "&outFields=" + urllib.parse.quote("LARID,LARNAME,CLASSIFICATION,GISACRES,REGION") +
         "&returnGeometry=true&outSR=4326&f=geojson")
    req = urllib.request.Request(q, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def ring_centroid(ring):
    a = 0.0; cx = 0.0; cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        c = x1 * y2 - x2 * y1
        a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    a /= 2.0
    return (cx / (6 * a), cy / (6 * a)) if a else (ring[0][0], ring[0][1])


def point_in_ring(p, ring):
    x, y = p; inside = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def largest_outer_ring(geom):
    # MultiPolygon: outer ring of the largest polygon by bbox area.
    polys = geom["coordinates"]
    best = None; best_a = -1.0
    for poly in polys:
        ring = poly[0]
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        a = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if a > best_a:
            best, best_a = ring, a
    return best


def main():
    d = fetch()
    assert len(d["features"]) == 1, f"expected 1 feature, got {len(d['features'])}"
    f = d["features"][0]
    p = f["properties"]
    assert p["LARID"] == "LAR0033" and p["LARNAME"] == "Leech Lake", p
    verts = sum(len(r) for poly in f["geometry"]["coordinates"] for r in poly)
    assert f["geometry"]["type"] == "MultiPolygon", f["geometry"]["type"]
    # Sanity: the recorded label point must fall inside the geometry.
    assert point_in_ring((LABEL_LON, LABEL_LAT),
                         largest_outer_ring(f["geometry"])), "label outside BIA geometry"
    out = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "name": "Leech Lake Reservation",
                "band": "Leech Lake Band of Ojibwe",
                "source": "Bureau of Indian Affairs, AIAN Land Area Representation (AIAN-LAR)",
                "vintage": "AIAN-LAR national dataset (LAR0033), fetched 2026-11-11",
                "larid": "LAR0033",
                "area_acres": AREA_ACRES,
                "trail_miles_inside": TRAIL_MILES_INSIDE,
                "trail_sections_inside": TRAIL_SECTIONS_INSIDE,
                "label_lat": LABEL_LAT,
                "label_lon": LABEL_LON,
                "note": "Federal reservation boundary as published — not a legal survey.",
            },
        }],
    }
    for path in (WORKING, SITE):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(out, fh, separators=(",", ":"))
    print(f"vertices: {verts}")
    print(f"area: {AREA_ACRES:,} acres (geometry-measured)")
    print(f"trail inside: {TRAIL_MILES_INSIDE} mi ({', '.join(TRAIL_SECTIONS_INSIDE)})")
    print(f"wrote {WORKING} and {SITE}")


if __name__ == "__main__":
    main()

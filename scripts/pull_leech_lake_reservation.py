#!/usr/bin/env python3
"""Pull the Leech Lake Reservation boundary (public federal data).

Source (chosen 2026-11-11; see SOURCES.md "Leech Lake Reservation"):
  U.S. Census Bureau, TIGER/Line American Indian Areas (AIANNH),
  TIGERweb current vintage (BAS 2026), Federal American Indian
  Reservations layer — GEOID 1940R, "Leech Lake Reservation".
  Geometry verified identical in the Census 2020 and ACS 2025
  vintages on the same service, and cross-checked against the BIA
  AIAN-LAR national dataset (LAR0033): same overall extent, median
  boundary separation 37 m. The Census polygon is the pick: a single
  clean polygon (9,685 vertices) of the reservation proper; BIA's
  feature is coarser (3,999 vertices, 3 polygons) and its GISACRES
  attribute (1,794,106) contradicts its own geometry (~819,000 ac).
  The separate Census off-reservation trust-land feature (GEOID
  1940T, 0.05 sq km) is deliberately NOT included: this layer is
  the reservation itself.

Outputs (identical GeoJSON, full unclipped polygon):
  data/native-nations/leech-lake-reservation.geojson  (working)
  site/data/leech-lake-reservation.geojson            (site copy)

Stdlib only. Re-run to refresh: python3 scripts/pull_leech_lake_reservation.py
"""
import json
import math
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING = os.path.join(ROOT, "data/native-nations/leech-lake-reservation.geojson")
SITE = os.path.join(ROOT, "site/data/leech-lake-reservation.geojson")
TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/"
            "TIGERweb/AIANNHA/MapServer/2/query")

# Trail overlap measured 2026-11-11 against the depicted chain
# (site/data/stretches.geojson + gaps): 2.28 mi, all of it Chip-12.
TRAIL_MILES_INSIDE = 2.28
TRAIL_SECTIONS_INSIDE = ["Chip-12"]


def fetch():
    import urllib.parse
    q = (TIGERWEB + "?where=" + urllib.parse.quote("GEOID = '1940R'") +
         "&outFields=NAME,GEOID,MTFCC,FUNCSTAT,AREALAND,AREAWATER"
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


def label_point(geom):
    ring = geom["coordinates"][0]
    c = ring_centroid(ring)
    if point_in_ring(c, ring):
        return c
    # Fall back: densest interior grid point (pole-of-inaccessibility approx).
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    best = None; best_d = -1.0
    for i in range(41):
        for j in range(41):
            p = (min(xs) + (max(xs) - min(xs)) * i / 40,
                 min(ys) + (max(ys) - min(ys)) * j / 40)
            if not point_in_ring(p, ring):
                continue
            d = min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in ring[::25])
            if d > best_d:
                best, best_d = p, d
    return best


def main():
    d = fetch()
    assert len(d["features"]) == 1, f"expected 1 feature, got {len(d['features'])}"
    f = d["features"][0]
    p = f["properties"]
    assert p["NAME"] == "Leech Lake Reservation" and p["GEOID"] == "1940R", p
    land_ac = p["AREALAND"] / 4046.8564224
    water_ac = p["AREAWATER"] / 4046.8564224
    verts = sum(len(r) for r in f["geometry"]["coordinates"])
    lat, lon = label_point(f["geometry"])[1], label_point(f["geometry"])[0]
    out = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "name": "Leech Lake Reservation",
                "band": "Leech Lake Band of Ojibwe",
                "source": "U.S. Census Bureau, TIGER/Line American Indian Areas (AIANNH)",
                "vintage": "BAS 2026 (TIGERweb current); geometry identical in Census 2020 and ACS 2025 vintages",
                "geoid": "1940R",
                "area_acres": round(land_ac + water_ac),
                "land_acres": round(land_ac),
                "water_acres": round(water_ac),
                "trail_miles_inside": TRAIL_MILES_INSIDE,
                "trail_sections_inside": TRAIL_SECTIONS_INSIDE,
                "label_lat": round(lat, 4),
                "label_lon": round(lon, 4),
                "note": "Federal reservation boundary as published — not a legal survey.",
            },
        }],
    }
    for path in (WORKING, SITE):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(out, fh, separators=(",", ":"))
    print(f"vertices: {verts}")
    print(f"area: {round(land_ac + water_ac):,} acres "
          f"(land {round(land_ac):,}, water {round(water_ac):,})")
    print(f"label: {round(lat, 4)}, {round(lon, 4)}")
    print(f"wrote {WORKING} and {SITE}")


if __name__ == "__main__":
    main()
